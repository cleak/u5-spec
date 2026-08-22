# Character creation

## 1. Overview

Character creation is the flow that runs when a player starts a fresh game from the intro menu. It produces the avatar's name, gender, and three of the four primary stat fields (strength, dexterity, intelligence) plus magic points; it does **not** assign a class — the avatar's class is fixed at "Avatar" by the seed save and remains so for the rest of the campaign. The flow is driven by Lord British's gypsy-card questionnaire — a sequence of seven A-or-B virtue dilemmas in the tradition of Ultima IV, paced as four questions, then two, then one in a single-elimination tournament across the eight Britannian virtues.

The output is a complete `SAVED.GAM` file written to disk. After the file is written, control returns to the intro menu; the player must explicitly choose "Journey Onward" to load the just-written save and enter the world. There is no automatic transition from chargen into the game.

The same intro menu also offers a "Transfer from Ultima IV" path that bypasses the questionnaire entirely and instead reads stats from a Ultima IV completion save. That path is described in Section 10.

This spec covers the questionnaire flow, the seed-save mechanism that surrounds it, the byte-level customisation done to the avatar's record, and the persistence step that commits everything to disk.

## 2. Entry from the intro menu

The intro menu — the screen with options like "Journey Onward", "Create New Character", "Transfer from Ultima IV", and so on — is implemented inside the intro overlay. When the player presses the key that selects "Create New Character", the intro overlay calls a small trampoline in the resident core, which in turn enters the character-creation routine that lives inside the proportional-font overlay (the same overlay that owns the word-wrapped paragraph renderer used for both the intro slides and the questionnaire prompts; the chargen routine and the renderer share the overlay because they share the proportional font).

The character-creation routine is self-contained inside that overlay. Every call it makes goes either to a helper living in the same proportional-font overlay — the per-question step driver and the word-wrapped paragraph renderer — or to a resident core routine for keyboard input, text output, tile and panel drawing, randomness, and file I/O. It does not chain into the spell-casting overlay, which owns the spell system and plays no part in character creation, and it does not chain into any other overlay. An implementation is free to place character creation wherever it likes, but should not model it as a multi-stage overlay chain.

The hand-off is a one-way call: chargen runs in its own scope, never returns control to the intro menu mid-run, and on completion either writes the new save and returns or — if the player declines to enter a name — aborts cleanly back to the menu without writing anything. On return, the intro overlay's scene byte is set to "intro mode" so the menu loop runs another iteration.

## 3. Seed loading

Ultima V ships with a pair of factory-seed files that hold the starting world state for a brand-new game:

- `INIT.GAM` — a 4,192-byte image with all sixteen party-roster slots pre-populated. Records 1 through 15 are the canonical companion roster (Shamino, Iolo, Mariah, Geoffrey, Jaana, Julia, Dupre, Katrina, Sentri, Gwenno, Johne, Gorn, Maxwell, Toshi, Saduj). Their names, classes, genders, stats, equipment, and inventory are all baked into this file. Record 0 is the Avatar seed slot: name field empty, class set to Avatar, status good, and the non-questionnaire fields already populated.
- `INIT.OOL` — a 256-byte image of the surface map's pre-placed movable objects (a skiff and a small handful of other markers).

Both files are read-only seeds shipped with the game. They are never overwritten at runtime; the engine only ever reads them. The corresponding read/write working files are `SAVED.GAM` (4,192 bytes) and `SAVED.OOL` (512 bytes — surface concatenated with underworld). The save system writes the latter pair on quit and re-reads them on load.

The character-creation routine begins by reading `INIT.GAM` whole into the in-memory save image. After this read, every byte of the eventual `SAVED.GAM` file is in place except the Avatar customisation fields; chargen will overwrite a small fixed slice of that record (eight entered-name bytes, one gender byte, three stat bytes, one MP byte) and leave everything else — the Avatar's class, status, HP, experience, level byte, equipment slots, all companion records, inventory, world coordinates, NPC met/kill flags, shrine quest flags, calendar, weather, and vehicle state — exactly as the seed file shipped them.

This "clone the template" pattern is why the campaign begins in a known initial state. The party's starting position, gold, food, keys, gems, equipped weapons, time of day, and weather are not chosen by the player; they are dictated by `INIT.GAM`. Chargen's job is to personalise one record, not to construct a fresh game.

