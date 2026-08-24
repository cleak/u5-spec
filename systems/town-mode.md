# Town mode

## 1. Overview

When the player steps onto an enclosed cell of the overworld — a town gate, a castle drawbridge, the entrance to a keep, the threshold of a dwelling — the engine pauses the overworld, swaps the active map for a thirty-two-by-thirty-two interior grid, loads the location's roster of named NPCs along with their daily routines, and hands control to the town-mode turn loop. The player walks among schedule-driven NPCs, talks to them, opens doors, climbs ladders to upper floors, takes things from chests, encounters castle services and story-critical set pieces, and eventually walks back across the boundary to leave. Town mode is where most of the game's storytelling happens.

Town mode shares almost everything with overworld mode — the per-letter command dispatcher, the input pipeline, the active-object table for sprites, the renderer, the time clock — and adds three things on top: a different map, a population (the NPC roster and scheduler), and a per-turn invocation of the schedule processor that keeps NPCs walking on their daily routines while the player takes their own turn. The baker is at the bakery in the morning, the guards stand at the city gates during the day and head to the barracks at night, the farmer goes home for dinner.

Shared terrain passability, dynamic occupancy, and movement commit rules are
specified in `systems/movement.md`. This town-mode spec owns the location floor
buffer, NPC scheduler integration, dawn/dusk rewrites, boundary exits, and
town-specific command hooks around that shared movement layer.

One set of code, one set of file formats, one tile encoding, and one schedule format serve four superficially different location classes — towns, dwellings, castles, and keeps. The differences are entirely encoded in data: a castle can have throne rooms, guards, healers, or other special residents; a keep is barracked and patrolled; a dwelling is a single small house with a few NPCs; a town is everything between. From the engine's perspective they are identical.

This spec describes how town mode is entered, how the location's map and NPCs are loaded, how the per-turn loop dispatches commands and runs the scheduler, how the player is represented while in a location, how multi-floor locations are navigated, what the special interactions do at the town-mode level, and how the player exits.

## 2. The four location classes and the scene byte

The world has thirty-two named non-overworld locations divided evenly into four classes — towns, dwellings, castles, and keeps — eight per class. Every named location has a unique *scene byte* in the range one through thirty-two. The class is selected by the high bits of the scene byte and the index within the class by the low bits, so that:

| Scene byte range | Class    |
|------------------|----------|
| 1–8              | Town     |
| 9–16             | Dwelling |
| 17–24            | Castle   |
| 25–32            | Keep     |

The engine tracks the active scene in a single resident byte. Zero means "overworld"; values one through thirty-two put the engine in town mode for one named location; values outside that range do not select a town-family location. Walking onto an enclosed cell sets the scene byte; stepping off the edge of the interior grid and confirming the leave prompt clears it.

Per-location data lives in four parallel families of files — one tile-grid file per class, one NPC roster file per class, one dialogue file per class. The roster and dialogue files use the per-class location index directly. The tile-grid file does **not**: its unit is the 1,024-byte floor page, and which pages belong to a location comes from the resident per-scene base-page table published in `formats/location-dat.md` Section 4.1, not from the location index. The engine resolves the file family from `(scene - 1) >> 3` against a four-entry pointer table.

## 3. Per-location map data

A location's map is a thirty-two-by-thirty-two grid of one-byte tile indices, totalling 1,024 bytes per floor. Each per-class file is a flat array of sixteen such floor pages numbered `0..15`. Runtime floor selection reads the scene's **base page** from a resident per-scene table and adds the signed floor byte to it: floor `0` is the base page, floor `+1` the page after it, floor `0xFF` the page before it. The loaded page is at file offset `page × 1024` and exactly 1,024 bytes are read.

`formats/location-dat.md` Section 4.1 publishes the complete table — base page, page run, and floor range for all thirty-two locations. Two things about it matter to town mode:

- **The base page is not the location index doubled.** For twenty of the thirty-two locations it is something else, so an engine that derives pages as `location_index × 2 + floor` renders the wrong room in most locations. Iolo's Hut, for example, is page 12 of `DWELLING.DAT`, not page 8.
- **A higher page index is a higher floor.** Floor `+1` is one storey up and floor `−1` is a basement. Four locations — Yew, both large castles, and Serpent's Hold — enter above the bottom of their page run and therefore use negative floor values in ordinary play.

Locations have between one and five floors. Thirteen have exactly one, and in those the floor byte never leaves zero because the page contains no transition cell at all.

The active floor is loaded into a single 32×32 byte buffer in the resident data segment. Cell `(row, col)` is at buffer offset `row × 32 + col`; row indices increase southward, column indices increase eastward. The renderer reads this buffer for the static terrain layer; the active-object table (described in the active-objects spec) layers sprites on top.

The on-disk tile bytes are *terrain plus markers*. Most cells contain a tile ID — wall, floor, grass, water, door, chair, ladder — that the renderer paints directly. A handful of special tile values are *markers* that the location-load pipeline and NPC scheduler harvest, rewrite, or consume:

- **NPC start markers** (`0x48` or `0x49`) record where each rostered NPC begins. The location-load pass walks the grid, finds these markers, and records each marker's coordinates and exact marker byte.
- **Spawn markers** (the literal asterisk character byte) record one or two map-entry coordinates. The first asterisk encountered is the *primary* spawn (typically the entrance from the overworld); the second is the *secondary* (typically an alternate exit or a stairway-up landing). What the engine does when a page carries no asterisk is an open item: earlier wording here named a per-scene default coordinate, and that rule is retracted — it belongs to the resident-Shadowlord install pass, not to player placement. See `formats/location-dat.md` Section 6.
- **Farmland and orchard terrain** (the standing-crop and fruit-tree tile values) is not marker data at all, but in a settlement that is currently hiding a Shadowlord it is rewritten in place by a blight pass at the end of the map load. In every other settlement that pass does nothing. See the Shadowlord blight below.
- **NPC floor-link markers** (`0xC8` and `0xC9`) are consumed by the NPC scheduler's tile-ID pathfinder after map load. They must remain distinguishable in the live tile buffer for the schedule processor.

Marker processing is in-memory only: the on-disk `.DAT` floor is unchanged. By the time normal play begins, runtime passes have harvested the markers needed for spawn/NPC state and may have rewritten selected marker cells, while visible actors are represented through the dynamic sprite layer. Some markers, notably the `0xC8`/`0xC9` floor-link pair, remain meaningful to runtime consumers after the initial load pass.

### Shadowlord blight on farmland and orchards

A second-tier pass walks the whole live floor buffer and thins out farmland and
orchards. It is not an NPC waypoint load, it is not path or grass texturing,
and it is not an unconditional harvest. The pass first reads the entry-time
record of *which Shadowlord is resident in the location being entered* (Section
13) and returns immediately when that record says "none". In an ordinary
settlement — any location that is not currently one of the three Shadowlord
hideouts, and any hideout whose Shadowlord has already been vanquished — the
pass does nothing at all and the authored farmland is drawn exactly as shipped.
The row-`4` guard of Section 5 suppresses the blight for the same reason it
suppresses the install: with no host recorded there is nothing for the pass to
act on.

The shipped location files store every farm cell as standing crops and every
orchard cell as a fruit tree. Where the pass does run, it knocks most of them
down to their spoiled counterparts:

| Authored terrain | Becomes | Chance |
|---|---|---|
| Standing crops | Plowed patch | Seven times in eight |
| Fruit tree | Hollow stump | Seven times in eight |

So in the settlement hosting the Shadowlord roughly one farm cell in eight is
still bearing and roughly one orchard cell in eight still has its tree, while
every other settlement keeps all of them. The in-game look-at descriptions name
all four tiles, so this is a visible world-state statement — the ground around
a hiding Shadowlord reads as blighted — and not a texture flourish. Nothing is
written back to the location file; the rewrite is confined to the live floor
buffer.

Two places invoke the pass, and the resident-host test applies at both:

- **The end of every floor load**, after marker harvest and the dawn/dusk
  substitution. On a fresh town entry this invocation does nothing, because the
  entry sequence clears the resident-host record immediately before the map
  load and only re-derives it afterwards. On an in-town floor change — a
  stairway or ladder between the location's own floors — the record is still
  standing, so each newly loaded floor of a hideout town is blighted as it
  arrives.
- **The first step of the Shadowlord install** (Section 13), which runs after
  the host has been recorded and *before* the install's one-at-a-time reject.
  A hideout town whose install is cancelled because a Shadowlord summoned
  elsewhere is still standing in the active-object table is therefore blighted
  anyway.

