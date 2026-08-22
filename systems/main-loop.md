# Main loop

## 1. Overview

Ultima V's life cycle is a single pair of nested loops. The outer loop runs for the entire session: it boots once at DOS launch, then dispatches forever among the playable world modes — overworld, the town family (town, dwelling, castle, keep), and dungeon — by reading a single resident byte that names the active scene. Combat is entered through a mode-local framer rather than as an ordinary outer-loop branch. The inner loop is whichever mode loop the outer loop has handed control to: a tight per-turn cycle that reads one player command, dispatches it, advances the world clock, and renders. When a command moves the player into a different scene class, the active mode loop sets the scene byte to the new scene and returns. The outer loop reads the new value on its next iteration and spins up the matching mode. Explicit program-exit prompts are handled by mode-loop control paths, separate from the resident Q save command.

This spec describes the outer loop and how it ties the modes together. Each individual mode has its own spec. Here the focus is on what runs before the first turn, what the scene byte means, how the outer dispatch picks a mode, what the cross-overlay call mechanism does behind every entry into a mode, and which hooks are common to every mode.

## 2. Boot sequence

When DOS hands control to the executable, three small layers run before the first frame is drawn.

**Layer one — runtime startup.** The executable performs its compiler/runtime startup work, establishes the process state it needs, and then enters the game-owned startup path. This layer has no game-relevant behaviour for a cleanroom engine beyond "initialise before gameplay".

**Layer two — `main` body.** The `main` function parses the command-line driver letter and captures persistent state. The driver letter — `C`, `H`, `T`, or `E` for CGA, Hercules, Tandy, or EGA — is read from the first character of the first argument and folded to upper case. Each recognized letter sets one of four mutually-exclusive driver-detection flags that the display-driver loader will consult in the next layer. With no argument or with an unsupported first character, the flags are clear and the loader picks a default through boot-time display detection. Additional arguments have no known engine meaning. The function then captures the current DOS drive letter (used by the disk-swap prompt), initialises a small group of disk-swap state bytes, and sets the type-ahead setting the input pipeline reads to its default state, which is "flush the queue on every read" (`input.md` Section 6). `main` then calls into the intro overlay and drops into the forever loop.

**Layer three — intro overlay.** The intro overlay performs the heavy boot work that `main` omits: machine-type detection, installation of DOS critical-error and Ctrl-Break interrupt handlers, the timer-tick interrupt handler, the text-window descriptor table initialiser, and the actual display-driver load and video-mode set. With those done, it paints the title screen — a full-window image, a scripted brush stroke that traces "Lord British" across the title (driven by a per-character path file), and a six-entry menu: Journey Onward (load a saved game), Create New Character, Transfer from Ultima IV, Ultima V Introduction (the slide show), Acknowledgements, and Return to the View. Pressing `J` at the title short-circuits the brush stroke. Journey Onward is the gameplay-entry path: a valid load sets the resident scene byte from the save image and returns to the outer loop. Character creation and Ultima IV transfer are fresh-save producer paths; after writing their save files, they return to the intro menu and require a later Journey Onward load to enter gameplay.

The intro is kept as an overlay rather than resident code because it is one of the largest pieces of code in the game and is needed only at startup. Once the intro returns, its memory becomes available for whatever overlay the next dispatch needs.

## 3. The scene byte

The outer loop's only routing state is a single resident byte — the *scene byte* — that names what the player is currently doing. It is an opaque scene id classified by comparisons, not a packed enum whose high bits can be decoded independently.

| Value or range | Meaning |
|------:|------|
| `0` | Overworld / underworld travel mode. |
| `1`–`32` | Town-family scene id: town, dwelling, castle, or keep. |
| `33`–`127` | Dungeon-class scene id when reached by playable dispatch. |
| `0x40`, `0x41`, `0x42` | Intro and Return-to-View preview states. These are not ordinary gameplay mode values. |
| `0xFF` | Temporary combat-class marker used by combat, shrine/urn meditation, and some cutscene freezes. |

