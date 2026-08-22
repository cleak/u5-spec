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
- An **animation state** for the subset of ids that animate (five small terrain/fixture ranges, plus certain monsters and vehicles in the actor half). Animated tiles occupy contiguous index runs and are advanced by the per-turn animator; Section 4 lists them.
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
| Effect      | 448..495            | 48          | Projectile sprites, splash, explosion and impact frames           |
| Avatar      | 496..511            | 16          | Player and party-member sprites with directional / vehicle frames |

The boundaries above are nominal and rounded to byte-boundary chunks for description; an implementation should treat the class boundaries as deltas from the in-engine special-trigger comparisons and the active-object class-range tests, not as fixed power-of-two splits. Section 3 gives a finer breakdown. For the actor half, Sections 3.1 and 7 take precedence over the rows above: the `256..383` "Monster" row is superseded, and the bestiary's monster runs resolve at `384..511`.

The fourteen classes split into three super-categories:

- **World/town/combat terrain classes** (water, terrain, path, wall,
  furniture, door, decoration, special, indices roughly `0..159`) live in the
  top-down map and arena terrain grids. They do not describe packed
  `DUNGEON.DAT` cells.
- **Actor-and-item classes** — the dynamic sprite layer drawn over terrain, living in *active-object records*. An active-object record does **not** carry the drawn tile id: it carries an actor byte in `0..255`, and the renderer adds `256` before indexing this catalogue, so every actor drawn through the world compositor resolves into the `256..511` half. See Section 3.1 for the rule and its one reserved value, and `systems/active-objects.md` section 12 for the compositor path.
- **Transient effects** are written into the rendered tile buffer by the projectile animator and certain spell handlers, but are not stored in any persistent map. Moongates are *not* in this group: a natural gate is live terrain written into the map buffer by the once-per-turn refresh, not a transient render effect.

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
| 74..79      | wall / opening  | Arrow slit `0x4A`, window `0x4B`, pile of rocks `0x4C`, wall variants `0x4D..0x4F` — confirmed from the shipped description table. The earlier nominal "Bookshelves, dressers, vanities, trunks" naming for this row is **withdrawn**; see Section 3.1 and `systems/visibility.md` Section 6. |
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

### 3.1 The upper half is the actor bank, and its nominal names are provisional

Indices `0..255` are the **terrain half**: the values that appear in map grids,
arena grids and scene records. Indices `256..511` are the **actor half**: the
values a live or cinematic actor resolves to. The two halves are reached by
different renderer paths, which is why the same byte can be a floor tile in one
and a person in the other. An actor's stored byte is a value in `0..255` and the
renderer adds **256** to it before indexing this catalogue; the sole reserved
actor byte is `0x16`, which means "draw nothing". `systems/endgame.md` section 4
publishes that rule in full, and `systems/active-objects.md` owns it for live
gameplay actors.

That indexing rule resolves a reported contradiction: actor byte `0x44` is not
the floor tile whose *terrain* index is `0x44`, it is tile 324; actor byte
`0x0E` is not furniture, it is tile 270. An engine reading actor bytes straight
into this catalogue will render furniture and floor where people should be.

**The nominal names given above for the actor half are provisional and at least
two of them are wrong.** Decoding the shipped tile atlas directly shows the
upper half is laid out coarsely as objects and vehicles, then people, then
monsters — not as one long monster run followed by items. Individual ids
confirmed from the shipped art, which take precedence over the range names
above:

| Tile index | Confirmed from the shipped atlas |
|---:|---|
| 264 | A small blue radiant spark — the Orb of the Moons flash used by the endgame |
| 270 | A red-and-white lidded chest — the sandalwood box as an actor |
| 320..323 | A blue-robed figure with a staff, four walk frames — the Mage class sprite |
| 324..327 | A green-clad figure, four walk frames — the Bard class sprite |
| 328..331 | A mailed figure with shield and sword, four frames — the Fighter class sprite |
| 332..335 | A green-tunic figure with sword, four frames — the Avatar class sprite, also used by every class outside the three above |
| 380..383 | A crowned, bearded figure in a red-and-purple robe seated between two banners — Lord British on his throne |

The nominal rows "320..335 Daemon, dragon (greater)" and
"368..383 Reserved / boss-monster slots" are therefore **withdrawn**: both of
those bands are person sprites. Decoding the atlas shows the actor half runs
roughly as objects and vehicles, then people, then monsters, rather than as one
long monster run followed by items — but most of the exact seams have not been
fixed, so no replacement range table is published here. One seam is fixed from
the combat side: Section 7 places the bestiary's monster runs at `384..511`.