One consequence of that pairing is worth naming rather than inheriting by
accident: the in-town floor reload that follows an NPC death does not clear the
host record and then re-runs the install, so on that path a hideout town's
floor gets the pass twice in a row. The second run can only touch cells that
survived the first, so the standing fraction after it is smaller than a single
seven-in-eight rule predicts.

The pass runs on a deterministic stream: immediately before the walk the
gameplay PRNG is seeded from the **calendar day of the month**, and immediately
after the walk it is re-seeded from the host clock. Two consequences follow.
First, the result is a pure function of the day byte and the floor content, so
every load of a given floor on the same in-game day produces the same pattern,
and the pattern re-rolls when the date advances — "which crops and trees are
still standing" is a stable, date-keyed property of the hosting town. (The
hideouts themselves are re-rolled at the midnight day rollover described in
`catalogs/quest-graph.md`, so which town is blighted and how it is blighted
change together.) Second, the bracketing is **not** a save-and-restore of the
PRNG: the pass discards whatever generator state was running and leaves fresh
clock entropy behind it. See `systems/prng.md` section 3.

### Floor transitions

Five authored cell families change the floor while the party is inside a location. All five are ordinary tile bytes in the location grid; there is no separate per-location transition record and no hidden-floor feature.

| Cell | Name | How it fires | Result |
|---|---|---|---|
| `0xC4..0xC7` | Staircase | Walking onto the cell | Floor `±1`, direction from the approach |
| `0xC8` | Ascend ladder | The K-Klimb command, while standing on it | Floor `+1`, prints `Up!` |
| `0xC9` | Descend ladder | The K-Klimb command, while standing on it | Floor `−1`, prints `Down!` |
| `0x86` | Metal grate | The K-Klimb command, while standing on it | Floor `−1`, prints `Down!` |
| `0x8C` | Trapdoor | Stepping onto the cell | Prints `A TRAPDOOR!`, then floor `−1` |

**Staircases.** The staircase byte encodes an axis in its low two bits, in the same normalized facing space the town movement wrapper uses. Entering the cell moving along that axis in the authored direction ascends; entering it from the opposite side descends; entering it from a perpendicular side does nothing at all. The same staircase byte is authored at the same cell coordinate on both connected pages, so a flight is two-way and the party arrives standing on its far end.

**K-Klimb inside a location.** The handler echoes the verb prefix `Klimb-`, then:

1. If the party is mounted on a horse it prints `-On foot!`, changes nothing, and costs no turn.
2. Otherwise it reads the cell under the party. An ascend ladder goes up; a descend ladder or a metal grate goes down. There is no two-way ladder cell in town mode — the two ladder ids are directional and a given cell is one or the other.
3. If the cell under the party is none of those, the command instead prompts for a direction and looks at the adjacent cell. Three ids are accepted: the pile of rocks `0x4C` and the two wooden-fence ids `0xCA`/`0xCB`. Any of them moves the party one cell onto that neighbour; this is climbing *over* something and **does not change the floor**. (Corrected 2026-08-22: this list was previously described as "a wooden fence or gate cell" — there is no gate id on this path, and the rubble id `0x4C` was missing.) Anything else prints `What?` and costs no turn. A cancelled direction prompt still counts as the party's action.

**Trapdoors.** Stepping onto a trapdoor cell announces `A TRAPDOOR!` and drops the party one floor. It is an underfoot reaction in the per-turn tile-effect pass, not a command. It is suppressed entirely while the party is on the magic carpet, which floats over the cell. Lord Blackthorn's Castle is built around this: its entry floor and the three floors above it carry forty-five, thirty-six, thirty, and thirty-six trapdoor cells respectively. Its basement carries none, so the bottom of the tower is where falling stops.

**One location overrides the trapdoor.** Stonegate is a single-floor keep whose trapdoor cells form a ring around one open centre cell. Walking into that ring does not descend; it runs a scripted sequence — a tone-and-fade presentation, the visible map replaced wholesale with a single tile, the active-object table cleared, and every party member's status set to dead. This is the *only* place a trapdoor is not a floor transition; every other trapdoor in the game takes the generic descend path above. Specify it as a scripted location event, not as part of floor selection.

**Every floor change is a full reload.** A transition re-runs the whole location load against the new page: read the page, harvest NPC start markers and the beacon's light sources (Section 5 step 3 - **not** spawn markers), run the dawn/dusk substitution if the hour is in the night band, run the Shadowlord blight pass, relink the active-object table for the new floor, and mark visibility dirty. It is never a partial update, and the announcement (`Up!` / `Down!`) is printed before the reload.

**A floor change preserves the party's column and row.** Only the floor index
changes - incremented or decremented by the stairway handler - and the new
floor's page is loaded in place. The party lands on the *corresponding cell* of
the new page. The entry cell is **not** recomputed on a floor change; it applies
only to entry from the overworld.

A separate path within the Klimb command moves the party one cell in its facing
when climbing a fence or wall tile. That is a move within a floor, not a page
change, and it does not interact with the rule above.

### The floor byte has two roles

The floor byte is interpreted as signed eight-bit for map loading. Values `0..127` are non-negative floors; values `128..255` are negative offsets from the base page. This lets a location place its entry floor in the middle of its authored pages and reach a basement with `0xFF`, while still using the same 32×32 tile encoding for every floor.

That is its role *while the scene byte names a location*. The moment the party leaves and the scene byte returns to the overworld value, the same saved field becomes the **world plane selector**: zero is Britannia and the all-ones byte is the Underworld. The town exit path writes it accordingly, and exactly one location — Ararat, which exists only underground — exits to the Underworld; every other location exits to Britannia (`systems/doors-and-z-transitions.md` Section 12, `systems/overworld.md` Section 2).

An engine must keep the two roles distinct in its own reasoning even though the original keeps them in one byte. In particular, "floor `−1`" inside a keep and "the Underworld" outside one are the same stored value meaning two unrelated things, and a floor-change handler must never run against an overworld scene byte.

## 4. Per-location NPC and dialogue data

Each named location carries a roster of up to thirty-one NPCs (slot zero is a sentinel). The roster lives in the per-class `.NPC` file, one 576-byte block per location, holding three parallel sub-blocks: a sixteen-byte schedule per slot, a one-byte type per slot, and a one-byte dialogue index per slot. Empty slots (zero type byte) are skipped at runtime. The schedule encoding and the per-tick walker are described in the NPC schedules spec.

Town entry applies an additional per-scene removal mask before a rostered NPC
becomes active. The mask holds one bit per NPC roster slot per town-mode
location, and a set bit means "this slot is permanently gone from this location;
do not place it". It is read once per slot on entry and it is durable: it lives
in the save image (`formats/saved-gam.md` section 9.2), nothing clears it on
scene exit or reload, and a new game starts with every bit clear. This is not
the same table as the hidden-NPC visual mask used by the schedule system when
allocating an already-active NPC's sprite: the removal mask controls whether a
slot enters the scheduler at all, while the hidden mask only changes the tile
used for the linked sprite.

**Which removals are recorded.** The write path filters on the NPC's sprite
class, and the filter is narrow:

| Sprite class group | Recorded as permanently gone? |
|---|---|
| The human/townsperson sprite classes (everything below the creature range) | Yes, with one exception below |
| The guard sprite group | **No** |
| Every creature sprite class | **No** |
| The royal-regalia sprite group (shard, crown, sceptre, amulet) | Yes |

So killing a townsperson or a named character is permanent: that slot is never
placed again in that location. Killing a guard or a monster is not recorded at
all, and those slots are placed again on the very next entry — which is why a
town's guard population regenerates however many the player cuts down.

Two removals bypass the sprite-class filter and are written directly against a
fixed location and slot:

- Vanquishing a Shadowlord marks that Shadowlord's roster slot in Stonegate as
  removed. A Shadowlord's sprite class is a creature class and would otherwise
  be rejected by the filter.
- Picking up the sandalwood box marks the box's roster slot in Lord British's
  Castle as removed. That pickup lives in a different overlay from the shared
  removal helper.

Both are ordinary entries in the same mask; neither is a separate quest field.

Dialogue lives in the per-class `.TLK` file, indexed by the per-NPC dialogue index. The dialogue engine, described in its own spec, is invoked when the player initiates a conversation (Section 9).

Town mode's contract with the schedule system is one call per consumed turn: each turn-taking action calls the per-tick walker once, with the current hour byte. The walker iterates all thirty-one NPC slots and advances each NPC's state machine. Town mode reads the walker's "any NPC moved" scratch flag to decide whether the screen needs a repaint.

## 5. Entry: map load, NPC load, Shadowlord install

Entering a town is a single setup pass that runs once per entry, before the per-turn loop starts spinning. Six things happen, in order:

1. **State reset.** Active-object slots one through thirty-one are freed (type byte cleared); slot zero is left for the player. The "town entered" flag and visibility-dirty flag are set; transient frame-scoped flags are cleared.

