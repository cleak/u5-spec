# Animation

## 1. Scope

Ultima V has two animation layers that run during normal play:

- **Active-object animation**, which advances the per-slot phase for visible
  actors, vehicles, monsters, projectiles, and other dynamic entities.
- **Global tile animation**, which advances shared frame selectors for terrain
  and effect tiles such as water, lava, torches, moongates, and other repeating
  map artwork.

Both layers are visual and turn-paced. They are not independent real-time
threads, and they are not driven directly by the in-world clock. They advance
when the resident world-tick path runs, which usually happens while the input
system is waiting for the next key and while mode loops finish a consumed turn.

This document describes the behaviour contract for those animation layers. It
does not prescribe the renderer's pixel pipeline, the active-object record's
private memory address, or the original executable's jump tables. Those details
remain in the private decompilation notes.

## 2. Cadence

The animation system runs from the resident world-tick path. The input system
calls that path while polling for a command, so idle time is not visually
frozen: cursor blinking, animated water, monster wandering, and viewport
refreshes can continue while the player has not pressed a key.

The world-tick path may be suppressed for one initial handoff frame after a
mode transition. Once the mode has settled, animation runs on each steady tick.
The important implementation rule is that animation is *tick based*, not wall
clock based. If an implementation polls input faster than the original did, it
must still choose a stable simulation cadence rather than advancing animation
on every host-frame paint.

Animation is also separate from Britannian time:

- The time system advances minutes, hours, days, and daylight.
- The animation system advances sprite phases and shared tile-frame selectors.
- A single player command may cause both systems to run, but neither derives
  its state from the other's counters.

The same separation applies to NPC schedules. The scheduler decides where an
NPC should go based on the current hour and the location roster. The animator
only advances the visible active-object slot that represents that NPC after it
has been placed on the current floor.

## 3. Active-Object Phase Model

Every dynamic on-screen entity lives in the active-object table described in
`systems/active-objects.md`. Each slot carries a phase byte with two packed
roles:

| Part | Role |
|---|---|
| Low half | Animation phase counter. |
| High half | Direction or movement substate used by wandering actors. |

The low half has three behavioural states:

| Phase state | Behaviour |
|---|---|
| Steady marker | Leave the slot untouched for this tick. |
| Non-zero animated phase | Decrement the phase; the renderer sees the new phase on the next draw. |
| Zero | The animation cycle has reached its decision point; the slot may receive an autonomous movement or direction update. |

This means animation is countdown-based. A moving or animated entity is seeded
with a finite phase; each tick reduces that phase until the slot reaches a
decision point. The steady marker is the opt-out value used for slots that are
visible but not currently animating.

The phase counter itself does not encode pixels. It is a small state value that
the renderer and class-specific logic combine with the slot's tile or class to
choose a frame. Modern engines may represent this as explicit `phase` and
`direction` fields rather than a packed byte, as long as they preserve the
three-state countdown semantics.

## 4. Per-Slot Pass

On each animation tick, the engine walks every active-object slot in increasing
slot order. Empty slots are skipped. For each non-empty slot, it examines the
slot's phase and applies the phase model from Section 3.

The pass has four cases:

1. **Empty slot.** Do nothing.
2. **Steady slot.** Do nothing.
3. **Mid-cycle slot.** Decrement the phase and keep the slot's direction
   substate unchanged.
4. **Decision-point slot.** Consult the slot's class behaviour. Some slots do
   nothing; some roll for a direction change; some attempt a one-cell movement.

The pass does not allocate or free slots. It also does not run the schedule
planner for NPCs, resolve player commands, apply combat initiative, or execute
scripted movement. Those systems can seed phase values or update coordinates,
but the per-slot animation pass is limited to visual phase advancement and the
small set of autonomous wandering behaviours.

Iteration order is deterministic but not a drawing priority. Rendering walks
the table in the opposite direction so that lower-index slots paint on top.
Animation walks forward because the phase update itself has no need for
back-to-front composition.

