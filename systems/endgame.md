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
2. The Doom Word of Power has been spoken beside the Doom entrance. That
   entrance is the centred coordinate on the Underworld surface, and the word is
   spoken from an adjacent outdoor cell there; it is not a seal inside the
   dungeon, not a Lord British throne-room target, and there is no
   dungeon-interior route that accepts it. Until the word is spoken the entrance
   is sealed and impassable, so this gate and the Shadowlord gate above are
   independent and both must pass. `systems/commands.md` Section 11 owns the
   predicate.
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

1. Mark the resident state as being in the endgame, so normal world redraw behaviour no longer applies, and mark the scene as having no active combatant so the arena renderer suppresses its target cursor.
2. Run a full status-panel redraw. Its side effect is that the message window of section 3.1 becomes the active text window for the whole dialogue phase.
3. Load endgame-specific data resources for the throne-room/cinematic scene and Lord British message records.
4. Load and draw the endgame bitmap assets through the same resident image-loading path used elsewhere.
5. Clear the active-object table and rebuild it as a cinematic tableau rather than as a gameplay object list.

The initial entry path loads `MISCMAPS.DAT` for the tableau and `ENDMSG.DAT`
for the Lord British dialogue. `END.DAT` is not part of that opening dialogue
load. It is consumed later by the final narrative presentation helper, which
reuses the message scratch buffer after the Lord British records are no longer
needed.

The original loader retries indefinitely if required resources are not available. A modern implementation can report a missing-asset error instead, but it should treat the sequence as blocked until the resources are present.

The active-object table is reused because the original engine already has sprite movement and drawing helpers for those records. During the endgame, the table no longer represents the live map. It represents the party, Lord British, and the two props the cinematic stages in front of the throne — the sandalwood box and the Orb spark it becomes (section 4). Since the endgame has no normal return path, these writes are presentation state rather than gameplay state.

### 3.1 The endgame surface is the ordinary gameplay screen

The endgame installs **no bespoke renderer and no bespoke screen layout**. It
reuses the standing gameplay surface and the standing text windows, and only
selects which of them is active. Everything below follows from that.

**The throne-room tableau is the ordinary eleven-by-eleven world viewport.**
Cells are sixteen pixels square and the grid's top-left corner is pixel
`(8, 8)`, so the tableau occupies the inclusive square
`(8, 8)..(183, 183)` — 176 pixels on a side. That is the same rectangle the
per-character revival flash of section 4 fills, and the same rectangle
`display-driver-abi.md` section 9.6 lists for the map viewport, so an engine
that gets one right gets all three.

**The tableau chamber is not the castle map.** The scene terrain is the fourth
eleven-by-eleven scene record of the shipped miscellaneous-maps file — record
index `3`, counting from zero. It is read as 11 rows of 16 bytes and re-strided
into the buffer a combat arena's terrain normally occupies, which uses a 32-byte
row stride; only the leading 11 bytes of each row are meaningful and the
remainder of each arena row is left as it was. The staging buffer the record is
read into is *not* the buffer the renderer draws from — the scene compositor
overwrites it every frame — so an implementation must perform the copy into the
arena terrain slot, not render the record in place.

Because the scene terrain lives in the arena slot, the endgame runs with the
engine's scene selector in its combat range. The consequence a clean engine
must reproduce is that **tableau actor coordinates are viewport cells
directly**: the world-to-viewport projection the outdoor and town modes apply is
skipped, so an actor at scene cell `(5, 4)` draws at viewport column 5, row 4,
i.e. pixels `(88, 72)..(103, 87)`. The overlay also marks "no active combatant"
on entry, which suppresses the combat target cursor the arena renderer would
otherwise draw.

**The text rectangles are standing fixed-cell windows.** The endgame never
resizes a text window; it only selects one. Two of the four standing windows are
used:

| Endgame text | Window rectangle (cells) | Rectangle (pixels) | Used for |
|---|---|---|---|
| Message window | `(24, 11)..(39, 23)`, 16 columns x 13 rows | `(192, 88)..(319, 191)` | Lord British's greeting, both box-delivery yes/no prompts and their echoes, the per-character revival lines, the seven rite messages, and the refusal branch's exchange |
| Full-screen window | `(0, 0)..(39, 24)`, 40 columns x 25 rows | `(0, 0)..(319, 199)` | The six narrative windows' page clears, and the certificate |

The message window is selected **implicitly**, as the last act of the
full-status-panel redraw the endgame calls on entry; nothing in the endgame
selects it explicitly, and nothing changes the selection again until the
narrative presentation of section 8 selects the full-screen window. The message
window does not overlap the `(8, 8)..(183, 183)` tableau, which is precisely why
the dialogue never occludes the scene — an engine that centres endgame text or
gives it its own rectangle will occlude the tableau and diverge.

Text behaviour inside the message window is the ordinary fixed-cell contract of
`text-output.md`: left-aligned, word-wrapped at the right margin, a line feed
advances one row, and the window scrolls up by one row when the cursor passes
the bottom.

