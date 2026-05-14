# Vehicles And Ship Fire

## 1. Overview

Vehicles are the bridge between the active-object layer, movement rules, time
costs, and several letter commands. A horse, skiff, ship, or carpet can exist
as an active object on the map; boarding it moves the party into a transport
state; exiting it writes a stand-in object back to the map so the vehicle can be
boarded again later.

This spec centralizes the visible vehicle contract for v1. It covers B-Board,
X-Xit dismount, movement/time hooks, Y-Yell sail toggling, persistent vehicle
object state, the known transport-marker ranges, and the F-Fire cannon paths.
The shared terrain-query and movement commit layer are specified in
`systems/movement.md`; vehicle-specific movement cadence and terrain
exceptions are called out here where they affect visible command behavior.

## 2. Vehicle State

Vehicle state is stored in three cooperating places:

- **Party transport state.** The player record carries the current
  avatar/vehicle sprite or transport marker. Movement, firing, rendering, and
  dismount all read this state to decide what the party is currently using.
- **Active-object record.** A parked vehicle is an ordinary active-object slot
  with a vehicle-class tile, coordinates, floor/plane marker, and auxiliary
  bytes. For ships, byte `+5` is hull condition and byte `+7` is skiffs
  aboard.
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

The known byte-compatible transport/action marker ranges are:

| Values | Family | Facing / mode contract |
|--------|--------|------------------------|
| `0x10..0x13` | Mounted horse | Low two bits give facing: `0` north, `1` east, `2` south, `3` west. Ordinary terrain queries use the horse predicate family in `systems/movement.md`. A mounted directional command is still a single destination-cell step; no separate player rough-terrain stride table is part of the traced baseline. |
| `0x14..0x17` | Magic carpet | Low two bits give facing. Ordinary terrain queries use the carpet predicate family in `systems/movement.md`. The current traces do not prove that the `T` timing tag means carpet, so carpet identity must come from this transport marker, not from the timing tag alone. |
| `0x1C..0x1F` | Foot/avatar | Low two bits give the party leader facing. Clean seed/default state is `0x1C`, facing north. No parked vehicle state is implied. |
| `0x20..0x23` | Ship under sail | Low two bits give ship facing. The ship is in the hoisted-sail, wind-controlled state. Ordinary terrain queries use the ship predicate family in `systems/movement.md`. |
| `0x24..0x27` | Ship furled / manually handled | Low two bits give ship facing. The ship is aboard but not under wind control. Ordinary terrain queries use the same ship predicate family as the under-sail range. |
| `0x28..0x2B` | Skiff | Low two bits give skiff facing. Ordinary terrain queries use the facing-sensitive skiff/water predicate family in `systems/movement.md`. Slow-water timing is represented separately by the `Q` timing/status tag. |

Values outside the known ranges above should remain opaque in byte-compatible
save tools until their consumers are documented. They are not a public balloon
range in the analyzed baseline. Implementations that do not need byte-identical
save editing can model the known transport families semantically, with facing
and sail state carried separately. The stats panel's ship-hull middle counter
is selected only by the `0x20..0x27` ship family; out-of-range marker values
remain opaque transport state rather than alternate hull-display selectors.

The overworld active-object and encounter epilogue has a separate
alternate-turn pendulum for the traced marker pairs `0x12`/`0x13` and
`0x14`/`0x15`. Treat this as actor/encounter cadence evidence only: it does not
change the clock increment and it is not a player movement-speed table.

## 3. Vehicle Families

| Vehicle | Confirmed command role | Known state/effect | Remaining gaps |
|---------|------------------------|--------------------|----------------|
| Foot | Default state. | No vehicle object; normal terrain restrictions. | None at this level. |
| Horse | Boardable. X-Xit can leave a horse object behind. | Overland transport; requires the party to be on foot before boarding. Directional movement uses the ordinary one-cell overland step with mounted-horse passability. | None at this level. |
| Ship | Boardable; can fire broadsides; can toggle sails through Y-Yell. | Carries hull condition in active-object byte `+5`, skiff count in byte `+7`, plus heading and sail state in the party transport marker while boarded. Shipwright Frigate purchase creates this family with full hull and two skiffs; boarding warns when hull is below ten or no skiffs are aboard. Boarding from the accepted carpet-compatible states stows one carried carpet for later ship exit fallback. Hoisted-sail movement is wind-cadenced as specified in `weather.md`. | No command-level repair path is traced for the analyzed baseline; future repair evidence would belong to shop/item acquisition work, not B-Board, X-Xit, Y-Yell, or F-Fire transitions. |
| Skiff | Boardable. | Water transport; time cleanup halves non-zero turn increments with a one-minute floor. The shared movement spec names the facing-sensitive skiff predicate family. | None at this level. |
| Magic carpet | Boardable as a carpet. | Boarding changes the party transport state to the carpet transport marker. The B-Board trace does not prove the `T` timing tag is carpet; outdoor Klimb is a separate Grapple-gated command, not a carpet ownership test. The shared movement spec names the carpet predicate family. | None at this level. |
| Balloon | Vehicle tile family only in the analyzed baseline. | Balloon art and manual-facing references can be preserved as assets, but no traced B-Board, X-Xit, U-Use, shipwright, or ordinary movement branch promotes a live balloon transport state. | No command-level balloon mechanics are specified for v1; do not infer a boardable vehicle from art alone. |

