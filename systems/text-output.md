# Text Output

## 1. Overview

Ultima V draws all of its game text — narration, names, prompts, conversation lines, and status panels — through a single small subsystem. It maintains four independent text windows on a fixed 40-column by 25-row character grid, exposes a small set of primitive operations (emit one character, emit a word-wrapped string, emit a padded number, read or write the cursor), and hands the pixels of each character off to a separately loaded display driver.

At any moment, exactly one of the four windows is the *active* window and is the destination of every text-emitting call. Each window owns its own rectangle on the grid, its own cursor, its own colour, and its own small set of style flags. The primitives consult the active window, advance its cursor, and wrap and scroll within its bounds; they never touch any other window. Switching the active window takes effect immediately, and the new window's cursor is wherever it was last left, so a UI can move focus between (for example) a dialogue window and a status window without losing position in either.

Driver-level concerns — which font is used, how the framebuffer is laid out, what a cell's pixel size actually is — are walled off from the text system. The text system asks the driver to render the glyph for a given code at a given cell, in a given colour, with optional underline and inverse, and the driver does the rest. The driver-side ABI is described elsewhere; here we describe only what the text system promises.

## 2. The Text-Window Model

The system maintains a fixed array of four window descriptors, numbered 0 through 3. The count is a hard constant; addressing a fifth window is silently ignored. Windows are not specialised by purpose — any window can be configured to any rectangle and used for any output — but in practice the game uses different windows for the main text area, the status panel, the input prompt, and so on, exploiting the fact that each window's cursor is preserved while others receive output.

A window descriptor carries three kinds of information:

- The window's rectangle on the screen, as the cell coordinates of its top-left and bottom-right corners (both corners inclusive).
- The window's live cursor position, relative to the window's top-left corner.
- The window's current style: a colour attribute and a set of independent flag bits.

Selecting an active window has two effects. First, the descriptor at the chosen index becomes the destination of all subsequent output and cursor operations. Second, the descriptor's style byte is unpacked into a small cache of "current style" values — foreground and background nibbles split out, each style flag bit moved into its own slot — so the inner loop emitting one cell can read style without re-decoding. If the implementation already keeps style fields directly accessible (rather than packed), the cache collapses away.

Switching back to a window that was active earlier finds its cursor exactly where output last left it, and its rectangle and style as last configured. Per-window state preservation across switches is the whole reason there are four windows rather than one.

## 3. Window Descriptor Structure

Each window's descriptor consists of eight pieces of information. Implementations may store them in any layout; the table below describes the *information content* of the descriptor, not a memory format.

| Field             | Type        | Range                  | Meaning                                                               |
|-------------------|-------------|------------------------|-----------------------------------------------------------------------|
| top_left_x        | cell column | 0–39                   | Column of the top-left corner of the window's rectangle.              |
| top_left_y        | cell row    | 0–24                   | Row of the top-left corner.                                           |
| bottom_right_x    | cell column | 0–39, ≥ top_left_x     | Column of the bottom-right corner. Inclusive.                         |
| bottom_right_y    | cell row    | 0–24, ≥ top_left_y     | Row of the bottom-right corner. Inclusive.                            |
| cursor_x          | cell column | 0 to (right − left)    | Live cursor column, relative to top_left_x.                           |
| cursor_y          | cell row    | 0 to (bottom − top)    | Live cursor row, relative to top_left_y.                              |
| color             | attribute   | foreground 0–15, background 0–15 | Colour for any cells the window emits. Foreground and background each occupy four bits. |
| flags             | bit field   | three independent bits | Style toggles applied to subsequent emissions. See below.             |

The colour attribute is interpreted in the standard PC-text-mode way: low four bits are the foreground index, high four bits are the background index. Specific palette entries are a driver concern.

The flag bits are independent — any combination of them may be set:

| Flag       | When set                                                           |
|------------|--------------------------------------------------------------------|
| underline  | Each emitted cell has its bottom row of pixels forced on.          |
| centre     | The next call to the wrap-aware string printer centres its line within the window's width before emitting. |
| inverse    | Each emitted cell has its glyph bitmap bitwise-inverted.           |

The colour and flag fields apply to subsequent emissions; they are read at glyph-emit time, not at character-receive time, so changing them between calls changes the appearance of the next output.

The rectangle has a hard invariant: `top_left_x ≤ bottom_right_x` and `top_left_y ≤ bottom_right_y`, both within the screen extent. Operations that mutate the rectangle (see Section 8) enforce this invariant by clamping out-of-range arguments and swapping inverted pairs. Operations that read the rectangle (wrap, scroll, conversion to pixel coordinates) assume the invariant holds.

