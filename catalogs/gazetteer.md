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
  scene-byte identities, location names, and transition tables. The saved-slot
  natural-moongate live-terrain schedule and live entry hook are owned by
  `systems/overworld.md`, not by this catalog.
- Town mode, dungeon mode, shrine meditation, the natural-moongate terrain
  refresh, and other handlers consume those semantic records.

The catalog is implementation-neutral. A modern engine may store it as JSON,
database rows, hardcoded constants, or authored resources. The required
behaviour is that each fixed place resolves consistently to its class, display
name, destination handler, scene identity where applicable, and validation
rules.

The forty-entry overworld entry/return table for town, dwelling, castle, keep,
and dungeon scenes is published in Section 5.1. Coordinate families outside
that table remain owned by their specific systems: shrine/Codex routes by the
shrine and karma specs, natural moongate live placement by the overworld
moongate contract, and surface/underworld plane-transition branches by the
overworld and dungeon-transition specs.

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
| Moongate | Britannia | Saved-slot live-terrain refresh and live `0xDC` entry hook | Overworld moongate placement and waning contract, Moonstone slot state, and entry contract |
| Plane transition | Britannia or Underworld | Overworld plane swap | Overworld loop branches plus the closed transition inventory of Section 8.3 |
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

Scene byte zero is the overworld. Values outside `1..32` do not name a
town-mode location: stock dungeon entries use their own range, intro and
Return-to-View use transient scene ids, and combat-like freezes use the
combat-class marker. A gazetteer row for a town-mode location should therefore
carry both its semantic class and its scene byte or class/sub-map key.

## 4. How To Use This Catalog

An engine should use the gazetteer in these places:

1. **Overworld entry.** When the player enters on a fixed location coordinate,
   look up the matching gazetteer row, set the corresponding scene byte, clear
   or reseed active objects as required, and load the destination mode.
2. **Interior exit.** When a town-mode grid-boundary step and its confirmed
   leave prompt clear the scene byte, resolve the active scene back to its
   overworld entry record and restore the party to the matching surface
   location. The exit is triggered by stepping off the edge of the interior
   grid, not by any exit tile.
3. **Dungeon exit.** When dungeon mode passes the top or the bottom of the
   level stack, resolve the active dungeon to its Section 5.1 entry row and
   return the party to that same outdoor cell — on Britannia when they left off
   the topmost level, in the Underworld when they left through the bottom of
   the lowest one (Section 6.1). There is no "exit-dungeon cell": earlier
   wording here named one, and `systems/dungeon-mode.md` Section 13.2 withdraws
   that class outright.
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
- uses a run of one to five 1,024-byte floor pages in the matching `*.DAT` file;
- uses the matching block in the matching `*.NPC` and `*.TLK` files;
- has between one and five floors;
- may have special tile, NPC, dialogue, or quest behaviour encoded by data.

**The sub-map index in a `FAMILY:n` key is a roster index, not a map-page
index.** It selects the location's block in the `.NPC` and `.TLK` files
correctly, but it does not select the location's tile pages. For twenty-two of
these thirty-two rows the location's map pages are *not* the pair `2n` and
`2n + 1` of the class `.DAT` file, and for twenty rows the page that is the
location's entry floor is not page `2n`. The two counts differ because a
location can own the expected pair of pages while entering on the *second* of
them: Yew is `TOWNE:3` and does own pages 6 and 7, but page 7 is its entry
floor and page 6 is the jail below. Section 5.2 summarises the consequence and
`formats/location-dat.md` Section 4.1 carries the authoritative per-scene page
binding.

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
identify the fifteen dwelling-associated named inhabitants: Jennifer, Jotham,
Windmire, Emilly, Anthony, Charlotte, Smith, Lord Kenneth, Sir Arbuthnot,
David, Gregory, Grendel, Jacqueline, Sutek, and Sin'Vraal.

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

`CASTLE:0` carries one authored puzzle worth noting here: a harpsichord on its
floor `+2` — two storeys above the entry floor, the fourth of its five pages —
which opens a walled-off passage when a fixed thirteen-note tune is played from
the chair beside it. `systems/town-mode.md` Section 13 owns
that contract. Source provenance: derived from private analysis under
`u5-decomp/notes/`.

`CASTLE:1` carries a scene-specific gate of its own: a guard at the palace
demands a password from the party, but only while the party is wearing the
Black Badge, and only the first four typed letters are compared.
`systems/blackthorn.md` Section 7a owns that contract. Source provenance:
derived from private analysis under `u5-decomp/notes/`.

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

