# Vehicles And Ship Fire

## 1. Overview

Vehicles are the bridge between the active-object layer, movement rules, time
costs, and several letter commands. A horse, skiff, ship, or carpet can exist
as an active object on the map; boarding it moves the party into a transport
state; exiting it writes a stand-in object back to the map so the vehicle can be
boarded again later.

This spec centralizes the visible vehicle contract for v1. It covers B-Board,
X-Xit dismount, movement/time hooks, Y-Yell sail toggling, persistent vehicle
object state, and the F-Fire cannon paths. The exact per-tile passability table
and the exact numeric transport-marker table remain open where the private
notes have not yet been promoted to a public table.

## 2. Vehicle State

Vehicle state is stored in three cooperating places:

- **Party transport state.** The player record carries the current
  avatar/vehicle sprite or transport marker. Movement, firing, rendering, and
  dismount all read this state to decide what the party is currently using.
- **Active-object record.** A parked vehicle is an ordinary active-object slot
  with a vehicle-class tile, coordinates, floor/plane marker, and auxiliary
  bytes. For ships, two auxiliary bytes carry hull condition and skiff count.
- **Timing/state tag.** The per-turn cleanup reads a nearby single-character
  state tag for the `Q` half-time and `T` no-minute cases. That tag is not the
  full vehicle identity and should not be used as the vehicle table.
- **Save and object-overlay files.** The live active-object table is persisted
  in `SAVED.GAM` for the current scene. The overworld plane object tables live
  in the `.OOL` companion files. See `formats/saved-gam.md` and
  `formats/ool.md`.

The public contracts should treat the active-object record as authoritative for
parked vehicles and the party transport state as authoritative while the party
is mounted or aboard. Boarding copies any needed object auxiliary state into the
party's active vehicle state; exiting should copy it back into the parked object
that remains on the map.

The complete byte-compatible marker table is not yet public, but the command
and mode traces prove these transport-marker families:

| Family | Public marker contract |
|--------|------------------------|
| Foot/avatar | Clean seed and default state. On-foot boarding preconditions accept the avatar/foot pair, and no parked vehicle state is implied. |
| Mounted horse | B-Board derives the mounted marker from the two horse object frames. Some outdoor actor passes treat the horse family as an alternate-turn state; the exact speed and rough-terrain table remains open. |
| Magic carpet | B-Board writes the carpet marker. The current traces do not prove that the `T` timing tag means carpet, so carpet identity must come from the transport marker, not from the timing tag alone. |
| Ship | Shipboard commands accept a multi-marker family. Boarding copies the selected ship object's facing into the active marker; Y-Yell toggles the semantic sail state; broadside fire uses the ship facing to reject bow and stern shots. Exact compass, facing, and hoisted/furled numeric mapping remain open. |
| Skiff | B-Board derives the mounted marker from the skiff object frame by applying a mounted-state adjustment. Slow-water timing is represented separately by the `Q` timing/status tag. Exact water-terrain rules remain open. |
| Balloon | The vehicle tile family is cataloged, but no promoted B-Board or transport-marker write path is public yet. |

Implementations that do not need byte-identical save editing can model these as
semantic transport families, with facing and sail state carried separately. A
byte-compatible reader or writer should keep unknown marker values intact until
the exact numeric table is promoted.

## 3. Vehicle Families

| Vehicle | Confirmed command role | Known state/effect | Remaining gaps |
|---------|------------------------|--------------------|----------------|
| Foot | Default state. | No vehicle object; normal terrain restrictions. | None at this level. |
| Horse | Boardable. X-Xit can leave a horse object behind. | Overland transport; requires the party to be on foot before boarding. | Full stride and rough-terrain speed table. |
| Ship | Boardable; can fire broadsides; can toggle sails through Y-Yell. | Carries hull condition, skiff count, heading, and sail state. Shipwright Frigate purchase creates this family with full hull and two skiffs; boarding warns when badly damaged or out of skiffs. | Repair, exact numeric marker/facing/hoist mapping, and compass naming. |
| Skiff | Boardable. | Water transport; time cleanup halves non-zero turn increments with a one-minute floor. | Exact shallow/deep water allowance table and numeric marker subrange. |
| Magic carpet | Boardable as a carpet. | Boarding changes the party transport state to the carpet transport marker. The B-Board trace does not prove the `T` timing tag is carpet, and the outdoor Klimb gear gate is unresolved and should not be assumed to be this vehicle. | Exact numeric marker variant and terrain exceptions. |
| Balloon | Vehicle tile family. | Aerial transport by manual/tile evidence. | Boarding/acquisition path, transport marker, and movement rules are not traced here. |

