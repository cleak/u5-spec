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
| `TOWNE` | 48 | 107 | 48 | 59 |
| `DWELLING` | 15 | 18 | 15 | 3 |
| `CASTLE` | 40 | 112 | 45 | 67 |
| `KEEP` | 32 | 88 | 32 | 56 |
| **Total** | **135** | **325** | **140** | **185** |

All 135 real `.TLK` entries are referenced by at least one occupied roster
slot. The named roster-slot count is higher than the unique `.TLK` count because
`CASTLE:1` uses one guard dialogue record — id 12, whose authored display name
is the punctuation string `....` — for six roster slots.

**Retraction.** Earlier revisions of this catalog bound each roster slot to the
wrong dialogue record. They read the `.TLK` header as `(offset, id)` pairs behind
a "count plus sentinel" leading pair, which shifts every binding by one id and
leaves the last blob of each class file unreferenced. The corrected header
contract is in `formats/tlk.md` Section 6: entries are `(id, offset)` pairs and
ids run `1..npc_count`. Consequently the four families hold 48/15/40/32 rather
than 47/14/39/31 dialogue records, dialog index `1` is an ordinary NPC rather
than a sentinel, and four NPCs that the old counts dropped entirely — Wartow,
Sir Arbuthnot, Geoffrey, and Julia — are restored below. Every `NPC`, `Dlg`, and
`Kw` cell in Section 3 was re-derived; the `Loc`, `Slot`, `Tag`, and `Schedule`
columns are unchanged, because those come from the `.NPC` roster and were never
affected.

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
from this value, and the shipped description string for that sprite is what
Section 4's role column now publishes. `01` forces the default human/person
sprite. `FC` is the Shadow Lord actor class; three shipped roster slots carry it
(Stonegate slots 1-3, one per Shadowlord), and the town-entry Shadowlord install
writes it into a live slot as well (`systems/town-mode.md` Section 13). Two
earlier claims about `FC` are retracted: that it is a runtime player mirror, and
that it appears in no shipped roster slot. The spec gives the player no NPC-slot
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
| TOWNE:0 | 3 | Zachariah | 1 | 40 | 16 | A 05-15 m0 @(13,17,0); B 15-17/18-05 m0 @(16,13,1); C 17-18 m0 @(20,23,0) |
| TOWNE:0 | 4 | Malifora | 2 | 50 | 14 | A 19-09 m0 @(8,5,0); B 09-12/13-19 m0 @(9,9,0); C 12-13 m0 @(20,21,0) |
| TOWNE:0 | 5 | Malik | 3 | 68 | 22 | A 19-09 m0 @(5,5,0); B 09-12/13-19 m2 @(15,24,0); C 12-13 m0 @(20,23,0) |
| TOWNE:0 | 11 | Donn Piatt | 4 | 50 | 13 | A 19-11 m0 @(9,24,1); B 11-15/17-19 m4 @(15,25,0); C 15-17 m0 @(20,23,0) |
| TOWNE:0 | 12 | Lord Stuart the Hungry | 5 | 50 | 13 | A 00-09 m0 @(19,24,1); B 09-11/13-00 m0 @(23,21,0); C 11-13 m0 @(19,24,1) |
| TOWNE:1 | 4 | Justin | 7 | 50 | 16 | A 23-09 m0 @(1,5,1); B 09-18/19-23 m1 @(8,1,0); C 18-19 m0 @(4,5,0) |
| TOWNE:1 | 5 | Eb | 8 | 68 | 20 | A 21-09 m0 @(5,4,1); B 09-18/19-21 m1 @(5,7,0); C 18-19 m0 @(3,5,0) |
| TOWNE:1 | 6 | Terrance | 9 | 50 | 17 | A 19-05 m0 @(23,16,0); B 05-12/13-19 m1 @(26,26,0); C 12-13 m0 @(24,16,1) |
| TOWNE:1 | 7 | Telila | 10 | 50 | 13 | A 19-06 m0 @(23,15,0); B 06-12/13-19 m1 @(30,5,0); C 12-13 m0 @(25,16,1) |
| TOWNE:1 | 8 | Gwenno | 11 | 50 | 17 | A 18-06 m0 @(5,21,1); B 06-11/12-18 m1 @(3,29,0); C 11-12 m0 @(3,8,0) |
| TOWNE:1 | 13 | Annon | 12 | 40 | 14 | A 19-07 m0 @(21,6,1); B 07-11/13-19 m1 @(15,6,1); C 11-13 m0 @(3,10,0) |
| TOWNE:1 | 14 | Greyson | 6 | 44 | 15 | A 21-07 m0 @(24,8,1); B 07-09/19-21 m0 @(3,10,0); C 09-19 m1 @(15,14,0) |
| TOWNE:2 | 4 | Bullwier | 13 | 50 | 13 | A 17-07 m0 @(7,14,1); B 07-12/13-17 m1 @(8,22,0); C 12-13 m0 @(11,7,0) |
| TOWNE:2 | 8 | Trian | 14 | 5C | 13 | A 21-11 m0 @(20,21,1); B 11-15/17-21 m0 @(9,7,0); C 15-17 m0 @(11,9,0) |
| TOWNE:2 | 9 | Goeth | 15 | 40 | 21 | A 18-09 m0 @(1,1,0); B 09-11/13-18 m2 @(2,2,1); C 11-13 m1 @(3,2,0) |
| TOWNE:2 | 10 | Thorne | 16 | 48 | 18 | A 19-09 m0 @(9,22,1); B 09-13/15-19 m2 @(13,17,0); C 13-15 m0 @(17,9,0) |
| TOWNE:3 | 7 | Judge Dryden | 19 | 50 | 19 | A 17-09 m0 @(29,15,0); B 09-13/15-17 m0 @(25,11,0); C 13-15 m0 @(3,5,0) |
| TOWNE:3 | 8 | Jeremy | 20 | 50 | 18 | A 23-09 m0 @(4,16,0); B 09-11/21-23 m0 @(25,7,0); C 11-21 m1 @(3,11,0) |
| TOWNE:3 | 9 | Jerone | 21 | 48 | 24 | A 21-07 m0 @(25,3,0); B 07-09/11-21 m1 @(24,4,0); C 09-11 m1 @(24,4,0) |
| TOWNE:3 | 10 | Felespar | 22 | 40 | 18 | A 19-09 m0 @(20,3,0); B 09-12/13-19 m0 @(22,4,0); C 12-13 m1 @(21,4,0) |
| TOWNE:3 | 11 | Mario | 23 | 44 | 18 | A 00-00 m0 @(18,14,0); B 00-00/00-00 m0 @(18,14,0); C 00-00 m0 @(18,14,0) |
| TOWNE:3 | 12 | Aleyn | 24 | 68 | 9 | A 00-00 m0 @(20,16,0); B 00-00/00-00 m0 @(20,16,0); C 00-00 m0 @(20,16,0) |
| TOWNE:3 | 13 | Landon | 18 | 44 | 14 | A 09-15 m0 @(19,24,-1); B 15-23/01-09 m1 @(22,1,0); C 23-01 m0 @(17,28,-1) |
| TOWNE:3 | 14 | Chamfort | 17 | 48 | 14 | A 18-09 m0 @(7,30,0); B 09-15/17-18 m1 @(2,23,0); C 15-17 m0 @(2,29,0) |
| TOWNE:3 | 19 | Greymarch | 36 | 48 | 12 | A 00-00 m1 @(29,3,0); B 00-00/00-00 m1 @(29,3,0); C 00-00 m1 @(29,3,0) |
| TOWNE:3 | 21 | Jaana | 35 | 44 | 9 | A 01-09 m0 @(19,22,-1); B 09-11/23-01 m0 @(17,30,-1); C 11-23 m2 @(19,27,-1) |
| TOWNE:4 | 1 | Tactus | 25 | 48 | 15 | A 21-09 m0 @(24,25,1); B 09-15/17-21 m1 @(27,26,0); C 15-17 m0 @(27,24,1) |
| TOWNE:4 | 3 | Fiona | 26 | 50 | 20 | A 19-06 m0 @(7,27,1); B 06-07/18-19 m2 @(12,17,0); C 07-18 m1 @(25,8,0) |
| TOWNE:4 | 6 | Rew | 27 | 68 | 19 | A 21-05 m0 @(23,4,0); B 05-12/13-21 m0 @(5,6,0); C 12-13 m0 @(26,13,0) |
| TOWNE:4 | 7 | Fenelon | 28 | 50 | 19 | A 21-05 m0 @(26,6,0); B 05-12/13-21 m0 @(7,6,0); C 12-13 m0 @(26,11,0) |
| TOWNE:4 | 8 | Lady Sahra | 29 | 50 | 13 | A 19-07 m0 @(23,6,0); B 07-11/13-19 m1 @(6,26,0); C 11-13 m0 @(25,11,0) |
| TOWNE:4 | 9 | Delwyn | 30 | 6C | 9 | A 19-09 m0 @(26,8,0); B 09-17/18-19 m4 @(13,19,0); C 17-18 m0 @(26,13,0) |
| TOWNE:5 | 3 | Woolfe | 31 | 48 | 20 | A 18-07 m0 @(24,12,1); B 07-12/13-18 m1 @(25,7,0); C 12-13 m0 @(23,15,0) |
| TOWNE:5 | 5 | Sindar... | 32 | 40 | 8 | A 06-00 m0 @(22,25,0); B 00-01/05-06 m0 @(25,7,1); C 01-05 m2 @(29,2,1) |
| TOWNE:5 | 6 | Jimmy | 33 | 68 | 26 | A 15-12 m0 @(24,25,0); B 12-12/13-15 m0 @(5,26,0); C 12-13 m0 @(24,14,0) |
| TOWNE:5 | 9 | Gruman | 34 | 48 | 13 | A 23-06 m0 @(11,30,0); B 06-09/15-23 m1 @(15,29,1); C 09-15 m2 @(29,2,1) |
| TOWNE:6 | 4 | Froed | 37 | 68 | 19 | A 00-00 m3 @(5,22,0); B 00-00/00-00 m3 @(5,22,0); C 00-00 m3 @(5,22,0) |
| TOWNE:6 | 5 | Flain | 38 | 40 | 15 | A 00-00 m2 @(15,14,1); B 00-00/00-00 m2 @(15,14,1); C 00-00 m2 @(15,14,1) |
| TOWNE:6 | 6 | Kindor | 39 | 44 | 9 | A 19-19 m0 @(26,24,0); B 19-17/19-19 m0 @(26,24,0); C 17-19 m0 @(28,25,0) |
| TOWNE:6 | 7 | Saul | 40 | 50 | 13 | A 18-09 m0 @(24,9,1); B 09-17/18-18 m2 @(17,5,0); C 17-18 m0 @(27,25,0) |
| TOWNE:7 | 3 | Yasuda | 43 | 50 | 8 | A 21-05 m0 @(3,28,0); B 05-11/12-21 m1 @(9,28,0); C 11-12 m0 @(27,18,0) |
| TOWNE:7 | 4 | Tetsuo | 44 | 50 | 8 | A 19-05 m0 @(2,13,0); B 05-12/13-19 m1 @(2,17,0); C 12-13 m0 @(25,21,0) |
| TOWNE:7 | 5 | Fumiko | 45 | 50 | 9 | A 19-05 m0 @(12,3,0); B 05-12/13-19 m1 @(4,17,0); C 12-13 m0 @(25,19,0) |
| TOWNE:7 | 6 | Kaiko | 46 | 50 | 12 | A 21-06 m0 @(4,2,0); B 06-12/13-21 m1 @(3,18,0); C 12-13 m0 @(27,16,0) |
| TOWNE:7 | 7 | Katrina | 47 | 50 | 8 | A 23-09 m0 @(28,12,0); B 09-11/13-23 m1 @(26,18,0); C 11-13 m0 @(23,4,0) |
| TOWNE:7 | 8 | Wartow | 48 | 50 | 18 | A 21-05 m0 @(28,29,0); B 05-12/13-21 m1 @(22,30,0); C 12-13 m0 @(29,28,0) |
| TOWNE:7 | 9 | Tomoka | 41 | 50 | 15 | A 19-05 m0 @(2,10,0); B 05-12/13-19 m1 @(5,16,0); C 12-13 m0 @(27,18,0) |
| TOWNE:7 | 10 | Shirita | 42 | 50 | 14 | A 23-09 m0 @(28,9,0); B 09-17/23-23 m1 @(23,4,0); C 17-23 m0 @(25,19,0) |

