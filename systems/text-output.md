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

- A byte with the high bit clear and not equal to line-feed or carriage-return is rendered as a glyph at the current cursor cell, in the active window's current colour and with any active style flags applied. The cursor then advances one cell to the right. If the advance would carry the cursor past `bottom_right_x`, the cursor wraps to the window's left edge and steps down one row. If the row advance would carry the cursor past `bottom_right_y`, the window scrolls (Section 7) and the cursor is left on the bottom row. The scroll does not blank the vacated row; the glyph that triggered the scroll is written over it immediately.
- A line-feed byte is a **combined carriage return and line feed**: it emits no glyph, advances the cursor down one row *and* returns the column to the window's left edge. If that step carries the cursor past `bottom_right_y`, the window scrolls. Implementations must not treat it as a bare row advance — the blank-row mechanism of Section 10.4 depends on the column reset.
- A carriage-return byte returns the cursor to the window's left edge without changing the row and without emitting a glyph. It is the column-only half of the line-feed behaviour.
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

If the active window's centre flag is set, the printer computes a centred starting column for the line and repositions the cursor horizontally to that column before emitting; the cursor's row is left alone, so centring affects only horizontal placement. The computation works from two quantities: the columns still *available* on the current row, which is `(bottom_right_x − top_left_x) − cursor_x` as the printer was entered, and the **index of the last character** of the line about to be emitted, which is one less than its character count. The starting column is `(available − last_character_index) / 2`, truncated toward zero. For the ordinary case of a line emitted with the cursor at the window's left edge, that is exactly `(columns_in_window − characters_in_line) / 2` truncating, where `columns_in_window` is `bottom_right_x − top_left_x + 1` — i.e. plain centring in the window's column count, with even-length lines centred exactly and odd-length lines landing half a cell (four pixels) to the left. Implementations must not drop the “plus one” and centre against `bottom_right_x − top_left_x`: that agrees on odd-length lines but shifts every even-length line one whole cell left. The centre flag applies once per line of output produced by this printer, and only by this printer — the per-cell emitter does not centre.

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

1. **Glyph-bitmap fetch.** The emitter selects the glyph bitmap for the byte being rendered from the currently active fixed-cell font. The font is a separately loaded asset held in the resident font-slot table described below, not part of the display driver's image; the text system needs to know only its row stride, which depends on which font pair the selected driver loaded. The bitmap is copied into a small working buffer that the system uses as the cell's pixel pattern. **Correction:** an earlier revision of this step said "the font lives inside the driver's loaded image". That is withdrawn — it contradicted the font-slot paragraph below, `formats/font-ch.md`, and the boot sequence in `systems/intro.md` section 3, which loads the two character files into resident slots before any driver text is drawn.

2. **Style transformations.** The working buffer is then post-processed in place per the active window's style flags. If the underline flag is set, the bottom row of the buffer is forced to all-ones (every pixel of the bottom scan-line lit). If the inverse flag is set, every word of the buffer is bitwise-inverted. The two transformations compose: a cell can be both inverse and underlined, in which case the underline pass runs first and the resulting buffer is then inverted, leaving the bottom row all-zeros. Implementations should follow this order to match the original.

3. **Driver dispatch.** The emitter asks the driver to render one cell at absolute screen position `(top_left_x + cursor_x, top_left_y + cursor_y)` in the active window's colour, using the working buffer as the cell's bitmap. The driver does whatever is needed to put those pixels on display — for an EGA-style driver, this is a per-plane write into video memory with bit-fielded foreground/background masks; for a modern backend, it could be a glyph-indexed blit or a terminal-style cell update.

**The active fixed-cell font is a selectable slot.** The text system keeps a
one-entry "current font" pointer plus a small table of loaded font slots, and a
selector call publishes a slot into it. Two slots are loaded at boot: **slot 0
is the Roman text font and slot 1 is the runic font**, both specified in
`formats/font-ch.md` - one hundred twenty-eight glyphs of eight bytes each,
eight by eight pixels, one bit per pixel, most significant bit leftmost, glyph
`n` at offset `n * 8`. The two fonts share code points, so switching slots
re-alphabets the same byte values rather than remapping them.

Callers switch the slot explicitly and are responsible for switching back;
several presentation surfaces do exactly that for a single cell. The inventory
picker selects the runic slot for one selector character and for the symbol
prefixes on spell and reagent rows (`inventory.md` section 4.5); the dungeon map
selects it for most of its cell glyphs and deliberately does *not* select it for
four classes whose runic slots are blank or wrong (`dungeon-mode.md` section
12.3). This closes the runtime-selection question left open in
`formats/font-ch.md` section 9.

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
before the next record is drawn. The concrete per-screen values one caller
supplies — the intro story sequence's twenty-one margin/band/pen sets — are
published in `systems/intro.md` section 10 under "Per-step paragraph box"; that
is also the worked example of how the band makes text flow around artwork.

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

