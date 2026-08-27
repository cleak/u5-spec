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

The audience path starts from the arrest outcome of Section 2 — the party is
seized by guards inside Lord Blackthorn's Castle, never as the result of losing
a fight. It counts the active party members that are still eligible for the
challenge, records the target party slot, and then switches into a cutscene
presentation.

The setup contract is:

1. Print the capture narration: the party is overcome, blinded, and dragged
   away by guards.
2. Select which shrine the interrogation will demand a mantra for: scan the
   eight shrine ruin flags in shrine order and take the first whose flag is
   *exactly* clear — never ruined and never restored. If every flag is
   non-zero the whole audience is abandoned.
3. Clear the active-object table so the audience scene can reuse those records
   as temporary cinematic actors.
4. Load the Blackthorn audience map from `MISCMAPS.DAT`.
5. Load the Blackthorn message cluster from `MISCMSG.DAT`.
6. Place the party, two guards, and the initially suppressed seated-Blackthorn
   tableau into cutscene actor slots.
7. Run the scripted throne approach and Blackthorn presentation beats.
8. Greet the current leader by name and print the gendered release line.
9. Enter the challenge loop.

The active-object writes in this flow are presentation state. They do not
describe the live town map and should not be saved back as ordinary world
objects.

> **Withdrawal.** Earlier revisions of this section said the handler "narrates
> the first party slot, scanning from the leader through all eight slots, whose
> per-member Blackthorn-jail flag is still clear". **There is no per-member jail
> flag.** The eight bytes that reading was built on are the game's **shrine ruin
> flags** — the same durable save field this spec already documents in
> `formats/saved-gam.md` and `systems/quest-flags.md`. The eight-slot scan
> selects a *shrine*, not a party member: the first shrine that is neither
> ruined nor restored. If every flag is non-zero the flow jumps directly past
> the block. The spec previously contradicted itself on these bytes; the shrine
> reading is correct and the jail reading is withdrawn in full.

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
Entering that location does not create a captivity timer or context field; the
scene and position are the complete persistent handoff.

## 4. Challenge Loop

The challenge is a short, blocking question sequence tied to virtues and
Words of Power. It can ask up to four prompts. Each prompt is assembled from a
template, reads a short text answer from the player, and compares the answer
against a fixed expected string.

Compatibility rules:

- The prompt input accepts at most fourteen typed characters before comparison.
- Answer comparison is case-insensitive and substring-style: the expected word
  may appear anywhere in the typed buffer rather than being the entire input.
- **The loop asks about ONE shrine, up to four times.** The shrine index is
  fixed before the loop starts and never changes inside it. The four prompt
  ordinals change only the *wording*, which escalates from a plain question, to
  a repeat, to an impatient demand, to a shouted final demand.
- **The expected answer is the selected shrine's mantra, and it is the same on
  all four prompts.** All eight virtue/mantra pairs are live:

  | Shrine | Accepted answer |
  |--------|-----------------|
  | Honesty | `Ahm` |
  | Compassion | `Mu` |
  | Valour | `Ra` |
  | Justice | `Beh` |
  | Sacrifice | `Cah` |
  | Honor | `Summ` |
  | Spirituality | `Om` |
  | Humility | `Lum` |

- **A correct answer ruins that shrine and costs five points of moral
  standing.** The shrine's durable ruin flag is set, so the shrine thereafter
  renders and behaves as a ruined shrine until the player restores it by
  meditating there. The moral-standing debit is a clamped subtraction of five,
  floored at zero.
- **A correct answer also decides a companion's fate.** If more than one
  companion is still alive, Blackthorn thanks the player for their honesty and
  **kills** one companion as "a merciful death". If only one remains, he spares
  the player instead.
- **A wrong answer, when few companions remain, ends the interrogation** with a
  mocking line about lying and a threat of the dungeon.
- **A wrong answer otherwise escalates.** The first wrong answer produces a
  threat naming the companion at risk. Later wrong answers stamp a tile into
  the cutscene map, and the fourth wrong answer **kills** the named companion
  with the pendulum-blade narration.

