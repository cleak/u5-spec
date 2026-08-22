# Standalone Bitmap Files (`.BIT`)

Format specification for Ultima V's standalone `.BIT` image resources.

## 1. Overview

A `.BIT` file is a small list of one-bit-per-pixel sub-images. Three of the
four shipped files carry that list inside the same LZW envelope the paired
`.16`/`.4` graphics archives use (`formats/lzw.md`); the fourth stores the list
raw. Nothing in the family is a display-driver "sparse strip" table, and the
leading value is never an entry count for such a table.

Known `.BIT` files:

| File | Role | On-disk form | Sub-images |
|---|---|---|---:|
| `TITLE.BIT` | Title-sequence artwork and lettering | LZW envelope | 10 |
| `BRITISH.BIT` | Lord British signature artwork | LZW envelope | 1 |
| `WD.BIT` | "Warriors of Destiny" story lettering | Raw, no envelope | 1 |

`PROPORT.PCS` uses the identical container with 91 sub-images, one per glyph;
see `formats/font-pcs.md`.

Because the pixels are one bit deep, these files carry no colour of their own.
The ink colour is whatever the caller has selected when the image is drawn.

## 2. Relationship To Other Graphics

Ultima V has two graphics container families, and they share a compression
envelope:

| Family | Files | Envelope | Payload |
|---|---|---|---|
| Paired graphics archives | `TILES.16`, `STARTSC.16`, `STORY1.16`, matching `.4` files, and so on | LZW (`formats/lzw.md`) | Packed four-bits-per-pixel image container (`formats/tiles.md`) |
| Standalone bitmaps and the proportional font | `TITLE.BIT`, `BRITISH.BIT`, `PROPORT.PCS` | LZW (`formats/lzw.md`) | One-bit-per-pixel sub-image list (Section 3) |
| Standalone bitmap, stored raw | `WD.BIT` | none | The same one-bit-per-pixel sub-image list |

### 2.1 Deciding whether a file is enveloped

`WD.BIT` is the only shipped member stored without the envelope, and its first
four bytes read as a 32-bit value happen to be a large number, so
"leading value larger than the file" is **not** a safe test. Use the structural
test instead, which is exact for all four shipped files:

1. Try to parse the file directly as the sub-image list of Section 3, starting
   at byte 0.
2. If the walk stays inside the file and consumes it exactly to the last byte,
   the file is stored raw. This succeeds only for `WD.BIT`.
3. Otherwise treat the first four bytes as the LZW decoded length, decode the
   remainder per `formats/lzw.md`, and parse the decoded image as the sub-image
   list. The decoded byte count must equal the declared length and the code
   stream must end with a proper end code.

For the shipped files the declared decoded lengths are `TITLE.BIT` 5364,
`BRITISH.BIT` 2116 and `PROPORT.PCS` 1276, each recovered exactly.

An implementation that only ever loads the four shipped resources may hard-code
the classification instead; the structural test exists so that a validator can
reject a corrupt or substituted file rather than mis-parsing it.

There is no known "pre-decoded" packaging variant of these files. Earlier
guidance in this document described one; that guidance was mistaken and has
been removed. Copies from a retail install, a re-release install, and a
preservation image all carry the layout described here.

## 3. File Layout

After the envelope is removed (or immediately, for a raw file), the image is a
directory followed by contiguous sub-images:

| Field | Width | Meaning |
|---|---:|---|
| Sub-image count | 2 bytes | Number of sub-images in this resource. |
| Offset table | `count * 2` bytes | For each sub-image, its byte offset measured from the start of the decoded image. |
| Sub-images | remainder | Stored back to back, in offset order. |

Each sub-image is:

| Field | Width | Meaning |
|---|---:|---|
| Width | 2 bytes | Pixel width. |
| Height | 2 bytes | Pixel height, in rows. |
| Rows | `row_stride * height` bytes | One bit per pixel, row-major. |

