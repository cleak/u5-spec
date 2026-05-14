# ENDMSG.DAT

## 1. Scope

`ENDMSG.DAT` contains the Lord British dialogue records printed during the
terminal endgame sequence. It is a text resource only. The endgame overlay owns
the confirmation prompts, quest-flag check, cinematic movement, pauses, and
terminal no-return behavior described in `systems/endgame.md`.

## 2. File Structure

The shipped file is 786 bytes and contains eleven non-empty records.

| Property | Value |
|---|---|
| Header | None |
| Offset table | None in the file |
| Record count | Eleven |
| Record terminator | NUL byte |
| Encoding | Plain low-ASCII dialogue text |
| Formatting | Embedded line feeds for paragraph breaks |

Records are packed back-to-back. The first records form the greeting and
two-step sandalwood-box confirmation. Later records form the successful
ending-rite monologue. The final record is used by the refusal or missing-box
branch.

## 3. Record Addressing

The file does not name or index records. The consumer treats it as an ordered
list and walks between NUL terminators. A modern loader may expose semantic
names such as `initial_greeting`, `first_box_prompt`, `second_box_prompt`,
`rite_message_n`, and `refusal_branch`, but those names are implementation
labels, not on-disk fields.

## 4. Consumer Behavior

The endgame sequence loads `ENDMSG.DAT` into a scratch buffer before printing
the Lord British dialogue. The flow uses the records in order:

1. Print the opening greeting, with the party leader's saved name inserted by
   surrounding code rather than by a placeholder in this file.
2. Print the first box-delivery prompt and collect a yes/no answer.
3. Print the second prompt naming the sandalwood box and collect the final
   yes/no answer.
4. If the final answer is yes and the saved quest flag is set, print the
   remaining rite records with pauses between them.
5. Otherwise, print the refusal-branch record and enter the non-victory
   terminal tableau.

The yes/no echoes, party-member names, pauses, palette effects, and final
scroll are not encoded in `ENDMSG.DAT`.

## 5. Validation and Error Handling

A compatible reader should require eleven NUL-terminated records. Missing
records should be treated as a bad asset, because the endgame cannot safely
continue without the prompt and branch text. Extra records may be ignored by
the original sequence because the record count is controlled by the consumer.

The file is expected to fit in the endgame text buffer. A modern
implementation should still bound reads by actual file length and reject
unterminated records.

## 6. System Boundaries

No file-layout work remains for the shipped DOS data set. The eleven-record
sequential text layout, prompt-record order, victory records, and refusal
record are public.

The external gameplay handoff is owned by `systems/endgame.md`: static caller
coverage reaches the overlay from dungeon-room/post-combat cleanup paths, and
the stock Doom final-room route is specified by `systems/endgame.md`,
`systems/dungeon-mode.md`, and the dungeon/arena format specs. This file's
layout and record order do not encode that route.

Pause cadence, animation timing, palette effects, and terminal branch behavior
belong to `systems/endgame.md`, not to this message table. The first
confirmation answer is displayed and echoed, but the endgame system branches
on the second confirmation plus the saved sandalwood-box flag. `ENDMSG.DAT`
supplies the dialogue records only; it does not encode that branch rule.

## 7. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`ENDMSG.DAT` section).
- `u5-decomp/functions/ENDGAME_OVL/0x0648_endgame_entry.md`.
- `u5-spec/systems/endgame.md`.
- `u5-spec/systems/text-output.md`.
