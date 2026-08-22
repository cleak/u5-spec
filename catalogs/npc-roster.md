# NPC Roster

A cleanroom catalog of the speaking NPC roster currently derivable from the
four `.NPC` roster files and the four paired `.TLK` dialogue files. This is a
lookup document, not a dialogue dump: it lists names, roster placement,
dialogue identifiers, keyword counts, opaque role tags, and daily schedules,
but it does not reproduce NPC responses, keyword strings, assembly, decompiled
code, file offsets, or raw dialogue blobs.

## 1. Scope And Completion

The local data supports a complete catalog of the named dialogue records and
the roster slots that point at them:

| Family | Real TLK entries | Occupied roster slots | Named roster slots | Generic/reserved slots |
|---|---:|---:|---:|---:|
| `TOWNE` | 47 | 107 | 47 | 60 |
| `DWELLING` | 14 | 18 | 14 | 4 |
| `CASTLE` | 39 | 112 | 44 | 68 |
| `KEEP` | 31 | 88 | 31 | 57 |
| **Total** | **131** | **325** | **136** | **189** |

All 131 real `.TLK` entries are referenced by at least one occupied roster
slot. The named roster-slot count is higher than the unique `.TLK` count because
`CASTLE:1` uses the same Gorn dialogue record for six roster slots.

The `Loc` column is a stable data key: file family plus sub-map index. For
example, `TOWNE:7` means sub-map seven of the town-family roster and its paired
town-family dialogue file. Runtime scene bytes `1..32` map to these keys by
class `(scene - 1) >> 3` and sub-map `(scene - 1) & 7`; the gazetteer owns the
human-readable place names and overworld-entry coordinates.

For convenience, the roster keys resolve to these public scene names:

| Scene | Loc | Place |
|---:|---|---|
| 1 | `TOWNE:0` | Moonglow |
| 2 | `TOWNE:1` | Britain |
| 3 | `TOWNE:2` | Jhelom |
| 4 | `TOWNE:3` | Yew |
| 5 | `TOWNE:4` | Minoc |
| 6 | `TOWNE:5` | Trinsic |
| 7 | `TOWNE:6` | Skara Brae |
| 8 | `TOWNE:7` | New Magincia |
| 9 | `DWELLING:0` | Fogsbane |
| 10 | `DWELLING:1` | Stormcrow |
| 11 | `DWELLING:2` | Greyhaven |
| 12 | `DWELLING:3` | Waveguide |
| 13 | `DWELLING:4` | Iolo's Hut |
| 14 | `DWELLING:5` | unnamed dwelling resident row |
| 15 | `DWELLING:6` | unnamed dwelling resident row |
| 16 | `DWELLING:7` | unnamed dwelling resident row |
| 17 | `CASTLE:0` | Lord British's Castle |
| 18 | `CASTLE:1` | Lord Blackthorn's Castle |
| 19 | `CASTLE:2` | West Britanny |
| 20 | `CASTLE:3` | North Britanny |
| 21 | `CASTLE:4` | East Britanny |
| 22 | `CASTLE:5` | Paws |
| 23 | `CASTLE:6` | Cove |
| 24 | `CASTLE:7` | Buccaneer's Den |
| 25 | `KEEP:0` | Ararat |
| 26 | `KEEP:1` | Bordermarch |
| 27 | `KEEP:2` | Farthing |
| 28 | `KEEP:3` | Windemere |
| 29 | `KEEP:4` | Stonegate |
| 30 | `KEEP:5` | The Lycaeum |
| 31 | `KEEP:6` | Empath Abbey |
| 32 | `KEEP:7` | Serpent's Hold |

The three unnamed dwelling rows are not transcription omissions. Their
resident name strings are blank in the analyzed data, so this catalog keeps the
stable storage key rather than inventing a place name.

## 2. How To Read The Table

`Dlg` is the dialogue id loaded from the roster slot and resolved against the
matching `.TLK` file. `Kw` is the number of variable keyword/response pairs
after the five fixed leading dialogue entries; the keywords themselves are not
listed here.

`Tag` is the roster type byte shown as two hexadecimal digits. It is the
engine's occupancy and sprite-class byte, not the schedule AI. Zero means an
empty slot; nonzero means occupied. Ordinary visible NPCs derive their sprite
from this value. `01` forces the default human/person sprite. `FC` appears in no shipped
roster slot: it is the Shadow Lord actor class, written into a live NPC slot
only by the town-entry Shadowlord install (`systems/town-mode.md` Section 13).
An earlier revision of this catalog called `FC` a runtime player mirror; that
is retracted, and the spec no longer gives the player any NPC-slot
representation.

The schedule column uses the roster's three-waypoint model:

- `A`, `B`, and `C` are the three stored waypoints.
- `m#` is the per-waypoint AI/mode byte. The values are interpreted in
  `systems/npc-schedules.md`: `m0` stationary, `m1` bounded wander, `m2`
  unbounded wander, `m3` follow/shadow, `m4` approach/attack, `m5` reserved
  engage path, `m6` guard/blocking event, and `m7` randomized chase.
- `@(x,y,z)` is the waypoint coordinate in the location's 32 by 32 grid. `z`
  is shown as signed when the byte is the observed below-floor sentinel.
- `A 21-09` means waypoint A applies from hour 21 through hour 8, wrapping
  midnight. Hours use a 24-hour clock and ranges are half-open.
