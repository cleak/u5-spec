# Combat

## 1. Overview

Ultima V's combat system is a turn-based, party-versus-monsters tactical mode that plays out on a small fixed-size arena grid. When an overworld, dungeon, or scripted/rest caller triggers a fight, the engine suspends what it was doing, swaps the on-screen scene for an arena, populates the arena with the player's party at one set of fixed entry points and a randomised set of monsters at another, and runs a self-contained round loop until one side is wiped out or the player flees. When the loop returns, the engine restores the suspended world state - player position, the dynamic-objects table, the scene byte - and returns control to the calling mode loop with the fight's after-effects baked in: damage taken, characters dead or asleep, time advanced by the round loop, and resources consumed by combat actions.

Combat is "inside-out" — the world freezes while the fight plays through, the fight has its own table of actors, its own per-letter command dispatch, its own AI, and its own arena terrain — and then the function call returns and the world resumes exactly where it left off. The mode-loops above combat are unaware that combat happened beyond the visible state changes.

This spec describes the combat trigger framing, the arena format and monster placement, the per-round walk over the actor table, the player command set, the monster AI, the attack-resolution primitive, the damage and status model, and integration points with text output, the spell system, and time.

## 2. Combat triggers

Combat enters from one entry point - a single function call from a mode or scripted setup path that takes three parameters: a flags word, an actor-slot index, and an entry-mode bitfield. The entry-mode bitfield distinguishes three setup families:

**Terrain combat.** The default. Reached when the player walks into (or attacks) a hostile creature on the overworld or in a town. The dynamic-objects-table slot of the offending creature is passed along. Two independent selections happen before the round loop: the **outdoor arena** is chosen from the world terrain under that creature plus the party's vehicle state, and the encounter's **base combat class** is derived from the creature's own sprite byte by a small linear formula. The arena is loaded first; the terrain-combat setup then seats the party, rolls the monster spawn count from the base class's stat row, and places each monster at one of the arena's sixteen arrival positions. `encounters.md` Section 4 publishes both selectors.

**Ambush combat.** A separate setup branch from ordinary terrain combat. The current resolved setup target is the DNGLOOK room-NPC setup entry used by dungeon/rest-style room setup, not the ordinary terrain helper and not the town hostile-NPC alarm path. Do not infer its arena choice, monster count, or placement order from the dormant shuffle branch inside the terrain setup helper unless a live caller is identified.
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

Each arena occupies a fixed-size record. The first part is the **terrain grid** — an eleven-by-eleven array of tile bytes describing the arena floor. The remainder is the **metadata band** — a flat run of bytes per row that the engine reads at setup. The confirmed outdoor slices provide six party entry coordinate pairs and sixteen monster placement-slot coordinate pairs. Hazard, edge, and other special-cell semantics must stay with their traced runtime consumers until a direct metadata reader is identified. The arena format spec covers the byte-by-byte layout; from combat's perspective the contract is "given an arena ID, the on-disk record tells us a 121-cell terrain grid and the confirmed setup slices."

When the arena loads, its terrain grid is copied into a runtime grid in the data segment with a row stride padded out to thirty-two bytes (a power-of-two stride that lets the renderer index by `(row << 5) + col`). Movement and visibility consult this runtime grid; the on-disk record is not touched again until the next combat enters.

**Wall and blocked tiles** in the runtime grid are recognised through combat's
own arena passability lookup, not through the world/town tile-id bitmap. An
actor whose record places it on a blocked arena tile is silently skipped for the
round; this corner case is a defensive guard since proper monster placement keeps
actors on walkable cells.

**Out-of-arena exits.** Any cardinal move whose destination falls outside the
11-by-11 arena is routed through a shared leave helper. Ship-style combats
refuse that helper and keep the party aboard. In constrained encounters, once a
party exit direction is established, later party exits must use the same
direction or the helper refuses them. Otherwise the helper accepts the
out-of-arena move as a combat leave/escape trigger. The visible presentation
depends on whether live foes remain: with foes present it is escape, and with no
foes present it is ordinary leaving/cleanup.

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

