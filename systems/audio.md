# PC-Speaker Audio

## 1. Scope and compatibility target

The analyzed DOS baseline has one audio backend: the IBM PC speaker. It has no
music sequencer, sampled-audio mixer, audio queue, or independently scheduled
sound channel. The display drivers and the resident game routines drive the
speaker directly. The files shipped with this baseline contain no AdLib, Sound
Blaster, MIDI, or external music-resource path.

Audio is presentation state unless a section below says otherwise. In
particular, pitch jitter normally does not select gameplay outcomes. Some
presentation routines nevertheless consume the gameplay random stream, so
silencing or replacing their sound must not accidentally remove those random
state advances.

This document gives the original numeric sound parameters. A modern frontend
may synthesize equivalent waveforms instead of emulating timer ports, provided
it preserves the stated trigger, cancellation, ordering, blocking, mute, and
random-state boundaries.

## 2. One channel, synchronous ownership

The speaker is a single mono, one-bit channel. There is no mixing. Starting a
new tone replaces the previous timer divisor; stopping clears the speaker. Most
effects own the calling thread until they finish, so gameplay and command input
do not continue underneath them.

Two presentation-driven cases are worth distinguishing:

- A visual loop may change the speaker frequency once per drawing step. The
  sound overlaps that loop's drawing, but it is still synchronous with the
  presentation and has no background worker.
- Frame- or tick-driven ambience may leave the speaker enabled until the next
  frame changes or stops it. This is still one serial speaker state, not an
  audio queue.

An implementation must stop the speaker at every specified effect end and on
the specified abort paths. Otherwise a muted or interrupted effect can leave a
stale tone sounding into the next scene.

## 3. Sound toggle and mute behavior

The sound setting is a runtime boolean. It starts enabled when the program
boots. Ctrl-S in overworld, town, combat, and dungeon command loops prints the
new `Sound On` or `Sound Off` state and flips the boolean. The toggle command
itself plays no acknowledgement sound and consumes no gameplay turn. The value
is not part of the saved game; a new process starts with sound enabled again.

For ordinary resident effects, muting suppresses audible speaker enable or
manual pin changes but does not shorten the effect:

- a blocking tone still performs its calibrated hold;
- a glissando still performs every calibrated step;
- random rumble still advances its sound-only jitter state, rewrites the timer
  divisor, and performs every delay;
- a software envelope follows a matched silent timing loop;
- all of these still perform their final speaker stop.

The practical contract is that Ctrl-S changes output, not command or animation
cadence. A silent frontend may omit physical synthesis, but it must preserve
the effect's blocking and state-advance behavior.

The EGA start-screen subtitle ignition is a special case. It runs inside the
display driver before gameplay can accept Ctrl-S and does not consult the
resident sound boolean. Its own burst gate decides whether each publication is
sounded.

## 4. Timing units

Three different timing classes occur in audio-related presentation:

| Unit | Meaning |
|---|---|
| Calibrated CPU unit | A boot-measured busy loop. It is neither a millisecond nor a gameplay minute. This owns blocking tones, glissandi, rumble fragments, software envelopes, and the subtitle-ignition waits. |
| BIOS tick | The approximately 18.2 Hz system tick. A few presentation scripts schedule an audio call once per tick, but the audio call's own short hold may still be calibrated. |
| Drawing work | No explicit wait. Tone changes are separated only by the synchronous raster or blit work between them. The shared full-viewport flash/rumble uses this cadence. |

`systems/timing.md` owns the boot calibration and BIOS-tick contracts. Exact
wall-clock playback on a historical machine depends on that calibration. A
modern implementation may choose stable real-time approximations, but should
keep relative duration, step count, and event ordering exact.

## 5. Sound families

### 5.1 PIT tone

A requested frequency `f` in hertz selects the integer timer divisor
`floor(1,193,182 / f)`. The low and high divisor bytes are installed and the
speaker is enabled. A stop operation unconditionally disables it.

A blocking tone is `(hold, frequency)`: begin the frequency, wait `hold`
calibrated units in delay context 1, then stop. Muting omits the audible begin
but retains the wait and stop.

### 5.2 Linear glissando

A glissando is described by `(span, delay, target, initial)`. It computes the
signed integer increment

```text
(target - initial) * delay / span
```

