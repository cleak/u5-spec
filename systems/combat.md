# Combat

## 1. Overview

Ultima V's combat system is a turn-based, party-versus-monsters tactical mode that plays out on a small fixed-size arena grid. When an overworld, dungeon, or scripted/rest caller triggers a fight, the engine suspends what it was doing, swaps the on-screen scene for an arena, populates the arena with the player's party at one set of fixed entry points and a randomised set of monsters at another, and runs a self-contained round loop until one side is wiped out or the player flees. When the loop returns, the engine restores the suspended world state - player position, the dynamic-objects table, the scene byte - and returns control to the calling mode loop with the fight's after-effects baked in: damage taken, characters dead or asleep, time advanced by the round loop, and resources consumed by combat actions.

Combat is "inside-out" — the world freezes while the fight plays through, the fight has its own table of actors, its own per-letter command dispatch, its own AI, and its own arena terrain — and then the function call returns and the world resumes exactly where it left off. The mode-loops above combat are unaware that combat happened beyond the visible state changes.

This spec describes the combat trigger framing, the arena format and monster placement, the per-round walk over the actor table, the player command set, the monster AI, the attack-resolution primitive, the damage and status model, and integration points with text output, the spell system, and time.

## 2. Combat triggers

Combat enters from one entry point - a single function call from a mode or scripted setup path that takes three parameters: a flags word, an actor-slot index, and an entry-mode bitfield. The entry-mode bitfield distinguishes three setup families:

**Terrain combat.** The default. Reached when the player walks into (or attacks) a hostile creature on the overworld or in a town. The dynamic-objects-table slot of the offending creature is passed along. Two independent selections happen before the round loop: the **outdoor arena** is chosen from the world terrain under that creature plus the party's vehicle state, and the encounter's **base combat class** is derived from the creature's own sprite byte by a small linear formula. The arena is loaded first; the terrain-combat setup then seats the party, rolls the monster spawn count from the base class's stat row, and places each monster at one of the arena's sixteen arrival positions. `encounters.md` Section 4 publishes both selectors.

**Ambush combat.** A separate setup branch from ordinary terrain combat. The current resolved setup target is the DNGLOOK room-NPC setup entry used by dungeon/rest-style room setup, not the ordinary terrain helper and not the town hostile-NPC alarm path. Do not infer its arena choice, monster count, or placement order from the placement-shuffle branch inside the terrain setup helper: that branch is live, but its caller is the surface camp-ambush route, not this one (Section 5).
**Rest/camp "alternate" setup.** Reached by H-Hole-up rest/camp callers. The
alternate setup target is the CMDS H-Hole-up helper rather than an SJOG or
scripted-fight dispatcher. It may finish the rest/camp outcome without combat
by returning a nonzero predicate; in that case the framer skips the round loop
entirely. When the helper returns the combat-continuation value, the framer
enters the ordinary combat round loop with the arena state prepared by that
rest/camp setup path.

If setup prepares an arena, the framer clears a few combat-state bytes and
calls into the round loop. If the rest/camp alternate helper declines combat,
the framer goes directly to teardown. On return from a real round loop, whether
via victory, defeat, or escape, the framer runs the teardown described in
Section 4.

## 3. The arena

A combat arena is a rectangle of terrain tiles plus a band of metadata describing where actors enter and which terrain pieces hold special meaning (spawn points, hazards, ladders). Two on-disk files hold the engine's full set of arenas: a bank of sixteen outdoor arenas keyed by overworld terrain class (each tied to a tile family — grass, forest, hills, swamp), and a much larger bank of dungeon-encounter arenas (one hundred twelve records).

Each arena occupies a fixed-size record. The first part is the **terrain grid** — an eleven-by-eleven array of tile bytes describing the arena floor. The remainder is the **metadata band** — a flat run of bytes per row that the engine reads at setup. The outdoor slices provide six party entry coordinate pairs and sixteen monster placement-slot coordinate pairs; the complete traced reader census finds no other outdoor metadata consumption. Hazards remain terrain/object runtime behavior, while edges are geometric and use no record byte. The arena format spec covers the byte-by-byte layout; from combat's perspective the contract is "given an arena ID, the on-disk record tells us a 121-cell terrain grid and the confirmed setup slices."

When the arena loads, its terrain grid is copied into a runtime grid in the data segment with a row stride padded out to thirty-two bytes (a power-of-two stride that lets the renderer index by `(row << 5) + col`). Movement and visibility consult this runtime grid; the on-disk record is not touched again until the next combat enters.

**Wall and blocked tiles** in the runtime grid are recognised through combat's
own arena passability lookup, not through the world/town tile-id bitmap. That
lookup governs **movement only**. An actor standing on a cell it could not have
walked onto still takes its turn on schedule.

**Retraction - the per-round skip is a restraint guard, not a walkability
guard.** Earlier revisions of this paragraph, and of Section 7's per-actor body,
said that an actor whose record places it on a blocked arena tile "is silently
skipped for the round" as a defensive guard against bad placement. That is
**withdrawn**. The round loop's pre-decrement skip reads the arena terrain under
the actor and tests it against exactly two tile ids - the stocks `0x84` and the
manacles `0x85` - and nothing else. Water, swamp, mountains, walls, force
fields and every other terrain are outside the test. Section 7.1 gives the full
contract for both cases. An engine that implements the withdrawn wording freezes
every actor the original leaves acting, which in the water arenas is every
monster in the fight (Section 5.4 and `encounters.md` Section 4).

**Blocked cells and geometric edges.** A requested cardinal destination that
stays inside X and Y `0..10` first runs the ordinary collision/passability
probe. Rejection prints `Blocked!` plus a newline, plays the 165 Hz bump tone
for 200 calibrated units, flushes pending input, and re-prompts without moving.
A destination outside that inclusive range bypasses collision and reaches the
edge helper; there is no open-edge metadata bit or edge terrain marker.
The movement primitive has already printed the requested cardinal name and a
newline before either branch, so that direction line precedes `Blocked!` or any
edge-helper text.

The edge helper applies these rules in order:

1. If the party's transport marker is in the ship family, print a leading
   newline, `Stay with ship!`, and a trailing newline, then refuse silently with
   no bump tone.
2. Only a party-side actor participates in direction sharing. The first such
   actor attempting an edge stores the cardinal direction if the shared byte is
   zero. In an encounter whose mode has the high bit set, a later party actor
   choosing a different direction is refused with a leading newline,
   `All must use the same exit!`, a trailing newline, and the same 165 Hz bump
   tone. Ordinary modes permit a different later direction. Monster-side
   actors neither seed nor test it.
3. On acceptance, count live unmarked actors before removing anybody. With no
   foes, print `Leave!`; with one or more foes, print `Escape!`. These two
   strings have a trailing newline and no leading newline. Both play the rising
   1200-to-2000 Hz glissando.
4. Clear active-player selection, remove only the acting combatant, run the
   party/status check and one world tick, and report success to the command
   parser. The arena coordinate itself is never committed outside combat.

An accepted edge is therefore an individual actor departure, not an immediate
fight exit. Remaining actors keep taking turns. An earlier revision said the
first accepted edge ended the round loop before anyone else could act; that is
withdrawn.

**Deterministic edge vectors.** Assume the direction name is the first line in
each transcript:

| Initial condition and request | Observable result |
|---|---|
| Actor at `(5,5)` requests North; in-bounds `(5,4)` fails passability | `North\nBlocked!\n`; bump tone and input flush; coordinates and actor tables unchanged; free re-prompt. |
| Actor at `(0,5)` requests West while the transport marker is ship-family | `West\n\nStay with ship!\n`; no tone; actor remains. |
| Constrained encounter already records North; a party actor at the east edge requests East | `East\n\nAll must use the same exit!\n`; bump tone; actor remains and the stored direction stays North. |
| Ordinary encounter, live foes remain, party actor at the east edge requests East | `East\nEscape!\n`; only that actor is released, command result is accepted/committed, and combat continues. |
| No live foes, party actor at the west edge requests West | `West\nLeave!\n`; only that actor is released. If it was the last actor on either side, the round loop returns word zero. |
| Live foes remain and the last party actor successfully leaves | The direction and `Escape!` lines occur first; the immediate side recount then prints the loss line and returns word one. |

For every accepted-edge vector, a later framer exit restores the exact saved
world X, Y and Z and the complete pre-combat active-object snapshot. Changing
the arena edge or direction in the vector changes no restored world coordinate.

## 4. Combat enter/exit framing

The framing function bridges the world-mode loop and the combat round loop. It must save and restore enough state that the calling mode loop is unaware combat happened.

**Save phase (before round loop).**
- Snapshot the player's world coordinates (X, Y, Z), the active-player byte, and the *scene byte* — the same scene byte the input system uses to choose between idle and prompt mode and the time system uses to choose between full-darkness and time-of-day daylight.
- Set the scene byte to a combat sentinel value, so any concurrent system that reads it knows combat is in progress.
- **Snapshot the entire 32-record dynamic-objects table** into a backup region. The table holds the world's monsters, NPCs, ships, horses, and other moveable entities; combat will overwrite it with its own actors.
- Run one of the three setup paths (terrain / ambush / rest/camp alternate) to
  populate the table with combat actors or decide that no combat round should
  run. The dispatch order is: an entry mode of **exactly zero** selects terrain
  setup; otherwise the rest/camp-alternate flag is tested before the ambush
  flag; and a nonzero entry mode with neither flag set runs **no setup at all**
  and falls straight through to the common tail. The rest/camp helper returns a
  predicate: a **zero** return skips the round loop entirely, while a nonzero
  return continues into combat.
- The **ambush** branch loads no arena of its own. It calls the same room-combat
  setup helper the dungeon room path uses, with an entry mode that passes that
  helper's placement gate and a zero tile argument, and it **discards** the slot
  or class argument its caller supplied. Consequently the ambush branch operates
  on whatever arena terrain and metadata band are already resident in the arena
  buffer, so its callers are responsible for having put a usable arena there
  first. For dungeon wandering-monster combat the dungeon room painter
  synthesises both the terrain and the metadata band immediately beforehand
  (`systems/dungeon-mode.md` Section 14.1).
- Clear the combat-state bytes the round loop expects on entry.

**Round loop.** Section 7 describes what runs inside.

**Restore phase (after round loop).**
- If the resident tile-restoration flag is set when the round loop returns,
  clear that flag and invoke the display driver's tile-graphics
  save/restore/mutation entry with mode value `1` before the ordinary world
  redraw. The reached mode restores driver-saved tile graphics; combat owns
  only the sampling/clear/call ordering, while the setter provenance and
  tile-asset mutation details belong to the dungeon and driver specs.
- Restore the player's coordinates and the scene byte from the saved slots.
- Mark visibility dirty so the next world frame redraws fully, and refresh the on-screen party-stats panel.
- Restore the active-player slot — but only if the pre-combat active player has not died or fallen asleep during the fight; if their status is now `'D'` (dead) or `'S'` (asleep), keep the active-player slot cleared and let the player re-select.
- Inverse-copy the dynamic-objects table from its backup, restoring the world's monsters, NPCs, ships, horses exactly as they were before the fight.

The overall effect is "combat is a function call." From the calling mode loop's perspective, control left for combat and came back with the world unchanged except for damage, deaths, and clock advance.

One resident terrain-target wrapper performs additional caller-side
reconciliation after the framer returns. That wrapper runs the framer with the
ordinary terrain setup, then calls a shared post-combat object reconciler with
the original trigger slot. The reconciler restores the saved world-object table
again, then either clears bytes 0 through 4 of that trigger slot or rewrites a
`0x2C..0x2F` restored trigger into the persistent body/retrieval state when the
combat exit-message state was set. This is the proved durable trigger-removal
path for ordinary active-object combat triggers. It is not a COMBAT-round-loop
loot sweep and it does not consume the temporary combat death/drop markers.

### 4.1 Combat-entry presentation

Two separate banners are printed when a terrain fight begins, by two different
stages, and an implementation that merges them gets both the order and the
blank rows wrong.

**Banner one - the group name.** The world-side terrain-combat entry step
prints it *before* it calls the framer. In emission order:

| Order | Emitted | Effect |
|---:|---|---|
| 1 | one line feed | closes whatever the command echo left on the row and moves to column 0 of the next row |
| 2 | centre-output on | control byte; no cell is written |
| 3 | the group name for the encounter's class | one row, horizontally centred |
| 4 | centre-output off | control byte; no cell is written |
| 5 | two line feeds | ends the name's row and leaves one blank row below it |

The name is a **shipped forty-eight-entry table indexed by class id**, published
in `catalogs/monster-bestiary.md` Section 2.2. There is no suffix rule: nothing
appends an `S`, nothing inspects the singular class-name table, and nothing
consults the monster count. Twenty-two of the forty-eight entries happen to be
the singular name plus `S`; the other twenty-six are not, so a generating rule
is impossible and the table must be shipped verbatim.

When the hostile's masked sprite byte is below `0x40` the table is bypassed
entirely and the fixed literal `PIRATES` is printed instead
(`systems/encounters.md` Section 4).

Three consequences worth stating flatly:

- **The banner is count-independent.** It is emitted a whole stage before the
  monster count is chosen, and nothing carries the count backwards, so a lone
  attacker still gets the group name: one bat announces `BATS`. There is no
  singular form of this banner anywhere in the game.
- **The Shadow Lord fight announces `SHADOW LORD`.** No article, no "The", no
  separate singular caption. The sceptre line of `systems/encounters.md`
  Section 4 is printed after it.
- **It is terrain-entry-only.** Only the world-side terrain-combat entry step
  prints it. The one entry that reaches setup without passing through that
  step is the surface camp ambush, which reaches terrain setup through its
  command-overlay wrapper rather than through the world-side entry step
  (Section 5); it prints the conflict banner below but **no** group name.
  *Confidence: probable.* The call sites are established by a near-call census
  of the resident image and all twenty-three overlays; the entry paths
  themselves were not stepped, and far or register-indirect transfers were not
  censused.

**Centring is a cursor move, not padding.** The printer computes a window-local
starting column and repositions the cursor there; the cells to its left are
never written, so whatever stood there remains. For a line emitted with the
cursor at the window's left edge - which the preceding line feed guarantees
here - that starting column is
`floor((columns_in_window - characters_in_line) / 2)`, truncating;
`systems/text-output.md` Section 5 owns the general form for a line that starts
mid-row. In the sixteen-column message window that is
`floor((16 - length) / 2)`, and the absolute column is 24 plus it - so
`BATS` occupies absolute columns 30..33 and `LORD BRITISH` occupies 26..37.
Every shipped entry is twelve characters or shorter, so no group name ever
wraps. At a capacity of sixteen the formula places every even-length caption
symmetrically, which is a useful self-check on the width figure but not
independent evidence for it.

**Banner two - the conflict banner.** Terrain setup prints it at the start,
before any monster is placed (Section 5, step 3). The literal is:

> `*** CONFLICT ***` followed by one line feed

Exactly sixteen printable characters: three flank glyphs, one space, the eight
letters of `CONFLICT`, one space, three flank glyphs. Its properties:

- **The flank glyph is character code `0x2A`**, three per side - the ASCII
  asterisk code point, **not** `0x2B` (`+`). The distinction is visible: in the
  8x8 gameplay font, `0x2A` is drawn as a solid four-pointed diamond that reads
  as a **bold cross** at cell size, while `0x2B` is a thin two-pixel cross. A
  transcript that renders this banner with literal `+` characters differs from
  the original in glyph shape, which is why player-facing transcripts of this
  line are commonly written `+++ CONFLICT +++`.
- **It fills the message window edge to edge**, absolute columns 24 through 39,
  on one row. Sixteen characters is exactly the window's capacity.
- **It is not centred, and centring would not move it.** The preceding stage
  cleared the centre flag and nothing on the terrain path sets it again; even if
  it were set, a sixteen-character caption in a sixteen-cell window has exactly
  one centred position, column zero.
- **Its trailing line feed costs no row.** The row is full when the line feed is
  reached inside the same source string, so the printer's full-row suppression
  consumes it (`systems/text-output.md` Section 6). The cursor is left at column
  0 of the following row and **no blank row** appears under the banner.
- **It is unconditional.** The test that precedes it cannot fail, so every
  terrain-setup entry prints it.

**No direct cell writes.** Both banners go through the ordinary wrap-aware
string printer and the per-cell emitter; neither pre-positions the cursor into
the frame, rewrites the window rectangle, nor pokes cells. Everything about
their placement follows from the active window's rectangle and the ordinary
wrap and centring rules.

**Which window.** Both banners land in whatever window is active; they select
none of their own. On the traced overworld and town routes that is the gameplay
message window, columns 24..39 (`systems/text-output.md` Section 10.1), and the
absolute columns quoted above follow from that. *Confidence: probable.* The
full-stats redraw that the turn loops run ends by selecting the message window,
and none of the routines between it and the banners re-selects another; the turn
loops themselves were not stepped, so the window-local placement is established
while the absolute columns inherit this caveat.

**The full entry transcript.** For an overworld Attack that lands on a hostile,
in order:

| Row | Content |
|---|---|
| 1 | the command-echo marker, then `Attack-` and the chosen direction word |
| 2 | *(blank)* |
| 3 | the centred group name |
| 4 | *(blank)* |
| 5 | `*** CONFLICT ***`, filling the row |

with `The Sceptre is reclaimed!` inserted after the group name on the Shadow
Lord branch when the sceptre is held (`systems/encounters.md` Section 4). The
echo marker is not an ASCII `>`: it is a composited cap glyph, described in
`systems/text-output.md` Section 10.2.


## 5. Party seating and monster placement

The arena record is selected and loaded **before** the framer runs, by the
terrain-combat entry step described in `encounters.md` Section 4. By the time
the setup helper runs, the arena's terrain grid and its four metadata slices —
six party entry X values, six party entry Y values, sixteen placement-slot X
values, sixteen placement-slot Y values — are already resident. The setup
helper then runs a per-encounter pass that clears both combat tables and seats
the party, and only afterwards picks a monster count, picks a class per
monster, and writes one record per spawned monster.

**Retraction - the placement-slot shuffle is live, and the terrain setup helper
has two callers, not one.** Earlier revisions of this section said the helper's
placement-shuffle branch was dormant because "the complete caller census has one
caller and it always leaves the branch inactive". **That is withdrawn.** There
are exactly two routes into the terrain setup helper and they pass different
setup flags:

- The **ordinary wilderness or town encounter** passes a flag word that leaves
  the shuffle bit clear. Monsters are placed in identity slot order: the first
  monster takes authored cell 0, the second cell 1, and so on.
- The **surface camp ambush** - overworld `H` Hole up, which rolls once per
  elapsed hour for an interruption and prints its ambush line when it fires
  (`rest-and-camp.md` Section 6, `encounters.md` Section 6) - reaches the same
  setup helper through its CMDS wrapper, and reaches it **only** with the
  shuffle bit set, which it forwards verbatim. The earlier statement that
  rest/camp entry "uses neither shuffle" is withdrawn with the rest.

The permutation itself is unchanged from the earlier description and is worth
restating precisely, because it is not a uniform shuffle: initialise slots
`0..15`, then for each current index `0..14` draw an independent index from the
full inclusive range `0..15` and swap the two entries. That is fifteen random
transpositions, and it does **not** produce a uniform permutation - an engine
that substitutes a correct Fisher-Yates shuffle will not reproduce the
original's distribution. With `N` monsters the permuted order makes them occupy
a random `N`-subset of the sixteen authored cells in a random order, rather than
the first `N`. The camp ambush loads arena record 0, whose sixteen monster cells
are all distinct and all on grass, spread around the arena's corners and edges,
so the permutation is observable in play rather than a no-op. The shuffle
permutes only which authored cell each monster receives; it reads no terrain, so
it does not affect Section 5.4's "no terrain validation" contract. The earlier
source summary that called this a Fisher-Yates ambush branch remains withdrawn.

**One further difference on the camp route.** The camp-ambush entry also skips
the pre-placement pass that clears the combat tables and seats the party from the
arena record's party-seat rows. **Where the party's arena coordinates come from
on that route is not established** and should be settled by observation before it
is implemented; do not assume the arena-record party seats apply there.

Dungeon ambush-mode entry is a separate matter and is unchanged. The only
reachable ambush-mode callers are the dungeon A-Attack forward contact and the
dungeon post-action contact/auto-face path. Both synthesize the resident arena
through the dungeon room painter, then call the framer. The framer loads no
`.CBT` record, discards the supplied class/slot argument, and invokes the
room-combat setup helper with mode two and tile zero.

The live room painter uses a distinct sixteen-swap algorithm: initialize
`0..15`, then for each current index `0..15` draw from the full inclusive
`0..15` range and swap. During those same sixteen passes it clears all source
cells. It then uses the already-stored wandering-monster class, always consumes
one `random_range(1, spawn_count)` draw, and only afterward overwrites the
result with exact eight or sixteen when that stat byte is a sentinel. It writes
the class source into the first `count` permuted slots. The later source setup
scans indexes in ascending order, so actor placement and speed draws occur in
ascending occupied-source order rather than permutation order.

After party seating, that setup helper consumes four unconditional
random-special palette draws even though synthesized wandering-monster bands
contain only ordinary sources. Party ring/equipment effects can insert their
own draws between the painter's count roll and those four palette rolls. Each
ordinary monster placement then consumes one speed-variation draw.

**Deterministic shuffle vector.** Starting from shared PRNG state `0x0000`, the
first sixteen `random_range(0,15)` results are
`[2,4,4,4,12,7,6,4,4,4,10,11,7,4,4,0]`. The live sixteen-swap result is
`[15,4,1,0,14,7,6,3,5,8,10,11,12,9,13,2]`, leaving state `0x01C0`.
For Giant Rat, the next `1..10` draw returns nine and leaves state `0x80DA`;
the source slots written are `[15,4,1,0,14,7,6,3,5]`, then consumed in order
`[0,1,3,4,5,6,7,14,15]`. For Bat, the corresponding `1..16` draw returns
eleven, then the exact-count sentinel overwrites it with sixteen while state
still advances to `0x80DA`. With no equipment-dependent seating draws, the four
palette indexes are `[5,1,7,4]` (classes `[24,21,24,33]`) and leave state
`0x752C` before the first speed draw. The fifteen-swap result from state zero -
the permutation the camp-ambush route actually applies - is
`[2,4,1,0,14,7,6,3,5,8,10,11,12,9,13,15]`, state `0x0CF4`. (*Corrected:* this
vector was previously labelled dormant.)

Earlier revisions of this section, and the answers published against it, seated
the party at the placement slots following the monster count -
`placement[count .. count+5]` - for both terrain and room combat. That is
retracted: party seats come from the arena record's own six party-entry X and Y
values and never depend on the monster count.

**Order of operations.** Ordinary terrain combat setup is strictly:

1. Clear all thirty-two combat descriptors (every field) and the first seven
   bytes of all thirty-two combat-instance active-object records. The eighth
   byte of an active-object record — its descriptor back-link — is not touched
   by this clear; it is set to the "no linked descriptor" sentinel when the
   record is allocated.
2. Seat the party from the per-arena party entry coordinates.
3. Print the conflict banner (Section 4.1).
4. Choose the monster count.
5. Place the monsters into the sixteen placement slots.

Because seating happens first and reads its own coordinate table, party seats
never depend on the monster count and never consume a placement slot.

**Seating the party.** The engine walks party slots zero through
`party_size - 1` in roster order. For each slot:

- A character whose status byte is `'D'` (dead) is skipped entirely: no
  descriptor, no active-object record, no arena presence. The remaining members
  therefore pack into the low descriptor indexes rather than keeping their
  roster index.
- Otherwise the member is placed at arena `(X, Y)` taken from the selected
  arena's party entry coordinate slices, indexed by *party slot* (the roster
  index, not the packed descriptor index).
- The member's renderer-facing tile is derived from the character's class
  letter, mapping onto the four human combat classes: Avatar to class 3,
  Bard/Shepherd/Tinker to class 1, Fighter/Paladin/Ranger to class 2,
  Druid/Mage to class 0. A class letter outside that set leaves the
  presentation byte at zero.
- A member whose status byte is `'S'` (asleep) is seated and then immediately
  marked asleep: status stays `'S'`, the descriptor's disabled bit is set, the
  presentation record shows the prone marker, and the active-player sentinel is
  cleared if that member was the active player.
- Before a living member is placed, if that member wears either the Ring of
  Invisibility or the Ring of Regeneration, one uniform draw in `[0, 15]` is
  taken. The single outcome `11` destroys the ring: the "a ring has vanished"
  message, a tone, and the matching equipment slot set to the empty marker.
- After the member is placed, a ring-effect step runs - but **only** for members
  whose status byte is exactly `'G'` (good) or `'P'` (poisoned). A wearer of the
  Ring of Invisibility is marked hidden and its presentation byte switched to the
  suppressed-sprite value. The Ring of Regeneration arm is a **whole-party
  regeneration sweep**, not a single tick for the member that triggered it: it
  draws one uniform value in `[0, 7]` for every party member who is alive and
  wearing the regeneration ring *at that moment*, including members whose status
  is neither good nor poisoned. *(Corrected: an earlier revision said a wearer
  "runs the regeneration tick once at entry". That understates both the draw
  count and the healing - with two eligible wearers in good condition the pass
  runs two sweeps of two draws each. See `catalogs/item-list.md`, Ring of
  Regeneration, whose combat-cadence note is scoped by this correction.)*

The exact per-member ordering is load-bearing for PRNG reproduction, because the
vanish check lands **before** the same member's own ring-effect step and before
every later member's vanish check: one vanish lowers every subsequent count in
the same seating pass. Section 5.3 gives the full entry-order contract.

**How the two tables are indexed.** Each seated actor gets one combat
descriptor and one renderer-facing active-object record, allocated by two
independent first-free scans:

- Descriptors are scanned from index zero for party members and from index six
  for monsters, taking the first descriptor whose flags byte is zero. The two
  ranges therefore cannot collide even when several party members are dead.
- Active-object records are scanned from index zero for *everyone*, taking the
  first record whose tile byte is zero.

For party members the two scans run in lockstep — both start at zero, and each
seated member consumes exactly one entry from each table — so **a party
member's descriptor index and its active-object index are always equal**.
Skipping a dead member packs both sequences identically: if the character in
roster slot zero is dead, the next living member takes descriptor zero and
active-object record zero.

The indexes do diverge for monsters, because their descriptors start at index
six while their active-object records continue from the first record left free
by the seated party. With a live party of four, the first monster is descriptor
six paired with active-object record four, the second is descriptor seven
paired with active-object record five, and so on.

Because of that, the descriptor's active-object link byte is the authoritative
pairing in both directions; an engine should follow the link rather than assume
the two indexes are equal.

One consequence of allocating active-object records by "tile byte is zero":
a party member whose class letter falls outside the recognised set leaves both
tile bytes at zero, so its record still reads as free and the next seated
member would be allocated the same record. No shipped class letter reaches
that case, but an engine that invents new class letters must give each one a
nonzero combat tile.

**Party descriptor seeding.** For each seated party member the descriptor
receives:

| Descriptor field | Seeded value |
|---|---|
| HP/wound counter | Not written; party health is read from the character record, not from the descriptor. |
| Base-step | The character's dexterity. |
| Flags/faction | The party-side marker (bit `0x80`, Section 6.1); the asleep/magically-disabled bit is additionally set when the status byte is neither `'G'` (good) nor `'P'` (poisoned). |
| Owner/target/class | The character's roster slot index. |
| Active-object link | The allocated combat-instance active-object index. |
| Phase counter | Thirty-six minus the base-step. |
| Arena X, arena Y | The per-arena party entry coordinates for that roster slot. |

The matching active-object record receives the class-derived tile in both its
tile and tile-mirror bytes, the same arena coordinates, the current Z plane, the
roster slot index in its auxiliary byte, and the "no linked descriptor yet"
sentinel in its last byte.

**Arena-centre special.** If the loaded arena's centre cell (row five, column
five) holds the magic-field marker tile `0xDC`, the setup pass converts that
cell into a special active object with setup id one, using the same
auxiliary-byte rule the dungeon-room loader applies to that id. No shipped
outdoor arena carries that tile at that cell, so this is inert for stock
`BRIT.CBT` data and is documented only so a custom arena behaves the same way.

**Counting monsters.** The engine consults the default spawn-count byte in the
combat-class stat row for the encounter's base class. That base class is the
class id derived from the triggering active object, not the arena index — the
two are independent selections (see `encounters.md` Section 4). The count byte
is one field of the eight-byte class stat row specified in
`formats/data-ovl.md`; the surrounding bytes are the other class stat fields,
not terrain-combat weights. Three count values are treated as exact counts and
used unchanged: one, eight, and sixteen. Any other value is treated as a
maximum: the actual count is rolled to a uniform integer in `[1, max]`.

An **early-game encounter-size damper** — a saved-game flag historically
mislabelled the "double-encounter" or "fortunes of war" flag — modifies that
roll while it is set. Both rolls draw a uniform integer in `[1, n]`, so applying
the second roll to the first roll's result can only lower the count, never raise
it: the flag is a damper, not a doubler. It has no effect at all on encounter
classes whose spawn-count field is one of the three exact-count values one,
eight and sixteen, because those skip both rolls. Its full life cycle is now
settled and no player action participates in it:

- The flag is a persistent byte of the saved game (`formats/saved-gam.md`).
- The factory new-game template ships it **already switched on**, and character
  creation copies that template wholesale into the first save, so every fresh
  game starts with the damper active. Save and load carry it unchanged.
- Nothing in gameplay ever sets it. The only write anywhere in the engine is a
  clear, performed by the per-turn cleanup at the calendar-month rollover.
- Because the shipped calendar starts partway through a month, the damper
  survives the first twenty-four in-game days of a new game and is then cleared
  permanently — nothing can switch it on again.

The reroll arm ends with a defensive cap at twenty-six.

**Reachable-count invariant.** With shipped class data the count can never
exceed sixteen. The largest default spawn count in the forty-eight-row class
stat table is sixteen, and sixteen is one of the three exact-count sentinels,
so it is used verbatim; every non-sentinel value is re-rolled down into
`[1, max]` and the largest non-sentinel value in the table is thirteen. The
twenty-six cap is therefore unreachable defensive code, placement slot indexes
sixteen through twenty-five are never used, and a conforming engine may treat
the sixteen placement slots as sufficient for every terrain encounter. A count
of exactly sixteen is also not a conflict with party seating, because party
seats come from a different per-arena table and are written before any monster
is placed.

