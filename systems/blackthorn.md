# Blackthorn Capture And Rescue

## 1. Scope

This spec covers the Blackthorn-specific cinematic overlay: the capture
audience, the virtue or Word-of-Power challenge, the punishment animation, and
the later rescue or refuge sequence.

It does not own ordinary conversation with Blackthorn's castle NPCs, ordinary
combat AI for the Blackthorn monster class, magic absorption in Blackthorn's
castle, or the endgame victory sequence. Those remain in
`systems/conversation.md`, `systems/combat.md`, `systems/magic.md`, and
`systems/endgame.md`.

## 2. Entry Families

The Blackthorn overlay exposes two player-visible scene families:

| Family | Visible role | Remaining trigger gap |
|--------|--------------|-----------------------|
| Audience / capture | The party is subdued, taken before Blackthorn, challenged, and then routed to captivity or release state | Town-side direct entry predicate is traced; the earlier defeat/capture context that selects that captive state remains open |
| Rescue / refuge | A darkness-and-thunder cinematic restores the party and moves it to a refuge scene | Traced caller families are town-mode, overworld-mode, and dungeon-mode; exact per-mode story predicates remain open |

Both families are cinematic handlers. They replace the ordinary map loop while
they run, manage their own text and timing, and hand control back through an
explicit scene/position transition rather than by restoring the prior map.

The current cross-overlay call inventory identifies the audience entry as a
town-mode Blackthorn handler and the rescue/refuge entry as reachable from
town, overworld, and dungeon mode. The audience entry's town-side direct
predicate is now known: when the town post-action NPC event cleanup reaches
the arrest/unconscious handler while the current scene is the Blackthorn
captive scene, that handler enters the Blackthorn audience instead of asking
the ordinary Yew-arrest surrender question. The broader upstream condition
that placed the party into that captive context, including the death-route
marker described below, remains caller-owned.

For the rescue/refuge entry, the traced evidence identifies the mode families
that can hand control to the cinematic: town, overworld, and dungeon. That is
a call-family fact, not a story-predicate fact. The exact local gate in each
mode remains owned by the corresponding mode system until those callers are
fully traced.

## 3. Audience Setup

The audience path starts from a captured-party state. It counts the active
party members that are still eligible for the challenge, records the target
party slot, and then switches into a cutscene presentation.

The setup contract is:

1. Print the capture narration: the party is overcome, blinded, and dragged
   away by guards.
2. Skip party members already marked as jailed or otherwise outside the
   current challenge target set.
3. Clear the active-object table so the audience scene can reuse those records
   as temporary cinematic actors.
4. Load the Blackthorn audience map from `MISCMAPS.DAT`.
5. Load the Blackthorn message cluster from `MISCMSG.DAT`.
6. Place the party, Blackthorn, attendants or guards, and throne markers into
   cutscene actor slots.
7. Run the scripted throne approach and Blackthorn presentation beats.
8. Greet the current leader by name and print the gendered release line.
9. Enter the challenge loop.

The active-object writes in this flow are presentation state. They do not
describe the live town map and should not be saved back as ordinary world
objects.

During the opening capture pass, the handler skips party members already marked
as jailed. A separate capture death-route marker can turn the same presentation
into a death outcome instead of the ordinary "dragged away" imprisonment
branch; the traced overlay reads that marker but does not own the combat or
town predicate that set it. Treat the marker as caller-provided capture context,
not as a general Blackthorn AI flag.

The town-side direct entry runs through the ordinary town NPC-event cleanup,
but the captive-scene branch bypasses the normal arrest prompt. In ordinary
towns, the same arrest helper can ask whether the party will surrender and then
send the party to Yew or trigger guard hostility. In the Blackthorn captive
scene, it instead transfers to this audience/capture cinematic and then
re-enters town setup after the cinematic returns.

After the challenge resolves, the handler can run a final throne cleanup beat
and then hands control to a captive-cell scene. The traced handoff uses scene
byte eighteen, the gazetteer's `CASTLE:1` location associated with Lord
Blackthorn's Castle, with local position `(10, 7)`.

