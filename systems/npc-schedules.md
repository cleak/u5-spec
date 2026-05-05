# NPC schedules

## 1. Overview

Ultima V's named locations — the eight towns, eight dwellings, eight castles, and eight keeps — are populated by NPCs that walk on a clock. Each non-player character has a daily routine encoded in a small fixed-width record on disk: three positions ("waypoints") tied to four hour-of-day boundaries, plus per-waypoint behaviour modes. The runtime reads the record, picks the waypoint matching the current hour, and walks the NPC toward that target one cell per player-turn. By the time the player has crossed town, the baker is in the bakery, the guards are at their posts, and the town drunk is back at the tavern.

The machinery has six pieces:

- **A roster file per location class** — one fixed-size table per class, sliced into a sub-map per location.
- **A schedule record** — sixteen bytes per NPC giving three waypoints and four time boundaries.
- **A per-NPC runtime state block** — a small mutable record tracking where the NPC is, what the engine is currently doing with them, and a few pathfinding helpers.
- **A per-tick walker** — a procedure called once per player-turn that scans every NPC and advances them toward their currently-active waypoint.
- **A flood-fill pathfinder** — a breadth-first search that produces the next cardinal step toward a target, plus a workspace builder that paints the walkable map.
- **A world-mutation primitive** — every NPC step updates the logical position and updates the on-screen sprite (the latter only when the NPC is on the player's current floor).

The clock, the midnight daily-event bundle, and "when does each player command advance time" are owned by the time spec. The schedule system is purely a consumer of the current hour byte and the per-turn-cleanup contract.

## 2. Roster and schedule storage on disk

The roster is split across four files, one per location class:

| File           | Class    |
|----------------|----------|
| `TOWNE.NPC`    | Town     |
| `DWELLING.NPC` | Dwelling |
| `CASTLE.NPC`   | Castle   |
| `KEEP.NPC`     | Keep     |

Each file is the same fixed size (4,608 bytes) and is internally a flat array of eight per-location blocks of 576 bytes each. Within a class, the engine's "scene number" (a one-based location index) selects the file by integer-dividing by eight, and the eight-modulo of the same value picks the block within the file.

Each 576-byte block holds three parallel sub-blocks of fixed width:

| Offset | Bytes | Sub-block          | Description                                                                                  |
|-------:|------:|--------------------|----------------------------------------------------------------------------------------------|
|     0  |   512 | `schedule[32]`     | Thirty-two sixteen-byte schedule records. Section 3 describes the record.                    |
|   512  |    32 | `type[32]`         | One byte per NPC. `0` means "slot empty"; non-zero means "slot occupied" and identifies role.|
|   544  |    32 | `dialog_index[32]` | One byte per NPC. Looks the NPC up in the matching `.TLK` dialogue file. Zero = no dialogue. |

Slot zero of each block is reserved as a sentinel; the engine never treats it as a real NPC. Effective capacity per location is therefore thirty-one NPCs, and per location class is `31 × 8 = 248`.

When the engine enters a location, a single load pass reads exactly one block: the schedule sub-block into one resident buffer, the type sub-block into a second, and the dialog-index sub-block into the per-NPC runtime slots (Section 4). Only the current location's NPCs are resident at any given time. The on-disk layout has no padding, no per-NPC header, no compression.

## 3. The schedule record

Each NPC occupies sixteen bytes in the schedule sub-block, partitioned into five parallel arrays:

| Bytes | Field     | Width        | Meaning                                                                                                          |
|------:|-----------|--------------|------------------------------------------------------------------------------------------------------------------|
|  0–2  | `ai[3]`   | three bytes  | Behaviour mode for each of the three waypoints. Section 9 describes values.                                      |
|  3–5  | `x[3]`    | three bytes  | Map X coordinate (0–31) for each waypoint. Locations are 32×32 cells.                                            |
|  6–8  | `y[3]`    | three bytes  | Map Y coordinate (0–31) for each waypoint.                                                                       |
| 9–11  | `z[3]`    | three bytes  | Map Z (floor) for each waypoint. Compared against the location's current floor; mismatches drive climb logic.    |
| 12–15 | `time[4]` | four bytes   | Hour-of-day boundaries (0–23) that delimit which waypoint is active.                                             |

`(ai[i], x[i], y[i], z[i])` is one waypoint, for `i` in `0..2`. The `time` array has four entries delimiting three waypoints.

**Three waypoints, four boundaries, one wraparound.** The four `time` bytes carve a 24-hour day into four contiguous segments, each mapped to one of three waypoints:

| Hour range                       | Active waypoint |
|----------------------------------|-----------------|
| `[time[0], time[1])`             | 0               |
| `[time[1], time[2])`             | 1               |
| `[time[2], time[3])`             | 2               |
| `[time[3], time[0])` (wraps)     | 1               |

The wraparound segment — the night band that crosses midnight from `time[3]` back to `time[0]` — selects waypoint **1**, not waypoint 0. In typical NPC routines, `time[1]` corresponds to "go home for the evening" and waypoint 1 is the home or sleep location. An NPC who goes home at 8 PM therefore stays home until the next morning's `time[0]` returns them to waypoint 0.

**Hour-only resolution.** Minute-of-hour is irrelevant to schedule selection; an NPC transitions exactly at the top of an hour. The selection is a function purely of the hour byte.

**Selection rule: "most recent past boundary".** The scheduler asks "which boundary's hour is closest to the current hour, looking backward in time, with twenty-four-hour wraparound?" and returns the waypoint that segment maps to. All four boundary values are distinct in well-formed schedules.

**Z is unsigned at runtime.** The runtime treats Z as unsigned when comparing against the location's current floor. Treat Z as a flat unsigned floor index.

## 4. Per-NPC runtime state

The on-disk schedule is read-only at runtime. Mutable state lives in a separate per-NPC runtime block of sixteen bytes per NPC, in a flat thirty-two-slot table. Each slot holds:

| Offset | Width | Field         | Purpose                                                                                          |
|-------:|-------|---------------|--------------------------------------------------------------------------------------------------|
|   0    | byte  | `state`       | The state machine's current state. Section 7 enumerates values.                                  |
|   2    | word  | `target_x`    | The NPC's currently-pursued X. After arrival, this is also "the NPC's current X".                |
|   4    | word  | `target_y`    | Currently-pursued Y.                                                                              |
|   6    | word  | `current_z`   | The NPC's current floor. Drives the Z-mismatch states.                                            |
|   8    | word  | `type_mirror` | A copy of the NPC's type byte for quick local lookup.                                             |
|  12    | word  | `linked_obj`  | Index into the active-object table (Section 11). Zero = not currently rendered.                   |
|  14    | word  | `cached_wp`   | The waypoint index most recently observed by the state machine. Drives transition detection.     |

Three parallel side tables, indexed by NPC slot, hold pathfinding-only state:

- **Move queue** — thirty-two bytes per NPC, holding packed direction codes for replay one-cell-at-a-time. Filled by the pathfinder, drained by the walker.
- **Move-queue read pointer** — a word per NPC; sentinel "all bits set" means "queue inactive".
- **Stuck counter** — a word per NPC, incremented every tick the NPC fails to make progress. A small threshold forces a queue reset and replan.

Two per-tick scratch booleans are shared by every NPC: an "any NPC moved" flag and an "any tile changed" flag. Both are cleared at the start of every tick; the town turn loop reads "any NPC moved" to decide whether the screen needs a repaint.

**Initialisation.** When the engine enters a location, a single pass walks the runtime table. For every occupied slot, the active waypoint for the current hour is computed (Section 3 selection rule); its `(x, y, z)` is copied into the runtime's `(target_x, target_y, current_z)` (the NPC is placed *at* its current waypoint on entry — no walk-from-yesterday sequence); the state byte is set to "idle"; the cached waypoint index is set to the freshly-computed waypoint so the next tick will not falsely fire a transition; the type field is mirrored; the move queue, queue pointer, and stuck counter are reset. For empty slots (on-disk type byte zero), only the state byte is cleared; the per-tick walker skips empty slots before reading any other field.

## 5. The schedule processor

The schedule processor — the per-tick walker — runs once per player-turn from the town turn loop, with the current hour byte as its only input. It also runs from the time-elapsing rest/wait command outside the normal mode loops. The overworld and dungeon mode loops do not invoke the scheduler.

Per call, the processor:

1. **Clears the per-tick scratch flags** so the caller can read them on return.
2. **Iterates NPC slots `1..31`.** Slot 0 is the unused sentinel.
3. **Skips empty slots.**
4. **Looks up the active waypoint** for the current hour.
5. **Reads the current state byte.** If state is "idle" (state ≤ 1), the processor first calls a *boundary trigger* sub-step (Section 6) that detects whether the current hour exactly matches one of the NPC's four schedule boundaries; on a hit it reclassifies the state byte.
6. **Dispatches on the (possibly updated) state byte** through the eight-state machine (Section 7) — cardinal-direction probes, optionally a pathfinder invocation, and zero or one position update via the world-mutation primitive (Section 11).
7. **Maintains the move queue.** If the dispatch chose to replay a cached path, the next direction byte is dequeued and applied. If the dispatch produced a new path, the queue is filled. If the NPC fails to make progress, the stuck counter is bumped and may force a queue reset.

The processor is a single sequential pass — no per-NPC concurrency, no priority queue, no skip-list. Every NPC gets one chance to act per tick, in slot order. An NPC moves at most one cell per turn the player takes.

## 6. The schedule-boundary trigger

The boundary trigger is the sub-step the processor calls on idle NPCs. It detects whether the current hour has crossed one of the NPC's four schedule boundaries.

**Boundary equality.** The trigger compares the current hour byte against each of the NPC's four `time` bytes. If none match exactly, the trigger returns "no action" — the NPC stays idle. An NPC *between* boundaries (already at a waypoint, no transition pending) never advances; schedules are sample-once, not interpolated.

**Cached-versus-current waypoint.** When the hour matches one of the four boundaries, the trigger asks for the new active waypoint. If it equals the cached waypoint, no real transition has occurred and state is set to "idle". If they differ, the NPC needs to move.

**Floor classification.** When a real transition is detected, the new state byte is chosen by comparing three quantities: the NPC's current floor (`current_z`), the new waypoint's floor (`z[new_wp]`), and the location's current floor:

| NPC floor vs map | Target floor vs map | New state | Meaning                                              |
|------------------|---------------------|-----------|------------------------------------------------------|
| equal            | equal               | 2         | Both on the player's floor; walk normally.           |
| equal            | below               | 7         | NPC on this floor; target downstairs.                |
| equal            | above               | 6         | NPC on this floor; target upstairs.                  |
| below            | equal               | 5         | NPC downstairs; target on this floor.                |
| above            | equal               | 4         | NPC upstairs; target on this floor.                  |
| neither          | neither             | 8         | Neither end on this floor; replan-needed.            |

"Above"/"below" is on the unsigned floor index; "below" means floor index numerically greater than the map's current floor.

After classifying, the trigger does one extra check: if the NPC's runtime `(target_x, target_y, current_z)` already equals the new waypoint's `(x, y, z)`, the NPC is already on the waypoint and state is reset to "idle".

The trigger does *not* update the cached waypoint field. As long as cached differs from new-waypoint, every subsequent boundary-tick fires the same transition path, keeping the NPC moving on consecutive boundary ticks until they actually arrive — at which point the next idle-tick's "already on the waypoint" check resets the state and updates the cached value.

## 7. The state machine

The state byte takes values in `0..8`:

| State | Name                           | What the tick does                                                                                                |
|------:|--------------------------------|-------------------------------------------------------------------------------------------------------------------|
| 0     | empty / unused                 | Slot is empty; the walker skips it before reading the state byte.                                                |
| 1     | idle / settled                 | NPC is at its currently-active waypoint with nothing to do. The boundary trigger may upgrade it.                 |
| 2     | in-plane move                  | Both NPC and target are on the player's floor; probe cardinal directions, run the pathfinder, commit a step.     |
| 3     | replaying cached path          | A pathfinder run earlier produced a queued route; pop the next direction byte and apply it.                      |
| 4     | descending toward target floor | NPC is upstairs of the target; steer toward a down-stairway tile on this floor.                                  |
| 5     | ascending toward target floor  | NPC is downstairs of the target; steer toward an up-stairway tile.                                               |
| 6     | climbing up off this floor     | NPC is on this floor and target is above; steer toward an up-stairway. Floor change happens via state 4/5.       |
| 7     | climbing down off this floor   | Mirror of state 6.                                                                                                |
| 8     | replan needed                  | Set when neither end of the move is on the player's floor. Walker treats as transient "replan".                  |

A few observations: state 3 is the queue-replay path — once the pathfinder produces a route, subsequent ticks dequeue and apply, and the pathfinder is not re-invoked until the queue drains or resets. States 2, 4, 5, 6, 7 all do "probe and step"; the structural difference is the target (waypoint coords, a stairway tile, an alternate-floor mirror coord) and which directions are tried first. State 8 is rarely dispatched: most ticks where neither end is on the player's floor are short-circuited at the boundary trigger.

The state byte is written by initialisation (1 for occupied, 0 for empty), by the boundary trigger (1, 2, 4, 5, 6, 7, or 8), by the pathfinder-success path (3), and by the world-mutation primitive (1 — "settled" — on every successful move). The "settled" write at the end of every successful move is what eventually drains a state-3 queue back to state 1.

## 8. Pathfinding

When an NPC needs to move and the next cardinal direction is blocked, the walker invokes a flood-fill pathfinder. The pathfinder operates on a 32×32 byte scratch workspace separate from the live world-tile array, and returns either a target cell coordinate (plus a queued sequence of direction codes that re-traces the path) or "no route within budget".

### 8.1 The workspace

The workspace is the same dimensions as the location map (32×32 = 1024 bytes), keyed by `(row, col)` in row-major order. It is *rebuilt from scratch on every pathfinding call* — no incremental update.

### 8.2 Cell encoding

Each workspace cell is a single byte split into a high nibble and a low nibble. After the workspace builder has run but before BFS expansion, four values occur:

| Cell value     | Meaning                                                                                                       |
|----------------|---------------------------------------------------------------------------------------------------------------|
| open           | Walkable and unvisited. The BFS visit gate accepts these.                                                     |
| goal sentinel  | Low-nibble marker for a cell the BFS is hunting; reaching it ends the search.                                 |
| start cell     | Pre-stamped with high-nibble direction code "north"; the BFS reads the high nibble as its initial direction.  |
| obstacle       | High nibble above the visit-gate threshold so BFS rejects it.                                                 |

As BFS expands, each visited cell is overwritten with `direction << 4`, where the direction code is the *inbound* direction. The visit gate accepts open and goal cells; it rejects already-visited, obstacle, and start cells.

Direction codes:

| Code | Direction | Coordinate effect    |
|-----:|-----------|----------------------|
|   1  | west      | column decreases     |
|   2  | south     | row increases        |
|   3  | east      | column increases     |
|   4  | north     | row decreases        |

Row indices increase southward, matching the location-map data convention.

The high-nibble inbound-direction codes form a parent-pointer trail: stepping *opposite* each cell's high-nibble direction from the goal cell yields the chain of cells back to the start. Reversing that sequence is the route from start to goal — exactly what the walker queues into the NPC's move queue.

### 8.3 The workspace builder

The builder constructs the workspace in five phases.

**Phase 1: marker selection.** A mode byte from the caller selects one of three search shapes:

- *Coordinate goal* — caller supplied an explicit (x, y) target. No tile-ID search; goal stamped at the supplied cell in phase 5.
- *Tile-ID goal A* / *Tile-ID goal B* — find the nearest tile matching one of two paired chair tile IDs (the chair-search variant; Section 8.5).

**Phase 2: per-cell walkability fill.** The builder iterates every cell. For each, it asks a walkability predicate "could this NPC legally stand on this cell, given its schedule waypoint and the location's current floor?". The predicate consults a per-tile passability bitmap (256 bits indexed by tile ID; "1" means passable for NPCs) plus a few extra rules — out-of-bounds returns "blocked", tiles where another NPC is mid-route return "blocked". Accepted cells are stamped open; rejected cells become obstacles.

**Phase 3: tile-ID goal markers.** When the mode flag is one of the two tile-ID modes, the builder walks the live world-tile array; cells whose live tile equals the marker become goal sentinels.

**Phase 4: dynamic-obstacle overlay.** The builder walks the active-object table and, for each occupied slot whose Manhattan distance from the NPC's destination is less than four, stamps the object's cell as obstacle. The player's position is included. The Manhattan-radius-four cutoff is deliberate: the BFS queue is small enough that obstacles further away cannot influence the route.

**Phase 5: goal stamp and start stamp.** When the mode flag was "coordinate goal", the supplied cell is stamped with the goal sentinel. For all modes, the start cell is stamped with high nibble 4 (seed direction "north"); BFS reads the seed as its initial direction.

### 8.4 The BFS

A textbook breadth-first search over a small queue. Each iteration:

1. **Dequeue a cell.** The cell's high nibble is the "current direction" — the direction the BFS arrived from.
2. **For each of four cardinal directions in cyclic order:** try the corresponding neighbour cell. If in-bounds and passing the visit gate:
   - Capture the neighbour's low nibble *before* writing.
   - Stamp the neighbour with `direction << 4`.
   - If the captured low nibble was the goal sentinel, the search has found the goal: write the cell coordinates to the pathfinding-output globals and return success.
   - Otherwise enqueue the neighbour.
3. **If the queue runs dry**, return failure.

The queue is a small circular FIFO of `(x, y)` byte pairs with capacity thirty-two. On a sufficiently open map the queue can exhaust before reaching a distant goal; the caller accepts that as "no route in budget" and falls back (state stays unchanged, NPC stays put, next tick retries). The destructive overwrite during the visit-mark phase is fine because the goal value is captured *before* the write.

Once BFS succeeds, the walker traces the high-nibble trail from goal back to start, reverses the sequence, and writes the resulting direction codes into the NPC's move queue. State is set to 3, and subsequent ticks dequeue and apply.

### 8.5 The chair-search variant

A common NPC routine is "go sit on a chair". The schedule's waypoint coords for "sit at the bar" point to the cell *in front of* the chair, not to the chair itself, because the chair is impassable terrain and the schedule waypoint must be a cell the NPC can reach. The chair-search variant bridges that gap.

The walker invokes the variant when an NPC's schedule says "sit" (Section 9) and the NPC has reached the schedule waypoint coords. The variant runs the pathfinder in tile-ID search mode with the marker set to one of two paired chair tile IDs. Two markers exist because chairs come in two facing-direction pairs in the tile encoding, and the walker picks a marker based on which cardinal direction the NPC is approaching from. The pathfinder returns the coordinates of the nearest matching chair tile, and the walker steers the NPC there for a final "sit" pose. Implementations that do not care about chair-facing match can use a single chair-tile-ID set; the visible behaviour is "the NPC sits on the chair adjacent to their schedule waypoint".

## 9. AI behaviours

The schedule's three `ai` bytes — one per waypoint — encode a per-waypoint behaviour modifier. An NPC at waypoint zero with `ai[0]` set to "wander" paces around the waypoint cell rather than standing still; "sit" triggers the chair-search variant; "stationary" pins the NPC to the cell.

The exact value-to-behaviour map is not yet fully enumerated. The family of behaviours is:

- **Stationary.** NPC remains on the waypoint cell; no per-tick movement.
- **Wander.** NPC paces around the waypoint within a small radius (typically a one-cell random-walk biased toward returning).
- **Sit.** NPC walks to the waypoint then triggers the chair-search variant.
- **Sleep.** Variant of stationary using a "sleeping" tile graphic.
- **Patrol.** Multi-cell route between waypoints; less common.

The AI byte does not affect the *target* the schedule resolves to — that is purely the (x, y, z) for the active waypoint. It only affects what the NPC does once they arrive. The exact byte values matching the original game have not been pinned down here.

## 10. Movement constraints

Several rules govern whether a candidate cell is a legal step. All are consulted by the workspace builder's per-cell walkability predicate (Section 8.3).

**Tile passability.** A 256-bit bitmap, indexed by tile ID, identifies which tiles are walkable for NPCs. Walls, water, and lava are clear; floors, grass, and stone roads are set.

**Active-object collisions.** Other NPCs and the player occupy cells in the active-object table. Occupied cells are reported as "blocked" when the occupant is within the dynamic-obstacle scan radius (Manhattan four from the destination). Outside that radius, the cell is treated as walkable — the BFS budget cannot reach there anyway.

**Player collision.** The player is an entry in the active-object table and is blocked by the dynamic-obstacle overlay. NPCs never step into the player's cell, even if the schedule's waypoint coordinate happens to match.

**Z-level transitions.** Floor changes happen via stairway tiles. When an NPC needs to change floors, the state machine routes through states 4–7 to steer toward a stairway, the world-mutation primitive detaches the NPC from the active-object table, and the NPC re-emerges on the new floor at the matching stairway. The schedule does not encode "which stairway"; the pathfinder picks whichever is reachable.

**Out-of-bounds.** The 32×32 cell grid is hard-bounded.

## 11. The world-mutation primitive

Every successful NPC step ends with a single call to a world-mutation helper that maintains the link between the *logical* NPC (with a schedule and runtime block) and the *visual* NPC (with an on-screen sprite). The helper is the only place in the schedule system that touches the on-screen sprite layer.

The helper takes the NPC index and the new `(x, y, z)`, and dispatches on the relationship between the new floor and the location's current floor:

- **Arriving on the player's floor, not yet linked.** Allocate a slot in the active-object table, fill it with the NPC's tile, type, and new coordinates, store the slot index in `linked_obj`. The NPC is now visible.
- **Moving on the player's floor, already linked.** Update the linked slot's coordinates. The sprite walks visibly.
- **Leaving the player's floor, currently linked.** Free the slot (clear its type byte) and zero `linked_obj`. The NPC is now invisible.
- **Neither arriving nor leaving.** No sprite-layer action.

After the sprite dispatch, the helper *unconditionally* writes `(x, y, z)` into the runtime's `(target_x, target_y, current_z)` and resets the state byte to "idle" (state 1). Every step ends in state 1; the next tick's boundary trigger and dispatch decide whether to re-enter movement.

The helper also consults a per-scene "hidden NPC" bitmask when allocating a sprite: certain NPCs are flagged as invisible-by-default in particular scenes (typically to hide a quest NPC who appears only under specific conditions). When a hidden bit is set, the sprite gets a "transparent" tile rather than the NPC's normal appearance — the slot is still allocated; only the visual is suppressed. This lets named NPCs appear and disappear as the plot advances.

A special-case rule covers the "default human" NPC type: when the type byte is a particular sentinel value, the sprite tile is forced to a single hard-coded "person" tile rather than being derived from the type.

## 12. Hooks into other systems

**Time.** The scheduler reads the shared hour byte, never writes it. The hour byte is updated by the time spec's per-turn cleanup. A clock running purely in hours is sufficient (Section 3). The cadence of one scheduler tick per player-turn is set by the town turn loop.

**Active objects (sprites).** Sprites are owned by the active-object subsystem; the schedule system only holds a slot index in the runtime block and only touches the slot table from the world-mutation helper. The active-object animator, run independently each render frame, draws the per-NPC sprites.

**World tiles.** The schedule system reads the live world-tile array for the chair-search variant (Section 8.5). It does not modify the array directly; tile changes that happen as a side effect of NPC movement (e.g. a door tile being walked through) are owned by other code paths.

**Look / inspect.** The paired "chair" tile IDs are also recognised by the look/inspect system. The schedule system writes nothing to look/inspect tables; it only consumes the same tile-ID encoding.

The scheduler does *not* talk to the dialogue system. The `dialog_index` byte loaded with the schedule is consumed by the dialogue overlay when the player initiates a conversation.

## 13. Persistence

The on-disk schedule is read-only: a save game does not embed copies of `TOWNE.NPC` and friends. The runtime state — runtime block, move queue, queue pointer, stuck counter — is *not* explicitly persisted as a chunk. On save-and-load, the engine re-loads the schedule sub-block from the appropriate `.NPC` file, runs the same initialisation pass that runs on first entry (Section 4), and recomputes the active waypoint from the saved hour byte. The NPC therefore reappears at their current waypoint, regardless of mid-route progress before the save. Saving inside town does not freeze NPCs at their exact position; it resets them to "currently scheduled location".

The scene byte and floor byte that drive location selection *are* persisted (they belong to the world state, not the schedule state). The first scheduler tick after load uses them to pick the right `.NPC` block and the right floor.

## 14. Open questions and variations

- **AI-byte value enumeration.** Section 9 names the behaviours but does not pin individual byte values to them. A dump of `AI[]` values from `TOWNE.NPC` and empirical correlation against in-game routines is the next step.

- **Chair tile IDs.** The chair-search variant's two markers correspond to two tile IDs, but the empirical correspondence between tile ID and "north-facing chair" or "east-facing chair" has not been verified.

- **Hidden-NPC bitmask.** Section 11's per-scene mask is one bit per NPC slot per scene, but the encoding of which conditions cause which bits to be set is plot-dependent and not enumerated here.

- **State 8.** Transitions in are clear (Section 6); transitions out happen indirectly via the next hour tick's boundary trigger. An implementer may safely treat state 8 as "re-enter the boundary check at the next opportunity".

- **Stuck counter thresholds.** The exact threshold at which the counter forces a queue reset is a small constant; implementations should pick a value that produces smooth behaviour and tune empirically.

- **Out-of-town NPCs.** Lord British in the intro and various plot-scripted overworld NPCs do not use this system; they belong to a separate "outdoor NPC" path.

- **Multi-NPC tick ordering.** The walker iterates slots `1..31` in slot-order; lower-indexed NPCs move first within a tick. This is observable but is not a gameplay-visible bug.

- **Stairway selection.** When a Z-mismatch forces an NPC to climb floors, the pathfinder picks "the nearest matching stairway tile" via the chair-search-style tile-ID search. Specific stairway tile IDs are not enumerated here.

- **Manhattan-radius-four constant.** The dynamic-obstacle scan radius (Section 8.3 phase 4) tracks the BFS queue's reach. Implementations with a larger BFS budget should scale the radius accordingly.

- **Rest / time-elapsing command path.** A second caller invokes the per-tick walker when a *Hole-up* command advances the clock by hours. The cadence is one walker tick per in-world hour during rest, so an NPC moves at most one cell per in-world hour. The exact loop structure is owned by the rest command, not the scheduler.

## 15. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The roster-load sub-step that runs on location entry — `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md`.
- The hour-to-waypoint selection rule and the wraparound-to-waypoint-1 behaviour — `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md`.
- The per-tick walker, the eight-state machine, the runtime block, the move queue, the stuck counter, and the per-tick scratch flags — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The location-entry initialisation pass — `u5-decomp/functions/NPC_OVL/0x00D6_npc_init_runtime_state.md`.
- The boundary-trigger sub-step and the floor-classification table — `u5-decomp/functions/NPC_OVL/0x0938_npc_should_act.md`.
- The flood-fill BFS, the workspace cell encoding, and the high-nibble inbound-direction trail — `u5-decomp/functions/NPC_OVL/0x032C_npc_pathfinder.md`.
- The chair-search variant's two-marker dispatch — `u5-decomp/functions/NPC_OVL/0x01A0_npc_path_probe.md`.
- The five-phase workspace builder, the walkability predicate, and the dynamic-obstacle overlay — `u5-decomp/functions/NPC_OVL/0x01D2_npc_floodfill_workspace_prep.md`.
- The world-mutation helper, the hidden-NPC bitmask, and the default-human tile sentinel — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The town turn loop's once-per-turn invocation of the scheduler — `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The on-disk `.NPC` file layout — `u5-decomp/formats/npc-tlk-pth.md`.
- The save-format omission of NPC runtime state and the location-entry re-initialisation that fills its place — `u5-decomp/formats/saves.md`.