## 5. Party seating and monster placement

The arena record is selected and loaded **before** the framer runs, by the
terrain-combat entry step described in `encounters.md` Section 4. By the time
the setup helper runs, the arena's terrain grid and its four metadata slices —
six party entry X values, six party entry Y values, sixteen placement-slot X
values, sixteen placement-slot Y values — are already resident. The setup
helper then runs a per-encounter pass that clears both combat tables and seats
the party, and only afterwards picks a monster count, picks a class per
monster, and writes one record per spawned monster.

The ordinary terrain setup helper also contains an optional placement-shuffle branch, but the only traced terrain caller passes flags that leave that branch inactive. Live ambush and rest/camp alternate setup use separate entry-mode helpers, so do not model those paths as the dormant terrain-helper shuffle unless a caller is found. Specifically, the ambush helper is the room-combat setup helper specified in `formats/cbt.md` Section 5: it runs its own party-entry readback and its own sixteen-source scan over the resident arena metadata band, and it never touches the terrain helper's count roll, companion-class roll, or shuffle.

**Order of operations.** Ordinary terrain combat setup is strictly:

1. Clear all thirty-two combat descriptors (every field) and the first seven
   bytes of all thirty-two combat-instance active-object records. The eighth
   byte of an active-object record — its descriptor back-link — is not touched
   by this clear; it is set to the "no linked descriptor" sentinel when the
   record is allocated.
2. Seat the party from the per-arena party entry coordinates.
3. Print the combat banner.
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
- A member wearing a Ring of Invisibility is marked hidden and its presentation
  byte switched to the suppressed-sprite value; a member wearing a Ring of
  Regeneration runs the regeneration tick once at entry.
- Independently of the above, each member wearing either of those two rings
  faces a one-in-sixteen check at combat entry that destroys the ring with the
  "a ring has vanished" message.

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

A short combat banner ("CONFLICT") is printed at the start of setup, before any monsters are placed.

**Picking arrival positions.** Each monster gets one of sixteen arena cells,
indexed by a placement slot. For ordinary terrain combat, slots are walked in
identity order so placements are deterministic for the selected arena record.
The terrain helper has a dormant Fisher-Yates branch behind a flag bit, but no
traced live caller reaches it. The selected `BRIT.CBT` arena is authoritative
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
exceed thirty; a phase counter of thirty-six minus the base-step; the class id
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
   placement path, so their class byte is the monster-side one and monster AI
   drives their turns — the bit never hands a creature to the player's prompt —
   but because the bit is the group helper's team toggle, a stamped creature
   groups with the party rather than with the monsters for the same-faction
   filter (see the dispatch and grouping paragraphs below). See `systems/magic.md`, Summoning and conjuration. The
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
| Vanish-on-death class | Monster whose class-flag word has the vanish bit set — Wanderer, Blackthorn, Lord British, Shadow Lord | `0x16` (vanish marker) | Prints `<name> vanishes!`, sets the per-combat status byte to `2`, runs the fade animation on the terrain under the actor, then the post-turn flush | **Yes** |
| Incorporeal class | Monster whose class-flag word has the low bit set but **not** the vanish bit — Sea Horse, Squid, Sea Serpent, Shark, Bat, Ghost, Slime, Insect Swarm, Wisp, Daemon | **none** | none | **Yes** |
| Gazer | Monster of the Gazer class | `0x1F` (eye-burst special) | **Places a live Insect Swarm combatant (class 31) at the death coordinate** through the ordinary monster-placement primitive, then redraws the arena. See "The Gazer death spawns a real combatant" below | No |
| Gargoyle | Monster of the Gargoyle class | **none** | Writes `0x4C` (lava pool) into the combat-arena **terrain** cell under the actor; that terrain edit persists for the rest of the combat instance | **Yes** |
| Ordinary monster, terrain rejects | Any other monster whose underlying arena terrain byte is `0x87`, or is numerically below `4` | **none** | none | **Yes** |
| Ordinary monster, drop roll rejected | Terrain accepted, and the first roll exceeds the class drop-cap byte | `0x1F` | none — byte 5 keeps whatever the per-encounter reset left there | No |
| Ordinary monster, drop roll accepted | Terrain accepted, and the first roll is less than or equal to the class drop-cap byte | `0x01` (dead-monster / drop marker) | Byte 5 of the active-object record receives **the class drop-cap byte itself**. A second independent roll strictly below the same drop cap ORs bit `0x80` into byte 5 as the special-drop marker | No |

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

