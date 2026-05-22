# Town mode

## 1. Overview

When the player steps onto an enclosed cell of the overworld — a town gate, a castle drawbridge, the entrance to a keep, the threshold of a dwelling — the engine pauses the overworld, swaps the active map for a thirty-two-by-thirty-two interior grid, loads the location's roster of named NPCs along with their daily routines, and hands control to the town-mode turn loop. The player walks among schedule-driven NPCs, talks to them, opens doors, climbs ladders to upper floors, takes things from chests, encounters castle services and story-critical set pieces, and eventually walks back across the boundary to leave. Town mode is where most of the game's storytelling happens.

Town mode shares almost everything with overworld mode — the per-letter command dispatcher, the input pipeline, the active-object table for sprites, the renderer, the time clock — and adds three things on top: a different map, a population (the NPC roster and scheduler), and a per-turn invocation of the schedule processor that keeps NPCs walking on their daily routines while the player takes their own turn. The baker is at the bakery in the morning, the guards stand at the city gates during the day and head to the barracks at night, the farmer goes home for dinner.

Shared terrain passability, dynamic occupancy, and movement commit rules are
specified in `systems/movement.md`. This town-mode spec owns the location floor
buffer, NPC scheduler integration, dawn/dusk rewrites, boundary exits, and
town-specific command hooks around that shared movement layer.

One set of code, one set of file formats, one tile encoding, and one schedule format serve four superficially different location classes — towns, dwellings, castles, and keeps. The differences are entirely encoded in data: a castle can have throne rooms, guards, healers, or other special residents; a keep is barracked and patrolled; a dwelling is a single small house with a few NPCs; a town is everything between. From the engine's perspective they are identical.

This spec describes how town mode is entered, how the location's map and NPCs are loaded, how the per-turn loop dispatches commands and runs the scheduler, what role the player's second representation in the NPC table plays, how multi-floor locations are navigated, what the special interactions do at the town-mode level, and how the player exits.

## 2. The four location classes and the scene byte

The world has thirty-two named non-overworld locations divided evenly into four classes — towns, dwellings, castles, and keeps — eight per class. Every named location has a unique *scene byte* in the range one through thirty-two. The class is selected by the high bits of the scene byte and the index within the class by the low bits, so that:

| Scene byte range | Class    |
|------------------|----------|
| 1–8              | Town     |
| 9–16             | Dwelling |
| 17–24            | Castle   |
| 25–32            | Keep     |

The engine tracks the active scene in a single resident byte. Zero means "overworld"; values one through thirty-two put the engine in town mode for one named location; values outside that range do not select a town-family location. Walking onto an enclosed cell sets the scene byte; leaving via a boundary tile clears it.

Per-location data lives in four parallel families of files — one tile-grid file per class, one NPC roster file per class, one dialogue file per class. The roster and dialogue files use the per-class location index directly; the tile-grid file uses the same physical ordering but active floor pages are selected through the resident base-page table described below. The engine resolves the file family from `(scene - 1) >> 3` against a four-entry pointer table.

## 3. Per-location map data

A location's map is a thirty-two-by-thirty-two grid of one-byte tile indices, totalling 1,024 bytes per floor. Each per-class file contains sixteen such floor pages, physically arranged as eight two-page location pairs. Runtime floor selection is driven by a resident per-scene base-page table, not just by the physical pair: logical floor zero is the scene's base page, floor one is the next page, and floor `0xFF` is the previous page.

The active floor is loaded into a single 32×32 byte buffer in the resident data segment. Cell `(row, col)` is at buffer offset `row × 32 + col`; row indices increase southward, column indices increase eastward. The renderer reads this buffer for the static terrain layer; the active-object table (described in the active-objects spec) layers sprites on top.

The on-disk tile bytes are *terrain plus markers*. Most cells contain a tile ID — wall, floor, grass, water, door, chair, ladder — that the renderer paints directly. A handful of special tile values are *markers* that the location-load pipeline and NPC scheduler harvest, rewrite, or consume:

- **NPC start markers** (`0x48` or `0x49`) record where each rostered NPC begins. The location-load pass walks the grid, finds these markers, and records each marker's coordinates and exact marker byte.
- **Spawn markers** (the literal asterisk character byte) record one or two map-entry coordinates. The first asterisk encountered is the *primary* spawn (typically the entrance from the overworld); the second is the *secondary* (typically an alternate exit or a stairway-up landing). Locations with no asterisk inherit a default per-scene spawn coordinate.
- **Dash/period markers** (the dash and period tile values) are processed by a secondary pass that runs after the player has been placed. When the runtime predicate accepts them, they rewrite to nearby ordinary tile-detail values; they are not currently proven to be per-NPC route hints.
- **NPC floor-link markers** (`0xC8` and `0xC9`) are consumed by the NPC scheduler's tile-ID pathfinder after map load. They must remain distinguishable in the live tile buffer for the schedule processor.

Marker processing is in-memory only: the on-disk `.DAT` floor is unchanged. By the time normal play begins, runtime passes have harvested the markers needed for spawn/NPC state and may have rewritten selected marker cells, while visible actors are represented through the dynamic sprite layer. Some markers, notably the `0xC8`/`0xC9` floor-link pair, remain meaningful to runtime consumers after the initial load pass.

After the player has been attached, a cosmetic variation pass may rewrite selected live floor cells that were authored as dash or period terrain into neighbouring visual variants. This is not an NPC waypoint load. It is a deterministic per-location texture pass: it is seeded from location state, saves and restores the gameplay PRNG around the pass, and exists only to break up large uniform stretches of path/ground in the loaded tile buffer.

The floor byte is interpreted as signed eight-bit for map loading. Values `0..127` are non-negative floors; values `128..255` are negative offsets from the base page. This lets a scene place its ground floor in the middle of nearby authored pages and reach a basement with `0xFF`, while still using the same 32×32 tile encoding for every floor.

## 4. Per-location NPC and dialogue data

Each named location carries a roster of up to thirty-one NPCs (slot zero is a sentinel). The roster lives in the per-class `.NPC` file, one 576-byte block per location, holding three parallel sub-blocks: a sixteen-byte schedule per slot, a one-byte type per slot, and a one-byte dialogue index per slot. Empty slots (zero type byte) are skipped at runtime. The schedule encoding and the per-tick walker are described in the NPC schedules spec.

Town entry applies an additional per-scene activation mask before a rostered NPC
becomes active. The mask is indexed by scene and NPC slot and is consulted only
for the NPC type families that participate in this persistent scene-state
system. The companion write path marks selected killed or removed NPC classes
into the same per-scene mask, so a later re-entry can suppress or alter that
slot according to scene state without editing the on-disk roster. This is not
the same table as the hidden-NPC visual mask used by the schedule system when
allocating an already-active NPC's sprite: the activation/death mask controls
whether a slot enters the scheduler, while the hidden mask only changes the
tile used for the linked sprite.

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

A *preserving re-entry* runs the same pass with the setup argument clear. In
that mode the active-object table tail is not zero-cleared and the
player-attach step can short-circuit if it finds an existing player slot in
place. Preserving re-entry is used when the top-level dispatcher is already in
a town-family scene and is re-running setup without having just returned from
the overworld or the dungeon wrapper.

Fresh entry paths pass the nonzero setup argument. This path clears active
object slots one through thirty-one, resets the town-entry scratch flags, runs
the entry-time service hooks, and then proceeds through the same map load,
player attach, NPC setup, and presentation sequence. The traced fresh-entry
callers are the main loop after an overworld-to-town scene change, the main
loop after a dungeon-wrapper return that leaves a town-family scene active, and
the resident NPC-location warp helper when it changes from one town-family
scene to another. The direct save/load or already-in-town dispatch path reaches
town setup with the preserving argument.

