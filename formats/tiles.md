# Tile-graphics files

Format specification for the paired tile-graphics archive family — the `*.16` files for sixteen-colour EGA and the `*.4` files for four-colour CGA. The two depths share an identical container layout; only the per-pixel encoding differs. Together they store every tile, sprite, title strip, screen panel, and cutscene frame the engine renders. The set covers the world tile atlas, the inventory and monster sprite sheets, the decorative chapter-heading strips, the dungeon wall billboards, the title and end-game panels, and the multi-page story screens.

## 1. Overview

Ultima V's renderable graphics are partitioned into four functional families — the world tile atlas, the variable-shape sprite sheets, the decorative chapter-heading strips, and the screen-sized panel sets. Each family lives in its own file, but every file in the set ships in two parallel copies: a `.16` for the sixteen-colour EGA card and a `.4` for the four-colour CGA card. The engine picks one of the two at boot based on the active display driver and never mixes the two depths in a single session.

Both depths share an identical outer envelope and an identical container structure. Inside the container, the only difference is the per-pixel encoding: `.16` packs two four-bit pixels per byte (chunky packed, high nibble first), while `.4` packs four two-bit pixels per byte (packed, most-significant bits first). Every container layout, every directory format, every image header, and every padding convention is depth-agnostic; a single decoder can read either depth by switching only the row-stride formula and the per-byte unpacking code.

The full file roster covers the canonical tile atlas (`TILES`), the inventory sprite sheet (`ITEMS`), the eight monster sprite sheets (`MON0` through `MON7`), the dungeon wall billboard sets (`DNG1`, `DNG2`, `DNG3`), the chapter-heading strip set (`TEXT`), the chargen panel set (`CREATE`), the universal banner panels (`ULTIMA`), the intro acknowledgement/credits page (`STARTSC`), the end-of-game cutscene frames (`ENDSC`, `END1`, `END2`), and the six story screens (`STORY1` through `STORY6`). Every file in this list ships as both `.16` and `.4`. There are no other tile-graphics files; the set is exhaustive.

Every file is wrapped in the shared Ultima V LZW envelope. After unwrap, the body is one of three small container layouts — a flat tile array, a directory of variable-shape images, or a directory of variable-shape image-and-mask sprites. The container choice is implicit per file (no tag, no magic number, no version); a reader knows which layout to apply because the file family's role is fixed. Sections 5 and 6 enumerate the layouts; Section 7 lists which files use which layout.

The format carries no embedded palette. The sixteen-entry palette for `.16` is the stock IBM set for the EGA mode with one substitution at index six, and it ships as a table in the resident image rather than inside any driver; the four-entry palette for `.4` is a single IBM CGA hardware palette that the CGA driver hard-codes at mode set time and never revisits. Neither palette is in the asset files, and a reader that wants to render the bytes faithfully must source the palette separately. Section 7 gives both in full.

## 2. The LZW envelope

Every tile-graphics file, regardless of depth or container layout, begins with
the shared LZW envelope specified in `formats/lzw.md`: a four-byte
little-endian unsigned integer giving the *uncompressed* length of the body in
bytes, immediately followed by the LZW-compressed body itself. There is no
magic number, no version word, no flag byte, no checksum, and no envelope
footer. A reader allocates a buffer of exactly the declared size and
decompresses the remaining bytes into it.

`TITLE.BIT`, `BRITISH.BIT`, and `PROPORT.PCS` use this same LZW envelope, but
their decompressed payload is a different container: a one-bit-per-pixel
sub-image list specified in `formats/bit.md` and `formats/font-pcs.md`.
`WD.BIT` carries that same sub-image list with no envelope at all. This
document specifies only the paired `.16`/`.4` graphics archive family that sits
under the envelope.

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

The two-bit-per-pixel encoding constrains the CGA renderer to four colours; on the IBM CGA card this is the canonical mode-four limitation. The four colours are the same for the whole run: the CGA driver selects one fixed palette during mode setup and never issues another palette request (Section 7). The disk format encodes no palette switch of any kind. **Correction:** an earlier revision of this paragraph said different game scenes select different sub-palettes through driver state; that is withdrawn.

The 2:1 byte ratio between the EGA and CGA encodings is exact for every image of the same width and height *except* for sprite-and-mask sub-blocks, where the depth-independent mask plane shifts the ratio (Section 6).

## 5. Container layouts after LZW unwrap

