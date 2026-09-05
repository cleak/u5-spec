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

The top-down world modes and combat read and write this same table. The shared visibility post-pass composites it into the top-down viewport buffers and the renderer then paints those buffers; the renderer itself is a read-only consumer and composites nothing (`systems/visibility.md` Sections 9 and 11). The visibility pipeline uses the table during compositing to decide which active sprites survive the current visibility grid. The NPC scheduler links into it when its NPCs cross onto the player's floor. Dungeon exploration is the main exception: its first-person view is rendered from dungeon coordinate globals and the loaded dungeon grid rather than by the top-down active-object compositor, although its one wandering monster reuses an eight-byte record in the resident table with dungeon-specific field meanings. When a dungeon room or ambush enters combat, the normal combat framer swaps the table for an isolated combat instance and swaps it back when the fight ends. The save image preserves the table byte-for-byte.

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
|   6  | `phase`      | Packed animation byte: frame-delay countdown (low nibble) and animation-script step (high nibble). Carries **no facing**. Advanced by the animator. |
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

**The phase byte.** Byte 6 packs two pieces of state into one byte: the low nibble is a frame-delay countdown (with the all-ones value meaning "rest at steady frame, do not animate"), and the high nibble is the slot's step within its animation script. The animator's per-tick rule, in the order the gates are actually applied:

1. All-ones low nibble — bail immediately, **writing nothing**. This is the freeze sentinel.
2. Low nibble in `1..14` — decrement it and write the recombined byte back. **This write is unconditional and has no tile-class precondition**, and it applies to every slot the walk reaches, slot zero included.
3. Low nibble zero — fall through to the eligibility gates (a frame-byte test, then a tile-class threshold), which may advance the script step and rewrite the byte.

**The scripts themselves (established 2026-09-05).** Each animated class owns a
short script of up to sixteen bytes, selected through a per-class script id, and
the high nibble of byte 6 is the current position in it. On an eligible tick
the animator reads the byte at that position and acts on it: values one to four
select that frame of the class's four-frame run and advance the position; zero
restarts the script; a value of five snaps the sprite back to its base frame on
a one-in-four draw (holding the position and, for every class but one, pausing
six ticks) and otherwise just advances; six restarts the script three times in
four and otherwise advances; seven jumps to position two; and any value of
eight or more sets the frame-delay nibble to that value less eight and
advances. Before the script runs, the eligibility gates require a non-zero
frame byte that is not the reserved transparent value, a tile class at or above
the animator's threshold, a class that is neither the field family nor the
regalia band, and - for every class except the two that animate unconditionally
- a one-in-two draw from the shared generator. The **whirlpool marker** uses
the same script as the party-sprite family: it steps through frames two, three
and four on successive eligible ticks and then, at the fifth position, either
snaps to frame one with a six-tick pause (one in four) or restarts the two-
three-four cycle. Source provenance: private analysis in
`u5-decomp/functions/ULTIMA_EXE/` and `u5-decomp/notes/`.

The tile-class gate is therefore *downstream* of the decrement, not upstream of it: a low nibble in `1..14` is decremented on any slot regardless of what class the record holds. An earlier reading of this section had the two gates the other way round and concluded that the player's tile class protects slot zero's byte 6 from the animator. It does not — what protects it in a shipped save is the stored **value** zero, which routes past the decrement into a class gate the player's class fails.

