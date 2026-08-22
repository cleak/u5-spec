# Proportional Font (`PROPORT.PCS`)

Format and runtime-use specification for Ultima V's proportional character-set
resource, `PROPORT.PCS`.

## 1. Overview

`PROPORT.PCS` supplies the proportional font used by the intro narrative,
Return-to-View text, and character-creation/questionnaire text. It is not a raw
fixed-cell font like `.CH` or `.HCS`.

It uses exactly the container documented in `formats/bit.md`: the shared LZW
envelope of `formats/lzw.md` wrapping a one-bit-per-pixel sub-image list.
Earlier revisions of this document described a "driver-compressed sparse strip
resource" and told readers not to feed the file to the LZW decoder. That was
wrong in both directions and has been replaced.

The file holds **91** sub-images, one per glyph, covering byte values `0x20`
through `0x7A` in order. Every glyph is 8 rows tall and 0 to 8 pixels wide, so
every glyph row occupies exactly one byte, every glyph record is 12 bytes, and
the offset table has a flat stride of 12. That flat stride holds for the
zero-width space glyph as well: it reserves its eight row bytes like every other
record, which is why `formats/bit.md` Section 3 states the row stride as
`max(1, ceil(width / 8))` rather than `ceil(width / 8)`.

Each glyph record begins with its own width, so the file does carry per-glyph
widths. The paragraph renderer nevertheless measures from a **resident**
128-byte advance window rather than from the file, because that window also
covers codes the font has no glyph for. The two agree byte for byte over
`0x20..0x7A`; Section 4 publishes the resident values.

## 2. File Identity

| File | Role | On-disk form |
|---|---|---|
| `PROPORT.PCS` | Proportional text font for narrative and character creation | LZW envelope wrapping a one-bit-per-pixel sub-image list |

The character-creation overlay loads this file before rendering the gypsy
arrival narrative and questionnaire prompts. The intro slide loop uses the
same paragraph renderer for story text.

## 3. Container

Read the file as follows:

1. Take the first four bytes as the little-endian decoded length and decode the
   remainder with the shared LZW decoder (`formats/lzw.md`). The shipped file is
   802 bytes on disk and declares, and produces, 1276 decoded bytes.
2. Parse the decoded image as the sub-image list of `formats/bit.md` Section 3:
   a 2-byte count, `count` 2-byte offsets, then contiguous sub-images of
   `width`, `height`, and `max(1, ceil(width / 8)) * height` bytes of
   one-bit-per-pixel rows, most-significant-bit leftmost, a set bit meaning ink.
   Because no glyph exceeds eight pixels of width, that stride is one byte per
   row for all 91 records.

For the shipped file that yields `count = 91`, a first offset of 184, and
offsets rising by 12 to 1264; the last record ends exactly at byte 1276. Index 0
is the only record with a width of zero, and it is still 12 bytes: a reader that
sizes it as four bytes will lose alignment for the whole rest of the file.

Glyph index `n` (0-based) corresponds to character code `0x20 + n`, so index 0
is the space and index 90 is lowercase `z`. The renderer selects a glyph by
subtracting `0x20` from the character code, which means codes above `0x7A` have
no glyph and must never reach the glyph draw. Section 5 explains how the
renderer prevents that for the codes shipped text actually uses.

The glyphs carry no colour. Ink colour is caller state.

## 4. Runtime Font Model And The Advance Table

The paragraph renderer is a proportional text layout engine, not a 40-column
cell printer. It uses:

| Component | Owner | Purpose |
|---|---|---|
| Text buffer | Caller | NUL-terminated narrative/question/story text. |
| Font segment | Loaded `PROPORT.PCS` resource | Glyph image source. |
| Advance table | Resident data | 128-byte window indexed by character code. |
| Layout descriptor | Resident | Pixel margins, band bounds, space advance, pen. |

### 4.1 The resident advance table

The table is static resident data, not built at load time. Only the range
`0x20..0x7F` is meaningful: the renderer never looks up a code below `0x21`,
because every byte at or below `0x20` is handled as a space (or as one of the
two terminators), and it only draws codes above `0x20`. The 32 entries below
`0x20` overlap unrelated resident text and must be treated as **unmeasurable**
rather than given values.

Values for `0x20..0x7A` are identical to the per-glyph widths stored in
`PROPORT.PCS`. Values for `0x7B..0x7F` are zero.