One traced coordinate edge intentionally bypasses the normal phantom-player
attachment path. When the town arrest sequence accepts surrender, it sends the
party to Yew jail at local position `(25, 4, 0)` and advances time until 08:00.
On the following town-entry setup, the player-attach helper treats local
`Y == 4` as a special case: it skips the permanent-location queue lookup and
returns before allocating a fresh phantom NPC if no active player queue entry is
already selected. Do not generalize this into an ordinary re-entry rule; it is
the jail-wakeup coordinate path currently traced from the arrest handler.

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
3. **Dispatch.** Movement commands use a small direction dispatch table; letter commands flow into the shared per-letter dispatcher described in the commands spec. Many handlers live in the town-mode overlay (Attack, Klimb); others are shared across modes (Cast, Get, Look, Talk, Use) and resolve to the appropriate cross-mode handler after a scene-byte check.
4. **Per-turn epilogue.** When the dispatcher returns and the action consumed a turn, the loop snapshots the current hour, advances the time clock by one minute via the time spec's per-turn cleanup, runs the dawn/dusk gate pass if the new hour is `5` or `20`, copies the party's current map coordinates into slot zero, ticks down the curse/buff counter, and calls the NPC schedule processor with the current hour byte.
5. **Render.** If the schedule processor reported any NPC moved, or the visibility-dirty flag is set, a full render runs. Otherwise the screen is left as-is and the loop reads the next command.

The dispatcher's return code decides when to skip parts of the epilogue: actions that take no turn (a cancelled command, a "What?" fallthrough, the buffer-toggle key) skip both the time advance and the schedule tick. Actions that consume more than one turn advance the clock once per inner action.

Cardinal movement in town is a mode-owned wrapper around the shared movement layer. It computes a bounded destination in the current 32-by-32 floor, prints the direction phrase, optionally prefixes it with the active vehicle verb ("Ride", "Row", or "Fly"), samples the target terrain, and asks the shared passability classifier with the current transport marker. A rejected destination prints the standard blocked feedback and leaves the avatar in place.

Successful movement commits the avatar coordinate, marks the view dirty, and then runs immediate tile effects. The traced town-family exit threshold is tile id `0x59`; stepping onto it prompts before leaving. Accepting clears the scene byte and maps the interior exit back to the location's overworld coordinate. Town stair tiles are the `0xC4..0xC7` family. Their low two bits are compared with the movement wrapper's normalized facing code: matching the movement code moves up one floor, matching that code's opposite-facing value moves down one floor, and crossing the stair from either side is just a normal walk. Floor changes reload the active floor and rerun the load-time passes for that floor.

The schedule tick is unconditional on consumed turns — every action that costs a turn advances NPCs by one tick — so an NPC walks at most one cell per player action.

The Hole-up command (Section 12) is the one path that bypasses this cadence. It
runs the schedule walker directly inside the rest handler while the requested
hours are simulated. In the traced town-hours path, each requested rest hour can
run up to sixteen walker/world-tick passes, so NPCs can move substantially more
than once per requested hour if the rest is not interrupted.

## 8. The player as NPC

Town mode keeps two parallel views of the player. The first is slot zero of the active-object table — the avatar sprite — owned by every world-mode renderer and updated each turn from the world-state globals. The second is an entry in the high end of the NPC slot table — a *phantom NPC* — whose schedule is three identical waypoints pinned to the player's spawn coordinate, whose AI byte is set to a stationary mode, and whose type byte is a player-sentinel distinct from any real NPC type.

The phantom exists because some town-mode helpers walk the NPC table when they
need the player to have an NPC-table identity. Without the phantom, those
helpers would be blind to the player. NPC movement collision and pathfinding
are not purely NPC-table scans, though: the pathfinding workspace marks nearby
active-object cells as dynamic obstacles and separately marks the player's
current cell, so NPCs refuse the live player position even after the phantom
entry has remained at its spawn coordinate.

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

Town-mode Open has a small amount of local policy before it reaches the shared door/chest machinery: it refuses while the player is mounted, samples the adjacent tile after the direction prompt, accepts the ordinary closed-door and gate families as openable, and recognizes the town chest family as a separate chest path. If opening or stepping through a door exposes a stair transition, the same stair/floor-change handling described in Section 7 runs.