> **Withdrawal.** Earlier revisions of this section said the answer lookup was
> "indexed by prompt ordinal rather than by party slot", that "this traced
> challenge loop only iterates the first four ordinals", that "a correct answer
> marks the current target party member as jailed or handled", that the flow
> "can silently route that member into jail state", that "the challenge does not
> directly adjust numeric karma", and that "the loop's party-slot argument is
> semantic: it names which companion is at risk". **All six claims are
> withdrawn.** The answer is indexed by shrine, not by prompt ordinal; the four
> ordinals are four wordings of one question, not four different questions; the
> flag set is a shrine's, not a party member's; the "silent routing" is a
> companion being killed; and the interrogation *does* debit moral standing.

## 5. Failure Reaction

When the interrogation fails on a branch that can punish a companion, Blackthorn
prints a reaction, runs the punishment animation, and names the party's second
living member as the victim.

The visible sequence is:

1. Build and print the failure reaction text.
2. Play the failed-demand cutscene beat.
3. Move one of the two guards and the victim through the audience scene.
4. Print the static punishment fragments around the named victim.
5. Wait for player acknowledgement before returning to the caller branch.

**The punishment is an execution, and it is durable.** Earlier revisions of this
section described only "a punishment animation" and "a dragged-away victim" and
omitted the consequence entirely. The victim is the second living party member
(the first living companion behind the Avatar), and the routine:

- erases that companion's on-screen actor;
- lifts their roster record out of the party, compacts the remaining records
  up, and decrements the party count;
- parks the lifted record in the last roster slot with a **whereabouts value
  that matches no location**.

That whereabouts field is the same one the innkeeper uses when a companion is
left at an inn; the value written here matches no inn and no scene, so no inn
can ever retrieve them, and nothing else in the game reads it back. The refuge/
rescue sequence does not restore them either. **The companion is dead and gone,
and the effect survives saving and reloading.**

The same execution runs on the *correct*-answer branch whenever more than one
companion is alive, under a different message — Blackthorn thanking the player
for their honesty and granting the companion "a merciful death".

The exact reaction-string builder and every static fragment's text remain
data-owned. This spec intentionally records the behavior and actor roles
rather than reproducing the source text.

## 6. Cutscene Script VM

The Blackthorn overlay uses a compact byte-script interpreter for these
cinematics. The interpreter is local to the Blackthorn audience/challenge
presentation and is separate from `.TLK` conversation scripts.

The script language supports ending a script, setting a repeat count, selecting
single- or paired-actor movement, enabling or disabling animated per-step
pauses, writing one terrain byte into the cutscene buffer, requesting a redraw,
running either of two pause forms, clearing one temporary actor slot, and
moving one or two actor slots by cardinal steps.

The exact presentation commands are:

| Command | Exact effect |
|---------|--------------|
| Quiet redraw pause | Consume one following byte as an unsigned count. If cinematic animation is enabled, repeat that many times: run one world tick, then one shared one-BIOS-tick delay. It neither reads nor changes any text window, cursor, font, glyph style, or text pixels. |
| Terrain write | Consume `(value, column, row)` and replace that byte in the 32-byte-stride cutscene terrain buffer. The write itself draws nothing. |
| Explicit redraw | Run one unconditional world tick. This rebuilds and repaints the viewport; it does not clear the viewport or either text window. |
| Stinger pause | Repeat the current count: play the shared two-tone PC-speaker sting, then request a two-tick quiet redraw pause. The repeat count resets to one afterward. |
| Animated movement step | After changing the selected actor coordinates, run one stinger-pause repetition when per-step animation is enabled. Per-step animation starts enabled. |

The so-called output-byte command is therefore not output. Its six shipped
operands are pause lengths, not character codes:

| Operand | Script location | Meaning |
|--------:|-----------------|---------|
| 22 (`0x16`) | Failed-challenge opening | Quiet 22-tick redraw pause before the acting guard moves. |
| 3 (`0x03`) | Failed-challenge middle | Quiet 3-tick redraw pause after the victim's last southward step. |
| 12 (`0x0C`) | Failed-challenge return | Quiet 12-tick redraw pause after the acting guard returns. |
| 8 (`0x08`) | Audience approach | Quiet 8-tick redraw pause after the two guards separate. |
| 11 (`0x0B`) | Guard release route | Quiet 11-tick redraw pause before the acting guard moves. |
| 4 (`0x04`) | Conditional cleanup | Quiet 4-tick redraw pause before the seated-Blackthorn tableau moves. |

