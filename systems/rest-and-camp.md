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

**Timed magic effects are cancelled first.** Before any terrain gate or hours
prompt, H-Hole-up unconditionally clears the single shared timed-effect slot
specified in `systems/magic.md`. That slot holds one effect at a time, so
resting cancels an active Protection, Quickness, Mass Charm, Negate Magic, or
Negate Time — and, because the worn regalia share the same slot, it also strips
the otherwise permanent Amulet of Lord British, Crown of Lord British, and
Black Badge auras. A rested party must re-use those items to get the aura back;
in particular, resting closes the Blackthorn palace-gate password exchange that
the worn Badge unlocks. The clear happens on entry, so it applies even when the
terrain gate then refuses the rest.

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

H-Hole-up has three distinct effects that should not be collapsed into one
"rest recovery" rule.

**Town-bed rest is status cleanup plus time passage.** In the traced town-hours
path, active party members who are in Good status are temporarily marked
Sleeping for the elapsed-rest loop. Cleanup changes any Sleeping member back to
Good and restores the input mode. This path does not contain its own HP or MP
restore block. Any HP change observed during a town-bed sleep comes from other
time-driven systems. Concretely, the town-bed loop invokes the shared party
status/provision pass specified in `systems/time.md` once per ten-minute step,
so during town-bed sleep a poisoned member loses one hit point every ten
simulated minutes (six per hour), a Ring of Regeneration wearer gets one
1-in-8 roll every ten simulated minutes, and any hour the loop crosses applies
the provision or starvation branch.

**Rest-with-watch is a prompt and delegation wrapper.** The resident
overworld/dungeon H handler prompts for a duration, counts Good and Poisoned
members for watch eligibility, optionally records a Good-status watcher, and
then delegates the accepted rest to the rest/combat sandwich. It does not write
HP, MP, or equipment slots directly. It also does not set or clear the ring
slot byte used by Ring of Regeneration.

**Completed long-camp recovery is a separate CMDS block.** On the completed
camp path, after the "Party rested!" result, the handler can walk active party
records and apply recovery if all of these guards pass:

- The camp cooldown counter is zero. That counter is set to 14 whenever a camp
  completes and is reduced by one, floored at zero, at every hour rollover. A
  second camp begun inside fourteen game hours of the previous one therefore
  prints the no-effect line and recovers nothing.
- The accepted duration is greater than five hours. Five or fewer never
  recovers.
- The member was not marked Poisoned in the rest-local snapshot taken when the
  camp began. A member poisoned during the camp is still eligible; a member
  already poisoned at entry is not.
- The member is not Dead.
- The member is not the selected watch/target slot. The watcher recovers
  neither HP nor MP.

**The cooldown is persisted.** It occupies the byte at `SAVED.GAM` offset
`0x02E6`, inside the mode-scratch band, and the shipped seed carries zero there
- correct, since no cooldown is active at game start. It survives save and
reload like any other saved counter. An implementation that keeps it only in
memory lets a player clear the window by saving and reloading, which the
original does not.

**A camp refused by the cooldown does not re-arm it.** The cooldown-refusal
path bypasses recovery, the apparition-context gate, the apparition random
draw, and the write that arms the next cooldown. A player cannot lock
themselves out by camping repeatedly.

**A duration of five hours or less has the same late bypass.** It does not
recover the party, does not evaluate the apparition-context gate, consumes no
apparition random draw, and does not arm a new cooldown. This duration check is
made after the accepted camp has elapsed, just like the cooldown check.

**But a refused camp still advances time in full.** The gate is evaluated
*after* the camp's hours are credited, so the counter decays during the very
attempt it refuses. Repeated camping is therefore not a no-op loop - each try
burns its hours and brings the window closer to expiry. An implementation that
tests the gate *before* advancing time will diverge, and it will diverge in the
direction that looks more sensible, which is the hard kind to notice.

**A refused camp prints its own message.** It is a distinct, shorter no-effect
line, not the rest-success line, emitted from a mutually exclusive branch. Both
strings ship adjacently in `DATA.OVL` - the success line at file offset
`0x41FC` and the no-effect line at `0x420B` - so an implementation should read
them from the shipped file rather than transcribe either. Reporting a refused
camp through the success message is a visible error: the player is told the
party rested when nothing happened.

For each member that passes those guards, the handler adds a uniform random
`1..63` HP, rolled independently per member, and caps current HP at maximum HP.
It then restores MP only for specific class rows: Avatar and Mage set current MP
to Intelligence, Bard sets current MP to half Intelligence rounded down, and
other classes receive no MP write from this block. The MP write is an
assignment, not an addition, so a class row on this list can have its magic
points reduced by camping if its current MP was already above the target value.
Poisoned members keep Poisoned status; rest does not cure poison.

