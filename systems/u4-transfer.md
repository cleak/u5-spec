# Ultima IV Transfer

## 1. Overview

The Ultima IV transfer path is the third fresh-game path offered by the
intro menu. It is for a player who already has an Ultima IV Avatar and wants
to bring that character forward instead of answering Ultima V's character
creation questionnaire.

The transfer is not a normal saved-game load. A Journey Onward load reads the
current Ultima V `SAVED.GAM` and resumes play from that state. The transfer
instead creates a new Ultima V save by cloning an Ultima V seed state,
patching the Avatar record from Ultima IV-derived data, writing the result to
the normal save files, and returning to the intro menu. Once the save has been
written, every later load and save uses the standard `SAVED.GAM` /
`SAVED.OOL` path; the rest of the engine does not care that the first save was
created by transfer rather than by the questionnaire.

This spec covers the intro entry, media handling, seed loading, source-save
validation, the single-character comparison preview, character mapping, commit
and abort behavior, save-state effects, and relationship to chargen.

## 2. Entry From The Intro Menu

The transfer begins when the player chooses the intro menu entry for
transferring from Ultima IV. The intro overlay owns this path directly. It
does not enter the proportional-font character-creation overlay used by the
questionnaire.

At entry, the transfer handler:

- records the current intro scene state so it can return cleanly;
- prepares the disk/media state used by the original floppy-disk prompt and
  retry layer;
- loads the Ultima V transfer seed files;
- renders the transfer preview and confirmation UI;
- either aborts without writing or commits the newly-created save.

The observed transfer path behaves like a fresh-save producer. After the
transfer writes its save files, control returns through the intro/menu redraw
path and resumes menu polling. Gameplay proceeds only after the player chooses
Journey Onward, which loads the newly-written save. This matches the
character-creation path's external contract more closely than the Journey
Onward path: both `C` and `T` create a save, while `J` is the path that
actually loads one into gameplay.

## 3. Media And Disk Handling

The original game was built for floppy media. The transfer path therefore
does more than a simple file read:

- It remembers the current DOS drive or media state at entry.
- It uses the same retrying disk-I/O wrappers used by the intro load path.
- It can prompt or wait for the Ultima IV transfer media when it needs the
  predecessor save.
- It returns to Ultima V media before writing the resulting Ultima V save.
- It treats missing or wrong media as a retryable condition rather than a hard
  process failure.

A modern implementation backed by one install directory can collapse these
prompts into ordinary file-existence checks. The important compatibility
contract is that no partial save should be committed merely because the wrong
disk was present. Reads must succeed before the preview is considered valid,
and writes happen only after the player commits the transfer.

The transfer source media is read-only from Ultima V's point of view. The path
does not alter the Ultima IV save. It only uses it to populate fields in the
Ultima V Avatar record.

## 4. Ultima V Seed Loading

The transfer starts from an Ultima V template, not from the player's existing
`SAVED.GAM`. The observed seed reads are:

| File | Role |
|---|---|
| `INIT.GAM` | Save-image template used as the destination baseline. It has the same layout family as `SAVED.GAM`. The transfer reads 4,192 bytes of it into the working save image. |
| `INIT.OOL` | Object-overlay seed paired with that baseline; it is the underworld plane table, byte-identical to the shipped `UNDER.OOL`. The transfer reads 256 bytes of it. |

Earlier revisions of this document named the seed pair `BRIT.GAM` and
`BRIT.OOL`. That is withdrawn: no file named `BRIT.GAM` exists in the shipped
data set at all, and the transfer path's two seed reads name `INIT.GAM` and
`INIT.OOL`. `BRIT.OOL` is the ordinary surface object overlay used by
save/load, not a transfer seed.

The save image seed supplies everything that is not imported from Ultima IV:
world position, calendar, inventory, quest flags, NPC flags, companion
records, and the general starting state for the new campaign. The object seed
supplies the starting surface object table used when composing the companion
save file.

As with questionnaire chargen, transfer does not generate separate starting
item, spell, or quest stock. The `INIT.GAM` seed's flat save image supplies the
shared inventory bands, spell-charge counters, scroll and potion counters,
Moonstone gate slots, reagents, shrine masks, and mixed quest/mode state. The
transfer path patches only the imported Avatar-facing fields and preserves
those seed-stock bytes.

Existing `SAVED.GAM` and `SAVED.OOL` are not read as inputs to transfer. If
the player already has an Ultima V save, that save is preserved only until the
transfer commit step. A committed transfer overwrites the working save slot.

## 5. Transfer Source

The transfer reads the Ultima IV player disk's `PARTY.SAV` file. The analyzed
DOS path validates the leading transferable character record before committing
anything to the U5 seed image. Out-of-range stat or progress values, an
unsupported class index, or invalid name bytes reject the transfer attempt
before the destination save is written.

### 5.1 Source-file shape the parser needs

Only three regions of the predecessor save are touched, and the transfer never
writes to it. The layout below is the public Ultima IV save layout, expressed
as the parser contract the Ultima V transfer actually relies on. Offsets are
file-relative hexadecimal, widths are in bytes, and multi-byte integers are
unsigned little-endian.

