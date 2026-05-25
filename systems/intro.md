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
2. Render the initial title/rune text appropriate to the active driver.
3. Load the title and Lord British artwork resources.
4. Run the seven-step initial title-mark helper for `TITLE.BIT` slots `0..6`.
5. Draw the later title overlays around the signature phase in the order
   specified below.
6. Play the `BRITISH.PTH` signature animation over the title screen unless
   the player skips it.
7. Load and draw the start/menu screen used behind the six menu options.

The intro uses two different graphics-resource families. Screen-panel assets
such as `STARTSC` and `STORY1` through `STORY6` use the paired `.16`/`.4` LZW
archive family. `TITLE.BIT`, `BRITISH.BIT`, and `WD.BIT` use the display
driver's compressed bitmap resource format instead. The intro orchestrates file
selection, loading, placement, and draw calls; the data formats themselves
belong to `formats/bit.md`, `formats/tiles.md`, and the display-driver layer.

The title phase accepts an early `J` keystroke. If the player presses `J` during the first title wait, the intro skips the remaining title flourish and commits to the Journey Onward load path. This is a convenience fast path into the same load behaviour reached by selecting `J` from the finished menu.

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
remain visible. The completed title flourish is a single coherent `TITLE.BIT`
slot `6` mark at `(20, 46)`, not seven stacked `ORIGIN SYSTEMS INC` fragments.

For frame-accurate EGA-style playback, each visible slot is revealed by rows in
the following source-row groups. Row numbers are relative to that slot's own
top row, not absolute screen rows. A vertical bar separates presentation
updates; an empty group is a timing/update step that does not add rows.

| Slot | Row reveal groups |
|---:|---|
| 0 | empty \| empty \| empty \| `1` \| empty \| empty \| empty \| empty \| `0, 2` \| empty |
| 1 | empty \| empty \| `1, 5` \| empty \| empty \| `2, 4` \| empty \| empty \| `3` \| empty \| `0, 6` \| empty |
| 2 | empty \| empty \| `2, 8` \| `3, 7` \| `1, 9` \| `4, 6` \| `5` \| `0, 10` \| empty |
| 3 | empty \| `4, 15` \| `1, 7, 12, 18` \| `5, 14` \| `2, 8, 11, 17` \| `3, 6, 13, 16` \| `9, 10` \| `0, 19` \| empty |
| 4 | empty \| `7, 24` \| `2, 12, 19, 29` \| `3, 8, 13, 18, 23, 28` \| `1, 6, 11, 20, 25, 30` \| `4, 9, 14, 17, 22, 27` \| `5, 10, 15, 16, 21, 26` \| `0, 31` \| empty |
| 5 | empty \| `4, 11, 18, 26, 33, 40` \| `1, 8, 15, 19, 36, 43` \| `6, 13, 20, 24, 31, 38` \| `3, 10, 17, 22, 27, 34, 41` \| `2, 5, 9, 12, 16, 19, 25, 28, 32, 35, 39, 42` \| `7, 14, 21, 23, 30, 37` \| `0, 44` \| empty |
| 6 | empty \| `28, 23, 18, 13, 8, 3, 32, 37, 42, 47, 52, 57` \| `26, 21, 16, 11, 6, 1, 34, 39, 44, 49, 54, 59` \| `29, 24, 19, 14, 9, 4, 31, 36, 41, 46, 51, 56` \| `27, 22, 17, 12, 7, 2, 33, 38, 43, 48, 53, 58` \| `25, 15, 5, 35, 45, 55` \| `30, 40, 50, 20, 10` \| `0, 60` \| empty |

The EGA baseline is not a normal white-on-black foreground blit. The helper
stamps 1-bit source pixels into the hidden driver surface, and the animation
player copies only the blue and intensity planes to the visible page. Treat set
source pixels as palette index `9` on the black title background for this
initial flourish. There is no XOR, inverse, alpha, or source sub-rectangle mode
for slots `0..6`; each source slot is consumed from its own `(0, 0)` origin for
its full documented width and height before the driver presentation script
chooses which rows to show.

The remaining title sequence uses four explicit overlay draws:

| Asset | Slot | Top-left X | Top-left Y | Size |
|---|---:|---:|---:|---|
| `TITLE.BIT` | 7 | 108 | 140 | 104 x 33 |
| `TITLE.BIT` | 8 | 152 | 0 | 16 x 15 |
| `BRITISH.BIT` | 0 | 24 | 66 | 272 x 62 |
| `TITLE.BIT` | 9 | 104 | 160 | 112 x 33 |

