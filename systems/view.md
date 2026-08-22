# Look And View

## 1. Scope

Ultima V has two inspection command families:

- `L` Look describes a target tile, object, sign, shrine, clock, fountain,
  dungeon cell, or other visible feature.
- `V` View consumes a vision gem outside combat and paints a temporary map or
  minimap overlay.

The resident command dispatcher owns the letter routing and the gem inventory
gate. LOOKOBJ owns overworld and town look/view rendering. DNGLOOK owns dungeon
look/view rendering. Combat recognizes `L` and `V` only as aborting labels; it
does not enter these non-combat renderers and does not consume a gem.

## 2. Command Routing

`L` and `V` are mode-aware.

| Mode | `L` Look | `V` View |
|---|---|---|
| Overworld and town-family scenes | Prompt for direction, then enter LOOKOBJ. | Require at least one gem, decrement one gem, then enter LOOKOBJ's local view path. |
| Dungeon scenes | Enter DNGLOOK's dungeon look path. | Require at least one gem, decrement one gem, then enter DNGLOOK's dungeon minimap path. |
| Combat | Print/acknowledge the command label and abort. | Print/acknowledge the command label and abort without spending a gem. |

The gem check happens before the view overlay is called. If the party has no
gems, the command prints the no-gem refusal and returns before LOOKOBJ or
DNGLOOK can render anything.

## 3. Overworld And Town Look

LOOKOBJ's look entry runs after the dispatcher has collected a direction. The
entry:

1. Runs a preflight visibility/reach gate. A failed gate exits quietly.
2. Computes the target coordinate from the party position plus the chosen
   direction step.
3. Reads the live map tile id at that coordinate through the shared
   live-map tile query.
4. Checks whether a per-map object entry also matches the target coordinate and
   active floor.
5. Dispatches to a special vision, object, sign/poster, or terrain
   description path, in that order of precedence.

### Top-down Look special cases

Every special case below is selected by the **live map tile id** at the
resolved target cell, or by a per-map object entry matching that cell. There is
no scene or floor gate on the dispatcher itself: the same predicates apply on
the overworld and in every town-family scene, and the two special cases that do
have a location condition carry it inside their own handler, not in the
dispatch. Dungeon Look is a different command path (Section 5) and shares none
of these predicates.

The tile id tested comes from the shared live-map tile query, the same one
movement and Talk use, and it is a single terrain-layer byte. It is therefore
always an id in the terrain-description domain of `LOOK2.DAT`, never an
active-object or creature descriptor. This matters for one band in particular.
Live tile band `0xD8..0xDB` is the fountain trigger below, while the identically
numbered entries in the **object-description domain** are the Daemon frame run
named in `catalogs/monster-bestiary.md` and `systems/active-objects.md`. Same
four numbers, two different lookup domains, no relationship between them; a
Daemon standing in front of the party does not make Look offer a drink.

**Entry dispatch, in the order the command tests it.** The order is
load-bearing: the vision case is decided before anything is printed, and the
per-map object case wins over the sign case when both would match.

| Order | Predicate | Result |
|---:|---|---|
| 1 | Preflight visibility/reach gate refuses | Abort silently. No prompt output, no description, no state change. |
| 2 | Live tile `0x29` (the crystal-sphere tile) | Death-vision case. Prompts for a party member; cancelling returns with nothing printed. Otherwise rolls `1..30` against that member's Intelligence as described below. Nothing else in this table is consulted. |
| 3 | *(the shared "thou dost see" preamble is printed here)* | Applies to rows 4, 5 and 6 alike. |
| 4 | A per-map object entry matches the target coordinate and active floor | Object description from the upper `LOOK2.DAT` object-description domain. |
| 5 | Live tile `0x89`, `0x8A`, `0xA0`, `0xA4` or `0xF8` | Sign/poster path: emit a line break, then render the sign or poster (including the fixed Yew wanted-poster exception described below). |
| 6 | Otherwise | Terrain description path, dispatched again by the table that follows. |

**Terrain description path, in the order it tests.**

| Order | Predicate | Result |
|---:|---|---|
| 1 | Live tile `0xE0`, `0xE1` or `0xE2` | Redirect: move the target cell one step and re-read it, then start this table over. `0xE0` moves one cell north, `0xE1` one cell east, `0xE2` one cell west. The redirect can chain, so a run of redirect tiles resolves to one final cell. |
| 2 | Live tile `0x59`, a **telescope** | Enter the sky renderer of Section 4.2 instead of printing any description text. Looking at a telescope shows the sky, not a map, and needs no gem or item. |
| 3 | Live tile `0xA1`, a **wishing well** | Wishing-well handler: drop a coin, make a wish. A different tile from the telescope, with its own handler and its own description. |
| 4 | Live tile `0xD8`, `0xD9`, `0xDA` or `0xDB` | Fountain handler. |
| 5 | Any other tile | Print that tile's base `LOOK2.DAT` description, then apply at most one appender from the rows below. |
| 5a | Live tile `0xFA` or `0xFB` | Append the current clock time: hour reduced to a twelve-hour value (zero displayed as twelve), a colon, two-digit minutes, then an `AM` suffix for hours zero through eleven and a `PM` suffix otherwise. |
| 5b | Live tile `0xDE` | Append a virtue word chosen by the current scene: scene `30` appends Truth, scene `31` appends Love, scene `32` appends Courage. In any other scene the base description is printed with no appended word. |
| 5c | Live tile `0xDF` | Append a dungeon name chosen by the target cell's map X coordinate: `58` Shame, `72` Destard, `91` Despise, `126` Wrong, `128` Doom, `156` Covetous, `239` Hythloth, `240` Deceit. Any other X appends nothing. |