| Code | Char | Adv | Code | Char | Adv | Code | Char | Adv | Code | Char | Adv |
|---:|:---|---:|---:|:---|---:|---:|:---|---:|---:|:---|---:|
| `0x20` | space | 0 | `0x38` | `8` | 6 | `0x50` | `P` | 7 | `0x68` | `h` | 5 |
| `0x21` | `!` | 2 | `0x39` | `9` | 6 | `0x51` | `Q` | 6 | `0x69` | `i` | 2 |
| `0x22` | `"` | 6 | `0x3A` | `:` | 2 | `0x52` | `R` | 7 | `0x6A` | `j` | 3 |
| `0x23` | `#` | 7 | `0x3B` | `;` | 3 | `0x53` | `S` | 6 | `0x6B` | `k` | 5 |
| `0x24` | `$` | 7 | `0x3C` | `<` | 5 | `0x54` | `T` | 6 | `0x6C` | `l` | 2 |
| `0x25` | `%` | 7 | `0x3D` | `=` | 5 | `0x55` | `U` | 6 | `0x6D` | `m` | 7 |
| `0x26` | `&` | 7 | `0x3E` | `>` | 5 | `0x56` | `V` | 6 | `0x6E` | `n` | 6 |
| `0x27` | `'` | 3 | `0x3F` | `?` | 6 | `0x57` | `W` | 7 | `0x6F` | `o` | 5 |
| `0x28` | `(` | 4 | `0x40` | `@` | 7 | `0x58` | `X` | 6 | `0x70` | `p` | 5 |
| `0x29` | `)` | 4 | `0x41` | `A` | 7 | `0x59` | `Y` | 6 | `0x71` | `q` | 5 |
| `0x2A` | `*` | 5 | `0x42` | `B` | 6 | `0x5A` | `Z` | 6 | `0x72` | `r` | 4 |
| `0x2B` | `+` | 6 | `0x43` | `C` | 6 | `0x5B` | `[` | 3 | `0x73` | `s` | 4 |
| `0x2C` | `,` | 3 | `0x44` | `D` | 6 | `0x5C` | backslash | 7 | `0x74` | `t` | 4 |
| `0x2D` | `-` | 3 | `0x45` | `E` | 6 | `0x5D` | `]` | 3 | `0x75` | `u` | 5 |
| `0x2E` | `.` | 2 | `0x46` | `F` | 6 | `0x5E` | `^` | 7 | `0x76` | `v` | 5 |
| `0x2F` | `/` | 7 | `0x47` | `G` | 6 | `0x5F` | `_` | 8 | `0x77` | `w` | 7 |
| `0x30` | `0` | 6 | `0x48` | `H` | 6 | `0x60` | backtick | 3 | `0x78` | `x` | 5 |
| `0x31` | `1` | 5 | `0x49` | `I` | 4 | `0x61` | `a` | 5 | `0x79` | `y` | 5 |
| `0x32` | `2` | 6 | `0x4A` | `J` | 7 | `0x62` | `b` | 5 | `0x7A` | `z` | 4 |
| `0x33` | `3` | 6 | `0x4B` | `K` | 7 | `0x63` | `c` | 4 | `0x7B` | `{` | 0 |
| `0x34` | `4` | 6 | `0x4C` | `L` | 6 | `0x64` | `d` | 5 | `0x7C` | vertical bar | 0 |
| `0x35` | `5` | 6 | `0x4D` | `M` | 7 | `0x65` | `e` | 5 | `0x7D` | `}` | 0 |
| `0x36` | `6` | 6 | `0x4E` | `N` | 6 | `0x66` | `f` | 5 | `0x7E` | `~` | 0 |
| `0x37` | `7` | 6 | `0x4F` | `O` | 6 | `0x67` | `g` | 5 | `0x7F` | (unused) | 0 |

Two entries need care:

- **Space (`0x20`) is zero.** The space advance does not come from this table;
  it comes from the layout descriptor (Section 5). The shipped default is 5
  pixels, and character creation temporarily uses 4 for one paragraph.
- **The `{` entry (`0x7B`) is zero**, but the renderer never consults the table
  for it: `{` is intercepted and given a fixed 15-pixel advance.

The `_` entry (`0x5F`) has the value 8, which is also never used: `_` is
intercepted as the soft-hyphen marker and measured as zero. What is used is the
hyphen's own entry (`0x2D`, advance 3), which the renderer reads once per line
for the soft-hyphen fit test and for the hyphen it draws at a hyphenated break.

### 4.2 Unit and spacing rule

Every drawn glyph advances the pen by **its table entry plus one pixel**. The
extra pixel is the inter-glyph gap; it is not baked into the table values and
it is added for every drawn glyph including the last one on a line. A space
advances by the descriptor's space advance with **no** extra pixel, plus any
justification padding (Section 5).

