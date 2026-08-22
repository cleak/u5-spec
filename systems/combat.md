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
| `0x40` | **Monster-side slot** (self-acting AI actor). Placement stamps this bit when it writes an ordinary monster descriptor, except for the two reserved unnamed classes 8 and 9, which are stamped `0x20` instead. Bits `0x80` and `0x40` are mutually exclusive as written by placement. |
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
   placement path, so their faction byte is the monster-side one and monster AI
   drives their turns; the bit changes their attack, not their allegiance or
   who commands them. See `systems/magic.md`, Summoning and conjuration. The
   monster AI's own summon-daemon ability does *not* set this bit (Section 9).
4. **The Sword of Chaos compulsion.** The round walker sends a slot down the
   player-driven path when the active-player sentinel is unset, or when the slot
   is party-side and its owner/character byte equals the sentinel. On that path,
   if the slot is party-side and its character has item id 35 (Sword of Chaos)
   readied in either the weapon-hand
   or shield-hand slot, the engine sets this bit on that party descriptor,
   clears the active-player sentinel, and runs the turn through the automatic
   actor driver instead of reading a command from the player. Any other readied
   equipment takes the ordinary interactive path and never sets the bit.

**Readers.** There are exactly three.

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

**Not a dispatch gate.** The round walker chooses the player-driven path from
the active-player sentinel — unset, or matching the slot's owner/character byte
— plus the equipment test above; it never reads bit `0x01` to decide who acts.
Earlier drafts of this spec said the walker dispatched any slot with the bit set
through the player command parser. That is withdrawn: a possessed party member
keeps taking turns in slot order, and the visible consequences are the `C`
status letter and the redirected attack branch, not a change of who is prompted.

**Sleep is a different bit.** Bit `0x08` is the asleep/magically-disabled
state and has nothing to do with charm, possession, or any other external
control. Nothing in the engine writes `0x08` for a charm or possess effect, and
nothing reads it when deciding whether an actor is controlled. An implementer
that stores the charmed state in `0x08` will skip the controlled actor's turn
instead of redirecting its attack, and will never draw the `C` status letter:
the panel's test is "party-side set, monster-side clear, dead clear,
controlled `0x01` set", and `0x08` is not part of it.

**Faction is a different byte.** The friend/foe resolver reads bit `0x40` to
recognise a monster-side slot, and the team-override flag it consults lives in
the per-monster-class flag word, not in this descriptor byte. Do not reuse
`0x80` or `0x01` as a faction toggle.

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
7. **Mark the slot acted, run the post-action render.** Redraws changed cells and runs any post-action sound or particle effect. Death narration runs here when relevant.

**End-of-round exit checks.** Three flags control exit:

- **Defeat flag**: the entire party is dead, asleep, or fled. Result is "defeat".
- **Leave-combat flag**: the out-of-arena leave helper has accepted, a spell or tile effect has ended combat, or the combat-only Escape cleanup path has accepted after no live foes remain. On the *first* such trigger per fight, the exit-message string is printed; subsequent reads pass through silently.
- **Exhausted slots** (loop reached slot 32): start a new round.

When defeat or leave-combat fires, the round loop returns "1" (victory/escape) or "0" (defeat).

**Post-round maintenance pass.** A separate round-adjacent maintenance pass
keeps arena tile effects and combat cursors in sync with the rendered tactical
view. It sweeps the eleven-by-eleven combat arena grid in row-major order using
the same padded row stride as the runtime terrain grid. For each cell, it reads
the terrain/state byte and the parallel magic/effect byte:

- Terrain/state byte `0x00` dispatches the magic/effect byte as a cell effect,
  except for magic/effect byte `0x16`, which is the skipped no-effect sentinel.
- Terrain/state byte `0xDC` ticks the shared combat magic-effect timer only
  while that timer is nonzero and below sixteen.
- Any other terrain/state byte is translated through the combat tile-effect
  table before dispatch.

After the grid sweep, the same pass handles presentation-only markers while
combat is active. A blink flag toggles the player cursor every other pass; if
the cursor is enabled and the player arena cell is valid, the renderer draws
the player marker at the cell's table-derived screen position. A separate
secondary-marker flag can draw another small marker at an explicit arena X/Y.
These marker updates do not advance combat time, mutate actor HP/status, or
consume placed field markers. They are visual/effect synchronization around the
round loop, distinct from actor dispatch and from the post-step field-contact
hook described later.

The phase-counter / base-step structure means actors act at *staggered* paces. There is no "player turn then monster turn" — initiative is *interleaved* by phase counter, so a fast monster might act twice between the player's turns.

## 8. Player commands in combat

When the round walker dispatches a player slot, the player command handler normally reads exactly one keystroke from the input pipeline (using the same input system that drives the rest of the engine). If Quickness's shared `Q` active-effect tag is live, that handler first rolls an inclusive 0..1 random gate: a zero result consumes the ready dispatch without reading input, while a one result continues normally. When input is read, the keystroke is folded to upper case, case-checked against the combat command set, and dispatched.

The combat command set consists of letter keys A-Z plus a small set of control codes (Escape, Ctrl-S, Ctrl-B, Space, digits, direction codes). Every letter and every special input is now pinned, and recognition is not the same as world-mode success. The parser routes its letters through two shared shapes plus a handful of direct calls.

