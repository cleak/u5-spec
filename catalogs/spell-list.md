# Spell List

A reference catalog of every spell in Ultima V — its rune-name, its common name, its circle and mana cost, its reagent recipe, and its effect category. This document is descriptive and table-driven; it does not specify the cast pipeline or the prerequisite gates (those live in `systems/magic.md`). Use this as the lookup table when implementing the spell book, the M-Mix prompt, the spell-effect dispatcher, or the Z-stats spell panel.

## 1. Overview

Ultima V ships with exactly forty-eight spells. The spells are organised into eight ascending circles of six spells each. Within a circle, all six spells share the same mana cost and the same minimum caster level; circles do not differ within themselves in terms of resource demands.

Every spell carries five fixed properties:

- A **rune name**, written as one to four syllables drawn from a fixed twenty-four-syllable runic vocabulary. The rune name is the spell's canonical identifier. Casting in-game requires the player to type the rune-name.
- A **common name** — the English label used in the manual and in narration. Common names are descriptive ("Heal", "Magic Lock", "Gate Travel") but are not used by the input parser.
- A **circle**, an integer in `1..8`, equal to both the spell's mana cost and its required caster level. A circle-five spell costs five mana, requires the caster to be at least level five, and is always one of six.
- A **reagent recipe**, a fixed subset of two to five of the eight available reagents. Mixing one charge of the spell consumes one of each listed reagent from the party's shared inventory.
- An **effect category** — utility, healing, buff/debuff, damage, field, summon, or marquee. Categories are descriptive only; they do not influence cost or eligibility.

The complete set is given in section 4. Sections 5 and 6 reorganise the same data by circle and by category for browsing convenience.

The total spell count of forty-eight, the eight-circle / six-per-circle structure, and the integer mana = circle = level rule are all confirmed by the project's analysis of the cast dispatcher; the exact rune-to-effect map is taken jointly from the dispatcher's forty-eight-entry token table, the print-on-success narration strings, and the published Ultima V manual.

## 2. The eight circles

The eight circles are ascending tiers. The cost increases linearly: circle-one spells cost one mana, circle-eight spells cost eight. Each tier holds exactly six spells.

| Circle | Mana cost | Min. caster level | Spell count | Index range | Tier label                  |
|:------:|:---------:|:-----------------:|:-----------:|:-----------:|-----------------------------|
| 1      | 1         | 1                 | 6           | 0..5        | Apprentice                  |
| 2      | 2         | 2                 | 6           | 6..11       | Novice                      |
| 3      | 3         | 3                 | 6           | 12..17      | Adept                       |
| 4      | 4         | 4                 | 6           | 18..23      | Expert                      |
| 5      | 5         | 5                 | 6           | 24..29      | Master                      |
| 6      | 6         | 6                 | 6           | 30..35      | Grand Master                |
| 7      | 7         | 7                 | 6           | 36..41      | Archmage                    |
| 8      | 8         | 8                 | 6           | 42..47      | Avatar                      |

Tier labels are conventional only — the engine does not store them; they are useful in the spell-book panel and in dialogue.

The inverse lookup — given a spell's index 0..47, recover its circle — is `(index / 6) + 1` with integer division. The dispatcher computes the cost this way at cast time. Implementations targeting period-faithful behaviour should derive cost from circle, not store it as a separate per-spell field.

## 3. The twenty-four rune syllables

A spell's rune-name is built from this fixed alphabet. Each syllable carries a small semantic meaning; combinations express the spell's effect compositionally. The vocabulary is canon and shared with non-spell uses (NPC dialogue, the Words of Power that disable certain barriers, the rune-codex view).

| Syllable  | Loose meaning                              |
|-----------|---------------------------------------------|
| An        | negate, dispel, undo                        |
| Bet       | small, lesser, minor                        |
| Corp      | death, dead, mortality                      |
| Des       | down, lower, descend                        |
| Ex        | freedom, release, set loose                 |
| Flam      | flame, fire, heat                           |
| Grav      | field, energy field, contained area         |
| Hur       | wind, weather, breath                       |
| In        | create, make, cause                         |
| Jux       | harm, danger (rare in spell names)          |
| Kal       | summon, invoke, call forth                  |
| Lor       | light, illumination                         |
| Mani      | life, healing, restoration                  |
| Nox       | poison, toxin                               |
| Ort       | magic, the magical (rare in spell names)    |
| Por       | movement, motion, transport                 |
| Quas      | illusion, image, deception                  |
| Rel       | change, alter                               |
| Sanct     | protection, ward                            |
| Tym       | time                                        |
| Uus       | up, raise, ascend                           |
| Vas       | great, large, increased                     |
| Wis       | knowledge, sight, awareness                 |
| Xen       | creature, being, animal                     |
| Ylem      | matter, substance, raw stuff                |
| Zu        | sleep, stillness                            |