2. **Tile-grid load.** The per-location floor page is loaded into the tile buffer (Section 3). Exactly 1,024 bytes — one floor of 32×32 — are read.

3. **Marker harvest.** The load pass walks the freshly-read tile grid
   cell-by-cell in a single walk that serves two purposes: it finds **NPC start
   markers** and records their coordinates for placement, and it finds the
   **night beacon's indoor light sources** and records theirs. *Corrected:* an
   earlier revision called the second kind "asterisk spawn markers" recording
   primary and secondary player-entry coordinates. **That reading is withdrawn**
   - see `formats/location-dat.md` Section 6. Those two slots belong to the
   beacon specified in `systems/visibility.md` Section 12.6, they hold light
   sources rather than player positions, and the byte occurs on no town, castle
   or keep floor at all.

4. **Dawn/dusk substitution.** The shipped maps store gate cells in their daytime, open form. When the current hour is in the night band (8 PM through 4 AM), a pass runs over the tile buffer and toggles the cell paired with each archway marker into its night, closed form. Section 6 describes the substitution in detail.

5. **NPC roster load.** For each occupied NPC slot in the location's `.NPC` block, the schedule and type are loaded into the resident schedule and type tables, the dialogue index is unpacked into the per-NPC runtime block, and the NPC's runtime state is initialised by sampling the schedule for the current hour. NPCs whose initial waypoint floor matches the current floor are linked into the active-object table; off-floor NPCs exist only in the schedule tables.

6. **Shadowlord install.** The last step of the pass compares the town's scene
   byte against the three Shadowlord hideout slots and, on a match, installs a
   live Shadowlord actor in the town. In a town that hosts no Shadowlord — the
   ordinary case — this step does nothing at all. Section 13 gives the guard,
   the one-at-a-time reject, the actor-index choice, and the placement. The
   player is present in this mode as slot zero of the active-object table, kept
   in step with the world-state globals by the compositor; the entry pass does
   not write a player entry anywhere else. *Corrected:* an earlier revision added that command
   handlers may use "asterisk spawn marker" slots for stair or alternate
   landing paths. **Withdrawn** - those slots are the beacon's light sources,
   not landing points, and no town floor carries the byte.

   **Retraction, and an open item.** This step was previously called "player
   attach" and was said to give the player a phantom NPC entry — a high-indexed
   NPC slot with a stationary three-identical-waypoint schedule — spawned at
   `(15, per-scene row, 0)`. All of that is withdrawn. Every detail came from
   the helper that installs a resident **Shadowlord**, which runs only when one
   of the three Shadowlord hideout slots equals the town being entered, takes
   its record from the ordinary monster-slot allocator (which never returns
   slot zero), and stamps the Shadow Lord actor tile. Section 13 now owns those
   coordinates, and Section 8 records the withdrawal of the phantom NPC itself.
   **The entry cell is now established.** On entering a town, castle, keep or
   dwelling from the overworld, the party is placed at **column 15, row 30, on
   floor 0**. Three fixed values, written by the overworld *Enter* path before
   the mode switch, for every such location.

   It does **not** depend on the location, on the direction of approach, or on
   the party's overworld position beyond identifying which location was
   entered. There is no table lookup and no per-scene variation. The town entry
   setup and the map loader write nothing to the party's column or row - what
   town mode starts with is exactly what the overworld path wrote.

   **The maps are authored around it.** Reading that cell on the floor-0 page of
   all thirty-two locations, using this specification's own published base-page
   table and the shipped map files, gives walkable ground in every one -
   cobble, grass, road or parched desert. Most locations lay a paved approach
   at columns 14 to 16 running up from the map's bottom edge.

   *On the earlier confusion:* the withdrawn wording gave "(column 15, a
   per-scene row, floor 0)" and the withdrawal was correct - those were the
   **Shadowlord install** helper's coordinates, written into a mob record rather
   than into the party position, with a per-scene row from a table. **Both
   fifteens are real.** They are unrelated writes to different storage that
   agree, which stands the Shadowlord in the entrance column. An implementation
   should keep the column, add the row and floor beside it, and source all three
   to the overworld entry path rather than to the Shadowlord helper.

After these six steps return, the entry pass calls a final screen redraw and hands off to the per-turn loop. The player is in town mode until the loop's per-turn epilogue notices that the scene byte has been cleared (Section 15).

A *preserving re-entry* runs the same pass with the setup argument clear. In
that mode the active-object table tail is not zero-cleared, so a Shadowlord
already standing in the table survives the re-entry and, by the one-at-a-time
reject of Section 13, suppresses a second install. Preserving re-entry is used when the top-level dispatcher is already in
a town-family scene and is re-running setup without having just returned from
the overworld or the dungeon wrapper.

Fresh entry paths pass the nonzero setup argument. This path clears active
object slots one through thirty-one, resets the town-entry scratch flags, runs
the entry-time service hooks, and then proceeds through the same map load,
Shadowlord install, NPC setup, and presentation sequence. The traced fresh-entry
callers are the main loop after an overworld-to-town scene change, the main
loop after a dungeon-wrapper return that leaves a town-family scene active, and
the resident NPC-location warp helper when it changes from one town-family
scene to another. The direct save/load or already-in-town dispatch path reaches
town setup with the preserving argument.

One traced coordinate edge suppresses the Shadowlord install outright. When the
town arrest sequence accepts surrender, it sends the party to Yew jail at local
position `(25, 4, 0)` and advances time until 08:00. On the following
town-entry setup, a party Y coordinate of exactly `4` skips the hideout
comparison entirely, and because the host selector is reset to its no-host
marker immediately before that test, the install then returns having done
nothing — the skip is unconditional, not contingent on any other state. A town
entered on that row therefore never receives its resident Shadowlord and never
runs the associated NPC sweep (Section 13). This is a coordinate test, not a
jail test: any entry with the party on row `4` behaves the same way. Do not
generalize it into an ordinary re-entry rule, and do not read it as a
player-placement rule — the retraction in Section 5 step 6 applies.

**Retraction.** This paragraph previously described the same edge as a bypass
of a "phantom-player attachment path", with the helper skipping a
permanent-location queue lookup and returning before allocating a phantom NPC
"if no active player queue entry is already selected". Both halves are
withdrawn: the helper is the Shadowlord install, and the trailing condition
does not exist.

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
2. **Pre-dispatch checks.** A short setup step handles meta-states (combat in progress, turn already in flight) and the cursed-by-spell timer. If the scene byte has been cleared during the previous turn — meaning the player just stepped off the edge of the interior grid and confirmed the leave prompt — the loop breaks out (Section 15).
3. **Dispatch.** Movement commands use a small direction dispatch table; letter commands flow into the shared per-letter dispatcher described in the commands spec. Many handlers live in the town-mode overlay (Attack, Klimb); others are shared across modes (Cast, Get, Look, Talk, Use) and resolve to the appropriate cross-mode handler after a scene-byte check.
4. **Per-turn epilogue.** When the dispatcher returns and the action consumed a turn, the loop snapshots the current hour, advances the time clock by one minute via the time spec's per-turn cleanup, runs the dawn/dusk gate pass if the new hour is `5` or `20`, runs the underfoot-effect handler described in Section 10, ticks down the curse/buff counter, and copies the party's current map coordinates into slot zero. It then normally calls the NPC schedule processor with the current hour byte. The sole exception is the explicit-T arrest-cleanup result: the clock and earlier underfoot/status work still run, but the schedule processor is skipped before arrest cleanup. The underfoot-effect handler is called on every consumed turn and it re-reads the tile the party is standing on, so it is not gated on the party having moved; its last act is to run the shared party status/provision pass specified in `systems/time.md`.
5. **Render.** If the schedule processor reported any NPC moved, or the visibility-dirty flag is set, a full render runs. Otherwise the screen is left as-is and the loop reads the next command.

Ahead of step one, each iteration runs the shared party-capability check that all three exploration modes use, described in `systems/main-loop.md` Section 6: if nobody in the party can act but somebody is asleep, the loop prints the sleep line and passes the turn without reading a command; if nobody can act and nobody is asleep, it runs the total-party-defeat sequence of `systems/blackthorn.md` Section 7 instead. Town mode adds no condition of its own to that check.

The dispatcher's return code decides when to skip parts of the epilogue: actions that take no turn (a cancelled command, a "What?" fallthrough, the buffer-toggle key) skip both the time advance and the schedule tick. Actions that consume more than one turn advance the clock once per inner action.

