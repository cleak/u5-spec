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

One caller-level exception runs the other way, and it is the only one in the
shipped game. The Lord British castle harpsichord tests the sound boolean in
its own handler and, when sound is off, **skips the generator call entirely**,
so the generator's timing-matched silent arm is never reached from it. Muting
that instrument therefore removes the whole of each note's hold - about 172 ms
per keypress, about 2.2 s across the thirteen-note tune - rather than merely
shortening it. It changes timing only: the tune matcher runs identically either
way, so mute never changes the puzzle outcome. `town-mode.md` section 13.1 owns
the instrument. *This is a withdrawal of the unqualified "Ctrl-S changes output,
not cadence" reading above; see `RETRACTIONS.md`.*

For contrast, and verified in the same pass: the blocking-tone primitive that
produces the blocked-step beep tests the same boolean but gates only the tone.
Its calibrated wait and its final speaker stop run regardless, so blocked-step
timing **is** mute-invariant.

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

#### 5.4.6 Gate polarity, duty cycle, and amplitude contour

Section 5.4.2 gives the gate's *rate*. This subsection gives its *width*, which
is what makes two envelopes running at the same rate sound different. It was
added when the tuned instrument of `town-mode.md` section 13.1 was specified,
because that instrument is unimplementable without it.

> **Exact.** The carrier is connected while the phase accumulator is strictly
> above the moving comparison value, and disconnected while it is at or below
> it. The connected fraction of one output cycle is therefore
> `duty = (65536 - comparison) / 65536`, evaluated with the comparison value in
> force at that iteration.

Three consequences follow, and all three are audible:

- **The comparison ramp is an amplitude envelope, not a pitch envelope.** A
  gated carrier is a pulse train, and the amplitude of a pulse train's
  fundamental goes as `sin(pi x duty)`. A duty moving away from 50 percent in
  either direction gets quieter; a duty moving toward 50 percent gets louder.
  The pitch does not move.
- **Sign of the delta chooses swell or decay, and the starting duty decides
  which.** The shared variant pair of section 6 starts near 96 percent duty by
  the closed form - section 5.4.2 quotes about 91 percent measured, the gap
  being the drop-out described below - and ramps toward 50 percent, then back:
  it swells and fades. The harpsichord
  starts at 69.5 percent and ramps to 93.9 percent, away from 50 percent
  throughout: it decays by about 12.4 dB, which is a plucked-string contour.
- **Cycle drop-out at the extreme.** While the comparison value is below the
  phase period, some accumulator wraps produce no disconnected sample at all
  and whole gate cycles are lost. Section 5.4.2 records this at the *start* of
  variant 0's first envelope, where it thins the opening; it happens equally at
  the *end* of a falling-comparison envelope, where it thins the tail. The
  sustained pitch is unaffected in both cases: measured over a mid-envelope
  window the fundamental tracks the closed form of section 5.4.2 to better than
  one percent.

The contour is only ever as simple as the ramp. One shipped envelope - the
monster summon cue of section 8.3 - ramps its comparison value **past the
16-bit wrap**, at which point the duty jumps discontinuously. That cue's
amplitude contour is marked unresolved in section 8.3 rather than guessed.

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

### 6.1 Which caller selects which variant

> **The rule is one sentence: the variant is the tier index of the thing being
> used.** A spell supplies its own **circle**, `floor(id / 6) + 1`, so circles 1
> through 8 map to variants 1 through 8. A scroll supplies its **scroll index**,
> 0 through 7. A potion supplies its **bottle index**, 0 through 7. No spell
> uses variant 0; variant 0 is reached only by scroll index 0 and bottle 0.

The variant is not computed at the shared dispatcher - each handler passes its
own constant - but every handler agrees with the rule, and one of them branches
explicitly to preserve it (id 20, below). An exhaustive census of the shared
dispatcher across the main executable and all 23 code overlays found exactly 40
trigger sites and attributed all 40.

**The 41 spell ids that play a shared variant.** The id, rune-name, and circle
columns are keyed to `catalogs/spell-list.md`; the variant equals the circle in
every row.