with the fractional part discarded. It starts at `initial`, emits
`ceil(span / delay)` tone updates, waits `delay` calibrated units after every
update, and stops once at the end. The target is normally the interpolation
endpoint rather than a played update.

The common recipes are:

| Recipe | Span | Per-update delay | Played frequency sequence |
|---|---:|---:|---|
| Action snap | 40 | 1 | 40 updates: 1200, 1220, ... 1980 Hz, rising toward 2000 Hz. |
| Cast failure | 50 | 1 | 50 updates: 800, 824, ... 1976 Hz, rising toward 2000 Hz. |
| Dungeon wall drip, near to far | 20, 12, 4, or -4 | 1 | Starts at 3200 Hz and rises toward 3500 Hz. The four depth bands emit 20 updates in steps of 15 Hz, 12 in steps of 25 Hz, 4 in steps of 75 Hz, or no tone at all. |

A negative span produces no tone update and only performs the final stop. No
confirmed caller supplies zero.

### 5.3 Random rumble

Random rumble is `(step, target, maximum_frequency)`. Its accumulator starts at
zero. Each iteration:

1. advances a private sound-only jitter state;
2. chooses an inclusive frequency from `100..maximum_frequency` Hz;
3. installs that timer divisor;
4. waits `step * (boot_calibration >> 4)` inner loop units; and
5. adds `step` to the accumulator.

The effect stops after `ceil(target / step)` iterations and then disables the
speaker. The private jitter state starts from the same fixed nonzero value on
each program run and is not the gameplay PRNG. A deterministic frontend may
replace its sequence freely, provided it does not use or perturb gameplay
randomness and preserves the frequency range, iteration count, and timing.

Common recipes are:

| Use | Step | Target | Inclusive pitch range | Updates |
|---|---:|---:|---:|---:|
| Trap or failed reagent mix | 40 | 3000 | 100..500 Hz | 75 |
| Ordinary damage presentation | 10 | 1600 | 100..2000 Hz | 160 |
| Shared potion/wind lead, variant `v` | 800 | `8000 + 1600v` | 100..700 Hz | 10 through 26 for variants 0 through 8 |
| Short two-part sting | 1, then 1 | 25, then 25 | 100..1000 Hz, then 100..1500 Hz | 25 + 25, separated by a 20-unit calibrated silent hold |

### 5.4 Software envelope

The envelope generator does not interpret one argument as a frequency in
hertz. It changes the speaker pin in a calibrated software loop. One envelope
is described by:

- signed comparison delta;
- initial unsigned comparison value;
- iteration count;
- idle count; and
- phase period.

The phase starts at zero. On each iteration it adds the phase period modulo
65536, compares that unsigned phase with the moving comparison value to choose
the low or high pin state, and advances the comparison value by the signed
delta modulo 65536. The per-iteration idle work is the idle count multiplied by
`floor(boot_calibration / 24)` when calibration is at least 100; below that
threshold the inner factor becomes zero.

This recurrence is the exact clean equivalent. There is no machine-independent
Hz conversion because the effective waveform also depends on the calibrated
software-loop rate. A host synthesizer may replace it with a perceptually
equivalent sweep, but the trigger, opposing sweep directions, iteration count,
and blocking duration remain normative.

## 6. Shared potion and wind envelope table

The nine low-numbered audiovisual variants share one sequence:

1. run random rumble `(800, 8000 + 1600v, 700)`;
2. invert the complete EGA/Tandy gameplay viewport;
3. run the first software envelope with positive delta;
4. run the second envelope with the same magnitude and negative delta; and
5. invert the same viewport again to restore it.

Both envelopes use idle count 1. Their remaining values are:

| Variant | Phase period | First initial comparison | Second initial comparison | Delta magnitude | Iterations per envelope |
|---:|---:|---:|---:|---:|---:|
| 0 | 8810 | 2700 | 32700 | 3 | 10000 |
| 1 | 7830 | 3000 | 31000 | 2 | 14000 |
| 2 | 7060 | 1000 | 37000 | 2 | 18000 |
| 3 | 6550 | 100 | 45000 | 2 | 22000 |
| 4 | 5950 | 5000 | 31000 | 1 | 26000 |
| 5 | 5570 | 4000 | 34000 | 1 | 30000 |
| 6 | 5180 | 2500 | 36500 | 1 | 34000 |
| 7 | 4820 | 1000 | 39000 | 1 | 38000 |
| 8 | 4480 | 1 | 42000 | 1 | 42000 |

