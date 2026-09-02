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
| `0x00`          | "Use companion buffer." The cell is visible but the terrain band holds the tile to paint. This is the normal successful active-object compositor output, including water-bound, water-creature, seated single-sprite-family, and default-helper stamps. |
| `0xDD`          | Clear visible (inside the near/far distance of Section 7). A marker indicating "this cell is fully lit." The renderer treats it as a terrain-tile-from-companion-buffer cue with full brightness. |
| `0x1C`          | Dim periphery. Same as `0xDD` but the cell is beyond the fixed near/far distance of Section 7; the renderer dims the painted tile. |
| `0x87`          | "Already rendered." A guard the active-object compositor checks to avoid double-stamping. Higher-priority sprite already in this cell. |
| any other byte  | A direct tile id or renderer marker. The renderer paints or interprets this byte directly. Used by terrain producers, the negative-light full-fill path, and a few terrain-aware compositor marker writes. |

The exact handling of `0x00`, `0xDC`, and `0xDD` is the renderer's contract; the producer and post-pass describe their own writes only in those terms.

*One caveat on the two brightness markers.* The reading of `0xDD` and `0x1C` as general clear/dim markers is contract and is used throughout this document, but it has an unreconciled observation against it: the fog refinement of Section 7 rewrites only cells already holding one of those two values, and the shipped tile-name table gives both ids the same terrain name. See the open item in Section 13 before building anything that depends on those bytes meaning *only* brightness.

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
| Negative        | Full-fill path — populate every cell from the world map with no carve, no threshold and no line-of-sight test. The **redraw orchestrator** can never present this value, because it zero-extends the unsigned lighting byte before the call. It is nevertheless reachable, and shipped content drives it: the spell/potion visibility sweep — the White potion and the X-Ray spell — calls the producer directly with a negative sentinel in the light argument, which is exactly how those two effects reveal the whole window through walls (`catalogs/item-list.md` Section 7.2). **Corrected (R327):** this row previously said the branch was "structurally unreachable in the shipped 2D pipeline" and that "no shipped scene drives it". |

*Open question on the positive row.* The work that produced R318 and R327
established that the caller's light value selects the branch above, and that the
literal the producer passes to its carve helper is hard-coded inside the producer
and the same for every caller. Whether the caller's value *also* reaches the
carve as the squared-distance threshold was not re-derived, and the routine that
would carry such a test was not read. The positive row and the cell counts below
are therefore un-rechecked by that work — unchanged and uncontradicted, but not
independently reconfirmed. See the last bullet of Section 14.

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
- **Threshold negative.** The producer takes a full-fill path: every cell is populated from the world map directly, without any visibility carve, distance gate or blocker test. The grid ends up holding exactly the underlying terrain in every cell, no fog applied. The ordinary redraw path never reaches it — the orchestrator zero-extends the unsigned lighting byte before the call and can therefore never present a negative value — but the branch is not dead: the spell/potion visibility sweep passes the negative sentinel deliberately, which is the whole mechanism of the White potion and the X-Ray spell. Implement it as live gameplay behaviour, not as compatibility scaffolding. **Corrected (R327):** this bullet previously called the branch structurally unreachable and told implementers they could treat it as non-gameplay.

**Stage 3 — return.** The producer does not clear or flip any flags itself; the redraw orchestrator handles the dirty-flag reset.

End-of-stage state, per case:

```text
positive threshold:  grid cells resolved by the carve = real tile bytes;
                     grid cells not resolved by the carve = 0xFF.

zero threshold:      every cell = 0xFF, the player's own cell included.

negative threshold:  every cell = real tile byte (no fog). Not reached from the
                     ordinary redraw path; driven by the spell/potion
                     visibility sweep.
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
| Diagonal wedge tiles `0xD0..0xD3` (terrain-half ids that carry the placeholder description; the driver also uses them as the water composite's stencil, `systems/animation.md` Section 12.3) | Stop propagation. |
| Sign/poster tile `0xF8` (terrain-half id carrying the placeholder description) | Stops propagation. |
| Wall `0xFE`, and the void tile `0xFF` ("darkness!") | Stop propagation. |
| Arrow slit `0x4A`, window `0x4B` | Propagate only when orthogonally adjacent to the centre cell. |
| Odd door `0x98` | Propagates only when orthogonally adjacent to the centre cell. |
| Wooden door with a window `0xBA`, locked door with a window `0xBB` | Propagate only when orthogonally adjacent to the centre cell. |

Read as a set, the rule is legible: solid vegetation, rock, walls and closed
doors block sight outright, while the four openings you can only see through
from immediately in front — an arrow slit, a window, and the two windowed doors —
propagate exactly one cell.

**Correction — the monster names below are withdrawn, and nothing in this
document names these ids after a creature.** Earlier revisions of the table
above named them after monsters: `0x97` a Bat frame, `0xB8..0xBB` Gargoyle
frames, `0xBC` an Insect Swarm frame, `0xD0..0xD3` Headless frames, `0xF8` a Rot
Worm frame, `0xFE..0xFF` Shadow Lord frames, `0x4A..0x4B` and `0x4D..0x4F`
bookshelf/dresser/vanity/trunk variants, and `0x5A` a sign post. **Every one of
those names is withdrawn**, and they are reproduced here only so a reader who
implemented them can recognise what to remove. The creature names were not
invented: they are real names, but of the **actor-half** atlas entries
`0x197`, `0x1B8..0x1BB`, `0x1BC`, `0x1D0..0x1D3`, `0x1F8` and `0x1FE..0x1FF`,
which this classifier can never see. They were read out
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
   - **Single-sprite-family seated branch.** If the slot's type byte is
     exactly `0x5C` and the terrain byte standing in the visibility-grid cell
     is the chair id `0x92`, the compositor stamps the slot's frame byte into
     the terrain band and leaves the visibility grid on the use-companion path
     — that is, an actor of this one sprite family sitting on a chair of that
     facing keeps its own sprite instead of being merged into a generic
     occupied-chair tile. When the type byte is `0x5C` but the terrain is
     anything else, the slot goes to the default helper with its frame byte
     reduced by eight, remapping it to a different sprite family; what that
     remap is *for* has not been established, only that it happens.
     *Retracted:* an earlier revision called this the "vehicle/avatar-family
     companion branch" and said it "takes the special vehicle stamp". Type
     byte `0x5C` is one ordinary NPC sprite family — the tile-name table calls
     it a minstrel — and the party's own type byte is the party sprite marker,
     which is never `0x5C` outside combat, so no vehicle and no avatar ever
     reaches this branch in a world scene. See `RETRACTIONS.md`.
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
| Current terrain `0x90` (chair, that facing), with the previous-row terrain equal to `0x9B` or `0x9C` — **laden-table ids only** | Stamp one of `0x38..0x3B`. |
| Current terrain `0x90`, without that previous-row match | Stamp `0x30`. **No variant is selected on this row.** |
| Current terrain `0x91` or `0x93` | Stamp `0x31` or `0x33`, respectively. |
| Current terrain `0x92` (chair, the opposite facing), with the next-row terrain equal to `0x9A` or `0x9C` — **laden-table ids only** | Stamp one of `0x34..0x37`. |
| Current terrain `0x92`, without that next-row match | Stamp `0x32`. **No variant is selected on this row.** |
| Current terrain `0x9D` or `0x9E` | Stamp one of `0x3C..0x3F`. (Only `0x9D` is reachable — see below.) |
| Current terrain `0xAB` | Stamp `0x1A`. **A single fixed tile — not a variant, and no selection is made.** |
| Current terrain `0xC8` | Stamp `0x17`. |
| Current terrain `0xC9` | Stamp `0x18`. |
| Any other current terrain, with previous-row terrain `0x9D` and the projected viewport row not on the top edge | Write direct marker `0x9E` into the previous viewport row, then stamp the effective tile unchanged through the companion band. |
| Any other current terrain | Stamp the effective tile unchanged through the companion band. |

*Convention for the table above: the values in the result column are the bytes
the compositor stamps into the companion band. The renderer paints a stamped
`0xNN` as the **second-bank** tile `0x1NN`, and that second-bank form is what
Sections 8.3 and 8.4 use whenever they discuss the artwork itself. The two
numberings name the same tiles.*

The four-entry variant choices above (`0x60..0x63`, `0x64..0x67`,
`0x38..0x3B`, `0x34..0x37`, and `0x3C..0x3F`) use the shared variant selector:
**unless the Negate Time timed effect is active, select a uniform random entry
from the four-value range; while it is active, the selector short-circuits and
returns the first entry for every actor.**

*Retracted:* an earlier revision of this paragraph said the first entry is
selected "when the current active character's class letter is Tinker". There is
no character-class input to this selector. The byte it tests is the single
global timed-magic-effect code, and the value that short-circuits it is the one
Negate Time writes; the resemblance is that both are stored as a letter. An
implementation that wired this to the party's classes will pick variant 0 for
the wrong reason and will animate through Negate Time. See `RETRACTIONS.md`.

> **Normative, and the single most-misread line in this section.** Those five
> rows are the **only** rows that reach the selector. **Every other row of the
> table above — including both chair fall-throughs, the bed, the two ladders,
> the two facing-only chairs, and the plain pass-through — makes no selection
> at all.** An engine that draws from the shared stream on any other row
> advances the single global generator when the original does not, and its
> stream position diverges permanently from the original's. See Section 8.1.

**How narrow the two chair rows really are.** Both are gated on a
*neighbouring-row* terrain byte, and the accepted set on each is exactly the
three ids the shipped tile-name table calls a table *with food on it*
(`0x9A`, `0x9B`, `0x9C`). Two consequences an implementer will get wrong from
the table alone:

- **The accepted set differs per facing, asymmetrically.** The `0x92` chair
  accepts `0x9A` or `0x9C` on the row below it and rejects `0x9B`; the `0x90`
  chair accepts `0x9B` or `0x9C` on the row above it and rejects `0x9A`. The
  two sets are not the same set, and neither is "any laden table".
- **A bare table is not a table for this purpose.** The plain-table ids
  `0x94..0x96` never qualify, and neither does any other furniture — an end
  table, a desk, a candelabrum, a harpsichord, or ordinary floor. Every one of
  them falls through to the single fixed occupied-chair tile, which can never
  change for as long as the actor sits there.

The practical shape of this in the shipped maps: a full census of every chair
cell in the four town/dwelling/castle/keep location files, adjudicated against
its own neighbouring row, finds **roughly half** of the `0x92` chairs and
**about two in five** of the `0x90` chairs qualifying. Both readings are
therefore common in normal play, and **a seated actor that never changes tile
is the expected result for the majority of seats in the game, not a defect.**
A test that seats an actor on an arbitrary chair is as likely as not to be
testing a fall-through.

**The four fixed occupied-chair tiles are four facings, not four frames.**
`0x30..0x33` are visually far apart from one another (they differ across most
of the tile), and the terrain id's low two bits pick among them directly. They
are not a cycle and nothing selects among them at random.

Negate Time is the only *effect* that produces that code in the shipped game,
but it has **two** producers, not one. A re-run census over the executable and
all twenty-three code overlays, decoding every occurrence of the effect byte's
address back to an instruction, finds nine writers: the **Negate Time spell**
handler, which writes the code as an immediate together with the effect's
ten-turn duration; the shared **timed-effect setter**, which writes the code
from its argument and is passed this code by exactly one of its call sites, the
**Negate Time scroll**, with a twenty-turn duration; **one site that installs a
different timed-effect code into the same byte** — this is a shared
timed-effect register that other effects also write, not a Negate Time flag —
and six sites that clear both the code and its duration, two writing the clear
as an immediate and four through the accumulator after zeroing it. The shipped starting state has the
code clear, so a game begun from the factory template has the selector on its
random arm from the first frame.

*Retracted:* an earlier revision of this paragraph said the census found "one
site that writes it as an immediate" and that the generic three-argument effect
setter's "only three call sites anywhere pass the Protection code twice and a
non-letter code once, **never this one**". That is wrong: one of that setter's
call paths is the Negate Time scroll, which installs this same code for twenty
turns. An engine that freezes the selector only for the spell will animate
seated furniture through the scroll's effect. `catalogs/item-list.md` has
carried the scroll's twenty-turn install correctly throughout; it was this
document's census that was incomplete. See `RETRACTIONS.md`.

*Scope:* that census is closed over every store whose destination is written as
a literal address. To bound the remaining forms, every byte store with a
literal-address destination anywhere in the saved-state band was also decoded
across the whole shipped set, and none of them writes this code as an
immediate. A store through a register-computed pointer that happened to land on
this byte carrying this value was not excluded, and neither was a bulk restore
of the surrounding saved-state band — though the latter would be a reload of a
previously set effect rather than a new producer.

Before the per-slot loop runs, and **only outside combat**, the compositor refreshes slot zero's bytes from the world-state globals: the avatar tile id, the player's world coordinates, the player's floor. This ensures the player slot reflects the current frame's truth before anything else is composited; the slot's data may otherwise be stale because the active-object animator runs only on certain ticks. Note that this refresh writes the party sprite marker into **both** the slot's type byte and its sprite byte, which is why the party can never satisfy the type-byte test of the single-sprite-family seated branch above. In combat the refresh does not run — nor does the fog refinement of Section 7 — and slot zero's type byte is then whatever the combat subsystem left there; that value was not established here, so the branch's behaviour for the party *in combat* is outside this contract.

The end state, after the compositor: the visibility grid contains either real tile bytes resolved by the carve, markers (`0xFF`, `0x1C`, `0xDD`, `0x00`, `0x87`), or direct marker writes from terrain-aware compositor cases. Active-object visual tiles that survive the cell guards normally live in the terrain band behind the `0x00` marker. Both grids are then handed to the renderer.

### 8.1 When the variant is drawn, and how often

> **Normative.** For an actor whose composite lands on one of the five
> selecting rows of the Section 8 table, the variant is drawn **once per
> composite pass** — not once per placement — and **it is never cached
> anywhere.** For every other composited actor, **no draw is taken at all.**

*Retracted:* an earlier revision of this box said, without that qualifier, that
"the variant is drawn once per composite pass, per actor", and this section
closed with "There is exactly one draw per qualifying actor per pass" while
Section 8 left "qualifying" to be inferred from a table whose fall-through rows
look like ordinary rows. An engine that draws once per *composited* actor takes
draws the original does not — most often for a seated actor next to furniture
that is not a laden table — and its global stream position then diverges
permanently. See `RETRACTIONS.md`.

The selector is a helper that takes no arguments and stores nothing of its own:
it returns a value in `0..3` which the caller consumes immediately. Its one
side effect is the generator advance inside the shared draw itself, which is
unconditional whenever the selector is entered on its random arm. It is reached
from five mutually exclusive arms of the terrain-substitution table above, so
no actor draws more than once in a pass.

**The exact per-pass count.** The composite pass takes, from the shared
gameplay stream:

> one draw for each actor that (a) survives all of the pass's per-slot skips,
> (b) is handed to the default helper rather than to one of the three
> direct-stamp branches, and (c) stands on stocks, manacles, a mirror, or a
> chair whose neighbouring row on the correct side holds a laden-table id —
> and zero draws for everything else, including actors on chairs that do not
> qualify, on beds, on ladders, and on ordinary floor.

That count is frequently **zero for a whole pass**, and in an ordinary town
scene with nobody seated at a laid table it is zero on every pass.

All three conditions are load-bearing for stream parity, and the order matters:
**every skip is evaluated before the compositor is invoked, so a skipped actor
costs no draw at all.** An implementation must not draw speculatively for an
actor it is about to skip, and must not cache a value across passes. The skips
are the empty slot, the wrong floor, the off-viewport projection, the missing
sprite byte, the fogged cell and the already-claimed cell — with the caveat
that in combat mode the viewport projection, the floor test and the range tests
are not performed at all, so the surviving-actor set is not the same in the two
modes. The three direct-stamp branches (the two water/companion classes and the
single-sprite-family seated branch of Section 8) bypass the compositor
entirely and therefore never draw, whatever terrain they are on.

Nothing about the actor's placement, arrival or movement enters the decision.
The drawing path reads five fields of an actor record — a type byte, a sprite
id, a map column, a map row and a map level — and derives the variant afresh
from the terrain beneath the actor every time the actor is drawn.

**There is no cache to find.** The compositor's complete write set is three
places: the visibility grid, one cell of that grid on the row above (for the
mirror-reflection rule of the table above), and the companion sprite band. It
never writes back into the actor record; the selector stores nothing of its own
beyond the shared generator advance already described; there is no per-actor
variant field, no scratch table keyed by actor, and no frame counter anywhere
in the path. The one place a chosen variant survives the
call is the companion-band cell the renderer reads — and that is a destination,
not a cache. Nothing reads it back to decide a later variant, and every
composite pass overwrites it.

The visibility grid does not preserve the composited cell either, and the
correct statement is narrower than "the producers restore it":

- **The cheap path** (Section 10) refills exactly the cells carrying the
  use-companion value from the map — precisely the set the previous composite
  consumed — so every one of them is re-composited.
- **The combat path** block-copies the arena terrain over the whole grid, so
  likewise every cell is restored.
- **The full rebuild** first clears the entire grid to the hidden marker, and
  what comes back depends on the current lighting scalar: with a positive light
  radius only cells the radial visibility pass marks visible are restored, so an
  actor outside line of sight is correctly skipped rather than re-composited;
  with the scalar negative (full daylight) every cell is refilled from the map;
  with it zero the grid stays entirely hidden.

While the player is standing still the dirty flag is clear and the cheap path is
what runs, so for the idle case every pass re-enters the same arm and draws
again.

### 8.2 The composite is not gated on the dirty flag

> **Normative.** The composite and the raster run **unconditionally** at the tail
> of the redraw routine. The visibility dirty flag exists, but it does not gate
> either of them.

This corrects a premise rather than a published claim, and it is worth stating
because the natural reading of Sections 10 and 11 is that a clean frame does
less work. It does less *producer* work. The redraw routine has exactly one
early exit — the master redraw-enable gate — and past it every path converges on
the same two steps, composite then rasterize. The dirty flag is tested upstream
of that convergence and only chooses **which** of the three grid producers above
runs. Nothing is gated on a turn boundary, and no branch skips either tail step.
The composite still runs while Negate Time is active; it just draws variant 0
every time.

*Scope on the early exit.* A widened scan covering every direct-address store
form across the executable and all overlays finds exactly two writers of the
master redraw-enable gate, both **setting** it (one on outdoor scene entry, one
on town entry), and the shipped data image has it clear. Indexed and
computed-pointer writes were not covered, so "nothing ever clears it in a world
scene" is an observation, not an invariant.

### 8.3 The variant therefore changes while the player stands still — *probable*

An actor standing on stocks, on manacles, on a mirror, or on a chair whose
neighbouring row on the correct side holds a laden-table id is redrawn with a
freshly chosen variant on **every idle pass**, so the value painted into its
cell changes on about **three passes in four** while the player presses
nothing. **This claim is about the four kinds of cell listed in that sentence
and no others**; a seated actor on any other chair is painted the same fixed
tile every pass and correctly never changes.

That three-in-four figure is a property of the shipped pseudo-random generator,
computed by re-running it, not a timing measurement: the generator's state
advances on every call, the requested span of four divides its output range
exactly so the four outcomes are equally likely, its state cycle is 47,343 long,
the `0..3` histogram over 200,000 draws is flat to within about 0.7 percent, and
the probability that two draws separated by one to five steps differ is 0.7508.

**This is not a rendering artefact to be smoothed away. It is how the original
produces idle animation for these merged sprites — a random frame per redraw
instead of a phase counter — and an engine should reproduce it.** The shipped
tile-name table names the four-frame sets "a prisoner", "an occupied chair" and
"a trapped soul!", and every non-animating case in the same table uses a single
fixed combined tile instead of a four-frame set. Independent capture on the
implementation side saw the same shape in combat, where party actors re-rolled a
weapon-angle variant on 95 percent of ticks among roughly eight variants in
scrambled order.

The exceptions that keep this from being universal:

- **Chairs that do not qualify — roughly half of the chairs in the shipped
  maps — take a single fixed occupied-chair tile with no draw at all**, and so
  do chairs in the other two facings, a bed, and the two ladder tiles. None of
  these ever changes. This is the large exception, not a corner case: see the
  narrowing paragraphs at the end of Section 8.
- **Only two of the five selecting rows are reachable by the party at all.**
  Stocks, manacles and mirrors are blocked terrain: the movement gate the
  party's own step consults refuses them, so the prisoner and trapped-soul
  variants are **NPC-only** in normal play. The party can walk onto the two
  chairs and onto a bed, and of those only the two chairs can select — the bed
  is one fixed tile. *Scope: this is a result about the walk validator. Non-walk
  placement routes — teleport, spell displacement, scripted imprisonment — were
  not enumerated, so it is not a whole-engine invariant.*
- **The shipped schedules never put an NPC on stocks or on a mirror.** Across
  the adjudicated scheduled waypoints of the four location NPC files,
  sixty-four land on qualifying chairs and three on manacles — one
  permanently manacled NPC in Serpent's Hold, scheduled to the same manacle
  cell at every waypoint, which should cycle its variant all day — while
  stocks and mirrors get none. So two of the five selecting rows have no
  scheduled occupant in that set and can be reached only by a dynamically
  placed actor, which the census does not cover. *Scope: it counts only
  waypoints whose floor index is one of the two ground-floor values,
  adjudicated against the map half that index is taken to select — a mapping
  that is itself only **probable**, since the same field also takes three
  further values, on hundreds of waypoints, that a two-half model cannot index
  at all. Waypoints outside that set were not adjudicated, so this is a
  statement about part of the schedule data under an unconfirmed mapping, not
  an exhaustive one.*
- Ship and monster sprites never merge, so they never animate this way: monsters
  are stamped through unchanged, and frigate/ship sprite values are routed by
  the compositor's entry test straight to the plain stamp before terrain is even
  sampled.
- The appearance freezes on variant 0 for the whole duration of Negate Time —
  **ten** turns when the effect came from the spell, **twenty** when it came
  from the scroll (Section 8).
- Scenes in the suppressed idle band — the eight dungeon scenes and the
  intro/front-end screens among them — do not run the idle redraw at all
  (`systems/timing.md` Section 8.2), so nothing animates this way there.

This stays published as **probable** rather than established, but the reason
has changed and is worth stating plainly, because the earlier reason invited
the wrong test. Every link in the mechanism was read — a fresh draw for an
actor on a selecting row, no cache to carry a choice forward, an unconditional
composite-and-rasterize tail, a rasterizer with no change detection, and one
redraw per key-less input poll. What is not established is the step from **"a
new value is painted"** to **"a person sees the sprite change"**, and there are
now two distinct reasons for the gap, only the first of which was previously
given:

1. **The arm is much narrower than the old prose suggested.** An observer who
   seats an actor on a chair that does not qualify will correctly see nothing
   move, and will reasonably but wrongly conclude the mechanism is absent. Any
   capture that does not first confirm the neighbouring-row terrain proves
   nothing either way. A report of "a seated actor never changes tile" is
   therefore consistent with a fully correct implementation.
2. **Two of the five sets are visually marginal.** Per-tile pixel comparison of
   the decoded tile art shows the `0x138..0x13B` occupied-chair set — the one
   for the chair that reads its row *above* — differs between frames in only a
   handful of the tile's 256 pixels, so a correct implementation painting a new
   value every pass may be genuinely imperceptible there. Worse, the
   trapped-soul set is effectively **two** images rather than four: two of its
   entries are identical and the other two differ from each other by a single
   pixel, so a uniform draw over four entries produces a fifty-fifty two-state
   blink, not a four-frame cycle. The `0x134..0x137` chair set and the two
   prisoner sets are the visually strong ones and are the right subjects for a
   capture.

Consequently: **a live capture settles this only if it names the cell it used
and the terrain on the neighbouring row.** The strongest available subjects in
the shipped data are the permanently manacled NPC in Serpent's Hold — one
roster slot whose every scheduled waypoint is the same manacle cell, carrying
the generic-townsperson sprite class (`catalogs/npc-roster.md`, tag `50`; that
is a sprite class, not an established role) — an unconditional row with no
neighbour predicate, visible all day, and the widest frame-to-frame spread of
any set. After that, any tavern patron seated at a laid table. A `0x90`-facing chair
is the worst possible primary test and should not be used. The *perceived rate* depends on the idle cadence and is owned by
`systems/timing.md` Section 8.

### 8.4 What the merge actually is, and a consequence for randomness

The substitution these variants belong to is a **furniture merge**: an actor
standing on a piece of furniture is not drawn as an actor on top of terrain, it
is replaced wholesale by a combined "occupied furniture" sprite drawn from the
second tile bank. The companion-band values in the table above are second-bank
ids — the stocks set is `0x160..0x163`, the manacles set `0x164..0x167`, the two
occupied-chair sets `0x134..0x137` and `0x138..0x13B`, and the trapped-soul set
`0x13C..0x13F` — and the merge applies only to the party's own sprite families
(on foot, horse, magic carpet, skiff) and to the humanoid NPC sprite range.
There is nothing avatar-specific anywhere in the merge: an NPC in the humanoid
sprite range on a selecting terrain merges by exactly the same rules the party
does.

**Terrain `0x9E` never appears as map terrain and its row is dead in the
shipped game.** Only `0x9D` reaches the trapped-soul selection. *Scope: this
negative was checked over the four location files (`TOWNE.DAT`,
`DWELLING.DAT`, `CASTLE.DAT`, `KEEP.DAT`), both overworld files (`BRIT.DAT`,
`UNDER.DAT`), both arena files (`BRIT.CBT`, `DUNGEON.CBT`), `DUNGEON.DAT`, and
`MISCMAPS.DAT`. The value occurs zero times in all of them except
`MISCMAPS.DAT`, which has two — and both of those fall inside its third
section, the Return-to-View **command stream** (`formats/location-dat.md`
Section 11), not inside either of its two map sections. Runtime writes of the
value into the live map buffer through a computed pointer were not excluded; no
literal-address store of it into that buffer exists anywhere in the shipped
set.* Note that the compositor's **own** `0x9E` write, on the last row of the
Section 8 table, targets the visibility grid one row above the actor and is the
mirror's reflection sprite — it is not a terrain write and the compositor never
reads the visibility grid back as terrain.

**Reachability of the merge in combat — now checked, and narrow.** *Retracted:*
an earlier revision said "whether combat arena maps actually contain the stocks,
manacles, chair or mirror terrain values was not checked, so reachability of the
merge in combat is unverified". It has now been checked, over both shipped
arena files, with the arena record's terrain columns separated from its
placement-metadata columns — separating those is essential, because a naive
whole-file byte count reads creature-type bytes out of the metadata band and
badly overstates every furniture count. Against arena **terrain** only:

- Outdoor arenas contain **none** of the furniture terrains at all.
- Dungeon-room arenas contain four manacle cells, one mirror cell, three
  chairs of each facing — and **no stocks whatsoever**.
- Of those six chairs, **exactly one selects**: a single `0x92` seat in one
  arena with a laden table on the row below it. That is the only rolling chair
  anywhere in combat in the whole shipped game.
- **No `0x90` seat can ever select in combat.** One arena demonstrates the
  per-facing asymmetry live, in a single column: one laden-table cell with a
  `0x92` seat directly above it and a `0x90` seat directly below it. The `0x92`
  seat selects; the `0x90` seat, reading that identical cell, does **not**,
  because that particular laden-table id is in the `0x92` row's accepted set
  and not in the `0x90` row's. Any implementation that treats the two rows as
  accepting the same set of neighbours gets this cell wrong.

The compositor itself remains scene-independent and reads whatever terrain
source the scene uses; what has changed is that the arena content is now known
rather than assumed.

**A consequence that belongs to `systems/prng.md` as much as to this document:
rendering and idling perturb the single global gameplay stream, so it is not
reproducible from the player's action sequence alone.** One idle world tick
draws from that stream in this order, and an engine aiming at deterministic
replay must reproduce all three consumers **in this order**:

1. **The active-object animator**, first. It draws from within its per-record
   loop at three separate points. *This consumer was omitted from this
   document's earlier inventory entirely.* Its per-pass count is
   record-dependent and has not been characterised here.
2. **The wind check**, second. It draws **once** and returns in the common
   case. On the uncommon result it enters a retry loop that takes **one further
   draw at a time**, so its per-invocation count is one, two, three, and so on
   upward — not one, two, or a jump to an unbounded sequence. The first draw
   settles it in sixty-three invocations out of sixty-four, and each additional
   iteration continues with probability roughly `0.15`. **No maximum exists and
   an engine must not assume one**; the loop has no static bound.
3. **The composite pass**, third — one draw for each composited actor that
   lands on a selecting row of the Section 8 table, and zero for every other
   actor (Section 8.1). The renderer that runs after it draws nothing.

*Retracted:* an earlier revision of this paragraph described the wind check as
entering "a retry loop that **draws in pairs** until it settles, so its draw
count per invocation is one, two, or an unbounded sequence above that". The
retries are single draws and every integer upward is reachable. An engine that
reproduced the pairs shape advances the shared stream by the wrong amount on
every retry. See `RETRACTIONS.md`.

*Retracted:* the same paragraph previously named **two** idle-path consumers,
the composite and the wind check. There are **three**; the active-object
animator draws ahead of both, and an engine that reproduces only two diverges
on ordinary idle frames even with no actor seated anywhere. See
`RETRACTIONS.md`.

The net direction of the correction is worth stating, because it runs opposite
to what a reader might expect from Section 8.1's narrowing: **this section's
"rendering perturbs the gameplay stream" was understated, not overstated.** Even
a pass in which no actor is on selecting furniture still draws at least once
from the wind check and usually more from the animator.

*Scope on that inventory:* it comes from walking the call graph transitively
from the world tick's callees to the shared draw helper, over direct calls
resolved from their own encodings, with each call site attributed to its
enclosing routine. Indirect calls and helpers without a standard prologue are
not covered by that walk; the one such helper in this path, the variant
selector itself, was added by hand.

## 9. The renderer's contract

The renderer (a separate system, described in its own spec) walks the visibility grid one cell at a time and paints the corresponding tile into the on-screen viewport. For each cell:

- If the cell holds the hidden marker (`0xFF`), nothing is painted. The previous frame's pixels remain; if the cell was visible last frame and is hidden this frame, a clear of those pixels is the renderer's responsibility.
- If the cell holds the use-companion marker (`0x00`), the renderer reads the corresponding cell of the terrain band and paints that tile **from the second tile bank**. This is exactly the set of cells the compositing pass stamped a sprite into, since that path is the only writer of the value. It is also the only branch that honours the reserved draw-nothing companion value `0x16`, which skips the cell.
- If the cell holds the dim-periphery marker (`0x1C`) or clear-visible marker (`0xDD`), the renderer reads the terrain band and paints the tile, applying a dim or full-brightness palette respectively.
- If the cell holds any other byte, the renderer paints that byte as a tile id directly, **from the first tile bank and through the engine's 256-entry animated-tile frame table** (`systems/animation.md` Section 6.1). That table is runtime state, not a fixed translation: it is identity-filled at startup and then advanced per animation step for the five animated families, so an ordinary terrain cell is repainted with that tile's *current* frame on every pass. An implementation that paints the authored id here will draw every waterfall, fountain, pendulum, banner and clock in the game motionless.

Those four branches are the whole of the per-cell dispatch an implementation should build. The trace also found one further branch — the moon-gate cell's rise-and-sink blit, taken while the shared gate-presence counter is inside its gating range. This document does not restate it, because it is already published as contract in `systems/overworld.md` Section 9.1 (counter value to painted artwork, and the counter's own lifecycle); implement it from there. Section 13 records the identification.

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

There is no previous-frame buffer, no per-cell comparison against the last frame, and no skip path other than the reserved draw-nothing value on the first branch. The cell loop is flat and emits a blit for every one of the one hundred twenty-one cells on every pass.

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

  **The two tile ids are `0x1B` for the lighthouse and `0x2A` for the bright
  light.** Both are fixed against the shipped description table, which is the
  method `catalogs/tile-catalog.md` itself sanctions: `0x1B` reads "a
  lighthouse" and `0x2A` reads "a bright light". The neighbouring ids are
  given here because they were the source of an earlier ambiguity: `0x27` and
  `0x28` **both** read "a roof", `0x29` is the crystal sphere and `0x2B` the
  hollow stump. An earlier revision of `systems/npc-schedules.md` listed four
  names across those five ids, which left `0x27` and `0x28` unresolved; that
  table now enumerates each id separately.
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
active-object compositing, the renderer/effect read contract for the four
per-cell branches of Section 9, cheap terrain refill, mode boundaries,
local-light mask ownership, beacon-mask ordering, and the negative-light
full-fill branch — now known to be live gameplay behaviour driven by the
spell/potion visibility sweep rather than compatibility scaffolding (R327) —
are fixed. Remaining work is visual parity, one
unspecified renderer branch, or external-tool synchronization policy rather than
ordinary gameplay visibility behavior.

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

- **One special-cased renderer branch — the value and gating range are now
  identified.** Beyond the four per-cell branches of Section 9, the renderer
  carries one more: a single visibility value is routed to a separate animated
  blit driven by its own counter while that counter is within a gating range,
  and takes the ordinary direct-tile-id path otherwise. That value is the
  moongate tile id `0xDC`, and the gating range on the counter is `1..0x0F`
  inclusive — it is the moon-gate **rise-and-sink blit**, driven by the shared
  gate-presence counter, **not** a moon-phase term. The branch is still not
  written out in Section 9, but it is **not unspecified**: the mapping from
  counter value to painted artwork, and the counter's own lifecycle, are
  published as contract in `systems/overworld.md` Section 9.1, and Section 9 of
  this document defers to it rather than restating it. What has changed here is
  only that an engine seeing one tile id animate on the direct path now knows
  which id it is and where its contract lives.

- **The two marker bytes of Section 2 may not be pure markers.** The fog
  refinement of Section 7 rewrites only cells that already hold `0xDD` or
  `0x1C` — and the shipped tile-name table gives **both** of those ids the
  *same* terrain name. A pass that substitutes between two ids naming one
  specific terrain reads more like a two-tile terrain substitution than like a
  general clear/dim marker pair. Section 2's reading of the two bytes as
  brightness markers is published contract and is **not** withdrawn here; it
  was simply not re-derived against this observation, and the two readings have
  not been reconciled. An engine that sees that one terrain behave oddly under
  fog should chase this first.

- **The asynchronous-read race window.** External readers sampling the visibility grid mid-frame see partial state — static-analysis notes record eleven distinct hashes during a thirty-sample passive read of one settled scene. Implementations that expose the grid to external readers should provide a synchronisation point.

## 14. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of those notes' assembly excerpts, byte offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The visibility producer's three-stage shape (hidden-fill, visibility-carve
  delegation, post-pass), the negative-light full-fill path, and the branching
  on the lighting value's sign — `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: Sections 8.1 through 8.4, and the frame-table clarification
  in Section 9 — the corrected identity of the variant selector's short-circuit
  input, the once-per-pass-never-cached contract and the compositor's complete
  write set, the three grid producers' differing restoration behaviour, the
  unconditional composite-and-rasterize tail, the rasterizer's two-branch cell
  rule, the furniture-merge substitution and its second-bank sprite sets, and the
  producer census for the Negate Time effect code — are a cleanroom
  rewrite of private analysis under `u5-decomp/functions/ULTIMA_EXE/`, repaired
  after an adversarial verification pass whose scope limits are carried in the
  prose. The three-in-four change figure was obtained by re-running the shipped
  generator, not by observing the game. Idle cadence, and therefore the perceived
  rate of the re-roll, is owned by `systems/timing.md` Section 8 and rests on a
  black-box measurement contributed by the clean implementation side on issue
  #179.
