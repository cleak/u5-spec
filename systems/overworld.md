# Overworld

## 1. Overview

Ultima V's overworld is the open-air mode the player spends the most time in. Two surfaces share the mode: **Britannia**, the surface world the game opens on, and the **Underworld**, the lightless mirror beneath it. Both are 256-by-256 tile grids driven by the same mode loop, the same camera, the same per-turn cadence. They differ only in which on-disk grid the engine reads tiles from, what default lighting the time system applies, and which surface features distinguish them: town and dungeon entries, runtime moongate presentation, and a confirmed falls trigger on Britannia, plus a uniformly dark and chasm-strewn cavern below.

Within either surface the player commands a small party (or a vehicle carrying that party) and walks one cell per turn. Around the party live the *active objects* -- wandering monsters, vehicles, dropped items, and the player avatar slot itself -- while render-only effects such as traced moongate frames are stamped into the viewport scratch outside that table. Each turn, the engine reads a command, dispatches it, advances time by two minutes, ticks every animated entity, rolls the random-encounter check, refreshes the daylight value, and rebuilds the on-screen viewport. When the command is "Enter" on a fixed town-mode or dungeon location coordinate, the loop sets a scene byte that the resident main-game loop sees on its next iteration, and overworld mode exits back to the dispatcher, which spins up town mode or dungeon mode. Falling through the confirmed surface chasm is different: it swaps the world plane while staying in overworld mode. Gate-like world-transition branches are handled as explicit underfoot special cases rather than as part of the general scene-entry dispatch.

The overworld is a thin shell over the resident systems. Almost everything that has its own spec — input, time, active objects, visibility, save/load — does the same work in this mode that it does anywhere else. The overworld's specific logic is small: which command goes where, when to load a chunk from disk, how to recognise the eight or nine tile types that mean "something special happens here", and a per-turn animator that is the dual of the town-mode NPC scheduler but does *not* consult the in-world hour. This spec describes those overworld-specific pieces and how they hook into the rest of the engine.

Shared terrain passability, dynamic occupancy, and movement commit rules are
specified in `systems/movement.md`. This overworld spec owns the outdoor map
source, chunk-window refresh, vehicle hooks, encounter hooks, and underfoot
special-tile probes that run around that shared movement layer.

## 2. The two surfaces

Britannia and the Underworld are the two values the *world plane* selects between. The plane is a single byte in the save image — the party's *Z* coordinate — and is consumed almost everywhere that decides which on-disk file a tile-read should hit and which lighting model to apply. Z is zero on Britannia and the all-ones byte (signed −1) in the Underworld.

The player crosses between planes through traced plane writers and unresolved
transition candidates:

- **Falling.** The traced falls handler has a confirmed fixed trigger at Britannia coordinate `(54, 138)`. When the party steps onto that chasm cell, the handler prints a falls banner and an underworld-transition line, applies the Dexterity-gated fall-damage check described in Section 8 to each non-dead party member, restores the pre-fall transport marker after the presentation clear, swaps the world plane to the underworld value, and re-initialises the active-object table for the new plane. The coordinate is hard-wired and fixed across all playthroughs.

- **Whirlpool forced-underworld transition.** Outdoor whirlpool active objects
  are another traced surface-to-underworld writer. When the adjacent-engagement
  path accepts the whirlpool branch while the party is not on foot, it prints
  the whirlpool warning, plays the swallow presentation, writes the underworld
  plane, moves the party to the fixed underworld emergence coordinate `(34,
  18)`, and re-enters overworld setup so chunks and active objects refresh for
  the new plane. If the party marker is the on-foot avatar when this branch is
  reached, the whirlpool branch is a no-op.

- **Interior exit plane selection.** Town-family exits clear the scene byte and
  restore overworld coordinates from the per-scene exit table. The traced town
  mover writes the surface plane for ordinary exits and writes the underworld
  plane for scene byte `0x19`. This is an interior-to-overworld
  exit rule, not proof of a general outdoor underworld-ascent tile set.

- **Gate-like world transition.** One traced surface coordinate owns a special narrative gate branch (Section 9). Ordinary natural moongates use the saved Moonstone slot live-terrain refresh and entry helper described separately in Section 9.

- **Unresolved ascent/additional routes.** No clean public contract currently
  publishes a mirror set of underworld-to-surface outdoor ascent coordinates,
  and the current writer census found no additional outdoor plane writer beyond
  the traced chasm, whirlpool, and interior-exit cases. Dungeon exit/reset paths
  clear the dungeon scene through their owning helpers and are not general
  outdoor ascent tiles.

The mode loop itself does not branch on Z. The chunk loader, the visibility producer, the renderer, the daylight calculator, and the random-encounter spawner treat the two planes identically — what differs is the data the helpers consult: a different on-disk grid (Section 3), a forced full-darkness ambient light on the underworld plane, and a different active-object seed file.

## 3. Map structure

Each surface is a flat 256-by-256 grid of tile bytes — one byte per cell, no padding. The grid is held on disk as a sequence of 16-by-16 *chunks*, each chunk a 256-byte block laid out row-major. The world has 256 chunks total (sixteen across by sixteen down), and the mapping from chunk grid position to disk offset goes through a 256-byte *chunk-index table* in the resident data segment.

