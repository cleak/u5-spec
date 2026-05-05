# Overworld

## 1. Overview

Ultima V's overworld is the open-air mode the player spends the most time in. Two surfaces share the mode: **Britannia**, the surface world the game opens on, and the **Underworld**, the lightless mirror beneath it. Both are 256-by-256 tile grids driven by the same mode loop, the same camera, the same per-turn cadence. They differ only in which on-disk grid the engine reads tiles from, what default lighting the time system applies, and which cells contain the small fixed set of features that distinguish them — moongates and town entries on the surface, a uniformly dark and chasm-strewn cavern below.

Within either surface the player commands a small party (or a vehicle carrying that party) and walks one cell per turn. Around the party live the *active objects* — wandering monsters, vehicles, dropped items, the moongates when visible, the player avatar slot itself. Each turn, the engine reads a command, dispatches it, advances time by two minutes, ticks every animated entity, rolls the random-encounter check, refreshes the daylight value, and rebuilds the on-screen viewport. When the command is "Enter" on a town tile, "fall" on a chasm, or "land on the gate", the loop sets a scene byte that the resident main-game loop sees on its next iteration, and overworld mode exits back to the dispatcher, which spins up town mode, dungeon mode, or the moongate teleport.

The overworld is a thin shell over the resident systems. Almost everything that has its own spec — input, time, active objects, visibility, save/load — does the same work in this mode that it does anywhere else. The overworld's specific logic is small: which command goes where, when to load a chunk from disk, how to recognise the eight or nine tile types that mean "something special happens here", and a per-turn animator that is the dual of the town-mode NPC scheduler but does *not* consult the in-world hour. This spec describes those overworld-specific pieces and how they hook into the rest of the engine.

## 2. The two surfaces

Britannia and the Underworld are the two values the *world plane* selects between. The plane is a single byte in the save image — the party's *Z* coordinate — and is consumed almost everywhere that decides which on-disk file a tile-read should hit and which lighting model to apply. Z is zero on Britannia and the all-ones byte (signed −1) in the Underworld.

The player crosses between planes through three tile-driven transitions:

- **Falling.** A small fixed set of "chasm" tiles on Britannia trigger a scripted falls handler. The handler prints a "F-A-L-L-S!" banner and a "Falling into the underworld" line, applies a random fall-damage roll to each conscious party member, swaps the world plane to the underworld value, and re-initialises the active-object table for the new plane. The trigger coordinates are hard-wired and fixed across all playthroughs.

- **Ascending.** The mirror operation: certain underworld tiles re-promote the party to the surface at a corresponding fixed coordinate.

- **Moongate teleport.** When the player walks onto a visible moongate tile, the per-turn block prompts and either teleports inside the surface or, on certain phase combinations, deposits the party in the underworld (Section 9).

The mode loop itself does not branch on Z. The chunk loader, the visibility producer, the renderer, the daylight calculator, and the random-encounter spawner treat the two planes identically — what differs is the data the helpers consult: a different on-disk grid (Section 3), a forced full-darkness ambient light on the underworld plane, and a different active-object seed file.

## 3. Map structure

Each surface is a flat 256-by-256 grid of tile bytes — one byte per cell, no padding. The grid is held on disk as a sequence of 16-by-16 *chunks*, each chunk a 256-byte block laid out row-major. The world has 256 chunks total (sixteen across by sixteen down), and the mapping from chunk grid position to disk offset goes through a 256-byte *chunk-index table* in the resident data segment.

The chunk-index table encodes one byte per chunk in row-major order. The byte is either a chunk's 0-based index in the on-disk file or the all-ones sentinel meaning *all-water*. On Britannia, large stretches of open ocean are pure water, and the on-disk grid omits those chunks — only the non-water chunks are stored. The index byte for a water chunk is the all-ones sentinel; the chunk loader recognises this, fills the chunk buffer with the water tile, and returns without doing any disk I/O. A non-sentinel index is the zero-based file index, multiplied by 256 to give the seek offset. This compression-by-omission is why Britannia's on-disk grid is about 52 KB rather than 64 KB.

The Underworld is dense — every chunk is stored, including uniformly cavern ones. Its on-disk grid is exactly 64 KB and its chunk-index table is the identity. The same table format is used; only the contents differ.