- Source provenance: the issue-#182 re-scoping of Sections 8, 8.1, 8.3 and 8.4 —
  the laden-table neighbour predicate and its per-facing asymmetry, the
  fall-through tiles that take no draw, the re-identification of the `0x5C`
  compositor arm, the two-producer Negate Time census, the three-consumer
  idle-path PRNG inventory and its ordering, the single-draw shape of the wind
  check's retry loop, the arena-terrain census behind the combat-reachability
  closure, the dead `0x9E` row, the moongate identification of Section 13's
  formerly unspecifiable renderer branch, and the per-frame pixel comparisons
  behind the "visually marginal" caveat — is a cleanroom rewrite of private
  analysis under `u5-decomp/notes/`, itself repaired after two adversarial
  verification passes. Every negative claim above carries the search scope it
  was established over, in the prose, because several of that note's earlier
  figures failed exactly by being stated without one: a whole-file byte count
  that swept in a map format's metadata band badly overstated the arena
  furniture counts until the terrain and metadata columns were separated.
- Source provenance: the finding that the lighting byte is the squared-distance
  threshold itself rather than a sight radius, the unaltered four-hop chain of
  custody from the per-turn ambient computation to the carve's comparison, the
  inclusive sense of that comparison, the per-threshold cell counts and reach
  values, the unconditional centre-cell seed, the local-light rule for
  candidates beyond the threshold, the fixed near/far distance of the fog
  refinement and its twenty-one-cell core, the zero-extension that keeps the ordinary
  redraw path off the negative-value branch (which the spell/potion sweep
  nevertheless reaches directly, R327), and the whole-binary census showing a
  single *distance-threshold* consumer of the lighting value, alongside the
  night-time beacon's day/night read of the same byte — derived from private
  analysis note
  `u5-decomp/notes/light_threshold_semantics_2026-08-22.md`. That note also
  withdraws the "light radius in tiles" and ray-walk descriptions carried by the
  older private lighting/visibility system trace.
