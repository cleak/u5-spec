# Location DAT files

Format specification for the four shared per-class location files: `TOWNE.DAT`, `DWELLING.DAT`, `CASTLE.DAT`, and `KEEP.DAT`. These hold the interior tile grids for every named non-overworld location in the game — towns, villages, hamlets, dwellings, castles, keeps. Also covers the small `MISCMAPS.DAT` file associated with intro and cutscene screens. The overworld surface files (`BRIT.DAT`, `UNDER.DAT`) and the dungeon-level file (`DUNGEON.DAT`) are out of scope here; see their dedicated format specs.

## 1. Overview

The world has thirty-two named non-overworld locations. Each is a small interior grid of one-byte tile indices, thirty-two cells wide by thirty-two cells tall, optionally with further floors of identical dimensions above it, below it, or both. The grids are stored in four files of identical format and identical size, eight locations per file, partitioned by location class. Locations have between one and five floors; the shipped distribution is thirteen one-floor locations, ten two-floor, seven three-floor, and two five-floor. A separate, small file (`MISCMAPS.DAT`) holds small cutscene maps plus the map strips and command stream for the intro Return-to-View preview.

The location files are paired one-for-one with their per-class NPC roster files (`*.NPC`) and per-class dialogue files (`*.TLK`); see the NPC and TLK format specs. The town-mode runtime resolves the active file from a single *scene byte* and reads the location's tile data into a working buffer in resident memory, where it is consumed by the renderer and walked at load time to harvest NPC start positions, spawn coordinates, and conditional map markers.

Each location file is exactly 16,384 bytes — a flat array of sixteen 1,024-byte *floor pages* numbered `0` through `15`, each page one complete thirty-two-by-thirty-two tile grid. There is no per-location header, no per-floor header, and no padding or alignment within any of the four files. The eight-locations-per-file split is a naming and roster convention, not a page-ownership rule: each location owns a *run* of one to five consecutive pages, and those runs do not all begin on an even page. Section 4.1 publishes the complete scene-to-page binding, and Section 4.2 publishes the reachable floor range of every location. The tile encoding is uniform across the four files; the four-way split exists for reasons of disk and engine memory layout, not because the file formats differ.

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

Within a class, the location's *roster* index is `(scene − 1) & 7`. That index selects the location's block in the class `.NPC` and `.TLK` files. It does **not** select the location's tile pages in the class `.DAT` file; those come from the per-scene base-page binding of Section 4.1. The engine resolves the file family by `(scene − 1) >> 3` against a four-entry pointer table whose four entries name `TOWNE.DAT`, `DWELLING.DAT`, `CASTLE.DAT`, and `KEEP.DAT` in that order; the resulting filename is opened and exactly one 1,024-byte page is read.

The four-way split is engine-side bookkeeping, not user-facing. The shipping data could equally well live in a single 65,536-byte file; the four files exist because the engine groups its disk I/O and its NPC-loading code by class. From a format-reader's perspective the four files are interchangeable, and a tool that wants to enumerate every interior in the game simply reads all four end-to-end.

The pairing between the roster files is one-for-one: the NPC block at index *k* in `TOWNE.NPC` corresponds to the dialogue block at index *k* in `TOWNE.TLK`, and the same holds for `DWELLING.*`, `CASTLE.*`, and `KEEP.*`. The `.DAT` file is the exception: its unit is the 1,024-byte page, not the roster index, and the page run belonging to roster index *k* is given by Section 4.1.

## 3. Per-file structure

Every file is exactly 16,384 bytes and contains exactly sixteen floor pages of 1,024 bytes each, in order:

| Page index | File offset (bytes) | Length (bytes) | Content                  |
|-----------:|--------------------:|---------------:|--------------------------|
| 0          |                   0 |          1,024 | One 32×32 tile grid      |
| 1          |               1,024 |          1,024 | One 32×32 tile grid      |
| 2          |               2,048 |          1,024 | One 32×32 tile grid      |
| …          |                   … |          1,024 | …                        |
| 15         |              15,360 |          1,024 | One 32×32 tile grid      |

The page at index *p* begins at file offset `p × 1024`. There are no inter-page headers, footers, separators, or padding, and every one of the sixteen pages of every one of the four files is authored content owned by exactly one location.

Older readings of this format — including earlier revisions of this document — described the file as eight 2,048-byte per-location blocks, each block a pair of floors. **That pairing is an authoring artifact and is withdrawn as a runtime model.** No runtime path reads a 2,048-byte unit, and page ownership does not respect the pairing: seven locations own a run of three pages and two own a run of five, nine of the thirty-two runs cross a 2,048-byte boundary, and one town's ground floor is the *second* page of a pair rather than the first. The 2,048-byte figure survives only as an observation about how the shipped data happens to group, and a decoder should not use it.