## 4. B-Board

B-Board reads the vehicle or object under the party and tries to move the party
into it.

The handler refuses immediately in the stock dungeon scene range with the stock
"Not here!" message. In other scenes it probes the current position for a
boardable vehicle-class object and branches by vehicle family:

The promoted boardable families are semantic, but their parked-object to
boarded-state transitions are byte-compatible:

| Object family | Boardable object bytes | Boarded transport result |
|---------------|------------------------|--------------------------|
| Horse | `0x10..0x11` | Requires the party to be on foot; writes the corresponding mounted-horse marker by adding two to the object byte, producing `0x12..0x13`. |
| Magic carpet | `0x1B` | Requires the party to be on foot; writes carpet transport marker `0x14`. |
| Ship | `0x24..0x27` | Accepts the ship-boarding precondition below; preserves the selected ship byte as the party ship marker and copies hull/skiff auxiliary state. |
| Skiff | `0x28..0x2B` | Requires the party to be on foot; preserves the selected skiff byte as the party skiff marker. |

These bytes are vehicle object and transport-state values, not tile-sheet art
indices. Visual tile IDs and sprite-sheet placement remain catalog-owned.
No balloon object byte is accepted by the traced B-Board handler; balloon art
or manual references are not boardable command behavior in the analyzed
baseline.

- **Horse.** Requires the party to be on foot. In non-overworld scenes an
  additional availability check can refuse with "Nay!" when the horse/object is
  occupied or unavailable. On success it prints the horse line and changes the
  party transport state to mounted horse.
- **Carpet.** Requires the party to be on foot. On success it prints the carpet
  line and changes the party transport state to carpet.
- **Skiff.** Requires the party to be on foot. On success it prints the skiff
  line and changes the party transport state to the selected skiff byte,
  preserving facing.
- **Ship.** Uses a broader boarding precondition than the on-foot-only cases.
  The gate accepts the ordinary foot/avatar family, carpet-compatible markers
  `0x14` and `0x15`, and the skiff family; if the current state is outside
  that accepted set it prints the stock "On foot" refusal and makes no state
  change.
  On success it prints the ship line, copies the selected ship object's byte
  `+5` hull condition and byte `+7` skiff count into the active vehicle state,
  warns if hull condition is below ten, warns if no skiffs are aboard, and
  changes the party transport state to ship. When the accepted starting state
  is one of the carpet-compatible values, boarding also increments the
  carried/stowed carpet counter so X-Xit can redeploy that carpet if the ship
  later has no nearby landing support and no skiffs aboard.

Under the transport-marker facing convention in Section 2, the two accepted
carpet-compatible values are the north/east carpet markers. The south/west
carpet markers remain ordinary carpet transport values for movement and X-Xit,
but they are outside this ship-boarding precondition and receive the same
refusal as any other non-accepted starting state.

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
Magic Carpet can also be activated through U-Use: outside dungeon/combat scenes,
when the party is on foot and the current tile accepts it, the item-use handler
changes the party transport marker to a carpet state and decrements the carried
carpet counter. That U-Use path is inventory-owned; B-Board remains the command
for boarding a carpet object already present on the map.

Frigate starts with hull condition `100` and two skiffs aboard; buying a Skiff
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

X-Xit validates the surroundings but does not relocate the party to a different
cell. A successful dismount parks the abandoned vehicle at the party's current
coordinate through the active-object/object-overlay path, copies vehicle
auxiliary state such as ship hull condition and carried-skiff count into that
parked object, and changes only the party's transport marker.

The vehicle families behave as follows:

- **Horse.** X-it succeeds unconditionally for the mounted-horse family. It
  parks the riderless horse object at the current coordinate and returns the
  party to foot travel.
- **Magic carpet.** X-it requires either a passable tile under the party or at
  least one nearby landing-support cell. If neither is true, it refuses as
  no-land-nearby. On success it parks a carpet object and returns the party to
  foot travel.
- **Skiff.** X-it requires at least one nearby landing-support cell and also
  rejects the deep-water tile family directly under the skiff. On success it
  parks the skiff object, preserving its facing, and returns the party to foot
  travel.