When an actor dies, the "marked dead" bit is set; when a slot is freed completely (a vanishing monster or a fled character), the record is cleared to all zeros and the slot becomes available for re-allocation.

A second, parallel table — the dynamic-objects table that combat overlays onto the world's normal table — holds the same actors indexed by class for purposes the renderer cares about. The two tables are kept in sync by the step-or-attack primitive (Section 11): when an actor moves, its (X, Y) is written into both.

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

Each round is one walk over the thirty-two-slot actor table. The round loop has start-of-round setup, a per-actor body that runs zero or one times per slot, and end-of-round exit checks. When the body has visited all thirty-two slots, the round restarts (unless an exit fires).

**Start-of-round setup.** A small bundle of housekeeping work: screen redraw, combat-begin overlay refresh, screen flush, per-round init that resets per-slot scratch state, and clearing the "any spell cast this round" flag.

**Per-actor body.** For each slot 0–31:

1. **Skip empty slots and slots already marked dead.** The "alive" flag and "marked dead" flag bits gate this.
2. **Sweep deaths from prior rounds.** If the slot is alive but its linked character record's status byte is now `'D'`, mark the slot dead, fire a death-narration effect, and advance to the next slot. This catches party members who died between rounds (poison, ongoing spells).
3. **Skip wall-cell slots.** A defensive guard against bad placement.
4. **Decrement the actor's phase counter.** While non-zero, the slot does not act this round. When it reaches zero, the actor *does* act.
5. **On zero, refresh the counter and act.** The counter is reset to `36 - base_step`. A round-counter at the table level is incremented and wrapped at ten; on every wrap, the engine fires a tile-render pass for animation.
6. **Dispatch the actor's turn.** A single function asks "is this slot a player or a monster?" — for a player, control passes to the player command handler (Section 8); for a monster, to the AI-then-command handler that runs the AI synthesis path before falling into the same dispatch (Section 9).
7. **Mark the slot acted, run the standing-cell hazard pass, then the post-action render.** These are two separate steps and only the second one draws. The hazard pass reads the arena terrain under the actor that just acted, and — if that terrain is not itself damaging — scans the object table for any object other than the actor's own sitting on the same cell. Three damaging kinds are recognized, each with its own effect: a low tier that applies the party status/damage path with the no-attacker sentinel and plays the hit sound, but only while the actor's own object entry is an ordinary live entry; a middle tier that plays the hit sound, rolls a small random amount, feeds it to the damage-and-status resolver, runs the shared finalize hook and raises the leave-combat flag; and a top tier that routes the actor into the same petrify-style special effect a Gazer's gaze uses. A cell with none of these kinds costs the actor nothing. Only after the hazard pass does the separate render step redraw changed cells and run any post-action sound or particle effect. Death narration runs here when relevant.

**End-of-round exit checks.** Three flags control exit:

- **Defeat flag**: the entire party is dead, asleep, or fled. Result is "defeat".
- **Leave-combat flag**: the out-of-arena leave helper has accepted, a spell or
  tile effect has ended combat, or the combat-only Escape cleanup path has
  accepted. The one-shot exit narration and Escape's table cleanup are separate
  operations; Section 14 gives their exact ordering and text.
- **Exhausted slots** (loop reached slot 32): start a new round.

