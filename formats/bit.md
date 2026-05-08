# Standalone Bitmap Files (`.BIT`)

Format specification for Ultima V's standalone `.BIT` image resources. The
extension covers LZW-compressed display-independent images used by the title
sequence and one raw monochrome bitmap used by the introduction.

## 1. Overview

`.BIT` files are standalone images rather than members of the paired
tile-graphics archive family. They are not shipped as parallel `.16` and `.4`
assets. Instead, the original engine loads one `.BIT` file and lets the active
display driver render it appropriately for EGA, CGA, Hercules, or Tandy output.

Three `.BIT` files are currently identified:

| File | Role | Observed form |
|---|---|---|
| `TITLE.BIT` | Main title-screen artwork region | Compressed resource |
| `BRITISH.BIT` | Lord British title-sequence portrait/signature artwork | Compressed resource |
| `WD.BIT` | "Warriors of Destiny" introduction lettering | Raw monochrome bitmap |

The compressed files use the same LZW resource envelope as `PROPORT.PCS` and
the paired graphics archives. `WD.BIT` does not use that envelope and is
directly renderable as a one-bit image after its dimension header.

## 2. Relationship To Tile Graphics

`.BIT` files are separate from the `.16` and `.4` tile-graphics resources:

- `.16` and `.4` files are paired by display depth and use the shared Ultima V
  LZW envelope.
- Compressed `.BIT` files are single-source resources rendered through the
  active display driver.
- `.BIT` files do not contain image directories, sprite masks, tile atlases, or
  palette tables.

The distinction is in the decoded image body, not the compression layer. A
reader can reuse the LZW decoder specified in `formats/tiles.md`, then interpret
the decoded `.BIT` body according to the layouts below.

## 3. Compressed `.BIT` Container

`TITLE.BIT` and `BRITISH.BIT` begin with the shared LZW resource envelope:

1. A four-byte little-endian decoded length.
2. A variable-width LZW payload using the dialect specified in
   `formats/tiles.md`.

For the shipped files, the declared decoded sizes are:

| File | Compressed size | Declared decoded size |
|---|---:|---:|
| `TITLE.BIT` | 3,323 bytes | 5,364 bytes |
| `BRITISH.BIT` | 784 bytes | 2,116 bytes |

The high word of the decoded length is zero for both shipped files, so the
first four bytes look like a length word followed by a zero word. Treating them
as one 32-bit decoded length keeps this family consistent with the other LZW
resources.

### 3.1 `TITLE.BIT` decoded body

After LZW expansion, `TITLE.BIT` is a directory of ten one-bit bitmap blocks:

| Field | Width | Meaning |
|---|---:|---|
| Block count | 2 bytes | Little-endian count. The shipped value is 10. |
| Offset table | 2 x count bytes | Little-endian offsets from the start of the decoded body. |
| Bitmap blocks | variable | Each block begins with width and height words, followed by packed one-bit pixels. |

Each bitmap block has this layout:

| Field | Width | Meaning |
|---|---:|---|
| Width | 2 bytes | Width in pixels. All shipped `TITLE.BIT` widths are multiples of eight. |
| Height | 2 bytes | Height in pixels. |
| Pixel bits | `width * height / 8` bytes | Row-major, most-significant-bit first within each byte. |

The shipped block dimensions are:

| Slot | Width | Height |
|---:|---:|---:|
| 0 | 24 | 3 |
| 1 | 40 | 7 |
| 2 | 72 | 11 |
| 3 | 112 | 20 |
| 4 | 152 | 32 |
| 5 | 216 | 45 |
| 6 | 280 | 61 |
| 7 | 104 | 33 |
| 8 | 16 | 15 |
| 9 | 112 | 33 |

The directory stores shapes, not final screen positions. The shipped DOS intro
uses fixed title-screen coordinates for all ten blocks; those coordinates are
part of the intro renderer contract rather than fields in this file. See
`systems/intro.md` for the placement sequence.

### 3.2 `BRITISH.BIT` decoded body

After LZW expansion, `BRITISH.BIT` is one raw one-bit bitmap using the same
four-word header shape as `WD.BIT`:

| Field | Meaning |
|---|---|
| Format marker | Little-endian word. The shipped value is `1`. |
| Bitmap-mode marker | Little-endian word. The shipped value is `4`. |
| Width | Image width in pixels. The shipped value is 272. |
| Height | Image height in pixels. The shipped value is 62. |

The post-header payload is exactly `width * height / 8` bytes, row-major and
most-significant-bit first within each byte. The first two words match the raw
`WD.BIT` header. Their higher-level driver-facing names are not yet proven, but
they are fixed header constants for the single-image one-bit bitmap form in the
analyzed DOS assets.

## 4. Raw `WD.BIT` Container

`WD.BIT` is an observed raw exception within the same extension family. It does
not start with the compressed-resource envelope. Instead, it has a small
four-word header followed by one-bit-per-pixel row data.

The confirmed semantic fields are:

| Field | Meaning |
|---|---|
| Format marker | Little-endian word. The shipped value is `1` |
| Bitmap-mode marker | Little-endian word. The shipped value is `4` |
| Width | Image width in pixels |
| Height | Image height in pixels |

The shipped `WD.BIT` dimensions are 288 pixels wide by 49 pixels high. After
the header, the payload is exactly large enough for one bit per pixel. Bits are
stored most-significant-bit first within each byte, in row-major order. Rendering
the payload with those dimensions produces the expected "Warriors of Destiny"
lettering.

The raw form has no palette. It should be treated as monochrome artwork whose
foreground and background colours are supplied by the active display mode or
caller.

## 5. Rendering Behaviour

Compressed `.BIT` loading first expands the LZW envelope into the decoded body
described above. Rendering then passes through the display-driver interface:
the caller normalizes a destination rectangle to the 320-by-200 screen and
dispatches into the active display path. The driver or modern renderer converts
the decoded one-bit artwork to the active display representation and clips it to
the requested rectangle.

Confirmed behaviour:

- The caller supplies a screen rectangle, not just a file pointer.
- Rectangles are normalized and clamped to the visible screen before driver
  dispatch.
- `TITLE.BIT` is drawn as ten positioned one-bit blocks, not as a complete raw
  screen.
- `BRITISH.BIT` is drawn as one positioned one-bit bitmap and participates in
  the title sequence alongside path-stroke animation data.
- The same compressed `.BIT` source files are used regardless of the selected
  display driver.

Because the same source files are used regardless of selected display hardware,
the decoded one-bit artwork should be considered display-independent. An
implementation can render it to any modern surface, but it should not assume the
decoded byte stream is already EGA planar data, CGA packed pixels, or a complete
framebuffer.

`WD.BIT` is simpler: after reading its dimensions, a renderer can draw the
post-header bits as a monochrome bitmap, left-to-right and top-to-bottom.

## 6. Expected Consumers

Known consumers are concentrated in the introduction and title flows:

- The title-screen setup loads `TITLE.BIT` and consumes all ten decoded blocks.
- The same title sequence loads and renders `BRITISH.BIT` before or during the
  Lord British path animation.
- The intro slide sequence references the "Warriors of Destiny" artwork family;
  `WD.BIT` is the raw monochrome form identified in the asset survey.

Other overlays may use the same display-driver compressed-bitmap dispatch for
non-`.BIT` resources. That does not make those resources `.BIT` files; this spec
is limited to files with the `.BIT` extension.

## 7. Validation And Error Handling

A `.BIT` loader should first classify the file by envelope:

- If the file starts with the compressed-resource envelope, treat it as a
  compressed `.BIT` and require the decoded output to match the declared
  length.
- If it does not, attempt the raw bitmap interpretation only for files whose
  header dimensions and payload length agree.

For compressed `.BIT` files:

- The declared decoded length must be plausible for the requested resource.
- The decompressor must stop exactly at the declared decoded length.
- `TITLE.BIT` must contain a valid block count, a complete offset table, and
  blocks whose payload lengths equal `width * height / 8`.
- `BRITISH.BIT` must contain the four-word raw-bitmap header and a payload
  length equal to `width * height / 8`.
