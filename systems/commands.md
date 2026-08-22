# Commands

## 1. Overview

Ultima V has two command-dispatch layers during normal play. The input system
turns keyboard events into one translated byte. The active mode loop then
handles mode-local controls first: movement directions, digits where the mode
uses them, sound toggles, explicit quit prompts, and any other control bytes
below the printable range. Printable command letters that survive this
pre-routing go to the resident world-command dispatcher.

This spec covers that resident dispatcher: the A-Z and Space command surface
shared by the overworld, town-family locations, and dungeons. Combat has its own
dispatcher and command table inside the combat overlay; see `combat.md`.

The dispatcher is not a user-interface loop. It does not poll the keyboard. It
receives one already-translated byte from the active mode loop, prints the
command's verb prefix, chooses the correct handler from the current scene byte,
and returns a status word to the caller.

## 2. Inputs And Scene Routing

The dispatcher expects one byte from the input pipeline:

- `Space`, uppercase `A..Z`, and a small number of printable punctuation bytes
  are legal dispatcher inputs.
- Lowercase letters should already have been folded to uppercase by the input
  system.
- Direction codes should normally have been consumed by the active mode loop.
  The one confirmed dispatcher-visible direction/control code is the cursor-east
  typeahead toggle described in Section 9.
- Function-key remap codes are not part of the resident A-Z command table.
  Mode loops or menu-specific prompts should consume or ignore them before
  falling through to letter dispatch.

Scene routing uses the resident scene byte:

| Scene byte range | Dispatcher meaning |
|---:|---|
| `0` | Overworld branch. |
| `1..32` | Town/dwelling/castle/keep branch. |
| `33..127` | Dungeon branch when the dungeon mode loop forwards a letter. |
| `0xFF` | Combat-class marker; not a normal caller of this dispatcher. |

Mode loops may intercept a key before it reaches this dispatcher. For example,
dungeon mode handles its own explicit "Exit to DOS?" prompt before forwarding
ordinary letters, and overworld mode has a control-code quit prompt in its
pre-dispatch table. Those paths are separate from the resident `Q` save-game
letter described below.

## 3. Return Contract

The returned status is a loop-control hint, not a gameplay result enum. The
default normal result means "the handler completed normally"; mode loops then
decide whether to run their per-turn epilogue. Other observed values cover:

- no-advance cases such as the typeahead-buffer toggle;
- cancelled or refused prompts;
- town-specific re-poll cases where the loop should continue without a full
  redraw;
- values forwarded directly from overlay handlers, especially movement,
  attack, climb, and yell handlers.

A modern implementation should preserve the observable turn cost of each
command rather than depend on the original numeric return values everywhere.
Mode specs document the visible turn-cost rules for their command families.

## 4. Command Table

The table below is the dispatcher-level contract. Individual handler specs own
the detailed prompts, item consumption, stat writes, tile rewrites, and combat
handoffs.

