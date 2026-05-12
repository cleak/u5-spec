# Combat

## 1. Overview

Ultima V's combat system is a turn-based, party-versus-monsters tactical mode that plays out on a small fixed-size arena grid. When a world-mode loop (overworld, town, or dungeon) triggers a fight, the engine suspends what it was doing, swaps the on-screen scene for an arena, populates the arena with the player's party at one set of fixed entry points and a randomised set of monsters at another, and runs a self-contained round loop until one side is wiped out or the player flees. When the loop returns, the engine restores the suspended world state — player position, the dynamic-objects table, the scene byte — and returns control to the calling mode loop with the fight's after-effects baked in: damage taken, characters dead or asleep, time advanced by the round loop, and resources consumed by combat actions.

Combat is "inside-out" — the world freezes while the fight plays through, the fight has its own table of actors, its own per-letter command dispatch, its own AI, and its own arena terrain — and then the function call returns and the world resumes exactly where it left off. The mode-loops above combat are unaware that combat happened beyond the visible state changes.

This spec describes the combat trigger framing, the arena format and monster placement, the per-round walk over the actor table, the player command set, the monster AI, the attack-resolution primitive, the damage and status model, and integration points with text output, the spell system, and time.

## 2. Combat triggers

Combat enters from one entry point — a single function call from a world mode loop that takes three parameters: a flags word, an actor-slot index, and an entry-mode bitfield. The entry-mode bitfield distinguishes three families of fight:

**Terrain combat.** The default. Reached when the player walks into (or attacks) a hostile creature on the overworld. The dynamic-objects-table slot of the offending creature is passed along; its tile class picks one of sixteen outdoor arenas via a small linear formula in the tile-class range. The terrain-combat setup chooses the arena, sets up the monster spawn count, and places each monster at one of a fixed set of arrival positions.

**Ambush combat.** Reached from town/dwelling/castle/keep mode-loops when a hostile NPC initiates a fight, and from a small handful of overworld scripted-encounter tiles. Has a different setup helper that places monsters at randomised arena positions rather than fixed ones.

**Scripted / "alternate" combat.** Reached from a small set of scripted-event triggers — most prominently the duel with Lord Blackthorn near the endgame. The handler is allowed to *cancel* the fight by returning a non-zero predicate; on cancel, the framer skips the round loop entirely and returns to the caller as if the fight never happened. Used for fights whose outcome is deterministic at trigger time.

Once one of the three setup paths has prepared the arena, the framer clears a few combat-state bytes and calls into the round loop. On return — whether via victory, defeat, or escape — the framer runs the teardown described in Section 4.

## 3. The arena

A combat arena is a rectangle of terrain tiles plus a band of metadata describing where actors enter and which terrain pieces hold special meaning (spawn points, hazards, ladders). Two on-disk files hold the engine's full set of arenas: a bank of sixteen outdoor arenas keyed by overworld terrain class (each tied to a tile family — grass, forest, hills, swamp), and a much larger bank of dungeon-encounter arenas (one hundred twelve records).

Each arena occupies a fixed-size record. The first part is the **terrain grid** — an eleven-by-eleven array of tile bytes describing the arena floor. The remainder is the **placement metadata band** — a flat run of bytes per row that the engine reads at setup to decide how the arena is populated. The band identifies valid party-arrival cells, valid monster-arrival cells, and cells containing hazards. The arena format spec covers the byte-by-byte layout; from combat's perspective the contract is "given an arena ID, the on-disk record tells us a 121-cell terrain grid and a placement plan."

When the arena loads, its terrain grid is copied into a runtime grid in the data segment with a row stride padded out to thirty-two bytes (a power-of-two stride that lets the renderer index by `(row << 5) + col`). Movement and visibility consult this runtime grid; the on-disk record is not touched again until the next combat enters.

**Wall tiles** in the runtime grid are recognised by the round loop as impassable. An actor whose record places it on a wall tile is silently skipped for the round; this corner case is a defensive guard since proper monster placement keeps actors on walkable cells.

**Entry-and-exit edges.** Some of the arena's four edges are valid "leave-combat" edges; an actor (typically the player) that walks off such an edge triggers the flee path. Non-exit edges are treated as walls. Which edge is which is encoded in the placement metadata; for dungeon-encounter arenas, only the edge through which the party arrived is open.

## 4. Combat enter/exit framing

The framing function bridges the world-mode loop and the combat round loop. It must save and restore enough state that the calling mode loop is unaware combat happened.

**Save phase (before round loop).**
- Snapshot the player's world coordinates (X, Y, Z), the active-player byte, and the *scene byte* — the same scene byte the input system uses to choose between idle and prompt mode and the time system uses to choose between full-darkness and time-of-day daylight.
- Set the scene byte to a combat sentinel value, so any concurrent system that reads it knows combat is in progress.
- **Snapshot the entire 32-record dynamic-objects table** into a backup region. The table holds the world's monsters, NPCs, ships, horses, and other moveable entities; combat will overwrite it with its own actors.
- Run one of the three setup paths (terrain / ambush / scripted) to populate the table with combat actors.
- Clear the combat-state bytes the round loop expects on entry.

**Round loop.** Section 7 describes what runs inside.

**Restore phase (after round loop).**
- If a "post-combat trap" flag was raised inside the loop (typically by a monster's death triggering a tile effect — chest explosions, lava pools, gas clouds), invoke the trap handler before redrawing.
- Restore the player's coordinates and the scene byte from the saved slots.
- Mark visibility dirty so the next world frame redraws fully, and refresh the on-screen party-stats panel.
- Restore the active-player slot — but only if the pre-combat active player has not died or fallen asleep during the fight; if their status is now `'D'` (dead) or `'S'` (asleep), keep the active-player slot cleared and let the player re-select.
- Inverse-copy the dynamic-objects table from its backup, restoring the world's monsters, NPCs, ships, horses exactly as they were before the fight.

The overall effect is "combat is a function call." From the calling mode loop's perspective, control left for combat and came back with the world unchanged except for damage, deaths, and clock advance.

## 5. Monster placement

Once the framer has decided which arena to load, the setup helper picks a monster count, picks a tile per monster, and writes one record per spawned monster into the actor table. The flow is the same for terrain and ambush combat, with a single switch deciding whether arrival positions are deterministic or shuffled.

**Counting monsters.** The engine consults a per-arena spawn-count byte from a small data-segment table. Three values are treated as exact counts and used unchanged: one, eight, and sixteen. Any other value is treated as a maximum: the actual count is rolled to a uniform integer in `[1, max]`. A "double-encounter" world flag, when set, re-rolls the count once more (taking the second roll); this corresponds to the "fortunes-of-war" mechanic that occasionally produces unusually large fights. The final count is capped at twenty-six.

A "town-style override" applies before the lookup: if combat was triggered while the player was inside a town/dwelling/castle/keep on a regular surface arena, the count is forced to one. This is the case where a hostile NPC pulls a weapon — a single attacker, not a wilderness pack.

A short combat banner ("CONFLICT") is printed at the start of setup, before any monsters are placed.

**Picking arrival positions.** Each monster gets one of sixteen pre-defined arena cells, indexed by a placement slot. For terrain combat, slots are walked in identity order so placements are deterministic per arena. For ambush combat, the placement slots are shuffled by a Fisher-Yates pass first. The sixteen slots' (X, Y) coordinates live in two flat sixteen-byte tables in the data segment.

**Picking tiles per monster.** The first monster always uses the arena's signature tile class (the class derived from the triggering creature's tile). Subsequent monsters fall into two groups by index: the first `count / 4 + 1` are **leaders** and get the per-arena "leader replacement" tile from a separate per-arena table; the rest are **followers** and reuse the original arena tile. A side-channel predicate suppresses the leader override in some arena classes (underworld, certain unique-creature encounters), in which case all monsters spawn as the same class.

