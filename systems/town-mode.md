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

Per-location data lives in four parallel families of files — one tile-grid file per class, one NPC roster file per class, one dialogue file per class — and within each file the eight per-class blocks are addressed by `scene & 7`. The dwelling at scene byte twelve is the fourth block of `DWELLING.DAT`, `DWELLING.NPC`, and `DWELLING.TLK`. The engine resolves the file family from `(scene − 1) >> 3` against a four-entry pointer table.

## 3. Per-location map data

A location's map is a thirty-two-by-thirty-two grid of one-byte tile indices, totalling 1,024 bytes per floor. Each location has up to two floors — typically *ground* and *upper* (or *basement*) — stored back-to-back in the per-class file as a 2,048-byte pair. The four shared files each hold eight such pairs, totalling 16,384 bytes per file.

The active floor is loaded into a single 32×32 byte buffer in the resident data segment. Cell `(row, col)` is at buffer offset `row × 32 + col`; row indices increase southward, column indices increase eastward. The renderer reads this buffer for the static terrain layer; the active-object table (described in the active-objects spec) layers sprites on top.

The on-disk tile bytes are *terrain plus markers*. Most cells contain a tile ID — wall, floor, grass, water, door, chair, ladder — that the renderer paints directly. A handful of special tile values are *markers* that the location-load pass strips out and converts into runtime state:

- **NPC start markers** (one of two paired tile values) record where each rostered NPC begins. The location-load pass walks the grid, finds these markers, and records each marker's coordinates and the underlying tile that should appear there at runtime.
- **Spawn markers** (the literal asterisk character byte) record one or two map-entry coordinates. The first asterisk encountered is the *primary* spawn (typically the entrance from the overworld); the second is the *secondary* (typically an alternate exit or a stairway-up landing). Locations with no asterisk inherit a default per-scene spawn coordinate.
- **Waypoint hint markers** (two paired tile values matching the dash and period characters) carry per-NPC route hints, processed by a secondary pass that runs after the player has been placed.

Marker stripping is *destructive*: by the time the load pass returns, the runtime tile buffer no longer contains marker bytes. Subsequent reads of the buffer see only ordinary terrain plus the dynamic sprite layer.

The two-floor stride is uniform: floor zero is the first 1,024 bytes of the location's pair; floor one is the next 1,024. A handful of locations encode a third level (basement plus ground plus upper) by repurposing the floor-index byte's high values; the engine treats those as additional floors using the same encoding.

## 4. Per-location NPC and dialogue data

Each named location carries a roster of up to thirty-one NPCs (slot zero is a sentinel). The roster lives in the per-class `.NPC` file, one 576-byte block per location, holding three parallel sub-blocks: a sixteen-byte schedule per slot, a one-byte type per slot, and a one-byte dialogue index per slot. Empty slots (zero type byte) are skipped at runtime. The schedule encoding and the per-tick walker are described in the NPC schedules spec.

Dialogue lives in the per-class `.TLK` file, indexed by the per-NPC dialogue index. The dialogue engine, described in its own spec, is invoked when the player initiates a conversation (Section 9).

Town mode's contract with the schedule system is one call per consumed turn: each turn-taking action calls the per-tick walker once, with the current hour byte. The walker iterates all thirty-one NPC slots and advances each NPC's state machine. Town mode reads the walker's "any NPC moved" scratch flag to decide whether the screen needs a repaint.

## 5. Entry: map load, NPC load, player attach

Entering a town is a single setup pass that runs once per entry, before the per-turn loop starts spinning. Six things happen, in order:

1. **State reset.** Active-object slots one through thirty-one are freed (type byte cleared); slot zero is left for the player. The "town entered" flag and visibility-dirty flag are set; transient frame-scoped flags are cleared.

2. **Tile-grid load.** The per-location map is loaded into the tile buffer (Section 3). Exactly 1,024 bytes — one floor of 32×32 — are read.

3. **Marker harvest.** The load pass walks the freshly-read tile grid cell-by-cell, finds NPC start markers and asterisk spawn markers, records their coordinates into per-NPC-slot arrays and into the primary/secondary spawn slots, and overwrites the marker bytes with their underlying tile.

