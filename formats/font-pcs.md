# Proportional Font (`PROPORT.PCS`)

Format specification for Ultima V's proportional character-set file,
`PROPORT.PCS`. This file supplies the proportional font used by the intro
narrative and character-creation text renderer. The on-disk compression and
the runtime font metadata are only partly recovered, so this document separates
confirmed container and consumer behaviour from hypotheses about the decoded
glyph body.

## 1. Overview

`PROPORT.PCS` is a compressed proportional font resource. Unlike the fixed-cell
`.CH` and `.HCS` font files, it is not directly field-walkable from disk: the
file begins with a small compressed-resource envelope, followed by an
entropy-dense payload that must be expanded by the original engine before glyph
metrics and bitmap rows can be used.

The file is loaded during character creation and reused by the paragraph
renderer. Runtime text layout uses per-character widths rather than a fixed
cell advance. This is the key behavioural distinction between `PROPORT.PCS` and
the raw monospace font files.

The exact decompression algorithm and exact post-decompression glyph-body
layout are not yet specified. A compatible implementation should therefore
treat the compressed bytes as an opaque original-engine resource until the
codec and decoded layout have been re-derived from the loader path.

## 2. File Identity

There is one known `.PCS` file in the Ultima V DOS asset set:

| File | Role | On-disk form |
|---|---|---|
| `PROPORT.PCS` | Proportional text font for narrative and character creation | Compressed resource with a small length-prefixed envelope |

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

## 4. Container Layout

The on-disk file belongs to the same compressed-resource family as the
compressed `.BIT` title images. The confirmed outer shape is:

1. A little-endian declared output length stored at the start of the file.
2. A zero word following that length.
3. A compressed payload occupying the rest of the file.

For the shipped `PROPORT.PCS`, the declared decoded size is 1,276 bytes and the
compressed file is 802 bytes. Those values are useful validation anchors, but
they do not by themselves identify the codec.

This is not the GIF-style LZW envelope used by the paired tile graphics
archives (`.16` and `.4`). The tile-graphics family uses a four-byte decoded
length and a known LZW dialect. `PROPORT.PCS` uses a smaller header shape shared
with the compressed `.BIT` family, and its decompressor has not been fully
recovered.

## 5. Decoded Font Model

The decoded data is expected to contain both glyph metrics and glyph bitmap
data. Runtime evidence confirms that the text renderer reads a 128-entry
character-width table from resident state while laying out proportional text.
That table is indexed by the character byte value used by the text stream.

The source of that width table is not yet proven byte-for-byte. The strongest
working interpretation is that loading `PROPORT.PCS` initializes the runtime
font segment and/or resident width table from the decoded resource. However,
the decoded 1,276-byte body has not yet been walked, so this spec does not
assign byte offsets, table ordering, glyph heights, row strides, or bitmap
packing for the decoded font.

Implementations should model the decoded resource at a semantic level:

- A set of up to 128 character slots.
- A width metric for each character slot.
- Monochrome glyph shapes used by the proportional renderer.
- Character advances measured in pixels rather than cells.

Do not assume that glyph bitmap data is a simple fixed-size array. The file is
small enough that variable-width glyph rows, compact row storage, or shared
metadata are all plausible. These details remain open.

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

A byte-compatible loader should enforce only the invariants that are currently
known:

- The file name is `PROPORT.PCS`.
- The file starts with the compressed-resource envelope described above.
- The declared decoded size for the shipped file is 1,276 bytes.
- The compressed input should not be interpreted as glyph rows until the codec
  succeeds.
- Text rendering should reject or substitute any character whose decoded glyph
  metadata is unavailable.

Because the codec is not yet specified, a modern cleanroom implementation has
two practical options:

1. Treat `PROPORT.PCS` as an opaque asset and use an independently authored
   replacement proportional font.
2. Defer support for exact original rendering until the decompressor and
   decoded glyph layout are re-derived.

A tolerant analysis tool may report the declared decoded size and payload
length without decoding. A compatibility-mode loader should fail closed if the
declared size, header shape, or decompression result does not match the
expected resource model.

## 9. Known Uncertainties

- **Compression algorithm.** The codec used by `PROPORT.PCS` has not been
  recovered. It appears related to the compressed `.BIT` resource family, but
  the exact algorithm and bitstream rules are not specified.
- **Decoded body layout.** The decoded file probably contains a width table and
  compact glyph bitmap data, but the ordering and row encoding are not known.
- **Width-table origin.** Runtime layout definitely consults a 128-entry width
  table. Whether that table is copied directly from decoded `PROPORT.PCS`,
  generated by the loader, or partly resident in the executable remains open.
- **Glyph coverage.** Runtime layout indexes widths by 7-bit character values,
  but the exact printable range and handling of control-marker bytes still need
  a decoded font walk.
- **Display-driver split.** Compressed `.BIT` rendering is known to pass through
  the display driver. The `PROPORT.PCS` load path is a font-loader path, and
  its relationship to the driver-side bitmap decompressor is not fully known.

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
- Tile-graphics survey, used only to distinguish the known `.16`/`.4` LZW
  envelope from the separate `.PCS`/compressed-`.BIT` family:
  `u5-decomp/formats/tile-graphics.md`.
- Character-creation loader and `PROPORT.PCS` consumer path:
  `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- Proportional paragraph renderer behaviour and runtime width-table use:
  `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- Intro slide-loop use of the proportional renderer:
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
