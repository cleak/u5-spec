# Tile-graphics files

Format specification for the paired tile-graphics archive family — the `*.16` files for sixteen-colour EGA and the `*.4` files for four-colour CGA. The two depths share an identical container layout; only the per-pixel encoding differs. Together they store every tile, sprite, font strip, screen panel, and cutscene frame the engine renders. The set covers the world tile atlas, the inventory and monster sprite sheets, the font and glyph strips, the dungeon wall billboards, the title and end-game panels, and the multi-page story screens.

## 1. Overview

Ultima V's renderable graphics are partitioned into four functional families — the world tile atlas, the variable-shape sprite sheets, the font and glyph strips, and the screen-sized panel sets. Each family lives in its own file, but every file in the set ships in two parallel copies: a `.16` for the sixteen-colour EGA card and a `.4` for the four-colour CGA card. The engine picks one of the two at boot based on the active display driver and never mixes the two depths in a single session.

Both depths share an identical outer envelope and an identical container structure. Inside the container, the only difference is the per-pixel encoding: `.16` packs two four-bit pixels per byte (chunky packed, high nibble first), while `.4` packs four two-bit pixels per byte (packed, most-significant bits first). Every container layout, every directory format, every image header, and every padding convention is depth-agnostic; a single decoder can read either depth by switching only the row-stride formula and the per-byte unpacking code.

The full file roster covers the canonical tile atlas (`TILES`), the inventory sprite sheet (`ITEMS`), the eight monster sprite sheets (`MON0` through `MON7`), the dungeon wall billboard sets (`DNG1`, `DNG2`, `DNG3`), the font and glyph strip set (`TEXT`), the chargen panel set (`CREATE`), the universal banner panels (`ULTIMA`), the start-of-game and end-of-game cutscene frames (`STARTSC`, `ENDSC`, `END1`, `END2`), and the six story screens (`STORY1` through `STORY6`). Every file in this list ships as both `.16` and `.4`. There are no other tile-graphics files; the set is exhaustive.

Every file is wrapped in the shared Ultima V LZW envelope. After unwrap, the body is one of three small container layouts — a flat tile array, a directory of variable-shape images, or a directory of variable-shape image-and-mask sprites. The container choice is implicit per file (no tag, no magic number, no version); a reader knows which layout to apply because the file family's role is fixed. Sections 5 and 6 enumerate the layouts; Section 7 lists which files use which layout.

The format carries no embedded palette. The sixteen-entry palette for `.16` is the standard IBM EGA hardware palette; the four-entry palette for `.4` is one of the standard IBM CGA hardware palettes selected by the display driver at mode set time. Both palettes are baked into the executable's display driver, not into the asset files, and a reader that wants to render the bytes faithfully must source the palette separately.

## 2. The LZW envelope

Every tile-graphics file, regardless of depth or container layout, begins with a four-byte little-endian unsigned integer giving the *uncompressed* length of the body in bytes, immediately followed by the LZW-compressed body itself. There is no magic number, no version word, no flag byte, no checksum, and no envelope footer. A reader allocates a buffer of exactly the declared size and decompresses the remaining bytes into it.

The same outer LZW envelope is also used by `PROPORT.PCS` and by the compressed
`.BIT` resources. Those files have different post-LZW body layouts, specified
in `formats/font-pcs.md` and `formats/bit.md`; this document specifies the
post-LZW layouts for the paired graphics archive family only.

The LZW dialect is the GIF variant, byte-for-byte identical to the dialect used by the Compuserve GIF87a image format that was contemporary with the game's release. Codes start at nine bits wide and grow by one bit each time the dictionary fills, capping at twelve bits. Bit packing is little-endian: the first emitted code occupies the low nine bits of the first compressed byte, and subsequent codes pack into adjacent bit positions, crossing byte boundaries freely. The dictionary holds up to four thousand ninety-six entries.

