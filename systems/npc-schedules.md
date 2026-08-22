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

Each file is the same fixed size (4,608 bytes) and is internally a flat array
of eight per-location blocks of 576 bytes each. The resident scene byte is
one-based across the full named-location range: `1..8` are towns, `9..16` are
dwellings, `17..24` are castles, and `25..32` are keeps. The loader resolves
the file family with `(scene - 1) >> 3` and the sub-map block within that file
with `(scene - 1) & 7`.

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
- **Stuck counter** — a word per NPC, incremented every tick the NPC fails to make progress. The ordinary replanning threshold is small: once the counter is greater than three, the move-queue read pointer is reset to the inactive sentinel and the counter is cleared, forcing a fresh route on a later tick. The same counter also has a high-range guard (Section 14) that prevents runaway stall accumulation.

Two per-tick scratch booleans are shared by every NPC: an "any NPC moved" flag and an "any tile changed" flag. Both are cleared at the start of every tick; the town turn loop reads "any NPC moved" to decide whether the screen needs a repaint.

**Initialisation.** When the engine enters a location, a single pass walks the runtime table. For every occupied slot, the active waypoint for the current hour is computed (Section 3 selection rule); its `(x, y, z)` is copied into the runtime's `(target_x, target_y, current_z)` (the NPC is placed *at* its current waypoint on entry — no walk-from-yesterday sequence); the state byte is set to "idle"; the cached waypoint index is set to the freshly-computed waypoint so the next tick will not falsely fire a transition; the type field is mirrored; the move queue, queue pointer, and stuck counter are reset. For empty slots (on-disk type byte zero), only the state byte is cleared; the per-tick walker skips empty slots before reading any other field.

## 5. The schedule processor

The schedule processor — the per-tick walker — runs once per player-turn from the town turn loop, with the current hour byte as its only input. It also runs from the H-Hole-Up hours path while rest time is being simulated outside the normal mode loop. The overworld and dungeon mode loops do not invoke this scheduler.

Per call, the processor:

1. **Clears the per-tick scratch flags** so the caller can read them on return.
2. **Iterates NPC slots `1..31`.** Slot 0 is the unused sentinel.
3. **Skips empty slots.**
4. **Looks up the active waypoint** for the current hour.
5. **Reads the current state byte.** If state is "idle" (state ≤ 1), the processor first calls a *boundary trigger* sub-step (Section 6) that detects whether the current hour exactly matches one of the NPC's four schedule boundaries; on a hit it reclassifies the state byte.
6. **Dispatches on the (possibly updated) state byte** through the eight-state machine (Section 7) — cardinal-direction probes, optionally a pathfinder invocation, and zero or one position update via the world-mutation primitive (Section 11).
7. **Maintains the move queue.** If the dispatch chose to replay a cached path, the next direction byte is dequeued and applied. If the dispatch produced a new path, the queue is filled. If the NPC fails to make progress, the stuck counter is bumped. A value greater than three resets the queue read pointer and clears the counter so the NPC can replan; high-range counter handling is bookkeeping/visual-exactness territory, not a separate pathfinding state.

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

The floor index grows upward: "above" means a numerically larger floor byte than the location's current floor, and "below" means a numerically smaller one. This is the same orientation the player-facing climb commands use, where climbing an ascend link raises the floor byte and a descend link lowers it.

After classifying, the trigger does one extra check: if the NPC's runtime `(target_x, target_y, current_z)` already equals the new waypoint's `(x, y, z)`, the NPC is already on the waypoint and state is reset to "idle".

The trigger does *not* update the cached waypoint field. It only compares the
cached value against the active waypoint and writes the movement state. The
per-tick walker updates the cached waypoint later, after route replay or step
application has resolved the transition to the newly active waypoint; at that
point it also settles the NPC back to the idle state and deactivates the active
move queue. Until that settle path runs, the cached value intentionally remains
old so a still-unresolved boundary transition can keep reclassifying on later
ticks.

## 7. The state machine

The state byte takes values in `0..8`:

| State | Name                           | What the tick does                                                                                                |
|------:|--------------------------------|-------------------------------------------------------------------------------------------------------------------|
| 0     | empty / unused                 | Slot is empty; the walker skips it before reading the state byte.                                                |
| 1     | idle / settled                 | NPC is at its currently-active waypoint with nothing to do. The boundary trigger may upgrade it.                 |
| 2     | in-plane move                  | Both NPC and target are on the player's floor; probe cardinal directions, run the pathfinder, commit a step.     |
| 3     | replaying cached path          | A pathfinder run earlier produced a queued route; pop the next direction byte and apply it.                      |
| 4     | off this floor, above          | NPC's floor is above the displayed floor and the active waypoint is on the displayed floor. Search the displayed floor for an **ascend-link** cell (`0xC8`), route to it, then surface there. |
| 5     | off this floor, below          | NPC's floor is below the displayed floor and the active waypoint is on the displayed floor. Search the displayed floor for a **descend-link** cell (`0xC9`), route to it, then surface there. |
| 6     | on this floor, waypoint above  | Ask the floor-transition gate whether the NPC already stands on an **ascend link** (`0xC8`) or a stairway tile. If it does, hand the NPC off to the waypoint's floor. If not, route toward the nearest `0xC8` cell.                |
| 7     | on this floor, waypoint below  | Mirror of state 6 using the **descend link** (`0xC9`).                                                            |
| 8     | neither end on this floor      | The NPC is placed directly at the active waypoint's `(x, y, z)` with no gate; the cached waypoint is updated, the move queue is deactivated, and the state returns to idle. |

A few observations. State 3 is the queue-replay path: once the pathfinder
produces a route, subsequent ticks dequeue and apply, and the pathfinder is not
re-invoked until the queue drains or resets. States 2, 4, 5, 6 and 7 all run
"search, route, step"; the structural difference is *what the search is hunting*
— the waypoint coordinate for the in-plane state, and a floor-link tile for the
four floor-transition states. There is no per-direction sweep and no
direction-priority ordering in these states; the only per-state input to the
search is which of the two floor-link markers it looks for (Section 8.5).

At most one NPC per tick may start a fresh search. The walker latches a
"someone already moved" flag on the first slot that enters a search arm, and
every later slot in the same tick that would have searched is skipped until the
next tick. Queue replay is not affected by the latch.

State 8 covers an NPC whose stored floor and active waypoint floor are both away
from the location's current floor. It is *not* a parked state: the walker
resolves it immediately by writing the active waypoint's `(x, y, z)` straight
into the NPC's runtime position, caching the waypoint, deactivating the move
queue and returning the state to idle. Because neither the old nor the new
position is on the displayed floor, no sprite is allocated and nothing is
visible; the NPC simply teleports off-screen to where its schedule says it
should be. The same ungated placement is what happens if any unexpected state
value reaches the floor-transition arm.

The state byte is written by initialisation (1 for occupied, 0 for empty), by
the boundary trigger (1, 2, 4, 5, 6, 7, or 8), by the pathfinder-success path
(3), by the off-floor arrival path (2, once the NPC has surfaced on the
displayed floor), by the floor hand-off and ungated placement paths (1), and by
the world-mutation primitive (1 — "settled" — on every successful move). The
"settled" write at the end of every successful move is what eventually drains a
state-3 queue back to state 1.

One further transition closes the loop for the on-floor transition states: when
a queued route drains while the NPC is still in state 3, the walker re-reads the
active waypoint and re-enters state 6 or 7 according to whether that waypoint's
floor is above or below the displayed floor. That is how an NPC that has just
walked onto a link tile gets re-offered to the floor-transition gate on the next
tick.

That one transition also ends the tick. It is the only path in the walker that
leaves the per-slot loop early: after rewriting the state to 6 or 7 the walker
returns immediately, so every slot after the one that triggered it is skipped
for that tick and resumes on the next one. Nothing else in the pass short-cuts
the loop this way — every other arm falls through to the loop tail and the next
slot. An implementation that instead continues iterating will let other NPCs
take an extra step on exactly the ticks where one NPC finishes a route toward a
floor link, which is observable as a one-tick timing difference in busy
locations.

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
- *Ascend-link goal* — every cell on the displayed floor whose live tile byte is the ascend floor-link marker `0xC8` becomes a goal.
- *Descend-link goal* — every cell on the displayed floor whose live tile byte is the descend floor-link marker `0xC9` becomes a goal.

The two tile-ID shapes are the floor-link variant of Section 8.5. They are
selected by the caller, never inferred from map content, and the builder never
mixes them: one call hunts `0xC8` cells or `0xC9` cells, never both.

**Phase 2: per-cell walkability fill.** The builder iterates every cell. For
each, it asks an NPC-specific predicate "is this cell open for this NPC
pathfinding workspace, given the NPC's active schedule waypoint and the
location's current floor?". This predicate is separate from the shared
foot/vehicle terrain-query dispatcher in `systems/movement.md`. It answers in
three ways — *blocked*, *open*, and *open because this cell is the NPC's own
active waypoint* — and the builder treats both open answers identically,
stamping the cell open. Only the blocked answer produces an obstacle. Section 10
gives the rules the predicate applies, in order, and the tile-id set behind
them.