The row stride is `max(1, ceil(width / 8))` bytes. For every record of non-zero
width that is simply `ceil(width / 8)`. The `max(1, ...)` clause covers the one
shipped record whose width is zero — glyph index 0 of `PROPORT.PCS`, the space —
which still reserves one byte per row, all of it padding. A zero-width record
paints nothing; the reserved bytes exist only to keep that file's record stride
uniform.

Row bits run most-significant-bit first, so bit 7 of the first byte of a row is
that row's leftmost pixel. A set bit is ink; a clear bit leaves the destination
untouched or is painted as background, at the caller's discretion. Each row
starts on a byte boundary, so a width that is not a multiple of eight leaves
padding bits at the end of the row; those padding bits are not pixels.

The first offset in the table always equals `2 + count * 2`, and the last
sub-image ends exactly at the end of the decoded image. Both are useful
integrity checks. So is the stronger invariant that pins the whole reading:
consecutive offsets differ by exactly `4 + max(1, ceil(width / 8)) * height` of
the earlier record — the four header bytes plus its row data, with nothing
between records. A candidate parse that satisfies that relation for every
adjacent pair and consumes the image exactly is the correct one; a parse that
does not is either mis-strided or applied to a file outside this family.

Two consequences worth stating, because a reader that drops the `max(1, ...)`
clause will reject a shipped file:

- Across the three `.BIT` files every width is non-zero, so there the relation
  reduces to `4 + ceil(width / 8) * height` and holds for every adjacent pair.
- In `PROPORT.PCS` every glyph is eight rows tall and at most eight pixels
  wide, so the stride is one byte per row for every record including the
  zero-width space, and the record stride is a flat 12 bytes throughout. A
  validator that computes the space glyph's record as four bytes will read the
  remaining ninety records at the wrong offsets.

## 4. File-Specific Notes

### 4.1 `TITLE.BIT`

`TITLE.BIT` holds ten sub-images with these roles:

| Record | Size | Role |
|---:|---|---|
| 0 | 24 x 3 | Publisher wordmark, zoom frame 1 of 7 |
| 1 | 40 x 7 | Publisher wordmark, zoom frame 2 |
| 2 | 72 x 11 | Publisher wordmark, zoom frame 3 |
| 3 | 112 x 20 | Publisher wordmark, zoom frame 4 |
| 4 | 152 x 32 | Publisher wordmark, zoom frame 5 |
| 5 | 216 x 45 | Publisher wordmark, zoom frame 6 |
| 6 | 280 x 61 | Publisher wordmark at full size, zoom frame 7 |
| 7 | 104 x 33 | The word "Presents", shown under the finished wordmark |
| 8 | 16 x 15 | The single article letter that opens the attribution card |
| 9 | 112 x 33 | The word "Production", closing the attribution card |

Records `0..6` are seven successively larger renderings of the same publisher
wordmark, not seven different marks; they exist to be played as a zoom-in
animation. Records `8` and `9` bracket the `BRITISH.BIT` signature to form the
three-line attribution card described in `systems/intro.md` section 3.

The title sequence still owns the visible flow: clear/configure the title
surface, draw the title resource, draw the Lord British resource and path
animation, then enter the menu/start-screen flow. The file format does not
encode menu timing, input handling, or the title/menu idle animation.

For intro-title compatibility, the resource's decoded records are not a
standalone draw list. `systems/intro.md` names the only title records that
become visible and the order in which they are drawn. In particular, the intro
title helper stamps `TITLE.BIT` records `0..6` into a hidden surface as a
vertical stack and never shows that stack; the driver's animation-script entry
then presents one frame at a time, replacing each with the next, so that the
finished flourish is a single full-size wordmark. Those records are not seven
simultaneous visible layers, and the finished title frame does not contain
seven copies of the wordmark. The later title phase draws only the explicitly
named records `7`, `8`, and `9` around the signature sequence, and it publishes
whole pages between phases, so records `6` and `7` are already gone from the
screen by the time records `8` and `9` are shown. A renderer that draws every
decoded record from this file as a simultaneous sprite layer will produce
spliced duplicate title marks.

### 4.2 `BRITISH.BIT`

