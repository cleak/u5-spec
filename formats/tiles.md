# Tile-graphics files

Format specification for the paired tile-graphics archive family — the `*.16` files for sixteen-colour EGA and the `*.4` files for four-colour CGA. The two depths share an identical container layout; only the per-pixel encoding differs. Together they store every tile, sprite, title strip, screen panel, and cutscene frame the engine renders. The set covers the world tile atlas, the dungeon object and monster sprite sheets, the decorative chapter-heading strips, the dungeon wall billboards, the title and end-game panels, and the multi-page story screens.

## 1. Overview

Ultima V's renderable graphics are partitioned into four functional families — the world tile atlas, the variable-shape sprite sheets, the decorative chapter-heading strips, and the screen-sized panel sets. Each family lives in its own file, but every file in the set ships in two parallel copies: a `.16` for the sixteen-colour EGA card and a `.4` for the four-colour CGA card. The engine picks one of the two at boot based on the active display driver and never mixes the two depths in a single session.

Both depths share an identical outer envelope and an identical container structure. Inside the container, the only difference is the per-pixel encoding: `.16` packs two four-bit pixels per byte (chunky packed, high nibble first), while `.4` packs four two-bit pixels per byte (packed, most-significant bits first). Every container layout, every directory format, every image header, and every padding convention is depth-agnostic; a single decoder can read either depth by switching only the row-stride formula and the per-byte unpacking code.

The full file roster covers the canonical tile atlas (`TILES`), the dungeon object sprite sheet (`ITEMS`), the eight dungeon monster sprite sheets (`MON0` through `MON7`), the dungeon wall billboard sets (`DNG1`, `DNG2`, `DNG3`), the chapter-heading strip set (`TEXT`), the chargen panel set (`CREATE`), the universal banner panels (`ULTIMA`), the intro acknowledgement/credits page (`STARTSC`), the end-of-game cutscene frames (`ENDSC`, `END1`, `END2`), and the six story screens (`STORY1` through `STORY6`). Every file in this list ships as both `.16` and `.4`. There are no other tile-graphics files; the set is exhaustive.

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

#### The beam stencil table itself

The table is now published, so an implementation can anchor to it rather than
rediscover it. It lives in the shared data overlay at file offset `0x1F8E` and
is **512 bytes**: sixteen consecutive 32-byte records, each sixteen signed byte
pairs `(dx, dy)`, `dx` east-positive and `dy` south-positive. Live pairs are
contiguous from the start of a record; every remaining pair is exactly `(0, 0)`
and means "no cell". No component exceeds seven in magnitude, and no record
repeats a pair.

Record *r* carries the heading `(r - 1) x 22.5` degrees clockwise from north, so
record 1 is north, 5 is east, 9 is south, 13 is west, and record 0 holds bearing
sixteen — which is what "indexed modulo sixteen" means in practice.

Cell counts follow the heading class exactly: the four **cardinals** (records 1,
5, 9, 13) light **fifteen** cells, the four **diagonals** (3, 7, 11, 15) light
**eleven**, and the eight **halfway** bearings light **nine**.

