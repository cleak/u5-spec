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

Records are packed back-to-back. To read record `n`, a reader starts at the
beginning of the file and skips `n` NUL-terminated records. The file itself
does not store tier thresholds, virtue ids, standing values, or record offsets.

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
table. The selector is related to moral presentation, but the current public
evidence does not prove that it is the entire per-virtue karma store.

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
