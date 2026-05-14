# Boot Initialization

## 1. Scope

This spec covers the low-level DOS boot path between the DOS loader entering
`ULTIMA.EXE` and the intro overlay accepting title/menu input. It is narrower
than `launcher.md`, which owns the packaging and command-line contract, and it
is lower-level than `intro.md`, which owns title presentation and menu flow.

Boot initialization has four visible responsibilities:

- enter the resident main function from the DOS MZ startup stub;
- classify the host machine and graphics capability;
- reconcile hardware detection with any command-line display request;
- install the shared process, text, timing, and display-driver state that later
  modes assume already exists.

Modern engines do not need to reproduce DOS segment setup or BIOS probing
internally, but compatibility tooling and original-driver harnesses need the
same startup decisions and driver-selection outcomes.

## 2. Entry Chain

The analyzed IBM PC baseline starts directly from `ULTIMA.EXE`. There is no
required game-owned `ULTIMA5.COM` wrapper in this file set.

The observable entry chain is:

1. DOS loads `ULTIMA.EXE` as an MZ executable.
2. The compiler/runtime startup stub relocates the stack to private process
   storage, clears the general-purpose register set, and transfers to the
   resident main entry.
3. The resident main entry parses the optional display selector, prepares early
   resident state, and enters the intro overlay.
4. The intro overlay performs the remaining boot initialization before drawing
   the title/menu surface.

The runtime startup stub is not a gameplay dispatcher. It has no game-state
side effects beyond creating a usable process state for the resident main
entry. A byte-compatible harness that executes the original MZ image should
honour the executable header's initial entry and stack state, then let the
stub perform its own stack relocation and resident-main transfer. A modern
engine that starts from a native entry point may replace this with ordinary
process initialization.

## 3. Machine Class Probe

Boot classifies the host along two axes: machine family and graphics adapter.
The machine-family probe starts from the IBM-compatible BIOS machine id and
then applies a Tandy-specific signature scan for machines that report like an
ordinary PC.

The public machine classes are:

| Machine class | Meaning | Boot use |
|---|---|---|
| PC/PCjr-class | IBM PC or PCjr-style baseline | Generic low-capability path; PCjr skips the extended graphics probe. |
| AT-class | IBM AT / later compatible | General compatible path. |
| Tandy 1000 | Tandy-compatible system detected by ROM signature | Enables the Tandy display path unless the low-memory fallback rewrites it. |
| Other / generic XT-class | Non-matching or clone BIOS id | General compatible path with graphics probing. |

The Tandy signature scan is intentionally conservative: it only runs for the
BIOS id family that can hide a Tandy 1000 behind a PC-compatible id. When the
signature is found, boot stamps both the Tandy machine class and the Tandy
graphics capability.

## 4. Graphics Capability Probe

For non-PCjr machines not already classified as Tandy, boot probes the active
graphics adapter using BIOS video services and one Hercules/MDA port test.

The resulting capability values are semantic, not user-facing labels:

| Capability | Meaning | Driver family |
|---|---|---|
| Generic four-colour / monochrome fallback | No EGA extension and no Hercules retrace toggle, or ordinary CGA-style mode | `CGA.DRV`-style path |
| EGA | EGA BIOS extension present and usable | `EGA.DRV` |
| Tandy | Tandy 1000 16-colour path | `T1K.DRV` |
| Hercules | Monochrome mode with Hercules retrace behaviour | `HER.DRV` |
| EGA sentinel | EGA extension present in an unusual current mode | Unresolved startup-selection state; it must be normalized before loading a driver or treated as an unsupported display setup, not as a fifth driver. |

The Hercules distinction matters because MDA and Hercules share the same
monochrome text mode from the BIOS perspective. The original distinguishes them
by observing whether the Hercules/MDA status bit changes during a bounded poll.

## 5. Display Request Reconciliation

The command-line selector parsed by the resident main entry can force one of
the four driver families: CGA, EGA, Tandy, or Hercules. The resident parser
looks only at the first character of the first argument, folds that character
to uppercase, and leaves all explicit selector flags clear if there is no
argument or if the character is not one of the recognized display letters.
Additional arguments are not part of the startup contract. The display-driver
loader checks the resulting request flags before using the detected capability
as the driver selector.

The compatibility contract is:

- an explicit selector wins over automatic detection when its flag is set;
- if no explicit selector is present, the detected capability selects the
  driver family;