*Corrected (issue #184).* This paragraph previously said the high nibble "holds a direction-step counter that AI movement uses". That reading is withdrawn: the high nibble is an animation-script step, byte 6 carries no facing anywhere, and a producer that writes a facing into it is not byte-compatible. In particular the freeze sentinel is **not** the player's stored value: the shipped player record carries zero in byte 6. See `RETRACTIONS.md` row R340.

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

The phases 2-5 off-screen test is an exact eleven-by-eleven square centred on
the current player-coordinate globals. For each axis, compute the byte-wide
unsigned value

```text
adjusted = (candidate_axis - player_axis + 5) modulo 256
```

The candidate is on-screen only when both adjusted axes are at most `10`.
Equivalently, its symmetric wrapped separation from the player must lie in the
inclusive range `-5..+5` on both axes. A separation of five remains on-screen;
six on either axis is off-screen and makes the slot eligible for phases 2-5.
The subtraction and addition both wrap as unsigned eight-bit arithmetic, so the
same rule applies across the 0/255 world seam.

This predicate reads the player X/Y state directly, not slot-zero coordinates
and not the viewport or scroll origin. It reads candidate record bytes 2 and 3
only; the candidate's floor/level byte does not participate. Matching X/Y on a
different floor is consequently still classified as on-screen for allocation
eviction. This is deliberately separate from the 32-cell scroll-base prune
predicate in Section 8.1.

For player `(2,2)`, the exact boundary cases are:

| Candidate | Wrapped separation | Classification |
|---|---|---|
| `(253,2)` | `(-5,0)` | on-screen |
| `(252,2)` | `(-6,0)` | off-screen |
| `(7,7)` | `(+5,+5)` | on-screen |
| `(8,7)` | `(+6,+5)` | off-screen |
| `(2,2)` on another floor | `(0,0)` | on-screen; floor is ignored |

The omitted ranges `0x12..0x1F` and `0x20..0x2F` protect NPC/person-like
entries and vehicle-like entries from the priority phases. The last-resort
phase can still take any byte except `0xB5`, so `0xB5` is the only universally
protected byte-0 value in this allocator.
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

The player occupies slot zero. Every world frame, the compositor refreshes bytes 0..4 of slot zero from the world-state globals (the transport/action marker into **both** byte 0 and byte 1, then the party X, Y and Z). The renderer then walks the table from slot thirty-one down so slot zero paints on top.

**Bytes 5, 6 and 7 of slot zero are not part of that rebuild.** The per-frame refresh writes bytes 0 through 4 and stops. Within a scene, while the stored byte 6 is either zero or the freeze sentinel, and while the party is on foot, those three bytes round-trip from the save image untouched — that is why the player's record in a shipped town save reads as the marker twice, the coordinates, and then three zero auxiliary bytes. The qualifiers are load-bearing, and this negative is a trace of the routines that own slot zero rather than a census, because dozens of pointer walks index the table:

- A stored low nibble in `1..14` in byte 6 **is** decremented in place by the animator, on slot zero as on any other (Section 3).
- The NPC purge path zeroes bytes 0..4, 6 and 7 of whichever record an NPC's linked-slot field names, and that is slot zero when the field is zero. In the shipped data the predicate guarding it does not fire, but it is not structurally impossible.
- Every return to the overworld replaces all eight bytes of all thirty-two slots from the per-plane object list (Section 11).
- The trace covers the party **on foot**. A transport/action marker that raises slot zero's tile class to or above the animator's class threshold — the whirlpool marker is the traced case — lets the walk reach its *second* byte-6 write even from a zero low nibble. That path is traced as reachable and its script has now been read (Section 8, "The scripts themselves"): the marker cycles its second, third and fourth frames with an occasional snap back to the first.

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

Placed combat fields also live in this temporary active-object table. Their
marker records use arena coordinates. After either per-actor dispatch branch
returns, the combat walker gives its current descriptor slot to the contact
hook. That descriptor remains the effect target. If no terrain hazard has
priority, the hook scans active-object records in ascending order, skips the
target descriptor's own linked renderer record, and selects the first separate
recognized marker at the target's coordinate. Thus the skip prevents an actor
sprite from masquerading as a field marker; it does not immunize the current
actor. Poison, Sleep, and Fire markers are passable and can affect the mover,
while Energy is blocking and has no result arm in this hook. The same contract
follows player and AI dispatch and is not restricted to actions that changed
coordinates. Contact is non-consuming: it applies the result without clearing,
aging, or rewriting the marker record. Field markers are active-object-only
records rather than paired combat-effect descriptors, so the monster
death/record-clear path cannot age or remove them. The accepted-placement
resident redraw helper and the generic active-object tick do not allocate,
remove, or decrement field marker records. Their presence is combat-local: they
persist until the framer restores the pre-combat active-object table on exit.

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
| any non-zero  | Mid-cycle. Decrement and write back — **and nothing else for that slot on that pass**, so its frame byte is not touched (see the early-out list below). The renderer combines the phase with the tile class to pick a frame. |
| zero          | Cycle ended. Eligible for a direction/frame decision: roll RNG, possibly change the stored facing, possibly reseed phase. It never changes the slot's coordinates. |

Each animated class has its current-frame index in a separate animation-frame table; the renderer combines the tile class with that counter to pick the actual byte to paint. The classes this per-slot pass animates are actor classes — vehicles, monsters and the other sprite-only tiles that live in the table. (An earlier revision of this paragraph listed "water (a four-frame cycle), lava, torches, and a small handful of 'special' tiles" as the animated classes. That list is **withdrawn**: no water, lava, brazier or torch tile animates through any per-tick pass. The separate world-tick tile animator touches exactly five terrain families — waterfall, fountain, pendulum, the standard of Britannia, and the clock/bellows pair — and none of them is a water or fire terrain family. **Further correction:** that withdrawal was then over-generalised in this document and elsewhere into "water, lava and fire tiles do not animate". That is also withdrawn. They have no frame family and no selector, but they are animated by a third layer — a driver-side pass that rewrites the loaded tile artwork in place on every animation step — specified in `systems/animation.md` Section 12. See `systems/animation.md` Sections 6 and 12 and `catalogs/tile-catalog.md` Section 4.)

Two responsibilities sit slightly outside the per-slot loop. A *frame-counter advance* runs at the end of the pass, incrementing a shared frame counter and toggling a few alternate-frame tile classes. A *video-driver flush* runs immediately after, sending the post-tick frame to the display driver. Both are part of the "advance one tick of on-screen state and present it" contract.

Some slots also receive a direction decision during the same pass: a slot whose
phase reaches zero gets an RNG roll that can rewrite its stored facing and its
displayed frame. The roll is gated by tile class, and the resident animation
pass owns these simple frame and direction updates for every animated class.
**It cannot move anything.** The animator's complete set of record writes is the
displayed-tile byte and the packed phase/facing byte; it never writes a slot's
column or row.

> *Corrected (R316).* This paragraph previously said the phase-zero roll "may
> turn or step them one cell" for "hostile creature classes that wander on the
> overworld (or in towns past their schedule)". The stepping half is withdrawn,
> and so is the town clause. The animator changes appearance only; ambient
> creature movement happens in the outdoor per-turn walker below, and a town's
> non-schedule roamers are walked by a separate town-mode walker. This completes
> the propagation of R315, which withdrew the same reading from
> `systems/main-loop.md`, `systems/animation.md` and `systems/input.md` but left
> these sentences standing here. Search scope for the negative: the animator was
> read end to end, and every function reachable from the world tick to a depth
> of six calls — fifty-six routines — was swept for writes into the
> active-object table. The only such write anywhere in that tree is the
> renderer's mirror of the **party's own** coordinates into slot zero. The sweep
> did not follow indirect or far calls, and outside the animator and the
> renderer it did not chase writes made through a pointer held in a register.

**The animator's two written bytes, and who else can see them.** The animator
writes exactly two of a record's eight bytes — the **displayed-frame byte** and
the **packed facing/phase byte** — and never any other, in any class, on any
path. Issue #189 asked what a turn-based frontend must reproduce beyond drawing.
The answer is in the three subsections below.

**Per-pass early-outs, in the order the animator applies them.** A slot that
fails any of these is abandoned for that pass, and the phase rule in the middle
is not the "decrement every live slot" rule an earlier reading of this section
implied:

1. An empty slot (type byte zero) is skipped.
2. A slot whose **phase nibble is the all-ones steady marker** is skipped
   entirely, writing nothing at all. Only gameplay can release it.
3. A slot whose **phase nibble is any other non-zero value** has that nibble
   decremented and written back, and then the animator **goes straight to the
   next slot** — such a slot never reaches the frame decision on that pass. Only
   a slot whose phase nibble is already zero falls through to the rest.
4. A slot whose displayed-frame byte is the hidden value, or either of the two
   prone/sleeping values, is skipped. This is how gameplay parks an actor.
5. A slot whose class lies **below the sprite-class floor**, or in either of two
   excluded classes, is skipped. Everything the animator can write to the frame
   byte therefore lies at or above that floor — which is exactly why the
   water-creature facing movers, which act only on frame values below it, can
   never see an animator-written value.
6. Otherwise, unless the class is one of two exempt classes, the animator draws
   one random value and skips the slot on the low half of the range.

**Random-stream accounting.** This is the animator's main coupling into
gameplay, because the generator it draws from is the one shared by the wander
coin, the NPC replan gate, the encounter roll and every combat roll. Per pass it
consumes:

- **one advance for every slot that survives early-outs 1–5 and whose class is
  neither of the two exempt classes** — spent whether or not the slot then goes on
  to animate, because the draw is taken before the skip decision it feeds;
- **no advance at all for the two exempt classes**, which enter the frame
  decision without drawing (both are live classes in the shipped class table, so
  the exemption is not vacuous);
- **plus one advance for each execution of the two random script steps** — the
  reseed step and the redirect step. A single slot can execute several script
  steps in one pass, because some steps loop rather than ending the slot.

An engine that models this as "one draw per animated slot" is wrong in both
directions at once. Note also that no cadence choice reconciles this with the
original, which fires the animator from a wall-clock idle pump: **full-session
roll-sequence parity is unachievable**, and an engine should not distort its
animation cadence chasing it (`systems/npc-schedules.md` Section 12).

**Who reads the two bytes.**

- The **frame byte** is read by two drawing consumers — the shared visibility
  post-pass compositor and the full-map builder — and by a handful of gameplay
  sites. All but one of those gameplay sites are excluded, but by three different
  arguments: most by the early-outs above, one by a compositor re-stamp of the
  party's own slot that runs after the animator on every pass (an ordering
  argument, *probable*), and one that only saves and restores the byte around a
  highlight rather than reading it for meaning. The exception is real: **one
  sprite class's animation script drives the frame byte to exactly the value a
  gameplay filter tests for**, and a slot of that class placed on one set of
  starting facings converges on that value while a slot placed on the others
  cycles through three neighbouring values and never matches. So whether the
  animator has run on such a slot is observable in gameplay, not only on screen.
  Publish this reader census as **probable**, on the same scope statement as the
  facing/phase byte below: an earlier pass of it missed three readers and
  answered one row backwards.
