# SIGNS.DAT

Format specification for `SIGNS.DAT`, the data file that stores sign placards
and sign-style glyph panels. The file is partly resolved: the rendered record
payloads and glyph encoding are understood, while the complete meaning of the
leading directory and every header field still needs deeper consumer analysis.

## 1. Overview

`SIGNS.DAT` stores precomposed sign panels rather than ordinary prose strings.
A sign record describes a small rectangular tile grid containing border pieces,
spaces, and letter glyphs. The sign reader uses the record to paint a placard
or sign-like page into the display area.

This is different from `LOOK2.DAT` and `QUESTION.DAT`:

- `LOOK2.DAT` maps a tile id to a NUL-terminated text string.
- `QUESTION.DAT` stores paragraph text consumed by the proportional-font
  renderer.
- `SIGNS.DAT` stores a compact grid of sign glyph cells and border cells.

The same glyph convention appears in at least one other message family for
Codex-style pages, so the encoding should be treated as a small reusable tile
alphabet rather than as arbitrary ASCII text.

## 2. File Model

At a high level the file contains:

| Region | Meaning |
|---|---|
| Leading directory | A compact set of little-endian values used to locate sign records. Some slots are empty. |
| Record bodies | Variable-size binary records containing a header and a grid of sign cells. |

The source survey identifies the file as an indexed sign-record table and
observes empty slots in the directory. A direct structural pass confirms that
nonzero directory values can point to placard records, but the exact slot count
and the complete role of the leading word are not yet settled. Implementations
should therefore parse this file defensively and avoid assuming that every
leading word-sized value is a valid record pointer.

The safest public contract is semantic:

- A sign lookup starts with a small integer sign id supplied by the caller.
- Empty directory slots mean "there is no sign record for this id."
- Nonempty slots identify a record body in the same file.
- Record bodies contain their own dimensions or layout fields plus the cell
  stream needed to render the sign.

The location-to-sign-id mapping does not live in `SIGNS.DAT`; it is supplied by
town/location state and command logic.

## 3. Record Structure

A sign record begins with a small binary header followed by a rectangular cell
payload. The source survey observes header fields consistent with a sign id,
dimensions, and additional placement or style values, but the field boundaries
are not fully verified. In particular, candidate width and height values are
visible in the header, but their exact offsets and whether they describe the
outer border or the interior text area remain open.

After the header, the payload is a run of one-byte cell codes. These codes are
not NUL-terminated strings. They describe the sign as a grid to be drawn using
the sign glyph alphabet:

- Border and frame codes draw corners, horizontal edges, vertical edges, posts,
  and fence-like separators.
- Letter codes draw uppercase Latin letters.
- Special spacing codes draw blanks between words or pad the interior.
- A small number of digraph and abbreviation codes stand for multi-letter
  glyphs used by Britannian sign text.

The payload should be consumed according to the dimensions supplied by the
record header once those fields are confirmed. Until then, tooling can use the
next directory offset or end of file as a record boundary for inspection, but a
runtime implementation should not rely on boundary inference alone.

## 4. Glyph Encoding

The sign glyph payload is mostly ASCII-like, but it is not ordinary text:

- Uppercase letter glyphs can appear either as direct uppercase byte values or
  as bytes with the high bit set. When the high bit is set, stripping it yields
  the corresponding uppercase letter.
- A dedicated spacing code represents an interior word space. This is distinct
  from an ordinary blank border or unused padding cell.
- Dedicated digraph codes represent common two-letter forms used by sign text.
  The source survey confirms at least the TH digraph; other similar glyphs are
  likely shared with Codex-style pages.
- Border and decorative cells use a separate small alphabet. These bytes should
  be interpreted as sign-cell ids, not as printable prose characters.

Because this is a grid encoding, a decoder should not first flatten the payload
to a text string and then lay it out with word wrap. The original content is
already laid out. Rendering should preserve cell order, line breaks implied by
the grid width, border placement, and spacing cells.

## 5. Indexing Semantics

`SIGNS.DAT` does not decide which sign the party is reading. The caller must
already have resolved a sign interaction from the active scene, the party or
cursor position, and the location's sign metadata.

The expected lookup pipeline is:

1. Command or movement logic determines that a sign should be read.
2. Scene/location metadata supplies a sign id.
3. The sign id indexes the file's directory.
4. An empty slot produces no sign panel or a stock "nothing readable" response.
5. A nonempty slot selects one sign record.
6. The sign renderer paints the record's precomposed grid.

The source survey notes unused slots. Those should be treated as normal content
holes, not as corrupt records.

## 6. Rendering Behaviour

`SIGNS.DAT` records are already visually arranged. A renderer should:

- Determine the outer grid size from the record header once the dimensions are
  known.
- Draw one cell per payload code in row-major order.
- Render border, space, letter, and digraph codes through the sign glyph
  alphabet.
- Avoid proportional-font wrapping, line breaking, or case folding.

The display target is a gameplay UI concern. A modern implementation can draw
the sign into a modal panel, text-grid layer, or equivalent surface as long as
the cell layout and glyph meanings are preserved.

The sign glyph alphabet should be shared with other page-like data that uses
the same encoding. If an implementation already supports Codex-style page
glyphs from another message file, that decoder is the right starting point for
sign payloads.

## 7. Validation and Error Handling

Because the directory/header structure is not fully resolved, validation should
separate hard file errors from unresolved fields:

- Directory entries that are explicitly empty are valid.
- Nonempty directory entries should point inside the file and to plausible
  record starts.
- A record's declared dimensions, once decoded, should fit within the bytes
  available before the next record or end of file.
- Payload bytes outside the known glyph alphabet should be preserved in tooling
  and reported as unknown glyph cells rather than silently discarded.
- A sign id outside the directory range should be treated as "no sign" in
  runtime code and as a content error in authoring tools.

If a record is malformed at runtime, the safest fallback is to decline to render
the sign rather than emitting raw cell bytes as prose.

## 8. Cross-References

- `formats/location-dat.md` describes town and location tile grids, including
  sign-post tiles as renderable terrain and trigger sources.
- `catalogs/tile-catalog.md` describes sign tiles as part of the furniture and
  special-trigger tile families.
- `systems/text-output.md` is relevant only for surrounding prompts; sign
  payloads themselves are grid-rendered rather than word-wrapped text.

## 9. Open Questions

- **Directory shape.** The source survey identifies indexed sign records and
  empty slots, but the exact leading directory width, slot count, and meaning
  of the first word need confirmation from the sign consumer.
- **Header fields.** The record header clearly carries layout metadata, but the
  exact field order and whether dimensions refer to border-inclusive or
  text-interior cells are not fully verified.
- **Complete glyph alphabet.** The letter, space, border, and TH-digraph cases
  are understood. The full set of decorative and digraph cells should be
  enumerated after the renderer is traced.
- **Sign-id source.** The per-location mapping from a sign tile or coordinate
  to a sign id is not documented here. It likely belongs with town-mode command
  logic or location metadata.

## 10. Sources

This cleanroom spec was derived from the following private analysis note. No
decompiled code, assembly, raw address tables, or copied sign text are
reproduced here. Existing public specs were used only for terminology and
cross-reference alignment.

- The `SIGNS.DAT` role, indexed-record interpretation, empty-slot observation,
  precomposed-grid payload, border-cell alphabet, and glyph encoding findings
  -- derived from `u5-decomp/formats/data-tables.md`.