After the LZW envelope is stripped, every file's body is one of three small layouts: a flat tile array, a directory of variable-shape images with thirty-two-bit offsets, or a directory of variable-shape image-and-mask sprite blocks with sixteen-bit offsets. The choice is implicit per file (Section 7 lists which file uses which); a reader cannot determine the layout from the bytes alone, but the partition is stable and well-documented.

### 5.1 Flat tile atlas

The flat atlas is the simplest layout: the body is exactly five hundred twelve back-to-back tiles, each tile sixteen pixels wide by sixteen pixels tall, no header, no directory, no padding between tiles. The first tile occupies bytes zero through tile-stride minus one of the body; the second tile occupies the next tile-stride bytes; and so on through tile five hundred eleven. The tile stride is one hundred twenty-eight bytes for `.16` (Section 3) and sixty-four bytes for `.4` (Section 4).

A decoder enumerates tiles by index by simply multiplying the index by the tile stride. There is no per-tile metadata — no width, no height, no animation flag, no class hint. The renderer applies its own tile-class table (held in the resident data slab) when it needs to know whether a given tile index represents a wall, a floor, a water surface, or a pickup item.

This layout is used by the world tile atlas only. Every other file uses one of the variable-shape directory layouts.

### 5.1.1 Resident miniature tile glyphs — withdrawn

**Withdrawn in full.** Earlier revisions of this section claimed that the
resident engine carries a second, compact per-tile rendering source: a
"miniature" encoding of thirty-two bytes per tile, sixteen rows of two offset
bytes each, expanded by a dedicated resident helper into the small tile glyph
shown in the stats panel and in inventory-style contexts. No such path exists.

The shared data overlay does hold a table of thirty-two-byte records made of
sixteen signed byte pairs, and a resident helper does walk it sixteen pairs at a
time — but the records are indexed by an **animation frame number reduced modulo
sixteen**, not by tile id; the helper writes only the two byte values "lit" and
"clear" into the thirty-two-by-thirty-two local-light mask, never into any pixel
buffer; and it performs no nibble, plane, or bitmap work of any kind. It is the
sixteen-bearing beam stencil of the night-time rotating light beacon specified in
`systems/visibility.md` Section 12.6. The mistaken reading is what put a
"miniature tile-glyph path" into this document and into
`systems/stats-panel.md`; that document withdrew its half of the claim in its
Section 8, where the timed-effect glyph is now specified as an ordinary
fixed-cell font character.

Consequently `TILES.{16,4}` is the **only** tile-shaped graphics source in the
game, and this document specifies it completely. There is no second resident
tile representation to reproduce.

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
| `STORY1`–`STORY6`| Image directory (5.2)        | 3, 4, 2, 2, 2 and 8 panels          | ~28.3–42.0 KB          | ~13.1–20.9 KB         |

The story-file counts are per file and not a range: an earlier revision of this
row gave "3–5 panels per file", which is **withdrawn**. Re-decoding the shipped
directories gives `STORY1` 3, `STORY2` 4, `STORY3` 2, `STORY4` 2, `STORY5` 2 and
`STORY6` 8, in both depth twins. `STORY6`'s eight records are what the intro's
story steps 13 through 20 address as subimages `0..7`
(`systems/intro.md` section 10); a reader that expects at most five records in
that file cannot resolve those steps.

Several roles deserve dedicated commentary.

The **tile atlas** is the heart of the two-dimensional rendering pipeline. Every overworld cell, town/interior cell, combat-arena terrain cell, and active-object sprite resolves to one of these five hundred twelve tiles. First-person dungeon floors are the exception: `DUNGEON.DAT` uses its own packed-nibble cell encoding and the dungeon renderer composites its own billboard and sprite art rather than indexing the world tile atlas for each floor cell. The high-nibble grouping is approximate (walls cluster in one range, floors in another, water in another, doors in another), but the catalogue treats the index as an opaque identifier and looks up animation, walkability, and class flags in a per-tile attribute table held in resident data. The atlas's indices are referenced from the location tile grids (see `formats/location-dat.md`), the surface and underworld chunk tables, combat arenas, and active-object tile bytes.

The **inventory sprites** in `ITEMS` are larger-than-tile artwork shown on the inventory and trade screens. The ten sprites are paired into the standard image-and-mask layout. Sprite dimensions vary — the larger ones are around forty by eighty pixels — and the iconography is rendered at a higher resolution than world tiles to fill the inventory panel.