`INIT.OOL` is similarly read into a scratch buffer late in the flow, immediately before the new save is written. The relationship between the seed and the working file is asymmetric: the engine reads `INIT.GAM` and `INIT.OOL` whenever a fresh game starts, but writes only `SAVED.GAM` and `SAVED.OOL`. Reading the working file at chargen time would be wrong — the player might already have saved a previous game in the working slot, and starting a new one must not depend on that slot's contents.

## 4. Name and gender prompts

After the seed is loaded, chargen renders two prompts in sequence.

Both prompts use the **fixed-cell 8-by-8 character path** on the standing
full-screen text window, not the proportional paragraph renderer. Character
creation never resizes a text window; see Section 4.1.

**The name prompt.** The text "By what name shalt thou be known?" is printed with the fixed-cell character printer, and a free-text input prompt is opened with a maximum length of eight characters. The avatar's name is written directly into the first eight bytes of the seed-loaded Avatar name field; the save record has a fixed nine-byte name field, and the ninth byte remains seed padding for questionnaire-created names. Names shorter than eight characters are null-padded; names exactly eight characters fill the entered-name slice with no terminator. The name prompt accepts printable ASCII; backspace deletes; Enter terminates.

If the player presses Enter at the empty prompt — a zero-length name — chargen takes its **abort path**. It skips the rest of the flow, leaves `SAVED.GAM` on disk untouched, and returns to the intro menu. The in-memory save image will have been clobbered with the seed contents (since the read happened before the prompt), but that is harmless because nothing has written it back to disk and the next "Journey Onward" or "Create New Character" attempt will start over from the working file.

**The gender prompt.** Provided a name was entered, chargen prints "Art thou Male or Female? " and polls for either `M` or `F` — upper or lower case, folded to upper case before the comparison — looping silently on any other key and echoing the accepted letter at the cursor. The chosen value is written into the avatar's record at the field one byte beyond the name. The byte values used are not ASCII letters — the male code is `0x0B` and the female code is `0x0C`, two adjacent bytes well below the printable-ASCII range. These same two byte values appear at the same offset in every companion record in `INIT.GAM`, distinguishing the male and female members of the canonical companion roster. The codes are interpreted as glyph indices by the proportional-font renderer when displaying the gender on the character sheet; an `M`/`F` ASCII pair in this slot would have collided with other glyphs.

### 4.1 There is no questionnaire text rectangle

**Retraction.** Earlier revisions of this section ended with "chargen sets up a
full-screen text rectangle for the questionnaire and proceeds". That is
**withdrawn**: there is no such rectangle, and character creation never resizes
or reconfigures a fixed-cell text window at any point. An engine that models
the questionnaire as fixed-cell text in a caller-configured window will not
match.

Character creation uses **two independent text systems**, and the split is
clean:

| Path | Used for |
|---|---|
| Fixed-cell 8-by-8 character printer, on the standing full-screen window | The name prompt, the typed name, the gender prompt, and the echoed gender letter — nothing else |
| Proportional paragraph renderer (`text-output.md` section 8) | The opening gypsy paragraph, every question paragraph, and the result paragraph |

The proportional renderer takes its geometry from a shared layout descriptor
rather than from a text window, so it is unaffected by which fixed-cell window
happens to be active. Section 5.1 publishes the descriptor values for all three
paragraph screens.

The one fixed-cell reset that *does* happen is a **single opaque fill of the
menu window's interior**, pixels `(8, 128)..(311, 191)`, in colour 0, issued
once immediately before the name prompt. That rectangle is character cells
`(1, 16)..(38, 23)`. Above it, two small fills draw the prompt area's divider:
a colour-1 fill of `(120, 120)..(200, 126)` and a colour-3 horizontal rule from
`(120, 127)` to `(200, 127)`.

The interior is **not** cleared again between the name and gender steps, which
is why the name prompt and the typed name stay visible under the gender prompt.
The next clear of any kind is the full-page clear that precedes the gypsy
screen, and that one happens on the hidden surface.

## 5. The QUESTION.DAT file

The questionnaire's text content lives in `QUESTION.DAT`, a 7,746-byte data file shipped with the game. It is laid out as thirty NUL-terminated text records in plain ASCII, sharing two lightweight markup conventions with the intro narrative file: a leading `{`, which is a **first-line indent** of 15 pixels that draws no glyph and is not a page break, and `_` anywhere mid-word as a soft hyphen — a syllable-break the line-wrapper may use as a wrap candidate, which draws a hyphen only when the line actually breaks there and produces no glyph otherwise. Both markers are specified in `systems/text-output.md` section 8.2.

