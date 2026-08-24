# Intro

## 1. Overview

The intro system is Ultima V's startup-facing mode. It is responsible for the work that happens after the resident executable has parsed its command-line display option and before the first gameplay mode is entered: hardware and driver setup, title-screen presentation, the Lord British signature animation, the six-option intro menu, the story slide show, the acknowledgement screen, and the entry paths for loading, creating, or transferring a game.

The intro is not a gameplay mode in the same sense as overworld, town, dungeon, or combat. It is a boot and menu overlay. While it is active, the engine uses a private intro scene state and stays inside the title/menu loop. When a player selects Journey Onward and the load succeeds, the intro updates the resident scene state and returns to the main loop. Character creation and Ultima IV transfer can produce new saves, but they return to the intro menu rather than entering gameplay directly. The main loop dispatches to the appropriate gameplay mode using the same scene-byte rules described in `main-loop.md`.

The original code keeps the intro in an overlay because it is large, graphics-heavy, and needed only at the start of a session. A modern implementation can treat it as an ordinary application state, but it should preserve the same externally visible flow:

- boot-time display and input initialisation happens before any title/menu input is accepted;
- the title art is shown before the menu;
- the Lord British path animation is skippable by keyboard input;
- the six intro-menu keys are accepted case-insensitively;
- non-load menu paths return to the menu;
- the Journey Onward load path hands control back to the main loop rather than
  running a gameplay loop inline.

## 2. Entry from the main loop

The resident executable performs only a thin first layer of boot work. It records the display-driver request from the command line, captures DOS/disk-swap state, primes a few input flags, and then calls the intro overlay. The boot contract in `boot.md` owns the machine/display probe and initialization boundary; this intro spec owns the title/menu behaviour that follows. The intro overlay performs the heavier system setup:

1. Detect the machine/display environment and reconcile it with the user's requested display driver.
2. Install the process-level interrupt and critical-error handling used by disk-swap prompts and safe aborts.
3. Initialise the text-window descriptor table used by all later text output.
4. Install the timer-tick hook used by cursor and animation timing.
5. Load the selected display driver.
6. Switch into the initial graphics mode.
7. Select the graphics asset depth used by title and story screens.

The depth selection chooses between the paired high-colour and low-colour graphics asset families. The intro uses the same rule as the rest of the engine: once the display driver has been selected, every screen-art filename is resolved to the matching depth and stays consistent for the session. See `formats/tiles.md` for the paired screen-panel asset format and `text-output.md` for the boot-time text-window setup this flow enables.

On old hardware, one display case can be downgraded to a simpler driver if the detected memory is too small. This is a boot compatibility fallback, not a user-visible option once the menu is drawn.

## 3. Title-screen construction

After boot setup, the intro builds the title presentation in ordered phases:

1. Clear and configure the full-screen text/graphics surface.
2. Prepare the intro text pipeline by loading the IBM and rune glyph
   assets, activating the IBM glyph asset, configuring the full-screen
   text window, selecting the active display-driver descriptor, and
   polling once for the early Journey Onward shortcut. This phase
   does not draw any text or runes; it only readies the fonts and
   checks for a queued `J` keypress.
3. Load the title and Lord British artwork resources.
4. Run the seven-step initial title-mark helper for `TITLE.BIT` slots `0..6`.
5. Draw the later title overlays around the signature phase in the order
   specified below.
6. Play the `BRITISH.PTH` signature animation over the title screen unless
   the player skips it.
7. Load and draw the start/menu screen used behind the six menu options.

The intro uses two different graphics-resource families. Screen-panel assets
such as `ULTIMA`, `STARTSC` and `STORY1` through `STORY6` use the paired
`.16`/`.4` packed-4bpp archive family. `TITLE.BIT`, `BRITISH.BIT`, and `WD.BIT`
are one-bit-per-pixel record archives handled by the driver's silhouette-stamp
entry. Both families share the same outer LZW envelope with the single
exception of `WD.BIT`, which ships uncompressed. The intro orchestrates file
selection, loading, placement, and draw calls; the data formats themselves
belong to `formats/bit.md`, `formats/tiles.md`, and the display-driver layer.

### Visible phase order

The construction list above is the intro's internal work order. What the player
actually sees, from launch to a settled menu, is the six-phase sequence below.
Each phase owns the screen exclusively until it ends or a keystroke interrupts
it. "Ink" is the palette index the pixels have **on the visible page**, which
for the publisher flourish is not the index the artwork was composed at — see
the two-surface discussion later in this section.

| # | Visible phase | Ink | What is on screen at the end of the phase | Pacing |
|---:|---|---:|---|---|
| 1 | Publisher flourish | `9` (bright blue) | the publisher wordmark, zoomed up through seven nested sizes, resting as the `280 x 61` mark at `(20, 46)` | 85 presentation steps, each one CPU-calibrated busy wait inside the driver; no timer tick at all |
| 2 | `Presents` | `15` (white), over the still-blue mark | the blue publisher mark **plus** the white `Presents` wordmark at `(108, 140)` | eighteen timer ticks, then a bounded poll of up to twenty more |
| 3 | The `a` ornament | `15` | a black screen carrying only the `16 x 15` ornament at `(152, 0)` | bounded poll of up to twenty ticks |
| 4 | Signature stroking | `15` | the ornament plus the `Lord British` signature being pen-drawn stroke by stroke | one timer tick per thirty-two path bytes, with the slow-CPU skip suppressed |
| 5 | Finished composition | `15` | the ornament at `(152, 0)`, the finished signature at `(24, 66)`, `Production` at `(104, 160)` | two publishes, then a bounded poll of up to twenty ticks |
| 6 | Start screen and menu | artwork palette | the `Ultima V` logo on rows `0..60`, the burning subtitle band on rows `65..113`, the menu window on rows `120..199` | see "Start/menu screen composition" below and section 5 |

Four properties of that list are load-bearing and were previously mis-stated:

- **The publisher flourish always runs.** There is no display-mode branch, no
  driver-capability branch and no slow-CPU short-circuit that skips it. The only
  way to miss it is the early `J` shortcut of the pre-flourish phase, which
  leaves the title sequence entirely. It is, however, *fast*: because it is
  paced by a calibrated busy loop with no timer floor, it can finish in well
  under a second on a quick host, and together with phase 2 the whole publisher
  block can fall between two samples of a two-second capture grid. Absence from
  a coarse capture is not evidence that it does not render.
- **Phase 2 is deliberately two-coloured.** The `Presents` publish is an
  ordinary all-plane rectangle copy of the lower band only, so the publisher
  mark above it survives *in its own ink*. The frame therefore carries a blue
  mark over white lettering. A renderer that draws both in one colour does not
  match.
- **The intro's ink is never yellow.** Phases 2 through 5 — the ornament, the
  live pen strokes, the finished signature bitmap, `Presents` and `Production` —
  are all palette index `15`, plain white. Phase 1 alone is index `9`. Nothing
  in the intro reprograms the palette registers, so these are the stock EGA
  colours for those indices. Any description of the title ink as a pale or light
  yellow, or as a distinct "signature colour", is withdrawn; a yellow cast in a
  capture comes from the host's scaler or colour management, not from the game.
- **One keystroke collapses the rest.** The abort contract is stated once, for
  the whole list, under "Keystroke abort" below.

### Pre-flourish phase (step 2)

The pre-flourish phase is a non-visual preparation pass. The intro
performs the following actions in order; none of them draw text,
runes, or other glyphs to the screen, and no portion of the display
surface is changed by this phase beyond the descriptor and active-font
bookkeeping described below:

1. Probe the loaded display driver for an "intro-ready" status. If
   the driver returns a zero status, the intro aborts: it restores
   the BIOS video mode that was captured before driver setup and
   terminates the program with exit code 1. This is a hard
   boot-failure path; a clean implementation that does not reuse the
   original driver dispatch can either omit this probe or replace it
   with an equivalent "display backend ready" assertion.
2. Load two bitmap-font assets into the resident font slot table:
   slot 0 receives the normal IBM-style glyph set used for ordinary
   intro and menu text; slot 1 receives the Britannian runic glyph
   set, kept resident for later activation when rune-styled text is
   required. The asset filenames differ only by driver:

   | Driver | IBM slot file | Rune slot file |
   |---|---|---|
   | EGA | `IBM.CH` | `RUNES.CH` |
   | CGA | `IBM.CH` | `RUNES.CH` |
   | Tandy | `IBM.CH` | `RUNES.CH` |
   | Hercules | `IBM.HCS` | `RUNES.HCS` |

   The pair-by-driver distinction is purely an asset-format choice:
   the `.CH` files are the 8×8 IBM-PC bitmap form used by the
   colour drivers; the `.HCS` files are the high-resolution monochrome
   form used by the Hercules driver. The loader is a generic "open,
   size, allocate, read" sequence; each load retries only when the
   file read returns zero bytes, and a non-zero return (success or a
   sentinel error) exits the retry. A clean v1 implementation that
   ships a single EGA-compatible bitmap font may load the EGA pair
   unconditionally; the driver-specific asset distinction is
   historical-parity work for the alternate display drivers.
3. Activate font slot 0 as the current glyph source so that any
   later intro text (e.g. the Journey Onward shortcut message in
   step 5, the start/menu labels in section 6) is drawn through the
   IBM glyph set by default. Slot 1 remains loaded and is reachable
   later through the same active-font selector when the rune glyph
   set is needed.
4. Reset the primary text-window descriptor to the full 40-column by
   25-row text-cell rectangle covering the entire screen. This
   establishes the print/cursor bounds for any subsequent
   text-window output in the intro.
5. Select display-driver descriptor index 0 as the active driver
   descriptor. This is the configuration bookkeeping step that
   publishes the descriptor's per-driver flags (column width, text
   foreground/background, centre-output gate) to the resident text
   primitives. It does not change the BIOS video mode.
6. Perform exactly one non-blocking keyboard poll, fold the returned
   byte to uppercase, and compare it to `J`. If a key was queued
   before this poll (typically because the player pressed `J`
   while the boot was still proceeding) and the key folds to `J`,
   the intro takes the early Journey Onward shortcut: it prints
   "Journey Onward" centered in the cleared text window, transitions
   the intro scene state to the post-menu transition state, and
   jumps directly to the Journey Onward load handler in section 7.
   For any other key, or no key, the intro falls through to step 3
   of the outer phase list (title and Lord British resource loads).

The early `J` shortcut is therefore accepted at exactly this single
poll, not throughout the flourish. The TITLE.BIT flourish in steps
4–5 and the `BRITISH.PTH` animation in step 6 can be interrupted by
any keystroke, but those interruptions proceed to the start/menu
screen, not to the Journey Onward load. The two paths are distinct:
the pre-flourish poll commits the load, while later flourish
keystrokes only skip the visual flourish.

This phase never draws to the display surface, so no pixels from it
persist into the TITLE.BIT flourish. The flourish loader stamps its
source surface and draws its visible frames over whatever the boot
setup and the preceding clear left on the screen. A clean
implementation may therefore implement step 2 as a pure preparation
pass with no rendering and no clearing beyond what step 1 already
performed.

The fixed title-screen bitmap placements use 320-by-200 pixel coordinates with
the origin at the upper-left corner. `TITLE.BIT` slots `0..6` form the initial
title-mark flourish, but the source placement and the visible placement are
different.

The resident title helper first builds a hidden source surface. It stamps
`TITLE.BIT` slots `0..6` in ascending order into that hidden surface, centered
horizontally, starting at hidden `y = 0`, and advancing hidden `y` by the drawn
slot's height before stamping the next slot. That hidden stack is only an
animation source. It must not be rendered directly to the visible title page.

| `TITLE.BIT` slot | Top-left X | Top-left Y | Size |
|---:|---:|---:|---|
| 0 | 148 | 0 | 24 x 3 |
| 1 | 140 | 3 | 40 x 7 |
| 2 | 124 | 10 | 72 x 11 |
| 3 | 104 | 21 | 112 x 20 |
| 4 | 84 | 41 | 152 x 32 |
| 5 | 52 | 73 | 216 x 45 |
| 6 | 20 | 118 | 280 x 61 |

The visible flourish then presents those hidden source rows through the EGA
driver's title animation player. The visible frame for each slot is centered at
the following destination, replacing the previous visible flourish frame rather
than accumulating on top of it:

| `TITLE.BIT` slot | Hidden source Y | Visible top-left X | Visible top-left Y | Size |
|---:|---:|---:|---:|---|
| 0 | 0 | 148 | 75 | 24 x 3 |
| 1 | 3 | 140 | 72 | 40 x 7 |
| 2 | 10 | 124 | 71 | 72 x 11 |
| 3 | 21 | 104 | 66 | 112 x 20 |
| 4 | 41 | 84 | 60 | 152 x 32 |
| 5 | 73 | 52 | 53 | 216 x 45 |
| 6 | 118 | 20 | 46 | 280 x 61 |

For a clean renderer, the compatibility rule is: show slot `0`, then replace
it with slot `1`, then replace that with slot `2`, continuing through slot
`6`. Clear the prior visible flourish area as needed so earlier slots do not
remain visible. The completed title flourish is a single coherent slot `6`
publisher wordmark at `(20, 46)`, not seven stacked copies of it. The seven
records are the same artwork at seven sizes, which is exactly why drawing them
all at once looks like a pile of nested duplicates.

#### Flourish playback: seven frames, seven reveal steps, six erase steps

The flourish is played by the display driver's animation-script entry, not by
the title tick. The intro helper stamps the seven marks into the hidden surface,
switches the render target back to the visible page, and makes exactly one call
into the driver; the driver then owns the whole flourish until it finishes or a
keystroke aborts it. The pacing unit is the driver's CPU-calibrated busy wait,
one wait per presentation step — see `timing.md` section 5.1.

