# Proportional Font (`PROPORT.PCS`)

Format specification for Ultima V's proportional character-set file,
`PROPORT.PCS`. This file supplies the proportional font used by the intro
narrative and character-creation text renderer. The on-disk compression and the
decoded glyph table are specified here.

## 1. Overview

`PROPORT.PCS` is a compressed proportional font resource. Unlike the fixed-cell
`.CH` and `.HCS` font files, it is not directly field-walkable from disk: the
file begins with the shared Ultima V LZW resource envelope, followed by a
compressed payload that expands to a compact proportional glyph table.

The file is loaded during character creation and reused by the paragraph
renderer. Runtime text layout uses per-character widths rather than a fixed
cell advance. This is the key behavioural distinction between `PROPORT.PCS` and
the raw monospace font files.

The decoded table covers the printable range from space through lowercase `z`.
Each decoded glyph carries an advance width and eleven one-bit bitmap rows.

## 2. File Identity

There is one known `.PCS` file in the Ultima V DOS asset set:

| File | Role | On-disk form |
|---|---|---|
| `PROPORT.PCS` | Proportional text font for narrative and character creation | LZW-compressed resource |

The resident asset-name table points at `PROPORT.PCS`, and the character
creation overlay loads it before rendering the gypsy-wagon narrative,
questionnaire prompts, and related prose.

## 3. Purpose

The proportional font supports text that needs smoother spacing and more
controlled layout than the normal cell printer can provide. Confirmed runtime
uses include:

- Intro-story narrative text drawn over slide artwork.
- Character-creation narrative paragraphs.
- Character-creation question text.

These paths use a paragraph renderer that measures upcoming text with a
per-character width table and performs word wrapping inside a pixel-space text
rectangle. Ordinary status, prompt, and map text can still use the engine's
fixed-cell text primitives; `PROPORT.PCS` is for the richer paragraph layout
paths.

## 4. LZW Container

`PROPORT.PCS` uses the same resource-compression envelope as the paired
graphics archives and the compressed `.BIT` files:

1. A four-byte little-endian unsigned decoded length.
2. A variable-width LZW payload.

For the shipped file, the decoded length is 1,276 bytes and the compressed file
is 802 bytes. The high word of the decoded length is zero, which is why earlier
surveys described the header as a length word followed by a zero word.

The LZW dialect is the same one specified in `formats/tiles.md`: codes start at
nine bits, use little-endian bit packing, reserve code 256 as clear and 257 as
end, add user dictionary entries starting at 258, grow to twelve bits, and
handle the standard self-reference case. A decoder must expand exactly the
declared number of bytes before the resource body is interpreted.

## 5. Decoded Font Layout

After LZW expansion, the body is a small indexed glyph table:

| Field | Width | Meaning |
|---|---:|---|
| Glyph count | 2 bytes | Little-endian count. The shipped file contains 91 glyphs. |
| Offset table | 2 x count bytes | Little-endian body-relative offsets, one per glyph. |
| Glyph blocks | 12 bytes each | One width byte followed by eleven bitmap-row bytes. |

The shipped decoded body has a 184-byte table header (`2 + 91 * 2`) followed by
91 fixed-size glyph blocks. Every offset points to the start of one 12-byte
block, and the blocks are contiguous.

Glyph slot zero corresponds to character code `0x20` (space). Slot `n`
corresponds to code `0x20 + n`, so the covered range is `0x20..0x7A`
inclusive. Codes outside that range do not have glyph records in this file.

Each glyph block has this layout:

| Field | Width | Meaning |
|---|---:|---|
| Advance width | 1 byte | Pixel advance used by the proportional renderer for this glyph. Observed values fit in 0..7. |
| Bitmap rows | 11 bytes | One byte per row, top to bottom. Bits are most-significant-bit first within each row; a set bit is foreground. |