### DWELLING

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| DWELLING:0 | 1 | Jennifer | 1 | 68 | 9 | A 07-17 m0 @(24,16,0); B 17-19/05-07 m0 @(21,16,0); C 19-05 m2 @(7,16,2) |
| DWELLING:0 | 2 | Jotham | 2 | 50 | 18 | A 07-17 m0 @(24,18,0); B 17-19/05-07 m0 @(21,18,0); C 19-05 m0 @(14,15,0) |
| DWELLING:1 | 1 | Windmire | 3 | 50 | 16 | A 19-05 m2 @(16,19,2); B 05-07/17-19 m0 @(19,12,0); C 07-17 m0 @(12,10,0) |
| DWELLING:1 | 2 | Emilly | 4 | 50 | 12 | A 19-05 m0 @(12,8,0); B 05-07/17-19 m0 @(19,14,0); C 07-17 m2 @(16,19,2) |
| DWELLING:2 | 1 | Anthony | 5 | 68 | 22 | A 21-07 m0 @(20,9,0); B 07-09/19-21 m0 @(11,12,0); C 09-19 m2 @(3,15,0) |
| DWELLING:2 | 2 | Charlotte | 6 | 50 | 17 | A 21-05 m0 @(18,9,0); B 05-09/17-21 m0 @(11,10,0); C 09-17 m2 @(16,17,2) |
| DWELLING:2 | 3 | David | 7 | 50 | 18 | A 07-17 m0 @(18,11,0); B 17-19/05-07 m0 @(11,12,0); C 19-05 m2 @(14,17,2) |
| DWELLING:2 | 4 | Lord Kenneth | 14 | 50 | 8 | A 21-09 m0 @(9,21,0); B 09-11/13-21 m1 @(11,18,0); C 11-13 m0 @(11,10,0) |
| DWELLING:2 | 5 | Sir Arbuthnot | 15 | 48 | 19 | A 23-09 m0 @(9,19,0); B 09-11/13-23 m0 @(20,17,0); C 11-13 m0 @(11,12,0) |
| DWELLING:3 | 1 | Gregory | 8 | 50 | 3 | A 07-17 m0 @(9,11,0); B 17-19/05-07 m0 @(20,12,0); C 19-05 m2 @(18,12,2) |
| DWELLING:3 | 2 | Jacqueline | 9 | 50 | 4 | A 07-17 m0 @(9,14,0); B 17-19/05-07 m0 @(20,14,0); C 19-05 m2 @(12,12,2) |
| DWELLING:4 | 4 | Smith | 13 | 11 | 12 | A 00-00 m1 @(27,3,0); B 00-00/00-00 m1 @(27,3,0); C 00-00 m1 @(27,3,0) |
| DWELLING:5 | 1 | Sutek | 10 | 40 | 2 | A 21-09 m0 @(12,16,0); B 09-13/15-21 m0 @(14,13,0); C 13-15 m0 @(3,3,0) |
| DWELLING:6 | 1 | Sin'Vraal | 11 | D8 | 14 | A 07-18 m1 @(6,9,0); B 18-19/06-07 m0 @(24,7,0); C 19-06 m1 @(15,15,0) |
| DWELLING:7 | 1 | Grendel | 12 | 90 | 11 | A 06-12 m2 @(15,14,0); B 12-18/00-06 m2 @(15,14,0); C 18-00 m2 @(15,14,0) |

