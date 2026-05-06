# Endgame

## 1. Overview

The endgame is Ultima V's terminal victory sequence. It is entered when Lord British's dialogue accepts the return of the sandalwood box, then it stages a throne-room scene, asks the player to confirm the delivery, runs a final cinematic, prints an Avatarhood certificate, and stops the game permanently.

This is not a normal gameplay mode. It does not run the main scene loop, it does not advance world time, and it does not return to the scene-byte dispatcher described in `main-loop.md`. Both the successful ending and the refusal or missing-box branch are terminal from the player's point of view. The original program leaves the player at the ending screen or ending tableau until the machine is reset or the process is otherwise killed.

The sequence reads existing saved state but is not a save/load flow:

- the party leader's name appears in the final certificate;
- the current in-game date is used for the certificate date;
- the party roster is used for the final character presentation;
- the sandalwood-box completion flag gates the real victory branch;
- dead party members are restored for presentation in the endgame scene;
- no save file is written after these presentation mutations.

## 2. Entry and trigger

The semantic trigger is Lord British's box-delivery conversation path. A faithful implementation should enter this state only from Lord British's throne-room dialogue after the player reaches the branch that asks about returning the box.

The exact binary caller has not yet been identified. The endgame overlay itself contains the terminal sequence, but the static notes do not yet prove which TALK or command handler transfers control into it. The safe implementation contract is therefore:

1. Lord British dialogue offers or reaches the box-delivery branch.
2. The endgame state is entered.
3. The endgame state performs its own confirmation and saved-flag check before granting the ending.

The overlay does not rely only on the caller to prove completion. It also reads a saved quest flag that appears to represent the sandalwood-box state. A player-visible "yes" answer is not enough by itself: if the saved completion flag is absent, the sequence falls into the non-victory branch.

The sandalwood box is the same story item listed in `catalogs/item-list.md`. The item catalog identifies the item and its broad role; this system spec describes only the final handoff behaviour. The acquisition path, inventory flag writer, and any earlier puzzle gates remain outside this document.

## 3. Resource and scene setup

On entry, the endgame takes over the screen and scene state:

1. Mark the resident state as being in the endgame, so normal world redraw behaviour no longer applies.
2. Reset the screen and palette state.
3. Load endgame-specific data resources for the throne-room/cinematic scene and Lord British message records.
4. Load and draw the endgame bitmap assets through the same resident image-loading path used elsewhere.
5. Clear the active-object table and rebuild it as a cinematic tableau rather than as a gameplay object list.

The original loader retries indefinitely if required resources are not available. A modern implementation can report a missing-asset error instead, but it should treat the sequence as blocked until the resources are present.

The active-object table is reused because the original engine already has sprite movement and drawing helpers for those records. During the endgame, the table no longer represents the live map. It represents the party, Lord British, and scene markers used by the cinematic. Since the endgame has no normal return path, these writes are presentation state rather than gameplay state.

## 4. Party tableau and restoration pass

Before Lord British's main dialogue, the endgame walks the active party slots and prepares each visible party member for the throne-room tableau.

For each party member:

- if the character is marked dead, the sequence announces their restoration, changes the character to a present/active post-death state, restores current health from the stored maximum, plays a short audio/visual flourish, and waits briefly;
- the character's class or role is mapped to a sprite used in the tableau;
- the character is placed into an active-object slot at the starting position for the scene;
- the movement helper steps that slot toward its target until it arrives.

The restoration is part of the ending presentation. Because the sequence cannot return to gameplay or save afterward, these mutations should not be interpreted as a normal resurrection service that the player can carry back into the world. A modern implementation with a post-ending menu should avoid writing these cinematic changes into a resumable save unless it deliberately defines a new post-game mode.

## 5. Lord British dialogue and confirmation

After setup, Lord British greets the party leader by name and presents a two-step box-delivery confirmation. The text itself is data-driven; this spec intentionally describes the content rather than reproducing the original wording.

The dialogue flow is:

1. Lord British greets the Avatar and asks whether the player brought his box.
2. The player answers yes or no.
3. The game echoes the answer into the dialogue stream.
4. Lord British asks again, explicitly identifying the sandalwood box.
5. The player answers yes or no.
6. The game echoes the second answer.
7. The branch decision is made from the second answer and the saved sandalwood-box completion flag.

Compatibility note: the observed control flow stores both answers, but the branch into the victory rite is controlled by the final confirmation together with the saved completion flag. The first answer is still visible and should still be accepted and echoed, but strict compatibility does not treat it as an independent final gate after the second answer is collected.