Town is the only mode that reads the dispatcher's status as more than a boolean.
Its four-way test is specified in `commands.md` Section 3: the arrest-cleanup
result runs the common clock/underfoot epilogue, skips the NPC schedule
processor, and fires town post-action cleanup with the arrest discriminator;
the "re-prompt" result returns straight to the input parser with no turn and no
epilogue at all. Each special result has exactly one producer: failed explicit
Talk against the reserved Blackthorn guard demand for the former, and the
harpsichord digit handler below for the latter.

### 7.1 Drunkenness

Town mode has one pre-dispatch stage no other mode has. Over-drinking at a
tavern arms a counter at twenty-five; while that counter is non-zero, every
command the player enters is subject to an even-odds scramble. When the scramble
fires, the engine discards the entered command and substitutes a random cardinal
step, prints the short hiccup line, runs the same one-shot schedule-rewrite
sweep over the NPC roster that Section 14 describes, and decrements the
counter by one; when it does not fire, the entered command runs normally and the
counter is untouched. The counter therefore drains only on scrambled commands,
not on every turn. Entering a town clears it outright, so the effect never
survives leaving and re-entering a location, and the tavern branch that arms it
is the only producer anywhere in the game. `systems/shops.md` owns the tavern
prompt that arms it.

### 7.2 Digits

Digits in town go to one handler with two behaviours. Seated at the harpsichord
in Lord British's castle, each digit plays a note and the handler reports the
town-only "re-prompt without advancing the world" status — the sole producer of
that status anywhere in the game, and the reason a player can key in a tune
without burning world turns or letting the NPC schedule run. Section 13 owns the
instrument's full contract. Anywhere else the same handler falls through to the
ordinary solo-member selector, which reports "acted" for an ordinary selection
and "no action" for the deselect-to-whole-party case.

Cardinal movement in town is a mode-owned wrapper around the shared movement layer. It computes a bounded destination in the current 32-by-32 floor, prints the direction phrase, optionally prefixes it with the active vehicle verb ("Ride", "Row", or "Fly"), samples the target terrain, and asks the shared passability classifier with the current transport marker. A rejected destination prints the standard blocked feedback and leaves the avatar in place.

Successful movement commits the avatar coordinate, marks the view dirty, and then runs immediate tile effects. Leaving a town-family location is a **map-boundary event, not a tile effect**: the handler raises the leave prompt when the requested step would carry the party off the thirty-two-by-thirty-two floor grid — that is, when the party is standing on the outermost row or column and steps outward. The ordinary passability and occupancy tests run first and still win, so a destination the classifier rejects prints the blocked feedback instead of prompting. Accepting the prompt clears the scene byte and maps the interior exit back to the location's overworld coordinate. Town stair tiles are the `0xC4..0xC7` family. Their low two bits are compared with the movement wrapper's normalized facing code: matching the movement code moves up one floor, matching that code's opposite-facing value moves down one floor, and crossing the stair from either side is just a normal walk. Floor changes reload the active floor and rerun the load-time passes for that floor.

The schedule tick is unconditional on consumed turns — every action that costs a turn advances NPCs by one tick — so an NPC walks at most one cell per player action.

The Hole-up command (Section 12) is the one path that bypasses this cadence. It
runs the schedule walker directly inside the rest handler while the requested
hours are simulated. In the traced town-hours path, each requested rest hour can
run up to sixteen walker/world-tick passes, so NPCs can move substantially more
than once per requested hour if the rest is not interrupted.

## 8. The player in town mode: one representation, not two

Town mode keeps exactly one view of the player: slot zero of the active-object
table — the avatar sprite — owned by every world-mode renderer and refreshed
each turn from the world-state globals, which remain the authoritative source
for the party's position and floor. The player has no entry in the NPC type
array, no per-NPC runtime descriptor, and no schedule.

**Retraction — the phantom NPC is withdrawn.** Earlier revisions of this
section described a second representation: a *phantom NPC* at the high end of
the NPC slot table, with a stationary three-waypoint schedule and a
player-sentinel type byte, allocated on town entry, short-circuited on
re-entry, and freed on exit. That contract is withdrawn in full, not merely
narrowed to "details unestablished". Its sole traced source was the town-entry
helper re-derived in Section 13: the helper installs a resident **Shadowlord**,
runs only in a town whose scene byte matches one of the three hideout slots,
and stamps the Shadow Lord actor tile — the value formerly read as a player
sentinel — into both the active-object record and the NPC type byte. The
apparent "an existing phantom is found, so skip allocation" short-circuit is
that install's one-at-a-time reject against an already-standing Shadowlord.
Nothing in the traced entry path writes a player entry into the NPC tables, so
the phantom's existence, purpose, slot index, spawn cell and waypoints are all
withdrawn together. `formats/npc.md` Section 6 and `systems/active-objects.md`
Section 5 carry the same retraction; `catalogs/npc-roster.md` no longer lists a
player-mirror tag.

**What an implementation still needs.** The concern the phantom was invented to
explain — that NPCs must not walk through the player — is met without it, and
that mechanism is independently traced. The NPC pathfinding workspace marks
nearby occupied active-object cells as dynamic obstacles and then separately
marks the player's *current* cell, so NPCs refuse the live player position on
every tick. Collision therefore uses the live player coordinate, and no
stationary mirror coordinate exists to consult. Likewise, the render-order
convention that mattered here is unchanged and independent of the retraction:
the renderer walks slots from thirty-one down to zero, so slot zero paints last
and the avatar is drawn on top of any actor sharing its cell — including a
Shadowlord installed on the same cell.

If a town-mode helper genuinely needs to find the player while walking the NPC
table, this spec does not currently describe one; treat any such requirement as
unestablished and read the player's position from the world-state globals.

## 9. Conversation: the Talk command

The Talk command triggers the conversation engine. The handler reads the player's current facing direction, computes the facing tile as `(player_x + dx, player_y + dy)`, and looks for an NPC whose linked sprite occupies that cell. If found, the NPC's dialogue index is handed to the conversation engine. If not found, the handler tests the facing tile for *talk-through* status (shop counters, low fences); if pass-through, it advances once more and queries again. If still no match, "Nobody's here!" is printed.

A pre-conversation gate then inspects the **live map tile at the resolved cell** — not the NPC's sprite. Tile `0xAB` (the bed tile) produces the "Zzzzzz..." line and tile `0x9D` (the mirror tile) produces the "No response!" line; both return without entering the engine, consuming the dialogue index, or reaching shop-trigger dispatch. Every other tile value falls through. `systems/conversation.md` Section 2 owns the full gate contract.

The Talk command is town-mode-only. The shared per-letter dispatcher routes T-Talk to the conversation engine when the scene byte indicates town mode; in overworld and dungeon modes the same key produces "Funny, no response!" or similar. There are no schedule-driven NPCs to talk to outside the named locations.

## 10. Special interactions

Several letter commands map to per-tile interactions that are interesting in town mode.

**Look.** L-Look prompts for a direction and samples the facing cell, then routes the terrain tile and active-object context through the shared world/town look handler. That handler resolves command-layer overlay markers to the tile being described, then either runs a special look path for wells, signs, and dungeon-mouth tiles or indexes `LOOK2.DAT` by the final tile id. Clock, shrine, and dungeon-entrance tiles print the base description and append their current context. Look does not consume a turn.

**Read sign.** Tile-class encoding for sign tiles triggers a prompt that loads the sign's text from a per-location sign data file, indexed by the sign's coordinates.

**Open / Jimmy.** O-Open applied to a door tile prompts for direction and triggers the door-open interaction: unlocked doors open (tile changes to "open door"); locked doors prompt for a key. J-Jimmy is the lockpick variant — it consumes a lockpick and either unlocks or breaks the lock. Both consume a turn.

**Retraction (2026-08-22).** This spec previously said town mode adds "a small amount of local policy" to Open — a mounted refusal, a direction prompt, an accepted closed-door and gate family, and a separate town chest path. That paragraph is withdrawn. It described the town **climb** handler, not Open: the mounted refusal, the direction prompt and the accepted fence/gate family all belong to K-Klimb and are already specified under "K-Klimb inside a location" in Section 7. Town mode contributes no local policy to Open at all — O routes straight to the shared Open handler, whose door, gate, and chest behavior is specified in `doors-and-z-transitions.md` and `containers.md`. If opening or stepping through a door exposes a stair transition, the stair/floor-change handling described in Section 7 runs.

**Attack.** A-Attack prompts for a direction and targets the adjacent cell. It refuses attacks from blocked posture/terrain states, resolves a small smashable-prop case, then looks for a live NPC linked to the target sprite. A valid hostile or attackable NPC target plays the attack presentation and either removes the NPC through the death flow or triggers town-wide alarm effects. Invalid targets produce the ordinary failure text. Attacking in town is therefore an in-town scene-state mutator: killing a townsperson or a named character records that slot as permanently removed in the per-scene removal mask (Section 4), while killing a guard or a creature records nothing and that slot is placed again on the next entry.

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

