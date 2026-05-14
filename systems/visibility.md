# Visibility

## 1. Overview

The visibility system answers the rendering pipeline's central question: *which of the cells around the player should the screen actually show this frame, and how?* Ultima V's two-dimensional scenes — overworld, underworld, towns, dwellings, castles, and keeps — all draw the world through an eleven-by-eleven viewport centred on the party. For each of those one hundred twenty-one cells, the engine decides one of three things on every redraw: the cell is fully visible (paint the underlying tile), the cell is dim periphery (paint the tile with a dimmed-edge marker), or the cell is hidden (paint nothing — the cell is dark, blocked, or outside the active light radius).

The decision is made by a producer that runs once per redraw, runs a
centre-out visibility carve over the viewport, takes account of the current
light radius, and writes a one-byte verdict into a fixed-size scratch grid in
the data segment. A second pass refines the edges of the visible region and
stamps active objects (NPCs, monsters, vehicles, the player avatar) into the
same grid on top of the terrain. The renderer then walks the grid one cell at a
time, consulting both the visibility verdict and a parallel terrain band, and
paints the corresponding tile to the screen.

The producer is called only when the visibility state is *dirty*. Most frames, only the player has moved by zero cells and the lighting hasn't changed; in that case the engine takes a much cheaper path that lazily refills any cells the compositor marked for terrain refetch, leaving the rest of the grid alone. A dirty flag in the resident data segment tells the per-frame redraw orchestrator which path to take.

This spec describes the viewport grid's shape, the inputs the producer reads, the visibility carve, the fog-edge refinement, the active-object compositing pass, and the renderer's contract for consuming the result. The dungeon and combat modes, which use different visibility models entirely, are described briefly at the end.

## 2. The viewport grid

