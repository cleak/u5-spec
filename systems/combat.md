# Combat

## 1. Overview

Ultima V's combat system is a turn-based, party-versus-monsters tactical mode that plays out on a small fixed-size arena grid. When a world-mode loop (overworld, town, or dungeon) triggers a fight, the engine suspends what it was doing, swaps the on-screen scene for an arena, populates the arena with the player's party at one set of fixed entry points and a randomised set of monsters at another, and runs a self-contained round loop until one side is wiped out or the player flees. When the loop returns, the engine restores the suspended world state — player position, the dynamic-objects table, the scene byte — and returns control to the calling mode loop with the fight's after-effects baked in: damage taken, characters dead or asleep, time advanced, loot dropped.

Combat is "inside-out" — the world freezes while the fight plays through, the fight has its own table of actors, its own per-letter command dispatch, its own AI, and its own arena terrain — and then the function call returns and the world resumes exactly where it left off. The mode-loops above combat are unaware that combat happened beyond the visible state changes.

This spec describes the combat trigger framing, the arena format and monster placement, the per-round walk over the actor table, the player command set, the monster AI, the attack-resolution primitive, the damage and status model, and integration points with text output, the spell system, and time.

## 2. Combat triggers

Combat enters from one entry point — a single function call from a world mode loop that takes three parameters: a flags word, an actor-slot index, and an entry-mode bitfield. The entry-mode bitfield distinguishes three families of fight:

**Terrain combat.** The default. Reached when the player walks into (or attacks) a hostile creature on the overworld. The dynamic-objects-table slot of the offending creature is passed along; its tile class picks one of sixteen outdoor arenas via a small linear formula in the tile-class range. The terrain-combat setup chooses the arena, sets up the monster spawn count, and places each monster at one of a fixed set of arrival positions.

**Ambush combat.** Reached from town/dwelling/castle/keep mode-loops when a hostile NPC initiates a fight, and from a small handful of overworld scripted-encounter tiles. Has a different setup helper that places monsters at randomised arena positions rather than fixed ones.

**Scripted / "alternate" combat.** Reached from a small set of scripted-event triggers — most prominently the duel with Lord Blackthorn near the endgame. The handler is allowed to *cancel* the fight by returning a non-zero predicate; on cancel, the framer skips the round loop entirely and returns to the caller as if the fight never happened. Used for fights whose outcome is deterministic at trigger time.

Once one of the three setup paths has prepared the arena, the framer clears a few combat-state bytes and calls into the round loop. On return — whether via victory, defeat, or escape — the framer runs the teardown described in Section 4.

## 3. The arena

A combat arena is a rectangle of terrain tiles plus a band of metadata describing where actors enter and which terrain pieces hold special meaning (spawn points, hazards, ladders). Two on-disk files hold the engine's full set of arenas: a bank of sixteen outdoor arenas keyed by overworld terrain class (each tied to a tile family — grass, forest, hills, swamp), and a much larger bank of dungeon-encounter arenas (over a hundred records).

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

Each placed monster's record is initialised with the chosen tile, the chosen arena coordinates, a phase counter and base-step value derived from the class (Section 7), and the appropriate flag bits. The placement helper returns when all monsters are written.

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

## 7. Per-round structure

Each round is one walk over the thirty-two-slot actor table. The round loop is a per-round prologue, a per-actor body that runs zero or one times per slot, and a per-round epilogue that checks the three exit conditions. When the body has visited all thirty-two slots, the round restarts (unless an exit fires).

**Per-round prologue.** A small bundle of housekeeping calls: screen redraw, combat-begin overlay refresh, screen flush, per-round init that resets per-slot scratch state, and clearing the "any spell cast this round" flag.

**Per-actor body.** For each slot 0–31:

1. **Skip empty slots and slots already marked dead.** The "alive" flag and "marked dead" flag bits gate this.
2. **Sweep deaths from prior rounds.** If the slot is alive but its linked character record's status byte is now `'D'`, mark the slot dead, fire a death-narration effect, and advance to the next slot. This catches party members who died between rounds (poison, ongoing spells).
3. **Skip wall-cell slots.** A defensive guard against bad placement.
4. **Decrement the actor's phase counter.** While non-zero, the slot does not act this round. When it reaches zero, the actor *does* act.
5. **On zero, refresh the counter and act.** The counter is reset to `(constant − base_step)`. A round-counter at the table level is incremented and wrapped at ten; on every wrap, the engine fires a tile-render pass for animation.
6. **Dispatch the actor's turn.** A single function asks "is this slot a player or a monster?" — for a player, control passes to the player command handler (Section 8); for a monster, to the AI-then-command handler that runs the AI synthesis path before falling into the same dispatch (Section 9).
7. **Mark the slot acted, run the post-action render.** Redraws changed cells and runs any post-action sound or particle effect. Death narration runs here when relevant.

**Per-round epilogue / exit checks.** Three flags control exit:

- **Defeat flag**: the entire party is dead, asleep, or fled. Result is "defeat".
- **Leave-combat flag**: the player has chosen to leave (via the X-it command, walking off an open edge, or a spell that ends combat). On the *first* such trigger per fight, the exit-message string is printed; subsequent reads pass through silently.
- **Exhausted slots** (loop reached slot 32): start a new round.

When defeat or leave-combat fires, the round loop returns "1" (victory/escape) or "0" (defeat).

The phase-counter / base-step structure means actors act at *staggered* paces. There is no "player turn then monster turn" — initiative is *interleaved* by phase counter, so a fast monster might act twice between the player's turns.

## 8. Player commands in combat

When the round walker dispatches a player slot, the player command handler reads exactly one keystroke from the input pipeline (using the same input system that drives the rest of the engine). The keystroke is folded to upper case, case-checked against the combat command set, and dispatched.

The combat command set consists of letter keys A–Z plus a small set of control codes (Escape, Ctrl-S, Space, digits, direction codes). The recognised letter commands are:

| Key   | Meaning                                                      |
|-------|--------------------------------------------------------------|
| **A** | Attack in a direction. Prompts for a direction key, then runs the step-or-attack primitive (Section 11). |
| **B** | Board ship or horse.                                          |
| **C** | Cast a spell (Section 10).                                    |
| **E** | Enter a portal, town, or moongate.                            |
| **F** | Fire a ship cannon.                                           |
| **G** | Get an item. Prompts for direction.                           |
| **H** | Hole up & camp.                                               |
| **I** | Ignite a torch.                                                |
| **J** | Jimmy a lock. Prompts for direction.                          |
| **K** | Klimb a ladder/cliff.                                          |
| **L** | Look at a tile. Prompts for direction, narrates the tile's name. |
| **M** | Mix reagents.                                                  |
| **N** | New order — re-arrange the party order.                       |
| **O** | Open a chest or door. Prompts for direction.                  |
| **P** | Push a barrel/item.                                            |
| **Q** | Quit (save and exit).                                          |
| **R** | Ready — equip an item from inventory.                         |
| **S** | Search the current cell.                                       |
| **T** | Talk to a monster. (Almost always rejected.)                  |
| **U** | Use an item from inventory.                                    |
| **V** | View the world map.                                            |
| **X** | X-it — leave combat voluntarily. Sets the leave-combat flag (Section 14). |
| **Y** | Yell an activation word.                                       |
| **Z** | Z-stats — show the active character's stat panel.             |

Letters that have no meaning in combat (D, W) print a short refusal ("D-What?", "W-What?"). Other inputs:

- **Space** — pass / wait one phase.
- **Escape** — abort whichever multi-stage prompt is active.
- **Ctrl-S** — toggle music.
- **Digit `0`** — clear the active-player selection.
- **Digits `1`–`6`** — select party member 1 through 6 as the active player.
- **Direction codes** (the eight movement codes the input system translates from numpad / arrow keys) — move one cell in the given direction. Movement uses the step-or-attack primitive: if the cell is occupied by a hostile, attack instead; if it is on the open edge, leave combat.

