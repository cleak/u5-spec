# Item List

A reference catalog of the party inventory, equipment, reagents, quest items, and vehicles in Ultima V. This document is descriptive and table-driven; it does not specify the command dispatchers, shop menu loops, combat formulas, or save-file byte layout. Use this as the lookup table when implementing inventory display, shop stock, equipment selection, treasure results, reagent stock, and vehicle ownership.

## 1. Scope and confidence

This catalog covers things the player can carry, equip, buy, consume, find, or board:

- **Shared party inventory**: food, gold, keys, gems, torches, reagents, potions, scrolls, and story items.
- **Per-character equipment**: weapon, armour, helm, ring, amulet or neck item, and related ammunition.
- **Spell stock**: raw reagents and pre-mixed spell charges. The full spell list lives in `catalogs/spell-list.md`; this catalog treats spells only as inventory stock.
- **Vehicles**: horses, ships, skiffs, magic carpets, balloons, and special wish vehicles.

Confidence varies by field. Names and broad categories are high confidence because they come from resident name pools, inventory narration strings, save-image categories, and the Z-stats/equipment refusal strings. Behaviour is medium confidence for items with traced command handlers, such as reagents, keys, torches, gems, vehicles, and the major quest items. Numeric stats are mostly open: weapon damage, armour class, weight, strength thresholds, exact shop prices, item IDs, tile IDs, and per-class equipment compatibility have not been fully decoded into a clean catalog.

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
- Some equipment has a strength requirement.
- Some ring use path can destroy the ring after use or expiration.

R-Ready moves items between the carried equipment band and these six readied
slots. It lists only nonzero carried equipment counters that the selected
character does not already have readied, applies class/capability, occupied
slot, combat-armour, and hand-occupancy gates, then decrements the carried
counter only after an equip is accepted. Displaced equipment is returned to the
shared counter band through the inventory increment helper. The exact
intermediate swap timing and ring-vanish item list remain parity details; the
public flow lives in `systems/inventory.md`.

The active-object table is the third inventory-adjacent store. Vehicles and dropped objects exist as active objects while they are on the map. Boarding a vehicle moves the party into a vehicle state; exiting creates or restores an active-object vehicle on the map so it can be boarded later.

## 3. Category summary

| Category | Examples | Persistent form | Known sources | Main gaps |
|----------|----------|-----------------|---------------|-----------|
| Currency and provisions | Gold, food | Shared party counters | Treasure, shops, scripted rewards | Food carry cap and all treasure formulas |
| Tools and commodities | Keys, gems, torches, magic powder | Shared counters | Guild shops, treasure, scripted rewards | Exact caps and some use effects |
| Reagents | Sulfur Ash, Ginseng, Mandrake | Eight shared counters | Herbalists, treasure, harvesting | Per-vendor price table not transcribed |
| Spell charges | Forty-eight spell stocks | One counter per spell | M-Mix command | Some charge cap/refund details cross-system |
| Equipment | Weapons, armour, helms, shields, rings, amulets | Forty-eight item-id keyed counters plus character equipment slots | Arms shops, R-Ready, treasure, drops | Damage, armour value, weight, class restrictions, price |
| Scrolls and potions | Spell-code scrolls, colored potions | Shared counters or item slots | Treasure, shops or scripted finds | Exact use effects and item ordering |
| Quest and utility items | Moonstone, Crown, Sceptre, Shards | Shared flags/counters | Scripted finds and story events | Full use-item effect map |
| Vehicles | Horse, ship, skiff, magic carpet, balloon | Active-object records plus party transport state | Seed objects, brokers, special finds | Exact numeric marker subranges, terrain rules, and purchase prices |

## 4. Currency, tools, and commodities