| ID | Rune-name | Common name | Variant | When the variant plays |
|---:|---|---|:-:|---|
| 0 | In Lor | Light | 1 | Unconditional, after the torch radius is set. |
| 2 | An Zu | Awaken | 1 | Only if the chosen member is asleep. |
| 3 | An Nox | Cure | 1 | Only if the chosen member is poisoned. |
| 4 | Mani | Heal | 1 | Only if the heal succeeded, i.e. the target was not dead. |
| 5 | An Ylem | Vanish | 1 | On an accepted direction, **before** the removable-tile test. A matching tile additionally plays the action snap. |
| 6 | An Sanct | Open | 2 | Dungeon arm: at entry. Surface/town/combat arm: only on a successful door unlock or a successful actor-flag clear. |
| 7 | An Xen Corp | Repel Undead | 2 | Unconditional at helper entry. |
| 8 | Rel Hur | Wind Change | 2 | Through the wind setter; see section 7.3 for the one silent case. |
| 9 | In Wis | Locate | 2 | Unconditional. |
| 10 | Kal Xen | Conjure | 2 | Unconditional at helper entry. |
| 11 | In Xen Mani | Create Food | 2 | Unconditional at helper entry. |
| 12 | Vas Lor | Great Light | 3 | Unconditional, after the larger torch radius is set. |
| 14 | In Flam Grav | Fire Field | 3 | **Dungeon arm only.** The combat arm plays the combat template instead. |
| 15 | In Nox Grav | Poison Field | 3 | Dungeon arm only; combat arm uses the template. |
| 16 | In Zu Grav | Sleep Field | 3 | Dungeon arm only; combat arm uses the template. |
| 17 | In Por | Blink | 3 | Combat arm: gated on a refusal bit being clear. Surface arm: on an accepted direction. See section 9 for the silent pass. |
| 18 | An Grav | Dispel Field | 4 | In **both** arms; the combat arm requires an accepted direction first. |
| 19 | In Sanct | Protection | 4 | Through the scene-flag helper, whose first argument is the variant. |
| 20 | In Sanct Grav | Energy Field | 4 | Dungeon arm. The shared field helper special-cases this field index and supplies 4 instead of 3, specifically to keep variant equal to circle. Combat arm uses the template. |
| 21 | Uus Por | Up | 4 | Unless the scene is the Doom scene, which refuses before the sound. |
| 22 | Des Por | Down | 4 | Same Doom refusal. |
| 23 | Wis Quas | Reveal | 4 | Unconditional at helper entry. |
| 24 | In Bet Xen | Swarm | 5 | Unconditional at helper entry. |
| 25 | An Ex Por | Magic Lock | 5 | On an accepted direction. |
| 26 | In Ex Por | Unlock Magic | 5 | Whenever the direction prompt was accepted, whether or not a door was there. |
| 27 | Vas Mani | Great Heal | 5 | Target picked, not dead, and either out of combat or a combat-permission flag set. |
| 29 | Rel Tym | Quickness | 5 | Through the scene-flag helper. |
| 30 | In Vas Por Ylem | Tremor | 6 | Unconditional at helper entry. |
| 31 | Quas An Wis | Mass Charm | 6 | Through the scene-flag helper. |
| 32 | In An | Negate Magic | 6 | Through the scene-flag helper. |
| 33 | Wis An Ylem | X-Ray | 6 | Unconditional, then the visibility-recompute animation. |
| 34 | An Xen Ex | Charm | 6 | After the creature cursor (range 15) is accepted; prints `charmed!`. |
| 35 | Rel Xen Bet | Polymorph | 6 | After the creature cursor is accepted. |
| 36 | Sanct Lor | Invisibility | 7 | Unconditional. |
| 38 | In Quas Xen | Clone | 7 | After the creature cursor is accepted. |
| 39 | In Quas Wis | Peer | 7 | Unconditional, then the look helper. **Both look helpers are silent.** |
| 41 | In Quas Corp | Cause Fear | 7 | Unconditional at helper entry. |
| 42 | In Mani Corp | Resurrect | 8 | Only if the target is dead. Cancel, or a living target, is **fully silent** - the spell path's caller tag also suppresses the refusal message. |
| 43 | Kal Xen Corp | Summon | 8 | **Unconditional at placement-helper entry, before the eight-try cell probe**, so a failed placement still plays it. An accepted placement additionally runs the summon envelope of section 8.3. |
| 46 | Vas Rel Por | Gate Travel | 8 | Only after the player types a digit `1`..`8` at the moongate prompt; any other key is silent. |
| 47 | An Tym | Negate Time | 8 | Unconditional at helper entry; if an absorbing actor takes it, adds `Magic absorbed!` plus a manual envelope cue. |

**The seven spell ids that play no shared variant at all.** These do not reach
the dispatcher on any path.

| ID | Rune-name | Common name | Circle | What it plays instead |
|---:|---|---|:-:|---|
| 1 | Grav Por | Magic Missile | 1 | Combat effect template - see below. |
| 13 | Vas Flam | Fireball | 3 | Combat effect template. |
| 37 | Xen Corp | Kill | 7 | Combat effect template. |
| 28 | In Zu | Sleep | 5 | Mass-target family - see below. |
| 40 | In Nox Hur | Poison Wind | 7 | Mass-target family. |
| 44 | In Vas Grav Corp | Death Wind | 8 | Mass-target family. |
| 45 | In Flam Hur | Flame Wind | 8 | Mass-target family. |

> **Withdrawal.** An earlier revision of this section listed "Kill/Slay Living"
> among variant 6's confirmed uses. That is wrong twice over: Kill is a circle-7
> spell, and it plays **no dispatcher variant at all**. Variant 6 belongs to the
> circle-6 ids 30 through 35, of which the creature-cursor pair Charm and
> Polymorph is the likely source of the confusion. See `RETRACTIONS.md`.
> Sharing a handler *shape* with Kill does not mean sharing a *sound* with it.

**The combat effect template (ids 1, 13, 37, and the combat arm of 14, 15, 16,
20).** All three template spells are combat-only in the castability table, so
there is no non-combat branch. The cast loop stores the spell's circle in a
shared slot as soon as the incantation parses; the combat impact helper then
plays random rumble `(800, 8000 + 1600 x circle, 700)` - which is **exactly the
rumble lead of that circle's shared variant**, with the viewport inversion and
both envelopes omitted. On a resolved effect it adds a **descending** glissando,
20 updates from 1300 Hz down toward 350 Hz. Per-victim damage or kill narration
may additionally play the 40-update action snap. Which impact branch runs is
statically determined for these templates: the area-of-effect branch always
runs and the projectile branch (a 400-to-750 Hz glissando) never does.

**The mass-target family (ids 28, 40, 44, 45).** No dispatcher call. Instead:

1. one bare random rumble `(800, T, 700)` with `T` = 16000 for Sleep, 19200 for
   Poison Wind, and 20800 for Death Wind and Flame Wind. Those are again
   `8000 + 1600 x circle` - the rumble lead of the id's own circle's variant,
   without the inversion or the envelope pair; then
2. a 21-by-21 cell raster in which **every drawn cell retunes the speaker to a
   fresh pseudorandom pitch in 100..10,000 Hz and leaves it running**. A single
   tone stop fires once after the whole raster. There is no programmed delay
   between retunes, so the audible rate is the cell-draw rate.

**Scroll use is a separate presentation with its own variant.** Each scroll
decrements its own count, prints its banner, then:

| Scroll | Banner | Variant | Notes |
|---:|---|:-:|---|
| 0 | `Light!` | 0 | Sets a torch radius, then calls the dispatcher directly. |
| 1 | `Wind change!` | 1 | Through the wind setter with the **scroll** caller tag. |
| 2 | `Protection!` | 2 | Through the scene-flag helper. |
| 3 | `Negate magic!` | 3 | Through the scene-flag helper. |
| 4 | `View!` | 4 | Dispatcher, then the look helper. Refused with `Not here!` and **no sound** outside the permitted scene class. |
| 5 | `Summon Daemon!` | 5 | Through the placement helper; only in the permitted scene class, else `Not here!` and silence. |
| 6 | `Resurrection!` | 6 | Through the resurrect helper; only in the permitted scene class and only if the target is dead. |
| 7 | `Negate time!` | 7 | Through the scene-flag helper. In two specific scenes it instead prints `No effect!` and plays the 50-update cast-failure glissando. |

