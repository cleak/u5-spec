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
the normal save files, and returning control to the intro flow. Once the save
has been written, every later load and save uses the standard `SAVED.GAM` /
`SAVED.OOL` path; the rest of the engine does not care that the first save was
created by transfer rather than by the questionnaire.

This spec covers the intro entry, media handling, seed loading, roster/status
preview, commit and abort behavior, save-state effects, relationship to
chargen, and the unresolved stat-mapping details.

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
path. Gameplay then proceeds through the normal Journey Onward load of the
newly-written save. This matches the character-creation path's external
contract more closely than the Journey Onward path: both `C` and `T` create a
save, while `J` is the path that actually loads one into gameplay.

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

Existing `SAVED.GAM` and `SAVED.OOL` are not read as inputs to transfer. If
the player already has an Ultima V save, that save is preserved only until the
transfer commit step. A committed transfer overwrites the working save slot.

## 5. Transfer Source

The transfer reads a saved party or character record from the Ultima IV disk.
The exact predecessor filename and record-level parse are not fully specified
yet. The current function note identifies the Ultima IV party save as the
likely source, but the field-by-field reader still needs a deeper pass.

The source data is used only for the Avatar-facing portion of the Ultima V
save:

- name, subject to player confirmation or replacement;
- gender, subject to player confirmation or flip;
- primary stats and related derived character fields;
- progress fields such as hit points, level, or experience, pending exact
  mapping.

Ultima IV location, quest flags, inventory, world map state, companions, and
object positions are not imported. Those come from the Ultima V seed.

## 6. Roster And Status Preview

After the seed and transfer source are available, the intro renders a
party/status preview screen. The preview is party-facing rather than a raw
dump of the entire save file. It shows the travelling roster slots and the
Avatar fields that are about to be committed, including name, gender or
pronoun state, class/status presentation, primary stats, hit points, magic
points, experience/level, and equipment or status labels.

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

The destination is the Avatar record in the Ultima V save image. Companion
records remain the companion records from the Ultima V seed. The transfer does
not add Ultima IV party members to the Ultima V roster and does not reorder
Ultima V companions.

The observed transfer flow touches or recalculates the Avatar's core
character fields:

- name;
- gender;
- strength;
- dexterity;
- intelligence;
- magic points;
- current and maximum hit points;
- experience and level-related presentation.

Initial magic points are tied to the transferred intelligence value, matching
the general fresh-character convention used by the questionnaire path. Strength
is normalized with a lower bound before commit. The precise scale factors,
caps, and formulas for converting Ultima IV values into Ultima V values remain
open.

Class handling is also unresolved. Character creation leaves the Avatar class
as the seed's Avatar class. The transfer path contains evidence of class or
class-display normalization, but the current notes do not yet prove whether
Ultima IV class is ever preserved, translated, or always forced back to
Avatar.

## 8. Commit And Abort

All transfer edits happen in memory until the final commit. Before that point,
an abort returns to the intro menu without writing `SAVED.GAM` or `SAVED.OOL`.
The in-memory seed image may have been changed, but that is not durable; the
next Journey Onward or creation attempt reads from disk again.

On commit, the transfer writes the normal Ultima V save files:

1. Compose the object-overlay companion from the loaded object seed and a blank
   counterpart plane.
2. Write `SAVED.OOL`.
3. Write the full save image to `SAVED.GAM`.
4. Return to intro/menu state.

The commit is destructive to the existing working save slot. There is no
separate confirmation that the previous Ultima V save should be replaced, no
backup file, and no multi-slot selection. A compatible implementation should
treat transfer commit the same way chargen commit is treated: it writes the
single canonical working save.

The transfer path does not write `INIT.GAM` or `INIT.OOL`. It also does not
itself perform the Journey Onward mirror writes to `BRIT.OOL` and `UNDER.OOL`;
those belong to the standard load/save system. After transfer, Journey Onward
will read the newly-written `SAVED.GAM` and run the ordinary save-load
housekeeping.

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
3. Locate and read the Ultima IV source save.
4. Build an in-memory Ultima V save image from the seed.
5. Patch only the Avatar-facing fields that transfer owns.
6. Render a roster/status preview and allow name/gender correction.
7. Abort without disk writes if the player cancels before commit.
8. On commit, write `SAVED.OOL` and `SAVED.GAM`.
9. Return to the intro/menu flow and let Journey Onward load the save.

An implementation may skip floppy-style prompt rendering when all files live
in one directory, but it should keep the same commit boundary: media failure
or malformed transfer data must not overwrite the existing Ultima V save.

## 12. Open Questions

- **Ultima IV source parse.** The exact predecessor filename, record layout,
  completion checks, and malformed-save behavior remain unresolved.

- **Primary stat mapping.** The transfer definitely normalizes primary stats
  into Ultima V fields, but the exact scale factors, caps, and lower bounds
  for strength, dexterity, and intelligence need a deeper transfer pass.

- **Magic points.** Initial MP follows the imported intelligence value in the
  observed write path, but whether any U4-specific class or level bonus can
  alter it is not yet proven.

- **Hit points, level, and experience.** The preview and write path touch
  these fields. The formulas that relate Ultima IV progress to Ultima V
  current HP, maximum HP, level, and experience are still open.

- **Class mapping.** It is not yet clear whether transfer can preserve or
  translate a U4 class, or whether the Avatar class is always restored from
  the Ultima V seed.

- **Object companion half order.** Transfer composes a two-plane
  `SAVED.OOL` from one loaded object seed and one blank plane. The precise
  half ordering should be verified alongside the existing chargen
  `SAVED.OOL` ordering question.

- **Preview coverage.** The transfer screen clearly shows the travelling
  party/status presentation, but the exact slot count and screen layout should
  be verified against a captured run if pixel-accurate reproduction is needed.

- **Post-commit UI.** Static analysis indicates transfer returns through the
  intro/menu redraw path after writing. A DOSBox capture should confirm the
  exact visible sequence, especially because older high-level summaries
  describe the path as play-producing.

## 13. Sources

The behavior described here is cleanroom prose derived from the notes and
existing cleanroom specs listed below. No assembly excerpts, decompiled code,
private offsets, or binary text dumps are reproduced.

- Transfer seed reads, disk-state setup, roster/status preview, confirmation
  loop, field writes, and final `SAVED.GAM` / `SAVED.OOL` commit:
  `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Intro menu entry and return-to-menu context:
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Standard Journey Onward load, empty-save guard, object-overlay mirror
  behavior, and media retry context:
  `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- Character creation seed and commit behavior used for comparison:
  `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- Save-image and object-overlay file roles:
  `u5-decomp/formats/saves.md`.
- Existing cleanroom cross-checks:
  `u5-spec/systems/intro.md`, `u5-spec/systems/chargen.md`,
  `u5-spec/systems/save-load.md`, `u5-spec/formats/saved-gam.md`, and
  `u5-spec/formats/ool.md`.
