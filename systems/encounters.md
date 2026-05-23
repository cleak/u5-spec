# Encounters

## 1. Overview

Ultima V's *encounter system* is the layer that decides **when combat starts**, **what is fought**, and **where it is fought**. It is distinct from combat itself: combat is the round-by-round arena play that begins after an encounter has been picked; encounters are the chance-and-script logic that turns a quiet step on the overworld, an attempt to sleep in a wood, or a dungeon room transition into a populated arena.

There are three arena-encounter trigger families in the running game:

- **Random overworld encounters.** On eligible overworld epilogue turns, a chance-roll decides whether a hostile monster spawns near the party. The roll is keyed off terrain, Z plane, and hour; surface roads and similar safe bands suppress daytime encounters but still receive the night-time boost.
- **Scripted encounters.** A small, hand-authored set of locations and events force a specific encounter when reached: ambush tiles in story-driven keeps, the duel with Lord Blackthorn, a few unique boss meetings. Blackthorn's follow-on capture and rescue scenes are specified in `systems/blackthorn.md`.
- **Dungeon room encounters.** Stepping onto certain dungeon-room cells loads a fixed dungeon arena from a separate on-disk bank.

Once any arena trigger fires, the same combat-enter framing function runs - combat is a function call from the world or dungeon mode loop perspective (see `combat.md`). The encounter system's job ends when that call begins; everything after the framer's save phase belongs to combat. This spec covers the trigger-side mechanics, the arena-selection logic, the class-row spawn-count and replacement-tile pipeline, and the small set of side mechanics - sleep ambushes and "fortunes-of-war" doublings - that change encounter pacing.

## 2. The three triggers

### 2.1 Random overworld encounters

Every turn the overworld mode loop runs its per-turn block (see
`overworld.md`), and that block contains an *encounter probe*. The probe runs
when the overworld animator's pendulum gates allow the epilogue to continue:

1. Roll a uniform integer in `[1, 30]` from the engine's RNG primitive (see `prng.md`).
2. Compare the roll against a *threshold* derived from the tile under the
   party, Z plane, and hour (Section 3).
3. If the threshold exceeds the roll, fire the *encounter spawner*, which writes one new monster into the active-object table on a tile near the party and lets the world loop's existing collision logic do the rest.

Note the inverted comparison: the threshold is the chance-of-encounter expressed on the same 1..30 scale as the roll. A higher threshold means encounters more often. The probe never *enters combat directly* — it spawns a monster as an active object, and combat starts the moment the player or that monster steps into the other's tile.

The probe is an overworld-mode-only routine. The town loop's per-turn block does
not run it; town hostility is handled by town/NPC alarm and arrest paths,
not by the arena-encounter system. The dungeon mode loop has its own
room-trigger logic (Section 8).
Slow-water `Q` timing and the traced horse/carpet transport-marker pendulum
pairs therefore reduce the effective random-encounter cadence by skipping some
probe opportunities; they do not change the threshold formula itself.

### 2.2 Scripted encounters

A scripted encounter is one where the engine, on detecting a particular tile,
event, or rest/camp interruption, calls the combat framer with a non-zero
entry-mode flag. The framer's three-way dispatch (see `combat.md` Section 2)
routes such calls past the ordinary terrain random-arena selection into either
the *ambush* setup helper or the *rest/camp alternate* setup helper, depending
on which flag bit was set. From the encounter system's perspective:

- **Ambush flag.** Indicates that the calling code already has the relevant
  active-object slot identified and is requesting the framer's ambush setup
  branch. This dispatch uses a separate setup helper, not the ordinary terrain
  helper. Do not infer this path's arena choice, monster count, or placement
  order from the dormant Fisher-Yates branch inside the terrain helper; that
  branch has no traced live caller.
- **Rest/camp alternate flag.** Used by the H-Hole-up rest/camp path. The
  alternate target is the CMDS H-Hole-up helper, not an SJOG or scripted-fight
  dispatcher. It owns rest-surface checks, rest-local status cleanup, the
  sleep-ambush interruption predicate, and the selected monster row. It may
  return a nonzero predicate to finish the rest outcome without running combat;
  otherwise the framer continues into the combat round loop after the rest/camp
  setup has prepared the encounter.

Scripted arena encounters are dispatched from overworld special-tile handlers and
a small handful of overworld tiles that always force a fight. Rest/camp interruptions
are a separate caller into the same framer rather than a tile-trigger family.
The list is hand-authored; there is no general "this tile triggers a scripted
encounter" mechanism beyond the per-tile dispatch.

Ambush and camp-attack scenes can also use combat's reveal-slot helper. In that
mode, the arena starts with up to eight hidden reveal coordinates. Stepping onto
one consumes that reveal coordinate and can stamp one or two terrain cells with
the associated reveal tile before redrawing the arena. This is a combat-local
terrain reveal, not a persistent world-map mutation.

