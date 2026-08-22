# LOOK2.DAT

Format specification for `LOOK2.DAT`, the surface/town description table used
by the L-Look command. The file has a lower terrain-description domain and an
upper object-description domain, both pointing into one shared string pool.

## 1. Overview

`LOOK2.DAT` is the lookup table that gives surface and town L-Look its base
description text. When the player looks at ordinary terrain, the handler
indexes the lower half of the table by the resolved map-cell tile id. When the
target resolves to a per-map or active-object entry, the handler indexes the
upper half by that object-domain id. In both cases the selected table word
points to a NUL-terminated string, which is then printed through the normal text
output path.

The file contains five hundred twelve table entries split into two domains:
two hundred fifty-six terrain entries followed by two hundred fifty-six object
entries. It does not store tile graphics, passability, animation, trigger
behaviour, or the active-object records themselves; those belong to the tile
graphics files, resident tile metadata, active-object state, and mode-specific
command handlers. `LOOK2.DAT` stores only player-facing description text.

Many entries intentionally share one description string. Multiple grass, water,
wall, furniture, NPC, monster, and item variants may point to the same text. A
reader should therefore treat the offset table as a many-to-one mapping rather
than as one string per table entry.

## 2. File Layout

The file has two regions:

| Region | Size | Meaning |
|---|---:|---|
| Offset table | 1,024 bytes | Five hundred twelve little-endian unsigned offsets: entries 0..255 for terrain descriptions and 256..511 for object descriptions. |
| String pool | Remaining bytes | NUL-terminated plain-ASCII description strings. |

The first word in the file is also the first terrain-domain table entry, for
tile id zero. In the shipped data it points to the start of the string pool.
That string is the shared sentinel used for terrain or object entries that
should not produce a useful look-at description.

Offsets are absolute byte positions from the start of `LOOK2.DAT`, not relative
to the string pool. Every valid shipped offset points into the string-pool
region. The final byte of the shipped file is a legacy DOS end-of-file marker;
it is not part of any string and should be ignored.

There is no magic number, version field, checksum, per-string length, or
terminating offset entry. The NUL byte ending each string is the only string
terminator.

## 3. Lookup Domains

The table has two public lookup domains:

- **Terrain domain.** Entries 0..255 are selected by the resolved world or town
  map-cell tile id. To resolve a terrain description, read the two-byte table
  entry at `tile_id * 2`, interpret that word as an absolute string-pool offset,
  and then read the NUL-terminated description at that position.
- **Object domain.** Entries 256..511 are selected by an object-domain id from
  the surface/town look path. To resolve an object description, read the
  two-byte table entry at `0x200 + object_id * 2`, interpret that word as an
  absolute string-pool offset, and then read the NUL-terminated description at
  that position.

Valid terrain ids and object-domain ids are zero through two hundred
fifty-five within their respective domains. A renderer or tool that receives an
out-of-range id should not wrap or mask it; it should report a content error or
substitute the not-lookable sentinel.

This split is important for clean implementations. Map files store one-byte
terrain tile ids and can only address the lower terrain domain directly.
Per-map object and active-object look paths can describe the visible upper layer
without treating those upper-domain entries as ordinary static map-cell tile
descriptions.

## 4. String Encoding

Strings are plain NUL-terminated ASCII. They are not token-compressed and do
not use the conversation/shop common-word dictionary. The bytes are intended to
be handed to the normal text-output pipeline after the string has been selected.

The shipped IBM PC baseline contains no inline control markup in this file.
Every byte inside every referenced string is printable ASCII; NUL is only the
string terminator. Formatting such as clock-time suffixes, shrine context, and
sign text is added by the LOOKOBJ command handlers around the base lookup, not
encoded inside `LOOK2.DAT`.

The sentinel string is a normal string in the pool. It is shared by many table
entries and means "there is no meaningful look description for this target."
Public specs should refer to it semantically rather than requiring user
interfaces to display the original sentinel glyph. In the original default
LOOK2 path, the selected sentinel string is still handed to text output like
any other selected string; suppressing or replacing it is a modern presentation
choice.