## 4. Challenge Loop

The challenge is a short, blocking question sequence tied to virtues and
Words of Power. It can ask up to four prompts. Each prompt is assembled from a
template, reads a short text answer from the player, and compares the answer
against a fixed expected string.

Compatibility rules:

- The prompt input accepts at most fourteen typed characters before comparison.
- Answer comparison is case-insensitive and substring-style: the expected word
  may appear anywhere in the typed buffer rather than being the entire input.
- The loop uses four fixed prompt ordinals. The active party-slot argument
  changes the prompt framing and the jailed target, but the traced answer
  lookup is indexed by prompt ordinal rather than by party slot.
- The four live prompt ordinals use the first four virtue names and answer
  syllables in paired order:

  | Prompt word | Accepted answer |
  |-------------|-----------------|
  | Honesty | `Ahm` |
  | Compassion | `Mu` |
  | Valour | `Ra` |
  | Justice | `Beh` |

  The resident tables also carry later virtue/mantra pairs, but this traced
  challenge loop only iterates the first four ordinals.
- A correct answer marks the current target party member as jailed or handled.
- If more than one eligible party member remains after a correct answer, the
  flow can silently route that member into jail state and continue.
- If the active count is too low, correct or wrong answers can end the loop
  through a reply-and-pause branch rather than continuing to another prompt.
- The challenge does not directly adjust numeric karma in the traced overlay.
  It reads moral or quest language for presentation, while durable virtue-score
  changes remain owned by the karma system.

The loop's party-slot argument is semantic: it names which companion is at
risk in the current capture branch. A compatible implementation should keep
the challenge party-targeted rather than treating it as a global yes/no quiz.

## 5. Failure Reaction

When the challenge fails on a branch that can punish a companion, Blackthorn
prints a reaction, runs a punishment animation, and names the party's second
visible member as the dragged-away victim.

The visible sequence is:

1. Build and print the failure reaction text.
2. Play the failed-challenge cutscene beat.
3. Move Blackthorn and the victim through the audience scene.
4. Print the static punishment fragments around the named victim.
5. Wait for player acknowledgement before returning to the caller branch.

The exact reaction-string builder and every static fragment's text remain
data-owned. This spec intentionally records the behavior and actor roles
rather than reproducing the source text.

## 6. Cutscene Script VM

The Blackthorn overlay uses a compact byte-script interpreter for these
cinematics. The interpreter is local to the Blackthorn audience/challenge
presentation and is separate from `.TLK` conversation scripts.

The script language supports:

- ending a script;
- setting a repeat count for following movement commands;
- switching between single-actor and paired-actor movement;
- enabling or disabling per-step pauses;
- emitting a control byte to the text or glyph output stream;
- writing one tile into the cutscene tile buffer;
- clearing the cutscene screen;
- running a timed pause;
- clearing one temporary actor slot; and
- moving one or two actor slots by cardinal steps.

The interpreter maintains three small pieces of modal state while it walks a
script:

- **Repeat count.** Defaults to one. A count-setting command changes how many
  times the next movement or pause command repeats, then the count resets to
  one after that command is consumed.
- **Paired movement mode.** A mode command makes the next movement consume a
  second movement descriptor, so two actors step together on each repeated
  tick. The mode resets after that movement.
- **Per-step pause mode.** A mode command enables or disables a one-tick pause
  after each individual movement step. This controls whether the actor motion
  is visibly animated one cell at a time or applied without per-cell delay.

Movement descriptors combine an actor family with a cardinal direction. The
known actor families are the Avatar, the second party member, Blackthorn, the
attendant, and the throne marker; the direction component moves that actor one
cell north, east, south, or west. A byte-compatible implementation may model
the compiled scripts as data, but the visible contract is actor-indexed
cardinal stepping with the modal repeat, paired-step, and pause rules above.

The public actor roles identified so far are:

| Slot | Role |
|------|------|
| 0 | Avatar / party leader presentation actor |
| 1 | Second party member, used by the failure punishment beat |
| 6 | Blackthorn |
| 7 | Attendant or guard |
| 8 | Throne or throne-marker tile |

