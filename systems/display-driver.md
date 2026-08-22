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
drawing-colour entries mask their argument to two bits before translating it
through a small driver-local table, so any larger index would alias. On the
Hercules path that translation does not produce a hue at all: the adapter is
one bit per pixel, so the four table outputs are a blank byte, two opposite
half-density dither patterns, and a solid byte. Read the "value" column for
that family as a pen selector, not as a colour.

Known consumers are the Return-to-View caption
panel (slot 2 for the panel fill, slot 1 for the rule beneath it), the
Return-to-View fixed wipe command (slot 1), the Ultima IV transfer preview
screen (slot 2 for its frame glyphs and panel bars, slot 1 for its pixel rules
and panel titles — `u4-transfer.md` section 6.1), and — the heaviest consumer —
the whole gameplay screen:

| Slot | Gameplay role |
|---:|---|
| 1 | Accent pen: every one-pixel rule of the game-screen frame, every bracket end-cap outline, and the standing text foreground. |
| 2 | Chrome pen: every solid chrome band, the rounded corner glyphs, and the filled body of every bracket end-cap. |
| 5 | Foreground of the sky strip's fixed hour marker (`moons.md`). |
| 6 | Foreground of the two moon markers in the sky strip (`moons.md`). |

Slots 0, 3 and 4 have no confirmed gameplay-screen consumer. Because these are
table entries rather than literals, an implementation should expose all seven
as configurable indices rather than hard-coding the EGA values.

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
scene state, not combat state, not party contents. Its only inputs are the two
border colour indices selected for the active display family. Because of that
it can legitimately run before any world state exists — the intro's Journey
Onward path draws the frame before it reads the save file, so the player sees
the gameplay layout appear while the load proceeds (see `intro.md` and
`save-load.md`).

#### The two chrome pens

The frame uses exactly two colours, both taken from the user-interface colour
table published in section 2, so the frame recolours itself per display family
without any code change:

| Role | UI colour slot | EGA/Tandy value | CGA/Hercules value |
|---|---:|---:|---:|
| Chrome fill — every solid band, the corner bevel glyphs, and the filled body of every bracket end-cap | 2 | 1 | 1 |
| Accent — every one-pixel rule, every end-cap outline stroke, and the standing text foreground the frame leaves behind | 1 | 15 | 3 |

On the EGA baseline that is chrome index `1` and accent index `15`. The paint
also leaves the text foreground set to the accent index when it returns, which
is the colour all later panel and message text inherits unless a caller changes
it.

#### Paint order

The frame is painted in three phases, in this order, with no conditional
branches anywhere in it. The order matters: phase 3 deliberately overpaints one
row or column of several phase-1 bands, and phase 2's opaque glyph cells carve
the rounded corners out of bands that phase 1 already filled. An implementation
that draws only the *visible* result, without reproducing the order, will get
the corner bevels and the label gaps wrong.

**Phase 1 — eight filled rectangles.** All rectangles are inclusive on all four
edges, in screen pixels.

| # | Colour | Rectangle `(x1, y1) - (x2, y2)` | Role |
|---:|---|---|---|
| 0 | black (index 0) | `(0, 0) - (319, 199)` | full-screen clear |
| 1 | chrome | `(0, 0) - (319, 6)` | top ribbon |
| 2 | chrome | `(0, 185) - (191, 191)` | bottom ribbon, viewport side only |
| 3 | chrome | `(0, 0) - (6, 191)` | left ribbon |
| 4 | chrome | `(185, 0) - (191, 191)` | centre divider ribbon |
| 5 | chrome | `(313, 0) - (319, 87)` | right ribbon — stops at `y = 87`, not at the bottom of the screen |
| 6 | chrome | `(192, 80) - (312, 87)` | lower stats divider band |
| 7 | chrome | `(192, 57) - (312, 63)` | upper stats divider band |

**Phase 2 — three rounded-corner glyph cells.** The text foreground is set to
the chrome colour and three glyphs from the fixed-cell text font (`IBM.CH`, or
its Hercules equivalent) are emitted through the ordinary text path into the
full-screen text window. The blit is opaque, so the clear bits of each glyph
punch black back through the ribbon fills and carve the bevel:

| Text cell | Glyph code | Shape |
|---|---:|---|
| `(0, 0)` | `0x7B` | rounded top-left |
| `(39, 0)` | `0x7C` | rounded top-right |
| `(0, 23)` | `0x7D` | rounded bottom-left |

There is **no bottom-right corner glyph**. The bottom-right of the screen is
the message window, not a chrome box. The font does contain a bottom-right
bevel and a solid block in the adjacent codes; the frame uses neither.

