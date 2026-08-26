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
- a software envelope runs a matched silent timing loop;
- all of these still perform their final speaker stop.

The practical contract is that Ctrl-S changes output, not command or animation
cadence. A silent frontend may omit physical synthesis, but it must preserve
the effect's blocking and state-advance behavior.

One correction to that invariant. Blocking tones, glissandi, and random rumble
are genuinely mute-invariant in duration: their mute checks gate only the
tone-start work and never the calibrated wait. The **software envelope is not**.
Its silent arm is matched in structure and iteration count but not in cost per
iteration; it omits the comparison and the speaker-control work and therefore
runs about **23 percent faster** than the audible arm. Earlier revisions
described it as a matched no-output timing arm without that qualification; that
is withdrawn. Section 10 gives the resulting difference in scene length, which
is real and audible in pacing terms even though it is silent.

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

Two facts from `timing.md` govern every calibrated figure in this document, and
neither needs repeating in the recipe sections:

- **There is one delay context, and its shift is zero** (`timing.md` section
  6.1). Every calibrated wait named below spins the full boot calibration count
  per outer unit. Do not model per-effect delay contexts; there are none. The
  random-rumble and software-envelope scales are fixed subdivisions of the same
  unit, not further contexts (`timing.md` section 6.2), and `timing.md` section
  6.3 lists which class each recipe uses.
- **One outer calibrated unit is about 0.88 ms, plus or minus 10 percent**
  (`timing.md` section 7.1). That figure is a static derivation for the original
  reference machine, not a measurement. Section 10 below applies it to every
  named effect.

Wherever this document states a duration in milliseconds or seconds it is
applying that anchor and inherits its tolerance. The counts, frequencies, and
orderings remain exact.

## 5. Sound families

### 5.1 PIT tone

A requested frequency `f` in hertz selects the integer timer divisor
`floor(1,193,182 / f)`. The low and high divisor bytes are installed and the
speaker is enabled. A stop operation unconditionally disables it.

A blocking tone is `(hold, frequency)`: begin the frequency, wait `hold` outer
calibrated units, then stop. Muting omits the audible begin but retains the wait
and stop, and does not change the duration.

The wait uses the single delay context of `timing.md` section 6.1, so the hold
is `hold x 0.88 ms` to within the anchor's tolerance. Earlier revisions of this
sentence named "delay context 1" as though other contexts existed; no other
context is reachable in the shipped game and that wording is withdrawn.

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

**In real time.** The per-update wait is `delay` outer units in the single delay
context, and each update also pays about 0.12 ms of retune and loop bookkeeping.
One update therefore costs `delay x 0.88 ms + 0.12 ms`, which for the common
`delay = 1` recipes is a convenient **1.00 ms**. The three recipes above run
about **40 ms**, **50 ms**, and **20 / 12 / 4 / 0 ms** respectively. Section 10
collects these with their tolerance.

### 5.3 Random rumble

Random rumble is `(step, target, maximum_frequency)`. Its accumulator starts at
zero. Each iteration:

1. advances a private sound-only jitter state;
2. chooses an inclusive frequency from `100..maximum_frequency` Hz;
3. installs that timer divisor;
4. waits `step` outer passes, each of `floor(boot_calibration / 16)` inner
   units; and
5. adds `step` to the accumulator.

The effect stops after `ceil(target / step)` iterations and then disables the
speaker. The private jitter state starts from the same fixed nonzero value on
each program run and is not the gameplay PRNG. A deterministic frontend may
replace its sequence freely, provided it does not use or perturb gameplay
randomness and preserves the frequency range, iteration count, and timing.

The `floor(boot_calibration / 16)` subdivision is a fixed scale, not a second
delay context (`timing.md` section 6.2), and the division truncates. On
reference-class hardware it evaluates to exactly **5** inner units across the
whole plausible calibration band (`timing.md` section 7.3), so one step unit
costs about **60 microseconds** and one iteration also pays about 130
microseconds of jitter, divisor, and accumulator work.