- unsupported selector characters behave like no explicit selector in the
  original parser; a modern launcher may reject them earlier as input
  validation, but the engine-level compatibility fallback is automatic
  detection;
- if the EGA sentinel reaches the display-driver loader unchanged and no
  explicit selector rewrites the display family, the traced loader takes no
  driver-load path. A compatible modern startup path should either normalize
  this host case deliberately or fail with a clear startup/display error;
- the selected family chooses both the `*.DRV` file and the high-colour versus
  low-colour intro asset suffix;
- Tandy mode reserves an extra small driver buffer before loading the driver;
- failure to load the selected driver is fatal for startup.

One historical fallback is machine-specific: a Tandy-class system with less
than 368 KB of conventional memory is downgraded to the generic low-colour path
before the driver and asset selection are finalized. The memory count is the
boot-time BIOS conventional-memory result captured by the timing calibration
helper, not a save-game value or gameplay resource.

## 6. Early Runtime Setup

Before the title/menu can render, the intro boot phase initializes shared
process state:

1. Clear the startup-owned uninitialized resident range used by intro/runtime
   state.
2. Run the machine and graphics probe described above.
3. Install DOS critical-error and Ctrl-Break handlers so disk prompts and aborts
   use the game's process-level handlers.
4. Initialize the four text-window descriptors used by every later text output
   path.
5. Initialize small resident flag/cache state used by input and display paths.
6. Install the timer-tick hook and CPU-speed calibration state used by cursor,
   delay, and animation timing, then capture the BIOS conventional-memory size
   used by the Tandy fallback gate.
7. Load the selected display driver and store its dispatch segment.
8. Enter the driver's initial graphics mode through the display ABI.

After these steps, the rest of the engine can assume text output, keyboard
polling, timer delays, display-driver dispatch, and disk-error handling are
available.

## 7. Boundaries

Boot initialization does not:

- load `SAVED.GAM` or mutate save state;
- run gameplay time, NPC schedules, weather, encounters, or combat;
- choose a gameplay scene;
- perform title/menu command dispatch beyond preparing the intro overlay to do
  so;
- require a modern wrapper, emulator profile, or launcher batch file.

Those behaviours belong to `save-load.md`, `time.md`, `main-loop.md`,
`intro.md`, and `launcher.md`.

## 8. Compatibility Rules

- Treat the MZ startup stub as process setup, not as game logic.
- Keep MZ header relocation and startup-stack arithmetic out of gameplay
  state. They matter only to a harness that directly runs the historical
  executable image.
- Preserve the command-line display selector letters described in
  `launcher.md` for compatibility tools.
- Keep machine class and graphics capability separate. Tandy is both a machine
  class and, after the signature path, a display capability; EGA and Hercules
  are graphics capabilities rather than machine classes.
- Use one of the four shipped display-driver families after reconciliation:
  CGA, EGA, Tandy, or Hercules.
- Keep boot-time real-time calibration separate from deterministic gameplay
  time. The calibration affects delays and presentation pacing, not turn costs.

## 9. Boundaries And Residuals

**EGA sentinel policy.** The traced display-driver loader bails if the
sentinel reaches it unchanged. Treat this as a startup-environment edge, not
gameplay state: a compatibility harness may preserve the historical no-load
outcome for that host setup, while a modern engine should normalize the display
selection deliberately or report a clear unsupported-display error before
driver loading.

## 10. Sources

This public spec is a cleanroom behavioral rewrite. It does not reproduce
private source, decompiler output, assembly excerpts, raw dumps, private address
tables, or implementation listings.

- DOS MZ entry and runtime transfer to resident main:
  `u5-decomp/functions/ULTIMA_EXE/0x81D0_boot_entry.md`.
- Machine and graphics detection:
  `u5-decomp/functions/ULTIMA_EXE/0x0DE0_detect_machine_type.md`.
- Intro boot-initialization root:
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Display-driver loading and selected-driver dispatch setup:
  `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- Startup command-line boundary and absence of a required launcher wrapper:
  `systems/launcher.md`.
- Timing calibration boundary:
  `systems/timing.md`.
- CPU-speed calibration and BIOS conventional-memory capture:
  `u5-decomp/functions/ULTIMA_EXE/0x11B4_timer_calibrate.md`.
- Local MZ relocation-table check against the shipped DOS `ULTIMA.EXE`, used
  only to confirm that startup-stub arithmetic is a process-loader boundary
  rather than gameplay state.
