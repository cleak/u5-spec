# Display Driver and Rendering Contract

## 1. Scope

Ultima V separates gameplay and UI code from hardware-specific drawing through
a loaded display driver. The original IBM PC build can load CGA, EGA, Tandy, or
Hercules driver modules. Most public gameplay specs do not need the binary
driver ABI, but they do need a shared rendering contract: which coordinate
system callers use, which draw operations exist, when frames become visible,
and which asset formats feed those operations.

This document defines that v1 contract for a cleanroom engine. The
driver-facing ABI for the EGA baseline is specified separately in
`display-driver-abi.md`; the underlying mode setup, planar buffer layout, and
palette mechanics are specified in `display-driver-mode.md`. Those companion
documents name dispatch slots, buffer layouts, palette tables, and resource
contracts without reproducing driver code. A modern implementation may
collapse the historical drivers into one renderer as long as it preserves the
visible behaviour described here and the asset-facing contracts in the format
specs.

## 2. Driver Selection

Startup records an optional display-family request from the command line. The
intro startup path then chooses one display driver and loads it before the
title/menu flow draws anything.

| Request | Original driver family | V1 public role |
|---|---|---|
| `C` | CGA | Historical low-colour backend. |
| `E` | EGA | Default v1 visual baseline. |
| `T` | Tandy | Historical alternate 16-colour backend. |
| `H` | Hercules | Historical monochrome backend. |

The selected driver determines which hardware implementation receives later
draw calls. It also selects which member of the paired graphics-resource family
every later load uses. The rule is a straight two-way split on the selected
driver, decided once during intro startup and never revisited:

| Selected driver | Graphics resource family | UI colour set |
|---|---|---|
| CGA | `.4` (low colour) | low-colour set |
| EGA | `.16` (high colour) | high-colour set |
| Tandy | `.16` (high colour) | high-colour set |
| Hercules | `.4` (low colour) | low-colour set |

**Tandy takes the high-colour family and Hercules takes the low-colour family.**
That pairing follows the colour depth of the hardware, not the resolution:
Tandy is a sixteen-colour mode like EGA, while Hercules is one bit per pixel and
CGA is four colours, so both of those read the reduced-depth art. Any statement
that Tandy shares CGA's asset family, or that Hercules shares EGA's, is wrong.

The selection is applied by rewriting the extension of every entry in the
startup asset-name table: a name whose extension begins with the high-colour
digit is rewritten to the low-colour digit and shortened by one character.
Names in the driver-bitmap and proportional-font families are untouched by that
pass, because their extensions do not begin with a digit. See `formats/tiles.md`
for the family itself.

Exactly one other asset differs by driver: the glyph pair. Hercules loads the
high-resolution monochrome glyph and rune files; the other three drivers load
the 8-by-8 bitmap pair. That is specified in `intro.md` section 3. There is no
separate Hercules-only screen-art family anywhere in the distribution.

The startup pass that selects the family also publishes a small table of user
interface colour indices used by later intro and preview screens. Its contents
differ between the two families:

| Slot | High-colour value (EGA, Tandy) | Low-colour value (CGA, Hercules) |
|---:|---:|---:|
| 0 | 4 | 2 |
| 1 | 15 | 3 |
| 2 | 1 | 1 |
| 3 | 2 | 1 |
| 4 | 5 | 2 |
| 5 | 14 | 3 |
| 6 | 7 | 3 |

The low-colour values are all inside `0..3` because the CGA and Hercules
drawing-colour entries mask their argument to two bits before translating it,
so any larger index would alias. Known consumers so far are the Return-to-View
caption panel (slot 2 for the panel fill, slot 1 for the rule beneath it) and
the Return-to-View fixed wipe command (slot 1).

For v1 asset compatibility, an implementation should support the EGA-compatible
rendering path and the original asset selectors. It may reject or map the
historical CGA/Tandy/Hercules requests unless exact hardware parity is a goal.