Several commands are **multi-stage** (Attack, Cast, Get, Jimmy, Klimb, Look, Open, Push, Use, Yell): they print a short prompt and call back into the input system to read a second keystroke. The combat command handler's dispatch is structured so multi-stage commands return control to the same handler for their continuation rather than recursing through the round walker. The command set mirrors the world mode loops' command set so muscle memory transfers cleanly between play modes; the most distinctive combat-only commands are A, C, and X.

## 9. Monster AI

When the round walker dispatches a monster slot, the AI runs as a sequence of three passes that ultimately produce a *synthesised keystroke* — the AI generates the same bytes the player would press if they were controlling this monster, and the synthesised byte runs through the same per-letter dispatcher as a player turn. Monsters and players share the action infrastructure.

**Pass 1 — Intent.** A small helper clears the per-actor narration buffer, picks animation flags, and decides whether the monster should act normally, perform a special-effect action (sleep aura, poison breath, charm), or do nothing this turn. The intent is written into the actor's record so subsequent passes can read it.

**Pass 2 — Direction.** A second helper consults the per-class AI script for this monster, looks at the arena around it, and writes a unit-step `(dx, dy)` vector to two well-known data-segment scratch slots. Each component is `-1`, `0`, or `+1`. The script may consult a per-instance state block (for active monsters) or a per-class static script pointer (for inactive or dead-ish monsters that still need to run an animation script).

**Target selection** is the heart of Pass 2. Given the acting monster's slot index, the target picker walks the actor table backwards from slot 31 to slot 0, computes the squared distance to each candidate, and picks the closest one that survives a chain of filters:

- Not the acting monster itself.
- Slot is not empty and not marked dead.
- Not on the same *faction* — friend/foe is decided by a "slot-to-group" helper that maps each slot to a faction id; party members are one faction, monsters typically a single hostile faction, with a third "neutral" faction for some monster types.
- Visible to the acting monster (the "invisible / not-yet-revealed" flag is clear) — except in specific encounter types where this filter is bypassed.

The target's distance is consulted via a precomputed squared-distance table indexed by folded coordinate pair (the table is reflection-symmetric about the centre cell of the arena). Backwards walk plus strict less-than comparison means *the lowest-numbered slot among candidates of equal distance wins*, biasing toward party members (low slots) when distances tie.

**Step direction.** Once a target is picked, the unit-step vector is the per-axis sign of `(target − self)`. If the acting monster's "fleeing" flag is set, both axes are negated — the monster moves *away* from the target. If no target survives the filters, the AI falls back: a per-turn cleanup helper produces a default target, or, failing that, the step vector is left at `(0, 0)` (stay put).

**Pass 3 — Synthesise.** A combat-specific input gate reads the synthesised byte from the actor's record. The AI's chosen direction is encoded as the byte the player would press if they wanted to walk the same way (`'N'`, `'S'`, `'E'`, `'W'` direction codes), or the byte for "Attack" if the chosen direction puts the target adjacent. The byte falls into the same per-letter dispatcher as the player command handler. Before the command runs, the AI assembles a one-line narration string — for example `<monster name> attacks <target name>, armed with <weapon>!` — by stitching together a short verb composer.

The architectural consequence: **all damage and movement effects in combat go through the same primitive, regardless of whether the actor is a player or a monster.** Section 11 describes that primitive.

## 10. Spells in combat (summary)

Combat shares the spell engine with the rest of the game; the C (Cast) command dispatches via the same routing as the overworld C. The combat-specific path adds three things.

**Prerequisite check.** Before queueing a spell, a short prereq cascade runs: the caster has a valid target, the target is not invisible or asleep, the caster is not in a prohibited vehicle (the "tower" vehicle disables casting), and the caster has enough MP and reagents. Failure prints a short refusal and aborts.

**Scene gate.** Each spell carries a four-bit allow-mask for the scenes it works in (overworld, town, shrine, combat). Scenes for which the spell has no entry print a "Not here!" refusal. Most damaging spells are gated to combat-only.

**MP and reagent debit.** The spell's MP cost is `(spell_id / 6) + 1` — eight circles of six spells each. The caster's MP is debited; the pre-mixed reagent stock for that spell (a per-spell counter built via the M-Mix command) is decremented; the spell-effect handler runs.

