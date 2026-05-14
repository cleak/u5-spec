# Launcher and Startup Contract

## 1. Scope

The IBM PC baseline for Ultima V has no separate game-owned launcher program
in the analyzed clean install. The executable entry point is `ULTIMA.EXE`.
Modern distribution wrappers, DOSBox configuration files, desktop shortcuts,
and cloud-save overlays are packaging conveniences around the original game;
they are not part of the original engine's startup logic.

This spec defines the public startup contract an implementation should expose:
what program is launched, which command-line display selector is recognized,
what files must be available before startup can continue, how control reaches
the intro menu, and what belongs outside the engine boundary. The lower-level
machine probe, runtime startup stub, and boot initialization sequence are
specified in `boot.md`.

## 2. Executable Boundary

The game-owned code set consists of one DOS MZ executable, raw overlay files,
and display-driver files. The executable is the root:

| Component | Startup role |
|---|---|
| `ULTIMA.EXE` | DOS program image and resident core. |
| `DATA.OVL` | Resident shared data image loaded by startup/resource code. |
| `INTRO.OVL` | First overlay entered by the resident core; performs boot initialization and shows the title/menu flow. |
| `*.DRV` | Display-driver modules selected by the display argument and startup detection. |
| Other `*.OVL` files | Loaded later through the overlay dispatcher as game modes or command handlers need them. |

No `ULTIMA5.COM` launcher is present in the canonical analyzed file set. If a
distribution contains a batch file, emulator profile, shortcut, installer
launcher, or storefront wrapper, treat that file as host packaging unless it is
independently proven to be original game code.

## 3. Command Line

`ULTIMA.EXE` accepts an optional one-character display selector as its first
argument. Startup folds the first character to uppercase and uses it to seed
the display-driver choice:

| Argument letter | Requested driver family |
|---|---|
| `C` | CGA |
| `E` | EGA |
| `T` | Tandy |
| `H` | Hercules |

If no selector is present, startup leaves the explicit selector unset and lets
the intro/display initialization path apply its default detection and fallback
rules. The display-driver loader ultimately chooses one of the four shipped
driver modules and records the selected mode in resident state.

Only the first character of the first argument is relevant to this contract.
Additional arguments have no known gameplay meaning in the current analysis
and should be ignored unless future startup tracing proves otherwise.

## 4. Startup Sequence

Startup proceeds in layers:

1. DOS loads `ULTIMA.EXE` as an MZ program and transfers control to the
   executable's runtime startup layer. See `boot.md` for the low-level entry
   and machine-probe contract.
2. The runtime startup layer establishes the process state and transfers
   control to the resident main function.
3. The resident main function parses the optional display selector, initializes
   early resident state, records DOS drive information, and calls the intro
   overlay.
4. The intro overlay performs the real boot initialization: machine detection,
   critical-error and break-handler setup, text-window initialization,
   display-driver loading, video-mode setup, title-art presentation, path
   animation, and the intro-menu loop.
5. When the player chooses a menu path, the intro overlay either starts a new
   character, loads or transfers a save, shows informational sequences, or
   returns to the resident main loop with the scene state set for normal play.
6. The resident main loop then dispatches forever among overworld, town,
   dungeon, and combat-related flows until a quit path exits through DOS.

This means there is no "launcher mode" after the executable begins. The
startup contract is a one-way transition from DOS program entry to the intro
menu and then to the resident game-mode loop.

## 5. Required Files

A startup environment must provide the resident executable and the data files
that the intro path can reach before ordinary gameplay starts:

- `ULTIMA.EXE`.
- `DATA.OVL`.
- `INTRO.OVL`.
- The four display drivers, or at minimum the driver selected by the command
  line or detection path.
- Title, intro, font, and path assets used by the intro/menu flows.
- Save seed or save files only when the selected menu path needs them.

Missing display-driver files are fatal for the corresponding display mode. A
missing intro overlay, resident data image, or required title/menu asset should
abort startup with a clear asset error. A missing save should affect only
Journey/Continue-style menu paths, not the ability to reach the title menu.