After the recovery walk, the handler arms the cooldown counter at 14. The
cooldown is armed unconditionally - whether or not any member actually
recovered.

**There is no camp marker tile, and nothing is stamped.** *Corrected:* an
earlier revision of this section said the handler "remembers the tile under the
party and stamps the camp marker tile" on a twenty-five percent roll. **Both
halves are withdrawn.** The roll's success path is three instructions: it copies
the **calendar month** byte into a second saved byte and calls one routine. No
tile array is written anywhere in the handler.

**The value copied is the month**, one-based in the range one to thirteen, not a
tile id - so the "remembered tile" reading was a value-space error, not a
misplaced write. The routine called is the **camp apparition and level-up
event** already specified in Section 7.

**So Sections 5 and 7 describe the same draw at the same instruction, counted
twice.** There is one event here, not two, and an implementation that builds
both will roll twice and stamp something that does not exist.

**The exact integer draw matters.** The apparition gate draws from the closed
range `0..99` and accepts `0..24`, giving twenty-five accepted outcomes in one
hundred. The neighbouring hit-point roll is a closed `1..63`, so an
implementation should preserve these bounded integer draws rather than replace
them with floating-point probability checks.

The apparition branch carries **an additional caller-context gate**, evaluated
before `random(0, 99)`:

| Caller context | Context condition | Apparition PRNG draw |
|----------------|-------------------|----------------------|
| Ordinary overworld H-Hole-up | No suppression condition | Consumed once |
| Dungeon H-Hole-up | Dungeon-rest condition | Not consumed |
| Town-bed H-Hole-up | Separate rest handler; never reaches this gate | Not consumed |
| Reserved compatibility condition | No shipped public caller sets it | Not consumed if supplied |

The first tested condition is therefore the live dungeon-rest selector, not an
outdoor selector. The second condition has no separate gameplay meaning in the
shipped caller set: it is a dormant, reserved apparition-suppression input. It
must not be inferred from paid lodging; town-bed rest is excluded by routing,
not by that condition.

When either condition suppresses the branch, the handler performs no
apparition draw and still arms the cooldown at 14. When both are clear, it
consumes exactly one `random(0, 99)` draw; either a miss or a completed event is
then followed by the same cooldown write. Cooldown refusal and duration of
five hours or less take an earlier branch and reach none of this logic.

Statuses outside the rest-participating set, including Charmed or Ashes if
present in the party record, have no dedicated H-Hole-up status transition in
the traced caller. Their changes remain owned by combat, magic, hazards,
healers, or other status-specific systems. The stats panel is marked for
refresh after visible HP, MP, or status changes.

Rest does not own a separate food/provision cadence. The rest loop advances
time, and the status/provision pass in `systems/time.md` observes any hour
crossings caused by those cleanup calls. Town bed rest's repeated ten-minute
cleanup calls can therefore cross 06:00, 12:00, or 18:00 and spend provisions
through the shared hourly rule; if the counter is already zero on an hour
crossing, the shared starvation branch applies. Shop food purchase semantics
remain outside H-Hole-up.

The wilderness camp elapse loop behaves differently and the difference is
observable. That loop advances the clock in five-minute steps and never enters
the shared party status/provision pass, so while a camp is elapsing no poison
damage is taken, no provisions are spent, and no starvation damage is applied,
regardless of how many hours the camp covers. Only the town-bed loop runs that
pass. An implementation that routes both rest paths through one per-hour status
tick will make camping far more punishing than the original.

The Ring of Regeneration tick is time-owned rather than rest-owned, and it is
per pass rather than per hour. It checks the member's ring equipment slot for
the Ring of Regeneration item id and can add exactly 1 HP on a 1-in-8 roll.
During town-bed rest it is reached once per ten-minute step through the shared
status pass; during a wilderness camp the camp loop calls the same check
directly, once per five-minute step. H-Hole-up does not set or clear the ring
slot byte.

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

The wilderness camp loop invokes that predicate once when a five-minute step
observes that the game-hour byte changed, not on every five-minute step. The
`0..63` predicate uses the PRNG state already in force. Results `1..63` do not
read the host clock and do not re-seed. Only result `0` performs one fresh
host-time read, replaces the shared PRNG state with the twelve-bit transform
specified in `systems/prng.md`, and then consumes `random(0, 7)` from that new
state to choose the sleep-ambush row. This conditional row-selection re-seed
is the only clock sample in the wilderness camp loop.