### 2.3 Dungeon room encounters

Dungeon mode runs its own per-turn block, but it does not roll the random-encounter probe. Instead, certain tile classes inside a dungeon level trigger a deterministic combat call: stepping onto a *room* tile loads a fixed arena from the dungeon-encounter arena bank. Room arena selection is keyed by the active dungeon scene and the trigger cell's low nibble. The rest of the combat pipeline — count, placement, leader/follower split — runs after the room arena has been selected.

Dungeon encounters do not consult the overworld terrain class or the time of day. The dungeon-encounter arena bank is much larger than the overworld bank (one hundred twelve records versus sixteen), reflecting the wider variety of fixed-content dungeon situations.

## 3. The probability of a random encounter

The probe runs against a 30-sided roll. It returns a small threshold from the
party's world plane, the tile underfoot, and the hour:

| Condition | Threshold |
|---|---:|
| Underworld plane | 3, with no hour-of-day adjustment |
| Surface no-encounter tile band `0x20..0x26` | 0 by day, 3 at hours `0..4` |
| Surface tile `0x04` or wilderness band `0x09..0x0F` | 2 by day, 5 at hours `0..4` |
| Any other surface tile | 1 by day, 4 at hours `0..4` |

The underworld plane short-circuits to threshold `3`. On the surface, hours
`0..4` add the night-time boost shown above. The per-turn block then rolls
`random(1, 30)` and spawns when `roll < threshold`. The effective per-turn spawn
chance is therefore `(threshold - 1) / 30`, with thresholds `0` and `1` both
producing no encounter.

Because the probe is tied to the overworld epilogue, the base encounter rate is
per eligible turn, not per-cell-of-distance: a party that walks back and forth
in place still rolls one chance per eligible turn for an encounter to spawn.
The pendulum gates described in `overworld.md` can reduce the number of
eligible turns before this formula is reached.

## 4. The encounter spawner — terrain branch