**In real time** the total is therefore, to within the anchor's tolerance:

```text
duration = target x 60.5 microseconds + iterations x 130 microseconds
```

Note that this depends on `target` and only weakly on `step`, because the number
of outer passes is `ceil(target / step) x step`, which is `target` rounded up to
a whole step. A recipe with a large step is not faster; it is coarser.

Common recipes are:

| Use | Step | Target | Inclusive pitch range | Updates |
|---|---:|---:|---:|---:|
| Trap or failed reagent mix | 40 | 3000 | 100..500 Hz | 75 |
| Ordinary damage presentation | 10 | 1600 | 100..2000 Hz | 160 |
| Shared potion/wind lead, variant `v` | 800 | `8000 + 1600v` | 100..700 Hz | 10 through 26 for variants 0 through 8 |
| Short two-part sting | 1, then 1 | 25, then 25 | 100..1000 Hz, then 100..1500 Hz | 25 + 25, separated by a 20-unit calibrated silent hold |

### 5.4 Software envelope

The envelope generator does not interpret one argument as a frequency in
hertz. One envelope is described by:

- signed comparison delta;
- initial unsigned comparison value;
- iteration count;
- idle count; and
- phase period.

The phase starts at zero. On each iteration it adds the phase period modulo
65536, compares that unsigned phase with the moving comparison value to choose
the connected or disconnected speaker state, and advances the comparison value
by the signed delta modulo 65536. The per-iteration idle work is the idle count
multiplied by `floor(boot_calibration / 24)` when calibration is at least 100;
below that threshold the inner factor becomes zero.

This recurrence is the exact clean equivalent, and it is the strongest
source-independent part of the contract. The rest of this section publishes what
it sounds like, which is a separate and weaker class of claim.

#### 5.4.1 What actually produces the audible tone

Two facts have to be stated together, because the second is counter-intuitive.

1. The routine programs the timer's speaker channel **once per call** with a
   fixed divisor of 60. That is a carrier of about **19,886 Hz**, at or above
   the top of adult hearing and far beyond what a speaker cone can track.
2. The loop then repeatedly **connects and disconnects that running carrier**
   from the speaker. It is a gate on a carrier, not a software flip of the
   speaker pin.

> **The audible waveform is the gate pattern, not the carrier.** Perceptually
> the connected phase is a half-amplitude push and the disconnected phase is
> silence, so the ear tracks the gate rate as the pitch.

Earlier revisions of this section described the loop as changing the speaker pin
directly in a calibrated software loop. That description is withdrawn. A
frontend that synthesises the envelope as a pin-toggle at the loop rate will be
about four octaves wrong.

#### 5.4.2 The gate rate is a direct digital synthesis

The phase accumulator wraps once every `65536 / phase_period` iterations, and
each wrap is one output cycle. Therefore:

> **Exact.** `output_cycles_per_iteration = phase_period / 65536`.

For variant 0's period of 8810 that is 0.134430 cycles per iteration, one output
cycle every 7.44 iterations. Simulating the exact 16-bit recurrence reproduces
0.13450, confirming the closed form. This relation carries no timing uncertainty
at all; only the conversion from iterations to seconds does.

Two shape facts follow from the same recurrence and are worth implementing:

- **The sweep changes duty cycle, not pitch.** Across variant 0's first envelope
  the connected fraction falls from about 91 percent to about 55 percent; the
  paired second envelope runs the same rate with the duty rising back from about
  55 percent to about 91 percent, so the pair fades in and out rather than
  sliding in pitch. Pitch is essentially constant throughout.
- **The opening of the first envelope is sparse.** While the moving comparison
  value is still below the phase period, many wraps produce no disconnected
  sample at all, so the effective rate is only about 64 percent of nominal and
  the character is a sparse click train rather than a tone. It locks to the
  nominal rate once the comparison value passes the period, which for variant 0
  happens after roughly the first fifth of the sweep.