### CASTLE

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| CASTLE:0 | 13 | Alistair the Bard | 1 | 5C | 11 | A 23-11 m0 @(9,7,0); B 11-15/17-23 m0 @(11,23,0); C 15-17 m0 @(9,26,0) |
| CASTLE:0 | 14 | Stephen | 2 | 50 | 13 | A 23-07 m0 @(12,10,0); B 07-15/17-23 m1 @(9,22,0); C 15-17 m0 @(9,24,0) |
| CASTLE:0 | 18 | Treanna | 3 | 68 | 18 | A 18-07 m0 @(22,18,0); B 07-13/15-18 m1 @(21,24,0); C 13-15 m0 @(9,24,0) |
| CASTLE:0 | 19 | Margaret | 4 | 50 | 19 | A 18-11 m0 @(7,25,1); B 11-15/17-18 m1 @(20,23,1); C 15-17 m0 @(21,20,1) |
| CASTLE:0 | 20 | Desiree | 5 | 68 | 12 | A 18-11 m0 @(7,27,1); B 11-15/17-18 m1 @(19,25,1); C 15-17 m0 @(21,18,1) |
| CASTLE:0 | 21 | Drudgeworth | 6 | 48 | 18 | A 00-00 m7 @(12,10,-1); B 00-00/00-00 m7 @(12,10,-1); C 00-00 m7 @(12,10,-1) |
| CASTLE:0 | 26 | Saduj | 7 | 50 | 23 | A 03-23 m0 @(13,19,-1); B 23-00/01-03 m1 @(15,20,2); C 00-01 m1 @(15,10,2) |
| CASTLE:0 | 27 | Stillwelt | 8 | 70 | 7 | A 23-03 m0 @(10,27,1); B 03-13/15-23 m4 @(15,25,2); C 13-15 m0 @(19,18,1) |
| CASTLE:0 | 29 | Chuckles | 9 | 58 | 14 | A 23-07 m0 @(9,12,0); B 07-17/18-23 m1 @(15,24,0); C 17-18 m0 @(10,7,1) |
| CASTLE:1 | 5 | Blackthorn | 10 | 78 | 6 | A 23-07 m0 @(11,8,2); B 07-13/15-23 m0 @(15,15,2); C 13-15 m1 @(15,23,3) |
| CASTLE:1 | 16 | Gorn | 11 | 48 | 6 | A 00-06 m4 @(5,7,-1); B 06-12/18-00 m4 @(5,7,-1); C 12-18 m4 @(5,7,-1) |
| CASTLE:1 | 19 | .... | 12 | 50 | 9 | A 00-00 m0 @(3,2,1); B 00-00/00-00 m0 @(3,2,1); C 00-00 m0 @(3,2,1) |
| CASTLE:1 | 20 | .... | 12 | 50 | 9 | A 00-00 m0 @(27,2,1); B 00-00/00-00 m0 @(27,2,1); C 00-00 m0 @(27,2,1) |
| CASTLE:1 | 21 | .... | 12 | 50 | 9 | A 00-00 m0 @(23,18,1); B 00-00/00-00 m0 @(23,18,1); C 00-00 m0 @(23,18,1) |
| CASTLE:1 | 22 | .... | 12 | 50 | 9 | A 00-00 m0 @(7,18,1); B 00-00/00-00 m0 @(7,18,1); C 00-00 m0 @(7,18,1) |
| CASTLE:1 | 23 | .... | 12 | 50 | 9 | A 00-00 m0 @(11,12,2); B 00-00/00-00 m0 @(11,12,2); C 00-00 m0 @(11,12,2) |
| CASTLE:1 | 24 | .... | 12 | 50 | 9 | A 00-00 m0 @(19,12,2); B 00-00/00-00 m0 @(19,12,2); C 00-00 m0 @(19,12,2) |
| CASTLE:1 | 25 | Kraw | 13 | 50 | 8 | A 19-07 m0 @(22,4,0); B 07-11/13-19 m1 @(8,10,0); C 11-13 m0 @(12,21,1) |
| CASTLE:1 | 26 | Weblock | 14 | 40 | 15 | A 19-06 m0 @(19,11,0); B 06-13/15-19 m0 @(15,6,1); C 13-15 m0 @(24,12,0) |
| CASTLE:1 | 29 | Gallrot | 15 | 50 | 12 | A 18-09 m0 @(22,6,0); B 09-15/17-18 m1 @(15,18,1); C 15-17 m0 @(12,23,1) |
| CASTLE:1 | 30 | Foulwell | 16 | 58 | 11 | A 23-07 m0 @(15,15,2); B 07-13/15-23 m1 @(15,18,2); C 13-15 m0 @(10,21,1) |
| CASTLE:1 | 31 | Hassad | 17 | 40 | 19 | A 00-00 m2 @(25,7,-1); B 00-00/00-00 m2 @(25,7,-1); C 00-00 m2 @(25,7,-1) |
| CASTLE:2 | 1 | Camile | 18 | 50 | 20 | A 18-06 m0 @(4,30,0); B 06-12/13-18 m1 @(4,20,0); C 12-13 m0 @(2,29,0) |
| CASTLE:2 | 2 | Phillip | 19 | 50 | 9 | A 17-05 m0 @(29,26,0); B 05-11/13-17 m1 @(21,22,0); C 11-13 m0 @(23,4,0) |
| CASTLE:2 | 3 | Christopher | 20 | 50 | 16 | A 17-05 m0 @(27,28,0); B 05-11/13-17 m1 @(21,28,0); C 11-13 m0 @(25,4,0) |
| CASTLE:3 | 2 | Thentis | 21 | 50 | 21 | A 23-01 m0 @(4,3,0); B 01-06/19-23 m0 @(27,25,0); C 06-19 m1 @(28,19,0) |
| CASTLE:3 | 3 | Joshua | 22 | 50 | 10 | A 23-01 m0 @(3,4,0); B 01-06/19-23 m0 @(27,29,0); C 06-19 m1 @(26,19,0) |
| CASTLE:3 | 4 | Leof | 23 | 50 | 9 | A 23-01 m0 @(5,4,0); B 01-07/18-23 m0 @(3,17,0); C 07-18 m1 @(6,28,0) |
| CASTLE:3 | 5 | Vigil | 24 | 50 | 24 | A 23-01 m0 @(4,5,0); B 01-07/18-23 m0 @(5,17,0); C 07-18 m1 @(6,27,0) |
| CASTLE:3 | 7 | Kurt | 25 | 68 | 16 | A 18-09 m0 @(3,21,0); B 09-13/15-18 m1 @(30,10,0); C 13-15 m0 @(2,20,0) |
| CASTLE:4 | 3 | Flint | 28 | 50 | 11 | A 19-07 m0 @(26,3,0); B 07-12/13-19 m1 @(4,2,0); C 12-13 m0 @(15,10,0) |
| CASTLE:4 | 4 | Sir Adam the Torch | 26 | 50 | 13 | A 18-09 m0 @(26,9,0); B 09-11/13-18 m0 @(9,3,0); C 11-13 m0 @(29,5,0) |
| CASTLE:4 | 5 | Squire Jimmy | 27 | 68 | 11 | A 18-09 m0 @(28,9,0); B 09-11/13-18 m0 @(10,3,0); C 11-13 m0 @(29,7,0) |
| CASTLE:5 | 5 | Glinkie | 29 | 50 | 18 | A 19-05 m0 @(22,9,0); B 05-07/17-19 m0 @(24,23,0); C 07-17 m1 @(6,10,0) |
| CASTLE:5 | 6 | Bandaii | 30 | 40 | 21 | A 21-12 m0 @(22,6,0); B 12-19/21-21 m1 @(7,23,0); C 19-21 m0 @(27,25,0) |
| CASTLE:6 | 3 | Ava | 31 | 6C | 15 | A 21-03 m0 @(3,20,0); B 03-06/19-21 m0 @(14,4,0); C 06-19 m0 @(14,7,0) |
| CASTLE:6 | 4 | Leona | 32 | 6C | 6 | A 21-03 m0 @(6,20,0); B 03-06/19-21 m0 @(16,4,0); C 06-19 m0 @(16,7,0) |
| CASTLE:6 | 7 | Ambrose | 33 | 48 | 13 | A 00-00 m0 @(27,22,0); B 00-23/00-00 m0 @(27,22,0); C 23-00 m0 @(27,24,0) |
| CASTLE:7 | 6 | Thorkin | 34 | 48 | 17 | A 18-06 m0 @(1,23,0); B 06-11/13-18 m1 @(22,12,0); C 11-13 m0 @(5,9,0) |
| CASTLE:7 | 7 | Scally | 35 | 5C | 16 | A 01-09 m0 @(1,20,0); B 09-15/17-01 m0 @(3,7,0); C 15-17 m0 @(5,9,0) |
| CASTLE:7 | 8 | Bidney | 36 | 44 | 16 | A 00-09 m0 @(1,28,0); B 09-11/18-00 m0 @(4,12,0); C 11-18 m2 @(12,30,0) |
| CASTLE:7 | 9 | Sven | 37 | 44 | 19 | A 23-07 m0 @(1,26,0); B 07-11/18-23 m0 @(4,10,0); C 11-18 m2 @(12,15,0) |
| CASTLE:7 | 10 | Lord Dalgrin | 38 | 48 | 14 | A 01-09 m0 @(4,26,0); B 09-11/19-01 m0 @(5,9,0); C 11-19 m2 @(12,4,0) |
| CASTLE:7 | 11 | Tierra | 39 | 44 | 12 | A 00-09 m0 @(4,28,0); B 09-11/13-00 m0 @(7,9,0); C 11-13 m0 @(17,2,0) |
| CASTLE:7 | 12 | Geoffrey | 40 | 48 | 16 | A 23-07 m0 @(7,28,0); B 07-11/17-23 m0 @(8,12,0); C 11-17 m0 @(8,23,0) |

