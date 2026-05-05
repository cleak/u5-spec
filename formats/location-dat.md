# Location DAT files

Format specification for the four shared per-class location files: `TOWNE.DAT`, `DWELLING.DAT`, `CASTLE.DAT`, and `KEEP.DAT`. These hold the interior tile grids for every named non-overworld location in the game — towns, villages, hamlets, dwellings, castles, keeps. Also covers the small `MISCMAPS.DAT` file used by intro and cutscene screens. The overworld surface files (`BRIT.DAT`, `UNDER.DAT`) and the dungeon-level file (`DUNGEON.DAT`) are out of scope here; see their dedicated format specs.

## 1. Overview

The world has thirty-two named non-overworld locations. Each is a small interior grid of one-byte tile indices, thirty-two cells wide by thirty-two cells tall, optionally with a second floor of identical dimensions. The grids are stored in four files of identical format and identical size, eight locations per file, partitioned by location class. A separate, small file (`MISCMAPS.DAT`) holds three concatenated sections used by the intro and cutscene system.

The location files are paired one-for-one with their per-class NPC roster files (`*.NPC`) and per-class dialogue files (`*.TLK`); see the NPC and TLK format specs. The town-mode runtime resolves the active file from a single *scene byte* and reads the location's tile data into a working buffer in resident memory, where it is consumed by the renderer and walked once at load time to harvest NPC start positions, spawn coordinates, and waypoint hints.

Each location file is exactly 16,384 bytes — eight per-location blocks of 2,048 bytes each, every block a pair of 1,024-byte floor grids. There is no per-location header, no per-floor header, and no padding or alignment within any of the four files. The tile encoding is uniform across the four files; the four-way split exists for reasons of disk and engine memory layout, not because the file formats differ.

`MISCMAPS.DAT` is structurally unrelated despite the suggestive name — it carries small fixed-size frames used by the title and demo sequences, plus a trailing data blob whose role is not documented here.

## 2. The four files and the scene-byte partition

The thirty-two location IDs are partitioned by class:

| Scene byte range | Class    | File           |
|------------------|----------|----------------|
| 1–8              | Town     | `TOWNE.DAT`    |
| 9–16             | Dwelling | `DWELLING.DAT` |
| 17–24            | Castle   | `CASTLE.DAT`   |
| 25–32            | Keep     | `KEEP.DAT`     |

Scene byte zero is reserved for *overworld* (no per-location file is loaded). Scene bytes above thirty-two are used for dungeon and combat states (other formats).

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

There are no inter-block headers, footers, separators, or padding. The 2,048-byte stride is uniform regardless of how many of the location's floors are populated.

A reader that wants the *k*-th location of a given class opens the class file, seeks to `k × 2048`, and reads 2,048 bytes. Class-to-file mapping is given in Section 2.

The mapping from block index to in-game location name (which town is block zero of `TOWNE.DAT`?) lives in a separate per-class name table in the game's resident data segment; see the resident-data spec. The on-disk format preserves only ordering, not naming.

## 4. Per-location structure

Each per-location 2,048-byte block contains two consecutive floor grids:

| Sub-block | Offset within block | Length | Content        |
|-----------|--------------------:|-------:|----------------|
| Floor 0   |                   0 |  1,024 | Ground floor   |
| Floor 1   |               1,024 |  1,024 | Upper or basement |

There is no per-floor header. The 1,024 bytes are a flat row-major grid of one-byte tile indices, thirty-two columns wide and thirty-two rows tall. Cell `(row, col)` is at sub-block offset `row × 32 + col`. Row indices increase southward; column indices increase eastward.

Floor zero is always the floor the player arrives on. Floor one is either the upper level (most castles, keeps, multi-storey houses) or the basement (a handful of dwellings) — the convention is per-location and is encoded in the floor's tile data, not in any explicit type byte.

Locations with only one populated floor still occupy the full 2,048 bytes: the unused floor's 1,024-byte grid is filled with a single repeating tile (often the location class's default wall byte), producing a visible-but-unreachable empty room. A reader cannot distinguish a populated single-cell room from an empty filler floor by inspection alone; the game knows which floors are real because the player can only reach them through stairway tiles laid out in floor zero.

