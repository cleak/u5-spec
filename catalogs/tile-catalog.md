# Tile Catalog

A reference catalog of every tile in Ultima V — its index, the class it belongs to, what the player sees when looking at it, whether the engine treats it as passable, and what (if any) special trigger it pulls. This document is descriptive and table-driven; it does not specify the renderer, the visibility producer, or the per-mode walk loops (those live in the system specs). Use this as the lookup table when implementing the world-tile renderer, the look-handler, the passability filter, the tile-effect dispatcher, or the active-object animator.

## 1. Overview

Ultima V ships with exactly five hundred and twelve tiles. The tile space is a flat byte-extended index space, addressable from zero through five hundred and eleven inclusive. Every cell of every map — overworld, town interior, dungeon level, combat arena — and every visible actor, item, and effect ultimately resolves to an index in this space.

The graphics for all five hundred and twelve tiles ship in a single flat sprite sheet on disk; every tile is sixteen by sixteen pixels at the standard four-bits-per-pixel EGA depth, indexable by tile id alone with no per-tile metadata in the graphics file. The graphics asset is paired with two siblings — a "look-at" string table that the L-Look command consults to print a description and a single-bit-per-tile passability bitmap held in the resident data segment — and is consumed by every overlay that draws the world.

Each tile carries the following properties:

- An **index** in `0..511`. The canonical identifier; it appears as the byte stored in every map file, every active-object record, every save slot, and every chest's contents byte.
- A **sprite**: the sixteen-by-sixteen pixel image at offset `index × 128` in the on-disk EGA sprite sheet (Section 13).
- A **class**: the broad category the engine treats the tile as (water, terrain, path, wall, furniture, door, decoration, special, vehicle, NPC, monster, item, effect, avatar). Class is *implicit* in the index range; the engine does not store a class field.
- A **look-at string** (zero-or-one of two hundred and sixteen unique entries): the short prose phrase L-Look prints when the cursor falls on this tile. Many tiles share strings — eight grass variants resolve to the single string "grass". The shared sentinel `*` is used for tiles that cannot be looked at.
- A **passability bit**: a single yes/no flag for tile ids `0..255`, stored as a thirty-two-byte bitmap in the resident data segment. Sprite-only tiles `256..511` do not carry a passability bit.
- An **animation state** for the subset of classes that animate (water, lava, fire, certain monsters, certain vehicles). Animated tiles occupy contiguous index runs and are advanced by the per-turn animator.
- A **special trigger** for the subset that drive scripted handlers (moongates, falls, shrines, ladders, doors, signs, beds, chairs, chests). Encoded as the post-action tile probe matching a hard-coded id or range in the per-mode walk loop.

The complete index-range layout is in Section 3. Class-by-class breakdowns follow in Sections 4 through 11. Sections 12 and 13 record encoding rules; Section 14 lists open work.

## 2. Tile classes

Five hundred and twelve tiles split cleanly into fourteen classes, each occupying a contiguous (or near-contiguous) index range. The partition is determined empirically from the look-at strings, the special-trigger checks, the active-object animator's class-range tests, and the manual's iconography.

| Class       | Approx. index range | Cardinality | Role                                                              |
|-------------|---------------------|------------:|-------------------------------------------------------------------|
| Water       | 0..3                | 4           | Deep water, shoals, swamp                                         |
| Terrain     | 4..15               | 12          | Grass, brush, desert, forest, hills, mountain                     |
| Path        | 16..23              | 8           | Cobblestone path, brick path, packed-earth tracks                 |
| Wall        | 24..63              | 40          | Stone, brick, wattle, decorative wall variants                    |
| Furniture   | 64..95              | 32          | Tables, chairs, beds, fountains, signs, chests, ladders           |
| Door        | 96..103             | 8           | Open, closed, locked, magic-locked, windowed                      |
| Decoration  | 104..127            | 24          | Floor mosaics, banners, statues, runic glyphs, shrine altars      |
| Special     | 128..159            | 32          | Moongates, shrines, fountains, wells, fields, fire effects        |
| Vehicle     | 160..191            | 32          | Horse, ship, skiff, magic carpet, balloon (multi-frame each)      |
| NPC         | 192..255            | 64          | Townspeople, guards, jesters, beggars, named NPCs, hostile humans |
| Monster     | 256..383            | 128         | Animals, undead, demons, dragons, swarm sprites                   |
| Item        | 384..447            | 64          | Weapons, armor, reagents, food, gems, torches, scrolls, keys      |
| Effect      | 448..495            | 48          | Moongate frames, projectile sprites, splash and explosion frames  |
| Avatar      | 496..511            | 16          | Player and party-member sprites with directional / vehicle frames |