4. **Dawn/dusk substitution.** When the current hour is in the *daytime* band (5 AM through 7 PM inclusive — the same band the lighting model uses for full daylight), a pass runs over the tile buffer applying a fixed per-tile substitution that swaps "night-form" tiles to "day-form" tiles. The maps ship in night form; the daytime pass procedurally produces the day form. At night the substitution is skipped. Section 6 describes the substitution in detail.

5. **NPC roster load.** For each occupied NPC slot in the location's `.NPC` block, the schedule and type are loaded into the resident schedule and type tables, the dialogue index is unpacked into the per-NPC runtime block, and the NPC's runtime state is initialised by sampling the schedule for the current hour. NPCs whose initial waypoint floor matches the current floor are linked into the active-object table; off-floor NPCs exist only in the schedule tables.

6. **Player attach.** The player is added to the active-object table at slot zero (the avatar) and given a phantom NPC entry — a high-indexed NPC slot whose schedule is three identical waypoints fixed at the location's per-scene entry coordinate. Section 8 describes the dual representation. The player's spawn cell is `(15, entry_y, 0)` where `entry_y` is read from a per-scene entry-Y table; X is hard-coded to fifteen and Z is the ground floor.

After these six steps return, the entry pass calls a final screen redraw and hands off to the per-turn loop. The player is in town mode until the loop's per-turn epilogue notices that the scene byte has been cleared (Section 15).

A *re-entry* — a player returning to a town that the engine briefly suspended for combat or a sub-mode — runs the same pass with one parameter changed: the active-object table is *not* zero-cleared, and the player-attach step short-circuits if it finds an existing player slot in place. Re-entries are therefore idempotent.

## 6. The dawn/dusk substitution

Maps ship in their night form: lamps lit, torches blazing, windows glowing. At runtime, when the current hour is in the daytime band, a load-time pass walks every cell of the freshly-loaded tile buffer and applies a fixed substitution to lit-tile bytes — turning them into their unlit-tile equivalents (unlit windows, dark torches, dim lamps). The substitution is a pure XOR of the tile byte against a small constant; the lit and unlit tile-encodings differ in exactly the bits the constant covers, so a single XOR walks one to the other.

The pass runs only on entry and on re-entry. Hour transitions across the band boundary *inside* a town are handled by the per-turn cleanup's daylight recompute on the visibility side, not by re-running the tile substitution. The visible effect is:

- A player who enters at 6 AM sees the day form throughout the visit; if they stay until midnight, the lighting darkens but the tiles themselves do not flip back to lit.
- A player who enters at 4 AM sees the night form; if they stay until 6 AM, the visibility brightens but the tiles remain in night form.
- A player who leaves and re-enters across the band boundary sees the substitution applied or not according to the current hour at re-entry.

The asymmetry between map and visibility avoids the mid-stay flicker that would result from re-running the substitution every hour. A modern engine that prefers continuous behaviour can re-run the substitution at the band boundary; the visible artefact is a one-frame change in lit-tile bytes without affecting any other state.

## 7. The per-turn loop

After entry, control sits in a tight loop that reads one command per iteration and runs it to completion:

1. **Read a command.** The input pipeline blocks until a keystroke arrives, applies its translation rules (key-to-command, numpad-to-direction, queue handling), and returns a single byte.
2. **Pre-dispatch checks.** A short prologue handles meta-states (combat in progress, turn already in flight) and the cursed-by-spell timer. If the scene byte has been cleared during the previous turn — meaning the player just walked across a boundary tile — the loop breaks out (Section 15).
3. **Dispatch.** Movement commands walk through a small jump table indexed by direction code; letter commands flow into the shared per-letter dispatcher described in the commands spec. Many handlers live in the town-mode overlay (Attack, Klimb); others are shared across modes (Cast, Get, Look, Talk, Use) and resolve to the appropriate cross-mode handler after a scene-byte check.
4. **Per-turn epilogue.** When the dispatcher returns and the action consumed a turn, the loop advances the time clock by one minute via the time spec's per-turn cleanup, copies the party's current map coordinates into slot zero, ticks down the curse/buff counter, and calls the NPC schedule processor with the current hour byte.
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

