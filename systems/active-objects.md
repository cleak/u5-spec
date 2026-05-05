# Active objects

## 1. Overview

Ultima V's runtime stage — the place where everything visible and not painted-on-the-floor lives — is a single fixed-size array called the *active-object table*. Thirty-two slots of eight bytes each: two hundred fifty-six bytes total in the resident data segment. One slot is the player; the rest are NPCs, monsters, projectiles, vehicles, animated tiles, scripted props, and any other moving or otherwise non-static entity on the player's current view of the world.

Every mode reads and writes this same table. The renderer composites it into the viewport. The visibility producer consults it for line-of-sight blockers. The NPC scheduler links into it when its NPCs cross onto the player's floor. The combat framer swaps it for an isolated combat instance and swaps it back when the fight ends. The save image preserves it byte-for-byte.

The design is "simple, fixed, and shared." There is no spatial index, no linked list, no per-mode subclass. Every system that touches dynamic on-screen content goes through these thirty-two slots, and every slot is a flat eight-byte record interpreted differently by different systems. This shared, untyped, fixed-size table is what lets the engine's sub-modes hand the world cleanly back and forth.

## 2. Table shape

The active-object table is a flat, contiguous, two hundred fifty-six byte block: thirty-two records of eight bytes each. Records are addressed by slot index `0..31`; field offsets within a record are `0..7`. The table lives at a fixed location in the resident data segment, directly readable and writable by every module.

A slot is *empty* when its first byte (the type/tile byte) is zero. Allocating a slot writes a non-zero value to byte zero; freeing a slot writes zero back. Slot zero is reserved for the player. The convention is unbreakable: every system that wants the player's on-screen state reads slot zero, and slot zero never gets compacted, swapped, or stolen.

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
|   5  | `dep1`       | Auxiliary state byte. Used variously: vehicle-passenger flag, projectile-velocity, animation extra.               |
|   6  | `phase`      | Packed animation phase (low nibble) and direction-step counter (high nibble). Advanced by the animator.           |
|   7  | `dep3`       | Auxiliary flag/aux byte. Carries class-specific state — monster HP for combat-instance records, etc.              |

A few observations on the field encoding:

**Type-byte conventions.** Byte 0 carries both "is this slot allocated?" (zero / non-zero) and a tile-class identifier (the high six bits used as an index into a per-class attribute table that the animator and dispatcher consult). The low two bits of byte 0 are reserved for sub-type or facing info on certain tile classes. A handful of byte-0 values are sentinels rather than tile classes: the value used to mean "this is the player slot" is one such sentinel, and the engine's slot-finder for the player searches by exact match against this sentinel rather than walking by index.

**The phase byte.** Byte 6 packs two pieces of state into one byte: the low nibble counts down through animation frames (with the all-ones value meaning "rest at steady frame, do not animate"), and the high nibble holds a direction-step counter that AI movement uses. The animator's per-tick rule is: if the low nibble is at the steady-state marker, leave the slot alone; if non-zero, decrement; if zero, the slot is eligible for an AI tick that may pick a new direction or move the slot one cell.

**Auxiliary bytes 5 and 7.** Different systems use these slots differently. The renderer reads them only for specific tile families (vehicles, water creatures, projectiles), where they hold rider type or next-tile-overlay data. Combat-instance records repurpose byte 5 as a per-actor speed counter and bytes 6 and 7 as per-actor X and Y in arena coordinates. Byte interpretation is therefore not type-uniform across world and combat instances; readers must know which mode is active.

**Coordinate axes.** Bytes 2 and 3 hold cell coordinates. In overworld and town/dwelling/castle/keep modes, they are world coordinates. In combat-instance use, they are arena coordinates on the eleven-by-eleven arena. The renderer's projection step subtracts the player's position to find each slot's offset in the on-screen viewport.

The eight-byte record fits a power-of-two stride. Implementations that prefer parallel arrays per field can split the record without changing the system's contract, as long as slot index mapping stays consistent between the active-object subsystem, the NPC subsystem (which holds slot indices in its runtime block), and the combat subsystem (which writes one record per actor).

## 4. Slot allocation and freeing

Slot allocation is centralised in a single resident helper. When a system needs a new active-object slot — an NPC arriving on the player's floor, a monster being placed by combat setup, a projectile spawning — it calls the allocator and receives a slot index. The allocator walks the table for the first slot with a zero type byte and returns its index. The engine never tries to allocate more than thirty-two slots; spawn-count caps and mode-entry initialisation that clears the table together guarantee this.