Two reserved code values flank the dictionary. Code one hundred twenty-eight in hexadecimal (decimal two hundred fifty-six) is the *clear code*: when emitted, it resets the dictionary to its initial nine-bit state and the next emitted code is the first user entry. Code one hundred twenty-nine in hexadecimal (decimal two hundred fifty-seven) is the *end code*: when emitted, the decompressor stops and returns its accumulated buffer. The first user dictionary entry sits at code one hundred thirty in hexadecimal (decimal two hundred fifty-eight); user entries fill upward as the encoder discovers new substrings.

The decompressor is the textbook GIF variant — clear-on-fill is supported, the KwKwK self-reference case is handled, and the output buffer's length is known from the four-byte header so the decompressor can sanity-check completion. Every file in the set decompresses to exactly the declared length; mismatched lengths are a content error and have not been observed in shipped data.

The 2:1 byte ratio between the two depths' uncompressed bodies follows directly from the per-pixel encoding (Section 3 versus Section 4): every pixel takes four bits in `.16` and two bits in `.4`, so a `.16` body is twice the size of a `.4` body for any image of the same width and height. Sprite-and-mask containers (Section 6) deviate from this ratio — they carry a depth-independent one-bit mask plane in addition to the depth-dependent image plane, which compresses the ratio from 2.0 to roughly five over three. This deviation is the easiest disk-side signal that a file uses the sprite-and-mask container.

## 3. EGA pixel encoding (`.16`)

The `.16` files store pixel data as *chunky packed nibbles*. Each byte holds two pixels: the high nibble is the first pixel, the low nibble is the second pixel. The four-bit nibble value is the pixel's index into the sixteen-entry EGA palette. There is no plane interleaving, no plane reassembly, and no run-length or delta encoding above the LZW envelope. A decoder unpacks each byte into two pixels by extracting the high four bits, then masking the low four bits.

A row of *w* pixels packs into `(w + 1) / 2` pixel bytes, then pads up to a multiple of four bytes — the row stride is `((w + 7) / 8) * 4` bytes. The padding bytes are zero on disk and contribute no rendered pixels. The per-row padding is a property of the directory-resident sub-images (Sections 5 and 6); the flat tile atlas (Section 5.1) needs no padding because every tile is a multiple of four bytes wide on its own.

A sixteen-by-sixteen tile costs sixteen rows times sixteen pixels divided by two pixels per byte, equals one hundred twenty-eight bytes total. A flat atlas of five hundred twelve such tiles costs five hundred twelve times one hundred twenty-eight, equals sixty-five thousand five hundred thirty-six bytes uncompressed — exactly what the EGA tile atlas decompresses to (Section 7).

Within a row, the pixel order is left-to-right: the leftmost pixel sits in the high nibble of the first byte, the second pixel in the low nibble of the first byte, the third pixel in the high nibble of the second byte, and so on. This is consistent with the EGA hardware's mode-thirteen-hexadecimal byte ordering, except that the EGA hardware actually drives the screen through four-plane mode-zero-D-hexadecimal at three hundred twenty by two hundred — the chunky-packed disk format is decompressed and re-laid-out by the EGA driver into the hardware's planar form before scanout. The disk format is *not* the hardware's native form; it is a lower-overhead packed form that the driver expands.

## 4. CGA pixel encoding (`.4`)

The `.4` files store pixel data as *packed two-bit values, four pixels per byte, most-significant bits first*. The leftmost pixel sits in bits seven and six of the first byte; the second pixel in bits five and four; the third in bits three and two; the fourth in bits one and zero. The two-bit value is the pixel's index into the four-entry CGA palette set by the display driver — typically one of the standard CGA mode-four palettes (palette zero or palette one, in either intensity).

A row of *w* pixels packs into `(w + 3) / 4` bytes. There is no row stride padding for the CGA depth; the row width is exactly the packed-byte count. A sixteen-by-sixteen tile costs sixteen rows times four bytes per row, equals sixty-four bytes — exactly half the EGA cost. A flat atlas of five hundred twelve such tiles costs five hundred twelve times sixty-four, equals thirty-two thousand seven hundred sixty-eight bytes uncompressed.

