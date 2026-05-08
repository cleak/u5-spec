# Weather

## 1. Overview

Ultima V's implemented weather system is wind. There is no confirmed rain, snow, storm, cloud-cover, temperature, fog-bank, or humidity model in the currently mapped behavior.

Wind has two jobs:

- It gives the overworld a visible "prevailing winds" state.
- It affects sailing and wind-driven ship movement.

Wind does not drive daylight, torch duration, dungeon visibility, NPC schedules, town behavior, or encounter probability in the notes currently available. Those systems may run on the same turn cadence, but they are not weather consumers.

## 2. Wind State

The wind state is a small enumerated value with five user-facing presentations:

| State | Meaning |
|-------|---------|
| Calm | No prevailing wind. |
| North | A cardinal wind state. |
| South | A cardinal wind state. |
| East | A cardinal wind state. |
| West | A cardinal wind state. |

The presentation labels are stored in DATA.OVL in the order Calm, North, South, East, and West, followed by the shared "Winds" suffix. The UI helper prints the current wind state as a short transition/status message when entering the world flow. The helper is presentation-only: it reads the wind state and displays the corresponding label, then returns to the normal mode dispatch.

The label order does not by itself prove the saved byte values. Implementations should store wind as a semantic enum internally, not as an exposed raw byte. Save import/export is the exception: `SAVED.GAM` carries the original wind state byte, and byte-compatible tooling should preserve that byte exactly. Until the byte-to-label table is verified, loaders should avoid clamping or normalizing unknown wind bytes; preserve the original byte for round-trip writes and map only recognised values into the public enum.

## 3. Rel Hur

Rel Hur is the spell-system hook into weather. The C-Cast pipeline identifies it as the Wind Change spell, applies the normal spell prerequisites, consumes the appropriate pre-mixed charge, and then routes to the spell effect.

The confirmed gameplay contract is that a successful Rel Hur invokes the Wind Change effect and changes the prevailing wind state. Current public evidence does not yet prove the exact state transition order, the calm-state rule, or the saved-byte mapping. A v1 implementation should expose a deterministic wind-change operation, preserve the raw saved wind byte for round-trip compatibility, and keep the chosen transition documented until the handler is traced or captured.

Rel Hur should not:

- Advance time by itself beyond the normal "casting consumes a turn" rule.
- Change daylight or torch/spell counters.
- Create rain, storms, or map hazards.
- Override dungeon blackout.

Until the transition order is proven, a practical implementation can choose a deterministic rule and keep the choice documented.

## 4. Ships And Sails

Ships have a sail state in addition to their heading. The Y-Yell command toggles a ship between the two sailing modes:

- **Sails hoisted.** The ship is under wind control.
- **Sails furled.** The ship is manually handled.

Changing sail state changes the party's ship avatar state. It does not directly move the ship on its own; movement still occurs through the overworld turn loop and its movement/action result handling.

A ship heading is encoded separately from the sail state. Turning to a new heading is observable as a command action, and movement along the current heading is handled by the movement routines after the heading/state gate accepts it.

## 5. Sailing Speed

Wind-driven sailing uses discrete turn cadence, not continuous velocity. The engine does not compute a physics vector; it consults a small directional cadence table keyed by wind state and ship heading.

The observed categories are:

- **Calm.** Wind-driven movement does not occur.
- **Perpendicular wind.** The ship does not advance under sail.
- **Same-axis wind.** The ship can advance, with one cadence for one direction along the axis and a different cadence for the opposite direction.

The cadence is tracked with a per-ship counter. On allowed wind/heading combinations, the counter makes ships move on a repeated schedule; on disallowed combinations, movement is skipped. This is the original's "speed" model: a ship moves on some turns and waits on others.

The exact interpretation of a label such as "North wind" as "wind blowing toward north" versus "wind coming from north" should be verified before assigning the faster cadence to a modern compass convention. The important cleanroom contract is axis and cadence based, not a continuous acceleration model.

## 6. Player Ship Feedback

When the player tries to sail in an invalid or stalled wind condition, the command path sets a short-lived sailing refusal state. The next pass command can report that the ship is stalled by the wind, then clears that state.

Implementations should preserve the behavior, not necessarily the exact original wording:

- A failed wind/sail attempt should be visible to the player.
- The refusal should clear after being reported.
- It should not become a permanent ship status.

## 7. Active Ships

The overworld active-object epilogue also processes ship-like active objects. These use the same kind of wind/heading cadence table: the object's heading, the current wind, and a per-object counter decide whether it advances this turn.

This matters for non-player ships. Pirates and other ship objects can drift or stall according to wind while the overworld active-object walker is running. The active-object walker does not consult the hour of day; wind-driven motion is per-turn, not per-hour.

## 8. Cosmetic Limits

Weather presentation is deliberately small:

- The transition/status display can show current winds.
- Wind may influence ship movement.
- Wind does not darken the map, spawn clouds, change the dawn/dusk curve, or alter moongate daylight gating.
- Wind does not affect dungeon lighting.
- Wind does not currently have a confirmed direct effect on random encounter probability.
- Wind does not change town NPC schedules.

Any modern additions such as rain overlays, thunder, wave animation, or storm encounter modifiers would be extensions, not cleanroom reproduction of the mapped original behavior.

## 9. Persistence

Wind is part of the runtime game state and should be saved with the rest of the world state. Loading a game should restore the prevailing wind before the overworld loop resumes, so ship motion and the wind display agree immediately after load.

Because the displayed wind message is cosmetic, it can be recomputed from the mapped wind state on demand rather than saved as text. The rendered text itself is never part of the save.

## 10. Open Questions

- **Rel Hur transition order.** The cast pipeline and Wind Change identity are known, but the exact state transition order and calm handling have not been isolated in a per-effect handler note.
- **Compass convention.** The wind cadence table proves axis-based movement, but the direction labels still need a final convention decision before assigning "with wind" and "against wind" language.
- **Player ship versus active-object ship path.** The active-object wind path is clearer than the player command path. The modern implementation should keep the visible behavior aligned, then refine once the movement helpers are fully documented.
- **Wind byte mapping.** The display label order is identified, and the load path displays the wind after reading the save. The exact saved-byte-to-label mapping still needs the display helper body or runtime capture before assigning stable public numeric values.

## 11. Sources

The behavior described here was derived from cleanroom reading of the following notes and sibling specs. No assembly excerpts, raw offsets, or raw private tables are reproduced here.

- Wind display strings and shared resident data context - `u5-decomp/formats/data-ovl.md`.
- Saved runtime state survey noting the wind field - `u5-decomp/formats/saves.md`.
- The world-entry/load note identifying the wind-direction display helper - `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- Overworld movement, ship state, active-object epilogue, and wind-driven object cadence - `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md` and `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- Ship boarding, sail toggling, and ship command behavior - `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`, `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`, and `u5-decomp/functions/CMDS_OVL/0x0962_cmds_fire_broadsides.md`.
- The A-Z dispatcher behavior for pass/refusal feedback - `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- Rel Hur's identity as Wind Change in the spell-cast system - `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`.
- Existing cleanroom descriptions of time, magic, and overworld integration - `u5-spec/systems/time.md`, `u5-spec/systems/magic.md`, and `u5-spec/systems/overworld.md`.