**Attack.** A-Attack prompts for a direction and targets the adjacent cell. It refuses attacks from blocked posture/terrain states, resolves a small smashable-prop case, then looks for a live NPC linked to the target sprite. A valid hostile or attackable NPC target plays the attack presentation and either removes the NPC through the death flow or triggers town-wide alarm effects. Invalid targets produce the ordinary failure text. Attacking in town is therefore an in-town scene-state mutator: killing selected NPC classes updates the per-scene activation mask used on re-entry.

**Push.** P-Push is the shared movable-tile command specified in
`commands.md`. In town-family scenes it samples the adjacent cell relative to
the avatar, accepts either a dynamic object or one of the known pushable static
tile families, and then either pushes the object forward into a matching
floor/occupancy stamp cell or pulls it backward into the avatar's old cell.
Directional objects such as the four-facing furniture families are reoriented
as they move. The command mutates the live tile buffer and advances the avatar
one cell only after a push or pull succeeds.

**Get.** G-Get applied to an interactable tile (chest, body, dropped item) runs the per-tile-class get-handler. Chests prompt for a key on locked variants; bodies are searched for items; dropped items are picked up directly. The handler is shared across modes.

**Use.** U-Use routes to the CAST-owned item-use handler shared by
non-combat modes. It picks from the party's usable item stock and dispatches by
item id; detailed potion, scroll, Moonstone, carpet, regalia, and quest-item
effects belong to `catalogs/item-list.md` and `systems/inventory.md` as they
are promoted. Do not fold J-Jimmy key use, V-View gem use, or I-Ignite torch
use into this command; those are separate letter commands.

All these interactions except Look and inspect-style actions consume a turn and run the per-turn epilogue.

Several underfoot effects also belong to town mode. Sleeping party members can recover from sleep as turns pass. Chair tiles normally act like a downward floor transition, but Stonegate's chair scene is a special imprisonment sequence that clears the town presentation, marks the party into the long-term consequence state, and returns after a fade. Rune/lever-style tiles print their local effect text and redraw.

The top-down poison-gas terrain case is keyed by live town tile id `0x04` while the party's current transport marker is the on-foot marker `0x1C`. This is a tile-id rule, not a coordinate sidecar: any loaded town-family cell that still has live tile `0x04` and is processed while the party is on foot uses this effect. The handler scans active party slots in order. Dead (`D`) and already Poisoned (`P`) slots are skipped. Every other status, including Sleeping, is eligible. For each eligible slot, roll the shared inclusive random range `0..29`; if the result is greater than that member's Dexterity byte, set the member's status to Poisoned and emit the standard status feedback. If the roll is less than or equal to Dexterity, the member is unchanged.

## 11. Multi-floor locations

Several locations span more than one floor. A castle has a throne room above and a great hall below; a dwelling may have a basement; a keep has watchtowers above the main floor. Floor changes are mediated by stairway tiles — ladders, staircases, and occasionally trapdoors.

The current floor is tracked in a single resident byte. When the player walks onto a facing-sensitive stairway tile and triggers the climb, or invokes K-Klimb on a ladder/trapdoor-style floor transition, the floor byte is updated, the tile buffer is reloaded with the new floor's data (running the marker-harvest and dawn/dusk gate-normalization passes again), the active-object table is partially reset (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and the player's slot is updated with the new Z. The schedule processor handles its own side through its Z-mismatch state machine described in the NPC schedules spec.

Visibility is per-floor: the visibility producer treats the active map as the only walkable surface and runs its centre-out carve against tiles in the current floor's tile buffer. NPCs on other floors are invisible and silent.

A handful of locations have *secret* floors or rooms, but town mode does not
own a separate hidden-room mechanism. Search-revealed wall passages are the
Search/door mutation contract from `systems/commands.md` and
`systems/doors-and-z-transitions.md`; movable furniture and trapdoor access use
the shared P-Push and floor-transition contracts. The authored inventory of
which location cells are secret is location/tile cataloguing work, not a
different town loop.

