# Visibility

## 1. Overview

The visibility system answers the rendering pipeline's central question: *which of the cells around the player should the screen actually show this frame, and how?* Ultima V's two-dimensional scenes — overworld, underworld, towns, dwellings, castles, and keeps — all draw the world through an eleven-by-eleven viewport centred on the party. For each of those one hundred twenty-one cells, the engine decides one of three things on every redraw: the cell is fully visible (paint the underlying tile), the cell is dim periphery (paint the tile with a dimmed-edge marker), or the cell is hidden (paint nothing — the cell is dark, blocked, or outside the current lighting threshold).

The decision is made by a producer that runs once per redraw, runs a
centre-out visibility carve over the viewport, takes account of the current
lighting threshold, and writes a one-byte verdict into a fixed-size scratch grid
in the data segment. A second pass refines the edges of the visible region and
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
| `0xFF`          | Hidden — fully obscured. The cell is outside the lighting threshold, blocked by a sight-blocker, or off-map. The renderer paints nothing here; the previous frame's pixels stay. |
| `0x00`          | "Use companion buffer." The cell is visible but the terrain band holds the tile to paint. This is the normal successful active-object compositor output, including water-bound, water-creature, vehicle/avatar-family, and default-helper stamps. |
| `0xDD`          | Clear visible (inside the near/far distance of Section 7). A marker indicating "this cell is fully lit." The renderer treats it as a terrain-tile-from-companion-buffer cue with full brightness. |
| `0x1C`          | Dim periphery. Same as `0xDD` but the cell is beyond the fixed near/far distance of Section 7; the renderer dims the painted tile. |
| `0x87`          | "Already rendered." A guard the active-object compositor checks to avoid double-stamping. Higher-priority sprite already in this cell. |
| any other byte  | A direct tile id or renderer marker. The renderer paints or interprets this byte directly. Used by terrain producers, the negative-light full-fill path, and a few terrain-aware compositor marker writes. |

The exact handling of `0x00`, `0xDC`, and `0xDD` is the renderer's contract; the producer and post-pass describe their own writes only in those terms.

## 3. Inputs

The producer reads several pieces of resident state on every dirty-frame call.

**Player position.** Two bytes in the data segment hold the player's world tile coordinates — column and row — for whatever map family the current scene uses. The producer subtracts the *scroll origin* (Section 4) to get a player position relative to the active map buffer, and offsets that by minus five so the upper-left corner of the eleven-by-eleven window sits at the right place in world space.

**Scroll origin.** Two bytes hold the column and row of the upper-left of the currently-loaded map chunk window in the overworld and underworld scenes. Town and dungeon-explore scenes set the scroll origin to zero (the active buffer is the entire 32×32 location grid, not a streamed chunk window).

**Scene identity.** A single byte distinguishes between mode families: zero for the overworld stream, one through some dozens for towns / dwellings / castles / keeps, a higher range for dungeon-explore, and an even higher range (at and above the high bit set) for combat. The producer mostly does not care which 2D scene type it is in — the visibility carve and the grid format are identical for all 2D scenes — but the choice of map buffer (Section 4) does depend on scene.

**Lighting threshold.** A single byte that the lighting subsystem maintains and
that the producer forwards, unaltered, to the visibility carve. This value is
**not a sight radius**. It is a **squared-distance threshold**, compared
directly against each viewport cell's squared distance from the centre. Nothing
between the lighting subsystem and that comparison squares it, halves it,
shifts it, scales it, or maps it through a table, and this document's Section 5
comparison is the *only* place in the engine that uses the value **as a
distance threshold**. Exactly one other site reads the byte, and not as a
distance: the night-time beacon of Section 12.6 tests it against the
full-daylight value as a day/night gate before it runs
(`systems/lighting.md` Sections 3 and 7.2). No third reader exists.

Earlier revisions of this section described the byte as "the player's current
effective sight radius". That wording is withdrawn in full; it contradicted
Section 5, and it is the reading this section now explicitly forbids.

Define the distance measure once, because the rest of this document and
`systems/lighting.md` both use it. The viewport is eleven by eleven with the
player at the centre cell, row five and column five. A cell's *centre distance*
is the sum of the squares of its signed offsets from that centre:

```text
d2 = dx * dx + dy * dy       with dx, dy each in -5 .. +5
```

`d2` runs from zero at the player's own tile to fifty at each of the four
corners; it is never a linear tile count. A cell is **inside the lighting
threshold** when

```text
d2 <= L
```

for the threshold value `L`. The comparison is **inclusive**, and the inclusive
sense matters at both ends of the usable range: it is what makes the corners lit
at the full-daylight value of fifty, and what makes the four diagonal
neighbours lit at the full-dark value of two.

The lighting subsystem owns the rules that decide what value goes into this byte
(`systems/lighting.md` Sections 3, 4 and 7); the producer reads it once per
dirty frame and hands it down unchanged.

Producer behaviour by value:

| Value           | Producer behaviour                                                  |
|-----------------|---------------------------------------------------------------------|
| Positive        | Normal case — run the visibility carve with the value as the inclusive squared-distance threshold. |
| Zero            | Total blackout — the carve is skipped outright and the grid is left fully obscured, including the player's own cell. Reachable only through the void-tile override in `systems/lighting.md` Section 7; it is *not* the ordinary night-time state. |
| Negative        | Full-fill path — populate every cell from the world map with no carve and no threshold. Structurally unreachable in the shipped 2D pipeline: the redraw orchestrator zero-extends the unsigned byte before the call, so the value handed to the producer is always in the range zero to two hundred fifty-five. Preserve the branch for compatibility, but no shipped scene drives it. |

**The threshold's cell set.** Before line of sight is applied, the set of cells
that clear the distance gate is fixed by `L` alone. These are the values the
lighting subsystem can actually produce, and the resulting counts are the
cheapest conformance test available for a reimplementation:

| Threshold `L`  | Where it comes from                              | Cells inside the gate (of 121) | Farthest cell along a row or column |
|---------------:|--------------------------------------------------|-------------------------------:|------------------------------------:|
| 0              | Void-tile blackout override                       | 0 (the carve never runs)       | —                                   |
| 2              | Full dark: night, the Underworld, below-entry floors, Ararat | 9 (the player's cell and all eight neighbours) | 1              |
| 5              | Dawn/dusk gradient step                           | 21                             | 2                                   |
| 10             | Dawn/dusk gradient step; torch floor              | 37                             | 3                                   |
| 18             | Light-spell floor                                 | 61                             | 4                                   |
| 20             | Dawn/dusk gradient step                           | 69                             | 4                                   |
| 34             | Dawn/dusk gradient step                           | 109                            | 5                                   |
| 49             | Dawn/dusk gradient step                           | 117 (every cell but the four corners) | 5                            |
| 50             | Full daylight, clock hours six through eighteen   | 121 (the whole viewport)       | 5                                   |

Because `d2` only takes thirty-six distinct values, the cell count is a step
function of `L`. The complete set of plateaus over the whole byte range that the
carve can meaningfully see is:

```text
L = 0      ->   0 cells      L = 16      ->  49 cells
L = 1      ->   5 cells      L = 17      ->  57 cells
L = 2..3   ->   9 cells      L = 18..19  ->  61 cells
L = 4      ->  13 cells      L = 20..24  ->  69 cells
L = 5..7   ->  21 cells      L = 25      ->  81 cells
L = 8      ->  25 cells      L = 26..28  ->  89 cells
L = 9      ->  29 cells      L = 29..31  ->  97 cells
L = 10..12 ->  37 cells      L = 32..33  -> 101 cells
L = 13..15 ->  45 cells      L = 34..40  -> 109 cells
                             L = 41..49  -> 117 cells
                             L >= 50     -> 121 cells
```

Two rules complete the gate's contract, and both are stated again with their
mechanism in Section 5:

- **The player's own cell is seeded unconditionally**, before any distance
  comparison, so it is visible at every nonzero threshold. Only the zero-value
  blackout hides it.
- **A cell inside the threshold is made visible regardless of whether its
  terrain blocks sight.** Opacity governs whether the carve *continues past* a
  cell, never whether that cell itself is seen. A mountain one tile from the
  party is drawn; the ground behind it is not.

**Do not convert the threshold to a radius.** Treating the byte as a linear
radius and squaring it before the comparison over-lights every value on the
scale, and the error grows quickly because the comparison is against a squared
quantity. Side by side, with `L` used as the threshold (correct) versus `L` used
as a radius whose square becomes the threshold (wrong):

| Value | Correct: cells at `d2 <= L` | Wrong: cells at `d2 <= L * L` |
|---:|---:|---:|
| 2 (full dark) | 9 | 13 |
| 5 (gradient step) | 21 | 81 |
| 10 (torch) | 37 | 121 |
| 18 (light spell) | 61 | 121 |
| 50 (full daylight) | 121 | 121 |

The bug is invisible in daytime outdoor testing, because at the full-daylight
value of fifty both readings light all one hundred twenty-one cells. Test the
distinction with a torch or a light spell in the dark, or at full dark with no
personal light at all — those are the cases where the two readings differ
visibly, and all three are directly observable in play.

**A conformance trap worth recording.** A scene walled by sight-blocking terrain
can produce a visible-cell count that coincides with a small threshold's disc
size. A daytime interior whose flood is cut short by blocker tiles can settle at
sixty-nine visible cells, which is also exactly the disc size for thresholds
twenty through twenty-four — but at that hour the threshold is fifty and all one
hundred twenty-one cells clear the distance gate, with the reduction coming
entirely from blockers. Never infer the threshold from a visible-cell count in a
scene that contains blockers; use an open outdoor scene instead.

**Visibility-dirty flag.** A single byte that other systems set when the visibility state must be recomputed: the player moved, the lighting changed, the night-time beacon lit or cleared a local-light cell, or a new scene was entered. The redraw orchestrator reads this byte to choose between the expensive path (run the producer) and the cheap path (lazy refill of consumed cells). The producer's caller clears the flag immediately after the producer returns.

**Active map buffer.** The world tiles that the visibility carve reads come from one of three buffers, selected by scene:

- **Overworld and underworld.** A one-kilobyte buffer holding the active 2×2 chunk window — four sixteen-by-sixteen chunks at adjacent offsets. The world is streamed: as the player approaches the edge of the loaded window, scene transitions reload chunks and shift the scroll origin.
- **Town / dwelling / castle / keep / dungeon-explore.** The same one-kilobyte buffer, interpreted as a single 32×32 grid for the entire location. The scroll origin is zero.
- **Combat.** A separate scratch grid (Section 11), pre-composited by the combat setup helper. The 2D-scene producer is not used in combat.

A leaf helper, the *world-tile getter*, encapsulates the three branches: given a tile column and row it returns a pointer to the byte that represents that tile in whichever buffer is currently active. Out-of-range queries to the location/dungeon-explore buffer return a sentinel byte address (a fixed location whose contents act as a "you walked off the map" tile).

**Local-light mask.** Non-combat scenes also maintain a separate thirty-two by
thirty-two local-light mask. A light-source refresh pass scans the active map
window for a narrow set of candidate tile ids, carves a fixed-threshold region
around each source into the mask, and finalizes untouched mask cells to zero.
The visibility carve consults this mask for candidates that fall outside the
lighting threshold; do not model special light as only an inflation of the
single global lighting-threshold byte.

## 4. The producer's three stages

The producer runs in three stages.

**Stage 1 — paint everything obscured.** The eleven-by-eleven active window is filled with the hidden marker (`0xFF`). Each row writes eleven `0xFF` bytes into the first eleven columns; the remaining twenty-one bytes per row are left untouched. After this stage, the entire grid says "nothing is visible."

**Stage 2 — branch on the lighting threshold.**

- **Threshold zero.** The producer skips both the visibility carve helper and the full-fill path. The grid stays fully obscured, the player's own cell included. This is the total-blackout state, and it is *not* the ordinary night-time state: night in the overworld with no light source, the Underworld at any hour, and a dark interior all run at the full-dark threshold of two, which lights a three-by-three neighbourhood. Zero is reached only through the void-tile override described in `systems/lighting.md` Section 7.
- **Threshold positive.** The producer hands the grid over to the visibility carve helper (Section 5) along with the player's local-window position and the threshold value. The helper starts from the centre cell and expands through candidate neighbours, writing tile bytes for cells it resolves as visible and writing a working all-zero marker for cells it has considered but not resolved as visible. After the helper returns, a post-pass walks the grid and converts every `0x00` byte back to `0xFF` (the hidden marker), so unresolved cells do not trigger the cheap terrain-refill path on the next frame.
- **Threshold negative.** The producer takes a full-fill path: every cell is populated from the world map directly, without any visibility carve or distance gate. The grid ends up holding exactly the underlying terrain in every cell, no fog applied. This branch is structurally unreachable in the shipped 2D pipeline, because the redraw orchestrator zero-extends the unsigned lighting byte before the call and can therefore never present a negative value. A compatibility implementation can preserve the branch without treating it as ordinary gameplay visibility.

**Stage 3 — return.** The producer does not clear or flip any flags itself; the redraw orchestrator handles the dirty-flag reset.

End-of-stage state, per case:

```text
positive threshold:  grid cells resolved by the carve = real tile bytes;
                     grid cells not resolved by the carve = 0xFF.

zero threshold:      every cell = 0xFF, the player's own cell included.

negative threshold:  every cell = real tile byte (no fog). Unreachable in the
                     shipped 2D pipeline.
```

The grid bytes leaving the producer are then handed to the fog post-pass
(Section 7) for edge refinement and active-object compositing.

## 5. The Visibility Carve

The visibility carve helper is called by the producer for the positive-light
case. It is queue-based rather than a simple "cast one independent ray to every
cell" algorithm.

The helper receives the grid base address, row stride, centre-cell position,
world-coordinate origin, and the lighting threshold value. It seeds a work queue
with the player's centre cell, writes that centre cell from the world-tile
getter, then repeatedly pops a coordinate and examines its eight neighbours in a
fixed ring order:

The neighbour expansion order is west, southwest, south, southeast, east,
northeast, north, northwest.

For each candidate neighbour, the helper rejects out-of-window coordinates,
uses the zero byte as an in-progress/already-considered marker, reads the
candidate world tile, computes squared distance from the centre, and applies
its propagation tests. It may then write the candidate tile, leave a zero
working marker for the producer's post-pass to collapse to hidden, or enqueue
the candidate for further expansion.

The settled external contract is:

- The player's centre cell is always seeded first, **before any distance
  comparison**, and is therefore visible for every positive threshold. Nothing
  gates the seed on the threshold value.
- The helper expands through neighbouring cells from the centre rather than
  scanning the viewport row by row.
- The helper uses the same squared-distance primitive as the fog post-pass for
  centre-relative distance checks: the folded lookup that returns exactly
  `dx * dx + dy * dy` for offsets in minus five to plus five, with values from
  zero at the centre to fifty at the corners.
- **The caller-provided lighting value is the squared-distance threshold
  itself.** A cell is inside the threshold when its centre distance is **less
  than or equal to** that value. The inclusive sense is deliberate and is the
  only adjustment the value receives anywhere between the lighting subsystem and
  this test: no squaring, no scaling, no shifting, no table mapping.
- This comparison and the gate described in Section 3 are **the same single
  comparison**, and it is the only place in the engine that uses the lighting
  value as a distance threshold. Nothing downstream re-applies it: the fog
  refinement pass of Section 7 uses its own fixed distance, and the
  active-object compositor of Section 8 reads only the finished grid. The one
  other site that reads the lighting value at all is the night-time beacon of
  Section 12.6, which uses it as a day/night gate rather than as a distance.
- A cell that is inside the threshold is painted with its world tile **whether
  or not that tile blocks sight**. Opacity is a propagation predicate, not a
  visibility predicate for the blocker's own cell.
- A zero byte written by this helper is not a renderer-visible result. The
  producer converts helper-written zeros back to the hidden marker before the
  fog post-pass runs.

The propagation predicate is tile-id based but separate from movement
passability. Ordinary tiles propagate the carve unless they are in the
visibility propagation-blocker set in Section 6. Five special-case tile ids use
a stricter rule: they propagate only when they are orthogonally adjacent to the
centre cell, which is the case where the squared-distance helper returns `1`.

Inside the lighting threshold, accepted candidates are written as their world
tile. **Cells that fail the distance gate are not automatically dark.** The
helper consults the separate local-light mask (Section 12) and applies a rule
that depends on whether the candidate's terrain propagates sight:

- A **sight-propagating** candidate beyond the threshold is painted with its
  world tile when its own local-light mask cell is nonzero; when the mask cell
  is zero it is left as a zero working marker that the producer later collapses
  to hidden. Either way **the candidate is still enqueued**, so the carve
  continues expanding through unlit transparent ground and can reach lit ground
  further out.
- A **sight-blocking** candidate beyond the threshold is painted only when the
  cell the carve arrived from was itself visible *and* both that parent cell and
  the candidate have nonzero local-light mask coverage. Otherwise it is hidden.
  In neither case does the carve expand past it.

This rule is what makes torch-lit streets, lamp-lit rooms and lighthouse beams
visible at night from outside the ambient threshold. A port that treats
"outside the threshold" as "hidden" will black out lit areas the original shows.

Do not implement this as a Bresenham line caster, a shadow-caster, or a
movement-passability rule. It is a centre-out neighbour carve with a separate
propagation-blocker set and local-light mask.

Section 12.2 specifies the companion rule for the mask itself: each individual
local light source contributes through the same inclusive squared-distance test
with a **fixed threshold of ten**, giving a thirty-seven-cell disc that reaches
at most three cells along a row or column, and overlapping sources union.

## 6. Sight-affecting tiles

Whether a tile affects sight is a property of the tile id, but the visibility
rule is its own classifier. It is not derived from movement passability, LOOK
text, or the tile's broad visual family.

The nineteen blocking ids and the five adjacent-only ids are listed below with
the names the shipped description table (`formats/look2-dat.md`) gives them.
Every one of them is **terrain or a fixture** — vegetation, rock, walls, doors
and windows, a fireplace, and the void tile. They are ordered by semantic family
rather than by their resident table order.

| Tile identity | Visibility propagation rule |
|---------------|----------------------------|
| Trees `0x09`, tropical forest `0x0A` | Stop propagation. |
| Mountains `0x0C`, high peaks `0x0D` | Stop propagation. |
| Wall variants `0x4D..0x4F` (a stone wall, a wall with a nick, a wall) | Stop propagation. |
| Window shelf `0x5A` | Stops propagation. |
| Odd door `0x97` | Stops propagation. |
| Wooden door `0xB8`, locked door `0xB9` | Stop propagation. |
| Fireplace `0xBC` | Stops propagation. It is also a local-light source (Section 12.3): a tile can both stop the carve and light its neighbourhood. |
| Unnamed fixtures `0xD0..0xD3` (shared placeholder description) | Stop propagation. |
| Sign/poster tile `0xF8` (shared placeholder description) | Stops propagation. |
| Wall `0xFE`, and the void tile `0xFF` ("darkness!") | Stop propagation. |
| Arrow slit `0x4A`, window `0x4B` | Propagate only when orthogonally adjacent to the centre cell. |
| Odd door `0x98` | Propagates only when orthogonally adjacent to the centre cell. |
| Wooden door with a window `0xBA`, locked door with a window `0xBB` | Propagate only when orthogonally adjacent to the centre cell. |

Read as a set, the rule is legible: solid vegetation, rock, walls and closed
doors block sight outright, while the four openings you can only see through
from immediately in front — an arrow slit, a window, and the two windowed doors —
propagate exactly one cell.

**Correction.** Earlier revisions of this table named these ids after monsters:
`0x97` a Bat frame, `0xB8..0xBB` Gargoyle frames, `0xBC` an Insect Swarm frame,
`0xD0..0xD3` Headless frames, `0xF8` a Rot Worm frame, `0xFE..0xFF` Shadow Lord
frames, `0x4A..0x4B` and `0x4D..0x4F` bookshelf/dresser/vanity/trunk variants,
and `0x5A` a sign post. All of those names are **withdrawn**. They were read out
of the nominal index ranges of `catalogs/tile-catalog.md` Sections 2 and 3.
That catalog's Section 3.1 precedence rule marks those range names as working
hypotheses for **every** band that has not been confirmed index by index — the
low furniture bands at decimal 74..79 exactly as much as the bands above index
128 — and a confirmation from the shipped description table or the shipped art
wins over the range name in all of them. These names also conflicted with ids
the same catalog has confirmed from the shipped description table, and that
catalog's 74..79 row has since been corrected to match. The carve reads a **terrain-layer byte in `0..255`**; an
actor's stored byte reaches the catalogue only after the renderer adds `256`
(`catalogs/tile-catalog.md` Section 3.1), so no monster frame can appear in this
list at all. The **tile-id membership of both groups is unchanged** — only the
names were wrong.

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

The refinement uses a small squared-distance lookup centred on viewport cell `(5, 5)`, distinct from the lighting threshold and never derived from it. The helper folds each coordinate around the centre (`folded = min(coord, 10 - coord)`), indexes a resident 6×6 table, and returns `(5 - folded_x)^2 + (5 - folded_y)^2`. The post-pass compares that squared distance to the literal threshold `5` and toggles two specific marker bytes:

- A cell currently holding the *clear-visible* marker (`0xDD`) whose squared distance is greater than `5` is downgraded to the *dim-periphery* marker (`0x1C`). It is still visible, but the renderer will dim it.
- A cell currently holding the *dim-periphery* marker (`0x1C`) whose squared distance is at most `5` is upgraded back to the *clear-visible* marker (`0xDD`).

This is not a five-cell radius. `5` is a squared distance on exactly the same scale as the lighting threshold of Section 3, applied with the same inclusive sense, and the clear-marker core is therefore **twenty-one cells**: the centre cell, its eight neighbours, the four cells two tiles away on a row or column, and the eight cells at offsets `(±1, ±2)` and `(±2, ±1)`. Marker cells farther out in the eleven-by-eleven viewport are dimmed. The lookup is reflection-symmetric across the viewport centre and avoids computing a square root at runtime.

This refinement is a **cosmetic near/far variant selector**: it swaps between the clear and dim renderer markers and never changes which cells are visible. It is also **independent of the lighting threshold** — the threshold value is never read here, and the fixed `5` never varies with time of day, torch, or spell. The producer decides which terrain cells are visible at all; the post-pass only adjusts cells already carrying the two renderer marker bytes. It is a no-op for grids where the visibility carve helper has emitted real tile bytes instead of `0xDD` / `0x1C` markers.

The refinement only toggles between the two marker bytes; cells holding any other value (a real tile byte, the hidden marker, the use-companion marker, the already-rendered marker) are left unchanged. The pass is a no-op for grids where the visibility carve helper has not emitted those markers — most ordinary frames have a visible-region full of *real tile bytes* rather than markers, so the toggle does nothing. The markers are written only by the active-object compositor (Section 8) and by certain mode-entry handlers; the refinement is what keeps them consistent with the fixed near/far distance.

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

The cheap path *does not* recompute the visibility carve, does not consult the lighting threshold, and does not touch fog markers. It is a pure terrain-refill, intended to keep the screen showing the current map without redoing the visibility math. The fog post-pass and active-object compositor still run after the cheap path each frame, so on-screen sprites and dim-periphery markers stay accurate.

The cost of the cheap path is roughly one tile-fetch per consumed cell — a small fraction of the producer's full-grid visibility carve. The engine is built around this asymmetry: the producer is an expensive once-per-event recompute, the cheap path is a per-frame topping-up.

## 11. Mode differences

**Overworld and underworld.** Use the full producer pipeline as described above. The active map buffer is the streamed 2×2 chunk window. The producer is called when the visibility-dirty flag is set, which happens on every player step (the step handler dirties the flag), on lighting changes (the per-turn cleanup dirties the flag if the daylight value changed), and when the night-time beacon of Section 12.6 changes a lit cell.

**Town, dwelling, castle, keep.** Use the same producer pipeline with the active map buffer interpreted as a single 32×32 grid (no chunk streaming). These scenes read **the same single lighting-threshold value** the outdoor world reads, produced by the same per-turn computation; there is no per-location ambient override and no second lighting source anywhere in the 2D modes. Interiors that appear lit at night are lit by the local-light mask of Section 12 (candles, lamps, hearths), not by a different ambient value. Two upstream rules in `systems/lighting.md` Section 3 are the only exceptions, and neither is a per-location table: scene twenty-five, Ararat, is pinned to the full-dark value regardless of the hour, and a party Z value with its high bit set — a below-entry (basement) floor, as well as the Underworld plane outdoors — is pinned the same way.

**Dungeon-explore.** Uses a different visibility model entirely. There is no eleven-by-eleven viewport grid; the dungeon view is a first-person three-dimensional projection drawn by a dedicated renderer. The light gate is binary: if neither torch nor light-spell counter is active, the panel is black; otherwise the renderer walks the current eight-by-eight dungeon geometry until blocked. Live dungeon-cell bytes do not store persistent visibility memory, and V-View's visited map is temporary scratch state owned by the dungeon view overlay.

**Combat.** Uses a fully materialised terrain grid in a separate buffer, pre-composited by the combat setup helper. The combat producer initialises this buffer to the hidden marker and fills it through the same visibility carve helper family the 2D-scene producer uses, but combat does not consult the global lighting threshold — combat scenes have their own lighting context, and the encoding does not include fog markers. The post-pass (fog refinement plus active-object compositing) skips combat scenes entirely; combat manages active-object compositing through its own round walker.

The mode boundary is enforced by the redraw orchestrator: it inspects the scene byte before choosing a path. Combat-class scenes use the high-range reader branch, and the traced gameplay writer uses `0xFF` for that state. That branch takes a *blat-copy* path that copies the pre-composited combat terrain grid byte-for-byte into the visibility grid, then runs the renderer. The producer is not called.

## 12. Local Light Sources

A handful of map and runtime tiles can make nearby cells visible independently
of the ambient lighting threshold. The mechanism is a separate local-light
mask, not a rewrite of the one lighting-threshold byte.

### 12.1 The refresh pass

1. Clear a thirty-two by thirty-two mask to the hidden sentinel.
2. Scan the active thirty-two by thirty-two map window for cells whose tile id
   is in the local-light source set, recording each hit as a source and writing
   its tile byte into the corresponding mask cell.
3. For each recorded source, in scan order:
   a. Clear a fresh eleven-by-eleven per-source visited grid.
   b. Run the **same centre-out queue carve** the ordinary visibility producer
      uses (Section 5), centred on the source, writing into the thirty-two by
      thirty-two mask with a thirty-two-byte row stride and an output origin
      five cells up and five cells left of the source, so the source sits at
      the centre of its own eleven-by-eleven carve box. Candidates whose output
      row would fall outside the thirty-two-row window are rejected.
4. Convert every mask cell still holding the hidden sentinel to zero. Carved
   and source cells keep their nonzero tile bytes.

Sources do not interfere: each carve writes into the same mask, so the lit set
is the union over all sources.

### 12.2 Source radius

The per-source carve is invoked with a light value of **ten**, and that value
is a **squared-distance threshold**, exactly as it is for the ordinary producer
in Section 5. A cell is inside a source's light when

```text
dx * dx + dy * dy <= 10
```

where `dx` and `dy` are the cell's offsets from the source. That is a Euclidean
disc of radius the square root of ten, roughly `3.16`. Concretely it covers
thirty-seven cells: every offset with `|dx| <= 3` and `|dy| <= 3` **except** the
twelve corner-ish offsets `(+-3, +-3)`, `(+-3, +-2)`, and `(+-2, +-3)`.

Two earlier statements about this radius are retracted. It is **not** Chebyshev
distance, it is **not** a solid seven-by-seven square, and the threshold value
is **not** three. The eleven-by-eleven per-source visited grid is larger than
the lit disc; it is bookkeeping for the queue carve, not the radius.

Two rules complete the shape.

**Inside the disc**, a reached cell is painted with its real tile byte even when
that tile is a propagation blocker. The blocker stops the *expansion*, not the
lighting of its own cell, so a wall segment facing a torch is lit while the
cells behind it are not. This is why a source does not light through a wall
even though its disc would reach past one.

**Outside the disc**, the local-light carve simply stops. A candidate whose
squared distance exceeds the threshold is neither painted nor expanded further,
so the flood never leaves the disc even though the per-source visited grid is
larger. This differs from the ordinary producer's carve, which does keep
expanding through dark space beyond its own threshold and consults this mask to
decide what to paint out there (Section 5). Do not carry that behaviour over
into the local-light pass; the mask is write-only while it is being built.

The mask is binary in effect — a cell is either locally lit or not. There is no
graduated brightness inside the disc; ambient brightness is owned by
`systems/lighting.md`.

### 12.3 Source tile ids

The candidate source ids proven by the resident lookup are `0xB0..0xB3`,
`0xBC..0xBF`, `0xDC`, and `0xDE`. The shipped description table names them, and
the set is exactly what one would expect of a light-source list: a flickering
torch `0xB0` and `0xB1`, a hot brazier `0xB2`, meat roasting on a spit `0xB3`, a
fireplace `0xBC`, a street lamp `0xBD`, a candelabrum `0xBE`, a hot stove
`0xBF`, a moon gate `0xDC`, and a shrine flame `0xDE`. Note that `0xBC` is
also a propagation blocker (Section 6): a tile can both stop the carve and act
as a light source.

### 12.4 When the pass runs, and in what order

The refresh is **not** a per-frame or per-turn pass. It has exactly three
trigger points:

- the Moonstone live-gate terrain refresh, after it rewrites eligible saved
  Moonstone slot cells;
- combat entry, after combat setup work;
- combat exit, after non-combat mode state is restored.

Between triggers the mask persists unchanged and the visibility producer keeps
consulting it. The combat entry and exit rebuilds exist because the same
scratch region is reused as combat terrain storage while combat is running, so
the mask must be re-established on both sides of a combat.

Ordering inside a non-combat redraw is: **local-light refresh first, beacon
stamps second, visibility carve third.** The producer consults the finished
mask; the mask is not produced from the producer's output. An earlier statement
that the local-light pass runs *after* the ordinary visibility producer and
before the renderer compositors is retracted — it is backwards.

The **night-time beacon** of Section 12.6 is the mask's one other non-combat
writer: it lights and clears individual cells of the same thirty-two-by-
thirty-two mask and sets the visibility-dirty flag. Those writes are transient
visibility state, not durable map edits and not replacements for the ambient
lighting-threshold byte. An earlier revision of this section called that writer a
"moongate animator" stamping moongate frames; that attribution is withdrawn in
full — it is a light source, it never draws a gate, and natural moongates are
ordinary live terrain owned by `systems/overworld.md`.

### 12.5 Dungeon mode

Nothing in the traced trigger list is scene-specific, so this specification
makes no claim that the pass is suppressed in dungeon mode. An earlier
statement that "the local-light pass does not run in dungeon mode" is
retracted as untraced. What is safe to implement: the mask is rebuilt only at
the three trigger points above, and the producer reads whatever the mask
currently holds.

Implementations should keep this as an isolated local-light resource. It is
part of visibility propagation state, not a permanent mutation of map bytes and
not a replacement for the ambient daylight / torch / spell counters.

### 12.6 Night-time rotating beacons

Separately from the disc-shaped sources of Sections 12.1 to 12.3, the engine
runs one **rotating beam** that writes into the same local-light mask. It is a
distinct mechanism with its own state and its own cadence, and it is the true
owner of the small resident scratch block that earlier revisions of the spec
set attributed to a moongate animator.

**Sources.** The beacon has at most two source positions, harvested by whichever
map loader is active rather than by the light pass itself:

- **Outdoors**, the chunk loader scans each freshly loaded thirty-two-by-
  thirty-two window for the **lighthouse** tile and records the first hit as the
  single beacon position, or records a "no beacon" sentinel when the window
  holds none. It never fills the second position. The four lighthouses on the
  Britannia surface are listed in `catalogs/gazetteer.md` Section 8.1; the
  Underworld map contains none, so the outdoor beacon is a surface-only effect.
- **Inside a location**, the map setup clears both positions and then records up
  to **two** hits on the **bright-light** tile.
- **Combat entry** switches the beacon off outright.

The shipped data image starts with both positions at the "no beacon" sentinel,
so nothing is lit until a loader finds a source.

**Light gate.** The very first thing the pass does is compare the ambient
lighting value against the full-daylight value of fifty. It runs only while the
value is **strictly below** fifty — that is, from the first step of the dusk ramp
until the last step of the dawn ramp. At or above fifty the pass clears its
state and draws nothing, and the rotation restarts from its initial bearing the
next time darkness falls. This comparison is the **only** read of the lighting
value anywhere outside the visibility carve of Section 5, and it is a day/night
test, not a distance threshold (`systems/lighting.md` Section 7.2). An earlier
revision of this spec set had this gate inverted, describing a daylight-only
effect; that is withdrawn.

**Beam shape.** The beam is a cone of lit cells reaching up to seven tiles from
the source. There are sixteen bearings evenly spaced around the compass:
bearing one points due north, five due east, nine due south, thirteen due west,
four bearings fall on the diagonals, and the remaining eight sit halfway between
those. Each bearing is a fixed set of at most sixteen cell offsets relative to
the source, so a bearing is a stencil, not a computed sweep.

**Cadence.** Three adjacent bearings are lit at any moment — a cone roughly
three sixteenths of the compass wide, a little under seventy degrees. Once per
world turn the trailing bearing is cleared and the next leading bearing is lit,
so the cone advances one sixteenth of a revolution per turn and completes a full
revolution every sixteen turns. The bearing counter wraps at sixteen.

**Effect.** Lit cells are written straight into the local-light mask, so they
become visible exactly as any other locally lit cell does, and the pass sets the
visibility-dirty flag when it changes anything. Apart from the day/night gate
above, the beacon never touches the ambient lighting value — it never writes it
and never uses it as a distance — and it does not create an active object or
modify map data.

An implementation that omits the beacon loses only night-time illumination
around lighthouses and indoor lamps; one that draws a moongate here is
modelling something the original does not do.

## 13. Visibility Boundaries And Remaining Parity Work

The visibility-grid contract is complete at gameplay depth: producer fill
states, centre-out carve behavior, blocker rules, marker refinement,
active-object compositing, renderer/effect read contract, cheap terrain refill,
mode boundaries, local-light mask ownership, beacon-mask ordering, and the
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
  delegation, post-pass), the negative-light full-fill path, and the branching
  on the lighting value's sign — `u5-decomp/functions/ULTIMA_EXE/0x5D0A_visibility_producer.md`.