The resulting bevel profile, at the screen's left edge, is: column `x = 0`
chrome from `y = 5`, `x = 1` from `y = 3`, `x = 2` from `y = 2`, `x = 3` and
`x = 4` from `y = 1`, and `x = 5` onward from `y = 0`. The bottom-left glyph
mirrors that vertically and the top-right glyph mirrors it horizontally, so the
same profile appears at all three painted corners.

Because cursor coordinates are window-relative, the caller must have the
full-screen text window active for these three cells to land at the absolute
grid corners. Every observed caller does.

**Phase 3 — four rule outlines.** The pen is set to the accent colour and four
polylines are stroked. Coordinates are inclusive pixel endpoints; each vertex
list is walked in order from the first point.

| Box | Path | Result |
|---|---|---|
| A — world viewport | `(7, 7)` → `(7, 184)` → `(184, 184)` → `(184, 7)` → `(7, 7)` | closed box `(7, 7) - (184, 184)`; interior `x = 8..183`, `y = 8..183`, exactly 11 by 11 tiles of 16 pixels with tile `(0, 0)` at pixel `(8, 8)` |
| B — message window | `(191, 191)` → `(191, 87)` → `(319, 87)` | an open "L": left rule `x = 191` over `y = 87..191`, top rule `y = 87` over `x = 191..319`. The message window has no right or bottom rule; it runs to the screen edge. |
| C — roster box | `(191, 7)` → `(312, 7)` → `(312, 56)` → `(191, 56)` → `(191, 7)` | closed box `(191, 7) - (312, 56)`; interior text cells columns 24..38, rows 1..6 |
| D — counters box | `(191, 63)` → `(312, 63)` → `(312, 80)` → `(191, 80)` → `(191, 63)` | closed box `(191, 63) - (312, 80)`; interior text cells columns 24..38, rows 8..9 |

#### Filled extents versus visible extents

Phase 3 runs after phase 1 and repaints one row or column of several bands in
the accent colour. Both figures are published because both are needed: the fill
list is what an implementation must execute, and the visible list is what a
pixel comparison against the original will show.

| Phase-1 band | Overpainted by | Chrome actually visible |
|---|---|---|
| centre divider `x = 185..191` | left rules of boxes B, C and D at `x = 191` (for `y >= 7`) | `x = 185..190` |
| right ribbon `y = 0..87` | top rule of box B at `y = 87` (for `x >= 191`) | `y = 0..86` |
| upper stats band `y = 57..63` | top rule of box D at `y = 63` | `y = 57..62` |
| lower stats band `y = 80..87` | bottom rule of box D at `y = 80` and top rule of box B at `y = 87` | `y = 81..86` |
| top ribbon `y = 0..6` | not overpainted | `y = 0..6` |
| left ribbon `x = 0..6` | not overpainted | `x = 0..6` |
| bottom ribbon `y = 185..191` | not overpainted | `y = 185..191` |

Text row 24 (`y = 192..199`) is left black by the phase-0 clear and is never
painted again by any gameplay path. It belongs to no text window.

#### Resulting zones

| Zone | Pixels | Text cells | Contents |
|---|---|---|---|
| World viewport | interior `(8, 8) - (183, 183)` | not text | 11 by 11 tiles of 16 pixels for the active mode |
| Roster box | interior `(192, 8) - (311, 55)` | cols 24..38, rows 1..6 | six party rows (`stats-panel.md`) |
| Upper divider band | `(192, 57) - (312, 62)` visible | row 7 | timed-magic-effect slot (`stats-panel.md`) |
| Counters box | interior `(192, 64) - (311, 79)` | cols 24..38, rows 8..9 | food/gold and date rows (`stats-panel.md`) |
| Lower divider band | `(192, 81) - (312, 86)` visible | row 10 | plain chrome |
| Message window | `(192, 88) - (319, 191)` | cols 24..39, rows 11..23 | command echo, output, and the live input line (`text-output.md`) |
| Bottom gutter | `(0, 192) - (319, 199)` | row 24 | always black |

The chrome ribbons carry three label gaps that other systems paint into: the
sky strip in the top ribbon (`moons.md`), the wind banner in the bottom ribbon
(`weather.md`), and the timed-effect slot in the upper stats divider band
(`stats-panel.md`). Each of those is bracketed by the end-cap described next.

#### Bracket end-caps