### 5.1 Overworld entry / return coordinates

Two resident one-byte-per-scene tables in `DATA.OVL` (one for X, one for Y) carry every scene's overworld entry / return coordinate. The full forty-entry table, indexed by `(scene - 1)`:

| Scene | Name | X | Y |
|---:|---|---:|---:|
| 1 | Moonglow | 232 | 135 |
| 2 | Britain | 81 | 106 |
| 3 | Jhelom | 36 | 222 |
| 4 | Yew | 58 | 43 |
| 5 | Minoc | 159 | 20 |
| 6 | Trinsic | 106 | 184 |
| 7 | Skara Brae | 22 | 128 |
| 8 | New Magincia | 187 | 169 |
| 9 | Fogsbane | 88 | 120 |
| 10 | Stormcrow | 152 | 24 |
| 11 | Greyhaven | 104 | 216 |
| 12 | Waveguide | 216 | 120 |
| 13 | Iolo's Hut | 45 | 62 |
| 14 | (dwelling 14) | 176 | 208 |
| 15 | (dwelling 15) | 201 | 59 |
| 16 | (dwelling 16) | 153 | 91 |
| 17 | Lord British's Castle | 86 | 107 |
| 18 | Lord Blackthorn's Castle | 196 | 245 |
| 19 | West Britanny | 84 | 106 |
| 20 | North Britanny | 86 | 105 |
| 21 | East Britanny | 88 | 106 |
| 22 | Paws | 98 | 145 |
| 23 | Cove | 136 | 90 |
| 24 | Buccaneer's Den | 136 | 158 |
| 25 | Ararat | 49 | 58 |
| 26 | Bordermarch | 15 | 160 |
| 27 | Farthing | 64 | 240 |
| 28 | Windemere | 248 | 8 |
| 29 | Stonegate | 148 | 74 |
| 30 | The Lycaeum | 218 | 107 |
| 31 | Empath Abbey | 28 | 50 |
| 32 | Serpent's Hold | 146 | 241 |
| 33 | Deceit | 240 | 73 |
| 34 | Despise | 91 | 67 |
| 35 | Destard | 72 | 168 |
| 36 | Wrong | 126 | 20 |
| 37 | Covetous | 156 | 27 |
| 38 | Shame | 58 | 102 |
| 39 | Hythloth | 239 | 240 |
| 40 | Doom | 128 | 128 |

#### Authoritative stock E-Enter narration join

This is the complete join required to turn the forty coordinate rows into
production E-Enter transcripts. `T` means the town-family helper's exact
accepted live-tile set `{0x10, 0x12, 0x13, 0x14, 0x15, 0x1B, 0x39, 0x3E}`;
`D` means the dungeon helper's exact set `{0x16, 0x17, 0x18}`. Within either
set, the actual live tile selects the narration and the coordinate selects the
row—there is no comparison with an expected per-row tile. The `stock` value is
the tile shipped at the accepted plane and therefore selects the exact
continuation shown here.

The continuation column begins immediately after the handler's `Enter `
prefix and gives the exact visible transcript. For rows with a proper-name
line, the serialized text stream inserts centre-on immediately before the
uppercase name and centre-off immediately after it. Those controls emit no
glyph or ASCII spaces; `Name col` gives the zero-based starting column in the
sixteen-cell message window after the cursor reposition. A renderer test must
therefore assert both the visible continuation shown and the two control-state
changes around the name.

