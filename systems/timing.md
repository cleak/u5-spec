# Timing Calibration

## 1. Scope

This document covers the original engine's CPU-speed calibration used for short
delays and display/audio pacing. It is separate from the in-game calendar,
per-turn minute advancement, moon phases, torch duration, and vehicle timing
tags, which are specified in `time.md`. The PC-speaker recipes that consume
these timing classes are specified in `audio.md`.

## 2. Boot Calibration

During boot, the engine measures how many tight-loop iterations fit inside one
hardware timer tick and stores a compact calibration value in resident state.
The same boot helper also captures the BIOS conventional-memory size, which the
boot path uses for its Tandy low-memory fallback. Later delay helpers consume
the calibration value so short waits, cursor/audio pauses, and small animation
delays run at roughly stable apparent speed across faster and slower DOS
machines.

The timing value is a CPU-speed calibration count. The adjacent memory-size
value is startup hardware state. Neither is a cursor coordinate, text window
field, gameplay clock, PRNG state, or save-game value. Gameplay systems must
not read either value to determine turn cost, animation phase, or calendar time.

## 3. Porting Contract

A modern implementation does not need to reproduce the busy-loop calibration
itself. It may map these waits to real elapsed-time timers, frame scheduling, or
platform sleep primitives. What matters for compatibility is the boundary:

- Gameplay time still advances only through the per-turn cleanup contracts in
  `time.md` and the mode specs.
- Display and audio delays may be real-time approximations.
- The calibration state should not leak into saved gameplay state or deterministic
  simulation state.

## 4. Delay Helper Contracts

The resident executable exposes two low-level presentation-delay families:

**Calibrated busy wait.** Short animation and flash pauses can request a nested
busy wait scaled by the boot calibration value. The caller supplies an outer
count and a context-specific shift selector; the helper scales the calibration
count by that selector, spins for the requested product, and returns without
performing input, I/O, gameplay-clock advancement, or save-backed state
changes. Its scratch counters are temporary presentation state. In the shipped
game exactly one selector value is ever supplied and its effective shift is
zero, so in practice the helper always spins the full calibration count per
outer pass; section 6 publishes the delay-context contract and section 7 gives
the wall-clock value of one outer unit.