Rows 2, 3 and 4 cover six tile ids in total (`0x59`, `0xA1`, `0xD8`, `0xD9`,
`0xDA` and `0xDB`) and all six replace the base description entirely: the
handler runs and returns before any description string is emitted. Whether the
tile also owns a description record is a separate question and is **not** a
usable test for which tiles are handler triggers. `0x59` and the four fountain
ids carry only the shared placeholder record, as do the five sign/poster ids of
entry-dispatch row 5; but `0xA1` carries a real description record of its own
naming a deep well, which the Look path simply never reaches. Implementations
should key these branches on the tile ids listed here, never on "the record is
a placeholder".

The telescope's missing description is therefore not an unreconciled gap: the
description table deliberately holds the placeholder for it, because the special
handler produces the output instead of a base string. Rows 2 and 3 are also two
genuinely different fixtures, tested one after the other and routed to different
handlers - an earlier revision of this document glossed the telescope tile as a
wishing well, and that label is withdrawn. Only three telescopes are placed in
shipped data, all indoors: in Moonglow, in Skara Brae, and in West Britanny,
each standing near a ladder inside the same building.

The shared line-spacing cleanup belongs to the plain-description path only. A
tile that took none of the appender rows above -- that is, a tile that is not
`0xFA`, `0xFB`, `0xDE` or `0xDF` -- finishes by running the same line-spacing
cleanup the per-map object branch uses, which may emit one further newline;
that affects spacing only and never changes the described text. A tile that
matched an appender row returns as soon as its suffix is printed and never
reaches the cleanup. This holds even when the matched row appends nothing:
`0xDE` in a scene other than `30`, `31` or `32`, and `0xDF` at an X coordinate
outside the list above, print the base description alone and still skip the
cleanup. So a clock tile emits its description and time and nothing further.

The wishing well's granting condition and the fixed wanted poster's coordinate
are handler-internal, not dispatch predicates: the well runs its coin and wish
prompts in every scene and only checks the scene when deciding whether to grant,
and the sign path checks the fixed poster coordinate only after it has already
been selected by the tile test in row 5 of the entry table.

### Description lookup and special-case outcomes

The ordinary terrain description uses `LOOK2.DAT`: the raw tile id selects a
description record. The format of that table is specified in
`formats/look2-dat.md`. LOOK2 has two public lookup domains: terrain tile ids
use the lower terrain-description half, while active-object and per-map object
classes use the upper object-description half. Several tile ids can share one
description record.

Special LOOKOBJ look cases include:

- **Per-map object entry.** Prints the object-description form from the upper
  LOOK2.DAT object-description range. The object branch always runs the shared
  line-spacing cleanup, which the terrain path runs only on its
  plain-description rows (Section 3).
- **Signs and wanted posters** (live tile `0x89`, `0x8A`, `0xA0`, `0xA4`, `0xF8`). Prints a line break, then renders
  the sign or poster text through the sign/poster helper. One fixed exception
  in Yew, floor `0`, at local coordinate `(x=17, y=21)` renders the
  resident wanted-poster presentation; that poster is not read from
  `SIGNS.DAT`. Other sign/poster tiles load a scene-indexed `SIGNS.DAT`
  record by current scene and target coordinate. If no record matches, the
  sign path prints the blank-sign fallback.

  The fixed wanted poster is a nine-row framed sign stream. It prints the
  heading `Wanted:`, one blank spacer row, three centered name rows, another
  blank spacer row, and the footer `Dead or Alive`. The name rows are filled
  from party slots `0`, `1`, and `2` in that order, but only while the slot
  index is lower than the current party count. A one- or two-member party
  leaves the remaining name rows blank. Slots `3+` are not listed, and status
  does not filter a listed slot. Each printed name starts at column
  `7 - floor(name_length / 2)` within the poster row, then the right border is
  emitted at column `14`.
- **Clock tiles** (live tile `0xFA`, `0xFB`). Prints the tile description and appends the current game
  time using the normal twelve-hour AM/PM presentation.