> **A scroll does not sound like its spell.** The scroll variant disagrees with
> the corresponding spell's variant in six of the eight cases: Light 0 against
> 1, Wind Change 1 against 2, Protection 2 against 4, Negate Magic 3 against 6,
> Summon Daemon 5 against 8, Resurrection 6 against 8. Only View and Negate Time
> coincide, at 4 and 7, and Negate Time only coincidentally. **A frontend must
> not reuse the spell's variant for the scroll.**

Potion use passes the bottle index straight through, confirming the existing
"bottle id, not effect variation, chooses the variant" contract of section 7.2.

**Two pre-commit sounds that section 8 does not list:**

- `Magic absorbed!` - in one specific scene, and in a second scene when a state
  flag is set, the cast is absorbed **before** reagents or magic points are
  spent, and plays a manual envelope cue (the same recipe as Negate Time's
  absorb branch).
- `Not here!` - a spell rejected by the castability mask plays the 50-update
  cast-failure glissando, also before commit. `M.P. too low!` and `None mixed!`
  reach the shared epilogue's `Failed!` plus the same glissando.

**Unresolved in this section, so the engine stops treating it as pending:**

- **Absolute pitch and duration of the nine variants** remain the modelled
  figures of sections 5.4.4 and 10.3, not measurements. One emulator capture of
  a known-circle cast per circle would settle the whole column at once.
- **The rate of the mass-target raster tone** is entirely a function of the
  cell-draw cost in the enclosing loop, which was not cycle-counted. It cannot
  be published as a frequency-versus-time curve.
- **How many times the circle-scaled rumble fires inside one combat spell
  resolution.** The shared circle slot is set by the cast loop, overwritten to 1
  by one combat path, and cleared by two others; the orderings were not traced.
  Once per accepted target cursor is what the code shape suggests, but that is
  **not established**.
- **The ambient audio that follows Up and Down (ids 21, 22).** Their own cue -
  variant 4, played before the level change - is direct and certain. The
  subsequent dungeon redraw sits in front of a rumble and two glissandi,
  including the depth-dependent wall drip; which of those a level change
  actually reaches was **not separated** and must not be guessed.

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

> **Withdrawal.** Earlier revisions of this section said the **previous wind
> state** chooses the variant, and gave a Calm-versus-direction transition
> matrix. Both are withdrawn; see `RETRACTIONS.md`. The old wind does not
> participate in variant selection at all.

**The variant is chosen by the caller tag, not by the wind.** The shared wind
setter takes a caller tag as its first argument, and that tag alone selects the
variant:

| Caller | Variant |
|---|:-:|
| The Wind Change spell (`Rel Hur`, id 8, circle 2) | **2** |
| The Wind Change scroll (scroll index 1) | **1** |

Both play the section 6 sequence before the new direction is committed and
announced. Neither the old wind nor the requested compass direction selects
pitch, so requesting the already-active direction still sounds, and every
accepted transition from any wind to any other sounds identically for a given
caller. Cancelling the direction prompt produces no wind sound at all, because
the cast never reaches the setter.

There is exactly one silent accepted path: a **spell**-tagged call requesting
direction "none". An out-of-range direction value falls through having already
played the sound and having set nothing - probably unreachable in the shipped
flow, but present.

> **Unresolved.** Two private passes describe the silent guard differently: one
> reads it as "spell tag and direction none", the other as "direction none and
> the current wind already Calm". Requesting "none" is necessary in both
> readings; whether the current wind must also already be Calm is **not
> settled**. A frontend that implements the narrower reading (both conditions)
> differs from the wider one only in whether a spell that calms an already-windy
> sea is audible.

**The autonomous wind drift is silent, and the engine's silent drift is
correct.** The sound belongs to the spell and scroll handlers, never to the
setter. The drift routine takes no arguments, rolls 1 in 64 and returns unless
it hits, picks a direction from five candidates, requires a further roll to
accept Calm, and then calls the setter; its only callees are three random draws
and the setter. There is no sound call, no wrapper, and no ambient hook. An
exhaustive reference sweep across all 24 code images found exactly one writer of
the wind state - the setter - and a transitive walk from the setter reaches 21
routines and **zero** sound primitives. That walk was sanity-checked against
three roots with known audio before being relied on for a negative.

Two non-audio facts fell out of the same trace and are recorded so they are not
lost. The drift passes the **raw** direction index to the setter, whereas the
spell applies a direction transform before committing (`weather.md` section 3),
so the two paths are not interchangeable. And the drift is **not a timer at
sea**: it reads no clock and tests no transport. It is a per-redraw-tick 1-in-64
roll gated only on the master-redraw flag and a first-tick handshake flag.

> **Unresolved.** The drift's **cadence** is not established. The world tick
> that hosts the roll has roughly 68 entry points across the build, and whether
> the roll runs once per game turn, once per idle keyboard poll, or somewhere
> between was not determined. It does not affect the audio answer, but a
> frontend modelling cadence from the incorrect "timer at sea" premise will get
> the drift rate wrong.

### 7.4 Blocked step: overworld, town, and combat beep; the dungeon does not

> **Withdrawal.** Earlier revisions of this section named only town and combat.
> That under-scoped the cue by one mode: **a rejected overworld step beeps too.**
> See `RETRACTIONS.md`.

**Normative scope.** Exactly four call sites in the shipped game carry the
blocked-step recipe - a blocking 165 Hz tone held for 200 calibrated units:

| Mode | Sites | Behaviour on a rejected step |
|---|:-:|---|
| Overworld | 1 | Prints `Blocked!`, beeps, flushes keyboard type-ahead - subject to the three exceptions below. |
| Town | 1 | Prints `Blocked!`, beeps, flushes type-ahead. Two refusal arms (object occupancy, tile-class refusal) share one tail. |
| Combat | 2 | The step-or-attack refusal, and the out-of-arena exit refusal that prints `All must use the same exit!`. Both beep. |
| Dungeon | 0 | **Silent.** No sound call on either refusal arm. |