### KEEP

| Loc | Slot | NPC | Dlg | Tag | Kw | Schedule |
|---|---:|---|---:|:---:|---:|---|
| KEEP:0 | 1 | Johne, Captain Johne. | 1 | 40 | 6 | A 19-07 m0 @(24,18,0); B 07-11/13-19 m4 @(15,14,0); C 11-13 m4 @(23,13,0) |
| KEEP:1 | 1 | Sir Simon | 2 | 50 | 9 | A 21-06 m0 @(7,19,0); B 06-09/18-21 m0 @(21,5,0); C 09-18 m2 @(15,18,1) |
| KEEP:1 | 2 | Lady Tessa | 3 | 50 | 8 | A 21-06 m0 @(7,18,0); B 06-09/18-21 m0 @(22,5,0); C 09-18 m2 @(15,13,0) |
| KEEP:1 | 4 | Dupre | 30 | 48 | 13 | A 21-07 m0 @(19,16,0); B 07-09/19-21 m0 @(22,7,0); C 09-19 m2 @(9,18,1) |
| KEEP:1 | 5 | Sentri | 31 | 48 | 10 | A 23-07 m0 @(19,20,0); B 07-09/19-23 m0 @(21,7,0); C 09-19 m2 @(21,18,1) |
| KEEP:2 | 1 | Lord Seggallion | 4 | 50 | 18 | A 21-05 m0 @(13,2,0); B 05-07/19-21 m0 @(24,14,0); C 07-19 m0 @(15,6,0) |
| KEEP:2 | 2 | Temme | 5 | 40 | 12 | A 21-05 m0 @(4,15,0); B 05-07/19-21 m0 @(24,12,0); C 07-19 m0 @(8,18,0) |
| KEEP:2 | 3 | Dufus | 6 | 68 | 11 | A 19-09 m0 @(4,13,0); B 09-11/13-19 m0 @(10,19,0); C 11-13 m0 @(23,12,0) |
| KEEP:2 | 4 | Quintin | 7 | 50 | 9 | A 23-05 m0 @(4,11,0); B 05-11/13-23 m1 @(21,16,0); C 11-13 m0 @(23,14,0) |
| KEEP:3 | 1 | Thrud | 8 | 48 | 12 | A 21-05 m0 @(7,23,0); B 05-07/19-21 m0 @(21,8,0); C 07-19 m2 @(11,8,0) |
| KEEP:3 | 2 | Elistaria | 9 | 40 | 15 | A 21-05 m0 @(10,23,0); B 05-07/19-21 m0 @(21,10,0); C 07-19 m2 @(22,22,0) |
| KEEP:4 | 4 | Balinor | 10 | D8 | 4 | A 00-06 m4 @(15,25,0); B 06-12/18-00 m4 @(15,25,0); C 12-18 m4 @(15,25,0) |
| KEEP:5 | 5 | Lady Janell | 11 | 40 | 18 | A 21-07 m0 @(22,7,2); B 07-09/19-21 m0 @(20,8,0); C 09-19 m0 @(16,22,2) |
| KEEP:5 | 6 | Lord Shalineth | 12 | 40 | 10 | A 21-07 m0 @(22,9,2); B 07-09/19-21 m0 @(20,10,0); C 09-19 m0 @(14,22,2) |
| KEEP:5 | 7 | Sir Sean | 26 | 50 | 14 | A 19-05 m0 @(7,19,1); B 05-07/17-19 m0 @(11,9,1); C 07-17 m0 @(15,9,2) |
| KEEP:5 | 8 | Lady Hayden. | 14 | 50 | 17 | A 19-09 m0 @(22,17,1); B 09-11/13-19 m1 @(20,17,0); C 11-13 m0 @(20,8,0) |
| KEEP:5 | 9 | Lord R'hien | 15 | 50 | 12 | A 23-09 m0 @(22,19,1); B 09-11/13-23 m0 @(15,18,2); C 11-13 m0 @(20,10,0) |
| KEEP:5 | 18 | Rollo | 13 | 50 | 18 | A 19-06 m0 @(21,23,1); B 06-13/15-19 m1 @(9,7,2); C 13-15 m0 @(9,9,1) |
| KEEP:5 | 19 | Mariah | 27 | 40 | 13 | A 18-09 m0 @(22,11,1); B 09-11/13-18 m0 @(23,10,1); C 11-13 m0 @(22,11,1) |
| KEEP:6 | 10 | Lord Michael | 16 | 50 | 16 | A 21-05 m0 @(3,8,1); B 05-07/19-21 m0 @(25,7,0); C 07-19 m0 @(25,7,1) |
| KEEP:6 | 11 | Cory | 17 | 50 | 17 | A 00-06 m0 @(26,18,0); B 06-17/19-00 m1 @(22,6,0); C 17-19 m0 @(26,18,0) |
| KEEP:6 | 12 | Hardluck | 18 | 58 | 8 | A 19-07 m0 @(26,24,0); B 07-11/13-19 m2 @(15,16,0); C 11-13 m0 @(25,13,0) |
| KEEP:6 | 13 | Barbra | 19 | 50 | 14 | A 21-05 m0 @(26,24,1); B 05-07/19-21 m0 @(15,3,1); C 07-19 m0 @(26,11,1) |
| KEEP:6 | 14 | Tim | 20 | 44 | 24 | A 23-07 m0 @(3,24,1); B 07-09/21-23 m0 @(25,7,0); C 09-21 m2 @(15,23,2) |
| KEEP:6 | 15 | Toshi | 28 | 44 | 13 | A 19-11 m0 @(3,20,0); B 11-13/15-19 m0 @(24,11,1); C 13-15 m0 @(25,9,0) |
| KEEP:6 | 16 | Julia | 32 | 44 | 10 | A 21-07 m0 @(9,27,1); B 07-09/19-21 m0 @(26,11,0); C 09-19 m0 @(23,11,1) |
| KEEP:7 | 9 | Toede | 21 | 50 | 12 | A 00-00 m0 @(17,4,0); B 00-00/00-00 m0 @(17,4,0); C 00-00 m0 @(17,4,0) |
| KEEP:7 | 11 | Lord Malone | 22 | 50 | 14 | A 21-07 m0 @(8,27,1); B 07-09/19-21 m0 @(17,5,1); C 09-19 m0 @(6,6,1) |
| KEEP:7 | 16 | Monsieur Loubet | 23 | 48 | 9 | A 21-07 m0 @(22,22,1); B 07-09/19-21 m0 @(13,5,1); C 09-19 m1 @(21,25,1) |
| KEEP:7 | 17 | Kristi | 24 | 50 | 13 | A 23-05 m0 @(23,21,0); B 05-13/15-23 m1 @(23,7,1); C 13-15 m2 @(15,5,1) |
| KEEP:7 | 18 | Gardner | 25 | 50 | 10 | A 19-05 m0 @(23,18,0); B 05-07/17-19 m0 @(15,16,-1); C 07-17 m0 @(17,7,1) |
| KEEP:7 | 19 | Maxwell | 29 | 48 | 17 | A 21-07 m0 @(20,18,0); B 07-09/19-21 m0 @(13,7,1); C 09-19 m1 @(21,26,1) |