Their draw order is part of the compatibility contract:

1. After the seven-step `TITLE.BIT` `0..6` flourish returns, clear the lower
   screen band from `y = 140` through the bottom of the 320-by-200 surface.
2. Draw `TITLE.BIT` slot `7` at `(108, 140)`.
3. Draw `TITLE.BIT` slot `8` at `(152, 0)`.
4. Draw the four `BRITISH.PTH` signature path segments, in order, from pen
   origins `(68, 44)`, `(94, 64)`, `(78, 143)`, and `(105, 167)`.
5. Draw `BRITISH.BIT` slot `0` at `(24, 66)`.
6. Draw `TITLE.BIT` slot `9` at `(104, 160)`.

`BRITISH.BIT` is therefore not a backing image under the live path strokes.
The path strokes are the animated pen movement; the `BRITISH.BIT` draw happens
after those strokes and supplies the completed bitmap overlay for the final
pre-menu title frame. A clean renderer should not draw `BRITISH.BIT` before
`BRITISH.PTH` and then stroke on top of it.

The final title frame before `STARTSC` is drawn contains the single completed
`TITLE.BIT` slot `6` flourish at `(20, 46)`, with the lower band replaced by
the later slot `7` and slot `9` overlays, the small slot `8` overlay at the
top, and the completed `BRITISH.BIT` overlay over the middle/lower signature
area. The subsequent `STARTSC` load replaces this title presentation; it is not
another transparent layer over the final title frame.

Only these semantic title slots are visible. Do not render every decoded
resource record from `TITLE.BIT` or `BRITISH.BIT` as an independent visible
sprite, and do not draw the hidden slot `0..6` source stack directly to the
front page. Their visibility is controlled by the intro call sequence and
driver presentation rules above.

The start/menu surface is built from `STARTSC` after the title flourish ends
or is skipped. `STARTSC` is a three-panel screen composition, not pre-rendered
menu text:

| `STARTSC` slot | Role | Top-left X | Top-left Y | Size |
|---:|---|---:|---:|---|
| 0 | Left side strip | 0 | 0 | 16 x 137 |
| 1 | Central start/menu backing art | 16 | 0 | 288 x 137 |
| 2 | Right side strip | 304 | 0 | 16 x 137 |

The loader clears the active intro display/text surface before drawing this
composition, draws all three panels as one adjacent 320-by-137 upper-screen
surface, then draws the intro menu text window over the lower portion of the
screen. The `STARTSC` panels therefore do not themselves contain the six menu
labels. The box/text-window pass owns the bottom menu area and overwrites any
pixels it covers; pixels below the 137-pixel panel height are established by
the preceding clear and by the subsequent text-window drawing, not by hidden
`STARTSC` artwork.

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

The title tick advances only at explicit intro/display call sites. The Lord
British signature path itself is paced by keyboard polling and real-time delay
ticks while it draws the path stream; those delay ticks do not advance the
four-frame title strip. A keypress stops the remaining signature strokes and
proceeds to the start/menu view; it does not skip boot setup or menu rendering.

Once `STARTSC` has been drawn, the start-screen loader runs one clear-carry
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
driver-local frame strip over the title/start screen at pixel `(0, 65)` with
size `320 x 49`, then advances the driver-local frame index modulo four. The
covered destination rows are `65..113` inclusive and the covered columns are
`0..319` inclusive. The first frame after driver initialisation is frame `0`;
the frame index is not reset merely because `STARTSC` is redrawn, a menu row is
re-highlighted, or a non-play submenu returns.

The source pixels are not in `TITLE.BIT`, `BRITISH.BIT`, `STARTSC`, or another
external art file; they are owned by the loaded display driver. In the EGA
driver, the four source phases are laid out as four 320-pixel-wide frame
bands with a 50-row source stride, and the tick copies the upper 49 rows of
the selected band to the destination rectangle. A cleanroom renderer that does
not use the original driver binaries should treat the tick as an intro-only
four-frame overlay in that rectangle, preserving the cadence and destination
even if the replacement frames are independently authored.

The public v1 replacement target is deterministic and opaque. A clean
implementation should provide four independently authored frames, advance one
frame per title-tick call, wrap modulo four, and overwrite the entire
`(0, 65)` `320 x 49` rectangle on every tick. There is no transparency key for
this overlay: black replacement pixels are still drawn as black pixels and
replace what was previously under them. A static placeholder can be useful
during development, but it is a lower-fidelity fallback rather than the
specified title/menu idle animation.

