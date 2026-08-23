# Item List

A reference catalog of the party inventory, equipment, reagents, quest items, and vehicles in Ultima V. This document is descriptive and table-driven; it does not specify the command dispatchers, shop menu loops, combat formulas, or save-file byte layout. Use this as the lookup table when implementing inventory display, shop stock, equipment selection, treasure results, reagent stock, and vehicle ownership.

## 1. Scope and confidence

This catalog covers things the player can carry, equip, buy, consume, find, or board:

- **Shared party inventory**: food, gold, keys, gems, torches, reagents, potions, scrolls, and story items.
- **Per-character equipment**: weapon, armour, helm, ring, amulet or neck item, and related ammunition.
- **Spell stock**: raw reagents and pre-mixed spell charges. The full spell list lives in `catalogs/spell-list.md`; this catalog treats spells only as inventory stock.
- **Vehicles**: horses, ships, skiffs, magic carpets, balloon art, and special wish vehicles.

Confidence varies by field. Names, broad categories, and the equipment item-id
order are high confidence because they come from resident name pools, inventory
narration strings, save-image categories, Z-stats equipment display, and the
arms-shop/R-Ready shared id space. Behaviour is medium confidence for items
with traced command handlers, such as reagents, keys, torches, gems, vehicles,
and the major quest items. Equipment base prices, ordinary attack max-damage
values, weapon-dispatch range/effect rows, and the shared combat attack-routing
model are covered here or in `systems/combat.md`; the separate equipped-item
weight statistic is covered below. Object pickup visuals are deliberately kept
separate from inventory-add class codes: `systems/containers.md` owns the
gettable visual filter and `systems/hidden-treasures.md` owns fixed Search
placements, while this catalog owns item identity, stock rows, and item-use
semantics. R-Ready owns readiness-time ammunition requirements and
equip/unequip stock movement. For the analyzed
baseline, per-shot ammunition loss, thrown-item consumption, and glass-family
breakage are negative boundaries: the traced combat attack stack does not
perform those mutations, and the separate traced equipment-stock and
readied-slot consumers do not add an attack-time ammunition, thrown-stock, or
glass-breakage path. Armour-to-defense behavior is also a negative boundary:
traced combat damage reads the cached character-defense byte, not a live
recomputation from readied armour rows.

## 2. Inventory model

The party has one shared inventory pool plus per-character equipment slots.

Shared inventory holds currency, commodities, consumables, reagents, spell charges, and story items. Food and gold are larger counters; most other carried quantities are byte-sized counters or one-byte present/absent flags. The save image persists all of these values. Shops, treasure, conversation rewards, chest results, searches, and item pickups add to the pool; spells, use-item actions, lockpicking, lighting, shopping, and food consumption remove from it.

Equipment is per character. Each character record carries six readied-equipment
slot bytes in this order: helm, body armour, weapon hand, shield/off hand,
ring, and amulet/neck item. Empty readied slots use the `0xFF` sentinel; any
other value is an equipment item id shared with the carried equipment counter
band. What is known from refusal text and command behaviour is:

- Armour cannot be changed during heated battle.
- A character must have ammunition for an ammunition-using weapon.
- A helm must be removed before another helm can be equipped.
- Body armour must be removed before another body armour can be equipped.
- Weapon readiness enforces hand occupancy; two-handed weapons require both hands free.
- Only one amulet and only one magic ring can be worn at once.
- R-Ready refuses equipment sets whose total readied burden would exceed the
  selected character's Strength.
- Ring of Invisibility and Ring of Regeneration are readied as ring-slot
  equipment, but each has a random vanish check after a successful ready action
  and a second, independent one at combat entry while worn. Ring of Regeneration
  also participates in the non-combat regeneration check that runs as the last
  step of the shared party status pass, once per turn-consuming action and once
  per ten-minute town-bed rest step, plus once per five-minute wilderness camp
  step issued directly by the camp loop. It is never an hourly effect.

R-Ready moves items between the carried equipment band and these six readied
slots. It lists rows whose carried counter is nonzero and rows already readied
by the selected character, applies ammunition, strength, occupied-slot,
combat-armour, and hand-occupancy gates, then decrements the carried counter
only after an equip is accepted. Selecting an already readied row unequips the
first matching slot and returns one carried copy up to the R-Ready equipment
stock cap of `99`. Different items are not swapped atomically into occupied
slots. Ring of Regeneration has a traced per-status-pass non-combat HP tick while worn;
Ring of Invisibility's continuing traced effect is combat-side. The public flow
lives in `systems/inventory.md`.

The active-object table is the third inventory-adjacent store. Vehicles and dropped objects exist as active objects while they are on the map. Boarding a vehicle moves the party into a vehicle state; exiting creates or restores an active-object vehicle on the map so it can be boarded later.

## 3. Category summary

| Category | Examples | Persistent form | Known sources | Catalog boundary |
|----------|----------|-----------------|---------------|-----------|
| Currency and provisions | Gold, food | Shared party counters | Treasure, dungeon chests, shops, scripted rewards | Non-chest treasure, shop, and scripted sources are owned by `systems/containers.md`, `systems/shops.md`, and `systems/conversation.md`. |
| Tools and commodities | Keys, gems, torches, Grapple / legacy magic-powder byte | Shared counters and flags | Guild shops, dungeon chests, treasure, scripted rewards | Ordinary key use, skull-key use, and Grapple/Klimb behavior are owned by command and movement specs. |
| Reagents | Sulfur Ash, Ginseng, Mandrake | Eight shared counters | Herbalists, treasure, harvesting | Vendor stock/prices and fixed harvest points are fully owned by shop/container specs. |
| Spell charges | Forty-eight spell stocks | One counter per spell | M-Mix command | Mix/cast stock gates live in `catalogs/spell-list.md` and `systems/magic.md`. |
| Equipment | Weapons, armour, helms, shields, rings, amulets | Forty-eight item-id keyed counters plus character equipment slots | Arms shops, R-Ready, treasure, drops | Equipment ids are inventory rows, shop rows, and ready-slot values. Loose-object pickup visuals are not the equipment id space. |
| Scrolls and potions | Spell-code scrolls, colored potions | Shared counters or item slots | Dungeon chests, treasure, shops or scripted finds | Use effects, chest grants, and fixed Search placements are covered; individual dialogue clues belong to the quest graph. |
| Quest and utility items | Moonstone, Crown, Sceptre, Shards | Shared flags/counters | Scripted finds, story events, and U-Use branches | Acquisition mechanics are owned by container/Search, conversation action-letter grants, or the relevant cinematic system; dialogue clues belong to the quest graph. |
| Vehicles | Horse, ship, skiff, magic carpet, balloon art | Active-object records plus party transport state for live vehicle families | Seed objects, brokers, special finds | Live vehicle behavior is owned by `systems/vehicles.md`; balloon art is not promoted to a live vehicle path. |

## 4. Currency, tools, and commodities

