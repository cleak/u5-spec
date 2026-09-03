# Monster Bestiary

A reference catalog of the hostile creature classes currently covered by the
DATA.OVL and combat analysis. This document is descriptive and table-driven; it
does not specify the combat round loop, target picker, or encounter spawner in
full. Use this as the lookup table when implementing combat actor creation,
monster display names, class traits, death handling, raw reward-unit derivation,
default loot-roll inputs, and best-effort encounter placement.

## 1. Overview

Ultima V's combat data uses a shared class table for party members, town actors,
special NPCs, and monsters. All forty-eight rows have the same eight-byte shape,
and Section 2 now publishes every one of them. Classes 0 through 11 are the
human/townsfolk actor classes (Section 2 gives their rows because terrain combat
can and does spawn them - the pirate boarding action uses class 1, and the four
party sprites are classes 0 through 3). The monster bestiary proper starts at
class 16 and runs through class 47, with two identity gaps at classes 42 and
43. Class 42 has no
decoded name and an all-zero stat row in the analyzed table. Class 43 is the
same: no decoded name and an all-zero stat row. Treat both as reserved identity
gaps rather than spawned monsters. Classes 12 through 15 are included
separately because the combat notes identify them as hostile or special NPC
classes that use the same damage, reward-unit, and death-resolution machinery
as monsters.

> **The sprite-run column is an actor-byte column, and several of its values
> collide with unrelated terrain ids.** A sprite byte and a map-cell terrain id
> are indices into different halves of the same atlas, so the same numerals name
> different artwork. The three collisions that have actually misled readers of
> this repository, all with the tile-asset masks of `systems/animation.md`
> Section 12:
>
> | Sprite run in this catalog | Atlas entry it draws | The identical numerals as a terrain id |
> |---|---|---|
> | Orc `0xC0..0xC3` | `0x1C0..0x1C3` | The flame masks for the torch, brazier and spit |
> | Ettin `0xCC..0xCF` | `0x1CC..0x1CF` | The flame masks for the fireplace, street lamp, candelabrum and stove |
> | Headless `0xD0..0xD3` | `0x1D0..0x1D3` | The diagonal wedge tiles the water composite uses as its stencil |
>
> The shipped description table settles it independently: its actor-half records
> for `0x1C0..0x1C3`, `0x1CC..0x1CF` and `0x1D0..0x1D3` read "an orc", "an
> ettin" and "a headless", while its terrain-half records for `0xC0..0xC3`,
> `0xCC..0xCF` and `0xD0..0xD3` hold the terrain half's placeholder. An engine
> that feeds a sprite byte straight to the atlas draws a stencil where the
> monster should be.

The confirmed per-class data supports these fields:

- **Class** - the combat class id stored in a combat actor record.
- **Sprite run** - the active-object **sprite byte** run produced from the class
  id, four sequential frames per class. This is a runtime active-object
  identifier, not a file offset and **not a tile-atlas index**. The atlas entry
  a sprite byte draws is `sprite_byte + 0x100`, because every actor resolves
  into the atlas's actor half (`catalogs/tile-catalog.md` Section 3.1). Final
  sprite-sheet tile-id verification belongs to `catalogs/tile-catalog.md` and
  renderer presentation QA, not to the class stat table.
- **HP** - initial monster HP loaded into the combat actor record at placement.
- **Reward unit** - the small raw value returned by the damage/death handler
  when the class dies. Current analysis shows it is derived from HP as
  `floor(HP / 4) + 1`. Combat-local attack and spell/effect callers can consume
  the returned value immediately as party-attacker experience, capped at
  `9999`; the combat framer does not forward it as a separate post-combat
  award. This catalog does not define any additional victory XP, gold, karma,
  loot, or score effect of that value.
- **Drop cap** - the class byte used by the default monster-death drop gate.
  Each of the two checks draws a near-uniform integer in `1..30`. The first
  check accepts when its draw is less than or equal to this drop cap; on
  acceptance the combat-instance active-object becomes the dead-monster/drop
  marker and byte five of that record stores **this drop-cap value itself**,
  not a random amount. The second check sets bit `0x80` in the same byte as a
  special-drop marker when its draw is strictly less than the drop cap. The
  combat framer restores the pre-combat world active-object table after the
  round loop, so this marker is not a durable world object by itself. Because
  the draw is never zero, a drop cap of zero can never accept: those classes
  always take the reject arm and leave the alternate no-drop death marker. The
  drop gate is also reached only from the ordinary death branch - classes with
  the vanish or incorporeal class-flag bit, the Gargoyle branch, and deaths on
  the excluded arena terrain values never run it at all
  (`systems/combat.md` Section 6.3).
- **Charm threshold** - the class byte used by Mass Charm's target-selection
  remap gate for an ordinary monster-side automatic actor. While Mass Charm's
  shared `C` tag is active, the target pick rolls one uniform random byte in
  `[0, 255]`; the acting slot is treated as party-aligned group 0 for that pick
  only when the roll is strictly greater than this threshold. Its descriptor is
  not rewritten. The generic selector uses a linked party member's Dexterity in
  the reachable controlled party-side automatic case instead of this class
  byte. *Corrected 2026-08-27:* the earlier description called group 0
  "neutral"; that label is withdrawn (Retraction R297).
- **Traits** - decoded combat flags or class-specific death paths. Undecoded flag
  bits are deliberately omitted rather than named speculatively. A blank trait
  cell therefore means "no decoded trait here," not "no flag bits are set."
  Ranged/effect attack selection, the scene-scoped magic-immune gate, and the
  per-type ranged/effect side-table bytes are combat-system readers. Their
  dispatcher semantics are specified in `systems/combat.md`; the clean
  row-value publication for the hostile and special classes is listed below.

The eight-byte class stat records have a fixed semantic layout even where this
catalog does not print every per-class value. The row fields are combat tier,
speed seed for phase timing, an endurance rating, defense rating, attack value,
maximum HP, default spawn count, and default kill/drop cap.

Which of those a *score* actually reads is narrower than this catalog used to
say. For an ordinary melee or ranged/effect to-hit, the shared actor-rating
selector returns the actor's per-actor **combat weight** - the jittered class
speed for a monster, the raw Dexterity byte for a party member - in every case
except the classes carrying the `zero-selector stat row` trait, which supply the
**tier**. The **endurance** byte is the monster-side rating of the separate
spell-*resistance* predicate. The **defense** byte is read directly by the
damage roller, never through the selector. *(**Corrected.** This paragraph
formerly said "the tier and endurance bytes are the two class-side ratings the
shared actor-rating selector can return into the to-hit and resistance scores",
which sends an implementer to the tier for forty-two of the forty-eight classes'
ordinary attacks. It is withdrawn; see `RETRACTIONS.md` R337. Earlier revisions
before that called the same two bytes inputs to a "chest/encounter team-flip"
comparison, which remains withdrawn.)* Initial HP, reward-unit input, drop-cap input,
Mass Charm threshold, and the teleport-capable movement flag consumer are
called out where they affect visible class behavior. Do not treat the stat
records as a flat damage or hit-chance matrix. The ranged/effect maximum-range
and payload bytes are separate class-indexed side tables, not extra columns in
the eight-byte stat record. The class-flag monster special hook is now bounded
to possess, blink/phase, and summon-daemon, with baseline row assignments
listed in the trait column where present.