When the probe fires, the *spawner* picks a monster type, picks an off-screen tile near the party, writes one new active-object record at that tile, and returns. The newly-spawned monster will appear on the player's next viewport refresh, at which point the overworld's existing path-finder and collision rules take over (the monster moves toward the party using the per-turn animator's AI path, and combat begins on actual contact).

The spawner is retry-based:

1. Roll a candidate coordinate inside the current 32-by-32 scroll window.
2. Accept only coordinates whose absolute X and Y separations from the party
   are both greater than six and both less than two hundred fifty. The first
   bound keeps the spawn outside the immediate visible center; the second bound
   rejects wrapped-near coordinates on the 256-by-256 torus.
3. Read the world tile at that candidate coordinate and classify it into a
   monster bucket. A zero result rejects the candidate and restarts the loop.
4. Reject the sea-creature class on shore/harbor high-nibble terrain and retry.
5. After one hundred twenty-eight rejected candidates, return silently without
   spawning.

On success, the spawner acquires or evicts an active-object slot and initializes
it as a monster record with tile, tile mirror, X, Y, current Z plane, and a
zero auxiliary byte. Sea-creature class spawns receive an auxiliary value of one
hundred, which seeds their outdoor animation/wander counter.

Monster selection is terrain-bucketed before the active-object write:

| Candidate terrain | Selection rule |
|---|---|
| Surface tile 1 after the low-tile allowance gate | One-in-seven chance of a special animated active-object class whose outdoor engagement is the whirlpool/forced-underworld branch; otherwise use the surface default/aquatic bucket. |
| Terrain tile 7 | One-in-three chance of the outdoor sea-serpent adjacency class; a failed special roll rejects the candidate. |
| Terrain tile 4 on the full underworld plane marker | Directly selects the Rot Worm sprite run. Other tile-4 cases continue to the land bucket selected by plane. |
| Surface town-outline tiles `0x0C` and `0x0D` | Reject. |
| Low tiles below 4, shore/harbor `0x60..0x6F`, roads `0xD4..0xD7`, and bridge/passable `0xE4..0xE7` | Run an extra one-in-four allowance die before any bucket selection; a failed die rejects. Allowed surface candidates use the surface default/aquatic bucket unless they take the tile-1 special branch above. Allowed underworld candidates use the underworld default/aquatic bucket. |
| Tile ids below `0x10` after the special and hard-reject cases, plus tile ids `0x30..0x33` | Use the land bucket selected by plane: surface land on the surface, underworld land below. |
| Other tile ids at or above `0x10` | Reject. |

The picker rolls on a 0..255 scale, walks weights in order, and returns the
first row whose cumulative weight covers the roll. Adjacent bucket data is
stored compactly in the original, but a clean implementation should treat this
as four semantic weighted tables. The rows below are ordered, and each weight
is out of 256.

**Surface default / aquatic bucket**

| Weight | Payload family |
|---:|---|
| 72 | Shark sprite run (`0x8C..0x8F`) |
| 72 | Squid sprite run (`0x84..0x87`) |
| 40 | Sea Serpent sprite run (`0x88..0x8B`) |
| 38 | Sea Horse sprite run (`0x80..0x83`) |
| 34 | Pirate-ship / water-creature facing frames (`0x2C..0x2F`) |

**Underworld default / aquatic bucket**

| Weight | Payload family |
|---:|---|
| 128 | Squid sprite run (`0x84..0x87`) |
| 128 | Sea Serpent sprite run (`0x88..0x8B`) |

**Surface land bucket**

| Weight | Payload family |
|---:|---|
| 60 | Orc sprite run (`0xC0..0xC3`) |
| 50 | Python sprite run (`0xC8..0xCB`) |
| 40 | Giant Rat sprite run (`0x90..0x93`) |
| 30 | Giant Spider sprite run (`0x98..0x9B`) |
| 20 | Insect Swarm sprite run (`0xBC..0xBF`) |
| 15 | Skeleton sprite run (`0xC4..0xC7`) |
| 15 | Headless sprite run (`0xD0..0xD3`) |
| 10 | Troll sprite run (`0xE4..0xE7`) |
| 10 | Ettin sprite run (`0xCC..0xCF`) |
| 3 | Wisp sprite run (`0xD4..0xD7`) |
| 2 | Dragon sprite run (`0xDC..0xDF`) |
| 1 | Daemon sprite run (`0xD8..0xDB`) |

**Underworld land bucket**

| Weight | Payload family |
|---:|---|
| 64 | Bat sprite run (`0x94..0x97`) |
| 56 | Giant Rat sprite run (`0x90..0x93`) |
| 56 | Giant Spider sprite run (`0x98..0x9B`) |
| 32 | Mongbat sprite run (`0xF0..0xF3`) |
| 32 | Corpser sprite run (`0xF4..0xF7`) |
| 8 | Daemon sprite run (`0xD8..0xDB`) |
| 8 | Dragon sprite run (`0xDC..0xDF`) |

The bucket payload is an **overworld active-object sprite byte**, not a combat
class id and not a town-map marker byte. Interpret it in the active-object
sprite domain before starting combat. This matters for byte values that have
different meanings in other domains: for example, `0xC8` is a town chair marker
inside town tile grids, but an overworld random-spawn payload in the monster
sprite run for Python-class outdoor actors.

The currently named payload families are:

| Payload family | Public interpretation |
|---|---|
| `0x2C..0x2F` | Pirate-ship / water-creature facing frames. The spawner seeds the auxiliary wander counter for this family and rejects its first frame on shore/harbor high-nibble terrain. |
| `0x80..0x83` | Sea Horse sprite run. |
| `0x84..0x87` | Squid sprite run. |
| `0x88..0x8B` | Sea Serpent sprite run. |
| `0x8C..0x8F` | Shark sprite run. |
| `0x90..0x93` | Giant Rat sprite run. |
| `0x94..0x97` | Bat sprite run. |
| `0x98..0x9B` | Giant Spider sprite run. |
| `0xBC..0xBF` | Insect Swarm sprite run. |
| `0xC0..0xC3` | Orc sprite run. |
| `0xC4..0xC7` | Skeleton sprite run. |
| `0xC8..0xCB` | Python sprite run in the overworld active-object domain. |
| `0xCC..0xCF` | Ettin sprite run. |
| `0xD0..0xD3` | Headless sprite run. |
| `0xD4..0xD7` | Wisp sprite run. |
| `0xD8..0xDB` | Daemon sprite run. |
| `0xDC..0xDF` | Dragon sprite run; the first frame also participates in a special outdoor near-range pull/effect path. |
| `0xE0..0xE3` | Outdoor sea-serpent adjacency family. Do not infer the combat Sand Trap row from this overworld-active-object behavior without an explicit combat spawn. |
| `0xE4..0xE7` | Troll sprite run. |
| `0xEC..0xEF` | Outdoor whirlpool / forced-underworld animated family. Do not treat this as a normal random Wisp encounter despite its byte proximity to monster sprite runs. |
| `0xF0..0xF3` | Mongbat sprite run. |
| `0xF4..0xF7` | Corpser sprite run. |
| `0xF8..0xFB` | Rot Worm sprite run. The random-spawn selector reaches this through a direct special terrain branch rather than through one of the weighted buckets. |

When the player steps onto (or attacks) an active-object tile that the engine recognises as hostile, the world loop calls the combat framer with `entry_mode = 0` (terrain combat). The framer then runs the **terrain-combat setup pipeline** described in `combat.md`. From the encounter system's side, the relevant sub-stages of that pipeline are:

**Arena selection.** The active-object record's byte 0 picks one of sixteen
*outdoor arenas*. The selector reads the hostile active object's own type/frame
byte; it does not inspect the party transport marker or the terrain tile under
the object. For active-object bytes in `0x40..0x7F`, the linear formula is
`arena_id = (byte0 - 0x40) / 4`. For the pirate/water-creature special case,
the selector first masks byte 0 with `0xFC`; therefore every byte in
`0x2C..0x2F` hard-codes outdoor arena 1. The sixteen outdoor arenas are stored
in the on-disk **outdoor combat arena bank**; each arena is an 11x11 terrain
grid with a band of placement metadata (see `formats/cbt.md` for the on-disk
format).

The range collapse is exact:

| Outdoor arena | Trigger class bytes |
|--------------:|---------------------|
| 0 | `0x40..0x43` |
| 1 | `0x44..0x47`; also active-object byte `0x2C..0x2F` for the pirate/water-creature special case |
| 2 | `0x48..0x4B` |
| 3 | `0x4C..0x4F` |
| 4 | `0x50..0x53` |
| 5 | `0x54..0x57` |
| 6 | `0x58..0x5B` |
| 7 | `0x5C..0x5F` |
| 8 | `0x60..0x63` |
| 9 | `0x64..0x67` |
| 10 | `0x68..0x6B` |
| 11 | `0x6C..0x6F` |
| 12 | `0x70..0x73` |
| 13 | `0x74..0x77` |
| 14 | `0x78..0x7B` |
| 15 | `0x7C..0x7F` |

This table is an arena-selection table, not a monster visual-name table. The
visual meaning of any given trigger byte remains owned by the active-object and
tile/monster catalogs.

**Underworld variant.** If the active-object's stored Z byte indicates the underworld (the high bit of the Z byte is set), a flag is raised that biases later table reads toward underworld variants of the same arena. The arena bank itself is shared between surface and underworld; only the player-Z value the placer writes into each placed monster's record differs.

**Spawn count.** The encounter's base class supplies the base monster count
from its combat-class stat row. In ordinary terrain combat the selected arena
index and the base class id are the same value, so this behaves like a
per-arena count for the stock outdoor arena ids; it is stored with class stats,
not as byte zero of a separate arena metadata row. Three values are sentinels
and used unchanged: `1` (single-attacker terrain-helper cases), `8`, and `16`
(fixed-size encounters typically used by dungeon arenas with hand-authored
counts). All other values are treated as a *maximum* and re-rolled to a uniform
integer in `[1, max]`. If the "fortunes of war" flag is set, the count is
re-rolled a second time, taking the second roll. The final count is capped at
twenty-six.

**Placement and tile assignment.** Each placed monster occupies one of sixteen
arena cells, indexed by a *placement slot*. The selected `BRIT.CBT` arena
record supplies the slot coordinates; the loader copies them into resident
scratch tables before the setup helper reads them. Slots 0-15 are walked in
identity order for ordinary terrain encounters. The terrain setup helper
contains a dormant Fisher-Yates branch, but the only traced live terrain caller
leaves it inactive; ambush and rest/camp alternate setup should be specified
from their own helpers rather than from that branch. The first monster uses the
arena's base tile class, derived from the triggering creature. Later monsters
normally use that same base tile. For spawn indexes below the `count / 4 + 1`
threshold, each monster rolls a one-in-nine replacement check; only a zero
result uses the separate per-arena replacement tile. Later spawn indexes never
roll for the replacement tile.

After the pipeline writes all `count` records to the active-object table, the framer enters the round loop and combat plays out as described in `combat.md`.

## 5. The "fortunes of war" doubler

A single runtime byte in the data segment, the "double-encounter" flag, modifies the
spawn-count roll when set. With the flag at zero, the engine behaves as
described above. With the flag non-zero:

- Spawn-count rolls are re-rolled once and the second roll is taken. Because the second roll is also uniform on `[1, max]`, this is not a guaranteed increase. The compatibility rule is simply "replace the first count roll with the second while the flag is non-zero."
- The flag is not part of the traced tile/Z/hour encounter-probe formula.

Current traced notes prove a terrain-setup read and a clear in the 28-day
month-boundary bundle. Broad static sweeps of the currently analysed binaries
have not found a gameplay writer that sets the byte. The flag also lives in the
flat `SAVED.GAM` image, so explicit save/load preserves its current byte value.
The public compatibility contract is therefore: preserve the byte, clear it
only at the 28-day rollover, and treat any non-zero value as the count-reroll
modifier when terrain combat setup reads it. Sleep ambushes and scripted events
must not be modeled as producers unless a future write site proves that path.

## 6. Sleep-ambush mechanics

The H-Hole-up-and-camp command (see `commands.md` and
`rest-and-camp.md`) lets the party rest for a
requested number of hours. The encounter-relevant part of the command is a
rest-interruption path, not a direct use of the overworld random-encounter
probe from Section 3.

The confirmed rest loop is:

1. The active scene routes H either to the wilderness/dungeon rest-with-watch
   wrapper or, in town-family locations, to the bed/inn-only hours path.
2. The handler probes whether the current tile permits rest, walks the party
   slots, prints the sleep narration, and handles sleeping/poisoned/dead member
   cleanup.
3. The hours path advances requested rest through a caller-owned loop. In the
   traced town-hours path, one bounded burst of up to sixteen schedule/world-tick
   passes runs after a nonzero duration digit is accepted, then elapsed rest
   advances through repeated ten-minute cleanup calls.
4. After each interruption/refusal check, the handler stops immediately if the
   rest path has been interrupted and branches to the ambush or thrown-out path;
   elapsed time and any completed per-tick side effects are not rewound.
5. If the loop completes without interruption, the command prints the rested
   result, restores sleeping members to good status, applies capped HP recovery
   to eligible living party members, and stamps the current rest/camp marker.

When an interruption becomes a combat encounter, the combat framer has entered
its alternate rest/camp setup path rather than the ordinary terrain setup path.
Combat-local placement and reveal behavior after that handoff remain owned by
`systems/combat.md`.

The interruption predicate is now pinned down: after the rest entry and
rest-surface gates accept a dangerous wilderness or dungeon rest pass, the rest
handler rolls the shared integer PRNG across sixty-four outcomes. The zero
outcome interrupts into the sleep-ambush branch; every nonzero outcome continues
rest. This gives a 1-in-64 interruption chance per eligible predicate
invocation.

The sleep-ambush chooser is not terrain-weighted. On an interruption, it picks
one of eight resident monster rows with equal row probability:

| Rows | Sleep-ambush monster |
|------|----------------------|
| 2 | Giant Rat |
| 1 | Troll |
| 1 | Bat |
| 1 | Slime |
| 1 | Giant Spider |
| 1 | Gremlin |
| 1 | Headless |

Because Giant Rat occupies two rows, its effective share is 2 in 8; each other
listed monster is 1 in 8. This row chooser is separate from the overworld
tile/Z/hour encounter probe and from the outdoor random-spawn terrain buckets.

After row selection, the rest helper prints the ambush result and restores its
rest-local party status snapshot before the round loop can start. Preexisting
poison is preserved, other participating sleepers/watch participants are
restored to Good, and Dead members remain outside the restoration. The selected
row stays inside the CMDS alternate rest/camp setup path; ordinary overworld
spawn-coordinate retries and random-spawn terrain buckets are not part of this
sleep-ambush path. Any remaining exactness in this branch is low-level
sound/delay/prompt presentation, not the monster-row chooser or
status-restoration ordering.

## 7. Town hostility boundary

Towns and other location-mode maps do not run the random-encounter probe and do not use the arena-encounter setup for ordinary hostile-NPC events in the traced town overlay. Hostility remains a town/NPC-system behavior: A-Attack can kill or clear town NPCs and can trigger the alarm sweep, the scheduler can report guard-catch or attack events, and post-action cleanup routes those events through arrest, pacify, death, or slot-clear paths.

The combat framer's ambush entry branch is real, but the current resolved `0x7C3E` target is the DNGLOOK room-NPC setup entry used by dungeon/rest-style room setup, not proof that town hostile-NPC events swap to an outdoor or town-derived `.CBT` arena. Keep town hostility specified in `systems/town-mode.md` unless a separate live combat-framer caller is traced.

## 8. Dungeon room encounters

Inside a dungeon, the traced fixed encounter trigger is the room tile:

Stepping onto a tile classified as a "dungeon room" triggers an encounter call into the combat framer. The arena selected comes from the **dungeon-encounter arena bank** (one hundred twelve arenas, in a separate on-disk file from the outdoor bank). The helper treats the room tile's low nibble as a slot and combines it with an adjusted dungeon-scene bank: `arena_index = arena_bank * 16 + (tile & 0x0F)`. Dungeon rooms are pre-authored: the same dungeon-room tile in the same dungeon level always loads the same arena, so the player can learn rooms over multiple visits.

No traced dungeon chest path currently loads `DUNGEON.CBT`. Dungeon chest
opening, lock-picking, trap narration, and loot generation are owned by the
SJOG command helpers described in `systems/containers.md` and
`systems/doors-and-z-transitions.md`. If future analysis finds a chest-triggered
combat route, it should be added as a separate caller rather than inferred from
the room-entry lookup.

Dungeon arenas are typically smaller and tighter than outdoor arenas, with fewer entry edges. The placement pipeline uses the same count/replacement model as terrain encounters: the count seed is a class stat field, while the leader/follower replacement tile lives in a separate encounter table.

## 9. The encounter probe and active-object overlap

The encounter spawner places its monster as a new active-object slot (Section 4) — but the active-object table is finite, with thirty-two slots and slot zero reserved for the player. If the table is already full when the spawner fires, the spawn silently fails. This is the engine's natural cap on visible monster density: the player will never see more than thirty-one hostile or neutral entities on the overworld at once.

Spawned monsters live in the table the same way as any other active-object: the per-tick animator (see `active-objects.md`) walks them every turn, advancing animation phase and stepping them along their AI path. Off-screen pruning runs at the end of each turn; a monster that wanders far enough from the party's viewport (more than about thirty-two cells from the scroll base) is silently removed from the table. In effect, the engine maintains a sliding window of active monsters around the party — far-distant encounters are forgotten without ceremony.

## 10. Encounter difficulty scaling

The exact per-arena monster count and per-arena leader tile are *static* — they do not scale with the party's level or the in-world calendar. The only dynamic-adjustment knobs are:

- The base spawn count gets re-rolled into `[1, max]` for non-sentinel max values (Section 4), so a "max twenty" arena produces fights from one to twenty monsters.
- The "fortunes of war" doubler re-rolls the count (Section 5).
- The terrain setup helper has an indoor-scene count-one override, but traced
  town hostile-NPC handling stays in town/NPC alarm paths rather than arena
  combat (Section 7).
- The per-class flag table is class-specific, not difficulty-specific, so a slime's split-on-damage behaviour is the same in arena 0 and arena 15. The class itself, though, is keyed off arena (the leader-replacement tile differs between forest and mountain arenas), so different terrains yield different monster mixes — a forest gives orcs and gremlins; mountains give trolls and headlesses.

The result is a difficulty curve that emerges from *what kinds of monsters appear in what kinds of terrain*, rather than from explicit level scaling. The Underworld is harder than Britannia because its arenas are seeded with tougher monster classes, not because the engine adjusts numbers based on the avatar's stats.

The probe's threshold formula does not inspect party level or conscious-party
count. There is no "monsters get tougher at higher level" mechanic; the player's
growing power simply means the same encounter is easier later than it was
earlier.

## 11. Returning to the world after combat

The combat framer's restore phase (see `combat.md` Section 4) restores the *active-object table* exactly to its pre-combat state. This means: at the framer boundary, a monster that was on the world map when combat started is still on the world map after combat ends, even if it died inside the arena. Combat death paths can write temporary loot metadata and compute a raw reward unit while the combat-instance table is live, but the framer restores the backup over those active-object bytes rather than merging them into the world table. For default monster deaths, the temporary loot marker is a class drop-cap byte with an optional high-bit special marker, gated by random checks; it is not itself the durable post-combat loot award.

Durable effects proven at the framer boundary are the ones stored outside the active-object table: party HP/status changes, active-player clearing when the saved active character is dead or asleep, resource consumption by combat actions, combat-round time advances, visibility/stat redraw requests, and any resident tile-graphics restoration call handled before the redraw. This settles the framer-level reconciliation question: the wrapper does not merge combat-instance death markers back into the world table. Ordinary attack and spell experience can be credited before that boundary by the damage/status caller when the attacker is a living party actor; the framer does not do that work itself.

The ordinary resident terrain-target caller performs the durable trigger-slot
reconciliation after the framer returns. It invokes a shared post-combat object
helper with the original active-object slot. That helper restores the saved
world-object table, then, for the ordinary terrain path, either clears bytes 0
through 4 of the original trigger slot or rewrites a restored `0x2C..0x2F`
body-family slot into the persistent body/retrieval state when combat set the
exit-message state. This is the traced trigger-removal/body-persistence path;
it is result-blind at the wrapper level and does not inspect the round-loop
return value as a separate victory award.

One older hypothesis placed post-fight loot handoff in the shared SJOG command
overlay. Current call coverage does not support that as a public contract: the
COMBAT-to-SJOG calls are in-round command delegates and combat helpers, not an
after-victory sweep that survives the framer's active-object restore.

The active-object slot the player attacked to *trigger* the encounter is the clearest boundary case. The framer itself restores it intact, but the ordinary terrain-target caller immediately follows with the original-slot reconciler. Implementations must keep those two stages separate: framer restore first, then caller-owned trigger-slot clear or body-state rewrite for the slot that launched the encounter. No traced helper sweeps every killed combat actor into world loot.

## 12. Hooks into other systems

The encounter system is the connecting tissue between several other systems:

- **Combat.** All arena-encounter triggers ultimately call the combat framer
  with one of three entry modes; the encounter system's job ends and combat's
  begins at that call.
- **Overworld.** The per-turn block runs the encounter probe; the overworld's per-turn animator walks the spawned monsters until they make contact with the party.
- **Time.** The probe consumes a single RNG draw per overworld turn but does not advance time. Time advances are mediated by the per-turn cleanup, which the encounter system itself never calls (the world mode loops do).
- **Active objects.** Spawning writes a new active-object record. The placement pipeline writes one record per spawned monster into the combat-instance overlay of the same table.
- **Save / load.** Encounter state is *not* mid-flow saveable — the player cannot save during the probe, the framer's setup phase, or the round loop (the input system gates saves to the world mode loops' wait-for-input states). The "fortunes of war" flag is a save-image tail byte documented in `formats/saved-gam.md`, so explicit save/load preserves its resident value even though no gameplay setter is currently traced.
- **Karma and rewards.** Combat computes a per-class raw reward value and temporary drop markers, but the framer does not propagate either as a post-combat award. Combat-local attack and spell/effect callers can consume the damage/status helper's return immediately by adding it to a living party attacker's experience with a `9999` cap. The ordinary terrain-target caller removes or rewrites the original trigger slot after the framer returns. No traced combat-exit path adds party gold, applies virtue deltas, promotes arbitrary killed-monster drops, or emits a separate victory bonus. Food/gold from a body-like post-combat result is deferred to later Search/Get interaction with the rewritten slot (see `containers.md` and `karma.md`).
- **Visibility.** Off-screen monsters are pruned from the active-object table but stay alive conceptually — the engine's "thirty-two-cell sliding window" means the player's far-away wanderings are not tracking specific monsters' positions.

