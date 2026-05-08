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
decoded name and no currently meaningful stat fields in the local notes. Class
43 also has no decoded name, but it does have nonzero bytes in still-unnamed
stat fields; treat it as unresolved, not as a confirmed empty slot or a known
monster. Classes 12 through 15 are included separately because the combat notes
identify them as hostile or special NPC classes that use the same damage,
reward-unit, and death-resolution machinery as monsters.

The confirmed per-class data supports these fields:

- **Class** - the combat class id stored in a combat actor record.
- **Sprite run** - the active-object sprite byte run produced from the class id,
  four sequential frames per class. This is a runtime active-object identifier,
  not a file offset. The final 512-tile catalog mapping still needs a separate
  verification pass.
- **HP** - initial monster HP loaded into the combat actor record at placement.
- **Reward unit** - the small raw value returned by the damage/death handler
  when the class dies. Current analysis shows it is derived from HP as
  `floor(HP / 4) + 1`. This catalog does not define the ordinary encounter XP,
  gold, karma, or score effect of that value; the currently traced COMBAT-level
  callers do not forward the value through the combat framer. Tremor is a
  spell-side exception that consumes the returned unit immediately as caster
  experience, capped at 9999.
- **Drop cap** - the class byte used by the default monster-death drop gate.
  The first random check decides whether the combat-instance active-object
  becomes a dead-monster/drop marker; when it does, byte five of that record
  stores this drop-cap value. A second random check may set bit `0x80` in the
  same byte as a special-drop marker. Zero means the current notes do not show a
  default drop bound for that class; it does not prove the absence of all
  post-kill effects.
- **Charm threshold** - the class byte used by Mass Charm's target-selection
  remap gate. While Mass Charm's shared `C` tag is active, a monster target pick
  rolls one uniform random byte in `[0, 255]`; the acting monster is remapped to
  neutral group 0 only when the roll is strictly greater than this threshold.
- **Traits** - decoded combat flags or class-specific death paths. Undecoded flag
  bits are deliberately omitted rather than named speculatively. A blank trait
  cell therefore means "no decoded trait here," not "no flag bits are set."

The eight-byte class stat records contain more data than this table exposes.
Armor, attack damage, spell power, movement cadence, unnamed flag bits, and
monster special-action or spell-like effect selection are not fully decoded
yet; section 8 records those gaps.

## 2. Shared AI And Reward Units

Monster turns run through the same command-dispatch architecture as player
turns: an AI path first stages a class-keyed intent, then produces a direction,
synthesizes the equivalent command byte, and uses the normal combat command
parser. The target picker scans the 32 combat slots, filters out empty, dead,
same-faction, suppressed, and invisible actors, then chooses the closest
surviving enemy. One saved-combat scene family and one special monster class
bypass the extra suppressed-state filter, but not the ordinary invisibility
filter. If no usable party target is visible, the AI can fall back toward the
centre of the arena and mark pending-action monsters for follow-up. Cause Fear
is a confirmed public writer of the flee flag. Once that flag, or any future
decoded setter, marks an actor as fleeing, the target picker reverses the chosen
direction so the same movement code handles both pursuit and retreat.

Current traces prove shared target selection, Cause Fear's flee setter, flee
inversion, and several per-class combat flags. The bestiary therefore records
only the class traits confirmed by the damage, spell, and target-picker readers:

| Trait | Confirmed effect |
|-------|------------------|
| `splits` | If damaged but not killed, the class may clone itself into an empty combat slot. |
| `physical half` | Non-magical physical damage is halved before HP is reduced. |
| `physical immune` | Non-magical physical damage is reduced to zero. |
| `team override` | The class participates in special faction handling used by target selection. |
| `vanish branch` | The damage handler has a vanish-on-death branch, but the analyzed `DATA.OVL` baseline does not assign its high flag bit to any listed class. |
| `special death` | A class-specific tile/effect transition runs on death. |