Placement initialises two linked records per monster. The renderer-facing active-object record receives the chosen tile and arena coordinates. The parallel combat-effect descriptor receives the class-derived base-step, phase counter, target/owner field, coordinates used by the round walker, and the appropriate flag bits. The placement helper returns when all monsters are written.

## 6. The actor table

Combat treats every actor — every party member, every monster, every summoned creature, every dynamic object that exists during the fight — as a slot in a fixed-size **actor table** of thirty-two slots. The first six slots are reserved for party members 0–5 (heroes, in party-roster order); the rest are used for monsters, summons, and any divisions or replications produced during the fight.

Each slot is a small fixed-size record carrying:

- **Current HP** (for monsters), or a link to the character record's HP word (for party members).
- **A "base-step" value** that determines how often this actor acts. Lower base-step means faster turns; the engine derives a phase counter from `(constant - base_step)` and decrements it each round, acting on zero (Section 7).
- **A phase counter**, decremented each round; the actor acts when it reaches zero.
- **Flag bits** describing the actor's state: "alive and active", "marked dead this round", "currently casting a spell", "fleeing", "invisible/not-yet-revealed", plus several monster-class-specific bits.
- **A target/owner index** — for party members, the linked character record index (0–5); for monsters, the slot the actor is currently targeting.
- **A class byte** — the tile family the actor belongs to. Used as the index into the per-monster-type tables (Section 13).
- **The actor's (X, Y) coordinates** on the eleven-by-eleven arena.

When an actor dies, the "marked dead" bit is set; when a slot is freed completely (a vanishing monster or a fled character), the record is cleared to all zeros and the slot becomes available for re-allocation.

A second, parallel table — the dynamic-objects table that combat overlays onto the world's normal table — holds the same actors indexed by class for purposes the renderer cares about. The two tables are kept in sync by the step-or-attack primitive (Section 11): when an actor moves, its (X, Y) is written into both.

Spell effects that create or duplicate actors allocate records in both tables.
Clone copies the accepted target's combat actor record and its linked
dynamic-object record, relinks the new combat record to the new dynamic-object
slot, and then places the copy at a random legal arena coordinate. Clone needs
one free slot in each table before it copies either record; if either table is
full, no partial clone is written. The original handler does not initialize its
spell-result word on this capacity-failure exit, so exact bug compatibility may
preserve an undefined success/failure narration result. A deterministic
reimplementation should treat that case as a no-op failure unless deliberately
emulating stack-state leakage. Clone does not try to place the copy adjacent to
the original target. The placement coordinate is accepted only after the same
combat placement probe agrees that the cell can hold the cloned actor.

## 7. Per-round structure

Each round is one walk over the thirty-two-slot actor table. The round loop has start-of-round setup, a per-actor body that runs zero or one times per slot, and end-of-round exit checks. When the body has visited all thirty-two slots, the round restarts (unless an exit fires).

**Start-of-round setup.** A small bundle of housekeeping work: screen redraw, combat-begin overlay refresh, screen flush, per-round init that resets per-slot scratch state, and clearing the "any spell cast this round" flag.

**Per-actor body.** For each slot 0–31:

1. **Skip empty slots and slots already marked dead.** The "alive" flag and "marked dead" flag bits gate this.
2. **Sweep deaths from prior rounds.** If the slot is alive but its linked character record's status byte is now `'D'`, mark the slot dead, fire a death-narration effect, and advance to the next slot. This catches party members who died between rounds (poison, ongoing spells).
3. **Skip wall-cell slots.** A defensive guard against bad placement.
4. **Decrement the actor's phase counter.** While non-zero, the slot does not act this round. When it reaches zero, the actor *does* act.
5. **On zero, refresh the counter and act.** The counter is reset to `(constant − base_step)`. A round-counter at the table level is incremented and wrapped at ten; on every wrap, the engine fires a tile-render pass for animation.
6. **Dispatch the actor's turn.** A single function asks "is this slot a player or a monster?" — for a player, control passes to the player command handler (Section 8); for a monster, to the AI-then-command handler that runs the AI synthesis path before falling into the same dispatch (Section 9).
7. **Mark the slot acted, run the post-action render.** Redraws changed cells and runs any post-action sound or particle effect. Death narration runs here when relevant.

**End-of-round exit checks.** Three flags control exit:

- **Defeat flag**: the entire party is dead, asleep, or fled. Result is "defeat".
- **Leave-combat flag**: the player has chosen to leave by walking off an open edge, a spell or tile effect has ended combat, or the combat-only X-it cleanup path has accepted after no live foes remain. On the *first* such trigger per fight, the exit-message string is printed; subsequent reads pass through silently.
- **Exhausted slots** (loop reached slot 32): start a new round.

When defeat or leave-combat fires, the round loop returns "1" (victory/escape) or "0" (defeat).

The phase-counter / base-step structure means actors act at *staggered* paces. There is no "player turn then monster turn" — initiative is *interleaved* by phase counter, so a fast monster might act twice between the player's turns.

## 8. Player commands in combat

When the round walker dispatches a player slot, the player command handler normally reads exactly one keystroke from the input pipeline (using the same input system that drives the rest of the engine). If Quickness's shared `Q` active-effect tag is live, that handler first rolls an inclusive 0..1 random gate: a zero result consumes the ready dispatch without reading input, while a one result continues normally. When input is read, the keystroke is folded to upper case, case-checked against the combat command set, and dispatched.

