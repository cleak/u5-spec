# NPC files

Format specification for the four shared per-class NPC roster files: `TOWNE.NPC`, `DWELLING.NPC`, `CASTLE.NPC`, and `KEEP.NPC`. These hold the daily schedule, behaviour mode, role tag, and dialogue index for every speaking NPC in the game's named non-overworld locations. Each file is exactly four thousand six hundred eight bytes and contains eight per-location sub-maps of identical layout. The format is uniform across the four files; only the per-location content differs.

## 1. Overview

Ultima V's named non-overworld world has thirty-two locations: eight towns, eight dwellings, eight castles, and eight keeps. Every location is populated by a small cast of NPCs who walk a daily routine — the baker behind the counter at noon, the guard at his post, the old man on his bench in the evening, the child in his bed at night. The schedule for each NPC's day is data, not code: it lives in the `.NPC` files described here, and is interpreted at runtime by the per-tick schedule processor.

The four files partition by location class, mirroring the same partition used by the location data files (`*.DAT`) and the dialogue files (`*.TLK`). One `.NPC` file holds eight locations; one location's worth of NPC data is a *sub-map* of fixed size. Within a sub-map, the cast is laid out as a fixed-size array of NPC slots; within an NPC slot, fields are at fixed offsets. There are no length prefixes, no per-NPC variable-size fields, no padding, and no version word. A reader navigates a `.NPC` file by arithmetic alone.

Each NPC's record specifies three *waypoints* — three (X, Y, Z) positions on the location's map — plus four *time boundaries* that select which waypoint is active at any given hour, three behaviour-mode bytes (one per waypoint), a one-byte role tag, and a one-byte dialogue index that points into the matching `.TLK` file. The schedule processor consumes this record once per game turn, advancing each NPC toward its currently active waypoint.

The four files are companions to each other: a live NPC is a row in a `.NPC` file's sub-map, possibly hosting a tile grid in the corresponding `.DAT` file's sub-map, possibly speaking lines from the corresponding `.TLK` file's NPC blob. The pairing is by file family (TOWNE/DWELLING/CASTLE/KEEP) and by sub-map index within that family.

## 2. The four files and the scene-byte partition

The class-to-file mapping mirrors the `.DAT` and `.TLK` partition exactly:

| Scene byte range | Class    | File           |
|------------------|----------|----------------|
| 1–8              | Town     | `TOWNE.NPC`    |
| 9–16             | Dwelling | `DWELLING.NPC` |
| 17–24            | Castle   | `CASTLE.NPC`   |
| 25–32            | Keep     | `KEEP.NPC`     |

Scene byte zero is overworld; no `.NPC` file is loaded outdoors, because outdoor NPCs are not schedule-driven in the same way. Scene bytes above thirty-two are dungeon and combat states, where no town-style NPC roster exists.

Within a class, the eight per-class sub-maps are addressed by `(scene − 1) & 7`. The runtime resolves the file family by `(scene − 1) >> 3` against a four-entry pointer table; the resulting filename is opened and the per-sub-map data is read into the resident schedule buffer.

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

Slot zero of every sub-map is reserved as an unused sentinel. Its schedule record is all zeros, its type byte is zero, and its dialog index is zero. The engine's per-tick walker iterates from slot one to slot thirty-one inclusive and skips slot zero entirely. Effective capacity per sub-map is therefore thirty-one NPCs, and per file is two hundred forty-eight NPCs (thirty-one × eight sub-maps); across the four files, the world's named-location NPC roster is bounded above by nine hundred ninety-two.

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

`Z[i]` is the location's floor index for waypoint *i*, matching the per-location floor convention used by the location data file: floor zero is the ground floor, floor one is upper or basement, occasional higher values address re-purposed extra floors. The schedule processor compares `Z[i]` against the player's current floor byte before moving the NPC; an NPC whose active waypoint is on a different floor from the player's view is suspended (in a "Z-mismatch" state) and resumes only when the player switches floors.

The `Z[i]` byte's signedness is open: shipped content uses only the unsigned range `0x00..0x07`, but the engine reads the byte as if it were unsigned in some code paths and treats specific sentinel values ("below" / "above") as triggers in others. For all shipped schedules, treating `Z[i]` as an unsigned byte gives correct behaviour. See Section 11 for the open question.

### 5.3 The AI byte

Each waypoint has its own `AI[i]` byte. The AI byte tells the schedule processor *how* the NPC behaves while at that waypoint — does the NPC stand still, wander in a small radius, follow a fixed route, or react to the player's approach? The AI byte is consumed by the per-tick walker and by the action-readiness classifier; it is the schedule's per-waypoint behaviour switch.

