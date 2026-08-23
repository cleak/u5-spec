# NPC files

Format specification for the four shared per-class NPC roster files: `TOWNE.NPC`, `DWELLING.NPC`, `CASTLE.NPC`, and `KEEP.NPC`. These hold the daily schedule, behaviour mode, role tag, and dialogue index for every speaking NPC in the game's named non-overworld locations. Each file is exactly four thousand six hundred eight bytes and contains eight per-location sub-maps of identical layout. The format is uniform across the four files; only the per-location content differs.

## 1. Overview

Ultima V's named non-overworld world has thirty-two locations: eight towns, eight dwellings, eight castles, and eight keeps. Every location is populated by a small cast of NPCs who walk a daily routine — the baker behind the counter at noon, the guard at his post, the old man on his bench in the evening, the child in his bed at night. The schedule for each NPC's day is data, not code: it lives in the `.NPC` files described here, and is interpreted at runtime by the per-tick schedule processor.

The four files partition by location class, mirroring the same partition used by the location data files (`*.DAT`) and the dialogue files (`*.TLK`). One `.NPC` file holds eight locations; one location's worth of NPC data is a *sub-map* of fixed size. Within a sub-map, the cast is laid out as a fixed-size array of NPC slots; within an NPC slot, fields are at fixed offsets. There are no length prefixes, no per-NPC variable-size fields, no padding, and no version word. A reader navigates a `.NPC` file by arithmetic alone.

Each NPC's record specifies three *waypoints* — three (X, Y, Z) positions on the location's map — plus four *time boundaries* that select which waypoint is active at any given hour, three behaviour-mode bytes (one per waypoint), a one-byte role tag, and a one-byte dialogue index that points into the matching `.TLK` file. The schedule processor consumes this record once per game turn, advancing each NPC toward its currently active waypoint.

The four files are companions to each other: a live NPC is a row in a `.NPC` file's sub-map, possibly walking a tile grid held in the corresponding `.DAT` file, possibly speaking lines from the corresponding `.TLK` file's NPC blob. The `.NPC`-to-`.TLK` pairing is by file family (TOWNE/DWELLING/CASTLE/KEEP) and by sub-map index within that family. The `.DAT` pairing is by family only: which page of the class file a location occupies comes from the per-scene base-page table in `formats/location-dat.md` Section 4.1, not from the sub-map index.

## 2. The four files and the scene-byte partition

The class-to-file mapping mirrors the `.DAT` and `.TLK` partition exactly:

| Scene byte range | Class    | File           |
|------------------|----------|----------------|
| 1–8              | Town     | `TOWNE.NPC`    |
| 9–16             | Dwelling | `DWELLING.NPC` |
| 17–24            | Castle   | `CASTLE.NPC`   |
| 25–32            | Keep     | `KEEP.NPC`     |

Scene byte zero is overworld; no `.NPC` file is loaded outdoors, because outdoor NPCs are not schedule-driven in the same way. Values outside `1..32` do not select one of the four town-style NPC roster files.

Within a class, the eight per-class sub-maps are addressed by `(scene − 1) & 7`. The runtime resolves the file family by `(scene − 1) >> 3` against a four-entry pointer table; the resulting filename is opened and the per-sub-map data is read into the resident schedule buffer.

The public scene byte remains one-based throughout gameplay. The roster loader
temporarily converts that byte to a zero-based index while selecting the file
family and sub-map block, then restores the global scene value before returning.
That scoped conversion is a loader detail, not a mode transition and not a
second persistent scene numbering scheme.

The four-way file split is engine-side bookkeeping; the four files exist because the engine groups its disk I/O and its NPC loading code by class.

## 3. Per-file structure

Every file is exactly four thousand six hundred eight bytes (`0x1200`) and contains exactly eight per-sub-map blocks of five hundred seventy-six bytes (`0x240`) each, in order:

| Sub-map index | File offset (bytes) | Length (bytes) | Content                          |
|---------------|--------------------:|---------------:|----------------------------------|
| 0             |                   0 |            576 | Sub-map 0 — schedule + type + dialog |
| 1             |                 576 |            576 | Sub-map 1 — schedule + type + dialog |
| 2             |               1,152 |            576 | Sub-map 2 — schedule + type + dialog |
| 3             |               1,728 |            576 | Sub-map 3 — schedule + type + dialog |
| 4             |               2,304 |            576 | Sub-map 4 — schedule + type + dialog |
| 5             |               2,880 |            576 | Sub-map 5 — schedule + type + dialog |
| 6             |               3,456 |            576 | Sub-map 6 — schedule + type + dialog |
| 7             |               4,032 |            576 | Sub-map 7 — schedule + type + dialog |

There are no inter-sub-map headers, footers, separators, or padding. The five-hundred-seventy-six-byte stride is uniform regardless of how many of the sub-map's NPC slots are populated.

A reader that wants the *k*-th sub-map opens the class file, seeks to `k × 576`, and reads five hundred seventy-six bytes.

## 4. Per-sub-map structure

Each five-hundred-seventy-six-byte sub-map is partitioned into three back-to-back arrays:

| Sub-block          | Offset within sub-map | Length     | Content                                             |
|--------------------|----------------------:|-----------:|-----------------------------------------------------|
| Schedule array     |                     0 |  512 bytes | Thirty-two NPC schedule records of sixteen bytes each |
| Type array         |                   512 |   32 bytes | Thirty-two NPC role tags                            |
| Dialog index array |                   544 |   32 bytes | Thirty-two NPC dialog index bytes                   |

The three arrays are *parallel*: the *n*-th schedule record corresponds to the *n*-th type byte and the *n*-th dialog index byte. NPC slot *n* is the tuple (schedule[n], type[n], dialog[n]); the engine reads the three arrays into separate working tables and only joins them by index at runtime.

Slot zero of every sub-map is reserved as an unused sentinel. The engine's per-tick walker iterates from slot one to slot thirty-one inclusive and skips slot zero entirely. Effective capacity per sub-map is therefore thirty-one NPCs, and per file is two hundred forty-eight NPCs (thirty-one times eight sub-maps); across the four files, the world's named-location NPC roster is bounded above by nine hundred ninety-two. In shipped data, slot zero's schedule record and dialog index are zero. Several shipped sub-maps carry a nonzero slot-zero type/tag byte as a structural marker; that byte is not a live NPC and is ignored by scheduling, Talk, collision, roster counts, and active-object linking.

The "empty slot" sentinel for indices one through thirty-one is `type[n] == 0`. The schedule processor uses the type byte as the slot's occupancy flag: any non-zero value means the slot is occupied; zero means the slot is unused and the schedule, type, and dialog index for that slot should be ignored.

## 5. The schedule record

Each schedule record is exactly sixteen bytes, laid out as four parallel arrays plus a trailing time array:

| Field offset | Width    | Field    | Meaning                                                              |
|--------------|----------|----------|----------------------------------------------------------------------|
| `+0x00`      | 3 bytes  | `AI[3]`  | Behaviour mode for each of the three waypoints.                      |
| `+0x03`      | 3 bytes  | `X[3]`   | Map column (0..31) for each of the three waypoints.                  |
| `+0x06`      | 3 bytes  | `Y[3]`   | Map row (0..31) for each of the three waypoints.                     |
| `+0x09`      | 3 bytes  | `Z[3]`   | Map floor for each of the three waypoints.                           |
| `+0x0C`      | 4 bytes  | `time[4]` | Four hour-of-day boundaries (each 0..23) selecting which waypoint is active. |

Every NPC has exactly *three* waypoints; the schedule cannot encode more or fewer. Time-of-day selects which waypoint is currently the NPC's destination: between `time[0]` and `time[1]` the destination is waypoint zero; between `time[1]` and `time[2]` it is waypoint one; between `time[2]` and `time[3]` it is waypoint two; between `time[3]` and (the next day's) `time[0]` it falls back to waypoint one.

