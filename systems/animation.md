# Animation

## 1. Scope

Ultima V has **three** animation layers that run during normal play:

- **Active-object animation**, which advances the per-slot phase for visible
  actors, vehicles, monsters, and other slot-backed dynamic entities.
- **Global tile animation** (the *frame-selector pass*), which advances shared
  frame selectors for a small, fixed set of decorative terrain families —
  waterfall, fountain, pendulum, the standard of Britannia, and the grandfather
  clock / bellows pair. It is a table of "which id does this id draw as right
  now"; it never touches pixels. Water, lava and torch/brazier tiles are **not**
  among its families (Section 6), and natural moongates are not one of them
  either; see Section 8. A moongate does change appearance over time, but
  through a persisted presence phase owned by the overworld rather than through
  any layer here.
- **Driver-side tile-asset animation** (Section 12), which runs inside the
  loaded display driver and **rewrites the pixels of the loaded tile artwork in
  place** on every animation step. This is what animates open water, shoals,
  lava, the rivers and their composited relatives, and every fire fixture; a
  further stage of the same pass animates the banner and sail tiles, but that
  stage alone is published as *probable* and has not been observed at runtime
  (Section 12.5). It is a wholly separate mechanism from the frame-selector
  pass, it shares none of that pass's tables, and a renderer that
  implements only the frame-selector pass will draw all of those tiles perfectly
  still.

**Correction.** Earlier revisions of this document published only the first two
layers, and stated as a positive contract that "no water, lava, brazier or torch
tile animates through this pass **at all**", that "open water and lava-like
terrain do not" animate, and that "torches, braziers, fireplaces and interior
water are static tiles; they do not animate". The half of that which concerns
the frame-selector pass stands and is re-confirmed — none of those tiles has a
frame family or a selector byte, and retraction R148 is not reopened. The
generalisation to "they do not animate" is **withdrawn**: they animate, by the
driver-side pass of Section 12, and this was confirmed independently by
black-box capture of the shipped game. See `RETRACTIONS.md`.

All three layers are visual and step-paced. They are not independent real-time
threads, and they are not driven directly by the in-world clock. They advance
when the resident world-tick path runs, which usually happens while the input
system is waiting for the next key and while mode loops finish a consumed turn.
Section 13 gives the exact set of paths that run an animation step and the gates
on each; `systems/timing.md` Section 8 gives the wall-clock cadence.

This document describes the behaviour contract for those animation layers. It
does not prescribe the renderer's pixel pipeline, the active-object record's
private memory address, or the original executable's jump tables. Those details
remain in the private analysis notes.

The historical `FLAMES.OVL` file is not one of these animation layers. Its
public role is limited to supporting a temporary screen-preservation buffer
used by the proportional-font / Return-to-View path. The title-menu flame-style
idle effect is owned by the loaded display driver and is specified from the
intro/display contract, not from this gameplay animation system.

## 2. Cadence

The animation system runs from the resident world-tick path. The input system
calls that path while polling for a command, so idle time is not visually
frozen: cursor blinking, animated terrain, monster wandering, and viewport
refreshes can continue while the player has not pressed a key.

The world-tick path may be suppressed for one initial handoff frame after a
mode transition. Once the mode has settled, animation runs on each steady tick.
The important implementation rule is that animation is *tick based*, not wall
clock based. If an implementation polls input faster than the original did, it
must still choose a stable simulation cadence rather than advancing animation
on every host-frame paint.