| Record | Heading | Cells | Offsets `(dx, dy)` |
|---|---|---|---|
| 0 | NNW | 9 | `(-1,-2) (-1,-3) (-2,-3) (-2,-4) (-2,-5) (-2,-6) (-2,-7) (-3,-5) (-3,-6)` |
| 1 | N | 15 | `(0,-1)..(0,-7)`, `(-1,-4)..(-1,-7)`, `(1,-4)..(1,-7)` |
| 2 | NNE | 9 | `(1,-2) (1,-3) (2,-3) (2,-4) (2,-5) (2,-6) (2,-7) (3,-5) (3,-6)` |
| 3 | NE | 11 | `(1,-1) (2,-2) (3,-3) (3,-4) (4,-3) (4,-4) (4,-5) (4,-6) (5,-4) (5,-5) (6,-4)` |
| 4 | ENE | 9 | `(2,-1) (3,-1) (3,-2) (4,-2) (5,-2) (5,-3) (6,-2) (6,-3) (7,-2)` |
| 5 | E | 15 | `(1,0)..(7,0)`, `(4,-1)..(7,-1)`, `(4,1)..(7,1)` |
| 6 | ESE | 9 | `(2,1) (3,1) (3,2) (4,2) (5,2) (5,3) (6,2) (6,3) (7,2)` |
| 7 | SE | 11 | `(1,1) (2,2) (3,3) (4,3) (4,4) (4,5) (5,4) (5,5) (6,4) (3,4) (4,6)` |
| 8 | SSE | 9 | `(1,2) (1,3) (2,3) (2,4) (2,5) (2,6) (2,7) (3,5) (3,6)` |
| 9 | S | 15 | `(0,1)..(0,7)`, `(1,4)..(1,7)`, `(-1,4)..(-1,7)` |
| 10 | SSW | 9 | `(-1,2) (-1,3) (-2,3) (-2,4) (-2,5) (-2,6) (-2,7) (-3,5) (-3,6)` |
| 11 | SW | 11 | `(-1,1) (-2,2) (-3,3) (-3,4) (-4,3) (-4,4) (-4,5) (-4,6) (-5,4) (-5,5) (-6,4)` |
| 12 | WSW | 9 | `(-2,1) (-3,1) (-3,2) (-4,2) (-5,2) (-6,2) (-7,2) (-5,3) (-6,3)` |
| 13 | W | 15 | `(-1,0)..(-7,0)`, `(-4,1)..(-7,1)`, `(-4,-1)..(-7,-1)` |
| 14 | WNW | 9 | `(-2,-1) (-3,-1) (-3,-2) (-4,-2) (-5,-2) (-6,-2) (-7,-2) (-5,-3) (-6,-3)` |
| 15 | NW | 11 | `(-1,-1) (-2,-2) (-3,-3) (-3,-4) (-4,-3) (-4,-4) (-4,-5) (-4,-6) (-5,-4) (-5,-5) (-6,-4)` |

Two notes for an implementation. The stamp always runs **all sixteen iterations**
of a record - there is no early exit on the `(0, 0)` padding, so a padded pair
writes at the record's own origin cell, which is harmless because that cell is
the source. And the table has exactly **one** reader in the whole shipped code
base, the stamp routine itself, so nothing else depends on its layout.

**Locating it structurally is unnecessary but safe.** Searching the shipped
overlay for a 512-byte region matching the structural rules above - sixteen
records, contiguous live pairs then exact `(0, 0)` padding, every component
within seven - yields **exactly one** candidate, and it is this table. That has
been reproduced independently twice. An implementation that prefers a search to
a fixed offset will therefore find the right table, but it should fail loudly on
zero candidates rather than silently lighting nothing.

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

The sprite-sheet files use a similar layout but with sixteen-bit offsets and two
directory entries per sprite: an *image* entry and a *mask* entry. The leading
count word is the number of sprites, not the number of offsets. The image entry
uses the same header-and-rows layout as Section 5.2; the mask entry uses the same
width-and-height header followed by a one-bit-per-pixel transparency plane.

The header is:

| Field             | Width   | Meaning                                                                                                |
|-------------------|---------|--------------------------------------------------------------------------------------------------------|
| Sprite count      | 2 bytes | Little-endian unsigned word; number of paired sprites.                                                 |
| Offset table      | 4 × *n* bytes | Two little-endian unsigned words per sprite, giving body-relative image and mask offsets.        |

Offset ordering alternates: entries zero, two, four, and so on point to image
sub-blocks; entries one, three, five, and so on point to mask sub-blocks. A
sprite at index *k* has its image offset at entry `2k` and its mask offset at
entry `2k + 1`. The first image therefore begins at body offset
`2 + sprite_count * 4`.

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

The sixteen-bit offset table sets a hard ceiling of sixty-five thousand five hundred thirty-five bytes for the body; every sprite-sheet file fits comfortably under this limit (the largest sprite sheet is around ten thousand bytes uncompressed). The offset-entry count is always even by construction, but the stored count word is the sprite count itself.

The five-bits-per-pixel (`.16` plus mask) and three-bits-per-pixel (`.4` plus mask) totals explain why the `.16` and `.4` sprite-sheet sizes are not in 2:1 ratio: the depth-dependent image plane scales 2:1, but the depth-independent mask plane does not. The observed ratio across the sprite-sheet family is approximately five over three (about 1.67), matching the predicted ratio.

## 6. File roster and roles

The full set of tile-graphics files, with their container layouts, sub-image counts, and approximate uncompressed sizes:

| File             | Layout                       | Sub-images / sprites                | Approximate `.16` body | Approximate `.4` body |
|------------------|------------------------------|-------------------------------------|------------------------|-----------------------|
| `TILES`          | Flat atlas (5.1)             | 512 fixed-size 16×16 tiles          | 65,536 bytes           | 32,768 bytes          |
| `ITEMS`          | Sprite-and-mask (5.3)        | 20 sprites (40 offsets)             | ~10.4 KB               | ~6.4 KB               |
| `MON0`–`MON7`    | Sprite-and-mask (5.3)        | 6 sprites per file (12 offsets)     | ~2.6 KB per file       | ~1.6 KB per file      |
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

The **dungeon object sprites** in `ITEMS` are twenty masked half-billboards used
by the first-person dungeon renderer. They form five consecutive four-record
families, one record per depth band: ladder, fountain, pit, closed chest, and
open chest. The complete dimensions and class-to-family mapping are specified
in `systems/dungeon-mode.md` Section 6.6. The filename does not establish an
inventory-screen role, and this traced consumer does not use it as an inventory
item-id sheet.

The **dungeon monster sprites** in `MON0` through `MON7` carry six masked
sprites per file. They are two poses of the same monster family, with three
visible depth records per pose; they are not frame strips sliced side-by-side.
Pose 0 occupies records 0 through 2 and pose 1 records 3 through 5. Within each
pose the dimensions are 24 x 66, 16 x 25, and 8 x 6. The resource-to-monster
mapping and runtime pose rules are specified in `systems/dungeon-mode.md`
Section 6.9.

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

### 6.1 Frame groups in the atlas that the animator never advances

The atlas is authored with many contiguous runs of two or four frames, and a
reader is strongly tempted to treat "four adjacent frames of the same subject"
as proof of an animated family. It is not proof, in either direction, and both
mistakes have been made here.

- **A four-frame authoring run does not imply animation.** `0xE8..0xEB` is four
  coherent frames of one hourglass — sand fully in the upper bulb, two
  intermediate levels, then sand fully in the lower bulb, a clean drain loop in
  the cyclic order `0xE9`, `0xEA`, `0xEB`, `0xE8`. **No animator advances any of
  them.** The tile-animation selector table has five windows and this is not one
  of them (`systems/animation.md` Section 6), and the driver-side pass does not
  touch it either. A map cell holding an hourglass id draws that exact frame for
  the whole program run.
- **Placing only the base id does not imply staticness.** The shipped maps place
  only `0xE8`, in exactly two grids — one castle-interior upper floor and the
  Blackthorn throne-room cutscene tableau — and that looked like corroboration.
  It is not: the standard of Britannia `0xEC..0xEF` is likewise placed exactly
  once and only as its base id, and the animator does advance it.

**What consumes the other three hourglass frames.** They are used as discrete
narrative states rather than as a cycle, by the Blackthorn throne-room
interrogation. That cutscene's fixed eleven-by-eleven map ships with the
`0x80..0x83` family's base member and, two cells below it in the same column,
the hourglass in its spent frame `0xE8`. During the four-question challenge:

| Wrong answer | Hourglass cell becomes |
|---|---|
| The first wrong answer, whichever question it is | `0xE9`, written by the cutscene script alongside the `0x80` → `0x82` swap in the cell above |
| A later wrong answer at question index 1 | `0xEB` |
| A later wrong answer at question index 2 | `0xE8` |
| A later wrong answer at question index 3 | Nothing is stamped; a companion is executed instead |

The visible sequence for an all-wrong run is therefore `0xE8` → `0xE9` → `0xEB`
→ `0xE8`. **`0xEA` is unreachable.** The index-0 arm would write it, but that arm
is entered only when an earlier answer was already wrong, and at index 0 no
earlier answer exists, so control necessarily takes the first-wrong-answer path.
That the observed sequence skips the third frame of a monotone drain looks like
an off-by-one in the original, but that reading is an inference from the
artwork's frame order and not something the code establishes; the unreachability
itself is established. See `systems/blackthorn.md` Section 6.1.

**Scope of the "nothing else consumes them" negative.** It covers a byte-for-byte
scan of every shipped map, location, cutscene, intro-screen and combat-arena
terrain grid; a search of every shipped file for a four-byte hourglass
frame-sequence table in any rotation or reversal; and an exhaustive per-byte
instruction decode of the resident executable, all code overlays and both the
EGA and CGA drivers for every comparison or move with an immediate in
`0xE8..0xEB`, with each hit classified from its surroundings. It does **not**
cover a tile write whose value comes from a data table that was not enumerated,
and the compressed graphics archives were deliberately excluded because their
bytes are compression codes.

