# Proportional Font (`PROPORT.PCS`)

Format and runtime-use specification for Ultima V's proportional character-set
resource, `PROPORT.PCS`.

## 1. Overview

`PROPORT.PCS` supplies the proportional font used by the intro narrative,
Return-to-View text, and character-creation/questionnaire text. It is not a
raw fixed-cell font like `.CH` or `.HCS`, and the updated EGA driver pass shows
that it does not use the paired-graphics LZW envelope. It belongs to the same
driver-compressed sparse strip resource family as `TITLE.BIT`, `BRITISH.BIT`,
and `WD.BIT`.

The paragraph renderer receives the loaded `PROPORT.PCS` segment, uses a
resident 128-entry width table for word wrapping, and draws proportional
glyphs through the display/font path. The width table is runtime data, not a
second table embedded in `PROPORT.PCS`.

## 2. File Identity

| File | Role | On-disk form |
|---|---|---|
| `PROPORT.PCS` | Proportional text font for narrative and character creation | Driver-compressed sparse strip resource |

The character-creation overlay loads this file before rendering the gypsy
arrival narrative and questionnaire prompts. The intro slide loop uses the
same paragraph renderer for story text.

## 3. Driver Resource Envelope

`PROPORT.PCS` starts with the same sparse pointer-table envelope described in
`formats/bit.md` and `systems/display-driver-abi.md`:

As with `.BIT`, pre-decoded local packaging variants are outside the canonical
v1 resource contract. A strict original-data validator should treat a
leading-length raw body as noncanonical `PROPORT.PCS` data. Engines may keep
best-effort fallback support for local asset folders, but no exact
variant-detection predicate or alternate body layout is published here.

| Field | Width | Meaning |
|---|---:|---|
| Entry count | 2 bytes | Number of pointer-table entries scanned by the driver/font path. |
| Entries | `entry_count * 4` bytes | Pointer word plus metadata word per entry. |
| Strip/glyph bodies | variable | Driver-consumed records reached through nonzero pointers. |

Zero pointer entries are skipped. Nonzero pointers are byte offsets inside the
loaded resource. The metadata word is not consumed during pointer-table
scanning, but should be preserved by tools that rewrite or round-trip the file.
If a pointer targets a metadata word, the pointed bytes are interpreted as the
start of that body record.

## 4. Runtime Font Model

The paragraph renderer is a proportional text layout engine, not a normal
40-column cell printer. It uses:

| Component | Owner | Purpose |
|---|---|---|
| Text buffer | Caller | NUL-terminated narrative/question/story text. |
| Font segment | Loaded `PROPORT.PCS` resource | Glyph image source. |
| Width table | Resident data | 128 byte widths indexed by character code. |
| Text rectangle | Resident paragraph descriptor | Pixel-space bounds and current cursor. |

For each printable character, the renderer measures and advances by the
character's width-table entry. The glyph image source comes from the loaded
font resource. Spaces are word-wrap opportunities; newline forces a line break;
underscore is a soft-hyphen marker; and `{` is treated as a paragraph/page
marker by the surrounding caller flow.

This separation is load-bearing for tools: the file supplies sparse strip
glyph artwork to the driver path, while glyph advances come from the resident
width table read by the FONT overlay. Do not try to split `PROPORT.PCS` into a
standalone width table followed by per-character glyph records; that was an
early hypothesis superseded by the traced display-driver codec.

## 5. Layout Behaviour

The renderer walks the text stream left-to-right:

1. Track a pixel cursor inside the active paragraph rectangle.
2. Use the width table to measure the current character and look ahead at words
   when handling spaces.
3. If the next word would exceed the right edge, wrap before rendering it.
4. Render printable glyphs from the loaded font segment.
5. Advance the cursor by the measured character width.
6. Move to the next line on newline or a wrap decision.

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

- Treat the first word as a resource entry count, not as an LZW decoded length.
- Require pointer-table entries to fit in the loaded resource image prepared
  for driver/font decoding.
- Skip zero pointers.
- Require nonzero pointers to reference complete driver/font records.
- Preserve pointer-entry metadata even when it is not needed by the EGA
  renderer.
- Reject text-render requests that index outside the supported width table or
  loaded glyph resource, unless the caller defines a substitution policy.

As with `.BIT`, the original resource image can be larger than the byte-exact
file view used by an inspection tool, and known sparse tables may be heavily
over-allocated. Zero pointer entries are compatible no-ops; large entry counts
are not errors by themselves.

## 8. Format Boundary And Remaining Parity Work

The `PROPORT.PCS` resource contract is complete at runtime format depth:
pointer-table scan, strip-body shape, driver ownership, and the separation
between resident glyph widths and file-backed glyph artwork are fixed.
Remaining work is authoring metadata or content parity, not file decoding.

- **Pointer-entry metadata.** As with `.BIT`, the EGA strip decoder does not
  consume the metadata word. Its authoring-tool meaning remains unidentified,
  so tools should preserve it when round-tripping.
- **Codes outside normal narrative text.** The renderer has a 128-entry width
  table, but shipped prose appears to stay within ordinary ASCII plus the
  documented control markers.
- **Pixel-perfect replacement fonts.** A clean implementation that wants
  byte-identical original visuals should decode the sparse strips through the
  same driver-resource rules. Independently authored replacement fonts only
  need to preserve the public width-table advances and paragraph layout
  behaviour.

## 9. Cross-References

- Driver-compressed sparse strip resource family: `formats/bit.md`.
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

- Proportional paragraph renderer and width-table use:
  `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- Character-creation loader and `PROPORT.PCS` consumer path:
  `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- EGA driver sparse strip decoder shared with `.BIT` resources:
  `u5-decomp/functions/EGA_DRV/0x1226_draw_compressed_bitmap.md`.
- EGA driver ABI overview:
  `u5-decomp/formats/ega-driver.md`.