The shipped value range is small. The most common values observed in `TOWNE.NPC` and the other class files cluster around `0x00`, `0x01`, `0x02`, and a sentinel `0x0F`. The full enumeration of AI values is not yet pinned down; the working hypothesis (subject to verification against in-game behaviour) is:

| AI value | Probable meaning                                      |
|----------|-------------------------------------------------------|
| `0x00`   | Stationary at waypoint (sit, sleep, stand still).     |
| `0x01`   | Wander a small radius around the waypoint.            |
| `0x02`   | Patrol along a fixed route.                           |
| `0x03+`  | Other patrol or interaction modes (children playing, beggars approaching, etc.). |
| `0x0F`   | Sentinel — possibly "ignore this waypoint."           |

The runtime dispatches on the AI byte through multiple states and branches; a complete enumeration belongs in the schedules systems spec, not in this format spec. This spec records the byte's location and width but not its full dispatch table.

### 5.4 The time array

`time[0]` through `time[3]` are four unsigned eight-bit hour values, range `0..23`. They are read as plain bytes; the engine does not validate their range, but values above twenty-three would never select a waypoint correctly because the engine's hour clock is itself bounded `0..23`.

The time array's semantics — three waypoints, four boundaries, with wraparound through waypoint one — is described in Section 5.1.

## 6. The type byte

Each NPC slot has a one-byte type tag at offset `+0x200..+0x21F` of the sub-map (one byte per slot). The type byte serves two purposes: it acts as the slot's occupancy flag (zero = empty, non-zero = populated), and it tags the NPC's role for the engine's tile selection, look-text generation, and combat-AI dispatch.

The full enumeration of type values is not yet finalised. Shipped sub-maps show repeated values — `0x1C`, `0x50`, `0x54`, `0x70`, `0x82`, `0x86` are common — strongly suggesting an enum plus per-bit flags. The working hypothesis is that the byte encodes:

| Conceptual field    | Likely encoding                                                                  |
|---------------------|----------------------------------------------------------------------------------|
| Role / sprite class | High nibble or upper bits select between merchant, guard, child, common, special. |
| Per-role flag bits  | Low bits select per-role variants — armed/unarmed, male/female, etc.             |

A reader can treat the type byte as opaque if it only needs to copy the field through. An implementation that wants to render NPCs with the correct sprite or run the correct AI must interpret the byte; the interpretation is engine-side and belongs in the schedules systems spec.

The "occupancy" use of the type byte is unconditional: any slot whose `type[n]` is zero is treated as empty and skipped by the schedule processor. The corresponding schedule record may still hold non-zero bytes (residue from authoring or from save-game state), but the engine does not read them.

## 7. The dialog index byte

Each NPC slot has a one-byte dialog index at offset `+0x220..+0x23F` of the sub-map (one byte per slot). The dialog index is a one-based pointer into the matching `.TLK` file's NPC table.

The matching is by file class: a town NPC's dialog index points into `TOWNE.TLK`, a castle NPC's into `CASTLE.TLK`, and so on. Within the matched `.TLK` file, the dialog index is compared against the `npc_id` field of each header entry; the first match identifies the NPC's blob. See the TLK format spec for the header layout.

Dialog index zero on a populated slot is a valid value: it means "this NPC has no dialogue." The engine dispatches the Talk command against an NPC whose dialog index is zero by emitting a "funny look" or equivalent stub message; no `.TLK` lookup happens. The format reserves `npc_id == 1` in `.TLK` files as a sentinel that no live NPC carries (because dialog index `1` is unused — every speaking NPC has dialog index `2` or above). The result is that `.TLK` files always start with a `(npc_count, 1)` leading pair, with the count word occupying the slot a regular header entry would use for its blob offset; see the TLK format spec for that mechanism.

A non-zero dialog index that does not resolve to any header entry in the matching `.TLK` file is a content error in the source data. The engine does not validate the lookup; an unresolved index will cause the talk dispatcher to read garbage from the working buffer.

## 8. Sub-map ordering

The on-disk file format preserves only the sub-map *index* (zero through seven). The mapping from sub-map index to in-game location name (which town is sub-map zero of `TOWNE.NPC`?) lives in a separate per-class name table in the resident data segment, not in the per-class file. The mapping is parallel between the `.DAT`, `.NPC`, and `.TLK` files: the *k*-th sub-map of `TOWNE.NPC` corresponds to the *k*-th block of `TOWNE.DAT` and the *k*-th block of `TOWNE.TLK`.

