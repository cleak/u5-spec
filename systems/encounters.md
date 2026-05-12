# Encounters

## 1. Overview

Ultima V's *encounter system* is the layer that decides **when combat starts**, **what is fought**, and **where it is fought**. It is distinct from combat itself: combat is the round-by-round arena play that begins after an encounter has been picked; encounters are the chance-and-script logic that turns a quiet step on the overworld, an attempt to sleep in a wood, or a dungeon room transition into a populated arena.

There are three encounter triggers in the running game:

- **Random overworld encounters.** Each turn taken on the surface or in the underworld, a chance-roll decides whether a hostile monster spawns near the party. The roll is keyed off terrain (mountains and forests are dangerous; roads are safe) and party state.
- **Scripted encounters.** A small, hand-authored set of locations and events force a specific encounter when reached: ambush tiles in story-driven keeps, the duel with Lord Blackthorn, a few unique boss meetings.
- **Dungeon room encounters.** Stepping onto certain dungeon-room cells, or springing a chest trap inside a dungeon, loads a fixed dungeon arena from a separate on-disk bank.

Once any trigger fires, the same combat-enter framing function runs — combat is a function call from the world mode loop's perspective (see `combat.md`). The encounter system's job ends when that call begins; everything after the framer's *save phase* belongs to combat. This spec covers the trigger-side mechanics, the arena-selection logic, the per-arena spawn-count and tile pipeline, and the small set of side mechanics — sleep ambushes, town-hostility events, "fortunes-of-war" doublings — that change the encounter pacing.

## 2. The three triggers

### 2.1 Random overworld encounters

Every turn the overworld mode loop runs its per-turn block (see `overworld.md`), and that block contains an *encounter probe*. The probe runs once per overworld turn:

1. Roll a uniform integer in `[1, 30]` from the engine's RNG primitive (see `time.md` for how the RNG is seeded — once, at game start, from the system clock).
2. Compare the roll against a *threshold* derived from the tile under the party and from the party's state (Section 3).
3. If the threshold exceeds the roll, fire the *encounter spawner*, which writes one new monster into the active-object table on a tile near the party and lets the world loop's existing collision logic do the rest.

Note the inverted comparison: the threshold is the chance-of-encounter expressed on the same 1..30 scale as the roll. A higher threshold means encounters more often. The probe never *enters combat directly* — it spawns a monster as an active object, and combat starts the moment the player or that monster steps into the other's tile.

The probe is an overworld-mode-only routine. The town loop's per-turn block does not run it; encounters in towns happen exclusively through scripted hostility (Section 7). The dungeon mode loop has its own room-trigger logic (Section 8).

### 2.2 Scripted encounters

A scripted encounter is one where the engine, on detecting a particular tile or event, calls the combat framer with a non-zero entry-mode flag. The framer's three-way dispatch (see `combat.md` Section 2) routes such calls past the random arena selection into either the *ambush* setup helper or the *alternate* setup helper, depending on which flag bit was set. From the encounter system's perspective:

- **Ambush flag.** Indicates that the calling code already knows which arena to use and already has the relevant active-object slot identified. The ambush setup helper applies a randomised placement (Fisher-Yates shuffle of the sixteen arena entry slots) so the player cannot anticipate the monster layout; otherwise it follows the same per-arena spawn-count pipeline the random branch uses.
- **Alternate flag.** Used for fully-scripted boss-style fights — the Lord Blackthorn duel, the Codex confrontation, and a small set of similar set-pieces. The alternate handler is allowed to *cancel* the fight by returning a non-zero predicate; in that case the framer skips the round loop entirely. This lets one-shot-kill scripted scenes ("the moment you walk in, X happens") use the same framing without forcing an actual fight.

Scripted encounters are dispatched from places like the town mode loop's hostility detector (Section 7), the moongate and chasm handlers in the overworld, and a small handful of overworld tiles that always force a fight. The list is hand-authored — there is no general "this tile triggers a scripted encounter" mechanism beyond the per-tile dispatch.