The original distribution ships only the four driver families listed above.
There is no separate VGA driver. VGA-equipped hosts run the EGA driver in the
standard 320-by-200, 16-colour mode, because VGA hardware preserves backward
compatibility with that EGA mode at the BIOS level. A modern engine that wants
to claim "VGA support" should treat that label as a synonym for "the EGA-
compatible rendering path running on a VGA-class adapter"; it does not imply a
new dispatch table, a wider colour palette, a higher resolution, or any 256-
colour code path. Higher-resolution and 256-colour modes were not shipped with
Ultima V and are not part of this contract.

## 3. Coordinate Systems

The gameplay and UI layers use two coordinate systems.

| Coordinate space | Extent | Unit | Primary users |
|---|---:|---|---|
| Text cells | 40 x 25 | 8-by-8 pixel cell | Text windows, cursor movement, scroll and clear windows. |
| Screen pixels | 320 x 200 | Pixel | Bitmap drawing, viewport rendering, title art, effects. |

Text-window descriptors store inclusive cell rectangles. A rectangle from
cell `(0, 0)` to `(39, 24)` covers the full text grid. When a text rectangle is
converted to pixels, the top-left cell is multiplied by eight and the
bottom-right cell is multiplied by eight with seven added, so cell `(39, 24)`
ends at pixel `(319, 199)`.

Pixel rectangles are also inclusive. Before a bitmap or rectangle operation is
sent to the display layer, callers normalize both axes so the first coordinate
is not greater than the second, then clamp X to `0..319` and Y to `0..199`.
This means a caller may supply the two corners in either order and still draw
inside the visible screen.

## 4. Rendering Operations

The original executable dispatches drawing through a small set of driver
operations. A cleanroom renderer should expose the same semantic operations,
not the original numeric dispatch entries.

| Operation | Inputs | Visible contract |
|---|---|---|
| Initialise graphics mode | Selected display family | Prepare the 320-by-200 drawing surface and any text-cell state before the intro draws. |
| Render one text cell | Cell coordinate, prepared 8-by-8 glyph bitmap, colour attribute, style flags | Draw exactly one glyph cell at the active text-window cursor. |
| Clear rectangle | Inclusive pixel rectangle, colour or attribute | Fill the rectangle; used by text clear and title/menu screen preparation. |
| Scroll rectangle | Inclusive pixel rectangle, signed pixel delta | Move the rectangle contents vertically and blank the exposed band. Text auto-scroll uses one cell, or eight pixels. |
| Draw tile/panel graphics | Decoded `.16` or `.4` graphics body, destination placement | Convert the asset pixels to the active display representation and draw them in the requested scene. |
| Draw one-bit bitmap | Decoded `.BIT` body block, inclusive destination or placement | Convert one-bit artwork such as `TITLE.BIT` and `BRITISH.BIT` to display pixels. |
| Paint one pixel or path point | Screen coordinate, current colour or mode | Used by the `BRITISH.PTH` signature walker and small scripted effects. |
| Present frame | Current back buffer or dirty surface | Make all simulation/render updates for the tick visible. |
| Palette or title tick | Scene-specific timing state | Advance title, fade, palette, or flame-style display effects when the intro or cutscene asks. |

The text system prepares glyph bitmaps and style effects before dispatching a
cell render. The display layer owns conversion from that prepared one-bit cell
pattern and colour attribute into the active pixel representation.

## 5. Asset Rendering

Renderable assets reach the display layer only after their file-level container
has been decoded:

- Paired `.16` and `.4` graphics use the shared LZW envelope and the graphics
  archive layout in `formats/tiles.md`.
- `TITLE.BIT`, `BRITISH.BIT`, and `PROPORT.PCS` use the same LZW envelope
  wrapping a one-bit-per-pixel sub-image list; `WD.BIT` carries that list raw.
  See `formats/bit.md` and `formats/font-pcs.md`. These are decoded by the
  caller, not by a driver dispatch entry.
- Fixed-cell fonts use `formats/font-ch.md` and `formats/font-hcs.md`.

The renderer should not infer a file format from the historical driver call
name. In particular, the public `.BIT` specs now describe the decoded one-bit
body; a modern renderer consumes that decoded body and performs display
conversion. It should not treat the decoded bytes as EGA planar memory or as a
complete framebuffer.

## 6. Text Integration

Text output is specified in `text-output.md`. The display layer participates at
three points:

1. Rendering one prepared glyph cell at an absolute cell coordinate.
2. Clearing or scrolling the active text-window rectangle after the text system
   has converted the cell rectangle into pixels.
3. Applying colour attributes and style-transformed bitmaps consistently.

Text windows are gameplay/UI state, not driver state. The display layer should
not decide wrapping, cursor movement, centering, or which window is active.

## 7. Viewport and Animation Presentation

World rendering proceeds through the resident redraw path: visibility and tile
state are produced first, then the viewport is rendered, and then animation
housekeeping gives the display layer a chance to present the frame. The public
ordering requirement is:

1. Apply gameplay or idle-tick state changes.
2. Rebuild or refresh the visible tile/object grid.
3. Draw the viewport and any UI changes that observe the new state.
4. Present or flush the resulting frame.

A modern engine may use double buffering, dirty rectangles, retained surfaces,
or an immediate-mode canvas. The visible result should still reflect the same
ordering: a frame is presented only after the relevant gameplay, animation,
visibility, and draw steps for that tick have completed.

For the EGA-compatible baseline, ordinary viewport tiles and fixed-cell text
are drawn directly to the front buffer. The historical driver back buffer is
reserved for full-screen bitmap staging and transition/effect paths such as
dissolves, silhouette stamping, and title/menu animation; it is not the
ordinary tile or glyph destination. Mode setup selects hardware page zero as
the visible page; later presentation effects copy or dissolve from
driver-managed page memory into that visible page rather than flipping ordinary
world/text frames between hardware pages.

### Shared game-screen frame

The chrome that surrounds gameplay — the border around the world viewport, the
party stats panel on the right, and the command/prompt area along the bottom —
is a single mode-independent paint. Overworld, town, dungeon, and combat all
present the same frame; it is not combat chrome, and a cleanroom engine should
not attach it to combat entry or to any other single mode. Earlier analysis
drafts labelled it as combat screen setup, which was a mistaken inference from
neighbouring combat code rather than from what the routine does.

The paint is deterministic and reads no gameplay state: not save data, not the
scene state, not combat state, not party contents. Its only inputs are the
border colour indices selected for the active display family. Because of that
it can legitimately run before any world state exists — the intro's Journey
Onward path draws the frame before it reads the save file, so the player sees
the gameplay layout appear while the load proceeds (see `intro.md` and
`save-load.md`).

On the 320-by-200 baseline the frame divides the screen into three zones:

| Zone | Extent | Contents |
|---|---|---|
| World viewport | Left band, roughly 184 pixels wide, inset from the top and left screen edges | Tile view for the active mode. |
| Stats panel | Right band, the remaining width of roughly 134 pixels | Party rows and the bottom information block described in `stats-panel.md`, split into an upper, a middle, and a lower zone by two horizontal dividers. |
| Command/prompt area | Band along the bottom beneath the viewport | Text output and command echo. |

The frame itself is built from filled rectangles: a full-screen ground fill, a
top bar, left and bottom viewport borders, the vertical divider between the
viewport and the stats panel, the stats panel's outer right edge, and the two
horizontal dividers inside that panel. Three box-drawing glyphs are then
stamped through the ordinary text path at the top-left, top-right, and
bottom-left text-grid corners, and line-draw helpers close the outlines of the
viewport, the stats panel, and the prompt area. There are no conditional
branches in the paint, so the frame looks identical on every entry.

## 8. Intro and Cutscene Effects

Intro and cutscene code uses the same display layer for title art, Lord British
signature strokes, story panels, endgame panels, rectangle transitions,
display-state changes, palette changes, and short display ticks.

The currently specified title layout is in `intro.md`: all ten `TITLE.BIT`
blocks, the `BRITISH.BIT` bitmap, and the four `BRITISH.PTH` pen origins are
fixed there. This display-driver spec owns only the rendering operations those
placements require.

The title/menu idle animation is a display-driver tick, not a gameplay tick.
The intro advances it only through explicit title-tick call sites: after the
start/menu surface is drawn, during no-key finished-menu idle polling, and in
intro-local preview or transition helpers that call the same tick. The Lord
British signature walker is paced by keyboard polling and real-time delay
ticks; those delay ticks do not advance the four-frame title strip. The
observed driver implementations maintain a compact four-frame
title/flame-style cycle. A cleanroom renderer should expose this as an
intro-only animation step that can be advanced on demand, independent of world
time, NPC schedules, or active-object animation.