- Waypoint B has two daily intervals by engine rule: `time[1]-time[2]` and
  `time[3]-time[0]`.

## 3. Roster

### TOWNE

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| TOWNE:0 | 4 | Zachariah | 2 | 50 | 16 | A 19-09 m0 @(8,5,0); B 09-12/13-19 m0 @(9,9,0); C 12-13 m0 @(20,21,0) |
| TOWNE:0 | 5 | Malifora | 3 | 68 | 14 | A 19-09 m0 @(5,5,0); B 09-12/13-19 m2 @(15,24,0); C 12-13 m0 @(20,23,0) |
| TOWNE:0 | 11 | Malik | 4 | 50 | 22 | A 19-11 m0 @(9,24,1); B 11-15/17-19 m4 @(15,25,0); C 15-17 m0 @(20,23,0) |
| TOWNE:0 | 12 | Donn Piatt | 5 | 50 | 13 | A 00-09 m0 @(19,24,1); B 09-11/13-00 m0 @(23,21,0); C 11-13 m0 @(19,24,1) |
| TOWNE:1 | 4 | Greyson | 7 | 50 | 15 | A 23-09 m0 @(1,5,1); B 09-18/19-23 m1 @(8,1,0); C 18-19 m0 @(4,5,0) |
| TOWNE:1 | 5 | Justin | 8 | 68 | 16 | A 21-09 m0 @(5,4,1); B 09-18/19-21 m1 @(5,7,0); C 18-19 m0 @(3,5,0) |
| TOWNE:1 | 6 | Eb | 9 | 50 | 20 | A 19-05 m0 @(23,16,0); B 05-12/13-19 m1 @(26,26,0); C 12-13 m0 @(24,16,1) |
| TOWNE:1 | 7 | Terrance | 10 | 50 | 17 | A 19-06 m0 @(23,15,0); B 06-12/13-19 m1 @(30,5,0); C 12-13 m0 @(25,16,1) |
| TOWNE:1 | 8 | Telila | 11 | 50 | 13 | A 18-06 m0 @(5,21,1); B 06-11/12-18 m1 @(3,29,0); C 11-12 m0 @(3,8,0) |
| TOWNE:1 | 13 | Gwenno | 12 | 40 | 17 | A 19-07 m0 @(21,6,1); B 07-11/13-19 m1 @(15,6,1); C 11-13 m0 @(3,10,0) |
| TOWNE:1 | 14 | Lord Stuart the Hungry | 6 | 44 | 13 | A 21-07 m0 @(24,8,1); B 07-09/19-21 m0 @(3,10,0); C 09-19 m1 @(15,14,0) |
| TOWNE:2 | 4 | Annon | 13 | 50 | 14 | A 17-07 m0 @(7,14,1); B 07-12/13-17 m1 @(8,22,0); C 12-13 m0 @(11,7,0) |
| TOWNE:2 | 8 | Bullwier | 14 | 5C | 13 | A 21-11 m0 @(20,21,1); B 11-15/17-21 m0 @(9,7,0); C 15-17 m0 @(11,9,0) |
| TOWNE:2 | 9 | Trian | 15 | 40 | 13 | A 18-09 m0 @(1,1,0); B 09-11/13-18 m2 @(2,2,1); C 11-13 m1 @(3,2,0) |
| TOWNE:2 | 10 | Goeth | 16 | 48 | 21 | A 19-09 m0 @(9,22,1); B 09-13/15-19 m2 @(13,17,0); C 13-15 m0 @(17,9,0) |
| TOWNE:3 | 7 | Landon | 19 | 50 | 14 | A 17-09 m0 @(29,15,0); B 09-13/15-17 m0 @(25,11,0); C 13-15 m0 @(3,5,0) |
| TOWNE:3 | 8 | Judge Dryden | 20 | 50 | 19 | A 23-09 m0 @(4,16,0); B 09-11/21-23 m0 @(25,7,0); C 11-21 m1 @(3,11,0) |
| TOWNE:3 | 9 | Jeremy | 21 | 48 | 18 | A 21-07 m0 @(25,3,0); B 07-09/11-21 m1 @(24,4,0); C 09-11 m1 @(24,4,0) |
| TOWNE:3 | 10 | Jerone | 22 | 40 | 24 | A 19-09 m0 @(20,3,0); B 09-12/13-19 m0 @(22,4,0); C 12-13 m1 @(21,4,0) |
| TOWNE:3 | 11 | Felespar | 23 | 44 | 18 | A 00-00 m0 @(18,14,0); B 00-00/00-00 m0 @(18,14,0); C 00-00 m0 @(18,14,0) |
| TOWNE:3 | 12 | Mario | 24 | 68 | 18 | A 00-00 m0 @(20,16,0); B 00-00/00-00 m0 @(20,16,0); C 00-00 m0 @(20,16,0) |
| TOWNE:3 | 13 | Chamfort | 18 | 44 | 14 | A 09-15 m0 @(19,24,-1); B 15-23/01-09 m1 @(22,1,0); C 23-01 m0 @(17,28,-1) |
| TOWNE:3 | 14 | Thorne | 17 | 48 | 18 | A 18-09 m0 @(7,30,0); B 09-15/17-18 m1 @(2,23,0); C 15-17 m0 @(2,29,0) |
| TOWNE:3 | 19 | Jaana | 36 | 48 | 9 | A 00-00 m1 @(29,3,0); B 00-00/00-00 m1 @(29,3,0); C 00-00 m1 @(29,3,0) |
| TOWNE:3 | 21 | Gruman | 35 | 44 | 13 | A 01-09 m0 @(19,22,-1); B 09-11/23-01 m0 @(17,30,-1); C 11-23 m2 @(19,27,-1) |
| TOWNE:4 | 1 | Aleyn | 25 | 48 | 9 | A 21-09 m0 @(24,25,1); B 09-15/17-21 m1 @(27,26,0); C 15-17 m0 @(27,24,1) |
| TOWNE:4 | 3 | Tactus | 26 | 50 | 15 | A 19-06 m0 @(7,27,1); B 06-07/18-19 m2 @(12,17,0); C 07-18 m1 @(25,8,0) |
| TOWNE:4 | 6 | Fiona | 27 | 68 | 20 | A 21-05 m0 @(23,4,0); B 05-12/13-21 m0 @(5,6,0); C 12-13 m0 @(26,13,0) |
| TOWNE:4 | 7 | Rew | 28 | 50 | 19 | A 21-05 m0 @(26,6,0); B 05-12/13-21 m0 @(7,6,0); C 12-13 m0 @(26,11,0) |
| TOWNE:4 | 8 | Fenelon | 29 | 50 | 19 | A 19-07 m0 @(23,6,0); B 07-11/13-19 m1 @(6,26,0); C 11-13 m0 @(25,11,0) |
| TOWNE:4 | 9 | Lady Sahra | 30 | 6C | 13 | A 19-09 m0 @(26,8,0); B 09-17/18-19 m4 @(13,19,0); C 17-18 m0 @(26,13,0) |
| TOWNE:5 | 3 | Delwyn | 31 | 48 | 9 | A 18-07 m0 @(24,12,1); B 07-12/13-18 m1 @(25,7,0); C 12-13 m0 @(23,15,0) |
| TOWNE:5 | 5 | Woolfe | 32 | 40 | 20 | A 06-00 m0 @(22,25,0); B 00-01/05-06 m0 @(25,7,1); C 01-05 m2 @(29,2,1) |
| TOWNE:5 | 6 | Sindar... | 33 | 68 | 8 | A 15-12 m0 @(24,25,0); B 12-12/13-15 m0 @(5,26,0); C 12-13 m0 @(24,14,0) |
| TOWNE:5 | 9 | Jimmy | 34 | 48 | 26 | A 23-06 m0 @(11,30,0); B 06-09/15-23 m1 @(15,29,1); C 09-15 m2 @(29,2,1) |
| TOWNE:6 | 4 | Greymarch | 37 | 68 | 12 | A 00-00 m3 @(5,22,0); B 00-00/00-00 m3 @(5,22,0); C 00-00 m3 @(5,22,0) |
| TOWNE:6 | 5 | Froed | 38 | 40 | 19 | A 00-00 m2 @(15,14,1); B 00-00/00-00 m2 @(15,14,1); C 00-00 m2 @(15,14,1) |
| TOWNE:6 | 6 | Flain | 39 | 44 | 15 | A 19-19 m0 @(26,24,0); B 19-17/19-19 m0 @(26,24,0); C 17-19 m0 @(28,25,0) |
| TOWNE:6 | 7 | Kindor | 40 | 50 | 9 | A 18-09 m0 @(24,9,1); B 09-17/18-18 m2 @(17,5,0); C 17-18 m0 @(27,25,0) |
| TOWNE:7 | 3 | Shirita | 43 | 50 | 14 | A 21-05 m0 @(3,28,0); B 05-11/12-21 m1 @(9,28,0); C 11-12 m0 @(27,18,0) |
| TOWNE:7 | 4 | Yasuda | 44 | 50 | 8 | A 19-05 m0 @(2,13,0); B 05-12/13-19 m1 @(2,17,0); C 12-13 m0 @(25,21,0) |
| TOWNE:7 | 5 | Tetsuo | 45 | 50 | 8 | A 19-05 m0 @(12,3,0); B 05-12/13-19 m1 @(4,17,0); C 12-13 m0 @(25,19,0) |
| TOWNE:7 | 6 | Fumiko | 46 | 50 | 9 | A 21-06 m0 @(4,2,0); B 06-12/13-21 m1 @(3,18,0); C 12-13 m0 @(27,16,0) |
| TOWNE:7 | 7 | Kaiko | 47 | 50 | 12 | A 23-09 m0 @(28,12,0); B 09-11/13-23 m1 @(26,18,0); C 11-13 m0 @(23,4,0) |
| TOWNE:7 | 8 | Katrina | 48 | 50 | 28 | A 21-05 m0 @(28,29,0); B 05-12/13-21 m1 @(22,30,0); C 12-13 m0 @(29,28,0) |
| TOWNE:7 | 9 | Saul | 41 | 50 | 13 | A 19-05 m0 @(2,10,0); B 05-12/13-19 m1 @(5,16,0); C 12-13 m0 @(27,18,0) |
| TOWNE:7 | 10 | Tomoka | 42 | 50 | 15 | A 23-09 m0 @(28,9,0); B 09-17/23-23 m1 @(23,4,0); C 17-23 m0 @(25,19,0) |