A **town-style single-attacker override** applies before the lookup: if the
pre-combat scene was a town, dwelling, castle, or keep, the party is on the
surface, and the base class is not 12 (Guard), the count is forced to one. This
path is live — the town mode loop reaches the same terrain-combat entry the
overworld uses — so attacking an ordinary townsperson produces one attacker,
while attacking a guard falls through to the Guard row's sentinel count of
eight.

The conflict banner is printed at the start of setup, before any monsters are placed. Its exact literal, flank glyphs, placement and blank-row behaviour are in Section 4.1.

**Picking arrival positions.** Each monster gets one of sixteen arena cells,
indexed by a placement slot. For ordinary terrain combat, slots are walked in
identity order so placements are deterministic for the selected arena record.
The terrain helper's fifteen-transposition branch specified above is inactive on
this route but live on the surface camp-ambush route. The selected `BRIT.CBT` arena is authoritative
for the sixteen slots' `(x, y)` coordinates: the arena loader copies those
coordinates from the record metadata band into two resident scratch tables, and
the placement helper then reads the resident copies. A clean engine should
therefore treat a hard-coded resident coordinate list as only the values from
whatever record was most recently loaded, not as global fixed placement data.
The same arena-load step also copies the two six-byte party entry coordinate
slices consumed by the seating pass above; those four slices are the whole of
the arena record's placement metadata.

**Ambush and camp reveal slots.** Ambush-style and camp-attack combats can
carry a small reveal table for hidden arena features. The reveal helper is
inactive in ordinary terrain combat. When the helper is active and an actor
steps onto one of up to eight pre-stamped reveal coordinates, that coordinate
is consumed so it cannot fire again, one or two arena cells are rewritten with
the associated reveal tile when their target coordinates are inside the
eleven-by-eleven arena, and the screen is redrawn immediately. Values outside
the arena coordinate range are sentinels for "no stamp" rather than map
coordinates. The clean record shape is specified in `formats/data-ovl.md`;
the shipped coordinates and reveal tiles are asset data.

**Picking a class per monster.** The first monster always uses the encounter's
base combat class, derived from the triggering creature. Subsequent monsters
normally reuse that same class. For early spawn indexes below the
`count / 4 + 1` threshold, each monster rolls a one-in-nine check; only a zero
result substitutes the base class's **companion class** from the per-class
companion table. Later spawn indexes never roll for that substitution. The
companion table is forty-eight entries indexed by class id, and its values are
class ids, not tile ids — it is the "and a few of something else showed up"
table (for example Orc bands mix in Trolls, Ghost bands mix in Skeletons,
Daemon bands mix in Dragons). The full mapping is published in
`catalogs/monster-bestiary.md`. A spawned actor's renderer-facing tile is then
derived from whichever class was chosen.

Placement initialises two linked records per monster. The renderer-facing
active-object record receives the class-derived tile in both its tile and
tile-mirror bytes, the arena coordinates, and the current Z plane. The parallel
combat-effect descriptor receives: the class's maximum HP as its HP/wound
counter; a base-step of the class speed seed randomised by a uniform `[-4, +3]`
adjustment, reverted to the unadjusted seed whenever the adjusted value would
exceed thirty (Section 5.2); a phase counter of thirty-six minus the base-step; the class id
in its owner/target/class field; the active-object link; and the hostile
faction tag — except for class ids eight and nine, which get the
passive/neutral tag instead so they render and can be interacted with but are
never targeted. The placement helper returns when all monsters are written.

**Marker-only placements.** The shared placement primitive has a third mode
besides party seeding and monster seeding. In marker mode it allocates **no**
combat descriptor at all: only a renderer-facing active-object record is
written, with the caller's raw id in both tile bytes and in the auxiliary byte,
plus the placement coordinates, the plane value, and the same last-byte
sentinel. Because no descriptor exists, a marker never takes a turn, never
appears to the target picker, and has no descriptor link pointing back at it.
Dungeon-room special sources use this mode; see `formats/cbt.md` Section 5.
Descriptor slots are considered free when their flags byte is zero, so an
implementation that leaves stale nonzero flags on a released slot makes that
slot permanently unallocatable.

### 5.1 The party actor's base step is the raw dexterity byte

**Is the party descriptor's base step floored, clamped or scaled before the
`36 - base_step` reset?** No. *(Established, for every combat entry: the
party-seeding arm is shared by the terrain, town and both dungeon entries.)*

The seating pass copies the character's dexterity byte into the actor's base
step verbatim. There is no minimum, no maximum, no level scaling, no equipment
adjustment and no random variation applied on the way - nothing sits between
reading the roster stat and writing the descriptor field. The phase counter is
then set to `36 - base_step` in eight-bit arithmetic, and the identical constant
and formula are used again at every in-combat refresh (Section 7). A dead member
is skipped before any of this and never receives a base step at all. The speed
variation in Section 5.2 belongs to the monster arm of the same placement
primitive and never touches a party actor.

**The floor is in character creation, not in combat, and the "DEX 3 fresh
Avatar" premise is false.** A questionnaire-created Avatar cannot have a
dexterity below 15, so the pathological case that motivated this contract is not
reachable from chargen. Both halves below matter, because an engine implementing
chargen needs the floor and an engine implementing transfer needs the
conversion:

- **Questionnaire chargen floors dexterity at 15.** The questionnaire's
  dexterity tally starts from the shipped seed record's dexterity of `15`, not
  from zero, and every virtue's dexterity delta is zero or positive
  (`chargen.md` Section 6 publishes the delta table; its dexterity column reads
  0, 2, 0, 1, 1, 0, 1, 0 across the eight virtues in canonical order). Dexterity
  receives no floor at commit time - unlike strength, which is floored to 20 -
  because 15 is simply where the tally starts. A questionnaire Avatar therefore
  enters play with dexterity 15 or better, giving a phase counter of **21 or
  less**. Against a bat, whose class speed rating is 30 and whose post-variation
  phase counter is 6 to 10, that is roughly one party action per two to three
  bat actions, not one per five or six. *(The floor of 15 is established. The
  **upper** end of the questionnaire's dexterity range is deliberately not
  published: it is an inference from the shape of the virtue tournament rather
  than a traced enumeration of the question-pair table, so bound it by the delta
  table and the tournament structure, not by a stated ceiling.)*
- **The Ultima IV transfer can produce a single-digit dexterity.** The
  transfer's three-region attribute conversion maps a source value below 10 to
  itself unchanged, and dexterity is one of the two attributes the transfer does
  not floor (`u4-transfer.md` Section 7 publishes the conversion; both of its
  divisions truncate toward zero). A transferred Avatar really can carry a
  single-digit dexterity - 1 through 9 - and therefore, by the `36 - base_step`
  formula above, a phase counter of **27 to 35** for the whole early game. The
  scenario is real; it is transfer-only. *(Established.)*
- **The shipped companions are unaffected either way.** Their seed dexterity
  values run from 17 to 26, giving phase counters of 10 to 19. *(Established.)*
- **Dexterity is never reduced by any game mechanic.** The only movement is
  upward, for the Avatar alone, through shrine meditation, and it is capped at
  30. *(Established, with this scope: the negative covers every direct reference
  to the dexterity field across the shipped executable, all of its overlays and
  all four display drivers, including indexed and negative-displacement forms,
  and every site that takes the field's address was opened individually - each
  is a dexterity-versus-roll saving throw whose only write is to the character's
  condition letter. A write reaching the field through a pointer built from an
  unrelated base would still fall outside the scan.)*

**The base step is written once.** A party actor's base step is written at
seating and is not touched again for the life of the encounter. The only writers
of that field anywhere in the shipped game are the encounter-setup table wipe
(which zeroes it), the two seeding arms of the placement primitive, and the
slot-clear that runs when an actor is removed from the arena. The round loop
only reads it. The party-seeding mode of the placement primitive has exactly one
caller in the whole game - the encounter-setup routine - which is what makes
"written once at seating, never again" safe to build on; every other caller
anywhere, including the mid-combat spawns from spell handlers and the Gazer's
death effect, uses the monster mode or the marker mode. *(Established, with this
residual scope: the writer census is exhaustive by construction over the shipped
executable, all twenty-three overlays and all four display drivers for direct
byte writes and for every occurrence of a literal inside the descriptor table's
address span, and the exclusivity census covers every direct near call plus an
exhaustive far-call scan. Still outside it: a write through a descriptor pointer
received as a function argument or built from a literal outside the table's
span, an indirect call through a pointer table reaching such a writer, and the
near-call negative over the four display drivers, which have no established load
base.)*

Two field-level details that do not change the model:

- An area-effect spell handler temporarily sets the top bit of the **phase
  counter** as an "already affected by this cast" marker, so one cast cannot hit
  the same actor twice. It clears that bit on all thirty-two actor slots before
  returning, through its single exit, and the round loop never observes the
  marker. An engine may therefore model the phase counter as a plain value in
  the 6-to-36 range.
- The speed floor of one that applies to time-stopped actors, to asleep or
  disabled actors, and to one particular actor class feeds only the to-hit score
  (Section 11). Turn order reads the unmodified base step, so that floor never
  affects initiative.

### 5.2 The monster speed variation reverts; it does not clamp

Each ordinary monster placement takes one uniform draw in `[0, 7]`, subtracts 4
to give an offset in `[-4, +3]`, and adds that to the class's shipped speed
rating in eight-bit arithmetic. If the result **exceeds 30**, the engine reverts
to the class's unmodified speed rating - it does not clamp to the boundary.
Because that test is an unsigned above-30 test, two behaviours follow and both
are worth building deliberately:

- A class already at the 30 maximum keeps 30 whenever the variation would push
  it above 30. Its reachable base steps are 26, 27, 28 and 29 at one chance in
  eight each, and 30 at four chances in eight - phase counters of 10, 9, 8, 7
  and 6, with 6 at even odds. *(These distribution figures are for a class whose
  shipped speed rating is 30. The general rule - uniform `[-4, +3]`, revert to
  the shipped rating when the result exceeds 30 - holds for every class.)*
- A very slow class is protected from wrapping below zero by the same revert,
  because an eight-bit underflow also fails the unsigned test.

Turn order is a consequence of these numbers rather than of any separate
initiative roll: the round loop walks the thirty-two actor slots in index order,
decrements every eligible actor's phase counter once per sweep, and lets an
actor act when its counter reaches zero. A larger phase counter is a longer
wait, so higher dexterity means acting more often. Ties within a sweep resolve
in slot order, and because the placement primitive seats party actors into the
low descriptor slots and monsters into the slots above them, **the party's slots
always resolve ahead of the monsters' in a tie**.

### 5.3 PRNG consumers at combat entry, in order

**Is combat-entry PRNG order exactly "clear tables, seat party with no draws,
banner, count roll, one speed-variation draw per monster placement"?** The
*ordering* is correct. The *draw accounting* is not: three of the steps can
draw, one of them without any bound, and there is an additional world tick
nobody had accounted for.

**Confidence and scope.** The ordering, the placement gates, the shuffle count,
the sentinel set, the count-roll nesting and the cap are established at
instruction level for the terrain and town entry chain, and the seating rules
and the round-loop prologue are established for every entry that reaches the
shared seating routine. **The draw counts of all three world ticks in this
window are undetermined and need live capture** - they are marked below and no
maximum is published for any of them. The dungeon in-room and dungeon
wandering-monster variants were traced far enough to establish which route seats
the party, that each reaches setup with a source band the dungeon room painter
has already permuted by its own sixteen-swap (Section 5), and that neither
alters base step or phase; they were not traced end to end, and the deterministic room-painter
vector published earlier in this section is not re-derived here.

| # | Step | Draws |
|---:|---|---|
| 1 | Combat framer entry through to the setup routine | None. |
| 2 | Clear both combat tables | None. |
| 3 | Seat the party | **Variable; not draw-bounded in general.** Free with the shipped starting roster. |
| 3a | Placement-slot shuffle (**surface camp ambush only**) | The terrain setup helper has exactly two callers (Section 5). The ordinary wilderness or town encounter leaves the shuffle bit clear and draws **zero** here. The surface camp ambush sets and forwards the bit, and draws exactly fifteen uniform `[0, 15]` draws, taken after seating and before the banner; on that route step 3 is skipped entirely, so the shuffle is the first drawing step there. **This row does not cover the dungeon entries.** Their permutation is a different mechanism on a different array - the dungeon room painter's own sixteen-swap over the source band, run before the framer is entered (Section 5; `dungeon-mode.md` Section 14.1) - and it is outside this table's terrain/town scope. |
| 4 | Conflict banner (Section 4.1) | None. |
| 5 | Monster count | Zero, one, or two. |
| 6 | World tick, on the same branch that rolled a count | **Variable and unbounded. Needs live capture.** |
| 7 | Monster placement | One or two draws per monster. |
| 8 | Round-loop entry prologue, before any actor slot is examined | **One world tick: variable and unbounded. Needs live capture.** |

The group-name banner and the arena-record selection both happen in the
world-side entry step, before the framer is entered, so neither appears in this
table; see Section 4.1 and `systems/encounters.md` Section 4. Neither consumes a
draw either, so the ordering above is unaffected.

Nothing between entering the combat framer and the setup routine consumes a
draw, and nothing between the setup routine returning and entry into the round
loop consumes one.

**Step 3, seating.** Party slots are walked in roster order. Per slot:

1. A dead member is skipped outright - no draw and no seat.
2. The ring vanish check runs **before** the member is placed: one uniform draw
   in `[0, 15]` if the member wears the Ring of Invisibility or the Ring of
   Regeneration, destroying the ring on the single outcome `11`.
3. The member is placed.
4. The ring-effect step runs, gated on status exactly `'G'` or `'P'`, and its
   regeneration arm sweeps the **whole party**, drawing one uniform `[0, 7]` for
   every member alive and wearing the regeneration ring at that moment.
5. A member whose status is `'S'` (asleep) takes a branch that runs a **full
   world tick**, itself a variable consumer - so seating is not draw-bounded at
   all whenever anyone in the party is asleep.

Seating's cost therefore has **no closed form**, for two independent reasons: a
vanish destroys the ring before every later count in the same pass, and the
population that *triggers* a regeneration sweep (good or poisoned wearers) is
not the population *counted inside* one (all living wearers). **Any closed-form
ring cost - in particular "one draw per wearer plus the square of the wearer
count" - is withdrawn. Implement the two rules and the ordering, not a
formula.** With the shipped starting roster none of it fires: no starting
character carries either ring value and all start in good condition, so seating
is genuinely draw-free in the default case.

**Step 5, the monster count.** The count is rolled only when the class's spawn
count rating is not one of the three exact-count sentinels 1, 8 and 16. When it
is rolled it is one uniform draw in `[1, rating]`; and when the early-game
damper flag is set, a second uniform draw in `[1, result of the first]`
immediately follows, taking the first result as its new upper bound. The result
is capped at 26. Sentinel ratings consume nothing here.

**Step 6, the mid-setup world tick.** The same non-sentinel branch that rolls a
count runs a **full world tick before any monster is placed**. That tick is a
variable PRNG consumer with three distinct drawing arms, and they draw **in
this order**:

1. The **active-object animation pass**, which draws from three separate points
   inside its per-record loop.
2. The **autonomous wind-drift roll**.
3. The **viewport composite** - which runs unless the pending command is the
   Talk command - and which takes one uniform `[0, 3]` draw **only** for a
   composited actor standing on one of the five selecting terrain rows of
   `systems/visibility.md` Section 8, and **zero** otherwise.

Arena terrain almost never carries a selecting row: outdoor arenas contain none
of the furniture terrains at all, and across every dungeon arena there are four
manacle cells, one mirror cell and exactly one selecting chair
(`systems/visibility.md` Section 8.4). So in ordinary combat entry the
composite arm contributes **nothing**. At that moment the object table has just
been wiped and repopulated with the seated party, so the animation pass has
that many records to walk; its per-record draw count is record-dependent and is
not characterised here. **The total could not be pinned statically** - it
depends on the redraw gate, the first-tick flag, the party size, and which arm
of the animation dispatch each record takes - so it is a measured quantity, not
a modelled one.

*Retracted:* an earlier revision of this paragraph listed the three arms in the
reverse order (wind first, then the animation pass, then the visibility pass),
said the visibility pass "takes a further uniform `[0, 3]` draw" as though it
drew on every tick, and said that every seated party member "qualifies for at
least one animation draw". The order is animator, wind, composite; the
composite draws only on a selecting terrain row, which arena terrain almost
never is; and the animator's per-record count is not established. See
`RETRACTIONS.md` R329 and R331.

**Step 7, placement.** Placement is not uniformly one draw each. The **first**
monster is placed with exactly one speed-variation draw and never gets a
companion draw. Each subsequent monster whose spawn index is below
`count / 4 + 1` is preceded by one additional uniform `[0, 8]` draw that
substitutes the class's companion species on a zero result; the remaining
monsters take only the speed draw.

**Step 8, the round loop's entry prologue.** The combat round loop's entry
prologue runs a **second world tick, as its very first action, before any actor
slot is examined**. It runs once per entry into the loop, the loop is entered
once per encounter, and the sweep restart jumps past the prologue - so exactly
one extra world tick sits between the last monster placement and the first
actor's action. At that point the object table holds the party *and* every
placed monster, so this tick has strictly more qualifying records than the
mid-setup one and its count is at least as undetermined. The prologue's other
calls draw nothing, directly or transitively.

**Do not publish or assume a maximum for any of the three world ticks.** The
autonomous wind-drift roll draws once in the common case; on an uncommon result
it enters a retry loop taking **one further draw at a time**, so its draw count
per invocation is one, two, three, and so on upward. **No maximum is published,
and an engine must not assume one** - the loop has no static bound, 63
invocations in 64 stop at a single draw, each extra iteration continues at
roughly `0.15`, and its expected value has not been measured. This is the same
contract, in the same words, as `systems/prng.md` Section 4 and
`systems/visibility.md` Section 8.4.

*Retracted:* an earlier revision of this paragraph said the retry loop "draws
in pairs until it settles, so its draw count per invocation is one, two, or an
unbounded sequence above that", and instructed the reader **not** to restate
the count as "any integer from one upward". The retries are single draws and
every integer from one upward *is* reachable, so that instruction was exactly
backwards. A world tick's draw count is also larger than this paragraph implies
for a second reason: the autonomous wind-drift roll is not the tick's only
consumer, and `systems/prng.md` Section 4 now lists all three in order. See
`RETRACTIONS.md`.

**A clean lever for a black-box harness.** A class whose shipped spawn-count
rating is one of the sentinels 1, 8 or 16 skips both the count roll and the
mid-setup world tick entirely, leaving only the placement draws before the
prologue tick. The bat's shipped spawn rating is 16, so a bat encounter isolates
the prologue tick cleanly.

One consumer outside this window, for completeness: the turn-clock advance run
after combat ends is itself a draw consumer, sitting between the encounter and
the next outdoor turn.

### 5.4 Placement performs no terrain validation

**Does initial monster placement validate arena terrain, re-roll, or skip?** It
does none of the three, on every placement path. *(Established for terrain
combat setup and its actor placer, read end to end with their complete callee
sets enumerated, plus dungeon-room setup. Shipped-data claims below are from a
full parse of both combat-arena files - 16 outdoor records and 112 dungeon
records.)*

For an outdoor encounter the monster placement coordinates are read verbatim
from the selected arena record's metadata - sixteen X values and sixteen Y
values - and handed straight to the actor placer, one per spawned monster. The
setup routine never reads the arena terrain grid, never consults the
cell-occupancy predicate, and never re-rolls a coordinate. The actor placer
likewise reads no terrain; its only helper call is the per-actor speed roll. The
dungeon-room path is the same: it walks the sixteen source entries in the room
record, skips entries whose source byte is zero, and places everything else at
the stored coordinates with no terrain test.

**Placement onto impassable cells is authored, not accidental.** The water arena
- the one selected when the party is on land and the hostile is standing on
water, shoals or deep water, arena 15 in `encounters.md` Section 4 - is authored
with **all sixteen** monster placement cells on water tiles and all six party
seats on grass and brush. A land-class monster fought over water is therefore
placed on water by design. The aboard-ship counterpart, arena 11 (party aboard
ship, hostile on water), likewise puts all sixteen monster cells on deep water
or water; the ship-versus-ship boarding arena 14 puts them on the enemy deck
instead (corrected 2026-09-03, R351 - an earlier revision of the sibling
sentence in `encounters.md` named arena 14 as the all-water one). This is deliberate
original behaviour and a port should reproduce it; what happens to such an actor
afterwards is specified in Section 7.1, and the short answer is that it acts
normally and simply cannot move.

**In-combat spawn effects are the exception.** The conjure, swarm and summon
spells each probe a random arena cell against the cell predicate and place only
on an accepted cell. That validation belongs to those spells, not to encounter
placement, and it must not be generalised back onto placement.

## 6. The actor table

Combat treats every actor — every party member, every monster, every summoned creature, every dynamic object that exists during the fight — as a slot in a fixed-size **actor table** of thirty-two slots. The first six slots are reserved for party members 0–5 (heroes, in party-roster order); the rest are used for monsters, summons, and any divisions or replications produced during the fight.

Each slot is a compact combat descriptor. At semantic level it carries:

- **HP/wound counter.** Combat-local health or wound state for this actor.
- **Base-step.** The speed input used to refresh the actor's phase counter.
  Higher base-step values produce shorter refreshed countdowns, so they act
  sooner after randomization and clamping.
- **Phase counter**, decremented each round; the actor acts when it reaches zero.
- **Flags/faction byte** describing party, hostile, or passive/neutral faction and per-turn state such as alive, marked dead, controlled/charmed, fleeing, hidden/not-yet-revealed, and asleep/magically disabled. Section 6.1 gives the exact bit layout; the low bit is the controlled/charmed state, not a "casting" state.
- **Owner/target/class byte.** Overloaded by caller: party slots use it to link
  to a character record, while monster and object slots use it for placement,
  target selection, and class-table lookup.
- **Active-object back-reference.** The matching slot in the renderer-facing
  active-object table.
- **The actor's (X, Y) coordinates** on the eleven-by-eleven arena.

The decoded row order is HP/wound counter, base-step, flags/faction,
owner/target/class, active-object back-reference, phase counter, arena X, and
arena Y. The owner/target/class field is deliberately overloaded by caller: it
links party slots to character records, supports monster target selection, and
selects class-table rows for monster/object slots.

### 6.1 Flags/faction byte bit layout

The flags/faction byte (byte 2 of the eight-byte descriptor) carries the
per-slot per-round state used by every consumer:

| Bit  | Meaning                                                                              |
|-----:|--------------------------------------------------------------------------------------|
| `0x80` | **Party-side slot.** Placement stamps this bit only when it writes a party member's descriptor. Monster and object descriptors never carry it. It is the discriminator the damage/death resolver uses to choose the party-death branch over the monster-death branch, so an engine that also sets it for live monsters routes every monster death through the party path. |
| `0x40` | **Monster-side slot** (self-acting AI actor). Placement stamps this bit when it writes an ordinary monster descriptor, except for the two passive/neutral classes 8 (Pirate) and 9 (the adjacent reserved row), which are stamped `0x20` instead. Bits `0x80` and `0x40` are mutually exclusive as written by placement. |
| `0x20` | Marked dead or otherwise non-acting. Monster death overwrites the whole flags byte with this value; party death ORs it in. |
| `0x10` | Phase/blink filter (bypassed on scene `'('` `0x28` and on monster type `'/'` `0x2F`). |
| `0x08` | **Asleep / magically disabled.** Not charm: charm and every other externally-controlled state live in bit `0x01` alone, and no traced path writes `0x08` for a charm or possession effect. Combat sleep for non-party targets stores into this bit; party sleep uses the character status byte `'S'` instead. Party placement also pre-sets this bit when the character's roster status byte at placement time is neither `'G'` (good) nor `'P'` (poisoned). The stats panel's combat status letter does not consult this bit, so an asleep party member still shows the roster status letter. |
| `0x04` | Hidden / not-yet-revealed (invisible).                                            |
| `0x02` | Fleeing. Set by the wound-morale writer, by the no-target centre fallback, and directly by the Cause Fear and Repel Undead sweeps (Section 9); consumed by the step-vector synthesizer. |
| `0x01` | **Charmed / under external control.** Set by monster possession, by the Charm spell, by summon/conjure placement, and by the Sword of Chaos compulsion path; see Section 6.1a for the full writer/reader contract. It is *not* a dispatch gate for the round walker. |

A descriptor whose flags byte is entirely zero is a free slot. Placement uses
exactly that test when it looks for somewhere to write a new actor, so an
engine must not leave residual bits on a released slot.

### 6.1a The controlled/charmed bit

Bit `0x01` records that an actor is acting under external control rather than
its own volition. Four traced paths set it and one clears it; nothing decays it
on a timer.

**Writers.**

1. **Monster possession** (the per-class possess ability, Section 9) sets the
   bit on the accepted *target*.
2. **The Charm spell** toggles the bit on its accepted target: casting Charm on
   an actor that already carries it clears it. This is the only traced clear
   short of the actor leaving the table. When the accepted target is a
   party-side slot, Charm also writes the Good status letter into that
   character's roster status byte and refreshes the stats panel — in both
   toggle directions, so Charm on a Sleeping or Poisoned party member restores
   the roster status letter to Good as a side effect. The spell prints its own
   charmed line and suppresses the dispatcher's success/failure epilogue.
3. **Conjure and Swarm placement** set the bit on each freshly placed creature,
   and **Summon** sets it on its placed Daemon whenever its caster self-check
   succeeds, so a freshly summoned creature normally starts life in the same
   controlled state a charmed monster is in. Summon's rebound branch is the one
   exception: it leaves the Daemon on the arena with the bit clear. They are still placed through the ordinary monster
   placement path, so their class byte is the monster-side one - but the bit
   **does** hand the creature to the player's prompt: a monster-side slot
   carrying it is dispatched to the keystroke/command path, not to the automatic
   driver, and it takes its turns under player control with the reduced turn
   banner of Section 8.1. Because the bit is also the group helper's team
   toggle, a stamped creature groups with the party rather than with the
   monsters for the same-faction filter (see the dispatch and grouping
   paragraphs below). *(**Corrected.** This writer previously read "monster AI
   drives their turns — the bit never hands a creature to the player's prompt".
   **That is withdrawn**, and it contradicted this section's own dispatch
   paragraph below, which already said a monster carrying the bit lands in the
   party's group. The slot-to-group helper described below - one read of this
   bit, also referred to in this document as the self-acting test - reports
   "self-acting" for a monster-side slot exactly when this bit is **clear**, and
   a not-self-acting result routes to the command handler. See `RETRACTIONS.md` R354 and Section 11.1.)* See `systems/magic.md`, Summoning and conjuration. The
   monster AI's own summon-daemon ability does *not* set this bit (Section 9).
4. **The Sword of Chaos compulsion.** The command-path handler (Section 8)
   takes its player-driven branch for a slot when the active-player sentinel is
   unset, or when the slot is party-side and its owner/character byte equals the
   sentinel. That sentinel test lives inside the handler, not in the round
   walker, which selects between the two handlers through the slot-to-group
   helper described below. On the player-driven branch,
   if the slot is party-side and its character has item id 35 (Sword of Chaos)
   readied in either the weapon-hand
   or shield-hand slot, the engine sets this bit on that party descriptor,
   clears the active-player sentinel, and runs the turn through the automatic
   actor driver instead of reading a command from the player. Any other readied
   equipment takes the ordinary interactive path and never sets the bit.

**Readers.** Three paths consume the bit directly, and a fourth — the
slot-to-group helper — reads it as the combat team toggle, which is what puts it
in the round walker's dispatch decision and in the friendly-fire filter (see the
dispatch paragraph below and Section 9). The three direct consumers are:

- **The attack driver.** When an actor whose bit `0x01` is set takes an attack
  action, the attack resolves as a fixed magic strike instead of running the
  ordinary weapon cascade. The driver still picks a target the normal way, and
  then applies one extra requirement that has no counterpart on the ordinary
  path: the chosen target must be at straight-line distance exactly one — that
  is, one of the eight cells surrounding the actor, diagonals included, since
  the distance function truncates. If the target is further away the actor's
  turn produces **no action at all**: the driver does not fall through to the
  ranged branch, does not consult the class's maximum-attack-range byte, and
  does not step. When the target is adjacent, the renderer's action-tile marker
  is set to the fixed magic-strike id and the strike is resolved by the shared
  attack-application primitive, which plays the hit sound, runs the ordinary
  to-hit roll and damage feeder with that same fixed id as the attack flavour,
  and narrates hit or miss. The pre-attack animation, the attacker back-link,
  the class-specific attack overrides and the monster ranged-spell branch are
  all skipped. This is the bit's only gameplay consumption inside attack
  resolution.
- **The possession eligibility filter,** which rejects a target that already
  carries the bit, so a controlled actor cannot be possessed a second time.
- **The stats panel.** A party member whose combat descriptor is party-side,
  not monster-side, not marked dead, and carries bit `0x01` is drawn with the
  status letter `C` in place of the roster status letter, for as long as that
  descriptor still points back at the same roster slot.

**A dispatch input.** The round walker does not read this bit directly, but the
slot-to-group helper it dispatches on does: for a party-side slot the helper
returns bit `0x01` itself (subject to the traitor-roster override of Section 9),
and for a monster-side slot it returns that bit inverted. The walker sends the
group ordinarily occupied by seated party members to the keystroke/command path
(Section 8) and the other group to the automatic actor driver (Section 9). A
party-side actor carrying this bit therefore takes its turns through the
automatic driver instead of the player's prompt — which is exactly the Sword of
Chaos behaviour described above — while a monster carrying it lands in the
party's group. Two earlier readings are withdrawn: that the walker dispatched
any slot with the bit set through the *player* command parser (the routing is
the other way round for party-side slots), and that the walker never consults
the bit at all and picks the player path from the active-player sentinel (that
sentinel test is real but lives one level down, inside the command-path handler
itself). A possessed party member still keeps its place in slot order, still
draws the `C` status letter, and still uses the redirected attack branch.

**Sleep is a different bit.** Bit `0x08` is the asleep/magically-disabled
state and has nothing to do with charm, possession, or any other external
control. Nothing in the engine writes `0x08` for a charm or possess effect, and
nothing reads it when deciding whether an actor is controlled. An implementer
that stores the charmed state in `0x08` will skip the controlled actor's turn
instead of redirecting its attack, and will never draw the `C` status letter:
the panel's test is "party-side set, monster-side clear, dead clear,
controlled `0x01` set", and `0x08` is not part of it.