| Region | File offset | Size | Use |
|---|---|---:|---|
| Two leading counters | `0x0000` | 8 | Skipped. The transfer never reads them, so their meaning does not matter to a clean parser. |
| Character records | `0x0008` | 8 records of 39 bytes each | Only the **first** record is read, so the transfer path itself never exercises the stride; the 39-byte stride is fixed instead by the file geometry — eight records between `0x0008` and the party-wide block at `0x0140` — and by the field layout below, which fills exactly 39 bytes. The read pulls 40 bytes from offset `0x0008`, i.e. the whole leading record plus one slack byte. |
| Party-wide block | `0x0140` | 182 bytes read | Begins immediately after the eighth character record (`0x0008 + 8 * 39 = 0x0140`). Used only for the Avatarhood test in Section 5.3. |

A character record is ten 16-bit fields, then a sixteen-byte name, then three
single bytes. The rows below name only the fields the Ultima V transfer
actually touches; the three word fields it never reads are listed as "not read"
rather than given labels this spec has not verified.

| Record offset | Width | Field | Used by the transfer |
|---|---:|---|---|
| `0x00` | 2 | Current hit points | Validated; feeds the progress recalculation |
| `0x02` | 2 | Maximum hit points | Validated; feeds the progress recalculation |
| `0x04` | 2 | Experience | Validated; feeds the progress recalculation |
| `0x06` | 2 | Strength | Validated; feeds the attribute translation |
| `0x08` | 2 | Dexterity | Validated; feeds the attribute translation |
| `0x0A` | 2 | Intelligence | Validated; feeds the attribute translation |
| `0x0C` | 2 | Magic points | Read, not validated |
| `0x0E` | 2 | Not read | Ignored |
| `0x10` | 2 | Not read | Ignored |
| `0x12` | 2 | Not read | Ignored |
| `0x14` | 16 | Name | First eight bytes validated, then imported |
| `0x24` | 1 | Sex marker | Imported as the gender field |
| `0x25` | 1 | Class index | Validated, then imported |
| `0x26` | 1 | Status | Ignored; the U5 slot is forced to Good |

What the transfer finally writes into the Ultima V record is not always the raw
source value: Section 7 specifies the attribute translation, the experience
scaling, and the recalculated level and hit-point fields. Validation happens
first, on the raw source values.

The party-wide block begins with a four-byte food counter and a two-byte gold
counter, and the eight virtue/karma standing values follow as eight consecutive
16-bit words at block offsets `0x06` through `0x14` (file offsets `0x0146`
through `0x0155`).

### 5.2 Validation gate

Every accepted range below is an upper-bound test on an unsigned value read from
the **leading character record**, so each field's accepted range is zero through
the stated maximum:

| Source-side field | Record offset | Accepted range |
|---|---|---:|
| Current hit points | `0x00` | `0..9999` |
| Maximum hit points | `0x02` | `0..9999` |
| Experience | `0x04` | `0..9999` |
| Strength | `0x06` | `0..70` |
| Dexterity | `0x08` | `0..70` |
| Intelligence | `0x0A` | `0..70` |
| Class index | `0x25` | `0..7` |
| First eight name bytes | `0x14..0x1B` | Each byte must be NUL or at least `0x20`; any other control byte rejects the transfer |

No party-wide counter is validated. In particular the predecessor's gold, food,
gems, torches, keys, sextants, move count, moon phase and dungeon-progress
fields are never read on this path, and an implementation must not reject a
transfer because of them. Earlier drafts of this section listed
"gold, gems and food" for the `0..9999` tests and "move, moon and dungeon"
for the `0..70` tests; those labels were wrong. The `0..9999` tests are the
leading character's hit points, maximum hit points and experience, and the
`0..70` tests are that character's Strength, Dexterity and Intelligence.

Failing any check aborts the transfer and leaves the destination save
untouched. The failure is reported on a full-screen message page whose exact
wording is given in Section 6.2.

### 5.3 Avatarhood test

After validation succeeds and the leading record has been copied, the path
reads the party-wide block and tests eight consecutive 16-bit values starting
six bytes into the block, i.e. skipping the block's leading food and gold
fields. **If all eight are zero the transferred character is marked an Avatar;
otherwise it is not.** Nothing about this test aborts or diverts the transfer:
both outcomes produce the normal preview, and the flag only selects a class
override and some wording (Section 6.6 and Section 7).

Those eight values are the predecessor's eight virtue standings — one unsigned
16-bit value per virtue, in the Ultima IV virtue order of Honesty, Compassion,
Valor, Justice, Sacrifice, Honor, Spirituality, and Humility — laid out
consecutively after the block's food and gold fields. Ultima IV zeroes a
virtue's standing once that virtue has been fully attained, so "every standing
is zero" is the predecessor's own full-Avatar condition, and the transfer is
simply asking whether the imported character finished all eight virtue quests.
Item counters such as gems, torches, keys, and sextants sit *after* the
standings and are not part of the test; a completed Avatar who is still
carrying equipment is still recognised as an Avatar.