## 13. Encounter Boundaries

The encounter contract is complete at system depth: random-overworld trigger
probability, spawn placement, terrain buckets, active-object handoff, terrain
combat setup, sleep-ambush interruption, dungeon room arena selection,
combat-framer ownership, town-hostility non-encounter ownership, and
caller-side trigger-slot reconciliation are specified. The remaining notes in
this section are ownership boundaries: they identify presentation/catalog work
owned outside the encounter system, source-free data-publication choices for
engines that do not load the original data, or future-evidence hooks that do not
change the current encounter contract.

- **Replacement-tile selection.** Only spawn indexes below the `count / 4 + 1` threshold can use the per-arena replacement tile, and each eligible index still needs a one-in-nine random zero roll. In ordinary terrain encounters, the placer walks the placement-slot array in identity order, so replacement-eligible indexes occupy the earliest placement slots. A dormant terrain-helper branch would shuffle the slot array before placement, but no traced live caller reaches that branch. The engine has no deterministic "boss flag" that forces every early slot to use the replacement tile.

- **Underworld arena variants.** The combat framer treats `arena_id >= 0x100` as an underworld variant of the same arena, and the per-arena tables are indexed identically — no separate underworld arena bank exists on disk. The arena terrain grid is therefore the same on both planes; the player-Z value written by the placer selects underworld lighting/renderer treatment rather than a different encounter-layout source.