The waypoint-match answer matters: an NPC's authored waypoint routinely sits on
a tile that the pathfinding tile set otherwise treats as an obstacle — a bed, a
mirror, a well, a counter — and the match rule is the only reason the NPC can
ever route onto its own destination. It is an escape hatch for one specific
cell, not a general relaxation.

**Phase 3: tile-ID goal markers.** When the mode flag is one of the two tile-ID
modes, the builder walks the live world-tile array; every cell whose live tile
equals the selected marker becomes a goal sentinel. The stamp is applied after
phase 2 has already written that cell, so goal status always wins over whatever
the walkability answer was. In practice both floor-link ids are already open
under the tile set, so this ordering does not rescue an otherwise-blocked cell
for them; it does guarantee that a goal cell is a goal even if a future map or
tile-set change made it an obstacle.

**Phase 4: dynamic-obstacle overlay.** The builder walks the active-object
table and, for each occupied slot whose Manhattan distance from the NPC's
runtime destination is strictly less than four, stamps the object's cell as an
obstacle. The player's position is included through the same distance rule.
This radius is a compatibility constant, not a derived tuning knob: objects at
Manhattan distance four or greater from the destination are ignored by this
overlay even if a different implementation could search farther.

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

### 8.5 The tile-ID floor-link variant

When a schedule transition forces an NPC to bridge floors, the walker needs a
map-authored link point rather than the final schedule coordinate. The tile-ID
floor-link variant supplies it.

**The two markers.** Two tile ids act as authored floor links in location tile
grids:

| Tile id | Role | Player-facing meaning |
|---|---|---|
| `0xC8` | **Ascend link** | Standing on it and climbing raises the floor index by one. |
| `0xC9` | **Descend link** | Standing on it and climbing lowers the floor index by one. |

Both share the same shipped description text, so a Look at either reports the
same thing; only their behaviour distinguishes them. They are ordinary members
of the tile-id space and are not the visible stairway family `0xC4..0xC7`, nor
the Stonegate step-trigger tile `0x8C`.

**Which marker a state selects.** The live tile grid only ever holds the floor
the player is on, so the search always runs on the displayed floor. The rule is
a single sentence: *the walker hunts the link that points toward whichever floor
is not the displayed one.*

| State | NPC's floor | Active waypoint's floor | Marker searched |
|------:|-------------|-------------------------|-----------------|
| 4 | above the displayed floor | the displayed floor | `0xC8` (ascend link) |
| 5 | below the displayed floor | the displayed floor | `0xC9` (descend link) |
| 6 | the displayed floor | above the displayed floor | `0xC8` (ascend link) |
| 7 | the displayed floor | below the displayed floor | `0xC9` (descend link) |

For states 4 and 5 the "other floor" is where the NPC currently stands, so the
NPC is hunting the displayed floor's link *up to itself* (state 4) or *down to
itself* (state 5). For states 6 and 7 the "other floor" is where the waypoint
is, so the NPC hunts the link that leads there.

**How each pair of states uses the result.** The two halves of the table do
different things with the cell the search returns.

*States 4 and 5 — the NPC is off the displayed floor.* The search runs first;
if no link cell is reachable within the search budget the NPC does nothing this
tick. On success the walker plans a route from that link cell toward the
waypoint, records one step of it, and then re-reads the live tile at the link
cell. If that tile is the state's own marker, or any tile in the stairway family
`0xC4..0xC7`, the NPC is placed on the displayed floor at that cell and switched
to the ordinary in-plane movement state. This is the moment an off-floor NPC
becomes visible: it appears standing on the link, then walks the rest of the way
normally.

*States 6 and 7 — the NPC is on the displayed floor.* A gate runs **before** any
search. The gate reads the live tile under the NPC's own cell and accepts only
if that tile is the direction-matching link — `0xC8` when the waypoint floor is
above, `0xC9` when it is below — or a stairway-family tile. When the gate
accepts, the walker writes the NPC's position directly to the active waypoint's
own `(x, y, z)`, caches the waypoint, deactivates the move queue and returns the
state to idle; the NPC leaves the displayed floor and its sprite is released.
When the gate refuses, the walker falls back to the tile-ID search for the
matching marker, routes toward it and enters the queue-replay state, so the NPC
walks onto the link and passes the gate on a later tick.

Two consequences worth stating explicitly, because they are easy to get wrong:

- There is no "paired marker cell on the destination floor". Nothing matches a
  link cell on one floor against a link cell on another. An off-floor NPC lands
  on the link cell the search found on the *displayed* floor; an on-floor NPC
  lands on its schedule waypoint's own coordinates, wherever they are.
- The schedule never says which link to use. Route selection is entirely
  "nearest reachable cell carrying the selected marker", measured by the same
  breadth-first search used for ordinary movement, so an authored map with
  several links routes the NPC through whichever one the search reaches first.

**Stairway acceptance.** Both halves also accept the visible stairway family in
place of a link marker, which is what lets NPCs use a stairwell where the map
author placed one instead of a ladder. The two acceptance tests are not
identical in the analysed baseline: the on-floor gate accepts a slightly wider
band of tile ids than the off-floor arrival test does, additionally treating
`0xCC..0xCF` as stairway-like. Those four ids carry no description text and do
not appear as authored floor links in shipped location data, so the widening has
no observed effect on shipped maps; an implementation aiming at byte-level
parity should still reproduce it.

## 9. AI behaviours

The schedule's three `ai` bytes -- one per waypoint -- encode a per-waypoint
behaviour modifier. The active waypoint is chosen by the time-boundary rule
first; then the matching AI byte decides what the NPC does at or near that
waypoint.

| AI value | Behaviour |
|---:|---|
| `0` | Stationary. The NPC remains at the selected waypoint unless another state, such as floor transition routing, is already in progress. |
| `1` | Bounded random wander. The NPC occasionally takes a random cardinal step but rejects moves that would leave a small radius around the waypoint. |
| `2` | Unbounded random wander. The NPC occasionally takes a random cardinal step without the waypoint-radius limit. |
| `3` | Follow or shadow the player at distance. If the player is too close, it falls into the chase/engagement family rather than standing still. |
| `4` | Approach-and-attack family. While the player is far enough away, the NPC uses the wander step with a shrinking range around the waypoint; when close, it can raise the town-mode attack event. |
| `5` | Reserved engage path. The dispatcher has a slot for it, but shipped `.NPC` data does not use it. |
| `6` | Guard/blocking event family. It shares the follow-distance movement path but raises the non-attack guard event when adjacent. |
| `7` | Randomized chase/engage family. It uses the engagement path with occasional direction variation. |

Values greater than `7` fall through to the no-action/default case. The AI byte
does not affect the *target* the schedule resolves to -- that is purely the
(x, y, z) for the active waypoint. It only affects what the NPC does once that
waypoint is active.

## 10. Movement constraints

Several rules govern whether a candidate cell is a legal step. All are consulted by the workspace builder's per-cell walkability predicate (Section 8.3).

**Tile passability.** NPC pathfinding does not reuse the foot/avatar or vehicle
terrain-query families from `systems/movement.md`. Its workspace builder uses a
dedicated one-bit-per-tile-id resource covering the full `0x00..0xFF` terrain
id space. **A set bit marks the tile id as an obstacle for NPC pathfinding; a
clear bit marks it open.** This is a pathfinding workspace rule, not a general
claim about which tiles are physically walkable by the player, and it is not
the same set as any of the player transport sets.

The predicate resolves in this order:

1. **Waypoint match.** A candidate whose `(x, y, z)` equals the selected
   schedule waypoint is reported open regardless of its tile id, and is
   distinguished from an ordinary open cell so a caller can tell the two apart.
   The workspace builder does not distinguish them: it stamps both open.
2. **Out-of-bounds.** X or Y outside `0..31` does not fault. The analysed
   baseline resolves such a probe to the byte that sits at the very end of the
   live tile grid — that is, to the grid's own last cell — and then applies the
   tile-set test to it. Passability of an out-of-bounds probe therefore depends
   on whatever tile the current map happens to carry in its final cell rather
   than on a dedicated constant. An implementation that simply rejects
   out-of-bounds candidates matches shipped behaviour on every map whose final
   cell is an obstacle tile, which is the usual case, but the two are not the
   same rule.
3. **Floor-link fast path.** While an NPC is replaying a cached path, the two
   floor-link ids `0xC8` and `0xC9` short-circuit to open without consulting the
   tile set. Both ids are already clear in the tile set, so this path changes
   nothing about the result; it is a shortcut, not a special case, and it must
   not be read as "floor links are blocked as intermediate cells".
4. **Tile-set test.** Otherwise, the tile id's bit decides: set means obstacle,
   clear means open.

For the analyzed DOS baseline the tile set marks these ranges as **obstacles**
for NPC pathfinding:

| Tile ids | Shipped description families |
|---|---|
| `0x01..0x03` | Deep water, water, and shoals. |
| `0x0C..0x0D` | Mountains and high peaks. |
| `0x10..0x1C` | Huts, shrines, keeps, settlements, cave/mine/dungeon entrances, lighthouse, and the world-map bridge run. |
| `0x27..0x2B` | Roof, crystal sphere, bright light, and hollow stump. |
| `0x2E..0x3F` | Fruit tree, cactus, the world-map grass art run `0x30..0x37`, gargoyle, and the mighty-castle run. |
| `0x41..0x43` | Codex, mast, and rail. |
| `0x46` | Pillar. |
| `0x4A..0x69` | Arrow slit, window, pile of rocks, stone/nicked/plain walls, crenellations, anvil, window shelf, potted plant, crowded bookshelf, the Guardian tile, and river variants. |
| `0x6C..0x86` | River variants, strange walls, pendulum, stocks, manacles, and metal grate. |
| `0x88..0x8F` | Cannonballs, torture rack, loose brick, harpsichord, guillotine, and molten lava. |
| `0x94..0xA9` | Tables, odd door, portcullis, table with food, the three mirror ids, deep well, hitching post, stack of logs, desk, barrel, wine cask, vanity, and pitcher. |
| `0xAB..0xB7` | Bed, chest of drawers, end table, heavy footlocker, flickering torch, hot brazier, meat on a spit, and cannon. |
| `0xB9` | Locked door. |
| `0xBB..0xC3` | Locked door with a window, fireplace, street lamp, candelabrum, hot stove, and the unnamed ids up to the stairway family. |
| `0xCA..0xFF` | Wooden fence, waterfall, moon gate, desert, the Flame family, collapsed dungeon entrance, flagpole, water, hourglass, the Britannia standard, the shop signs, the grandfather clock, bellows, wall, and darkness. |

Everything not listed above is open. Written out, the open ids are `0x00`,
`0x04..0x0B`, `0x0E..0x0F`, `0x1D..0x26`, `0x2C..0x2D`, `0x40`, `0x44..0x45`,
`0x47..0x49`, `0x6A..0x6B`, `0x87`, `0x90..0x93`, `0xAA`, `0xB8`, `0xBA`, and
`0xC4..0xC9`: swamp, grass, brush, desert, trees, tropical forest and foothills;
bridges, desert and the road run; wooden planks and cobble; pier and the two
bridge/NPC-marker ids; carpet; the archway; the chair family `0x90..0x93`; the
two unlocked door ids `0xB8` and `0xBA`; and the stairway family `0xC4..0xC7`
together with both floor links `0xC8` and `0xC9`.

The door ids are the sharpest confirmation that the polarity above is the right
way round: the plain wooden door `0xB8` and the wooden door with a window `0xBA`
are open for NPC routing, while the locked door `0xB9` and the locked door with
a window `0xBB` are obstacles. NPCs walk through unlocked doors and are stopped
by locked ones.

Two consequences fall straight out of that split and are easy to get backwards:

- **Chairs are walkable for NPC routing and beds are not.** An NPC whose
  schedule seats it in a chair reaches that chair as ordinary open ground; an
  NPC whose schedule beds it down reaches the bed only through the
  waypoint-match rule above, because the bed id is an obstacle. The same is true
  of the mirror and well ids. This is exactly why an NPC parked on a bed or a
  mirror is the thing the Talk status gate detects (`systems/conversation.md`
  Section 2).
- **Both floor links are ordinary open ground.** They are never obstacles at
  any point in the pass. What makes them special is only that the tile-ID search
  mode additionally stamps them as goals.

**Active-object collisions.** Other NPCs and the player occupy cells in the
active-object table. Occupied cells are reported as "blocked" only when the
occupant is within the dynamic-obstacle scan radius: Manhattan distance less
than four from the NPC's runtime destination. Outside that radius, the cell is
treated as walkable by the pathfinding workspace.

**Player collision.** The player is an entry in the active-object table and is blocked by the dynamic-obstacle overlay. NPCs never step into the player's cell, even if the schedule's waypoint coordinate happens to match.

**Z-level transitions.** Floor changes happen through the two authored
floor-link markers `0xC8` and `0xC9`, or through a visible stairway tile.
States 4 and 5 bring an off-floor NPC onto the displayed floor by routing to a
link cell and placing the NPC there; states 6 and 7 send an on-floor NPC away by
requiring it to stand on the direction-matching link and then writing its
position to the schedule waypoint's own coordinates. The world-mutation
primitive is what releases or allocates the sprite as the NPC leaves or arrives.
The schedule does not encode "which link"; the pathfinder picks whichever
carrying cell is nearest and reachable. Section 8.5 has the full contract.