- The **facing/phase byte** has no gameplay reader that consumes an
  animator-written value. Gameplay writes it freely — as a one-way control
  channel into presentation, setting the steady marker to freeze a slot, zero to
  release it, or a facing with a zero phase — but the only routine that reads it
  back outside the animator does so inside a scene that has saved the affected
  records to its own frame first and restored them on exit, so it is reading its
  own scratch.

  *Scope of that negative, stated exactly.* It rests on a corpus-wide census over
  the shipped executable, all overlays and all display drivers, covering direct,
  indexed, and hand-checked pointer-derived references to the byte. It does
  **not** cover writes or reads made through a pointer loaded from memory, block
  fills, computed displacements, or accesses a display driver makes through its
  own interface. That hole is not theoretical: an earlier, narrower census of the
  same byte missed seven real accesses inside it, all of them writes. Publish and
  implement this as **probable**, not established. Whether the animator runs
  during dungeon or combat play at all is separately unresolved; Section 13 below
  records what is and is not established there.

The outdoor per-turn walker is separate from that resident frame animator. It
walks overworld slots from high to low, skips slot zero, and applies only to the
outdoor animated/monster predicate: ship-like water-creature frames plus most
monster-range tiles, excluding the small environment-animation ranges handled by
the resident frame animator. Its first phase handles immediate hostile
reactions. Orthogonal adjacency is tested **before** any class test, so an
adjacent creature engages rather than firing.