- **Shrine and dungeon-entrance tiles** (live tile `0xDE` and `0xDF`). Prints the generic tile description
  and appends the virtue or dungeon name selected as tabulated above.
- **Fountains** (live tile `0xD8..0xDB`). Prompt for the drinking party member; cancelling prints the
  no-one result. Dead or asleep members refuse as incapacitated. Any other
  selected member receives the refresh message. The overworld/town fountain
  result is presentation-only: this LOOKOBJ path does not restore HP, cure
  status, wake sleepers, or otherwise write party state. Dungeon fountains are
  the state-changing fountain family and are specified in `dungeon-mode.md`.
- **Wishing wells** (live tile `0xA1`). Prompt for a coin and a wish, then run the well-specific
  object-spawn branch when the wish matches one of the accepted names in an
  accepted scene. The accepted wish keywords are Corvette, Ferrari,
  Lamborghini, Lotus, Porsche, and Horse. A coin is consumed only after the
  player accepts the coin prompt and before wish matching; coinless, empty,
  mismatched, and ungated paths spawn nothing. The only granting scenes are
  Paws (`22`) and Empath Abbey (`31`). All accepted words map to the same
  created object: a horse-family active-object record with type/frame `0x10`,
  placed one cell east of the well caller's X coordinate at the caller's Y and
  floor, with the first auxiliary field cleared. There is no per-word vehicle
  mapping.
- **Death-vision tile** (live tile `0x29`, the crystal-sphere tile). Prompts for a party member and rolls `1..30` against
  that member's Intelligence. If Intelligence is greater than the roll, the
  command reports a strange vision and paints the local thirty-two-by-thirty-
  two view overlay. If the roll is greater than or equal to Intelligence, it
  reports the death-vision line and prints the selected member number; it does
  not paint the overlay or change party state.

Looking at an NPC or transient active object can resolve through the active
object table to the terrain underneath. Creature-specific conversation and
interaction text belongs to Talk, not Look.

`SIGNS.DAT` sign bodies are small interpreted records, not plain NUL-terminated
paragraphs. Their public bytecode is deliberately limited:

| Record token | Meaning |
|---|---|
| End marker | Ends the record. |
| Header-skip marker | Skipped before body rendering. |
| Pause marker | Waits for a keypress, then resumes rendering. |
| Two literal placeholders | Emit the same literal placeholder character used by shipped signs. |
| Macro range | Substitutes one of the sign macro strings from the LOOKOBJ macro pool. |
| Other bytes | Print the low seven bits as a display character. |

The high bit of ordinary sign text is not text content; the renderer masks it
off for output while preserving the path's mode toggle side effect.

## 4. Overworld And Town View

Outside dungeons, `V` View enters LOOKOBJ after the resident dispatcher has
spent one gem. The main view renderer paints a temporary thirty-two-by-thirty-
two local-area overlay using the current active-object/terrain lookup for each
cell. Each cell is reduced to a view class and drawn by a per-class renderer.

The local view overlay is modal:

- It saves or covers the existing view area before drawing.
- It renders into a scratch/display overlay rather than mutating map data.
- It waits for a keypress.
- It restores the prior view region before returning.

LOOKOBJ also contains a second, completely separate renderer, described in
Section 4.2. Earlier revisions of this document called it "the full Britannia
chunk-map renderer" and said it paints an eight-row by twenty-two-column
shorthand map of Britannia chunks with the party's chunk marked. **That
description is withdrawn in full.** It is a sky renderer: it draws a starfield
and eight moving celestial bodies whose positions are driven by the calendar
date, and its overlay marker tracks the Shadowlords, not the party.

The path that enters it from ordinary Look is keyed by tile id `0x59`, and that
tile is a **telescope** - a light tube on a splayed tripod. The in-world reading
is simply that *looking at a telescope shows the sky*. Three things follow, and
all three correct earlier wording:

- It is **not** a wishing well. The wishing well is the separate tile `0xA1`,
  with its own coin-and-wish handler and its own printed description.
- It draws **no map of any kind**, and it is not "the same view the gem
  provides". The gem's `V` View command is an unrelated path with its own
  dispatch and its own renderer, described in the rest of this section.
- It has **no gem or item precondition**. The gem spend described above belongs
  to `V` View alone; a telescope answers Look whatever the party is carrying.

The local 32-by-32 overlay renders at a four-pixel cell scale inside the
message-panel region. A cell anchor is:

```text
anchor_x = 32 + column * 4
anchor_y = 32 + row * 4
```

Each sampled cell is mapped through a private visual class and then through one
of the class renderers below. The tile-id ranges are the tile catalog ids after
active-object/terrain lookup has selected the cell to draw. Coordinates in the
renderer table are relative to the cell anchor and use `(x,y)` order.

