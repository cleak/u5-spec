# Gazetteer

Cleanroom catalog and implementation contract for Britannia's named travel
locations: settlements, castles, keeps, dwellings, dungeons, shrines, and
fixed overworld landmarks. This is not a map dump. It intentionally does not
publish private coordinate tables, file offsets, raw resident-data records, or
decompiled code.

## 1. Scope

The gazetteer answers "what named place is this, what class of place is it,
what mode or handler should the engine enter, and what other data files belong
to it?" It sits between the world map formats and the runtime mode specs:

- `BRIT.DAT` and `UNDER.DAT` store static terrain.
- Resident location metadata supplies fixed entrance and shrine coordinates,
  scene-byte identities, location names, moongate state, and transition tables.
- Town mode, dungeon mode, shrine meditation, moongate travel, and other
  handlers consume those semantic records.

The catalog is implementation-neutral. A modern engine may store it as JSON,
database rows, hardcoded constants, or authored resources. The required
behaviour is that each fixed place resolves consistently to its class, display
name, destination handler, scene identity where applicable, and validation
rules.

Exact overworld coordinates are out of scope until they are present in an
existing cleanroom spec. The private analysis confirms that the original has
resident coordinate tables for overworld locations and shrines, but this public
catalog names those tables semantically rather than reproducing their raw
contents.

## 2. Location Classes

The engine should distinguish at least these classes:

| Class | Plane | Runtime destination | Data owner |
|---|---|---|---|
| Town | Britannia | Town mode | `TOWNE.DAT`, `TOWNE.NPC`, `TOWNE.TLK` |
| Dwelling | Britannia | Town mode | `DWELLING.DAT`, `DWELLING.NPC`, `DWELLING.TLK` |
| Castle | Britannia | Town mode | `CASTLE.DAT`, `CASTLE.NPC`, `CASTLE.TLK` |
| Keep | Britannia | Town mode | `KEEP.DAT`, `KEEP.NPC`, `KEEP.TLK` |
| Dungeon | Britannia or scripted underworld entry | Dungeon mode | `DUNGEON.DAT`, `DUNGEON.CBT` |
| Shrine | Britannia | Shrine meditation handler | Resident shrine table and virtue/mantra data |
| Moongate | Britannia, with some underworld outcomes | Moongate travel handler | Resident moongate state and time system |
| Plane transition | Britannia or Underworld | Overworld plane swap | Resident transition table and overworld loop |
| Minor landmark | Usually Britannia | Local prompt or effect handler | Tile class plus fixed runtime handler |

Town, dwelling, castle, and keep are one runtime family. They all enter town
mode, use a thirty-two-by-thirty-two tile buffer, load a per-location NPC
roster and dialogue file, and use the same scene-byte partition. The class
mainly selects which three per-class files are opened.

Dungeons are a separate runtime family. They use the first-person dungeon mode,
the eight-by-eight-by-eight dungeon geometry bank, dungeon-specific combat room
lookup, and no town-style NPC schedules.

Shrines, moongates, and plane transitions are overworld landmarks rather than
interior scenes. They may have names and fixed coordinates, but they do not
load a `*.DAT` interior block.

## 3. Scene And Data Keys

Use stable data keys even while human-readable names are still being
confirmed. The preferred key form is:

| Key form | Meaning |
|---|---|
| `TOWNE:n` | Town-family sub-map `n`, where `n` is `0..7`. |
| `DWELLING:n` | Dwelling-family sub-map `n`. |
| `CASTLE:n` | Castle-family sub-map `n`. |
| `KEEP:n` | Keep-family sub-map `n`. |
| `DUNGEON:n` | Dungeon geometry record `n`. |
| `SHRINE:virtue` | Shrine keyed by virtue name. |
| `LANDMARK:name` | Named overworld landmark with no town/dungeon scene. |

For the thirty-two town-mode locations, the scene byte is authoritative:

| Scene byte range | Class | Sub-map key |
|---|---|---|
| `1..8` | Town | `TOWNE:(scene - 1) & 7` |
| `9..16` | Dwelling | `DWELLING:(scene - 1) & 7` |
| `17..24` | Castle | `CASTLE:(scene - 1) & 7` |
| `25..32` | Keep | `KEEP:(scene - 1) & 7` |

Scene byte zero is the overworld. Scene bytes above thirty-two belong to
dungeon and combat states. A gazetteer row for a town-mode location should
therefore carry both its semantic class and its scene byte or class/sub-map key.

## 4. How To Use This Catalog

An engine should use the gazetteer in these places:

1. **Overworld entry.** When the player enters on a fixed location coordinate,
   look up the matching gazetteer row, set the corresponding scene byte, clear
   or reseed active objects as required, and load the destination mode.
2. **Interior exit.** When a town-mode boundary tile clears the scene byte,
   resolve the active scene back to its overworld entry record and restore the
   party to the matching surface location.
3. **Dungeon exit.** When dungeon mode exits from the top level or an
   exit-dungeon cell, resolve the active dungeon to its surface return record.
4. **Shrine meditation.** Resolve the shrine by fixed overworld coordinate or
   shrine tile, then bind it to one virtue, one mantra, and the shrine
   meditation flow.
5. **UI and tooling.** Show display names from the gazetteer, not from
   filenames or sub-map numbers.
6. **Cross-catalog joins.** Join `catalogs/npc-roster.md` rows to place names
   through `FAMILY:n` keys once the sub-map-to-name binding is confirmed.

Do not infer a place from terrain tile alone. Entrance terrain contributes to
the trigger, but the named destination is selected by fixed resident metadata
and the mode's entry rules.

## 5. Town-Mode Location Family

The thirty-two non-overworld interiors are divided evenly into four classes:
eight towns, eight dwellings, eight castles, and eight keeps. Every member of
this family:

- has one class/sub-map key;
- has a town-mode scene byte in `1..32`;
- uses one block in the matching `*.DAT` file;
- uses the matching block in the matching `*.NPC` and `*.TLK` files;
- may have one or more floors;
- may have special tile, NPC, dialogue, or quest behaviour encoded by data.

The location file format does not carry the display name. Names and overworld
entrance coordinates are resident metadata. The DATA.OVL-derived world-location
table now binds scene bytes one through thirty-two to the storage-family keys
below. Some resident name strings are intentionally blank; those rows still have
stable scene bytes and storage keys.

### Towns

Town rows use `TOWNE:n` keys and load `TOWNE.DAT`, `TOWNE.NPC`, and
`TOWNE.TLK`. Their resident order is:

| Scene | Key | Resident name |
|---:|---|---|
| 1 | `TOWNE:0` | Moonglow |
| 2 | `TOWNE:1` | Britain |
| 3 | `TOWNE:2` | Jhelom |
| 4 | `TOWNE:3` | Yew |
| 5 | `TOWNE:4` | Minoc |
| 6 | `TOWNE:5` | Trinsic |
| 7 | `TOWNE:6` | Skara Brae |
| 8 | `TOWNE:7` | New Magincia |

Shop/healer cross-reference: the healer Cure/Heal no-price branch is keyed to
the Minoc town scene, which the shop tables resolve to `The Healers Mission`.
The service flow is documented in `systems/shops.md`.

### Dwellings

Dwelling rows use `DWELLING:n` keys and load `DWELLING.DAT`,
`DWELLING.NPC`, and `DWELLING.TLK`. Dwellings are small town-mode locations:
homes, isolated sites, villages, or special residences. Current NPC roster rows
identify several dwelling-associated named inhabitants, including Jennifer,
Jotham, Windmire, Emilly, Anthony, Charlotte, Smith, Lord Kenneth, David,
Gregory, Grendel, Jacqueline, Sutek, and Sin'Vraal.

The first five dwelling rows have resident names; the last three rows have
blank resident name strings and should be displayed through their stable keys
until another clean source names them.