Every mode loop reads the scene byte each iteration and exits when the value changes. Every transition between modes is a write to the scene byte — by an entry handler in the source mode (Enter on a fixed town or dungeon location coordinate, an interior boundary exit, a traced special branch, or a combat framer). Mode entry is declarative rather than imperative: the source mode sets the scene byte and returns, and the outer loop dispatches on the next iteration. World-plane changes, such as the confirmed surface fall into the underworld, are not scene-byte mode transitions. Natural-moongate entry is owned by the overworld transition contract rather than this generic scene-byte summary.

Sub-ranges carry additional meaning. In the town family, the scene byte selects one of four file families and one of eight per-family members; per-class data is addressed by the same encoding. In the dungeon class, stock scenes `33..40` map to the eight named dungeons; subtract `33` for the zero-based `DUNGEON.DAT` record index. Values at or above `0x80` are treated as combat-class by several readers, but the only observed writer in that high range uses `0xFF`. Do not invent durable arena ids from the unused high values.

The scene byte is part of the saved-game image, so the outer loop's dispatch on resume picks the correct mode by reading the saved value. Combat is not saved, so the byte is normalised to its post-combat home scene before the save is written.

## 4. The outer dispatch

After the intro returns, the outer loop is a simple read-and-route:

1. Read the scene byte.
2. If zero, run the overworld mode loop until it returns.
3. Else if in `1..32`, run the town entry pass and then the town turn loop until it returns.
4. Else, run the dungeon dispatch path. The dungeon cluster uses DNGLOOK-owned view/lifecycle helpers to set up or tear down the first-person view and hands steady-state turns to the DUNGEON turn loop until it returns. OUTSUBS is not part of this dungeon-class dispatch; it is the overworld helper library for chunk loading, entry checks, status ticks, and related travel work. This path is intended for dungeon-class gameplay values; intro-only values are established and consumed before normal play reaches this loop.
5. Run a between-mode cleanup pass that gives pending disk-prompt presentation
   state a chance to run.
6. Loop.

Each branch ends only when the active mode's loop has noticed a change in the scene byte and returned. The four transition cases are:

- **Overworld → town.** Enter on a fixed town-mode location coordinate sets the scene byte to a value in `1..32`. The overworld loop's exit check sees the change and returns. The next outer iteration enters the town entry path.
- **Overworld → dungeon.** Enter on a fixed dungeon location coordinate sets the scene byte to a value in `33..40` and the overworld loop returns; the next iteration runs the DNGLOOK/DUNGEON dungeon dispatch path rather than an OUTSUBS entry path.
- **Town / dungeon → overworld.** Stepping off the edge of a town-family interior grid and confirming the leave prompt, or reaching a dungeon scene-clear path, clears the scene byte. Town exits and the dungeon surface-reset helper restore a defined exterior coordinate before the next outer iteration runs the overworld loop; the dungeon helper also writes the destination world plane, choosing Britannia when the party left off the topmost level and the Underworld when they left off the lowest. The pit-chain off-bottom path is traced as a dungeon scene-clear that leaves the incremented off-bottom level byte and the trap-chain X/Y in resident state; it does not call the surface-reset coordinate table.
- **Combat from any mode.** Combat is entered from inside a mode's per-turn loop — by a combat framer that saves the active-object table, swaps in a combat-instance map, runs the combat round loop, and on return restores the table. The outer loop never directly dispatches into combat: by the time control reaches the outer loop, the scene byte has already been restored to the home scene.

The outer loop has one piece of mid-iteration state: a one-bit "exit pending" flag that the overworld branch sets when it returns. The flag prevents a tight overworld → overworld loop with no work between when the overworld loop returns with the scene byte still zero (for instance, because a no-op cancellation produced no scene change). A second flag tracks whether the previous iteration ran the dungeon branch; the dungeon dispatch is called with this flag so it knows whether the player is entering fresh or returning from combat.

The outer loop's body is short. All the per-turn complexity — input, dispatch, redraw, time advance, NPC scheduling, encounter rolls — lives inside the mode loops. The outer loop is a strict scene router with one piece of cleanup glue.

## 5. The cross-overlay call mechanism