A simple viewer that wants to paint every interior of a class can open the class file and paint all sixteen pages end to end. A viewer that wants to present them *as locations* — or any game-compatible loader — must use the per-scene base-page binding in Section 4.1, because the *k*-th location of a class does not in general start at page `2k`.

The mapping from roster index to in-game location name lives in the
DATA.OVL-derived world-location table; see `catalogs/gazetteer.md` and
`formats/npc.md` for the public scene-to-key binding. The on-disk format
preserves only ordering, not naming.

## 4. Per-location structure

A floor page has no header. Its 1,024 bytes are a flat row-major grid of one-byte tile indices, thirty-two columns wide and thirty-two rows tall. Cell `(row, col)` is at page offset `row × 32 + col`. Row indices increase southward; column indices increase eastward.

A location is a *run* of consecutive pages within its class file. The run is one to five pages long. One page of the run is the location's **base page** — the floor the party stands on when it walks in from the overworld — and the rest of the run lies above it, below it, or both.

The active page is selected as:

1. Pick the class file from the scene byte: town, dwelling, castle, or keep.
2. Read that scene's base floor-page number from the resident per-scene base-page table. The value is a page index within the selected class file, not a byte offset. The table is published in Section 4.1.
3. Interpret the current floor byte as signed eight-bit: values `0..127` are non-negative floors, values `128..255` mean `value − 256`.
4. Add the signed floor to the base page and read exactly 1,024 bytes starting at `page × 1024`.

**Sign convention: a higher page index is a higher floor.** Floor `0` is the base page and the location's entry floor. Floor `+1` is the page immediately after it and is one storey up; floor `0xFF` (signed −1) is the page immediately before it and is a basement. The engine confirms the direction on screen: a transition that increases the floor byte prints `Up!` and a transition that decreases it prints `Down!`. An implementation that inverts this will place every basement above its ground floor.

Nothing in the format constrains the base page to an even index, and it is not derivable from the scene byte. In the shipped data twenty of the thirty-two locations have a base page that is *not* twice their roster index, so `location_index × 2 + floor` is wrong for the majority of locations, not for an exotic minority. The table in Section 4.1 is the only correct source.

### 4.1 Per-scene base floor-page table

The resident table is indexed by the raw scene byte and holds one page index per location. Slot zero corresponds to the overworld and is never consulted by this path. Scene bytes above thirty-two are not part of this table at all; the dungeon scene rows dispatch to dungeon mode and a different file.

The complete binding for the shipped DOS data. "Base page" is the page loaded when the floor byte is zero; "page run" is the set of pages the location owns; "floor range" is the set of signed floor values that address them.

| Scene | Location | Class file | Base page | Page run | Floor range |
|------:|----------|------------|----------:|----------|-------------|
| 1  | Moonglow | `TOWNE.DAT` | 0 | 0–1 | 0, +1 |
| 2  | Britain | `TOWNE.DAT` | 2 | 2–3 | 0, +1 |
| 3  | Jhelom | `TOWNE.DAT` | 4 | 4–5 | 0, +1 |
| 4  | Yew | `TOWNE.DAT` | **7** | 6–7 | −1, 0 |
| 5  | Minoc | `TOWNE.DAT` | 8 | 8–9 | 0, +1 |
| 6  | Trinsic | `TOWNE.DAT` | 10 | 10–11 | 0, +1 |
| 7  | Skara Brae | `TOWNE.DAT` | 12 | 12–13 | 0, +1 |
| 8  | New Magincia | `TOWNE.DAT` | 14 | 14–15 | 0, +1 |
| 9  | Fogsbane | `DWELLING.DAT` | 0 | 0–2 | 0, +1, +2 |
| 10 | Stormcrow | `DWELLING.DAT` | 3 | 3–5 | 0, +1, +2 |
| 11 | Greyhaven | `DWELLING.DAT` | 6 | 6–8 | 0, +1, +2 |
| 12 | Waveguide | `DWELLING.DAT` | 9 | 9–11 | 0, +1, +2 |
| 13 | Iolo's Hut | `DWELLING.DAT` | **12** | 12 | 0 |
| 14 | `DWELLING:5` (blank resident name) | `DWELLING.DAT` | 13 | 13 | 0 |
| 15 | `DWELLING:6` (blank resident name) | `DWELLING.DAT` | 14 | 14 | 0 |
| 16 | `DWELLING:7` (blank resident name) | `DWELLING.DAT` | 15 | 15 | 0 |
| 17 | Lord British's Castle | `CASTLE.DAT` | **1** | 0–4 | −1 … +3 |
| 18 | Lord Blackthorn's Castle | `CASTLE.DAT` | **6** | 5–9 | −1 … +3 |
| 19 | West Britanny | `CASTLE.DAT` | 10 | 10 | 0 |
| 20 | North Britanny | `CASTLE.DAT` | 11 | 11 | 0 |
| 21 | East Britanny | `CASTLE.DAT` | 12 | 12 | 0 |
| 22 | Paws | `CASTLE.DAT` | 13 | 13 | 0 |
| 23 | Cove | `CASTLE.DAT` | 14 | 14 | 0 |
| 24 | Buccaneer's Den | `CASTLE.DAT` | 15 | 15 | 0 |
| 25 | Ararat | `KEEP.DAT` | 0 | 0–1 | 0, +1 |
| 26 | Bordermarch | `KEEP.DAT` | 2 | 2–3 | 0, +1 |
| 27 | Farthing | `KEEP.DAT` | 4 | 4 | 0 |
| 28 | Windemere | `KEEP.DAT` | 5 | 5 | 0 |
| 29 | Stonegate | `KEEP.DAT` | 6 | 6 | 0 |
| 30 | The Lycaeum | `KEEP.DAT` | 7 | 7–9 | 0, +1, +2 |
| 31 | Empath Abbey | `KEEP.DAT` | 10 | 10–12 | 0, +1, +2 |
| 32 | Serpent's Hold | `KEEP.DAT` | **14** | 13–15 | −1, 0, +1 |