The script is a fixed seven-frame program. Each frame names the hidden source
row it starts from, the visible destination row its band starts at, and the
band's height. The source rows and heights repeat the hidden-stack table above;
the destination rows are the flourish's own vertical drift.

| Frame (`TITLE.BIT` slot) | Hidden source top row | Visible band top row | Band height |
|---:|---:|---:|---:|
| 0 | 0 | 75 | 3 |
| 1 | 3 | 72 | 7 |
| 2 | 10 | 71 | 11 |
| 3 | 21 | 66 | 20 |
| 4 | 41 | 60 | 32 |
| 5 | 73 | 53 | 45 |
| 6 | 118 | 46 | 61 |

Each frame carries seven **reveal steps**. A step adds a fixed set of that
frame's own source rows to the visible set — row numbers are relative to the
frame's own top row, not to the screen — and then presents. Steps whose set is
empty are timing-only steps that repaint the same image. The sets are
cumulative within a frame: step `k` shows the union of the sets from steps `1`
through `k`.

| Frame | Reveal 1 | Reveal 2 | Reveal 3 | Reveal 4 | Reveal 5 | Reveal 6 | Reveal 7 |
|---:|---|---|---|---|---|---|---|
| 0 | `0, 2` | — | — | — | `1` | — | — |
| 1 | `0, 6` | `3` | — | `2, 4` | — | `1, 5` | — |
| 2 | `0, 10` | `5` | `4, 6` | `1, 9` | `3, 7` | `2, 8` | — |
| 3 | `0, 19` | `9, 10` | `3, 6, 13, 16` | `2, 8, 11, 17` | `5, 14` | `1, 7, 12, 18` | `4, 15` |
| 4 | `0, 31` | `5, 10, 15, 16, 21, 26` | `4, 9, 14, 17, 22, 27` | `1, 6, 11, 20, 25, 30` | `3, 8, 13, 18, 23, 28` | `2, 12, 19, 29` | `7, 24` |
| 5 | `0, 44` | `7, 14, 21, 23, 30, 37` | `2, 5, 9, 12, 16, 19, 25, 28, 32, 35, 39, 42` | `3, 10, 17, 22, 27, 34, 41` | `6, 13, 20, 24, 31, 38` | `1, 8, 15, 19, 36, 43` | `4, 11, 18, 26, 33, 40` |
| 6 | `0, 60` | `30, 40, 50, 20, 10` | `25, 15, 5, 35, 45, 55` | `27, 22, 17, 12, 7, 2, 33, 38, 43, 48, 53, 58` | `29, 24, 19, 14, 9, 4, 31, 36, 41, 46, 51, 56` | `26, 21, 16, 11, 6, 1, 34, 39, 44, 49, 54, 59` | `28, 23, 18, 13, 8, 3, 32, 37, 42, 47, 52, 57` |

Between two consecutive frames — that is, after frames `0` through `5`, but not
after frame `6` — the driver runs six **erase steps** on the frame just shown.
Erase step `j` removes the rows named in that frame's reveal column
`8 - j` and presents: erase 1 removes the reveal-7 set, erase 2 removes the
reveal-6 set, and so on down to erase 6 removing the reveal-2 set. The reveal-1
set (the frame's top and bottom rows) is never erased; it is discarded when the
next frame resets the visible set to empty. The flourish therefore runs
`7 x 7 = 49` reveal steps plus `6 x 6 = 36` erase steps, **85 presentation
steps in total**.

Two data quirks in the shipped script are part of the contract:

- The reveal sets for frame `5` name source row `19` twice (in reveal 3 and
  reveal 6) and never name source row `29`. Row `29` of that 45-row mark is
  therefore blank for the whole of frame `5`.
- Every other frame's reveal sets partition its rows exactly once.

Each presentation repaints the frame's whole band rather than drawing only the
newly added rows. The currently visible rows are drawn **packed contiguously
and centred vertically inside the band**, and the remaining band rows are
blanked. The centring rounds down at the top: if the frame currently hides `c`
of its rows, `floor(c / 2)` blank rows come first, then all currently visible
rows in ascending source order, then `ceil(c / 2)` blank rows. The three parts
always sum to the band height. The visible result is an expanding
venetian-blind reveal followed by the reverse collapse, not a simple row-by-row
wipe.

The fill runs top-down on even-numbered frames and bottom-up on odd-numbered
frames, and the two directions are not symmetric. On an odd frame the band is
written from its last row upward while the visible source rows are still taken
in ascending order, so an odd frame is drawn **vertically mirrored and shifted
one row down**: its band occupies `band top + 1` through
`band top + height` instead of `band top` through `band top + height - 1`.
Frames `1`, `3` and `5` are affected. Frame `6` — the one that leaves the
finished mark on the screen — is an even frame, so the finished mark is neither
mirrored nor shifted, and sits exactly at `(20, 46)`.

Rows are copied and blanked at the **full 320-pixel screen width**, not at the
mark's own width. The band a presentation owns is therefore the inclusive
rectangle `(0, band top)..(319, band top + height - 1)` on an even frame, or
that rectangle shifted one row down on an odd frame, and the mark's horizontal
position inside it is simply the centred X it was stamped at in the hidden
surface. A renderer that clips the repaint to the mark's width will leave stale
pixels beside it.

Because each frame's band is a different rectangle, the erase pass is what
removes the previous frame's pixels from the rows the next frame does not
cover. A renderer that skips the erase steps must clear the outgoing band
before drawing the incoming one.

**Keystroke abort.** The driver probes the keyboard once per repainted row, so
a keystroke can land in the middle of any presentation step. It does not leave
a half-built mark on the screen. The driver stops the script, sets every row of
frame `6` visible, forces the even-frame fill direction, and makes one final
presentation, so an aborted flourish ends on exactly the same image a completed
one does: the whole `280 x 61` mark at `(20, 46)`. It then reports the abort to
the intro.

That report is load-bearing, because it is also the intro's "player skipped the
title sequence" flag. When the flourish is aborted:

- the lower-band clear and the slot `7` draw described below still happen and
  are still published, so `Presents` is briefly visible either way;
- everything after that is skipped. The slot `8` ornament, the whole
  `BRITISH.PTH` signature animation, the `BRITISH.BIT` signature and the slot
  `9` line are not drawn at all, and the intro goes straight to the start/menu
  screen load;
- the automatic Return-to-View preview that normally runs once after the
  start/menu screen is drawn is also suppressed.

The same flag is carried forward by the later phases: a key during the hold
after slot `7` skips from there, and a key during the signature strokes
abandons the remaining stroke segments but still draws `BRITISH.BIT` and slot
`9`. In every case the destination is the start/menu screen, and any skip
suppresses the Return-to-View preview.

The EGA baseline is not a normal white-on-black foreground blit. The helper
stamps 1-bit source pixels into the hidden driver surface, where they set every
colour plane; the animation player then reads a single plane of that surface
back and writes it to the visible page through a blue-plus-intensity write
mask. The net effect is that set source pixels appear as palette index `9` on
the black title background, and cleared ones as index `0`, for this initial
flourish only. There is no XOR, inverse, alpha, or source sub-rectangle mode
for slots `0..6`; each source slot is consumed from its own `(0, 0)` origin for
its full documented width and height before the driver presentation script
chooses which rows to show.

The later title overlays are a different colour for the same reason in reverse:
slots `7`, `8`, `9` and the `BRITISH.BIT` signature are stamped into the hidden
surface the same way but are published by whole-surface copies that carry every
plane, so they appear as palette index `15`. The signature pen strokes are
drawn directly at index `15` as well. Nothing in the intro reprograms the
palette registers, so all of these are the stock EGA colours for those indices:
the flourish is blue, everything after it is white.

The remaining title sequence uses four explicit overlay draws:

| Asset | Slot | Top-left X | Top-left Y | Size | Role |
|---|---:|---:|---:|---|---|
| `TITLE.BIT` | 7 | 108 | 140 | 104 x 33 | The word "Presents", under the finished publisher wordmark |
| `TITLE.BIT` | 8 | 152 | 0 | 16 x 15 | The article letter that opens the attribution card |
| `BRITISH.BIT` | 0 | 24 | 66 | 272 x 62 | The handwritten author signature, middle line of the card |
| `TITLE.BIT` | 9 | 104 | 160 | 112 x 33 | The word "Production", closing line of the card |

Slots `8`, `BRITISH.BIT` `0` and `9` are the three lines of one attribution
card and are meant to be seen together. Slot `7` belongs to the preceding
publisher card and is gone by the time the attribution card is complete.

Their draw order is part of the compatibility contract:

1. After the seven-step `TITLE.BIT` `0..6` flourish returns, clear the lower
   screen band from `y = 140` through the bottom of the 320-by-200 surface.
2. Draw `TITLE.BIT` slot `7` at `(108, 140)`.
3. Draw `TITLE.BIT` slot `8` at `(152, 0)`.
4. Draw the four `BRITISH.PTH` signature path segments, in order, from pen
   origins `(68, 44)`, `(94, 64)`, `(78, 143)`, and `(105, 167)`.
5. Draw `BRITISH.BIT` slot `0` at `(24, 66)`.
6. Draw `TITLE.BIT` slot `9` at `(104, 160)`.

#### Two surfaces and whole-page publishes

These four overlay draws are not painted straight onto the visible page. Each
one is stamped into the same hidden surface the flourish used, and the intro
then publishes the **entire** hidden surface over the **entire** visible page.
That is the mechanism behind the title sequence's scene changes, and a renderer
that draws the overlays directly onto the running image will get the wrong
picture. The precise sequence is:

1. After the flourish returns, clear the hidden surface's lower band from
   `y = 140` to `y = 199`, stamp `TITLE.BIT` slot `7` at `(108, 140)`, and
   publish **only the rectangle** `(0, 140)..(319, 199)`. The flourish's slot-6
   mark, which lives on the visible page above that band, is untouched, so the
   screen now reads as the finished mark plus the slot-7 line beneath it.
2. If the flourish was not skipped, hold that image briefly, then poll for a
   keystroke. If the flourish **was** skipped, or if this poll returns a key,
   the sequence ends here and the intro jumps straight to the start/menu screen
   load; steps 3 to 6 do not run at all.
3. Clear the whole hidden surface, stamp `TITLE.BIT` slot `8` at `(152, 0)`,
   and publish the whole surface. This is the point at which the title mark and
   the slot-7 line disappear: the visible page becomes black except for the
   small slot-8 ornament at the top.
4. Hold the slot-8 image briefly with a bounded keyboard poll, then draw the
   four `BRITISH.PTH` signature path segments, in order, from pen origins
   `(68, 44)`, `(94, 64)`, `(78, 143)`, and `(105, 167)`. These strokes are
   painted **directly onto the visible page**, over the slot-8 ornament, and are
   not stamped into the hidden surface. A key during the hold, or during any
   segment, abandons the remaining segments — but steps 5 and 6 still run, so
   the finished signature and the slot-9 line still appear.
5. Stamp `BRITISH.BIT` slot `0` at `(24, 66)` into the hidden surface and
   publish the whole surface. Because the hidden surface still holds only the
   slot-8 ornament plus the freshly stamped signature bitmap, this publish
   **replaces** the live pen strokes with the finished signature artwork. The
   strokes and the bitmap are never both visible.
6. Stamp `TITLE.BIT` slot `9` at `(104, 160)` into the hidden surface and
   publish the whole surface again.

`BRITISH.BIT` is therefore not a backing image under the live path strokes, and
the strokes are not drawn over `BRITISH.BIT`. The strokes are the animation;
the bitmap is the finished state that supersedes them. A clean renderer should
not draw `BRITISH.BIT` before `BRITISH.PTH` and then stroke on top of it.

The final title frame before the start/menu screen is drawn therefore contains
exactly three things: the small `TITLE.BIT` slot `8` ornament at `(152, 0)`, the
completed `BRITISH.BIT` signature at `(24, 66)`, and `TITLE.BIT` slot `9` at
`(104, 160)`. It does **not** still contain the slot-6 flourish mark or the
slot-7 line; those belonged to the earlier presentation and were cleared by the
whole-page publish in step 3. The subsequent start/menu screen load replaces
this frame in turn; it is not another transparent layer over it.

That is the unskipped ending. If the player pressed a key during the flourish
or during the step-2 hold, the last title image instead is the finished
flourish mark plus the slot-7 line, and the start/menu screen replaces *that*.
Either way the start/menu load begins by clearing the visible page, so no title
pixels survive into the menu.

Only these semantic title slots are visible. Do not render every decoded
resource record from `TITLE.BIT` or `BRITISH.BIT` as an independent visible
sprite, and do not draw the hidden slot `0..6` source stack directly to the
front page. Their visibility is controlled by the intro call sequence and
driver presentation rules above.

#### Start/menu screen composition

The start/menu surface is built from the `ULTIMA` banner archive — the same
paired `.16`/`.4` family member the boot depth rule resolves for the current
driver — after the title flourish and signature sequence end or are skipped. It
is **not** built from `STARTSC`. `STARTSC` is the acknowledgement-screen credits
card used by the `A` menu path (section 11); it plays no part in the start/menu
screen.

The `ULTIMA` archive holds five records:

| `ULTIMA` record | Role | Size |
|---:|---|---|
| 0 | "Ultima V" logo banner | 319 x 61 |
| 1 | Burning subtitle wordmark, animation phase 1 | 288 x 49 |
| 2 | Burning subtitle wordmark, animation phase 2 | 288 x 49 |
| 3 | Burning subtitle wordmark, animation phase 3 | 288 x 49 |
| 4 | Burning subtitle wordmark, animation phase 4 | 288 x 50 |

The loader runs the following sequence:

1. Load the `ULTIMA` archive, retrying until the load reports a nonzero
   segment. Force the intro scene state.
2. Select the visible page and clear it.
3. Select the hidden surface and draw record `0` at `(0, 0)`, opaque, no
   mirroring and no transparency mask.
4. Transfer the inclusive rectangle `(0, 0)..(319, 100)` from the hidden surface
   to the visible page. The animated caller path performs that transfer as a
   pseudo-random per-pixel dissolve (`display-driver-abi.md` section 9.6); the
   plain caller path copies the rectangle in one step. There is no per-column
   wipe on either path. The animated path then samples the keyboard once, and a
   keystroke downgrades the rest of the loader to the plain path.
5. Select the hidden surface, clear it, and draw records `1`, `2`, `3`, `4` at
   `(16, 0)`, `(16, 50)`, `(16, 100)`, `(16, 150)` respectively — opaque, no
   mirroring, no transparency mask. This lays out the four idle-animation bands
   the title tick consumes; see section 5.
6. Release the `ULTIMA` archive.
7. On the still-animated path only: load `WD.BIT`, run the driver's
   subtitle ignition transition with it, then release it. On the plain path this
   step is skipped entirely.
8. Select the visible page, run one title tick, and draw the lower intro text
   window over the bottom of the screen so the menu labels can be rendered into
   it. That step **draws** the window's frame band and inner rule; it is not a
   clear. Section 6.1 owns the full three-pass construction, including which
   pass clears the interior.

Whether the loader takes the animated or the plain path is decided by the same
"player skipped the title sequence" flag described in section 3: an unskipped
title sequence gets the animated path, and any earlier keystroke gets the plain
one. That flag has one further effect. Immediately after the loader returns, an
unskipped run plays the Return-to-View preview once, before the menu is polled
for the first time; a skipped run goes straight to the menu. Only this first
automatic showing is conditional — the two-hundred-pass idle timeout in section
6 and the explicit `R` command are unaffected.

The finished start/menu screen is therefore the `ULTIMA` record-0 logo occupying
rows `0..60`, the animated subtitle band at rows `65..113`, and the intro menu
text window below. The archive records do not contain the six menu labels; the
box/text-window pass in section 6 owns the bottom area and overwrites whatever
it covers.

## 4. `BRITISH.PTH` signature animation

`BRITISH.PTH` is a one-off path stream used only by the intro. The file stores small signed pen movements, not absolute coordinates and not NPC schedule data. The intro loads the whole path file into a scratch buffer, then calls a path walker four times. Each call starts from a fixed title-screen origin and consumes one segment of the path stream, so the four calls together draw the whole Lord British signature.

At each path step, the walker decodes one movement, advances the pen, and paints when the movement represents a pen-down stroke. Larger movement magnitudes act as short pen-up moves so the signature can jump across small gaps without drawing a connecting line. Segment terminators end the current walker call and return control to the intro, which restarts the next segment from its next fixed origin.

The animation is intentionally interruptible. The walker polls the keyboard between path steps, and any pending key aborts the remaining animation. The intro then continues to the same start/menu screen it would have reached after a complete animation. Skipping the animation does not skip boot initialisation, menu setup, or later load validation.

The path format, segmentation, and pen-up rule are specified in `formats/pth.md`. This system spec defines only how the intro uses that format: load once, draw four title-screen segments, poll for early exit, then continue to the menu.

## 5. Title Tick And Idle Animation

The title sequence has a small display-driver-owned tick distinct from the
gameplay world tick. It advances the driver's title/flame-style visual state
and presents the updated frame; it does not run gameplay animation, NPC
schedules, or the world clock.

The wall-clock cadence for every visible intro animation phase is specified
in `timing.md` section 5; this section gives the per-phase behaviour and
defers the unit, the catch-up policy, and the slow-CPU-gate handling to that
document. The title tick's own unit is one DOS BIOS user-tick (approximately
54.945 ms at the standard 18.2065 Hz rate), and the title-tick helper has that
one-tick wait built into its body. The `BRITISH.PTH` signature and the menu
idle pump inherit that unit.

