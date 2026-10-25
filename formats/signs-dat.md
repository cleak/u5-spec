# SIGNS.DAT

Format specification for `SIGNS.DAT`, the data file that stores sign placards
and sign-style message streams read by the surface/town Look command. The
runtime consumer is now traced: `SIGNS.DAT` is a scene-indexed table of
coordinate-matched records, and each selected record is printed by a small
byte-stream formatter.

## 1. Overview

`SIGNS.DAT` stores sign and poster text for sign-like map tiles. A sign lookup
starts from the active scene and the looked-at tile coordinate. The file first
selects where the scene's block starts, then scans a fixed window from there for
the first record whose header matches the looked-at `(z, x, y)` coordinate, and
sends that one record to the sign formatter. The window is not bounded by the
scene: it can run on into later scenes' records (Section 5). *(Corrected
2026-10-25, issue #300 Q13: this paragraph said the block is scanned for one or
more matching records and all are printed; that is retracted, `RETRACTIONS.md`
R598 and R599.)*

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
- A scene block may contain multiple records. No shipped scene block holds two
  records for the same coordinate; a duplicate match arises in shipped data only
  when the read window runs on into a later scene's records (Section 5), and
  only the first match is ever printed.
- A zero directory entry, or a window in which nothing matches, prints the fixed
  six-row placard of Section 6. *(Corrected 2026-10-25, issue #300 Q13: these
  bullets said more than one record may match and that a non-matching scene
  block gives a "stock blank/cancel" response; see `RETRACTIONS.md` R598 and
  R599.)*

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
then walking through the payload terminator. A scene block has no terminator of its
own: the scan ends only at the scratch-buffer end sentinel that follows the
fixed read window, so it continues across the next scenes' records until the
window is used up. *(Corrected 2026-10-25, issue #300 Q13: this sentence said a
block ends at the sentinel, implying the scan stays within the scene; retracted,
`RETRACTIONS.md` R599.)*

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

Each payload byte is handled in this order *(corrected 2026-10-25, issue #300
Q13 and Q21)*:

1. **The high bit selects the font for that byte.** High bit clear selects the
   runic font (font slot 1); high bit set selects the Roman text font (slot 0).
   The two fonts share code points (`systems/text-output.md` Section 7), so the
   low seven bits are the code point either way. Most sign text therefore shows
   in runes, and high-bit bytes show as plain Roman characters.
2. **The control tests then compare the raw byte, high bit included.**
   - Byte `0x00` terminates the record.
   - Only raw `0x26` and `0x27` are separators. Each prints one cell in the runic
     font at the code point of lowercase `l`, which in that font is a full-width
     horizontal bar. Shipped records use them in repeated pairs as a decorative
     divider.
   - Only raw `0x29..0x31` are macros. Each switches to the runic font and prints
     one NUL-terminated decoration fragment from a small resident pool; all nine
     fragments are sixteen cells wide. Shipped records use them for framed-sign
     edges and corners.
   - Only raw `0x0D` pauses. It switches to the Roman font and waits for a key; it
     prints nothing and does not echo the key.
3. **Every other byte prints its low seven bits in the font chosen in step 1.**
   This is the only place the high bit is removed. So `0xA6` and `0xA7` print the
   Roman `&` and `'`, not the bar; `0xA9..0xB1` print the Roman characters at code
   points `0x29..0x31`, not a macro; `0x8D` reaches the cell emitter as a carriage
   return (column reset, no glyph), not a pause; and `0x8A` is a line feed.
4. **After the terminator** the Roman font is restored, and one line feed is
   printed only if the cursor is not at column 0.

The high bit was previously described here as a presentation mode that "does
not change which low-seven-bit character is emitted"; it selects the font, and
the control codes are recognised only with it clear, so that text is retracted
(`RETRACTIONS.md` R600).

Sign bodies go through the per-cell emitter, not the word-wrapping printer
(`systems/text-output.md` Section 5). A sixteen-cell row wraps on its own in
the sixteen-column message window; 30 of the 79 shipped records instead end
fifteen-cell rows with a high-bit line feed (`0x8A`).

Census of the shipped file, for implementers checking a reader: raw `0x26` and
`0x27` occur 56 times each; `0xA6` never and `0xA7` 8 times; raw macro-range
bytes 88 times; high-bit macro-range bytes 81 times, and those are only the
Roman comma, period, slash and digit `1`; raw `0x0D` 8 times and `0x8D` never;
`0x8A` 150 times. A reader that masked the high bit before the control tests
would turn that shipped punctuation into frame fragments and bars.

Because this is an already-authored message stream, a decoder should not run it
through proportional word wrapping or case folding. It should preserve explicit
newlines, pauses, macro substitutions, and the per-byte font selection.

## 5. Indexing Semantics

`SIGNS.DAT` does not decide whether the party is reading a sign. The caller must
already have resolved a sign interaction from the active scene, target tile, and
looked-at coordinate.

The expected lookup pipeline is:

1. Command or movement logic determines that a sign should be read.
2. The active scene indexes the `SIGNS.DAT` scene directory.
3. A zero directory entry produces the stock blank/cancel sign response.
4. A nonzero directory entry gives the start of the scene's block. A fixed-size
   window is read from there, and the space after whatever was read is filled
   with the end sentinel.
