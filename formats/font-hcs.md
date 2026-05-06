# HCS fonts

Format specification for the `IBM.HCS` and `RUNES.HCS` bitmap fonts. These
files store fixed-cell monochrome glyphs for the same one hundred twenty-eight
character-code slots as the `.CH` font family, but with a larger cell.

## 1. Scope

The `.HCS` files are raw bitmap font assets. They are not compressed, do not
carry a header, and do not contain colour, palette, or display-driver metadata.
Each file is a sequence of same-sized glyph bitmaps indexed directly by
character code.

Two files use this format:

| File | Purpose |
|---|---|
| `IBM.HCS` | Larger Roman/IBM-style text glyphs. |
| `RUNES.HCS` | Larger rune-style glyphs using the same layout and indexing. |

The extension's historical expansion is not documented in the source material.
This spec treats `.HCS` as a high-resolution companion character set because
that matches the observed cell geometry and one-bit bitmap content.

## 2. File Identity

A valid shipped `.HCS` font is exactly three thousand seventy-two bytes long.
That length is the product of one hundred twenty-eight glyphs times
twenty-four bytes per glyph.

There is no magic number, version field, checksum, glyph count, width table, or
terminator. A decoder identifies the format from the filename family and the
exact byte length.

## 3. Glyph Geometry

Each glyph occupies a sixteen-by-twelve pixel cell:

| Property | Value |
|---|---:|
| Glyph count | 128 |
| Cell width | 16 pixels |
| Cell height | 12 pixels |
| Bytes per row | 2 |
| Bytes per glyph | 24 |
| Bits per pixel | 1 |

All glyphs have the same advance width. The file does not support proportional
spacing, kerning, bearings, vertical metrics, or per-glyph dimensions.

The wider cell means an `.HCS` glyph is not byte-compatible with a `.CH` glyph,
but the code-point order is compatible. A renderer can choose between `.CH` and
`.HCS` by changing the glyph-cell metrics and row stride while keeping the same
character-code lookup.

## 4. Glyph Ordering

The file contains glyphs for character codes zero through one hundred
twenty-seven, in numeric order. Glyph number `n` starts at byte `n * 24` and
runs for twenty-four bytes.

The printable ASCII region maps directly to matching glyph positions. The
normal and rune variants use the same indexing; selecting runes is a matter of
loading the rune font rather than remapping character codes.

The format has no storage for high-bit character codes. Values above one
hundred twenty-seven are outside the file-defined range and should be handled by
caller policy.

## 5. Byte and Bit Interpretation

Rows are stored top to bottom. Each row is two bytes wide, giving sixteen bits
for sixteen pixels. Within each byte, bits are interpreted from most
significant to least significant.

For each row:

| Byte | Pixels |
|---|---|
| First row byte | pixels 0 through 7, left to right, bit 7 first |
| Second row byte | pixels 8 through 15, left to right, bit 7 first |

A set bit means foreground. A cleared bit means background. The font file does
not define colour values; the text-output state and display backend supply
foreground and background colour at render time.

The byte stream is row-major inside each glyph and glyph-major across the file:
all twelve rows of glyph zero, followed by all twelve rows of glyph one, and so
on through glyph one hundred twenty-seven.

## 6. Rendering Expectations

A renderer should treat each glyph as a one-bit stencil over a sixteen-by-twelve
cell. Lit pixels draw with the active foreground colour. Unlit pixels are either
transparent or background-coloured according to the higher-level text operation
being performed.

The file carries no style information. Underline, inverse video, centering,
window clipping, scrolling, and cursor advance belong to the text-output system
or display backend. When those systems need to transform a glyph, they should
apply the transformation after fetching the raw `.HCS` bitmap and before
writing pixels to the destination.

Because `.HCS` cells are larger than the forty-by-twenty-five small-text grid's
eight-pixel cell assumption, an engine implementer should treat `.HCS` as a
separate font mode or display path. The format itself does not say which screen
modes, menus, or title/UI paths use it. It only defines the glyph storage.

## 7. Validation and Error Handling

For a strict reader:

- Reject files whose length is not exactly three thousand seventy-two bytes.
- Reject attempts to index glyphs outside the range zero through one hundred
  twenty-seven unless the caller has explicitly requested wrapping or masking.
- Treat all bytes as bitmap data. There are no reserved byte values and no
  embedded metadata to validate.

For a tolerant viewer:

- A short file may be padded with blank rows for inspection, but should not be
  accepted as original-compatible content.
- A long file may be rendered from the first three thousand seventy-two bytes
  for diagnosis, but the extra data is outside this format.

Generated replacement assets should preserve the exact glyph count, cell
dimensions, row order, and bit order if they are intended to be original-
compatible.

## 8. Relationship to Other Formats and Systems

The `.HCS` fonts are companion assets to the `.CH` fonts described in
`formats/font-ch.md`. They share the same glyph count, code-point order, one-bit
pixel interpretation, and normal/rune pairing. They differ only in cell
geometry and row stride.

The `.HCS` files are not tile-graphics containers. They do not use the LZW
envelope, image directories, palettes, or packed colour-pixel encodings
described in `formats/tiles.md`.

The text-output system described in `systems/text-output.md` owns cell
positioning, window state, wrapping, and style flags. A backend that uses
`.HCS` must adapt those higher-level cell concepts to a sixteen-by-twelve
glyph, but no such policy is stored in the font file.

## 9. Open Questions

- The full historical meaning of the `.HCS` extension is not confirmed.
  "High-resolution character set" is a format-level interpretation, not a
  recovered label.
- The exact runtime paths that choose `.HCS` instead of `.CH` remain to be
  specified from the font or display-driver loading logic.
- It is not yet confirmed whether any specific historical hardware driver
  requires `.HCS`, or whether the files are used by higher-resolution UI
  screens independent of hardware.
- The original handling of character codes above one hundred twenty-seven has
  not been pinned down in this spec.

## 10. Sources

This is a cleanroom prose rewrite derived from
`u5-decomp/formats/fonts-bitmaps.md`, cross-checked against
`u5-spec/systems/text-output.md` and `u5-spec/formats/tiles.md`. It omits
decompiled code, assembly, private offsets, raw address tables, and copied
binary dumps.