| Scene | Key | Resident name |
|---:|---|---|
| 9 | `DWELLING:0` | Fogsbane |
| 10 | `DWELLING:1` | Stormcrow |
| 11 | `DWELLING:2` | Greyhaven |
| 12 | `DWELLING:3` | Waveguide |
| 13 | `DWELLING:4` | Iolo's Hut |
| 14 | `DWELLING:5` | Blank resident name |
| 15 | `DWELLING:6` | Blank resident name |
| 16 | `DWELLING:7` | Blank resident name |

### Castles

Castle rows use `CASTLE:n` keys and load `CASTLE.DAT`, `CASTLE.NPC`, and
`CASTLE.TLK`. In this spec, "Castle" is the storage family, not a claim that
every row is an in-world castle. The resident order is:

| Scene | Key | Resident name / binding |
|---:|---|---|
| 17 | `CASTLE:0` | Blank resident name; roster and verification slice identify Lord British's Castle |
| 18 | `CASTLE:1` | Blank resident name; roster content identifies Lord Blackthorn's Castle |
| 19 | `CASTLE:2` | West Britanny |
| 20 | `CASTLE:3` | North Britanny |
| 21 | `CASTLE:4` | East Britanny |
| 22 | `CASTLE:5` | Paws |
| 23 | `CASTLE:6` | Cove |
| 24 | `CASTLE:7` | Buccaneer's Den |

### Keeps

Keep rows use `KEEP:n` keys and load `KEEP.DAT`, `KEEP.NPC`, and `KEEP.TLK`.
Keep interiors are town-mode locations with schedule-driven NPCs, doors,
stairs, possible hostility, and quest-specific scripts. Their resident order is:

| Scene | Key | Resident name |
|---:|---|---|
| 25 | `KEEP:0` | Ararat |
| 26 | `KEEP:1` | Bordermarch |
| 27 | `KEEP:2` | Farthing |
| 28 | `KEEP:3` | Windemere |
| 29 | `KEEP:4` | Stonegate |
| 30 | `KEEP:5` | The Lycaeum |
| 31 | `KEEP:6` | Empath Abbey |
| 32 | `KEEP:7` | Serpent's Hold |

## 6. Dungeons

There are eight named dungeons. Dungeon mode, `DUNGEON.DAT`, and the DATA.OVL
world-location rows agree on this scene/name/record order:

| Scene | Key | `DUNGEON.DAT` record | Resident name | Runtime notes |
|---:|---|---:|---|---|
| 33 | `DUNGEON:0` | 0 | Deceit | Dungeon-mode scene; presentation flavour byte 3. |
| 34 | `DUNGEON:1` | 1 | Despise | Dungeon-mode scene; normal presentation flavour. |
| 35 | `DUNGEON:2` | 2 | Destard | Dungeon-mode scene; normal presentation flavour. |
| 36 | `DUNGEON:3` | 3 | Wrong | Dungeon-mode scene; presentation flavour byte 3. |
| 37 | `DUNGEON:4` | 4 | Covetous | Dungeon-mode scene; presentation flavour byte 3. |
| 38 | `DUNGEON:5` | 5 | Shame | Dungeon-mode scene; mine presentation flavour. |
| 39 | `DUNGEON:6` | 6 | Hythloth | Dungeon-mode scene; mine presentation flavour; bottom-level underworld transition remains a specific open question. |
| 40 | `DUNGEON:7` | 7 | Doom | Dungeon-mode scene; normal presentation flavour. |

The `DUNGEON.DAT` file is dungeon-major and stores eight dungeon records in the
same order. The gazetteer row should therefore carry a dungeon display name,
its `DUNGEON:n` key, its scene byte, its surface or underworld entry record,
and any special exit or scripted transition behaviour.

The standard dungeon-mode entry seed is `(Z=0, X=1, Y=1)` facing east when
entered from Britannia. When entered from the underworld, non-Doom dungeons use
`(Z=7, X=7, Y=7)` facing west; Doom is the exception and still uses the
surface-style seed.

Dungeon rows must not be modeled as town interiors. They have no `*.NPC` roster
and no `*.TLK` block. Talking in dungeon mode always follows the dungeon-mode
no-response path.

