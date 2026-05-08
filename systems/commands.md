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
  typeahead toggle described in Section 7.
- Function-key remap codes are not part of the resident A-Z command table.
  Mode loops or menu-specific prompts should consume or ignore them before
  falling through to letter dispatch.

Scene routing uses the resident scene byte:

| Scene byte range | Dispatcher meaning |
|---:|---|
| `0` | Overworld branch. |
| `1..32` | Town/dwelling/castle/keep branch. |
| `33..127` | Dungeon branch when the dungeon mode loop forwards a letter. |
| `128..255` | Combat range; not a normal caller of this dispatcher. |

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
| `H` | Hole up / rest. | Overworld and dungeon use the rest-with-watch path. Town mode uses the inn/bed-hours path and refuses off bed tiles. |
| `I` | Ignite. | Routes to the torch-lighting handler. It consumes one torch if available and then sets or extends the torch duration as described in `lighting.md`. |
| `J` | Jimmy. | Routes to the lockpick handler for doors, chests, and pickpocket-like cases. |
| `K` | Klimb. | Mode-aware: overworld, town-family locations, and dungeons each have their own climb/Z-transition handler; the gear gate, on-foot check, ladder cases, and dungeon level rules are specified in `doors-and-z-transitions.md`. |
| `L` | Look. | Dungeon scenes route to DNGLOOK. Overworld and town-family scenes route to LOOKOBJ and `LOOK2.DAT`. |
| `M` | Mix / shrine-command family. | Routes into the reagent-mixing command family; shrine meditation is a special handler reached from this command family when the party is at a valid shrine. |
| `N` | New order. | Routes to the party-order swap handler. |
| `O` | Open. | Routes to the Open handler for doors, chests, and dungeon underfoot cases. |
| `P` | Push. | Refuses in dungeons; otherwise routes to the push/movable-tile handler. |
| `Q` | Save game. | Routes to the save-game handler, which prompts whether to save. On `N`, it returns without writing. On `Y`, it writes the save files, acknowledges completion, and returns to the caller. This letter is not the DOS-terminate path by itself. |
| `R` | Ready. | Routes to the equipment-ready handler in the status/equipment overlay. |
| `S` | Search. | Routes to the Search handler, including secret-door and searchable-object paths. |
| `T` | Talk. | Town-family scenes route to the conversation engine. Overworld and dungeon scenes refuse; the overworld path may still prompt for a direction before printing its refusal. |
| `U` | Use. | Routes to the item-use handler. The implementation lives with the spell/item overlays rather than in the command dispatcher. |
| `V` | View / gem. | The dispatcher checks gem count first. If none remain, it prints the no-gem refusal. Otherwise it decrements the count and routes to LOOKOBJ for overworld/town view or DNGLOOK for dungeon view. |
| `W` | Default refusal. | No resident world-command handler is currently confirmed; it falls through to the stock "What?" response when it reaches this dispatcher. |
| `X` | X-it. | Routes to the vehicle-exit/dismount handler. Ordinary dungeon `X` is a refusal/no-op; spell contexts may call a separate dungeon-escape helper that shares the escape wording. |
| `Y` | Yell. | Routes to the Yell handler. Shipboard Y toggles sails as specified in `vehicles.md` and `weather.md`; non-ship branches handle words of power and Shadowlord-name effects. |
| `Z` | Z-stats. | Routes to the character/status display overlay. |

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

## 6. Search/Jimmy/Open/Get Tile Commands

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
the underfoot cell: unopened doors refuse, chest cells roll contents across the
chest-content categories, and unrelated cells refuse.

`J` Jimmy is the key-and-lock handler. It refuses immediately when the key stock
is empty. Non-dungeon Jimmy handles locked doors, floor chests, and NPC pocket
cases from the target cell: success rewrites the lock/container state or grants
the pickpocket reward, while door and chest failures can break a key. The NPC
pocket failure path shares the broken-key narration, but the traced public
contract is only that no reward is granted and the pocket-completion state is
not advanced. Dungeon Jimmy uses the dungeon grid variant and shorter
dungeon-specific door/chest outcomes. Detailed lock-state rules live in
`doors-and-z-transitions.md`.

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

