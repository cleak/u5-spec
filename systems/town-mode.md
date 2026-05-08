# Town mode

## 1. Overview

When the player steps onto an enclosed cell of the overworld — a town gate, a castle drawbridge, the entrance to a keep, the threshold of a dwelling — the engine pauses the overworld, swaps the active map for a thirty-two-by-thirty-two interior grid, loads the location's roster of named NPCs along with their daily routines, and hands control to the town-mode turn loop. The player walks among schedule-driven NPCs, talks to them, opens doors, climbs ladders to upper floors, takes things from chests, presents quest items to Lord British, and eventually walks back across the boundary to leave. Town mode is where most of the game's storytelling happens.

Town mode shares almost everything with overworld mode — the per-letter command dispatcher, the input pipeline, the active-object table for sprites, the renderer, the time clock — and adds three things on top: a different map, a population (the NPC roster and scheduler), and a per-turn invocation of the schedule processor that keeps NPCs walking on their daily routines while the player takes their own turn. The baker is at the bakery in the morning, the guards stand at the city gates during the day and head to the barracks at night, the farmer goes home for dinner.

One set of code, one set of file formats, one tile encoding, and one schedule format serve four superficially different location classes — towns, dwellings, castles, and keeps. The differences are entirely encoded in data: a castle has Lord British's throne room and audience prompts; a keep is barracked and patrolled; a dwelling is a single small house with a few NPCs; a town is everything between. From the engine's perspective they are identical.

This spec describes how town mode is entered, how the location's map and NPCs are loaded, how the per-turn loop dispatches commands and runs the scheduler, what role the player's second representation in the NPC table plays, how multi-floor locations are navigated, what the special interactions do at the town-mode level, and how the player exits.

## 2. The four location classes and the scene byte

The world has thirty-two named non-overworld locations divided evenly into four classes — towns, dwellings, castles, and keeps — eight per class. Every named location has a unique *scene byte* in the range one through thirty-two. The class is selected by the high bits of the scene byte and the index within the class by the low bits, so that:

| Scene byte range | Class    |
|------------------|----------|
| 1–8              | Town     |
| 9–16             | Dwelling |
| 17–24            | Castle   |
| 25–32            | Keep     |

The engine tracks the active scene in a single resident byte. Zero means "overworld"; values one through thirty-two put the engine in town mode for one named location; values above thirty-two are used for dungeon and combat states (described in their own specs). Walking onto an enclosed cell sets the scene byte; leaving via a boundary tile clears it.

Per-location data lives in four parallel families of files — one tile-grid file per class, one NPC roster file per class, one dialogue file per class. The roster and dialogue files use the per-class location index directly; the tile-grid file uses the same physical ordering but active floor pages are selected through the resident base-page table described below. The engine resolves the file family from `(scene - 1) >> 3` against a four-entry pointer table.

## 3. Per-location map data

A location's map is a thirty-two-by-thirty-two grid of one-byte tile indices, totalling 1,024 bytes per floor. Each per-class file contains sixteen such floor pages, physically arranged as eight two-page location pairs. Runtime floor selection is driven by a resident per-scene base-page table, not just by the physical pair: logical floor zero is the scene's base page, floor one is the next page, and floor `0xFF` is the previous page.

The active floor is loaded into a single 32×32 byte buffer in the resident data segment. Cell `(row, col)` is at buffer offset `row × 32 + col`; row indices increase southward, column indices increase eastward. The renderer reads this buffer for the static terrain layer; the active-object table (described in the active-objects spec) layers sprites on top.

The on-disk tile bytes are *terrain plus markers*. Most cells contain a tile ID — wall, floor, grass, water, door, chair, ladder — that the renderer paints directly. A handful of special tile values are *markers* that the location-load pipeline and NPC scheduler harvest, rewrite, or consume:

- **NPC start markers** (`0x48` or `0x49`) record where each rostered NPC begins. The location-load pass walks the grid, finds these markers, and records each marker's coordinates and exact marker byte.
- **Spawn markers** (the literal asterisk character byte) record one or two map-entry coordinates. The first asterisk encountered is the *primary* spawn (typically the entrance from the overworld); the second is the *secondary* (typically an alternate exit or a stairway-up landing). Locations with no asterisk inherit a default per-scene spawn coordinate.
- **Dash/period markers** (the dash and period tile values) are processed by a secondary pass that runs after the player has been placed. When the runtime predicate accepts them, they rewrite to nearby ordinary tile-detail values; they are not currently proven to be per-NPC route hints.
- **Chair/seat markers** (`0xC8` and `0xC9`) are consumed by the NPC scheduler's sitting pathfinder after map load. They must remain distinguishable in the live tile buffer for the schedule processor.