**Shape A — the labelled prompt with a live-actor gate.** The helper prints the verb label, then requires that the acting combatant is still alive. A dead actor gets the short "Can't!" refusal and the prompt is re-issued at no cost. A live actor's command is handed to one shared world-mode delegate chosen by the letter, and the combatant's action ends. Six letters use this shape: `G` Get, `J` Jimmy, `O` Open, `R` Ready, `S` Search and `U` Use. Their delegates are the same handlers the world modes use — the shared tile-interaction overlay for Get/Jimmy/Open/Search, the status/equipment overlay for Ready, and the item-use handler for Use.

**Shape B — the shared "that verb means nothing here" responder.** The responder prints the verb label, appends one of three fixed tails (" what?", "-Not here", or "-Funny, no response!"), plays a two-tone refusal beep, and always re-prompts without cost. Twelve letters use it: `B` Board and `X` X-it take the first tail; `E` Enter, `F` Fire, `H` Hole up, `I` Ignite, `L` Look, `M` Mix, `N` New order, `Q` Quit and `V` View take the second; `T` Talk takes the third. `D` and `W` bypass the responder and print their own `D-What?` / `W-What?`, with the same no-cost re-prompt.

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
| **J** | Jimmy. Labelled prompt with the live-actor gate, then the shared Jimmy handler. |
| **K** | Klimb. Dispatches to the arena climb helper. It handles ladder up/down prompts, upward/downward combat exit attempts, and a limited in-arena climb/move case that mutates the active combat record; otherwise it prints a refusal. A blocked climb re-prompts at no cost; an applied climb ends the actor's action. |
| **L** | Look — shared refusal responder, second tail. This dispatcher does not run the world/town look flow. No cost. |
| **M** | Mix — shared refusal responder, second tail. It does not open the reagent mixer. No cost. |
| **N** | New order — shared refusal responder, second tail. No cost. |
| **O** | Open. Labelled prompt with the live-actor gate, then the shared Open handler. That handler carries no combat-specific branch of its own, so in an arena it behaves as it does on the surface. |
| **P** | Push. Prints the `Push-` label and calls the shared movable-tile handler directly, without the live-actor gate used by Shape A. In combat the handler uses the acting combatant as the coordinate anchor; a successful push or pull mutates the temporary arena tile/object state, advances that actor's arena position, dirties the redraw, and returns to the round loop. Ends the actor's action. |
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

**Pass 1 - Dispatch setup.** The per-actor dispatcher clears the actor's
combat-status presentation area, prepares narration scratch, and checks whether
the current slot should run a normal turn, yield to a queued animation/effect,
or continue into AI decision-making. Current evidence does not support a
general per-class AI script runner. The ordinary monster path is table and
helper driven: status/flee gates run first, then the class-flag special hook,
target selection, movement-direction synthesis, optional step/teleport logic,
and finally the same command parser used by player turns.

**Pass 2 - Per-class special ability hook and direction.** Before ordinary
movement is synthesized, monster AI runs a small class-flag hook. It is not a
general script runner: it reads the acting monster's class flag word and tests
three ability bits in fixed order.

- `0x0040` is the possess/charm-on-turn ability. It draws one uniform slot index
  in `[0, 31]` — a single draw, with no retry if the draw lands on an ineligible
  slot. The drawn slot is accepted only if it is party-side and none of
  marked-dead, phased/blinked, asleep-or-disabled, hidden/not-yet-revealed, or
  already controlled is set; because the ability hook itself only runs on
  monster-side actors, a monster can possess party members and never another
  monster. An accepted target then runs the normal resistance check, and the
  effect lands only when that check does not block. On landing: the target's
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
- `0x0800` is the blink/phase ability. It has an approximately one-in-eight
  chance per AI turn, toggles the actor's phase/hidden flag and linked visual
  tile between visible and hidden, and narrates the disappearance or return.
- `0x0400` is the summon-daemon ability. It has the same approximately
  one-in-eight chance gate and then makes **exactly one** attempt, using the
  same shared random arena probe and spawn-cell validator the player's Summon
  spell uses (`systems/magic.md`, Summoning and conjuration). No direction of
  any kind is consulted: the candidate cell is random, and if the probe lands
  off the arena, if the validator rejects the cell, or if the actor table is
  full, the ability simply ends for that turn with nothing placed — there is no
  retry budget. On success a Daemon-class actor (class 38) is placed at that
  cell, the acting monster's name and a short summoning line are printed with a
  sound, and the new actor's linked sprite plays the brief flame transition
  before settling on the Daemon tile. Unlike the player's Summon spell, this
  branch does **not** stamp the controlled bit (Section 6.1a) on the placed
  Daemon: a monster-summoned Daemon is an ordinary hostile.

The branches are tested in the order above; a class with multiple bits would
attempt possess first, then blink, then summon-daemon. The analyzed v1 data set
assigns possess, blink/phase, and summon-daemon rows as listed in
`monster-bestiary.md`; for any variant class carrying multiple turn-special
bits, the fixed branch order determines which branch is attempted first.
After this hook, the AI target picker and direction synthesis run as normal.

**Target selection** is the heart of Pass 2. Given the acting monster's slot index, the target picker walks the actor table backwards from slot 31 to slot 0, computes the truncated linear Euclidean distance to each candidate, and picks the closest one that survives a chain of filters:

- Not the acting monster itself.
- Slot is not empty and not marked dead.
- Not on the same *faction* - friend/foe is decided by a "slot-to-group"
  helper that maps each slot to a small group id.