If no hidden object is found, surface/town Search checks the saved Moonstone
slots for a valid buried slot at the target coordinate. A matching Moonstone
slot creates a visible "strange rock" pickup tagged with that slot; if several
slots share the same coordinate, the highest-numbered matching slot is
considered first, and Search does not duplicate a rock for a slot that is
already surfaced. After object and Moonstone misses, the handler falls back to
resident trap and tile classification: treasure-like, door/wall/feature,
field, pit, fountain, bomb-trap, poison-gas, sleep-field, and empty searches
produce their feature-specific results. Object-table and treasure results feed
the inventory-add path; ordinary feature descriptions are narration only; and
the mutating fallback cases are live-tile effects such as hidden-door reveal,
bomb-trap clearing, and chest-related helper outcomes. Dungeon Search does not
use the surface object-table scan; it routes to the dungeon inner handler, which
reads the packed dungeon cell class/subtype and prints the corresponding
feature-specific search result. The secret-door reveal contract belongs to
`doors-and-z-transitions.md`; inventory grants and chest contents belong to
`containers.md` and `catalogs/item-list.md`.

## 7. Special Non-Letter Dispatcher Input

One translated control code that normally represents an eastward cursor/numpad
direction can reach the dispatcher in at least one path. When it does, the
dispatcher toggles the typeahead-buffer flag and prints the corresponding
Buffer On / Buffer Off message. This action does not consume a game turn.

Other direction/control codes are normally consumed by the active mode loop
before letter dispatch. Their exact mode-by-mode pre-routing belongs to
`input.md`, `overworld.md`, `town-mode.md`, and `dungeon-mode.md`.

## 8. Cross-References

- `input.md` describes keyboard polling, uppercase folding, direction-code
  translation, prompt reentrancy, and the handoff to this dispatcher.
- `main-loop.md` describes where the resident dispatcher sits in the four
  top-level mode loops.
- `overworld.md`, `town-mode.md`, and `dungeon-mode.md` document the mode-local
  pre-routing that happens before printable letters are forwarded.
- `combat.md` documents the separate combat command dispatcher.
- `vehicles.md`, `magic.md`, `doors-and-z-transitions.md`,
  `conversation.md`, `shops.md`, `save-load.md`, `lighting.md`, and
  `weather.md` document major command families after dispatch.

## 9. Open Questions

- **Per-handler return values.** The dispatcher-level status values are known
  well enough for loop routing, but several overlay handlers forward their own
  values. Exact numeric compatibility belongs with per-handler decomp passes.
- **Full control-code pre-routing.** The dispatcher-visible typeahead toggle is
  identified, but each mode loop has its own control-code table. These tables
  should be documented in the mode specs rather than collapsed into the
  resident command table.
- **M command shrine split.** Public behaviour supports both reagent mixing and
  shrine meditation through the command family, but the precise branch point
  between CMDS and CAST2 should be traced further.
- **Search trap classification.** Search's surface/town fallback distinguishes
  several trap and feature classes, including bomb-trap tile replacement, but
  the exact trap-kind table and difficulty formulas remain with the container
  trap work.

## 10. Sources

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
- The Search/Jimmy/Open/Get overlay overview and public command handlers:
  `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`,
  `u5-decomp/functions/SJOG_OVL/0x095C_sjog_search.md`,
  `u5-decomp/functions/SJOG_OVL/0x0D4A_sjog_jimmy.md`,
  `u5-decomp/functions/SJOG_OVL/0x1374_sjog_open.md`, and
  `u5-decomp/functions/SJOG_OVL/0x18CE_sjog_get.md`.