## 5. Layout Behaviour

The full contract for measurement, wrapping, justification, and control-byte
handling is specified in `systems/text-output.md`. In summary, so that this
document is self-contained about what the advance table is for:

1. The layout descriptor supplies two margin pairs and a vertical band; the pen
   Y selects which margin pair applies, giving the line's available width.
2. Measurement accumulates the table entry plus one for each drawn glyph, the
   space advance for spaces, 15 for `{`, and 0 for `_`. A line is accepted only
   while the accumulated advance is strictly less than the available width, so
   the right edge is exclusive.
3. When the line overflows, the renderer backtracks to a space or to a soft
   hyphen that fits and breaks there, consuming exactly one break byte.
4. Interior spaces on a line are padded so the line fills the available width.
   The last line of a paragraph and any line ended by a newline are not padded.
5. The line advance is a fixed 9 pixels of pen Y.

The font file does not define the text rectangle, line stride, page waits, or
keyboard pauses. Those are runtime behaviours in the intro and chargen flows.

## 6. Expected Consumers

Confirmed consumers:

- Character creation: gypsy arrival narrative and questionnaire prompts.
- Questionnaire iteration: one prompt per virtue-pair question.
- Intro slide show: story text over slide artwork.
- Return-to-View and related intro-local text paths that call the shared
  paragraph renderer.

The ordinary status/prompt text path uses fixed-cell fonts and the text-output
system, not `PROPORT.PCS`.

## 7. Validation And Error Handling

A strict loader should:

- Treat the first four bytes as the LZW decoded length, not as a resource entry
  count, and require the decoded byte count to match it.
- Require the decoded image's sub-image count, offset table, and record sizes to
  satisfy the checks in `formats/bit.md` Section 6, taking the row stride as
  `max(1, ceil(width / 8))` so that the zero-width space glyph is sized at 12
  bytes and the flat stride check below agrees with the tiling check there.
- Require the record stride to be a flat 12 bytes for the shipped file.
- Expect 91 records, every one 8 rows tall with a width of 0 to 8, for the
  shipped file. A replacement font may vary the widths but must keep the record
  order aligned to character codes starting at `0x20`.
- Reject a glyph draw whose character code is below `0x21` or above
  `0x20 + count - 1`, unless the caller defines a substitution policy.

There are no sparse entries, no skipped pointers, and no over-allocated table.

## 8. Format Boundary And Remaining Parity Work

The container and the advance table are both fixed at byte depth. Remaining
work is content parity, not decoding.

- **Codes below `0x20`.** Their resident advance entries are unmeasurable, since
  that part of the resident image overlaps unrelated data, and they are
  unreachable through the renderer. Do not invent values for them; a clean
  engine should treat a control byte other than NUL and newline as a space,
  which is what the original does.
- **Codes above `0x7A`.** The advance entries are zero and the font has no
  glyph. Shipped text does not use them apart from the intercepted `{`.
- **Pixel-perfect replacement fonts.** A clean implementation that wants
  byte-identical visuals should decode the shipped records. An independently
  authored replacement font only needs to preserve the advances in Section 4
  and the layout rules in `systems/text-output.md`.

## 9. Cross-References

- Shared container and one-bit-per-pixel sub-image list: `formats/bit.md`.
- Shared compression envelope: `formats/lzw.md`.
- EGA display-driver ABI: `systems/display-driver-abi.md`.
- Paragraph/text behaviour: `systems/text-output.md`, `systems/chargen.md`,
  and `systems/intro.md`.
- Narrative text resources rendered with this font:
  `formats/story-dat.md`, `formats/question-dat.md`, and `formats/end-dat.md`.
- Fixed-cell fonts: `formats/font-ch.md` and `formats/font-hcs.md`.

## 10. Sources

Cleanroom prose derived from private analysis notes. This document intentionally
omits decompiled source, assembly excerpts, raw address tables, and raw glyph
data.

- Container re-decode, advance-table promotion, and the entry-by-entry match
  against the font's own per-glyph widths:
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` sections 1 and 2.
- Proportional paragraph renderer, layout descriptor field roles, and the
  advance/justification rules: the paragraph-renderer note under
  `u5-decomp/functions/FONT_OVL/`.
- Character-creation loader and `PROPORT.PCS` consumer path: the
  character-creation entry note in the same directory, which is also the only
  writer of the space advance.
- Withdrawal of the sparse strip reading:
  `u5-decomp/CORRECTIONS.md` "2026-08-22 corrections (bitmap codec re-decode)".