### DWELLING

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| DWELLING:0 | 2 | Jennifer | 2 | 50 | 9 | A 07-17 m0 @(24,18,0); B 17-19/05-07 m0 @(21,18,0); C 19-05 m0 @(14,15,0) |
| DWELLING:1 | 1 | Jotham | 3 | 50 | 18 | A 19-05 m2 @(16,19,2); B 05-07/17-19 m0 @(19,12,0); C 07-17 m0 @(12,10,0) |
| DWELLING:1 | 2 | Windmire | 4 | 50 | 16 | A 19-05 m0 @(12,8,0); B 05-07/17-19 m0 @(19,14,0); C 07-17 m2 @(16,19,2) |
| DWELLING:2 | 1 | Emilly | 5 | 68 | 12 | A 21-07 m0 @(20,9,0); B 07-09/19-21 m0 @(11,12,0); C 09-19 m2 @(3,15,0) |
| DWELLING:2 | 2 | Anthony | 6 | 50 | 22 | A 21-05 m0 @(18,9,0); B 05-09/17-21 m0 @(11,10,0); C 09-17 m2 @(16,17,2) |
| DWELLING:2 | 3 | Charlotte | 7 | 50 | 17 | A 07-17 m0 @(18,11,0); B 17-19/05-07 m0 @(11,12,0); C 19-05 m2 @(14,17,2) |
| DWELLING:2 | 4 | Smith | 14 | 50 | 12 | A 21-09 m0 @(9,21,0); B 09-11/13-21 m1 @(11,18,0); C 11-13 m0 @(11,10,0) |
| DWELLING:2 | 5 | Lord Kenneth | 15 | 48 | 30 | A 23-09 m0 @(9,19,0); B 09-11/13-23 m0 @(20,17,0); C 11-13 m0 @(11,12,0) |
| DWELLING:3 | 1 | David | 8 | 50 | 18 | A 07-17 m0 @(9,11,0); B 17-19/05-07 m0 @(20,12,0); C 19-05 m2 @(18,12,2) |
| DWELLING:3 | 2 | Gregory | 9 | 50 | 3 | A 07-17 m0 @(9,14,0); B 17-19/05-07 m0 @(20,14,0); C 19-05 m2 @(12,12,2) |
| DWELLING:4 | 4 | Grendel | 13 | 11 | 11 | A 00-00 m1 @(27,3,0); B 00-00/00-00 m1 @(27,3,0); C 00-00 m1 @(27,3,0) |
| DWELLING:5 | 1 | Jacqueline | 10 | 40 | 4 | A 21-09 m0 @(12,16,0); B 09-13/15-21 m0 @(14,13,0); C 13-15 m0 @(3,3,0) |
| DWELLING:6 | 1 | Sutek | 11 | D8 | 2 | A 07-18 m1 @(6,9,0); B 18-19/06-07 m0 @(24,7,0); C 19-06 m1 @(15,15,0) |
| DWELLING:7 | 1 | Sin'Vraal | 12 | 90 | 14 | A 06-12 m2 @(15,14,0); B 12-18/00-06 m2 @(15,14,0); C 18-00 m2 @(15,14,0) |

