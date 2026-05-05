# Input

## 1. Overview

Ultima V's input system is a single keystroke-at-a-time pipeline. A central "wait for the next command" routine paints a blinking text cursor, polls the keyboard, and — when nothing has been pressed — runs one tick of the world so animation, NPC schedules, and the game clock advance smoothly while the game is idle. Once a key arrives, the routine folds it to upper case, optionally rewrites it as one of the engine's eight cardinal-or-diagonal direction codes, and returns it to the caller — usually one of the three top-level mode loops (overworld, town, dungeon), which then routes the byte through a per-letter command dispatcher.

The pipeline is non-blocking at the bottom: the keyboard is peeked, not waited on. Blocking is achieved by looping over the peek-and-tick step. This is why the cursor blinks at all (each loop iteration paints one frame of it) and why time passes in towns even when the player is idle.

## 2. Idle vs Prompt Modes

The same wait-for-input routine is used in two distinct modes, controlled by a single byte of state — the *prompt-character* byte, written by whichever piece of the UI most recently displayed a Y/N or text prompt.

**Idle / open-ended command mode.** The prompt-character byte is outside the printable-ASCII range. Each iteration of the wait loop paints one frame of the blinking cursor, peeks the keyboard, and — on a miss — runs one *world tick*: NPCs walk, lighting and torch fuel are updated, the world clock advances, and the viewport is re-rendered. Idle time is gameplay time.

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
| Blink base glyph | a small low-ASCII code | The first glyph code in the cursor-frame range. The blink cycles through consecutive glyph codes starting here. |
| Blink modulus | a four-digit constant | Number of frames before the counter wraps to zero. The exact value is tied to the engine's idle-loop rate; with a modern fixed-frame backend, an implementer should pick a modulus that produces a roughly half-second period at the chosen tick rate. |

Both parameters are mutable globals — anything that wants a different cursor shape (e.g. a screen that wants no cursor at all) sets them before calling the wait loop. In practice the only adjustment the game makes is to suppress the cursor entirely on certain "press any key" prompts by setting the modulus tight enough that the cursor never actually appears.

## 4. Keyboard Hardware Abstraction

Every keyboard interrupt happens in one place — the *keyboard peek* routine called from inside the cursor-blink loop. From the rest of the engine's perspective, the keyboard is a pure function that returns either zero or a single translated byte.

The peek routine performs three steps:

1. **Status check.** Ask the BIOS whether a key is pending. If not, return zero immediately.
2. **Read the byte.** Use the platform's "direct console input" facility to consume one byte from the keyboard buffer without line-editing or signal handling (no echo, no Ctrl-C interception, no buffered line). The byte is either an ASCII character or zero.
3. **Classify and translate.** A non-zero byte falls through to "regular" ASCII handling. A zero byte triggers a second read for the *extended scancode*, which is translated against fixed tables for arrow keys, function keys, and a few other navigation keys. Anything that doesn't classify is returned as "no key."

After a successful read, the BIOS keyboard buffer is normally flushed (see Section 6) so any keys typed during the previous turn are discarded.

Classification produces three families of returned values, each in a non-overlapping byte range:

- **Regular ASCII** — printable letters, digits, punctuation, and a small set of control bytes (Enter, Backspace, Escape).
- **Function-key remap** — a contiguous block in the high byte range. F1 through F10 are renumbered into adjacent slots that don't collide with printable ASCII or the direction codes.
- **Direction codes** — a small block, also in the high byte range, distinct from the function-key block. See Section 5.

Remaining byte values are unused; the engine treats them as "no key" and continues polling.

## 5. Scancode Translation: Numpad, Arrows, and Diagonals

Movement in Ultima V is eight-way. The player can request any of the four cardinal directions or any of the four diagonals. The engine accepts five physically different ways of asking for a movement, and translates all five into the same set of eight internal codes:

| Source | What the player presses | Translated to |
|---|---|---|
| Numpad cardinals | numpad 4 / numpad 6 / numpad 8 / numpad 2 | west / east / north / south |
| Numpad diagonals | numpad 7 / numpad 9 / numpad 1 / numpad 3 | northwest / northeast / southwest / southeast |
| Arrow keys | left / right / up / down | west / east / north / south |
| Home / End / PgUp / PgDn | Home / End / PgUp / PgDn | northwest / southwest / northeast / southeast |
| Top-row digits with a modifier | digit `1` through `9` while Shift or NumLock is held | same as the numpad layout above |