## 4. Party tableau and restoration pass

Before Lord British's main dialogue, the endgame walks the active party slots and prepares each visible party member for the throne-room tableau.

For each party member:

- if the character is marked dead, the sequence announces their restoration,
  changes the character to a present/active post-death state, restores current
  health from the stored maximum, plays a short audio/visual flourish, and waits
  briefly. The announcement is a line feed, the character's name, and the
  literal text `" lives!"` followed by a line feed, printed into the message
  window of section 3.1. The flourish is a **single opaque fill of the whole
  `(8, 8)..(183, 183)` tableau rectangle** in the resident drawing colour,
  followed by a speaker tone and then a full status-panel redraw, which is what
  restores the tableau underneath. It is one flash, not a repeating cycle;
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
That means the party leader in slot 0 draws above the other party members and
above both of the scripted scene actors.

| Slot | Role | Initial actor byte | Initial X,Y | Phase | Initial settled target |
|---:|---|---:|---|---:|---|
| 0 | Active party member 0 / party leader | Class table | 5,9 | 0 | 5,5 |
| 1 | Active party member 1 | Class table | 5,9 | 0 | 4,6 |
| 2 | Active party member 2 | Class table | 5,9 | 0 | 6,6 |
| 3 | Active party member 3 | Class table | 5,9 | 0 | 3,7 |
| 4 | Active party member 4 | Class table | 5,9 | 0 | 5,7 |
| 5 | Active party member 5 | Class table | 5,9 | 0 | 7,7 |
| 6 | The sandalwood box, then the Orb — victory branch only | `0x0E`, later `0x08` | 5,4 | 0 | Created already at target |
| 31 | Lord British | `0x7C` | 5,8 | 0 | 5,3 in the victory branch; 4,1 in the refusal branch |

**Correction — the two scripted actors were inverted in earlier revisions.**
Earlier versions of this table named slot 6 "Lord British" and slot 31 a
"scene marker". Both are **withdrawn**. Slot 31 carries Lord British; slot 6
is the sandalwood box, which is later swapped in place for the Orb spark and
then cleared. The staging in section 7 only reads coherently with the corrected
identities: Lord British is on stage before the party arrives and walks up to
the throne row, and the box does not appear until the player's actor has
stepped forward to hand it over. An engine built on the old table draws a
chest on the throne and a king on the floor in front of it.

Party slots are populated only for active party indices below the current
party count. The setup loop does not synthesize absent party members for
empty slots above the party count.

#### The actor-byte index space

Tableau actor bytes are **not** tile-catalogue indices, and reading them as
such produces floor and furniture tiles rather than people. The rule is a
property of the shared scene compositor, not of the endgame:

1. When the compositor places an active object, it writes the object's actor
   byte into the companion band for that cell and sets the corresponding
   viewport grid cell to zero.
2. When the renderer meets a **non-zero** grid cell, it draws the terrain tile
   that cell names, through the animation-frame table.
3. When the renderer meets a **zero** grid cell, it reads the companion byte
   and draws tile index `companion_byte + 256`.

So an actor byte indexes the **upper half of the 512-entry tile space** — the
creature-and-person bank described in `catalogs/tile-catalog.md` — at an offset
of 256. One value is reserved: companion byte `0x16` means **draw nothing**,
and is how a transparent cell is expressed. Nothing else in the actor range is
special-cased.

Applying the `+256` rule, the endgame's actors resolve as follows.

| Actor byte | Drawn tile index | What it depicts |
|---:|---:|---|
| `0x40` | 320 | Mage sprite |
| `0x44` | 324 | Bard sprite |
| `0x48` | 328 | Fighter sprite |
| `0x4C` | 332 | Avatar sprite |
| `0x0E` | 270 | Lidded chest — the sandalwood box |
| `0x08` | 264 | Radiant spark — the Orb of the Moons |
| `0x7C` | 380 | Crowned, robed, seated figure between two banners — Lord British on his throne |
| `0x16` | — | Reserved "draw nothing" sentinel |

Note in particular that actor byte `0x44` is the Bard sprite at tile 324, not
the floor tile whose *terrain* index is also `0x44`; the two live in different
halves of the tile space and are never confused by the renderer, because a
terrain byte only ever reaches the renderer through a non-zero grid cell.

The party type and tile/frame bytes are both initialized from the class table.
The table has nine entries but only four distinct values, so only Mage, Bard
and Fighter get their own sprite and every other class — the Avatar included —
draws the Avatar sprite:

| Class byte | Class | Tableau actor byte | Drawn tile |
|---|---|---:|---:|
| `A` | Avatar | `0x4C` | 332 |
| `M` | Mage | `0x40` | 320 |
| `B` | Bard | `0x44` | 324 |
| `F` | Fighter | `0x48` | 328 |
| `D` | Druid | `0x4C` | 332 |
| `T` | Tinker | `0x4C` | 332 |
| `P` | Paladin | `0x4C` | 332 |
| `R` | Ranger | `0x4C` | 332 |
| `S` | Shepherd | `0x4C` | 332 |

