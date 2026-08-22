# Location DAT files

Format specification for the four shared per-class location files: `TOWNE.DAT`, `DWELLING.DAT`, `CASTLE.DAT`, and `KEEP.DAT`. These hold the interior tile grids for every named non-overworld location in the game — towns, villages, hamlets, dwellings, castles, keeps. Also covers the small `MISCMAPS.DAT` file associated with intro and cutscene screens. The overworld surface files (`BRIT.DAT`, `UNDER.DAT`) and the dungeon-level file (`DUNGEON.DAT`) are out of scope here; see their dedicated format specs.

## 1. Overview

The world has thirty-two named non-overworld locations. Each is a small interior grid of one-byte tile indices, thirty-two cells wide by thirty-two cells tall, optionally with a second floor of identical dimensions. The grids are stored in four files of identical format and identical size, eight locations per file, partitioned by location class. A separate, small file (`MISCMAPS.DAT`) holds small cutscene maps plus the map strips and command stream for the intro Return-to-View preview.

The location files are paired one-for-one with their per-class NPC roster files (`*.NPC`) and per-class dialogue files (`*.TLK`); see the NPC and TLK format specs. The town-mode runtime resolves the active file from a single *scene byte* and reads the location's tile data into a working buffer in resident memory, where it is consumed by the renderer and walked at load time to harvest NPC start positions, spawn coordinates, and conditional map markers.

Each location file is exactly 16,384 bytes — eight per-location blocks of 2,048 bytes each, every block a pair of 1,024-byte floor grids. There is no per-location header, no per-floor header, and no padding or alignment within any of the four files. The tile encoding is uniform across the four files; the four-way split exists for reasons of disk and engine memory layout, not because the file formats differ.

`MISCMAPS.DAT` is structurally unrelated despite the suggestive name - it carries small fixed-size map records for cutscenes and Return-to-View layouts, plus a command stream consumed by the intro-side preview renderer.

## 2. The four files and the scene-byte partition

The thirty-two location IDs are partitioned by class:

| Scene byte range | Class    | File           |
|------------------|----------|----------------|
| 1–8              | Town     | `TOWNE.DAT`    |
| 9–16             | Dwelling | `DWELLING.DAT` |
| 17–24            | Castle   | `CASTLE.DAT`   |
| 25–32            | Keep     | `KEEP.DAT`     |

Scene byte zero is reserved for *overworld* (no per-location file is loaded). Values outside `1..32` do not select one of these per-location files; dungeon-class maps, intro/Return-to-View maps, and combat-class state are owned by other formats.

Within a class, the eight per-class blocks are addressed by `(scene − 1) & 7`. The dwelling at scene byte twelve is the fourth block of `DWELLING.DAT`; the castle at scene byte twenty is the fourth block of `CASTLE.DAT`. The engine resolves the file family by `(scene − 1) >> 3` against a four-entry pointer table; the resulting filename is opened and the per-block data is read.

The four-way split is engine-side bookkeeping, not user-facing. The shipping data could equally well live in a single 65,536-byte file; the four files exist because the engine groups its disk I/O and its NPC-loading code by class. From a format-reader's perspective the four files are interchangeable, and a tool that wants to enumerate every interior in the game simply reads all four end-to-end.

The pairing across files is one-for-one: the per-location block in `TOWNE.DAT` at index *k* corresponds to the per-location NPC block at index *k* in `TOWNE.NPC` and the per-location dialogue block at index *k* in `TOWNE.TLK`. The same is true for `DWELLING.*`, `CASTLE.*`, and `KEEP.*`.

## 3. Per-file structure

Every file is exactly 16,384 bytes and contains exactly eight per-location blocks of 2,048 bytes each, in order:

| Block index | File offset (bytes) | Length (bytes) | Content              |
|-------------|--------------------:|---------------:|----------------------|
| 0           |                   0 |          2,048 | Location 0, both floors |
| 1           |               2,048 |          2,048 | Location 1, both floors |
| 2           |               4,096 |          2,048 | Location 2, both floors |
| 3           |               6,144 |          2,048 | Location 3, both floors |
| 4           |               8,192 |          2,048 | Location 4, both floors |
| 5           |              10,240 |          2,048 | Location 5, both floors |
| 6           |              12,288 |          2,048 | Location 6, both floors |
| 7           |              14,336 |          2,048 | Location 7, both floors |

There are no inter-block headers, footers, separators, or padding. The 2,048-byte stride is the physical authoring convention, regardless of how many of the location's floors are populated.

A simple viewer that wants the *k*-th location of a given class can open the class file, seek to `k × 2048`, and read the two physically paired floors. A game-compatible loader should instead use the resident floor-page table described in Section 4, because several scenes address a floor page outside the simple two-page pair.

The mapping from block index to in-game location name lives in the
DATA.OVL-derived world-location table; see `catalogs/gazetteer.md` and
`formats/npc.md` for the public scene-to-key binding. The on-disk format
preserves only ordering, not naming.

## 4. Per-location structure

Each physical per-location 2,048-byte block contains two consecutive floor grids:

| Sub-block | Offset within block | Length | Content        |
|-----------|--------------------:|-------:|----------------|
| Floor 0   |                   0 |  1,024 | Ground floor   |
| Floor 1   |               1,024 |  1,024 | Upper or basement |

There is no per-floor header. The 1,024 bytes are a flat row-major grid of one-byte tile indices, thirty-two columns wide and thirty-two rows tall. Cell `(row, col)` is at sub-block offset `row × 32 + col`. Row indices increase southward; column indices increase eastward.

The physical first page is not always the logical ground floor for the scene. At runtime, town mode treats each class file as sixteen consecutive 1,024-byte floor pages and uses a resident per-scene base-page table to choose which page is logical floor zero.

The active page is selected as:

1. Pick the class file from the scene byte: town, dwelling, castle, or keep.
2. Read that scene's base floor-page number from the resident location-floor table. The value is a page index within the selected class file, not a byte offset.
3. Interpret the current floor byte as signed eight-bit: values `0..127` are non-negative floors, values `128..255` mean `value - 256`.
4. Add signed floor to the base page and read exactly 1,024 bytes starting at `page × 1024`.

With the normal floor byte of zero, the base page is the player's ground floor. A floor byte of one reads the next page; a floor byte of `0xFF` reads the previous page and is how basement-style floors are reached. This rule is why an implementation must not derive active-floor pages solely as `location_index × 2 + floor`.

Locations with only one populated floor still occupy the full 2,048 bytes: the unused floor's 1,024-byte grid is filled with a single repeating tile (often the location class's default wall byte), producing a visible-but-unreachable empty room. A reader cannot distinguish a populated single-cell room from an empty filler floor by inspection alone; the game knows which floors are real because the player can only reach them through stairway tiles laid out in floor zero.

A small number of locations encode an extra level by choosing a base page whose neighbouring page belongs physically to another 2,048-byte pair. The mechanism uses the same per-floor stride and the same tile encoding; an implementation that reads only the canonical two floors per block will see a plausible location and miss some reachable floors. Section 9 covers this in more detail.

## 5. Tile encoding

Every byte of a floor grid is a tile index. The renderer maps the byte through the global tile catalogue (described in the tile-graphics format spec) to a 16×16 pixel sprite drawn at the cell's position. Tile indices are flat one-byte integers; there is no class-bit, terrain-bit, or animation-bit *intrinsic* to the encoding.

Pragmatically, the tile catalogue is laid out so that tiles of the same animation set sit at consecutive indices: paired tiles whose low bit toggles between two animation phases (a flickering torch, a rippling water cell), or four-tile sets whose low two bits sweep through frames. The renderer animates by overlaying the global animation phase counter onto the tile byte's low bits at draw time. This is a *catalogue convention*, not a property of the file format: the bytes stored on disk are the canonical (phase-zero) tile indices, and the renderer's animation pass operates on the rendered output.

Within the catalogue, tiles cluster by visual class — wall tiles in one range, floor tiles in another, doors in another, water in another, special markers near the start of the printable-ASCII range. The high nibble approximately groups by class (walls, floors, water, monsters, vehicles, etc.); the low nibble approximately encodes variant or animation phase. This is a useful mnemonic for human readers but is not enforced by the renderer: any tile byte indexes any tile sprite, and the catalogue mapping is the source of truth.

Several tile values are *not* ordinary terrain at all but markers consumed by load-time passes. Section 6 covers them.

## 6. NPC and spawn markers

A location's tile grid carries authored markers — tile values that load-time or schedule-processing passes scan for and convert into runtime state, conditional tile rewrites, or pathfinding goals. The known marker classes are:

### NPC start markers

The adjacent tile values `0x48` and `0x49` encode "an NPC starts here". The load pass treats them as one paired marker class by ignoring the low bit during the match. It walks every cell of the freshly-read tile grid in loader order (column 0 north-to-south, then column 1, and so on), and for each cell whose tile byte matches either value, it:

1. Records the cell's column index in the per-NPC start-X array, indexed by a sequential counter.
2. Records the cell's row index in the per-NPC start-Y array.
3. Re-reads the tile byte (yielding the marker itself, since the byte is not yet overwritten) and stores it in the per-NPC start-tile array.
4. Increments the counter.

After the walk completes, the counter holds the number of NPC start positions found. The NPC roster loader then matches per-roster-slot type bytes against per-roster-slot expected positions and populates the active-object table accordingly. The matching pass is described in the NPC roster format spec.

The low-bit distinction between the two marker values is preserved in the recorded tile-id (because the load pass stores the actual tile-byte read), but the engine does not appear to consume this distinction. It may have been intended as a facing hint or a static-versus-walker indicator; the empirical behaviour is identical for both values.

The per-NPC start-X, start-Y, and start-tile arrays each have thirty-two entries — one per slot in the per-class NPC roster, less the sentinel slot. A roster with fewer NPCs than markers, or markers without corresponding roster entries, is a content error in the source data; the load pass does not validate counts.

### Spawn markers

A single tile value — the ASCII byte for the asterisk character (`0x2A`, decimal 42) — encodes "a player spawn or stairway-up landing point". The load pass tracks two slots: the *primary* spawn and the *secondary* spawn. The first asterisk encountered in loader order (column 0 north-to-south, then column 1, and so on) fills the primary slot with `(column, row)`; the second asterisk encountered fills the secondary slot. Subsequent asterisks (if any) are silently ignored.