The combat command set consists of letter keys A-Z plus a small set of control codes (Escape, Ctrl-S, Space, digits, direction codes). Dispatcher-level coverage is complete for all twenty-six letters and the special inputs listed below. Recognition is not the same as world-mode success: several letter branches print the familiar verb label and then run the combat scene-message/abort tail, while others enter shared command overlays through combat-specific stubs. The public map below names those overlay targets where they are resolved; object-specific success and refusal cases remain with the command-family specs.

| Key   | Combat behaviour |
|-------|------------------|
| **A** | Attack. Prompts for a direction key, then runs the step-or-attack primitive (Section 11). |
| **B** | Recognised as Board, then routed to the combat scene-message/abort tail. |
| **C** | Cast a spell through the combat spell path (Section 10). |
| **D** | Prints the combat-specific `D-What?` refusal and aborts the command. |
| **E** | Recognised as Enter, then routed to the combat scene-message/abort tail. |
| **F** | Recognised as Fire, then routed to the combat scene-message/abort tail. |
| **G** | Get. Prints `Get-`, gates on the active combat actor still being alive, then dispatches through the shared SJOG Get handler and returns to the combat parser for any follow-up input. |
| **H** | Recognised as Hole up, then routed to the combat scene-message/abort tail. |
| **I** | Recognised as Ignite torch, then routed to the combat scene-message/abort tail; no torch counter update is proven on this combat branch. |
| **J** | Jimmy. Prints `Jimmy-`, applies the same live-actor gate as Get, then dispatches through the shared SJOG Jimmy handler. |
| **K** | Klimb. Dispatches to the SJOG combat Klimb helper. It handles ladder up/down prompts, upward/downward combat exit attempts, and a limited in-arena climb/move case that mutates the active combat record; otherwise it prints a refusal. |
| **L** | Recognised as Look, then routed to the combat scene-message/abort tail; this dispatcher does not run the world/town LOOKOBJ flow. |
| **M** | Recognised as Mix, then routed to the combat scene-message/abort tail; it does not open the reagent mixer. |
| **N** | Recognised as New order, then routed to the combat scene-message/abort tail. |
| **O** | Open. Prints `Open-`, applies the same live-actor gate as Get, then dispatches through the shared SJOG Open handler. |
| **P** | Push. Prints `Push-` and dispatches through the push/refusal helper path; exact pushable-object effects are the shared P-Push command behaviour rather than a combat-only table. |
| **Q** | Recognised as combat Quit, then routed to the combat scene-message/abort tail. It is not the resident Q save-game command and does not save. |
| **R** | Ready. Dispatches to the ZSTATS R-Ready handler. In combat, the character picker reuses the active combat actor instead of prompting for an arbitrary party member; equipment mutation semantics are specified in `inventory.md`. |
| **S** | Search. Prints `Search-`, applies the same live-actor gate as Get, then dispatches through the shared SJOG Search handler. |
| **T** | Recognised as Talk, then routed to the combat scene-message/abort tail. |
| **U** | Use item. Prints `Use item`, applies the same live-actor gate as the prompt-with-string commands, and dispatches through the sixth combat sub-verb slot. The continuation crosses into CAST-owned command/item logic, but current evidence does not yet settle the exact combat item-effect body. |
| **V** | Recognised as View, then routed to the combat scene-message/abort tail; it is not the resident gem-view map path. |
| **W** | Prints the combat-specific `W-What?` refusal and aborts the command. |
| **X** | X-it. Calls the combat-only CMDS escape handler. The command succeeds only when no active-not-dead foes remain; otherwise it prints a combat refusal. Fleeing while enemies remain is handled by stepping out of arena bounds, not by this branch. |
| **Y** | Yell. Dispatches to the CMDS Yell handler, reusing the normal ship-sail, Shadowlord-name, and word-of-power logic for the current scene. |
| **Z** | Z-stats. Dispatches to the ZSTATS display handler; in combat it selects the active combat actor's party slot instead of prompting for an arbitrary character. |

Other inputs:

- **Space** — pass / wait one phase.
- **Escape** — abort whichever multi-stage prompt is active.
- **Ctrl-S** — toggle music.
- **Digit `0`** — clear the active-player selection.
- **Digits `1`–`6`** — select party member 1 through 6 as the active player.
- **Direction codes** (the eight movement codes the input system translates from numpad / arrow keys) — move one cell in the given direction. Movement uses the step-or-attack primitive: if the cell is occupied by a hostile, attack instead; if it is on the open edge, leave combat.

Several commands are **multi-stage** (Attack, Cast, Get, Jimmy, Open, Ready, Search, Use, Yell, and some delegated arena handlers): they print a short prompt or call a sub-handler that reads a follow-up keystroke. The combat command handler's dispatch is structured so multi-stage commands return control to the same handler for their continuation rather than recursing through the round walker. The command set mirrors the world mode loops' visible vocabulary so muscle memory transfers cleanly between play modes, but the combat parser owns its own branches and refusals. The most distinctive combat-only paths are Attack, Cast, active-player selection, out-of-bounds fleeing, and the X-it cleanup exit.

## 9. Monster AI

When the round walker dispatches a monster slot, the AI runs as a sequence of three passes that ultimately produce a *synthesised keystroke* — the AI generates the same bytes the player would press if they were controlling this monster, and the synthesised byte runs through the same per-letter dispatcher as a player turn. Monsters and players share the action infrastructure.

**Pass 1 - Dispatch setup.** The per-actor dispatcher clears the actor's
combat-status presentation area, prepares narration scratch, and checks whether
the current slot should run a normal turn, yield to a queued animation/effect,
or continue into AI decision-making. Current evidence does not support a
general per-class AI script runner. The ordinary monster path is table and
helper driven: status/flee gates run first, then the class-flag special hook,
target selection, movement-direction synthesis, optional step/teleport logic,
and finally the same command parser used by player turns.

**Pass 2 - Per-class special ability hook and direction.** Before ordinary
movement is synthesized, monster AI runs a small class-flag hook. It is not a
general script runner: it reads the acting monster's class flag word and tests
three ability bits in fixed order.

- `0x0040` is the possess/charm-on-turn ability. It chooses a random combat
  slot, accepts only a living party member that is not dead/passive, blinking,
  status-disabled, invisible, or already in the active command state, then runs
  the normal resistance check. On a failed resistance roll the target is marked
  controlled for the current combat state, the active-player sentinel is cleared
  if needed, the stats panel is redrawn, and a short possession narration and
  sound play. If the caster is a Daemon-class actor, the caster then clears
  itself from combat. Once a valid target reaches the resistance path, the hook
  returns handled whether the resistance blocks or the effect lands.