After a chunk is loaded, the loader walks each cell applying a small set of *substitutions*: certain animated tile values are replaced by their alternate-frame value as a function of the global animation phase, so a body of water flickers through its multi-frame cycle without the renderer needing to know about animation. Substitutions are applied to the in-buffer copy, leaving the on-disk chunk untouched.

The visible viewport at any moment is an 11-by-11 window centred on the party. To service it, the engine keeps four 16-by-16 chunks live in a 1-KiB *chunk buffer* in the data segment, arranged as a 2-by-2 grid. The four chunks together form a 32-by-32 cell window, of which the renderer projects the central 11-by-11. Movement crossing an internal cell boundary is satisfied from the buffer; movement crossing a chunk boundary triggers a reload (Section 4).

The on-disk filename for Britannia is `BRIT.DAT` and for the Underworld `UNDER.DAT`. A small companion file per plane (`BRIT.OOL` / `UNDER.OOL`) holds the seed active-object table; see Section 11.

## 4. The camera and the chunk buffer

The viewport is an 11-by-11 window centred on the party. The chunk buffer holds a 32-by-32 window of the world, anchored at a chunk-aligned origin — the *scroll base* — at a multiple of sixteen on each axis.

Per turn, the per-tick init recomputes the scroll base from the party position:

1. Round the party's tile position down to the nearest multiple of sixteen.
2. If the party's position within that chunk is in the upper or left half (its low nibble is less than eight), step the scroll base back another sixteen.

The result is a chunk-aligned window with the party near the centre most of the time. The "step back when in the upper half" rule provides hysteresis so the buffer reloads only when the chunk-aligned scroll base actually changes — once every sixteen cells of motion in steady walking.

The aligned origin determines which four chunks live in the buffer: the chunk at the origin and the three to its east, south, and southeast. The tile-reader projects (world X, world Y) into this buffer by subtracting the scroll base, masking to five bits per axis, splitting on the sixth bit to pick the quadrant, and indexing in row-major within that quadrant.

Two helpers manage the buffer:

- **The four-chunk reload.** When the scroll base changes, this helper re-reads the appropriate chunks from disk, taking a (dx, dy) direction and reloading only the chunks that crossed in. The Z byte selects which on-disk grid to read. After the reload, the per-plane companion file is opened and four bytes of "scroll position" indicators are written for the on-screen status display.

- **The chunk shuffler.** When the scroll base shifts but the new window overlaps the old, the chunks already in the buffer can be slid into place rather than re-read. The shuffler does a simple block-copy pass — pure data-segment work, no I/O. Reloader and shuffler are typically used together: the shuffler covers chunks that still apply, the reloader fills in chunks that just rolled in.

The 1-KiB buffer is the resident representation of "the world right now". The visibility producer reads from it; the renderer composites from it; the per-turn block consults the tile under the party from it. The same buffer is reused for town and dungeon scenes — those modes' entry handlers refill it with a single 32-by-32 grid loaded from a different on-disk file — but in the overworld it is interpreted as the four-quadrant 2-by-2 chunk window described above.

## 5. The per-turn loop

Every iteration walks the same sequence:

1. **Per-tick init.** Refresh the visibility-dirty flag, the redraw-enabled gate, the master "fresh frame" flags, the found-object cache. Recompute the scroll base; if it changed, reload chunks. Run the world-buffer commit twice with a viewport rebuild between, then flush the screen. None of this advances time.

2. **Pre-loop tile probe.** Read the tile under the party. If it is the water tile, raise an "in-water" flag for this iteration; this is the hook a few water-specific behaviours pull on. The water-specific path also clears the light radius to zero so the visibility producer treats the player as having no torch — water cells are dark.

3. **Block on input.** Call into the input system's keystroke fetch. Sub-printable codes are control keys (cursor, special), printable letters are commands like A-attack, E-enter, T-talk, K-klimb, and digits go to the party-speed selector.

4. **Mode-switch exit check.** If the *scene byte* has gone non-zero since last iteration — because a sub-handler dispatched into town, dungeon, or combat — break out and return to the resident main-game loop.

5. **Dispatch the command.** Three layers: control codes go through a small jump table; digits go to the speed selector; everything else goes to the resident command dispatcher, which routes single-letter verbs to per-letter handlers in this overlay (Attack, Enter, ...) or to one of the action overlays (Cast, Talk, Look, Stats, ...). The dispatcher returns 0 for a no-op (or cancelled action) or 1 for an action that consumed a turn.