Marker processing is in-memory only: the on-disk `.DAT` floor is unchanged. By the time normal play begins, runtime passes have harvested the markers needed for spawn/NPC state and may have rewritten selected marker cells, while visible actors are represented through the dynamic sprite layer. Some markers, notably the chair/seat pair, remain meaningful to runtime consumers after the initial load pass.

The floor byte is interpreted as signed eight-bit for map loading. Values `0..127` are non-negative floors; values `128..255` are negative offsets from the base page. This lets a scene place its ground floor in the middle of nearby authored pages and reach a basement with `0xFF`, while still using the same 32×32 tile encoding for every floor.

## 4. Per-location NPC and dialogue data

Each named location carries a roster of up to thirty-one NPCs (slot zero is a sentinel). The roster lives in the per-class `.NPC` file, one 576-byte block per location, holding three parallel sub-blocks: a sixteen-byte schedule per slot, a one-byte type per slot, and a one-byte dialogue index per slot. Empty slots (zero type byte) are skipped at runtime. The schedule encoding and the per-tick walker are described in the NPC schedules spec.

Dialogue lives in the per-class `.TLK` file, indexed by the per-NPC dialogue index. The dialogue engine, described in its own spec, is invoked when the player initiates a conversation (Section 9).

Town mode's contract with the schedule system is one call per consumed turn: each turn-taking action calls the per-tick walker once, with the current hour byte. The walker iterates all thirty-one NPC slots and advances each NPC's state machine. Town mode reads the walker's "any NPC moved" scratch flag to decide whether the screen needs a repaint.

## 5. Entry: map load, NPC load, player attach

Entering a town is a single setup pass that runs once per entry, before the per-turn loop starts spinning. Six things happen, in order:

1. **State reset.** Active-object slots one through thirty-one are freed (type byte cleared); slot zero is left for the player. The "town entered" flag and visibility-dirty flag are set; transient frame-scoped flags are cleared.

2. **Tile-grid load.** The per-location floor page is loaded into the tile buffer (Section 3). Exactly 1,024 bytes — one floor of 32×32 — are read.

3. **Marker harvest.** The load pass walks the freshly-read tile grid cell-by-cell, finds NPC start markers and asterisk spawn markers, and records their coordinates into per-NPC-slot arrays and into the primary/secondary spawn slots. Later load-time passes handle any runtime tile-buffer cleanup or conditional marker rewrites.

4. **Dawn/dusk substitution.** The shipped maps store gate cells in their daytime, open form. When the current hour is in the night band (8 PM through 4 AM), a pass runs over the tile buffer and toggles the cell paired with each archway marker into its night, closed form. Section 6 describes the substitution in detail.

5. **NPC roster load.** For each occupied NPC slot in the location's `.NPC` block, the schedule and type are loaded into the resident schedule and type tables, the dialogue index is unpacked into the per-NPC runtime block, and the NPC's runtime state is initialised by sampling the schedule for the current hour. NPCs whose initial waypoint floor matches the current floor are linked into the active-object table; off-floor NPCs exist only in the schedule tables.

6. **Player attach.** The player is added to the active-object table at slot zero (the avatar) and given a phantom NPC entry — a high-indexed NPC slot whose schedule is three identical waypoints fixed at the location's per-scene entry coordinate. Section 8 describes the dual representation. The player's default spawn cell is `(15, entry_y, 0)`: X is fixed at fifteen, Y is read from the DATA.OVL-derived `LocationEntryYTable`, and Z is the ground floor. If the map-load pass found explicit asterisk spawn markers, command handlers may use those marker slots for stair/alternate landing paths, but the player-as-NPC attach contract uses the resident entry-Y table.

After these six steps return, the entry pass calls a final screen redraw and hands off to the per-turn loop. The player is in town mode until the loop's per-turn epilogue notices that the scene byte has been cleared (Section 15).

A *re-entry* — a player returning to a town that the engine briefly suspended for combat or a sub-mode — runs the same pass with one parameter changed: the active-object table is *not* zero-cleared, and the player-attach step short-circuits if it finds an existing player slot in place. Re-entries are therefore idempotent.

