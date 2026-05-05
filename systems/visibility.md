# Visibility

## 1. Overview

The visibility system answers the rendering pipeline's central question: *which of the cells around the player should the screen actually show this frame, and how?* Ultima V's two-dimensional scenes — overworld, underworld, towns, dwellings, castles, and keeps — all draw the world through an eleven-by-eleven viewport centred on the party. For each of those one hundred twenty-one cells, the engine decides one of three things on every redraw: the cell is fully visible (paint the underlying tile), the cell is dim periphery (paint the tile with a dimmed-edge marker), or the cell is hidden (paint nothing — the cell is dark, blocked, or outside the active light radius).

The decision is made by a producer that runs once per redraw, walks a line of sight from the player to each cell, takes account of the current light radius, and writes a one-byte verdict into a fixed-size scratch grid in the data segment. A second pass — the fog post-pass — refines the edges of the visible region and stamps active objects (NPCs, monsters, vehicles, the player avatar) into the same grid on top of the terrain. The renderer then walks the grid one cell at a time, consulting both the visibility verdict and a parallel terrain band, and paints the corresponding tile to the screen.

The producer is called only when the visibility state is *dirty*. Most frames, only the player has moved by zero cells and the lighting hasn't changed; in that case the engine takes a much cheaper path that lazily refills any cells the renderer "consumed" on the previous frame, leaving the dirty cells alone. A dirty flag in the resident data segment tells the per-frame redraw orchestrator which path to take.

This spec describes the viewport grid's shape, the inputs the producer reads, the line-of-sight algorithm, the fog-edge refinement, the active-object compositing pass, and the renderer's contract for consuming the result. The dungeon and combat modes, which use different visibility models entirely, are described briefly at the end.

## 2. The viewport grid

