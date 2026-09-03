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
byte used by sailing and by wind-driven actors — that is save byte `0x02DD`
(`formats/saved-gam.md` Section 5), and clearing it is the setter's only side
effect on the save image besides the wind byte itself.

**Entry and load never reroll the wind.** The set-and-repaint helper takes a
"print only" sentinel in place of a direction, and that is what every scene
entry passes and what the load path passes after the save image has been read.
The `Calm Winds` line a player sees on walking into a town, and the line the
intro prints after a Journey Onward, are **reprints of the restored state**, not
new draws. There is exactly one writer of the wind byte in the shipped build —
the store inside this helper — so wind changes can arrive only from *Rel Hur*
(Section 3) and from the autonomous drift below. That single-writer finding is
**established for a stated scan scope**: a reference census over the shipped
executable, all twenty-three code overlays and all four display drivers,
covering direct, indexed and accumulator-relative forms, with every call site of
the helper enumerated. An access computed from a pointer base outside the
scanned window would not appear in it.

One detail of the load path, published for exactness rather than because it is
observable: before the save image is read, the intro calls the same helper once
with a **real** direction — Calm — which does store the wind byte and clear the
cadence byte. The `SAVED.GAM` read then overwrites both a moment later, so the
restored values are the file's. An implementation is free to omit that
pre-restore call entirely.

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
cardinal direction. The stationary distribution of the accepted value is
therefore **one seventeenth Calm and four seventeenths for each of the four
cardinal directions**.

**Cadence, stated precisely, because it is easy to get wrong.** The selector
runs **once per idle world tick** — not once per keyboard poll. The idle
key-wait loop reaches the world tick on one iteration in four, and many other
call sites drive the world tick besides (`systems/main-loop.md` Section 9). The
world tick also skips its entire body while the master redraw-enable byte at
save offset `0x02FE` is clear, and no roll happens on such a pass. What is
**established** is one roll per world tick at a one-in-sixty-four trigger; how
often that is in wall-clock seconds is **inferred**, because no timing run was
made and the world-tick rate itself is unmeasured. Do not publish a seconds
figure for the expected drift interval.

**An engine whose idle loop omits the drift shows Calm forever.** That is as
visible a divergence as rerolling on entry would be: two runs of the original
that load the same save and press Q shortly afterwards can legitimately record
different wind values, because the drift fired between the load and the save.
A wind byte that never changes without a spell is a defect, not parity.

**The autonomous drift is silent.** It contains no sound call, no wrapper, and
no ambient hook; the wind sound belongs to the spell and scroll handlers, never
to the setter (`audio.md` section 7.3). The drift also passes the **raw**
direction index to the setter, without the transform the spell applies in
section 3, so the two paths are not interchangeable.

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
values do nothing. The sound variant is selected by the **caller tag** — spell
or scroll — and by nothing else: the Wind Change spell plays variant 2 and the
Wind Change scroll plays variant 1, whatever the old and new winds are.
*Earlier revisions of this sentence said the variant is selected from the prior
Calm/non-Calm state; that is withdrawn, see `RETRACTIONS.md`.* `audio.md`
section 7.3 gives the recipe and the one silent accepted path.

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

**Why crosswind is the fastest point of sail.** The wait threshold is not an
ordering by how far the heading is from downwind. The engine counts the axes on
which the requested heading disagrees with the wind's push vector, starting the
count at one, and takes that count modulo three. Downwind disagrees on no axis
and yields one; upwind disagrees on exactly one axis and yields two; crosswind
disagrees on both and yields three, which folds to **zero**. A crosswind heading
therefore releases on the very first pass, strictly faster than downwind. It
reads like an off-by-one in the original, and an engine reproducing the cadence
has to reproduce the fold. The table above already encodes it; the note is here
so nobody "fixes" the table.

A wait tick is a real overworld wait pass inside the input helper. Each pass
runs the shared cleanup/redraw path, advances the outdoor clock, runs the whole
outdoor per-turn epilogue (encounter probe and creature movement — so a wait
pass is a **fully consumed game turn**, not an idle pass; monsters close in and
encounters spawn while the ship waits for wind), performs one world step,
increments the sailing counter, polls one key, and then tests the cached sail
direction again. `systems/timing.md` Section 8.2 owns the per-pass tick and
world-step accounting and the same-direction key swallow. After movement is
released, the counter is cleared and the movement command returns to the normal
overworld movement dispatcher. The next released movement uses the same cadence
again unless the wind, heading, or cache changes.

Calm wind never releases a cached hoisted-sail movement. The ship waits until
the player enters a different command. A later Pass command reports the
stalled-sailing feedback and clears the cached sailing state.

