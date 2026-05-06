# MISCMSG.DAT

## 1. Scope

`MISCMSG.DAT` is a shared message file for small scripted scenes and virtue
presentation text that do not have a more specific data file. Known consumers
include Blackthorn audience or rescue paths, shrine or virtue flows, and Codex
or prophecy-style pages.

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

Consumers address records by hardcoded ordinal or by an external table. The
file itself does not label records by scene, virtue, or caller.

## 3. Record Families

The known record clusters are:

| Records | Role |
|---|---|
| 0-11 | Blackthorn mantra interrogation and related audience text |
| 12-19 | Virtue-failing or weakness phrases keyed by the eight virtues |
| 20-27 | Virtue aphorism paragraphs keyed by the eight virtues |
| 28-35 | Shrine meditation prompts and related altar or offering text |
| 36-46 | Codex revelation or prophecy pages, including tile-glyph text |

The record-family boundaries are observations from the source notes. The file
does not contain family headers.

## 4. Text and Glyph Encoding

Most records are plain low-ASCII text and use ordinary line feeds where a
caller wants fixed breaks.

Some Codex or prophecy records use the same tile-glyph convention observed in
sign text:

| Glyph byte | Meaning |
|---|---|
| `@` | Inter-word space in tile-glyph text |
| `[` | `TH` digraph |
| `]` | `NG` digraph |
| `_` | `ER` digraph |

These glyph records are intended for a tile/sign-style renderer, not the
ordinary prose printer. A reader should keep the record's bytes intact and let
the caller choose the correct renderer.

## 5. Consumer Behavior

`MISCMSG.DAT` is loaded into a scratch buffer by scene handlers that need the
current cluster. The caller chooses a record, sends it to either the ordinary
text-output pipeline or the tile-glyph renderer, and performs any prompt,
virtue check, flag update, or animation separately.

The file does not encode branching, karma adjustments, shrine outcomes, Codex
state, or Blackthorn punishment logic. It only provides the text shown by
those flows.

## 6. Validation and Error Handling

A full shipped-compatible asset should contain forty-seven records. Tools
should reject unterminated records and should preserve the raw bytes of
tile-glyph records rather than normalizing them as prose.

If a consumer requests a record outside the available count, a modern
implementation should report a missing-message error. Falling through to the
next family can produce misleading virtue or Codex text.

## 7. Known Uncertainties

- Not every record's exact caller has been mapped.
- The tile-glyph renderer shared by signs and Codex-style records still needs
  a complete public spec.
- The Blackthorn and shrine clusters are record-indexed, but the external
  lookup rules remain partly in code notes rather than public data tables.

## 8. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`MISCMSG.DAT` section).
- `u5-decomp/functions/BLCKTHRN_OVL/0x060E_blackthorn_audience.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/OVERVIEW.md`.
- `u5-spec/systems/karma.md`.
- `u5-spec/systems/endgame.md`.
- `u5-spec/systems/text-output.md`.