Ctrl-S suppresses the tone but not the 200-unit hold. Two hundred outer units
is about **176 ms**, a little over three BIOS ticks. This is the reference cue
for the whole anchor: if the blocked-step beep reads as a roughly
two-tenths-of-a-second bump in play, every other duration in section 10 scales
correctly from it.

Successful top-down movement has no corresponding footstep sound. The beep is a
rejection cue and must not be attached to ordinary movement.

**Complete census of the blocking-tone primitive.** The primitive takes a
frequency and a hold in outer calibrated units. Every user in the shipped game:

| Event | Recipe |
|---|---|
| Overworld blocked step | 165 Hz, 200 units |
| Town blocked step | 165 Hz, 200 units |
| Combat step-or-attack refused | 165 Hz, 200 units |
| Combat exit refused, `All must use the same exit!` | 165 Hz, 200 units |
| An unidentified combat refusal, two-tone pair | 220 Hz for 150 units, then 150 Hz for 150 units |
| A Return-to-View presentation strip | 2000 Hz, 3 units |
| The ambient shrine/flame tick | 3000 Hz, 3 units |

The narration census corroborates the mode scope independently: the game
contains exactly five copies of the `Blocked!` string and exactly five pieces of
code that print one - town (beeps), overworld (beeps, conditionally), **two in
the dungeon (both silent)**, and combat (beeps).

**The overworld predicate is not simply "step refused".** After a step is
refused, whether by a blocking object or by terrain impassable for the current
transport:

1. **Under sail**, the path prints `BREAKING UP!`, `COLLISION!`, or `Docked!`.
   Docking is silent and furls the sails; the other two run the ship-collision
   rumble `(100, 2000, 300)` and then apply ship damage. **No 165 Hz beep occurs
   on any under-sail path.**
2. **Aboard a vehicle, when the blocking object is of the whirlpool class**, the
   step returns completely silently, with no message at all.
3. Otherwise the path prints `Blocked!` and then splits:
   - if the destination tile is a particular animated-terrain tile, it prints
     `OUCH!` and applies random party damage **instead of beeping**. That helper
     walks up to six party slots, skipping the dead, and each surviving member's
     damage application fires the 160-update damage rumble `(10, 1600, 2000)`.
     So this branch emits one rumble per living member in place of the beep.
   - otherwise it plays the 165 Hz / 200-unit beep.
4. Both non-whirlpool branches then flush keyboard type-ahead.

The `OUCH!` destination tile is **unidentified**: it is known only as one frame
of a four-frame animated-terrain block, and no shipped string names it. The
behaviour above is complete without the tile identity.

**Combat has a third, silent refusal.** The accepted exit arm prints `Escape!`
and plays the 40-update action snap; a third arm prints `Stay with ship!`
**silently**. Only the two refusals in the table above beep.

**The dungeon nuance a frontend will otherwise get wrong.** A blocked dungeon
step is silent, but it is not always *followed* by silence, and the difference
matters:

- The dungeon's shared post-action tail runs a redraw, and that redraw ticks a
  dungeon rumble. The tick flips a parity flag; on one phase it returns
  immediately, and on the other it emits a rumble whose target is a decaying
  intensity value, then subtracts 4 from that intensity with a floor at zero.
- Both the parity flag and the intensity value are referenced only inside the
  dungeon overlay, and the **only writer that raises the intensity is the
  committed-step path**, which sets it to 15.
- A successful dungeon step therefore emits two bursts (targets 15 then 11),
  leaving 7 behind; every later redraw - blocked steps, turns, turn-arounds -
  emits the decaying tail on alternating parity until it reaches zero.

> **The dungeon has a footstep-ish rumble attached to the *accepted* step and no
> cue attached to the *rejection*.** A frontend that ports the 165 Hz beep into
> the dungeon is **adding a sound the original does not have**.

**Unresolved in this section:**

- **Does a missed attack beep, or only a blocked step?** The combat beep fires
  when a destination-cell query returns zero, and two private analyses of that
  query directly contradict each other - one calls it the to-hit roll, the other
  a read-only cell-occupancy predicate with inverted polarity. This was **not
  adjudicated**. Until it is, the contract says "a refused combat
  step-or-attack" and **must not** assert whether a whiffed attack roll is
  included.
- **Dungeon rumble parity was not simulated.** The mechanism above is
  established; which specific blocked steps land on the emitting phase is not,
  because the parity across all redraw and tick entry points was not enumerated.
  What *is* established is that the rejection branch itself makes no sound call.
- **The two-tone 220/150 Hz combat refusal pair is still unidentified.** It is a
  refusal-shaped sound in the same subsystem as the combat blocked beep, it is
  **not** the blocked-step recipe, and its game event is unknown (section 10.6).
  Do not conflate it with the blocked step.
- **The two three-unit blips in the census.** Section 8.6 attributes both a
  3000 Hz and a 2000 Hz three-unit blip to Return-to-View strip 3, while the
  census above labels one of them an ambient shrine/flame tick. Whether these
  are two sites or one was **not settled**.

## 8. Confirmed trigger inventory

### 8.1 Commands, inventory, and conversation

| Trigger | Sound and boundary |
|---|---|
| Stolen-action warning | After the warning line and before the selected item or gold is removed, play the 40-update action snap. |
| Ring vanishes, Ready/equip path | On a 1-in-16 roll when the equipped item is a ring of Invisibility or Regeneration: print `Ring vanishes!`, destroy the item, then play the 40-update action snap. *There is no confirmation prompt; the roll is not player-visible. Any earlier text describing a cancelled confirmation is withdrawn - see `RETRACTIONS.md`.* |
| Ring vanishes, terrain-combat entry | Identical recipe and identical 1-in-16 odds, rolled once per party member carrying one of the same two ring types, inside the per-encounter seating loop whose only entry point is terrain-combat setup: print `A ring has vanished!`, play the 40-update action snap, then remove the item. An engine implementing both paths the same way is **correct**. |
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


#### 8.3.1 The summon tile flash is the shared single-cell converge