The bitmap rows are one byte wide even for narrow glyphs. The width byte tells
the renderer how far to advance and how much of the row is visually meaningful;
unused right-side bits are padding. The space glyph is blank and has a zero
width in the resource, so any visible word spacing beyond that is renderer text
layout behaviour, not bitmap content.

## 6. Rendering Behaviour

The paragraph renderer consumes ordinary byte strings with a few text-layout
conventions handled outside the font file:

- Character bytes select proportional glyph slots.
- The renderer advances by the glyph's measured width.
- Spaces are word-wrap opportunities.
- Newline characters force a line break.
- Some narrative text uses marker characters for paragraph or syllable
handling; those are text-stream semantics, not font-file metadata.

The renderer measures ahead at spaces to decide whether the next word fits
within the active text rectangle. It updates a pixel cursor and wraps to the
next line when needed. The line stride and clipping rectangle come from runtime
text-window state, not from `PROPORT.PCS`.

The font file does not define colours. The active display mode and text-render
state choose foreground/background treatment when glyph pixels are drawn.

## 7. Expected Consumers

Confirmed consumers are:

- The character-creation entry path, which loads `PROPORT.PCS` before rendering
  narrative and question text.
- The proportional paragraph renderer in `FONT.OVL`, which receives a font
  segment and uses runtime glyph widths during layout.
- The intro slide loop, which calls the same paragraph renderer for story text
  over slide artwork.

The fixed-width text printer in the resident executable is a separate path and
should not be treated as a `PROPORT.PCS` consumer unless a future trace shows
otherwise.

## 8. Validation And Error Handling

A byte-compatible loader should enforce these invariants:

- The four-byte decoded length must match the number of bytes produced by LZW.
- The shipped `PROPORT.PCS` decoded length is 1,276 bytes.
- The decoded glyph count must be nonzero and the offset table must fit inside
  the decoded body.
- Every glyph offset must point to a complete 12-byte glyph block.
- The shipped file contains exactly 91 glyphs covering `0x20..0x7A`.
- Character codes outside the covered range should be rejected, substituted, or
  handled by caller-specific text control logic rather than indexing past the
  table.

A strict loader should reject short LZW output, overlong output, malformed
offsets, or a glyph block that would run past the decoded body.

## 9. Known Uncertainties

- **Renderer spacing for blanks and markers.** The decoded space glyph has zero
  width. The paragraph renderer may apply additional spacing or control-marker
  handling outside the font file.
- **Runtime width-table copy.** The decoded glyph width byte is the source a
  clean implementation should use. The exact original-memory copy path into the
  renderer's width table is an implementation detail.
- **Codes above lowercase `z`.** The decoded table ends at `0x7A`. Any original
  text stream use of higher printable ASCII would need a caller-side fallback.

## 10. Cross-References

- Fixed-cell font and bitmap survey: `formats/bit.md` and the private source
  notes listed below.
- Narrative text files rendered with the proportional font:
  `formats/story-dat.md`, `formats/question-dat.md`, and `formats/end-dat.md`.
- Intro and character-creation systems are expected to document when the
  renderer is invoked and which text is passed to it.

## 11. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It
intentionally omits decompiled code, assembly, raw address tables, binary
dumps, and private implementation identifiers.

- First-pass font and bitmap survey, including the `PROPORT.PCS` compressed
  envelope, file size, declared decoded size, and comparison with `.BIT`:
  `u5-decomp/formats/fonts-bitmaps.md`.
- Tile-graphics survey, used for the shared LZW envelope and compression
  dialect:
  `u5-decomp/formats/tile-graphics.md`.
- Character-creation loader and `PROPORT.PCS` consumer path:
  `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- Proportional paragraph renderer behaviour and runtime width-table use:
  `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- Intro slide-loop use of the proportional renderer:
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- Fresh local loader-path verification decoded `PROPORT.PCS` with the shared
  LZW dialect and field-walked the 91 decoded glyph records; no disassembly or
  raw glyph bytes are reproduced here.