## 6. The dawn/dusk substitution

Town-class maps ship with gate approaches in their daytime, open form. Tile `0x87` is the marker: its `LOOK2.DAT` string names an archway, and the pass does not rewrite that marker cell. Instead, for every `0x87` it finds, the pass XORs the tile byte immediately south of the marker (`same column, row + 1`) with `0xDD`.

The stock assets use a single authored pair: every `0x87` marker that participates in the pass has `0x44` cobble in the paired south cell on disk. Applying the pass changes that byte to `0x99`, the portcullis tile; applying it again changes the byte back to `0x44`. The routine does not validate the paired byte before XORing it, so custom maps should only place `0x87` above a byte whose `value ^ 0xDD` partner is intentional.

On entry and floor reload, the loader runs the pass only in the night band: hours `0..4` and `20..23`. It skips the pass during the daytime band, hours `5..19`, leaving the shipped open-gate bytes in place. While the player remains in town, the normal turn epilogue watches for hour changes; when the new hour is `5` or `20`, it runs the same XOR pass against the current tile buffer. The visible effect is:

- A player who enters at 6 AM sees open gates; if they stay until 8 PM, the boundary pass toggles those paired cells to portcullises.
- A player who enters at 4 AM has the loader close the gates; when the clock reaches 5 AM, the boundary pass opens them again.
- A player who leaves and re-enters across the band boundary gets the tile buffer normalized from disk according to the saved/current hour.

## 7. The per-turn loop

After entry, control sits in a tight loop that reads one command per iteration and runs it to completion:

1. **Read a command.** The input pipeline blocks until a keystroke arrives, applies its translation rules (key-to-command, numpad-to-direction, queue handling), and returns a single byte.
2. **Pre-dispatch checks.** A short setup step handles meta-states (combat in progress, turn already in flight) and the cursed-by-spell timer. If the scene byte has been cleared during the previous turn — meaning the player just walked across a boundary tile — the loop breaks out (Section 15).
3. **Dispatch.** Movement commands walk through a small jump table indexed by direction code; letter commands flow into the shared per-letter dispatcher described in the commands spec. Many handlers live in the town-mode overlay (Attack, Klimb); others are shared across modes (Cast, Get, Look, Talk, Use) and resolve to the appropriate cross-mode handler after a scene-byte check.
4. **Per-turn epilogue.** When the dispatcher returns and the action consumed a turn, the loop snapshots the current hour, advances the time clock by one minute via the time spec's per-turn cleanup, runs the dawn/dusk gate pass if the new hour is `5` or `20`, copies the party's current map coordinates into slot zero, ticks down the curse/buff counter, and calls the NPC schedule processor with the current hour byte.
5. **Render.** If the schedule processor reported any NPC moved, or the visibility-dirty flag is set, a full render runs. Otherwise the screen is left as-is and the loop reads the next command.

The dispatcher's return code decides when to skip parts of the epilogue: actions that take no turn (a cancelled command, a "What?" fallthrough, the buffer-toggle key) skip both the time advance and the schedule tick. Actions that consume more than one turn advance the clock once per inner action.

The schedule tick is unconditional on consumed turns — every action that costs a turn advances NPCs by one tick — so an NPC walks at most one cell per player action.

The Hole-up command (Section 12) is the one path that bypasses this cadence. It runs the schedule walker directly in an inner loop, advancing several in-world hours at once. During rest the schedule ticks once per in-world hour, so during an eight-hour rest each NPC walks at most eight cells.

## 8. The player as NPC

Town mode keeps two parallel views of the player. The first is slot zero of the active-object table — the avatar sprite — owned by every world-mode renderer and updated each turn from the world-state globals. The second is an entry in the high end of the NPC slot table — a *phantom NPC* — whose schedule is three identical waypoints pinned to the player's spawn coordinate, whose AI byte is set to a stationary mode, and whose type byte is a player-sentinel distinct from any real NPC type.

The phantom exists because town-mode helpers — collision detection during NPC movement, conversation-target lookup at the facing tile, and a few other systems — walk the NPC table when they need to find a thing-on-this-cell. Without the phantom, those helpers would be blind to the player. With it, uniform code handles both NPC-NPC and player-NPC interactions: every walking, looking, and pathfinding helper just walks the NPC table, and the player participates the way every named NPC does.