Names follow `catalogs/gazetteer.md` Section 5; the three dwellings whose resident name string is blank are listed by their stable storage key.

Two properties of this table are worth relying on as consistency checks:

- **The sixty-four pages partition exactly.** Every page of all four class files is claimed by exactly one location; there are no unowned pages, no shared pages, and no gaps. A decoder that reconstructs page runs from this table and finds a hole or an overlap has made an error.
- **The base page is not always the lowest page of the run.** Exactly four locations enter above the bottom of their run: Yew, both large castles, and Serpent's Hold. Every other location enters on the lowest page it owns.

The four bold rows are the ones most likely to expose a `2 × index` implementation. With that derivation Yew renders its jail instead of its town, Iolo's Hut renders a lighthouse lantern room belonging to a different dwelling, Lord British's Castle renders its own basement, and Lord Blackthorn's Castle renders a floor of Lord British's Castle entirely.

### 4.2 Reachable floors, and rederiving the page runs from assets

The floor range in Section 4.1 is not an engine constant; it is what the shipped tile data makes reachable. A tool that wants to rederive it from assets alone — or to validate a modified asset set — can do so by walking the transition cells, because a real floor link is authored on *both* pages at the same cell coordinate:

- **Ladder pairs.** Every ascend-link cell (`0xC8`) at `(x, y)` on page *p* is matched by a descend-link cell (`0xC9`) — or, in one keep, a metal grate — at the same `(x, y)` on page *p + 1*. There is no exception anywhere in the shipped data, and this signal alone reconstructs the complete run structure. Run the check in the ascend direction: the converse does not quite hold. Exactly one page in the shipped data breaks it: the top floor of Lord British's Castle (floor `+3`) carries four descend links at its tower corners, and the same four cells one floor down carry a further descend link rather than an ascend link. Those four corner descents are therefore one-way.
- **Shared staircases.** An identical stairway byte from the `0xC4..0xC7` family at the same `(x, y)` on both *p* and *p + 1* is a two-way flight between them.
- **One-way descents.** A trapdoor (`0x8C`) or a metal grate (`0x86`) on page *p + 1* paired with an ascend link on page *p* is a drop down plus a way back up. A grate can also stand in for the descend half of a ladder pair — Ararat's upper floor carries a grate at exactly the cell where its lower floor carries the ascend link.

Following those links outward from each base page yields exactly the page runs of Section 4.1, and the runs so derived tile the sixteen pages of each file with no overlap.

Two conventions a reader might mistake for structure:

- **There is no filler page.** Earlier revisions of this document said single-floor locations still occupy 2,048 bytes with one page of repeated filler tile, and that the engine relies on stairways never leading into it. **That is withdrawn.** Every page in the shipped data is authored content owned by a location. The pages that look like filler — a mostly uniform field with a small complex cut into it — are small-footprint basements and secondary levels, and they are reachable: the Yew jail, the level below Blackthorn's castle, and the level below Serpent's Hold all have that shape.
- **A one-page location has no unreachable second floor.** Locations such as Iolo's Hut own a single page and contain no stairway, ladder, grate, or trapdoor cell at all, so their floor byte never leaves zero.

## 5. Tile encoding