- Source provenance: the finding that the lighting byte is the squared-distance
  threshold itself rather than a sight radius, the unaltered four-hop chain of
  custody from the per-turn ambient computation to the carve's comparison, the
  inclusive sense of that comparison, the per-threshold cell counts and reach
  values, the unconditional centre-cell seed, the local-light rule for
  candidates beyond the threshold, the fixed near/far distance of the fog
  refinement and its twenty-one-cell core, the zero-extension that makes the
  negative-value branch unreachable, and the whole-binary census showing a
  single *distance-threshold* consumer of the lighting value, alongside the
  night-time beacon's day/night read of the same byte — derived from private
  analysis note
  `u5-decomp/notes/light_threshold_semantics_2026-08-22.md`. That note also
  withdraws the "light radius in tiles" and ray-walk descriptions carried by the
  older private lighting/visibility system trace.
- The queue-based visibility carve, propagation-blocker set, and special-case
  adjacent-only propagation rule
  — `u5-decomp/functions/ULTIMA_EXE/0x5A28_visibility_buffer_setup.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x5DFE_visibility_tile_class.md`.
- Source provenance: the names of the nineteen propagation blockers and the five
  adjacent-only ids in Section 6, and of the ten local-light source ids in
  Section 12.3, were re-derived by decoding the shipped description table with
  the container rules in `u5-spec/formats/look2-dat.md`. That decode also
  withdraws the monster/furniture names those two lists previously carried; the
  id membership of every list is unchanged.