| View class | Source family | Clean pixel/stroke contract |
|---:|---|---|
| `0` | none | No-op; leaves the cell unornamented. |
| `1` | secondary terrain bank | Four 8-by-8 micro-blits rooted at `(1,0)`, `(1,2)`, `(3,1)`, `(3,3)`, forming the sparse checker/corner pattern. |
| `2` | secondary terrain bank | Filled rectangle from `(0,0)` through `(3,3)`. |
| `3` | frame-fill bank | Filled rectangle from `(0,0)` through `(3,3)`. This uses the frame-fill source family rather than the class-2 terrain source. |
| `4` | frame-line bank | Horizontal line `(0,0)..(3,0)` and horizontal line `(0,3)..(3,3)`. |
| `5` | frame-line bank | Horizontal line `(1,1)..(2,1)` and horizontal line `(1,2)..(2,2)`, forming a centered two-by-two marker. |
| `6` | frame-line bank | Hollow rectangle: top `(0,0)..(3,0)`, bottom `(0,3)..(3,3)`, left `(0,1)..(0,2)`, right `(3,1)..(3,2)`. |
| `7` | frame-line bank | Direct frame-chain variant. It selects the same frame-line source family used by class `0x5A`, then draws the ordinary filled cell frame. |
| `8` | dedicated rough-terrain bank | Upper-left two-by-two block plus lower-right two-by-two block: `(0,0)..(1,0)`, `(0,1)..(1,1)`, `(2,2)..(3,2)`, `(2,3)..(3,3)`. |
| `9` | secondary terrain bank | Hybrid pattern: horizontal line `(0,0)..(3,0)`, horizontal line `(0,2)..(3,2)`, plus two lower-half micro-blits rooted at `(1,2)` and `(0,3)`. |
| `0xA` | modal terrain banks | Four-corner/ring renderer rooted at `(1,0)`, `(3,1)`, `(1,2)`, `(3,3)`. Source selection is per corner and may switch among normal, secondary, and peer/blue families according to the view-mode flag and the cell's low-nibble class. |
| `0xB` | modal terrain banks | Two diagonal micro-blits rooted at `(0,0)` and `(2,2)`. Normal and peer/gem-view modes select different source families. |
| `0xC` | none | Table-mapped no-op/default class for tile id `0x01`; it falls through without a dedicated renderer. |
| `0xD` | fixed plus modal terrain banks | Four micro-blits. The top pair `(1,0)` and `(3,1)` always use the fixed secondary terrain source; the bottom pair `(0,2)` and `(2,3)` use the modal normal/peer source. |
| `0xE` | frame-line bank | Vertical line `(1,0)..(1,3)` and vertical line `(2,0)..(2,3)`. |
| `0xF` | normal terrain bank | Direct peer/gem-view variant using the normal terrain source with the ordinary cell-frame chain. |
| `0x10` | frame-fill and frame-line banks | Fence/wall renderer. It first paints a center fill `(1,1)..(2,2)`. Edge bits then add top `(1,0)..(2,0)`, right `(3,1)..(3,2)`, bottom `(1,3)..(2,3)`, and left `(0,1)..(0,2)`. Tile ids `0x22..0x25` add one interior orientation marker at `(1,2)`, `(1,1)`, `(2,1)`, or `(2,2)` respectively. |
| `0x5A` | frame-line bank | Compatibility/direct-call class. It uses the same source family and filled-cell frame chain as class `7`; no shipped tile-id table entry maps here. |

The resident view-class table maps tile ids to these classes as compact ranges:

| View class | Tile ids |
|---:|---|
| `0` | `0x00`, `0xC0..0xC3`, `0xCC..0xCF`, `0xFF` |
| `1` | `0x05`, `0x30..0x37` |
| `2` | `0x09..0x0A`, `0x2D` |
| `3` | `0x07`, `0x1C`, `0x1E..0x1F`, `0x40`, `0x44`, `0x48..0x49`, `0x6A..0x6B`, `0x70..0x7F`, `0x87`, `0x8C`, `0x8F`, `0xAA`, `0xBC`, `0xDD` |
| `4` | `0x1D`, `0x38`, `0x47`, `0x5A`, `0x5C..0x5D`, `0x94..0x96`, `0x9A..0x9C`, `0xAB..0xAC`, `0xBE` |
| `5` | `0x10..0x1B`, `0x29..0x2B`, `0x2E..0x2F`, `0x41..0x43`, `0x4C`, `0x58..0x59`, `0x5B`, `0x5E..0x5F`, `0x80..0x85`, `0x88..0x8B`, `0x8D..0x8E`, `0x90..0x93`, `0x9D..0xA9`, `0xAD..0xB7`, `0xBD`, `0xBF`, `0xC8..0xCB`, `0xDE..0xDF`, `0xE8..0xEB`, `0xFA..0xFD` |
| `6` | `0x0D`, `0x45`, `0x4A..0x4B`, `0x86`, `0x97..0x99`, `0xB8..0xBB`, `0xC4..0xC7`, `0xEC..0xF9` |
| `7` | `0x0C`, `0x27..0x28`, `0x39..0x3F`, `0x46`, `0x4D..0x57`, `0xD0..0xD3`, `0xFE` |
| `8` | `0x0B`, `0x0E..0x0F` |
| `9` | `0x06`, `0x08`, `0x2C` |
| `0xA` | `0x03`, `0x60..0x69`, `0x6C..0x6F`, `0xE4..0xE7` |
| `0xB` | `0x02`, `0xD4..0xD7` |
| `0xC` | `0x01` |
| `0xD` | `0x04` |
| `0xE` | `0xE0..0xE3` |
| `0xF` | `0xD8..0xDC` |
| `0x10` | `0x20..0x26` |

