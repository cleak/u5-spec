# Active objects

## 1. Overview

Ultima V's runtime stage - the place where persistent top-down actors live - is
a single fixed-size array called the *active-object table*. Thirty-two slots of
eight bytes each: two hundred fifty-six bytes total in the resident data
segment. One slot is the player; the rest are NPCs, monsters, vehicles, combat
field markers, dropped or scripted props, and other traced entities that need
table-backed position and animation state.

Not every visible effect uses this table. Projectile and impact visuals and
ordinary terrain-animation frames are direct scratch-buffer or renderer effects
unless a specific owning system writes an active-object record for them.
Natural moongates are in neither group: a gate is live terrain written into the
map buffer by the once-per-turn refresh in `systems/overworld.md`, not a slot
and not a render-time stamp.

The top-down world modes and combat read and write this same table. The renderer composites it into the top-down viewport. The visibility pipeline uses the table during compositing to decide which active sprites survive the current visibility grid. The NPC scheduler links into it when its NPCs cross onto the player's floor. Dungeon exploration is the main exception: its first-person view is rendered from dungeon coordinate globals and the loaded dungeon grid rather than by the top-down active-object compositor, although its one wandering monster reuses an eight-byte record in the resident table with dungeon-specific field meanings. When a dungeon room or ambush enters combat, the normal combat framer swaps the table for an isolated combat instance and swaps it back when the fight ends. The save image preserves the table byte-for-byte.

The design is "simple, fixed, and shared." There is no spatial index, no linked list, no per-mode subclass. In top-down world scenes and combat, dynamic on-screen content goes through these thirty-two slots, and every slot is a flat eight-byte record interpreted differently by different systems. This shared, untyped, fixed-size table is what lets the engine's sub-modes hand the world cleanly back and forth while still allowing dungeon exploration to use its separate first-person renderer.

## 2. Table shape

The active-object table is a flat, contiguous, two hundred fifty-six byte block: thirty-two records of eight bytes each. Records are addressed by slot index `0..31`; field offsets within a record are `0..7`. The table lives at a fixed location in the resident data segment, directly readable and writable by every module.

Outside the dungeon wandering-monster interpretation, a slot is *empty* when
its first byte (the type/tile byte) is zero. Allocating a slot writes a non-zero
value to byte zero; freeing a slot writes zero back. Slot zero is reserved for
the player. The convention is unbreakable: every system that wants the player's
on-screen state reads slot zero, and slot zero never gets compacted, swapped,
or stolen. The dungeon exception and its different inactive marker are defined
in Section 3.

Iteration order matters in two distinct passes. The renderer walks slots from thirty-one down to zero so that lower-indexed slots paint on top — this is what guarantees the player (slot zero) draws on top of every other entity in the same cell. The per-tick animator walks slots from zero up to thirty-one; iteration order there does not affect correctness, only deterministic tie-breaking.

## 3. Record fields

Each record's eight bytes are interpreted as follows. Different systems read different subsets and interpret the higher-numbered bytes in slightly different ways; the reader's table below documents the most-evidenced view, with notes on alternative interpretations encountered in different systems.

| Byte | Field        | Description                                                                                                       |
|-----:|--------------|-------------------------------------------------------------------------------------------------------------------|
|   0  | `type`       | Slot type / tile class. Zero = empty slot. Non-zero values double as the tile-class byte the renderer uses.       |
|   1  | `tile`       | Per-frame tile byte. Frequently a duplicate of byte 0 at allocation time; modified during animation playback.     |
|   2  | `x`          | World (or arena) X coordinate, in cells.                                                                          |
|   3  | `y`          | World (or arena) Y coordinate, in cells.                                                                          |
|   4  | `z`          | World floor (or vertical layer). For the overworld, this is the surface/underworld marker.                        |
|   5  | `dep1`       | Auxiliary state byte. For ship/frigate objects this is hull condition; otherwise class-specific.                  |
|   6  | `phase`      | Packed animation phase (low nibble) and direction-step counter (high nibble). Advanced by the animator.           |
|   7  | `dep3`       | Auxiliary flag/aux byte. For ship/frigate objects this is skiffs aboard; otherwise class-specific.                |

Dungeon first-person mode is a deliberate exception to the generic empty-slot
test. It reuses one eight-byte record in this table for its wandering monster,
but family zero is a valid Giant Rat. That record is inactive when `dep1` is
`0xFF`, not when `type` is zero. Its complete field interpretation is specified
in `dungeon-mode.md` Section 6.9. Top-down and combat consumers must not inherit
the dungeon validity rule, and dungeon consumers must not inherit the generic
`type == 0` rule.

A few observations on the field encoding:

**Type-byte conventions.** Byte 0 carries both "is this slot allocated?" (zero / non-zero) and a tile-class identifier (the high six bits used as an index into a per-class attribute table that the animator and dispatcher consult). The low two bits of byte 0 are reserved for sub-type or facing info on certain tile classes. Player identity is not encoded by a special byte-0 value: the player is the record at slot zero. The withdrawn player-as-NPC interpretation in Section 5 must not be revived as a second player sentinel or phantom record.

**The phase byte.** Byte 6 packs two pieces of state into one byte: the low nibble counts down through animation frames (with the all-ones value meaning "rest at steady frame, do not animate"), and the high nibble holds a direction-step counter that AI movement uses. The animator's per-tick rule is: if the low nibble is at the steady-state marker, leave the slot alone; if non-zero, decrement; if zero, the slot is eligible for an AI tick that may pick a new direction or move the slot one cell.

**Auxiliary bytes 5 and 7.** Different systems use these slots differently. For
ship/frigate objects, byte 5 is hull condition and byte 7 is the carried-skiff
count; boarding copies both into the active vehicle state, X-it writes them
back to the parked ship object, and broadsides decrement byte 5 on hit. The
F-Fire broadside path also treats byte 5 as an unsigned depletion counter for
any struck active object: a hit subtracts `1..20`, and if the subtraction wraps
into the high-bit range the command clears the hit slot. This hit-resolution
meaning is layered on top of, and does not replace, the byte's ordinary
family-specific meaning between hits. The renderer reads bytes 5 and 7 only
for specific tile families such as vehicles and water creatures, where they can
hold rider type or next-tile-overlay data. Projectile flight visuals do not use
active-object auxiliary bytes; they are drawn by direct visual-effect helpers
described below. Combat-instance active-object records are still the renderer-facing
table: arena coordinates are in bytes 2 and 3, while byte 5 can be overwritten
by the default monster-death path with a temporary drop marker. The round-loop
fields named in the combat spec -- base-step, phase counter, target slot,
flags, and duplicate arena coordinates -- live in the parallel combat-effect
descriptor table, not in these active-object auxiliary bytes. Byte
interpretation is therefore not type-uniform across world and combat
instances; readers must know which mode is active.