### CASTLE

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| CASTLE:0 | 14 | Alistair the Bard | 2 | 50 | 11 | A 23-07 m0 @(12,10,0); B 07-15/17-23 m1 @(9,22,0); C 15-17 m0 @(9,24,0) |
| CASTLE:0 | 18 | Stephen | 3 | 68 | 13 | A 18-07 m0 @(22,18,0); B 07-13/15-18 m1 @(21,24,0); C 13-15 m0 @(9,24,0) |
| CASTLE:0 | 19 | Treanna | 4 | 50 | 18 | A 18-11 m0 @(7,25,1); B 11-15/17-18 m1 @(20,23,1); C 15-17 m0 @(21,20,1) |
| CASTLE:0 | 20 | Margaret | 5 | 68 | 19 | A 18-11 m0 @(7,27,1); B 11-15/17-18 m1 @(19,25,1); C 15-17 m0 @(21,18,1) |
| CASTLE:0 | 21 | Desiree | 6 | 48 | 12 | A 00-00 m7 @(12,10,-1); B 00-00/00-00 m7 @(12,10,-1); C 00-00 m7 @(12,10,-1) |
| CASTLE:0 | 26 | Drudgeworth | 7 | 50 | 18 | A 03-23 m0 @(13,19,-1); B 23-00/01-03 m1 @(15,20,2); C 00-01 m1 @(15,10,2) |
| CASTLE:0 | 27 | Saduj | 8 | 70 | 23 | A 23-03 m0 @(10,27,1); B 03-13/15-23 m4 @(15,25,2); C 13-15 m0 @(19,18,1) |
| CASTLE:0 | 29 | Stillwelt | 9 | 58 | 7 | A 23-07 m0 @(9,12,0); B 07-17/18-23 m1 @(15,24,0); C 17-18 m0 @(10,7,1) |
| CASTLE:1 | 5 | Chuckles | 10 | 78 | 14 | A 23-07 m0 @(11,8,2); B 07-13/15-23 m0 @(15,15,2); C 13-15 m1 @(15,23,3) |
| CASTLE:1 | 16 | Blackthorn | 11 | 48 | 6 | A 00-06 m4 @(5,7,-1); B 06-12/18-00 m4 @(5,7,-1); C 12-18 m4 @(5,7,-1) |
| CASTLE:1 | 19 | Gorn | 12 | 50 | 6 | A 00-00 m0 @(3,2,1); B 00-00/00-00 m0 @(3,2,1); C 00-00 m0 @(3,2,1) |
| CASTLE:1 | 20 | Gorn | 12 | 50 | 6 | A 00-00 m0 @(27,2,1); B 00-00/00-00 m0 @(27,2,1); C 00-00 m0 @(27,2,1) |
| CASTLE:1 | 21 | Gorn | 12 | 50 | 6 | A 00-00 m0 @(23,18,1); B 00-00/00-00 m0 @(23,18,1); C 00-00 m0 @(23,18,1) |
| CASTLE:1 | 22 | Gorn | 12 | 50 | 6 | A 00-00 m0 @(7,18,1); B 00-00/00-00 m0 @(7,18,1); C 00-00 m0 @(7,18,1) |
| CASTLE:1 | 23 | Gorn | 12 | 50 | 6 | A 00-00 m0 @(11,12,2); B 00-00/00-00 m0 @(11,12,2); C 00-00 m0 @(11,12,2) |
| CASTLE:1 | 24 | Gorn | 12 | 50 | 6 | A 00-00 m0 @(19,12,2); B 00-00/00-00 m0 @(19,12,2); C 00-00 m0 @(19,12,2) |
| CASTLE:1 | 25 | .... | 13 | 50 | 9 | A 19-07 m0 @(22,4,0); B 07-11/13-19 m1 @(8,10,0); C 11-13 m0 @(12,21,1) |
| CASTLE:1 | 26 | Kraw | 14 | 40 | 8 | A 19-06 m0 @(19,11,0); B 06-13/15-19 m0 @(15,6,1); C 13-15 m0 @(24,12,0) |
| CASTLE:1 | 29 | Weblock | 15 | 50 | 15 | A 18-09 m0 @(22,6,0); B 09-15/17-18 m1 @(15,18,1); C 15-17 m0 @(12,23,1) |
| CASTLE:1 | 30 | Gallrot | 16 | 58 | 12 | A 23-07 m0 @(15,15,2); B 07-13/15-23 m1 @(15,18,2); C 13-15 m0 @(10,21,1) |
| CASTLE:1 | 31 | Foulwell | 17 | 40 | 11 | A 00-00 m2 @(25,7,-1); B 00-00/00-00 m2 @(25,7,-1); C 00-00 m2 @(25,7,-1) |
| CASTLE:2 | 1 | Hassad | 18 | 50 | 19 | A 18-06 m0 @(4,30,0); B 06-12/13-18 m1 @(4,20,0); C 12-13 m0 @(2,29,0) |
| CASTLE:2 | 2 | Camile | 19 | 50 | 20 | A 17-05 m0 @(29,26,0); B 05-11/13-17 m1 @(21,22,0); C 11-13 m0 @(23,4,0) |
| CASTLE:2 | 3 | Phillip | 20 | 50 | 9 | A 17-05 m0 @(27,28,0); B 05-11/13-17 m1 @(21,28,0); C 11-13 m0 @(25,4,0) |
| CASTLE:3 | 2 | Christopher | 21 | 50 | 16 | A 23-01 m0 @(4,3,0); B 01-06/19-23 m0 @(27,25,0); C 06-19 m1 @(28,19,0) |
| CASTLE:3 | 3 | Thentis | 22 | 50 | 21 | A 23-01 m0 @(3,4,0); B 01-06/19-23 m0 @(27,29,0); C 06-19 m1 @(26,19,0) |
| CASTLE:3 | 4 | Joshua | 23 | 50 | 10 | A 23-01 m0 @(5,4,0); B 01-07/18-23 m0 @(3,17,0); C 07-18 m1 @(6,28,0) |
| CASTLE:3 | 5 | Leof | 24 | 50 | 9 | A 23-01 m0 @(4,5,0); B 01-07/18-23 m0 @(5,17,0); C 07-18 m1 @(6,27,0) |
| CASTLE:3 | 7 | Vigil | 25 | 68 | 24 | A 18-09 m0 @(3,21,0); B 09-13/15-18 m1 @(30,10,0); C 13-15 m0 @(2,20,0) |
| CASTLE:4 | 3 | Squire Jimmy | 28 | 50 | 11 | A 19-07 m0 @(26,3,0); B 07-12/13-19 m1 @(4,2,0); C 12-13 m0 @(15,10,0) |
| CASTLE:4 | 4 | Kurt | 26 | 50 | 16 | A 18-09 m0 @(26,9,0); B 09-11/13-18 m0 @(9,3,0); C 11-13 m0 @(29,5,0) |
| CASTLE:4 | 5 | Sir Adam the Torch | 27 | 68 | 13 | A 18-09 m0 @(28,9,0); B 09-11/13-18 m0 @(10,3,0); C 11-13 m0 @(29,7,0) |
| CASTLE:5 | 5 | Flint | 29 | 50 | 11 | A 19-05 m0 @(22,9,0); B 05-07/17-19 m0 @(24,23,0); C 07-17 m1 @(6,10,0) |
| CASTLE:5 | 6 | Glinkie | 30 | 40 | 18 | A 21-12 m0 @(22,6,0); B 12-19/21-21 m1 @(7,23,0); C 19-21 m0 @(27,25,0) |
| CASTLE:6 | 3 | Bandaii | 31 | 6C | 21 | A 21-03 m0 @(3,20,0); B 03-06/19-21 m0 @(14,4,0); C 06-19 m0 @(14,7,0) |
| CASTLE:6 | 4 | Ava | 32 | 6C | 15 | A 21-03 m0 @(6,20,0); B 03-06/19-21 m0 @(16,4,0); C 06-19 m0 @(16,7,0) |
| CASTLE:6 | 7 | Leona | 33 | 48 | 6 | A 00-00 m0 @(27,22,0); B 00-23/00-00 m0 @(27,22,0); C 23-00 m0 @(27,24,0) |
| CASTLE:7 | 6 | Ambrose | 34 | 48 | 13 | A 18-06 m0 @(1,23,0); B 06-11/13-18 m1 @(22,12,0); C 11-13 m0 @(5,9,0) |
| CASTLE:7 | 7 | Thorkin | 35 | 5C | 17 | A 01-09 m0 @(1,20,0); B 09-15/17-01 m0 @(3,7,0); C 15-17 m0 @(5,9,0) |
| CASTLE:7 | 8 | Scally | 36 | 44 | 16 | A 00-09 m0 @(1,28,0); B 09-11/18-00 m0 @(4,12,0); C 11-18 m2 @(12,30,0) |
| CASTLE:7 | 9 | Bidney | 37 | 44 | 16 | A 23-07 m0 @(1,26,0); B 07-11/18-23 m0 @(4,10,0); C 11-18 m2 @(12,15,0) |
| CASTLE:7 | 10 | Sven | 38 | 48 | 19 | A 01-09 m0 @(4,26,0); B 09-11/19-01 m0 @(5,9,0); C 11-19 m2 @(12,4,0) |
| CASTLE:7 | 11 | Lord Dalgrin | 39 | 44 | 14 | A 00-09 m0 @(4,28,0); B 09-11/13-00 m0 @(7,9,0); C 11-13 m0 @(17,2,0) |
| CASTLE:7 | 12 | Tierra | 40 | 48 | 31 | A 23-07 m0 @(7,28,0); B 07-11/17-23 m0 @(8,12,0); C 11-17 m0 @(8,23,0) |