Default monster kills can update the combat-instance active-object table with
post-kill markers. The current notes confirm the class drop-cap marker and
special-drop high bit, but not the final item, gold, XP, karma, or score
interpretation. The raw reward unit is not forwarded by the traced COMBAT-level
caller path; Tremor consumes it only from its spell handler before that boundary.
Classes that use a special death path may bypass the default drop path. The
traced vanish branch remains an unassigned variant-data branch in this baseline.

## 3. Aquatic Creatures

Aquatic classes are the water and sea encounter family. They are expected to
appear in ocean, shoal, ship, pirate, and water-bound encounter contexts, but the
exact terrain-to-class distribution table has not been fully labelled.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 16 | Sea Horse | `0x80..0x83` | 30 | 8 | 0 | 20 | - | Water encounters |
| 17 | Squid | `0x84..0x87` | 50 | 13 | 0 | 8 | - | Water encounters |
| 18 | Sea Serpent | `0x88..0x8B` | 70 | 18 | 0 | 8 | - | Dangerous water encounters |
| 19 | Shark | `0x8C..0x8F` | 22 | 6 | 0 | 5 | - | Water encounters |

The aquatic classes carry several undecoded high or terrain flags. Current
combat notes do not yet prove whether these flags mean water-bound movement,
floating, terrain immunity, specialized movement, or spell-like action
selection.

## 4. Lesser Beasts And Undead

These are low- and mid-tier creatures that can appear in wilderness fights,
dungeon rooms, chest-trap style encounters, or summoned/swarm effects. Exact
dungeon-room mappings are open.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 20 | Giant Rat | `0x90..0x93` | 10 | 3 | 5 | 5 | - | Low-tier wilderness or trap encounter |
| 21 | Bat | `0x94..0x97` | 5 | 2 | 0 | 5 | - | Low-tier dungeon or night encounter |
| 22 | Giant Spider | `0x98..0x9B` | 10 | 3 | 5 | 5 | - | Wilderness, dungeon, poison-themed encounter |
| 23 | Ghost | `0x9C..0x9F` | 20 | 6 | 0 | 10 | physical half | Undead or spectral encounter |
| 24 | Slime | `0xA0..0xA3` | 10 | 3 | 0 | 2 | splits | Replicating dungeon creature |
| 25 | Gremlin | `0xA4..0xA7` | 10 | 3 | 12 | 10 | - | Dungeon, trap, or nuisance encounter |
| 31 | Insect Swarm | `0xBC..0xBF` | 5 | 2 | 0 | 1 | - | Swarm encounter; also associated with the Insect Swarm spell |
| 34 | Python | `0xC8..0xCB` | 10 | 3 | 0 | 8 | - | Snake or trap encounter |
| 46 | Rot Worm | `0xF8..0xFB` | 5 | 2 | 0 | 6 | - | Dungeon or underworld vermin encounter |

Slime division is the only fully decoded replication behavior in this group.
Gremlin, rat, spider, python, and rot-worm special behaviors are not yet decoded
beyond their shared closest-target AI and default damage/death paths.

## 5. Wilderness And Dungeon Monsters

These are the main hostile monster classes for outdoor and dungeon combat. The
encounter system confirms the terrain setup's first-spawn plus
leader/follower-style replacement model, but not a full terrain distribution per
class. The contexts below are therefore broad.

