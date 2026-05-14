# Rest And Camp

## 1. Scope

This spec covers the H-Hole-up command family: outdoor camping, town/inn bed
rest, the simulated-hours loop, rest interruption, party recovery, and the
special Lord British-in-disguise camp event.

It does not own ordinary shop lodging, healer services, food merchants, or
combat rounds. Those remain in `systems/shops.md`, `systems/magic.md`,
`systems/inventory.md`, and `systems/combat.md`. It also does not define the
low-level calendar cascade, which remains in `systems/time.md`.

## 2. Command Entry

H-Hole-up is reached through the shared world-command dispatcher. The active
scene determines which rest surface is available:

| Scene class | Rest surface | Primary result |
|-------------|--------------|----------------|
| Overworld / underworld | Outdoor camp, gated by current terrain | Rest with watch, possible interruption, possible camp event |
| Town-family scenes | Bed or inn rest surface | Prompt for hours, run simulated rest, refuse off the bed/rest tile |
| Dungeon scenes | Dungeon rest-with-watch path | Rest can be interrupted by dungeon danger |
| Combat | Not this command family | Combat has its own command table |

The command may ask for a direction or use the party's current cell depending
on the active mode and caller path. A compatible implementation should preserve
the visible rule: if the selected cell or current terrain does not support
rest, H-Hole-up prints the local refusal and consumes no useful rest.

## 3. Terrain And Entry Gates

Outdoor camping probes the tile under or near the party through the same
terrain classification family used by movement and special tile checks.
Accepted terrain can pitch a camp/rest marker and enter the hours prompt.
Rejected terrain refuses before the simulated rest loop.

Town rest is tile-gated. The known public town-mode rule is that the player
must be standing on an inn bed/rest surface; off that surface, the command
prints the stock refusal and does not advance time.

Dungeon rest uses the dungeon mode's own terrain and danger rules. It shares
the rest-with-watch and interruption concept, but dungeon tile encoding and
room/trap effects remain owned by `systems/dungeon-mode.md` and
`systems/encounters.md`.

## 4. Hours Prompt And Time Advance

After the entry gate accepts, the rest handler prompts for a duration in hours.
Cancelling or entering no usable duration returns without applying rest
recovery. Accepted durations advance time through a caller-owned simulation
loop rather than by adding the whole duration to the clock at once.

The resident overworld/dungeon rest-with-watch handler accepts the same visible
duration shape as the town-hours path: Space and `0` cancel, while a digit
`1` through `9` is echoed and becomes the requested rest duration. Before the
dangerous-rest handoff, it counts active party members whose status can
participate in the watch decision. If more than one eligible member is present,
it asks whether to set a watch. Answering no, cancelling the member prompt, or
choosing a member who is not in Good status leaves the watch slot unset.
Choosing a Good-status member records that member as the watcher for the
dangerous-rest setup.

The traced town bed/rest path accepts a single duration digit. Space and `0`
cancel. Digits `1` through `9` define the target hour relative to the current
hour. If current hour plus digit exceeds 23, the original subtracts 23 rather
than applying a normal modulo-24 wrap; preserve that compatibility edge. The
handler then advances time until the current hour reaches that target or the
rest surface rejects the party.

Compatibility rules:

- The time system accepts rest/wait increments larger than ordinary movement;
  the rest handler owns how often those increments are applied.
- The traced town-hours path runs one bounded scheduler/world-tick burst after
  a nonzero digit is accepted: up to sixteen NPC schedule passes, each followed
  by a world tick, before the elapsed-time loop begins.
- The same town path then advances elapsed rest through repeated ten-minute
  time-cleanup calls until the target hour or thrown-out branch.
- After each interruption check, already-applied time, schedule, and world side
  effects remain; the command does not roll the clock back.
- Ordinary prompts do not pass time while waiting for input. Time changes only
  after a duration has been accepted and the rest loop runs.
- Dungeon dangerous rest hands the accepted duration and watcher selection to
  the combat framer using the combined rest/camp alternate entry mode. This is
  the path that can skip the round loop or continue into sleep-ambush combat.
  Surface rest uses the resident rest/camp completion helper instead of the
  dungeon combat-framer handoff.

This preserves the original distinction between "the player is sitting at a
prompt" and "the party is actually sleeping or camping."

## 5. Party Recovery

A completed or partially completed rest pass walks the active party records and
applies recovery effects:

- Dead party members are skipped by ordinary rest recovery.
- Sleeping members are returned to Good status during cleanup.
- In the traced town-hours path, active party members who are in Good status are
  temporarily marked Sleeping for the elapsed-rest loop, then all Sleeping
  members are restored to Good during cleanup. Non-Good members are not changed
  by that temporary sleep-marking pass.
- In the traced rest-with-watch path, Good, Poisoned, and Sleeping members are
  the rest-participating statuses. Poisoned members are remembered as poisoned
  for any sleep-ambush restoration and do not receive ordinary rest HP recovery.
- Statuses outside the rest-participating set, including Charmed or Ashes if
  present in the party record, have no dedicated H-Hole-up status transition in
  the traced caller. Their changes remain owned by combat, magic, hazards,
  healers, or other status-specific systems.
- Eligible living members can recover current HP, capped at maximum HP.
- The stats panel is marked for refresh after visible HP or status changes.

Rest does not own a separate food/provision cadence. The rest loop advances
time, and the hourly status/provision cadence in `systems/time.md` observes any
hour crossings caused by those cleanup calls. Town bed rest's repeated
ten-minute cleanup calls can therefore cross 06:00, 12:00, or 18:00 and spend
provisions through the shared hourly rule; if the counter is already zero on an
hour crossing, the shared starvation branch applies. Shop food purchase
semantics remain outside H-Hole-up.

## 6. Interruption And Ambush

Rest can stop early. The interruption branch belongs to the rest handler, not
to the ordinary overworld random-encounter probe:

1. The rest loop advances one simulated tick pass.
2. The handler checks whether an interruption was raised.
3. If not, rest continues until the requested duration is exhausted.
4. If yes, rest stops immediately and branches to the mode-appropriate
   interruption result.

Dangerous wilderness and dungeon rest can interrupt into a sleep-ambush combat
handoff. The rest helper owns the interruption predicate and selected monster
row. In the combat framer this path is the CMDS H-Hole-up alternate setup, not
an SJOG or special-script dispatcher; it can finish the rest outcome without a
round loop, or return the continuation value that lets combat proceed. Town/inn
rest can instead produce a local refusal or "thrown out" style result depending
on the caller context.

For dangerous wilderness and dungeon rest, the interruption predicate is a
single shared-PRNG roll over sixty-four outcomes after the entry and rest-surface
gates have accepted the rest path. The zero outcome interrupts into the sleep
ambush branch; all other outcomes continue the rest pass. The effective
interruption chance is therefore 1 in 64 per eligible predicate invocation.

This roll is not the ordinary overworld random-encounter probe. It does not use
the tile/Z/hour threshold from `systems/encounters.md`, and there is no separate
terrain probability table in the traced rest path. Terrain determines whether
rest is accepted before the predicate runs; it does not weight the interruption
roll itself.

After a sleep-ambush row is selected, the rest helper performs caller-side
cleanup before delegating to combat setup. It restores each participating party
member from the rest-local status snapshot: members who entered the rest pass
poisoned remain Poisoned, while other eligible sleepers/watch participants are
restored to Good. This restoration is not a poison cure, and it does not turn
Dead members into active combatants.

The visible ambush branch is ordered by the rest handler, not by the ordinary
overworld encounter probe. The handler prints the sleep/rest narration before
the interruption test. If the interruption test fires, it picks the
sleep-ambush monster row, prints the ambush message, restores the rest-local
party statuses described above, and only then hands the selected row to the
alternate rest/camp setup path. A clean implementation should therefore not
wait for ordinary terrain-combat setup to produce the ambush message or status
restoration.

The selected sleep-ambush row remains inside the alternate rest/camp setup path
that the combat framer entered through CMDS. The ordinary overworld tile/Z/hour
encounter predicate, outdoor spawn-coordinate retry loop, and random-spawn
terrain buckets are bypassed.

## 7. Lord British Camp Event

One conditional outdoor camping branch invokes a hard-coded narrative event
where a strangely familiar old man appears, addresses the Avatar, rewards the
party for their deeds, and vanishes.

This is the visible Lord British level-up service in the analyzed game. It is
not a throne-room Talk handler and it is not a normal `.TLK` conversation. The
event is reached from ordinary overworld H-Hole-up camping when the rest path's
gates accept the special event branch.

The event's public contract:

- It is outdoor-camp owned.
- It is cinematic text plus party-stat mutation, not an interactive dialogue.
- It is considered only on the eligible normal camp-success path: not the
  sleep-ambush branch and not the paid/town rest branch.
- The trigger roll is `random(0, 99)`. Results `0..24` run the old-man event;
  results `25..99` skip it. The event chance is therefore 25%.
- It iterates active party members. Dead members do not receive the level-up
  narration or stat reward.
- For each eligible member, it recomputes the displayed level from experience:
  start at level 1, divide experience by 100, then increment level once for
  each halving step while that quotient remains nonzero. This yields level 1
  below 100 XP, level 2 for 100..199 XP, level 3 for 200..399 XP, and so on.
- If the recomputed level equals the stored level, that member gets no level
  narration and no stat reward from this event.
- If the recomputed level differs, the handler stores the new level, sets both
  current HP and maximum HP to `30 * level`, prints the member's level line, and
  applies exactly one primary-stat reward.
- The stat reward is selected by a uniform `random(1, 3)` roll: one result adds
  Strength, one adds Dexterity, and one adds Intelligence. The selected stat is
  increased by one with a cap of 30.
- After the member pass reaches the class-refresh branch, Avatar and Mage set
  current MP from Intelligence, Bard sets current MP from half Intelligence,
  and other classes leave MP unchanged.
- After the level-up/stat-reward pass, it prints a `KARMA.DAT` verdict. Lower
  moral-standing bands select records zero through three; the top band selects
  the sixth record. This differs from Blackthorn rescue/refuge, whose top band
  selects record four.
- It refreshes the party/status display before returning to the caller.
- It removes the temporary old-man presentation state before normal play
  resumes.

Implementations should keep the event outdoor-camp-only and separate from Lord
British's castle services.

## 8. Relationship To Other Systems

- **Commands.** `systems/commands.md` owns the dispatcher row for H and routes
  into this rest contract.
- **Time.** `systems/time.md` owns minute/hour/day/month rollover, rest's
  repeated cleanup calls, and the hourly status/provision cadence that can fire
  during simulated rest.
- **Encounters.** `systems/encounters.md` owns the combat setup reached after a
  sleep ambush fires.
- **Town mode.** `systems/town-mode.md` owns bed/tile gating and the fact that
  the NPC scheduler can run during simulated rest.
- **Overworld.** `systems/overworld.md` owns outdoor camp terrain context and
  the special-tile inventory around camp/well/cave tiles.
- **Shops.** `systems/shops.md` owns innkeeper lodging and healer services;
  those can share recovery concepts but are not H-Hole-up.
- **Inventory.** `systems/inventory.md` and `catalogs/item-list.md` own the
  food/provision counter as inventory state; `systems/time.md` owns its hourly
  consumption cadence.

## 9. Boundaries And Residuals

The clean ordering of narration, interruption, row selection, ambush message,
status restoration, and selected-row handoff is public here. The dormant
placement-shuffle branch in the ordinary terrain setup helper is not evidence
for this live rest/camp path.

The remaining residual is presentation parity around the same public mechanics:
exact low-level string-window boundaries, audio/delay helper timing, and
screen-refresh helper identity. The duration prompt, optional watch prompt,
watcher validation, dungeon framer handoff, sleep-ambush row selection,
status restoration, and selected-row handoff are public behavior rather than
open setup questions.

## 10. Sources

This cleanroom spec was derived from private analysis notes and sibling public
specs. It intentionally does not reproduce decompiled code, assembly, raw data
tables, or implementation-specific addresses.

- `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- `u5-decomp/functions/CMDS_OVL/0x0552_cmds_holeup_hours.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x3C9A_party_view_screen.md`
  (resident H-Hole-up rest-with-watch handler; the private filename is a stale
  working name for this behavior).
- `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x6360_exit_combat.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x3EF0_sat_add_byte.md`.
- `u5-decomp/functions/OUTSUBS_OVL/0x0658_lord_british_dialogue.md`.
- `u5-decomp/functions/OUTSUBS_OVL/0x0658_outsubs_camp_or_save.md`
  (superseded identity note; structural observations only).
- `u5-decomp/notes/lord_british_dialogue.md`.
- `u5-decomp/notes/npc_walker_callers_2026-05-08.md`.
- `systems/time.md`.
- `systems/encounters.md`.
- `systems/town-mode.md`.
- `systems/overworld.md`.
- `systems/shops.md`.
