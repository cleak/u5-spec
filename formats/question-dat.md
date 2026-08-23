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

- One opening gypsy-scene record and one post-question/result gypsy record.
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
| 1 | 1 | Post-question/result gypsy paragraph before save commit. |
| 2..29 | 28 | A/B virtue dilemma paragraphs. |

The shipped file ends immediately after the last record terminator. A reader
can enumerate records by scanning from the beginning of the file, splitting at
NUL bytes, and ignoring any empty trailing records if future data adds padding.

Record ordinals are semantic. Record 0 is addressed directly before the
tournament, record 1 is addressed directly after the tournament, and the
dilemma records are addressed indirectly: the chargen system resolves a virtue
pair to the byte offset of the corresponding record and then reads from that
position until the terminating NUL.

## 3. String Encoding and Markup

Text is plain ASCII with two lightweight markup conventions shared with the
intro narrative renderer:

| Byte | Meaning |
|---|---|
| `{` | First-line paragraph indent consumed by the proportional-font paragraph renderer: nothing is drawn and the pen advances a flat fifteen pixels. It is layout markup, not a visible glyph, and it is not a page break or an input wait. |
| `_` | Soft hyphen at a syllable break. Invisible and zero-width; it gives the renderer a legal wrap point inside a word, and a real hyphen glyph is drawn only when the line actually breaks there. The renderer never hyphenates on its own, so these markers must survive loading. |

Line-feed bytes, if present, should be treated as hard line breaks by the
renderer. NUL terminates the current record and is not rendered.

The file is not XOR-obfuscated and does not use the common-word dictionary used
by conversation and shop text. Bytes are read as authored text plus the markup
above. The shipped IBM PC file contains no high-bit bytes and no control bytes
other than NUL and line-feed. A byte-compatible content set should preserve
that plain-text profile.

## 4. Dilemma Indexing

The game has eight virtues numbered by the chargen system. The public chargen
spec identifies the observed order as the canonical Britannian virtue order.
`QUESTION.DAT` does not store those names or numbers; it only stores the
paragraphs selected by the chargen logic.

For each question, the chargen system:

1. Selects two distinct virtues still eligible in the tournament. The first
   selected virtue is marked as selected before the second draw, so a virtue
   cannot be paired with itself.
2. Sorts the pair for stable A/B presentation.
3. Looks up the pair in a resident symmetric pair-to-question table.
4. Seeks to the selected `QUESTION.DAT` record.
5. Renders the paragraph and waits for an A or B answer.

There are twenty-eight dilemma records because eight virtues have twenty-eight
unique unordered pairings. The diagonal "virtue paired with itself" case does
not occur and has no record.

The record order in the file should not be treated as a simple formula unless
the resident pair table has been consulted. For the shipped IBM PC data, that
table resolves to this clean record-ordinal mapping:

| Record | Virtue pair |
|---:|---|
| 2 | Honesty / Compassion |
| 3 | Honesty / Valor |
| 4 | Honesty / Justice |
| 5 | Honesty / Sacrifice |
| 6 | Honesty / Honor |
| 7 | Honesty / Spirituality |
| 8 | Honesty / Humility |
| 9 | Compassion / Valor |
| 10 | Compassion / Justice |
| 11 | Compassion / Sacrifice |
| 12 | Compassion / Honor |
| 13 | Compassion / Spirituality |
| 14 | Compassion / Humility |
| 15 | Valor / Justice |
| 16 | Valor / Sacrifice |
| 17 | Valor / Honor |
| 18 | Valor / Spirituality |
| 19 | Valor / Humility |
| 20 | Justice / Sacrifice |
| 21 | Justice / Honor |
| 22 | Justice / Spirituality |
| 23 | Justice / Humility |
| 24 | Sacrifice / Honor |
| 25 | Sacrifice / Spirituality |
| 26 | Sacrifice / Humility |
| 27 | Honor / Spirituality |
| 28 | Honor / Humility |
| 29 | Spirituality / Humility |

The diagonal table cells are unreachable because a virtue is marked selected
before the second draw. A modern implementation can use the ordinal table above
directly, or can reproduce the original symmetric lookup as long as it resolves
to the same records.

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
It also does not encode pacing or cancellation rules. The two introductory
records advance on any key after rendering, and A/B question records wait for
the questionnaire driver's accepted answer keys; those behaviours are runtime
flow rules, not file-format fields.

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

## 9. Variant Boundary

The shipped file uses only the markup conventions described above. Repeated
markers, markers at end of record, and high-bit bytes do not occur in the
shipped file. Tooling should reject or explicitly flag those bytes in strict
compatibility mode rather than assigning them new runtime meaning.

## 10. Sources

This cleanroom spec was derived from the following private analysis notes. No
decompiled code, assembly, raw address tables, or copied questionnaire prose are
reproduced here. Existing public specs were used only for terminology and
cross-reference alignment.

- The `QUESTION.DAT` file size, thirty-record layout, introductory-versus-
  dilemma split, NUL-terminated record structure, markup conventions, and
  consumer attribution -- derived from `u5-decomp/formats/data-tables.md`.
- The chargen flow, virtue tournament, pair-table selection semantics,
  pair-to-record ordinal mapping, proportional-font renderer role, stat
  effects, and save-writing context --
  derived from `u5-decomp/functions/FONT_OVL/`, and
  `u5-decomp/functions/FONT_OVL/`.