## 4. Generic And Reserved Slots

The roster also contains occupied slots that are not named by a real `.TLK`
entry. They are retained here as counts because they matter for NPC placement,
collision, guards, hostiles, hidden actors, and scenery-like people. They are
not enumerated row-by-row because the task target is the named roster.

| Family | Dialog id 0 | High/special dialog ids | Total generic/reserved |
|---|---:|---:|---:|
| `TOWNE` | 31 | 28 | 59 |
| `DWELLING` | 3 | 0 | 3 |
| `CASTLE` | 42 | 25 | 67 |
| `KEEP` | 50 | 6 | 56 |
| **Total** | **126** | **59** | **185** |

Dialog id 0 is the ordinary no-dialogue value. There is no "dialog id 1"
category: the four slots that carry index `1` are ordinary speaking NPCs and are
listed in Section 3 (Zachariah, Jennifer, Alistair the Bard, and Captain Johne).
Earlier revisions counted them as reserved.

High/special ids in the observed roster are exactly `129` through `136`
(`0x81`..`0x88`) and `255` (`0xFF`). They are not `.TLK` ids, and they are not
"probably guards": `0x81`..`0x88` are the eight Talk-entry **shop triggers**
enumerated in `formats/npc.md` Section 7 and `systems/shops.md` Section 3 —
weaponsmith, tavern/sage, horse trader, shipwright, herbalist, guildmaster,
healer, innkeeper — and `0xFF` is the reserved "not a real NPC" marker that
routes Talk to the Blackthorn regime's guard-demand handler
(`systems/blackthorn.md` Section 7a). The per-family counts match that reading
exactly: the 28 high ids in `TOWNE` are 23 shop triggers plus 5 guard-demand
markers, `CASTLE` has 17 plus 8, `KEEP` has 6 shop triggers and no guard-demand
marker, and `DWELLING`, which hosts neither shops nor regime guards, has none.
Their roster slots are overwhelmingly tag `54` (the merchant sprite) for the
shop triggers and tag `70` (the guard sprite) for the `0xFF` markers.