The visibility grid is a rectangular block of bytes in the resident data segment, sized for the on-screen viewport. The active region is eleven rows of eleven columns — one hundred twenty-one cells — laid out row-major. Each row is *thirty-two bytes wide*, however; only the first eleven bytes per row are used, and the remaining twenty-one bytes of each row are scratch space that other passes (the active-object compositor, the renderer's special-tile fixups) read and write.

The layout looks like this, with columns zero through ten as the active window and the player at the centre:

```text
       col 0   col 5   col 10
       v       v       v
row  0 [..........]                .. = active cells (terrain or marker)
row  1 [..........]                XX = scratch / unused
row  2 [..........]
row  3 [..........]
row  4 [..........]
row  5 [.....P....]                P  = player position (row 5, col 5)
row  6 [..........]
row  7 [..........]
row  8 [..........]
row  9 [..........]
row 10 [..........]
       (each row: 11 active bytes + 21 trailing scratch bytes = 32 bytes)
```

The thirty-two-byte stride makes each visibility row a fixed-size slot even though only the first eleven bytes are active visibility cells. The trailing twenty-one bytes per row are not touched by the producer's main pass; they are scratch/staging space for adjacent visibility and rendering work.

The grid coexists with a *terrain band* of identical row count but a different stride. The terrain band uses sixteen bytes per row, also row-major over eleven rows, holding the underlying terrain tile bytes that the renderer falls back to when the visibility grid emits a "use companion buffer" marker. The two grids are fed by different producers (the visibility grid by the per-frame redraw, the terrain band by mode-entry and scroll-recentre handlers) and consumed together by the renderer; their contents are kept in lockstep by mode-entry initialisation.

Each byte in the visibility grid encodes one of several things at end-of-frame:

| Byte value      | Meaning                                                              |
|-----------------|----------------------------------------------------------------------|
| `0xFF`          | Hidden — fully obscured. The cell is outside the light radius, blocked by a sight-blocker, or off-map. The renderer paints nothing here; the previous frame's pixels stay. |
| `0x00`          | "Use companion buffer." The cell is visible but the terrain band holds the tile to paint. This is the normal successful active-object compositor output, including water-bound, water-creature, vehicle/avatar-family, and default-helper stamps. |
| `0xDD`          | Clear visible (in-radius). A marker indicating "this cell is fully lit." The renderer treats it as a terrain-tile-from-companion-buffer cue with full brightness. |
| `0x1C`          | Dim periphery. Same as `0xDD` but the cell is on the visibility-radius boundary; the renderer dims the painted tile. |
| `0x87`          | "Already rendered." A guard the active-object compositor checks to avoid double-stamping. Higher-priority sprite already in this cell. |
| any other byte  | A direct tile id or renderer marker. The renderer paints or interprets this byte directly. Used by terrain producers, the negative-light full-fill path, and a few terrain-aware compositor marker writes. |

The exact handling of `0x00`, `0xDC`, and `0xDD` is the renderer's contract; the producer and post-pass describe their own writes only in those terms.

## 3. Inputs

The producer reads several pieces of resident state on every dirty-frame call.

**Player position.** Two bytes in the data segment hold the player's world tile coordinates — column and row — for whatever map family the current scene uses. The producer subtracts the *scroll origin* (Section 4) to get a player position relative to the active map buffer, and offsets that by minus five so the upper-left corner of the eleven-by-eleven window sits at the right place in world space.

**Scroll origin.** Two bytes hold the column and row of the upper-left of the currently-loaded map chunk window in the overworld and underworld scenes. Town and dungeon-explore scenes set the scroll origin to zero (the active buffer is the entire 32×32 location grid, not a streamed chunk window).

**Scene identity.** A single byte distinguishes between mode families: zero for the overworld stream, one through some dozens for towns / dwellings / castles / keeps, a higher range for dungeon-explore, and an even higher range (at and above the high bit set) for combat. The producer mostly does not care which 2D scene type it is in — the visibility carve and the grid format are identical for all 2D scenes — but the choice of map buffer (Section 4) does depend on scene.

**Light radius.** A single byte that the lighting subsystem maintains, holding the player's current effective sight radius. The radius is large during outdoor daylight, smaller at night, smaller still in dungeons and at indoor scenes after dark, and clamped upward by a torch or a light spell. The producer treats the radius as a *signed* quantity:

| Sign            | Producer behaviour                                                  |
|-----------------|---------------------------------------------------------------------|
| Positive        | Normal case — run the visibility carve with the radius value.        |
| Zero            | Total darkness — leave the grid fully obscured. The player sees nothing.   |
| Negative        | Full-fill path — populate every cell from the world map regardless of visibility carve or radius. Reserved/debug-style compatibility branch; no normal shipped scene is known to drive it. |

The lighting subsystem owns the rules that decide what value goes into this byte; from the producer's point of view, the byte is read once per frame and passed down to the visibility carve helper.

**Visibility-dirty flag.** A single byte that other systems set when the visibility state must be recomputed: the player moved, the lighting changed, a live moongate animation frame was stamped, or a new scene was entered. The redraw orchestrator reads this byte to choose between the expensive path (run the producer) and the cheap path (lazy refill of consumed cells). The producer's caller clears the flag immediately after the producer returns.

**Active map buffer.** The world tiles that the visibility carve reads come from one of three buffers, selected by scene:

- **Overworld and underworld.** A one-kilobyte buffer holding the active 2×2 chunk window — four sixteen-by-sixteen chunks at adjacent offsets. The world is streamed: as the player approaches the edge of the loaded window, scene transitions reload chunks and shift the scroll origin.
- **Town / dwelling / castle / keep / dungeon-explore.** The same one-kilobyte buffer, interpreted as a single 32×32 grid for the entire location. The scroll origin is zero.
- **Combat.** A separate scratch grid (Section 11), pre-composited by the combat setup helper. The 2D-scene producer is not used in combat.

A leaf helper, the *world-tile getter*, encapsulates the three branches: given a tile column and row it returns a pointer to the byte that represents that tile in whichever buffer is currently active. Out-of-range queries to the location/dungeon-explore buffer return a sentinel byte address (a fixed location whose contents act as a "you walked off the map" tile).

**Local-light mask.** Non-combat scenes also maintain a separate thirty-two by
thirty-two local-light mask. A light-source refresh pass scans the active map
window for a narrow set of candidate tile ids, carves a fixed-radius region
around each source into the mask, and finalizes untouched mask cells to zero.
The visibility carve consults this mask in its boundary and out-of-radius
branches; do not model special light as only an inflation of the single global
light-radius byte.

## 4. The producer's three stages

The producer runs in three stages.

**Stage 1 — paint everything obscured.** The eleven-by-eleven active window is filled with the hidden marker (`0xFF`). Each row writes eleven `0xFF` bytes into the first eleven columns; the remaining twenty-one bytes per row are left untouched. After this stage, the entire grid says "nothing is visible."

**Stage 2 — branch on the light-radius sign.**

- **Light radius zero.** The producer skips both the visibility carve helper and the full-fill path. The grid stays fully obscured. This is the "pitch dark" case: night in the overworld with no torch, an unlit dungeon level, an extinguished town scene.
- **Light radius positive.** The producer hands the grid over to the visibility carve helper (Section 5) along with the player's local-window position and the radius. The helper starts from the centre cell and expands through candidate neighbours, writing tile bytes for cells it resolves as visible and writing a working all-zero marker for cells it has considered but not resolved as visible. After the helper returns, a post-pass walks the grid and converts every `0x00` byte back to `0xFF` (the hidden marker), so unresolved cells do not trigger the cheap terrain-refill path on the next frame.
- **Light radius negative.** The producer takes a debug-style full-fill path: every cell is populated from the world map directly, without any visibility carve or radius clamp. The grid ends up holding exactly the underlying terrain in every cell, no fog applied. No normal shipped scene is known to write the negative light value; a compatibility implementation can preserve the branch without treating it as ordinary gameplay visibility.

**Stage 3 — return.** The producer does not clear or flip any flags itself; the redraw orchestrator handles the dirty-flag reset.

End-of-stage state, per case:

```text
positive light:  grid cells resolved by the carve = real tile bytes;
                 grid cells not resolved by the carve = 0xFF.

zero light:      every cell = 0xFF.

negative light:  every cell = real tile byte (no fog).
```

The grid bytes leaving the producer are then handed to the fog post-pass
(Section 7) for edge refinement and active-object compositing.

## 5. The Visibility Carve

The visibility carve helper is called by the producer for the positive-light
case. It is queue-based rather than a simple "cast one independent ray to every
cell" algorithm.

The helper receives the grid base address, row stride, centre-cell position,
world-coordinate origin, and light-radius value. It seeds a work queue with the
player's centre cell, writes that centre cell from the world-tile getter, then
repeatedly pops a coordinate and examines its eight neighbours in a fixed ring
order:

The neighbour expansion order is west, southwest, south, southeast, east,
northeast, north, northwest.

For each candidate neighbour, the helper rejects out-of-window coordinates,
uses the zero byte as an in-progress/already-considered marker, reads the
candidate world tile, computes squared distance from the centre, and applies
its propagation tests. It may then write the candidate tile, leave a zero
working marker for the producer's post-pass to collapse to hidden, or enqueue
the candidate for further expansion.

The settled external contract is:

- The player's centre cell is always seeded first and is visible when the
  positive-light producer runs.
- The helper expands through neighbouring cells from the centre rather than
  scanning the viewport row by row.
- The helper uses the same squared-distance primitive as the fog post-pass for
  centre-relative distance checks.
- The caller-provided light value is a squared-distance threshold: cells whose
  squared distance from the centre is less than or equal to that value are
  inside the main light radius.
- A zero byte written by this helper is not a renderer-visible result. The
  producer converts helper-written zeros back to the hidden marker before the
  fog post-pass runs.

The propagation predicate is tile-id based but separate from movement
passability. Ordinary tiles propagate the carve unless they are in the
visibility propagation-blocker set in Section 6. Five special-case tile ids use
a stricter rule: they propagate only when they are orthogonally adjacent to the
centre cell, which is the case where the squared-distance helper returns `1`.

Inside the main light threshold, accepted candidates are written as their
world tile. Outside that threshold, the helper consults the separate local-light
mask:

- A propagating candidate can still extend the queue through dark space. It is
  painted only if its local-light mask cell is nonzero; otherwise it is left as
  a zero working marker and may still propagate onward.
- A non-propagating candidate outside the main radius is painted only when it is
  reached from a nonzero parent cell and both the parent and candidate cells
  are locally lit. Otherwise it remains hidden and does not extend the queue.

Do not implement this as a Bresenham line caster, a shadow-caster, or a
movement-passability rule. It is a centre-out neighbour carve with a separate
propagation-blocker set and local-light mask.

## 6. Sight-affecting tiles

Whether a tile affects sight is a property of the tile id, but the visibility
rule is its own classifier. It is not derived from movement passability, LOOK
text, or the tile's broad visual family.

The helper members below are expressed as public tile-catalog identities, sorted
by semantic family rather than by their resident table order.

| Tile identity | Visibility propagation rule |
|---------------|----------------------------|
| Forest tree tile `0x09` | Stops propagation. |
| Hill / mountain / lava-rock variants `0x0A`, `0x0C`, `0x0D` | Stop propagation. |
| Bookshelf / dresser / vanity / trunk variants `0x4D..0x4F` | Stop propagation. |
| Sign-post tile `0x5A` | Stops propagation. |
| Bat frame `0x97` | Stops propagation. |
| Gargoyle frames `0xB8..0xB9` | Stop propagation. |
| Insect Swarm frame `0xBC` | Stops propagation. |
| Headless frames `0xD0..0xD3` | Stop propagation. |
| Rot Worm frame `0xF8` | Stops propagation. |
| Shadow Lord frames `0xFE..0xFF` | Stop propagation. |
| Bookshelf / dresser variants `0x4A..0x4B` | Propagate only when orthogonally adjacent to the centre cell. |
| Giant Spider frame `0x98` | Propagates only when orthogonally adjacent to the centre cell. |
| Gargoyle frames `0xBA..0xBB` | Propagate only when orthogonally adjacent to the centre cell. |

Tiles not named in either group use the ordinary propagation rule: they may
extend the centre-out carve.

Active-object slots are not part of the tile propagation classifier. The
visibility carve helper resolves terrain visibility first; the active-object
compositor (Section 8) then projects visible actors and vehicles onto the
finished grid. Actor visibility is therefore gated by the terrain cell's
visibility result, not by direct participation in the centre-out carve.

Confirmed high-level expectations such as closed doors being distinct from open
doors, forest interiors being distinct from forest edges, and mountains being
opaque should be represented through this isolated predicate rather than being
inferred from visual family names.

## 7. Fog edge refinement

After the producer returns, a post-pass walks the grid and refines the fog edges. The pass runs in non-combat scenes only — combat materialises terrain through a separate path (Section 11) and skips the refinement.

The refinement uses a small squared-distance lookup centred on viewport cell `(5, 5)`, distinct from the producer's light radius. The helper folds each coordinate around the centre (`folded = min(coord, 10 - coord)`), indexes a resident 6×6 table, and returns `(5 - folded_x)^2 + (5 - folded_y)^2`. The post-pass compares that squared distance to the literal threshold `5` and toggles two specific marker bytes:

- A cell currently holding the *clear-visible* marker (`0xDD`) whose squared distance is greater than `5` is downgraded to the *dim-periphery* marker (`0x1C`). It is still visible, but the renderer will dim it.
- A cell currently holding the *dim-periphery* marker (`0x1C`) whose squared distance is at most `5` is upgraded back to the *clear-visible* marker (`0xDD`).

This is not a five-cell radius. The clear-marker core covers the centre cell and cells within squared Euclidean distance `5` of it; marker cells farther out in the eleven-by-eleven viewport are dimmed. The lookup is reflection-symmetric across the viewport centre and avoids computing a square root at runtime.

This marker refinement is independent of the producer's light radius. The producer decides which terrain cells are visible at all; the post-pass only adjusts cells already carrying the two renderer marker bytes. It is a no-op for grids where the visibility carve helper has emitted real tile bytes instead of `0xDD` / `0x1C` markers.

The refinement only toggles between the two marker bytes; cells holding any other value (a real tile byte, the hidden marker, the use-companion marker, the already-rendered marker) are left unchanged. The pass is a no-op for grids where the visibility carve helper has not emitted those markers — most ordinary frames have a visible-region full of *real tile bytes* rather than markers, so the toggle does nothing. The markers are written only by the active-object compositor (Section 8) and by certain mode-entry handlers; the refinement is what keeps them consistent with the player's current radius.

## 8. Active-object compositing

The same post-pass that handles fog refinement also stamps active objects into the grid. The active-object table — thirty-two slots of eight bytes each, shared with the rest of the engine — holds the player avatar (slot zero), all on-screen NPCs, monsters, vehicles, and animated props.

The compositor walks the table from slot thirty-one down to slot zero. Walking backwards means low-indexed slots paint *on top of* higher-indexed ones — and slot zero is the player, so the avatar always draws on top of any overlapping NPC or monster.

For each non-empty slot the compositor:

1. Reads the slot's world coordinates and floor.
2. In non-combat scenes, projects the world coordinates into the eleven-by-eleven viewport: subtract the player's position then add five (so the player sits at row five, column five). If the result is outside the eleven-by-eleven range, or the slot is on a different floor than the player, the slot is skipped.
3. Reads the corresponding visibility-grid cell. If the cell currently holds the hidden marker (`0xFF`) — the slot is in fog — it is skipped: no point compositing an invisible NPC. If the cell holds the already-rendered marker (`0x87`), it is also skipped: a higher-priority sprite has already claimed the cell.
4. Otherwise, stamps the slot's tile bytes into one or both of the two grids,
   with class-specific rules:
   - **Water-bound companion-band classes.** If the slot's type byte belongs to
     the `0xE8..0xEB` class, or is exactly `0x1E` or `0x1F`, the compositor
     stamps the slot's frame byte into the terrain band and writes the
     use-companion marker (`0x00`) into the visibility grid. If the visibility
     grid cell is already `0x00`, the slot is skipped instead of restamping.
   - **Water-creature companion-band classes.** If the slot's frame byte is
     exactly `0x1D` or `0x1E`, the compositor stamps that frame byte into the
     terrain band and writes the use-companion marker into the visibility grid.
   - **Vehicle/avatar-family companion branch.** If the slot's type byte is
     exactly `0x5C` and the current visibility-grid cell holds marker `0x92`,
     the compositor stamps the slot's frame byte into the terrain band and
     leaves the visibility grid on the use-companion path. If the underlay
     marker is not present, this branch falls through to the default helper.
   - **Default helper.** All other slots are handed to the default tile
     compositor. Its ordinary successful output is the same companion-band
     shape: final tile in the terrain band and `0x00` in the visibility grid.
     A small set of effective tile bytes are terrain-aware and can suppress or
     remap the final tile before that stamp.

The default helper treats effective tile bytes `0x1C`, `0x12..0x15`,
`0x28..0x2B`, and `0x40..0xFF` as terrain-aware. Other effective tile bytes
stamp unchanged through the companion band. Terrain-aware stamps use the live
world/combat tile at the object's coordinate, plus one neighbouring row for a
few edge shapes:

| Terrain condition | Compositor result |
|---|---|
| Current terrain `0xEC` or `0x0A` | Suppress the active-object stamp; leave the existing cell state intact. |
| Current terrain `0x57` | Write direct visibility-grid marker `0x38`; do not write the terrain band. |
| Current terrain `0x6A` or `0x6B`, and effective tile in `0x80..0x8F` or `0x28..0x2B` | Suppress the active-object stamp. |
| Current terrain `0x6A` or `0x6B`, any other effective tile | Stamp the effective tile unchanged through the companion band. |
| Effective tile `0x80..0xFF`, with any other current terrain | Stamp the effective tile unchanged through the companion band. |
| Current terrain `0x84` | Stamp one of `0x60..0x63`. |
| Current terrain `0x85` | Stamp one of `0x64..0x67`. |
| Current terrain `0x90`, with the previous-row terrain equal to `0x9B` or `0x9C` | Stamp one of `0x38..0x3B`. |
| Current terrain `0x90`, without that previous-row match | Stamp `0x30`. |
| Current terrain `0x91` or `0x93` | Stamp `0x31` or `0x33`, respectively. |
| Current terrain `0x92`, with the next-row terrain equal to `0x9A` or `0x9C` | Stamp one of `0x34..0x37`. |
| Current terrain `0x92`, without that next-row match | Stamp `0x32`. |
| Current terrain `0x9D` or `0x9E` | Stamp one of `0x3C..0x3F`. |
| Current terrain `0xAB` | Stamp `0x1A`. |
| Current terrain `0xC8` | Stamp `0x17`. |
| Current terrain `0xC9` | Stamp `0x18`. |
| Any other current terrain, with previous-row terrain `0x9D` and the projected viewport row not on the top edge | Write direct marker `0x9E` into the previous viewport row, then stamp the effective tile unchanged through the companion band. |
| Any other current terrain | Stamp the effective tile unchanged through the companion band. |

The four-entry variant choices above (`0x60..0x63`, `0x64..0x67`,
`0x38..0x3B`, `0x34..0x37`, and `0x3C..0x3F`) use the shared variant selector:
when the current active character's class letter is Tinker, select the first
entry; otherwise select a uniform random entry from the four-value range.

Before the per-slot loop runs, the compositor refreshes slot zero's bytes from the world-state globals: the avatar tile id, the player's world coordinates, the player's floor. This ensures the player slot reflects the current frame's truth before anything else is composited; the slot's data may otherwise be stale because the active-object animator runs only on certain ticks.

The end state, after the compositor: the visibility grid contains either real tile bytes resolved by the carve, markers (`0xFF`, `0x1C`, `0xDD`, `0x00`, `0x87`), or direct marker writes from terrain-aware compositor cases. Active-object visual tiles that survive the cell guards normally live in the terrain band behind the `0x00` marker. Both grids are then handed to the renderer.

## 9. The renderer's contract

The renderer (a separate system, described in its own spec) walks the visibility grid one cell at a time and paints the corresponding tile into the on-screen viewport. For each cell:

- If the cell holds the hidden marker (`0xFF`), nothing is painted. The previous frame's pixels remain; if the cell was visible last frame and is hidden this frame, a clear of those pixels is the renderer's responsibility.
- If the cell holds the use-companion marker (`0x00`), the renderer reads the corresponding cell of the terrain band and paints that tile.
- If the cell holds the dim-periphery marker (`0x1C`) or clear-visible marker (`0xDD`), the renderer reads the terrain band and paints the tile, applying a dim or full-brightness palette respectively.
- If the cell holds any other byte, the renderer paints that byte as a tile id directly.

The renderer does not own the visibility-grid zeroing that enables lazy refill.
That zeroing is performed by the active-object compositor path when it prepares
cells that need terrain refetch after sprite compositing. The renderer consumes
the grid as prepared by the producer/post-pass pipeline.

The renderer and its per-cell visual/effect walker are read-only consumers of
the visibility grid. They compare marker bytes, consult the companion terrain
band when the grid cell is the use-companion marker, and dispatch the effective
cell value to the display/effect layer, but they do not clear, refill, or
rewrite the eleven-by-eleven visibility grid. The zero cells consumed by the
next cheap path are therefore leftovers from the previous frame's
active-object compositor, not a post-render side effect.

No traced gameplay system outside this viewport render/effect path reads the
dim-periphery marker differently from the clear-visible marker. Treat `0x1C`
and `0xDD` as render-visible brightness markers: visibility production and
fog refinement decide which marker is present, while non-render gameplay
queries must not infer separate collision, interaction, or memory-map state
from either value.

The renderer does not consult the producer or the post-pass; it sees only the resulting bytes in the two grids. This decoupling is what lets the engine support different visibility producers (overworld, dungeon, combat) feeding the same renderer, with each producer responsible for materialising the grid into the renderer's expected end-state.

## 10. The cheap path

Most frames are *not* dirty: the player has not moved, the light has not changed, and no event has dirtied the visibility state. On those frames, the per-frame redraw orchestrator skips the producer entirely and instead runs a lazy refill loop directly on the grid.

The cheap path walks the eleven-by-eleven active window. For each cell whose current byte is *zero*, the path queries the world-tile getter at the cell's world coordinates and writes the resulting tile byte. Cells whose current byte is non-zero — a real tile byte, a marker, or an active-object stamp — are left alone.

The interpretation: zero cells are "marked by the compositor as needing a fresh
tile this frame." Cells left nonzero are still valid; they retain their fog
markers and active-object stamps from the previous expensive recompute.

The cheap path *does not* recompute the visibility carve, does not consult the light radius, and does not touch fog markers. It is a pure terrain-refill, intended to keep the screen showing the current map without redoing the visibility math. The fog post-pass and active-object compositor still run after the cheap path each frame, so on-screen sprites and dim-periphery markers stay accurate.

The cost of the cheap path is roughly one tile-fetch per consumed cell — a small fraction of the producer's full-grid visibility carve. The engine is built around this asymmetry: the producer is an expensive once-per-event recompute, the cheap path is a per-frame topping-up.

## 11. Mode differences

**Overworld and underworld.** Use the full producer pipeline as described above. The active map buffer is the streamed 2×2 chunk window. The producer is called when the visibility-dirty flag is set, which happens on every player step (the step handler dirties the flag), on lighting changes (the per-turn cleanup dirties the flag if the daylight value changed), and when the moongate animator stamps a live transient frame.

**Town, dwelling, castle, keep.** Use the same producer pipeline with the active map buffer interpreted as a single 32×32 grid (no chunk streaming). Indoor lighting is computed against the local scene's lighting context, which may be different from the surrounding outdoor light. Some interiors are lit at night by candles and lamps; others are dark. The producer doesn't care which — it just consumes whatever light radius the lighting subsystem hands it.

**Dungeon-explore.** Uses a different visibility model entirely. There is no eleven-by-eleven viewport grid; the dungeon view is a first-person three-dimensional projection drawn by a dedicated renderer. The light gate is binary: if neither torch nor light-spell counter is active, the panel is black; otherwise the renderer walks the current eight-by-eight dungeon geometry until blocked. Live dungeon-cell bytes do not store persistent visibility memory, and V-View's visited map is temporary scratch state owned by the dungeon view overlay.

**Combat.** Uses a fully materialised terrain grid in a separate buffer, pre-composited by the combat setup helper. The combat producer initialises this buffer to the hidden marker and fills it through the same visibility carve helper family the 2D-scene producer uses, but combat does not consult the global light radius — combat scenes have their own lighting context, and the encoding does not include fog markers. The post-pass (fog refinement plus active-object compositing) skips combat scenes entirely; combat manages active-object compositing through its own round walker.

The mode boundary is enforced by the redraw orchestrator: it inspects the scene byte before choosing a path. Combat-class scenes use the high-range reader branch, and the traced gameplay writer uses `0xFF` for that state. That branch takes a *blat-copy* path that copies the pre-composited combat terrain grid byte-for-byte into the visibility grid, then runs the renderer. The producer is not called.

## 12. Local Light Sources

A handful of map and runtime tiles can make nearby cells visible independently
of the player's ambient/personal light radius. The observed mechanism is a
separate local-light mask, not a simple rewrite of the one light-radius byte.

The local-light refresh pass:

1. Clears a thirty-two by thirty-two mask to the hidden sentinel.
2. Scans the active map window for local-light-source candidates.
3. For each source, clears an eleven-by-eleven per-source visited grid.
4. Runs the same centre-out visibility carve into the thirty-two by
   thirty-two mask, using the source as the centre and a fixed source radius.
5. Converts untouched mask cells to zero, leaving carved/source cells nonzero.

The candidate source ids currently proven by the resident lookup are
`0xB0..0xB3`, `0xBC..0xBF`, `0xDC`, and `0xDE`. Their exact gameplay names and
the full visual names should be sourced from the tile catalog rather than from
this byte list alone.

The resident redraw order gives the mask one additional non-combat writer: the
moongate animator. The NPC/light refresh path can rebuild the mask after
rewriting in-scene NPC light tiles, then the moongate animator may stamp the
current moongate frame into the same thirty-two-byte-stride scratch region and
set the visibility-dirty flag. The following expensive visibility producer
then sees the current mask contents during the carve. Preserve that ordering:
local-light refresh first, transient moongate frame stamps second, visibility
carve third. The moongate writes are transient visibility/render state, not
durable map edits and not replacements for the ambient light-radius byte.

Implementations should keep this as an isolated local-light resource. It is
part of visibility propagation state, not a permanent mutation of map bytes and
not a replacement for the ambient daylight / torch / spell counters.

## 13. Visibility Boundaries And Remaining Parity Work

The visibility-grid contract is complete at gameplay depth: producer fill
states, centre-out carve behavior, blocker rules, marker refinement,
active-object compositing, renderer/effect read contract, cheap terrain refill,
mode boundaries, local-light mask ownership, moongate-mask ordering, and the
negative-light full-fill compatibility branch are fixed. Remaining work is
visual parity or external-tool synchronization policy rather than ordinary
gameplay visibility behavior.

- **Renderer marker live palette.** The producer/compositor writes and the
  read-only renderer/effect consumption for `0x00`, `0x1C`, `0xDD`, `0x87`,
  `0xFF`, and the direct terrain-aware helper markers are now specified.
  Remaining exactness, if visual pixel parity is required, is display-driver
  palette/art verification for those marker bytes rather than visibility-grid
  ownership.

- **Dungeon visual parity.** Dungeon mode does not use the two-dimensional
  visibility grid and does not store persistent visibility memory in live
  dungeon cells. Remaining dungeon exactness belongs to the dungeon-mode
  renderer and V-View visual glyph/pixel parity, not to this visibility-grid
  system.

- **The asynchronous-read race window.** External readers sampling the visibility grid mid-frame see partial state — static-analysis notes record eleven distinct hashes during a thirty-sample passive read of one settled scene. Implementations that expose the grid to external readers should provide a synchronisation point.

## 14. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of those notes' assembly excerpts, byte offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The visibility producer's three-stage shape (hidden-fill, visibility-carve
  delegation, post-pass), the negative-light full-fill path, and the
  radius-sign branching — `u5-decomp/functions/ULTIMA_EXE/0x5D0A_visibility_producer.md`.