The phantom has zero effect on the schedule walker. Its three identical waypoints make every transition trivial; its AI byte routes to a stationary behaviour; the player's current floor matches the location's current floor on every tick. The walker's per-NPC pass for the phantom slot completes in essentially constant time.

The active-object slot zero and the phantom's linked-object slot are different: the avatar's active-object slot is hard-coded as zero (the renderer relies on this); the phantom's linked-object slot is allocated like any other NPC's. Both might paint at the same cell. The system avoids double-painting by leaning on slot zero's "always last" render-order convention: the renderer walks slots from thirty-one down to zero, so slot zero (the canonical avatar) paints on top of any phantom-NPC sprite at the same cell.

The phantom is allocated on town entry and freed on town exit. Re-entries to the same town find the existing phantom and short-circuit allocation. Cross-location re-entries clear NPC slots and create a fresh phantom for the new location.

## 9. Conversation: the Talk command

The Talk command triggers the conversation engine. The handler reads the player's current facing direction, computes the facing tile as `(player_x + dx, player_y + dy)`, and looks for an NPC whose linked sprite occupies that cell. If found, the NPC's dialogue index is handed to the conversation engine. If not found, the handler tests the facing tile for *talk-through* status (shop counters, low fences); if pass-through, it advances once more and queries again. If still no match, "Nobody's here!" is printed.

A pre-conversation gate inspects the candidate NPC's current sprite tile to detect transient states: a "sleeping" tile produces "Zzzzzz...", a "no response" tile produces "No response!" — both return without entering the engine.

The Talk command is town-mode-only. The shared per-letter dispatcher routes T-Talk to the conversation engine when the scene byte indicates town mode; in overworld and dungeon modes the same key produces "Funny, no response!" or similar. There are no schedule-driven NPCs to talk to outside the named locations.

## 10. Special interactions

Several letter commands map to per-tile interactions that are interesting in town mode.

**Look.** L-Look prompts for a direction and samples the facing cell, then routes the terrain tile and active-object context through the shared world/town look handler. That handler resolves command-layer overlay markers to the tile being described, then either runs a special look path for wells, signs, and dungeon-mouth tiles or indexes `LOOK2.DAT` by the final tile id. Clock, shrine, and dungeon-entrance tiles print the base description and append their current context. Look does not consume a turn.

**Read sign.** Tile-class encoding for sign tiles triggers a prompt that loads the sign's text from a per-location sign data file, indexed by the sign's coordinates.

**Open / Jimmy.** O-Open applied to a door tile prompts for direction and triggers the door-open interaction: unlocked doors open (tile changes to "open door"); locked doors prompt for a key. J-Jimmy is the lockpick variant — it consumes a lockpick and either unlocks or breaks the lock. Both consume a turn.

**Push.** P-Push applied to a movable tile (chair, barrel, pushable cart) computes the destination cell on the far side of the pushed tile, and if the destination is walkable, swaps the two tile IDs in the live tile buffer. The player can then step into the freshly-vacated cell.

**Get.** G-Get applied to an interactable tile (chest, body, dropped item) runs the per-tile-class get-handler. Chests prompt for a key on locked variants; bodies are searched for items; dropped items are picked up directly. The handler is shared across modes.

**Use.** U-Use picks an item from inventory and applies its per-item action. Many items have town-mode-specific effects: a key opens the closest locked door, a magic gem reveals the local map, a torch lights nearby cells. The handler is shared across modes.

All these interactions except Look and inspect-style actions consume a turn and run the per-turn epilogue.

## 11. Multi-floor locations

Several locations span more than one floor. A castle has a throne room above and a great hall below; a dwelling may have a basement; a keep has watchtowers above the main floor. Floor changes are mediated by stairway tiles — ladders, staircases, and occasionally trapdoors.

The current floor is tracked in a single resident byte. When the player walks onto a stairway tile and triggers the climb (via K-Klimb, or automatically on certain stair tiles), the floor byte is updated, the tile buffer is reloaded with the new floor's data (running the marker-harvest and dawn/dusk gate-normalization passes again), the active-object table is partially reset (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and the player's slot is updated with the new Z. The schedule processor handles its own side through its Z-mismatch state machine described in the NPC schedules spec.

Visibility is per-floor: the visibility producer treats the active map as the only walkable surface and computes line-of-sight only against tiles in the current floor's tile buffer. NPCs on other floors are invisible and silent.