### KEEP

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| KEEP:1 | 1 | Johne, Captain Johne. | 2 | 50 | 6 | A 21-06 m0 @(7,19,0); B 06-09/18-21 m0 @(21,5,0); C 09-18 m2 @(15,18,1) |
| KEEP:1 | 2 | Sir Simon | 3 | 50 | 9 | A 21-06 m0 @(7,18,0); B 06-09/18-21 m0 @(22,5,0); C 09-18 m2 @(15,13,0) |
| KEEP:1 | 4 | Maxwell | 30 | 48 | 17 | A 21-07 m0 @(19,16,0); B 07-09/19-21 m0 @(22,7,0); C 09-19 m2 @(9,18,1) |
| KEEP:1 | 5 | Dupre | 31 | 48 | 13 | A 23-07 m0 @(19,20,0); B 07-09/19-23 m0 @(21,7,0); C 09-19 m2 @(21,18,1) |
| KEEP:2 | 1 | Lady Tessa | 4 | 50 | 8 | A 21-05 m0 @(13,2,0); B 05-07/19-21 m0 @(24,14,0); C 07-19 m0 @(15,6,0) |
| KEEP:2 | 2 | Lord Seggallion | 5 | 40 | 18 | A 21-05 m0 @(4,15,0); B 05-07/19-21 m0 @(24,12,0); C 07-19 m0 @(8,18,0) |
| KEEP:2 | 3 | Temme | 6 | 68 | 12 | A 19-09 m0 @(4,13,0); B 09-11/13-19 m0 @(10,19,0); C 11-13 m0 @(23,12,0) |
| KEEP:2 | 4 | Dufus | 7 | 50 | 11 | A 23-05 m0 @(4,11,0); B 05-11/13-23 m1 @(21,16,0); C 11-13 m0 @(23,14,0) |
| KEEP:3 | 1 | Quintin | 8 | 48 | 9 | A 21-05 m0 @(7,23,0); B 05-07/19-21 m0 @(21,8,0); C 07-19 m2 @(11,8,0) |
| KEEP:3 | 2 | Thrud | 9 | 40 | 12 | A 21-05 m0 @(10,23,0); B 05-07/19-21 m0 @(21,10,0); C 07-19 m2 @(22,22,0) |
| KEEP:4 | 4 | Elistaria | 10 | D8 | 15 | A 00-06 m4 @(15,25,0); B 06-12/18-00 m4 @(15,25,0); C 12-18 m4 @(15,25,0) |
| KEEP:5 | 5 | Balinor | 11 | 40 | 4 | A 21-07 m0 @(22,7,2); B 07-09/19-21 m0 @(20,8,0); C 09-19 m0 @(16,22,2) |
| KEEP:5 | 6 | Lady Janell | 12 | 40 | 18 | A 21-07 m0 @(22,9,2); B 07-09/19-21 m0 @(20,10,0); C 09-19 m0 @(14,22,2) |
| KEEP:5 | 7 | Gardner | 26 | 50 | 10 | A 19-05 m0 @(7,19,1); B 05-07/17-19 m0 @(11,9,1); C 07-17 m0 @(15,9,2) |
| KEEP:5 | 8 | Rollo | 14 | 50 | 18 | A 19-09 m0 @(22,17,1); B 09-11/13-19 m1 @(20,17,0); C 11-13 m0 @(20,8,0) |
| KEEP:5 | 9 | Lady Hayden. | 15 | 50 | 17 | A 23-09 m0 @(22,19,1); B 09-11/13-23 m0 @(15,18,2); C 11-13 m0 @(20,10,0) |
| KEEP:5 | 18 | Lord Shalineth | 13 | 50 | 10 | A 19-06 m0 @(21,23,1); B 06-13/15-19 m1 @(9,7,2); C 13-15 m0 @(9,9,1) |
| KEEP:5 | 19 | Sir Sean | 27 | 40 | 14 | A 18-09 m0 @(22,11,1); B 09-11/13-18 m0 @(23,10,1); C 11-13 m0 @(22,11,1) |
| KEEP:6 | 10 | Lord R'hien | 16 | 50 | 12 | A 21-05 m0 @(3,8,1); B 05-07/19-21 m0 @(25,7,0); C 07-19 m0 @(25,7,1) |
| KEEP:6 | 11 | Lord Michael | 17 | 50 | 16 | A 00-06 m0 @(26,18,0); B 06-17/19-00 m1 @(22,6,0); C 17-19 m0 @(26,18,0) |
| KEEP:6 | 12 | Cory | 18 | 58 | 17 | A 19-07 m0 @(26,24,0); B 07-11/13-19 m2 @(15,16,0); C 11-13 m0 @(25,13,0) |
| KEEP:6 | 13 | Hardluck | 19 | 50 | 8 | A 21-05 m0 @(26,24,1); B 05-07/19-21 m0 @(15,3,1); C 07-19 m0 @(26,11,1) |
| KEEP:6 | 14 | Barbra | 20 | 44 | 14 | A 23-07 m0 @(3,24,1); B 07-09/21-23 m0 @(25,7,0); C 09-21 m2 @(15,23,2) |
| KEEP:6 | 15 | Mariah | 28 | 44 | 13 | A 19-11 m0 @(3,20,0); B 11-13/15-19 m0 @(24,11,1); C 13-15 m0 @(25,9,0) |
| KEEP:6 | 16 | Sentri | 32 | 44 | 22 | A 21-07 m0 @(9,27,1); B 07-09/19-21 m0 @(26,11,0); C 09-19 m0 @(23,11,1) |
| KEEP:7 | 9 | Tim | 21 | 50 | 24 | A 00-00 m0 @(17,4,0); B 00-00/00-00 m0 @(17,4,0); C 00-00 m0 @(17,4,0) |
| KEEP:7 | 11 | Toede | 22 | 50 | 12 | A 21-07 m0 @(8,27,1); B 07-09/19-21 m0 @(17,5,1); C 09-19 m0 @(6,6,1) |
| KEEP:7 | 16 | Lord Malone | 23 | 48 | 14 | A 21-07 m0 @(22,22,1); B 07-09/19-21 m0 @(13,5,1); C 09-19 m1 @(21,25,1) |
| KEEP:7 | 17 | Monsieur Loubet | 24 | 50 | 9 | A 23-05 m0 @(23,21,0); B 05-13/15-23 m1 @(23,7,1); C 13-15 m2 @(15,5,1) |
| KEEP:7 | 18 | Kristi | 25 | 50 | 13 | A 19-05 m0 @(23,18,0); B 05-07/17-19 m0 @(15,16,-1); C 07-17 m0 @(17,7,1) |
| KEEP:7 | 19 | Toshi | 29 | 48 | 13 | A 21-07 m0 @(20,18,0); B 07-09/19-21 m0 @(13,7,1); C 09-19 m1 @(21,26,1) |

