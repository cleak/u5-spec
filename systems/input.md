# Input

## 1. Overview

Ultima V's input system is a single keystroke-at-a-time pipeline. A central "wait for the next command" routine paints a blinking text cursor, polls the keyboard, and — when nothing has been pressed — runs one resident redraw tick so active-object animation, visibility refreshes, moongate/event presentation, and viewport rendering keep moving while input waits. It does not advance the in-world clock or NPC schedules; committed actions do that through the per-turn mode loops. Once a key arrives, the routine folds it to upper case, optionally rewrites it as one of the engine's eight cardinal-or-diagonal direction codes, and returns it to the caller — usually one of the three top-level mode loops (overworld, town, dungeon), which then routes the byte through a per-letter command dispatcher.

The pipeline is non-blocking at the bottom: the keyboard is peeked, not waited on. Blocking is achieved by looping over the peek-and-tick step. This is why the cursor blinks at all and why the screen can keep animating while the game is waiting for exactly one command, without spending an in-world turn.

## 2. Idle vs Prompt Modes

The same wait-for-input routine is used in two distinct modes, controlled by a single byte of state — the *prompt-character* byte, written by whichever piece of the UI most recently displayed a Y/N or text prompt.

**Idle / open-ended command mode.** The prompt-character byte is outside the printable-ASCII range. Each iteration of the wait loop paints one frame of the blinking cursor, peeks the keyboard, and — on a miss — runs one *world tick*: the resident redraw orchestrator updates per-frame visual state and re-renders the viewport. NPC schedules and the in-world clock do not advance from this idle tick. Idle time is real time, not gameplay turn time.

**Prompt mode.** The prompt-character byte is a printable ASCII character — typically the last character of a prompt like `Y/N?` or `For how many hours?`. The cursor still blinks and the keyboard is still polled, but the world-tick step is suppressed. The world freezes while the player thinks. This is what makes it safe to ask "Are you sure?" without an attacking NPC crossing a tile in the meantime.

The two modes share every other piece of behaviour: cursor blink, key polling, case folding, direction translation, and one-keystroke-per-call discipline. Switching modes is a one-byte write by whichever component owned the prompt; nothing in the input system itself toggles modes.

## 3. The Cursor-Blink and Poll Loop

Inside each iteration of the wait loop, the engine performs a small fixed sequence:

1. **Save and suppress the cursor-advance gate.** The text-output system normally moves the cursor one cell to the right after every emitted glyph. The input system needs to draw and erase the blink in place, so it temporarily disables the advance gate, runs its blits, and restores the gate before returning. Save-and-restore on the local stack means a nested call (such as a text-input prompt that itself calls into this routine) composes cleanly.
2. **Paint the next blink frame.** A single 16-bit blink counter is incremented, and a glyph code is computed as `blink_base + counter`. The glyph code is sent to the per-cell text emitter at the cursor's current position. Because the advance gate is suppressed, the cursor stays on the same cell.
3. **Wrap the counter modulo a fixed limit.** When the counter reaches the wrap-around limit, it is reset to zero. The two parameters together — the base glyph and the modulus — fully describe the blink animation. (See the Cursor-Blink Parameters subsection for ranges.)
4. **Peek the keyboard.** A single non-blocking call into the keyboard hardware abstraction returns either zero (no key pending) or a translated key byte.
5. **Erase or rewind.** If a key arrived, the blink cell is overwritten with a literal space so the cursor visibly disappears at the moment the key is consumed. If no key arrived, the logical cursor X-position is rolled back by one cell (a side effect of the blit having been done with the gate suppressed already leaves it pinned, but this rewind handles the rare case where a nested emission did move it). Either way, the next iteration paints over the same physical cell.

The blink counter is a single global, shared across all four text windows. There is no per-window blink phase: only one cursor blinks at a time, and that is whichever window most recently received output.

### Cursor-Blink Parameters

| Parameter | Default value | Meaning |
|---|---|---|
| Blink base glyph | glyph code `4` | The first glyph code in the cursor-frame range. Each poll paints `base + phase` through the active font. |
| Blink modulus | `4658` poll calls | Number of blink/poll calls before the phase counter wraps back to zero. This is an input-loop iteration count, not a real-time duration. |

Both parameters are mutable resident values. A DOS-compatible loop can use the
same poll-count semantics; a modern fixed-timestep frontend should instead
derive a visually similar blink cadence from elapsed time while preserving the
same erase/rewind and no-advance behaviour.

## 4. Keyboard Hardware Abstraction