| Scene / target | Accepted plane and coordinate | Narration class | Exact continuation after `Enter ` | Name col | Live-tile guard |
|---|---|---|---|---:|---|
| 1 / `TOWNE:0` | Britannia `(232,135)` | towne | `towne\n\nMOONGLOW\n` | 4 | `T`; stock `0x14` |
| 2 / `TOWNE:1` | Britannia `(81,106)` | towne | `towne\n\nBRITAIN\n` | 4 | `T`; stock `0x14` |
| 3 / `TOWNE:2` | Britannia `(36,222)` | towne | `towne\n\nJHELOM\n` | 5 | `T`; stock `0x14` |
| 4 / `TOWNE:3` | Britannia `(58,43)` | towne | `towne\n\nYEW\n` | 6 | `T`; stock `0x14` |
| 5 / `TOWNE:4` | Britannia `(159,20)` | towne | `towne\n\nMINOC\n` | 5 | `T`; stock `0x14` |
| 6 / `TOWNE:5` | Britannia `(106,184)` | towne | `towne\n\nTRINSIC\n` | 4 | `T`; stock `0x14` |
| 7 / `TOWNE:6` | Britannia `(22,128)` | towne | `towne\n\nSKARA BRAE\n` | 3 | `T`; stock `0x14` |
| 8 / `TOWNE:7` | Britannia `(187,169)` | village | `village\n\nNEW MAGINCIA\n` | 2 | `T`; stock `0x13` |
| 9 / `DWELLING:0` | Britannia `(88,120)` | lighthouse | `lighthouse\n\nFOGSBANE\n` | 4 | `T`; stock `0x1B` |
| 10 / `DWELLING:1` | Britannia `(152,24)` | lighthouse | `lighthouse\n\nSTORMCROW\n` | 3 | `T`; stock `0x1B` |
| 11 / `DWELLING:2` | Britannia `(104,216)` | lighthouse | `lighthouse\n\nGREYHAVEN\n` | 3 | `T`; stock `0x1B` |
| 12 / `DWELLING:3` | Britannia `(216,120)` | lighthouse | `lighthouse\n\nWAVEGUIDE\n` | 3 | `T`; stock `0x1B` |
| 13 / `DWELLING:4` | Britannia `(45,62)` | hut | `hut\n\nIOLO'S HUT\n` | 3 | `T`; stock `0x10` |
| 14 / `DWELLING:5` | Britannia `(176,208)` | hut; unnamed | `hut\n` | — | `T`; stock `0x10` |
| 15 / `DWELLING:6` | Britannia `(201,59)` | hut; unnamed | `hut\n` | — | `T`; stock `0x10` |
| 16 / `DWELLING:7` | Britannia `(153,91)` | hut; unnamed | `hut\n` | — | `T`; stock `0x10` |
| 17 / `CASTLE:0` | Britannia `(86,107)` | Lord British special | `the Castle of Lord British!\n` | — | `T`; stock `0x3E` |
| 18 / `CASTLE:1` | Britannia `(196,245)` | Blackthorn special | `the palace of Blackthorn!\n` | — | `T`; stock `0x39` |
| 19 / `CASTLE:2` | Britannia `(84,106)` | village | `village\n\nWEST BRITANNY\n` | 1 | `T`; stock `0x13` |
| 20 / `CASTLE:3` | Britannia `(86,105)` | village | `village\n\nNORTH BRITANNY\n` | 1 | `T`; stock `0x13` |
| 21 / `CASTLE:4` | Britannia `(88,106)` | village | `village\n\nEAST BRITANNY\n` | 1 | `T`; stock `0x13` |
| 22 / `CASTLE:5` | Britannia `(98,145)` | village | `village\n\nPAWS\n` | 6 | `T`; stock `0x13` |
| 23 / `CASTLE:6` | Britannia `(136,90)` | village | `village\n\nCOVE\n` | 6 | `T`; stock `0x13` |
| 24 / `CASTLE:7` | Britannia `(136,158)` | towne | `towne\n\nBUCCANEER'S DEN\n` | 0 | `T`; stock `0x14` |
| 25 / `KEEP:0` | Underworld `(49,58)` | keep | `keep\n\nARARAT\n` | 5 | `T`; stock `0x12` |
| 26 / `KEEP:1` | Britannia `(15,160)` | keep | `keep\n\nBORDERMARCH\n` | 2 | `T`; stock `0x12` |
| 27 / `KEEP:2` | Britannia `(64,240)` | keep | `keep\n\nFARTHING\n` | 4 | `T`; stock `0x12` |
| 28 / `KEEP:3` | Britannia `(248,8)` | keep | `keep\n\nWINDEMERE\n` | 3 | `T`; stock `0x12` |
| 29 / `KEEP:4` | Britannia `(148,74)` | keep | `keep\n\nSTONEGATE\n` | 3 | `T`; stock `0x12` |
| 30 / `KEEP:5` | Britannia `(218,107)` | castle | `castle\n\nTHE LYCAEUM\n` | 2 | `T`; stock `0x15` |
| 31 / `KEEP:6` | Britannia `(28,50)` | castle | `castle\n\nEMPATH ABBEY\n` | 2 | `T`; stock `0x15` |
| 32 / `KEEP:7` | Britannia `(146,241)` | castle | `castle\n\nSERPENT'S HOLD\n` | 1 | `T`; stock `0x15` |
| 33 / `DUNGEON:0` | Britannia or Underworld `(240,73)` | dungeon | `dungeon\n\nDECEIT\n` | 5 | `D`; stock `0x18` |
| 34 / `DUNGEON:1` | Britannia or Underworld `(91,67)` | cave | `cave\n\nDESPISE\n` | 4 | `D`; stock `0x16` |
| 35 / `DUNGEON:2` | Britannia or Underworld `(72,168)` | cave | `cave\n\nDESTARD\n` | 4 | `D`; stock `0x16` |
| 36 / `DUNGEON:3` | Britannia or Underworld `(126,20)` | dungeon | `dungeon\n\nWRONG\n` | 5 | `D`; stock `0x18` |
| 37 / `DUNGEON:4` | Britannia or Underworld `(156,27)` | dungeon | `dungeon\n\nCOVETOUS\n` | 4 | `D`; stock `0x18` |
| 38 / `DUNGEON:5` | Britannia or Underworld `(58,102)` | mine | `mine\n\nSHAME\n` | 5 | `D`; stock `0x17` |
| 39 / `DUNGEON:6` | Britannia or Underworld `(239,240)` | mine | `mine\n\nHYTHLOTH\n` | 4 | `D`; stock `0x17` |
| 40 / `DUNGEON:7` | Underworld `(128,128)` | cave; Doom special | `cave\n` | — | `D`; stock `0x16` |