## 2. Combat Stat Rows

The following table publishes the eight stat-record fields for the hostile and
special classes covered by this catalog. Columns are the clean field names from
the fixed class-stat layout:

| Class | Actor / creature | Tier | Speed | Endurance | Defense | Attack value | HP | Spawn count | Drop cap |
|------:|------------------|-----:|------:|--------:|--------:|-----------:|---:|------------:|---------:|
| 0 | Mage | 10 | 15 | 20 | 0 | 15 | 10 | 3 | 20 |
| 1 | Bard | 15 | 20 | 10 | 4 | 12 | 15 | 9 | 10 |
| 2 | Fighter | 20 | 15 | 10 | 8 | 15 | 20 | 6 | 15 |
| 3 | Avatar | 25 | 25 | 25 | 7 | 30 | 20 | 1 | 25 |
| 4 | Villager | 12 | 12 | 12 | 0 | 6 | 8 | 1 | 10 |
| 5 | Merchant | 12 | 12 | 18 | 0 | 6 | 8 | 1 | 10 |
| 6 | Jester | 12 | 18 | 12 | 0 | 6 | 8 | 1 | 10 |
| 7 | Bard (second row) | 12 | 16 | 14 | 0 | 6 | 8 | 1 | 10 |
| 8 | Pirate | 12 | 12 | 12 | 0 | 0 | 5 | 1 | 0 |
| 9 | Unnamed reserved | 12 | 12 | 12 | 0 | 0 | 5 | 1 | 0 |
| 10 | Child | 8 | 8 | 8 | 0 | 0 | 5 | 1 | 0 |
| 11 | Beggar | 8 | 8 | 8 | 0 | 0 | 5 | 1 | 0 |
| 12 | Guard | 22 | 30 | 10 | 6 | 30 | 99 | 8 | 5 |
| 13 | Wanderer | 30 | 30 | 30 | 30 | 99 | 99 | 1 | 0 |
| 14 | Blackthorn | 30 | 30 | 30 | 30 | 30 | 99 | 1 | 0 |
| 15 | Lord British | 30 | 30 | 30 | 30 | 99 | 99 | 1 | 0 |
| 16 | Sea Horse | 17 | 20 | 20 | 2 | 10 | 30 | 3 | 0 |
| 17 | Squid | 24 | 20 | 8 | 0 | 20 | 50 | 2 | 0 |
| 18 | Sea Serpent | 17 | 17 | 8 | 2 | 30 | 70 | 1 | 0 |
| 19 | Shark | 20 | 17 | 5 | 0 | 8 | 22 | 10 | 0 |
| 20 | Giant Rat | 5 | 20 | 5 | 0 | 6 | 10 | 10 | 5 |
| 21 | Bat | 5 | 30 | 5 | 0 | 6 | 5 | 16 | 0 |
| 22 | Giant Spider | 10 | 10 | 5 | 0 | 8 | 10 | 4 | 5 |
| 23 | Ghost | 1 | 20 | 10 | 0 | 12 | 20 | 6 | 0 |
| 24 | Slime | 6 | 6 | 2 | 0 | 4 | 10 | 16 | 0 |
| 25 | Gremlin | 10 | 21 | 10 | 2 | 4 | 10 | 13 | 12 |
| 26 | Mimic | 20 | 30 | 12 | 3 | 15 | 30 | 1 | 20 |
| 27 | Reaper | 20 | 25 | 12 | 4 | 20 | 40 | 3 | 25 |
| 28 | Gazer | 8 | 10 | 25 | 0 | 10 | 20 | 4 | 0 |
| 29 | Crawler | 17 | 15 | 12 | 0 | 15 | 35 | 4 | 0 |
| 30 | Gargoyle | 20 | 10 | 5 | 15 | 20 | 40 | 1 | 0 |
| 31 | Insect Swarm | 1 | 30 | 1 | 0 | 4 | 5 | 10 | 0 |
| 32 | Orc | 15 | 13 | 10 | 2 | 12 | 10 | 10 | 11 |
| 33 | Skeleton | 10 | 20 | 5 | 0 | 12 | 20 | 8 | 13 |
| 34 | Python | 5 | 18 | 8 | 1 | 8 | 10 | 4 | 0 |
| 35 | Ettin | 20 | 15 | 12 | 3 | 15 | 30 | 6 | 17 |
| 36 | Headless | 19 | 12 | 8 | 2 | 12 | 20 | 8 | 12 |
| 37 | Wisp | 8 | 30 | 20 | 0 | 20 | 40 | 4 | 0 |
| 38 | Daemon | 25 | 25 | 25 | 5 | 20 | 75 | 4 | 0 |
| 39 | Dragon | 30 | 25 | 25 | 10 | 30 | 99 | 2 | 30 |
| 40 | Sand Trap | 25 | 25 | 5 | 10 | 30 | 80 | 1 | 25 |
| 41 | Troll | 18 | 17 | 9 | 4 | 15 | 15 | 4 | 15 |
| 42 | Reserved gap | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 43 | Reserved gap | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 44 | Mongbat | 10 | 30 | 15 | 4 | 20 | 20 | 16 | 5 |
| 45 | Corpser | 17 | 10 | 8 | 0 | 15 | 40 | 4 | 0 |
| 46 | Rot Worm | 5 | 17 | 6 | 0 | 6 | 5 | 10 | 0 |
| 47 | Shadow Lord | 25 | 30 | 30 | 10 | 30 | 99 | 1 | 0 |

The **Attack value** column was published as `Attack cap` through earlier
revisions. That name is withdrawn (`RETRACTIONS.md` R336): a monster's ordinary
melee attack uses this byte **flat, with no random draw**, so it is the damage
the class brings every time and not the ceiling of a `1..N` roll. A Bat's 6 is
always 6. Only the *party* side of the ordinary damage roller randomizes its
attack value, from the readied item's `Attack max` in `catalogs/item-list.md`.
The **Defense** column is a roll on both sides: the roller subtracts an
inclusive `1..Defense` draw when this byte is non-zero and takes no draw at all
when it is zero. `systems/combat.md` Sections 11 and 12 own the full contract
and the worked Bat example.

Two further readers of these columns, for orientation: **Speed** is the seed of
the per-actor combat weight, which is both the defender term of every ordinary
to-hit score and the phase-timing input, so a fast class is harder to hit *and*
acts more often; and **Tier** becomes the attacker term only for the six
`zero-selector stat row` classes, which is why a Bat is more accurate than a
Gargoyle.

Notes on the low rows:

- Classes 0 through 3 are the four party sprites. A character's class letter
  maps to one of them at combat entry: Avatar to 3, Bard/Shepherd/Tinker to 1,
  Fighter/Paladin/Ranger to 2, Druid/Mage to 0. Seated party members read their
  HP and stats from the character record, not from these rows; the rows matter
  when a *hostile* actor of that class is spawned.
- Class 1 is the row terrain combat uses for the pirate/ship boarding action, so
  a boarded pirate ship yields nine fifteen-HP human combatants.