This table describes the moving phase/comparison waveform, not a list of PIT
frequencies. Sound-disabled play still executes the rumble, both envelope
loops, and both viewport operations.

Spell handlers reuse these variants. Confirmed groupings include:

| Variant | Confirmed uses |
|---:|---|
| 0 | The lowest shared effect class, including the corresponding scroll/light presentation. |
| 1 | Awaken, Cure, Heal, and Vanish's committed pre-effect. |
| 2 | Reveal/locate, Conjure, Create Food, successful Open, and the calm-to-wind transition. |
| 3 | Blink and Great Light. |
| 4 | Dungeon rise/fall and Dispel Field. |
| 5 | Swarm, Magic Lock, and successful unlock-door effects. |
| 6 | Charm, Polymorph, Kill/Slay Living, and related high-circle attack effects. |
| 7 | Invisibility, creature clone, and View. |
| 8 | The highest resurrection-mode presentation. |

The spell-specific state changes, target gates, and cancellation results remain
owned by `systems/magic.md` and `catalogs/spell-list.md`.

## 7. Priority effects

### 7.1 Start-screen WD.BIT subtitle ignition

The ignition is a two-pass masked reveal. Sound is considered only after a
batch publication; ordinary visited positions emit no burst and perform no
audio wait.

At the start of each pass the burst threshold is 400. Publication number `k`,
counting from one, uses threshold `400 - 3k`. A persistent driver-local gate
state is advanced, and a burst is admitted when its low nine bits are below
that threshold. The gate state is not reset between the two passes or between
later ignition calls.

An admitted burst emits 25 successive frequencies. A separate persistent
pitch state advances once per frequency and maps to `100..1500` Hz. Each tone
uses divisor `floor(1,193,182 / frequency)` and is held for one outer delay unit
whose inner count is `boot_calibration >> 4`. The speaker stops after the 25th
tone.

Every sounded publication then waits 45 full calibration units. Every silent
publication waits 50. The burst therefore adds its 25 short pitch holds but
selects the shorter of the two publication waits.

Normal calibration publishes 110 batches per pass. Calibration below 250
publishes 55 per pass. From fresh driver state, the two normal passes admit 48
then 53 bursts; the two slow-cadence passes admit 35 then 33. Later calls can
differ because the gate and pitch states persist.

The pitch state is driver-local presentation state, not gameplay randomness.
A frontend may substitute another deterministic 25-pitch sequence within the
same 100..1500 Hz range, provided it preserves burst admission, pitch count,
holds, final stop, and the 45/50-unit publication branch. `intro.md` Section 5
publishes the exact recurrence for implementations that want bit-for-bit pitch
selection.

Keyboard status is checked once per nonzero reveal state after that state's
work. An abort completes the current position and any publication it caused,
leaves the key queued for the caller, stops the speaker, and omits all later
states. The transition cannot be muted through Ctrl-S because it occurs before
that gameplay command is available.

### 7.2 Accepted potion

The selected bottle is decremented and a party-member target is accepted before
the shared presentation begins. Cancellation before target acceptance skips
the presentation. The selected bottle id, not the later variation roll, chooses
variant 0 through 7 from Section 6.

The effect is blocking, polls no input, advances no gameplay clock, and uses no
BIOS tick. Muting preserves all three sound timing loops and the paired viewport
inversions. `catalogs/item-list.md` owns the later colour-specific gameplay
result and randomized substitution rule.

### 7.3 Accepted wind change / Rel Hur

Cancelling the direction prompt produces no wind sound. If both the old and
requested wind are Calm, the accepted setter is also a silent no-op. Every
other accepted transition plays the Section 6 sequence before committing and
announcing the new wind.

The previous wind state chooses the variant:

| Old wind | Requested wind | Result |
|---|---|---|
| Calm | Calm | No state change and no effect. |
| Calm | Any direction | Variant 2. |
| Any direction | Calm, the same direction, or another direction | Variant 1. |

The new compass direction does not select pitch. In particular, requesting the
already-active direction still plays variant 1 because the only fully silent
equality case is Calm-to-Calm.

### 7.4 Blocked top-down movement or combat step