| Item | Type | Known role | Gaps |
|------|------|------------|------|
| Gold | Currency | Shared party money. Shops debit it; treasure and reward paths credit it. | Exact treasure generation and all maximum-display rules. |
| Food | Provision | Shared food stock. Time/rest systems consume it; tavern and meal-counter flows are the confirmed shop-adjacent surface. | Food carry cap, per-meal/rest consumption, and any exact food-pricing path beyond tavern/meal flows. |
| Keys / Skull Keys | Tool | Used by lock and door interactions. Failed lockpicks can break a key. Guild shops sell key stock. | Exact split between ordinary keys, skull keys, and odd keys. |
| Odd Key | Quest/tool | Inventory narration distinguishes an odd key from ordinary keys. | Which lock or quest gate consumes it. |
| Gems | Tool | The command verb identifies a gem-view action; shops sell gems. | Exact map reveal radius, whether a gem is consumed, and mode restrictions. |
| Torches | Consumable light | Guild shops sell torches; the command dispatcher has an ignite-torch verb; lighting uses a torch timer. | Duration table and exact dungeon/town light radius. |
| Magic Powder | Consumable or quest stock | Save layout names a magic-powder counter. | Use action and source are not decoded. |
| Arrows | Ammunition | Required for bows. Equipment refusal text confirms ammunition gating. | Per-shot consumption and compatibility table. |
| Quarrels | Ammunition | Required for crossbows. | Per-shot consumption and compatibility table. |

## 5. Equipment

The equipment list below is the currently derivable master list. The row order is by family, not confirmed internal item ID. Names are canonical display names; some abbreviated inventory labels differ only to fit the Z-stats panel.

### 5.1 Armour, helms, and shields

| Item | Family | Known role | Gaps |
|------|--------|------------|------|
| Leather Helm | Helm | Head-slot armour. | Armour value, weight, price, class limits. |
| Spiked Helm | Helm | Head-slot armour. | Armour value, weight, price, class limits. |
| Chain Coif | Helm | Head-slot armour. | Armour value, weight, price, class limits. |
| Iron Helm | Helm | Head-slot armour. | Armour value, weight, price, class limits. |
| Small Shield | Shield | Off-hand defence item. | Defence value, hand rules, price. |
| Large Shield | Shield | Off-hand defence item. | Defence value, hand rules, price. |
| Spiked Shield | Shield | Off-hand defence item. | Defence value, hand rules, price. |
| Magic Shield | Shield | Magical shield. | Defence value, effect, price. |
| Jewel Shield | Shield | High-tier shield. | Defence value, effect, price. |
| Cloth Armour | Body armour | Body-slot armour. | Armour value, weight, price, class limits. |
| Leather Armour | Body armour | Body-slot armour. | Armour value, weight, price, class limits. |
| Ring Mail | Body armour | Body-slot armour. | Armour value, weight, price, class limits. |
| Scale Mail | Body armour | Body-slot armour. | Armour value, weight, price, class limits. |
| Chain Mail | Body armour | Body-slot armour. | Armour value, weight, price, class limits. |
| Plate Mail | Body armour | Heavy body armour. | Armour value, weight, price, class limits. |
| Mystic Armour | Body armour | Top-tier or magical body armour. | Armour value, effect, price, class limits. |

### 5.2 Weapons and ammunition