- Classes 8 and 9 are the passive/neutral classes: an actor placed with either
  class id gets the passive faction tag instead of the hostile one, so it is
  visible and addressable but never targeted.
- The shipped name data is two parallel tables, and classes 8 and 9 differ
  between them. Neither class has an entry in the **singular** name table —
  which is also blank for 42 and 43 — but the **group** encounter-banner table
  does name class 8, and that banner is where the name "Pirate" used for row 8
  above comes from; class 9's group entry is a placeholder, so it has no name
  in either table. **The placeholder set is larger than the blank set, and the
  two do not line up:** classes 3, 9, 13, 29, 42 and 43 all carry the
  one-character placeholder `x` as their group banner, yet classes 3, 13 and 29
  have perfectly real singular names (Avatar, Wanderer, Crawler). An engine that
  falls back to the singular name when the group entry looks empty will print
  `Avatar`, `Wanderer` or `Crawler` where the original prints a single `x`.
  Section 2.2 has the whole table. Rows 42
  and 43 are all-zero identity gaps; row 9's stats duplicate class 8's. The two
  gap rows sit exactly where the special outdoor animated sprite families
  (`0xE8..0xEB` and `0xEC..0xEF`) would map, which is consistent with those
  families never entering ordinary combat. Their zero spawn count is not a
  usable value - see the reachable-count invariant in `systems/encounters.md`
  Section 4.

### 2.1 Companion Classes

A separate forty-eight-entry resident table, indexed by class id, gives each
class a **companion class**. During terrain-combat placement, each spawn index
below the `(count / 4) + 1` threshold rolls a one-in-nine check; on success that
actor is created as the companion class instead of the base class. The values
are class ids, not tile ids.

| Class | Companion | Class | Companion | Class | Companion |
|---:|---:|---:|---:|---:|---:|
| 0 Mage | 33 Skeleton | 16 Sea Horse | 17 Squid | 32 Orc | 41 Troll |
| 1 Bard | 1 Bard | 17 Squid | 16 Sea Horse | 33 Skeleton | 0 Mage |
| 2 Fighter | 1 Bard | 18 Sea Serpent | 17 Squid | 34 Python | 22 Giant Spider |
| 3 Avatar | 3 Avatar | 19 Shark | 19 Shark | 35 Ettin | 36 Headless |
| 4 Villager | 4 Villager | 20 Giant Rat | 33 Skeleton | 36 Headless | 35 Ettin |
| 5 Merchant | 4 Villager | 21 Bat | 21 Bat | 37 Wisp | 23 Ghost |
| 6 Jester | 4 Villager | 22 Giant Spider | 20 Giant Rat | 38 Daemon | 39 Dragon |
| 7 Bard (second) | 4 Villager | 23 Ghost | 33 Skeleton | 39 Dragon | 39 Dragon |
| 8 Pirate | 4 Villager | 24 Slime | 24 Slime | 40 Sand Trap | 40 Sand Trap |
| 9 Unnamed | 4 Villager | 25 Gremlin | 26 Mimic | 41 Troll | 20 Giant Rat |
| 10 Child | 10 Child | 26 Mimic | 35 Ettin | 42 Gap | 42 Gap |
| 11 Beggar | 4 Villager | 27 Reaper | 21 Bat | 43 Gap | 43 Gap |
| 12 Guard | 12 Guard | 28 Gazer | 21 Bat | 44 Mongbat | 44 Mongbat |
| 13 Wanderer | 13 Wanderer | 29 Crawler | 24 Slime | 45 Corpser | 45 Corpser |
| 14 Blackthorn | 14 Blackthorn | 30 Gargoyle | 30 Gargoyle | 46 Rot Worm | 20 Giant Rat |
| 15 Lord British | 15 Lord British | 31 Insect Swarm | 24 Slime | 47 Shadow Lord | 38 Daemon |

Eighteen of the forty-eight classes are their own companion, which makes the
substitution a no-op for them; it is only observable for the rest.

### 2.2 Group Banner Names

A second forty-eight-entry resident table, parallel to the stat rows and to the
singular name table and indexed by the same class id, holds the **group banner
name** — the caption printed when a terrain fight begins
(`systems/combat.md` Section 4.1). It is a shipped table of finished strings.
There is no suffix rule to derive it from: nothing appends an `S`, and the
banner never consults the monster count, so the group form is printed even for a
single attacker.

Every entry is uppercase, letters and spaces only, with no trailing punctuation
and no line feed of its own. The longest is twelve characters, so no banner ever
wraps in the sixteen-column message window. The **Derived?** column says whether
the entry is exactly the singular name uppercased with an `S` appended: twenty-
two of the forty-eight are, and twenty-six are not.

| Class | Group banner | Singular name | Derived? |
|------:|--------------|---------------|----------|
| 0 | `WIZARDS` | Mage | no — different word |
| 1 | `BARD` | Bard | no — singular form |
| 2 | `FIGHTER` | Fighter | no — singular form |
| 3 | `x` | Avatar | no — placeholder |
| 4 | `VILLAGER` | Villager | no — singular form |
| 5 | `MERCHANT` | Merchant | no — singular form |
| 6 | `JESTER` | Jester | no — singular form |
| 7 | `BARD` | Bard | no — singular form |
| 8 | `PIRATES` | *(none)* | no — no singular counterpart |
| 9 | `x` | *(none)* | no — placeholder |
| 10 | `CHILD` | Child | no — singular form |
| 11 | `BEGGAR` | Beggar | no — singular form |
| 12 | `GUARDS` | Guard | yes |
| 13 | `x` | Wanderer | no — placeholder |
| 14 | `BLACKTHORN` | Blackthorn | no — proper noun |
| 15 | `LORD BRITISH` | Lord British | no — proper noun |
| 16 | `SEA HORSES` | Sea Horse | yes |
| 17 | `SQUIDS` | Squid | yes |
| 18 | `SEA SERPENTS` | Sea Serpent | yes |
| 19 | `SHARKS` | Shark | yes |
| 20 | `GIANT RATS` | Giant Rat | yes |
| 21 | `BATS` | Bat | yes |
| 22 | `SPIDERS` | Giant Spider | no — different word |
| 23 | `GHOSTS` | Ghost | yes |
| 24 | `SLIME` | Slime | no — singular form |
| 25 | `GREMLINS` | Gremlin | yes |
| 26 | `MIMICS` | Mimic | yes |
| 27 | `REAPERS` | Reaper | yes |
| 28 | `GAZERS` | Gazer | yes |
| 29 | `x` | Crawler | no — placeholder |
| 30 | `GARGOYLE` | Gargoyle | no — singular form |
| 31 | `INSECTS` | Insect Swarm | no — different word |
| 32 | `ORCS` | Orc | yes |
| 33 | `SKELETONS` | Skeleton | yes |
| 34 | `SNAKES` | Python | no — different word |
| 35 | `ETTINS` | Ettin | yes |
| 36 | `HEADLESSES` | Headless | no — irregular plural |
| 37 | `WISPS` | Wisp | yes |
| 38 | `DAEMONS` | Daemon | yes |
| 39 | `DRAGONS` | Dragon | yes |
| 40 | `SAND TRAPS` | Sand Trap | yes |
| 41 | `TROLLS` | Troll | yes |
| 42 | `x` | *(none)* | no — placeholder |
| 43 | `x` | *(none)* | no — placeholder |
| 44 | `MONGBATS` | Mongbat | yes |
| 45 | `CORPSERS` | Corpser | yes |
| 46 | `ROTWORMS` | Rot Worm | no — different word (no space) |
| 47 | `SHADOW LORD` | Shadow Lord | no — singular form |