The `TITLE.BIT` flourish does **not**. It is played entirely inside the display
driver's animation-script entry and is paced by that entry's CPU-calibrated
busy wait, one wait per presentation step, with no BIOS-tick involvement at
all. Any statement that the flourish advances one reveal group per title-tick
call, or that it runs at 18.2 Hz, is wrong. See `timing.md` section 5.1.

The title tick advances only at explicit intro/display call sites. The Lord
British signature path itself is paced by keyboard polling and real-time delay
ticks while it draws the path stream; those delay ticks do not advance the
four-frame title strip. A keypress stops the remaining signature strokes and
proceeds to the start/menu view; it does not skip boot setup or menu rendering.

Once the start/menu screen has been drawn, the loader runs one clear-carry
title tick before it redraws the lower intro text window and before the menu
labels are rendered. The finished menu then polls input in a bounded idle loop:
each no-key poll pass runs one clear-carry title tick, then polls again. If
two hundred consecutive no-key passes elapse, the menu commits the same path as
`R` Return to View. Each no-key pass costs two BIOS ticks, not one — the input
poll waits one and the title tick waits another — so the idle strip advances
roughly every 110 ms and the timeout fires after roughly 22 seconds of
unattended menu (`timing.md` section 5.1). This is why the menu remains visually
alive without advancing any saved-game state, and why the Return-to-View
preview can start after a long unattended menu idle.

The historical driver implements the title tick behind a display dispatch
rather than in `FLAMES.OVL`. The observed EGA/CGA/Hercules/Tandy paths use a
small four-frame counter. A modern renderer can implement the same visible
contract as a four-frame loop tied to the intro menu's idle cadence.

For the EGA-compatible baseline, one clear-carry title tick draws the current
frame strip over the start/menu screen at pixel `(0, 65)` with size
`320 x 49`, then advances the frame index modulo four. The covered destination
rows are `65..113` inclusive and the covered columns are `0..319` inclusive.
The first frame after driver initialisation is frame `0`; the frame index is
not reset merely because the start/menu screen is redrawn, a menu row is
re-highlighted, or a non-play submenu returns.

**Slot-to-frame order and starting frame.** The mapping is ascending and
one-to-one: `ULTIMA` record `1` is frame `0`, record `2` is frame `1`, record
`3` is frame `2`, record `4` is frame `3`. Frame `N` is sourced from hidden row
`50 x N`, which is exactly where record `N + 1` was staged, so the mapping is a
consequence of the staging layout rather than an independent convention. The
counter is zero when the driver image is loaded and the entry draws before it
advances, so the very first tick of a session shows record `1`.

That is *not* the same as saying the menu starts on record `1`. The counter is
**free-running driver state**: nothing in the intro resets it, and the subtitle
ignition transition on the animated path ticks it many times before the menu is
ever polled. On an animated start the first menu-idle frame is therefore
wherever the counter happened to land, and on a skipped start it is frame `1`
(the loader runs exactly one tick after staging, which shows frame `0` and
leaves the counter at `1`). An engine must model the index as a single
long-lived counter, not as "restart at zero for each screen". The one place the
band's contents are decoupled from the counter is the return from
Acknowledgements, which repaints the band statically from record `1` while the
counter keeps its own position (section 11.2, step 6).

#### The four frames are shipped art, not driver-internal pixels

Earlier revisions of this section said the frame pixels are produced at runtime
by the display driver, that no external asset contains them, and that a clean
engine must author replacement art. **That was wrong and is withdrawn.**

The frames are records `1`, `2`, `3` and `4` of the `ULTIMA` banner archive —
the same paired `.16`/`.4` file the start/menu loader has already opened. They
are ordinary packed-4bpp records in the family described by `formats/tiles.md`:

| `ULTIMA` record | Size | Role |
|---:|---|---|
| 1 | 288 x 49 | Idle frame `0` |
| 2 | 288 x 49 | Idle frame `1` |
| 3 | 288 x 49 | Idle frame `2` |
| 4 | 288 x 50 | Idle frame `3`; only its upper 49 rows are ever shown |

The reason the pixels appear to come from nowhere is the staging step. Before
the menu is drawn, the loader clears the driver's hidden surface and draws
those four records into it at `(16, 0)`, `(16, 50)`, `(16, 100)` and
`(16, 150)` — a 50-row band pitch. The tick then copies the **full 320-pixel
width** of 49 rows starting at hidden row `50 x frame_index` onto visible rows
`65..113`. Because the art is 288 pixels wide and drawn at `x = 16`, the
16 columns at each end of every band come from the clear, not from the art, and
are therefore background-coloured.

A clean engine has two equivalent ways to satisfy this contract:

1. **Direct.** Decode `ULTIMA` records `1..4`, composite each one onto a
   `320 x 49` background-filled canvas at `x = 16` (records `1..3` use all 49
   rows; record `4` contributes its first 49 rows), and blit the selected canvas
   to `(0, 65)` on each tick.
2. **Faithful.** Reproduce the staging surface literally: a `320 x 200`
   offscreen buffer, cleared, with the four records drawn at the band origins
   above, and a tick that copies rows `50 x frame_index .. 50 x frame_index + 48`
   at full width to visible rows `65..113`.

Both produce identical pixels. No authored replacement art, no driver-binary
reuse, and no captured screenshots are required, and there is no
"title-tick frame offset" inside the driver file to locate — the earlier
suggestion of a locator-from-driver-file approach was based on the withdrawn
claim and should be removed from any implementation.

The tick is still an opaque full-rectangle overwrite. Every tick replaces all
`320 x 49` pixels of the destination, including background-coloured ones. There
is no transparency key, no alpha, no mask, no scaling, no cropping and no
dithering, and the tick never preserves what was previously inside the
rectangle. Where issue `#52` described this overlay as a sparse overlay that
leaves surrounding pixels alone, that description is superseded: the surrounding
pixels inside the rectangle are overwritten with the band's background, and only
pixels outside the rectangle are preserved.

A static placeholder can be useful during development, but it is a
lower-fidelity fallback rather than the specified idle animation, and it is no
longer necessary now that the source records are identified.

Stated as a contract: the renderer keeps one frame index, initialised to `0`
when the intro renderer is created and never reset by anything the menu does.
Each clear-carry title tick draws the frame that index currently names across
columns `0..319` of rows `65..113`, and only then increments the index modulo
four. Drawing before advancing is the part that matters — the first tick after
initialisation shows frame `0`, not frame `1`.

The frames use the active 16-colour EGA-compatible palette indices directly.
Do not alpha-blend, scale, dither against the previous screen, or treat any
palette index as transparent. Palette index `0` pixels overwrite the
destination as black.

#### Subtitle ignition: the two-pass masked band reveal

The carry-set title helper is a different operation and is not the public
frame-advance. It takes a loaded one-bit-per-pixel resource as its argument and
plays the subtitle ignition transition. Its only intro caller passes `WD.BIT`,
and it runs exactly once, on the animated start/menu path. Carry clear is the
public one-frame title tick; carry set invokes that same draw-then-advance body
internally at its batch-publication boundaries.

The effect is what makes the burning subtitle appear to catch light rather than
simply switch on, and its structure is part of the contract:

1. The whole hidden surface — which at this point holds the four staged bands —
   is copied aside into scratch storage, and the hidden surface is blanked.
2. The reveal then runs **two passes** over the same `288 x 49` position space.
   Each pass walks every nonzero state of a fourteen-bit maximal Galois
   sequence, interprets the state by division by 288, and applies positions
   whose row is 0 through 48. After the nonzero-state cycle, a successfully
   completed pass applies one explicit `(0,0)` fixup. That fixup is not counted
   toward publication, is not paced or polled, and is skipped on abort.
   Restoring a position means copying that pixel back
   from the scratch copy into the hidden surface **at all four band origins at
   once** — vertical offsets `0`, `50`, `100` and `150`, horizontally shifted to
   the bands' `x = 16` origin.
3. `WD.BIT`'s single `288 x 49` record is the mask that separates the two
   passes. Pass one restores only the positions where the mask bit is **clear**
   — every pixel *around* the `Warriors of Destiny` lettering, that is, the
   flames. Pass two restores the rest, so the lettering fills in last. One mask
   suffices because the lettering is effectively static across the four frames:
   of the `1624` positions the mask marks as lettering, `1623` hold the same
   palette index in all four band records, while `7871` of the band's `14112`
   positions vary between frames. The single exception is a lone pixel and has
   no bearing on the effect; treat the lettering as frame-invariant.
4. Each pass starts a fresh publication countdown: 128 in-bounds nonzero-state
   positions normally, or 256 when the boot calibration value is less than
   250. The countdown advances for every in-bounds position whether that
   pass's mask selects the pixel or not. One pass therefore makes 110 or 55
   publications, then ends with 31 counted positions plus the uncounted corner
   fixup still unpublished. There is no tail publication. Pass one's 32-position
   tail first becomes visible with pass two's first batch; pass two's tail is
   exposed only by the loader's ordinary title tick after this entry restores
   the complete hidden bands.
5. A batch publication draws the frame named by the current free-running
   modulo-four counter and increments the counter afterward. The counter is not
   reset at the effect or pass boundary. Thus a fresh normal run makes 220
   internal publications and returns the counter to zero; the 256-position
   cadence makes 110 and leaves it at two before the loader's following tick.
6. Speaker and calibrated waiting occur only after a batch publication, never
   per position. For publication `k` within either pass, starting at one, let
   `T = 400 - 3k`. A speaker burst occurs exactly when the low nine bits of the
   persistent gate state are less than `T`; the gate-state recurrence and burst
   shape are given below. A burst publication then waits 45 full calibration
   units, while a silent publication waits 50. There is no BIOS tick.
