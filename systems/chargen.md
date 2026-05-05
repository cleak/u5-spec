# Character creation

## 1. Overview

Character creation is the flow that runs when a player starts a fresh game from the intro menu. It produces the avatar's name, gender, and three of the four primary stat fields (strength, dexterity, intelligence) plus magic points; it does **not** assign a class — the avatar's class is fixed at "Avatar" by the seed save and remains so for the rest of the campaign. The flow is driven by Lord British's gypsy-card questionnaire — a sequence of seven A-or-B virtue dilemmas in the tradition of Ultima IV, paced as four questions, then two, then one in a single-elimination tournament across the eight Britannian virtues.

The output is a complete `SAVED.GAM` file written to disk. After the file is written, control returns to the intro menu; the player must explicitly choose "Journey Onward" to load the just-written save and enter the world. There is no automatic transition from chargen into the game.

The same intro menu also offers a "Transfer from Ultima IV" path that bypasses the questionnaire entirely and instead reads stats from a Ultima IV completion save. That path is described in Section 10.

This spec covers the questionnaire flow, the seed-save mechanism that surrounds it, the byte-level customisation done to the avatar's record, and the persistence step that commits everything to disk.

## 2. Entry from the intro menu

The intro menu — the screen with options like "Journey Onward", "Create New Character", "Transfer from Ultima IV", and so on — is implemented inside the intro overlay. When the player presses the key that selects "Create New Character", the intro overlay calls a small trampoline in the resident core, which in turn enters the character-creation routine that lives inside the proportional-font overlay (the same overlay that owns the word-wrapped paragraph renderer used for both the intro slides and the questionnaire prompts; the chargen routine and the renderer share the overlay because they share the proportional font).

The hand-off is a one-way call: chargen runs in its own scope, never returns control to the intro menu mid-run, and on completion either writes the new save and returns or — if the player declines to enter a name — aborts cleanly back to the menu without writing anything. On return, the intro overlay's scene byte is set to "intro mode" so the menu loop runs another iteration.

## 3. Seed loading

Ultima V ships with a pair of factory-seed files that hold the starting world state for a brand-new game:

- `INIT.GAM` — a 4,192-byte image with all sixteen party-roster slots pre-populated. Records 1 through 15 are the canonical companion roster (Shamino, Iolo, Mariah, Geoffrey, Jaana, Julia, Dupre, Katrina, Sentri, Gwenno, Johne, Gorn, Maxwell, Toshi, Saduj). Their names, classes, genders, stats, equipment, and inventory are all baked into this file. Record 0 is the avatar slot — name field empty, class set to Avatar, all other stat bytes zero.
- `INIT.OOL` — a 256-byte image of the surface map's pre-placed movable objects (a skiff and a small handful of other markers).

Both files are read-only seeds shipped with the game. They are never overwritten at runtime; the engine only ever reads them. The corresponding read/write working files are `SAVED.GAM` (4,192 bytes) and `SAVED.OOL` (512 bytes — surface concatenated with underworld). The save system writes the latter pair on quit and re-reads them on load.

The character-creation routine begins by reading `INIT.GAM` whole into the in-memory save image. After this read, every byte of the eventual `SAVED.GAM` file is in place except the avatar's record; chargen will overwrite a small fixed slice of that record (eight name bytes, one gender byte, three stat bytes, one MP byte) and leave everything else — companion records, inventory, world coordinates, NPC met/kill flags, shrine quest flags, calendar, weather, vehicle state — exactly as the seed file shipped them.

This "clone the template" pattern is why the campaign begins in a known initial state. The party's starting position, gold, food, keys, gems, equipped weapons, time of day, and weather are not chosen by the player; they are dictated by `INIT.GAM`. Chargen's job is to personalise one record, not to construct a fresh game.

`INIT.OOL` is similarly read into a scratch buffer late in the flow, immediately before the new save is written. The relationship between the seed and the working file is asymmetric: the engine reads `INIT.GAM` and `INIT.OOL` whenever a fresh game starts, but writes only `SAVED.GAM` and `SAVED.OOL`. Reading the working file at chargen time would be wrong — the player might already have saved a previous game in the working slot, and starting a new one must not depend on that slot's contents.