The chunk-index table encodes one byte per chunk in row-major order. The byte is either a chunk's 0-based index in the on-disk file or the all-ones sentinel meaning *all-water*. On Britannia, large stretches of open ocean are pure water, and the on-disk grid omits those chunks — only the non-water chunks are stored. The index byte for a water chunk is the all-ones sentinel; the chunk loader recognises this, fills the chunk buffer with the water tile, and returns without doing any disk I/O. A non-sentinel index is the zero-based file index, multiplied by 256 to give the seek offset. This compression-by-omission is why Britannia's on-disk grid is about 52 KB rather than 64 KB.

The Underworld is dense — every chunk is stored, including uniformly cavern ones. Its on-disk grid is exactly 64 KB and its chunk-index table is the identity. The same table format is used; only the contents differ.

After a chunk is loaded or synthesized, the loader walks the 16-by-16 live
chunk copy and applies a fixed substitution pass. Tile ids `0x16..0x18`
trigger a write of tile `0xDF` through the live world-tile accessor; tile id
`0x19` triggers a write of tile `0x1A` only when the chunk high-byte classifier
accepts the current chunk descriptor. These substitutions affect the live
chunk/window state, leaving the on-disk chunk untouched, and are separate from
the per-turn tile animator.

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

2. **Pre-loop tile probe.** Read the tile under the party. If it is the special underfoot tile byte `0xFF` and the current state tag is not the `0x0E` exemption, raise a latched underfoot-state flag and force the current ambient light/radius value to zero. On the first frame entering that state, mark the view dirty. When the state clears, run a zero-minute cleanup call so daylight is recomputed without advancing time.

3. **Block on input.** Call into the input system's keystroke fetch. Sub-printable codes are control keys (cursor, special), printable letters are commands like A-attack, E-enter, T-talk, K-klimb, and digits go to the party-speed selector.

4. **Mode-switch exit check.** If the *scene byte* has gone non-zero since last iteration — because a sub-handler dispatched into a town-family scene or a dungeon-class scene — break out and return to the resident main-game loop. Combat is handled through a framer that restores the pre-combat scene before the outer loop sees it.

5. **Dispatch the command.** Three layers: control codes go through a small dispatch table; digits go to the speed selector; everything else goes to the resident command dispatcher, which routes single-letter verbs to per-letter handlers in this overlay (Attack, Enter, ...) or to one of the action overlays (Cast, Talk, Look, Stats, ...). The dispatcher returns 0 for a no-op (or cancelled action) or 1 for an action that consumed a turn.

6. **Per-turn block (only when the action consumed a turn).**
   a. Run the per-turn cleanup (see `time.md`) with a minute increment of two — the standard outdoor turn cost.
   b. Re-read the tile under the (now possibly moved) party.
   c. Camp / wishing-well dispatch if the tile matches.
   d. Pirate-ship ambush if the tile and transport state indicate one.
   e. Fixed narrative gate branch if on its surface-world coordinate.
   f. Per-turn party-status tick through the OUTSUBS status helper.
   g. Active-object animator if the under-tile is animated (Section 6).

7. **Loop.** Back to step 1 unless the exit flag is set.

The "consumed a turn" gate means looking at the sky, opening the inventory, mistyping a command, talking-to-no-one cost zero time. Only a successful action advances the clock.

The pre-loop underfoot latch is also passed into the outdoor movement
dispatcher. Direction keys still run the normal facing and passability checks,
but a set latch prevents the coordinate-update step from committing. This is a
movement gate and lighting override, not a damage/status tick.

The separate OUTSUBS party-status helper walks the active party once per
overworld turn and can poison living members that are not already poisoned.
That status tick is independent of the special-underfoot lighting latch.

## 6. Active objects and the per-turn animator

Like every other gameplay mode, the overworld owns a 32-slot *active-object table* in the resident data segment (see `active-objects.md`). Slot zero holds the player; the other slots hold:

- **Wandering monsters** — pirates, dragons, sea serpents, troll bands, gargoyle parties, gremlins. Spawned by the random-encounter trigger, kept alive between turns, animated each turn, pruned when they drift outside the view window.
- **Vehicles** — ships, skiffs, horses, and magic carpets. The plane's seed
  `.OOL` pre-places standard live vehicle objects; player-dropped vehicles get
  a slot when the player exits them; ridden vehicles disappear from the table
  while carrying the player. Balloon art is catalogued, but the analyzed
  baseline does not promote it as a live overworld transport object.
- **Pre-placed objects** — chests, items dropped by previous play, plot-significant overworld props.
- **Render-only effects.** Natural moongate frames are not active-object slots
  in the traced animator. They are stamped directly into the rendered tile
  buffer from the moongate scratch coordinates described in Section 9.

