# Doors and Z transitions

## 1. Overview

Almost every non-trivial cell in Ultima V's interior maps is bounded — by a wall, a door, a ladder up, a ladder down, a chasm, a vehicle. The interactions that move the party past those bounds form a small, very visible cluster: open a door, pick a lock, climb or descend, exit a vehicle, or trigger a dungeon exit. Most command paths share a common shape — verb prefix, direction prompt, tile probe, deterministic per-tile reaction — and all Z-transition paths converge on the *scene byte*, which decides which world mode is active and therefore which transition makes sense.

This spec describes that cluster: the door tile family and the J-Jimmy and O-Open commands that act on it, the K-Klimb command and the automatic-descent triggers it complements, the X-Xit vehicle command, the spell-context dungeon escape helper, and how the scene byte mediates Z transitions between overworld, town floors, dungeon levels, and the underworld.

## 2. The door tile family

Doors live in two parallel encodings — one for the surface and town tile maps, the other for the packed-nibble dungeon grid. Both distinguish *closed-and-unlocked*, *closed-and-locked*, *closed-and-magic-locked*, and *open*; both encode the lock state in adjacent tile bytes so that toggling the lock is a one-byte rewrite.

In the surface and town encoding, the relevant tile codes form four small ranges of adjacent bytes:

- **Closed door pair.** Two adjacent codes; the lower byte is magic-locked, the next is regular locked. A successful Jimmy decrements the byte by one, walking the cell down the lock-state ladder until it reaches an unlocked-and-openable form that Open then writes through to the open variant.
- **Open door.** A single code drawn as the open-door sprite. Both Jimmy and Open recognise this as already-open and consume the turn without acting. The renderer paints it identically to a passage.
- **Chest-on-floor pair.** Closeable-versus-locked, structurally identical to the door pair. Open success writes a fixed "open container" tile; Jimmy success rolls a key-pick check.
- **Pickpocketable NPC marker.** A non-rendered occupancy marker returned by the tile-probe path when the target cell is occupied by an NPC.

The dungeon grid packs the tile class into the high four bits of the cell byte and a sub-type into the low four bits. One high-nibble value identifies "heavy door"; another identifies "secret door / room trigger". The low nibble selects per-class variant — open versus closed, orientation. The dungeon Open handler matches purely on the high nibble; the dungeon Jimmy and Search handlers consult the low nibble for variant-specific narration.

A separate set of tile codes encodes *secret doors* — see § 8.

## 3. The J-Jimmy command

J-Jimmy is the engine's lockpick verb, dispatched from the A-Z router via the verb prefix `Jimmy-` and a single direction prompt. It exists for three interactions: doors, chests on the floor, and NPC pockets.

The handler's first guard is a key check: if the key inventory is zero it prints "No keys!" and returns. It then consults the scene byte; in a dungeon scene it routes to a dungeon-specific inner handler that uses the packed-nibble grid, and in overworld or town scenes it uses the active-map tile fetch.

For a non-dungeon door, the handler:

1. Prompts for which party member is picking.
2. Rolls a uniform random die against a class-derived threshold drawn from that member's class byte. If the class byte exceeds the roll, the attempt fails; otherwise it succeeds. Class correlates with dexterity in the per-character table, so this is in effect a DEX-versus-lock check. The dungeon inner variant blends the level into the threshold — deeper dungeons are harder.
3. **On success**, decrement the door's tile byte by one (one rung down the lock-state ladder), set the tile-changed dirty bit, and print "Unlocked!". A subsequent Open turns the cell into an open door.
4. **On failure**, decrement the key counter and print "Key broke!" — the key snapped. The door's tile byte is *unchanged*; the lock still stands.

For a chest, the same three steps run; success rewrites the cell to the open-container tile and dispatches into the chest-contents generator (which may yield treasure, nothing, or a trap).