## 6. Display Driver Selection

The launcher contract does not require a separate pre-executable hardware
detector. The original executable owns display selection:

- The command-line letter sets one of four requested-driver flags.
- The intro startup path performs machine detection and applies any hardware
  fallback rules.
- The driver loader selects the matching `*.DRV` file and installs its dispatch
  entry for subsequent rendering calls.
- Scene and asset code chooses colour-depth-specific resources after the mode
  is known.

For a modern engine, expose this as a user-visible display backend option
rather than as a DOS command-line quirk. For compatibility tooling, support the
single-letter selector because it is how the original DOS executable receives
an explicit mode request.

## 7. Packaging Boundaries

Do not model these as original engine behaviour:

- DOSBox `mount` commands.
- Overlay-mounted cloud-save directories.
- Storefront launchers.
- Desktop shortcuts.
- Installer-created configuration files.
- Host fullscreen, scaler, cycle-count, or sound-device options.

Those settings decide how an emulator starts DOS and where files are found.
Once DOS executes `ULTIMA.EXE`, the game-owned startup contract begins.

Likewise, a cleanroom implementation should not require a wrapper named after a
modern package. The portable engine entry point can be its own binary or
front-end command, but the emulated original startup path begins at
`ULTIMA.EXE` semantics.

## 8. Exit Behaviour

Normal gameplay does not return to an outer launcher. The resident main loop is
effectively permanent. Exit occurs through game commands that eventually call
the DOS terminate path, restoring control to the surrounding DOS or emulator
environment.

A modern implementation may return to its own title screen, desktop shell, or
front-end menu after quit. That is host application behaviour. The original
engine contract is simply "quit terminates the DOS process."

## 9. Validation and Error Handling

An implementation should validate startup inputs before entering gameplay:

- The executable/resource set should match the IBM PC baseline: one executable,
  the expected overlays, and the display-driver family.
- If a user supplies a display selector, it should be one of `C`, `E`, `T`, or
  `H`; unsupported letters should either be rejected or treated as "no explicit
  selector."
- Missing required boot resources should stop startup before any save state is
  mutated.
- Missing optional save files should be reported only when a menu path tries to
  load them.
- Packaging files should not be required for engine correctness.

When building compatibility tests, treat "there is no `ULTIMA5.COM` in this
baseline" as an invariant. A later release or another platform may have a
different wrapper, but that would be a version-specific packaging difference,
not part of this IBM PC engine baseline.

## 10. Boundaries and Variations

- No-selector display fallback is not launcher-owned. The launcher contract
  ends at "no explicit selector was supplied"; `boot.md` owns machine/display
  detection, selector reconciliation, and the remaining EGA sentinel policy.
- There is one resident display-driver dispatch cell. The separate resident
  screen-mode dispatch cell is a resident executable controller, not a second
  driver ABI. Its contract is specified in `screen-mode-dispatch.md` and its
  separation from the loaded driver ABI is specified in
  `display-driver-abi.md`.
- This document covers the analyzed DOS/GOG file set. Other historical PC
  distributions should be compared before making cross-version claims.

## 11. Sources

This spec is a cleanroom rewrite derived from the following analysis notes and
inventory evidence. It intentionally omits private addresses, assembly, and
raw executable bytes.

- Code-file inventory and absence of a separate `ULTIMA5.COM` code file in the
  analyzed baseline - `u5-decomp/code-inventory.md`.
- DOS entry into the executable, runtime transfer to the resident main
  function, and machine/display detection - `systems/boot.md`.
- Command-line display selector parsing, intro-overlay call, and resident
  mode-dispatch loop - `u5-decomp/functions/ULTIMA_EXE/0x0000_main_game_loop.md`.
- Display-driver loading from startup flags -
  `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- Intro overlay's boot initialization, title/menu loop, and handoff into
  normal play - `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Resident screen-mode dispatch ownership and its separation from the loaded
  display driver ABI - `systems/screen-mode-dispatch.md` and
  `systems/display-driver-abi.md`.