Implementations should key on the geometry rather than on the labels: read the
sixteen bytes that begin six bytes into the party-wide block and require every
one of them to be zero. That is the shipped test, and it produces the correct
result regardless of how a particular predecessor save spells the standings.

The test is **satisfied only when each of the eight values is individually
zero**. It is not a sum, a total, or a check on any wider aggregate, so a
predecessor save whose standings happen to cancel out or wrap around still
fails it. Element width is 16 bits and the
stride is two bytes, giving file offsets `0x0146`, `0x0148`, `0x014A`, `0x014C`,
`0x014E`, `0x0150`, `0x0152` and `0x0154`, with the block ending at `0x0155`.
The 182-byte read that supplies them begins at file offset `0x0140`, so the
party-wide food and gold fields at the head of that block are skipped by
construction rather than by an explicit step. **A byte-wide test, an eight-byte
span, or any offset near the head of the file is wrong**: eight bytes at
`0x0002` lands on the moon counter, the dungeon counter and the 16-bit gold
field, none of which this path ever reads.

The resulting flag is set at most once and is **never cleared** for the
remainder of the run, so treat it as a one-shot latch computed per transfer
attempt and do not assume it resets between attempts.

Earlier revisions of this document described this as a "no-transferable-data
gate" in which all-zero values reject the transfer. That is withdrawn and was
backwards: all-zero is the *success* condition for Avatarhood, and no value of
this block ever prevents a transfer.

The source data is used only for the first Ultima V roster slot, the
Avatar-facing slot. The transfer does not import the Ultima IV location, quest
flags, inventory, world map state, companion roster, or object positions. Those
come from the Ultima V seed.

Note that validation runs on the raw predecessor values, before any of the
translations in Section 7. A source Strength of 70 passes the gate and is then
put through the attribute translator; the gate does not see U5-side values.

## 6. Character Comparison And Status Preview

The transfer screen is built entirely from the resident fixed-cell text system
described in `text-output.md`. It uses no proportional font, no screen-panel
art, and no hidden surface. Every write lands on the visible page immediately:
**there is no double buffering, no page swap and no deferred flush anywhere in
this path.** Earlier revisions of this document said the slot headings were
"written to both display pages so page swaps preserve the headings"; that is
withdrawn. What is written twice is written into two different *text windows*
(the two character-information panels), not two display pages.

The screen is drawn once and then edited in place, one field at a time, as the
player works through a fixed sequence of confirmation stages.

### 6.1 Windows and regions

Cell coordinates below are absolute screen cells on the 40-column by 25-row
grid. Pixel coordinates use the 320-by-200 surface with the origin at the
upper-left corner.

The path defines three text windows:

| Window | Cell rectangle | Role |
|---|---|---|
| Left panel | columns `0..19`, rows `0..18` | The character as Ultima IV supplied it |
| Right panel | columns `21..39`, rows `0..18` | The character as Ultima V will store it |
| Message line | columns `3..37`, row `21` | Prompts and stage messages |

Before those rectangles are installed, the path clears the whole screen with a
single full-screen text window and draws the lower prompt frame.

**Lower prompt window.** Drawn from the same five frame glyphs as the intro
menu's lower text-window frame (`systems/intro.md` section 6.1), but it is a
**separate descriptor with its own bounds**, not a reuse of the menu frame: the
menu frame has an eight-row interior, this one has three. Those five glyphs are
the four rounded bevel corners (`IBM.CH` codes `0x7B`, `0x7C`, `0x7D`, `0x7E`)
and **one fully solid cell** (code `0x7F`, all sixty-four pixels set). There is
no separate horizontal-bar and vertical-bar glyph: the horizontal runs and the
side columns are the same solid cell, so the frame reads as a thick band, not as
a line-drawn box. Earlier revisions of this section called them "horizontal-bar"
and "vertical-bar" glyphs; that is withdrawn. The frame is: at cell `(0, 19)`
the top-left corner glyph, thirty-eight solid cells, the top-right corner glyph;
on rows `20`, `21` and `22` one solid cell in column `0` and another in column
`39`; on row `23` the bottom-left corner glyph, thirty-eight solid cells, and
the bottom-right corner glyph.
The frame glyphs are emitted in the panel colour — user-interface colour
slot 2 of `display-driver.md` section 2. A four-segment line rectangle is then
drawn in the accent colour — slot 1 — through the pixel corners `(7, 159)`,
`(312, 159)`, `(312, 184)`, `(7, 184)` and back to `(7, 159)`.

**Character-information panels.** Each panel is drawn by the same routine with
a different pixel origin: the left panel at `x = 0`, the right panel at
`x = 168`. For an origin `x0` the panel is:

- three filled bars in the panel colour — user-interface colour slot 2 of
  `display-driver.md` section 2: `(x0, 0)..(x0 + 6, 143)`,
  `(x0 + 143, 0)..(x0 + 151, 137)`, and `(x0 + 7, 137)..(x0 + 150, 143)`;