### 2.3 Dungeon room encounters

Dungeon mode runs its own per-turn block, but it does not roll the random-encounter probe. Instead, certain tile classes inside a dungeon level trigger a deterministic combat call: stepping onto a *room* tile loads a fixed arena from the dungeon-encounter arena bank, and springing a *trap chest* loads a different arena (typically a smaller, fixed-monster encounter — gremlins, snakes, or similar). Room arena selection is keyed by the active dungeon scene and the trigger cell's low nibble; for chests, the trap-specific lookup remains separate. The rest of the pipeline — count, placement, leader/follower split — runs the same way as for overworld encounters.

Dungeon encounters do not consult the overworld terrain class or the time of day. The dungeon-encounter arena bank is much larger than the overworld bank (one hundred twelve records versus sixteen), reflecting the wider variety of fixed-content dungeon situations.

## 3. The probability of a random encounter

The probe runs against a 30-sided roll. The threshold depends on:

- **Terrain class of the cell under the party.** Mountains, forests, swamp, and similar wilderness tiles produce the highest threshold; grass and roads produce a low one; cleared/town tiles produce zero (no random encounters in town squares). The terrain class is read from the same world tile under the party that the per-turn block already has cached.
- **Party state.** The smaller the conscious party (fewer non-dead, non-asleep members), the higher the threshold. A solo Avatar walking through a forest is more likely to draw a fight than the full party of six. The exact weighting is a small lookup table indexed by conscious-party-member count.
- **Time-of-day cues.** Some cues (e.g. night-time on the surface) bias the threshold upward — the same cell becomes more dangerous after dusk than it is at noon. The bias is small but noticeable and is mediated through the daylight value the time system maintains.
- **The "fortunes of war" flag.** A small single-byte flag in the data segment, when set, doubles encounters (Section 5). Its writer is one of the sleep-ambush paths (Section 6) and possibly a unique mid-game scripted event.

The threshold is computed by a small probe helper called from the per-turn block; the probe returns the chance-out-of-thirty value, which the per-turn block compares against a fresh roll. When the comparison triggers, the spawner places a monster.

The 30-sided wheel is uniform — the RNG primitive returns a uniform integer in `[1, 30]`. Because the probe is run once per overworld turn, *the encounter rate is per-turn, not per-cell-of-distance*: a party that walks back and forth in place still rolls one chance per turn for an encounter to spawn. Combined with the surface/underworld split, this produces the perceived rate at which roving monsters appear around the party.

## 4. The encounter spawner — terrain branch