The flash that accompanies both summon cues is **neither the shared
full-viewport flash nor a bespoke effect**. It is one invocation of the engine's
shared single-cell pseudorandom pixel converge - the same primitive, the same
driver path, as the moongate tile shimmer, the Conjure and Swarm placement
flashes, the camp apparition and level-up, the Blackthorn audience appearances,
the Return-to-View and character-creation tile previews, and one command-layer
site: fourteen sites in all. **If a "single-cell tile converge" or "moongate
shimmer" contract already exists elsewhere in this specification, the summon
flash is that contract instantiated with the flash tile named below.** It needs
no separate implementation.

The monster summon and the player Summon spell use an identical construct: play
the envelope cue, set the new actor's tile to a placeholder, run the converge on
the flash tile, then set the actor's tile to the real creature sprite.

- **Region.** Exactly one 16-by-16 viewport cell - the cell where the creature
  will appear. In combat the 11-by-11 arena maps one-to-one onto the viewport
  and this trigger applies **no row bias**, unlike some other users of the same
  primitive. Nothing outside that cell is touched.
- **What is drawn.** A class-parallel *flash* tile, not the creature. The rule
  is `flash tile = creature class x 4 + 320`, and the settle tile that replaces
  it is `creature class x 4 + 64`. For the daemon the flash tile is a
  red/bright-red column with yellow highlights - a flame or gate glyph. Four
  consecutive frames exist per class.
- **Colour.** Straight per-pixel copy of the tile's own colour, one pixel mask
  at a time across four colour planes. **No XOR, no palette swap, no
  inversion.** It draws to the visible page.
- **Repetitions.** Exactly **one pass of 256 plots**, with no outer repeat: 256
  plots covering 256 distinct sub-pixels, in the pseudorandom order specified in
  `display-driver-abi.md` section 9.6. The cell is painted exactly once. It
  converges into existence rather than popping in.
- **Timing.** **No calibrated delay is involved at all.** Pacing is the 256 plot
  dispatches plus an input/redraw poll after every eighth completed step - 31
  checkpoints, and none after the final step. In combat that poll runs the world
  tick. Roughly 100 to 130 microseconds per plot dispatch gives about **25 to
  35 ms of plotting**, but the 31 world ticks are the dominant term and are
  **unpriced**. Treat the wall clock as a coarse estimate only.
- **It is not abortable here.** The abort test on a non-zero poll result exists
  **only** on the Return-to-View poll branch. On the world-tick branch the loop
  continues unconditionally and the world tick returns nothing, so in combat and
  in every non-Return-to-View scene the reveal always runs all 256 steps. *An
  earlier internal note saying it aborts "in either case" is wrong.*
- **The placeholder is not a gravestone.** All thirteen overlay users of this
  primitive pre-set the object's tile to the *same* placeholder before
  converging; it is a universal placeholder, not a summon-specific one, and a
  render of it shows a speckled terrain-like pattern with no headstone shape.

**Unresolved for the flash:**

- **Whether it reads as a smooth converge or a sparkle.** The converge writes to
  the visible page and its 31 poll checkpoints reach the viewport renderer
  unconditionally. If that repaint covers the same cell and also targets the
  visible page, the partial reveal is wiped 31 times and the effect reads as a
  sparkle; if the renderer composes into a back page, it does not. **The
  renderer's draw target was not traced, and an implementation must not be told
  which of the two it is** until someone traces it or captures the effect.
- **Wall-clock length**, per the unpriced world ticks above.
- **What the placeholder tile depicts** - identified from rendered pixels, not
  from any stored name.
- **Non-EGA drivers.** Only the EGA driver was analysed. Whether the other three
  shipped drivers implement the converge at all, consume the step counter the
  same way, or plot in the same order is **unchecked**. The "256 plots, each
  sub-pixel once" result is EGA-only.
- **Whether every creature class has a populated flash tile.** The
  `class x 4 + 320` rule was verified arithmetically for the daemon and
  cross-checked against the Conjure and Swarm rows, but two spot-checked classes
  render as recognisable, unrelated pictures. The upper tile bank is **not** a
  uniform "gate" family and the rule must not be assumed to give a sensible
  flash for every class.
- **The amplitude contour of the two summon cues.** Both sit at about 981 Hz
  (approximate, same band as every other derived envelope pitch) and last about
  215 ms and about 516 ms. But both comparison ramps are **positive**, and the
  monster cue's ramp **wraps the 16-bit comparison value partway through**, so
  the clean monotonic contour of section 5.4.6's other examples does not
  transfer. The resulting contour was **not characterised and must not be
  guessed**; simulating the exact 16-bit arithmetic would close it.

#### 8.3.2 A passed direction prompt is silent, in Blink and in Vanish alike

Outside combat, Blink asks for a direction. If the player passes with space, the
prompt returns "no direction" and the handler jumps straight to its epilogue
with the result code left at the shared *cancelled* sentinel, skipping even the
redraw helper. On a pass the handler does literally nothing: no sound, no
message, no redraw, no coordinate write. **The engine's silent Blink pass is
correct.**

The prompt itself is silent on the pass: its only non-input callee is the string
printer, and on space it prints its cancel token and returns "none". The
key-input helper it loops on has exactly three callees - a blinking-cursor poll,
a case fold, and the world tick - and makes no sound call.

The shared cast epilogue branches on the result: *success* prints a message with
no sound; *failure* prints a message **and** plays the 50-update cast-failure
glissando; and **the cancelled sentinel matches neither branch**, so it produces
no message and no sound.

Two premises that appear in older material are wrong and are corrected here:

- **Blink has no charge or mana gate of its own.** Both are spent by the shared
  cast dispatcher, before per-spell dispatch, for *every* spell id including
  Blink and Vanish: check the mixed-reagent count and abort with a message if
  zero; decrement it; check magic points against the spell's cost; subtract the
  cost; preset the result to the cancelled sentinel; then dispatch. There is no
  charge or mana operation anywhere inside the Blink handler.
- **Vanish's pass is the same shape, not a different one.** Vanish calls the
  same prompt, tests it the same way, sets the same cancelled sentinel, and
  jumps to its own epilogue; its effect cue is reached only on a real direction.
  If any text distinguishes Blink from Vanish on pass behaviour, that
  distinction is not in the code.

The one real structural difference is a **scene gate that runs before the
prompt**: Blink tests whether the scene is in the combat/dungeon class and takes
an arm that never prompts. That arm plays its effect cue unconditionally unless a
refusal bit is set, in which case it reports failure and plays the failure
glissando. **There is therefore no such thing as a Blink pass in combat.**