- `0x0800` is the blink/phase ability. It has an approximately one-in-eight
  chance per AI turn, toggles the actor's phase/hidden flag and linked visual
  tile between visible and hidden, and narrates the disappearance or return.
- `0x0400` is the summon-daemon ability. It has the same approximately
  one-in-eight chance gate, requires the combat-side live-target and placement
  helpers to accept, then attempts to place a Daemon-class actor near the
  current AI step direction with a brief visual transition and sound.

The branches are tested in the order above; a class with multiple bits would
attempt possess first, then blink, then summon-daemon. In the analyzed v1 data
set, only the possess bit is assigned to listed classes; the blink and summon
branches remain variant-data behaviours until an asset table sets those bits.
After this hook, the AI target picker and direction synthesis run as normal.

**Target selection** is the heart of Pass 2. Given the acting monster's slot index, the target picker walks the actor table backwards from slot 31 to slot 0, computes the squared distance to each candidate, and picks the closest one that survives a chain of filters:

- Not the acting monster itself.
- Slot is not empty and not marked dead.
- Not on the same *faction* — friend/foe is decided by a "slot-to-group" helper that maps each slot to a faction id; party members are one faction, monsters typically a single hostile faction, with a third "neutral" faction for some monster types.
- Not in a suppressed phase/hidden state, except that one saved-combat scene
  family and one special monster class bypass this extra suppression filter.
  The public labels for that scene and class-specific exception remain open,
  but the exception is separate from ordinary invisibility.
- Visible to the acting monster: the "invisible / not-yet-revealed" flag is
  still rejected after the phase/hidden check. This ordinary invisibility
  filter is not the same as the special suppression-filter bypass above.

When Mass Charm is active, the same target picker first checks the shared
active-effect tag for `C`. It resolves the acting monster's class charm
threshold from the per-class combat record, then rolls one uniform random byte
in `[0, 255]`. If the roll is strictly greater than the threshold, the acting
monster's faction for this target pick is forced to neutral group 0 before the
filter above runs; otherwise the monster keeps its normal faction. This does not
mark individual actors as charmed; it changes which candidates survive the
normal same-faction filter for the current AI decision. For a threshold `T`, the
remap chance is `(255 - T) / 256` for `0 <= T <= 255`; the current class
thresholds are catalogued in `catalogs/monster-bestiary.md`.

The target's distance is consulted via the same precomputed squared-distance table used by the 2D visibility post-pass. Each eleven-by-eleven arena coordinate is folded around centre cell five (`folded = min(coord, 10 - coord)`), and the table returns `(5 - folded_x)^2 + (5 - folded_y)^2`. The table is therefore reflection-symmetric about the centre cell of the arena. Backwards walk plus strict less-than comparison means *the lowest-numbered slot among candidates of equal distance wins*, biasing toward party members (low slots) when distances tie.

The target scan also tracks whether any of the first five party slots survived
the filters. If no target and no counted party member survive, the AI asks the
per-turn cleanup/effect helper for a fallback target. If that still leaves no
usable target, the original moves toward the centre of the eleven-by-eleven
arena and marks pending-action monster slots for follow-up. Slot 5 still
participates in the normal closest-target competition when it survives the
filters, but by itself it does not suppress this no-party fallback.

**Step direction.** Once a target or fallback point is picked, the unit-step
vector is the per-axis sign of `(target - self)`: each component is `-1`, `0`,
or `+1`. If the acting monster's "fleeing" flag is set, both axes are negated
— the monster moves *away* from the target or fallback point. The no-target
centre fallback therefore moves actors toward the centre unless they are
already aligned with it.

The confirmed public writer for the fleeing flag is the Cause Fear spell: it
sweeps eligible hostile combat actors and marks each accepted target as fleeing.
Other possible writers, such as low-HP morale or other class-specific
decisions, remain unclassified. The decoded possess/blink/summon-daemon hook
does not write the fleeing flag.

**Pass 3 — Synthesise.** A combat-specific input gate reads the synthesised byte from the actor's record. The AI's chosen direction is encoded as the byte the player would press if they wanted to walk the same way (`'N'`, `'S'`, `'E'`, `'W'` direction codes), or the byte for "Attack" if the chosen direction puts the target adjacent. The byte falls into the same per-letter dispatcher as the player command handler. Before the command runs, the AI assembles a one-line narration string — for example `<monster name> attacks <target name>, armed with <weapon>!` — by stitching together a short verb composer.

The architectural consequence: **all damage and movement effects in combat go through the same primitive, regardless of whether the actor is a player or a monster.** Section 11 describes that primitive.

## 10. Spells in combat (summary)

Combat shares the spell engine with the rest of the game; the C (Cast) command dispatches via the same routing as the overworld C. The combat-specific path adds three things.

**Interference and active-effect checks.** Before queueing a spell, combat runs
an interference check, not a resource gate. It reads the caster's current target
mapping; if that target exists, is a valid live/visible/awake actor, Time Stop's
`T` runtime tag is not active, and the target is at distance one from the caster,
the handler prints a newline, the target's actor name, and ` interferes!`, then
returns to combat command input before the shared spell dispatcher prompts for a
spell. If any of those conditions fail, combat proceeds to the shared spell
dispatcher. The charge, mana, level, and scene checks are still owned by that
dispatcher. The combat C-Cast path also checks the shared active-effect tag:
when Negate Magic's `N` tag is active, the cast is absorbed/refused before the
shared spell dispatcher consumes charge or MP.

**Scene gate.** Each spell carries a four-bit allow-mask for the scenes it works in: combat, dungeon, indoor/town-mode, and overworld. Scenes for which the spell has no entry print a `Not here!` refusal. Most damaging spells are gated to combat-only.

**Charge and MP debit.** The spell's MP cost is `(spell_id / 6) + 1` - eight circles of six spells each. The pre-mixed charge counter for that spell is decremented before MP and level validation. If MP is too low, the charge is not refunded; if the caster's level is too low, both charge and mana are spent. The spell-effect handler runs only after these gates pass.

The full spell system is described in its own spec; only the combat-side gating
and dispatch are covered here. Monster turns use AI command synthesis before
they enter the shared combat parser. The class-flag special hook is now bounded
to possess, blink/phase, and summon-daemon branches before movement synthesis.
Those effects do not route through the party spell prompt, party reagents,
premixed charges, MP, or player circle gates.