When the probe fires, the *spawner* picks a monster type, picks an off-screen tile near the party, writes one new active-object record at that tile, and returns. The newly-spawned monster will appear on the player's next viewport refresh, at which point the overworld's existing path-finder and collision rules take over (the monster moves toward the party using the per-turn animator's AI path, and combat begins on actual contact).

When the player steps onto (or attacks) an active-object tile that the engine recognises as hostile, the world loop calls the combat framer with `entry_mode = 0` (terrain combat). The framer then runs the **terrain-combat setup pipeline** described in `combat.md`. From the encounter system's side, the relevant sub-stages of that pipeline are:

**Arena selection.** The active-object's tile-class byte picks one of sixteen *outdoor arenas* via a small linear formula: `arena_id = (class − 0x40) / 4` for class bytes in the range `0x40..0x7F`, with two known exceptions (a "skiff" class is hard-coded to arena 1 to handle pirate-ship encounters; classes outside the linear range fall through to scripted handling). The sixteen outdoor arenas are stored in the on-disk **outdoor combat arena bank**; each arena is an 11×11 terrain grid with a band of placement metadata (see `formats/cbt.md` for the on-disk format).

**Underworld variant.** If the active-object's stored Z byte indicates the underworld (the high bit of the Z byte is set), a flag is raised that biases later table reads toward underworld variants of the same arena. The arena bank itself is shared between surface and underworld; only the player-Z value the placer writes into each placed monster's record differs.

**Spawn count.** The selected arena's record in a per-arena data-segment table provides the *base monster count*. Three values are sentinels and used unchanged: `1` (single attacker — primarily for town hostility, see Section 7), `8`, and `16` (fixed-size encounters typically used by dungeon arenas with hand-authored counts). All other values are treated as a *maximum* and re-rolled to a uniform integer in `[1, max]`. If the "fortunes of war" flag is set, the count is re-rolled a second time, taking the second roll. The final count is capped at twenty-six.

**Placement and tile assignment.** Each placed monster occupies one of sixteen pre-defined arena cells, indexed by a *placement slot*. Slots 0–15 are walked in identity order for terrain encounters and shuffled (Fisher-Yates) for ambush encounters. The first `count / 4 + 1` monsters are *leaders* and use a separate per-arena tile from a leader-replacement table; the remaining monsters are *followers* and use the arena's signature tile (the tile class derived from the triggering creature). A side-channel predicate suppresses the leader override in some classes — most notably the underworld arenas, where every monster spawns as the same class.

After the pipeline writes all `count` records to the active-object table, the framer enters the round loop and combat plays out as described in `combat.md`.

## 5. The "fortunes of war" doubler

A single byte in the data segment, the "double-encounter" flag, modifies both the random-probe threshold and the spawn-count roll when set. With the flag at zero, the engine behaves as described above. With the flag non-zero:

- Spawn-count rolls are re-rolled once (the second roll is taken). Because the second roll is also uniform on `[1, max]`, this *reduces* the average count slightly — the doubler is more about "fight pacing variability" than about "fight size escalation". Combined with the cap at twenty-six and the minimum of one, the practical effect is "encounters trend toward larger groups in some streaks and smaller in others."
- The probe threshold may be biased upward (encounter probability rises) for as long as the flag is set.

The flag is cleared by certain world-tick boundaries (the next morning, by some accounts), and is set by sleep ambushes that succeeded (Section 6) and possibly by one or two scripted events. The effect is a "string of bad luck" mechanic — a successful ambush makes the next several turns more dangerous.

## 6. Sleep-ambush mechanics

The H-Hole-up-and-camp command (see `input.md` and the rest command's spec) lets the party rest for a number of hours, recovering HP and MP. While resting, the engine runs an *ambush probe* once per simulated hour. The probe is a per-tile chance-roll: rest in safe terrain (a town, a grassy plain, an inn) and the probe's threshold is zero (no ambush possible); rest in dangerous wilderness (mountains, forests, deep underworld) and the threshold is high enough to make multi-hour rests risky.

When the ambush probe fires:

1. The rest is interrupted at the current hour.
2. The combat framer is called with the *ambush* entry-mode flag. The active-object slot passed is the synthesised slot the engine writes to represent the attacker (the type is rolled from a per-terrain monster table).
3. The "fortunes of war" flag is set, so the next several encounters scale upward.
4. The combat-arena placement uses the shuffled (rather than identity) slot order, so the party arrives at randomised cells and the ambushers' positions are unpredictable.

A successful sleep ambush is the engine's main "punish bad camping decisions" mechanic; safe rest sites (inn rooms, towns) skip the probe entirely.

## 7. Town hostility — combat in a town map

Towns and other location-mode maps (castle, keep, dwelling) do not run the random-encounter probe. Instead, they run a **hostility detector**: when a player action — most often Attack, but also some failed conversation outcomes — provokes an NPC, that NPC's record is converted into a hostile active-object slot, and the town loop calls the combat framer with the *ambush* entry-mode flag and the converted slot's index.

The most prominent example is the guards in Lord Blackthorn's keep, who attack the Avatar on sight if the player is wearing the wrong outfit, and the various "hidden hostile" NPCs scattered through the towns. When such a fight starts, the combat framer's terrain-setup helper runs but applies the **town-style override**: the spawn count is forced to one (a single attacker, not a wilderness pack), regardless of what the per-arena table says. The terrain grid is selected from the outdoor arena bank as usual, keyed off the hostile NPC's tile class.

Functionally, town hostility uses the same arena bank and the same placement pipeline as wilderness encounters; the differences are the trigger (NPC interaction rather than random probe) and the count override. The town map itself is not used as a combat arena — the engine swaps to a separate combat arena, plays the fight, and restores the town map on return. The Blackthorn-keep guards-attack scenarios behave the same way as any other town hostility event from the framer's perspective.

## 8. Dungeon room and chest-trap encounters

Inside a dungeon, encounter triggers split into fixed room tiles and Open-handler chest traps:

- **Room tiles.** Stepping onto a tile classified as a "dungeon room" triggers an encounter call into the combat framer. The arena selected comes from the **dungeon-encounter arena bank** (one hundred twelve arenas, in a separate on-disk file from the outdoor bank). The helper treats the room tile's low nibble as a slot and combines it with an adjusted dungeon-scene bank: `arena_index = arena_bank * 16 + (tile & 0x0F)`. Dungeon rooms are pre-authored: the same dungeon-room tile in the same dungeon level always loads the same arena, so the player can learn rooms over multiple visits.
- **Trap chests.** Opening a chest in a dungeon (and only in a dungeon — overworld chests use a separate trap-effect pipeline) may, depending on the chest's roll, trigger a small monster encounter from a fixed sub-set of dungeon arenas (gremlins, rats, slimes). This "encounter trap" is one of several possible chest-trap effects; others are damage, poison, or sleep.

Dungeon arenas are typically smaller and tighter than outdoor arenas, with fewer entry edges. The placement pipeline runs the same way as for terrain encounters: the per-arena spawn-count, the leader/follower split, and the per-arena leader-replacement tile all live in the same data-segment tables.

## 9. The encounter probe and active-object overlap

The encounter spawner places its monster as a new active-object slot (Section 4) — but the active-object table is finite, with thirty-two slots and slot zero reserved for the player. If the table is already full when the spawner fires, the spawn silently fails. This is the engine's natural cap on visible monster density: the player will never see more than thirty-one hostile or neutral entities on the overworld at once.

Spawned monsters live in the table the same way as any other active-object: the per-tick animator (see `active-objects.md`) walks them every turn, advancing animation phase and stepping them along their AI path. Off-screen pruning runs at the end of each turn; a monster that wanders far enough from the party's viewport (more than about thirty-two cells from the scroll base) is silently removed from the table. In effect, the engine maintains a sliding window of active monsters around the party — far-distant encounters are forgotten without ceremony.

## 10. Encounter difficulty scaling

The exact per-arena monster count and per-arena leader tile are *static* — they do not scale with the party's level or the in-world calendar. The only dynamic-adjustment knobs are:

- The base spawn count gets re-rolled into `[1, max]` for non-sentinel max values (Section 4), so a "max twenty" arena produces fights from one to twenty monsters.
- The "fortunes of war" doubler re-rolls the count (Section 5).
- The town-style override forces count one (Section 7).
- The per-class flag table is class-specific, not difficulty-specific, so a slime's split-on-damage behaviour is the same in arena 0 and arena 15. The class itself, though, is keyed off arena (the leader-replacement tile differs between forest and mountain arenas), so different terrains yield different monster mixes — a forest gives orcs and gremlins; mountains give trolls and headlesses.

The result is a difficulty curve that emerges from *what kinds of monsters appear in what kinds of terrain*, rather than from explicit level scaling. The Underworld is harder than Britannia because its arenas are seeded with tougher monster classes, not because the engine adjusts numbers based on the avatar's stats.

The probe's threshold formula is the only place where party state (conscious-member count) feeds into encounter pacing. There is no "monsters get tougher at higher level" mechanic; the player's growing power simply means the same encounter is easier later than it was earlier.

## 11. Returning to the world after combat

The combat framer's restore phase (see `combat.md` Section 4) restores the *active-object table* exactly to its pre-combat state. This means: a monster that was on the world map when combat started is *still on the world map after combat ends*, even if it died inside the arena. Combat death paths can write temporary loot metadata and compute a raw reward unit while the combat-instance table is live, but the currently traced framer restores the backup over those active-object bytes rather than merging them into the world table. For default monster deaths, the temporary loot marker is a class drop-cap byte with an optional high-bit special marker, gated by random checks; it is not itself the durable post-combat loot award.

Durable effects proven at the framer boundary are the ones stored outside the active-object table: party HP/status changes, active-player clearing when the saved active character is dead or asleep, resource consumption by combat actions, combat-round time advances, visibility/stat redraw requests, and any post-combat trap flag handled before the redraw. This settles the framer-level reconciliation question: the wrapper does not merge combat-instance death markers back into the world table. Terrain loot promotion, XP/karma accounting, and trigger-slot removal are caller-side handoff questions until the caller or a deeper cleanup helper is traced. The traced COMBAT-level callers do not forward the raw reward-unit return through the framer; spell-side callers can still consume it before that boundary, as Tremor does by crediting caster experience.

The active-object slot the player attacked to *trigger* the encounter is the clearest boundary case. If the player fled, the original active-object slot is restored *intact* and the monster keeps walking around the world as if nothing happened. If the player won, replacing that slot with loot or removing it from the world must be implemented only once the caller-side reconciliation path is pinned; it is not an automatic effect of the framer restore.

## 12. Hooks into other systems

The encounter system is the connecting tissue between several other systems:

- **Combat.** All triggers ultimately call the combat framer with one of three entry modes; the encounter system's job ends and combat's begins at that call.
- **Overworld.** The per-turn block runs the encounter probe; the overworld's per-turn animator walks the spawned monsters until they make contact with the party.
- **Time.** The probe consumes a single RNG draw per overworld turn but does not advance time. Time advances are mediated by the per-turn cleanup, which the encounter system itself never calls (the world mode loops do).
- **Active objects.** Spawning writes a new active-object record. The placement pipeline writes one record per spawned monster into the combat-instance overlay of the same table.
- **Save / load.** Encounter state is *not* mid-flow saveable — the player cannot save during the probe, the framer's setup phase, or the round loop (the input system gates saves to the world mode loops' wait-for-input states). The "fortunes of war" flag is part of the save image so that a save-and-reload preserves the doubler's effect.
- **Karma and rewards.** Combat computes a per-class raw reward value and temporary drop markers, but the traced COMBAT-level callers do not propagate them through the framer. Tremor is a spell-side exception: it consumes the damage/status helper's return immediately by adding it to the caster's experience with a 9999 cap. The caller-side path that turns ordinary kill results into XP, gold, virtue deltas, loot, or no-op for fled encounters is still open (see `karma.md`).
- **Visibility.** Off-screen monsters are pruned from the active-object table but stay alive conceptually — the engine's "thirty-two-cell sliding window" means the player's far-away wanderings are not tracking specific monsters' positions.

## 13. Open questions and partial information

Several aspects of the encounter system are not fully mapped as of this writing.

- **Exact threshold formula for the random-encounter probe.** The probe consults the under-party tile, the conscious-party-member count, and possibly the daylight value, but the exact arithmetic combining these into the chance-out-of-thirty has not been fully traced. Strong candidates: a per-tile-class base value indexed by tile, multiplied by a small `f(party_size)` factor, possibly biased by daylight. Implementers may match the *observed* feel of the game (mountains very dangerous, roads safe, smaller party more likely to be ambushed) without committing to the exact formula.

- **Selection between leaders and followers.** The first `count / 4 + 1` monsters get the leader tile. *Which* monster slots are "first"? The placer walks the placement-slot array in identity order for terrain encounters, so leaders end up at slots 0, 1, 2, ... — i.e. closer to the centre of the arena. For ambush encounters, the slot array is shuffled before the leader/follower split is computed, so leaders are scattered randomly. This is the only confirmed split rule; the engine has no "boss flag" that overrides it.

- **Per-tile-class arena selection within the sixteen-arena bank.** The linear formula `(class − 0x40) / 4` maps class bytes `0x40..0x7F` to arenas `0..15`, which is a 4:1 collapse — four tile classes share each arena. Which classes share which arenas is an empirical question; the player's expectation that "forests look like forests" suggests the arenas were authored to cluster by terrain visual, but the mapping has not been fully traced.

- **Underworld arena variants.** The combat framer treats `arena_id >= 0x100` as an underworld variant of the same arena, and the per-arena tables are indexed identically — but no separate underworld arena bank exists on disk. The interpretation is that the arena's *terrain grid* is the same on both planes; only the player-Z value the placer writes differs, which changes the lighting model the renderer applies but not the layout. This is consistent with what is observed but not verified end-to-end.

- **Sleep-ambush probability per terrain.** The ambush probe runs once per simulated hour during rest, but the exact per-tile-class threshold is not yet pinned down. Inn rooms and towns are clearly safe; deep wilderness is clearly risky. The middle ground (a meadow on the edge of a forest, a road near a swamp) is unclear.

- **Dungeon chest-trap arena indexing.** Dungeon room-tile indexing is fixed by dungeon scene and trigger low nibble. Chest-trap values may also select from the dungeon arena bank, but that Open-handler mapping has not been fully traced.

- **The "fortunes of war" flag's writer.** The flag is read in two places (the spawn-count reroll and possibly the probe threshold), but its setter is empirical — a sleep-ambush success is one confirmed setter; a mid-game scripted event may be another.

- **Town-hostility's relationship to the arena bank.** Town hostility uses the outdoor arena bank with the count-override forcing one. *Which* outdoor arena it picks for an indoor fight is determined by the hostile NPC's tile class, but the outdoor arenas don't have a "town interior" variant — so the player ends up fighting one guard in, say, a forest-themed arena. This is the engine's behaviour as confirmed, but the visual mismatch suggests there may be an undiscovered "use the town's tile grid as the arena" path that has not yet surfaced in the current analysis.

- **Random-monster type for sleep ambushes.** The ambush probe spawns *some* monster type, but the per-terrain monster table that drives this selection has not been fully labelled. The intuition is "the forest spawns forest-appropriate monsters", and the per-arena leader-replacement table is the most likely source of the type.

- **Caller-side loot and reward consumers.** Combat death paths produce temporary drop markers while the combat instance is live and compute a raw reward unit, but the framer restores the world active-object table exactly and the traced COMBAT-level callers do not forward the reward return through that framer. Tremor proves that spell-side callers may consume the return before the framer restores the world, but it does not explain the ordinary encounter-victory path. The caller or deeper cleanup helper that promotes drops, removes the triggering monster, or applies XP/karma still needs tracing.

## 14. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The 30-sided per-turn random-encounter probe in the overworld loop's per-turn block, including the call-out to the encounter spawner — derived from `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The combat enter/exit framer with its three-way entry-mode dispatch (terrain, ambush, alternate), the active-object backup-and-restore around the round loop, and the post-combat active-player check — derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The terrain-combat setup pipeline, the per-arena spawn-count and leader-replacement tables, the optional Fisher-Yates shuffle for ambush placement, the leader-vs-follower count-and-tile split, the town-style single-attacker override, and the "fortunes of war" double-roll — derived from `u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`.
- The combat-arena file layout — outdoor arena bank versus dungeon-encounter arena bank, 11×11 terrain grid plus placement metadata band, per-record stride, room-trigger arena indexing, and the surface/underworld variant model — derived from `u5-decomp/formats/maps.md` and the dungeon room-entry helper.