5. The window is scanned for a record whose `z`, `x` and `y` match the
   looked-at tile. The scene byte is never compared, and a scene block has no
   terminator of its own, so the scan runs on into the records of later scenes
   for as long as the window lasts. Executed on shipped data: a lookup in
   scene 3 at a coordinate that has only a scene-4 record printed that scene-4
   sign, not the placard.
6. The first matching record is printed through the sign formatter and the scan
   stops; a later record with the same coordinate is never shown. Executed on
   shipped data: a scene-4 coordinate that a later scene-5 record also uses
   printed one sign.
7. If nothing in the whole window matches, the placard of Section 6 is printed.

*(Corrected 2026-10-25, issue #300 Q13.)* Step 6 previously said every matching
record is printed; only the first is, and that text is retracted
(`RETRACTIONS.md` R598). Steps 5 and 7 previously bounded the scan by the scene
block; it is bounded by the read window, which crosses into later scenes, and
that text is retracted (`RETRACTIONS.md` R599). The window's length is not
published here (`OPEN-QUESTIONS.md` section 3).

Directory holes are normal content holes, not corrupt records.

## 6. Rendering Behaviour

`SIGNS.DAT` records are already authored as display streams. A renderer should:

- Print ordinary bytes as low-seven-bit characters in the font their high bit
  selects (Section 4).
- Apply the sign formatter's macro substitutions (raw bytes only).
- Pause on the embedded pause code (raw `0x0D` only).
- Select the runic font for high-bit-clear bytes and the Roman font for
  high-bit-set bytes, and restore the Roman font at the end of the record.
  *(Corrected 2026-10-25, issue #300 Q13/Q21: this bullet called the high bit a
  presentation-mode flag; it selects the font, `RETRACTIONS.md` R600.)*
- Avoid proportional-font wrapping, implicit line breaking, or case folding.

The display target is a gameplay UI concern. A modern implementation can draw
the sign into a modal panel, text-grid layer, or equivalent surface as long as
the byte-stream semantics and output ordering are preserved.

The hard-coded wanted-poster path is separate from `SIGNS.DAT`: Yew, floor `0`,
local coordinate `(x=17, y=21)` renders a fixed poster from resident text and
party names without consulting the file's scene blocks. That exception belongs
to the Look command behavior, but implementers should not try to find that
poster in `SIGNS.DAT`.

The poster's logical rows are:

```text
abbbbbbbbbbbbbc
g   Wanted:   g
g             g
g<slot 0 name>g
g<slot 1 name>g
g<slot 2 name>g
g             g
gDead or Aliveg
deeeeeeeeeeeeeef
```

The border letters above are the resident sign-border glyph fragments used by
the original text layer, not prose to be word-wrapped. The three name rows use
current party slots `0..2` in order and are centered by starting each name at
column `7 - floor(name_length / 2)` before emitting the right border at column
`14`. Rows whose slot index is not below the current party count remain blank.

**The no-record placard** *(added 2026-10-25, issue #300 Q13)*. A zero
directory entry, or a read window with no matching record, prints a fixed
six-row framed placard from resident text, in the runic font, in the same
code-point notation as the poster above:

```text
abbbbbbbbbbbbbbc
g              g
g  LIVE@BY@[E  g
g  EIGHT@LAWS  g
g              g
deeeeeeeeeeeeeef
```

In the runic font `@` is a centred word-divider dot and `[` is the TH rune, so
the two inner rows read "LIVE BY THE / EIGHT LAWS". Every row is sixteen cells
and ends with a line feed carried in the same stored string. The Roman font is
selected again afterwards, and unlike a record this path does not run the
column-0 test of Section 4 step 4, so it adds no line feed beyond its rows.
Executed for both triggers (the rows matched the stored strings). That no blank
row appears between the rows is inferred, not observed: the printer was stubbed,
and the conclusion rests on the full-row suppression rule of
`systems/text-output.md` Section 6.

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
- `systems/text-output.md` owns the Roman and runic font slots that the sign
  high bit selects (Section 7).
- `systems/view.md` owns the Look-command sign lookup and the wanted-poster
  exception.

## 9. Format Boundaries And Content Catalog Work

The file-format contract is complete at reader depth: scene-directory lookup,
coordinate-record scanning, first-match selection, alias bridges, formatter
controls, macro substitution, pause handling, per-byte font selection, the
no-record placard and the wanted-poster separation are public; the read
window's length is not.

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
  `u5-decomp/functions/LOOKOBJ_OVL/`.
- The per-record formatter controls, macro substitution, pause behavior, and
  high-bit presentation-mode semantics -- derived from
  `u5-decomp/functions/LOOKOBJ_OVL/`.
- Issue #300 Q13 and Q21 (2026-10-25): the per-byte font selection, the
  raw-byte control tests, the first-match stop, the scene-unbounded read
  window and the no-record placard -- established by executing the original
  Look entry, sign lookup and formatter on the shipped file and on synthetic
  records with the font selector logged, plus a byte census of the shipped
  file and an independent re-run by a verifier; glyph shapes are from the
  shipped runic font. Private analysis in `u5-decomp/notes/` and
  `u5-decomp/functions/LOOKOBJ_OVL/`.
- Shipped `SIGNS.DAT` header, alias-bridge layout, decorator macros, and
  separator-glyph usage were cross-checked against the traced directory offsets
  and record scanner.