The thirty records decompose as: record 0, the gypsy-wagon arrival narrative (about 800 bytes); record 1, the gypsy's post-question/result paragraph (about 900 bytes); and records 2 through 29, the twenty-eight virtue-pair dilemmas, each a short prose paragraph (150 to 300 bytes) asking the player to choose between an option A and an option B. Twenty-eight is the count of unique unordered pairs of eight virtues, and the records cover exactly those twenty-eight pairings. The mapping from pair to record is held in an eight-by-eight symmetric table in the resident data image: indexing by the smaller-numbered virtue along one axis and the larger-numbered along the other yields the selected record. The diagonal cells are zero and unreachable because no virtue is paired with itself. The public record-ordinal mapping is listed in `formats/question-dat.md`.

The file is read in slices during chargen, never as a whole. Record 0 is loaded for the opening gypsy scene, records 2 through 29 are loaded one-per-question during the seven-question tournament, and record 1 is loaded after the tournament as the final gypsy/result paragraph before save commit. The game opens the file, seeks to the requested record, reads two kilobytes (more than any record but small enough for the scratch buffer), and the proportional-font renderer reads up to the NUL terminator. The same scratch buffer is reused across all reads.

## 5.1 Presentation layout

The character-creation graphics come from the eleven-slot `CREATE` image
directory. Name and gender prompts do not draw a `CREATE` panel; they are
fixed-cell text prompts over the chargen display state after the proportional
font and `CREATE` asset have been loaded.

| Flow point | `CREATE` slot | Top-left X | Top-left Y | Size | Role |
|---|---:|---:|---:|---|---|
| Opening gypsy paragraph | 0 | 0 | 96 | 168 x 96 | Opening scene panel |
| Question frame left backing | 1 | 16 | 0 | 120 x 148 | Left option backing |
| Question frame right backing | 1 | 200 | 0 | 120 x 148 | Right option backing |
| Post-question/result paragraph | 10 | 168 | 100 | 152 x 100 | Closing/result scene panel |

Slots 2 through 9 are the virtue option panels. The option labelled `A` is the
**left** panel: it uses the lower-numbered virtue in the current pair and is
drawn at that virtue's base origin. The option labelled `B` is the **right**
panel: it uses the higher-numbered virtue and is drawn 184 pixels to the right
of that virtue's base origin.

| Virtue | `CREATE` slot | Base X | Base Y | Size |
|---|---:|---:|---:|---|
| Honesty | 2 | 40 | 5 | 51 x 67 |
| Compassion | 3 | 48 | 7 | 43 x 67 |
| Valor | 4 | 48 | 4 | 34 x 69 |
| Justice | 5 | 40 | 10 | 55 x 58 |
| Sacrifice | 6 | 40 | 8 | 48 x 61 |
| Honor | 7 | 48 | 0 | 42 x 64 |
| Spirituality | 8 | 40 | 5 | 50 x 65 |
| Humility | 9 | 48 | 6 | 42 x 65 |

The visible draw order is:

1. Render the name prompt at fixed-cell column 3, row 17.
2. Read up to eight typed characters at fixed-cell column 14, row 19.
3. If the entered name is empty, abort back to the intro menu without drawing
   the gypsy panels or writing the save.
4. Render the gender prompt at fixed-cell column 8, row 21, loop silently until
   `M` or `F`, then echo the accepted key and store the encoded gender byte.
5. Draw `CREATE` slot 0, render `QUESTION.DAT` record 0 in the proportional
   font, flush the display, and wait for one keypress.
6. For each of the seven questions, draw slot 1 twice as the left and right
   backing panels, choose two eligible virtues, draw their option panels, load
   and render the selected question paragraph, flush the display, then loop
   until `A` or `B`.
7. Draw `CREATE` slot 10, render `QUESTION.DAT` record 1 in the proportional
   font, flush the display, and wait for one keypress.
8. Commit the generated save files, restore intro scene ownership, and return
   to the intro menu.

Invalid gender and question keys do not trigger a redraw or error message; the
polling loop keeps waiting. The paragraph renderer owns word wrapping through
the proportional font width table and advances within the caller's active
paragraph rectangle. The caller flushes after each paragraph/page and performs
the wait; paragraph rendering itself does not consume input.

### 5.1.1 Prompt cell positions

The two fixed-cell prompts sit inside the menu window's interior, at these
character cells on the standing full-screen window:

| Element | Cell `(column, row)` |
|---|---|
| `By what name shalt thou be known?` | `(3, 17)` |
| The `:` that precedes the typed name | `(14, 19)` |
| The typed name itself | begins at `(15, 19)`, at most 8 characters |
| `Art thou Male or Female? ` | `(8, 21)` |
| The echoed `M` or `F` | at the cursor where the prompt leaves it |