## 5. Autonomous Wandering

When a slot reaches phase zero, a subset of dynamic classes can receive an
autonomous movement tick. This is the path used by wandering hostile creatures
and other non-scheduled actors that move without an explicit player command.

The movement decision is class-driven. The engine first reduces the slot's
type/tile byte to a broader behaviour class, then reads the class's movement
attributes. The attribute determines whether the actor can move, whether it
turns in place, whether it jitters randomly, and how likely it is to skip this
tick.

The observed behaviour can be specified without exposing the private class
tables:

- Some classes never wander; reaching phase zero leaves them in place.
- Some classes are gated by a random roll, so they move only on a fraction of
  eligible ticks.
- A few classes bypass the ordinary random gate and are effectively always
  considered when their phase reaches zero.
- Direction is eight-way. The decision code chooses among the eight compass
  directions or retains the current direction.
- A movement attempt is still subject to the normal collision and terrain rules
  of the current mode. The animator is not allowed to push actors through
  blocked cells merely because the phase expired.

For implementation, treat autonomous wandering as a narrow supplement to the
active-object system. Scheduled town NPCs remain schedule-driven; combat actors
remain combat-round-driven; the player remains input-driven. The animator's
wandering path covers ambient map creatures and similar actors that exist in
the world table between explicit commands.

## 6. Global Tile Animation

After the per-slot pass, the engine advances a second animation layer: shared
frame selectors for animated map tiles. These selectors are not stored in each
map cell. Instead, a small resident table says, for each animated tile family,
"which tile id should this family display right now?"

Known animated families include:

| Family | Behaviour |
|---|---|
| Water | Repeats through a four-frame cycle. |
| Lava | Repeats through a four-frame cycle. |
| Torch / fire light | Repeats through a four-frame cycle. |
| Special effect tiles | Repeat or toggle based on the shared frame counter. |
| Alternate decorative tiles | Toggle between paired frames on selected counter bits. |

The tile grid itself does not need to be rewritten for every animated water
cell. A map cell continues to mean "water"; the renderer resolves that semantic
tile through the current water-frame selector at draw time. This keeps the map
stable and makes one frame-counter update affect every visible cell in the same
family.

The global tile-animation step increments a shared frame counter after updating
the selectors. Some families use every tick; others use only selected bits of
the counter so they toggle more slowly. The exact private selector table belongs
in the decompilation workspace; the public contract is that animated terrain is
family-wide, deterministic, and driven by the same tick cadence as active
objects.

## 7. Presentation Flush

The animation tick ends by asking the active display driver to present or flush
the updated frame. The resident core does not know the details of EGA, CGA,
Tandy, or Hercules presentation at this point. It writes a driver command
through the display-driver dispatch cell and lets the loaded driver perform the
hardware-specific work.

This has two consequences for an implementation:

- Animation and presentation are coupled in the original: after advancing
  phases and tile selectors, the engine explicitly gives the display layer a
  chance to make the result visible.
- The animation rules are display-depth independent. EGA and CGA assets differ
  in pixel encoding, but the phase model and tile-family counters do not.

Modern engines may decouple simulation and rendering, but they should preserve
the ordering: update active-object phases, update global tile selectors, then
render/present the frame that observes both updates.

## 8. Mode Interactions

### Overworld

The overworld is the main consumer of ambient animation. Water, lava-like
terrain, moongate frames, vehicles, and random outdoor monsters all use the
animation tick. The overworld's per-turn epilogue can also prune off-screen
active objects; pruning is separate from animation and may remove slots that
would otherwise be considered on later ticks.

### Towns, Castles, Keeps, and Dwellings

In town-like scenes, scheduled NPC movement is controlled by the NPC scheduler.
The animator only advances the visible active-object slots after the scheduler
has updated them. If an NPC is off the player's floor and therefore has no
active-object slot, the animator has nothing to advance for that NPC.

