# Tile Catalog

A reference catalog of every tile in Ultima V — its index, semantic family, what the player sees when looking at it, whether the engine treats it as passable, and what (if any) special trigger it pulls. This document is descriptive and table-driven; it does not specify the renderer, the visibility producer, or the per-mode walk loops (those live in the system specs). Use this as the lookup table when implementing the world-tile renderer, the look-handler, the passability filter, the tile-effect dispatcher, or the active-object animator.

## 1. Overview

Ultima V ships with exactly five hundred and twelve top-down tiles. The tile
space is a flat byte-extended index space, addressable from zero through five
hundred and eleven inclusive. Every overworld cell, town/interior cell, combat
arena terrain cell, visible actor, item, and effect ultimately resolves to an
index in this space. Dungeon level cells are different: `DUNGEON.DAT` stores
packed class/variant bytes for first-person dungeon geometry, not unified
tile-sheet ids.

The graphics for all five hundred and twelve tiles ship in a single flat sprite
sheet on disk; every tile is sixteen by sixteen pixels at the standard
four-bits-per-pixel EGA depth, indexable by tile id alone with no per-tile
metadata in the graphics file. The graphics asset is paired with two siblings
— a surface/town "look-at" string table and a resident terrain-query table
family held in the data segment — and is consumed by the top-down world, town,
combat, object, actor, item, and transient-effect drawing paths. Dungeon mode
is the cell-geometry exception: dungeon cells use their own packed-byte
encoding, even though dungeon presentation can still draw tile-sheet art for
side effects, actors, or UI elements.

Do not use a tile byte's high nibble as a universal class id. World and town map
tiles use tile ids whose primary classifier is the look/attribute data associated
with that id; the high nibble is only a loose animation or sentinel bucket.
Dungeon cells use a separate packed-byte encoding where the high nibble is a
strict sixteen-way dungeon class and the low nibble is class-specific variant
data. The two systems are intentionally separate and their nibble values do not
line up.

Each tile carries the following properties:

- An **index** in `0..511`. The canonical identifier for top-down map/arena
  terrain, active-object records, save slots, and chest/object contents bytes.
  It is not the identifier stored in `DUNGEON.DAT` dungeon cells.
- A **sprite**: the sixteen-by-sixteen pixel image at offset `index × 128` in the on-disk EGA sprite sheet (Section 13).
- A **class**: the broad category the engine treats the tile as (water, terrain, path, wall, furniture, door, decoration, special, vehicle, NPC, monster, item, effect, avatar). Class is *implicit* in the index range; the engine does not store a class field.
- A **look-at string** (zero-or-one of two hundred and sixteen unique entries):
  the short prose phrase the surface/town look path prints when the cursor
  falls on this tile or on an object resolved by that path. LOOK2's lower
  domain describes map-cell terrain ids, and its upper domain describes object
  ids. Dungeon L-Look uses `DUNGEON.DAT` cell classes instead of LOOK2 tile ids.
  Many entries share strings — eight grass variants resolve to the single
  string "grass". The shared sentinel `*` is used for entries that cannot be
  looked at.
- A **base terrain bitset** for tile ids `0..255`, stored as a resident
  thirty-two-byte table grouped by tile-id family. It is combined with a
  caller-query dispatcher for movement and interaction checks. Sprite-only
  tiles `256..511` do not carry static terrain passability.
- A **visibility propagation rule** for a narrow set of tile ids touched by the
  visibility carve helper. This set is separate from movement passability and
  LOOK text; its current public contract lives in `systems/visibility.md`.
- An **animation state** for the subset of classes that animate (water, lava, fire, certain monsters, certain vehicles). Animated tiles occupy contiguous index runs and are advanced by the per-turn animator.
- A **special trigger** for the subset that drive scripted handlers (moongates, falls, shrines, ladders, doors, signs, beds, chairs, chests). Encoded as the post-action tile probe matching a hard-coded id or range in the per-mode walk loop.

The complete index-range layout is in Section 3. Class-by-class breakdowns follow in Sections 4 through 11. Sections 12 and 13 record encoding rules; Sections 14 and 16 separate the gameplay-complete catalog contract from optional presentation/catalog QA.

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
| Special     | 128..159            | 32          | Fixtures, shrines, fountains, wells, fields, fire effects         |
| Vehicle     | 160..191            | 32          | Live horse/ship/skiff/magic-carpet frames plus balloon art        |
| NPC         | 192..255            | 64          | Townspeople, guards, jesters, beggars, named NPCs, hostile humans |
| Monster     | 256..383            | 128         | Animals, undead, demons, dragons, swarm sprites                   |
| Item        | 384..447            | 64          | Weapons, armor, reagents, food, gems, torches, scrolls, keys      |
| Effect      | 448..495            | 48          | Moongate frames, projectile sprites, splash and explosion frames  |
| Avatar      | 496..511            | 16          | Player and party-member sprites with directional / vehicle frames |