No forty-row destination uses the `ruins` narration. That is the direct
non-transition arm for the blocked ruined-shrine tile, not a town-family scene
row. The Shrine of the Codex and virtue-shrine forms are likewise direct
overworld tile interactions rather than entries in this forty-row destination
table.

The last eight entries (scenes 33..40, the dungeons) double as the Word-of-Power seal-coordinate table. The coordinate names the **entrance cell itself**, and the party speaks the word from an adjacent cell, not from the entrance: the Yell handler looks for the entrance among the party's four cardinal neighbours and then requires that neighbour's coordinate to equal the row below. The sealed entrance is impassable, so standing on it before the word is spoken is not possible in any case. The full predicate is in `systems/commands.md` Section 11.1.

Doom's `(128, 128)` is the Doom dungeon entrance at the centre of the Underworld surface. It is not a Codex-chamber coordinate and it is not reached from inside a dungeon; earlier wording describing it as the Codex chamber wall is retracted. The seven other rows carry a dungeon entrance on **both** world surfaces at the same coordinate, and the saved seal flag is shared between them, so unsealing a dungeon opens it on both.

The four "Britain" castles cluster around `(80..90, 105..107)` plus Lord Blackthorn's Castle at the far southeast outlier `(196, 245)`. Buccaneer's Den at the map center `(136, 158)` sits on its eponymous central island.

One family of shop coordinates is deliberately *not* folded into this table.
The four shipwrights each deliver a purchased vessel to a fixed overworld cell
of their own, published as a column of the shipwright row table in
`systems/shops.md` Section 8.7. Those cells are in the same overworld
coordinate space as the entry coordinates above and sit near the selling town,
but none of them equals the town's entry coordinate, and none of them is
derived from the scene entry/exit mapping. Do not resolve a ship delivery
through this table.

This table is complete for stock scene entry and ordinary exterior return for
the forty scene rows, and the dungeon rows are also the destination of every
dungeon exit: there is no separate exit-coordinate family and no per-dungeon
special case (Section 6). The shrine and Codex-route coordinates are published
in Section 7, and the eight default Moonstone/moongate positions, the four
lighthouse positions, and the two fixed plane-transition coordinates are
published in Section 8. What remains outside this catalog is the runtime
placement state itself - which moongates are currently lit, where a moonstone
has since been buried - which is save state owned by `systems/overworld.md`,
not a fixed landmark.

### 5.2 Floors per location

Every town-family location owns a run of consecutive 1,024-byte floor pages in
its class file. The run length is the location's floor count, and the location's
*entry* floor — the one the party arrives on — is not always the lowest page of
the run. `formats/location-dat.md` Section 4.1 is authoritative for the page
numbers; this table is the gazetteer-side view of how many floors each named
place actually has and which floor indices address them.

| Floors | Locations | Floor indices in play |
|---:|---|---|
| 1 | Iolo's Hut and the three unnamed dwellings, West Britanny, North Britanny, East Britanny, Paws, Cove, Buccaneer's Den, Farthing, Windemere, Stonegate | `0` only |
| 2 | Moonglow, Britain, Jhelom, Minoc, Trinsic, Skara Brae, New Magincia, Ararat, Bordermarch | `0`, `+1` |
| 2 | Yew | `−1`, `0` |
| 3 | Fogsbane, Stormcrow, Greyhaven, Waveguide, The Lycaeum, Empath Abbey | `0`, `+1`, `+2` |
| 3 | Serpent's Hold | `−1`, `0`, `+1` |
| 5 | Lord British's Castle, Lord Blackthorn's Castle | `−1` through `+3` |

