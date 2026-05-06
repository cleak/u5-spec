# STORY.DAT

## 1. Scope

`STORY.DAT` contains the proportional-font narrative text for the Ultima V
Introduction path reached from the intro menu. It is paired with the story art
slides, but it stores only text. Graphics, palette changes, screen placement,
and slide timing are owned by the intro and rendering systems.

The format is intentionally simple: a run of page records using the same
paragraph markers as the character-creation question text.

## 2. File Structure

The shipped file is 11,679 bytes and contains twenty non-empty text records.
Records are stored sequentially, with no header and no offset table.

| Element | Meaning |
|---|---|
| Text record | A NUL-terminated low-ASCII paragraph/page stream |
| End of record | NUL byte |
| End of file | Two NUL bytes after the final non-empty record in the shipped data |
| Record order | Intro slide order, selected by the intro slide loop |

The file does not carry per-slide filenames, art ids, rectangles, colours, or
wait durations. The intro system supplies those from code and resident tables.

## 3. Text Markers

The record payload is plain ASCII with a few renderer-visible markers:

| Marker | Role |
|---|---|
| `{` | Paragraph or page-start marker used by the proportional-font renderer's callers. It is not displayed as a glyph. |
| `_` | Soft hyphen or syllable-break marker. It permits a line break but is not rendered as an underscore. |
| Line feed | Hard newline inside the current record. |
| NUL | End of the current story record. |

The `{` marker usually appears at the start of a record. The renderer walks
past it and continues layout; the caller owns the actual wait-for-key or slide
advance behavior.

## 4. Consumer Behavior

The intro menu's Introduction option plays the story sequence. For each slide,
the intro path loads or selects the corresponding art panel, selects the next
`STORY.DAT` text record, renders the art, renders the proportional text, waits
for the player to advance, and then proceeds to the next slide.

`STORY.DAT` does not mutate game state. Playing the sequence returns to the
intro menu afterward. No save file is created or modified.

## 5. Validation and Error Handling

A reader should treat records as sequential and bounded by NUL bytes. For a
faithful data set, expect twenty non-empty records followed by an empty trailer.
If fewer records are available than the intro sequence requests, a modern
implementation should fail the asset load or show a missing-page diagnostic
rather than reading into later memory.

Unknown printable bytes should be passed through to the proportional-font
renderer. Unknown control bytes should be rejected by tooling or displayed by
the renderer's normal fallback policy; the shipped content is plain text plus
the markers listed above.

## 6. Known Uncertainties

- The exact slide-to-record pacing, transition timing, and text placement are
  intro-system concerns and are not fully specified by this file.
- The record reader is known behaviorally, but the exact location of every
  loader call remains partly open in the intro notes.
- The empty final trailer is best treated as a sentinel or padding; no
  gameplay meaning is known.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`STORY.DAT` section).
- `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- `u5-spec/systems/intro.md`.
- `u5-spec/systems/text-output.md`.