**A namespace hazard that will otherwise mislead every reader of this range.**
Two different id spaces use these byte values. *Map and terrain* bytes index the
atlas directly, so `0xE8..0xEB` there is the four hourglass frames. *Active-object
marker* bytes — the live-object table, and the placement-metadata band of
combat-arena records — index the atlas offset by one sprite bank, so the same
byte values there are the four **combat field-effect tiles**, second-bank ids
`0x1E8..0x1EB`. **Refer to these four by id, not by label.** They carry two
roles at once, and the two roles have produced two different naming habits:
authored as drawable combat field effects, they are named in `systems/animation.md`
Section 12.4 as `0x1E8` a poison field, `0x1E9` a sleep field, and `0x1EA` and
`0x1EB` each a force field, while a "poison, sleep, fire, energy" labelling of the
same four ids has also circulated in this document. This specification does not
resolve which of the two labels for `0x1EA`/`0x1EB` matches the shipped
description table, so nothing here should be keyed off the name. Independently of
the field-effect role, the display driver reuses the same four tiles as its own
randomness store: it refreshes all four with fresh pseudo-random pixel bits on
every animation step and XORs the fire fixtures from `0x1EA` (and the shrine
flame from `0x1EB`) through per-fixture masks — Section 6.2 below and
`systems/animation.md` Section 12.4. A tile being a drawable field effect and a
driver noise source is not a contradiction; it is both. Every routine in the
engine that tests
this range as a family is working in the second space, not the first; seven such
sites exist and each was traced to the writer of the value it tests. Anyone
citing one of those classifiers as evidence about hourglass behaviour gets a
wrong answer. Two related precision points: the town-side test covers the wider
band `0xE8..0xEF`, eight marker values, not four; and the outdoor tile
classifier's polarity is the opposite of the usual assumption — it returns true
for `0x2C..0x2F` and for values at or above `0x80` generally, but **false** for
`0xB4..0xB7`, false for `0xE8..0xEB`, and false for everything below `0x80`.

By contrast the two lookup tables that really are keyed by raw terrain id — the
NPC-pathfinding blocking bitmap and the projectile-passability bitmap — draw no
distinction between the frames of a family at all. All four hourglass ids block
NPC pathfinding and all four pass projectiles, and the same holds for all four
clock and bellows ids.

### 6.2 The loaded atlas is mutated at run time, and a few entries serve the driver as masks

Two facts about `TILES` are invisible from the file but change what a reader may
conclude from it.

**The loaded copy is not the shipped copy.** Once the atlas has been loaded and
prepared for blitting, the display driver rewrites tile pixels inside it on
every animation step: it rotates the water, shoals and lava tiles by one pixel
row, stamps a water frame into three groups of composited tiles, and XORs
pseudo-random noise into every fire fixture through a mask. The full contract is
`systems/animation.md` Section 12. Consequences for anyone working with the
asset:

- A dump of the tile buffer taken from a running game is **not** the shipped
  artwork, and for the fire fixtures the divergence is cumulative and never
  undone — the pristine bytes inside each flame mask are gone after the first
  animation step of the session.
- The archive on disk is nevertheless the authoritative source. Every effect
  above is derived from these shipped bytes; nothing is generated from a second
  asset.
- None of this is a palette effect. The palette is programmed once at mode set
  and never revisited (Section 7 and Section 10).

> **Read every id in this section as an atlas index, never as an actor byte.**
>
> The atlas is five hundred twelve entries and splits in half. Indices
> `0x000..0x0FF` are the **terrain half** — the one-byte values that appear in
> map grids, arena grids and scene records. Indices `0x100..0x1FF` are the
> **actor half** — what a live actor resolves to, reached by adding `0x100` to
> the actor byte stored in an active-object record
> (`catalogs/tile-catalog.md` Section 3.1). Section 6.1 calls the same two
> halves the first and second sprite bank; the terms are interchangeable.
>
> Every bare id in Section 6 is an atlas index in the terrain half unless it is
> written with a leading `0x1`. The same numerals also name actor bytes
> elsewhere in this spec set, and they mean something completely different
> there. The three collisions that have actually misled readers:
>
> | Numeral | As a terrain-half atlas index | As an actor byte (atlas index) |
> |---|---|---|
> | `0xC0..0xC3` | Flame masks for the torch, brazier and spit | Orc, four frames (`0x1C0..0x1C3`) |
> | `0xCC..0xCF` | Flame masks for the fireplace, street lamp, candelabrum and stove | Ettin, four frames (`0x1CC..0x1CF`) |
> | `0xD0..0xD3` | Diagonal wedge tiles, reused as the water composite mask | Headless, four frames (`0x1D0..0x1D3`) |
>
> An engine that conflates the two halves draws monsters as masks and masks as
> monsters. `catalogs/monster-bestiary.md` and `systems/encounters.md` publish
> the right-hand column; this document and `systems/animation.md` publish the
> left.

