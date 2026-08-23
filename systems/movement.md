# Movement And Passability

## 1. Scope

This spec describes the shared movement contract behind the player and actor
walk loops. It covers command-to-direction routing, destination sampling,
terrain passability, dynamic-object collision, movement commit, and mode-owned
post-step effects.

It does not replace the mode specs. Overworld chunk loading, town NPC
scheduling, dungeon first-person rendering, combat rounds, vehicles, time
cleanup, and special tile effects remain owned by their dedicated specs. This
document is the compatibility layer those systems share.

## 2. Direction Input

The input system translates cursor and keypad movement keys into compact
direction codes before mode loops see them. World and town movement consume the
four cardinal directions only: west, east, north, and south. Diagonal codes
exist in the input vocabulary, but the only consumer that treats one as a
movement is the combat targeting cursor; elsewhere they page full-screen lists
or are refused. No mode steps diagonally.

The stationary keypad centre / pass input is not a movement command. It can be
meaningful inside prompts such as spell direction selection, but it must not
move the party or actor in world, town, dungeon, or combat movement.

Each active mode handles movement before the resident A-Z command dispatcher:

- **Overworld.** Cardinal movement attempts a step or vehicle move in the
  256-by-256 world plane.
- **Town.** Cardinal movement attempts a step in the current 32-by-32 location
  floor.
- **Dungeon.** Movement is first-person and relative to the current facing:
  turn left/right, step forward/back, and process dungeon cell effects.
- **Combat.** Cardinal movement is an actor turn primitive: a legal empty
  target cell is a step, while a hostile occupied cell becomes an attack.

Letter commands and non-movement controls fall through to the mode's ordinary
command dispatcher only after this movement layer declines them.

## 3. Destination Sampling

Every movement attempt starts by deriving a candidate destination from the
current mode:

| Mode | Source grid | Candidate cell |
|------|-------------|----------------|
| Overworld | The 32-by-32 live chunk window over `BRIT.DAT` or `UNDER.DAT` | Party X/Y plus cardinal delta, wrapping in the 256-by-256 plane where the world rules allow it |
| Town | The loaded 32-by-32 location floor | Avatar X/Y plus cardinal delta on the current floor |
| Dungeon | The loaded packed dungeon record and current level | A relative cell in front of or behind the party, or a facing change with no cell step |
| Combat | The loaded 11-by-11 arena runtime grid | Actor X/Y plus cardinal delta, with edge cells able to flee combat |

The sampled cell supplies the static terrain input to passability. Dynamic
actors, vehicles, items, and projectiles are tested separately through active
object or combat actor records.

## 4. Static Terrain Predicate

World and town terrain use a resident tile-query dispatcher over map tile ids
`0..255`. Tile ids above that range are dynamic sprites or effects and are not
static map cells.

The base terrain predicate uses a thirty-two-byte bitset grouped by tile-id
family. The byte selected by `tile_id >> 3` contains one bit for each of eight
tile ids, read most-significant first. A set bit rejects that tile for the base
predicate; a clear bit accepts it. The moving class is not encoded as a column
inside this bitset.

Caller-specific behavior is selected by a separate query predicate table keyed by
the caller's class/query byte. Movement callers usually derive that byte from
the avatar, vehicle, or active-object type. The selected predicate may use the
base bitset, a low-tile/water-family predicate, a fixed-id check, or an
auxiliary per-tile mask.

Compatibility rules:

- Treat the bitset as a base tile-family rule, not as a single universal
  "walkable" flag and not as the older per-mover matrix model.
- Keep caller query identities data-driven. The vehicle, on-foot, and known
  active-object predicate families below are named; query families not listed
  here remain opaque until their callers are promoted.
- Preserve the known base-predicate edge: tile ids `0x90..0x93` are
  force-rejected for most query classes even when their base bit is clear. The
  force-reject is skipped for the foot/avatar query family and the `0x40`
  query family.
- Runtime tile-state changes should change the live tile id. The mask itself
  is read-only during play.

These ids are tile ids, not private addresses. Their exact authored tile names
remain with `catalogs/tile-catalog.md`.

