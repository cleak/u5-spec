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
validation, roster/status preview, character mapping, commit and abort
behavior, save-state effects, and relationship to chargen.

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
| `BRIT.GAM` | Save-image template used as the destination baseline. It has the same layout family as `SAVED.GAM` / `INIT.GAM`. |
| `BRIT.OOL` | Britannia object-overlay seed paired with the transfer baseline. |

The save image seed supplies everything that is not imported from Ultima IV:
world position, calendar, inventory, quest flags, NPC flags, companion
records, and the general starting state for the new campaign. The object seed
supplies the starting surface object table used when composing the companion
save file.

As with questionnaire chargen, transfer does not generate separate starting
item, spell, or quest stock. The `BRIT.GAM` seed's flat save image supplies the
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
anything to the U5 seed image. Malformed counter ranges, an unsupported class
index, or invalid name bytes reject the transfer attempt before the destination
save is written.

The leading-record validation accepts only these source-side shapes:

| Source-side value | Accepted range |
|---|---:|
| Gold, gems, and food counters | `0..9999` |
| Move, moon, and dungeon counters | `0..70` |
| Class index | `0..7` |
| Name bytes copied into the U5 Avatar field | NUL or printable bytes; any other control byte rejects the transfer |

The path also performs a broader "no transferable data" check over a later
source-save block. Within that later block, the transfer skips the predecessor
party-wide food and gold fields, then tests the eight consecutive virtue or
karma standing words for Honesty, Compassion, Valor, Justice, Sacrifice,
Honor, Spirituality, and Humility. If all eight words are zero, the intro
presents the no-transferable-data branch instead of producing a normal
preview. Any nonzero virtue-standing word allows the normal transfer preview
to proceed.

The source data is used only for the first Ultima V roster slot, the
Avatar-facing slot. The transfer does not import the Ultima IV location, quest
flags, inventory, world map state, companion roster, or object positions. Those
come from the Ultima V seed.

## 6. Roster And Status Preview

After the seed and transfer source are available, the intro renders a
party/status preview screen. The preview is party-facing rather than a raw
dump of the entire save file. It uses an eight-column character-slot heading
strip for the preview roster and shows the Avatar fields that are about to be
committed, including name, gender or pronoun state, class/status presentation,
primary stats, hit points, magic points, experience/level, and equipment or
status labels.

The preview surface is a fixed intro screen, not a scrolling text report. The
slot-heading strip is drawn once for each of the eight visible roster columns
and is written to both display pages so page swaps preserve the headings. The
lower continue/transfer window is a full-width boxed region with a three-row
interior; it is the prompt/status area used while the path waits for
confirmation, name replacement, gender correction, or abort input. Above that
prompt window, the intro paints two side-by-side character-information panels:
one at the left edge of the screen and one beginning 168 pixels from the left
edge. These panels carry the compared character-info/stat presentation while
the lower window remains available for transfer prompts.

The screen is also the transfer confirmation surface. The transfer path polls
single keystrokes and updates the in-memory Avatar record before the final
write:

- The imported or seeded name can be rejected and replaced. A blank
  replacement name is not accepted as the final name.
- The displayed gender can be confirmed or flipped.
- Primary stats are previewed after normalization into Ultima V fields.
- The preview can be aborted before the disk write.

The exact prompt text and screen wording are intentionally not reproduced
here. Implementations should reproduce the behavior: show the player the
resulting character record, allow correction of name and gender, and require a
clear commit action before overwriting the save slot.

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
| Class | Translate the U4 class index directly into the corresponding U5 class letter: Mage, Bard, Fighter, Druid, Tinker, Paladin, Ranger, or Shepherd. Transfer therefore can leave roster slot 0 with a non-Avatar class. |

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

Fields not owned by the transfer remain whatever the `BRIT.GAM` / `BRIT.OOL`
seed supplied. This includes the wider campaign state, inventory, equipment
outside the transferred slot fields, quest state, time, location, party size,
and companion records.

## 8. Commit And Abort

All transfer edits happen in memory until the final commit. Before that point,
an abort returns to the intro menu without writing `SAVED.GAM` or `SAVED.OOL`.
The in-memory seed image may have been changed, but that is not durable; the
next Journey Onward or creation attempt reads from disk again.

