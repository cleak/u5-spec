# Endgame

## 1. Overview

The endgame is Ultima V's terminal victory sequence. Once entered, it stages a Lord British throne-room scene, asks the player to confirm delivery of the sandalwood box, runs a final cinematic, prints an Avatarhood certificate, and stops the game permanently.

This is not a normal gameplay mode. It does not run the main scene loop, it does not advance world time, and it does not return to the scene-byte dispatcher described in `main-loop.md`. Both the successful ending and the refusal or missing-box branch are terminal from the player's point of view. The original program leaves the player at the ending screen or ending tableau until the machine is reset or the process is otherwise killed.

The sequence reads existing saved state but is not a save/load flow:

- the party leader's name appears in the final certificate;
- the current in-game date is used for the certificate date;
- the party roster is used for the throne-room tableau and certificate leader;
- the sandalwood-box completion flag gates the real victory branch;
- dead party members are restored for presentation in the endgame scene;
- no save file is written after these presentation mutations.

## 2. Entry and trigger

The endgame is reached from the main-quest completion path, not from ordinary
scene dispatch. The public prerequisite chain is:

1. The three Shadowlords have been vanquished, which opens the Doom entrance.
2. The Doom Word of Power participates in the Doom-side seal route. Its target
   coordinate in the resident word table is the centered Underworld/Doom-side
   coordinate, not a Lord British throne-room conversation target.
3. The party has obtained the Sandalwood Box story item, which sets the
   save-backed box flag used by the ending.
4. The party reaches Doom's deepest final room trigger. In stock data this is
   Doom level seven, local coordinate `(X=5, Y=7)`, with room id fifteen.
5. That room selects the final Doom `DUNGEON.CBT` arena slot. The room setup
   scan consumes the arena metadata cell that carries the `0x3C` absorbable-field
   family marker, placing it as a special active-object marker for combat.
6. Dungeon-room or post-combat cleanup consumes that marker and reaches the
   endgame overlay entry.

The endgame overlay has a normal export entry, and the low-level static caller
census now resolves its direct callers as dungeon-room and post-combat cleanup
paths. Both callers are gated by the same special combat absorption marker: when
the marker has the terminal handoff value, the cleanup path enters the endgame
overlay instead of returning to ordinary dungeon or post-combat play. This is
not an ordinary Lord British throne-room TALK keyword route, and no public
contract should require talking to Lord British as the mechanical caller of the
overlay entry.

The marker writer itself is the special combat absorption effect described in
`combat.md`. A clean implementation does not need to emulate the original
overlay-loader indirection literally, but it should preserve the player-visible
result: when the completed quest's Doom final-room combat handoff fires, the
game enters the terminal endgame state rather than returning to ordinary play.
The Sandalwood Box is checked inside the endgame overlay for the victory branch;
it is not the low-level caller predicate for entering the overlay.

The endgame overlay itself contains the terminal sequence and performs its own
Lord-British-styled confirmation and saved-flag check. This dialogue is inside
the terminal overlay; it should not be treated as evidence for a normal
Lord-British throne-room conversation service. The implementation contract is:

1. A completed-quest handoff transfers control into the endgame state.
2. The endgame state presents the box-delivery confirmation dialogue.
3. The endgame state performs its own confirmation and saved-flag check before
   granting the ending.

The overlay does not rely only on the caller to prove completion. It also reads the save-backed sandalwood-box ownership flag set by the shared item-acquisition path. A player-visible "yes" answer is not enough by itself: if the saved completion flag is absent, the sequence falls into the non-victory branch.

The sandalwood box is the same story item listed in `catalogs/item-list.md`.
The item catalog identifies the item and its broad role; this system spec
describes only the final handoff behaviour. The pickup route is specified in
the item and container specs: a fixed `CASTLE:0` object-slot pickup reaches the
shared item-add writer and sets the save-backed flag. No traced acquisition
handler requires Saduj's clue conversation as a mechanical prerequisite.

## 3. Resource and scene setup

On entry, the endgame takes over the screen and scene state:

1. Mark the resident state as being in the endgame, so normal world redraw behaviour no longer applies.
2. Reset the screen and palette state.
3. Load endgame-specific data resources for the throne-room/cinematic scene and Lord British message records.
4. Load and draw the endgame bitmap assets through the same resident image-loading path used elsewhere.
5. Clear the active-object table and rebuild it as a cinematic tableau rather than as a gameplay object list.

The initial entry path loads `MISCMAPS.DAT` for the tableau and `ENDMSG.DAT`
for the Lord British dialogue. `END.DAT` is not part of that opening dialogue
load. It is consumed later by the final narrative presentation helper, which
reuses the message scratch buffer after the Lord British records are no longer
needed.

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