**Hardware-tick wait.** Longer or wall-clock-sensitive waits can request a
counted BIOS timer-tick delay. The helper temporarily installs a user-tick
counter, waits until the requested number of ticks has elapsed, and restores the
prior timer hook. A one-tick request is skipped entirely — no hook, no wait —
when the boot calibration value reports a CPU **at or below** the original IBM
PC measured baseline; any faster host performs the real one-tick wait. Earlier
revisions of this section stated that direction backwards ("skipped on
sufficiently fast machines"); that is retracted. Section 5.2 gives the gate and
the calibration-override pattern that suppresses it. This wait is for visible pacing
only; it is not the calendar, not an animation phase counter, and not a source
of deterministic gameplay time.

Input-facing modal waits layer on top of the same presentation boundary: they
poll the blinking-cursor input helper for a bounded number of iterations and
return early when a key arrives. They may temporarily override the calibration
used by that blink/poll loop so text prompts feel consistent, but they still do
not advance the in-world clock.

## 5. Intro Animation Cadences

Most visible intro animation steps are driven by the DOS BIOS user-tick
interrupt at the standard PC rate of approximately 18.2065 Hz (roughly
54.945 ms per tick). The intro never uses a free-running real-time clock, never
uses the host frame rate, and never accumulates missed time. A single call to
the hardware-tick helper from section 4 waits until exactly the requested
number of ticks have elapsed, regardless of how long the rest of the call site
took.

The hardware tick is **not** the only pacing primitive the intro uses. Two
intro effects run entirely inside the display driver and are paced by the
driver's own CPU-calibrated busy wait with no tick involvement at all: the
`TITLE.BIT` title flourish and the start/menu subtitle-ignition transition. An
earlier revision of this section asserted that every visible intro animation
step is BIOS-tick driven; that is withdrawn.

### 5.1 Cadence By Phase

The table below gives the per-step cadence each intro visual phase uses. "One
tick" means one ~55 ms BIOS tick produced by the hardware-tick wait helper.

| Phase | Wait unit | What advances once per unit |
|---|---|---|
| Title-tick helper (`display-driver-abi` slot 0x69 entry) | One BIOS tick | Driver-local four-frame title/menu strip frame index advances once; one paint of the destination rectangle. |
| `TITLE.BIT` title flourish | One calibrated delay unit per presentation step, inside the driver's animation-script entry | One presentation step from `intro.md` section 3 is consumed; the frame's whole band is repainted with the currently visible rows. Eighty-five steps for the whole flourish. **Not** title-tick or BIOS-tick paced. |
| `Presents` hold (`intro.md` section 3, visible phase 2) | Eighteen BIOS ticks, then a bounded poll of up to twenty more | Nothing is redrawn; the phase simply holds. The first wait is unconditional, the second returns as soon as a key arrives, so the hold is about 1.0 s at minimum and about 2.1 s if the player does not press anything. On a run where the flourish was aborted the hold is skipped entirely and the frame flashes past. |
| The `a` hold and the finished-composition hold (visible phases 3 and 5) | A bounded poll of up to twenty BIOS ticks each | Nothing is redrawn; each phase holds for about 1.1 s or until a key arrives. |
| `BRITISH.PTH` signature path | One BIOS tick per 32 consumed path bytes | Thirty-two path bytes (each encoding two nibble-deltas) are walked and painted; a single keyboard poll separates each byte within the chunk. |
| Start/menu logo reveal | Self-paced inside one driver call, with no delay at all | The pseudo-random per-pixel dissolve of the inclusive rectangle `(0, 0)..(319, 100)` runs to completion in a single driver call. It is not a per-column, per-tick loop, and unlike the two calibrated phases it has no wait of any kind in its inner loop — it transfers one pixel per iteration as fast as the host manages, so on a modern host it is close to instantaneous. |
| Start/menu subtitle ignition | One calibrated busy wait per batch publication, inside the driver | Runs once on the animated path; no BIOS tick. Each pass resets a 128-in-bounds-position countdown, changed to 256 when calibration is below 250. A publication first draws the current idle frame, then advances its counter. A speaker-gated publication waits 45 full calibration units; a silent one waits 50, in addition to the burst's own short pitch holds. Ordinary positions have no calibrated wait. Two passes make 110 publications each normally or 55 each at the 256-position cadence; neither pass publishes its 32-position tail. Keyboard status is tested once per nonzero LFSR state after that state's work. See `intro.md` section 5. |
| Story step-1 rectangle reveal | Self-paced inside one driver call | The pseudo-random per-pixel dissolve of the inclusive rectangle `(40, 86)..(75, 120)` runs to completion in a single driver call. It is not a per-column, per-tick loop; see `intro.md` section 10. |
| Story `U` slide-show inter-slide pacing | Blocking keyboard wait | Bounded by player input; no wall-clock advancement except the cursor blink loop. |
| Return-to-View preview tick | One BIOS tick per preview tick | One preview tick advances the animated-tile frame table and active-object animation by one step, fires one title tick, rescatters preview actors, repaints the revealed columns, widens the strip reveal on every second tick, and runs one consuming nonblocking keyboard read. Commands request a fixed number of these; a consumed key aborts before the tick wait and is not handed to the restored menu. See `formats/location-dat.md` section 11. |
| Return-to-View local cell effect | One preview tick between steps | One of the fifteen shimmer steps of an open or close effect. |
| Return-to-View temporary actor draw | Eight pixel writes between preview ticks | One cell converges through exactly 256 one-pixel writes. After completed counts `8,16,...,248`, exactly 31 times, the wrapper runs one complete preview tick whose consuming keyboard read may abort; there is no tick or input read after count 256. |
| Menu idle pump (Return-to-View timeout) | **Two** BIOS ticks per no-key pass, about 110 ms | One menu-idle pass advances. The pass first calls the blinking-cursor input poll, which waits one tick when no key is queued (when a key *is* queued it erases the cursor cell and returns without waiting), and then, still holding no key, calls the title tick, which waits a second tick before advancing the idle strip. The two waits are sequential, so the idle strip advances about every 110 ms and the two-hundred-pass Return-to-View timeout is about 22 seconds of unattended menu, not 11. |
| Acknowledgement screen, part and close wipes | One BIOS tick per step | One eight-pixel band of the credits page (part) or of the rebuilt menu screen (close) is published and both ornamental pillars advance eight pixels. Eighteen steps each, so about 0.99 s per phase; see `intro.md` section 11.2. |
| Acknowledgement screen, rise and sink wipes | No wait at all | The pillar slide phases are unpaced: 137 rise steps and 136 sink steps run back to back at draw speed. Any claim that the whole acknowledgement sequence is uniformly tick-paced is wrong. |
| Animation-script player (display-driver dispatch offset `0x6F`) | One calibrated delay unit per presentation step, driven by a byte-stream script | This is the same entry that plays the `TITLE.BIT` flourish above — it is the flourish player, not a credits or death-screen player. The script's frame and group structure determines the step count. |

One cadence outside the intro follows the same rule and is listed here so it is
not modelled with a tick schedule by mistake: the endgame's full-screen fade to
black (`endgame.md` section 7.1) is a full-surface fill followed by a
pseudo-random per-pixel dissolve of the inclusive rectangle `(0, 0)..(319, 199)`
in one driver call. Like the two intro dissolves it is self-paced, blocking, not
tick-driven, and runs no title tick and no keyboard poll while it works.

The same cadence applies to all three map-viewport calls listed in
`display-driver-abi.md` section 9.6: each `(8,8)..(183,183)` dissolve is one
self-paced blocking driver call. The two rescue/refuge calls and the dungeon
Search reveal call run no world tick, gameplay-time advance, or
caller redraw during the dissolve itself; their caller-side composition and
mutation order is specified in `blackthorn.md` section 7 and
`dungeon-mode.md` section 8.

The title-tick helper has the per-call BIOS-tick wait built into its body, so
intro callers do not add an external wait around it. The pacing of any phase
whose unit is "one title-tick call per X" therefore inherits the same ~55 ms
per step as a direct hardware-tick wait of one tick. That is a floor, not a
ceiling: where the caller does its own waiting in the same pass — the menu idle
pump is the case that matters — the per-pass cost is the sum of both waits.

#### Calibrated delay unit for the flourish

The animation-script entry's per-step wait is twelve passes of an inner loop
whose iteration count is the boot calibration value from section 2. That
calibration value is defined as the number of iterations of a short
memory-increment loop that fit inside one BIOS tick, scaled by `18 / 750`. If
the wait loop and the calibration loop cost the same per iteration, one
presentation step is therefore
`12 x (18 / 750) x 54.945 ms`, about **15.8 ms**. In the original the wait loop
is the cheaper of the two — roughly two thirds the cost per iteration on the
baseline CPU — which brings a step nearer **10.5 ms**. Across the flourish's
85 presentation steps that puts the whole `TITLE.BIT` flourish at roughly
**0.9 to 1.4 seconds**, plus the per-row keyboard-probe overhead of each
repaint.

For a v1 engine the normative compatibility cadence is **14 ms per
presentation step**. An uninterrupted 85-step flourish therefore has a nominal
duration of **1.190 seconds**. Implement it as a wall-clock requirement, not as
a calibration emulation: one logical presentation per deadline, in order, with
no multi-step catch-up.

Deterministic scheduler tests should use exact 14 ms logical deadlines. For a
real captured frontend, host scheduling jitter is acceptable when the mean
step duration is within **14 ms ± 1 ms** and the uninterrupted whole flourish
is within **1.190 s ± 0.100 s**. These tolerances cover publication timing only;
the 85-frame raster sequence and abort snap to the completed frame remain exact.

Anything that claims the flourish is 67 groups long, one BIOS tick per group,
or about 3.7 seconds total is wrong on all three counts and is withdrawn.

An independent black-box observation of a real run agrees with the short
figure. Sampling the original at two-second intervals from launch shows a black
screen at about two seconds and the attribution card's first line already alone
on the screen at about four seconds. The intro holds the preceding frame for
eighteen ticks — about one second — plus a bounded poll before that card is
drawn, so the flourish has to fit comfortably inside the remaining interval. A
3.7-second flourish is not compatible with that capture; a one-second flourish
is.

Because the flourish is calibration-paced rather than tick-paced, it is also
the one intro phase whose duration genuinely varied with CPU generation,
memory/video timing, and emulator configuration. A timed capture can describe
one reference setup, but there is no single historical wall-clock value encoded
by the program. Treating it as a fixed wall-clock target is a deliberate
modernisation, not a reproduction.

A keystroke ends the flourish early, but not by cutting to the next phase
mid-picture: the driver presents the completed final frame once before
returning, so the abort is visible as an instant snap to the finished mark
rather than as a partial one. See `intro.md` section 3.

**Compatibility decision.** The 10.5–15.8 ms bracket remains historical
instruction-cost context, not an acceptance range and not a placeholder for a
future universal measurement. The final clean-engine contract is the 14 ms
cadence and capture tolerance above. No timed capture is required to replace
it, and an implementation must not describe 14 ms as a measured original-
hardware constant.

### 5.2 Slow-CPU Gate And Override

The hardware-tick wait helper has a fast-path skip: when the boot calibration
value indicates a CPU at or below the original IBM PC measured baseline, the
helper short-circuits and returns immediately without installing the timer
hook or waiting. This keeps total time stable on the original target hardware
where the surrounding loop body itself already consumed comparable time.

Three intro paths override the calibration for the duration of an inner loop
so the hardware-tick wait runs on every host, not only on hosts above the
baseline:

- The `BRITISH.PTH` signature path swaps in a calibration override (the
  literal value the original walker uses is just above the IBM PC baseline)
  before entering its inner loop, and restores the prior calibration on exit.
  This guarantees the 32-bytes-per-tick chunk pacing on every CPU.
- The input-modal "wait for key with timeout" helper swaps in a larger
  calibration override for the duration of any timeout-bounded wait so the
  cursor blink and modal input feel consistent across host speeds.
- The finished-menu idle pump does the same: the intro writes a calibration
  override just above the baseline before entering the bounded poll loop and
  restores the previous value when the loop exits. This is what keeps the
  idle-strip animation running at one frame per tick on every host rather than
  free-running on machines the gate would otherwise skip.

A modern engine reproducing the contract should treat the cadences in section
5.1 as wall-clock requirements rather than calibration-conditional ones. The
calibration override pattern is the original code's way of removing the
slow-CPU skip; a modern implementation that always honours the cadence does
not need to emulate the override.

### 5.3 Catch-Up Policy

The original engine's wall-clock pacing is "wait until target tick count
reached", not "advance N steps based on elapsed time". A modern implementation
should not run multiple logical steps in one rendered frame to catch up to
wall-clock drift. The correct behaviour is at most one step per BIOS-tick
interval; if a host frame straddles multiple ticks, draw one step and let the
remaining ticks elapse on subsequent frames. The intro will visibly slow if
the host stalls, which matches the original DOS-tick behaviour.

A renderer driven by `Time::delta_secs()` or any other free-running real-time
source must therefore accumulate elapsed time and only advance one logical
step per ~55 ms slot, dropping anything more than one slot's worth of
accumulated time per advance to avoid catch-up.

### 5.4 Phase Ownership Per Frame

When multiple intro effects are concurrently pending (the title-flourish row
reveal during the early title screen, or a transition wipe overlapping with
the menu idle pump), the original code's structure is sequential, not
concurrent: each phase owns the screen exclusively until it finishes or is
interrupted by input. There is no per-frame multiplexing of the title tick,
the path walker, and the reveal helper. A clean engine should follow the same
ownership rule and only advance one phase per tick interval.

The implication for an engine that wants to render at a host frame rate
higher than 18.2 Hz: present the current intro frame on every host frame,
but only advance the logical state at most once per BIOS-tick interval. The
visible image is unchanged on intermediate host frames.

## 6. Delay Contexts For The Calibrated Wait

Section 4 describes the calibrated busy wait as taking an outer count and a
context-specific shift selector. This section publishes what those contexts
actually resolve to in the shipped game, because the answer is much simpler than
the interface suggests.

### 6.1 There is exactly one live delay context, and its shift is zero

> **Normative.** The shipped game exposes one selector-driven delay context and
> uses no other. Its effective shift is **zero**. Every calibrated wait in the
> resident game therefore spins `outer_count x boot_calibration_count` inner
> steps, with no scaling of the calibration count at all.

Every reachable call into the shared calibrated wait passes the same selector,
as an unconditional constant. There is no second selector value anywhere in the
resident program, no conditional that could produce one, and no caller-supplied
selector. A clean implementation should model a single calibrated delay unit and
drop the selector from its interface entirely.

A ramp of shift amounts does exist as data in the shipped build, but no
reachable path selects any entry other than the one that yields shift zero. It
is dead data. An implementation **must not** model it, and this spec
deliberately does not publish its contents: reproducing an unreferenced table
would only invite an engine to implement behaviour the original never exhibits.

Why the one live selector has the particular value it has cannot be determined.
A deliberate choice, an off-by-one, and a leftover from an earlier data layout
are all consistent with the shipped build, and the observable behaviour is
identical under all three. This spec asserts no reason, and an implementation
must not infer one.

**Scope of this claim.** It rests on an exhaustive static census of the call
sites in the shipped images. That census cannot see two things: a call reached
through a target pointer computed at run time, and a write into the shift table
through a computed destination. Neither was found and neither has any positive
evidence behind it, but a static census cannot exclude them. Treat "one context,
shift zero" as a strong contract carrying that stated residual, not as a proof.

### 6.2 Two fixed subdivisions that are not delay contexts

Two further timing scales occur in audio presentation and are easily mistaken
for additional delay contexts. They are not. They are fixed subdivisions
hard-coded inside their own routines, and they never consult the selector table:

| Timing class | Inner count per outer pass | Selector-driven | Speed gate |
|---|---|---|---|
| Calibrated wait (section 6.3) | The full boot calibration count | Yes, but only one selector exists | None |
| Random-rumble step | The calibration count divided by 16, truncated toward zero | No | None |
| Software-envelope idle work | The calibration count divided by 24, truncated toward zero | No | Forced to zero whenever the calibration count is below 100 |
| Title-sequence ignition burst pitch hold | The calibration count divided by 16, truncated toward zero | No | None |
| Title-sequence publication wait | The full calibration count | No | None; there is no shift at all |

Both divisions **truncate**, and that truncation is normative for any
implementation that models a machine speed other than the baseline. At low
calibration counts a rational divide overstates the wait by up to about 18
percent for the rumble scale and about 24 percent for the envelope scale. At the
baseline the distinction does not arise; see section 7.3.

The two title-sequence waits are not calls into the resident helper at all. The
display driver is a separately loaded module that cannot reach the resident
wait, so it carries its own copy of the same nested-wait shape over its own
private calibration storage. Behaviourally the 45-unit and 50-unit publication
waits are the same timing class as the resident shift-zero wait, and the burst
pitch hold is the same timing class as the rumble step. Only the per-unit cost
differs slightly; section 7.4 gives the figure.

### 6.3 Which recipe uses which timing class

Every row in the first group reaches the same single delay context of section
6.1. `audio.md` owns the recipes themselves; this table exists so that an
implementer never has to guess which scale a named effect sits on.

| Recipe | Route | Outer count | Entered |
|---|---|---:|---|
| Blocked step / blocked combat attack beep | Blocking-tone wrapper | 200 | Once |
| Two-tone "not here" pair, each tone | Blocking-tone wrapper | 150 | Once per tone |
| Return-to-View strip 3 blip | Blocking-tone wrapper | 3 | Once per phase |
| Action snap glissando | Glissando helper | 1 | Once per update, 40 updates |
| Cast-failure glissando | Glissando helper | 1 | Once per update, 50 updates |
| Dungeon wall drip | Glissando helper | 1 | Once per update |
| All other glissandi | Glissando helper | The recipe's per-update delay | Once per update |
| Stonegate trapdoor descending sweep | Direct wait | 40 | Once per tone, 750 tones |
| Two-tone sting inter-part gap | Direct wait | 20 | Once |
| Projectile flight animation step | Direct wait | 40 | Once per animation step |
| Title-sequence publication wait, sounded branch | Driver-local copy | 45 | Once per publication |
| Title-sequence publication wait, silent branch | Driver-local copy | 50 | Once per publication |

The remaining audio waits use the fixed subdivisions of section 6.2:

| Recipe | Scale | Inner count per outer pass |
|---|---|---|
| Every random rumble | Rumble step | Calibration count divided by 16, truncated |
| Every software envelope's idle work | Envelope idle | Calibration count divided by 24, truncated, and gated to zero below calibration 100 |
| Title-sequence ignition burst, each of its 25 pitches | Rumble scale | Calibration count divided by 16, truncated |

## 7. Wall-Clock Anchor For The Calibrated Unit

Sections 2 through 6 describe the calibrated unit as a machine-relative
quantity, which is what it is. Engine work nevertheless needs one real-time
number to hang everything on. This section publishes that anchor, states its
tolerance, and says plainly what an implementation is free to vary.

**Nothing in this section was verified at run time.** Every wall-clock figure
here is a static timing derivation for a documented reference machine. No figure
was observed on original hardware or in a cycle-accurate emulator. The
tolerances below are honest modelling bands, not measurement error bars. Section
7.6 says what a single emulator run would settle.

### 7.1 The anchor

> **Normative, approximate.**
> **One outer calibrated unit = 0.88 ms.**
> **Published tolerance: plus or minus 10 percent, that is 0.79 to 0.97 ms.**

An implementation **may** use any value inside that band, and **may** round to a
flat 1 ms if that simplifies its scheduler; effects then run about 14 percent
long, which is well inside the spread the original hardware itself produced. An
implementation **must not** present 0.88 ms as a measured original-hardware
constant and **must not** treat it as exact.

Two narrower bands are recorded because they explain where the published
tolerance comes from:

| Band | Range | What it covers |
|---|---|---|
| Reference-machine modelling spread | 0.83 to 0.92 ms | Uncertainty in the derivation for the 4.772727 MHz reference machine alone |
| Whole-era hardware spread | 0.86 to 0.99 ms | The same unit as produced on every CPU generation of the period, from an 8-bit-bus original through a 486 |
| **Published contract** | **0.79 to 0.97 ms** | Both of the above, rounded outward |

What stays exact regardless of the constant chosen: the outer counts, update
counts, step counts, iteration counts, and ordering in section 6.3 and in
`audio.md`. Those are program constants and carry no uncertainty. Only the
seconds-per-unit scale is approximate.

### 7.2 The inner unit and the boot calibration count

> **Approximate.** One inner unit is about **10.0 microseconds** on the reference
> machine, band 9.4 to 10.3 microseconds. The boot calibration count on that
> machine is about **87**, band 80 to 92. One outer unit is one calibration count
> of inner units plus about **10 microseconds** of fixed per-outer-pass overhead.

So at the baseline an outer unit contains roughly 87 inner units, and one inner
unit is a little over 1 percent of an outer unit.

The upper end of the calibration band is firmer than the central value, because
it follows from bus bandwidth rather than from instruction-timing assumptions:

> **On a stock 4.772727 MHz machine the boot calibration count cannot exceed
> 92.** The calibration loop must refetch its whole body and move its own working
> data on every pass, which imposes a floor on the per-trip cost; that floor caps
> the trip count and therefore caps the stored calibration value.

This bound matters for exactly one reason, and it is a large one: the
software-envelope idle gate of section 6.2 fires whenever the calibration count
is below 100. On genuine baseline hardware that gate therefore **always** fires.
See section 7.3.

An implementation that does not model original CPUs needs neither the inner unit
nor the calibration count. They are published so the two fixed subdivisions of
section 6.2 can be converted to real time, and so that an implementation which
does model machine speeds knows where the truncation boundaries sit.

### 7.3 The derived integer subdivisions are stable across the whole baseline band

This is the most useful robustness result available, and it is what lets a
frontend ignore the uncertainty in the calibration count entirely. Both
hard-coded divisions truncate to the **same integer** everywhere in the derived
band of 80 to 92:

| Quantity | At calibration 80 | At 87 | At 92 |
|---|---:|---:|---:|
| Rumble step inner count (divide by 16) | 5 | 5 | 5 |
| Envelope idle factor before the gate (divide by 24) | 3 | 3 | 3 |
| Envelope idle factor after the "at least 100" gate | 0 | 0 | 0 |

Therefore, on any stock reference-class machine:

- **A random-rumble step unit costs about 60 microseconds** — five inner units
  plus the per-outer-pass overhead.
- **A title-sequence ignition burst pitch hold costs about 60 microseconds.**
- **The software envelope's idle work is exactly zero.** The gate never fails to
  fire at baseline, so the envelope's iteration cost at baseline is instruction
  time only.

None of the uncertainty in the calibration count propagates into these three
quantities. Once a machine is known to be reference-class they are stable
integers, not approximations. The dependency does return on faster hardware,
which is why section 6.2 makes the truncation normative.

### 7.4 Conversion contract for a frontend

Publish one constant and derive the rest. Every figure below inherits the
plus-or-minus-10-percent tolerance of section 7.1 unless stated otherwise.

| Quantity | Value | Notes |
|---|---|---|
| Outer calibrated unit | 0.88 ms | The single published anchor |
| Inner unit | Outer unit divided by 87, about 10.0 microseconds | Only needed in order to model the subdivisions |
| Random-rumble wait, per step unit | About 60 microseconds | Stable integer at baseline, section 7.3 |
| Software-envelope idle wait | Zero | The gate always fires at baseline |
| One glissando update | `delay_unit x 0.88 ms` plus about 0.12 ms of retune and bookkeeping overhead | For `delay_unit = 1` this is a convenient **1.00 ms** |
| Retuning the speaker to a new frequency | About 89 microseconds | Dominated by the divisor computation; already folded into the glissando figure |
| Random-rumble per-iteration setup | About 130 microseconds | Jitter advance, divisor computation, divisor install, accumulator update |
| Title-sequence (driver-local) unit | About 0.92 ms, roughly 4 percent slower than the resident unit | The driver's copy of the wait is marginally more expensive per pass |
| Software-envelope iteration, audible | About 43.0 microseconds, band 40.4 to 48.2 | See `audio.md` section 5.4 |
| Software-envelope iteration, muted | About 33.3 microseconds | About 23 percent faster than the audible arm; see `audio.md` section 3 |

`audio.md` section 10 applies this table to every named effect and publishes the
resulting durations.

**Consistency check against section 5.1.** The `TITLE.BIT` flourish's per-step
wait is twelve driver-local units. Under this anchor that is about **11.0 ms**,
which falls inside the 10.5 to 15.8 ms historical bracket section 5.1 already
publishes, near its low end, consistent with that section's own statement that
the wait loop is the cheaper of the two loops. This is a cross-check between two
derivations, not a measurement, and it **does not** change the normative 14 ms
cadence decided in section 5.1. That cadence remains a deliberate modernisation.

### 7.5 Why the anchor is robust across original hardware

The calibration count and the cost of one inner step move in opposite directions
as machines get faster, and the two effects very nearly cancel. The outer unit is
approximately one BIOS timer tick, scaled by the `18 / 750` factor of section 2,
multiplied by the ratio between the inner step's cost and the calibration loop's
cost. That ratio stays between roughly 0.65 and 0.75 on every CPU of the period,
so:

> **One outer unit stays inside 0.86 to 0.99 ms from a 4.772727 MHz 8-bit-bus
> machine right through to a 486.** A 6 to 8 MHz AT-class machine produces a much
> larger calibration count with a proportionally cheaper inner step and lands in
> the same place.

This, rather than any particular calibration count, is the practical meaning of
the `18 / 750` scaling: the outer unit is engineered to be "about a millisecond,
a little short" on any machine of the era. A modern frontend may therefore treat
the outer unit as a fixed 0.88 ms with no machine model at all and still be
correct to within the original hardware's own spread. That is the recommended
implementation.

### 7.6 Confidence, and what remains unresolved

**Approximate but well constrained.** The outer unit, the inner unit, the
calibration count band, the retune and bookkeeping overheads, and the envelope
iteration cost. Each is published above with its band. An implementation may
vary any of them within its band.

**Exact, carrying no timing uncertainty.** Every outer count, update count, step
count, iteration count, frequency, and ordering constraint in section 6.3 and in
`audio.md`. Also exact: the ratios between the nine envelope variants' carrier
rates (`audio.md` section 5.4), because they are ratios of program constants.

**Explicitly unresolved.** These are recorded so an engine stops treating them as
pending answers and treats them as known gaps:

1. **Nothing in this section was verified at run time.** A single cycle-accurate
   run that read the boot calibration value after startup would collapse most of
   the band in section 7.2 and much of the band in section 7.1. This is the
   largest single gap in the whole timing contract.
2. **The purpose of the dead shift ramp** (section 6.1) is unrecoverable. Do not
   model it.
3. **The reason the one live selector has its particular value** (section 6.1) is
   undecidable. Behaviour is unaffected; assert nothing.
4. **The static census behind section 6.1** cannot see a run-time-computed call
   target or a computed write into the shift table. Neither was found; neither is
   excluded.
5. **Two board-level inputs were assumed, not derived**: the era-typical memory
   refresh steal, taken as about 6 percent with a 2-percentage-point band, and
   the wait-state count on speaker-control accesses, taken as one. The latter is
   the single largest contributor to the envelope-carrier band in `audio.md`
   section 5.4.
6. **Interrupt jitter during long envelope loops** was not quantified. Whether a
   tick handler is live during gameplay envelopes was not determined; if one is,
   it would inject on the order of eight brief interruptions per
   ten-thousand-iteration envelope.
7. **The boot calibration value is not proven constant during a session.**
   Several resident and intro paths save, overwrite, and restore it; the extent
   of those overrides beyond the three documented in section 5.2 was not traced.
   An implementation that models calibration-dependent behaviour must not assume
   one value holds for a whole run.
8. **Only one display driver's ignition constants were derived.** The 45-unit and
   50-unit publication waits and the 25-pitch burst are established for the EGA
   driver. The same wait shape exists in the other three drivers, but whether
   they use the same pitch count, subdivision, and thresholds is unverified.

## 8. Sources

This public description is a cleanroom prose rewrite from private timing-helper
analysis. It does not reproduce decompiled source, assembly listings, raw bytes,
or private address tables.

The delay-context census of section 6 and the wall-clock derivation of section 7
are cleanroom restatements of a static analysis of the shipped resident and
display-driver wait loops, cross-checked against a second independent derivation
that reached the same anchor once its own machine model was applied
consistently. Neither derivation was validated at run time; section 7.6 records
that as the largest open gap in this contract.

The boot calibration, delay, dissolve-wrapper, and input-helper evidence is
under `u5-decomp/functions/ULTIMA_EXE/`; intro phase ownership, title ticking,
path pacing, menu pumping, and caller order are under
`u5-decomp/functions/INTRO_OVL/`; Return-to-View timing is under
`u5-decomp/functions/FONT_OVL/`; display-entry wait and publication behavior is
under `u5-decomp/functions/EGA_DRV/`; and the independent title, dissolve,
subtitle-ignition, acknowledgement, and Return-to-View retraces are under
`u5-decomp/notes/`. The subtitle ignition's pass counter, corner fixup,
publication order, poll placement, speaker gate, and two wait branches were
re-read directly from the shipped EGA driver for this timing contract.