The four mode handlers are not functions in the resident image. They live in separate overlay files that the runtime loads on demand. The resident image holds only the outer loop, the scene byte, the central command dispatcher, the per-turn cleanup helper, the world-tick redraw orchestrator, the input pipeline, the active-object table, the visibility producer, the renderer, and a handful of small primitives. The per-mode loops, conversation engine, spell handler, shop dialogues, chargen flow, and combat AI all live in overlays.

The original reaches those overlays through a resident dispatch table whose entries correspond to externally callable overlay entry points. The dispatch entry ensures the owning overlay is loaded, then transfers control to the requested entry point. If the overlay is already resident, the loader step is skipped; otherwise the runtime reads the overlay file into an appropriate buffer and updates the cached dispatch state. `overlay-abi.md` owns the detailed call and residency contract; this main-loop spec only depends on the fact that overlay entries behave like ordinary calls.

From the caller's perspective, an overlay entry behaves like a regular function: the target runs and returns normally. The loader is an implementation detail between the caller and the overlay.

The overlay buffers are not unique. A handful of buffers in the data segment hold one overlay each at any given moment, and each buffer is shared by several overlays. Overlays that share a buffer are mutually exclusive — loading one evicts whichever was previously resident. The link-time partition groups overlays that are never simultaneously needed. A modern engine that loads everything from a single directory can ignore buffer-sharing and link the entry points directly; the externally observable behaviour is unchanged.

Cross-overlay calls — overlay A calls an entry in overlay B — work the same way as resident-to-overlay calls. The mechanism is invisible in the call graph.

## 6. The four mode loops

Each world mode has its own per-turn loop. The shared structure is a five-step cycle:

1. **Input.** Block on the input pipeline until a keystroke arrives. The pipeline polls the keyboard, paints the cursor blink, and — when no key is pending — runs one *world tick* of redraw and ambient animator-driven side effects. In-world time and scheduled NPCs freeze during the wait; the idle tick is not a committed turn.
2. **Pre-dispatch checks.** A short setup step handles meta-state — combat in progress, cursed-by-spell timer — and the scene-byte exit check. If the scene byte changed during the previous turn, the loop returns to the outer loop.
3. **Dispatch.** Direction codes go to a small per-mode movement table. Letter commands go to the shared command dispatcher, which returns a status word saying whether the action consumed a turn.
4. **Per-turn epilogue.** When the action consumed a turn, the loop calls the per-turn cleanup helper with the mode's minute increment — two minutes for overworld, one minute elsewhere. Mode-specific work runs after cleanup: town runs the NPC schedule processor; overworld runs random-encounter checks and object-pruning work; dungeon runs dungeon-local turn bookkeeping; combat advances the round counter.
5. **Render.** A redraw if any per-turn work flagged the visibility-dirty flag or moved an animated object. Otherwise the loop reads the next command without painting.

The three exploration loops — town, overworld, dungeon — share one further step, ahead of the input block: a **party-capability check** over the roster. A member counts as able to act when their status is Good or Poisoned. If at least one is able, the turn proceeds normally, and the check also records which member that was for callers that need one able to act. If none is able but at least one is asleep, the loop prints the sleep line and passes the turn without reading a command. If none is able and none is asleep, the loop runs the total-party-defeat sequence specified in `systems/blackthorn.md` Section 7 instead of taking a turn. The check, and the mapping from its three results to those three behaviours, is identical in all three modes; combat has no such check of its own and reaches the defeat sequence only through the loop it returned to.

The cycle is otherwise identical in shape across the playable mode loops. The differences are entirely in step four: which subsystems run, what the minute increment is, what bookkeeping each mode keeps. The shared dispatcher and shared cleanup are what make the modes feel like one engine rather than unrelated subsystems.

Combat is special: it does not advance the world clock on every action (only on round-end), and it never returns directly to the outer loop. A combat round ends with a return to whichever mode invoked the framer; the framer restores that mode's saved active-object table; the source mode's per-turn loop resumes from where it called the framer.

## 7. The command dispatcher

Every printable letter that survives the input pipeline goes to a single dispatcher in the resident image. The dispatcher takes one byte (the uppercased command letter) and returns a status word. Internally it searches a per-letter handler table; each block prints a verb prefix from the resident verb table, checks the scene byte to pick the appropriate per-mode handler, and either acts inline or routes to an overlay entry. `commands.md` is the detailed per-letter contract.