| Item | Type | Known role | Catalog boundary |
|------|------|------------|------|
| Gold | Currency | Shared party money. Shops debit it; treasure and reward paths credit it. Traced grant paths cap gold at 9999. | Exact non-chest treasure generation and maximum-display edge cases. |
| Food | Provision | Shared food stock. Time/rest systems consume it; table food and crops can add single units through `G` Get tile-consumable branches; the tavern/meal-counter provision branch is the confirmed shop-adjacent purchase surface. The previously suspected SHOPPES2 `F`/`S` provisions menu is shipwright-owned, not a food merchant. Traced grant paths cap food at 9999. | No separate shop-owned food purchase route in the analyzed baseline. |
| Keys / Skull Keys | Tool | Used by lock and door interactions. Failed lockpicks can break an ordinary key. Guild shops sell ordinary key stock. Container/Search odd-key grants add to the skull/special-key stock instead of the ordinary key stock. Both stocks cap at 99 through traced grant paths. | Exact split between skull keys and odd-key story locks. |
| Odd Key | Quest/tool | Inventory narration distinguishes odd-key grants from ordinary keys; the grant path stores them in the skull/special-key stock. | Which lock or quest gate consumes the odd-key stock variant. |
| Gems | Tool | Vision gems consumed by `V` View outside combat. The shared dispatcher refuses when the gem count is zero; otherwise it decrements one gem before routing to the LOOKOBJ overworld/town view or DNGLOOK dungeon minimap. Combat `V` is only a label/abort branch and does not consume a gem. Guild shops sell gems. Traced grant paths cap carried gems at 99. | Exact LOOKOBJ overworld/town pixel layout and edge-case restoration timing; see `systems/view.md`. |
| Torches | Consumable light | Guild shops sell torches; the command dispatcher has an ignite-torch verb; lighting uses a torch duration counter, not a radius. Igniting consumes one carried torch and refuses with none held; durations and the ambient floor a burning torch produces are specified in `systems/lighting.md`. Traced grant paths cap carried torches at 99. | None outstanding for light state; remaining questions are shop stock and pricing details. |
| Grapple / legacy magic-powder byte | Quest mobility gate. The save byte historically labelled magic powder is the traced outdoor Klimb gear byte: Lord Michael's conversation grant sets it, and K-Klimb refuses without it. | No separate magic-powder use consumer is currently traced. |
| Arrows | Ammunition | Required to ready bows and magic bows. Equipment refusal text confirms readiness-time ammunition gating. | No attack-time consumer in the analyzed baseline. |
| Quarrels | Ammunition | Required to ready crossbows. | No attack-time consumer in the analyzed baseline. |

### 4.1 Guild commodity prices

Guild shops sell ordinary keys, gems, and torches from fixed shop-instance
price rows. Prices are per unit.

| Guild shop | Keys | Gems | Torches |
|---|---:|---:|---:|
| The Den | 190 | 255 | 12 |
| The Guild | 160 | 200 | 11 |
| The Nemesis | 185 | 225 | 25 |

## 5. Equipment

The equipment list below is the confirmed forty-eight-row equipment item-id
space. Names are canonical display names; some abbreviated inventory labels
differ only to fit the Z-stats panel.

### 5.1 Equipment item-id order

The equipment stock band, readied-equipment slots, arms-shop stock records,
Z-stats equipment display, and R-Ready all share this forty-eight-entry item-id
space. Item id `N` addresses the carried equipment counter `N` in the save
format and is the value stored in a character's readied-equipment slot when
that item is equipped.

| Id | Item | Family | Class tag | R-Ready burden | Equipped weight stat | Base price | Attack max |
|---:|------|--------|---:|---:|---:|---:|---:|
| 0 | Leather Helm | Helm | `0x80` | 0 | 1 | 15 | 0 |
| 1 | Chain Coif | Helm | `0x80` | 1 | 2 | 50 | 0 |
| 2 | Iron Helm | Helm | `0x80` | 2 | 3 | 120 | 0 |
| 3 | Spiked Helm | Helm | `0x80` | 3 | 3 | 150 | 4 |
| 4 | Small Shield | Shield | `0x20` | 2 | 2 | 40 | 0 |
| 5 | Large Shield | Shield | `0x20` | 3 | 3 | 70 | 0 |
| 6 | Spiked Shield | Shield | `0x20` | 4 | 3 | 120 | 6 |
| 7 | Magic Shield | Shield | `0x20` | 0 | 5 | 2000 | 0 |
| 8 | Jewel Shield | Shield | `0x20` | 0 | 0 | 0 | 0 |
| 9 | Cloth Armour | Body armour | `0x40` | 0 | 1 | 20 | 0 |
| 10 | Leather Armour | Body armour | `0x40` | 2 | 2 | 50 | 0 |
| 11 | Ring Mail | Body armour | `0x40` | 4 | 3 | 100 | 0 |
| 12 | Scale Mail | Body armour | `0x40` | 6 | 4 | 150 | 0 |
| 13 | Chain Mail | Body armour | `0x40` | 10 | 5 | 300 | 0 |
| 14 | Plate Mail | Body armour | `0x40` | 12 | 7 | 700 | 0 |
| 15 | Mystic Armour | Body armour | `0x40` | 0 | 10 | 0 | 0 |
| 16 | Dagger | Weapon | `0x20` | 1 | 0 | 1 | 6 |
| 17 | Sling | Weapon | `0x30` | 2 | 0 | 10 | 6 |
| 18 | Club | Weapon | `0x20` | 3 | 0 | 5 | 8 |
| 19 | Flaming Oil | Thrown/consumable weapon | `0x30` | 2 | 0 | 5 | 8 |
| 20 | Main Gauche | Weapon | `0x20` | 3 | 1 | 15 | 8 |
| 21 | Spear | Weapon | `0x20` | 4 | 0 | 7 | 10 |
| 22 | Throwing Axe | Thrown weapon | `0x20` | 6 | 0 | 3 | 10 |
| 23 | Short Sword | Weapon | `0x20` | 5 | 0 | 40 | 12 |
| 24 | Mace | Weapon | `0x20` | 7 | 0 | 50 | 15 |
| 25 | Morning Star | Weapon | `0x20` | 8 | 0 | 60 | 15 |
| 26 | Bow | Ranged weapon | `0x30` | 8 | 0 | 75 | 10 |
| 27 | Arrows | Ammunition | `0x00` | 0 | 0 | 10 | 1 |
| 28 | Crossbow | Ranged weapon | `0x30` | 6 | 0 | 150 | 12 |
| 29 | Quarrels | Ammunition | `0x00` | 0 | 0 | 15 | 1 |
| 30 | Long Sword | Weapon | `0x20` | 9 | 0 | 70 | 15 |
| 31 | 2H Hammer | Two-handed weapon | `0x30` | 16 | 0 | 85 | 20 |
| 32 | 2H Axe | Two-handed weapon | `0x30` | 15 | 0 | 150 | 20 |
| 33 | 2H Sword | Two-handed weapon | `0x30` | 13 | 0 | 200 | 20 |
| 34 | Halberd | Two-handed weapon | `0x30` | 18 | 0 | 250 | 30 |
| 35 | Sword of Chaos | Magical weapon | `0x30` | 0 | 0 | 0 | 99 |
| 36 | Magic Bow | Magical ranged weapon | `0x30` | 0 | 0 | 800 | 15 |
| 37 | Silver Sword | Weapon | `0x20` | 8 | 0 | 250 | 12 |
| 38 | Magic Axe | Magical weapon | `0x20` | 0 | 0 | 1000 | 20 |
| 39 | Glass Sword | Weapon | `0x20` | 5 | 0 | 0 | 99 |
| 40 | Jeweled Sword | Weapon | `0x20` | 0 | 0 | 0 | 1 |
| 41 | Mystic Sword | Weapon | `0x30` | 0 | 1 | 0 | 30 |
| 42 | Ring of Invisibility | Ring | `0x02` | 0 | 0 | 450 | 0 |
| 43 | Ring of Protection | Ring | `0x02` | 0 | 2 | 500 | 0 |
| 44 | Ring of Regeneration | Ring | `0x02` | 0 | 0 | 200 | 0 |
| 45 | Amulet/Turning | Amulet | `0x04` | 0 | 0 | 900 | 0 |
| 46 | Spiked Collar | Neck item | `0x04` | 0 | 2 | 240 | 0 |
| 47 | Ankh | Miscellaneous worn item | `0x04` | 0 | 0 | 0 | 0 |

`Base price` is the canonical equipment price keyed by the equipment id. A zero
price marks rows that are not valued by the ordinary arms-equipment pricing
path; it does not make quest or special equipment disposable in other systems.

`Equipped weight stat` is the separate resident lookup that the original game
intended to use as a per-item defence contribution: a helper would sum this
column across the selected character's six readied slots, treat empty slots as
zero, and add a small bonus when the shared active-effect tag is Protection. In
the shipped game that helper produces nothing. Each per-slot accumulation is
guarded by a comparison that is tautologically true and therefore always
skipped, and the helper's result is never consumed by any reachable caller.
The combat damage path reads a cached character-defense byte instead of
recomputing defense from this table. The column is published because it is the
designers' intended balance data and a port may choose to honour it; see
`systems/combat.md` and `systems/magic.md` for the decision.