## 4. Cell Coordinates and the Screen

The screen is a 40-column by 25-row grid. The top-left cell is column 0, row 0; the bottom-right is column 39, row 24. All cell-coordinate fields and arguments in this document live in this grid.

A cell is one glyph-sized rectangle of pixels. The pixel dimensions of a cell are decided by the loaded display driver and are not part of the text-system contract; the text system only speaks in cell coordinates. When the driver converts a cell rectangle into a pixel rectangle (for clear or scroll), it scales both corners by the cell size and adjusts the bottom-right corner to the *last* pixel inside that cell, not the first pixel of the next cell.

Window rectangles use absolute cell coordinates. Cursor positions and width arguments to the wrap-aware printer use window-local coordinates. The conversion is addition: a cursor at window-local `(cursor_x, cursor_y)` lies at absolute screen cell `(top_left_x + cursor_x, top_left_y + cursor_y)`. A window's width in cells is `bottom_right_x − top_left_x`; this figure is what wrapping decisions use, and it does not include the trailing column. A window whose corners are columns 6 and 33 has width 27 — twenty-seven characters fit before wrapping is forced.

## 5. Output Primitives

The system exposes four families of operations. None of them takes a window argument — they all operate on whichever window is currently active.

**The per-cell emitter** takes one byte and either renders one glyph at the active window's cursor or interprets newline/carriage-return as cursor movement. It is the foundation of the system; both the wrap-aware printer and the numeric printer go through it. Its behaviour:

- A byte with the high bit clear and not equal to line-feed or carriage-return is rendered as a glyph at the current cursor cell, in the active window's current colour and with any active style flags applied. The cursor then advances one cell to the right. If the advance would carry the cursor past `bottom_right_x`, the cursor wraps to the window's left edge and steps down one row. If the row advance would carry the cursor past `bottom_right_y`, the window scrolls (Section 7) and the cursor is left on the now-blank bottom row.
- A line-feed byte advances the cursor down one row without emitting a glyph and without resetting the column. If that step carries the cursor past `bottom_right_y`, the window scrolls.
- A carriage-return byte returns the cursor to the window's left edge without changing the row and without emitting a glyph.
- Any high-bit-set byte is silently dropped by the decoded per-cell path. There is no error.
- A resident cursor-advance gate can suppress the cursor advance after a glyph emit. The glyph is still rendered, but the cursor stays put. This gate is shared runtime state rather than one of the descriptor style bits; the input cursor blink temporarily disables it so blink frames paint in place.

**The wrap-aware string printer** takes a near pointer to a NUL-terminated byte string and emits it into the active window with word wrapping. It accumulates characters in a fixed-size internal line buffer (large enough for the widest possible window) while tracking the most recent point at which a word break could have happened. When a soft break (space, line-feed, or carriage-return) is reached and the line still fits in the window's width, the line is emitted via the per-cell emitter. When the next character would carry the line past the window's right edge, the printer backs up to the most recent soft break, emits everything up to that break, and begins a new line with the remainder. A NUL forces a final flush. Line-feed and carriage-return bytes embedded in the source string force an immediate flush at that point and pass through to the per-cell emitter so the cursor moves accordingly.

If the active window's centre flag is set, the printer computes the centred starting column for the line (`(width − characters_in_line) / 2`) and repositions the cursor horizontally to that column before emitting; the cursor's row is left alone, so centring affects only horizontal placement. The centre flag applies once per line of output produced by this printer, and only by this printer — the per-cell emitter does not centre.

An empty string is a no-op.