- **Ambush reveal table values.** The combat-local reveal helper and clean
  record shape are specified in `systems/combat.md` and `formats/data-ovl.md`.
  A byte-compatible engine that loads the original resident data should consume
  those records from `DATA.OVL`; do not copy the shipped coordinate/tile rows
  into public prose. Only a source-free reauthored-data target would need a
  separately curated semantic table.

- **Sleep-ambush setup internals.** The H-Hole-Up rest loop and its
  interruption boundary are mapped, including the town-hours path's single
  bounded scheduler/world-tick burst, repeated ten-minute cleanup loop, the
  overworld/dungeon duration prompt, optional watch prompt and Good-status
  watcher validation, the dangerous-rest 1-in-64 interruption predicate, the
  eight-row monster chooser, the caller-side ambush-message/status restoration
  ordering, and the CMDS alternate setup target. Low-level string-window,
  audio/delay, and refresh-helper parity belongs to rest/camp presentation QA
  rather than encounter trigger or row-selection behavior.

- **Dungeon chest encounter callers.** No traced dungeon chest path currently
  selects from the dungeon arena bank. Keep any future chest-triggered combat
  route separate from the room-tile formula until a caller is identified.

- **The "fortunes of war" flag.** The flag is read by the spawn-count reroll
  path, saved/loaded as resident state, and cleared by the 28-day
  month-boundary bundle. Current static sweeps found no gameplay setter, so the
  public encounter rule is the read/save/load/month-clear/count-reroll
  behaviour unless future evidence identifies a live producer.

