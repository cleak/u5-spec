# Blackthorn Capture And Rescue

## 1. Scope

This spec covers the Blackthorn-specific cinematic overlay: the capture
audience, the virtue or Word-of-Power challenge, the punishment animation, and
the later rescue or refuge sequence.

It also covers the regime's everyday guard demands: the scene-keyed shakedown
handler that the conversation dispatcher reaches through its reserved
"not a real NPC" dialog index.

It does not own ordinary conversation with Blackthorn's castle NPCs, ordinary
combat AI for the Blackthorn monster class, magic absorption in Blackthorn's
castle, or the endgame victory sequence. Those remain in
`systems/conversation.md`, `systems/combat.md`, `systems/magic.md`, and
`systems/endgame.md`.

## 2. Entry Families

The Blackthorn overlay exposes two player-visible scene families:

| Family | Visible role | Entry condition |
|--------|--------------|-----------------|
| Audience / capture | The party is subdued, taken before Blackthorn, challenged, and then routed to captivity or release state | Town guards arrest the party while it is inside Lord Blackthorn's Castle and at least one member can still act or is merely asleep |
| Rescue / refuge | A darkness-and-thunder cinematic restores the party and moves it to a refuge scene | No party member can act and none is asleep — the same check in town, overworld, and dungeon mode |

Both families are cinematic handlers. They replace the ordinary map loop while
they run, manage their own text and timing, and hand control back through an
explicit scene/position transition rather than by restoring the prior map.

**The audience is reached from the town arrest path, and from nowhere else.**
Town post-action cleanup can hand a guard-catch outcome to the town
arrest/unconscious handler, and that handler splits on the current location.
Inside Lord Blackthorn's Castle — scene byte eighteen, the gazetteer's
`CASTLE:1` — and with at least one party member still able to act or merely
asleep, it plays this audience and afterwards re-runs town entry setup for the
same location. Everywhere else the same handler asks the ordinary surrender
question: accepting prints the knockout line, fades, and wakes the party in the
Yew jail cell at 08:00; refusing turns the guards hostile. There is no
combat-defeat entry into the audience, no capture flag staged by an earlier
fight, and no alternate death outcome. Being "captive" means nothing more than
being arrested inside Blackthorn's castle, which the player normally reaches by
walking in; the only path that ever selects that location as a handoff target
is the tail of this same cinematic, which returns the party there.

**The rescue/refuge cinematic is the total-party-defeat handler.** It has no
mode-local predicate at all. Town, overworld, and dungeon mode each open a turn
with the same shared party-capability check described in Section 7, and its
"nobody can act and nobody is asleep" result is the only condition that enters
the cinematic, identically in all three modes. Losing a fight reaches it
indirectly: a combat wipe returns to whichever exploration loop framed the
fight, and that loop's next capability check reports the wipe.

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

During the opening capture pass, the handler narrates the first party slot —
scanning from the leader through all eight slots — whose per-member
Blackthorn-jail flag is still clear. If every slot is already flagged, the whole
capture narration is skipped and the flow jumps directly to the audience proper.

**Retraction.** Earlier revisions of this section described a "capture
death-route marker" that could turn the same presentation into a death outcome.
That is withdrawn in full: there is no death branch and no second outcome here.
The byte formerly described that way is the game's global sound on/off setting,
and its only effect inside this cinematic is the length of one scroll pause
between two lines of the capture narration — a long pause when sound is on, a
short one when it is off.

The entry runs through the ordinary town NPC-event cleanup, but the
Blackthorn-castle branch bypasses the normal arrest prompt. In every other
location the same arrest helper asks whether the party will surrender and then
sends the party to Yew or turns the guards hostile. Inside Lord Blackthorn's
Castle, and only while the party-capability check of Section 7 reports that
somebody can act or is asleep, it transfers to this audience/capture cinematic
instead and re-enters town entry setup for the same location afterwards. If the
party is arrested there with nobody able to act and nobody asleep, the arrest
takes the ordinary surrender branch rather than the audience.

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

**Entry condition: the shared party-capability check.** Every exploration mode
opens each turn by asking the same resident question of the party roster, and
the answer decides whether the turn proceeds, is slept through, or ends the
party's run of bad luck here. A member *can act* when their status is Good or
Poisoned; every other status — dead, asleep, ashes, charmed, and the rest —
counts as unable.