The boundaries above are nominal and rounded to byte-boundary chunks for description; an implementation should treat the class boundaries as deltas from the in-engine special-trigger comparisons and the active-object class-range tests, not as fixed power-of-two splits. Section 3 gives a finer breakdown.

The fourteen classes split into three super-categories:

- **World/town/combat terrain classes** (water, terrain, path, wall,
  furniture, door, decoration, special, indices roughly `0..159`) live in the
  top-down map and arena terrain grids. They do not describe packed
  `DUNGEON.DAT` cells.
- **Actor-and-item classes** (vehicle, NPC, monster, item, effect, avatar, indices `160..511`) live in *active-object records* — the dynamic sprite layer drawn over terrain. Records carry the tile id directly; the renderer composites them on top of the underlying cell.
- **Transient effects** are written into the rendered tile buffer by the moongate animator, projectile animator, and certain spell handlers, but are not stored in any persistent map.

Storage discipline is rigorous: a chair in a town map is a furniture-class index in the tile grid; a horse the player can mount is a vehicle-class index in the active-object table; a fireball mid-flight is an effect-class index temporarily in a slot; a dungeon wall or fountain cell is instead a packed dungeon class/variant byte interpreted by dungeon-mode systems. The same five-hundred-and-twelve-entry sprite sheet serves top-down terrain, actors, items, and effects, while dungeon cell geometry is specified by `formats/dungeon-dat.md` and `systems/dungeon-mode.md`.

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
| 104..111    | decoration      | Floor mosaics, banners, statues, glyphs                                  |
| 112..127    | barrier/field   | Magic barrier or shadow-field family; Sceptre U-Use treats this range as dissolvable top-down cells |
| 128..135    | special         | Pendulum/restraint/grate/archway fixtures; not the traced natural-moongate terrain byte |
| 136..143    | special         | Shrine altars (eight, one per virtue)                                    |
| 144..151    | special         | Fountains, wishing-wells, energy fields                                  |
| 152..159    | special         | Fire effects, poison fields, sleep fields                                |
| 160..167    | vehicle         | Horse (mounted)                                                          |
| 168..175    | vehicle         | Ship (four facings, possibly damaged variants)                           |
| 176..183    | vehicle         | Skiff (four facings)                                                     |
| 184..187    | vehicle         | Magic carpet                                                             |
| 188..191    | vehicle art     | Balloon art family; no traced live balloon transport path in the analyzed baseline |
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

The ranges above are the working partition. Gameplay systems should rely on the class, storage, passability, animator, and special-trigger contracts here and in the cross-referenced system specs. Some precise visual names within the upper actor/item/effect ranges remain presentation/catalog QA rather than unresolved gameplay behavior.

## 4. Animation phases

A subset of classes animates. The engine implements animation by reserving a contiguous run of two, four, or eight indices for one animated tile, and stepping the displayed index through the run on each per-turn animator pass.

The dominant pattern is the **four-frame cycle**: a single conceptual tile (water, lava, fire) reserves four sequential indices `N, N+1, N+2, N+3`, each carrying a sprite for one phase. The animator advances the cell's stored index by one each turn (modulo four within the run). The renderer paints whichever index is currently in the cell.

Moongate graphics use a bespoke render-frame plate driven by the overworld
moongate animator. They are not ordinary stored map-cell animation and are not
selected from the sky/status moon glyph display. The animator's phase counter
cycles through a sixteen-step visual sequence; `systems/overworld.md` owns the
timing and scratch-state contract.

| Class        | Cycle length    | Animator                                    |
|--------------|-----------------|---------------------------------------------|
| Water        | 4               | Per-turn world-tick animator                |
| Lava         | 4               | Per-turn world-tick animator                |
| Fire / brazier | 4             | Per-turn world-tick animator                |
| Wind / gust visuals | 4 | Effect-specific animation; not a confirmed `DUNGEON.DAT` contact class |
| Moongate     | 16 visual phases | Bespoke render-frame animator (overworld)   |
| Vehicles     | 4 per facing    | Active-object animator                      |
| Monsters     | 2..4 per facing | Active-object animator                      |
| Effects      | 1..8            | Per-effect handler                          |

The active-object animator runs as part of the per-turn epilogue. It walks the table from the highest slot down, classifies each slot's tile id, and for animated classes advances the slot's frame-counter and rewrites the slot's tile id to the next-frame index in the same run.

The per-turn world-tick animator walks the rendered tile buffer (not the persistent map) and, for cells whose tile id falls in an animated-static-class run, advances the displayed id by one. The persistent map cell is *not* modified; the animation is render-only. A saved game loaded mid-cycle re-starts from frame zero — no save data records the animator's phase counter.