Before the main loop begins, overworld entry also consumes a one-shot
pending-action state shared with a few out-of-mode interactions. If that state
carries a queued vehicle acquisition, entry allocates a free active-object slot
at the stored pending-action coordinates, chooses ship-family versus
skiff-family placement from the acquisition class, initializes ship-family hull
state where applicable, copies the queued skiff-count payload for a purchased
frigate, and clears the pending state before normal input begins. The shipwright
sale flow is a confirmed writer of this handshake; exact numeric vehicle marker
variants remain with `vehicles.md`.

Each turn that the per-turn block reaches the animator, the animator walks the active-object table from slot 31 down to slot 1. For each non-empty slot whose tile class is *animated* (a small set of class ranges including monsters, certain vehicles, animated effects), it:

1. **Animates the slot.** Advance the slot's animation phase, swap to the next frame's tile id, and run the outdoor hostile-slot pipeline described in `active-objects.md`: adjacent engagement, Sea Serpent/Dragon first-frame near-range effects, aligned water-creature attack, and cleanup movement. Ship-like water-creature and pirate frames have an additional wind-state cadence before their cleanup movement; `weather.md` owns that cadence table, while `active-objects.md` owns the step-selection and validation behavior.
2. **Prunes the slot if off-screen.** If the slot's (X, Y) is more than 32 cells away from the scroll base on either axis, free the slot. This caps the live monster set to whatever currently lives in the player's neighbourhood.

The animator does not consume the in-game hour; nothing in the overworld animator branches on time-of-day. NPC schedules — the structured "this character is at the bakery 8 AM to 5 PM" mechanic — are a *town-mode-only* concept. Overworld monsters wander but they do not have schedules.

A small *pendulum gate* sits on top of the animator. The `T` timing/state tag
returns before animation, while the `Q` timing/state tag lets the animator and
encounter probe run only on alternate turns. A separate transport-marker
pendulum covers the traced horse/carpet marker pairs described in
`vehicles.md`. This is the same mechanism town mode uses to slow NPCs to
half-speed, but in overworld mode it gates active-object and encounter cadence
rather than the clock directly.

## 7. Random encounters

The per-turn block fires a random-encounter check on every turn that reaches the animator. The check is roll-and-threshold:

1. The encounter probe consults the current world tile class, the party's Z
   plane, and the hour, producing a small threshold in a range covered by a
   30-sided RNG.
2. The mode loop draws a uniform integer in `[1, 30]`.
3. If the threshold exceeds the draw, the spawner fires.

The spawner picks a tile class and a placement cell (off-screen or just at the edge of the visible window) and writes a fresh active-object slot. The slot animates on the next pass and may walk into the viewport over following turns. Whether the player engages is up to the player; the encounter system places monsters near the party, it does not directly enter combat.

Combat is entered when a movement command attempts to step onto a hostile monster's tile, when the per-turn block matches a pirate-ship trigger, or when an ambush event fires from a script. See `combat.md`.

The exact threshold formula is specified in `encounters.md`: underworld travel
uses a fixed mid-level threshold; on the surface, roads and similar safe bands
produce no random encounters by day but still receive the night-time boost,
wilderness bands produce higher thresholds, and hours `0..4` add the surface
night-time boost. The same encounter spec owns the spawn-coordinate retry loop,
terrain bucket selection, and weighted monster-class picker.

A handful of *scripted* encounters bypass the random system. Pirate ships, for example, are placed on specific Britannia coordinates by the seed `.OOL` and follow their wandering AI from there.

## 8. Special tiles

A small set of tile classes triggers special handling in the per-turn block, recognised by the post-action tile probe at step 6b. Each class corresponds to a small handler that may print a prompt, dispatch into another mode, or apply a status effect:

- **Town/keep/dwelling/castle entrance.** When the player's last action was Enter (E), the entry helper compares the party's current overworld coordinate against the first thirty-two rows of the DATA.OVL-derived `WorldLocationTable`. Row zero maps to scene byte one, row one maps to scene byte two, and so on through row thirty-one mapping to scene byte thirty-two. The scene-to-name and scene-to-file-family binding is published in `catalogs/gazetteer.md` and `formats/npc.md`.

  On a match, the original path emits the location-entry prompt, performs any needed surface-disk availability check, clears or reseeds the active-object table, writes the scene byte to `matched_row + 1`, and seeds the party's town-mode coordinates on floor zero. The following town entry pass owns the final player attach point; see `systems/town-mode.md` for the `LocationEntryYTable` rule. If no row matches, E-Enter does not change mode.

- **Dungeon entrance.** E-Enter compares the party's current coordinate against rows thirty-two through thirty-nine of the same DATA.OVL-derived `WorldLocationTable`. Row thirty-two maps to `DUNGEON:0` / scene byte thirty-three, row thirty-three maps to `DUNGEON:1` / scene byte thirty-four, and so on through row thirty-nine mapping to `DUNGEON:7` / scene byte forty. The name and data-record order is Deceit, Despise, Destard, Wrong, Covetous, Shame, Hythloth, Doom.

  On a match, the engine emits the dungeon-entry prompt, loads the selected 512-byte `DUNGEON.DAT` record into the active dungeon tile buffer, writes the scene byte to `matched_row + 1`, and seeds dungeon-mode level, X/Y, and facing. Surface-plane entry lands at level `0`, X `1`, Y `1`, facing east. Underworld-plane entry into non-Doom dungeons lands at level `7`, X `7`, Y `7`, facing west. Doom uses the surface-style entry seed even when reached from the underworld. If no dungeon row matches, E-Enter does not change mode.