- Grouping note: ordinary placed party actors and ordinary placed monsters
  start in opposite combat groups. The resolver recognises a monster-side actor
  from descriptor flags bit `0x40`, and the team-override that can invert a
  monster's default group lives in that monster's **per-class flag word**, not
  in the descriptor byte. The controlled bit `0x01` is not consulted here at
  all, so charming or possessing an actor does not by itself move it between
  factions. One shipped roster template is hard-wired hostile: whenever a
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
an interference check, not a resource gate. It reads the caster's current target
mapping; if that target exists, is a valid live/visible/awake actor, Negate Time's
`T` runtime tag is not active, and the target is at distance one from the caster,
the handler prints a newline, the target's actor name, and ` interferes!`, then
returns to combat command input before the shared spell dispatcher prompts for a
spell. If any of those conditions fail, combat proceeds to the shared spell
dispatcher. The charge, mana, level, and scene checks are still owned by that
dispatcher. The combat C-Cast path also checks the shared active-effect tag:
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
5. **On success**, the round walker's post-action render redraws the new positions.
6. **On failure**, narrate "Blocked!" — a short blocked-message and a beep tone are emitted; the actor stays in place.

A side path — controlled by special-combat state bits — runs a **post-step effect** when a placed-field, arena hazard, or special encounter mode is active. This hook is reached only after the step-or-attack primitive succeeds and commits the actor's new coordinate to both combat actor tables. Range failures, blocked cells, and failed attacks do not fire it. It is therefore the confirmed contact boundary for arena hazards and placed-field effects; Poison/Sleep field routing, Fire/Energy damage inputs, non-consuming contact, and combat-exit lifetime for placed fields are fixed below.

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
target returned by the helper, not whether the marker is placed. The post-action
hook matches marker coordinates against the actor's committed coordinate when
checking contact. The contact side resolves the actor at the field coordinate,
skips the current active actor slot, and does not run the creature-prompt
friend/foe lookup. Contact does not consume the marker: the hook applies the
field result and returns without clearing or aging the matched active-object
record. Poison Field contact first rejects actors whose linked active-object
tile/class byte is `>= 0x80`; accepted party targets are poisoned only if their
character status is Good, while monsters and already non-Good party targets fall
through to poison damage with no field-contact XP credit. Sleep Field contact
ignores dead party targets; otherwise it writes asleep status for party targets
or the combat sleep/disabled bit for non-party targets. Fire Field rolls raw
damage in `[1, 21]` before the normal random defense subtraction, and Energy
Field supplies raw zero to the same damage/value path. The traced
CAST/COMSUBS/COMBAT callbacks, the accepted-placement resident redraw helper,
the post-action contact hook, the generic active-object tick, and the monster
death/record-clear path do not contain a field countdown, decrement, or pre-exit
removal. Placed markers persist until combat exits, when the combat framer
restores the pre-combat active-object table.

Separate from player-cast field markers, one special combat tile-effect path
handles an actor being absorbed by a scripted field-like cell. The path runs
only from the special post-step hook after movement has committed. It validates
that the active combat descriptor is live, not already claimed by the
dead/removed bit, has the expected pending-action class, and is linked to an
active-object family whose class masks to the `0x3C` absorbable-field family. On
success it narrates the absorption, plays the effect, invalidates the current
active-player selector, updates the affected slot through the shared combat
effect helpers, and writes the shared combat-result marker consumed by dungeon
room cleanup. That marker is the low-level bridge into the terminal endgame
handoff when the caller is a qualifying dungeon room. In stock data, the
qualifying room is Doom's deepest room-id-fifteen arena; its metadata supplies
the special setup marker for this path. The dungeon-room setup pass reads that
marker from the arena metadata band, places it through the special active-object
path rather than as an ordinary monster, and preserves it as the active-object
family whose masked class matches the absorption hook. The unresolved portion is
now limited to per-subtype labels for unrelated special-placement values in the
same dungeon metadata scan, not the final-room handoff conversion.

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
shape. The item catalog now publishes the traced weapon-dispatch range/effect
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

**Damage modifiers.** Negative damage is clamped to zero and an "attack missed" status flag is raised so the narration reads as a miss. A magic value (decimal 99) is treated as **instant kill** — bypass HP, force the death path; used for between-round death finalisation and one-shot-kill spell effects. Magic Missile and Fireball reach this handler only after the spell-damage wrapper rolls raw damage (`1..16` and `1..30`, respectively) and subtracts a random defense roll based on the target's combat defense; Kill reaches it with the instant-kill sentinel and skips that defense subtraction. For party-member defenders, the damage roll reads the cached combat-defense byte in the character record at offset `+0x18`; factory-seed records carry value `7`. This is not one of the stat bytes earlier in the record — Strength `+0x0C`, Dexterity `+0x0D`, Intelligence `+0x0E`. The original game also defines a separate per-item defence contribution keyed by readied equipment, plus a small bonus that Protection's shared `P` tag was meant to add on top of it, but neither ever applies: every one of the per-item accumulations is guarded by a comparison that is tautologically true and therefore always skipped, and the resulting total is never consumed — one caller discards it, and the other is reachable only through an attribute-selector arm that no call site in the game ever selects. No traced combat path recomputes the character-defense byte from readied armour. Treat the intended contribution as an original-game defect and a deliberate decision point for a port; do *not* generalise it into "worn equipment has no effect on combat", because the surviving to-hit computation reads other character-record fields whose relationship to equipment has not been traced. The target's per-class flags are consulted: a "halve damage" flag halves *physical* (non-magical) damage; an "immune to physical" flag zeroes it.

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
two ring ids. A party member wearing Ring of Invisibility is marked with the
same hidden/suppressed combat flag that the target picker rejects, and the
linked visual/effect byte is changed while the ring is active; removing that
ring in combat clears the hidden flag. A party member wearing Ring of
Regeneration participates in a regeneration pass: each living wearer has a
1-in-8 chance to recover 1 HP, capped by that character's maximum HP. During
the combat round loop, either Ring of Invisibility or Ring of Regeneration has
a separate 1-in-16 removal check; on the accepted outcome, the game prints the
ring-vanish feedback, plays the short timed sound, and clears the first matching
ring from that character's readied equipment slots.