Left brace is a **first-line indent marker**: the renderer draws nothing and
leaves a 15-pixel gap. It is not a page break and it does not make the renderer
wait for input; the caller's record loop owns the wait. Every shipped story and
question record opens with one, and a record with several paragraphs has
several.

Underscore is a soft hyphen: invisible and weightless, but a legal break point
(section 8.3). **The renderer never hyphenates on its own.** Mid-word breaks in
the original come only from soft hyphens the author placed in the text data, so
a compatible implementation must preserve them through loading and must not run
its own hyphenator.

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

3. **Per-window configuration by gameplay code.** Three windows are given their
   standing gameplay rectangles once, when the gameplay screen is assembled;
   section 10.1 publishes those three rectangles and is the authoritative list.
   On top of that standing layout, overlays reshape windows transiently:

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
   - **Window 2** is set once, during gameplay-screen assembly, to the message
     window rectangle in section 10.1, and no overlay reshapes it afterwards.
     An earlier revision of this document said window 2 is never passed to the
     rectangle setter and keeps the full-screen boot default; that is withdrawn.
     The earlier census covered the shop and panel overlays and did not reach
     the one-time gameplay-screen assembly.
   - **Window 3 is never passed to the rectangle setter at all.** It keeps the
     boot-time defaults from step 2 for the whole session: full-screen
     rectangle, bright white on black, cleared flags. It is unused by gameplay.

   Window 2 is the one ordinary gameplay text goes to — conversation, shop
   dialogue, command feedback. Because nothing recolours it after assembly, its
   only mutable state is its cursor, which advances with output and is moved
   only by explicit cursor calls made while it is active. The colour setters are
   called only by the dungeon inspection overlay and by the resident
   framed-message-window helpers; the town, overworld, and conversation overlays
   never call them.

   From then on, the active window is switched whenever UI focus moves; a panel
   selects window 1, draws, and selects window 2 again when it is done.

   Source provenance: derived from private analysis notes in
   `../u5-decomp/notes/`.

The rectangle setter takes a window index (0–3) and four cell coordinates, and updates only the four rectangle bytes of the chosen descriptor; it leaves the cursor, colour, and flag bytes untouched, so a window can be resized without losing its other state. The setter clamps each X to 0–39 and each Y to 0–24, then swaps the X pair if the supplied left exceeds the supplied right and swaps the Y pair if the supplied top exceeds the supplied bottom. The result always satisfies the rectangle invariant. An out-of-range window index is a silent no-op.

The colour and flag setters write one byte of one descriptor; their effects are as described where the colour and flag fields are introduced.

## 10. Gameplay Screen Text Windows

### 10.1 The three windows the gameplay screen installs

The gameplay screen is assembled once, on the intro's Journey Onward path,
before the save file is read. That assembly configures three of the four
window descriptors and leaves the fourth alone:

| Window | Cell rectangle | Pixel rectangle | Role |
|---:|---|---|---|
| 0 | `(0, 0) - (39, 24)` | `(0, 0) - (319, 199)` | Full screen. Every piece of border chrome is written through it — the frame's corner glyphs, the sky strip, the wind banner, the dungeon level and facing labels — so its window-relative cursor coordinates are identical to absolute grid cells. |
| 1 | `(24, 1) - (39, 9)` | `(192, 8) - (319, 79)` | Stats window: six roster rows, the counters row, the date row, and the timed-effect slot. See `stats-panel.md`. |
| 2 | `(24, 11) - (39, 23)` | `(192, 88) - (319, 191)` | Message window: command echo, command output, and the live input line. |

One transient reshape precedes those three: window 0 is briefly set to
`(1, 16) - (38, 23)`, then restored to the full screen and cleared with the
clear-window control byte, which blanks the intro's lower text block before the
frame is painted.

**There is no fourth gameplay window.** Window 3 is never reshaped after boot
and keeps the full-screen default for the whole session.

- **Attributes.** Windows 1 and 2 keep the boot attribute — foreground 15 on
  background 0 — for the whole session; no gameplay path rewrites either. Window
  0's foreground is left at the frame's accent index by the chrome writers, and
  its background is never changed from 0.
- **Initial cursors.** Windows 1 and 3 keep `(0, 0)` from boot. Window 0's
  cursor is wherever the last chrome writer left it. Window 2's cursor is
  explicitly set to window-relative `(0, 12)` — absolute row 23, its own last
  row — so the message log is bottom-anchored from the very first frame.