7. Keyboard status is polled once after every nonzero LFSR state, including
   states that map outside the valid row range. For an in-bounds state the
   masked restore happens first; if it completes a batch, publication, counter
   advance, sound, and wait also happen before the poll. A pending key is not
   consumed. It aborts before the LFSR/gate-state advance and before the final
   corner fixup; an abort in pass one also skips pass two.
8. On exit the scratch copy is written back over the hidden surface, so the four
   clean bands survive intact for the idle strip, and the scratch storage is
   released.

The speaker gate uses a persistent sixteen-bit state initialized to `0x7664`
when the driver is loaded and not reset between passes or ignition calls. After
each non-aborted nonzero LFSR-state iteration, including an out-of-bounds one,
it is advanced modulo 65,536 as follows:

```text
gate = (((gate + 0x9248) rotate-right 3) XOR 0x9248) + 0x0011
```

For the first uninterrupted ignition after driver load, this gives 48 then 53
speaker bursts across the two normal 128-position passes, or 35 then 33 across
the two 256-position passes. One burst keeps the speaker enabled while it
programs 25 successive pitches. A separate persistent pitch state, also
initialized to `0x7664`, uses the same recurrence once per pitch; the requested
frequency is `100 + (pitch_state modulo 1401)`, or 100 through 1500 Hz, and
each pitch is held by a calibrated wait whose inner count is the boot
calibration shifted right four bits. The speaker is disabled after pitch 25.
Audio output may be omitted by a silent implementation; the gate still defines
which publication takes the 45-unit rather than 50-unit pacing branch.

The reveal covers only the band footprint. It is a different effect from the
logo dissolve in section 3's loader step 4, which is an ordinary pseudo-random
rectangle transfer over `(0, 0)..(319, 100)` with no timing gate, no mask and no
second pass. The logo does not stipple in at band cadence, and the band is not
revealed by the rectangle-dissolve entry.

The menu and message timing rules are:

| Situation | Title-strip advancement |
|---|---|
| Signature path drawing `BRITISH.PTH` | No title-strip advancement from the signature delay/poll steps. |
| Plain start/menu screen load or redraw | One clear-carry title tick before the lower intro text window and menu labels are redrawn. |
| Finished menu idle, no key returned | One clear-carry title tick for each no-key poll pass, up to the two-hundred-pass Return-to-View timeout. |
| Valid menu key returned | No extra idle tick for that key pass; dispatch begins immediately. |
| Invalid key returned | No extra idle tick for that key pass; the menu is re-rendered and resumes polling. |
| Empty-save / no-active-game message | No autonomous title ticks while the message is waiting; the following menu redraw performs the ordinary one-tick start/menu path. |
| Return from story, transfer, chargen, acknowledgement, or Return-to-View | No background ticking while the subflow owns the screen. Ticking resumes only at explicit transition/title-tick calls and then in the menu idle loop. |

Return-to-View is the exception among subflows in that its own per-frame
preview tick calls the same clear-carry title tick before drawing preview
content. The preview then draws over the affected area for that frame and
restores the preserved title/menu surface before returning to menu polling.

## 6. Intro menu model

The intro menu is a six-entry menu with a moving highlight. It is rendered after the title/start screen is ready and remains the controlling loop until a valid Journey Onward load returns to the main loop or the process exits by another path. Keys are folded to uppercase before dispatch, matching the input-system contract in `input.md`.

The six entries, in row order, with the label each one shows on screen:

| Row | Key | On-screen label | Result |
|---:|---|---|---|
| 0 | `J` | `Journey Onward` | Load the active save and return to the main loop if valid. |
| 1 | `C` | `Create New Character` | Enter character creation through the proportional-font/chargen flow. |
| 2 | `T` | `Transfer from Ultima IV` | Enter the Ultima IV character-transfer path and commit or abandon from there. |
| 3 | `U` | `Ultima V Introduction` | Play the story slide sequence, then return to the intro menu. |
| 4 | `A` | `Acknowledgements` | Show credits/acknowledgements, then return to the intro menu. |
| 5 | `R` | `Return to the View` | Run the non-interactive Return-to-View preview, restore the menu surface, then remain in intro mode. |

The letter keys are only one of the three ways to reach those results; the
arrow keys, Enter/Space and the idle timeout are specified in section 6.2.

### 6.1 Lower menu window

The lower menu window is drawn as the last act of the start/menu loader, after
the loader's one clear-carry title tick and before the six menu labels. It is
**not** a single-line rectangle of five box-drawing glyphs. That description was
wrong and is withdrawn: the window is a thick frame band of solid and rounded
character cells, with a separate one-pixel rectangle stroked inside it and the
interior blanked by a text-window clear.

It is built in three passes.

**Pass 1 — the frame band, in the frame colour.** These are ordinary fixed-cell
glyph writes in the intro's frame colour — slot 2 of the boot-time UI colour
table (`display-driver.md` section 2), which is palette index `1`, blue, on the
sixteen-colour drivers:

| Text row | Cells written |
|---:|---|
| 15 | column `0`: top-left rounded corner; columns `1..38`: 38 solid cells; column `39`: top-right rounded corner |
| 16 through 23 | column `0` and column `39`: one solid cell each; the interior is not written by this pass |
| 24 | column `0`: bottom-left rounded corner; columns `1..38`: 38 solid cells; column `39`: bottom-right rounded corner |

The corners are **font content, not generated geometry**. In the fixed-cell font
(`IBM.CH`, or its Hercules equivalent) the solid cell is glyph code `0x7F` —
all sixty-four pixels set — and the four corners are glyph codes `0x7B`
(top-left), `0x7C` (top-right), `0x7D` (bottom-left) and `0x7E`
(bottom-right). These are the same bevel glyphs the gameplay screen's frame uses
for three of its corners (`display-driver.md` section 7, "Shared game-screen
frame"); the menu window is the one caller that uses all four. The top-left corner's ink begins at column `5` on
its first row and then at columns `3`, `2`, `1`, `1`, `0`, `0`, `0` on the
remaining seven; the other three corners are its horizontal, vertical and
diagonal mirrors. Because the frame band starts at text row 15, that profile
lands on pixel rows `120..127`, which is exactly the rounded-corner run a
capture of the running game measures.

The last cell of row 24 is the bottom-right cell of the full-screen text window,
so writing it would normally scroll the window. The intro suppresses the
window's auto-scroll for that one write and restores it immediately afterwards.
An earlier revision of this section attributed that suppression to the
inverse-video attribute; that was wrong and is withdrawn — the flag being
toggled is the scroll suppressor.

**Pass 2 — the inner rectangle, in the bright colour.** With the drawing colour
set to slot 1 of the UI colour table — palette index `15`, white, on the
sixteen-colour drivers — the intro strokes one closed four-segment
path with the driver's line primitive: from `(7, 127)` to `(312, 127)`, down to
`(312, 192)`, back to `(7, 192)`, and up to `(7, 127)`. The result is a
one-pixel white rectangle: horizontal rules on pixel rows `127` and `192`
spanning columns `7..312`, and verticals in columns `7` and `312` spanning rows
`128..191`. An earlier revision described only the top rule plus "two short
horizontal fills below it"; that is withdrawn — the top rule is one of four
segments of a closed rectangle, and the short fills belong to the bottom caption
described below.

**Pass 3 — the interior clear.** The intro narrows the active text window to
cells `1..38` by rows `16..23`, issues the text system's window-clear control
(`text-output.md` section 3), and restores the full 40-by-25 window. The clear
converts the narrowed window to its pixel rectangle and fills it with the
window's background colour, so pixel columns `8..311` of rows `128..191` become
black. This clear lands on the visible page, because the loader selected it
before returning; the same control code is used against the hidden surface
elsewhere in the intro, which is why the driver's filled-rectangle entry must
honour the render target rather than being visible-page-only
(`display-driver.md` section 8).

Net geometry, which is what a renderer should be checked against:

- a frame band in palette index `1` covering pixel rows `120..199` across the
  full width, rounded at all four corners by the profile above;
- a one-pixel palette-index-`15` rectangle with rules at `y = 127` and `y = 192`
  over `x = 7..312`, and verticals at `x = 7` and `x = 312` over `y = 128..191`;
- an interior of `x = 8..311`, `y = 128..191` in the text background (black).

#### Captions on the border band

Both captions are written as ordinary text cells in the text window's own
attribute — white foreground on background `0` — so they punch black cells
straight through the blue band. Each caption is flanked on both sides by the
**triangular bracket end-cap** composite that the gameplay screen reuses so
heavily: the right-pointing cap (`IBM.CH` glyph code `0x02`) on the left of the
caption and the left-pointing cap (code `0x01`) on the right, each drawn as a
solid triangle in the frame colour on background `0` with two accent-coloured
lines stroked along its hypotenuse, and the window attribute restored
afterwards. `display-driver.md` section 7 owns that composite's construction and
its two stroke pairs; the intro is simply another caller, so the caps are **not**
`>` and `<` characters and must not be typeset as such.

| Caption | Row | Literal text | Cells occupied |
|---|---:|---|---|
| Select prompt | 15 | `Select: ` (eight characters, including the trailing space) | `15` right-pointing cap, `16..23` text, `24` left-pointing cap |
| Copyright | 24 | `Copyright 1988 Lord British` (twenty-seven characters) | `5` right-pointing cap, `6..32` text, `33` left-pointing cap |

After printing the select prompt the intro parks the cursor at cell `23` of row
15 — the blank that ends `Select: `, immediately before the closing cap.
That is where the animated cursor cell described below appears.

The copyright caption is placed by the shared centred-caption helper specified
in section 12.1 — the same helper the Return-to-View chapter captions use — so
its geometry is not restated here beyond the instance. For a twenty-seven
character string the helper's rule `start_col = 18 - floor(len / 2)` gives
column `5`, so the caption group runs `5` (opening cap), `6..32` (text), `33`
(closing cap), and the helper's `end_col` — the first cell past the group — is
`34`. Drawing the caption also **repaints the border band either side of it**,
because the caption cells would otherwise leave the white bottom rule broken
beyond the caption's ends: the helper fills pixel rows `193..199` in the frame
colour from `x = 8` to `x = start_col * 8` and from `x = end_col * 8` to
`x = 311`, then draws a single row at `y = 192` in the bright colour over the
same two spans.

The top caption is placed differently: it is not centred by that helper at all.
The intro sets the cursor directly to column `15` of row 15 and emits cap,
string, cap, then repositions to column `23`. There is no border repaint around
it, because the top rule at `y = 127` sits inside the frame band's *first* cell
row and the caption cells sit in that same row — the caption interrupts the rule
and nothing restores it.

#### The cursor cell

The cell parked at row 15, column 23 is not an on/off blink. It cycles the same
four consecutive fixed-cell glyph codes `0x05` through `0x08` that the gameplay
message window's input cursor uses (`text-output.md` section 10.6), one phase
per menu poll pass. Each
of the four is a diagonal hatch of two-pixel steps, and the four are the same
hatch shifted two pixels along, so the cell reads as a diagonal pattern marching
steadily across it. The instant a poll returns a key the cell is overwritten
with a space.

#### Window lifetime and messages

The frame is drawn once and stays for the whole intro-menu lifetime. It is not
redrawn between the menu labels and a message. For the no-active-save message
the intro reuses the same interior: the message is written into the interior
cells through the normal text-output path (which clears each output cell as it
draws), waits for one keystroke, and returns to the menu poll loop.

### 6.2 Menu labels and input model

The six labels are rendered as fixed-cell text inside the window interior after
the frame is drawn. Each is emitted as one leading blank, the label string, and
one trailing blank, starting at the row's column origin.

The labels are the **full names**. The abbreviated forms `Create New Char.`,
`Transfer from U4`, `Ultima V Intro.` and `Return to View` that earlier
revisions of this table published do not exist in the shipped data; they were
invented. The column origins were right and are unchanged.

| Row index | Text row | Column origin | Label | Cells occupied, blanks included |
|---:|---:|---:|---|---|
| 0 | 17 | 12 | `Journey Onward` | 12..27 |
| 1 | 18 | 9 | `Create New Character` | 9..30 |
| 2 | 19 | 8 | `Transfer from Ultima IV` | 8..32 |
| 3 | 20 | 9 | `Ultima V Introduction` | 9..31 |
| 4 | 21 | 11 | `Acknowledgements` | 11..28 |
| 5 | 22 | 10 | `Return to the View` | 10..29 |

The highlight is the text layer's inverse-video attribute, toggled on
immediately before the leading blank and off immediately after the trailing
blank, so the highlighted row shows a solid bar over the whole cell span in the
table's last column — including both blanks. **The initial highlight is row 0,
`Journey Onward`**, and the highlight index survives across poll passes.

#### Input

The menu has one input model with three entry points, all of which operate on
that same highlight index. An earlier revision of this section said dispatch was
purely by key and that "the row number only controls presentation"; that is
withdrawn — the row index is load-bearing, because Enter, Space and the idle
timeout all resolve through it. The claim that the menu keeps a
"recent-selection cache" that Enter replays is withdrawn as well; there is no
such cache. What exists is a fixed six-entry row-to-letter table: rows `0`
through `5` map to `J`, `C`, `T`, `U`, `A`, `R`.

| Input | Effect |
|---|---|
| `J`, `C`, `T`, `U`, `A`, `R` (folded to uppercase) | Move the highlight to that row **and** commit it in the same pass. |
| Up arrow, left arrow | Move the highlight one row toward row 0, wrapping from row 0 to row 5; repaint the labels; keep polling. |
| Down arrow, right arrow | Move the highlight one row toward row 5, wrapping from row 5 to row 0; repaint the labels; keep polling. |
| Enter, Space | Commit whichever row is currently highlighted, resolved through the row-to-letter table. |
| Any other key | Discarded. The caption is redrawn and polling resumes; no idle title tick runs for that pass. |
| Two hundred consecutive no-key passes | Commit `Return to the View` exactly as though `R` had been pressed. |

Letter hotkeys and the highlight model therefore coexist rather than competing:
a letter both moves the bar and activates the row, so the bar always reflects
the last selection made.

Each no-key poll pass costs two BIOS ticks — one in the cursor poll, one in the
title tick — so the two-hundred-pass timeout is roughly twenty-two seconds of
unattended menu (`timing.md` section 5.1). No gameplay time advances while the
intro menu is active, because no gameplay mode has started.

Behaviourally, the player sees a stable six-option menu with a moving highlight
bar, a marching cursor cell after the `Select: ` prompt, and a burning subtitle
band that keeps ticking above the window; the menu waits for one of the accepted
inputs and returns to the same state after every non-play sub-screen finishes.

## 7. Journey Onward (`J`)

`J` is the standard load path. It is reachable both from the finished menu and from the early title wait. The intro performs the load inline before returning to the main loop; there is no general-purpose "load game" function that other systems call.

The load path does the following at a behavioural level:

1. Draw the standard game-screen border frame. This is the viewport, stats panel, and command-prompt chrome shared by all gameplay modes. The frame is a pure deterministic paint that depends on no save data; it sets up the visual layout in preparation for gameplay.
2. Initialise the scene-transition display state. At this point the intro scene state is still active, so this step is effectively a no-op; it primes the transition cell for the post-load hand-off.
3. Switch the display mode to the gameplay configuration and position the text cursor.
4. If the intro scene state is still the menu state, load any required transition resource and advance to the post-menu transition state.
5. Show a wait indicator.
6. Read the whole `SAVED.GAM` image into the resident save-state region.
7. Check whether the save contains an active Avatar record.
8. If the save is empty, display the "no active game" style message, wait for a key, and return to the intro menu.
9. Read `SAVED.OOL`, the object-overlay companion file.
10. Mirror the surface and underworld object-overlay halves to their per-plane files.
11. If the loaded state resumes on the underworld surface, prompt/probe for the underworld data disk and refresh the underworld object overlay once the disk is available.
12. Mark the display/gameplay transition as ready and return from the intro overlay.

Steps 1 through 5 prepare the display for gameplay before any save data is read. The game-screen frame is drawn first so the player sees the gameplay viewport appear while the save loads. The frame consists of the left viewport area, the right stats panel with horizontal subdividers, and the bottom command-prompt area, formed by filled rectangles, three rounded corner glyph cells, and four rule outlines. This is the same screen layout used by overworld, town, dungeon, and combat modes. The complete rectangle list, glyph cells, outline paths, colours and paint order are published in `systems/display-driver.md` section 7, and the three text windows the same step installs are in `systems/text-output.md` section 10.1.

After the intro returns, the main loop reads the scene state that came from the loaded save and dispatches to overworld, town, or dungeon as appropriate. The intro does not load map files such as world data, location data, NPC files, or talk files during this path. Those are loaded by the gameplay mode that the main loop selects.

The file roles, empty-save guard, object-overlay mirror writes, and disk-swap semantics are specified in `save-load.md`, `formats/saved-gam.md`, and `formats/ool.md`.

The empty-save message is written into the current intro text window after the
failed load check, then the path waits for one keypress and returns to the
intro menu loop. It does not start a gameplay mode, does not tick world time,
and does not require a fresh start/menu art load before the menu labels are
repainted by the normal menu loop.

## 8. Create New Character (`C`)

`C` hands control from the intro menu to the character-creation flow. The hand-off goes through a resident trampoline into the proportional-font overlay, which owns both the paragraph renderer used by the questionnaire and the chargen driver. The chargen routine is entirely self-contained within that overlay: it loads its own assets, runs the questionnaire using local helpers, writes the save files through resident I/O wrappers, and returns directly to the intro menu. It does not chain through the spell-casting overlay or any other overlay.

From the intro system's perspective, the contract is simple:

- select `C`;
- enter chargen;
- let chargen either abort without writing or write the first `SAVED.GAM` and `SAVED.OOL`;
- return to intro mode after chargen completes;
- require the player to press `J` afterward to load the newly written save.

The intro does not automatically enter Britannia after character creation. This is visible in play: creating a character produces a save, then returns to the menu. The player must explicitly choose Journey Onward to start the game.

The questionnaire, seed-file cloning, name/gender prompts, stat assignment, and save commit are specified in `chargen.md`. The intro spec only owns the menu hand-off and return-to-menu behaviour.

## 9. Transfer from Ultima IV (`T`)

`T` enters the transfer path for players bringing forward an Ultima IV character. This path is intro-owned rather than part of the proportional-font questionnaire flow, but it shares the same end goal as chargen: produce a playable U5 save state and return to the intro menu. The player must still choose Journey Onward afterward to enter gameplay from the newly written save.

The observed transfer path:

1. Switches the intro into its transfer/continue state.
2. Sets up disk-swap state for the transfer media.
3. Loads the `INIT.GAM` save-image seed and the `INIT.OOL` object-overlay seed
   as the destination baseline — the same pair chargen uses.
4. Runs the drive-selection loop for the Ultima IV media. **This is the only
   place the path can be abandoned:** `Esc` here restores the intro/menu state
   and returns to the menu without reading or writing anything.
5. Reads and validates the predecessor save, then renders the comparison
   screen — two character-information panels for the single imported
   character, not a party roster — and walks its fixed sequence of
   confirmation and conversion stages.
6. On a validation failure, prints the bad-data page, waits for a key, and
   returns to the menu with nothing written.
7. On commit, writes the normal save files, restores the intro/menu state, redraws the start/menu screen, and resumes menu polling.

Earlier revisions of this list named a "Britannia seed image", described the
preview as "a character-roster/status screen showing party slots", and placed
an abort in the confirmation polling loop. All three are **withdrawn**: the
seed files are `INIT.GAM` and `INIT.OOL` (no `BRIT.GAM` exists), the preview is
a two-panel single-character comparison screen, and once the drive has been
selected no key aborts the transfer — `Esc` at the confirmation stages is
simply ignored. `systems/u4-transfer.md` sections 6.4, 6.5 and 8 own the
detail.

The U4-to-U5 character-field translation is specified in
`systems/u4-transfer.md`. It belongs with the transfer spec because it
determines the contents of the resulting save, not the intro menu's control
flow. The comparison-preview and disk-swap behaviour are included here because the
intro overlay owns that screen and its polling loop.

## 10. Ultima V Introduction (`U`)

`U` plays the story slide sequence. This is a non-play path: after the sequence ends, the player returns to the intro menu.

The sequence begins by making sure the intro/start-screen state is active. It
loads the proportional font art, the shared `TEXT.16` art strip, and the first
story-art file, then iterates through twenty-one fixed narrative steps. A step
uses one of the six story-art files `STORY1.16` through `STORY6.16`; the art
file changes only at fixed step boundaries:

| Zero-based steps | Story art file |
|---|---|
| 0-1 | `STORY1.16` |
| 2-6 | `STORY2.16` |
| 7-8 | `STORY3.16` |
| 9-10 | `STORY4.16` |
| 11-12 | `STORY5.16` |
| 13-20 | `STORY6.16` |

Each step is composed on the hidden surface and revealed as one whole page
after the wait, which is why a keypress appears to swap the slide instantly.
The per-step order is:

1. Ensure the story-art file for the current step is loaded, reloading only
   when the fixed step boundary changes the file.
2. Select the hidden surface and clear it. Every step therefore starts from a
   blank page; no part of the previous step survives.
3. If the step is a transition-strip step, draw its two `TEXT.16` records
   first.
4. Draw the step's primary story-art record at its fixed placement.
5. If the step has a secondary story-art pass, draw that record.
6. Publish the step's paragraph-box parameters (margins, band bounds, and the
   starting pen position) to the proportional renderer.