| Roster scan result | Effect |
|--------------------|--------|
| At least one member can act | Ordinary turn. The scan also records which member that was, for callers that need a member able to act. |
| Nobody can act, but at least one member is asleep | The mode prints the sleep line ("Zzzzzz...") and the turn passes with nothing else happening. |
| Nobody can act and nobody is asleep | This rescue/refuge cinematic runs. |

That third case is the only entry condition. There is no quest gate, no
moonstone requirement, no location test, and no per-mode variation: town,
overworld, and dungeon mode all use the identical check and the identical
result mapping, and combat reaches it only indirectly, when the exploration
loop that framed the fight runs its next check. The mode-local work around the
check is bookkeeping rather than predicate — the overworld, when the party is
above ground, asks for the surface map disc and runs its active-object
maintenance pass first, and the dungeon runs its own view-helper pass first. An
empty roster also falls into the third case.

Because this cinematic restores the party and returns it to play, an ordinary
party wipe in Ultima V is not a terminal game-over: the run continues from Lord
British's Castle, with a verdict on the party's moral standing read out along
the way.

The rescue contract:

1. Enter cutscene mode and suppress ordinary map play.
2. Clear terrain and temporary-object scratch state for the cinematic.
3. Print the darkness, refuge, thunder, and fortune-themed narrative beats.
4. Run the timed scene animation and tile placement passes.
5. Select and print one `KARMA.DAT` record through the five-band rescue
   selector.
6. Restore every party member: the member's status is reset to able-bodied and
   their current hit points are set to their maximum.
7. Print the disorientation or vertigo beat.
8. Fade out and hand control to scene byte seventeen, the gazetteer's
   `CASTLE:0` location associated with Lord British's Castle, on logical floor
   one at local position `(10, 10)`, with the clock spun forward until the hour
   reads 06:00.
9. Raise the moral-standing selector to a floor of seventy-five if it was
   below that, so the rescue cannot regress the save state. The verdict record
   printed in step 5 is chosen from the standing *before* this raise.

The restoration in steps 8 and 9 also wipes the party's magical state. As it
sets the destination scene and position it clears the single shared
timed-effect slot specified in `systems/magic.md`, so an active Protection,
Quickness, Mass Charm, Negate Magic, or Negate Time is cancelled and any worn
Amulet of Lord British, Crown of Lord British, or Black Badge aura is stripped.
Once the clock has been spun forward it also zeroes both light counters, so a
burning torch and an active light spell are both extinguished; see
`systems/lighting.md`. A party rescued from a wipe therefore arrives with no
buffs, no worn regalia aura, and no light.

`KARMA.DAT` is reused here as player-facing verdict text. This does not make
the file a numeric karma table. The rescue selector divides a one-byte verdict
input into five twenty-point bands: `0..19`, `20..39`, `40..59`, `60..79`, and
`80..99`, selecting records zero through four respectively. The shipped sixth
record is not selected by this traced rescue/refuge table.

## 7a. Regime Guard Demands

Separately from the two cinematics, the regime has a small everyday presence in
ordinary play: the guards who stop the party and demand something. These are not
NPCs with dialogue files. They are reached from the conversation dispatcher's
reserved "not a real NPC" dialog index, described in
`systems/conversation.md`, which hands off to one scene-keyed handler instead of
loading a `.TLK` blob.

That handler has exactly three branches, chosen by the current scene, and its
only durable effect is on the party's gold. It writes no character status, no
hit points, and no karma, and it returns one of two results — "paid or passed",
or "refused" — which becomes the conversation's result. Nothing runs afterwards.

**Branch 1 — the palace gate password.** In Lord Blackthorn's Castle, and only
while the Black Badge aura is the party's active timed magic effect (see
`systems/magic.md`), the guard asks the party to give the password as a bearer
of the Badge and prompts for a response. The player may type up to fourteen
characters, but only the **first four** are compared, and the comparison folds
letter case. The expected answer is the Oppression-side password that
`catalogs/quest-graph.md` Section 3 names, and that word is longer than four
letters — so the truncation is what lets the full word pass, and it also means
any word sharing those first four letters is accepted. A match prints a short "pass, friend" acknowledgement
and returns success; anything else simply refuses. Because the gate reads the
shared timed-effect slot, this branch is unreachable until the party actually
uses the Black Badge, and it becomes unreachable again the moment anything
clears that slot — camping or resting, entering an innkeeper's menu, using the
Badge a second time to take it off, or donning the Amulet or Crown instead.