**A few terrain-half entries are the driver's mask assets.** The driver reads
them as stencils during the animation step of `systems/animation.md`
Section 12:

| Terrain-half ids | Role in the driver |
|---|---|
| `0xC0..0xC3`, `0xCC..0xCF` | Per-fixture flame masks. Each is a small two-value blob sitting exactly over its fixture's flame; the XOR touches only pixels inside it. |
| `0xD0..0xD3` | The four diagonal half-tile wedges used as the water composite's stencil. |
| `0x70..0x7F` | The river composite's stencil. |

Actor-half `0x1E8..0x1EB` are the driver's noise store: all four are
re-randomised on every animation step, and the fire effect XORs from `0x1EA`
for every fixture except the shrine flame, which uses `0x1EB`. Those same four
ids are **also** the drawable combat field-effect tiles of Section 6.1: they
hold both roles at once. Name them by id; see Section 6.1 on the two naming
habits.

**Serving as a mask does not make an id undrawable, and the shipped data says
so twice.** All sixteen of `0x70..0x7F` are ordinary, placeable terrain named
"strange walls" in the shipped description table (they are the
Sceptre-dissolvable barrier family of `catalogs/tile-catalog.md`), and they are
placed as arena terrain in both shipped combat-arena banks. `0xD0..0xD3` are
the same kind of dual-role id: all four appear as arena terrain cells in the
shipped dungeon-room arena bank, and `0xD1` and `0xD2` are placed on both
shipped Ararat pages of the keep location file, where the two complementary
wedges form the prow of the wrecked ship. Independently, the resident view-class
table of `systems/view.md` Section 4 gives `0xD0..0xD3` a real ornament renderer
while giving `0x00`, `0xC0..0xC3` and `0xCC..0xCF` the no-op class. A reader
enumerating drawable tiles must not exclude `0x70..0x7F` or `0xD0..0xD3`.

**A placeholder description record proves nothing about drawability.** The
terrain half's placeholder record is a lone `*` and the actor half's is a lone
`x` — two different strings, one per half. Twenty-three terrain-half ids carry
`*`: `0x00`, `0x59`, `0x89..0x8A`, `0xA0`, `0xA4`, `0xC0..0xC3`, `0xCC..0xD3`,
`0xD8..0xDB` and `0xF8`. Eleven of those twenty-three hold cells in shipped map
or arena data — the telescope `0x59`, the sign and poster ids, the fountain
`0xD8`, and `0xD0..0xD3` — and ten of the twenty-three carry the placeholder
only because a Look handler produces their output instead of the table
(`formats/look2-dat.md` Section 5, `catalogs/tile-catalog.md` Section 3).
Sixteen actor-half ids carry `x`: `0x100`, `0x112..0x116`, `0x11C..0x11D`,
`0x174..0x177` and `0x17C..0x17F`.

**Scope of the placement statements above.** "Placed in shipped map or arena
data" here means a terrain cell in one of eight shipped files: the surface and
underworld world-map files, the four per-class location files, and the two
combat-arena banks — counting, in the arena files, only the eleven visible
terrain columns of each record and not the metadata band
(`formats/cbt.md` Section 3). Nothing else was counted: not dungeon-level cell
data, which uses its own byte encoding (`formats/dungeon-dat.md`), not cutscene
or endgame scene records, and not anything a runtime path writes into a live
grid. Absence from this set is therefore weak evidence on its own — several
plainly drawable ids are absent from it because they are animation frames or are
only ever placed at run time — which is why the mask-only conclusion for
`0xC0..0xC3` and `0xCC..0xCF` rests on their driver role first and this census
second.