The twenty-six non-derived entries break down as six placeholders (3, 9, 13, 29,
42, 43), eleven written in the singular (1, 2, 4, 5, 6, 7, 10, 11, 24, 30, 47),
two proper nouns that have no plural (14, 15), five that use a different word
from the singular table (0, 22, 31, 34, 46), one irregular plural (36), and one
with no singular counterpart at all (8).

Two entries are reachable without an index into this table. A hostile whose
masked sprite byte is below `0x40` never indexes it and prints the fixed literal
`PIRATES` — byte-identical to class 8's entry, but selected by a range test
rather than a lookup (`systems/encounters.md` Section 4). And class 47's
`SHADOW LORD` is the caption of the Shadow Lord fight, which is always a single
opponent.

This table is **not** `LOOK2.DAT`; both name tables are resident data, and the
banner strings do not appear in that file. *(Scope: literal search of the
shipped `LOOK2.DAT` for representative banner strings.)*

Source provenance: derived from private analysis in `u5-decomp/notes/`.

## 3. Ranged/Effect Side Rows

The following rows publish the class-indexed side metadata consumed by the
combat ranged/effect path. **Both side tables are dense forty-eight-entry
arrays with a defined byte for every class id, and every one of those rows is
now published below** (issue #187 question 9). There is no such thing as a class
without a row; the eleven party/NPC rows one through eleven that earlier rounds
recorded as "absent" were a gap in this catalog, not in the data, and an engine
that resolves "a class with no row" to "no attack" is answering a question the
data never asks.

**The range/effect selector.** Its meaning depends on which consumer reads it,
and the two do not agree above the melee value. In the AI attack resolver, on
the autonomous driver's path, it is an inclusive **maximum attack range**:
a target further away than the byte refuses the attack, distance exactly one
routes to melee, and any greater in-range distance takes the ranged/effect path.
In the shared spell/weapon dispatcher, on its non-party-side arm - the arm a
controlled monster acting at the player's prompt reaches, and the arm a
no-readied-item attempt reaches - value `1` is folded to zero and selects the
**melee / Aim-cursor arm**, while **any** higher value selects the cast/effect
arm unconditionally, at every distance including one, because that routine
contains no distance test at all. (That dispatcher's *party-side* arm does not
read these tables; it keys the same two decisions off the readied item's own
reach and payload rows in `catalogs/item-list.md`.) `systems/combat.md`
Section 11 carries the per-consumer table; do not merge the two into one rule.

*(**Corrected.** This paragraph previously said "the spell/weapon dispatcher
also treats value `1` as the zero-damage sentinel that routes through effect
handling". **That polarity is inverted and is withdrawn.** Value `1` is the
**melee** sentinel: it is normalised to zero and takes the ordinary adjacent
attack. `systems/combat.md` Section 8.2 has always said so for the same byte.)*

**The payload byte** is forwarded to the ranged/effect resolver and spell/effect
dispatcher as the class's effect-class payload. Its eight values are effect
classes, and value `0` is the first of the eight effect classes and selects a
distinct handler rather than meaning "no effect"; *what* it draws is **not
established** (a trailing-streak visual is the working reading, confidence
**probable**). The payload is consumed only on the ranged arm, so for a
class whose selector keeps it on the melee arm the payload is inert.

**Scene resistance** means the class participates in the special combat-context
ranged/effect abort gate. **Theft branch** marks the separate class flag that
replaces ordinary melee damage with the food-theft branch when the party's food
supply is non-empty; `systems/combat.md` Section 11 gives its sequence and its
draw. *(**Corrected**: this column was previously described as a "cast-like
branch" that "can consume the action through the cast/effect narration branch".
**That description is withdrawn** - the branch is not a cast, narrates no cast,
aims nothing and animates nothing. The row assignment is unchanged.)*

| Class | Actor / creature | Range/effect selector | Payload | Scene resistance | Theft branch | Pre-gate bypass |
|------:|------------------|----------------------:|--------:|------------------|------------------|-----------------|
| 0 | Mage (party row) | 7 | 4 | yes | - | - |
| 1 | Bard | 3 | 0 | - | - | - |
| 2 | Fighter | 1 | 0 | - | - | - |
| 3 | Avatar | 1 | 0 | - | - | - |
| 4 | Villager | 1 | 0 | - | - | - |
| 5 | Merchant | 1 | 0 | - | - | - |
| 6 | Jester | 1 | 0 | - | - | - |
| 7 | Bard (second row) | 1 | 0 | - | - | - |
| 8 | Pirate | 1 | 0 | - | - | - |
| 9 | Unnamed reserved | 1 | 0 | - | - | - |
| 10 | Child | 1 | 0 | - | - | - |
| 11 | Beggar | 1 | 0 | - | - | - |
| 12 | Guard | 15 | 2 | - | - | - |
| 13 | Wanderer | 9 | 4 | yes | - | - |
| 14 | Blackthorn | 9 | 3 | yes | - | - |
| 15 | Lord British | 9 | 4 | yes | - | - |
| 16 | Sea Horse | 5 | 4 | yes | - | - |
| 17 | Squid | 7 | 4 | - | - | - |
| 18 | Sea Serpent | 9 | 3 | - | - | - |
| 19 | Shark | 1 | 0 | - | - | - |
| 20 | Giant Rat | 1 | 0 | - | - | - |
| 21 | Bat | 1 | 0 | - | - | - |
| 22 | Giant Spider | 1 | 0 | - | - | - |
| 23 | Ghost | 1 | 0 | - | - | - |
| 24 | Slime | 1 | 0 | - | - | - |
| 25 | Gremlin | 1 | 0 | - | yes | - |
| 26 | Mimic | 2 | 5 | - | - | yes |
| 27 | Reaper | 9 | 4 | yes | - | - |
| 28 | Gazer | 5 | 6 | yes | - | - |
| 29 | Crawler | 1 | 0 | - | - | - |
| 30 | Gargoyle | 9 | 7 | - | - | - |
| 31 | Insect Swarm | 1 | 0 | - | - | - |
| 32 | Orc | 1 | 0 | - | - | - |
| 33 | Skeleton | 1 | 0 | - | - | - |
| 34 | Python | 3 | 5 | - | - | - |
| 35 | Ettin | 5 | 7 | - | - | - |
| 36 | Headless | 1 | 0 | - | - | - |
| 37 | Wisp | 1 | 0 | - | - | - |
| 38 | Daemon | 9 | 3 | yes | - | - |
| 39 | Dragon | 9 | 3 | - | - | - |
| 40 | Sand Trap | 1 | 0 | - | - | - |
| 41 | Troll | 5 | 2 | - | - | - |
| 42 | Reserved gap | 1 | 0 | - | - | - |
| 43 | Reserved gap | 1 | 0 | - | - | - |
| 44 | Mongbat | 1 | 0 | - | - | - |
| 45 | Corpser | 1 | 0 | - | - | - |
| 46 | Rot Worm | 1 | 0 | - | - | - |
| 47 | Shadow Lord | 9 | 3 | yes | - | - |

**Reading the eleven newly published rows.** Classes two through eleven all
carry selector `1` and payload `0`, so under **both** consumers they make an
ordinary adjacent melee attempt and nothing else: melee-only, adjacent-only,
with the payload inert. That agreement is the substantive correction, and it is
what an engine should implement for those ten classes. Class one (Bard) is the
exception and must **not** be given one merged rule: with selector `3` the AI
attack resolver gives it maximum range three, routing distance one to melee and
distances two and three to the ranged/effect path with payload `0`, while the
spell/weapon dispatcher sends it to the cast/effect arm at every distance
including one. Publish the entry point with the contract.

These values do not change the trait table's meaning: the Amulet/Turning
scatter branch is the target-side response to the same scene-resistance class
family when a party target wears the amulet, while the side-table selector and
payload bytes control range, effect routing, and forwarded effect parameters.

## 4. Shared AI And Reward Units

Monster turns are driven by the automatic actor driver, not by the command
path player turns use: the AI path runs status and class-flag gates, picks a
target, chooses a movement direction, and then calls the shared attack,
movement and special-ability primitives **directly**. It reads no key,
synthesises none, and enters no combat command parser. *(**Corrected**, issue
#185: this paragraph previously said monster turns "run through the same
command-dispatch architecture as player turns" and that the AI path
"synthesizes the equivalent command byte, and uses the normal combat command
parser". **That framing is withdrawn** - `RETRACTIONS.md` R353 and
`systems/combat.md` Section 11.1.)* The target picker scans the 32 combat slots,
filters out empty, dead,
same-faction, suppressed, and invisible actors, then chooses the closest
surviving enemy by truncated Euclidean distance between arena cells. One
saved-combat scene, Doom, and one special monster class, Shadow Lord, bypass the
extra suppressed-state filter, but not the ordinary invisibility filter. If no
usable party target is visible, the AI can fall back toward the centre of the
arena and mark pending-action monsters for follow-up. Cause Fear is a confirmed
upstream flee route: it sweeps all thirty-two combat slots and, for every
monster-side actor that is not one of the three protected special classes
(14 Blackthorn, 15 Lord British, 47 Shadow Lord) and that fails the shared
resistance check, drives that actor's combat HP counter to one and sets the
fleeing flag directly. Repel Undead is the same sweep with one extra condition:
the actor's class must also carry the undead class-flag bit. Both write only the
HP counter and the fleeing flag; neither creates, repurposes, tames, or
re-types an actor, and neither touches the controlled/charmed flag. Earlier
revisions of this catalog described Repel Undead as "a lower-tier
summon/tame-style spell helper" that repurposed eligible actors; that
description was wrong and is withdrawn, and it also omitted the undead-class
condition. The no-target centre fallback is the other traced direct writer: it marks eligible
monster-side slots with the flee flag and critical-HP marker. Once that flag
marks an actor as fleeing, the target picker reverses the chosen direction so
the same movement code handles both pursuit and retreat.

If an attack path does not consume the turn, monster movement uses the shared
movement fallback described in `systems/combat.md`: teleport-capable classes can
attempt a random legal arena cell, ordinary stepping uses the surrounded check
and in-arena step test, and successful moves update both the combat descriptor
and linked render object.

Current traces prove shared target selection, Cause Fear's HP-forced flee
setup, wound-score flee writes, flee inversion, and several per-class combat
flags. The bestiary therefore records only the class traits confirmed by the
damage, spell, target-picker, movement, and monster-special readers:

| Trait | Confirmed effect |
|-------|------------------|
| `splits` | If damaged but not killed, the class may clone itself into an empty combat slot. |
| `physical half` | Non-magical physical damage is halved before HP is reduced. |
| `physical immune` | Non-magical physical damage is reduced to zero. |
| `zero-selector stat row` | When the shared stat-selector helper is asked for this class's stat with a selector of zero, it returns the class stat row's first byte instead of the value the combat-weight path would give. Nothing about factions or sides is involved. *(Renamed 2026-08-23 from `team override`; see the withdrawal note below.)* |
| `vanish branch` | On death, the class prints the vanish narration, leaves the gravestone-style marker in the temporary combat view, clears the combat actor, and bypasses the default drop-marker path. |
| `special death` | A class-specific death transition runs instead of the terrain/drop path. Only two classes carry it: the Gazer, whose branch marks its own record and then places a live Insect Swarm at the death cell, and the Gargoyle, whose branch edits the arena terrain and releases the slot. |
| `possess` | On a monster AI turn, the class may pick a random eligible party target, run resistance, and mark the target controlled for combat. Daemon-class possessors self-clear after a successful landing path. |
| `blink` | On a monster AI turn, the class may toggle its phase/hidden state and linked visual tile. |
| `summon-daemon` | On a monster AI turn, the class may make one attempt to place a Daemon-class actor at a random legal arena cell. No direction is consulted, there is no retry, and the placed Daemon is an ordinary hostile — it does not receive the controlled/charmed marker the player's Summon spell stamps (`systems/combat.md` Section 9). |
| `poison/status attack` | The class's attack can route through the shared party-status/damage helper before ordinary melee damage. Against a Good party member this can apply poison with zero ordinary damage and no attacker experience. |
| `turnable attack` | When this class targets a living party member wearing Amulet/Turning with a ranged or special effect attack, half of attempts are forced into the scattered-impact path instead of the ordinary hit-roll result. |
| `teleport-capable` | If ordinary attack/action handling falls through to movement, a class with this flag can attempt a random legal arena-cell move before ordinary stepping. |

> *Corrected (2026-08-23).* The trait now called `zero-selector stat row` was
> published as `team override`, defined as participation "in special faction
> handling used by target selection". **That is withdrawn.** An exhaustive scan
> of every shipped code file for accesses to the per-class flag table finds
> exactly one instruction anywhere that tests this bit, inside the shared
> stat-selector helper, and it fires only for a monster slot asked for a
> zero-valued selector. Nothing about sides or factions is computed, and the
> helper writes nothing outside its own frame. The routine that actually
> resolves friend from foe reads per-actor descriptor bytes and one roster byte;
> it never reads the class-flag table at all. `systems/combat.md` Section 6.1a
> carries the same withdrawal with the scope limits.

**No-corpse death family.** Ten classes carry the low class-flag bit without the
vanish bit: Sea Horse, Squid, Sea Serpent, Shark, Bat, Ghost, Slime, Insect
Swarm, Wisp, and Daemon. Their deaths release the combat slot immediately and
write no tile marker and no drop byte at all - they never reach the Gazer,
Gargoyle, terrain, or drop-gate logic. Treat this as a first-class death branch,
not as a default kill whose roll happened to fail. The four vanish-bit classes
(Wanderer, Blackthorn, Lord British, Shadow Lord) are the other branch that
leaves the ordinary path, and they do write the vanish marker before releasing
the slot.

Default monster kills can update the combat-instance active-object table with
post-kill markers. The current notes confirm the class drop-cap marker and
special-drop high bit, and also confirm that the combat framer restores the
pre-combat active-object table instead of making those markers durable.
Combat-local attack and spell/effect callers can credit the returned damage or
reward unit directly to a living party attacker before framer exit. The
ordinary terrain-target caller can remove or rewrite the original trigger slot
after the framer returns, but that reconciler does not sweep all killed
combat-instance monsters into world loot. Food/gold from a rewritten
body/retrieval slot is later Search/Get behavior, not a class-table reward, and
the framer does not grant party gold, karma, score, or a separate victory bonus.
Classes that use a special death path may bypass the default drop path. In the
analyzed baseline, the vanish branch is assigned to the special boss-style
classes listed below rather than being an unused variant-data branch.

## 5. Aquatic Creatures

Aquatic classes are the water and sea encounter family. They are expected to
appear in ocean, shoal, ship, pirate, and water-bound encounter contexts. Exact
terrain-to-payload distribution is owned by `systems/encounters.md`; the rows
below publish class metadata rather than duplicating spawn tables.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 16 | Sea Horse | `0x80..0x83` | 30 | 8 | 0 | 20 | turnable attack | Water encounters |
| 17 | Squid | `0x84..0x87` | 50 | 13 | 0 | 8 | poison/status attack | Water encounters |
| 18 | Sea Serpent | `0x88..0x8B` | 70 | 18 | 0 | 8 | - | Dangerous water encounters |
| 19 | Shark | `0x8C..0x8F` | 22 | 6 | 0 | 5 | - | Water encounters |

Aquatic outdoor movement and passability are keyed by the sprite-run and
movement predicate families described in `systems/movement.md` and
`systems/active-objects.md`; do not infer those water rules from an unnamed
combat class flag. Any remaining aquatic high bits stay unnamed until a direct
combat or terrain consumer is identified.

## 6. Lesser Beasts And Undead

These are low- and mid-tier creatures that can appear in wilderness fights,
dungeon rooms, scripted/trap-like effects, or summoned/swarm effects. Dungeon
room and ambush mappings are encounter data, not additional class-row fields.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 20 | Giant Rat | `0x90..0x93` | 10 | 3 | 5 | 5 | poison/status attack | Low-tier wilderness or trap encounter |
| 21 | Bat | `0x94..0x97` | 5 | 2 | 0 | 5 | - | Low-tier dungeon or night encounter |
| 22 | Giant Spider | `0x98..0x9B` | 10 | 3 | 5 | 5 | poison/status attack | Wilderness, dungeon, poison-themed encounter |
| 23 | Ghost | `0x9C..0x9F` | 20 | 6 | 0 | 10 | physical half; blink | Undead or spectral encounter |
| 24 | Slime | `0xA0..0xA3` | 10 | 3 | 0 | 2 | splits | Replicating dungeon creature |
| 25 | Gremlin | `0xA4..0xA7` | 10 | 3 | 12 | 10 | - | Dungeon, trap, or nuisance encounter |
| 31 | Insect Swarm | `0xBC..0xBF` | 5 | 2 | 0 | 1 | - | Swarm encounter; also associated with the Insect Swarm spell. Additionally spawned mid-combat, one per death, by the Gazer's special-death branch (row 28) |
| 34 | Python | `0xC8..0xCB` | 10 | 3 | 0 | 8 | poison/status attack | Snake or trap encounter |
| 46 | Rot Worm | `0xF8..0xFB` | 5 | 2 | 0 | 6 | poison/status attack | Dungeon or underworld vermin encounter |

Slime division is the only decoded replication behavior in this group.
Rat, spider, python, and rot-worm poison/status attacks are decoded in the
shared attack resolver and listed in the trait column above. The Gremlin's own
branch row is published in Section 3.

*(**Corrected.** This paragraph previously continued "no additional
Gremlin-specific resource theft or nuisance writer is promoted beyond shared
closest-target AI, ranged/effect routing, and default damage/death paths."
**That negative is withdrawn.** The Gremlin has exactly such a writer, and it is
live in ordinary play: on a landed Gremlin attack, a three-in-four draw followed
by a non-empty party food supply prints `A <monster> stole some food!`,
subtracts five from the food supply saturating at zero, plays a rising cue,
requests a stats-panel refresh, and **consumes the attack in place of all damage
resolution**. The draw is taken even when the food supply is empty. Class 25 is
the only class in the shipped table carrying the flag. `systems/combat.md`
Section 11 gives the ordered sequence and the parity consequences.)*

## 7. Wilderness And Dungeon Monsters

These are the main hostile monster classes for outdoor and dungeon combat. The
encounter system confirms the terrain setup's first-spawn plus
companion-class substitution model (Section 2.1), but not a full terrain
distribution per class. The contexts below are therefore broad.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 26 | Mimic | `0xA8..0xAB` | 30 | 8 | 20 | 12 | zero-selector stat row | Chest-like or ambush-style monster |
| 27 | Reaper | `0xAC..0xAF` | 40 | 11 | 25 | 12 | zero-selector stat row; turnable attack | Forest or fixed dungeon encounter |
| 28 | Gazer | `0xB0..0xB3` | 20 | 6 | 0 | 25 | special death; possess; turnable attack | Eye-burst death: writes the eye-burst tile onto its own record, keeps the slot, runs no drop roll, and **places a live class-31 Insect Swarm at the death cell** through the ordinary monster-placement mode (tile `0xBC`, five HP, hostile), then redraws. The spawn is a real combatant, not a visual effect. |
| 29 | Crawler | `0xB4..0xB7` | 35 | 9 | 0 | 12 | - | Dungeon or underworld encounter |
| 30 | Gargoyle | `0xB8..0xBB` | 40 | 11 | 0 | 5 | splits; zero-selector stat row; special death | Writes the lava-pool byte into the arena terrain under the corpse, then releases the slot. It does **not** continue into the default kill path, so it leaves no corpse marker and no drop; pixel details belong to combat presentation QA. |
| 32 | Orc | `0xC0..0xC3` | 10 | 3 | 11 | 10 | zero-selector stat row | Humanoid wilderness or dungeon group |
| 33 | Skeleton | `0xC4..0xC7` | 20 | 6 | 13 | 5 | physical half | Undead encounter |
| 35 | Ettin | `0xCC..0xCF` | 30 | 8 | 17 | 12 | zero-selector stat row | Large humanoid encounter |
| 36 | Headless | `0xD0..0xD3` | 20 | 6 | 12 | 8 | zero-selector stat row | Wilderness or underworld encounter |
| 37 | Wisp | `0xD4..0xD7` | 40 | 11 | 0 | 20 | possess; teleport-capable | Magical or spectral encounter |
| 38 | Daemon | `0xD8..0xDB` | 75 | 19 | 0 | 25 | physical half; possess; turnable attack | High-tier magical/dungeon encounter |
| 39 | Dragon | `0xDC..0xDF` | 99 | 25 | 30 | 25 | summon-daemon | High-tier wilderness or dungeon encounter |
| 40 | Sand Trap | `0xE0..0xE3` | 80 | 21 | 25 | 5 | - | Desert or fixed trap-like encounter |
| 41 | Troll | `0xE4..0xE7` | 15 | 4 | 15 | 9 | - | Mountain, bridge, or wilderness encounter |
| 44 | Mongbat | `0xF0..0xF3` | 20 | 6 | 5 | 15 | - | Flying or cave-style encounter |
| 45 | Corpser | `0xF4..0xF7` | 40 | 11 | 0 | 8 | - | Underworld or fixed dungeon encounter |

The Sprite-run column here is an actor-byte column (Section 1). Three of its
runs — Orc `0xC0..0xC3`, Ettin `0xCC..0xCF` and Headless `0xD0..0xD3` — share
their numerals with driver mask ids in the atlas's terrain half; the atlas
entries these rows actually draw are `0x1C0..0x1C3`, `0x1CC..0x1CF` and
`0x1D0..0x1D3`.

Classes 42 and 43 are not listed as monsters because the name table has blank
entries for both. Their sprite runs would fall between Troll and Mongbat, but no
monster identity is currently supported by the local notes. Both rows have
all-zero stat records in the analyzed table; keep them as reserved identity gaps
rather than inventing monster names or runtime behavior.

## 8. Shadow And Special Classes

Shadow Lords and a few human special actors use the same combat class machinery.
They are separated from the ordinary monster rows because their encounter
contexts are scripted or NPC-driven rather than regular wandering monster
spawns.

| Class | Actor | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|-------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 12 | Guard | `0x70..0x73` | 99 | 25 | 5 | 10 | - | Town hostility or scripted guard fight |
| 13 | Wanderer | `0x74..0x77` | 99 | 25 | 0 | 30 | physical immune; blink; teleport-capable; turnable attack; vanish branch | Special NPC combat class |
| 14 | Blackthorn | `0x78..0x7B` | 99 | 25 | 0 | 30 | physical immune; possess; teleport-capable; turnable attack; vanish branch | Scripted boss or special encounter |
| 15 | Lord British | `0x7C..0x7F` | 99 | 25 | 0 | 30 | physical immune; blink; teleport-capable; turnable attack; vanish branch | Special protected NPC class |
| 47 | Shadow Lord | `0xFC..0xFF` | 99 | 25 | 0 | 30 | physical half; possess; teleport-capable; turnable attack; vanish branch | Scripted Shadowlord encounter |

The combat table also contains non-hostile town roles and party classes, but
those belong in an NPC roster rather than this bestiary. Guards are included
because the encounter and combat notes explicitly describe town-hostility fights
that convert an NPC into a single combat attacker.

One party/profession row still matters to combat trait consumers: the Mage row
uses the same turnable-attack flag that `systems/combat.md` assigns to the
Amulet/Turning scatter branch. It is not listed as a hostile monster class here
because no traced baseline encounter treats that row as a spawned creature, but
a byte-compatible combat table should preserve the flag if a scenario or
variant data set ever routes that class through the ranged/effect attack path.

## 9. Encounter Behavior Summary

The encounter system does not directly start most overworld fights. It normally
spawns a hostile active object near the party; combat begins when the player or
monster contacts the other. Terrain combat then chooses one of sixteen outdoor
arenas from the terrain under the triggering active object (plus the party's
vehicle state), derives the encounter's base class from that object's sprite
byte, and populates at most sixteen monster actors plus the seated party.

For a terrain fight:

- The base monster count comes from the encounter base class's stat row, indexed
  by class id and never by arena index. Counts of 1, 8, and 16 are exact; other
  counts are rolled into a 1-to-max range. Since the largest shipped count is 16
  and 16 is exact, a terrain encounter never spawns more than sixteen monsters.
- The early-game encounter-size damper repeats the count roll while it is set,
  which lowers the count; it is active for the first in-game month of a new game
  and off permanently afterwards (`systems/encounters.md` Section 5).
- Town-style hostility overrides the count to one attacker.
- Placement uses sixteen arena slots supplied by the selected arena's metadata
  and cached in resident scratch before placement. Ordinary terrain fights walk those
  slots in identity order. **Corrected 2026-08-31 (R306).** An earlier revision
  of this bullet said the terrain setup helper's placement-slot shuffle branch
  had no live caller, and that "ambush and rest/camp setup run through
  different helpers entirely"; both statements are withdrawn. The helper has
  **two** callers: the ordinary encounter route leaves the gating flag clear,
  and the surface camp-ambush route reaches the *same* helper through its
  command-overlay wrapper with the flag **set**, and forwards it — so the
  branch is live, and rest/camp does not bypass the helper
  (`systems/combat.md` Section 5, `systems/rest-and-camp.md`,
  `formats/cbt.md` Section 5). A still-earlier revision said "ambushes can
  shuffle the slots"; that remains withdrawn as stated, because the shuffle is
  reached by the *camp-ambush* route specifically rather than by ambushes in
  general.

  When the branch does run, it performs **fifteen random transpositions**, which
  is not a uniform permutation — an engine must reproduce the transposition
  sequence rather than substituting a uniform shuffle. Where an ambush-style fight does get a randomised arrangement —
  dungeon wandering-monster combat — the randomisation is performed upstream by
  the dungeon room painter when it writes the synthesised source band, not by
  the terrain helper's own placement-slot branch (`systems/dungeon-mode.md`
  Section 14.1). That branch is not dormant either - it is enabled on the
  surface camp-ambush route, where it does randomise which authored cells the
  monsters occupy (`systems/combat.md` Section 5).
