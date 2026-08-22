# Text Output

## 1. Overview

Ultima V draws all of its game text — narration, names, prompts, conversation lines, and status panels — through a single small subsystem. It maintains four independent text windows on a fixed 40-column by 25-row character grid, exposes a small set of primitive operations (emit one character, emit a word-wrapped string, emit a padded number, erase or pad typed input, read or write the cursor), and hands the pixels of each character off to a separately loaded display driver.

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

Selecting a window unpacks the descriptor's colour and flags into cached
runtime fields used by the inner glyph loop. Extended text control bytes can
also affect those cached fields: `0xFB` clears centre-output, `0xFC` sets
centre-output, `0xFD` toggles inverse video, `0xFE` toggles underline, and
`0xFF` clears the active text window's rectangle through the display-driver
fill path. A separate clear/reset helper clears underline, centre, and inverse
together. These control bytes are not rendered as glyphs.

The rectangle has a hard invariant: `top_left_x ≤ bottom_right_x` and `top_left_y ≤ bottom_right_y`, both within the screen extent. Operations that mutate the rectangle (see Section 8) enforce this invariant by clamping out-of-range arguments and swapping inverted pairs. Operations that read the rectangle (wrap, scroll, conversion to pixel coordinates) assume the invariant holds.

## 4. Cell Coordinates and the Screen

The screen is a 40-column by 25-row grid. The top-left cell is column 0, row 0; the bottom-right is column 39, row 24. All cell-coordinate fields and arguments in this document live in this grid.

A cell is one glyph-sized rectangle of pixels. The pixel dimensions of a cell are decided by the loaded display driver and are not part of the text-system contract; the text system only speaks in cell coordinates. When the driver converts a cell rectangle into a pixel rectangle (for clear or scroll), it scales both corners by the cell size and adjusts the bottom-right corner to the *last* pixel inside that cell, not the first pixel of the next cell.

Window rectangles use absolute cell coordinates. Cursor positions and width arguments to the wrap-aware printer use window-local coordinates. The conversion is addition: a cursor at window-local `(cursor_x, cursor_y)` lies at absolute screen cell `(top_left_x + cursor_x, top_left_y + cursor_y)`. A window's width in cells is `bottom_right_x − top_left_x`; this figure is what wrapping decisions use, and it does not include the trailing column. A window whose corners are columns 6 and 33 has width 27 — twenty-seven characters fit before wrapping is forced.

## 5. Output Primitives

The system exposes five families of operations. None of them takes a window argument — they all operate on whichever window is currently active.

**The per-cell emitter** takes one byte and either renders one glyph at the active window's cursor or interprets newline/carriage-return as cursor movement. It is the foundation of the system; both the wrap-aware printer and the numeric printer go through it. Its behaviour:

- A byte with the high bit clear and not equal to line-feed or carriage-return is rendered as a glyph at the current cursor cell, in the active window's current colour and with any active style flags applied. The cursor then advances one cell to the right. If the advance would carry the cursor past `bottom_right_x`, the cursor wraps to the window's left edge and steps down one row. If the row advance would carry the cursor past `bottom_right_y`, the window scrolls (Section 7) and the cursor is left on the now-blank bottom row.
- A line-feed byte advances the cursor down one row without emitting a glyph and without resetting the column. If that step carries the cursor past `bottom_right_y`, the window scrolls.
- A carriage-return byte returns the cursor to the window's left edge without changing the row and without emitting a glyph.
- Selected high-bit control bytes are handled by the adjacent extended-control
  path. The confirmed controls are `0xFB` for centre-output off, `0xFC` for
  centre-output on, `0xFD` for inverse-video toggle, and `0xFE` for underline
  toggle; they do not emit glyph pixels and do not advance the cursor. `0xFF`
  clears the active window's inclusive pixel rectangle using the same
  cell-to-pixel conversion as scroll. Other high-bit bytes outside the
  confirmed control range have no public glyph meaning.
- A resident cursor-advance gate can suppress the cursor advance after a glyph emit. The glyph is still rendered, but the cursor stays put. This gate is shared runtime state rather than one of the descriptor style bits; the input cursor blink temporarily disables it so blink frames paint in place.