Animated-static classes are deliberately rare. Walls, doors, paths, terrain, vegetation, and furniture do not animate.

## 5. Passability

Whether a map tile is enterable starts with a thirty-two-byte resident bitset.
The table covers tile ids `0..255` - the world/town map-cell range.
Sprite-only tile ids (`256..511`) never live in a static map cell and have no
static terrain passability entry.

For a tile id in `0..255`, the bitset byte is selected by `id >> 3`, so each
byte covers one eight-tile family. Bits inside that byte are numbered
most-significant first. A set bit rejects that tile for the base terrain
predicate; a clear bit accepts it. The caller's movement or interaction class
is not a bit column in this table. Instead, a separate tile-class dispatcher
uses the caller's query byte to select which predicate family should be applied
to the tile.

Movement handlers for world/town maps, outdoor active-object movement, and
several command guards go through this query-dispatcher layer. The town NPC
schedule pathfinder is a deliberate exception: it builds its BFS workspace from
a dedicated NPC pathfinding bitmap, described in `systems/npc-schedules.md`,
rather than from the foot/avatar terrain query. Dungeon first-person floors use
the separate packed-nibble `DUNGEON.DAT` encoding rather than this table.
Combat arenas also use their own tile-class passability lookup, separate from
the world/town table, so a class that is blocked in one mode is not
automatically blocked in the other.

The table is *not* mutated at runtime. Tile-state changes that affect
walkability - a closed door becoming open, a destroyed wall becoming rubble -
are implemented by *changing the tile id* in the live tile buffer, not by
editing passability data. The engine treats tile id family and caller-query
passability as fixed data.

The base bitset predicate also carries a compatibility edge: LOOK2 chair tiles
`0x90..0x93` are rejected for most query classes even when their bit is clear.
The force-reject is skipped for the foot/avatar query family and for the
`0x40` query family. Earlier notes that described tile ids `0x1C..0x1D` and
`0x40..0x4F` as globally permitted were incorrect; those comparisons are
against the caller query byte, not the tile id.

The mask captures only the *broad* walkability rule. Class-specific predicates
layer on top:

- **Water tiles** are passable for ships and skiffs; the magic carpet also
  accepts the deep-water/water/shoal family through its special query. Foot and
  horse movement reject ordinary water.
- **Mountain tiles** are rejected by the named foot, horse, and carpet
  movement queries. Balloon art has no promoted live transport predicate in
  the analyzed baseline; see `systems/vehicles.md`.
- **Lava and chair compatibility-edge tiles** are query-specific: foot/avatar
  accepts LOOK2 `0x8F` molten lava and chair variants `0x90..0x93` because
  that query skips the chair force-reject rule; mounted horses reject the edge,
  and the magic carpet accepts molten lava `0x8F` but still rejects the chair
  edge `0x90..0x93`.
- **Door tiles** are passable when open, impassable when closed; the tile id changes to reflect this.
- **NPC and monster cells** are blocked-by-occupant, not blocked-by-tile; the underlying tile may be passable but the active-object table records an actor on it. Movement and pathfinding test both.

The full "is this cell walkable for actor X with vehicle Y" combinator lives in
`systems/movement.md`, with mode-specific hooks in `systems/overworld.md` and
`systems/town-mode.md`. The base terrain bitset and caller-query dispatcher
are the first gate; vehicle, occupancy, and mode-specific predicates are later
gates.

## 6. Special-trigger tiles

A small set of world tiles drives scripted handlers. These tiles do not look or animate any differently from their inert counterparts, but the per-turn walk loop's post-action tile probe matches them and dispatches to a special handler.

**Town poison-gas terrain.** In town-family scenes, live map tile `0x04`
has an additional underfoot effect when the party is on foot. The clean
semantic key for the effect is:

| Live town tile id | Town underfoot class | Required party transport marker | Effect owner |
|---|---:|---:|---|
| `0x04` | `4` | `0x1C` | `systems/town-mode.md` poison-gas / swamp save |

The transport marker is party state, not data stored on the tile itself. A
clean implementation that stores tile attributes as `(tile_class,
required_transport)` can use the row above for the poison-gas doorway check and
does not need a coordinate fallback for this effect. The same tile id remains
ordinary static terrain for systems that do not run the town underfoot-effect
handler.

**Falls.** The traced surface chasm trigger is the fixed Britannia coordinate
`(54, 138)`. Stepping onto that falls cell triggers the
fall-into-the-underworld handler — print a banner, apply random fall damage,
swap the world plane, re-initialise the active-object table. Any additional
plane-transition sources remain with the overworld transition inventory.

**Outdoor ascents.** The public spec does not yet publish a traced set of underworld-to-surface outdoor ascent tiles. Preserve candidate special tiles as tile identities, but do not assign an ascent contract until the overworld transition inventory is traced.