- **Ship with sails hoisted.** X-it refuses while the ship is in the
  wind-control sail range. The player must furl sails first.
- **Ship with sails furled.** X-it first parks the ship hull at the current
  coordinate. If nearby landing support exists, the party leaves on foot and
  the parked ship keeps its carried-skiff count. If no landing support exists
  but the ship has a carried skiff, the party launches into a skiff facing the
  same direction and the parked ship's carried-skiff count is decremented. If
  no support and no skiff are available but a stowed carpet is available, the
  party redeploys that carpet and the stowed-carpet count is decremented. This
  is the counterpart to the ship-boarding path that records a carpet-compatible
  starting state. If none of those exits is possible, X-it refuses with the
  no-skiffs-on-board result and does not park a new object.

The full terrain predicate for passable neighbours is shared with
`systems/movement.md`. For v1, preserve the observable requirements: exiting can
fail when no legal nearby landing support exists, and a vehicle left behind
must remain boardable through active-object persistence.

The nearby landing-support probe is not a search for a destination to move the
party into. It checks only the four cardinal cells around the player in the
current rendered viewport. A cell supports leaving the vehicle when either:

- The visible terrain byte in that cell is passable for an on-foot avatar.
- The rendered cell is a companion/overlay cell representing a carpet object,
  an on-foot avatar/party sprite, a riderless horse, a manually handled ship,
  or a skiff.

This rule explains two visible edges. First, a carpet can be exited while it is
over passable ground even when no neighbouring support cell is accepted.
Second, skiff and ship exits use nearby support as a yes/no gate; when the gate
passes, the abandoned vehicle is still parked at the current party coordinate,
not in the accepted neighbouring cell.

## 6. Movement And Time Hooks

Vehicle movement is still mode-owned. The overworld and town movement handlers
own directional stepping, collision, boundary checks, and tile effects. The
vehicle system contributes the current transport state and a few modifiers:

- Foot and ships use the normal minute increment supplied by the active mode.
- Horse travel uses the mounted-horse terrain predicate. It otherwise follows
  the ordinary overland directional-step contract: one accepted destination
  cell per movement command and the standard overworld minute increment. The
  confirmed transport-marker pendulum for horse/carpet values gates
  active-object and encounter cadence, not player stride and not the time
  cleanup's minute increment.
- Skiff/raft-like water travel is associated with the time cleanup's `Q` tag,
  which halves non-zero time increments and floors the result at one minute.
- A separate `T` timing/state tag suppresses minute and light-counter
  advancement in the time cleanup, but it is not currently identified as a
  boarded vehicle family.
- Vehicle state participates in encounter checks and the overworld special
  underfoot-tile handling that can suppress movement and force zero light.

Tile passability is a layered decision. Ordinary vehicle movement passes the
current transport-marker family to the shared terrain-query dispatcher:
mounted horses, carpets, ships, and skiffs each select the predicate family
listed in `systems/movement.md`. Sail state affects ship cadence and X-Xit
refusal behavior, but both ship ranges use the same ordinary static terrain
predicate. `systems/movement.md` lists the exact accepted static tile ranges
for these ordinary vehicle terrain queries.

### Ship Sails

Y-Yell is the ship sail command when the party is aboard a ship. The vehicle
branch toggles between two visible modes:

- **Sails hoisted.** The ship is marked as under wind control.
  Movement/refusal is resolved later by the overworld movement loop using the
  wind/heading cadence in `weather.md`.
- **Sails furled.** The ship is manually handled. Wind-driven drift should not
  advance the ship while furled.

Toggling sail state updates the party's ship state but does not directly move
the ship. X-Xit should refuse the under-sail case while the ship is in the
hoisted/wind-control range `0x20..0x23`. The furled/manual ship range is
`0x24..0x27`. In both ranges, the low two bits carry heading as north, east,
south, west.

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
   random `1..20` amount from the target object's active-object byte `+5`.
   The broadside helper treats this byte as an unsigned depletion counter for
   hit resolution regardless of object family.
6. If the subtraction wraps the byte into the high-bit range, the hit object
   slot is cleared and object state is marked dirty. If the byte remains in the
   low range, the object stays in place with the reduced byte value.
7. If no target is found in range, the projectile is still animated to the
   endpoint.

For ship/frigate targets, byte `+5` is also hull condition, so broadside damage
directly lowers hull condition. For non-ship targets, byte `+5` can have an
ordinary family-specific meaning outside F-Fire, such as an animation seed,
object code, or movement counter. F-Fire does not branch on those meanings; it
only applies the generic depletion-and-clear rule above. Whirlpool-family
targets are explicitly skipped by the broadside path after the target
classifier, so their swirl phase byte is not depleted by ship fire.

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
  object-update chain, and marks object state dirty. The local cannon path also
  reduces the shared moral-standing selector by five units, floored at zero,
  after a successful active-object hit; it does not apply the overworld
  broadside's target byte-`+5` depletion rule in town-family scenes.