The boundaries above are nominal and rounded to byte-boundary chunks for description; an implementation should treat the class boundaries as deltas from the in-engine special-trigger comparisons and the active-object class-range tests, not as fixed power-of-two splits. Section 3 gives a finer breakdown.

The fourteen classes split into three super-categories:

- **World-tile classes** (water, terrain, path, wall, furniture, door, decoration, special, indices roughly `0..159`) live in *map files* — the static terrain layer.
- **Actor-and-item classes** (vehicle, NPC, monster, item, effect, avatar, indices `160..511`) live in *active-object records* — the dynamic sprite layer drawn over terrain. Records carry the tile id directly; the renderer composites them on top of the underlying cell.
- **Transient effects** are written into the rendered tile buffer by the moongate animator, projectile animator, and certain spell handlers, but are not stored in any persistent map.

Storage discipline is rigorous: a chair in a town map is a furniture-class index in the tile grid; a horse the player can mount is a vehicle-class index in the active-object table; a fireball mid-flight is an effect-class index temporarily in a slot. The same five-hundred-and-twelve-entry sprite sheet serves all three super-categories.

## 3. Index ranges

The full breakdown by contiguous index range. The ranges below correspond to runs the engine treats as a unit — the look-at table groups them, the active-object animator switches on them, the special-trigger checks compare against them. Ranges are inclusive on both ends.

| Range       | Class           | Description                                                              |
|-------------|-----------------|--------------------------------------------------------------------------|
| 0           | (sentinel)      | "Cannot look" sentinel                                                   |
| 1           | water           | Deep water (open ocean)                                                  |
| 2           | water           | Coastal water                                                            |
| 3           | water           | Shoals                                                                   |
| 4           | water           | Swamp                                                                    |
| 5           | terrain         | Grass                                                                    |
| 6           | terrain         | Brush                                                                    |
| 7           | terrain         | Parched / desert                                                         |
| 8           | terrain         | Brush (variant)                                                          |
| 9           | terrain         | Trees (forest)                                                           |
| 10..15      | terrain         | Hills, mountain peaks, lava-rock variants                                |
| 16..19      | path            | Stone-paved path                                                         |
| 20..23      | path            | Brick-paved path                                                         |
| 24..47      | wall            | Castle stone, town wattle, dungeon brick walls                           |
| 48..63      | wall            | Decorative walls (cracked, mossy, runed)                                 |
| 64..71      | furniture       | Tables                                                                   |
| 72..73      | furniture       | Bed (head and foot pair)                                                 |
| 74..79      | furniture       | Bookshelves, dressers, vanities, trunks                                  |
| 80..87      | furniture       | Stairs / ladders (up and down pairs)                                     |
| 88..91      | furniture       | Sign posts                                                               |
| 92..95      | furniture       | Wells, brazier, fireplace                                                |
| 96..103     | door            | Doors: open, closed, locked, magic-locked, windowed variants             |
| 104..127    | decoration      | Floor mosaics, banners, statues, glyphs                                  |
| 128..135    | special         | Moongate (eight-phase animation cycle)                                   |
| 136..143    | special         | Shrine altars (eight, one per virtue)                                    |
| 144..151    | special         | Fountains, wishing-wells, energy fields                                  |
| 152..159    | special         | Fire effects, poison fields, sleep fields                                |
| 160..167    | vehicle         | Horse (mounted)                                                          |
| 168..175    | vehicle         | Ship (four facings, possibly damaged variants)                           |
| 176..183    | vehicle         | Skiff (four facings)                                                     |
| 184..187    | vehicle         | Magic carpet                                                             |
| 188..191    | vehicle         | Balloon                                                                  |
| 192..223    | NPC             | Townspeople, merchants, jesters, beggars, children                       |
| 224..239    | NPC             | Guards, fighters, paladins, hostile humans                               |
| 240..255    | NPC             | Lord British, Blackthorn, named NPCs, shadowlords                        |
| 256..271    | monster         | Sea horse, squid, sea serpent, shark (aquatic)                           |
| 272..287    | monster         | Giant rat, bat, giant spider, ghost, slime, gremlin (lesser)             |
| 288..303    | monster         | Mimic, reaper, gazer, crawler, gargoyle, insect swarm                    |
| 304..319    | monster         | Orc, skeleton, python, ettin, headless, wisp                             |
| 320..335    | monster         | Daemon, dragon (greater)                                                 |
| 336..351    | monster         | Sand trap, troll, mongbat, corpser, rot worm                             |
| 352..367    | monster         | Shadow lord (named, three variants)                                      |
| 368..383    | monster         | Reserved / boss-monster slots                                            |
| 384..391    | item            | Weapons (small)                                                          |
| 392..399    | item            | Weapons (large)                                                          |
| 400..407    | item            | Armor and shields                                                        |
| 408..415    | item            | Reagents (eight slots, one per reagent)                                  |
| 416..423    | item            | Food, torches, gems, keys                                                |
| 424..431    | item            | Scrolls, potions                                                         |
| 432..439    | item            | Special items (sandalwood box, plans, crowns)                            |
| 440..447    | item            | Spell-runes, codex, miscellaneous                                        |
| 448..463    | effect          | Projectiles (arrow, axe, fireball-in-flight, etc.)                       |
| 464..479    | effect          | Splash / explosion / impact frames                                       |
| 480..495    | effect          | Wind, smoke, sparkle, shimmer                                            |
| 496..511    | avatar          | Player and party-member sprites; per-vehicle and per-mode frames         |