- The local-light mask refresh pass, source-candidate lookup, per-source carve
  radius, its squared-distance semantics, the three trigger points, and the
  final untouched-cell zeroing —
  `u5-decomp/functions/ULTIMA_EXE/0x5E4A_light_radius_lookup.md` and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 4.
- The carve's two caller modes, the per-source visited grid, the stop-at-the-
  disc-boundary rule for local light, the fact that a blocker cell inside the
  disc is itself lit, and the folded squared-distance lookup being exactly
  `dx * dx + dy * dy` - `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md`
  sections 6.2 through 6.4, cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/0x5A28_visibility_buffer_setup.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x5DFE_visibility_tile_class.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x6FF0_range_to_player.md`.
- The Moonstone-slot live-gate refresh caller that rebuilds the local-light
  mask after in-scene tile rewrites -
  `u5-decomp/functions/ULTIMA_EXE/0x475A_npc_schedule_tick.md`.
- The night-time rotating beacon, its source harvest, its inverted light gate,
  its sixteen-bearing stencil plate and its per-turn cadence —
  `u5-decomp/functions/ULTIMA_EXE/0x7040_light_beacon_stamp.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x70A6_moongate_or_event.md`.
- Source provenance: the identification of that scratch block as beacon state
  rather than moongate state, the complete writer census behind it, and the
  correction of the light gate are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- The visibility-grid writer scan proving the renderer is read-only on the
  eleven-by-eleven grid and that zero cells are compositor-owned -
  `u5-decomp/notes/visibility_grid_zeroing_2026-05-08.md`.
- The fog post-pass — squared-distance marker toggling, active-object compositing, and compositor-owned visibility-grid zeroing for cells that need terrain refetch — `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md` and `u5-decomp/notes/visibility_grid_zeroing_2026-05-08.md`.
- The 6×6 folded squared-distance helper used by the fog post-pass — `u5-decomp/functions/ULTIMA_EXE/0x6FF0_range_to_player.md`. Combat AI target scoring uses a separate computed range primitive covered in `systems/combat.md`.
- The redraw orchestrator that calls the producer on dirty frames, takes the cheap path on clean frames, blat-copies the combat terrain on combat frames, and clears the dirty flag after the producer returns — `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The world-tile getter that dispatches between combat, overworld 2×2 chunk window, and town/dungeon-explore single-grid buffers, including the out-of-bounds sentinel — `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The default active-object compositor helper and its 0..3 variant selector -
  `u5-decomp/functions/ULTIMA_EXE/0x51B8_monster_spawn_table.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x51A0_combat_class_roll.md`. Both filenames
  predate their naming corrections: neither routine spawns monsters and neither
  is combat-scoped or class-related; the second returns the variant index used
  by the first.
- The cross-overlay alias and callsite census for the same world-tile getter -- `u5-decomp/functions/ULTIMA_EXE/0xC232_tile_at_world_coord.md`.
- The overworld map family's chunk layout (BRIT.DAT sparse, UNDER.DAT dense), the four-class location-DAT format, and the combat arena format that combat pre-composites — `u5-decomp/formats/maps.md`.
- The resident data segment's fixed locations for the visibility grid, the terrain band, and the per-cell scrap regions — `u5-decomp/formats/data-ovl.md`.
- The visibility-system analysis notebook from the companion-app project, used as a starting reference for buffer addresses, scene-to-routine map, and the asynchronous-read race observations — `ninth-virtue/docs/visibility-re.md:11-352`.