**There is no outdoor equivalent of the town wander gate.** An ordinary land
monster has no per-turn "do I move at all" roll: every turn the walker runs, an
eligible slot goes straight to the directed step planner. The per-turn
randomness an implementation has to reproduce outdoors is only these, and they
are all downstream of the decision to move:

- the fair coin that picks **which axis to attempt first** — an ordering roll,
  never a gate;
- the destination-terrain cadence gates in the step committer (one-in-two and
  one-in-three, tabulated later in this section), which can refuse an already
  validated candidate;
- the class-specific pacing of the whirlpool parity bit and the wind cadence for
  ship-like frames.

The planner reduces each axis offset to a sign and never compares the two
magnitudes, so a creature on the far edge of the window closes at the same
nominal rate as one two cells away — there is no distance band and no
"activation radius". *Scope of that negative:* the directed planner, the random
fallback walker and the reaction pass were each read end to end, and the only
distance-shaped tests in them are the ones this section already publishes (the
orthogonal adjacency test, the breath/broadside proximity tests, the Shadow Lord
proximity mask, and the off-screen prune). The three class special cases named
in the third bullet were not re-derived, so a distance test inside one of those
is not excluded.

The adjacency reaction is likewise ungated: it is evaluated before any class
test and behind no roll. That is why an adjacent hostile engages on the *first*
turn the player passes, rather than after a variable delay — and why it does not
move on that turn, since a returning reaction both consumes the slot's turn and
zeroes out movement for every remaining slot in that pass.