| Input | Dispatcher route | Scene-specific contract |
|---|---|---|
| `Space` | Pass / wait inline path. | Prints the pass feedback and consumes a pass action unless a mode/vehicle-specific refusal applies. |
| `A` | Attack. | Routes to overworld, town, or dungeon attack handlers by scene. Combat attack is handled by the combat dispatcher instead. |
| `B` | Board. | Routes to the vehicle-boarding handler; succeeds only when the local vehicle/object context allows boarding. See `vehicles.md`. |
| `C` | Cast. | Routes to the spell-casting overlay. Spell prerequisites, parser rules, charge use, mana use, and scene masks live in `magic.md`. |
| `D` | Default refusal. | No resident world-command handler is currently confirmed; it falls through to the stock "What?" response when it reaches this dispatcher. |
| `E` | Enter. | Overworld routes to the location/dungeon entry helper. Non-overworld scenes use the resident refusal prompt path. |
| `F` | Fire. | Routes to the fire/cannon handler family. Overworld ship broadsides use a sub-handler; dungeon mode refuses. Door-destruction messages belong to this family, not to Open or Jimmy. See `vehicles.md`. |
| `G` | Get. | Routes to the Search/Jimmy/Open/Get overlay's Get handler. Dungeon mode skips the surface/town Get prefix and falls into the underfoot chest path. |
| `H` | Hole up / rest. | Overworld and dungeon use the rest-with-watch path. Town mode uses the inn/bed-hours path and refuses off bed tiles. The shared rest handler owns the hours prompt, sleep cleanup, HP recovery, rest-interruption checks, and the rare outdoor Lord British camp event; see `rest-and-camp.md`. |
| `I` | Ignite. | Routes to the torch-lighting handler. It consumes one torch if available and then sets or extends the torch duration as described in `lighting.md`. |
| `J` | Jimmy. | Routes to the lockpick handler for doors, chests, and pickpocket-like cases. |
| `K` | Klimb. | Mode-aware: overworld, town-family locations, and dungeons each have their own climb/Z-transition handler; the gear gate, on-foot check, ladder cases, and dungeon level rules are specified in `doors-and-z-transitions.md`. |
| `L` | Look. | Dungeon scenes route to DNGLOOK. Overworld and town-family scenes route to LOOKOBJ and `LOOK2.DAT`; see `view.md`. |
| `M` | Mix / shrine-command family. | Ordinary field use routes to CMDS reagent mixing. Shrine-family special tiles route through CAST2's shrine/urn entry handler, which then dispatches internally to virtue meditation or Codex urn reading. |
| `N` | New order. | Routes to the party-order swap handler described in Section 6. |
| `O` | Open. | Routes to the Open handler for doors, chests, and dungeon underfoot cases. |
| `P` | Push. | Refuses in dungeons; otherwise routes to the push/movable-tile handler described in Section 8. |
| `Q` | Save game. | Routes to the save-game handler, which prompts whether to save. On `N`, it returns without writing. On `Y`, it writes the save files, acknowledges completion, and returns to the caller. This letter is not the DOS-terminate path by itself. |
| `R` | Ready. | Routes to the equipment-ready handler in the status/equipment overlay. The picker, slot mapping, stock-counter mutations, and hand-occupancy gates are specified in `inventory.md`. |
| `S` | Search. | Routes to the Search handler, including secret-door and searchable-object paths. |
| `T` | Talk. | Town-family scenes route to the conversation engine. Overworld and dungeon scenes refuse; the overworld path may still prompt for a direction before printing its refusal. |
| `U` | Use. | Routes to the non-combat item-use handler. The implementation lives with the spell/item overlays rather than in the command dispatcher; usable-item families are specified in `inventory.md` and `catalogs/item-list.md`. |
| `V` | View / gem. | The dispatcher checks gem count first. If none remain, it prints the no-gem refusal. Otherwise it decrements the count and routes to LOOKOBJ for overworld/town view or DNGLOOK for dungeon view. Combat `V` is label-only and does not consume a gem; see `view.md`. |
| `W` | Default refusal. | No resident world-command handler is currently confirmed; it falls through to the stock "What?" response when it reaches this dispatcher. |
| `X` | X-it. | Routes to the vehicle-exit/dismount handler outside combat. Ordinary dungeon `X` is a refusal/no-op; combat `X` uses the combat-only escape handler specified in `combat.md`. |
| `Y` | Yell. | Routes to the Yell handler described in Section 11. Shipboard Y toggles sails as specified in `vehicles.md` and `weather.md`; non-ship branches handle words of power and Shadowlord-name effects. |
| `Z` | Z-stats. | Routes to the character/status display overlay. Character stat pages, equipment display, and shared-inventory browsing are specified in `inventory.md` and `text-output.md`. |

## 5. Verb Prefixes And Prompts

Each command block prints a resident verb prefix before it invokes the handler
or refusal path. Examples include the familiar command names such as Attack,
Board, Cast, Open, Quit, and Z-stats. The prefix is part of the original text UI:
commands that immediately prompt for a direction, party member, item, spell, or
yes/no answer do so after the prefix has been emitted.

Handlers are allowed to re-enter the input system for follow-up prompts. The
input spec owns the cursor, prompt-character, typeahead, and reentrancy rules.
The command spec's contract is simply that prompts are synchronous: a handler
does not return to the mode loop until its prompt sequence has completed or been
cancelled.

## 6. N-New Order Party Command

N-New Order is a party-roster command for changing the travelling order. It is
available from the resident world-command dispatcher; combat has its own `N`
label and does not inherit this party-order effect.