`Attack max` is the ordinary attack-damage table value for the same equipment
id. For values greater than `1` other than `99`, the default combat damage path
rolls a pre-soak damage value in the inclusive range `1..Attack max`. A value
of `99` enters the combat special branch used by glass/special swords. A value
of `1` is a fixed low-damage entry, and `0` means the row has no ordinary attack
damage value. This column is not an armour or shield defence table.

### 5.1.1 Equipment class tags

R-Ready classifies each equipment id with a compact class tag before it applies
slot occupancy and hand-equipment rules. These tags are not the same thing as
the visible family label: shields and one-handed weapons share one hand tag,
while ammunition rows have no ordinary readied-equipment tag.

| Class tag | Public meaning | Equipment ids |
|---:|---|---|
| `0x80` | Helm / head equipment | 0-3 |
| `0x40` | Body armour | 9-15 |
| `0x20` | One-hand hand equipment, including shields and one-handed weapons | 4-8, 16, 18, 20-25, 30, 37-40 |
| `0x30` | Two-hand hand equipment, including explicit two-handed, ranged, and special weapon rows | 17, 19, 26, 28, 31-36, 41 |
| `0x02` | Ring equipment | 42-44 |
| `0x04` | Amulet / neck equipment | 45-47 |
| `0x00` | Ammunition stock, not ordinary readied equipment | 27, 29 |

The tag controls R-Ready's slot family and hand-occupancy branch. The R-Ready
burden column is summed against the selected character's current readied burden
and Strength before the item is accepted. Damage, cached combat defense, price,
and the separate equipment-weight statistic remain distinct metadata. The
traced equipment-weight helper is not a non-R-Ready encumbrance gate; its only
identified caller discards the computed result after combat-side item removal.

Search/container equipment grants use the same equipment ids. Arrows (`27`) and
Quarrels (`29`) are ammunition bundle grants worth five units per award; other
equipment grants add one carried unit. All traced equipment grant counters cap
at 99.

### 5.1.2 Short display labels

Two display names exist per equipment id: the canonical name in the table above
and a shorter label used where the canonical name would not fit a narrow
column. Consumers that render into a narrow column measure the canonical name
and substitute the short label when the canonical name is **thirteen characters
or longer**; the arms-shop buy list is the traced consumer of that rule, and the
character-sheet equipment listing draws from the same short-label set.

Ten of the forty-eight ids trip the length rule. Their short labels are:

| Id | Canonical name | Short label |
|---:|---|---|
| 6 | Spiked Shield | `Spkd. Shld` |
| 10 | Leather Armour | `Leather` |
| 15 | Mystic Armour | `Myst. Armr` |
| 35 | Sword of Chaos | `Chaos Swrd` |
| 40 | Jeweled Sword | `Jewel Swrd` |
| 42 | Ring of Invisibility | `Inv. Ring` |
| 43 | Ring of Protection | `Prot. Ring` |
| 44 | Ring of Regeneration | `Regen Ring` |
| 45 | Amulet/Turning | `Am/Turning` |
| 46 | Spiked Collar | `Sp. Collar` |

Every other id's short label is either identical to its canonical name or a
shorter spelling that the length rule never selects, so an engine that always
prints the canonical name below the threshold matches the original. Of the ten
above, ids `6`, `10`, `42`, `43`, `44`, `45`, and `46` appear in shipped
arms-shop stock rows; `15`, `35`, and `40` do not.

Source provenance: derived from private analysis note
`../u5-decomp/functions/SHOPPES_OVL/`.

### 5.2 Armour, helms, and shields

| Item | Family | Known role | Catalog boundary |
|------|--------|------------|------|
| Leather Helm | Helm | Head-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Chain Coif | Helm | Head-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Iron Helm | Helm | Head-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Spiked Helm | Helm | Head-slot armour; also has a nonzero ordinary attack max value. | No traced live defense recomputation; combat reads cached character defense. |
| Small Shield | Shield | Off-hand item. | No traced live defense recomputation; combat reads cached character defense. |
| Large Shield | Shield | Off-hand item. | No traced live defense recomputation; combat reads cached character defense. |
| Spiked Shield | Shield | Off-hand item; also has a nonzero ordinary attack max value. | No traced live defense recomputation; combat reads cached character defense. |
| Magic Shield | Shield | Magical shield. | No traced live defense recomputation; special effects outside ready/combat-passive coverage remain untraced. |
| Jewel Shield | Shield | High-tier shield. | No traced live defense recomputation; special effects outside ready/combat-passive coverage remain untraced. |
| Cloth Armour | Body armour | Body-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Leather Armour | Body armour | Body-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Ring Mail | Body armour | Body-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Scale Mail | Body armour | Body-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Chain Mail | Body armour | Body-slot armour. | No traced live defense recomputation; combat reads cached character defense. |
| Plate Mail | Body armour | Heavy body armour. | No traced live defense recomputation; combat reads cached character defense. |
| Mystic Armour | Body armour | Top-tier or magical body armour. | No traced live defense recomputation; special effects outside ready/combat-passive coverage remain untraced. |

### 5.3 Weapons and ammunition

The `Attack max` column in the equipment id table is an ordinary damage ceiling,
not a range or hit-chance table. Combat attack handling has a shared architecture
across party and monster actors:

- The attack dispatcher separates zero-damage rows, which route to spell or
  special effect handling, from nonzero-damage rows, which route to weapon-style
  target selection and attack application.
- Target distance for AI and ranged/effect attacks uses the combat arena's
  truncated Euclidean slot range. Attacks beyond the relevant per-class or
  per-weapon range cap do not apply damage.
- Adjacent targets use the melee damage path. Non-adjacent targets that pass the
  range gate use the ranged/projectile/effect path and the same shared to-hit
  helper unless a special effect forces a hit or redirects the impact.
- The shared to-hit helper accepts certain special action/effect tiles as
  always-hit cases; otherwise it computes a score from attacker and defender
  combat ratings, `(attacker - defender + 30) / 2`, and compares that score
  with a uniform random byte.

The traced weapon-dispatch range table is item-id keyed and independent of the
`Attack max` damage ceiling. A range cap of zero means the ordinary
weapon-dispatch path has no non-adjacent route for that item. A positive cap
allows targeting any arena cell whose truncated Euclidean distance from the
attacker is within the cap; cap `15` reaches the whole eleven-by-eleven arena.
The companion effect code is the small projectile/impact variant passed into
the shared ranged/effect resolver. Rows with range cap zero do not make that
effect code live through this weapon-dispatch path.

| Id | Item | Non-adjacent range cap | Effect code | Compatibility note |
|---:|---|---:|---:|---|
| 16 | Dagger | 3 | 0 | Throwable or reach-capable through the ranged/effect route. |
| 17 | Sling | 4 | 7 | Uses the ranged/effect route; no separate sling ammunition stock is traced. |
| 19 | Flaming Oil | 4 | 3 | Uses a distinct thrown-effect variant; the traced combat attack stack does not consume quantity. |
| 21 | Spear | 5 | 0 | Pole/throw reach through the ranged/effect route. |
| 22 | Throwing Axe | 4 | 2 | Uses a distinct thrown-effect variant; the traced combat attack stack does not consume quantity. |
| 25 | Morning Star | 2 | 0 | Short reach beyond adjacency. |
| 26 | Bow | 7 | 0 | Requires arrows to ready; the traced combat attack stack does not decrement arrows. |
| 28 | Crossbow | 8 | 0 | Requires quarrels to ready; the traced combat attack stack does not decrement quarrels. |
| 34 | Halberd | 2 | 0 | Reach weapon. |
| 36 | Magic Bow | 15 | 0 | Requires arrows to ready; cap reaches any arena cell. |
| 38 | Magic Axe | 15 | 2 | Uses the thrown-axe effect variant and reaches any arena cell. |

