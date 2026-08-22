# Weather

## 1. Overview

Ultima V's implemented weather system is wind. There is no confirmed rain, snow, storm, cloud-cover, temperature, fog-bank, or humidity model in the currently mapped behavior.

Wind has two confirmed jobs:

- It gives the overworld a visible "prevailing winds" state.
- It can drift through an idle-redraw random selector.
- It drives hoisted-sail player-ship cadence and stalled-sailing feedback.
- It gates the non-player water-creature / pirate-ship active-object cadence.

Wind does not drive daylight, torch duration, dungeon visibility, NPC schedules, town behavior, or encounter probability in the notes currently available. Those systems may run on the same turn cadence, but they are not weather consumers.

## 2. Wind State

The wind state is a small enumerated value with five user-facing presentations
and five saved/runtime values:

| Value | State | Meaning |
|---:|-------|---------|
| `0` | Calm | No prevailing wind. |
| `1` | North | A cardinal wind state. |
| `2` | South | A cardinal wind state. |
| `3` | East | A cardinal wind state. |
| `4` | West | A cardinal wind state. |

The presentation labels are stored in DATA.OVL in the order Calm, North, South,
East, and West, followed by the shared wind suffix. Wind labels name the
direction the wind blows **from**.

`SAVED.GAM` carries this wind state byte. Values 0 through 4 should round-trip
as the states above. A byte-compatible loader should still preserve any
unrecognised value for round-trip writes rather than normalising it, because
variant or corrupted saves may contain out-of-range state. Section 2.1 specifies
what the banner does with such a value.

### 2.1 The Wind Banner

**The wind banner is persistent border chrome, not a message-log line.** It is
written into a gap in the game-screen frame's bottom chrome ribbon, through the
full-screen text window, and it stays on screen until something repaints it.
Earlier revisions of this document described it as a "transition/status message"
printed on entering the world flow; that wording is withdrawn. It never enters
the message window and never scrolls.

**Cell layout.** The banner starts at a fixed cell — absolute column 6, row 23 —
and there is no centring arithmetic anywhere in it. Every direction label is
padded to exactly five characters in storage, so the banner is a constant
thirteen cells wide:

| Absolute column | Content |
|---:|---|
| 6 | Right-pointing bracket end-cap (`display-driver.md` section 7) |
| 7..11 | Direction label, five characters, left-aligned within its own padding |
| 12 | Space — the leading space of the stored suffix |
| 13..17 | `Winds` |
| 18 | Left-pointing bracket end-cap |

**The five labels**, exactly as stored and exactly as they render:

| Value | Stored label | Banner reads |
|---:|---|---|
| `0` | `Calm ` | `Calm  Winds` |
| `1` | `North` | `North Winds` |
| `2` | `South` | `South Winds` |
| `3` | `East ` | `East  Winds` |
| `4` | `West ` | `West  Winds` |

`Calm`, `East` and `West` are four letters padded to five, and the shared suffix
contributes its own leading space, so those three render with a **double space**
between the direction and `Winds`. `North` and `South` are five letters and
render with a single space. This is a visible difference, not a rounding
artefact, and an implementation that formats the banner as
`direction + " Winds"` without the pad will get three of the five states wrong.

**Out-of-range values.** A preserved value above 4 falls out of the label
selection entirely: the right cap is still drawn at column 6, the suffix is
printed at columns 7 through 12, and the closing cap lands at column 13 instead
of 18. Columns 14 through 18 keep whatever was previously there. The result is a
visibly short, visibly wrong banner rather than a clamp to Calm or to any valid
direction.

**Suppression and erase.** The banner is not drawn in combat-class scenes, in
the underworld scene, or on below-surface map levels. Combat and the underworld
simply skip it. A below-surface level actively **erases** it: it strokes the rule
`(48, 184)` to `(152, 184)` in the accent colour and then fills
`(48, 185) - (152, 191)` in the chrome colour, restoring the plain ribbon. Stale
text is never left behind. The dungeon view then writes its own bracketed facing
label into the same gap.