#### 5.4.3 The absolute rate, and what it sounds like

Converting iterations to seconds needs the loop's per-iteration cost, which is
where the uncertainty enters. On reference-class hardware the idle gate always
fires (`timing.md` section 7.2), so the idle work is zero and the iteration cost
is instruction time only:

> **Approximate.** One audible envelope iteration costs about **43.0
> microseconds** on the reference machine, about **23,300 iterations per
> second**. Modelling band 40.4 to 48.2 microseconds.

Combining that with the exact rate relation:

> ### Variant 0's envelope sounds at about **3.13 kHz**. Published band **2.8 to 3.35 kHz**.
>
> That is roughly G7, close to the ear's most sensitive region. **It is a
> piercing high whistle, not a low growl.** Nothing in this effect family is a
> rumble; the low-frequency material in the shared potion and wind sequence comes
> entirely from the random rumble that precedes it (section 6).

The band is a modelling band, not a measurement error bar, and its low end has
been widened deliberately to absorb a coarser independent estimate of the
iteration cost rather than paper over the disagreement. An implementation
**may** place its synthesised pitch anywhere in the published band. It **must
not** treat 3.13 kHz as a measured original-hardware frequency.

#### 5.4.4 The nine shared variants form an exact descending octave

Applying the same rate to the nine phase periods of section 6:

| Variant | Phase period | Rate at baseline | Ratio to variant 0 |
|---:|---:|---:|---:|
| 0 | 8810 | about 3,130 Hz | 1.000 |
| 1 | 7830 | about 2,782 Hz | 0.889 |
| 2 | 7060 | about 2,508 Hz | 0.801 |
| 3 | 6550 | about 2,327 Hz | 0.743 |
| 4 | 5950 | about 2,114 Hz | 0.675 |
| 5 | 5570 | about 1,979 Hz | 0.632 |
| 6 | 5180 | about 1,840 Hz | 0.588 |
| 7 | 4820 | about 1,712 Hz | 0.547 |
| 8 | 4480 | about 1,592 Hz | 0.509 |

> **The ratio column is exact.** It is the ratio of two published program
> constants and carries no timing uncertainty whatever. Only the absolute scale
> carries the plus-or-minus-8-percent band, and it scales the whole column
> together. An implementation that transposes the family must transpose it as a
> unit.

The nine periods span very nearly exactly one octave, 8810 divided by 4480 being
1.967, in near-semitone steps. That the shipped table produces a clean
descending octave under this model, and nothing musically recognisable under any
other reading of the recurrence, is the strongest available evidence that
`iteration_rate x phase_period / 65536` is the intended pitch. **All nine are
whistles. None is a growl.**

The other named envelopes in sections 8.3 and 8.7 follow the same relation:
period 2760 gives about 980 Hz, period 3100 about 1,101 Hz, period 5200 about
1,847 Hz, period 5900 about 2,096 Hz, and period 8800 about 3,126 Hz. Those
absolute figures inherit the same band; their ratios to each other are exact.

#### 5.4.5 Machine dependence, and the muted arm

The idle gate is deliberate speed compensation, and it works: on hardware fast
enough that instruction time approaches zero the iteration period tends toward
pure idle work and the rate settles around 3.3 to 3.8 kHz, while on the
reference machine the instruction time alone lands at 3.13 kHz. Reference-class,
AT-class, 386 and 486 machines all land inside roughly 2.5 to 3.8 kHz. The one
badly behaved region is machines just above the gate threshold, where both terms
contribute; a hypothetical 8 MHz 8-bit-bus turbo machine would run about a fifth
flat. Those machines are the outlier and a modern frontend should ignore them.

**Muting.** As section 3 records, the silent arm is not cost-matched. It omits
the comparison and the speaker-control work and runs at about **33.3
microseconds** per iteration instead of 43.0, so a muted envelope is about 23
percent shorter than the audible one. The iteration count, the recurrence, and
the blocking boundary are unchanged; only the wall-clock length differs. Section
10 gives the effect of this on the shared potion and wind sequence.