The command prompts for two party members through the shared party-member
selector. Cancelling either prompt prints the no-selection result and returns
without consuming a turn. If either selected slot is slot zero, the command
refuses because the leader must remain first, and it returns without consuming
a turn.

On a successful non-leader selection pair, the command exchanges the two
selected roster records as whole thirty-two-byte character records. Name,
status, stats, class letter, equipment, and per-record counters all move
together. The party-size field is not changed, no world object or tile state is
touched, and the command marks the turn as consumed after the exchange. Picking
the same nonzero slot twice is accepted: the whole-record exchange is a
behavioural no-op, but the turn is still consumed.

The selector owns membership and cancellation validation; the New Order handler
trusts the non-cancel slot indices it receives except for its explicit slot-zero
leader check. Compatible implementations should therefore model New Order as a
swap of the current active party records, not as a rewrite of a separate
canonical companion-order table.

## 7. Search/Jimmy/Open/Get Tile Commands

The `S`, `J`, `O`, and `G` letters share one tile-interaction overlay. They are
mode-aware command handlers, not simple dispatcher stubs:

- **Overworld and town-family scenes** use the target cell in front of the party.
  The handlers run the shared reachability gate, compute the adjacent target
  from the current position plus the cached direction step, and read or rewrite
  the live map tile at that coordinate.
- **Dungeon scenes** route to smaller dungeon-specific inner handlers. Dungeon
  Get and Open act on the underfoot dungeon cell; dungeon Search and Jimmy use
  the dungeon chunk-grid representation rather than the surface/town map tile
  fetch.
- **Combat scenes** do not use this resident route. Combat has separate
  same-letter parser branches; matching labels in combat must not be assumed to
  inherit these world-mode effects.

`G` Get picks up things from the target cell. In surface/town scenes it first
scans the current map's object table for a matching pickup slot, but it does not
accept every record at that coordinate. The accepted set is limited to special
pickup-category markers and the loose-object visual family; actor, blocker,
already-handled, and unrelated object entries are skipped even if their
coordinates match. Accepted slots dispatch the slot's item code into the
inventory-add routine. If that object is a Search-surfaced Moonstone "strange
rock", the pickup grants the Moonstone and invalidates the associated Gate
Travel slot. If no accepted object slot matches, Get falls back to tile-specific
cases such as borrowing a table item, picking crops, or eating from a reachable
plate; otherwise it prints the nothing-to-get refusal. In dungeons, Get reads
the underfoot cell: closed chest cells refuse until opened, open chest cells are
consumed in the loaded dungeon image and roll the seven-row reward generator
described in `containers.md`, and unrelated cells refuse.

`J` Jimmy is the key-and-lock handler. Non-dungeon Jimmy checks key stock before
ordinary door, visible-chest, and NPC pocket rolls. Those rolls use the
selected member's lock-pick class byte against a `1..29` die; a failed roll
breaks one key. Success rewrites the lock/container state or grants the
pickpocket reward. A failed NPC pocket roll grants no reward and does not mark
the NPC picked/thanked; a target cell with no active NPC refuses without a key
loss. Per-map object chests and dungeon chests use separate formulas and key
side effects. Detailed lock-state rules live in `doors-and-z-transitions.md`.

`O` Open is the no-key counterpart. Non-dungeon Open runs the door auto-close
tracker before probing the target tile. Already-open targets acknowledge that
state, heavy targets refuse without a lock-pick roll, locked targets refuse,
openable targets snapshot their previous tile and rewrite the live cell to the
open tile, and unclassified chest-like fallthroughs are delegated to the chest
helper. Dungeon Open checks the underfoot dungeon class: door cells route to the
dungeon door opener, chest cells open, and unrelated cells refuse.

`S` Search probes for hidden objects, traps, secret features, and buried
Moonstones. In surface/town scenes, Search first runs the shared pre-search
gate and direction prompt. A failed gate or cancelled direction exits without a
map, inventory, or object-table change. A successful prompt computes the
adjacent target cell, then scans the live runtime object table for a hidden
entry at that coordinate. Multi-floor locations also require the hidden entry
to belong to the active floor/chunk. A matching hidden object prints the found
result and dispatches the object through the same inventory-add path used by
pickup/container commands.