The lookup is by the **position of the character's class letter** within the
nine-letter class-order string `AMBFDTPRS`, not by an arithmetic mapping from
the letter's character code.

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

### 5.1 Message source and pacing

All of this dialogue, and all seven rite messages of section 7, come from the
endgame message file `ENDMSG.DAT`. The whole file is read once, at entry, into
the shared text scratch buffer; the endgame then addresses records inside it by
ordinal. The file holds **eleven NUL-terminated records** with these roles:

| Record | Role |
|---:|---|
| 0 | Lord British's greeting, ending mid-sentence so the party leader's name and the literal `!"` plus a blank line can be appended |
| 1 | The first box question, ending with the literal reply lead-in `You reply: ` |
| 2 | The second, explicit sandalwood-box question, likewise ending with `You reply: ` |
| 3 | The first rite message, describing Lord British opening the box |
| 4..9 | The remaining six rite messages |
| 10 | The refusal branch's "pull up a chair" exchange |

Each yes/no prompt is a **blocking single-key read** that accepts only `Y` or
`N` and re-reads on anything else. The accepted answer is echoed into the
message window as the literal `Yes` or `No` followed by a blank line, and only
then does the next record print. There is no on-screen cursor prompt beyond the
record's own `You reply: ` tail.

The seven rite messages are printed as **seven discrete pages**. After the
first of them the sequence runs a short timed pause and then prints a fixed
`He says:` lead-in with exactly one blank row before it and one after; from
there every remaining rite
message is separated from the next by a blocking key read, so the player
advances each page. Nothing in this stretch is timed out or auto-advanced.

## 6. Refusal or missing-box branch

If the final confirmation is not yes, or if the saved sandalwood-box completion flag is absent, the sequence does not return the player to ordinary conversation. Instead, Lord British moves into a non-victory ending tableau: the player is made to wait with him, the party is seated or animated around the scene, and the endgame remains there indefinitely.

This branch is terminal in practice. It does not restore the previous map, re-enter the main loop, return to the title menu, or offer a new prompt to resume play. A modern implementation should treat it as a dead-end ending state. If an implementation adds a restart or title-menu command for usability, that command should be an out-of-band modern affordance rather than part of the original endgame state.

The refusal/missing-box branch uses the same initial party tableau setup, then
changes the scene as follows:

1. Slot 0's Y coordinate is decremented once.
2. The script repeatedly steps slot 2 toward (8,6), slot 31 — Lord British —
   toward (4,1), and slot 0 toward (8,4) until all three have arrived.
3. The terminal loop then jitters only slots 1, 3, 4, and 5. Slot 0, slot 2 and
   Lord British's slot 31 do not participate in that jitter loop, and slot 6 is
   never created on this branch at all.

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

1. Display-state changes prepare the screen for the ceremony.
2. Party-member active-object slots are stepped into their target positions.
3. The sandalwood box is placed as a separate scene sprite in front of the
   throne. Lord British is already on stage, from the setup pass of section 4.
4. A series of Lord British message records is printed with page pauses between records.
5. The box sprite is replaced by the Orb spark, then cleared, and the gate cell
   takes over that scene cell.
6. Timed world ticks and the gate's brightness ramp create the visual transition.
7. Every scripted actor is walked into the gate cell and cleared, the gate cell
   is repainted with the chamber floor tile, and the screen is prepared for the
   narrative presentation and the certificate.

The movement predicate used by the endgame is grid based: each call examines one active-object slot and moves it one cell toward a target, preferring the axis with the greater remaining distance. The caller repeats this until the slot reaches the target.

The separate tableau animation helper is a random local wander, not an animation-frame table. When the selected active-object slot is occupied, the helper first throttles the step with a two-outcome random roll. On an allowed step it samples up to eight four-direction candidates around the current cell, in random direction order, and commits the first candidate whose scene cell is marked as part of the endgame tableau's walkable region. If no candidate qualifies, the slot remains where it is for that call. The helper then advances the display/palette tick once before returning.

This helper is used by the terminal "wait here a while" tableau for party-member slots rather than by ordinary gameplay movement. It should be modeled as cinematic jitter within the authored endgame scene, not as a reusable NPC pathfinder, not as a direction-facing animation switch, and not as evidence for an unresolved party-sprite facing map.

The scripted staging and victory movement order, in full and with the corrected
actor identities of section 4, is:

1. Place **Lord British** in slot 31 with actor byte `0x7C` at cell (5, 8), let
   the display settle, then step slot 31 to (5, 3) — he walks up to the throne
   row before anyone else is on stage.
2. For each live party index in ascending order: place that party member's class
   actor byte in the slot of the same index at cell (5, 9), then step it to its
   fixed target. The targets are (5,5), (4,6), (6,6), (3,7), (5,7) and (7,7) —
   a wedge fanning out below the throne.