### Underfoot effects

Town mode has a single underfoot-effect handler, and Section 7's epilogue calls
it once per consumed turn. Its cadence matters as much as its contents:

- It runs **after** the clock advance for that turn, not before.
- It runs on **every** turn-consuming action, not only on a committed step. A
  party that stands still and passes turns, waits, attacks, opens a door, or
  takes any other turn-costing action re-runs the whole handler, including the
  tile effect for the cell it is standing on.
- Actions that consume no turn — Look, a cancelled prompt, an unrecognized key
  — do not run it at all.
- If an effect moves the party to a different floor, the handler re-reads the
  tile under the party's new position and applies that tile's effect too, so
  chained effects within one turn are possible.

The handler does the following, in order.

**Waking sleepers.** Each active party member whose status is Sleeping gets an
independent 1-in-16 chance to wake to Good status. This runs before the tile
effects and independently of what tile the party is on.

**Trapdoor / loose-brick step trigger, live tile `0x8C`.** (`0x8C` is *not* a
chair: the shipped description table names it a loose brick, and the seat tiles
are the separate `0x90..0x93` family, which carries no step trigger — see
`catalogs/tile-catalog.md`. The earlier "chair family" label here is withdrawn.)
Skipped entirely while the party's
transport marker is `0x14` or `0x15`, the carpet-family markers listed in
`systems/vehicles.md`. Otherwise the handler prints
its line, temporarily clears the transport marker for the presentation, rebuilds
the view, applies an independently rolled `1..8` hit points of damage to every
non-Dead party slot below the party count (capped at six slots), and restores
the transport marker. In the Stonegate scene the sequence then continues into
the special imprisonment cutscene that clears the town presentation, marks the
party into the long-term consequence state, and returns after a fade. In every
other scene the handler instead decrements the floor index, reloads the map, and
re-probes the tile under the party on the new floor.

**Burning family, live tiles `0xBC` and `0x8F`.** Rebuild the view, print the
stored line `Burning!`, then apply the same independently rolled `1..8` mass
damage to every non-Dead slot. These tiles are damage tiles, not cosmetic ones.
The two ids are the fireplace and molten lava of `catalogs/tile-catalog.md`
Section 6; an earlier revision of this bullet called them "the rune/lever
family", which is withdrawn.

**Poison-gas terrain, live tile `0x04`.** Keyed by live town tile id `0x04`
while the party's current transport marker is the on-foot marker `0x1C`. This is
a tile-id rule, not a coordinate sidecar: any loaded town-family cell that still
has live tile `0x04` and is processed while the party is on foot uses this
effect, and no coordinate table is needed. The handler scans active party slots
in order. Dead (`D`) and already Poisoned (`P`) slots are skipped. Every other
status, including Sleeping, is eligible. For each eligible slot, roll the shared
inclusive random range `0..29`; if the result is greater than that member's
Dexterity byte, set the member's status to Poisoned, print the status line for
that member, and repaint the stats panel. If the roll is less than or equal to
Dexterity, the member is unchanged and nothing is printed for that member.
Because the roll's maximum is 29, a member whose Dexterity is 29 or higher never
fails this save, and the failure chance is `(29 - Dexterity) / 30` otherwise.
Each eligible slot rolls independently, so several members can be poisoned in
the same turn, and the messages appear in slot order.

The predicate has no further conditions, and the list of ways it can fail to
fire is short and complete: the tile under the party is not `0x04`; the party's
transport marker is anything other than on-foot `0x1C`, which is how every
vehicle and mount suppresses the effect; the slot is Dead or already Poisoned;
or the member's Dexterity save succeeds. There is no scene, floor, coordinate,
authored-cell, or per-tile-attribute component to look up, no daytime or
schedule component, and no cell-consumption state — the same cell keeps working
forever. The effect is reachable only in town-family scenes because it lives in
the town underfoot handler; overworld and dungeon modes have their own
underfoot handlers and their own hazard sets.

Two consequences follow from the per-turn cadence that a step-only reading would
miss. First, standing on a gas tile is not safe: every turn spent on it is a
fresh save for every eligible member, so a party that lingers will eventually be
poisoned. Second, because the poison status tick in `systems/time.md` also runs
once per consumed turn, a member poisoned on a gas tile begins losing one hit
point per turn immediately, starting with the very same turn's status pass,
which runs at the end of this handler.

**Trailing party pass.** The handler finishes by invoking the shared party
status/provision pass specified in `systems/time.md`. That is where the
per-turn poison damage, the provision consumption and starvation branches, and
the Ring of Regeneration check happen for town mode.

## 11. Multi-floor locations

Nineteen of the thirty-two locations span more than one floor: ten have two, seven have three, and the two large castles have five each. The remaining thirteen are single-floor. `formats/location-dat.md` Section 4.1 gives the exact floor range of each.

Floor changes are mediated by the five authored cell families listed in Section 3 — the facing-sensitive staircase family, the two directional ladder ids, the metal grate, and the trapdoor.

The current floor is tracked in a single resident byte, signed, added to the location's base page (Section 3). When the player walks onto a staircase cell and triggers the climb, invokes K-Klimb on a ladder or grate cell, or steps onto a trapdoor, the floor byte is updated, the tile buffer is reloaded with the new page's data (running the marker-harvest, dawn/dusk gate-normalization, and blight passes again), the active-object table is partially reset (NPCs not on the new floor are unlinked, NPCs on the new floor are linked), and the player's slot is updated with the new Z. X and Y are preserved across the transition. The schedule processor handles its own side through its Z-mismatch state machine described in the NPC schedules spec.

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
Ring of Regeneration check belong in `systems/time.md`. The town-bed loop does
invoke the shared party status/provision pass once per ten-minute step, so
poison damage, the Ring of Regeneration roll, and any crossed-hour provision or
starvation branch all apply while a town-bed sleep elapses.

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

**The harpsichord and the secret passage.** Lord British's castle holds a
harpsichord — tile `0x8D`, whose `LOOK2.DAT` description names it as an
instrument with ten keys numbered zero through nine — on floor `+2`, two
storeys above the castle's entry floor, with a chair in the cell immediately
north of it. The instrument is armed by
position alone, and the test is exactly "the tile one cell south of the party
is the harpsichord tile": no flag, latch, or prior event arms it. This is the
same four-neighbour probe the Fire and Yell commands use.

While the party is seated there, the town turn loop routes the digit keys `0`
through `9` to the instrument instead of to the ordinary command dispatcher.
Anywhere else, and on any other floor, the handler immediately forwards the
digit to the ordinary dispatcher and returns its result, so digits behave as
normal commands everywhere but the chair.

- **Sound.** Pressing a digit plays one note, and only when the global sound
  setting is on. The ten keys are a descending major scale: digit `1` is the
  highest pitch, the pitch falls through `2`..`9`, and digit `0` is the lowest,
  one whole step below `9`. The scale's two semitone steps fall between `3` and
  `4` and between `7` and `8`.
- **No turn is consumed.** The handler returns the loop's re-prompt result, so
  playing the instrument never advances the clock, never ticks the NPC
  schedule, and never redraws.
- **The tune is thirteen notes:** `6 7 8 9 8 7 8 7 6 7 6 5 3`.
- **A wrong note does not necessarily start the player over.** Progress
  re-syncs to the longest run of just-played notes that is still a beginning of
  the tune. Concretely: after ten correct notes a stray `8` leaves the player
  three notes in; after eleven correct notes a stray `7` leaves them two notes
  in; a stray `6` at any other point leaves them one note in; any other wrong
  note resets progress to zero. Progress is not cleared by leaving the chair —
  only by a wrong note or by completing the tune.
- **Completion.** On the thirteenth correct note, and only while the scene is
  Lord British's Castle and the floor byte is `2`, the wall cell five squares north
  of the harpsichord in the same column is rewritten in the live tile buffer to
  ordinary cobble floor, opening the passage behind it, and the view is marked
  dirty. Progress resets to zero. The rewrite is a live tile-buffer edit rather
  than a saved map change, so reloading that floor restores the wall.

The castle's tile grid, NPC roster, and dialogue file are otherwise ordinary. A
handful of other named locations have one-scene quirks (a scripted NPC arrival
in one dwelling, a special-event stairway in one keep), encoded entirely in
their data or mode-specific handlers.