**Active-effect display counter.** Protection, Quickness, Mass Charm, and
Negate Magic install a single shared visible tag/counter rather than writing a
per-character status byte. A resident update helper ages this counter: zero and
255 are inert, other values decrement when that helper runs, and expiry clears
the visible tag and requests a redraw. This counter is not the time system's
torch/light-spell counter; do not model it as one decrement per minute or per
full actor-table sweep. The traced combat-side aging endpoint is the
active-player/selection cleanup path; Negate Time's `T` tag uses the same counter
shape, while the per-turn clock cleanup only observes `T` to skip minute
advancement. The tag is not display-only.
Protection's `P` tag has no effective consumer: the defence bonus it was meant
to add rides on a per-item defence total that is both unreachable and never
read, so Protection changes no combat number. Combat damage reads the cached
party defense byte instead.
Quickness's `Q` tag randomly gates player-side combat command dispatch with a
0..1 roll; Mass
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

The character status byte is the load-bearing summary value: `'G'` good, `'P'` poisoned, `'D'` dead, `'S'` asleep, `'C'` charmed, `'A'` ashes, plus other state-specific letters. The `C` the stats panel shows during combat is not read from this byte: it is a presentation override driven by the controlled/charmed descriptor bit (Section 6.1a), and the Charm spell writes `'G'`, never `'C'`, into a party target's status byte. Other systems read the byte to decide whether the character can act, can be selected as active player, or counts toward the party-defeat check.

## 13. Per-monster-class data

Several aspects of combat behaviour are driven by per-class tables that the spawning, AI, and damage paths all consult — small fixed-stride arrays in the data segment, indexed by monster class byte.

| Table                            | Purpose                                                                                                                                          |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Combat-class spawn-count byte    | The default spawn count field of the eight-byte class stat row, indexed by the encounter's base class id (never by the arena index). Combined with the random reroll it decides how many monsters spawn; the largest shipped value is sixteen. |
| Per-class companion class        | Forty-eight entries indexed by class id, values are class ids. Early spawned monsters roll a one-in-nine chance to be created as the base class's companion class instead of the base class. Published in `catalogs/monster-bestiary.md`. |
| Per-class flag word              | Sixteen bits per class. Includes split-on-damage, halve-damage-when-physical, immune-to-physical, faction-override, vanish-on-death, special death checks, the turnable-attack flag consumed by Amulet/Turning, ranged/effect branch selection, the magic-immune ranged/effect gate, teleport-capable movement, and the turn special bits for possess, blink/phase, and summon-daemon. |
| Ordinary AI helper state         | Not a class script table. Ordinary monster decisions use the combat actor/effect records, target-selection scratch, per-class flag/stat tables, and shared helper outputs such as the AI step vector. Slot-local position, target, phase, flee, and visibility data remain in the combat actor/effect tables. |
| Per-class display/narration data | Pointer data used by combat narration and class labels; this is not an AI behavior table.                                                        |
| Per-class stat record            | Eight bytes per class: combat tier, speed seed/base-step input, HP-comparison byte for chest/encounter team-flip checks, defense rating, attack-damage cap, maximum HP, default spawn count, and default kill/drop cap. Maximum HP initializes monster HP and supplies the reward-unit input. The attack and defense bytes are consumed by the computed attack resolver; this row is not a flat damage/hit lookup matrix. |
| Per-class name pointers          | Sixteen-bit pointers per class to the printable monster name strings.                                                                            |

A monster's class id is set at spawn time and never changes (death may cause a tile swap, but the class stays). The forty-eight-row class space is shared: classes 0-3 are the four human party sprites (Mage, Bard, Fighter, Avatar), classes 4-15 are townsfolk and special NPC actors, and classes 16-47 are the bestiary. Note that the descriptor's owner/target/class field is overloaded: for a seated party member it holds the character's roster slot index, and only for monsters and objects does it hold a class id. The AI's friend/foe filter relies on the descriptor faction tag and the slot index range rather than on that field alone.

The 48-row stat table boundary is part of the public combat contract: party
combat classes, special NPC classes, and monsters share the same eight-byte row
shape. The ordinary friend/foe filter uses the combat slot index range and
descriptor faction tag rather than a separate class-family table.

The grouping helper therefore combines actor-family defaults (descriptor flags
bit `0x40` identifies the monster side), the per-class team-override flag from
the monster's class flag word, and the single hard-wired hostile roster template
described in Section 9, rather than consulting a separate faction table. That
last override is guarded so that it can never apply to the player's own
character.

## 14. Victory, defeat, and escape

Three exit conditions end combat; each sets one of the round-loop's flag bytes, and the per-round epilogue checks them.

**Victory.** When every hostile actor has been killed (no non-party slot has the "alive and active" flag bits set), the round-loop exits with result code "1". The framer then restores the suspended world state, refreshes party stats, and returns to the calling mode. Combat death paths may have produced temporary loot markers and a raw reward unit while the combat-instance tables were live, but the traced framer does not merge those active-object bytes into the restored world table or propagate the helper's return value as a post-combat award. The traced SJOG calls reached from COMBAT are command-time delegates and per-round helpers, not an after-victory loot-conversion pass. Ordinary terrain-trigger removal happens after the framer, in the resident caller that invokes the post-combat object reconciler for the original trigger slot. This settles the combat-exit boundary: ordinary attack/spell experience can be credited before the framer restores the world, the original trigger slot can be cleared or rewritten by the caller-side reconciler, and any body-like food/gold result belongs to later Search/Get interaction with that rewritten slot. Arbitrary combat corpse markers, party gold, karma, and any victory bonus are not automatic framer outputs. No separate victory message prints — the death-tile transitions tell the story.