- **Column 39.** The stats window spans columns 24..39, but the panel only ever
  writes columns 24..38, because the roster and counter boxes are fifteen cells
  wide: their right rule sits at pixel `x = 312`, the first pixel of column 39.
- **Row 24.** Absolute text row 24 (`y = 192..199`) is addressable — it is the
  last row of window 0's full-screen rectangle above — but **no gameplay path
  writes it**. It is cleared to black when the frame is painted and stays black
  for the rest of the session. (An earlier revision said it "lies inside no
  window", which contradicted this section's own window-0 rectangle. Outside
  gameplay the row is used: the Return-to-View chapter caption is printed on it
  through the same full-screen window, `systems/intro.md` section 12.)

An earlier revision of section 9 said, on the strength of a shop-overlay
geometry census, that windows 2 and 3 are never passed to the rectangle setter
and keep full-screen defaults for the whole session. That is withdrawn for
window 2: the gameplay-screen assembly reshapes it to the message-window
rectangle above, and every later message, echo and prompt is bounded by that
rectangle rather than by the full screen. The statement stands for window 3.

### 10.2 The command-echo cycle

Every gameplay mode loop — overworld, town, and dungeon — runs the same three
steps in the same order before it reads a command key:

1. Emit a line feed into the message window.
2. Draw the right-pointing bracket end-cap at the window's first column
   (absolute column 24). The end-cap composite is specified in
   `display-driver.md` section 7; it is **not** the ASCII `>` character.
3. Read the key.

The marker therefore occupies column 24 and leaves the cursor at column 25,
which is where the echoed verb begins. Because the marker is emitted before the
read, echoed command lines carry it and pure output lines do not: a line such as
`Player: None!` starts unprefixed at column 24.

The overworld loop gates the newline-and-marker pair on a one-byte flag, and
sets that flag again immediately after emitting the pair. The flag is cleared
only on the "already sailing that way" path, where the loop synthesises a repeat
movement command rather than reading a key, so those synthesised turns do not
accumulate empty prompt lines. The town and dungeon loops emit the pair
unconditionally on every polled turn.

The newline-first ordering is a rule, not an incidental observation. It is what
produces the single blank row between command turns, and it is what closes lines
left open by verbs that prompt for an operand.

### 10.3 Echoed verb strings and their punctuation contract

There is no keystroke-indexed echo table; each command's handler holds its own
literal string and prints it through the wrap-aware printer. The trailing
punctuation of that string is a contract:

| Suffix | Meaning |
|---|---|
| `-` | A direction is prompted next and appended to the same line. |
| `...` then newline | The command opens a sub-mode or a full-screen panel; the line is closed immediately. |
| trailing space | An operand name is appended to the same line by the handling overlay. |
| newline | Complete; result text starts on the next row. |
| two newlines | Complete, plus one deliberate extra blank row. |
| none | The handling overlay owns the rest of the line. |

Representative literals, exactly as they appear on screen:

| Echo | Suffix class |
|---|---|
| `Pass` + newline | complete |
| `Board ` | operand follows |
| `Cast...` + newline | sub-mode |
| `Fire-`, `Get-`, `Jimmy-`, `Klimb-`, `Open-`, `Push-`, `Search-`, `Talk-` | direction follows |
| `Hole up- ` | direction follows, then an operand |
| `Mix Reagents` + two newlines | complete plus blank row |
| `Ready...` + two newlines | sub-mode plus blank row |
| `Use item` + two newlines | sub-mode plus blank row |
| `X-it `, `Yell ` | operand follows |
| `Z-stats...` + newline | full-screen panel |
| `Look` | overlay-owned; the handler appends the direction hyphen itself, so the visible line reads `Look-` while the direction is awaited |

The direction prompt appends `North`, `South`, `East`, `West` or `Pass`, each
followed by a newline, to the open line. `Pass` is what Escape and Space
produce.

An unrecognised command key prints `What?` followed by a newline and **consumes
no turn**: the mode loop skips its per-turn cleanup for that keypress, so no
game time passes. Two sibling refusals reach the screen through the same slot
with a disambiguating prefix, `D-What?` and `W-What?`, and the push-into-nothing
case prints `Push` + newline + `Not here!` + newline.

### 10.4 The blank row between commands

The per-cell emitter treats the line-feed byte as a combined carriage return and
line feed: it advances the row *and* returns the column to the window's left
edge. The carriage-return byte returns the column only.