- a broken-top rule polyline in the accent colour — user-interface colour
  slot 1 — through `(x0 + 24, 7)`, `(x0 + 7, 7)`, `(x0 + 7, 136)`,
  `(x0 + 143, 136)`, `(x0 + 143, 7)`, `(x0 + 128, 7)`. The deliberate gap
  between `x0 + 24` and `x0 + 128` is where the panel title plate sits;
- the panel's own text window then paints a nineteen-cell title row, a
  bottom-left corner and a bottom-right corner. Every cell of the title row is
  written, left to right, starting from cell `(0, 0)`:

| Panel cell(s) on row 0 | Content | Colour |
|---|---|---|
| 0 | top-left corner glyph | panel colour |
| 1, 2 | solid cell (`0x7F`) | panel colour |
| 3 | left title-plate cap: the right-pointing bracket end-cap glyph (`IBM.CH` code `0x02`), plus two short angled rules drawn through the cell's pixel box from `(px, py)` to `(px + 5, py + 3)` and from `(px + 5, py + 4)` to `(px, py + 7)` | cap glyph in panel colour, rules in accent colour |
| 4..14 | the eleven characters of the title text ` Ultima IV ` (leading and trailing space included) | accent colour |
| 15 | right title-plate cap: the left-pointing bracket end-cap glyph (code `0x01`), plus the mirrored rules from `(px + 7, py)` to `(px + 2, py + 3)` and from `(px + 2, py + 4)` to `(px + 7, py + 7)` | cap glyph in panel colour, rules in accent colour |
| 16, 17 | solid cell (`0x7F`) | panel colour |
| 18 | top-right corner glyph | panel colour |

  where `px` and `py` are the pixel coordinates of the cap cell's upper-left
  corner (cell column times eight, cell row times eight, in absolute screen
  terms). The cap cells are what make the polyline's break exact: cell 3 begins
  at pixel `x0 + 24` and cell 15 ends at pixel `x0 + 127`, meeting the rule
  again at `x0 + 128`. Finally, at cell `(0, 17)` a bottom-left corner glyph
  and at cell `(18, 17)` a bottom-right corner glyph.

**The two panels are titled differently.** Both are painted from the same
` Ultima IV ` string, but immediately after the second panel is drawn the path
selects the right panel and writes a single space over its title cell `12` —
the `I` of `IV`. The right panel therefore reads ` Ultima  V ` (with the
doubled inner space left behind) and the left panel keeps ` Ultima IV `. That
one-cell edit is the only difference between the two panel frames, and an
implementation must reproduce it: the left panel is the Ultima IV source and
the right panel is the Ultima V result.

Earlier revisions of this document said that "both panels carry the same
` Ultima IV ` title" and that "the title string is never rewritten, so the
right-hand panel is titled Ultima IV". The second half of that is true of the
*string* and false of the *screen*; the claim is withdrawn.

### 6.2 Field-label strip

The strip the older text called an "eight-column character-slot heading strip"
is in fact an eight-**row** field-label column, drawn once into each panel.
Each label is printed at **column 3** of its panel, at these panel-relative
rows, with the leading spaces shown:

| Row | Label text |
|---:|---|
| 2 | `    Name:` |
| 5 | `  Sex:` |
| 6 | `Class:` |
| 8 | `  Exp:` |
| 9 | `Level:` |
| 11 | `  STR:` |
| 12 | `  DEX:` |
| 13 | `  INT:` |

The leading spaces right-align the words so that the word itself always begins
at column 7 for `Name:` and at column 5 for `Sex:`, `Exp:`, `STR:`, `DEX:` and
`INT:`, and at column 3 for `Class:` and `Level:`. Those are exactly the
positions the stage machine reprints a single label at when it highlights it.

Each label is printed twice: once with the left panel selected, once with the
right panel selected.

### 6.3 The "Found" summary page

Before the comparison screen is built, the transfer shows a full-screen summary
of the character it read, using the full 40-by-25 window. The screen is cleared
first. Content, in draw order:

| Cell `(column, row)` | Content |
|---|---|
| `(0, 11)` | `Found:` followed by a line break, centred |
| `(0, 12)` | the imported name, centred |
| `(12, 13)` | `a level `, the level number, then ` Male ` or ` Female `, then the class name |
| `(17, 15)` | `STR:  ` followed by the Strength value |
| `(17, 16)` | `DEX:  ` followed by the Dexterity value |
| `(17, 17)` | `INT:  ` followed by the Intelligence value |
| `(10, 20)` | the imported name, then ` is `, then `an Avatar.` or `not an Avatar` |

Centring is a text-window mode that the path turns on before `Found:` and off
after the name. The class names printed are `Mage`, `Bard`, `Fighter`,
`Druid`, `Tinker`, `Paladin`, `Ranger` and `Shepherd`, each followed by a line
break. All values on this page are the **unconverted** Ultima IV values.

The level shown on this page is **not** the level Section 7 computes. It is the
staged value written when the source record is copied: the source record's
maximum-hit-points field divided by one hundred, truncating. Section 7's
experience-derived level and the `30 * level` hit points overwrite it later,
during the conversion stage, so the number on this page and the number on the
comparison screen's right-hand panel can legitimately differ.