**Towns do not use this walker.** A town's non-schedule roaming objects are
advanced by a separate town-mode object walker that runs once per turn,
immediately before the NPC schedule processor and under the same three effect
gates (`systems/npc-schedules.md` Section 5). It considers only slots whose type
byte is in the loose-horse family `0x10..0x11` and whose floor byte matches the
displayed floor, and it applies its own independent one-in-two per-slot coin
before probing directions, drawn from the same shared random stream. On a
committed step it also rewrites the slot's type/frame byte to the facing value
implied by the direction, exactly as the outdoor water-creature movers do. Town roamers, town schedule NPCs and outdoor
creatures are three separate movement systems that happen to share this table.
*Scope:* established by a call census over the town overlay covering direct near
calls only; indirect and far call forms were not enumerated, and no claim is
made here about whether the overworld module is resident during town mode.

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

  The two gates in that sentence are exact. The terrain set is
  `0x00..0x03` inclusive: the sentinel/void value, deep water, water, and
  shoals. It includes `0x03`, so it is **not** the ship movement predicate
  `0x00..0x02` from `systems/movement.md`. The accepted transport markers are
  exactly carpet `0x14..0x15` and skiff `0x28..0x2B`. No foot, horse, frigate,
  sprite-suppressed (`0x00`), or other marker qualifies. Both gates must pass;
  if either fails, the branch enters terrain combat.

  Terrain combat derives the encounter's base combat class and banner from
  the triggering slot's byte-0 type. The low two frame bits do not affect the
  result:

  | Active-object type | Base combat class / banner identity |
  |---|---|
  | `0x2C..0x2F` | Class 1 for stats, but the banner is not a table entry: any type whose masked byte is below `0x40` bypasses the group-name table and prints the fixed literal `PIRATES` (`systems/encounters.md` Section 4, `RETRACTIONS.md` R350). The ship family is the only sub-`0x40` family known to reach it, and that is established only on the Attack path. |
  | `0x80..0x8F` | Classes 16..19, one class per four-byte run. |
  | `0x90..0x9F` | Classes 20..23, one class per four-byte run. |
  | `0xA0..0xAF` | Classes 24..27, one class per four-byte run. |
  | `0xB0..0xBF` | Classes 28..31, one class per four-byte run. The excluded `0xB4..0xB7` subfamily does not reach this fallback through the ordinary walker. |
  | `0xC0..0xCF` | Classes 32..35, one class per four-byte run. |
  | `0xD0..0xDF` | Classes 36..39, one class per four-byte run. |
  | `0xE0..0xEF` | Classes 40..43, one class per four-byte run. The Sand Trap, excluded `0xE8..0xEB`, and whirlpool subfamilies do not reach this generic fallback through the ordinary walker. |
  | `0xF0..0xFF` | Classes 44..47, one class per four-byte run. |

  Every value in that table is an active-object **type/sprite byte**, never a
  map-cell terrain id. The atlas entry it draws is `type + 0x100`
  (`catalogs/tile-catalog.md` Section 3.1), so the `0xC0..0xCF` and
  `0xD0..0xDF` rows above are the Orc-through-Wisp creatures at atlas
  `0x1C0..0x1DF` — not the identically numbered terrain ids, which are the
  display driver's flame and wedge stencils (`systems/animation.md`
  Section 12).

  Equivalently, every ordinary type at or above `0x40` uses
  `(type - 0x40) / 4`, discarding the remainder. This is a complete mapping,
  not a gate limited to `0x40..0x7F`: the whole `0x80..0xFF` actor band maps
  to bestiary classes 16..47. See `catalogs/monster-bestiary.md` Section 2 for
  class names and Section 2.2 for the group banner names; the two tables are
  independent, and an entry that looks blank in one is not a cue to fall back on
  the other.

  The combat class is **not** the outdoor arena number. The battlefield is
  selected independently by the terrain under the hostile and party ship
  state, using the complete priority and terrain tables in
  `systems/encounters.md` Section 4. Type contributes only three special
  inputs to that selector: `0x2C..0x2F` marks a ship target,
  `0x80..0x8F` forces the water condition, and `0xFC..0xFF` forces Shadow Lord
  arena 10. All other type families leave arena selection to terrain and
  transport. A generic engagement implementation must call that complete
  terrain-combat entry; a partial type-to-arena switch is not equivalent.

**Multiple adjacent hostiles do not compete for one winning slot.** The outer
walker visits eligible slots from thirty-one down through one and runs the
adjacency test separately for each. After a returning reaction it continues
with the next lower slot; there is no direction-order scan, class priority, or
break after the first match. A generic terrain-combat call can therefore return
and be followed by another lower-indexed adjacent reaction in the same
epilogue. The first reaction makes the walker's running reaction total
non-zero, which suppresses ordinary movement dispatch for the rest of that
turn, but it does **not** suppress later reaction checks. A special branch that
changes scene or re-enters overworld setup can of course transfer control away
before the original walk resumes.

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

**Town / dwelling / castle / keep entry.** This entry takes an **entry-mode argument**, and the argument decides whether the NPC layer is rebuilt at all. Getting it wrong is the difference between a live town and an empty one.

*Mode one — a fresh entry.* Clears every slot except slot zero (writing zero to the type byte of slots one through thirty-one). Runs the per-NPC roster load (reading the location's NPC sub-map into the resident schedule, type and dialogue tables), the per-NPC runtime-state initialisation from the current hour, the per-NPC initial-waypoint placement (calling the world-mutation helper for each NPC whose waypoint floor equals the player's floor, allocating slots), and finally the Shadowlord install, which runs only in a town that currently hosts one of the three Shadowlords and is skipped entirely otherwise (`systems/town-mode.md` Section 13). Result: slot zero has the avatar and a handful of low-indexed slots have on-screen NPCs; in a hideout town one further active-object slot and the highest empty NPC index hold the resident Shadowlord. The entry pass writes no NPC-table entry for the player.