3. Print the greeting and run the two box-delivery prompts of section 5.
4. Step slot 0 from its settled position to (5, 4), then back to (5, 5) — the
   player's actor walks up to hand the box over and steps back.
5. Create the **sandalwood box** in slot 6 with actor byte `0x0E` at (5, 4).
6. Print the seven rite messages with the pacing of section 5.1.
7. Change slot 6's actor byte to `0x08`, the **Orb spark** — the box opens.
   A blocking key read and a speaker sting follow.
8. Clear slot 6, and write the moongate terrain tile into the scene grid at
   cell (5, 4). The gate now owns that cell.
9. **Raise the gate.** The gate cell is drawn at the shared moongate presence
   phase, which the sequence raises through 1, 2, ... 15, running one world tick
   at each of those fifteen phases. The phase then steps once more, to 16, which
   is outside the composed range, and the sequence holds there for **four**
   world ticks with the cell drawn as the ordinary gate tile — the gate at full
   height, and the pause before Lord British moves.
10. Step slot 31 — Lord British — to (5, 4), then clear it. He enters the gate.
11. For each live party slot in ascending order, step that slot to (5, 4), then
    clear it, running a world tick between actors. The party follows one by one.
12. **Lower the gate**: the phase is reset to 15 and stepped down, one world
    tick at each of the phases 15 through 1, finishing at 0 with no further
    tick. The down-ramp has no full-height hold.
13. Repaint the gate cell (viewport column 5, row 4) with the plain chamber
    floor tile, drawn from the terrain bank rather than the actor bank.

The gate cell's terrain byte is the moongate value, and the phase counter the
two ramps drive is **the same world-global moongate presence phase** that
overworld gates use — not a private endgame effect. The renderer composes the
cell exactly as `systems/overworld.md` Section 9.1 describes: for phase `N` in
1..15 it draws the ground tile with its bottom `N` pixel rows replaced by the
top `N` rows of the moon-gate tile, so the ramps read as the gate rising out of
the throne-room floor and then sinking back into it. The one endgame-specific
detail is the ground half of that composition: this scene substitutes its own
chamber floor tile for the grass the overworld uses, which is why step 13's
repaint matches the ground the gate rose from.

Two consequences for implementation. First, an engine that models this as a
palette animation, a brightness level, or a dedicated endgame effect will not
reproduce it and will duplicate work it already owns — build one phase
composition and let the overworld refresh, the overworld transit, and both
endgame ramps drive it. Second, because the counter is the shared save-backed
byte, these ramps write world state; an engine that keeps the endgame's copy
separate will diverge from the original's save image.

The step helper moves one cell per call and runs one display tick after each
movement. It prefers the axis with greater remaining distance; equal remaining
distance chooses X movement. The caller loops until the current actor reaches
its target before advancing to the next scripted actor or message beat.

The display effects are palette/display operations and full-screen rectangle transitions driven by resident helpers. The exact helper names are implementation details. The compatibility requirement is the order and blocking nature of the presentation: messages pause, movement settles before the next beat, and the final certificate is reached only after the fade/transition sequence completes.

### 7.1 The full-screen fade to black

Between the pulse/fade and panel-transition sequence and the final narrative
presentation, the endgame performs a full-screen **fade to black**. It is one
beat with two halves, and the two halves live in different routines, which is
why earlier revisions of this section got it wrong.

The first half, in the victory sequence itself, is a full-screen opaque fill:

- **Primitive.** A filled rectangle in the driver's current drawing colour. It
  is not a copy, not a mask, and not a palette operation.
- **Bounds.** Inclusive `(0, 0)..(319, 199)` — the whole surface.
- **Colour.** The drawing colour is set to palette index `0` immediately
  before, so the fill is black.
- **Surface.** The render target is pointed at the **hidden** surface before
  the fill and back at the visible page immediately afterwards, so the fill
  itself changes no visible pixel. It also releases the active graphics asset
  segment just before filling.

The second half is the first thing the final narrative presentation helper
(section 8) does. After it has acquired its three presentation resources, and
before it draws anything else, it issues a **full-screen rectangle dissolve**
of the inclusive rectangle `(0, 0)..(319, 199)` from the hidden surface to the
visible page — the entry specified in `display-driver-abi.md` section 9.6. That
path is unconditional and straight-line; there is no branch that skips it.

Because the hidden surface was just filled black, the visible result is that
the whole screen dissolves to black in the driver's deterministic pseudo-random
per-pixel order, and only then does the narrative presentation begin.

**Retraction.** Earlier revisions of this section described the fill as
producing "no visible change at all" and told implementers they could "omit it
entirely if the compositor already starts the certificate page from a known
state". Both statements are withdrawn. The fill is invisible only when
considered in isolation; the dissolve one call later is what puts it on screen.
The clear is therefore load-bearing: an engine that skips it, and then runs the
dissolve, will dissolve the stale contents of its offscreen surface onto the
screen instead of fading to black. If an engine chooses to model neither half,
it must model the net effect — the screen going black — some other way.