The visibility grid is a rectangular block of bytes in the resident data segment, sized for the on-screen viewport. The active region is eleven rows of eleven columns — one hundred twenty-one cells — laid out row-major. Each row is *thirty-two bytes wide*, however; only the first eleven bytes per row are used, and the remaining twenty-one bytes of each row are scratch space that other passes (the active-object compositor, the renderer's special-tile fixups) read and write.

The layout looks like this, with columns zero through ten as the active window and the player at the centre:

```
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

The thirty-two-byte stride lets the engine address a row by shifting the row index left by five — much faster than a multiply by eleven on the target processor. The trailing twenty-one bytes per row are not touched by the producer's main pass; they are used opportunistically by callees that need scratch within the loop and by the renderer for per-row staging.

The grid coexists with a *terrain band* of identical row count but a different stride. The terrain band uses sixteen bytes per row, also row-major over eleven rows, holding the underlying terrain tile bytes that the renderer falls back to when the visibility grid emits a "use companion buffer" marker. The two grids are fed by different producers (the visibility grid by the per-frame redraw, the terrain band by mode-entry and scroll-recentre handlers) and consumed together by the renderer; their contents are kept in lockstep by mode-entry initialisation.

Each byte in the visibility grid encodes one of several things at end-of-frame:

| Byte value      | Meaning                                                              |
|-----------------|----------------------------------------------------------------------|
| `0xFF`          | Hidden — fully obscured. The cell is outside the light radius, blocked by a sight-blocker, or off-map. The renderer paints nothing here; the previous frame's pixels stay. |
| `0x00`          | "Use companion buffer." The cell is visible but the terrain band holds the tile to paint. Set by the active-object compositor for water-bound and water-creature classes. |
| `0xDD`          | Clear visible (in-radius). A marker indicating "this cell is fully lit." The renderer treats it as a terrain-tile-from-companion-buffer cue with full brightness. |
| `0x1C`          | Dim periphery. Same as `0xDD` but the cell is on the visibility-radius boundary; the renderer dims the painted tile. |
| `0x87`          | "Already rendered." A guard the active-object compositor checks to avoid double-stamping. Higher-priority sprite already in this cell. |
| any other byte  | A direct tile id. The renderer paints this tile in this cell. Used for active-object stamps and for the negative-light full-fill path. |

The exact handling of `0x00`, `0xDC`, and `0xDD` is the renderer's contract; the producer and post-pass describe their own writes only in those terms.

## 3. Inputs

The producer reads several pieces of resident state on every dirty-frame call.

**Player position.** Two bytes in the data segment hold the player's world tile coordinates — column and row — for whatever map family the current scene uses. The producer subtracts the *scroll origin* (Section 4) to get a player position relative to the active map buffer, and offsets that by minus five so the upper-left corner of the eleven-by-eleven window sits at the right place in world space.

**Scroll origin.** Two bytes hold the column and row of the upper-left of the currently-loaded map chunk window in the overworld and underworld scenes. Town and dungeon-explore scenes set the scroll origin to zero (the active buffer is the entire 32×32 location grid, not a streamed chunk window).

**Scene identity.** A single byte distinguishes between mode families: zero for the overworld stream, one through some dozens for towns / dwellings / castles / keeps, a higher range for dungeon-explore, and an even higher range (at and above the high bit set) for combat. The producer mostly does not care which 2D scene type it is in — the line-of-sight algorithm and the grid format are identical for all 2D scenes — but the choice of map buffer (Section 4) does depend on scene.

**Light radius.** A single byte that the lighting subsystem maintains, holding the player's current effective sight radius. The radius is large during outdoor daylight, smaller at night, smaller still in dungeons and at indoor scenes after dark, and clamped upward by a torch or a light spell. The producer treats the radius as a *signed* quantity:

| Sign            | Producer behaviour                                                  |
|-----------------|---------------------------------------------------------------------|
| Positive        | Normal case — run line-of-sight, clamp by the radius.               |
| Zero            | Total darkness — leave the grid fully obscured. The player sees nothing.   |
| Negative        | Full-fill path — populate every cell from the world map regardless of LOS or radius. Used for special "free-look" scenes. |

The lighting subsystem owns the rules that decide what value goes into this byte; from the producer's point of view, the byte is read once per frame and passed down to the line-of-sight helper.

**Visibility-dirty flag.** A single byte that other systems set when the visibility state must be recomputed: the player moved, the lighting changed, a moongate appeared, a new scene was entered. The redraw orchestrator reads this byte to choose between the expensive path (run the producer) and the cheap path (lazy refill of consumed cells). The producer's caller clears the flag immediately after the producer returns.

**Active map buffer.** The world tiles that line of sight steps through come from one of three buffers, selected by scene:

- **Overworld and underworld.** A one-kilobyte buffer holding the active 2×2 chunk window — four sixteen-by-sixteen chunks at adjacent offsets. The world is streamed: as the player approaches the edge of the loaded window, scene transitions reload chunks and shift the scroll origin.
- **Town / dwelling / castle / keep / dungeon-explore.** The same one-kilobyte buffer, interpreted as a single 32×32 grid for the entire location. The scroll origin is zero.
- **Combat.** A separate scratch grid (Section 11), pre-composited by the combat setup helper. The 2D-scene producer is not used in combat.

A leaf helper, the *world-tile getter*, encapsulates the three branches: given a tile column and row it returns a pointer to the byte that represents that tile in whichever buffer is currently active. Out-of-range queries to the location/dungeon-explore buffer return a sentinel byte address (a fixed location whose contents act as a "you walked off the map" tile).

## 4. The producer's three stages

The producer runs in three stages.

**Stage 1 — paint everything obscured.** The eleven-by-eleven active window is filled with the hidden marker (`0xFF`). Each row writes eleven `0xFF` bytes into the first eleven columns; the remaining twenty-one bytes per row are left untouched. After this stage, the entire grid says "nothing is visible."

**Stage 2 — branch on the light-radius sign.**

- **Light radius zero.** The producer skips both the line-of-sight helper and the full-fill path. The grid stays fully obscured. This is the "pitch dark" case: night in the overworld with no torch, an unlit dungeon level, an extinguished town scene.
- **Light radius positive.** The producer hands the grid over to the line-of-sight helper (Section 5) along with the player's local-window position and the radius. The helper carves out visible cells, writing tile bytes for cells that are both within the radius and have an unblocked sight path, and writing a "considered but blocked" marker (the all-zero byte) for cells on the radius but blocked by terrain. After the helper returns, a post-pass walks the grid and converts every `0x00` byte back to `0xFF` (the hidden marker), so the only difference between "blocked" and "outside radius" disappears at end-of-stage.
- **Light radius negative.** The producer takes a debug-style full-fill path: every cell is populated from the world map directly, without any line-of-sight test or radius clamp. The grid ends up holding exactly the underlying terrain in every cell, no fog applied. This path is used for special viewing modes; ordinary play does not exercise it.

**Stage 3 — return.** The producer does not clear or flip any flags itself; the redraw orchestrator handles the dirty-flag reset.

End-of-stage state, per case:

```
positive light:  grid cells inside radius and unblocked = real tile bytes;
                 grid cells on the radius edge but blocked = 0xFF;
                 grid cells outside the radius = 0xFF.

zero light:      every cell = 0xFF.

negative light:  every cell = real tile byte (no fog).
```

The grid bytes leaving the producer are then handed to the fog post-pass (Section 6) for edge refinement and active-object compositing.

## 5. The line-of-sight algorithm

The line-of-sight helper is a single helper called by the producer for the positive-light case. It walks the eleven-by-eleven viewport, and for each cell decides whether the player has unobstructed sight to that cell.

The contract: the helper receives the grid base address, the row stride, the player's local-window centre coordinates, the light radius, and a few small constants. For each cell of the grid in turn, it walks a short *sight ray* from the player's centre cell to the candidate cell, querying the world-tile getter at each step. If any step lands on a sight-blocking tile, the ray is cut short and the candidate cell is marked obscured. Otherwise, the candidate cell receives the underlying terrain byte and is considered visible.

The exact stepping shape (whether it is a Bresenham-style integer-rasterised line, a quadrant-symmetric flood with shadow-casting, or a precomputed sight-ray table) is not nailed down by static analysis alone — see Section 13. What is settled is the helper's *external* behaviour:

- **Sight rays start at the player's centre cell.** No diagonal-cell-permitting fudges around the player's own position; the player always sees their own cell.
- **The radius gate is applied before the ray walks.** Cells whose Chebyshev or Euclidean distance from the player exceeds the radius are immediately marked obscured without a sight-ray walk.
- **The first blocking tile cuts the ray.** Cells "behind" a blocker — along the same ray, further from the player — are marked obscured. Cells *at* the blocker are also obscured (the renderer paints the blocker's tile from the active-object compositor or from a separate terrain pass; the visibility grid says "you can't see past here").
- **Two end-state markers.** Cells the helper walks all the way to without finding a blocker are written with the underlying terrain byte. Cells the helper considers but blocks are written with the all-zero byte (a "visited but blocked" tag). The producer's post-pass then converts those zeros back to the hidden marker, so by the time the fog post-pass runs the grid contains real tile bytes for visible cells and `0xFF` for everything else.

The split between "real tile" and "all-zero" matters because the engine needs to distinguish the two during the carve, even though they end up identical to the renderer. The all-zero placeholder is a working state inside the helper; it is not part of the renderer's contract.

## 6. Sight-blocking tiles

Whether a tile blocks sight is a property of the tile id, looked up against the engine's per-tile attribute table. Roughly:

| Tile family                         | Blocks sight? |
|-------------------------------------|---------------|
| Open ground (grass, sand, paths)    | No            |
| Floor (wood, stone, carpet)         | No            |
| Water (deep, river, swamp)          | No            |
| Forest interior (deep woods)        | Yes           |
| Mountain                            | Yes           |
| Wall, door (closed)                 | Yes           |
| Door (open)                         | No            |
| Pillar, large furniture, statue     | Yes           |
| Hedge, dense vegetation             | Yes           |
| Cave wall                           | Yes           |
| Rubble, low debris                  | No            |

The exact table — the precise tile-id cutoffs that say "indices A through B block sight" — is part of the per-tile-class attribute data, which is shared with the collision system, the active-object compositor, and the path-finding code. From the visibility system's point of view, the contract is: given a tile id, ask the attribute table whether it blocks sight, and use that answer to terminate or continue the sight ray.

Active-object slots that block sight (boats, large creatures, NPCs in the way) act as dynamic occluders. The line-of-sight helper does not consult the active-object table directly; instead, the active-object compositor (Section 8) writes obstructing slots into the grid *before* the producer runs in some cases, and the player's existing slot-zero registration as a sight blocker is encoded into the producer's algorithm via the player-centred starting point. The full set of slot-bytes that count as blockers is the same set encoded in the per-tile-class table.

A few special cases:

- **Closed doors block sight; open doors don't.** Door state is part of the tile id (closed and open doors have different ids), so the line-of-sight helper sees the right answer naturally.
- **Forest edges don't block sight; forest interiors do.** The map data uses different tile ids for the perimeter of a forest (which paints as forest but has the open-ground attribute) and the interior (which has the blocking attribute). This lets the player walk into a forest and see one cell out before the interior wraps around.
- **Mountains always block.** A mountain tile is opaque from any side. There is no "see over the mountain from a hill" mechanic.

## 7. Fog edge refinement

After the producer returns, a post-pass walks the grid and refines the fog edges. The pass runs in non-combat scenes only — combat materialises terrain through a separate path (Section 11) and skips the refinement.

The refinement uses a fixed five-cell light-periphery radius, distinct from the producer's light radius. It re-checks every cell against this periphery and toggles two specific marker bytes:

- A cell currently holding the *clear-visible* marker (`0xDD`) whose distance from the player exceeds five cells is downgraded to the *dim-periphery* marker (`0x1C`). It is still visible, but the renderer will dim it.
- A cell currently holding the *dim-periphery* marker (`0x1C`) whose distance from the player is at most five cells is upgraded back to the *clear-visible* marker (`0xDD`).

The five-cell threshold uses a quadrant-folded distance metric — distances are looked up in a small per-(dx, dy) table rather than computed via square roots. The table treats the four quadrants symmetrically (the metric is mirror-equivalent across both axes) and produces a small-integer distance approximating Chebyshev or octile.

The five-cell periphery is independent of the producer's light radius. In practice the producer's radius is usually equal to or larger than five (full daylight is much further), so the dim periphery sits inside the producer's visible region. Light sources whose radius is less than five — a torch in a dungeon, say — produce a fully-visible region with no dim periphery; the refinement passes idle on those frames.

The refinement only toggles between the two marker bytes; cells holding any other value (a real tile byte, the hidden marker, the use-companion marker, the already-rendered marker) are left unchanged. The pass is a no-op for grids where the line-of-sight helper has not emitted those markers — most ordinary frames have a visible-region full of *real tile bytes* rather than markers, so the toggle does nothing. The markers are written only by the active-object compositor (Section 8) and by certain mode-entry handlers; the refinement is what keeps them consistent with the player's current radius.

## 8. Active-object compositing

The same post-pass that handles fog refinement also stamps active objects into the grid. The active-object table — thirty-two slots of eight bytes each, shared with the rest of the engine — holds the player avatar (slot zero), all on-screen NPCs, monsters, vehicles, and animated props.

The compositor walks the table from slot thirty-one down to slot zero. Walking backwards means low-indexed slots paint *on top of* higher-indexed ones — and slot zero is the player, so the avatar always draws on top of any overlapping NPC or monster.

For each non-empty slot the compositor:

1. Reads the slot's world coordinates and floor.
2. In non-combat scenes, projects the world coordinates into the eleven-by-eleven viewport: subtract the player's position then add five (so the player sits at row five, column five). If the result is outside the eleven-by-eleven range, or the slot is on a different floor than the player, the slot is skipped.
3. Reads the corresponding visibility-grid cell. If the cell currently holds the hidden marker (`0xFF`) — the slot is in fog — it is skipped: no point compositing an invisible NPC. If the cell holds the already-rendered marker (`0x87`), it is also skipped: a higher-priority sprite has already claimed the cell.
4. Otherwise, stamps the slot's tile bytes into one or both of the two grids, with class-specific rules:
   - **Water-bound classes** (boats and rafts): tile bytes go into the *terrain band* (the sixteen-byte-stride buffer); the visibility grid receives the use-companion marker (`0x00`). The renderer reads the tile from the terrain band so that boats sit on water without overwriting it.
   - **Water-creature classes**: same handling as water-bound, with a different tile family.
   - **Vehicles** (the party leader on horseback, on a magic carpet): tile bytes go into both grids if the cell beneath has a specific terrain class; otherwise the slot falls through to the default branch.
   - **Default**: tile bytes go directly into the visibility grid. The terrain band is left alone; the renderer paints the slot's tile from the visibility grid in the normal way.

Before the per-slot loop runs, the compositor refreshes slot zero's bytes from the world-state globals: the avatar tile id, the player's world coordinates, the player's floor. This ensures the player slot reflects the current frame's truth before anything else is composited; the slot's data may otherwise be stale because the active-object animator runs only on certain ticks.

The end state, after the compositor: the visibility grid contains either real tile bytes (for in-radius unblocked terrain), markers (`0xFF`, `0x1C`, `0xDD`, `0x00`, `0x87`), or active-object tile bytes for slots that survived the cell guards. The terrain band has stamps for water-bound and water-creature classes. Both grids are then handed to the renderer.

## 9. The renderer's contract

The renderer (a separate system, described in its own spec) walks the visibility grid one cell at a time and paints the corresponding tile into the on-screen viewport. For each cell:

- If the cell holds the hidden marker (`0xFF`), nothing is painted. The previous frame's pixels remain; if the cell was visible last frame and is hidden this frame, a clear of those pixels is the renderer's responsibility.
- If the cell holds the use-companion marker (`0x00`), the renderer reads the corresponding cell of the terrain band and paints that tile.
- If the cell holds the dim-periphery marker (`0x1C`) or clear-visible marker (`0xDD`), the renderer reads the terrain band and paints the tile, applying a dim or full-brightness palette respectively.
- If the cell holds any other byte, the renderer paints that byte as a tile id directly.

After painting, the renderer is permitted to *zero* the visibility-grid cells it consumed. This is what enables the cheap path on the next frame: only cells the renderer cleared will be refilled by the cheap path's per-cell lazy fill, leaving any cell that the renderer left alone (because the producer will repaint it next dirty cycle anyway) as is.

The renderer does not consult the producer or the post-pass; it sees only the resulting bytes in the two grids. This decoupling is what lets the engine support different visibility producers (overworld, dungeon, combat) feeding the same renderer, with each producer responsible for materialising the grid into the renderer's expected end-state.

## 10. The cheap path

Most frames are *not* dirty: the player has not moved, the light has not changed, and no event has dirtied the visibility state. On those frames, the per-frame redraw orchestrator skips the producer entirely and instead runs a lazy refill loop directly on the grid.

The cheap path walks the eleven-by-eleven active window. For each cell whose current byte is *zero*, the path queries the world-tile getter at the cell's world coordinates and writes the resulting tile byte. Cells whose current byte is non-zero — a real tile byte, a marker, or an active-object stamp — are left alone.

The interpretation: zero cells are "consumed by the renderer last frame and need a fresh tile this frame." The renderer's discipline of zeroing-after-consume is what makes this work. Cells the renderer left alone are still valid; they retain their fog markers and active-object stamps from the previous expensive recompute.

The cheap path *does not* recompute line of sight, does not consult the light radius, and does not touch fog markers. It is a pure terrain-refill, intended to keep the screen showing the current map without redoing the visibility math. The fog post-pass and active-object compositor still run after the cheap path each frame, so on-screen sprites and dim-periphery markers stay accurate.

The cost of the cheap path is roughly one tile-fetch per consumed cell — a small fraction of the producer's full-grid line-of-sight walk. The engine is built around this asymmetry: the producer is an expensive once-per-event recompute, the cheap path is a per-frame topping-up.

## 11. Mode differences

**Overworld and underworld.** Use the full producer pipeline as described above. The active map buffer is the streamed 2×2 chunk window. The producer is called when the visibility-dirty flag is set, which happens on every player step (the step handler dirties the flag), on lighting changes (the per-turn cleanup dirties the flag if the daylight value changed), and on moongate appearance / disappearance.

**Town, dwelling, castle, keep.** Use the same producer pipeline with the active map buffer interpreted as a single 32×32 grid (no chunk streaming). Indoor lighting is computed against the local scene's lighting context, which may be different from the surrounding outdoor light. Some interiors are lit at night by candles and lamps; others are dark. The producer doesn't care which — it just consumes whatever light radius the lighting subsystem hands it.

**Dungeon-explore.** Uses a different visibility model entirely. There is no eleven-by-eleven viewport grid; the dungeon view is a first-person three-dimensional projection drawn by a dedicated renderer. The light radius still drives what's visible, but the rule is "darkness rendered as a black void" rather than "obscured cells in a top-down grid." The dungeon's visibility byte encoding lives directly in the live dungeon buffer (the dungeon terrain bytes are mutated in place to flag visited / unvisited cells), not in a separate scratch grid. Section 13 lists the open questions on this path.

**Combat.** Uses a fully materialised terrain grid in a separate buffer, pre-composited by the combat setup helper. The combat producer initialises this buffer to the hidden marker and fills it through the same line-of-sight helper family the 2D-scene producer uses, but combat does not consult the global light radius — combat scenes have their own lighting context, and the encoding does not include fog markers. The post-pass (fog refinement plus active-object compositing) skips combat scenes entirely; combat manages active-object compositing through its own round walker.

The mode boundary is enforced by the redraw orchestrator: it inspects the scene byte before choosing a path. Combat scenes (`scene >= 0x80`) take a *blat-copy* path that copies the pre-composited combat terrain grid byte-for-byte into the visibility grid, then runs the renderer. The producer is not called.

## 12. Special-case lighting

A handful of map tiles cast their own light, regardless of the global radius. The producer treats them as ordinary tiles for line-of-sight purposes; the lighting subsystem inflates the radius byte when the player is near such a tile, so the producer's downstream computation behaves as expected.

Known cases (interpretation; see Section 13):

- **Moongates.** An open moongate near the player adds a lit region surrounding the gate even at night.
- **Lord British's chamber.** Always fully lit, regardless of time of day.
- **Magical fields, glowing crystals, mounted dungeon torches.** Each contributes to the local light radius via a per-tile-class lookup.

The lighting subsystem's per-turn cleanup runs the inflation rules and produces the single light-radius byte the producer reads. Implementations should compute the inflated value at light-state-update time, not in the producer.

## 13. Open questions

- **Exact LOS step algorithm.** The line-of-sight helper's six-hundred-byte body has not been fully decompiled. Plausible candidates are Bresenham-style integer rasterisation per ray, quadrant-symmetric shadow-casting, or a precomputed sight-ray table. The function's large frame is consistent with any of these. A runtime probe with a known map would discriminate.

- **The blocks-sight tile-class bitmap.** The set of tile ids that block sight is a per-tile-class attribute, but the table itself has not been transcribed. The Section 6 list is interpretation; derive the blocking set from the engine's combined attribute table when it is mapped.

- **The dim-periphery vs fully-obscured semantics.** Whether the dim-periphery marker is *only* a renderer cue or whether some other system reads it is unconfirmed. Treat it as renderer-only until a reader is found.

- **The negative-light full-fill path's call sites.** No production game scene uses a negative radius in the data so far observed; the path may be a debug or development holdover. Implementers can omit it without behavioural difference in normal play.

- **Active-object record byte interpretation.** The active-objects spec reads bytes five through seven differently in different modes. The two interpretations should be reconciled against a per-class union.

- **The use-companion marker's full encoding.** The renderer's contract for `0x00`, `0xDC`, and `0xDD` is described in static-analysis notes but has not been confirmed against a live render. Treat as a renderer-internal contract.

- **Light-radius inflation at moongates and special tiles.** The per-tile-class inflation rules (which tiles add to the radius, by how much) are part of the lighting subsystem's table data and have not been transcribed.

- **Dungeon visibility encoding.** Dungeon mode encodes visited / unvisited / current-frame-visible directly into the live dungeon buffer via masking of the low three bits. The full encoding has not been mapped.

- **The asynchronous-read race window.** External readers sampling the visibility grid mid-frame see partial state — static-analysis notes record eleven distinct hashes during a thirty-sample passive read of one settled scene. Implementations that expose the grid to external readers should provide a synchronisation point.

## 14. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of those notes' assembly excerpts, byte offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The visibility producer's three-stage shape (hidden-fill, line-of-sight delegation, post-pass), the negative-light full-fill path, and the radius-sign branching — `u5-decomp/functions/ULTIMA_EXE/0x5D0A_visibility_producer.md`.
- The fog post-pass — five-cell-radius marker toggling and the active-object compositor that walks the table backwards and gates each slot on the visibility grid's cell value — `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md`.
- The redraw orchestrator that calls the producer on dirty frames, takes the cheap path on clean frames, blat-copies the combat terrain on combat frames, and clears the dirty flag after the producer returns — `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The world-tile getter that dispatches between combat, overworld 2×2 chunk window, and town/dungeon-explore single-grid buffers, including the out-of-bounds sentinel — `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The overworld map family's chunk layout (BRIT.DAT sparse, UNDER.DAT dense), the four-class location-DAT format, and the combat arena format that combat pre-composites — `u5-decomp/formats/maps.md`.
- The resident data segment's fixed locations for the visibility grid, the terrain band, and the per-cell scrap regions — `u5-decomp/formats/data-ovl.md`.
- The visibility-system reverse-engineering notebook from the companion-app project, used as a starting reference for buffer addresses, scene-to-routine map, and the asynchronous-read race observations — `ninth-virtue/docs/visibility-re.md:11-352`.