A host synthesizer may replace the waveform with a perceptually equivalent gated
tone, but the trigger, the opposing sweep directions, the iteration count, the
relative pitches, and the blocking duration remain normative.

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

Section 5.4.4 gives each variant's audible rate; section 10.3 gives each
variant's wall-clock length. One boundary must be stated here, because it caps
what can honestly be published about this sequence:

> **Unresolved.** The two viewport inversions in steps 2 and 5 are
> display-driver blits. Their cost scales with video bandwidth and with the
> driver's own inner loop, and does not derive from the calibration constants
> under any model, so it is not recoverable from timing analysis. Every duration
> published for this sequence is therefore the **audio-timed total only**: a
> lower bound plus two unknown terms. Resolving it needs a separate pass over the
> driver's invert path, or a capture.

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
inversions, but does not preserve the scene's length: the two envelope loops run
about 23 percent faster when silent, so a muted potion runs measurably shorter
(sections 3, 5.4.5, and 10.3). `catalogs/item-list.md` owns the later colour-specific gameplay
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

Two hundred outer units is about **176 ms**, a little over three BIOS ticks.
This is the reference cue for the whole anchor: if the blocked-step beep reads
as a roughly two-tenths-of-a-second bump in play, every other duration in
section 10 scales correctly from it.

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
| Stonegate trapdoor scripted death | After the black viewport fill, play every integer frequency from 1000 down through 251 Hz, 750 tones total, holding each for 40 calibrated units. Stop, then play one 75-update 100..500 Hz rumble for each party member as that member is killed and the stats panel is repainted. The tone count and the loop bound are exact; under the section 4 anchor the sweep alone runs about **26.5 seconds**, which is far longer than the effect intuitively sounds. Section 10 marks that figure as derived and unverified. |

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

## 10. Wall-clock durations of the named effects

This section applies the anchor of `timing.md` section 7 to every effect named
above, so a frontend does not have to redo the arithmetic. It exists because
"200 calibrated units" is not implementable on its own.

**Read the confidence labels.** Every duration here is a static derivation, not
a measurement: nothing in this section was observed on original hardware or in a
cycle-accurate emulator. What is exact and what is approximate splits cleanly:

| Class | Confidence |
|---|---|
| Outer counts, update counts, iteration counts, tone counts, frequencies, ordering | **Exact.** Program constants. |
| Every duration in milliseconds or seconds below | **Approximate**, plus or minus 10 percent, inheriting `timing.md` section 7.1. |
| Ratios between two durations in the same family | Better than the absolute figures, because the anchor cancels. |
| The two potion viewport inversions | **Unresolved.** Not derivable; see section 6. |

An implementation may vary any duration below within its stated band. It must
not vary the counts.

### 10.1 Blocking tones and direct calibrated waits

One outer unit is about 0.88 ms.

| Effect | Outer units | Duration | Band |
|---|---:|---:|---|
| Blocked step / blocked combat attack beep, 165 Hz (section 7.4) | 200 | **176 ms** | 166 to 183 ms |
| Two-tone "not here" pair, each of its two tones | 150 each | **132 ms each** | 125 to 138 ms |
| Two-tone sting inter-part silent gap (section 5.3) | 20 | **17.6 ms** | 16.6 to 18.3 ms |
| Return-to-View strip 3 blip, each phase (section 8.6) | 3 | **2.6 ms** | 2.5 to 2.8 ms |
| Projectile flight animation, per step | 40 | **35.3 ms** | 33 to 37 ms |
| Stonegate trapdoor descending sweep, per tone (section 8.2) | 40 | **35.3 ms** | 33 to 37 ms |
| Stonegate trapdoor descending sweep, all 750 tones | 30,000 | **about 26.5 s** | see 10.5 |
| Title-sequence publication wait, sounded branch (section 7.1) | 45 driver-local | **41.3 ms** | 38 to 45 ms |
| Title-sequence publication wait, silent branch (section 7.1) | 50 driver-local | **45.9 ms** | 42 to 50 ms |
| Title-sequence ignition burst, all 25 pitch holds | 25 at the rumble scale | **about 3.7 ms** total | 3.4 to 4.0 ms |

