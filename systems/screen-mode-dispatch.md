# Screen-Mode Dispatch

## 1. Scope

This document specifies the resident screen/prompt presentation controller used
by the DOS baseline. It is not the display-driver ABI and it is not a gameplay
mode loop. It is the resident presentation handoff that reacts when another
system has selected a presentation mode, disk-prompt context, or mode-specific
setup.

Gameplay systems own their own state transitions: overworld, town, dungeon,
combat, intro, shops, and endgame decide what gameplay loop should be active.
This controller owns the visible prompt and setup work around those calls:
clearing regions, rebinding text windows, printing mode or disk labels,
invoking driver fill/colour helpers, and guarding against recursive
presentation calls.

## 2. Dispatch Cell

The resident core keeps a far-call cell for this presentation controller. That
cell points back into the resident executable, not into the loaded display
driver. It is therefore separate from the driver dispatch cell documented in
`display-driver-abi.md`.

The cell has three observable states:

| State | Meaning |
|-------|---------|
| Active presentation handler | Normal state. Calls run the controller described here. |
| Immediate-return guard | Temporary state installed while the controller is already running. Recursive calls return immediately. |
| Write-error handler | Temporary state installed by the save/load write wrapper while an inner file write is active. Write errors report through this handler, then the wrapper restores the active presentation handler before retrying. |

The loaded display driver still receives drawing calls through the driver ABI.
The presentation cell is a resident orchestration hook that may call the driver,
but it is not itself a driver entry.

## 3. Recursion Guard

On entry, the controller installs the immediate-return guard into its own
dispatch cell. If any nested text, bitmap, or driver setup path calls the
screen-mode cell before the outer call finishes, the nested call does nothing
and returns to its caller.

Before returning from the outer call, the controller restores the dispatch cell
to the active handler. A compatible implementation should preserve this
re-entrancy rule: mode setup is single-depth, and nested mode refreshes are
suppressed rather than queued.

## 4. Mode State

The controller reads the current presentation-mode byte from resident
session-only state and uses that byte as an index into a per-mode state table.
This state family is also used by the disk-swap prompt layer to remember the
running disk-prompt context. It is not a save-backed world-state flag and it is
not the gameplay scene selector. The controller also keeps a cached
"last rendered" mode value that is compared against the current
presentation-mode byte.

The transition rule is:

1. Read the current presentation-mode byte.
2. Read that mode's state byte.
3. If the state byte is the inactive sentinel, skip the transition comparison.
4. If the current mode differs from the cached last-rendered mode and the
   mode-query helper says the cached state is no longer current, run the
   transition setup for the new mode.
5. Update the cached last-rendered mode when setup accepts the transition.

Some mode-state bytes below the printable-letter range have a low-bit toggle
path controlled by resident presentation flags. That toggle calls the same
mode-setup helper used by ordinary transitions. The public contract is that a
prompt or presentation mode can request a small state alternation without
changing the gameplay scene. The index-to-state-table mechanism is fixed; the
remaining presentation-parity work is the full table mapping each
presentation-mode value to its visible setup branch and prompt path.

## 5. Disk-Prompt Request And Retry

The disk-swap layer uses the same resident state family as the presentation
controller, but with a narrower contract. A disk-prompt request first normalizes
the requested prompt mode: historical mode values two and five are folded to
mode one, while other values are preserved. It then writes the normalized active
disk or drive hint into the current-mode byte, looks up that hint in the
per-mode prompt-state table, and invokes the mode-setup helper only when the
looked-up prompt state requires visible work. The request also marks the
rendered-mode cache so the same prompt is not redundantly treated as an
ordinary scene repaint.

The read retry helper consumes that active disk hint before each attempted
file read. For the full-install or no-swap case, the helper can skip the
visible swap request when the per-mode table says no disk prompt is needed. If
the active hint and table state say a prompt is required, it reaches the
screen-mode dispatch cell directly, waits for the user-visible prompt path to
complete, and then retries the underlying read.