Classes that switch banks under peer/gem-view mode affect presentation only.
They do not change terrain, active objects, or visibility state.

The source-family names above are public renderer roles, not raw asset
addresses. The renderer uses these families consistently:

| Source family | Used by |
|---|---|
| Frame fill | Class `3` and the center fill in class `0x10`. |
| Frame line / structure outline | Classes `4`, `5`, `6`, `7`, `0xE`, and compatibility class `0x5A`. |
| Normal terrain | Class `0xF` and the normal-mode branches of `0xA`, `0xB`, and `0xD`. |
| Secondary terrain | Classes `1`, `2`, `9`, the fixed top layer of class `0xD`, and one class-`0xA` branch. |
| Peer/blue terrain | Peer/gem-view branches of classes `0xA`, `0xB`, and `0xD`. |
| Dedicated rough terrain | Class `8` only. |

### 4.2 The Sky Renderer

The second LOOKOBJ renderer is a separate overlay from the local
thirty-two-by-thirty-two view. It has two mutually exclusive presentation
paths, selected by the current hour.

Retractions, because earlier revisions of this document published the wrong
model and engine work may have been built on it:

- It does **not** draw an eight-by-twenty-two grid of chunk cells. It draws
  **eight** cells in total, one per row.
- Its cell positions are **not** derived from the party's chunk position. The
  party's position is never read. The inputs are the saved year, month, and day.
- The overlay marker is **not** a party marker. It is drawn only for rows that
  a Shadowlord currently occupies.
- The marker strips published previously had `x` and `y` transposed and put the
  clip gates on the wrong axis. The corrected geometry is below.
- There is no chunk-map "edge wrapping"; the wrap is a column cursor wrapping
  around a twenty-two-slot ring.

#### 4.2.1 Daylight path

When the hour is in `6..17` inclusive, the renderer:

1. Prints `the sun!` followed by a newline.
2. Ensures an active party member is selected. If there is none, it scans the
   roster in slot order for the first member whose status is healthy or
   poisoned and makes that member active.
3. Applies **one point of damage** to the active member, with the ordinary
   damage presentation and death handling that damage normally carries.
4. Redraws the stats panel and returns.

Nothing is painted on this path. An implementation that draws a picture during
the day does not match the original, and one that omits the damage will drift
from the original's party state.

#### 4.2.2 Night path

At every other hour the renderer paints into the main viewport region and then
waits for input:

1. Set the visibility-dirty flag so the ordinary world view is repainted after
   the overlay closes.
2. Fill the eleven-by-eleven viewport visibility grid with the hidden marker.
3. Run the overlay capture/setup step that the modal view paths share.
4. Select the starfield colour, then plot **eighty** single points at
   pseudo-random coordinates: `x` uniform in `9..182` inclusive and `y` uniform
   in `9..172` inclusive, drawn from the shared engine random-number generator
   in that order (`x` first, then `y`, one draw each per point). The generator,
   its state, and its sequence are specified in `systems/prng.md`; the
   starfield consumes exactly one hundred and sixty draws.
5. Draw the eight rows (Section 4.2.3).
6. Print `the night sky! ` — note the trailing space and the absence of a
   newline — then busy-wait until any key is available.

The renderer leaves world state unchanged apart from the visibility-dirty flag
and the active-member selection on the daylight path.

#### 4.2.3 The eight rows and the column rule

There are eight rows. Row `k` has a fixed pixel `y` origin and a fixed
twenty-two-slot ring of columns, of which only some slots are permitted. Column
`c` has pixel `x` origin `c * 8`.

| Row | `y` origin | Start column | Permitted columns | Slots |
|---:|---:|---:|---|---:|
| `0` | 144 | 18 | 4, 11, 18 | 3 |
| `1` | 136 | 2 | 2, 7, 11, 15, 20 | 5 |
| `2` | 120 | 8 | 2, 5, 8, 11, 14, 17, 20 | 7 |
| `3` | 104 | 15 | 1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21 | 11 |
| `4` | 88 | 11 | 0, 2, 4, 6, 8, 9, 11, 13, 14, 16, 18, 19, 21 | 13 |
| `5` | 64 | 6 | 1, 2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16, 17, 19, 20, 21 | 17 |
| `6` | 40 | 4 | 1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21 | 19 |
| `7` | 8 | 2 | 0 through 21 (all) | 22 |