Every interruption in the chrome — the sky strip, the wind banner, the
timed-effect slot, the stats-window label strip, and the message window's
command-echo prompt — is framed by the same pair of triangular caps. This is
the single most reused piece of chrome on the screen, and it is **not stored
art**: no matching bitmap exists in the shipped fonts, the shared data overlay,
or the display drivers. It is composited at draw time from a glyph and two
strokes, at the active text window's current cursor cell:

1. Save the active window's colour attribute; set the text foreground to the
   chrome colour and the text background to black.
2. Emit one opaque 8-by-8 fixed-cell glyph at the cursor. The right-pointing
   cap uses `IBM.CH` glyph code `0x02`; the left-pointing cap uses code `0x01`.
   Both are solid triangles in that font.
3. Set the pen to the accent colour and stroke two straight lines along the
   triangle's hypotenuse. With `(px, py)` the cell's top-left pixel, the
   right-pointing cap strokes `(px, py)` → `(px + 5, py + 3)` and
   `(px + 5, py + 4)` → `(px, py + 7)`; the left-pointing cap strokes
   `(px + 7, py)` → `(px + 2, py + 3)` and `(px + 2, py + 4)` →
   `(px + 7, py + 7)`.
4. Restore the saved colour attribute.

The cursor advances one cell, exactly as for an ordinary glyph.

Two consequences are worth stating because they are visible and easy to get
wrong. First, the union of the cap's chrome-coloured pixels and its
accent-coloured pixels is exactly the source triangle glyph, and the
chrome-coloured component alone is that triangle with its diagonal traced away
— which is why searching the shipped assets for either colour component finds
nothing. Second, both strokes terminate on the cell's outer column at its top
and bottom rows, which are the same rows the adjoining ribbon rules occupy. The
rule therefore appears to run continuously into the cap, and the measurable gap
in the rule stops one pixel short of the cap cell at each end. For the two
viewport-ribbon labels that produces the rule gaps `y = 7` broken over
`x = 41..150` and `y = 184` broken over `x = 49..150`.

#### Repaintable chrome regions

Four small helpers repaint a chrome region back to its plain state when the
label that occupied it goes away. They are published because their extents are
one pixel different from the corresponding frame rectangles, and matching them
matters for pixel comparison:

| Region | Repaint |
|---|---|
| Sky-strip gap (top ribbon) | fill `(40, 0) - (152, 6)` in chrome, then stroke the rule `(40, 7)` → `(152, 7)` in accent |
| Wind-banner gap (bottom ribbon) | stroke the rule `(48, 184)` → `(152, 184)` in accent, then fill `(48, 185) - (152, 191)` in chrome |
| Upper stats divider band | fill `(191, 57) - (312, 62)` in chrome, then stroke single scanlines `(192, 56) - (311, 56)` and `(192, 63) - (311, 63)` in accent |
| Stats-window label strip (top ribbon, right of the divider) | fill `(192, 0) - (311, 6)` in chrome, then stroke the single scanline `(192, 7) - (311, 7)` in accent |

The dungeon view blanks both viewport-ribbon gaps with its own pair of fills
before writing its own labels: `(40, 0) - (152, 7)` and `(48, 185) - (152, 191)`
in chrome, followed by the two rules `(40, 7)` → `(152, 7)` and
`(48, 184)` → `(152, 184)` in accent.

#### Primitive requirements

The frame relies on four display-layer behaviours that a cleanroom renderer
must match:

- **Filled rectangles are inclusive on all four edges** and are normalised and
  clamped to the screen before drawing, so either corner order is accepted.
- **The single-scanline fill and the rectangle fill are distinct operations.**
  The single-scanline entry takes one row coordinate and has no row loop; see
  `display-driver-abi.md` section 5.
- **Lines include both endpoints** and cover all eight octants; a polyline is a
  first line followed by continuation strokes from the current point.
- **The message-window scroll is hardwired.** On the EGA baseline the scroll
  entry accepts only the message window's left pixel column, moves a
  128-pixel-wide stripe up by exactly one 8-pixel cell row, and ignores any
  requested distance. A portable engine may generalise it, but must not assume
  the original honours a row count; see `display-driver-abi.md` section 9.5.

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

Frame `N` is sourced from hidden-surface row `50 x N`, which is where the
loader staged archive record `N + 1`, so the slot-to-frame mapping is ascending
and one-to-one: record `1` is frame `0` through record `4` is frame `3`. The
counter is **driver state, not screen state**. It starts at zero when the driver
is loaded, is advanced by every tick from any caller, and is never reset by a
start/menu redraw, a menu repaint, or a subflow return. A renderer must model it
as one long-lived counter; in particular, on the animated start path the
subtitle ignition entry below has already ticked it many times before the menu
is first polled, so the menu does not begin at frame `0`.