- **Shrine.** A meditation prompt with its own subsystem handlers; from the overworld's perspective, the trigger is a tile-class match.

- **Moongate.** Section 9.

- **Falls (chasm).** A confirmed fixed Britannia coordinate, `(54, 138)`, triggers the fall-into-underworld transition.
- **Whirlpool.** Outdoor whirlpool active-object engagement can force the
  party to the fixed underworld emergence coordinate `(34, 18)` on the
  underworld plane. This is an active-object engagement effect, not a dungeon
  or town scene-entry route.

- **Water and current-like movement.** The traced overworld loop does not
  publish a general player-facing waterfall/current sweep that repeatedly
  pushes the party or vessel through a coordinate row. Water movement is
  ordinary one-cell movement through the transport-specific terrain predicates
  in `systems/movement.md`, plus the active-object effects listed below.

  | Trigger family | Trigger source | Movement / transition effect | Transport handling | Damage, messages, and persistence |
  |---|---|---|---|---|
  | Ordinary water travel | Player directional movement into a destination cell accepted by the current transport predicate | One committed cardinal step; no sweep, queue, or multi-cell current is installed | Ships accept the deep-water/water predicate; skiffs use the facing-sensitive skiff predicate; foot and horse reject ordinary water through their predicates; carpets use their own carpet predicate; balloon has no promoted live transport path | Normal consumed-turn timing only; no drowning roll or queued forced-movement state |
  | Pre-loop `0xFF` underfoot state | The tile under the party is the special all-ones tile and the exemption state is not active | Suppresses the next movement commit while forcing the cached light/radius to zero | Applies to the mode loop state rather than to a vehicle family | No damage, no status change, and no scene/plane transition; clearing the state recomputes light with a zero-minute cleanup |
  | Surface chasm/falls | Britannia coordinate `(54, 138)` | Prints the falls presentation, switches the world plane to the underworld value, and reloads the destination plane/object state | Vehicle marker is saved across the presentation clear and restored before the plane swap completes; the traced falls handler does not force the durable post-transition transport marker to foot | Each non-dead party member is checked once during the fall presentation: draw one random byte `0..255`; if the member's Dexterity byte is greater than the roll, no damage is applied, otherwise the normal party-damage helper applies `1 HP` damage. There is no persistent partial-fall queue; save/load sees only the resulting coordinates, plane, transport marker, party HP/status, and active-object table |
  | Whirlpool active object | Orthogonally adjacent outdoor active-object slot in the whirlpool family | If the party is not on foot, clears the whirlpool slot, prints the whirlpool warning, plays the swallow presentation, moves the party to `(34, 18)` on the underworld plane, and re-enters overworld setup | On-foot state is a no-op defensive branch. Ship, skiff, carpet, horse, and any other non-foot marker all take the same forced-underworld branch when this active-object engagement path is reached | No drowning damage is applied by the whirlpool branch. The transition is immediate and durable in ordinary save state after it completes; there is no queued or partially resolved forced movement |
  | Water-creature / pirate active-object movement | Outdoor active-object slots in the water-creature/pirate frame family | Active objects move one cardinal cell when their cadence and validation allow it; they do not push the player along a current row | This is actor movement, not player transport. Wind cadence controls ship-like water-creature movement; ordinary player ship/skiff movement remains command-driven | May print the attack line or enter the ordinary engagement/combat path when adjacency/collision rules fire; it does not install a water-current sweep |

- **Other plane-transition routes.** Current writer sweeps identify no
  additional outdoor plane writer beyond the traced falls, whirlpool, and
  interior-exit cases. Treat any future route as a new writer requiring its own
  evidence.

- **Camp / wishing well.** The H (Hole-up) command runs a multi-screen UI for rest, eating, and per-camp event checks. Camp is its own mini-system; from the overworld it is a sub-handler that runs to completion and returns the party to the same cell. The Lord British level-up service is part of this camp event surface, not a throne-room Talk interaction. See `systems/rest-and-camp.md`.

- **Ship-with-pirate.** When the under-tile is the boarded-ship class and the transport state indicates an enemy ship has been engaged, the per-turn block dispatches into ship-combat ambush. This is the overworld's only non-movement combat trigger.

- **Wells, springs, caves.** Smaller tile classes with their own minor handlers — give a hint, restore a small amount of MP, drop a chest.

The order in which the per-turn block tests these classes matters for correctness. The handlers themselves are mostly thin: some set the scene byte and let the mode loop exit, some swap the world plane, and others run a small interactive flow before returning to the same cell.

The precedence relevant to water/current parity is:

1. Natural moongate live-tile entry is checked before ordinary input dispatch.
2. A successful movement/action must consume a turn before the post-action
   special-tile pass runs.
3. The post-action pass handles fixed coordinate/tile effects such as the
   surface chasm/falls, narrative gate, camp/well checks, status helper, and
   active-object epilogue in the order described by the mode loop.