The primary spawn is typically the cell directly inside the location's main entrance from the overworld — the gate cell, the doorway cell, the threshold the player crosses to enter. The secondary spawn is typically the cell where the player lands after climbing a stairway from a floor above or below — i.e., the floor's stair-landing cell.

Both slots are initialised to a sentinel "no spawn" value before the walk. Whatever default the engine uses when no asterisk was harvested is not stored in the `.DAT` file.

Earlier wording here named that default as "column fifteen, a per-scene row from the resident entry-row table, floor zero". That rule has been retracted: it is traced from the helper that installs a resident Shadowlord in a hideout town, not from any player placement (`systems/town-mode.md` Section 5 step 6 and Section 13). The player's fallback town-entry cell is currently an open item, and no part of the withdrawn rule should be implemented for the player.

The marker is harvested into runtime spawn coordinates. Any visual replacement is handled by the broader town load pipeline, not by the spawn-coordinate harvest itself.

### Farmland and orchard harvest scatter

Four adjacent tile values form two authored/harvested pairs of ordinary
terrain: standing crops (`0x2D`) and its plowed-patch counterpart (`0x2C`),
and a fruit tree (`0x2E`) and its hollow-stump counterpart (`0x2B`). The
in-game look-at description table names all four, so they are visible terrain,
not markers and not route hints.

Location files store only the *full* member of each pair. A second-tier pass,
gated on the player's actor slot already being assigned, scans the 32-by-32
runtime tile buffer after load-time marker harvest and thins them:

- Standing crops (`0x2D`) rewrite to a plowed patch (`0x2C`) on a nonzero roll
  from `0..7`, i.e. seven times out of eight.
- A fruit tree (`0x2E`) rewrites to a hollow stump (`0x2B`) on the same
  seven-in-eight roll.

If the roll is zero the cell is left standing. The rewrite is confined to the
runtime buffer; the on-disk file is unchanged, and a decoder reading the file
always sees the full-terrain form.

The pass is bracketed by two generator seeds, not by a save and restore. Before
the scan the gameplay PRNG is seeded from the calendar day of the month, so the
scatter is identical for every entry to every location on the same in-game day
and re-rolls when the date advances; after the scan the generator is re-seeded
from the host clock, so the previous stream position is discarded rather than
recovered. See `systems/prng.md` section 3 and `systems/town-mode.md` section 3.

### NPC floor-link markers

Two marker values, `0xC8` and `0xC9`, participate in NPC floor-transition routing. Unlike the purely harvested placement markers above, these bytes are also consumed after map load: when an NPC needs to route between floors, the NPC pathfinder searches the live tile buffer for cells containing one selected marker ID and uses matching cells as goals.

The two values are directional and not interchangeable. `0xC8` is the ascend link (climbing while on it raises the floor index) and `0xC9` is the descend link (climbing while on it lowers the floor index); `systems/npc-schedules.md` Section 8.5 gives the scheduler's selection rule and `catalogs/tile-catalog.md` Section 6 gives the player-facing contract. They are distinct both from the visible stairway family `0xC4..0xC7` and from the town step-trigger tile `0x8C`. A location decoder should preserve the two byte values distinctly in the working tile grid until the schedule processor has had a chance to consume them.

### Runtime marker handling

Marker handling is in-memory only. The original on-disk file is unchanged. Implementations should treat marker bytes as authored annotations, not as ordinary tiles. The traced loader always harvests the NPC and asterisk markers into runtime coordinate slots; companion passes may then rewrite selected marker cells in the runtime buffer, while the NPC floor-link markers are runtime pathfinding goals. The exact visual cleanup is therefore a property of the town load and schedule pipeline rather than of the static file format alone.

## 7. Multi-floor handling

Floor changes within a location are mediated by stairway tiles, ladders, and trapdoors. The facing-sensitive town stair family is `0xC4..0xC7`: the low two bits identify the stair facing in the same normalized facing space used by the town movement wrapper. The renderer paints these as ordinary terrain tiles, but the movement handler intercepts an attempt to walk onto them. Entering along the authored facing moves up, entering from the opposite facing moves down, and side crossings do not change floors.