Known top-down movement query families:

| Caller query family | Public meaning | Static terrain predicate family |
|---|---|---|
| `0x10..0x13` | Mounted horse | Base bitset, then rejects two additional authored tile ids. |
| `0x14..0x17` | Magic carpet | Accepts the special static door/portal-family run, then the glyph-family predicate, then the base bitset. |
| `0x1C..0x1F` | On-foot avatar or party leader | Base bitset. Movement callers pass the masked family query, so all foot facings share this predicate and skip the `0x90..0x93` force-reject edge. |
| `0x20..0x23` | Ship under sail | Accepts only the low water/sentinel tile-id family used by ship travel. |
| `0x24..0x27` | Furled or manually handled ship | Same static terrain predicate as the under-sail ship family; sail state changes cadence and X-Xit behavior, not the ship's ordinary terrain query. |
| `0x28..0x2B` | Skiff | Uses the skiff/water predicate family, combining a small authored tile-id family, the glyph-family predicate, and auxiliary per-tile masks. |

The table above names the caller-side query families as the dispatcher sees
them, four values wide because the dispatcher matches on the family run rather
than on a single facing. It is not a list of transport-marker values the party
can actually hold: the horse and the carpet occupy only two of their four
values, and only one of the on-foot values is ever written.
`systems/vehicles.md` section 2 gives the complete persistent marker set.

The table above names the caller-side query families and predicate shapes. The
following table gives the exact accepted map-tile ranges for those named
queries and summarizes their LOOK2-derived descriptions; broader per-tile art
verification remains catalog work.

For byte-compatible world/town movement, the named vehicle and foot queries
accept the following static map tile ids before dynamic occupancy is checked:

| Query family | Accepted static tile ids | LOOK2-derived descriptions |
|---|---|---|
| Foot/avatar | `0x00`, `0x04..0x0B`, `0x0E..0x19`, `0x1B`, `0x1D..0x26`, `0x2C..0x2D`, `0x30..0x37`, `0x39`, `0x3E`, `0x40`, `0x44..0x45`, `0x47..0x49`, `0x6A..0x6B`, `0x86..0x87`, `0x8C`, `0x8F..0x93`, `0xAA..0xAC`, `0xBC`, `0xC4..0xC9`, `0xDC..0xDD`, `0xF9`, `0xFF` | Sentinel/darkness cells, swamp/grass/brush/desert/trees/forest/foothills, settlements and entrances, bridge/road/pier/cobble/planks, crops, selected grates/archways/loose brick, lava/chairs, carpet/bed/fireplace, stairs/ladders, moon gate, shipwright sign. |
| Mounted horse | `0x00`, `0x05..0x0B`, `0x0E..0x19`, `0x1B`, `0x1D..0x26`, `0x2C..0x2D`, `0x30..0x37`, `0x39`, `0x3E`, `0x40`, `0x44..0x45`, `0x47..0x49`, `0x6A..0x6B`, `0x86..0x87`, `0x8C`, `0xAA..0xAC`, `0xBC`, `0xC4..0xC9`, `0xDC..0xDD`, `0xF9`, `0xFF` | Foot-like land and structure set, but excluding the foot-only swamp and the lava/chair compatibility-edge ids. |
| Magic carpet | `0x00..0x0B`, `0x0E..0x19`, `0x1B`, `0x1D..0x26`, `0x2C..0x2D`, `0x30..0x37`, `0x39`, `0x3E`, `0x40`, `0x44..0x45`, `0x47..0x49`, `0x60..0x6F`, `0x86..0x87`, `0x8C`, `0x8F`, `0xAA..0xAC`, `0xBC`, `0xC4..0xC9`, `0xDC..0xDD`, `0xF9`, `0xFF` | Foot-like land and structure set plus deep water/water/shoals, river and bridge variants, and molten lava; still excludes the chair compatibility-edge ids. |
| Ship, under sail or furled/manual | `0x00..0x02` | Sentinel plus deep-water/water tile ids. Sail state changes timing and exit rules, not the static terrain query. |
| Skiff north-facing query | `0x00..0x03`, `0x36..0x37`, `0x60`, `0x63..0x64`, `0x66..0x68`, `0x6A`, `0x6C` | Sentinel, deep water, water, shoals, selected shoreline grass, selected river/bridge variants. |
| Skiff east-facing query | `0x00..0x03`, `0x34`, `0x37`, `0x61`, `0x64..0x65`, `0x67..0x69`, `0x6B`, `0x6D` | Sentinel, deep water, water, shoals, selected shoreline grass, selected river/bridge variants. |
| Skiff south-facing query | `0x00..0x03`, `0x34..0x35`, `0x60`, `0x62`, `0x65..0x66`, `0x68..0x6A`, `0x6E` | Sentinel, deep water, water, shoals, selected shoreline grass, selected river/bridge variants. |
| Skiff west-facing query | `0x00..0x03`, `0x35..0x36`, `0x61..0x63`, `0x66..0x67`, `0x69`, `0x6B`, `0x6F` | Sentinel, deep water, water, shoals, selected shoreline grass, selected river/bridge variants. |