**Look.** L-Look prompts for a direction and reads the tile at the facing cell. The tile ID is mapped through a lookup table (described in the look spec) to a short prose description loaded from the location-look data file. Look does not consume a turn.

**Read sign.** Tile-class encoding for sign tiles triggers a prompt that loads the sign's text from a per-location sign data file, indexed by the sign's coordinates.

**Open / Jimmy.** O-Open applied to a door tile prompts for direction and triggers the door-open interaction: unlocked doors open (tile changes to "open door"); locked doors prompt for a key. J-Jimmy is the lockpick variant — it consumes a lockpick and either unlocks or breaks the lock. Both consume a turn.

**Push.** P-Push applied to a movable tile (chair, barrel, pushable cart) computes the destination cell on the far side of the pushed tile, and if the destination is walkable, swaps the two tile IDs in the live tile buffer. The player can then step into the freshly-vacated cell.

**Get.** G-Get applied to an interactable tile (chest, body, dropped item) runs the per-tile-class get-handler. Chests prompt for a key on locked variants; bodies are searched for items; dropped items are picked up directly. The handler is shared across modes.

**Use.** U-Use picks an item from inventory and applies its per-item action. Many items have town-mode-specific effects: a key opens the closest locked door, a magic gem reveals the local map, a torch lights nearby cells. The handler is shared across modes.

All these interactions except Look and inspect-style actions consume a turn and run the per-turn epilogue.

## 11. Multi-floor locations

Several locations span more than one floor. A castle has a throne room above and a great hall below; a dwelling may have a basement; a keep has watchtowers above the main floor. Floor changes are mediated by stairway tiles — ladders, staircases, and occasionally trapdoors.

The current floor is tracked in a single resident byte. When the player walks onto a stairway tile and triggers the climb (via K-Klimb, or automatically on certain stair tiles), the floor byte is updated, the tile buffer is reloaded with the new floor's data (running the marker-harvest and dawn/dusk passes again), the active-object table is partially reset (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and the player's slot is updated with the new Z. The schedule processor handles its own side through its Z-mismatch state machine described in the NPC schedules spec.

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

The player leaves a town by walking onto a boundary tile — typically the same gate or threshold they entered through. The boundary is encoded in the tile-class table: a small set of tile values are flagged as exit tiles, and stepping onto one runs the exit handler, which clears the scene byte, computes the player's overworld coordinate from the per-scene entry-coordinate table, and signals the loop to break.

The town turn loop's per-turn epilogue checks the scene byte each iteration. When the byte clears, the loop returns to the main game loop, which reloads the overworld map, restores the overworld active-object table from the on-disk overlay, and resumes overworld mode at the location's overworld cell.

Exit is symmetric with entry: every per-location piece of state allocated during entry is cleared or freed; the next entry runs the full setup pass against the next location's data. There is no cross-town retention.

Soft exits — combat returning to the town, sub-modes re-entering the same town — do not clear the scene byte and short-circuit the entry pass on return. NPC slot state is preserved across the round-trip, so a guard who was at slot fifteen before combat is still at slot fifteen after.

## 16. Hooks into other systems

**Visibility.** Town mode shares the visibility producer with overworld and dungeon modes. The producer runs against the location's tile buffer and the active-object table on each render. Town mode sets the visibility-dirty flag on entry, on floor change, and on schedule-walker reports of "any NPC moved", forcing a recompute.

**Command dispatch.** The shared per-letter dispatcher receives every keystroke not handled by the town-mode movement table. It routes mode-aware commands (A-Attack, K-Klimb, T-Talk) to town-specific handlers and shared commands (G-Get, P-Push, V-View) to cross-mode handlers.

**NPC schedules.** Town mode invokes the schedule processor exactly once per consumed turn, and once per in-world hour during rest.