- The queue-based visibility carve, propagation-blocker set, and special-case
  adjacent-only propagation rule
  — `u5-decomp/functions/ULTIMA_EXE/0x5A28_visibility_buffer_setup.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x5DFE_visibility_tile_class.md`.
- The local-light mask refresh pass, source-candidate lookup, per-source carve
  radius, and final untouched-cell zeroing —
  `u5-decomp/functions/ULTIMA_EXE/0x5E4A_light_radius_lookup.md`.
- The Moonstone-slot live-gate refresh caller that rebuilds the local-light
  mask after in-scene tile rewrites -
  `u5-decomp/functions/ULTIMA_EXE/0x475A_npc_schedule_tick.md`.
- The moongate sprite writer that stamps into the same mask-shaped scratch
  region — `u5-decomp/functions/ULTIMA_EXE/0x7040_render_2x16_sprite.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x70A6_moongate_or_event.md`.
- The visibility-grid writer scan proving the renderer is read-only on the
  eleven-by-eleven grid and that zero cells are compositor-owned -
  `u5-decomp/notes/visibility_grid_zeroing_2026-05-08.md`.
- The fog post-pass — squared-distance marker toggling, active-object compositing, and compositor-owned visibility-grid zeroing for cells that need terrain refetch — `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md` and `u5-decomp/notes/visibility_grid_zeroing_2026-05-08.md`.
- The 6×6 folded squared-distance helper used by the fog post-pass — `u5-decomp/functions/ULTIMA_EXE/0x6FF0_range_to_player.md`. Combat AI target scoring uses a separate computed range primitive covered in `systems/combat.md`.
- The redraw orchestrator that calls the producer on dirty frames, takes the cheap path on clean frames, blat-copies the combat terrain on combat frames, and clears the dirty flag after the producer returns — `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The world-tile getter that dispatches between combat, overworld 2×2 chunk window, and town/dungeon-explore single-grid buffers, including the out-of-bounds sentinel — `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The default active-object compositor helper and its 0..3 variant selector -
  `u5-decomp/functions/ULTIMA_EXE/0x51B8_monster_spawn_table.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x51A0_combat_class_roll.md`.
- The cross-overlay alias and callsite census for the same world-tile getter -- `u5-decomp/functions/ULTIMA_EXE/0xC232_tile_at_world_coord.md`.
- The overworld map family's chunk layout (BRIT.DAT sparse, UNDER.DAT dense), the four-class location-DAT format, and the combat arena format that combat pre-composites — `u5-decomp/formats/maps.md`.
- The resident data segment's fixed locations for the visibility grid, the terrain band, and the per-cell scrap regions — `u5-decomp/formats/data-ovl.md`.
- The visibility-system analysis notebook from the companion-app project, used as a starting reference for buffer addresses, scene-to-routine map, and the asynchronous-read race observations — `ninth-virtue/docs/visibility-re.md:11-352`.