**Coordinate axes.** Bytes 2 and 3 hold cell coordinates. In overworld and town/dwelling/castle/keep modes, they are world coordinates. In combat-instance use, they are arena coordinates on the eleven-by-eleven arena. The renderer's projection step subtracts the player's position to find each slot's offset in the on-screen viewport.

The eight-byte record fits a power-of-two stride. Implementations that prefer parallel arrays per field can split the record without changing the system's contract, as long as slot index mapping stays consistent between the active-object subsystem, the NPC subsystem (which holds slot indices in its runtime block), and the combat subsystem (which writes one record per actor).

## 4. Slot allocation and freeing

The ordinary world/town acquisition path searches only slots one through
twenty-three. Slot zero is the canonical player slot, and slots twenty-four
through thirty-one are reserved for setup paths outside this allocator. Its
first phase is to take an empty ordinary slot, but that is not the whole
contract: if the ordinary range is full, acquisition can evict a lower-priority
object.

The eviction cascade is deterministic:

| Phase | Accepted byte-0 range | Screen test | Meaning |
|---:|---|---|---|
| 1 | `0x00` | none | Empty slot. |
| 2 | `0x01..0x0F` | off-screen | Low-priority scenery/decorations. |
| 3 | `0x80..0xFF`, except `0xB5` | off-screen | Monsters, dynamic actors, or effects. |
| 4 | `0x10..0x11` | off-screen | Door/fixture-like low classes. |
| 5 | `0x30..0x7F` | off-screen | Items, chests, pickups, and midrange objects. |
| 6 | `0x01..0x0F` | any | Same class as phase 2, now visible allowed. |
| 7 | `0x80..0xFF`, except `0xB5` | any | Same class as phase 3, now visible allowed. |
| 8 | `0x10..0x11` | any | Same class as phase 4, now visible allowed. |
| 9 | `0x30..0x7F` | any | Same class as phase 5, now visible allowed. |
| 10 | `0x00..0xFF`, except `0xB5` | any | Last-resort eviction. |

The off-screen test is viewport-sized rather than global-map-sized: a candidate
more than roughly five cells from the player in either axis is considered
eligible for the off-screen phases. The omitted ranges `0x12..0x1F` and
`0x20..0x2F` protect NPC/person-like entries and vehicle-like entries from the
priority phases. The last-resort phase can still take any byte except `0xB5`,
so `0xB5` is the only universally protected byte-0 value in this allocator.
The decoded NPC roster uses `0xB5` as a monster-variant actor class, including
the Grendel row; it is not a moongate renderer. There is no moongate renderer:
natural gates are live terrain written and removed by the once-per-turn refresh
in `systems/overworld.md` Section 9, with no frame plate and no animator.

Slot allocation is centralised in a single resident helper. When a system needs
a new active-object slot -- an NPC arriving on the player's floor, a monster
being placed by combat setup, a summoned creature, or a dynamic world object --
it calls the allocator and receives a slot index. The allocator's first phase
walks the ordinary range for a slot with a zero type byte; if none is
available, the priority cascade above chooses a victim. Spawn-count caps and
mode-entry initialisation usually keep this pressure case rare, but it is part
of the compatibility contract.

Slot freeing is a one-byte write: zero to byte 0. There is no separate free-list, no compaction pass, no garbage collector. Freed slots become candidates for the next acquisition pass, but occupied slots keep their index until freed or explicitly evicted.

A few call sites use a *highest-empty-slot-down* discipline rather than the allocator's lowest-up scan. The town-entry Shadowlord install, for example, walks the parallel NPC type array from index thirty-one down looking for an empty NPC slot, so that low NPC indices stay reserved for the schedule-driven NPCs of the location's own roster. That walk has no failure exit: if every index is occupied it proceeds with index thirty-one and overwrites whatever was there. The discipline lives at the call site, not in the allocator. See `systems/town-mode.md` Section 13.

A second-level helper sits behind the allocator: the *initialiser*. After a slot is allocated, the initialiser takes the slot index plus the tile byte, type byte, target coordinates, and floor, and writes them into the first six bytes of the record in one pass, leaving the animation and auxiliary bytes to the caller or later animator. The split (allocator finds slot, initialiser fills it) lets call sites that already know the slot index -- combat setup, the town-entry Shadowlord install -- bypass the search.

The table is never compacted or defragmented. Repeated allocate-and-free fragments empty slots between occupied ones; that is the steady-state condition and costs nothing measurable at thirty-two slots.

## 5. The player slot