Every start column is itself a permitted column of its row.

The column actually used is found by counting days:

```text
elapsed = number of days from the campaign epoch to the current saved date
column  = start_column[k] stepped backwards through the permitted columns of
          row k, `elapsed` times, wrapping from column 0 round to column 21
```

The campaign epoch is the game's start date: the year whose last two decimal
digits are `39`, month `4`, day `5`. The comparison that drives the count uses
the year modulo one hundred, so a campaign that runs past year `199` would wrap;
no shipped campaign reaches that. The walk decrements the date one day at a
time on the same twenty-eight-day-month, thirteen-month calendar the turn clock
maintains (`systems/time.md`), so `elapsed` is
`(years * 364) + (months * 28) + days` measured from the epoch.

Because each row has a different number of permitted slots, the eight rows
return to their start columns on different periods: 3, 5, 7, 11, 13, 17, 19 and
22 days respectively.

#### 4.2.4 Per-row body glyph

Each row draws exactly one body, at column `c + 1` where `c` is the column
computed above. Let `X = (c + 1) * 8` and `Y = row_y_origin`. The body is
eleven single points in the body colour:

| Point | Clip gate |
|---|---|
| `(X + 6, Y + 8)` | none |
| `(X + 7 + i, Y + 7 + j)` for `i` and `j` each in `0..2` | each point is skipped when `X + i > 176` |
| `(X + 10, Y + 8)` | skipped when `X > 173` |

That is a three-by-three square with one extra pixel on the left and one on the
right at mid-height — a small round disc.

#### 4.2.5 The Shadowlord marker

For each of the three Shadowlords, if that Shadowlord's current location value
equals `row + 1`, a marker is drawn on that row. The location values are the
scene ids `1..8` used by the Shadowlord tracking described in
`catalogs/quest-graph.md`; a vanquished Shadowlord holds the vanquished
sentinel and never matches. Two or three Shadowlords in the same scene draw the
marker two or three times on the same row, which is idempotent.

The marker is drawn at column `c` — one column left of its body — so it trails
the body. Let `X = c * 8` and `Y = row_y_origin`. It is eight **vertical**
runs in the marker colour, inclusive at both ends:

| Run | Clip gate |
|---|---|
| `x = X + 5`, `y = Y + 10 .. Y + 12` | `X > 2` |
| `x = X + 6`, `y = Y + 10 .. Y + 12` | `X > 2` |
| `x = X + 7`, `y = Y + 8 .. Y + 12` | `X > 2` |
| `x = X + 8`, `y = Y + 8 .. Y + 12` | `X <= 175` |
| `x = X + 9`, `y = Y + 6 .. Y + 10` | `X <= 174` |
| `x = X + 10`, `y = Y + 6 .. Y + 10` | `X <= 173` |
| `x = X + 11`, `y = Y + 5 .. Y + 8` | `X <= 172` |
| `x = X + 12`, `y = Y + 5 .. Y + 7` | `X <= 171` |

The runs step up and to the right, so the shape reads as a short diagonal
streak leaning away from the body. With column values in `0..21` the upper
gates never fire; the `X > 2` gate suppresses the first three runs when the
marker lands in column `0`.

The marker composites over whatever is already in those pixels; it is not a
replacement cell, and the body is drawn first.

#### 4.2.6 Colours

Three distinct colour slots are used, all taken from the boot-time
user-interface colour table (`display-driver.md` section 2) rather than being
literals in the renderer: the starfield uses the chrome slot biased into the
bright half of the palette, the bodies use the accent slot, and the Shadowlord
markers use slot 0. A clean implementation should expose them as three
configurable indices rather than hard-coding EGA numbers, because the shipped
values are per-display-mode.

#### 4.2.7 What is still open

Static analysis fixes the geometry, the cadence, and the selection rule, but not
the visual identity of the eight rows. Their return periods are 3, 5, 7, 11, 13,
17, 19 and 22 days (Section 4.2.3), and they key to scene ids `1..8`, the eight
towns, through the Shadowlord comparison. Whether they read on screen as
constellations, planets, moons, or something else is a question for a screenshot
comparison, not for this contract.

One earlier "open question" here is retracted rather than answered: this
renderer was once said to begin with a gem-count band check that might or might
not apply on the telescope route. There is no gem-count read in it at all - the
band is the hour band of Section 4.2.1 - so the question was based on a
misreading and does not need resolving.

## 5. Dungeon Look

DNGLOOK's `L` path describes the dungeon cell in front of the party. It:

1. Prompts for the party member performing the look.
2. Refuses with darkness if neither torchlight nor light spell is active.
3. Computes the forward dungeon cell from current level, X/Y, and facing.
4. Reads the packed dungeon cell byte from the loaded dungeon record.
5. Normalizes the known fall-trap byte that is described as ordinary passage.
6. Dispatches by dungeon high-nibble class and selected low-nibble variants.