The same caveat applies to the terrain half above index 128, and this document
already contradicts itself there: the nominal row "192..255 NPC — Townspeople,
guards, ... named NPCs" is inconsistent with the shipped-description list later
in this section, which names `0xC4..0xC7` as the stairway family, `0xCA..0xCB`
as wooden fence, `0xD4..0xD7` as the waterfall family, `0xDC` as the moon gate,
`0xF0..0xF7` as shop signs and `0xFA..0xFB` as the grandfather clock — all of
them inside that band, and none of them a person. Decoding the atlas agrees
with the confirmed list: `192..255` is scenery and fixtures.

**Precedence rule.** Where an index has been confirmed from the shipped
description table or from the shipped art, that confirmation wins. The Section 2
class table and the Section 3 range table are working hypotheses for the bands
nobody has confirmed yet; re-cataloguing both halves index by index is open
catalogue work and is tracked in Section 16.

Where an individual id has been confirmed directly against the shipped
description table (`formats/look2-dat.md`), that confirmation takes precedence
over the nominal range it falls in above. Ids confirmed this way so far, and
used as behavioural predicates elsewhere in this spec set, are: crystal sphere
`0x29`; metal grate `0x86`; loose brick `0x8C`; chair `0x90..0x93`; mirror
`0x9D`, mirror-with-reflection `0x9E`, broken mirror `0x9F`; deep well `0xA1`;
bed `0xAB`; arrow slit `0x4A`, window `0x4B`, pile of rocks `0x4C` and the wall
variants `0x4D..0x4F`; window shelf `0x5A`; stairway family `0xC4..0xC7`; ascend/descend floor links `0xC8` and
`0xC9`; wooden fence `0xCA..0xCB`; waterfall family `0xD4..0xD7`; moon gate
`0xDC`; shrine flame `0xDE`;
collapsed dungeon entrance `0xDF`; shop-sign family `0xF0..0xF7` and `0xF9`;
grandfather clock `0xFA..0xFB`; **telescope** `0x59`. A further group is
confirmed as *sentinel* rows — ids whose description record is the shared
placeholder string because a command handler produces their output instead:
`0x59` again, the sign/poster ids `0x89`, `0x8A`, `0xA0`, `0xA4` and `0xF8`, and
the fountain band `0xD8..0xDB`. The telescope appears in both lists because its
name is confirmed from its **art**, not from a description record: its row in
the description table holds only the placeholder, since looking at it runs the
sky renderer instead of printing a string. Those ids are used as Look predicates in `systems/view.md`
Section 3 and are therefore fixed even though they carry no name. The two
groups are not complements: the wishing well `0xA1` is a Look predicate
handled entirely by a command handler, yet it appears in the *named* list
above because it does carry a real description record — one the Look path
never reaches. Sentinel status corroborates handler ownership where it
applies, but it does not define the predicate set. Reconciling
the remaining nominal ranges against the description table is open catalogue
work.

## 4. Animation phases

A subset of classes animates. The engine implements animation by reserving a contiguous run of two or four indices for one animated tile, and stepping a **selector** through the run on each per-turn animator pass.

The dominant pattern is the **four-frame cycle**: a single conceptual tile reserves four sequential indices `N, N+1, N+2, N+3`, each carrying a sprite for one phase. The map cell keeps its authored index forever; a small resident table holds one selector byte per animated id, and the animator advances those selector bytes. The renderer resolves the cell's authored id through its selector at draw time. `systems/animation.md` Section 6 owns this contract.

Moongate graphics are **not** animated at all. A natural moongate is ordinary
live terrain: the once-per-turn refresh writes the moon-gate tile onto an
eligible Moonstone cell at night and restores the underlying grass after dawn,
and the renderer paints it like any other tile. An earlier revision of this
catalog described a bespoke render-frame plate driven by a moongate animator
that cycled a sixteen-step visual sequence; that reading is withdrawn. The
sixteen-step cycle it described belongs to the night-time light beacon
(`systems/visibility.md` Section 12.6), which paints light, not gates.
`systems/overworld.md` owns the gate placement and entry contract.

| Tile ids | Family | Cycle length | Animator |
|---|---|---|---|
| `0xD4..0xD7` | Waterfall | 4 (every tick, ungated) | Per-turn world-tick tile animator |
| `0xD8..0xDB` | Fountain | 4 (every tick, ungated) | Per-turn world-tick tile animator |
| `0xEC..0xEF` | The standard of Britannia | 4 (half rate — same gate as the pendulum) | Per-turn world-tick tile animator |
| `0x80..0x83` | Pendulum | 2 (paired toggle, half rate) | Per-turn world-tick tile animator |
| `0xFA..0xFD` | Grandfather clock, bellows | 2 (paired toggle, quarter rate) | Per-turn world-tick tile animator |
| — | Moongate | None | Not animated; live terrain (see note above) |
| — | Vehicles | 4 per facing | Active-object animator |
| — | Monsters | 2..4 per facing | Active-object animator |
| — | Effects | 1..8 | Per-effect handler |