There is consequently no glyph code, font selection, cursor position or
movement, text overwrite, or text compositing rule for any of these six
operands. Text printed before a pause remains exactly as the ordinary text
contract left it, and the next explicit string print resumes from that same
text state.

**Retraction.** Earlier revisions called the quiet-pause operand a byte sent to
the text/glyph stream and called the explicit-redraw command a cutscene-screen
clear. Both claims are withdrawn: the first is a tick count and the second is
one ordinary world-tick redraw.

The interpreter maintains three small pieces of modal state while it walks a
script:

- **Repeat count.** Defaults to one. A count-setting command changes how many
  times the next movement or pause command repeats, then the count resets to
  one after that command is consumed.
- **Paired movement mode.** A mode command makes the next movement consume a
  second movement descriptor, so two actors step together on each repeated
  tick. The mode resets after that movement.
- **Per-step pause mode.** A mode command enables or disables the
  sting-plus-two-tick pause after each individual movement step. This controls
  whether actor motion is visibly animated one cell at a time or accumulated
  without intermediate redraws.

Movement descriptors combine an actor family with a cardinal direction. The
known actor families are the Avatar, the second party member, two guards, and
the seated-Blackthorn tableau; the direction component moves that actor one
cell north, east, south, or west. A byte-compatible implementation may model
the compiled scripts as data, but the visible contract is actor-indexed
cardinal stepping with the modal repeat, paired-step, and pause rules above.

The public actor roles identified so far are:

| Slot | Role |
|------|------|
| 0 | Avatar / party leader presentation actor |
| 1 | Second party member, used by the failure punishment beat |
| 6 | Left/acting guard; actor byte `0x70` |
| 7 | Right/secondary guard; actor byte `0x70` |
| 8 | Seated Blackthorn and throne tableau; initially suppressed, then actor byte `0x78` |

The known script beats are the per-question intermission, the failed-answer
punishment, the audience guards' approach and separation, the acting guard's
release route after Blackthorn's order, and a conditional seated-Blackthorn
cleanup after a successful audience flag. A
modern engine can model these as named cinematic actions as long as it
preserves actor order, pauses, tile writes, and final scene handoff.

**Retraction.** Earlier revisions assigned slot 6 to Blackthorn and described
that sprite as approaching the throne, rising, and dragging the victim. Slot 6
and slot 7 are both guards; seated Blackthorn is slot 8. The movements formerly
attributed to Blackthorn belong to the acting guard.

### 6.1 Exact tile identities and domains

The viewport is an eleven-by-eleven cell rectangle whose EGA pixel origin is
`(8,8)`. A cell `(column,row)` therefore begins at
`(8 + 16*column, 8 + 16*row)`. Terrain bytes select the lower half of the
512-tile atlas directly. Cinematic actor bytes select the upper half by adding
256; the direct reveal and blit operations instead receive the full atlas
index.