The **monster sprites** in `MON0` through `MON7` carry three animated monster sprites per file across eight files, for twenty-four sprites total. Each sprite's width is wider than its visible silhouette because animation frames are laid out side-by-side within a single sprite — a four-frame walk cycle of a sixteen-pixel-tall figure is rendered as one sixty-four-pixel-wide image, which the renderer slices into four sixteen-pixel frames at draw time. The exact frame count per sprite varies; the cataloguing of which file holds which monster category is a property of the resident monster table, not of the file format.

The **title strips** in `TEXT` are decorative chapter headings, drawn as artwork and blitted whole. Each of the six records is one word rendered in an ornate blackletter face, at a fixed height of 32 or 33 pixels, and the consumer draws the record as a single opaque image at a caller-supplied origin. They are **not** a bitmap font and are never sliced per character.

| `TEXT` record | Size | Word |
|---:|---|---|
| 0 | 52 x 32 | `The` |
| 1 | 152 x 32 | `Summoning` |
| 2 | 104 x 32 | `Arrival` |
| 3 | 71 x 32 | `Story` |
| 4 | 168 x 33 | `Homecoming` |
| 5 | 96 x 33 | `Dream` |

Callers pair record 0 with one of the others to compose a two-word heading. The intro story sequence uses records 0 through 3 (`systems/intro.md` section 10) and the endgame's narrative windows use records 0, 4 and 5 (`systems/endgame.md` section 8.2).

**Retraction.** Earlier revisions of this section described `TEXT` as "the bitmap font and other glyph artwork ... a row of glyphs laid out side-by-side ... which the renderer slices per-character at draw time", and listed "printable ASCII, runic glyphs, status-bar bitmaps, party-status icons" as candidate per-strip roles. All of that is **withdrawn**. The printable and runic fixed-cell fonts live in the `.CH` character files (`formats/font-ch.md`) and the proportional font in `PROPORT.PCS` (`formats/font-pcs.md`); no font data of any kind is in `TEXT`.

The **dungeon wall billboards** in `DNG1`, `DNG2`, and `DNG3` carry the pre-rendered three-dimensional perspective views the dungeon mode composites onto the player's view. Each file carries twenty-eight slots in a fixed directory, with two slots empty (offset zero) and the rest filled. The three files correspond to the three dungeon presentation flavour bytes, selected on dungeon-mode entry from a three-entry filename table indexed by that byte; the flavour-to-dungeon binding is published in `systems/dungeon-mode.md` section 2. All three directories are byte-identical - same slot count, same empty slots, same per-image dimensions - while every slot's pixel block differs between the three files, so they are pure texture variants over one shared geometry. The slot-to-role mapping is in Section 10.

The **screen panels** in `STARTSC`, `ENDSC`, `END1`, `END2`, `STORY1` through `STORY6`, `ULTIMA`, and `CREATE` carry full-screen or partial-screen artwork for the title and menu screens, the acknowledgement/credits page, the end-game sequence, the story screens, and the character-creation screen. Note the split inside the title sequence: `ULTIMA` holds the start/menu banner and its animated bands, while `STARTSC` holds only the acknowledgement page and its two ornamental pillars and is used by no other path (`systems/intro.md` sections 3 and 11.1). These are the files whose decompressed sizes can rival or exceed the tile atlas itself, because each panel is a single large bitmap rather than a packed atlas of small tiles.

The three title-and-menu panel files have been decoded record by record, and
their inventories are published here because the intro contract depends on
exactly which record is which:

| File | Record | Size (`.16`) | Role |
|---|---:|---|---|
| `ULTIMA` | 0 | 319 x 61 | The `Ultima V` logo banner, drawn at `(0, 0)` on the start/menu screen |
| `ULTIMA` | 1 | 288 x 49 | Burning subtitle band, animation frame `0` |
| `ULTIMA` | 2 | 288 x 49 | Burning subtitle band, animation frame `1` |
| `ULTIMA` | 3 | 288 x 49 | Burning subtitle band, animation frame `2` |
| `ULTIMA` | 4 | 288 x 50 | Burning subtitle band, animation frame `3`; only its first 49 rows are ever displayed |
| `STARTSC` | 0 | 16 x 137 | Left ornamental pillar of the acknowledgement page |
| `STARTSC` | 1 | 288 x 137 | The acknowledgement page itself, with all its credit lines painted into the artwork |
| `STARTSC` | 2 | 16 x 137 | Right ornamental pillar — a mirrored *variant*, not a horizontal flip of record 0 |
| `ENDSC` | 0 | 260 x 168 | Single end-screen parchment panel |