The player occupies slot zero. Every world frame, the compositor refreshes bytes 0..4 of slot zero from the world-state globals (the avatar tile id, the active player's position, the floor index). The renderer then walks the table from slot thirty-one down so slot zero paints on top.

The world-state globals are the *authoritative* source for player position; slot zero is a *derived* view that other systems read — NPCs computing distance to the player, the visibility producer determining what the player blocks. Slot zero is never freed, compacted, or reallocated; mode entries preserve it; the combat backup-and-restore preserves it.

**Retraction — the player has no second representation.** Earlier revisions of
this section described a *player-as-NPC* slot in town / dwelling / castle /
keep modes: a high-indexed NPC slot stamped with a player sentinel type byte,
the player's spawn coordinates in its coordinate fields, and a stationary
three-waypoint schedule pinning the player to the spawn cell. That contract is
withdrawn in full. Every detail of it was read off a single town-entry helper
that has since been re-derived: the helper installs a resident **Shadowlord**
in a town that hosts one, the sentinel byte is the Shadow Lord actor tile
(`systems/town-mode.md` Section 13, `formats/npc.md` Section 6), and the scan
that appeared to be an "existing player slot found, skip" short-circuit is the
Shadowlord's one-at-a-time reject. No traced path gives the player an entry in
the NPC type array, the per-NPC runtime descriptor table, or the schedule
tables. Implement the player as slot zero of the active-object table only.

The one behaviour that formerly rested on the mirror is independently sourced
and unaffected: NPC pathfinding does not need the player to be an NPC. Its
workspace builder stamps nearby occupied active-object cells as dynamic
obstacles and then stamps the player's *current* cell separately, so NPCs
cannot route through the live player position. For compatibility, collision
uses the current player coordinate — there is no stationary mirror coordinate
to consult.

## 6. NPC slots

NPCs in town / dwelling / castle / keep modes occupy slots one through thirty-one. Each named NPC has two parallel runtime representations:

- A **per-NPC runtime descriptor** in a separate sixteen-byte-per-NPC table holding the schedule's pursuit target, pathfinding state, active waypoint, and a *linked-slot index* into the active-object table. Logical state.
- An **active-object record** at the linked-slot index, holding the NPC's tile, on-screen coordinates, and animation phase. Visual state.

The link is the linked-slot field of the runtime descriptor. The world-mutation helper, called by the scheduler on every step, keeps the two halves in sync. It handles four cases:

| Old floor / new floor                              | Active-object slot action                                  |
|----------------------------------------------------|------------------------------------------------------------|
| Off player's floor → on player's floor             | Allocate a new slot, fill the record, set linked-slot.     |
| On player's floor → on player's floor              | Update the existing slot's coordinates.                    |
| On player's floor → off player's floor             | Free the slot (zero its type byte), clear linked-slot.     |
| Off player's floor → off player's floor            | No active-object slot action; logical state only.          |

The active-object table only holds the on-screen cast. NPCs on other floors of the same building exist in the schedule and runtime descriptor but have no slot. When a multi-floor NPC crosses a floor boundary, the helper performs the appropriate free or allocate, and the player sees the NPC disappear or appear at the right moment.

A per-scene "hidden NPC" bitmask layered on top of the floor-visibility check lets specific NPCs be invisible in specific scenes. When an NPC has its bit set in the current scene's mask, the helper still allocates a slot but writes a "transparent" tile byte so the renderer paints nothing. Plot-controlled NPCs (a tied-up Lord British, a hiding spy) are kept on-stage but not visible.

The per-NPC runtime descriptor's slot index and the active-object slot index are independent. Schedule-driven NPCs occupy low NPC indices and land in low active-object slot indices in arrival order; a Shadowlord installed on town entry takes a high *NPC* index and whatever active-object slot the allocator returns. The player's avatar lives at active-object *slot zero* and has no NPC index at all.

## 7. Monster slots

Combat mode uses the same active-object table for combatants, but the contents are different — a combat instance, not a world snapshot. The combat framer's enter/exit save-and-restore (Section 9) is what makes this work: combat overwrites the table with combatant records and restores the world's table on exit.

Within combat there is no reserved player slot and no twenty-six-combatant cap; earlier drafts of this section claimed both and were wrong. The setup pass first clears all thirty-two records, then seats the party, then places monsters. Party members are allocated the first free records, one per live (non-dead) member in roster order, so a full party occupies records zero through five and a party with dead members packs into fewer. Monsters take the next free records. The hard limits are the thirty-two records themselves and, for terrain combat, the sixteen arena placement slots; a terrain encounter can never place more than sixteen monsters (`systems/combat.md` Section 5). Each spawned monster gets one renderer-facing active-object slot with the monster's class-derived tile in byte 0, the per-frame tile byte at byte 1, arena coordinates in bytes 2 and 3, and a floor/plane flag at byte 4. A seated party member's record uses the same shape, with the class-derived party sprite in bytes 0 and 1, its arena seat in bytes 2 and 3, and its roster slot index in byte 5. The higher auxiliary bytes remain mode-specific render/drop scratch rather than round-loop scheduling fields. At placement time byte 5 receives the placed monster's starting HP, byte 4 receives the arena plane/Z argument, and byte 7 receives an all-ones marker; the default monster-death path may later overwrite byte 5 with the class drop-cap value while the temporary combat table is live (`systems/combat.md` Section 6.3). Placements made on the special marker path receive the setup id in both tile bytes and in byte 5, and get no parallel combat descriptor at all.

A *parallel* combat-effect descriptor table holds the additional per-actor state combat needs — base-step, phase counter, target index, flag bits — at a different data-segment location. The two tables are allocated by independent first-free scans: descriptors are taken from index zero for party members and from index six for monsters, while active-object records are always taken from the lowest free index for everyone. For party members the two scans therefore run in lockstep and a member's descriptor index always equals its active-object index, dead-member skips included. For monsters the indexes differ by construction: descriptor six pairs with the first active-object record left free by the seated party, so a party of four puts the first monster at descriptor six and active-object record four. The descriptor's active-object link byte is the authoritative pairing either way, and an engine should follow it rather than assume the indexes match. The two tables are kept in sync by the per-action primitive: when an actor moves, its coordinates are written into both.

The combat-effect descriptor table owns combat-only fields that earlier notes sometimes attributed to the active-object record. Its first byte is the current monster HP or wound counter for non-party actors, it contains the friend/foe faction tag used by target selection, and one byte is a back-reference to the linked active-object slot. The active-object table remains the renderer-facing table during combat; it is not the source of the combat faction byte.

Placed combat fields also live in this temporary active-object table. Their marker records use arena coordinates and are matched by the combat post-action hook when an actor finishes a successful step on the same cell. Marker creation is gated by the arena field helper: target selection and coordinate lookup must succeed, then the COMBAT acceptance callback must accept before the marker/application callbacks run. The coordinate lookup scans combat slots in ascending order and accepts the first selected-coordinate descriptor with `0x80` or `0x40` set, without `0x20` or `0x04`, and without linked active-object tile byte `0xF4`. Contact is non-consuming: the post-action hook applies the field result without clearing, aging, or rewriting the matched marker record. Field markers are active-object-only records rather than paired combat-effect descriptors, so the monster death/record-clear path cannot age or remove them. The accepted-placement resident redraw helper and the generic active-object tick do not allocate, remove, or decrement field marker records. Their presence is combat-local: they persist until the framer restores the pre-combat active-object table on exit.

Projectile and impact visuals are not active-object records. The combat and
spell projectile path builds a temporary line in scratch path buffers, steps
that line, plays per-cell sound/visual effects, flushes the affected screen
area, and stops on collision or at the endpoint. It does not allocate a slot,
write an active-object record, or leave a record to be freed later. Ship and
cannon fire follows the same ownership boundary: the command traces a short
line, renders the shot or impact directly, and then mutates the hit terrain or
hit active-object slot only if the trace finds one. The projectile visual
itself has no persistent table lifetime.

The flight routine also carries no damage payload of its own. It was read from
entry to exit: it builds the line into two scratch coordinate buffers, walks it
drawing a figure per sampled step, and returns a clear/blocked result. It writes
no character record and reaches no damage routine. Damage, where there is any,
is applied by the caller **after** the trace returns clear — for the outdoor
ranged attacks that is the payload in `systems/overworld.md` Section 6.2.4.

The split keeps combat-only state out of the world-mode table. When combat exits, the framer restores the live active-object table from its pre-combat backup, so combat movement, deaths, and loot-marker writes in the temporary table do not directly merge back into world objects. Durable combat outcomes travel through character records, clock/status globals, resources consumed by combat actions, and any encounter-side reconciliation traced outside the table restore. The combat round walker, described in the combat spec, iterates the combat-effect descriptor table for action selection and reads the active-object table for sprite rendering.

## 8. Animation

A per-tick animator runs once per world tick, walking the table from slot zero to slot thirty-one. For each non-empty slot, the animator advances the animation phase and, when the phase reaches zero, may roll an AI direction change for monster-class slots.

The animation cycle uses byte 6's low nibble. It counts down each tick:

| Phase value   | Meaning                                                                                                       |
|---------------|---------------------------------------------------------------------------------------------------------------|
| steady marker | Steady; do not animate this slot. The animator skips. (Encoded as the all-ones nibble.)                       |
| any non-zero  | Mid-cycle. Decrement and write back. The renderer combines the phase with the tile class to pick a frame.     |
| zero          | Cycle ended. Eligible for an AI tick: roll RNG, possibly turn or move, possibly reseed phase.                 |

Each animated class has its current-frame index in a separate animation-frame table; the renderer combines the tile class with that counter to pick the actual byte to paint. The classes this per-slot pass animates are actor classes — vehicles, monsters and the other sprite-only tiles that live in the table. (An earlier revision of this paragraph listed "water (a four-frame cycle), lava, torches, and a small handful of 'special' tiles" as the animated classes. That list is **withdrawn**: no water, lava, brazier or torch tile animates through any per-tick pass. The separate world-tick tile animator touches exactly five terrain families — waterfall, fountain, pendulum, the standard of Britannia, and the clock/bellows pair — and none of them is a water or fire terrain family. See `systems/animation.md` Section 6 and `catalogs/tile-catalog.md` Section 4.)

Two responsibilities sit slightly outside the per-slot loop. A *frame-counter advance* runs at the end of the pass, incrementing a shared frame counter and toggling a few alternate-frame tile classes. A *video-driver flush* runs immediately after, sending the post-tick frame to the display driver. Both are part of the "advance one tick of on-screen state and present it" contract.

Some slots also receive AI ticks during the same pass: hostile creature classes
that wander on the overworld (or in towns past their schedule) get an RNG roll
on their phase-zero tick that may turn or step them one cell. Probability is
gated by tile class, and the resident animation pass owns the simple frame and
direction updates for environment-like animated classes.

The outdoor per-turn walker is separate from that resident frame animator. It
walks overworld slots from high to low, skips slot zero, and applies only to the
outdoor animated/monster predicate: ship-like water-creature frames plus most
monster-range tiles, excluding the small environment-animation ranges handled by
the resident frame animator. Its first phase handles immediate hostile
reactions. Orthogonal adjacency is tested **before** any class test, so an
adjacent creature engages rather than firing.

The adjacency reactions, in the order the handler tests them:

- **Adjacent whirlpool engagement** is a plane-transition effect when the party
  is not on foot: it announces the whirlpool, runs the swallow presentation,
  applies the Section 6.2.4 payload, moves the party to underworld coordinate
  `(34, 18)`, and re-enters overworld setup for the new plane.

  *Corrected:* an earlier revision said "the same branch is a no-op if reached
  while the party marker is the ordinary on-foot avatar". **That is withdrawn.**
  The on-foot arm reaches the same impact-absorption stage, which under a foot
  marker means every living party member takes damage. It skips the plane
  transition, not the damage. See the forced-movement table in
  `systems/overworld.md` Section 8.
- **Sand Trap family, orthogonally adjacent.** The sprite run `0xE0..0xE3`
  reaches the shared impact-absorption stage directly and **silently** — no
  message of any kind — so an adjacent sand trap applies exactly the payload the
  ranged attacks apply: the whole-party damage pass, or the frigate hull roll
  when the party is aboard a ship. The payload is specified once, in
  `systems/overworld.md` Section 6.2.4.

  *Corrected:* an earlier revision of this document, of `systems/encounters.md`
  and of `systems/movement.md` called `0xE0..0xE3` the "outdoor sea-serpent
  adjacency family". **That is withdrawn and was backwards.** `0xE0..0xE3` is
  the Sand Trap sprite run in every domain, exactly as
  `catalogs/monster-bestiary.md` class 40 already published; the Sea Serpent run
  is `0x88..0x8B`. An implementation that spawned sand traps as sea serpents
  would also silently never fire their breath attack, because the breath test is
  exact equality against `0x88`.
- **Every other adjacent hostile, Sea Serpent included, takes the generic arm.**
  It rebuilds the viewport, prints the "attacked" line, and then reads the tile
  under the party. It reaches the same impact payload **only** when that tile is
  in the low water/void family **and** the party marker is a carpet or a skiff;
  otherwise it enters the encounter/combat entry, which looks the slot's class up
  for its banner name. An orthogonally adjacent sea serpent therefore does *not*
  apply the ranged payload on ordinary terrain.

The ranged reactions, reached only when no adjacency reaction fired:

- **Sea Serpent and Dragon breath.** Entered when the slot's type byte **equals**
  the first frame of the Sea Serpent run (`0x88`) or of the Dragon run (`0xDC`) —
  exact equality on the unmasked byte, not a range and not a masked family, so
  frames `0x89..0x8B` and `0xDD..0xDF` never enter it. Within three cells of the
  player on **both** axes, inclusive, a one-in-eight roll triggers the shot.
  Trace, sampling and payload are all specified in `systems/overworld.md`
  Section 6.2; that section is normative and this one does not restate it.
  *Corrected:* the earlier wording "the same per-turn finishers as other outdoor
  encounter effects run and damage is applied" is **withdrawn** as too vague to
  implement; the payload is now published in full at the reference above.
- **Ship-like water-creature and pirate frames** aligned with the player on the
  same row or column within three cells fire a broadside: they print the boom
  message and then run the same trace and the same payload as the breath attack,
  per `systems/overworld.md` Section 6.2. Unlike the breath test, this
  recognition **is** a masked family test on `0x2C..0x2F`; do not generalise
  either form to the other. The generic "attacked" message belongs to the
  adjacent-engagement path, not to this one.

If no immediate reaction has fired **so far this turn**, the movement-dispatch
phase decides ordinary movement for the slot. Whirlpool-class slots flip a
stored parity bit and move only on the turns where it clears, choosing between a
random cardinal step and the directed step planner. Ship-like water-creature and
pirate frames first pass through the wind cadence table owned by `weather.md`;
once that cadence permits movement, they use the same directed step planner as
land monsters.

> *Corrected (2026-08-23).* Two things this section said are withdrawn.
>
> First, the phase was called a **cleanup** phase that runs **per slot** when
> that slot's own reaction pass declined it. It is neither. A complete re-read
> of the routine and of both movement helpers it calls shows it performs no
> drawing, no frame advance and no cleanup at all: given a slot, it decides
> whether that object takes a step and dispatches it. And the gate is not
> per-slot. The walker keeps a **running total** of the reaction pass's results,
> zeroed once before the slot loop and never reset, and consults that total.
> Once any earlier slot in the same turn produced a reaction, the movement
> dispatch is skipped for **every remaining slot for the rest of that turn**. An
> implementation that re-evaluates the gate per slot will move objects the
> original leaves standing. The walk runs from the highest slot index down to
> one; slot zero is excluded.
>
> Second, the whirlpool "two-frame swirl" was an animation reading. The bit
> being toggled gates **movement**, and the byte holding it is persisted state,
> not a render frame.
>
> Two limits on the re-read, recorded so this is not over-read: the helpers that
> validate a candidate cell and commit the step were **not** examined, so "the
> step is committed" is inferred from the callers' structure; and one branch's
> two exits were found to reach the same movement call with a dead argument, so
> no behavioural difference should be modelled between them beyond the counter
> byte one of them increments.

A special `0xFC` sprite class has an additional proximity-mask branch. That
sprite value is the Shadow Lord actor class (`catalogs/monster-bestiary.md`,
class 47), not an avatar marker, and the ordinary per-turn walk skips slot zero
in any case, so the branch never applies to the player. The branch first
computes wrapped
absolute distance to the player and consults a fixed mask:

| Wrapped `dy` | Wrapped `dx` values that enter the special branch |
|---:|---|
| 0 | 2, 3, 4 |
| 1 | 3, 4 |
| 2 | 2, 3 |
| 3 | 0, 1, 2, 3 |
| 4 | 0, 1 |
| 5 | none |

Cells outside the six-by-six half-window, and cells not listed above, fall
through to ordinary directed movement. Listed cells increment the slot's first
auxiliary byte as an age counter; while that counter remains below twenty, the
slot requests a directed step toward the player through the same step planner.

The directed step planner is deliberately small, and it is smaller than it looks.
It reduces each axis offset from the player to a **sign** -- move one cell toward
the player, or do not move on that axis -- and never forms or compares the two
distances. There is no preference for the longer axis, and there is no special
case for a creature standing exactly diagonal from the party. Having formed the
two candidate steps, it rolls a fair coin to decide which axis to attempt first;
if that candidate is blocked it tries the other. A candidate must pass the
outdoor tile-walkability check and the target-cell check before the step
committer is called. If neither directed axis can be accepted, the slot falls
back to the random four-direction walker, which rolls one cardinal direction and
makes a single attempt at it -- so a blocked creature shuffles rather than
freezing, and can back itself out of a dead end.

On an exact diagonal, therefore, the creature moves horizontally half the time
and vertically half the time, re-rolled fresh every turn, exactly as it does in
every other geometry. There is no tie-break rule to reproduce because there is
no tie to break.

The outdoor tile-walkability check reads the candidate world tile, passes that
tile plus the moving slot's type byte through the shared tile-class dispatcher,
and then runs the reverse active-object lookup on the candidate coordinate and
current world layer. Any occupant found by that lookup blocks the active-object
step. The target-cell check adds one more per-pass guard: after any outdoor
active object commits a step, the engine records the cell it just vacated; the
next directed step in the same pass cannot target that recorded cell. This
prevents a later slot in the high-to-low walk from immediately following into
the most recently vacated coordinate.

The step committer can still refuse a validated candidate through
destination-tile chance gates. For ordinary outdoor movers:

| Destination tile ids | Post-validation movement gate |
|---|---|
| `0x04`, `0x06..0x08`, `0x1E..0x1F` | Move only on a one-in-two roll. |
| `0x09..0x0F` | Move only on a one-in-three roll. |
| `0x05`, `0x10..0x1D`, and ids outside `0x04..0x1F` | Move immediately once validation accepts the candidate. |

These gates are movement cadence rules layered after terrain/occupancy
acceptance; they are not the primary passability predicate. A refused chance
gate ends that slot's movement attempt rather than falling back to another axis.

Ship-like water-creature frames `0x2C..0x2F` bypass these low-terrain chance
gates. Four monster first-frame values also bypass them exactly: Bat `0x94`,
Daemon `0xD8`, Dragon `0xDC`, and Mongbat `0xF0`. Sibling animation frames in
those monster classes are not part of this bypass test.

The `0xDC` comparison above is made against the moving active-object's type
byte, where it is the first Dragon frame. This is a different storage domain
from a live terrain byte with the same numeric value. Movement and visibility
queries may treat terrain byte `0xDC` as a moon-gate / local-light source, but
the active-object step planner must not rename every `0xDC` byte globally.

When the move commits, the old coordinate is stored for the per-pass guard, the
new coordinate is written into the active-object slot, and world redraw state is
dirtied. Ship-like water-creature movers also rewrite their type/frame byte to
the facing frame implied by the cardinal delta before the coordinate update. If
a committed step lands on destination tile id `0xDC`, the moving slot is
cleared. That destination test is against the live terrain byte, not the moving
slot's type byte; in the public terrain catalog this value belongs to the
moon-gate / local-light family. The rule does not specify the natural-gate
placement schedule or live entry hook, which are owned by the overworld
contract.

This is not the town NPC pathfinder. Outdoor monsters have no schedules,
waypoints, flood-fill queue, or AI byte. Their chasing behavior is the result
of repeated one-cell cardinal attempts toward the player plus the random wander
fallback when blocked.

The animator does not move the player. Player movement is owned by the input system and per-mode command handlers. Slot zero is refreshed from world-state globals by the renderer/compositor path before objects are stamped into the viewport, not by the animator itself.

### 8.1 Off-screen pruning on the overworld

Pruning is specified here, in the document that owns the table, because it
changes table occupancy. It was previously mentioned only in passing in
`systems/animation.md` and `systems/encounters.md`, neither of which is
normative for this table and neither of which named a trigger. An
implementation that reads only those mentions can build the predicate and never
invoke it, leaving occupancy to diverge from the original over play.

**Trigger.** The overworld per-turn epilogue runs two passes over the table: the
animate pass described above, and then a **separate prune pass**. Pruning is not
animation, is not on the render tick, and is not driven by the animator. It runs
once per overworld turn. Town, dungeon and combat loops do not run it.

**What the prune pass tests.** For each slot it considers, the pass compares the
slot's stored X and Y against the current **scroll base** - the top-left corner
of the loaded window - and keeps the slot only when **both** differences land
inside the loaded window. Failing either axis releases the slot.

Precisely: each difference must be in the range **0 to 31 inclusive** - thirty-two
positions, matching the 32-by-32 chunk-aligned window anchored at the scroll base
(`systems/overworld.md` Section 4). An implementation that admits a difference of
thirty-two keeps a row and a column of objects the original releases.

Four properties are contract, and three of them are places an implementation
predictably goes wrong:

- **It is a square window, not a radius.** The two axes are tested separately
  and independently against the same bound. There is no distance computation,
  no hypotenuse and no disc. Naming this quantity a *radius* invites an
  implementation to compute a Euclidean or squared distance, which prunes the
  corners of the window that the original keeps.
- **The comparison is window-relative and wraps.** The difference is formed in
  **unsigned eight-bit arithmetic** against the scroll base, so it wraps
  naturally with the 256-cell coordinate space rather than needing a special
  case at the map seam. An implementation using signed or wider arithmetic will
  mis-handle objects across the wrap.
- **Slot zero is never pruned.** The pass walks the slots above zero only. The
  player slot cannot be released by this path however far the scroll base moves,
  and an implementation that includes slot zero in the sweep can delete the
  player.
- **Only classified slots are considered.** A slot whose type byte does not
  classify as a prunable kind is skipped before the position test runs, so an
  out-of-window slot of an unclassified kind survives.

The classification is an exact byte-range predicate:

| Type byte | Prunable? |
|---|---:|
| `0x00..0x2B` | No |
| `0x2C..0x2F` | Yes |
| `0x30..0x7F` | No |
| `0x80..0xB3` | Yes |
| `0xB4..0xB7` | No |
| `0xB8..0xE7` | Yes |
| `0xE8..0xEB` | No |
| `0xEC..0xFF` | Yes |

Only byte 0, `type`, selects a row. The mutable byte-1 `tile` value does not
participate, even if it no longer mirrors `type`; neither do coordinates,
floor, phase, or auxiliary state. After classification succeeds, and only
then, X and Y participate in the window test. An implementation must therefore
not combine `type` and `tile`, fall back from one to the other, or infer the
answer from a broad semantic label such as vehicle, item, or effect.

Consequences for the special cases are explicit:

- There is no player phantom to classify. The player is slot zero, and the
  slot-number exclusion keeps it out of the pass regardless of its current
  type byte.
- Parked vehicle objects (`0x10..0x11`, `0x1B`, and `0x24..0x2B`) are not
  prunable. The adjacent water-creature/pirate family `0x2C..0x2F` is prunable,
  so a blanket "vehicle-like" exclusion is too broad. Boarded transport is
  represented by the player state and is already protected by slot zero.
- Pickups and midrange objects in `0x30..0x7F` are not prunable.
- `0xB5` is not prunable because the whole `0xB4..0xB7` range is excluded.
  This is separate from Section 4's allocator rule, which protects exact
  `0xB5` from eviction.
- Projectile flight visuals ordinarily have no active-object slot, so this
  pass has nothing to classify for them. Combat field markers are likewise
  outside this pass because it does not run in combat. There is no additional
  field/projectile semantic exception: for any record that does reach this
  overworld pass, the byte-range table above is the complete classifier.

**How a pruned slot is released.** *Corrected:* an earlier revision of this
section said pruning frees a slot through the ordinary one-byte rule of
Section 4. **That is withdrawn.** The prune path instead calls the shared
record-writer with the slot index and **six zero field values**, so it clears
the record's first six bytes rather than only its type byte. The freed slot is
immediately available to allocation either way, and Section 4's one-byte rule
remains correct for the other paths that free slots - but an implementation
that models pruning as a single-byte clear leaves five stale bytes behind in a
record that allocation will later hand out.

**Consumers, in both directions.** The prune pass is invoked by the overworld
per-turn epilogue, and by nothing else. It is **not** invoked by
the animator, **not** by the renderer, **not** by mode entry, and **not** by the
combat backup/restore path of Section 9. Nothing reads a "was pruned" result:
the pass returns no report and the epilogue keeps none, so an implementation
must not build a pruning event that other systems observe.

**Relationship to eviction.** Pruning and the eviction cascade of Section 4 are
different mechanisms with different triggers and must not be collapsed.
Eviction is demand-driven - it runs when acquisition needs a slot and the range
is full - and chooses a victim by class priority. Pruning is time-driven, runs
every overworld turn regardless of pressure, and chooses by position alone. A
single shared distance constant serving both is a sign the two have been
conflated.

## 9. Combat backup and restore

Combat suspends the world by swapping the active-object table to a backup region and overwriting the live table with combat actors. The mechanism is a pair of byte-for-byte copies.

**Enter combat.** The framer copies the entire two hundred fifty-six bytes of the live table into a fixed backup region. It runs one of three setup paths — terrain, ambush, or the rest/camp alternate (`systems/combat.md` Section 4; "scripted" was an older name for the third one, which is the H-Hole-up rest/camp helper) — that populate the live table with combatants. Only after this swap does the framer call into the round loop, and the rest/camp path can decline combat so that the round loop is never entered at all.

**Exit combat.** On round-loop return (victory, defeat, or escape), the framer restores by copying the backup region back over the live table. Every byte returns to its pre-combat value: world NPCs to their pre-combat coordinates, vehicles to where they were docked, projectiles to their last position. The world resumes exactly where it left off.

The backup region is dedicated to this purpose, not preserved across saves, a transient buffer used only inside the framer's call. The framer also saves and restores the player's world coordinates (seating writes arena coordinates over the low records, record zero included), the active-player byte, and a scene-byte sentinel that signals "combat is in progress." Record zero is overwritten because it is the first record the party seating allocates, not because combat reserves a player slot; see Section 7. The calling mode loop sees combat as a function call that returns with the table and globals exactly as they were, plus side effects (damage, death, time advance) baked into separate persistent state.

The copy is byte-for-byte; slot indices are stable across the round-trip. An NPC in slot fifteen before combat is in slot fifteen after, with the same tile and coordinates. The NPC scheduler resumes per-tick walking without re-allocation.

Some callers intentionally run a second reconciliation helper after the framer
has restored the backup. The ordinary resident terrain-target wrapper does
this for the original active-object slot that triggered combat: it first
restores the saved world table again, then mutates only the caller-supplied
slot. In the ordinary terrain path, if the slot is not preserved as a
body/retrieval object, bytes 0 through 4 of that slot are cleared, which frees
the trigger from future object scans while leaving caller-owned auxiliary bytes
outside that clear range untouched. If the restored trigger is in the
`0x2C..0x2F` water-creature/body family and combat has set the exit-message
state, the helper instead rewrites the slot into the persistent body/retrieval
state by lowering both sprite bytes by eight and stamping the auxiliary body
state (`dep1 = 0x63`, `dep3 = 0x02`). This is caller-side world reconciliation,
not a merge of temporary combat death markers.

## 10. Mode-entry initialisation

Each mode's entry handler initialises the table according to its needs.

**Town / dwelling / castle / keep entry.** Clears every slot except slot zero. Runs the per-NPC roster load (building runtime descriptors and schedules), the per-NPC initial-waypoint placement (calling the world-mutation helper for each NPC currently on the player's floor, allocating slots), and finally the Shadowlord install, which runs only in a town that currently hosts one of the three Shadowlords and is skipped entirely otherwise (`systems/town-mode.md` Section 13). Result: slot zero has the avatar and a handful of low-indexed slots have on-screen NPCs; in a hideout town one further active-object slot and the highest empty NPC index hold the resident Shadowlord. The entry pass writes no NPC-table entry for the player.

**Overworld entry.** Slot zero is the player. The remainder of the table is populated from the on-disk overworld object overlay (per-map static object lists). Each non-zero record from the overlay is copied into a free slot. Before normal outdoor input begins, entry also consumes the one-shot pending vehicle-acquisition state used by shipwright purchases: if set, it allocates a free slot, writes the pending coordinates, initializes either a ship-family object with hull/skiff auxiliary state or a skiff-family object, and clears the pending state. Those pending coordinates are the fixed delivery cell of the shipwright that sold the vessel, published per row in `systems/shops.md` Section 8.7; they are not the town's entrance or exit cell. Random encounters, dropped items, and spawned creatures appear in the table over the course of overworld play and are pruned when they leave the player's viewport: the overworld per-turn walker checks each slot's distance from the scroll bases and frees slots more than thirty-two cells away.

**Dungeon entry.** Dungeon exploration does not populate the table for its first-person view. The dungeon loop reads the player's dungeon Z/X/Y and facing globals, renders from the loaded dungeon record, and does not run the town NPC scheduler or the overworld active-object walker. The active-object table remains part of global saved state, but it is not the dungeon renderer's actor list. If a dungeon room, trap, ambush, or attack enters combat, the combat framer takes over as described in Section 9.

**Combat entry.** Section 9.

Slot zero is preserved or written by the entry handler before any other slot is touched. No mode runs with slot zero empty.

## 11. Persistence in saves

The active-object table is persisted as part of the save image. The save format reserves a two hundred fifty-six byte region; on save, the engine writes the live table verbatim; on load, it reads the region back into the live table. Persistence is byte-for-byte: empty slots stay empty, filled slots keep their current tile, coordinates, and animation phase.

The NPC scheduler's runtime descriptor table is *not* persisted. On load, descriptors are re-initialised from the schedule and current hour, "re-snapping" each NPC to its scheduled waypoint. The scheduler then re-allocates active-object slots through the world-mutation helper. The asymmetry produces a brief inconsistency at load time — saved table positions versus freshly-rebuilt waypoint positions — that the runtime initialiser resolves by overwriting NPC slots with re-derived waypoint coordinates. Visible effect: loading reverts NPCs to their currently-scheduled location, as already documented in the schedule spec.

The on-disk overworld object overlay (per-map static object list) is a *seed* file, copied into the table on first overworld entry of a new game. The runtime save-overlay is the *current* working copy, written alongside the main save file. The combat backup region is not persisted; saving inside combat is not supported.

## 12. Hooks into other systems

**NPC scheduler.** Reads the table for the player's position (slot zero) and writes it indirectly through the world-mutation helper on every NPC step that crosses the player's floor or moves within it. The scheduler's runtime descriptor holds the linked-slot index that ties one logical NPC to one active-object slot.

**Renderer.** Walks the table from slot thirty-one down, projects each slot's world coordinates into the on-screen viewport, and stamps the slot's tile into the viewport scratch grid (skipping cells already obscured by fog or already containing a higher-priority sprite). Slot zero (the player) draws last. Special tile classes get class-specific compositor branches that consult the auxiliary bytes: the water-bound `0xE8..0xEB` class and exact `0x1E` / `0x1F` type bytes stamp through the companion terrain band and leave the visibility grid with the use-companion marker; water-creature frame bytes `0x1D` and `0x1E` use the same companion-band path; the `0x5C` vehicle/avatar-family branch takes the special vehicle stamp only when the underlying grid cell holds marker `0x92`, otherwise it falls through to the default compositor.

**Visibility compositor.** Active-object slots are projected into the viewport
after the terrain visibility carve has produced the grid. Slots hidden by the
grid's obscured marker are skipped; visible slots stamp their tile bytes or
companion-buffer markers according to vehicle/creature class. The currently
traced carve helper does not directly scan the active-object table.

**The actor tile-index space.** A slot's tile byte is **not** a terrain index,
and reading it straight into `catalogs/tile-catalog.md` produces floor and
furniture instead of people. When the compositor places an actor it writes the
actor byte into the companion band for that cell and sets the corresponding
viewport grid cell to zero. The renderer then branches on the grid cell: a
non-zero cell draws the terrain tile that cell names, and a **zero** cell reads
the companion byte and draws tile index `companion_byte + 256`. Actor bytes
therefore index the upper, actor half of the 512-entry tile space. One value is
reserved: companion byte `0x16` means "draw nothing", and it is the only
transparent value this path recognises — an actor that must occupy a slot
without being drawn carries it. A few tile families are not written through
verbatim: before the companion write, the compositor inspects the terrain under
the actor and substitutes a context-dependent actor byte for actors standing on
chairs, beds, stairs and floor links, so a seated or climbing figure draws a
different sprite than the same actor standing on open floor. The substitution
changes only which actor byte is written; the `+256` rule then applies to the
substituted value exactly as it would to the original. `catalogs/tile-catalog.md` section 3.1 carries the same rule
from the catalogue side, and `systems/endgame.md` section 4 works it through for
the endgame tableau.

**Combat.** The framer swaps the table to a backup, runs combat with combatant
records in place, and restores. Inside combat there is no reserved player
record: the round walker iterates the parallel combat-effect descriptor table,
which holds all round-only state, and reads whichever active-object record each
descriptor's link byte names. Record zero belongs to the first seated party
member, not to the player avatar (Section 7). An earlier revision of this entry
said the round walker reads slot zero for the player and slots one and up for
monsters; that is withdrawn, and it is the same withdrawn "reserved player
slot" claim Section 7 corrects.

**Per-tick animator.** Runs once per world tick (the input system's idle loop), advancing each non-empty slot's animation phase and rolling AI movement decisions for monster classes. It animates only the actor classes held in the table; it drives no water, lava or torch terrain cycle. Animated *terrain* belongs to the separate world-tick tile animator and its five families (`systems/animation.md` Section 6).

**Save / load.** The table is a persistent region in the save image, byte-for-byte.

**Time.** No direct hook. Animation is per-tick, not per-hour; the animator does not consult the time system.

## 13. Active-object boundaries and remaining dynamic users

The core active-object contract is complete for known traced users at
table-lifecycle depth: record shape, slot allocation/freeing, player slot
ownership, NPC linkage, renderer/visibility
compositor ownership, combat backup/restore, field-marker lifetime,
projectile/impact non-ownership, mode-entry initialization, persistence, and
outdoor hostile-slot movement are public.

Remaining dynamic-object work, if a new non-projectile user is found, belongs
to that caller's system contract. It should not change the shared table
lifecycle or reclassify projectile and impact visuals as active-object records.

## 14. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The dungeon loop's first-person rendering path and its absence of NPC/active-object population during exploration — `u5-decomp/functions/DUNGEON_OVL/`.

- The per-tick animator that walks the table to advance animation phases and roll monster AI movement — `u5-decomp/functions/ULTIMA_EXE/`.
- The compositor's companion-band write, the renderer's zero-grid-cell branch,
  the `+256` actor index rule and the reserved transparent value —
  `u5-decomp/notes/presentation_endgame_chargen_u4_2026-08-22.md`.
- The resident active-object acquisition cascade and slot initialiser -
  `u5-decomp/functions/ULTIMA_EXE/`.
- The `0xB5` actor-class interpretation is cross-checked against the shipped
  NPC roster analysis in `u5-decomp/formats/npc-tlk-pth.md`.
- The overworld per-turn slot walker, its exact outdoor type-byte predicate,
  the proof that both animation and pruning classify record byte zero alone,
  hostile reaction dispatch, water-creature step path, per-slot movement
  dispatch, directed step planner, and proximity helper -
  `u5-decomp/functions/MAINOUT_OVL/`, and
  `u5-decomp/functions/MAINOUT_OVL/`.
- Source provenance: the exact-equality breath recognition, the
  adjacency-before-class ordering, the identification of `0xE0..0xE3` as the
  Sand Trap run and of its adjacency arm as silent-but-damaging, the generic
  adjacent arm's terrain-and-marker condition for reaching the shared payload,
  and the withdrawal of the on-foot whirlpool no-op, were **re-derived from the
  shipped binaries** in a verification pass that read each routine from entry to
  exit and did not use any private note as evidence. Sprite-run identity was
  fixed two independent ways: the shipped description strings for the sprite
  pages, and the published `class * 4 + 0x40` actor-byte rule of
  `catalogs/tile-catalog.md` Section 7 applied to
  `catalogs/monster-bestiary.md` class numbers. Working directories:
  `u5-decomp/functions/MAINOUT_OVL/` and `u5-decomp/functions/ULTIMA_EXE/`.
  Private notes in the first of those that name the `0xE0` adjacency arm after
  the sea serpent are contradicted by this pass and should be corrected on the
  private side.
- The resident tile-class dispatcher and reverse active-object lookup used by
  outdoor step validation -
  `u5-decomp/functions/ULTIMA_EXE/`.
- The compositor that walks the table backwards to stamp on-screen sprites into the viewport, plus the fog post-pass — `u5-decomp/functions/ULTIMA_EXE/`.
- The world-mutation helper that links logical NPC state to a slot in the table when an NPC arrives on or leaves the player's floor — `u5-decomp/functions/TOWN_OVL/`.
- The town-entry Shadowlord install that allocates an active-object slot and a parallel high-indexed NPC slot for a resident Shadowlord — `u5-decomp/functions/TOWN_OVL/` (see that note's 2026-08-22 repair-round correction, which supersedes its original "player attach" framing) and `u5-decomp/notes/2026-08-22_quest-world-retrace.md`.
- The NPC pathfinding workspace builder that overlays active-object obstacles
  and the current player cell for collision avoidance -
  `u5-decomp/functions/NPC_OVL/`.
- The combat round loop that operates on the table during combat — `u5-decomp/functions/COMBAT_OVL/`.
- The combat enter/exit framer that backs up and restores the table — `u5-decomp/functions/ULTIMA_EXE/`.
- The resident terrain-target wrapper and SJOG post-combat object reconciler
  that clear or rewrite the original trigger slot after combat --
  `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/functions/SJOG_OVL/`.
- The NPC per-tick walker that drives schedule-based NPC movement and feeds the world-mutation helper — `u5-decomp/functions/NPC_OVL/`.
- The save image's region holding the table and the on-disk overlay files — `u5-decomp/formats/saves.md`.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_npc-walkers.md` -- the confirmation
  that the directed step planner never compares the two axis distances (so
  there is no longer-axis preference and no diagonal tie-break), the coin flip's
  role as attempt ordering only, the single-attempt random wanderer fallback,
  and the identification of the shared five-argument helper as the ranged
  projectile animator rather than a movement probe or path-clear scan.
- The combat/spell projectile visual path and per-cell effect renderer -
  `u5-decomp/functions/COMSUBS_OVL/`.
- The F-Fire and ship-broadside projectile traces -
  `u5-decomp/functions/CMDS_OVL/`.
- Vehicle byte interpretation for ship boarding, X-it parking, and broadside
  damage -- `u5-decomp/functions/CMDS_OVL/`, and
  `u5-decomp/functions/CMDS_OVL/`.