A rejected town movement and a rejected combat step-or-attack both print
`Blocked!`, then play a blocking 165 Hz tone for 200 calibrated units, then run
their ordinary display/input cleanup. Ctrl-S suppresses the tone but not the
200-unit hold.

Successful top-down movement has no corresponding footstep sound. The beep is
a rejection cue and must not be attached to ordinary movement.

## 8. Confirmed trigger inventory

### 8.1 Commands, inventory, and conversation

| Trigger | Sound and boundary |
|---|---|
| Stolen-action warning | After the warning line and before the selected item or gold is removed, play the 40-update action snap. |
| Ring vanishes | After the accepted mutation and narration, play the 40-update action snap. A cancelled confirmation does not. |
| Jimmy key breaks | Failure only: print the break line, play the 40-update action snap, then decrement the key count. Success is silent. |
| Borrowed fixed object | After the live tile is rewritten and the borrowing line is printed, play the 40-update action snap. |
| Ordinary active-object pickup, crop pickup, and successful Jimmy | No generic pickup cue is confirmed. Do not reuse the borrowing or ring sound for them. |

### 8.2 Traps and damage

| Trigger | Sound and boundary |
|---|---|
| Trapped surface chest, trapped dungeon chest, or failed reagent mix | On entry to the shared trap resolver, before trap-class selection, play the 75-update 100..500 Hz rumble. A refusal or cancellation that never enters the resolver is silent. |
| Ordinary damage presentation | The shared damage presentation runs the 160-update 100..2000 Hz rumble. Preserve the caller's own damage/narration order; this is not a global sound for every HP write. |
| Stonegate trapdoor scripted death | After the black viewport fill, play every integer frequency from 1000 down through 251 Hz, 750 tones total, holding each for 40 calibrated units. Stop, then play one 75-update 100..500 Hz rumble for each party member as that member is killed and the stats panel is repainted. |

### 8.3 Spells, projectiles, and supernatural actors

The ordinary spell presentation is committed only after the spell's own input
gate accepts. A direction or combat-cursor cancellation that the spell spec
places before its sound skips the shared variant. For combat cursor spells,
confirmation plays the spell effect before the coordinate/projectile-impact
resolver. There is no second universal per-cell projectile sound; actual damage
may subsequently invoke the damage rumble.

| Trigger | Sound and boundary |
|---|---|
| Common committed spell pre-effect | Use the named spell's variant from Section 6. It brackets the viewport inversion and blocks until both envelopes and restoration complete. |
| Common spell failure tail | After `Failed!`, play the 50-update 800-to-2000 Hz cast-failure glissando. |
| Vanish success | Vanish first runs variant 1 when direction input commits. After the accepted tile rewrite, `POOF!`, dirtying, and redraw, it plays the 40-update action snap. Pass is silent. A nonmatching tile retains the earlier variant-1 presentation, then reaches the common failure tail. |
| Monster possession success | After possession narration, run software envelope `(delta 2, initial comparison 1000, 30000 iterations, idle 1, period 3100)`. Resistance skips this success envelope. |
| Monster summon success | After successful placement and narration, run `(15, 1000, 5000, 1, 2760)`, then perform the summon tile flash. Failed chance, coordinate, legality, or allocation gates are silent. |
| Player Summon | The committed cast uses its shared spell variant. An accepted placement additionally runs `(5, 500, 12000, 1, 2760)` before actor finalization. Cancellation before commit is silent. |
| Moongate transit | During an accepted transit, run `(2, 2000, 30000, 1, 5900)`. No destination handoff means no transit envelope. |

### 8.4 Shrines, Words of Power, and major flashes

Shrine restoration, a recognized Word of Power, Shadowlord destruction, and
several other momentous presentation callers share a turbulent full-viewport
flash with a continuous low rumble.

The routine performs eight rounds of four 58-band sweeps, for 1856 band draws
and 1856 frequency changes. Every band consumes one gameplay-PRNG draw and
selects an inclusive frequency from 19 through 150 Hz. There is no explicit
audio delay; raster work spaces the retunes. The speaker stops after the final
band.

Muting suppresses each tone start but does not skip the drawing or any of the
1856 gameplay-PRNG advances. Unlike the random-rumble family, replacing this
pitch sequence is safe for gameplay parity only if the implementation still
consumes the same gameplay random draws at the same boundary.