**The class bits are not the toggle.** The slot-to-group helper reads the
party-class bit `0x80` only to choose which rule applies, and then keys on bit
`0x01` as the team toggle, so this bit — not `0x80` — is what moves an actor
between combat groups for the friendly-fire filter and the walker's dispatch.
Do not reuse `0x80` as a faction toggle. The separate team resolver used on the
target picker's special pre-combat-scene branch (Section 9) reads only
**descriptor** bytes plus one roster byte.

> *Corrected (2026-08-23).* Earlier revisions described class-flag bit `0x0080` as a **team / faction override** consulted by target selection. **That is withdrawn.** An exhaustive scan of every shipped code file for accesses to the per-class flag table finds exactly one instruction anywhere that tests this bit, and it is inside the shared stat-selector helper. It fires only when that helper is handed a monster slot **together with a selector value of exactly zero**, and its entire effect is to change which byte of the class stat row the helper returns for that zero selector: the row's first byte instead of a value from the combat-weight helper. The helper computes no side, writes nothing outside its own frame, and returns a single byte its callers use as a scalar threshold.
>
> The confusion had a specific cause worth recording: the real friend/foe resolver also tests a bit called `0x80`, but that is a bit of the **per-actor combat descriptor**, a different byte in a different binary from the per-class flag word. The resolver never reads the class-flag table at all - the table's address does not occur anywhere in the resident image.
>
> Scope of the re-derivation: the negative ("no other site tests this bit") is bounded to accesses that name the table by a literal displacement; an access through a base register loaded arithmetically would not appear. The other bits of the flag word were classified only by their test masks, not re-read.
>
> The same correction removes a second error from this paragraph: the resolver's
> first test is descriptor bit `0x20`, not bit `0x40`. Read whole, it returns
> "no side" when that bit is set; otherwise, for a party-linked descriptor, it
> returns the hostile side when the linked roster record is the shipped traitor
> template and the descriptor's link byte is non-zero, and otherwise the
> descriptor's low bit; for a non-party descriptor it returns the inverse of
> that low bit.

**Lifetime.** The bit lives only in the combat-instance descriptor table. It
survives rounds, is cleared by a second successful Charm, by the slot-clear path
when the actor dies or de-spawns, and by the wholesale descriptor-table reset
performed on the next combat entry. Nothing writes it into the save image.

### 6.2 Active-object link (byte 4)

Byte 4 of the descriptor is the renderer-facing active-object back-reference.
An earlier revision of this document called byte 4 the status sub-flags byte
and put the non-party asleep/charmed/disabled bit in it; that is retracted, and
that bit is byte 2. Using byte 4 as a bitfield collides with ordinary
active-object slot ids.
It is an index into the temporary combat-instance active-object table, not a
status flag byte. Death-marker writers, movement synchronization, and loot/drop
presentation all use this byte to locate the active-object record that mirrors
the combat descriptor.

Do not store sleep, charm, casting, or other status bits in byte 4. Every
per-slot status bit lives in byte 2 of that slot's eight-byte combat
descriptor: the asleep/magically-disabled flag is byte 2 bit `0x08`, and the
controlled/charmed flag is the separate byte 2 bit `0x01` described in
Section 6.1a. Those two are different states with different writers, different
readers, and different in-game effects; do not merge them. Using byte 4 as a
bitfield will collide with ordinary active-object slot ids.

The combat sleep/disabled bit has no traced per-slot duration counter. Player
Sleep, Sleep Field contact, and any other combat path that marks a non-party
actor asleep set descriptor byte 2 bit `0x08`; they do not seed a separate
per-slot countdown for that descriptor state.

Wake timing is owned by the acting slot's dispatch. When a slot whose descriptor
still has bit `0x08` set reaches its own action dispatch, the driver rolls a
uniform inclusive `0..16` value. Any result other than `16` consumes that
dispatch and leaves the bit set. On result `16`, the wake helper clears bit
`0x08`, refreshes the linked presentation/status state, and still returns
without continuing into the normal action parser or monster action path. The
actor becomes eligible for later predicates after the bit is cleared, but the
dispatch that performed the wake check is spent.

While bit `0x08` remains set, the actor remains present in the descriptor table
and still occupies its arena cell; the bit does not imply death, slot removal,
or loss of the active-object link. Consumers that explicitly reject asleep or
disabled actors, such as the action dispatcher and combat spell prerequisite
gate, continue to reject it until the own-turn wake helper clears the bit.

### 6.3 Death-marker tile bytes

When a slot dies, the death resolver may write a tile byte into the
combat-instance active-object record at the slot linked from descriptor byte 4.
Not every death branch writes a marker, and the branches that do not write one
are exactly the branches that release the slot.

Three inputs decide the branch:

- whether the descriptor's flags byte carries the party-side bit (§ 6.1);
- the dying class's sixteen-bit class-flag word, specifically its low bit
  (call it the *incorporeal* bit) and its *vanish-on-death* bit;
- for ordinary monsters only, the arena terrain byte under the dying actor and
  two independent rolls against the class's drop-cap stat byte.

The branch order is: party-side bit first; then the pair test "incorporeal bit
or vanish bit set"; inside that pair, vanish wins over incorporeal; outside it,
the two hand-written class exceptions (Gazer, then Gargoyle) win over the
general terrain/drop path.

| Death branch | Selected when | Tile byte written into active-object bytes 0 and 1 | Other writes | Slot released? |
|---|---|---|---|---|
| Party member | Descriptor carries the party-side bit and the damage meets or exceeds current HP, or the damage is the instant-kill sentinel `99` | `0x1E` (corpse) | Character HP forced to zero, roster status byte set to `'D'`, marked-dead bit ORed in, death audio played, active-player sentinel set to `0xFF` if the dead character was active | No |
| Vanish-on-death class | Monster whose class-flag word has the vanish bit set — Wanderer, Blackthorn, Lord British, Shadow Lord | `0x16` (temporary vanish marker) | Prints `<name> vanishes!`, sets shared action-result bit `0x02`, restores the underlying terrain through the single-cell pixel reveal, releases the slot, then runs the party control/faint scan described below | **Yes** |
| Incorporeal class | Monster whose class-flag word has the low bit set but **not** the vanish bit — Sea Horse, Squid, Sea Serpent, Shark, Bat, Ghost, Slime, Insect Swarm, Wisp, Daemon | **none** | none | **Yes** |
| Gazer | Monster of the Gazer class | `0x1F` (eye-burst special) | **Places a live Insect Swarm combatant (class 31) at the death coordinate** through the ordinary monster-placement primitive, then redraws the arena. See "The Gazer death spawns a real combatant" below | No |
| Gargoyle | Monster of the Gargoyle class | **none** | Writes `0x4C` (lava pool) into the combat-arena **terrain** cell under the actor; that terrain edit persists for the rest of the combat instance | **Yes** |
| Ordinary monster, terrain rejects | Any other monster whose underlying arena terrain byte is `0x87`, or is numerically below `4` | **none** | none | **Yes** |
| Ordinary monster, drop roll rejected | Terrain accepted, and the first roll exceeds the class drop-cap byte | `0x1F` | none — byte 5 keeps whatever the per-encounter reset left there | No |
| Ordinary monster, drop roll accepted | Terrain accepted, and the first roll is less than or equal to the class drop-cap byte | `0x01` (dead-monster / drop marker) | Byte 5 of the active-object record receives **the class drop-cap byte itself**. A second independent roll strictly below the same drop cap ORs bit `0x80` into byte 5 as the special-drop marker | No |

#### Vanish ordering and the shared result field

The vanish branch has this exact order:

1. Print the monster's name and then the ` vanishes!` suffix.
2. Replace the shared combat action-result/narration field with `0x02`.
3. Put `0x16` into both tile bytes of the actor's linked active-object record.
4. Reveal the underlying arena-terrain tile into that viewport cell as defined
   below. The marker remains in the active-object record throughout the reveal.
5. Release the combat descriptor and its linked active-object record. This
   erases the marker after the terrain reveal has completed.
6. Run the party control/faint scan below, ignore its return value, and return
   from death resolution.

The field in step 2 is **global action-result scratch**, not a field in the
dying actor's descriptor and not a persistent vanish status. Bit `0x02` means
that branch-specific narration has already been printed. The common attack
result narrator is its only relevant bit reader. It first clears the field's
kill-narrated bit `0x01`; when `0x02` is still present, the combined suppression
test skips the generic killed/slept/hit chain, produces no message or sound,
and clears `0x02` in cleanup. If that narrator is not reached, the combat walker
replaces the whole field with zero before the next actor dispatch. The automatic
actor driver reads the same byte's unrelated cancelled-step bit but does not
read `0x02`.

This scratch byte happens to lie inside the fixed saved-game image and is
therefore serialized mechanically. That storage fact does not extend its
behavioral lifetime: combat cannot be saved and resumed, and the next actor
dispatch resets it before use. A loader must not reconstruct a pending vanish
from a saved value.

There is one original ordering collision. If the control/faint scan finds a
party member and sleep succeeds, the sleep helper replaces the whole result
field with sleep bit `0x04`, losing `0x02`. On the ordinary successful-attack
path, the attack's existing impact cue and separating newline occur before
damage resolution, hence before the vanish line and faint tail. The later
common narrator has already cached the vanished target's released descriptor
state. Its dead/passive test precedes its sleep test, so it appends the vanished
target's `<name> killed!` line—not `<name> slept!`—after the faint tail and
plays no additional sound. It sets kill-narrated bit `0x01`, clears the
transient sleep bit, and leaves `0x01` until the combat walker zeroes the whole
field before the next actor dispatch.

If the scan finds no party member, `0x02` survives and suppresses the duplicate.
The same suppression survives when a matching member is already Dead: that
case still prints the faint line, plays its envelope, and removes the Sword of
Chaos, but the sleep helper returns without replacing the result field. Do not
preserve both `0x02` and `0x04` across the successful-sleep overwrite when
reproducing baseline behavior.

#### Single-cell terrain reveal

The vanish visual is **not a palette fade** and has no page-flip or buffered
frame sequence. It copies the prepared pixels of the arena terrain tile that
was under the dying actor into the corresponding 16-by-16 cell on the visible
viewport page, one pixel per display-driver operation. Direct visible-page
writes make each completed pixel operation observable without a later flush.

The reveal always performs 256 pixel operations. In the EGA baseline, the
first paints the cell's top-left pixel. The other 255 follow an eight-bit
maximal-length shift-register sequence: start at one; interpret the high
nibble as X and the low nibble as Y; after each pixel, shift right and, when
the discarded low bit was one, exclusive-OR the state with `0xB8`. This visits
every nonzero `(X,Y)` pair exactly once, so together with the first operation
every pixel in the cell is written once in pseudo-random order.

After every eighth completed operation except the last — after counts 8, 16,
through 248 — the reveal runs one world tick. There are exactly 31 such ticks,
no fixed-delay call, and no checkpoint after pixel 256. The combat branch does
not test input or the tick's return value, so the operation is blocking and
unskippable and always completes all 256 writes. Its cadence is therefore the
cost of 256 driver operations plus 31 world ticks, not a separately timed
animation. The pixel-order claim is the EGA compatibility baseline; other
original display-driver pixel packing is not specified here.

#### Party control/faint tail — not a flush

The call after slot release is a gameplay scan, not a post-turn flush, redraw,
clock advance, or visibility barrier. It examines party combat slots zero
through five in order and stops at the first descriptor carrying both the
party-side and controlled/charmed bits. For that first match it performs these
mutations in order:

1. Clear the controlled/charmed bit.
2. Print the linked character's name followed by ` passes out!`.
3. Play the controlled-party faint envelope specified below.
4. Remove the first Sword of Chaos (item 35) found among that character's six
   equipment bytes, replacing it with the ordinary empty-equipment sentinel.
5. Apply the normal sleep-state helper to that combat slot.

The faint sound is exactly the software envelope also used by monster
possession success: phase period 3100, initial comparison 1000, comparison
delta `+2`, 30,000 iterations, and idle count 1. The 16-bit phase accumulator
starts at zero and advances by 3100 modulo 65,536 each iteration; comparison
starts at 1000 and advances by two. A fixed divisor-60 carrier is connected
only while phase is strictly greater than comparison. Thus the carrier pitch
is fixed (about 19.9 kHz), while the roughly 1.1 kHz gate and its changing duty
cycle form the audible swell-and-decay contour. The envelope blocks until all
30,000 iterations finish, then forces silence. With sound disabled, it still
runs the complete phase/comparison recurrence and remains blocking, but omits
speaker I/O and completes faster: about 999 ms rather than about 1.29 seconds
under the calibrated baseline. `audio.md` Sections 5.4 and 10.3 define the
shared envelope more fully.

The sleep helper does nothing further when the linked roster status is already
Dead; the control clear, faint narration, sound, and item removal have already
happened by then. Otherwise it changes the roster status to Sleeping, sets the
descriptor's asleep/disabled bit, switches the linked object's displayed byte
to the prone presentation, clears the active-player selection if it names that
slot, replaces the whole shared result field with sleep bit `0x04`, and redraws
the full stats panel. It then runs exactly one blocking world tick unless the
combat-entry cache carries the rest/camp alternate-entry bit `0x04`. Entry
modes 4 and 6 set that guard bit and skip the tick; ordinary terrain combat and
dungeon ambush/wandering combat leave it clear and take the tick. The sleep
helper itself plays no sound.

The scan returns the matched slot, including five for the last party slot, but
the vanish caller ignores it. With no match it returns the no-match sentinel
and performs none of these effects.

There is no full-arena redraw after the vanished actor's records are released.
The guaranteed visible state comes from the earlier direct reveal: all 256
pixels of the cell already show the underlying terrain before record cleanup.
A matched faint may additionally redraw the stats panel and run its conditional
world tick, but those are faint-state consequences, not a vanish flush.

*Corrected (2026-08-27).* Earlier text called the visual a terrain fade and
the final call a post-turn flush, and treated value `2` as an unspecified
per-combat status byte. Those descriptions are withdrawn; the contracts above
identify the pixel reveal, shared action-result bit, and mutating party scan.

Notes that an implementation must not get wrong:

- **Byte 5 is the drop-cap value, not a random amount.** The random draw is only
  the gate comparand; the stored value is the class's drop-cap stat byte. This
  matches `catalogs/monster-bestiary.md` Section 1, which is the authoritative
  wording for the drop-cap field.
- **The accepted-drop marker is a chest object, and its byte-5 high bit is the
  ordinary lock/trap flag.** The marker values in this table are ids in the
  shared searchable-object class space, the same space the Search/Get narration
  uses: `0x01` is a **chest**, `0x1E` a rotting body, `0x1F` a moldy corpse.
  So the accepted drop branch leaves a chest object standing on the dead
  monster's cell, and the high bit of that record's byte 5 is the same
  lock/trap flag the Jimmy and Search command family reads (its low seven bits
  carry the contents/difficulty value). That is why the Open spell has a real
  effect in combat: its object arm matches a chest-class object at the target
  cell and clears exactly this bit (`systems/magic.md`, Directed utility tile
  helpers). The G-Get command does not pick these records up; its accepted
  object classes are a different, narrower set.
- **Both rolls use the same helper**, which returns a near-uniform integer in
  `1..30` (the underlying draw is a uniform `0..60` halved with truncation, with
  a zero result promoted to one). Since the roll can never be zero, a class
  whose drop-cap byte is zero can never take the accepted branch. Most stock
  monster classes have a zero drop cap, so `0x1F` is by far the most common
  ordinary corpse marker in play.
- **The drop gate never releases the slot.** Neither the accepted nor the
  rejected branch calls the slot-clear helper; the marker and its descriptor
  stay in place for the rest of the combat instance.
- **Gargoyle does not fall through to the ordinary path.** After stamping the
  lava terrain byte it goes directly to the slot-clear helper, so a Gargoyle
  death produces no corpse marker and no drop.
  An earlier revision of this section routed Gargoyle death through the default
  monster-killed path and left a lava pool under a corpse; that is retracted.
- **The Gazer death spawns a real combatant, not a cosmetic effect.** After
  writing `0x1F` into its own record's bytes 0 and 1, the Gazer branch calls the
  same monster-placement primitive that per-encounter setup and dungeon-room
  setup call, in its ordinary place-a-monster mode, with class id 31 and the
  dying Gazer's arena coordinates and Z plane. That allocates a **new**
  descriptor and a **new** active-object record and seeds them exactly as any
  other monster placement would (§ 5): HP/wound counter from class 31's maximum
  HP (`5`), base-step from class 31's speed seed (`30`) with the standard
  uniform `[-4, +3]` adjustment reverted whenever the sum would exceed thirty,
  phase counter of thirty-six minus the base-step, the hostile faction tag,
  class id `31`, and active-object tile bytes `31 * 4 + 0x40 = 0xBC`. Class 31
  is the **Insect Swarm**, and `0xBC..0xBF` is
  the Insect Swarm sprite run published in `catalogs/monster-bestiary.md`.
  The engine must therefore add a live, self-acting, five-hit-point hostile
  actor to the arena when a Gazer dies; implementing a particle effect instead
  silently drops a combatant. The dead Gazer's own record keeps its `0x1F`
  marker and its slot is not released, so the marker and the new swarm coexist.
  The spawn is skipped with no other side effect when the arena has no free
  descriptor (all thirty-two allocated) or no free active-object record — the
  same allocation failure any other placement can hit. Note that class 31 is
  itself a member of the incorporeal family in the table above, so the spawned
  swarm's own death releases its slot and leaves nothing behind.
- **Monster death overwrites the flags byte** with the marked-dead value rather
  than ORing it, so all other per-round flag state on that descriptor is lost.
- The reward unit returned to the caller (`floor(max_HP / 4) + 1`) is computed
  before the branch and is returned from every monster branch, including the
  ones that leave no marker.

All death markers live in the **temporary** combat-instance active-object table.
The combat framer snapshots the world active-object table to a backup before
combat and restores it on exit, so default-kill markers do not leak as world
loot. A compatible implementation must not promote combat-instance drop markers
into automatic world loot.

When an actor dies, the "marked dead" bit is set. When the negative-form release
used by a vanishing monster or fled actor frees a slot, it zeros descriptor
bytes 0, 1, 2, 4, 5, 6, and 7 but deliberately preserves byte 3, the overloaded
owner/target/class field. It also zeros linked active-object bytes 0 through 5
while preserving that record's two trailing auxiliary bytes. The zero flags
byte makes the descriptor available for re-allocation; an all-zero record is
not required. *Corrected (2026-08-27): an earlier revision said release cleared
the record to all zeros; the preserved fields make that statement false.*

A second, parallel table — the dynamic-objects table that combat overlays onto the world's normal table — holds the same actors indexed by class for purposes the renderer cares about. The two tables are kept in sync by the movement step primitive (Section 11): when an actor moves, its (X, Y) is written into both.

The combat actor table is the authoritative combat-instance descriptor, not the persistent world active-object table. Its first byte is the current monster HP or wound counter for non-party actors, while another byte links the descriptor back to the renderer-facing active-object slot. Friend/foe classification also lives in this combat-instance descriptor: party slots are tagged as the party faction, ordinary monster slots as the hostile faction, and a passive/neutral tag is used for non-combatant combat props. The passive override is keyed by the placed actor's class id — classes eight and nine — not by the arena index. Public specs should not model the persistent active-object table as the owner of the combat faction byte.

The stats panel also reads this table during combat refreshes. Its row overlay
uses the current combat slot selector plus the selected descriptor's target or
owner field to inverse-video highlight the matching party row, and uses the
row's own descriptor to show the `C` status override, which is driven by the
controlled/charmed bit described in Section 6.1a and not by any casting state. The panel
is a read-side consumer only; combat setup, actor dispatch, spell/action
handlers, and actor cleanup own descriptor mutation.

Spell effects that create or duplicate actors allocate records in both tables.
Clone copies the accepted target's combat actor record and its linked
dynamic-object record, relinks the new combat record to the new dynamic-object
slot, and then places the copy at a random legal arena coordinate. Clone needs
one free slot in each table before it copies either record; if either table is
full, no partial clone is written. The original handler does not initialize its
spell-result word on this capacity-failure exit, so exact bug compatibility may
preserve an undefined success/failure narration result. A deterministic
reimplementation should treat that case as a no-op failure unless deliberately
emulating stack-state leakage. Clone does not try to place the copy adjacent to
the original target. The placement coordinate is accepted only after the same
combat placement probe agrees that the cell can hold the cloned actor.

## 7. Per-round structure

Each round is one walk over the thirty-two-slot actor table. The round loop has a one-time entry prologue, a per-actor body that runs zero or one times per slot, and end-of-round exit checks. When the body has visited all thirty-two slots, the round restarts (unless an exit fires).

**Loop-entry prologue.** A small bundle of housekeeping work: screen redraw,
combat-begin overlay refresh, screen flush, per-slot scratch state reset, and
clearing the "any spell cast this round" flag.

**It runs once per encounter, not once per round, and its first action draws.**
Two corrections belong here, and an engine that seeds its stream from this
section needs both. First, the prologue runs once per entry into the round loop,
and the loop is entered once per encounter: the sweep restart jumps back past
the prologue, so the bundle is *not* re-run at the top of each table walk. Any
earlier reading of this as per-round start-of-round setup is **withdrawn**.
Second, the prologue's very first action - before any actor slot is examined - is
a **full world tick**, a variable and unbounded PRNG consumer whose draw count
needs live capture (Section 5.3, step 8). The prologue's other calls draw
nothing, directly or transitively.

**Per-actor body.** For each slot 0–31:

1. **Skip empty slots and slots already marked dead.** The "alive" flag and "marked dead" flag bits gate this.
2. **Sweep deaths from prior rounds.** If the slot is alive but its linked character record's status byte is now `'D'`, mark the slot dead, fire a death-narration effect, and advance to the next slot. This catches party members who died between rounds (poison, ongoing spells).
3. **The restraint skip.** Read the arena terrain under the actor and compare it
   against exactly two tile ids - the stocks `0x84` and the manacles `0x85`. On a
   match, skip the slot entirely. This happens **before** the phase decrement in
   step 4, so a restrained actor's counter never advances and it never takes a
   turn at all. No other terrain participates: water, swamp, mountains, walls and
   force fields are all outside the test. *(**Corrected.** Earlier revisions
   called this step "skip wall-cell slots, a defensive guard against bad
   placement". That is withdrawn - it is a restraint guard, and reading it as a
   walkability guard freezes actors the original leaves acting. Section 7.1 has
   the full contract.)*
4. **Decrement the actor's phase counter.** While non-zero, the slot does not act this round. When it reaches zero, the actor *does* act.
5. **On zero, refresh the counter and act.** The counter is reset to `36 - base_step`. A round-counter at the table level is incremented and wrapped at ten; on every wrap, the engine fires a tile-render pass for animation.
6. **Dispatch the actor's turn.** A single function asks "is this slot a player or a monster?" — for a player, control passes to the player command handler (Section 8); for a monster, to the AI-then-command handler that runs the AI synthesis path before falling into the same dispatch (Section 9).
7. **Mark the slot acted, run the standing-cell hazard pass, then the post-action render.** These are two separate steps and only the second one draws. The hazard pass reads the arena terrain under the actor that just acted, and — if that terrain is not itself damaging — scans the object table for any object other than the actor's own sitting on the same cell. Three damaging kinds are recognized, each with its own effect: a low tier that applies the party status/damage path with the no-attacker sentinel and plays the hit sound, but only while the actor's own object entry is an ordinary live entry; a middle tier that plays the hit sound, rolls a small random amount, feeds it to the damage-and-status resolver, runs the shared finalize hook and raises the leave-combat flag; and a top tier that routes the actor into the same petrify-style special effect a Gazer's gaze uses. A cell with none of these kinds costs the actor nothing. Only after the hazard pass does the separate render step redraw changed cells and run any post-action sound or particle effect. Death narration runs here when relevant.

**Post-dispatch and table-terminal checks.** The loop recounts live unmarked
actors by side after a dispatched action. If no party-side actors remain while
foes do, it first gives the party control/faint helper a chance to restore one
actor; if none can be restored, it prints the one-shot defeat line when that
line has not already been guarded and returns word `1`. If neither side
remains, it returns word `0` without another announcement. If party actors
remain and foes do not, it prints `VICTORY!` once and continues; cleanup still
requires accepted actor departures or the Escape-key sweep described in
Section 14. Reaching slot 32 with actors still present starts another table
walk. The framer discards this return word, so it is not a caller-visible
victory boolean. Earlier revisions labelled `1` as victory/escape and `0` as
defeat; that polarity is withdrawn.

The renderer blink/redraw byte set by an accepted edge is not a leave-combat
flag. Edge departure ends that actor's action and the recount observes the
updated sides; it does not by itself return from combat.

**Combat does not own a post-round render pass.** An earlier revision of this
section described a "post-round maintenance pass" that swept the arena grid
"dispatching cell effects" once per round. That framing is **withdrawn**: it
misread the shared viewport rasterizer described in `systems/visibility.md` and
`systems/display-driver.md` as a combat-scoped routine. The routine in question is the
engine's single tile-painting pass, run by the idle redraw tick in *every*
mode - overworld, town, dungeon and combat alike - immediately after the
visibility post-pass composites active objects into the viewport buffers. It
walks the eleven-by-eleven viewport in row-major order and, per cell, issues one
sixteen-by-sixteen tile blit: a cleared viewport byte means "paint the byte from
the parallel companion terrain band" (one companion value is a
paint-nothing sentinel), one reserved viewport value routes to a second blit
entry point that also takes the shared magic-effect timer, and every other
viewport value is translated through the animated-tile state table before being
blitted. Every one of those calls is a display-driver blit. None of them applies
a hazard, ticks an actor, or mutates HP, status or field markers; the
"per-cell effect dispatch" reading was an artifact of the private working name,
not of the behaviour.

The only combat-specific part of that pass is its tail, which runs when the
scene byte is in the combat band. It toggles a blink flag each pass and, on the
lit pass, draws the player cursor box around the eligible active player's arena
cell, skipping the entire overlay tail when that cell is the invalid sentinel
or belongs to the non-player group. A separate flag can then draw an additional
marker at an explicit arena X/Y. That marker is not independently gated: a dark
blink pass, invalid active cell, or non-player active group suppresses both
overlays. These updates are presentation only: they do not advance combat time,
mutate actor HP or status, or consume placed field markers, and they are
distinct both from actor dispatch and from the post-dispatch field-contact hook
described later.

**Exact combat-overlay raster contract.** For either overlay cell, let its
sixteen-by-sixteen screen-cell origin be `(8 + 16*x, 8 + 16*y)`, where `(x,y)`
is the corresponding arena coordinate. Every endpoint below is inclusive and
every coordinate is relative to that origin.

The cursor uses EGA/Tandy palette index 15 (white) and covers the complete
two-pixel outer ring of its cell:

| Primitive | Relative coverage |
|---|---|
| Horizontal strokes | All pixels from `x=0` through `x=15` on rows `y=0`, `1`, `14`, and `15` |
| Vertical strokes | All pixels from `y=0` through `y=15` on columns `x=0`, `1`, `14`, and `15` |

The secondary marker occupies the twelve-by-twelve box from relative
`(2,2)` through `(13,13)`. Its exact strokes are:

| Draw group | Horizontal strokes | Vertical strokes |
|---|---|---|
| Upper white, palette 15 | row 6, columns 2 through 6 | column 6, rows 2 through 6 |
| Upper black, palette 0 | row 5, columns 2 through 5 and 10 through 13; row 7, columns 2 through 6 and 9 through 13 | columns 5 and 10, rows 2 through 5; columns 7 and 8, rows 2 through 6 |
| Lower white, palette 15 | row 9, columns 2 through 6 | column 6, rows 9 through 13 |
| Lower black, palette 0 | row 10, columns 2 through 5 and 10 through 13; row 8, columns 2 through 6 and 9 through 13 | columns 5 and 10, rows 10 through 13; columns 7 and 8, rows 9 through 13 |

Those four marker groups are emitted in the table's order. Within each white
group the horizontal stroke precedes the vertical stroke; within each black
group the narrower left horizontal/vertical pair is followed by the wider left
pair, then by the narrower and wider right pairs. Each pair draws its horizontal
stroke before its vertical stroke. These are solid colour replacement writes,
not XOR or inversion: white and black overwrite the pixels already present.

Composition order for a lit eligible pass is the full eleven-by-eleven base
viewport repaint (terrain and composited actors), the cursor, then the
secondary marker. Consequently a secondary-marker stroke wins wherever the
two overlays coincide. There is no save-under, XOR erase, or overlay-specific
clear. The next pass's base repaint removes both old shapes before the blink
and eligibility tests decide whether to draw them again.

The overlay routine does not clip either shape to its sixteen-by-sixteen cell,
and it performs no separate range validation on the secondary coordinate.
Ordinary display clipping still applies. Legal arena coordinates from 0 through
10 keep every pixel of both shapes inside the viewport.

**Consumers of the shared effect counter, in both directions.** The second
blit entry that pass uses takes a shared counter, and it is worth naming what
touches that counter, because a contract nobody can falsify is exactly how an
invented one survives review. That counter is the natural moon-gate presence
value specified in `systems/overworld.md` Section 9.1. **It is persisted world
state**, carried in the save image — **not** scratch, and **not** scoped to a
call, a round or a turn. An earlier informal characterisation of it as a
short-lived animation counter is withdrawn. It **is read by** the tile-painting
pass, to choose the gate's current appearance, and by the gate-travel path that
advances it. It is **not** ticked by the per-turn cleanup, **not** advanced by
the round loop, **not** written by any combat routine, and nothing in combat
reads it. An implementation that ties it to combat rounds, or that treats it as
scratch that may be discarded between calls, is wrong in both directions.

**Nothing else in this section owns shared state.** The blink flag and the
marker coordinates named above are read only by that same painting pass, and
neither is saved. If a future revision of this section introduces a counter or
a flag, it should state its lifetime and its readers in this same form — and
where the honest answer is that nothing reads it, that is evidence the contract
is not real.

The phase-counter / base-step structure means actors act at *staggered* paces. There is no "player turn then monster turn" — initiative is *interleaved* by phase counter, so a fast monster might act twice between the player's turns.

### 7.1 Actors on cells they cannot leave

Two different situations get confused here, and only one of them is a freeze.