No separate item-specific chance-to-hit table is traced in this dispatcher.
Once the range/effect route has selected an impact target, ordinary hits still
use the shared combat to-hit helper described above unless the effect family
forces a special result. The traced combat attack stack does not decrement
arrows or quarrels, does not decrement the readied weapon's carried equipment
counter, and does not clear the readied weapon slot for thrown or glass-family
attacks. The separate traced equipment-stock and readied-slot consumers are
R-Ready/equip-time stock movement, carried-equipment grants, display/search
helpers, and magic-ring combat removal; none adds an attack-time ammunition,
thrown-stock, or glass-breakage path for the analyzed baseline.

| Item | Family | Known role | Catalog boundary |
|------|--------|------------|------|
| Flaming Oil | Thrown/consumable weapon | Listed with weapons and has an ordinary attack max value; non-adjacent range cap 4 with effect code 3. | No attack-time consumption in the analyzed baseline. |
| Main Gauche | Weapon | Small blade or off-hand weapon with an ordinary attack max value. | Detailed hand rule. |
| Dagger | Weapon | Small blade with an ordinary attack max value; non-adjacent range cap 3. | No attack-time consumption in the analyzed baseline. |
| Throwing Axe | Weapon | Throwable axe with an ordinary attack max value; non-adjacent range cap 4 with effect code 2. | No attack-time consumption in the analyzed baseline. |
| Sling | Ranged weapon | Ranged weapon with an ordinary attack max value; non-adjacent range cap 4 with effect code 7. | No separate ammunition stock is traced. |
| Club | Weapon | Simple melee weapon with an ordinary attack max value. | None for ordinary damage. |
| Spear | Weapon | Pole weapon with an ordinary attack max value; non-adjacent range cap 5. | One- or two-handed rule outside R-Ready's stored class tag. |
| Mace | Weapon | Melee weapon with an ordinary attack max value. | None for ordinary damage. |
| Bow | Ranged weapon | Uses arrows at ready time, has an ordinary attack max value, and has non-adjacent range cap 7. | No attack-time ammunition consumption in the analyzed baseline. |
| Crossbow | Ranged weapon | Uses quarrels at ready time, has an ordinary attack max value, and has non-adjacent range cap 8. | No attack-time ammunition consumption in the analyzed baseline. |
| Short Sword | Weapon | One-handed sword with an ordinary attack max value. | None for ordinary damage. |
| Long Sword | Weapon | Sword with an ordinary attack max value. | Detailed hand rule. |
| Morning Star | Weapon | Heavy melee weapon with an ordinary attack max value; non-adjacent range cap 2. | None for ordinary damage. |
| Sword of Chaos | Magical weapon | Named high-tier sword using the combat special attack value. Its drawback is now traced: while item id 35 sits in the wielder's weapon-hand or shield-hand readied slot, that character's combat turns are taken away from the player. The combat turn dispatcher stamps the controlled/charmed descriptor bit on the character, clears the active-player sentinel, and runs the turn through the automatic actor driver instead of reading a command, so the character shows the `C` status letter and acts on its own. See `systems/combat.md` Section 6.1a. | Whether any narration accompanies the compulsion. |
| Silver Sword | Weapon | Special sword, likely effective against specific enemies. | Exact enemy interactions. |
| Glass Sword | Weapon | Named weapon using the combat special attack value. | No attack-time breakage in the analyzed baseline. |
| Jeweled Sword | Weapon | High-tier sword with a fixed low ordinary attack value. | Exact special-purpose use, if any. |
| Mystic Sword | Weapon | Top-tier or magical sword with an ordinary attack max value. | Exact special effect, if any. |
| 2H Hammer | Two-handed weapon | Requires both hands free and has an ordinary attack max value. | Display weight. |
| 2H Axe | Two-handed weapon | Requires both hands free and has an ordinary attack max value. | Display weight. |
| 2H Sword | Two-handed weapon | Requires both hands free and has an ordinary attack max value. | Display weight. |
| Halberd | Two-handed weapon | Polearm with an ordinary attack max value; non-adjacent range cap 2. | Display weight. |
| Magic Bow | Magical ranged weapon | Uses arrows at ready time, has an ordinary attack max value, and has arena-wide range cap 15. | No attack-time ammunition consumption in the analyzed baseline. |
| Magic Axe | Magical weapon | Named axe with an ordinary attack max value; arena-wide range cap 15 with effect code 2. | No attack-time consumption in the analyzed baseline. |
| Arrows | Ammunition | Used by bows. Search/container equipment grants award five-arrow bundles, and traced equipment grant paths cap carried stock at 99. The traced combat attack stack does not decrement this stock. | No attack-time consumer in the analyzed baseline. |
| Quarrels | Ammunition | Used by crossbows. Search/container equipment grants award five-quarrel bundles, and traced equipment grant paths cap carried stock at 99. The traced combat attack stack does not decrement this stock. | No attack-time consumer in the analyzed baseline. |

### 5.4 Rings, amulets, and miscellaneous worn items

| Item | Family | Known role | Catalog boundary |
|------|--------|------------|------|
| Ring of Invisibility | Ring | Ring-slot equipment. After accepted R-Ready, it has a 1-in-16 immediate vanish check; when worn by a combatant, it marks that combatant hidden/suppressed. A second, independent 1-in-16 vanish check runs at combat entry, inside the pass that seats the party, and can destroy the ring before that marking happens; it is not a per-round check. No separate non-combat invisibility timer or world-mode effect writer is traced. | Broader combat visibility details live in `systems/combat.md`. |
| Ring of Protection | Ring | Magic ring; one ring may be worn at a time. | Protection value, duration, and whether it has any related random-removal path. |
| Ring of Regeneration | Ring | Ring-slot equipment. After accepted R-Ready, it has a 1-in-16 immediate vanish check. Outside combat, a regeneration check gives each non-Dead wearer a 1-in-8 chance to recover exactly 1 HP, capped at maximum HP. It is reached once per turn-consuming action in world, town, and dungeon modes and once per ten-minute town-bed rest step, in both cases as the last step of the shared party status pass, and once per five-minute wilderness camp step, in that case called directly by the camp loop rather than through the status pass. It is never an hourly effect. In combat, each living wearer gets exactly one regeneration tick, applied by the pass that seats the party at combat entry, and faces one independent 1-in-16 vanish check in that same pass. Neither is repeated by the combat round loop; earlier wording attributing the in-combat removal to the round loop is withdrawn. | Non-combat cadence lives in `systems/time.md`; combat healing cadence lives in `systems/combat.md`. |
| Amulet/Turning | Amulet | Amulet/neck-slot equipment row. Its combat passive effect applies when a living party wearer is targeted by a turnable ranged/effect attack: half the time, the attack is forced through the scattered-impact path instead of the ordinary hit-roll result. The v1 flagged attackers are Mage, Wanderer, Blackthorn, Lord British, Sea Horse, Reaper, Gazer, Daemon, and Shadow Lord. | No U-Use activation, countdown, random disappearance, or non-combat periodic effect is traced. |
| Spiked Collar | Neck item | Listed beside amulets; likely neck-slot equipment. | Whether it is equippable, cursed, or creature-specific. |
| Ankh | Miscellaneous amulet/neck equipment row | Metadata places it in the same amulet/neck equipment class as the neck-slot rows above. The traced CAST U-Use picker and dispatcher do not include Ankh in their usable-item family, and no carried quest, ritual, or consumable consumer is traced. | No U-Use activation, quest ritual, or consumable effect is traced. |

## 6. Reagents and spell stock

Raw reagents are party-shared counters. The M-Mix command reads the eight raw
reagent counters, shows only nonzero reagent counters in its selection list,
lets the player select a reagent set and nonzero quantity, and compares the
selected set to the recipe for the chosen spell. A matching recipe creates
pre-mixed spell charges; a wrong recipe consumes the selected reagents but
creates no charges. Spell charge counters are capped at 99 in the current
command note.

The display order for mixing is:

| Reagent | Common role |
|---------|-------------|
| Sulfur Ash | Fire, light, and several utility recipes. |
| Ginseng | Healing and sleep-family recipes. |
| Garlic | Protection and undead/curse-related recipes. |
| Spider Silk | Binding, field, and healing recipes. |
| Blood Moss | Motion, wind, speed, and several high-circle recipes. |
| Black Pearl | Projectile, fire, and field recipes. |
| Nightshade | Poison, illusion, and rare high-circle recipes. |
| Mandrake | Rare power reagent for high-circle spells. |

