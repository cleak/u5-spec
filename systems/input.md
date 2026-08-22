# Input

## 1. Overview

Ultima V's input system is a single keystroke-at-a-time pipeline. A central "wait for the next command" routine paints a blinking text cursor, polls the keyboard, and — when nothing has been pressed — runs one resident redraw tick so active-object animation, visibility refreshes, night-time light-beacon stamps, and viewport rendering keep moving while input waits. It does not advance the in-world clock or NPC schedules; committed actions do that through the per-turn mode loops. Once a key arrives, the routine folds it to upper case, optionally rewrites it as one of the engine's eight cardinal-or-diagonal direction codes, and returns it to the caller — usually one of the three top-level mode loops (overworld, town, dungeon), which then routes the byte through a per-letter command dispatcher.

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

The input layer can represent eight direction requests: four cardinal
directions and four diagonals. This is an input vocabulary, not a guarantee
that every mode moves in eight directions. World, town, dungeon, and combat
movement consumers accept only the cardinal subset. The diagonals have exactly
one movement-style consumer in the whole game — the combat targeting cursor —
and otherwise act as paging keys inside the full-screen stats/inventory and shop
lists; everywhere else they fall through as non-movement input.

The keyboard layer accepts several physical ways of asking for a direction and
translates them into one internal direction-code set:

| Source | What the player presses | Translated to |
|---|---|---|
| Numpad cardinals | numpad 4 / numpad 6 / numpad 8 / numpad 2 | west / east / north / south |
| Numpad diagonals | numpad 7 / numpad 9 / numpad 1 / numpad 3 | northwest / northeast / southwest / southeast |
| Extended arrow keys | left / right / up / down | west / east / north / south |
| Home / End / PgUp / PgDn | Home / End / PgUp / PgDn | northwest / southwest / northeast / southeast |
| Top-row digits with a modifier | digit `1` through `9` while Shift or NumLock is held | same as the numpad layout above |

The four cardinals land in a low code block and the four diagonals in a high
one, and neither collides with printable ASCII, so a single returned byte
unambiguously says "the player typed letter X" or "the player asked for
direction D". The final input-layer codes are:

| Direction | Final internal code |
|---|---:|
| West | `0x01` |
| East | `0x02` |
| North | `0x03` |
| South | `0x04` |
| Northwest | `0xD3` |
| Southwest | `0xD4` |
| Northeast | `0xD5` |
| Southeast | `0xD6` |

The digit `5` at the centre of the numpad has no direction and is passed through
as the ordinary character.

A separate flag internal to the keyboard peek marks input that arrived through
the scancode table or through the shifted top-row-digit rule, so the upper layer
can apply the final digit-to-direction translation only to those keys. That flag
also suppresses the pseudo-code rewrite described below, which is why a cursor
or numpad key can never be delivered as one of the high pseudo-codes.

Typed ASCII characters, control characters included, are passed through
verbatim, with one exception: a typed Control character in the low range that
was *not* produced by the scancode table is biased into a block of high
pseudo-codes. Only one of those is ever consumed anywhere in the game — the one
produced by Control with the second letter of the alphabet, which is the
typeahead-buffer toggle described in Section 6 and in `commands.md`. Every other
typed Control character reaches the mode loops as its ordinary low code, where
each loop's own control-code table decides what it means.

Function keys F1 through F10 are also remapped into a different contiguous
block, returned directly without passing through the numpad/direction-code
path. Nothing in the game consumes that block: no mode loop, no letter
dispatcher, no prompt, and no panel. An implementation may simply not generate
these codes; if it does generate them, it should keep the block distinct so
nothing mistakes a function key for a direction or a command.

The top-row-digits-with-modifier rule is an accessibility convenience for laptop users without a numpad. Plain unshifted digits remain available as ordinary text input. The modifier check accepts left-shift, right-shift, or NumLock; an implementation that lacks NumLock state can treat shift held as the trigger. Dungeon mode is the one exception to the whole rule: it does not run the digit-to-direction translation at all, so shifted or NumLock-ed top-row digits stay ordinary digits there and select the solo party member like unshifted ones.

The extended-key translation table accepts all four arrow keys plus Home, End,
PgUp, and PgDn. Left and right arrows reach the same West/East cardinal path as
numpad 4 and numpad 6; up and down reach the same North/South path as numpad 8
and numpad 2.

## 6. Case Folding and One-Keystroke-per-Turn

Two transformations are applied to every keystroke between the keyboard peek and the caller:

**Case fold.** Lowercase ASCII letters are folded to upper case by simple subtraction. Other bytes pass through unchanged. The fold is locale-free and table-free. Higher-byte codes (function keys, direction codes, control bytes) fall outside the lowercase range, so the fold is a no-op for them. The rest of the engine sees only uppercase letters and never has to compare both cases.