**Conversation.** The Talk command hands the dialogue engine the NPC's dialogue index; the engine runs a self-contained per-NPC loop until the player exits.

**Time.** Each consumed turn calls the time spec's per-turn cleanup with a one-minute increment. The cleanup advances the clock, refreshes daylight, and triggers any once-per-hour side effects.

**Active objects.** Town mode owns the active-object table during a town visit. Entry clears it (preserving slot zero), the schedule walker fills it from the NPC roster, the per-turn loop refreshes slot zero from world-state on each iteration, and the combat framer transiently swaps it during attack handling.

**Save / load.** A save inside town freezes the scene byte, the floor byte, the player position, the active-object table, and the world-state clock. On load, the engine notices the non-zero scene byte, re-runs the entry pass, and snaps the player and NPCs to saved-or-re-derived positions. The runtime NPC block is not persisted as a chunk; it is re-derived from the schedule and the saved hour, producing NPCs at their currently-scheduled location regardless of mid-route progress. The dawn/dusk pass runs at load time using the saved hour.

## 17. Open questions and variations

- **Exact dawn/dusk substitution sentinel.** The substitution swaps lit-tile bytes to unlit-tile bytes via a fixed XOR; the precise tile values matched and the constant used are observable from the load-pass code, but the encoding of which tile classes participate is not fully enumerated here. An engine that wants a different lighting model can replace the pass with a more general lighting layer.

- **Audience-prompt logic at Lord British's Castle.** The audience-pending table is consulted on every entry, but the data flow that populates it (which quest events set which entries) is plot-dependent and not enumerated here. A modern engine should treat the table as data and drive it from the quest-flag store.

- **Hidden-room mechanics.** A few locations have rooms accessible only via Push or via a quest-flag-gated tile change. There is no engine-level "hidden rooms" feature; the gating lives in the per-location tile data.

- **The Y == 4 short-circuit on town entry.** The player-attach helper has a special-case path that skips the perm-loc search when the player's Y coordinate equals four. Plausibly a "returning from sub-mode" sentinel, but the exact write site has not been confirmed.

- **Per-scene entry-coordinate table.** The thirty-two-byte entry-Y table gives one Y per location; X is hard-coded to fifteen. An engine that wants bidirectional per-scene entry coordinates can extend the table to two bytes per scene.

- **The two paired NPC start markers.** Two adjacent tile values both serve as NPC start markers, with the low bit ignored. The intent of the low-bit distinction — facing hint, static-versus-walker — is not pinned down. The marker harvest treats them identically.

- **Boundary-tile mapping for exit.** The set of tile values flagged as exits is small and per-location data-driven. A modern engine should treat the exit set as data.

- **Soft re-entry preservation.** Combat-and-back preserves the active-object table; dungeon-and-back may not. The exact set of preserving sub-modes should be matched empirically against original-game behaviour.

## 18. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The town-mode entry handler that loads the location's map, runs the marker harvest, applies the dawn/dusk substitution, and attaches the player — `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The per-turn loop that reads commands, dispatches, runs the schedule walker, and advances time — `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The per-location map loader, the marker harvest, and the dawn/dusk substitution — `u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md`.
- The player-as-NPC attachment helper and the phantom-NPC schedule synthesis — `u5-decomp/functions/TOWN_OVL/0x02AE_town_attach_player_slot.md`.
- The world-mutation primitive that links logical NPC state to active-object slots — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The NPC roster loader for one location — `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md`.
- The per-tick NPC walker invoked once per turn from the town loop — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The shared per-letter command dispatcher routed by mode — `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The per-turn cleanup that advances the clock and recomputes daylight — `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The location tile-grid file format and the two-floor-per-location layout — `u5-decomp/formats/maps.md`.
- The NPC roster and dialogue file formats — `u5-decomp/formats/npc-tlk-pth.md`.
- The first verification slice for Lord British's castle scene binding and
  town-mode load smoke checks — `u5-engine/reports/lb-throne-room-slice.txt`.
- The save image's scene-byte encoding and the per-location coordinate state — `u5-decomp/formats/saves.md`.
