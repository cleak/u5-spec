# QUESTION.DAT

Format specification for `QUESTION.DAT`, the character-creation questionnaire
text file. The file stores the gypsy introduction and the virtue-dilemma
paragraphs used when creating a new avatar.

## 1. Overview

`QUESTION.DAT` is the text content for the questionnaire portion of character
creation. The character-creation system asks the player a sequence of A-or-B
virtue dilemmas, uses the answers to accumulate stat deltas, then writes the
new avatar into the seed-loaded save image. This file supplies the paragraphs;
it does not contain the virtue list, stat deltas, tournament state, random
selection logic, answer handling, or save-writing code.

The file is a simple sequence of NUL-terminated text records:

- Two introductory records for the gypsy scene.
- Twenty-eight dilemma records, one for each unordered pair of the eight
  Britannian virtues.

The pairing from two virtue ids to a specific dilemma record is supplied by a
resident lookup table used by the character-creation code. It is not stored in
`QUESTION.DAT` itself.

## 2. File Layout

The file contains thirty nonempty records in order. Each record is a
NUL-terminated byte string. There is no file header, magic number, version
field, count word, offset table, per-record length, checksum, or compression.

| Record range | Count | Purpose |
|---|---:|---|
| 0 | 1 | Gypsy-scene arrival narrative. |
| 1 | 1 | Gypsy invitation and setup for the questions. |
| 2..29 | 28 | A/B virtue dilemma paragraphs. |

The shipped file ends immediately after the last record terminator. A reader
can enumerate records by scanning from the beginning of the file, splitting at
NUL bytes, and ignoring any empty trailing records if future data adds padding.

Record ordinals are semantic. The two introductory records are addressed by
their fixed positions. The dilemma records are addressed indirectly: the
chargen system resolves a virtue pair to the byte offset of the corresponding
record and then reads from that position until the terminating NUL.

## 3. String Encoding and Markup

Text is plain ASCII with two lightweight markup conventions shared with the
intro narrative renderer:

| Byte | Meaning |
|---|---|
| `{` | Paragraph/page-start marker consumed by the proportional-font paragraph renderer. It is layout markup, not a visible glyph. |
| `_` | Soft hyphen or syllable-break marker. It gives the renderer an additional wrap point inside a word and is not normally emitted as an underscore glyph. |

Line-feed bytes, if present, should be treated as hard line breaks by the
renderer. NUL terminates the current record and is not rendered.

The file is not XOR-obfuscated and does not use the common-word dictionary used
by conversation and shop text. Bytes are read as authored text plus the markup
above.

## 4. Dilemma Indexing

The game has eight virtues numbered by the chargen system. The public chargen
spec identifies the observed order as the canonical Britannian virtue order.
`QUESTION.DAT` does not store those names or numbers; it only stores the
paragraphs selected by the chargen logic.

For each question, the chargen system:

1. Selects two distinct virtues still eligible in the tournament.
2. Sorts the pair for stable A/B presentation.
3. Looks up the pair in a resident symmetric pair-to-question table.
4. Seeks to the selected `QUESTION.DAT` record.
5. Renders the paragraph and waits for an A or B answer.

There are twenty-eight dilemma records because eight virtues have twenty-eight
unique unordered pairings. The diagonal "virtue paired with itself" case does
not occur and has no record.

The record order in the file should not be treated as a simple formula such as
"all pairs in row-major order" unless the resident pair table has been
consulted. The pair table is the source of truth for which record belongs to
which virtue pairing.

## 5. Loading Behaviour

The original character-creation flow reads slices rather than loading the whole
file as a parsed table. For each paragraph it seeks to the selected record
offset, reads enough bytes into a scratch buffer to cover the largest shipped
record, and lets the proportional-font renderer consume bytes until NUL.

A modern implementation may load and split the entire file up front. To keep
the same semantics, it should preserve:

- Thirty nonempty records.
- Fixed introductory records at ordinals zero and one.
- Dilemma records at ordinals two through twenty-nine.
- Markup handling for `{`, `_`, line feed, and NUL.
- External pair-table selection rather than deriving pair mapping from prose.

The file does not encode the A/B answer effects. It is valid for a dilemma
paragraph to mention options A and B, but the engine decides which virtue wins
from the sorted pair and the key pressed, not from parsing the paragraph text.

## 6. Rendering Behaviour

`QUESTION.DAT` is rendered by the character-creation proportional-font paragraph
renderer, not by the normal fixed-cell text-window printer used for most
in-game messages.

The renderer is responsible for:

- Consuming the paragraph-start marker.
- Treating soft hyphen markers as internal wrap opportunities.
- Wrapping prose to the active chargen text area.
- Pausing between introductory paragraphs and questions according to the
  chargen flow.
- Returning the selected answer key to the questionnaire driver for A/B
  questions.

The file itself does not specify screen coordinates, font metrics, colours,
card art, virtue option positions, random order, or persistence. Those belong
to `systems/chargen.md` and the graphics assets used by character creation.

## 7. Validation and Error Handling

A content validator should check:

- The file contains at least thirty nonempty NUL-terminated records.
- Records zero and one exist before any dilemma selection can run.
- Records two through twenty-nine exist for all twenty-eight virtue pairings.
- Every referenced pair-table offset lands on the start of one of those
  records.
- Each record terminates before the reader's maximum paragraph buffer.
- Markup bytes are limited to conventions the paragraph renderer understands.

For runtime robustness:

- A missing introductory record should abort character creation before writing a
  save.
- A missing dilemma record should abort the questionnaire or substitute a clear
  internal-error message; it should not silently select a different virtue
  pairing.
- A malformed record without a NUL terminator should be rejected rather than
  allowing the renderer to read into following records.

## 8. Cross-References

- `systems/chargen.md` describes the questionnaire tournament, virtue order,
  stat accumulation, seed-save loading, and persistence.
- `systems/text-output.md` describes the normal fixed-cell text system. It is
  useful context, but `QUESTION.DAT` uses the chargen paragraph renderer rather
  than the ordinary in-game text windows.

## 9. Open Questions

- **Complete pair table transcription.** The existence and role of the
  symmetric virtue-pair table are understood, but this format spec does not
  publish a byte-exact table. A future public appendix could name each
  virtue-pair-to-record mapping in prose after it is re-derived cleanly.
- **Pacing details.** The broad paragraph-pacing model is known, but the exact
  key handling for the introductory records and whether any cancel key is
  accepted should be confirmed in gameplay.
- **Markup edge cases.** The `{` and `_` conventions are understood for shipped
  content. Behaviour for repeated markers, markers at end of record, or unknown
  high-bit bytes is not yet specified.

## 10. Sources

This cleanroom spec was derived from the following private analysis notes. No
decompiled code, assembly, raw address tables, or copied questionnaire prose are
reproduced here. Existing public specs were used only for terminology and
cross-reference alignment.

- The `QUESTION.DAT` file size, thirty-record layout, introductory-versus-
  dilemma split, NUL-terminated record structure, markup conventions, and
  consumer attribution -- derived from `u5-decomp/formats/data-tables.md`.
- The chargen flow, virtue tournament, pair-table selection semantics,
  proportional-font renderer role, stat effects, and save-writing context --
  derived from `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`,
  `u5-decomp/functions/FONT_OVL/0x09C8_questionnaire_iter.md`,
  `u5-decomp/functions/FONT_OVL/0x0998_pick_random_unused_virtue.md`, and
  `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