This layer does not define file semantics. It only owns the prompt and wait
presentation around disk changes. The open/read/seek/count behaviour, zero
return retry signal, and unbounded retry loop are specified in
`systems/save-load.md`.

The write wrapper uses the same resident cell for a narrower purpose: before
calling the inner file writer, it installs a write-error handler in the cell;
after the writer returns, it restores the normal presentation handler. This is
not a fourth gameplay or presentation mode. It is the save/load layer's
write-side critical-error path, used so write failures can report through a
different prompt family than ordinary read/disk-swap failures.

## 6. Visible Work

Depending on the selected mode and state byte, the controller can:

- call the resident mode-setup helper with the mode value or toggled state;
- set or query the current display mode;
- clear rectangular screen regions through the display driver;
- set the current drawing colour through the display driver;
- re-bound the active text descriptor rectangle;
- print resident labels and punctuation through the text-output system;
- draw individual characters;
- run short input/poll helpers used by presentation and disk-prompt flows;
- invoke page or back-buffer helpers for modes that need staged display work.

The controller is presentation-side glue. It does not itself advance game time,
move actors, mutate inventory, resolve combat, or load scene data. Those effects
belong to the caller that selected the mode.

## 7. Compatibility Rules

- Keep the screen-mode dispatch cell separate from the display-driver dispatch
  cell.
- Suppress recursive screen-mode calls while one mode dispatch is active.
- Treat the presentation-mode byte and per-mode state table as resident
  session state that must survive across calls during a session but does not
  round-trip through saved-game files.
- Treat disk-swap prompts as presentation state around I/O. A modern
  single-directory installation may no-op the visible disk swap, but should
  still preserve the retry/error semantics owned by the I/O layer.
- Do not use this controller as the gameplay scene dispatcher. The main loop
  and overlay mode loops own gameplay scene selection.
- Preserve the distinction between mode setup and rendering helpers: driver
  calls draw pixels, text-output calls draw text, and the controller sequences
  them.

## 8. Controller Boundary And Remaining Parity Work

The resident controller contract is complete at the level needed by gameplay
and save/load callers: the dispatch-cell ownership, recursion guard,
session-only mode state, disk-prompt retry boundary, write-error handler swap,
and display/text helper sequencing are public. Modern engines should preserve
those call boundaries even when the historical disk-swap prompt is hidden by a
single-directory installation.

Remaining exactness is presentation parity, not gameplay state:

- **Per-mode table.** The final presentation-mode value to visible setup or
  prompt-path mapping belongs in a clean public table once each mode branch is
  decoded.
- **Prompt helper roles.** Several helper calls inside the controller are known
  only by their visible family: input/poll, mode query, mode setup, and
  page/back-buffer support. Exact user-visible effects and the historical
  disk-label text for each prompt-state entry should be promoted when traced.
- **Prompt-mode labels.** The disk-prompt request path's normalization and
  active/inactive table gate are specified, but the user-facing label for each
  historical prompt-state entry remains a floppy-install presentation detail.

## 9. Sources

This is a cleanroom behavioral rewrite from private resident function analysis.
It does not reproduce private source, decompiler output, assembly excerpts, raw
dumps, private address tables, or implementation listings.

- Resident screen-mode controller and dispatch-cell ownership:
  `u5-decomp/functions/ULTIMA_EXE/0x2322_screen_mode_dispatch.md`.
- Disk-prompt mode-state interpretation and save/load persistence boundary:
  `u5-decomp/notes/dosbox_probes_2026-05-07.md`,
  `u5-decomp/notes/system-trace_save-load.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x251E_disk_swap_request.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x256E_disk_swap_inner.md`.
- Write-side critical-error handler ownership:
  `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`,
  `u5-decomp/functions/ULTIMA_EXE/0xF0C6_write_file.md`, and
  `u5-decomp/notes/system-trace_save-load.md`.
- Display-driver dispatch separation:
  `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x2322_screen_mode_dispatch.md`.
- Text-output and display-driver helper boundaries:
  `systems/text-output.md` and `systems/display-driver-abi.md`.