The two-bit-per-pixel encoding constrains the CGA renderer to four colours per scene; on the IBM CGA card this is the canonical mode-four limitation. Different game scenes select different sub-palettes through driver state — the disk format does not encode a per-scene palette switch.

The 2:1 byte ratio between the EGA and CGA encodings is exact for every image of the same width and height *except* for sprite-and-mask sub-blocks, where the depth-independent mask plane shifts the ratio (Section 6).

## 5. Container layouts after LZW unwrap

After the LZW envelope is stripped, every file's body is one of three small layouts: a flat tile array, a directory of variable-shape images with thirty-two-bit offsets, or a directory of variable-shape image-and-mask sprite blocks with sixteen-bit offsets. The choice is implicit per file (Section 7 lists which file uses which); a reader cannot determine the layout from the bytes alone, but the partition is stable and well-documented.

### 5.1 Flat tile atlas

The flat atlas is the simplest layout: the body is exactly five hundred twelve back-to-back tiles, each tile sixteen pixels wide by sixteen pixels tall, no header, no directory, no padding between tiles. The first tile occupies bytes zero through tile-stride minus one of the body; the second tile occupies the next tile-stride bytes; and so on through tile five hundred eleven. The tile stride is one hundred twenty-eight bytes for `.16` (Section 3) and sixty-four bytes for `.4` (Section 4).

A decoder enumerates tiles by index by simply multiplying the index by the tile stride. There is no per-tile metadata — no width, no height, no animation flag, no class hint. The renderer applies its own tile-class table (held in the resident data slab) when it needs to know whether a given tile index represents a wall, a floor, an animated water surface, or a pickup item.

This layout is used by the world tile atlas only. Every other file uses one of the variable-shape directory layouts.

### 5.2 Directory of variable-shape images, thirty-two-bit offsets

The screen-panel and font-strip files use a small two-pass layout: a count word, an array of body-relative offsets, and a sequence of variable-shape image blocks at the listed offsets. The header is:

| Field             | Width   | Meaning                                                                                                |
|-------------------|---------|--------------------------------------------------------------------------------------------------------|
| Sub-image count   | 2 bytes | Little-endian unsigned word; number of slot entries that follow.                                       |
| Offset table      | 4 × *n* bytes | Little-endian unsigned doublewords; one per slot, giving the body-relative offset of each image. |

The offset for a given slot is measured from the start of the decompressed body (the byte immediately after the four-byte LZW length header is *not* part of the body — the body begins at offset zero of the unwrapped buffer). Slots may carry an offset of zero, which the engine treats as "empty slot, skip" — only the dungeon wall billboard files (`DNG1`, `DNG2`, `DNG3`) ship with empty slots. The remaining offsets point into the body's image region, which begins immediately after the offset table.

Each image block at the listed offset begins with its own four-byte header followed by the raw pixel rows:

| Field        | Width   | Meaning                                                                       |
|--------------|---------|-------------------------------------------------------------------------------|
| Width        | 2 bytes | Little-endian unsigned word; image width in pixels.                           |
| Height       | 2 bytes | Little-endian unsigned word; image height in pixels.                          |
| Pixel rows   | bytes   | `height` rows of `bytes_per_row` bytes each, packed left-to-right per Section 3 or 4. |

The rows are stored top-to-bottom, with no inter-row separator and no per-row padding beyond the depth-dependent stride formula. For `.16` the row stride is `((w + 7) / 8) * 4` bytes; for `.4` it is `(w + 3) / 4` bytes. The total pixel-data size for an image is `height × bytes_per_row` bytes.

Two facts make this layout robust against forward-compatibility: the offset table is the source of truth for where each image lives, so a future author could reorder images on disk without breaking the format; and the per-image width and height are stored in the image's own header rather than in the directory, so a reader does not need a separate side-table to interpret the offsets.

### 5.3 Directory of variable-shape sprite-and-mask blocks, sixteen-bit offsets