A verb whose echo ends in a newline therefore leaves the cursor at column 0 of a
fresh row, and the next cycle's leading line feed advances again — producing
exactly one blank row after each completed command turn. Verbs whose echo ends
in a hyphen or a trailing space rely on that same leading line feed to close
their partially written line, which is why the newline comes first rather than
last.

### 10.5 Scrolling the message window

When output would carry the cursor below the message window's bottom row, the
window scrolls up by exactly one cell row and the cursor is left on the last
visible row. The vacated bottom row is **not** blanked; the output that caused
the scroll immediately overwrites it. There is no "press a key to continue"
pause anywhere on this path, and no page-at-a-time behaviour.

The underlying display entry is hardwired to this window's pixel column and to a
one-cell-row step, and ignores any larger requested distance; a general
scroll-by-N request therefore still scrolls exactly one row on the original.
See `display-driver-abi.md` section 9.5.

### 10.6 The live input line and its cursor

Typed input happens on the message window's own last row, so the visible layout
is a log whose final line is being edited — for example `Player: ` followed by
the input cursor, or `Look-` while a direction is awaited.

The input cursor is an animation, not a single glyph: it cycles through four
consecutive fixed-cell glyph codes, `0x05` through `0x08`, drawn in place with
the cursor-advance gate suppressed, and is erased with a space as soon as a key
arrives. The starting code and the cycle length are resident values rather than
literals, so an implementation should expose them as configuration.

Three readers share that presentation but differ in their key rules:

| | General typed string | Case-preserving text | Typed number |
|---|---|---|---|
| Used for | most free-text prompts | character names | numeric prompts |
| Case | keys are uppercased | preserved as typed | not applicable |
| World ticks while idle | yes | no | yes |
| Accepted | any printable byte | any printable byte | digits; a leading sign only in the first position |
| Backspace | destructive, erases one character backwards | same | same |
| Escape | erases the whole typed buffer | same | same |
| Terminator | Return, not echoed | same | same |

Backspace and Escape erase rather than overwrite: the helper repaints the
editable tail with spaces in place, with cursor advance suppressed, and then
repositions the cursor, wrapping back to the end of the previous row when it
passes column 0.

Not every prompt is typed input. The active-player prompt prints `Player: ` and
then runs a highlight picker — digit keys `1` through `6`, up and down, Return or
Space to accept, Escape to cancel, and `0` for "no active player", which prints
`None!` and a newline.

### 10.7 Framed border labels

A *framed border label* is a short caption written into a chrome band and
bracketed by the two triangular end-caps of `display-driver.md` section 7. The
stored literal is always the bare text; the brackets a reader transcribes as
angle characters are the two cap glyphs, and **no label literal in the game
contains an angle character**.

There are three distinct label slots, and they must not be described as one
mechanism, because their blanking geometry and their centring rules differ:

| Slot | Band | Written by | Content |
|---|---|---|---|
| Viewport top ribbon | text row 0, pixels x 40 to 152 | the surface sky strip, or the dungeon level label | see `view.md` section 4.2 and `dungeon-mode.md` section 4.1 |
| Viewport bottom ribbon | text row 23, pixels x 48 to 152 | the surface wind banner, or the dungeon facing label | as above |
| Stats-panel top ribbon | text row 0, pixels x 192 to 311 | the shared panel-label writer | `Select:` plus the picker page labels (`inventory.md` section 4.7) |

Only the third has a general writer. Its contract is:

1. Place the **opening cap in column `30 - (L / 2)`** (integer division), for a
   caption of `L` characters; the caption then occupies the next `L` columns and
   the closing cap the column after that. Column 30 is the anchor of that cap
   formula, **not** the caption's centre: the centre of the panel's fifteen-cell
   field (columns 24..38) is column 31, and an odd-length caption lands exactly
   on it. The full arithmetic and its worked example are in `stats-panel.md`
   section 9.
2. Blank the chrome band either side of the caption, within the pixel span
   x 192 to 311 on row 0.
3. Redraw the horizontal accent rule beneath the band at y = 7.
4. Emit the right-pointing cap, the caption, and the left-pointing cap.

When no picker and no selection is active, the stats-panel ribbon carries no
label and is repainted plain by the corresponding chrome helper.

The two viewport ribbons have no general writer: each producer positions its own
cursor, draws its own caps, and owns its own cell arithmetic. That is why the
dungeon facing label and the surface wind banner start at the same cell yet end
one cell apart.

A **fourth, unrelated** slot exists and is easy to confuse with these: the
single-character badge parked in the divider row between the stats panel and the
message window, which frames one glyph with the same caps. It is the
timed-effect indicator specified in `stats-panel.md` section 8, not a text
label, and it uses neither the centring rule nor the blanking geometry above.