The recognized-Word effect occurs before the location-specific success test,
so a known Word spoken at the wrong place is still audible and visible. A
successful ruined-shrine restoration invokes the shared effect again at its
own success boundary.

### 8.5 Dungeon presentation and Codex boundary

In ordinary-flavour dungeons, a five-stage animated wall droplet plays the
depth-dependent glissando from Section 5.2 only when it reaches landing stage
5, then resets to stage 0. The four depth bands produce 20, 12, 4, or zero tone
updates. The no-tone far-depth case still performs the final speaker stop.

This is a wall-decoration cue, not a Codex-glow cue. The Codex approach
transcript itself has no speaker call. A similarly named Sceptre-reclaimed
envelope elsewhere in the game is unrelated and must not be attached to Codex
approach.

Ordinary dungeon walking and turning are silent. A walking or turning redraw
may incidentally advance an already-eligible wall decoration to its landing
stage; that event owns the sound, not the movement command.

### 8.6 Intro and scripted presentation

| Trigger | Sound and boundary |
|---|---|
| First EGA rectangle dissolve while its driver-local gate is still enabled | Every second visited pixel advances a driver-local sound state and emits a progress-dependent click/hiss. The same points poll keyboard status. A pending key aborts after the current copied pixel and the abort stops the speaker. The first ordinary glyph draw permanently disables this gate, so later dissolves in the same run are silent and cannot be aborted through this gate. |
| Return-to-View strip 2 | Each scheduled inner tick runs rumble `(20, 60, 10000)`, exactly three random pitches in 100..10000 Hz. The enclosing tick is BIOS-clock paced. |
| Return-to-View strip 3 | At local phase 0 play a 3000 Hz blocking tone for 3 calibrated units; at phase 4 play 2000 Hz for 3. The enclosing tick remains BIOS-clock paced. |
| Harpsichord digit puzzle | Each accepted digit plays its digit-specific note only while sound is enabled. Ordinary name or text typing does not reuse this behavior. |

### 8.7 Endgame

When a Dead party member is restored for the endgame tableau, the sequence
announces the restoration, fills the gameplay rectangle once, runs software
envelope `(1, 5000, 40000, 1, 8800)`, and redraws the full stats panel. It is a
single blocking flourish per restored member.

The later box/tableau presentation uses envelope
`(1, 10000, 50000, 1, 5200)`. A two-part rumble call physically present after
the certificate is unreachable behind the shipped terminal infinite loop and
is not a live endgame trigger.

These are ending presentation effects. They do not create a reusable
resurrection-service sound contract and do not make the cinematic roster
changes durable.

## 9. Explicit silence boundaries

The following actions have no universal acknowledgement sound in the analyzed
baseline:

- start/menu navigation and menu acceptance;
- character-name entry and ordinary line editing;
- successful top-down walking;
- ordinary dungeon walking and turning;
- generic successful commands;
- generic active-object and crop pickup; and
- the Codex approach transcript.

Specific handlers can still produce a listed effect after one of these actions.
For example, blocked top-down movement beeps, a dungeon redraw can land a wall
droplet, and a command can commit a spell or trap. Those event-specific calls
do not imply menu clicks, footsteps, key clicks, or a global success chime.

## 10. Sources and confidence

The single-channel model, timer divisor rule, calibrated mute behavior,
glissando interpolation, random-rumble state separation, software-envelope
recurrence, shared variant table, and shipped-code caller census were derived from
private executable and overlay analysis under
`u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/functions/CAST_OVL/`,
`u5-decomp/functions/CAST2_OVL/`, `u5-decomp/functions/COMSUBS_OVL/`, and
`u5-decomp/notes/`.

The intro-driver effects were derived independently from private EGA-driver
analysis under `u5-decomp/functions/EGA_DRV/` and `u5-decomp/notes/`. The
blocked movement, trap, dungeon decoration, conversation warning, ring,
Stonegate, Return-to-View, and endgame trigger boundaries were cross-checked
against their owning overlay analyses under `u5-decomp/functions/`.

Confidence is high for the numeric inputs, step counts, trigger/cancellation
order, random-stream ownership, and mute behavior. Exact host-audio spectra for
the software envelope remain machine-calibration dependent; the phase and
comparison recurrence is the strongest source-independent contract.