The known script beats are the per-question intermission, the failed-answer
punishment, the audience throne approach, Blackthorn's rise or movement to the
throne, and a conditional throne cleanup after a successful audience flag. A
modern engine can model these as named cinematic actions as long as it
preserves actor order, pauses, tile writes, and final scene handoff.

The five traced scripts have these clean roles:

| Script beat | Caller context | Visible contract |
|-------------|----------------|------------------|
| Per-question intermission | Challenge prompt resolves through the early-exit branch | Drops a temporary marker into the cutscene tile buffer, walks Blackthorn and the Avatar through a short paired movement, moves the throne setup off-stage, clears the throne, Blackthorn, and attendant actors, then pauses. |
| Failed-challenge reaction | Challenge loop reaches the wrong-answer reaction | Emits formatting/control bytes around the reaction text, moves Blackthorn toward the second party member, drags that member off-stage with paired movement, clears the member actor, resets Blackthorn and the attendant, and writes two temporary scene tiles. |
| Audience throne approach | Audience opening before Blackthorn's main speech | Pauses, then moves Blackthorn and the attendant north together before splitting them horizontally so Blackthorn approaches the throne and the attendant shifts aside. |
| Blackthorn rises | After the release line and before the challenge loop | Emits a formatting/control byte, moves Blackthorn up onto the throne axis, and leaves him positioned for the challenge. |
| Conditional throne cleanup | Successful-audience cleanup flag is set | Emits a formatting/control byte, slides the throne marker away, clears the throne actor, and clears the cutscene screen. |

The tile-write commands and output-byte commands are specified only at the
semantic layer here: tile writes modify the cutscene tile buffer at an explicit
cell, and output-byte commands send one byte through the current text/glyph
output stream. The exact visual identities of the written tile bytes and the
exact cursor/glyph effects of those output bytes remain visual-parity work.

## 7. Rescue / Refuge Sequence

The second Blackthorn family is a rescue or refuge cinematic. It waits for the
overworld resource file to be available, switches into cutscene mode, prints a
darkness/refuge/thunder sequence, runs timed animation passes, places the
rescue scene tiles, then prints a selected `KARMA.DAT` verdict message.

The rescue contract:

1. Enter cutscene mode and suppress ordinary map play.
2. Clear terrain and temporary-object scratch state for the cinematic.
3. Print the darkness, refuge, thunder, and fortune-themed narrative beats.
4. Run the timed scene animation and tile placement passes.
5. Select and print one `KARMA.DAT` record through the five-band rescue
   selector.
6. Restore or update party members so the party can continue play.
7. Print the disorientation or vertigo beat.
8. Fade out and hand control to scene byte seventeen, the gazetteer's
   `CASTLE:0` location associated with Lord British's Castle, at local
   position `(10, 10)`.
9. Clamp the related story progression counter upward so the rescue cannot
   regress the save state.

`KARMA.DAT` is reused here as player-facing verdict text. This does not make
the file a numeric karma table. The rescue selector divides a one-byte verdict
input into five twenty-point bands: `0..19`, `20..39`, `40..59`, `60..79`, and
`80..99`, selecting records zero through four respectively. The shipped sixth
record is not selected by this traced rescue/refuge table.

## 8. State Boundaries

The Blackthorn overlay uses several kinds of state with different lifetimes:

| State | Lifetime |
|-------|----------|
| Jailed or handled party-member flags | Durable story/capture state |
| Active-object table during audience/rescue | Temporary cinematic actors |
| `MISCMAPS.DAT` cutscene map | Temporary scene background |
| `MISCMSG.DAT` audience records | Temporary message source |
| `KARMA.DAT` rescue record | Temporary verdict text source |
| Scene byte and local position handoff | Next ordinary gameplay location |
| Capture death-route marker | Caller-provided branch context for the audience presentation |
| Conversation Blackthorn signal | Transient one-conversation cleanup signal produced by TALK action handling; not the capture predicate or rescue trigger |
| Captive-cell duration/progression counter | Durable or semi-durable post-capture state; initialized if empty by the rescue path |
| Standing/progression byte clamp | Durable rescue/story floor |