Source provenance: derived from private analysis note
`../u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.

## 11. Boundaries And Parity Work

This section separates text-output compatibility boundaries from remaining
pixel-parity work.

### There is no "current message" to overwrite

An implementation that keeps a **single message slot** — one string field that
the turn epilogue writes and a command handler then overwrites — has invented a
conflict the original does not have, and will silently lose whichever line is
written first.

**The original has no such slot.** Text output is a *stream* into a windowed
grid. Each window carries a live cursor that stays where output last left it,
emission continues from that cursor, and when a line feed carries the cursor past
the window's bottom edge **the window scrolls**. Nothing holds "the current
message", so nothing can replace it.

So the question "does an epilogue line append, replace, queue, or take
precedence over a command result?" has no answer in the original's terms,
because it presupposes a slot. **Both lines are emitted, in the order they
occur**, and both are visible unless the second scrolls the first out of the
window. A turn that produces an epilogue announcement *and* a command result
shows the announcement first, then the result beneath it.

The practical consequence for a port: model the message area as an append-and-
scroll region, not as a value. An architecture that stores one message per turn
will match the original whenever a turn happens to produce exactly one line, and
diverge silently whenever it produces two — which is the hardest kind of
divergence to notice, because the common case looks correct.

This is a case where **matching the original's behaviour requires matching its
structure**. A port that reproduces each individual message correctly but holds
them in a slot will still lose lines, and no test of an individual message will
show it.

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
  text-window rectangle up by exactly one cell row and leaves the cursor on the
  last visible row. It does **not** blank the vacated row: whatever pixels lay
  immediately below the window scroll into it, and the caller's next output
  covers them. An earlier revision of this bullet said the bottom row is left
  blank in the current background colour; that is withdrawn. The lower-level
  driver operation nominally accepts a pixel-distance argument, but the EGA
  entry ignores it and always steps one cell row; see `display-driver-abi.md`
  section 9.5.

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

## 12. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The per-cell emitter, its extended controls, and its glyph and scroll helpers — derived from `u5-decomp/functions/ULTIMA_EXE/`, and `u5-decomp/functions/ULTIMA_EXE/`.
- The wrap-aware string printer and its centring branch — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The padded numeric printer — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The cursor accessors — derived from `u5-decomp/functions/ULTIMA_EXE/`, and `u5-decomp/functions/ULTIMA_EXE/`.
- The window-descriptor initialisation, rectangle configuration, and active-window selection — derived from `u5-decomp/functions/ULTIMA_EXE/`, and `u5-decomp/functions/ULTIMA_EXE/` (the latter, despite its filename, is the active-window selector).
- The overlay-side census of which windows are reshaped transiently — derived from `u5-decomp/notes/shop_window_geometry_recount_2026-08-22.md`. Its "window 2 is never configured" conclusion is corrected in section 9 step 3 and section 10.1.
- Source provenance: the three standing gameplay window rectangles and their attributes and initial cursors, the absence of a fourth gameplay window, the command-echo cycle and its newline-first ordering, the echoed verb strings and their punctuation contract, the unrecognised-key response and its no-turn result, the blank-row mechanism, the un-blanked scroll, the input-cursor animation, and the three typed-input readers are derived from private analysis note `../u5-decomp/notes/gameplay_screen_layout_2026-08-22.md`, cross-checked against a fresh local re-read of the shipped executable, overlays and shared data overlay.
- The selectable fixed-cell font slot, the two boot-loaded fonts and their shared code points, and the three framed-border-label slots with their differing centring and blanking rules — derived from private analysis note `../u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.
- The driver-load step in boot-time setup — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The C-runtime string-length utility used at some call sites for label width — derived from `u5-decomp/functions/ULTIMA_EXE/`. This utility is the standard NUL-terminated string length function and does not warrant a dedicated spec section.
- Cross-overlay call-frequency and no-thunk text-output architecture — derived
  from `u5-decomp/notes/hot_path_analysis.md` and
  `u5-decomp/notes/engine_idioms.md`.
- The proportional-font paragraph renderer used by intro, chargen, and
  Return-to-View text, including the layout descriptor field roles, the
  exclusive right-edge test, the plus-one inter-glyph gap, the backtracking
  break rule, the justification arithmetic, and the fixed nine-pixel line
  advance -- derived from
  `u5-decomp/functions/FONT_OVL/` and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 2.
- The typed-input space eraser and cursor-advance gate preservation -- derived
  from `u5-decomp/functions/ULTIMA_EXE/` and
  cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/`.
- Intro-frame decoration as another cursor-advance gate writer -- derived from
  `u5-decomp/functions/INTRO_OVL/`.