6. **Per-turn block (only when the action consumed a turn).**
   a. Run the per-turn cleanup (see `time.md`) with a minute increment of two — the standard outdoor turn cost.
   b. Re-read the tile under the (now possibly moved) party.
   c. Camp / wishing-well dispatch if the tile matches.
   d. Pirate-ship ambush if the tile and vehicle byte indicate one.
   e. Moongate landing prompt if on a moongate cell on the surface plane.
   f. In-water side-effect handler if the in-water flag is set.
   g. Per-turn party-status tick (Section 13).
   h. Active-object animator if the under-tile is animated (Section 6).

7. **Loop.** Back to step 1 unless the exit flag is set.

The "consumed a turn" gate means looking at the sky, opening the inventory, mistyping a command, talking-to-no-one cost zero time. Only a successful action advances the clock.

## 6. Active objects and the per-turn animator

Like every other gameplay mode, the overworld owns a 32-slot *active-object table* in the resident data segment (see `active-objects.md`). Slot zero holds the player; the other slots hold:

- **Wandering monsters** — pirates, dragons, sea serpents, troll bands, gargoyle parties, gremlins. Spawned by the random-encounter trigger, kept alive between turns, animated each turn, pruned when they drift outside the view window.
- **Vehicles** — ships, skiffs, horses, magic carpets, balloons. The plane's seed `.OOL` pre-places standard ones; player-dropped vehicles get a slot when the player exits them; ridden vehicles disappear from the table while carrying the player.
- **Pre-placed objects** — chests, items dropped by previous play, plot-significant overworld props.
- **Moongates** — when active. The animator writes directly to the rendered buffer rather than placing a slot, but the moongate's spawn-and-despawn determines whether a "moongate tile" appears in the player's view.

Each turn that the per-turn block reaches the animator, the animator walks the active-object table from slot 31 down to slot 1. For each non-empty slot whose tile class is *animated* (a small set of class ranges including monsters, certain vehicles, animated effects), it:

1. **Animates the slot.** Advance the slot's animation phase, swap to the next frame's tile id, and roll a wandering-AI step for hostile monsters (see `active-objects.md`).
2. **Prunes the slot if off-screen.** If the slot's (X, Y) is more than 32 cells away from the scroll base on either axis, free the slot. This caps the live monster set to whatever currently lives in the player's neighbourhood.

The animator does not consume the in-game hour; nothing in the overworld animator branches on time-of-day. NPC schedules — the structured "this character is at the bakery 8 AM to 5 PM" mechanic — are a *town-mode-only* concept. Overworld monsters wander but they do not have schedules.

A small *pendulum gate* sits on top of the animator: when the scene-type byte indicates one of two transient states (a pending town-entry handshake, certain vehicle states), the animator either bails immediately or runs only on alternate turns. This is the same mechanism town mode uses to slow NPCs to half-speed; in the overworld it serves to suppress unwanted animation while the engine is mid-transition.

## 7. Random encounters

The per-turn block fires a random-encounter check on every turn that reaches the animator. The check is roll-and-threshold:

1. The encounter probe consults the current world tile class, party state (vehicle byte, Z plane), and a few hidden modifiers (encounter-suppression flags, double-encounter flag), producing a *threshold* in a range covered by a 30-sided RNG.
2. The mode loop draws a 30-sided random integer.
3. If the draw exceeds the threshold, the spawner fires.

The spawner picks a tile class and a placement cell (off-screen or just at the edge of the visible window) and writes a fresh active-object slot. The slot animates on the next pass and may walk into the viewport over following turns. Whether the player engages is up to the player; the encounter system places monsters near the party, it does not directly enter combat.

Combat is entered when a movement command attempts to step onto a hostile monster's tile, when the per-turn block matches a pirate-ship trigger, or when an ambush event fires from a script. See `combat.md`.

The exact threshold formula and per-tile-class distribution are not yet pinned down (Section 14). Empirically, the rate is highest in forest, swamp, and underworld terrain; lowest in open grassland.

A handful of *scripted* encounters bypass the random system. Pirate ships, for example, are placed on specific Britannia coordinates by the seed `.OOL` and follow their wandering AI from there.

## 8. Special tiles

A small set of tile classes triggers special handling in the per-turn block, recognised by the post-action tile probe at step 6b. Each class corresponds to a small handler that may print a prompt, dispatch into another mode, or apply a status effect:

- **Town/keep/dwelling/castle entrance.** When the player's last action was Enter (E) on a coordinate matching one of the entries in the resident *location-coords* tables, the entry helper prints the location's name, waits for the appropriate disk to be inserted, clears the active-object table, sets the scene byte to the matching town index (a value in the town/keep/dwelling/castle range), and sets the party position to the conventional town-entry coordinates inside the destination town. The mode loop sees the non-zero scene byte and exits to town mode.

- **Dungeon entrance.** Same shape as town entry, but the scene byte goes into the dungeon range that the resident main-game loop dispatches into dungeon mode rather than town mode.

- **Shrine.** A meditation prompt with its own subsystem handlers; from the overworld's perspective, the trigger is a tile-class match.

- **Moongate.** Section 9.

- **Falls (chasm).** A small set of fixed Britannia coordinates triggering the underworld transition.

- **Camp / wishing well.** The H (Hole-up) command runs a multi-screen UI for rest, eating, and a per-camp event roll. Camp is its own mini-system; from the overworld it is a sub-handler that runs to completion and returns the party to the same cell.

- **Ship-with-pirate.** When the under-tile is the boarded-ship class and the vehicle byte indicates an enemy ship has been engaged, the per-turn block dispatches into ship-combat ambush. This is the overworld's only non-movement combat trigger.

- **Wells, springs, caves.** Smaller tile classes with their own minor handlers — give a hint, restore a small amount of MP, drop a chest.

The order in which the per-turn block tests these classes matters for correctness. The handlers themselves are mostly thin: most either set the scene byte and let the mode loop exit, or run a small interactive flow and return to the same cell.

## 9. Moongates

Moongates are the surface plane's signature feature. Eight of them, one per virtue, appear and disappear at fixed in-game hours and teleport the party between fixed locations on a multi-day cycle.

The moongate state is kept in five bytes in the resident data:

- **Origin (X, Y).** Two coordinates marking the cell where the gate appears. The all-ones sentinel value means "no gate is currently active".
- **Destination (X, Y).** The cell the gate teleports to. The all-ones sentinel means "single-ended" — a gate that exists for visual effect but does not teleport on landing.
- **Animation phase counter.** A byte cycling through a 16-frame open/full/close animation. The all-ones value is the "uninitialised" state; the first valid call paints the open frames, subsequent calls advance the cycle, and on overflow the counter wraps.

The moongate animator runs once per render frame from the overworld redraw orchestrator. It checks two preconditions: ambient light at or above the daytime threshold (gates do not appear at night) and an active origin (the all-ones sentinel skips the body). When both pass, the animator stamps the moongate sprite into the rendered tile buffer at the origin (and at the destination if not the all-ones sentinel) using a 16-byte sprite plate indexed by the current phase, then bumps the counter.

The animator is self-contained — it writes directly to the rendered buffer rather than placing an active-object slot. This means the moongate appears and disappears based purely on the animator's two preconditions; the active-object animator does not need to know moongates exist.

The *placer* — the code that sets origin and destination — runs from the time system's hour-change hook. On each hour change while the player is on the surface, the hook recomputes moongate state from the in-world calendar:

- The day of the lunar cycle (derived from day-of-month and the per-13-day counter; see `time.md`) selects a position on the eight-virtue ring.
- Each gate has a fixed *origin* per day on the ring.
- Each gate's *destination* depends on the second moon's phase, cycling through a separate eight-position pattern.
- During specific hours, the gate is *active* — origin and destination are written, the animator runs. Outside those hours, the all-ones sentinel is written to the origin, the animator skips, and the gate is invisible.

The *landing prompt* fires from the per-turn block when the party stands on a coordinate matching the current origin. The prompt asks whether to enter the gate; on yes, the destination is written into the party position (or, on certain phase combinations, the destination is in the underworld and the Z byte flips); on no, the prompt closes and the player remains on the cell.

The gates' destinations form Britannia's in-game fast travel. The four "sleep" hours of each day are when most gates are visible; a fast traveller manages their schedule around the gate hours and their day-of-month around the desired destination.

## 10. Lord British's path

A scripted path drives one cosmetic animation in the title sequence: Lord British, in his throne room, traces a pattern that spells out his signature in the floor tiles. The path is stored in `BRITISH.PTH`, in the same path-format that NPC schedules use (see `npc-schedules.md`). The animation is part of the title-screen overlay, not the overworld loop, but the file's existence and format match the same per-NPC path layout used elsewhere. The path file is consumed only at title time; once gameplay starts, it is unread for the rest of the session.