| Item | Family | Known role | Gaps |
|------|--------|------------|------|
| Flaming Oil | Thrown/consumable weapon | Listed with weapons; likely consumed when used. | Exact damage, range, and use mode. |
| Main Gauche | Weapon | Small blade or off-hand weapon. | Hand rule, damage, class limits. |
| Dagger | Weapon | Small blade. | Damage, range/throwability, class limits. |
| Throwing Axe | Weapon | Throwable axe. | Damage, range, quantity consumption. |
| Sling | Ranged weapon | Ammunition-using or stone-using ranged weapon. | Ammo rule and damage. |
| Club | Weapon | Simple melee weapon. | Damage and class limits. |
| Spear | Weapon | Pole weapon. | One- or two-handed rule, range, damage. |
| Mace | Weapon | Melee weapon. | Damage and class limits. |
| Bow | Ranged weapon | Uses arrows. | Damage, range, class limits. |
| Crossbow | Ranged weapon | Uses quarrels. | Damage, range, class limits. |
| Short Sword | Weapon | One-handed sword. | Damage and class limits. |
| Long Sword | Weapon | Sword. | Damage and hand rule. |
| Morning Star | Weapon | Heavy melee weapon. | Damage and class limits. |
| Sword of Chaos | Magical weapon | Named high-tier sword. | Effect, damage, price, and drawbacks. |
| Silver Sword | Weapon | Special sword, likely effective against specific enemies. | Exact enemy interactions. |
| Glass Sword | Weapon | Named weapon with special behaviour in Ultima tradition. | Whether it breaks or has a one-hit effect in U5. |
| Jeweled Sword | Weapon | High-tier sword. | Damage, price, and class limits. |
| Mystic Sword | Weapon | Top-tier or magical sword. | Damage, effect, price, and class limits. |
| 2H Hammer | Two-handed weapon | Requires both hands free. | Damage, weight, class limits. |
| 2H Axe | Two-handed weapon | Requires both hands free. | Damage, weight, class limits. |
| 2H Sword | Two-handed weapon | Requires both hands free. | Damage, weight, class limits. |
| Halberd | Two-handed weapon | Polearm. | Damage, reach, class limits. |
| Magic Bow | Magical ranged weapon | Ranged weapon, probably arrow-compatible. | Damage, ammo rule, effect. |
| Magic Axe | Magical weapon | Named axe. | Damage, range/throwability, effect. |
| Arrows | Ammunition | Used by bows. | Consumption and cap. |
| Quarrels | Ammunition | Used by crossbows. | Consumption and cap. |

### 5.3 Rings, amulets, and miscellaneous worn items

| Item | Family | Known role | Gaps |
|------|--------|------------|------|
| Ring of Invisibility | Ring | Magic ring; one ring may be worn at a time. | Duration, activation, vanishing rule. |
| Ring of Protection | Ring | Magic ring; one ring may be worn at a time. | Protection value, duration, vanishing rule. |
| Ring of Regeneration | Ring | Magic ring; one ring may be worn at a time. | Healing rate, duration, vanishing rule. |
| Amulet/Turning | Amulet | Neck-slot item; one amulet may be worn at a time. | Targeted enemy family and exact effect. |
| Spiked Collar | Neck item | Listed beside amulets; likely neck-slot equipment. | Whether it is equippable, cursed, or creature-specific. |
| Ankh | Miscellaneous holy item | Named in the item pool. | Whether it is carried, worn, or consumed by a ritual. |

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

`catalogs/spell-list.md` is the authoritative lookup for which spell uses which reagents. This catalog's contract is only that the eight reagents are inventory items, vendors sell some of them at fixed per-vendor prices, and mixing consumes their counters.

## 7. Scrolls and potions

The inventory narration and item-name pools identify scroll and potion families, but their use effects are not fully decoded.

### 7.1 Spell scrolls

Eight scroll labels are currently derivable by their compact spell-code labels:

| Scroll code | Cross-reference | Known status |
|-------------|-----------------|--------------|
| `LV` | Vas Lor / Great Light | Label identified; use effect not traced. |
| `HR` | Rel Hur / Wind Change | Label identified; use effect not traced. |
| `IS` | In Sanct / Protection | Label identified; use effect not traced. |
| `AI` | In An / Negate Magic | Label identified; use effect not traced. |
| `IQW` | In Quas Wis family | Label identified; exact scroll effect not traced. |
| `CKX` | Kal Xen Corp / Summon | Label identified; use effect not traced. |
| `CIM` | In Mani Corp / Resurrect | Label identified; use effect not traced. |
| `AT` | An Tym / Time Stop | Referenced spell effect is traced; scroll U-Use branch still not traced. |

The labels strongly suggest one-shot spell-scroll items. The U-Use Item handler is known to dispatch by item id, but the per-scroll branches have not been decoded into clean prose.

### 7.2 Potions

Potions are color-coded. The color vocabulary is:

| Color |
|-------|
| Blue |
| Yellow |
| Red |
| Green |
| Orange |
| Purple |
| Black |
| White |

The inventory narration composes a color with the potion noun. The exact effect table for each color is open.