*Mode zero — a preserving entry.* **The entire NPC layer above is skipped**: the slot one-through-thirty-one clear, the roster load, the runtime-state initialisation and the waypoint reseat all do not run. What still runs is everything that is not the cast — the floor tile load, the dawn/dusk substitution, the marker and light-beacon harvest, the moon-phase strip refresh, the wind-banner reprint, the resident-Shadowlord latch reset **and the Shadowlord install pass itself, which sits outside the entry-mode guard and therefore runs in both modes** (`systems/town-mode.md` Section 5 step 6), the mode-zero clock call, and the final redraw. The live cast is whatever the resident image already holds.

*Which mode a caller passes.* Mode one is passed when this dispatch iteration reached the town through the overworld handler or through the dungeon-wrapper return, and by the resident warp helper that moves the party from one town-family scene to another. **Mode zero is passed on the first dispatch iteration after a load** — Journey Onward straight into a town-family scene — and by an already-in-town re-dispatch.

**Mode zero is correct, not a shortcut.** The whole NPC runtime family — schedule table, per-NPC runtime state, path queues and their read pointers, type array, stuck counters — lives *inside the save image* alongside this table (`formats/saved-gam.md` Section 12). A save taken inside a town therefore already carries its complete live cast, and re-running the loader would throw away every NPC's mid-route position, queued path and pursuit target and snap them all back to their scheduled waypoint. An implementation that persists only the active-object table and rebuilds the NPC layer on load produces the opposite failure and produces it visibly: a location that the original resumes fully populated comes up **empty**, and stays empty, because the type array it would have to walk was never loaded.