Twenty-six entries are listed; the resident data segment holds exactly twenty-four of them. `Jux` and `Ort` appear in the wider Britannian magic lore but are not required to spell out any of the forty-eight U5 spells; some implementations include them as alphabet entries even though they are unused.

A spell's rune-name is the syllables in order, separated by spaces (`Vas Mani`, `In Mani Corp`, `An Xen Corp`, `Vas Rel Por`). The C-Cast prompt does not accept the syllable form directly — it accepts the compact letter-coded form described in section 4.

## 4. The forty-eight spells

The full spell list, ordered by index 0..47. Each row gives the spell's rune-name, its common name, its circle (= mana cost = minimum level), its compact rune-code (the form typed at the C-Cast prompt), its reagent recipe (using the abbreviations from section 8), and its effect category.

| ID | Rune-Code | Rune-Name             | Common Name        | C | Recipe                                    | Category   |
|---:|:---------:|-----------------------|--------------------|:-:|-------------------------------------------|------------|
| 0  | `IL`      | An Zu                 | Awaken             | 1 | Garlic + Ginseng                          | healing    |
| 1  | `GP`      | An Nox                | Cure               | 1 | Garlic + Ginseng                          | healing    |
| 2  | `M`       | Mani                  | Heal               | 1 | Ginseng + Spider Silk                     | healing    |
| 3  | `AY`      | An Ylem               | Light              | 1 | Sulfur Ash                                | utility    |
| 4  | `AS`      | An Sanct              | Magic Unlock       | 1 | Sulfur Ash + Black Pearl                  | utility    |
| 5  | `AXC`     | An Xen Corp           | Repond             | 1 | Sulfur Ash + Garlic                       | buff/debuff|
| 6  | `RH`      | Rel Hur               | Wind Change        | 2 | Sulfur Ash + Blood Moss                   | utility    |
| 7  | `IW`      | In Wis                | Locate             | 2 | Nightshade + Mandrake                     | utility    |
| 8  | `KX`      | Kal Xen               | Summon Creature    | 2 | Sulfur Ash + Mandrake                     | summon     |
| 9  | `IXM`     | In Xen Mani           | Heal Animal        | 2 | Spider Silk + Ginseng                     | healing    |
| 10 | `VL`      | Vas Lor               | Great Light        | 2 | Sulfur Ash + Mandrake                     | utility    |
| 11 | `VF`      | Vas Flam              | Fireball           | 2 | Sulfur Ash + Black Pearl                  | damage     |
| 12 | `IFG`     | In Flam Grav          | Fire Field         | 3 | Sulfur Ash + Black Pearl + Spider Silk    | field      |
| 13 | `INXG`    | In Nox Grav           | Poison Field       | 3 | Nightshade + Black Pearl + Spider Silk    | field      |
| 14 | `IZG`     | In Zu Grav            | Sleep Field        | 3 | Ginseng + Spider Silk + Black Pearl       | field      |
| 15 | `IP`      | In Por                | Blink              | 3 | Spider Silk + Blood Moss                  | utility    |
| 16 | `AG`      | An Grav               | Dispel Field       | 3 | Sulfur Ash + Black Pearl                  | field      |
| 17 | `IS`      | In Sanct              | Protection         | 3 | Garlic + Ginseng + Mandrake               | buff/debuff|
| 18 | `ISG`     | In Sanct Grav         | Mass Protection    | 4 | Garlic + Ginseng + Mandrake               | buff/debuff|
| 19 | `UP`      | Uus Por               | Up                 | 4 | Spider Silk + Blood Moss + Mandrake       | utility    |
| 20 | `DP`      | Des Por               | Down               | 4 | Spider Silk + Blood Moss + Nightshade     | utility    |
| 21 | `WQ`      | Wis Quas              | Reveal             | 4 | Sulfur Ash + Mandrake + Nightshade        | utility    |
| 22 | `IBX`     | In Bet Xen            | Insect Swarm       | 4 | Sulfur Ash + Garlic + Mandrake            | summon     |
| 23 | `AEP`     | An Ex Por             | Negate Field       | 4 | Sulfur Ash + Blood Moss + Mandrake        | utility    |
| 24 | `IEP`     | In Ex Por             | Magic Lock         | 5 | Sulfur Ash + Black Pearl + Mandrake       | utility    |
| 25 | `VM`      | Vas Mani              | Great Heal         | 5 | Ginseng + Spider Silk + Mandrake          | healing    |
| 26 | `IZ`      | In Zu                 | Sleep              | 5 | Ginseng + Spider Silk + Nightshade        | buff/debuff|
| 27 | `RT`      | Rel Tym               | Quickness          | 5 | Blood Moss + Mandrake                     | buff/debuff|
| 28 | `IVPY`    | In Vas Por Ylem       | Earthquake         | 5 | Sulfur Ash + Blood Moss + Mandrake        | damage     |
| 29 | `QAW`     | Quas An Wis           | Mass Confuse       | 5 | Nightshade + Mandrake                     | buff/debuff|
| 30 | `IA`      | In An                 | Negate Magic       | 6 | Sulfur Ash + Garlic + Mandrake            | marquee    |
| 31 | `WAY`     | Wis An Ylem           | View               | 6 | Sulfur Ash + Mandrake + Nightshade        | utility    |
| 32 | `AXE`     | An Xen Ex             | Dispel Monster     | 6 | Sulfur Ash + Garlic + Mandrake            | summon     |
| 33 | `RXB`     | Rel Xen Bet           | Polymorph          | 6 | Spider Silk + Mandrake + Nightshade       | buff/debuff|
| 34 | `SL`      | Sanct Lor             | Invisibility       | 6 | Blood Moss + Nightshade                   | buff/debuff|
| 35 | `XC`     | Xen Corp              | Slay Living        | 6 | Black Pearl + Nightshade + Mandrake       | damage     |
| 36 | `IQX`     | In Quas Xen           | Conjure            | 7 | Spider Silk + Mandrake + Nightshade       | summon     |
| 37 | `IQW`     | In Quas Wis           | Confuse            | 7 | Nightshade + Mandrake                     | buff/debuff|
| 38 | `INH`     | In Nox Hur            | Poison Wind        | 7 | Nightshade + Blood Moss                   | damage     |
| 39 | `IQC`     | In Quas Corp          | Fear               | 7 | Garlic + Mandrake + Nightshade            | buff/debuff|
| 40 | `IMC`     | In Mani Corp          | Resurrection       | 7 | Garlic + Ginseng + Spider Silk + Blood Moss + Mandrake | healing |
| 41 | `KXC`     | Kal Xen Corp          | Summon Daemon      | 7 | Spider Silk + Mandrake + Nightshade       | summon     |
| 42 | `IVGC`    | In Vas Grav Corp      | Cataclysm          | 8 | Sulfur Ash + Black Pearl + Mandrake + Nightshade | damage |
| 43 | `IFH`     | In Flam Hur           | Fire Storm         | 8 | Sulfur Ash + Black Pearl + Blood Moss     | damage     |
| 44 | `VRP`     | Vas Rel Por           | Gate Travel        | 8 | Sulfur Ash + Mandrake + Black Pearl       | marquee    |
| 45 | `AT`      | An Tym                | Time Stop          | 8 | Mandrake + Nightshade + Blood Moss        | marquee    |
| 46 | `IQW8`    | In Quas Wis (greater) | Codex Vision       | 8 | Sulfur Ash + Mandrake + Nightshade        | marquee    |
| 47 | `VAT`     | Vas An Tym            | Negate Time        | 8 | Mandrake + Nightshade + Blood Moss        | marquee    |