## 12. The Hole-up command

H-Hole-up is gated by terrain: in town mode it runs only when the player is standing on a bed tile in an inn. On a bed it prompts for a duration in hours; off it, "Not here!" prints and no turn is consumed. The shared command contract is in `systems/rest-and-camp.md`.

When the rest is accepted, control hands off to the rest handler in a shared
overlay. The handler prompts for hours, walks the party status records, and
advances simulated rest through a caller-owned loop. For each requested hour the
town-hours path can run up to sixteen schedule/world-tick passes, checking after
each pass for a rest-interruption event. If an interruption fires, rest stops
without rolling back elapsed side effects. If the requested duration completes,
sleeping members are restored to good status before control returns to the town
loop. The town-bed path does not contain its own HP/MP recovery block; recovery
claims belong in `systems/rest-and-camp.md` and time-driven effects such as the
hourly Ring of Regeneration tick belong in `systems/time.md`.

Hole-up is the only path that runs the schedule processor outside the per-turn
epilogue. The cadence differs from ordinary turns, but the scheduler contract is
the same: one call per tick advances every NPC by at most one cell.

## 13. Lord British's castle

One castle-family scene is Lord British's Castle. The first verification slice
binds the strongest roster/dialogue evidence to `CASTLE:0`; do not rely on
older notes that describe this as the fifth castle slot.

The traced Lord British dialogue evidence is narrower than older notes implied:

- Lord British is not an ordinary keyword-driven `CASTLE.TLK` speaker.
- The zero-dialogue castle residents and throne sprites are not a normal
  hard-coded Lord British conversation path.
- Castle healer service is dispatched through the ordinary shop/service path,
  not through Lord British's personal dialogue.
- Lord British's level-up service belongs to the overworld camp/rest event
  where a strangely familiar old man may appear.

The terminal endgame dialogue is owned by `systems/endgame.md`, not by the
ordinary town Talk loop. Town mode should not claim an endgame
audience-prompt or quest-item-presentation contract.

Lord British's castle also has a basement-only secret-door chord. While the
scene and floor gate are active, numpad digits advance a fixed combination
state with partial-match recovery after mistakes; correct progress gives audio
feedback, and completing the sequence flips the live secret-door tile. Outside
that gated state, the same entry point falls through to ordinary command
dispatch. The exact shipped digit sequence remains a data-table verification
item.

The castle's tile grid, NPC roster, and dialogue file are otherwise ordinary. A
handful of other named locations have one-scene quirks (a scripted NPC arrival
in one dwelling, a special-event stairway in one keep), encoded entirely in
their data or mode-specific handlers.

Stonegate has a separate entry-time presentation surface. On entry, the town
setup path can play a Sceptre-gated prelude row when the party carries the
Sceptre of Lord British. After the location is drawn, the same presentation
helper walks the three Shadowlord runtime slots and, for every Shadowlord that
is still alive, prints the corresponding "air of" virtue-opposition line and
plays the associated tone. This is not Lord British's Castle, not an ordinary
throne-room audience, not a generic town audience-prompt system, and not an
independent trigger queue. The three-slot producer is the Shadowlord hideout
state described in `catalogs/quest-graph.md`; values with the vanquished marker
are skipped, while any living value selects that Shadowlord's atmospheric row.

## 14. Town alarms and hostile NPCs

Some named locations contain hostile NPCs. A guard in Blackthorn's keep, for example, is a normal NPC for most of the game but turns hostile under specific quest conditions; the type byte encodes "hostile when flag X is set". When an NPC's hostile predicate is true, the walker stamps the NPC's current sprite with a hostile tile.

A hostile NPC adjacent to the player blocks movement onto their cell ("Bump!"). A-Attack directed at a town NPC stays inside town mode: it plays the attack presentation, can smash a small prop, can mark or clear the targeted NPC through the town death flow, and can trigger the town-wide alarm sweep. It does not call the combat framer or swap to a `.CBT` arena in the traced town overlay.