Implementations should not conflate these. In particular, the active-object
table is repurposed for cinematic drawing, while party jail flags, the
post-capture counter, and the rescue progression counter are the durable
gameplay outputs. The death-route marker is read by the audience presentation
but should be set by the caller that decides the party's capture outcome.

The conversation-side Blackthorn signal belongs to the transient conversation
cleanup band described in `systems/quest-flags.md`. It can be produced by TALK
action handling and cleared by later cleanup or arrest/audience flows, but it
is not itself the upstream defeat/capture predicate, the death-route marker, or
the per-mode rescue/refuge trigger.

## 9. Relationship To Other Systems

- **Combat.** `systems/combat.md` owns ordinary Blackthorn class behavior and
  the defeat result that some callers can translate into capture.
- **Encounters.** `systems/encounters.md` owns scripted-fight framing before a
  Blackthorn-specific caller chooses capture, cancellation, or ordinary combat.
- **Conversation.** `systems/conversation.md` owns normal NPC Talk and `.TLK`
  execution. The Blackthorn challenge here is a separate cinematic prompt loop.
- **Karma.** `systems/karma.md` owns numeric virtue standings. This overlay
  can read virtue language and `KARMA.DAT` text but does not publish a traced
  in-overlay karma-score adjustment.
- **Magic.** `systems/magic.md` owns Blackthorn's-castle magic absorption and
  the Crown of Lord British pre-gate.
- **Endgame.** `systems/endgame.md` owns the terminal victory state. The
  Blackthorn rescue/refuge path resumes ordinary play instead.
- **Formats.** `formats/location-dat.md`, `formats/miscmsg-dat.md`, and
  `formats/karma-dat.md` own the file formats consumed by these scenes.

## 10. Blackthorn Boundaries And Remaining Entry Work

The overlay contract is complete for the traced cinematic behaviors:
audience/capture setup, challenge prompts and answer matching, punishment and
release branches, byte-script movement semantics, rescue/refuge restoration,
`KARMA.DAT` verdict selection, durable state writes, and the direct town-side
audience entry predicate are public.

Remaining exactness belongs to entry predicates and pixel parity:

- Pin the upstream defeat/capture predicate that sets the Blackthorn captive
  context and any death-route marker before the town-side audience entry.
- Pin the exact town, overworld, and dungeon story predicates that enter the
  rescue/refuge handler. The current overlay and cross-call evidence proves
  reachability from those mode families, but not the mode-local conditions.
- Verify the exact visual identities of the cutscene tile-write bytes and the
  exact cursor/glyph effects of the output-byte commands if pixel-level
  Blackthorn cutscene parity is required.

## 11. Sources

This cleanroom spec was derived from private analysis notes and sibling public
specs. It intentionally does not reproduce decompiled code, assembly, raw data
tables, raw script bytes, or implementation-specific addresses.

- `u5-decomp/functions/BLCKTHRN_OVL/bytecode_scripts.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/OVERVIEW.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x00BE_bytecode_interpreter.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x0510_challenge_pause_script.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x051C_challenge_reaction_text.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x054A_virtue_challenge_loop.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x060E_blackthorn_audience.md`.
- `u5-decomp/functions/BLCKTHRN_OVL/0x0910_blackthorn_rescue.md`.
- `u5-decomp/functions/TOWN_OVL/0x12AE_town_arrest_or_unconscious.md`.
- `u5-decomp/functions/TOWN_OVL/0x1352_town_post_action_cleanup.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- `u5-decomp/formats/data-ovl.md`.
- `u5-decomp/notes/subsystem_coupling_matrix.md`.
- `catalogs/gazetteer.md`.
- `systems/combat.md`.
- `systems/encounters.md`.
- `systems/karma.md`.
- `formats/location-dat.md`.
- `formats/miscmsg-dat.md`.
- `formats/karma-dat.md`.