**Correction.** Earlier revisions of this table listed water, lava, and
fire/brazier as four-frame families driven by the per-turn world-tick animator,
and added a "wind / gust visuals" row. That family list is **withdrawn**: the
world-tick tile animator touches exactly the five id ranges above and no others,
and **no water, lava, torch or brazier tile is among them**. The same revision
left the flag row without a rate note, which implied it advanced every tick;
that too is **withdrawn** — only the waterfall and fountain rows are ungated, and
the remaining three sit behind nested gates. `systems/animation.md`
Section 6 carries the full contract and the same correction.

The active-object animator runs as part of the per-turn epilogue. It walks the
table in **increasing** slot order, classifies each slot's tile id, and for
animated classes advances the slot's frame-counter and rewrites the slot's tile
id to the next-frame index in the same run. (An earlier revision said "from the
highest slot down"; that is withdrawn. Descending order belongs to the
*compositor*, which walks slot thirty-one down to slot zero so that low-indexed
slots paint on top — `systems/visibility.md` Section 8.)

The per-turn world-tick tile animator does **not** sweep the rendered tile
buffer. It advances one selector byte per animated tile id in a small resident
table, so a single update changes every visible cell of that family at once. The
persistent map cell is *not* modified; the animation is render-only. A saved game
loaded mid-cycle re-starts from the selectors' current values — no save data
records the animator's phase counter.

Animated-static ids are deliberately rare. Walls, doors, paths, terrain,
vegetation, and the great majority of furniture do not animate.

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

The probe is not step-gated. Town mode's underfoot handler runs once per
turn-consuming action, after that turn's clock advance, and re-reads the tile
the party currently occupies, so the effect re-rolls for every turn spent
standing on the tile.

Two further town underfoot tile families are damage tiles rather than cosmetic
ones: live tile `0x8C` (shipped description "a loose brick"; it also changes
floor outside the Stonegate scene) and live tiles `0xBC` and `0x8F` — **the
burning family**, whose shipped descriptions are "a fireplace" and "molten lava"
and whose handler prints the stored line `Burning!`. Both apply an independently
rolled `1..8` hit points to every non-Dead party slot. Their behavior is
specified in `systems/town-mode.md`.

**Correction.** Earlier revisions of this catalog, and `systems/town-mode.md`,
called `0xBC`/`0x8F` "the rune/lever family". That name is **withdrawn**. It came
from a working guess in an early overlay note, not from the data: the description
table names the two ids a fireplace and molten lava, the string the handler
prints is `Burning!` — sitting in the shipped string pool immediately beside
`A TRAPDOOR!` and `Poisoned!`, the other two town underfoot lines — and `0xBC`
is independently confirmed as a light source by the local-light source list in
`systems/visibility.md` Section 12.3. This document already named `0x8F` molten
lava in Section 5, so the two sections contradicted each other.

**Falls.** The traced surface chasm trigger is the fixed Britannia coordinate
`(54, 138)`. Stepping onto that falls cell triggers the
fall-into-the-underworld handler: print a banner, run the Dexterity-gated
one-point damage check described in `systems/overworld.md`, restore the
pre-fall transport marker after the presentation clear, swap the world plane,
and re-initialise the active-object table. This falls cell is the only outdoor
cell in either plane that swaps the world plane when the party steps onto it,
and it is a coordinate, not a tile class: the shipped surface map stores an
ordinary water tile at that coordinate, with the waterfall tile in the cell
directly north of it, so
there is no distinct "chasm" tile id to look up and an implementation must key
the fall on the coordinate. The only other outdoor terrain byte that can change
the plane is the live moongate cell, which copies whatever plane its saved
Moonstone slot records; every remaining transition is an active object
(whirlpool) or a scene exit (town-family exit, dungeon exit) rather than an
outdoor terrain trigger.
The full closed inventory is published in `systems/overworld.md` Section 2 and
`catalogs/gazetteer.md` Section 8.3.

**Outdoor ascents.** There are none, and this is settled rather than pending: no Underworld terrain tile lifts the party to the surface. Preserve candidate special tiles as tile identities, but do not assign an ascent contract to any of them. The routes back up are a dungeon's top exit, a moongate or Gate Travel to a surface Moonstone slot, and a saved-position reload; `catalogs/gazetteer.md` Section 8.3 carries the closed inventory.

