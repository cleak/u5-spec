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
prior timer hook. A one-tick request may be skipped on sufficiently fast
calibrated machines to avoid hook overhead. This wait is for visible pacing
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
| `BRITISH.PTH` signature path | One BIOS tick per 32 consumed path bytes | Thirty-two path bytes (each encoding two nibble-deltas) are walked and painted; a single keyboard poll separates each byte within the chunk. |
| Start/menu screen animated reveal | Self-paced inside one driver call | The pseudo-random per-pixel dissolve of the inclusive rectangle `(0, 0)..(319, 100)` runs to completion in a single driver call. It is not a per-column, per-tick loop. |
| Start/menu subtitle ignition | Calibrated busy wait inside the driver | Runs once, on the animated start/menu path only, when the ignition resource is supplied. Self-paced; no BIOS tick. |
| Story step-1 rectangle reveal | Self-paced inside one driver call | The pseudo-random per-pixel dissolve of the inclusive rectangle `(40, 86)..(75, 120)` runs to completion in a single driver call. It is not a per-column, per-tick loop; see `intro.md` section 10. |
| Story `U` slide-show inter-slide pacing | Blocking keyboard wait | Bounded by player input; no wall-clock advancement except the cursor blink loop. |
| Menu idle pump (Return-to-View timeout) | One BIOS tick per no-key pass | One menu-idle pass advances; the title-tick is fired separately before each pass, so each no-key pass is one tick of wait plus one title-tick. |
| Acknowledgement screen pacing | One BIOS tick per scripted step | The acknowledgement screen uses its own scripted sequence of one-tick waits between paint steps. |
| Animation-script player (display-driver dispatch offset `0x6F`) | One calibrated delay unit per presentation step, driven by a byte-stream script | This is the same entry that plays the `TITLE.BIT` flourish above — it is the flourish player, not a credits or death-screen player. The script's frame and group structure determines the step count. |

The title-tick helper has the per-call BIOS-tick wait built into its body, so
intro callers do not add an external wait around it. The pacing of any phase
whose unit is "one title-tick call per X" therefore inherits the same ~55 ms
per step as a direct hardware-tick wait of one tick.

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

Two intro phases override the calibration during their inner loop so the
hardware-tick wait runs on every host, not just fast machines:

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

- Boot-time calibration helper and calibrated delay consumers --
  `u5-decomp/functions/ULTIMA_EXE/0x11B4_timer_calibrate.md`.
- Calibrated busy waits, hardware-tick waits, and bounded prompt/input waits --
  `u5-decomp/functions/ULTIMA_EXE/0x20C8_delay_calibrated.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x20FA_delay_with_int1c.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x1DDA_delay_with_input_check.md`.
- Title-tick helper (one-tick built-in wait, slot-0x69 dispatch) --
  `u5-decomp/functions/INTRO_OVL/0x2090_title_tick.md`.
- `BRITISH.PTH` per-stroke chunking and calibration override --
  `u5-decomp/functions/INTRO_OVL/0x0050_pth_walker.md`.
- Menu idle pump (`iter_until_kbd`) --
  `u5-decomp/functions/INTRO_OVL/0x094E_iter_until_kbd.md`.
- Start/menu reveal helper and intro slide-loop call sites --
  `u5-decomp/functions/INTRO_OVL/0x05B0_startsc_loader.md`,
  `u5-decomp/functions/EGA_DRV/0x256B_lfsr_pixel_dissolve.md`, and
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- Title-flourish player, its animation script, the presentation step counts,
  and the calibrated per-step wait --
  `u5-decomp/functions/ULTIMA_EXE/0x0D72_title_flourish_player.md`,
  `u5-decomp/functions/EGA_DRV/0x1DE8_delay_with_animation_step.md`, and
  `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`.
- Acknowledgement screen pacing --
  `u5-decomp/functions/INTRO_OVL/0x072E_ack_render.md`.