Every byte of a floor grid is a tile index. The renderer maps the byte through the global tile catalogue (described in the tile-graphics format spec) to a 16×16 pixel sprite drawn at the cell's position. Tile indices are flat one-byte integers; there is no class-bit, terrain-bit, or animation-bit *intrinsic* to the encoding.

Pragmatically, the tile catalogue is laid out so that tiles of the same animation set sit at consecutive indices: paired tiles whose low bit toggles between two animation phases (a flickering torch, a rippling water cell), or four-tile sets whose low two bits sweep through frames. The renderer animates by overlaying the global animation phase counter onto the tile byte's low bits at draw time. This is a *catalogue convention*, not a property of the file format: the bytes stored on disk are the canonical (phase-zero) tile indices, and the renderer's animation pass operates on the rendered output.

Within the catalogue, tiles cluster by visual class — wall tiles in one range, floor tiles in another, doors in another, water in another, special markers near the start of the printable-ASCII range. The high nibble approximately groups by class (walls, floors, water, monsters, vehicles, etc.); the low nibble approximately encodes variant or animation phase. This is a useful mnemonic for human readers but is not enforced by the renderer: any tile byte indexes any tile sprite, and the catalogue mapping is the source of truth.

Several tile values are *not* ordinary terrain at all but markers consumed by load-time passes. Section 6 covers them.

## 6. NPC start markers and the beacon light source

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

### The `0x2A` marker — corrected

**`0x2A` is not a player spawn marker. It is the night beacon's indoor light
source.** An earlier revision of this section read it as "a player spawn or
stairway-up landing point", harvested into primary and secondary spawn slots.
**That reading is withdrawn.**

Two independent lines settle it, and the first needs no code at all:

- **`0x2A` appears in zero town, castle and keep floors.** It occurs **five
  times across four floors, every one of them dwelling-class** — and those four
  are the lantern rooms of the game's four lighthouses. A player town-entry
  spawn marker that exists in no town is not a spawn marker.
- The shipped description table gives tile `0x2A` as "a bright light", which is
  what `systems/visibility.md` Section 12.6 resolves as the beacon's indoor
  source.

The load pass does harvest the byte into two coordinate slots during its single
grid walk, which is what the spawn reading was built on — but those slots are
the beacon's, not the player's. **One walk, two purposes**: the same pass also
harvests NPC start markers, and only the NPC half concerns placement.

**The harvest rule, corrected.** The walk tests only whether the *first* slot is
still empty. So the **first** hit takes slot one and, once slot one is filled,
**every later hit overwrites slot two** — meaning the **last** hit wins slot
two, not the second. No shipped floor carries three, so behaviour is unchanged
today; it matters only for custom data.

**Exactly one shipped floor carries two.** Three of the four carry one. So the
second slot is exercised in exactly one place in the whole shipped data set, and
an implementation that silently handles one source per floor is correct on three
floors and wrong on the fourth.

**Ordering cannot disarm it, and the reason matters more than the fact.** The
harvest converts tile positions into resident coordinate *words* at load time,
and the beacon never re-reads the map afterwards. A later pass that rewrites the
cell therefore cannot switch the source off. An implementation that instead
harvests from a normalised or scrubbed copy of the floor **loses this property**,
and will find the source present on one entry path and absent on another. Since
a lantern room is reached by climbing, the stairs path is the only one reachable
in play.

### Player spawn placement

**There is no asterisk-based spawn marker, and the two slots this section used
to describe are the beacon's.** Earlier revisions described a *primary* and
*secondary* spawn harvested from `0x2A` cells, with the first occurrence taking
the primary slot; they also named, and later retracted, a positional default for
when no asterisk was found. **All of that is withdrawn** - it was the beacon's
light-source harvest read as player placement, and the retracted default was a
symptom of trying to explain what happens when a marker that is not a spawn
marker is absent.

The two slots are initialised to a sentinel before the grid walk and are filled
only from `0x2A` cells, which exist on four dwelling-class floors and nowhere
else. They never carry a player position.

**Marker handling remains in-memory only** and the on-disk file is unchanged by
a load, which is the one claim from the old wording that survives intact.

This document does not specify where the player is placed on entering a
location. That is mode behaviour rather than file format, and it is **not
established here** - an implementation should not infer it from this file.

### Farmland and orchard blight in a Shadowlord hideout

Four adjacent tile values form two authored/spoiled pairs of ordinary
terrain: standing crops (`0x2D`) and its plowed-patch counterpart (`0x2C`),
and a fruit tree (`0x2E`) and its hollow-stump counterpart (`0x2B`). The
in-game look-at description table names all four, so they are visible terrain,
not markers and not route hints.