- The renderer should clip to the caller's normalized destination rectangle.
- A failed or short decode should prevent drawing rather than drawing partial
  garbage.

For raw `WD.BIT`:

- The file must be large enough to contain the four-word header.
- The first two words should match the known single-image `.BIT` header
  constants `1` and `4` for strict compatibility.
- Width and height must be nonzero.
- The payload length must equal the number of bytes needed to store
  `width * height` one-bit pixels rounded up to a whole byte.
- Any trailing bytes should be treated as a format error for strict
  compatibility.

A tolerant inspection tool may report nonstandard marker words without rejecting
an otherwise exact raw bitmap, as long as the dimensions and payload budget are
exact.

## 8. Implementation Notes

A cleanroom engine can use the same LZW decoder for `.16`, `.4`, `.PCS`, and
compressed `.BIT` resources, then switch on the decoded body type:

- `TITLE.BIT`: block directory of one-bit images.
- `BRITISH.BIT`: one raw one-bit image with a four-word header.
- `WD.BIT`: one raw one-bit image with a four-word header and no LZW envelope.

Do not transpose the `.16`/`.4` post-LZW containers onto `.BIT` files.
Compressed `.BIT` files have no colour pixel packing, no sprite mask plane, and
no embedded palette.

## 9. Known Uncertainties

- **Title/menu timing.** `TITLE.BIT` block placement and the intro title tick
  cadence are specified in `systems/intro.md`. This container format does not
  encode waits, palette fades, or menu animation timing.
- **Source pointer convention.** The resident image path passes a destination
  rectangle to the driver, but the exact original runtime slot or driver-facing
  convention used to tell the driver which loaded bitmap segment to read remains
  an implementation-detail question.
- **Single-image marker-word names.** `BRITISH.BIT` and `WD.BIT` both use
  leading words `1` and `4`; the exact driver-facing names for those constants
  are not yet proven.
- **Per-driver rendering differences.** EGA, CGA, Hercules, and Tandy drivers
  may convert the same decoded one-bit artwork into different native pixel
  layouts. Those differences belong in the display-driver ABI and renderer
  specs, not in this container spec.

## 10. Cross-References

- Tile, sprite, and panel graphics that use `.16`/`.4` rather than `.BIT`:
  `formats/tiles.md`.
- Proportional font resource sharing the compressed-resource envelope:
  `formats/font-pcs.md`.
- Path animation used with `BRITISH.BIT`: `formats/pth.md`.
- Display-driver dispatch and rendering behaviour: `systems/display-driver.md`.

## 11. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It
intentionally omits decompiled code, assembly, raw address tables, binary
dumps, and private implementation identifiers.

- First-pass font and bitmap survey, including compressed `.BIT` envelope,
  shipped file sizes, declared decoded sizes, and raw `WD.BIT` dimensions:
  `u5-decomp/formats/fonts-bitmaps.md`.
- Tile-graphics survey, used for the shared LZW dialect and to distinguish the
  `.BIT` post-LZW body layouts from the `.16`/`.4` archive containers:
  `u5-decomp/formats/tile-graphics.md`.
- Title-screen loader and runtime title-sequence use of `TITLE.BIT` and
  `BRITISH.BIT`: `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Display-driver bitmap dispatch behaviour:
  `u5-decomp/functions/ULTIMA_EXE/0x0AA6_draw_compressed_bitmap.md`.
- Intro slide-loop context for the "Warriors of Destiny" artwork family:
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- Fresh local loader-path verification decoded `TITLE.BIT` and `BRITISH.BIT`
  with the shared LZW dialect and field-walked the decoded one-bit bitmap
  containers; no disassembly or raw bitmap bytes are reproduced here.
- Fresh local title-sequence verification identified the fixed screen
  placements for all ten `TITLE.BIT` blocks and the decoded `BRITISH.BIT`
  bitmap; those placements are recorded in `systems/intro.md`.
- Fresh local header verification compared the decoded `BRITISH.BIT` body with
  raw `WD.BIT` and confirmed both single-image bitmap headers start with the
  marker words `1` and `4`.