If no hidden object is found, surface/town Search checks for a slot-indexed
treasure marker at the target coordinate. That coordinate lookup scans the
active-object table in reverse priority order and only the treasure marker
short-circuits into an immediate found-object grant. Other active-object
classes do not drive the fallback narration; Search uses the live tile byte
read before the coordinate lookup.

The live-tile fallback table supplies fixed furniture/location prefixes such
as stump, shelf, bookshelf, wall, desk, barrel, vanity, bed, dresser, trunk,
brazier, and fireplace. The hidden-door marker is the mutating case: it prints
the hidden-door result, rewrites the live tile to the revealed variant, marks
the map dirty, and stops. Otherwise, Search continues through the saved
Moonstone table, rare-reagent harvest table, and fixed hidden-treasure table
in that order; one live-tile marker skips only the Moonstone table before
continuing. Object-table, slot-indexed treasure, Moonstone, reagent, and fixed
hidden-treasure results feed their owning inventory or pickup-staging paths.
Ordinary feature descriptions are narration only. Per-map object slots that
carry trap-class metadata use a member-stat threshold roll only to choose the
visible no-trap/simple/complex/generic-trap narration, including possible
missed traps and false positives. Actual trap effects are owned by the later
trap resolver when a caller selects one.

Dungeon Search does not use the surface object-table scan. It routes to the
dungeon inner handler, which first enforces the dungeon light gate: with no
torch light and no light-spell radius, Search reports that it is too dark and
does not inspect the cell. In light, it reads the packed dungeon cell ahead of
the party and classifies by high nibble. Ordinary ladders, doors, walls, pits,
fountains, open chests, fields, and flavour objects print feature-specific
search descriptions. Chest cells use the dungeon chest trap/detail branch.
Exact pit-family Search bytes cover ordinary pit, secret-passage reveal, and
bomb detection/springing, while flavour/wall classes can rewrite only the
visit-local loaded dungeon image. Those dungeon Search rewrites are specified
in `dungeon-mode.md`. Inventory grants and chest contents belong to
`containers.md` and `catalogs/item-list.md`.

When a Search, Open, Jimmy, or container outcome selects the shared resident
trap-effect resolver, the common party damage/revive effects are specified in
`systems/traps.md`. The command layer owns routing and prompt/refusal text; the
trap spec owns the selected effect once the routing layer has chosen it.

## 8. P-Push Movable-Tile Command

P-Push is a direction-prompt command for movable map furniture and similar
objects. Escape at the direction prompt cancels silently. Before resolving the
push, the handler runs the same last-opened-door cleanup used by other
directional CMDS commands, so a previously opened door may close before the
object interaction is tested.

The command samples the adjacent source cell in the chosen direction. In
town-family and interior scenes this coordinate is relative to the avatar. In
overworld scenes the command temporarily works in the active camera-anchor
coordinate frame, then restores the party coordinate after a successful
resolution and requests a full redraw.

A source cell is pushable when either a dynamic object occupies that coordinate
or the static tile is in the known pushable set:

| Pushable tile family | Behaviour |
|---|---|
| `0x5B` | Single non-rotating pushable class. |
| `0x90..0x93` | Four-facing chair family; successful movement rewrites the facing bits. |
| `0xA5`, `0xA6`, `0xA8`, `0xA9` | Non-rotating pushable classes. |
| `0xAD..0xAF` | Non-rotating pushable run. |
| `0xB4..0xB7` | Four-facing cannon family; successful movement rewrites the facing bits. |

If neither dynamic-object presence nor the pushable static tile test accepts,
the command prints the emphatic "won't budge" refusal and exits.

The cell one tile farther in the same direction decides whether the command is
a push or a pull:

- **Push.** If the far cell has no dynamic object and its static tile is the
  expected floor/occupancy stamp for the source object family, the source object
  moves into the far cell and the source cell receives that stamp. Directional
  families are rotated to face the movement direction.
- **Pull.** If the push path is blocked but the avatar's current cell already
  carries the matching stamp, the object is dragged into the avatar's old cell
  and the source cell receives the old player-cell stamp. Directional families
  are rotated with the opposite-facing rule used for pulling.