The full spell system is described in its own spec; only the combat-side gating and dispatch are covered here. The AI's monster-cast path does *not* run through the same dispatcher — monsters with spell-like attacks have hand-coded effects that don't consume reagents or check MP.

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

A side path — controlled by a flag bit in the combat-state byte — runs a **post-step effect** when a special encounter mode is active (notably the per-monster sleep auras and certain spell echoes). The post-step effect runs after a successful step but before control returns to the round walker.

Damage application is the responsibility of the inner-pass attack roll (when the destination is a hostile actor), which calls into Section 12's damage-and-status handler with the rolled damage value and the target's slot.

## 12. Damage and status

The damage-and-status handler bundles "apply damage, update status, narrate the result, and handle special-class death effects" into one function. It takes a damage amount and a target slot.

**Damage modifiers.** Negative damage is clamped to zero and an "attack missed" status flag is raised so the narration reads as a miss. A magic value (decimal 99) is treated as **instant kill** — bypass HP, force the death path; used for between-round death finalisation and one-shot-kill spell effects. The target's per-class flags are consulted: a "halve damage" flag halves *physical* (non-magical) damage; an "immune to physical" flag zeroes it.

**Apply to HP.** For party members, damage is subtracted from the character record's HP word; on death, the status byte is set to `'D'`, the active-player byte is cleared if this character was the active one, and a death-tile is written to the dynamic-objects table. For monsters, damage is subtracted from the slot's HP byte; on death, control passes to the class-specific death paths.

**Special-class death paths.** Each monster class has a sixteen-bit flag word in a per-class table that encodes several death behaviours. **Vanish on death** for boss-tier classes (the Wanderer, Lord Blackthorn, Lord British): the slot prints `<monster name> vanishes!`, the dynamic-objects tile becomes a gravestone, the actor record is cleared, a fade-out animation plays. **Special tile transitions** for the Gazer (eye-burst tile + particle effect) and the Daemon (lava pool left under the corpse) — hand-tweaked deaths encoded as conditional branches on the class byte. **Default** kill: the slot's tile becomes a generic dead-monster tile; a random-loot byte is rolled (a quantity bounded by max-HP) and written to the active-object record; a second roll may set a "special drop" flag.

Each monster killed produces a small XP/gold reward (roughly a quarter of max-HP plus one), returned to the round walker for the calling code to aggregate.

**Splitting / replicating monsters.** Some classes (slimes, certain gargoyles) carry a "split on damage" flag. When such a monster is *damaged but not killed*, the function looks for an empty slot in the table, copies the parent's class byte into it, and prints `<monster name> divides!`. Up to eight attempts are made to find a free slot.

**Other status changes** — Sleep, Poison, Charm — are applied by separate per-effect handlers (a poison-tick handler firing once per round, a sleep-effect handler invoked when the Sleep spell hits). Those handlers update the character status byte to `'S'` (asleep) or `'P'` (poisoned) and run their own narration.

The character status byte is the load-bearing summary value: `'G'` good, `'P'` poisoned, `'D'` dead, `'S'` asleep, `'C'` casting, plus other state-specific letters. Other systems read the byte to decide whether the character can act, can be selected as active player, or counts toward the party-defeat check.

## 13. Per-monster-class data

Several aspects of combat behaviour are driven by per-class tables that the spawning, AI, and damage paths all consult — small fixed-stride arrays in the data segment, indexed by monster class byte.

| Table                            | Purpose                                                                                                                                          |
|----------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| Per-arena spawn-count table      | One byte per arena. Combined with the random reroll, decides how many monsters spawn.                                                            |
| Per-arena leader replacement     | One byte per arena. The tile assigned to the first `count/4 + 1` "leader" monsters.                                                              |
| Per-class flag word              | Sixteen bits per class. Includes split-on-damage, halve-damage-when-physical, immune-to-physical, vanish-on-death, faction-override, plus several un-classified bits the AI scripts read. |
| Per-class AI script pointers     | One pointer per class to the byte-coded AI script the runner walks during Pass 2 of the AI.                                                      |
| Per-class HP/AC/damage stats     | Eight bytes per class. Byte 0 is a base value used by the reward formula; byte 2 is a max-HP/cap value used by the loot roll.                  |
| Per-class name pointers          | Sixteen-bit pointers per class to the printable monster name strings.                                                                            |