Two named cases are intentionally special:

- Lord British has **no** roster slot in `CASTLE:0`. **Retraction:** earlier
  revisions of this section said his slot was present with a no-dialogue id and
  the guard-class role tag; that claim is withdrawn. The role tag that names his
  own sprite class occurs nowhere in any of the four `.NPC` files, none of
  `CASTLE:0`'s dialogue ids resolves to a Lord British record (its nine authored
  ids are the residents tabulated above, Alistair the Bard through Chuckles),
  and the twelve no-dialogue slots that prompted the original claim all carry
  the ordinary guard role tag `70`, twelve of them, indistinguishable from one
  another. Whatever presents Lord British in the throne room is not a scheduled
  roster NPC, and an implementation must not synthesise one.
- Lord Blackthorn's castle reuses dialogue id 12 for six guard roster slots.
  Those guards are interchangeable schedule actors sharing one authored
  dialogue record, whose display-name entry is the punctuation string `....`
  rather than a personal name. Gorn is a separate record (id 11) on the single
  slot in the castle's basement.
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

The role column below is no longer inferred from the names on nearby rows. The
tag resolves through the sprite page into the object-description domain of
`LOOK2.DAT`, so each class has a shipped description string, and that string is
what an L-Look at the actor reports. Several earlier labels in this table were
guesses that the corrected dialogue binding contradicts, and they are retracted:
`40` is the wizard class (not "noble/lady"), `44` and `5C` are minstrel classes
(not "lord/scholar" and "uncommon human"), `58` is the jester class, `68` is the
child class (not "bard/jester/performer"), `6C` is the beggar class (not
"nobility/dignitary"), `78` is Blackthorn himself (not a generic court jester),
`90` is the rodent class, `94` is the bat class, and `D8` is the daemon class.