**Moongate cells.** Terrain byte `0xDC` is LOOK2-named as a moon
gate and is accepted by movement and local-light systems as
moon-gate-family state. Saved Moonstone slots drive the live-terrain
placement and waning schedule, and that terrain byte is the whole of a gate's
presentation - there is no separate frame plate and no animator. General
underfoot entry is specified in `systems/overworld.md`; this catalog only names
storage-domain semantics. The `0x80..0x87` special range is a
pendulum/restraint/grate/archway fixture range in the LOOK2-backed catalog, not
the traced natural-moongate terrain byte; do not infer teleport behavior from a
tile id merely because the tile reads as gate-like artwork.

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

**Dungeon-entrance seal pair.** Four overworld tile ids form the Word-of-Power
seal family, and an implementation needs their identities because the Yell path
and the region-load pass swap between them:

| Tile id | Look name | Passable | Role |
|---:|---|---|---|
| `0x16` | a dark cave | yes | Unsealed entrance variant used by Despise, Destard, and Doom. |
| `0x17` | an abandoned mine | yes | Unsealed entrance variant used by Shame and Hythloth. |
| `0x18` | a dungeon | yes | Unsealed entrance variant used by Deceit, Wrong, and Covetous. |
| `0xDF` | the collapsed entrance to the dungeon | no | The single sealed form shared by all eight entrances. |

The shipped world maps store only the unsealed variants. The sealed form is
written into the live view at region-load time for every entrance whose word is
still unspoken, and the Yell path toggles a single cell between the two forms.
Because the sealed form is impassable, a sealed entrance cannot be stood on and
therefore cannot be entered. `systems/commands.md` Section 11 owns the
behaviour.

The shrine pair works the same way: `0x19` ("a mystic shrine", passable) is
rewritten to `0x1A` ("a ruined shrine", impassable) for any shrine whose saved
ruin flag is set. The Eternal Flame fixture inside the three flame keeps is a
separate impassable special tile; the party stands beside it rather than on it.

The ids in the two paragraphs above are hexadecimal. Section 3's coarse range
partition is written in decimal and does not resolve this band correctly: it
assigns decimal `16..23` to paved-path art and `24..47` to walls, but decimal
`22`, `23`, and `24` are the three dungeon-entrance variants named here,
decimal `25` and `26` are the shrine pair, and decimal `27` is a lighthouse.
Where the coarse partition and a named-tile row disagree, the named row is
authoritative; the partition is a working summary of art families, not a
per-id table.

**Water/current effects.** The traced overworld contract does not publish a
general player-facing waterfall/current sweep. Treat water-like terrain as
ordinary transport-specific passability unless a mode spec names a concrete
handler. The currently promoted outdoor forced-water transition is the
whirlpool active-object engagement in `systems/overworld.md`; the fixed
surface falls/chasm is coordinate-triggered, not a water-tile sweep.

No `world_waterfalls.tsv` runtime sidecar is part of the promoted baseline.

**Ladders / staircases.** In town mode, facing-sensitive stairway tiles are the `0xC4..0xC7` family. The low two bits are a facing selector in the town movement wrapper's normalized direction space: entering along that facing goes up one floor, entering from the opposite facing goes down one floor, and side crossings leave the current floor unchanged. K-Klimb ladders and trapdoors use the same floor-reload machinery after their own underfoot command checks. In dungeon mode, ladders are encoded in the tile byte's high nibble and handled by the dungeon turn loop's K-Klimb branch.

**Doors.** Any door tile (indices `96..103`) blocks movement when closed and dispatches the door-interaction handler. The handler maps to O-Open (key for locked doors), J-Jimmy (lockpick), or dispel (the An Sanct / In Ex Por spells).

**Chests.** Stepping onto a chest tile triggers G-Get. The handler may prompt for a key on locked chests, apply a random trap, and either yield treasure or print "Nothing of note".

**Signs.** Sign-post tiles trigger the read-sign handler — a sign sub-table in `SIGNS.DAT` is indexed by per-location coord.

**Beds.** A bed tile in an inn enables H-Hole-up. Outside an inn or off a bed, H prints "Not here!" and consumes no turn. The hours/rest contract is in `systems/rest-and-camp.md`.