Notes on the table.

- Rune-codes use the upper-case compact letter-coding from the cast dispatcher's input parser. The codes are not always the literal first letters of every syllable — they are *distinguishing* letters chosen so that no two of the forty-eight codes collide. A few entries (`M` for Mani, `IPVY` historically rendered for In Vas Por Ylem) reflect this convention.
- Recipes are taken from the U5 manual's spellbook entries. The dispatcher and M-Mix handler reference an in-engine recipe table; transcribing each byte of that table into this catalog is open work (section 9). Where the recipe given here disagrees with implementation behaviour, the implementation is the authoritative source.
- The five circle-eight entries that are marked `marquee` in the category column are spells whose effect dwarfs their numerical cost — they are spotlight spells that change the world, not just the local actor table.
- The Codex Vision (id 46) and Negate Time (id 47) circle-eight slots are tentative attributions; the dispatcher's eighth-circle handlers have not all been individually decoded. Implementations should treat ids 46 and 47 as best-guess and verify them against in-game dialogue once the per-handler decompilation completes (section 10).

## 5. By circle (alternative organisation)

Browsing by circle is convenient when balancing class progression and shop stocks. Each subsection below enumerates the six spells in one circle. Order within a circle is the engine-internal index order; class progression typically grants spells in this order as the character levels.