Location files store only the *full* member of each pair. A second-tier pass
scans the 32-by-32 runtime tile buffer after the load-time marker harvest and
thins them — but only in the one settlement that is currently hiding a living
Shadowlord. The pass reads the runtime record of which Shadowlord is resident
in the location being entered and returns immediately when that record says
"none", which is the ordinary case for every location in the game. A decoder or
an editor therefore never needs to model it, and an engine must not apply it as
a general harvest.

Where it does run:

- Standing crops (`0x2D`) rewrite to a plowed patch (`0x2C`) on a nonzero roll
  from `0..7`, i.e. seven times out of eight.
- A fruit tree (`0x2E`) rewrites to a hollow stump (`0x2B`) on the same
  seven-in-eight roll.

If the roll is zero the cell is left standing. The rewrite is confined to the
runtime buffer; the on-disk file is unchanged, and a decoder reading the file
always sees the full-terrain form.

The pass is bracketed by two generator seeds, not by a save and restore. Before
the scan the gameplay PRNG is seeded from the calendar day of the month, so the
result is a pure function of the day byte and the loaded floor content and is
therefore identical for every load of that floor on the same in-game day,
re-rolling when the date advances; after the scan the generator is re-seeded
from the host clock, so the previous stream position is discarded rather than
recovered. `systems/town-mode.md` section 3 owns the gate, the two call sites,
and the double application that follows an in-town floor reload;
`systems/prng.md` section 3 owns the seeding contract.

### NPC floor-link markers

Two marker values, `0xC8` and `0xC9`, participate in NPC floor-transition routing. Unlike the purely harvested placement markers above, these bytes are also consumed after map load: when an NPC needs to route between floors, the NPC pathfinder searches the live tile buffer for cells containing one selected marker ID and uses matching cells as goals.

The two values are directional and not interchangeable. `0xC8` is the ascend link (climbing while on it raises the floor index) and `0xC9` is the descend link (climbing while on it lowers the floor index); `systems/npc-schedules.md` Section 8.5 gives the scheduler's selection rule and `catalogs/tile-catalog.md` Section 6 gives the player-facing contract. They are distinct both from the visible stairway family `0xC4..0xC7` and from the town step-trigger tile `0x8C`. A location decoder should preserve the two byte values distinctly in the working tile grid until the schedule processor has had a chance to consume them.

### Runtime marker handling

Marker handling is in-memory only. The original on-disk file is unchanged. Implementations should treat marker bytes as authored annotations, not as ordinary tiles. The traced loader always harvests the NPC and asterisk markers into runtime coordinate slots; companion passes may then rewrite selected marker cells in the runtime buffer, while the NPC floor-link markers are runtime pathfinding goals. The exact visual cleanup is therefore a property of the town load and schedule pipeline rather than of the static file format alone.

## 7. Multi-floor handling

Floor changes within a location are mediated by five authored cell families. All five are ordinary tile bytes in the location grid; none of them is a separate per-location record, and none of them carries a destination — the destination is always the adjacent page in the same location's run.

| Cell family | Trigger | Floor change |
|---|---|---|
| Stairway `0xC4..0xC7` | Walking onto the cell | ±1, direction from the approach |
| Ascend link `0xC8` | The climb command, while standing on it | +1 |
| Descend link `0xC9` | The climb command, while standing on it | −1 |
| Metal grate `0x86` | The climb command, while standing on it | −1 |
| Trapdoor `0x8C` | Stepping onto the cell | −1 |

The stairway family is facing-sensitive: the low two bits identify the stair's axis in the same normalized facing space the town movement wrapper uses. Entering along the authored facing moves up, entering from the opposite facing moves down, and side crossings do not change floors. Because the same stairway byte is authored at the same cell coordinate on both connected pages, a flight is two-way.

`systems/town-mode.md` Section 3 owns the player-facing contract for all five, including the on-screen text and the one location where the trapdoor is not a floor transition.