In particular, it is not the completed-camp Lord British trigger. Section 7's
later `random(0, 99)` draw uses whatever stream is then in force and is not
preceded by a host-clock sample or seed assignment. A camp that reaches that
final draw without an earlier 1-in-64 interruption hit has not re-seeded during
the camp, which is original behaviour.

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
- It is considered only after an uninterrupted ordinary overworld camp has
  completed, the persisted cooldown is zero, and the requested duration is
  greater than five hours. It is not considered on the sleep-ambush, dungeon,
  town-bed, cooldown-refusal, or short-duration paths.
- The caller-context gate is evaluated before the trigger roll. A suppressed
  context consumes no event PRNG value.
- When the context is eligible, the trigger roll is `random(0, 99)`. Results
  `0..24` run the old-man event; results `25..99` skip it. The event chance is
  therefore 25%.
- It iterates active party members. Dead members do not receive the heal, the
  cure, the level recomputation, the narration or the stat reward. They are
  **not** passed over entirely, though: the class-keyed magic-point refresh
  described below still runs for them, so a dead Bard's magic points are still
  rewritten. *Clarified 2026-08-23; the earlier wording named only the
  narration and reward, which invited implementers to skip dead members
  outright.*
- **Every member who is not dead is silently full-healed and cured before the
  level check.** Current hit points are set to that member's maximum, and the
  status is forced to the healthy value, clearing poison, sleep and any other
  affliction letter. No text accompanies this; it happens for the whole living
  party whether or not anyone gains a level. *Added 2026-08-23 from a complete
  re-read of the handler; an earlier revision of this section omitted it, so an
  implementer working from the previous text would have shipped the event
  without its heal.*
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
- **Each living member's turn in the pass is presented, not just the ones who
  gain a level.** Before the level check, the handler restamps that member's
  map sprite from a class-keyed tile and plays a short two-tone sting with a
  brief flashing pause. This runs for every living member on every occurrence
  of the event. *Added 2026-08-23; an implementation built from the previous
  text would have played the sting only on a level-up.*
- It refreshes the party/status display before returning to the caller.
- The old man's on-screen figure is an ordinary temporary entry in the world's
  active-object table, placed at the centre cell of the viewport — the party's
  own cell — for the duration of the scene, and cleared to an empty tile at the
  end. It is not a separate presentation layer.
- It removes the temporary old-man presentation state and advances the turn
  clock before normal play resumes.

Implementations should keep the event outdoor-camp-only and separate from Lord
British's castle services.

## 8. Relationship To Other Systems

- **Commands.** `systems/commands.md` owns the dispatcher row for H and routes
  into this rest contract.
- **Time.** `systems/time.md` owns minute/hour/day/month rollover, rest's
  repeated cleanup calls, and the shared party status pass that can fire during
  simulated rest. Only the provision/starvation branch of that pass is gated on
  an hour crossing. The poison point and the Ring of Regeneration roll fire once
  per pass, which during town-bed rest means once per ten-minute step, and which
  during a wilderness camp means not at all for poison and once per five-minute
  step for the ring.
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
status restoration, and selected-row handoff is public here.

**Corrected (issue #178).** An earlier revision said the placement-shuffle branch
in the ordinary terrain setup helper was dormant and "not evidence for this live
rest/camp path". Both halves are withdrawn. The surface camp ambush reaches that
same terrain setup helper through its CMDS wrapper, and reaches it **only** with
the shuffle bit set, so its monsters occupy a randomly permuted subset of the
authored placement cells rather than the first `count` of them; the same route
also skips the pre-placement pass that clears the combat tables and seats the
party from the arena record's party-seat rows, and where the party's arena
coordinates come from on that route is **not established**. See `combat.md`
Section 5 and `encounters.md` Section 4.

The camp cooldown counter, the greater-than-five-hours duration gate, the
caller-context mapping, suppression-before-PRNG ordering, per-member `1..63`
roll, class-keyed magic-point assignment, and absence of any status/provision
pass inside the wilderness camp loop are all public behavior here. The second
apparition-suppression condition is intentionally specified as reserved: the
shipped public callers do not assign it a gameplay context.

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

- `u5-decomp/functions/CMDS_OVL/`.
- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/functions/OUTSUBS_OVL/`.
- `u5-decomp/notes/` (independent caller censuses and second-pass rest,
  persistence, cadence, and camp-event traces).
- `systems/time.md`.
- `systems/encounters.md`.
- `systems/town-mode.md`.
- `systems/overworld.md`.
- `systems/shops.md`.