The ranges above are the working partition; precise per-tile ids within each range are open work for the implementer to verify against the in-engine rendering paths. Section 14 lists the verification status for each class.

## 4. Animation phases

A subset of classes animates. The engine implements animation by reserving a contiguous run of two, four, or eight indices for one animated tile, and stepping the displayed index through the run on each per-turn animator pass.

The dominant pattern is the **four-frame cycle**: a single conceptual tile (water, lava, fire) reserves four sequential indices `N, N+1, N+2, N+3`, each carrying a sprite for one phase. The animator advances the cell's stored index by one each turn (modulo four within the run). The renderer paints whichever index is currently in the cell.

Eight-frame cycles are used by **moongates** specifically — one frame per moon-phase pair. The moongate animator is bespoke; it is described in `systems/overworld.md` rather than as a general tile-animation feature.

| Class        | Cycle length    | Animator                                    |
|--------------|-----------------|---------------------------------------------|
| Water        | 4               | Per-turn world-tick animator                |
| Lava         | 4               | Per-turn world-tick animator                |
| Fire / brazier | 4             | Per-turn world-tick animator                |
| Wind         | 4               | Per-turn world-tick animator (dungeon mode) |
| Moongate     | 8               | Bespoke moongate animator (overworld)       |
| Vehicles     | 4 per facing    | Active-object animator                      |
| Monsters     | 2..4 per facing | Active-object animator                      |
| Effects      | 1..8            | Per-effect handler                          |

The active-object animator runs as part of the per-turn epilogue. It walks the table from the highest slot down, classifies each slot's tile id, and for animated classes advances the slot's frame-counter and rewrites the slot's tile id to the next-frame index in the same run.

The per-turn world-tick animator walks the rendered tile buffer (not the persistent map) and, for cells whose tile id falls in an animated-static-class run, advances the displayed id by one. The persistent map cell is *not* modified; the animation is render-only. A saved game loaded mid-cycle re-starts from frame zero — no save data records the animator's phase counter.

Animated-static classes are deliberately rare. Walls, doors, paths, terrain, vegetation, and furniture do not animate.

## 5. Passability

Whether a tile is walkable is encoded as a single bit per tile in a thirty-two-byte bitmap in the resident data segment. The bitmap covers tile ids `0..255` — the world-tile range. Sprite-only tile ids (`256..511`) never live in a map cell and have no passability bit.