For an NPC, success is a pickpocket: the engine checks that an active NPC really occupies the target cell, looks up that NPC's interaction record, clears the pending loot marker when present, grants a capped gold reward when the NPC has not already been handled, marks the NPC as picked/thanked, and prints the NPC's thanks line. Failure shares the broken-key narration used by failed lock attempts, but the traced path does not prove a key decrement or any broader NPC hostility/refusal side effect. Treat failed-pocket consequences beyond "no reward and no completion mark" as open for v1.

A handful of cases short-circuit before the roll:

- **Wrong tile class** — print "No lock!" and return.
- **No NPC at the cell** — when the tile-probe path reports the NPC occupancy marker but the active-object table reports no NPC at those coordinates, print "No one is there!".
- **Magic lock** — reject unconditionally with "Magic lock!" (no roll, no key consumed).

## 4. The O-Open command

O-Open is the lighter cousin of Jimmy: it acts only on already-unlocked doors and chests, and never consumes a key. The dispatcher prints `Open-`, prompts for direction, and then runs the Open handler. As with Jimmy, scene byte routes between a dungeon-mode inner variant (which consults the *underfoot* tile rather than the tile in front — see § 9) and a non-dungeon variant.

The non-dungeon Open handler always begins with one piece of bookkeeping: the door auto-close pass (§ 5). It then runs the shared pre-flight reachability gate, computes target coordinates, fetches the front-tile byte, and cascades:

- **Already-open door** — "It's open!" and return.
- **Too-heavy target** — "Too heavy!" and return. This is a refusal distinct
  from a locked target; Open does not try to pick or force it.
- **Locked door / chest / lockable NPC** — "Locked!" and return. Open does not pick.
- **Closed-and-unlocked door / closeable chest** — open path: snapshot the previous tile id, X, and Y into the door-close-tracker, set the tracker countdown to four, rewrite the cell to the open-container byte, set the tile-changed bit, and print "Opened!".
- **Magic-locked door** — treated as locked.
- **Anything else** — route to the chest-on-floor helper, which scans the location's per-map object table for a chest at the target cell and grants its contents (with trap-roll), prints "Trapped!", "Nothing to open!", or another container line.

Open writes the same open-container tile for both doors and closeable chest-like tiles, so a freshly opened door and a freshly opened closeable container can be visually indistinguishable in the live tile buffer. Additional refusals can still come from the chest helper or other per-map object metadata; the exact guarded/plot-controlled override semantics are not yet a v1 public contract.

## 5. The auto-close timer

Every door opened with O resets a four-byte resident block holding the previous tile, X, Y, and a countdown initialised to four. Each turn that consumes a turn decrements the countdown; when it hits zero the engine writes the previous-tile byte back to the saved cell and the door silently re-closes. The player has roughly four turns to pass through before it shuts.

Three observations:

- The block holds *one* door's state at a time. Opening a second door before the first auto-closes overwrites the saved state; the first door stays open for the rest of the visit.
- Doors closed by the auto-close pass do not re-lock — the snapshot is the unlocked closed form, not the locked form. A door the player Jimmied open and walked through stays unlocked across the visit.
- The pass is suppressed in dungeon mode; dungeon doors are toggled by Open and stay in whatever state Open last left them in until the player leaves the dungeon.

## 6. The "BOOOM!" outcome

The "BOOOM! Door destroyed!" string pair belongs not to Jimmy or Open but to the F-Fire ship-cannon handler. Firing a ship's cannon at a door (or wall) prints "BOOOM!" with the cannon's hit narration; on a hit at a door cell, the engine rewrites the cell to the open-door tile (or rubble) and prints "Door destroyed!".

Two consequences: ship-fire is a third unlock path, and it is the only one that bypasses both the magic-lock and guard-flag overrides — a magic-locked door that Jimmy refuses can still be cannon-blasted. The destruction is non-persistent across save / load: the location's tiles are reloaded from disk on every entry, so "Door destroyed!" is undone the next time the player walks back into that town.

## 7. Magic-locked doors

Some doors carry a magical lock that no key can pick — the lower byte of the door pair (§ 2). Magic-locked doors appear mostly in plot-critical locations: a sealed throne room, the entrance to a quest reward, a story-gated dungeon cell.