| Class | Creature | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|----------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 26 | Mimic | `0xA8..0xAB` | 30 | 8 | 20 | 12 | team override | Chest-like or ambush-style monster |
| 27 | Reaper | `0xAC..0xAF` | 40 | 11 | 25 | 12 | team override | Forest or fixed dungeon encounter |
| 28 | Gazer | `0xB0..0xB3` | 20 | 6 | 0 | 25 | special death | Eye-burst death effect |
| 29 | Crawler | `0xB4..0xB7` | 35 | 9 | 0 | 12 | - | Dungeon or underworld encounter |
| 30 | Gargoyle | `0xB8..0xBB` | 40 | 11 | 0 | 5 | splits; team override; special death | Terrain-hazard transition before normal cleanup; exact visual needs verification |
| 32 | Orc | `0xC0..0xC3` | 10 | 3 | 11 | 10 | team override | Humanoid wilderness or dungeon group |
| 33 | Skeleton | `0xC4..0xC7` | 20 | 6 | 13 | 5 | physical half | Undead encounter |
| 35 | Ettin | `0xCC..0xCF` | 30 | 8 | 17 | 12 | team override | Large humanoid encounter |
| 36 | Headless | `0xD0..0xD3` | 20 | 6 | 12 | 8 | team override | Wilderness or underworld encounter |
| 37 | Wisp | `0xD4..0xD7` | 40 | 11 | 0 | 20 | - | Magical or spectral encounter |
| 38 | Daemon | `0xD8..0xDB` | 75 | 19 | 0 | 25 | physical half | High-tier magical/dungeon encounter |
| 39 | Dragon | `0xDC..0xDF` | 99 | 25 | 30 | 25 | - | High-tier wilderness or dungeon encounter |
| 40 | Sand Trap | `0xE0..0xE3` | 80 | 21 | 25 | 5 | - | Desert or fixed trap-like encounter |
| 41 | Troll | `0xE4..0xE7` | 15 | 4 | 15 | 9 | - | Mountain, bridge, or wilderness encounter |
| 44 | Mongbat | `0xF0..0xF3` | 20 | 6 | 5 | 15 | - | Flying or cave-style encounter |
| 45 | Corpser | `0xF4..0xF7` | 40 | 11 | 0 | 8 | - | Underworld or fixed dungeon encounter |

Classes 42 and 43 are not listed as monsters because the name table has blank
entries for both. Their sprite runs would fall between Troll and Mongbat, but no
monster identity is currently supported by the local notes. Class 42 currently
looks like a blank stat row; class 43 has nonzero bytes in fields that are not
decoded yet, so it remains an identity gap rather than a proven unused class.

## 6. Shadow And Special Classes

Shadow Lords and a few human special actors use the same combat class machinery.
They are separated from the ordinary monster rows because their encounter
contexts are scripted or NPC-driven rather than regular wandering monster
spawns.

| Class | Actor | Sprite run | HP | Reward unit | Drop cap | Charm threshold | Traits | Encounter context |
|------:|-------|------------|---:|------------:|---------:|---------------:|--------|-------------------|
| 12 | Guard | `0x70..0x73` | 99 | 25 | 5 | 10 | - | Town hostility or scripted guard fight |
| 13 | Wanderer | `0x74..0x77` | 99 | 25 | 0 | 30 | physical immune | Special NPC combat class |
| 14 | Blackthorn | `0x78..0x7B` | 99 | 25 | 0 | 30 | physical immune | Scripted boss or special encounter |
| 15 | Lord British | `0x7C..0x7F` | 99 | 25 | 0 | 30 | physical immune | Special protected NPC class |
| 47 | Shadow Lord | `0xFC..0xFF` | 99 | 25 | 0 | 30 | physical half | Scripted Shadowlord encounter |

The combat table also contains non-hostile town roles and party classes, but
those belong in an NPC roster rather than this bestiary. Guards are included
because the encounter and combat notes explicitly describe town-hostility fights
that convert an NPC into a single combat attacker.

## 7. Encounter Behavior Summary

The encounter system does not directly start most overworld fights. It normally
spawns a hostile active object near the party; combat begins when the player or
monster contacts the other. Terrain combat then chooses one of sixteen outdoor
arenas from the triggering active-object class and populates up to twenty-six
combat actors.

For a terrain fight:

- The selected arena supplies a base monster count. Counts of 1, 8, and 16 are
  exact; other counts are rolled into a 1-to-max range.
- A "fortunes of war" flag can cause the count roll to be repeated.
- Town-style hostility overrides the count to one attacker.
- Placement uses sixteen fixed arena slots. Terrain fights use deterministic
  slot order; ambushes can shuffle the slots.
- The first placed monster uses the triggering arena class. For later placements,
  actors whose placement index is below `(count / 4) + 1` may use a per-arena
  replacement class when the replacement predicate permits it; later actors reuse
  the triggering class. This is the confirmed basis for the leader/follower
  shorthand used elsewhere.

Dungeon room encounters and chest-trap encounters use the same combat framer but
select arenas from the dungeon encounter bank. The exact dungeon-room-to-monster
mapping is not yet labelled in the current notes.