**The padded numeric printer** takes a signed 16-bit integer, a field width, and a single-byte pad character. It formats the value into a small internal buffer with leading copies of the pad character, an optional minus sign, and the decimal digits of the absolute value, producing a NUL-terminated string of exactly the requested width (or wider, if the value's natural width exceeds the field). It then hands the buffer to the wrap-aware string printer. The field width is clamped at 39, matching the maximum window width. The integer is treated as signed: values from −32768 through 32767 print correctly; values above 32767 (if interpreted as unsigned) render as their two's-complement signed equivalent. To zero-pad, the caller passes the digit-zero character as the pad; to space-pad, the caller passes a space. Because the numeric printer routes through the wrap-aware string printer, numeric output respects the active window's width, centre flag, and wrap behaviour.

**The cursor accessors** read or write the active window's cursor in window-local coordinates. The two readers return `cursor_x` and `cursor_y` respectively; both are zero-based and unsigned. The writer takes a `(column, row)` pair in window-local coordinates and updates the cursor only after checking that the resulting *absolute* screen position lies within the 40×25 grid. If the check fails — that is, if the window has been positioned such that the requested local position falls off the screen — the writer silently leaves the cursor unchanged. There is no error return and no clamp; callers are expected to compute valid coordinates.

## 6. Word-Wrap Algorithm

The wrap-aware printer treats word boundaries as the only legal places to break a line. Each byte from the source string is one of three kinds:

- A *break* byte: space, line-feed, carriage-return, or NUL.
- A *visible* byte: any other low-ASCII printable byte.
- A *control* byte handled by the per-cell emitter (style toggles, etc.); these pass through unchanged and do not interrupt the wrap state.

The printer keeps two pieces of state between input bytes: a fixed-size buffer for the line being assembled (wide enough to hold the widest window line, with a small safety margin), and a count of the characters that would be emitted if the line were flushed now. Visible bytes are appended to the buffer and increment the count. Break bytes act as follows:

- A space: if the count is still within the window's available width on the current line, remember this position as the most recent legal break point and continue. If the count has just exceeded the available width, emit the buffer up to (but not including) the most recent remembered break, then move the surplus to the front of the buffer and continue assembling.
- A line-feed or a carriage-return: emit the buffer immediately, then pass the break byte through to the per-cell emitter so the cursor moves accordingly. Reset the buffer.
- A NUL: emit the buffer immediately and stop reading input.

The "available width on the current line" used by the wrap test is `window_width − cursor_x_at_function_entry` for the first emitted line, and full window width thereafter. This honours text already on the current row before the call: the first wrap point is computed against the remaining columns, not the whole window.

The buffer is sized to hold any window's worth of text (at least 64 characters in the original implementation). If a single word exceeds the window width — a degenerate case — the original implementation overflows that word past the right edge before the next break forces a wrap. Implementations may choose a stricter behaviour so long as visible output matches for well-formed input.

## 7. Driver-Side Glyph Dispatch

When the per-cell emitter decides to render a glyph, it does so in three conceptual steps. The text system itself is responsible for the first two; the third is delegated to the loaded display driver.

1. **Glyph-bitmap fetch.** The emitter selects the glyph bitmap for the byte being rendered from the driver's font. The font lives inside the driver's loaded image; the text system knows nothing about its internal layout beyond the row stride, which depends on the driver. The bitmap is copied into a small working buffer that the system uses as the cell's pixel pattern.

2. **Style transformations.** The working buffer is then post-processed in place per the active window's style flags. If the underline flag is set, the bottom row of the buffer is forced to all-ones (every pixel of the bottom scan-line lit). If the inverse flag is set, every word of the buffer is bitwise-inverted. The two transformations compose: a cell can be both inverse and underlined, in which case the underline pass runs first and the resulting buffer is then inverted, leaving the bottom row all-zeros. Implementations should follow this order to match the original.

3. **Driver dispatch.** The emitter asks the driver to render one cell at absolute screen position `(top_left_x + cursor_x, top_left_y + cursor_y)` in the active window's colour, using the working buffer as the cell's bitmap. The driver does whatever is needed to put those pixels on display — for an EGA-style driver, this is a per-plane write into video memory with bit-fielded foreground/background masks; for a modern backend, it could be a glyph-indexed blit or a terminal-style cell update.

The text system's contract with the driver is "render this prepared cell at this position in this colour". Anything beyond that — scrolling a rectangle, clearing a rectangle, setting an attribute on a rectangle — is also a driver call, but invoked from elsewhere in the text system, such as auto-scroll on overflow or a higher-level clear-window helper, and is described in the driver ABI document rather than here.

## 8. Boot-Time Setup and Window Configuration

At program startup, the text system is initialised in three steps:

1. **Driver selection and load.** Startup inspects flags set from the command line (or the player's earlier configuration) to decide which of the available drivers — historically CGA, EGA, Tandy, and Hercules — to load. The chosen driver's image is loaded into memory and its dispatch entry point is registered. A modern engine targeting a single backend collapses this step to "load the one display driver."

2. **Window descriptor defaults.** All four window descriptors are reset to a known initial state: each window's rectangle is set to the full 40×25 screen (corners `(0, 0)` and `(39, 24)`), each cursor is set to `(0, 0)`, each colour is set to bright white on black (foreground 15, background 0), and each window's flags are cleared. The active window is set to window 0. After this step, any output call produces visible output.

3. **Per-window configuration by gameplay code.** When the game's UI is assembled, gameplay routines call the rectangle setter to lay out each window — main text area, status panel, input prompt, and so on — and the cursor and colour setters as needed. From then on, the active window is switched whenever UI focus moves.

The rectangle setter takes a window index (0–3) and four cell coordinates, and updates only the four rectangle bytes of the chosen descriptor; it leaves the cursor, colour, and flag bytes untouched, so a window can be resized without losing its other state. The setter clamps each X to 0–39 and each Y to 0–24, then swaps the X pair if the supplied left exceeds the supplied right and swaps the Y pair if the supplied top exceeds the supplied bottom. The result always satisfies the rectangle invariant. An out-of-range window index is a silent no-op.

The colour and flag setters write one byte of one descriptor; their effects are as described where the colour and flag fields are introduced.

## 9. Open Questions and Variations

This section records places where the picture is not yet complete or where evidence is internally inconsistent.

- **Style and clear writers.** The descriptor/cache carries underline,
  centring, inverse, colour, and rectangle-clear state used by the text and
  display paths. The decoded per-cell emitter itself only handles line-feed and
  carriage-return, and drops high-bit bytes. The remaining writer paths for
  toggling underline/inverse and clearing the active window are not fully
  pinned down in public prose yet.

- **No-advance gate writers.** The per-cell emitter consults a shared resident
  cursor-advance gate, and the input cursor blink is one confirmed writer. Any
  additional gameplay/UI writers outside the blink path still need call-site
  enumeration.

- **Screen size constants under non-EGA drivers.** The cursor-write bounds check, the rectangle clamps, and the descriptor defaults all assume a 40-column by 25-row grid. The original game ships drivers for four hardware targets, and at least one (Hercules) triples the per-cell pixel stride. Whether the *cell* dimensions ever change — whether 40×25 is the same on all drivers — has not been verified. The conservative reading: 40×25 is a system-wide constant, and drivers vary only in pixel size per cell. A modern backend can treat 40×25 as fixed.

- **NUL inside the per-cell emitter.** The emitter does not special-case NUL; in isolation it would render the glyph for code zero. In practice the wrap-aware printer flushes on NUL and never forwards one, so this corner is hard to observe. Treat NUL-to-emitter as undefined.

- **Live-snapshot anomaly for descriptor 0.** A memory snapshot taken at the title screen shows record 0 with a rectangle that violates the invariant (right < left). The most likely explanation is that the title-screen overlay reuses the descriptor table memory as scratch; under normal gameplay, the API never produces an inverted rectangle. Implementations following the API described here cannot reach that state and need not handle it.

- **Scroll-by-N semantics.** The auto-scroll path that runs when the cursor steps off the bottom invokes a driver operation with what appears to be a one-cell pixel argument. Whether this is generic "scroll by N pixels" or specifically "scroll by one cell" is a driver-ABI question. The text system's contract is "scroll up by exactly one cell, leaving the bottom row blank in the current background colour."

- **Single-driver collapse.** A modern implementation almost certainly does not need four parallel hardware drivers. The text-system behaviour described here is independent of which driver is loaded; treating the system as if exactly one (EGA-equivalent) driver is always present is a sound simplification.

## 10. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The per-cell emitter and its glyph and scroll helpers — derived from `u5-decomp/functions/ULTIMA_EXE/0x16BA_putchar.md`, `u5-decomp/functions/ULTIMA_EXE/0x17F4_glyph_to_cell_buffer.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1F77_descriptor_to_pixel_rect.md`.
- The wrap-aware string printer and its centring branch — derived from `u5-decomp/functions/ULTIMA_EXE/0x1850_print_string.md`.
- The padded numeric printer — derived from `u5-decomp/functions/ULTIMA_EXE/0x1A3E_print_number.md`.
- The cursor accessors — derived from `u5-decomp/functions/ULTIMA_EXE/0x1F12_get_cursor_x.md`, `u5-decomp/functions/ULTIMA_EXE/0x1CEE_get_cursor_y.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1BF2_set_cursor_pos.md`.
- The window-descriptor initialisation, rectangle configuration, and active-window selection — derived from `u5-decomp/functions/ULTIMA_EXE/0x1184_init_text_descriptor_table.md`, `u5-decomp/functions/ULTIMA_EXE/0x1C22_set_text_descriptor_rect.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1B94_set_display_mode.md` (the latter, despite its filename, is the active-window selector).
- The driver-load step in boot-time setup — derived from `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- The C-runtime string-length utility used at some call sites for label width — derived from `u5-decomp/functions/ULTIMA_EXE/0x216C_string_length.md`. This utility is the standard NUL-terminated string length function and does not warrant a dedicated spec section.