The confirmation is a blocking prompt. While it waits, normal gameplay turns, world ticks, NPC schedules, and time advancement do not run.

## 6. Refusal or missing-box branch

If the final confirmation is not yes, or if the saved sandalwood-box completion flag is absent, the sequence does not return the player to ordinary conversation. Instead, Lord British moves into a non-victory ending tableau: the player is made to wait with him, the party is seated or animated around the scene, and the endgame remains there indefinitely.

This branch is terminal in practice. It does not restore the previous map, re-enter the main loop, return to the title menu, or offer a new prompt to resume play. A modern implementation should treat it as a dead-end ending state. If an implementation adds a restart or title-menu command for usability, that command should be an out-of-band modern affordance rather than part of the original endgame state.

## 7. Victory rite and visual animation

If the final confirmation is yes and the saved completion flag is present, the endgame enters the victory rite. The rite is a scripted cinematic, not a gameplay loop.

The visible sequence has these functional parts:

1. Palette and display-state changes prepare the screen for the ceremony.
2. Party-member active-object slots are stepped into their target positions.
3. Lord British is placed as a separate scene sprite.
4. A series of Lord British message records is printed with page pauses between records.
5. The scene changes to the orb/cinematic portion of the ending.
6. Timed waits, palette pulses, and fade-like display steps create the visual transition.
7. Scene markers are cleared, a final panel or zoom transition runs, and the screen is prepared for the certificate.

The movement predicate used by the endgame is grid based: each call examines one active-object slot and moves it one cell toward a target, preferring the axis with the greater remaining distance. The caller repeats this until the slot reaches the target. A separate animation helper advances character slots through a small set of poses or directions; the exact pose mapping is still unresolved, but the behavioural role is clear: it gives motion to the party members during the terminal scenes.

The display effects are palette/display operations and full-screen rectangle transitions driven by resident helpers. The exact helper names are implementation details. The compatibility requirement is the order and blocking nature of the presentation: messages pause, movement settles before the next beat, and the final certificate is reached only after the fade/transition sequence completes.

## 8. Roster and retirement presentation

Immediately before the final scroll, the endgame prepares per-character roster data. It reads the six party records and opens location data files used to resolve the home or retirement location associated with each character.

The helper's presentation role is:

- read each party-slot record;
- resolve the character's associated location from the location data families;
- render a per-character screen using the character's name, class or sprite data, and location;
- handle dead or inactive characters through a separate presentation branch;
- wait for player input at least once before continuing into the scroll.

This is not the normal save/load roster handling from `save-load.md`. It is a final presentation pass over live saved state. It opens world location resources because those files contain the names or signs needed for the retirement display, not because the player is entering those maps again.

The exact per-character home-location index table is still incomplete. Implementations that need full compatibility should keep this as data-driven and verify the index-to-location mapping before freezing the final roster presentation.

## 9. Certificate scroll

The certificate scroll is the final successful ending screen. It uses the text-output system, but with a small endgame-specific line accumulator so the overlay can compose a line from multiple fragments before flushing it to the screen.

The certificate body is assembled from:

- the current saved day, rendered as an ordinal word;
- the current saved month number, also rendered as an ordinal word;
- the current saved year, rendered in words split into hundreds and remainder;
- the party leader's name;
- a short royal salvation statement naming Lord British, the people, and the land;
- a centered Codex-style closing title rendered through the sign/tile-glyph text path rather than ordinary prose text.

The month is treated as a numbered month for this output, not as a named month. The ordinal helper covers the game's calendar range and composes twenty-first through twenty-eighth style ordinals from smaller word fragments. The cardinal helper covers the year fragments used by the certificate.

After the certificate body, the scroll clears or advances to a final report panel. It computes elapsed campaign time from the fixed campaign start date using the same thirteen-month, twenty-eight-day calendar model used by the rest of the game. Negative day or month differences borrow from the next larger unit. The result is printed as numeric years, months, and days, omitting zero-value units and applying singular or plural labels as needed. The final line asks the player to report the completed quest to Origin.

When this output finishes, the original program enters an intentional infinite loop. There is no keypress-to-continue, no return to title, no DOS exit, and no automatic save.

## 10. State effects

The endgame has a small number of state effects. Most are safe only because the sequence is terminal.