**Timing and input.** Two blocking calls, in that order. Neither is paced by a
tick, neither has a per-column or per-pixel schedule the caller controls, and
the title tick does not run during either, because nothing calls it. The
dissolve is self-paced: it visits every pixel of the rectangle exactly once and
returns. There is no keyboard poll in the surrounding code, and by this point
in a session the dissolve entry's own abort gate has long been cleared by
earlier text drawing (`display-driver-abi.md` section 9.6), so this dissolve is
silent and cannot be interrupted. No input is sampled or consumed across the
whole beat.

**Rectangle census.** This is the only rectangle dissolve anywhere in the
endgame, and the only full-screen one in the program. The complete list of
dissolve rectangles and their callers is in `display-driver-abi.md`
section 9.6.

## 8. Final narrative presentation

Immediately before the final scroll, the endgame runs a fixed narrative
presentation sequence. This is not a party-roster retirement lookup and it does
not open town, dwelling, castle, or keep location data to resolve character
homes. The helper opens endgame presentation graphics resources, loads fixed
windows from `END.DAT`, renders the selected window with proportional text, and
uses blocking waits between presentation beats.

The helper's presentation role is:

- retry required endgame graphics and text resources until they are available;
- once they are available, and before drawing anything, dissolve the whole
  screen from the hidden surface to the visible page, which lands as a
  full-screen fade to black because the caller has just filled the hidden
  surface with palette index `0` (section 7.1);
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
Brace markers inside `END.DAT` remain layout markers for the text renderer, as
specified in `formats/end-dat.md`. A clean implementation should keep the six
window selections data-driven, but their semantic role is fixed narrative
presentation, not party-slot retirement data.

### 8.1 Per-window bindings

Each of the six windows binds one panel from the endgame panel archives to one
`END.DAT` record and one paragraph rectangle. All of the values below are fixed
resident data laid out as parallel per-window tables; nothing about them is
computed at run time.

Windows 1 to 3 take their panel from the first endgame panel archive `END1`,
slots 0 to 2 in order; windows 4 to 6 take theirs from the second archive
`END2`, slots 0 to 2 in order. The archive is opened when it first becomes the
required one and released when the next window needs a different archive.

| Window | Archive | Slot | Panel size | Panel top-left | `END.DAT` record |
|---:|---|---:|---|---|---:|
| 1 | `END1` | 0 | 167 x 124 | `(0, 0)` | 1 |
| 2 | `END1` | 1 | 191 x 90 | `(64, 0)` | 2 |
| 3 | `END1` | 2 | 192 x 95 | `(0, 52)` | 3 |
| 4 | `END2` | 0 | 173 x 98 | `(0, 0)` | 4 |
| 5 | `END2` | 1 | 157 x 90 | `(0, 92)` | 5 |
| 6 | `END2` | 2 | 153 x 110 | `(160, 0)` | 6 |

The panel is drawn opaque, with no border, no shadow and no frame of its own.
The window numbering here matches the `END.DAT` record numbering published in
`formats/end-dat.md` section 4.

### 8.2 Per-window paragraph rectangles

The prose is laid out by the proportional paragraph renderer of
`text-output.md` section 8, so each window supplies that renderer's layout
descriptor rather than a single rectangle: a margin pair for lines outside a
named vertical band, a second margin pair for lines strictly inside it, the
band's two bounds, and the pen's starting position. The margin pair is
re-selected at entry and after every line break, which is what makes the prose
flow around the panel. Line advance is nine pixels and glyph output stops once
the pen reaches vertical position 192. The endgame never writes the space
advance, so all six windows lay out with the shipped default of five.

| Window | Pen start | Outside band: left, right | Inside band: left, right | Band low, high |
|---:|---|---|---|---|
| 1 | `(172, 66)` | 172, 320 | 0, 320 | 126, 200 |
| 2 | `(0, 92)` | 0, 320 | 0, 320 | 126, 200 |
| 3 | `(0, 9)` | 0, 320 | 196, 320 | 42, 148 |
| 4 | `(179, 38)` | 179, 320 | 0, 320 | 100, 200 |
| 5 | `(0, 9)` | 0, 320 | 161, 320 | 82, 200 |
| 6 | `(0, 0)` | 0, 154 | 0, 320 | 112, 200 |

Read plainly, that gives: window 1 starts to the right of its top-left panel
and opens out to the full width once the pen passes y = 126; window 2 is full
width throughout, since both of its margin pairs are identical; window 3 starts
full width at the top and indents to x = 196 while the pen is between y = 42
and y = 148, clearing the panel that sits at `(0, 52)`; window 4 mirrors window
1 against a taller panel; window 5 starts full width and indents to x = 161
once the pen passes y = 82, clearing the panel at `(0, 92)`; and window 6 is
clipped to a right margin of 154 — the space to the left of its right-hand
panel — until the pen passes y = 112, after which it uses the full width.