Slot freeing is a one-byte write: zero to byte 0. There is no separate free-list, no compaction pass, no garbage collector. The next allocation walks from low index upward and finds the freed slot.

A few call sites use a *highest-empty-slot-down* discipline rather than the allocator's lowest-up scan. The player-as-NPC attachment helper, for example, walks the parallel NPC type array from index thirty-one down looking for an empty NPC slot. The intent is to keep low NPC indices reserved for schedule-driven NPCs from the location's roster while the player's "NPC mirror" lives in a high index that won't collide. The discipline lives at the call site, not in the allocator.

A second-level helper sits behind the allocator: the *initialiser*. After a slot is allocated, the initialiser takes the slot index plus the tile byte, type byte, target coordinates, and floor, and writes them into the record in one pass. The split (allocator finds slot, initialiser fills it) lets call sites that already know the slot index — combat setup, the player attachment helper — bypass the search.

The table is never compacted or defragmented. Repeated allocate-and-free fragments empty slots between occupied ones; that is the steady-state condition and costs nothing measurable at thirty-two slots.

## 5. The player slot

The player occupies slot zero. Every world frame, the compositor refreshes bytes 0..4 of slot zero from the world-state globals (the avatar tile id, the active player's position, the floor index). The renderer then walks the table from slot thirty-one down so slot zero paints on top.

The world-state globals are the *authoritative* source for player position; slot zero is a *derived* view that other systems read — NPCs computing distance to the player, the visibility producer determining what the player blocks. Slot zero is never freed, compacted, or reallocated; mode entries preserve it; the combat backup-and-restore preserves it.

A second representation of the player exists in town / dwelling / castle / keep modes: the *player-as-NPC* slot. On entry, the engine allocates a high-indexed NPC slot and stamps a sentinel value into its type byte and the player's spawn coordinates into the coordinate fields. The runtime descriptor is populated with a stationary three-waypoint schedule pinning the player to the spawn cell. The NPC scheduler then treats the player as a static NPC; the "already-on-waypoint" check passes every tick; the player never actually moves through the scheduler. The active-object slot is still slot zero — the player has two representations, in two different tables, referring to the same conceptual entity.

The pattern exists because town-mode helpers walking the NPC table for collision checks, spell targeting, and "talk to whoever is in this cell" need to find the player there. Without the second representation, the player would be invisible to those helpers. With it, uniform code handles both NPC-NPC and player-NPC interactions.

The player-as-NPC slot is allocated on town entry and preserved across re-entries to the same town (the setup helper checks for an existing slot with the player sentinel byte and returns early if found). Cross-location re-entries clear all NPC slots; the new town creates a fresh one.

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

The per-NPC runtime descriptor's slot index and the active-object slot index are independent. The player-as-NPC mirror lives at a high *NPC* index; the player's avatar lives at active-object *slot zero*. Schedule-driven NPCs occupy low NPC indices and land in low active-object slot indices in arrival order.

## 7. Monster slots

Combat mode uses the same active-object table for combatants, but the contents are different — a combat instance, not a world snapshot. The combat framer's enter/exit save-and-restore (Section 9) is what makes this work: combat overwrites the table with combatant records and restores the world's table on exit.

Within combat, slot zero is still the player. Slots one through twenty-five (capped at twenty-six total combatants) are populated by the monster-placement helper at entry. Each spawned monster gets one slot with the monster's tile class in byte 0, the per-frame tile byte at byte 1, arena coordinates in bytes 2 and 3, and a floor flag at byte 4. The auxiliary bytes 5..7 are repurposed: byte 5 is a per-actor speed counter, bytes 6 and 7 hold per-arena coordinates duplicated for the combat round walker.

A *parallel* combat-effect descriptor table holds the additional per-actor state combat needs — base-step, phase counter, target index, flag bits — at a different data-segment location, indexed by the same slot index. The two tables are kept in sync by the per-action primitive: when an actor moves, its coordinates are written into both.

The split keeps combat-only state out of the world-mode table. When combat exits, the active-object table can be restored cleanly because it never accumulated combat-internal flags during the fight. The combat round walker, described in the combat spec, iterates the combat-effect descriptor table for action selection and reads the active-object table for sprite rendering.

## 8. Animation

A per-tick animator runs once per world tick, walking the table from slot zero to slot thirty-one. For each non-empty slot, the animator advances the animation phase and, when the phase reaches zero, may roll an AI direction change for monster-class slots.

The animation cycle uses byte 6's low nibble. It counts down each tick:

| Phase value   | Meaning                                                                                                       |
|---------------|---------------------------------------------------------------------------------------------------------------|
| steady marker | Steady; do not animate this slot. The animator skips. (Encoded as the all-ones nibble.)                       |
| any non-zero  | Mid-cycle. Decrement and write back. The renderer combines the phase with the tile class to pick a frame.     |
| zero          | Cycle ended. Eligible for an AI tick: roll RNG, possibly turn or move, possibly reseed phase.                 |

Animated tile classes include water (a four-frame cycle), lava, torches, and a small handful of "special" tiles. Each animated class has its current-frame index in a separate animation-frame table; the renderer combines the tile class with that counter to pick the actual byte to paint.

Two responsibilities sit slightly outside the per-slot loop. A *frame-counter advance* runs at the end of the pass, incrementing a shared frame counter and toggling a few alternate-frame tile classes. A *video-driver flush* runs immediately after, sending the post-tick frame to the display driver. Both are part of the "advance one tick of on-screen state and present it" contract.

Some slots also receive AI ticks during the same pass: hostile creature classes that wander on the overworld (or in towns past their schedule) get an RNG roll on their phase-zero tick that may turn or step them one cell. Probability is gated by tile class — different monsters wander with different rates — and the eight-way direction decision is dispatched through a small jump table indexed by the current direction nibble.

The animator does not move the player. Player movement is owned by the input system and per-mode command handlers; the animator only refreshes slot zero from world-state globals at the start of its pass.

## 9. Combat backup and restore

Combat suspends the world by swapping the active-object table to a backup region and overwriting the live table with combat actors. The mechanism is a pair of byte-for-byte copies.

**Enter combat.** The framer copies the entire two hundred fifty-six bytes of the live table into a fixed backup region. It runs one of three setup paths (terrain, ambush, or scripted) that populate the live table with combatants. Only after this swap does the framer call into the round loop.

**Exit combat.** On round-loop return (victory, defeat, or escape), the framer restores by copying the backup region back over the live table. Every byte returns to its pre-combat value: world NPCs to their pre-combat coordinates, vehicles to where they were docked, projectiles to their last position. The world resumes exactly where it left off.

The backup region is dedicated to this purpose, not preserved across saves, a transient buffer used only inside the framer's call. The framer also saves and restores the player's world coordinates (combat overwrites slot zero's coords with arena coords), the active-player byte, and a scene-byte sentinel that signals "combat is in progress." The calling mode loop sees combat as a function call that returns with the table and globals exactly as they were, plus side effects (damage, death, time advance) baked into separate persistent state.

The copy is byte-for-byte; slot indices are stable across the round-trip. An NPC in slot fifteen before combat is in slot fifteen after, with the same tile and coordinates. The NPC scheduler resumes per-tick walking without re-allocation.

## 10. Mode-entry initialisation

Each mode's entry handler initialises the table according to its needs.

**Town / dwelling / castle / keep entry.** Clears every slot except slot zero. Runs the per-NPC roster load (building runtime descriptors and schedules), the per-NPC initial-waypoint placement (calling the world-mutation helper for each NPC currently on the player's floor, allocating slots), and finally the player-as-NPC attachment helper (which finds an empty NPC slot, allocates an active-object slot for the player, and stamps the player sentinel value into both). Result: slot zero has the avatar, a handful of low-indexed slots have on-screen NPCs, and the highest empty NPC index gets the player-as-NPC mirror.

**Overworld entry.** Slot zero is the player. The remainder of the table is populated from the on-disk overworld object overlay (per-map static object lists). Each non-zero record from the overlay is copied into a free slot. Random encounters, dropped items, and spawned creatures appear in the table over the course of overworld play and are pruned when they leave the player's viewport: the overworld per-turn walker checks each slot's distance from the scroll bases and frees slots more than thirty-two cells away.

**Dungeon entry.** Whether dungeon mode populates the table is an open question (Section 13). The available decompilation is consistent with "dungeon uses the same table for player only, plus combat instances when fighting."

**Combat entry.** Section 9.

Slot zero is preserved or written by the entry handler before any other slot is touched. No mode runs with slot zero empty.

## 11. Persistence in saves

The active-object table is persisted as part of the save image. The save format reserves a two hundred fifty-six byte region; on save, the engine writes the live table verbatim; on load, it reads the region back into the live table. Persistence is byte-for-byte: empty slots stay empty, filled slots keep their current tile, coordinates, and animation phase.

The NPC scheduler's runtime descriptor table is *not* persisted. On load, descriptors are re-initialised from the schedule and current hour, "re-snapping" each NPC to its scheduled waypoint. The scheduler then re-allocates active-object slots through the world-mutation helper. The asymmetry produces a brief inconsistency at load time — saved table positions versus freshly-rebuilt waypoint positions — that the runtime initialiser resolves by overwriting NPC slots with re-derived waypoint coordinates. Visible effect: loading reverts NPCs to their currently-scheduled location, as already documented in the schedule spec.

The on-disk overworld object overlay (per-map static object list) is a *seed* file, copied into the table on first overworld entry of a new game. The runtime save-overlay is the *current* working copy, written alongside the main save file. The combat backup region is not persisted; saving inside combat is not supported.

## 12. Hooks into other systems

**NPC scheduler.** Reads the table for the player's position (slot zero) and writes it indirectly through the world-mutation helper on every NPC step that crosses the player's floor or moves within it. The scheduler's runtime descriptor holds the linked-slot index that ties one logical NPC to one active-object slot.

**Renderer.** Walks the table from slot thirty-one down, projects each slot's world coordinates into the on-screen viewport, and stamps the slot's tile into the viewport scratch grid (skipping cells already obscured by fog or already containing a higher-priority sprite). Slot zero (the player) draws last. Special tile classes — boats, water creatures, projectiles — get class-specific compositor branches that consult byte 5 or byte 7.

**Visibility producer.** Active-object slots that block sight (boats, creatures, NPCs) act as dynamic occluders during the line-of-sight pass. The producer reads the table once per frame and treats blocking slots as opaque cells when computing the visibility grid.

**Combat.** The framer swaps the table to a backup, runs combat with combatant records in place, and restores. The round walker reads slot zero for the player and slots one and up for monsters; the parallel combat-effect descriptor table holds round-only state.

**Per-tick animator.** Runs once per world tick (the input system's idle loop), advancing each non-empty slot's animation phase and rolling AI movement decisions for monster classes. Also drives water, lava, and torch animation cycles via per-tile-class frame indices.

**Save / load.** The table is a persistent region in the save image, byte-for-byte.

**Time.** No direct hook. Animation is per-tick, not per-hour; the animator does not consult the time system.

## 13. Open questions

- **Combat-instance byte interpretation.** The combat instance repurposes the auxiliary bytes for round state. Which world fields are preserved and which are overwritten by combat setup is a point that needs verification; the Section 7 mapping is the working hypothesis.

- **Dungeon-mode use of the table.** Dungeon mode may use a separate table or share this one with only the player slot populated. The available decompilation does not yet show a dungeon equivalent of the town scheduler or the overworld per-turn walker driving this table; the working hypothesis is "player only, plus combat instances when fighting."

- **The allocator's full algorithm.** First-empty-slot is the established behaviour, but the table-full edge case (sentinel? wrap?) is not fully traced. Call-site discipline keeps the table from filling in practice; the allocator may simply trust this.

- **Projectile and animated-effect lifecycle.** Spell projectiles and similar transient entities live in the table for a few ticks then disappear. Whether they auto-free via a counter in the auxiliary bytes or are removed by the spawning system is open; the animator does not free slots itself.

- **The full enumeration of byte-0 sentinel values.** The player-as-NPC sentinel is documented; possible vehicle, moongate, and boat sentinels are read by the compositor but not catalogued.

- **The boat-and-water-creature compositor branches.** The renderer dispatches on type-byte family for water-bound objects and water-creature monsters. The full set of triggering values has not been integrated here.

- **Mode-entry initialisation for dungeon mode.** Tied to the dungeon question above.

- **Cell-collision rules for the player-as-NPC slot.** Town-mode helpers walking the NPC table for collision detection must recognise the player sentinel and skip it. The exact tests are not yet documented.

## 14. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The per-tick animator that walks the table to advance animation phases and roll monster AI movement — `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
- The compositor that walks the table backwards to stamp on-screen sprites into the viewport, plus the fog post-pass — `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md`.
- The world-mutation helper that links logical NPC state to a slot in the table when an NPC arrives on or leaves the player's floor — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The player-as-NPC attachment helper that allocates a slot and a parallel high-indexed NPC slot for the avatar on town entry — `u5-decomp/functions/TOWN_OVL/0x02AE_town_attach_player_slot.md`.
- The overworld per-turn walker that animates and prunes off-screen entries — `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The combat round loop that operates on the table during combat — `u5-decomp/functions/COMBAT_OVL/0x0B94_combat_main_loop.md`.
- The combat enter/exit framer that backs up and restores the table — `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The NPC per-tick walker that drives schedule-based NPC movement and feeds the world-mutation helper — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The save image's region holding the table and the on-disk overlay files — `u5-decomp/formats/saves.md`.