## 8. Quest and utility items

These items are named by inventory strings, save-image categories, use-item dispatch, or story-specific notes. Where the exact use effect is not decoded, the table says so.

| Item | Known role | Gaps |
|------|------------|------|
| Moonstone | Story item tied to Blackthorn rescue/refuge handling and Gate Travel. Burying one records the current valid location into that stone's saved gate slot when outside dungeon/combat scenes and when the underfoot tile is `4..10`, `44`, or `45`; *Vas Rel Por* later teleports to the selected slot. Searching a matching buried coordinate surfaces a "strange rock" pickup, and collecting it grants the Moonstone and invalidates that slot. | Full acquisition path. |
| Magic Carpet | Both an inventory item and a vehicle/boarding target. Older notes conflated it with the outdoor climb gate, but the traced Klimb handler reads a separate unresolved gear byte. | Exact inventory flag, numeric marker variant, and terrain exceptions. |
| Sandalwood Box | Story item returned to Lord British in the endgame sequence. | Pickup flag and full prerequisite chain. |
| Plans for the HMS Cape | Named story item. | Full quest use and effect. |
| Crown of Lord British | Unique royal item; U-Use handler dispatches crown-family items. | Exact use effect and quest flags. |
| Sceptre of Lord British | Unique royal item; U-Use handler dispatches sceptre-family items. | Exact use effect and quest flags. |
| Amulet of Lord British | Unique royal item distinct from Amulet/Turning equipment. | Exact use effect and quest flags. |
| Shard of Falsehood | Shadowlord shard story item. | Acquisition, destruction, and effect flags. |
| Shard of Hatred | Shadowlord shard story item. | Acquisition, destruction, and effect flags. |
| Shard of Cowardice | Shadowlord shard story item. | Acquisition, destruction, and effect flags. |
| Spyglass | Named utility item. | Use effect not decoded. |
| Sextant | Named navigation item. | Whether it reports coordinates, time, or both is not traced here. |
| Pocket Watch | Named utility item. | Use effect not decoded. |
| Black Badge | Named story or faction item. | Use effect and quest gates not decoded. |
| Wooden Box | Named story item, distinct from the sandalwood box label. | Role and use effect not decoded. |
| Skull Keys | Named key-family stock. | Difference from ordinary keys and odd keys. |
| Odd Key | Key-family story item. | Matching lock or story gate. |
| Magic Powder | Save-backed inventory counter. | Use effect and source not decoded. |
| Ankh | Named item in the equipment/item pool. | Whether equipment, quest, or consumable. |

## 9. Vehicles

Vehicles straddle inventory and world state. A vehicle can be a map object, a shop purchase, a carried or owned item, and a current party state.

| Vehicle | Form | Known behaviour | Gaps |
|---------|------|-----------------|------|
| Horse | Active-object vehicle; Talk-entered stable purchase path | Boardable when available. Overland transport. | Full speed/terrain table and exact price table. |
| Ship | Active-object vehicle; ship-broker purchase path | Boardable; carries condition and skiff-count state; can fire broadsides; warns when badly damaged or without skiffs; sail state determines whether wind cadence applies. Shipwright Frigate purchases create a full-hull ship with two skiffs. | Purchase price table, repair rules, and exact compass/facing convention. |
| Skiff | Active-object vehicle; also ship-carried | Boardable; water transport; time system halves movement time for the skiff/raft timing state. | Exact terrain allowance and numeric marker subrange. |
| Magic Carpet | Inventory item and active vehicle | Boardable as a carpet. The current timing-tag cleanup no longer treats the `T` tag as proof of carpet identity; the outdoor Klimb gear gate is unresolved and should not be assumed to be this vehicle. | Exact numeric marker variant and all terrain restrictions. |
| Balloon | Vehicle tile family | Aerial vehicle in the tile and overworld catalogs. | Boarding, purchase/acquisition path, transport marker, and movement rules. |
| Corvette, Ferrari, Lamborghini, Lotus, Porsche | Wishing-well vehicle names | Easter-egg vehicle names in wishing-well strings. | Whether any creates durable transport or only maps to a horse/carpet branch. |

