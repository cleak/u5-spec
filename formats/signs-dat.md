# SIGNS.DAT

Format specification for `SIGNS.DAT`, the data file that stores sign placards
and sign-style message streams read by the surface/town Look command. The
runtime consumer is now traced: `SIGNS.DAT` is a scene-indexed table of
coordinate-matched records, and each selected record is printed by a small
byte-stream formatter.

## 1. Overview

`SIGNS.DAT` stores sign and poster text for sign-like map tiles. A sign lookup
starts from the active scene and the looked-at tile coordinate. The file first
selects a scene block, then scans that block for one or more records whose
header matches the looked-at `(z, x, y)` coordinate. Matching records are sent
to the sign formatter.

This is different from `LOOK2.DAT` and `QUESTION.DAT`:

- `LOOK2.DAT` maps a tile id to a NUL-terminated text string.
- `QUESTION.DAT` stores paragraph text consumed by the proportional-font
  renderer.
- `SIGNS.DAT` stores coordinate-keyed sign streams with formatter controls.

The same high-bit text presentation conventions appear in other message
families, so sign records should be treated as formatted message streams rather
than as arbitrary ASCII text.

## 2. File Model

At a high level the file contains:

| Region | Meaning |
|---|---|
| Scene directory | Thirty-three little-endian scene-block offsets. A zero offset means the scene has no sign block. |
| Scene blocks | Variable-size record streams for one scene, read into a scratch buffer before scanning. |
| Records | Coordinate header plus a NUL-terminated formatted sign stream. |

The traced consumer reads the first 66 bytes as the directory and indexes it by
the active scene byte. The resulting offset, if nonzero, is used as the seek
position for the scene block. The consumer reads a fixed maximum window from
that block into scratch memory, fills unread scratch with an end sentinel, and
then scans records until it reaches the sentinel.

The safest public contract is semantic:

- A sign lookup starts with the active scene and the looked-at tile coordinate.
- Empty directory slots mean "there is no sign block for this scene."
- Nonempty slots identify a scene block in the same file.
- A scene block may contain multiple records, and more than one record may match
  the same coordinate.
- If no record matches, the renderer emits the stock blank/cancel sign response.

The tile-to-coordinate mapping does not live in `SIGNS.DAT`; it is supplied by
the Look command path and active location state.

## 3. Record Structure

A sign record begins with a four-byte header:

| Header byte | Meaning |
|---:|---|
| 0 | Scene id. |
| 1 | Z or floor discriminator. |
| 2 | X coordinate. |
| 3 | Y coordinate. |

The scene id is selected primarily through the scene directory: each nonempty
directory entry points to the first record for that scene. After loading that
window, the traced scanner compares only the record's `z`, `y`, and `x` bytes
against the looked-at coordinate. A content tool should still preserve and
validate the scene byte because it is present in every shipped record header
and is the basis for the directory ordering.

After the header, the payload is a NUL-terminated byte stream. The scene-block
scanner advances from one record to the next by skipping the four-byte header,
then walking through the payload terminator. A block ends when the scanner
encounters the scratch-buffer end sentinel.

The formatter has one additional wrinkle: after the four-byte coordinate
header, it can skip six-byte alias bridges while it sees the line-separator
marker used by the sign stream. These bridges let multiple coordinate headers
share one printed body. In the shipped file, the bridge is a separator byte, a
zero byte that terminates the scanner's current payload walk, and then another
four-byte `[scene, z, y, x]` header. The scanner can therefore encounter the
alternate header as the next record, while the formatter skips over the bridge
and prints the shared body.

The printable body is interpreted by the formatter described below; it is not a
rectangular grid with width and height fields.

## 4. Glyph Encoding

The sign payload is mostly ASCII-like, but it is not ordinary plain text:

- Byte `0x00` terminates the current record.
- Byte `0x0D` pauses for a keypress and then resumes printing.
- Bytes `0x29..0x31` select NUL-terminated decoration fragments from a small
  resident macro pool rather than printing the byte directly. Shipped records
  use these fragments for framed-sign edges and corners.
- Bytes `0x26` and `0x27` both emit the same separator glyph through the sign
  presentation mode. Shipped records use them in repeated pairs as a decorative
  divider, not as gameplay substitutions.
- Other bytes print as their low-seven-bit character value.
- The high bit controls a presentation mode used by the text output layer; it
  does not change which low-seven-bit character is emitted.

Because this is an already-authored message stream, a decoder should not run it
through proportional word wrapping or case folding. It should preserve explicit
newlines, pauses, macro substitutions, and the presentation-mode toggles.

## 5. Indexing Semantics