**The tick entry's second form.** The same entry has a second behaviour selected
by its carry flag on entry. With carry set, and a loaded one-bit-per-pixel
resource segment supplied, it is not a single frame advance at all: it saves the
whole hidden surface aside, blanks it, and runs a two-pass masked pseudo-random
reveal that restores the saved pixels into all four staged bands at once,
publishing the current band and advancing the frame counter every 128 restored
positions (256 below the calibration baseline), then restores the saved hidden
surface and releases its scratch storage. The pass structure, the mask polarity,
the speaker effect and the abort rule are specified in `intro.md` section 5
under "Subtitle ignition". Only the carry-clear form is the public frame
advance.

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
`(8, 128)..(311, 191)`. The strip is **nineteen cells across by four down**; a
reader that transposes it computes an impossible 64-by-304 preview. The five
fixed wipe rectangles are absolute framebuffer pixel rectangles on that same
page. Nothing about the preview is scaled, cropped, or drawn through a private
miniature raster.

Two further display-side rules the preview depends on:

- **No clear, no full repaint.** Each preview tick repaints only the cells
  inside the currently revealed column span, and skips cells that a cell-effect
  command has marked as owned by another entry. Everything else on the page,
  inside and outside the strip, is left alone. This is cell-granular painting
  over preserved backing, not a dirty-rectangle system and not a full redraw.
- **The strip reveals from its centre column outward.** A strip load resets a
  repaint cursor to column 9 only; it widens by one column on each side on every
  second preview tick and reaches the full span after eighteen ticks. The
  planes are filled immediately by the load, so this is purely a painting-order
  contract for the display layer.

The preview also uses two driver entries besides the tile blitter: the
animated-terrain shimmer entry, driven directly on one preview cell with a step
value for the local cell effect, and the pixel-dissolve entry's single-cell
sub-entry for the temporary actor draws. Both are specified in
`display-driver-abi.md` sections 9.6 and 10.

**Surface targeting of the filled-rectangle entry.** The driver's clipped
filled-rectangle operation honours the screen descriptor's render-target
selector and fills whichever surface that selector currently names. Any
statement that it is visible-page-only is withdrawn. The intro depends on this:
the text system's window-clear control is implemented as a filled rectangle, and
the intro uses it against the hidden surface to blank the flourish stack before
the ornament phase, to blank the hidden surface before the four subtitle bands
are staged, and again to blank the menu window's interior. A renderer that makes
the fill a no-op on the hidden surface cannot reach the documented frames.

**Ink of the flourish, stated once.** The publisher-flourish playback entry
(`display-driver-abi.md` section 10) is the only publisher in the whole intro
that does not move all four colour planes. It holds a two-plane write mask for
its entire run and copies a single plane of the composed image, which is why the
publisher wordmark arrives on screen as palette index `9` while every other
title phase — published by all-plane surface or rectangle copies — arrives as
index `15`. That is the entry's own contract and is not restated here, so the
two documents cannot drift.

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
- Preserve the original asset-depth selection rule exactly as section 2 states
  it: the high-colour `.16` family for EGA **and Tandy**, the low-colour `.4`
  family for CGA **and Hercules**. The split follows colour depth, not
  resolution. A v1 engine that ships EGA only always uses the `.16` family.
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
- **Story rectangle-transition helper.** Closed for the intro and the endgame.
  Fixed title artwork placement, menu idle ticking, story-art selection, story
  primary placement, and the step-1 story transition are specified in
  `intro.md`; the step-1 effect is the rectangle dissolve, not a column wipe. A
  focused intro slide-loop caller census found no step-2 or later story-page
  transition table. The start/menu loader's optional reveal is specified in
  section 8 above.
  **Correction.** An earlier revision of this bullet said the late endgame
  rectangle "turned out to be an opaque fill of the hidden surface with no
  visible effect". That is withdrawn. The fill is real, but it is immediately
  followed by a full-screen rectangle dissolve issued from the next routine, so
  the beat is a visible full-screen fade to black; see `endgame.md` section
  7.1. A whole-program census of the dissolve entry now lists all six of its
  call sites in `display-driver-abi.md` section 9.6. Three of them — two in the
  Blackthorn audience/rescue scene and one on the search/open command path, all
  over the `(8, 8)..(183, 183)` map viewport — are still unspecified in their
  own system docs, and remain open work outside this document.