**Shadowlord hideout installation on town entry.** Entering one of the eight
towns compares the town's own scene byte against the three Shadowlord hideout
slots. On a match, the entry path records which of the three is hosted here and
allocates a live actor slot for that Shadowlord, so the Shadowlord is present in
the town's cast without the player doing anything. The town's scene identity,
map, and NPC roster are unaffected — entry never rewrites the scene byte to a
different location. Only the eight town scenes can match, because the slot value
is itself a town scene byte (`catalogs/quest-graph.md`, Runtime Shadowlord
State). One guard applies before anything else: the whole check is skipped when
the party's Y coordinate at that moment is `4`, in which case no host is
recorded and no Shadowlord is installed.

The first thing the entry path does with a recorded host is the
farmland and orchard blight described in Section 3: the hosting town's live
floor buffer is walked and most of its standing crops and fruit trees are
rewritten to a plowed patch and a hollow stump. That pass runs before the
cancel condition below, so it applies even on an entry whose install is
rejected, and it is the only visible effect a resident Shadowlord has on the
terrain itself.

Once a host is recorded, exactly one condition can still cancel the install.
The entry path walks the whole 32-record active-object table and abandons the
install if any live record already carries the Shadow Lord actor tile `0xFC`.
**This is a one-at-a-time rule, not a "the table is full" rule.** It is the same
mechanism as the Y-Yell summon gate in `systems/commands.md` Section 11, and it
has the same two consequences: a town whose active-object table is merely
crowded still receives its Shadowlord, and a town entered while a Shadowlord
summoned elsewhere is still standing in the table receives none. An engine that
substitutes a free-slot test here lets the player stack Shadowlords, and an
engine that omits the check entirely does the same.

The install itself has no failure outcome. After the one-at-a-time check
passes, the path reserves an actor record and then chooses a scene-actor index
by taking the highest-numbered free index, searching downward from `31`. If no
index is free it proceeds with index `31` regardless, overwriting whatever
occupied it. There is no "no room, skip the Shadowlord" path.

The installed record is a Shadowlord actor: both identity bytes of the
active-object record carry the Shadow Lord actor tile `0xFC`, the auxiliary and
phase bytes are cleared, the floor byte is `0`, and the position is column `15`
of the town's thirty-two-by-thirty-two grid at a fixed per-town row:

| Town (scene byte) | Shadowlord row |
|---|---:|
| Moonglow (`1`) | 4 |
| Britain (`2`) | 9 |
| Jhelom (`3`) | 15 |
| Yew (`4`) | 8 |
| Minoc (`5`) | 17 |
| Trinsic (`6`) | 10 |
| Skara Brae (`7`) | 11 |
| New Magincia (`8`) | 10 |

The actor is also given a stationary three-waypoint schedule pinned to that same
cell, so it does not wander away from its install position on its own.

The host is also announced to the player. After the map has been loaded and the
host recorded, a settlement that hosts a Shadowlord prints one line naming
which — an air of falsehood, of hatred, or of cowardice doth surround thee —
and plays the associated tone. That single line is the only in-town notice, and
a settlement hosting none prints nothing. Stonegate's separate entry
presentation, described at the end of this section, is a different producer: it
prints one such line per still-living Shadowlord regardless of where each is
hiding.

Which of the three is hosted also selects a one-shot, town-wide NPC state
sweep that runs at the end of the same entry pass. This paragraph is the only
statement of that mapping in this spec — nothing earlier describes it. Hatred
rewrites every eligible NPC's schedule into **permanent pursuit of the party**,
Cowardice rewrites every eligible NPC's schedule into **flight** and replaces
that NPC's conversation with a cowering line, and Falsehood changes no NPC at
all (its effects are the shop surcharge and the conversation theft). Eligibility
is the same per-NPC predicate the alarm sweeps of Section 14 use, and the two
resulting rewrites are the same two described there; the difference is only the
trigger.

> **Withdrawal.** Earlier revisions of this paragraph called these outcomes "the
> fortified/alert state" and "the pacified state". Both names were wrong and the
> first was inverted. There is no NPC "state" field involved: each outcome
> overwrites the NPC's stored *schedule* and its stored *dialogue index*. The
> "fortified" outcome installs an aggressive approach mode — nothing about it
> holds position or defends — and the "pacified" outcome installs the engine's
> only retreating mode plus a cowering line, so the NPC is frightened rather than
> calmed. Both rewrites are destructive of persisted data: the NPC's real
> conversation index is overwritten and cannot be recovered from the save. Eligibility asks three things of an NPC:
that its daily schedule block is not empty, that its type falls in the
ordinary-townsperson band, and that a per-NPC coin flip comes up — so roughly
half of the eligible cast flips on any given entry.

That predicate carries one original-code quirk worth naming rather than
inheriting by accident: the type-band half of the test is evaluated against a
fixed roster slot instead of against the NPC being tested, so it returns the
same answer for every NPC in the sweep, while the schedule test and the coin
flip are per-NPC as intended. The schedule-rewriting helper the sweep then calls
performs the same band test correctly, against the real NPC. A reimplementation
should decide deliberately whether to reproduce the fixed-slot read; it is an
implementation artefact, not a designed rule. In a town hosting no Shadowlord, and in a
town whose install was skipped by the row-`4` guard, the sweep does not run.

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

A hostile NPC adjacent to the player blocks movement onto their cell ("Bump!"). A-Attack directed at a town NPC plays the attack presentation, can smash a small prop, can mark or clear the targeted NPC through the town death flow, and can trigger the town-wide alarm sweep. An earlier revision of this section also said the town overlay "does not call the combat framer or swap to a `.CBT` arena"; that is withdrawn. The town overlay has a live NPC-conflict chain, entered both from A-Attack and from post-action cleanup, that hands the target NPC's linked active-object slot to the same terrain-combat entry the overworld uses, so a town fight is an ordinary arena fight: ordinary town ground resolves to the cobble arena, and the scene-keyed town-style override forces the monster count to one unless the target's class is Guard (whose stat row carries the sentinel count eight). On exit the town chain clears the NPC slot, reloads the town map, and re-runs the Shadowlord install pass of Section 13 (which, in a hideout town whose Shadowlord is still standing in the active-object table, is rejected by the one-at-a-time check and does nothing). The full contract is in `systems/encounters.md` Section 7.

NPCs whose hostile predicate is always true remain schedule-driven town actors between fights. When the scheduler reports an attack/catch event, town post-action cleanup routes it through the alarm, arrest, frighten, death, or slot-clear paths described below, or into the NPC-conflict chain above; those routings are what this section owns, while the arena fight itself belongs to the encounter and combat specs.

Town alarms are one-shot sweeps over the NPC roster. Depending on the triggering path, an eligible NPC's stored schedule is overwritten in one of two ways.

> *Corrected (2026-08-23).* An earlier revision of Section 7.1 said the
> drunkenness stage "scatters nearby NPCs", and the source list below called the
> same effect an "NPC scatter"; that wording is **withdrawn**. Nothing in the
> sweep displaces an NPC. A fresh full re-read of the sweep and of both of the
> helpers it calls found that none of the three writes a coordinate anywhere:
> what changes is the NPC's persisted per-period behaviour modes, its
> time-of-day boundaries, and (on the flight path) its dialogue index. An
> implementer must not move any actor on this path.
>
> Two further limits on what has been established, recorded so they are not
> over-read: the coin flip on the non-special path was re-confirmed as a draw
> compared against a mid-range threshold, but the draw's exact range was not
> re-verified, so "half" is approximate rather than an exact one-in-two; and the
> meaning of the individual behaviour-mode values written by the two helpers
> comes from the separate analysis of those helpers, not from the sweep itself.

- **Forced pursuit.** All three of the NPC's per-period behaviour modes are set to an approach mode, and all four of its time-of-day boundaries are zeroed so the schedule can never advance past its first period. The NPC's waypoint coordinates are left alone. Two approach modes are used, chosen by the NPC's class: one acts only while the party is within about four tiles, the other acts every turn and adds an occasional random step. Both step toward the party and both raise the "reached the party" event on adjacency, which this section's cleanup turns into the attack path.
- **Forced flight.** All three behaviour modes are set to the engine's only *retreating* mode — it acts only while the party is within about four tiles, and then steps to whichever neighbouring square is **further** from the party — and the NPC's dialogue index is overwritten with a sentinel that makes conversation produce a single canned cowering line instead of the NPC's real script. This is destructive: the real dialogue index is gone.

Some special classes — the Shadow Lord actor class, the lich/death-mage class, and the guard class — always take the pursuit rewrite. Other eligible townsfolk take a random half-chance of the flight rewrite; the rest are untouched. The flight rewrite additionally applies only to ordinary human townsperson classes, so monsters cannot be made to flee. The schedule walker consumes these rewrites on later ticks.