Frame-perfect replacement behaviour can be implemented as:

```text
state title_frame = 0        ; initialised when the intro renderer/driver is created

clear_carry_title_tick():
    draw replacement_frame[title_frame] to pixels x=0..319, y=65..113
    title_frame = (title_frame + 1) mod 4
```

The replacement frames must use the active 16-colour EGA-compatible palette
indices directly. Do not alpha-blend, scale, dither against the previous
screen, or treat any palette index as transparent. If a replacement frame
contains palette index `0`, those pixels overwrite the destination as black.

The carry-set title helper used by some start-screen transition code is not the
public frame-advance operation. Only the clear-carry title tick above advances
the four-frame idle strip in the public intro/menu contract.

The menu and message timing rules are:

| Situation | Title-strip advancement |
|---|---|
| Signature path drawing `BRITISH.PTH` | No title-strip advancement from the signature delay/poll steps. |
| Plain `STARTSC` load or redraw | One clear-carry title tick before the lower intro text window and menu labels are redrawn. |
| Finished menu idle, no key returned | One clear-carry title tick for each no-key poll pass, up to the two-hundred-pass Return-to-View timeout. |
| Valid menu key returned | No extra idle tick for that key pass; dispatch begins immediately. |
| Invalid key returned | No extra idle tick for that key pass; the menu is re-rendered and resumes polling. |
| Empty-save / no-active-game message | No autonomous title ticks while the message is waiting; the following menu redraw performs the ordinary one-tick `STARTSC` path. |
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

The menu labels are rendered as fixed-cell text inside the intro menu window,
after `STARTSC` and the lower window frame have been drawn. The labels appear
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

1. Read the whole `SAVED.GAM` image into the resident save-state region.
2. Check whether the save contains an active Avatar record.
3. If the save is empty, display the "no active game" style message, wait for a key, and return to the intro menu.
4. Read `SAVED.OOL`, the object-overlay companion file.
5. Mirror the surface and underworld object-overlay halves to their per-plane files.
6. If the loaded state resumes on the underworld surface, prompt/probe for the underworld data disk and refresh the underworld object overlay once the disk is available.
7. Mark the display/gameplay transition as ready and return from the intro overlay.

After the intro returns, the main loop reads the scene state that came from the loaded save and dispatches to overworld, town, or dungeon as appropriate. The intro does not load map files such as world data, location data, NPC files, or talk files during this path. Those are loaded by the gameplay mode that the main loop selects.

The file roles, empty-save guard, object-overlay mirror writes, and disk-swap semantics are specified in `save-load.md`, `formats/saved-gam.md`, and `formats/ool.md`.

The empty-save message is written into the current intro text window after the
failed load check, then the path waits for one keypress and returns to the
intro menu loop. It does not start a gameplay mode, does not tick world time,
and does not require a fresh `STARTSC` art load before the menu labels are
repainted by the normal menu loop.

## 8. Create New Character (`C`)

`C` hands control from the intro menu to the character-creation flow. The hand-off goes through a resident trampoline into the proportional-font overlay, which owns both the paragraph renderer used by the questionnaire and the chargen driver.

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

Each normal step follows the same pattern:

1. Ensure the story-art file for the current step is loaded, reloading only
   when the fixed step boundary changes the file.
2. Select the story-art subimage and placement for this narrative step.
3. Load or select the corresponding story text.
4. Draw the panel through the screen-art renderer.
5. Render the narrative text through the proportional-font renderer.
6. Wait for the player to advance, except for the automatic opening step.
7. Run any local display effect tagged to that step: transition-strip art, the step-1 rectangle transition, or secondary story art.

Step 0 is an automatic opening transition: it consumes the first story text
record and advances into the rest of the sequence without waiting for input.
Steps 1 through 20 wait until the keyboard poll returns a non-zero key. This
wait is local to the intro; it does not run gameplay world ticks, NPC
schedules, active-object animation, or the saved-game clock.