- The first placed monster uses the encounter's base class. For later
  placements, actors whose placement index is below `(count / 4) + 1` may use
  the base class's **companion class** when the one-in-nine predicate permits
  it; later actors reuse the base class. The companion mapping is per class, not
  per arena, and is published in Section 2.1. This is the confirmed basis for
  the leader/follower shorthand used elsewhere.
- Party members are seated first, from the selected arena's own party entry
  coordinates, and do not occupy monster placement slots.

Dungeon room encounters use the same combat framer and select arenas from the
dungeon encounter bank. No traced dungeon chest path currently selects a
`DUNGEON.CBT` arena. Room-trigger selection, placement slots, and the
companion-class substitution are encounter/arena data contracts owned
by `systems/encounters.md`, `systems/dungeon-mode.md`, and `formats/cbt.md`;
this bestiary owns the class rows consumed after a room arena has chosen actor
classes.

## 10. Completion Boundaries

**Complete in this catalog:**

- All named monster classes currently supported by the DATA.OVL name table:
  Sea Horse through Shadow Lord, excluding identity-gap classes 42 and 43.
- Hostile/special NPC combat classes confirmed by the shared combat table:
  Guard, Wanderer, Blackthorn, Lord British.
- The low human/townsfolk classes 0 through 11, whose stat rows are now
  published in Section 2. Their traits, ranged/effect rows, and Mass Charm
  behaviour are not covered here; only the eight stat fields and the companion
  mapping are.