Many letters are *mode-aware*. A-Attack runs different overlays in overworld, town, and dungeon. K-Klimb has three handlers — one for each non-combat mode. T-Talk runs the conversation engine in town and prints "Funny, no response!" elsewhere. L-Look uses the dungeon's first-person look overlay underground and the world look overlay above. The dispatcher reads the scene byte to pick the branch, then routes to the relevant overlay entry. A few letters are shared — Q save-game, Z-Stats, R-Ready — and route to a single handler whenever they reach this dispatcher. The dispatcher is the one place where the scene byte is consulted at letter-granularity; everywhere else, the active mode loop has already routed by mode.

The dispatcher's return value is a four-member enum: acted, no action, a
town-only "a conversation happened" value, and a town-only "re-prompt without
advancing the world" value produced when the party keys digits at the
harpsichord. The overworld and dungeon loops read it as a single boolean; only
the town loop distinguishes all four. There is no separate global turn flag
anywhere in the engine — turn cost travels entirely in this value.
`commands.md` Section 3 gives the full contract, including the six routes that
forward an overlay handler's own value.

The dispatcher is shared across the three non-combat mode loops. Combat has its own dispatcher inside the combat overlay because the per-letter set is different. The world dispatcher does not poll; it is called by mode loops with an already-translated byte.

## 8. The per-turn cleanup hook

Every mode loop's per-turn epilogue calls a single shared helper — the *per-turn cleanup* — with a minute increment. The helper does five things, in order:

1. **State-tag adjustment.** If the cleanup sees the `Q` tag, halve the increment with a one-minute floor. If it sees the `T` tag, skip the minute and light-counter writes for that pass. This timing tag is adjacent to, but distinct from, the party's boarded vehicle/transport tile.
2. **Time advance.** Add the increment to the minutes byte and cascade rollovers: minutes to hours, hours to days, days through a 28-day month and a 13-month year. Time has its own spec; the cleanup is the call site.
3. **Daylight recompute.** Compute the ambient daylight value from hour, scene, and the party's Z value. A Z value with its high bit set (the Underworld plane, and below-entry floors inside a location) and scene twenty-five force full darkness before the clock is consulted; surface daytime hours produce full daylight; dawn and dusk interpolate through a small gradient using the minute byte. A burning torch or light spell then raises that ambient value to a floor, so a torch-bearer in a dark tunnel sees by their own light rather than by the ambient level; the two light counters are durations feeding those floors, not radii themselves. See `systems/lighting.md` section 4.
4. **Visibility-dirty flag.** If daylight changed, set the visibility-dirty flag so the next world-tick will re-run the expensive visibility producer.
5. **Hour-change presentation refresh.** If the hour changed and the active scene uses the surface/town status presentation, refresh the sky strip in the top viewport border (`systems/moons.md`). Earlier notes treated this as an unresolved gameplay event hook; the resolved public contract is narrower and display-only. Natural-moongate placement is still separate open overworld work.

The cleanup is also called with a minute increment of zero by handlers that want the daylight recompute and dirty-flag side effects without advancing time — the overworld entry handler does this when the player steps off a town's grid boundary back into the outdoors; the town entry handler does it as a final post-load tile pass.

The cleanup does not run the NPC schedule processor, encounter checks, combat cadence, or the resident active-object animator. Town NPC scheduling and overworld encounter/object-pruning work are mode-specific steps after cleanup. The active-object animator instead runs from the resident world-tick redraw path while the input loop is waiting. The cleanup is the time clock; the mode loop and idle redraw path own the rest of the world's visible cadence.

## 9. The world tick and redraw

Between keystrokes the input pipeline runs a world tick — the resident *redraw orchestrator* that rebuilds the on-screen viewport. The tick has three internal paths:

- **Combat.** A blat-copy of the precomputed combat terrain grid into the viewport scratch grid. The combat overlay maintains the precomputed grid; the orchestrator only blits.
- **2D scene with the visibility-dirty flag set.** Run the centre-out visibility producer against the active map, the lighting threshold from the daylight cleanup (a squared-distance threshold, not a radius - see `systems/visibility.md` Section 3), local-light mask state, and viewport origin from the player position. Initialise the scratch grid to the "unknown / dark" sentinel, then expand outward from the player and reveal cells as the visibility carve permits. Clear the dirty flag.
- **2D scene with the dirty flag clear.** Refresh only the cells whose current value is the post-render zero. For each zero cell, fetch the world tile at the corresponding coordinate from the active map. Non-zero cells are left alone, preserving last-frame state.

After producing the scratch grid, the tick refines visibility by toggling certain marker tiles through the shared squared-distance lookup centred on the viewport, then renders. On the very first tick after a mode entry, an additional full-panel repaint runs, painting the side panels, status bars, and frame borders that the in-loop renderer otherwise leaves alone.

The world tick also runs three secondary subsystems before producing the grid: an active-object animator for per-frame sprite phases and eligible ambient wandering, a small RNG dispatcher, and a lighting / torch presentation timer.

The world tick is only called from inside the input pipeline's idle wait. It does not run when the pipeline is in prompt mode (a Y/N or numeric prompt has set a printable prompt-character byte). Prompt mode freezes the world while the player thinks. Cleanup time is gameplay time; prompt time is real time.

## 10. Disk-Prompt Presentation

The original game distributed across multiple floppies and carried resident
state for the currently requested disk or drive. The outer loop's between-mode
cleanup is presentation glue for that state: after a mode loop returns, it can
give the disk-prompt controller an opportunity to repaint or wait for the
active prompt context before the next gameplay mode is dispatched.

The outer loop does not define file I/O semantics. Failed reads and writes are
retried by the save/load I/O wrappers, while the visible prompt, active disk
hint, and per-mode prompt-state table are owned by
`systems/screen-mode-dispatch.md`. A modern engine that loads everything from
one directory can no-op the visible prompt path, but should keep the retry
contract described in `systems/save-load.md` for byte-compatible I/O wrappers.

## 11. Save and load integration

The save system writes a single image of resident state — player position, plane, scene byte, inventory, active-object table, time-clock bytes, party stats, transport marker/state tags, scroll origin, and a few hundred bytes of flags. The image lives on disk as `SAVED.GAM` plus a companion file with the per-plane active-object seed.

A load runs from the intro overlay's Journey Onward path. The path reads the saved image into the resident data segment, which makes the saved scene byte the active scene byte. The intro overlay then returns to the outer loop, which on its first iteration dispatches into whichever mode the saved value names. Each mode's entry pass is idempotent in the sense that it produces the same result when re-run with the saved bytes set as inputs.

A save is initiated from the resident Q command when that letter reaches the shared command dispatcher. The save logic freezes whatever the current resident state is. Combat is the exception: combat has its own command dispatcher and does not route through the resident Q save path.

## 12. Quit And Exit Paths

The resident Q command is a save-game prompt, not a DOS terminate by itself. On confirmation it writes the save files, acknowledges completion, and returns to the caller; on rejection it returns without writing. The active mode loop then continues from its normal post-dispatch path.

Explicit program-exit prompts are mode-loop control paths rather than the resident Q save handler. The dungeon loop has its own "Exit to DOS?" prompt before forwarding ordinary letters. The overworld loop also has a pre-dispatch quit prompt in its control-code table. Those paths can unwind or terminate play without changing the save-game writer's contract.

## 13. Hooks into other systems

**Boot sequence.** The intro overlay initialises every resident interrupt handler, the text-window descriptors, the timer-tick handler, and the display driver. Every later subsystem assumes these are in place.

**Time.** The per-turn cleanup is the time spec's ingestion point — every tick, hour, day, and month transition flows through it. See `time.md`.

**Input.** The input pipeline is the only blocking call in any mode loop. The pipeline's idle-vs-prompt mode determines whether the world tick runs between polls. See `input.md`.

**Active objects.** The per-mode loops each own the active-object table during their tenure; the combat framer save-and-restores the table around fights. See `active-objects.md`.

**Visibility.** The world tick is the only call site of the centre-out visibility producer. See `visibility.md`.