The eight resulting direction codes occupy one block of bytes in the high range, all outside printable ASCII, so a single returned byte unambiguously says either "the player typed letter X" or "the player asked to move in direction D". A separate flag internal to the keyboard peek marks any of the above translations so the upper layer can apply final renumbering: cardinals are folded into one contiguous four-code range, diagonals into another. The two ranges do not overlap each other or any letter command.

Function keys F1 through F10 are also remapped into a different contiguous block, returned directly without passing through the numpad/direction-code path. The game uses them for menus, save/load, and music toggles; per-key meanings belong in the commands spec.

The top-row-digits-with-modifier rule is an accessibility convenience for laptop users without a numpad. Plain unshifted digits remain available as ordinary text input. The modifier check accepts left-shift, right-shift, or NumLock; an implementation that lacks NumLock state can treat shift held as the trigger.

The arrow-key translation has a notable gap: up, down, Home, End, PgUp, and PgDn are all in the table, but **left and right arrow scancodes are not.** Whether this is deliberate or a historical oversight is unclear (see Section 10). The game is fully playable with arrows regardless; a modern reimplementation can fill in the gap by mapping left and right to the same codes the numpad produces.

## 6. Case Folding and One-Keystroke-per-Turn

Two transformations are applied to every keystroke between the keyboard peek and the caller:

**Case fold.** Lowercase ASCII letters are folded to upper case by simple subtraction. Other bytes pass through unchanged. The fold is locale-free and table-free. Higher-byte codes (function keys, direction codes, control bytes) fall outside the lowercase range, so the fold is a no-op for them. The rest of the engine sees only uppercase letters and never has to compare both cases.

**Buffer flush.** After each successful read, the BIOS keyboard buffer is reset — its head and tail pointers are forced equal, discarding keystrokes that piled up during the just-completed action. This is the game's distinctive feel: type-ahead is suppressed, one keystroke advances exactly one game turn, and a fast typist cannot accidentally walk through a hostile NPC by holding a movement key.

The flush is gated on a global flag, enabled by default. Text-input prompts (NPC keywords, character names, save filenames, hour counts) clear the flag before they begin and restore it afterwards. While clear, the BIOS buffer is *not* flushed after each read, and the player can type ahead through a multi-character word at full speed.

A correct implementation on a modern event-driven keyboard API: maintain a small input queue per game state; when the flush flag is set, drop all pending keystrokes after consuming one; when the flag is clear, leave the queue alone so subsequent calls drain it in order.

## 7. The Command-Letter Dispatch Model

The translated byte that emerges from the wait loop goes to one of the three top-level mode loops (overworld, town, dungeon). Each loop does a small amount of pre-routing:

- **Direction codes** are handled inline by the mode loop as "move the player one cell that way." They never reach the central dispatcher, with one minor exception (the cursor-east code, in at least one mode, toggles a typeahead flag).
- **Function-key remap codes** are handled by a mode-specific side table — F1 might mean "music toggle" in town and "abandon spell" in combat.
- **Letter commands** — uppercase A through Z and a small set of punctuation like Space — are passed to the *central command dispatcher*.

The central dispatcher routes by letter. Each letter has a unique handler; many letters have *multiple* handlers selected by the engine's *scene* state (overworld / town / dungeon / combat). The full per-letter behaviour belongs in a separate commands spec; the input-side relevance is only that:

- The dispatcher prints the verb prefix ("Attack-", "Cast...", "Hole up- ", and so on) and then either runs an in-resident handler or makes a cross-overlay call into one of the per-command overlays.
- The handler on the other side may *itself* prompt the user — for a direction, a target slot, a string, a digit. It does so by calling back into the same wait-for-input routine, often after writing the prompt-character byte to switch into prompt mode and clearing the buffer-flush gate to allow type-ahead.
- The wait-for-input routine is therefore *reentrant*. There is no global "I'm reading a key right now" lock and no input queue between caller and callee. Reentrance is enabled by save-and-restore of the cursor-advance gate on the local stack (Section 3); the calling handler is responsible for save-and-restore of the prompt-character byte and the buffer-flush gate.

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

When the wait-for-input routine has no key to consume and the prompt-character byte is outside the printable range, it calls the *world tick*. This is the single function that makes idle time productive in Ultima V. It runs once per failed peek — typically many times per second — so a single in-game "moment" of idle time consists of many ticks.

The internals of the tick belong in a separate spec. From the input system's perspective, the contract is simple:

- The tick is invoked exactly once per failed keyboard peek, *only* when the prompt-character byte is non-printable (Section 2).
- The tick can take long enough to be perceptible — a full viewport rebuild, NPC schedule advancement, animation frames — and the input system trusts it to return promptly enough that the cursor blink remains responsive.
- The wait-for-input routine, on entry, also sets a one-shot "first-tick after mode entry" hint when it detects entry to town mode; the world tick uses this to do a fuller initial re-paint. The hint write is the only piece of world-tick state the input system touches directly.

A modern implementation can time-slice (cap the tick to one per render frame, or once every fixed number of milliseconds) without losing fidelity — the game does not depend on precise wall-clock pacing of the idle ticks.

## 10. Open Questions and Variations

This section records places where the picture is not yet complete or where evidence is internally inconsistent.

- **Left and right arrow keys missing from the scancode translation.** The arrow-key block translates up, down, Home, End, PgUp, and PgDn, but the left and right arrows are absent. Whether this is deliberate (arrows are a partial mirror of the numpad) or an accident of memory layout (the two scancodes appear in adjacent memory used by the cursor-blink counter, which may have been a coincidence the original authors did not unwind) is unclear. A modern implementation should fill in the gap; the game is fully playable either way.

- **Cardinal and diagonal direction pairing.** The numpad-to-direction mapping (4 / 6 / 8 / 2 = west / east / north / south, and 7 / 9 / 1 / 3 = NW / NE / SW / SE) is read off the obvious physical layout. The internal byte codes are consecutive within each group; the engine's movement handlers consume them by table lookup, so the pairing is defined by that table. Independent confirmation against a live in-game test is pending.

- **NumLock as a numpad-promotion modifier.** The shift-state mask treats NumLock-on as equivalent to Shift-held for promoting top-row digits to numpad-equivalent. This is unusual — most software uses NumLock to enable the numpad, not to promote top-row digits — and may have been a heuristic for the era's laptop keyboards. An implementation that does not surface NumLock state can omit it without affecting playability.

- **Cursor-east direction code reaching the dispatcher.** Of the eight direction codes, exactly one — cursor-east — reaches the central command dispatcher in at least one mode, where it toggles a typeahead-buffer flag. Whether other direction codes are dispatcher-bound in modes not yet examined (combat in particular) is unverified.

- **Function-key destinations.** The remapped F1..F10 codes are produced by the keyboard layer, but where each one is consumed (which mode loop, which handler, which menu) has not been fully traced. The remapped block is contiguous and disjoint from the letter and direction blocks; per-key meanings belong in the commands spec.

- **Prompt-character byte writers.** The byte that toggles between idle and prompt mode is written by various places (the verb-prefix printer, the Y/N prompt, the numeric prompt, the text-input prompt) with no single owner. A modern implementation should consolidate these into an explicit "input mode" enum.

- **Reentrancy and the blink counter.** The cursor-advance gate is saved and restored on the local stack across reentrant calls, but the global blink counter is not — a recursive call shares the parent's blink phase. This is benign (the blink is purely visual) but worth flagging if an implementation introduces per-window blink counters.

- **Game-mode-specific entry stamps.** On entry, the wait-for-input routine checks a "game mode" tag and stamps a hint byte when the tag indicates town. The full set of recognised values has not been enumerated; town is the one observed case.

## 11. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The top-level wait-for-input loop, idle vs prompt switching, case folding, numpad-to-direction translation, and the cardinal-direction renumbering — derived from `u5-decomp/functions/ULTIMA_EXE/0x266C_get_command.md`.
- The cursor-blink animation, blink-base / blink-modulus parameters, cursor-advance gate save/restore, and erase-or-rewind step — derived from `u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`.
- The keyboard hardware abstraction, the three input classes (regular ASCII, function-key remap, extended-scancode translation), the scancode-to-direction tables, the function-key block, the numpad-equivalent flag, and the buffer-flush gate — derived from `u5-decomp/functions/ULTIMA_EXE/0x1D5E_keyboard_poll.md`.
- The ASCII-only case-fold helper used between the keyboard peek and the caller — derived from `u5-decomp/functions/ULTIMA_EXE/0x2032_to_upper.md`.
- The central per-letter command dispatcher, the mode-aware routing, the verb-prefix printing, and the cross-overlay call model — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`. Per-letter handler behaviour is properly the subject of a separate commands spec; only the input-side interface appears here.
- An example per-command handler (Hole up) showing how a handler reads further input, calls back into prompts, and returns a status word — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The world-tick orchestrator that runs during idle iterations — derived from `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`. Only the input-facing contract (the suppression gate and the per-iteration trigger) is described here; the tick's internal subsystems are properly the subject of separate specs.