7. Render the step's narrative text through the proportional-font renderer:
   either the `STORY.DAT` record selected for this step, or — for step 6 only
   — the two inline doorway lines specified in section 10.1.
8. Except for step 0, flush the keyboard type-ahead buffer once and then wait
   until a key is returned.
9. Transfer the whole hidden surface to the visible page. This is the moment
   the step becomes visible.
10. Run any post-reveal effect tagged to that step (only step 1 has one).

Step 0 is an automatic opening transition: it renders its text and is revealed
immediately, without waiting for input. Steps 1 through 20 wait until the
keyboard poll returns a non-zero key. Because the reveal happens *after* the
wait, the key that dismisses step `n - 1` is the key that presents step `n`;
after step 20 is presented, one further keypress ends the sequence. This wait
is local to the intro; it does not run gameplay world ticks, NPC schedules,
active-object animation, the title tick, or the saved-game clock, and nothing
on the visible page changes while it is pending.

The shipped `STORY.DAT` file supplies twenty non-empty text records. The intro
sequence has one additional visual step: step 6 uses two inline
doorway-transition lines owned by the intro code instead of reading a
`STORY.DAT` record. Every other step reads the record selected for it and uses
the same paragraph conventions as other proportional-font narrative screens.
Story text is addressed by a **fixed per-step record selection**, not by a
running cursor: each text-consuming step names its own record independently, so
step 6's lack of a read cannot desynchronise step 7 and an implementation needs
no record-index bookkeeping at all. See `formats/story-dat.md`.

Primary story-art placement uses 320-by-200 pixel coordinates with the origin
at the upper-left corner. The following table records the story-art subimage
chosen by each narrative step; special-effect steps can replace this primary
draw or add an additional text-strip or story-art draw around it.

| Step | Art file | Subimage | Top-left X | Top-left Y | Notes |
|---:|---|---:|---:|---:|---|
| 0 | `STORY1.16` | 0 | 0 | 0 | Opening transition step |
| 1 | `STORY1.16` | 1 | 0 | 74 | Post-wait transition |
| 2 | `STORY2.16` | 0 | 136 | 0 |  |
| 3 | `STORY2.16` | 1 | 0 | 38 |  |
| 4 | `STORY2.16` | 2 | 152 | 76 |  |
| 5 | `STORY2.16` | 2 | 0 | 0 |  |
| 6 | `STORY2.16` | 2 | 72 | 38 | Inline doorway text |
| 7 | `STORY3.16` | 0 | 0 | 0 | Transition step |
| 8 | `STORY3.16` | 1 | 0 | 82 |  |
| 9 | `STORY4.16` | 0 | 0 | 82 |  |
| 10 | `STORY4.16` | 1 | 0 | 82 |  |
| 11 | `STORY5.16` | 0 | 0 | 82 |  |
| 12 | `STORY5.16` | 1 | 0 | 82 |  |
| 13 | `STORY6.16` | 0 | 176 | 0 |  |
| 14 | `STORY6.16` | 1 | 0 | 0 | Transition step |
| 15 | `STORY6.16` | 2 | 176 | 0 | Secondary art pass |
| 16 | `STORY6.16` | 6 | 0 | 46 | Secondary art pass |
| 17 | `STORY6.16` | 4 | 176 | 78 | Secondary art pass |
| 18 | `STORY6.16` | 2 | 0 | 0 | Secondary art pass |
| 19 | `STORY6.16` | 6 | 176 | 55 | Secondary art pass |
| 20 | `STORY6.16` | 4 | 0 | 87 | Secondary art pass |

Special transition steps use the following additional draws and text sources:

| Steps | Extra behavior |
|---|---|
| 0, 7, 14 | Draw two `TEXT.16` transition subimages before the story-art draw. Step 0 uses transition subimages 0 and 1 at `(224, 30)` and `(168, 58)`. Step 7 uses transition subimages 0 and 2 at `(232, 26)` and `(200, 54)`. Step 14 uses transition subimages 0 and 3 at `(184, 0)` and `(248, 0)`. |
| 1 | After the step's key wait, draw `STORY1.16` subimage 2 at `(40, 86)` and run a local rectangular transition over the inclusive region from `(40, 86)` to `(75, 120)`. |
| 6 | Draw an additional `STORY2.16` subimage 3 at `(96, 39)` and render two inline doorway-transition text lines instead of reading a `STORY.DAT` record. Fully specified in section 10.1. |
| 15, 20 | Draw a second `STORY6.16` subimage 3 at the same X coordinate and 55 pixels below the primary story-art Y coordinate. |
| 16, 18 | Draw a second `STORY6.16` subimage 5 at the same X coordinate and 55 pixels below the primary story-art Y coordinate. |
| 17, 19 | Draw a second `STORY6.16` subimage 7 at the same X coordinate and 55 pixels below the primary story-art Y coordinate. |

The transition effects are local to the story loop and do not advance gameplay
time. Steps 0, 7, and 14 are static transition-strip pre-draws that happen
before the primary story art, on the hidden surface, inside the same
composition pass as everything else on that step; they are not animated
transitions. The secondary art passes for steps 15 through 20 are likewise
ordinary draws in the same composition pass, not post-reveal effects.