## 11. Vehicles

The party's transport state lives in two bytes of the resident data: the *vehicle byte* and the *scene-type* byte. Together they describe what the party is in or on; the per-turn block consults them to decide turn cost, terrain restrictions, and special handling.

The vehicle byte takes one of a small set of single-character values:

- **On foot.** The default. No vehicle byte set; standard 2-minute outdoor turn.
- **Horse.** Faster overland travel — uses the standard 2-minute increment, but the dispatch system treats horse-mode movement as a multi-cell stride per turn. Cannot enter water.
- **Skiff.** Water-only, slow. The vehicle byte's value is the letter `Q`. The time system halves the turn's minute increment, with a one-minute floor — water travel takes half as long per cell as land but is never instantaneous.
- **Ship.** Water-bound but faster than skiff. Uses the standard outdoor turn cost.
- **Tower / magic carpet (`T`).** A zero-time vehicle. The time system recognises this byte's value and skips the minute increment entirely. The exact identity of the `T` vehicle — whether the magic carpet, a tower-mounted vehicle, or another entry in the in-game list — is one of the open questions (see `time.md` Section 12).
- **Balloon.** Wind-driven aerial travel, with its own movement constraints (cannot land except on certain tiles, drifts on the wind direction). Uses the standard outdoor cost.

The vehicle byte is part of the save image and persists across save/load. Boarding (B-board) sets it; exiting (X-it) clears it. Dismounted vehicles live as active-object slots on the world stage and remain there indefinitely.

## 12. Time advancement

Each overworld turn that consumes the player's action advances the clock by **two minutes**. The time system's per-turn cleanup is called by the mode loop's per-turn block with the increment value 2.

Two vehicle modifiers apply:

- **Skiff.** The increment is halved (with a one-minute floor) before the cascade runs.
- **Tower / magic carpet (`T`).** The increment is forced to zero — cleanup still runs (still recomputes daylight, still checks for hour boundaries that may force special events) but the minute counter does not advance.

The cleanup itself does the cascade — minutes to hours, hours to days, days to weeks, weeks to years — and runs the day-rollover bundle (per-character daily counter, day-scope flag clears) at midnight crossings. On any hour change while the player is on the surface, an "hour event" callback fires; this is the hook that updates moongates and may also be where the hourly random-encounter roll and a few minor world events live. The full cleanup contract is in `time.md`.

Two notable absences from the overworld's per-turn cleanup compared to town mode:

- **No NPC scheduler.** The schedule processor is not invoked from the overworld loop. NPC schedules are a town-mode-only concept.
- **No special "no-time" interactions.** Overworld turns either consume the standard increment or are no-ops at the dispatch level (the dispatcher returns 0 for actions that do not consume a turn, and the per-turn block skips the cleanup for those).

## 13. Hooks into other systems

**Visibility.** The producer reads the chunk buffer for terrain blockers, the active-object table for dynamic blockers, the daylight value for ambient light, and the player's torch / spell counters for personal light sources. Daylight on the surface follows the time system's day-night curve; on the underworld, the time system forces full-darkness regardless of hour. A water-tile under the party clears the light radius for the duration of the iteration.

**Command dispatch.** The mode loop hands every printable letter to the resident command dispatcher (see `input.md`). The dispatcher routes A-Attack and E-Enter to in-overlay handlers, X-Exit and B-Board to vehicle handlers, K-Klimb and D-Descend to ascent/descent handlers, and the rest of the alphabet to action overlays loaded on demand.

**Active objects.** The overworld owns the player slot and a fixed quota of monster/vehicle/object slots. The per-turn animator, the random-encounter spawner, and the off-screen pruner all operate through the table. The combat framer save-and-restores the table around fights so the world resumes exactly as it was. Plane-swap (Z change) re-initialises the slots from the destination plane's seed `.OOL` file.

**Time.** Per-turn cleanup runs once per consumed turn at increment 2; mode-zero recomputes run from the per-tick init at entry. The moongate hook fires on hour change.

**Save / load.** The full state — party position, plane, active-object table, vehicle byte, scene-type byte — sits in the save-image region described in `save-load.md`. The seed `.OOL` files are mirror-written on every save so per-plane state is always current.