The driver-local unit is about 0.92 ms rather than 0.88 ms; `timing.md` section
7.4 explains why.

### 10.2 Glissandi and rumbles

A glissando update costs `delay x 0.88 ms + 0.12 ms`.

| Recipe | Updates | Per update | Total |
|---|---:|---:|---:|
| Action snap, span 40, delay 1 | 40 | 1.00 ms | **40 ms** (36 to 44 ms) |
| Cast failure, span 50, delay 1 | 50 | 1.00 ms | **50 ms** (45 to 55 ms) |
| Dungeon wall drip, spans 20 / 12 / 4 / -4, delay 1 | 20 / 12 / 4 / 0 | 1.00 ms | **20 / 12 / 4 / 0 ms** |

A rumble costs about `target x 60.5 microseconds + iterations x 130
microseconds`.

| Recipe | Iterations | Total |
|---|---:|---:|
| Trap or failed reagent mix, step 40, target 3000 | 75 | **190 ms** (180 to 200 ms) |
| Ordinary damage presentation, step 10, target 1600 | 160 | **118 ms** (112 to 124 ms) |
| Shared potion/wind lead, variant 0, step 800, target 8000 | 10 | **485 ms** (455 to 515 ms) |
| Shared potion/wind lead, variant `v` | 10 + 2`v` | **485 ms plus about 97 ms per variant step** |
| Two-tone sting, each half (step 1, target 25) | 25 | **about 4.8 ms** |
| Two-tone sting, whole effect | 25 + 25 | **about 9.5 ms**, plus the 17.6 ms gap between the halves, so about **27 ms** end to end |
| Return-to-View strip 2, step 20, target 60 | 3 | **about 4.0 ms** |

The trap rumble's band is narrower than its inputs suggest. Its inner count
would fall from 5 to 4 only at a calibration count of 79 or below, which is
outside the derived baseline band, so the truncation cannot flip and the
duration cannot jump (`timing.md` section 7.3).

### 10.3 Software envelopes

An audible envelope costs about `iterations x 43.0 microseconds`; muted, about
`iterations x 33.3 microseconds`. At baseline the idle gate always fires, so an
envelope's idle count does not affect its baseline duration.

| Envelope | Iterations | Audible | Muted |
|---|---:|---:|---:|
| Shared variant 0 (each of the pair) | 10,000 | **430 ms** | about 333 ms |
| Shared variant 1 | 14,000 | **602 ms** | about 466 ms |
| Shared variant 2 | 18,000 | **774 ms** | about 599 ms |
| Shared variant 3 | 22,000 | **946 ms** | about 733 ms |
| Shared variant 4 | 26,000 | **1.12 s** | about 866 ms |
| Shared variant 5 | 30,000 | **1.29 s** | about 999 ms |
| Shared variant 6 | 34,000 | **1.46 s** | about 1.13 s |
| Shared variant 7 | 38,000 | **1.63 s** | about 1.27 s |
| Shared variant 8 | 42,000 | **1.81 s** | about 1.40 s |
| Monster possession success (section 8.3) | 30,000 | **1.29 s** | about 999 ms |
| Monster summon success (section 8.3) | 5,000 | **215 ms** | about 167 ms |
| Player Summon placement (section 8.3) | 12,000 | **516 ms** | about 400 ms |
| Moongate transit (section 8.3) | 30,000 | **1.29 s** | about 999 ms |
| Endgame member restoration (section 8.7) | 40,000 | **1.72 s** | about 1.33 s |
| Endgame box/tableau (section 8.7) | 50,000 | **2.15 s** | about 1.67 s |