A small number of locations encode a third level by re-purposing the runtime floor index byte's high values to address other regions of the same file or of a separate per-class block. The mechanism uses the same per-floor stride and the same tile encoding; an implementation that reads only the canonical two floors per block will see the standard location and miss the secret level. Section 9 covers this in more detail.

## 5. Tile encoding

Every byte of a floor grid is a tile index. The renderer maps the byte through the global tile catalogue (described in the tile-graphics format spec) to a 16×16 pixel sprite drawn at the cell's position. Tile indices are flat one-byte integers; there is no class-bit, terrain-bit, or animation-bit *intrinsic* to the encoding.

Pragmatically, the tile catalogue is laid out so that tiles of the same animation set sit at consecutive indices: paired tiles whose low bit toggles between two animation phases (a flickering torch, a rippling water cell), or four-tile sets whose low two bits sweep through frames. The renderer animates by overlaying the global animation phase counter onto the tile byte's low bits at draw time. This is a *catalogue convention*, not a property of the file format: the bytes stored on disk are the canonical (phase-zero) tile indices, and the renderer's animation pass operates on the rendered output.

Within the catalogue, tiles cluster by visual class — wall tiles in one range, floor tiles in another, doors in another, water in another, special markers near the start of the printable-ASCII range. The high nibble approximately groups by class (walls, floors, water, monsters, vehicles, etc.); the low nibble approximately encodes variant or animation phase. This is a useful mnemonic for human readers but is not enforced by the renderer: any tile byte indexes any tile sprite, and the catalogue mapping is the source of truth.

Three specific tile values are *not* renderable terrain at all but markers consumed by the load-time pass and stripped before render. Section 6 covers them.

## 6. NPC and spawn markers

A location's tile grid carries *placement markers* — tile values that the load-time pass scans for and converts into runtime state, overwriting the marker byte with its underlying terrain tile in the working buffer. Three marker classes are recognised:

### NPC start markers

Two adjacent tile values — a paired set whose low bit is ignored — encode "an NPC starts here". The exact byte values are fixed across all four files. The load pass walks every cell of the freshly-read tile grid, and for each cell whose tile byte matches the NPC start marker (regardless of the low bit), it:

1. Records the cell's column index in the per-NPC start-X array, indexed by a sequential counter.
2. Records the cell's row index in the per-NPC start-Y array.
3. Re-reads the tile byte (yielding the marker itself, since the byte is not yet overwritten) and stores it in the per-NPC start-tile array.
4. Increments the counter.

After the walk completes, the counter holds the number of NPC start positions found. The NPC roster loader then matches per-roster-slot type bytes against per-roster-slot expected positions and populates the active-object table accordingly. The matching pass is described in the NPC roster format spec.

The low-bit distinction between the two marker values is preserved in the recorded tile-id (because the load pass stores the actual tile-byte read), but the engine does not appear to consume this distinction. It may have been intended as a facing hint or a static-versus-walker indicator; the empirical behaviour is identical for both values.

The per-NPC start-X, start-Y, and start-tile arrays each have thirty-two entries — one per slot in the per-class NPC roster, less the sentinel slot. A roster with fewer NPCs than markers, or markers without corresponding roster entries, is a content error in the source data; the load pass does not validate counts.

### Spawn markers

A single tile value — the ASCII byte for the asterisk character (decimal 42) — encodes "a player spawn or stairway-up landing point". The load pass tracks two slots: the *primary* spawn and the *secondary* spawn. The first asterisk encountered (in row-major order) fills the primary slot with `(column, row)`; the second asterisk encountered fills the secondary slot. Subsequent asterisks (if any) are silently ignored.

The primary spawn is typically the cell directly inside the location's main entrance from the overworld — the gate cell, the doorway cell, the threshold the player crosses to enter. The secondary spawn is typically the cell where the player lands after climbing a stairway from a floor above or below — i.e., the floor's stair-landing cell.

Both slots are initialised to a sentinel "no spawn" value before the walk; locations with no asterisks inherit a default per-scene spawn coordinate from a small resident table (X is hard-coded to fifteen; Y is read from a per-scene entry-Y table; floor is zero).

After the walk, the marker byte is overwritten in the working buffer with its underlying tile (most often a floor or grass tile), so the renderer never sees the asterisk.

### Waypoint hint markers