The ship-rigging flag set by using the Plans for the HMS Cape affects the
wait-pass timing, not the direction table. Without the rigging flag, a sailing
wait pass uses the ordinary two-minute outdoor cleanup increment. With the
rigging flag active, **every** sailing wait pass uses the one-minute increment,
while the outdoor per-turn epilogue is run on **alternate** passes only — the two
halves of the flag's own parity toggle differ in the epilogue, not in the clock
step. The same movement-release table above still decides when the ship actually
advances.

A former candidate in the overworld loop has also been ruled out: the resident
helper reached from the proximity and terrain-trigger paths is a short
world-tick pause, not a ship-sail or wind-state consumer.

### 5.1 The cached sail direction: one setter and four clears

Earlier revisions of this section named the Pass command and left the rest of the
cache's lifecycle unenumerated, and issue #189 asked which commands — collision,
docking, furling, boarding, disembarking — clear it. The complete rule is not a
command list at all. It is **marker-conditioned**, and it is smaller than any
enumeration of commands. This is a first publication of the full set, not a
reversal of the two events already published.

**The one setter.** A movement command taken while the party's transport marker
is a hoisted frigate (`0x20`–`0x23`) stores the requested heading into the cache.
Two details an engine needs:

- The stored value is always a real movement direction and is **never zero**, so
  **a new heading replaces the cache rather than clearing it.** An engine that
  clears first and then re-sets exposes a momentarily empty cache the original
  never has.
- The store runs only when the requested heading **differs** from the cached one,
  and it is the same step that zeroes the sailing counter. Repeating the heading
  already cached changes neither the cache nor the counter, and in particular
  does not restart the wait.

**The four clears.**

| Event | What it is |
|---|---|
| Entering outdoor mode | The outdoor-mode entry pass clears the cache in its opening block, so no cached heading survives a scene change into the overworld. |
| An under-sail step refusal | **One** decision point with three narration arms — `BREAKING UP!` on the shoal value, `Docked!` on exact pier terrain (which also furls the marker), `COLLISION!` otherwise — and all three clear the cache (`systems/overworld.md` Section 6.2.5, `systems/vehicles.md`). |
| The Pass command | Only while the outdoor scene is current and the cache is non-zero; it prints the stalled-sailing line first, then clears. |
| The post-command marker guard | After **every** outdoor command handler returns, and before the next input is read, the loop clears the cache unless the transport marker is still a hoisted frigate. |

**The marker guard is the answer to the command question.** Furling, boarding,
disembarking, mounting a horse or a carpet, and anything else that moves the
transport marker out of the hoisted-frigate run are covered by that single guard,
on the same turn. None of those command handlers references the sail cache at
all; each one moves the marker, and the guard does the rest. The guard is equally
the reason a Look, a Ztats, or any other marker-neutral command under sail does
**not** interrupt sailing: the marker is unchanged, so the guard leaves the cache
alone. An engine that implements per-command clears will agree with the original
on the commands it thought of and disagree on the ones it did not.

*Scope of the negative.* "One setter and four clears" is complete within a
corpus-wide census over the shipped executable, all overlays and all display
drivers, covering direct, indexed and pointer-forming references to the cache
byte. Writes made through a pointer loaded from memory, block fills and computed
addresses are outside that census; none was found and none is excluded.

**A fourth reset of the sailing counter.** Besides the heading change and the
release described above, and besides the per-pass increment, **a wind change
zeroes the sailing counter.** The routine that stores a new wind state clears the
counter immediately afterwards, and both are skipped when the same routine is
called only to re-announce the wind already in force. So a ship one pass into a
two-pass upwind wait restarts that wait when the wind shifts; Section 2's
autonomous drift is the ordinary source of such a change. This reset was not
previously published.


## 6. Player Ship Feedback

When the player tries to sail in an invalid or stalled wind condition, the command path sets a short-lived sailing refusal state. The next pass command can report that the ship is stalled by the wind, then clears that state.

Implementations should preserve the behavior, not necessarily the exact original wording:

- A failed wind/sail attempt should be visible to the player.
- The refusal should clear after being reported.
- It should not become a permanent ship status.

## 7. Active Ships

The overworld per-slot movement dispatch applies prevailing wind to the
ship-like water-creature class, including pirate-ship frames. This is not the
adjacent/short-range attack path.

> *Corrected (2026-08-23).* This section called that path the "active-object
> cleanup path" and said it "runs only when the earlier active-object animator
> did not already handle the slot". Both are withdrawn. The path performs no
> cleanup and no animation - it dispatches movement - and its gate is a running
> total of the reaction pass's results across the whole slot walk, not a
> per-slot test: once any earlier slot in the turn produced a reaction, this
> path is skipped for every remaining slot that turn. `systems/active-objects.md`
> carries the full contract.