## 8. Completion And Gaps

**Complete in this catalog:**

- All named monster classes currently supported by the DATA.OVL name table:
  Sea Horse through Shadow Lord, excluding identity-gap classes 42 and 43.
- Hostile/special NPC combat classes confirmed by the shared combat table:
  Guard, Wanderer, Blackthorn, Lord British.
- Initial HP, raw reward unit, raw drop-cap byte, Mass Charm threshold,
  active-object sprite run, and decoded combat traits for every listed class.
- Shared AI target-selection behavior and the confirmed first-spawn,
  replacement-class, and follower placement model.

**Still open:**

1. The remaining bytes in each class stat record and the remaining class flag
   bits need names. Armor class, attack damage, hit chance, spell power,
   movement cadence, status attack strength, terrain handling, and other
   high-bit traits are not safely decoded.
2. Monster special-action and spell-like effect selection is bounded to the
   staged intent plus class-script dispatch path. Live actors of the same class
   share mutable class-state for that path, while dead or inactive actors use
   the class's static script entry, but the intent selector's class-effect map,
   runner state fields, runner instruction set, and final class-to-effect map
   are not fully mapped. Per-class tactics beyond closest-target pursuit, Cause
   Fear-driven fleeing, flee inversion, and faction overrides are incomplete.
3. The exact terrain-to-monster and dungeon-room-to-monster distribution tables
   are not labelled. Encounter contexts in this catalog are broad, not exact
   spawn tables.
4. Ordinary drop contents and encounter reward consumers are not decoded. The
   default kill path can set a class drop-cap marker and a special-drop high
   bit, and the damage/death handler returns a raw reward unit. Tremor's
   spell-side consumer of that return value is known, but the ordinary final
   item, gold, XP, karma, or score interpretation is still open.
5. The public tile catalog still needs a verification pass that maps these
   active-object sprite bytes onto final sprite-sheet tile ids.
6. The class-specific special death paths need runtime verification for visual
   details and follow-up cleanup effects, especially the Gazer and Gargoyle
   paths.
7. The damage handler's vanish-on-death branch is traced, but no listed class in
   the analyzed baseline has the corresponding high flag bit set. Do not assign
   that trait to the special NPC or Shadow Lord rows without variant-table
   evidence.

## 9. Sources

This catalog is cleanroom prose derived from the local analysis notes and the
existing public specs. It does not reproduce disassembly, decompiled code, data
offsets, raw private addresses, binary dumps, or private note prose.

**Private analysis sources used:**

- `u5-decomp/formats/data-ovl.md` - resident data segment overview, monster name
  and combat table regions, and DATA.OVL completion notes.
- COMBAT overlay damage/status-resolution note - damage, raw reward unit,
  drop-roll markers, class flags, split, vanish, and special-death behavior.
- COMBAT overlay target-picker note - target filtering, faction handling,
  nearest-target scoring, and flee-direction inversion.
- COMBAT overlay actor AI/command-dispatch note - synthesized monster command
  dispatch and shared combat command parser.
- COMSUBS overlay AI direction note - class-script dispatch, live-state versus
  inactive-script split, and direction-vector output.
- ULTIMA executable combat-framer note - combat entry branches and
  town-hostility count override.
- ULTIMA executable terrain-combat setup note - encounter count roll, placement
  slots, replacement-class selection, and active-object placement.

**Public specs cross-checked:**

- `u5-spec/systems/combat.md`
- `u5-spec/systems/encounters.md`
- `u5-spec/systems/overworld.md`
- `u5-spec/catalogs/tile-catalog.md`
- `u5-spec/catalogs/spell-list.md`

## 10. Cross-References

- `systems/combat.md` - combat round loop, actor table, damage/status
  application, and victory/escape framing.
- `systems/encounters.md` - random encounters, ambushes, dungeon room fights,
  and post-combat world reconciliation.
- `catalogs/tile-catalog.md` - broad tile and active-object class partitions.
- `catalogs/spell-list.md` - summon and field spells that can introduce or
  interact with creature classes.