**Trapdoor / town step trigger `0x8C`.** Stepping onto live town tile `0x8C`
runs the town step-interaction handler. Its **general** arm prints
"A TRAPDOOR!" and drops the party one floor, and that is what happens in every
location but one; the arm is skipped entirely while the party is on the magic
carpet. Stonegate is the single exception, keyed on that scene byte alone: its
trapdoor ring runs a scripted party-death sequence instead of a floor change.
Earlier wording here presented the scripted arm as the general behaviour and
the descent as the special case; that is backwards and is withdrawn. See
`systems/town-mode.md` Section 3.

The shipped description table names `0x8C` a loose brick, not a chair; ordinary
seat tiles are `0x90..0x93` and carry no step trigger. Do not conflate `0x8C`
with the paired NPC floor-link markers `0xC8` and `0xC9` either.

**Floor-link markers `0xC8` and `0xC9`.** Two marker bytes appear in town tile
grids as authored floor links. They share one description string in the shipped
description table, so a Look at either reports the same thing, but they are
directional and are not interchangeable:

| Tile id | Role | Effect of climbing while standing on it |
|---|---|---|
| `0xC8` | Ascend link | Floor index increases by one. |
| `0xC9` | Descend link | Floor index decreases by one. |

Tile `0x86`, the metal grate, shares the descend behaviour under the player's
climb command, and in one keep it stands in for the descend link at the exact
cell where the floor below carries the ascend link. There is no two-way link
cell in town mode: the climb command never prompts up-or-down there. The
NPC scheduler consumes the same two bytes: when schedule movement must bridge
floors it searches the live tile buffer for cells carrying whichever marker
points toward the floor that is not currently displayed, and uses those cells as
pathfinding goals. `systems/npc-schedules.md` Section 8.5 owns that selection
rule. For NPC routing these ids are ordinary open ground, exactly like the
stairway family they sit beside; what is special about them is only that the
scheduler's tile-ID search mode additionally stamps them as goal cells. They
remain distinct ids from the visible stairway family `0xC4..0xC7` and must not
be folded into it.

**Telescopes.** Tile `0x59` is a telescope: a light tube on a splayed tripod.
It is a Look trigger, not a step trigger, and looking at one shows the sky
rather than any kind of map — the sun by day, at the cost of one point of damage
to the active party member, and a moving star field at night.
`systems/view.md` Sections 3 and 4.2 own the full contract. Two labels that were
previously attached to this id are withdrawn: it is **not** a wishing well (that
is the separate tile `0xA1` below, which has its own handler and its own
description), and its Look path is **not** the gem's View command or any
Britannia overview map. It has no gem or item precondition of any kind. Exactly
three telescopes are placed in shipped data, all indoors: in Moonglow, in Skara
Brae, and in West Britanny. A third label is withdrawn with them: the transition
specs formerly read this id as the "town-family exit threshold" tile. It is not,
and an id occurring in three interior cells could not line any location's
boundary; town-family locations are left by stepping off the edge of the
interior grid, as `systems/town-mode.md` Section 15 and
`systems/doors-and-z-transitions.md` Section 12 now state.

**Wishing-wells, springs, caves.** The deep-well tile `0xA1` is a Look trigger, not a step trigger: looking at it runs the coin-and-wish handler whose six accepted words are the Easter-egg list "Corvette / Ferrari / Lamborghini / Lotus / Porsche / Horse". In the two granting scenes every accepted word creates the same horse-family active object, so the older "wish for a vehicle" framing is a misnomer. `systems/view.md` Section 3 owns the full contract. Springs restore MP; caves drop a chest.

**Camp / fire.** Camp tiles and brazier tiles trigger the camp-and-rest handler when H-Hole-up is invoked on them. Outdoor rest and the rare camp-event level-up live in `systems/rest-and-camp.md`.

The per-mode *walk loop* trigger set above (what happens when the party steps
onto a tile) is documented case by case rather than as one free-standing table,
because each case belongs to a different mode spec. The *inspection* trigger set
is different and is now published in full: `systems/view.md` Section 3 carries a
"Top-down Look special cases" table giving each tile id and object class that
diverts the overworld/town Look command away from the plain description path,
together with the order in which the dispatcher tests them.

## 7. Monster tiles

Monster sprites occupy the **top** of the actor half, indices `384..511`. Each
monster — sea horse, squid, sea serpent, shark, giant rat, bat, giant spider,
ghost, slime, gremlin, mimic, reaper, gazer, crawler, gargoyle, insect swarm,
orc, skeleton, python, ettin, headless, wisp, daemon, dragon, sand trap, troll,
mongbat, corpser, rot worm, shadow lord — owns four sequential indices, one per
facing or animation phase.