The class byte is set at spawn time and never changes (death may cause a tile swap, but the class byte stays). The same class index is used for party members (classes 0–15, one per character record slot) and monsters (classes 16+); the AI's friend/foe filter relies on the slot index range to distinguish them.

## 14. Victory, defeat, and escape

Three exit conditions end combat; each sets one of the round-loop's flag bytes, and the per-round epilogue checks them.

**Victory.** When every hostile actor has been killed (no non-party slot has the "alive and active" flag bits set), the round-loop exits with result code "1". Cleanup happens in the framer's restore phase: party stats are refreshed, loot drops left in the dynamic-objects table by the death paths become part of the world's items table, karma and XP are aggregated by the calling mode loop. No separate victory message prints — the death-tile transitions tell the story.

**Defeat.** When the entire party is dead, asleep, or otherwise inactive, the engine sets the defeat flag and the round loop returns "0". What happens next depends on the calling mode loop — typically a game-over sequence; a few specific encounters (the Blackthorn capture path) treat defeat as a scripted plot event rather than a death.

**Escape.** When the player chooses to leave (the X-it command, or walking off an open arena edge), the leave-combat flag fires. On the *first* trigger per fight, an exit message is printed; the round loop exits with code "1". Surviving party members and monsters are *not* given a chance to land final blows — escape is immediate.

The framer's restore phase runs the same way for all three — the only difference is the result code returned. Time advances by one minute (the cleanup routine is called once at combat exit).

## 15. Hooks into other systems

Combat is built on top of several other systems and integrates cleanly with each.

- **Text output.** All combat narration flows through the per-cell emitter and wrap-aware string printer described in `text-output.md`. Combat does not maintain its own text window; it writes to whichever window was active before the fight.

- **Input.** The player command handler reads via the same wait-for-input routine described in `input.md`. The scene byte is set to the combat sentinel during the fight, so the world-tick step is suppressed; the cursor blink is the only background animation. Free-text and Y/N prompts within combat use the same prompt-mode mechanism.

- **Time.** Combat advances time at one specific point — when the round counter wraps inside a round (corresponding to one full actor walk under typical game pacing). The wrap fires the per-turn cleanup with a one-minute increment, exactly as the town and dungeon loops do.

- **Spell system.** Combat shares the single spell dispatcher described in `magic.md` (when written). Combat-specific gates wrap the dispatcher's call from within the combat C-handler. Monster spells are *not* dispatched through this system — they have hand-coded effects keyed by monster class.

- **Visibility.** The arena's visibility model is similar to the world model but uses the combat terrain grid rather than the world map. Each cell ends up with one of the standard visibility byte values, and the renderer composites actors over those values.

- **Save image.** Character HP, MP, and status bytes are part of the persistent save. Combat itself cannot be saved mid-fight, but a fight's after-effects are persisted. Combat's swap-and-restore mechanism ensures the saved dynamic-objects table is the world's, not the fight's.

## 16. Open questions and variations

This section records places where the picture is not yet complete or where evidence is internally inconsistent.

- **Per-class flag word — un-classified bits.** Six of the sixteen flag bits in the per-class table are tested by some readers but their exact effect is not yet fully traced. Strong candidates: damage-type modifiers (fire / cold / electric), AI traits (passive / aggressive / ranged-preferring), and tile-interaction bits (incorporeal / water-bound / floats-over-terrain).

- **The "double-encounter" world flag writer.** The flag in the data segment that causes the spawn count to be re-rolled (Section 5) has a not-yet-pinned-down setter. Strong candidates are sleep ambushes and a specific mid-game scripted encounter family.

- **Wait commands in combat.** Space is "pass". Best evidence is "advance the actor's phase counter past zero so it does not act this round but does not lose its position in the table." Implementers should treat Space as "no movement, no attack, end the actor's turn cleanly".

- **Multi-target spells.** Several combat spells are AOE (Cataclysm, Fire-storm, Mass Heal). The effect-dispatch mechanism handles them by walking the actor table and applying the spell to each cell in the AOE; per-actor effect application reuses the damage-and-status handler. The exact AOE shape and friendly-fire policy is per-spell.