An empty name aborts character creation, as described in Section 4.

### 5.1.2 Paragraph rectangles

All three paragraph screens drive the proportional paragraph renderer of
`text-output.md` section 8, whose full contract — the margin-pair-plus-band
model, the brace indent, the soft hyphen, the justification rule, the nine-pixel
line advance and the clip at vertical position 192 — is published there and is
not restated here. The per-glyph advance table those rules measure with is
published in `formats/font-pcs.md` section 4. What chargen supplies is the
per-screen descriptor.

Three facts that black-box observation gets wrong often enough to be worth
stating flatly: **the line advance is exactly 9 pixels, not about 12**; glyphs
carry **no drop shadow and no outline** of any kind; and glyph drawing stops
once the pen reaches vertical position **192**, though the pen keeps advancing
as though it had not.

The renderer **fully justifies** every line except the last line of a paragraph
— that is, except a line ended by an explicit newline or by the end of the
record — which is left ragged. The leftover pixels of a justified line are
distributed across that line's spaces, each space taking the base space advance
plus the remaining slack divided by the number of spaces still to come,
truncating, with the remainder carried into later spaces; the leftovers
therefore land on the *last* spaces of the line.

| Field | Opening gypsy paragraph | Per-question paragraph | Result paragraph |
|---|---|---|---|
| `QUESTION.DAT` record | 0 | the pair's record, 2..29 | 1 |
| Pen start | `(0, 9)` | `(0, 152)` | `(0, 0)` |
| Outside band: left, right | 0, 320 | 0, 320 | 0, 320 |
| Inside band: left, right | 175, 320 | (band disabled) | 0, 166 |
| Band low, high | 89, 200 | (band disabled) | 90, 200 |
| Space advance | 5 | 5 | **4** |
| Line advance | 9 | 9 | 9 |
| Glyph shadow | none | none | none |

Read plainly:

- **The opening gypsy paragraph** starts at the very top-left, runs the full
  320-pixel width justified, and from the first line whose pen passes y = 89 it
  flows in the 175..320 column — to the right of the 168-wide art that starts at
  y = 96. The left margin is **175**, not 176.
- **The per-question paragraph** is full width throughout. The band is
  *disabled* before the questions begin, by collapsing its low bound onto its
  high bound so the band test can never succeed; that is the mechanism the
  original uses to turn the flow-around-art rule off, and setting the two bounds
  equal is the portable way to express it. With a pen start of `(0, 152)` and a
  nine-pixel advance, its lines land at y = 152, 161, 170, 179 and 188 before
  the clip at 192 stops output.
- **The result paragraph** is the mirror of the gypsy screen: full width at the
  top, then clipped to the 0..166 column — to the *left* of the 152-wide art
  that starts at x = 168 — for every line whose pen has passed y = 90. It is the
  only paragraph in the game that runs with the tightened 4-pixel space advance,
  which is restored to 5 as soon as the paragraph is laid out.

Each record's leading brace supplies a 15-pixel first-line indent that draws
nothing; every shipped `QUESTION.DAT` record opens with one.

### 5.1.3 Screen composition and buffer discipline

Every character-creation screen composes off-screen and is published in **one
instantaneous full-screen copy**. There is no wipe, no dissolve, and no
save-and-restore of a backing surface anywhere in this path. Per screen, in
order:

1. Install the layout descriptor values for this screen.
2. Read the `QUESTION.DAT` record into the shared text scratch buffer.
3. Select the hidden surface.
4. Issue the text system's clear control, blanking the page.
5. Draw the artwork.
6. Lay out the paragraph.
7. Copy the hidden page to the visible page.
8. Wait for a key — any key on the gypsy and result screens, `A` or `B` on a
   question screen.

The question screen is cleared this way **before each question**, so the
previous question's panels never survive into the next one. The proportional
font resource and the `CREATE` archive are opened once at the start of the
sequence and held for its whole duration; both are released after the result
screen, which then clears the hidden page, publishes it, and returns.

## 6. The questionnaire — eight virtues, seven questions

Britannia has eight virtues. The chargen code numbers them zero through seven, and the in-engine numbering matches the canonical Britannian order: Honesty, Compassion, Valor, Justice, Sacrifice, Honor, Spirituality, Humility. Each virtue has its own per-stat delta weights — small integer increments (zero, one, or two) added to the running stat tallies whenever that virtue is selected as the winner of a question. The deltas are:

| Virtue        | INT delta | DEX delta | STR delta |
|---------------|-----------|-----------|-----------|
| Honesty       | 2         | 0         | 0         |
| Compassion    | 0         | 2         | 0         |
| Valor         | 0         | 0         | 2         |
| Justice       | 1         | 1         | 0         |
| Sacrifice     | 0         | 1         | 1         |
| Honor         | 1         | 0         | 1         |
| Spirituality  | 1         | 1         | 1         |
| Humility      | 0         | 0         | 0         |

The rows follow the Britannian principle mapping: Honesty is Truth/INT, Compassion is Love/DEX, Valor is Courage/STR, the compound virtues add the corresponding paired principles, Spirituality adds all three, and Humility adds none. The total stat tally a player can accumulate is bounded by seven questions times the per-virtue maximum delta (two for any single stat), giving a hard ceiling well below twenty for any of the three stats.

The questionnaire is structured as a single-elimination tournament across the eight virtues, paced in three rounds:

- **Round 1.** Four questions are asked, each pairing two distinct virtues. After round 1, all eight virtues have been "asked about" once and four of them have lost.
- **Round 2.** Two questions are asked, each pairing two of the four round-1 winners. After round 2, two virtues remain alive.
- **Round 3.** One question pairs the last two virtues. The final winner is the single virtue still standing after this question.

Total: seven questions. The pairing within each round is randomised — chargen draws two virtues uniformly at random from the still-eligible pool for each question.

Two flag arrays support the elimination logic:

- The **selected-this-round** array — one byte per virtue — is set when a virtue is drawn for any question in the current round. It prevents a virtue from being asked twice in the same round even if the random number generator picks it again. It is cleared by the chargen driver between rounds, so winners from round 1 are eligible again in round 2, and round-2 winners are eligible again in round 3.
- The **lost-forever** array — one byte per virtue — is set on the loser of each question. It persists across rounds; once a virtue is eliminated, it cannot be drawn again until the next chargen run.

A virtue is eligible for a question only if both arrays are clear for it. The random virtue-picker is rejection-sampled — it draws a random index in zero through seven and rolls again if the chosen virtue is flagged. When a virtue is accepted, the picker immediately marks it selected for the current round before returning. Because each question calls the picker twice, the second draw cannot return the first draw's virtue; self-pairings are unreachable. With four eligible virtues drawn two at a time per round, the picker never has fewer than two candidates and so cannot loop forever.

For each question, after the two virtues are drawn, chargen sorts them by index: the smaller-numbered virtue gets the **`A` slot, which is the left panel**, and the larger-numbered virtue the **`B` slot, which is the right panel**. The internal record of which random draw ended up as the smaller number lets the engine map the player's A/B keypress back to winner/loser. The question record is loaded from `QUESTION.DAT` at the offset given by the symmetric pair table (which makes draw order irrelevant to question selection), and the two option tiles are drawn at fixed-per-virtue screen positions.

**Retraction — the panels are left and right, not top and bottom.** Earlier
revisions of this section called the two slots "top" and "bottom", which
contradicted Section 5.1's own placement table. The panels are side by side:
both smoke backings are drawn at vertical position 0, at horizontal positions
16 and 200, and the right-hand virtue symbol is displaced by exactly 184 pixels
in X from the left-hand one's per-virtue base origin. `A` selects the left
panel and `B` the right.

**No literal `A` or `B` glyph is drawn.** Neither the code nor the artwork
carries option letters: the two smoke backings are a plume rising from a
brazier with no lettering, and no character is printed beside either panel. The
option letters exist **only inside the question prose itself**, which reads in
the form "Dost thou A) ... or B) ...". An engine that draws its own A/B labels
beside the panels will not match.

The player presses A or B — upper or lower case, folded to upper case before
the comparison; any other key loops silently with no redraw and no error. The
engine reorders its internal pair when the pressed letter does not match the
side the lower-numbered virtue was drawn on, so the left/right mapping holds
regardless of which virtue was drawn first. On a valid answer, chargen adds the winner virtue's three stat deltas into running totals (INT, DEX, STR) and sets the loser's lost-forever flag. The loser contributes no stat deltas, including in the final round. The winner remains eligible for subsequent rounds; the loser does not.

## 7. Stat assignment

After the seven questions complete, chargen converts the running stat totals into the avatar's STR, DEX, INT, and MP fields. The INT total is written directly into the INT byte; the same value is also written into the MP byte (a freshly created avatar's magic points equal intelligence — subsequent gameplay depletes and restores MP independently). The DEX total is written directly into the DEX byte. The STR total is written after a one-step floor: if below twenty, it is replaced with twenty.