Dungeon scenes in the stock dungeon range refuse F-Fire with "What?". Combat
has its own command parser and does not inherit this resident F-Fire route.

## 9. Persistence

Vehicles persist through the active-object and object-overlay systems, not
through static map files.

- Parked vehicles are active-object records.
- Boarding removes or updates the parked object and moves its relevant state
  into the party transport state.
- Exiting creates or restores a parked object at the party's current map
  position after the command's terrain and carried-craft gates accept.
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
- **Movement.** `movement.md` owns the shared terrain-query layer, dynamic occupancy
  boundary, and movement commit rules consumed by vehicle travel and X-Xit
  landing checks.
- **Weather.** `weather.md` owns the prevailing wind state, wind display,
  hoisted-sail player-ship cadence, and sailing-refusal feedback boundary.
- **Doors and Z transitions.** `doors-and-z-transitions.md` cross-references
  X-Xit at the ordinary Z-transition boundary and documents door destruction
  as a door-system side effect.
- **Time.** `time.md` owns the `Q` and `T` state-tag modifiers that alter the
  minute increment; this spec owns the boarded vehicle families.
- **Active objects.** `active-objects.md` owns the slot record, allocator,
  renderer relationship, and combat backup/restore behaviour.
- **Save/load and OOL.** `save-load.md`, `formats/saved-gam.md`, and
  `formats/ool.md` own persistence of active-object vehicle records.
- **Items.** `catalogs/item-list.md` names vehicle inventory/acquisition
  families. Purchase prices and brokers live with shops.

## 11. Vehicle Boundaries And Remaining Work

The vehicle command contract is complete for the traced baseline at command and
state-transition depth: B-Board, X-Xit, F-Fire broadsides, Y-Yell sail toggling,
known transport-marker ranges, active-object persistence, ship hull/skiff bytes,
the town-family cannon active-object hit moral-standing selector debit, and
wind cadence ownership are fixed. Remaining work is catalog or opaque-state work, not a
change to the known horse, carpet, ship, skiff, broadside, or town-cannon command
transitions.

- **Unknown transport-marker consumers.** The known foot, horse, carpet, ship,
  and skiff ranges are public. The stats-panel now separates the nearby
  timing/status glyph byte from this transport/action marker, and it identifies
  marker family `0x20..0x27` as the ship hull-condition panel selector, but
  values outside the known marker ranges are still opaque. Keep this separate
  from the `Q`/`T` timing tag byte used by `time.md`; do not relabel opaque
  transport values as balloon state without a traced writer and consumer.
- **Vehicle art verification.** B-Board's object-byte families and boarded
  transport-state writes are public. Remaining catalog work is visual
  sprite-sheet naming for those vehicle frames; do not confuse sprite-sheet IDs
  with the transport/action marker ranges in Section 2.
- **Repair boundary.** Ship hull condition is consumed by boarding warnings and
  broadside depletion. The traced vehicle command set does not provide a
  separate repair command. If a repair service is later identified, document it
  under the shop/item acquisition surface that triggers it and leave the vehicle
  command transitions unchanged.
- **Balloon boundary.** Balloon sprites remain catalog assets, but the traced
  B-Board, X-Xit, U-Use, shipwright, and movement contracts do not provide a
  live balloon transport path for the analyzed baseline. Preserve the art family
  and any opaque saved marker values, but do not invent boarding, landing, or
  wind-driven balloon movement from catalog evidence alone.

## 12. Sources

This cleanroom spec was derived from private analysis notes and sibling public
specs. It intentionally does not reproduce decompiled code, assembly, raw data
tables, or implementation-specific addresses.

- `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`.
- `u5-decomp/functions/CMDS_OVL/0x0EB4_cmds_xit_vehicle.md`.
- `u5-decomp/functions/CMDS_OVL/0x073E_xit_nearby_landing_probe.md`.
- `u5-decomp/functions/CMDS_OVL/0x0962_cmds_fire_broadsides.md`.
- `u5-decomp/functions/CMDS_OVL/0x0AEA_cmds_fire.md`.
- `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- `u5-decomp/functions/ULTIMA_EXE/0xB8A4_init_object_slot.md`.
- `u5-decomp/functions/CAST_OVL/0x1792_use_item.md`.
- Local SHOPPES2 shipwright control-flow analysis and direct `SHOPPE.DAT`
  record inspection.
- `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- `u5-decomp/functions/MAINOUT_OVL/0x0490_mainout_letter_dispatch.md`.
- `u5-decomp/functions/MAINOUT_OVL/0x0598_mainout_input_helper.md`.
- `u5-decomp/notes/system-trace_movement.md`.
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