> **Withdrawal.** Earlier revisions called these "a fortified/alert schedule
> state" and "a pacified/fleeing schedule state". "Fortified" was inverted — the
> mode installed is an approach mode — and "pacified" was wrong in the other
> direction: the NPC is frightened, not calmed, and calm is a different mode
> entirely. Neither writes an NPC "state" field; both overwrite persisted
> schedule data, and the flight rewrite also destroys the NPC's conversation.

After each schedule tick, town mode interprets the walker's event bytes. When an NPC in one of the two approach modes reaches the party, it raises the guard/non-attack event; if that NPC's dialogue index is already the sentinel written by an earlier sweep, town mode prints a shouted brush-off ("Begone, vermin!") and then applies the **flight** rewrite to that NPC — one warning, then it runs. (Earlier revisions described this as printing a message and "pacifying" the NPC; both halves are withdrawn.)

Three routings reach the arrest sequence, and all are now bounded. First, an approaching guard reaches the party with the ordinary guard sprite and without the cowering-dialogue sentinel. Second, a different flagged-NPC event automatically dispatches that NPC's reserved Blackthorn guard demand; refusal, insufficient gold, a missing Badge aura, or a wrong password produces its sole positive outcome and enters arrest. Third, the player explicitly uses `T` on the same reserved guard-demand figure and receives the same failed outcome. The resident command dispatcher converts only that explicit-T failure into town result `2`; result `2` has no other command producer, skips a fresh schedule walk, and passes the arrest discriminator to cleanup. Because the schedule walker is also the only ordinary clearer of its event bytes, the original examines a retained approach-event code before the result-derived discriminator; that rare prior-event state can take precedence. In the normal no-event state, result `2` enters arrest directly. Ordinary NPC conversations, shops, canned replies, successful payment, and the accepted password all use the normal action result and do not take this route.

The arrest sequence itself branches on the current location before it prints anything. Inside Lord Blackthorn's Castle, and while the shared party-capability check reports that at least one member can act or is asleep, it plays the Blackthorn audience/capture cinematic and then re-runs town entry setup for the same location; `systems/blackthorn.md` owns that path. In every other location, and in Blackthorn's castle when nobody can act and nobody is asleep, it prints the arrest challenge and asks whether the party will come quietly: surrendering prints the knockout and awakening lines, fades, moves the party to the Yew jail scene at `(25, 4, 0)`, marks the view dirty, advances time in twenty-minute cleanup calls until the hour reaches 08:00, clears the jail-scene latch, and returns as a consumed turn. Refusing prints the guards' challenge, triggers the alarm sweep, and consumes the turn. Monster-class or attack outcomes can route through the NPC death flow, which marks the scene mask, clears the live slot, reloads the floor, and re-runs the Shadowlord install pass of Section 13 (normally a no-op, for the reason given above).

## 15. Exit

The player leaves a town by walking off the edge of the interior grid. There is
no exit tile. The movement handler flags a step whose destination would fall
outside the thirty-two-by-thirty-two floor — north from the top row, south from
the bottom row, west from the leftmost column, east from the rightmost column —
and, once the step has otherwise passed the ordinary terrain and occupancy
tests, asks whether the party wishes to leave instead of committing the step. A
destination that fails those ordinary tests prints the blocked feedback and the
prompt is never raised, so a location whose outer ring is impassable in some
direction cannot be left that way.

The prompt is a yes/no question. Accepting prints the affirmative and the
destination plane, clears the scene byte, computes the player's overworld
coordinate from the fixed world-location coordinate tables, writes the
destination plane (Britannia for ordinary scenes, the Underworld for scene byte
`0x19`), clears the town-local curse/state latch, and signals the loop to
break. Declining — by answering no or by cancelling — prints the refusal,
clears the pending-exit flag, leaves town mode active, and does not move the
party; the step itself is discarded either way, so a declined exit never nudges
the avatar onto the boundary cell.

**Withdrawn label.** Earlier revisions of this spec named "the town-family exit
threshold, tile id `0x59`" as the trigger. That is withdrawn. Tile `0x59` is the
telescope (`catalogs/tile-catalog.md`), a Look trigger that occurs in exactly
three interior cells across all shipped maps and never on a location boundary;
the value was a misreading of the affirmative keystroke consumed by the leave
prompt. No tile id participates in the town-family exit decision.

The town turn loop's per-turn epilogue checks the scene byte each iteration. When the byte clears, the loop returns to the main game loop, which reloads the overworld map, restores the overworld active-object table from the on-disk overlay, and resumes overworld mode at the location's overworld cell.

Exit is symmetric with entry: every per-location piece of state allocated during entry is cleared or freed; the next entry runs the full setup pass against the next location's data. There is no cross-town retention.

Soft exits and sub-modes re-entering the same town do not clear the scene byte
and short-circuit the entry pass on return. NPC slot state is preserved across
the round-trip, so a guard who was at slot fifteen before the sub-mode remains
at slot fifteen after.

## 16. Hooks into other systems

**Visibility.** Town mode shares the visibility producer with overworld and dungeon modes. The producer runs against the location's tile buffer and the active-object table on each render. Town mode sets the visibility-dirty flag on entry, on floor change, and on schedule-walker reports of "any NPC moved", forcing a recompute.

**Command dispatch.** The shared per-letter dispatcher receives every keystroke not handled by the town-mode movement table. It routes mode-aware commands (A-Attack, K-Klimb, T-Talk) to town-specific handlers and shared commands (G-Get, P-Push, V-View) to cross-mode handlers.

**NPC schedules.** Town mode invokes the schedule processor once per ordinary
consumed turn. The explicit-T arrest-cleanup result is the one exception: it
skips the processor and enters arrest cleanup after the common time and
underfoot work. The H-Hole-Up hours path invokes the same scheduler from inside
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

The exact free-roaming object contract is:

| Step | Rule |
|---|---|
| Slot scan | Walk all 32 active-object slots in ascending slot order. Eligibility is based on active-object byte `+0`, not the rendered tile buffer. |
| Eligible object bytes | `(byte0 & 0xFE) == 0x10`; in the traced data this is the animal/horse/cow style pair `0x10` and `0x11`. Empty slots, the avatar's slot-zero record, linked NPC sprite classes, and all other object families are skipped. |
| Floor gate | Active-object byte `+4` must equal the current floor/Z byte exactly as a byte. Off-floor objects are skipped and are not moved toward the current floor. |
| Chance gate | After the byte and floor gates pass, draw one uniform bit through the shared PRNG range helper. Nonzero skips the object for this tick; zero proceeds, so each eligible on-floor object has a 50% movement-attempt chance. No PRNG value is consumed for ineligible or off-floor slots. |
| Pen gate | Before selecting a destination, test all four cardinal neighbours with the walker-local `0xA2`/`0x43` blocker predicate. If any cardinal neighbour is exactly `0xA2` or exactly `0x43`, the object makes no movement attempt this tick. |
| Walker blocker predicate | The walker-local helper returns nonzero only for live town tile bytes `0xA2` and `0x43`, and this caller treats nonzero as "abort movement." This is not the NPC pathfinding bitmap, not the foot/avatar movement predicate, and not the final destination passability check. |
| Direction selection | After the pen gate passes, draw two uniform bits. The first bit selects the movement axis: nonzero selects X, zero selects Y. The second bit selects the sign on that axis: zero is `-1`, nonzero is `+1`. This yields one of the four cardinal one-cell destinations with equal probability. There is no retry with a different direction after the chosen destination fails later checks. |
| Bounds | Destination X and Y must remain in the loaded 32-by-32 location floor, `0..31` on each axis. Town object walking does not wrap at edges. |
| Destination terrain and occupancy | The chosen destination is re-read and must pass the resident tile-class dispatcher with query byte `0x10`. The active-object lookup at that destination and current floor must return no occupied slot. The player cell, NPC-linked objects, unlinked objects, and slot-zero records therefore block by occupying the destination coordinate on the current floor. |
| State update on success | Write the chosen animal facing byte to active-object bytes `+0` and `+1`, write the destination X/Y to bytes `+2` and `+3`, and set the visibility-dirty bit. X+ movement writes `0x10`, X- movement writes `0x11`, and Y movement preserves the object's previous `0x10`/`0x11` facing byte. Byte `+4` and auxiliary bytes are left as they were. |
| State update on failure | Failed terrain, bounds, or occupancy checks leave the object record unchanged and do not mark visibility dirty. |
| Persistence | The active-object table is part of the saved town scene state, so a save made after a free-roaming object has moved preserves the moved object record. Reloading a saved town scene then runs normal town entry reconciliation, which may reattach roster-driven NPCs from schedules; unlinked animal/object records remain active-object state rather than schedule waypoints. |