The sprite-sheet files use a similar layout but with sixteen-bit offsets and twice as many slots — every sprite occupies two consecutive slots, an *image* slot and a *mask* slot. The image slot uses the same header-and-rows layout as Section 5.2; the mask slot uses the same width-and-height header followed by a one-bit-per-pixel transparency plane.

The header is:

| Field             | Width   | Meaning                                                                                                |
|-------------------|---------|--------------------------------------------------------------------------------------------------------|
| Slot count        | 2 bytes | Little-endian unsigned word; equals two times the sprite count.                                        |
| Offset table      | 2 × *n* bytes | Little-endian unsigned words; one per slot, giving the body-relative offset of each sub-block.   |

Slot ordering alternates: even-indexed slots (zero, two, four, ...) point to image sub-blocks; odd-indexed slots (one, three, five, ...) point to mask sub-blocks. A given sprite at sprite-index *k* has its image at slot `2k` and its mask at slot `2k + 1`. Sprite-zero is at slots zero and one; sprite-one is at slots two and three; and so on.

The image sub-block follows the Section 5.2 image format — width word, height word, raw pixel rows in chunky packed (`.16`) or two-bit packed (`.4`) form. The mask sub-block follows the same width-and-height header but its pixel rows are one bit per pixel:

| Field        | Width   | Meaning                                                                                                  |
|--------------|---------|----------------------------------------------------------------------------------------------------------|
| Width        | 2 bytes | Little-endian unsigned word; should match the paired image's width.                                      |
| Height       | 2 bytes | Little-endian unsigned word; should match the paired image's height.                                     |
| Mask bits    | bytes   | `(width × height + 7) / 8` bytes of one-bit-per-pixel transparency data, most-significant bit first, no per-row padding. |

The mask is row-major, packed as a flat run of bits across the width times height pixel grid with no per-row stride. A set bit means "this pixel is transparent — do not draw the corresponding image pixel"; a cleared bit means "draw the image pixel". Implementations use the mask to composite sprites onto background tiles without requiring a designated colour-key value in the image plane.

Local asset sanity over `ITEMS` and `MON0` through `MON7` in both `.16` and
`.4` forms confirms the polarity: paired image and mask dimensions match for
every shipped sprite slot, and set mask bits correspond to transparent image
regions rather than visible silhouette pixels.

The sixteen-bit offset table sets a hard ceiling of sixty-five thousand five hundred thirty-five bytes for the body; every sprite-sheet file fits comfortably under this limit (the largest sprite sheet is around ten thousand bytes uncompressed). Slot count is always even by construction — the count word equals twice the sprite count.

The five-bits-per-pixel (`.16` plus mask) and three-bits-per-pixel (`.4` plus mask) totals explain why the `.16` and `.4` sprite-sheet sizes are not in 2:1 ratio: the depth-dependent image plane scales 2:1, but the depth-independent mask plane does not. The observed ratio across the sprite-sheet family is approximately five over three (about 1.67), matching the predicted ratio.

## 6. File roster and roles

The full set of tile-graphics files, with their container layouts, sub-image counts, and approximate uncompressed sizes:

| File             | Layout                       | Sub-images / sprites                | Approximate `.16` body | Approximate `.4` body |
|------------------|------------------------------|-------------------------------------|------------------------|-----------------------|
| `TILES`          | Flat atlas (5.1)             | 512 fixed-size 16×16 tiles          | 65,536 bytes           | 32,768 bytes          |
| `ITEMS`          | Sprite-and-mask (5.3)        | 10 sprites in 20 slots              | ~10.4 KB               | ~6.4 KB               |
| `MON0`–`MON7`    | Sprite-and-mask (5.3)        | 3 sprites per file in 6 slots       | ~2.6 KB per file       | ~1.6 KB per file      |
| `TEXT`           | Image directory (5.2)        | 6 strips                            | ~10.5 KB               | ~5.3 KB               |
| `CREATE`         | Image directory (5.2)        | 11 chargen panels                   | ~37.5 KB               | ~18.3 KB              |
| `ULTIMA`         | Image directory (5.2)        | 5 panels                            | ~38.2 KB               | ~19.0 KB              |
| `DNG1`/`DNG2`/`DNG3` | Image directory (5.2)    | 28 wall billboards (2 empty slots)  | ~54.7 KB               | ~27.4 KB              |
| `STARTSC`        | Image directory (5.2)        | 3 panels                            | ~21.9 KB               | ~11.0 KB              |
| `ENDSC`          | Image directory (5.2)        | 1 panel                             | ~22.2 KB               | ~10.9 KB              |
| `END1` / `END2`  | Image directory (5.2)        | 3 panels each                       | ~24.7–28.2 KB          | ~12.2–14.1 KB         |
| `STORY1`–`STORY6`| Image directory (5.2)        | 3–5 panels per file                 | ~28.3–42.0 KB          | ~13.1–20.9 KB         |