- The full forty-eight-entry companion-class mapping (Section 2.1).
- Initial HP, raw reward unit, raw drop-cap byte, Mass Charm threshold,
  active-object sprite run, full eight-field stat rows, and decoded combat
  traits for every listed class.
- Ranged/effect side-table row values for hostile and special classes,
  including the Mage party-row boundary, the range/effect selector, payload,
  scene-resistance rows, the Gremlin food-theft branch row, and the Mimic
  pre-gate bypass row.
- Shared AI target-selection behavior and the confirmed first-spawn,
  companion-class, and follower placement model.

**Owned by sibling specs rather than this catalog:**

1. Class-flag publication is complete at behavioral-trait depth. The
   eight-byte class-stat row layout is specified, and the decoded traits above
   publish row assignments for damage modifiers, the zero-selector stat-row
   select (**corrected 2026-08-23** from "faction override"), death
   branches, monster-turn specials, poison/status attacks, turnable attacks,
   and teleport-capable movement, including the Mage turnable-attack flag
   boundary outside the hostile-monster table. The common ranged/effect branch,
   the dual-use maximum-range/damage-selector byte, the scene-scoped
   magic-immune gate, and the ranged/effect payload-byte reader are specified
   in `systems/combat.md` and row-published above. Component bits that only
   appear through combined tests or still lack direct behavioral consumers are
   intentionally not named as separate public traits.