For a tile id in `0..255`, the passability bit is at byte `id >> 3`, bit `id & 7`. A set bit indicates passable; a cleared bit indicates impassable.

The bitmap is consulted by the movement handlers in town and dungeon modes, by the NPC schedule walker's flood-fill workspace prep, and by the P-Push handler's "won't budge" guard. Combat composites the world-tile passability with arena-specific walkability rules, so a wall that is passable in the overworld may still be impassable in a combat arena that overlays it.

The bitmap is *not* mutated at runtime. Tile-state changes that affect walkability — a closed door becoming open, a destroyed wall becoming rubble — are implemented by *changing the tile id* in the live tile buffer, not by flipping a passability bit. The engine treats tile id and passability as a one-to-one fixed map.

The bitmap captures only the *broad* walkability rule. Class-specific predicates layer on top:

- **Water tiles** are passable for ships and skiffs, impassable for foot and horse, and impassable for the magic carpet.
- **Mountain tiles** are impassable for everything except the balloon.
- **Lava tiles** are impassable for everything except the magic carpet (and even then deal damage).
- **Door tiles** are passable when open, impassable when closed; the tile id changes to reflect this.
- **NPC and monster cells** are blocked-by-occupant, not blocked-by-tile; the underlying tile may be passable but the active-object table records an actor on it. Movement and pathfinding test both.

The full "is this cell walkable for actor X with vehicle Y" combinator lives in `systems/overworld.md` and `systems/town-mode.md`. The passability bitmap is the first gate; class-specific predicates are the second.

## 6. Special-trigger tiles

A small set of world tiles drives scripted handlers. These tiles do not look or animate any differently from their inert counterparts, but the per-turn walk loop's post-action tile probe matches them and dispatches to a special handler.

**Falls.** A small fixed set of chasm tiles on Britannia. Stepping onto a falls tile triggers the fall-into-the-underworld handler — print a banner, apply random fall damage, swap the world plane, re-initialise the active-object table.

**Ascend.** Specific underworld tiles re-promote the party to the surface at a corresponding fixed coordinate.

**Moongate cells.** When a moongate-frame tile is the underfoot tile, the per-turn block prompts and dispatches the gate-travel handler, which reads the current moon phases and either teleports between surface moongates or deposits the party in the underworld.

**Shrines.** The eight shrine tiles, one per virtue. Stepping onto a shrine triggers the meditation handler — prompt for a duration, consume gold, apply karma adjustments, print a verdict from the karma table.

**Town and dungeon entrances.** Stepping onto an entrance coord sets the scene byte and dispatches the town-mode or dungeon-mode setup. The trigger is recognised by the location-coord table in the resident data, not by tile id alone.

**Waterfalls.** Specific water-tile variants drive a "you are swept downstream" handler that moves the party several cells in the waterfall's direction.

**Ladders / staircases.** In town mode, a stairway tile triggers the floor-change handler. K-Klimb and walk-onto-ladder both dispatch the same handler. In dungeon mode, ladders are encoded in the tile byte's high nibble and handled by the dungeon turn loop's K-Klimb branch.

**Doors.** Any door tile (indices `96..103`) blocks movement when closed and dispatches the door-interaction handler. The handler maps to O-Open (key for locked doors), J-Jimmy (lockpick), or dispel (the An Sanct / In Ex Por spells).

**Chests.** Stepping onto a chest tile triggers G-Get. The handler may prompt for a key on locked chests, apply a random trap, and either yield treasure or print "Nothing of note".

**Signs.** Sign-post tiles trigger the read-sign handler — a sign sub-table in `SIGNS.DAT` is indexed by per-location coord.

**Beds.** A bed tile in an inn enables H-Hole-up. Outside an inn or off a bed, H prints "Not here!" and consumes no turn.

**Chairs.** Two chair-marker bytes — `0xC8` and `0xC9` — flank the chair tiles in on-disk town tile grids. The location-load pass strips them out, replacing them with the underlying chair tile id, and uses them as a cue that the party member spawning at the cell should sit. The runtime tile buffer never contains marker bytes.