`BRITISH.BIT` holds a single 272x62 sub-image: the author's handwritten
signature, forming the middle line of the intro's attribution card. It is drawn
during the title sequence as a caller-selected record, not as an automatic
overlay for every decoded record. In the intro title flow, `BRITISH.PTH`
supplies the animated pen movement first, and `BRITISH.BIT` record `0` is
stamped afterward and published over the whole page, which **replaces** the
live pen strokes rather than layering on top of them. A renderer should not put
`BRITISH.BIT` under the path strokes, and should not leave the strokes visible
underneath it.

### 4.3 `WD.BIT`

`WD.BIT` is the one shipped member stored without the LZW envelope. Parsed
directly it is a one-sub-image resource: count `1`, single offset `4`, then a
288x49 image whose rows occupy 36 bytes each. Header plus offset table plus
`36 * 49` accounts for the whole file exactly.

Earlier revisions of this document described `WD.BIT` as a sparse strip table
whose entry count happened to be one and whose pointer targeted a metadata
word. That reading was an artefact of the withdrawn strip model; the four
leading words are simply the count, the single offset, the width, and the
height.

The practical visible role is narrower than "lettering artwork", and worth
stating because it explains the odd storage: the record is never drawn. It is a
**mask**. Its `288 x 49` footprint is exactly the footprint of one burning
subtitle band, and the driver's subtitle-ignition entry uses it to split a
two-pass reveal — the first pass restores only the positions where the mask bit
is clear, so the flames appear around the lettering, and the second pass
restores the positions where it is set, so the lettering fills in last. One mask
serves all four animation frames because the lettering is effectively invariant
across them: of the `1624` positions this record marks as lettering, `1623`
carry the same palette index in all four band records and exactly one does not.
That single pixel has no bearing on the effect, but "identical in all four" is
an overstatement and is withdrawn. See `systems/intro.md` section 5.

## 5. Rendering Behaviour

Loading is a two-step job that belongs to the caller, not to a display-driver
codec entry:

1. Read the file, classify it per Section 2.1, and decode the envelope when
   present.
2. Parse the sub-image list and keep the records addressable by index.

Drawing a record means stamping its set bits at a caller-chosen position. The
caller decides which records are drawn, where, in what order, and whether
earlier screen contents survive.

There is no driver dispatch entry that decompresses a `.BIT` file, but there is
one that draws a record from an already-decoded one. The intro hands the loaded
resource, a record index, and a destination pixel position to the driver's
one-bit stamp entry (`systems/display-driver-abi.md`, dispatch offset `0x4E`),
which bounds-checks the index, reads that record's own width and height, and
stamps its set bits into the hidden surface. Record indices are zero-based and
the whole range `0` through `count - 1` is addressable: the entry reads the
two-byte directory slot for the requested index and rejects only indices at or
above the count, returning without drawing. `TITLE.BIT` record `9` of its ten
records is a live intro draw, which settles the point; any implementation that
treats index `0` as a header slot or reserves the last record is wrong. The dispatch slot that earlier
revisions of this document assigned the decode role (`0x42`) belongs to the
packed-to-planar preparation step for the `.16`/`.4` archives and never touches
this family.

Because the records are one bit deep, a modern renderer needs a foreground
colour from the caller and a decision about background bits. The original
presentation draws ink only, leaving cleared bits untouched.

## 6. Validation And Error Handling

A strict loader or inspection tool should:

- Require at least the count word after decoding.
- Require `count` to be at least one and the offset table to fit in the image.
- Require the first offset to equal `2 + count * 2`.
- Require every offset to leave room for a four-byte sub-image header.
- Require each sub-image's row data (`max(1, ceil(width / 8)) * height` bytes)
  to stay inside the image. Do not special-case a zero width to zero bytes; see
  Section 3.
- Require the sub-images to tile the remainder of the image without gaps and to
  end exactly at the end of the image, using that same stride.
- For an enveloped file, require the decoded byte count to match the declared
  length and the code stream to terminate with an end code.

