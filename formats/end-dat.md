# END.DAT

## 1. Scope

`END.DAT` is fixed endgame narrative text used by the final presentation near
the end of the terminal sequence. It is not a map file, despite older inventory
labels that grouped it with map data. It is also not party-roster or retirement
lookup data. The Lord British confirmation and rite dialogue comes from
`ENDMSG.DAT`; the final certificate body is assembled from resident text
fragments and live save-state values.

This spec describes only the text file. The throne-room setup, confirmation
logic, party tableau, animations, final certificate, and no-return behavior are
specified in `systems/endgame.md`.

## 2. File Structure

The shipped file is 3,698 bytes of narrative text carrying the layout markers of section 3 — first-line indents, soft hyphens and hard line breaks. It carries **no page markers**: nothing in the file divides a record into separately presented pages, and the one-record-per-window binding of section 4 is the only pagination there is. Earlier revisions of this document described page or paragraph-start markers
and a closing brace; both are retracted — `{` is a first-line indent and the
file contains no `}` byte.

| Property | Value |
|---|---|
| Header | None observed |
| In-file offset table | None observed |
| Encoding | Plain low-ASCII text |
| Record terminator | NUL |
| Records | Six, plus two NUL bytes of tail padding |
| Paragraph-indent marker | `{`, eleven occurrences across the six records |
| Soft break marker | `_`, 139 occurrences |
| Hard break | Line feed, seven occurrences |

The runtime does not need a table inside `END.DAT`. The endgame presentation
records supply six fixed file-relative seek offsets. The consumer seeks to the
requested offset and reads a **fixed 2,000 bytes** into the shared scratch
buffer regardless of how long the record actually is; because the longest record
is 764 bytes, that is always an over-read, and the record's own NUL terminator
is what bounds the text the renderer consumes. A clean reader may either read
the exact record or replicate the fixed-length read — the rendered result is
identical — but it must not treat the read length as a record length.

Brace markers inside the selected window are layout markers for the renderer;
they are not a runtime ordinal section index by themselves. Any NUL padding in
the shipped asset is not a separate rendered page. The file likewise carries no
page-in transition rectangle table; visual transition ownership belongs to the
endgame display caller, not to `END.DAT` itself.

## 3. Text Markers

`END.DAT` uses the same proportional-text conventions observed in intro and
character-creation narrative files:

| Marker | Role |
|---|---|
| `{` | Paragraph first-line indent: draws no glyph and advances the pen 15 pixels |
| `_` | Soft hyphen: draws nothing and advances nothing, but marks a legal break point; a hyphen glyph is drawn only when the line actually breaks there |
| Line feed | Hard newline; also suppresses justification for the line it ends |

These markers are layout hints. They do not encode branching, flags, waits, or
animation commands by themselves.

**The brace is an indent, not a page break.** Earlier readings treated `{` as a
page or paragraph *boundary*. It is not: it produces a 15-pixel first-line
indent and nothing else, it never makes the renderer wait for input, and it
never splits a record into separately presented pages. The endgame presents one
record per window regardless of how many braces the record contains — records
4, 5 and 6 hold two, three and three braces respectively, and each is still a
single window. The full marker contract lives in `systems/text-output.md`
section 8.2.

**There is no closing-brace marker.** The shipped file contains no `}` byte at
all. Earlier revisions of this document referred to "brace markers (`{` and
`}`)"; the closing half of that is withdrawn.

## 4. Consumer Behavior

The traced endgame consumer is the fixed final-presentation helper that runs
after the Lord British message sequence and before the final certificate scroll.
That helper reuses the same scratch text buffer that previously held
`ENDMSG.DAT`, loads selected windows of `END.DAT` through the generic retrying
file-read helper, and renders them as narrative pages with endgame graphics.
The selected window is chosen by the current final-presentation control record.

`END.DAT` is a plain text file at rest, not an LZW-wrapped graphics archive and
not a driver-compressed bitmap resource. The consumer combines the loaded text
window with the proportional font, endgame graphics panels, and blocking waits.

The six fixed windows have the following clean semantic roles, with their byte-traced offsets in the shipped `END.DAT`:

| Window | Bytes | Length | Braces | Leading line feed | Role |
|---|---|---:|---:|---|---|
| 1 | `0..423` | 423 | 1 | no | Return-home opening at the circle of stones. |
| 2 | `424..955` | 531 | 1 | no | The Avatar's homecoming and laying down the long quest. |
| 3 | `956..1529` | 573 | 1 | **yes** | The restless night after returning home. |
| 4 | `1530..2279` | 749 | 2 | no | Blackthorn's closing judgment scene opens. |
| 5 | `2280..2931` | 651 | 3 | **yes** | Blackthorn's sentence and choice continues. |
| 6 | `2932..3696` | 764 | 3 | no | Orb/Gate exile resolution and final Blackthorn departure. |

Each window is a contiguous NUL-terminated ASCII text page. Records 3 and 5
open with a line feed *before* their first brace, so their first line of prose
sits one nine-pixel line advance below the pen origin the caller supplies; a
renderer that strips leading whitespace will place those two windows' text one
line too high.

A clean reader can either consume the table above as the canonical seek offsets
or walk the file by NUL boundaries (each non-trivial text segment longer than
ten bytes is one window, in order). Both approaches produce identical results
for the shipped asset. The two trailing NUL bytes after window 6 are padding,
not a seventh record.

The window index in this table is the same window index `systems/endgame.md`
section 8.1 uses to bind each record to its panel archive, slot, panel origin
and paragraph rectangle.

The file does not contain the Lord British yes/no dialogue; that text is in
`ENDMSG.DAT`. It also does not contain the final certificate template that uses
the party leader's name and saved date; that text is assembled from resident
strings and live save-state values.

## 5. Validation and Error Handling

A modern reader should require the file to be valid low-ASCII text and should
reject malformed text only if the renderer cannot advance through the selected
window. Tools may tolerate trailing NUL padding, but should not expose padding
as additional rendered prose.

If the endgame requests a seek window outside the asset, or if the selected
window does not contain renderable text, the runtime should report a missing
endgame-text asset error rather than continuing with a blank cinematic page.

## 6. Boundaries

The file-read mechanism and six narrative windows are known: `END.DAT` is
caller-windowed plain text. Visual page/panel parity in the endgame
presentation belongs to `systems/endgame.md`, and is now published there: each
window's panel archive, slot, panel size and origin, paragraph rectangle,
optional title strips and presentation model are in section 8. Nothing about
that binding lives in this file.

`END.DAT` remains separate from `ENDMSG.DAT`: the former is narrative page
text, while the latter is Lord British dialogue records.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/maps.md` (`END.DAT` reclassification and text-marker observations).
- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/functions/ENDGAME_OVL/` — the
  filename records a superseded reading; the function is the six-window
  narrative sequencer, not a roster lookup.
- `u5-decomp/functions/ENDGAME_OVL/`.
- `u5-decomp/notes/presentation_endgame_chargen_u4_2026-08-22.md` — the fixed
  read length, the brace-as-indent correction, the absence of a closing brace,
  the per-record brace counts and leading line feeds, and the binding of window
  index to the endgame presentation table.
- local binary checks against `C:\Games\U5-Clean\END.DAT` and `DATA.OVL` for
  the fixed presentation-window sequence and endgame asset table.
- `u5-spec/systems/endgame.md`.
- `u5-spec/systems/text-output.md`.