NPCs whose hostile predicate is always true remain schedule-driven town actors. When the scheduler reports an attack/catch event, town post-action cleanup handles the event through alarm, arrest, pacify, death, or slot-clear paths rather than through arena combat.

Town alarms are one-shot sweeps over the NPC roster. Depending on the triggering path, eligible NPCs are forced into a fortified/alert schedule state or into a pacified/fleeing schedule state; some special classes, including the player proxy and corpse/guard-like classes, are fortified instead of fleeing. Other eligible townsfolk use a random half-chance before switching into the fleeing state. The schedule walker consumes these state changes on later ticks.

After each schedule tick, town mode interprets the walker's event bytes. A non-attack/flee event from an alarmed NPC can print the associated message and pacify that NPC. A guard-catch event can run the arrest sequence: surrendering moves the party to the Yew jail scene, marks the view dirty, advances time in twenty-minute cleanup calls until the hour reaches 08:00, clears the jail-scene latch, and returns as a consumed turn. Refusing triggers the alarm sweep and consumes the turn. If that same arrest handler is reached while the party is already in the Blackthorn captive scene, it enters the Blackthorn audience/capture cinematic instead of the ordinary Yew-arrest prompt. Monster-class or attack outcomes can route through the NPC death flow, which marks the scene mask, clears the live slot, reloads the floor, and reattaches the player.

## 15. Exit

The player leaves a town by walking onto the traced town-family exit threshold,
tile id `0x59`. The handler prompts before leaving. Accepting the prompt clears
the scene byte, computes the player's overworld coordinate from the fixed
world-location coordinate tables, writes the destination plane (`0` for
ordinary scenes, the underworld value for scene byte `0x19`), clears the
town-local curse/state latch, and signals the loop to break. Refusing the
prompt leaves town mode active and does not move the party out to the
overworld.

The town turn loop's per-turn epilogue checks the scene byte each iteration. When the byte clears, the loop returns to the main game loop, which reloads the overworld map, restores the overworld active-object table from the on-disk overlay, and resumes overworld mode at the location's overworld cell.

Exit is symmetric with entry: every per-location piece of state allocated during entry is cleared or freed; the next entry runs the full setup pass against the next location's data. There is no cross-town retention.

Soft exits and sub-modes re-entering the same town do not clear the scene byte
and short-circuit the entry pass on return. NPC slot state is preserved across
the round-trip, so a guard who was at slot fifteen before the sub-mode remains
at slot fifteen after.

## 16. Hooks into other systems

**Visibility.** Town mode shares the visibility producer with overworld and dungeon modes. The producer runs against the location's tile buffer and the active-object table on each render. Town mode sets the visibility-dirty flag on entry, on floor change, and on schedule-walker reports of "any NPC moved", forcing a recompute.

**Command dispatch.** The shared per-letter dispatcher receives every keystroke not handled by the town-mode movement table. It routes mode-aware commands (A-Attack, K-Klimb, T-Talk) to town-specific handlers and shared commands (G-Get, P-Push, V-View) to cross-mode handlers.

**NPC schedules.** Town mode invokes the schedule processor exactly once per
consumed turn. The H-Hole-Up hours path invokes the same scheduler from inside
its rest simulation loop, up to sixteen times per requested rest hour.

**Conversation.** The Talk command hands the dialogue engine the NPC's dialogue index; the engine runs a self-contained per-NPC loop until the player exits.

**Time.** Each consumed turn calls the time spec's per-turn cleanup with a one-minute increment. The cleanup advances the clock, refreshes daylight, and triggers any once-per-hour side effects. When that one-minute cleanup changes the hour to `5` or `20`, town mode also runs the dawn/dusk gate substitution against the loaded tile buffer.

**Rest and camp.** `rest-and-camp.md` owns the H-Hole-up hours prompt,
simulated-time loop, status cleanup, camp recovery effects, and interruption boundary. Town mode
owns only the bed/tile gate and the schedule-walker integration.