- The queue-based visibility carve, propagation-blocker set, and special-case
  adjacent-only propagation rule
  — `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: the names of the nineteen propagation blockers and the five
  adjacent-only ids in Section 6, and of the ten local-light source ids in
  Section 12.3, were re-derived by decoding the shipped description table with
  the container rules in `u5-spec/formats/look2-dat.md`. That decode also
  withdraws the monster/furniture names those two lists previously carried; the
  id membership of every list is unchanged.
- The local-light mask refresh pass, source-candidate lookup, per-source carve
  radius, its squared-distance semantics, the three trigger points, and the
  final untouched-cell zeroing —
  `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 4.
- The carve's two caller modes, the per-source visited grid, the stop-at-the-
  disc-boundary rule for local light, the fact that a blocker cell inside the
  disc is itself lit, and the folded squared-distance lookup being exactly
  `dx * dx + dy * dy` - `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md`
  sections 6.2 through 6.4, cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/`, and
  `u5-decomp/functions/ULTIMA_EXE/`.
- The Moonstone-slot live-gate refresh caller that rebuilds the local-light
  mask after in-scene tile rewrites -
  `u5-decomp/functions/ULTIMA_EXE/`.
- The night-time rotating beacon, its source harvest, its inverted light gate,
  its sixteen-bearing stencil plate and its per-turn cadence —
  `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: the identification of that scratch block as beacon state
  rather than moongate state, the complete writer census behind it, and the
  correction of the light gate are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- The visibility-grid writer scan proving the renderer is read-only on the
  eleven-by-eleven grid and that zero cells are compositor-owned -
  `u5-decomp/notes/visibility_grid_zeroing_2026-05-08.md`.