**Unresolved, and scoped so it is not read as a Blink behaviour:**

- **Ambient audio during any prompt.** The world tick, which runs on every key
  poll, *can* reach the speaker through the ambient shrine/flame tick. That tick
  is reached from the world tick only while a mode-entry handshake flag is
  clear - once after entering a mode, after which the same tick sets the flag.
  This is ambient audio reachable during **any** keyboard prompt and is not
  attributable to Blink or to a pass. How often the handshake flag is re-cleared
  in practice was **not determined**, and the tick's other entry points were not
  traced.
- **Depth of the negative search.** The world tick's callees were enumerated at
  depth 1 (nine targets) with their callees listed at depth 2, and only the
  ambient tick reaches a sound primitive. This does **not** cover depth 3 and
  beyond, indirect calls, display-driver code reached through the driver
  dispatch table, or interrupt handlers. The EGA driver contains its own speaker
  code, which was not checked for reachability from the viewport renderer's
  dispatch slots.
- **Whether any command layer other than the cast dispatcher offers a second
  Blink entry point** with its own resource gate. Only the cast path was audited.

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
| First EGA rectangle dissolve while its driver-local gate is still enabled | Every second visited pixel advances a driver-local pitch state and **retunes a continuously running speaker carrier**; the speaker is enabled at the first click and silenced only at the dissolve's shared exit. The same points poll keyboard status. A pending key aborts after the current copied pixel, and that exit silences the speaker. The first ordinary glyph draw permanently disables this gate, so later dissolves in the same run are silent and cannot be aborted through this gate. **Section 8.6.1 gives the full contract**; it is not a click train and its band is not 100..1500 Hz. |
| Return-to-View strip 2 | Each scheduled inner tick runs rumble `(20, 60, 10000)`, exactly three random pitches in 100..10000 Hz. The enclosing tick is BIOS-clock paced. |
| Return-to-View strip 3 | At local phase 0 play a 3000 Hz blocking tone for 3 calibrated units; at phase 4 play 2000 Hz for 3. The enclosing tick remains BIOS-clock paced. |
| Harpsichord digit puzzle | Each accepted digit plays its digit-specific note through the software envelope generator, only while sound is enabled. The note **blocks** for its full 4,000 iterations, about 172 ms, and ends in a hard silence. Muting skips the generator call outright and therefore removes the hold as well as the sound - the one caller-level exception to section 3. `town-mode.md` section 13.1 owns the ten-note table, the ascending scale, and the plucked amplitude contour. Ordinary name or text typing does not reuse this behavior. |


#### 8.6.1 The intro rectangle-dissolve click

This subsection replaces the phrase "progress-dependent click/hiss" in the row
above with a full contract. The phrase was too thin to implement from, and the
implementation it produced is wrong in three independent ways, itemised below.

> **Withdrawal.** `display-driver-abi.md` section 9.6 described the effect as
> "one short percussive speaker click" per checked visit, with the speaker
> silenced as part of that per-click behaviour. Both halves are withdrawn: the
> speaker is enabled at the first click and **nothing disables it until the
> dissolve exits**. See `RETRACTIONS.md`.

**What it is.** The dissolve's tone routine is a display-driver-local clone of
the resident random-rumble primitive. It owns five words of driver-local state.
At the shipped driver image the pitch state is 30308, the band-width counter is
240, the pitch budget is 1, and the per-pitch delay is 1.

**How the pitch state advances.** Exactly, all arithmetic modulo 65536:

```text
state = rotate_right_16(state + 37448, 3)
state = state XOR 37448
state = state + 17
```

This is bit-for-bit the recurrence of section 7.1, published in hexadecimal in
`intro.md` section 5, from the same seed. Simulated from the shipped seed it is
a **pure cycle of period 47,343 with no tail**, so across the 16,160 clicks of
the effect no value ever repeats.

**How a state becomes a frequency.** With `n` the band-width counter:

```text
span      = floor(n / 2) - 99
frequency = 100 + (state modulo span)
divisor   = floor(1,193,182 / frequency)
```

The emitted frequency is therefore a pseudorandom integer in `100..floor(n/2)`
Hz, **with the modulo bias of that formula baked in**. An implementation that
substitutes a uniform draw runs about 6 percent low at the top end; the decile
table below already includes the bias.

**Relationship to the subtitle ignition, which is both "same" and "different".**
The distinction matters and has been got wrong:

- The **pitch** state is literally the same state word advanced by the same
  code, because the dissolve and the ignition share one routine. It is never
  re-seeded, so the dissolve's 16,160 steps leave it 16,160 positions along its
  cycle before the ignition burst ever fires.
- The ignition's **click-gating** recurrence - low nine bits against a threshold
  decaying from 400 by 3 (section 7.1) - is a *separate* state word running the
  identical formula. The dissolve has no counterpart: it clicks unconditionally
  on every second visited pixel. The same formula appears a third time elsewhere
  in the driver on a third independent state word.
- The two effects diverge in the **band parameter, not the generator**: the
  ignition pins the band-width counter to 3000 before every burst, fixing its
  band at 100..1500 Hz forever, while the dissolve lets the counter free-run
  upward.

Because the dissolve runs before the ignition in the intro's step order, at the
one gated dissolve in the game all five words still hold their shipped-image
values. **The entire click sequence is deterministic and exactly reproducible.**

**What "progress-dependent" means.** Not the fraction of the rectangle copied,
and not the pixel coordinate. It is the driver's own **click counter** - the
band-width counter - incremented by one immediately after each click. Three
properties matter:

1. It counts **clicks**, that is every second visited pixel, not pixels.
2. It is **never reset by the dissolve**. It is a driver-global that starts at
   its shipped value of 240 and only grows, or is overwritten with 3000 by the
   ignition. "Progress" is progress **since driver load**; it coincides with
   progress within the rectangle only because the intro logo dissolve is its
   first user.
3. It feeds **only the upper band edge**. The lower edge is a hard-coded 100 Hz
   for the entire effect, first click to last.