The skiff query is facing-sensitive because the low two bits of the skiff
transport marker select directional shoreline and river masks. The accepted
neighbour rule used by X-Xit is separate: it asks the foot/avatar query for
nearby terrain support and also accepts selected rendered companion sprites.

The named compatibility edge in the table is intentional: the on-foot query
accepts LOOK2 tile `0x8F` ("molten lava") and chair variants `0x90..0x93`,
while the horse and magic-carpet queries reject at least the chair variants.
Callers that do not use the on-foot exception continue to force-reject the
chair run even though the base bitset alone would otherwise allow it.

Additional non-vehicle query families are promoted at predicate-family depth.
Many of their sprite-run names are owned by `systems/encounters.md` and
`catalogs/monster-bestiary.md`; the movement contract here is the terrain
predicate each family uses while an outdoor active object is trying to step:

| Query family | Public role | Static terrain predicate family |
|---|---|---|
| `0x2C..0x2F` | Water-creature / pirate-ship active-object movement | Same `0x00..0x02` water/sentinel predicate as ships. |
| `0x70..0x7F` | Guard, Wanderer, Blackthorn, and Lord British combat/NPC-class sprite runs. | Guard and Blackthorn use the base predicate; Wanderer and Lord British use the carpet-like composite predicate. |
| `0x80..0x8F` | Sea Horse, Squid, Sea Serpent, and Shark sprite runs. | Glyph-restricted predicate: only the very-low ids and `0x60..0x6F` glyph/river family. |
| `0x90..0x9F` | Giant Rat, Bat, Giant Spider, and Ghost sprite runs. | Giant Rat and Giant Spider use the base predicate; Bat uses the carpet-like composite predicate; Ghost uses the glyph-restricted predicate. |
| `0xA0..0xBF` | Slime, Gremlin, Mimic, Reaper, Gazer, Crawler, Gargoyle, and Insect Swarm sprite runs. | Slime, Gremlin, Mimic, Reaper, Crawler, Gargoyle, and Insect Swarm use the base predicate; Gazer uses the carpet-like composite predicate. |
| `0xC0..0xD7` | Orc, Skeleton, Python, Ettin, Headless, and Wisp sprite runs. | Base bitset predicate, with the documented `0x90..0x93` force-reject edge. |
| `0xD8..0xDF` | Daemon and Dragon sprite runs. | Carpet-like composite predicate. |
| `0xE0..0xE3` | **Sand Trap sprite run** (`catalogs/monster-bestiary.md` class 40) in both domains. *Corrected:* an earlier revision said "outdoor sea-serpent adjacency family in the overworld active-object domain; Sand Trap in the combat class table". **That domain split is withdrawn — there is none.** The Sea Serpent run is `0x80..0x8F`'s `0x88..0x8B`, listed above. | Accepts only tile id `0x07`, which the terrain catalogue names parched desert — itself corroborating the Sand Trap identity. |
| `0xE4..0xE7` | Troll sprite run. | Base bitset predicate, with the documented `0x90..0x93` force-reject edge. |
| `0xE8..0xEB` | Immobile or never-pass family; no promoted ordinary mover identity. | Rejects every static tile. |
| `0xEC..0xEF` | Outdoor whirlpool / forced-underworld animated family. | Accepts only tile id `0x01`. |
| `0xF0..0xF3` | Mongbat sprite run. | Carpet-like composite predicate. |
| `0xF4..0xF7` | Corpser sprite run. | Accepts only tile id `0x05`. |
| `0xF8..0xFB` | Rot Worm sprite run. | Accepts only tile id `0x04`. |
| `0xFC..0xFF` | Shadow Lord sprite run, which is also the quest-sprite defensive branch family. | Glyph-restricted predicate: only the very-low ids and `0x60..0x6F` glyph/river family. |
| Other non-vehicle families using the base predicate | Generic active-object / interaction movement with no promoted art name at this layer. | Base bitset predicate, with the documented `0x90..0x93` force-reject edge unless the query is in an exception family. |