**Moongate cells.** Terrain byte `0xDC` is LOOK2-named as a moon
gate and is accepted by movement and local-light systems as
moon-gate-family state. Saved Moonstone slots drive the traced live-terrain
placement/waning schedule, and the natural-moongate animator can stamp frame
tiles into the rendered world view while a gate is visible. General underfoot
entry is specified in `systems/overworld.md`; this catalog only names
storage-domain semantics. The `0x80..0x87` special range is a
pendulum/restraint/grate/archway fixture range in the LOOK2-backed catalog, not
the traced natural-moongate terrain byte; do not infer teleport behavior solely
from a moongate-frame tile id.

The same numeric byte can have a different public name in a different storage
domain. In particular, `0xDC` is a terrain byte accepted by movement and
local-light systems as moon-gate-family state, while active-object records use
`0xDC` as the first Dragon sprite frame. Runtime consumers must interpret the
byte through the buffer they are reading: live terrain, rendered scratch, or
active-object slot.

**Shrines and Codex urns.** Shrine-family special tiles are consumed by the
M-command kneel handler, not merely by stepping onto them. Ordinary virtue
shrines prompt for the correct mantra and advance the shrine quest state as
specified in `systems/karma.md`. The Codex urn special tile routes through the
same command family but reads the Codex/prophecy text and sets the Codex-read
quest bit for an ordained virtue.

**Town and dungeon entrances.** Entering on a fixed entrance coordinate sets the scene byte and dispatches the town-mode or dungeon-mode setup. The trigger is recognised by the resident world-location table, not by tile id alone; rows 0..31 select town-mode scenes and rows 32..39 select dungeon scenes.

**Waterfalls.** Specific water-tile variants drive a "you are swept downstream" handler that moves the party several cells in the waterfall's direction.

**Ladders / staircases.** In town mode, facing-sensitive stairway tiles are the `0xC4..0xC7` family. The low two bits are a facing selector in the town movement wrapper's normalized direction space: entering along that facing goes up one floor, entering from the opposite facing goes down one floor, and side crossings leave the current floor unchanged. K-Klimb ladders and trapdoors use the same floor-reload machinery after their own underfoot command checks. In dungeon mode, ladders are encoded in the tile byte's high nibble and handled by the dungeon turn loop's K-Klimb branch.

**Doors.** Any door tile (indices `96..103`) blocks movement when closed and dispatches the door-interaction handler. The handler maps to O-Open (key for locked doors), J-Jimmy (lockpick), or dispel (the An Sanct / In Ex Por spells).

**Chests.** Stepping onto a chest tile triggers G-Get. The handler may prompt for a key on locked chests, apply a random trap, and either yield treasure or print "Nothing of note".

**Signs.** Sign-post tiles trigger the read-sign handler — a sign sub-table in `SIGNS.DAT` is indexed by per-location coord.

**Beds.** A bed tile in an inn enables H-Hole-up. Outside an inn or off a bed, H prints "Not here!" and consumes no turn. The hours/rest contract is in `systems/rest-and-camp.md`.

**Chairs.** The visible chair trigger in town mode is tile `0x8C`; Stonegate adds a special scene effect when the party steps on it. Do not conflate that chair tile with the paired NPC floor-link markers `0xC8` and `0xC9`.

**NPC floor-link markers.** Two marker bytes - `0xC8` and `0xC9` - appear in town tile grids and are consumed by the NPC scheduler's tile-ID pathfinder variant. When schedule movement needs to bridge floors, the pathfinder searches the live tile buffer for cells containing one selected marker ID and uses those cells as goals. Shipped location data places these values as authored floor-link annotations rather than ordinary furniture. Do not treat these IDs as ordinary passable terrain, and do not assume they are unavailable to runtime consumers.

**Wishing-wells, springs, caves.** Wishing-wells run the wish-for-a-vehicle handler (the Easter-egg "Corvette / Ferrari / Lamborghini / Lotus / Porsche / Horse" dialogue); in the granting scenes, all accepted well words create the same horse-family active object. Springs restore MP; caves drop a chest.

**Camp / fire.** Camp tiles and brazier tiles trigger the camp-and-rest handler when H-Hole-up is invoked on them. Outdoor rest and the rare camp-event level-up live in `systems/rest-and-camp.md`.

The exact tile-id-to-trigger mapping is implementation-detail of the per-mode walk loops, captured in the private per-mode loop notes rather than as a free-standing table here.

## 7. Monster tiles

Monster sprites occupy indices `256..383`. Each monster — sea horse, squid, sea serpent, shark, giant rat, bat, giant spider, ghost, slime, gremlin, mimic, reaper, gazer, crawler, gargoyle, insect swarm, orc, skeleton, python, ettin, headless, wisp, daemon, dragon, sand trap, troll, mongbat, corpser, rot worm, shadow lord — owns a small range of indices, typically four sequential frames (one per facing or one per animation phase).