The floor always fires for the questionnaire path. The maximum STR contribution from any virtue is two, and seven questions of two-per-question contribute at most fourteen, well below twenty. So every newly-created questionnaire avatar emerges with exactly STR twenty, and STR is the one stat the questionnaire does not influence. INT and DEX, by contrast, do reflect the player's choices — the spread is small (low double-digits at the high end) but real.

The avatar's class field is **not written by chargen**. The class byte stays at whatever `INIT.GAM` shipped — the ASCII letter `A`, denoting "Avatar". Despite the eight-virtues-eight-classes parallel from Ultima IV, Ultima V's chargen does not pick a Fighter / Bard / Mage / Druid / Tinker / Paladin / Ranger / Shepherd class for the avatar based on the questionnaire winner. The avatar is always class Avatar. The class letters that *do* appear in the save file belong to the companion records (Shamino is a Ranger, Iolo a Bard, Mariah a Mage, and so on) — all preset by `INIT.GAM` and not modified by chargen.

The questionnaire is therefore a **stat-rolling mechanism** rather than a class-selection one. The single "winning virtue" emerging from the round-3 question is recorded in the running tallies (its deltas were the last to be added), but the winning virtue's identity is not stored anywhere — only the cumulative byte values survive.

## 8. Initial inventory and world state

Because chargen seeds the save from `INIT.GAM` and customises only a handful of
bytes in the Avatar's record, every other piece of the starting state is
dictated by the seed file: the sixteen-slot party roster (Avatar plus fifteen
companions, with classes, genders, stats, and equipment all preset), inventory,
starting position, NPC met/kill bitmaps, shrine flags, dungeon-map dump, and
codex-page flags.