## 4. Name and gender prompts

After the seed is loaded, chargen renders two prompts in sequence.

**The name prompt.** The text "By what name shalt thou be known?" is printed in the proportional font, and a free-text input prompt is opened with a maximum length of eight characters. The avatar's name is written directly into the seed-loaded save image at the eight bytes that constitute the avatar record's name field. Names shorter than eight characters are null-padded; names exactly eight characters fill the field with no terminator (the field is fixed-width). The name prompt accepts printable ASCII; backspace deletes; Enter terminates.

If the player presses Enter at the empty prompt — a zero-length name — chargen takes its **abort path**. It skips the rest of the flow, leaves `SAVED.GAM` on disk untouched, and returns to the intro menu. The in-memory save image will have been clobbered with the seed contents (since the read happened before the prompt), but that is harmless because nothing has written it back to disk and the next "Journey Onward" or "Create New Character" attempt will start over from the working file.

**The gender prompt.** Provided a name was entered, chargen prints "Art thou Male or Female? " and polls for either `M` or `F`, looping silently on any other key. The chosen value is written into the avatar's record at the field one byte beyond the name. The byte values used are not ASCII letters — the male code is `0x0B` and the female code is `0x0C`, two adjacent bytes well below the printable-ASCII range. These same two byte values appear at the same offset in every companion record in `INIT.GAM`, distinguishing the male and female members of the canonical companion roster. The codes are interpreted as glyph indices by the proportional-font renderer when displaying the gender on the character sheet; an `M`/`F` ASCII pair in this slot would have collided with other glyphs.

After both prompts are answered, chargen sets up a full-screen text rectangle for the questionnaire and proceeds.

## 5. The QUESTION.DAT file

The questionnaire's text content lives in `QUESTION.DAT`, a 7,746-byte data file shipped with the game. It is laid out as thirty NUL-terminated text records in plain ASCII, sharing two lightweight markup conventions with the intro narrative file: a leading `{` marking the start of a paragraph (consumed by the renderer as a paragraph-break sigil that produces no glyph), and `_` anywhere mid-word as a soft hyphen — a syllable-break the line-wrapper may use as a wrap candidate but which produces no glyph otherwise.

The thirty records decompose as: record 0, the gypsy-wagon arrival narrative (about 800 bytes); record 1, the gypsy's "So be it!" invitation (about 900 bytes); and records 2 through 29, the twenty-eight virtue-pair dilemmas, each a short prose paragraph (150 to 300 bytes) asking the player to choose between an option A and an option B. Twenty-eight is the count of unique unordered pairs of eight virtues, and the records cover exactly those twenty-eight pairings. The mapping from pair to record is held in an eight-by-eight symmetric table in the data segment: indexing by the smaller-numbered virtue along one axis and the larger-numbered along the other yields the byte offset of that pair's record. The diagonal cells are zero (no virtue paired with itself).

The file is read in slices during chargen, never as a whole. Records 0 and 1 are loaded at the start for the gypsy scene; the remaining seven slices are one-per-question, with the file seek calculated from the pair table. The game opens the file, seeks to the requested record, reads two kilobytes (more than any record but small enough for the scratch buffer), and the proportional-font renderer reads up to the NUL terminator. The same scratch buffer is reused across all reads.

## 6. The questionnaire — eight virtues, seven questions

Britannia has eight virtues. The chargen code numbers them zero through seven, and the in-engine numbering matches the canonical Britannian order: Honesty, Compassion, Valor, Justice, Sacrifice, Honor, Spirituality, Humility. Each virtue has its own per-stat delta weights — small integer increments (zero, one, or two) added to the running stat tallies whenever that virtue is selected as the winner of a question. The deltas are:

| Virtue        | INT delta | DEX delta | STR delta |
|---------------|-----------|-----------|-----------|
| Honesty       | 2         | 0         | 1         |
| Compassion    | 0         | 2         | 0         |
| Valor         | 0         | 0         | 0         |
| Justice       | 1         | 1         | 0         |
| Sacrifice     | 0         | 1         | 2         |
| Honor         | 1         | 0         | 0         |
| Spirituality  | 1         | 1         | 1         |
| Humility      | 0         | 0         | 1         |