The shipped sub-map orderings are believed to follow the canonical Ultima V town ordering — Moonglow, Britain, Jhelom, Yew, Minoc, Trinsic, Skara Brae, New Magincia for towns; the four castles plus four keeps in lord-by-lord order for the castle and keep files; and the eight named dwellings in their canonical order for the dwelling file. This ordering is provisional; it can be confirmed empirically by loading a save in each location and reading the live scene byte. See Section 11 for the open question.

The engine reads the *(scene − 1) & 7*-th sub-map on town entry; the engine never reads the entire file at once and never iterates across sub-maps for a single play session.

## 9. Slot zero and the empty-slot sentinel

Slot zero of every sub-map is the *unused sentinel slot*: its schedule record is sixteen zero bytes, its type byte is zero, and its dialog index is zero. This is true for every sub-map of every shipped `.NPC` file.

The sentinel is structural, not optional. The schedule processor iterates from slot one to slot thirty-one inclusive; slot zero is skipped at the loop's entry condition. The reservation lets the processor use index zero as a "no NPC" marker in other tables (active-object link, stuck counter, pathfinding queue) without colliding with a real NPC.

A sub-map with fewer than thirty-one NPCs uses the empty-slot sentinel — `type[n] == 0` — to mark the unused tail. The schedule and dialog index entries for an unused slot are unconstrained by the format, but in shipped content they are zeroed.

## 10. Worked example — `TOWNE.NPC` first sub-map

This example walks the first non-stub NPC slot of the first sub-map of `TOWNE.NPC` to illustrate the on-disk layout.

The file begins at byte zero of `TOWNE.NPC`. The first five hundred seventy-six bytes are the per-sub-map block for sub-map zero. Within that block, bytes zero through five hundred eleven are the schedule array (thirty-two records of sixteen bytes); bytes five hundred twelve through five hundred forty-three are the type array (thirty-two bytes); bytes five hundred forty-four through five hundred seventy-five are the dialog index array (thirty-two bytes).

The first sixteen bytes of the schedule array (bytes zero through fifteen) are slot zero's schedule, which is all zeros. Slot zero's type byte (byte five hundred twelve) is zero. Slot zero's dialog index byte (byte five hundred forty-four) is zero. This is the unused sentinel slot.

The second schedule record (bytes sixteen through thirty-one) is slot one — the first real NPC of the first sub-map. A representative byte run is:

```
00 00 01    13 17 1D    15 13 1D    01 00 01    15 09 11 12
```

The fields decode as:

| Bytes              | Field       | Decoded                                                                   |
|--------------------|-------------|---------------------------------------------------------------------------|
| `00 00 01`         | `AI[3]`     | Stationary at waypoint zero, stationary at waypoint one, mode `0x01` at waypoint two. |
| `13 17 1D`         | `X[3]`      | Column nineteen at waypoint zero, twenty-three at waypoint one, twenty-nine at waypoint two. |
| `15 13 1D`         | `Y[3]`      | Row twenty-one at waypoint zero, nineteen at waypoint one, twenty-nine at waypoint two. |
| `01 00 01`         | `Z[3]`      | Floor one, floor zero, floor one across the three waypoints.              |
| `15 09 11 12`      | `time[4]`   | Boundaries at hours twenty-one, nine, seventeen, eighteen.                |

Reading the time boundaries against the waypoint selection rule (Section 5.1): from hour twenty-one (nine PM) until hour nine (nine AM the next day), the NPC is at waypoint zero — column nineteen, row twenty-one, floor one. From nine AM until five PM, the NPC is at waypoint one — column twenty-three, row nineteen, floor zero. From five PM until six PM, the NPC is at waypoint two — column twenty-nine, row twenty-nine, floor one. From six PM until nine PM (the wraparound segment), the NPC is at waypoint one — column twenty-three, row nineteen, floor zero.

In other words, this NPC sleeps upstairs (waypoint zero) from nine PM until nine AM, works on the ground floor (waypoint one) from nine AM until five PM, briefly visits a second upstairs location (waypoint two) from five PM until six PM, and returns to the ground-floor work spot (waypoint one) from six PM until bedtime.

The matching type byte and dialog index — at sub-map offset five hundred thirteen and five hundred forty-five — identify the NPC's role and dialogue. A type byte of `0x50` would indicate one role class (e.g., "common townsfolk"); a dialog index of `0x02` would point into `TOWNE.TLK`'s header entries to locate the NPC's blob.

A reader can sanity-check a `.NPC` decoder by:

1. Confirming the file size equals four thousand six hundred eight bytes.
2. Confirming bytes zero through fifteen are all zero (slot zero's schedule), and that bytes five hundred twelve and five hundred forty-four are zero (slot zero's type and dialog index).
3. Picking any populated slot (`type[n] != 0`), decoding its sixteen-byte schedule against the waypoint selection rule, and confirming the resulting waypoint coordinates fall within the location's thirty-two-by-thirty-two grid.

## 11. Open questions

The format is verified by direct byte inspection at the file-structure level (file size, sub-map stride, schedule record stride, slot-zero sentinel) and by behavioural inspection at the schedule-processor level (waypoint selection rule, AI byte dispatch outline, type byte occupancy use, dialog index use). The following points remain open.

- **Sub-map index → location name mapping.** The on-disk format records only the sub-map index. The mapping is presumed to follow the canonical Ultima V ordering (Moonglow → Britain → Jhelom → Yew → Minoc → Trinsic → Skara Brae → New Magincia for towns; analogous orderings for the other classes), but this needs empirical confirmation by loading a save in each location and reading the live scene byte.

- **AI byte enumeration.** A complete enumeration of value-to-behaviour mapping is not yet pinned down. The working hypothesis (`0x00` stationary, `0x01` wander, `0x02` patrol, `0x0F` sentinel) covers the most common values but is not exhaustive. A full enumeration belongs in the schedules systems spec.

- **Type byte enumeration.** Shipped values cluster around `0x1C`, `0x50`, `0x54`, `0x70`, `0x82`, `0x86`, suggesting an enum plus per-bit flags. The split between role bits and flag bits has not been pinned down. A full enumeration belongs in the schedules systems spec.

- **Z byte signedness.** The schedule processor reads `Z[i]` as an unsigned byte in some paths and treats specific sentinels as triggers in others. All shipped schedules use only the unsigned range `0x00..0x07`, so unsigned interpretation gives correct behaviour for shipped content. Signedness becomes load-bearing only for user-supplied or modded schedules using values above `0x7F`.

- **Sentinel AI value.** The value `0x0F` appears occasionally in shipped schedules and is pre-tested against a sentinel by initialisation code. Its exact role — "ignore this waypoint" versus "this waypoint is special" versus authoring stub — is unconfirmed.

- **Dialog index zero on populated slots.** A populated slot (`type[n] != 0`) with `dialog[n] == 0` is a valid "NPC has no dialogue" configuration. Whether the engine routes such an NPC to a generic fallback or emits a "funny look" stub is engine-side.

- **Slot-zero contents on save-load.** The `.NPC` files are read-only at runtime. From a format perspective, on-disk slot zero is always all zeros.

## 12. Cross-references

- The per-tick schedule processor that consumes this format — the eight-state per-NPC state machine, the time-of-day waypoint dispatch, the per-cardinal-direction probe, the floodfill pathfinder, the path queue, the stuck counter — `systems/npc-schedules.md`.
- The per-class location data file format whose tile grids host the live NPCs — `formats/location-dat.md`.
- The per-class dialogue file format whose NPC blobs are looked up by `dialog_index` — `formats/tlk.md`.
- The save image layout that persists the per-NPC quest flags toggled by dialogue — `formats/saved-gam.md`.
- The text-output pipeline that ultimately renders an NPC's name and description — `systems/text-output.md`.
- The combat AI dispatch keyed off the type byte for hostile encounters — described under `systems/combat.md`.
- The active-object table that links a live NPC to its on-screen sprite — `formats/saved-gam.md` (Section 8).

## 13. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of the four `.NPC` files, file size, sub-map partition, schedule stride, and slot-zero sentinel — `u5-decomp/formats/npc-tlk-pth.md`.
- The schedule processor's entry point — class-to-file dispatch, sub-map indexing, and the three back-to-back reads of schedule, type, and dialog arrays — `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md`.
- The per-tick walker — per-NPC state machine, AI-byte dispatch, type-byte occupancy use, pathfinding, and cross-overlay sprite-position writeback — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The waypoint selection routine — four-boundary, three-waypoint, wraparound-through-waypoint-one rule — `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md`.
- Runtime schedule field semantics confirmed against the schedule processor's read sites — `u5-decomp/functions/NPC_OVL/0x0938_npc_should_act.md`.
- Runtime initialisation that snapshots schedule waypoints to per-NPC runtime fields — `u5-decomp/functions/NPC_OVL/0x00D6_npc_init_runtime_state.md`.
- The schedules systems spec covering the runtime semantics this format spec only references — `u5-spec/systems/npc-schedules.md` (planned).