## 5. Tile-Class Dispatcher

A second resident tile-class dispatcher classifies map tile ids for gameplay
queries that are broader than "can this mover stand here?" It maps the supplied
caller class/query byte to a predicate family, then tests the tile id against
that selected predicate.

Publicly visible uses include movement and interaction decisions such as
passability, door/stair/exit-style tile categories, special underfoot effects,
and command-specific probes. The dispatcher is a semantic classifier; public
specs should not model it as private control-flow machinery or publish its raw
table contents.

Compatibility rules:

- A caller must pass both a tile id and the caller's class/query id.
- Some predicates delegate to the base tile bitset.
- Some predicates test a fixed tile id or a small tile-id family.
- Some predicates combine a tile-family rule with a caller class.
- Unknown or unlisted class/query ids should remain opaque until their callers
  are promoted into public prose.

## 6. Vehicle Layer

Vehicles layer on top of static terrain passability. The active transport
marker determines whether the party is on foot, riding a horse or carpet,
aboard a ship, in a skiff, or in another vehicle family.

The high-level rules are:

- Foot and horse travel use land-oriented terrain classes and reject ordinary
  water.
- Ships and skiffs require water-compatible terrain; their exact shallow/deep
  distinctions remain with `systems/vehicles.md`.
- Magic carpets bypass some ordinary water/terrain restrictions but still
  respect blocked families such as walls and other hard barriers.
- Balloons are an identified vehicle art family, but the traced movement,
  B-Board, X-Xit, U-Use, and shipwright contracts do not publish a live balloon
  transport marker, boarding path, landing rule, or drift rule for the analyzed
  baseline. Do not infer passability or movement from the art family alone.
- Ship movement with sails hoisted is wind-cadenced; the wind system owns that
  timing and direction contract.

Vehicle exiting uses a narrower nearby-support probe rather than a normal
movement commit. X-Xit checks the four rendered cardinal neighbours around the
party. Visible terrain neighbours are accepted only if they are passable for an
on-foot avatar; selected companion/overlay cells, such as nearby carpet,
party/avatar, horse, manually handled ship, or skiff sprites, also count as
support. A successful X-Xit still parks the abandoned vehicle at the current
party cell rather than moving the party to the accepted neighbour. See
`systems/vehicles.md`.

## 7. Dynamic Occupancy

Static terrain acceptance is not enough to commit a move. The destination must
also be legal with respect to dynamic occupants:

- **Overworld.** Active-object slots represent monsters, vehicles, dropped
  items, and other objects. Stepping into a hostile monster can enter combat;
  stepping onto or adjacent to a vehicle/object may route to a command-specific
  interaction instead of an ordinary move. The outdoor active-object walker uses
  the same tile-class dispatcher for static terrain validation, passing the
  moving slot's type byte as the caller-side class/query. It then uses the
  reverse active-object lookup against the candidate coordinate and current
  world layer; any returned occupant blocks that active-object step.
- **Town.** The NPC roster and active-object table supply collision. A hostile
  adjacent NPC blocks movement and can lead to combat; ordinary NPCs block or
  move according to the schedule/pathfinding rules.
- **Dungeon.** Occupancy is represented by dungeon cell features and mode-local
  triggers rather than by town-style schedule slots.