## 4. Generic And Reserved Slots

The roster also contains occupied slots that are not named by a real `.TLK`
entry. They are retained here as counts because they matter for NPC placement,
collision, guards, hostiles, hidden actors, and scenery-like people. They are
not enumerated row-by-row because the task target is the named roster.

| Family | Dialog id 0 | Dialog id 1 | High/special dialog ids | Total generic/reserved |
|---|---:|---:|---:|---:|
| `TOWNE` | 31 | 1 | 28 | 60 |
| `DWELLING` | 3 | 1 | 0 | 4 |
| `CASTLE` | 42 | 1 | 25 | 68 |
| `KEEP` | 50 | 1 | 6 | 57 |
| **Total** | **126** | **4** | **59** | **189** |

Dialog id 0 is the ordinary no-dialogue value. Dialog id 1 is the universal
sentinel carried by each `.TLK` header. High/special ids in the observed roster
are `129` through `136` and `255`; they do not resolve to real `.TLK` records
in the paired file and likely mark guards, generic role actors, hostile actors,
or non-speaking schedule participants.

Two named cases are intentionally special:

- Lord British's roster slot in `CASTLE:0` has a no-dialogue id; his throne-room
  conversation is handled by engine logic rather than by a normal `CASTLE.TLK`
  blob.