The public dungeon cell classes are specified in `formats/dungeon-dat.md` and
`systems/dungeon-mode.md`. Look descriptions include passage, ladders, wooden
chests, fountains, fields, special wall/corpse flavour, and other dungeon cell
families. Fountain and field subtypes use their cell variant to choose the
description.

Dungeon Look is descriptive. It does not consume a gem, mutate the dungeon
record, reveal secret doors, or enter combat.

## 6. Dungeon View

In a dungeon, `V` View spends one gem in the resident dispatcher and then enters
DNGLOOK's map renderer. The renderer:

- clears the viewport used by the first-person dungeon view, covering the
  rectangle from `(8,8)` through `(183,183)`;
- initialises a temporary visited grid and a frontier queue;
- seeds the queue at the party's own cell, pre-marked as visited;
- flood-walks up to eight neighbours per visited cell in this order:
  northwest, north, northeast, west, east, southwest, south, southeast;
- converts each accepted scratch coordinate back to the current dungeon level's
  wrapped eight-by-eight cell coordinates;
- paints each accepted cell by dungeon class;
- stops expansion only on the three dungeon wall presentation classes;
- waits for a keypress or poll result;
- clears the same rectangle and returns through the dungeon composite redraw,
  which repaints the first-person view and rewrites both border labels.

### 6.1 Cell size, origin and extent

The map is a **twenty-two by twenty-two grid of eight-by-eight-pixel cells**.
Grid cell `(0,0)` begins at the top-left corner of the clear rectangle, and a
cell's pixel origin is `x = 8 * grid_x + 8`, `y = 8 * grid_y + 8`. Twenty-two
cells of eight pixels exactly fill `(8,8)` to `(183,183)`, so the grid and the
clear rectangle are the same area, and that area is the same viewport interior
the first-person view uses.

The party occupies the centre cell `(11,11)`, whose pixels are `(96,96)` to
`(103,103)`.

**Correction.** An earlier revision of this section and of
`systems/dungeon-mode.md` implied a twelve-row cell whose lower four rows were
left untouched. The cell is eight rows tall and all eight rows are drawn. That
reading is withdrawn.

**Correction.** An earlier revision described fountain cells as painting a
"two-by-three multi-cell icon rooted at the mapped cell". The fountain is a
**single-cell vector drawing** inside one eight-by-eight cell, and so is the
energy field. Their exact geometry is in `systems/dungeon-mode.md` section 12.5.

The dungeon coordinate of a grid cell is the party's coordinate plus the cell's
offset from the centre, **taken modulo eight in both axes**, so the level tiles
about two and three-quarter times across the window. The player is looking at a
wrapped view of the floor, not a single copy of it.

### 6.2 The glyph source

The map does **not** use the corridor billboard art or the dungeon object
sprites. It uses the engine's two fixed **eight-by-eight one-bit fonts** - the
text font and the runic font - each one hundred twenty-eight glyphs of eight
bytes, one byte per row, most significant bit leftmost. Every published glyph
identifier in the class-to-glyph table is an index into whichever of the two
fonts that class selects, and each cell is drawn opaquely in a
foreground/background pair.

Most classes select the runic font. Four deliberately select the text font: the
three directional-arrow classes and the solid-block bedrock class, whose runic
slot is blank. Two classes are drawn as vectors instead of glyphs.

The class-to-glyph, font-selection and flood-return table lives in
`systems/dungeon-mode.md` section 12.4; in short, `0xB?`, `0xC?`, and `0xD?`
wall presentation classes stop expansion, while heavy-door and room-trigger
classes still paint a door glyph and allow the flood to continue.

### 6.3 The flood bound and the visited grid

The frontier queue is a fixed ring of two hundred fifty-six entries with no
occupancy check. Shipped data never approaches that bound, but a compatible
implementation should treat it as a contract requirement rather than swap in an
unbounded queue, which would paint a differently shaped map on hand-authored
data. Diagonal steps are permitted with no corner-cutting test.

The visited grid is separate scratch state, not a flag inside the loaded dungeon
cells. It starts filled as unvisited, marks cells during the one flood walk, and
is discarded when the viewport is restored. Dungeon cell bit `0x08` remains
class-specific variant/overlay data owned by dungeon-mode systems; View must not
treat it as seen/unseen map memory.

**Withdrawal.** Earlier revisions of this section described a magic peer-view
tint branch inside the dungeon map renderer, and an alternate tinted tile source
for some wall classes. Both are withdrawn: the value being read is the display
adapter identifier, not a peer-spell flag. The dungeon map renderer has no
peer-spell branch. The peer spell's own presentation is specified in `magic.md`.

The map is a temporary overlay. It is not a persistent automap, does not write
exploration bits, and is recomputed from the current dungeon record every time
the player spends a gem. Map floodability is not the same as movement
passability.

