# Monster Bestiary

A reference catalog of the hostile creature classes currently covered by the
DATA.OVL and combat analysis. This document is descriptive and table-driven; it
does not specify the combat round loop, target picker, or encounter spawner in
full. Use this as the lookup table when implementing combat actor creation,
monster display names, class traits, death handling, raw reward-unit derivation,
default loot-roll inputs, and best-effort encounter placement.

## 1. Overview

Ultima V's combat data uses a shared class table for party members, town actors,
special NPCs, and monsters. The monster bestiary starts at class 16 and runs
through class 47, with two identity gaps at classes 42 and 43. Class 42 has no
decoded name and an all-zero stat row in the analyzed table. Class 43 is the
same: no decoded name and an all-zero stat row. Treat both as reserved identity
gaps rather than spawned monsters. Classes 12 through 15 are included
separately because the combat notes identify them as hostile or special NPC
classes that use the same damage, reward-unit, and death-resolution machinery
as monsters.

The confirmed per-class data supports these fields:

- **Class** - the combat class id stored in a combat actor record.
- **Sprite run** - the active-object sprite byte run produced from the class id,
  four sequential frames per class. This is a runtime active-object identifier,
  not a file offset. Final sprite-sheet tile-id verification belongs to
  `catalogs/tile-catalog.md` and renderer presentation QA, not to the class
  stat table.
- **HP** - initial monster HP loaded into the combat actor record at placement.
- **Reward unit** - the small raw value returned by the damage/death handler
  when the class dies. Current analysis shows it is derived from HP as
  `floor(HP / 4) + 1`. Combat-local attack and spell/effect callers can consume
  the returned value immediately as party-attacker experience, capped at
  `9999`; the combat framer does not forward it as a separate post-combat
  award. This catalog does not define any additional victory XP, gold, karma,
  loot, or score effect of that value.
- **Drop cap** - the class byte used by the default monster-death drop gate.
  The first random check decides whether the combat-instance active-object
  becomes a dead-monster/drop marker; when it does, byte five of that record
  stores this drop-cap value. A second random check may set bit `0x80` in the
  same byte as a special-drop marker. The combat framer restores the pre-combat
  world active-object table after the round loop, so this marker is not a
  durable world object by itself. Zero means the current notes do not show a
  default drop bound for that class; it does not prove the absence of all
  post-kill effects.
- **Charm threshold** - the class byte used by Mass Charm's target-selection
  remap gate. While Mass Charm's shared `C` tag is active, a monster target pick
  rolls one uniform random byte in `[0, 255]`; the acting monster is remapped to
  neutral group 0 only when the roll is strictly greater than this threshold.
- **Traits** - decoded combat flags or class-specific death paths. Undecoded flag
  bits are deliberately omitted rather than named speculatively. A blank trait
  cell therefore means "no decoded trait here," not "no flag bits are set."
  Ranged/effect attack selection, the scene-scoped magic-immune gate, and the
  per-type ranged/effect side-table bytes are combat-system readers. Their
  dispatcher semantics are specified in `systems/combat.md`; the clean
  row-value publication for the hostile and special classes is listed below.

The eight-byte class stat records have a fixed semantic layout even where this
catalog does not print every per-class value. The row fields are combat tier,
speed seed for phase timing, an HP-comparison byte used by chest/encounter
team-flip checks, defense rating, attack-damage cap, maximum HP, default spawn
count, and default kill/drop cap. Initial HP, reward-unit input, drop-cap input,
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

| Class | Actor / creature | Tier | Speed | Flip HP | Defense | Attack cap | HP | Spawn count | Drop cap |
|------:|------------------|-----:|------:|--------:|--------:|-----------:|---:|------------:|---------:|
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

## 3. Ranged/Effect Side Rows

The following rows publish the class-indexed side metadata consumed by the
combat ranged/effect path. The range/effect selector is the attack range cap in
the AI attack path; the spell/weapon dispatcher also treats value `1` as the
zero-damage sentinel that routes through effect handling. The payload byte is
forwarded to the ranged/effect resolver and spell/effect dispatcher as the
class's effect/accuracy payload. Scene resistance means the class participates
in the special combat-context ranged/effect abort gate. Cast-like branch marks
the separate class flag that can consume the action through the cast/effect
narration branch when its prerequisite state is active.

| Class | Actor / creature | Range/effect selector | Payload | Scene resistance | Cast-like branch | Pre-gate bypass |
|------:|------------------|----------------------:|--------:|------------------|------------------|-----------------|
| 0 | Mage (party row) | 7 | 4 | yes | - | - |
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

These values do not change the trait table's meaning: the Amulet/Turning
scatter branch is the target-side response to the same scene-resistance class
family when a party target wears the amulet, while the side-table selector and
payload bytes control range, effect routing, and forwarded effect parameters.

## 4. Shared AI And Reward Units