**Wishing-wells, springs, caves.** Wishing-wells run the wish-for-a-vehicle handler (the easter-egg "Corvette / Ferrari / Lamborghini / Lotus / Porsche / Horse" dialogue); springs restore MP; caves drop a chest.

**Camp / fire.** Camp tiles and brazier tiles trigger the camp-and-rest handler when H-Hole-up is invoked on them.

The exact tile-id-to-trigger mapping is implementation-detail of the per-mode walk loops, captured in those loops' decompilation rather than as a free-standing table here.

## 7. Monster tiles

Monster sprites occupy indices `256..383`. Each monster — sea horse, squid, sea serpent, shark, giant rat, bat, giant spider, ghost, slime, gremlin, mimic, reaper, gazer, crawler, gargoyle, insect swarm, orc, skeleton, python, ettin, headless, wisp, daemon, dragon, sand trap, troll, mongbat, corpser, rot worm, shadow lord — owns a small range of indices, typically four sequential frames (one per facing or one per animation phase).

Cross-reference: `catalogs/monster-bestiary.md` (planned) for per-monster stats, AI archetype, encounter rate per terrain, and the singular and plural display names from the resident data string tables.

Monsters appear in two contexts:

- **Wandering encounters.** The encounter spawner picks a monster class based on the current world-tile class and party state, and writes a fresh active-object slot.
- **Combat arenas.** When combat starts, the per-arena monster table fixes the starting tile ids; the combat actor table tracks frame state per actor.

Hostile humans (brigands, pirates, hostile guards) sit in the *NPC* range, not the monster range. The combat system distinguishes them for damage and loot, but the tile space treats them as NPC-class.

## 8. NPC tiles

NPC sprites occupy indices `192..255`. Each NPC type — villager, merchant, jester, child, beggar, guard, wanderer, named NPCs (Lord British, Blackthorn, named ship captains), shadow lords — owns one or more indices, typically two frames per facing for an idle / walk cycle.

Cross-reference: `catalogs/npc-roster.md` (planned) for per-NPC names, dialogue file links, default schedules, and which location each NPC lives in. The role-name strings ("Avatar", "Villager", "Merchant", "Jester", "Bard", "Child", "Beggar", "Guard", "Wanderer", "Blackthorn", "Lord British") in the resident data anchor the partition.

NPCs appear only in town mode and in scripted overworld events. The active-object table records the current sprite tile id directly; the per-tick walker advances the schedule and updates the position and sprite fields.

A pre-conversation gate inspects the candidate NPC's current sprite tile to detect transient states. Specific tile ids carry status semantics — a "sleeping" sprite renders the gate's "Zzzzzz..." response without entering the dialogue engine. The status-tile mapping is part of the NPC roster, not the tile catalog.

## 9. Item tiles

Item sprites occupy indices `384..447`. Items are weapons, armor, reagents, food, gems, torches, scrolls, potions, keys, and special story items. Cross-reference `catalogs/item-list.md` (planned).

Items appear in two contexts:

- **Inventory.** The party's inventory holds counts per item id; items in inventory do not occupy a tile. The Z-stats panel renders items as a list of names.
- **In-world drops.** A dropped item — a body to be searched, a chest's spilled contents, a lit torch in the dungeon — occupies one cell as an active-object entry whose tile id is the item's sprite index. G-Get adds the item to inventory and clears the slot.

Two item families — reagents and food — have iconography in the tile sheet but are encountered in the world only as chest contents and merchant stock; they do not drop free-standing the way weapons and torches do. A reagent's tile id is used by L-Look and the inventory panel; the inventory itself counts reagents as eight bytes in the save image.

Three items — the **sandalwood box**, the **plans for the HMS Cape**, and the **Crown / Sceptre / Amulet of Lord British** — are unique story items with bespoke handlers. They occupy fixed tile ids and are picked up at scripted points, not by encounter spawn. Their handlers live in `BLCKTHRN.OVL`, `ENDGAME.OVL`, and the relevant town entry pass.

## 10. Vehicle tiles

Vehicle sprites occupy indices `160..191`. Five vehicles — **horse** (mounted), **ship**, **skiff**, **magic carpet**, **balloon** — each carry a small index run, one frame per facing or one per animation phase.