- Lord Blackthorn's castle reuses the same Gorn dialogue id for multiple guard
  roster slots. Those guards are interchangeable schedule actors sharing one
  authored dialogue record.
- The Blackthorn capture audience and rescue/refuge scenes do not use this
  roster as ordinary town NPC scheduling state; they are cinematic overlay
  flows specified in `systems/blackthorn.md`.

Excluding the reserved slot-zero rows, the occupied roster uses 25 distinct role
tags:

`01`, `0E`, `10`, `11`, `1B`, `1E`, `28`, `40`, `44`, `48`, `50`, `54`,
`58`, `5C`, `68`, `6C`, `70`, `78`, `90`, `94`, `B5`, `B6`, `B8`, `D8`,
`FC`.

Slot zero can also carry nonzero sentinel tags in the shipped files. Those
sentinel rows are structural markers, not live NPCs, and the scheduler still
starts at slot one.

| Tag | Engine-facing role |
|---:|---|
| `01` | Default-person sentinel; the sprite-link helper forces the standard person tile instead of using the tag as a direct sprite class. |
| `0E` | Rare walking actor class; eligible for the town activation mask type gate. |
| `10`, `11` | Unmounted horse / horse-frame classes used in stable or paddock contexts. |
| `1B` | Unmounted magic-carpet class. |
| `1E` | Rare static/special actor class. |
| `28` | Rare vehicle or fixture-like actor class. |
| `40` | Noble/lady-style human class. |
| `44` | Lord, scholar, or sage-style human class. |
| `48` | Knight/fighter/companion-style human class. |
| `50` | Generic adult townsperson class; the most common named-NPC sprite class. |
| `54` | Shared shop/service actor class, paired with shop-trigger dialogue ids. |
| `58`, `5C` | Uncommon human actor classes; keep the tag when no local name clarifies the role. |
| `68` | Bard, jester, or performer-style human class. |
| `6C` | Rare nobility or dignitary-style human class. |
| `70` | Silent guard or patrol class; guard-like tags participate in alarm/guard handling. |
| `78` | Court-jester class. |
| `90` | Monster or non-humanoid actor class used for hostile or unusual town actors. |
| `94` | Animal, pet, or livestock-style actor class. |
| `B5`, `B6`, `B8` | Monster-variant actor classes. |
| `D8` | Lich, wizard, or death-mage style actor class. |
| `FC` | Shadow Lord actor class (`catalogs/monster-bestiary.md`, class 47). Never shipped in a roster; allocated dynamically by the town-entry Shadowlord install. |