- **Final refusal.** If neither path is legal, the command prints the shorter
  "won't budge" refusal and exits.

On any successful push or pull, the avatar advances one tile in the prompted
direction and the map is marked dirty. The command mutates the live tile buffer;
implementations should not model it as an overlay-only animation. The written
floor/occupancy stamps are visit-local for top-down location scenes: they live
in the runtime tile buffer, not in the saved top-down location files, and
ordinary location entry reloads that buffer from the static scene data. A
byte-compatible implementation should preserve the mutated live cells until the
owning map or floor is reloaded, another traced command rewrites the cells, or
temporary combat arena state is torn down. A save/load round trip does not
create a durable P-Push furniture trail for towns, castles, keeps, dwellings,
or overworld chunk windows. The generic stamp `0x44` and the cannon-family
stamp `0x45` both resolve to the same cobble description in the
LOOK2-backed tile catalog. The separate stamp byte is still load-bearing for
P-Push's family-matching rule, but it does not require a distinct public
visual label.

Combat is a supported caller of this same handler. The combat command parser
prints the `Push-` label and enters P-Push directly, without the live-actor gate
used by the combat Get/Jimmy/Open/Search prompt helper. Because combat runs with
an actor-anchor scene frame, a successful push/pull advances the currently
acting combat actor in the arena and mutates only the temporary combat tile and
object state that the combat framer later tears down.

## 9. Special Non-Letter Dispatcher Input

One translated control code that normally represents an eastward cursor/numpad
direction can reach the dispatcher in at least one path. When it does, the
dispatcher toggles the typeahead-buffer flag and prints the corresponding
Buffer On / Buffer Off message. This action does not consume a game turn.

Other direction/control codes are normally consumed by the active mode loop
before letter dispatch. Their exact mode-by-mode pre-routing belongs to
`input.md`, `overworld.md`, `town-mode.md`, and `dungeon-mode.md`.

## 10. H-Hole-Up Rest Contract

H-Hole-Up is routed by scene before the detailed rest handler runs:

- **Overworld and dungeon.** The dispatcher calls the resident rest-with-watch
  wrapper. That wrapper performs the wilderness/dungeon rest flow and can turn a
  rest interruption into an ambush-style combat.
- **Town-family locations.** The dispatcher first requires the party to be on a
  bed/inn-style tile. If the tile gate fails, the command is refused. If it
  succeeds, control enters the hours-prompt rest path.
- **Combat.** Combat has its own H label and refuses the action; world-mode rest
  is not available inside an arena.

The rest handler saves the current input mode, probes whether the current tile
allows rest, walks the party slots, prints the sleep narration, and prompts for
the number of hours when the path requires an explicit duration. Poisoned and
dead members are not treated like healthy sleepers. Sleeping party members are
restored to good status during cleanup.

Recovery is not part of this routing contract and is not a per-hour drip. The
town-bed path has no recovery block of its own at all. Only a *completed long
camp* recovers anything, and it does so once, at the end, under the guard set
and with the `1..63` hit-point roll and class-keyed magic-point rules specified
in `systems/rest-and-camp.md` section 5. An earlier revision of this section
described a "small random HP gain" with a "class-aware regeneration gate";
that was a conflation of the camp block's hit-point roll with its separate
class-keyed magic-point write, and it is withdrawn.

The town hours path advances elapsed rest with a caller-owned loop rather than
by handing the clock one large "N hours" value. It accepts one nonzero digit,
runs one bounded burst of up to sixteen schedule/world-tick passes, then
advances elapsed rest in repeated ten-minute cleanup calls until the target hour
is reached or the rest surface rejects the party. If an interruption or refusal
fires, the command stops early and hands control to the ambush/refusal path;
elapsed time already applied is not rolled back. If the duration completes, the
command prints the normal rested result and stamps the current camp/rest marker.

## 11. Y-Yell Command

Y-Yell is a mode-sensitive command with three visible families.

When the party is aboard a ship in a normal gameplay scene, Yell is a no-input
sail command. It toggles the ship between hoisted and furled sail states while
preserving heading, prints the corresponding short sail command, and does not
move the ship immediately. Wind-driven movement and X-it's under-sail refusal
remain vehicle-system behaviour; this command only changes the sail state.