Monster turns run through the same command-dispatch architecture as player
turns: the AI path runs status and class-flag gates, picks a target, produces a
movement direction, synthesizes the equivalent command byte, and uses the
normal combat command parser. The target picker scans the 32 combat slots,
filters out empty, dead,
same-faction, suppressed, and invisible actors, then chooses the closest
surviving enemy by truncated Euclidean distance between arena cells. One
saved-combat scene, Doom, and one special monster class, Shadow Lord, bypass the
extra suppressed-state filter, but not the ordinary invisibility filter. If no
usable party target is visible, the AI can fall back toward the centre of the
arena and mark pending-action monsters for follow-up. Cause Fear is a confirmed
upstream flee route: it forces accepted hostile actors into the critical-HP
state, and the wound-score morale classifier writes the flee flag from that
state. A lower-tier summon/tame-style spell helper also sets the same
actor-state flag while repurposing eligible live non-party, non-humanoid actors;
that path is a spell-side activation/repurpose effect rather than morale. The
no-target centre fallback is the other traced direct writer: it marks eligible
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
| `team override` | The class participates in special faction handling used by target selection. |
| `vanish branch` | On death, the class prints the vanish narration, leaves the gravestone-style marker in the temporary combat view, clears the combat actor, and bypasses the default drop-marker path. |
| `special death` | A class-specific tile/effect transition runs on death. |
| `possess` | On a monster AI turn, the class may pick a random eligible party target, run resistance, and mark the target controlled for combat. Daemon-class possessors self-clear after a successful landing path. |
| `blink` | On a monster AI turn, the class may toggle its phase/hidden state and linked visual tile. |
| `summon-daemon` | On a monster AI turn, the class may attempt to place a Daemon-class actor near the AI step direction. |
| `poison/status attack` | The class's attack can route through the shared party-status/damage helper before ordinary melee damage. Against a Good party member this can apply poison with zero ordinary damage and no attacker experience. |
| `turnable attack` | When this class targets a living party member wearing Amulet/Turning with a ranged or special effect attack, half of attempts are forced into the scattered-impact path instead of the ordinary hit-roll result. |
| `teleport-capable` | If ordinary attack/action handling falls through to movement, a class with this flag can attempt a random legal arena-cell move before ordinary stepping. |

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
| 31 | Insect Swarm | `0xBC..0xBF` | 5 | 2 | 0 | 1 | - | Swarm encounter; also associated with the Insect Swarm spell |
| 34 | Python | `0xC8..0xCB` | 10 | 3 | 0 | 8 | poison/status attack | Snake or trap encounter |
| 46 | Rot Worm | `0xF8..0xFB` | 5 | 2 | 0 | 6 | poison/status attack | Dungeon or underworld vermin encounter |

Slime division is the only decoded replication behavior in this group.
Rat, spider, python, and rot-worm poison/status attacks are decoded in the
shared attack resolver and listed in the trait column above. The Gremlin
cast-like branch row is published in Section 3; no additional Gremlin-specific
resource theft or nuisance writer is promoted beyond shared closest-target AI,
ranged/effect routing, and default damage/death paths.

## 7. Wilderness And Dungeon Monsters

These are the main hostile monster classes for outdoor and dungeon combat. The
encounter system confirms the terrain setup's first-spawn plus
leader/follower-style replacement model, but not a full terrain distribution per
class. The contexts below are therefore broad.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 26 | Mimic | `0xA8..0xAB` | 30 | 8 | 20 | 12 | team override | Chest-like or ambush-style monster |
| 27 | Reaper | `0xAC..0xAF` | 40 | 11 | 25 | 12 | team override; turnable attack | Forest or fixed dungeon encounter |
| 28 | Gazer | `0xB0..0xB3` | 20 | 6 | 0 | 25 | special death; possess; turnable attack | Eye-burst death effect |
| 29 | Crawler | `0xB4..0xB7` | 35 | 9 | 0 | 12 | - | Dungeon or underworld encounter |
| 30 | Gargoyle | `0xB8..0xBB` | 40 | 11 | 0 | 5 | splits; team override; special death | Terrain-hazard transition before normal cleanup; pixel details belong to combat presentation QA. |
| 32 | Orc | `0xC0..0xC3` | 10 | 3 | 11 | 10 | team override | Humanoid wilderness or dungeon group |
| 33 | Skeleton | `0xC4..0xC7` | 20 | 6 | 13 | 5 | physical half | Undead encounter |
| 35 | Ettin | `0xCC..0xCF` | 30 | 8 | 17 | 12 | team override | Large humanoid encounter |
| 36 | Headless | `0xD0..0xD3` | 20 | 6 | 12 | 8 | team override | Wilderness or underworld encounter |
| 37 | Wisp | `0xD4..0xD7` | 40 | 11 | 0 | 20 | possess; teleport-capable | Magical or spectral encounter |
| 38 | Daemon | `0xD8..0xDB` | 75 | 19 | 0 | 25 | physical half; possess; turnable attack | High-tier magical/dungeon encounter |
| 39 | Dragon | `0xDC..0xDF` | 99 | 25 | 30 | 25 | summon-daemon | High-tier wilderness or dungeon encounter |
| 40 | Sand Trap | `0xE0..0xE3` | 80 | 21 | 25 | 5 | - | Desert or fixed trap-like encounter |
| 41 | Troll | `0xE4..0xE7` | 15 | 4 | 15 | 9 | - | Mountain, bridge, or wilderness encounter |
| 44 | Mongbat | `0xF0..0xF3` | 20 | 6 | 5 | 15 | - | Flying or cave-style encounter |
| 45 | Corpser | `0xF4..0xF7` | 40 | 11 | 0 | 8 | - | Underworld or fixed dungeon encounter |

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
arenas from the triggering active-object class and populates up to twenty-six
combat actors.