2. Monster special-action selection is bounded to the class-flag hook for
   possess, blink/phase, and summon-daemon. The analyzed v1 baseline assigns
   possess, blink, and summon-daemon as shown in the trait rows above; branch
   ordering remains data-driven for variants that set more than one turn-special
   trait. The target-picker exceptions, no-target centre fallback flee writer,
   out-of-arena leave/escape, and movement fallback contracts are specified in
   `systems/combat.md`, not a separate class-script table.
3. Outdoor random-spawn terrain buckets are specified in `systems/encounters.md`
   as ordered weighted active-object payload tables. Dungeon room arena
   selection, outdoor arena selection, and placement-slot geometry are also
   specified by the encounter, dungeon-mode, and `.CBT` specs. Spawn counts and
   companion classes are class-indexed and live here, in Section 2 and Section
   2.1. This catalog does not duplicate those tables per monster row; a
   monster-centric cross-index would be an optional convenience artifact, not a
   missing class-table contract.
4. Caller-side ordinary drop contents and post-combat reward consumers are
   specified at their system boundary. The default kill path can set a temporary
   class drop-cap marker and a special-drop high bit, and the damage/death
   handler returns a raw reward unit. Ordinary attack/spell experience credit is
   handled immediately by the damage caller when there is a living party
   attacker. The ordinary terrain-target caller can remove or rewrite the
   original trigger slot after the framer returns. If a later caller consumes a
   rewritten body/retrieval slot, that belongs to Search/Get/container rules,
   not the class table. The framer does not make arbitrary drop markers durable
   and does not grant party gold, karma, score, or a separate victory bonus.