**Defeat.** When the entire party is dead, asleep, or otherwise inactive, the engine sets the defeat flag and the round loop returns "0". There is no command that reaches the defeat exit deliberately: an earlier revision of this section described combat `Q` as an abandon-party command that did so, and that is withdrawn — the combat parser refuses `Q` like the other meaningless verbs (Section 8). What happens next is not decided by combat: control returns to the exploration loop that framed the fight, and that loop's next per-turn party-capability check sees the result. A wipe with nobody left able to act and nobody asleep runs the rescue/refuge cinematic specified in `systems/blackthorn.md` Section 7 — which restores the party and resumes play at Lord British's Castle, so an ordinary wipe is not a terminal game-over. A wipe that leaves a sleeping member instead simply passes turns until someone wakes or dies.

**Escape.** Moving outside the arena reaches the out-of-bounds combat leave helper. Ship-style fights can refuse the attempt, and constrained encounters require party exits to share the established exit direction. Once the helper accepts, it sets the leave-combat path; the first accepted trigger per fight prints the exit presentation and the round loop exits with code "1". Surviving party members and monsters are not given a chance to land final blows once that helper accepts. The Escape key is different: its escape handler scans for active-not-dead foes and refuses while any remain, so it is a cleanup/victory exit path rather than the ordinary flee-with-enemies-live path. The `X` letter does not reach that handler at all — the combat parser refuses it outright (Section 8).

The framer's restore phase runs the same way for all three — the only difference is the result code returned. Combat time advances from the round loop's round-counter wrap, which fires the per-turn cleanup with a one-minute increment; a separate one-minute exit increment is not part of the currently traced framer restore.

## 15. Hooks into other systems

Combat is built on top of several other systems and integrates cleanly with each.

- **Text output.** All combat narration flows through the per-cell emitter and wrap-aware string printer described in `text-output.md`. Combat does not maintain its own text window; it writes to whichever window was active before the fight.

- **Input.** The player command handler reads via the same wait-for-input routine described in `input.md`. The scene byte is set to the combat sentinel during the fight, so the world-tick step is suppressed; the cursor blink is the only background animation. Free-text and Y/N prompts within combat use the same prompt-mode mechanism.

- **Time.** Combat advances time at one specific point — when the round counter wraps inside a round (corresponding to one full actor walk under typical game pacing). The wrap fires the per-turn cleanup with a one-minute increment, exactly as the town and dungeon loops do.

- **Rendering and tile effects.** The post-round maintenance pass sweeps the
  runtime combat terrain/effect grid, dispatches per-cell visual or hazard
  effects, blinks the player cursor, and optionally draws a secondary marker.
  It is not the ownership point for placed-field lifetime; field markers still
  persist until combat exit unless an explicit command or spell removes them.

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
  ranged/effect branch selection and resistance gating, faction override,
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
  routing: the combat-mode branches inside the shared Get, Jimmy, Search, Klimb,
  Yell and member-select delegates are surveyed but not enumerated one branch at
  a time. Two are settled negatively — the shared Open handler and the escape
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

- **Multi-target spells.** Several combat spells are AOE or multi-target effects (Tremor, Poison Wind, Death Wind, Flame Wind). The effect-dispatch mechanism handles them by walking the actor table and applying the spell to each cell in the AOE; per-actor effect application can reuse the damage-and-status handler. Tremor's loop is exact at public semantic depth: no faction filter, 1..20 damage per accepted actor, shared damage/status application, and returned reward credited to caster experience. The separate active-target attack wrappers are also exact at public semantic depth: Magic Missile rolls 1..16, Fireball rolls 1..30, and Kill passes the decimal 99 instant-kill sentinel after the shared aiming/projectile path accepts a collision target. The directed wind-cone family prompts for a cardinal direction and builds the widening clipped cone specified in `systems/magic.md`, with up to 63 de-duplicated arena coordinates. The shared scan de-duplicates actors and skips common empty/status-masked records, but neither that scan nor the Sleep/Poison Wind/Death Wind/Flame Wind per-effect branches run the friend/foe lookup or reject same-faction actors. Sleep applies party sleep status or descriptor byte 2 bit `0x08` for non-party targets, Poison Wind applies a resistance/random gate before poison status, Death Wind uses the decimal 99 instant-kill sentinel, and Flame Wind rolls raw 1..30 damage; the two damage winds credit returned monster-kill reward units to the caster with the normal 9999 cap. Mass Charm is now covered as a class-threshold active-effect target-selection remap rather than an actor-table damage/status scan. Field contact is bounded to the post-step effect hook, and combat field casting reaches a shared arena-field helper before splitting placement from application. Placed fields live as active-object markers in the temporary combat table, and the contact scan matches those markers by coordinate while skipping only the current active actor slot; contact applies without consuming the marker. Poison Field skips linked active-object classes `>= 0x80`, poisons only Good party members, and otherwise falls through to poison damage with no field-contact XP credit. Sleep Field skips dead party members and otherwise writes party sleep status or descriptor byte 2 bit `0x08` for non-party targets. Fire Field contact rolls raw 1..21 before defense, Energy Field supplies raw zero to the same path, and the placement path has no Fire/Sleep/Energy random acceptance gate once impact resolution confirms an in-arena cell. Field markers are not aged by the placement, contact, redraw, generic active-object tick, or monster death/record-clear paths; they persist until combat exit restores the pre-combat active-object table.