On commit, the transfer writes the normal Ultima V save files:

1. Compose the object-overlay companion by zeroing the first 256-byte half and
   leaving the loaded `BRIT.OOL` seed in the second 256-byte half.
2. Write `SAVED.OOL`.
3. Write the full save image to `SAVED.GAM`.
4. Return to intro/menu state and redraw the start/menu screen.

The traced transfer writer therefore emits `SAVED.OOL` as a blank half followed
by the 256 bytes from `BRIT.OOL`. As with the questionnaire chargen writer in
`systems/chargen.md`, this is opposite the normal surface-first interpretation
specified in `formats/ool.md`. A byte-compatible transfer implementation should
preserve the emitted order, while Journey Onward and normal saves should still
follow the canonical surface-first load/save contract. The later Journey
Onward load does not repair or rotate the emitted halves; it reads the blank
first half as the surface table, reads the seed half as the underworld table,
and mirrors those interpreted halves to `BRIT.OOL` and `UNDER.OOL`.

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
| Seed save | `INIT.GAM` | `BRIT.GAM` |
| Object seed | `INIT.OOL` | `BRIT.OOL` |
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
3. Locate and read the Ultima IV player disk's `PARTY.SAV` source save.
4. Build an in-memory Ultima V save image from the seed.
5. Patch only the Avatar-facing fields that transfer owns.
6. Render a roster/status preview and allow name/gender correction.
7. Abort without disk writes if the player cancels before commit.
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
regions are fixed. Remaining work is exhaustive preview text-field cursor,
attribute, and redraw-timing parity.

- **Ultima IV no-data gate.** The transfer source filename is pinned to
  `PARTY.SAV`, and the imported identity/stat/progress behavior is now mapped.
  The later no-transferable-data gate is fixed as the eight predecessor
  virtue/karma standing words; any nonzero word permits the normal preview,
  while all eight zero words produce the no-transferable-data branch.

- **First-load handling after transfer.** The traced writer order is fixed:
  `SAVED.OOL` is emitted as a blank half followed by `BRIT.OOL`, while normal
  save/load treats `SAVED.OOL` as surface-first. Journey Onward performs no
  special-case normalization; it mirrors the blank first half to `BRIT.OOL` and
  the seed half to `UNDER.OOL`.

- **Preview presentation parity.** The transfer screen's eight-column heading
  strip, lower prompt/status window, and paired character-info panels are fixed
  at region level. Exact cursor positions for every field, text attributes,
  and redraw timing should be verified against a captured run or a deeper
  text-call inventory if pixel-accurate reproduction is needed. Static
  control-flow analysis fixes the post-commit path as menu redraw rather than
  direct gameplay entry.

## 13. Sources

The behavior described here is cleanroom prose derived from the notes and
existing cleanroom specs listed below. No assembly excerpts, decompiled code,
private offsets, or binary text dumps are reproduced.

- Transfer seed reads, `PARTY.SAV` source-save filename, disk-state setup,
  roster/status preview, confirmation loop, XP/level/HP recalculation, field
  writes, and final `SAVED.GAM` / `SAVED.OOL` commit:
  `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Transfer preview slot-heading count and column-label helper behavior:
  `u5-decomp/functions/INTRO_OVL/0x1E22_print_slot_label.md`.
- Transfer preview lower prompt window and paired character-info panels:
  `u5-decomp/functions/INTRO_OVL/0x1E62_clear_continue_window.md` and
  `u5-decomp/functions/INTRO_OVL/0x1F26_render_charinfo_window.md`.
- `PARTY.SAV` validation, slot-0 transfer target, name/gender/status/class
  import, and first-pass source-field copy:
  `u5-decomp/functions/INTRO_OVL/0x1016_transfer_u4_disk.md`.
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
- Public Ultima IV `PARTY.SAV` semantic layout for the eight virtue/karma
  standing words, cross-checked only as source-format labels:
  <https://wiki.ultimacodex.com/wiki/Ultima_IV_internal_formats>.
- Existing cleanroom cross-checks:
  `u5-spec/systems/intro.md`, `u5-spec/systems/chargen.md`,
  `u5-spec/systems/save-load.md`, `u5-spec/formats/saved-gam.md`, and
  `u5-spec/formats/ool.md`.