Every keyboard interrupt happens in one place — the *keyboard peek* routine called from inside the cursor-blink loop. From the rest of the engine's perspective, the keyboard is a pure function that returns either zero or a single translated byte.

The peek routine performs three steps:

1. **Status check.** Ask the BIOS whether a key is pending. If not, return zero immediately.
2. **Read the byte.** Use the platform's "direct console input" facility to consume one byte from the keyboard buffer without line-editing or signal handling (no echo, no Ctrl-C interception, no buffered line). The byte is either an ASCII character or zero.
3. **Classify and translate.** A non-zero byte falls through to "regular" ASCII handling. A zero byte triggers a second read for the *extended scancode*, which is translated against fixed tables for arrow keys, function keys, and a few other navigation keys. Anything that doesn't classify is returned as "no key."

After a successful read, the BIOS keyboard buffer is normally flushed (see Section 6) so any keys typed during the previous turn are discarded.

Classification produces three families of returned values, each in a non-overlapping byte range:

- **Regular ASCII** — printable letters, digits, punctuation, and a small set of control bytes (Enter, Backspace, Escape).
- **Function-key remap** — F1 through F10 become the contiguous internal
  byte range `0xC9` through `0xD2`, disjoint from printable ASCII and the
  direction codes.
- **Direction codes** — a small block, also in the high byte range, distinct
  from the function-key block. See Section 5.

Remaining byte values are unused; the engine treats them as "no key" and continues polling.

## 5. Scancode Translation: Numpad, Arrows, and Diagonals

Movement in Ultima V is eight-way. The player can request any of the four cardinal directions or any of the four diagonals. The input layer accepts several physical ways of asking for movement and translates them into one internal direction-code set:

| Source | What the player presses | Translated to |
|---|---|---|
| Numpad cardinals | numpad 4 / numpad 6 / numpad 8 / numpad 2 | west / east / north / south |
| Numpad diagonals | numpad 7 / numpad 9 / numpad 1 / numpad 3 | northwest / northeast / southwest / southeast |
| Extended arrow keys | up / down | north / south |
| Home / End / PgUp / PgDn | Home / End / PgUp / PgDn | northwest / southwest / northeast / southeast |
| Top-row digits with a modifier | digit `1` through `9` while Shift or NumLock is held | same as the numpad layout above |

The eight resulting direction codes occupy high byte values outside printable
ASCII, so a single returned byte unambiguously says either "the player typed
letter X" or "the player asked to move in direction D". The final input-layer
codes are:

| Direction | Final internal code |
|---|---:|
| Northwest | `0xD3` |
| Southwest | `0xD4` |
| Northeast | `0xD5` |
| Southeast | `0xD6` |
| West | `0xFB` |
| East | `0xFC` |
| North | `0xFD` |
| South | `0xFE` |

A separate flag internal to the keyboard peek marks numpad-equivalent input so
the upper layer can apply the final digit/cardinal translation. Diagonals are
already in their final high-byte range when they leave the keyboard peek.

Function keys F1 through F10 are also remapped into a different contiguous
block, returned directly without passing through the numpad/direction-code
path. The resident A-Z command dispatcher does not own this block. Mode loops
or menu-specific input handlers must either consume these codes before letter
dispatch or ignore them; exact per-key destinations are not yet public.

The top-row-digits-with-modifier rule is an accessibility convenience for laptop users without a numpad. Plain unshifted digits remain available as ordinary text input. The modifier check accepts left-shift, right-shift, or NumLock; an implementation that lacks NumLock state can treat shift held as the trigger.

The extended-key translation has a notable gap: up, down, Home, End, PgUp, and
PgDn are accepted, but left and right arrow scancodes are not in the traced DOS
table. A compatibility-focused implementation should preserve that behaviour;
a modern convenience layer may additionally map left/right arrows to west/east
before handing input to the game core.

## 6. Case Folding and One-Keystroke-per-Turn

Two transformations are applied to every keystroke between the keyboard peek and the caller:

**Case fold.** Lowercase ASCII letters are folded to upper case by simple subtraction. Other bytes pass through unchanged. The fold is locale-free and table-free. Higher-byte codes (function keys, direction codes, control bytes) fall outside the lowercase range, so the fold is a no-op for them. The rest of the engine sees only uppercase letters and never has to compare both cases.

**Buffer flush.** After each successful read, the BIOS keyboard buffer is reset — its head and tail pointers are forced equal, discarding keystrokes that piled up during the just-completed action. This is the game's distinctive feel: type-ahead is suppressed, one keystroke advances exactly one game turn, and a fast typist cannot accidentally walk through a hostile NPC by holding a movement key.