The complete shared sequence of section 6 is its lead rumble plus both
envelopes. **These totals exclude the two viewport inversions**, which are
unresolved:

| Variant | Lead rumble | Both envelopes | Audio-timed total, audible | Audio-timed total, muted |
|---:|---:|---:|---:|---:|
| 0 | 485 ms | 860 ms | **about 1.35 s** (1.26 to 1.48 s) | about 1.15 s |
| 1 | 582 ms | 1.20 s | about 1.79 s | about 1.51 s |
| 2 | 679 ms | 1.55 s | about 2.23 s | about 1.88 s |
| 3 | 776 ms | 1.89 s | about 2.67 s | about 2.24 s |
| 4 | 873 ms | 2.24 s | about 3.11 s | about 2.61 s |
| 5 | 970 ms | 2.58 s | about 3.55 s | about 2.97 s |
| 6 | 1.07 s | 2.92 s | about 3.99 s | about 3.33 s |
| 7 | 1.16 s | 3.27 s | about 4.43 s | about 3.70 s |
| 8 | 1.26 s | 3.61 s | about 4.87 s | about 4.06 s |

The muted column is a real, mute-state-dependent difference in scene length, not
a rounding artifact: it follows from the uncompensated silent arm described in
sections 3 and 5.4.5. An implementation that reproduces mute-preserving timing
at all should reproduce this difference too, or should deliberately decide to
make both arms equal and say so.

### 10.4 One sanity check that validates the whole anchor

**The blocked-step beep should read as a bump of roughly two tenths of a
second.** If that feels right in play, every other figure in this section scales
correctly from it. If it feels wrong, the anchor is what to re-examine, not the
step counts, which are exact.

### 10.5 Two long durations that deserve a second look

Two derived figures are much longer than the effects intuitively sound. Both
follow unambiguously from loop bounds that are themselves exact, so they are
published, but both are explicitly flagged as **derived and unverified** and are
the two figures most worth an emulator run:

- **The Stonegate trapdoor descending sweep runs about 26.5 seconds.** It plays
  750 discrete tones, every integer frequency from 1000 Hz down through 251 Hz,
  holding each for 40 outer units including the retune.
- **A long glissando present in the shipped game — 660 Hz falling toward 150 Hz,
  span 7800, per-update delay 40 — runs about 6.9 seconds** across 195 updates.

If an implementation finds either implausible in play, re-check the anchor
rather than the counts.

### 10.6 Gaps in the trigger inventory found while deriving these figures

Two effects exist in the shipped game that section 8 does not account for. They
are recorded here so they are not silently lost, and both need their own
investigation rather than a timing answer:

- **An uninventoried two-tone pair**: 220 Hz then 150 Hz, 150 outer units each,
  so two 132 ms tones. Reached through a three-way selection. Its game event was
  not identified.
- **The long glissando of section 10.5** is likewise not attached to a named
  trigger in section 8.

Neither should be implemented until its trigger is established; an effect with
no known trigger cannot be placed correctly.

## 11. Sources and confidence

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
order, random-stream ownership, and mute behavior. The phase and comparison
recurrence remains the strongest source-independent contract for the software
envelope.

The wall-clock material added in sections 4, 5.4.3, and 10, and the delay-context
material it depends on in `timing.md` sections 6 and 7, is a **static timing
derivation for a documented reference machine**. It was not measured on original
hardware and was not run in a cycle-accurate emulator. Its confidence is
therefore lower than the rest of this document and is banded rather than stated
flat. The distinction that matters for an implementer is the one drawn at the
head of section 10: counts and orderings are exact program facts, durations and
absolute pitches are modelled approximations with published tolerance, and the
two potion viewport inversions are unresolved. `timing.md` section 7.6 lists the
remaining gaps and says what a single emulator run would settle.