**A monster placed on terrain it cannot walk on is not frozen.** It takes its
turn every round on schedule; only its *movement* is constrained. So for the
case that prompted this section - a land class fought over water, placed by
Section 5.4 onto one of arena 15's sixteen authored water cells - there is no
freeze at all. The "permanently stuck actor" hypothesis is refuted for that
case. Such an actor still selects a target and attacks anything in reach, and it
remains a live, targetable, killable combatant. A class flagged teleport-capable
can additionally relocate, and *that* relocation is validated against the cell
predicate, so a stranded monster of such a class may free itself. It is
immobile, not inert. *(The water case is traced through the automatic driver,
the mover and the cell predicate, but was not observed live.)*

The random-cardinal movement arm behaves in a way an engine will not guess; see
Section 9 for its exact contract.

**The real freeze is restraint, and it is authored, visible, and recoverable.**
The round loop's step-3 skip fires on exactly two tiles, the stocks `0x84` and
the manacles `0x85`. Because the skip precedes the phase decrement, an actor on
one of those tiles never advances its counter and never acts. Exactly one
shipped arena - a dungeon room - places an actor on a restraint tile, and the
class placed there is a villager: an authored prisoner. No shipped party seat in
either combat-arena file lands on a restraint tile. Such an actor:

- never takes a turn while it stands on the restraint tile;
- is still a live combatant for every other purpose. It is returned by the
  cell-occupancy lookup, so it can be targeted, attacked and killed normally. The
  one exception is the Charm spell, whose own cursor explicitly refuses restraint
  cells;
- **can be released with `J` Jimmy**, which works in combat and targets the
  acting combatant's own cell plus the chosen direction. Jimmy first requires the
  party to hold at least one key: with a key count of zero it prints `No keys!`
  and returns immediately, before the direction prompt and before any tile is
  examined. Given a key, on a restraint tile in a combat scene the engine skips
  the live-occupant branch, rolls the selected member's Dexterity against a
  uniform draw of 0 to 29, and on Dexterity **strictly greater** than the draw
  rewrites that arena cell to cobble `0x44`, marks the display dirty, and prints
  `Unlocked` - consuming no key. The cell then no longer matches the restraint
  test, so the actor begins taking turns again from the next pass. A failed roll
  prints the broken-key result and destroys one key. The full Jimmy contract,
  including how the combat tail differs from the town prisoner release, is in
  `doors-and-z-transitions.md` Section 3.1.

**Consequence for victory.** The friend/foe census that gates the victory
announcement counts every descriptor that is non-empty and not dead-marked, with
**no terrain filter at all**. A restrained hostile therefore keeps the hostile
count above zero and suppresses `VICTORY!` until it is either freed or killed
(Section 14).

**Nothing displaces an actor between its own turns - scoped honestly.** Every
routine that writes an actor's arena coordinates during play acts either on the
slot whose turn it currently is (the combat movement step, the Klimb handler, the
combat arm of the Blink spell, the teleport commit, and the Push command's
in-combat tail) or at entry/camp time on a specific chosen slot (the two
placement passes, and the Hole-up watcher reposition, which selects its target by
roster identity rather than by whose turn it is). A restrained actor never takes
a turn, so none of the between-turns writers reach it. *(This finding carries
confidence **probable**, not established, and the reason is stated rather than
hidden: the exhaustive search behind it covers only direct absolute-displacement
writes across every shipped binary. Register-relative writers were checked case
by case rather than enumerated to exhaustion, and a redone search did find one
direct-write site an earlier scan had missed. Treat the negative as a strong
inference, not a proof.)*

## 8. Player commands in combat

When the round walker dispatches a player slot, the player command handler
reads exactly one keystroke from the input pipeline (using the same input
system that drives the rest of the engine), folds it to upper case,
case-checks it against the combat command set, and dispatches it. This handler
consults exactly one shared active-effect tag, Negate Magic's `N`, and only on
the `C`-Cast branch (Section 10). An earlier revision of this section said the
player command handler first rolled an inclusive 0..1 gate whenever Quickness's
`Q` tag was live; that is withdrawn. The `Q` gate and the corresponding Negate
Time `T` skip live at the head of the **automatic actor driver** — the other
half of the round walker's two-way dispatch, described in Section 9 — so they
suppress self-acting actors' turns, not the player's keystroke prompt.

The combat command set consists of letter keys A-Z plus a small set of control codes (Escape, Ctrl-S, Ctrl-B, Space, digits, direction codes). Every letter and every special input is now pinned, and recognition is not the same as world-mode success. The parser routes its letters through two shared shapes plus a handful of direct calls.

**Shape A — the labelled prompt with a live-actor gate.** The helper prints the verb label, then requires that the acting combatant is still alive. A dead actor gets the short "Can't!" refusal and the prompt is re-issued at no cost. A live actor's command is handed to one shared world-mode delegate chosen by the letter, and the combatant's action ends. Six letters use this shape: `G` Get, `J` Jimmy, `O` Open, `R` Ready, `S` Search and `U` Use. Their delegates are the same handlers the world modes use — the shared tile-interaction overlay for Get/Jimmy/Open/Search, the status/equipment overlay for Ready, and the item-use handler for Use.

**Shape B — the shared "that verb means nothing here" responder.** The
responder prints a bare verb label, appends one of three exact tails, then emits
the newline and plays a two-tone refusal beep. The tails contain no newline of
their own: `" what?"` (including its leading space), `"-Not here"` (no
exclamation point), and `"-Funny, no response!"`. Twelve letters use it: `B`
Board and `X` X-it take the first tail and therefore produce exactly
`Board what?` and `X-it what?`; `E` Enter, `F` Fire, `H` Hole up, `I` Ignite,
`L` Look, `M` Mix, `N` New order, `Q` Quit and `V` View take the second; `T`
Talk takes the third. The responder always re-prompts without cost. `D` and
`W` bypass it and print their own `D-What?` / `W-What?`, with the same no-cost
re-prompt.

The remaining letters call their targets directly, as the table below records.

| Key   | Combat behaviour |
|-------|------------------|
| **A** | Attack. Routes into the shared arena attack helper with the acting combatant and a flag saying whether that combatant is armed. It produces **one attempt per readied item that can be swung**, each opening its own targeting cursor; Section 8.2 has the full contract. Resolution is Section 11. Ends the actor's action. *(**Corrected.** Earlier revisions said this helper "announces the actor and the weapons it is wielding (or bare hands) before the attack resolves". That is withdrawn: the actor-and-armament line is the **turn banner**, printed before the keystroke is read and therefore printed identically whatever the player then presses. See Section 8.1.)* |
| **B** | Board — shared refusal responder, first tail. No cost. |
| **C** | Cast a spell: the combat prerequisite check, then either the in-arena prompt loop or the shared spell dispatcher (Section 10). Ends the actor's action unless the caster is dead, which re-prompts. |
| **D** | Prints the combat-specific `D-What?` refusal and re-prompts at no cost. |
| **E** | Enter — shared refusal responder, second tail. No cost. |
| **F** | Fire — shared refusal responder, second tail. No cost. |
| **G** | Get. Labelled prompt with the live-actor gate, then the shared Get handler. |
| **H** | Hole up — shared refusal responder, second tail. World-mode rest is not available inside an arena. No cost. |
| **I** | Ignite — shared refusal responder, second tail. No torch counter is touched on this branch. No cost. |
| **J** | Jimmy. Labelled prompt with the live-actor gate, then the shared Jimmy handler. The combat scene takes Jimmy's high-range restraint tail: a successful Dexterity pick on stocks `0x84` or manacles `0x85` clears that arena tile to cobble `0x44` and reports "Unlocked" without resolving or persisting an NPC release. Other Jimmy target families retain their shared behavior. |
| **K** | Klimb. Dispatches to the arena climb helper. It handles ladder up/down prompts, upward/downward combat exit attempts, and a limited in-arena climb/move case that mutates the active combat record; otherwise it prints a refusal. A blocked climb re-prompts at no cost; an applied climb ends the actor's action. |
| **L** | Look — shared refusal responder, second tail. This dispatcher does not run the world/town look flow. No cost. |
| **M** | Mix — shared refusal responder, second tail. It does not open the reagent mixer. No cost. |
| **N** | New order — shared refusal responder, second tail. No cost. |
| **O** | Open. Labelled prompt with the live-actor gate, then the shared Open handler. That handler carries no combat-specific branch of its own, so in an arena it behaves as it does on the surface. |
| **P** | Push. Prints the `Push-` label and calls the shared movable-static-tile handler directly, without the live-actor gate used by Shape A. It never moves an active-object record. In combat the handler uses the acting combatant as the coordinate anchor; a successful push or pull mutates the temporary arena tile state, advances that actor's arena position, dirties the redraw, and returns to the round loop. Space cancellation, either refusal, and either success all end the actor's action; Escape inside the direction prompt is ignored and leaves the prompt waiting. Exact transcripts, the out-of-grid backing-state edge, and the ambush/camp reveal preemption are in `systems/commands.md` Sections 8.1–8.2. |
| **Q** | Quit — shared refusal responder, second tail. An earlier revision of this section described combat `Q` as an "abandon party" command that forced the defeat exit; that is withdrawn. Combat `Q` prints its label and re-prompts, and there is no resident save route in combat either. |
| **R** | Ready. Labelled prompt with the live-actor gate, then the same status/equipment handler non-combat `R` uses, with the selection bound to the acting combatant instead of prompting for an arbitrary party member. Equipment mutation semantics, including the body-armour lock, are in `inventory.md`. |
| **S** | Search. Labelled prompt with the live-actor gate, then the shared Search handler. |
| **T** | Talk — shared refusal responder, third tail. No cost. |
| **U** | Use item. Labelled prompt with the live-actor gate, then the same item-use handler the world modes use, which opens the special-item picker and has its own combat branches. An earlier revision of this section said combat `U` was label-only and aborted without entering the item-use flow; that is withdrawn. Which individual item families accept a combat scene is owned by `inventory.md` and `catalogs/item-list.md`. |
| **V** | View — shared refusal responder, second tail. It is not the resident gem-view map path and consumes no gem. No cost. |
| **W** | Prints the combat-specific `W-What?` refusal and re-prompts at no cost. |
| **X** | X-it — shared refusal responder, first tail. Combat cannot be left with `X`: the command prints its label with the "what?" tail and re-prompts. An earlier revision of this section routed combat `X` to the escape handler; that is withdrawn. Leaving a fight is done by Escape, by stepping out of arena bounds, or by winning. |
| **Y** | Yell. Prints the combat Yell label and dispatches to the shared Yell handler, but combat's scene frame is not accepted by the ship-sail, Word-of-Power, or Shadowlord-name success branches. In combat, nonempty Yell input reaches the handler's no-effect path; empty input still uses the normal nothing-said result. Ends the actor's action. |
| **Z** | Z-stats. Dispatches to the same status display handler the world modes use, with no live-actor gate, selecting the acting combatant's party slot instead of prompting. Ends the actor's action. |

Other inputs:

- **Space** — pass / wait one phase. Ends the actor's action.
- **Escape** — routes to the combat escape handler, which is the command form of
  leaving a fight; its own result decides whether the actor's action ends or the
  prompt is re-issued.
- **Ctrl-S** — toggle sound. Re-prompts without even reaching the turn test.
- **Ctrl-B** — combat's own copy of the typeahead-buffer toggle, writing the
  same engine-wide setting as the resident one (`commands.md`). Re-prompts.
- **Digit `0`** - clear the active-player selection and repaint the panel. `0`
  is never remapped to a direction (Section 8.3).
- **Digits `1`-`6`** - select party member 1 through 6 as the active player. A
  failed selection re-prompts at no cost. **Reachable only while the input
  layer's numpad flag is clear** - that is, with NumLock off and no shift key
  held. With NumLock on, eight of the ten digits arrive as direction codes
  instead and a typed `4` steps west rather than selecting member 4. Section 8.3
  states the rule and the remap table.