A handful of locations have *secret* floors — areas accessible only by a Push revealing a hidden trapdoor or by a quest-flag-gated stairway. The mechanism is identical to ordinary stairways; the gating is encoded in the tile-class table or in per-stairway behaviour. Town mode does not special-case secret floors.

## 12. The Hole-up command

H-Hole-up is gated by terrain: in town mode it runs only when the player is standing on a bed tile in an inn. On a bed it prompts for a duration in hours; off it, "Not here!" prints and no turn is consumed.

When the rest is accepted, control hands off to the rest handler in a shared overlay. The handler runs an inner loop of one iteration per in-world hour: advance the clock by sixty minutes via the per-turn cleanup, call the schedule processor with the new hour byte, roll a per-hour random-encounter check, and stop early if any event fires. At the end of the rest, control returns to the per-turn loop with party HP / MP partially restored.

Hole-up is the only path that runs the schedule processor outside the per-turn epilogue. The cadence differs (per in-world hour rather than per consumed turn) but the contract is the same: one call per tick advances every NPC by at most one cell.

## 13. Lord British's castle

One castle-family scene is Lord British's Castle, distinct in two ways. The
first verification slice binds the strongest roster/dialogue evidence to
`CASTLE:0`; do not rely on older notes that describe this as the fifth castle
slot until that private special-scene label is rechecked.

1. **Audience prompt on entry.** A quest-flag-gated check at the end of the entry pass examines a small audience-pending table; for each pending audience, an inline prompt fires that prints a per-audience preamble and waits for the player to acknowledge. The first time the player reaches Lord British, an introductory cutscene runs; subsequent entries are gated on quest progress.

2. **Quest-flag side effects.** Several actions inside the throne room — speaking to Lord British about specific keywords, presenting quest items — set quest flags that the audience-pending table consults on subsequent entries. The conversation system writes these flags through its `SET-FLAG` control byte; town mode reads them only via the audience prompt.

The castle's tile grid, NPC roster, and dialogue file are otherwise ordinary. The audience prompt is one extra step at the end of the entry pass, gated on the scene byte. A handful of other named locations have similar one-scene quirks (a scripted NPC arrival in one dwelling, a special-event stairway in one keep), encoded entirely in their data.

## 14. Combat triggers

Some named locations contain hostile NPCs. A guard in Blackthorn's keep, for example, is a normal NPC for most of the game but turns hostile under specific quest conditions — the type byte encodes "hostile when flag X is set". When an NPC's hostile predicate is true, the walker stamps the NPC's current sprite with a hostile tile.

A hostile NPC adjacent to the player blocks movement onto their cell ("Bump!"); A-Attack directed at a hostile NPC initiates combat. The combat framer saves the town's active-object table, swaps in a combat-instance map, runs the combat round loop, and on return restores the table. The town-mode loop continues from where it was; the encounter does not consume a town turn beyond what the framer charges.

NPCs whose hostile predicate is *always* true — robbers, bandits in certain backwater dwellings — initiate combat automatically: the schedule walker, finding such an NPC adjacent to the player, calls the combat framer directly without waiting for A-Attack.

## 15. Exit

The player leaves a town by walking onto a boundary tile — typically the same gate or threshold they entered through. The boundary is encoded in the tile-class table: a small set of tile values are flagged as exit tiles, and stepping onto one runs the exit handler, which clears the scene byte, computes the player's overworld coordinate from the fixed world-location coordinate tables, and signals the loop to break.

The town turn loop's per-turn epilogue checks the scene byte each iteration. When the byte clears, the loop returns to the main game loop, which reloads the overworld map, restores the overworld active-object table from the on-disk overlay, and resumes overworld mode at the location's overworld cell.

Exit is symmetric with entry: every per-location piece of state allocated during entry is cleared or freed; the next entry runs the full setup pass against the next location's data. There is no cross-town retention.

Soft exits — combat returning to the town, sub-modes re-entering the same town — do not clear the scene byte and short-circuit the entry pass on return. NPC slot state is preserved across the round-trip, so a guard who was at slot fifteen before combat is still at slot fifteen after.

## 16. Hooks into other systems

**Visibility.** Town mode shares the visibility producer with overworld and dungeon modes. The producer runs against the location's tile buffer and the active-object table on each render. Town mode sets the visibility-dirty flag on entry, on floor change, and on schedule-walker reports of "any NPC moved", forcing a recompute.