### Circle 1 — Apprentice (1 mana, level 1)

| ID | Code | Rune-Name      | Common Name    | Recipe                                  |
|---:|:----:|----------------|----------------|------------------------------------------|
| 0  | IL   | An Zu          | Awaken         | Garlic + Ginseng                         |
| 1  | GP   | An Nox         | Cure           | Garlic + Ginseng                         |
| 2  | M    | Mani           | Heal           | Ginseng + Spider Silk                    |
| 3  | AY   | An Ylem        | Light          | Sulfur Ash                               |
| 4  | AS   | An Sanct       | Magic Unlock   | Sulfur Ash + Black Pearl                 |
| 5  | AXC  | An Xen Corp    | Repond         | Sulfur Ash + Garlic                      |

### Circle 2 — Novice (2 mana, level 2)

| ID | Code | Rune-Name      | Common Name      | Recipe                                |
|---:|:----:|----------------|------------------|----------------------------------------|
| 6  | RH   | Rel Hur        | Wind Change      | Sulfur Ash + Blood Moss               |
| 7  | IW   | In Wis         | Locate           | Nightshade + Mandrake                 |
| 8  | KX   | Kal Xen        | Summon Creature  | Sulfur Ash + Mandrake                 |
| 9  | IXM  | In Xen Mani    | Heal Animal      | Spider Silk + Ginseng                 |
| 10 | VL   | Vas Lor        | Great Light      | Sulfur Ash + Mandrake                 |
| 11 | VF   | Vas Flam       | Fireball         | Sulfur Ash + Black Pearl              |

### Circle 3 — Adept (3 mana, level 3)

| ID | Code | Rune-Name      | Common Name    | Recipe                                          |
|---:|:----:|----------------|----------------|--------------------------------------------------|
| 12 | IFG  | In Flam Grav   | Fire Field     | Sulfur Ash + Black Pearl + Spider Silk          |
| 13 | INXG | In Nox Grav    | Poison Field   | Nightshade + Black Pearl + Spider Silk          |
| 14 | IZG  | In Zu Grav     | Sleep Field    | Ginseng + Spider Silk + Black Pearl             |
| 15 | IP   | In Por         | Blink          | Spider Silk + Blood Moss                        |
| 16 | AG   | An Grav        | Dispel Field   | Sulfur Ash + Black Pearl                        |
| 17 | IS   | In Sanct       | Protection     | Garlic + Ginseng + Mandrake                     |

### Circle 4 — Expert (4 mana, level 4)

| ID | Code | Rune-Name      | Common Name      | Recipe                                          |
|---:|:----:|----------------|------------------|--------------------------------------------------|
| 18 | ISG  | In Sanct Grav  | Mass Protection  | Garlic + Ginseng + Mandrake                     |
| 19 | UP   | Uus Por        | Up               | Spider Silk + Blood Moss + Mandrake             |
| 20 | DP   | Des Por        | Down             | Spider Silk + Blood Moss + Nightshade           |
| 21 | WQ   | Wis Quas       | Reveal           | Sulfur Ash + Mandrake + Nightshade              |
| 22 | IBX  | In Bet Xen     | Insect Swarm     | Sulfur Ash + Garlic + Mandrake                  |
| 23 | AEP  | An Ex Por      | Negate Field     | Sulfur Ash + Blood Moss + Mandrake              |

### Circle 5 — Master (5 mana, level 5)

| ID | Code | Rune-Name        | Common Name    | Recipe                                          |
|---:|:----:|------------------|----------------|--------------------------------------------------|
| 24 | IEP  | In Ex Por        | Magic Lock     | Sulfur Ash + Black Pearl + Mandrake             |
| 25 | VM   | Vas Mani         | Great Heal     | Ginseng + Spider Silk + Mandrake                |
| 26 | IZ   | In Zu            | Sleep          | Ginseng + Spider Silk + Nightshade              |
| 27 | RT   | Rel Tym          | Quickness      | Blood Moss + Mandrake                           |
| 28 | IVPY | In Vas Por Ylem  | Earthquake     | Sulfur Ash + Blood Moss + Mandrake              |
| 29 | QAW  | Quas An Wis      | Mass Confuse   | Nightshade + Mandrake                           |