**Movement.** The shared movement spec owns direction-code routing,
the resident terrain-query layer, dynamic occupancy, and commit rules. This
town-mode spec owns the current floor buffer, NPC collision/scheduling side,
the grid-boundary exit prompt, and floor-transition hooks around successful
movement.

**Save / load.** A save inside town freezes the scene byte, the floor byte, the player position, the active-object table, and the world-state clock. On load, the engine notices the non-zero scene byte, re-runs the entry pass, and snaps the player and NPCs to saved-or-re-derived positions. The runtime NPC block is not persisted as a chunk; it is re-derived from the schedule and the saved hour, producing NPCs at their currently-scheduled location regardless of mid-route progress. The dawn/dusk gate pass runs at load time using the saved hour.

## 17. Town Boundaries And Remaining Data Work

Town/interior mode is complete at behavioral-contract depth: entry, map load,
marker harvest, dawn/dusk substitution, the resident-Shadowlord farmland blight, movement and
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

- **Underfoot-effect cadence is fixed.** The underfoot handler is a per-turn
  post-action pass, not a step-commit hook. Any earlier statement that the
  poison-gas effect "fires from the step path" is retracted: it fires once per
  turn-consuming action while the party occupies the tile, including turns spent
  passing in place, and it fires after that turn's clock advance. No separate
  idle or pass table exists, and none is needed.

- **Soft re-entry empirical parity.** The traced caller census now assigns the
  preserving and fresh setup argument paths. Remaining work is empirical parity
  for rare nested script returns, if a test target needs confirmation of
  whether they can reach town setup without going through one of the traced
  caller families.

## 18. Sources

The behaviour described above was derived by reading the function and format notes listed below. None of the assembly excerpts, byte offsets, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed behaviour.

- The town-mode entry handler that loads the location's map, runs the marker harvest, applies the dawn/dusk gate substitution, and calls the Shadowlord install — `u5-decomp/functions/TOWN_OVL/` (its own step describing the coordinate guard is stated inverted there and is superseded by the 2026-08-22 repair-round correction in the install's note).
- The top-level dispatcher and resident NPC-location warp helper that supply
  the traced fresh-versus-preserving town setup arguments -
  `u5-decomp/functions/ULTIMA_EXE/`.
- The per-turn loop that reads commands, dispatches, runs the schedule walker, advances time, and toggles gates at the dawn/dusk hour boundaries — `u5-decomp/functions/TOWN_OVL/`.
- The per-location map loader, the marker harvest, and the dawn/dusk gate substitution — `u5-decomp/functions/TOWN_OVL/`.
- Source provenance: derived from private analysis notes
  `u5-decomp/functions/TOWN_OVL/` and
  `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md` -- the
  farmland/orchard blight, its resident-Shadowlord gate and its two call sites,
  its two substitutions, its seven-in-eight rate, its day-of-month seed, and
  the clock re-seed that follows it. That note's earlier "grass/path
  texturing", "six-in-seven", "save/restore the PRNG" and
  "runs once the player's actor slot has been assigned" readings are all
  superseded; the gate is the resident-Shadowlord record of Section 13, not an
  actor-slot sentinel, and the substitution is therefore a hideout-town blight
  rather than a generic harvest.
- The town-entry Shadowlord install — its hideout-slot match, its
  one-at-a-time reject, its actor-index choice, and its placement and schedule —
  `u5-decomp/functions/TOWN_OVL/` (see that
  note's 2026-08-22 repair-round correction, which supersedes its original
  "player attach" framing) and
  `u5-decomp/notes/2026-08-22_quest-world-retrace.md`.
- The per-scene NPC removal mask reader/writer and runtime slot free helper - `u5-decomp/functions/TOWN_OVL/`, and `u5-decomp/functions/TOWN_OVL/`.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_save-band-transport.md` -- the
  corrected sprite-class filter for recorded removals (townspeople and royal
  regalia in, guards and creatures out), the two hard-wired removal writers, and
  the exhaustive accessor sweep showing the mask has no other owners.
- The reverse lookup from sprite slot to live NPC slot - `u5-decomp/functions/TOWN_OVL/`.
- The stair/floor movement tail, vehicle movement presentation, movement command handler, and underfoot interaction handler - `u5-decomp/functions/TOWN_OVL/`, and `u5-decomp/functions/TOWN_OVL/`. The Section 15 grid-boundary exit contract, and the withdrawal of the earlier "exit threshold tile" reading of it, are derived from the same movement-handler note as re-traced on 2026-08-22, cross-checked against the shipped-map placement census in `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md`.
- The town Attack handler and the town K-Klimb handler - the corresponding command-handler notes under `u5-decomp/functions/TOWN_OVL/`. The climb-handler note predates the 2026-08-22 retrace and is filed under a different command name than the one it actually analyses; the retrace note above supersedes its labelling.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/scene_floor_page_table_2026-08-22.md`. That note supplies the
  per-scene base floor-page binding and its sign convention, the complete
  inventory of floor-transition cells and their on-screen text, the climb
  command's refusal cases and its fence/gate side path, the trapdoor's general
  descend behaviour and the single scripted exception at Stonegate, the
  full-reload semantics of a floor change, and the two roles of the saved floor
  byte. It also fixes the floor of the harpsichord puzzle: floor `2` is two
  storeys above the castle's entry floor, not a basement.
- The town alarm, forced-pursuit / forced-flight schedule rewrites, death, arrest, and post-scheduler cleanup helpers - `u5-decomp/functions/TOWN_OVL/`.
- The Lord British castle chord handler - `u5-decomp/functions/TOWN_OVL/`.
- The Stonegate setup helper audio/presentation pattern - `u5-decomp/functions/TOWN_OVL/`.
- The free-roaming animal/object walker and its narrow town terrain predicate - `u5-decomp/functions/TOWN_OVL/`.
- The town input parser, including command refresh and modal override behavior - `u5-decomp/functions/TOWN_OVL/`.
- The town NPC reseat pass that runs on entry and after every floor reload - it clears the dynamic-object records, then re-places every occupied NPC at the waypoint its schedule selects for the current hour and resets that NPC's walk state - `u5-decomp/functions/TOWN_OVL/` (see that note's 2026-08-22 naming correction: the pass touches no visibility state, and the earlier "visibility pass" wording here inherited the stale private filename).
- The world-mutation primitive that links logical NPC state to active-object slots — `u5-decomp/functions/TOWN_OVL/`.
- The NPC roster loader for one location — `u5-decomp/functions/NPC_OVL/`.
- The per-tick NPC walker invoked once per turn from the town loop — `u5-decomp/functions/NPC_OVL/`.
- The NPC pathfinder notes that bind the ascend/descend marker IDs `0xC8` and `0xC9` to the scheduler's tile-ID goal path, plus the town step handler's separate `0x8C` trigger — `u5-decomp/functions/NPC_OVL/`, and `u5-decomp/functions/TOWN_OVL/`.
- The shared per-letter command dispatcher routed by mode — `u5-decomp/functions/ULTIMA_EXE/`.
- The per-turn cleanup that advances the clock and recomputes daylight — `u5-decomp/functions/ULTIMA_EXE/`.
- The underfoot handler's unconditional per-turn placement after the clock
  advance, its wake roll, its two mass-damage tile families, its poison-gas
  Dexterity save and per-member presentation order, and its trailing party
  status pass -
  `u5-decomp/functions/TOWN_OVL/`,
  `u5-decomp/functions/ULTIMA_EXE/`, and
  `u5-decomp/notes/party_status_pass_cadence_2026-08-22.md`.
- Independent second-pass re-derivation of the poison-gas predicate, the
  Dexterity save comparison, the absence of any further gating condition, and
  the caller-side per-turn placement:
  `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.
- The location tile-grid file format and the two-floor-per-location layout — `u5-decomp/formats/maps.md`.
- The NPC roster and dialogue file formats — `u5-decomp/formats/npc-tlk-pth.md`.
- The clean verification summary for Lord British's castle scene binding and
  town-mode load smoke checks - `u5-spec/NEXT-STEPS.md`.
- The save image's scene-byte encoding and the per-location coordinate state — `u5-decomp/formats/saves.md`.

Source provenance: derived from private analysis in `u5-decomp/notes/` for the
three routings into the arrest sequence and its
Blackthorn-castle branch, the resident-Shadowlord entry effects, and the
harpsichord's arming condition, key-to-pitch mapping, thirteen-note tune,
mistake re-sync, and completion effect.

- The town drunkenness stage (the tavern-armed counter, the even-odds command
  substitution with its hiccup line and NPC schedule-rewrite sweep, the decrement
  rule, and the town-entry clear), the harpsichord digit behaviour and its no-turn re-prompt
  status, and the town loop's four-way reading of the command status. Source
  provenance: derived from private analysis in `../u5-decomp/notes/`.