When the party is not in the ship-sail branch, Yell prompts for a free-text
word of up to thirty characters using the same style of line input as the
conversation keyword path. Empty input prints the nothing-said result and
returns without a world change. Nonempty input is routed by scene context:

- **Shadowlord-name contexts.** Only the three Eternal Flame keeps — The
  Lycaeum, Empath Abbey, and Serpent's Hold — accept Shadowlord names. In one of
  those three scenes the typed word is compared with the three Shadowlord names.
  A matching name summons that Shadowlord only when all three of these hold:
  that Shadowlord's slot is not vanquished; the party's Y coordinate is at least
  `2`, so there is room two rows north of the party; and **no Shadowlord actor is
  already present in the scene** — the handler rejects the summon if any live
  active-object slot already carries the Shadowlord actor tile (`0xFC`, the
  Shadow Lord row of `catalogs/monster-bestiary.md`). That last test is a
  one-at-a-time rule, not a "table is full" rule: an engine that instead checks
  for a free slot will let the player stack Shadowlords.
  On success the handler records which Shadowlord is now active (the handshake
  the destruction path checks), installs the Shadowlord as an active object
  **exactly two cells north of the party** in the party's current floor and
  region, and plays the appearance line together with the long warble and the
  fade-in effect. The actor takes the highest free active-object slot, searching
  downward from the last slot.
  Any of the three names works in any of the three keeps; the pairing is enforced
  later by the destruction position, not here. Wrong names, any other scene, a
  vanquished Shadowlord, a party standing within one row of the north edge, or a
  Shadowlord already present all produce no effect.
- **Word-of-Power contexts.** Only the outdoor scene accepts Words of Power.
  Both world surfaces qualify, because both use the outdoor scene with the
  plane distinguished by the party's floor/depth byte. There is no
  dungeon-interior, town, or keep Word-of-Power route. The full predicate is
  given below.
- **Other contexts.** Non-ship scenes that are not accepted by either
  Shadowlord-name or Word-of-Power routing produce no effect after the prompt.

### 11.1 The Word-of-Power seal predicate

The command scans the eight dungeon Words of Power in their fixed order and
takes the first prefix match. A recognised word immediately prints the
uttered-word result and plays the shared low-rumble / full-viewport flash
presentation effect, before any location test. An unrecognised word prints the
no-effect result and nothing else happens.

After a recognised match the handler picks a direction, then checks a
coordinate, then mutates one cell:

1. **Direction.** It inspects the four cells cardinally adjacent to the party in
   the currently visible map, in the order west, south, east, north, and takes
   the first one whose tile is any of: that word's own dungeon-entrance tile,
   the sealed collapsed-entrance tile, or the ruined-shrine tile. If no
   neighbour qualifies, the command additionally prints the no-effect result and
   stops. **The party stands next to the sealed cell, never on it** — the sealed
   tile is impassable, so standing on it is not possible anyway.
2. **Ruined-shrine branch.** If the neighbour selected in step 1 is a ruined
   shrine, the handler hands off to the shrine restoration/mantra prompt for
   that word's index instead of doing anything to a dungeon entrance. This
   branch is reachable in normal play; earlier public wording that called the
   mantra-style Yell branch unreachable was wrong. `systems/karma.md` owns the
   restoration contract itself.
3. **Coordinate.** Otherwise the handler requires the selected neighbour's
   world coordinate to equal that word's published dungeon entrance coordinate
   (`catalogs/gazetteer.md` Section 5.1). Speaking a valid word anywhere else
   still produces the utterance feedback and presentation effect, but changes
   nothing. Note that the check compares only the horizontal coordinate pair, so
   the same word works at the same coordinate on either world surface.
4. **Mutation.** On a coordinate match the handler toggles the cell between the
   sealed collapsed-entrance tile and that dungeon's own entrance tile, and
   toggles that word's saved seal flag. The mutation dirties visibility so the
   changed cell is redrawn.

The per-word entrance tile is fixed data:

| Word | Dungeon | Entrance tile shown when unsealed |
|---|---|---|
| `FALLAX` | Deceit | `0x18` dungeon |
| `VILIS` | Despise | `0x16` dark cave |
| `INOPIA` | Destard | `0x16` dark cave |
| `MALUM` | Wrong | `0x18` dungeon |
| `AVIDUS` | Covetous | `0x18` dungeon |
| `INFAMA` | Shame | `0x17` abandoned mine |
| `IGNAVUS` | Hythloth | `0x17` abandoned mine |
| `VERAMOCOR` | Doom | `0x16` dark cave |

The sealed form is tile `0xDF` for all eight. Equivalently, the mutation in step
4 flips the cell by the difference between the two ids, which is why a single
rule covers all eight words.

All three unsealed variants are ordinary passable terrain; the single sealed
tile shared by all eight is impassable. `catalogs/tile-catalog.md` carries the
tile identities.

### 11.2 Seal persistence

The per-word marker is **not** scratch. Earlier public wording that called it
non-contractual bookkeeping with no live reader was wrong and is retracted.

Eight save-backed flags, one per word, record whether that word has been
spoken. They are durable state in the save image (`formats/saved-gam.md`
Section 9.1) and start clear on a new game, so **every dungeon entrance begins
sealed**. The shipped world maps always store the unsealed entrance tile; the
sealed presentation is re-derived from these flags every time a map region is
loaded into the live view. Concretely, when a map chunk is loaded, any cell
holding one of the three dungeon-entrance tiles is rewritten to the
collapsed-entrance tile if the word owning that chunk is still unspoken. The
same pass rewrites shrine cells to the ruined-shrine tile according to a
parallel set of eight saved shrine flags. The gating is per chunk, not per cell:
each word owns exactly one of the 256 map chunks, and the two rules take
opposite defaults for a chunk that owns no word or no shrine. The loader-side
statement of the rule, with those defaults, is in `formats/brit-dat.md`
Section 9.1, and it applies identically to both world surfaces
(`formats/under-dat.md`, `systems/overworld.md` Section 3).

Two consequences an implementation must honour:

- Unsealing survives save, reload, and leaving and re-entering the region. An
  engine that mutates only its live tile buffer will silently re-seal the
  dungeon when the region reloads.
- The mutation is a genuine toggle. Speaking the same word again while standing
  beside an already-open entrance clears the flag and re-seals the entrance.

## 12. Cross-References

- `input.md` describes keyboard polling, uppercase folding, direction-code
  translation, prompt reentrancy, and the handoff to this dispatcher.
- `main-loop.md` describes where the resident dispatcher sits in the four
  top-level mode loops.
- `overworld.md`, `town-mode.md`, and `dungeon-mode.md` document the mode-local
  pre-routing that happens before printable letters are forwarded.
- `combat.md` documents the separate combat command dispatcher.
- `vehicles.md`, `weather.md`, `magic.md`, `doors-and-z-transitions.md`,
  `conversation.md`, `shops.md`, `save-load.md`, `lighting.md`, and
  `catalogs/quest-graph.md` document major command families after dispatch.

## 13. Dispatcher Boundaries And Remaining Work

The resident command-dispatch contract is complete at A-Z routing depth: mode
pre-routing, scene-aware letter families, no-action fallthroughs, command
prompt ownership, typeahead toggle, save route, major CMDS/SJOG/CAST/ZSTATS
delegates, and command-family cross-references are fixed. Remaining work belongs
to per-handler return compatibility, mode-local control-code tables, and
P-Push stamp rendering, not to the resident dispatch table itself.

- **Per-handler return values.** The dispatcher-level status values are known
  well enough for loop routing, but several overlay handlers forward their own
  values. Exact numeric compatibility belongs with per-handler decomp passes.
- **Full control-code pre-routing.** The dispatcher-visible typeahead toggle is
  identified, but each mode loop has its own control-code table. These tables
  should be documented in the mode specs rather than collapsed into the
  resident command table.
- **P-Push stamp rendering.** The command writes floor/occupancy stamp tiles
  into the live map buffer. Save/load durability is bounded negatively for
  top-down location and overworld buffers. The generic `0x44` stamp and the
  cannon-family `0x45` stamp both resolve to cobble through LOOK2; the byte
  distinction remains part of P-Push's family-matching rule rather than a
  separate visual-label gap.

## 14. Sources

