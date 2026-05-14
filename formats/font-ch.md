# CH fonts

Format specification for the `IBM.CH` and `RUNES.CH` bitmap fonts. These files
store fixed-cell monochrome glyphs for the game's small character set.

## 1. Scope

The `.CH` files are raw font assets. They are not compressed, do not carry a
header, and do not contain colour or palette data. Each file is a sequence of
fixed-size glyph bitmaps addressed directly by character code.

Two files use this format:

| File | Purpose |
|---|---|
| `IBM.CH` | Normal Roman/IBM-style text glyphs. |
| `RUNES.CH` | Rune-style glyphs using the same code-point order and cell geometry. |

The file format is identical for both files. The active alphabet is selected by
choosing which file to load, not by changing the byte values passed through the
text pipeline.

## 2. File Identity

A valid shipped `.CH` font is exactly one thousand twenty-four bytes long. That
length is the product of one hundred twenty-eight glyphs times eight bytes per
glyph.

There is no magic number, version field, checksum, glyph count, width table, or
terminator. A decoder identifies the format from the filename family and the
exact byte length.

## 3. Glyph Geometry

Each glyph occupies an eight-by-eight pixel cell:

| Property | Value |
|---|---:|
| Glyph count | 128 |
| Cell width | 8 pixels |
| Cell height | 8 pixels |
| Bytes per row | 1 |
| Bytes per glyph | 8 |
| Bits per pixel | 1 |

All glyphs have the same advance width. The file does not support proportional
spacing, kerning, bearings, vertical metrics, or per-glyph dimensions. A text
renderer should advance by exactly one text cell after drawing a glyph, unless
the higher-level text-output system suppresses the advance for a style or
control-flow reason.

## 4. Glyph Ordering

The file contains glyphs for character codes zero through one hundred
twenty-seven, in numeric order. Glyph number `n` starts at byte `n * 8` and runs
for eight bytes.

The printable ASCII region maps directly to matching glyph positions. For
example, the glyph for exclamation mark is stored in the slot for code
thirty-three, and the glyph for uppercase A is stored in the slot for code
sixty-five. Control-code slots at the start of the file are mostly blank or
non-printing in the shipped data.

The format has no storage for high-bit character codes. The resident text
emitter owns that caller-side policy: ordinary cell output ignores high-bit
bytes unless an adjacent extended-control path has already consumed them. The
file itself defines only the lower seven-bit range.

## 5. Byte and Bit Interpretation

Rows are stored top to bottom. Within each row, bits are interpreted from most
significant to least significant:

| Bit | Pixel |
|---|---|
| 7 | leftmost pixel |
| 6 | second pixel |
| 5 | third pixel |
| 4 | fourth pixel |
| 3 | fifth pixel |
| 2 | sixth pixel |
| 1 | seventh pixel |
| 0 | rightmost pixel |

A set bit means foreground. A cleared bit means background. The font file does
not define the actual colours; the text-output state and display backend supply
foreground and background colour at render time.

The byte stream is row-major inside each glyph and glyph-major across the file:
all eight rows of glyph zero, followed by all eight rows of glyph one, and so
on through glyph one hundred twenty-seven.

## 6. Rendering Expectations

A renderer should treat each glyph as an opaque one-bit stencil. For each lit
bit, draw the current foreground colour. For each unlit bit, either leave the
destination unchanged or draw the current background colour according to the
text-output operation being performed. Window clearing, scrolling, inverse
video, underline, and cursor movement are behaviours of the text system and
display backend, not fields in the `.CH` file.

The public text-output contract describes rendering in forty columns by
twenty-five rows of text cells. The `.CH` cell size explains an eight-pixel-high
small-font path, but the text system itself should remain cell-oriented: it
asks the backend to draw a glyph for a character code at a cell position, while
the backend knows how to interpret the loaded font's bitmap rows.

`IBM.CH` and `RUNES.CH` should be interchangeable at the file-format level. A
tool that can render one can render the other by changing only the source file.
The visual meaning of a code point changes, but the indexing and bit packing do
not.

## 7. Validation and Error Handling

For a strict reader:

- Reject files whose length is not exactly one thousand twenty-four bytes.
- Reject attempts to index glyphs outside the range zero through one hundred
  twenty-seven unless the caller has explicitly requested wrapping or masking.
- Treat all byte values as bitmap data. There are no reserved byte patterns and
  no metadata bytes to validate.

For a tolerant viewer:

- A short file may be padded with blank rows for inspection, but should not be
  accepted as original-compatible content.
- A long file may be rendered from the first one thousand twenty-four bytes for
  diagnosis, but the extra data is outside this format.

Generated assets should preserve the exact geometry and glyph count if they are
intended to be drop-in replacements for the original engine.

## 8. Relationship to Other Formats and Systems

The `.CH` fonts are separate from the compressed tile-graphics files. The
`TEXT` graphics resources described in `formats/tiles.md` are image strips in
the tile-graphics container family; `.CH` is a direct per-code-point bitmap
font with no LZW envelope and no strip slicing.

The `.HCS` font family, described in `formats/font-hcs.md`, carries the same
one hundred twenty-eight code points at a larger fixed cell size. It should be
treated as a companion high-resolution font rather than as a palette or colour
extension to `.CH`.

The text-output system described in `systems/text-output.md` owns wrapping,
window rectangles, style flags, and driver dispatch. This format spec only
defines how to fetch and decode the glyph bitmap once a character code has been
chosen.

## 9. Runtime Boundaries

- The exact runtime rule for selecting `IBM.CH` versus `RUNES.CH` belongs to
  the text or magic/rune display path and is not encoded in the file.
- The relationship between these standalone fonts and any driver-embedded font
  cache is a runtime-loading question, not an on-disk-format question.

## 10. Sources

This is a cleanroom prose rewrite derived from
`u5-decomp/formats/fonts-bitmaps.md`, cross-checked against
`u5-spec/systems/text-output.md` and `u5-spec/formats/tiles.md`. High-bit
caller handling is cross-checked against
`u5-decomp/functions/ULTIMA_EXE/0x16BA_putchar.md`. It omits decompiled code,
assembly, private offsets, raw address tables, and copied binary dumps.