**Buffer flush.** After each successful read, the BIOS keyboard buffer is reset — its head and tail pointers are forced equal, discarding keystrokes that piled up during the just-completed action. This is the game's distinctive feel: type-ahead is suppressed, one keystroke advances exactly one game turn, and a fast typist cannot accidentally walk through a hostile NPC by holding a movement key.

The flush is gated on a global setting, and it is best described by behaviour
rather than by a flag value. The setting has two states: with type-ahead **on**,
keystrokes queued during an animation or a long action are honoured in order;
with it **off**, the queue is emptied on every read. Off is the default at
startup, which is why the stock game feels strictly one-key-per-turn.

Three things write the setting and nothing else does. The player toggles it from
the world command dispatcher (Control with the second letter of the alphabet),
combat offers a second, independent copy of the same toggle writing the same
setting, and the free-text line reader saves the setting, forces type-ahead on
for the duration of a typed line, and restores it afterwards. That last one
means typing a name, a keyword, or a word of power always honours the queue
regardless of the player's choice. The engine prints the new state as a short
Buffer On / Buffer Off message; "on" is the honour-the-queue state.

A correct implementation on a modern event-driven keyboard API: maintain a small input queue per game state; when the flush flag is set, drop all pending keystrokes after consuming one; when the flag is clear, leave the queue alone so subsequent calls drain it in order.

## 7. The Command-Letter Dispatch Model

The translated byte that emerges from the wait loop goes to one of the three top-level mode loops (overworld, town, dungeon). Each loop does a small amount of pre-routing:

- **Direction codes** are handled inline by the mode loop as "move the player one cell that way." They never reach the central dispatcher — the rule is unconditional. The one non-letter code the central dispatcher does accept is the typeahead toggle, and that is a typed Control character, not a cursor code.
- **Function-key remap codes** are outside printable-letter dispatch. The
  keyboard layer produces them and nothing in the game consumes them.
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

The free-text reader accepts printable ASCII bytes up to the caller-supplied
maximum length, echoes each accepted byte, and NUL-terminates the caller's
buffer when Enter is pressed. Backspace erases one accepted character by
printing a replacement space through the text eraser. Escape clears the whole
line and terminates with an empty buffer. These prompts may disable the normal
type-ahead flush while active so a typed word can be drained across repeated
single-key reads.

Single-character prompts (Y/N, a digit, a target-slot letter) run the loop exactly once. The prompt is responsible for validating the returned byte and looping if it is unacceptable; the wait-for-input routine itself does no validation. Numeric prompts accumulate digits into an integer (multiply by ten, add the digit) and treat backspace as integer division by ten.

While any free-text prompt is active, the cursor blink continues — the player sees the same blinking cursor described in Section 3 at the end of what they have typed.

## 9. Party-Member Selection Prompts

Several command and spell paths ask the player to choose a travelling party
member. The shared selector is slot-based, not name-based: digits and navigation
keys choose among the currently active party slots, capped by the live
party-size field. Slots are zero-based internally even though the visible
choices are presented to the player as party positions.

The standard party-target wrapper prints a short "on whom" prompt, invokes the
resident slot selector, then echoes either the selected character's displayed
name or the none/cancel result. If a selected name did not already wrap output
to the next line, the wrapper appends a newline so the following prompt starts
cleanly.

The selector itself accepts visible digits `1` through `6` for direct slot
choice, caps navigation to the live party size, lets direction/navigation keys
cycle the highlighted slot, treats Space, Enter, and `0` as confirmation, and
treats Escape as cancellation. Combat contexts can add the current arena tile's
short label to the prompt when the selected actor is standing on a labelled
combat tile; that label is presentation only and does not change the returned
slot family.

Selector returns have three semantic families:

- **Selected slot.** A nonnegative result is the zero-based active-party slot
  chosen by the player.
- **Cancel.** Escape or the cancel key returns a negative result.
- **Explicit none.** The zero key returns a distinct negative result. Most
  callers treat all negative results as the same no-target branch, but
  compatibility code should preserve the distinction where a caller does
  inspect it.

Callers own the prompt wording and no-target consequence. Party-target spells
usually print the none result and abort before mutating a character record.
N-New Order asks for two selected slots and refuses or cancels without spending
a turn when either selection is negative or targets the leader slot. Combat
commands often bypass the arbitrary selector and use the current active combat
actor instead.

## 10. Adjacent-Tile Command Direction Prompt