The page waits for any key and is then cleared.

**Rejected source data.** If validation (Section 5.2) fails, the path instead
clears the screen, turns on centring, and prints from cell `(0, 5)`:
`Error:  Your Ultima IV game`, a blank line, `contains bad data.`, a blank
line, `Unable to continue transfer.`, two blank lines, and
`Press any key to return to the menu.` It waits for any key and returns to the
intro menu with nothing written.

### 6.4 Media selection

The transfer does not begin with an on-screen "insert the Ultima IV disk"
prompt. It takes the current DOS drive, tries to select it, and on failure
waits for a single keystroke and retries with that key as the drive letter.
`Esc` at this prompt is the **only** abort in the whole transfer path; it
restores the intro scene state and returns to the menu without writing
anything. The player-visible feedback for a wrong or absent disk comes from the
resident media-error handler, not from this screen.

The shipped executable does contain an unused block that would have printed
`Transfer Character from Ultima IV`, then at cell `(0, 15)`
`Please insert the Ultima IV Player Disk`, at `(8, 16)`
`and press drive letter`, and at `(3, 18)`
`or press <Esc> to abort transfer`. Static control-flow analysis shows that
block is unreachable in the shipped build: the code jumps over it and nothing
branches into it. A clean implementation should follow the reachable behaviour
and not draw those lines; the strings are documented here only so an
implementer who finds them in the data knows they are dead.

### 6.5 Stage machine

Once the comparison screen exists, the left panel is filled with the
unconverted Ultima IV values and the path walks a fixed sequence of stages.
Left-panel content, at panel-relative cells:

| Cell | Content |
|---|---|
| `(0, 3)` | imported name, centred |
| `(10, 5)` | `Male` or `Female` |
| `(10, 6)` | `Avatar` if the Avatarhood test passed, otherwise the class name |
| `(10, 8)` | experience |
| `(10, 9)` | level |
| `(10, 11)` | Strength |
| `(10, 12)` | Dexterity |
| `(10, 13)` | Intelligence |
| `(0, 15)` | `Avatar` or `Non-Avatar`, centred |

Every stage then repeats the same four moves:

1. In **both** panels, reprint the previous stage's label in normal video and
   the new stage's label in inverse video, at the label positions from
   Section 6.2. Highlighting is a per-window inverse toggle applied around the
   single label reprint; nothing else is repainted.
2. Write the converted value into the **right** panel at column 10 of the
   stage's row.
3. Clear the message-line window and print the stage's prompt or message there.
4. Wait for input.

Nothing else on the screen is redrawn at any point. The panels are never
rebuilt, the frames are never redrawn, and no region is repainted after a name
or gender edit beyond the single cell run that changed.

The stages, in order:

| Stage | Row | Message-line content and cursor | Input | Effect |
|---|---:|---|---|---|
| Name confirm | 2 | `Keep this name?` at message-line cell `(10, 0)` | loops until `Y` or `N`; every other key is ignored | none |
| Name replace | 2 | `Enter new name: ` at message-line cell `(1, 0)`, then a typed-entry field starting immediately after that sixteen-character prompt | typed text, maximum eight characters | only entered when the previous stage answered `N`; repeats while the entered name is empty, so a blank name can never be accepted. The accepted name is written centred into the right panel at `(0, 3)` |
| Sex confirm | 5 | `Keep same sex?`, centred | loops until `Y` or `N` | `Y` keeps the imported gender, `N` flips it; the resulting `Male` or `Female` is written to right-panel `(10, 5)` |
| Class | 6 | `Thou art now an Avatar:` if the Avatarhood test passed, otherwise `Class remains intact`, at message-line cell `(2, 0)` | any key | right-panel `(10, 6)` shows `Avatar` or the class name |
| Experience | 8 | `Experience has been converted`, centred | any key | experience is divided by ten and written to right-panel `(10, 8)` |
| Level | 9 | `Level has been converted`, centred | any key | level and hit points are recalculated (Section 7) and the level is written to right-panel `(10, 9)` |
| Strength | 11 | `Strength: was ` + old value + `(50), now ` + new value + `(30)`, at message-line cell `(1, 0)` | any key | translated Strength, floored to 20, written to right-panel `(10, 11)` |
| Dexterity | 12 | `Dexterity: was ` + old value + `(50), now ` + new value + `(30)`, at message-line cell `(1, 0)` | any key | translated Dexterity written to right-panel `(10, 12)` |
| Intellect | 13 | `Intellect: was ` + old value + `(50), now ` + new value + `(30)`, at message-line cell `(1, 0)` | any key | translated Intelligence written to right-panel `(10, 13)`, and copied into current magic points |

`(50)` and `(30)` are literal text: the Ultima IV and Ultima V maxima printed
after each number.

**Invalid keys.** The two confirmation prompts accept only `Y` and `N`
(case-folded); any other key is discarded silently with no beep, no message and
no redraw. The informational stages accept any key. Once the drive has been
selected, **no key aborts the transfer** — `Esc` at any of these prompts is
simply ignored, and there is no cancel path back to the menu.

### 6.6 Finishing the screen