**Branch 2 — the Minoc charity demand.** In Minoc, the guard announces that the
party will give half its gold to charity. On a yes, the party's gold word is
halved. On a no, nothing is taken.

**Branch 3 — the default tribute.** In every other scene the handler reaches,
the guard demands a tribute to Blackthorn of ten gold per **living** party
member; members marked Dead are not counted, so the amount is a head tax on the
survivors. The demanded amount is printed in the line. On a yes, and only if the
party can afford the full amount, that amount is subtracted; if the party cannot
pay, the handler refuses and takes nothing.

None of the three branches touches karma, party status, quest flags, or the
inventory. Gold is the entire mechanical consequence.

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
| Timed magic-effect slot and both light counters | Cleared by the rescue restoration; see `systems/magic.md` and `systems/lighting.md` |
| Carried-key count zeroed by the audience cleanup | Durable inventory effect of the capture |
| Captive-cell duration/progression counter | Durable or semi-durable post-capture state; initialized if empty by the rescue path |
| Standing/progression byte clamp | Durable rescue/story floor |

Implementations should not conflate these. In particular, the active-object
table is repurposed for cinematic drawing, while party jail flags, the
post-capture counter, and the rescue progression counter are the durable
gameplay outputs.

**Retraction.** An earlier revision of this table also listed a "capture
death-route marker" and a "conversation Blackthorn signal". Both are withdrawn.
There is no death-route marker (Section 3). The byte previously called a
Blackthorn conversation signal is the party's ordinary carried-key counter —
the same counter the conversation letter-grant table fills and the lockpicking
paths spend — and the audience's cleanup simply zeroes it, so the party leaves
the capture without its keys. Nothing in that band is a capture predicate or a
rescue trigger.

## 9. Relationship To Other Systems

- **Combat.** `systems/combat.md` owns ordinary Blackthorn class behavior and
  the defeat result that some callers can translate into capture.
- **Encounters.** `systems/encounters.md` owns scripted-fight framing before a
  Blackthorn-specific caller chooses capture, cancellation, or ordinary combat.
- **Conversation.** `systems/conversation.md` owns normal NPC Talk and `.TLK`
  execution, and owns the reserved dialog index that routes to the guard
  demands in Section 7a. The Blackthorn challenge in Sections 4 and 5 is a
  separate cinematic prompt loop.
- **Magic and inventory.** `systems/magic.md` owns the single shared
  timed-effect slot that the Black Badge aura occupies and that gates the
  palace-gate password branch; `catalogs/item-list.md` owns wearing and
  removing the Badge itself.
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

Both entry predicates are now published. The audience is entered only from the
town arrest handler, on the location test plus the party-capability test of
Section 2; the rescue/refuge cinematic is entered only from the shared
party-capability check of Section 7, with no mode-local condition of any kind.
Neither a defeat/capture context byte nor a death-route marker exists.

Remaining exactness is presentation parity and one shared-state question:

- Verify the exact visual identities of the cutscene tile-write bytes and the
  exact cursor/glyph effects of the output-byte commands if pixel-level
  Blackthorn cutscene parity is required.
- The per-member Blackthorn-jail flag band is claimed by more than one reader
  in the private analysis; a compatible implementation should keep it a
  Blackthorn-owned band until that overlap is resolved.

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
- `u5-decomp/functions/TALK_OVL/0x01E2_scene_service_dispatch.md` — the
  three guard-demand branches, the four-character password comparison, the
  living-member head count, and the handler's complete set of writes.
- `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` — the
  independent re-verification of that handler, and the Black Badge aura gate on
  the password branch.
- `u5-decomp/functions/TOWN_OVL/0x12AE_town_arrest_or_unconscious.md`.
- `u5-decomp/functions/TOWN_OVL/0x1352_town_post_action_cleanup.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x39FC_find_paladin_or_shepherd.md` — the
  shared party-capability check of Section 7.
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

Source provenance: derived from private analysis note
`u5-decomp/notes/oq-closures_2026-08-22_blackthorn-town.md`, sections Q1 and
Q2, for the audience entry path, the withdrawal of the death-route marker, the
shared party-capability check that enters the rescue/refuge cinematic, and that
cinematic's restoration, standing-floor, and handoff effects.
