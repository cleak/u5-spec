# MISCMSG.DAT

## 1. Scope

`MISCMSG.DAT` is a shared message file for small scripted scenes and virtue
presentation text that do not have a more specific data file. Traced consumers
are the Blackthorn capture audience, shrine meditation and virtue presentation,
and the urn/Codex prophecy flow.

The file is a message table, not a script language. Record selection and side
effects are owned by the calling systems.

## 2. File Structure

The shipped file is 2,745 bytes and contains forty-seven NUL-terminated
records stored sequentially.

| Property | Value |
|---|---|
| Header | None |
| Offset table | None in the file |
| Record count | Forty-seven in the shipped data |
| Record terminator | NUL byte |
| Encodings | Plain ASCII records plus tile-glyph records for Codex-style pages |

Consumers address records by hardcoded ordinal, loaded-window offset, or an
external pointer table. The file itself does not label records by scene,
virtue, or caller.

## 3. Record Families

The known record clusters are:

| Records | Primary owner | Role |
|---|---|---|
| 0-11 | Blackthorn capture audience | Challenge templates, audience prompts, and related punishment/release presentation text |
| 12-19 | Shrine and virtue presentation | Virtue-failing or weakness phrases keyed by the eight virtues |
| 20-27 | Codex virtue reading | One aphorism per virtue, Honesty through Humility in canonical order |
| 28-36 | Shrine meditation | Meditation prompts, altar text, offering text, and ordained/quest turn-in presentation |
| 37-38 | Codex reading | Shared book-open and page-introduction preambles, independent of quest state |
| 39 | Codex reading | Result when no virtue is ordained |
| 40 | Codex completion | Page-turn transition, printed once before the shared completion pages |
| 41-44 | Codex completion | Four shared runic pages, presented sequentially when the selected virtue leaves the read mask complete |
| 45 | Shrine entry | Approach narration before the kneeling and virtue-input records |
| 46 | Codex entry | Approach narration for the Codex presentation |

The earlier classification of the entire final group as Codex revelation or
prophecy text is withdrawn for record 45 (`RETRACTIONS.md` R417). Its shrine
entry use was freshly verified under `u5-decomp/functions/CAST2_OVL/`.

The earlier Codex classification of record 36 is also withdrawn: it is the
shrine's Codex-read quest turn-in response (`RETRACTIONS.md` R423), confirmed
by fresh resource selection and isolated original-code execution under
`u5-decomp/notes/`.

The record-family boundaries are consumer contracts, not in-file structure. The
Blackthorn audience loads the front cluster as its temporary message source.
The shrine path loads the later message window before dispatching either shrine
meditation or urn reading. Codex reading selects an ordained virtue's aphorism
from `20`–`27`; the `37`–`44` cluster is not an eight-entry virtue selector.
`systems/karma.md` Sections 8.1 and 8.2 specify the first-ordained selection,
shared completion extension and three/four/nine-key presentation paths.

The exact one-line ordinal-to-English mapping is intentionally not duplicated
here. Implementations should treat the shipped file as authored content and use
the owning system's selector rather than trying to infer gameplay behavior from
message text.

## 4. Text and Glyph Encoding

Most records are plain low-ASCII text and use ordinary line feeds where a
caller wants fixed breaks.

Some Codex or prophecy records use the same tile-glyph convention observed in
sign-style text:

| Glyph byte | Meaning |
|---|---|
| `@` | Inter-word space in tile-glyph text |
| `[` | `TH` digraph |
| `]` | `NG` digraph |
| `_` | `ER` digraph |

For Codex records `41`–`44`, the caller selects the runic font and uses the
ordinary fixed-window message printer, then restores the normal font before
the following key wait. Keep the authored glyph stream and line separators
intact. The related glyph convention in `formats/signs-dat.md` does not make
these records sign streams or require that parser.
The earlier direction to use a separate Codex/sign-style display path rather
than the ordinary message printer is retracted (`RETRACTIONS.md` R453).

## 5. Consumer Behavior

`MISCMSG.DAT` is loaded into a scratch buffer by scene handlers that need the
current cluster. The caller chooses a record, prints it with the appropriate
active font, and performs any prompt, virtue check, flag update, or animation
separately. Codex runic pages share the fixed-window text-output path; their
font selection is part of the Codex caller's presentation contract.

The file does not encode branching, karma adjustments, shrine outcomes, Codex
state, or Blackthorn punishment logic. It only provides the text shown by
those flows.

Public consumer contracts:

| Consumer | MISCMSG role |
|---|---|
| `systems/blackthorn.md` | Loads the audience cluster for capture/challenge prompts and related presentation strings. The challenge answer words are selected from resident virtue/Word tables, not from `MISCMSG.DAT`. |
| `systems/karma.md` | Owns shrine meditation, virtue aphorism/failing text, and the ordained/Codex-read state transitions that decide which virtue text can be shown. |
| `catalogs/quest-graph.md` | Describes the quest-state effect of the urn/Codex flow: ordained virtues become Codex-read when the corresponding urn page is read. |
| `systems/text-output.md` | Owns ordinary fixed-window text printing. Codex runic pages use that same message window with a caller-selected font. |

## 6. Validation and Error Handling

A full shipped-compatible asset should contain forty-seven records. Tools
should reject unterminated records and should preserve tile-glyph records
unchanged rather than normalizing them as prose.

If a consumer requests a record outside the available count, a modern
implementation should report a missing-message error. Falling through to the
next family can produce misleading virtue or Codex text.

## 7. Compatibility Boundaries

No file-layout work remains for the shipped DOS data set. The sequential
forty-seven-record layout, record-family ownership, and plain-text versus
tile-glyph rendering boundary are public.

Codex presentation order, input waits and font selection are specified in
`systems/karma.md` Section 8. Preserve the stored glyph bytes and apply the
ordinary message-window layout with the selected font.

Individual record ordinals inside each family are data-authored content. A
modern content tool may expose them for editing, but gameplay code should
depend on the owning system's selector contract rather than hardcoded prose.

## 8. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`MISCMSG.DAT` section).
- `u5-decomp/functions/BLCKTHRN_OVL/`.
- `u5-decomp/functions/BLCKTHRN_OVL/OVERVIEW.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/`.
- `u5-decomp/functions/CAST2_OVL/`.
- `u5-spec/systems/karma.md`.
- `u5-spec/systems/blackthorn.md`.
- `u5-spec/systems/text-output.md`.

The Codex record map and font use were freshly verified for issue #253 from
original caller/data traces and 1,047 controlled original-code cases under
`u5-decomp/functions/CAST2_OVL/`, `u5-decomp/functions/ULTIMA_EXE/` and
`u5-decomp/notes/`. These cases establish selection and ordering, not rendered
frame timing.