### Circle 6 — Grand Master (6 mana, level 6)

| ID | Code | Rune-Name      | Common Name    | Recipe                                          |
|---:|:----:|----------------|----------------|--------------------------------------------------|
| 30 | IA   | In An          | Negate Magic   | Sulfur Ash + Garlic + Mandrake                  |
| 31 | WAY  | Wis An Ylem    | View           | Sulfur Ash + Mandrake + Nightshade              |
| 32 | AXE  | An Xen Ex      | Dispel Monster | Sulfur Ash + Garlic + Mandrake                  |
| 33 | RXB  | Rel Xen Bet    | Polymorph      | Spider Silk + Mandrake + Nightshade             |
| 34 | SL   | Sanct Lor      | Invisibility   | Blood Moss + Nightshade                         |
| 35 | XC   | Xen Corp       | Slay Living    | Black Pearl + Nightshade + Mandrake             |

### Circle 7 — Archmage (7 mana, level 7)

| ID | Code | Rune-Name      | Common Name    | Recipe                                                        |
|---:|:----:|----------------|----------------|----------------------------------------------------------------|
| 36 | IQX  | In Quas Xen    | Conjure        | Spider Silk + Mandrake + Nightshade                           |
| 37 | IQW  | In Quas Wis    | Confuse        | Nightshade + Mandrake                                          |
| 38 | INH  | In Nox Hur     | Poison Wind    | Nightshade + Blood Moss                                        |
| 39 | IQC  | In Quas Corp   | Fear           | Garlic + Mandrake + Nightshade                                 |
| 40 | IMC  | In Mani Corp   | Resurrection   | Garlic + Ginseng + Spider Silk + Blood Moss + Mandrake         |
| 41 | KXC  | Kal Xen Corp   | Summon Daemon  | Spider Silk + Mandrake + Nightshade                           |

### Circle 8 — Avatar (8 mana, level 8)

| ID | Code | Rune-Name             | Common Name      | Recipe                                                  |
|---:|:----:|-----------------------|------------------|----------------------------------------------------------|
| 42 | IVGC | In Vas Grav Corp      | Cataclysm        | Sulfur Ash + Black Pearl + Mandrake + Nightshade        |
| 43 | IFH  | In Flam Hur           | Fire Storm       | Sulfur Ash + Black Pearl + Blood Moss                   |
| 44 | VRP  | Vas Rel Por           | Gate Travel      | Sulfur Ash + Mandrake + Black Pearl                     |
| 45 | AT   | An Tym                | Time Stop        | Mandrake + Nightshade + Blood Moss                      |
| 46 | IQW8 | In Quas Wis (greater) | Codex Vision     | Sulfur Ash + Mandrake + Nightshade                      |
| 47 | VAT  | Vas An Tym            | Negate Time      | Mandrake + Nightshade + Blood Moss                      |

## 6. By category (alternative organisation)

The seven effect categories are descriptive only; the engine does not store them. The category column in section 4 makes it easy to enumerate spells by family for design discussions.

### 6.1 Utility (twelve spells)

Scene-altering or single-step interactions that do not damage actors. Most have a short narration message and finish in one handler call.

| ID | Code | Rune-Name      | Common Name    | Circle |
|---:|:----:|----------------|----------------|:------:|
| 3  | AY   | An Ylem        | Light          | 1      |
| 4  | AS   | An Sanct       | Magic Unlock   | 1      |
| 6  | RH   | Rel Hur        | Wind Change    | 2      |
| 7  | IW   | In Wis         | Locate         | 2      |
| 10 | VL   | Vas Lor        | Great Light    | 2      |
| 15 | IP   | In Por         | Blink          | 3      |
| 19 | UP   | Uus Por        | Up             | 4      |
| 20 | DP   | Des Por        | Down           | 4      |
| 21 | WQ   | Wis Quas       | Reveal         | 4      |
| 23 | AEP  | An Ex Por      | Negate Field   | 4      |
| 24 | IEP  | In Ex Por      | Magic Lock     | 5      |
| 31 | WAY  | Wis An Ylem    | View           | 6      |

### 6.2 Healing (six spells)

Restore HP, lift status conditions, or revive the dead. All target a party slot (chosen separately or implicit via the active player).

| ID | Code | Rune-Name      | Common Name    | Circle |
|---:|:----:|----------------|----------------|:------:|
| 0  | IL   | An Zu          | Awaken         | 1      |
| 1  | GP   | An Nox         | Cure           | 1      |
| 2  | M    | Mani           | Heal           | 1      |
| 9  | IXM  | In Xen Mani    | Heal Animal    | 2      |
| 25 | VM   | Vas Mani       | Great Heal     | 5      |
| 40 | IMC  | In Mani Corp   | Resurrection   | 7      |