**The wrap-aware string printer** is the resident text primitive used throughout
the overlays; there is no per-overlay formatted-output thunk layer. It takes a
near pointer to a NUL-terminated byte string and emits it into the active window
with word wrapping. It accumulates characters in a fixed-size internal line
buffer (large enough for the widest possible window) while tracking the most
recent point at which a word break could have happened. When a soft break
(space, line-feed, or carriage-return) is reached and the line still fits in the
window's width, the line is emitted via the per-cell emitter. When the next
character would carry the line past the window's right edge, the printer backs
up to the most recent soft break, emits everything up to that break, and begins
a new line with the remainder. A NUL forces a final flush. Line-feed and
carriage-return bytes embedded in the source string force an immediate flush at
that point and pass through to the per-cell emitter so the cursor moves
accordingly.

If the active window's centre flag is set, the printer computes the centred starting column for the line (`(width − characters_in_line) / 2`) and repositions the cursor horizontally to that column before emitting; the cursor's row is left alone, so centring affects only horizontal placement. The centre flag applies once per line of output produced by this printer, and only by this printer — the per-cell emitter does not centre.

An empty string is a no-op.

**The padded numeric printer** takes a signed 16-bit integer, a field width, and a single-byte pad character. It formats the value into a small internal buffer with leading copies of the pad character, an optional minus sign, and the decimal digits of the absolute value, producing a NUL-terminated string of exactly the requested width (or wider, if the value's natural width exceeds the field). It then hands the buffer to the wrap-aware string printer. The field width is clamped at 39, matching the maximum window width. The integer is treated as signed: values from −32768 through 32767 print correctly; values above 32767 (if interpreted as unsigned) render as their two's-complement signed equivalent. To zero-pad, the caller passes the digit-zero character as the pad; to space-pad, the caller passes a space. Because the numeric printer routes through the wrap-aware string printer, numeric output respects the active window's width, centre flag, and wrap behaviour.

**The typed-input space eraser** emits a caller-supplied number of spaces while
temporarily suppressing normal cursor advance, then explicitly repositions the
cursor. Free-text prompts use it for destructive backspace and Escape-clears:
one erased character repaints the editable tail with a space and leaves the
cursor at the next replacement position; clearing a whole typed buffer repeats
the same operation for the accumulated length. This helper is a presentation
companion to the input line editor, not a general string printer. It must
preserve and restore the prior cursor-advance gate so nested prompt or blink
rendering keeps its own advance policy.

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

## 8. Proportional Paragraph Renderer

The intro slides, chargen gypsy paragraphs, and chargen question prompts use a
separate proportional-font paragraph renderer from the FONT overlay. It is not
the same path as the fixed 40-by-25 text-window printer above. Its coordinates
are pixel-oriented, its glyph advances come from the resident advance table
published in `formats/font-pcs.md` section 4, and it is called with a loaded
NUL-terminated text buffer plus the active proportional-font resource segment.

The renderer owns layout and glyph emission. The caller owns which text record
is loaded, where the paragraph starts, and whether the player must press a key
before the next record is drawn.

### 8.1 Layout descriptor

The renderer reads and updates a small resident descriptor. It holds, in pixel
units:

| Field | Meaning |
|---|---|
| Left margin A, right margin A | Horizontal bounds used outside the special band. |
| Left margin B, right margin B | Horizontal bounds used inside the special band. |
| Band low, band high | The vertical range that selects the B margins. |
| Space advance | Pixels a space contributes (shipped default 5). |
| Pen X, pen Y | The running cursor. |

Margin selection is evaluated once at entry and again after every line break:
the B pair is used when `band_low < pen_y < band_high` — strictly inside, both
ends excluded — and the A pair otherwise. `available = right - left` for the
selected pair. Because the check runs per line, a paragraph can flow around a
picture: the chargen gypsy-wagon paragraph uses full width above the artwork
and an indented left margin below it.

At entry the renderer treats `pen_x - left` as width already consumed on the
current line, so a caller can chain a second paragraph onto a partly filled
line without resetting the pen.

The shipped resident defaults are margins `0..320` for both pairs, a band of
`200..200` (which never matches, so the A pair always applies), a space advance
of `5`, and a pen of `(0, 60)`. Callers overwrite what they need. The only
caller that changes the space advance is character creation, which uses `4` for
one paragraph and restores `5` immediately afterwards.

### 8.2 Byte handling

| Byte | Measured as | Drawn as |
|---|---|---|
| NUL | ends the buffer | nothing |
| Line feed (`0x0A`) | ends the line | nothing |
| Space (`0x20`) | the descriptor's space advance | horizontal advance only, plus justification padding |
| Any other byte at or below `0x20` | same as space | same as space |
| Left brace (`0x7B`) | a fixed **15** pixels | nothing; the pen still advances 15 |
| Underscore (`0x5F`) | **zero** | nothing, and no advance |
| Any byte above `0x20` not listed above | its advance-table entry **plus one** | one glyph, then the same advance |

The plus-one is the inter-glyph gap. It applies to every drawn glyph including
the last one on a line, and it is not part of the table values. A space never
gets the plus-one.

Neither the advance table nor the font gives the space a width of its own; both
record zero. The space advance comes from the descriptor. An engine that
measures spaces from the font will collapse every space to nothing.

Left brace is a paragraph/page marker owned by the caller's record loop: the
renderer does not wait for input on it, it just leaves a 15-pixel gap.
Underscore is a soft hyphen: invisible and weightless, but a legal break point
(section 8.3).

Control bytes other than NUL and line feed do not appear in shipped text. The
renderer would measure and advance them as spaces, so that is the safe
behaviour to implement; do not look up an advance-table entry for a code below
`0x21`.

### 8.3 Measurement, wrapping, and the right edge

Measurement runs from the current line start, accumulating an advance and
counting spaces, and stops at the first of:

- NUL or line feed, which ends the line cleanly;
- `available <= accumulated`, which is an overflow.

The right edge is therefore **exclusive**: a line is kept only while its total
advance is strictly less than the available width.

On overflow the renderer backtracks from the stop position, subtracting each
glyph's advance as it goes and skipping brace and underscore without
subtracting, until one of:

- **a space** — break there. The space is not drawn: its advance is subtracted
  and the space count drops by one.
- **an underscore that fits** — break there, and add the hyphen glyph's advance
  plus one to the line, because a visible hyphen will be drawn. "Fits" means
  `hyphen_advance + accumulated + 1 < available`, using the advance-table entry
  for `-` (which is `3` in the shipped font).
- **the start of the line** — a degenerate single-token overflow. The line ends
  where it is and the walk consumes one byte, so an over-long unbreakable token
  is emitted one byte per line rather than looping forever.

After the line is drawn, the renderer skips **exactly one** break byte: the
space, line feed, or underscore it broke at. That is the leading-space rule: a
single space after a wrap is dropped, and a run of two or more leaves the
extras as leading spaces on the next line. Line feed is likewise consumed once,
so a blank line requires two consecutive line feeds.

### 8.4 Justification, not centering

There is **no centering** in this renderer. Single-line intro overlays are not
centered from a measured width; their pen X comes from the caller's per-slide
layout values. An engine that centers proportional intro text will not match
the original.

What the renderer does instead is **full justification**. When a line is
accepted, `slack = available - measured_advance` is computed once. During the
render pass, at each space, after the ordinary space advance:

```text
extra = slack / spaces_remaining        (integer division, truncating)
pen_x += extra
slack -= extra
spaces_remaining -= 1
```

Because the division truncates and the remainder is carried forward, the
leftover pixels land on the **last** spaces of the line, not the first.

Justification is skipped entirely when the byte the line broke at is NUL or
line feed. So the last line of a paragraph, and any line ended by an explicit
newline, are left ragged-right; every other line is flush on both margins.

### 8.5 Line advance and clipping

If the line broke at an underscore, the hyphen glyph is drawn at the pen before
the line advances.

The line advance is a fixed **9** pixels of pen Y, independent of the margins
or the space advance. After advancing, the margin pair is re-selected, pen X is
reset to the selected left margin, and the available width is recomputed.

Glyph drawing is clipped at the bottom: once pen Y reaches **192**, glyphs stop
being drawn but the pen still advances exactly as if they were, so layout does
not change when text runs off the bottom.

`QUESTION.DAT` and the intro story records both rely on the brace and
underscore conventions. A compatible implementation should treat those bytes as
lightweight markup in this proportional-font path only; they are not global
control bytes for the fixed-cell resident printer.

### 8.6 Centered single-line captions

Some intro-family text is centered, but it does not go through this renderer at
all — it goes through the fixed-cell printer. See `systems/intro.md` for the
Return-to-View chapter captions and the title-screen credit line, which share
one centered-caption helper: the caption is centered by character cell, not by
measured pixel width.

## 9. Boot-Time Setup and Window Configuration

At program startup, the text system is initialised in three steps:

1. **Driver selection and load.** Startup inspects flags set from the command line (or the player's earlier configuration) to decide which of the available drivers — historically CGA, EGA, Tandy, and Hercules — to load. The chosen driver's image is loaded into memory and its dispatch entry point is registered. A modern engine targeting a single backend collapses this step to "load the one display driver."

2. **Window descriptor defaults.** All four window descriptors are reset to a known initial state: each window's rectangle is set to the full 40×25 screen (corners `(0, 0)` and `(39, 24)`), each cursor is set to `(0, 0)`, each colour is set to bright white on black (foreground 15, background 0), and each window's flags are cleared. The active window is set to window 0. After this step, any output call produces visible output.

3. **Per-window configuration by gameplay code.** A census of every call to the
   rectangle setter in the analyzed build shows that gameplay code reshapes only
   two of the four windows, and it does so transiently rather than as a one-time
   UI layout pass:

   - **Window 0** is reshaped by the resident inverse-text banner helper, which
     narrows it to a single-row strip spanning columns 6 to 33 on rows 12–13 and
     then restores it to the full screen, and by the dungeon view, which sets a
     variable left/top with the full right/bottom and later restores full
     screen.
   - **Window 1** is the framed right-hand side panel. Every caller — the
     character-sheet overlay, the command overlay, the inn guest register, and
     the arms-shop sell browser — uses the same idiom: set the window to
     `(24, 1)..(38, N)` and clear it, then widen the right edge to
     `(24, 1)..(39, 9)` and draw the frame.
   - **Windows 2 and 3 are never passed to the rectangle setter at all.** They
     keep the boot-time defaults from step 2 for the whole session: full-screen
     rectangle, bright white on black, cleared flags.

   Window 2 is the one ordinary gameplay text goes to — conversation, shop
   dialogue, command feedback. Because it is never reshaped or recoloured, its
   only mutable state is its cursor, which advances with output and is moved
   only by explicit cursor calls made while it is active. The colour setters are
   called only by the dungeon inspection overlay and by the resident
   framed-message-window helpers; the town, overworld, and conversation overlays
   never call them.

   From then on, the active window is switched whenever UI focus moves; a panel
   selects window 1, draws, and selects window 2 again when it is done.

   Source provenance: derived from private analysis note
   `../u5-decomp/notes/shop_window_geometry_recount_2026-08-22.md`.

The rectangle setter takes a window index (0–3) and four cell coordinates, and updates only the four rectangle bytes of the chosen descriptor; it leaves the cursor, colour, and flag bytes untouched, so a window can be resized without losing its other state. The setter clamps each X to 0–39 and each Y to 0–24, then swaps the X pair if the supplied left exceeds the supplied right and swaps the Y pair if the supplied top exceeds the supplied bottom. The result always satisfies the rectangle invariant. An out-of-range window index is a silent no-op.

The colour and flag setters write one byte of one descriptor; their effects are as described where the colour and flag fields are introduced.

## 10. Boundaries And Parity Work

This section separates text-output compatibility boundaries from remaining
pixel-parity work.

- **Cursor-advance gate ownership.** The per-cell emitter consumes a shared
  cursor-advance gate. Confirmed callers use it for cursor blink painting,
  typed-input erase/padding, and intro-frame cell decoration. The clean
  contract is the visible result: emit a glyph with normal advance, or emit a
  glyph in place while the caller restores or repositions the cursor. The gate
  itself is resident presentation state, not save state or gameplay state.

- **Screen size constants under non-EGA drivers.** The cursor-write bounds
  check, rectangle clamps, and descriptor defaults all assume a 40-column by
  25-row cell grid. Hardware drivers may vary the pixel stride or pixel
  encoding behind each cell, but the fixed-cell text-system contract remains
  40 by 25.

- **NUL inside the per-cell emitter.** The wrap-aware string printer treats NUL
  as terminator and never forwards it. Directly sending NUL to the per-cell
  emitter is outside the public text contract; compatible callers should use
  NUL only as string termination.

- **Live-snapshot anomaly for descriptor 0.** A title-screen snapshot showed one
  descriptor with inverted rectangle corners. The public writer API clamps and
  orders rectangle corners, so normal gameplay cannot produce that state. Treat
  the snapshot as title/overlay scratch reuse unless a future caller-level
  trace proves otherwise.

- **Scroll-by-N semantics.** Auto-scroll after bottom overflow moves the active
  text-window rectangle up by exactly one cell and leaves the bottom row blank
  in the current background colour. The lower-level driver operation also
  supports a pixel-distance argument; that is display-driver ABI detail, not a
  separate text-output rule.

- **Proportional right-edge exactness.** Resolved. The advance table is
  published in `formats/font-pcs.md` section 4, the exclusive right-edge test,
  the plus-one inter-glyph gap, the space advance source, the backtracking
  break rule, and the justification arithmetic are in section 8 above, and the
  glyph artwork container is specified in `formats/font-pcs.md` section 3.
  What remains is screenshot comparison, not unknown rules. The one honestly
  unknown piece is the advance-table entries for codes below `0x20`, which
  overlap unrelated resident data and are unreachable through the renderer;
  they must not be invented.

- **Single-driver collapse.** A modern implementation does not need four
  parallel hardware drivers unless it is explicitly emulating original hardware
  targets. The text-system behaviour described here is independent of which
  driver is loaded; treating the system as if exactly one EGA-equivalent driver
  is always present is a sound engine simplification.

## 11. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The per-cell emitter, its extended controls, and its glyph and scroll helpers — derived from `u5-decomp/functions/ULTIMA_EXE/0x16BA_putchar.md`, `u5-decomp/functions/ULTIMA_EXE/0x17F4_glyph_to_cell_buffer.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1F77_descriptor_to_pixel_rect.md`.
- The wrap-aware string printer and its centring branch — derived from `u5-decomp/functions/ULTIMA_EXE/0x1850_print_string.md`.
- The padded numeric printer — derived from `u5-decomp/functions/ULTIMA_EXE/0x1A3E_print_number.md`.
- The cursor accessors — derived from `u5-decomp/functions/ULTIMA_EXE/0x1F12_get_cursor_x.md`, `u5-decomp/functions/ULTIMA_EXE/0x1CEE_get_cursor_y.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1BF2_set_cursor_pos.md`.
- The window-descriptor initialisation, rectangle configuration, and active-window selection — derived from `u5-decomp/functions/ULTIMA_EXE/0x1184_init_text_descriptor_table.md`, `u5-decomp/functions/ULTIMA_EXE/0x1C22_set_text_descriptor_rect.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1B94_set_display_mode.md` (the latter, despite its filename, is the active-window selector).
- The whole-build census of which windows are actually configured at runtime — derived from `u5-decomp/notes/shop_window_geometry_recount_2026-08-22.md`.
- The driver-load step in boot-time setup — derived from `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- The C-runtime string-length utility used at some call sites for label width — derived from `u5-decomp/functions/ULTIMA_EXE/0x216C_string_length.md`. This utility is the standard NUL-terminated string length function and does not warrant a dedicated spec section.
- Cross-overlay call-frequency and no-thunk text-output architecture — derived
  from `u5-decomp/notes/hot_path_analysis.md` and
  `u5-decomp/notes/engine_idioms.md`.
- The proportional-font paragraph renderer used by intro, chargen, and
  Return-to-View text, including the layout descriptor field roles, the
  exclusive right-edge test, the plus-one inter-glyph gap, the backtracking
  break rule, the justification arithmetic, and the fixed nine-pixel line
  advance -- derived from
  `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md` and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 2.
- The typed-input space eraser and cursor-advance gate preservation -- derived
  from `u5-decomp/functions/ULTIMA_EXE/0x1FA0_print_n_spaces.md` and
  cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/0x1E38_read_text_input.md`.
- Intro-frame decoration as another cursor-advance gate writer -- derived from
  `u5-decomp/functions/INTRO_OVL/0x04E0_clear_intro_text_window.md` and
  `u5-decomp/functions/INTRO_OVL/0x1E62_clear_continue_window.md`.