## 11. Attack resolution

Movement and attack share a single primitive, called once per actor turn. The primitive takes a direction code (1 = west, 2 = east, 3 = north, 4 = south, the same mapping the world-mode-loops use) and the actor's slot index:

1. **Translate direction to a unit step.** Cardinals map to `(dx, dy)` of `(±1, 0)` or `(0, ±1)`. A direction code of zero or out of range produces `(0, 0)` — "attack in place".
2. **Print the direction word** ("North", "South", "East", or "West") followed by a newline. Movement narration is part of the primitive.
3. **Range-check the destination.** `(new_x, new_y) = (self_x + dx, self_y + dy)` must fall in `[0, 10]`. If off the arena, route to the out-of-bounds handler — for an actor stepping off an open edge, this triggers the leave-combat flag; for monsters, this is "blocked".
4. **Run the step-or-attack inner pass.** A separate function handles whichever case applies:
   - **Empty walkable cell:** the actor moves. Update its (X, Y) in both the actor table and the parallel dynamic-objects table.
   - **Hostile actor at the destination:** run the attack roll. Hit/miss decision, damage roll, write to the target's HP and flags. The attack-roll consults a damage table indexed by attacker class and target class.
   - **Friendly actor or wall at the destination:** treat as blocked.
5. **On success**, the round walker's post-action render redraws the new positions.
6. **On failure**, narrate "Blocked!" — a short blocked-message and a beep tone are emitted; the actor stays in place.

A side path — controlled by special-combat state bits — runs a **post-step effect** when a placed-field, arena hazard, or special encounter mode is active. This hook is reached only after the step-or-attack primitive succeeds and commits the actor's new coordinate to both combat actor tables. Range failures, blocked cells, and failed attacks do not fire it. It is therefore the confirmed contact boundary for arena hazards and placed-field effects; Poison/Sleep field routing, Fire/Energy damage inputs, non-consuming contact, and combat-exit lifetime for placed fields are fixed below.

Combat field casting itself enters a shared arena-field helper that separates placement from contact/application before any per-field result is applied. The CAST field-kind table maps Fire/Poison/Sleep/Energy to `0x35`/`0x33`/`0x34`/`0x36` for this path. Placement is gated before marker materialization: target selection must produce an in-arena coordinate, a coordinate lookup must resolve a compatible combat-table entry there, and the COMBAT acceptance callback must accept the field pair. The coordinate lookup scans slots in ascending order and returns the first descriptor at the selected coordinate with either live/selectable bit (`0x80` or `0x40`) set, without marked-dead bit `0x20`, without hidden/not-yet-revealed bit `0x04`, and without linked active-object tile byte `0xF4`. Poison Field's kind is immediate-accept in the normal combat-cast state; Fire, Sleep, and Energy use the callback's per-slot lookup plus random gate. Accepted placement materializes a field as an active-object marker in the temporary combat table without creating a paired combat-effect descriptor. The post-action hook matches marker coordinates against the actor's committed coordinate when checking contact. The contact side resolves the actor at the field coordinate, skips the current active actor slot, and does not run the creature-prompt friend/foe lookup. Contact does not consume the marker: the hook applies the field result and returns without clearing or aging the matched active-object record. Poison Field contact first rejects actors whose linked active-object tile/class byte is `>= 0x80`; accepted party targets are poisoned only if their character status is Good, while monsters and already non-Good party targets fall through to poison damage with no field-contact XP credit. Sleep Field contact ignores dead party targets; otherwise it writes asleep status for party targets or the combat sleep/disabled bit for non-party targets. Fire Field rolls raw damage in `[1, 21]` before the normal random defense subtraction, and Energy Field supplies raw zero to the same damage/value path. The traced CAST/COMSUBS/COMBAT callbacks, the accepted-placement resident redraw helper, the post-action contact hook, the generic active-object tick, and the monster death/record-clear path do not contain a field countdown, decrement, or pre-exit removal. Placed markers persist until combat exits, when the combat framer restores the pre-combat active-object table.

Damage application is the responsibility of the inner-pass attack roll (when the destination is a hostile actor), which calls into Section 12's damage-and-status handler with the rolled damage value and the target's slot. The same damage/status endpoint is also used by combat spells after their own targeting and raw-damage calculation.

## 12. Damage and status

The damage-and-status handler bundles "apply damage, update status, narrate the result, and handle special-class death effects" into one function. It takes a damage amount and a target slot.

**Damage modifiers.** Negative damage is clamped to zero and an "attack missed" status flag is raised so the narration reads as a miss. A magic value (decimal 99) is treated as **instant kill** — bypass HP, force the death path; used for between-round death finalisation and one-shot-kill spell effects. Magic Missile and Fireball reach this handler only after the spell-damage wrapper rolls raw damage (`1..16` and `1..30`, respectively) and subtracts a random defense roll based on the target's combat defense; Kill reaches it with the instant-kill sentinel and skips that defense subtraction. Party-member combat defense is computed by summing the readied equipment defense values; when Protection's shared `P` tag is active, that helper adds 3 after the equipment sum. The target's per-class flags are consulted: a "halve damage" flag halves *physical* (non-magical) damage; an "immune to physical" flag zeroes it.

**Apply to HP.** For party members, damage is subtracted from the character record's HP word; on death, the status byte is set to `'D'`, the active-player byte is cleared if this character was the active one, and a death-tile is written to the dynamic-objects table. For monsters, damage is subtracted from the slot's HP byte; on death, control passes to the class-specific death paths.

**Special-class death paths.** Each monster class has a sixteen-bit flag word in a per-class table that encodes several death behaviours. A traced **vanish on death** branch prints `<monster name> vanishes!`, changes the dynamic-object tile to a gravestone, clears the actor record, and plays a fade-out animation, but no class row in the analyzed `DATA.OVL` baseline currently sets the high vanish bit; treat it as a reachable code branch only if a supported asset set supplies a class flag for it. **Special tile transitions** for the Gazer (eye-burst tile + particle effect) and the Gargoyle (lava pool left under the corpse) are hand-tweaked deaths encoded as conditional branches on the class byte. **Default** kill: the death path runs two random checks against the class's drop-cap byte. If the first check accepts, the combat-instance active-object tile becomes the generic dead-monster/drop marker, and byte five of that record stores the class drop-cap value; if the second check also accepts, bit `0x80` is ORed into that same byte as a special-drop marker. If the first check rejects, the active-object tile becomes the alternate no-drop death marker and byte five is not promoted into a loot marker. These markers live in the temporary combat-instance active-object table. The enter/exit framer restores the pre-combat world active-object table after the round loop, so a compatible implementation must not treat default death markers as automatic world loot or trigger-slot removal.