### Party tableau active-object layout

The endgame reuses the active-object record shape described in
`active-objects.md`, but the records are cinematic sprites rather than live
map objects. On entry, the original clears only each slot's type and
tile/frame bytes for all 32 active-object slots, then rebuilds the tableau.
The setup sites listed below write type, tile/frame, X, Y, and phase; they
do not initialize the record's floor/Z or auxiliary bytes. Clean engines
should treat this scene as a single cinematic plane rather than deriving
gameplay floor semantics from those untouched bytes.

The renderer's ordinary active-object order still matters: slots are scanned
from 31 down to 0, so lower-numbered slots draw on top when sprites overlap.
That means the party leader in slot 0 draws above other party members, Lord
British in slot 6, and the scene marker in slot 31.

| Slot | Role | Initial type/tile | Initial X,Y | Phase | Initial settled target |
|---:|---|---:|---|---:|---|
| 0 | Active party member 0 / party leader | Class table | 5,9 | 0 | 5,5 |
| 1 | Active party member 1 | Class table | 5,9 | 0 | 4,6 |
| 2 | Active party member 2 | Class table | 5,9 | 0 | 6,6 |
| 3 | Active party member 3 | Class table | 5,9 | 0 | 3,7 |
| 4 | Active party member 4 | Class table | 5,9 | 0 | 5,7 |
| 5 | Active party member 5 | Class table | 5,9 | 0 | 7,7 |
| 6 | Lord British, victory branch only | `0x0E` | 5,4 | 0 | Created already at target |
| 31 | Scene marker | `0x7C` | 5,8 | 0 | Branch-specific |

Party slots are populated only for active party indices below the current
party count. The setup loop does not synthesize absent party members for
empty slots above the party count.

The party type and tile/frame bytes are both initialized from the class table:

| Class byte | Class | Tableau type/tile |
|---|---|---:|
| `A` | Avatar | `0x4C` |
| `M` | Mage | `0x40` |
| `B` | Bard | `0x44` |
| `F` | Fighter | `0x48` |
| `D` | Druid | `0x4C` |
| `T` | Tinker | `0x4C` |
| `P` | Paladin | `0x4C` |
| `R` | Ranger | `0x4C` |
| `S` | Shepherd | `0x4C` |

Only the Dead status has a special restoration branch during tableau setup:
it is changed to the restored/present status and current health is copied from
maximum health. Asleep, poisoned, ashes, and other non-Dead statuses are not
filtered by this setup pass; those party records are still assigned tableau
actors from their class byte.

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

The refusal/missing-box branch uses the same initial party tableau setup, then
changes the scene as follows:

1. Slot 0's Y coordinate is decremented once.
2. The script repeatedly steps slot 2 toward (8,6), slot 31 toward (4,1),
   and slot 0 toward (8,4) until all three have arrived.
3. The terminal loop then jitters only slots 1, 3, 4, and 5. Slot 0, slot 2,
   Lord British's slot, and the scene marker do not participate in that jitter
   loop.

The jitter helper is a local cinematic wander. On each call for an occupied
slot, movement is first throttled by a random yes/no gate. If movement is
allowed, the helper tries up to eight random cardinal candidates:

| Random result | Candidate |
|---:|---|
| 0 | `x + 1` |
| 1 | `x - 1` |
| 2 | `y + 1` |
| 3 | `y - 1` |

The first candidate whose local scene-buffer cell is the authored walkable
marker `0x44` is committed. Other cell values are blocked. The helper does
not check active-object occupancy, so actor-to-actor collision is not part of
this terminal wander rule. Each call advances the display tick once whether
or not movement is committed.

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

The movement predicate used by the endgame is grid based: each call examines one active-object slot and moves it one cell toward a target, preferring the axis with the greater remaining distance. The caller repeats this until the slot reaches the target.

The separate tableau animation helper is a random local wander, not an animation-frame table. When the selected active-object slot is occupied, the helper first throttles the step with a two-outcome random roll. On an allowed step it samples up to eight four-direction candidates around the current cell, in random direction order, and commits the first candidate whose scene cell is marked as part of the endgame tableau's walkable region. If no candidate qualifies, the slot remains where it is for that call. The helper then advances the display/palette tick once before returning.

This helper is used by the terminal "wait here a while" tableau for party-member slots rather than by ordinary gameplay movement. It should be modeled as cinematic jitter within the authored endgame scene, not as a reusable NPC pathfinder, not as a direction-facing animation switch, and not as evidence for an unresolved party-sprite facing map.

The scripted victory movement order is:

1. Step slot 0 from its initial settled position to (5,4), then back to
   (5,5).
2. Create Lord British in slot 6 at (5,4) with type/tile `0x0E`.
3. Print the Lord British message beats.
4. Change Lord British's slot 6 type/tile to `0x08`.
5. After the long wait, clear Lord British's slot 6 type/tile.
6. Move slot 31, the scene marker, to (5,4), then clear its type/tile.
7. For each active party slot in ascending party order, step that slot to
   (5,4), then clear its type/tile before advancing to the next party slot.

The step helper moves one cell per call and runs one display tick after each
movement. It prefers the axis with greater remaining distance; equal remaining
distance chooses X movement. The caller loops until the current actor reaches
its target before advancing to the next scripted actor or message beat.

The display effects are palette/display operations and full-screen rectangle transitions driven by resident helpers. The exact helper names are implementation details. The compatibility requirement is the order and blocking nature of the presentation: messages pause, movement settles before the next beat, and the final certificate is reached only after the fade/transition sequence completes.

The late orb/certificate path includes one traced full-screen rectangle
operation after the pulse/fade and panel-transition sequence and before the
certificate setup. Its bounds are the full inclusive 320-by-200 surface:
`(0, 0)..(319, 199)`. The immediate caller does not sample input around that
operation. Current evidence is sufficient to preserve its ordering and
full-screen bounds, but not to model it as the intro-style column reveal or to
assign a per-column tick cadence.

## 8. Final narrative presentation

Immediately before the final scroll, the endgame runs a fixed narrative
presentation sequence. This is not a party-roster retirement lookup and it does
not open town, dwelling, castle, or keep location data to resolve character
homes. The helper opens endgame presentation graphics resources, loads fixed
windows from `END.DAT`, renders the selected window with proportional text, and
uses blocking waits between presentation beats.

The helper's presentation role is:

- retry required endgame graphics and text resources until they are available;
- keep the proportional font and endgame scene graphics resident while the
  presentation runs;
- select one of six fixed `END.DAT` windows from presentation control records;
- draw foreground panels or sprites from the endgame graphics resources around
  the loaded text window;
- wait for player input between narrative windows after the first automatic
  setup beat;
- clear presentation state and continue into the final certificate scroll.

The six fixed windows form two narrative groups:

| Window group | Presentation role |
|---|---|
| Return-home sequence | The Avatar returns from Britannia to the familiar circle of stones, enters the old home, and confronts the emotional aftermath of the quest. |
| Blackthorn judgment and gate sequence | Lord British and Blackthorn share the closing judgment scene, the Orb/Gate choice is presented, and Blackthorn's exile resolution is shown. |

Each selected window is bounded by the caller rather than by an in-file table.
Brace markers inside `END.DAT` remain layout/page markers for the text
renderer. A clean implementation should keep the six window selections
data-driven, but their semantic role is fixed narrative presentation, not
party-slot retirement data.

The exact page-in transition rectangles and reveal rates for the six fixed
`END.DAT` narrative windows are not promoted into this baseline because the
current endgame entry trace does not expose a six-per-window page-in rectangle
table. The traced endgame entry surface identifies one full-screen rectangle
operation in the late orb/certificate transition path, but that is not evidence
for six distinct `END.DAT` page wipes, and that full-screen operation belongs
after the final transition sequence rather than to the ordinary fixed-window
narrative helper. Do not inherit the intro step-1 rectangle or
one-column-per-title-tick rate for these endgame windows unless a caller-specific
trace supplies the endgame bounds and rate.

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

The elapsed-time baseline is year 139, month 4, day 5. The calculation subtracts that baseline from the saved world clock, borrows twenty-eight days from the month delta when the day delta is negative, and borrows thirteen months from the year delta when the month delta is negative. Separators are emitted only between printed nonzero units, so "years, months, days" collapses naturally when any component is zero.

When this output finishes, the original program enters an intentional infinite loop. There is no keypress-to-continue, no return to title, no DOS exit, and no automatic save.

## 10. State effects

The endgame has a small number of state effects. Most are safe only because the sequence is terminal.

| State | Effect |
|---|---|
| Endgame mode flag | Set on entry so normal scene redraw no longer owns the display. |
| Sandalwood-box completion flag | Save-backed story item flag set by item acquisition, read during confirmation, and not cleared by the endgame notes. |
| Party roster | Read for names, party size, class/sprite selection, date/certificate leader, and the throne-room tableau. |
| Dead party members | Mutated into a present/restored state for the ending tableau, with current health restored from the stored maximum. |
| Active-object table | Cleared and repopulated as cinematic sprites and markers. These are not live world objects. |
| World clock | Read for the certificate and elapsed-time calculation. It is not advanced by the endgame. |
| Save files | Not written by the endgame. |
| Main loop scene byte | Not used as a route back to gameplay after the endgame starts. |