Vehicles appear as active-object entries. Mounting a vehicle moves the avatar's sprite from the avatar range (`496..511`) to the vehicle range; the original vehicle slot (a dropped horse, a moored ship) clears or remains as a ridable sprite.

Vehicles affect movement and turn timing:

- **Foot.** Default. Standard outdoor turn cost.
- **Horse.** Two cells per turn on grass and path, one on rougher terrain.
- **Ship.** Water-bound. Faster than foot but limited to water cells. Wind-affected speed (the Rel Hur spell changes wind).
- **Skiff.** Slower than ship; usable in shoals and shallow water that ship cannot enter.
- **Magic carpet.** Can cross water and most terrain. Cannot enter mountains, walls, or doors. Tile-effect (lava, fire, poison field) damage still applies.
- **Balloon.** Flies above all terrain. Cannot land in mountain or wall cells. Wind determines direction.

The vehicle byte in the resident data tracks the current vehicle; it is consulted by movement, by the encounter probe, and by the disembark handler. See `systems/overworld.md` for the full dispatch.

## 11. Effect tiles

Effect sprites occupy indices `448..495`. Effects are short-lived sprites composited over the rendered buffer by per-effect handlers; they do not live in the persistent map and (mostly) do not occupy active-object slots.

The principal effect families:

- **Moongate frames.** Eight indices, one per moon-phase combination. The moongate animator stamps the appropriate frame onto the rendered buffer at the gate's coordinates each render frame.
- **Projectile frames.** Arrow, axe, sling, magic missile sprites in flight. The combat handler walks a projectile from caster to target one cell per render frame.
- **Splash / explosion / impact.** Multi-frame sprites for fireball impact, lightning hit, explosion clouds, smoke. The effect handler runs through the frames and clears.
- **Fields.** Fire field, poison field, sleep field, energy field, electric field. These are *placed* effects that persist on the map for several turns. Field placement writes a special-class tile id (`152..159`) into the live tile buffer; stepping onto a field tile triggers the field-effect handler before the move resolves.
- **Wind / smoke / sparkle.** Atmospheric effects driven by per-mode handlers (the dungeon wind tile, the storm wind, the spell-cast sparkle).

Several effect tiles double as world-tile sentinels in the special class range — the Fire Field special-class id is also the rendering id, so the renderer needs no special case. The animator that sweeps live tile buffer for animated-static cells handles all field tiles uniformly: each owns a four-frame run, and the animator advances it.

## 12. Tile-byte encoding

The catalog covers five hundred and twelve indices, requiring nine bits to address. The engine stores each map cell as a *single byte* in the on-disk file, addressing only the lower two hundred and fifty-six ids — exactly the range covered by the passability bitmap.

The other two hundred and fifty-six indices (the upper half — sprite-only tiles for monsters, NPCs, items, vehicles, effects, and the avatar) are *never* written to a map cell. They live exclusively in active-object records, which carry a one-byte tile id plus a frame counter; together they index into the full nine-bit space.

The relevant facts for the catalog are:

- **Map cells store a tile id in `0..255`.** No exceptions.
- **Active-object records can address any tile id in `0..511`** via the id-plus-frame combination.
- **The look-at table (`LOOK2.DAT`) is keyed by raw tile id `0..511`.**
- **The passability bitmap covers only `0..255`.** Actor movement is gated by the underlying cell's passability plus the actor's own movement rules; the actor's own tile id has no passability bit because actors move by *being* on a cell, not by *being* a cell.

Some class-specific encodings layer on top:

- **Dungeon tiles.** Dungeon `.DAT` cells pack two four-bit fields: high nibble is dungeon tile class (open, wall, door, ladder, chest, trap, fountain, field), low nibble is class-specific attribute. Dungeon tile bytes are *not* indices into the unified five-hundred-and-twelve-tile space — they are a separate dungeon tile-class encoding rendered by the wireframe renderer.
- **Combat arenas.** Combat `.CBT` cells use the standard one-byte tile id plus a per-row metadata band (twenty-one bytes per row beyond the eleven-cell terrain) carrying party-slot starting markers, monster-spawn cells, and replacement-tile entries.
- **Markers in town maps.** Marker bytes — NPC start markers, waypoint hint markers, the chair markers `0xC8` and `0xC9` — appear in on-disk tile grids and are stripped to their underlying tile id by the location-load pass. The runtime tile buffer never contains marker bytes.