**Active objects.** Town mode owns the active-object table during a town visit. Entry clears it (preserving slot zero), the schedule walker fills it from the NPC roster, the per-turn loop refreshes slot zero from world-state on each iteration, and town interaction handlers mutate NPC-linked slots through their own clear, death, alarm, and placement helpers.

The town overlay also owns a small free-roaming object walker for animal-like
sprites. These objects move independently of the NPC schedule: each tick gives
eligible animal sprites a random chance to step one cardinal cell, constrained
by a narrow terrain predicate and by empty-destination checks. A committed step
updates the sprite coordinate/facing and marks visibility dirty.

**Movement.** The shared movement spec owns direction-code routing,
the resident terrain-query layer, dynamic occupancy, and commit rules. This
town-mode spec owns the current floor buffer, NPC collision/scheduling side,
boundary-tile exit, and floor-transition hooks around successful movement.

**Save / load.** A save inside town freezes the scene byte, the floor byte, the player position, the active-object table, and the world-state clock. On load, the engine notices the non-zero scene byte, re-runs the entry pass, and snaps the player and NPCs to saved-or-re-derived positions. The runtime NPC block is not persisted as a chunk; it is re-derived from the schedule and the saved hour, producing NPCs at their currently-scheduled location regardless of mid-route progress. The dawn/dusk gate pass runs at load time using the saved hour.

## 17. Town Boundaries And Remaining Data Work

Town/interior mode is complete at behavioral-contract depth: entry, map load,
marker harvest, dawn/dusk substitution, cosmetic variation, movement and
floor/exit transitions, command hooks, alarm/arrest handling, NPC schedule
integration, active-object ownership, free-roaming object movement, entry-mode
preservation behavior, and save/load entry reconstruction are specified.
Remaining work is data cataloguing and caller-census parity, not a separate
town-loop mechanism.

- **Stonegate presentation parity.** The entry-time producers are now assigned:
  the Sceptre carried-item flag gates the prelude row, and the three
  Shadowlord hideout slots gate the per-living-Shadowlord "air of" rows. Any
  remaining work is exact presentation-asset parity for the prelude row,
  timing, and tone, not producer identity or an audience/queue mechanism.

- **Authored secret-location inventory.** The runtime mechanisms for
  Search-revealed doors, P-Push movable blockers, hidden pickups, and floor
  transitions are covered in their owning command/door/container specs.
  Remaining work is cataloguing authored secret room cells and their
  player-visible contents, if a per-location parity atlas is needed.

- **Soft re-entry empirical parity.** The traced caller census now assigns the
  preserving and fresh setup argument paths. Remaining work is empirical parity
  for rare nested script returns, if a test target needs confirmation of
  whether they can reach town setup without going through one of the traced
  caller families.

## 18. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The town-mode entry handler that loads the location's map, runs the marker harvest, applies the dawn/dusk gate substitution, and attaches the player — `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The top-level dispatcher and resident NPC-location warp helper that supply
  the traced fresh-versus-preserving town setup arguments -
  `u5-decomp/functions/ULTIMA_EXE/0x0000_main_game_loop.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x47F4_npc_warp_to_scene.md`.