For the EGA-compatible baseline, that title tick copies a four-frame strip into
the start/menu screen at pixel `(0, 65)`, covering `320 x 49` pixels, with
covered columns `0..319` and covered rows `65..113`. The first frame after
driver or renderer initialisation is frame `0`; each clear-carry tick draws the
current frame and then advances the frame index modulo four. Redrawing the
start/menu screen, re-highlighting a menu row, or returning from a non-play
intro subflow does not reset that frame index.

**Correction.** Earlier revisions of this section stated that the driver
produces the four frames at runtime, that they exist at no fixed offset in any
external resource, and that a clean engine must author replacement art or
capture the runtime back buffer. All of that is withdrawn. The frames are
shipped art: records `1`, `2`, `3` and `4` of the `ULTIMA` banner archive, sized
`288 x 49`, `288 x 49`, `288 x 49` and `288 x 50`. The start/menu loader clears
the driver's back buffer and draws those four records into it at `(16, 0)`,
`(16, 50)`, `(16, 100)` and `(16, 150)` before the menu is shown; the tick then
copies 49 rows at full 320-pixel width starting at back-buffer row
`50 x frame_index` to the destination rectangle. The 16 columns at each end of
every band come from the clear, not from the art. `intro.md` section 5 carries
the full contract and the two equivalent ways to implement it.

Each title-tick call draws the next frame over the full `(0, 65)` `320 x 49`
destination rectangle, including background-coloured pixels, then advances the
frame index modulo four. The renderer must not alpha-blend, mask, scale, crop,
or reuse the previous surface contents inside that rectangle; the rectangle is
fully overwritten every time. Pixels outside the rectangle are never touched.

The animation advances only when intro or cutscene code requests the title
tick. It runs once after the start/menu screen is drawn, once for each no-key
finished-menu poll pass, and during start/menu transition or preview helpers
that explicitly call the same tick. Finished-menu idle polling auto-enters
Return-to-View after two hundred consecutive no-key passes; valid and invalid
nonzero key passes do not add an extra idle tick. Blocking waits or message
paths that do not call the title tick should not advance the title/menu idle
animation on their own.

Story-sequence art selection and primary placement are specified in
`intro.md`, including the special secondary panel draws. The display layer
only needs to provide the requested panel draws, the step-1 rectangle
transition, display-state changes, and frame presentation. Story steps wait for
player input in the intro code; any transition work is a local visual effect
around that input-driven sequence, not a gameplay-time advance.

For the step-1 story rectangle transition, the intro composes the extra story
panel on the hidden surface first and then transfers the inclusive rectangle
`(40, 86)..(75, 120)` to the visible page with the same rectangle-dissolve entry
(`display-driver-abi.md` section 9.6). **Correction.** Earlier revisions of this
section described that transfer as a left-to-right reveal of one pixel column
per title tick, 36 ticks long. That is withdrawn: the effect is not
left-to-right, not per-column, and not paced by title ticks at all. It is a
single blocking driver call that visits every pixel of the rectangle exactly
once in the driver's deterministic pseudo-random order. The rectangle bounds and
the ordering statements around it are unchanged, and the display layer still
must not add dithering, blending, recolouring, or gameplay-time advancement.
This step-1 contract does not define bounds or rates for any other intro or
endgame caller.

The start/menu-screen loader has its own caller contract, and it is not a
column wipe. After the `ULTIMA` banner record has been drawn into the back
buffer, callers that request the animated loader path transfer the inclusive
upper-screen rectangle `(0, 0)..(319, 100)` to the visible page with the
rectangle-dissolve entry described in `display-driver-abi.md` section 9.6 - one
call, self-paced, every pixel visited exactly once. The plain caller path copies
the same rectangle in one step. Input is sampled after the transfer, so the
transfer itself is blocking once started.