Each monster killed computes a small raw reward unit (roughly a quarter of max-HP plus one). The currently traced COMBAT-level callers use the helper for death finalisation and do not forward that return value through the combat framer; the framer itself restores the active-object snapshot and discards the round-loop return except for victory/defeat/escape control flow. Spell-side callers may consume the helper return immediately: Tremor adds the returned unit to the caster's experience word after each accepted actor, capped at 9999. Whether a caller-side encounter-victory path consumes the value as XP, gold, karma credit, loot selection, or no-op remains the reward-accounting gap.

**Splitting / replicating monsters.** Some classes (slimes, certain gargoyles) carry a "split on damage" flag. When such a monster is *damaged but not killed*, the function looks for an empty slot in the table, copies the parent's class byte into it, and prints `<monster name> divides!`. Up to eight attempts are made to find a free slot.

**Other status changes** — Sleep, Poison, Charm — are applied by separate
per-effect handlers (a poison-tick handler firing once per round, a sleep-effect
handler invoked when the Sleep spell hits). Those handlers update the character
status byte to `'S'` (asleep) or `'P'` (poisoned) and run their own narration.
Inventory counters for carried equipment and use-items live in the same
resident save image and may be decremented by equipment or combat/spell helper
paths, but they are inventory stock, not combat effect timers. Do not
model the carried item counter band as a sleep/charm counter table.

**Active-effect display counter.** Protection, Quickness, Mass Charm, and
Negate Magic install a single shared visible tag/counter rather than writing a
per-character status byte. A resident update helper ages this counter: zero and
255 are inert, other values decrement when that helper runs, and expiry clears
the visible tag and requests a redraw. This counter is not the time system's
torch/light-spell counter; do not model it as one decrement per minute or per
full actor-table sweep. The traced combat-side aging endpoint is the
active-player/selection cleanup path; Time Stop's `T` tag uses the same counter
shape, while the per-turn clock cleanup only observes `T` to skip minute
advancement. The tag is not display-only.
Protection's `P` tag adds 3 to party-member combat defense; Quickness's `Q` tag
randomly gates player-side combat command dispatch with a 0..1 roll; Mass
Charm's `C` tag lets the AI target picker roll against the acting monster's
class charm threshold and, on success, remap that monster to neutral group 0
before friend/foe filtering; Negate Magic's `N` tag absorbs combat casts before
the shared spell dispatcher spends charge or MP. The character status byte `C`
for "casting" is separate from the shared active-effect `C` tag. The exact
number of decrements per full actor-table pass depends on which command/AI
paths run, so per-round parity remains tied to actor dispatch.

The character status byte is the load-bearing summary value: `'G'` good, `'P'` poisoned, `'D'` dead, `'S'` asleep, `'C'` casting, plus other state-specific letters. Other systems read the byte to decide whether the character can act, can be selected as active player, or counts toward the party-defeat check.

## 13. Per-monster-class data

Several aspects of combat behaviour are driven by per-class tables that the spawning, AI, and damage paths all consult — small fixed-stride arrays in the data segment, indexed by monster class byte.

| Table                            | Purpose                                                                                                                                          |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Per-arena spawn-count table      | One byte per arena. Combined with the random reroll, decides how many monsters spawn.                                                            |
| Per-arena leader replacement     | One byte per arena. The tile assigned to the first `count/4 + 1` "leader" monsters.                                                              |
| Per-class flag word              | Sixteen bits per class. Includes split-on-damage, halve-damage-when-physical, immune-to-physical, faction-override, special death checks, and the turn special bits for possess, blink/phase, and summon-daemon. The damage handler also has a vanish-on-death branch, but the analyzed baseline has no class row with that high bit set. |
| Ordinary AI helper state         | Not a class script table. Ordinary monster decisions use the combat actor/effect records, target-selection scratch, per-class flag/stat tables, and shared helper outputs such as the AI step vector. Slot-local position, target, phase, flee, and visibility data remain in the combat actor/effect tables. |
| Per-class display/narration data | Pointer data used by combat narration and class labels; this is not an AI behavior table.                                                        |
| Per-class HP/AC/damage stats     | Eight bytes per class. Includes the base value used by the reward formula, the drop-cap byte used by the default death loot gate, and the Mass Charm threshold used by target-selection remaps. Remaining bytes are only broadly classified. |
| Per-class name pointers          | Sixteen-bit pointers per class to the printable monster name strings.                                                                            |

The class byte is set at spawn time and never changes (death may cause a tile swap, but the class byte stays). The same class index is used for party members (classes 0–15, one per character record slot) and monsters (classes 16+); the AI's friend/foe filter relies on the slot index range to distinguish them.

## 14. Victory, defeat, and escape

Three exit conditions end combat; each sets one of the round-loop's flag bytes, and the per-round epilogue checks them.

**Victory.** When every hostile actor has been killed (no non-party slot has the "alive and active" flag bits set), the round-loop exits with result code "1". The framer then restores the suspended world state, refreshes party stats, and returns to the calling mode. Combat death paths may have produced temporary loot markers and a raw reward unit while the combat-instance tables were live, but the traced framer does not merge those active-object bytes into the restored world table or propagate the helper's return value as a durable encounter reward. This settles the framer-level boundary: ordinary loot, trigger removal, XP, gold, and karma must come from a caller-side or pre-restore consumer if they occur. A spell handler can consume the helper return before the framer boundary, as Tremor does for caster experience, but that is not the ordinary victory handoff. No separate victory message prints — the death-tile transitions tell the story.

**Defeat.** When the entire party is dead, asleep, or otherwise inactive, the engine sets the defeat flag and the round loop returns "0". What happens next depends on the calling mode loop — typically a game-over sequence; a few specific encounters (the Blackthorn capture path) treat defeat as a scripted plot event rather than a death.

**Escape.** Walking off an open arena edge reaches the out-of-bounds combat leave helper. On the first accepted trigger per fight, an exit message is printed; the round loop exits with code "1". Surviving party members and monsters are not given a chance to land final blows once that helper accepts. The `X` command is different: its CMDS escape handler scans for active-not-dead foes and refuses while any remain, so it is a cleanup/victory exit path rather than the ordinary flee-with-enemies-live path.

The framer's restore phase runs the same way for all three — the only difference is the result code returned. Combat time advances from the round loop's round-counter wrap, which fires the per-turn cleanup with a one-minute increment; a separate one-minute exit increment is not part of the currently traced framer restore.