World command handlers that act on one neighboring map cell share a resident
direction prompt after the dispatcher has printed the verb prefix. This prompt
does not print a generic `Direction-` label itself; the visible lead-in is the
calling command's prefix, such as `Search-`, `Jimmy-`, `Open-`, `Get-`,
`Push-`, `Talk-`, or a ship-fire prompt.

The prompt clears a shared command-direction vector, then blocks on the normal
single-keystroke input routine until it receives a cardinal direction or a
pass/cancel choice. Cardinal choices are the same pre-routed direction values
used by world movement:

| Player choice | Command vector adjustment | Echoed label |
|---|---|---|
| West | X minus one | `West` |
| East | X plus one | `East` |
| North | Y minus one | `North` |
| South | Y plus one | `South` |

After a cardinal choice, the prompt returns a positive direction result and the
caller reads the cached vector to choose its target tile. Diagonals, ordinary
letters, function keys, and unshifted top-row digits are ignored and cause the
prompt to read again. Space prints `Pass` and returns the no-direction result;
callers normally treat that as a silent cancellation with no tile mutation. A
compatibility implementation should preserve the cardinal-only filter rather
than treating diagonals as valid adjacent targets.

This adjacent-tile prompt is distinct from the spell direction prompt below.
The spell prompt owns a target coordinate chosen from party or combat-actor
origin state, while command handlers usually interpret the cached vector
relative to their own map/object context.

## 11. Spell Direction Prompts

Spell and spell-like helpers that target one adjacent cardinal cell use a
shared direction prompt. The prompt prints `Direction-`, blocks for one
keystroke through the normal command-input routine, and owns both a returned
direction result and a cached target coordinate pair for the caller.

The origin depends on mode. Outside combat, the cached target starts at the
party's current map position. In combat-class scenes, it starts from the active
combat actor's current targeting coordinate. A recognized cardinal key then
moves the cached target by one cell:

| Player choice | Cached target adjustment | Echoed label |
|---|---|---|
| North | Y minus one | `North` |
| East | X plus one | `East` |
| South | Y plus one | `South` |
| West | X minus one | `West` |

Space is accepted as `Pass`: it echoes `Pass`, leaves the cached coordinate at
the origin, and returns the no-direction result. Other keys are ignored and the
prompt reads again rather than returning to the caller. Callers that treat the
returned no-direction result as cancellation therefore make Space the
player-visible no-effect choice for this prompt family; Escape is not the
confirmed cancellation key for this shared spell prompt.

Callers read the cached coordinate pair rather than receiving coordinates in
the return value. This is why direction-target spells can share the same prompt
while doing different work afterward: Open, Dispel Field, Wind Change, field
placement, and directional attack helpers all interpret the same chosen target
or no-direction result in their own effect layer.

## 12. World Tick During Idle

When the wait-for-input routine has no key to consume and the prompt-character byte is outside the printable range, it calls the *world tick*. This is the resident redraw orchestrator that keeps the visible scene alive while the game waits for a command. It runs once per failed peek — typically many times per second — but those calls do not spend game-clock minutes or move scheduled NPCs.

The internals of the tick belong in a separate spec. From the input system's perspective, the contract is simple:

- The tick is invoked exactly once per failed keyboard peek, *only* when the prompt-character byte is non-printable (Section 2).
- The tick can take long enough to be perceptible — a full viewport rebuild,
  active-object animation frames, or a first-frame panel repaint — and the
  input system trusts it to return promptly enough that the cursor blink
  remains responsive.
- The wait-for-input routine, on entry, also sets a one-shot "first-tick after mode entry" hint when it detects entry to town mode; the world tick uses this to do a fuller initial re-paint. The hint write is the only piece of world-tick state the input system touches directly.

A modern implementation can time-slice (cap the tick to one per render frame, or once every fixed number of milliseconds) without losing fidelity — the game does not depend on precise wall-clock pacing of the idle redraw ticks, and the game clock is advanced only by the per-turn cleanup that the mode loops call, never by the idle tick. Do not read that as "the clock advances only on a consumed turn": the overworld, town, and combat loops gate their cleanup call on a consumed turn, but the dungeon loop's call is ungated and costs a minute every iteration (`systems/main-loop.md` Section 6, `systems/dungeon-mode.md` Section 15). An earlier revision of this paragraph said the clock is advanced only by committed-turn cleanup; that framing is withdrawn.

## 13. Input Boundaries, Variations, And Remaining Entry-Stamp Work

This section separates input-backend variation from the remaining input-facing
runtime gap: the full recognised set for the game-mode-specific entry stamp.

- **NumLock as a numpad-promotion modifier.** The keyboard abstraction treats
  NumLock-on as a compatibility modifier for promoting top-row digits to
  numpad-equivalent direction codes. This belongs to the IBM PC keyboard
  backend, not to gameplay command semantics. An implementation that does not
  surface NumLock state can omit this modifier without changing the accepted
  command vocabulary.