The floor-change pass updates the resident floor byte, reloads the tile buffer using the signed floor-page rule from Section 4, runs the marker harvest and dawn/dusk gate-normalization passes against the new buffer, partially resets the active-object table (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and updates the player's slot with the new Z. The schedule processor handles its own per-floor consistency through its Z-mismatch state machine described in the schedules spec.

Other floor-transition sub-types, such as K-Klimb ladders and trapdoors, are also authored as tile ids in the location grid. Their command behavior is encoded in the shared tile-class/runtime tables, not in a separate per-location record.

A location with only one populated floor has stair tiles, if any, leading to its filler floor — visually the player can step onto the stair, but the destination floor is empty filler. Such cases are content errors in the source data; the engine does not detect them.

## 8. Worked example — `TOWNE.DAT`, location zero

This example walks the first cell-row of the first location of `TOWNE.DAT` to illustrate the on-disk layout.

The file begins at byte zero of `TOWNE.DAT`. The first 2,048 bytes are the per-location block for the first town. Within that block, bytes 0 through 1,023 are floor zero of that town, laid out row-major.

Bytes 0 through 31 (decimal) are the first row of the ground floor — the row at row index zero, columns zero through thirty-one. The bytes are tile indices, each encoding one of:

- A wall tile, painted as a solid stone or wooden barrier, blocking movement.
- A grass or dirt tile, painted as outdoor terrain, walkable.
- A floor tile, painted as interior flooring, walkable.
- A door tile, painted as a closed door, openable via the O-Open command.
- An NPC start marker (`0x48` or `0x49`), to be harvested as an NPC coordinate.
- An asterisk byte (`0x2A`), the primary or secondary spawn marker.

A typical first row of an outdoor town is dominated by city-wall tiles (the town's perimeter) interspersed with a single gate tile (the entrance) and possibly an NPC start marker representing a guard standing at the gate. The asterisk is usually placed at the cell immediately inside the gate, so that the player arrives directly on the threshold.

Continuing past byte 31, the next thirty-two bytes (bytes 32 through 63) are the second row, and so on. After 1,024 bytes (the last cell of row 31, column 31), floor one of the same town begins at byte 1,024 of the file. After 2,048 bytes the next town's per-location block begins.

A reader writing a viewer can sanity-check its decoding by:

1. Reading the first 2,048 bytes of `TOWNE.DAT`.
2. Splitting into floor-zero and floor-one halves.
3. Painting both as 32×32 grids using the global tile catalogue.
4. Checking that the result is a recognisable rendering of the first town with internal buildings and roads.

The on-disk layout is thus simple enough that no decoder is needed — only the tile catalogue and the marker-handling rules.

## 9. Re-purposed floor pages

A small number of locations have a floor layout that is not simply "the two pages physically paired under this scene's block." Typical cases are a basement reached from the ground floor via a trapdoor while the upper level is reached from the same ground floor via a staircase, or a scene whose ground floor is authored in the second page of one physical block.

The mechanism is the signed floor-page rule from Section 4. Each scene's resident table entry names the class-file page for logical floor zero. The current floor byte is signed and added to that base. Therefore:

- Floor `0` means the resident base page.
- Floor `1` means the page immediately after the base page.
- Floor `0xFF` means the page immediately before the base page.

The class file is a flat array of sixteen floor pages numbered `0..15`; the table values in the shipped DOS data all fall within that range. Reachability is still content-driven by stairway tiles and command handlers. A tool that wants to enumerate every reachable floor must combine the resident base-page table with the location's stair/ladder/trapdoor layout rather than assuming every scene has exactly two floors.

## 10. The dawn/dusk substitution pass

After a location's floor is loaded into the working buffer and the marker harvest has run, an additional *dawn/dusk substitution* pass may normalize gate tiles for the current hour. The pass walks every cell of the working buffer. When it sees tile `0x87`, it applies an XOR of `0xDD` to the cell immediately south of that marker (`same column, row + 1`). The maps use `0x87` as an archway/gate marker rather than as the tile that is itself rewritten.

The on-disk format ships affected gate cells in their *daytime/open* form. In the shipped data, every participating marker has paired south tile `0x44` (cobble), and the XOR pass turns it into `0x99` (portcullis). Applying the pass a second time turns `0x99` back into `0x44`. The original routine does not validate the paired byte before XORing it, so the byte-level rule is generic (`paired = paired ^ 0xDD`) even though the stock assets use only the cobble/portcullis pair.

At floor load, the pass runs if and only if the in-game hour is in the night band: hours `0..4` or `20..23`. It is skipped for hours `5..19`. A reader that paints the disk bytes directly will therefore show the daytime/open form regardless of the in-game hour. Engines that wish to preserve the original gate timing must apply the load-time normalization and also mirror the town loop's boundary toggle at hour `5` and hour `20`.

Authored maps should not place `0x87` in the bottom row unless the implementation deliberately defines bottom-edge wrapping or clamping. The original loader relies on the shipped content avoiding an out-of-grid paired rewrite.

Town mode also runs the same XOR pass against the already-loaded buffer when the normal per-turn clock update changes the hour to `5` or `20`. The pass is therefore stateful: callers should run it exactly when crossing those two boundaries, not on every daylight recompute.

## 11. `MISCMAPS.DAT`

`MISCMAPS.DAT` is a small file (under 2,000 bytes) carrying three concatenated sections:

| Section offset | Length (bytes) | Content                                               |
|---------------:|---------------:|-------------------------------------------------------|
|              0 |            704 | Four cutscene maps, each 11x11, padded to 16-byte rows |
|            704 |            512 | Four Return-to-View map strips, each 4 rows by 19 columns, stored as four 32-byte rows |
|          1,216 |            655 | Return-to-View command stream                          |

### Cutscene maps

Four small 11-tile-wide-by-11-tile-tall grids used as background frames during cutscenes. Two runtime load paths are traced at v1 depth: the Blackthorn audience loads record 0, and the endgame sequence loads record 3. The middle two records share the same verified layout, but their exact scene bindings remain unnamed in this spec. The Blackthorn cutscene consumer is specified in `systems/blackthorn.md`.

Each cell is a one-byte tile index drawn from the same global tile catalogue used by the location files. The on-disk row stride is sixteen bytes, with the trailing five bytes per row zero-padded — the data is laid out as if for a 16-tile-wide grid, but only the leftmost eleven columns carry tile data.

The four cutscene maps are stored back-to-back in this section: each map occupies `16 × 11 = 176` bytes, totalling 704 bytes for the four. A reader extracts the *k*-th cutscene map by skipping `k × 176` bytes from the section start, then for each of the eleven rows reading sixteen bytes and using only the first eleven.

### Return-to-View maps

Four short, wide grids - **4 rows by 19 columns** - are used by the intro menu's Return-to-View preview. The Return-to-View path loads `MISCMAPS.DAT` starting at this section and treats the first 512 bytes of the loaded buffer as four padded map strips.

**Orientation correction.** Earlier revisions of this document, and the answer originally posted on the Return-to-View issue, described each record as 4 columns by 19 rows stored as four 32-byte columns. That is transposed and is withdrawn. Each record is **four 32-byte rows**; within a row the first nineteen bytes carry tile data and the trailing thirteen bytes are unused padding. The strip is therefore wide and short, which is also what the preview displays: nineteen tiles across by four tiles down. A reader that transposes the record will place every cell wrongly and will compute a preview that cannot fit the screen.

Each Return-to-View map occupies `32 x 4 = 128` bytes, totalling 512 bytes for the four. Extraction skips `record_index x 128`, then for rows `0..3` reads a 32-byte row and uses only columns `0..18`.

Corroborating evidence in the shipped data: the command stream's own coordinate arguments span `x = 0..15` and `y = 0..3`, and it contains runs of five to eight consecutive eastward actor steps, which no four-cell-wide strip could hold.

### Return-to-View command stream

The remaining 655 bytes are not tile data. They form the command stream that drives the Return-to-View preview after the four map-strip records have been loaded. The preview interpreter starts at the first byte of this stream. Each command begins with one command byte followed by the fixed argument bytes shown below.

The interpreter maintains:

- a 32-slot preview actor table using the same eight-byte record shape as the normal active-object table;
- a **terrain plane** covering the strip's `19 x 4` cells, holding the currently displayed terrain byte for each cell;
- an **overlay plane** of the same shape, holding the actor sprite byte for each cell;
- a **backing plane** of the same shape, holding the untouched terrain byte so a cell can be restored after an actor leaves it;
- the current Return-to-View map-strip index;
- the reveal cursor (a left and a right column bound plus an alternating gate); and
- a single loop counter plus loop-start pointer.

A cell is drawn from its terrain byte when that byte is non-zero, and from its
overlay byte otherwise. The two planes are read with different conventions:

- A non-zero **terrain** byte is not a tile id directly. It is an index into the
  engine's animated-tile frame table, the same table the world renderer uses to
  cycle water, flags, mirrors and similar cells; the table's current entry for
  that byte is the tile actually drawn. This is why preview terrain animates on
  its own without the command stream touching it.
- An **overlay** byte selects a tile from the upper half of the tile catalogue:
  the drawn tile index is `256 + byte`.
- The reserved overlay value `0x16` means "another helper owns this cell this
  frame"; the ordinary repaint skips it. The reserved terrain value `0xFE` has
  the same meaning on the terrain plane and is used by the cell-effect commands.

Preview coordinates use the same tile coordinate convention as other 2D maps: X increases eastward and Y increases southward. Direction bytes in this stream use the dungeon-facing cardinal order: `0` north, `1` east, `2` south, `3` west.

| Command byte | Argument bytes | Name | Effect |
|---:|---|---|---|
| `0x00` | `slot, tile, x, y` | Set actor | Fill one preview actor slot. The tile byte is stored as both actor tile bytes, X/Y are copied into the actor position, and the actor is marked drawable. |
| `0x01` | `slot` | Hide actor | Clear the actor's tile bytes and drawability flag, then restore the backing-map tile at the actor's current cell into the visible buffer. |
| `0x02` | `slot, direction` | Move actor | Restore the backing tile at the actor's old cell, then move the actor one cardinal step. This command updates state only; later draw/tick commands make the new position visible. |
| `0x03` | `ticks` | Run preview tick | Run the Return-to-View animation/input tick with the supplied timing value. If the tick reports a keypress or abort condition, the preview exits. |
| `0x04` | `x, y` | Open cell effect | Cache the cell coordinate, mark that cell skipped on the terrain and backing planes, run a forward 15-step local cell effect, then write the fixed post-open tile to both planes and run a two-tick preview update. |
| `0x05` | none | Close cell effect | Reuse the coordinate cached by `0x04`, run the same local cell effect in reverse, then write the fixed post-close tile to both planes and run a two-tick preview update. |
| `0x06` | `strip` | Load map strip and caption | Render that strip's fixed chapter caption, copy one of the four 4-row by 19-column Return-to-View maps into the terrain and backing planes, remember that strip index as current, and reset the reveal cursor to the centre column. |
| `0x07` | `slot` | Temporary actor draw | Temporarily draw the actor slot through the preview actor renderer using an alternate marker tile, then restore the actor's original tile byte. |
| `0x08` | `slot` | Temporary actor draw over backing | Variant of `0x07` that draws the temporary actor over the backing-map tile at its current cell, then restores the actor's original tile byte. |
| `0x09` | none | Restart stream | Reset the command pointer to the first byte of the command stream. The shipped stream ends with this command, so the Return-to-View scene loops until interrupted. |
| `0x0A` | `tile, x, y` | Set map cell | Write a tile byte to one preview map cell in both the visible and backing buffers. |
| `0x0B` | `reserved0, reserved1, slot` | Fixed wipe and actor draw | Run a fixed five-step rectangle/wipe effect, skip two reserved bytes, draw the named actor slot's cell at its current position, play a short percussive sound effect, then run a three-tick preview update. The first two argument bytes are present in the shipped stream but are not consumed by the traced interpreter. |
| `0x0C` | none | Clear actors | Clear tile and drawability bytes for all thirty-two preview actor slots. |
| `0x0D` | `slot, direction` | Move actor and tick | Restore the backing tile at the actor's old cell, move the actor one cardinal step, then run a **seven-tick** preview update. If the tick reports a keypress or abort condition, the preview exits. |
| `0x0E` | `count` | Loop start | Store a loop count and remember the command immediately after this one as the loop body start. |
| `0x0F` | none | Loop end | Decrement the active loop count. If it is still non-zero, continue from the saved loop-body start; otherwise continue after this command. |

Several visually complex commands have fixed script-level schedules:

- `0x06` is the only chapter-caption trigger. The command has no text payload:
  the one-byte strip argument selects both the map strip and a fixed caption
  string from the intro text table.

| Strip argument | Caption |
|---:|---|
| `0` | The Summoning |
| `1` | The Journey |
| `2` | The Arrival |
| `3` | The Welcoming |

- `0x04` writes the sentinel tile `0xFE` to the target cell in both tile buffers, then runs the local cell-effect renderer at screen tile `(x, y + 7)` for steps 1 through 15. Each step is followed by a one-tick preview update that may abort the preview. If all steps complete, the command writes tile `0xDC` to the cell in both buffers and runs a two-tick preview update.
- `0x05` reuses the coordinate cached by `0x04`, writes `0xFE` to the cell in both buffers, and runs the same local cell-effect renderer at `(x, y + 7)` for steps 15 down through 1. Each step is followed by a one-tick preview update that may abort the preview. If all steps complete, the command writes tile `0x05` to the cell in both buffers and runs a two-tick preview update.
- `0x07` and `0x08` temporarily replace the actor slot's two tile bytes with the `0x16` suppression sentinel so the ordinary repaint leaves the cell alone, draw the actor's cell through the **single-cell dissolve helper** at screen tile `(actor.x, actor.y + 7)`, then restore the original actor tile bytes. The helper is the driver's pseudo-random pixel-dissolve entry driven one cell at a time: it converges the cell to the requested tile over a fixed run of small steps, polling the keyboard roughly every eighth step, and reports an abort that ends the preview. `0x07` passes the actor's own sprite, which is an overlay-plane value and so selects tile index `256 + byte`; `0x08` passes the backing-plane terrain byte at the actor's current cell instead, used as an ordinary terrain value, which is how an actor is dissolved away rather than in.
- `0x0B` runs five rectangle-effect steps. Step `n` from 0 through 4 begins with a one-tick preview update, then sets the drawing colour to user-interface colour slot 1 (see `systems/display-driver.md` section 2) and emits two inclusive pixel-rectangle operations: `(128 + 9n, 152 + 3n)` to `(137 + 9n, 155 + 3n)`, followed by `(128 + 9n, 153 + 3n)` to `(137 + 9n, 156 + 3n)`. These are **absolute framebuffer pixel rectangles** on the same visible page the preview strip occupies, not cell indices; the five steps together sweep a small diagonal band across the middle of the strip. After the five steps, the command skips two reserved argument bytes, reads the actor slot byte, draws that actor's cell at screen tile `(actor.x, actor.y + 7)` with tile/control value zero, plays a short percussive speaker effect, and then runs a three-tick preview update. Earlier revisions described that speaker call as a short fixed resident wait; it is a sound effect whose duration is incidental, and an engine that renders silently should not model it as a timed pause.

Command bytes above `0x0F` are treated as one-byte no-ops by the traced interpreter: they are skipped after the normal input poll. There is no separate caption opcode and no length-prefixed caption payload in the shipped stream.

### Return-to-View preview geometry

The preview is drawn with the ordinary 16-by-16 viewport tile blitter, on the
same visible page as the intro menu, with the viewport's pixel origin
temporarily moved. There is no miniature raster, no scaled cell path, no
cropping and no clipping.

| Quantity | Value |
|---|---|
| Cell size | 16 x 16 pixels, from the shared tile archive |
| Viewport pixel origin during the preview | `(8, 16)` |
| Screen tile row for strip row `y` | `y + 7`, giving rows `7..10` |
| Screen tile column for strip column `x` | `x`, giving columns `0..18` |
| Pixel position of a cell | `(8 + 16x, 16 + 16(y + 7))` |
| Occupied rectangle | inclusive `(8, 128)..(311, 191)`, i.e. 304 x 64 pixels |

That rectangle is exactly the interior of the intro menu's lower text window,
so the preview replaces the menu labels while it runs and the window frame
stays visible around it. The upper part of the screen, the banner logo and the
idle animation band, is untouched.

The `+ 7` in the published `(x, y + 7)` rule is therefore an offset on the
**row** axis, applied to the 0..3 axis of the strip. It is not an offset on the
19-wide axis. Outside the preview the viewport origin is `(8, 8)`; the preview
lowers the strip by one cell row and the intro restores the origin on exit.

### Return-to-View preview tick

Every preview tick mentioned in the command table is one iteration of a single
shared routine, and commands differ only in how many iterations they request.
One iteration does the following, in order:

1. Advance the engine's animated-tile frame table and active-object animation
   by one step. This is what makes preview terrain cycle.
2. Fire one intro title tick, so the menu's idle animation band keeps moving
   while the preview owns the lower window.
3. Scatter the preview actor table into the planes: for every drawable actor,
   clear the terrain byte at its cell and write its sprite byte into the
   overlay byte at that cell.
4. Repaint the cells inside the currently revealed column span, four rows at a
   time, skipping any cell whose terrain byte is the `0xFE` sentinel.
5. Advance the reveal cursor, as described below.
6. Poll the keyboard once. Any pending key aborts the preview immediately; the
   caller restores the saved title/menu image and returns to the menu.
7. Wait one hardware tick, per `systems/timing.md` section 5.
8. Run the current strip's ambient sound step, if that strip has one.

There is **no clear of the preview area and no full-rectangle repaint**. Step 4
is a cell-granular repaint over preserved backing, so an engine that clears the
strip each frame will not match: cells outside the revealed span, and cells
marked with the sentinel, must keep whatever is already on screen.

### Return-to-View strip reveal

Loading a strip with command `0x06` does not make the whole strip visible at
once. It resets a reveal cursor whose left and right bounds both start at
**column 9**, and step 5 of each preview tick widens that span by one column on
each side on **every second tick**, stopping when the left bound reaches column
0. The full `0..18` span is therefore exposed after **eighteen preview ticks**
and stays exposed until the next `0x06`.

| Preview ticks elapsed | Columns painted |
|---:|---|
| 1-2 | 9 |
| 3-4 | 8..10 |
| 5-6 | 7..11 |
| ... | widening one column on each side every second tick |
| 17-18 | 1..17 |
| 19 and later | 0..18 |

**Correction.** An earlier revision of the public spec retracted the outward
reveal as stale, non-normative prose. That retraction was wrong in substance
and is itself withdrawn: the reveal exists and is normative. What was wrong in
the original prose was only its axis. The strip opens outward from its centre
**column**, not from a middle row, and all four rows of a revealed column
appear together. The reveal is a property of the repaint cursor, not of the
plane contents: command `0x06` fills the planes completely and immediately, and
the cursor controls only which columns are repainted onto the screen.

Because the reveal advances only inside a preview tick, a strip load followed
by commands that request few ticks will still be part-way revealed when the
next beat starts. That is the original behaviour and should not be corrected by
revealing the strip eagerly.

A reader that consumes only maps can still extract every tile record described above, but an asset-compatible intro preview needs both the four map strips and this command stream. Tools that do not implement the preview script should preserve the entire stream byte-for-byte when unpacking or repacking `MISCMAPS.DAT`.

`MISCMAPS.DAT` is structurally unrelated to the four per-class location files despite carrying small tile grids — its frame sizes are different (11 by 11, and 19 columns by 4 rows, versus 32 by 32), its strides include padding, and it has no per-frame two-floor pairing. The shared element is only the global tile catalogue.

## 12. Cross-references

- The town-mode entry sequence consuming this format — `systems/town-mode.md`.
- The per-class NPC roster file format — `formats/npc.md` (a separate format spec).
- The per-class dialogue file format — `formats/tlk.md` (a separate format spec).
- The global tile-index-to-sprite catalogue — `formats/tiles.md` (a separate format spec).
- The per-tile classification (walkable, openable, talk-through, exit) — the tile-catalog reference.
- The schedule processor that consumes the harvested NPC start positions — `systems/npc-schedules.md`.
- The active-object table populated from harvested NPC start positions — `systems/active-objects.md`.
- The save image layout and how a saved game preserves scene byte and floor byte for re-derivation on load — `systems/save-load.md`.

## 13. Format Boundary And Runtime Work

The per-class location file contract is complete at byte-layout depth: file
partition, block stride, floor-page rule, row-major tile grids, marker harvest,
dawn/dusk substitution, and `MISCMAPS.DAT` sectioning are fixed. Remaining
items belong to runtime interpretation, catalog inventory, content validation,
or visual parity.

- **NPC marker low-bit semantics.** The loader matches `0x48` and `0x49` as one
  class and preserves the actual byte in the recorded start-tile array. The
  later semantic difference, if any, is still unclear. Decoders must preserve
  the exact marker byte while treating both values as the same placement marker
  for load-time harvest.

- **Filler floor convention.** Single-floor locations encode their unused upper
  or basement as a 1,024-byte filler grid; the convention varies between
  repeated walls, repeated grass, and repeated empty-floor tiles. A reader
  cannot distinguish filler from authored content by inspection. Reachability
  is determined by stairway content and by the resident base-page table.

- **Reachable floor enumeration.** The floor-page selection rule is known, but
  the exact set of floors reachable in shipped content is catalog work best
  derived by walking each location's transition tiles rather than by trusting
  physical block pairs.

- **Secret-room tile encoding.** A few locations have rooms accessible only
  through a Push-revealed trapdoor or a quest-flag-gated stairway. The gating
  lives in the global tile-class table and the per-location tile data; there is
  no engine-level "hidden room" feature. The exact tile values that participate
  belong to the tile catalog and quest/runtime specs.

- **Return-to-View resident helper internals.** Closed. The command-byte table,
  argument shapes, actor/map side effects, local cell-effect step loops, fixed
  rectangle sequence, preview tick counts, strip orientation, framebuffer
  geometry, per-frame repaint policy, and column reveal are all specified in
  section 11. The three helpers the commands call are ordinary published driver
  entries: the 16-by-16 viewport tile blitter for cells and actors, the
  animated-terrain shimmer entry for the local cell effect, and the
  pixel-dissolve entry driven one cell at a time for the temporary actor draws.
  The only residual is the shimmer entry's exact per-step pixel pattern, which
  is a driver-internal raster question tracked in
  `systems/display-driver-abi.md`, not a format question.

- **Marker-roster cross-validation.** When a location's NPC start markers and
  its NPC roster do not agree on count, the load pass does not detect the
  mismatch. A content tool that wants to audit consistency must compare the
  per-class NPC file's occupied-slot count against the per-class location
  file's marker count for each block, separately.

## 14. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of every map and arena file shipped with the game, including per-file size verification, the four-class location partition, the two-floor-per-block reading, the verified `MISCMAPS.DAT` section sizes, and cross-file consistency checks — `u5-decomp/formats/maps.md`.
- The Blackthorn audience cutscene note that verifies the first cutscene-map record load from `MISCMAPS.DAT` — `u5-decomp/functions/BLCKTHRN_OVL/0x060E_blackthorn_audience.md`.
- The endgame entry note that verifies a later cutscene-map record load from `MISCMAPS.DAT` — `u5-decomp/functions/ENDGAME_OVL/0x0648_endgame_entry.md`.
- The FONT overlay overview and Return-to-View trace that bind the four 4-row by 19-column map strips plus the following command stream to the intro `R` preview path — `u5-decomp/functions/FONT_OVL/_OVERVIEW.md` and fresh local FONT helper analysis.
- The preview's framebuffer geometry, plane split, per-command tick schedule and column reveal — `u5-decomp/notes/rtv_preview_pixel_geometry_2026-08-22.md` and `u5-decomp/notes/rtv_command_schedule_and_reveal_2026-08-22.md`.
- The generic file-read helper note confirming these `.DAT` reads are plain uncompressed file slices — `u5-decomp/functions/ULTIMA_EXE/0x7234_read_file_seek.md`.
- The town-mode location loader that opens the per-class file, computes the per-floor offset, reads exactly 1,024 bytes into the working buffer, and runs the marker harvest and dawn/dusk gate passes — `u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md`.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/TOWN_OVL/0x0212_town_load_npc_waypoints.md` -- the
  farmland/orchard harvest scatter, the direction of both substitutions, the
  seven-in-eight rate, the day-of-month seed, and the clock re-seed that
  follows the pass. That note's earlier "grass/path texturing", "six-in-seven"
  and "save/restore the PRNG" readings are superseded.
- The town-mode entry orchestrator that calls the loader once per location entry and re-entry — `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The world-mutation primitive that links logical NPC state to active-object slots, consuming the harvested NPC start positions — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The facing-sensitive town stair family and floor-change reload path -
  `u5-decomp/functions/TOWN_OVL/0x052E_town_movement_log.md`, cross-checked
  against `u5-decomp/functions/TOWN_OVL/0x0600_town_movement_handler.md`.
- The NPC pathfinder notes that identify `0xC8` and `0xC9` as tile-ID goals in the live tile buffer, their ascend/descend identity, and the town step handler's separate `0x8C` trigger — `u5-decomp/functions/NPC_OVL/0x01A0_npc_path_probe.md`, `u5-decomp/functions/NPC_OVL/0x01D2_npc_floodfill_workspace_prep.md`, `u5-decomp/functions/NPC_OVL/0x0A4A_npc_floor_transition_gate.md`, `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md`, `u5-decomp/functions/TOWN_OVL/0x0F02_town_step_interaction.md`, and `u5-decomp/formats/maps.md`.
- The overworld main loop providing the cross-mode contract under which the location loader is invoked, including the scene-byte-driven mode switch — `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The overworld chunk loader establishing the convention that per-class files are addressed by filename pointer through a small resident table — `u5-decomp/functions/OUTSUBS_OVL/0x0098_outsubs_load_chunk.md`.