Two adjacent tile values — the ASCII bytes for the dash and the period (decimal 45 and 46) — encode per-NPC route waypoints. A second-tier load pass, gated on a "player slot known" flag, walks the same tile grid a second time looking for these markers. For each match it computes the sub-region of the grid the marker belongs to (the location is divided into a small fixed number of named sub-regions for waypoint purposes) and records the marker's coordinates in the runtime route-hint table indexed by the corresponding NPC.

The dash and period are interpreted as two distinct hint classes — typically a "main path" hint and a "side path" hint, with the schedule processor consulting the appropriate hint when an NPC needs to choose between two equally-good moves toward its scheduled waypoint. The exact heuristic is described in the NPC schedules spec.

Like the spawn marker, waypoint hint markers are stripped from the working buffer after the walk. They are also not present in every location: many locations have empty waypoint hint tables, and the schedule processor falls back to its primary waypoint-targeting algorithm.

### Marker stripping is destructive

By the time the load pass completes, the runtime tile buffer contains only ordinary terrain tiles plus the dynamic active-object sprite layer. Subsequent reads of the buffer — by the renderer, by the look handler, by collision detection — never see a marker byte. The original on-disk file is unchanged; the stripping is in-memory.

## 7. Multi-floor handling

Floor changes within a location are mediated by stairway tiles — ladders, staircases, and trapdoors. A stairway tile's value identifies it as a Z-transition trigger; the renderer paints it as a normal terrain tile, but the movement handler intercepts an attempt to walk *onto* it and triggers the floor-change pass.

The floor-change pass updates the resident floor byte (zero for ground floor, one for upper or basement, occasionally a higher value for re-purposed extra floors), reloads the tile buffer with the new floor's 1,024 bytes from the same per-location block, runs the marker harvest and dawn/dusk passes against the new buffer, partially resets the active-object table (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and updates the player's slot with the new Z. The schedule processor handles its own per-floor consistency through its Z-mismatch state machine described in the schedules spec.

Stair tile values cluster in a small range of the tile catalogue. Different stair sub-types behave differently — descending stairs versus ascending stairs versus ladders versus trapdoors. The behaviour is encoded in the global tile catalogue's tile-class table, not in the per-location file format.

A location with only one populated floor has stair tiles, if any, leading to its filler floor — visually the player can step onto the stair, but the destination floor is empty filler. Such cases are content errors in the source data; the engine does not detect them.

## 8. Worked example — `TOWNE.DAT`, location zero

This example walks the first cell-row of the first location of `TOWNE.DAT` to illustrate the on-disk layout.

The file begins at byte zero of `TOWNE.DAT`. The first 2,048 bytes are the per-location block for the first town. Within that block, bytes 0 through 1,023 are floor zero of that town, laid out row-major.

Bytes 0 through 31 (decimal) are the first row of the ground floor — the row at row index zero, columns zero through thirty-one. The bytes are tile indices, each encoding one of:

- A wall tile, painted as a solid stone or wooden barrier, blocking movement.
- A grass or dirt tile, painted as outdoor terrain, walkable.
- A floor tile, painted as interior flooring, walkable.
- A door tile, painted as a closed door, openable via the O-Open command.
- An NPC start marker (one of the paired values), to be replaced by the underlying tile after the load pass.
- An asterisk byte (decimal 42), the primary or secondary spawn marker, to be replaced after the load pass.

