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
blanked. The fill direction alternates by frame: frames are filled top-down and
bottom-up on alternating frames, which is why the mark appears to unfold from
opposite edges as it grows. The visible result is an expanding venetian-blind
reveal followed by the reverse collapse, not a simple row-by-row wipe.

Rows are copied and blanked at the **full 320-pixel screen width**, not at the
mark's own width. The band a presentation owns is therefore the inclusive
rectangle `(0, band top)..(319, band top + height - 1)`, and the mark's
horizontal position inside it is simply the centred X it was stamped at in the
hidden surface. A renderer that clips the repaint to the mark's width will
leave stale pixels beside it.

Because each frame's band is a different rectangle, the erase pass is what
removes the previous frame's pixels from the rows the next frame does not
cover. A renderer that skips the erase steps must clear the outgoing band
before drawing the incoming one.

A keystroke aborts the flourish at the current presentation step; the intro then
proceeds directly to the overlay draws below.

The EGA baseline is not a normal white-on-black foreground blit. The helper
stamps 1-bit source pixels into the hidden driver surface, and the animation
player copies only the blue and intensity planes to the visible page. Treat set
source pixels as palette index `9` on the black title background for this
initial flourish. There is no XOR, inverse, alpha, or source sub-rectangle mode
for slots `0..6`; each source slot is consumed from its own `(0, 0)` origin for
its full documented width and height before the driver presentation script
chooses which rows to show.

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
   keystroke.
3. Clear the whole hidden surface, stamp `TITLE.BIT` slot `8` at `(152, 0)`,
   and publish the whole surface. This is the point at which the title mark and
   the slot-7 line disappear: the visible page becomes black except for the
   small slot-8 ornament at the top.
4. Draw the four `BRITISH.PTH` signature path segments, in order, from pen
   origins `(68, 44)`, `(94, 64)`, `(78, 143)`, and `(105, 167)`. These strokes
   are painted **directly onto the visible page**, over the slot-8 ornament, and
   are not stamped into the hidden surface.
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
8. Select the visible page, run one title tick, and clear the intro text window
   so the menu frame and labels can be drawn over the lower screen.

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
`R` Return to View. This is why the menu remains visually alive without
advancing any saved-game state, and why the Return-to-View preview can start
after a long unattended menu idle.

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

Frame-perfect replacement behaviour can be implemented as:

```text
state title_frame = 0        ; initialised when the intro renderer/driver is created

clear_carry_title_tick():
    draw idle_frame[title_frame] to pixels x=0..319, y=65..113
    title_frame = (title_frame + 1) mod 4
```

The frames use the active 16-colour EGA-compatible palette indices directly.
Do not alpha-blend, scale, dither against the previous screen, or treat any
palette index as transparent. Palette index `0` pixels overwrite the
destination as black.

The carry-set title helper is a different operation and is not the public
frame-advance. It takes a loaded one-bit-per-pixel resource as its argument and
plays the subtitle ignition transition described in section 3: it saves the
hidden surface, clears it, runs a pseudo-random pixel reveal that interleaves
idle-strip steps with a percussive sound effect, and then restores the hidden
surface. Its only intro caller passes `WD.BIT`, and it runs exactly once, on
the animated start/menu path. Only the clear-carry title tick advances the
four-frame idle strip.

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

The intro menu is a six-entry key menu. It is rendered after the title/start screen is ready and remains the controlling loop until a valid Journey Onward load returns to the main loop or the process exits by another path. Keys are folded to uppercase before dispatch, matching the input-system contract in `input.md`.

The accepted keys are:

| Key | Menu action | Result |
|---|---|---|
| `J` | Journey Onward | Load the active save and return to the main loop if valid. |
| `C` | Create New Character | Enter character creation through the proportional-font/chargen flow. |
| `T` | Transfer from Ultima IV | Enter the transfer/roster path and commit or abort from there. |
| `U` | Ultima V Introduction | Play the story slide sequence, then return to the intro menu. |
| `A` | Acknowledgements | Show credits/acknowledgements, then return to the intro menu. |
| `R` | Return to View | Run the non-interactive Return-to-View preview, restore the menu surface, then remain in intro mode. |

### 6.1 Lower text-window frame

The lower intro text-window frame is drawn after the one clear-carry title tick
and before the six menu labels. It is a single-line rectangle composed of the
intro's fixed-cell box-drawing glyphs (the five-glyph corner/edge set the font
file reserves for that purpose) and a thin horizontal rule beneath the top
border row.

