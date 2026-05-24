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
3. Resolves the visible active-object class at that coordinate.
4. Checks whether a per-map object entry also matches the target coordinate and
   active floor.
5. Dispatches to an object, sign/poster, special vision, or terrain
   description path.

The ordinary terrain description uses `LOOK2.DAT`: the raw tile id selects a
description record. The format of that table is specified in
`formats/look2-dat.md`. LOOK2 has two public lookup domains: terrain tile ids
use the lower terrain-description half, while active-object and per-map object
classes use the upper object-description half. Several tile ids can share one
description record.

Special LOOKOBJ look cases include:

- **Per-map object entry.** Prints the object-description form from the upper
  LOOK2.DAT object-description range. The object branch appends the same
  line-spacing cleanup as terrain descriptions so object and terrain look text
  remain visually consistent.
- **Signs and wanted posters.** Prints the sign/poster heading, then renders
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
- **Clock tiles.** Prints the tile description and appends the current game
  time using the normal twelve-hour AM/PM presentation.
- **Shrine and dungeon-entrance tiles.** Prints the generic tile description
  and appends the shrine or dungeon name selected by scene/tile context.
- **Fountains.** Prompt for the drinking party member; cancelling prints the
  no-one result. Dead or asleep members refuse as incapacitated. Any other
  selected member receives the refresh message. The overworld/town fountain
  result is presentation-only: this LOOKOBJ path does not restore HP, cure
  status, wake sleepers, or otherwise write party state. Dungeon fountains are
  the state-changing fountain family and are specified in `dungeon-mode.md`.
- **Wishing wells.** Prompt for a coin and a wish, then run the well-specific
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
- **Death-vision tile.** Prompts for a party member and rolls `1..30` against
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

LOOKOBJ also contains a full Britannia chunk-map renderer used by a special
look path and related view contexts. That renderer paints an eight-row by
twenty-two-column shorthand map of Britannia chunks, wraps the chunk walk at
the world edges, marks the party's current chunk with a crosshair-style marker,
prints a day/night flavour line, waits for input, and leaves the underlying
world state unchanged. A view-restore flag causes the ordinary world view to be
repainted after the overlay closes. The traced LOOKOBJ path that enters this
renderer from ordinary Look is keyed by tile id `0x59`; the final catalog name
for that tile remains a tile/LOOK2 reconciliation issue and should not change
the renderer contract.

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
| Frame fill | Class `3`, the center fill in class `0x10`, and the full-map party marker layer. |
| Frame line / structure outline | Classes `4`, `5`, `6`, `7`, `0xE`, and compatibility class `0x5A`. |
| Normal terrain | Class `0xF` and the normal-mode branches of `0xA`, `0xB`, and `0xD`. |
| Secondary terrain | Classes `1`, `2`, `9`, the fixed top layer of class `0xD`, and one class-`0xA` branch. |
| Peer/blue terrain | Peer/gem-view branches of classes `0xA`, `0xB`, and `0xD`. |
| Dedicated rough terrain | Class `8` only. |

The full Britannia chunk-map renderer is a separate overlay from the local
32-by-32 view. Its base chunk-cell painter uses the world-map glyph family,
places each shorthand cell on an eight-pixel grid, then overlays the party
marker from the frame-fill family after the base glyph. The marker is clipped
against the visible strip and is composed as a small crosshair/diamond-shaped
highlight. The map is eight rows by twenty-two columns, wraps at the world
edges as it walks the chunk index, prints the day/night flavour line after
painting, then busy-waits until any key is available.

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
DNGLOOK's minimap renderer. The renderer:

- clears the side panel used by the first-person dungeon view, covering the
  rectangle from `(8,8)` through `(183,183)`;
- initializes a temporary unrevealed/visited grid and queue;
- seeds the queue at the party's current cell;
- flood-walks up to eight neighbours per visited cell in this order:
  northwest, north, northeast, west, east, southwest, south, southeast;
- converts each accepted scratch coordinate back to the current dungeon level's
  wrapped eight-by-eight cell coordinates;
- paints each visible cell by dungeon class;
- stops expansion only on dungeon minimap wall presentation classes;
- waits for a keypress or poll result;
- clears the same side-panel rectangle and restores the first-person dungeon
  renderer.

When the magic peer-view flag is active, the renderer applies the same
alternate/tinted tile-source branch used by the peer spell. This affects
presentation only; it does not change the dungeon cell data.

The minimap is a temporary side-panel overlay. It is not a persistent automap,
does not write exploration bits, and is repainted from the current dungeon
record every time the player spends a gem.

The visited grid used by this flood walk is separate scratch state, not a flag
inside the loaded dungeon cells. Dungeon cell bit `0x08` remains class-specific
variant/overlay data owned by dungeon-mode systems; View must not treat it as
seen/unseen map memory.

Dungeon minimap floodability is not the same as movement passability. The
class-to-glyph and flood-return table lives in `systems/dungeon-mode.md`; in
short, `0xB?`, `0xC?`, and `0xD?` wall presentation classes stop expansion,
while heavy-door/room-trigger classes still paint a door glyph and allow the
minimap flood to continue.

The dungeon minimap is also source-family based rather than raw-pixel-table
based. Passage, ladder, chest, pit, door, and wall classes emit the glyph ids
specified in `systems/dungeon-mode.md`. Fountain cells paint a two-by-three
multi-cell icon rooted at the mapped cell. The `0x8?` stair/field helper paints
stacked horizontal rules through the upper part of the minimap cell using the
dungeon minimap source families. Peer-view mode changes the source family for
the magic-vision tint branches only; it does not change the flood queue, visited
grid, or dungeon bytes.

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
handling, fountain and wishing-well special cases, full-map and local view
overlays, dungeon look descriptions, and dungeon minimap flood behavior are
fixed. Remaining work is visual cataloging and pixel-level parity, not command
state or persistence behavior.

- **Exact visual QA.** The clean per-class pixel/stroke placement, source
  family selection, dungeon flood order, and overlay clear/restore rectangles
  are specified above. Remaining visual parity work is empirical screenshot QA
  against DOS output and catalog naming for source-family palettes, not unknown
  gameplay or renderer control flow.
- **Tile special cases.** Tile id `0x59` is the traced ordinary-Look trigger
  for the full Britannia map renderer. Its final in-world catalog label still
  needs reconciliation with the tile catalog and `LOOK2.DAT` description.

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
- `u5-decomp/functions/LOOKOBJ_OVL/0x0366_gem_world_map_renderer.md`.
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