That is thirteen one-floor locations, ten two-floor, seven three-floor, and two
five-floor. Higher floor indices are higher storeys; a negative index is a
basement.

Four rows deserve a note for UI and tooling:

- **Yew** is the only town with a basement, and its lower floor is the town
  jail.
- **Lord British's Castle** enters on floor `0` with a basement below and three
  storeys above. Its harpsichord puzzle sits on floor `+2` — two storeys above
  the entry floor, which earlier wording described as a basement. That is
  retracted; the passage it opens is upstairs.
- **Lord Blackthorn's Castle** has the same five-floor shape and the densest
  trapdoor layout in the game: its entry floor and the three floors above it
  carry forty-five, thirty-six, thirty, and thirty-six trapdoor cells
  respectively, while its basement carries none.
- **Serpent's Hold** is the only keep with a basement.

`formats/location-dat.md` Section 4.2 gives the procedure for rederiving these
runs from the shipped tile data, which is what a content tool should do if the
asset set has been modified.

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
| 39 | `DUNGEON:6` | 6 | Hythloth | Dungeon-mode scene; mine presentation flavour. |
| 40 | `DUNGEON:7` | 7 | Doom | Dungeon-mode scene; normal presentation flavour. |

The `DUNGEON.DAT` file is dungeon-major and stores eight dungeon records in the
same order. The gazetteer row should therefore carry a dungeon display name,
its `DUNGEON:n` key, its scene byte, its surface or underworld entry record,
and any special exit or scripted transition behaviour.

The standard dungeon-mode entry seed is `(Z=0, X=1, Y=1)` facing east when
entered from Britannia. When entered from the underworld, non-Doom dungeons use
`(Z=7, X=7, Y=7)` facing west; Doom is the exception and still uses the
surface-style seed. **The seed applies to walk-in entry only.** Loading a saved
game never runs it, so a party resuming a save inside a dungeon keeps the level,
position and facing the save recorded; a save whose facing field is zero resumes
facing north, not east. See `systems/dungeon-mode.md` section 4.1. Only a party travelling on foot may enter a dungeon;
mounted, sailing, and flying parties are refused at the mouth.

### 6.1 Leaving a dungeon

Leaving a dungeon follows one uniform rule, and there is no per-dungeon exit
branch of any kind. Whatever caused the party to pass the top or the bottom of
the level stack, the engine returns them to **that dungeon's own row in the
Section 5.1 table** - the same outdoor cell they would have entered by. The
world plane is chosen by the level they were standing on: leaving off the
topmost level surfaces them on Britannia, and leaving through the bottom of the
lowest level puts them in the Underworld. Because seven of the eight dungeon
mouths carry an entrance tile at the *same* coordinate on both world maps, the
one published coordinate serves both arms.

Earlier revisions of this catalog described a Hythloth-specific bottom-level
handoff and additional Doom or Codex dungeon-exit branches. Both are withdrawn:
no such branch exists, and the Codex approach is an outdoor coordinate gate
(Section 8.1), not a dungeon exit.

Every dungeon except Doom therefore has a working exit at both ends, because
the two dungeon level-change spells move the party one level from wherever they
stand and, at a level edge, hand off to that same exit. What the map data
decides is only where the party may **climb** between levels without a spell,
and by that route the two ends are not symmetric:

| Dungeon | Climbable exit off the topmost level | Climbable exit off the lowest level |
|---|---|---|
| Deceit | ladder | none |
| Despise | ladder | pit and two-way ladder |
| Destard | only while carrying the climbing gear | pit |
| Wrong | ladder | several pits and a ladder |
| Covetous | ladder | ladder |
| Shame | none | ladder |
| Hythloth | two-way ladder | none |
| Doom | none | none |

Each of the five dungeons with a climbable exit off the lowest level places one
of them on the very cell the underworld-side entry drops the party onto, so that
round trip is reciprocal.