5. Final sprite-sheet tile-id verification belongs to `catalogs/tile-catalog.md`
   and renderer presentation QA. The sprite-run bytes published here are the
   runtime class identifiers used by combat actor setup, and they are **actor
   bytes**: the atlas entry drawn is `sprite_byte + 0x100`. Do not read a
   sprite-run value as a map-cell terrain id; see the collision box in
   Section 1.
6. Class-specific death behavior is specified in `systems/combat.md`; the
   bestiary records the assigned classes and traits. Pixel-level death visuals
   and animation timing are presentation QA, not class-row metadata.
7. The damage handler's vanish-on-death branch is traced and assigned to
   Wanderer, Blackthorn, Lord British, and Shadow Lord in the analyzed
   baseline.

## 11. Sources

This catalog is cleanroom prose derived from the local analysis notes and the
existing public specs. It does not reproduce disassembly, decompiled code, data
offsets, raw private addresses, binary dumps, or private note prose.

**Private analysis sources used:**

- Terrain-combat entry chain retrace of 2026-08-22 - outdoor arena selection from
  world terrain plus ship state, the class-id derivation and its separation from
  the arena index, the reachable spawn-count invariant, the forty-eight-entry
  companion-class table, and the party-seating pass that runs before monster
  placement. Source provenance: derived from private analysis notes
  `../u5-decomp/notes/combat_entry_arena_selection_2026-08-22.md`,
  `../u5-decomp/functions/ULTIMA_EXE/`, and
  `../u5-decomp/functions/ULTIMA_EXE/`.
- The Cause Fear and Repel Undead sweeps described in the monster-AI section
  (the shared exclusion of the three protected special classes, Repel Undead's
  extra undead class-flag condition, the combat-HP-to-one plus fleeing-bit
  writes, and the withdrawal of the earlier "summon/tame-style repurpose helper"
  description): `u5-decomp/notes/2026-08-22_combat-status-magic-verify.md` and
  `u5-decomp/functions/CAST_OVL/all_spells.md`.
- `u5-decomp/formats/data-ovl.md` - resident data segment overview, monster name
  and combat table regions, ranged/effect side rows, and DATA.OVL completion
  notes.
- COMBAT overlay damage/status-resolution note - damage, raw reward unit,
  drop-roll markers, class flags, split, vanish, and special-death behavior.
- COMBAT overlay target-picker note - target filtering, faction handling,
  nearest-target scoring, and flee-direction inversion.
- COMBAT overlay monster movement note and SJOG auxiliary combat helpers -
  teleport-capable movement, surrounded checking, and in-arena step validity.
- COMBAT overlay actor AI/driver note - the automatic actor driver's direct
  calls into the shared attack, movement and special-ability primitives
  (**corrected, issue #185**: no command synthesis and no command parser -
  R353).
- COMSUBS overlay monster-special note - possess, blink/phase,
  summon-daemon, branch order, and baseline class-flag assignments.
- ULTIMA executable combat-framer note - combat entry branches and
  town-hostility count override.
- ULTIMA executable terrain-target wrapper and SJOG auxiliary combat helpers -
  caller-side original trigger-slot reconciliation.
- ULTIMA executable terrain-combat setup note - encounter count roll, placement
  slots, companion-class selection, and active-object placement.

**Public specs cross-checked:**

- `u5-spec/systems/combat.md`
- `u5-spec/systems/encounters.md`
- `u5-spec/systems/overworld.md`
- `u5-spec/catalogs/tile-catalog.md`
- `u5-spec/catalogs/spell-list.md`

- The rename of the `Attack cap` column to **Attack value** and the narrowing of
  which stat-row bytes an ordinary to-hit score actually reads (issue #183) --
  derived from private analysis in `../u5-decomp/notes/` and
  `../u5-decomp/functions/COMBAT_OVL/`. The full contract, the per-score hit
  table and a worked Bat example live in `systems/combat.md` Sections 11 and 12;
  `RETRACTIONS.md` R336 and R337 carry the withdrawals.

## 12. Cross-References

- `systems/combat.md` - combat round loop, actor table, damage/status
  application, and victory/escape framing.
- `systems/encounters.md` - random encounters, ambushes, dungeon room fights,
  and post-combat world reconciliation.
- `catalogs/tile-catalog.md` - broad tile and active-object class partitions.
- `catalogs/spell-list.md` - summon and field spells that can introduce or
  interact with creature classes.