- **Status narration.** "Sleep!", "Poison!", "Charm!" lines are not produced by the damage-and-status handler. They live in separate per-effect handlers (one per status). The exact wording and trigger mechanics belong in those handlers' specs.

- **Active-effect side effects.** The shared display counter for Protection,
  Quickness, Mass Charm, and Negate Magic is now traced through cast setup and
  the counter-aging boundary. Combat distinguishes that path from the
  time/render cleanup on ten-ready-action wraps; zero and 255 are inert, other
  values decrement at the reached cleanup endpoints, and expiry clears the
  shared tag and requests redraw. Negate Time's `T`/10 runtime tag uses the same
  counter shape, but the clock cleanup only observes `T` to suppress minute
  advancement. Confirmed consumers are the equipped-item statistic helper's
  Protection `P` bonus, Quickness's `Q` player-dispatch random gate, Mass Charm's `C`
  class-threshold AI-target remap, and Negate Magic's `N` combat-cast
  absorption path.

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

- Terrain-combat entry chain retrace of 2026-08-22 - outdoor arena selection from
  world terrain plus ship state, the class-id derivation and its separation from
  the arena index, the reachable spawn-count invariant, the forty-eight-entry
  companion-class table, and the party-seating pass that runs before monster
  placement. Source provenance: derived from private analysis notes
  `../u5-decomp/notes/combat_entry_arena_selection_2026-08-22.md`,
  `../u5-decomp/functions/ULTIMA_EXE/0x6150_combat_enter_terrain.md`,
  `../u5-decomp/functions/ULTIMA_EXE/0x6936_combat_round_engine.md`,
  `../u5-decomp/functions/ULTIMA_EXE/0x60EC_load_combat_audio.md`,
  `../u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`, and
  `../u5-decomp/functions/ULTIMA_EXE/0x6506_combat_monster_place.md`.
- The combat enter/exit framer with its three-way entry-mode dispatch, save-and-restore of player position and the dynamic-objects table, the scene-byte sentinel, and the post-combat active-player check — derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The combat-exit tile-graphics restoration dispatch reached from the framer's
  sampled restoration flag -- derived from
  `u5-decomp/functions/ULTIMA_EXE/0x6FBC_post_combat_trap.md`.
- The terrain-combat setup, the class-row spawn-count lookup, the dormant optional Fisher-Yates branch in the terrain helper, the early-spawn companion-class roll, and the single-attacker town-style override — derived from `u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`.
- The combat monster-placement writer that initializes renderer-facing and combat descriptor records -- derived from `u5-decomp/functions/ULTIMA_EXE/0x6506_combat_monster_place.md`.
- The ambush/camp-attack reveal-slot helper, including mode gating, one-shot
  reveal-coordinate consumption, arena terrain stamping, and redraw ordering --
  derived from
  `u5-decomp/functions/COMBAT_OVL/0x111A_reveal_ambush_at_coord.md`.
- The per-round walk over the thirty-two-slot actor table, the phase-counter mechanic, the round-counter wrap, the dispatch to player vs. monster handlers, and the three exit conditions — derived from `u5-decomp/functions/COMBAT_OVL/0x0B94_combat_main_loop.md`.
- The post-round combat terrain/effect sweep, player-cursor blink marker, and
  secondary-marker render hook -- derived from
  `u5-decomp/functions/ULTIMA_EXE/0x56AC_combat_post_round.md`.
- The per-actor turn dispatcher, complete dispatcher-level combat command map
  for all twenty-six letters and seven special inputs, the AI synthesis path for
  monster turns, the verb-stitching narration buffer, and the unified
  per-letter parser — derived from
  `u5-decomp/functions/COMBAT_OVL/0x063E_actor_ai_or_command.md`.
- Delegated combat command targets and edge behaviour for SJOG
  Get/Jimmy/Open/Search/Klimb, CMDS escape/Yell/Push, and ZSTATS
  Ready/Z-stats - derived from
  the corresponding COMBAT command table plus
  `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`,
  `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md`,
  `u5-decomp/functions/CMDS_OVL/0x17EC_cmds_escape.md`,
  `u5-decomp/functions/CMDS_OVL/0x1418_cmds_yell.md`,
  `u5-decomp/functions/CMDS_OVL/0x161A_cmds_push.md`, and
  `u5-decomp/functions/ZSTATS_OVL/_OVERVIEW.md`, with
  `u5-decomp/notes/cross_mode_behavior_matrix.md` as a cross-mode check.
- The negative post-combat SJOG boundary -- COMBAT reaches SJOG for in-round
  command delegates and helpers, not for an after-victory loot sweep -- derived
  from `u5-decomp/functions/COMBAT_OVL/_OVERVIEW.md` and cross-checked against
  `u5-decomp/notes/system-trace_combat-round.md`.
