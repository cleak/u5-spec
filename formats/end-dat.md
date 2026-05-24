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

The shipped file is 3,698 bytes of narrative text with page/paragraph markers.

| Property | Value |
|---|---|
| Header | None observed |
| In-file offset table | None observed |
| Encoding | Plain low-ASCII text |
| Primary marker | `{` marker at the start of a narrative page or paragraph |
| Soft break marker | `_` |

The runtime does not need a table inside `END.DAT`. The endgame presentation
records supply six fixed file-relative seek windows. The consumer reads the
selected bounded window into the shared scratch buffer and then hands that
window to the proportional text renderer. Brace markers inside the selected
window are layout markers for the renderer or its caller; they are not a
runtime ordinal section index by themselves. Any NUL padding in the shipped
asset is not a separate rendered page. The file likewise carries no page-in
transition rectangle table; visual transition ownership belongs to the endgame
display caller, not to `END.DAT` itself.

## 3. Text Markers

`END.DAT` uses the same proportional-text conventions observed in intro and
character-creation narrative files:

| Marker | Role |
|---|---|
| `{` | Page or paragraph-start marker; not displayed as a literal glyph |
| `_` | Soft hyphen or syllable-break marker used by line layout |
| Line feed | Hard newline where present |

These markers are layout hints. They do not encode branching, flags, waits, or
animation commands by themselves.

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

| Window | Bytes | Length | Role |
|---|---|---:|---|
| 1 | `0..423` | 423 | Return-home opening at the circle of stones. |
| 2 | `424..955` | 531 | The Avatar's homecoming and laying down the long quest. |
| 3 | `956..1529` | 573 | The restless night after returning home. |
| 4 | `1530..2279` | 749 | Blackthorn's closing judgment scene opens. |
| 5 | `2280..2931` | 651 | Blackthorn's sentence and choice continues. |
| 6 | `2932..3696` | 764 | Orb/Gate exile resolution and final Blackthorn departure. |

Each window is a contiguous NUL-terminated ASCII text page. Brace markers (`{` and `}`) inside each page are layout hints for the proportional text renderer (line-break helpers), not page boundaries. A clean reader can either consume the table above as the canonical seek windows or walk the file by NUL boundaries (each non-trivial text segment longer than ten bytes is one window, in order). Both approaches produce identical results for the shipped asset.

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
presentation belongs to `systems/endgame.md`; it is not a file-layout gap.

`END.DAT` remains separate from `ENDMSG.DAT`: the former is narrative page
text, while the latter is Lord British dialogue records.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/maps.md` (`END.DAT` reclassification and text-marker observations).
- `u5-decomp/functions/ULTIMA_EXE/0x82DE_load_lzw_image.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x7234_read_file_seek.md`.
- `u5-decomp/functions/ENDGAME_OVL/0x0000_endgame_load_party_roster.md`.
- `u5-decomp/functions/ENDGAME_OVL/0x0648_endgame_entry.md`.
- local binary checks against `C:\Games\U5-Clean\END.DAT` and `DATA.OVL` for
  the fixed presentation-window sequence and endgame asset table.
- `u5-spec/systems/endgame.md`.
- `u5-spec/systems/text-output.md`.