## 7. Shrines

There is one shrine per virtue. Shrine rows are keyed by the virtue order used
by the karma system:

| Shrine key | Virtue | Mantra | Engine notes |
|---|---|---|---|
| `SHRINE:honesty` | Honesty | `Ahm` | Meditation and Honesty karma/ordainment. |
| `SHRINE:compassion` | Compassion | `Mu` | Meditation and Compassion karma/ordainment. |
| `SHRINE:valor` | Valor | `Ra` | Meditation and Valor karma/ordainment. |
| `SHRINE:justice` | Justice | `Beh` | Meditation and Justice karma/ordainment. |
| `SHRINE:sacrifice` | Sacrifice | `Cah` | Meditation and Sacrifice karma/ordainment. |
| `SHRINE:honor` | Honor | `Summ` | Meditation and Honor karma/ordainment. |
| `SHRINE:spirituality` | Spirituality | `Om` | Meditation and Spirituality karma/ordainment. |
| `SHRINE:humility` | Humility | `Lum` | Meditation and Humility karma/ordainment. |

Shrines are fixed overworld landmarks, not scene-byte interiors. The shrine
handler should resolve the active shrine from the shrine table, ask for the
mantra, ask for an offering, update the appropriate karma and quest flags, and
return to overworld mode. The exact shrine coordinates belong in the cleanroom
resident-table transcription when available.

## 8. Other Travel Landmarks

The following landmark classes are needed for a usable engine even when they
do not have town/dungeon scene rows.

| Landmark class | Engine contract |
|---|---|
| Moongates | Time-driven surface gates with origin, destination, and animation state. Landing prompts may teleport within Britannia or, for certain phase combinations, to the Underworld. |
| Falls / chasms | Fixed Britannia cells that damage the party, swap the plane to the Underworld, and reseed active objects. |
| Underworld ascents | Fixed Underworld cells that return the party to Britannia at a matching surface location. |
| Wishing wells | Tile-triggered or command-triggered prompt/effect landmarks; no scene byte. |
| Springs | Minor restorative landmarks; no scene byte. |
| Caves and special holes | Local handlers that may give treasure, trigger descent, or route to another mode depending on tile and coordinate. |
| Camps / inns / beds | Rest landmarks; inns are interior data, while outdoor camp sites are overworld/tile-driven. |
| Signs | Location-local text landmarks indexed by sign data and coordinates. |

For these rows, a gazetteer implementation should record the class, display
name if one exists, trigger conditions, destination or effect handler, and
whether the landmark persists, animates, or depends on time.

## 9. Validation And Error Handling

A content loader or audit tool should enforce these rules:

- Every town-mode row has exactly one class in Town, Dwelling, Castle, or Keep.
- Every town-mode row resolves to one scene byte in `1..32`.
- Scene bytes `1..32` are unique.
- The class implied by a scene byte matches the row's class.
- Every town-mode row points to the matching `*.DAT`, `*.NPC`, and `*.TLK`
  family and a sub-map index in `0..7`.
- The paired `*.DAT`, `*.NPC`, and `*.TLK` sub-map indexes match for a row.
- Dungeon rows use dungeon-mode data, not town-mode data.
- Dungeon indexes are unique and in `0..7`.
- Shrine rows are exactly the eight virtues, in the karma system's virtue
  order, and each has exactly one mantra.
- Landmark coordinates, when published, wrap or validate according to the
  owning plane's coordinate rules.
- No coordinate-only record should override scene-byte class rules.
- Unknown names or blank resident-name rows should remain explicit placeholders
  rather than guessed display strings.

Runtime error handling should be conservative:

- If the player triggers an unknown town-mode location coordinate, refuse entry
  or log a content error rather than entering an arbitrary scene byte.
- If a scene byte points outside its class file's eight-block range, treat the
  save or content as corrupt.
- If a shrine coordinate resolves to no virtue, do not run shrine meditation.
- If a dungeon return coordinate is missing, keep the party in dungeon mode or
  fail the load with a diagnostic rather than dropping to a default surface
  cell.