The shipped `STORY.DAT` file supplies twenty non-empty text records. The intro
sequence has one additional visual step: step 6 uses two inline
doorway-transition lines owned by the intro code instead of consuming a
`STORY.DAT` record. Every other step consumes the next `STORY.DAT` record in
sequence and uses the same paragraph conventions as other proportional-font
narrative screens.

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
| 6 | Draw an additional `STORY2.16` subimage 3 at `(96, 39)` and render two inline doorway-transition text lines instead of reading a `STORY.DAT` record. |
| 15, 20 | Draw a second `STORY6.16` subimage 3 at the same X coordinate and 55 pixels below the primary story-art Y coordinate. |
| 16, 18 | Draw a second `STORY6.16` subimage 5 at the same X coordinate and 55 pixels below the primary story-art Y coordinate. |
| 17, 19 | Draw a second `STORY6.16` subimage 7 at the same X coordinate and 55 pixels below the primary story-art Y coordinate. |

The transition effects are local to the story loop and do not advance gameplay
time. Steps 0, 7, and 14 are static transition-strip pre-draws before the
primary story art. Step 1 is the only confirmed rectangular transition: after
the player advances that step, the extra `STORY1.16` art is drawn at `(40, 86)`
and the intro runs a left-to-right column reveal over the inclusive rectangle
`(40, 86)..(75, 120)`. The reveal is 36 title ticks long: one pixel column is
made visible per tick, starting at `x = 40` and ending at `x = 75`. Previously
revealed columns remain visible, unrevealed columns retain the previous screen
contents, and the effect does not dither, blend, or recolour the panel. The
player-input gate is the wait before the transition; once the reveal starts,
the transition is a blocking local visual effect.

No wider intro story-page rectangle/rate table is part of this baseline. A
focused caller sweep of the intro slide loop identifies the step-1 case as the
only column-wipe rectangle in that twenty-one-step story sequence. Steps 0, 7,
and 14 are pre-drawn transition-strip art, not column-wipe rectangles, and the
secondary art passes for steps 15 through 20 are direct draws after the step
waits. A separate start/menu-screen loader also uses a rectangle helper, but it
belongs to start-screen presentation rather than to a step-2 or later story-page
transition table. If later evidence identifies additional story-page callers of
the same rectangle helper, specify their bounds and rates per caller instead of
inheriting the step-1 bounds by default.

The start/menu-screen loader's separate rectangle use is optional and
caller-selected. It first loads and directly draws the `STARTSC` art, then, only
when the caller requests the animated path, reveals the inclusive pixel
rectangle `(0, 0)..(319, 100)` with the same left-to-right, one-pixel-column per
title-tick helper used by story step 1. The reveal is therefore 320 title ticks
long when enabled, copying columns `x = 0` through `x = 319` in order.
Unrevealed columns retain the prior screen contents until their column is
copied. The loader polls input only after this rectangle pass has completed;
that poll can affect the following start-screen prompt/continuation path, but
it does not interrupt the reveal itself. Ordinary direct `STARTSC` loads skip
this rectangle pass. Fixed `END.DAT` and other ordinary bitmap-window callers
do not inherit the start-screen reveal contract; their clear, page-in, border
redraw, and wait timing remain caller-owned presentation details.

The slide loop does not mutate gameplay state, does not create a save, and does not select a gameplay scene. Its only persistent effect is that, when it returns, the intro reloads or redraws the start/menu view so the six-option menu can continue.

The screen-panel asset container is specified in `formats/tiles.md`. The proportional text output contract is described in `text-output.md`, and the story text file is specified in `formats/story-dat.md`.

## 11. Acknowledgements (`A`)

`A` displays the acknowledgement/credits screen and then returns to the intro menu. It uses the same already-initialised display and text systems as the title and story paths. The acknowledgement path is self-contained: it does not read or write the save image, does not change the gameplay scene, and does not exit the program.

After the acknowledgement screen finishes, the intro returns to its menu loop with intro state still active. A later `J`, `C`, or `T` selection is required to leave the intro.

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
sections and renders a centered chapter caption above it. Captions are derived
from the strip index: strip 0 is The Summoning, strip 1 is The Journey, strip 2
is The Arrival, and strip 3 is The Welcoming. The command stream does not carry
a separate caption opcode or inline caption text. Command `0x06` loads the
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
- **Acknowledgement screen content.** The acknowledgement branch is identified
  as a self-contained intro submenu. Its exact text and pagination are left to
  a source-free content transcription rather than copied binary text dumps.
- **Title tick replacement art.** The EGA baseline destination rectangle,
  four-frame cadence, and driver-local ownership are known. The original frame
  pixels live inside the historical display driver rather than an external
  asset; a modern cleanroom renderer needs independently authored replacement
  frames if exact driver binary reuse is out of scope.