- The fog post-pass — squared-distance marker toggling, active-object compositing, and compositor-owned visibility-grid zeroing for cells that need terrain refetch — `u5-decomp/functions/ULTIMA_EXE/` and `u5-decomp/notes/visibility_grid_zeroing_2026-05-08.md`.
- The 6×6 folded squared-distance helper used by the fog post-pass — `u5-decomp/functions/ULTIMA_EXE/`. Combat AI target scoring uses a separate computed range primitive covered in `systems/combat.md`.
- The redraw orchestrator that calls the producer on dirty frames, takes the cheap path on clean frames, blat-copies the combat terrain on combat frames, and clears the dirty flag after the producer returns — `u5-decomp/functions/ULTIMA_EXE/`.
- The world-tile getter that dispatches between combat, overworld 2×2 chunk window, and town/dungeon-explore single-grid buffers, including the out-of-bounds sentinel — `u5-decomp/functions/ULTIMA_EXE/`.
- The default active-object compositor helper and its 0..3 variant selector -
  `u5-decomp/functions/ULTIMA_EXE/`. Both filenames
  predate their naming corrections: neither routine spawns monsters and neither
  is combat-scoped or class-related; the second returns the variant index used
  by the first.
- The cross-overlay alias and callsite census for the same world-tile getter -- `u5-decomp/functions/ULTIMA_EXE/`.
- The overworld map family's chunk layout (BRIT.DAT sparse, UNDER.DAT dense), the four-class location-DAT format, and the combat arena format that combat pre-composites — `u5-decomp/formats/maps.md`.
- The resident data segment's fixed locations for the visibility grid, the terrain band, and the per-cell scrap regions — `u5-decomp/formats/data-ovl.md`.
- The visibility-system analysis notebook from the companion-app project, used as a starting reference for buffer addresses, scene-to-routine map, and the asynchronous-read race observations — `ninth-virtue/docs/visibility-re.md:11-352`.
- The spell/potion visibility sweep's use of the negative sentinel, and with it
  the reachability of the full-fill branch and the withdrawal of the
  threshold-32 reading of the White potion (R318, R327). Source provenance:
  derived from private analysis note
  `u5-decomp/notes/2026-09-02_issue-180_blocking-presentation-world-step-census.md`.
  **What that pass leaves open for this document.** It established two things
  about the producer's argument handling: the light value a caller supplies is
  what *selects* which of the three branches runs, and the literal the producer
  hands down to its carve helper is hard-coded **inside the producer** and is
  identical for every caller. It did **not** re-derive whether the caller's light
  value *also* reaches the carve as a distance threshold; the routine that would
  carry a genuine distance or line-of-sight rule was not read. Section 3's
  positive-value row and Section 4's per-threshold cell counts therefore stand
  **un-rechecked** by this work rather than re-confirmed by it. They are not
  withdrawn and no evidence against them was found, but an implementation that
  depends on the exact per-threshold cell sets should treat them as awaiting
  their own derivation rather than as corroborated by issue #180.