When defeat or leave-combat fires, the round loop returns "1" (victory/escape) or "0" (defeat).

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
| **A** | Attack. Routes into the shared arena attack helper with the acting combatant and a flag saying whether that combatant is armed; the helper announces the actor and the weapons it is wielding (or bare hands) before the attack resolves. Resolution is Section 11. Ends the actor's action. |
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
- **Digit `0`** — clear the active-player selection and repaint the panel.
- **Digits `1`–`6`** — select party member 1 through 6 as the active player. A
  failed selection re-prompts at no cost.
- **Cardinal direction codes** — move one cell in the requested cardinal
  direction. Movement uses the step-or-attack primitive: if the cell is
  occupied by a hostile, attack instead; if the destination leaves the arena,
  run the out-of-arena helper described in Section 3. A blocked step re-prompts
  at no cost. Diagonal direction codes are not combat movement commands; they
  fall through to the ordinary invalid-command refusal.
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
that accepts eight-way input, and it is not movement. While combat asks the
player to pick a cell, the four cardinal keys move the targeting cursor one cell
and the four corner keys (Home / End / PgUp / PgDn, or the numpad corners) move
it one cell diagonally. Enter or the attack letter confirms, Escape cancels, and
Space runs the self-target check. An implementer should not generalise this into
diagonal stepping: no mode loop, and no letter dispatcher, accepts a diagonal
step.

Several commands are **multi-stage** (Attack, Cast, Get, Jimmy, Open, Ready, Search, Use, Yell, and some delegated arena handlers): they print a short prompt or call a sub-handler that reads a follow-up keystroke. The combat command handler's dispatch is structured so multi-stage commands return control to the same handler for their continuation rather than recursing through the round walker. The command set mirrors the world mode loops' visible vocabulary so muscle memory transfers cleanly between play modes, but the combat parser owns its own branches and refusals. The most distinctive combat-only paths are Attack, Cast, active-player selection, the arena targeting cursor, combat Yell's no-effect scene fallthrough, out-of-bounds fleeing, and the Escape cleanup exit.

## 9. Monster AI

When the round walker dispatches a monster slot, the AI runs as a sequence of three passes that ultimately produce a *synthesised keystroke* — the AI generates the same bytes the player would press if they were controlling this monster, and the synthesised byte runs through the same per-letter dispatcher as a player turn. Monsters and players share the action infrastructure.

**Pass 1 - Dispatch setup.** The per-actor dispatcher — the **automatic actor
driver** — clears the actor's combat-status presentation area, prepares
narration scratch, and checks whether the current slot should run a normal
turn, yield to a queued animation/effect, or continue into AI decision-making.
Current evidence does not support a general per-class AI script runner. The
ordinary monster path is table and helper driven: status/flee gates run first,
then the class-flag special hook, target selection, movement-direction
synthesis, optional step/teleport logic, and finally the same command parser
used by player turns.

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
active-effect tag for `C`. It resolves the acting monster's class charm
threshold from the per-class combat record, then rolls one uniform random byte
in `[0, 255]`. If the roll is strictly greater than the threshold, the acting
monster's faction for this target pick is forced to neutral group 0 before the
filter above runs; otherwise the monster keeps its normal faction. This does not
mark individual actors as charmed; it changes which candidates survive the
normal same-faction filter for the current AI decision. For a threshold `T`, the
remap chance is `(255 - T) / 256` for `0 <= T <= 255`; the current class
thresholds are catalogued in `catalogs/monster-bestiary.md`.

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
test used by combat placement allows it. Ordinary stepping asks the surrounded
helper whether all four cardinal neighbors are blocked, then uses the in-arena
step test for candidate moves. The engine first tries the target vector on one
axis, with randomized axis priority, then falls back to random cardinal tries
when the direct axes are blocked. An accepted move updates both the combat
actor/effect record and the linked renderer-facing active-object record before
the post-step terrain/effect check runs. If no tested direction is legal, the
actor's move is blocked for that turn.

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

