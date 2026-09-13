# KARMA.DAT

## 1. Scope

`KARMA.DAT` is a small text resource used by traced moral-verdict
presentation paths: Blackthorn rescue/refuge and the Lord British-in-disguise
camp event. Despite its name, it is not the table of karma adjustments for
player actions. Karma gains, losses, thresholds, and quest gates are owned by
code and save-state fields described in `systems/karma.md`.

This file supplies player-facing verdict speeches. A consumer chooses a record
according to a computed moral-standing tier and prints that text through the
normal text-output path.

## 2. File Structure

The file is a sequential string table:

| Property | Value |
|---|---|
| File size | 761 bytes in the shipped DOS data set |
| Header | None |
| Offset table | None in the file |
| Record count | Six text records |
| Record terminator | NUL byte |
| Encoding | Plain low-ASCII text |
| Trailer | Ends after the final record terminator |

Records are packed back-to-back, and the file itself stores no tier
thresholds, virtue ids, standing values, or record offsets.

**How the original reads a record.** It does not walk the file. The consumer
holds the five band start positions itself, seeks straight to the selected
one, and issues **one fixed-length request** - two thousand bytes, from a
761-byte file - into a scratch buffer. The request therefore always reads to
end of file and always returns fewer bytes than asked for, and the printed
record is delimited by its own NUL terminator, not by the length read. A reader
that validates the requested length, or that treats a short read as an error,
diverges from the original on every verdict it prints. *(Corrected 2026-09-12,
issue #269: this paragraph previously said a reader "starts at the beginning of
the file and skips `n` NUL-terminated records". That description is withdrawn -
`RETRACTIONS.md` R495. Skipping terminators yields the same five record bodies
for the five defined bands, which is why the difference went unnoticed; it does
not yield the same behaviour for a short read, a truncated asset, or an
out-of-range band.)*

A modern implementation is free to index a parsed list of six strings instead,
provided it accepts a file whose final record runs to end of file and does not
require a fixed record length.

## 3. Record Semantics

The six records are ordered from lowest moral standing to highest moral
standing. The first records are corrective speeches for an Avatar who has
fallen away from the virtue being judged. The middle records describe
potential and partial attainment. The top records describe an Avatar who has
approached the expected destiny.

The final two records are near variants of the same highest-tier message.
Different consumers choose between them: Blackthorn's rescue/refuge selector
can reach record four, while the Lord British-in-disguise camp event reaches
record five for its highest band.

## 4. Consumer Behavior

The current traced filename consumers are the Blackthorn rescue/refuge
presentation and the Lord British-in-disguise camp event. Older private
survey notes treated shrine meditation as a possible consumer, but the traced
CAST2 shrine path uses shrine-local text and `MISCMSG.DAT` instead.

The traced Blackthorn rescue/refuge presentation divides a one-byte verdict
selector into five twenty-point bands and selects records zero through four.
Record five is the sixth record by zero-based index and is not selected by that
table: the five band start positions match the shipped records' starts exactly,
while the table entry that would follow the fifth is not a record start. The
selector is related to moral presentation, but the current public evidence does
not prove that it is the entire per-virtue karma store.

That selector's divide is eight-bit and cannot overflow, so a standing of one
hundred or more produces a band of five through twelve and indexes past the
five-entry table into adjacent data, issuing the read at a position beyond end
of file. Nothing traps and only the printed text is affected. Treat it as
observed behaviour rather than a contract: clamp or reject the band.
`systems/blackthorn.md` Section 7 owns the surrounding print order, the
quotation marks the consumer adds around the record - a leading line feed and
an opening quote before it, one closing quote after it - and the fact that the
record body itself carries no line feed at either end.

The traced Lord British-in-disguise camp event also prints `KARMA.DAT` after
its level-up/stat-reward pass. It uses the same twenty-point band scale for the
lower range, selecting records zero through three for bands below eighty. For
values in the top band, it seeks directly to record five. This event does not
select record four.

The live shrine meditation path uses shrine-local strings and `MISCMSG.DAT`
for urn/Codex prophecy text. No traced CAST2 shrine path loads `KARMA.DAT`.
Shrine implementations should still keep all six records available because
they are shipped data consumed by the traced verdict paths above, not because
the shrine handler owns them.

The tier computation is outside this file. A modern implementation should load
the six strings as data and let the karma or event system choose a record by
semantic tier.

## 5. Validation and Error Handling

A compatible reader should validate that the file contains at least six
NUL-terminated records before using it. Extra trailing data should be ignored
unless an implementation is running in a strict asset-verification mode.

If fewer than six records are present, the original-style behavior would be an
out-of-bounds text read. A modern implementation should fail the asset load or
fall back to a clear missing-text placeholder. It should not silently treat
missing verdicts as zero karma, because standing values and text are separate
systems.

## 6. System Boundaries

No file-layout work remains for the shipped DOS data set. The six records,
their sequential packing, and both traced selectors are public.

Broader karma-storage and action-delta work belongs to `systems/karma.md`, not
this text-resource format. No traced shrine or endgame standing gate currently
reads `KARMA.DAT`; shrine meditation uses shrine-local and `MISCMSG.DAT` text,
while the endgame overlay uses quest/state flags.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`KARMA.DAT` section).
- `u5-decomp/functions/CAST2_OVL/`.
- `u5-decomp/functions/BLCKTHRN_OVL/`.
- `u5-decomp/functions/OUTSUBS_OVL/`.
- `u5-spec/systems/karma.md`.
- Fresh original consumer execution for the read shape, band offsets and
  out-of-range behaviour in `u5-decomp/functions/BLCKTHRN_OVL/` and
  `u5-decomp/notes/`, issue #269.
