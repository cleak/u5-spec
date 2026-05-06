# KARMA.DAT

## 1. Scope

`KARMA.DAT` is a small text resource used by virtue and endgame-related
presentation paths. Despite its name, it is not the table of karma adjustments
for player actions. Karma gains, losses, thresholds, and quest gates are owned
by code and save-state fields described in `systems/karma.md`.

This file supplies player-facing verdict speeches. A consumer chooses one
record according to a computed moral-standing tier and prints that text through
the normal text-output path.

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
does not store tier thresholds, virtue ids, karma scores, or record offsets.

## 3. Record Semantics

The six records are ordered from lowest moral standing to highest moral
standing. The first records are corrective speeches for an Avatar who has
fallen away from the virtue being judged. The middle records describe
potential and partial attainment. The top records describe an Avatar who has
approached the expected destiny.

The final two records are near variants of the same highest-tier message. The
current notes do not prove whether both are reachable in ordinary shrine play,
whether one belongs to a Blackthorn or endgame branch, or whether one is unused
content.

## 4. Consumer Behavior

The shrine meditation flow is the primary known consumer. After the player
meditates at a shrine and the engine computes the relevant virtue's standing,
the handler maps the score to a tier index and prints the corresponding
`KARMA.DAT` record.

Blackthorn-related rescue or judgement paths also load `KARMA.DAT` and select
a message from it. These paths reuse the file as a verdict-text table; they do
not make it a numeric karma table.

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
missing verdicts as zero karma, because scores and text are separate systems.

## 6. Known Uncertainties

- The exact score thresholds that choose records zero through five are not
  encoded in `KARMA.DAT` and remain part of the meditation and event-handler
  decompilation work.
- The distinction between the two highest-tier records is unresolved.
- The full list of non-shrine consumers has not been exhaustively mapped.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`KARMA.DAT` section).
- `u5-decomp/functions/CAST2_OVL/0x0966_shrine_meditate.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x0910_blackthorn_rescue.md`.
- `u5-spec/systems/karma.md`.