**Pass 3 — Synthesise.** A combat-specific input gate reads the synthesised byte from the actor's record. The AI's chosen direction is encoded as the byte the player would press if they wanted to walk the same way (`'N'`, `'S'`, `'E'`, `'W'` direction codes), or the byte for "Attack" if the chosen direction puts the target adjacent. The byte falls into the same per-letter dispatcher as the player command handler. Before the command runs, the AI assembles a one-line narration string — for example `<monster name> attacks <target name>, armed with <weapon>!` — by stitching together a short verb composer.

The architectural consequence: **all damage and movement effects in combat go through the same primitive, regardless of whether the actor is a player or a monster.** Section 11 describes that primitive.

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
and dispatch are covered here. Monster turns use AI command synthesis before
they enter the shared combat parser. The class-flag special hook is now bounded
to possess, blink/phase, and summon-daemon branches before movement synthesis.
Those effects do not route through the party spell prompt, party reagents,
premixed charges, MP, or player circle gates.

## 11. Attack resolution

Movement and attack share a single primitive, called once per actor turn. The primitive takes a direction code (1 = west, 2 = east, 3 = north, 4 = south, the same mapping the world-mode-loops use) and the actor's slot index:

1. **Translate direction to a unit step.** Cardinals map to `(dx, dy)` of `(±1, 0)` or `(0, ±1)`. A direction code of zero or out of range produces `(0, 0)` — "attack in place".
2. **Print the direction word** ("North", "South", "East", or "West") followed by a newline. Movement narration is part of the primitive.
3. **Range-check the destination.** `(new_x, new_y) = (self_x + dx, self_y + dy)` must fall in `[0, 10]`. If off the arena, route to the out-of-bounds handler. That handler decides between ship-style refusal, same-direction refusal for constrained exits, and an accepted leave/escape trigger.
4. **Run the step-or-attack inner pass.** A separate function handles whichever case applies:
   - **Empty walkable cell:** the actor moves. Update its (X, Y) in both the actor table and the parallel dynamic-objects table.
   - **Hostile actor at the destination:** run the attack roll. Hit/miss decision, raw damage, defense subtraction, and the target HP/status writes are computed from the attacker/target combat state, class stats, cached party defense bytes, active effects, and random rolls. The formerly suspected data-region lookup is not a combat damage or hit-chance matrix.
   - **Friendly actor or wall at the destination:** treat as blocked.
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

The ordinary attack damage roller—which randomizes attack value and defense—is
not called by Poison or Fire contact. Their raw damage still enters the shared
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

The shared to-hit helper is used by ordinary melee and ranged/effect attacks
unless a caller has forced the outcome. Certain special action/effect tile
families are always-hit cases. Otherwise the helper resolves attacker and
defender combat ratings, computes `(attacker - defender + 30) / 2`, and accepts
the hit when that score beats a uniform random byte. This is the public hit-roll
shape. One of the ratings the selector can return is not a stat-table byte at
all but a per-actor *combat weight*: normally the actor's own speed seed, and
the floor value one in three override cases — while the Negate Time tag is
running and the actor is a monster, for one specific actor class, and for any
actor carrying the asleep/magically-disabled bit. It is the defender term of
the score in the ordinary melee case, and can stand in as the attacker term as
well, so all three overrides make the affected actor markedly easier to hit
while barely changing what it can land; the Negate Time override is the
mechanical bite of a time-stopped arena. Earlier revisions described this
weight as a "team modifier" consumed by a chest-encounter targeting flip; that
reading is withdrawn. The item catalog now publishes the traced weapon-dispatch range/effect
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
resets the scene state, and consumes the action. A separate magic-immune or
boss-resistance trait is checked inside the ranged/effect helper for special
combat contexts; when it accepts, the helper aborts before damage or status
resolution. Mimic bypasses the ordinary resistance pre-gate while remaining
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

## 12. Damage and status

The damage-and-status handler bundles "apply damage, update status, narrate the result, and handle special-class death effects" into one function. It takes a damage amount and a target slot.

