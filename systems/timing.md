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
| Start/menu logo reveal, **ungated** | Self-paced inside one driver call, with no delay at all | The pseudo-random per-pixel dissolve of the inclusive rectangle `(0, 0)..(319, 100)` runs to completion in a single driver call. It is not a per-column, per-tick loop, and it has no wait of any kind in its inner loop — it transfers one pixel per iteration as fast as the host manages, so on a modern host it is close to instantaneous. |
| Start/menu logo reveal, **first (gated) call** | A short calibrated hold on every second visited pixel | *Correction: the "no wait of any kind" row above describes the ungated dissolve only.* While the driver-local sound/abort gate is still set, every second visited pixel retunes the speaker and pays about 50 to 60 microseconds of calibrated hold — one outer unit at the shift-four subdivision of section 6.2 — plus the retune and poll work. For the 32,320-pixel logo rectangle that is 16,160 such visits. A hand-built cycle model puts the whole gated call at roughly 8 to 14 s, but it omits display-memory wait states entirely and is **unverified**; see `audio.md` section 8.6.1. |
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
| Blocked step, including the combat arena's refused step | Blocking-tone wrapper | 200 | Once |
| Combat command refused as inapplicable, each tone | Blocking-tone wrapper | 150 | Once per tone |
| Return-to-View strip 3 blip | Blocking-tone wrapper | 3 | Once per phase |
| Action snap glissando | Glissando helper | 1 | Once per update, 40 updates |
| Cast-failure glissando | Glissando helper | 1 | Once per update, 50 updates |
| Long descent (drowning, whirlpool) | Glissando helper | 40 | Once per update, 195 updates |
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
| One glissando update | `delay_unit x 0.88 ms` plus a per-tone install cost of about **0.17 ms** | For `delay_unit = 1` this is **1.05 ms**. See section 7.4.1 |
| Per-tone install cost, sweep | About **0.173 ms**, that is **17.4 inner units**, band 16.3 to 18.5 | The whole cost of putting one tone on the speaker from inside a sweep loop. Section 7.4.1 |
| Per-tone install cost, blocking-tone wrapper | About **0.187 ms**, that is **18.8 inner units** | Higher because that wrapper pays a stop and its own frame per tone. Section 7.4.1 |
| One-time setup, per sweep invocation | About 0.18 ms | The generator's own frame plus the interpolation multiply and divide; roughly one extra update's worth |
| Stopping a tone | About 0.014 ms, that is 1.4 inner units | It only clears the speaker gate; it never reprograms the timer |
| Tone-start routine body alone | About 0.08 ms | Dominated by the divisor division. This is the part earlier revisions published as "retuning the speaker", about 89 microseconds; it is a component of the install cost, not the whole of it |
| Random-rumble per-iteration fixed cost | About **0.125 ms**, that is 12.5 inner units | Jitter advance, pitch mapping, retune core, shift setup, bookkeeping, loop test. Section 7.4.2 |
| Random-rumble per outer pass | About 0.0596 ms | Five inner units plus the per-outer-pass overhead; an iteration performs `step` of these, so the per-iteration cost is **linear in the step**. Section 7.4.2 |
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

#### 7.4.1 The per-tone install cost

> **Derived, approximate.** Installing one tone costs about **0.173 ms** -
> **17.4 inner units**, band 16.3 to 18.5 - on top of whatever calibrated wait
> the recipe then performs. Through the blocking-tone wrapper it is about
> **0.187 ms** (**18.8 inner units**), because that wrapper additionally pays a
> speaker stop and its own call frame on every tone.

The point of publishing this as a first-class quantity is that a recipe should
read as **per-tone install plus updates times interval**, rather than as a total
an implementer has to back out:

```text
sweep = one_time_setup + updates x (delay x outer_unit + per_tone_install)
tone  = hold x outer_unit + per_tone_install_blocking
```

Where the cost goes, per sweep update:

| Component | Inner units |
|---|---:|
| Tone-start routine body, sound enabled | about 8.1 |
| Caller-side argument setup, call, instruction-queue refill | 0.9 |
| Delay-helper argument setup, call, refill | 1.6 |
| **The delay helper's own entry, table lookup, exit and return** | **about 5.1** |
| The sweep loop's own arithmetic and test | 1.7 |
| **Total** | **about 17.4** |

Three consequences are worth stating plainly.

- **The install cost is the divide.** Starting a tone is dominated by the
  32-by-16-bit division that computes the timer divisor. *Stopping* a tone is
  cheap - about 1.4 inner units, call inclusive - because it only clears the
  speaker gate and never reprograms the timer. The two sweep loops that were
  priced call the stop once, after the loop, not per update; a loop that stopped
  per tone would pay that 1.4 extra every tone.
- **Every sweep also pays a one-time setup of about 0.18 ms** - its own frame
  plus the interpolation multiply and divide - roughly one extra update's worth,
  which no earlier published figure carried.
- **The delay helper's own call frame is the term that gets missed.** At about
  5.1 inner units it is larger than the loop arithmetic at 1.7, it is roughly
  30 percent of the total, and it is invisible to any model that prices only the
  code inside the loop body.

**This figure disagrees with the value the implementation side currently uses,
and the disagreement is published rather than smoothed over.** An implementation
reported (issue #146 follow-up) a fitted per-tone constant of **12 inner
units**. The derivation above gives **17.4**, so the fitted figure is **too low
by about 45 percent** - about 5.4 inner units, or 0.054 ms, per tone. Two things
about that gap matter:

- **The derivation was not fitted to this repository's published totals.** It
  was priced component by component from the shipped code and then independently
  recounted. Neither is the 12 an independent measurement: it is this
  repository's own earlier per-update overhead of 0.12 ms re-expressed, and that
  overhead omitted the delay helper's call frame. Anyone who checked the 12
  against our published totals was checking our arithmetic against itself.
- **Almost no published cross-check can tell the two apart.** On the blocked-step
  beep the install cost is 0.11 percent of the total; on the Stonegate descent,
  0.48 percent per tone. Both agree with any per-tone constant between zero and
  forty inner units, so reporting them as confirmation would be circular. The
  only discriminating check in either document is the 40-update action snap,
  where the install cost is about 16 percent of each update: **42.2 ms derived
  against 40.0 ms fitted, against a published 40 ms.** That is a 5 percent
  disagreement, comfortably inside the plus-or-minus-10-percent band of section
  7.1 - which is exactly why it went unnoticed, and exactly why it needs a
  cycle-accurate run rather than more desk work.

**What moves if 17.4 replaces 12.** Only recipes whose update interval is one
calibrated unit move materially, from 1.000 ms to 1.048 ms per update: the
action snap 40 to 42 ms, the cast failure 50 to 52 ms, the 2500-to-800 sweep 301
to 314 ms, the dungeon wall drip 20/12/4 to 21/12.6/4.2 ms. Five-unit-interval
recipes shift by under 1 percent; the long descent, the Stonegate sweep and the
blocking beeps are unchanged to within 0.5 percent. Every sweep additionally
gains the one-time 0.18 ms setup term. All of those movements land inside the
bands `audio.md` section 10 already publishes, so this is a refinement within a
stated tolerance rather than a withdrawal - but the underlying per-tone figure
is nonetheless 45 percent different, and an engine carrying the old one will
drift on any recipe with a short update interval.

**Mute.** The tone-start path returns early when sound is off, saving about
0.046 ms of the install cost per tone. That is 0.13 percent of the long descent
and about 4 percent of a one-unit-interval sweep, so **muting does not preserve
duration exactly**: it shortens an effect in proportion to how little of that
effect is spin. `audio.md` section 3 carries the same statement in audio terms.

**A note on the constant behind the anchor.** The same pricing pass refined the
calibrated wait's fixed per-outer-pass overhead from about 10.5 to about **9.8
microseconds**, because the inner-count reload needs no address calculation.
That puts one outer unit at **0.8757 ms**. The published anchor of 0.88 ms in
section 7.1 is unchanged: the two agree to 0.5 percent, far inside its own band.
Use 0.88 ms. The third digit is only needed when separating an install cost from
a recipe total.

**Tolerance.** Install costs carry about plus or minus 6 percent in clocks,
driven by the data-dependence of the division instructions, the I/O wait-state
count, and instruction-queue refill after calls. Expressed in inner units they
carry between 6 and 8 percent, the wider figure applying when the inner-unit
band enters as the denominator; the band quoted at the head of this subsection
is the narrower one. Whole-recipe totals stay at the plus or minus 10 percent of section
7.1, dominated by the calibration count; the install cost contributes materially
to that band only when the update interval is one unit.

#### 7.4.2 The rumble's per-iteration cost is linear in the step

> **Derived, approximate.** One random-rumble iteration costs a fixed
> **0.125 ms** - about 12.5 inner units - **plus `step` outer passes of about
> 0.0596 ms each**, each pass being five inner units plus the per-outer-pass
> overhead. It is **not** a constant.

```text
iterations    = ceil(target / step)
per_iteration = 0.125 ms + step x 0.0596 ms
duration      = iterations x per_iteration
```

The fixed part itemises as the jitter-state advance, the pitch mapping (a second
division), the retune core, the shift setup, the spin bookkeeping and the loop
test. Two independent recounts of it landed 2 percent apart, at 12.5 and 12.8
inner units, which is inside the tolerance stated in section 7.4.1; 12.5 is the
value used in the closed form.

Derived durations, with nothing fitted to them:

| Recipe | Step | Target | Iterations | Derived | `audio.md` 10.2 |
|---|---:|---:|---:|---:|---:|
| Trap or failed reagent mix | 40 | 3000 | 75 | 188 ms | 188 ms |
| Ordinary damage presentation | 10 | 1600 | 160 | 115 ms | 115 ms |
| Short sting, each half | 1 | 25 | 25 | 4.6 ms | 4.6 ms |

**A single fitted per-iteration constant is wrong, and the way it is wrong is
instructive.** Expressed in the shape an implementation is likely to hold it -
"five inner units per outer pass, plus K per iteration" - the derived K is

```text
K(step) = 12.5 + 0.99 x step   inner units
```

so K is 52.1 at step 40, 22.4 at step 10 and 13.5 at step 1. An implementation
reported a single fitted **K of 53** (issue #146 follow-up). That is right,
within 2 percent, for the trap rumble - and only for the trap rumble, whose step
happens to be 40. It is **2.4 times too high** for the damage rumble and **3.9
times too high** for the short sting. The 53 is a composite of a genuinely
per-iteration 12.5 and forty copies of a per-outer-pass 0.99: **the step count
leaked into what was recorded as a constant.** Replace the constant with the
linear form above.

**Why the two fitted numbers looked like siblings, and why they are not.** The
rumble's per-iteration fixed part and the per-tone install cost contain the same
retune atom - one division plus two divisor writes. Around that shared atom,
tone-start spends its remaining budget on a call frame and a flag test, while a
rumble iteration spends rather more on a pseudo-random advance, a second
division and spin setup. Two different routines, one shared atom, superficially
comparable totals. They are not the same quantity in any sense, and neither is a
constant of the kind a single fitted number can capture.

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
9. **The per-tone install cost of section 7.4.1 disagrees with the value the
   implementation side is using**, 17.4 inner units against a fitted 12, and
   nothing in this repository can settle the disagreement: only one published
   cross-check discriminates between them, and it disagrees by 5 percent, which
   is inside the band. A cycle-accurate run of the 40-update action snap would
   settle it in minutes and has not been done. Until then, both figures are on
   the record and the derived one is the published contract.
10. **Only two per-tone loops were priced.** The four-phase swept envelope and
    the shrine dispatch were not priced at all, and other call sites may wrap
    the same primitives in more or less bookkeeping. Nothing in 7.4.1 should be
    generalised to them.
11. **Whether an implementation applies its per-tone constant to the
    blocking-tone wrapper as well as to sweeps was not established.** If it
    does, the right figure there is 18.8 inner units, not 17.4.
12. **The timer's mode and access latch are assumed, not verified.** The game
    never writes the mode port, so every divisor and carrier figure that depends
    on it inherits the assumption that the inherited BIOS latch is the
    conventional mode with low-then-high byte access (`audio.md` section 8.6.1
    records the same assumption for the driver's own carrier).
    If it were low-byte-only, several derivations collapse rather than shift.

## 8. Gameplay Idle Cadence And Catch-Up

Sections 5 through 7 cover the intro and the calibrated audio/presentation
waits. This section covers the loop the player actually spends the game in: the
wait-for-command pump. It was previously unpublished.

### 8.1 One hardware timer tick per idle pass

> **Normative.** Each pass of the wait-for-command loop paints one frame of the
> animated text cursor, polls the keyboard once, and — if no key was pressed —
> waits until the next hardware timer tick and then performs **at most one**
> world step. There is exactly **one** wait per pass. Not two, and not
> unthrottled polling.

The keyboard poll is a non-blocking peek, so the poll itself never waits; the
timer wait is the only blocking operation in a pass.

**The two-tick figure published for the main menu is not transferable to
gameplay.** A menu pass contains two separate one-tick waits — one in the shared
cursor-poll helper and a second inside the title-animation step — and the menu
additionally disarms the elision of Section 8.3. Gameplay has only the first
wait and disarms nothing. See the "Menu idle pump" row of Section 5.1, which
remains correct for the menu.

**The timer rate is the stock BIOS rate, and that is structural rather than
estimated.** Nothing in the executable, in any overlay, or in any of the four
display drivers programs the interval timer's counter 0 — there is not a single
write to its command or data port anywhere in the shipped code, and no read of
it either. The tick period is therefore exactly **54.9254 ms (18.2065 Hz)**,
given the untouched divisor.

**Independent measurement agrees.** The clean implementation side timed the
shipped game's idle-screen animation onto one shared clock at **54.913 ms
(18.2105 Hz)** over 89.948 s and 1638 transitions — within 0.02 percent — and
obtained the identical figure at two very different emulated CPU speeds. That
control is what establishes empirically that the loop is timer-driven rather
than CPU-calibrated. Where a figure in this document and that measurement meet,
**the measurement is authoritative**; nothing in Sections 8.1 to 8.5 was
verified at run time on this side.

**Model the wait as "block until the next timer edge", not "block for one full
period".** The helper zeroes its own counter, installs a counting interrupt
handler, spins until that counter reaches the requested count, then uninstalls
and restores the previous handler. The loop therefore synchronises itself to the
timer grid: each pass ends on a tick boundary, and the effective steady-state
period is the per-pass work rounded up to a whole number of ticks. Only the
first pass after entering the loop blocks for an arbitrary fraction of a tick.

Whether the per-pass work fits inside one tick on the original 4.77 MHz baseline
was deliberately not modelled. If it does not, the steady-state cadence on a
throttled host is a whole multiple of 54.9254 ms rather than exactly one.

### 8.2 The same loop paces every prompt in the game

This wait is not specific to the three mode loops. It is the game's universal
wait-for-a-keystroke routine, reached from **at least 100 call sites across 20
of the shipped code images**: the overworld, town and combat command waits, but
also shop and merchant prompts, conversation prompts, spell and item prompts,
the character status pages, the endgame sequence, the Look command, and the
Blackthorn audience. All of them run the identical loop, so all of them pace at
one tick per pass and all of them perform the same per-pass world step whenever
the current scene value permits it. **That shared behaviour belongs to the
routine, and it is what an engine must reproduce: implementing any of these
prompts as a plain blocking key read - one that stops the world for as long as
the prompt is up - is wrong.**

*What that implies for any one caller is an inference from the shared routine,
not a traced result for that caller.* On that inference a shop prompt inside a
town, whose scene value lies outside the suppressed band below, keeps the world
animating and rolling creature AI while it waits for a key. What the shop path
does with the returned key was not traced, and the census that places it among
the callers covers direct near calls only (scope note below), so publish that
instance as *probable*; a capture at a shop prompt settles it.

*Scope.* That census covers direct near calls only; calls routed through the
overlay trampoline table, indirect calls and computed targets are not covered,
so 100 is a lower bound. What each caller does with the returned key was not
traced — the shared behaviour above follows from its being one routine.

Two further idle pumps share the one-tick wait but not the world step: a
Look-object print-and-wait loop that waits one tick per pass and performs no
world step, and a Look redraw loop that performs a single world step on exit
rather than one per pass. On the overworld the input helper performs one
scripted step-and-wait — one world step followed by one one-tick wait — before
either entering the command wait or, when sails are set, performing a bare
cursor poll instead; so an **under-sail auto-advance pass costs two ticks and one
world step and never enters the command wait at all**.

**The world step is suppressed for a contiguous band of scene values.** The
shared wait tests the current scene value and performs no world step for values
`0x21` through `0x7F` **inclusive**; both the bound and its inclusiveness are
exact. First-person dungeon scenes occupy `0x21..0x28` and therefore get no idle
world step — they run their own loop instead, which uses the same cursor-poll
helper and so inherits the same one-tick pacing and four-frame cursor, but whose
per-pass work is a first-person re-render and a rumble step, with no viewport
rebuild, no sprite animation, no wind check and no moongate or beacon work.
Combat sets scene value `0xFF` and does run the world step. Implement the gate
as a numeric range test on the scene value, **not** as an "is this dungeon mode"
test: the band is a strict superset of the dungeon scenes, and the intro,
character-creation and Return-to-View animation states (`0x40`, `0x41`, `0x42`)
also lie inside it. On present evidence those three matter to the gate's
definition rather than to observable gameplay, because neither the intro nor the
character-creation code appears in the shared wait's caller census.

### 8.3 The one place the cadence is conditional — *probable*

The one-tick wait has a fast path, and an engine must not drop this
qualification.

> **A request for exactly one tick returns immediately, performing no wait at
> all, when the boot speed-calibration value of Section 2 is at or below 240.**

Nothing on the gameplay path overrides that value (Section 8.4), so during play
the decision is made by the host's actual measured speed. Above the threshold
the wait runs and the cadence is one world step per timer tick. At or below it,
the gameplay idle loop performs no wait at all and free-runs at whatever the
per-pass rendering costs.

**Which side of that threshold the original hardware falls on is modelled, not
measured, and is published as `probable`.** The calibration is produced at boot
by counting iterations of a short memory-increment loop between two consecutive
timer ticks and scaling the count by `18 / 750`. A cycle model of that loop on a
stock 4.77 MHz 8088 puts the result near 87, with a hard ceiling near 92 imposed
by the bus rate (Section 7.2); reaching 240 would require about 26 processor
clocks per iteration, which is below the instruction-plus-bus floor. The
direction is robust — original XT-class hardware almost certainly falls below the
threshold and free-runs — but it rests on a static cycle model and a black-box
capture outranks it. The observable signature is direct: **on a throttled host
the animated text cursor steps at a uniform interval of about 55 ms; where the
fast path fires it runs faster than that and varies with machine load.** The
capture cited in Section 8.1 shows the uniform 55 ms signature, so on that host
the wait was performed.

Two properties of this gate a naive implementation gets wrong:

- **The mapping from host speed to "throttled" is not monotonic.** The boot
  loop's iteration counter is a 16-bit quantity with no clamp, so a host fast
  enough to complete more than 65,535 iterations within one timer tick — roughly
  1.19 million iterations per second, well within reach of a modern machine or a
  high-speed emulator configuration — wraps the counter and the calibration
  restarts from a small value. That can drop an extremely fast host back below
  the threshold and **re-arm** the elision. Do not model "faster host implies
  larger calibration" without bound.
- **The comparison against the threshold is signed.** For every value the boot
  routine can actually produce this is immaterial, because the scaling caps the
  result near 1572, well inside the positive range. An implementation that
  stores the calibration in a wider type and lets it grow past 32,767 would
  diverge from the original.

This is the reverse of the intro and menu pumps, which deliberately *raise* the
calibration to 275 for the duration of their loops precisely so their waits can
never be elided (Section 5.2).

### 8.4 Calibration overrides during play

Nothing on the gameplay path overrides the calibration. Across the executable
and every overlay only three routines write it: the boot routine that measures
it, the intro sequence, and the "display a message and wait for a key" helper.

The message-wait helper raises the calibration to 500 for its own duration, but
**only when its count argument is greater than one**; the raise and the restore
are gated identically. So a message-box key wait with a count above one is paced
at one timer tick per poll on every host, including hosts where the main idle
loop's wait is elided, and its count argument is effectively a timeout expressed
in timer ticks. With a count of one (a single poll) or zero (wait indefinitely
for a key) the calibration is left alone and the elision can still fire.

*Scope.* Covers accesses to the calibration value encoded with an absolute
displacement, over the executable and all overlays: 19 sites, each attributed. A
write through a computed base or index register, a block store with a computed
destination, or an indirect call reaching the calibration store is not excluded;
none was found. This is the same residual Section 7.6 item 7 records for the same
value.

### 8.5 Catch-up: there is none, and it is structural

> **Normative.** The gameplay loop cannot run catch-up steps, and the surplus is
> dropped. In outcome this is exactly the "at most one step per interval, drop
> the surplus" rule Section 5.3 publishes for the intro pumps, and an
> implementation of that rule behaves correctly here.

It is worth recording *why*, because the mechanism differs from a deadline check
in one respect that matters:

- The loop keeps **no elapsed-time accumulator** and performs **no deadline
  comparison** anywhere.
- The wait helper zeroes its own counter at the start of every call and installs
  its counting handler only for the duration of that one wait, restoring the
  previous handler afterwards. Timer ticks that elapse while the world step
  itself is running are counted nowhere and are invisible to the program.
- Outside a wait, the game is not measuring time at all. Across the executable,
  every overlay and every display driver, only two routines touch the periodic
  timer interrupt vector: the boot calibration routine and this wait helper. The
  only other wall-clock source in the build is the system time-of-day read,
  which occurs at exactly one place and is called from exactly two sites, both
  inside the copy-protection check — never from any gameplay path.
- The loop body performs at most one world step per pass, unconditionally on the
  no-key path, with no repeat count and no "while behind" construct. A step that
  overruns its interval simply finishes late; the following wait then runs to the
  next timer edge, the loop re-locks to the timer grid, and the intervening edges
  are never replayed.

**The difference from a deadline check:** because the pacing is a wait rather
than a comparison, it disappears entirely rather than degrading gracefully when
the fast path of Section 8.3 elides it. An engine implementing the Section 5.3
rule with a real accumulator is *more* stable than the original, which is an
acceptable modernisation, but it is not identical behaviour on a host below the
threshold.

The game's own scripted-pause primitive states the same discipline explicitly:
it runs a requested number of steps as a strict alternation of one world step
followed by one one-tick wait, sequentially, never batching, and it is itself
gated off when the master redraw gate is clear.

One detail for anyone modelling interrupt behaviour: the counting handler **does
not chain**. It reloads its own data segment from a fixed constant, increments
the counter and returns from the interrupt without calling the handler it
displaced, so any resident periodic-timer hook installed by the host environment
is suppressed for the duration of every wait.

*Scope.* "No other periodic-timer handler is installed anywhere" covers the
standard vector get and set encodings over the executable, all overlays and the
four display drivers; six matches, all inside the two named routines. A vector
write built from a computed register value, or a direct poke of the vector
table, is not excluded and none was seen. "No other elapsed-time reader" covers
direct near-call sites to the time-of-day reader across the executable and all
overlays. The "at most one step per pass" claim is verified for the shared
command-wait loop and for the first-person dungeon loop; the intro and menu
pumps were not audited for catch-up behaviour.

### 8.6 What the idle pass does, and what it does not

The per-pass world step and its two gates — including the freeze that runs for
the whole duration of the Negate Time effect and the Tandy-only first-pass
sentinel — are specified in `systems/animation.md` Section 13, which also gives
the relative rates of the animated tile families. The re-composition of actors
that happens on the same pass, and the variant re-roll it performs, are in
`systems/visibility.md` Section 8.

What is *not* on this path, confirmed by capture: the game clock, the calendar,
food and gold, party status, and the NPC schedule walk. Over 160 s of idle with
no input none of them changed, and town NPCs animated in place without stepping.
They advance in the per-turn epilogue after a command has been executed. **The
one world state observed to change with no player input is the prevailing
wind**, which is a per-pass random event rather than a timed one
(`systems/animation.md` Section 13.2); two capture sessions gave visibly
different rates for it (about 0.22 and about 0.117 visible changes per second)
with a broad irregular interval distribution in both, so no wall-clock rate for
it should be committed to.

### 8.7 Open items for this section

1. Whether the per-pass work fits inside one timer tick on the original
   4.77 MHz baseline. Deliberately not modelled; needs a capture, not desk work.
2. Which side of the 240 threshold a given emulator configuration lands on. The
   calibration is measured at boot from the host's real speed and no attempt was
   made to convert an emulator cycles setting into a calibration value. The
   cursor signature in Section 8.3 settles it observationally in seconds.
3. Whether the calibration counter's 16-bit wrap is reachable on any host the
   implementation will actually be tested against.
4. Whether the intro, menu, conversation and message-wait pumps share the
   no-catch-up property. Only the shared command wait and the dungeon loop were
   audited.
5. Membership of the suppressed scene band beyond the two pinned sub-ranges. The
   dungeon scenes and the intro/front-end states are established to sit inside
   `0x21..0x7F`; roughly half the band is unmapped. Do not implement it as "the
   dungeon range" and do not implement it as anything narrower than the numeric
   test.

## 9. Sources

This public description is a cleanroom prose rewrite from private timing-helper
analysis. It does not reproduce decompiled source, assembly listings, raw bytes,
or private address tables.

The delay-context census of section 6 and the wall-clock derivation of section 7
are cleanroom restatements of a static analysis of the shipped resident and
display-driver wait loops, cross-checked against a second independent derivation
that reached the same anchor once its own machine model was applied
consistently. Neither derivation was validated at run time; section 7.6 records
that as the largest open gap in this contract.

Section 8 is a cleanroom restatement of a static analysis of the shipped
wait-for-command loop, the shared tick-wait primitive and its fast path, the
boot calibration's writers, and the periodic-timer and time-of-day censuses,
across the executable, all code overlays and the four display drivers; it was
repaired after an adversarial verification pass, and the scope limits that pass
attached to each negative are carried in the prose rather than dropped. The
wall-clock measurement it cites, and the two-CPU-speed control that establishes
the loop as timer-driven, are black-box runtime observations contributed by the
clean implementation side on issue #179 and are authoritative over any figure
derived here.

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