**Repaint triggers.** The banner is repainted, without changing the stored state,
on mode entry for the overworld and town loops and on loading a save. It is
repainted **with** a new state by the Wind Change spell and by the idle-redraw
random wind selector. Setting a new state also clears the cached wind-cadence
byte used by sailing and by wind-driven actors.

### Autonomous Wind Drift

The idle redraw tick includes a random wind selector. This is not a spell cast,
does not consume a turn by itself, and does not run from the time cleanup. It is
part of the redraw-side subsystem bundle that also handles active-object visual
animation, lighting refresh, and the night-time light beacon's beam stamps.

On an eligible redraw tick, the selector first rolls in `0..63`. Any non-zero
roll does nothing. On a zero roll, it chooses a candidate wind in `0..4`.
Cardinal candidates `1..4` are accepted immediately. Candidate `0` (Calm) is
accepted only when a follow-up roll in `0..255` is at least `192`; otherwise the
candidate selection repeats. The result is that a successful outer event always
eventually changes or re-announces a wind state, but Calm is much rarer than any
cardinal direction.

The accepted value routes through the same resident wind set-and-repaint helper
used by world entry. Supplying a new value stores it as the current wind state
and clears the cached wind-cadence byte used by sailing and wind-driven actors.
The store happens before any scene test, so the state is always updated; only
the banner repaint is conditional. The helper draws nothing in combat-class or
underworld scenes, and on a below-surface map level it takes the erase branch in
section 2.1 instead of writing a label.

## 3. Rel Hur

Rel Hur is the spell-system hook into weather. The C-Cast pipeline identifies it as the Wind Change spell, applies the normal spell prerequisites, consumes the appropriate pre-mixed charge, prompts for a direction, and then routes to the wind setter.

The direction prompt uses the shared spell direction picker described in
`systems/input.md`. Accepted cardinal directions print their direction name,
then Wind Change stores and displays the resulting prevailing wind:

| Prompt result | Stored wind state |
|---|---|
| North | West |
| East | East |
| South | South |
| West | North |

Space is accepted by the prompt as `Pass`; for Wind Change it is the
player-visible no-effect choice and leaves the stored wind unchanged. Other
non-cardinal keys re-prompt rather than returning an effect. The wind setter
also accepts Calm as a programmatic target. Calm is not reached by the
four-cardinal Rel Hur prompt, but the shared setter supports it for callers
that deliberately pass a calm target. Calling the setter with both old wind and
new wind Calm is a no-op. Any other accepted transition plays the wind sound
before storing and displaying the resulting wind state. Unrecognised target
values do nothing.

Rel Hur should not:

- Advance time by itself beyond the normal "casting consumes a turn" rule.
- Change daylight or torch/spell counters.
- Create rain, storms, or map hazards.
- Override dungeon blackout.

## 4. Ships And Sails

Ships have a sail state in addition to their heading. The Y-Yell command toggles a ship between the two sailing modes:

- **Sails hoisted.** The ship is under wind control.
- **Sails furled.** The ship is manually handled.

Changing sail state changes the party's ship avatar state. It does not directly move the ship on its own; movement still occurs through the overworld turn loop and its movement/action result handling.

A ship heading is encoded in the low two bits of the party transport marker:
`0` north, `1` east, `2` south, and `3` west. The surrounding marker range
records the sail state: `0x20..0x23` means hoisted and wind-controlled, while
`0x24..0x27` means furled and manually handled. Turning to a new heading is
observable as a command action, and movement along the current heading is
handled by the movement routines after the heading/state gate accepts it.

## 5. Player Ship Sailing Speed

Wind-driven sailing should be treated as discrete turn cadence, not continuous
velocity. The intended cleanroom model is a state-and-counter decision made by
the overworld turn loop, not a physics vector.

When sails are hoisted, a movement command first establishes or changes the
ship's heading. If the requested heading differs from the current cached sail
direction, the ship turns and clears the sailing counter; that action does not
also move the ship. Once the requested direction matches the cached heading,
the input helper can synthesize repeated movement commands from the cached
direction until the cache is cleared or replaced.