- **Status narration.** "Sleep!", "Poison!", "Charm!" lines are not produced by the damage-and-status handler. They live in separate per-effect handlers (one per status). The exact wording and trigger mechanics belong in those handlers' specs.

- **Flee mechanics.** A monster's "fleeing" flag (Section 9) reverses its movement direction. What *sets* the fleeing flag — low HP threshold? specific spell effects? — is per-class and not yet fully traced.

- **Round counter wrap at ten.** The per-round counter wraps at ten and fires a tile-render on every wrap. Likely a "render every N actor-turns" cadence balancing CPU cost on original hardware. A modern implementation can treat it as "redraw every frame" without preserving the cadence.

- **Map of three friend/foe factions.** The slot-to-group helper used by target selection returns a small int per slot. Party members are one faction, monsters typically another, but a third "neutral" faction exists for some encounter types. The full set of factions is per-class and partially traced.

- **The thirty-two-slot table size.** Plausibly: six party slots + sixteen monster placement slots + ten "dynamic" slots for replicated/summoned creatures. The round walker's "less than thirty-two" test is the only hard upper bound.

## 17. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions and format notes in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The combat enter/exit framer with its three-way entry-mode dispatch, save-and-restore of player position and the dynamic-objects table, the scene-byte sentinel, and the post-combat active-player check — derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The terrain-combat setup, the per-arena spawn-count lookup, the optional Fisher-Yates shuffle for ambush placement, the leader-vs-follower count-and-tile split, and the single-attacker town-style override — derived from `u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`.
- The per-round walk over the thirty-two-slot actor table, the phase-counter mechanic, the round-counter wrap, the dispatch to player vs. monster handlers, and the three exit conditions — derived from `u5-decomp/functions/COMBAT_OVL/0x0B94_combat_main_loop.md`.
- The per-actor turn dispatcher, the player command set with its inline jump tables, the AI synthesis path for monster turns, the verb-stitching narration buffer, and the unified per-letter parser — derived from `u5-decomp/functions/COMBAT_OVL/0x063E_actor_ai_or_command.md`.
- The AI target-selection helper, the backwards walk and filter chain, the squared-distance scoring with closest-wins tie-break, and the unit-step direction output with flee inversion — derived from `u5-decomp/functions/COMBAT_OVL/0x0D30_target_picker.md`.
- The damage application and status transitions, the per-monster-class flag word's effect on damage and death, the special-class death paths, and the slime-divide replication path — derived from `u5-decomp/functions/COMBAT_OVL/0x1574_narrate_status_change.md`.
- The step-or-attack primitive — direction-to-unit-step translation, arena range check, on-success and on-failure narration, and the post-step effect gate — derived from `u5-decomp/functions/SJOG_OVL/0x1C56_actor_step_or_attack.md`.
- The AI direction-picker dispatch — alive-vs-dead split between per-instance state blocks and per-class script pointers — derived from `u5-decomp/functions/COMSUBS_OVL/0x0094_ai_pick_direction.md`.
- The combat-side spell prereq cascade — target validity, target visibility/awakeness, vehicle gate, MP/resource check — derived from `u5-decomp/functions/COMSUBS_OVL/0x09FC_check_spell_prereqs.md`.
- The shared spell dispatcher used by combat casts — derived from `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`.
- The dynamic-objects table that combat overlays and the sprite animator that walks it during world ticks — derived from `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
- The fog/visibility post-pass that consumes the same active-object table during world rendering — derived from `u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md`.
- The squared-distance primitive used by combat AI target scoring, with its 11×11 arena coordinate space and reflection-folded precomputed table — derived from `u5-decomp/functions/ULTIMA_EXE/0x6FF0_range_to_player.md`.
- The combat-arena file layout — 352-byte record stride, 11×11 terrain grid, metadata band, outdoor and dungeon-encounter banks — derived from `u5-decomp/formats/maps.md`.
- The character-record layout consulted by damage application and the active-player restore — derived from `u5-decomp/formats/saves.md`.