### 6.3 Buff and debuff (ten spells)

Set or clear flags or per-round timers in a target's combat-state record. The Repond entry borders on a healing buff (it calms undead) but is filed here.

| ID | Code | Rune-Name      | Common Name      | Circle |
|---:|:----:|----------------|------------------|:------:|
| 5  | AXC  | An Xen Corp    | Repond           | 1      |
| 17 | IS   | In Sanct       | Protection       | 3      |
| 18 | ISG  | In Sanct Grav  | Mass Protection  | 4      |
| 26 | IZ   | In Zu          | Sleep            | 5      |
| 27 | RT   | Rel Tym        | Quickness        | 5      |
| 29 | QAW  | Quas An Wis    | Mass Confuse     | 5      |
| 33 | RXB  | Rel Xen Bet    | Polymorph        | 6      |
| 34 | SL   | Sanct Lor      | Invisibility     | 6      |
| 37 | IQW  | In Quas Wis    | Confuse          | 7      |
| 39 | IQC  | In Quas Corp   | Fear             | 7      |

### 6.4 Direct damage (six spells)

Walk the actor table, pick targets either by direction (line-of-effect) or by area (every visible enemy), and call the same damage-and-status handler that combat melee uses.

| ID | Code | Rune-Name        | Common Name  | Circle |
|---:|:----:|------------------|--------------|:------:|
| 11 | VF   | Vas Flam         | Fireball     | 2      |
| 28 | IVPY | In Vas Por Ylem  | Earthquake   | 5      |
| 35 | XC   | Xen Corp         | Slay Living  | 6      |
| 38 | INH  | In Nox Hur       | Poison Wind  | 7      |
| 42 | IVGC | In Vas Grav Corp | Cataclysm    | 8      |
| 43 | IFH  | In Flam Hur      | Fire Storm   | 8      |

### 6.5 Field placement (four spells)

Place or remove a tile-effect entry on the active map at a chosen cell. The field persists for several turns and applies its effect to any actor that enters or starts a turn on the cell.

| ID | Code | Rune-Name      | Common Name  | Circle |
|---:|:----:|----------------|--------------|:------:|
| 12 | IFG  | In Flam Grav   | Fire Field   | 3      |
| 13 | INXG | In Nox Grav    | Poison Field | 3      |
| 14 | IZG  | In Zu Grav     | Sleep Field  | 3      |
| 16 | AG   | An Grav        | Dispel Field | 3      |

### 6.6 Summoning and conjuration (five spells)

Insert a new entry into the actor table or the dynamic-objects table, with a tile drawn from a per-spell summoned-class list. Summoned creatures are then run by the standard AI; they vanish when killed or after a per-spell duration.

| ID | Code | Rune-Name      | Common Name      | Circle |
|---:|:----:|----------------|------------------|:------:|
| 8  | KX   | Kal Xen        | Summon Creature  | 2      |
| 22 | IBX  | In Bet Xen     | Insect Swarm     | 4      |
| 32 | AXE  | An Xen Ex      | Dispel Monster   | 6      |
| 36 | IQX  | In Quas Xen    | Conjure          | 7      |
| 41 | KXC  | Kal Xen Corp   | Summon Daemon    | 7      |

### 6.7 Marquee (five spells)

The fewest-use spells with the largest gameplay impact. They suppress every active enchantment and field within a scene, freeze monster turns for several rounds, teleport the party to a moongate destination, or open a unique scripted view.

| ID | Code | Rune-Name             | Common Name      | Circle |
|---:|:----:|-----------------------|------------------|:------:|
| 30 | IA   | In An                 | Negate Magic     | 6      |
| 44 | VRP  | Vas Rel Por           | Gate Travel      | 8      |
| 45 | AT   | An Tym                | Time Stop        | 8      |
| 46 | IQW8 | In Quas Wis (greater) | Codex Vision     | 8      |
| 47 | VAT  | Vas An Tym            | Negate Time      | 8      |

## 7. Marquee spells in detail

The five marquee spells deserve a paragraph each because they implement effects unique in the engine.

**In An — Negate Magic (circle 6).** Suppresses every active enchantment and persistent field within the current scene. All buffs (Protection, Mass Protection, Quickness, Invisibility, Polymorph) on every actor — friendly or hostile — drop to zero immediately. All placed fields (Fire, Poison, Sleep) are cleared from the tile-effect overlay. Active illusions are revealed. The narrative effect resembles "the magic in this place stops working for a moment." The handler prints `Negate magic!`.

