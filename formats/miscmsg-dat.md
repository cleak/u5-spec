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
| 20-27 | Shrine and virtue presentation | Virtue aphorism paragraphs keyed by the eight virtues |
| 28-35 | Shrine meditation | Meditation prompts, altar text, offering text, and ordained/quest presentation |
| 36-46 | Urn/Codex prophecy | Codex revelation or prophecy pages, including tile-glyph text |

The record-family boundaries are consumer contracts, not in-file structure. The
Blackthorn audience loads the front cluster as its temporary message source.
The shrine path loads the later message window before dispatching either shrine
meditation or urn reading. The urn reader then selects Codex prophecy text from
that loaded window through its virtue-specific pointer table.

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

These glyph records are intended for a Codex/sign-style display path, not the
ordinary prose printer. A reader should keep the record's bytes intact and let
the caller choose the correct renderer. See `formats/signs-dat.md` for the
closely related sign-stream formatter; `MISCMSG.DAT` itself only supplies the
message bytes.

## 5. Consumer Behavior

`MISCMSG.DAT` is loaded into a scratch buffer by scene handlers that need the
current cluster. The caller chooses a record or loaded-window offset, sends it
to either the ordinary text-output pipeline or the tile-glyph renderer, and
performs any prompt, virtue check, flag update, or animation separately.

The file does not encode branching, karma adjustments, shrine outcomes, Codex
state, or Blackthorn punishment logic. It only provides the text shown by
those flows.

Public consumer contracts:

| Consumer | MISCMSG role |
|---|---|
| `systems/blackthorn.md` | Loads the audience cluster for capture/challenge prompts and related presentation strings. The challenge answer words are selected from resident virtue/Word tables, not from `MISCMSG.DAT`. |
| `systems/karma.md` | Owns shrine meditation, virtue aphorism/failing text, and the ordained/Codex-read state transitions that decide which virtue text can be shown. |
| `catalogs/quest-graph.md` | Describes the quest-state effect of the urn/Codex flow: ordained virtues become Codex-read when the corresponding urn page is read. |
| `systems/text-output.md` | Owns ordinary fixed-window text printing. Codex tile-glyph presentation is a caller-selected rendering mode layered above the raw message table. |

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

Exact visual parity for the Codex tile-glyph presentation still depends on the
display/layout contract for that caller. The message-file contract is stable:
preserve the tile-glyph bytes and let the caller render them.

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