**Out-of-bounds.** The 32×32 cell grid is hard-bounded.

## 11. The world-mutation primitive

Every successful NPC step ends with a single call to a world-mutation helper that maintains the link between the *logical* NPC (with a schedule and runtime block) and the *visual* NPC (with an on-screen sprite). The helper is the only place in the schedule system that touches the on-screen sprite layer.

The helper takes the NPC index and the new `(x, y, z)`, and dispatches on the relationship between the new floor and the location's current floor:

- **Arriving on the player's floor, not yet linked.** Allocate a slot in the active-object table, fill it with the NPC's tile, type, and new coordinates, store the slot index in `linked_obj`. The NPC is now visible.
- **Moving on the player's floor, already linked.** Update the linked slot's coordinates. The sprite walks visibly.
- **Leaving the player's floor, currently linked.** Free the slot (clear its type byte) and zero `linked_obj`. The NPC is now invisible.
- **Neither arriving nor leaving.** No sprite-layer action.

After the sprite dispatch, the helper *unconditionally* writes `(x, y, z)` into the runtime's `(target_x, target_y, current_z)` and resets the state byte to "idle" (state 1). Every step ends in state 1; the next tick's boundary trigger and dispatch decide whether to re-enter movement.

The helper also consults a per-scene "hidden NPC" bitmask when allocating a
sprite. This mask is separate from the town-entry activation/death mask
described in `systems/town-mode.md`: activation decides whether the rostered
slot participates in the scheduler at all, while the hidden mask applies only
after an NPC is already scheduled and being linked to an active-object slot.
When a hidden bit is set, the active-object slot is still allocated and linked,
but its visible tile is the transparent sentinel instead of the NPC's normal
appearance. The logical NPC position, schedule state, collision link, and
conversation eligibility remain tied to the runtime slot; only the sprite is
visually suppressed.

The shipped DOS data sets hidden-sprite bits only for the public scenes below.
The mask is indexed by the town-mode scene order; the public scene byte remains
one-based, so the roster key in the table is the same key used by
`catalogs/npc-roster.md`.

| Public scene | Location | Roster key | Hidden roster slots | Clean role |
|---:|---|---|---|---|
| 1 | Moonglow | `TOWNE:0` | 0 | Reserved slot-zero marker; the scheduler never treats it as a live NPC. |
| 1 | Moonglow | `TOWNE:0` | 1, 2 | Shared shop/service actors. |
| 1 | Moonglow | `TOWNE:0` | 3 | Unnamed occupied human/noble actor using the universal sentinel dialogue id. |
| 1 | Moonglow | `TOWNE:0` | 4 | Zachariah. |
| 1 | Moonglow | `TOWNE:0` | 5 | Malifora. |
| 1 | Moonglow | `TOWNE:0` | 9 | Silent guard or patrol actor. |
| 1 | Moonglow | `TOWNE:0` | 11 | Malik. |
| 5 | Minoc | `TOWNE:4` | 15, 17 | Empty roster slots in the shipped block; the bits are inert unless a compatible data mod occupies those slots. |
| 6 | Trinsic | `TOWNE:5` | 1 | Shared shop/service actor. |
| 29 | Stonegate | `KEEP:4` | 3 | Avatar/free-slot sentinel actor authored into the Stonegate roster. |
| 29 | Stonegate | `KEEP:4` | 4 | Elistaria. |
| 29 | Stonegate | `KEEP:4` | 5, 6, 7, 8 | Animal/pet/livestock-style actors in Stonegate's hidden presentation group. |
| 29 | Stonegate | `KEEP:4` | 9 | Monster-variant actor in Stonegate's hidden presentation group. |
| 30 | The Lycaeum | `KEEP:5` | 5 | Balinor. |
| 30 | The Lycaeum | `KEEP:5` | 6 | Lady Janell. |
| 30 | The Lycaeum | `KEEP:5` | 7 | Gardner. |
| 30 | The Lycaeum | `KEEP:5` | 8 | Rollo. |

These hidden bits do not by themselves activate a slot, create an NPC, or
change dialogue routing. If the roster slot is empty or filtered out by the
activation/death mask, the hidden bit has no immediate visible effect. If the
slot is active, the slot remains present for collision, scheduling, and Talk
targeting while its active-object tile is the transparent sentinel.

A special-case rule covers the "default human" NPC type: when the type byte is a particular sentinel value, the sprite tile is forced to a single hard-coded "person" tile rather than being derived from the type.