Cross-reference: `catalogs/monster-bestiary.md` for per-monster stats, AI archetype, encounter rate per terrain, and the singular and plural display names from the resident data string tables.

Monsters appear in two contexts:

- **Wandering encounters.** The encounter spawner picks a monster class based on the current world-tile class and party state, and writes a fresh active-object slot.
- **Combat arenas.** When combat starts, the encounter base class and the
  separate replacement-tile table choose starting tile ids; the combat actor
  table tracks frame state per actor.

Hostile humans (brigands, pirates, hostile guards) sit in the *NPC* range, not the monster range. The combat system distinguishes them for damage and loot, but the tile space treats them as NPC-class.

## 8. NPC tiles

NPC sprites occupy indices `192..255`. Each NPC type — villager, merchant, jester, child, beggar, guard, wanderer, named NPCs (Lord British, Blackthorn, named ship captains), shadow lords — owns one or more indices, typically two frames per facing for an idle / walk cycle.

Cross-reference: `catalogs/npc-roster.md` for per-NPC names, dialogue file links, default schedules, and which location each NPC lives in. The role-name strings ("Avatar", "Villager", "Merchant", "Jester", "Bard", "Child", "Beggar", "Guard", "Wanderer", "Blackthorn", "Lord British") in the resident data anchor the partition.

NPCs appear only in town mode and in scripted overworld events. The active-object table records the current sprite tile id directly; the per-tick walker advances the schedule and updates the position and sprite fields.

A pre-conversation gate inspects the candidate NPC's current sprite tile to detect transient states. Specific tile ids carry status semantics — a "sleeping" sprite renders the gate's "Zzzzzz..." response without entering the dialogue engine. The status-tile mapping is part of the NPC roster, not the tile catalog.

## 9. Item tiles

Item sprites occupy indices `384..447`. Items are weapons, armor, reagents, food, gems, torches, scrolls, potions, keys, and special story items. Cross-reference `catalogs/item-list.md`.

Items appear in two contexts:

- **Inventory.** The party's inventory holds counts per item id; items in inventory do not occupy a tile. The Z-stats panel renders items as a list of names.
- **In-world drops.** A dropped item — a body to be searched, a chest's spilled contents, a lit torch in the dungeon — occupies one cell as an active-object entry whose tile id is the item's sprite index. G-Get adds the item to inventory and clears the slot.

Two item families — reagents and food — have iconography in the tile sheet but are encountered in the world only as chest contents and merchant stock; they do not drop free-standing the way weapons and torches do. A reagent's tile id is used by L-Look and the inventory panel; the inventory itself counts reagents as eight bytes in the save image.

Three items — the **sandalwood box**, the **plans for the HMS Cape**, and the **Crown / Sceptre / Amulet of Lord British** — are unique story items with bespoke acquisition handlers. They occupy fixed item-sprite identities and are picked up at scripted points, not by encounter spawn. The Sandalwood Box grant enters through the shared Get/container inventory-add path from a fixed `CASTLE:0` object-slot pickup; the endgame only reads the resulting save-backed flag.

## 10. Vehicle tiles

Vehicle sprites occupy indices `160..191`. Four live vehicle families —
**horse** (mounted), **ship**, **skiff**, and **magic carpet** — carry frame
runs used by the traced command and movement systems. The adjacent **balloon**
run is preserved as art/catalog data; it is not a traced live transport family
in the analyzed baseline.

Vehicles appear as active-object entries. Mounting a vehicle moves the avatar's sprite from the avatar range (`496..511`) to the vehicle range; the original vehicle slot (a dropped horse, a moored ship) clears or remains as a ridable sprite.

For B-Board, `systems/vehicles.md` publishes the clean boardable object-byte
families and transport-state transitions: horse objects `0x10..0x11` become
mounted horse markers `0x12..0x13`, carpet object `0x1B` becomes carpet marker
`0x14`, ship objects `0x24..0x27` board as the same ship-facing marker, and
skiff objects `0x28..0x2B` board as the same skiff-facing marker. Those are
engine object/transport bytes, not a promise that the sprite-sheet tile indices
use the same numeric ids. This catalog still owns final visual naming for the
vehicle art frames and has no promoted balloon boarding path.

Vehicles affect movement and turn timing:

- **Foot.** Default. Standard outdoor turn cost.
- **Horse.** Mounted overland transport; water is rejected by the movement
  predicate, and mounted-horse movement timing is described in
  `systems/vehicles.md`.