| State | Effect |
|---|---|
| Endgame mode flag | Set on entry so normal scene redraw no longer owns the display. |
| Sandalwood-box completion flag | Read during confirmation; not cleared by the endgame notes. |
| Party roster | Read for names, party size, class/sprite selection, date/certificate leader, and final roster display. |
| Dead party members | Mutated into a present/restored state for the ending tableau, with current health restored from the stored maximum. |
| Active-object table | Cleared and repopulated as cinematic sprites and markers. These are not live world objects. |
| World clock | Read for the certificate and elapsed-time calculation. It is not advanced by the endgame. |
| Save files | Not written by the endgame. |
| Main loop scene byte | Not used as a route back to gameplay after the endgame starts. |

The lack of a save write is important. If the original process is reset after the ending, the last durable save remains whatever it was before the endgame was entered. The cinematic restoration of dead party members and the overwritten active-object table are not committed by the ending itself.

## 11. Implementation notes

A modern engine should model the endgame as a terminal application state entered from Lord British conversation. It should not be implemented as a normal map, town mode, or outer-loop dispatch branch.

Recommended implementation structure:

1. `enterEndgame()` freezes normal gameplay and captures the live saved state needed by the sequence.
2. A resource-loading step obtains the endgame messages, bitmaps, and location-name resources.
3. A cinematic scene object owns party/Lord British sprites instead of mutating the live active-object table directly.
4. The two confirmation prompts run as blocking UI prompts.
5. The refusal branch transitions to a terminal wait/tableau state.
6. The success branch runs the ceremony, roster presentation, certificate, and terminal final screen.

For compatibility, keep these details:

- accept the two visible confirmations in order;
- gate success on the final confirmation and the saved sandalwood-box state;
- do not consume turns, advance time, or run NPC schedules during the sequence;
- do not write a save as part of the ending;
- preserve the final no-exit behaviour unless adding an explicit modern restart affordance;
- keep the certificate date and elapsed-time calculations tied to the saved world clock and the thirteen-month, twenty-eight-day calendar.

The original resource loaders busy-wait forever on missing files. A modern implementation should fail with a clear asset error, but it should not silently skip the endgame resources or proceed with partial text/graphics.

The original uses the active-object renderer for cinematic movement. A modern engine can instead use a dedicated cinematic sprite layer, provided it preserves the visible ordering: party tableau, confirmation, Lord British messages, orb/fade transition, roster presentation, certificate, final terminal state.

## 12. Gaps and open questions

- **Actual caller.** The decomp notes identify the Lord British box-delivery branch as the semantic trigger, but the exact caller that transfers control into the endgame overlay is still unresolved.
- **Sandalwood-box flag writer.** The endgame reads a completion flag, but the note set does not yet identify where the flag is set when the box is acquired.
- **First confirmation semantics.** The first yes/no answer is displayed and echoed, but the final branch appears to be controlled by the second answer plus the completion flag. This should be verified against live gameplay before deliberately "fixing" the behaviour.
- **Roster location mapping.** The final roster helper reads location data to resolve per-character homes or retirement locations, but the exact index-to-location mapping remains incomplete.
- **Dead/inactive character presentation.** The main restoration pass is clear, but one special branch in the roster helper still needs a full behavioural decode.
- **Animation pose mapping.** The helper that advances character animation slots has an unresolved small switch. The high-level role is known; exact poses or directions are not.
- **Display helper identities.** The visual sequence uses resident display, palette, sound, and wait helpers whose exact names are inferred. The player-visible order is better established than the helper taxonomy.
- **Asset variant mapping.** The endgame loads bitmap resources through the resident image path, but the exact high-colour/low-colour filename selection belongs with the graphics format specs and should be cross-checked there.

## 13. Sources

This document is a cleanroom prose rewrite from the following source notes. It intentionally omits assembly, decompiled code, private offsets, and copied binary text dumps.

- `u5-decomp/functions/ENDGAME_OVL/0x0648_endgame_entry.md`
- `u5-decomp/functions/ENDGAME_OVL/0x0000_endgame_load_party_roster.md`
- `u5-decomp/functions/ENDGAME_OVL/0x023A_fn_buffer_print.md`
- `u5-decomp/functions/ENDGAME_OVL/0x028C_print_number_word.md`
- `u5-decomp/functions/ENDGAME_OVL/0x02D6_print_day_ord.md`
- `u5-decomp/functions/ENDGAME_OVL/0x0326_print_scroll.md`
- `u5-decomp/functions/ENDGAME_OVL/0x0510_prompt_yes_no.md`
- `u5-decomp/functions/ENDGAME_OVL/0x05A2_character_anim_scene.md`

Local spec cross-references used for terminology and integration:

- `u5-spec/systems/main-loop.md`
- `u5-spec/systems/save-load.md`
- `u5-spec/systems/text-output.md`
- `u5-spec/catalogs/item-list.md`