## 12. Hooks into other systems

**Time.** The scheduler reads the shared hour byte, never writes it. The hour byte is updated by the time spec's per-turn cleanup. A clock running purely in hours is sufficient (Section 3). The cadence of one scheduler tick per player-turn is set by the town turn loop.

**Active objects (sprites).** Sprites are owned by the active-object subsystem; the schedule system only holds a slot index in the runtime block and only touches the slot table from the world-mutation helper. The active-object animator, run independently each render frame, draws the per-NPC sprites.

**World tiles.** The schedule system reads the live world-tile array for the tile-ID floor-link variant (Section 8.5). It does not modify the array directly; tile changes that happen as a side effect of NPC movement (e.g. a door tile being walked through) are owned by other code paths.

**Look / inspect.** The two floor-link marker IDs share the global tile-ID space with the look/inspect tables. The schedule system writes nothing to look/inspect tables; it only consumes the live tile bytes for pathfinding goals.

The scheduler does *not* talk to the dialogue system. The `dialog_index` byte loaded with the schedule is consumed by the dialogue overlay when the player initiates a conversation.

## 13. Persistence

The on-disk schedule is read-only: a save game does not embed copies of `TOWNE.NPC` and friends. The runtime state — runtime block, move queue, queue pointer, stuck counter — is *not* explicitly persisted as a chunk. On save-and-load, the engine re-loads the schedule sub-block from the appropriate `.NPC` file, runs the same initialisation pass that runs on first entry (Section 4), and recomputes the active waypoint from the saved hour byte. The NPC therefore reappears at their current waypoint, regardless of mid-route progress before the save. Saving inside town does not freeze NPCs at their exact position; it resets them to "currently scheduled location".

The scene byte and floor byte that drive location selection *are* persisted (they belong to the world state, not the schedule state). The first scheduler tick after load uses them to pick the right `.NPC` block and the right floor.

## 14. NPC Schedule Boundaries And Remaining Runtime Exactness

The scheduler contract is complete at mode-integration depth: roster loading,
hour-to-waypoint selection, runtime block ownership, per-turn walking, boundary
state handling, pathfinding workspace construction, dynamic-obstacle avoidance,
floor-link marker handling, sprite placement, persistence omission, and
town-mode/rest-loop invocation cadence are specified. Remaining work is
low-visibility presentation parity outside the scheduler contract.

- **Hidden-NPC bitmask catalogue.** Section 11's per-scene mask is one bit per
  NPC slot per scene and is distinct from the activation/death mask. Its runtime
  effect and the shipped nonempty scene/slot catalogue are now specified. Any
  anonymous occupied slots are labelled by the conservative sprite-tag roles in
  `catalogs/npc-roster.md`; there is no additional hidden-mask scheduler
  contract behind those labels.

- **Long-stall visual parity.** The counter has confirmed short and high
  guard bands. More than three failed-progress ticks invalidates the active
  move queue and clears the counter so the NPC can replan. In the high range,
  the analyzed walker also routes through a last-resort stalled-actor helper
  around the two-hundred-tick band and resets values above that band rather
  than allowing unbounded growth. Current evidence does not identify a
  separate durable gameplay state, persistent schedule mutation, or alternate
  pathfinding state for the high guard. Treat any remaining work as
  presentation/helper parity only if later tracing shows a visible effect.

- **Out-of-town actors.** The scheduler is not a general actor system.
  Outdoor monsters, vehicles, whirlpools, and pre-placed world props live in
  the active-object table and are advanced by the overworld per-turn walker
  described in `systems/active-objects.md` and `systems/overworld.md`. They
  have no `.NPC` schedule, waypoint selection, AI-mode byte, runtime
  descriptor, or flood-fill queue. Title-sequence Lord British signature
  motion is likewise an intro/display path stream, not an NPC schedule. These
  actors are outside the scheduler by ownership, not a missing scheduler
  variant.

- **Multi-NPC tick ordering.** The walker iterates slots `1..31` in slot-order;
  lower-indexed NPCs move first within a tick. This is observable but is not a
  gameplay-visible bug. One arm cuts the iteration short: the state-3 drain that
  re-enters a floor-transition state returns from the whole pass rather than
  continuing to the next slot (Section 7), so higher-numbered slots lose that
  tick.

- **Floor-link selection.** When a floor mismatch forces an NPC to change
  floors, the pathfinder picks the nearest reachable cell carrying the selected
  floor-link marker: the ascend link `0xC8` when the other floor is above the
  displayed floor, the descend link `0xC9` when it is below (Section 8.5). The
  scheduler owns route selection and the on-floor gate; town movement and the
  location/tile catalogues own the visible `0xC4..0xC7` stairway facing contract
  and the player-facing floor-change presentation.