Two depth differences are worth recording. In the `.4` twin of `ULTIMA`, record
4 is `288 x 49` rather than `288 x 50`; the band pitch the consumer uses is a
display-driver constant, not a record height, so the 50-row-pitch backends
simply leave one background row at the bottom of the last staged band. (50 is
the EGA, Tandy and CGA figure; the Hercules driver stages at its own pitch —
see `systems/display-driver.md` section 8.) `STARTSC.4` and
`ENDSC.4` carry the same record shapes as their high-colour twins.

The naming is a trap worth calling out, because it has been got wrong before:
`STARTSC` is **not** the start screen. The start/menu screen is built from
`ULTIMA`; `STARTSC` is used by the acknowledgement path and by nothing else.

## 7. Palette and rendering

The format does not embed a palette. The sixteen-entry `.16` palette is a table of sixteen attribute-controller palette values that ships inside the resident screen descriptor, at a fixed offset from the descriptor pointer (`systems/display-driver-mode.md` section 5). The EGA and Tandy drivers hand that table to the BIOS "set all palette registers" call during mode setup and never touch it again; nothing colour-related is baked into a driver image. Fifteen of the sixteen entries are the stock IBM values for that mode — index zero black, index one dark blue, index two dark green, and so on up to index fifteen bright white. The one deviation is index six: the shipped table selects **dark yellow** where the stock mode table selects **brown**. That single substitution is the only way the game's palette differs from the hardware default, and a reader that renders index six as brown will get the game's dark-yellow tones wrong.

The four-entry `.4` palette is one of the IBM CGA hardware palettes, and the CGA driver fixes the choice once, during mode setup: it requests the four-colour 320-by-200 mode, selects palette **one** (black, cyan, magenta, white), and sets the background/border to black at low intensity. That selection is never revisited. The driver issues no further palette request anywhere, and it programs no palette hardware directly, so **the active `.4` palette does not vary by scene, by map, or by any runtime state.** An earlier revision of this paragraph said the palette could change per scene through driver state; that is withdrawn. The format does not encode the choice on disk either — every `.4` file ships its tile bytes in the same encoding, and the same four colours are active whenever any of them is rendered.

The fact that no palette is embedded means a reader extracting the bytes to a portable image format must source the palette from outside the file: the sixteen `.16` entries from the resident screen descriptor's palette table, and the four `.4` entries from the fixed CGA selection above. A reader targeting visual fidelity should take the stock sixteen-colour set for the mode and then apply the index-six substitution described above, rather than assuming an unmodified hardware default.

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
- The text-output pipeline — `systems/text-output.md`. Note that it does **not** consume this file family for glyphs: the fixed-cell fonts are the `.CH`/`.HCS` character files and the proportional font is `PROPORT.PCS`. The `TEXT` records are whole-image chapter headings and are never sliced per character (Section 6).
- The dungeon mode that composites the wall billboards from `DNG1`/`DNG2`/`DNG3` — `systems/dungeon-mode.md`.
- The chargen sequence that displays the panels in `CREATE` — `systems/chargen.md`.
- The intro and end-game sequences that display panels from `STARTSC`, `ENDSC`, `END1`, `END2`, `STORY1`–`STORY6`, `ULTIMA` — `systems/intro.md` and `systems/endgame.md`.

## 10. Format Boundaries And Remaining Catalog Work

The file-format contract is complete at structural depth: LZW envelope,
directory layouts, image and mask sub-block headers, depth-dependent row
strides, sprite-mask polarity, and byte-budget checks are verified. Every
container's expected size matches the declared LZW length exactly, including
the sprite-and-mask family's deviation from the 2:1 inter-depth ratio.

Remaining work is catalog, renderer, or historical-hardware parity rather than
archive decoding:

- **Per-screen palette overrides.** *Closed — there are none.* An earlier
  revision of this bullet said the CGA palette "is set by driver state at
  mode-switch time and may differ between scenes", and asked which scenes carry
  which palette. That is withdrawn. Both palettes are loaded exactly once, inside
  the mode-set entry, and no entry in any of the four drivers and no path in the
  resident image or any overlay issues a further palette request or writes
  palette hardware directly (`systems/display-driver-mode.md` Section 5.2). The
  CGA selection is fixed and is named in Section 7. Apparent recolouring in the
  shipped presentation is always either a draw performed under a restricted plane
  write mask or a mutation of the loaded asset bytes, never a palette change. A
  reader can therefore render every `.4` file against one four-colour set and
  every `.16` file against one sixteen-entry set.

- **Per-strip roles in `TEXT`.** Closed. The six records are whole-image chapter headings, not glyph strips; their sizes, words and consumers are published in Section 6. There is nothing to slice and no font data in this file.