| Value or index | Storage context | Exact visual | Cell and pixel origin in this cinematic |
|---------------:|-----------------|--------------|-----------------------------------------|
| `0x44` | VM terrain byte | Cobble: the red-and-grey cobble pattern. | `(0,4)`, pixels `(8,72)`. |
| `0xBB` | VM terrain byte | A locked wooden door with a window, drawn as a grey frame with yellow bars. | Replaces `0x44` at `(0,4)`, pixels `(8,72)`. |
| `0x82` | VM terrain byte | The top-down pendulum fixture. This is not the dungeon first-person fire-field interpretation of the same low byte. | `(5,7)`, pixels `(88,120)`. |
| `0xE9` | VM terrain byte | An hourglass. | `(5,9)`, pixels `(88,152)`. |
| `0x70` / `0x170` | Guard actor byte / full atlas index | A silver-armoured guard in a blue surcoat, carrying a polearm or sword-and-shield silhouette depending on frame. Both slots 6 and 7 start in this family. | Slots begin at `(4,10)` and `(6,10)`. |
| `0x16` | Actor byte sentinel | Draw nothing. In actor storage this must not be interpreted as full atlas tile `0x116`. | Used to suppress slots before direct reveals. |
| `0x178` | Full atlas index; then actor byte `0x78` | The Dark King Blackthorn seated on his red throne. | `(5,5)`, pixels `(88,88)`. |
| `0x5E`, `0x5F` | Rescue terrain bytes | The two complementary blue circular Guardian images; both are Guardian-named art. | `(2,7)` / `(8,7)`, pixels `(40,120)` / `(136,120)`. |
| `0x174` | Full atlas index; then actor byte `0x74` | A cyan-and-blue crowned spectral humanoid with bright eyes and both arms raised. Its general description-table row is intentionally unnamed. | `(5,2)`, pixels `(88,40)`. |
| `0x11C` | Full atlas index | The party-on-foot sprite. | `(5,5)`, pixels `(88,88)`. |

### 6.2 Direct drawing and redraw boundaries

A VM terrain write becomes visible only on a later world tick. Actor-coordinate
changes behave the same way. By contrast, each caller-level single-cell reveal
draws directly to the visible page: exactly 256 pixel writes in the shared EGA
LFSR order, with one world tick after each eight completed pixels except the
last group—31 checkpoints in all. These Blackthorn reveals are blocking and
cannot be skipped. There is no final flush. The caller commits the same terrain
or actor identity afterward so the next ordinary redraw preserves the revealed
image.

The rescue's two whole-viewport transitions are the shared blocking rectangle
dissolve over inclusive pixels `(8,8)..(183,183)`. The thunder beat also runs
the shared full-viewport flash/low-rumble operation from `systems/audio.md`
Section 8.4 twice back-to-back. Those are direct-screen operations; none is a
text-window clear.

### 6.3 Minimal deterministic audience vectors

| Beat | Observable sequence |
|------|---------------------|
| Per-question intermission | The acting guard first steps west with one animated stinger pause. Cobble `0x44` is buffered at `(0,4)` and the next explicit world tick exposes it. The subsequent guard/Avatar repositioning remains animated one step at a time. Door `0xBB` replaces the cobble and the following one-repetition stinger pause exposes the door. The seated-Blackthorn tableau and both guards then continue moving or are cleared with per-step redraws; each cleared actor disappears on the next movement or pause redraw. The first repetition of the final six-repetition stinger pause exposes the empty tableau and the remaining five hold it. |
| Failed challenge | Quiet pause 22; the acting guard moves to and with the second member; quiet pause 3; buffer pendulum `0x82` at `(5,7)` and clear that member; one explicit world tick exposes both changes together. The acting guard returns with animated steps; quiet pause 12; the secondary guard walks west three animated steps; hourglass `0xE9` is buffered at `(5,9)`; the first of that guard's three animated east steps exposes it. |
| Guard approach | One stinger-pause repetition; both guards move north together one animated step; then slot 6 moves west while slot 7 moves east for three animated paired steps, opening the centre; quiet pause 8. The caller then hides slot 8 at `(5,5)`, reveals seated Blackthorn `0x178` there with the 256-pixel transition, assigns actor byte `0x78` to preserve it, and performs another quiet pause 8 before Blackthorn's speech. |
| Guard release route | After Blackthorn orders the guard to release the captive: quiet pause 11; the acting guard moves west once, north four times, and east once, with a stinger-plus-two-tick redraw after every step. Blackthorn remains seated in slot 8. |
| Conditional Blackthorn-tableau cleanup | Quiet pause 4; seated Blackthorn and the throne move east once and south five times with an animated redraw after every step; slot 8 is cleared; one explicit world tick repaints the resulting tableau. It does not clear the screen. |

These vectors deliberately test visible checkpoints rather than duplicating the
already-published movement byte stream. A conforming renderer must additionally
preserve the actor order, repeat counts, paired movement, and final coordinates
described above.

## 7. Rescue / Refuge Sequence