`catalogs/spell-list.md` is the authoritative lookup for which spell uses which reagents. This catalog's contract is only that the eight reagents are inventory items, vendors sell some of them at fixed per-vendor prices, fixed midnight Search points can harvest mandrake root and nightshade with a once-per-day cooldown, and mixing consumes reagent counters. The exact harvest coordinates and quantity roll are specified in `systems/containers.md`.

### 6.1 Herbalist price matrix

Herbalists use a fixed per-shop reagent matrix. Prices are gold per ounce.
An em dash means the reagent is not stocked by that herbalist and is omitted
from the shop menu.

| Herbalist | Sulfur Ash | Ginseng | Garlic | Spider Silk | Blood Moss | Black Pearl | Nightshade | Mandrake |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| The Herbalist | — | 20 | 18 | 12 | — | — | 12 | 13 |
| Healers Herbs | 12 | 16 | 16 | 8 | 20 | — | — | — |
| The Alchemist | 14 | 16 | — | — | 30 | 18 | — | — |
| Mysticism | — | — | — | 6 | 8 | 8 | 10 | 15 |
| The Sharper Mage | — | — | — | — | 50 | — | 30 | 40 |

## 7. Scrolls and potions

The inventory narration and item-name pools identify scroll and potion families.
The CAST-owned U-Use handler dispatches both families directly; scroll branches
are now named at the effect-family level, and potions have a verified
display-order-to-effect mapping.

### 7.1 Spell scrolls

Eight scroll labels use the same compact code vocabulary as spell parsing, but
they are item rows with their own effect constants and gates. U-Use decrements
the selected scroll counter before any branch-specific scene gate or target
prompt runs, then prints the scroll-use label and the branch's effect label.
Container/Search grants use the same eight ids, mask the grant subtype to the
low three bits for the displayed scroll label, and cap each scroll counter at
99. The HMS Cape plans grant is a special subtype in the same grant family, but
sets the plans flag instead of a scroll counter.

| Scroll id | Code | Cross-reference | U-Use effect and gates |
|-----------|------|-----------------|------------------------|
| 0 | `LV` | Vas Lor / Great Light | Prints `Light!`, sets the magic-light counter to 240 minutes, and plays the light presentation effect. It writes the light counter, not the timed-effect slot, and it is not a torch inventory consumer. |
| 1 | `HR` | Rel Hur / Wind Change | Prints `Wind change!`, prompts for a wind direction, and applies the wind only when the active scene byte is below 33: overworld or named town/castle/keep/dwelling scenes. Dungeon-class scenes return without changing wind after the prompt. |
| 2 | `IS` | In Sanct / Protection | Prints `Protection!` and installs the shared timed-effect tag `P` with a 100-turn duration, replacing whatever effect the slot held. Like the spell, it has no mechanical consequence in the shipped game: the defence bonus the `P` tag was meant to grant rides on a per-item defence total that is unreachable and never read. See `systems/magic.md`. |
| 3 | `AI` | In An / Negate Magic | Prints `Negate magic!` and installs the shared timed-effect tag `N` with a 20-turn duration, replacing whatever effect the slot held. Combat cast absorption reads the same `N` tag as the cast spell path. |
| 4 | `IQW` | In Quas Wis family | Prints `View!`. Combat-class scenes print `Not here!` and stop. Overworld and named interior scenes invoke the surface/local view renderer at the party coordinates; dungeon-class scenes invoke the dungeon V-View renderer. No gem counter is spent by this scroll path. |
| 5 | `CKX` | Kal Xen Corp / Summon | Prints `Summon Daemon!`. Combat-class scenes invoke the summon/target animation helper; non-combat scenes print `Not here!` and perform no summon. Combat `U` does reach the item-use handler (an earlier note that it did not is withdrawn), so this effect is reachable both from the scroll handler and from the combat command's item-use path where the family's own gates allow. |
| 6 | `CIM` | In Mani Corp / Resurrect | Prints `Resurrection!`. Non-combat scenes prompt for a party member, invoke the same resurrection helper described in `systems/magic.md`, and refresh the party stats display. A successful scroll resurrection leaves the revived member Good with 1 current HP, class-derived mana, recomputed level, and maximum HP equal to thirty times that level. Combat-class scenes print `Not here!`. |
| 7 | `AT` | An Tym / Negate Time | In Stonegate and Doom, prints `No effect!` and plays the no-effect presentation. In all other scenes, prints `Negate time!` and installs the shared timed-effect tag `T` with a 20-turn duration, replacing whatever effect the slot held. |

### 7.2 Potions

Potions are color-coded. The inventory narration composes a color with the
potion noun, and the carried potion counters use this display order:
Container/Search grants use the same eight ids and cap each colour counter at
99.

| Potion id | Color | Normal effect |
|-----------|-------|---------------|
| 0 | Blue | Wake a sleeping target. If the selected target is asleep, set the party status back to good; in combat, also clear the matching active combat sleep presentation when the active combatant maps to that party member. If the target is not asleep, no status change succeeds. |
| 1 | Yellow | Heal the selected target through the shared small-heal helper: Dead targets are skipped, other statuses keep their status byte, and a small HP amount is added up to maximum HP. On success, print the healed feedback and refresh party status display. |
| 2 | Red | Cure poison. If the selected target is poisoned, set status back to good, print the poison-cured feedback, and refresh party status display. |
| 3 | Green | Poison. If the selected target is good, set status to poisoned, print the poisoned feedback, and refresh party status display. |
| 4 | Orange | Sleep. If the selected target is good, set status to sleeping in non-combat scenes; in combat, apply the combat sleep/disabled presentation to the selected party member. |
| 5 | Purple | Combat-only "Poof" presentation. Outside combat, print the no-noticeable-effect feedback. In combat, mark the active combatant's linked presentation record with the temporary visual effect. |
| 6 | Black | Combat invisibility. Outside combat, print the no-noticeable-effect feedback. In combat, mark the active combatant hidden/suppressed and update its linked presentation record. |
| 7 | White | Surface/town visibility sweep. Dungeon and combat-class scenes print the no-noticeable-effect feedback. Accepted overworld and named interior scenes run a twenty-frame visibility/animation sweep centered on the party with radius 32 and finish with a normal world redraw. This branch does not spend a gem, enter the modal View overlay, set an active-effect tag, or persist a detector flag. |

U-Use decrements the selected potion counter and selects a party-member target
before final effect selection. The final effect is usually the selected colour,
but the handler applies a variation roll first: fourteen chances in sixteen use
the selected colour's effect, one chance in sixteen forces the Orange sleep
effect, and one chance in sixteen replaces the effect with a random potion id
from `0..7`. This variation changes only the effect branch after the counter is
spent; the consumed counter is still the colour the player chose.

## 8. Quest and utility items

These items are named by inventory strings, save-image categories, use-item dispatch, or story-specific notes. Where the exact use effect is not decoded, the table says so.