> A latent hazard worth knowing when reimplementing: the span formula divides by
> `floor(n/2) - 99`, which is 21 at `n = 240`. At `n = 200` it would be zero - a
> divide fault - and below 200 it goes negative and, read as unsigned, lets the
> frequency fall under 19 Hz and overflow the second division. This is
> unreachable in the shipped flow because `n` only rises, but it explains why the
> shipped value is 240 rather than 0.

**It is not a pin toggle and not a train of discrete clicks.** The routine turns
the speaker on at every click and nothing turns it off until the dissolve exits;
the single silencing point sits on the dissolve's shared exit block, reached by
both the abort path and normal completion. There *is* a calibrated hold per
click, but it is negligible: one outer unit at the shift-four subdivision, the
same scale as the random-rumble step of section 5.3, so roughly **50 to 60
microseconds**, invariant across the plausible calibration band.

> **Correct model: the speaker's square wave runs continuously from the first
> click to the end of the dissolve, and is retuned to a fresh pseudorandom
> frequency every second visited pixel.** The "hiss" is neither a train of
> discrete clicks nor the raw copy rate - it is one continuous waveform whose
> frequency is randomised at the retune cadence.

**Direction and range: it rises and widens; it does not sweep.** For the one
gated dissolve in the game the rectangle is 320 by 101, that is 32,320 pixels.
Simulating the visit order gives 32,320 helper invocations and, by the
every-second-pixel parity, exactly **16,160 clicks**. The band-width counter
therefore runs 240 to 16,399 and the **top** band edge runs 120 Hz to 8199 Hz.
The **bottom edge stays at 100 Hz throughout**.

Exact emitted-frequency statistics, from simulating the real arithmetic
including the modulo bias:

| Progress | Band (Hz) | Mean | Median | p10 | p90 |
|---|---|---:|---:|---:|---:|
| 0-10 % | 100..927 | 311 | 264 | 121 | 583 |
| 10-20 % | 100..1735 | 706 | 682 | 226 | 1244 |
| 20-30 % | 100..2543 | 1104 | 1084 | 314 | 1944 |
| 30-40 % | 100..3351 | 1509 | 1508 | 360 | 2645 |
| 40-50 % | 100..4159 | 1875 | 1856 | 438 | 3382 |
| 50-60 % | 100..4967 | 2362 | 2383 | 604 | 4074 |
| 60-70 % | 100..5775 | 2670 | 2668 | 583 | 4744 |
| 70-80 % | 100..6583 | 3086 | 3110 | 658 | 5521 |
| 80-90 % | 100..7391 | 3473 | 3442 | 799 | 6198 |
| 90-100 % | 100..8199 | 3964 | 4033 | 882 | 7019 |

The first ten emitted frequencies are exactly **118, 105, 101, 110, 108, 113,
113, 123, 123, 117 Hz**. The overall mean across the run is 2106 Hz, and
**52 percent of clicks exceed 1500 Hz**.

Closed form for any rectangle, independent of size, for click `k` counting from
zero:

```text
n_k        = 240 + k
frequency  = 100 + (pitch_state_k modulo (floor(n_k / 2) - 99))
band top  ~= 120 + k / 2
mean      ~= 110 + k / 4
```

A gated rectangle of `P` pixels produces `ceil(P / 2)` clicks and ends at a band
top of about `P / 4 + 120` Hz.

> **Three specific errors in the common implementation.** A frontend that models
> this as a linear frequency sweep from 100 Hz to 1500 Hz is wrong in three
> independent ways, and 100..1500 Hz is not even this effect's band - it is the
> fixed band of the *subtitle ignition* (section 7.1), apparently borrowed, with
> the random draw turned into a sweep.
>
> 1. **It is not a sweep.** Every click is an independent pseudorandom draw
>    across the *whole current band*, and the low edge stays pinned at 100 Hz
>    from first pixel to last. A rising sweep sounds like a slide whistle; the
>    original is a rising, broadening rasp with low pops scattered through it
>    right to the end.
> 2. **The top is wrong by a factor of 5.5** - about 8.2 kHz, not 1.5 kHz. Half
>    the clicks are above 1500 Hz.
> 3. **The start is too high and too wide.** The first roughly 1600 clicks, ten
>    percent of the effect, never leave 100..930 Hz and cluster near 260 Hz.

**Timbre evolution, and the assumption it rests on.** Early in the run the
programmed half-period (about 4 to 5 ms at 100 to 120 Hz) is much longer than
the retune interval, so under square-wave-mode reload rules most writes are
superseded before the counter reaches zero and only the last write before each
zero crossing takes effect. By mid-dissolve the half-period (about 120 to 250
microseconds) is shorter than the retune interval and essentially every write
lands. The texture therefore evolves from a low irregular buzz into genuine
broadband noise, independently of the band-edge growth. This paragraph is
**conditional on the reload semantics in the unresolved list below**.

**Unresolved, and stated so the engine stops treating any of it as pending:**

- **Wall-clock retune cadence and total duration are not established.** A
  hand-built cycle model gives roughly **0.5 to 1.0 ms per retune** (about a 1
  to 2 kHz retune rate) and a total run of roughly **8 to 14 s** for the
  32,320-pixel logo rectangle. Those figures omit display-memory wait states on
  the read-modify-write plane accesses (not modelled at all), bus wait states on
  the fourteen port writes per pixel, memory-refresh steal, and the firmware
  keyboard-poll handler cost. **Treat them as unverified.** The structure above
  is exact; only the wall clock is not. One cycle-accurate emulator run with an
  audio capture is the only thing that will settle it.
- **The actual audible waveform**, and with it the timbre paragraph above,
  follows from the same run.
- **Timer mode and access latch are assumed, not verified.** The driver never
  writes the timer's mode register, so the mode is inherited from firmware. The
  frequency table above **assumes** conventional square-wave mode with
  low-then-high byte access. If the latch were low-byte-only, the second byte
  write would be read as a fresh low byte and the whole pitch analysis collapses
  to something else.
- **Reload semantics under fast rewrite.** The claim that early writes are
  mostly superseded rests on the standard rule that a new count loads at the end
  of the current half-cycle. Which behaviour a given emulator or chip revision
  exhibits was not verified, and it materially changes the low-progress timbre.