The Return-to-View preview is another intro-local display sequence. Its map
strips and command stream live in `MISCMAPS.DAT`; the display layer only sees
the resulting tile draws, preview actors, rectangle operations, waits, and frame
presentation. It should treat the sequence like title/story effects: no
gameplay ticks, saved-game time, NPC schedules, or world-mode redraws run while
the preview owns the screen.

Combat can request one driver-owned tile-graphics restoration step after the
arena loop returns but before the world view is restored. The binary driver ABI
fixes this as dispatch offset `0x6C` with mode value `1`; that reached mode
restores driver-saved tile bytes after earlier tile-asset mutation. The combat
framer only samples and clears the resident restoration flag; known flag setup
belongs to dungeon room-layout state. This is not a standalone presentation
effect, and it does not advance gameplay time or alter combat results.

The Return-to-View script-level visual schedule is owned by
`formats/location-dat.md`: local cell effects render at tile row `y + 7`,
temporary actor draws also use actor row `y + 7`, and the fixed wipe command
emits two inclusive pixel rectangles per step for five steps. The display layer
must preserve that ordering.

The resident helper behind those preview draws is no longer an open item. Both
the preview cell draws and the preview actor draws go through the ordinary
16-by-16 viewport tile entry, with the viewport origin temporarily moved. The
resulting geometry is given in `intro.md` section 12 and
`formats/location-dat.md` section 11: origin `(8, 16)`, 16-by-16 cells, screen
tile rows `7..10` and columns `0..18`, i.e. the pixel rectangle
`(8, 128)..(311, 191)`. The five fixed wipe rectangles are absolute framebuffer
pixel rectangles on that same page. Nothing about the preview is scaled,
cropped, or drawn through a private miniature raster.

### Per-driver title-band geometry

The title/menu idle band is the one intro effect whose geometry differs between
driver families, because each family has its own framebuffer shape. All four
keep the same modulo-four frame index and all four read the band out of their
own hidden surface.

| Driver family | Hidden-surface band pitch | Rows copied | Destination top row | Copied width |
|---|---:|---:|---:|---:|
| EGA | 50 | 49 | 65 | 320 pixels |
| CGA | 50 | 49 | 65 | 320 pixels |
| Tandy | 50 | 49 | 65 | 320 pixels |
| Hercules | 75 | 74 | 97 | 640 of the 720 pixels in a row |

## 9. Implementation Rules

- Treat EGA-compatible 320-by-200 rendering as the v1 baseline.
- Use `display-driver-abi.md` for binary-compatible driver dispatch, including
  the corrected `0x3F` filled-rectangle and `0x42` compressed-bitmap entries.
- Keep text-cell behaviour in `text-output.md`; use the renderer only for
  prepared cells, clears, scrolls, and final pixel conversion.
- Normalize and clamp pixel rectangles before drawing.
- Decode file containers before handing image bodies to the renderer.
- Preserve the update-then-render-then-present ordering for idle animation and
  viewport redraws.
- Preserve the original asset-depth selection rule: use `.16` resources for
  EGA-compatible output and `.4` resources only when intentionally supporting a
  low-colour historical backend.
- Do not require the original `*.DRV` binaries in a modern cleanroom engine.

## 10. Known Uncertainties

- **Alternate driver ABI details.** The EGA dispatch surface is specified in
  `display-driver-abi.md`. Exact CGA, Hercules, and Tandy conversion details
  remain follow-up work unless those historical backends become targets.
- **Dirty rectangles and low-level port sequencing.** The public contract
  requires frame presentation in the right order. The EGA baseline's visible
  page-zero policy and back-buffer copy/dissolve boundary are specified in
  `display-driver-abi.md`; exact port-level sequencing is only relevant for a
  hardware-driver reproduction.
- **Title tick art.** Closed. The destination rectangle, four-frame cadence,
  staging layout, and source records are specified in section 8 and in
  `intro.md` section 5: the frames are records `1..4` of the `ULTIMA` banner
  archive, staged into the driver's back buffer at a 50-row pitch. No authored
  replacement art and no driver-binary reuse are required. Only the alternate
  display backends remain: the CGA, Hercules, and Tandy builds stage the
  equivalent low-colour archive records, and their pixel conversion is part of
  the alternate-hardware parity item above.