## 4. B-Board

B-Board reads the vehicle or object under the party and tries to move the party
into it.

The handler refuses immediately in the stock dungeon scene range with the stock
"Not here!" message. In other scenes it probes the current position for a
boardable vehicle-class object and branches by vehicle family:

The promoted boardable families are semantic, not a raw tile-ID table:

| Object family | Boardable shape |
|---------------|-----------------|
| Horse | Two horse object frames. Boarding requires the party to be on foot and converts the object frame to the corresponding mounted-horse marker. |
| Magic carpet | A single carpet object frame. Boarding requires the party to be on foot and writes the carpet transport marker. |
| Skiff | A compact skiff-facing run. Boarding requires the party to be on foot and converts the object frame to a mounted skiff marker. |
| Ship | A compact ship-facing run. Boarding preserves the selected ship's facing and copies its auxiliary hull/skiff state. The broader shipboard command family includes active ship states that are not necessarily parked boardable ship objects. |

- **Horse.** Requires the party to be on foot. In non-overworld scenes an
  additional availability check can refuse with "Nay!" when the horse/object is
  occupied or unavailable. On success it prints the horse line and changes the
  party transport state to mounted horse.
- **Carpet.** Requires the party to be on foot. On success it prints the carpet
  line and changes the party transport state to carpet.
- **Skiff.** Requires the party to be on foot. On success it prints the skiff
  line and changes the party transport state to skiff.
- **Ship.** Uses a broader boarding precondition than the on-foot-only cases.
  The gate accepts the ordinary foot/avatar state and selected already-mounted
  or waterborne transport states; if the current state is outside that accepted
  set it prints the stock "On foot" refusal and makes no state change. On
  success it prints the ship line, copies the selected ship object's hull
  condition and skiff count into the active vehicle state, warns if the ship is
  badly damaged, warns if no skiffs are aboard, and changes the party transport
  state to ship.

Successful boarding then runs the shared object-update helper for the boarded
slot, marks map/object state dirty, and returns as a consumed command. Refusals
inside a boardable family, such as "Nay!" or "On foot", are also handled command
outcomes. If the current object is not a boardable vehicle, B-Board prints the
stock "What?" refusal, does not board anything, and returns as the command's
ordinary no-action fallthrough rather than as a vehicle interaction.

The B-Board trace documents boarding semantics only. Horse-trader purchase is a
Talk-entered shop helper that pays for and places a boardable horse object; after
that, B-Board treats the horse like any other boardable object. Ship-broker
purchase is also Talk-entered: payment queues an overworld acquisition, and the
next overworld entry places either a Frigate as a ship-family object or a
standalone skiff-family object at the stored sale coordinates. A purchased
Frigate starts with full hull condition and two skiffs aboard; buying a Skiff
while that Frigate is still queued increments its carried-skiff count and does
not place a second object. Buying a second standalone Skiff before delivery is
refused by the shipwright flow. Ordinary B-Board then owns boarding the placed
object.

## 5. X-Xit

X-Xit is the inverse of boarding for mounted or shipboard travel. When the
party is already on foot, X-Xit reports that there is nothing to exit. When the
current vehicle cannot be left at the current location, it refuses with the
appropriate location-specific line, including no-land-nearby and under-sail
cases.

On a successful dismount, X-Xit:

1. Finds a valid adjacent or nearby landing cell for the party.
2. Spawns or restores an active-object slot for the abandoned vehicle.
3. Copies vehicle-specific auxiliary state, such as ship hull condition and
   skiff count, into that parked object.