The tag byte is a sprite and occupancy class, not the schedule AI byte and not
the dialogue id. A compatible engine should preserve the byte value even when a
human-facing label is generic, because collision, sprite selection, visibility,
guard handling, and special town setup all consume the tag semantically.

## 5. Boundaries And Remaining Work

The following boundaries are explicit and intentional.

1. **Punctuation-only name.** `CASTLE:1` slot 25 resolves to a real dialogue
   record whose first display entry is punctuation rather than a conventional
   personal name. The catalog preserves that authored display entry as `....`;
   this is not a missing-person-name placeholder.
2. **Keyword graph.** Keyword counts are included, but keyword names and
   response text are deliberately omitted. That belongs in a quest-graph pass
   and must be summarized without dumping dialogue strings.
3. **Anonymous hidden actors.** Some hidden-mask entries in
   `systems/npc-schedules.md` point at occupied slots that do not have a
   personal name in the public roster. Those slots should be identified by
   their tag-derived role labels from Section 4, such as shop/service actor,
   silent guard or patrol, animal or livestock actor, monster-variant actor,
   or Avatar/free-slot sentinel. This is a presentation/catalog label boundary,
   not a missing schedule behavior.

## 6. Sources

This catalog is cleanroom prose derived from the local analysis notes and the
existing public specs. It does not reproduce disassembly, decompiled code, data
offsets, raw dialogue text, or private note prose.

Private analysis sources used:

- `u5-decomp/formats/npc-tlk-pth.md` - `.NPC` block structure, `.TLK`
  leading-pair/header structure, name-entry decoding rules, AI-byte
  enumeration, type-byte sprite-class interpretation, and file counts.
- `u5-decomp/formats/maps.md` - scene-byte to storage-family/sub-map mapping
  and the Lord British / Blackthorn / Gorn roster peculiarities.
- `u5-spec/catalogs/gazetteer.md` - public scene-name bindings for the roster
  keys, including blank resident-name boundaries.
- `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md` - class-family roster load,
  schedule/type/dialogue array loading, and slot-zero convention.
- `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md` - the
  three-waypoint/four-boundary schedule selection rule.
- `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md` - schedule
  consumer, type-byte occupancy use, and per-tick movement model.
- `u5-decomp/functions/TOWN_OVL/0x0000_npc_in_class_filter.md`,
  `u5-decomp/functions/TOWN_OVL/0x0052_npc_set_class_bit.md`, and
  `u5-decomp/functions/TOWN_OVL/0x0958_npc_scatter.md` - town activation,
  guard/alarm, and death-mask type filters.
- `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md` - dialogue id lookup
  against the `.TLK` header and blob load.
- `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md` - text-byte
  classification and common-word dictionary behaviour used to recover display
  names.

Public spec cross-checks:

- `u5-spec/formats/npc.md`
- `u5-spec/formats/tlk.md`
- `u5-spec/systems/npc-schedules.md`
- `u5-spec/systems/conversation.md`
- `u5-spec/systems/town-mode.md`
- `u5-spec/catalogs/tile-catalog.md`

## 7. Cross-References

- `formats/npc.md` - storage format for the schedule, tag, and dialogue-index
  fields listed here.
- `formats/tlk.md` - dialogue file format and the meaning of `Dlg` and `Kw`.
- `systems/npc-schedules.md` - runtime interpretation of the schedule column.
- `systems/conversation.md` - Talk command, keyword loop, and dialogue-control
  runtime.
- `catalogs/tile-catalog.md` - broad NPC tile range and role-tag follow-up.
- `catalogs/gazetteer.md` - final place names for each `Loc` key.