Two windows also draw decorative title strips from the shared `TEXT` strip
archive on top of the panel, before the prose is laid out:

| Window | Strips drawn, in order |
|---:|---|
| 1 | `TEXT` slot 0 at `(216, 0)`, then slot 4 at `(152, 28)` |
| 4 | `TEXT` slot 5 at `(224, 0)`, then slot 0 at `(176, 0)` |

Those two strip pairs read as the chapter titles "The Homecoming" and
"The Dream" respectively; the words are part of the artwork, not typeset text.
The overlap between the two strips of window 4 is intentional kerning — the
second strip is drawn opaque over the first.

### 8.3 Presentation model

The presentation model is a **hard cut**, not a fade or a wipe. Per window,
in order:

1. If this window needs a different panel archive than the one currently open,
   release the open one and load the new one.
2. Select the hidden surface.
3. Issue the text system's clear control. The active text window at this point
   is the full-screen one selected when the presentation began, so this blanks
   the entire hidden page.
4. Draw the decorative title strips, if this window has any.
5. Draw the panel.
6. Install the window's layout descriptor values.
7. Read the window's `END.DAT` record into the shared text scratch buffer and
   lay out its prose with the proportional renderer.
8. For every window except the first, block until a key is pressed.
9. Copy the whole hidden page to the visible page in one instantaneous
   full-screen operation.

So window 1 appears as soon as it is composed, and each later window is
composed entirely off-screen and then published in a single copy on the
player's keypress. The player never sees a partial page, a per-window wipe, or
a redraw in progress.

**Retraction.** Earlier revisions of this section stated that the six windows
have "no caller-owned clear" and that "there is exactly one full-screen
rectangle operation on this path". Both are **withdrawn**. Every window issues
a full-page clear on the hidden surface (step 3) and a full-page copy to the
visible page (step 9); they are simply never visible as separate events,
because both land off-screen or as one atomic copy. What *is* unique on this
path is the **rectangle dissolve** of section 7.1: that happens once, before
the first window, and is not a per-window page-in transition. Do not inherit
the intro's step-1 rectangle dissolve for these windows either; the intro
step-1 contract is specific to that caller.

### 8.4 The certificate backdrop

After the sixth window the presentation waits for one more key, then prepares
the certificate page: select the hidden surface, issue the text system's clear
control, load the end-screen archive, draw its **only** record — a single
260-by-168 image of a blank torn-edged parchment with a plain light interior —
at `(40, 0)`, release the archive, copy the hidden page to the visible page,
and select the visible page as the render target.

The parchment therefore occupies pixels `(40, 0)..(299, 167)`, and the
certificate text of section 9 is printed **directly onto the visible page, over
that parchment**. There is no second composition step and no further page copy;
the text appears line by line as it is printed.

## 9. Certificate scroll

The certificate scroll is the final successful ending screen. It uses the
fixed-cell text-output system, printing **directly onto the visible page over
the parchment image of section 8.4**, with a small endgame-specific line
accumulator so the overlay can compose one line from several fragments before
flushing it.

### 9.1 Text mode and geometry

Three things are set up before the first character is printed, and none of them
is changed again until the elapsed-time report:

1. The cursor is placed at **column 0 of row 1** of the full-screen text window
   (`(0, 0)..(39, 24)`, the window selected back in section 8.3).
2. **Inverse video is switched on**, so every glyph is drawn with its bitmap
   inverted. That is what puts dark lettering on the light parchment; there is
   no colour change and no palette work involved.
3. **Centred output is switched on**, so the wrap-aware printer centres each
   line it emits.

Centring is the standard rule of `text-output.md` section 5, and on this window
it works out to **ordinary centring in a forty-column window**. The printer
counts the columns still available on the current row — the window's right
column minus its left column, minus the cursor's current column — and compares
that count with the **index of the last character** of the line it is about to
emit. The line's starting column is half that difference, truncated toward
zero. Every certificate line begins at column 0 of the full-screen window, so
the rule reduces to `(40 - characters_in_line) / 2`, truncating.

Even-length lines are therefore centred exactly. Odd-length lines land half a
cell — four pixels — left of true centre, because truncation always drops the
half column on the left. That is the only offset in play. An engine that
centres against a width of 39 instead of 40 agrees on odd-length lines but
places **every even-length line one cell (eight pixels) too far left**; among
the lines below that would misplace `saved the life`, `of our sovereign`,
`IS FOREVER` and `to Lord British at Origin Systems!`.

Note that the text is centred on the **screen**, not on the parchment. The
parchment of section 8.4 spans x = 40 through x = 299, so its own centre is
x = 170 while the text's centre is the screen's x = 160. The certificate
therefore sits about ten pixels left of the parchment's centre. **That is
correct and must be reproduced** — do not re-centre the text on the artwork.

