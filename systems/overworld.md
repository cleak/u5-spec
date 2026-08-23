# Overworld

## 1. Overview

Ultima V's overworld is the open-air mode the player spends the most time in. Two surfaces share the mode: **Britannia**, the surface world the game opens on, and the **Underworld**, the lightless mirror beneath it. Both are 256-by-256 tile grids driven by the same mode loop, the same camera, the same per-turn cadence. They differ only in which on-disk grid the engine reads tiles from, what default lighting the time system applies, and which surface features distinguish them: town and dungeon entries, runtime moongate presentation, and a confirmed falls trigger on Britannia, plus a uniformly dark and chasm-strewn cavern below.

Within either surface the player commands a small party (or a vehicle carrying that party) and walks one cell per turn. Around the party live the *active objects* -- wandering monsters, vehicles, dropped items, and the player avatar slot itself -- while render-only effects such as spell and projectile frames are stamped into the viewport scratch outside that table. Each turn, the engine reads a command, dispatches it, advances time by two minutes, ticks every animated entity, rolls the random-encounter check, refreshes the daylight value, and rebuilds the on-screen viewport. When the command is "Enter" on a fixed town-mode or dungeon location coordinate, the loop sets a scene byte that the resident main-game loop sees on its next iteration, and overworld mode exits back to the dispatcher, which spins up town mode or dungeon mode. Falling through the confirmed surface chasm is different: it swaps the world plane while staying in overworld mode. Gate-like world-transition branches are handled as explicit underfoot special cases rather than as part of the general scene-entry dispatch.

The overworld is a thin shell over the resident systems. Almost everything that has its own spec — input, time, active objects, visibility, save/load — does the same work in this mode that it does anywhere else. The overworld's specific logic is small: which command goes where, when to load a chunk from disk, how to recognise the eight or nine tile types that mean "something special happens here", and a per-turn animator that is the dual of the town-mode NPC scheduler but does *not* consult the in-world hour. This spec describes those overworld-specific pieces and how they hook into the rest of the engine.

Shared terrain passability, dynamic occupancy, and movement commit rules are
specified in `systems/movement.md`. This overworld spec owns the outdoor map
source, chunk-window refresh, vehicle hooks, encounter hooks, and underfoot
special-tile probes that run around that shared movement layer.

## 2. The two surfaces

Britannia and the Underworld are the two values the *world plane* selects between. The plane is a single byte in the save image — the party's *Z* coordinate — and is consumed almost everywhere that decides which on-disk file a tile-read should hit and which lighting model to apply. Z is zero on Britannia and the all-ones byte (signed −1) in the Underworld.

Before reading the transition list, note that the plane byte is **overloaded**.
It means "which world" only while the scene byte says the party is outdoors.
Inside a building the same byte is the floor number, and inside a dungeon it is
the level index. Every reader and writer of it has to be interpreted in that
light, and an implementation that treats it as a global "which world" flag will
corrupt town floors and dungeon levels.

The player crosses between planes through exactly the routes below. The list is
closed: it comes from a complete census of everything that writes the plane
byte, not from a search that happened to stop.

- **Falling.** The traced falls handler has a confirmed fixed trigger at Britannia coordinate `(54, 138)`. When the party steps onto that chasm cell, the handler prints a falls banner and an underworld-transition line, applies the Dexterity-gated fall-damage check described in Section 8 to each non-dead party member, restores the pre-fall transport marker after the presentation clear, swaps the world plane to the underworld value, and re-initialises the active-object table for the new plane. The coordinate is hard-wired and fixed across all playthroughs.

- **Whirlpool forced-underworld transition.** Outdoor whirlpool active objects
  are another traced surface-to-underworld writer. When the adjacent-engagement
  path accepts the whirlpool branch while the party is not on foot, it prints
  the whirlpool warning, plays the swallow presentation, writes the underworld
  plane, moves the party to the fixed underworld emergence coordinate `(34,
  18)`, and re-enters overworld setup so chunks and active objects refresh for
  the new plane. If the party marker is the on-foot avatar when this branch is
  reached, no plane is written. *Corrected:* an earlier revision called the
  on-foot case "a no-op"; **that is withdrawn.** The on-foot arm still applies
  the impact payload of Section 6.2.4, which under a foot marker damages every
  living party member. It skips the plane transition, not the damage.

- **Interior exit plane selection.** Town-family exits clear the scene byte and
  restore overworld coordinates from the per-scene exit table. The traced town
  mover writes the surface plane for ordinary exits and writes the underworld
  plane for scene byte `0x19`. This is an interior-to-overworld
  exit rule, not proof of a general outdoor underworld-ascent tile set.

- **Not a plane writer: the narrative gate branch.** One traced surface
  coordinate owns a special narrative gate branch — the Shrine of the Codex
  approach of Section 9. It is listed here only to be excluded: it grants or
  refuses passage and can push the party one cell south, and it never writes
  the plane byte. An earlier revision counted it as a sixth plane-crossing
  route; that is withdrawn, and the closed writer sets in
  `systems/doors-and-z-transitions.md` Section 14, `formats/under-dat.md`
  Section 7 and `catalogs/gazetteer.md` Section 8.3 correctly omit it.
  Ordinary natural moongates are the separate saved-Moonstone-slot route in
  the next bullet but one; their live-terrain refresh and entry helper are in
  Section 9.

- **Dungeon exits.** Leaving a dungeon writes the plane as well as the scene:
  off the topmost level the party surfaces on Britannia, and out through the
  bottom of the lowest level they arrive in the Underworld. Either way they land
  on that dungeon's own outdoor entrance cell. `systems/dungeon-mode.md` owns
  the contract and `catalogs/gazetteer.md` Section 6.1 the per-dungeon detail.

- **Moongates and Gate Travel.** Both resolve to a saved Moonstone slot and copy
  that slot's recorded plane along with its coordinates. All eight slots ship
  recorded on the surface, so in a stock game this is the ordinary way back up
  from the Underworld.

- **No outdoor ascent exists.** There is no Underworld terrain feature that
  lifts the party to the surface - no mirror of the surface chasm, no upward
  whirlpool, nothing. This is a closed negative result from a complete writer
  census, not an unexplored area, and an implementation should not invent one.
  The only ways back to the surface are a dungeon's top exit, a moongate or Gate
  Travel to a surface Moonstone slot, and reloading a saved position.

The mode loop itself does not branch on Z. The chunk loader, the visibility producer, the renderer, the daylight calculator, and the random-encounter spawner treat the two planes identically — what differs is the data the helpers consult: a different on-disk grid (Section 3), a forced full-darkness ambient light on the underworld plane, and a different active-object seed file.

## 3. Map structure

Each surface is a flat 256-by-256 grid of tile bytes — one byte per cell, no padding. The grid is held on disk as a sequence of 16-by-16 *chunks*, each chunk a 256-byte block laid out row-major. The world has 256 chunks total (sixteen across by sixteen down). On Britannia the mapping from chunk grid position to disk offset goes through a 256-byte *chunk-index table* in the resident data segment; in the Underworld it is plain arithmetic.

The chunk-index table encodes one byte per chunk in row-major order. The byte is either a chunk's 0-based index in the on-disk file or the all-ones sentinel meaning *all-water*. On Britannia, large stretches of open ocean are pure water, and the on-disk grid omits those chunks — only the non-water chunks are stored. The index byte for a water chunk is the all-ones sentinel; the chunk loader recognises this, fills the chunk buffer with the water tile, and returns without doing any disk I/O. A non-sentinel index is the zero-based file index, multiplied by 256 to give the seek offset. This compression-by-omission is why Britannia's on-disk grid is about 52 KB rather than 64 KB.

The Underworld is dense — every chunk is stored, including uniformly cavern
ones. Its on-disk grid is exactly 64 KB and its chunk index is the identity
map, **computed rather than looked up**. There is no second resident
chunk-index table: the single resident table accounts for the 205 stored
Britannia chunks and nothing else. The shared per-chunk loader tells the two
planes apart by the **first letter of the map filename** it is handed — the
Britannia arm indexes that table and synthesizes an all-water chunk on the
sentinel, while the Underworld arm uses the caller's chunk-aligned descriptor
directly as the file offset. An earlier revision of this section said "the same
table format is used; only the contents differ", implying a second resident
table for the Underworld; that is withdrawn. See `formats/under-dat.md`
Section 1 and `formats/data-ovl.md` Section 5.2.