Step 1 is the only step with a post-reveal effect, and it is **not** a column
wipe. Earlier revisions of this document described it as a left-to-right,
one-pixel-column-per-title-tick reveal 36 ticks long; that is withdrawn. After
step 1 has been presented, the intro selects the hidden surface again, draws
`STORY1.16` subimage 2 at `(40, 86)`, and transfers the inclusive rectangle
`(40, 86)..(75, 120)` to the visible page with the driver's pseudo-random
per-pixel dissolve (`display-driver-abi.md` section 9.6), invoked once and
self-paced. Every pixel in the rectangle is visited exactly once, the rectangle
matches the hidden surface when the call returns, pixels outside it are
untouched, and the effect does not dither, blend, or recolour the panel. The
player-input gate is the wait before the transition; once the dissolve starts
it runs to completion as a blocking local effect. The dissolve entry's own
abort gate has already been cleared by this point in the run, because menu and
story text have been drawn through the glyph entry, so this dissolve is silent
and uninterruptible; see `display-driver-abi.md` section 9.6.

No wider intro story-page transition table is part of this baseline. A caller
sweep of the story loop finds exactly one post-reveal effect — the step-1
dissolve above. Every other step's visual work is a plain
compose-then-reveal.

The start/menu-screen loader's separate reveal is optional and caller-selected,
and it is **not** a column wipe. Earlier revisions of this document described it
as a left-to-right, one-pixel-column-per-title-tick pass 320 ticks long; that is
withdrawn. The loader draws the `ULTIMA` banner record into the hidden surface
and then, only when the caller requests the animated path, transfers the
inclusive pixel rectangle `(0, 0)..(319, 100)` to the visible page with the
driver's pseudo-random per-pixel dissolve (`display-driver-abi.md` section 9.6),
invoked once and self-paced. Every pixel in the rectangle is visited exactly
once and the rectangle matches the hidden surface when the call returns; pixels
outside the rectangle are untouched. The loader polls input only after the
transfer completes; that poll can downgrade the rest of the loader to the plain
path. The plain caller path copies the same rectangle in one step with no
animation.

There is one wrinkle worth reproducing. The dissolve entry carries an abort
gate that is enabled when the driver is loaded and is cleared permanently the
first time any character is drawn through the driver's glyph entry
(`display-driver-abi.md` section 9.6). On the **very first** title/menu load no
menu text has been drawn yet, so that gate is still enabled: that one dissolve
emits a short percussive speaker click on every second visited pixel, and a
pending key found by the check that rides alongside those clicks aborts it
mid-rectangle, leaving the banner partly transferred before the loader's own
poll then downgrades the rest of the loader. The click is not per pixel and its
pitch does not simply climb; see `display-driver-abi.md` section 9.6. Every later reveal in the same run
happens after menu text has been drawn and is therefore silent and
uninterruptible. Earlier revisions of this section said the transfer is never
interruptible; that is true of every call except the first one, and the
difference is audible as well as visible. Fixed `END.DAT` and
other ordinary bitmap-window callers do not inherit this contract; their clear,
page-in, border redraw, and wait timing remain caller-owned presentation
details.

#### Per-step paragraph box

Step order item 6 above publishes the proportional renderer's layout descriptor
before any text is drawn. The descriptor model — two horizontal margin pairs,
a vertical band that selects between them, and a pen origin — is specified in
`text-output.md` section 8.1. This is what makes the story text flow around the
slide artwork: the pair selected while the pen is inside the band clears the
picture, and the other pair is used above and below it. Margin pair **B** is
selected while `band_low < pen_y < band_high`, strictly inside; pair **A**
applies otherwise.

All values are pixels on the 320-by-200 screen. A band of `200..200` can never
match, so those steps use pair A for every line.

| Step | Left A | Right A | Left B | Right B | Band low | Band high | Pen origin |
|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 180 | 320 | 0 | 320 | 180 | 200 | `(180, 128)` |
| 1 | 0 | 320 | 172 | 320 | 70 | 200 | `(0, 0)` |
| 2 | 0 | 132 | 0 | 320 | 131 | 200 | `(0, 40)` |
| 3 | 0 | 320 | 210 | 320 | 32 | 160 | `(0, 0)` |
| 4 | 0 | 320 | 0 | 148 | 70 | 200 | `(0, 9)` |
| 5 | 176 | 320 | 0 | 320 | 133 | 200 | `(176, 0)` |
| 6 | 0 | 320 | 0 | 320 | 200 | 200 | `(32, 9)` |
| 7 | 188 | 320 | 0 | 320 | 168 | 200 | `(188, 136)` |
| 8 | 0 | 320 | 0 | 320 | 200 | 200 | `(0, 0)` |
| 9 | 0 | 320 | 0 | 320 | 200 | 200 | `(0, 0)` |
| 10 | 0 | 320 | 0 | 320 | 200 | 200 | `(0, 0)` |
| 11 | 0 | 320 | 0 | 320 | 200 | 200 | `(0, 0)` |
| 12 | 0 | 320 | 0 | 320 | 200 | 200 | `(0, 0)` |
| 13 | 0 | 170 | 0 | 320 | 114 | 200 | `(0, 0)` |
| 14 | 184 | 320 | 0 | 320 | 114 | 200 | `(184, 32)` |
| 15 | 0 | 170 | 0 | 320 | 96 | 200 | `(0, 0)` |
| 16 | 0 | 320 | 148 | 320 | 33 | 137 | `(0, 0)` |
| 17 | 0 | 320 | 0 | 170 | 70 | 200 | `(0, 0)` |
| 18 | 148 | 320 | 0 | 320 | 96 | 200 | `(174, 0)` |
| 19 | 0 | 320 | 0 | 170 | 51 | 146 | `(0, 9)` |
| 20 | 0 | 320 | 156 | 320 | 79 | 200 | `(0, 0)` |

Each row is consistent with that step's art placement. Step 2, for example,
draws its picture at `x = 136` and clamps pair A's right margin to `132`, so
text above the band stays clear of the picture and text below it runs the full
width. Step 7 draws a 188-pixel-wide art column on the left and sets pair A's
left margin to `188`. Step 18's pen X (`174`) deliberately differs from its
left margin (`148`), which is legal: the renderer treats the difference as
width already consumed on the first line and resets the pen to the margin at
the first line break.

The intro never changes the space advance, so every story step uses the shipped
default of five pixels.

**Answers to the layout questions this sequence raises.**

- **Line stride.** A fixed **nine** pixels of pen Y per line, for every step.
  It does not vary with the margins, the band, or the artwork. A measurement of
  roughly twelve pixels from a scaled screen capture is a capture artefact, not
  a second stride.
- **Justification.** The renderer fully justifies every line except the last
  line of a paragraph and any line ended by an explicit newline. That is why a
  three-word line can appear stretched to the full column width. The arithmetic
  is in `text-output.md` section 8.4; the leftover pixels land on the last
  spaces of the line, not the first.
- **Hyphenation.** The renderer does **not** hyphenate. Every mid-word break in
  the shipped story text comes from a soft-hyphen marker the author placed in
  `STORY.DAT` at a syllable boundary; the renderer only chooses whether to use
  one. See `formats/story-dat.md` section 3.
- **Centering.** There is none in this path. Every step's first line starts at
  the pen origin in the table above.
- **Chapter titles.** The large ornamental chapter lettering is artwork, not
  renderer text: it comes from the two `TEXT.16` transition records that steps
  0, 7, and 14 draw before their story art, at the placements already listed in
  the special-transition table above. `STORY.DAT` contains no title strings at
  all. Do not try to typeset this lettering with the proportional font.

### 10.1 Step 6: the inline doorway lines

Step 6 is the one step whose narrative text is not a `STORY.DAT` record. Its
full contract:

**Text.** Two lines, each a single plain sentence, rendered in this order:

1. `Instantly, a shimmering blue door springs up!`
2. `With heart beating rapidly, you step into it.`

Each line is exactly 45 characters long, stored as a 45-byte string plus a
one-byte NUL terminator. (An earlier revision of this section said 44; that
was a miscount and is retracted.) Neither line contains a paragraph-indent
brace, a soft-hyphen underscore, a line feed, or any other renderer marker. An implementation must not add the markers
that `STORY.DAT` records carry, and the renderer's brace and underscore
handling never fires on this step.

**Renderer.** The same proportional-font paragraph renderer used for ordinary
story records (`text-output.md`), not a fixed-cell text window and not a
special two-line overlay primitive. Each line is issued as its own complete
paragraph.

**Placement.** Step 6 publishes the ordinary paragraph-box parameters for its
step before the first line: left margin `0`, right margin `320`, and vertical
band bounds that never select the alternate margin pair, so both lines have the
full screen width available. Line 1 starts at the step's ordinary pen origin
`(32, 9)`. Between the two lines the intro re-issues the **same left origin,
`x = 32`**, with the vertical origin pinned to pixel row `180`, so line 2 starts
at `(32, 180)`. The two lines therefore sit near the top and near the bottom of
the screen with the doorway art between them. The renderer's line advance does
not apply across the two lines: they are placed by explicit origins. Neither
line is justified, because each ends at its terminator rather than at a wrap.

**Draw order.** Within the step's single composition pass on the hidden
surface: the primary `STORY2.16` subimage 2 at `(72, 38)` first, then the extra
`STORY2.16` subimage 3 at `(96, 39)`, then line 1, then line 2. The extra
subimage is drawn **before** the text, so text may overlay it but never the
reverse. There is no text-band clear between the primary art, the extra art,
and the lines; the only clear is the whole-page clear at the start of the step,
which is also why no earlier step's text is still visible.

**Colour and shadow.** The lines use the same colour and glyph treatment as
every other story page. The renderer has no shadow, outline, or per-caller
colour override.

**Record bookkeeping.** Step 6 performs no `STORY.DAT` read of any kind.
Because story text is addressed by fixed per-step record selection rather than
by a running cursor, this leaves nothing to adjust for step 7 and no index
state for an implementation to track.

**Advance.** After the two lines are rendered, step 6 takes the ordinary
non-automatic path: flush the keyboard type-ahead buffer, wait for any key,
then present the page. There is no extra delay, no additional transition, and
no post-reveal effect on this step.

Source provenance: derived from the intro-overlay function notes under
`../u5-decomp/functions/INTRO_OVL/`.

### 10.2 Boundaries

The slide loop does not mutate gameplay state, does not create a save, and does not select a gameplay scene. Its only persistent effect is that, when it returns, the intro reloads or redraws the start/menu view so the six-option menu can continue.

The screen-panel asset container is specified in `formats/tiles.md`. The proportional text output contract is described in `text-output.md`, and the story text file is specified in `formats/story-dat.md`.

## 11. Acknowledgements (`A`)

`A` displays the acknowledgement/credits screen and then returns to the intro menu. It uses the same already-initialised display and text systems as the title and story paths. The acknowledgement path is self-contained: it does not read or write the save image, does not change the gameplay scene, and does not exit the program.

### 11.1 The acknowledgement page is artwork, not text

The acknowledgement screen is a **pre-rendered image page**. Its credit lines
are drawn into the bitmap: no part of the credits is typeset. Nothing
typesets the credits: no font selection, no text-window rectangle, and no
printable character contributes to the credits page itself. The one use of the
text pipeline in this path is the menu rebuild of section 11.2 step 6, and it
lands entirely on the hidden surface while the credits remain on display. The
hardware palette is never reprogrammed at any point in the path. For the
credits page there is consequently no font path, no per-line layout, no text colour
or inverse behaviour, and no pagination; the single page's input rule is the
one any-key wait in section 11.2 step 7. An implementation reproduces this
screen by drawing the shipped artwork; it must not attempt to typeset the
credits from strings.

**Retraction — the text claim was over-broad.** An earlier revision of this
section stated flatly that the handler "never sets a text rectangle, never
emits a printable character, and never changes a palette or text attribute".
That blanket wording is **withdrawn**. It holds for the credits page, but not
for the path as a whole: step 6 of section 11.2 rebuilds the menu screen
through the ordinary text pipeline while the credits are still on display —
a whole-page clear of the hidden surface, the box-drawing window frame of
section 6.1, and the six menu labels of section 6.2 with the Acknowledgements
row bracketed by the inverse-video attribute toggle. Those emissions all land
on the hidden surface, never on the displayed credits. The only accurate
forms of the claim are the scoped ones: the credits are artwork rather than
text, and nothing clears the lower band of the visible page before the
credits appear (section 11.2, "No pre-clear").

The page comes from the `STARTSC` archive — the paired `.16`/`.4` screen-panel
family member the boot depth rule resolves for the current driver. Earlier
revisions of this document attributed `STARTSC` to the start/menu screen and
sourced the credits from the end-screen family; both were wrong. The
start/menu screen is built from the `ULTIMA` banner archive (section 3), and
`STARTSC` is used by nothing except this path.

`STARTSC` holds three records:

| `STARTSC` record | Role | Size |
|---:|---|---|
| 0 | Left ornamental pillar | 16 x 137 |
| 1 | Credits page (all credit text is part of the artwork) | 288 x 137 |
| 2 | Right ornamental pillar — a mirrored *variant* of record 0, shipped as its own record | 16 x 137 |

Records 0 and 2 read as a mirrored pair, but record 2 is **not** a horizontal
flip of record 0 and must not be synthesised as one: their dithering differs,
and only seven of the 137 row pairs are exact mirrors of each other (one row
is identical rather than mirrored). An implementation must decode and draw
record 2 from the archive, exactly as the original does.

Assembled, the three records form one 320-by-137 band whose top row is `63`,
so the finished page occupies rows `63..199` — the whole screen below the
`ULTIMA` logo band. Record 1 sits at `(16, 63)`, record 0 finishes at
`(0, 63)`, record 2 finishes at `(304, 63)`.

### 11.2 Presentation sequence

All draws below use 320-by-200 pixel coordinates with the origin at the
upper-left corner. "Hidden surface" and "visible page" are the two surfaces of
the display-driver model in `display-driver-abi.md`.