Furniture, torches, water, and other animated environmental tiles use the
global tile-animation layer exactly as they do outdoors.

### Dungeons

Dungeon mode has less confirmed use of the active-object table outside combat,
but dungeon rendering still consumes animated tile families where applicable.
Dungeon dark-out, torch radius, and light spells are lighting concerns, not
animation concerns, even though torch artwork may animate at the same time.

### Combat

Combat has its own phase-counter system for actor initiative. That combat
phase model is separate from the active-object visual phase described here.
During combat, the round loop owns actor timing and actions; the world idle
animation path is suppressed except for presentation effects that the combat
loop explicitly invokes.

When combat exits, the combat framer restores the world active-object table.
The restored slots bring back their saved phase bytes, so the world resumes
from the visual state it had before combat began.

### Intro and Endgame Scenes

Cutscenes and endgame sequences may use dedicated animation helpers or display
driver commands outside the world-tick path. Those effects share the same
presentation layer but are scripted scene animation, not the general
active-object/tile animation system described here.

## 9. Persistence

Active-object phase state is persisted because the active-object table is saved
as part of the live game state. Saving and loading a game preserves each
occupied slot's current phase, direction substate, tile, and coordinates.

Global tile-animation selectors are transient. They are derived runtime state,
not semantic world state. A loaded game may restart shared terrain animations
from the engine's current selector values without changing gameplay. The visual
phase of water or torch flicker has no gameplay meaning.

The distinction matters:

- Persist per-object phase when saving active objects.
- Do not treat family-wide terrain frame selectors as authoritative map data.
- Rebuild or reset transient animation counters during startup or mode entry as
  needed, provided the resulting animation cadence is stable.

## 10. Implementation Rules

An implementation should follow these rules:

- Use a fixed simulation cadence for animation ticks. Do not let host rendering
  frame rate change game simulation speed.
- Keep visual animation separate from world time. A day-night transition is a
  lighting/time event, not a tile-animation event.
- Keep scheduled NPC movement separate from ambient wandering. The NPC
  scheduler owns schedule targets; the animator owns only phase advancement and
  class-driven wandering for eligible active-object slots.
- Represent the active-object phase as explicit fields if desired, but preserve
  the steady, countdown, and decision-point states.
- Advance global tile-family frames once per animation tick, not once per map
  cell.
- Apply movement/collision rules before accepting any autonomous movement
  produced by the animator.
- Present the frame only after both the per-slot pass and the global tile
  selector pass have completed.

## 11. Open Questions

- The exact public enumeration of every class attribute is not complete. The
  private notes identify the existence of the class-behaviour table, but the
  semantic names for all entries are still being correlated against monster,
  vehicle, and effect families.
- A few special classes bypass the ordinary random movement gate. Their visual
  identities are not all confirmed in public prose.
- Projectile and spell-effect lifetime is not fully separated from spawning
  handlers. The animator advances phases but does not appear to be the owner of
  slot deallocation for every transient effect.
- Dungeon-mode use of active-object animation outside combat remains less
  certain than overworld and town use.

## 12. Sources

This spec is a cleanroom rewrite derived from the following analysis notes and
public-bound specs. It intentionally omits private addresses, assembly, and raw
tables from the decompilation workspace.

- Active-object record shape, persistence, renderer order, and system
  interactions - `systems/active-objects.md`.
- Input idle-loop relationship to world ticks - `systems/input.md`.
- Time-system separation and per-turn cleanup cadence - `systems/time.md`.
- Per-slot animator, global tile selector update, and display-driver flush -
  `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
- Caller relationship from the resident world-tick path -
  `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- NPC scheduler separation -
  `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- Combat save/restore interaction -
  `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md` and
  `u5-decomp/functions/COMBAT_OVL/0x0B94_combat_main_loop.md`.