The band follows from two published rules rather than from the provisional
range table in Section 3. A combat class's stored actor byte is
`class * 4 + 0x40` (`catalogs/monster-bestiary.md` sprite-run column), and the
renderer adds `256` to an actor byte before indexing this catalogue
(Section 3.1). The bestiary classes are `16..47`, so their actor bytes run
`0x80..0xFF` and their catalogue indices run `384..511` — Sea Horse (class 16)
at `384..387` through Shadow Lord (class 47) at `508..511`. The same arithmetic
reproduces the two ids Section 3.1 confirmed directly from the shipped art:
the four party classes `0..3` land at `320..335`, and Lord British (class 15)
lands at `380..383`.

An earlier revision of this section put monsters at `256..383`, matching the
Section 3 nominal rows. That is withdrawn: it is the same band Section 3.1
already withdrew for holding person sprites, and it is exactly `128` low, which
is the signature of reading a monster's actor byte as though the actor half
began at the monster runs rather than at actor byte zero.

Cross-reference: `catalogs/monster-bestiary.md` for per-monster stats, AI archetype, encounter rate per terrain, and the singular and plural display names from the resident data string tables.

Monsters appear in two contexts:

- **Wandering encounters.** The encounter spawner picks a monster class based on the current world-tile class and party state, and writes a fresh active-object slot.
- **Combat arenas.** When combat starts, each spawned actor's starting tile id
  follows from its combat class (tile id `class * 4 + 0x40` in the
  active-object sprite domain); the combat actor table tracks frame state per
  actor. Early spawn slots may roll the base class's **companion class** —
  another class id, from the per-class companion table in
  `catalogs/monster-bestiary.md` — and the substituted class then determines the
  tile. There is no per-arena replacement-*tile* table; earlier drafts that
  described one were wrong.

Hostile humans (brigands, pirates, hostile guards) sit in the *NPC* range, not the monster range. The combat system distinguishes them for damage and loot, but the tile space treats them as NPC-class.

## 8. NPC tiles

NPC sprites occupy indices `192..255`. Each NPC type — villager, merchant, jester, child, beggar, guard, wanderer, named NPCs (Lord British, Blackthorn, named ship captains), shadow lords — owns one or more indices, typically two frames per facing for an idle / walk cycle.

Cross-reference: `catalogs/npc-roster.md` for per-NPC names, dialogue file links, default schedules, and which location each NPC lives in. The role-name strings ("Avatar", "Villager", "Merchant", "Jester", "Bard", "Child", "Beggar", "Guard", "Wanderer", "Blackthorn", "Lord British") in the resident data anchor the partition.

NPCs appear only in town mode and in scripted overworld events. The active-object table records the current sprite tile id directly; the per-tick walker advances the schedule and updates the position and sprite fields.

A pre-conversation gate runs before the dialogue engine, but it does **not**
inspect an NPC sprite id. It reads the live **map tile** occupying the cell the
Talk command resolved to, and the two ids it tests are furniture ids in the
`LOOK2.DAT` terrain-description domain, not actor sprites. Exactly two ids
divert the command:

| Live map tile at the resolved cell | Shipped description | Talk result |
|---|---|---|
| `0x9D` | a mirror | The "no response" line; the conversation engine is not entered. |
| `0xAB` | a bed | The sleeping line; the conversation engine is not entered. |

Every other value falls through to normal conversation entry. The full gate
contract, including where it sits relative to shop-trigger and dialogue-index
dispatch, is in `systems/conversation.md` Section 2.

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

- **Moongate frames.** *None exist.* An earlier revision of this catalog listed
  a bespoke transient frame plate driven by an overworld moongate animator and
  selected by that animator's phase counter. Both the plate and the animator are
  withdrawn: a natural gate is the live terrain byte `0xDC`, written and removed
  by the saved-slot refresh and drawn by the ordinary renderer. The
  sixteen-position cycle that reading described belongs to the night-time light
  beacon in `systems/visibility.md` Section 12.6.
- **Projectile frames.** Arrow, axe, sling, magic missile sprites in flight. The combat handler walks a projectile from caster to target one cell per render frame.
- **Splash / explosion / impact.** Multi-frame sprites for fireball impact, lightning hit, explosion clouds, smoke. The effect handler runs through the frames and clears.
- **Fields.** Fire field, poison field, sleep field, energy field, electric field. Dungeon field placement writes the field terrain bytes documented in `systems/magic.md` into the live dungeon image, optionally preserving the dungeon visit marker bit. Combat arena fields are handled by the arena-field helper instead of direct dungeon terrain writes; contact is checked after a successful step commits, then routes to the per-field status or damage/value helper.
- **Wind / smoke / sparkle.** Atmospheric and transient effect graphics driven by weather, storm, and spell handlers. The wind/gust graphics are tile-atlas effects; baseline dungeon contact handling does not use them as `DUNGEON.DAT` torch-extinguishing cells.