4. Clears the party transport state back to foot/avatar.
5. Prints the vehicle-specific success line.

The exact landing-cell search radius and full terrain predicate are not yet
publicly pinned down. For v1, preserve the observable requirements: exiting can
fail when no legal landing exists, and a vehicle left behind must remain
boardable through the active-object/object-overlay persistence path.

## 6. Movement And Time Hooks

Vehicle movement is still mode-owned. The overworld and town movement handlers
own directional stepping, collision, boundary checks, and tile effects. The
vehicle system contributes the current transport state and a few modifiers:

- Foot and ships use the normal minute increment supplied by the active mode.
- Horses alter movement distance/stride in outdoor travel, but do not change
  the time cleanup's minute increment directly.
- Skiff/raft-like water travel is associated with the time cleanup's `Q` tag,
  which halves non-zero time increments and floors the result at one minute.
- A separate `T` timing/state tag suppresses minute and light-counter
  advancement in the time cleanup, but it is not currently identified as a
  boarded vehicle family.
- Vehicle state participates in encounter checks and in-water handling.

Tile passability is a layered decision: the base tile passability bitmap is
checked first, then vehicle-specific terrain rules are applied. The tile catalog
records the high-level roles; exact parity needs the movement-handler tables.

### Ship Sails

Y-Yell is the ship sail command when the party is aboard a ship. The vehicle
branch toggles between two visible modes:

- **Sails hoisted.** The ship is under wind control. Movement is resolved later
  by the overworld movement loop using the wind/heading cadence described in
  `systems/weather.md`.
- **Sails furled.** The ship is manually handled. Wind-driven drift should not
  advance the ship while furled.

Toggling sail state updates the party's ship state but does not directly move
the ship. X-Xit should refuse the under-sail case while the ship is in the
hoisted/wind-control state. The exact byte or bit pattern that combines ship
heading with hoisted/furled state remains part of the numeric transport-marker
mapping gap; v1 implementations should model heading and sail state
semantically.

Y-Yell's word-of-power and Shadowlord-name branches are command-system
features, not vehicle behavior.

## 7. F-Fire In The Overworld

In overworld scene zero, public F-Fire delegates to the ship-broadside helper.
That helper is ship-only:

1. If the party is not aboard a ship, it prints the stock "What?" refusal.
2. It runs the shared pre-action gate; a failed gate aborts without the shot.
3. It compares the requested firing direction with the ship's facing. Bow or
   stern shots refuse with "Fire broadsides only!".
4. A legal broadside traces a short line, up to three cells, from the ship in
   the chosen direction.
5. If the shot hits a target object, it animates the impact and subtracts a
   random damage amount from the target object's condition/durability byte. A
   destroyed or underflowed object is handed to the shared object-update helper
   and object state is marked dirty.
6. If no target is found in range, the projectile is still animated to the
   endpoint.

The helper does not enter combat by itself. It mutates world object state and
returns to the overworld loop.

## 8. F-Fire In Town-Family Scenes

Outside the overworld and dungeon ranges, F-Fire uses a local cannon/fire-source
path rather than the ship-broadside helper.

The handler first runs the door auto-close pass, then searches the cells around
the party for an adjacent fire-source or cannon-facing tile. If none is found,
it prints "What?". If a source is found, its orientation determines the firing
direction, the handler prints the blast line, animates the shot, and scans a
short fixed line for the first blocking target.

Two target classes have visible side effects:

- **Door-like targets.** The handler prints "Door destroyed!", rewrites the live
  map cell to the open/rubble tile, marks the map dirty, and clears the current
  door auto-close tracker. This is a visit-local tile-buffer rewrite unless a
  separate persistent object path records it.
- **Active objects.** The handler records the hit object slot, runs the shared
  object-update chain, applies the associated damage/state decrement, and marks
  object state dirty.

Dungeon scenes in the stock dungeon range refuse F-Fire with "What?". Combat
has its own command parser and does not inherit this resident F-Fire route.

## 9. Persistence

Vehicles persist through the active-object and object-overlay systems, not
through static map files.