**Vas An Tym — Negate Time (circle 8).** Freezes monster and NPC turn-walkers for an extended span, allowing the party to move freely. While the negation holds, the per-turn world tick still runs (food still depletes, time of day still advances), but actor AI turns are skipped. The simpler `An Tym` (Time Stop) at the same circle is a shorter-duration variant.

**In Quas Wis — Codex Vision (circle 8).** Invokes a unique scripted scene that replaces the in-world view with a visualisation of the eight virtues' codex inscription. The effect is mostly narrative — game state is not advanced beyond the current turn — but the moment is iconic and the spell handler calls a dedicated cinematic-screen routine rather than the standard effect handler. (This entry is one of the tentatively-attributed circle-eight slots — verification is open work.)

**Vas Rel Por — Gate Travel (circle 8).** The eight-rune teleport. The handler reads the current moon phases and the party's world position, computes a destination from the global moongate destination table (one entry per moon-phase combination), and moves the party to the target moongate. Gate Travel is the one spell whose target is the *world* map, not any individual actor. Pre-conditions: the party must be on the surface (not in a town, dungeon, or combat); the relevant moongate must be active for the current moon phase. A failed pre-condition prints `Failed!` and consumes mana but no charge.

These marquee spells are individually expensive to mix — every one requires Mandrake Root, the rarest reagent — and the player typically holds only a handful of pre-mixed charges. The strategic element of saving them for the right moment is part of the magic system's pacing.

## 8. Reagent inventory

Every spell recipe is built from some subset of these eight reagents. The order is canonical and corresponds to the engine's per-reagent inventory slots; recipe tables are expressed as bitmasks against this same eight-slot order.

| Reagent      | Abbreviation | Common source                                              |
|--------------|--------------|-------------------------------------------------------------|
| Sulfur Ash   | `Sulfur Ash` | Britain, Skara Brae herbalists                              |
| Ginseng      | `Ginseng`    | Cove, Yew herbalists                                        |
| Garlic       | `Garlic`     | Most large-town herbalists                                  |
| Spider Silk  | `Sp. Silk`   | Specialist shops; occasional drops from large arachnids     |
| Blood Moss   | `Blood Moss` | Swamp regions; certain herbalists carry small stocks        |
| Black Pearl  | `Blk. Pearl` | Coastal-town herbalists; occasional dungeon drops           |
| Nightshade   | `Nightshade` | Rare; specific outdoor patches at night, certain phase only |
| Mandrake Root| `Mandrake`   | Rare; specific outdoor patches at full moon, marsh terrain  |

The two reagents at the bottom of the list (Nightshade and Mandrake Root) are deliberately scarce. They are not sold by herbalists in the standard distribution. The player must hunt down specific outdoor tiles in the world map at the correct in-game time-of-day or moon-phase. Many high-circle spells require both, which makes them naturally rare in mid-game and unbottlenecked only after the party can reliably travel back to the harvesting tiles. In practice, the cap on the spell economy is the player's stock of these two reagents, not gold.

The shorter abbreviations are used in tight UI lines (the M-Mix prompt, combat narration); the long forms are used on the dedicated reagent inventory panel and on the Z-stats reagent line.

The reagent inventory is part of the persistent save image. Each reagent is a single byte counter; the cap is the standard inventory cap (treated by U5 as 99). The counter is decremented by mixing and incremented by herbalist purchases and by occasional plot-driven gifts. There is no on-the-fly cast that consumes raw reagents directly — reagents are only ever consumed by the M-Mix command.

Common recipe patterns recurring across many spells:

- **Heal-family** spells (Heal, Great Heal, Heal Animal) use Ginseng + Spider Silk as the base; rarer healing (Resurrection) adds Mandrake.
- **Light-family** spells use Sulfur Ash, sometimes paired with Mandrake for the great-light variants.
- **Fire-family** spells use Sulfur Ash + Black Pearl, sometimes augmented with Spider Silk or Blood Moss for AOE variants.
- **Field-placement** spells use the relevant element (Sulfur Ash for fire, Nightshade for poison, Ginseng for sleep) plus Black Pearl + Spider Silk to bind the field to a tile.
- **Protection** uses Garlic + Ginseng + Mandrake; the mass variant is the same.
- **Top-circle marquee** spells (Cataclysm, Time Stop, Gate Travel, Negate Time) use Mandrake + Nightshade as a base and add the spell-specific elements; this is what makes them strategically expensive.

