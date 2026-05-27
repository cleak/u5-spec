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
draw calls. It also influences which paired graphics resource depth is chosen:
EGA-like output uses the `.16` family, while low-colour output uses the `.4`
family. See `formats/tiles.md`.

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
- `PROPORT.PCS`, `TITLE.BIT`, `BRITISH.BIT`, and `WD.BIT` use the
  driver-compressed sparse strip resource format described in
  `formats/font-pcs.md`, `formats/bit.md`, and `display-driver-abi.md`.
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
`STARTSC` surface is drawn, during no-key finished-menu idle polling, and in
intro-local preview or transition helpers that call the same tick. The Lord
British signature walker is paced by keyboard polling and real-time delay
ticks; those delay ticks do not advance the four-frame title strip. The
observed driver implementations maintain a compact four-frame
title/flame-style cycle. A cleanroom renderer should expose this as an
intro-only animation step that can be advanced on demand, independent of world
time, NPC schedules, or active-object animation.

For the EGA-compatible baseline, that title tick copies a driver-local
four-frame strip into the title screen at pixel `(0, 65)`, covering
`320 x 49` pixels, with covered columns `0..319` and covered rows `65..113`.
The first frame after driver or renderer initialisation is frame `0`; each
clear-carry tick draws the current frame and then advances the frame index
modulo four. Redrawing `STARTSC`, re-highlighting a menu row, or returning from
a non-play intro subflow does not reset that frame index.

The original driver produces the frames at runtime rather than loading them
from `TITLE.BIT`, `BRITISH.BIT`, `STARTSC`, or any other external resource.
The EGA driver reads its source from its own back-buffer region of EGA video
memory, treating it as four 320-pixel-wide frame bands with a 50-row source
stride and copying the upper 49 rows of the selected band to the destination
rectangle. The back-buffer holding those bands is populated by other
display-driver entries earlier in the intro setup; the bands are not present
as a contiguous data block inside the `EGA.DRV` file image, and there is no
fixed byte offset within the driver image at which a clean engine can find
them by passive parsing. The public v1 contract is therefore the destination
rectangle, four-frame cadence, intro-only ownership, opaque overwrite
semantics, and separation from gameplay time; exact reuse of the historical
driver-resident pixels is a driver-binary parity issue, not a static
asset-format requirement, and a clean engine that wants byte-identical title
visuals must either capture the runtime back-buffer through the original
driver or supply independently authored replacement frames.

A cleanroom replacement must be independently authored. For v1 fidelity, treat
the replacement as four opaque frames in the active EGA-compatible palette:
each title-tick call draws the next frame over the full `(0, 65)` `320 x 49`
destination rectangle, including black pixels, then advances the frame index
modulo four. The renderer should not alpha-blend, mask, scale, crop, or reuse
the previous surface contents inside that rectangle. A static placeholder is
acceptable only as an explicit development fallback; it does not satisfy the
four-frame idle-animation contract.

The animation advances only when intro or cutscene code requests the title
tick. It runs once after `STARTSC` drawing, once for each no-key finished-menu
poll pass, and during start/menu transition or preview helpers that explicitly
call the same tick. Finished-menu idle polling auto-enters Return-to-View after
two hundred consecutive no-key passes; valid and invalid nonzero key passes do
not add an extra idle tick. Blocking waits or message paths that do not call
the title tick should not advance the title/menu idle animation on their own.

Story-sequence art selection and primary placement are specified in
`intro.md`, including the special secondary panel draws. The display layer
only needs to provide the requested panel draws, the step-1 rectangle
transition, display-state changes, and frame presentation. Story steps wait for
player input in the intro code; any transition work is a local visual effect
around that input-driven sequence, not a gameplay-time advance.

For the step-1 story rectangle transition, the intro draws the extra story
panel first and then reveals the inclusive rectangle `(40, 86)..(75, 120)` from
left to right. The effect is 36 title ticks long, revealing one pixel column per
tick from `x = 40` through `x = 75`. Previously revealed columns remain visible,
unrevealed columns retain the prior screen contents, and the display layer must
not add dithering, blending, recolouring, or gameplay-time advancement. This
step-1 contract does not define bounds or rates for any other intro or endgame
caller.

The start/menu-screen loader has its own caller contract. After `STARTSC` has
been drawn, callers that request the animated loader path reveal the inclusive
upper-screen rectangle `(0, 0)..(319, 100)` from left to right using the same
one-column-per-title-tick helper. This is a title/menu-screen effect, not a
story-slide effect. Input is sampled after the reveal, so the reveal itself is
blocking once started.

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
must preserve that ordering. The exact resident helper raster internals remain
below the public v1 driver contract unless hardware-level visual parity becomes
in scope.

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
- **Title tick replacement art.** The EGA title-tick destination rectangle,
  four-frame cadence, and driver-local ownership are specified. The historical
  source pixels live inside the original display driver; replacement frames for
  a driver-free cleanroom renderer must be independently authored unless exact
  driver-binary parity becomes in scope.
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
- **Alternate hardware parity.** CGA, Hercules, and Tandy conversion details
  are outside the v1 baseline unless a later implementation targets those modes
  explicitly.

## 11. Sources

This spec is a cleanroom prose rewrite from private analysis notes. It omits
assembly, decompiled code, raw jump tables, driver binary bytes, and private
addresses.

- Driver selection and load sequence:
  `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
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
  evidence, and signature delay/poll separation:
  `u5-decomp/functions/INTRO_OVL/0x2090_title_tick.md`,
  `u5-decomp/functions/INTRO_OVL/0x094E_iter_until_kbd.md`,
  `u5-decomp/functions/FLAMES_OVL/0x0000_flames_entry_stub.md`, and
  `u5-decomp/formats/ega-driver.md`.
- Story panel draw ordering and the local rectangle transition:
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md` and fresh
  local rectangle-transition helper analysis.
- Return-to-View preview ownership of `MISCMAPS.DAT` map strips, command
  stream, actor draw scheduling, and effect steps:
  `u5-decomp/functions/FONT_OVL/_OVERVIEW.md` and fresh local FONT helper
  analysis.