J-Jimmy on a magic-locked door rejects with "Magic lock!" and consumes neither a key nor a turn. The paths through are:

- **Unlock Magic** cast on the door rewrites the cell from magic-locked to plain locked; Jimmy can then pick it normally.
- **Blink** can place the caster on the cell on the far side when the destination is legal, bypassing the lock; the door stays locked but the party is past it.
- **Cannon fire** (§ 6) destroys magic-locked doors as readily as regular ones.

Magic-lock clears are sticky for the visit but revert on location reload. Plot progress that opens such a door permanently is encoded outside the tile grid — in the per-character flag table or the world flag table — and consulted on location load to walk the door's tile byte down a slot before painting.

## 8. Secret doors

Secret doors are walls that look like walls until the player searches the cell.

- **In dungeons**, a secret door is a wall cell whose low nibble carries a flag the dungeon Search handler recognises and clears. After clearing, the cell's high nibble is rewritten from "wall" to "door" and from then on it behaves like a normal heavy door.
- **In towns and dwellings**, secret doors are wall tiles flagged in the location's per-map object table. Search matches the target cell's coordinates to the table and replaces the wall tile with a normal door tile.

Search is the only way to find a secret door. Once revealed, the door responds to Open (no key needed; secret doors are always closed-but-unlocked) and to Jimmy with "No lock!". Walking into an unrevealed secret door fails the same way walking into a wall fails. Secret doors do not auto-close; once opened they stay open until the player leaves the location. Reveals are sticky for the visit but revert on location reload.

## 9. The K-Klimb command

K-Klimb is the climb / descend verb, mode-aware: the resident dispatcher routes K through one of three handlers depending on scene byte — overworld, town, or dungeon — each with its own interpretation.

**Overworld K.** On the surface and underworld planes, K is the outdoor climb verb. The handler first requires a nonzero, unresolved climbing-gear inventory byte; if the byte is zero, it prints "With what?" and exits. It then requires the party to be on foot; any vehicle state prints "On foot!" and exits. After the shared pre-action gate, it probes the target tile in the current facing direction. One target class refuses as "Impassable!", non-climbable classes refuse as "Not climbable!", and the confirmed climbable class continues. For each living party member, the handler rolls `1..30` against a per-character climb/agility-style stat byte; if the stat is lower than the roll, it prints "Fell!" and applies `1..5` fall damage to that member. Dead party members skip this risk roll. After all living members are checked, the successful path calls the resident climb/move helper with the original direction vector, advancing the party one cell without changing Z. Falling through a chasm to the underworld is a separate underfoot trigger — not a Klimb path (§ 10).

**Town K.** Inside a town, dwelling, castle, or keep, K is "climb the ladder". The handler consults the underfoot tile of the leader (or a prompted member): an up-ladder moves to the floor above, a down-ladder to the floor below, a two-way ladder prompts up-or-down. The Z change is implemented by rewriting the active floor index and reloading the tile buffer with a different 1024-byte slice from the location's per-floor pair, then re-running the per-map NPC linker so that NPCs on the new floor become visible while NPCs on the old floor are unlinked from the active-object table (their schedules continue running). X and Y are preserved; only the floor index and the surrounding 32-by-32 tile content shift. Non-ladder underfoot tiles print "Not climbable!" and consume no turn. There is no falling within a town's floor structure.

**Dungeon K.** In a dungeon scene, K reads the underfoot dungeon tile's high nibble. Three classes are climbable: up-ladder, down-ladder, two-way. Up-ladder decrements the level Z (toward the surface), down-ladder increments it, two-way prompts and follows. X and Y on the new level are the same as on the old. Climbing up while standing on the topmost level resets the scene byte to overworld, restores the party's surface position from the per-dungeon entry table, and the dungeon turn loop exits at its scene-byte epilogue check. Descending past the deepest level is rejected unless the cell is a scripted "deeper transition" — Hythloth's bottom ladder, for instance, leads into the underworld via a scene-byte-and-plane rewrite. Non-ladder cells print "Not climbable!". A handful of dungeons have *exit-dungeon* tiles — non-ladder cells the engine recognises as "kick the player straight out", handled like climbing up from Z zero.