**Doom is the exception in every direction.** Its mouth coordinate `(128, 128)`
holds an entrance tile in the Underworld only - on the surface that position
falls inside open ocean - so Doom is entered from the Underworld and nowhere
else. Entry is refused unless all three Shadowlords have been destroyed; a
party that tries earlier is ambushed at the entrance instead. Alone among the
dungeons entered from below, Doom seeds the party on its **topmost** level in
the north-west corner rather than the bottom level. And it cannot be left at
all: its top level carries neither a ladder nor a climbing-gear cell, and the
two level-change spells refuse to work inside it. Doom is a one-way descent.

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
handler resolves the active shrine from the shrine table, asks for the mantra,
asks for an offering, updates the appropriate karma and quest flags, and
returns to overworld mode.

There is **one** resident shrine coordinate table, not two. It serves both
roles at once: the "is the party standing at a shrine" test and the
"the shrine of *virtue*" name the Enter command prints. Any earlier wording
implying a separate render-position table and a separate position-test table is
withdrawn. The table is in the standard virtue order:

| Virtue | X | Y |
|---|---:|---:|
| Honesty | 233 | 66 |
| Compassion | 128 | 92 |
| Valor | 36 | 229 |
| Justice | 73 | 11 |
| Sacrifice | 205 | 45 |
| Honor | 81 | 207 |
| Spirituality | 0 | 0 |
| Humility | 231 | 216 |

The seven non-zero rows are Britannia surface coordinates, and each one holds
the shrine tile; the whole surface map holds exactly those seven shrine tiles
and the Underworld map holds none.

Spirituality's `(0, 0)` row is a **deliberate sentinel** meaning "not on the
surface map", and it encodes a behavioural rule rather than a position:
`(0, 0)` is open ocean, so no party can ever stand there, and a meditation
attempt whose position matches none of the seven mapped shrines resolves to
**Spirituality**. That is how the Shrine of Spirituality - which is not placed
on the Britannia surface - is reached. An implementation must therefore treat
"matched no row" as "Spirituality", not as an error. An older reading of the
same fall-through as a hidden ninth-virtue Humility case is withdrawn; Humility
is an ordinary row and matches by position like the rest.

The **Shrine of the Codex** is a separate landmark with its own tile, occurring
exactly once on the Britannia surface at `(233, 233)` and nowhere in the
Underworld. Its approach gate is described in Section 8.1.

## 8. Other Travel Landmarks

The following landmark classes are needed for a usable engine even when they
do not have town/dungeon scene rows.

| Landmark class | Engine contract |
|---|---|
| Moongates | Saved-slot-driven surface gates whose live-terrain refresh and live `0xDC` entry handling are specified in `systems/overworld.md`. Their eight shipped positions are tabulated below; the positions are save state, so burying a moonstone moves that gate. |
| Lighthouses | Four surface landmarks that double as the outdoor night-time light source (below). Each is also a town-family scene row in Section 5.1. |
| Shrine of the Codex | One surface cell at `(233, 233)`, approached from `(233, 235)` (below). |
| Falls / chasms | The confirmed surface chasm at Britannia `(54, 138)` damages the party, swaps the plane to the Underworld, and reseeds active objects. |
| Whirlpools | Outdoor active objects, not fixed cells. Being swallowed while aboard a vessel always deposits the party at the fixed Underworld coordinate `(34, 18)`. |
| Underworld ascents | **There are none.** No outdoor Underworld terrain feature lifts the party to the surface; see Section 8.3. |
| Telescopes | Three indoor fixtures - in Moonglow, Skara Brae, and West Britanny - each standing near a ladder inside its building. Looking at one shows the sky (`systems/view.md`). |
| Wishing wells | Tile-triggered or command-triggered prompt/effect landmarks; no scene byte. |
| Springs | Minor restorative landmarks; no scene byte. |
| Caves and special holes | Local handlers that may give treasure, trigger descent, or route to another mode depending on tile and coordinate. |
| Camps / inns / beds | Rest landmarks; inns are interior data, while outdoor camp sites are overworld/tile-driven. |
| Signs | Location-local text landmarks indexed by sign data and coordinates. |

For these rows, a gazetteer implementation should record the class, display
name if one exists, trigger conditions, destination or effect handler, and
whether the landmark persists, animates, or depends on time.

### 8.1 Fixed landmark coordinates

**The eight Moonstone / natural-moongate positions.** These are the shipped
values of the eight saved Moonstone slots on a new game. All eight are grass
cells on the Britannia surface, and the daytime pass restores exactly that
grass when a gate closes.