- **Ship.** Water-bound. Sail state and facing determine whether the wind/heading cadence described in `systems/weather.md` applies.
- **Skiff.** Slower than ship; usable in shoals and shallow water that ship cannot enter.
- **Magic carpet.** Can cross water and most terrain. Cannot enter mountains, walls, or doors. Tile-effect (lava, fire, poison field) damage still applies.
- **Balloon.** Vehicle art family only at this catalog layer. The traced
  B-Board, X-Xit, U-Use, shipwright, and movement contracts do not publish a
  live balloon transport marker, landing rule, or wind-drift rule for the
  analyzed baseline.

The resident transport marker tracks the current boarded vehicle for movement, encounter probes, and disembark handling. A separate timing/state tag supplies the `Q`/`T` cleanup modifiers described in `systems/time.md`; do not derive the full vehicle table from those letters. See `systems/vehicles.md` for the command-level vehicle contract and `systems/overworld.md` for outdoor movement.

## 11. Effect tiles

Effect sprites occupy indices `448..495`. Effects are short-lived sprites composited over the rendered buffer by per-effect handlers; they do not live in the persistent map and (mostly) do not occupy active-object slots.

The principal effect families:

- **Moongate frames.** A bespoke transient frame plate used by the overworld
  moongate animator. The selected frame comes from the animator's local phase
  counter, not from the status-strip Trammel/Felucca glyph tables and not from
  the saved-slot live-terrain placement/waning schedule.
- **Projectile frames.** Arrow, axe, sling, magic missile sprites in flight. The combat handler walks a projectile from caster to target one cell per render frame.
- **Splash / explosion / impact.** Multi-frame sprites for fireball impact, lightning hit, explosion clouds, smoke. The effect handler runs through the frames and clears.
- **Fields.** Fire field, poison field, sleep field, energy field, electric field. Dungeon field placement writes the field terrain bytes documented in `systems/magic.md` into the live dungeon image, optionally preserving the dungeon visit marker bit. Combat arena fields are handled by the arena-field helper instead of direct dungeon terrain writes; contact is checked after a successful step commits, then routes to the per-field status or damage/value helper.
- **Wind / smoke / sparkle.** Atmospheric and transient effect graphics driven by weather, storm, and spell handlers. The wind/gust graphics are tile-atlas effects; baseline dungeon contact handling does not use them as `DUNGEON.DAT` torch-extinguishing cells.

Several effect tiles double as world-tile sentinels in the special class range, so renderers should keep map-cell field bytes and transient combat-field visuals in the same semantic family even when their storage paths differ. The animator that sweeps live tile buffer for animated-static cells handles dungeon field tiles uniformly: each owns a four-frame run, and the animator advances it.

## 12. Tile-byte encoding

The catalog covers five hundred and twelve indices, requiring nine bits to address. The engine stores each map cell as a *single byte* in the on-disk file, addressing only the lower two hundred and fifty-six ids — exactly the range covered by the resident base terrain bitset.

The other two hundred and fifty-six indices (the upper half — sprite-only tiles for monsters, NPCs, items, vehicles, effects, and the avatar) are *never* written to a map cell. They live exclusively in active-object records, which carry a one-byte tile id plus a frame counter; together they index into the full nine-bit space.

The relevant facts for the catalog are:

- **Map cells store a tile id in `0..255`.** No exceptions.
- **Active-object records can address any tile id in `0..511`** via the id-plus-frame combination.
- **The look-at table (`LOOK2.DAT`) has two domains:** lower entries are keyed
  by raw map-cell tile id `0..255`, while upper entries are keyed by
  surface/town object-domain ids selected by the look handler.
- **The base terrain bitset covers only `0..255`.** Actor movement is gated by
  the underlying cell's terrain family plus the actor's own movement rules; the
  actor's own tile id has no static passability entry because actors move by
  *being* on a cell, not by *being* a cell.

Some class-specific encodings layer on top:

- **Dungeon tiles.** Dungeon `.DAT` cells pack two four-bit fields: high nibble is a strict dungeon tile class (open, wall, door, ladder, chest, trap, fountain, field), low nibble is class-specific attribute. Dungeon tile bytes are *not* indices into the unified five-hundred-and-twelve-tile space and do not share the world/town high-nibble buckets — they are a separate dungeon tile-class encoding rendered by the sparse first-person dungeon renderer.
- **Combat arenas.** Combat `.CBT` terrain cells use standard one-byte tile ids in an eleven-by-eleven grid with a thirty-two-byte row stride. The twenty-one bytes after each terrain row are arena metadata and must be preserved. For `BRIT.CBT`, traced setup copies the placement-slot coordinate slices from that metadata into resident tables; spawn counts and replacement-tile rolls still come from resident combat tables.
- **Markers in town maps.** Marker bytes — NPC start markers `0x48`/`0x49`, spawn marker `0x2A`, dash/period conditional markers `0x2D`/`0x2E`, dawn/dusk archway marker `0x87`, and the NPC floor-link markers `0xC8`/`0xC9` — appear in on-disk tile grids and are consumed by location-load or NPC-scheduler passes. Some are harvested into runtime state, some are conditionally rewritten in the runtime tile buffer, and `0xC8`/`0xC9` remain queryable as runtime tile-ID goals. They should not be treated as ordinary terrain. For the dawn/dusk pass, `0x87` marks the south-adjacent gate cell; shipped maps pair it with `0x44` cobble, which toggles to `0x99` portcullis via XOR `0xDD` at night.