## 10. Automatic descent: chutes, pits, and falls

Three movement events change Z without a Klimb:

- **Dungeon fall traps.** Exact bytes `0x61` and `0x69` trigger an automatic drop. Each fired step prints the pit/fall messages, increments Z by one, and lands the party at the same X and Y on the next level. The handler rewrites the loaded dungeon image as it falls: it clears marker bits on the departure cell and, when the destination byte is below the wall/door band (`< 0x90`), marks bit `0x08` in that destination cell. If the destination is another `0x61` or `0x69`, the fall repeats, so multi-level drops are vertical trap chains rather than a direct subtype-to-distance table. Bomb traps `0x62` and `0x6A` share the high-nibble family but do not change Z.
- **Overworld chasms.** Specific cells on Britannia are "fall into the underworld" triggers. Walking onto one prints "F-A-L-L-S!" and "Falling into the underworld", applies fall-damage, swaps the world plane to the underworld value, and re-initialises the active-object table. The trigger coordinates are hard-wired. Ascent from the underworld is a matter of finding one of a small fixed set of "ascend" tiles whose underfoot reaction promotes the party back to the surface at a predetermined coordinate.
- **Town and dwelling trap-doors.** A few interiors have trap-door cells in their floor (an oubliette, a basement entry); walking onto one triggers the same Z-down behaviour as a dungeon pit.

In all three cases the trigger is an *underfoot reaction*, not a command, run as part of the per-turn epilogue's tile-effect pass — the same pass that handles damage tiles, energy fields, and moongate landings.

## 11. X-Xit and dungeon escape wording

The ordinary X-Xit command is the vehicle dismount command. A separate helper in the same command overlay carries the "Escape" / "An Ex Por" dungeon-escape wording used by spell contexts. Do not treat the player's `X` key in normal dungeon mode as the dungeon escape spell; dungeon-mode `X` is routed as a refusal/no-op before any such spell helper is involved.

**Vehicle dismount.** When the party is on a horse, in a skiff, on a carpet, or aboard a ship, X-Xit dismounts. The handler searches a small radius for a valid landing tile and spawns a stand-in active-object slot for the abandoned vehicle so the player can re-board later. The narration cascade:

- "On foot!" if the party is already walking — X has nothing to do.
- "Not here!" if the surroundings cannot support the dismount.
- "horse!" / "carpet!" / "skiff!" / "ship!" — the corresponding successful dismount line.

Dismount from a damaged ship triggers an additional "DANGER: SHIP BADLY DAMAGED!" or "WARNING: NO SKIFFS ON BOARD!" narration. The party transport marker is cleared and the party leader's tile id is restored to the avatar tile.

The broader vehicle contract, including B-Board, F-Fire ship broadsides, and
parked-vehicle persistence, lives in `vehicles.md`. This section keeps X-Xit
because its command-overlay ownership sits near the dungeon escape helper and
other Z-transition wording.

**Spell-context dungeon escape helper.** A separate sub-routine in CMDS drives the dungeon escape path. When a relevant spell path invokes it inside a dungeon, the helper prints either "Escape" or one of two refusal lines ("Not here!" / "Not yet!") depending on whether the current cell allows exit. On allow, it clears the scene byte to overworld and restores the per-dungeon surface position, matching K-Klimb's level-zero exit result. The helper is also associated with the "An Ex Por" narration phrase. The exact split between the spell handlers that call it is still an open tracing item; the user-visible rule is that spell context, not a normal dungeon `X` keypress, selects this path.


## 12. Z transitions across modes

The scene byte ties everything together. The value zero is the overworld; values one through thirty-two are towns, dwellings, castles, and keeps; values from thirty-three through one-hundred-twenty-seven route through dungeon mode, with the stock dungeons occupying thirty-three through forty; values from one-hundred-twenty-eight upward are combat. Within town scenes the floor index is a separate byte; within dungeon scenes the level index is in Z.

The transitions across the major boundaries are:

- **Overworld → town / dungeon.** Enter on a fixed location coordinate sets the scene byte to the location's index and triggers entry. Town scenes seed the ground floor through their entry table; dungeon scenes load the selected dungeon record and seed the level/X/Y/facing entry state: surface entries use `(0, 1, 1)` facing east, underworld non-Doom entries use `(7, 7, 7)` facing west, and Doom uses the surface entry seed.
- **Town / dungeon → overworld.** A boundary tile (town spawn, dungeon top-floor up-ladder, exit-dungeon tile, spell-context dungeon escape helper, or total-party-wipe) clears the scene byte. The mode loop's only contract is "if the scene byte is no longer in my range, exit". Hythloth's bottom-ladder transition uses a separate path: the cell's tile byte is recognised as a scripted underworld-transition and the engine swaps both scene byte (to zero) and world plane (to underworld), depositing the party at a fixed coordinate.
- **Town floor ↔ town floor.** Klimb on a ladder cell rewrites the active floor index and reloads the tile buffer from the corresponding slice of the location's per-floor pair. The scene byte does not change. NPCs on the new floor are linked into the active-object table; NPCs on the old floor are unlinked. Quick and stateless: a single tile-buffer reload, a single NPC re-link, no save-game write.
- **Dungeon level ↔ dungeon level.** Klimb on an up-ladder, down-ladder, or two-way cell, stepping on a pit, or standing on a scripted teleport changes the level index. The new level's eight-by-eight slice of DUNGEON.DAT becomes active. The scene byte does not change.
- **Surface ↔ underworld.** Falls through a chasm and ascending tiles in the underworld toggle the world plane byte and re-initialise the active-object table. The scene byte stays at the overworld value — the underworld is part of overworld mode.
- **Any mode → combat.** A movement step onto a hostile, an encounter roll firing in the per-turn block, or a room-cell trigger inside a dungeon all swap the scene byte into the combat range. Combat saves the active-object table, reloads it with combatants from a `.CBT` arena file, and runs the combat loop; exit restores the saved table and resets the scene byte to its pre-combat value. Coordinates are preserved.

## 13. Hooks into the rest of the engine

- **Active-object table.** Vehicle dismount allocates a slot for the abandoned vehicle; `vehicles.md` owns the broader parked-vehicle persistence contract. Town floor changes re-link the NPC table. Combat enter/exit replaces and restores the table wholesale.
- **Per-turn epilogue.** Door auto-close runs from the tile-effect pass. Pit triggers, chasm triggers, and energy-field triggers run from the same pass.
- **Visibility.** Door state changes mark the dirty flag so the renderer rebuilds the visibility set. Z transitions reset visibility entirely — the new floor or level paints from scratch.
- **Save image.** Scene byte, floor or level index, party chunk-X / chunk-Y, the four-byte door-close-tracker block, and the per-character class fields that drive the lockpick roll are all persisted. Loaded saves resume mid-floor, mid-dungeon, mid-vehicle, or mid-combat.
- **Spells.** Unlock Magic clears magic locks; Blink can bypass them by movement when its destination is legal. The spell handlers live in a different overlay but write into or consult the same tile grid the door commands read.
- **Inventory.** Jimmy reads the key counter up front. Failed door and chest lock attempts decrement it; the NPC pocket failure path shares broken-key narration but does not have a confirmed key-counter decrement in the current cleanroom contract. Open does not touch inventory. Overworld Klimb reads an unresolved climbing-gear byte before it will attempt an outdoor climb.
- **Time.** Door open / close, vehicle dismount, and Klimb each consume one turn at the current mode's rate (two minutes outdoor, one minute indoor / dungeon). Jimmy attempts that reach a door, chest, or NPC outcome also consume a turn, including failed attempts.

## 14. Open questions