Several effect tiles double as world-tile sentinels in the special class range, so renderers should keep map-cell field bytes and transient combat-field visuals in the same semantic family even when their storage paths differ. **Correction:** an earlier revision added that "the animator that sweeps live tile buffer for animated-static cells handles dungeon field tiles uniformly: each owns a four-frame run, and the animator advances it." That is withdrawn on both counts — there is no live-tile-buffer sweep (Section 4), and no field id is in the five families that animator advances. Field frame cycling, where it happens, belongs to the per-effect handlers.

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

- **Dungeon tiles.** Dungeon `.DAT` cells pack two four-bit fields: high nibble is a strict dungeon tile class (open, wall, door, ladder, chest, trap, fountain, field), low nibble is class-specific attribute. Dungeon tile bytes are *not* indices into the unified five-hundred-and-twelve-tile space and do not share the world/town high-nibble buckets — they are a separate dungeon tile-class encoding rendered by the billboard first-person dungeon renderer.
- **Combat arenas.** Combat `.CBT` terrain cells use standard one-byte tile ids in an eleven-by-eleven grid with a thirty-two-byte row stride. The twenty-one bytes after each terrain row are arena metadata and must be preserved. For `BRIT.CBT`, traced setup copies the party-entry and placement-slot coordinate slices from that metadata into resident tables; spawn counts and companion-class rolls still come from resident per-class combat tables, keyed by combat class id rather than by arena index.
- **Markers in town maps.** Marker bytes — NPC start markers `0x48`/`0x49`, spawn marker `0x2A`, dawn/dusk archway marker `0x87`, and the NPC floor-link markers `0xC8`/`0xC9` — appear in on-disk tile grids and are consumed by location-load or NPC-scheduler passes. Some are harvested into runtime state, some are conditionally rewritten in the runtime tile buffer, and `0xC8`/`0xC9` remain queryable as runtime tile-ID goals. They should not be treated as ordinary terrain. The standing-crop and fruit-tree terrain values `0x2D`/`0x2E` were previously listed here as markers; they are not. They are ordinary named terrain. In the one settlement that is currently hiding a living Shadowlord — and nowhere else — a load-time blight pass thins them into their plowed-patch and hollow-stump counterparts (`0x2C` and `0x2B`) seven times in eight, on a stream keyed to the calendar day; see `systems/town-mode.md` section 3 for the gate. For the dawn/dusk pass, `0x87` marks the south-adjacent gate cell; shipped maps pair it with `0x44` cobble, which toggles to `0x99` portcullis via XOR `0xDD` at night.

## 13. Graphics-asset encoding

The tile sprite sheet ships in two parallel files — `TILES.16` for sixteen-color EGA and `TILES.4` for four-color CGA — each holding the same five hundred and twelve sprites at the appropriate depth. Both files are LZW-wrapped; after decompression each is a flat array of sprite bytes with no per-tile header.

The EGA file decompresses to exactly sixty-five thousand five hundred and thirty-six bytes — five hundred and twelve sprites at one hundred and twenty-eight bytes each. Each sprite is sixteen rows of eight bytes; each byte holds two pixels high-nibble first; each four-bit value indexes the sixteen-entry palette the display driver installs at mode setup — the stock set for the mode, with index six substituted to dark yellow (`formats/tiles.md` section 7).

The CGA file decompresses to thirty-two thousand seven hundred and sixty-eight bytes — five hundred and twelve sprites at sixty-four bytes each. Each sprite is sixteen rows of four bytes; each byte holds four pixels MSB-first; each two-bit value indexes the four-colour CGA sub-palette the CGA driver fixes at mode setup — black, cyan, magenta, white at low intensity. That choice is made once and never varies by scene; see `formats/tiles.md` section 7.

To address a tile by id, the renderer multiplies the id by the per-tile byte size. There are no offsets, no inner directory, no per-tile headers — tile id alone is the file offset divided by the tile byte size. This is the simplest of the LZW-wrapped graphics families.

Palettes are not stored in the file. The sixteen-entry set for the EGA-class path lives in the resident screen descriptor and is loaded into the adapter once at mode setup; the four-entry CGA set is fixed at mode setup as well. Neither changes at scene-init time or at any other point in the run. The driver overlays (`EGA.DRV`, `CGA.DRV`, `T1K.DRV`, `HER.DRV`) handle palette and blit.

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
- Source provenance: derived from private analysis note
  `u5-decomp/notes/presentation_endgame_chargen_u4_2026-08-22.md` - the
  companion-band compositor write, the renderer's zero-grid-cell branch, the
  `+256` actor index rule and its one reserved transparent value, together
  with the seven actor-half sprite identities confirmed by decoding the
  shipped atlas with this document's own container rules.