Several roles deserve dedicated commentary.

The **tile atlas** is the heart of the two-dimensional rendering pipeline. Every overworld cell, town/interior cell, combat-arena terrain cell, and active-object sprite resolves to one of these five hundred twelve tiles. First-person dungeon floors are the exception: `DUNGEON.DAT` uses its own packed-nibble cell encoding and the dungeon renderer draws wireframe wall art rather than indexing the world tile atlas for each floor cell. The high-nibble grouping is approximate (walls cluster in one range, floors in another, water in another, doors in another), but the catalogue treats the index as an opaque identifier and looks up animation, walkability, and class flags in a per-tile attribute table held in resident data. The atlas's indices are referenced from the location tile grids (see `formats/location-dat.md`), the surface and underworld chunk tables, combat arenas, and active-object tile bytes.

The **inventory sprites** in `ITEMS` are larger-than-tile artwork shown on the inventory and trade screens. The ten sprites are paired into the standard image-and-mask layout. Sprite dimensions vary — the larger ones are around forty by eighty pixels — and the iconography is rendered at a higher resolution than world tiles to fill the inventory panel.

The **monster sprites** in `MON0` through `MON7` carry three animated monster sprites per file across eight files, for twenty-four sprites total. Each sprite's width is wider than its visible silhouette because animation frames are laid out side-by-side within a single sprite — a four-frame walk cycle of a sixteen-pixel-tall figure is rendered as one sixty-four-pixel-wide image, which the renderer slices into four sixteen-pixel frames at draw time. The exact frame count per sprite varies; the cataloguing of which file holds which monster category is a property of the resident monster table, not of the file format.

The **font and glyph strips** in `TEXT` carry the bitmap font and other glyph artwork as a small set of large bitmap strips rather than as a per-character grid. A typical strip is a row of glyphs laid out side-by-side at a consistent height, and the renderer slices the strip per-character at draw time. The exact role of each of the six strips — printable ASCII, runic glyphs, status-bar bitmaps, party-status icons — is a property of the text-rendering overlay, not of the file format.

The **dungeon wall billboards** in `DNG1`, `DNG2`, and `DNG3` carry the pre-rendered three-dimensional perspective views the dungeon mode composites onto the player's view. Each file carries twenty-eight slots in a fixed directory, with two slots empty (offset zero) and the rest filled. The three files presumably correspond to three visual styles (above-ground dungeon, underworld, deep dungeon, or similar); the assignment is a property of the dungeon-mode overlay.

The **screen panels** in `STARTSC`, `ENDSC`, `END1`, `END2`, `STORY1` through `STORY6`, `ULTIMA`, and `CREATE` carry full-screen or partial-screen artwork for the title sequence, end-game sequence, story screens, and character-creation screen. These are the files whose decompressed sizes can rival or exceed the tile atlas itself, because each panel is a single large bitmap rather than a packed atlas of small tiles.

## 7. Palette and rendering