- **Town hostility boundary.** Town hostility is not an arena-encounter path in
  the traced town overlay. A-Attack, alarm scatter, guard arrest, pacify, death,
  and slot-clear behavior are owned by `systems/town-mode.md`; do not model
  them as `.CBT` combat unless a separate live combat-framer caller is traced.

- **Random-spawn payload visuals.** The overworld random-spawn bucket
  mechanics, placement retry loop, ordered weighted memberships, and named
  payload families are public. Per-frame visual atlas verification for
  ambiguous outdoor animated families belongs to `catalogs/tile-catalog.md` and
  renderer/presentation QA, not encounter trigger or placement behaviour.


- **Caller-side post-combat consumers.** Combat death paths produce temporary drop markers while the combat instance is live and compute a raw reward unit, but the framer restores the world active-object table exactly and does not turn those values into a post-combat award. Ordinary attack/spell experience credit is handled before the framer returns when a party attacker owns the damage call. The ordinary terrain-target caller now has a traced original-slot reconciler; no traced combat-exit consumer promotes arbitrary killed-monster drops, adds gold, changes karma, or grants a separate victory bonus. If the reconciler rewrites the original trigger slot into body/retrieval state, later Search/Get owns any food/gold/plague result.
- **SJOG post-fight handoff.** Current COMBAT call coverage does not show a
  post-fight SJOG loot handoff. SJOG remains relevant for in-combat delegated
  commands and shared helpers, but not as the missing durable loot consumer.