| Property | Value |
|---|---|
| Anchor cell | column `0`, row `15` |
| Width | 40 text cells (full screen width, columns `0..39`) |
| Height | 10 text cells (rows `15..24`, inclusive), giving pixel rows `120..199` |
| Top border row | row `15`: top-left corner glyph, 38 top-edge glyphs, top-right corner glyph |
| Side rows | rows `16..23`: left-edge glyph at column `0`, right-edge glyph at column `39`, interior preserved for menu and message text |
| Bottom border row | row `24`: bottom-left corner glyph, 38 bottom-edge glyphs, bottom-right corner glyph |
| Glyph colour | the intro's bright foreground palette index, applied as the current text attribute |
| Glyph set | the fixed-cell font's reserved corner-and-edge codes for the menu window; the same five-glyph set used elsewhere in the intro for boxed text |

The bottom-right corner glyph is emitted with the text-attribute "inverse" flag
briefly cleared so that the corner is drawn in plain foreground colour even
when the surrounding cells are inverse-video. The flag is restored immediately
after the corner glyph.

After the corner-and-edge pass completes, the intro emits one thin horizontal
rule through the display driver's line primitive at pixel `y = 127`, spanning
columns `7..312` in the current intro foreground colour. The rule lies inside
the top border row's eight-pixel cell, immediately under the top-edge glyph
row; the intro then issues two short horizontal fills below that rule to
finish the underline detail.

The frame does not clear the interior cells. The preceding intro display
clear, the start/menu screen paint, and the title tick are the steps that establish
the interior pixels; the frame's job is the border and underline, not the
fill.

For the no-active-save message, the intro reuses the same window. The message
is written into the interior cells through the normal text-output path
(which clears each output cell as it draws), waits for one keystroke, and
returns to the menu polling loop. The frame itself is not redrawn between the
message and the menu labels; the rectangle established here remains visible
through the entire intro menu lifetime.

### 6.2 Menu labels

The menu labels are rendered as fixed-cell text inside the intro menu window,
after the start/menu screen and the lower window frame have been drawn. The
labels appear
in this order and at these text-cell origins:

| Row | Key | Label | Text-cell origin |
|---:|---|---|---|
| 0 | `J` | Journey Onward | column 12, row 17 |
| 1 | `C` | Create New Char. | column 9, row 18 |
| 2 | `T` | Transfer from U4 | column 8, row 19 |
| 3 | `U` | Ultima V Intro. | column 9, row 20 |
| 4 | `A` | Acknowledgements | column 11, row 21 |
| 5 | `R` | Return to View | column 10, row 22 |

Each label is emitted with one leading and one trailing blank around the
label text at that origin. When a row is highlighted, the text output layer's
inverse-video toggle is emitted before that line and again after it, so the
highlight is a text-attribute effect over the same label placement. Dispatch
is still by key, not by row index; the row number only controls presentation.

Invalid keys are ignored and the menu continues polling. An invalid nonzero
key does not run the title-strip tick for that key pass; the menu highlight is
redrawn and polling resumes. The menu also keeps a short recent-selection cache
for repeat-by-Enter behaviour; pressing Enter can reuse a cached menu
selection while the intro menu remains active. If there is no cached
selection, Enter behaves like any other ignored key.

Behaviourally, the player sees a stable six-option menu that waits for one of
the accepted keys and returns to that same menu after non-play sub-screens
finish.

While the menu waits, the intro continues to run its lightweight title tick
only on no-key poll passes, and after two hundred consecutive no-key passes it
enters the Return-to-View preview as if `R` had been selected. This is separate
from the gameplay world tick. No gameplay time advances while the intro menu is
active because no gameplay mode has started.

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

Steps 1 through 5 prepare the display for gameplay before any save data is read. The game-screen frame is drawn first so the player sees the gameplay viewport appear while the save loads. The frame consists of the left viewport area, the right stats panel with horizontal subdividers, and the bottom command-prompt area, formed by filled rectangles and box-drawing corner glyphs. This is the same screen layout used by overworld, town, dungeon, and combat modes.

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
3. Loads a U5 Britannia seed image and object-overlay seed used as the destination baseline.
4. Renders a character-roster/status screen showing party slots and statistics.
5. Polls for transfer confirmation, abort, or follow-up input.
6. On abort, restores intro/menu state and returns to the menu.
7. On commit, writes the normal save files, restores the intro/menu state, redraws the start/menu screen, and resumes menu polling.