4. Active-object whirlpool transition is not an underfoot terrain effect. It
   runs from the active-object animator's adjacent-engagement path after the
   per-turn block reaches the active-object epilogue.

There is no separate save-backed "current in progress" state. Effects above
finish synchronously inside the consumed turn that reaches them.

No `world_waterfalls.tsv` or equivalent sidecar table is part of the promoted
runtime contract. Tooling may retain such data as a retired compatibility or
diagnostic artifact, but baseline movement must not consume it as a current or
waterfall sweep source.

## 9. Moongates

Moongates are the surface plane's signature feature. At player-facing design level, eight virtue-linked gates appear and disappear according to the in-game calendar and provide fast travel between fixed Britannia locations. The binary-compatible contract below separates the saved-slot live-terrain refresh, the live entry hook, the render-frame animator, and the fixed narrative gate branch.

The moongate animator reads a transient resident scratch block as four
coordinate words plus one phase byte when the active owner has supplied
moongate-style values:

- **Origin (X, Y).** Two coordinates marking the cell where the gate appears. The all-ones sentinel value means "no gate is currently active".
- **Destination (X, Y).** The cell the gate teleports to. The all-ones sentinel means "single-ended" — a gate that exists for visual effect but does not teleport on landing.
- **Animation phase counter.** A byte cycling through a 16-frame open/full/close animation. The all-ones value is the "uninitialised" state; the first valid call paints the open frames, subsequent calls advance the cycle, and on overflow the counter wraps.

This render-frame moongate scratch is separate from the Moonstone slots used by
*Vas Rel Por* / Gate Travel and by the natural live-tile refresh. Gate Travel
selects one of eight persisted Moonstone destinations saved in `SAVED.GAM`.
The traced Moonstone U-Use helper writes only the selected saved destination
slot after validating the current scene and underfoot terrain; it does not
write the animator scratch block or teleport the party. The same small resident
coordinate block is reused by unrelated mode-entry and chunk-loader contexts.
The current writer census finds the outdoor chunk loader using the first two
coordinate words as scroll-position scratch, the town map setup using the four
coordinate words as primary and secondary asterisk-marker positions, and combat
exit resetting only the animation phase byte. Implementations should therefore
treat these fields as mode-local scratch owned by the active subsystem, not as
durable save state or the natural-moongate live-terrain schedule.

The moongate animator runs once per render frame from the overworld redraw orchestrator. It checks two preconditions: ambient light at or above the daytime threshold and an active origin (the all-ones sentinel skips the body). Below the daylight threshold, the animator resets its phase instead of stamping a frame; this is render eligibility, not proof of the placement schedule. When both preconditions pass, the animator marks visibility dirty, stamps the moongate frame into the rendered tile buffer at the origin (and at the destination if not the all-ones sentinel) using a compact frame plate indexed by the current phase, then bumps the counter.

The animator is self-contained — it writes directly to the rendered buffer
rather than placing an active-object slot. This means the moongate appears and
disappears based on the animator's two preconditions and the current scratch
coordinates; the active-object animator and active-object slot allocator do not
own natural moongate frame lifetime.

The ordinary natural-gate live-tile refresh runs during the resident world tick
for non-combat scenes, before the render-frame animator. It treats the eight
saved Moonstone slots as gate anchors. A slot is eligible when its saved scene
and Z/floor match the current scene. On the overworld, the saved X/Y must also
fall inside the active 32-by-32 loaded chunk window; interior and town-family
non-combat scenes use only the scene/Z match.

The refresh has one shared gate-presence counter. During night hours `20..23`
and `0..4`, the counter increases toward sixteen and eligible slots are stamped
with live moon-gate terrain byte `0xDC`. During hours `5..19`, the counter
decreases toward zero; eligible slots remain `0xDC` while the counter is
nonzero, then are restored to terrain byte `5` when it reaches zero. Any actual
tile change marks the viewport dirty and refreshes local light. This covers the
ordinary natural-gate placement and waning schedule at live-terrain level, and
it is driven by saved Moonstone slots rather than by the animator scratch block.

The overworld command loop also has a live-gate entry hook before normal input
dispatch. It reads the party's current live terrain cell and returns
immediately unless that cell is `0xDC`. On `0xDC`, the hook pauses the loop,
plays the portal shimmer, temporarily uses the moongate action marker for
rendering, runs the tile-effect animation, clears that live cell back to
terrain `5`, and marks visibility dirty.

After clearing the tile, the hook has two outcomes. If the clock is in hour
`0` and the minute is below `10`, it reports success to the outer loop; the
outer loop then dispatches the same shrine/urn kneel overlay used by
M-Meditate. Otherwise, the hook chooses a destination from the cached moon-glyph
digits: before noon it uses the first cached glyph, and from noon onward it
uses the second. The glyph digit selects one of the saved Moonstone slots, and
the hook calls the same saved-slot warp helper used by Gate Travel. If that
warp changes scene, the outer loop exits through the normal scene-byte check.