Vehicles are persisted through the active-object and save/load systems. Dismounting leaves a vehicle object on the map; loading restores the per-plane object tables through the `.OOL` companion files. Command-level boarding, exiting, and ship-fire behaviour lives in `systems/vehicles.md`. Outdoor Klimb separately requires an unresolved inventory/gear byte; current evidence does not identify that byte as the carpet.

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
- **Tavern and meal-counter flows** are the known shop-adjacent food/provision
  surface. Food remains a shared party counter consumed by time/rest systems,
  but no separate provision-shop trigger is present in the shipped `.NPC`
  shop-trigger range.
- **Horse traders** handle a Talk-entered vehicle sale that places a horse
  active object after payment. **Ship brokers** also have a Talk-entered
  shop-triggered sale flow; after payment, the next overworld entry places a
  watercraft active object at the sale coordinates. `F` purchases a Frigate
  ship-family object with full hull and two skiffs aboard; `S` purchases a
  standalone Skiff unless a Frigate is already queued, in which case the Skiff
  is added to that Frigate's carried-skiff count. A second standalone Skiff
  before delivery is refused. Do not model shipwrights as an ordinary
  carried-item inventory menu.
- **Treasure, search, chest, and body results** can grant food, gold, torches, gems, keys, scrolls, potions, equipment, or story items.
- **Scripted story events** grant unique items such as the moonstone, regalia, shards, plans, and boxes.

Prices are intentionally not listed in this catalog. The resident price and stock tables are known to exist, arms equipment pricing has decoded buy and sell formulas, and the shop system does not use karma-modulated prices. For arms equipment, the shop stock, base price, display name, and inventory counter rows share the same equipment item id.

## 11. Completion and gaps

**Complete enough for display.** The catalog identifies the broad inventory families and the currently derivable item names for equipment, reagents, potions, scroll labels, quest items, commodities, and vehicles.

**Not complete enough for mechanics.** The following fields remain open and should not be guessed by an implementation seeking original-compatible balance:

1. Item-to-tile IDs outside the arms-shop equipment id mapping.
2. Weapon damage, hit chance, range, breakage, and ammo consumption.
3. Armour/shield defence values and weight.
4. Exact equipment class-restriction table values and strength/capability
   thresholds.
5. Exact prices per shop, reagent, treatment, tavern/meal, horse, and ship.
6. Potion color effects.
7. Scroll use effects and whether scrolls are consumed on use.
8. Full U-Use Item dispatch for Crown, Sceptre, Amulet, keys, tools, and quest boxes; Moonstone gate-slot writes and Search/Get recovery are known, but its acquisition path remains open.
9. Exact transport-marker numeric subranges and terrain rules for horse, ship, skiff, carpet, and balloon.
10. Caps for most byte counters beyond the confirmed spell-charge cap.

## 12. Sources

This catalog is a cleanroom prose rewrite from the following source notes and safe local specs. It intentionally omits assembly, decompiled code, raw private offsets, and binary dumps.

- `u5-decomp/formats/data-ovl.md`
- `u5-decomp/formats/saves.md`
- `u5-decomp/functions/CMDS_OVL/0x1AD8_cmds_mix_reagents.md`
- `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`
- `u5-decomp/functions/CMDS_OVL/0x1C20_cmds_klimb.md`
- `u5-decomp/functions/CAST_OVL/_OVERVIEW.md`
- local CAST Moonstone helper analysis
- `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`
- `u5-decomp/functions/SJOG_OVL/0x095C_sjog_search.md`
- `u5-decomp/functions/SJOG_OVL/0x18CE_sjog_get.md`
- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md`
- `u5-decomp/functions/SHOPPES_OVL/0x12B2_arms_main.md`
- `u5-decomp/functions/ENDGAME_OVL/0x0648_endgame_entry.md`
- `u5-decomp/functions/BLCKTHRN_OVL/0x0910_blackthorn_rescue.md`
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