The format does not embed a palette. The sixteen-entry `.16` palette is the standard IBM EGA hardware palette — index zero is black, index one is dark blue, index two is dark green, and so on through index fifteen as bright white, with index six set to dark yellow rather than the brown the EGA hardware would otherwise emit (the canonical hardware quirk that distinguishes the EGA palette from the canonical sixteen-colour CGA composite palette). The exact red-green-blue triples are baked into the EGA driver in the executable.

The four-entry `.4` palette is one of the IBM CGA hardware palettes set by the CGA driver at mode-set time. The standard CGA mode-four palettes are palette zero (black, green, red, brown) and palette one (black, cyan, magenta, white), each available in low or high intensity. The active CGA palette can change per-scene through driver state, but the format does not encode the choice on disk — every `.4` file ships its tile bytes in the same encoding regardless of which palette will be active when the file is rendered.

The fact that no palette is embedded means a reader extracting the bytes to a portable image format must source the palette from the executable (technically from the resident data and the CGA or EGA driver). The repository's tile-graphics analysis notes carry the canonical sixteen-entry RGB list for the EGA palette; readers targeting visual fidelity should reuse it rather than re-deriving from the raw VGA register dumps.

The rendering pipeline that consumes the unwrapped pixels is distributed across the mode specs (`systems/overworld.md`, `systems/town-mode.md`, `systems/dungeon-mode.md`, `systems/text-output.md`, and `systems/animation.md`); this format spec restricts itself to the on-disk arrangement.

## 8. Worked example — `TILES.16` container layout

`TILES.16` uses the shared LZW container layout:

- Bytes zero through three: the four-byte little-endian uncompressed length. For a five-hundred-twelve-tile EGA atlas with each tile costing one hundred twenty-eight bytes, the decoded length is sixty-five thousand five hundred thirty-six bytes.
- Bytes four onward: the variable-width LZW codes. The first nine-bit code occupies the low nine bits of byte four and the low bit of byte five; subsequent codes pack into adjacent bit positions, growing to ten bits when the dictionary fills its first one hundred twenty-six user slots, and so on through twelve bits.

A reader processes the file in three stages:

1. Read bytes zero through three as a little-endian unsigned word. Allocate a buffer of exactly that size.
2. Read the remaining bytes, feed them to a GIF-variant LZW decompressor, and write the decompressed output into the allocated buffer until the end-code is observed. Confirm that the decompressed length matches the declared length.
3. Interpret the buffer as exactly five hundred twelve back-to-back one-hundred-twenty-eight-byte tiles. The *k*-th tile starts at byte `k × 128` of the buffer. Within each tile, the sixteen rows of eight bytes each pack two pixels per byte (high nibble first).

A reader sanity-checks the decoded output by:

1. Verifying the decompressed length is exactly sixty-five thousand five hundred thirty-six bytes.
2. Picking a known tile index — say, the first water tile or the first grass tile — and rendering its sixteen-by-sixteen pixel grid against the EGA palette.
3. Confirming the rendered output is recognisably the expected tile artwork.

For `TILES.4`, the procedure is identical except the declared length is thirty-two thousand seven hundred sixty-eight bytes, the per-tile cost is sixty-four bytes, and each row packs four pixels per byte (most-significant bits first). For directory-format files (Section 5.2 and 5.3), the post-LZW body begins with a count word and an offset table rather than a flat tile array.

## 9. Cross-references

- The display and mode systems that consume this format and translate it to visible output — `systems/overworld.md`, `systems/town-mode.md`, `systems/dungeon-mode.md`, `systems/text-output.md`, and `systems/animation.md`.
- The world tile-index-to-attribute catalogue — the per-tile walkability and animation flags consumed by movement and rendering — `catalogs/tile-catalog.md`.
- The location tile grids that index into the world tile atlas — `formats/location-dat.md`.
- The active-object table whose tile bytes index into the world tile atlas — `systems/active-objects.md`.
- The text-output pipeline that renders glyphs by slicing the `TEXT` strips — `systems/text-output.md`.
- The dungeon mode that composites the wall billboards from `DNG1`/`DNG2`/`DNG3` — `systems/dungeon-mode.md`.
- The chargen sequence that displays the panels in `CREATE` — `systems/chargen.md`.
- The intro and end-game sequences that display panels from `STARTSC`, `ENDSC`, `END1`, `END2`, `STORY1`–`STORY6`, `ULTIMA` — `systems/intro.md` and `systems/endgame.md`.