There are no sparse or skipped entries and no over-allocated table; every entry
in the directory names a real sub-image. A resource that does not satisfy the
checks above is corrupt or is not a member of this family.

## 7. Implementation Notes

- Share one LZW decoder between `formats/tiles.md` and this format; only the
  payload parser differs.
- Do not route `.BIT` or `.PCS` loading through a display-driver dispatch slot.
  See `systems/display-driver-abi.md` for the corrected mapping: `0x3F` fills a
  rectangle and `0x42` prepares an already-decompressed `.16`/`.4` container
  for plane-at-a-time blitting.
- Treat decoded records as addressable resources. The caller decides which
  records are drawn, where they are placed, and whether earlier screen contents
  remain visible.
- The title/menu idle animation frames are not stored in `.BIT`. They are
  records `1..4` of the paired-archive `ULTIMA` banner file; see
  `systems/intro.md` section 5. Earlier guidance calling them driver-local
  frames with no external source is withdrawn.

## 8. Boundaries And Residuals

**Ink colour.** The records carry no colour. Which palette index a record ends
up wearing is presentation state owned by `systems/intro.md` and
`systems/display-driver.md`, not by this format. For the EGA intro the answer
is not uniform, so it is worth stating where it lands: the stamp entry sets ink
bits in every colour plane of the hidden surface, so a record stamped and then
published by a whole-surface copy appears as palette index `15`. That covers
`TITLE.BIT` records `7`, `8` and `9` and the `BRITISH.BIT` signature. The seven
flourish records `0..6` are the exception, because they are never published by
a whole-surface copy: the animation-script entry reads one plane of the hidden
surface and writes it under a two-plane mask, so the flourish appears as
palette index `9`. Nothing in the intro reprograms the palette registers, so
those indices are the stock EGA colours.

**Non-EGA backends.** The analyzed CGA, Hercules, and Tandy drivers do not
provide an equivalent one-bit stamping path at the same fidelity. Rendering
substitute art for those backends is a modern enhancement, not a baseline rule.

**Title and story presentation.** This format owns the container and the
per-record pixel contract. The intro system owns the higher-level title flow,
story slide sequence, rectangle transitions, waits, and input handling.

## 9. Cross-References

- EGA display-driver ABI and driver bitmap entry:
  `systems/display-driver-abi.md`.
- Semantic display contract and title/menu idle animation:
  `systems/display-driver.md`.
- Intro title, menu, and story flow: `systems/intro.md`.
- Lord British path animation: `formats/pth.md`.
- Paired `.16`/`.4` screen-panel graphics: `formats/tiles.md`.
- Proportional font sibling resource: `formats/font-pcs.md`.

## 10. Sources

Cleanroom prose derived from private analysis notes. This document does not
include decompiled source, assembly excerpts, raw address tables, or raw bitmap
data.

- Container re-decode, envelope classification, and per-record dimensions:
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 1 and
  `u5-decomp/formats/fonts-bitmaps.md`.
- Withdrawal of the sparse strip / driver-codec reading:
  `u5-decomp/CORRECTIONS.md` "2026-08-22 corrections (bitmap codec re-decode)"
  and `u5-decomp/formats/ega-driver.md`.
- Intro title and story consumers, the one-bit stamp entry used to draw these
  records, per-record roles, and the whole-page publish ordering:
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x0D72_title_flourish_player.md`,
  `u5-decomp/functions/EGA_DRV/0x190E_silhouette_stamp_back_buffer.md`,
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`, and
  `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`.
- Which palette index each drawn record ends up wearing on the EGA path, and
  why the seven flourish records differ from the rest:
  `u5-decomp/notes/title_flourish_presenter_verification_2026-08-22.md`
  sections 4 and 6.
- The consecutive-offset invariant, and `WD.BIT`'s role as the two-pass mask of
  the subtitle ignition rather than as drawn artwork:
  `u5-decomp/notes/intro_title_sequence_2026-08-22.md`. The record inventories
  restated in section 4 were re-decoded from the shipped files before
  publication.