| Tag | Shipped description | Engine-facing role |
|---:|---|---|
| `01` | *(sprite forced)* | Default-person sentinel; the sprite-link helper forces the standard person tile instead of using the tag as a direct sprite class. |
| `0E` | `a sandalwood box` | Not a person at all: the story-object slot at Lord British's Castle that `G` Get consumes (`catalogs/quest-graph.md` Section 7). |
| `10`, `11` | `a horse` | Unmounted horse frames, used for stable and paddock actors and for Smith at Iolo's Hut. |
| `1B` | `an odd rug` | Unmounted magic-carpet object. |
| `1E` | `a corpse` | Static corpse actor. |
| `28` | `a skiff` | Moored-skiff object. |
| `40` | `a wizard` | Mage/scholar sprite; carried by Mariah, Zachariah, and similar. |
| `44` | `a minstrel` | Minstrel sprite. |
| `48` | `a fighter` | Fighter sprite; carried by Dupre, Sentri, Geoffrey, Gorn. |
| `50` | `a villager` | Generic adult townsperson; the most common named-NPC sprite class. |
| `54` | `a merchant` | Shop/service actor, paired with the `0x81`..`0x88` shop-trigger dialogue ids. |
| `58` | `a jester` | Jester sprite; carried by Chuckles. |
| `5C` | `a minstrel` | Second minstrel sprite class. |
| `68` | `a child` | Child sprite. |
| `6C` | `a beggar` | Beggar sprite. |
| `70` | `a guard` | Guard/patrol class; guard-like tags participate in alarm/guard handling and carry the `0xFF` guard-demand dialogue marker. |
| `78` | `the Dark King Blackthorn!` | Blackthorn's own sprite; it appears on exactly one roster slot, in his castle. |
| `90` | `a rodent of unusual size` | Hostile/unusual town actor class. |
| `94` | `a bat` | Animal actor class. |
| `B5` | `the Crown!` | Royal-regalia object slot. |
| `B6` | `the Sceptre!` | Royal-regalia object slot; Stonegate slot 9, cleared once the Sceptre is taken. |
| `B8` | `a gargoyle` | Monster actor class. |
| `D8` | `a daemon` | Daemon actor class; carried by Sin'Vraal and by Stonegate's guardian. |
| `FC` | `a shadow lord` | Shadow Lord actor class (`catalogs/monster-bestiary.md`, class 47). Authored on Stonegate slots 1-3 and also written by the town-entry Shadowlord install. |