- The special combat absorption marker producer that bridges qualifying dungeon
  room cleanup into ENDGAME -- derived from
  `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md` and the
  ENDGAME caller census in
  `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- The caller-side post-combat original-slot reconciler -- derived from
  `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md` and
  `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md`.
- The absence of combat-exit gold/karma/victory-bonus writes is derived from
  the traced combat framer, COMBAT round loop, and relevant COMBAT-to-SJOG call
  coverage; later body food/gold staging is owned by
  `u5-decomp/functions/SJOG_OVL/0x01F2_sjog_corpse_grant.md` and
  `u5-decomp/functions/SJOG_OVL/0x1458_sjog_inventory_add.md`.
- The AI target-selection helper, the backwards walk and filter chain, the Mass
  Charm active-effect tag remap with class-threshold random gate, the
  Doom and Shadow Lord phase/hidden suppression exceptions, the ordinary invisibility filter, the
  first-five-party-slot fallback guard, centre fallback flee-marker writer,
  linear truncated Euclidean distance scoring with closest-wins tie-break, and the unit-step
  direction output with flee inversion — derived from
  `u5-decomp/functions/COMBAT_OVL/0x0D30_target_picker.md` and the sibling
  COMBAT damage/death note that identifies the same random-byte helper.
- The combat slot-to-group helper, including party/monster default inversion,
  the monster-side descriptor bit `0x40` test, and the per-class team-override
  flag, derived from
  `u5-decomp/functions/ULTIMA_EXE/0xD476_slot_to_group_id.md` and
  `u5-decomp/functions/COMBAT_OVL/0x13E2_slot_team_resolve.md`.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/0xD476_slot_to_group_id.md` -- the hard-wired
  hostile roster template, the guard that keeps roster record zero out of the
  override, the census of shipped roster names confirming exactly one match, and
  the confirmation that character creation and the Ultima IV import name only
  roster record zero. The roster-relocation paths that move whole records
  between slots -- the companion join/leave paths, the usurper's capture scene,
  and New Order -- were each checked to confirm that none of them can move the
  player-named record out of record zero and that none writes player-supplied
  text into another record; see
  `u5-decomp/functions/SHOPPES3_OVL/0x02AE_leave_companion.md`,
  `u5-decomp/functions/SHOPPES3_OVL/0x04E6_inn_main.md`,
  `u5-decomp/functions/BLCKTHRN_OVL/0x03AE_jail_party_member.md` and
  `u5-decomp/functions/CMDS_OVL/0x0DDC_cmds_new_order.md`. Cross-checked against
  `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md`.
- Note for save-tooling authors: a hand-edited save could in principle make one
  of the other roster records match the shipped traitor template's name shape
  and so flip that companion to the monster side. No path in the shipped game
  reaches that state, so an implementation keyed to the roster record itself is
  behaviourally equivalent; the distinction matters only to code that validates
  or migrates save files.
- The controlled/charmed bit contract in Section 6.1a — its four writers, its
  three readers, the Charm toggle as the only in-combat clear, the fact that the
  round walker does not dispatch on it, and the separation of the
  asleep/magically-disabled bit from the controlled/charmed bit (including the
  exact five-term condition the stats panel uses to draw the `C` override:
  party-side set, monster-side clear, dead clear, controlled bit set, owner
  field equal to the drawn row), together with the withdrawal of the earlier
  reading of the roster status letter `C` as "casting" (it means charmed) —
  derived from
  `u5-decomp/notes/2026-08-22_combat-status-magic-verify.md`,
  `u5-decomp/notes/2026-08-22_combat-status-magic-retrace.md`,
  `u5-decomp/functions/COMSUBS_OVL/0x00F4_monster_special_ability_tick.md`,
  `u5-decomp/functions/COMBAT_OVL/0x0226_actor_attack_target.md`, and
  `u5-decomp/functions/COMBAT_OVL/0x063E_actor_ai_or_command.md`.
- The HP-bucket wound-score classifier, low-HP morale writer for the fleeing
  flag, and fear/panic spell route that forces combat current HP into the
  critical bucket — derived from
  `u5-decomp/functions/COMBAT_OVL/0x1A5C_compute_wound_score.md` and
  `u5-decomp/formats/data-ovl.md`.
- Protection's equipped-item-statistic bonus, Quickness's player-side dispatch gate, Negate Magic's combat-cast absorption path, Negate Time's `T`/10 runtime tag, and the active-effect counter-aging rule — derived from local ULTIMA.EXE, COMBAT, CAST, CAST2, and SJOG helper analysis summarized without copying implementation text.
- Equipped Ring of Invisibility and Ring of Regeneration combat behaviour,
  including hidden-flag marking, wearer healing, and combat-round removal checks
  -- derived from `u5-decomp/functions/ULTIMA_EXE/0x6794_combatant_set_carrier.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x6936_combat_round_engine.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x6E60_remove_inventory_match.md`.
- The damage application and status transitions, the per-monster-class flag word's effect on damage and death, the special-class death paths, the slime-divide replication path, and the combat-local attacker experience credit — derived from `u5-decomp/functions/COMBAT_OVL/0x1574_narrate_status_change.md`, `u5-decomp/functions/COMBAT_OVL/0x194A_resolve_attack_damage.md`, `u5-decomp/functions/COMBAT_OVL/0x18BA_apply_party_status_or_damage.md`, and `u5-decomp/functions/ULTIMA_EXE/0x3F14_sat_add_word.md`.
- Amulet/Turning's combat passive branch and ranged/effect scatter boundary —
  derived from `u5-decomp/functions/COMBAT_OVL/0x0226_actor_attack_target.md`,
  `u5-decomp/functions/COMBAT_OVL/0x014E_apply_ranged_attack.md`, and
  `u5-decomp/functions/COMSUBS_OVL/0x0822_attack_geometry_resolver.md`.