The second Blackthorn family is a rescue or refuge cinematic. It waits for the
overworld resource file to be available, switches into cutscene mode, prints a
darkness/refuge/thunder sequence, runs its audio and direct-screen effects,
places the rescue scene tiles, then prints a selected `KARMA.DAT` verdict
message.

**Entry condition: the shared party-capability check.** Every exploration mode
opens each turn by asking the same resident question of the party roster, and
the answer decides whether the turn proceeds, is slept through, or ends the
party's run of bad luck here. A member *can act* when their status is Good or
Poisoned; every other status — dead, asleep, ashes, charmed, and the rest —
counts as unable.

| Roster scan result | Effect |
|--------------------|--------|
| At least one member can act | Ordinary turn. The scan also records which member that was, for callers that need a member able to act. |
| Nobody can act, but at least one member is asleep | The mode prints the sleep line ("Zzzzzz...") and follows its mode-local no-input asleep path. |
| Nobody can act and nobody is asleep | This rescue/refuge cinematic runs. |

That third case is the only entry condition. There is no quest gate, no
moonstone requirement, no location test, and no per-mode variation: town,
overworld, and dungeon mode all use the identical check and the identical
result mapping, and combat reaches it only indirectly, when the exploration
loop that framed the fight runs its next check. An empty roster also falls into
the third case.

The result mapping is shared; the work surrounding it is mode-local. On the
asleep result, overworld mode runs its entire ordinary two-minute consumed-turn
path without input, including underfoot/environment, party-status/provisions,
encounter, and active-object work under their normal gates. Town mode runs its
documented wake-before-underfoot path. Dungeon mode skips its post-action
helper; its next ordinary loop head owns the indoor clock advance.

On defeat, overworld mode first makes gameplay disk 1 available when necessary,
selects the current plane's object file, and persists all thirty-two live
active-object records byte-for-byte. It does not run the ordinary animator or
pruner and consumes no randomness. Dungeon mode first tears down only transient
graphics resources: it releases the dungeon banks, restores the ordinary tile
atlas with retry semantics, marks dungeon graphics inactive, and draws no
intermediate frame. Neither preamble changes the shared predicate or makes
rescue conditional; rescue follows the successful persistence/resource step.

Because this cinematic restores the party and returns it to play, an ordinary
party wipe in Ultima V is not a terminal game-over: the run continues from Lord
British's Castle, with a verdict on the party's moral standing read out along
the way.

The rescue contract:

1. Enter cutscene mode and suppress ordinary map play.
2. Print the unending-darkness beat, then dissolve the map viewport out to
   black. This happens before clearing terrain or temporary-object scratch
   state and before building the refuge tableau.
3. Clear terrain and temporary-object scratch state for the cinematic.
4. Print the refuge, thunder, and fortune-themed narrative beats; run the
   audio-envelope sequence, three cell reveals, and paired viewport flash.
5. Select and print one `KARMA.DAT` record through the five-band rescue
   selector.
6. Restore every party member: the member's status is reset to able-bodied and
   their current hit points are set to their maximum.
7. Print the disorientation or vertigo beat.
8. Fill the hidden map viewport black, draw the on-foot party sprite at its
   centre cell `(5,5)`, and dissolve that image onto the visible viewport.
9. Raise the moral-standing selector to a floor of seventy-five if it was
   below that, so the rescue cannot regress the save state. The verdict record
   printed in step 5 is chosen from the standing *before* this raise.
10. Hand control to scene byte seventeen, the gazetteer's
   `CASTLE:0` location associated with Lord British's Castle, on logical floor
   one at local position `(10, 10)`, with the clock spun forward until the hour
   reads 06:00.
11. Clear both light counters. If and only if the full two-byte food word is
    zero, replace it with 63; preserve every nonzero value unchanged.

### 7.1 Minimal deterministic rescue/refuge vector

The exact visible tableau between the two rectangle dissolves is:

1. After the first dissolve-to-black and the refuge narration, install the
   party-on-foot actor at cell `(5,5)` and redraw. The following six-entry
   software-envelope sequence is PC-speaker audio only and changes no pixels.