Calm wind suppresses this movement. For non-calm wind, the object
uses its current frame and the prevailing wind to select a cadence cap:

| Current frame | North wind | South wind | East wind | West wind |
|---|---|---|---|---|
| North-facing frame | 2 of 3 turns | 3 of 4 turns | every turn | every turn |
| East-facing frame | every turn | every turn | 2 of 3 turns | 3 of 4 turns |
| South-facing frame | 3 of 4 turns | 2 of 3 turns | every turn | every turn |
| West-facing frame | every turn | every turn | 3 of 4 turns | 2 of 3 turns |

The cadence counter is stored per active-object slot. A "2 of 3" entry means
the slot moves on two eligible passes, then resets and skips one. A
"3 of 4" entry moves on three eligible passes, then resets and skips one. The
cadence counter is persisted with the object, so it survives save and reload.
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

The wind byte lives at save offset `0x02EC` and the cached wind-cadence byte at `0x02DD` (`formats/saved-gam.md` Sections 5 and 6). **Neither is recomputed, normalised or rerolled by the load path or by scene entry** (Section 2.1): a load restores whatever the file held, and the banner that follows is a reprint. Save and load are therefore verbatim for wind in both directions.

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
  `u5-decomp/functions/INTRO_OVL/` and
  `u5-decomp/functions/ULTIMA_EXE/` (that note's
  filename predates its 2026-08-22 naming correction; the routine sets and
  announces the prevailing wind and has nothing to do with scene entry).
- The idle-redraw random wind selector that feeds the same display/setter
  helper - `u5-decomp/functions/ULTIMA_EXE/`
  (filename likewise predates its 2026-08-22 naming correction; it selects a
  wind, not a scene transition)
  and `u5-decomp/functions/ULTIMA_EXE/`.
- The Rel Hur / Wind Change spell's prompt-to-state handoff and calm/no-effect
  boundaries - `u5-decomp/functions/CAST2_OVL/`.
- Overworld movement, ship state, and active-object epilogue boundaries -
  `u5-decomp/functions/MAINOUT_OVL/`.
- The resolved overworld pause helper that rules out the former wrapped-call
  candidate as a wind-cadence routine -
  `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/functions/MAINOUT_OVL/`.
- Player-ship movement dispatch, under-sail direction cache, wind-vector
  cadence, and stalled-sailing feedback boundary -
  `u5-decomp/functions/MAINOUT_OVL/`, and
  `u5-decomp/functions/ULTIMA_EXE/`.
- Active-object pirate, water-creature, whirlpool, and monster behavior used to
  separate mapped actor AI from player-ship sailing and to derive the
  non-player water-creature wind cadence -
  `u5-decomp/functions/MAINOUT_OVL/`.
- Ship boarding, sail toggling, and ship command behavior - `u5-decomp/functions/CMDS_OVL/`, and `u5-decomp/functions/CMDS_OVL/`.
- Rel Hur's identity as Wind Change in the spell-cast system - `u5-decomp/functions/CAST_OVL/`.
- Wind Change's direction prompt handoff, prompt-result mapping, calm no-op
  rule, wind sound trigger, and saved/runtime wind values -
  `u5-decomp/functions/CAST2_OVL/`.
- Source provenance: the wind banner's fixed cell layout, its bracket end-caps,
  the five stored five-character direction labels and the shared suffix's leading
  space, the resulting double-space rendering for Calm, East and West, the
  short-banner behaviour for out-of-range values, the erase rectangles used
  below the surface, and the correction that the banner is persistent chrome
  rather than a message-log line are derived from private analysis under
  `u5-decomp/notes/`, cross-checked
  against a fresh local re-read of the shipped executable and shared data
  overlay.
- Existing cleanroom descriptions of time, magic, and overworld integration - `u5-spec/systems/time.md`, `u5-spec/systems/magic.md`, and `u5-spec/systems/overworld.md`.
- Source provenance: the single-writer census for the wind byte, the complete
  call-site list of the set-and-repaint helper (including the two intro calls on
  the Journey Onward path), the drift roll's per-world-tick cadence and its
  master-redraw gate, the one-seventeenth/four-seventeenths stationary
  distribution, and the setter's clear of the cached wind-cadence byte are
  derived from private analysis in `u5-decomp/notes/`, cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/functions/INTRO_OVL/`,
  `u5-decomp/functions/TOWN_OVL/` and `u5-decomp/functions/MAINOUT_OVL/`. The
  census scope is the shipped executable, all twenty-three code overlays and all
  four display drivers. No wall-clock timing was measured, so every interval
  statement in Section 2.1's drift subsection is inferred from per-tick cadence.