- **Non-EGA display drivers were never opened.** Only the EGA driver was
  analysed. Whether the other three shipped drivers carry the same tone routine,
  the same parameter block, the same shipped values, or the same behaviour is
  **unknown**. Nothing in this subsection may be generalised to a non-EGA
  install.
- **Whether the effect is audible at all in the shipped flow.** This subsection
  relies on the published finding that the driver's sound/abort gate is still
  set at the intro logo dissolve, the gate being cleared only by the driver's
  text-glyph path. The gate references, the clear, and the loader's step order
  were re-confirmed, but **boot-time output - driver load, machine detection, a
  disk-swap prompt - was not audited** for an earlier text dispatch. If any text
  is drawn through the driver before the intro, the first dissolve is silent and
  this whole subsection describes an unreachable path. The other rectangle
  dissolves in the game all occur after menu text and are, on the same finding,
  silent; that was not re-verified per site.
- **Interrupt jitter.** Whether a timer interrupt handler is live during the
  intro dissolve, and what it does to a run of this length with a continuously
  gated speaker, was not determined.

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
- generic active-object and crop pickup;
- the Codex approach transcript;
- **a rejected dungeon step**, on either refusal arm (section 7.4);
- **the autonomous wind drift**, on every path (section 7.3);
- **a passed direction prompt**, in Blink and in Vanish alike (section 8.3.2);
- the combat `Stay with ship!` refusal, and the overworld dock and
  whirlpool-class refusals (section 7.4); and
- both look/peer helpers, and a `Not here!` refusal of the View or Summon
  Daemon scroll (section 6.1).

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
| Harpsichord key note (`town-mode.md` 13.1) | 4,000 | **172 ms** | **no note at all** - the handler skips the call |

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

## 11. Caller scope index

Section 8 says what each cue sounds like. This section says **exactly which
callers produce it**, because scope has repeatedly been inferred from a section
heading and inferred wrongly. Every row is normative. Where a row's scope is
narrower or wider than an earlier revision of this document, the change is
listed in `RETRACTIONS.md`.

| Cue | Produced by | Explicitly **not** produced by |
|---|---|---|
| Blocked-step beep, 165 Hz for 200 units | Exactly four sites: one overworld, one town, two combat (step-or-attack refused; out-of-arena exit refused). See section 7.4. | The dungeon, on either refusal arm. Any under-sail refusal. A whirlpool-class refusal aboard a vehicle. The overworld `OUCH!` branch, which rumbles instead. Successful movement in any mode. |
| Action snap, 40 updates 1200 toward 2000 Hz | The stolen-action warning; the Ready-path ring destruction; the combat-entry ring destruction; the Jimmy key break; the borrowed fixed object; a matching Vanish tile; the accepted combat exit (`Escape!`); per-victim combat damage or kill narration. Eight further sites share the recipe; it is the generic action snap, not a ring-specific sound. | Ordinary pickup, crop pickup, or a successful Jimmy. |
| Shared variant sequence (section 6) | 41 of the 48 spell ids, at variant = circle; all 8 scrolls, at variant = scroll index; all 8 potions, at variant = bottle index. | The seven spell ids of section 6.1's second table - the three combat effect-template spells and the four mass-target spells - on any path. The combat arm of the four field spells. |
| Summon tile flash | The monster summon and the player Summon spell, identically: one invocation of the shared single-cell converge on the flash tile. See section 8.3.1. | The shared full-viewport XOR flash, which neither summon path invokes. |
| Envelope cue before a summon | Monster summon on successful placement; player Summon on accepted placement. | Failed chance, coordinate, legality, or allocation gates - all silent. |
| Wind-change sequence | The Wind Change spell (variant 2) and the Wind Change scroll (variant 1). See section 7.3. | The autonomous wind drift, which is silent on every path. The wind setter itself, which contains no sound call. |
| Nothing at all, on a passed direction prompt | Blink and Vanish both return the shared cancelled sentinel, which matches neither epilogue branch. See section 8.3.2. | There is no Blink pass in combat: the scene gate takes an arm that never prompts. |
| Intro dissolve retune | The first gated rectangle dissolve only, on every second visited pixel, as a continuously running retuned carrier. See section 8.6.1. | Every later dissolve in the run, the gate having been cleared by the first glyph draw. It is not a per-pixel click and not a discrete click train. |
| Harpsichord note | The castle harpsichord handler, one note per accepted digit, only while sound is on. See `town-mode.md` section 13.1. | Ordinary name or text typing. Any other digit-key context. |

Two scope questions in this table are **open** rather than answered, and are
flagged at their own sections rather than resolved here: whether a *missed
combat attack* also produces the blocked-step beep (section 7.4), and whether the
ambient shrine/flame tick can sound during an arbitrary keyboard prompt
(section 8.3.2).

## 12. Sources and confidence

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

The material added in sections 5.4.6, 6.1, 7.3, 7.4, 8.3.1, 8.3.2, 8.6.1, and
11 answers two implementation issues raised against this document. Its exact
parts are program constants and simulations of the exact 16-bit arithmetic:
the ten harpsichord phase periods and every ratio between them, the 48-row
variant map and the scroll and potion rules, the four-site blocked-step census,
the dissolve's state recurrence and band formula, the dissolve decile table and
its first ten frequencies, the 256-plot converge, and every "which callers"
statement in section 11. Its approximate parts are every frequency in hertz and
every duration, all of which inherit the bands published in sections 5.4.3 and
10. Each of those sections ends with an explicit unresolved list; those lists
are the honest limit of what static analysis reached, and none of them is
pending further desk work - each names the experiment that would close it.

**No runtime verification of any kind was performed for any of that material.**
Nothing was run under an emulator and no audio was captured. Every caller and
reference census behind it is a direct near-call and absolute-displacement scan
over the main executable, all 23 code overlays, and the EGA display driver. Such
a scan does not cover indirect calls through a register or memory, far calls,
tail-jumps into a primitive, runtime-computed or self-modified targets, or a
port access whose port number arrives in a register; state-reference censuses
cover absolute-address encodings only. The three non-EGA display drivers were
never opened, so nothing in sections 8.3.1 or 8.6.1 may be generalised beyond an
EGA install. No evidence of any of those uncovered mechanisms was found. Their
absence was **not** proved.

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