A typical schedule represents a daily routine by setting the four time boundaries to the hours the NPC moves and the three waypoints to morning, afternoon, and evening positions, with the wraparound segment routing through waypoint one as the NPC's home. The engine has no concept of "weekday versus weekend"; the schedule is purely a function of the hour of the day.

### 5.1 Waypoint selection rule

The runtime rule for picking a waypoint from the four time boundaries is:

| Time-of-day range                      | Active waypoint |
|----------------------------------------|----------------:|
| `[time[0], time[1])`                   |               0 |
| `[time[1], time[2])`                   |               1 |
| `[time[2], time[3])`                   |               2 |
| `[time[3], time[0])` (wraps midnight)  |               1 |

The wraparound segment from `time[3]` back to (the next day's) `time[0]` returns waypoint one, *not* waypoint zero. This asymmetry is load-bearing: the shipping convention is that waypoint one is the NPC's home/sleep location, and the wraparound covers night-time hours when most NPCs are at home. An implementation that returned waypoint zero for the wraparound would walk every named-location NPC to the wrong place between sundown and sunrise.

The four boundary values are not required to be sorted ascending. The engine computes the active waypoint by picking the boundary whose unsigned eight-bit subtraction `current_hour − time[i]` is smallest — equivalent to "the boundary most recently passed, with midnight wraparound implicit." Most shipped schedules are sorted for legibility.

### 5.2 Coordinate fields

`X[i]` and `Y[i]` are zero-based map cell coordinates within the location's thirty-two-by-thirty-two tile grid, with X increasing eastward and Y increasing southward. Both are unsigned eight-bit values; valid range is `0..31`. Coordinates outside that range are not validated by the engine and would produce out-of-bounds reads on the location's tile buffer.

`Z[i]` is the location's floor index for waypoint *i*, stored in exactly the same encoding as the player's floor byte and read the same way: signed eight-bit, floor zero is the location's entry floor, positive values are storeys above it, and `0xFF` (signed −1) is the storey below it. `formats/location-dat.md` Section 4 owns that convention and Section 4.1 gives each location's legal floor range. Because the two fields use one encoding, the runtime's floor test is a plain byte-for-byte equality between the waypoint's `Z` and the player's floor byte — `0xFF` matches `0xFF`. Do **not** sign-extend one side of that comparison and not the other, and do not normalise `0xFF` to zero on load; either error silently relocates every basement NPC. The schedule processor performs that comparison every tick. An NPC whose active waypoint is on a different floor from the player's view enters a Z-mismatch movement state. It leaves that state either by routing to a floor-link or stairway cell on the displayed floor and surfacing there, or by being placed directly at its waypoint when neither end of the transition is on the displayed floor. `systems/npc-schedules.md` Sections 7 and 8.5 own the state set and the marker-selection rule.

The shipped waypoint `Z` alphabet is exactly five values: `0x00`, `0x01`, `0x02`, `0x03`, and `0xFF`. `0xFF` is not a sentinel, not padding, and not an out-of-range artifact — it is the basement floor and it is used by forty-one waypoints across four locations:

| Class file | Sub-map (roster index) | Location | Waypoint `Z` values present | Waypoints at `0xFF` |
|---|---:|---|---|---:|
| `TOWNE.NPC` | 3 | Yew | `0x00`, `0xFF` | 14 |
| `CASTLE.NPC` | 0 | Lord British's Castle | `0x00`, `0x01`, `0x02`, `0xFF` | 18 |
| `CASTLE.NPC` | 1 | Lord Blackthorn's Castle | `0x00`, `0x01`, `0x02`, `0x03`, `0xFF` | 8 |
| `KEEP.NPC` | 7 | Serpent's Hold | `0x00`, `0x01`, `0xFF` | 1 |

Those are precisely the four locations whose floor range starts below zero in `formats/location-dat.md` Section 4.1, which is an independent confirmation of the signed reading. Every other shipped sub-map uses only non-negative values, and no sub-map's `Z` alphabet exceeds its location's published floor range: the four lighthouse dwellings use `0x00` and `0x02` (they have no scheduled activity on their middle floor), Iolo's Hut and the other single-floor rows use `0x00` only, and the Lycaeum and Empath Abbey use `0x00` through `0x02`. The highest value that appears anywhere is `0x03`, in Lord Blackthorn's Castle.

Values outside the location's own floor range are not validated by the engine and would address a page belonging to a different location. A content tool should preserve whatever it finds; a gameplay implementation should treat any `Z` outside the range Section 4.1 gives for that scene as authored error rather than as a new floor.

### 5.3 The AI byte

Each waypoint has its own `AI[i]` byte. The byte is a per-waypoint behaviour selector: it belongs to the same waypoint tuple as `X[i]`, `Y[i]`, and `Z[i]`, and it affects what the NPC does after the time system has selected that waypoint. It does not affect which waypoint is active; the active waypoint is selected solely from `time[4]` and the current hour.

The shipped behaviour dispatcher accepts values `0..7`. Values above `7` fall
through to the no-action/default case. The public behaviour names are:

| Value | Behaviour family |
|---:|---|
| `0` | Stationary at the selected waypoint. |
| `1` | Random wander, bounded to a small radius around the waypoint. |
| `2` | Random wander without the radius bound. |
| `3` | **Flee** when the player comes within about four tiles. The only mode that moves away from the player. (Earlier revisions said "follow or shadow the player while maintaining distance"; that was inverted.) |
| `4` | Approach and attack when close enough. |
| `5` | Randomized chase with the attack-event adjacency behaviour; fully live in the dispatcher but not used by shipped roster data. |
| `6` | Guard or blocking event path. |
| `7` | Randomized chase/engage path. |

The schedule system spec describes the runtime consequences of these values.
This format spec fixes only that the byte is per-waypoint, one byte wide, and
interpreted through this `0..7` behaviour selector.

### 5.4 The time array

`time[0]` through `time[3]` are four unsigned eight-bit hour values, range `0..23`. They are read as plain bytes; the engine does not validate their range, but values above twenty-three would never select a waypoint correctly because the engine's hour clock is itself bounded `0..23`.

The time array's semantics — three waypoints, four boundaries, with wraparound through waypoint one — is described in Section 5.1.

## 6. The type byte

Each NPC slot has a one-byte type tag at offset `+0x200..+0x21F` of the sub-map (one byte per slot). The type byte serves two purposes: it acts as the slot's occupancy flag (zero = empty, non-zero = populated), and it supplies the NPC's sprite/tile classifier.

The type byte is not a packed AI or role bitfield. For ordinary visible NPCs,
the runtime sprite tile is derived by adding the byte to the NPC sprite page.
Most shipped values are multiples of four because sprite classes occupy small
runs of adjacent animation/facing frames in the tile atlas; the low bits are a
tile-frame consequence, not independent behavioural flags.

Three special values matter to the engine contract:

| Value | Meaning |
|---:|---|
| `0` | Empty slot. The scheduler skips the slot. |
| `1` | Occupied slot that uses the default human/person sprite instead of the ordinary derived sprite. |
| `0xFC` | Shadow Lord actor class. Three shipped roster slots carry it — Stonegate slots one, two and three (`KEEP.NPC` sub-map 4) — and it is also written into a live NPC slot by the town-entry Shadowlord install (`systems/town-mode.md` Section 13), which stamps the matching Shadow Lord actor tile into the linked active-object record. |

**Retraction.** Earlier revisions of this table described `0xFC` as a "runtime
player-mirror marker written when the town-mode player is attached to an NPC
slot". That is withdrawn. `0xFC` is the head of the Shadow Lord sprite run
`0xFC..0xFF` (`catalogs/monster-bestiary.md`, class 47), it resolves through the
sprite page to the shipped "a shadow lord" look-up string, and the only runtime
writer of the value is the Shadowlord install described in
`systems/town-mode.md` Section 13 — not a player attach. An implementation that
treats a `0xFC` slot as the player will render a Shadowlord as the avatar, or
mistake a live Shadowlord for the player in NPC-table scans. The spec no longer
claims that the player has any NPC-slot representation; see
`systems/town-mode.md` Section 8.

A second, narrower claim in the same paragraph is also withdrawn: `0xFC` **is**
present in shipped roster data. Stonegate's roster slots one, two and three are
authored `0xFC` with no dialogue and no schedule times, one per Shadowlord, and
the shard-destruction path marks the matching slot permanently removed so a
vanquished Shadowlord is never placed there again
(`catalogs/quest-graph.md` Section 5). "Written only at runtime" was an artifact
of scanning writers rather than the shipped files.

Values such as `0x50`, `0x54`, `0x70`, `0x90`, and `0xD8` are stable sprite
classes used by shipped roster slots. The roster catalog keeps them as tags and
adds role hints where supported by multiple NPC examples. They do not drive the
NPC schedule AI; movement behaviour comes from `AI[3]`.

Town-mode helpers do apply a few broad type-byte filters outside scheduling:
the scene activation mask considers the default special walker class and high
sprite classes, while alarm/death helpers recognise guard-like and hostile or
corpse-state bands. Those filters are behavioural gates, not a full
human-readable role table. A compatible implementation should preserve the tag
byte and apply the documented scheduler/town filters directly instead of
renaming every class into an inferred profession.

Earlier notes that treated `0x82` and `0x86` as type-byte values were reading
the dialog-index array, not the type array. Those two values are Talk-entry shop
triggers in `dialog[n]`, not NPC sprite classifiers.

The "occupancy" use of the type byte is unconditional: any slot whose `type[n]` is zero is treated as empty and skipped by the schedule processor. The corresponding schedule record may still hold non-zero bytes (residue from authoring or from save-game state), but the engine does not read them.

## 7. The dialog index byte

Each NPC slot has a one-byte dialog index at offset `+0x220..+0x23F` of the sub-map (one byte per slot). For ordinary speaking residents, the dialog index is a one-based pointer into the matching `.TLK` file's NPC table.

The matching is by file class: a town NPC's dialog index points into `TOWNE.TLK`, a castle NPC's into `CASTLE.TLK`, and so on. Within the matched `.TLK` file, the dialog index is compared against the `npc_id` field of each header entry; the first match identifies the NPC's blob. See the TLK format spec for the header layout.

Dialog index zero on a populated slot is a valid value: it means "this NPC has no dialogue." The engine dispatches the Talk command against an NPC whose dialog index is zero by emitting a "funny look" or equivalent stub message; no `.TLK` lookup happens.

Dialog index `1` is **not** reserved. It addresses an ordinary authored blob like
any other id, and exactly one occupied roster slot in each of the four class
files carries it: `TOWNE:0` slot 3, `DWELLING:0` slot 1, `CASTLE:0` slot 13, and
`KEEP:0` slot 1. Earlier revisions of this section said the opposite — that
`npc_id == 1` was a `.TLK` sentinel no live NPC carried, that every speaking NPC
had index `2` or above, and that a roster using index `1` would be corrupt data
aliased to the first real blob. All of that is withdrawn; see `formats/tlk.md`
Section 6 for the corrected `.TLK` header contract and
`catalogs/npc-roster.md` for the four slots.

High dialog-index values are not `.TLK` ids. In the shipped rosters, the
values `0x81` through `0x88` are Talk-entry shop triggers:

| Value | Meaning |
|-------|---------|
| `0x81` | Weaponsmith / armourer shop trigger. |
| `0x82` | Tavern, meal-counter, or sage-style interactive shop trigger. |
| `0x83` | Horse-trader shop trigger. |
| `0x84` | Ship-broker / shipwright shop trigger. |
| `0x85` | Herbalist / reagent shop trigger. |
| `0x86` | Guild shop trigger. |
| `0x87` | Healer / sanctum shop trigger. |
| `0x88` | Innkeeper shop trigger. |

The value identifies the shop family; the active scene and resident shop tables
select the local shop instance, display name, vendor name, prices, and stock.
The shipped rosters also contain special high values outside this range for
non-shop Talk special cases. Treat those as conversation/town-system special
markers rather than `.TLK` ids. The value `0xFF` is the reserved
"not a real NPC" marker: Talk on such a figure runs the scene-keyed
Blackthorn guard-demand handler instead of loading any dialogue, as specified
in `systems/conversation.md` Section 2.1 and `systems/blackthorn.md`
Section 7a.

A non-zero ordinary dialog index that does not resolve to any header entry in the matching `.TLK` file is a content error in the source data. The engine does not validate the lookup; an unresolved index will cause the talk dispatcher to read garbage from the working buffer.

## 8. Sub-map ordering

The on-disk file format preserves only the sub-map *index* (zero through seven). The mapping from sub-map index to the overworld entry and resident location-name string lives in the DATA.OVL-derived world-location table, not in the per-class file. The mapping is parallel between the `.NPC` and `.TLK` files: the *k*-th sub-map of `TOWNE.NPC` corresponds to the *k*-th block of `TOWNE.TLK`, and likewise for the other three classes. Both files use the same fixed per-sub-map stride, so index *k* alone locates the block.

**The sub-map index does not index the class `.DAT` file the same way.** A location's tile pages are found through the per-scene base floor-page table in `formats/location-dat.md` Section 4.1, never by computing `2k` and `2k + 1`. The `.DAT` class file is a flat array of sixteen 1,024-byte floor pages, and a location owns a *run* of one to five consecutive pages whose length and starting page are authored per scene: for twenty-two of the thirty-two locations the page run is not `{2k, 2k + 1}`, and for twenty of them the entry floor's page is not `2k`. Sub-map index *k* is a roster index for the `.NPC` and `.TLK` files and nothing more.

The resident world-location table confirms the scene/sub-map order below. The class names here are storage families, not necessarily the in-world type of the place; for example Paws and Cove live in the `CASTLE.*` storage family.

| Scene | Key | Resident location name |
|---:|---|---|
| 1 | `TOWNE:0` | Moonglow |
| 2 | `TOWNE:1` | Britain |
| 3 | `TOWNE:2` | Jhelom |
| 4 | `TOWNE:3` | Yew |
| 5 | `TOWNE:4` | Minoc |
| 6 | `TOWNE:5` | Trinsic |
| 7 | `TOWNE:6` | Skara Brae |
| 8 | `TOWNE:7` | New Magincia |
| 9 | `DWELLING:0` | Fogsbane |
| 10 | `DWELLING:1` | Stormcrow |
| 11 | `DWELLING:2` | Greyhaven |
| 12 | `DWELLING:3` | Waveguide |
| 13 | `DWELLING:4` | Iolo's Hut |
| 14 | `DWELLING:5` | Blank resident name |
| 15 | `DWELLING:6` | Blank resident name |
| 16 | `DWELLING:7` | Blank resident name |
| 17 | `CASTLE:0` | Blank resident name; roster and verification slice identify this as Lord British's Castle |
| 18 | `CASTLE:1` | Blank resident name; roster content identifies this as Lord Blackthorn's Castle |
| 19 | `CASTLE:2` | West Britanny |
| 20 | `CASTLE:3` | North Britanny |
| 21 | `CASTLE:4` | East Britanny |
| 22 | `CASTLE:5` | Paws |
| 23 | `CASTLE:6` | Cove |
| 24 | `CASTLE:7` | Buccaneer's Den |
| 25 | `KEEP:0` | Ararat |
| 26 | `KEEP:1` | Bordermarch |
| 27 | `KEEP:2` | Farthing |
| 28 | `KEEP:3` | Windemere |
| 29 | `KEEP:4` | Stonegate |
| 30 | `KEEP:5` | The Lycaeum |
| 31 | `KEEP:6` | Empath Abbey |
| 32 | `KEEP:7` | Serpent's Hold |

The engine reads the *(scene − 1) & 7*-th sub-map on town entry; the engine never reads the entire file at once and never iterates across sub-maps for a single play session.

## 9. Slot zero and the empty-slot sentinel

Slot zero of every sub-map is the *unused sentinel slot*. Its schedule record is zeroed and its dialog index is zero in shipped data. Its type/tag byte is not a validity predicate: some shipped sub-maps store a nonzero type/tag marker there, but the runtime still skips slot zero before scheduling, Talk lookup, collision participation, roster counts, or active-object linkage.

The sentinel is structural, not optional. The schedule processor iterates from slot one to slot thirty-one inclusive; slot zero is skipped at the loop's entry condition. The reservation lets the processor use index zero as a "no NPC" marker in other tables (active-object link, stuck counter, pathfinding queue) without colliding with a real NPC. Clean validators must not reject a nonzero slot-zero type/tag byte. They may warn on nonzero slot-zero schedule or dialog bytes as noncanonical data, but runtime behavior remains "skip slot zero regardless of stored bytes."

A sub-map with fewer than thirty-one NPCs uses the empty-slot sentinel — `type[n] == 0` — to mark the unused tail. The schedule and dialog index entries for an unused slot are unconstrained by the format, but in shipped content they are zeroed.

## 10. Worked example — one schedule record

This example walks one schedule record to illustrate the on-disk layout without
reproducing raw shipped bytes.

The file begins at byte zero of `TOWNE.NPC`. The first five hundred seventy-six bytes are the per-sub-map block for sub-map zero. Within that block, bytes zero through five hundred eleven are the schedule array (thirty-two records of sixteen bytes); bytes five hundred twelve through five hundred forty-three are the type array (thirty-two bytes); bytes five hundred forty-four through five hundred seventy-five are the dialog index array (thirty-two bytes).

The first sixteen bytes of the schedule array (bytes zero through fifteen) are slot zero's schedule, which is all zeros in shipped data. Slot zero's dialog index byte (byte five hundred forty-four) is zero. Slot zero's type byte (byte five hundred twelve) may be zero or a nonzero structural marker; either way, slot zero is the unused sentinel slot and is not a live NPC.

The second schedule record (bytes sixteen through thirty-one) is slot one: the
first real NPC slot of that sub-map. Interpreting the sixteen bytes in the
record-layout order gives:

| Field       | Decoded example                                                          |
|-------------|---------------------------------------------------------------------------|
| `AI[3]`     | Stationary at waypoint zero, stationary at waypoint one, and a third behaviour mode at waypoint two. |
| `X[3]`      | Three waypoint columns, one per waypoint.                                |
| `Y[3]`      | Three waypoint rows, one per waypoint.                                   |
| `Z[3]`      | A floor byte for each waypoint.                                          |
| `time[4]`   | Four hour boundaries, interpreted by the segment rule in Section 5.1.    |

Reading the time boundaries against the waypoint selection rule (Section 5.1):
the segment from the first boundary through the second boundary routes to
waypoint zero; the next segment routes to waypoint one; the next routes to
waypoint two; and the wraparound segment routes back through waypoint one.

In game terms, a typical record uses waypoint zero for a night/rest location,
waypoint one for the main daytime location, waypoint two for a short alternate
location, then waypoint one again for the evening wraparound segment.

The matching type byte and dialog index identify the NPC's sprite class and
dialogue. A nonzero type byte indicates an occupied role class whose exact
display tile and town filters are interpreted by the runtime; a dialog index of
`0x02` would point into `TOWNE.TLK`'s header entries to locate the NPC's blob.

A reader can sanity-check a `.NPC` decoder by:

1. Confirming the file size equals four thousand six hundred eight bytes.
2. Confirming bytes zero through fifteen are all zero (slot zero's schedule), confirming byte five hundred forty-four is zero (slot zero's dialog index), and treating byte five hundred twelve as an ignored slot-zero type/tag marker rather than a live occupancy flag.
3. Picking any populated slot (`type[n] != 0`), decoding its sixteen-byte schedule against the waypoint selection rule, and confirming the resulting waypoint coordinates fall within the location's thirty-two-by-thirty-two grid.

## 11. Format Boundary And Catalog Work

The `.NPC` format contract is complete at file-structure and schedule-consumer
depth. It is verified by direct byte inspection at the file-structure level
(file size, sub-map stride, schedule record stride, slot-zero sentinel) and by
behavioural inspection at the schedule-processor level (waypoint selection
rule, AI byte dispatch outline, type byte occupancy use, dialog index use).
Remaining work belongs to catalog naming rather than to this file format.

- **Blank resident location-name rows.** Scenes 14 through 18 have blank
  resident location-name strings in the world-location table. Two of them are
  semantically identified by roster and special-behaviour evidence
  (`CASTLE:0` = Lord British's Castle, `CASTLE:1` = Lord Blackthorn's Castle);
  the three blank dwelling-family rows should keep their stable `DWELLING:n`
  keys until another clean source names them. This is a catalog naming
  boundary, not a `.NPC` file-layout gap.

- **Sprite-class role names.** The AI-byte values and the type byte's engine
  role are fixed. Human-readable role labels for every shipped sprite class are
  still partly interpretive and belong in `catalogs/npc-roster.md`, not this
  format layer.

## 12. Cross-references

- The per-tick schedule processor that consumes this format — the eight-state per-NPC state machine, the time-of-day waypoint dispatch, the per-cardinal-direction probe, the floodfill pathfinder, the path queue, the stuck counter — `systems/npc-schedules.md`.
- The town-mode activation, alarm, and death-mask type filters that consume
  the same type byte — `systems/town-mode.md`.
- The per-class location data file format whose tile grids host the live NPCs — `formats/location-dat.md`.
- The per-class dialogue file format whose NPC blobs are looked up by `dialog_index` — `formats/tlk.md`.
- Dialogue runtime flag stores and save-backed NPC interaction flags — `systems/quest-flags.md` and `formats/saved-gam.md`.
- The text-output pipeline that ultimately renders an NPC's name and description — `systems/text-output.md`.
- The combat AI dispatch keyed off the type byte for hostile encounters — described under `systems/combat.md`.
- The active-object table that links a live NPC to its on-screen sprite — `formats/saved-gam.md` (Section 8).

## 13. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of the four `.NPC` files, file size, sub-map partition, schedule stride, and slot-zero sentinel — `u5-decomp/formats/npc-tlk-pth.md`.
- The schedule processor's entry point — class-to-file dispatch, sub-map indexing, and the three back-to-back reads of schedule, type, and dialog arrays — `u5-decomp/functions/NPC_OVL/`.
- Shipped roster scan of the four clean `.NPC` files and Talk shop-dispatch
  evidence from `u5-decomp/functions/TALK_OVL/` and
  `u5-decomp/functions/ULTIMA_EXE/` -- high
  dialog-index shop-trigger values.
- Resident world-location table verification that binds scene bytes 1 through
  32 to storage-family sub-map keys and resident location-name strings:
  `u5-decomp/functions/OUTSUBS_OVL/` and
  `u5-decomp/formats/data-ovl.md`.
- Scene-byte lifecycle audit confirming that the NPC loader's arithmetic
  scene-byte write is only a temporary one-based-to-zero-based conversion:
  `u5-decomp/notes/critical_state_lifecycles.md`.
- The per-tick walker — per-NPC state machine, AI-byte dispatch, type-byte occupancy use, pathfinding, and cross-overlay sprite-position writeback — `u5-decomp/functions/NPC_OVL/`.
- The waypoint selection routine — four-boundary, three-waypoint, wraparound-through-waypoint-one rule — `u5-decomp/functions/NPC_OVL/`.
- Runtime schedule field semantics confirmed against the schedule processor's read sites — `u5-decomp/functions/NPC_OVL/`.
- Runtime initialisation that snapshots schedule waypoints to per-NPC runtime fields — `u5-decomp/functions/NPC_OVL/`.
- The waypoint `Z` floor convention of Section 5.2 — the signed reading, the
  shipped five-value alphabet, the forty-one basement waypoints, and the
  correction that sub-map index is not a `.DAT` page index. Source provenance:
  derived from private analysis note
  `u5-decomp/notes/scene_floor_page_table_2026-08-22.md`, cross-checked by
  re-scanning the shipped `.NPC` files.
- The schedules systems spec covering the runtime semantics this format spec only references — `u5-spec/systems/npc-schedules.md`.