2. Temporarily suppress an actor at `(2,7)`, clear that underlying cell, and
   reveal Guardian image `0x5E` there with the blocking 256-pixel cell reveal.
   Commit `0x5E` as terrain, suppress the temporary actor again, redraw, then
   wait four BIOS ticks without changing text or pixels.
3. Repeat that pattern at `(8,7)` for complementary Guardian image `0x5F`,
   followed by another redraw and four-tick wait.
4. Print the thunder line, then run the shared full-viewport flash/low-rumble
   effect twice consecutively. Each invocation performs 1,856 band draws and
   consumes 1,856 gameplay-PRNG draws even when sound is muted; the pair
   therefore consumes 3,712 draws.
5. Temporarily suppress the actor at `(5,2)`, clear the underlying cell, and
   reveal full atlas tile `0x174` there. Assign actor byte `0x74` at that cell
   and redraw, leaving the blue crowned spectral figure persistent while the
   verdict text is printed.
6. After party restoration and the `Vertigo...` beat, select the hidden page,
   fill the inclusive viewport rectangle black, and immediately blit party tile
   `0x11C` at `(5,5)`. Restore the visible-page target, then run the second
   blocking rectangle dissolve to expose exactly black plus the centred party.

The tile identities, cell positions, pixel origins, and single-cell reveal
cadence are in Sections 6.1 and 6.2. Text is ordered around these operations as
stated above; none of the delay, envelope, redraw, or reveal calls advances a
text cursor or selects a font.

**Retraction.** Earlier revisions called the six-entry software-envelope loop
a timed scene animation. It is audio only; the visible rescue animation is the
redraws, three single-cell reveals, paired viewport flash, and two rectangle
dissolves enumerated here.

Both viewport transitions are single blocking rectangle dissolves over the
inclusive rectangle `(8,8)..(183,183)`. The first hidden rectangle contains
only colour zero, so it is a dissolve-out to black. The second hidden rectangle
contains colour zero plus exactly one centred party tile, so it is a
dissolve-in to the restored party against black—not a redraw of Lord British's
Castle. The moral-standing floor, destination scene/floor/position writes,
timed-effect clear, advance to 06:00, and light-counter clears all occur only
after the second dissolve has completed. The ordinary castle viewport is
therefore a later handoff result, not the hidden source of this transition.

The handoff in step 10 also wipes the party's magical state. As it
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
or "refused/failed" — which becomes the conversation's result. At the Talk
layer, paid/passed is the ordinary outcome. Refusal or failure is the only
positive outcome and requests the town loop's arrest cleanup.

**Branch 1 — the palace gate password.** In Lord Blackthorn's Castle, and only
while the Black Badge aura's exact effect code `0x1D` is the party's active
timed magic effect (see `systems/magic.md`), the guard asks the party to give
the password as a bearer
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
halved. On a no, nothing is taken and the refusal proceeds to arrest.

**Branch 3 — the default tribute.** In every other scene the handler reaches,
the guard demands a tribute to Blackthorn of ten gold per **living** party
member; members marked Dead are not counted, so the amount is a head tax on the
survivors. The demanded amount is printed in the line. On a yes, and only if the
party can afford the full amount, that amount is subtracted; if the party cannot
pay, the handler refuses, takes nothing, and proceeds to arrest.

None of the three branches touches karma, party status, quest flags, or the
inventory. Gold is the entire direct state change inside the demand handler;
arrest is the caller-owned consequence of any failed outcome. The demand can be
raised in two ways: automatically when town cleanup dispatches the flagged
guard's reserved dialogue, or explicitly when the player uses `T` on that
guard. The explicit route is the sole command producer of the town loop's
special arrest-cleanup status. Successful payment or the accepted password
uses the ordinary town action result instead.

## 8. State Boundaries

The Blackthorn overlay uses several kinds of state with different lifetimes:

| State | Lifetime |
|-------|----------|
| Shrine ruin flags | Durable world state, shared with `systems/quest-flags.md` and `formats/saved-gam.md`. **Correction:** this row previously read "Jailed or handled party-member flags"; those bytes are the shrine ruin flags. |
| Roster removal of an executed companion | Durable and irreversible: record lifted from the party, party count decremented, record parked with an unmatchable whereabouts value |
| Moral standing | Durable scalar at saved-game offset `0x02E2`; debited five per correct interrogation answer and floored to seventy-five by the rescue path. This one byte is both the verdict selector and the formerly duplicated "standing/progression" row. |
| Active-object table during audience/rescue | Temporary cinematic actors |
| `MISCMAPS.DAT` cutscene map | Temporary scene background |
| `MISCMSG.DAT` audience records | Temporary message source |
| `KARMA.DAT` rescue record | Temporary verdict text source |
| Scene byte and local position handoff | Next ordinary gameplay location |
| Timed magic-effect slot and both light counters | Cleared by the rescue restoration; see `systems/magic.md` and `systems/lighting.md` |
| Carried-key count zeroed by the audience cleanup | Durable inventory effect of the capture |
| Food/provisions rescue floor | The existing durable two-byte food word, not Blackthorn progression state. Rescue changes exactly zero to 63 and leaves every nonzero value alone. |

Implementations should not conflate these. In particular, the active-object
table is repurposed for cinematic drawing, while the shrine ruin flags, roster
removal, moral-standing changes, key loss, and ordinary food word are durable
gameplay state.

### 8.1 No captive counter or parallel progression field

The two save-backed scalars touched at the rescue tail are existing global
fields:

| Field | Saved-game storage | Factory value | Normal gameplay domain | Blackthorn behavior |
|---|---:|---:|---:|---|
| Food/provisions | `0x0202`, two-byte little-endian word | 63 | `0..9999`; ordinary grants saturate at 9999 and consumption floors at zero | Rescue compares the complete word with zero once. Zero becomes 63, represented by bytes `0x3F, 0x00`; any nonzero word is preserved exactly, even if a save editor supplied a value above the normal cap. Audience/capture never reads or writes it. |
| Moral-standing selector | `0x02E2`, one byte | 75 | `0..99` in normal play; moral gains cap at 99 and debits floor at zero | Rescue selects its verdict from the pre-change value, then raises values below 75 to 75. Values 75 and above remain unchanged. This is the same field named Moral standing in the table above, not a second rescue-progress byte. |
| Captive-cell duration/progression | **No field** | — | — | No writer, reader, increment, decrement, cadence, saturation, wrap, or reset exists. The earlier counter was a misidentification of Food. |
| Capture context | **No field** | — | — | Audience entry is selected by the town arrest path and current location; rescue entry is selected by the shared party-capability result. Neither path reads a saved capture tag. |

“Initialized if empty” therefore means one literal food safety grant at the end
of rescue, after the wait to 06:00 and after both light counters are cleared:
test the full food word, store 63 only when it equals zero, and return to the
ordinary handoff. There is no later Blackthorn-owned update cadence. All
subsequent food reads and changes belong to the ordinary provision, inventory,
shop, spell, pickup, and party-upkeep contracts.

Within the Blackthorn overlay this adjacent test/store pair is the food word's
only real access; the audience/capture entry has none. Outside Blackthorn, the
stats panel reads the word for display, the provision pass reads and subtracts
it at the meal-hour cadence in `systems/time.md`, and shops, tavern meals,
Create Food, crop pickup, inventory grants, and conversation grants can add to
it under their owning contracts. None treats it as capture progress.

The original save format needs no `SAVED.BTH` sidecar and no reserved legacy
capture byte. A compatible implementation may discard both extension fields;
the captive-cell location, food word, moral-standing selector, party roster,
and ordinary scene state contain every durable value these paths use.

*Corrected (2026-08-27).* Earlier revisions published a durable or
semi-durable captive-cell counter and a separate rescue progression output.
Both are withdrawn: the first is Food and the second is the already-listed
moral-standing byte.

**Retraction.** An earlier revision of this table also listed a "capture
death-route marker" and a "conversation Blackthorn signal". Both are withdrawn.
There is no death-route marker (Section 3). The byte previously called a
Blackthorn conversation signal is the party's ordinary carried-key counter —
the same counter the conversation letter-grant table fills and the lockpicking
paths spend — and the audience's cleanup simply zeroes it, so the party leaves
the capture without its keys. Nothing in that band is a capture predicate or a
rescue trigger.