*Corrected (issue #184).* This entry previously described the town-family entry as unconditionally clearing every slot except slot zero and running the roster load and reseat, and `systems/town-mode.md` Section 5 described the preserving form as differing only in that "the active-object table tail is not zero-cleared". Both are withdrawn. See `RETRACTIONS.md` row R341.

The roster that issue used as its worked example - Iolo's Hut's three
rodent-class actors and Smith the horse - stands on forest and grass cells that
both the party's terrain test and the NPC pathing predicate accept, so the four
reseated records are placed on cells terrain cannot refuse (established
2026-09-04 from the shipped page; private analysis in `u5-decomp/notes/`).

**Overworld entry.** The selected plane's current `.OOL` replaces the entire
live table byte-for-byte; records are not compacted or copied into newly chosen
slots. Slot zero is included. Outdoor setup then synchronizes slot zero's X/Y
to the party globals and its type/frame to the saved transport marker while
preserving its reloaded auxiliary bytes. Before normal outdoor input begins,
entry also consumes the one-shot pending vehicle-acquisition state used by
shipwright purchases: after that reload and slot-zero synchronization, it
allocates a free ordinary slot, writes the pending coordinates, initializes
either a ship-family object with hull/skiff auxiliary state or a skiff-family
object, and clears the pending state. Those pending coordinates are the fixed
delivery cell of the shipwright that sold the vessel, published per row in
`systems/shops.md` Section 8.7; they are not the town's entrance or exit cell.
Random encounters, dropped items, and spawned creatures appear in the table
over the course of overworld play and are pruned when they leave the player's
viewport: the overworld per-turn walker checks each slot's distance from the
scroll bases and frees slots more than thirty-two cells away.

**Dungeon entry.** Dungeon exploration does not populate the table for its first-person view. The dungeon loop reads the player's dungeon Z/X/Y and facing globals, renders from the loaded dungeon record, and does not run the town NPC scheduler or the overworld active-object walker. The active-object table remains part of global saved state, but it is not the dungeon renderer's actor list. If a dungeon room, trap, ambush, or attack enters combat, the combat framer takes over as described in Section 9.

**Combat entry.** Section 9.

Slot zero is preserved, reloaded, or written by the entry handler before any
new non-player object is allocated. No mode runs with slot zero empty.

## 11. Persistence in saves

The active-object table is persisted as part of the save image. The save format reserves a two hundred fifty-six byte region; on save, the engine writes the live table verbatim; on load, it reads the region back into the live table. Persistence is byte-for-byte **within a scene, between object-list reloads**: empty slots stay empty and filled slots keep their tile, coordinates and animation byte for as long as the party stays in the scene the save was taken in.

**The qualifier is not decorative.** Every return to the overworld reads the whole two-hundred-fifty-six-byte per-plane object list straight over the live table, replacing all eight bytes of all thirty-two slots — from both the town return and the dungeon return, not only on the first entry of a new game. Outdoor setup then re-synchronises slot zero (Section 10). A natural-moongate warp performs the mirror operation, writing the live table back out to the per-plane file before the warp. So a slot's bytes round-trip through `SAVED.GAM` inside a scene, and are replaced wholesale the moment the party steps back onto the overworld. *Corrected (issue #184): this section previously called the per-plane object list a seed file "copied into the table on first overworld entry of a new game", which understated it by a whole class of overwrites and contradicted Section 10 of this same document. See `RETRACTIONS.md` row R342.*

**The NPC runtime family is persisted too, and is not rebuilt on load.** The schedule table, the per-NPC runtime state, the path queues and their read pointers, the type array and the stuck counters all live inside the save image (`formats/saved-gam.md` Section 12), immediately after this table, and a town-family load reaches its entry pass in the preserving mode that skips the roster load and the reseat entirely (Section 10). Loading a town-family save therefore restores the cast **exactly as it stood at the save**, mid-route positions and queued paths included — it does not snap NPCs back to their scheduled waypoint. An implementation that persists this table alone and rebuilds the NPC layer from the schedule and the hour resumes an empty location instead. *Corrected (issue #184): this section previously stated that the runtime descriptor table is "not persisted", that descriptors are "re-initialised from the schedule and current hour" on load, and that the visible effect is that "loading reverts NPCs to their currently-scheduled location". All three are withdrawn; `systems/npc-schedules.md` Section 13 and `systems/town-mode.md` Section 16 carried the same claim and are corrected with it. See `RETRACTIONS.md` row R341.*

The runtime save-overlay is the current working copy of the *other* plane's cast, written alongside the main save file. The combat backup region is not persisted; saving inside combat is not supported.

## 12. Hooks into other systems

**NPC scheduler.** Reads the table for the player's position (slot zero) and writes it indirectly through the world-mutation helper on every NPC step that crosses the player's floor or moves within it. The scheduler's runtime descriptor holds the linked-slot index that ties one logical NPC to one active-object slot.

**Renderer.** Walks the table from slot thirty-one down, projects each slot's world coordinates into the on-screen viewport, and stamps the slot's tile into the viewport scratch grid (skipping cells already obscured by fog or already containing a higher-priority sprite). Slot zero (the player) draws last. Special tile classes get class-specific compositor branches that consult the auxiliary bytes: the water-bound `0xE8..0xEB` class and exact `0x1E` / `0x1F` type bytes stamp through the companion terrain band and leave the visibility grid with the use-companion marker; water-creature frame bytes `0x1D` and `0x1E` use the same companion-band path; and a slot whose type byte is exactly `0x5C` stamps its own sprite through the companion band when the terrain under it is the chair id `0x92`, otherwise falling through to the default compositor with its frame byte reduced by eight. *Retracted:* an earlier revision called that last one "the `0x5C` vehicle/avatar-family branch" taking "the special vehicle stamp". It is neither a vehicle nor an avatar branch — `0x5C` is one ordinary NPC sprite family, and the party's own type byte is the party sprite marker, never `0x5C` outside combat. Its effect is that an actor of that one family seated on a chair of that facing keeps its own sprite instead of merging into an occupied-chair tile. See `RETRACTIONS.md` and `systems/visibility.md` Section 8.

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

**Per-tick animator.** Runs once per world tick (the input system's idle loop), advancing each non-empty slot's animation phase and rolling facing/frame decisions for monster classes. It moves no actor (Section 8, R316). It animates only the actor classes held in the table; it drives no water, lava or torch terrain *cycle*. Animated *terrain* belongs to the separate world-tick tile animator and its five families (`systems/animation.md` Section 6) and, for water, lava, rivers and fire fixtures, to the driver-side tile-asset pass that runs in the same step (`systems/animation.md` Section 12) - which is also where the banner and sail tiles are animated, on a stage of that pass published only as *probable* and not observed at runtime (`systems/animation.md` Section 12.5). Neither of those is an active-object concern, but neither is absent: an earlier revision's "no water, lava or torch animation" reading of this sentence is withdrawn.

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

**Open (issue #189): whether the animator runs during dungeon and combat play.**
It certainly runs at least once on dungeon *entry* — the dungeon overlay calls
the shared world tick directly from its entry path, and neither of the two flags
that can suppress the animator is in a suppressing state at that moment. What was
not established is whether it runs on any *later* dungeon turn, because the only
other route in is the shared command wait's idle step, and the scene-value band
the dungeon actually occupies during play was not pinned against that wait's
suppression range (`systems/timing.md` Section 8.2). The combat case is likewise
untraced. This matters because the dungeon overlay reuses two of this table's
records as its own scratch, saving them on entry and restoring them on exit; the
animator's phase decrement runs ahead of every class test, so a synthetic value
in the reused facing/phase byte would be decremented under it. An engine that
runs the animator only in the world modes is safe under either resolution; one
that runs it everywhere should not also reuse table records as scene scratch.

## 14. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The dungeon loop's first-person rendering path and its absence of NPC/active-object population during exploration — `u5-decomp/functions/DUNGEON_OVL/`.

- The per-tick animator that walks the table to advance animation phases and roll monster facing changes — `u5-decomp/functions/ULTIMA_EXE/`.
- The animator's complete record-write set, the depth-six sweep of the world
  tick's call tree that found no other write into this table, the absence of any
  per-turn movement roll in the outdoor walker, and the separate town-mode
  object walker for loose horse-family objects, with its own one-in-two
  per-slot coin. Source
  provenance: derived from private analysis note
  `u5-decomp/notes/2026-09-02_issue-180_per-turn-wander-gate.md`.
- The compositor's companion-band write, the renderer's zero-grid-cell branch,
  the `+256` actor index rule and the reserved transparent value —
  `u5-decomp/notes/`.
- The resident active-object acquisition cascade and slot initialiser -
  `u5-decomp/functions/ULTIMA_EXE/`.
- The `0xB5` actor-class interpretation is cross-checked against the shipped
  NPC roster analysis in `u5-decomp/formats/`.
- The overworld per-turn slot walker, its exact outdoor type-byte predicate,
  the proof that both animation and pruning classify record byte zero alone,
  hostile reaction dispatch, water-creature step path, per-slot movement
  dispatch, directed step planner, and proximity helper -
  `u5-decomp/functions/MAINOUT_OVL/`, and
  `u5-decomp/functions/MAINOUT_OVL/`.
- Source provenance: the exact-equality breath recognition, the
  adjacency-before-class ordering, the identification of `0xE0..0xE3` as the
  Sand Trap run and of its adjacency arm as silent-but-damaging, the generic
  adjacent arm's exact terrain and marker sets, its complete class/banner and
  arena-selector handoff, the descending walk's ability to process more than
  one adjacent hostile, and the withdrawal of the on-foot whirlpool no-op,
  were **re-derived from the
  shipped binaries** in a verification pass that read each routine from entry to
  exit and did not use any private note as evidence. Sprite-run identity was
  fixed two independent ways: the shipped description strings for the sprite
  pages, and the published `class * 4 + 0x40` actor-byte rule of
  `catalogs/tile-catalog.md` Section 7 applied to
  `catalogs/monster-bestiary.md` class numbers. Working directories:
  `u5-decomp/functions/MAINOUT_OVL/` and `u5-decomp/functions/ULTIMA_EXE/`.
  The older private interpretation that named the `0xE0` adjacency arm after
  the sea serpent was corrected in the same pass.
- The resident tile-class dispatcher and reverse active-object lookup used by
  outdoor step validation -
  `u5-decomp/functions/ULTIMA_EXE/`.
- The compositor that walks the table backwards to stamp on-screen sprites into the viewport, plus the fog post-pass — `u5-decomp/functions/ULTIMA_EXE/`.
- The world-mutation helper that links logical NPC state to a slot in the table when an NPC arrives on or leaves the player's floor — `u5-decomp/functions/TOWN_OVL/`.
- The town-entry Shadowlord install that allocates an active-object slot and a parallel high-indexed NPC slot for a resident Shadowlord — private analysis in `u5-decomp/functions/TOWN_OVL/` and `u5-decomp/notes/`.
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
- The save image's region holding the table and the on-disk overlay files — private analysis in `u5-decomp/formats/`.
- The town round trip's whole-table `.OOL` write and reload, slot-zero
  inclusion, outdoor synchronization, and shipwright-delivery ordering —
  private analysis in `u5-decomp/functions/MAINOUT_OVL/`,
  `u5-decomp/functions/OUTSUBS_OVL/`, `u5-decomp/functions/ULTIMA_EXE/`, and
  `u5-decomp/notes/`.
- Source provenance: derived from private analysis in
  `u5-decomp/notes/` -- the confirmation
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
- Source provenance: the packed encoding of record byte 6 and the animator's
  real gate order, the per-frame slot-zero rebuild's write set, the entry-mode
  argument of the town-family setup pass and everything mode zero suppresses,
  the presence of the whole NPC runtime family inside the save image, and the
  wholesale per-plane object-list reload on every return to the overworld are
  derived from private analysis in `u5-decomp/notes/`, cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/functions/TOWN_OVL/`,
  `u5-decomp/functions/NPC_OVL/` and `u5-decomp/functions/MAINOUT_OVL/`. The
  slot-zero auxiliary-byte claim in Section 5 is scoped in the text as a trace
  of the routines that own slot zero rather than a census; a pointer-based
  census of this table is not feasible, and the three named exceptions are the
  ones that trace found.