- Parked vehicles are active-object records.
- Boarding removes or updates the parked object and moves its relevant state
  into the party transport state.
- Exiting creates or restores a parked object at a legal map position.
- Saving writes the active object table for the current scene and writes the
  overworld plane object tables through `SAVED.OOL` and the per-plane mirrors.
- Loading restores those records byte-for-byte before the relevant mode entry
  code resumes play.

Static map files such as `BRIT.DAT`, `UNDER.DAT`, and location `.DAT` files are
not rewritten when vehicles move.

## 10. Hooks Into Other Systems

- **Commands.** `commands.md` owns dispatcher routing for B, F, X, and Y. This
  spec owns the vehicle behaviour behind B, F, X, and the ship-sail branch of
  Y.
- **Overworld.** `overworld.md` owns the outdoor movement loop, encounter
  checks, and plane object setup that consume vehicle state.
- **Weather.** `weather.md` owns the prevailing wind state, wind display, and
  wind/heading cadence used when ship sails are hoisted.
- **Doors and Z transitions.** `doors-and-z-transitions.md` cross-references
  X-Xit near the spell-context dungeon escape helper and documents door
  destruction as a door-system side effect.
- **Time.** `time.md` owns the `Q` and `T` state-tag modifiers that alter the
  minute increment; this spec owns the boarded vehicle families.
- **Active objects.** `active-objects.md` owns the slot record, allocator,
  renderer relationship, and combat backup/restore behaviour.
- **Save/load and OOL.** `save-load.md`, `formats/saved-gam.md`, and
  `formats/ool.md` own persistence of active-object vehicle records.
- **Items.** `catalogs/item-list.md` names vehicle inventory/acquisition
  families. Purchase prices and brokers live with shops.

## 11. Open Questions

- **Transport marker numeric table.** The public specs now identify the known
  transport-marker families semantically, but the exact numeric subranges and
  variant meanings still need a promoted table. For ships, this includes the
  exact facing and hoisted/furled encoding. For balloons, the boarding/write
  path is still not public. Keep this separate from the `Q`/`T` timing tag byte
  used by `time.md`.
- **Boarding tile ID verification.** The B-Board handler's semantic vehicle
  families are now public, but the exact sprite IDs and variant meanings within
  each family still need tile-catalog verification.
- **Ship boarding precondition variants.** Ship boarding accepts a broader set
  of starting states than horse/carpet/skiff boarding, and the refusal text is
  public. The exact numeric marker variants inside that accepted set still need
  to be reconciled with the transport-marker table.
- **X-Xit landing search.** The legal landing scan and terrain predicate are
  observed by behaviour but not yet pinned down as a public algorithm.
- **Ship durability semantics.** The auxiliary byte decremented by broadside
  fire is clearly target condition-like, but whether every target interprets it
  as hull HP, object HP, or a mixed durability byte remains open.
- **Balloon mechanics.** Balloon sprites and manual behaviour are cataloged,
  but the command path for boarding, landing, and wind-driven movement needs a
  focused pass.

## 12. Sources

This cleanroom spec was derived from private analysis notes and sibling public
specs. It intentionally does not reproduce decompiled code, assembly, raw data
tables, or implementation-specific addresses.

- `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`.
- `u5-decomp/functions/CMDS_OVL/0x0962_cmds_fire_broadsides.md`.
- `u5-decomp/functions/CMDS_OVL/0x0AEA_cmds_fire.md`.
- `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- Local SHOPPES2 shipwright control-flow analysis and direct `SHOPPE.DAT`
  record inspection.
- `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- Local MAINOUT outer-loop analysis for pending shipwright delivery placement.
- `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- `u5-decomp/formats/ds-bss-map.md`.
- `u5-decomp/formats/saves.md`.
- `systems/overworld.md`.
- `systems/doors-and-z-transitions.md`.
- `systems/time.md`.
- `systems/weather.md`.
- `systems/active-objects.md`.
- `formats/ool.md`.
- `catalogs/item-list.md`.
- `catalogs/tile-catalog.md`.