- If two gazetteer rows claim the same trigger coordinate, report an ambiguity
  and require a priority rule from the owning system spec.

## 10. Known Gaps

The following gaps are intentional in this first catalog:

1. **Exact overworld coordinates.** Resident tables are known to exist for
   locations and shrines, but their byte-exact contents have not been published
   in a cleanroom spec.
2. **Blank resident town-mode names.** Scenes 14 through 18 have blank resident
   location-name strings. `CASTLE:0` and `CASTLE:1` are semantically identified
   by roster and special-behaviour evidence; `DWELLING:5` through
   `DWELLING:7` remain stable keyed rows with no public display name.
3. **Location coordinate publication.** The scene/name binding is public, but
   the exact overworld coordinates for those rows are still omitted from this
   cleanroom catalog.
4. **Dungeon return and special-transition coordinates.** The dungeon
   scene/name/data-record order is public, but exact entrance and return
   coordinates are still omitted from this cleanroom catalog.
5. **Moongate schedule.** The overworld spec describes the state machine, but
   the full per-day, per-hour origin/destination table remains open.
6. **Plane-transition pairs.** Falls and Underworld ascents are known system
   features, but the complete paired coordinate set is not public yet.
7. **Minor landmark names.** Wishing wells, springs, caves, signs, and special
   holes need a later pass that joins tile data, sign data, and coordinate
   triggers.

## 11. Sources

This catalog is cleanroom prose derived from existing public specs first, with
private analysis cited only as provenance for semantic table existence. It
omits decompiled code, assembly, byte offsets, private raw tables, and string
dumps.

Public specs used:

- `u5-spec/systems/overworld.md` - overworld surfaces, entrance handling,
  moongates, falls, special tiles, object reseeding, and coordinate wrapping.
- `u5-spec/systems/town-mode.md` - scene-byte partition, town-mode entry and
  exit, location classes, Lord British's Castle special entry behaviour, and
  hostile NPC notes.
- `u5-spec/systems/dungeon-mode.md` - dungeon scene model, named dungeon set,
  scene/name/data-record order, flavour classes, movement, exits, and Hythloth
  open question.
- `u5-spec/formats/brit-dat.md` - Britannia map shape and relationship between
  terrain cells and resident location metadata.
- `u5-spec/formats/under-dat.md` - Underworld map shape and plane-transition
  relationship.
- `u5-spec/formats/location-dat.md` - four per-class location files, sub-map
  partition, floor layout, markers, and resident name/floor table dependency.
- `u5-spec/formats/npc.md` - `.NPC` scene partition, scene-to-storage-key
  order, and blank resident-name rows.
- `u5-spec/catalogs/npc-roster.md` - current named NPC rows and roster-based
  identification of special blank-name locations.
- `u5-engine/reports/lb-throne-room-slice.txt` - first verification slice
  binding Lord British's castle evidence to `CASTLE:0`.
- `u5-spec/systems/karma.md` - virtue order and shrine mantras.
- `u5-spec/catalogs/tile-catalog.md` - shrine, moongate, entrance, ladder,
  sign, well, spring, cave, and other tile-trigger classes.
- `u5-spec/formats/data-ovl.md` - public semantic description of resident
  location, shrine, moongate, and transition metadata.

Private analysis provenance:

- `u5-decomp/formats/data-ovl.md` - confirms the resident image contains
  location coordinate tables, shrine coordinate tables, location/name
  vocabulary, and map metadata. This catalog cites only those semantic facts.
- `u5-decomp/functions/OUTSUBS_OVL/0x0388_outsubs_check_town_entry.md` -
  confirms that overworld location-table index plus one becomes the town-mode
  scene byte for entries one through thirty-two.
- MAINOUT E-Enter helper analysis in `u5-decomp` - confirms that rows
  thirty-two through thirty-nine use the same row-plus-one scene rule for
  dungeons, load the matching `DUNGEON.DAT` record, and seed the dungeon entry
  position by plane.
