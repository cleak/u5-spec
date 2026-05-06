# LOOK2.DAT

Format specification for `LOOK2.DAT`, the tile-description table used by the
L-Look command. The file maps each global tile id to a short prose description
or to a shared "not lookable" sentinel.

## 1. Overview

`LOOK2.DAT` is the lookup table that gives world and sprite tiles their
look-at text. When the player moves the look cursor over a tile, the look
handler resolves the tile id, indexes this file, and prints the description
string reached through the table.

The file covers the full tile-id space, five hundred twelve entries numbered
zero through five hundred eleven. It does not store tile graphics, passability,
animation, or trigger behaviour; those belong to the tile graphics files,
resident tile metadata, and mode-specific command handlers. `LOOK2.DAT` stores
only player-facing description text.

Many tile ids intentionally share one description string. Multiple grass,
water, wall, furniture, NPC, monster, and item variants may point to the same
text. A reader should therefore treat the offset table as a many-to-one mapping
rather than as one string per tile.

## 2. File Layout

The file has two regions:

| Region | Size | Meaning |
|---|---:|---|
| Offset table | 1,024 bytes | Five hundred twelve little-endian unsigned offsets, one per tile id. |
| String pool | Remaining bytes | NUL-terminated plain-ASCII description strings. |

The first word in the file is also the first table entry, for tile id zero. In
the shipped data it points to the start of the string pool. That string is the
shared sentinel used for tiles that should not produce a useful look-at
description.

Offsets are absolute byte positions from the start of `LOOK2.DAT`, not relative
to the string pool. Every valid shipped offset points into the string-pool
region. The final byte of the shipped file is a legacy DOS end-of-file marker;
it is not part of any string and should be ignored.

There is no magic number, version field, checksum, per-string length, or
terminating offset entry. The NUL byte ending each string is the only string
terminator.

## 3. Tile Indexing

Tile ids are global tile-catalog indices. To resolve a tile description, a
consumer selects the two-byte table entry for the tile id, interprets that
entry as the start position of a string in the same file, and then reads the
NUL-terminated description at that position.

Valid tile ids are zero through five hundred eleven. The on-disk table has no
room for higher ids. A renderer or tool that receives an out-of-range tile id
should not wrap or mask it; it should report a content error or substitute the
not-lookable sentinel.

The table's coverage matches the tile catalog rather than any one map format.
Map files store one-byte terrain tile ids, active-object records can refer to
sprite tile ids, and the look handler may need to describe either layer
depending on what occupies the selected cell.

## 4. String Encoding

Strings are plain NUL-terminated ASCII. They are not token-compressed and do
not use the conversation/shop common-word dictionary. The bytes are intended to
be handed to the normal text-output pipeline after the string has been selected.

No inline control markup has been confirmed for this file. Implementations
should treat bytes before the terminating NUL as printable text unless future
analysis proves a control convention.

The sentinel string is a normal string in the pool. It is shared by many tile
ids and means "there is no meaningful look description for this tile." Public
specs should refer to it semantically rather than requiring user interfaces to
display the original sentinel glyph.

## 5. Rendering Behaviour

`LOOK2.DAT` does not define its own renderer. The look command selects a string
and passes it to the game's text-output subsystem. Word wrapping, cursor
advance, active text window, colours, and scrolling are therefore governed by
the text-output rules, not by this file.

A modern implementation may render the selected description in any equivalent
look-message UI. To match original behaviour, it should preserve these
semantics:

- Resolve the visible tile to its global tile id before indexing the table.
- Use the offset table directly; do not derive descriptions from tile ranges.
- Allow duplicate offsets and shared strings.
- Treat the sentinel as "not lookable" rather than as an ordinary terrain name.

The exact precedence between terrain and active-object descriptions is a
look-command behaviour, not a property of `LOOK2.DAT`.

## 6. Validation and Error Handling

A robust reader should validate the table before using it:

- The file must be at least 1,024 bytes long.
- Every table offset should be greater than or equal to 1,024 and less than the
  file length after ignoring a final DOS end-of-file marker if present.
- Every offset should reach a NUL terminator before end of meaningful file data.
- Duplicate offsets are valid and expected.
- Offsets need not be sorted by tile id; consumers should not depend on
  monotonic ordering.

For malformed data, an implementation should fail loudly in tooling. At
runtime, substituting the not-lookable sentinel is the least disruptive
fallback when one tile's entry is bad.

## 7. Cross-References

- `catalogs/tile-catalog.md` describes the global tile-id space and how look-at
  strings fit alongside sprites, passability, animation, and triggers.
- `systems/text-output.md` describes the text window and wrapping behaviour
  used after a description string is selected.

## 8. Open Questions

- **Layer precedence.** The table is keyed by tile id, but the exact look-command
  rule for choosing between terrain and active-object layers belongs to the
  look handler and remains to be documented in a system spec.
- **Sentinel presentation.** The original data uses a compact sentinel string.
  Whether the UI prints that glyph literally in every context, suppresses it,
  or replaces it with a stock refusal message should be confirmed against the
  look-command path.
- **Inline controls.** No control bytes are currently known in the file. Future
  analysis should confirm whether all strings are plain printable text.

## 9. Sources

This cleanroom spec was derived from the following private analysis notes. No
decompiled code, assembly, raw address tables, or copied data strings are
reproduced here. Existing public specs were used only for terminology and
cross-reference alignment.

- The `LOOK2.DAT` size, offset-table shape, string-pool sharing, sentinel role,
  and consumer attribution -- derived from
  `u5-decomp/formats/data-tables.md`.
- The direct tile-id lookup, two-stage file read, and print handoff -- derived
  from `u5-decomp/functions/LOOKOBJ_OVL/0x0000_lookobj_print_tile_string.md`.
- The look-command layer resolution and special-tile fall-through context --
  derived from `u5-decomp/functions/LOOKOBJ_OVL/0x0502_lookobj_describe.md`.
