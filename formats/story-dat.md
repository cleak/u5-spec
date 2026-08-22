# STORY.DAT

## 1. Scope

`STORY.DAT` contains the proportional-font narrative text for the Ultima V
Introduction path reached from the intro menu. It is paired with the story art
slides, but it stores only text. Graphics, palette changes, screen placement,
special inline lines, and slide timing are owned by the intro and rendering
systems.

The format is intentionally simple: a run of page records using the same
paragraph markers as the character-creation question text.

## 2. File Structure

The shipped file is 11,679 bytes and contains twenty non-empty text records.
Records are stored back to back, with no header and no offset table **inside
the file**. The reader does not scan for them: the intro carries a fixed table
of byte positions, one entry per text-consuming story step, and seeks straight
to the position it needs.

| Element | Meaning |
|---|---|
| Text record | A NUL-terminated low-ASCII paragraph/page stream |
| End of record | NUL byte |
| End of file | Two NUL bytes after the final non-empty record in the shipped data |
| Record addressing | Absolute byte position, supplied per story step by the intro |

For the shipped asset the twenty positions are exactly the twenty records in
file order, so a reader that simply splits the file on NUL bytes and indexes
the resulting list produces identical results. The distinction matters only for
the bookkeeping question: because each step names its own position, a step that
consumes no record cannot desynchronise the steps that follow it.

The file does not carry per-slide filenames, art ids, rectangles, colours, or
wait durations. The intro system supplies those from its fixed story-step
contract.

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

The intro menu's Introduction option plays a twenty-one-step story sequence.
For each text-consuming step, the intro path loads or selects the
corresponding art panel, seeks to that step's fixed byte position in
`STORY.DAT`, reads a fixed-size window of two kilobytes into a shared scratch
buffer, renders the art, renders the proportional text up to the first NUL, and
then advances according to the intro system's step rules. The two-kilobyte read
is larger than any record and smaller than the scratch buffer; the terminator,
not the read length, ends the record.

The sequence contains one visual step that does not read `STORY.DAT` at all:
step 6 uses two inline doorway-transition lines owned by the intro code and
specified in `systems/intro.md` section 10.1. The remaining twenty steps read
the twenty non-empty `STORY.DAT` records, and in the shipped data those
positions are the records in file order. Step 0 reads the first record but
advances automatically; the later text-consuming steps wait for a key in the
intro system before advancing.

Because addressing is by fixed per-step position rather than by a running
cursor, an implementation needs no "next record" state. Step 6 leaves nothing
to skip, and a missing or reordered record affects only the step that names it.

The complete step-to-art mapping, secondary art draws, transition effects, and
the exact text and placement of the non-consuming step-6 lines belong to
`systems/intro.md`. This file's contract is only that the twenty records are
read, one per text-consuming story step, by absolute byte position.

`STORY.DAT` does not mutate game state. Playing the sequence returns to the
intro menu afterward. No save file is created or modified.

## 5. Validation and Error Handling

A reader should treat records as sequential and bounded by NUL bytes. For a
faithful data set, expect twenty non-empty records followed by an empty trailer.
If fewer than twenty records are available, a modern
implementation should fail the asset load or show a missing-page diagnostic
rather than reading into later memory.

Unknown printable bytes should be passed through to the proportional-font
renderer. Unknown control bytes should be rejected by tooling or displayed by
the renderer's normal fallback policy; the shipped content is plain text plus
the markers listed above.

## 6. System Boundaries

No file-layout work remains for the shipped DOS data set. The twenty-record
sequential layout, supported text markers, non-consuming doorway step, and
record order are public.

The step-1 transition is no longer an open item: it is a pseudo-random
per-pixel dissolve of a fixed rectangle, specified in `systems/intro.md`
section 10. Nothing about it affects `STORY.DAT` parsing or record order.

The empty final trailer is padding or a sentinel. It has no known gameplay
meaning and should not be exposed as a twenty-first story page.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`STORY.DAT` section).
- `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- `u5-spec/systems/intro.md`.
- `u5-spec/systems/text-output.md`.