This cleanroom spec was derived from the private analysis notes listed below.
No decompiled code, assembly, raw address tables, or copied data strings are
reproduced here.

- The resident A-Z dispatcher, scene-aware letter routing, verb-prefix scheme,
  gem gate, save-game route, typeahead toggle, and return-value categories:
  `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The save-game handler reached by `Q`, including its prompt, save/cancel
  branches, file writes, and return-to-caller behaviour:
  `u5-decomp/functions/CAST2_OVL/0x10FE_save_game.md`.
- The overworld mode loop's pre-dispatch control-code table and separate quit
  prompt path: `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The dungeon mode loop's pre-dispatch handling of digits, sound toggle, and
  explicit exit prompt:
  `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The CMDS overlay command-family inventory and corrected F/J/O/G/S ownership:
  `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`,
  `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`,
  `u5-decomp/functions/CMDS_OVL/0x0962_cmds_fire_broadsides.md`, and
  `u5-decomp/functions/CMDS_OVL/0x0AEA_cmds_fire.md`.
- The M-family split between CMDS reagent mixing and CAST2 shrine/urn entry:
  `u5-decomp/functions/CMDS_OVL/0x1AD8_cmds_mix_reagents.md` and
  `u5-decomp/functions/CAST2_OVL/_INDEX_2026-05-08.md`.
- The New Order active-party record exchange, leader refusal, cancel paths, and
  same-slot self-swap behaviour:
  `u5-decomp/functions/CMDS_OVL/0x0DDC_cmds_new_order.md`.
- The Y-Yell sail toggle, free-text prompt, Shadowlord-name branch,
  Word-of-Power seal predicate, saved per-word seal flags and the region-load
  pass that re-applies them, and the ruined-shrine mantra hand-off:
  `u5-decomp/notes/2026-08-22_quest-world-retrace.md`,
  `u5-decomp/functions/CMDS_OVL/0x1418_cmds_yell.md`,
  `u5-decomp/functions/OUTSUBS_OVL/0x0098_outsubs_load_chunk.md`,
  `u5-decomp/functions/CMDS_OVL/0x70F2_shrine_effect.md`, and
  `u5-decomp/functions/CMDS_OVL/0x1202_cmds_meditate.md`.
- The P-Push direction prompt, pushable tile families, push/pull branch
  conditions, facing rewrite, overworld coordinate-frame side effects, and
  live-tile mutations:
  `u5-decomp/functions/CMDS_OVL/0x161A_cmds_push.md`. The non-durable
  save/load boundary for top-down live buffers also uses
  `u5-decomp/notes/system-trace_save-load.md` and
  `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The Search/Jimmy/Open/Get overlay overview and public command handlers:
  `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`,
  `u5-decomp/functions/SJOG_OVL/0x095C_sjog_search.md`,
  `u5-decomp/functions/SJOG_OVL/0x0646_sjog_search_inner.md`,
  `u5-decomp/functions/SJOG_OVL/0x02EA_sjog_search_object_handler.md`,
  `u5-decomp/functions/SJOG_OVL/0x0D4A_sjog_jimmy.md`,
  `u5-decomp/functions/SJOG_OVL/0x0C3E_sjog_jimmy_inner.md`,
  `u5-decomp/functions/SJOG_OVL/0x0BAA_sjog_object_table_action.md`,
  `u5-decomp/functions/SJOG_OVL/0x1374_sjog_open.md`, and
  `u5-decomp/functions/SJOG_OVL/0x18CE_sjog_get.md`.
- The Search coordinate-object fallback:
  `u5-decomp/functions/ULTIMA_EXE/0x3702_lookup_object_at.md`.
- Corrected entry notes for the shared Look/View and Ready/Z-stats command
  families: `u5-decomp/functions/LOOKOBJ_OVL/0x099C_lookobj_master.md`,
  `u5-decomp/functions/LOOKOBJ_OVL/0x10FC_local_view_render.md`,
  `u5-decomp/functions/ZSTATS_OVL/0x1296_ready_main.md`, and
  `u5-decomp/functions/ZSTATS_OVL/0x0A3A_zstats_main.md`.
- The CAST-owned U-Use item route:
  `u5-decomp/functions/CAST_OVL/0x1792_use_item.md`.