The flush is gated on a global flag, enabled by default. Text-input prompts (NPC keywords, character names, save filenames, hour counts) clear the flag before they begin and restore it afterwards. While clear, the BIOS buffer is *not* flushed after each read, and the player can type ahead through a multi-character word at full speed.

A correct implementation on a modern event-driven keyboard API: maintain a small input queue per game state; when the flush flag is set, drop all pending keystrokes after consuming one; when the flag is clear, leave the queue alone so subsequent calls drain it in order.

## 7. The Command-Letter Dispatch Model

The translated byte that emerges from the wait loop goes to one of the three top-level mode loops (overworld, town, dungeon). Each loop does a small amount of pre-routing:

- **Direction codes** are handled inline by the mode loop as "move the player one cell that way." They never reach the central dispatcher, with one minor exception (the cursor-east code, in at least one mode, toggles a typeahead flag).
- **Function-key remap codes** are outside printable-letter dispatch. The
  keyboard layer produces them, but the currently public dispatcher trace does
  not assign resident A-Z meanings to them.
- **Letter commands** — uppercase A through Z and a small set of punctuation like Space — are passed to the *central command dispatcher*.

The central dispatcher routes by letter. Each letter has a unique handler; many letters have *multiple* handlers selected by the engine's *scene* state (overworld / town / dungeon; combat uses its own dispatcher). The full per-letter behaviour belongs in `commands.md`; the input-side relevance is only that:

- The dispatcher prints the verb prefix ("Attack-", "Cast...", "Hole up- ", and so on) and then either runs an in-resident handler or makes a cross-overlay call into one of the per-command overlays.
- The handler on the other side may *itself* prompt the user — for a direction, a target slot, a string, a digit. It does so by calling back into the same wait-for-input routine, often after writing the prompt-character byte to switch into prompt mode and clearing the buffer-flush gate to allow type-ahead.
- The wait-for-input routine is therefore *reentrant*. There is no global "I'm reading a key right now" lock and no input queue between nested prompts. Reentrance is enabled by preserving the cursor-advance gate around each nested read (Section 3); the calling handler is responsible for preserving the prompt-character byte and the buffer-flush gate.

## 8. Free-Text Input

Some prompts need more than one keystroke: NPC conversations accept a four- to six-character keyword; character creation accepts a name; save filenames are typed in full; hours-to-rest is a small unsigned number. All are built on the same wait-for-input routine, with three additions:

1. **Print the prompt and park the cursor.** The prompt is emitted into the active text window. The cursor is left where typed input will appear. The prompt-character byte is set to a printable value so the world-tick step is suppressed (Section 2).
2. **Disable the buffer flush.** The flush gate (Section 6) is cleared so the player can type ahead. The prompt restores it on exit.
3. **Loop on the wait-for-input routine, accumulating into a small line buffer.** Each returned byte is one of:
   - A printable ASCII character — appended to the buffer (subject to a maximum length) and echoed at the cursor.
   - A backspace — pops the most recent character from the buffer (if any) and overwrites the previous cell with a space.
   - Enter — terminates the prompt, returning the accumulated string.
   - Escape, on prompts that allow cancellation — terminates with a "cancelled" indication.
   - Any other byte (function key, direction code, etc.) — discarded.

The line buffer is small (the longest string the game ever asks for is on the order of a dozen characters). There is no input history, no cursor movement within the buffer, and no insertion mode — backspace destructively removes the last character, and that is the only editing operation.

Single-character prompts (Y/N, a digit, a target-slot letter) run the loop exactly once. The prompt is responsible for validating the returned byte and looping if it is unacceptable; the wait-for-input routine itself does no validation. Numeric prompts accumulate digits into an integer (multiply by ten, add the digit) and treat backspace as integer division by ten.

While any free-text prompt is active, the cursor blink continues — the player sees the same blinking cursor described in Section 3 at the end of what they have typed.

## 9. World Tick During Idle

When the wait-for-input routine has no key to consume and the prompt-character byte is outside the printable range, it calls the *world tick*. This is the resident redraw orchestrator that keeps the visible scene alive while the game waits for a command. It runs once per failed peek — typically many times per second — but those calls do not spend game-clock minutes or move scheduled NPCs.

The internals of the tick belong in a separate spec. From the input system's perspective, the contract is simple:

- The tick is invoked exactly once per failed keyboard peek, *only* when the prompt-character byte is non-printable (Section 2).
- The tick can take long enough to be perceptible — a full viewport rebuild,
  active-object animation frames, or a first-frame panel repaint — and the
  input system trusts it to return promptly enough that the cursor blink
  remains responsive.
- The wait-for-input routine, on entry, also sets a one-shot "first-tick after mode entry" hint when it detects entry to town mode; the world tick uses this to do a fuller initial re-paint. The hint write is the only piece of world-tick state the input system touches directly.

A modern implementation can time-slice (cap the tick to one per render frame, or once every fixed number of milliseconds) without losing fidelity — the game does not depend on precise wall-clock pacing of the idle redraw ticks, and the game clock is advanced only by committed-turn cleanup.

## 10. Open Questions and Variations

This section records places where the picture is not yet complete or where evidence is internally inconsistent.

- **Left and right arrow keys missing from the scancode translation.** The
  traced extended-key table translates up, down, Home, End, PgUp, and PgDn,
  but not left or right. Corrected DATA.OVL address handling shows this is not
  an off-by-two table read; whether the omission is deliberate or a historical
  oversight still needs live DOS confirmation.

- **Direction-code consumers.** The input layer's numpad and navigation-key
  mappings are pinned down. Each mode's movement handler should still be
  checked as it is promoted to verify that all consumers interpret the final
  direction-code set identically.

- **NumLock as a numpad-promotion modifier.** The shift-state mask treats NumLock-on as equivalent to Shift-held for promoting top-row digits to numpad-equivalent. This is unusual — most software uses NumLock to enable the numpad, not to promote top-row digits — and may have been a heuristic for the era's laptop keyboards. An implementation that does not surface NumLock state can omit it without affecting playability.

- **Cursor-east direction code reaching the dispatcher.** Of the eight direction codes, exactly one — cursor-east — reaches the central command dispatcher in at least one mode, where it toggles a typeahead-buffer flag. Whether other direction codes are dispatcher-bound in modes not yet examined (combat in particular) is unverified.

- **Function-key destinations.** The remapped F1..F10 codes are produced by the
  keyboard layer, and the resident A-Z dispatcher does not consume them as
  command letters. Where each one is consumed, if anywhere, still needs
  mode-loop or menu-specific tracing. The remapped block is contiguous and
  disjoint from the letter and direction blocks.

- **Prompt-character byte writers.** The byte that toggles between idle and prompt mode is written by various places (the verb-prefix printer, the Y/N prompt, the numeric prompt, the text-input prompt) with no single owner. A modern implementation should consolidate these into an explicit "input mode" enum.

- **Reentrancy and the blink counter.** The cursor-advance gate is saved and restored on the local stack across reentrant calls, but the global blink counter is not — a recursive call shares the parent's blink phase. This is benign (the blink is purely visual) but worth flagging if an implementation introduces per-window blink counters.

- **Game-mode-specific entry stamps.** On entry, the wait-for-input routine checks a "game mode" tag and stamps a hint byte when the tag indicates town. The full set of recognised values has not been enumerated; town is the one observed case.

## 11. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The top-level wait-for-input loop, idle vs prompt switching, case folding, numpad-to-direction translation, and the cardinal-direction renumbering — derived from `u5-decomp/functions/ULTIMA_EXE/0x266C_get_command.md`.
- The cursor-blink animation, blink-base / blink-modulus parameters, cursor-advance gate save/restore, and erase-or-rewind step — derived from `u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`.
- The keyboard hardware abstraction, the three input classes (regular ASCII, function-key remap, extended-scancode translation), the scancode-to-direction tables, the function-key block, the numpad-equivalent flag, and the buffer-flush gate — derived from `u5-decomp/functions/ULTIMA_EXE/0x1D5E_keyboard_poll.md`.
- The ASCII-only case-fold helper used between the keyboard peek and the caller — derived from `u5-decomp/functions/ULTIMA_EXE/0x2032_to_upper.md`.
- The central per-letter command dispatcher, the mode-aware routing, the verb-prefix printing, and the cross-overlay call model — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`. Per-letter handler behaviour is covered by `systems/commands.md`; only the input-side interface appears here.
- An example per-command handler (Hole up) showing how a handler reads further input, calls back into prompts, and returns a status word — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The world-tick orchestrator that runs during idle iterations — derived from `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`. Only the input-facing contract (the suppression gate and the per-iteration trigger) is described here; the tick's internal subsystems are properly the subject of separate specs.