- **Cardinal direction codes** - move one cell in the requested cardinal
  direction. If the destination leaves the arena, run the out-of-arena helper
  described in Section 3. A blocked step re-prompts at no cost. **A direction key
  is purely a step: there is no bump attack.** *(**Corrected.** Earlier revisions
  said "movement uses the step-or-attack primitive: if the cell is occupied by a
  hostile, attack instead". That is withdrawn - see Section 8.3 and Section 11.)*
  Diagonal direction codes are not combat movement commands; they are rejected
  with the stock `What?` refusal and cost no turn.
- **Anything else** — the stock `What?` refusal and a free re-prompt.

**The turn rule.** The parser keeps a single re-prompt flag, cleared at the head
of every parse. It is raised only by the dead-actor refusal, the shared
"not meaningful here" responder, the `D` / `W` / `What?` stubs, the escape
handler's own result, a failed party-member select, and the dead-caster Cast
path; a blocked step and a blocked climb raise it too. When the flag is raised
the player is returned to the prompt and the combatant has spent nothing. When
it is clear, that combatant's action is over. Every accepted verb therefore
costs the acting combatant its action, and every refusal is free — including a
refused Ready, whose refusal is indistinguishable from success to everything
outside the equipment overlay.

Cast clears that re-prompt flag before entering the shared spell dispatcher;
the spell handler's success or failure result does not restore it. Kill's
protected-class rejection is therefore a committed action even though it
reports `Failed!`: it neither re-opens the creature cursor nor returns the same
actor to this command prompt. Its exact resource, randomness, and presentation
envelope is specified in `systems/magic.md` Section 8.

**Where the free re-prompt occurs.** A raised re-prompt flag branches straight
back to the input read inside the same actor dispatch. It occurs before the
committed-action maintenance tail and before control returns to the round
walker. Shape-B `Q`, `X`, and the other free refusals therefore do **not** run
the acting slot's worn-ring hook, do not age the shared timed-magic counter, and
do not run the remaining post-action presentation/effect helpers. The same
actor is simply asked for another key.

For a committed non-digit action, that tail does run. If the acting descriptor
is an eligible party-side slot, it re-applies that member's equipped ring hook:
Ring of Invisibility reasserts the hidden presentation, while Ring of
Regeneration invokes the party-wide regeneration roll described in Section 12.
This is not the ring-destruction roll; the `A ring has vanished!` check is
encounter-entry-only. Digits `0` through `6` use their selection/UI path and
also skip this tail. Accepted Escape reaches the committed path only after its
handler has cleared the combat descriptors, so the later ring hook has no
eligible acting slot and does nothing.

**Diagonal input and the targeting cursor.** Combat is the one place in the game
that accepts eight-way input, and it is not movement. The full cursor contract is
in Section 8.2. An implementer should not generalise it into diagonal stepping:
no mode loop, and no letter dispatcher, accepts a diagonal step.

Several commands are **multi-stage** (Attack, Cast, Get, Jimmy, Open, Ready, Search, Use, Yell, and some delegated arena handlers): they print a short prompt or call a sub-handler that reads a follow-up keystroke. The combat command handler's dispatch is structured so multi-stage commands return control to the same handler for their continuation rather than recursing through the round walker. The command set mirrors the world mode loops' visible vocabulary so muscle memory transfers cleanly between play modes, but the combat parser owns its own branches and refusals. The most distinctive combat-only paths are Attack, Cast, active-player selection, the arena targeting cursor, combat Yell's no-effect scene fallthrough, out-of-bounds fleeing, and the Escape cleanup exit.

### 8.1 The turn banner is printed before the keystroke, for every command

**Does only `A` print the announce-actor-and-weapons line, or does a bare
direction key attack identically?** Neither half of that premise holds.
*(Established for the keyboard-driven per-actor handler in the combat overlay and
its whole entry path. Not verified for the automatic driver, which narrates
monsters' actions elsewhere.)*

The actor-and-weapons line is **not** Attack's announcement. It is the **turn
banner**, emitted at the start of every keyboard-driven combatant's turn, *before
any key is read*: a newline, the actor's name, and - for a party-side actor - the
clause `, armed with ` followed by the names of that actor's readied items
separated by `, `, or `bare hands` when none qualifies, terminated by a colon.

- Only the helm, weapon-hand and shield-hand slots are scanned, and only items
  whose per-item weapon-capability entry is non-zero are named. Ordinary helms,
  ordinary shields and all body armour therefore never appear in the clause -
  while the **spiked helm and spiked shield do**, because they carry a non-zero
  capability entry.
- A charmed monster acting under player control gets only its name and the colon,
  with no armament clause.
- Because the banner precedes the keystroke, it appears identically whether the
  player then presses `A`, a direction key, `Space`, or anything else.

What `A` adds on top of the banner is `Attack-` and `Aim! ` per attempt, plus a
per-item name line when two or three items qualify (Section 8.2).

The banner is unconditional once the actor passes the active-player gate, the
Sword-of-Chaos gate and the invisible-reveal / asleep early-outs. Note that a
free re-prompt after a refusal uses the short form and does **not** reprint the
banner.

**A bare direction key does not attack.** It is purely a step. The engine prints
the direction word (`West`, `East`, `North`, `South`), checks that the
destination stays inside the arena, and asks the arena-cell predicate whether
this mover may stand there. On acceptance the actor moves and its turn ends. On
rejection - which includes both terrain the mover cannot enter **and a cell
already occupied by a live actor** - the engine prints `Blocked!`, plays the low
bump tone (roughly 165 Hz for 200 duration units), drains pending input, and
re-prompts the same actor without spending the turn. There is **no bump attack**:
walking into an occupied cell never produces a to-hit roll, never prints
`Attack-` or `Aim! `, and never resolves damage. A destination outside the arena
takes the separate edge-exit path (Section 3) and does not print `Blocked!`.

### 8.2 `A` Attack: attempts, the interference abort, and the targeting cursor

**After `A` is accepted, does the engine enter a distinct direction read?** Yes -
accepting Attack opens a second, separate input read, and it is not a one-shot
direction key but an **interactive targeting cursor**. It is entered once per
readied weapon, not once per Attack command, and it is not reached
unconditionally. *(Established for the keyboard-driven handler and everything
downstream of its Attack branch: the per-character attack walker, the per-item
dispatcher, the melee and ranged arms, the cursor, the interference gate and the
cell-occupancy lookup; verified for the zero-reach, non-zero-reach and
bare-handed arms and for both the party-side and charmed-monster-side entries.
Not verified for the automatic driver, which never reads the keyboard, nor for
spell targeting beyond the shared cursor.)*

**What Attack runs.** The engine walks the acting character's three readied
equipment slots in order - helm, weapon hand, shield hand. Each slot holding an
item with a non-zero weapon-capability entry produces **one attack attempt**;
body armour is never scanned, and ordinary helms and shields have a zero entry
and are skipped. A character with no qualifying item makes a single bare-handed
attempt, which behaves as melee with range one. Each attempt prints `Attack-` and
then consults the item's **reach** (`catalogs/item-list.md` publishes the
per-item reach values): reach zero opens the cursor with maximum range one; a
non-zero reach opens it with that reach as the maximum range. Immediately before
the cursor opens the engine prints `Aim! `. When two or three items qualify, each
attempt additionally prints a newline, that item's name, and a colon on its own
line before its `Attack-`; with exactly one qualifying item, or none, no
item-name line is printed.

Two notes on the reach values, because the split is easy to get wrong. A non-zero
reach does **not** mean "missile weapon": the morning star and the halberd are
in-hand melee weapons with reach 2 and open a two-cell cursor, and the dagger
(reach 3) and spear (reach 5) are throwables. On the monster side, a class reach
of exactly 1 is normalised to zero, so it takes the fixed-range-one melee path
rather than a one-cell ranged cursor.

**The one case where no cursor opens: the adjacent-attacker interference abort.**
Five items - **sling, flaming oil, bow, crossbow and magic bow** - run an
interference test before the cursor. The engine keeps, per combatant, the
identity of whichever actor most recently struck that combatant; the value is set
when damage is resolved against them and cleared at the end of that combatant's
own next turn. The attempt is aborted if **all** of the following hold:

- that recorded actor exists, and its slot is not empty;
- it is on the automatic-driver side - a monster, or a party member acting under
  Sword-of-Chaos / charm control. **An adjacent ordinary party member never
  interferes;**
- it is neither invisible nor asleep;
- the Negate Time effect is not currently active;
- its distance from the attacker is exactly one. Distance uses the same truncated
  Euclidean metric as the cursor, so "exactly one" means any of the eight
  surrounding cells, diagonals included.

On abort the engine prints a newline, the interfering actor's name, and
` interferes!`, opens no cursor, **and the turn is still spent**. This is the
common, gameplay-visible "you cannot fire a missile weapon while something is on
top of you" rule, not an edge case. The other reach-bearing items - dagger,
spear, throwing axe, morning star, halberd, magic axe - do **not** run this test,
and neither does any zero-reach melee attempt or a bare-handed attempt.
*(**Corrected.** An earlier revision implied every Attack reaches the cursor.
That universal claim is withdrawn.)*

**The cursor.** It starts on the attacker's remembered previous target when that
target is still a valid, live, visible actor within the maximum range, and on the
attacker's own cell otherwise. Inside the loop:

Two different code spaces meet in this loop, and the numeral `1` occurs in both.
The table below writes an **internal direction code** as a bare number and a key
the player presses in `code` font, so *direction code 1* (west) and the *typed
key* `1` (the numpad key marked End, south-west) are never the same thing.
Section 8.3 gives the remapping that connects them.

| Input | Effect |
|---|---|
| Internal direction codes 1, 2, 3, 4 - delivered by the arrow keys, or by a typed digit the shared reader has already remapped (Section 8.3), never by the characters `1`-`4` reaching the loop unremapped | Move the cursor one cell west, east, north, south. |
| The four corner keys - Home, End, PgUp, PgDn, which are the numpad keys marked `7`, `1`, `9`, `3` | Move it one cell diagonally: Home/`7` north-west, End/`1` south-west, PgUp/`9` north-east, PgDn/`3` south-east. Note that the key `1` on this row is End, and is unrelated to internal direction code 1 on the row above. |
| Enter, or the letter `A` (either case) | Confirm at the cursor cell - **unless** the cursor is on the attacker's own cell, in which case nothing happens and the loop reads another key. |
| Space | Cancels if the cursor is on the attacker's own cell; anywhere else it confirms exactly like Enter. |
| Escape | Cancels. |
| Anything else | Discarded; the loop reads again. |

A move is applied only if the destination stays inside the eleven-by-eleven arena
**and** its distance from the attacker does not exceed the maximum range. If
either test fails the cursor simply does not move: no message, no beep, no turn
consumed, and the loop reads another key. Because the range test is the truncated
Euclidean distance, all eight neighbours are within range one, so **a melee
attack can target diagonals**.

On cancel the engine prints `Nothing!` (melee arm) or returns silently (ranged
arm). On confirm it looks for an actor occupying the cursor cell; if there is
none, or the occupant is dead-marked, invisible, or an empty/decoration slot, it
prints `Nothing!`. **The occupancy lookup does not filter by side**, so confirming
on a party member's cell attacks that party member. The acting character's turn
is consumed either way: cancelling with Escape or Space does not return to the
command prompt and does not give the turn back.

### 8.3 Direction keys, digits, and the numpad flag

The engine team's premise here was half right: direction codes 1-4 are not
produced by typing the digit characters directly - but the two namespaces **do**
collide, and the collision is the normal case rather than an edge case.
*(Established. This behaviour belongs to the shared keyboard poll and command
reader specified in `input.md` Section 5, so it applies to every prompt those
serve, not only to combat.)*

The shared input routine sets an internal **numpad flag** in two ways:

1. A key arriving as an extended scancode is matched against a small table - the
   four arrow keys plus Home / End / PgUp / PgDn - and translated to the
   direction codes; the flag is set.
2. A key arriving as one of the ASCII characters `1` through `9` causes the
   routine to read the BIOS keyboard shift-status byte and set the flag if
   **either shift key is down OR NumLock is currently active**.

When the flag is set, the command reader remaps the typed digits through a fixed
table: `1` south-west, `2` south, `3` south-east, `4` west, `6` east, `7`
north-west, `8` north, `9` north-east. `5` passes through unchanged, and `0` is
outside the window and is never remapped.

The consequences for combat:

- **NumLock off, no shift held.** Typed digits keep their ASCII meaning and reach
  the active-player-selection handler at the command prompt (Section 8), and they
  are inert inside the targeting cursor.
- **NumLock on, or either shift held.** Eight of the ten digits become direction
  codes. At the combat command prompt a typed `4` means "step west" rather than
  "select member 4", and inside the targeting cursor a typed `4` moves the cursor
  west. **Member selection by digit is therefore only reachable with NumLock
  off.**
- Only `0` and `5` are unconditionally inert inside the cursor.

This is deliberate: it is how the game reads the numeric keypad when NumLock is
on, because the keypad then emits plain ASCII digits and the shift-status byte is
the only distinguishing evidence available. *(**Corrected.** An earlier answer
said typed digits are inert as directions and that "the two namespaces never
collide". That is withdrawn and replaced by the conditional rule above.)*
Whether NumLock is on in a given player's session is an environment fact, not a
game fact; an engine should expose it as one.


## 9. Monster AI

When the round walker dispatches a self-acting slot, the AI runs as a sequence
of three passes that end in a **direct call** to the attack, movement or
special-ability helper it chose. Monsters and players share the *action*
infrastructure - the to-hit roll, the impact presentation, the damage roller and
the result narrator are one set of primitives used by both - but they do **not**
share the command layer above it. The automatic driver reads no key, synthesises
no key, enters no per-letter dispatcher, and prints no announcement.
*(**Corrected.** This paragraph previously said the three passes "ultimately
produce a *synthesised keystroke*", that "the AI generates the same bytes the
player would press", and that "the synthesised byte runs through the same
per-letter dispatcher as a player turn". **That is withdrawn** - see Pass 3
below, `RETRACTIONS.md` R353, and Section 11.1 for what each side actually
prints.)*

**Pass 1 - Dispatch setup.** The per-actor dispatcher — the **automatic actor
driver** — clears the actor's combat-status presentation area, prepares
narration scratch, and checks whether the current slot should run a normal
turn, yield to a queued animation/effect, or continue into AI decision-making.
Current evidence does not support a general per-class AI script runner. The
ordinary monster path is table and helper driven: status/flee gates run first,
then the class-flag special hook, target selection, movement-direction
choice, optional step/teleport logic, and finally a direct call into the shared
attack or movement primitive. *(**Corrected.** The tail of this sentence
previously read "and finally the same command parser used by player turns"; the
command parser is not on this path - `RETRACTIONS.md` R353.)*

**Active-effect gates at the head of the automatic driver.** Before any of
that, this driver reads the single shared active-effect tag (Section 12) twice.
These two are the driver's only reads of that tag; they are not the tag's only
consumers in combat. The `C`-Cast absorption check reads it for Negate Magic's
`N` (Section 10), and the AI target picker reads it for Mass Charm's `C` later
in this section:

- **Negate Time (`T`).** The driver returns immediately. The actor's whole
  turn is skipped — no status tick, no ability hook, no target pick, no attack,
  no step — and the round walker moves on to the next slot. Because this driver
  is the one that runs self-acting actors, the visible effect of Negate Time in
  an arena is that hostiles stop acting entirely for the tag's duration, while
  the party keeps being prompted normally.
- **Quickness (`Q`).** The driver rolls an inclusive `0..1` value. A zero
  consumes the dispatch and returns without acting; a one continues into the
  ordinary turn. Self-acting actors therefore act about half as often while
  Quickness is running. The player's own command prompt is not gated
  (Section 8).

Both gates precede the invisibility, sleep-wake and flee checks below, so a
skipped dispatch does not run the wake roll either.

**Pass 2 - Per-class special ability hook and direction.** Before any ordinary
target selection, attack, or movement is attempted, monster AI runs a small
class-flag hook. It is not a general script runner: it reads the acting
monster's class flag word and tests three ability bits in fixed order. Every
random choice below advances the same gameplay PRNG specified in
`systems/prng.md`; the hook does not precompute branch rolls.

Negate Magic's `N` active-effect tag and the Crown of Lord British's permanent
active-effect code gate the **whole hook**, not a spell-only sub-branch. Either
code returns an unhandled result before the class-flag lookup and before every
target or chance draw below. The automatic actor driver then continues to
ordinary target selection and attack, and to movement if the attack does not
consume the dispatch. Thus possession, blink, and hostile daemon summoning are
all suppressed without costing the actor its ordinary action opportunity. An
earlier abstraction called this an "enemy-cast gate" that returned "no spell";
that is withdrawn. The hook includes non-spell special actions, and its actual
return means "no special handled this dispatch."

- `0x0040` is the possess/charm-on-turn ability. It draws one uniform slot index
  in `[0, 31]` — a single draw, with no retry if the draw lands on an ineligible
  slot. The drawn slot is accepted only if it is party-side and none of
  marked-dead, phased/blinked, asleep-or-disabled, hidden/not-yet-revealed, or
  already controlled is set; because the ability hook itself only runs on
  monster-side actors, a monster can possess party members and never another
  monster. An accepted target then runs the normal resistance check. This is
  the branch's second PRNG advance: the resistance helper makes its underlying
  inclusive `0..60` draw and derives the engine's usual skewed `1..30` combat
  roll. No resistance draw occurs for an ineligible target. The effect lands
  only when that check does not block. On landing: the target's
  controlled bit (`0x01`, Section 6.1a) is set; the active-player sentinel is
  cleared to "none" **if the sentinel currently names the possessed character** —
  it is compared against the target's own owner/character byte, never against the
  caster's slot; the stats panel is redrawn, so the possessed member immediately
  shows the `C` status letter; and the target's name plus a short possession line
  and sound play. If the *caster's* class is Daemon, the caster's own descriptor
  is then released through the slot-clear path, so a Daemon that possesses
  someone removes itself from the fight. Once a valid target reaches the
  resistance path, the hook returns handled whether the resistance blocks or the
  effect lands.
- `0x0800` is the blink/phase ability. It draws one inclusive `0..255` gate
  value and fires on exactly `0..31`, an exact `32/256 = 1/8` acceptance.
  Success toggles the actor's phase/hidden flag and linked visual tile between
  visible and hidden, narrates the disappearance or return, and consumes the
  actor's turn. Values `32..255` decline to the summon test.
- `0x0400` is the summon-daemon ability. It independently draws the same
  inclusive `0..255` gate and accepts exactly `0..31`, again exactly `1/8`.
  A passed gate then makes **exactly one** random arena probe using the shared
  picker and spawn-cell validator used by the player's Summon spell
  (`systems/magic.md`, Summoning and conjuration). The picker makes two fresh,
  ordered draws: X from inclusive `0..15`, then Y from inclusive `0..15`;
  both draws occur before either bound is checked, and the probe survives only
  when both coordinates are at most 10. Thus the gate value is not reused as a
  placement seed, and no existing AI direction state supplies the candidate.
  The surviving cell is then checked deterministically for terrain and
  occupancy before ordinary actor allocation is attempted. There is no retry
  budget. On success a Daemon-class actor (class 38) is placed at that cell,
  the acting monster's name and a short summoning line are printed with a
  sound, and the new actor's linked sprite plays the brief flame transition
  before settling on the Daemon tile. Unlike the player's Summon spell, this
  branch does **not** stamp the controlled bit (Section 6.1a) on the placed
  Daemon: a monster-summoned Daemon is an ordinary hostile.

The exact lazy cascade for a class with multiple bits is:

| Stage | When reached | Result |
|---|---|---|
| Possess target draw | Possess bit is set | An ineligible single target declines to blink. An eligible target invokes resistance and then returns handled whether the effect is resisted or lands. |
| Blink gate draw | Possess is absent or selected an ineligible target, and the blink bit is set | `0..31` returns handled after blinking; `32..255` declines to summon. |
| Summon gate draw | Earlier branches declined and the summon bit is set | `32..255` returns unhandled. `0..31` proceeds to the fresh X and Y draws. |
| Summon probe, validation, and allocation | Summon gate passed | Any off-arena coordinate, rejected cell, or allocation/placement failure returns unhandled. Successful placement returns handled. |

“Handled” means the automatic actor driver ends this actor's dispatch: no
ordinary target pick, attack, or movement follows. “Unhandled” means the
ordinary AI target picker, attack path, and—if needed—movement path continue
in the same dispatch. Consequently, a successful blink or summon never also
performs an ordinary action, while every failed summon stage does. The
analyzed v1 data set assigns possess, blink/phase, and summon-daemon rows as
listed in `monster-bestiary.md`; the cascade above is the contract for any
variant class carrying multiple turn-special bits.

### Shared spell-resistance predicate

Several combat effects use one side-aware resistance comparison. For each
actor, the rating source depends on that actor's side, not on whether the actor
is the caster or the target:

| Actor side | Resistance rating |
|---|---|
| Party | The character's persisted Intelligence byte |
| Monster | The monster class's endurance rating |

Both ratings are interpreted as unsigned bytes. Let `C` be the caster's
rating, `T` the target's rating, and `R` one standard skewed combat roll in
`1..30`. The resistance score is

`S = truncate_toward_zero((T - C + 30) / 2)`.

The arithmetic is signed, and there is no clamp. The byte inputs bound the
numerator to `-225..285`, so the calculation cannot overflow a signed 16-bit
intermediate. The target blocks the effect only when `S > R`; when `S = R`,
the effect lands. Consequently, scores at most 1 can never block and scores
greater than 30 always block, as consequences of the comparison rather than
explicit clamps. The standard combat roll advances the shared gameplay PRNG
once through an underlying inclusive `0..60` draw `U`, then uses
`R = max(1, floor(U / 2))`. Thus `R = 1` corresponds to `U = 0..3`, each
result `2..29` corresponds to two underlying values, and `R = 30` corresponds
only to `U = 60`; the roll is intentionally not uniform.

The shipped effects using this predicate are monster possession, Repel Undead,
Charm, Kill/Slay Living, Cause Fear, directed Sleep, and Death Wind. Possession
therefore compares the party target's Intelligence against the monster
caster's endurance; a party-cast effect against a monster reverses those role
sources. Every listed path treats a blocked result as effect failure.

Tremor and Poison Wind use a different target-only gate. Each draws the same
skewed `1..30` combat roll and accepts the target when the roll is greater than
or equal to that target's combat weight. No caster rating or resistance score
enters this comparison. Combat weight is normally the actor's base-step/speed
byte. It is forced to 1 for a monster while Negate Time is active, for class 26
(Mimic), or for an actor carrying the asleep/magically-disabled flag.

**Target selection** is the heart of Pass 2. Given the acting monster's slot index, the target picker walks the actor table backwards from slot 31 to slot 0, computes the truncated linear Euclidean distance to each candidate, and picks the closest one that survives a chain of filters:

- Not the acting monster itself.
- Slot is not empty and not marked dead.
- Not on the same *faction* - friend/foe is decided by a "slot-to-group"
  helper that maps each slot to a small group id.
- Grouping note: ordinary placed party actors and ordinary placed monsters
  start in opposite combat groups, because the slot-to-group helper reads the
  party-class bit `0x80` to pick its rule and then keys on the controlled/charmed
  bit `0x01` as a team toggle — returning that bit for a party-side slot and its
  inverse for a monster-side slot (Section 6.1a). Charming or possessing an
  actor therefore does move it to the opposite group for this filter. A
  *separate* team resolver, consulted only on a special pre-combat-scene branch,
  reads **descriptor** bytes only - it never consults the per-class flag word.
  (**Corrected 2026-08-23**: this sentence previously said it "reads descriptor
  bit `0x40` and a team-override flag that lives in the monster's per-class flag
  word". Both halves are withdrawn - the test is on descriptor bit `0x20`, and
  the class-flag table is not read by that routine, or by any resident routine,
  at all. See Section 6.1a.) One shipped roster template is hard-wired hostile: whenever a
  party-class actor stands in for the game's traitor character - the last
  record of the shipped sixteen-record roster - the resolver forces it into
  the monster-side group however it reached the field (charm, summon, or
  scripted spawn), so it reads as an enemy to the party and as a friend to the
  monsters, for both the friendly-fire filter and the player-versus-AI dispatch
  gate. **The player's own character is exempt by construction, and no name the
  player can enter changes any actor's team.** The override is consulted only
  for slots that reference a *non-zero* roster record, and roster record zero is
  the player's own character; further, record zero is the only record the player
  ever names - character creation and the Ultima IV import both write only that
  record. Whole thirty-two-byte roster records do move between slots elsewhere
  in the game: a companion joining or leaving the travelling party is inserted
  or lifted out and the neighbouring records shift by one slot, the usurper's
  capture scene removes a member the same way, and New Order exchanges two
  records outright. None of those moves can carry the player's own record out
  of record zero. A companion joins at the current party-size index, which is
  never zero because the player's character always occupies record zero and is
  always counted; the leave path refuses the leader's own slot with a refusal
  message; the capture scene's selector passes over the leader and takes the
  first eligible companion after it; and New Order rejects the leader's slot in
  either prompt. None of these paths writes player-supplied text into a record
  either - they only relocate records that already exist. Names in records one
  through fifteen therefore always arrive verbatim from the shipped seed roster
  or from the save.
  In the shipped roster exactly one record matches, and it is the traitor
  template. An implementation may key this rule directly to that roster record;
  it must not key it to any property that a player-entered name could satisfy.
  This is part of combat grouping, not a conversation or quest flag.
- Not in a suppressed phase/hidden state, except that combat whose saved
  pre-combat scene is Doom and combat whose acting monster class is Shadow Lord
  bypass this extra suppression filter. The exception is separate from ordinary
  invisibility.
- Visible to the acting monster: the "invisible / not-yet-revealed" flag is
  still rejected after the phase/hidden check. This ordinary invisibility
  filter is not the same as the special suppression-filter bypass above.

When Mass Charm is active, the same target picker first checks the shared
active-effect tag for `C`. For an ordinary monster-side automatic actor, it
resolves the actor's class charm threshold from the per-class combat record.
The generic selector instead supplies the linked party member's Dexterity when
a controlled party-side actor reaches this automatic path. It then rolls one
uniform random byte in `[0, 255]`. If the roll is strictly greater than the
selected threshold, the acting slot is treated as **party-aligned group 0** for
this target pick; otherwise it keeps its resolved group. This is a caller-local
override: it does not mark an actor as charmed, rewrite its descriptor, change
cell occupancy, or alter side counts. It changes only which candidates survive
the normal same-group filter for the current AI decision. For a threshold `T`,
the remap chance is `(255 - T) / 256` for `0 <= T <= 255`; a threshold of 255
can never remap. The current class thresholds are catalogued in
`catalogs/monster-bestiary.md`.

*Corrected 2026-08-27:* the earlier description called group 0 "neutral";
that label is withdrawn. Group 0 is the party-aligned group (Retraction R296).

The target's distance is `floor(sqrt(dx^2 + dy^2))`, computed from the acting actor's arena coordinate and the candidate's arena coordinate. It is not Manhattan distance, Chebyshev distance, or a squared-distance table lookup. Backwards walk plus strict less-than comparison means *the lowest-numbered slot among candidates of equal distance wins*, biasing toward party members (low slots) when distances tie.

The target scan also tracks whether any of the first five party slots survived
the filters. If no target and no counted party member survive, the AI asks the
per-turn cleanup/effect helper for a fallback target. If that still leaves no
usable target, the original moves toward the centre of the eleven-by-eleven
arena. During this centre fallback, it scans the monster-side slot range
backwards and, for each live monster-class record, stamps the same critical-HP
marker used by fear setup and sets the fleeing flag. Slot 5 still participates
in the normal closest-target competition when it survives the filters, but by
itself it does not suppress this no-party fallback.

**Step direction.** Once a target or fallback point is picked, the unit-step
vector is the per-axis sign of `(target - self)`: each component is `-1`, `0`,
or `+1`. If the acting monster's "fleeing" flag is set, both axes are negated
— the monster moves *away* from the target or fallback point. The no-target
centre fallback therefore moves actors toward the centre unless they are
already aligned with it.

**Movement fallback and teleport.** When an actor's attack path does not consume
the turn, the movement primitive uses the synthesized step vector. A
teleport-capable monster first gets a chance to move to a random legal arena
cell; the candidate is accepted only if the same arena-cell occupancy/hazard
test used by combat placement allows it. Negate Magic's tag and the Crown's
permanent code suppress this teleport arm before its chance roll and random-cell
probe, but do not suppress movement: control proceeds directly to ordinary
stepping in the same dispatch. Ordinary stepping first tries the target
vector on one axis, with randomized axis priority, then falls back to random
cardinal tries when the direct axes are blocked. An accepted move updates both
the combat actor/effect record and the linked renderer-facing active-object
record before the post-step terrain/effect check runs.

**The random-cardinal fallback is four independent draws, not a neighbour
scan.** *(**Corrected.** An earlier revision described this arm as asking a
"surrounded" helper whether all four cardinal neighbours are blocked and
returning "no action" when they are. That is withdrawn.)* The arm makes **up to
four independent attempts**; each attempt draws one of the four cardinal
directions uniformly at random and tests **only that direction** against the cell
predicate, retrying on rejection. It commits the first accepted direction. Two
consequences an engine must reproduce rather than optimise away:

- A monster with exactly one open direction can still fail to move within its
  four attempts, purely because the draws never landed on it.
- When all four attempts fail, the routine still reports the action as consumed
  unless the final draw happened to be the first direction tried, and the
  committed displacement in that case is zero.

This is what makes a monster stranded on terrain it cannot enter (Section 7.1)
look stuck without being frozen: it acts every round, it attacks anything in
reach, and its movement simply never succeeds.

The per-turn morale writer for the fleeing flag is the monster wound-score
classifier. Cause Fear and Repel Undead are the two spell-side writers: each
accepted actor has its combat HP counter driven to one *and* its fleeing bit set
directly by the spell, so the flag is already up before the classifier next runs,
and the critical HP keeps the classifier re-asserting it. The classifier compares the acting monster's current HP against its
class maximum: below one quarter sets fleeing, one-quarter through just under
one-half rolls a morale check that sets fleeing on 252 of 256 possible
random-byte results, and one-half or higher clears fleeing. It also returns a
four-bucket wound score for other AI consumers.

Cause Fear sweeps all thirty-two combat slots and accepts every monster-side
actor that is not one of the three protected special classes (14 Blackthorn,
15 Lord British, 47 Shadow Lord) and that fails the shared resistance check. For
each accepted actor it writes the combat HP counter to one and ORs in the
fleeing bit `0x02`.

Repel Undead is exactly the same sweep with one extra condition: the actor's
class must also carry the undead class-flag bit. It writes the same two values
and nothing else. Neither spell places, re-types, tames, or repurposes an actor,
and neither touches the controlled/charmed bit `0x01`. Earlier drafts described
Repel Undead as a "lower-tier summon/tame" effect that wrote `0x01`; that is
withdrawn. The no-target centre fallback described above is
the third traced direct flee writer: it marks eligible monster-side slots with
the flee flag while forcing their critical-HP marker. The
possess/blink/summon-daemon hook does not write the fleeing flag.

**Pass 3 — Commit.** The automatic driver commits the chosen action by calling
the attack, movement and special-ability helpers **directly**. It reads no key,
synthesises no key, and never enters the per-letter command dispatcher. Its
chosen direction is carried as an internal direction code, the same encoding the
movement primitive of Section 11 takes from a player's direction key, but the
code is handed to that primitive as an argument rather than routed through the
command parser. **And no announcement is composed or printed at any point on
this path.**

*(**Corrected.** This paragraph previously said the AI "generates the same bytes
the player would press", that "the byte falls into the same per-letter
dispatcher as the player command handler", and - the load-bearing error - that
"before the command runs, the AI assembles a one-line narration string — for
example `<monster name> attacks <target name>, armed with <weapon>!` — by
stitching together a short verb composer". **All of that is withdrawn.** No
string of that shape, and no verb composer, exists anywhere in the shipped game:
an exhaustive scan of every printable text run in the executable, all overlays
and all four display drivers finds eleven strings containing "attack", every one
of them a fixed prompt or a fixed event line, and none of the form
`<attacker> attacks <target>`. The automatic driver's complete callee set was
enumerated and contains neither the command handler nor any announcement
routine. See `RETRACTIONS.md` R353 and Section 11.1.)*

The architectural consequence, correctly stated: **the two sides share the
to-hit roll, the impact presentation, the damage roller and the result narrator,
and they join *below* the announcement layer.** All damage and movement effects
in combat go through the same primitives regardless of whether the actor is
player-driven or self-acting - but the banner, `Attack-`, `Aim! `, `Nothing!`
and the miss line all live *above* the join, on the keyboard-driven side only.
That is precisely why an ordinary hostile monster announces nothing and, on a
melee miss, prints nothing at all. Section 11 describes the shared primitives
and Section 11.1 gives the exact narration census for both sides.

## 10. Spells in combat (summary)

Combat shares the spell engine with the rest of the game; the C (Cast) command dispatches via the same routing as the overworld C. The combat-specific path adds three things.

**Interference and active-effect checks.** Before queueing a spell, combat runs
an interference check, not a resource or spell-target gate. Each actor slot has
an incoming-attacker entry. The ordinary automatic adjacent-attack path writes
the attacker into the victim's entry before resolving whether the attack hits,
so a miss records too; later qualifying attacks overwrite the source. Ranged,
failed-range, no-target, and special controlled-actor attacks leave the entry
unchanged.

When a party actor presses `C`, combat blocks only if the recorded source is
currently occupied, hostile, visible/revealed, awake, and in one of the eight
adjacent cells, and Negate Time's `T` tag is not active. On a block it prints a
newline, the source actor's name, and ` interferes!`, then re-prompts the same
actor. The refusal is not a completed action and does not clear the entry or
consume another actor turn. If any current-state test fails, combat proceeds to
the shared spell dispatcher.

The victim's entry clears only after that victim completes an action. It is not
reset at combat entry, round start, or combat exit, and skipped actors do not
clear it. The map is save-backed, so an uncleared source can survive combat and
save/load; later Cast attempts revalidate the referenced slot rather than
trusting its history. `systems/magic.md` Section 7 gives the full predicate and
`formats/saved-gam.md` Section 10 gives the saved representation. The charge,
mana, level, and scene checks remain owned by the shared dispatcher. The combat
C-Cast path also checks the shared active-effect tag:
when Negate Magic's `N` tag is active, the cast is absorbed/refused before the
shared spell dispatcher consumes charge or MP.

**Scene gate.** Each spell carries a four-bit allow-mask for the scenes it works in: combat, dungeon, indoor/town-mode, and overworld. Scenes for which the spell has no entry print a `Not here!` refusal. Most damaging spells are gated to combat-only.

**Charge and MP debit.** The spell's MP cost is `(spell_id / 6) + 1` - eight circles of six spells each. The pre-mixed charge counter for that spell is decremented before MP and level validation. If MP is too low, the charge is not refunded; if the caster's level is too low, both charge and mana are spent. The spell-effect handler runs only after these gates pass.

The full spell system is described in its own spec; only the combat-side gating
and dispatch are covered here. Monster turns choose their action in the
automatic driver and call the shared primitives directly; they do **not** enter
the command parser (Section 9, `RETRACTIONS.md` R353). The class-flag special
hook is bounded to possess, blink/phase, and summon-daemon branches before the
movement-direction choice.
Those effects do not route through the party spell prompt, party reagents,
premixed charges, MP, or player circle gates.

## 11. Attack resolution

Movement and attack are reached through one per-turn dispatch, and the movement
step primitive is called once per actor turn. The primitive takes a direction code (1 = west, 2 = east, 3 = north, 4 = south, the same mapping the world-mode-loops use) and the actor's slot index:

1. **Translate direction to a unit step.** Cardinals map to `(dx, dy)` of `(±1, 0)` or `(0, ±1)`. A direction code of zero or out of range produces `(0, 0)` — "attack in place".
2. **Print the direction word** ("North", "South", "East", or "West") followed by a newline. Movement narration is part of the primitive.
3. **Range-check the destination.** `(new_x, new_y) = (self_x + dx, self_y + dy)` must fall in `[0, 10]`. If off the arena, route to the out-of-bounds handler. That handler decides between ship-style refusal, same-direction refusal for constrained exits, and an accepted leave/escape trigger.
4. **Run the step inner pass.** A separate function handles whichever case applies:
   - **Empty walkable cell:** the actor moves. Update its (X, Y) in both the actor table and the parallel dynamic-objects table.
   - **Any live actor at the destination, or terrain the mover cannot enter:** treat as blocked.

   *(**Corrected.** Earlier revisions of this step listed a third case -
   "hostile actor at the destination: run the attack roll" - and described the
   primitive as a step-or-attack primitive. **That is withdrawn.** There is no
   bump attack in combat: a direction key or a synthesised step into an occupied
   cell prints `Blocked!` and resolves no damage, and the cell-occupancy check
   does not distinguish friend from foe for this purpose. Attacks are reached
   only through `A` and its targeting cursor (Section 8.2) or through the AI
   attack path (Section 9). An engine built on the withdrawn text lets players
   attack by walking, which the original does not. The separate observation that
   the formerly suspected data-region lookup is not a combat damage or hit-chance
   matrix is unaffected and still stands.)*
5. **On success**, the primitive commits the new positions and returns the completed command to the actor dispatcher.
6. **On failure**, narrate "Blocked!", play the 165 Hz blocking tone for 200 calibrated units, and leave the actor in place. The exact mute and timing behavior is specified in `audio.md`.

Placed-field contact does not run inside this primitive. It belongs to the
round walker's common post-dispatch tail. After either per-actor handler returns,
the walker passes its current combat-descriptor slot to the terrain/field hook;
there is no intervening test for movement success, attack success, or a changed
coordinate. A parser-local refusal or blocked direction that re-prompts without
returning has not reached the hook, but a completed pass, attack, cast, automatic
status/no-action dispatch, or successful move does. The rule is identical for
player-controlled and AI-controlled slots because their dispatch branches join
before this call.

Combat field casting itself enters a shared arena-field helper that separates
marker placement from contact/application before any per-field result is
applied. The CAST field-kind table maps Fire/Poison/Sleep/Energy to
`0x35`/`0x33`/`0x34`/`0x36` for this path. Player C-Cast field targeting uses
the combat arena cursor, followed by the ordinary projectile/impact resolver;
it is not an adjacent-direction prompt. The cursor is bounded to the
eleven-by-eleven arena and the spell's range. Invalid cursor moves are ignored
rather than clipped or wrapped, and the cursor stage does not reject blocked
terrain, occupied cells, or empty cells. Escape cancels after C-Cast has spent
the premixed charge and mana, but before spell sound, coordinate lookup,
projectile/impact resolution, or marker placement.

After cursor confirmation, placement requires a confirmed impact cell from the
projectile/geometry helper, but there is no Fire/Sleep/Energy random acceptance
gate for marker materialization. Once impact resolution confirms the cell, the
field-kind switch places the matching active-object marker in the temporary
combat table without creating a paired combat-effect descriptor. The helper also
scans slots in ascending order and returns the first descriptor at the selected
coordinate with either live/selectable bit (`0x80` or `0x40`) set, without
marked-dead bit `0x20`, without hidden/not-yet-revealed bit `0x04`, and without
linked active-object tile byte `0xF4`; that lookup controls the hit/contact
target returned by the helper, not whether the marker is placed.

The post-dispatch hook has this exact ordered contract:

| Stage | Input and result |
|---|---|
| Target selection | The argument is the round walker's current combat-descriptor slot. That same descriptor is the effect target; no second descriptor is found by coordinate. Its current X/Y and its active-object back-reference are the lookup inputs. |
| Terrain priority | Check arena terrain at that X/Y first. The exact recognized bytes are listed below. A recognized terrain hazard selects its effect immediately and suppresses the placed-marker scan for that dispatch. |
| Marker scan | If terrain selected no effect, scan all thirty-two active-object records in ascending index order. Skip the record whose index equals the target descriptor's active-object back-reference, then compare every other record's X/Y with the target descriptor's X/Y. The first colocated recognized marker wins. |
| Meaning of the skip | The skipped item is the actor's renderer-facing active-object record, not the current combat actor. This prevents an actor sprite from being interpreted as a field marker. A separate field record on the same cell still targets and affects the actor whose slot was passed. |
| Completion | Apply the selected result to the passed slot, then continue through the ordinary post-action maintenance. Contact does not clear, age, or rewrite the marker. |

Terrain recognition is exact-byte, not a tile-family range test:

| Arena terrain byte | Shipped tile identity | Hook-level predicates and result | PRNG use after lookup |
|---:|---|---|---|
| `0x04` | Swamp | Select the Poison-tier result. Reject the result when the target descriptor's linked active-object tile/class byte is at least `0x80`. For an accepted party target whose character status is Good, change status to Poisoned. Any other accepted target enters the shared damage/status endpoint with no attacker credit. | The linked-record rejection and Good-status test occur before any draw. Rejection and the Good-to-Poisoned arm consume none. The accepted damage fallback consumes one inclusive `0..20` draw and passes that raw value directly to damage/status application. It makes no defense draw. |
| `0x8F` | Molten lava | Select the Fire-tier result: play the target sound, pass a rolled raw value to the shared damage/status endpoint, run no-attacker finalization, and request a status-panel refresh. | Consume one inclusive `0..10` draw after terrain selection. It makes no defense draw. |
| `0xBC` | Fireplace | Same Fire-tier result as molten lava. | Consume one inclusive `0..10` draw after terrain selection. It makes no defense draw. |

No other arena terrain byte is recognized by this hook. In particular, there
is no arena-terrain Sleep, Energy, or Doom-absorption arm. Selection of swamp,
molten lava, or fireplace suppresses the placed-marker scan before the selected
effect is dispatched. Therefore a swamp cell still suppresses a colocated
field marker when the later linked-record class gate rejects the swamp result;
the hook does not fall back to the marker scan.

Consequently, a successful move onto Poison, Sleep, or Fire applies that field
to the mover. Remaining on one of those markers while completing another action
can apply it again. Field ownership and the caster's slot are not inputs, and
the creature-prompt friend/foe lookup is not repeated.

The per-marker results and random-consumption order are:

| Field | Hook-level predicates and result | PRNG use after lookup |
|---|---|---|
| Poison | Reject contact when the target's linked active-object tile/class byte is at least `0x80`. For an accepted party target whose character status is Good, change the status to Poisoned. Any other accepted target enters the shared damage/status endpoint with no attacker credit. | The linked-record rejection and Good-status test occur before any draw. The Good-to-Poisoned arm consumes none. The damage fallback consumes one inclusive `0..20` draw and passes that raw value directly to damage/status application. It makes no defense draw. |
| Sleep | Ignore a dead party target; otherwise write asleep status for a party target or the combat sleep/disabled bit for a non-party target. | No hook-local draw. |
| Fire | Pass a rolled raw value directly to the shared damage/status endpoint, then run the ordinary no-attacker finalization and status-panel refresh. | After the marker has won the scan, consume one inclusive `0..10` draw. It makes no defense draw. |
| Energy | The Energy marker is not recognized by this contact hook. The arena movement validator treats it as a blocking marker, while Poison, Sleep, and Fire markers are passable for destination occupancy. | No contact-path draw and no zero-valued damage dispatch. |

The ordinary attack damage roller (Section 12) is not called by Poison or Fire
contact. *(**Corrected.** This sentence formerly described that roller as the
one "which randomizes attack value and defense". Only the **party** side of it
randomizes the attack value; a monster's attack value is the flat class byte
with no draw at all. See `RETRACTIONS.md` R336.)* Their raw damage still enters the shared
damage/status endpoint, so its ordinary class modifiers, HP changes, and death
handling remain applicable.

The traced
CAST/COMSUBS/COMBAT callbacks, the accepted-placement resident redraw helper,
the post-action contact hook, the generic active-object tick, and the monster
death/record-clear path do not contain a field countdown, decrement, or pre-exit
removal. Placed markers persist until combat exits, when the combat framer
restores the pre-combat active-object table.

Separate from player-cast field markers and arena-terrain contact, one special
combat path handles an actor being absorbed by a scripted field-like cell. It
runs in the actor handler's committed non-digit action tail, before that handler
returns to the round walker and before the common terrain/field hook above.
Parser refusals that re-prompt and the `0` through `6` active-player selection
commands skip this inner tail. The absorption call itself has no
movement-success predicate, so any committed non-digit action can trigger it
when its remaining conditions hold.

The path requires the active combat descriptor to be live, not already claimed
by the dead/removed bit, and at arena row `2`. It then reads the renderer's
sixteen-byte-stride companion band at row `1` and the actor's arena X—the cell
directly north of that actor—and accepts a byte whose family masks to
`0x3C..0x3F`. It does not read the combat arena terrain grid. This predicate and
the absorption effect consume no PRNG draw. On success it narrates the
absorption, plays the effect, invalidates the current active-player selector,
updates the affected slot through the shared combat effect helpers, and writes
the shared combat-result marker consumed by dungeon room cleanup.

The distinction between origin and immediate input matters. In stock data,
Doom's deepest room-id-fifteen arena supplies a special `0x3C` setup source in
its metadata band. Dungeon-room setup places that source through the special
active-object path rather than as an ordinary monster; viewport composition
then projects it into the renderer companion band inspected by the absorption
hook. Thus the Doom family originates as a special active object and is
observed through render composition, but it is neither an arena-terrain byte
nor one of the common hook's recognized placed markers (`0xE8`, `0xE9`,
`0xEA`). It does not participate in terrain-over-marker priority. The result
marker remains the low-level bridge into the terminal endgame handoff when the
caller is a qualifying dungeon room. The unresolved portion is limited to
per-subtype labels for unrelated special-placement values in the same dungeon
metadata scan, not the final-room handoff conversion.

Damage application is the responsibility of the inner-pass attack roll (when the destination is a hostile actor), which calls into Section 12's damage-and-status handler with the rolled damage value and the target's slot. The same damage/status endpoint is also used by combat spells after their own targeting and raw-damage calculation.

**Weapon, range, and hit routing.** The same attack infrastructure also serves
weapon-style combat actions chosen through the spell/weapon dispatcher and the
AI attack driver. A zero damage row routes to spell or special effect handling;
a nonzero damage row routes to target selection and attack application. AI and
ranged/effect attacks measure arena distance with the same truncated Euclidean
slot-range helper used by target selection. If the target is beyond the
actor's applicable range cap, the attack action exits without applying damage.
Adjacent targets use the melee damage path; in-range non-adjacent targets use
the ranged/projectile/effect path.

The shared to-hit helper is used by ordinary melee and ranged/effect attacks in
both directions - a monster attacking a party member and a party member
attacking a monster - unless the caller has forced the outcome. Certain special
action/effect tile families are always-hit cases. Otherwise the helper asks the
shared actor-rating selector for one rating per side, computes a score from the
pair, takes one draw, and compares.

**The score.** With `A` the attacker's rating and `D` the defender's rating,

`S = truncate_toward_zero((D - A + 30) / 2)`.

**The defender's rating is the added term and the attacker's is the subtracted
one** - the same way round as the shared spell-resistance predicate in Section
9, where the target's rating is the one added. The arithmetic is signed and
nothing is clamped; both ratings are unsigned bytes, so the numerator cannot
leave a signed sixteen-bit intermediate. *(**Corrected.** Earlier revisions
published `(attacker - defender + 30) / 2` and, separately, called the combat
weight "the defender term of the score in the ordinary melee case". Taken
together those are inverted relative to the original, which adds the defender's
rating and subtracts the attacker's. With the comparison direction below, the
inversion flips who is favoured on every ordinary melee and ranged/effect
attack. **The formula is withdrawn; the combat-weight clause is confirmed** -
the weight really is the defender term, and what was wrong was the surrounding
formula naming that term the subtracted one. See `RETRACTIONS.md` R334. This
closes the operand-labelling residual that R232 left open.)*

**The draw.** One standard skewed combat roll `R` in `1..30` - the same shared
helper used by the drop gate (Section 6.3), the resistance predicate and the
Tremor/Poison Wind gate (Section 9): one inclusive `0..60` draw halved with
truncation, with a zero result promoted to one. Across the sixty-one underlying
values `1` occurs four times, each of `2..29` twice, and `30` once, so the draw
leans toward low values and therefore toward hits. *(**Corrected.** An earlier
revision said the draw's range was unverified, that two private analyses
disagreed about which source the helper called, and that **no hit percentage is
published**. The source is now identified as this shared helper, and both limits
are withdrawn; see `RETRACTIONS.md` R335. Percentages are published below.)*

**The comparison.** **The hit is accepted when `R >= S`.** The score is a
difficulty number: a larger score is a *worse* chance to hit. This is the
direction R232 established and it is unchanged. Two boundaries follow from the
arithmetic rather than from any explicit clamp - a score of `1` or less always
hits, and a score of `31` or more always misses. For `2 <= S <= 30` the
**idealised** chance to hit is `(2 * (30 - S) + 1) / 61`:

| Score | <=1 | 2 | 5 | 7 | 8 | 9 | 12 | 15 | 20 | 22 | 25 | 30 | >=31 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Chance to hit | 1.000 | 0.934 | 0.836 | 0.770 | 0.738 | 0.705 | 0.607 | 0.508 | 0.344 | 0.279 | 0.180 | 0.016 | 0.000 |

That closed form is an idealisation, not the exact realised law. The underlying
range primitive carries about 0.16 percent modulo bias toward low values - the
same caveat `RETRACTIONS.md` R321 already publishes for this shared roll - so
the realised figures sit a shade off the fractions above: the Bat example below
is 0.7457 realised against 0.7459 idealised. Parity comes from reproducing the
helper, not from reproducing the fraction, so an engine that "fixes" the draw to
be uniform over `1..30` is close but not parity-exact.

The resistance predicate in Section 9 shares this score *shape* but reports the
opposite outcome: it returns "blocked" when the score beats the roll, while this
helper returns "hit" when the roll reaches the score. Do not generalise one
acceptance test across both.

**Which rating each side supplies.** The selector is side-aware, and the two
sides of an ordinary melee are not symmetric.

| Side | Case | Rating returned |
|---|---|---|
| Defender | every ordinary melee and ranged/effect attack, party or monster | that actor's **combat weight** |
| Attacker | monster whose class carries the `zero-selector stat row` trait | the class **combat tier** |
| Attacker | any other monster | its own **combat weight** |
| Attacker | party member attacking with one of the five strength-arm items | the character's **Strength** |
| Attacker | party member with any other readied item, or bare-handed | its own **combat weight** |

The `zero-selector stat row` trait is the per-class flag
`catalogs/monster-bestiary.md` already publishes; in the analyzed v1 data six
classes carry it - Mimic, Reaper, Gargoyle, Orc, Ettin and Headless - and every
other class, Bat included, feeds its combat weight into the attacker term.

**Combat weight** is the per-actor descriptor field the round loop also uses as
the base step (Sections 5.1, 5.2 and 9): for a **party** actor it is the raw
Dexterity byte copied at seating, and for a **monster** it is the class speed
rating jittered by a uniform `[-4, +3]` at placement, reverting to the shipped
rating when the sum would exceed 30. It is forced to the floor value one in
three override cases - while the Negate Time tag is running and the actor is a
monster, for one specific actor class, and for any actor carrying the
asleep/magically-disabled bit - so all three overrides make the affected actor
markedly easier to hit while barely changing what it can land; the Negate Time
override is the mechanical bite of a time-stopped arena. Earlier revisions
described this weight as a "team modifier" consumed by a chest-encounter
targeting flip; that reading is withdrawn.

Because the defender term is *always* the combat weight, **Dexterity is the
party's melee evasion stat and the jittered class speed is the monster's**. No
other character field enters the to-hit score: not level, not Intelligence, not
the cached combat-defense byte, and not any readied armour. And because the
attacker term is normally the combat weight too, a fast actor is simultaneously
harder to hit, more accurate, and acting more often.

**The strength arm.** Five equipment ids select Strength instead of the
attacker's combat weight, through a per-item to-hit-attribute value that is a
third per-item side table - separate from the `Attack max` damage value and from
the non-adjacent range cap. In the analyzed v1 data they are **Spiked Helm,
Spiked Shield, Club, Mace and 2H Hammer** - the catalog's own names for ids 3,
6, 18, 24 and 31: the blunt/impact family.
Every other readied item, and bare hands, leaves the attacker term as Dexterity,
so on the shipped starting weapon a character's Strength does not affect
accuracy at all. *(Established over the forty-eight-entry equipment id space.
The same selecting value also occurs at byte positions past the item tables,
which no readied slot can address.)*

**Always-hit cases, and who can reach them.** In the non-casting path the
always-hit set is three readied equipment ids - **Sword of Chaos, Glass Sword
and Jeweled Sword** - and the casting path has its own always-hit range of
action ids whose spell-level meanings are not established. **Neither is
reachable from the automatic actor driver**: both driver-side call sites pass a
fixed neutral item id, so a monster's ordinary attack can never short-circuit to
an automatic hit. Only the two player-side attack paths reach them, and the five
true missile items the ranged path gates on contain no always-hit id, so in
practice only a melee attempt delivers one.

**Boundary: an automatic-driver party attacker has a fixed score of 15.** The
neutral selector value is normalised on the selector's monster arm - that is
exactly what the `zero-selector stat row` trait test does - but there is no
matching normalisation on its party arm, and no party case matches the neutral
value. The helper then returns a stale value which, by the order of its two
calls, is precisely the defender rating it returned a moment earlier. The score
therefore collapses to `(D - D + 30) / 2 = 15`, and the attempt hits about
**50.8 %** of the time whatever either combatant's stats are. Monster attackers
are unaffected.

The one party-side route private analysis traces to this call site is the
**shipped traitor roster identity of Section 9**. Its controlled/charmed bit is
clear - that identity's override lives in the Section 9 team resolver, which
reads descriptor and roster bytes, not in the bit - so it reaches the automatic
driver on the *ordinary* attack path and presents the neutral item id there.
*(The arithmetic is established from the call sequence and the selector's own
case list. That this route reaches the call site end to end is **probable**: the
full path was not executed. A port that initialises the selector's fall-through
value, or that normalises the party arm the way the monster arm is normalised,
will silently diverge from the original for that actor.)*

The published boundary is therefore scoped to a party-side actor that reaches
the automatic driver **on the ordinary attack path**. The other party-side
actors Section 6.1a routes through that driver - Sword of Chaos compulsion,
monster possession, and Charm cast on a party member - are *not* published as
members of this set, for two separate reasons:

- **They do not take the ordinary attack path.** An actor carrying the
  controlled/charmed bit takes Section 6.1a's redirected fixed magic-strike
  branch instead of the ordinary weapon cascade, and that branch hands the
  shared attack primitive a fixed action id as the attack flavour. Whether that
  fixed id reaches the rating selector as the neutral value - and so whether
  such an actor's to-hit also collapses to 15 - is an **open question**, not a
  traced route. Published otherwise, Sections 6.1a and 11 would assert
  incompatible things about the same three actors.
- **The reachability of the bit itself is disputed.** Private analysis's
  encoding-level write scan found no reachable writer of the controlled/charmed
  bit and concluded these routes dead. This repository keeps Section 6.1a's four
  traced writers over that negative, because the scan's own stated residual -
  writes through a base register already offset into the descriptor, word-sized
  writes straddling the byte, and block copies - covers exactly the shape those
  writers take. The disagreement is recorded in `NEXT-STEPS.md` and is not
  resolved here.

Treat the controlled-bit routes as an unresolved second population rather than
as published members of the fixed-score set.

**Attempts per turn.** One attack per activation on the monster side: the
automatic driver reaches the attack path once, that path runs one target pick,
one to-hit and one damage resolution, and there is no multi-attack loop anywhere
on it. A class range byte smaller than the slot distance skips the attack
entirely, and melee is taken only at distance exactly one - any other in-range
distance routes to the ranged/effect path. On the party side an Attack command
produces **zero to three attempts**, one per readied helm, weapon-hand or
shield-hand item with a non-zero `Attack max`, body armour never scanned, or
exactly one bare-handed attempt when none qualifies (Section 8.2).

**Attempts per phase.** Attempts per *turn* is not attempts per unit of time:
the phase counter decides how often a turn comes round. An actor acts once every
`36 - base_step` sweeps of the thirty-two-slot walker (Section 7), and that
period is fixed at placement - except while the actor stands on a restraint
tile, the stocks or the manacles, where the round loop's per-actor skip precedes
the phase decrement, so the counter does not advance and the actor never comes
round at all (Section 7.1). A Bat, class speed 30, has a period of 6 at even
odds and 7, 8, 9 or 10 at one chance in eight each; a Dexterity-15 Avatar has a
period of 21. The expected number of Bat attempts per Avatar turn is therefore
`21 * E[1/period] = 3.01`, **not** `21 / E[period] = 2.90` - the per-bat rate is
linear in the reciprocal of the period, so the expectation has to be taken
there. An engine that models a round as "everyone acts once" understates Bat
pressure roughly threefold before any other difference is counted.

**Worked example: a Bat against the shipped starting Avatar.** The seed roster's
Avatar has Strength, Dexterity and Intelligence all 15, 60 of 60 HP, level 2, a
cached combat-defense byte of 7, and the shipped starting loadout. Bat is class
21: speed 30, attack 6, defense 0, 5 HP (`catalogs/monster-bestiary.md`).

*Bat attacking the Avatar.* The Bat's attacker rating is its combat weight, so
26 to 30 with 30 at even odds; the Avatar's defender rating is Dexterity 15. The
score is `(15 - W + 30) / 2` truncated.

| Bat combat weight | Chance | Score | Chance to hit |
|---:|---:|---:|---:|
| 26 | 1/8 | 9 | 0.705 |
| 27 | 1/8 | 9 | 0.705 |
| 28 | 1/8 | 8 | 0.738 |
| 29 | 1/8 | 8 | 0.738 |
| 30 | 4/8 | 7 | 0.770 |

**Per-swing chance to hit: `364/488 = 0.746`.** On a hit the Bat brings its flat
class attack value 6 and the Avatar's defence roll subtracts an inclusive
`1..7`, so the seven outcomes are equally likely:

| Defence roll | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---:|---:|---:|---:|---:|---:|---:|
| HP lost | 5 | 4 | 3 | 2 | 1 | 0 | 0 (negative; clamped) |
| Line printed | `<name> hit!` | `<name> hit!` | `<name> hit!` | `<name> hit!` | `<name> hit!` | `<name> grazed!` | `<name> grazed!` |

*(**Corrected.** The last cell of the HP row previously read "0 (negative;
narrated as a miss)". **That is withdrawn.** A landed swing that comes out at
zero or below prints `<name> grazed!` with the rising action-snap cue, not a
miss line and not silence, and it suppresses the party stats-panel redraw the
ordinary hit arm runs. Section 11.1 gives the whole outcome census and
`RETRACTIONS.md` R352 indexes the withdrawal. The arithmetic in this table is
unchanged: two of the seven equally likely defence draws still cost no HP. An
engine that copied this row prints a miss line on roughly two sevenths of
*landed* monster swings on top of the genuinely missed ones.)*