After a chunk is loaded or synthesized, the loader walks the 16-by-16 live
chunk copy and applies a substitution pass that re-derives two pieces of quest
presentation from save state. **Both substitutions are conditional; neither is
unconditional.** A cell holding a dungeon-entrance tile (`0x16`, `0x17`, `0x18`)
is rewritten to the collapsed-entrance tile `0xDF` only while the Word of Power
owning that chunk is still unspoken; a cell holding the shrine tile `0x19` is
rewritten to the ruined-shrine tile `0x1A` only while that chunk's shrine is
marked ruined. Each of the eight words owns exactly one chunk, and a parallel
list assigns chunks to shrines; the two rules take opposite defaults for a chunk
that owns neither, and the full contract is in `formats/brit-dat.md`
Section 9.1 and `systems/commands.md` Section 11.2.

Because these are the only producers of the sealed and ruined tiles, an engine
that applies either rewrite unconditionally leaves every dungeon entrance
permanently sealed and the Word of Power apparently inert, while one that omits
the pass entirely starts every dungeon open on a new game. Both substitutions
affect only the live chunk/window state, leave the on-disk chunk untouched, and
are separate from the per-turn tile animator.

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

3. **Block on input.** Call into the input system's keystroke fetch. Sub-printable codes are control keys (direction codes and the mode-local Control bindings), and printable bytes are commands like A-attack, E-enter, T-talk, K-klimb. Under sail on the wind-driven cadence, this step does not read the keyboard at all: the input helper returns the cached sail direction instead, which is how a ship keeps moving with no keypress.

4. **Mode-switch exit check.** If the *scene byte* has gone non-zero since last iteration — because a sub-handler dispatched into a town-family scene or a dungeon-class scene — break out and return to the resident main-game loop. Combat is handled through a framer that restores the pre-combat scene before the outer loop sees it.

5. **Dispatch the command.** Three layers: control codes go through a small dispatch table; digits go to the speed selector; everything else goes to the resident command dispatcher, which routes single-letter verbs to per-letter handlers in this overlay (Attack, Enter, ...) or to one of the action overlays (Cast, Talk, Look, Stats, ...). The overworld reads the returned status as a single boolean — zero skips the whole per-turn block, and every non-zero value is treated identically (`commands.md` Section 3).

   The overworld's own control-code table is small. The four cardinal direction codes route to movement. Four typed Control bindings are shared with the other modes: an "Exit to DOS?" prompt, a moral-standing readout printed as a number, a sound toggle that prints its new state, and a version banner. None of the four consumes a turn. Every other control code prints the stock refusal. One table slot is synthetic — it can only be produced internally, reports "no action", and prints nothing.

6. **Per-turn block (only when the action consumed a turn).**
   a. Run the per-turn cleanup (see `time.md`) with a minute increment of two — the standard outdoor turn cost.
   b. Re-read the tile under the (now possibly moved) party.
   c. Camp / wishing-well dispatch if the tile matches.
   d. Pirate-ship ambush if the tile and transport state indicate one.
   e. Fixed narrative gate branch if on its surface-world coordinate.
   f. Per-turn party-status tick through the OUTSUBS status helper.
   g. Active-object animator if the under-tile is animated (Section 6).

7. **Loop.** Back to step 1 unless the exit flag is set.

Ahead of the input block of step three, each iteration runs the shared
party-capability check that all three exploration modes use, described in
`systems/main-loop.md` Section 6: if nobody in the party can act but somebody is
asleep, the loop prints the sleep line and passes the turn without reading a
command; if nobody can act and nobody is asleep, it runs the total-party-defeat
sequence of `systems/blackthorn.md` Section 7 instead of taking a turn. The
overworld contributes no condition of its own to that check. It does add
bookkeeping on the defeat path: when the party is on the Britannia surface
rather than in the Underworld, the loop first asks the player to make the
surface map file available and re-asks until it is, and it then runs a
maintenance pass over the active-object table. Neither step is a precondition —
the sequence runs either way, and the object pass runs on both surfaces.

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
- **Render-only effects.** Natural moongates are not active-object slots: a gate
  is live terrain, written into the map buffer by the once-per-turn refresh of
  Section 9. It is not a "render-only effect" in the sense of something the
  renderer invents and the map does not know about - but neither is it drawn
  like any other tile, because the renderer resolves it through the presence
  phase of Section 9.1.

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

### 6.1 How a creature chooses its step

Creature movement on the overworld is simpler than it is often assumed to be,
and the simplification is part of the compatibility contract.

A wandering creature reduces its offset from the party to a **direction on each
axis** and ignores how far away the party is. The two distances are never
formed and never compared with each other, so there is no "move along the longer
axis first" rule and no special handling for a creature that stands exactly
diagonal from the party.

Each turn the creature flips a fair coin to decide whether to attempt the
horizontal or the vertical move first, then takes whichever of the two is legal,
preferring the one it tried first. On an exact diagonal this means it moves
horizontally half the time and vertically half the time, re-rolled every turn.

If neither directed move is legal, the creature instead attempts one randomly
chosen cardinal move. That single attempt is why a blocked creature shuffles
rather than freezing in place, and why it can work its way out of a dead end
without any pathfinding.

`active-objects.md` owns the validation steps a candidate cell must pass and the
post-validation terrain chance gates. No outdoor "directed-step probe" or
"path-clear scan" participates in creature movement; earlier drafts that
described one were wrong, and the line-tracing routine they were thinking of
belongs entirely to the ranged attacks below.

### 6.2 Creature ranged attacks

Some creatures attack the party at a distance instead of closing with it. Two
outdoor cases exist. They share one trace procedure and one damage payload, and
**this section is the normative owner of both**. `systems/active-objects.md`
Section 8 describes the same two reactions from the per-turn walker's side and
points here rather than restating the contract.

#### 6.2.1 Which creature fires, and when

| Attacker | Recognition | Geometry | Roll | Announcement |
|---|---|---|---|---|
| Sea serpent or dragon | The slot's type byte **equals** the first frame of the Sea Serpent run (`0x88`) or the first frame of the Dragon run (`0xDC`). Exact equality on the unmasked byte. | Wrapped absolute separation from the party of at most three on **both** axes, inclusive on each axis | One-in-eight each turn | None |
| Hostile ship / water creature | The slot's type byte, masked to its four-frame family, is the water-creature / pirate family `0x2C..0x2F` | Strictly axis-aligned: zero separation on one axis, separation below four on the other | None; it fires whenever the geometry holds | A boom message before the shot |

Three properties of the recognition tests are contract:

- **The breath test is exact equality — not a range, not a masked family.**
  Sibling animation frames `0x89..0x8B` and `0xDD..0xDF` never enter the breath
  branch. This is why `systems/active-objects.md` Section 8 calls these the
  *first-frame* classes, and the word is meant literally.
- **The broadside test is a masked family test**, deliberately unlike the one
  above. The same walker uses both forms a few steps apart. Do not generalise
  either rule to the other.
- **Orthogonal adjacency is tested before the class test.** A sea serpent or
  dragon standing exactly one cell north, south, east or west of the party takes
  the adjacent-engagement path and does not breathe that turn. In play the
  breath is a two- or three-cell reaction, and the broadside reaches only
  effective distances two and three, adjacency having been consumed first.

The one-in-eight is exact rather than approximate. The shared range draw is
**inclusive on both bounds**; the breath asks for the closed interval `[0, 7]`
and fires on one of those eight outcomes.

Counting the geometries this admits: with separation of at most three on both
axes, excluding the co-located cell and the four adjacency cells, **44** signed
offsets reach the breath branch. Eight are cardinal, twelve are exact diagonals,
and the remaining **24** are neither — non-cardinal, non-diagonal breath lines
genuinely occur. The broadside admits exactly **8** offsets: two and three cells
out along each of the four cardinal directions.

#### 6.2.2 How the line is generated and sampled

*Corrected:* an earlier revision of this section said "a straight line is traced
from the attacker's cell to the party's cell, drawn as an animated projectile
travelling along that line, and tested cell by cell for obstructions as it
goes." **The cell-by-cell reading is withdrawn.** The trace runs at sub-tile
resolution, and obstruction testing happens only at positions sampled at a fixed
interval along it. Cells that lie on the geometric line are routinely skipped,
one cell is often tested twice, and for several geometries the projectile stops
short of the party's cell while still counting as a hit.

**Coordinate space.** Both endpoints are converted from cells to sub-tile
positions before the line is generated. There are sixteen sub-tile units per
cell; cell `c` owns the closed span of positions `16c + 8` through `16c + 23`,
and an endpoint converts to `16c + 16`. The inverse conversion, applied to every
sampled position, subtracts eight and divides by sixteen truncating toward zero.
Positions outside the closed band `[8, 183]` on either axis are off the
eleven-by-eleven viewport; reaching one ends the walk and reports a clear line.