- The weapon/spell damage-row split, target selection handoff, item-id keyed
  range/effect rows, ranged/projectile apply path, and shared to-hit formula --
  derived from
  `u5-decomp/functions/COMSUBS_OVL/0x0C52_dispatch_spell_or_weapon.md`,
  `u5-decomp/functions/COMSUBS_OVL/0x0A68_cast_spell_effect.md`,
  `u5-decomp/functions/COMBAT_OVL/0x0226_actor_attack_target.md`,
  `u5-decomp/functions/COMBAT_OVL/0x014E_apply_ranged_attack.md`, and
  `u5-decomp/functions/COMBAT_OVL/0x14D6_attack_to_hit_roll.md`.
- Monster ranged/effect side-table row values and row attribution -- derived
  from `u5-decomp/formats/data-ovl.md` and cross-checked against the COMBAT and
  COMSUBS ranged/effect consumers above.
- Shared saturating byte/word arithmetic used by stat and inventory mutation paths — derived from `u5-decomp/functions/ULTIMA_EXE/0x3EF0_sat_add_byte.md` and sibling helper notes.
- The monster movement fallback, teleport-capable movement bit, random legal
  arena-cell candidate path, surrounded check, in-arena step test, and linked
  combat-record/active-object coordinate updates — derived from
  `u5-decomp/functions/COMBAT_OVL/0x0EE4_monster_step_or_teleport.md` and
  `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md`.
- The step-or-attack primitive — direction-to-unit-step translation, arena range check, on-success and on-failure narration, and the post-step effect gate — derived from `u5-decomp/functions/SJOG_OVL/0x1C56_actor_step_or_attack.md`.
- The dungeon-room special source conversion for the final Doom absorbable
  marker -- derived from
  `u5-decomp/functions/DNGLOOK_OVL/0x117E_setup_room_npcs.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x6506_combat_monster_place.md`, and local
  binary verification of `DUNGEON.CBT`.
- The monster special-ability hook, including possess, blink/phase,
  summon-daemon, branch ordering, chance gates, and baseline class-flag
  assignments, derived from
  `u5-decomp/functions/COMSUBS_OVL/0x00F4_monster_special_ability_tick.md`
  and the `DATA.OVL` class-flag table.
- The combat-side C-Cast interference gate -- target mapping, target validity,
  visibility/awakeness, Negate Time suppression, and adjacency -- derived from
  `u5-decomp/functions/COMSUBS_OVL/0x09FC_check_spell_prereqs.md`.
- The shared spell dispatcher used by combat casts — derived from `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`.
- The combat spell-damage wrapper used by Magic Missile, Fireball, and Kill — derived from local CAST, COMSUBS, and COMBAT helper analysis summarized without copying implementation text.
- The Clone spell's allocation and random legal arena placement behaviour — derived from local CAST and COMBAT helper analysis summarized without copying implementation text.
- The dynamic-objects table that combat overlays and the sprite animator that walks it during world ticks — derived from `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
- The fog/visibility post-pass that consumes the same active-object table during world rendering — derived from `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md`.
- The combat AI target-range primitive, which computes truncated linear Euclidean distance between two arena coordinates — derived from `u5-decomp/functions/ULTIMA_EXE/0xDC42_range_to_target.md`.
- The data-region correction that rules out a combat damage/hit-chance matrix and identifies the combat-instance faction tagging and per-class stat-record shape — derived from `u5-decomp/formats/data-ovl.md`.
- The combat-arena file layout — 352-byte record stride, 11×11 terrain grid, metadata band, outdoor and dungeon-encounter banks — derived from `u5-decomp/formats/maps.md`.
- The character-record layout consulted by damage application and the active-player restore — derived from `u5-decomp/formats/saves.md`.
- The death-branch contract in Section 6.3 -- branch ordering, the incorporeal
  and vanish class-flag arms, the Gazer and Gargoyle exceptions, the arena
  terrain gate, which branches release the slot, and the drop-cap byte written
  into the active-object auxiliary byte -- derived from the 2026-08-22 retrace in
  `u5-decomp/functions/COMBAT_OVL/0x1574_narrate_status_change.md`.
- The `1..30` range of the roll helper used by both drop gates -- derived from
  `u5-decomp/functions/ULTIMA_EXE/0x3ABE_roll_1_to_30.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x2092_random_byte_in_range.md`.
- The three placement modes, the party-side versus monster-side flag-bit
  assignment, and the marker-only mode -- derived from the 2026-08-22 retrace in
  `u5-decomp/functions/ULTIMA_EXE/0x6506_combat_monster_place.md`.
- The framer's ambush entry branch, its setup target, and its discarded slot
  argument -- derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`
  and `u5-decomp/notes/2026-08-22_dungeon-ambush-arena.md`.
- The per-letter combat command map of Section 8 — the two shared delegate
  shapes, the three refusal tails, the direct-call letters, the exact re-prompt
  rule, and the withdrawal of the earlier U-Use, X-it and Quit readings — plus
  the encounter-size damper's full life cycle in Section 5. Source provenance:
  derived from private analysis note
  `../u5-decomp/notes/oq-closures_2026-08-22_combat-encounter.md`, with
  `../u5-decomp/functions/COMBAT_OVL/0x0544_prompt_with_string.md`,
  `../u5-decomp/functions/SJOG_OVL/0x1F26_sjog_verb_not_here.md`,
  `../u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`, and
  `../u5-decomp/functions/CAST_OVL/0x1792_use_item.md`.
- Combat's own typeahead toggle, its Escape / Space / actor-select bindings, and
  the arena targeting cursor as the game's only eight-way input surface. Source
  provenance: derived from private analysis note
  `../u5-decomp/notes/oq-closures_2026-08-22_commands-dispatch.md` and
  `../u5-decomp/functions/COMSUBS_OVL/0x0504_arena_cursor_picker.md`.