A typical first row of an outdoor town is dominated by city-wall tiles (the town's perimeter) interspersed with a single gate tile (the entrance) and possibly an NPC start marker representing a guard standing at the gate. The asterisk is usually placed at the cell immediately inside the gate, so that the player arrives directly on the threshold.

Continuing past byte 31, the next thirty-two bytes (bytes 32 through 63) are the second row, and so on. After 1,024 bytes (the last cell of row 31, column 31), floor one of the same town begins at byte 1,024 of the file. After 2,048 bytes the next town's per-location block begins.

A reader writing a viewer can sanity-check its decoding by:

1. Reading the first 2,048 bytes of `TOWNE.DAT`.
2. Splitting into floor-zero and floor-one halves.
3. Painting both as 32×32 grids using the global tile catalogue.
4. Checking that the result is a recognisable rendering of the first town with internal buildings and roads.

The on-disk layout is thus simple enough that no decoder is needed — only the tile catalogue and the marker stripping rules.

## 9. Re-purposed third floors

A small number of locations have a third level — typically a basement reached from the ground floor via a trapdoor while the upper level is reached from the same ground floor via a staircase. The on-disk per-location block has only two 1,024-byte floor sub-blocks; the third level is stored elsewhere.

The mechanism re-purposes the runtime floor byte's high values: floor byte zero and one address the canonical two floors of the location's own block, while higher values address per-floor sub-blocks of *another* per-location block in the same file. Which other block, and which sub-block of it, is encoded in the global location-floor-offset table in resident data — a thirty-two-entry table keyed by scene byte, giving the per-floor offset (in 1,024-byte units) within the class file from which to read the active floor.

Most scene bytes have an entry in the table that simply reads "two floors at the canonical block offset"; a handful have entries that say "ground floor at canonical block offset, upper floor at offset *k* (a different block's first sub-block)". The encoding is symmetrical: the class file is a flat array of 1,024-byte floor sub-blocks numbered 0 through 15, and any scene byte's two-or-three floors can pick any of those sixteen sub-blocks as long as the picks are consistent across the game's content.

For a reader that consumes only the canonical two-floor block per location, this is invisible: the third floor is "missing" but the location is otherwise renderable. For a tool that wants to enumerate every floor in the game, the resident floor-offset table is required.

## 10. The dawn/dusk substitution pass

After a location's floor is loaded into the working buffer and the marker pass has run, an additional *dawn/dusk substitution* pass runs *if and only if* the in-game hour is in the daytime band (5 AM through 7 PM inclusive). The pass walks every cell of the working buffer and, for each cell whose tile byte matches a specific "lit" tile value, replaces the byte with its "unlit" equivalent. The replacement is a fixed XOR against a small constant; the lit and unlit tile-encodings differ in exactly the bits the constant covers.

The on-disk format ships every floor in its *night form* (lit windows, glowing torches, illuminated lamps). The daytime substitution procedurally produces the day form; the night form is the disk format. A reader that paints the disk bytes directly will see every floor in night form regardless of the in-game hour. Engines that wish to preserve the day-versus-night distinction must either re-implement the substitution or ship pre-substituted day-form floors as a separate asset.

The exact lit-tile values matched by the substitution are a small set (typically three or four values) and the XOR constant is a single byte. Both are documented in the load-pass code; the format does not constrain them, and a content tool can extend the set by adding entries to the load pass.

The pass runs *only* on entry and re-entry. Hour transitions across the band boundary while the player is inside the location do not re-run the substitution; the visibility model handles intra-stay lighting changes through a separate mechanism described in the visibility spec.

## 11. `MISCMAPS.DAT`

`MISCMAPS.DAT` is a small file (under 2,000 bytes) carrying three concatenated sections:

| Section offset | Length (bytes) | Content                                               |
|---------------:|---------------:|-------------------------------------------------------|
|              0 |            704 | Four cutscene maps, each 11×11, padded to 16-byte rows |
|            704 |            512 | Four intro-screen maps, each 19×4, padded to 32-byte rows |
|          1,216 |            655 | Trailing data blob, role not fully documented          |

### Cutscene maps

Four small 11-tile-wide-by-11-tile-tall grids used as background frames during cutscenes. Each cell is a one-byte tile index drawn from the same global tile catalogue used by the location files. The on-disk row stride is sixteen bytes, with the trailing five bytes per row zero-padded — the data is laid out as if for a 16-tile-wide grid, but only the leftmost eleven columns carry tile data.

The four cutscene maps are stored back-to-back in this section: each map occupies `16 × 11 = 176` bytes, totalling 704 bytes for the four. A reader extracts the *k*-th cutscene map by skipping `k × 176` bytes from the section start, then for each of the eleven rows reading sixteen bytes and using only the first eleven.

### Intro-screen maps

Four wider and shorter grids — 19 tiles wide by 4 tiles tall — used as the title and demo screen layout. The on-disk row stride is thirty-two bytes, with the trailing thirteen bytes per row zero-padded; the data is laid out as if for a 32-tile-wide grid.

Each intro map occupies `32 × 4 = 128` bytes, totalling 512 bytes for the four. Extraction follows the same skip-and-read pattern as the cutscene section.

### Trailing data blob

The remaining 655 bytes are a structured but undocumented blob, likely script or sequence data consumed by the intro overlay alongside the four intro-screen maps. The first bytes look like short variable-length records, but the format has not been specified here. A reader that consumes only the first two sections will produce correct cutscene and intro-screen frames; the third section is the responsibility of the intro and demo systems.

`MISCMAPS.DAT` is structurally unrelated to the four per-class location files despite carrying small tile grids — its frame sizes are different (11×11 and 19×4 versus 32×32), its row strides include padding, and it has no per-frame two-floor pairing. The shared element is only the global tile catalogue.

## 12. Cross-references

- The town-mode entry sequence consuming this format — `systems/town-mode.md`.
- The per-class NPC roster file format — `formats/npc.md` (a separate format spec).
- The per-class dialogue file format — `formats/tlk.md` (a separate format spec).
- The global tile-index-to-sprite catalogue — `formats/tiles.md` (a separate format spec).
- The per-tile classification (walkable, openable, talk-through, exit) — the tile-catalog reference.
- The schedule processor that consumes the harvested NPC start positions and waypoint hints — `systems/npc-schedules.md`.
- The active-object table populated from harvested NPC start positions — `systems/active-objects.md`.
- The save image layout and how a saved game preserves scene byte and floor byte for re-derivation on load — `systems/save-load.md`.

## 13. Open questions

- **Exact NPC start marker tile values.** The two paired values are fixed across all four files but their byte values are not enumerated in this spec; an implementation must read the load-pass code or an equivalent reference. The low-bit distinction between the two values is preserved in the recorded tile-id but is not consumed by any subsequent stage; the intent is unclear (facing hint, static-versus-walker, future-use).

- **Exact dawn/dusk substitution table.** The set of lit-tile values matched by the substitution and the XOR constant are documented in the load-pass code but not in this format spec. They affect the visible day form of every interior; an implementer must inherit the same values to produce visually-consistent results.

- **Filler floor convention.** Single-floor locations encode their unused upper or basement as a 1,024-byte filler grid; the convention varies between repeated walls, repeated grass, and repeated empty-floor tiles. A reader cannot distinguish filler from authored content by inspection. The mapping of which scene bytes are single-floor versus two-floor is in the resident floor-offset table.

- **Re-purposed third floors.** A handful of locations have a third level stored as the first sub-block of a different per-location block in the same file. The exact set of locations with third floors and the mapping to other blocks is encoded in the resident floor-offset table, not in the on-disk file format.

- **Secret-room tile encoding.** A few locations have rooms accessible only through a Push-revealed trapdoor or a quest-flag-gated stairway. The gating lives in the global tile-class table and the per-location tile data; there is no engine-level "hidden room" feature. The exact tile values that participate are not fully enumerated here.

- **MISCMAPS section C.** The trailing 655-byte blob in `MISCMAPS.DAT` is consumed by the intro overlay; its record format has not been documented in this spec.

- **Marker-roster cross-validation.** When a location's NPC start markers and its NPC roster do not agree on count, the load pass does not detect the mismatch. A content tool that wants to audit consistency must compare the per-class NPC file's occupied-slot count against the per-class location file's marker count for each block, separately.

- **Waypoint sub-region map.** The waypoint hint pass divides each location into named sub-regions for the dash and period markers; the sub-region boundaries are encoded in the load-pass code. This is a property of the schedule processor's input format more than the location file format; a reader that does not consume waypoint hints can ignore it.

## 14. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of every map and arena file shipped with the game, including per-file size verification, the four-class location partition, the two-floor-per-block reading, the verified `MISCMAPS.DAT` section sizes, and cross-file consistency checks — `u5-decomp/formats/maps.md`.
- The town-mode location loader that opens the per-class file, computes the per-floor offset, reads exactly 1,024 bytes into the working buffer, and runs the marker harvest pass — `u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md`.
- The town-mode entry orchestrator that calls the loader once per location entry and re-entry — `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The world-mutation primitive that links logical NPC state to active-object slots, consuming the harvested NPC start positions — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The overworld main loop providing the cross-mode contract under which the location loader is invoked, including the scene-byte-driven mode switch — `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The overworld chunk loader establishing the convention that per-class files are addressed by filename pointer through a small resident table — `u5-decomp/functions/OUTSUBS_OVL/0x0098_outsubs_load_chunk.md`.