1. Load the `STARTSC` archive, retrying until the load reports a nonzero
   segment.
2. Select the hidden surface and draw record `1` at `(16, 63)`, opaque. The
   credits page is composed off-screen; nothing is visible yet.
3. Select the visible page. Everything from here draws directly to it.
4. **Rise phase.** For `y` from `199` down to `63` inclusive, one pixel per
   step, draw record `0` at `(144, y)` and record `2` at `(160, y)`. The two
   pillars climb the centre of the screen from the bottom edge and come to
   rest side by side occupying columns `144..175` at rows `63..199`.
5. **Part phase.** For `k = 0, 8, 16, ... 136` (eighteen steps):
   1. draw record `0` at `(136 - k, 63)`;
   2. copy the inclusive rectangle `(152 - k, 63)..(159 - k, 199)` from the
      hidden surface to the visible page;
   3. draw record `2` at `(168 + k, 63)`;
   4. copy the inclusive rectangle `(160 + k, 63)..(167 + k, 199)` from the
      hidden surface to the visible page;
   5. wait one hardware timer tick.

   The pillars walk outward to `(0, 63)` and `(304, 63)` while two
   eight-pixel-wide bands expand from the screen centre and publish the
   credits page column by column. The last step's bands are `16..23` and
   `296..303`, which exactly meet the resting pillars, so the completed band
   is contiguous.
6. Rebuild the menu screen on the hidden surface while the credits are still
   displayed: load the `ULTIMA` archive, select the hidden surface, issue the
   text system's clear control (`text-output.md` section 3) — the intro's
   active text window is the full-screen one, so this blanks the **entire**
   hidden page, including the rows the credits page occupied — draw `ULTIMA`
   record `1` at `(16, 65)` (the first subtitle animation phase), release the
   archive, draw the lower intro text-window frame (section 6.1), and render
   the six menu labels with the Acknowledgements row highlighted (section
   6.2). This step is the one place in the path that uses the text pipeline:
   it clears, emits box-drawing glyphs, prints label strings, and toggles the
   inverse attribute for the highlighted row. All of it lands on the hidden
   surface; none of it is visible until the close phase.
7. Poll the keyboard until any key is returned. **Any key advances; `Esc` has
   no special meaning here.** There is no timeout, no timed auto-advance, and
   no second page.
8. Select the visible page. **Close phase**, the mirror of step 5. For
   `k = 136, 128, ... 8, 0` (eighteen steps): draw record `0` at
   `(144 - k, 63)`; copy `(136 - k, 63)..(143 - k, 199)` from the hidden
   surface; draw record `2` at `(160 + k, 63)`; copy
   `(176 + k, 63)..(183 + k, 199)` from the hidden surface; wait one
   hardware timer tick. The pillars walk back to the centre while the rebuilt
   menu screen is published from the outside inward.
9. Release the `STARTSC` archive.
10. **Sink phase.** For `y` from `63` to `198` inclusive, one pixel per step,
    draw record `0` at `(144, y + 1)` and record `2` at `(160, y + 1)`, then
    copy the single-row inclusive rectangle `(144, y)..(175, y)` from the
    hidden surface to the visible page. Finish with one more single-row copy
    of `(144, 199)..(175, 199)`. The two pillars slide off the bottom of the
    screen and the last centre column of the menu screen is published behind
    them.
11. Rebuild the four subtitle animation bands on the hidden surface exactly as
    the start/menu loader does (section 3, step 5): clear the hidden surface
    again — a second whole-page clear — and draw `ULTIMA` records `1`, `2`,
    `3`, `4` at `(16, 0)`, `(16, 50)`, `(16, 100)` and `(16, 150)`. This
    clears hidden-surface rows `0..199` and overdraws the four band
    rectangles, the last of the path's writes above row `63` (see section
    11.3).
12. Select the visible page, flush the keyboard type-ahead buffer, and return
    to the menu poll loop.

**Wipe cadence.** Only the part and close phases are paced. Each of their
eighteen steps ends with a wait of exactly **one hardware timer tick** — the
counted-tick helper in `timing.md` section 4, approximately 54.9 ms — so each
of those two phases takes about **0.99 seconds** on a host above the
calibration baseline, and completes immediately on a host at or below it,
because a one-tick request is exactly the case the slow-CPU skip in
`timing.md` section 5.2 elides. The rise and sink phases carry **no wait at
all**: their 137 and 136 steps run back to back at whatever rate the two
pillar draws and the row copy allow, which on period hardware reads as a fast
slide rather than a timed animation. There is no other pacing primitive in
this path — no calibrated busy wait, no per-step keyboard probe, and no title
tick.

**No pre-clear.** Nothing clears the lower band of the visible page before
the credits appear. (The whole-page clears in steps 6 and 11 land on the
hidden surface, never on the displayed credits.) The coverage is exact
instead: the part phase's left bands sweep columns
`16..159`, its right bands sweep columns `160..303`, and the two pillars come
to rest on columns `0..15` and `304..319`, so every column of the
320-by-137 band is published exactly once by the time the phase ends. During
the rise phase the pillars are drawn straight over the still-visible menu
window.

**Menu restore.** The menu screen that reappears is **rebuilt from scratch**
on the hidden surface (step 6) while the credits are still displayed, not
restored from a saved copy of the pre-credits screen. The close and sink
phases then publish that freshly built surface.

### 11.3 Backing-surface contract

No pixel above row `63` **of the visible page** is written at any point in
this path. The `ULTIMA` logo occupying rows `0..60` of the visible page is
simply never touched, so it remains on screen throughout the credits. Visible
rows `63..199` are overwritten by the credits band and then rebuilt from the
hidden surface; nothing of the previous menu screen is saved or restored.

**Retraction — the surface scope was wrong.** An earlier revision of this
section said "no pixel above row `63` is written on either surface at any
point in this path". That is **withdrawn**: it is true only of the visible
page. The hidden surface is written above row `63` twice, and an
implementation that honours the withdrawn sentence literally cannot reach the
documented end state:

- Step 6 clears the whole hidden page and draws `ULTIMA` record `1` at
  `(16, 65)`, plus the frame and menu labels below.
- Step 11 clears the whole hidden page again and stages `ULTIMA` records
  `1..4` at vertical origins `0`, `50`, `100` and `150`, so every hidden row
  `0..199` is written by the clear and rows `0..48`, `50..98`, `100..148` and
  `150..199` are then overdrawn by the four bands (the three single rows
  between bands keep the cleared background).

None of that reaches the visible page above row `63`, because every copy the
close and sink phases perform has top edge `63` and bottom edge `199`. That
is why the logo survives: not because the hidden surface is untouched up
there, but because nothing above row `63` is ever copied out of it.

The hidden surface is repurposed twice — first for the credits page, then for
the rebuilt menu screen — and is finally left holding the subtitle animation
atlas, which is what the title tick expects to find (section 5).

After the acknowledgement screen finishes, the intro returns to its menu loop with intro state still active. A later `J`, `C`, or `T` selection is required to leave the intro.

Source provenance: derived from the private intro-overlay analysis notes under
`../u5-decomp/functions/INTRO_OVL/` and the private presentation analyses under
`../u5-decomp/notes/`.

## 12. Return to View (`R`)

`R` is a visual preview path for the intro view. It invokes a renderer in the font/display overlay family to run the non-interactive Return-to-View scene, then returns to the intro menu. It is not a saved-game resume command; saved-game resume is `J`.

When entered from the normal intro menu, the path preserves the underlying title/menu surface, runs the preview until its local script or input wait completes, then restores the preserved surface before menu polling resumes. The renderer loads `MISCMAPS.DAT` from the Return-to-View section: the first four records are **19-column by 4-row** map strips, and the following 655-byte stream drives preview actors, map-strip switches, movement, waits, and repeated animation beats. The file layout is specified in `formats/location-dat.md`.

**Orientation correction.** Earlier revisions of this section, and the earlier answers on the Return-to-View issue, called the strips 4 columns by 19 rows. That is transposed and is withdrawn. Each strip is four rows of nineteen columns, and the preview draws it as a wide, short band. The published `(x, y + 7)` coordinate rule is unaffected in form but must be read with `y` as the 0..3 **row** index: the `+ 7` moves the strip down the screen, it does not move it across.

The preview renderer uses the proportional-font overlay as a small intro-local
cinematic runtime. On entry it moves the viewport's pixel origin down by one
cell row, paints out the menu's top-border `Select:` caption and restores the
one-pixel rule beneath it, loads the preview data into the shared map scratch
area when needed, and then forces the intro scene byte into the Return-to-View
substate so repeated `R` entries do not reload the data unnecessarily. Entry
from the ordinary intro title page is wrapped by a screen-snapshot pair: the
active display mirror is copied to overlay scratch, the preview is drawn over
it, and the mirror is restored before menu polling continues. This snapshot is
presentation-only; no save state or gameplay mode is entered.

**Correction.** Earlier revisions said the renderer "switches to a
Return-to-View display state" and "configures the text rectangles used by the
chapter captions". Neither is accurate. There is no Return-to-View display
mode: the single value written at entry is the **viewport pixel Y origin**,
moved from 8 to 16 for the duration of the preview and restored to 8 when the
intro menu resumes. And the two rectangle calls that follow are not text-rect
configuration; they are a filled rectangle in user-interface colour slot 2 over
the top border's caption cells plus a one-pixel run in slot 1 underneath it,
which is how the `Select:` caption is erased while the preview runs.

### Preview geometry

The preview occupies the interior of the intro menu's lower text window and
nothing else. `formats/location-dat.md` section 11 is authoritative; the
summary an engine needs is:

| Quantity | Value |
|---|---|
| Cells | 19 across by 4 down, one 16-by-16 tile-archive cell each |
| Viewport pixel origin while the preview runs | `(8, 16)` |
| Screen tile row for strip row `y` | `y + 7`, i.e. rows `7..10` |
| Screen tile column for strip column `x` | `x`, i.e. columns `0..18` |
| Pixel rectangle covered | inclusive `(8, 128)..(311, 191)`, 304 by 64 pixels |

Nothing is scaled, cropped, clipped, or drawn through a separate miniature
raster; the preview uses the same 16-by-16 viewport tile entry the world view
uses. The window frame, the banner logo and the idle animation band above it
are untouched, and the six menu labels are simply covered while the preview
runs. An engine that computes a 64-by-304 preview has transposed the strip.

The preview area is **never cleared and never fully repainted**. Each preview
tick repaints only the cells inside the currently revealed column span, skipping
cells that a cell-effect command has marked as owned by another helper. Cells
outside that span keep whatever is already on screen.

### Strip reveal

A strip load does not expose the whole strip at once. The reveal cursor starts
on column 9 alone and widens by one column on each side on every second preview
tick. The widening happens at the end of a tick, after that tick's repaint, so
the span reaches its full `0..18` extent at the end of the **eighteenth**
preview tick and the outermost columns `0` and `18` are first painted on the
**nineteenth**. The span then stays open until the next strip load. All four
rows of a revealed column appear together. The per-tick table is in
`formats/location-dat.md` section 11.

**Correction.** A previous revision of this section retracted the outward
reveal as "stale, non-normative prose" and told engines that no reveal was
required. That retraction is itself withdrawn: the reveal is real and
normative. The only thing wrong with the original wording was the axis. It
expands outward along the **column** axis from the centre column, not from a
middle row. The reveal is a repaint-cursor effect: the strip load fills the
preview planes completely and immediately, and the cursor decides only which
columns reach the screen. Keypresses abort the preview at the ordinary
per-tick poll; there is no separate uninterruptible reveal phase.

Each map-strip transition selects one of four 19-column by 4-row preview
sections and renders a centered chapter caption. The command stream does not
carry a separate caption opcode or inline caption text; the caption is a fixed
function of the strip index. The exact strings, including capitalization and
the absence of trailing punctuation, are:

| Strip index | Caption |
|---:|---|
| `0` | `The Summoning` |
| `1` | `The Journey` |
| `2` | `The Arrival` |
| `3` | `The Welcoming` |

The strip index also selects the preview's ambient sound: strips `0` and `1`
are silent, strip `2` emits a random-pitch percussive speaker effect on every
preview tick, and strip `3` emits a two-tone chime on an eight-tick cycle. The
sound is the only per-strip difference in the tick; it changes nothing visible
and can be omitted by an engine that renders silently. See
`formats/location-dat.md` section 11.

### 12.1 The centered-caption helper

The caption does **not** use the proportional font or the proportional
paragraph renderer of `systems/text-output.md` section 8. It uses the ordinary
**fixed-cell** text printer, through the same helper that draws the
title-screen credit line, so the two share one geometry:

- Let `len` be the caption length in characters. The starting text column is
  `18 - floor(len / 2)`, and the helper also computes an end column
  `start_col + len + 2`. The division truncates, so odd lengths sit half a cell
  left of true centre.
- Centering is **horizontal only**. The caption row is the fixed text row `24`;
  there is no vertical centering inside a caption band and no configurable
  caption rectangle.
- Before the text, two filled rectangles are drawn in user-interface colour
  slot 2 (see `display-driver.md` section 2): one spanning `x = 8` to
  `start_col * 8` and one spanning `x = end_col * 8` to `x = 311`, both
  covering `y = 193` through `y = 199`. These repaint the window's bottom
  border either side of where the caption will sit, erasing whatever was there.
- Then, in user-interface colour slot 1, two single-pixel rows at `y = 192`
  over the same two horizontal spans. These are the rules that flank the
  caption; the caption interrupts them.
- Then the cursor is placed at column `start_col`, row `24`, the shared
  text-window border chrome is drawn, the caption is printed with the
  ordinary string printer, and the closing border chrome is drawn.