The traced fixed-coordinate narrative gate remains separate from the ordinary
saved-slot natural moongates. It fires from the post-action special-tile pass
after a consumed command has committed movement and the loop has sampled the
party's underfoot world tile. The branch is checked only while still in
overworld mode on the surface plane at the fixed world coordinate `(233, 235)`.
It first prints the branch's opening narrative line, then reads the save-backed
ordained progress bitmask, not a Codex-read mask, moon phase, or
moongate-placement phase. If the ordained mask is nonzero, it prints the
blocked narrative and leaves the party in place. If the mask is clear, it
prints the two-line entry narration, moves the party one cell south, and then
continues through the ordinary post-action cleanup. This branch is a special
world-transition case, not the saved-slot live-tile refresh, not an
animator-origin collision test, not a Moonstone-slot Gate Travel cast, and not
a moon-phase display hook.

The gates' destinations form Britannia's in-game fast travel at the player
manual level. Placement and waning of live terrain, the live `0xDC` entry hook,
and the saved-slot warp target are specified from the saved Moonstone slots.
Do not infer natural-gate behavior from the render animator, the fixed
narrative gate branch, or the sky/status moon display alone.

One adjacent active-object rule is traced: if an outdoor active object commits a
step onto live terrain byte `0xDC`, that active-object slot is cleared. This is
a terrain-byte destination rule and does not conflict with active-object type
byte `0xDC` naming the first Dragon frame in the monster sprite domain. It also
does not own the player-facing natural-gate entry hook.

## 10. Lord British's path

A scripted path drives one cosmetic animation in the title sequence: Lord
British, in his throne room, traces a pattern that spells out his signature in
the floor tiles. The path is stored in `BRITISH.PTH` as a title-only pen
movement stream, not as an NPC schedule or gameplay route. The animation is
part of the title-screen overlay, not the overworld loop. The path file is
consumed only at title time; once gameplay starts, it is unread for the rest of
the session.

## 11. Vehicles

The party's transport state lives in the resident player record as an avatar/vehicle tile or transport marker. A nearby scene/action tag participates in timing and animation pendulums. These are related during movement, but they are not one byte and should not be collapsed into a single vehicle enum.

This section is the overworld summary. The command-level vehicle contract
for B-Board, X-Xit, ship broadsides, cannon fire, and vehicle object
persistence is centralized in `vehicles.md`.

The transport state covers the visible vehicle families:

- **On foot.** The default. Standard 2-minute outdoor turn.
- **Horse.** Mounted overland travel. It uses the standard 2-minute
  increment and the ordinary one-cell movement-command shape. The shared
  movement predicates provide the horse-specific terrain restrictions; no
  separate player rough-terrain stride table is part of the traced baseline.
- **Skiff.** Water-only transport. The time system has a `Q` state-tag modifier that halves the turn's minute increment, with a one-minute floor; public specs associate that timing with skiff/raft-like water travel without using `Q` as the full vehicle identity.
- **Ship.** Water-bound but faster than skiff. Uses the standard outdoor turn
  cost when manually handled; with sails hoisted, `weather.md` owns the
  wind-cadenced movement and any wait passes before movement releases.
- **Magic carpet.** Boardable carpet transport. The current public trace does not prove that carpet travel sets the `T` timing tag, so v1 should not make carpet travel minute-free solely from that tag.
- **Balloon.** Known from vehicle art/manual-facing material, but not promoted
  into the traced B-Board, X-Xit, U-Use, shipwright, active movement, or
  transport-marker contract. Do not infer a live boarding path, transport
  marker, landing rule, or wind drift from the other vehicle families.

Separately, the overworld active-object and encounter epilogue contains an
alternate-turn pendulum for traced transport-marker pairs in the horse/carpet
range. This is cadence evidence for actor and encounter passes, not proof of a
different clock increment and not a player movement-speed table.

The transport state is part of the save image and persists across save/load. Boarding (B-board) sets it; exiting (X-it) clears it. Dismounted vehicles live as active-object slots on the world stage and remain there indefinitely.

## 12. Time advancement

Each overworld turn that consumes the player's action advances the clock by **two minutes**. The time system's per-turn cleanup is called by the mode loop's per-turn block with the increment value 2.

Two state-tag modifiers can apply before the cascade:

- **`Q` tag.** The increment is halved (with a one-minute floor) before the cascade runs. Use this for the skiff/raft timing contract.
- **`T` tag.** The minute and light-counter writes are skipped for that cleanup call. Cleanup still recomputes daylight and can still mark visibility dirty. Current public evidence treats `T` as a scene/action tag, not as a proved vehicle identity.

The cleanup itself does the cascade — minutes to hours, hours to days, days to months, months to years. Shadowlord hideout maintenance runs at midnight, while character month counters and long-period flag clears run only when the day wraps past 28. On any hour change while the player is in a surface/town-family scene, the sky/status presentation row is refreshed; this is display work, not natural-moongate placement. The full cleanup contract is in `time.md`.

Two notable absences from the overworld's per-turn cleanup compared to town mode:

- **No NPC scheduler.** The schedule processor is not invoked from the overworld loop. NPC schedules are a town-mode-only concept.
- **No special "no-time" interactions.** Overworld turns either consume the standard increment or are no-ops at the dispatch level (the dispatcher returns 0 for actions that do not consume a turn, and the per-turn block skips the cleanup for those).