Note that Valor's row is all zeros — choosing Valor as a winner contributes no stat tally. The other seven virtues all add at least one to at least one stat. The total stat tally a player can accumulate is bounded by seven questions times the per-virtue maximum delta (two for any single stat), giving a hard ceiling well below twenty for any of the three stats.

The questionnaire is structured as a single-elimination tournament across the eight virtues, paced in three rounds:

- **Round 1.** Four questions are asked, each pairing two distinct virtues. After round 1, all eight virtues have been "asked about" once and four of them have lost.
- **Round 2.** Two questions are asked, each pairing two of the four round-1 winners. After round 2, two virtues remain alive.
- **Round 3.** One question pairs the last two virtues. The final winner is the single virtue still standing after this question.

Total: seven questions. The pairing within each round is randomised — chargen draws two virtues uniformly at random from the still-eligible pool for each question.

Two flag arrays support the elimination logic:

- The **selected-this-round** array — one byte per virtue — is set when a virtue is drawn for any question in the current round. It prevents a virtue from being asked twice in the same round even if the random number generator picks it again. It is cleared by the chargen driver between rounds, so winners from round 1 are eligible again in round 2, and round-2 winners are eligible again in round 3.
- The **lost-forever** array — one byte per virtue — is set on the loser of each question. It persists across rounds; once a virtue is eliminated, it cannot be drawn again until the next chargen run.

A virtue is eligible for a question only if both arrays are clear for it. The random virtue-picker is rejection-sampled — it draws a random index in zero through seven and rolls again if the chosen virtue is flagged. With four eligible virtues drawn two at a time per round, the picker never has fewer than two candidates and so cannot loop forever.

For each question, after the two virtues are drawn, chargen sorts them by index: smaller-numbered virtue gets the "A" slot (top), larger-numbered the "B" slot (bottom). The internal record of which random draw ended up as the smaller number lets the engine map the player's A/B keypress back to winner/loser. The question record is loaded from `QUESTION.DAT` at the offset given by the symmetric pair table (which makes draw order irrelevant to question selection), and the two option tiles are drawn at fixed-per-virtue screen positions.

The player presses A or B; any other key loops silently. On a valid answer, chargen adds the winner virtue's three stat deltas into running totals (INT, DEX, STR) and sets the loser's lost-forever flag. The winner remains eligible for subsequent rounds; the loser does not.

## 7. Stat assignment

After the seven questions complete, chargen converts the running stat totals into the avatar's STR, DEX, INT, and MP fields. The INT total is written directly into the INT byte; the same value is also written into the MP byte (a freshly created avatar's magic points equal intelligence — subsequent gameplay depletes and restores MP independently). The DEX total is written directly into the DEX byte. The STR total is written after a one-step floor: if below twenty, it is replaced with twenty.

The floor appears to always fire. The maximum STR contribution from any virtue is two, and seven questions of two-per-question contribute at most fourteen, well below twenty. So in practice every avatar emerges with exactly STR twenty, and STR is the one stat the questionnaire does not actually influence. INT and DEX, by contrast, do reflect the player's choices — the spread is small (low double-digits at the high end) but real.

The avatar's class field is **not written by chargen**. The class byte stays at whatever `INIT.GAM` shipped — the ASCII letter `A`, denoting "Avatar". Despite the eight-virtues-eight-classes parallel from Ultima IV, Ultima V's chargen does not pick a Fighter / Bard / Mage / Druid / Tinker / Paladin / Ranger / Shepherd class for the avatar based on the questionnaire winner. The avatar is always class Avatar. The class letters that *do* appear in the save file belong to the companion records (Shamino is a Ranger, Iolo a Bard, Mariah a Mage, and so on) — all preset by `INIT.GAM` and not modified by chargen.

The questionnaire is therefore a **stat-rolling mechanism** rather than a class-selection one. The single "winning virtue" emerging from the round-3 question is recorded in the running tallies (its deltas were the last to be added), but the winning virtue's identity is not stored anywhere — only the cumulative byte values survive.

## 8. Initial inventory and world state