*Corrected:* an earlier revision of this subsection declared `0x00`,
`0xC0..0xC3`, `0xCC..0xCF`, `0xD0..0xD3` and `0x100` to be driver-private
entries that are never drawn, on the strength of their all carrying "the shared
placeholder `*`". Three things in that sentence are withdrawn
(`RETRACTIONS.md` R314): `0xD0..0xD3` are drawn, as placed terrain, in shipped
map and arena data; `0x100` does not carry `*` at all, it carries the actor
half's `x`; and the placeholder itself is not evidence of anything, as the
twenty-three-id list above shows. Of the original list only `0xC0..0xC3` and
`0xCC..0xCF` are confirmed mask-only, and that confirmation comes from their
role in the driver and from their absence from every shipped map and arena
terrain cell, not from their description record. `0x00` is neither: no
composite or XOR step in `systems/animation.md` Section 12 uses it as a stencil,
its shipped artwork is a full-colour radial burst rather than a two-value
stencil, and no shipped map or arena cell holds it — what draws it, if anything
does, is not established here.

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
  every `.16` file against one sixteen-entry set. The largest such asset mutation
  — the per-animation-step rewrite of the water, lava, river and fire-fixture
  tiles — is specified in `systems/animation.md` Section 12, and Section 6.2
  above records what it means for anyone dumping the loaded atlas. That negative
  covers the EGA driver by a scan for immediate video-range port addresses and
  BIOS video calls; the CGA, Hercules and Tandy drivers were not examined for
  palette handling at all.

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

- **Dungeon sprite catalog.** *Closed.* `ITEMS` is the twenty-sprite dungeon
  object bank, ordered as five four-band families. Each `MON0` through `MON7`
  file contains two poses times three depths for one named wandering-monster
  family. `systems/dungeon-mode.md` Sections 6.6 and 6.9 publish both mappings
  and the runtime pose selection contract.

- **`STORY1` compression ratio outlier.** The compression ratio for `STORY1` is approximately 2.16 versus the cluster of 2.00 to 2.05 across the other story files. The deviation is small enough to attribute to dictionary luck on the specific bitmap content, but a comparison against an independent LZW encoder could confirm.

## 11. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of every tile, sprite, font, and screen-panel file in both depths, the LZW envelope identification and verification, the three container layouts, the sprite-and-mask budget arithmetic, and the cross-file size and ratio audits — private analysis under `u5-decomp/formats/`.
- The resident LZW bit-reader and loader wrapper notes that confirm the
  variable-width code stream contract -
  `u5-decomp/functions/ULTIMA_EXE/`.
- Fresh local sprite-mask verification over `ITEMS` and `MON0` through `MON7`
  in both `.16` and `.4` forms confirmed matching image/mask dimensions and
  the "set bit = transparent" polarity, as well as the stored sprite counts
  and the two-offsets-per-sprite directory rule.
- The display drivers' byte-by-byte unpacking of the chunky packed (EGA) and packed two-bit (CGA) row data into hardware framebuffer form — private driver analysis under `u5-decomp/formats/` and `u5-decomp/functions/`.
- The `TEXT` record roles, sizes and words, decoded from the shipped archive with this document's own container rules and cross-checked against consumers analyzed under `u5-decomp/notes/`.
- The world tile attribute table held in the resident data slab — referenced by the location tile grids' decoded tile indices — private analysis under `u5-decomp/formats/`.
- The withdrawal of the "resident miniature tile-glyph rendering path" of
  Section 5.1.1: the routine that reading rested on is the night-time light
  beacon's stencil stamp, re-read from the shipped executable for this revision
  and written up under `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/notes/`. The stale private readings are superseded.
- Per-record inventories and roles for `ULTIMA`, `STARTSC` and `ENDSC`, the depth difference in `ULTIMA`'s last record, and the `STARTSC`-is-not-the-start-screen correction — private analysis under `u5-decomp/notes/`, with every record shape re-decoded from the shipped files before publication.
- The active-object table whose per-slot tile byte indexes the world tile atlas — `u5-spec/systems/active-objects.md`.
- The location tile grids' per-cell tile byte that indexes the world tile atlas — `u5-spec/formats/location-dat.md`.
- Section 6.1: the hourglass frame group's staticness, the cutscene consumers of
  its non-base frames and the unreachable arm, the placement census, and the
  marker-space namespace hazard with the seven classifier sites and the two
  raw-terrain bitmaps — cleanroom rewrite of private analysis under
  `u5-decomp/functions/ULTIMA_EXE/` and the Blackthorn overlay analysis under
  `u5-decomp/functions/`, repaired after an adversarial verification pass. The
  frame ordering of the drain loop and the mask and noise artwork of Section 6.2
  were rendered from the decompressed shipped tile file.
- Section 6.2: the run-time mutation of the loaded atlas and the private/drawable
  split of the mask and noise ids — see `u5-spec/systems/animation.md` Section 12
  for the behavioural contract and its own provenance.
