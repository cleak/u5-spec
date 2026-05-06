# Intro

## 1. Overview

The intro system is Ultima V's startup-facing mode. It is responsible for the work that happens after the resident executable has parsed its command-line display option and before the first gameplay mode is entered: hardware and driver setup, title-screen presentation, the Lord British signature animation, the six-option intro menu, the story slide show, the acknowledgement screen, and the entry paths for loading, creating, or transferring a game.

The intro is not a gameplay mode in the same sense as overworld, town, dungeon, or combat. It is a boot and menu overlay. While it is active, the engine uses a private intro scene state and stays inside the title/menu loop. When a player selects a path that produces or loads a playable state, the intro updates the resident scene state and returns to the main loop. The main loop then dispatches to the appropriate gameplay mode using the same scene-byte rules described in `main-loop.md`.

The original code keeps the intro in an overlay because it is large, graphics-heavy, and needed only at the start of a session. A modern implementation can treat it as an ordinary application state, but it should preserve the same externally visible flow:

- boot-time display and input initialisation happens before any title/menu input is accepted;
- the title art is shown before the menu;
- the Lord British path animation is skippable by keyboard input;
- the six intro-menu keys are accepted case-insensitively;
- non-play menu paths return to the menu;
- play-producing paths hand control back to the main loop rather than running a gameplay loop inline.

## 2. Entry from the main loop

The resident executable performs only a thin first layer of boot work. It records the display-driver request from the command line, captures DOS/disk-swap state, primes a few input flags, and then calls the intro overlay. The intro overlay performs the heavier system setup:

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

After boot setup, the intro builds the title presentation in layers:

1. Clear and configure the full-screen text/graphics surface.
2. Render the initial title/rune text appropriate to the active driver.
3. Load the title and Lord British artwork.
4. Draw the title artwork through the display driver's compressed-bitmap path.
5. Load `BRITISH.PTH`.
6. Play the signature animation over the title screen unless the player skips it.
7. Load and draw the start/menu screen used behind the six menu options.

The compressed bitmap and screen-panel assets are decoded by the display and graphics pipeline, not by intro-specific code. The intro orchestrates file selection, loading, and draw calls; the data formats themselves belong to `formats/tiles.md` and the display-driver layer.

The title phase accepts an early `J` keystroke. If the player presses `J` during the first title wait, the intro skips the remaining title flourish and commits to the Journey Onward load path. This is a convenience fast path into the same load behaviour reached by selecting `J` from the finished menu.

## 4. `BRITISH.PTH` signature animation

`BRITISH.PTH` is a one-off path stream used only by the intro. The file stores small signed pen movements, not absolute coordinates and not NPC schedule data. The intro loads the whole path file into a scratch buffer, then calls a path walker four times. Each call starts from a fixed title-screen origin and consumes one segment of the path stream, so the four calls together draw the whole Lord British signature.

At each path step, the walker decodes one movement, advances the pen, and paints when the movement represents a pen-down stroke. Larger movement magnitudes act as short pen-up moves so the signature can jump across small gaps without drawing a connecting line. Segment terminators end the current walker call and return control to the intro, which restarts the next segment from its next fixed origin.

The animation is intentionally interruptible. The walker polls the keyboard between path steps, and any pending key aborts the remaining animation. The intro then continues to the same start/menu screen it would have reached after a complete animation. Skipping the animation does not skip boot initialisation, menu setup, or later load validation.

The path format, segmentation, and pen-up rule are specified in `formats/pth.md`. This system spec defines only how the intro uses that format: load once, draw four title-screen segments, poll for early exit, then continue to the menu.

## 5. Intro menu model

The intro menu is a six-entry key menu. It is rendered after the title/start screen is ready and remains the controlling loop until a play-producing option commits or the process exits by another path. Keys are folded to uppercase before dispatch, matching the input-system contract in `input.md`.

The accepted keys are:

| Key | Menu action | Result |
|---|---|---|
| `J` | Journey Onward | Load the active save and return to the main loop if valid. |
| `C` | Create New Character | Enter character creation through the proportional-font/chargen flow. |
| `T` | Transfer from Ultima IV | Enter the transfer/roster path and commit or abort from there. |
| `U` | Ultima V Introduction | Play the story slide sequence, then return to the intro menu. |
| `A` | Acknowledgements | Show credits/acknowledgements, then return to the intro menu. |
| `R` | Return to View | Restore the title/start view through the intro's view-render path, then remain in intro mode. |