`SIGNS.DAT` does not decide whether the party is reading a sign. The caller must
already have resolved a sign interaction from the active scene, target tile, and
looked-at coordinate.

The expected lookup pipeline is:

1. Command or movement logic determines that a sign should be read.
2. The active scene indexes the `SIGNS.DAT` scene directory.
3. A zero directory entry produces the stock blank/cancel sign response.
4. A nonzero directory entry selects a scene block.
5. The scene block is scanned for records whose coordinate header matches the
   looked-at tile.
6. Every matching record is printed through the sign formatter.
7. If no records match before the scene-block sentinel, the stock blank/cancel
   response is printed.

Directory holes are normal content holes, not corrupt records.

## 6. Rendering Behaviour

`SIGNS.DAT` records are already authored as display streams. A renderer should:

- Print ordinary bytes as low-seven-bit characters.
- Apply the sign formatter's macro substitutions.
- Pause on the embedded pause code.
- Honour the high-bit presentation-mode flag through the same text-output mode
  used by the surrounding Look renderer.
- Avoid proportional-font wrapping, implicit line breaking, or case folding.

The display target is a gameplay UI concern. A modern implementation can draw
the sign into a modal panel, text-grid layer, or equivalent surface as long as
the byte-stream semantics and output ordering are preserved.

The hard-coded wanted-poster path is separate from `SIGNS.DAT`: Yew, floor `0`,
local coordinate `(x=17, y=21)` renders a fixed poster from resident text and
party names without consulting the file's scene blocks. That exception belongs
to the Look command behavior, but implementers should not try to find that
poster in `SIGNS.DAT`.

## 7. Validation and Error Handling

Validation should separate hard file errors from data that the runtime simply
skips:

- Directory entries that are explicitly empty are valid.
- Nonempty directory entries should point inside the file and to plausible
  scene-block starts.
- A scene block should contain NUL-terminated records and an end sentinel within
  the maximum read window used by the runtime consumer.
- Records whose scene byte does not match the directory slot are suspicious in
  authoring tools, but the runtime does not re-check that byte after using the
  directory.
- Records whose `z`, `y`, and `x` header bytes do not match the looked-at
  coordinate are skipped, not treated as malformed.
- Alias bridges should lead to another four-byte header and then to a shared
  NUL-terminated printable body.
- Payload bytes outside the known formatter controls should be preserved in
  tooling and printed by the low-seven-bit fallback unless a stricter authoring
  mode flags them for review.
- A scene id outside the directory range should be treated as "no sign" in
  runtime code and as a content error in authoring tools.

If a record is malformed at runtime, the safest fallback is to decline to render
the sign rather than emitting raw cell bytes as prose.

## 8. Cross-References

- `formats/location-dat.md` describes town and location tile grids, including
  sign-post tiles as renderable terrain and trigger sources.
- `catalogs/tile-catalog.md` describes sign tiles as part of the furniture and
  special-trigger tile families.
- `systems/text-output.md` owns the text-output presentation mode used by sign
  high-bit toggles.
- `systems/view.md` owns the Look-command sign lookup and the wanted-poster
  exception.

## 9. Format Boundaries And Content Catalog Work

The file-format contract is complete at reader depth: scene-directory lookup,
coordinate-record scanning, alias bridges, formatter controls, macro
substitution, pause handling, high-bit presentation toggles, and the
wanted-poster separation are public.

Remaining work is content cataloguing, not format interpretation:

- **Macro fragment identities.** The formatter's macro selector range and
  substitution role are specified above. The exact resident decoration
  fragments remain a visual-parity boundary; do not copy shipped sign text or
  resident string dumps into this clean spec.
- **Full scene-block inventory.** A content pass should enumerate which scenes
  have nonzero directory entries and which coordinates have sign records,
  without copying the shipped sign text into the spec.

## 10. Sources

This cleanroom spec was derived from the following private analysis note. No
decompiled code, assembly, raw address tables, or copied sign text are
reproduced here. Existing public specs were used only for terminology and
cross-reference alignment.

- The original `SIGNS.DAT` survey and indexed-record observation -- derived
  from `u5-decomp/formats/data-tables.md`.
- The scene directory, coordinate scan, hard-coded wanted-poster exception, and
  scene-block read window -- derived from
  `u5-decomp/functions/LOOKOBJ_OVL/0x07E4_wanted_poster_render.md`.
- The per-record formatter controls, macro substitution, pause behavior, and
  high-bit presentation-mode semantics -- derived from
  `u5-decomp/functions/LOOKOBJ_OVL/0x06F8_signs_dat_print.md`.
- Shipped `SIGNS.DAT` header, alias-bridge layout, decorator macros, and
  separator-glyph usage were cross-checked against the traced directory offsets
  and record scanner.