**Damage modifiers.** Negative damage is clamped to zero and an "attack missed" status flag is raised so the narration reads as a miss. A magic value (decimal 99) is treated as **instant kill** — bypass HP, force the death path; used for between-round death finalisation and one-shot-kill spell effects. Magic Missile and Fireball reach this handler only after the spell-damage wrapper rolls raw damage (`1..16` and `1..30`, respectively) and subtracts a random defense roll based on the target's combat defense; Kill/Slay Living reaches its death result only after the separate shared resistance predicate permits it and does not use that defense subtraction. For party-member defenders, the damage roll reads the cached combat-defense byte in the character record at offset `+0x18`; factory-seed records carry value `7`. This is not one of the stat bytes earlier in the record — Strength `+0x0C`, Dexterity `+0x0D`, Intelligence `+0x0E`. The original game also defines a separate per-item defence contribution keyed by readied equipment, plus a small bonus that Protection's shared `P` tag was meant to add on top of it, but neither ever applies: every one of the per-item accumulations is guarded by a comparison that is tautologically true and therefore always skipped, and the resulting total is never consumed — one caller discards it, and the other is reachable only through an attribute-selector arm that no call site in the game ever selects. No traced combat path recomputes the character-defense byte from readied armour. Treat the intended contribution as an original-game defect and a deliberate decision point for a port; do *not* generalise it into "worn equipment has no effect on combat", because the surviving to-hit computation reads other character-record fields whose relationship to equipment has not been traced. The target's per-class flags are consulted: a "halve damage" flag halves *physical* (non-magical) damage; an "immune to physical" flag zeroes it.

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

- **Vanish on death** (vanish bit set; Wanderer, Blackthorn, Lord British, Shadow Lord in the analyzed baseline) prints `<monster name> vanishes!`, changes the active-object tile to the vanish marker, sets the per-combat status byte, plays the fade-out animation, and releases the slot.
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
class charm threshold and, on success, remap that monster to neutral group 0
before friend/foe filtering; Negate Magic's `N` tag absorbs combat casts before
the shared spell dispatcher spends charge or MP. Three different things can put
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
| Per-class stat record            | Eight bytes per class: combat tier, speed seed/base-step input, endurance rating, defense rating, attack-damage cap, maximum HP, default spawn count, and default kill/drop cap. The tier and endurance bytes are the two class-side ratings the shared actor-rating selector returns into the to-hit and resistance scores; the "chest/encounter team-flip" reading of them in earlier revisions is withdrawn. Maximum HP initializes monster HP and supplies the reward-unit input. The attack and defense bytes are consumed by the computed attack resolver; this row is not a flat damage/hit lookup matrix. |
| Per-class name pointers          | Sixteen-bit pointers per class to the printable monster name strings.                                                                            |

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

Three exit conditions end combat; each sets one of the round-loop's flag bytes, and the per-round epilogue checks them.

**Victory.** When every hostile actor has been killed (no non-party slot has the "alive and active" flag bits set), the round loop prints the resident combat string `VICTORY!` through the ordinary string printer. The stored string has one leading and one trailing newline, and a one-shot guard prevents a duplicate announcement. The loop exits with result code "1" after cleanup. The framer then restores the suspended world state, refreshes party stats, and returns to the calling mode. Combat death paths may have produced temporary loot markers and a raw reward unit while the combat-instance tables were live, but the traced framer does not merge those active-object bytes into the restored world table or propagate the helper's return value as a post-combat award. The traced SJOG calls reached from COMBAT are command-time delegates and per-round helpers, not an after-victory loot-conversion pass. Ordinary terrain-trigger removal happens after the framer, in the resident caller that invokes the post-combat object reconciler for the original trigger slot. This settles the combat-exit boundary: ordinary attack/spell experience can be credited before the framer restores the world, the original trigger slot can be cleared or rewritten by the caller-side reconciler, and any body-like food/gold result belongs to later Search/Get interaction with that rewritten slot. Arbitrary combat corpse markers, party gold, karma, and any victory bonus are not automatic framer outputs.