Lines are built in a **39-character accumulator**. Each fragment is appended,
clamped at 39 characters, and the whole accumulator is flushed through the
centring printer as soon as the character just appended is a line feed. Fixed
strings that already end in a line feed bypass the accumulator and go straight
to the printer. This is how the variable date, name and duration fragments join
their fixed suffixes into single centred lines. There is no word wrapping in
play: no certificate line reaches 39 characters, and every break below is an
explicit line feed in the fixed text.

### 9.2 The certificate body

The literal prose, in emission order, one line per row:

```text
Be it known that on
the <day ordinal> Day of
the <month ordinal> Month
of the Year
<year hundreds cardinal> Hundred
<year remainder cardinal>

<party leader name> the Avatar

saved the life
of our sovereign
Lord British, thereby
saving our people
and our land.

```

The blank rows shown in that block are exactly the ones the original emits:
**one** after the year-remainder line, **one** after the leader-name line, and
**one** after `and our land.` Each of those three gaps is encoded the same way
in the fixed text — a pair of line feeds — and a line feed is a *combined*
carriage return and line feed (`text-output.md` section 5). The first line feed
of a pair ends the line just printed; the second advances one further row. So a
run of *k* line feeds leaves *k − 1* blank rows, never *k*.

Because the cursor starts on row 1 and nothing on this screen wraps or scrolls,
the whole certificate has a fixed row assignment, which is the easiest thing to
check an implementation against:

| Row | Content |
|---:|---|
| 1 | `Be it known that on` |
| 2 | `the <day ordinal> Day of` |
| 3 | `the <month ordinal> Month` |
| 4 | `of the Year` |
| 5 | `<year hundreds cardinal> Hundred` |
| 6 | `<year remainder cardinal>` |
| 7 | *(blank)* |
| 8 | `<party leader name> the Avatar` |
| 9 | *(blank)* |
| 10 | `saved the life` |
| 11 | `of our sovereign` |
| 12 | `Lord British, thereby` |
| 13 | `saving our people` |
| 14 | `and our land.` |
| 15 | *(blank)* |
| 16 | `THE QUEST OF THE AVATAR` (section 9.3) |
| 17 | `IS FOREVER` (section 9.3) |
| 18–20 | *(blank)* |
| 21 | `Report now, thy Quest compleat in` (section 9.4) |
| 22 | the elapsed-interval line (section 9.4) |
| 23 | `to Lord British at Origin Systems!` (section 9.4) |

Rows 0 through 20 are the rows the parchment covers, so the certificate body
and the closing title land on the parchment while the three report rows land on
the cleared black page below its bottom edge. That is not a coincidence and it
is a useful self-check: an implementation whose report does not fall clear of
the parchment has miscounted a blank row somewhere above.

The four substituted values are:

| Placeholder | Value |
|---|---|
| `<day ordinal>` | The saved day of the month as an ordinal word |
| `<month ordinal>` | The saved month number as an ordinal word — a numbered month, not a named one |
| `<year hundreds cardinal>` | The saved year divided by one hundred, as a cardinal word |
| `<year remainder cardinal>` | The saved year modulo one hundred, as a cardinal word |

The ordinal helper covers the game's calendar range and composes
twenty-first-through-twenty-eighth style ordinals from smaller word fragments.
The cardinal helper covers the year fragments used here.

### 9.3 The closing title

Two more centred lines follow, still in inverse video, reading:

```text
THE QUEST OF THE AVATAR
IS FOREVER
```

They are **not** a sign, a tile composition, or a graphics blit. They go
through the same ordinary fixed-cell character path as everything above, using
the font-slot selector of `text-output.md` section 7: **slot 1, the runic font,
is selected for exactly those two lines** and slot 0 is restored immediately
afterwards. Earlier revisions of this section described a "sign/tile-glyph text
path"; that is withdrawn — the only difference from the body text is which font
slot the glyph source points at. Centring and inverse video are both still in
force, so the two lines are centred and inverse like the body above them.

The stored form uses these exact one-cell code points:

| Decoded token | Stored character | Stored byte | Fixed-font cells |
|---|---|---:|---:|
| `TH` | `[` | `0x5B` | 1 |
| `ST` | `_` | `0x5F` | 1 |
| word space | `@` | `0x40` | 1 |

Other uppercase Latin letters retain their ordinary byte values. The shipped
title is already stored in this encoded form; this presentation path does not
run a Latin-to-rune encoder. A clean implementation whose authored text is
decoded uppercase Latin can reproduce that representation with an ordinary
left-to-right scan: consume `TH` or `ST` as a two-letter token and emit its
single stored character, convert each space to `@`, and pass each other
uppercase letter through unchanged. The two digraphs do not overlap, so their
test order cannot change the result.

The complete vectors, excluding the terminating line feeds, are:

| Decoded line | Stored character sequence | Cells | Start column / x |
|---|---|---:|---:|
| `THE QUEST OF THE AVATAR` | `[E@QUE_@OF@[E@AVATAR` | 20 | 10 / 80 px |
| `IS FOREVER` | `IS@FOREVER` | 10 | 15 / 120 px |