- **Magic-lock encoding details.** The exact tile-byte pair for magic-locked-versus-locked is observed but not formally enumerated. Whether the engine ever writes a magic-lock back into a cell at runtime (versus only reading it from disk) is unclear.
- **Lock-pick formula deltas.** The non-dungeon Jimmy uses class-byte versus a uniform die in a fixed range; the dungeon-inner Jimmy uses a level-modulated formula. Why two formulas exist for ostensibly the same action is unclear; whether the formula consults DEX directly or only the class byte is also not pinned down.
- **NPC pocket reward and failure effects.** The success path grants capped gold and marks the NPC as picked/thanked. The exact reward amount/cap parameter order and any failed-pocket NPC memory beyond refusal remain open.
- **Secret-door flag bit positions.** The dungeon-grid low-nibble flag is observed but not byte-identified. The town per-map encoding is also observed only by behaviour.
- **Auto-close-tracker multi-door interaction.** When a player opens a second door before the first auto-closes, the first stays open for the rest of the visit. Whether intentional or bug-as-feature is unclear.
- **Cannon-destroyed doors.** Whether the engine has any way to permanently destroy a door across save / load is unclear; the save image does not appear to persist tile-grid mutations.
- **Overworld Klimb gear byte.** The CMDS handler requires a nonzero inventory/gear byte before an outdoor climb. The exact item identity is unresolved; do not assume it is the magic carpet until the save layout or item-use path is pinned down.
- **Hythloth's underworld transition.** The bottom-ladder rewrite is plausible but the tile-byte identity has not been pinned down. Trap-door / chute encoding in towns is similarly observed only by behaviour.
- **X-Xit vehicle landing rules.** The "find a valid landing tile" search radius and the tile-passability table are observed only by behaviour.
- **Dungeon escape-helper spell invocation.** The dungeon escape helper is part of the command overlay but is invoked from spell contexts; the exact split between the spell handlers that call it is not fully traced.

## 15. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The J-Jimmy command's tile cascade, lock-pick roll and class-byte-versus-die formula, key consumption on failure, NPC pickpocket path, dungeon-mode routing, and the encoding of the door / chest / NPC tile pairs — derived from `u5-decomp/functions/SJOG_OVL/0x0D4A_sjog_jimmy.md` and `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`.
- The O-Open command's tile cascade, the auto-close countdown's record format and decrement, the pre-flight gate shared with Jimmy and Search, and the route to the chest-on-floor helper — derived from `u5-decomp/functions/SJOG_OVL/0x1374_sjog_open.md`.
- The S-Search command's secret-door reveal path, the per-map object table layout, and the dungeon-mode high-nibble cascade — derived from `u5-decomp/functions/SJOG_OVL/0x095C_sjog_search.md`.
- The CMDS overlay's overworld K-Klimb handler, including its gear gate, on-foot check, target-tile refusals, fall rolls, and final climb/move call — derived from `u5-decomp/functions/CMDS_OVL/0x1C20_cmds_klimb.md`.
- The CMDS overlay's X-Xit vehicle handler with its dismount-line cascade, and the separate spell-context dungeon-escape helper with its "Escape", "Not here!", "Not yet!", "An Ex Por" lines — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The mode-aware routing of K-Klimb across CMDS, TOWN, and DUNGEON overlays; the "BOOOM!" / "Door destroyed!" string association with F-Fire's ship-cannon path; and the verb-prefix scheme that the dispatcher prints before each per-letter handler — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The dungeon-tile high-nibble class table including up-ladder, down-ladder, two-way ladder, pit/trap, and heavy-door classes; the exact `0x61`/`0x69` fall-trap and `0x62`/`0x6A` bomb-trap post-action behaviour; and the dungeon Klimb's Z-axis behaviour with its level-zero exit and scripted underworld transition — derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`, local DUNGEON post-action/fall-helper analysis, and `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`.
- The town-mode floor-pair encoding and the per-location NPC re-linking on floor change — derived from `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The chasm and underworld transition encoding — derived from sibling spec `u5-spec/systems/overworld.md`.
- The active-object table contract that vehicle dismount and floor changes consult — derived from sibling spec `u5-spec/systems/active-objects.md`.
- The broader vehicle command and persistence contract — derived from sibling spec `u5-spec/systems/vehicles.md`.
- The world-clock advance contract that doors, climb, and dismount each consume — derived from sibling spec `u5-spec/systems/time.md`.