The floor-change pass updates the resident floor byte, reloads the tile buffer using the signed floor-page rule from Section 4, runs the marker harvest and dawn/dusk gate-normalization passes against the new buffer, partially resets the active-object table (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and updates the player's slot with the new Z. The schedule processor handles its own per-floor consistency through its Z-mismatch state machine described in the schedules spec.

A transition cell always has a real destination in the shipped data: the page it leads to belongs to the same location's page run, and the authored links form a single chain per location with no branch and no dead end. See Section 4.2.

## 8. Worked example — `TOWNE.DAT`, location zero

This example walks the first cell-row of the first location of `TOWNE.DAT` to illustrate the on-disk layout.

The file begins at byte zero of `TOWNE.DAT`. The first 1,024 bytes are page 0, which the base-page table of Section 4.1 assigns to the first town as its floor zero. The page is laid out row-major.

Bytes 0 through 31 (decimal) are the first row of the ground floor — the row at row index zero, columns zero through thirty-one. The bytes are tile indices, each encoding one of:

- A wall tile, painted as a solid stone or wooden barrier, blocking movement.
- A grass or dirt tile, painted as outdoor terrain, walkable.
- A floor tile, painted as interior flooring, walkable.
- A door tile, painted as a closed door, openable via the O-Open command.
- An NPC start marker (`0x48` or `0x49`), to be harvested as an NPC coordinate.
- An asterisk byte (`0x2A`) - **not** a spawn marker; it is the night beacon's
  indoor light source, and it occurs only on the four dwelling-class lantern
  floors. See the corrected subsection above.

A typical first row of an outdoor town is dominated by city-wall tiles (the town's perimeter) interspersed with a single gate tile (the entrance) and possibly an NPC start marker representing a guard standing at the gate. The asterisk is usually placed at the cell immediately inside the gate, so that the player arrives directly on the threshold.

Continuing past byte 31, the next thirty-two bytes (bytes 32 through 63) are the second row, and so on. After 1,024 bytes (the last cell of row 31, column 31) page 1 begins, which for this file is the same town's floor `+1`. Page 2, at byte 2,048, is the *next* town's floor zero — but only because this class file happens to pair its towns that way. In `DWELLING.DAT` and `CASTLE.DAT` the location boundaries fall elsewhere, so a reader must consult Section 4.1 rather than counting in 2,048-byte steps.

A reader writing a viewer can sanity-check its decoding by:

1. Reading the first 2,048 bytes of `TOWNE.DAT`, which for this class file is the whole of the first town.
2. Splitting into floor-zero and floor-one halves.
3. Painting both as 32×32 grids using the global tile catalogue.
4. Checking that the result is a recognisable rendering of the first town with internal buildings and roads.

The on-disk layout is thus simple enough that no decoder is needed — only the tile catalogue and the marker-handling rules.

## 9. Entry floors above the bottom of a page run

Most locations enter on the lowest page they own, so their floor byte only ever climbs. Four do not, and they are the reason the base page has to be published rather than derived.

The mechanism is the signed floor-page rule of Section 4: the resident table names the page for logical floor zero, and the signed floor byte is added to it. Floor `0` is the base page, floor `+1` the page after it, floor `0xFF` the page before it. When the base page is not the lowest page of the run, the pages below it are addressed with negative floor values.

| Location | Base page | Pages below the base | Pages above the base | What the lower page is |
|---|---:|---:|---:|---|
| Yew | 7 | 1 | 0 | The town jail, reached by trapdoor and grate from the town above and by the two ladder pairs back up |
| Lord British's Castle | 1 | 1 | 3 | The castle basement |
| Lord Blackthorn's Castle | 6 | 1 | 3 | A smaller-footprint level below the entry floor |
| Serpent's Hold | 14 | 1 | 1 | A small complex below the keep |

Yew is the only town-class location with a basement and the only town whose base page is odd. Both large castles are the only five-floor locations in the game, spanning floors `−1` through `+3`. Lord Blackthorn's Castle also carries the densest trapdoor layout in the game: its entry floor and the three floors above it (floors `0`, `+1`, `+2`, `+3`) hold forty-five, thirty-six, thirty, and thirty-six trapdoor cells respectively, while its basement holds none — the trapdoors all drop *into* the tower and there is nothing below the bottom. Falling a floor there is routine rather than exceptional.

Reachability remains content-driven by the transition cells of Section 7. A tool that wants to enumerate every reachable floor should combine the base-page table of Section 4.1 with the link-walking procedure of Section 4.2 rather than assuming any fixed floor count per location.

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

Four small 11-tile-wide-by-11-tile-tall grids used as background frames during cutscenes. Two runtime load paths are traced at v1 depth: the Blackthorn audience loads record 0, and the endgame sequence loads record 3 — the Lord British throne-room chamber, with a brick floor, shelved walls, a table, a chest and torches, and its four corner cells marked as outside the playable square. The middle two records share the same verified layout, but their exact scene bindings remain unnamed in this spec. The Blackthorn cutscene consumer is specified in `systems/blackthorn.md`; the endgame consumer, including the re-stride into the combat-arena terrain buffer that both cutscene consumers perform, is specified in `systems/endgame.md` section 3.1.

Each cell is a one-byte tile index drawn from the same global tile catalogue used by the location files. The on-disk row stride is sixteen bytes, with the trailing five bytes per row zero-padded — the data is laid out as if for a 16-tile-wide grid, but only the leftmost eleven columns carry tile data.

The four cutscene maps are stored back-to-back in this section: each map occupies `16 × 11 = 176` bytes, totalling 704 bytes for the four. A reader extracts the *k*-th cutscene map by skipping `k × 176` bytes from the section start, then for each of the eleven rows reading sixteen bytes and using only the first eleven.

### Return-to-View maps

Four short, wide grids - **4 rows by 19 columns** - are used by the intro menu's Return-to-View preview. The Return-to-View path loads `MISCMAPS.DAT` starting at this section and treats the first 512 bytes of the loaded buffer as four padded map strips.

**Orientation correction.** Earlier revisions of this document, and the answer originally posted on the Return-to-View issue, described each record as 4 columns by 19 rows stored as four 32-byte columns. That is transposed and is withdrawn. Each record is **four 32-byte rows**; within a row the first nineteen bytes carry tile data and the trailing thirteen bytes are unused padding. The strip is therefore wide and short, which is also what the preview displays: nineteen tiles across by four tiles down. A reader that transposes the record will place every cell wrongly and will compute a preview that cannot fit the screen.

Each Return-to-View map occupies `32 x 4 = 128` bytes, totalling 512 bytes for the four. Extraction skips `record_index x 128`, then for rows `0..3` reads a 32-byte row and uses only columns `0..18`.

Corroborating evidence in the shipped data: the command stream's own coordinate arguments span `x = 0..15` and `y = 0..3`, and it contains runs of five to eight consecutive eastward actor steps, which no four-cell-wide strip could hold.

**How much the preview actually reads.** The Return-to-View path seeks to this section's offset, 704, and requests a fixed 2,000-byte window into its scratch buffer. The shipped file has only 1,167 bytes from that offset onward — the 512 bytes of map strips plus the 655-byte command stream — so the request is short by design and satisfied in full by the file's remaining bytes. A loader must treat the short read as normal and must not require 2,000 bytes to be present. The interpreter's own command pointer is bounded by that same 2,000-byte window: reaching the bound ends the preview. The shipped stream never gets there, because it ends with the restart command.

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
- `0x0B` runs five rectangle-effect steps. Step `n` from 0 through 4 begins with a one-tick preview update, then sets the drawing colour to user-interface colour slot 1 (see `systems/display-driver.md` section 2) and emits two inclusive pixel-rectangle operations: `(128 + 9n, 152 + 3n)` to `(137 + 9n, 155 + 3n)`, followed by `(128 + 9n, 153 + 3n)` to `(137 + 9n, 156 + 3n)`. These are **absolute framebuffer pixel rectangles** on the same visible page the preview strip occupies, not cell indices; the five steps together sweep a small diagonal band across the middle of the strip. Over the five steps the two rectangles together cover `x = 128` through `x = 173` and `y = 152` through `y = 168` inclusive — note the bottom edge is `168`, from the second rectangle of the last step, not `167`. Neither rectangle aligns to a cell boundary: the pair straddles the cell edge at `x = 136` and sits inside the strip's second cell row. After the five steps, the command skips two reserved argument bytes, reads the actor slot byte, draws that actor's cell at screen tile `(actor.x, actor.y + 7)` with tile/control value zero, plays a short percussive speaker effect, and then runs a three-tick preview update. Earlier revisions described that speaker call as a short fixed resident wait; it is a sound effect whose duration is incidental, and an engine that renders silently should not model it as a timed pause.

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

The keyboard poll of step 6 happens **before** the one-tick wait, and an abort
returns from the whole tick request immediately, so the remaining iterations of
a multi-tick command are not run.

Step 8 depends only on the current strip index:

| Strip | Ambient sound per preview tick |
|---:|---|
| `0` | none |
| `1` | none |
| `2` | a random-pitch percussive speaker effect, emitted on every tick |
| `3` | a two-tone chime driven by a private counter that cycles through eight tick positions: a lower tone at position `0` and a higher tone at position `4`, silence at the other six |

The counter for strip `3` is the preview's own and advances once per preview
tick, so the chime repeats every eight ticks for as long as strip `3` is
current. An engine that renders silently can skip step 8 entirely; nothing in
the step changes the picture or the pacing.

There is **no clear of the preview area and no full-rectangle repaint**. Step 4
is a cell-granular repaint over preserved backing, so an engine that clears the
strip each frame will not match: cells outside the revealed span, and cells
marked with the sentinel, must keep whatever is already on screen.

### Return-to-View strip reveal

Loading a strip with command `0x06` does not make the whole strip visible at
once. It resets a reveal cursor whose left and right bounds both start at
**column 9**, and step 5 of each preview tick widens that span by one column on
each side on **every second tick**, stopping when the left bound reaches column
0. Because the widen happens **after** the tick's repaint, the span reaches its
full `0..18` extent at the end of the **eighteenth** preview tick, and columns
`0` and `18` are first painted on the **nineteenth**. The span then stays open
until the next `0x06`.

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
partition, page stride, per-scene base-page binding, signed floor-page rule,
row-major tile grids, marker harvest,
dawn/dusk substitution, and `MISCMAPS.DAT` sectioning are fixed. Remaining
items belong to runtime interpretation, catalog inventory, content validation,
or visual parity.

- **NPC marker low-bit semantics.** The loader matches `0x48` and `0x49` as one
  class and preserves the actual byte in the recorded start-tile array. The
  later semantic difference, if any, is still unclear. Decoders must preserve
  the exact marker byte while treating both values as the same placement marker
  for load-time harvest.

- **Filler floor convention.** Closed, and the premise was wrong. There is no
  filler page: all sixty-four pages of the four class files are authored
  content, each owned by exactly one location, and the pages that look like
  filler are small-footprint basements. Section 4.2 states the correction.

- **Reachable floor enumeration.** Closed. Section 4.1 publishes the base page,
  page run, and floor range of every one of the thirty-two locations, and
  Section 4.2 gives the link-walking procedure that rederives them from assets
  for a modified data set.

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
- The Blackthorn audience cutscene note that verifies the first cutscene-map record load from `MISCMAPS.DAT` — `u5-decomp/functions/BLCKTHRN_OVL/`.
- The endgame entry note that verifies a later cutscene-map record load from `MISCMAPS.DAT` — `u5-decomp/functions/ENDGAME_OVL/`.
- The FONT overlay overview and Return-to-View trace that bind the four 4-row by 19-column map strips plus the following command stream to the intro `R` preview path — `u5-decomp/functions/FONT_OVL/_OVERVIEW.md` and fresh local FONT helper analysis.
- The preview's framebuffer geometry, plane split, per-command tick schedule and column reveal — `u5-decomp/notes/rtv_preview_pixel_geometry_2026-08-22.md` and `u5-decomp/notes/rtv_command_schedule_and_reveal_2026-08-22.md`.
- The generic file-read helper note confirming these `.DAT` reads are plain uncompressed file slices — `u5-decomp/functions/ULTIMA_EXE/`.
- The town-mode location loader that opens the per-class file, computes the per-floor offset, reads exactly 1,024 bytes into the working buffer, and runs the marker harvest and dawn/dusk gate passes — `u5-decomp/functions/TOWN_OVL/`.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/scene_floor_page_table_2026-08-22.md`. That note supplies the
  complete per-scene base floor-page binding of Section 4.1, the sign convention
  and the on-screen text that confirms it, the exact page run and floor range of
  every location, the exhaustive sixty-four-page partition check, the inventory
  of floor-transition cell families in Section 7, the four entry-above-the-bottom
  cases of Section 9, and the withdrawal of both the two-floors-per-block runtime
  model and the filler-page convention. One reading in that note is superseded
  here: the vehicle state that suppresses the trapdoor is the magic carpet, not
  a skiff, per the closed transport-marker set in `systems/vehicles.md`
  Section 2.
- Source provenance: derived from private analysis notes
  `u5-decomp/functions/TOWN_OVL/` and
  `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md` -- the
  farmland/orchard blight, its resident-Shadowlord gate, the direction of both
  substitutions, the seven-in-eight rate, the day-of-month seed, and the clock
  re-seed that follows the pass. That note's earlier "grass/path texturing",
  "six-in-seven", "save/restore the PRNG" and "gated on the player's actor slot
  already being assigned" readings are all superseded.
- The town-mode entry orchestrator that calls the loader once per location entry and re-entry — `u5-decomp/functions/TOWN_OVL/`.
- The world-mutation primitive that links logical NPC state to active-object slots, consuming the harvested NPC start positions — `u5-decomp/functions/TOWN_OVL/`.
- The facing-sensitive town stair family and floor-change reload path -
  `u5-decomp/functions/TOWN_OVL/`, cross-checked
  against `u5-decomp/functions/TOWN_OVL/`.
- The NPC pathfinder notes that identify `0xC8` and `0xC9` as tile-ID goals in the live tile buffer, their ascend/descend identity, and the town step handler's separate `0x8C` trigger — the path-probe, flood-fill workspace and floor-transition-gate notes under `u5-decomp/functions/NPC_OVL/`, the town step-interaction note under `u5-decomp/functions/TOWN_OVL/`, `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md`, and `u5-decomp/formats/maps.md`.
- The overworld main loop providing the cross-mode contract under which the location loader is invoked, including the scene-byte-driven mode switch — `u5-decomp/functions/MAINOUT_OVL/`.
- The overworld chunk loader establishing the convention that per-class files are addressed by filename pointer through a small resident table — `u5-decomp/functions/OUTSUBS_OVL/`.