After the Intellect stage the path writes `Avatar` or `Non-Avatar`, centred, to
right-panel cell `(0, 15)`, widens the message-line window to columns `2..37`
and rows `21..22`, clears it, requests the Ultima V save media, and prints
` Conversion complete, saving...`. The message is emitted as one string that
begins with two line breaks, then a single leading space, then the words, then
one more line break. Because the widened window is only two rows tall, the
second and fourth line breaks each scroll it by one row under the standard
text-window overflow rule (`text-output.md`), so the settled result is the
message on screen row `21`, its leading space at column `2` and its first
letter at column `3`, with row `22` left blank. The save files
are then written (Section 8).

**Commit timing.** The commit is issued immediately after the last stage's
keypress. Nothing is presented or flushed first, because nothing on this screen
is buffered — the message text is already on the visible page by the time the
write starts. An implementation that does use a back buffer must present the
"saving" message before it writes, so the visible ordering matches.

**Backing state.** No part of the screen underneath the transfer UI is saved or
restored. The transfer clears the whole screen at entry and, on return, the
intro reloads and redraws the start/menu view from scratch. This is true of
both the abort path and the commit path.

Source provenance: derived from private analysis note
`../u5-decomp/notes/u4_transfer_screen_trace_2026-08-22.md` and the intro
overlay function notes it cites.

## 7. Character Mapping

The destination is roster slot 0 in the Ultima V save image. Companion records
remain the companion records from the Ultima V seed. The transfer does not add
Ultima IV party members to the Ultima V roster and does not reorder Ultima V
companions.

The imported identity fields are:

| U5 field | Transfer behavior |
|---|---|
| Name | Copy up to eight characters from the source record, then terminate or pad the fixed U5 name field. The preview can still reject and replace the imported name before commit. |
| Gender | Preserve the source male marker as U5 male; any other source value becomes U5 female. The preview can still flip the displayed gender before commit. |
| Status | Set to Good. |
| Class | Translate the U4 class index directly into the corresponding U5 class letter: index `0` Mage, `1` Bard, `2` Fighter, `3` Druid, `4` Tinker, `5` Paladin, `6` Ranger, `7` Shepherd. If the Avatarhood test in Section 5.3 passed, that letter is then overwritten with the Avatar class letter. Transfer therefore leaves roster slot 0 with a non-Avatar class only when the source character had not attained all eight virtues. |

Primary attributes use the same three-region translator for Strength,
Dexterity, and Intelligence:

| Source attribute `n` | U5 attribute before any field-specific floor |
|---:|---:|
| `0..9` | `n` |
| `10..29` | `floor((n - 9) / 2) + 10` |
| `30+` | `floor((n - 30) / 4) + 20` |

After translation, Strength alone is floored to 20. Dexterity and Intelligence
are not floored. The converted Intelligence value is also copied into current
magic points, so transferred current MP starts equal to transferred INT.

Progress fields are recalculated rather than copied through verbatim:

| U5 field | Transfer behavior |
|---|---|
| Experience | Source experience divided by 10, truncating toward zero. |
| Level | Start at level 1, divide the scaled U5 experience by 100, then increment level once for each halving step while that quotient remains nonzero. This yields level 1 below 100 scaled XP, level 2 for 100..199, level 3 for 200..399, and so on. |
| Current HP | `30 * level`. |
| Maximum HP | `30 * level`. |

Fields not owned by the transfer remain whatever the `INIT.GAM` / `INIT.OOL`
seed supplied. This includes the wider campaign state, inventory, equipment
outside the transferred slot fields, quest state, time, location, party size,
and companion records.

## 8. Commit And Abort

All transfer edits happen in memory until the final commit. The only abort is
the `Esc` at the drive-selection prompt described in Section 6.4, which happens
before any source data has been read; the confirmation stages have no cancel
key. An abort returns to the intro menu without writing `SAVED.GAM` or
`SAVED.OOL`, and no transfer window or backing surface is preserved: the intro
simply reloads and redraws the start/menu view. The source-validation failure
in Section 6.3 is the other way out, and it likewise writes nothing. The
in-memory seed image may have been changed, but that is not durable; the next
Journey Onward or creation attempt reads from disk again.

On commit, the transfer writes the normal Ultima V save files:

1. Compose the object-overlay companion by zeroing the first 256-byte half -
   the surface table - and leaving the loaded `INIT.OOL` seed in the second
   256-byte half, which is the underworld table.
2. Write `SAVED.OOL`.
3. Write the full save image to `SAVED.GAM`.
4. Return to intro/menu state and redraw the start/menu screen.

The traced transfer writer therefore emits `SAVED.OOL` as a blank half followed
by the 256 bytes from `INIT.OOL`. As with the questionnaire chargen writer in
`systems/chargen.md`, this **is** the normal surface-first interpretation
specified in `formats/ool.md`: `INIT.OOL` is the underworld seed, and the
shipped surface seed `BRIT.OOL` is empty, so a blank first half followed by
`INIT.OOL` is precisely [surface][underworld]. An earlier revision of this
paragraph called the emitted order "opposite the normal surface-first
interpretation"; that is withdrawn, along with the idea that transfer needs a
special writer order at all. The later Journey Onward load has nothing to
repair or rotate; it reads the blank first half as the surface table, reads the
seed half as the underworld table, and mirrors those interpreted halves to
`BRIT.OOL` and `UNDER.OOL`, restoring both to their shipped contents.