Five sevenths of landed swings therefore cost HP, the mean cost of a landed
swing is `15/7 = 2.14`, **a Bat can never take more than 5 HP in one swing and
cannot one-shot a 60-HP Avatar**, the expected loss per *attempted* swing is
`0.746 * 15/7 = 1.60` HP, and the chance that a given Bat swing costs the Avatar
any HP at all is `0.746 * 5/7 = 0.533`.

Two inputs the example is usually asked about turn out not to matter. The
Avatar's **level** enters neither the to-hit score nor the melee damage roll.
The **starting body armour** is inert in melee: the damage roll reads the cached
combat-defense byte and never the armour slot, the to-hit score reads neither,
and the Attack walker does not scan the body-armour slot at all (Section 8.2 and
`catalogs/item-list.md`). An asleep defender is not a certainty either - with
the defender rating floored to one the score is 2, 2, 1, 1 and 0 across the same
weights, giving **98.4 %**, not 100 %.

*The Avatar attacking the Bat.* The attacker term is Dexterity 15, since the
starting weapon is not in the strength family; the defender term is the Bat's
combat weight 26 to 30; the score is 20 to 22, and the per-swing chance to hit
is `18/61 = 0.295`. Damage is the ordinary `1..Attack max` roll for the readied
weapon, and the Bat's class defense byte is `0`, so **no defence roll is taken
at all** and nothing is subtracted - an engine that always rolls a defence term
both softens the hit and consumes a PRNG draw the original does not. With the
shipped weapon's `Attack max` of 15 against 5 HP, `11/15` of landed hits kill,
so one swing kills a Bat with probability `0.216`.

*Accuracy is not tier.* Because a monster's attacker rating is its speed-derived
combat weight unless its class carries the `zero-selector stat row` trait, a Bat
is *more* accurate against a Dexterity-15 party member (74.6 %) than a Gargoyle
is (60.7 %, taken off class tier 20). The Gargoyle compensates with attack 20
against 6 and defense 15 against 0. On defence the roles reverse: the same
Avatar hits a Bat 29.5 % of the time and a Gargoyle 60.7 % - numerically the
same figure as the Gargoyle's own accuracy, by coincidence of the two averages.

The item catalog now publishes the traced weapon-dispatch range/effect
rows; attack-time ammunition and breakage/consumption remain a negative
boundary shared with the item catalog. The traced combat attack stack does not
decrement arrows/quarrels, decrement a readied weapon's carried stock, or clear
the readied weapon slot for thrown/glass-family attacks. The separate traced
equipment-stock and readied-slot consumers do not add an attack-time ammunition,
thrown-stock, or glass-breakage path for the analyzed baseline.

**Ranged/effect attacks and Amulet/Turning.** Some monster and special-actor
classes carry a high per-class flag that marks their ranged or special attack
as turnable by Amulet/Turning. When such an actor targets a living party member
who has Amulet/Turning readied in the amulet/neck equipment slot, attack setup
rolls one byte in `[0, 255]`. On rolls below `128`, the ranged/effect helper is
forced into its scatter mode instead of using the ordinary hit-roll result.
Scatter mode picks a random adjacent impact cell around the intended target,
retrying until it is not the attacker's current cell, then resolves projectile
geometry and any impact at that scattered cell. Rolls `128..255`, attackers
without the flag, non-party targets, and party members not wearing
Amulet/Turning use the ordinary ranged/effect hit-roll path.

In the analyzed v1 data, the turnable-attack flag is set on Mage, Wanderer,
Blackthorn, Lord British, Sea Horse, Reaper, Gazer, Daemon, and Shadow Lord.
This is a combat-only passive equipment effect. R-Ready merely equips the
amulet; there is no U-Use activation, countdown, random disappearance, or
non-combat periodic effect tied to Amulet/Turning in the traced baseline.

The ranged/effect attack path is also data-driven by per-class metadata beyond
the visible Amulet/Turning trait. One class trait can route an attack into a
cast-like ranged/effect branch, rather than ordinary melee, when the combat
effect prerequisite state is active. That branch prints the cast/effect
narration, reuses the AI direction/effect dispatch, plays the ranged animation,
resets the scene state, and consumes the action. A separate scene-resistant
class trait is checked inside the ranged/effect helper against Negate Magic's
tag and the Crown's permanent code. When either code is active for a class with
that trait, the helper returns before projectile presentation, hit testing,
effect dispatch, damage, or status resolution. Its enclosing attack path still
reports the non-adjacent attack handled, so the actor silently spends that
attack action and does not fall through to melee or movement. This is checked
on each qualifying ranged attempt, not once per actor turn or round. Mimic
bypasses the ordinary resistance pre-gate while remaining
eligible for the later ranged/effect path rather than becoming melee-only.

Two neighboring one-byte side tables feed this family. The first is read by the
AI attack path as the per-class maximum attack range; if the slot distance to
the chosen target is greater than that byte, the actor consumes no attack. The
COMSUBS spell/weapon dispatcher reuses that same class-indexed byte as the
monster-side damage/effect selector, with value `1` treated as the zero-damage
sentinel that routes into the cast/effect branch. The second table is read as
the monster-side accuracy/effect payload: COMSUBS passes it into the
spell/effect dispatcher, while the COMBAT ranged helper passes it onward to the
cross-overlay ranged-effect resolver along with the hit-roll result and target
coordinate. These side-table bytes are class metadata, not hard-coded by
monster name, and not the eight-byte stat-record fields.

The control-flow contract above is public independently of table storage
details. `catalogs/monster-bestiary.md` publishes the clean per-class
ranged/effect side rows for the hostile and special classes, including the
range/effect selector, payload byte, scene-resistance row assignments, the
Gremlin cast-like branch row, and the Mimic pre-gate bypass row.

### 11.1 Attack outcome narration: what prints, on which side, in what order

This subsection is the complete printed-and-audible census of one attack
outcome in the arena, in both directions. It is published in full because two
things in this document were wrong in the same direction - Sections 11 and 12
called the zero-or-negative-damage outcome a printed miss, and Section 9
published an invented monster attack announcement - and an implementation built
on either narrates outcomes the original leaves silent. Both are withdrawn in
place; `RETRACTIONS.md` R352 and R353 index them.

**Two rules cover most of the census.**

1. **Every result line names the target, never the attacker.** No combat result
   line anywhere in the game is attacker-named. `Bat missed!` is a real
   original-game line, and it reads *the Bat was missed*: it is printed by a
   party member's failed swing **at** a Bat, never by the Bat's failed swing at
   the party. An engine that prints the attacker's name in the miss line
   produces a transcript that is wrong on every line it emits.
2. **The two sides join below the announcement layer.** A keyboard-driven actor
   prints its turn banner (Section 8.1), then `Attack-` and `Aim! ` per attempt
   (Section 8.2), before any roll. The automatic actor driver (Section 9) calls
   the shared helpers directly and passes through none of that. Both sides then
   share the to-hit roll, the impact presentation, the damage roller and the
   result narrator. The single most consequential result: **an ordinary hostile
   monster's melee miss prints nothing and sounds nothing** - no newline, no
   name, no line, no tone - while a party member's melee miss prints one line.

#### The census

`<target>` stands for the target's name: a party member's roster name field, or
the monster class's name. Lines are written the way the original emits them; a
line that ends **without** a newline is marked, because the next thing printed
continues on the same row.

| Outcome | Side | Printed, in order | Sound and visual |
|---|---|---|---|
| Swing begins | monster, melee and ranged | *nothing* | the swing sweep, played **before** the roll, running **downwards** (roughly 750 Hz toward 400 Hz) |
| Swing begins | party melee | **a newline, unconditionally, before the roll** | the same swing sweep in the opposite direction, roughly 400 Hz toward 750 Hz (`audio.md` section 7.4) |
| Swing begins | party ranged or thrown | *no newline here* | a descending sweep, roughly 1300 Hz toward 300 Hz, after `Aim! ` and a confirmed cursor |
| **To-hit fails** | **monster melee** | **nothing at all** | nothing beyond the swing sweep already heard |
| **To-hit fails** | **monster ranged or thrown** | conditional - see "the ranged carve-out" below | as the hit chain, in the cases where it narrates |
| **To-hit fails** | **party melee** | `<target> missed!`, following the newline already printed before the roll | **no sound at all** |
| **To-hit fails** | party ranged or thrown | conditional; when it prints, a newline then `<target> missed!` naming the **originally aimed** actor | none |
| To-hit fails on a cast issued from the combat command layer | party melee or ranged | `Failed!` - **with no name** - replacing the miss line entirely | none from this arm |
| **Hit lands** | both | a newline (the party melee path already emitted it before the roll) | **impact presentation runs first**: the impact tile is drawn on the target's cell; for a **party** target that member's stats row is flashed around a noise burst; for a **monster** target a noise burst alone, with a different noise setting and no flash; then a visibility pass. All of this precedes the newline and the damage. |
| Damage zero or negative | both | `<target> grazed!` **and nothing else** - the kill, sleep, hit and wound lines are all suppressed | the rising action-snap cue (`audio.md`, 1200 toward 2000 Hz) |
| Target dies | both | `<target> killed!` | no cue of its own; the party death arm runs a full stats redraw, the monster death arms write their tiles (Section 6.3) |
| Monster dies, vanish class | party attacker | `<monster> vanishes!` - **no trailing newline** - printed inside the damage handler, which then suppresses the kill line | none |
| Monster damaged, split class | party attacker | `<monster> divides!` inside the damage handler, and the ordinary result line **still** prints after it | none |
| Target slept or stoned | both | `<target> slept!` | none |
| Party target poisoned | monster attacker | `<target> is poisoned!`, printed **inside** damage resolution - after the hit newline and before the result line - and the ordinary result line is then suppressed | none |
| Ordinary landed hit, **party** target | monster attacker | `<target> hit!` - **flat and ungraded** | none |
| Ordinary landed hit, **party** target, attacker is a **Corpser** (class 45) | monster attacker | `<target> dragged under!` in place of `hit!` | the rising action-snap cue; the target is additionally marked asleep and its sprite blanked |
| Ordinary landed hit, **monster** target | party attacker | `<target>` plus one graded wound line - see below | none |
| Glass Sword swing | party melee | `Thy sword hath shattered!`, printed **inside** the damage roll, so it lands between the hit newline and the result line | none |
| Food-steal branch | monster attacker | a newline, then `A <monster> stole some food!` - this **replaces the entire damage and narration chain** | a rising cue roughly 800 Hz toward 2000 Hz, then a stats-panel redraw |
| After any narrated hit on a **party** target | both | *no text* | full stats-panel redraw and a visibility pass - **skipped on the graze arm and on the vanish arm** |

#### Order, stated once

For a landed **monster melee** attack, the sequence an engine must reproduce:

1. the swing sweep - already played, **before** the roll;
2. the impact presentation: impact tile, stats-row flash for a party target or
   noise burst for a monster target, visibility pass;
3. a newline;
4. damage application - which may itself print the poison line, the shatter
   line, the vanish line or the divide line;
5. the result line (`grazed!` / `killed!` / `slept!` / `dragged under!` / `hit!`
   / a wound grade), with a cue only on the graze and dragged-under arms;
6. for a party target only, the full stats-panel redraw and visibility pass.

A landed **party melee** attack is identical except that step 3's newline was
already emitted at step 0, before the roll. The **party ranged** and **monster
ranged** arms emit the newline at step 3, as monster melee does.

One tier narrates differently and is easy to get wrong: the per-turn standing
hazard reuses the same result narrator with **no newline before it at all**, and
with no attacker, so a party target on that tier always reads the flat
`<target> hit!` and never `dragged under!`. An engine that moves the newline
inside the result narrator - a natural simplification - emits one newline too
many on the hazard tier.

#### The ranged carve-out

A monster's failed **ranged or thrown** to-hit is not unconditionally silent, and
this is the one place where "a monster's miss prints nothing" must not be
generalised. On a failed roll the shot scatters: the impact point is drawn from
the three-by-three neighbourhood centred on the **aim cell**, redrawn only while
the draw lands on the **attacker's own** cell. The aim cell is therefore itself a
legal landing cell. The resolver then reports whoever occupies the landing cell,
and the **full hit chain runs against that actor** - impact presentation,
newline, damage, result line - whether that actor is a monster or a party member.

The attack stays silent in exactly three cases, the cases where the resolver
reports no occupant: the projectile pass fails, the landing cell is empty, or the
landing cell holds the acting slot itself. The resolver does carry a second test
that would turn a failed roll back into "no target", but it is guarded by the
cast marker, and the round walker clears that marker before **every** actor
dispatch, so an ordinary monster never reaches it.

The party ranged and thrown arm has the same gap, plus one extra rule of its own:
aiming at an **empty** cell forces the hit outcome, so no scatter happens and no
miss line prints. When the roll fails and the scattered shot lands on somebody,
the hit chain runs and the miss line is skipped entirely. The party miss line
prints only when the resolver reports nobody **and** the originally aimed cell
held a real actor - and it names that originally aimed actor, not the cell the
shot reached.

#### The graded wound lines are monster-target only

When a party attacker lands an ordinary hit on a **monster**, the result line is
graded by the target's remaining HP against its class maximum, using the same
four-bucket wound score the flee classifier of Section 9 computes:

| Wound score | Remaining HP against class maximum | Line |
|---:|---|---|
| 1 | below one quarter | `<target> critical!` |
| 2 | one quarter to just under one half | `<target> heavily wounded!` |
| 3 | one half to just under three quarters | `<target> lightly wounded!` |
| 4 | three quarters or more | `<target> barely wounded!` |

The quarter is the class maximum divided by four with truncation, and the three
thresholds are one, two and three of those truncated quarters, so the boundaries
sit slightly low for maxima that are not multiples of four. Because this is the
same classifier, a score of 1 - and a score of 2 on the morale draw described in
Section 9 - also raises the target's fleeing bit as a side effect of narrating
the hit.

The grading never applies to a **party** target: the classifier refuses a party
record outright, returning without producing a score at all, and its denominator
is a per-class maximum-HP row that a party record does not have. **A party member
who takes a solid landed hit always reads the flat `<target> hit!`** - or
`<target> dragged under!` when the attacker is a Corpser. Sections 11 and 12
previously did not mention the grading in either direction; this is a first
publication, not a correction.

#### Announcements: what each side prints before the roll

| Actor | Announcement |
|---|---|
| Party member at the command prompt | the full turn banner - newline, name, `, armed with ` and the readied item names or `bare hands`, a colon, newline (Section 8.1) - then `Attack-` and `Aim! ` per attempt, an item-name line when two or three items qualify, and `Nothing!` on a cancelled or empty melee confirm (Section 8.2) |
| **Ordinary hostile monster** | **nothing whatsoever** - no banner, no `Attack-`, no `Aim! `, no `Nothing!`, and on a melee miss no line either |
| Monster carrying the controlled/charmed bit (Section 6.1a) | the **reduced** banner - newline, name, colon, newline, with **no** `, armed with ` clause - then one fixed attempt: `Attack-`, `Aim! `, and on a failed roll `<target> missed!` |

**There is no `<attacker> attacks <target>` line, in any wording, anywhere in the
shipped game.** An exhaustive scan of every printable text run in the executable,
in every shipped overlay and in all four display drivers, filtered for the
word "attack" in either case, returns eleven strings; every one is a fixed prompt
(`Attack-`), a fixed refusal (`Nothing to attack!`), a fixed event line
(`Attacked!`, `Attacked at entrance!`) or a fixed command echo. None has an
attacker-and-target shape, and there is no verb composer that could build one at
run time from fragments.

#### Strings this document had not previously published

The following are exact original-game lines that the spec named only
descriptively, or not at all, before this revision: `<target> grazed!`,
`<target> hit!`, the four wound lines above, `<target> dragged under!`,
`<target> is poisoned!`, `<target> possessed!`, `<monster> escapes!`,
`<monster> teleports!`, `A <monster> stole some food!`, `<monster> reappears!`,
`<monster> disappears!` and `<monster> gates in a daemon!`. The last six are
printed on a self-acting monster's turn outside the attack chain: `escapes!`
with a rising cue on the arena-exit arm, `teleports!`, printed straight after the class name with no
newline before it, `possessed!` and the daemon-gate line each with their own
software envelope, and `reappears!` / `disappears!` on the blink ability with
**no trailing newline on either**. The already-published lines `missed!`,
`Failed!`, `killed!`, `slept!`, `vanishes!`, `divides!`, `interferes!`,
`Attack-`, `Aim! `, `Nothing!`, `Thy sword hath shattered!` and
`<name> passes out!` are unchanged.

Note that `Failed!` is not unique to combat: the shipped data image holds four
separate copies of that literal, and three of them belong to spell and dungeon
paths - two spell load sites and one dungeon load site. Only the combat copy is
the one described here, and it carries no sound of its own - the cast-failure
glissando `audio.md` documents belongs to one of the other three - established
by elimination, because neither caller of the combat copy is followed by any
sound call at all. Which of the three carries that glissando, and what the
remaining two print alongside, was not read.

#### Scope of the negatives in this subsection

Every corpus scan behind a negative claim here covered the shipped executable's
code image, every shipped overlay and all four display drivers; the GOG
installer's uninstaller is not game code and was excluded.

- **"An ordinary monster's melee miss prints and sounds nothing"** rests on a
  full read of the executed miss path and of its caller, which ignores the
  result either way. Established.
- **"The routine that prints a miss line has exactly two call sites, both inside
  party-side attack helpers"** rests on decoding every directly encoded near and
  far call at every byte offset of the corpus, resolved against
  descriptor-derived load bases and against every cross-overlay trampoline, plus
  the observation that no trampoline exports it at all. A call target computed
  at run time into a register would fall outside that scan. Note the scoping:
  *party-side helper* describes the routine, not the actor - Section 6.1a's
  controlled bit lets a monster reach it and lets a party member bypass it.
- **"There is no miss flag"** rests on a displacement scan for the shared result
  marker with both its writer and its reader sets closed: the bit in question has
  two writers, both the zero-or-negative-damage condition, and two readers -
  one prints the graze line with its cue, and the other is a wider test that
  halts the narrator before the kill, sleep, hit and wound chain and skips the
  party stats-panel redraw (the same test the vanish marker trips). Neither
  reader is a miss. A write through a base register already holding that
  address, or a word write straddling it, would not appear.
- **"No `<attacker> attacks <target>` string exists"** rests on the printable-run
  scan described above. A line assembled at run time from fragments none of which
  contain the word "attack" would not appear; the item-name composer used by the
  turn banner is not such a thing.
- **"Each narration line has exactly one producer"** rests on an immediate-load
  scan over all twenty-six combat narration strings, every hit re-decoded. It is
  a claim per *storage location*, not per spelling - see the `Failed!` note
  above. A string reached through a pointer table would fall outside it.
- **Probable, not established:** the reading of the party stats-row flash as an
  XOR flash rather than some other raster operation, and the identity of the
  impact-tile draw. Both were inferred from call shape, not read to the bottom.
  The absolute frequencies quoted for the swing sweeps and cues are inherited
  from the existing `audio.md` census rather than re-derived here; only the sweep
  **directions** were established in this pass, and the monster swing runs
  opposite to the party's. The impact noise burst likewise carries a **different
  setting** on the party-target and monster-target arms, but which perceptual
  axis that setting moves - pitch band, duration or loudness - was not
  established, so no engine should infer that one burst is louder or shorter
  than the other.
- **Not covered:** the spell overlays' own presentation around the shared result
  narrator, the standing-hazard tier's trigger conditions, the projectile pass
  that is one of the three ways a monster's ranged miss stays silent, and what a
  player can usefully do with a controlled monster once the prompt hands them
  one.

Source provenance: derived from private analysis in `../u5-decomp/notes/`.


## 12. Damage and status

The damage-and-status handler bundles "apply damage, update status, narrate the result, and handle special-class death effects" into one function. It takes a damage amount and a target slot.

**The ordinary attack damage roll.** Melee and ordinary weapon attacks reach the
damage-and-status handler through one shared roller that takes the attacker's
slot and the defender's slot and returns a signed amount. It runs in two stages,
and the two sides are not symmetric.

*Stage one, the attacker's raw value.*

| Attacker | Raw value |
|---|---|
| Monster | the class's **attack byte, used flat**, with **no random draw at all** |
| Party member | the readied action item's `Attack max` value; when that value is greater than `1` and is not the instant-kill sentinel `99`, it is replaced by an inclusive `1..value` draw. Values `0` and `1` pass through unchanged, and bare hands are a flat `1`. |