## 13. Graphics-asset encoding

The tile sprite sheet ships in two parallel files — `TILES.16` for sixteen-color EGA and `TILES.4` for four-color CGA — each holding the same five hundred and twelve sprites at the appropriate depth. Both files are LZW-wrapped; after decompression each is a flat array of sprite bytes with no per-tile header.

The EGA file decompresses to exactly sixty-five thousand five hundred and thirty-six bytes — five hundred and twelve sprites at one hundred and twenty-eight bytes each. Each sprite is sixteen rows of eight bytes; each byte holds two pixels high-nibble first; each four-bit value indexes the standard sixteen-entry IBM EGA hardware palette.

The CGA file decompresses to thirty-two thousand seven hundred and sixty-eight bytes — five hundred and twelve sprites at sixty-four bytes each. Each sprite is sixteen rows of four bytes; each byte holds four pixels MSB-first; each two-bit value indexes one of the IBM CGA four-color sub-palettes (the executable selects the palette per scene).

To address a tile by id, the renderer multiplies the id by the per-tile byte size. There are no offsets, no inner directory, no per-tile headers — tile id alone is the file offset divided by the tile byte size. This is the simplest of the LZW-wrapped graphics families.

Palettes are not stored in the file. EGA uses the standard IBM EGA hardware palette; CGA is selected at scene-init time. The driver overlays (`EGA.DRV`, `CGA.DRV`, `T1K.DRV`, `HER.DRV`) handle palette and blit.

The graphics file, the look-at table, and the resident terrain-query tables are
the three siblings that together specify the base static-tile contract. The
per-tile sprite lives in `TILES.{16,4}`; the per-tile string in `LOOK2.DAT`;
the base terrain bitset and caller-query predicate table live in the resident data
segment.

## 14. Sources and completion

The data here is drawn from four sources. Each tile's position in the partition is anchored to a bytes-on-disk observation (the `LOOK2.DAT` string, the resident terrain-query tables), to a per-class engine behaviour (the animator's class-range tests, the special-trigger comparisons), or to the canonical naming from the published manual.

**From the project's private analysis notes** (`u5-decomp/formats/tile-graphics.md`, `data-tables.md`, `data-ovl.md`, `maps.md`, function notes under `functions/LOOKOBJ_OVL/`, `CMDS_OVL/`, `OUTSUBS_OVL/`, `NPC_OVL/`):

- The five-hundred-and-twelve-tile count and the EGA / CGA file-size invariants.
- The `LOOK2.DAT` layout (five hundred and twelve sixteen-bit offsets split
  into terrain and object domains, two hundred and sixteen unique strings, one
  sentinel).
- The thirty-two-byte base terrain bitset in the resident data segment,
  including MSB-first tile-bit ordering within each byte, plus the
  caller-query tile-class dispatcher and the corrected `0x90..0x93`
  force-reject edge.
- The active-object animator's class-range tests.
- The special-trigger comparisons in the per-mode walk loops.
- The marker-byte consumers (NPC start markers, waypoint markers, dawn/dusk archway marker `0x87`, and the NPC floor-link markers `0xC8` and `0xC9`).
- The two-nibble dungeon tile encoding and its separate tile-class space.

**From the published Ultima V manual** (`The Book of Lore`, `The Book of Play`):

- The English names for monsters, NPCs, items, vehicles, and special tiles.
- The descriptive role of each vehicle and special tile.
- The narrative framing of moongates, shrines, and the eight virtues.

**From `LOOK2.DAT`'s string pool, decoded directly:**

- Tile id one is "deep water"; ids two through nine walk through "water", "shoals", "swamp", "grass", "brush", "parched desert", "brush", "trees".
- The dawn/dusk gate pair is named by the same table: `0x87` is an archway, `0x44` is cobble, and `0x99` is a portcullis. P-Push also uses `0x45` as a family-specific occupancy stamp; LOOK2 resolves `0x45` to the same cobble description as `0x44`.
- The last unique string is "a shadow lord".
- Two hundred and sixteen of the five hundred and twelve ids carry unique strings; the rest share a string with a prior id.

**Completion summary.** The catalog assigns all five hundred and twelve indices to one of fourteen classes. Per-tile detail varies:

- **Static gameplay tiles (~160 tiles, indices `0..159`).** The world-tile
  classes are attested by their `LOOK2.DAT` strings, resident terrain-query
  families, visibility ownership, and special-trigger comparisons. The grass /
  brush / desert subdivisions, door variants, barrier family, `0xDC`
  terrain-domain moongate boundary, shrine ids, and town marker ownership boundaries are specified at
  gameplay depth.
- **Actor and vehicle tiles (~220 tiles, indices `160..383`).** Vehicle, NPC,
  and monster ranges are established by the animator's class-range tests and by
  their owning movement, roster, and bestiary catalogs. Exact sprite-frame
  labels inside a run are renderer/catalog attribution unless a system spec
  names a tile id as a gameplay gate.
- **Item, effect, and avatar tiles (~130 tiles, indices `384..511`).** Item,
  inventory, magic, combat, command, and presentation specs cover the gameplay
  consumers. Remaining per-frame art labels, pixel ordering checks, and
  render-only sentinel names are presentation/catalog QA, not unresolved command
  ownership.

All five hundred and twelve indices have a class assignment and storage-domain
contract. The tile catalog is complete for passability, LOOK2 ownership,
special-trigger routing, active-object classing, and file-format boundaries.

## 15. Cross-references

- `systems/movement.md` - Shared movement and passability predicate, including
  the resident terrain bitset, caller-query dispatcher, vehicle layer, dynamic
  occupancy, and commit rules.
- `systems/overworld.md` — Overworld mode specification, including the active-object animator, the per-turn tile probe, and the moongate animator. Section 8 lists the special tile classes the per-turn block recognises.
- `systems/town-mode.md` — Town-mode specification, including marker harvest/runtime marker handling (Section 3 / Section 6), the dawn/dusk gate substitution (Section 6), and the per-tile interaction commands (Section 9).
- `systems/dungeon-mode.md` — Dungeon-mode specification, including the two-nibble dungeon tile encoding (Section 4) and the sparse renderer's wall checks (Section 6).
- `systems/active-objects.md` — Active-object table specification, including the per-slot record format and the animator pass.
- `systems/vehicles.md` — Boarding, exiting, parked-vehicle persistence, and ship-fire behaviour.
- `systems/visibility.md` — Visibility producer, including the queue-based carve, propagation-blocker set, and adjacent-only special cases.
- `systems/doors-and-z-transitions.md` — Door interaction and floor-change handlers, including the per-door tile id and the stair / ladder dispatchers.
- `formats/saved-gam.md` — Save image, including the active-object table snapshot and the `.OOL` file (the persistent active-object slice).
- `formats/look2-dat.md` — `LOOK2.DAT` format spec.
- `formats/tiles.md` — `TILES.{16,4}` graphics format spec.
- `catalogs/spell-list.md` — Spell catalog (the field-placement spells reference the field-tile entries here).
- `catalogs/monster-bestiary.md` — Per-monster names, stats, and tile-id ranges.
- `catalogs/npc-roster.md` — Per-NPC names, dialogue indices, and tile-id ranges.
- `catalogs/item-list.md` — Per-item names, prices, and tile-id ranges.

## 16. Tile Catalog Presentation QA Queue

The gameplay tile contract is complete at class, storage, passability,
animation-family, and special-trigger depth. The remaining tasks below are
optional presentation/catalog QA or source-free reauthored-data aids; they
should not be treated as blockers for implementing the runtime behavior already
specified by this catalog and the linked system specs.

1. Refine the per-tile id within each monster's frame run by walking `MON0.16` through `MON7.16` against the manual's monster list and the resident data monster-name pool.
2. Refine the per-NPC tile-id labels against the role-name string pool ("Avatar", "Villager", ..., "Lord British") and the named-NPC list.
3. Refine the per-item tile-id labels against the item-name pool and the Z-stats inventory panel.
4. Keep marker-byte catalog labels aligned with their owning systems: location
   loading owns NPC start and conditional rewrite markers, while the NPC
   scheduler owns the `0xC8`/`0xC9` floor-link goal markers.
5. Check any remaining visual edge cases around local-light writer order and
   special runtime stamps; the core propagation-blocker list and moongate-mask
   ordering are covered in `systems/visibility.md`.
6. Refine the field-tile per-frame tile-id runs (Fire Field, Poison Field,
   Sleep Field, Energy Field, Wall of Fire, Electric Field) and their visual
   frame durations if pixel-perfect presentation becomes a target.
7. Label any tile ids that double as render-only sentinels in the upper half
   of the space; keep active-object sentinel values separate from atlas tile
   ids unless a traced renderer consumes them as art.
8. Cross-check tile-id partition boundaries against runtime DOSBox traces for
   water, mountain, lava, and door classes when pixel-perfect presentation or
   independent reauthored data is desired; movement/passability behavior is
   already owned by `systems/movement.md`.