**Combat.** Entered when a movement command targets a hostile monster's tile, when the per-turn block matches a pirate-ship trigger, or when an ambush event fires. The framer suspends the active-object table, runs a self-contained fight, and restores the table on return. See `combat.md`.

**Conversation.** The Talk command is *not* available in overworld mode (there are no scheduled NPCs to address). The dispatcher returns "no-op" for T outdoors. See `conversation.md`.

**Text output.** All overworld banners, prompts, and messages go through the standard text output stack. See `text-output.md`.

## 14. Open questions

- **Encounter probability formula.** The 30-sided draw and threshold-exceeds gate are confirmed; the formula behind the threshold (which tile classes give which biases, how the vehicle byte modulates the rate, whether time-of-day affects it) is not.

- **Tile-class enumeration.** Several tile-class checks in the per-turn block test against specific class ranges (camp class, moongate class, falls coordinates, ship-with-pirate class). The full enumeration of these ranges and their corresponding visual tiles is partially documented but not exhaustively mapped. The boundary between "monster classes the animator ticks" and "static prop classes" needs the full tile palette.

- **Fall-trigger coordinates.** The full set of "fall into the underworld" coordinates on Britannia is not exhaustively enumerated; only one centrally located trigger is documented. The mirror set of underworld-to-surface ascents is similarly open.

- **Vehicle byte values and full set.** The skiff (`Q`) and tower (`T`) byte values are documented because the time system reads them. The full table — horse, ship, balloon, magic carpet, raft, the various types in the in-game manual — and which letter each maps to is not fully traced.

- **Moongate placement schedule.** The animator and landing prompt are documented; the per-day, per-hour table that drives where each gate appears and where it sends the player is encoded in resident data but the specific layout is one of the still-open questions.

- **Per-turn modulators.** A few flag bytes in resident state modulate the per-turn block (suppress encounters during a quest segment, force a double-roll after a specific event). The day-rollover bundle (`time.md` Section 7) clears them at midnight; what sets them and how they affect the encounter probe is open.

- **The "in-water" status side-effect.** When the party is in a water tile without a vehicle, a status side-effect handler runs that may apply drowning damage; the exact mechanic is not yet pinned down.

- **The chunk-substitution rules.** The chunk loader applies a small set of tile-byte substitutions after each disk read (water frames, certain animated terrain). The full table and the global animation phase that drives them needs a sweep of the loader's body.

- **The scene-type byte's `Q`-pendulum case.** The per-turn animator gates on a "scene-type is Q" pendulum that toggles between alternate-turn states. Which gameplay scenario this corresponds to is open.

## 15. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The overworld mode-loop main body — `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The per-tick init that recomputes the scroll base and refreshes redraw flags — `u5-decomp/functions/MAINOUT_OVL/0x0000_mainout_entry.md`.
- The per-turn epilogue that walks the active-object table, animates and prunes, and rolls the random-encounter trigger — `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The OUTSUBS overlay's collection of overworld helpers — `u5-decomp/functions/OUTSUBS_OVL/OVERVIEW.md` and the eleven per-function notes in that directory: `0x0000_outsubs_water_check.md`, `0x004A_outsubs_chunk_classify.md`, `0x0098_outsubs_load_chunk.md`, `0x01B4_outsubs_load_4chunks.md`, `0x02C8_outsubs_scroll_chunks.md`, `0x0368_outsubs_world_filename.md`, `0x0388_outsubs_check_town_entry.md`, `0x0458_outsubs_falls_handler.md`, `0x0566_outsubs_actor_init.md`, `0x05FC_outsubs_check_status.md`, `0x0658_outsubs_camp_or_save.md`.
- The world-tile getter that reads from the chunk buffer with the four-quadrant 2-by-2 interpretation — `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The moongate animator that paints the open / full / close cycle into the rendered buffer — `u5-decomp/functions/ULTIMA_EXE/0x70A6_moongate_or_event.md`.
- The render-loop orchestrator — `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The visibility producer that produces the 11-by-11 viewport scratch grid — `u5-decomp/functions/ULTIMA_EXE/0x5D0A_visibility_producer.md`.
- The per-turn cleanup that advances time, refreshes daylight, and dispatches the hour-change hook — `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The on-disk format of the surface and underworld grids — `u5-decomp/formats/maps.md`.
- The data-segment layout, including moongate state, chunk-index tables, and location-coords tables — `u5-decomp/formats/data-ovl.md`.