- **Per-slot mapping in `DNG1`/`DNG2`/`DNG3`.** *Closed.* The twenty-eight slots are seven families of four, one image per depth band, addressed as `slot = family_base + band`:

  | Slot | Role |
  |---|---|
  | 0-3 | Side wall |
  | 4-7 | Side door |
  | 8-11 | Forward wall |
  | 12-15 | Forward door |
  | 16-19 | Side opening |
  | 20-23 | Side flavour wall |
  | 24-27 | Forward flavour wall |

  The two empty slots are 8 and 24, the band-0 entries of the forward wall and forward flavour wall families: at point-blank range the renderer substitutes slot 12 for every blocker class, so nothing ever requests them. The same table with per-band widths, the visual signature of each family, and the class-to-family selection rule are in `systems/dungeon-mode.md` sections 6.2 and 6.4; the placement rule is in section 6.3 and the file-to-flavour assignment in section 6.2.

- **`MON0`–`MON7` monster category mapping.** Each of the eight files carries three sprites; which file holds which monster category (animals, undead, demons, dragons, and so on) is a property of the resident monster table, not of the file format. A content tool that wants to extract a named monster's sprites must consult the monster table.

- **`ITEMS` slot-to-item-id mapping.** The ten sprites in `ITEMS` correspond to inventory items, but the slot-index-to-item-id mapping is a property of the inventory-rendering overlay, not of the file format.

- **Animation frame layout within a sprite.** Monster and item sprites lay multiple animation frames side-by-side inside a single image. The frame count and per-frame width are not part of the on-disk header — they are encoded by the engine's per-sprite slicing convention. A reader extracting individual frames must consult the resident sprite-attribute table.

- **`STORY1` compression ratio outlier.** The compression ratio for `STORY1` is approximately 2.16 versus the cluster of 2.00 to 2.05 across the other story files. The deviation is small enough to attribute to dictionary luck on the specific bitmap content, but a comparison against an independent LZW encoder could confirm.

## 11. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of every tile, sprite, font, and screen-panel file in both depths, the LZW envelope identification and verification, the three container layouts, the sprite-and-mask budget arithmetic, and the cross-file size and ratio audits — `u5-decomp/formats/tile-graphics.md`.
- The resident LZW bit-reader and loader wrapper notes that confirm the
  variable-width code stream contract -
  `u5-decomp/functions/ULTIMA_EXE/0x135A_buffered_stream_read.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x82DE_load_lzw_image.md`.
- Fresh local sprite-mask verification over `ITEMS` and `MON0` through `MON7`
  in both `.16` and `.4` forms confirmed matching image/mask dimensions and
  the "set bit = transparent" polarity.
- The display drivers' byte-by-byte unpacking of the chunky packed (EGA) and packed two-bit (CGA) row data into hardware framebuffer form — `u5-decomp/code-inventory.md` (the `EGA.DRV`, `CGA.DRV`, `HERC.DRV`, and `TANDY.DRV` driver entries).
- The `TEXT` record roles, sizes and words, decoded from the shipped archive with this document's own container rules and cross-checked against their consumers in `u5-decomp/notes/presentation_endgame_chargen_u4_2026-08-22.md`.
- The world tile attribute table held in the resident data slab — referenced by the location tile grids' decoded tile indices — `u5-decomp/formats/data-ovl.md`.
- The withdrawal of the "resident miniature tile-glyph rendering path" of
  Section 5.1.1: the routine that reading rested on is the night-time light
  beacon's stencil stamp, re-read from the shipped executable for this revision
  and written up in `u5-decomp/functions/ULTIMA_EXE/0x7040_light_beacon_stamp.md`
  and `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`. The stale
  reading survives as `u5-decomp/functions/ULTIMA_EXE/0x7040_render_2x16_sprite.md`
  and in a `u5-decomp/CORRECTIONS.md` entry; both are superseded.
- Per-record inventories and roles for `ULTIMA`, `STARTSC` and `ENDSC`, the depth difference in `ULTIMA`'s last record, and the `STARTSC`-is-not-the-start-screen correction — `u5-decomp/notes/intro_title_sequence_2026-08-22.md`, with every record shape re-decoded from the shipped files before publication.
- The active-object table whose per-slot tile byte indexes the world tile atlas — `u5-spec/systems/active-objects.md`.
- The location tile grids' per-cell tile byte that indexes the world tile atlas — `u5-spec/formats/location-dat.md`.