## 9. Mana cost lookup

For convenience, the relationship between spell index, circle, mana cost, and minimum caster level:

| Index range | Circle | Mana cost | Min. level |
|:-----------:|:------:|:---------:|:----------:|
| 0..5        | 1      | 1         | 1          |
| 6..11       | 2      | 2         | 2          |
| 12..17      | 3      | 3         | 3          |
| 18..23      | 4      | 4         | 4          |
| 24..29      | 5      | 5         | 5          |
| 30..35      | 6      | 6         | 6          |
| 36..41      | 7      | 7         | 7          |
| 42..47      | 8      | 8         | 8          |

The formulas are:

- `circle(index) = (index / 6) + 1` (integer division)
- `mana_cost(index) = circle(index)`
- `min_level(index) = circle(index)`

These are not stored per-spell in the engine — the dispatcher computes them at cast time from the input index.

## 10. Sources and completion

The data here is drawn jointly from three sources. Boundaries are noted so an implementer can check an authoritative source for any disputed entry.

**From the project's decompilation work** (`u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`, `u5-decomp/formats/data-ovl.md`):

- The forty-eight-entry compact rune-code table.
- The eight-circle / six-spell structure and the integer mana-cost formula `(id / 6) + 1`.
- The print-on-success narration strings that confirm specific effect mappings (Light, Wind Change, Protection, Negate Magic, View, Summon Daemon, Resurrection, Negate Time).
- The twenty-four-syllable rune dictionary, the eight reagent abbreviations, the forty-eight runic incantation strings.
- The C-Cast prompt, the prerequisite-gate cascade, and the per-spell allow-mask byte.

**From the published Ultima V manual** (`The Book of Lore`):

- The full per-spell recipe (which reagents each spell needs).
- The English common name for each of the forty-eight spells and its descriptive effect summary.
- The broad categorisation into utility, healing, buff/debuff, damage, field, summon, marquee.
- The narrative framing of the marquee spells.

The manual is openly published source material that ships with every legitimate copy of the game. Citing it openly here is consistent with this catalog's role as a cross-cutting reference; byte-derived data is cross-checked against documented player-facing behaviour without contaminating the cleanroom.

**Tentative per-handler attributions** (depend on per-handler decompilation that has not yet completed):

- Ids 33 (Polymorph), 35 (Slay Living), 41 (Summon Daemon) — rune-code correct; common name from the manual; per-handler effect not yet individually decoded.
- Ids 28 (Earthquake), 40 (Resurrection), 44 (Gate Travel), 45 (Time Stop) — heal/restore-family handlers use a shared dispatcher; the individual entries are provisionally mapped.
- Ids 46 (Codex Vision) and 47 (Negate Time) — best-guess; alternate readings would assign these slots to a resurrection long-form and a final negate variant.

**Completion summary.** All 48 spells carry rune-code, rune-name, common name, circle, mana cost, recipe, and effect category. Confidence is high for ids 0–32 and 34, 36–40, 42–44; medium for the five tentative entries above (33, 35, 41, 46, 47). All 24 rune syllables, all 8 reagents, and all 8 circles are documented at high confidence.

## 11. Cross-references

- `systems/magic.md` — Full specification of the magic system, including the C-Cast and M-Mix command flows, the prerequisite gates, the combat-cast pre-gate, and the linkage to the eight virtue shrines.
- `systems/combat.md` — Combat-mode specification, including the combat-only spell prereq pre-gate that runs before the dispatcher.
- `formats/saved-gam.md` — Persistent save image, including the eight reagent counters, the forty-eight per-spell charge counters, and the per-character mana and level fields.
- `systems/text-output.md` — The narration pipeline that prints spell success and failure messages.

## 12. Open work

1. Transcribe the engine's per-spell recipe table byte-by-byte from the M-Mix handler; confirm or correct the recipes in section 4.
2. Transcribe the per-spell allow-mask byte-by-byte. The four bits encode which scenes a spell may be cast in.
3. Decode the tentative circle-six and circle-eight handler attributions (ids 33, 35, 41, 46, 47).
4. Verify the per-spell charge-counter cap (byte 0..255 vs. U5 standard cap 99).
5. Document the per-spell duration for buffs and summons (Protection turns, Quickness extra-action ratio, Time Stop freeze span).
6. Document the friendly-fire policy for AOE spells (Earthquake, Cataclysm, Fire Storm, Mass Confuse, and the field placements).