For a questionnaire-created Avatar, the seed supplies current HP 60, maximum HP
60, experience 150, level 2, class Avatar, and good status; the
questionnaire supplies only name, gender, STR, DEX, INT, and MP. The same seed
starts the party with food 63, gold 150, keys 2, gems 0, torches 4, magic powder
0, and reagent counters of black pearl 4, blood moss 6, garlic 7, ginseng 6,
mandrake 0, nightshade 3, spider silk 0, and sulfurous ash 0. The travelling
party size is 3, the save clock starts at year 139, month 4, day 5, 08:35, and
the starting map tuple is scene 13 (Iolo's Hut), saved-scene scratch 0, floor/Z
0, X 15, Y 15. The seeded surface-map object overlay places a small handful of
pre-positioned objects (a skiff and a few cargo-shaped tiles) at fixed
coordinates.

The factory seed also supplies every roster member's readied equipment. The
six equipment columns below use the save-record order: helm, body armour,
weapon hand, shield/off hand, ring, and amulet/neck item. "Empty" means the
live empty-slot sentinel; non-empty names are equipment ids from
`catalogs/item-list.md`.

| Slot | Member | Helm | Body | Weapon | Off hand | Ring | Amulet / neck |
|---:|--------|------|------|--------|----------|------|---------------|
| 0 | Avatar | Chain Coif | Chain Mail | Long Sword | Empty | Empty | Ankh |
| 1 | Shamino | Leather Helm | Ring Mail | Short Sword | Small Shield | Empty | Empty |
| 2 | Iolo | Leather Helm | Leather Armour | Main Gauche | Short Sword | Empty | Empty |
| 3 | Mariah | Empty | Cloth Armour | Dagger | Empty | Empty | Empty |
| 4 | Geoffrey | Spiked Helm | Scale Mail | Mace | Spiked Shield | Empty | Spiked Collar |
| 5 | Jaana | Empty | Cloth Armour | Dagger | Empty | Empty | Empty |
| 6 | Julia | Chain Coif | Leather Armour | Spear | Empty | Empty | Empty |
| 7 | Dupre | Iron Helm | Scale Mail | 2H Sword | Empty | Empty | Empty |
| 8 | Katrina | Empty | Cloth Armour | Club | Empty | Empty | Empty |
| 9 | Sentri | Leather Helm | Leather Armour | Short Sword | Small Shield | Empty | Empty |
| 10 | Gwenno | Leather Helm | Leather Armour | Sling | Empty | Empty | Empty |
| 11 | Johne | Empty | Leather Armour | Dagger | Empty | Empty | Amulet/Turning |
| 12 | Gorn | Iron Helm | Scale Mail | Club | Large Shield | Empty | Empty |
| 13 | Maxwell | Chain Coif | Leather Armour | Throwing Axe | Small Shield | Empty | Empty |
| 14 | Toshi | Empty | Cloth Armour | Main Gauche | Empty | Ring of Protection | Empty |
| 15 | Saduj | Iron Helm | Scale Mail | Morning Star | Empty | Empty | Empty |

All other item, spell, and quest-stock bytes are inherited from the seed image
as the flat save-format contract describes them: shared supplies, special-item
flags, equipment inventory stock, premixed spell charges, scrolls, potions,
Moonstone gate slots, reagents, shrine progress masks, and mixed quest/mode
state are not generated by chargen. The creation flow only preserves those
seed bytes and writes them out with the customized Avatar record. Any remaining
semantic labels inside the shared item bands belong to `systems/inventory.md`,
`catalogs/item-list.md`, `systems/quest-flags.md`, and
`formats/saved-gam.md`, not to the character-creation producer.

A modern reimplementation that wants a fresh-game start without shipping `INIT.GAM` as an opaque blob has two reasonable choices: ship the seed unchanged (small, read-only, easiest path to behaviour-parity), or hand-author equivalent data tables in source. The seed's contents are not generated by any code path; they were authored at Origin and shipped frozen.

## 9. Persistence

Once the avatar's record has been customised, chargen commits the result to disk in a single sequence: it reads `INIT.OOL` into the second half of the object-overlay scratch region, zeroes the first 256-byte half, writes the full 512-byte block as `SAVED.OOL`, and finally writes the 4,192-byte `SAVED.GAM` from the in-memory save image. Every companion record, every inventory byte, every world flag — all bytes the seed shipped — are written verbatim alongside the eight bytes of avatar customisation.

This traced chargen writer therefore emits `SAVED.OOL` as a blank 256-byte half followed by the 256 bytes from `INIT.OOL`. That is the opposite of the canonical `SAVED.OOL` interpretation in `formats/ool.md` - surface plane first, underworld plane second - and the opposite of the clean-install seeded `SAVED.OOL` shape. A byte-compatible chargen implementation should preserve this emitted order. The later Journey Onward load does not repair or rotate the halves; it reads the first half as surface, reads the second half as underworld, and mirrors those interpreted halves to `BRIT.OOL` and `UNDER.OOL`.

Both writes are unconditional once the player has confirmed a name. There is no "are you sure?" Y/N prompt; commit is implicit in completing the questionnaire.

After the writes, chargen sets the scene byte to "intro mode" and returns. The intro overlay re-runs its menu with the just-written save now present on disk; the player must press the "Journey Onward" key explicitly to load it. The save writer used at chargen time is specific to chargen — distinct from the resident Q save command used during normal gameplay. Both write the same `SAVED.GAM` byte-image format, but they live in different overlays because of the source-side overlay split. Neither writer touches `INIT.GAM` or `INIT.OOL`, which are read-only seeds.

Because the chargen writer overwrites the whole save image, any existing `SAVED.GAM` is destroyed at this step. A player who already has a save in the slot and chooses "Create New Character" by accident loses that save without warning. If the player aborted earlier at the empty-name prompt, this commit step is never reached and the on-disk save is left untouched.

## 10. Transfer from Ultima IV

The intro menu offers a third path: instead of running the questionnaire, the player can transfer their completed Ultima IV avatar's stats forward by selecting "Transfer from Ultima IV" instead of "Create New Character". The transfer flow is implemented in the intro overlay rather than the proportional-font overlay, but it shares the same goal: produce a populated `SAVED.GAM` plus `SAVED.OOL` from Ultima V seed data and a small Avatar-record delta.

At v1 depth, the transfer source filename is pinned as `PARTY.SAV` on the Ultima IV player disk. The destination baseline comes from the same Ultima V seed pair chargen uses, `INIT.GAM` and `INIT.OOL`, not from the current `SAVED.GAM`. (Earlier text here named `BRIT.GAM`/`BRIT.OOL`; that was wrong, and no `BRIT.GAM` exists in the shipped data.) The transfer path uses the standard disk-swap/retry dance to read the predecessor save and then return to Ultima V media before writing the resulting save. The exact transfer mapping is owned by `systems/u4-transfer.md`: it imports the leading U4 character into U5 roster slot 0, translates U4 class into the corresponding U5 class letter, converts primary stats onto U5's scale, derives MP from converted INT, scales experience, derives level, and sets current and maximum HP from that level.

The observed transfer path renders a character-roster/status preview, lets the player confirm or replace name/gender, and supports both an abort path and a commit path. Abort returns to the intro menu without writing; commit writes the standard Ultima V save pair and then returns through the intro flow, where Journey Onward performs the normal load.

Both the questionnaire path and the transfer path produce a `SAVED.GAM` in the same on-disk format, so the rest of the engine sees no difference between them. Players who arrive into Britannia via either path see the same town tile, the same companion roster, and the same calendar; the personalized roster-slot-0 fields are what differ. One important distinction is class: questionnaire-created characters keep the seed's Avatar class, while transferred characters can keep the transferred U4 class family.

## 11. Chargen Boundaries And Remaining First-Load Check

The character-creation producer contract is fixed: chargen reads the seed
files, customizes only the Avatar's small record slice, preserves the seed
class/equipment/inventory/spell-stock/quest/world state, writes `SAVED.GAM`,
emits its traced `SAVED.OOL` ordering, returns to the intro menu, and waits for
the player to choose Journey Onward. First-load mirror handling is also fixed:
the normal load path treats the emitted halves as canonical surface then
underworld and mirrors them without normalization. Remaining work is not about
the questionnaire, seed-stock ownership, save-image producer, or first-load
file lifecycle.

- **`BRIT.OOL`/`UNDER.OOL` lifecycle.** The chargen writer does not refresh either per-plane mirror; it writes only `SAVED.OOL` and `SAVED.GAM`. The standard load path later refreshes both per-plane mirrors from `SAVED.OOL`, while the in-game save path stages through those files, writes both mirrors, and may flush the underworld mirror a second time. This belongs to the save/load system rather than chargen; it is flagged here only because the filenames overlap.

## 12. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The chargen entry point, the eight-phase flow, the abort path, the per-virtue stat-delta tables, the seed file relationships, the gender encoding, the class byte's preservation, and the STR floor — derived from `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- The confirmation that character creation reaches no further overlay — every call the routine makes is either local to the proportional-font overlay or a resident core routine, with none reaching the spell-casting overlay — derived from the callee inventory in `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` (2026-05-24).
- The per-virtue stat-delta weights and the pair-to-record table's properties — a zero diagonal, symmetry about that diagonal, and exactly twenty-eight distinct non-zero entries, one per unordered virtue pair — were re-verified on 2026-05-24 by reading the shipped resident data image directly, independently of the function notes.
- The per-question logic, the random-draw sort into A/B slots, the symmetric eight-by-eight pair-to-record table, the tournament's three-round structure, and the two flag arrays — derived from `u5-decomp/functions/FONT_OVL/0x09C8_questionnaire_iter.md`.
- The rejection-sampled random virtue picker — derived from `u5-decomp/functions/FONT_OVL/0x0998_pick_random_unused_virtue.md`.
- The proportional-font paragraph renderer and its paragraph-pacing conventions — derived from `u5-decomp/functions/FONT_OVL/0x0000_render_paragraph.md`.
- The three paragraph screens' layout descriptors, the nine-pixel line advance,
  the justification rule, the absence of a glyph shadow, the prompt cell
  positions, the single menu-interior clear, the left/right panel orientation,
  the absence of drawn option letters, and the compose-off-screen-then-publish
  discipline — derived from
  `u5-decomp/notes/presentation_endgame_chargen_u4_2026-08-22.md`.
- The intro menu key dispatch, the trampoline into the chargen routine on `C`, and the scene-byte handshake on return — derived from `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- The Transfer-from-Ultima-IV path's character-roster screen, disk-swap reads, and abort-versus-commit dispatch — derived from `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- The misclassification correction that placed chargen in the proportional-font overlay rather than the spell-casting overlay — derived from `u5-decomp/functions/CAST_OVL/_OVERVIEW.md`.
- The in-game save/quit writer (referenced for context; the chargen writer is a separate path) — derived from `u5-decomp/functions/CAST2_OVL/0x10FE_save_game.md`.
- The `QUESTION.DAT` file's thirty-record layout and the markup conventions shared with the intro narrative — derived from `u5-decomp/formats/data-tables.md`.
- The `SAVED.GAM` image layout, the 32-byte character record fields, the seed-file shipping equivalences, and the gender-byte encoding — derived from `u5-decomp/formats/saves.md`.
- The fresh-seed supplies, reagent counters, clock, and location tuple were
  cross-checked against a clean local asset image using the public save-field
  layout, without copying raw seed bytes.
- The factory-seed readied equipment table was cross-checked against the clean
  local seed image by interpreting the saved equipment slots through the
  public equipment item-id order in `catalogs/item-list.md`.