Source provenance: derived from private analysis note
`../u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.

## 7. Data Ownership

- `LOOK2.DAT` owns surface/town tile and object description strings.
- `SIGNS.DAT` owns sign and poster text records.
- LOOKOBJ-private view tables own the surface/town view class selection above
  and the per-class glyph choices.
- DNGLOOK owns dungeon high-nibble look descriptions and the dungeon minimap
  flood painter.
- The resident inventory state owns gem count and enforces spending before
  non-combat `V` View renderers run.

## 8. View Boundaries And Remaining Parity Work

The Look/View command contract is complete at gameplay depth: dispatcher
routing, gem consumption, surface/town description flow, sign and poster
handling, fountain and wishing-well special cases, sky and local view
overlays, dungeon look descriptions, and dungeon minimap flood behavior are
fixed. Remaining work is visual cataloging and pixel-level parity, not command
state or persistence behavior.

- **Exact visual QA.** The clean per-class pixel/stroke placement, source
  family selection, dungeon flood order, and overlay clear/restore rectangles
  are specified above. Remaining visual parity work is empirical screenshot QA
  against DOS output and catalog naming for source-family palettes, not unknown
  gameplay or renderer control flow.
- **Dungeon map geometry.** *Closed.* Cell size, cell origin, grid extent, the
  wrap rule, the flood bound and the two-font glyph source are published in
  Section 6.1 through 6.3 and in `systems/dungeon-mode.md` section 12. The
  twelve-row cell, the multi-cell fountain icon and the peer-view tint branch
  are all withdrawn there.
- **Tile special cases.** *Closed.* The full trigger set for top-down Look is
  published in Section 3, including the dispatch order and the redirect tiles.
  Tile id `0x59` is a **telescope**, and it is the trigger for the sky renderer
  of Section 4.2; the older "Britannia chunk-map renderer" reading of that path
  and the older "wishing well" label for that tile are both withdrawn in full,
  as Sections 3 and 4 record. Whether a trigger tile also owns a `LOOK2.DAT`
  description record is a separate question and is not a test for handler
  ownership: `0x59`, the fountain ids and the sign ids carry only the shared
  placeholder record, while the wishing-well tile `0xA1` carries a real record
  of its own naming a deep well that the Look path never reaches.

## 9. Sources

This cleanroom spec was derived from private analysis notes. It intentionally
does not reproduce decompiled code, assembly, raw tables, string dumps, or
private address maps.

- `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/_OVERVIEW.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x099C_lookobj_master.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0000_lookobj_print_tile_string.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0042_wishing_well.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0162_fountain_drinker.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0502_lookobj_describe.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x06A4_lookobj_print_object_string.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x06F8_signs_dat_print.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x07E4_wanted_poster_render.md`.
- The dungeon map's cell size and origin, its twenty-two by twenty-two extent,
  the modulo-eight wrap rule, the fixed frontier bound, the two eight-by-eight
  one-bit fonts that supply its glyphs, the per-class font selection, the
  single-cell fountain and energy-field vector drawings, and the withdrawal of
  the peer-view tint branch and of the twelve-row cell -- derived from private
  analysis note
  `u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.
- The sky renderer's two presentation paths, the eight rows, the calendar-driven
  column rule, the per-row body and Shadowlord-marker geometry, and the
  retraction of the chunk-map/party-marker reading —
  `u5-decomp/functions/LOOKOBJ_OVL/0x0366_gem_world_map_renderer.md` and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 5.
- Source provenance: the telescope identity of tile `0x59`, its three shipped
  placements, the placeholder-description reconciliation, the separation from
  the wishing-well tile, and the absence of any gem or item precondition on the
  Look route are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x01AC_view_blit_tile.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x024C_view_party_marker.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0A9C_set_view_origin.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0ABE_view_class1_corners.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0B04_view_class2_fill.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0B60_view_class4_two_horizontals.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0B98_view_class5_center_bars.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0BD0_view_class6_full_box.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0C36_view_class8_diagonal_steps.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0C9C_view_class9_lines_blits.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0CF4_view_dungeon_room_tile.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0DDA_view_classB_two_blits_modal.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0E16_view_classD_two_pair_modal_split.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0E7A_view_creature_marker.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x0F7E_view_dispatch.md`.
- `u5-decomp/functions/LOOKOBJ_OVL/0x10FC_local_view_render.md`.
- `u5-decomp/functions/DNGLOOK_OVL/_OVERVIEW.md`.
- `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`.
- `u5-decomp/functions/DNGLOOK_OVL/0x06A8_dnglook_v_view.md`.
- The complete top-down trigger set, the dispatch order, the redirect tiles,
  the clock/shrine/dungeon appenders, and the confirmation that the tested
  byte is a live terrain tile rather than an active-object class —
  `u5-decomp/notes/npc_look_talk_trigger_retrace_2026-08-22.md`.