## 5. Rendering Behaviour

`LOOK2.DAT` does not define its own renderer. The look command selects a string
and passes it to the game's text-output subsystem. Word wrapping, cursor
advance, active text window, colours, and scrolling are therefore governed by
the text-output rules, not by this file.

A modern implementation may render the selected description in any equivalent
look-message UI. To match original behaviour, it should preserve these
semantics:

- Resolve the visible target to the correct LOOK2 domain before indexing the
  table.
- Use the offset table directly; do not derive descriptions from tile or object
  ranges.
- Allow duplicate offsets and shared strings.
- Treat the sentinel as "not lookable" rather than as an ordinary terrain name.

For world and town L-Look, the command handler owns the layer resolution before
`LOOK2.DAT` is indexed. The direction prompt and facing-cell lookup produce a
terrain tile plus active-object context. Terrain descriptions use the lower
domain directly. Per-map object descriptions use the upper object domain. The
table lookup itself is direct in the chosen domain; there is no extra
description-category translation step inside the file format.

A few tile ids have command-specific handling around the table lookup:

- `0x59` routes to LOOKOBJ's sky renderer (`systems/view.md` section 4.2) instead of
  printing the base `LOOK2.DAT` string. Its final in-world catalog label is
  intentionally left to `systems/view.md` and `catalogs/tile-catalog.md`.
- `0xA1` routes to the LOOKOBJ wishing-well handler and `0xD8..0xDB` routes to
  the LOOKOBJ fountain handler. Both replace the base string entirely rather
  than decorating it. The two differ in what they store: `0xD8..0xDB` share the
  placeholder record, but `0xA1` carries a real description record of its own
  naming a deep well, which the look path never reaches because the handler
  returns first. Owning a real record therefore does not mean an id lacks a
  handler, and carrying the placeholder is not a reliable way to enumerate the
  handler-driven ids; use the dispatch tables in `systems/view.md` Section 3.
  `0xD8..0xDB` here is a terrain-domain id; the identically numbered entries in
  the object domain are an unrelated creature sprite run.
- `0xE0`, `0xE1` and `0xE2` behave as redirects: the look command moves its
  target cell one step (north, east and west respectively) and re-resolves
  before any lookup happens, so the look path never prints these ids' own
  records. They do carry real description records all the same — all three
  share one desert-terrain string — which other readers of the table may use.
- `0xFA` and `0xFB` print their base `LOOK2.DAT` description, then append the
  current clock time with an AM/PM suffix.
- `0xDE` prints its base description, then appends the current shrine
  principle or virtue context.
- `0xDF` prints its base description, then appends the dungeon name selected
  from the command context.

The command-level trigger table, including the dispatch order and the
predicates that never reach this file at all, is in `systems/view.md`
Section 3.

These rules belong to the L-Look command path. The data file itself remains a
plain table from a domain-specific lookup id to a base description string.

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
fallback when one table entry is bad.

## 7. Cross-References

- `catalogs/tile-catalog.md` describes the global tile-id space and how terrain
  look strings fit alongside sprites, passability, animation, and triggers.
- `systems/town-mode.md` describes the town command loop that routes L-Look into
  this shared world/town look path.
- `systems/text-output.md` describes the text window and wrapping behaviour
  used after a description string is selected.

## 8. Variant Boundary

No open format questions remain for the shipped IBM PC baseline. Future variant
support is an asset-validation task: re-run the rules in Section 6 against that
variant's `LOOK2.DAT` and do not infer new runtime semantics from different
description strings alone.

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
- The upper object-domain lookup and shared print handoff -- derived from
  `u5-decomp/functions/LOOKOBJ_OVL/0x06A4_lookobj_print_object_string.md`.
- The look-command layer resolution and special-tile fall-through context --
  derived from `u5-decomp/functions/LOOKOBJ_OVL/0x0502_lookobj_describe.md`.
- Which handler-driven tile ids carry the placeholder record and which carry a
  real record (the deep-well and desert cases) -- derived from
  `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md`.