**The tick is the BIOS timer tick, and the number is measured.** A black-box
capture of the shipped game (issue #179) timed every idle-screen animation in
the game onto one shared clock at **54.913 ms per step (18.2105 Hz)**, over
89.948 s and 1638 observed transitions, and reproduced the same figure at two
very different emulated CPU speeds. That control settles that the gameplay clock
is timer-driven rather than CPU-calibrated. Use **54.9 ms** as the animation
step interval. Structurally the figure is exactly the untouched PC interval-timer
rate, 54.9254 ms; `systems/timing.md` Section 8 owns the cadence contract, the
one place where it is conditional, and the catch-up rule.

Two qualifications an implementer must carry, because they are the difference
between "one step per tick" being a definition and being an observation:

- The measured figure is the cadence of the **idle command wait**, which is the
  path a player spends nearly all their time on. It is not a property of the
  animator itself. The animator advances once per *invocation* of the animation
  step, and Section 13 lists three callers, one of which fires twenty
  invocations inside the execution of a single command.
- Wherever this document or `catalogs/tile-catalog.md` gives a cycle length "in
  ticks", read it as **animator invocations**. On the ordinary idle path the two
  are the same number and the capture confirms it. Every traced caller pays a
  one-tick wait per frame, so the two have not been observed to diverge — but
  the equality is an observation about the paths that were traced, not a
  structural property, and command execution advances the animator too.

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
remain combat-round-driven; the player remains input-driven. > **Corrected 2026-08-31 (R315).** This paragraph previously ended: "The
> animator's wandering path covers ambient map creatures and similar actors
> that exist in the world table **between explicit commands**." That is
> withdrawn. The animator has no wandering path — it advances sprite phases and
> nothing else. Ambient map creatures do move, but on the **per-turn** path
> together with scheduled NPCs and the in-world clock, never on the idle tick.
> An engine that wanders actors from the animator will move the world while the
> player is standing still, which the original does not do.

## 6. Global Tile Animation

After the per-slot pass, the engine advances a second animation layer: shared
frame selectors for animated map tiles. These selectors are not stored in each
map cell. Instead, a small resident table says, for each animated tile family,
"which tile id should this family display right now?"

There are exactly **five** such families, and the pass that advances them is
short. Two families advance unconditionally; the other three sit behind two
**nested** gates on the shared phase counter, so the pass is not a flat list of
independently gated families. Named from the shipped description table, except
the fountain band, whose description record is the shared placeholder and whose
name comes from its Look handler (`systems/view.md` Section 3):

| Tile ids | Family | Behaviour |
|---|---|---|
| `0xD4..0xD7` | Waterfall | Four-frame cycle, advanced every tick. Ungated. |
| `0xD8..0xDB` | Fountain | Four-frame cycle, advanced every tick. Ungated. |
| `0x80..0x83` | Pendulum | Two-frame toggle in adjacent pairs. Inside the bit-0 gate, so it changes at half rate. |
| `0xEC..0xEF` | The standard of Britannia (a flag) | Four-frame cycle. Inside the same bit-0 gate as the pendulum, so it advances at half rate, **not** every tick. |
| `0xFA..0xFD` | Grandfather clock (`0xFA..0xFB`) and bellows (`0xFC..0xFD`) | Two-frame toggle in adjacent pairs. Inside the bit-1 gate, which is itself nested inside the bit-0 gate, so it changes at quarter rate. |

The gate structure, in order: advance the waterfall family, advance the fountain
family, then test bit 0 of the shared phase counter. If bit 0 is clear, the pass
skips **everything** that follows — pendulum, flag and clock/bellows alike — and
goes straight to incrementing the counter. If bit 0 is set, the pendulum and the
flag advance, and only then is bit 1 tested; the clock/bellows family advances
only when both bits are set. The counter is incremented once at the end of the
pass, whichever path was taken.

**Correction.** An earlier revision of this table listed `0xEC..0xEF` as
"advanced every tick" and summarised the pass as "short and unconditional" with
"three families advancing on every tick" and "the two toggling families reading
one bit each". All of that is **withdrawn**. Only two families are ungated, the
flag is gated exactly as the pendulum is, and the two gates are nested rather
than independent. The quarter rate of `0xFA..0xFD` is a consequence of that
nesting (bit 0 *and* bit 1), not of a lone bit-1 test.

**Confirmed by capture, in half.** A black-box capture of a castle courtyard
fountain (issue #179) counted exactly the same number of transitions as the
reference command cursor over 149.97 s — 2730 against 2730, one phase per
54.92 ms step, strict `0 1 2 3` order, full cycle 219.7 ms — and a pixel-level
pass over the same tile found exactly four distinct frames. That is an exact
match for the *ungated* rows of the table above. **The gated rows have not been
observed**: the pendulum, the standard and the clock/bellows pair were all
behind a locked door in that capture. Their half-rate and quarter-rate cadences
are established from the shipped code but remain unconfirmed at runtime.

### 6.1 The selector table itself

The selector table is a full 256-entry table indexed by tile id, holding the id
that each id currently draws as. Three properties of it are load-bearing:

- **It is initialised to the identity map at startup**, and after that only the
  five-family pass ever writes it. An id outside the five windows therefore
  draws as itself for the entire program run — this is exactly why a tile can be
  authored in four frames and still never animate (Section 6.2).
- **Every map byte is translated through it before being drawn.** The renderer
  does not special-case animated ids; it looks every ordinary terrain cell up in
  this table on every pass (`systems/visibility.md` Section 9).
- **It is transient and global.** It is not part of saved state, it survives map
  changes and reloads, and its shipped initial contents are all zero — the
  identity fill at boot is what makes it meaningful. The shipped phase counter
  starts at zero.

Each id inside a family owns its own selector byte, so the four ids of a
four-frame family are permanently a quarter-cycle apart and a wall of waterfall
cells does not flicker in lockstep. These are render selectors, not map edits;
the authored map byte remains the phase-zero tile id. Because the table starts as
the identity map, **the id the map author wrote selects both the fixture and its
starting phase**: a cell authored with the second frame of a family is
permanently one step ahead of a cell authored with the first, and the two are
never in phase.

### 6.2 `0xE8..0xEB` (the hourglass) is not a family, and is genuinely static

The atlas authors four hourglass frames and the shipped maps place only the
first, `0xE8`. That is the authoring signature of an animated family, and it is
misleading here. **The hourglass is not one of the five windows, has no selector
advance, and draws the exact id the map author wrote for the whole program
run.** The five windows in the table above are the complete list.

A caution that follows from this, and that cost real analysis time: **placing
only a family's base id is not evidence that the family is static.** The
standard of Britannia, `0xEC..0xEF`, is placed exactly once in the whole shipped
map set and only as its base id, and the animator does advance it. Argue
staticness from the animator's windows, never from the placement census.

The other three hourglass frames are consumed, but as discrete narrative states
rather than as a cycle; `formats/tiles.md` Section 6.1 publishes what consumes
them and which one is unreachable.

### 6.3 `0xFA`/`0xFB` are two phases of one clock

Confirmed. `0xFA..0xFD` is two independent two-frame fixtures, not four
fixtures and not one four-frame cycle: `0xFA` and `0xFB` are the two phases of a
single one-cell grandfather clock, and `0xFC`/`0xFD` are the two phases of a
single bellows. The pass flips the low bit of each id's selector, so both
members of a pair flip in the same step and two such cells on screen together
are permanently in opposite phase.

The supporting evidence is independent of the animator: the two clock frames are
the same cabinet with the pendulum bob drawn two pixel columns apart and differ
in 23 of the tile's 128 shipped bytes (the bellows pair likewise); the shipped
description table gives `0xFA` and `0xFB` **one shared** record, and `0xFC` and
`0xFD` one shared record; the Look handler masks off the low bit before matching
and reads the raw map byte rather than the animated frame, so phase can never
affect the description text; and the NPC-pathfinding blocking table and the
projectile-passability table make no distinction between the members of either
pair.

**A map authored with `0xFB` therefore behaves identically to one authored with
`0xFA` in every respect traced, differing only in which frame it starts on.**
This matters because the shipped data does exactly that: across every world,
location, cutscene, intro-screen and combat-arena terrain grid, ten cells are
authored `0xFA` and exactly one is authored `0xFB` — on an upper floor of the
castle whose ground floor carries a `0xFA` clock. Twelve cells are authored
`0xFC` and none `0xFD`.

Two byte ranges will look like counterexamples to anyone scanning the shipped
files, and are not: the packed dungeon-level file uses its bytes as nibble-packed
level and room codes rather than tile ids (it happens to contain fourteen bytes
equal to `0xFB`), and the placement-metadata bands of the combat-arena files are
active-object markers rather than terrain (they contain sixteen bytes equal to
`0xFC`). A trailing non-tile section of the miscellaneous-maps file holds three
further `0xFC` bytes that are likewise not placements.

### 6.4 A naming caveat on `0x80..0x83`

This document names `0x80..0x83` the *pendulum* family, and that label comes
from an earlier derivation rather than from the animator, which carries no
names. Independent analysis of the Blackthorn throne-room tableau for issue #179
reads the same two pairs as an **unoccupied** fixture (`0x80`/`0x81`) and an
**occupied** one (`0x82`/`0x83`) — the cutscene swaps `0x80` for `0x82` on the
first wrong answer, which only makes sense as an occupancy change
(`systems/blackthorn.md` Section 6.1). The animator's behaviour is unaffected
either way and is what this section specifies; the visual name is not settled and
an implementation should not depend on it.

**Correction.** Earlier revisions of this section headed the list with "known
animated families" of water, lava, and torch/fire light, plus unnamed
"special effect" and "alternate decorative" families, and described the tile grid
as continuing to "mean water" while the renderer resolved a water-frame selector.
All of that is withdrawn: **no water, lava, brazier or torch tile animates
through this pass at all.** The five families above are the complete list, and
none of them is a water or fire terrain family. `catalogs/tile-catalog.md`
Section 4 carried the same wrong family list and is corrected there.

The tile grid itself is never rewritten for an animated cell. A map cell
continues to mean, say, "waterfall"; the renderer resolves that semantic tile
through the family's current selector at draw time. This keeps the map stable
and makes one selector update affect every visible cell in the same family.

The global tile-animation step increments a shared frame counter after updating
the selectors. Two families — waterfall and fountain — advance on every tick.
The pendulum and the flag advance on every second tick, behind the shared bit-0
gate. The clock/bellows family advances on every fourth tick, behind the bit-1
gate nested inside the bit-0 gate. The public contract is that animated terrain is family-wide, selector-based,
deterministic, and driven by the same tick cadence as active objects — never a
per-cell sweep of the rendered tile buffer.

## 7. Presentation Flush

The animation tick ends by asking the active display driver to present or flush
the updated frame. The resident core does not know the details of EGA, CGA,
Tandy, or Hercules presentation at this point. It writes a driver command
through the display-driver dispatch cell and lets the loaded driver perform the
hardware-specific work. The public rendering contract is described in
`display-driver.md`.

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

The overworld is the main consumer of ambient animation. Waterfalls, vehicles,
and random outdoor monsters all use the animation tick. Open water, shoals and
lava do **not** use the frame-selector pass of Section 6 — they have no family
and no selector — but they are **not static**: they are animated by the
driver-side pass of Section 12, which scrolls their pixels. *An earlier revision
of this paragraph said "no water or lava family is animated at all", which an
implementation could only read as "the sea does not move". That is retracted;
open water visibly rolls, and the capture in Section 12 measures it.*
Natural moongates do not: a gate is a live terrain byte written and removed by
the once-per-turn saved-slot refresh, and it has no entry in the family table of
Section 6, no frame selector, and no advance from the animation tick.

**Correction.** An earlier revision of this sentence went on to say a gate has
"no frame cycle of its own", and an implementation could reasonably read that as
"the gate is a static sprite". It is not. A moon-gate cell is drawn through a
sixteen-phase rise-and-sink composition, and the phase is a persisted counter
that the once-per-turn refresh advances and that a blocking transition drives
directly. The full contract is `systems/overworld.md` Sections 9.1 and 9.2. What
belongs in *this* document is only the boundary: that phase is not a
tile-animation family, it is not on the tick cadence described here, and an
engine's animation clock must not try to own it. A skipped render frame does not
advance it; a consumed world turn does.

The overworld's per-turn epilogue also prunes off-screen active objects.
Pruning is separate from animation - it is not on the tick cadence described
here and the animator must not own it - and it may remove slots that would
otherwise be considered on later ticks. The normative contract, including the
trigger, the window test and the consumers, is `systems/active-objects.md`
Section 8.1; this mention is not sufficient to implement from.

### Towns, Castles, Keeps, and Dwellings

In town-like scenes, scheduled NPC movement is controlled by the NPC scheduler.
The animator only advances the visible active-object slots after the scheduler
has updated them. If an NPC is off the player's floor and therefore has no
active-object slot, the animator has nothing to advance for that NPC.

The decorative fixtures that animate indoors through the frame-selector layer —
the fountain, the pendulum, the standard of Britannia, and the grandfather
clock / bellows pair — use it exactly as they do outdoors.

Torches, braziers, fireplaces, street lamps, candelabra, stoves, spits, the
shrine flame and interior water animate too, through the driver-side pass of
Section 12 instead. *An earlier revision of this paragraph said they "are static
tiles; they do not animate". That is retracted.* Their flicker was measured
directly in a castle interior at one update per 54.9 ms step, and it is a
per-pixel re-randomisation rather than a frame cycle; Section 12 gives the
mechanism and the capture.

### Dungeons

Dungeon mode has less confirmed use of the active-object table outside combat,
but dungeon rendering still consumes animated tile families where applicable.
Dungeon dark-out, the torch counter, and light spells are lighting concerns, not
animation concerns; the torch artwork itself does not animate through this
layer.

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

The driver-side layer of Section 12 is transient in the same sense — nothing
about it is saved — but it is **not** reset, and that is a behavioural
difference rather than a bookkeeping one. It mutates the loaded tile artwork
itself, so its state lives in the asset buffer for the whole program run: the
water tiles keep whatever rotation they have reached, and the fire fixtures keep
every noise pattern ever XORed into them. Loading a saved game does not restore
pristine artwork. Section 12 states the parity consequence.

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
- Run the driver-side tile-asset pass of Section 12 in the same step, after the
  selector pass and before presentation. Model it as shared-asset state, not as
  per-cell or per-instance state.
- Present the frame only after the per-slot pass, the global tile selector pass
  and the driver-side tile-asset pass have all completed.

## 11. Animation Boundary And Remaining Catalog Work

The general animation contract is complete at system depth: world ticks advance
slot-backed phase counters, selected phase-zero classes may attempt autonomous
movement through the normal terrain/collision gates, shared tile-family
selectors advance once per step, the driver-side pass of Section 12 rewrites the
loaded tile artwork in the same step, and presentation is flushed after all
three layers observe the same step.

The following details belong to narrower catalogs or caller specs rather than
to this general animation layer:

- **Class-attribute catalog.** The exact public enumeration of every
  class-attribute entry belongs with active-object, monster, vehicle, and tile
  catalogs. This document only requires the semantic classes needed by the
  tick contract: steady slots, countdown slots, random-gated movers, and
  special classes that bypass the ordinary random movement gate.
- **Visual identity names.** A few special classes bypass the ordinary random
  movement gate. Their final art or entity names should be promoted in the
  owning catalog once confirmed, but the animation rule is already known:
  when their phase reaches zero, they are considered without the ordinary
  movement skip roll.
- **Projectile and impact effects.** Combat and spell projectile visuals are
  not persistent active-object lifecycles. They are direct scratch-buffer and
  renderer effects owned by combat, spell, ship-fire, and display callers.
- **Dungeon exploration.** First-person dungeon play does not use the
  active-object table as its actor list. Dungeon exploration uses dungeon
  position and cell data until a room, trap, ambush, or attack hands off to
  combat; combat then owns actor timing through its separate phase-counter
  model.

## 12. Driver-Side Tile-Asset Animation

This section specifies the third animation layer of Section 1. It is new to this
document: the specification previously described no such mechanism, and the
absence is what produced the withdrawn "water and fire are static" claims.

> **Every id in Section 12 is a tile-atlas index, not an actor byte.** The atlas
> has five hundred twelve entries in two halves: the terrain half
> `0x000..0x0FF`, whose values appear in map and arena grids, and the actor half
> `0x100..0x1FF`, reached by adding `0x100` to the actor byte an active-object
> record stores (`catalogs/tile-catalog.md` Section 3.1). Ids written here
> without a leading `0x1` are terrain-half indices; the four field tiles of
> Section 12.4 are written `0x1E8..0x1EB` because they are actor-half indices.
>
> This matters because three of the mask runs collide numerically with monster
> sprite runs published elsewhere. The masks `0xC0..0xC3`, `0xCC..0xCF` and
> `0xD0..0xD3` are terrain-half atlas entries. The identical numerals in
> `catalogs/monster-bestiary.md` and `systems/encounters.md` are **actor bytes**
> for Orc, Ettin and Headless, whose atlas entries are `0x1C0..0x1C3`,
> `0x1CC..0x1CF` and `0x1D0..0x1D3`. An engine that runs the two together
> XOR-flickers its monsters and draws stencils where creatures should be.

### 12.1 What it is, and the one property that defines it

Immediately after the frame-selector pass of Section 6, and in the same
unconditional tail of the same animation step, the engine calls into the loaded
display driver and asks it to run one animation step of its own. That call has no
gate of its own; whenever the animation step runs at all, this runs too
(Section 13). The driver entry it uses is the "animated tile" entry catalogued in
`systems/display-driver-abi.md` Section 10.

**The defining property, and the thing an implementation most needs to get
right: this pass rewrites the pixels of the loaded tile artwork in place.** It
does not write the visible screen and it does not write the back buffer. Every
consequence below follows from that one fact:

- **There is no per-instance phase and there cannot be one.** Every on-screen
  instance of a given tile changes identically and simultaneously, because they
  are all blits of the same bytes. Capture confirms this directly: five separate
  water regions across the visible map transitioned within 0.1–0.4 ms of one
  another, and forty-two sea tiles in a later capture were in exactly the same
  phase.
- **The change becomes visible the next time that tile is blitted, from any
  caller, in any view** — not at a composite step and not through a redraw of a
  particular cell.
- **The mutation persists.** It is not an overlay applied at draw time and
  undone afterwards. It survives scene changes, save loads, and everything else
  short of reloading the asset.
- **A renderer that implements only the frame-selector pass draws every tile in
  this section motionless.** That is the failure mode this section exists to
  prevent.

A modern engine will almost certainly prefer to keep pristine artwork and derive
each frame. That is a legitimate implementation choice for the rotation, whose
state is a single counter, and Section 12.4 states exactly where it stops being
legitimate.

One narrow exception to "writes only the tile asset": each rotation block parks
a handful of bytes in a scratch area inside the driver's own segment to carry
the wrapping row across the shift, and reads them back. The load-bearing
negative — nothing here writes the visible screen or the back buffer — is
unaffected.

### 12.2 The vertical rotation: open water, shoals and lava

For each of four tile ids the driver performs a **one-pixel-row vertical
rotation of the whole 16×16 tile** on every invocation. The bottom row is saved,
rows 0 through 14 move down into rows 1 through 15, and the saved bottom row is
written back as row 0. The image scrolls **downward** one pixel row per step and
wraps inside the tile; after sixteen invocations it is back where it started.

| Tile id | Shipped name |
|---|---|
| `0x01` | Deep water |
| `0x02` | Water |
| `0x03` | Shoals |
| `0x8F` | Molten lava |

Tile `0x00` is **not** in this set. Lava is not an analogue of the water
treatment — it is literally the same operation in the same pass, and an engine
should implement one rotation over the four ids rather than a water rule and a
lava rule.

Static analysis and black-box capture were performed independently and agree
exactly. The capture's model, over forty-two open-sea tiles and all sixteen
phases, is that phase *k* row *r* equals the source's row `(r - k) mod 16`; the
downward match held on 672 of 672 rows and the upward match on 0 of 672,
including row 0, which can only match by wrapping from row 15. An earlier
reading of the same capture as a one-pixel *horizontal* scroll was withdrawn by
its author and is wrong: a diagonal wave texture rolling vertically reads as
sideways motion to a row-wise correlator.

**The period is sixteen animator invocations**, and that is the figure to
implement and test against. On the idle path sixteen invocations are sixteen
timer ticks — the capture measured the full cycle at 878.6 ms, and it is exactly
sixteen ticks. The conversion is nevertheless an assumption rather than a
structural fact: every animator caller *that was traced* pays a one-tick wait
per frame, but the animation step also runs during command execution
(Section 13), and no census established that every world-tick call site is
tick-paced. Count invocations, not ticks, and the two agree wherever it has been
checked.

Coast and river appearances are the same rotated tiles seen through static
overlay pixels, not separate art: capture found diagonal coast tiles to be the
open-water tile plus a static land overlay on an exact 45° half-plane
(the three observed masks are `x <= y`, `x >= 15-y` and `x >= y`, each 136 water
pixels; the fourth diagonal is inferred by symmetry rather than observed).

### 12.3 The composites, and the rule that is *not* uniform

After the rotation, the driver stamps the **current frame of the shoals tile
`0x03`** into three further groups of tiles, so those animate in sympathy
without being rotated themselves. In each case the stencil is one colour plane
of a mask tile, broadcast to all planes.

> **The three groups do not all use the same rule.** One of them is composited
> through the **complement** of the mask the others use. An engine that applies a
> single uniform rule renders that group inside-out — water where the bank
> should be and bank where the water should be.

| Destination ids | What they are | Mask ids | Rule |
|---|---|---|---|
| `0x60..0x6F` | Fourteen "a river" and two "a bridge" | `0x70..0x7F` | `dest = (dest AND NOT mask) OR (source AND mask)` |
| `0x34..0x37` | Grass | `0xD0..0xD3` | `dest = (dest AND NOT mask) OR (source AND mask)` |
| `0xE4..0xE7` | Water | `0xD0..0xD3`, **inverted** | `dest = (dest AND mask) OR (source AND NOT mask)` |

The inversion is not a different mask asset. The driver flips the relevant plane
of `0xD0..0xD3` wholesale between the second and third composites and restores
it afterwards, so `0x34..0x37` and `0xE4..0xE7` are a complementary pair sharing
one wedge mask. The shipped artwork settles it: `0xD0` is a solid colour-15
upper-left triangle, `0x34` carries shoals pixels *inside* that triangle and
grass outside it, and `0xE4` carries solid colour 15 inside it and water
outside. The CGA, Hercules and Tandy drivers reproduce the same complementary
behaviour, the Tandy one by writing mask-or-source outright.

Two further points an implementation needs:

- **The source frame is not advanced between destinations.** Every destination
  in a single invocation receives the same water frame, so all sixteen
  river/bridge tiles match each other exactly. This is why the capture saw
  separate regions move in lockstep.
- **Under the inverted rule, the mask-covered wedge of `0xE4..0xE7` keeps that
  tile's own shipped pixels** — solid colour 15 — and this pass never rewrites
  it. Whether anything else overpaints that wedge before display was not traced.
  Do not assume it is decorative, and do not "fix" it.

**Scope.** This is the verified destination set: three groups. An interim answer
delivered on issue #179 additionally named "two gem ids" as destinations; the
verification pass's re-derivation does not carry them, so they are not published
here and must not be implemented. That interim answer also stated the
first rule for all three groups, which is the error this table corrects.

**A mask id is not automatically a private id, and two of these three runs are
ordinary drawable terrain.** `0x70..0x7F` are named "strange walls" in the
shipped description table — placeable, drawable tiles, and the
Sceptre-dissolvable barrier family of `catalogs/tile-catalog.md` — that the
driver *additionally* reuses as the river composite's stencil. `0xD0..0xD3` are
the same: all four are placed as arena terrain in the shipped dungeon-room
arena bank, and `0xD1` and `0xD2` are placed on both shipped Ararat pages of the
keep location file, where the two complementary wedges form the prow of the
wrecked ship. Both runs must stay in any enumeration of drawable tiles.

*Corrected:* an interim answer on issue #179 described `0x70..0x7F` as
engine-private mask assets, and a first revision of this paragraph replaced that
with a list of "genuinely engine-private" ids — `0x00`, `0xC0..0xC3`,
`0xCC..0xCF`, `0xD0..0xD3` and `0x100` — resting on their all carrying the
placeholder record `*`. Both are withdrawn (`RETRACTIONS.md` R303 and R314).
`0xD0..0xD3` are drawn; `0x100` carries the actor half's placeholder `x`, not
`*`; and the placeholder record is not evidence of privacy in either half, since
the telescope `0x59`, the sign and poster ids and the fountain band
`0xD8..0xDB` all carry `*` and are ordinary drawn artwork placed on shipped
maps. `formats/tiles.md` Section 6.2 carries the full accounting. The only ids
this section confirms as mask-only are `0xC0..0xC3` and `0xCC..0xCF`, and the
confirmation is their driver role first, corroborated by their absence from the
shipped map and arena census whose scope `formats/tiles.md` Section 6.2 states —
not by their description record.

### 12.4 The fire fixtures: cumulative masked-noise XOR

The same pass animates every fire fixture in the game, by a completely different
mechanism from the water rotation. **There is no frame set to enumerate.** Any
small-N frame-loop model is wrong: a capture of ~1,900 sampled updates produced
~1,900 distinct frames, and a separate 5,000-sample run produced 2,755 distinct
states.

The step has two parts. First the driver refreshes four actor-half "field"
tiles — atlas ids `0x1E8` (a poison field), `0x1E9` (a sleep field),
`0x1EA` and `0x1EB` (a force field) — with fresh pseudo-random pixel bits from a
generator the driver owns. These are the combat field-effect tiles, so those
fields are themselves re-randomised on every animation step. Then it uses one of
the refreshed tiles as a noise source and, for each fire fixture, over the whole
16×16 tile:

```text
fixture ^= (noise AND mask)
```

| Fixture id | Shipped name | Mask id | Noise source |
|---|---|---|---|
| `0xB0`, `0xB1` | A flickering torch | `0xC0`, `0xC1` | `0x1EA` |
| `0xB2` | A hot brazier | `0xC2` | `0x1EA` |
| `0xB3` | Meat roasting on a spit | `0xC3` | `0x1EA` |
| `0xBC` | A fireplace | `0xCC` | `0x1EA` |
| `0xBD` | A street lamp | `0xCD` | `0x1EA` |
| `0xBE` | A candelabrum | `0xCE` | `0x1EA` |
| `0xBF` | A hot stove | `0xCF` | `0x1EA` |
| `0xDE` | The shrine flame | `0xC2` | `0x1EB` |

Each mask is a small shape sitting exactly over its fixture's flame, so only
pixels inside the flame silhouette are ever touched. Capture agrees: the
brazier's animated region is 26 pixels of the tile's 256, confined to rows 2
through 6 at four to six pixels per row, and about 12.8 of those 26 pixels
change per update. Capture also confirms it is **not a roll of any kind** — the
best whole-tile circular shift between consecutive frames is the null shift with
a large residual, where water matches bit for bit.

> **This XOR is cumulative and is never undone.** After the first step the
> original artwork inside the masked region is gone. What renders from then on is
> the shipped art XORed with every noise pattern accumulated since the program
> started. An engine that re-derives each frame from pristine artwork is
> statistically equivalent and visually indistinguishable, but it is **not
> bit-identical** to the original. This is a real parity boundary: a pixel-parity
> test against the original will fail for reasons that have nothing to do with
> the test's subject. Reproduce the accumulation if bit parity matters; otherwise
> know why it does not hold.

**Which colour bits move — static derivation from shipped data, not observed.**
Treat any capture as authoritative over this paragraph. The generator writes the
same random byte into both of the two colour planes that noise tile `0x1EA`
occupies and leaves that tile's other two planes at zero, which is also their
shipped state. The net rule is that a masked pixel's colour is XORed with
`random_bit x (mask_pixel_colour AND 12)`, and for `0xDE` with its different
noise tile, `AND 9`. **On this derivation from the shipped mask and noise
artwork - a static reading of shipped data, not an observation - no fire fixture
flickers its blue or green bit; the claim holds only as far as that derivation
does, and a capture showing otherwise overrides it.** Per fixture: the torch
pair, the brazier, the stove and the shrine flame have single-colour masks that
admit only the brightness bit, so those flame pixels alternate between the dark and bright form of one colour (red / bright red,
brown / yellow); the street lamp's mask colour flips red and brightness
together; the spit and the fireplace have mixed-colour masks and flip red and/or
brightness per pixel. The candelabrum *looks* like a two-plane mask, but one of
its planes is a plane the noise tile never supplies, so it too flickers on the
brightness bit alone — **do not infer flicker breadth from a mask's colour
without intersecting it with the noise tile's planes.** Capture of a brazier
found six EGA colours in the animated region, dominated by red (36 %) and bright
red (33 %), consistent with this derivation.

### 12.5 The banner and sail row swap — *probable*

A further stage in the same driver pass **swaps row pairs within the banner and
sail tiles under per-bit pseudo-random gates**. The affected ids are `0x12`,
`0x14`, `0x15`, `0x3E` and four ship tiles — the keep, town and castle banners
and the ship sails. It is a third mechanism again, distinct from both the
rotation and the fire XOR, and distinct from the standard-of-Britannia family of
Section 6, which is a frame-selector family and is unrelated.

This stage is published at lower confidence than the rest of Section 12: it was
identified in the same re-derivation of the driver body but was not itself the
subject of a dedicated verification pass, and none of it was observed at
runtime. One detail is flagged as a probable defect of the original: the
trailing row-swap gate re-tests the **same** pseudo-random bit as the leading
gate rather than a distinct one. Whether that is intentional is unknown. An
implementation should reproduce the shared gate rather than "correct" it to two
independent draws, and should confirm the visual against a capture of a keep or
a ship under sail before pinning tests to it.

### 12.6 There is no palette animation

The EGA driver programs the palette exactly once, through the BIOS, when it sets
the video mode, and never touches the palette or colour-lookup hardware again.
The only hardware registers it writes while drawing are the plane-select and
graphics-controller registers used for ordinary blitting. **No effect in this
document is a palette rotation**, and an implementation must not reach for one.

*Scope of that negative.* It was established by scanning the EGA driver for
immediate port addresses in the video range and for every BIOS video call, so it
would not catch a port address computed at run time, and it says nothing about
the CGA, Hercules and Tandy drivers, which were not examined for palette
handling at all. `formats/tiles.md` Section 10 records the same result from the
asset side.

### 12.7 What still needs a capture

- **No wall-clock rate for this pass was derived statically.** The step count is
  sixteen invocations for the rotation and unbounded for the fire XOR. The
  measured 54.9 ms per step on the idle path (Section 2) is the engine team's
  measurement and is authoritative over anything derived here.
- The colour-bit characterisation of Section 12.4 and the scroll direction and
  period of Section 12.2 are byte-movement and shipped-artwork derivations. The
  scroll and the period have since been confirmed by capture; the colour-bit
  breakdown has not.
- Section 12.5 in its entirety.
- Whether any resident-side code writes into the tile-asset buffer directly. The
  buffer is allocated by the resident engine and handed to the driver, so it can
  be addressed from outside; no such write was found on any traced path, but the
  search covered driver dispatch sites, the selector table and the traced tick
  path rather than arbitrary writes into that segment.

## 13. When An Animation Step Runs

Section 2 gives the cadence of the ordinary idle path. This section gives the
complete set of paths that run an animation step at all, and the gates on each,
because the issue that produced this text arrived with the reasonable but wrong
assumption that the animator is stepped once per idle redraw and nowhere else.

Both the frame-selector pass of Section 6 and the driver-side pass of Section 12
run as the unconditional tail of the **active-object animation step** of Section
4. They share its gating exactly; neither has a gate of its own. That step has
**three** callers:

1. **The world tick.** The call sits behind a master redraw/animation gate and a
   mode-handshake byte that must be in neither of its two skip states. The world
   tick is itself invoked from far more than the idle loop: a near-call census
   finds seven distinct sites in the resident image and sixty-one across sixteen
   of the twenty-three code overlays, and one resident site calls it repeatedly
   in succession, with a one-timer-tick wait between calls; the repeat count at
   that site was not established, and no number for it is published here. The
   number of animator advances therefore tracks world-tick invocations, not idle
   redraws.
2. **The Return-to-View preview tick**, which calls it **unconditionally** as its
   first action, once per preview frame.
3. **The spell/potion visibility sweep** — the White-potion / expanding-flash
   visual — which calls it **once per rendered frame for twenty consecutive
   frames** inside the execution of a single command, with none of the
   world-tick gating of caller 1. Each of those twenty frames pays its own
   one-tick wait, so the sweep is not faster than the timer rate; what it breaks
   is the assumption that an animator advance implies an *idle* pass. Twenty
   steps of water roll and fire flicker occur while a command is executing. The
   sweep does carry the Negate Time test (Section 13.1).

*Scope.* That caller enumeration is a near-call and near-jump census over the
resident image and all twenty-three overlays, each rebased through the shipped
overlay-descriptor load bases. It cannot see a far call or an indirect call
through a run-time function-pointer table. None was observed at any site read.

### 13.1 Two freezes an implementation must reproduce

- **Negate Time freezes all of it.** While that timed effect is active, the world
  tick forces the gating byte into a skip state on *every* call, and the
  spell-effect sweep carries the same test. For the effect's full duration
  nothing advances: no water rotation, no fire flicker, no fountain, no banner,
  no clock or bellows, no object animation, no AI roll, no wind check, no
  moongate refresh, no beacon step, and no shrine/lava ambience tick. The
  Return-to-View path carries no such test. An engine that keeps animating
  during Negate Time is visibly wrong. *The identification of the effect code as
  Negate Time rests on this repository's separate state map rather than on the
  trace that established the gating; the gating itself is established.*
- **A clear master redraw gate stops it too.** When that gate is clear the world
  tick returns early and nothing advances, while the idle loop's timer wait still
  runs — so the loop keeps pacing at one tick per pass and performs no world work
  at all. *Two writers of that gate were found, both setting it (one on outdoor
  scene entry, one on town entry), and the shipped data image has it clear. The
  scan covered direct-address stores only, so "nothing ever clears it during a
  world scene" is an observation, not an invariant.*

### 13.2 What one world step advances

When both gates allow it, one world step advances each of the following exactly
once:

- every active on-screen object's animation phase, with the turn-or-move AI
  decision taken behind a random gate when a phase reaches zero;
- one wind-change check — a single **1-in-64** check, not a drift step. When it
  fires a new prevailing direction is drawn, with "calm" accepted only behind a
  further roughly 1-in-4 confirmation, so a fired event always installs some
  direction. The observed rate of an actual wind change is therefore about one
  per sixty-four qualifying passes;
- outside combat only, the saved-moongate terrain refresh and the rotating
  light-beacon step;
- the tail pair of Sections 6 and 12;
- a shrine and lava ambience tick.

The viewport rebuild and redraw run whenever the master redraw gate is set,
regardless of the second gate.

Beyond the two states already described, the gating byte has a third: a sentinel
that suppresses **object animation and the tile passes alone**, leaving the rest
of the step intact. It is written at exactly one place in the whole build — at
entry to the command wait, and **only when the display adapter is Tandy
16-colour**. On CGA, EGA and Hercules that state never occurs. On Tandy it
recurs at every entry to the command wait, which is once per command prompt
rather than once per mode entry, so on that adapter alone the first idle pass of
every command wait skips tile and object animation. The shipped initial value of
the byte is the freeze state, so **the very first world step of a session is a
bare repaint**.

### 13.3 Relative rates within the frame-selector pass

Per invocation of the frame-selector pass: the waterfall and fountain families
advance one frame every call; the `0x80..0x83` pairs and the standard of
Britannia advance on every second call; the clock and bellows pairs toggle on
every fourth call. **These are ratios between families, not absolute rates.**
The pass is reached only from the tail of the object-animation step, so it
inherits every suppression above, and "every call" does not mean "every idle
pass". An implementation that advances all animated families at the same rate is
visibly wrong.

### 13.4 What is *not* on this path

The game clock and the NPC schedule walk are not part of the idle pass at all.
They advance in the per-turn epilogue after a command has been executed
(`systems/time.md`, `systems/npc-schedules.md`). Capture confirms the visible
consequence: over 160 s of idle with no input, date, food, gold, sun and party
status never changed, and town NPCs animated in place without ever stepping.
Town NPC wander was measured at about one step per 2.6 passed turns and exactly
zero steps per second of wall clock while idle — **express wander per game turn,
never per tick.**

The text cursor is also outside the world step: it advances on every pass of the
cursor-poll helper regardless of the gating above, because it lives one level
above it. It is a four-frame animation rather than a two-state blink — capture
measured exactly four phases in strict order, one phase per tick, a 219.7 ms
cycle — and `systems/text-output.md` owns it.

Two NPC-side cadences were measured and are recorded here because they are
neither of the rates above and this document should not be read as covering
them: a pair of stationary castle guards each advanced one frame per **eight**
ticks (7.95 and 8.01 measured) and were demonstrably *not* in phase with each
other, while a mobile jester and an overworld creature both showed an irregular
dwell with a mean of about 2.7 ticks and a long decaying tail — the signature of
a per-pass random gate. Both are consistent with the per-slot countdown model of
Section 3 (a seeded countdown gives the guards' clean period; a random movement
gate gives the decaying tail), but neither has been reconciled against the
class-attribute tables, and the per-actor phase offset confirms these are
per-slot counters rather than anything global.

## 14. Sources

This spec is a cleanroom rewrite derived from the following analysis notes and
public-bound specs. It intentionally omits private addresses, assembly,
decompiler output, implementation listings, and raw private tables.

- Active-object record shape, persistence, renderer order, and system
  interactions - `systems/active-objects.md`.
- Input idle-loop relationship to world ticks - `systems/input.md`.
- Time-system separation and per-turn cleanup cadence - `systems/time.md`.
- Per-slot animator, global tile selector update, and display-driver flush -
  `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: the five global tile-animation families of Section 6, their
  cycle lengths and phase gating, and their per-id selector bytes were re-read
  from the shipped executable for this revision; their names come from decoding
  the shipped description table (`u5-spec/formats/look2-dat.md`). Both private
  notes above still carry the older water/lava/torch labels for those ranges,
  and the tile-animator note additionally lists `0xEC..0xEF` as a plain
  four-frame cycle with no gate; those labels and that cadence were guesses,
  and both are superseded by the nested two-gate structure re-read from the
  shipped executable for this revision.
- Caller relationship from the resident world-tick path -
  `u5-decomp/functions/ULTIMA_EXE/`.
- NPC scheduler separation -
  `u5-decomp/functions/NPC_OVL/`.
- Combat save/restore interaction -
  `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/functions/COMBAT_OVL/`.
- `FLAMES.OVL` non-animation role and title-effect ownership -
  `u5-decomp/functions/FLAMES_OVL/`.
- Source provenance: the boundary between this document's frame-selector layer
  and the moongate presence phase - that the phase is not a tile-animation
  family, is not advanced by the animation tick, and is not per-frame - is
  derived from private analysis in `u5-decomp/notes/`. The withdrawn "no frame
  cycle of its own" wording in Section 8 is superseded by the same analysis.
- Source provenance: Section 12 in full - the driver-side tile-asset pass, the
  four rotated ids, the three composite groups and the mask inversion between
  them, the fire fixtures with their mask and noise pairings, the cumulative
  XOR, the colour-plane restriction, and the "no palette rotation" negative -
  is a cleanroom rewrite of a private re-derivation of the shipped EGA display
  driver's animated-tile entry, performed three times independently, with the
  tile identities decoded from the shipped description table, the mask and noise
  artwork rendered from the decompressed shipped tile file, and the tile-id
  arithmetic cross-checked against the CGA, Hercules and Tandy drivers, which
  use a different stride and reach the same ids. Private analysis under
  `u5-decomp/functions/EGA_DRV/` and `u5-decomp/notes/`. No decompiled output,
  driver slot numbers or addresses are reproduced here.
- Source provenance: Section 6.1 through 6.3 and Section 13 - the completeness
  of the five-window list, the identity-initialised selector table, the
  behavioural equivalence of the two clock phases, the placement census, the
  three callers of the animation step, the Negate Time and master-gate freezes,
  the Tandy-only sentinel, and the per-family rate ratios - are cleanroom
  rewrites of private analysis under `u5-decomp/functions/ULTIMA_EXE/`, repaired
  after an adversarial verification pass whose corrections are carried into the
  prose above rather than dropped.
- The wall-clock master cadence of 54.913 ms, the fountain's confirmed ungated
  four-phase cycle, the sixteen-phase downward water roll and its in-tile wrap,
  the fire fixtures' per-tick per-pixel re-randomisation and mask extent, the
  four-phase text cursor, the guard and jester NPC cadences, and the "no world
  advance while idle" result are **black-box runtime measurements contributed by
  the clean implementation side** on issue #179, not static derivations. Where
  this document's figures and those measurements meet, the measurements are
  authoritative.
