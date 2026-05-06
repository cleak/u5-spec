# END.DAT

## 1. Scope

`END.DAT` is endgame narrative text. It is not a map file, despite older
inventory labels that grouped it with map data. The endgame system uses it as
part of the terminal presentation alongside `ENDMSG.DAT`, endgame bitmap
assets, and resident certificate text.

This spec describes only the text file. The throne-room setup, confirmation
logic, party tableau, animations, final certificate, and no-return behavior are
specified in `systems/endgame.md`.

## 2. File Structure

The shipped file is 3,698 bytes of printable narrative text divided by
paragraph or frame markers.

| Property | Value |
|---|---|
| Header | None observed |
| In-file offset table | None observed |
| Encoding | Plain low-ASCII text |
| Primary separator | `{` marker at the start of narrative sections |
| Soft break marker | `_` |

The file is best modeled as an ordered sequence of narrative frames or pages.
Each section begins with a `{` marker and contains prose for the proportional
text renderer. The exact count of endgame frames and their one-to-one mapping
to visual beats remain less certain than the simpler `ENDMSG.DAT` record
table.

## 3. Text Markers

`END.DAT` uses the same proportional-text conventions observed in intro and
character-creation narrative files:

| Marker | Role |
|---|---|
| `{` | Section or page-start marker; not displayed as a literal glyph |
| `_` | Soft hyphen or syllable-break marker used by line layout |
| Line feed | Hard newline where present |

These markers are layout hints. They do not encode branching, flags, waits, or
animation commands by themselves.

## 4. Consumer Behavior

The endgame loader reads `END.DAT` through the same generic data-file helper
used for other endgame resources. The endgame presentation can then select a
section, render it with the proportional-font or page renderer, and combine it
with bitmap panels and scripted waits.

The file does not contain the Lord British yes/no dialogue; that text is in
`ENDMSG.DAT`. It also does not contain the final certificate template that uses
the party leader's name and saved date; that text is assembled from resident
strings and live save-state values.

## 5. Validation and Error Handling

A modern reader should require the file to be valid low-ASCII text and should
reject an unterminated or malformed section only if the renderer cannot advance
to the next page. Because the exact section count is not yet public, tools
should avoid hard-failing on a count mismatch unless they are verifying the
shipped DOS asset.

If the endgame requests a page that cannot be found, the runtime should report
a missing-endgame-text asset error rather than continuing with a blank
cinematic page.

## 6. Known Uncertainties

- The exact number of rendered sections and their mapping to endgame visual
  beats remain open.
- The notes classify the file confidently as text, but the precise caller-side
  indexing or seek table has not been fully published.
- `END.DAT` should remain separate from `ENDMSG.DAT`: the former is narrative
  page text, while the latter is Lord British dialogue records.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/maps.md` (`END.DAT` reclassification and text-marker observations).
- `u5-decomp/functions/ULTIMA_EXE/0x82DE_load_lzw_image.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x7234_read_file_seek.md`.
- `u5-decomp/functions/ENDGAME_OVL/0x0648_endgame_entry.md`.
- `u5-spec/systems/endgame.md`.
- `u5-spec/systems/text-output.md`.