## 10. Open questions

The format is verified at the structural level (LZW envelope, directory layouts, image and mask sub-block headers, depth-dependent row strides) and at the byte-budget level (every container's expected size matches the declared LZW length exactly, including the sprite-and-mask family's deviation from the 2:1 inter-depth ratio). The following points remain open.

- **Per-screen palette overrides.** The CGA palette is set by driver state at mode-switch time and may differ between scenes. Whether any specific scene transition triggers a palette change — and which scenes carry which palette — is a property of the CGA driver and the scene-mode initialisers, not of the file format. A reader that wants to faithfully render the CGA artwork must either source the active palette from the running engine or assume one of the standard CGA mode-four palettes per scene.

- **Per-strip glyph ranges in `TEXT`.** The six strips' widths and heights are known, but the assignment of strips to character sets — printable ASCII, runic glyphs, status-bar bitmaps, party-status icons — is a property of the text-output overlay's slicing logic, not of the file format. A content tool that wants to extract the printable font as a per-character bitmap must read the text-output overlay's slicing parameters.

- **Per-slot mapping in `DNG1`/`DNG2`/`DNG3`.** The twenty-eight directory slots include two empty slots in every file (offset zero). Which slot index corresponds to which wall billboard direction (north-facing wall, side wall, ceiling, floor) and which file represents which dungeon visual style is a property of the dungeon-mode overlay's drawing logic.

- **`MON0`–`MON7` monster category mapping.** Each of the eight files carries three sprites; which file holds which monster category (animals, undead, demons, dragons, and so on) is a property of the resident monster table, not of the file format. A content tool that wants to extract a named monster's sprites must consult the monster table.

- **`ITEMS` slot-to-item-id mapping.** The ten sprites in `ITEMS` correspond to inventory items, but the slot-index-to-item-id mapping is a property of the inventory-rendering overlay, not of the file format.

- **Animation frame layout within a sprite.** Monster and item sprites lay multiple animation frames side-by-side inside a single image. The frame count and per-frame width are not part of the on-disk header — they are encoded by the engine's per-sprite slicing convention. A reader extracting individual frames must consult the resident sprite-attribute table.

- **`STORY1` compression ratio outlier.** The compression ratio for `STORY1` is approximately 2.16 versus the cluster of 2.00 to 2.05 across the other story files. The deviation is small enough to attribute to dictionary luck on the specific bitmap content, but a comparison against an independent LZW encoder could confirm.

## 11. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of every tile, sprite, font, and screen-panel file in both depths, the LZW envelope identification and verification, the three container layouts, the sprite-and-mask budget arithmetic, and the cross-file size and ratio audits — `u5-decomp/formats/tile-graphics.md`.
- Fresh local sprite-mask verification over `ITEMS` and `MON0` through `MON7`
  in both `.16` and `.4` forms confirmed matching image/mask dimensions and
  the "set bit = transparent" polarity.
- The display drivers' byte-by-byte unpacking of the chunky packed (EGA) and packed two-bit (CGA) row data into hardware framebuffer form — `u5-decomp/code-inventory.md` (the `EGA.DRV`, `CGA.DRV`, `HERC.DRV`, and `TANDY.DRV` driver entries).
- The text-output overlay's slicing of the `TEXT` strips into per-character glyphs — `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` and the text-output overlay's per-character draw function.
- The world tile attribute table held in the resident data slab — referenced by the location tile grids' decoded tile indices — `u5-decomp/formats/data-ovl.md`.
- The active-object table whose per-slot tile byte indexes the world tile atlas — `u5-spec/systems/active-objects.md`.
- The location tile grids' per-cell tile byte that indexes the world tile atlas — `u5-spec/formats/location-dat.md`.