- **Combat.** The combat actor table is authoritative. A move into an empty
  legal cell commits a step; a move into a hostile occupied cell becomes an
  attack through the combat primitive.

Actor movement and player movement generally use the shared tile-class
dispatcher where they share tile grids, but their dynamic occupancy sources are
mode-specific. Town NPC schedule pathfinding is the known exception: its BFS
workspace uses a dedicated NPC pathfinding bitmap and additional scheduler
rules rather than the foot/avatar terrain-query family. See
`systems/npc-schedules.md`.

## 8. Commit And Redraw

After terrain and occupancy accept the candidate:

1. The mover's coordinate is updated in the mode-owned state.
2. The visible active-object or combat actor descriptor is updated to match.
3. Directional sprite families are rewritten or retagged to face the movement
   direction when the caller owns such a sprite.
4. Visibility, viewport, or map-redraw dirty flags are raised.
5. Mode-specific post-step effects run.

Overworld movement may also cross a chunk-window boundary; when it does, the
overworld chunk loader refreshes the live 32-by-32 world window before the next
viewport rebuild. Town movement remains inside the loaded location floor until
a boundary or floor-transition tile changes the scene or floor. Dungeon movement
may turn without a step, or may step and then fire trap, ladder, room, fountain,
field, or other cell effects. Combat movement charges the actor's turn through
the combat round system.

Actions that fail before commit do not move the actor. Whether they consume a
turn is owned by the caller; ordinary rejected movement is generally a consumed
movement attempt only when the mode explicitly treats the bump or attack as a
turn-taking action.

## 9. Mode Notes

**Overworld.** Movement is party-centric and uses world coordinates, the live
chunk window, active objects, vehicle state, encounter hooks, and underfoot
special tile probes. Time advances by the outdoor turn increment after a
consumed action.

**Town.** Movement is floor-local and shares the location tile buffer with the
NPC scheduler. Each consumed player turn advances time, then runs the schedule
walker once. The player is not represented in the NPC tables; NPC/player
collision comes from the pathfinding workspace, which marks the player's live
cell as an obstacle alongside nearby active objects (`systems/town-mode.md`
Section 8).

**Dungeon.** Movement is first-person. The party's facing is part of movement
state, and turning can be the whole movement action. Dungeon cells use the
packed dungeon encoding, not the world/town resident terrain-query tables.

**Combat.** Movement and melee contact share one primitive. The four cardinal
direction codes map to arena deltas; stepping off a legal edge can leave
combat, while stepping toward a hostile occupied cell attacks instead of
moving.

## 10. Boundaries And Catalog Ownership

The movement contract owns direction routing, destination sampling, static
terrain predicates, dynamic occupancy gates, and commit/redraw ordering. It
does not need final art or sprite catalog names for every generic non-vehicle
query family in order to define passability. Where `catalogs/monster-bestiary.md`,
`catalogs/npc-roster.md`, or interaction specs identify a sprite run, this
document names it; otherwise the query family remains a generic predicate with
the published terrain rule above.

## 11. Sources

This cleanroom spec was derived from private analysis notes and sibling public
specs. It intentionally does not reproduce decompiled code, assembly, raw data
tables, or implementation-specific addresses.

- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/functions/MAINOUT_OVL/`.
- `u5-decomp/functions/NPC_OVL/`.
- Source provenance: the withdrawal of the `0xE0..0xE3` domain split was
  re-derived from the shipped binaries, fixing sprite-run identity two
  independent ways — the shipped description strings for the sprite pages, and
  the published `class * 4 + 0x40` actor-byte rule of
  `catalogs/tile-catalog.md` Section 7 applied to
  `catalogs/monster-bestiary.md` class numbers.
- `u5-decomp/notes/system-trace_movement.md`.
- `systems/overworld.md`.
- `systems/town-mode.md`.
- `systems/dungeon-mode.md`.
- `systems/combat.md`.
- `systems/vehicles.md`.
- `systems/encounters.md`.
- `catalogs/tile-catalog.md`.
- `catalogs/monster-bestiary.md`.
- `formats/look2-dat.md`.