- The per-turn loop that reads commands, dispatches, runs the schedule walker, advances time, and toggles gates at the dawn/dusk hour boundaries — `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The per-location map loader, the marker harvest, and the dawn/dusk gate substitution — `u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md` and `u5-decomp/functions/TOWN_OVL/0x0170_town_dawn_dusk_pass.md`.
- The per-location cosmetic terrain variation pass - `u5-decomp/functions/TOWN_OVL/0x0212_town_load_npc_waypoints.md`.
- The player-as-NPC attachment helper and the phantom-NPC schedule synthesis — `u5-decomp/functions/TOWN_OVL/0x02AE_town_attach_player_slot.md`.
- The per-scene NPC activation mask reader/writer and runtime slot free helper - `u5-decomp/functions/TOWN_OVL/0x0000_npc_in_class_filter.md`, `u5-decomp/functions/TOWN_OVL/0x0052_npc_set_class_bit.md`, and `u5-decomp/functions/TOWN_OVL/0x00B0_npc_clear_slot.md`.
- The reverse lookup from sprite slot to live NPC slot - `u5-decomp/functions/TOWN_OVL/0x011E_npc_find_idle.md`.
- The stair/floor movement tail, vehicle movement presentation, movement command handler, and underfoot interaction handler - `u5-decomp/functions/TOWN_OVL/0x052E_town_movement_log.md`, `u5-decomp/functions/TOWN_OVL/0x057C_town_movement_print.md`, `u5-decomp/functions/TOWN_OVL/0x0600_town_movement_handler.md`, and `u5-decomp/functions/TOWN_OVL/0x0F02_town_step_interaction.md`.
- The town Attack and Open handlers - `u5-decomp/functions/TOWN_OVL/0x09E6_town_attack_handler.md` and `u5-decomp/functions/TOWN_OVL/0x0B82_town_open_handler.md`.
- The town alarm, pacify/fortify, death, arrest, and post-scheduler cleanup helpers - `u5-decomp/functions/TOWN_OVL/0x085E_npc_set_state_fortified.md`, `u5-decomp/functions/TOWN_OVL/0x08D4_npc_set_state_pacified.md`, `u5-decomp/functions/TOWN_OVL/0x0958_npc_scatter.md`, `u5-decomp/functions/TOWN_OVL/0x09BC_npc_death_handler.md`, `u5-decomp/functions/TOWN_OVL/0x10DA_npc_print_killed.md`, `u5-decomp/functions/TOWN_OVL/0x10F2_npc_should_pacify.md`, `u5-decomp/functions/TOWN_OVL/0x1156_town_setup_post_npc.md`, `u5-decomp/functions/TOWN_OVL/0x12AE_town_arrest_or_unconscious.md`, and `u5-decomp/functions/TOWN_OVL/0x1352_town_post_action_cleanup.md`.
- The Lord British castle chord handler - `u5-decomp/functions/TOWN_OVL/0x0E34_lb_audience_chord.md`.
- The Stonegate setup helper audio/presentation pattern - `u5-decomp/functions/TOWN_OVL/0x11B8_town_setup_helper.md`.
- The free-roaming animal/object walker and its narrow town terrain predicate - `u5-decomp/functions/TOWN_OVL/0x0C78_town_object_walker.md` and `u5-decomp/functions/TOWN_OVL/0x0C4A_tile_walkable_predicate.md`.
- The town input parser, including command refresh and modal override behavior - `u5-decomp/functions/TOWN_OVL/0x0DC4_town_input_parser.md`.
- The town NPC visibility pass - `u5-decomp/functions/TOWN_OVL/0x1694_town_npc_visibility_pass.md`.
- The world-mutation primitive that links logical NPC state to active-object slots — `u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`.
- The NPC roster loader for one location — `u5-decomp/functions/NPC_OVL/0x0000_npc_main.md`.
- The per-tick NPC walker invoked once per turn from the town loop — `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The NPC pathfinder notes that bind marker IDs `0xC8` and `0xC9` to the scheduler's tile-ID goal path, plus the town step handler's separate `0x8C` chair trigger — `u5-decomp/functions/NPC_OVL/0x01A0_npc_path_probe.md`, `u5-decomp/functions/NPC_OVL/0x01D2_npc_floodfill_workspace_prep.md`, and `u5-decomp/functions/TOWN_OVL/0x0F02_town_step_interaction.md`.
- The shared per-letter command dispatcher routed by mode — `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The per-turn cleanup that advances the clock and recomputes daylight — `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The location tile-grid file format and the two-floor-per-location layout — `u5-decomp/formats/maps.md`.
- The NPC roster and dialogue file formats — `u5-decomp/formats/npc-tlk-pth.md`.
- The clean verification summary for Lord British's castle scene binding and
  town-mode load smoke checks - `u5-spec/NEXT-STEPS.md`.
- The save image's scene-byte encoding and the per-location coordinate state — `u5-decomp/formats/saves.md`.