- **Dynamic-obstacle radius.** The active-object/player obstacle overlay uses
  a hardcoded destination-relative Manhattan cutoff: distances less than four
  are blocked, distances four or greater are ignored. This is part of the
  compatibility contract and does not scale with an implementation's internal
  search budget.

- **Rest / time-elapsing command path.** A second caller invokes the per-tick
  walker from the H-Hole-Up hours subroutine. In the traced town-hours path,
  one nonzero rest command can run up to sixteen walker/world-tick passes before
  the elapsed-time cleanup loop, stopping early if the rest loop observes an
  interruption event. The exact visible result of the interruption belongs to
  the rest/encounter specs; the scheduler's contract is only that each call
  advances each NPC by at most one cell.

- **NPC entry scene-byte indexing.** The location scene byte remains a
  one-based public scene id. NPC roster loading uses `(scene - 1) >> 3` for the
  file family and `(scene - 1) & 7` for the block within that file; gameplay
  systems continue to observe the original one-based scene id. The loader's
  temporary arithmetic conversion is restored before control returns, so it
  must not be modeled as a scene change, transition side effect, or persistent
  alternate numbering scheme.

## 15. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The roster-load sub-step that runs on location entry — `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md`.
- The hour-to-waypoint selection rule and the wraparound-to-waypoint-1 behaviour — `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md`.
- The per-tick walker, the eight-state machine, the runtime block, the move queue, the stuck counter, and the per-tick scratch flags — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The location-entry initialisation pass — `u5-decomp/functions/NPC_OVL/0x00D6_npc_init_runtime_state.md`.
- The boundary-trigger sub-step and the floor-classification table — `u5-decomp/functions/NPC_OVL/0x0938_npc_should_act.md`.
- The flood-fill BFS, the workspace cell encoding, and the high-nibble inbound-direction trail — `u5-decomp/functions/NPC_OVL/0x032C_npc_pathfinder.md`.
- The tile-ID floor-link variant's two-marker dispatch, the per-state marker
  selection, and the up/down identity of the two markers — `u5-decomp/functions/NPC_OVL/0x01A0_npc_path_probe.md`
  and `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md`, the latter
  cross-checking the markers against the shipped tile-description table and
  against the town climb handler's floor-index change, and against the town step
  handler's separate `0x8C` trigger in `u5-decomp/functions/TOWN_OVL/0x0F02_town_step_interaction.md`.
- The on-floor floor-transition gate, its direction-matching acceptance test,
  and its wider stairway band — `u5-decomp/functions/NPC_OVL/0x0A4A_npc_floor_transition_gate.md`.
- The five-phase workspace builder, the walkability predicate, and the dynamic-obstacle overlay — `u5-decomp/functions/NPC_OVL/0x01D2_npc_floodfill_workspace_prep.md`.
- The dedicated NPC pathfinding predicate, its three-way answer, the
  out-of-bounds resolution, and the tile-set polarity (set bit means obstacle) —
  `u5-decomp/functions/NPC_OVL/0x0ADC_is_tile_walkable_for_npc.md`,
  `u5-decomp/functions/NPC_OVL/0x0B9E_npc_can_enter_cell.md`, and
  `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md` section 5, which
  re-derives the tile set directly and reconciles two private notes that stated
  the polarity in opposite directions.
- The early return that ends a whole walker pass when a drained route re-enters
  a floor-transition state — `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md`
  sections 1.6 and 5.
- The world-mutation helper, the hidden-NPC bitmask, and the default-human tile sentinel — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The shipped hidden-mask scene/slot catalogue was cross-checked against local
  `DATA.OVL` table reads, the public roster keys in `catalogs/gazetteer.md`,
  and the role-label notes in `u5-decomp/formats/npc-tlk-pth.md`.
- The town turn loop's once-per-turn invocation of the scheduler — `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The on-disk `.NPC` file layout — `u5-decomp/formats/npc-tlk-pth.md`.
- The save-format omission of NPC runtime state and the location-entry re-initialisation that fills its place — `u5-decomp/formats/saves.md`.
- The scene-byte lifecycle audit that resolves the NPC loader's temporary
  scene-index conversion — `u5-decomp/notes/critical_state_lifecycles.md`.
- The outdoor active-object trace that separates overworld monster/vehicle
  motion from `.NPC` scheduling — `u5-decomp/notes/outdoor_npc_scheduling.md`.