- **Story rectangle-transition helper.** Fixed title artwork placement, menu
  idle ticking, story-art selection, story primary placement, and the step-1
  story-transition rectangle reveal are specified in `intro.md`. A focused
  intro slide-loop caller census did not find a step-2 or later story-page
  column-wipe table. Any non-story intro helper use or endgame display-helper
  use needs its own caller-specific bounds and reveal-rate trace.
- **Return-to-View resident helper internals.** The script-level command
  schedule, rectangle coordinates, actor draw ordering, and preview tick counts
  are specified in `formats/location-dat.md`. The remaining display gap is the
  exact resident helper implementation for special actor draws, local
  cell-effect rastering, and the short fixed wait.
- **Which entry paths repaint the game-screen frame.** The frame's content and
  its independence from gameplay state are settled, and the intro's Journey
  Onward path is a confirmed painter. Whether each mode-loop entry repaints it
  on every transition, or whether it persists once painted, has not been traced
  exhaustively. Because the paint is deterministic, repainting more often than
  the original is visually indistinguishable except for the cost of the redraw.

- **Alternate hardware parity.** CGA, Hercules, and Tandy conversion details
  are outside the v1 baseline unless a later implementation targets those modes
  explicitly.

## 11. Sources

This spec is a cleanroom prose rewrite from private analysis notes. It omits
assembly, decompiled code, raw jump tables, driver binary bytes, and private
addresses.

- Driver selection and load sequence:
  `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- Shared game-screen frame — zone layout, deterministic paint, absence of any
  gameplay-state dependency, and the correction that the frame is common to all
  gameplay modes rather than combat-specific:
  `u5-decomp/functions/ULTIMA_EXE/0x637E_combat_screen_layout.md` (the note file
  keeps its original filename; its contents were corrected on 2026-05-24) and
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- EGA dispatch ABI, slot inventory, rectangle fill, driver-compressed bitmap
  decode, 16-by-16 tile blit, and 8-by-8 glyph blit:
  `u5-decomp/formats/ega-driver.md` and the `u5-decomp/functions/EGA_DRV/`
  notes.
- Text descriptor initialization, cell rendering, rectangle conversion, and
  scroll/clear dispatch:
  `u5-decomp/functions/ULTIMA_EXE/0x1184_init_text_descriptor_table.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x16BA_putchar.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x1F77_descriptor_to_pixel_rect.md`.
- Pixel-rectangle normalization and bitmap draw dispatch:
  `u5-decomp/functions/ULTIMA_EXE/0x0AA6_draw_compressed_bitmap.md`, plus
  fresh local rectangle-normalization verification.
- Redraw, animation, and frame-presentation ordering:
  `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
- Combat-exit tile-graphics restoration dispatch:
  `u5-decomp/functions/ULTIMA_EXE/0x6FBC_post_combat_trap.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`, and
  `u5-decomp/formats/ega-driver.md`.
- Title display tick, intro call-site cadence, driver-side frame-counter
  evidence, the identification of the four idle frames as `ULTIMA` archive
  records `1..4` and of their 50-row staging pitch in the back buffer, and
  signature delay/poll separation:
  `u5-decomp/functions/INTRO_OVL/0x2090_title_tick.md`,
  `u5-decomp/functions/INTRO_OVL/0x0010_four_row_helper.md`,
  `u5-decomp/functions/INTRO_OVL/0x05B0_startsc_loader.md`,
  `u5-decomp/functions/EGA_DRV/0x282D_animate_flames_strip.md`,
  `u5-decomp/functions/INTRO_OVL/0x094E_iter_until_kbd.md`,
  `u5-decomp/functions/FLAMES_OVL/0x0000_flames_entry_stub.md`,
  `u5-decomp/formats/ega-driver.md`, and
  `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`.
- Story panel draw ordering and the local rectangle transition:
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md` and fresh
  local rectangle-transition helper analysis.
- Return-to-View preview ownership of `MISCMAPS.DAT` map strips, command
  stream, actor draw scheduling, and effect steps:
  `u5-decomp/functions/FONT_OVL/_OVERVIEW.md` and fresh local FONT helper
  analysis.