*(**Corrected.** Earlier revisions of this document, of
`catalogs/monster-bestiary.md` and of `formats/data-ovl.md` described the class
attack byte as a "cap" or "attacker-side maximum for ordinary monster attack
damage", which reads as an upper bound on a roll. **It is not rolled.** A Bat
brings exactly 6 every time. An engine that rolls `1..attack` for monsters
delivers about 39 % of the original's damage; see `RETRACTIONS.md` R336. The
party column keeps the `1..Attack max` roll `catalogs/item-list.md` already
publishes, which is unchanged.)*

Two per-item overrides run before the roll on the party side. The **Glass
Sword** id narrates `Thy sword hath shattered!` and substitutes the instant-kill
sentinel `99`; the **Jeweled Sword** id forces the raw value to `0` whatever its table
entry says. The sentinel short-circuits the whole roller and returns immediately
- **before the defender's defence byte is read** - so an instant kill takes no
defence draw. *(One residual on the Glass Sword arm: this document and
`catalogs/item-list.md` publish, as a traced negative boundary, that the combat
attack stack does not clear the readied weapon slot for glass-family attacks,
while private analysis now reads that arm as also clearing the readied slot.
That conflict is **not resolved here** and the published negative stands until
it is; it is recorded in `NEXT-STEPS.md`. An engine should treat readied-slot
consumption on shatter as an open question, not as settled either way.)*

*Stage two, the defence subtraction.* The defender's defence rating is the class
defense byte for a monster and the cached character combat-defense byte for a
party member. **When that rating is non-zero the roller subtracts an inclusive
`1..rating` draw; when it is zero it takes no draw at all and subtracts
nothing.** The defence term is a roll on *both* sides. Two consequences an
engine must honour: a flat subtraction of the rating instead of a roll is not a
near-miss but a different game (against the shipped party defence of 7 it makes
every Bat swing land for `6 - 7`, i.e. exactly zero HP, forever), and skipping
the draw on a zero rating is part of PRNG parity, not an optimisation - most
low-tier classes, Bat included, have defense `0`.

The result may be zero or negative, and **both are narrated as a graze, not as a
miss**. Against a **party** defender a negative result short-circuits early;
against a **monster** defender, and for a zero result on either side, it falls
through into the damage-and-status handler below, which clamps it to zero, and
the party attacker's experience-credit step still runs on the clamped value.
Both routes raise the same shared result marker, and two readers consume it:
the first prints `<target> grazed!` followed by the rising action-snap cue, and
the second - a wider test that the vanish marker also trips - stops the narrator
there, so no kill, sleep, hit or wound line follows and the party stats-panel
redraw that an ordinary landed hit runs is skipped. The two routes
are therefore gameplay-identical - one printed graze line and no HP change - and
differ only in whether the experience block runs.

*(**Corrected.** This paragraph previously said "the result may be zero or
negative, and both read as a miss", that a negative result against a party
defender "short-circuits with the miss narration", and that the two routes give
"a printed miss and no HP change". **The miss wording is withdrawn**; the
mechanical half - same marker, no HP change, experience the only difference - is
unchanged and confirmed. There is no miss flag: the marker bit raised here has
exactly two writers, both of them this zero-or-negative condition, and exactly
two readers - the one that prints the graze line, and the wider test that
suppresses the rest of the narration and the stats-panel redraw. See Section
11.1 and `RETRACTIONS.md` R352.)*

**Damage modifiers.** Negative damage is clamped to zero and the shared result marker's graze bit is raised, so the narration reads `<target> grazed!` and every later result line is suppressed (Section 11.1). *(**Corrected.** This sentence previously called that bit an "attack missed" status flag and said "the narration reads as a miss"; that is withdrawn - `RETRACTIONS.md` R352.)* A magic value (decimal 99) is treated as **instant kill** — bypass HP, force the death path; used for between-round death finalisation and one-shot-kill spell effects. Magic Missile and Fireball reach this handler only after the spell-damage wrapper rolls raw damage (`1..16` and `1..30`, respectively) and subtracts a random defense roll based on the target's combat defense; Kill/Slay Living reaches its death result only after the separate shared resistance predicate permits it and does not use that defense subtraction. For party-member defenders, the damage roll reads the cached combat-defense byte in the character record at offset `+0x18`; factory-seed records carry value `7`. This is not one of the stat bytes earlier in the record — Strength `+0x0C`, Dexterity `+0x0D`, Intelligence `+0x0E`. The original game also defines a separate per-item defence contribution keyed by readied equipment, plus a small bonus that Protection's shared `P` tag was meant to add on top of it, but neither ever applies: every one of the per-item accumulations is guarded by a comparison that is tautologically true and therefore always skipped, and the resulting total is never consumed — one caller discards it, and the other is reachable only through an attribute-selector arm that no call site in the game ever selects. No traced combat path recomputes the character-defense byte from readied armour. Treat the intended contribution as an original-game defect and a deliberate decision point for a port; do *not* generalise it into "worn equipment has no effect on combat". Body armour enters neither the to-hit score nor the damage roll, but the **readied item id is a real to-hit input**: exactly five ids - Spiked Helm, Spiked Shield, Club, Mace and 2H Hammer - switch the attacker term from Dexterity to Strength, and that is the only equipment input the to-hit score has (Section 11). *(An earlier revision of this sentence left the point open, saying "the surviving to-hit computation reads other character-record fields whose relationship to equipment has not been traced". Section 11 now enumerates every character-record field the score reads, so that hedge is resolved rather than withdrawn.)* The target's per-class flags are consulted: a "halve damage" flag halves *physical* (non-magical) damage; an "immune to physical" flag zeroes it.

**Monster status/effect attacks.** The attack resolver checks monster-only
status branches before ordinary melee damage. Classes with the poison/status
attack flag cluster get a random gate; on acceptance, the shared
party-status/damage helper runs instead of the default melee roll. The traced
reader tests this as a combined cluster before the random gate; current
evidence does not assign separate public meanings to the component bits.
Against a living party member whose status is Good, that helper flips the
character to Poisoned, narrates the poison result, marks the status-applied
combat feedback, requests the combat exit cascade, returns zero damage, and
does not award attacker experience. If the same helper is reached for a
non-Good party member or non-party target, it rolls a small raw damage value
and then delegates to the normal damage-and-status endpoint. Gazer attacks
have a separate stoning-style effect against awake defenders, and magic/effect
attack tiles can also enter
the same poison or stoning-style branches before falling back to ordinary
damage.

**Apply to HP.** For party members, damage is subtracted from the character record's HP word using the engine's saturating counter arithmetic; on death, the status byte is set to `'D'`, the active-player byte is cleared if this character was the active one, and a death-tile is written to the dynamic-objects table. For monsters, damage is subtracted from the slot's HP byte without wrapping through underflow; on death, control passes to the class-specific death paths.

**Special-class death paths.** Each monster class has a sixteen-bit flag word in a per-class table that encodes several death behaviours. Two of its bits gate the death branch: the low *incorporeal* bit and the *vanish-on-death* bit. When either is set, the death leaves the ordinary path entirely.

- **Vanish on death** (vanish bit set; Wanderer, Blackthorn, Lord British,
  Shadow Lord in the analyzed baseline) prints `<monster name> vanishes!`,
  writes the temporary marker and shared action-result suppression bit, restores
  the underlying terrain with the blocking 256-pixel reveal, releases the slot,
  and runs the party control/faint scan. Section 6.3 specifies the exact order,
  cadence, scratch-field lifetime, and the scan's mutations. *Corrected
  (2026-08-27): the former fade-out and post-turn-flush description is
  withdrawn.*
- **Incorporeal death** (low bit set, vanish bit clear; Sea Horse, Squid, Sea Serpent, Shark, Bat, Ghost, Slime, Insect Swarm, Wisp, Daemon) releases the slot immediately and leaves **no tile marker and no drop at all**. This is a distinct branch, not a variant of the default kill.
- **Special death transitions** for the Gazer (eye-burst tile on its own record, slot kept, and a **live class-31 Insect Swarm placed at the death cell** through the ordinary monster-placement mode, then a redraw) and the Gargoyle (lava-pool byte written into the arena terrain under the corpse, then the slot released with no corpse marker and no drop) are hand-written class exceptions taken only when neither class-flag bit above is set. The Gazer case is a real combatant, not a visual effect; § 6.3 carries the seeded values.
- **Default kill** applies to every other monster and is gated first on the arena terrain under the actor: the excluded terrain values release the slot with no marker. On accepted terrain the path runs two independent rolls against the class's drop-cap byte. If the first roll is within the cap, the active-object tile becomes the dead-monster/drop marker and byte five of that record stores **the class drop-cap value itself** (not a random amount); a second roll strictly within the cap ORs bit `0x80` into that byte as a special-drop marker. If the first roll exceeds the cap, the tile becomes the alternate no-drop death marker and byte five is left alone. Neither outcome releases the slot.

Section 6.3 carries the concrete tile bytes, the roll range, and the terrain gate. These markers live in the temporary combat-instance active-object table. The enter/exit framer restores the pre-combat world active-object table after the round loop, and the traced post-combat object reconciler edits only the original caller-supplied trigger slot. A compatible implementation must not turn arbitrary default death markers into automatic world loot.

Each monster killed computes a small raw reward unit (roughly a quarter of max-HP plus one). Combat-local attack and status/damage callers consume the damage handler's return immediately when the attacker is a living party actor: the returned value is added to the attacker's experience word with the normal `9999` cap. For non-kill hits, that returned value is the applied damage result; for a monster kill, it is the class reward unit. Hazard calls with no party attacker, poison-only status applications, and field-contact poison fallthrough do not grant this credit. Spell-side multi-target callers can also consume the returned unit immediately: Tremor adds it to the caster's experience word after each accepted actor, capped at `9999`.

The combat framer itself still restores the active-object snapshot and discards
the round-loop return except for victory/defeat/escape control flow. Ordinary
trigger-slot removal is handled by the resident caller-side reconciler described
in Section 4, not by the framer. No traced combat-exit path adds party gold,
applies a virtue delta, promotes arbitrary combat-instance drop markers, or
emits a separate victory bonus. Durable food/gold from a body-like combat
result is deferred to the ordinary Search/Get contract: the caller-side
reconciler may rewrite the original trigger slot into persistent body/retrieval
state, and later SJOG body rules stage plague, food, or gold from that object.

The traced COMBAT-to-SJOG calls do not supply any broader post-combat consumer.
Those calls are in-round command delegates (`G`, `J`, `O`, `S`, `K`), active
player or refusal helpers, out-of-arena/counting helpers, and per-turn combat
checks. They are not a sweep that converts combat corpse markers into durable
world loot after the framer restores the pre-combat active-object table.

**Splitting / replicating monsters.** Some classes (slimes, certain gargoyles) carry a "split on damage" flag. When such a monster is *damaged but not killed*, the function looks for an empty slot in the table, copies the parent's class byte into it, and prints `<monster name> divides!`. Up to eight attempts are made to find a free slot.

**Other status changes** — Sleep, Poison, Charm — are applied by separate
per-effect handlers (a poison-tick handler firing once per round, a sleep-effect
handler invoked when the Sleep spell hits). Sleep writes the character status
byte to `'S'` for party targets and descriptor byte 2 bit `0x08` for non-party
combat targets; non-party wake timing is the random own-turn wake check
described in Section 6.2, not a deterministic countdown. Those handlers update
the character status byte to `'S'` (asleep) or `'P'` (poisoned) and run their own
narration.
Inventory counters for carried equipment and use-items live in the same
resident save image and may be decremented by equipment or combat/spell helper
paths, but they are inventory stock, not combat effect timers. Do not
model the carried item counter band as a sleep/charm counter table.

**Equipped magic rings.** Combat reads the party equipment slots directly for
two ring ids. The shared worn-ring hook marks a Ring of Invisibility wearer
with the hidden/suppressed flag rejected by the target picker and changes the
linked presentation byte. On a Ring of Regeneration wearer, the hook invokes a
party-wide pass: every active non-dead member wearing that ring independently
has a 1-in-8 chance to recover 1 HP, capped at maximum HP.

**Ring effects run at seating and after committed non-digit actions.** During
encounter setup, each living, awake party member is seated and sent through the
worn-ring hook. Later, the combat parser's committed-action tail sends its
acting party-side slot through the same hook. A free refusal branches back to
input before this tail (Section 8), so repeatedly pressing `Q` or `X` cannot
farm regeneration rolls or refresh an effect boundary. This is action-tail
cadence, not an unconditional once-per-round sweep.

The separate 1-in-16 check that destroys a worn Ring of Invisibility or Ring
of Regeneration — printing `A ring has vanished!`, playing the short timed
sound, and clearing the first matching ring from that character's readied
equipment slots — is **encounter-entry-only**. It runs immediately before that
member is placed, so it can remove the ring before the seating-time effect hook.
It is not repeated by committed actions or by the round loop.

**Active-effect display counter.** Protection, Quickness, Mass Charm, and
Negate Magic install a single shared visible tag/counter rather than writing a
per-character status byte. A resident update helper ages this counter: zero and
255 are inert, other values decrement when the committed non-digit action tail
runs, and expiry clears the visible tag and requests a redraw. One early
active-player denial route enters the same maintenance endpoint directly. This
counter is not the time system's
torch/light-spell counter; do not model it as one decrement per minute or per
full actor-table sweep. Negate Time's `T` tag uses the same counter shape, while
the per-turn clock cleanup only observes `T` to skip minute
advancement. Inside an arena the `T` tag has one further consumer of its own:
the automatic actor driver returns immediately when it is set, so every
self-acting actor's turn is skipped for as long as the tag lasts (Section 9).
The tag is not display-only.
Protection's `P` tag has no effective consumer: the defence bonus it was meant
to add rides on a per-item defence total that is both unreachable and never
read, so Protection changes no combat number. Combat damage reads the cached
party defense byte instead.
Quickness's `Q` tag randomly gates the automatic actor driver with a 0..1 roll,
so self-acting actors act about half as often while it runs and the player's
own command prompt is untouched (Sections 8 and 9); Mass
Charm's `C` tag lets the AI target picker roll against the acting monster's
selected threshold and, on success, treat that slot as party-aligned group 0
for that target pick only (ordinary monsters select the class threshold; the
reachable controlled party-side case selects linked-member Dexterity); Negate
Magic's `N` tag absorbs party combat casts
before the shared spell dispatcher spends charge or MP and also feeds the
class-special, teleport, and scene-resistant ranged/effect checks specified in
Sections 9 and 11. Three different things can put
a `C` on screen and none of them is a "casting" state: the character status
byte's `C` letter means *charmed* (see the status-byte paragraph below), the
shared active-effect `C` tag above is Mass Charm's timed tag, and the stats
panel's in-combat `C` is a presentation override driven by the
controlled/charmed descriptor bit (Section 6.1a). Earlier revisions of this
document glossed the status-byte `C` as "casting"; that reading is withdrawn.
The exact
number of decrements per full actor-table pass depends on which command/AI
paths run, so per-round parity remains tied to actor dispatch.

The character status byte is the load-bearing summary value. Shipped new-game
and gameplay paths write `'G'` good, `'P'` poisoned, `'D'` dead, and `'S'`
asleep. The `C` the stats panel shows during combat is not read from this byte:
it is a presentation override driven by the controlled/charmed descriptor bit
(Section 6.1a), and the Charm spell writes `'G'`, never `'C'`, into a party
target's status byte. Ashes `'A'` has no shipped producer, though an external,
edited, or legacy U5 save can supply a byte that the verbatim save/load path
preserves. *Corrected:* an earlier revision listed `'C'` and `'A'` alongside the
four written letters as though all six were gameplay-produced states; that
framing is withdrawn. `formats/saved-gam.md` owns the complete reachability and
compatibility rule. Other systems read the byte to decide whether the character
can act, can be selected as active player, or counts toward the party-defeat
check.

## 13. Per-monster-class data

Several aspects of combat behaviour are driven by per-class tables that the spawning, AI, and damage paths all consult — small fixed-stride arrays in the data segment, indexed by monster class byte.

| Table                            | Purpose                                                                                                                                          |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Combat-class spawn-count byte    | The default spawn count field of the eight-byte class stat row, indexed by the encounter's base class id (never by the arena index). Combined with the random reroll it decides how many monsters spawn; the largest shipped value is sixteen. |
| Per-class companion class        | Forty-eight entries indexed by class id, values are class ids. Early spawned monsters roll a one-in-nine chance to be created as the base class's companion class instead of the base class. Published in `catalogs/monster-bestiary.md`. |
| Per-class flag word              | Sixteen bits per class. Includes split-on-damage, halve-damage-when-physical, immune-to-physical, the zero-selector stat-row select (**corrected 2026-08-23** from "faction-override"), vanish-on-death, special death checks, the turnable-attack flag consumed by Amulet/Turning, ranged/effect branch selection, the magic-immune ranged/effect gate, teleport-capable movement, and the turn special bits for possess, blink/phase, and summon-daemon. |
| Ordinary AI helper state         | Not a class script table. Ordinary monster decisions use the combat actor/effect records, target-selection scratch, per-class flag/stat tables, and shared helper outputs such as the AI step vector. Slot-local position, target, phase, flee, and visibility data remain in the combat actor/effect tables. |
| Per-class display/narration data | Pointer data used by combat narration and class labels; this is not an AI behavior table.                                                        |
| Per-class stat record            | Eight bytes per class: combat tier, speed seed/base-step input, endurance rating, defense rating, attack value, maximum HP, default spawn count, and default kill/drop cap. Maximum HP initializes monster HP and supplies the reward-unit input. The attack and defense bytes are consumed by the ordinary damage roller (Section 12), and this row is not a flat damage/hit lookup matrix. **Which of these the shared actor-rating selector actually returns is narrower than earlier revisions said** - see the correction below the table. |
| Per-class name pointers          | Sixteen-bit pointers per class to the printable monster name strings.                                                                            |

*(**Corrected.** The stat-record row above formerly read "the tier and endurance
bytes are the two class-side ratings the shared actor-rating selector returns
into the to-hit and resistance scores", and formerly named the attack byte an
"attack-damage cap". Both are withdrawn (`RETRACTIONS.md` R336 and R337). The
selector has four class-side arms, not two, and for an **ordinary melee to-hit**
it returns the actor's per-actor **combat weight** in every case except the
classes carrying the `zero-selector stat row` trait, which supply the **tier**.
The **endurance** byte is the monster-side rating of the *resistance* predicate
(Section 9), not of the ordinary to-hit score. The **defense** byte is read
directly by the damage roller and never reaches a score through the selector at
all - the selector has an arm that would return it, but no call site in the game
selects that arm. And the **attack** byte is used flat on the monster side, not
as the ceiling of a roll. The "chest/encounter team-flip" reading of the tier
and endurance bytes remains withdrawn from the revision before that.)*

A monster's class id is set at spawn time and never changes (death may cause a tile swap, but the class stays). The forty-eight-row class space is shared: classes 0-3 are the four human party sprites (Mage, Bard, Fighter, Avatar), classes 4-15 are townsfolk and special NPC actors, and classes 16-47 are the bestiary. Note that the descriptor's owner/target/class field is overloaded: for a seated party member it holds the character's roster slot index, and only for monsters and objects does it hold a class id. The AI's friend/foe filter relies on the descriptor faction tag and the slot index range rather than on that field alone.

The 48-row stat table boundary is part of the public combat contract: party
combat classes, special NPC classes, and monsters share the same eight-byte row
shape. The ordinary friend/foe filter uses the combat slot index range and
descriptor faction tag rather than a separate class-family table.

The grouping helper therefore combines actor-family defaults read from the
**descriptor** bytes with the single hard-wired hostile roster template
described in Section 9, rather than consulting a separate faction table.
*Corrected 2026-08-23:* this paragraph previously said the helper combines
"descriptor flags bit `0x40`" with "the per-class team-override flag from the
monster's class flag word". Both are withdrawn - the helper's first test is
descriptor bit `0x20`, and it never reads the class flag word; see the
correction in Section 6.1a for what that flag bit actually does. That
last override is guarded so that it can never apply to the player's own
character.

## 14. Victory, defeat, and escape

Combat ends when the post-action side recount reaches a terminal table state.
Victory narration, individual edge departure, and Escape-key cleanup are
distinct transitions rather than three interchangeable exit flags.

**Victory.** When every hostile actor has been killed (no non-party slot has the
"alive and active" flag bits set), the round loop prints the resident combat
string `VICTORY!` through the ordinary string printer. The census that decides
this counts every descriptor that is non-empty and not dead-marked, with **no
terrain filter**, so a hostile standing on a restraint tile - which never takes a
turn (Section 7.1) - still holds the hostile count above zero and suppresses the
announcement until it is freed or killed. The stored string has one
leading and one trailing newline, and a one-shot guard prevents a duplicate
announcement. The announcement does **not** return from combat. Party actors
remain in the arena and cleanup continues until they walk out with `Leave!` or
the player invokes the now-accepted Escape-key sweep. An earlier revision said
the loop exited with result one immediately after victory cleanup; that is
withdrawn.

After `Leave!` departures or the Escape sweep empty both sides, the round loop
returns word zero and the framer restores the suspended
world state, refreshes party stats, and returns to the calling mode. Combat
death paths may have produced temporary loot markers and a raw reward unit while
the combat-instance tables were live, but the traced framer does not merge those
active-object bytes into the restored world table or propagate the helper's
return value as a post-combat award. The traced SJOG calls reached from COMBAT
are command-time delegates and per-round helpers, not an after-victory
loot-conversion pass. Ordinary terrain-trigger removal happens after the
framer, in the resident caller that invokes the post-combat object reconciler
for the original trigger slot. This settles the combat-exit boundary: ordinary
attack/spell experience can be credited before the framer restores the world,
the original trigger slot can be cleared or rewritten by the caller-side
reconciler, and any body-like food/gold result belongs to later Search/Get
interaction with that rewritten slot. Arbitrary combat corpse markers, party
gold, karma, and any victory bonus are not automatic framer outputs.

**Defeat.** When no party-side actor remains while at least one foe does, the
engine first runs the party control/faint helper. If it cannot restore an actor,
the engine prints `BATTLE IS LOST!` from the resident combat string pool and
returns word `1`. That stored string begins with a newline and has no trailing
newline before its terminator. The same terminal branch is reached when the
last party actor successfully flees while foes remain, so that actor's
`Escape!` line is followed by the loss line. An earlier revision called this
return word zero and treated one as victory/escape; that polarity is withdrawn.
The framer discards the word.

There is no command that reaches the defeat exit deliberately: an earlier
revision of this section described combat `Q` as an abandon-party command that
did so, and that is withdrawn — the combat parser refuses `Q` like the other
meaningless verbs (Section 8). What happens next is not decided by combat:
control returns to the exploration loop that framed the fight, and that loop's
next per-turn party-capability check sees the result. A wipe with nobody left
able to act and nobody asleep runs the rescue/refuge cinematic specified in
`systems/blackthorn.md` Section 7 — which restores the party and resumes play at
Lord British's Castle, so an ordinary wipe is not a terminal game-over. A wipe
that leaves a sleeping member instead simply passes turns until someone wakes
or dies.

**Edge departure.** Moving outside the arena reaches the geometric edge helper
specified in Section 3. A successful attempt removes only the acting actor and
prints `Escape!` while foes remain or `Leave!` after they are gone. Remaining
party members and monsters continue to receive turns, so further blows are
possible after a party member flees. If the last party actor leaves while foes
remain, the subsequent side recount prints `BATTLE IS LOST!` and returns word
one. The previous claim that the first accepted edge ended combat immediately
is withdrawn.

The Escape key uses a distinct cleanup handler and always prints the bare prefix
`Escape` first. Contrary to the earlier contract, its table scan does **not**
look for foes. It looks for any party-side descriptor whose marked-dead bit is
clear. Its exact branches are:

- If such a party-side descriptor exists and the encounter mode's high bit is
  set, append `-Not here!` plus a newline and re-prompt the same actor at no
  cost. The complete line is `Escape-Not here!`.
- If such a descriptor exists in an ordinary mode and the one-shot exit
  announcement has not yet happened, append `-Not yet!` plus a newline and
  re-prompt at no cost. The complete line is `Escape-Not yet!`.
- If the ordinary-mode exit announcement has already happened, or if no
  qualifying party-side descriptor exists, accept cleanup. Append the single
  character `!`, producing `Escape!`; this handler appends no newline after it.

Accepted cleanup sweeps the thirty-two combat descriptors and the thirty-two
combat-instance active-object records, advancing one world tick after each
occupied slot it clears. It then plays a rising PC-speaker glissando and marks
the stats panel for repaint. This presentation is separate from the round
loop's `VICTORY!` / `BATTLE IS LOST!` narration above. The later committed-action
ring hook sees the already-cleared acting descriptor and is therefore inert.
The `X` letter does not reach this handler at all — the combat parser produces
`X-it what?` and re-prompts (Section 8).

The framer's restore phase is independent of which terminal table state caused
the round loop to return. It restores the exact pre-combat X, Y and Z; no arena
edge coordinate or chosen exit direction becomes a world coordinate. It also
restores the complete pre-combat active-object snapshot, so individual actor
departures are combat-local. Any persistent ordinary encounter-trigger rewrite
is the caller-side reconciliation after the framer. Combat time advances from
the round loop's round-counter wrap, which fires the per-turn cleanup with a
one-minute increment; a separate one-minute exit increment is not part of the
currently traced framer restore.

## 15. Hooks into other systems

Combat is built on top of several other systems and integrates cleanly with each.

- **Text output.** All combat narration flows through the per-cell emitter and wrap-aware string printer described in `text-output.md`. Combat does not maintain its own text window; it writes to whichever window was active before the fight.

- **Input.** The player command handler reads via the same wait-for-input routine described in `input.md`. The scene byte is set to the combat sentinel during the fight, so the world-tick step is suppressed; the cursor blink is the only background animation. Free-text and Y/N prompts within combat use the same prompt-mode mechanism.

- **Time.** Combat advances time at one specific point — when the round counter wraps inside a round (corresponding to one full actor walk under typical game pacing). The wrap fires the per-turn cleanup with a one-minute increment, exactly as the town and dungeon loops do.

- **Rendering and tile effects.** Combat contributes no render pass of its own.
  The shared viewport rasterizer that paints every other mode also paints the
  arena, driven by the idle redraw tick rather than by the round loop, and its
  only combat-specific work is blinking the player cursor and optionally
  drawing a secondary marker (Section 7). It applies no hazards and is not the
  ownership point for placed-field lifetime; field markers persist until combat
  exit unless an explicit command or spell removes them.

- **Spell system.** Combat shares the single player/party spell dispatcher
  described in `magic.md`. Combat-specific gates wrap the dispatcher's call
  from within the combat C-handler. Monster turns first pass through AI intent,
  target selection and a direction choice, then call the shared attack and
  movement primitives directly; they do not enter the combat command parser
  (Section 9, `RETRACTIONS.md` R353).
  The decoded class-flag special hook may possess, blink/phase, or
  summon-daemon before ordinary movement. These branches are separate from the
  player spell table, premixed charges, MP, reagents, and circle gates.

- **Visibility.** The arena's visibility model is similar to the world model but uses the combat terrain grid rather than the world map. Each cell ends up with one of the standard visibility byte values, and the renderer composites actors over those values.

- **Save image.** Character HP, MP, and status bytes are part of the persistent save. Combat itself cannot be saved mid-fight, but a fight's after-effects are persisted. Combat's swap-and-restore mechanism ensures the saved dynamic-objects table is the world's, not the fight's.

## 16. Combat Boundaries And Class-Flag Policy

The combat contract is complete at loop/framer depth: entry modes, actor
rounds, command dispatch, target selection, ordinary AI, damage/death,
experience credit, active-effect consumers, field contact, terrain/effect
maintenance, escape/victory exits, and post-combat reconciliation boundaries are
specified. Class flags are public at behavioral-trait depth; component bits
without independent behavioral consumers remain opaque metadata.

- **Per-class flag word policy.** The common combat flag
  consumers are decoded: damage modifiers, the poison/status cluster,
  ranged/effect branch selection and resistance gating, the zero-selector stat-row select (**corrected 2026-08-23** from "faction override"),
  death behaviour, target selection, the turnable-attack branch used by
  Amulet/Turning, teleport-capable movement, and the possess/blink/summon-daemon
  turn hook. The decoded row assignments for the published traits are in
  `monster-bestiary.md`. Component bits that only appear as part of a combined
  cluster, or that are not reached by traced readers, are not assigned separate
  public trait names. They should be preserved as opaque metadata only by tools
  that retain the original class-flag table; gameplay implementations should
  use the published traits and side rows as the behavioral contract. This is
  not uncertainty in the neighboring eight-byte class-stat row boundary.

- **Per-class flag publication.** The vanish-on-death,
  poison/status attack, monster-turn special, turnable-attack, and
  teleport-capable movement assignments are public in `monster-bestiary.md`.
  The ranged/effect branch semantics are specified above, and the class
  side-table values are published in the public catalog. No separate public
  component-bit labels are required for the analyzed baseline beyond those
  behavior traits.

- **The encounter-size damper — closed.** The flag that causes the spawn count
  to be re-rolled (Section 5) has no gameplay setter because it never had one.
  It is a saved-game byte that the factory new-game template ships switched on,
  and the only write in the engine is the clear performed at the calendar-month
  rollover. Sleep ambushes and scripted encounter families are not producers and
  must not be modelled as such. The remaining uncertainty is a formality: a
  write through a computed pointer cannot be excluded by static means alone, but
  nothing in the traced control flow suggests one exists.

- **Wait commands in combat.** Space is "pass". Best evidence is "advance the actor's phase counter past zero so it does not act this round but does not lose its position in the table." Implementers should treat Space as "no movement, no attack, end the actor's turn cleanly".

- **Combat command branch bodies — closed.** Every letter's delegate and every
  letter's turn cost are exact (Section 8): two shared shapes, a handful of
  direct calls, and one re-prompt flag. Two earlier claims are withdrawn there —
  combat U-Use does enter the item-use flow, and combat X-it is refused outright
  rather than escaping the fight. What remains is interior detail rather than
  routing: the combat-mode branches inside the shared Get, Search, Klimb, Yell
  and member-select delegates are surveyed but not enumerated one branch at a
  time. Jimmy's combat-specific restraint result is now exact in Section 8.
  Two are settled negatively — the shared Open handler and the escape
  handler carry no combat-specific branch at all, so they behave in an arena
  exactly as they do on the surface.