**Command dispatch.** The shared per-letter dispatcher receives every keystroke not handled by the town-mode movement table. It routes mode-aware commands (A-Attack, K-Klimb, T-Talk) to town-specific handlers and shared commands (G-Get, P-Push, V-View) to cross-mode handlers.

**NPC schedules.** Town mode invokes the schedule processor exactly once per consumed turn, and once per in-world hour during rest.

**Conversation.** The Talk command hands the dialogue engine the NPC's dialogue index; the engine runs a self-contained per-NPC loop until the player exits.

**Time.** Each consumed turn calls the time spec's per-turn cleanup with a one-minute increment. The cleanup advances the clock, refreshes daylight, and triggers any once-per-hour side effects. When that one-minute cleanup changes the hour to `5` or `20`, town mode also runs the dawn/dusk gate substitution against the loaded tile buffer.

**Active objects.** Town mode owns the active-object table during a town visit. Entry clears it (preserving slot zero), the schedule walker fills it from the NPC roster, the per-turn loop refreshes slot zero from world-state on each iteration, and the combat framer transiently swaps it during attack handling.

**Save / load.** A save inside town freezes the scene byte, the floor byte, the player position, the active-object table, and the world-state clock. On load, the engine notices the non-zero scene byte, re-runs the entry pass, and snaps the player and NPCs to saved-or-re-derived positions. The runtime NPC block is not persisted as a chunk; it is re-derived from the schedule and the saved hour, producing NPCs at their currently-scheduled location regardless of mid-route progress. The dawn/dusk gate pass runs at load time using the saved hour.

## 17. Open questions and variations

- **Audience-prompt logic at Lord British's Castle.** The audience-pending table is consulted on every entry, but the data flow that populates it (which quest events set which entries) is plot-dependent and not enumerated here. A modern engine should treat the table as data and drive it from the quest-flag store.

- **Hidden-room mechanics.** A few locations have rooms accessible only via Push or via a quest-flag-gated tile change. There is no engine-level "hidden rooms" feature; the gating lives in the per-location tile data.

- **The Y == 4 short-circuit on town entry.** The player-attach helper has a special-case path that skips the perm-loc search when the player's Y coordinate equals four. Plausibly a "returning from sub-mode" sentinel, but the exact write site has not been confirmed.

- **The two paired NPC start markers.** Two adjacent tile values both serve as NPC start markers, with the low bit ignored. The intent of the low-bit distinction — facing hint, static-versus-walker — is not pinned down. The marker harvest treats them identically.

- **Boundary-tile mapping for exit.** The set of tile values flagged as exits is small and per-location data-driven. A modern engine should treat the exit set as data.

- **Soft re-entry preservation.** Combat-and-back preserves the active-object table; dungeon-and-back may not. The exact set of preserving sub-modes should be matched empirically against original-game behaviour.

## 18. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The town-mode entry handler that loads the location's map, runs the marker harvest, applies the dawn/dusk gate substitution, and attaches the player — `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The per-turn loop that reads commands, dispatches, runs the schedule walker, advances time, and toggles gates at the dawn/dusk hour boundaries — `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The per-location map loader, the marker harvest, and the dawn/dusk gate substitution — `u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md`.
- The player-as-NPC attachment helper and the phantom-NPC schedule synthesis — `u5-decomp/functions/TOWN_OVL/0x02AE_town_attach_player_slot.md`.
- The world-mutation primitive that links logical NPC state to active-object slots — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The NPC roster loader for one location — `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md`.
- The per-tick NPC walker invoked once per turn from the town loop — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The NPC pathfinder notes that bind chair/seat marker IDs `0xC8` and `0xC9` to the sitting schedule path — `u5-decomp/functions/NPC_OVL/0x01A0_npc_path_probe.md` and `u5-decomp/functions/NPC_OVL/0x01D2_npc_floodfill_workspace_prep.md`.
- The shared per-letter command dispatcher routed by mode — `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The per-turn cleanup that advances the clock and recomputes daylight — `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The location tile-grid file format and the two-floor-per-location layout — `u5-decomp/formats/maps.md`.
- The NPC roster and dialogue file formats — `u5-decomp/formats/npc-tlk-pth.md`.
- The first verification slice for Lord British's castle scene binding and
  town-mode load smoke checks — `u5-engine/reports/lb-throne-room-slice.txt`.
- The save image's scene-byte encoding and the per-location coordinate state — `u5-decomp/formats/saves.md`.