## 14. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The H-Hole-Up rest handler, including scene routing, party status cleanup,
  capped HP recovery, camp marker writes, the 1-in-64 interruption predicate,
  the eight-row sleep-ambush monster chooser, ambush-message/status restoration
  ordering, and the hours-loop interruption boundary -- derived from
  `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md` and cross-checked
  against `u5-decomp/notes/npc_walker_callers_2026-05-08.md`.

- Random-spawn placement and terrain bucket provenance:
  `u5-decomp/functions/MAINOUT_OVL/0x0FC4_encounter_spawn.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x0F4E_encounter_pick_coord.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x0E4E_encounter_pick_monster.md`, and
  `u5-decomp/functions/MAINOUT_OVL/0x0E04_table_weighted_pick.md`, with
  DATA.OVL address conversion cross-checked against
  `u5-decomp/formats/data-ovl.md`.
- Random-spawn active-object payload behavior and special outdoor animated
  families:
  `u5-decomp/functions/MAINOUT_OVL/0x105C_mainout_tile_classifier.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x131A_active_object_animate.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x1248_active_object_engage.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x1578_apply_step.md`, and
  the public sprite-run cross-checks in `catalogs/monster-bestiary.md` and
  `catalogs/tile-catalog.md`.

- The 30-sided per-turn random-encounter probe in the overworld loop's per-turn block, including the call-out to the encounter spawner — derived from `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The DOSBox probe that pinned the tile/Z/hour threshold formula -- `u5-decomp/notes/dosbox_probes_2026-05-07.md`.
- The shared integer PRNG used for the 30-sided roll -- `u5-decomp/functions/ULTIMA_EXE/0x2092_prng_range.md`.
- The combat enter/exit framer with its three-way entry-mode dispatch (terrain, ambush, alternate), the active-object backup-and-restore around the round loop, and the post-combat active-player check — derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The absence of a traced post-fight SJOG loot handoff from COMBAT call
  coverage -- derived from `u5-decomp/functions/COMBAT_OVL/_OVERVIEW.md` and
  `u5-decomp/notes/system-trace_combat-round.md`.
- The resident terrain-target wrapper's post-combat original-slot reconciler
  -- derived from `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`
  and `u5-decomp/functions/SJOG_OVL/0x1B34_sjog_aux_combat_helpers.md`.
- The ambush/camp-attack reveal-slot helper, including mode gating, one-shot
  reveal-coordinate consumption, terrain stamping, and redraw ordering --
  derived from
  `u5-decomp/functions/COMBAT_OVL/0x111A_reveal_ambush_at_coord.md`.
- The terrain-combat setup pipeline, the class-row spawn-count field and replacement-tile table, the dormant optional Fisher-Yates branch in the terrain helper, the early-spawn replacement roll, the town-style single-attacker override, and the "fortunes of war" double-roll — derived from `u5-decomp/functions/ULTIMA_EXE/0x6BC2_combat_setup_terrain.md`.
- The combat-arena file layout — outdoor arena bank versus dungeon-encounter arena bank, 11×11 terrain grid plus placement metadata band, per-record stride, room-trigger arena indexing, and the surface/underworld variant model — derived from `u5-decomp/formats/maps.md` and the dungeon room-entry helper.