The commit is destructive to the existing working save slot. There is no
separate confirmation that the previous Ultima V save should be replaced, no
backup file, and no multi-slot selection. A compatible implementation should
treat transfer commit the same way chargen commit is treated: it writes the
single canonical working save.

The transfer path does not write `INIT.GAM` or `INIT.OOL`. It also does not
itself perform the Journey Onward mirror writes to `BRIT.OOL` and `UNDER.OOL`;
those belong to the standard load path. After transfer returns to the menu,
Journey Onward will read the newly-written `SAVED.GAM`, read `SAVED.OOL`, and
refresh the per-plane mirrors as ordinary load housekeeping. The separate
Q-save staging and conditional underworld mirror update are owned by
`systems/save-load.md`.

## 9. Save-State Effects

A committed transfer produces an ordinary Ultima V starting save with a
transferred Avatar. The resulting state has these properties:

- The Avatar record contains the transferred and player-confirmed identity and
  stat fields.
- The companion roster comes from the Ultima V seed.
- Party size, starting position, scene state, calendar, inventory, NPC flags,
  shrine flags, dungeon-map state, and other world fields come from the
  Ultima V seed.
- The object-overlay companion comes from the Ultima V object seed plus an
  empty counterpart plane.
- Existing Ultima V progress is overwritten.
- Later gameplay sees a normal `SAVED.GAM` / `SAVED.OOL` pair and uses the
  standard Journey Onward and Quit-and-Save paths.

The transfer therefore imports a character, not a campaign. It is not a
cross-game save converter for world state.

## 10. Relationship To Chargen

Character creation and Ultima IV transfer are sibling ways to create the first
Ultima V save:

| Aspect | Character creation | Ultima IV transfer |
|---|---|---|
| Intro key | `C` | `T` |
| Owning overlay | Proportional-font/chargen flow | Intro transfer flow |
| Primary input | Name, gender, seven-question virtue tournament | Ultima IV save plus confirmation/edit prompts |
| Seed save | `INIT.GAM` | `INIT.GAM` |
| Object seed | `INIT.OOL` | `INIT.OOL` |
| Output | `SAVED.GAM` and `SAVED.OOL` | `SAVED.GAM` and `SAVED.OOL` |
| Gameplay entry | Later Journey Onward load | Later Journey Onward load |

Both paths personalize the Avatar record while leaving the wider Ultima V
starting world to a seed file. Both overwrite the single working save on
commit. Both return to the intro flow after writing. The difference is the
source of the Avatar stats: the questionnaire derives them from Ultima V's
virtue tournament, while transfer derives them from a predecessor save.

## 11. Implementation Contract

A compatible implementation should model transfer as:

1. Enter from the intro menu's transfer command.
2. Locate and read the Ultima V transfer seed image and object seed.
3. Select the Ultima IV source media. This is the single abort point in the
   whole path: `Esc` here restores the intro scene state and returns to the
   menu with nothing read and nothing written (Section 6.4).
4. Locate and read the Ultima IV player disk's `PARTY.SAV` source save. If it
   fails the validation gate, print the bad-data page and return to the menu
   without writing anything (Section 6.3).
5. Build an in-memory Ultima V save image from the seed.
6. Patch only the Avatar-facing fields that transfer owns.
7. Render the two-panel single-character comparison screen and walk its fixed
   confirmation and conversion stages, which allow name and gender correction
   but offer no cancel key: once the drive has been selected, no key aborts
   the transfer (Sections 6.5 and 8).
8. On commit, write `SAVED.OOL` and `SAVED.GAM`.
9. Return through the intro/menu redraw path and let a later Journey Onward
   load enter gameplay from the save.

An implementation may skip floppy-style prompt rendering when all files live
in one directory, but it should keep the same commit boundary: media failure
or malformed transfer data must not overwrite the existing Ultima V save.

## 12. Transfer Boundaries And Remaining Parity Work

The transfer contract is complete at fresh-save producer depth: entry point,
source filename, destination seed files, validation gate, imported Avatar
fields, preview/confirmation boundary, abort-before-write behavior, commit file
set, object-companion emission order, return-through-menu behavior, later
Journey Onward handoff, first-load mirror behavior, and major preview surface
regions are fixed. The preview presentation is now fixed at print-call depth
as well: window rectangles, frame geometry, field-label positions, per-stage
prompt wording and cursor cells, per-stage redraw scope, input acceptance, and
commit ordering are all in Section 6.

- **Ultima IV Avatarhood test.** The transfer source filename is pinned to
  `PARTY.SAV`, and the imported identity/stat/progress behavior is mapped. The
  party-wide block test is fixed as sixteen bytes that must all be zero for the
  character to be marked an Avatar. It never rejects a transfer. The earlier
  reading of this test as a "no-transferable-data gate" that aborts on all-zero
  values is withdrawn; see Section 5.3.