## 15. Hooks into other systems

Combat is built on top of several other systems and integrates cleanly with each.

- **Text output.** All combat narration flows through the per-cell emitter and wrap-aware string printer described in `text-output.md`. Combat does not maintain its own text window; it writes to whichever window was active before the fight.

- **Input.** The player command handler reads via the same wait-for-input routine described in `input.md`. The scene byte is set to the combat sentinel during the fight, so the world-tick step is suppressed; the cursor blink is the only background animation. Free-text and Y/N prompts within combat use the same prompt-mode mechanism.

- **Time.** Combat advances time at one specific point — when the round counter wraps inside a round (corresponding to one full actor walk under typical game pacing). The wrap fires the per-turn cleanup with a one-minute increment, exactly as the town and dungeon loops do.

- **Spell system.** Combat shares the single player/party spell dispatcher
  described in `magic.md`. Combat-specific gates wrap the dispatcher's call
  from within the combat C-handler. Monster turns first pass through AI intent,
  target selection, direction synthesis, and the shared combat command parser.
  The decoded class-flag special hook may possess, blink/phase, or
  summon-daemon before ordinary movement. These branches are separate from the
  player spell table, premixed charges, MP, reagents, and circle gates.

- **Visibility.** The arena's visibility model is similar to the world model but uses the combat terrain grid rather than the world map. Each cell ends up with one of the standard visibility byte values, and the renderer composites actors over those values.

- **Save image.** Character HP, MP, and status bytes are part of the persistent save. Combat itself cannot be saved mid-fight, but a fight's after-effects are persisted. Combat's swap-and-restore mechanism ensures the saved dynamic-objects table is the world's, not the fight's.

## 16. Open questions and variations

This section records places where the picture is not yet complete or where evidence is internally inconsistent.

- **Per-class flag word - un-classified bits.** Several bits in the per-class table are still unnamed. Confirmed readers cover damage/status, faction override, death behaviour, target selection, and the possess/blink/summon-daemon turn hook. Candidate buckets for the remaining bits include damage-type modifiers and movement/terrain interaction; do not assign stable names until their resident consumers are mapped.

- **Vanish-on-death branch reachability.** The damage/status helper contains a vanish branch, but direct asset verification of the analyzed `DATA.OVL` class table found no row with the corresponding high bit set. Keep the branch as an implementation option for variant data, but do not assign it to Wanderer, Blackthorn, Lord British, Shadow Lords, or any other v1 baseline class without fresh table evidence.

- **The "double-encounter" world flag writer.** The flag in the data segment that causes the spawn count to be re-rolled (Section 5) has a not-yet-pinned-down setter. Strong candidates are sleep ambushes and a specific mid-game scripted encounter family.

- **Wait commands in combat.** Space is "pass". Best evidence is "advance the actor's phase counter past zero so it does not act this round but does not lose its position in the table." Implementers should treat Space as "no movement, no attack, end the actor's turn cleanly".

- **Combat command branch bodies.** The dispatcher-level map for all twenty-six
  letters and the special keys is complete, and most delegated overlay targets
  are now named. Remaining exactness work is narrower: the exact CAST
  continuation and item effects reached by combat U-Use, any P-Push
  scene/object edge cases, and command-family edge cases in the
  SJOG/CMDS/ZSTATS helpers.

- **Multi-target spells.** Several combat spells are AOE or multi-target effects (Tremor, Poison Wind, Death Wind, Flame Wind). The effect-dispatch mechanism handles them by walking the actor table and applying the spell to each cell in the AOE; per-actor effect application can reuse the damage-and-status handler. Tremor's loop is exact at public semantic depth: no faction filter, 1..20 damage per accepted actor, shared damage/status application, and returned reward credited to caster experience. The separate active-target attack wrappers are also exact at public semantic depth: Magic Missile rolls 1..16, Fireball rolls 1..30, and Kill passes the decimal 99 instant-kill sentinel after the shared aiming/projectile path accepts a collision target. The directed target-walk family is also exact at public semantic depth for faction behavior: the shared scan de-duplicates actors and skips common empty/status-masked records, but neither that scan nor the Sleep/Poison Wind/Death Wind/Flame Wind per-effect branches run the friend/foe lookup, reject same-faction actors, or reject the caster if the caster's cell is selected. Sleep applies sleep status, Poison Wind applies a resistance/random gate before poison status, Death Wind uses the decimal 99 instant-kill sentinel, and Flame Wind rolls raw 1..30 damage; the two damage winds credit returned monster-kill reward units to the caster with the normal 9999 cap. Mass Charm is now covered as a class-threshold active-effect target-selection remap rather than an actor-table damage/status scan. Field contact is bounded to the post-step effect hook, and combat field casting reaches a shared arena-field helper before splitting placement from application. Placed fields live as active-object markers in the temporary combat table, and the contact scan matches those markers by coordinate while skipping only the current active actor slot; contact applies without consuming the marker. Poison Field skips linked active-object classes `>= 0x80`, poisons only Good party members, and otherwise falls through to poison damage with no field-contact XP credit. Sleep Field skips dead party members and otherwise writes party sleep status or the non-party combat sleep/disabled bit. Fire Field contact rolls raw 1..21 before defense, Energy Field supplies raw zero to the same path, and the placement path's target-selection/coordinate-lookup/acceptance gate is bounded down to slot-order and flag eligibility. Field markers are not aged by the placement, contact, redraw, generic active-object tick, or monster death/record-clear paths; they persist until combat exit restores the pre-combat active-object table.

- **Status narration.** "Sleep!", "Poison!", "Charm!" lines are not produced by the damage-and-status handler. They live in separate per-effect handlers (one per status). The exact wording and trigger mechanics belong in those handlers' specs.

- **Active-effect side effects.** The shared display counter for Protection,
  Quickness, Mass Charm, and Negate Magic is now traced through cast setup and
  the counter-aging boundary. Combat distinguishes that path from the
  time/render cleanup on ten-ready-action wraps; zero and 255 are inert, other
  values decrement at the reached cleanup endpoints, and expiry clears the
  shared tag and requests redraw. Time Stop's `T`/10 runtime tag uses the same
  counter shape, but the clock cleanup only observes `T` to suppress minute
  advancement. Confirmed consumers are Protection's `P` defense bonus,
  Quickness's `Q` player-dispatch random gate, Mass Charm's `C`
  class-threshold AI-target remap, and Negate Magic's `N` combat-cast
  absorption path.