**Save / load.** The intro overlay is the load path's entry; the resident Q command is the save path. The saved scene byte drives the outer loop's first dispatch on resume. See `save-load.md`.

## 14. Main-Loop Boundaries And Variations

The main-loop contract is complete at scene-routing depth: startup handoff,
driver-letter argument parsing, scene-byte dispatch, playable mode loop
ownership, combat's non-outer-loop status, world-tick/redraw placement,
per-turn cleanup placement, save/load resume behavior, resident Q save
routing, and explicit exit prompt separation are fixed. The items below are
cleanup, overlay-loading, or refresh-only compatibility boundaries rather than
gaps in the playable scene router.

- **Driver-letter argv parsing.** The resident main entry reads only the first
  character of the first argument, folds it to uppercase, and recognizes
  `C`, `E`, `T`, or `H`. Because only one character is consumed, normal
  command-line parsing can set at most one explicit display request. Missing
  or unsupported first characters leave the explicit request unset, so startup
  falls through to boot-time display detection rather than producing a
  gameplay-visible error. Additional arguments have no known engine meaning.

- **Exit cleanup branches.** A handful of branches in the outer loop's cleanup pass — restore-video-mode on `main` return and disk-prompt presentation state cleanup — are not reached by the resident Q save handler. They exist for explicit exit/control paths and defensive cleanup.

- **The "exit pending" flag's exact role.** The flag prevents the overworld branch from re-entering itself when the scene byte is still zero after a return. In practice the only path that produces this is a rare cancel-during-overworld case; a modern engine can collapse the flag and the cleanup branch into the natural loop structure without observable difference.

- **Unused high scene values.** Readers often split "combat-class" work with a high-range comparison, but the only confirmed high-range writer uses `0xFF`. From the outer loop's perspective, `0xFF` is transient: the source mode's framer restores the home scene byte before returning.

- **Overlay buffer assignment.** The link-time partition of overlays to four shared buffers is now specified in `overlay-abi.md`. A modern engine that loads everything once into a flat memory model has no need for buffer sharing, but should preserve the same entry ownership and call order.

- **Mode arg of zero in cleanup.** Several entry handlers call the cleanup with a minute increment of zero. The intent is "refresh derived state without advancing the clock". A modern engine can collapse the zero-arg cases into a separate "refresh-only" entry without behavioural change.

## 15. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The DOS/runtime startup note that separates compiler setup from game-owned startup — `u5-decomp/functions/ULTIMA_EXE/0x81D0_boot_entry.md`.
- The `main` function and the forever-loop scene-byte dispatch — `u5-decomp/functions/ULTIMA_EXE/0x0000_main_game_loop.md`.
- The intro overlay's boot-init, title screen, and menu dispatch — `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md`.
- Overlay dispatch, loader behaviour, and the buffer-sharing partition — `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- The shared per-letter command dispatcher and its mode-aware routing — `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The redraw orchestrator that drives the world tick — `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The per-turn cleanup that advances time and recomputes daylight — `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The shared per-turn party-capability check that opens each exploration turn and routes a total-party defeat — `u5-decomp/functions/ULTIMA_EXE/0x39FC_find_paladin_or_shepherd.md`. Source provenance: derived from private analysis note `u5-decomp/notes/oq-closures_2026-08-22_blackthorn-town.md`, section Q2.
- The data-segment layout of the scene byte, time clock, daylight value, and disk-swap state — `u5-decomp/formats/data-ovl.md`.
- Disk-prompt presentation state and retry ownership —
  `u5-decomp/functions/ULTIMA_EXE/0x251E_disk_swap_request.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x256E_disk_swap_inner.md`, and
  `systems/screen-mode-dispatch.md`.
- The save-image encoding of the scene byte and the resumption rules — `u5-decomp/formats/saves.md`.
- The lifecycle trace that corrects the scene-byte value set and combat marker semantics — `u5-decomp/notes/critical_state_lifecycles.md`.
- The OUTSUBS ownership correction and DNGLOOK/DUNGEON dungeon-cluster
  cross-checks — `u5-decomp/functions/OUTSUBS_OVL/OVERVIEW.md` and
  `u5-decomp/notes/full_call_graph.md`.