| Slot | X | Y | Slot | X | Y |
|---:|---:|---:|---:|---:|---:|
| 0 | 224 | 133 | 4 | 166 | 19 |
| 1 | 96 | 102 | 5 | 104 | 194 |
| 2 | 38 | 224 | 6 | 23 | 126 |
| 3 | 50 | 37 | 7 | 187 | 167 |

These are **save state**, not fixed geography. Burying a moonstone rewrites its
slot with the party's current position, which relocates both that gate's
nightly appearance and the destination every gate that selects that slot leads
to. A catalog should present the table above as the shipped starting layout.

**The four lighthouses.** Stormcrow `(152, 24)`, Fogsbane `(88, 120)`,
Waveguide `(216, 120)`, and Greyhaven `(104, 216)` - the same coordinates their
scene rows carry in Section 5.1. Each is also the outdoor night-time light
source described in `systems/overworld.md`: after dark, a lighthouse inside the
loaded map window sweeps a rotating beam across the surrounding cells.

**The Shrine of the Codex approach.** The shrine tile itself is at
`(233, 233)`. The gate the player actually meets is one cell of open approach
at `(233, 235)`: standing there on the Britannia surface, the game either
grants passage or refuses it and pushes the party one cell back south,
according to the saved ordained-progress state. `systems/overworld.md` owns the
branch; it is an outdoor coordinate gate and has nothing to do with dungeon
exits.

**The two fixed plane-transition cells.** The surface chasm at `(54, 138)`
drops the party into the Underworld, and every whirlpool deposits them at
`(34, 18)`.

### 8.2 What the Enter command recognises

The overworld Enter command switches on the terrain the party is standing on
and prints `Enter` plus a label. The recognised terrain kinds, and the label
each prints, are: hut, **the Shrine of the Codex!**, keep, village, towne,
castle, cave, mine, dungeon, **the shrine of** *virtue* (the virtue selected
from the Section 7 table), ruins, lighthouse, **the palace of Blackthorn!**,
and **the Castle of Lord British!**. Standing on anything else answers `What?`
and consumes nothing.

Recognising the terrain is not the same as entering: the town-family and
dungeon paths still require the party's coordinate to match a Section 5.1 row,
and dungeon entry additionally requires foot travel and, for Doom, the
Shadowlord gate of Section 6.1.

### 8.3 Crossing between the two world planes

The inventory of plane transitions is closed, and it is asymmetric.

**Surface to Underworld**, three routes: the fixed chasm at `(54, 138)`; being
swallowed by a whirlpool while aboard a vessel, which always lands at
`(34, 18)`; and leaving a dungeon through the bottom of its lowest level.

**Underworld to surface**, three routes, **none of them outdoor terrain**:
leaving a dungeon off its topmost level; taking a moongate or casting Gate
Travel to a Moonstone slot whose recorded position is on the surface (all eight
ship that way); and a save-state restore that simply replays a previously saved
position. There is no Underworld cell that lifts the party up - no mirror of
the surface chasm exists, and the claim is exhaustive rather than
not-yet-found.

One location exists **only** in the Underworld: **Ararat**, at `(49, 58)`,
where the Underworld map carries a keep and the surface map carries plain
brush. Leaving Ararat correctly returns the party to the Underworld rather than
to the surface, and it is the only location row that behaves that way; every
other location exit selects the surface.

## 9. Validation And Error Handling

A content loader or audit tool should enforce these rules:

- Every town-mode row has exactly one class in Town, Dwelling, Castle, or Keep.
- Every town-mode row resolves to one scene byte in `1..32`.
- Scene bytes `1..32` are unique.
- The class implied by a scene byte matches the row's class.
- Every town-mode row points to the matching `*.DAT`, `*.NPC`, and `*.TLK`
  family and a sub-map index in `0..7`.
- The paired `*.NPC` and `*.TLK` sub-map indexes match for a row. Do **not**
  extend this check to the class `*.DAT` file: its floor pages are selected
  through the per-scene base-page table of `formats/location-dat.md`
  Section 4.1, and for twenty of the thirty-two locations that base page is
  not twice the sub-map index (twenty-two locations do not own the page *pair*
  `2n`/`2n + 1` at all — the two counts are different checks, and Section 5
  states both).
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

1. **Minor virtue-route waypoints.** The forty scene entry/return rows, the
   eight shrine coordinates, and the Shrine of the Codex coordinate and its
   approach cell are all published above. What is not catalogued is the
   narrative furniture of the virtue quests - urn placements inside buildings
   and similar interior fixtures - which stay with `systems/karma.md`.