Wind labels are source-direction labels. A "West" wind is wind coming from the
west and pushing east. The hoisted-sail player ship uses that push vector as
follows:

| Wind | Sail north | Sail east | Sail south | Sail west |
|---|---|---|---|---|
| North wind | move after two wait ticks | immediate | move after one wait tick | immediate |
| South wind | move after one wait tick | immediate | move after two wait ticks | immediate |
| East wind | immediate | move after two wait ticks | immediate | move after one wait tick |
| West wind | immediate | move after one wait tick | immediate | move after two wait ticks |

A wait tick is a real overworld wait pass inside the input helper: the helper
runs the shared cleanup/redraw path, optionally advances the active-object
epilogue, pauses one world tick, increments the sailing counter, and then tests
the cached sail direction again. After movement is released, the counter is
cleared and the movement command returns to the normal overworld movement
dispatcher. The next released movement uses the same cadence again unless the
wind, heading, or cache changes.

Calm wind never releases a cached hoisted-sail movement. The ship waits until
the player enters a different command. A later Pass command reports the
stalled-sailing feedback and clears the cached sailing state.

The ship-rigging flag set by using the Plans for the HMS Cape affects the
wait-pass timing, not the direction table. Without the rigging flag, a sailing
wait pass uses the ordinary two-minute outdoor cleanup increment. With the
rigging flag active, sailing wait passes use a one-minute cleanup increment and
alternate the active-object epilogue. The same movement-release table above
still decides when the ship actually advances.

A former candidate in the overworld loop has also been ruled out: the resident
helper reached from the proximity and terrain-trigger paths is a short
world-tick pause, not a ship-sail or wind-state consumer.

## 6. Player Ship Feedback

When the player tries to sail in an invalid or stalled wind condition, the command path sets a short-lived sailing refusal state. The next pass command can report that the ship is stalled by the wind, then clears that state.

Implementations should preserve the behavior, not necessarily the exact original wording:

- A failed wind/sail attempt should be visible to the player.
- The refusal should clear after being reported.
- It should not become a permanent ship status.

## 7. Active Ships

The overworld active-object cleanup path applies prevailing wind to the
ship-like water-creature class, including pirate-ship frames. This is not the
adjacent/short-range attack path; it runs only when the earlier active-object
animator did not already handle the slot.

Calm wind suppresses this post-animate movement. For non-calm wind, the object
uses its current frame and the prevailing wind to select a cadence cap:

| Current frame | North wind | South wind | East wind | West wind |
|---|---|---|---|---|
| North-facing frame | 2 of 3 turns | 3 of 4 turns | every turn | every turn |
| East-facing frame | every turn | every turn | 2 of 3 turns | 3 of 4 turns |
| South-facing frame | 3 of 4 turns | 2 of 3 turns | every turn | every turn |
| West-facing frame | every turn | every turn | 3 of 4 turns | 2 of 3 turns |

The cadence counter is stored per active-object slot. A "2 of 3" entry means
the slot moves on two eligible cleanup passes, then resets and skips one. A
"3 of 4" entry moves on three eligible passes, then resets and skips one.
"Every turn" bypasses the counter and immediately allows the slot's movement
helper to run.

After the cadence allows a movement attempt, `active-objects.md` owns the
actual step-selection and validation behavior. Weather owns only the wind-state
gate and cadence table.

## 8. Cosmetic Limits

Weather presentation is deliberately small:

- The wind banner in the bottom border shows the current wind at all times on the surface (section 2.1).
- Idle redraws can occasionally choose a new wind state and repaint the banner.
- Wind gates hoisted-sail player ship movement.
- Wind does gate non-player water-creature / pirate active-object cadence.
- Wind does not darken the map, spawn clouds, change the dawn/dusk curve, alter the night-time beacon's light gate, or affect moongate placement.
- Wind does not affect dungeon lighting.
- Wind does not currently have a confirmed direct effect on random encounter probability.
- Wind does not change town NPC schedules.