- The special-trigger comparisons in the per-mode walk loops.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/scene_floor_page_table_2026-08-22.md` - the trapdoor
  `0x8C` step handler's general descend arm with its single scripted
  exception, the magic-carpet suppression, and the metal grate `0x86`
  standing in for a descend link opposite an ascend link on the floor below.
- The marker-byte consumers (NPC start markers, waypoint markers, dawn/dusk archway marker `0x87`, and the NPC floor-link markers `0xC8` and `0xC9`).
- The two-nibble dungeon tile encoding and its separate tile-class space.
- Source provenance: the telescope identity of tile `0x59`, its three shipped
  placements, the separation from the wishing-well tile `0xA1`, and the
  withdrawal of the moongate-animation plate are derived from private analysis
  notes `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md` and
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.

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
- **Actor and vehicle tiles (~220 tiles, indices `160..383`).** Vehicle and NPC
  ranges are established by the animator's class-range tests and by their owning
  movement and roster catalogs, and the person sprites confirmed from the
  shipped art sit at the top of this span (Section 3.1). The bestiary's monster
  runs are *not* in this span; they resolve above it (Section 7). Exact
  sprite-frame labels inside a run are renderer/catalog attribution unless a
  system spec names a tile id as a gameplay gate.
- **Upper actor-half tiles (~130 tiles, indices `384..511`).** This is the band
  the bestiary's combat classes resolve into once the renderer's actor-byte rule
  is applied (Section 7). The "item, effect, and avatar" labels Sections 2 and 3
  give these indices are nominal and provisional (Section 3.1); the item,
  inventory, magic, combat, command, and presentation specs cover the gameplay
  consumers of that art wherever its indices finally land. Remaining per-frame
  art labels, pixel ordering checks, and render-only sentinel names are
  presentation/catalog QA, not unresolved command ownership.

All five hundred and twelve indices have a class assignment and storage-domain
contract. The tile catalog is complete for passability, LOOK2 ownership,
special-trigger routing, active-object classing, and file-format boundaries.

**Qualification.** The three bullets above describe the *class assignment*, not
the per-range visual names. Section 3.1 withdraws several of those names and
publishes the actor-half indexing rule that governs how an actor's stored byte
reaches this catalogue; read it before using any range label above index 128 as
a predicate.

## 15. Cross-references

- `systems/movement.md` - Shared movement and passability predicate, including
  the resident terrain bitset, caller-query dispatcher, vehicle layer, dynamic
  occupancy, and commit rules.
- `systems/overworld.md` — Overworld mode specification, including the active-object animator, the per-turn tile probe, and the once-per-turn moongate terrain refresh. Section 8 lists the special tile classes the per-turn block recognises.
- `systems/town-mode.md` — Town-mode specification, including marker harvest/runtime marker handling (Section 3 / Section 6), the dawn/dusk gate substitution (Section 6), and the per-tile interaction commands (Section 9).
- `systems/dungeon-mode.md` — Dungeon-mode specification, including the two-nibble dungeon tile encoding (Section 4) and the first-person renderer's cell-class-to-image mapping (Section 6.4).
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

0. **Re-catalogue the nominal index ranges of Sections 2 and 3 against the
   shipped atlas.** Section 3.1 shows both halves' nominal names are wrong in
   places — the actor half's `320..335` and `368..383` bands are person sprites
   rather than monsters, and the terrain half's `192..255` band is scenery and
   fixtures rather than NPCs. This is the highest-value item in this queue,
   because engine code that resolves a tile id by range rather than by
   confirmed id will mislabel actors.
1. Refine the per-tile id within each monster's frame run by walking `MON0.16` through `MON7.16` against the manual's monster list and the resident data monster-name pool.
2. Refine the per-NPC tile-id labels against the role-name string pool ("Avatar", "Villager", ..., "Lord British") and the named-NPC list.
3. Refine the per-item tile-id labels against the item-name pool and the Z-stats inventory panel.
4. Keep marker-byte catalog labels aligned with their owning systems: location
   loading owns NPC start and conditional rewrite markers, while the NPC
   scheduler owns the `0xC8`/`0xC9` floor-link goal markers.
5. Check any remaining visual edge cases around local-light writer order and
   special runtime stamps; the core propagation-blocker list and beacon-mask
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