| Item | Known role | Catalog boundary |
|------|------------|------|
| Moonstone | Story item tied to Blackthorn rescue/refuge handling (`systems/blackthorn.md`) and Gate Travel. Burying one records the current valid location into that stone's saved gate slot when outside dungeon/combat scenes and when the underfoot tile is `4..10`, `44`, or `45`; *Vas Rel Por* later teleports to the selected slot. Searching a matching buried coordinate surfaces a "strange rock" pickup, and collecting it grants the Moonstone and invalidates that slot. | This catalog owns the carried item and use/recovery contract. The rescue/refuge presentation is owned by `systems/blackthorn.md`; the saved destination slots are owned by `formats/saved-gam.md`. |
| Grapple | Quest mobility item/flag. Lord Michael's conversation grant sets the Grapple flag used by outdoor K-Klimb. On the overworld and underworld planes, K-Klimb refuses without this flag; with it, on foot, and facing a climbable mountain tile, each living party member rolls Dexterity against `1..30` and may take `1..5` fall damage before the party advances one cell. | Exact inventory display label/stock presentation, if any. |
| Magic Carpet | Both an inventory item and a vehicle/boarding target. U-Use can board a carried carpet when the party is on foot, outside dungeon/combat scenes, and standing on an accepted tile; success changes the party transport marker to carpet and decrements carried carpet stock. Older notes conflated it with the outdoor climb gate, but the traced Klimb handler reads the separate Grapple flag. | Carried-stock grants use conversation or Search/Get/container paths. Normal carpet terrain and transport-marker ranges live in `systems/movement.md` and `systems/vehicles.md`. |
| Sandalwood Box | Story item returned to Lord British in the endgame sequence. Saduj's hostile clue identifies Lord British's chamber as the story route for discovering the hidden box's importance. The shipped castle roster places the non-speaking `CASTLE:0` object slot 31 at local `(18,12,2)` with a gettable object-tile family and separate inventory-add code `0x0E`; `G` Get accepts the object tile through the per-map pickup visual filter, then dispatches the shared Search/Get/container inventory-add writer, which sets the save-backed box flag. The endgame confirmation reads that flag. | No traced acquisition handler requires Saduj's conversation as a mechanical prerequisite; his branch is a clue. Inventory-add code `0x0E` is not itself a gettable object-tile id. |
| Plans for the HMS Cape | Shipboard utility. U-Use marks the ship-rigging flag and reports that the ship is rigged for double speed; off-ship use refuses. The public sailing effect is the hoisted-sail wait-pass timing change in `systems/weather.md`. | Search/Get/container grants store this as the special scroll-family plans flag; ship purchase and sailing behavior are owned by shop and weather specs. |
| Crown of Lord British | Unique royal item. U-Use toggles it through the one shared timed-effect slot described in `systems/magic.md`: using the Crown while its own code already occupies the slot prints the removal acknowledgement and vacates the slot; otherwise the handler prints the wearing message, plays a sound cue, and installs the Crown code with the permanent duration. While worn, the Crown code is read by the enemy-cast gate and acts as a permanent Negate Magic aura. Because the slot is shared and singular, donning the Crown cancels any active buff, and camping, entering an innkeeper menu, or the Blackthorn rescue restoration silently strips it. Note this worn state is separate from the Crown ownership flag, which gates magic absorption in Lord Blackthorn's Castle; acquisition-side rescue/NPC-table work belongs to `systems/containers.md` and `systems/endgame.md`, not to wearing the Crown. | Dialogue reactions, if any, belong to targeted quest-graph branch validation rather than item activation. |
| Sceptre of Lord British | Unique royal item. U-Use is not a worn-state toggle for the Sceptre. In eligible non-dungeon scenes, the branch prints the wielding label, scans the party-centered nearby square for the top-down `0x70..0x7F` barrier/field family, rewrites each accepted cell to ordinary open ground with redraw/effect presentation, and reports success when any cell dissolves; if none are accepted, it reports no effect or the alternate helper result. Stonegate entry presentation is gated by Sceptre ownership and owned by `systems/town-mode.md`, not by Sceptre U-Use. | Exact per-tile art labels belong to `catalogs/tile-catalog.md`. |
| Amulet of Lord British | Unique royal item distinct from Amulet/Turning equipment. U-Use toggles it through the one shared timed-effect slot described in `systems/magic.md`: using the Amulet while its own code already occupies the slot prints the removal acknowledgement and vacates the slot; otherwise the handler prints the wearing message, plays a sound cue, and installs the Amulet code with the permanent duration. The Amulet code has exactly one consumer: the overworld void tile, which forces the effective lighting threshold to zero unless the Amulet is worn - a total blackout that hides even the party's own tile and blocks the pending move (`systems/lighting.md` Section 7) - so the Amulet is what lets the party see anything at all in the void. Because the slot is shared and singular, donning the Amulet cancels any active buff, and camping, entering an innkeeper menu, or the Blackthorn rescue restoration silently strips it. | Dialogue or location predicates, if any, belong to quest-graph validation rather than item activation. |
| Shard of Falsehood | Shadowlord shard story item. U-Use dispatches shard index 0 into the Shadowlord-destruction handler. A successful destruction consumes the shard: the handler clears its carried flag together with retiring the Shadowlord. A refused attempt keeps it. | Search/Get/container grants use the same shard index; destruction requires the matching interior destruction position and active Faulinei encounter, as specified by the quest graph. |
| Shard of Hatred | Shadowlord shard story item. U-Use dispatches shard index 1 into the Shadowlord-destruction handler. A successful destruction consumes the shard: the handler clears its carried flag together with retiring the Shadowlord. A refused attempt keeps it. | Search/Get/container grants use the same shard index; destruction requires the matching interior destruction position and active Astaroth encounter, as specified by the quest graph. |
| Shard of Cowardice | Shadowlord shard story item. U-Use dispatches shard index 2 into the Shadowlord-destruction handler. A successful destruction consumes the shard: the handler clears its carried flag together with retiring the Shadowlord. A refused attempt keeps it. | Search/Get/container grants use the same shard index; destruction requires the matching interior destruction position and active Nosfentor encounter, as specified by the quest graph. |
| Spyglass | Night utility, surface plane only. U-Use permits a look only when all three hold: the party is on the **surface** world plane (the same lower-half magnitude test on the world-plane value that the Sextant uses, not an equality against the surface value); the scene is the outdoor world scene or a town-class scene (dungeon-class and combat-class scenes are excluded — a broader scene gate than the Sextant's, which admits the outdoor scene only); and the hour is in the night window `19..23` or `0..5` — the same window the Sextant uses. A scene or plane failure prints the "not here" refusal; a daytime hour prints the no-stars refusal. **The Underworld is excluded by the same plane condition that excludes it from the Sextant.** The successful path prints the looking message and enters the same LOOKOBJ sky renderer specified in `systems/view.md` section 4.2. Lord Seggallion's shipped conversation branch grants the carried-item flag. | Pixel-perfect sky/view presentation belongs to `systems/view.md`; this row owns item gates and acquisition. |
| Sextant | Outdoor night-only navigation utility. U-Use permits a reading only when **all three** of these hold: the party is on the **surface** world plane (the shipped test is a magnitude comparison — the world-plane value must lie in the lower half of its byte range — rather than an equality against the surface value; the two agree because on the outdoor scene the plane only ever holds the surface value or the all-ones Underworld value, and the threshold form is the safer contract if an engine represents the plane numerically); the scene is the outdoor world scene; and the hour is in the night window `19..23` or `0..5`. The item label is printed unconditionally, before any of the three tests, so it appears even on a refusal. Four outcomes exist: the label, then either the "only outdoors" refusal (any non-outdoor scene, **and also the Underworld**), the "only at night" refusal (hours `6..18` on the surface outdoor scene), or the position label followed by the coordinate line. **The Underworld does not qualify.** It is the outdoor world scene on the *other* world plane, and the plane is tested first, so a use in the Underworld prints the same "outdoors" refusal an indoor scene produces — there is no separate Underworld message and no coordinate readout, even though the party is standing outdoors. The branch consumes and writes nothing on any of its four paths. Formatting: the shared sextant-style formatter prints the Y-coordinate (latitude) first, then the X-coordinate (longitude), each encoded as two `A`..`P` nibble letters separated by an apostrophe **and terminated by its own double-quote**, with the two coordinates joined by a comma and a space. The formatter also emits a **newline before** the coordinate pair and another after it, while the position label the Sextant prints carries no newline of its own — so the reading always appears as the label on one line and the coordinate pair on the line below. *Corrected:* an earlier revision of this row described only the intra-line punctuation and a closing newline, which leaves an implementer free to print label and coordinates on one line; that omission is withdrawn. *Corrected:* an earlier revision of this row (and of `systems/magic.md`) described a single trailing double-quote at the end of the line; that is withdrawn — there are two, one per coordinate. David's shipped conversation branch grants the carried-item flag. | Caller-side refusal text variants. Whether the U-Use item picker itself would ever hide the Sextant row is not traced; if it did, the label simply would not print, and the item would still be unusable. The shared formatter brackets the coordinate line with two calls into a presentation helper whose screen-placement effect is **not established**, so the pair's exact vertical placement is an open point. Whether the reading costs a game turn is also untraced — turn accounting sits above this handler. None of the four outcomes has been confirmed in a running game; one probe would settle all of them. |
| Pocket Watch | Time utility. U-Use prints the current time as a twelve-hour reading: the hour (zero maps to twelve after modulo-twelve conversion), then a colon, then the **minutes** as a two-digit zero-padded field, then the AM/PM suffix selected from the current hour byte. The minutes byte it prints is the same byte the per-turn clock accumulates and reduces at sixty (`systems/time.md`). | *Corrected:* an earlier revision of this row said "No minute display is present in the traced branch." That is **wrong** and is withdrawn — the branch does print minutes. |
| Black Badge | Wearable story or faction item. U-Use behaves exactly like the two regalia items and uses the same one shared timed-effect slot described in `systems/magic.md`: using the Badge while its own code already occupies the slot prints the same removal acknowledgement and vacates the slot; otherwise it installs the Badge code with the permanent duration and marks party/status presentation dirty. The only difference worth specifying is presentational — donning the Badge plays no sound cue, where the Amulet and Crown do. While worn, the Badge code is the disguise that unlocks the Blackthorn palace-gate password exchange in `systems/blackthorn.md`; camping, entering an innkeeper menu, or the Blackthorn rescue restoration clears the slot and closes that gate again. Elistaria's shipped conversation branch grants the carried-item flag. No separate quest/NPC mutation is traced in the U-Use branch. | Dialogue reactions, if any, belong to targeted quest-graph branch validation rather than item activation. |
| Wooden Box | Named box-family item, distinct from the Sandalwood Box story flag. The traced CAST Box U-Use branch prints the box label and asks how to use it, but direct U-Use does not perform the terminal Sandalwood Box handoff; that handoff belongs to the Lord British endgame confirmation flow. | Treat the direct Box U-Use prompt as non-terminal presentation unless a separate branch is traced; it is not the Sandalwood Box victory handoff. |
| Skull Keys | Named key-family stock. U-Use decrements the skull-key/special-key counter and attempts the adjacent-lock helper in supported non-combat scenes; this family's own scene gate refuses in dungeon and combat scenes, and ordinary `J` Jimmy key use is a separate command. (The `U` command itself does reach the item-use handler in combat; it is the per-family gate that refuses here.) | This row owns carried stock identity. Lock matching and refusal effects belong to `systems/doors-and-z-transitions.md`. |
| Odd Key | Key-family story item. Search/container odd-key narration grants the same skull/special-key stock used by Skull Keys rather than ordinary skeleton keys. | Odd-key grants feed the skull/special-key stock; any authored lock that consumes that stock is a door/quest predicate, not a separate inventory row. |
| Magic Powder | Legacy label for the same save byte now traced as the Grapple/Klimb gear gate. | No separate magic-powder item effect or source is currently traced. |
| Ankh | Equipment-row item, not a traced CAST U-Use item. See section 5.4. | No separate quest or ritual consumer is traced. |

Search/container shard grants use the same public shard indexes `0..2` as
U-Use and set the corresponding ownership flag.

The world source of the three shards, and of the Amulet of Lord British, is a
fixed-coordinate placement on the Underworld plane rather than a container or a
hidden-treasure record. The four coordinates and the placement gates — including
the rule that a shard stops being placed once its Shadowlord is vanquished — are
published in `catalogs/quest-graph.md` Section 5.

## 9. Vehicles

Vehicles straddle inventory and world state. A vehicle can be a map object, a shop purchase, a carried or owned item, and a current party state.

| Vehicle | Form | Known behaviour | Catalog boundary |
|---------|------|-----------------|------|
| Horse | Active-object vehicle; Talk-entered stable purchase path | Boardable when available. Overland transport. Stable base prices are listed below; the shop quote applies the speaking member's Intelligence adjustment before the affordability check. Mounted-horse passability and one-cell movement cadence are owned by `systems/movement.md` and `systems/vehicles.md`. | None at item-catalog level. |
| Ship | Active-object vehicle; ship-broker purchase path | Boardable; carries condition and skiff-count state; can fire broadsides; warns when badly damaged or without skiffs; sail state determines whether wind cadence applies. Shipwright Frigate purchases create a full-hull ship with two skiffs. Shipwright base prices are listed below. Boarding from a carpet-compatible state stows a carried carpet for later ship-exit redeploy when no landing support or skiffs are available. Ship facing and sail-state marker ranges are owned by `systems/vehicles.md`. | No traced command-level repair path in the analyzed baseline. |
| Skiff | Active-object vehicle; also ship-carried | Boardable; water transport at the ordinary mode turn cost. The time system's `Q` half-increment belongs to the Quickness magic effect, not to skiffs; the earlier "skiff/raft timing state" reading is withdrawn. Facing-sensitive skiff terrain predicates are owned by `systems/movement.md`. | Ship-carried object variants outside the normal skiff transport-marker range. |
| Magic Carpet | Inventory item and active vehicle | Boardable as a carpet. The `T` timing tag is the Negate Time magic effect, not carpet identity, and no vehicle path writes it; outdoor Klimb is gated by the Grapple flag instead of by carpet ownership. Normal carpet terrain predicates are owned by `systems/movement.md`. | Inventory flag and edge variants outside the normal carpet transport-marker range. |
| Balloon | Vehicle art family | Balloon sprites are catalog assets, but the traced B-Board, X-Xit, U-Use, shipwright, and movement contracts do not provide a live balloon transport path in the analyzed baseline. | Do not infer boarding, purchase, transport markers, or movement rules from art alone. |
| Corvette, Ferrari, Lamborghini, Lotus, Porsche | Wishing-well vehicle names | Easter-egg vehicle names in wishing-well strings. | In the granting scenes, every accepted name maps to the same horse-family active-object spawn; no distinct car or carpet object is selected by the typed word. |

Vehicles are persisted through the active-object and save/load systems.
Dismounting leaves a vehicle object on the map; loading restores the per-plane
object tables through the `.OOL` companion files. Command-level boarding,
exiting, and ship-fire behaviour lives in `systems/vehicles.md`. Outdoor Klimb
is not a vehicle action; it requires the Grapple flag and is specified with
Z-transition command behaviour in `systems/doors-and-z-transitions.md`.

### 9.1 Vehicle purchase base prices

Horse traders and shipwrights use fixed local base prices before the ordinary
shop quote and post-transaction surcharge behaviour. Horse quotes also apply
the speaking member's Intelligence adjustment described in `systems/shops.md`.

| Stable | Horse base price |
|---|---:|
| Horse & Rider | 100 |
| The Stablehouse | 130 |
| Wishing Well Horses | 160 |

| Shipwright | Frigate | Skiff |
|---|---:|---:|
| Island Shipwrights | 600 | 200 |
| The Crow's Nest | 753 | 175 |
| The Oaken Oar | 650 | 125 |
| The Rusty Bucket | 700 | 100 |

Shipwright quotes take the same Intelligence adjustment as horse quotes. A paid
vessel is not handed over in the shop: it is queued and then placed on the
overworld at a fixed per-shipwright delivery cell, published with these rows in
`systems/shops.md` Section 8.7. That cell is a sidecar value belonging to the
shipwright row, not the selling town's entrance or exit coordinate.

## 10. Shops and acquisition

Known acquisition paths:

- **Weaponsmiths and armourers** sell equipment from fixed per-shop stock
  tables. The `B` buy list is a per-shop list of up to eight equipment item ids;
  each id maps directly to the item-name row, base-price row, and shared
  equipment counter. Buy quotes use the canonical equipment price adjusted by
  the speaking party member's Intelligence, check gold and carry capacity,
  debit gold on acceptance, increment the shared equipment counter, and do not
  deplete shop stock. The `S` sell path scans nonzero carried equipment
  counters, refuses unsellable rows, and on acceptance adds gold and decrements
  the sold counter.
- **Guild shops** sell keys, gems, and torches.
- **Herbalists** sell reagents, with fixed per-vendor availability and prices.
  Zero-priced resident entries are omitted from the shop menu rather than sold.
- **Rare reagent harvests** are Search results at three fixed overworld
  coordinates: two mandrake-root points and one nightshade point. Each point is
  accepted only at midnight, can be harvested once per in-game day, grants a
  rolled 2..15 quantity, and caps the corresponding reagent counter at 99.
- **Tavern and meal-counter provisions** are the known shop-adjacent
  food/provision purchase surface. The branch debits gold per served unit and
  writes the shared food counter. The SHOPPES2 `F`/`S` menu belongs to
  shipwright sales; the analyzed baseline has no separate Talk-entered food
  merchant purchase path.
- **Tavern drinks** are priced in `systems/shops.md`. They debit gold through
  the tavern menu but do not add item inventory or provision stock.
- **Horse traders** handle a Talk-entered vehicle sale that places a horse
  active object after payment. **Ship brokers** also have a Talk-entered
  shop-triggered sale flow; after payment, the next overworld entry places a
  watercraft active object at that shipwright's fixed delivery cell, published
  as a per-shipwright coordinate column in `systems/shops.md` Section 8.7.
  `F` purchases a Frigate ship-family object with hull condition `99` and two
  skiffs aboard; `S` purchases a standalone Skiff unless a Frigate is already
  queued, in which case the Skiff is added to that Frigate's carried-skiff
  count. A second standalone Skiff
  before delivery is refused. Do not model shipwrights as an ordinary
  carried-item inventory menu.
- **Treasure, search, chest, and body results** can grant food, gold, torches, gems, ordinary or special keys, scrolls, potions, equipment, or story items.
- **Dungeon open-chest Get results** use the seven-row generator in
  `systems/containers.md`: food, gold, keys, gems, torches, one random potion
  subtype, and one random scroll subtype can each be awarded independently.
- **Scripted story events** grant unique items such as the moonstone, regalia, shards, plans, and boxes.

Equipment base prices are listed in the equipment item-id table above. The
resident price and stock tables are known to exist, arms equipment pricing has
decoded buy and sell formulas, and the shop system does not use
karma-modulated prices. For arms equipment, the shop stock, base price, display
name, and inventory counter rows share the same equipment item id. Non-equipment
service and commodity prices remain owned by the relevant shop/system specs.

## 11. Completion Boundaries

This catalog is complete at item-catalog depth. It identifies the inventory
families, carried counters or flags, equipment ids, shop/display names, price
and attack metadata, ready-slot classes, U-Use item families, scroll and potion
effects, quest-item flags, and live vehicle item boundaries needed by the
engine specs.

Do not use this catalog as a tile atlas or placement database. The compatible
pickup pipeline deliberately has two separate identities:

1. A gettable object visual, owned by `systems/containers.md` and
   `catalogs/tile-catalog.md`.
2. An inventory-add class code or subtype, owned by `systems/containers.md`,
   `systems/hidden-treasures.md`, and this item catalog.

The object tile that makes `G` Get legal is therefore not necessarily the same
byte that selects the item awarded. For example, the Sandalwood Box pickup is
accepted through the loose-object visual family, then awarded through the
Sandalwood Box inventory-add class. Implementations should preserve that
separation rather than deriving inventory identity from tile art.

Remaining cross-system work belongs to other specs, not to this catalog:

- Combat item restrictions are the shared combat attack-routing, range/effect,
  damage, ammunition, burden, and hand-occupancy contracts already referenced
  here and in `systems/combat.md`.
- Dialogue reactions to carried or worn story items are quest-graph
  branch-validation work.
- Vehicle motion, transport markers, ship hull/skiff state, and opaque
  transport/action bytes are owned by `systems/vehicles.md` and
  `formats/saved-gam.md`.
- Balloon art remains catalogued as art only; no live balloon boarding,
  purchase, transport marker, or movement path is promoted for the analyzed
  baseline.

## 12. Sources

This catalog is a cleanroom prose rewrite from the following source notes and safe local specs. It intentionally omits assembly, decompiled code, raw private offsets, and binary dumps.

- `u5-decomp/formats/data-ovl.md`
- `u5-decomp/formats/saves.md`
- `u5-decomp/functions/CMDS_OVL/`
- `u5-decomp/functions/SJOG_OVL/`
- `u5-decomp/functions/COMBAT_OVL/`
- `u5-decomp/functions/COMSUBS_OVL/`
- `u5-decomp/functions/TALK_OVL/`
- `u5-decomp/notes/tlk-quest-graph.md`
- `u5-decomp/notes/system-trace_inventory.md`
- `u5-decomp/functions/ULTIMA_EXE/`
- `u5-decomp/functions/CAST_OVL/_OVERVIEW.md`
- `u5-decomp/functions/CAST_OVL/`
- local CAST scroll subhandler analysis
- local CAST potion subhandler analysis
- `u5-decomp/functions/CAST2_OVL/`
- `u5-decomp/functions/CAST_OVL/`
- `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`
- `u5-decomp/functions/SJOG_OVL/`
- `u5-decomp/functions/TOWN_OVL/`
- `u5-decomp/functions/LOOKOBJ_OVL/`
- `u5-decomp/functions/DNGLOOK_OVL/`
- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md`
- `u5-decomp/functions/SHOPPES_OVL/`
- `u5-decomp/functions/SHOPPES2_OVL/`
- `u5-decomp/functions/SHOPPES3_OVL/`
- `u5-decomp/functions/COMBAT_OVL/`
- `u5-decomp/functions/ZSTATS_OVL/`
- `u5-decomp/notes/engine_idioms.md`
- `u5-decomp/functions/ULTIMA_EXE/`
- `u5-decomp/functions/ENDGAME_OVL/`
- `u5-decomp/functions/BLCKTHRN_OVL/`
- `u5-spec/systems/containers.md`
- `u5-spec/systems/hidden-treasures.md`
- `u5-spec/systems/conversation.md`
- `u5-spec/catalogs/spell-list.md`
- `u5-spec/catalogs/tile-catalog.md`
- `u5-spec/formats/saved-gam.md`
- `u5-spec/formats/ool.md`
- `u5-spec/systems/active-objects.md`
- `u5-spec/systems/doors-and-z-transitions.md`
- `u5-spec/systems/magic.md`
- `u5-spec/systems/overworld.md`
- `u5-spec/systems/save-load.md`
- `u5-spec/systems/shops.md`
- `u5-spec/systems/vehicles.md`

Combat U-Use correction: the combat parser routes `U` into the same item-use
handler the world modes use, so a family that refuses in an arena does so
through its own scene gate rather than because the command never arrives.
Source provenance: derived from private analysis note
`../u5-decomp/notes/oq-closures_2026-08-22_combat-encounter.md`.

Sextant, Spyglass and Pocket Watch correction (2026-08-23): the three-part
plane/scene/night gate on the Sextant and the Spyglass, the Underworld's
exclusion by the plane condition, the four Sextant outcomes and the
unconditional item label, the per-coordinate closing double-quote in the shared
formatter, and the Pocket Watch's minute field. Re-derived directly from the
shipped binaries, with `u5-decomp/functions/CAST_OVL/` used only to locate the
U-Use item dispatch. Two things a reader of the private notes should know: a
data-access table for that dispatch mis-attributes the minutes byte to the
coordinate formatter (the formatter never reads it), and this catalog follows
the binary rather than that note. The behaviour has **not** been confirmed in a
running game; a single live probe standing in the Underworld would raise the
Sextant claim from re-derived to observed.

A second, independent re-derivation on the same day confirmed all of the above
against the shipped binaries without relying on the private notes, and added the
newline the shared formatter emits *before* the coordinate pair, the threshold
form of the plane test, and the untraced presentation-helper calls that bracket
the coordinate line. It also confirmed the plane encoding from a second place
entirely - the map-loading path opens the Underworld map exactly when the outdoor
scene is combined with a non-surface plane value - which is direct evidence that
the state the Sextant refuses in is the Underworld.