**Generation.** The two axes are not treated alike. The **column** axis is the
driver and the **row** axis is accumulated:

- The column advances exactly one sub-tile step per iteration, toward the target.
- An accumulator carries one hundred times the row-per-column slope, truncated
  toward zero exactly once at setup and then taken positive. A shot with no
  column delta substitutes a very large constant in place of the slope.
- The accumulator is **initialised to that full slope value** — not to zero, and
  not to half of it.
- At the top of each iteration, while the accumulator is strictly greater than
  zero and row steps remain, the row advances one step and the accumulator loses
  one hundred. This repeats within the same iteration, so a steep line takes
  several row steps per column step. This is not one-minor-step-per-major-step.
- The column then steps and the slope value is added back to the accumulator.
- The starting position is itself part of the emitted run.

Four consequences are contract, because they are where an implementation that
substitutes a textbook line-drawing routine will diverge:

- Because the accumulator starts full, the first thing after the start position
  is a **row** step whenever the shot has any row delta at all. The projectile
  leaves the attacker's cell vertically before it moves horizontally.
- An accumulator value of exactly zero does **not** step the row: the test is
  strictly greater than zero. There is no other rounding anywhere in the walk.
- Consecutive emitted positions differ on exactly one axis, by one unit.
- The run always ends inside the target cell, but the column coordinate may
  overshoot the target position by exactly one sub-tile step **in the direction
  of travel** — never more, and never far enough to leave the target cell. A
  shot with no column delta always ends one such step off on the column axis.

**Sampling and testing.** The walker does not visit every emitted position. On
the overworld it visits every thirteenth position, starting with the first. For
each visited position, in this order: convert it to a cell, and stop reporting
*clear* if either coordinate is outside the valid band; draw the effect figure;
wait briefly and flush the dirty rectangle; advance the sampling index, and stop
reporting *clear* if the run has ended; **and only then** test the current cell
for obstruction. **The last sampled cell is therefore never obstruction-tested**,
and neither is any position the sampling interval skips.

The obstruction test consults the on-screen eleven-by-eleven viewport tile grid
rather than the world map, against a fixed per-tile-id passability bitmap in
which exactly **46** of the 256 tile ids block. A blocking cell whose coordinates
equal the shooter's own starting cell is ignored and the walk continues — this
is a coordinate comparison, not a "skip the first sample" rule, and it is why
the attacker's own cell never obstructs its own shot. Any other blocking cell
ends the walk and reports *blocked*.

Return polarity, stated positively: **a run that reaches the end of the
generated line reports clear, and clear is what both outdoor call sites treat as
a hit.** *Blocked* means the shot stops where it stopped and nothing further
happens — no payload, no message, no state change.

**Worked example.** A creature three columns east and one row south of the party
sits at viewport cell (8, 6) with the party at (5, 5). The generated run holds
sixty-five positions. Sampling every thirteenth gives five visits, whose cells
are (8, 6), (7, 6), (7, 6), (6, 5) and (6, 5) in that order. The first is the
launch cell and is exempt; the next three are tested; the fifth is the last
sample and is not tested. Exactly two distinct cells, (7, 6) and (6, 5), can
block this shot. Cells (8, 5), (7, 5), (6, 6) and the party's own cell (5, 5)
are never tested — the projectile is never even drawn on the party's cell — and
the hit is still awarded.

Two results hold across every reachable geometry of both attacks, swept
exhaustively over the 44 breath offsets and the 8 broadside offsets: **the
party's own cell is never obstruction-tested**, and the number of tested samples
per shot lies in the closed interval `[2, 7]`, inclusive. In twelve of the
forty-four breath geometries the sampled path never reaches the party's cell at
all, and a broadside fired three cells away never samples the party's cell — the
animation visibly stops one cell short and still connects.

#### 6.2.3 Symmetry with the player's own shot

*Corrected:* an earlier revision said "the player's own ranged attack uses the
identical procedure with the endpoints exchanged, so **line-of-fire rules are
symmetric between the party and the creatures**." The shared-routine half stands;
**the symmetry conclusion is withdrawn.**

The same routine is used with the endpoints exchanged, and an implementation
should share it. But the traced cell set is **not** mirror-symmetric in general:
the column axis drives the walk and sampling starts at the shooter's end, so
exchanging the endpoints can change which cells are tested. Sixteen of the
forty-four breath geometries have direction-dependent effective-blocker sets.

Two positive statements bound that. Every one of those sixteen is non-cardinal
and non-diagonal; and every cardinal geometry and every exact-diagonal geometry
traces identically in both directions. On the overworld the player's own shot is
always axis-aligned — the fire-direction prompt yields a single unit cardinal
step, the ship-facing gate requires the fire axis to be perpendicular to the
hull, and the target search steps one to three cells along that cardinal — so
the asymmetry is not observable in overworld play. It remains a property of the
shared routine: **trace from the actual shooter's cell; do not normalise the
direction and mirror the result.**

#### 6.2.4 The damage payload

On a clear line the attack connects, and the payload below runs. It is the same
payload for both outdoor ranged attacks: the calls and their arguments are
identical. (The two tails around them are not byte-identical — the broadside
rebuilds the viewport once more before the impact presentation, and the two pass
different effect-figure indices — but nothing in the payload itself differs.)

The same payload is also reached from the sand-trap adjacency reaction and from
the whirlpool engagement described in Section 8 and in
`systems/active-objects.md` Section 8. Two further outdoor sites reach it whose
triggers are not established; see Section 6.2.5.

**Stage one — impact presentation.** An impact figure is drawn at the party's
own map coordinates (converted to viewport-relative coordinates), a short tone
plays, and the viewport is rebuilt. This stage writes no character state and no
vehicle state, and prints no narration line.

**Stage two — impact absorption.** This stage takes no arguments and branches on
exactly one thing: the party's transport marker.