## 13. Hooks into other systems

**Visibility.** The producer reads the chunk buffer for terrain, the daylight value for ambient light, the player's torch / spell counters for personal light sources, and the local-light mask maintained by the visibility system. Dynamic actors affect the final viewport through the active-object compositor rather than a direct table scan inside the carve helper. Daylight on the surface follows the time system's day-night curve; on the underworld, the time system forces full-darkness regardless of hour. The overworld pre-loop underfoot probe can also force the cached light/radius value to zero while the party is on its special `0xFF` tile state, distinct from the visibility system's own hidden-cell marker that uses the same byte value inside the viewport scratch grid.

**Command dispatch.** The mode loop hands every printable letter to the resident command dispatcher (see `commands.md`). The dispatcher routes A-Attack and E-Enter to in-overlay handlers, X-Exit and B-Board to vehicle handlers documented in `vehicles.md`, K-Klimb to the outdoor mountain-climb handler, and the rest of the recognised alphabet to action overlays loaded on demand. `D` has no confirmed resident world-command handler and falls through to the stock refusal when it reaches the dispatcher.

**Active objects.** The overworld owns the player slot and a fixed quota of monster/vehicle/object slots. The per-turn animator, the random-encounter spawner, and the off-screen pruner all operate through the table. The combat framer save-and-restores the table around fights so the world resumes exactly as it was. Plane-swap (Z change) re-initialises the slots from the destination plane's seed `.OOL` file.

**Movement.** The shared movement spec owns direction-code routing,
the resident terrain-query layer, vehicle layering, dynamic occupancy, and commit
rules. This overworld spec owns the outdoor chunk buffer and the post-step
overworld effects that consume a successful movement.

**Time.** Per-turn cleanup runs once per consumed turn at increment 2; mode-zero recomputes run from the per-tick init at entry. Hour changes refresh the sky/status row through the time/status-panel path. Natural moongate live-terrain refresh and entry remain overworld-owned behavior, not a time-system or moon-display hook.

**Save / load.** The full state - party position, plane, active-object table, transport marker, scene/action tag - sits in the save-image region described in `save-load.md`. `SAVED.OOL` is the canonical per-plane object-overlay companion. The load path refreshes `BRIT.OOL` and `UNDER.OOL` from it so plane-entry paths can read the appropriate per-plane file; the save path stages from the per-plane files, refreshes both per-plane mirrors, repeats the `UNDER.OOL` mirror write unless the save handler entered with disk-prompt mode already set to mode 1, and writes the canonical `SAVED.OOL`.

**Combat.** Entered when a movement command targets a hostile monster's tile, when the per-turn block matches a pirate-ship trigger, or when an ambush event fires. The framer suspends the active-object table, runs a self-contained fight, and restores the table on return. See `combat.md`.

**Conversation.** The Talk command is *not* available in overworld mode (there are no scheduled NPCs to address). The dispatcher returns "no-op" for T outdoors. See `conversation.md`.

**Text output.** All overworld banners, prompts, and messages go through the standard text output stack. See `text-output.md`.

## 14. Overworld Boundaries And Remaining Work

The overworld/underworld loop is specified for the traced baseline at outdoor
mode depth: scene entry, chunk loading, live-buffer substitutions, movement
commit, special underfoot latch, confirmed surface chasm fall, active-object
per-turn handling, encounter probe inputs, save/object-overlay ownership, mode
hooks, saved-slot natural moongate live-tile refresh, and live `0xDC`
moongate entry handling are fixed. Encounter
probe and random-spawn behaviour are complete at overworld-loop depth; visual
atlas naming for spawned payload families belongs to tile/catalog and
presentation work. Timing-tag, transport-marker, and chunk-substitution naming
outside the traced baseline are catalog or opaque-data work rather than
unresolved outdoor loop control flow.

- **Random encounter payload presentation.** The 30-sided draw,
  threshold-exceeds gate, tile/Z/hour threshold formula, terrain selector,
  weighted bucket memberships, spawn-coordinate retry loop, and active-object
  payload-family selection are covered in `encounters.md`. Per-frame visual
  verification for ambiguous outdoor animated payload families and optional
  source-free reauthored data tables are catalog/data-publication concerns, not
  missing overworld probe logic.

- **Tile-class enumeration.** The runtime checks used by movement, encounter,
  active-object, camp, fall, ship-with-pirate, and special-tile handling are
  specified through this document and `catalogs/tile-catalog.md`. Remaining
  per-frame art labels or source-free reauthored-data tables are presentation
  and catalog QA, not overworld loop blockers.

- **Plane-transition inventory.** The traced falls handler covers the fixed
  Britannia chasm at `(54, 138)`, the outdoor active-object engagement path
  covers whirlpool forced-underworld movement to `(34, 18)`, and the
  town-family movement trace covers the special interior exit branch that
  selects the underworld plane. Current writer sweeps do not identify a mirror
  outdoor underworld-to-surface ascent set; if future evidence finds one, add it
  as a new writer rather than deriving it from the surface fall.