The lack of a save write is important. If the original process is reset after the ending, the last durable save remains whatever it was before the endgame was entered. The cinematic restoration of dead party members and the overwritten active-object table are not committed by the ending itself.

## 11. Implementation notes

A modern engine should model the endgame as a terminal application state entered
from the completed-quest handoff. It should not be implemented as a normal map,
town mode, or outer-loop dispatch branch.

Recommended implementation structure:

1. Route the completed-quest dungeon/post-combat handoff into `enterEndgame()`;
   the handoff is driven by the special combat absorption marker, while the
   overlay still performs its own sandalwood-box saved-flag check.
2. `enterEndgame()` freezes normal gameplay and captures the live saved state needed by the sequence.
3. A resource-loading step obtains the endgame messages, final narrative text,
   proportional font, and endgame graphics resources. `ENDMSG.DAT` is needed
   for the Lord British dialogue; `END.DAT` is loaded later for the fixed final
   narrative windows. The endgame `.DAT` resources are read through the generic
   retrying file helper as plain data; this path is not the paired-graphics LZW
   envelope.
4. A cinematic scene object owns party/Lord British sprites instead of mutating the live active-object table directly.
5. The two confirmation prompts run as blocking UI prompts.
6. The refusal branch transitions to a terminal wait/tableau state.
7. The success branch runs the ceremony, final narrative presentation, certificate, and terminal final screen.

For compatibility, keep these details:

- accept the two visible confirmations in order;
- gate success on the final confirmation and the saved sandalwood-box state;
- do not consume turns, advance time, or run NPC schedules during the sequence;
- do not write a save as part of the ending;
- preserve the final no-exit behaviour unless adding an explicit modern restart affordance;
- keep the certificate date and elapsed-time calculations tied to the saved world clock and the thirteen-month, twenty-eight-day calendar.

The original resource loaders busy-wait forever on missing files. A modern implementation should fail with a clear asset error, but it should not silently skip the endgame resources or proceed with partial text/graphics.

The original uses the active-object renderer for cinematic movement. A modern engine can instead use a dedicated cinematic sprite layer, provided it preserves the visible ordering: party tableau, confirmation, Lord British messages, orb/fade transition, fixed `END.DAT` narrative presentation, certificate, final terminal state.

## 12. Gaps and open questions

- **Pixel-perfect endgame scene rasters.** The terminal tableau slot layout,
  sprite ids, movement order, and local wander rule are specified here. Exact
  per-frame display-helper internals for every fade/palette transition remain
  presentation-parity work.
- **Final narrative page-in transitions.** The six fixed `END.DAT` windows and
  their narrative roles are specified. The traced endgame entry surface has one
  late full-screen rectangle operation, not a six-entry page-in rectangle table;
  per-window transition rectangles and reveal rates therefore remain
  unspecified unless a more specific caller trace identifies them.
- **Display helper taxonomy.** The visual sequence uses resident display, palette, sound, and wait helpers whose exact labels are inferred. The player-visible order and blocking boundaries are specified; the unresolved part is helper taxonomy, not state progression.
- **Asset variant mapping.** The paired graphics archive family and bitmap formats are specified, but exact endgame resource-slot-to-panel selection should be cross-checked if pixel-perfect presentation parity becomes required.

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
- `u5-decomp/functions/ENDGAME_OVL/_OVERVIEW.md`
- `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`
- `u5-decomp/functions/DUNGEON_OVL/0x0000_dungeon_room_enter.md`
- `u5-decomp/functions/DNGLOOK_OVL/0x117E_setup_room_npcs.md`
- `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md`
- `u5-decomp/functions/SJOG_OVL/0x1458_sjog_inventory_add.md`
- local binary checks against `C:\Games\U5-Clean\DUNGEON.DAT`,
  `DUNGEON.CBT`, and `DATA.OVL` for the Doom final-room trigger and
  setup marker plus Word-of-Power coordinate binding.
- local binary checks against `C:\Games\U5-Clean\DATA.OVL` and `END.DAT`
  for the fixed final-presentation asset table and six text-window starts.
- `u5-decomp/notes/system-trace_quest-endgame.md`
- `u5-decomp/notes/lord_british_dialogue.md`

Local spec cross-references used for terminology and integration:

- `u5-spec/systems/main-loop.md`
- `u5-spec/systems/save-load.md`
- `u5-spec/systems/text-output.md`
- `u5-spec/catalogs/item-list.md`