- **Post-combat loot boundary.** Current COMBAT-to-SJOG call coverage does not
  include an after-victory loot sweep. The resident terrain-target caller has a
  traced post-combat object reconciler for the original trigger slot, so
  ordinary trigger removal/body rewriting is no longer an open framer gap.
  Temporary combat death markers outside that original slot remain non-durable
  and cannot be treated as automatic world loot, gold, karma, or a separate
  victory bonus. Gold/food from a rewritten body-like slot is obtained only
  through the later Search/Get body rules in `containers.md`.

- **Multi-target spells.** Several combat spells are AOE or multi-target effects (Tremor, Poison Wind, Death Wind, Flame Wind). The effect-dispatch mechanism handles them by walking the actor table and applying the spell to each cell in the AOE; per-actor effect application can reuse the damage-and-status handler. Tremor's loop is exact at public semantic depth: no faction filter, target-only combat-weight acceptance (`roll >= weight`), 1..20 damage per accepted actor, shared damage/status application, and returned reward credited to caster experience. The separate active-target attack wrappers are also exact at public semantic depth: Magic Missile rolls 1..16 and Fireball rolls 1..30. Kill/Slay Living uses a creature target and the shared resistance predicate before applying its death result. The directed wind-cone family prompts for a cardinal direction and builds the widening clipped cone specified in `systems/magic.md`, with up to 63 de-duplicated arena coordinates. The shared scan de-duplicates actors and skips common empty/status-masked records, but neither that scan nor the Sleep/Poison Wind/Death Wind/Flame Wind per-effect branches run the friend/foe lookup or reject same-faction actors. Sleep runs the shared resistance predicate before applying party sleep status or descriptor byte 2 bit `0x08` for non-party targets. Poison Wind uses the distinct target-only combat-weight gate before poison status. Death Wind runs the shared resistance predicate before using the decimal 99 instant-kill sentinel, and Flame Wind rolls raw 1..30 damage; the two damage winds credit returned monster-kill reward units to the caster with the normal 9999 cap. Mass Charm is now covered as a class-threshold active-effect target-selection remap rather than an actor-table damage/status scan. Field contact runs from the common post-dispatch hook for the current actor slot, not from a successful-step-only hook. Its scan skips the current descriptor's linked renderer record, not the current actor as target, so a separate colocated Poison, Sleep, or Fire marker affects that actor. Poison's accepted Good-party status arm consumes no randomness; its damage fallback rolls raw 0..20 with no defense draw. Fire rolls raw 0..10 with no defense draw. Energy is a blocking marker and has no contact payload in this hook. Before that scan, exact arena bytes for swamp, molten lava, and fireplace select the Poison or Fire result and suppress marker scanning. Doom absorption is a separate committed-action predicate over the renderer companion band, not arena terrain or a common-hook marker. The same terrain/field rule follows both player and AI dispatch, and contact does not consume the marker. Field markers persist until combat exit restores the pre-combat active-object table.

- **Status narration.** "Sleep!", "Poison!", "Charm!" lines are not produced by the damage-and-status handler. They live in separate per-effect handlers (one per status). The exact wording and trigger mechanics belong in those handlers' specs.

- **Active-effect side effects.** The shared display counter for Protection,
  Quickness, Mass Charm, and Negate Magic is now traced through cast setup and
  the counter-aging boundary. Combat distinguishes that path from the
  time/render cleanup on ten-ready-action wraps; zero and 255 are inert, other
  values decrement at the reached cleanup endpoints, and expiry clears the
  shared tag and requests redraw. Negate Time's `T`/10 runtime tag uses the same
  counter shape, but the clock cleanup only observes `T` to suppress minute
  advancement. Confirmed consumers are the equipped-item statistic helper's
  Protection `P` bonus, Quickness's `Q` 0..1 gate and Negate Time's `T`
  outright skip at the head of the automatic actor driver, Mass Charm's `C`
  class-threshold AI-target remap, and Negate Magic's `N` party-cast
  absorption plus the three enemy-side automatic-action checks specified in
  Sections 9 and 11. The `Q` gate was previously attributed to the player
  command handler; it is on the automatic driver, which is why it slows
  hostiles rather than the player (Sections 8 and 9).

- **Flee mechanics.** The monster wound-score morale classifier is the per-turn
  morale writer of the fleeing flag, and Cause Fear is a spell-side writer that
  drives accepted hostile targets to combat HP one and sets the flee bit itself,
  after which the classifier keeps re-asserting it from that critical-HP state. Repel Undead is the same critical-HP flee
  setup restricted to monster-side actors whose class carries the undead flag,
  excluding the three protected special classes 14, 15 and 47; it writes the HP counter and the flee bit `0x02` and does not
  touch the controlled bit `0x01`. The no-target centre fallback also
  writes the flee flag and critical-HP marker for eligible monster-side slots.
  Section 9 specifies how the flag reverses movement. The out-of-arena leave
  helper is specified above. The decoded possess/blink/summon-daemon hook does
  not set the flee flag.

- **Monster special-action variants.** The monster-turn path proves the
  class-flag special hook, shared target selection, phase/hidden/invisibility
  filters, no-target fallback, movement-vector choice, and direct reuse of the
  shared attack, movement and special-ability primitives - not command
  synthesis and not parser reuse (Section 9, `RETRACTIONS.md` R353). The v1
  baseline assigns possess, blink/phase, and summon-daemon rows as listed in
  `monster-bestiary.md`. Keep branch ordering
  data-driven for variant assets that set more than one turn-special trait.

- **Ordinary AI edge labels.** The old "class script runner" hypothesis has
  been removed. The step-permission, step-validity, fallback-target, and
  no-target cleanup paths are now specified as surrounded checking, in-arena step
  testing, per-turn fallback, and pending-action marking. The target-picker
  suppression-filter exceptions are now labelled as Doom and Shadow Lord, and
  the centre fallback's flee-bit writer is specified above.

- **Round counter wrap at ten.** The per-round counter wraps at ten and fires a tile-render on every wrap. Likely a "render every N actor-turns" cadence balancing CPU cost on original hardware. A modern implementation can treat it as "redraw every frame" without preserving the cadence.

- **Faction edge cases — closed.** An exhaustive census found no additional
  reachable class-specific faction remaps. Section 16.1 gives the complete
  placement map, runtime overrides, downstream effects, and verification
  vectors.

- **The thirty-two-slot table size.** Plausibly: six party slots + sixteen monster placement slots + ten "dynamic" slots for replicated/summoned creatures. The round walker's "less than thirty-two" test is the only hard upper bound.

### 16.1 Exhaustive Faction And Remap Closure

Combat has two acting sides plus a passive descriptor form. Group 0 is
party-aligned and group 1 is hostile-aligned. Passive actors are filtered before
the side comparison; if their descriptor is nevertheless passed directly to
the group resolver, it yields group 0, but that fallback does not make them
party actors.

The complete placement map is:

| Placement source | Class or identity | Initial faction state | Randomness and prerequisites |
|---|---|---|---|
| Monster placement | Class 8 (Pirate) or class 9 (reserved) | Passive/nonacting descriptor tag `0x20` | Deterministic after the final class is chosen. |
| Monster placement | Every other class: `0..7` and `10..47` | Ordinary hostile descriptor tag `0x40`, group 1 | Deterministic after the final class is chosen. An earlier spawn stage may independently replace the encounter class with its companion class on a one-in-nine draw; the resulting class is then mapped by these same rows. Placement-speed randomness has no faction effect. |
| Party placement | Any seated roster member | Party descriptor tag `0x80`, group 0; an independently applicable disabled-state bit may also be present | The descriptor's owner field is a roster index, not a combat class id. No faction draw occurs. |

Those base tags have only the following reachable runtime remaps or overrides:

| State or effect | Resolved group | Scope |
|---|---|---|
| Controlled/charmed bit on an ordinary party descriptor | Group 1 | Persistent for that combat descriptor until the bit is cleared or combat ends. |
| Controlled/charmed bit on an ordinary monster descriptor | Group 0 | Persistent for that combat descriptor until the bit is cleared or combat ends. |
| Shipped traitor roster identity | Group 1, with or without the controlled bit | Roster-identity exception for a party descriptor; it is not a class remap and cannot be triggered by a player-chosen name. |
| Active Mass Charm and `roll > threshold` | Group 0 | Local to one target-picker call. The descriptor and its ordinary group remain unchanged. Ordinary monster-side actors use the class charm threshold; the reachable party-side automatic case uses the linked member's Dexterity. |

No per-class faction-override flag exists. The former candidate flag is only a
stat-selector trait and is not read by faction resolution. Once group identity
is known, its downstream effects are exact:

- Target selection first removes empty, dead, passive, suppressed, or invisible
  candidates as applicable, then rejects candidates in the acting slot's group.
- The round walker sends group-1 actors to the automatic action driver. Group-0
  actors enter the combined command handler; it prompts only for an eligible
  selected party member, while a monster descriptor that control moved to group
  0 still synthesizes an automatic action.
- Side counting skips empty, dead, and passive descriptors, then uses the same
  group resolver. Group 1 counts as foes and group 0 as friends. Control and the
  traitor identity therefore affect victory detection. Mass Charm's local
  target-picker override does not.
- Faction does not remove physical occupancy. Ordinary occupied cells either
  block movement or become attack destinations according to the normal
  same-group/opposite-group rules. Classes 8 and 9 retain an active object and
  reject movement into their occupied cell even though their passive descriptor
  is not a target.
- Combat descriptors and controlled bits are encounter-local and there is no
  mid-combat save. Base tags are rebuilt at the next placement. The shared Mass
  Charm effect tag and counter are save-backed and can remain active into a
  later fight; the traitor's roster identity is also save-backed. No per-actor
  local Mass Charm remap is serialized.

Conformance vectors:

| Setup | Required result |
|---|---|
| Place monster classes 7, 8, 9, and 10 | Initial tags are respectively `0x40`, `0x20`, `0x20`, `0x40`; resolved groups are 1, 0, 0, 1. Classes 8 and 9 are skipped for action, targeting, and side counts, leaving two foes, but all four occupied cells reject movement. |
| Compare ordinary and controlled descriptors | Party `0x80` resolves to group 0 and controlled party `0x81` to group 1. Monster `0x40` resolves to group 1 and controlled monster `0x41` to group 0. No random draw occurs. |
| Mass Charm with threshold 0 | Roll 0 leaves the ordinary group unchanged; roll 1 locally supplies group 0. In both cases the descriptor stays `0x40` and side counting still sees a foe. With threshold 255, no roll remaps. |
| Resolve the shipped traitor roster identity | Party descriptors `0x80` and `0x81` both resolve to group 1. |

## 17. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The exhaustive faction/remap census, including placement tags, group
  resolution, automatic dispatch, occupancy, side counting, Mass Charm's local
  override, and the roster-identity exception, is derived from private analysis
  in `u5-decomp/functions/ULTIMA_EXE/`,
  `u5-decomp/functions/COMBAT_OVL/`, `u5-decomp/functions/SJOG_OVL/`, and
  `u5-decomp/notes/`.

- The status-byte producer boundary, including the absence of an Ashes writer,
  is derived from private analysis in `u5-decomp/notes/` and the status-owning
  overlay directories under `u5-decomp/functions/`.
- Terrain-combat entry chain retrace of 2026-08-22 - outdoor arena selection from
  world terrain plus ship state, the class-id derivation and its separation from
  the arena index, the reachable spawn-count invariant, the forty-eight-entry
  companion-class table, and the party-seating pass that runs before monster
  placement. Source provenance: derived from private analysis notes
  `../u5-decomp/notes/`,
  `../u5-decomp/functions/ULTIMA_EXE/`, and
  `../u5-decomp/functions/ULTIMA_EXE/`.
- The combat enter/exit framer with its three-way entry-mode dispatch, save-and-restore of player position and the dynamic-objects table, the scene-byte sentinel, and the post-combat active-player check — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The combat-exit tile-graphics restoration dispatch reached from the framer's
  sampled restoration flag -- derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The terrain-combat setup, the class-row spawn-count lookup, the
  fifteen-transposition placement-slot branch in the terrain helper, the early-spawn
  companion-class roll, and the single-attacker town-style override — derived
  from `u5-decomp/functions/ULTIMA_EXE/`.
- The combat monster-placement writer that initializes renderer-facing and combat descriptor records -- derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The ambush/camp-attack reveal-slot helper, including mode gating, one-shot
  reveal-coordinate consumption, arena terrain stamping, and redraw ordering --
  derived from
  `u5-decomp/functions/COMBAT_OVL/`.
- The per-round walk over the thirty-two-slot actor table, the phase-counter mechanic, the round-counter wrap, the dispatch to player vs. monster handlers, and the three exit conditions — derived from `u5-decomp/functions/COMBAT_OVL/`.
- The retraction of the "post-round combat terrain/effect sweep", and the
  player-cursor blink marker and secondary-marker hook that survive it as the
  shared rasterizer's combat-only tail, including exact EGA/Tandy stroke
  geometry, palette indices, replacement operation, composition order,
  clipping boundary, and base-repaint erasure -- derived from private analysis
  in `../u5-decomp/functions/ULTIMA_EXE/`,
  `../u5-decomp/functions/EGA_DRV/`, `../u5-decomp/formats/`, and
  `../u5-decomp/notes/`. The resident routine is the shared viewport rasterizer,
  not a combat post-round pass.
- The per-actor turn dispatcher, complete dispatcher-level combat command map
  for all twenty-six letters and seven special inputs, the AI synthesis path for
  monster turns, the verb-stitching narration buffer, and the unified
  per-letter parser — derived from
  `u5-decomp/functions/COMBAT_OVL/`.
- Delegated combat command targets and edge behaviour for SJOG
  Get/Jimmy/Open/Search/Klimb, CMDS escape/Yell/Push, and ZSTATS
  Ready/Z-stats - derived from
  the corresponding COMBAT command table plus
  `u5-decomp/functions/SJOG_OVL/`,
  `u5-decomp/functions/SJOG_OVL/`,
  `u5-decomp/functions/CMDS_OVL/`, and
  `u5-decomp/functions/ZSTATS_OVL/`, with
  `u5-decomp/notes/` as a cross-mode check.
- The negative post-combat SJOG boundary -- COMBAT reaches SJOG for in-round
  command delegates and helpers, not for an after-victory loot sweep -- derived
  from `u5-decomp/functions/COMBAT_OVL/` and cross-checked against
  `u5-decomp/notes/`.
- The special combat absorption marker producer that bridges qualifying dungeon
  room cleanup into ENDGAME -- derived from
  `u5-decomp/functions/SJOG_OVL/` and the
  ENDGAME caller census in
  `u5-decomp/functions/ULTIMA_EXE/`.
- The caller-side post-combat original-slot reconciler -- derived from
  `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/functions/SJOG_OVL/`.
- The absence of combat-exit gold/karma/victory-bonus writes is derived from
  the traced combat framer, COMBAT round loop, and relevant COMBAT-to-SJOG call
  coverage; later body food/gold staging is owned by
  `u5-decomp/functions/SJOG_OVL/`.
- The AI target-selection helper, the backwards walk and filter chain, the Mass
  Charm active-effect tag remap with class-threshold random gate, the
  Doom and Shadow Lord phase/hidden suppression exceptions, the ordinary invisibility filter, the
  first-five-party-slot fallback guard, centre fallback flee-marker writer,
  linear truncated Euclidean distance scoring with closest-wins tie-break, and the unit-step
  direction output with flee inversion — derived from
  `u5-decomp/functions/COMBAT_OVL/` and the sibling
  COMBAT damage/death note that identifies the same random-byte helper.
- The combat slot-to-group helper, including the party-class rule keyed on the
  controlled/charmed bit `0x01`, the monster-side inversion of that same bit,
  the dead-slot collapse, and the round walker's use of the helper's result as
  its two-way dispatch gate, derived from
  `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/functions/COMBAT_OVL/`; the secondary
  team resolver's descriptor-byte tests - **corrected 2026-08-23**: it tests
  descriptor bit `0x20`, not `0x40`, and reads no per-class flag - derived from
  `u5-decomp/functions/COMBAT_OVL/` and `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/` -- the hard-wired
  hostile roster template, the guard that keeps roster record zero out of the
  override, the census of shipped roster names confirming exactly one match, and
  the confirmation that character creation and the Ultima IV import name only
  roster record zero. The roster-relocation paths that move whole records
  between slots -- the companion join/leave paths, the usurper's capture scene,
  and New Order -- were each checked to confirm that none of them can move the
  player-named record out of record zero and that none writes player-supplied
  text into another record; see
  `u5-decomp/functions/SHOPPES3_OVL/`,
  `u5-decomp/functions/BLCKTHRN_OVL/` and
  `u5-decomp/functions/CMDS_OVL/`. Cross-checked against
  `u5-decomp/notes/`.
- Note for save-tooling authors: a hand-edited save could in principle make one
  of the other roster records match the shipped traitor template's name shape
  and so flip that companion to the monster side. No path in the shipped game
  reaches that state, so an implementation keyed to the roster record itself is
  behaviourally equivalent; the distinction matters only to code that validates
  or migrates save files.
- The controlled/charmed bit contract in Section 6.1a — its four writers, its
  three direct readers plus the slot-to-group helper that reads it as the team
  toggle, the Charm toggle as the only in-combat clear, the routing consequence
  that a party-side actor carrying the bit is dispatched to the automatic actor
  driver rather than the player's prompt, and the separation of the
  asleep/magically-disabled bit from the controlled/charmed bit (including the
  exact five-term condition the stats panel uses to draw the `C` override:
  party-side set, monster-side clear, dead clear, controlled bit set, owner
  field equal to the drawn row), together with the withdrawal of the earlier
  reading of the roster status letter `C` as "casting" (it means charmed) —
  derived from
  `u5-decomp/notes/`,
  `u5-decomp/functions/COMSUBS_OVL/`,
  `u5-decomp/functions/COMBAT_OVL/`, and
  `u5-decomp/functions/COMBAT_OVL/`.
- The HP-bucket wound-score classifier, low-HP morale writer for the fleeing
  flag, and fear/panic spell route that forces combat current HP into the
  critical bucket — derived from
  `u5-decomp/functions/COMBAT_OVL/` and
  `u5-decomp/formats/`.
- Protection's equipped-item-statistic bonus, Negate Magic's combat-cast absorption path, Negate Time's `T`/10 runtime tag, and the active-effect counter-aging rule — derived from local ULTIMA.EXE, COMBAT, CAST, CAST2, and SJOG helper analysis summarized without copying implementation text.
- The placement of Quickness's `Q` 0..1 gate and Negate Time's `T` outright
  turn skip at the head of the automatic actor driver rather than in the player
  command handler, and the correction of the earlier "player-side dispatch
  gate" reading — derived from a 2026-08-22 re-read of
  `u5-decomp/functions/COMBAT_OVL/`, and
  `u5-decomp/notes/`, with the
  round walker's two-way dispatch confirmed against
  `u5-decomp/functions/ULTIMA_EXE/`.
- The two equipped-ring effect hooks at encounter seating and at the parser's
  committed non-digit action tail, including hidden-state reassertion and the
  party-wide regeneration roll; the free-refusal branch before that tail; and
  the separate encounter-entry-only 1-in-16 ring-destruction check -- derived
  from `u5-decomp/functions/ULTIMA_EXE/`,
  `u5-decomp/functions/COMBAT_OVL/`, and
  `u5-decomp/functions/SJOG_OVL/`.
- The damage application and status transitions, the per-monster-class flag word's effect on damage and death, the special-class death paths, the slime-divide replication path, and the combat-local attacker experience credit — derived from `u5-decomp/functions/COMBAT_OVL/`, and `u5-decomp/functions/ULTIMA_EXE/`.
- Amulet/Turning's combat passive branch and ranged/effect scatter boundary —
  derived from `u5-decomp/functions/COMBAT_OVL/`, and
  `u5-decomp/functions/COMSUBS_OVL/`.
- The weapon/spell damage-row split, target selection handoff, item-id keyed
  range/effect rows, ranged/projectile apply path, and shared to-hit formula --
  derived from
  `u5-decomp/functions/COMSUBS_OVL/`,
  `u5-decomp/functions/COMBAT_OVL/`, and
  `u5-decomp/functions/COMBAT_OVL/`.
- Monster ranged/effect side-table row values and row attribution -- derived
  from `u5-decomp/formats/` and cross-checked against the COMBAT and
  COMSUBS ranged/effect consumers above.
- Shared saturating byte/word arithmetic used by stat and inventory mutation paths — derived from `u5-decomp/functions/ULTIMA_EXE/` and sibling helper notes.
- The monster movement fallback, teleport-capable movement bit, random legal
  arena-cell candidate path, surrounded check, in-arena step test, and linked
  combat-record/active-object coordinate updates — derived from
  `u5-decomp/functions/COMBAT_OVL/` and
  `u5-decomp/functions/SJOG_OVL/`.
- The step-or-attack primitive — direction-to-unit-step translation, arena range check, and on-success and on-failure narration — derived from `u5-decomp/functions/SJOG_OVL/`. The separate common post-dispatch field-contact call, target-slot contract, exact terrain arms, marker scan, priority, and effect/PRNG ordering are derived from private analysis in `u5-decomp/functions/COMBAT_OVL/`. The distinct Doom absorption caller timing and renderer-companion predicate are derived from private analysis in `u5-decomp/functions/COMBAT_OVL/`, `u5-decomp/functions/SJOG_OVL/`, and `u5-decomp/functions/ULTIMA_EXE/`.
- The dungeon-room special source conversion for the final Doom absorbable
  marker -- derived from
  `u5-decomp/functions/DNGLOOK_OVL/`,
  `u5-decomp/functions/ULTIMA_EXE/`, and local
  binary verification of `DUNGEON.CBT`.
- The monster special-ability hook, including possess, blink/phase,
  summon-daemon, lazy PRNG draw ordering, exact chance gates, random placement
  probe, handled-result turn consumption, failure continuation, and baseline
  class-flag assignments, derived from
  `u5-decomp/functions/COMSUBS_OVL/`
  and `u5-decomp/functions/COMBAT_OVL/`, with the `DATA.OVL` class-flag table.
- Negate Magic's and the Crown's three enemy-side combat checks -- the complete
  class-special-hook bypass, teleport-arm bypass, and scene-resistant
  ranged/effect abort -- including their different fall-through meanings and
  per-dispatch cadence, are derived from
  `u5-decomp/functions/COMSUBS_OVL/`,
  `u5-decomp/functions/COMBAT_OVL/`, and `u5-decomp/notes/`.
- The shared spell-resistance rating sources, signed score formula, strict
  comparison, caller census, and the distinct Tremor/Poison Wind target-only
  gate are derived from private analysis in
  `u5-decomp/functions/COMSUBS_OVL/`,
  `u5-decomp/functions/COMBAT_OVL/`,
  `u5-decomp/functions/CAST_OVL/`, and `u5-decomp/notes/`.
- The combat-side C-Cast interference-source lifecycle — write and clear
  timing, same-actor re-prompt, current-state predicates, no encounter/round/exit
  reset, and save persistence — is derived from
  `u5-decomp/functions/COMBAT_OVL/`,
  `u5-decomp/functions/COMSUBS_OVL/`,
  `u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/formats/`, and
  `u5-decomp/notes/`.
- The shared spell dispatcher used by combat casts — derived from `u5-decomp/functions/CAST_OVL/`.
- The combat spell-damage wrapper used by Magic Missile and Fireball — derived from local CAST, COMSUBS, and COMBAT helper analysis summarized without copying implementation text.
- The Clone spell's allocation and random legal arena placement behaviour — derived from local CAST and COMBAT helper analysis summarized without copying implementation text.
- The dynamic-objects table that combat overlays and the sprite animator that walks it during world ticks — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The fog/visibility post-pass that consumes the same active-object table during world rendering — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The combat AI target-range primitive, which computes truncated linear Euclidean distance between two arena coordinates — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The data-region correction that rules out a combat damage/hit-chance matrix and identifies the combat-instance faction tagging and per-class stat-record shape — derived from `u5-decomp/formats/`.
- The combat-arena file layout — 352-byte record stride, 11×11 terrain grid, metadata band, outdoor and dungeon-encounter banks — derived from `u5-decomp/formats/`.
- The character-record layout consulted by damage application and the active-player restore — derived from `u5-decomp/formats/`.
- The death-branch contract in Section 6.3 -- branch ordering, the incorporeal
  and vanish class-flag arms, the Gazer and Gargoyle exceptions, the arena
  terrain gate, which branches release the slot, and the drop-cap byte written
  into the active-object auxiliary byte -- derived from the 2026-08-22 retrace in
  `u5-decomp/functions/COMBAT_OVL/`.
- The vanish branch's action-result lifetime and overwrite edge, pixel-reveal
  sequence and cadence, partial slot cleanup, and party control/faint tail --
  derived from private analysis in `u5-decomp/functions/COMBAT_OVL/`,
  `u5-decomp/functions/COMSUBS_OVL/`, `u5-decomp/functions/SJOG_OVL/`,
  `u5-decomp/functions/ULTIMA_EXE/`, and `u5-decomp/notes/`.
- The `1..30` range of the roll helper used by both drop gates -- derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The three placement modes, the party-side versus monster-side flag-bit
  assignment, and the marker-only mode -- derived from the 2026-08-22 retrace in
  `u5-decomp/functions/ULTIMA_EXE/`.
- The framer's ambush entry branch, its setup target, and its discarded slot
   argument -- derived from `u5-decomp/functions/ULTIMA_EXE/`
   and `u5-decomp/notes/`.
- The exact edge classification and presentation, per-actor departure rather
  than immediate fight exit, post-victory cleanup requirement, complete ambush
  caller census, two distinct full-range-swap algorithms, PRNG ordering and
  deterministic vectors were re-audited in private analysis under
  `u5-decomp/notes/` and the ULTIMA, DNGLOOK, DUNGEON, COMBAT, SJOG, and CMDS
  function directories.
- The per-letter combat command map of Section 8 — the two shared delegate
  shapes, the exact three refusal tails and newline/audio ordering, the
  direct-call letters, the exact pre-maintenance re-prompt rule, and the
  withdrawal of the earlier U-Use, X-it and Quit readings — plus
  the encounter-size damper's full life cycle in Section 5. Source provenance:
  derived from private analysis in
  `../u5-decomp/notes/`, with
  `../u5-decomp/functions/COMBAT_OVL/`,
  `../u5-decomp/functions/SJOG_OVL/`,
  `../u5-decomp/functions/ULTIMA_EXE/`, and
  `../u5-decomp/functions/CAST_OVL/`.
- Combat's own typeahead toggle, its Escape / Space / actor-select bindings, and
  the arena targeting cursor as the game's only eight-way input surface. Source
  provenance: derived from private analysis in
  `../u5-decomp/notes/` and
  `../u5-decomp/functions/COMSUBS_OVL/`.
- The Escape handler's party-side predicate, exact `Escape-Not here!`,
  `Escape-Not yet!`, and newline-free `Escape!` outputs, two-pass cleanup,
  per-slot ticks, speaker glissando, and relationship to the round loop's exact
  victory/defeat strings -- derived from
  `../u5-decomp/functions/CMDS_OVL/`,
  `../u5-decomp/functions/COMBAT_OVL/`,
  `../u5-decomp/functions/ULTIMA_EXE/`, and
  `../u5-decomp/notes/`.
- The ordinary melee and ranged/effect to-hit contract of Section 11 -- the
  operand orientation (defender added, attacker subtracted), the identification
  of the draw as the shared skewed `1..30` combat roll, the per-score hit table,
  the side-by-side rating selection including the `zero-selector stat row`
  normalisation on the monster arm and the strength-arm item family, the
  always-hit membership and its player-path-only reachability, the fixed score
  of 15 taken by an automatic-driver party attacker, attempts per activation on
  both sides, and the worked Bat-versus-starting-Avatar example in both
  directions -- together with Section 12's two-stage damage roller, the flat
  monster attack value, the `1..rating` defence roll and its skip on a zero
  rating (issue #183) -- derived from private analysis in
  `../u5-decomp/notes/`, `../u5-decomp/functions/COMBAT_OVL/` and
  `../u5-decomp/functions/COMSUBS_OVL/`. Scope on the negatives in those
  sections: the call-site enumerations behind "both driver-side call sites pass
  a fixed neutral item id", "no call site selects the defense arm of the
  selector" and "there is no multi-attack loop on the monster path" rest on an
  exhaustive decode of directly encoded near and far calls across the shipped
  executable, every overlay and all four display drivers, resolved against
  descriptor-derived load bases, plus a literal scan that rules out a pointer
  table; a target computed at run time would fall outside them. That an
  automatic-driver party attacker is reachable end to end through the routes
  Section 6.1a lists is **probable** rather than established: the arithmetic was
  re-derived, the full path was not executed.
- The combat-entry banner presentation of Section 4.1 -- the two-banner
  split and its emission order, the group-name table's shipped-verbatim status
  and its indexing by class id, centring-as-cursor-move and the left-edge form
  of the centring column, count-independence and the Shadow Lord caption, and
  the conflict banner's literal, flank glyph code point, edge-to-edge
  placement, suppressed trailing line feed and unconditional print (issue #185)
  -- derived from private analysis in `../u5-decomp/notes/`. Scope on the two
  *probable* claims in that section: the terrain-entry-only statement rests on
  a near-call census of the resident image and all twenty-three overlays,
  with the entry paths themselves unstepped and far or register-indirect
  transfers uncensused; and the identification of the active window as the
  gameplay message window rests on the full-stats redraw's closing selection
  plus a captured frame, with the turn loops unstepped, so the window-local
  placement is established while the absolute columns inherit that caveat.
- The attack-outcome narration census of Section 11.1 (issue #185) -- which
  outcomes print a line on each side, the exact lines, their newline behaviour,
  and their order relative to the impact presentation, damage application and
  the stats-panel redraw; the ordinary hostile monster's silent melee miss and
  its two carve-outs (the ranged scatter and the controlled bit); the
  target-named rule; the graze line that Sections 11 and 12 used to call a miss;
  the monster-target-only wound grading; and the negative that no
  attacker-and-target announcement string exists -- derived from private
  analysis in `../u5-decomp/notes/`. That analysis was re-derived adversarially
  by two independent verifiers and repaired in a second pass; the corpus scans
  behind each negative, and the two claims that remain *probable* rather than
  established, are stated in Section 11.1's own scope list rather than left
  implicit here. The same pass supplied the Section 9 correction to the monster
  turn's dispatch shape and the Section 6.1a / `catalogs/spell-list.md`
  correction to where a controlled monster's turn is driven from.