The U4-to-U5 character-field translation is specified in
`systems/u4-transfer.md`. It belongs with the transfer spec because it
determines the contents of the resulting save, not the intro menu's control
flow. The roster-preview and disk-swap behaviour are included here because the
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
it runs to completion as a blocking local effect.

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
path, but it does not interrupt the transfer itself. The plain caller path
copies the same rectangle in one step with no animation. Fixed `END.DAT` and
other ordinary bitmap-window callers do not inherit this contract; their clear,
page-in, border redraw, and wait timing remain caller-owned presentation
details.

### 10.1 Step 6: the inline doorway lines

Step 6 is the one step whose narrative text is not a `STORY.DAT` record. Its
full contract:

**Text.** Two lines, each a single plain sentence, rendered in this order:

1. `Instantly, a shimmering blue door springs up!`
2. `With heart beating rapidly, you step into it.`

Both are 44 characters long. Neither contains a paragraph-indent brace, a
soft-hyphen underscore, a line feed, or any other renderer marker; each is
ordinary text terminated by a NUL. An implementation must not add the markers
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

Source provenance: derived from private analysis note
`../u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.

### 10.2 Boundaries

The slide loop does not mutate gameplay state, does not create a save, and does not select a gameplay scene. Its only persistent effect is that, when it returns, the intro reloads or redraws the start/menu view so the six-option menu can continue.

The screen-panel asset container is specified in `formats/tiles.md`. The proportional text output contract is described in `text-output.md`, and the story text file is specified in `formats/story-dat.md`.

## 11. Acknowledgements (`A`)

`A` displays the acknowledgement/credits screen and then returns to the intro menu. It uses the same already-initialised display and text systems as the title and story paths. The acknowledgement path is self-contained: it does not read or write the save image, does not change the gameplay scene, and does not exit the program.

### 11.1 The acknowledgement page is artwork, not text

The acknowledgement screen is a **pre-rendered image page**. Its credit lines
are drawn into the bitmap; the handler never selects a font, never sets a text
rectangle, never emits a printable character, and never changes a palette or
text attribute. There is consequently no font path, no per-line layout, no
text colour or inverse behaviour, no pagination, and no per-page input rule to
specify. An implementation reproduces this screen by drawing the shipped
artwork; it must not attempt to typeset the credits from strings.

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
| 2 | Right ornamental pillar (mirror of record 0) | 16 x 137 |

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
   5. wait one presentation beat.

   The pillars walk outward to `(0, 63)` and `(304, 63)` while two
   eight-pixel-wide bands expand from the screen centre and publish the
   credits page column by column. The last step's bands are `16..23` and
   `296..303`, which exactly meet the resting pillars, so the completed band
   is contiguous.
6. Rebuild the menu screen on the hidden surface while the credits are still
   displayed: load the `ULTIMA` archive, select the hidden surface, clear it,
   draw `ULTIMA` record `1` at `(16, 65)` (the first subtitle animation
   phase), release the archive, draw the lower intro text-window frame
   (section 6.1), and render the six menu labels with the Acknowledgements row
   highlighted (section 6.2).
7. Poll the keyboard until any key is returned. **Any key advances; `Esc` has
   no special meaning here.** There is no timeout, no timed auto-advance, and
   no second page.
8. Select the visible page. **Close phase**, the mirror of step 5. For
   `k = 136, 128, ... 8, 0` (eighteen steps): draw record `0` at
   `(144 - k, 63)`; copy `(136 - k, 63)..(143 - k, 199)` from the hidden
   surface; draw record `2` at `(160 + k, 63)`; copy
   `(176 + k, 63)..(183 + k, 199)` from the hidden surface; wait one
   presentation beat. The pillars walk back to the centre while the rebuilt
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
    and draw `ULTIMA` records `1`, `2`, `3`, `4` at `(16, 0)`, `(16, 50)`,
    `(16, 100)` and `(16, 150)`.
12. Select the visible page, flush the keyboard type-ahead buffer, and return
    to the menu poll loop.

### 11.3 Backing-surface contract

No pixel above row `63` is written on either surface at any point in this
path. The `ULTIMA` logo occupying rows `0..60` of the visible page is simply
never touched, so it remains on screen throughout the credits. Rows `63..199`
are overwritten by the credits band and then rebuilt from the hidden surface;
nothing of the previous menu screen is saved or restored. The hidden surface
is repurposed twice — first for the credits page, then for the rebuilt menu
screen — and is finally left holding the subtitle animation atlas, which is
what the title tick expects to find (section 5).

After the acknowledgement screen finishes, the intro returns to its menu loop with intro state still active. A later `J`, `C`, or `T` selection is required to leave the intro.

Source provenance: derived from private analysis notes
`../u5-decomp/functions/INTRO_OVL/0x072E_ack_render.md`,
`../u5-decomp/functions/INTRO_OVL/0x05B0_startsc_loader.md`, and
`../u5-decomp/functions/INTRO_OVL/0x0010_four_row_helper.md`.

## 12. Return to View (`R`)

`R` is a visual preview path for the intro view. It invokes a renderer in the font/display overlay family to run the non-interactive Return-to-View scene, then returns to the intro menu. It is not a saved-game resume command; saved-game resume is `J`.

When entered from the normal intro menu, the path preserves the underlying title/menu surface, runs the preview until its local script or input wait completes, then restores the preserved surface before menu polling resumes. The renderer loads `MISCMAPS.DAT` from the Return-to-View section: the first four records are 4-column by 19-row map strips, and the following 655-byte stream drives preview actors, map-strip switches, movement, waits, and repeated animation beats. The file layout is specified in `formats/location-dat.md`.

The preview renderer uses the proportional-font overlay as a small intro-local
cinematic runtime. It switches to a Return-to-View display state, configures the
text rectangles used by the chapter captions, loads the preview data into the
shared map scratch area when needed, and then forces the intro scene byte into
the Return-to-View substate so repeated `R` entries do not reload the data
unnecessarily. Entry from the ordinary intro title page is wrapped by a
screen-snapshot pair: the active display mirror is copied to overlay scratch,
the preview is drawn over it, and the mirror is restored before menu polling
continues. This snapshot is presentation-only; no save state or gameplay mode
is entered.

Each map-strip transition selects one of four 4-column by 19-row preview
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
- Before the text, two filled rectangles are drawn in the first configured
  chrome colour: one spanning `x = 8` to `start_col * 8` and one spanning
  `x = end_col * 8` to `x = 311`, both covering `y = 193` through `y = 199`.
  These are the horizontal rules that flank the caption.
- Then, in the second configured chrome colour, two single-pixel rows at
  `y = 192` over the same two horizontal spans.
- Then the cursor is placed at column `start_col`, row `24`, the shared
  text-window top border chrome is drawn, the caption is printed with the
  ordinary string printer, and the bottom border chrome is drawn.

There is no shadow pass, so nothing about shadow pixels affects centering.
Because the caption is printed by the fixed-cell printer it uses that printer's
active window colour, not a caption-specific attribute.

**Draw order.** The caption is emitted by the strip-load helper at the very
start of a chapter transition: caption first, then the 4-by-19 strip is copied
into the preview buffers, then the strip-animation state is reset. It therefore
precedes every per-frame tick of that chapter, including the per-frame title
tick and the preview actor/tile overlay. The caption is not redrawn per frame;
it persists until something else paints over that row. Command `0x06` loads the
selected 4-by-19 strip into the preview buffers as one script action; the public
clean contract does not require a middle-row outward reveal mask. Static terrain
cells are copied into the active 32-by-32 preview tile planes, while moving
preview actors use the shared active-object table and are scattered into the
overlay plane each frame. The per-frame tick also runs the ordinary
active-object animation step and the intro title tick before drawing the
preview cells, so actor animation and the title/menu visual cadence stay in the
same timing family even though gameplay time is not advancing.

The loaded command stream is interpreted as a compact sixteen-command bytecode
for this cinematic only. Its commands create, delete, move, teleport, and clear
preview actors; switch to a new strip section and its fixed caption; run short
sprite-walk and cell-effect loops; run a fixed wipe/actor-draw beat; wait for
keypress; and repeat blocks of commands. Any keypress observed by the wait/tick
path exits the preview and restores the title/menu surface. A command-stream
end or restart command remains local to the preview and never resumes a saved
game.

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
story rectangle's 36-tick left-to-right reveal and any still-unspecified
resident helper behaviour for other sub-screens. The title/menu idle contract
is narrower: run the driver-style title tick while waiting, and keep that tick
separate from gameplay time.

## 15. Intro Boundaries And Remaining Visual Parity Work

The intro/menu/story contract is complete at gameplay and user-flow depth:
boot-time setup, title/menu input, signature path playback, story slide
sequencing, acknowledgement/menu ownership, Journey load handoff, transfer
handoff, and Return-to-View preview ownership are all specified here or in the
linked save/load, transfer, and display contracts. The remaining work is not
needed for a clean implementation to enter gameplay correctly; it is exact
historical-renderer parity work.

- **Return-to-View resident helper internals.** The `R` path has a traced owner,
  asset layout, command-byte table, argument shapes, loop rule, actor/map side
  effects, local cell-effect step loops, fixed rectangle sequence, and preview
  tick counts. A frame-for-frame preview still needs the low-level resident
  display helper behavior behind special actor drawing, local cell-effect
  rasterization, and the short fixed wait.
- **Story rectangle-transition helper.** The fixed story-step list, primary
  story-art placement, secondary draws, text source, key-advance behavior, and
  step-1 left-to-right rectangle reveal are specified. A focused slide-loop
  caller census did not find additional story-page column-wipe rectangles.
  Remaining parity work is limited to independently traced non-story intro
  presentation helpers or endgame display helpers, not an inferred story-page
  table.
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
  their exact pixel conversion is separate hardware-parity work.
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

The behaviour described here was derived by reading the function and format notes listed below. None of those notes' assembly excerpts, decompiled code, private addresses, or binary text dumps appear in this spec; this document is a cleanroom prose re-derivation of the observed behaviour.

- Boot initialisation, title-screen orchestration, asset-depth selection, intro menu rendering, key dispatch, and the high-level hand-off to the main loop: `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Pre-flourish phase composition (driver-ready probe, IBM/RUNES glyph
  asset loading by driver, active-font selection, text-window descriptor
  reset, driver-descriptor selection, and the early Journey Onward
  single-poll shortcut): `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x1D02_load_font_into_slot.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x1C9E_select_active_font.md`.