- **Alternate display-driver entries.** The EGA dispatch surface for rectangle
  fill, driver-compressed bitmap resources, and title ticks is specified in
  `display-driver-abi.md`. Exact CGA, Hercules, and Tandy conversion details
  remain alternate-hardware parity work.

## 16. Sources

The behaviour described here was derived by reading the function and format notes listed below. None of those notes' assembly excerpts, decompiled code, private addresses, or binary text dumps appear in this spec; this document is a cleanroom prose re-derivation of the observed behaviour.

- Boot initialisation, title-screen orchestration, asset-depth selection, intro menu rendering, key dispatch, and the high-level hand-off to the main loop: `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Start/menu screen loading, `STARTSC` composition use, lower intro text-window redraw, and fixed menu-entry placement: `u5-decomp/functions/INTRO_OVL/0x05B0_startsc_loader.md`, `u5-decomp/functions/INTRO_OVL/0x04E0_clear_intro_text_window.md`, `u5-decomp/functions/INTRO_OVL/0x0676_menu_entry_render.md`, and `u5-decomp/functions/INTRO_OVL/0x06BC_menu_render.md`.
- Lord British signature path consumption, four-segment walking, pen movement, pen-up semantics, and keyboard skip behaviour: `u5-decomp/functions/INTRO_OVL/0x0050_pth_walker.md`.
- Title-mark helper sequencing for `TITLE.BIT` slots `0..6`, hidden-source
  versus visible-destination placement, EGA row reveal groups, lower-band
  clearing, and the explicit slot `7`, slot `8`, `BRITISH.BIT` slot `0`, and
  slot `9` overlay order: `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`,
  `u5-decomp/formats/ega-driver.md`, and fresh local resident
  display-helper verification.
- Story slide loop, story-art loading, proportional-font text rendering, slide wait/advance behaviour, the step-1 rectangle-transition handoff, and return-to-menu path: `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md` and fresh local rectangle-transition helper analysis.
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
- Title tick ownership, EGA destination rectangle, four-frame cadence, signature
  delay/poll separation, and the clarification that `FLAMES.OVL` is a
  scratch-buffer thunk, not the flame renderer:
  `u5-decomp/functions/INTRO_OVL/0x2090_title_tick.md`,
  `u5-decomp/functions/INTRO_OVL/0x094E_iter_until_kbd.md`,
  `u5-decomp/functions/FLAMES_OVL/0x0000_flames_entry_stub.md`, and
  `u5-decomp/formats/ega-driver.md`.
- Filled-rectangle dispatch, corrected driver-compressed bitmap dispatch, and
  driver-side title/bitmap rendering relationship:
  `u5-decomp/functions/ULTIMA_EXE/0x0AA6_draw_compressed_bitmap.md`,
  `u5-decomp/functions/EGA_DRV/0x1180_fill_rect_v2.md`, and
  `u5-decomp/functions/EGA_DRV/0x1226_draw_compressed_bitmap.md`.
- Journey Onward load path, empty-save guard, `SAVED.GAM` and `SAVED.OOL` reads, object-overlay mirror writes, underworld disk-swap branch, and final return to the main loop: `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- Transfer/continue roster path, transfer disk-state setup, seed loads, roster/status screen rendering, and commit/abort behaviour: `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Outer main-loop boot context, scene dispatch after intro return, and overlay call model: `u5-decomp/functions/ULTIMA_EXE/0x0000_main_game_loop.md`.
- Display-driver loading and initial mode setup: `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- Text-window descriptor initialisation and text output primitives used by intro screens: `u5-decomp/functions/ULTIMA_EXE/0x1184_init_text_descriptor_table.md`, `u5-decomp/functions/ULTIMA_EXE/0x1850_print_string.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`.
- `BRITISH.PTH` file structure and its confirmation as a title-screen path stream rather than an NPC schedule file: `u5-decomp/formats/npc-tlk-pth.md`.
- Title, start-screen, and story-panel graphics container format: `u5-decomp/formats/tile-graphics.md`.
- Story text data observations used to identify the intro slide text source: `u5-decomp/formats/data-tables.md`.
- Fresh local title-sequence verification identified the visible title
  sequencing and the four `BRITISH.PTH` pen origins; no code, disassembly, or
  raw data is reproduced here.