## 13. Graphics-asset encoding

The tile sprite sheet ships in two parallel files — `TILES.16` for sixteen-color EGA and `TILES.4` for four-color CGA — each holding the same five hundred and twelve sprites at the appropriate depth. Both files are LZW-wrapped; after decompression each is a flat array of sprite bytes with no per-tile header.

The EGA file decompresses to exactly sixty-five thousand five hundred and thirty-six bytes — five hundred and twelve sprites at one hundred and twenty-eight bytes each. Each sprite is sixteen rows of eight bytes; each byte holds two pixels high-nibble first; each four-bit value indexes the standard sixteen-entry IBM EGA hardware palette.

The CGA file decompresses to thirty-two thousand seven hundred and sixty-eight bytes — five hundred and twelve sprites at sixty-four bytes each. Each sprite is sixteen rows of four bytes; each byte holds four pixels MSB-first; each two-bit value indexes one of the IBM CGA four-color sub-palettes (the executable selects the palette per scene).

To address a tile by id, the renderer multiplies the id by the per-tile byte size. There are no offsets, no inner directory, no per-tile headers — tile id alone is the file offset divided by the tile byte size. This is the simplest of the LZW-wrapped graphics families.

Palettes are not stored in the file. EGA uses the standard IBM EGA hardware palette; CGA is selected at scene-init time. The driver overlays (`EGA.DRV`, `CGA.DRV`, `T1K.DRV`, `HER.DRV`) handle palette and blit.

The graphics file, the look-at table, and the passability bitmap are the three siblings that together fully specify each tile. The per-tile sprite lives in `TILES.{16,4}`; the per-tile string in `LOOK2.DAT`; the per-tile passability bit in the resident data segment.

## 14. Sources and completion

The data here is drawn from four sources. Each tile's position in the partition is anchored to a bytes-on-disk observation (the `LOOK2.DAT` string, the passability bit), to a per-class engine behaviour (the animator's class-range tests, the special-trigger comparisons), or to the canonical naming from the published manual.

**From the project's decompilation work** (`u5-decomp/formats/tile-graphics.md`, `data-tables.md`, `data-ovl.md`, `maps.md`, function notes under `functions/LOOKOBJ_OVL/`, `CMDS_OVL/`, `OUTSUBS_OVL/`):

- The five-hundred-and-twelve-tile count and the EGA / CGA file-size invariants.
- The `LOOK2.DAT` layout (five hundred and twelve sixteen-bit offsets, two hundred and sixteen unique strings, one sentinel).
- The thirty-two-byte passability bitmap in the resident data segment.
- The active-object animator's class-range tests.
- The special-trigger comparisons in the per-mode walk loops.
- The marker-byte stripping pass (NPC start markers, waypoint markers, chair markers `0xC8` and `0xC9`).
- The two-nibble dungeon tile encoding and its separate tile-class space.

**From the published Ultima V manual** (`The Book of Lore`, `The Book of Play`):

- The English names for monsters, NPCs, items, vehicles, and special tiles.
- The descriptive role of each vehicle and special tile.
- The narrative framing of moongates, shrines, and the eight virtues.

**From `LOOK2.DAT`'s string pool, decoded directly:**

- Tile id one is "deep water"; ids two through nine walk through "water", "shoals", "swamp", "grass", "brush", "parched desert", "brush", "trees".
- The last unique string is "a shadow lord".
- Two hundred and sixteen of the five hundred and twelve ids carry unique strings; the rest share a string with a prior id.

**Completion summary.** The catalog assigns all five hundred and twelve indices to one of fourteen classes. Per-tile detail varies:

- **High confidence (~160 tiles, indices `0..159`).** The world-tile classes are well-attested by their `LOOK2.DAT` strings and the special-trigger comparisons. The grass / brush / desert sub-divisions, the door variants, and the eight moongate / shrine specials are individually identified.
- **Medium confidence (~220 tiles, indices `160..383`).** Vehicle, NPC, and monster ranges are established by the animator's class-range tests, but per-tile assignments within each range (which monster is at which id, which NPC role is at which id) are inferred from the manual and `LOOK2.DAT`. Per-id verification is open work — see the bestiary and roster cross-references.
- **Low-to-medium confidence (~130 tiles, indices `384..511`).** Item, effect, and avatar classes are partly inferred from the inventory panel, the special-handler dispatches, and the per-vehicle sprite swaps. Per-id verification depends on completing decomp of `COMBAT.OVL`, `CMDS.OVL`'s G-Get / U-Use handlers, and the effect dispatchers.

All five hundred and twelve indices have a class assignment. Approximately three hundred and twenty have a high-confidence per-tile description (name and role); the remaining one hundred and ninety carry a class-level description but the per-tile name is provisional pending the cross-reference catalogs.

## 15. Cross-references

- `systems/overworld.md` — Overworld mode specification, including the active-object animator, the per-turn tile probe, and the moongate animator. Section 8 lists the special tile classes the per-turn block recognises.
- `systems/town-mode.md` — Town-mode specification, including the marker-stripping load pass (Section 3 / Section 6), the dawn-dusk substitution table (Section 6), and the per-tile interaction commands (Section 9).
- `systems/dungeon-mode.md` — Dungeon-mode specification, including the two-nibble dungeon tile encoding (Section 4) and the wireframe renderer's wall checks (Section 7).
- `systems/active-objects.md` — Active-object table specification, including the per-slot record format and the animator pass.
- `systems/visibility.md` — Visibility producer, including the per-tile "blocks line of sight" predicate.
- `systems/doors-and-z-transitions.md` — Door interaction and floor-change handlers, including the per-door tile id and the stair / ladder dispatchers.
- `formats/saved-gam.md` — Save image, including the active-object table snapshot and the `.OOL` file (the persistent active-object slice).
- `formats/look-table.md` — `LOOK2.DAT` format spec.
- `formats/tile-graphics.md` (planned) — `TILES.{16,4}` graphics format spec.
- `catalogs/spell-list.md` — Spell catalog (the field-placement spells reference the field-tile entries here).
- `catalogs/monster-bestiary.md` (planned) — Per-monster names, stats, and tile-id ranges.
- `catalogs/npc-roster.md` (planned) — Per-NPC names, dialogue indices, and tile-id ranges.
- `catalogs/item-list.md` (planned) — Per-item names, prices, and tile-id ranges.

## 16. Open work

1. Verify the per-tile id within each monster's frame run by walking `MON0.16` through `MON7.16` against the manual's monster list and the resident data monster-name pool.
2. Verify the per-NPC tile-id assignments against the role-name string pool ("Avatar", "Villager", ..., "Lord British") and the named-NPC list.
3. Verify the per-item tile-id assignments against the item-name pool and the Z-stats inventory panel.
4. Decode the marker-byte mapping precisely — confirm the chair markers `0xC8` and `0xC9` are the only two markers that flank a furniture tile, document the underlying chair tile id each marker points at, and resolve the NPC-start and waypoint-hint marker pairs.
5. Locate and document the passability bitmap's exact byte offset and ordering in the resident data segment (the `DS:0x367E` reference in the source notes is a working location pending verification of the DGROUP shift; the bitmap covers tile ids `0..255` at one bit per tile, but the per-byte bit ordering — whether bit zero is tile zero or tile seven — is open).
6. Document the per-tile "blocks line of sight" predicate that the visibility producer consults; check whether it is a separate bitmap, derived from the passability bitmap, or class-derived.
7. Document the dawn-dusk tile substitution table — the per-tile-id swap from night-form to day-form that the town-mode entry pass applies — by tracing the substitution loop in `TOWN.OVL`.
8. Document the field-tile per-frame tile-id runs (Fire Field, Poison Field, Sleep Field, Energy Field, Wall of Fire, Electric Field) and their per-frame durations.
9. Identify any tile ids that double as render-only sentinels in the upper half of the space (for example, the player avatar sprite sentinel value `0xFC` referenced in the town-entry handler — confirm whether this is a tile id, an active-object table marker, or both).
10. Verify the tile-id partition boundaries against runtime DOSBox traces for water, mountain, lava, and door classes — the ranges given in Section 3 are working approximations.