Because chargen seeds the save from `INIT.GAM` and customises only a handful of bytes in the avatar's record, every other piece of the starting state is dictated by the seed file: the sixteen-slot party roster (avatar plus fifteen companions, with classes, genders, stats, and equipment all preset), inventory (food, gold, keys, gems, torches, weapons, armor, runes, spells learned, reagents, quest-item flags), starting position (a known town tile in Britannia, with date and time-of-day baked in), and the all-zero NPC met/kill bitmaps, shrine flags, dungeon-map dump, and codex-page flags. The seeded surface-map object overlay places a small handful of pre-positioned objects (a skiff and a few cargo-shaped tiles) at fixed coordinates.

A modern reimplementation that wants a fresh-game start without shipping `INIT.GAM` as an opaque blob has two reasonable choices: ship the seed unchanged (small, read-only, easiest path to behaviour-parity), or hand-author equivalent data tables in source. The seed's contents are not generated by any code path; they were authored at Origin and shipped frozen.

## 9. Persistence

Once the avatar's record has been customised, chargen commits the result to disk in a single sequence: it reads `INIT.OOL` (the surface-map object overlay) into a scratch buffer, zeros a second scratch buffer (the underworld overlay, all zero because the seed places no underworld objects), writes the 512-byte `SAVED.OOL` from the two scratches concatenated, and finally writes the 4,192-byte `SAVED.GAM` from the in-memory save image. Every companion record, every inventory byte, every world flag — all bytes the seed shipped — are written verbatim alongside the eight bytes of avatar customisation.

Both writes are unconditional once the player has confirmed a name. There is no "are you sure?" Y/N prompt; commit is implicit in completing the questionnaire.

After the writes, chargen sets the scene byte to "intro mode" and returns. The intro overlay re-runs its menu with the just-written save now present on disk; the player must press the "Journey Onward" key explicitly to load it. The save writer used at chargen time is specific to chargen — distinct from the Q-Quit save routine used during normal gameplay. Both produce byte-identical output (both are writing the canonical `SAVED.GAM` format), but they live in different overlays because of the source-side overlay split. Neither writer touches `INIT.GAM` or `INIT.OOL`, which are read-only seeds.