- **Transport marker values and timing tags.** The known foot, horse, carpet,
  ship, and skiff transport-marker ranges and low-bit facing rules are
  centralized in `vehicles.md`. Balloon art is not a traced live transport path
  for the analyzed baseline. Separately, the time cleanup's `Q` and `T` tags
  are documented as timing/state modifiers; `T` is not a proved vehicle
  identity. Any values outside the named ranges remain opaque unless another
  traced writer/reader promotes them.

- **Moongate entry path.** The animator, the scratch-writer census, the
  saved-slot live-terrain refresh, the live `0xDC` shimmer/entry hook, and the
  fixed ordained-bitmask narrative gate branch are documented. Future evidence
  may refine presentation timing or asset naming, but the outdoor-loop entry
  contract no longer depends on the render animator or status-strip moon
  display alone.

- **Per-turn pendulum ownership.** The outdoor epilogue's live cadence gates are
  specified: the `T` timing/state tag skips the active-object and encounter
  epilogue, the `Q` timing/state tag alternates it through a mode-local
  pendulum, and the traced horse/carpet transport-marker pairs alternate
  through a separate pendulum. Remaining work is writer/catalog ownership for
  unusual timing tags and transport markers, not an unresolved encounter
  suppression or double-roll rule.

- **Chunk-substitution semantics.** The chunk loader's live-buffer substitution
  cases are identified. The remaining work is semantic naming and optional
  helper-level polish for the substituted visual classes, not an unresolved
  map-file or outdoor-loop mutation rule.

## 15. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The overworld mode-loop main body — `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The pre-loop special-underfoot latch that forces zero light and gates outdoor
  movement commit — `u5-decomp/functions/MAINOUT_OVL/0x0A1A_mainout_pre_loop_water_check.md`.
- Local MAINOUT outer-loop analysis -- one-shot pending vehicle-acquisition
  active-object placement before normal outdoor input.
- The per-tick init that recomputes the scroll base and refreshes redraw flags — `u5-decomp/functions/MAINOUT_OVL/0x0000_mainout_entry.md`.
- The per-turn epilogue that walks the active-object table, animates and prunes, and rolls the random-encounter trigger — `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The OUTSUBS overlay's collection of overworld helpers — `u5-decomp/functions/OUTSUBS_OVL/OVERVIEW.md` and the eleven per-function notes in that directory: `0x0000_outsubs_water_check.md`, `0x004A_outsubs_chunk_classify.md`, `0x0098_outsubs_load_chunk.md`, `0x01B4_outsubs_load_4chunks.md`, `0x02C8_outsubs_scroll_chunks.md`, `0x0368_outsubs_world_filename.md`, `0x0388_outsubs_check_town_entry.md`, `0x0458_outsubs_falls_handler.md`, `0x0566_outsubs_actor_init.md`, `0x05FC_outsubs_check_status.md`, `0x0658_lord_british_dialogue.md`, and the superseded structural note `0x0658_outsubs_camp_or_save.md`.
- The world-tile getter that reads from the chunk buffer with the four-quadrant 2-by-2 interpretation — `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The moongate animator that paints the open / full / close cycle into the rendered buffer — `u5-decomp/functions/ULTIMA_EXE/0x70A6_moongate_or_event.md`.
- The saved Moonstone slot scene/window test, natural live-gate tile refresh,
  saved-slot warp helper, and live moongate-tile shimmer/entry helper -
  `u5-decomp/functions/ULTIMA_EXE/0x4702_npc_in_player_scene.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x475A_npc_schedule_tick.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x47F4_npc_warp_to_scene.md`, plus
  `u5-decomp/functions/ULTIMA_EXE/0x48A8_lockpick_or_unlock.md` (historical
  filename; note content now corrected).
- The town setup marker harvest that reuses the moongate animator coordinate
  scratch for primary and secondary asterisk markers — `u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md`.
- The combat loop exit reset of the moongate animation phase byte —
  `u5-decomp/functions/COMBAT_OVL/0x0B94_combat_main_loop.md`.
- The MAINOUT caller boundary for the live moongate-tile shimmer helper, as
  captured in `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The render-loop orchestrator — `u5-decomp/functions/ULTIMA_EXE/0x5910_world_tick.md`.
- The visibility producer that produces the 11-by-11 viewport scratch grid — `u5-decomp/functions/ULTIMA_EXE/0x5D0A_visibility_producer.md`.
- The per-turn cleanup that advances time, refreshes daylight, and dispatches the hour-change hook — `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The on-disk format of the surface and underworld grids — `u5-decomp/formats/maps.md`.
- The data-segment layout, including the shared scratch block read by the moongate animator, chunk-index tables, and the `WorldLocationTable` — `u5-decomp/formats/data-ovl.md`.
- Public scene/name binding for town-mode location rows — `catalogs/gazetteer.md`,
  `formats/npc.md`, and `formats/data-ovl.md`.
- Public dungeon scene/name/record binding — `systems/dungeon-mode.md`,
  `formats/dungeon-dat.md`, and the MAINOUT E-Enter helper re-derived from
  the private analysis workspace.