For a terrain fight:

- The base monster count comes from the encounter base class's stat row. For
  stock ordinary terrain combat the outdoor arena id and base class id are the
  same value, so this can be described as a per-arena count at encounter level;
  the surrounding bytes are still class stats, not terrain weights. Counts of
  1, 8, and 16 are exact; other counts are rolled into a 1-to-max range.
- A "fortunes of war" flag can cause the count roll to be repeated.
- Town-style hostility overrides the count to one attacker.
- Placement uses sixteen arena slots supplied by the selected arena's metadata
  and cached in resident scratch before placement. Terrain fights use
  deterministic slot order; ambushes can shuffle the slots.
- The first placed monster uses the triggering arena class. For later placements,
  actors whose placement index is below `(count / 4) + 1` may use a per-arena
  replacement class when the replacement predicate permits it; later actors reuse
  the triggering class. This is the confirmed basis for the leader/follower
  shorthand used elsewhere.

Dungeon room encounters use the same combat framer and select arenas from the
dungeon encounter bank. No traced dungeon chest path currently selects a
`DUNGEON.CBT` arena. Room-trigger selection, per-arena spawn counts, placement
slots, and replacement-tile behavior are encounter/arena data contracts owned
by `systems/encounters.md`, `systems/dungeon-mode.md`, and `formats/cbt.md`;
this bestiary owns the class rows consumed after a room arena has chosen actor
classes.

## 10. Completion Boundaries

**Complete in this catalog:**

- All named monster classes currently supported by the DATA.OVL name table:
  Sea Horse through Shadow Lord, excluding identity-gap classes 42 and 43.
- Hostile/special NPC combat classes confirmed by the shared combat table:
  Guard, Wanderer, Blackthorn, Lord British.
- Initial HP, raw reward unit, raw drop-cap byte, Mass Charm threshold,
  active-object sprite run, full eight-field stat rows, and decoded combat
  traits for every listed class.
- Ranged/effect side-table row values for hostile and special classes,
  including the Mage party-row boundary, the range/effect selector, payload,
  scene-resistance rows, the Gremlin cast-like branch row, and the Mimic
  pre-gate bypass row.
- Shared AI target-selection behavior and the confirmed first-spawn,
  replacement-class, and follower placement model.

**Owned by sibling specs rather than this catalog:**

1. Class-flag publication is complete at behavioral-trait depth. The
   eight-byte class-stat row layout is specified, and the decoded traits above
   publish row assignments for damage modifiers, faction override, death
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
   selection, per-arena spawn counts, placement slots, and replacement-tile
   behavior are also specified by the encounter, dungeon-mode, and `.CBT`
   specs. This catalog does not duplicate those tables per monster row; a
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
   runtime class identifiers used by combat actor setup.
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

- `u5-decomp/formats/data-ovl.md` - resident data segment overview, monster name
  and combat table regions, ranged/effect side rows, and DATA.OVL completion
  notes.
- COMBAT overlay damage/status-resolution note - damage, raw reward unit,
  drop-roll markers, class flags, split, vanish, and special-death behavior.
- COMBAT overlay target-picker note - target filtering, faction handling,
  nearest-target scoring, and flee-direction inversion.
- COMBAT overlay monster movement note and SJOG auxiliary combat helpers -
  teleport-capable movement, surrounded checking, and in-arena step validity.
- COMBAT overlay actor AI/command-dispatch note - synthesized monster command
  dispatch and shared combat command parser.
- COMSUBS overlay monster-special note - possess, blink/phase,
  summon-daemon, branch order, and baseline class-flag assignments.
- ULTIMA executable combat-framer note - combat entry branches and
  town-hostility count override.
- ULTIMA executable terrain-target wrapper and SJOG auxiliary combat helpers -
  caller-side original trigger-slot reconciliation.
- ULTIMA executable terrain-combat setup note - encounter count roll, placement
  slots, replacement-class selection, and active-object placement.

**Public specs cross-checked:**

- `u5-spec/systems/combat.md`
- `u5-spec/systems/encounters.md`
- `u5-spec/systems/overworld.md`
- `u5-spec/catalogs/tile-catalog.md`
- `u5-spec/catalogs/spell-list.md`

## 12. Cross-References

- `systems/combat.md` - combat round loop, actor table, damage/status
  application, and victory/escape framing.
- `systems/encounters.md` - random encounters, ambushes, dungeon room fights,
  and post-combat world reconciliation.
- `catalogs/tile-catalog.md` - broad tile and active-object class partitions.
- `catalogs/spell-list.md` - summon and field spells that can introduce or
  interact with creature classes.