2. **Blank resident town-mode names.** Scenes 14 through 18 have blank resident
   location-name strings. `CASTLE:0` and `CASTLE:1` are semantically identified
   by roster and special-behaviour evidence; `DWELLING:5` through
   `DWELLING:7` remain stable keyed rows with no public display name.
3. **Room-mediated dungeon level changes.** The uniform dungeon exit rule, the
   per-dungeon climbable-exit table, and Doom's special case are published in
   Section 6.1. The one narrow thing left open is which dungeon *room* maps
   place a ladder cell under the party, since an up-or-down request raised
   inside a room feeds the same level-change and exit machinery.
4. **Quest-bit semantics behind the Codex approach gate.** The gate itself is
   published in Section 8.1, but exactly which quest beats set the saved
   ordained-progress state it reads is still owned by `systems/quest-flags.md`
   and is not fully traced.
5. *(This gap is closed. The eight shipped Moonstone positions, the four
   lighthouses, and the Codex approach are published in Section 8.1.)*
6. **Minor landmark names.** Wishing wells, springs, caves, signs, and special
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
  scene/name/data-record order, flavour classes, movement, and the level-change
  and exit contract.
- `u5-spec/formats/brit-dat.md` - Britannia map shape and relationship between
  terrain cells and resident location metadata.
- `u5-spec/formats/under-dat.md` - Underworld map shape and plane-transition
  relationship.
- `u5-spec/formats/location-dat.md` - four per-class location files, the flat
  sixteen-page array in each, floor-page layout, markers, and the authoritative
  per-scene base floor-page table that Section 5.2 summarises.
- `u5-spec/formats/npc.md` - `.NPC` scene partition, scene-to-storage-key
  order, and blank resident-name rows.
- `u5-spec/catalogs/npc-roster.md` - current named NPC rows and roster-based
  identification of special blank-name locations.
- `u5-spec/NEXT-STEPS.md` - clean summary of the earlier external verification
  slice binding Lord British's castle evidence to `CASTLE:0`.
- `u5-spec/systems/karma.md` - virtue order and shrine mantras.
- `u5-spec/catalogs/tile-catalog.md` - shrine, moongate, entrance, ladder,
  sign, well, spring, cave, and other tile-trigger classes.
- `u5-spec/formats/data-ovl.md` - public semantic description of resident
  location, shrine, moongate, and transition metadata.

Private analysis provenance:

- Source provenance: derived from private analysis under
  `u5-decomp/notes/` - the per-location
  floor counts and floor ranges of Section 5.2, the four locations that enter
  above the bottom of their page run, and the correction placing the Lord
  British's Castle harpsichord two storeys above the entry floor rather than in
  a basement.
- `u5-decomp/formats/` - confirms the resident image contains
  location coordinate tables, shrine coordinate tables, location/name
  vocabulary, and map metadata. This catalog cites only those semantic facts.
- `u5-decomp/functions/OUTSUBS_OVL/` -
  confirms that overworld location-table index plus one becomes the town-mode
  scene byte for entries one through thirty-two.
- `u5-decomp/functions/OUTSUBS_OVL/` -
  confirms the traced surface falls coordinate and underworld plane swap.
- Source provenance: the uniform dungeon exit rule, the per-dungeon climbable
  exit table, Doom's entry gate and one-way descent, the closed
  plane-transition inventory, Ararat's underworld-only status, the eight
  shipped Moonstone positions, the four lighthouse positions, and the Shrine of
  the Codex approach are derived from private analysis under
  `u5-decomp/notes/`.
- Source provenance: the single shrine coordinate table, the Spirituality
  sentinel rule, the Shrine of the Codex coordinate, the Enter label set, and
  the three shipped telescope placements are derived from private analysis
  under `u5-decomp/notes/`.
- MAINOUT E-Enter helper analysis in `u5-decomp` - confirms that rows
  thirty-two through thirty-nine use the same row-plus-one scene rule for
  dungeons, load the matching `DUNGEON.DAT` record, and seed the dungeon entry
  position by plane.
- The complete E-Enter live-tile switch, forty-row map join, centered-name
  envelope, no-match transcripts, action results, `.OOL` write ordering, and
  direct-construction boundary are derived from private analysis under
  `u5-decomp/functions/MAINOUT_OVL/`,
  `u5-decomp/functions/OUTSUBS_OVL/`,
  `u5-decomp/functions/ULTIMA_EXE/`, `u5-decomp/formats/`, and
  `u5-decomp/notes/`.
