# Timing Calibration

## 1. Scope

This document covers the original engine's CPU-speed calibration used for short
delays and display/audio pacing. It is separate from the in-game calendar,
per-turn minute advancement, moon phases, torch duration, and vehicle timing
tags, which are specified in `time.md`.

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
changes. Its scratch counters are temporary presentation state.

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
| Return-to-View preview tick | One BIOS tick per preview tick | One preview tick advances the animated-tile frame table and active-object animation by one step, fires one title tick, rescatters preview actors, repaints the revealed columns, widens the strip reveal on every second tick, and polls the keyboard once. Commands request a fixed number of these; see `formats/location-dat.md` section 11. |
| Return-to-View local cell effect | One preview tick between steps | One of the fifteen shimmer steps of an open or close effect. |
| Return-to-View temporary actor draw | Eight pixel writes between preview ticks | One cell converges through exactly 256 one-pixel writes. After completed counts `8,16,...,248`, exactly 31 times, the wrapper runs one complete preview tick whose keyboard poll may abort; there is no tick or poll after count 256. |
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

For a v1 engine the recommended target is **14 ms per presentation step**,
giving a flourish of about **1.2 seconds**. Implement it as a wall-clock
requirement per section 5.3, not as a calibration emulation.

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
the one intro phase whose duration genuinely varied with host speed in the
original. Treating it as a fixed wall-clock target is a deliberate
modernisation, not a reproduction.

A keystroke ends the flourish early, but not by cutting to the next phase
mid-picture: the driver presents the completed final frame once before
returning, so the abort is visible as an instant snap to the finished mark
rather than as a partial one. See `intro.md` section 3.

**Residual.** The 10.5–15.8 ms bracket is derived from the calibration contract
and instruction-cost reasoning, not from a timed capture. A measured
wall-clock figure from an instrumented run would replace the bracket with a
single number; until then, treat 14 ms per step as the target and the bracket
as the tolerance.

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

## 6. Sources

This public description is a cleanroom prose rewrite from private timing-helper
analysis. It does not reproduce decompiled source, assembly listings, raw bytes,
or private address tables.

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