## 9. Relationship To Other Systems

- **Combat.** `systems/combat.md` owns ordinary Blackthorn monster-class
  behavior and the combat defeat result. That result never enters the audience
  of Sections 2 and 3: a wipe returns to the exploration loop that framed the
  fight, and only that loop's next party-capability check can reach the
  rescue/refuge cinematic of Section 7.
- **Encounters.** `systems/encounters.md` owns scripted-fight framing,
  including the scripted Blackthorn duel. No encounter or fight outcome selects
  this overlay's audience; the audience has exactly one entry, the town arrest
  path of Section 2.
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

The pixel-level Blackthorn presentation boundary is now public as well:
Sections 6 and 7 identify every scripted terrain byte, the actor-bank identities
used by the direct reveals, all quiet-pause operands, the absence of any
output-byte/text effect, every redraw boundary, the three single-cell reveals,
the paired flash/rumble, and both rectangle dissolves.

- ~~The per-member Blackthorn-jail flag band is claimed by more than one
  reader.~~ **Resolved.** That band is the shrine ruin flags. It is *shared*
  world state, not a Blackthorn-owned band: the interrogation sets a shrine's
  flag, shrine meditation clears it, and region loading reads it to choose
  between the intact and ruined shrine tile.

## 11. Sources

This cleanroom spec was derived from private analysis notes and sibling public
specs. It intentionally does not reproduce decompiled code, assembly, raw data
tables, raw script bytes, or implementation-specific addresses.

- `u5-decomp/functions/BLCKTHRN_OVL/`.
- `u5-decomp/functions/TALK_OVL/` — the
  three guard-demand branches, the four-character password comparison, the
  living-member head count, and the handler's complete set of writes.
- `u5-decomp/notes/` — the
  independent re-verification of that handler, and the Black Badge aura gate on
  the password branch.
- `u5-decomp/functions/TOWN_OVL/`.
- `u5-decomp/functions/ULTIMA_EXE/` — the
  shared party-capability check of Section 7.
- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/formats/`.
- `u5-decomp/notes/`.
- `catalogs/gazetteer.md`.
- `systems/combat.md`.
- `systems/encounters.md`.
- `systems/karma.md`.
- `formats/location-dat.md`.
- `formats/miscmsg-dat.md`.
- `formats/karma-dat.md`.

The Section 8 storage correction -- identification of the alleged captive
counter as the ordinary food word, confirmation that the standing clamp uses
the existing moral-standing byte, exact rescue-tail ordering, and the negative
capture-context census -- is derived from private analysis in
`u5-decomp/functions/BLCKTHRN_OVL/`,
`u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/functions/CAST_OVL/`,
`u5-decomp/functions/SHOPPES2_OVL/`, `u5-decomp/functions/SJOG_OVL/`,
`u5-decomp/formats/`, and `u5-decomp/notes/`.

Source provenance: derived from private analysis in `u5-decomp/notes/` for the
audience entry path, the withdrawal of the death-route marker, the
shared party-capability check that enters the rescue/refuge cinematic, and that
cinematic's restoration, two viewport dissolves, standing-floor, and handoff
effects; the mode-local asleep and defeat preambles were cross-checked against
`u5-decomp/functions/MAINOUT_OVL/`, `u5-decomp/functions/OUTSUBS_OVL/`,
`u5-decomp/functions/DUNGEON_OVL/`, and `u5-decomp/functions/DNGLOOK_OVL/`;
the cinematic presentation was cross-checked against
`u5-decomp/functions/BLCKTHRN_OVL/` and the display-driver notes under
`u5-decomp/functions/EGA_DRV/`.

The Section 6 and 7 pixel-exact tables were derived by resolving the
Blackthorn overlay's resident-call targets against the established overlay
base, cross-checking the five script consumers and rescue caller ordering,
decoding the relevant fixed-size atlas entries and description-table rows, and
matching the direct reveal/flash/dissolve helpers to their shared contracts.
Source provenance: private analysis in `u5-decomp/functions/BLCKTHRN_OVL/`,
`u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/functions/EGA_DRV/`,
`u5-decomp/formats/`, and `u5-decomp/notes/`.