Those two chrome calls are what produce the wedges the caption sits between,
and they fix the caption's exact cells:

| Element | Column |
|---|---|
| Opening wedge (solid, pointing right) | `start_col` |
| Caption characters | `start_col + 1` through `start_col + len` |
| Closing wedge (the mirrored form, pointing left) | `start_col + len + 1` |
| First column past the caption group | `end_col = start_col + len + 2` |

So `end_col` is not the last caption cell; it is the first cell beyond the
closing wedge, which is why the right-hand repaint rectangle starts at
`end_col * 8` and the wedge cell is left untouched. For `The Summoning`
(`len = 13`) that gives an opening wedge at column `12`, caption text in
columns `13..25`, a closing wedge at column `26`, and a repaint rectangle
beginning at column `27` (`x = 216`). The two wedge cells are the shared
triangular bracket end-cap composite, not a rule and not a text character: an
opaque solid-triangle glyph followed by two **diagonal** accent strokes tracing
that triangle's hypotenuse, whose endpoints land on the cell's outer column at
its top and bottom rows. Because those rows are the rows the flanking rules
occupy, the rule appears to run continuously into the wedge; nothing horizontal
is drawn inside the wedge cell to achieve that. `display-driver.md` section 7
("Bracket end-caps") owns the composite and gives both stroke pairs; the
caption helper is only another caller. An alternative reading of the same
geometry, `start_col = (40 - (len + 2)) / 2`, produces identical columns for
every shipped caption; both forms are correct.

There is no shadow pass, so nothing about shadow pixels affects centering.
Because the caption is printed by the fixed-cell printer it uses that printer's
active window colour, not a caption-specific attribute.

**Draw order.** The caption is emitted by the strip-load helper at the very
start of a chapter transition: caption first, then the 19-column by 4-row strip
is copied into the preview planes, then the reveal cursor is reset. It
therefore precedes every per-frame tick of that chapter, including the
per-frame title tick and the preview actor overlay. The caption is not redrawn
per frame; it persists until something else paints over that row.

Command `0x06` fills the preview planes completely and immediately, as one
script action. The **reveal is a separate, repaint-side effect** described
above: the planes are full from the moment the strip loads, and the cursor
controls only which columns are painted onto the screen on each subsequent
tick. Static terrain cells live in the preview terrain plane, moving preview
actors are scattered from the shared active-object table into the overlay plane
on every tick, and a cell is drawn from its terrain byte when that byte is
non-zero and from its overlay byte otherwise. The per-frame tick also runs the
ordinary active-object animation step and the intro title tick before drawing
the preview cells, so actor animation and the title/menu visual cadence stay in
the same timing family even though gameplay time is not advancing.

The loaded command stream is interpreted as a compact sixteen-command bytecode
for this cinematic only. Its commands create, delete, move, teleport, and clear
preview actors; switch to a new strip section and its fixed caption; run short
sprite-walk and cell-effect loops; run a fixed wipe/actor-draw beat; run a
requested number of preview ticks; and repeat blocks of commands. There is no
wait-for-keypress command: waiting is a side effect of running preview ticks,
and every tick polls the keyboard once. Any pending key aborts the preview at
that poll, immediately, abandoning the rest of the tick count the current
command asked for; the caller then restores the title/menu surface. There is no
uninterruptible phase and no key with a special meaning. A command-stream
restart command remains local to the preview and never resumes a saved game.

Two cell effects have stronger pixel-level contracts than the ordinary preview
repaint. The open/close effect paints fifteen complete 16-by-16 rasters made by
splicing an increasing or decreasing number of portal-tile rows into the
bottom of the base terrain tile; it restores its temporary loaded-tile scratch
after every raster. Temporary actor draws instead replace one pixel at a time
in a fixed 256-position permutation, running a full preview tick and keyboard
poll after each completed group of eight except the final group. These effects
write palette index zero opaquely. Their exact raster formula, permutation,
31-checkpoint schedule, and non-transactional abort state are specified in
`formats/location-dat.md` section 11 and `display-driver-abi.md` sections 9.6
and 10.

The control-flow contract is clear: run the preview as an intro-local screen, keep the intro scene active, do not load or resume a save, and continue polling the six-option menu afterward. The preview command-byte table, argument shapes, loop rule, actor/map side effects, and fixed script-level helper schedules are specified in `formats/location-dat.md`. Asset-compatible tooling that does not implement the preview interpreter should still preserve the command stream unchanged.

## 13. Hand-off back to gameplay

Only the load path should cause the intro overlay to return in a gameplay-ready state:

- `J` returns after a valid save has been loaded.
- `C` returns to the intro menu after writing a save; the later `J` is what enters gameplay.
- `T` follows the same visible contract as `C`: a successful transfer writes a save and redraws the intro menu, and the later `J` load is what enters gameplay.

On a successful hand-off, the intro leaves resident state arranged so the main loop can do its ordinary scene dispatch. The scene byte is part of the save image, so a loaded game resumes in the same high-level mode in which it was saved. The intro does not directly invoke overworld, town, or dungeon turn loops as part of the load. It returns and lets the main loop route.

This keeps the boot architecture consistent with all later scene transitions: systems set state and return, and the main loop decides which mode owns control next. See `main-loop.md` for the outer dispatch rules and `save-load.md` for the load path's final commit.

## 14. Implementation notes

A modern implementation does not need to reproduce the overlay loader, DOS interrupt setup, or disk-swap callbacks literally. It should preserve their user-visible contracts:

- Initialise display, text windows, input, timing, and file I/O before drawing the first title/menu frame.
- Select one graphics depth/backend for the whole intro session.
- Treat disk-swap prompts as file-availability prompts; on a single-directory install they can be no-ops.
- Keep intro input one-keystroke-at-a-time and case-insensitive.
- Suppress gameplay world ticks while the intro is active; only the intro title
  tick continues during title/menu waits.
- Make every non-play submenu return to the intro menu without mutating gameplay state.
- Make the Journey load path validate the save before leaving the intro.
- Route successful gameplay entry through the main-loop scene dispatcher.

For pixel-perfect reproduction, an implementation should preserve the step-1
story rectangle's pseudo-random per-pixel dissolve (section 10) rather than any
column-by-column reveal, and the Return-to-View preview's centre-outward column
reveal (section 12). Earlier revisions of this paragraph asked for a "36-tick
left-to-right reveal" on step 1; that was based on a withdrawn reading and must
not be implemented. The title/menu idle contract is narrower: run the
driver-style title tick while waiting, and keep that tick separate from
gameplay time.

## 15. Intro Boundaries And Remaining Visual Parity Work

The intro/menu/story contract is complete at gameplay and user-flow depth:
boot-time setup, title/menu input, signature path playback, story slide
sequencing, acknowledgement/menu ownership, Journey load handoff, transfer
handoff, and Return-to-View preview ownership are all specified here or in the
linked save/load, transfer, and display contracts. The remaining work is not
needed for a clean implementation to enter gameplay correctly; it is exact
historical-renderer parity work.

- **Return-to-View resident helper internals.** Closed. The `R` path's owner,
  asset layout, strip orientation, command-byte table, argument shapes, loop
  rule, actor/map side effects, local cell-effect step loops, fixed rectangle
  sequence, preview tick counts, framebuffer geometry, per-frame repaint policy
  and column reveal are specified in section 12 and in
  `formats/location-dat.md` section 11. The helpers turned out to be ordinary
  published driver entries rather than private ones: the 16-by-16 viewport tile
  blitter draws both preview cells and actors, the animated-terrain shimmer
  entry drives the local cell effect, and the pixel-dissolve entry driven one
  cell at a time performs the temporary actor draws. The "short fixed wait"
  after the fixed wipe was a misreading of a speaker call and is withdrawn.
  The shimmer's exact per-step row splice and the temporary actor draw's exact
  256-pixel permutation, input cadence, and abort state are now published in
  `formats/location-dat.md` section 11 and `display-driver-abi.md`. There is no
  remaining Return-to-View resident-helper raster gap for EGA/Tandy.
- **Story rectangle-transition helper.** Closed for the intro. The fixed
  story-step list, primary story-art placement, secondary draws, text source,
  key-advance behaviour, and the step-1 rectangle transition are specified in
  section 10. The step-1 effect is the driver's pseudo-random per-pixel
  dissolve, not a left-to-right column reveal; the earlier "left-to-right
  reveal" wording in this bullet is withdrawn. A focused slide-loop caller
  census found no other story-page transition rectangles, so step 1 is the only
  story-sequence dissolve.
  **Correction.** An earlier revision of this bullet said there were exactly
  two non-story callers sharing the dissolve entry, and described the endgame
  one as a surface clear. Both claims were wrong. A whole-program census of the
  dissolve entry finds six call sites: the two intro ones specified in section
  10, one in the endgame that is a genuine full-screen dissolve and not a clear
  (`endgame.md` section 7.1), and three map-viewport ones outside the intro and
  endgame entirely. The full list lives in `display-driver-abi.md` section 9.6,
  which is where new callers should be recorded; the three map-viewport sites
  are caller-specified in `blackthorn.md` section 7 and `dungeon-mode.md`
  section 8.
- **Acknowledgement screen content.** Closed. The acknowledgement page is a
  pre-rendered three-record image band, not typeset text, so there is no text
  transcription, font path, or pagination to publish. Its asset, record sizes,
  placement, four-phase wipe geometry, input rule, and backing-surface
  behaviour are specified in section 11.
- **Title tick art.** Closed. The destination rectangle, four-frame cadence,
  staging layout, and source records are all specified in section 5: the frames
  are records `1..4` of the `ULTIMA` banner archive, staged into the driver's
  hidden surface at a 50-row band pitch. No replacement art and no driver-binary
  reuse are needed. The only residual is the alternate-driver question below:
  the CGA, Hercules, and Tandy builds stage the equivalent `.4` records, and
  their exact pixel conversion is separate hardware-parity work. The `.4` twin
  of the `ULTIMA` archive holds the same five records with one difference — its
  record `4` is `288 x 49` rather than `288 x 50`. The band pitch is a driver
  constant rather than a record height, so on the four-colour (CGA) path — which
  keeps the 50-row pitch, 49 copied rows and destination row `65` of the EGA
  baseline — the last source row of band `3` is simply background. The pitch is
  **not** 50 on every backend: the Hercules driver uses its own band geometry,
  published in `display-driver.md` section 8 ("Per-driver title-band geometry").
  Earlier wording here generalised the 50-row pitch to the whole `.4` path and
  is withdrawn.
- **Flourish wall-clock.** The `TITLE.BIT` flourish's step count, per-step
  content, and pacing mechanism are specified (section 3, `timing.md` section
  5.1). The remaining gap is a measured wall-clock figure for one presentation
  step on period hardware; the published figure is derived from the calibration
  contract rather than from a timed capture.
- **Alternate display-driver entries.** The EGA dispatch surface for rectangle
  fill, driver-compressed bitmap resources, and title ticks is specified in
  `display-driver-abi.md`. Exact CGA, Hercules, and Tandy conversion details
  remain alternate-hardware parity work.

## 16. Sources

The behaviour described here was derived by reading the private function and
format notes for the modules listed below. Those notes' assembly excerpts,
decompiled code, private addresses, private function labels, and binary text
dumps do not appear in this spec; this document is a cleanroom prose
re-derivation of the observed behaviour, and provenance is cited by note
directory rather than by individual note, so that nothing here doubles as an
index into private analysis.

Private analysis directories consulted:

| Area | Provenance directory |
|---|---|
| Boot, title orchestration, start/menu screen loading and composition, menu rendering, key dispatch, acknowledgements page, story slide loop, Journey Onward load path, transfer/continue path | `u5-decomp/functions/INTRO_OVL/` |
| Resident title-mark flourish presenter, display-driver loading and mode setup, font loading and active-font selection, text-window descriptor initialisation, text output and cursor-poll primitives, compressed-bitmap draw, game-screen frame, outer main loop | `u5-decomp/functions/ULTIMA_EXE/` |
| Driver-side presentation: the calibrated delay-with-animation-step entry, the one-bit silhouette stamp, the directional full-screen buffer copy in both its publish and seed directions, filled rectangle, compressed-bitmap draw, and the pseudo-random pixel dissolve in both its plain and carry-set forms | `u5-decomp/functions/EGA_DRV/` |
| Proportional-font paragraph renderer, character creation, Return-to-View preview runtime and its map-strip loader | `u5-decomp/functions/FONT_OVL/` |
| Cross-cutting retraces: the visible phase order and per-phase ink, the flourish's presentation script and its verification, the four `BRITISH.PTH` pen origins, the free-running band-frame counter, the two-pass masked subtitle reveal, the menu window's drawing passes, the dissolve-entry caller census, the Return-to-View pixel geometry and command schedule, and the paragraph-box retrace | `u5-decomp/notes/` |
| Container and data-file formats: the paired graphics archives, the one-bit bitmap family, `BRITISH.PTH` as a title-screen path stream rather than an NPC schedule, the EGA driver's own layout, and the shared data overlay's string tables | `u5-decomp/formats/` |

Two conclusions in this document rest on a caller census rather than on a single
note, and are recorded as such: the rectangle-dissolve entry has exactly two
intro call sites and four outside the intro; and the `C` key enters character
creation in the proportional-font overlay and returns directly to the intro
menu without chaining through the spell-casting overlay.

Every literal string, column origin, cell span, corner-glyph ink profile,
record dimension and record count published above was re-checked directly
against the shipped data files before publication, independently of the notes.
Earlier revisions of this section attributed some findings to unrecorded "fresh
local verification"; those attributions are withdrawn in favour of the recorded
retraces above.