- **Return-to-View resident helper internals.** Closed. The script-level
  command schedule, rectangle coordinates, actor draw ordering, preview tick
  counts, framebuffer geometry, repaint policy, and column reveal are specified
  in `formats/location-dat.md` section 11 and `intro.md` section 12, and the
  three driver entries involved are ordinary published ones. The only residual
  is the shimmer entry's exact per-step pixel pattern, which falls under the
  alternate-hardware and exact-raster parity item rather than under
  Return-to-View. The "short fixed wait" after the fixed wipe was a misreading
  of a speaker call and is withdrawn.
- **Which entry paths repaint the game-screen frame.** The frame's geometry,
  paint order, colours, and independence from gameplay state are now fully
  specified in section 7, and the intro's Journey Onward path is a confirmed
  painter. Whether each mode-loop entry repaints the frame itself on every
  transition, or whether it persists once painted, has not been traced
  exhaustively. Because the paint is deterministic, repainting more often than
  the original is visually indistinguishable except for the cost of the redraw.
  The labels that sit inside the frame's chrome gaps have their own, separately
  specified cadences (`moons.md`, `weather.md`, `stats-panel.md`).

- **Bracket end-cap art.** Closed. The caps are a two-pass composite of a font
  glyph and two accent strokes, specified in section 7. Searching the shipped
  fonts, the shared data overlay, or the driver binaries for either colour
  component of the cap will not find it, because neither component is stored
  art. No authored replacement sprite is required.

- **Alternate hardware parity.** CGA, Hercules, and Tandy conversion details
  are outside the v1 baseline unless a later implementation targets those modes
  explicitly.

## 11. Sources

This spec is a cleanroom prose rewrite from private analysis notes. It omits
assembly, decompiled code, raw jump tables, driver binary bytes, and private
addresses.

- Driver selection and load sequence:
  `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- The title-tick entry's slot-to-frame mapping and free-running counter, its
  carry-set two-pass masked band reveal, the filled-rectangle entry's honouring
  of the descriptor render target, and the single-plane masked publish that
  gives the publisher flourish its own ink:
  `u5-decomp/notes/intro_title_sequence_2026-08-22.md` and
  `u5-decomp/notes/title_flourish_presenter_verification_2026-08-22.md`.
- Shared game-screen frame — zone layout, deterministic paint, absence of any
  gameplay-state dependency, and the correction that the frame is common to all
  gameplay modes rather than combat-specific:
  `u5-decomp/functions/ULTIMA_EXE/0x637E_combat_screen_layout.md` (the note file
  keeps its original filename; its contents were corrected on 2026-05-24) and
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Source provenance: the frame's three-phase paint order, the eight filled
  rectangles, the three rounded-corner glyph cells, the four rule polylines, the
  filled-versus-visible overpaint relationship, the two chrome pens and their
  place in the user-interface colour table, the bracket end-cap composite, and
  the four chrome-repaint regions are derived from private analysis note
  `../u5-decomp/notes/gameplay_screen_layout_2026-08-22.md`, cross-checked
  against a fresh local re-read of the shipped executable and shared data
  overlay.
- EGA dispatch ABI, slot inventory, rectangle fill, packed-to-planar archive
  preparation, 16-by-16 tile blit, and 8-by-8 glyph blit:
  `u5-decomp/formats/ega-driver.md` and the `u5-decomp/functions/EGA_DRV/`
  notes.
- Driver-to-asset-family selection, the two user-interface colour sets, the
  per-driver framebuffer shapes, the per-driver title-band geometry, and the
  status of the packed-to-planar preparation entry in each family:
  `u5-decomp/notes/driver_asset_family_and_ui_colours_2026-08-22.md`,
  `u5-decomp/formats/cga-driver.md`, `u5-decomp/formats/tandy-driver.md`,
  `u5-decomp/formats/hercules-driver.md`, and
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
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
- Return-to-View strip orientation, framebuffer origin and cell size, per-tick
  repaint policy, and centre-outward column reveal:
  `u5-decomp/notes/rtv_preview_pixel_geometry_2026-08-22.md` and
  `u5-decomp/notes/rtv_command_schedule_and_reveal_2026-08-22.md`.
- Rectangle-dissolve abort gate and its speaker effect:
  `u5-decomp/notes/rect_dissolve_abort_and_sound_2026-08-22.md`.
- Whole-program rectangle-dissolve caller census, the separation of the entry's
  two carry paths, the fill-then-dissolve fade idiom, and the correction that
  the clipped rectangle fill is render-target aware:
  `u5-decomp/notes/dissolve_entry_caller_census_2026-08-22.md`.