**Defeat.** When the entire party is dead, asleep, or otherwise inactive, the engine prints `BATTLE IS LOST!` from the same resident combat string pool and the round loop returns "0". That stored string begins with a newline and has no trailing newline before its terminator. There is no command that reaches the defeat exit deliberately: an earlier revision of this section described combat `Q` as an abandon-party command that did so, and that is withdrawn — the combat parser refuses `Q` like the other meaningless verbs (Section 8). What happens next is not decided by combat: control returns to the exploration loop that framed the fight, and that loop's next per-turn party-capability check sees the result. A wipe with nobody left able to act and nobody asleep runs the rescue/refuge cinematic specified in `systems/blackthorn.md` Section 7 — which restores the party and resumes play at Lord British's Castle, so an ordinary wipe is not a terminal game-over. A wipe that leaves a sleeping member instead simply passes turns until someone wakes or dies.

**Escape.** Moving outside the arena reaches the out-of-bounds combat leave helper. Ship-style fights can refuse the attempt, and constrained encounters require party exits to share the established exit direction. Once the helper accepts, it sets the leave-combat path; the first accepted trigger per fight prints the exit presentation and the round loop exits with code "1". Surviving party members and monsters are not given a chance to land final blows once that helper accepts.

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

The framer's restore phase runs the same way for all three — the only difference is the result code returned. Combat time advances from the round loop's round-counter wrap, which fires the per-turn cleanup with a one-minute increment; a separate one-minute exit increment is not part of the currently traced framer restore.

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
  target selection, direction synthesis, and the shared combat command parser.
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
  class-threshold AI-target remap, and Negate Magic's `N` combat-cast
  absorption path. The `Q` gate was previously attributed to the player
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
  filters, no-target fallback, movement-vector synthesis, synthesized command
  dispatch, and parser reuse. The v1 baseline assigns possess, blink/phase, and
  summon-daemon rows as listed in `monster-bestiary.md`. Keep branch ordering
  data-driven for variant assets that set more than one turn-special trait.

- **Ordinary AI edge labels.** The old "class script runner" hypothesis has
  been removed. The step-permission, step-validity, fallback-target, and
  no-target cleanup paths are now specified as surrounded checking, in-arena step
  testing, per-turn fallback, and pending-action marking. The target-picker
  suppression-filter exceptions are now labelled as Doom and Shadow Lord, and
  the centre fallback's flee-bit writer is specified above.

- **Round counter wrap at ten.** The per-round counter wraps at ten and fires a tile-render on every wrap. Likely a "render every N actor-turns" cadence balancing CPU cost on original hardware. A modern implementation can treat it as "redraw every frame" without preserving the cadence.

- **Faction edge cases.** The ordinary party, hostile monster, and passive/neutral faction tags are identified in the combat-instance descriptor table. Remaining exactness work is limited to any additional class-specific remaps beyond the Mass Charm threshold path.

- **The thirty-two-slot table size.** Plausibly: six party slots + sixteen monster placement slots + ten "dynamic" slots for replicated/summoned creatures. The round walker's "less than thirty-two" test is the only hard upper bound.

## 17. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

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
- The terrain-combat setup, the class-row spawn-count lookup, the dormant optional Fisher-Yates branch in the terrain helper, the early-spawn companion-class roll, and the single-attacker town-style override — derived from `u5-decomp/functions/ULTIMA_EXE/`.
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
- The `1..30` range of the roll helper used by both drop gates -- derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The three placement modes, the party-side versus monster-side flag-bit
  assignment, and the marker-only mode -- derived from the 2026-08-22 retrace in
  `u5-decomp/functions/ULTIMA_EXE/`.
- The framer's ambush entry branch, its setup target, and its discarded slot
  argument -- derived from `u5-decomp/functions/ULTIMA_EXE/`
  and `u5-decomp/notes/`.
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
