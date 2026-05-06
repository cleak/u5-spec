# Standalone Bitmap Files (`.BIT`)

Format specification for Ultima V's standalone `.BIT` image resources. The
extension covers two observed forms: compressed display-independent images used
by the title sequence, and one raw monochrome bitmap used by the introduction.
The compressed codec is not yet fully recovered, so this document specifies the
confirmed container, runtime usage, and validation boundaries without inventing
decompressor details.

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

The compressed files use the same small length-prefixed envelope shape as
`PROPORT.PCS`. `WD.BIT` does not use that envelope and is directly renderable
as a one-bit image after its dimension header.

## 2. Relationship To Tile Graphics

`.BIT` files are separate from the `.16` and `.4` tile-graphics resources:

- `.16` and `.4` files are paired by display depth and use a known GIF-style
  LZW envelope.
- Compressed `.BIT` files are single-source resources rendered through the
  active display driver.
- `.BIT` files do not contain image directories, sprite masks, tile atlases, or
  palette tables.

The distinction matters because a `.BIT` reader cannot reuse the tile-graphics
LZW decoder unless future driver analysis proves the codecs are the same. They
are currently different resource families.

## 3. Compressed `.BIT` Container

`TITLE.BIT` and `BRITISH.BIT` begin with the compressed-resource envelope also
seen on `PROPORT.PCS`:

1. A little-endian declared output length at the start of the file.
2. A zero word following that length.
3. A compressed payload occupying the remaining bytes.

For the shipped files, the declared decoded sizes are:

| File | Compressed size | Declared decoded size |
|---|---:|---:|
| `TITLE.BIT` | 3,323 bytes | 5,364 bytes |
| `BRITISH.BIT` | 784 bytes | 2,116 bytes |

The decoded sizes do not match a full 320-by-200 screen at common direct pixel
depths. Runtime use confirms that these files are drawn into caller-specified
screen rectangles rather than treated as full-screen framebuffers.

The compression algorithm, dictionary model, and bit-packing rules are not yet
known. The only safe implementation-neutral statement is that the original
driver expands the payload to the declared byte count before or while drawing
the requested rectangle.

## 4. Raw `WD.BIT` Container

`WD.BIT` is an observed raw exception within the same extension family. It does
not start with the compressed-resource envelope. Instead, it has a small
four-word header followed by one-bit-per-pixel row data.

The confirmed semantic fields are:

| Field | Meaning |
|---|---|
| First word | Nonzero format or mode marker; exact meaning unresolved |
| Second word | Format, depth, or version marker; exact meaning unresolved |
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

Compressed `.BIT` rendering is performed through the display-driver interface.
The caller loads the bitmap resource, normalizes a destination rectangle to the
320-by-200 screen, and dispatches to the active driver's compressed-bitmap draw
entry. The driver owns both decompression and conversion to its hardware pixel
format.

Confirmed behaviour:

- The caller supplies a screen rectangle, not just a file pointer.
- Rectangles are normalized and clamped to the visible screen before driver
  dispatch.
- `TITLE.BIT` is drawn as a title-screen region, not as a complete raw screen.
- `BRITISH.BIT` participates in the title sequence alongside path-stroke
  animation data.
- The same compressed `.BIT` source files are used regardless of the selected
  display driver.

Because the driver performs the final expansion, the compressed source should
be considered display-independent. An implementation can render a decoded image
to any modern surface, but it should not assume the decoded byte stream is
already EGA planar data, CGA packed pixels, or a complete framebuffer.

`WD.BIT` is simpler: after reading its dimensions, a renderer can draw the
post-header bits as a monochrome bitmap, left-to-right and top-to-bottom.

## 6. Expected Consumers

Known consumers are concentrated in the introduction and title flows:

- The title-screen setup loads and renders `TITLE.BIT`.
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
- The renderer should clip to the caller's normalized destination rectangle.
- A failed or short decode should prevent drawing rather than drawing partial
  garbage.

For raw `WD.BIT`:

- The file must be large enough to contain the four-word header.
- Width and height must be nonzero.
- The payload length must equal the number of bytes needed to store
  `width * height` one-bit pixels rounded up to a whole byte.
- Any trailing bytes should be treated as a format error for strict
  compatibility.

A tolerant inspection tool may report unknown marker words without rejecting
`WD.BIT`, as long as the dimensions and payload budget are exact.

## 8. Implementation Notes

For a cleanroom engine, the practical implementation choices are:

- Use independently authored replacement title artwork and bypass original
  compressed `.BIT` decoding.
- Preserve compressed `.BIT` files as opaque resources until the driver-side
  decompressor is re-derived.
- Implement `WD.BIT` directly as a raw monochrome image, since its dimensions
  and bit order are confirmed.

Do not transpose rules from `.16`/`.4` graphics onto compressed `.BIT` files.
In particular, compressed `.BIT` files have no confirmed sub-image table, no
confirmed mask plane, and no embedded palette.

## 9. Known Uncertainties

- **Compressed codec.** The algorithm used by `TITLE.BIT` and `BRITISH.BIT`
  has not been recovered. Runtime notes locate the draw-time decompression
  inside the loaded display driver.
- **Decoded compressed layout.** The decoded byte stream's internal structure
  is unknown. It may be an intermediate bitmap representation consumed directly
  by the driver, not a portable image header.
- **Source pointer convention.** The resident stub passes a destination
  rectangle to the driver, but the exact runtime slot or calling convention used
  to tell the driver which loaded bitmap segment to read remains unresolved.
- **`WD.BIT` marker words.** Width, height, size, and bit order are confirmed;
  the two leading marker words are not named yet.
- **Per-driver rendering differences.** EGA, CGA, Hercules, and Tandy drivers
  may expand the same compressed source into different native pixel layouts.
  Those differences belong in the display-driver ABI and renderer specs, not in
  this container spec.

## 10. Cross-References

- Tile, sprite, and panel graphics that use `.16`/`.4` rather than `.BIT`:
  `formats/tiles.md`.
- Proportional font resource sharing the compressed-resource envelope:
  `formats/font-pcs.md`.
- Path animation used with `BRITISH.BIT`: `formats/pth.md`.
- Display-driver dispatch behaviour should be described in a future
  display-driver ABI/system spec.

## 11. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It
intentionally omits decompiled code, assembly, raw address tables, binary
dumps, and private implementation identifiers.

- First-pass font and bitmap survey, including compressed `.BIT` envelope,
  shipped file sizes, declared decoded sizes, and raw `WD.BIT` dimensions:
  `u5-decomp/formats/fonts-bitmaps.md`.
- Tile-graphics survey, used to distinguish `.BIT` from the known `.16`/`.4`
  LZW archive family: `u5-decomp/formats/tile-graphics.md`.
- Title-screen loader and runtime title-sequence use of `TITLE.BIT` and
  `BRITISH.BIT`: `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Display-driver compressed-bitmap dispatch behaviour and unresolved
  driver-side decompressor details:
  `u5-decomp/functions/ULTIMA_EXE/0x0AA6_draw_compressed_bitmap.md`.
- Intro slide-loop context for the "Warriors of Destiny" artwork family:
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