- **Flee mechanics beyond Cause Fear.** The Cause Fear spell is a confirmed
  public writer of the fleeing flag, and Section 9 specifies how the flag
  reverses movement. Other possible writers, such as low-HP morale or helper
  side effects, are not yet fully traced. The decoded possess/blink/summon-daemon
  hook does not set this flag.

- **Monster special-action variants.** The monster-turn path proves the
  class-flag special hook, shared target selection, phase/hidden/invisibility
  filters, no-target fallback, movement-vector synthesis, synthesized command
  dispatch, and parser reuse. The v1 baseline assigns the decoded possess bit
  to Blackthorn, Gazer, Wisp, Daemon, and Shadow Lord. The blink/phase and
  summon-daemon branches are implemented but not assigned by the analyzed v1
  class table, so keep them data-driven for variant assets.

- **Ordinary AI helper identities.** The old "class script runner" hypothesis
  has been removed. Remaining exactness work is narrower: helper identities for
  some step-permission, step-validity, fallback-target, and no-target cleanup
  calls; exact labels for a few scene/class exceptions in the target picker;
  and any additional writers of the flee bit.

- **Round counter wrap at ten.** The per-round counter wraps at ten and fires a tile-render on every wrap. Likely a "render every N actor-turns" cadence balancing CPU cost on original hardware. A modern implementation can treat it as "redraw every frame" without preserving the cadence.

- **Map of three friend/foe factions.** The slot-to-group helper used by target selection returns a small int per slot. Party members are one faction, monsters typically another, but a third "neutral" faction exists for some encounter types. The full set of factions is per-class and partially traced.

- **The thirty-two-slot table size.** Plausibly: six party slots + sixteen monster placement slots + ten "dynamic" slots for replicated/summoned creatures. The round walker's "less than thirty-two" test is the only hard upper bound.

## 17. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The combat enter/exit framer with its three-way entry-mode dispatch, save-and-restore of player position and the dynamic-objects table, the scene-byte sentinel, and the post-combat active-player check — derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The terrain-combat setup, the per-arena spawn-count lookup, the optional Fisher-Yates shuffle for ambush placement, the leader-vs-follower count-and-tile split, and the single-attacker town-style override — derived from `u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`.
- The per-round walk over the thirty-two-slot actor table, the phase-counter mechanic, the round-counter wrap, the dispatch to player vs. monster handlers, and the three exit conditions — derived from `u5-decomp/functions/COMBAT_OVL/0x0B94_combat_main_loop.md`.
- The per-actor turn dispatcher, complete dispatcher-level combat command map
  for all twenty-six letters and seven special inputs, the AI synthesis path for
  monster turns, the verb-stitching narration buffer, and the unified
  per-letter parser — derived from
  `u5-decomp/functions/COMBAT_OVL/0x063E_actor_ai_or_command.md`.
- Delegated combat command targets and edge behaviour for SJOG
  Get/Jimmy/Open/Search/Klimb, CMDS X-it/Yell/Push, ZSTATS
  Ready/Z-stats, and the unresolved CAST-owned combat U-Use continuation -
  derived from the corresponding COMBAT stub table plus
  `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`,
  `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md`,
  `u5-decomp/functions/CMDS_OVL/0x17EC_cmds_escape.md`,
  `u5-decomp/functions/CMDS_OVL/0x1418_cmds_yell.md`,
  `u5-decomp/functions/CMDS_OVL/0x161A_cmds_push.md`, and
  `u5-decomp/functions/ZSTATS_OVL/_OVERVIEW.md`, with
  `u5-decomp/functions/CAST_OVL/_OVERVIEW.md` and
  `u5-decomp/functions/CAST_OVL/all_spells.md` as CAST-side cross-checks.
- The AI target-selection helper, the backwards walk and filter chain, the Mass
  Charm active-effect tag remap with class-threshold random gate, the
  phase/hidden suppression exception, the ordinary invisibility filter, the
  first-five-party-slot fallback guard, centre fallback, pending-action marker,
  squared-distance scoring with closest-wins tie-break, and the unit-step
  direction output with flee inversion — derived from
  `u5-decomp/functions/COMBAT_OVL/0x0D30_target_picker.md` and the sibling
  COMBAT damage/death note that identifies the same random-byte helper.
- Protection's active-effect defense bonus, Quickness's player-side dispatch gate, Negate Magic's combat-cast absorption path, Time Stop's `T`/10 runtime tag, and the active-effect counter-aging rule — derived from local ULTIMA.EXE, COMBAT, CAST, CAST2, and SJOG helper analysis summarized without copying implementation text.
- The damage application and status transitions, the per-monster-class flag word's effect on damage and death, the special-class death paths, and the slime-divide replication path — derived from `u5-decomp/functions/COMBAT_OVL/0x1574_narrate_status_change.md`.
- The step-or-attack primitive — direction-to-unit-step translation, arena range check, on-success and on-failure narration, and the post-step effect gate — derived from `u5-decomp/functions/SJOG_OVL/0x1C56_actor_step_or_attack.md`.
- The monster special-ability hook, including possess, blink/phase,
  summon-daemon, branch ordering, chance gates, and baseline class-flag
  assignments, derived from
  `u5-decomp/functions/COMSUBS_OVL/0x00F4_monster_special_ability_tick.md`
  and the `DATA.OVL` class-flag table.
- The combat-side spell prereq cascade — target validity, target visibility/awakeness, vehicle gate, MP/resource check — derived from `u5-decomp/functions/COMSUBS_OVL/0x09FC_check_spell_prereqs.md`.
- The shared spell dispatcher used by combat casts — derived from `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`.
- The combat spell-damage wrapper used by Magic Missile, Fireball, and Kill — derived from local CAST, COMSUBS, and COMBAT helper analysis summarized without copying implementation text.
- The Clone spell's allocation and random legal arena placement behaviour — derived from local CAST and COMBAT helper analysis summarized without copying implementation text.
- The dynamic-objects table that combat overlays and the sprite animator that walks it during world ticks — derived from `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
- The fog/visibility post-pass that consumes the same active-object table during world rendering — derived from `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md`.
- The squared-distance primitive used by combat AI target scoring, with its 11×11 arena coordinate space and reflection-folded precomputed table — derived from `u5-decomp/functions/ULTIMA_EXE/0x6FF0_range_to_player.md`.
- The combat-arena file layout — 352-byte record stride, 11×11 terrain grid, metadata band, outdoor and dungeon-encounter banks — derived from `u5-decomp/formats/maps.md`.
- The character-record layout consulted by damage application and the active-player restore — derived from `u5-decomp/formats/saves.md`.