- **Aboard a frigate** — any marker in the hoisted or furled ship families of
  `systems/vehicles.md` Section 2, meaning all four headings and both sail
  states, eight values in total. Draw a uniform integer in the **closed interval
  `[1, 30]`, inclusive on both ends**, and compare it against the ship's
  hull-condition byte (active-object byte `+5` of the party's vessel record).
  - Roll **strictly less than** the hull: subtract the roll from the hull,
    repaint the stats panel, and return. **No party member loses hit points.**
    The hull cannot fall to zero or below by this route; the least it can hold
    afterwards is one.
  - Roll **greater than or equal to** the hull: the ship is destroyed. The
    ship-sunk line prints and the loss-of-ship ladder in
    `systems/vehicles.md` Section 6 runs exactly as published there.
- **Under every other transport marker** — foot, horse, carpet, skiff, and the
  sprite-suppressed value — the **whole-party damage pass** below runs, and the
  stage returns.

**Target selection, as a positive statement.** The whole-party damage pass walks
roster slots from index zero upward. For each slot index that is **below the
party-size byte** and whose **status byte is not the dead marker**, it draws its
own **fresh, independent** uniform integer in the **closed interval `[1, 8]`,
inclusive on both ends**, and applies it. The pass's own hard bound is six slots,
indices `0..5`.

What demonstrably does **not** apply — scoped to the whole of that pass and the
whole of the absorption stage, both of which were read from entry to exit:

- No active-player selection, no first-living selection, no single randomly
  chosen target, and no fixed slot. Every qualifying member is damaged.
- One roll per damaged member, not one roll shared between them.
- No attacker identity, sprite byte, class or sentinel participates anywhere on
  this path, and the path never reaches the combat damage-and-status resolver.

**The per-member application.** The pass applies each amount through the same
party-damage helper that the surface chasm/falls row of Section 8 uses for its
one-point fall damage. That helper:

- flashes the member's row in the stats panel;
- subtracts the amount from that member's **current hit points** word, character
  record `+0x10` (`formats/saved-gam.md` Section 3.1);
- if the signed result is zero or below, clamps that word to **zero** and writes
  the **dead** status letter into the member's status byte, record `+0x0B`;
- if the member that just died is the currently selected character, writes the
  published "none selected" value into the active-player index byte
  (`formats/saved-gam.md` Section 5). That value is the no-active-member
  sentinel; it is **not** an attacker id, and nothing on this path reads it back
  as one;
- repaints the stats panel.

Maximum hit points, experience, level, magic points and equipment are untouched
by this helper. That list is bounded by the helper's own body, which was read
from entry to exit; the one routine it calls that was not fully read is named as
a gap in Section 6.2.5.

**The payload prints no narration line — but it is not silent on screen.** The
closing stats-panel repaint draws panel text, including the hull readout while
the party is aboard a frigate. Implement "no narration line", not "prints
nothing".

Two presentation notes. The two outdoor cases share the flight machinery but
pass different effect-figure indices, selecting what is drawn at each sampled
position. An inherited description, not re-derived by the verification pass, has
the ship's broadside drawing a small solid burst travelling along the line and
the breath painting a coloured spark cloud around each sampled position with no
outline; treat the appearance itself as unverified (Section 6.2.5). The firing
sound is played by the caller before the flight begins, not per sampled
position. Neither the generic "attacked" message nor any melee narration belongs
to these paths; that message is the adjacent-engagement case.

None of this changes turn cadence, the encounter-spawn formula, or active-object
pruning.

#### 6.2.5 Named gaps in this section

These are open. The engine must not treat their absence from the text above as
licence to invent a rule.

- **Stats-panel repaint field census.** The closing repaint called by the
  per-member helper was read only as far as its frigate hull-readout branch. It
  is established positively that it prints panel text and that nothing in the
  part read writes a character record. It is **not** established that it writes
  no character field and narrates no death. Until that routine is read to its
  end, treat the field list above as "these fields are written", not as "only
  these fields are written". Reading that routine, and the per-slot panel-row
  routine it calls in its loop, would settle it.
- **The status-byte domain.** The pass's only status test is inequality against
  the dead marker, and that inequality is what is published. Whether "not dead"
  is equivalent to membership in any particular set of living letters is **not**
  established: the scan for status writes covered one addressing form only and
  found writers for good, poisoned and dead; the shared living-member scan tests
  good, poisoned and sleeping; no write of the charmed letter was found.
  `formats/saved-gam.md` Section 3.1 carries the same caution about the letter
  space. Implement the inequality, not a living-letter whitelist. A scan for
  status stores through computed pointers would settle it.
- **Drowning-loop asymmetry.** The whole-party pass skips only dead members,
  while the living-member scan that decides whether the drowning loop of
  `systems/vehicles.md` Section 6 continues counts only good, poisoned and
  sleeping members. A member in some other living state would keep taking damage
  while no longer being counted alive by the exit test. Whether that state is
  reachable is unexamined, and what runs after that loop exits was not traced.
- **Two further absorption sites, triggers unestablished.** Besides the two
  ranged attacks and the Section 8 adjacency reactions, the outdoor code reaches
  the same impact-absorption stage from a sailing-collision site and from a
  per-turn site preceded by a rough-seas line and guarded on the party marker
  being a skiff or a carpet. Both calls, and the second one's marker guard, are
  established; neither enclosing routine was read to its end, so **neither
  trigger is published as a mechanic**. Reading those two routines would settle
  what schedules them.
- **Call discovery is near-call only.** The census of sites reaching this
  payload — and the count of creatures that can fire a ranged shot at all — is
  an exhaustive byte scan for near calls across the shipped executable and every
  overlay with a published load base. It does not cover far calls, indirect or
  computed calls, or table dispatch, and four overlays have no published load
  base. A dispatcher-reached caller would not appear in it. Inside the routines
  read entry-to-exit there are no indirect or far calls on this path; that is a
  whole-routine statement, not a whole-program one.
- **Interior, dungeon and combat modes are out of scope.** Everything in
  Section 6.2.2 is overworld-only. The sampling interval is smaller in interior
  scenes, which changes every tested-cell set above. The non-overworld branch of
  the player's Fire command calls the same walker with a different argument set
  that was not traced, and no combat or dungeon breath analogue was examined. Do
  not carry this section into those modes without redoing the work.
- **Unresolved viewport cells and stamped actors.** An unresolved viewport cell
  — one the visibility pass never filled — holds a value the passability bitmap
  marks passable, so darkness of that kind does not block a shot. That is a
  positive result about the fill and the bitmap. The broader claim "no cell the
  party cannot see ever blocks" is **not** established: the shadow-casting pass
  that fills visible cells, and the pass that stamps active-object sprites into
  the same grid, were not read. Whether a creature standing between attacker and
  party blocks the line is therefore open.
- **The blocking tile-id set is uncharacterised.** The 46 blocking ids are
  established as a set of ids; they were not mapped to named terrain, and
  whether other systems read the same bitmap was not checked.
- **Frigate sub-state narrowing.** The absorption stage's ship branch covers both
  hoisted and furled markers. The per-turn walker that reaches the ranged
  branches was not read to its end, so a gate above it that narrows which frigate
  sub-states can reach a ranged attack cannot be ruled out.
- **Long-line edge cases.** The generator carries a step budget, and only the
  first part of each path buffer is pre-filled with the run terminator. A line
  long enough to exhaust either is unreachable at breath and broadside ranges and
  was not analysed. An implementation should not reproduce a wrap or an
  uninitialised read here; treat long lines as undefined and out of contract.

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

  On a match, the original path emits the location-entry prompt, performs any needed surface-disk availability check, clears or reseeds the active-object table, writes the scene byte to `matched_row + 1`, and seeds the party's town-mode coordinates on floor zero. The following town entry pass owns the final player placement; see `systems/town-mode.md` Section 5 step 6, which now records the player's fallback entry cell as an open item (the `LocationEntryYTable` rule previously stated there belongs to the Shadowlord install, and the phantom-NPC representation of the player is withdrawn entirely). If no row matches, E-Enter does not change mode.

- **Dungeon entrance.** E-Enter compares the party's current coordinate against rows thirty-two through thirty-nine of the same DATA.OVL-derived `WorldLocationTable`. Row thirty-two maps to `DUNGEON:0` / scene byte thirty-three, row thirty-three maps to `DUNGEON:1` / scene byte thirty-four, and so on through row thirty-nine mapping to `DUNGEON:7` / scene byte forty. The name and data-record order is Deceit, Despise, Destard, Wrong, Covetous, Shame, Hythloth, Doom.

  On a match, the engine emits the dungeon-entry prompt, loads the selected 512-byte `DUNGEON.DAT` record into the active dungeon tile buffer, writes the scene byte to `matched_row + 1`, and seeds dungeon-mode level, X/Y, and facing. Surface-plane entry lands at level `0`, X `1`, Y `1`, facing east. Underworld-plane entry into non-Doom dungeons lands at level `7`, X `7`, Y `7`, facing west. Doom uses the surface-style entry seed even when reached from the underworld. This seeding belongs to the walk-in entry path only; the load-game path never writes the dungeon facing, so a resumed save keeps whatever facing it recorded. If no dungeon row matches, E-Enter does not change mode.

  Two gates sit in front of that seed. **Transport:** only a party travelling on
  foot may enter; a mounted, sailing, or flying party is refused with the
  on-foot message. **Doom:** entry into Doom additionally requires all three
  Shadowlords to have been destroyed. A party that tries earlier is told it is
  attacked at the entrance, an ambush object is spawned beside them, and the
  scene byte is not written. Doom's coordinate carries an entrance tile in the
  Underworld only, so in practice Doom is entered from below or not at all.

- **Shrine.** A meditation prompt with its own subsystem handlers; from the overworld's perspective, the trigger is a tile-class match.

- **Moongate.** Section 9.

- **Falls (chasm).** A confirmed fixed Britannia coordinate, `(54, 138)`, triggers the fall-into-underworld transition.
- **Whirlpool.** Outdoor whirlpool active-object engagement can force the
  party to the fixed underworld emergence coordinate `(34, 18)` on the
  underworld plane. This is an active-object engagement effect, not a dungeon
  or town scene-entry route. It also applies the Section 6.2.4 impact payload,
  on foot as well as aboard a vehicle; see the forced-movement table below for
  the two withdrawn statements this corrects.

- **Water and current-like movement.** The traced overworld loop does not
  publish a general player-facing waterfall/current sweep that repeatedly
  pushes the party or vessel through a coordinate row. Water movement is
  ordinary one-cell movement through the transport-specific terrain predicates
  in `systems/movement.md`, plus the active-object effects listed below.

  | Trigger family | Trigger source | Movement / transition effect | Transport handling | Damage, messages, and persistence |
  |---|---|---|---|---|
  | Ordinary water travel | Player directional movement into a destination cell accepted by the current transport predicate | One committed cardinal step; no sweep, queue, or multi-cell current is installed | Ships accept the deep-water/water predicate; skiffs use the facing-sensitive skiff predicate; foot and horse reject ordinary water through their predicates; carpets use their own carpet predicate; balloon has no promoted live transport path | Normal consumed-turn timing only; no drowning roll or queued forced-movement state |
  | Pre-loop `0xFF` underfoot state | The tile under the party is the special all-ones tile and the exemption state is not active | Suppresses the next movement commit while forcing the cached light/radius to zero | Applies to the mode loop state rather than to a vehicle family | No damage, no status change, and no scene/plane transition; clearing the state recomputes light with a zero-minute cleanup |
  | Surface chasm/falls | Britannia coordinate `(54, 138)` | Prints the falls presentation, switches the world plane to the underworld value, and reloads the destination plane/object state | Vehicle marker is saved across the presentation clear and restored before the plane swap completes; the traced falls handler does not force the durable post-transition transport marker to foot | Each non-dead party member is checked once during the fall presentation: draw one random byte `0..255`; if the member's Dexterity byte is greater than the roll, no damage is applied, otherwise the normal party-damage helper applies `1 HP` damage. That helper is the same per-member application specified in Section 6.2.4. There is no persistent partial-fall queue; save/load sees only the resulting coordinates, plane, transport marker, party HP/status, and active-object table |
  | Whirlpool active object | Orthogonally adjacent outdoor active-object slot in the whirlpool family | If the party is not on foot, clears the whirlpool slot, prints the whirlpool warning, plays the swallow presentation, applies the Section 6.2.4 impact payload, moves the party to `(34, 18)` on the underworld plane, and re-enters overworld setup | *Corrected:* an earlier revision said the on-foot state is a no-op defensive branch; **that is withdrawn**. The on-foot arm tests the marker for the published foot/avatar value and reaches the Section 6.2.4 impact-absorption stage, which under a foot marker is the whole-party damage pass. Ship, skiff, carpet, horse, and any other non-foot marker all take the same forced-underworld branch when this active-object engagement path is reached, and that branch reaches the same absorption stage immediately before the plane change | *Corrected:* an earlier revision said no drowning damage is applied by the whirlpool branch; **that is withdrawn**. Both arms reach the Section 6.2.4 payload. One mechanism detail matters here: the swallow presentation temporarily overwrites the party marker with the whirlpool sprite and **restores the original marker before** the absorption call, so aboard a frigate the closed-interval `[1, 30]` hull roll really does apply and can sink the ship in the instant before the teleport — with the coordinate change and overworld re-entry still following. The transition is immediate and durable in ordinary save state after it completes; there is no queued or partially resolved forced movement |
  | Water-creature / pirate active-object movement | Outdoor active-object slots in the water-creature/pirate frame family | Active objects move one cardinal cell when their cadence and validation allow it; they do not push the player along a current row | This is actor movement, not player transport. Wind cadence controls ship-like water-creature movement; ordinary player ship/skiff movement remains command-driven | May print the attack line or enter the ordinary engagement/combat path when adjacency/collision rules fire; it does not install a water-current sweep |

- **Other plane-transition routes.** None. Outside the falls cell, the
  whirlpool engagement, the interior-exit branch, and the dungeon exit, nothing
  writes the world plane during outdoor play. In particular there is no outdoor
  Underworld ascent tile. Section 2 carries the closed inventory.

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

Moongates are the surface plane's signature feature. At player-facing design level, eight gates appear and disappear with the clock and provide fast travel between fixed Britannia locations. The binary-compatible contract below has three parts and one retraction: the saved-slot live-terrain refresh that places and removes gates, the live entry hook that consumes one and warps the party, and the separate Shrine of the Codex approach branch - plus the withdrawal of the "render-frame animator" that earlier revisions described.

**There is no moongate animator.** Earlier revisions of this document
described a per-render-frame animator that read a small resident scratch block
as a gate origin, a gate destination and a sixteen-step animation phase, and
stamped moongate frames into the rendered buffer. That reading is withdrawn in
full, and an implementation carrying it should delete it rather than adapt it.

The scratch block it described belongs to the **night-time light beacon**
specified in `systems/visibility.md` Section 12.6. Its coordinate words are
light-source positions harvested from the loaded map, its phase byte is the
beacon's current bearing, and it never holds a moongate. Three specific
consequences follow:

- Natural moongates are ordinary **live terrain**. They are written into the
  live map by the once-per-turn refresh below and drawn by the normal renderer,
  never by an animator of their own. That does **not** make a gate a static
  sprite. The renderer resolves a moon-gate cell through the sixteen-phase
  rise-and-sink model in Section 9.1, reading the same presence counter the
  refresh advances. Nothing about a gate's appearance is per-*frame*, and
  nothing resets when a frame is skipped - but the appearance is not fixed
  either, and an implementation that draws the gate tile unconditionally is
  wrong in a different way than the withdrawn animator was.
- The supposed "daylight threshold" precondition was also inverted. The beacon
  that owns that gate runs only **after dark**; nothing runs it by day.
- The supposed "destination" coordinate pair was never a teleport target. A
  gate's destination comes from the Moonstone slots.

The Moonstone slots are eight persisted destinations in `SAVED.GAM`, shared by
natural gates and by *Vas Rel Por* / Gate Travel. The traced Moonstone U-Use
helper writes only the selected saved slot after validating the current scene
and underfoot terrain; it does not teleport the party. Burying a moonstone is
therefore how a gate relocates - the slot takes the party's current position,
and both that gate's nightly appearance and every arrival that selects that slot
move with it. The eight shipped slot positions are published in
`catalogs/gazetteer.md` Section 8.1, and all eight ship as surface grass cells,
which is exactly the terrain the daytime pass restores when a gate closes.

The ordinary natural-gate live-tile refresh runs once per world turn during the
resident world tick, for non-combat scenes. It treats the eight
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
it is driven by saved Moonstone slots.

That counter is **persisted world state**, not scratch. It occupies the
byte at `SAVED.GAM` offset `0x02E1`, inside the mode-scratch band next to the
cached moon glyphs, and the shipped starting save holds zero there - correct,
because the game opens at hour eight with no gate up. Its lifetime is discussed
in full in Section 9.1, because getting that lifetime wrong is the single most
likely way to mis-implement this feature.

**The moon phase plays no part in whether a gate is present.** Placement is
gated on the hour alone, so all eligible gates open together at nightfall and
fade together over the sixteen turns after dawn - one shared counter, not one
per gate. The phase decides only *where* a gate leads, through the destination
rule below. An implementation that opens gates one at a time as their moon
waxes is modelling something the original does not do.

### 9.1 Gate-presence phase and how a gate is drawn

A moon-gate cell is **not** drawn as a plain tile most of the time. The renderer
special-cases live terrain byte `0xDC` against the shared gate-presence counter
introduced above, and the counter behaves as a sixteen-step position, not as a
mere on/off flag:

| Presence counter | What the cell draws as |
|---|---|
| `0` | Not a gate. The refresh has already restored the cell to terrain `5`. |
| `1..15` | A **composed transition frame**: the ground tile, with its bottom *N* pixel rows replaced by the top *N* pixel rows of the moon-gate tile. |
| `16` | The whole moon-gate tile `0xDC`, drawn through the ordinary tile path. |

Read as an animation, phase `N` is "the gate has risen *N* of sixteen pixel rows
out of the ground". Counting the phase up makes the gate rise; counting it down
makes it sink. Sixteen is the fully open gate and the only phase at which the
authored moon-gate artwork is shown intact.

Three properties follow, and all three are contract:

- **The composition is per-cell but the phase is global.** Every visible
  moon-gate cell is composed at the same phase, so a view containing more than
  one gate shows them rising and sinking in lockstep. There is no per-gate
  phase.
- **The ground half of the frame is scene-dependent.** In ordinary play the
  ground plate is terrain `5`, grass - the same tile the daytime pass restores.
  The endgame scene substitutes tile `0x44`, its throne-room floor, which is why
  the endgame's gate appears to rise out of flagstones rather than turf.
- **The composed frame is written into a dedicated scratch tile, id `0x116`.**
  That slot is saved and restored around every composition, so its shipped
  artwork survives; but an implementation must not treat `0x116` as a stable
  authored tile while a gate is on screen. The same id doubles as the
  party-vanishing sprite in Section 9.2.

**The exact tile inventory, and its boundary.** The whole effect uses **three**
tile ids and no others: the moon-gate tile `0xDC` as the thing that rises, one
ground tile (`5` in ordinary play, `0x44` in the endgame chamber) as what it
rises out of, and `0x116` as the scratch the composed frame is built in. The
composition reads exactly two source tiles and writes exactly one destination,
so this is a closed set rather than a summary of the ids that happen to appear.

Stating the boundary explicitly, because the neighbours are inviting:

| Nearby id | What it actually is | Not part of the gate effect because |
|---|---|---|
| `0xD8..0xDB` | The **fountain** family, a genuine four-frame animated family (`systems/animation.md` Section 6) | It is adjacent to `0xDC` and really does animate, which makes "the gate is the fifth frame of that band" an easy and wrong guess. `0xDC` is not in that family and has no selector. |
| `0xDD` | Not a gate frame | Nothing in the composition or the placement refresh references it. |
| `0xDE` | The **shrine flame** | A separate special tile with its own handler. |
| `0x114`, `0x115` | The **magic carpet**, two facings | Immediately below the scratch slot in the atlas; a transport sprite, unrelated. |
| `0x117` | A **ladder** | Immediately above the scratch slot; unrelated. |

There is no run of consecutive gate-frame ids anywhere in the atlas. If an
implementation finds itself wanting one, it has mistaken the draw-time
composition for authored art.

**The phase model is display-independent.** This is a checked result, not an
assumption from the EGA path. All four shipped display drivers implement the
composition, and all four agree on everything that is contract here: the same
sixteen phases, the same "phase `N` means `N` rows", the same three tile ids
(`0xDC`, the ground tile, and `0x116` as scratch), and the same scene-byte
choice between the two ground plates. They differ only in pixel encoding - the
two four-plane drivers move twice as many bytes per row as the two lower-depth
ones - and that difference cancels exactly, because both scale their row count
by the phase. An engine may therefore treat the sixteen-row rise as a property
of the game rather than of the EGA renderer, and `0x116` as the scratch id on
every display path.

**Lifetime of the presence counter: persistent, not turn-scoped and not
call-scoped.** There is exactly one such byte in the whole engine, it is
save-backed at `SAVED.GAM` offset `0x02E1`, and it survives turns, mode changes,
scene changes and save/load alike. Three consequences an implementation should
check itself against:

- Modelling it as a local, per-call value destroys the natural rise and sink
  outright, because the rise is spread across sixteen consecutive world turns.
- Modelling it as turn-scoped - reset or recomputed at each turn boundary -
  breaks save/load round-trip and loses the mid-rise state, so a game saved at
  20:07 reloads with a gate at the wrong height.
- Because it is shared, the blocking transit sequence in Section 9.2 leaves it
  at zero when it finishes. A gate that was mid-rise elsewhere in view is
  therefore driven to zero by an unrelated party's transit and rises again from
  zero on subsequent turns. That is the original's behaviour, not a defect to
  design around.

The counter is **not** a member of the global tile-animation families in
`systems/animation.md` Section 6. It is not advanced by the animation tick, it
has no frame selector, and skipping a rendered frame does not advance it.

Everything that touches it, in the whole engine:

| User | Access | Cadence |
|---|---|---|
| The natural-gate placement refresh, above | advances by one, up or down | once per world turn, every non-combat scene |
| The viewport tile-painting pass | reads it to choose each moon-gate cell's appearance | every compose, every scene including combat |
| The gate-transit sequence, Section 9.2 | sets it to fifteen, drives it to zero | once, blocking, per gate entered |
| The endgame gate ramps, `systems/endgame.md` | drives it one to sixteen, then fifteen to zero | twice during the closing rite |

**And, deliberately, what does not touch it.** The list above is a complete
census, established by scanning every shipped executable and overlay for
accesses to that byte - both direct accesses and sites that pass its address to
a helper - and then confirming each candidate against the surrounding code. It
found **fourteen sites in two files** and nothing else, so the following are
positive findings rather than inferences from silence:

| Does **not** touch the counter | Why an implementer might expect it to |
|---|---|
| The per-turn clock cleanup | It is the obvious home for a per-turn counter, and it does advance other timed state. The gate counter is advanced by the placement refresh instead. |
| Any combat routine, and the combat round loop | The tile-painting pass runs during combat and reads the counter there, which can look like combat ownership. It is not: combat neither reads nor writes it. |
| The global tile-animation pass | Gates are not one of its five families, so it has no selector for them and never advances this value. |
| Any spell, command handler, or NPC path | Nothing in the magic, command-dispatch or scheduler paths references it. |
| Every overlay except the endgame one | Twenty-one of the twenty-three overlays contain no reference at all. |

One negative is worth stating carefully, because the obvious phrasing is wrong.
**No code path writes this byte into the save image by name** - there is no
per-field save or load handler for it. It is nonetheless **fully persisted**,
because it lives inside the resident state region that the save is a bulk image
of (Section 5 of `formats/saved-gam.md`). "Nothing saves it" is therefore true
about *code* and false about *behaviour*, and an implementation that concludes
from the first that it may drop the value on save will be wrong.

An implementation should provide exactly one such value and exactly one
composition routine, and let those four callers share both; building the effect
separately for gates and for the endgame is duplicated work that will drift.

**How to falsify this section.** If your engine ends up with a second gate-phase
value, with a per-gate phase, with a phase that a combat round or the clock
cleanup advances, or with a phase that does not survive a save/load round trip,
then either your implementation or this section is wrong - and this section is
written so you can tell which.

### 9.2 The transit transition

The overworld command loop has a live-gate entry hook that runs before normal
input dispatch, on every iteration. It reads the party's current live terrain
cell and returns immediately unless that cell is `0xDC`. **That terrain test is
the only precondition.** Nothing about daylight, moon phase, party transport,
surface versus Underworld plane, or party composition gates it. It is confined
to the overworld only because it is the overworld loop that runs it; town,
dungeon and combat loops never do.

On `0xDC`, the hook runs a **blocking** transition to completion before the
party is relocated and before any key is read. It is not driven by the per-turn
tile animator and it cannot be skipped by the player - the abort poll that some
other presentation effects offer is disabled in overworld scenes. The whole
sequence plays at the **gate cell**, which is the party's own cell and therefore
the centre cell of the eleven-by-eleven view. **Nothing is played at the
destination cell**; the arrival is drawn by the next ordinary compose after the
warp.

The sequence, in order:

1. One world-tick pause, then a short PC-speaker sweep from the shared
   parameter-sweep sound helper - a swept tone, not a melodic cue. *Corrected:*
   an earlier revision named the shrine effect as another user of that same
   helper. **That comparison is withdrawn** - it rested on a mis-identified
   routine, and the effect it named does not use this helper at all. The
   verified other user of it is the Blackthorn pendulum-blade descent.
2. **Stage A, the party is swallowed.** The party sprite is switched to tile
   `0x116`, and the party's view cell is dissolved into the moon-gate tile
   pixel by pixel: the cell is first cleared to colour zero, then **255** of its
   256 pixels are plotted in a fixed pseudo-random order, one pixel per step.
   The count is 255, not 256 - the shuffle that orders the pixels never reaches
   one of them, so a single pixel of the cell is left at colour zero when the
   stage ends. It is repainted a moment later by step 4 and is not worth
   engineering around, but an implementation that plots all 256 and then wonders
   why its step count is off by one should know the original does not.
   The stage is paced by a world tick every eight steps rather than by a fixed
   wait, so it also advances ambient animation while it runs.
3. **Stage B, the gate closes.** The party sprite is suppressed entirely, and
   the shared presence counter is driven from `15` down to `1`, one phase per
   step, with a wait of **two BIOS timer ticks** between phases - roughly
   110 ms per phase at the standard 18.2 Hz tick, and about 1.65 seconds for the
   stage. Each phase draws the composed frame of Section 9.1 at the gate cell,
   so the visible effect is the gate sinking back into the ground with the party
   already gone. The countdown ends with the counter at zero.
4. The gate's live cell is rewritten to terrain `5`, the viewport is marked
   dirty, and the cell is repainted.

The frame counts are `15` for stage B and `256` dispatch steps for stage A; both
are exact, and neither is a duration an implementation may retune without
changing observable behaviour.

After the tile is cleared, the hook has two outcomes. If the clock is in hour
`0` and the minute is below `10`, it reports success to the outer loop; the
outer loop then dispatches the same shrine/urn kneel overlay used by
M-Meditate. Otherwise, the hook chooses a destination from the cached moon-glyph
digits: before noon it uses the first cached glyph, and from noon onward it
uses the second. The glyph digit selects one of the saved Moonstone slots, and
the hook calls the same saved-slot warp helper used by Gate Travel. If that
warp changes scene, the outer loop exits through the normal scene-byte check.
The party's transport marker is restored on every path that ran the transition.

The **endgame overlay reuses this presentation twice**, on the same shared
counter and with the same fifteen-step counts: once counting up, as a gate rises
in the throne room, and once counting down, as it sinks after the party has
passed through. The only differences are the substituted ground plate noted in
Section 9.1 and the pacing - the endgame spends a full world tick plus one BIOS
tick per phase where the transit spends a bare two ticks. An implementation
should build one phase-composition routine and let all three callers drive it.
See `systems/endgame.md`.

### 9.3 The Shrine of the Codex approach gate

The **Shrine of the Codex approach gate** is a separate fixed-coordinate
branch and has nothing to do with moongates. It fires from the post-action
special-tile pass after a consumed command has committed movement and the loop
has sampled the party's underfoot world tile. The branch is checked only while
still in overworld mode on the surface plane at the fixed world coordinate
`(233, 235)`, two cells south of the Shrine of the Codex tile at `(233, 233)`.
It prints the branch's opening narrative line, then reads the save-backed
ordained progress bitmask - not a Codex-read mask, a moon phase, or any
placement phase.

The polarity is: **a nonzero ordained mask grants passage**, printing the
seeker's welcome and leaving the party where they stand; **a clear mask refuses
it**, printing the two-line refusal and then pushing the party one cell south,
back the way they came. An earlier revision of this section had those two arms
swapped and is corrected here. Either way the loop continues through the
ordinary post-action cleanup.

This branch is a special world-transition case, not the saved-slot live-tile
refresh, not a Moonstone-slot Gate Travel cast, and not a moon-phase display
hook. It is also not a dungeon exit: no dungeon-side Codex branch exists.

The gates' destinations form Britannia's in-game fast travel at the player
manual level. Placement and waning of live terrain, the live `0xDC` entry hook,
and the saved-slot warp target are all specified from the saved Moonstone slots.
Do not infer natural-gate behavior from the Codex approach branch or from the
sky/status moon display alone, and do not reintroduce a render animator.

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

The party's transport state lives in the resident player record as an avatar/vehicle tile or transport marker. A separate neighbouring byte is the **timing/state tag**, which carries the timed magic effects `Q` (Quickness) and `T` (Negate Time) that modify the per-turn clock increment; no vehicle writes it. An earlier revision called that byte a "nearby scene/action tag" and let it stand for vehicle-specific timing; that label is withdrawn (Section 12, `systems/time.md` Section 4). The alternate-turn animation pendulum keys off the transport marker itself. The two bytes are related during movement, but they are not one byte and should not be collapsed into a single vehicle enum.

This section is the overworld summary. The command-level vehicle contract
for B-Board, X-Xit, ship broadsides, cannon fire, and vehicle object
persistence is centralized in `vehicles.md`.

The transport state covers the visible vehicle families:

- **On foot.** The default. Standard 2-minute outdoor turn.
- **Horse.** Mounted overland travel. It uses the standard 2-minute
  increment and the ordinary one-cell movement-command shape. The shared
  movement predicates provide the horse-specific terrain restrictions; no
  separate player rough-terrain stride table is part of the traced baseline.
- **Skiff.** Water-only transport at the standard outdoor turn cost. The time system's `Q` state-tag modifier, which halves the minute increment with a one-minute floor, is the Quickness magic effect and is not set by boarding a skiff; the earlier association of that timing with skiff/raft travel is withdrawn (`systems/time.md` Section 4).
- **Ship.** Water-bound but faster than skiff. Uses the standard outdoor turn
  cost when manually handled; with sails hoisted, `weather.md` owns the
  wind-cadenced movement and any wait passes before movement releases.
- **Magic carpet.** Boardable carpet transport at the standard outdoor turn cost. The `T` timing tag is Negate Time, not carpet identity, and no carpet path writes it; carpet travel is never minute-free.
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

- **`Q` tag.** The increment is halved (with a one-minute floor) before the cascade runs. This is the Quickness magic effect, not a skiff/raft timing contract; no vehicle sets it.
- **`T` tag.** The minute and light-counter writes are skipped for that cleanup call. Cleanup still recomputes daylight and can still mark visibility dirty. This is the Negate Time magic effect (`systems/magic.md`), not a scene/action tag and not any vehicle's identity; no vehicle path writes it, so carpet travel is never minute-free (Section 11).

The cleanup itself does the cascade — minutes to hours, hours to days, days to months, months to years. Shadowlord hideout maintenance runs at midnight, while character month counters and long-period flag clears run only when the day wraps past 28. On any hour change while the player is in a surface/town-family scene, the sky/status presentation row is refreshed; this is display work, not natural-moongate placement. The full cleanup contract is in `time.md`.

Two notable absences from the overworld's per-turn cleanup compared to town mode:

- **No NPC scheduler.** The schedule processor is not invoked from the overworld loop. NPC schedules are a town-mode-only concept.
- **No special "no-time" interactions.** Overworld turns either consume the standard increment or are no-ops at the dispatch level (the dispatcher returns 0 for actions that do not consume a turn, and the per-turn block skips the cleanup for those).

## 13. Hooks into other systems

**Visibility.** The producer reads the chunk buffer for terrain, the daylight value for ambient light, the player's torch / spell counters for personal light sources, and the local-light mask maintained by the visibility system. Dynamic actors affect the final viewport through the active-object compositor rather than a direct table scan inside the carve helper. Daylight on the surface follows the time system's day-night curve; on the underworld, the time system forces full-darkness regardless of hour. The overworld pre-loop underfoot probe can also force the cached lighting-threshold value to zero while the party is on the void tile (`0xFF`) without the Amulet of Lord British, which blacks out the whole viewport including the party's own cell and blocks the pending move; that tile id is distinct from the visibility system's own hidden-cell marker, which uses the same byte value inside the viewport scratch grid. See `systems/lighting.md` Section 7.

**Command dispatch.** The mode loop hands every printable letter to the resident command dispatcher (see `commands.md`). The dispatcher routes A-Attack and E-Enter to in-overlay handlers, X-Exit and B-Board to vehicle handlers documented in `vehicles.md`, K-Klimb to the outdoor mountain-climb handler, and the rest of the recognised alphabet to action overlays loaded on demand. `D` has no confirmed resident world-command handler and falls through to the stock refusal when it reaches the dispatcher.

**Active objects.** The overworld owns the player slot and a fixed quota of monster/vehicle/object slots. The per-turn animator, the random-encounter spawner, and the off-screen pruner all operate through the table. The combat framer save-and-restores the table around fights so the world resumes exactly as it was. Plane-swap (Z change) re-initialises the slots from the destination plane's seed `.OOL` file.

**Movement.** The shared movement spec owns direction-code routing,
the resident terrain-query layer, vehicle layering, dynamic occupancy, and commit
rules. This overworld spec owns the outdoor chunk buffer and the post-step
overworld effects that consume a successful movement.

**Time.** Per-turn cleanup runs once per consumed turn at increment 2; mode-zero recomputes run from the per-tick init at entry. Hour changes refresh the sky/status row through the time/status-panel path. Natural moongate live-terrain refresh and entry remain overworld-owned behavior, not a time-system or moon-display hook.

**Save / load.** The full state - party position, plane, active-object table, transport marker, timing/state tag - sits in the save-image region described in `save-load.md`. `SAVED.OOL` is the canonical per-plane object-overlay companion. The load path refreshes `BRIT.OOL` and `UNDER.OOL` from it so plane-entry paths can read the appropriate per-plane file; the save path stages *from* the per-plane files - it reads both of them into its staging halves, writes `UNDER.OOL` back out unless the save handler entered with disk-prompt mode already set to mode 1, never writes `BRIT.OOL`, and composes the canonical `SAVED.OOL` from those halves.

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

- **Plane-transition inventory.** *Closed.* Descent to the Underworld happens
  three ways: the fixed Britannia chasm at `(54, 138)`, whirlpool engagement
  while aboard a vessel (always landing at `(34, 18)`), and leaving a dungeon
  through the bottom of its lowest level. The return has no outdoor counterpart
  at all: a dungeon's top exit, a moongate or Gate Travel to a surface Moonstone
  slot, and a saved-position reload are the only ways up. The interior-exit
  branch that selects the Underworld belongs to one location, Ararat, which
  exists only underground. Section 2 carries the full list, and the plane byte's
  reuse as a building floor and a dungeon level is stated there as well.

- **Transport marker values and timing tags.** *Closed for the marker.* The
  complete persistent transport-marker value set and its facing rules are
  centralized in `vehicles.md` section 2; an exhaustive sweep of every shipped
  binary found no writer or reader outside it, so there are no opaque marker
  values left to preserve and there is no live balloon transport path.
  Separately, the time cleanup's `Q` and `T` tags are *closed too*: they are the
  Quickness and Negate Time codes of the shared timed-magic-effect byte
  (`systems/magic.md`), no vehicle path writes that byte, and neither tag is a
  vehicle identity or a vehicle-derived timing state.

- **Moongate entry path.** *Closed.* Placement is the once-per-turn live-terrain
  refresh over the eight saved Moonstone slots, gated on the hour alone with no
  moon-phase term; entry is the live `0xDC` shimmer hook, which consumes the
  cell and warps to the slot named by the current moon glyph. The former "render
  animator" is withdrawn: that scratch block is the night-time light beacon
  (`systems/visibility.md` Section 12.6). The Shrine of the Codex approach gate
  is a separate branch with its own corrected polarity.

- **Moongate presentation.** *Closed.* The presentation timing and asset naming
  that the previous entry left open are now specified: the sixteen-phase
  rise-and-sink render in Section 9.1, the persisted presence counter and its
  save offset, the scratch tile the composed frame occupies, the two-stage
  blocking transit in Section 9.2 with its exact step counts and its two-tick
  inter-phase wait, and the endgame's reuse of the same counter. The remaining
  gap is subjective: no recording of the accompanying PC-speaker sweep has been
  made, so this spec describes that cue only by generator and not by character.

- **Outdoor light sources.** After dark the outdoor map lights one rotating
  beacon from a lighthouse in the loaded window, and a location map lights up to
  two from bright-light fixtures. The beam geometry, cadence and reset rule are
  owned by `systems/visibility.md` Section 12.6; the four lighthouse coordinates
  are in `catalogs/gazetteer.md` Section 8.1.

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

- The overworld mode-loop main body — `u5-decomp/functions/MAINOUT_OVL/`.
- The shared per-turn party-capability check that precedes the overworld input
  block, its three-way result mapping, and the surface-only map-file prompt and
  active-object maintenance pass that precede the total-party-defeat sequence.
  Source provenance: derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_blackthorn-town.md`, section Q2.
- The pre-loop special-underfoot latch that forces zero light and gates outdoor
  movement commit — `u5-decomp/functions/MAINOUT_OVL/`.
- Local MAINOUT outer-loop analysis -- one-shot pending vehicle-acquisition
  active-object placement before normal outdoor input.
- The per-tick init that recomputes the scroll base and refreshes redraw flags — `u5-decomp/functions/MAINOUT_OVL/`.
- The per-turn epilogue that walks the active-object table, animates and prunes, and rolls the random-encounter trigger — `u5-decomp/functions/MAINOUT_OVL/`.
- The OUTSUBS overlay's collection of overworld helpers — `u5-decomp/functions/OUTSUBS_OVL/OVERVIEW.md` and the per-function notes in that directory covering water and chunk classification, chunk loading and scrolling, world filename selection, town-entry checks, the falls handler, per-plane actor setup, status checks, and the outdoor-camp Lord British service.
- The world-tile getter that reads from the chunk buffer with the four-quadrant 2-by-2 interpretation — `u5-decomp/functions/ULTIMA_EXE/`.
- The night-time rotating light beacon that owns the resident scratch block
  formerly attributed to a moongate animator, its inverted light gate, and its
  sixteen-bearing beam plate —
  `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: the withdrawal of the moongate animator, the hour-only
  placement schedule with no moon-phase term, the shipped Moonstone slot
  positions, the closed plane-transition inventory, the overloaded plane byte,
  Ararat's underworld-only exit, and the corrected Codex approach-gate polarity
  are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- The saved Moonstone slot scene/window test, natural live-gate tile refresh,
  saved-slot warp helper, and live moongate-tile shimmer/entry helper -
  `u5-decomp/functions/ULTIMA_EXE/`, and
  `u5-decomp/functions/ULTIMA_EXE/`, plus
  `u5-decomp/functions/ULTIMA_EXE/` (historical
  filename; note content now corrected).
- Source provenance: the sixteen-phase gate render and its composition rule,
  the persistence and save offset of the shared presence counter, the complete
  census of that counter's users, the two-stage blocking transit sequence with
  its exact step counts and inter-phase wait, the scratch tile the composed
  frame occupies, the scene-dependent ground plate, and the endgame's reuse of
  the same counter are derived from private analysis note
  `u5-decomp/notes/moongate_transition_2026-08-23.md`.
- The viewport rasterizer that resolves moon-gate cells against the presence
  counter — `u5-decomp/functions/ULTIMA_EXE/`
  (historical filename; the routine is the eleven-by-eleven rasterizer).
- Source provenance: the two-directional consumer census in Section 9.1 — both
  the four users and the explicit non-users — is a positive result, not an
  inference from silence. It comes from an exhaustive scan of all twenty-eight
  shipped executables, overlays and drivers for every access to the counter's
  byte, including sites that pass its address to a helper rather than touching
  it directly, with each candidate confirmed or excluded against the surrounding
  code. Fourteen genuine sites were found, in two files; one further textual
  match, in a third file, was confirmed to be an unrelated instruction and is
  excluded. Recorded in `u5-decomp/notes/moongate_transition_2026-08-23.md`.
- The location map setup that harvests up to two indoor light-source positions
  into the same beacon coordinate scratch — `u5-decomp/functions/TOWN_OVL/`.
- The combat loop exit reset of the light beacon's bearing byte —
  `u5-decomp/functions/COMBAT_OVL/`.
- The MAINOUT caller boundary for the live moongate-tile shimmer helper, as
  captured in `u5-decomp/functions/MAINOUT_OVL/`.
- The render-loop orchestrator — `u5-decomp/functions/ULTIMA_EXE/`.
- The visibility producer that produces the 11-by-11 viewport scratch grid — `u5-decomp/functions/ULTIMA_EXE/`.
- The per-turn cleanup that advances time, refreshes daylight, and dispatches the hour-change hook — `u5-decomp/functions/ULTIMA_EXE/`.
- The on-disk format of the surface and underworld grids — `u5-decomp/formats/maps.md`.
- The data-segment layout, including the shared scratch block read by the light beacon, the single Britannia chunk-index table, and the `WorldLocationTable` — `u5-decomp/formats/data-ovl.md`.
- Public scene/name binding for town-mode location rows — `catalogs/gazetteer.md`,
  `formats/npc.md`, and `formats/data-ovl.md`.
- Public dungeon scene/name/record binding — `systems/dungeon-mode.md`,
  `formats/dungeon-dat.md`, and the MAINOUT E-Enter helper re-derived from
  the private analysis workspace.
- Source provenance: the creature step planner's absence of any distance
  comparison, the coin flip's role as attempt ordering only, and the
  single-attempt random-wander fallback are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_npc-walkers.md`, cross-checked
  against `u5-decomp/notes/outdoor_npc_scheduling.md`.
- Source provenance: the two outdoor ranged attacks, their trigger conditions,
  the shared traced-line resolution with the launch-cell exemption, the
  announcement assignment, and the per-sample effect figures were first derived
  from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_npc-walkers.md`, cross-checked against
  `u5-decomp/functions/COMSUBS_OVL/`. Earlier readings that treated the shared
  helper as a directed-step probe or a path-clear scan are superseded.
- Source provenance for Section 6.2 as it now stands: the exact-equality breath
  recognition, the adjacency-before-class ordering, the inclusive range draw and
  the exact one-in-eight, the sub-tile line generation with its column-driven
  accumulator, the fixed sampling interval and the untested last sample, the
  viewport-grid obstruction test and its passable/blocking split, the
  direction-dependence result and the axis-aligned player shot that hides it,
  and the two-stage damage payload with its frigate hull branch and whole-party
  pass, were **re-derived from the shipped binaries** in a verification pass
  that did not consult the earlier notes for any claim. Routine boundaries were
  read from entry to exit and the caller censuses were exhaustive near-call
  scans; the limits of both are published in Section 6.2.5 rather than left
  implicit. Working directories: `u5-decomp/functions/MAINOUT_OVL/`,
  `u5-decomp/functions/COMSUBS_OVL/`, `u5-decomp/functions/OUTSUBS_OVL/`,
  `u5-decomp/functions/CMDS_OVL/` and `u5-decomp/functions/ULTIMA_EXE/`. Record
  field positions are cited from `formats/saved-gam.md`, not from private notes.
  Private notes in those directories that describe the line generator as a
  classical eight-connected line-drawing routine, or that name the sand-trap
  adjacency family after the sea serpent, are contradicted by this pass and
  should be corrected on the private side.

- The overworld's pre-dispatch control-code table, its four shared Control
  bindings, the synthetic table slot, the under-sail input substitution, and the
  loop's boolean reading of the command status. Source provenance: derived from
  private analysis note
  `../u5-decomp/notes/oq-closures_2026-08-22_commands-dispatch.md`.