- **Source-side parser contract.** Section 5 now publishes the full source
  layout the parser needs: the eight-byte leading counter pair, the eight
  thirty-nine-byte character records, the field map inside a record, the
  party-wide block's position and its food/gold/karma ordering, and the exact
  validated field set. No coordinate or heuristic guessing is required to read
  `PARTY.SAV` for transfer purposes. Fields outside that set are never read,
  so nothing is known or claimed about them here.

- **First-load handling after transfer.** The traced writer order is fixed and
  is the same surface-first order normal save/load uses: `SAVED.OOL` is emitted
  as a blank surface half followed by the `INIT.OOL` underworld seed. Journey
  Onward performs no special-case normalization and needs none; it mirrors the
  blank first half to `BRIT.OOL` and the seed half to `UNDER.OOL`.

- **Preview presentation parity.** Closed for implementation purposes.
  Section 6 publishes the three text-window rectangles, the lower prompt
  frame's glyph and pixel geometry, both character-info panel geometries, the
  eight field-label rows and columns, the per-stage prompt wording and cursor
  cells, the per-stage redraw scope, the input-acceptance rule for every stage,
  and the commit ordering. Two residual items remain, neither of which blocks a
  faithful implementation:
  - the exact behaviour of the shared typed-entry helper used by the
    replacement-name field (backspace, padding and terminator handling) is
    owned by `text-output.md`, not by this document;
  - the finding that the on-screen insert-disk instructions are dead code is a
    static-analysis result. A captured run would confirm it, but nothing in
    the reachable control flow contradicts it.

  The former residual "both character-info panels carry the same `Ultima IV`
  title" is closed and was wrong: the right panel is retitled in place to
  ` Ultima  V ` by a single-cell blank write, which Section 6.1 now specifies.

  Static control-flow analysis fixes the post-commit path as menu redraw rather
  than direct gameplay entry.

## 13. Sources

The behavior described here is cleanroom prose derived from the notes and
existing cleanroom specs listed below. No assembly excerpts, decompiled code,
private offsets, or binary text dumps are reproduced.

- Complete print-call-granularity trace of the transfer screen: seed
  filenames, drive-selection loop, summary page, window rectangles, panel and
  frame geometry, field-label table, every stage's prompt text and cursor cell,
  per-stage redraw scope, input acceptance, and commit ordering:
  `u5-decomp/notes/u4_transfer_screen_trace_2026-08-22.md`.
- Transfer seed reads, `PARTY.SAV` source-save filename, disk-state setup,
  comparison preview, confirmation loop, XP/level/HP recalculation, field
  writes, and final `SAVED.GAM` / `SAVED.OOL` commit:
  `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Transfer preview slot-heading count and column-label helper behavior:
  `u5-decomp/functions/INTRO_OVL/0x1E22_print_slot_label.md`.
- Transfer preview lower prompt window and paired character-info panels:
  `u5-decomp/functions/INTRO_OVL/0x1E62_clear_continue_window.md` and
  `u5-decomp/functions/INTRO_OVL/0x1F26_render_charinfo_window.md`.
- `PARTY.SAV` region geometry, record stride, validated field identities,
  slot-0 transfer target, name/gender/status/class import, and first-pass
  source-field copy:
  `u5-decomp/functions/INTRO_OVL/0x1016_transfer_u4_disk.md`.
- File-read parameter contract used to establish the two read regions
  (seek position and read length per read):
  `u5-decomp/functions/ULTIMA_EXE/0x7234_read_file_seek.md`.
- Independent second-pass re-derivation of the validated field set, the record
  stride, the derived-level source field, and the identity of the eight tested
  party-wide values as the virtue standings:
  `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.
- Third-pass re-verification of the virtue-standing block's offset, element
  width and stride, the per-element (rather than aggregate) form of the test, the
  one-shot latch behaviour of the resulting flag, and the staged
  maximum-hit-points-derived level shown on the summary page:
  `u5-decomp/notes/presentation_endgame_chargen_u4_2026-08-22.md`.
- U4-to-U5 primary-attribute translator:
  `u5-decomp/functions/INTRO_OVL/0x12EA_u4_attr_to_u5.md`.
- Intro menu entry and return-to-menu context:
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Standard Journey Onward load, empty-save guard, object-overlay mirror
  behavior, and media retry context:
  `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- Character creation seed and commit behavior used for comparison:
  `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- Save-image and object-overlay file roles:
  `u5-decomp/formats/saves.md`.
- Public Ultima IV `PARTY.SAV` semantic layout, used only to attach names to
  the fields the Ultima V transfer reads and to confirm the record stride:
  <https://wiki.ultimacodex.com/wiki/Ultima_IV_internal_formats>.
- Existing cleanroom cross-checks:
  `u5-spec/systems/intro.md`, `u5-spec/systems/chargen.md`,
  `u5-spec/systems/save-load.md`, `u5-spec/formats/saved-gam.md`, and
  `u5-spec/formats/ool.md`.