Because the chargen writer overwrites the whole save image, any existing `SAVED.GAM` is destroyed at this step. A player who already has a save in the slot and chooses "Create New Character" by accident loses that save without warning. (See Section 11 for the abort-path's effect on the on-disk save.)

## 10. Transfer from Ultima IV

The intro menu offers a third path: instead of running the questionnaire, the player can transfer their completed Ultima IV avatar's stats forward by selecting "Transfer from Ultima IV" instead of "Create New Character". The transfer flow is implemented in the intro overlay rather than the proportional-font overlay, but it shares the same goal — produce a populated `SAVED.GAM` from `INIT.GAM` plus a small delta.

The transfer reads the U4 saved-game files from a designated transfer disk (the player is prompted to insert the disk when the path begins), parses the U4 character record, and copies a subset of the U4 stats forward into the new U5 avatar's record. The exact mapping — which U4 fields become which U5 fields, how Ultima IV's eight-class breakdown projects onto Ultima V's avatar-only model, and whether levels or experience are translated as well as primary stats — has not been fully decompiled and is open. What is observed is:

- The transfer flow reads two files: `BRIT.GAM` (a Britannia-state seed structurally identical to `INIT.GAM`) and `BRIT.OOL`. It uses the standard Ultima V disk-swap dance to handle floppy-disk media — prompt the user to insert the U4 disk, read what it needs, prompt for the U5 disk, and proceed.
- It renders a character-roster screen showing all sixteen party slots with their current stats, equipment, and status, presumably so the player can confirm what is being transferred.
- It supports both an "abort" path (return to menu without writing) and a "commit" path (proceed into Britannia with the transferred avatar).

Both the questionnaire path and the transfer path produce a `SAVED.GAM` in the same on-disk format, so the rest of the engine sees no difference between them. Players who arrive into Britannia via either path see the same town tile, the same companion roster, and the same calendar; only the avatar's stats and (for transfers) name and gender differ.

## 11. Open questions

Several aspects of the chargen flow are firm; others remain to be confirmed against in-game observation.

- **Whether the STR floor of twenty ever fails to fire.** The maximum possible STR tally over seven questions is fourteen — below twenty — so the floor appears to always fire, making STR an effectively constant twenty on every run and the player's choices affect only INT, DEX, and (derived) MP. Confirmation against the delta tables is done; an in-game check would catch any code path that bypasses the floor.

- **Whether the round-3 loser's deltas are skipped or added.** Rounds 1 and 2 ignore the loser's deltas; round 3's implementation is the same, but verify no late code path adds the round-3 loser's contribution as a "consolation" before writeout.

- **The exact eight-by-eight question-record table contents.** The pair-to-record mapping is held in a 128-byte symmetric table; spot-checks confirm a handful of pairings, but a full decoded transcript of every (i, j) cell would supplement the spec.

- **The on-disk byte order of `SAVED.OOL` after chargen.** The seed `SAVED.OOL` has its surface overlay in the first 256 bytes and zeros in the second 256. Reading the chargen writer, the buffer it composes appears to have the opposite order. Either the writer's two scratch-buffer addresses combine in a way that has been read incorrectly, or chargen produces a different byte order than the shipping seed. A single in-DOSBox capture immediately after chargen would resolve it.

- **The abort path's effect on an existing `SAVED.GAM`.** Pressing Enter at the empty name prompt aborts before writing. The on-disk save is therefore preserved, but the in-memory image has been clobbered with the seed; this is harmless because the engine only reads from disk when "Journey Onward" is selected. Verify by triggering the abort with an existing save and confirming the file is intact.

- **Whether the avatar's class can ever become anything other than Avatar.** Chargen never writes the class byte. The transfer flow may overwrite it with the U4 character's class — pending decomp of the transfer's class translation.

- **Pacing and interruption of the gypsy paragraphs.** The renderer's paragraph-pacing convention is "render one record, wait for any keypress, advance"; the questionnaire follows the same model with A/B as the advance keys. Whether the gypsy paragraphs accept escape as a cancel is open; the observed behaviour is "any key advances".

- **`BRIT.OOL`/`UNDER.OOL` mirror-write behaviour.** A recent finding suggests the in-game save/load path mirror-writes the seed alongside the working file under some conditions and mirror-reads on load. The chargen writer does not appear to do this — it writes only `SAVED.OOL` and `SAVED.GAM`. The mirror behaviour belongs to the in-game save/load path rather than chargen; flagged here because the filenames overlap.

- **The avatar's seeded starting equipment, level, HP, and experience.** All taken from `INIT.GAM` unchanged. A full enumeration of the seed avatar's starting items belongs in the save-file format spec.

## 12. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions and format dissections in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, byte-level structure tables, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The chargen entry point, the eight-phase flow, the abort path, the per-virtue stat-delta tables, the seed file relationships, the gender encoding, the class byte's preservation, and the STR floor — derived from `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- The per-question logic, the random-draw sort into A/B slots, the symmetric eight-by-eight pair-to-record table, the tournament's three-round structure, and the two flag arrays — derived from `u5-decomp/functions/FONT_OVL/0x09C8_questionnaire_iter.md`.
- The rejection-sampled random virtue picker — derived from `u5-decomp/functions/FONT_OVL/0x0998_pick_random_unused_virtue.md`.
- The proportional-font paragraph renderer and its paragraph-pacing conventions — derived from `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- The intro menu key dispatch, the trampoline into the chargen routine on `C`, and the scene-byte handshake on return — derived from `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- The Transfer-from-Ultima-IV path's character-roster screen, disk-swap reads, and abort-versus-commit dispatch — derived from `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- The misclassification correction that placed chargen in the proportional-font overlay rather than the spell-casting overlay — derived from `u5-decomp/functions/CAST_OVL/_OVERVIEW.md`.
- The in-game save/quit writer (referenced for context; the chargen writer is a separate path) — derived from `u5-decomp/functions/CAST2_OVL/0x10FE_save_game.md`.
- The `QUESTION.DAT` file's thirty-record layout and the markup conventions shared with the intro narrative — derived from `u5-decomp/formats/data-tables.md`.
- The `SAVED.GAM` image layout, the 32-byte character record fields, the seed-file shipping equivalences, and the gender-byte encoding — derived from `u5-decomp/formats/saves.md`.