Centring counts the encoded stored characters. Each digraph occupies one
eight-pixel fixed-font cell; using the decoded Latin length would shift the
first line two cells left.

**Three** blank rows follow the closing title — rows 18 through 20 — the gap
between the certificate body and the report below. The fixed text ends that
line with four line feeds, and four line feeds leave three blank rows, for the
reason given in section 9.2.

### 9.4 The elapsed-time report

The report is **not a separate panel**, and there is **no clear** between it and
the certificate. It continues in the same text window, on the same page, with
centring still on. The only thing that changes is that **inverse video is
switched off**, so the report renders in normal video while the body above it
stays inverse. That is consistent with where it lands: its three rows are rows
21 through 23, which fall below the parchment's bottom edge on the cleared
page, so normal video is what makes them legible there while inverse video is
what makes the body legible on the light parchment. Its lines are:

```text
Report now, thy Quest compleat in
<N year(s)>[, <N month(s)>][, <N day(s)>]
to Lord British at Origin Systems!
```

The interval is measured from the fixed campaign start date — year 139, month
4, day 5 — using the same thirteen-month, twenty-eight-day Britannian calendar
as the rest of the game. Subtract the baseline from the saved world clock;
borrow twenty-eight days from the month delta when the day delta is negative,
then borrow thirteen months from the year delta when the month delta is
negative. Each of the three components is then formatted as a decimal number
followed by ` year`, ` month` or ` day`, with a trailing `s` when the value is
greater than one. **A zero component is skipped entirely**, and the `, `
separator is emitted only when a later component will also be printed, so
"years, months, days" collapses naturally.

### 9.5 The terminal state

**Nothing follows.** After `to Lord British at Origin Systems!` the original
program enters a deliberate infinite loop: no key is read, no timer runs, the
program never returns to the menu, and it never exits to the operating system.
The player must reset the machine.

A clean engine should reproduce this as an explicit, intentional end-of-program
state rather than treating it as a hang to be worked around. If an
implementation adds a way out, that is a modern affordance and should be
labelled as one. The refusal branch of section 6 ends the same way: a permanent
idle loop in which the remaining party actors wander the throne room forever.

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

- **Endgame screen geometry.** Closed. The tableau rectangle, cell size, scene
  terrain source and buffer, and both text-window rectangles are published in
  section 3.1; the actor index space and per-class sprites in section 4.
- **Pixel-perfect endgame scene rasters.** The terminal tableau slot layout,
  actor bytes, movement order, gate brightness ramp, and local wander rule are
  specified here. The residual is the driver's exact per-step pixel pattern for
  the gate's brightness entry, which belongs to `display-driver-abi.md`.
- **Final narrative page-in transitions.** Closed. The six windows' archive,
  slot, panel size, panel origin, text record, layout descriptor, title strips
  and presentation model are published in section 8. Each window does clear the
  hidden page and does publish itself with a full-page copy; neither is visible
  as a transition, and neither is the rectangle dissolve of section 7.1, which
  still happens exactly once, before the first window.
- **Display helper taxonomy.** The visual sequence uses resident display, sound, and wait helpers whose exact labels are inferred. The player-visible order and blocking boundaries are specified; the unresolved part is helper taxonomy, not state progression.
- **Asset variant mapping.** Closed for the endgame. The panel archive, slot,
  size and origin for every window, the title strips, and the certificate
  backdrop are published in section 8. The equivalent alternate-depth archives
  hold the same records and remain alternate-hardware parity work.
- **Closing-title rune encoding.** Closed. Section 9.3 publishes the exact TH,
  ST, and word-space code points, canonical decoded-Latin re-encoding rule,
  stored-character test vectors, encoded cell counts, and centred positions.
- **`END.DAT` and `ENDMSG.DAT` prose.** The certificate's fixed prose is
  published in section 9 because it is assembled from resident fragments. The
  narrative prose in `END.DAT` and the dialogue prose in `ENDMSG.DAT` are shipped
  data files: their structure, record count, ordering, seek windows and markup
  conventions are published, but their wording is read from the shipped files at
  run time and is not transcribed here.

## 13. Sources

This document is a cleanroom prose rewrite from private analysis under the
following directories. It intentionally omits assembly, decompiled code,
private offsets, copied binary text dumps, and private note filenames.

- `u5-decomp/functions/ENDGAME_OVL/`
- `u5-decomp/functions/ULTIMA_EXE/`
- `u5-decomp/functions/DUNGEON_OVL/`
- `u5-decomp/functions/DNGLOOK_OVL/`
- `u5-decomp/functions/SJOG_OVL/`
- `u5-decomp/notes/`
- local semantic checks of the shipped dungeon, combat, shared-data, and
  endgame narrative resources.

Local spec cross-references used for terminology and integration:

- `u5-spec/systems/main-loop.md`
- `u5-spec/systems/save-load.md`
- `u5-spec/systems/text-output.md`
- `u5-spec/catalogs/item-list.md`