Invalid keys are ignored and the menu continues polling. Behaviourally, the player sees a stable six-option menu that waits for one of the accepted keys and returns to that same menu after non-play sub-screens finish.

While the menu waits, the intro continues to run its lightweight title tick so the screen does not become a dead static wait. This is separate from the gameplay world tick. No gameplay time advances while the intro menu is active because no gameplay mode has started.

## 6. Journey Onward (`J`)

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

## 7. Create New Character (`C`)

`C` hands control from the intro menu to the character-creation flow. The hand-off goes through a resident trampoline into the proportional-font overlay, which owns both the paragraph renderer used by the questionnaire and the chargen driver.

From the intro system's perspective, the contract is simple:

- select `C`;
- enter chargen;
- let chargen either abort without writing or write the first `SAVED.GAM` and `SAVED.OOL`;
- return to intro mode after chargen completes;
- require the player to press `J` afterward to load the newly written save.

The intro does not automatically enter Britannia after character creation. This is visible in play: creating a character produces a save, then returns to the menu. The player must explicitly choose Journey Onward to start the game.

The questionnaire, seed-file cloning, name/gender prompts, stat assignment, and save commit are specified in `chargen.md`. The intro spec only owns the menu hand-off and return-to-menu behaviour.

## 8. Transfer from Ultima IV (`T`)

`T` enters the transfer path for players bringing forward an Ultima IV character. This path is intro-owned rather than part of the proportional-font questionnaire flow, but it shares the same end goal as chargen: produce a playable U5 save state and return control through the normal intro/main-loop boundary.

The observed transfer path:

1. Switches the intro into its transfer/continue state.
2. Sets up disk-swap state for the transfer media.
3. Loads a U5 Britannia seed image and object-overlay seed used as the destination baseline.
4. Renders a character-roster/status screen showing party slots and statistics.
5. Polls for transfer confirmation, abort, or follow-up input.
6. On abort, restores intro/menu state and returns to the menu.
7. On commit, updates the resident state and lets the intro hand back to the main loop.

The exact U4-to-U5 stat translation is not fully specified here. It belongs with the chargen and transfer specs because it determines the contents of the resulting save, not the intro menu's control flow. The roster-preview and disk-swap behaviour are included here because the intro overlay owns that screen and its polling loop.

## 9. Ultima V Introduction (`U`)

`U` plays the story slide sequence. This is a non-play path: after the sequence ends, the player returns to the intro menu.

The sequence begins by making sure the intro/start-screen state is active, then iterates through a fixed set of story-art screens. Each slide iteration follows the same pattern:

1. Load the next story-art panel for the active display depth.
2. Load or select the corresponding story text.
3. Draw the panel through the screen-art renderer.
4. Render the narrative text through the proportional-font renderer.
5. Wait for the player to advance.
6. Optionally run the local fade or palette transition used by that slide.

The graphic sequence covers the six numbered story panels plus the Warriors of Destiny panels used to bookend or extend the introduction. The narrative text comes from the intro story data file and uses the same paragraph conventions as other proportional-font narrative screens.

The slide loop does not mutate gameplay state, does not create a save, and does not select a gameplay scene. Its only persistent effect is that, when it returns, the intro reloads or redraws the start/menu view so the six-option menu can continue.

The screen-panel asset container is specified in `formats/tiles.md`. The proportional text output contract is described in `text-output.md`. The story text file does not yet have a dedicated cleanroom format spec in this repository.

## 10. Acknowledgements (`A`)

`A` displays the acknowledgement/credits screen and then returns to the intro menu. It uses the same already-initialised display and text systems as the title and story paths. The acknowledgement path is self-contained: it does not read or write the save image, does not change the gameplay scene, and does not exit the program.

After the acknowledgement screen finishes, the intro returns to its menu loop with intro state still active. A later `J`, `C`, or `T` selection is required to leave the intro.

## 11. Return to View (`R`)

`R` is a visual return/reset path for the intro view. It invokes a renderer in the font/display overlay family to restore the title/start view and then remains in intro mode. It is not a saved-game resume command; saved-game resume is `J`.

This path is useful after a sub-screen has displaced the title/menu view or when the player wants to return from an intro-side display to the main view. Its exact visual result should be verified against a captured run; the control-flow contract is clear: render the view, keep the intro scene active, and continue polling the six-option menu.

## 12. Hand-off back to gameplay

Only play-producing paths should cause the intro overlay to return in a gameplay-ready state:

- `J` returns after a valid save has been loaded.
- `T` returns after a transfer/continue path commits a playable state.
- `C` normally returns to the intro menu after writing a save; the later `J` is what enters gameplay.

On a successful hand-off, the intro leaves resident state arranged so the main loop can do its ordinary scene dispatch. The scene byte is part of the save image, so a loaded game resumes in the same high-level mode in which it was saved. The intro does not directly invoke overworld, town, or dungeon turn loops as part of the load. It returns and lets the main loop route.

This keeps the boot architecture consistent with all later scene transitions: systems set state and return, and the main loop decides which mode owns control next. See `main-loop.md` for the outer dispatch rules and `save-load.md` for the load path's final commit.

## 13. Implementation notes

A modern implementation does not need to reproduce the overlay loader, DOS interrupt setup, or disk-swap callbacks literally. It should preserve their user-visible contracts:

- Initialise display, text windows, input, timing, and file I/O before drawing the first title/menu frame.
- Select one graphics depth/backend for the whole intro session.
- Treat disk-swap prompts as file-availability prompts; on a single-directory install they can be no-ops.
- Keep intro input one-keystroke-at-a-time and case-insensitive.
- Suppress gameplay world ticks while the intro is active.
- Make every non-play submenu return to the intro menu without mutating gameplay state.
- Make the Journey load path validate the save before leaving the intro.
- Route successful gameplay entry through the main-loop scene dispatcher.

For pixel-perfect reproduction, an implementation will also need the fixed title-screen origins for the four `BRITISH.PTH` segments and the exact visual timings of palette/fade transitions. Those are implementation constants recovered from the intro overlay, not part of the `BRITISH.PTH` file itself.

## 14. Open questions and variations

- **Return to View visual semantics.** The control-flow role of `R` is known, but the exact screen it restores should be verified against live capture.
- **Transfer stat mapping.** The intro-owned transfer path and roster screen are identified, but the exact U4-to-U5 stat translation belongs to a deeper transfer/chargen pass and remains incomplete.
- **Story text file format.** The story slide text source is known at a behavioural level, but there is no dedicated cleanroom `formats/story-dat.md` yet.
- **Slide layout and pacing.** The fixed slide list and render/wait pattern are known. Per-slide rectangle placement, fade timing, and exact wait semantics need a capture or a fuller renderer pass if the intro must be pixel-perfect.
- **Acknowledgement screen content.** The acknowledgement branch is identified as a self-contained intro submenu, but its exact text and pagination are not specified here to avoid copying binary text dumps.
- **Display-driver opcodes.** The intro uses several driver calls for compressed bitmap drawing, palette/fade work, and title ticks. Their ABI belongs in a future display-driver spec rather than this intro spec.

## 15. Sources

The behaviour described here was derived by reading the function and format notes listed below. None of those notes' assembly excerpts, decompiled code, private addresses, or binary text dumps appear in this spec; this document is a cleanroom prose re-derivation of the observed behaviour.

- Boot initialisation, title-screen orchestration, asset-depth selection, intro menu rendering, key dispatch, and the high-level hand-off to the main loop: `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Lord British signature path consumption, four-segment walking, pen movement, pen-up semantics, and keyboard skip behaviour: `u5-decomp/functions/INTRO_OVL/0x0050_pth_walker.md`.
- Story slide loop, story-art loading, proportional-font text rendering, slide wait/advance behaviour, and return-to-menu path: `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- Journey Onward load path, empty-save guard, `SAVED.GAM` and `SAVED.OOL` reads, object-overlay mirror writes, underworld disk-swap branch, and final return to the main loop: `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- Transfer/continue roster path, transfer disk-state setup, seed loads, roster/status screen rendering, and commit/abort behaviour: `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Outer main-loop boot context, scene dispatch after intro return, and overlay call model: `u5-decomp/functions/ULTIMA_EXE/0x0000_main_game_loop.md`.
- Display-driver loading and initial mode setup: `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- Text-window descriptor initialisation and text output primitives used by intro screens: `u5-decomp/functions/ULTIMA_EXE/0x1184_init_text_descriptor_table.md`, `u5-decomp/functions/ULTIMA_EXE/0x1850_print_string.md`, and `u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`.
- `BRITISH.PTH` file structure and its confirmation as a title-screen path stream rather than an NPC schedule file: `u5-decomp/formats/npc-tlk-pth.md`.
- Title, start-screen, and story-panel graphics container format: `u5-decomp/formats/tile-graphics.md`.
- Story text data observations used to identify the intro slide text source: `u5-decomp/formats/data-tables.md`.