The tag byte is a sprite and occupancy class, not the schedule AI byte and not
the dialogue id. A compatible engine should preserve the byte value even when a
human-facing label is generic, because collision, sprite selection, visibility,
guard handling, and special town setup all consume the tag semantically.

## 5. Boundaries And Remaining Work

The following boundaries are explicit and intentional.

1. **Punctuation-only name.** `CASTLE:1` dialogue id 12 — the record its six
   repeated guard slots share — has a first display entry of punctuation rather
   than a conventional personal name. The catalog preserves that authored display
   entry as `....`; this is not a missing-person-name placeholder. An earlier
   revision attached this note to slot 25, which the corrected binding shows is
   Kraw.
2. **Keyword graph.** Keyword counts are included, but keyword names and
   response text are deliberately omitted. That belongs in a quest-graph pass
   and must be summarized without dumping dialogue strings.
3. **Anonymous hidden actors.** Some hidden-mask entries in
   `systems/npc-schedules.md` point at occupied slots that do not have a
   personal name in the public roster. Those slots should be identified by the
   shipped sprite descriptions in Section 4 — merchant, guard, bat, rodent, and
   so on. An earlier revision offered "Avatar/free-slot sentinel" as one of
   those labels; there is no such class, and the spec gives the player no
   NPC-slot representation.

## 6. Sources

This catalog is cleanroom prose derived from the local analysis notes and the
existing public specs. It does not reproduce disassembly, decompiled code, data
offsets, raw dialogue text, or private note prose.

Private analysis sources used:

- `u5-decomp/formats/npc-tlk-pth.md` - `.NPC` block structure, `.TLK`
  header structure, name-entry decoding rules, AI-byte
  enumeration, type-byte sprite-class interpretation, and file counts. That
  note's leading-pair reading of the `.TLK` header is superseded by the
  corrected contract in `formats/tlk.md` Section 6; the bindings in Section 3
  above were re-derived against the corrected reading.
- `u5-decomp/formats/maps.md` - scene-byte to storage-family/sub-map mapping
  and the Lord British / Blackthorn / Gorn roster peculiarities.
- `u5-spec/catalogs/gazetteer.md` - public scene-name bindings for the roster
  keys, including blank resident-name boundaries.
- `u5-decomp/functions/NPC_OVL/` - class-family roster load,
  schedule/type/dialogue array loading, and slot-zero convention.
- `u5-decomp/functions/NPC_OVL/` - the
  three-waypoint/four-boundary schedule selection rule.
- `u5-decomp/functions/NPC_OVL/` - schedule
  consumer, type-byte occupancy use, and per-tick movement model.
- `u5-decomp/functions/TOWN_OVL/`, and
  `u5-decomp/functions/TOWN_OVL/` - town activation,
  guard/alarm, and death-mask type filters.
- `u5-decomp/functions/TALK_OVL/` - dialogue id lookup
  against the `.TLK` header and blob load. The corrected `(id, offset)` header
  binding of Sections 1 and 3 was re-derived from this walk together with a
  direct re-scan of the shipped `.TLK` and `.NPC` files; the earlier
  `(offset, id)` reading in `u5-decomp/formats/npc-tlk-pth.md` is superseded.
- Sprite-class role names in Section 4 are read from the object-description
  domain of the shipped `LOOK2.DAT` (see `u5-spec/formats/look2-dat.md`) rather
  than inferred from neighbouring roster names.
- `u5-decomp/functions/TALK_OVL/` - text-byte
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