Any modern additions such as rain overlays, thunder, wave animation, or storm encounter modifiers would be extensions, not cleanroom reproduction of the mapped original behavior.

## 9. Persistence

Wind is part of the runtime game state and should be saved with the rest of the world state. Loading a game should restore the prevailing wind before the overworld loop resumes, so wind-dependent player-ship cadence, active-object cadence, and the wind display agree immediately after load.

Because the displayed wind message is cosmetic, it can be recomputed from the mapped wind state on demand rather than saved as text. The rendered text itself is never part of the save.

## 10. Ownership Boundary

The weather contract in this document is complete at wind-state and cadence
depth. Weather owns wind state, wind presentation, idle-redraw random wind
selection, player-ship wind gating, and the wind-based cadence rules for
eligible non-player water actors. After those cadence rules allow a movement
attempt, the active-object step planner belongs to `active-objects.md`.

## 11. Sources

The behavior described here was derived from cleanroom reading of the following notes and sibling specs. No assembly excerpts, raw offsets, or raw private tables are reproduced here.

- Wind display strings and shared resident data context - `u5-decomp/formats/data-ovl.md`.
- Saved runtime state survey noting the wind field - `u5-decomp/formats/saves.md`.
- The world-entry/load note identifying the wind-direction display helper and
  the helper trace used for valid and out-of-range wind banner behavior -
  `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x2E96_announce_scene.md`.
- The idle-redraw random wind selector that feeds the same display/setter
  helper - `u5-decomp/functions/ULTIMA_EXE/0x2F62_event_random_scene_transition.md`
  and `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The Rel Hur / Wind Change spell's prompt-to-state handoff and calm/no-effect
  boundaries - `u5-decomp/functions/CAST2_OVL/0x040A_set_wind.md`.
- Overworld movement, ship state, and active-object epilogue boundaries -
  `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md` and
  `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The resolved overworld pause helper that rules out the former wrapped-call
  candidate as a wind-cadence routine -
  `u5-decomp/functions/ULTIMA_EXE/0x3AE6_world_tick_pause.md` and
  `u5-decomp/functions/MAINOUT_OVL/0x007A_mainout_proximity_yell_check.md`.
- Player-ship movement dispatch, under-sail direction cache, wind-vector
  cadence, and stalled-sailing feedback boundary -
  `u5-decomp/functions/MAINOUT_OVL/0x0490_mainout_letter_dispatch.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x0598_mainout_input_helper.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- Active-object pirate, water-creature, whirlpool, and monster behavior used to
  separate mapped actor AI from player-ship sailing and to derive the
  non-player water-creature wind cadence -
  `u5-decomp/functions/MAINOUT_OVL/0x131A_active_object_animate.md` and
  `u5-decomp/functions/MAINOUT_OVL/0x198C_post_animate.md`.
- Ship boarding, sail toggling, and ship command behavior - `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`, `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`, and `u5-decomp/functions/CMDS_OVL/0x0962_cmds_fire_broadsides.md`.
- Rel Hur's identity as Wind Change in the spell-cast system - `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`.
- Wind Change's direction prompt handoff, prompt-result mapping, calm no-op
  rule, wind sound trigger, and saved/runtime wind values -
  `u5-decomp/functions/CAST2_OVL/0x0306_prompt_direction.md` and
  `u5-decomp/functions/CAST2_OVL/0x040A_set_wind.md`.
- Source provenance: the wind banner's fixed cell layout, its bracket end-caps,
  the five stored five-character direction labels and the shared suffix's leading
  space, the resulting double-space rendering for Calm, East and West, the
  short-banner behaviour for out-of-range values, the erase rectangles used
  below the surface, and the correction that the banner is persistent chrome
  rather than a message-log line are derived from private analysis note
  `../u5-decomp/notes/gameplay_screen_layout_2026-08-22.md`, cross-checked
  against a fresh local re-read of the shipped executable and shared data
  overlay.
- Existing cleanroom descriptions of time, magic, and overworld integration - `u5-spec/systems/time.md`, `u5-spec/systems/magic.md`, and `u5-spec/systems/overworld.md`.