- **Function-key destinations — closed.** An exhaustive sweep of every shipped
  code file for consumers of the remapped F1..F10 block finds none: no mode
  loop, no letter dispatcher, no direction prompt, no free-text prompt, and no
  full-screen panel. The block is produced and then accepted by nothing, so an
  implementation may simply not generate it. If it does, the block must stay
  disjoint from the letter and direction blocks. The same sweep settled the
  diagonal block the other way: its consumers are the combat targeting cursor
  and the paging keys of the stats/inventory and shop lists.

- **Prompt-character byte writers.** Several prompt families select the
  visible prompt/idle cursor byte before entering the shared input wait. The
  clean contract is the semantic input mode and cursor presentation state, not
  the original split of writer sites. A modern implementation should consolidate
  these into an explicit input-mode enum.

- **Reentrancy and the blink counter.** The cursor-advance gate is local to a
  wait call, while the blink phase is shared process state. This is a visual
  compatibility boundary rather than a gameplay rule; implementations with
  per-window blink counters only need to preserve prompt acceptance and cursor
  erase/restore behavior.

- **Game-mode-specific entry stamps.** On entry, the wait-for-input routine checks a "game mode" tag and stamps a hint byte when the tag indicates town. The full set of recognised values has not been enumerated; town is the one observed case.

## 14. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The top-level wait-for-input loop, idle vs prompt switching, case folding, numpad-to-direction translation, and the cardinal-direction renumbering — derived from `u5-decomp/functions/ULTIMA_EXE/0x266C_get_command.md`.
- The cursor-blink animation, blink-base / blink-modulus parameters, cursor-advance gate save/restore, and erase-or-rewind step — derived from `u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`.
- The keyboard hardware abstraction, the three input classes (regular ASCII, function-key remap, extended-scancode translation), the scancode-to-direction tables, the function-key block, the numpad-equivalent flag, and the buffer-flush gate — derived from `u5-decomp/functions/ULTIMA_EXE/0x1D5E_keyboard_poll.md`.
- The ASCII-only case-fold helper used between the keyboard peek and the caller — derived from `u5-decomp/functions/ULTIMA_EXE/0x2032_to_upper.md`.
- The central per-letter command dispatcher, the mode-aware routing, the verb-prefix printing, and the cross-overlay call model — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`. Per-letter handler behaviour is covered by `systems/commands.md`; only the input-side interface appears here.
- The resident adjacent-tile command direction prompt, including cardinal-only
  filtering, shared vector output, direction echo labels, and Space/Pass
  cancellation -- derived from
  `u5-decomp/functions/ULTIMA_EXE/0x35EC_direction_prompt.md`.
- Direction-code consumer boundaries, including cardinal-only world, town,
  dungeon, and combat movement plus diagonal fallthrough behavior -- derived from
  `u5-decomp/notes/system-trace_movement.md` and
  `u5-decomp/notes/cross_mode_behavior_matrix.md`.
- The standard party-member target wrapper and selector return families --
  selected active slot, cancel, and explicit none -- derived from
  `u5-decomp/functions/CAST2_OVL/0x009E_prompt_party_member.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x2D7A_input_party_select.md`.
- The shared spell direction prompt -- origin selection, cardinal target
  adjustment, Space/Pass no-direction result, and re-prompt on other keys --
  derived from `u5-decomp/functions/CAST2_OVL/0x0306_prompt_direction.md`.
- An example per-command handler (Hole up) showing how a handler reads further input, calls back into prompts, and returns a status word — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The world-tick orchestrator that runs during idle iterations — derived from `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`. Only the input-facing contract (the suppression gate and the per-iteration trigger) is described here; the tick's internal subsystems are properly the subject of separate specs.
- The free-text reader's printable-byte, Backspace, Enter, Escape, echo, and
  NUL-termination behavior -- derived from
  `u5-decomp/functions/ULTIMA_EXE/0x1E38_read_text_input.md`.

- The corrected direction-code assignments of Section 5, the mutual exclusion
  between scancode translation and the typed-Control pseudo-code rewrite, the
  behavioural description of the type-ahead setting and its three writers, and
  the closure of the function-key and diagonal-code consumer questions. Source
  provenance: derived from private analysis note
  `../u5-decomp/notes/oq-closures_2026-08-22_commands-dispatch.md`, with
  `../u5-decomp/functions/ULTIMA_EXE/0x1D5E_keyboard_poll.md` and
  `../u5-decomp/functions/COMSUBS_OVL/0x0504_arena_cursor_picker.md`.