- Start/menu screen loading, `ULTIMA` banner composition, the dissolve reveal, the idle-band staging layout, lower intro text-window redraw, and fixed menu-entry placement: `u5-decomp/functions/INTRO_OVL/0x05B0_startsc_loader.md`, `u5-decomp/functions/INTRO_OVL/0x0010_four_row_helper.md`, `u5-decomp/functions/INTRO_OVL/0x04E0_clear_intro_text_window.md`, `u5-decomp/functions/INTRO_OVL/0x0676_menu_entry_render.md`, `u5-decomp/functions/INTRO_OVL/0x06BC_menu_render.md`, and `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`.
- Acknowledgement/credits page asset, record roles and sizes, four-phase wipe
  geometry, any-key advance, menu rebuild on the hidden surface, and the
  untouched upper band: `u5-decomp/functions/INTRO_OVL/0x072E_ack_render.md`.
- Lord British signature path consumption, four-segment walking, pen movement, pen-up semantics, and keyboard skip behaviour: `u5-decomp/functions/INTRO_OVL/0x0050_pth_walker.md`.
- Title-mark helper sequencing for `TITLE.BIT` slots `0..6`, the resident
  width/height tables behind the hidden-source stack, the seven-frame
  presentation script with its per-frame source/destination/height triples and
  eight row-reveal groups, the packed-and-centred band repaint, the
  two-plane palette-index-9 rule, the lower-band clear, and the explicit
  slot `7`, slot `8`, `BRITISH.BIT` slot `0`, and slot `9` overlay order with
  its whole-page publishes:
  `u5-decomp/functions/ULTIMA_EXE/0x0D72_title_flourish_player.md`,
  `u5-decomp/functions/EGA_DRV/0x1DE8_delay_with_animation_step.md`,
  `u5-decomp/functions/EGA_DRV/0x190E_silhouette_stamp_back_buffer.md`,
  `u5-decomp/functions/EGA_DRV/0x098A_back_buffer_invalidate.md`,
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`,
  `u5-decomp/formats/ega-driver.md`, and
  `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`.
- Story slide loop, story-art loading, proportional-font text rendering, slide wait/advance behaviour, the step-1 rectangle-transition handoff, and return-to-menu path: `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md` and `u5-decomp/functions/EGA_DRV/0x256B_lfsr_pixel_dissolve.md`.
- Return-to-View chapter caption strings, the centered-caption helper's column
  arithmetic, flanking-rule rectangles, caption row, and draw order relative to
  the strip copy and per-frame ticks:
  `u5-decomp/functions/INTRO_OVL/0x043E_print_centered_credit.md`,
  `u5-decomp/functions/FONT_OVL/0x0418_load_world_section.md`, and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 2.4.
- Return-to-View entry point, preview bytecode runtime, preview map-strip
  loader, per-frame active-object animation bridge, per-cell tile rendering,
  helper schedules, and screen save/restore behaviour:
  `u5-decomp/functions/FONT_OVL/_OVERVIEW.md`,
  `u5-decomp/functions/FONT_OVL/0x04A4_return_to_view.md`,
  `u5-decomp/functions/FONT_OVL/0x0418_load_world_section.md`,
  `u5-decomp/functions/FONT_OVL/0x02FC_animate_overworld_tick.md`,
  `u5-decomp/functions/FONT_OVL/0x02A2_render_entity_tile.md`,
  `u5-decomp/functions/FONT_OVL/0x0E52_screen_save.md`, and
  `u5-decomp/functions/FONT_OVL/0x0E7B_screen_restore.md`.
- Title tick ownership, EGA destination rectangle, four-frame cadence, the
  `ULTIMA` record `1..4` frame source and its 50-row staging pitch, the
  carry-set subtitle-ignition variant, signature delay/poll separation, and the
  clarification that `FLAMES.OVL` is a scratch-buffer thunk, not the flame
  renderer: `u5-decomp/functions/INTRO_OVL/0x2090_title_tick.md`,
  `u5-decomp/functions/INTRO_OVL/0x0010_four_row_helper.md`,
  `u5-decomp/functions/EGA_DRV/0x282D_animate_flames_strip.md`,
  `u5-decomp/functions/INTRO_OVL/0x094E_iter_until_kbd.md`,
  `u5-decomp/functions/FLAMES_OVL/0x0000_flames_entry_stub.md`,
  `u5-decomp/formats/ega-driver.md`, and
  `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`.
- Filled-rectangle dispatch, corrected driver-compressed bitmap dispatch, and
  driver-side title/bitmap rendering relationship:
  `u5-decomp/functions/ULTIMA_EXE/0x0AA6_draw_compressed_bitmap.md`,
  `u5-decomp/functions/EGA_DRV/0x1180_fill_rect_v2.md`, and
  `u5-decomp/functions/EGA_DRV/0x1226_draw_compressed_bitmap.md`.
- Journey Onward load path, pre-load game-screen-frame draw, empty-save guard, `SAVED.GAM` and `SAVED.OOL` reads, object-overlay mirror writes, underworld disk-swap branch, and final return to the main loop: `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md` and `u5-decomp/functions/ULTIMA_EXE/0x637E_combat_screen_layout.md` (renamed to `draw_game_screen_frame` 2026-05-24).
- Character-creation chain verification: the `C` key enters `chargen_main` in the proportional-font overlay and returns directly to the intro menu. The chargen routine is self-contained and does not chain through the spell-casting overlay. Verified via `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` callee list (2026-05-24).
- Transfer/continue roster path, transfer disk-state setup, seed loads, roster/status screen rendering, and commit/abort behaviour: `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Outer main-loop boot context, scene dispatch after intro return, and overlay call model: `u5-decomp/functions/ULTIMA_EXE/0x0000_main_game_loop.md`.
- Display-driver loading and initial mode setup: `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- Text-window descriptor initialisation and text output primitives used by intro screens: `u5-decomp/functions/ULTIMA_EXE/0x1184_init_text_descriptor_table.md`, `u5-decomp/functions/ULTIMA_EXE/0x1850_print_string.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`.
- `BRITISH.PTH` file structure and its confirmation as a title-screen path stream rather than an NPC schedule file: `u5-decomp/formats/npc-tlk-pth.md`.
- Title, start-screen, and story-panel graphics container format: `u5-decomp/formats/tile-graphics.md`.
- Story text data observations used to identify the intro slide text source: `u5-decomp/formats/data-tables.md`.
- The visible title sequencing and the four `BRITISH.PTH` pen origins were
  re-derived and recorded in
  `u5-decomp/notes/intro_title_flourish_and_flames_2026-08-22.md`; no code,
  disassembly, or raw data is reproduced here. That note supersedes the
  unrecorded "fresh local verification" attributions that earlier revisions of
  this section used.
