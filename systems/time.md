# Time

## 1. Overview

Ultima V keeps a single in-world clock that advances during play and is consulted by every system that cares about when something happens — NPC schedules, lighting, hour-prompted events, the date displayed on the look-at-the-sky tile, daily schedule maintenance, and month-boundary character counters. The clock is driven from one cleanup routine that every active mode loop calls once per consumed turn; that routine takes a "minute increment" argument from its caller, advances minutes, and cascades minute → hour → day → month → year through fixed wrap thresholds. The same routine is also called with a zero increment as a "recompute, do not advance" form so that systems whose state depends on the current time (most notably ambient light) can be brought up to date when the player crosses between modes without spending a turn.

The clock is part of the saved game. Year, month, day, hour, and minute are persistent fields in the save image and survive every save/load cycle.

This spec describes the clock's state, the cascade rules, the per-mode minute costs, the daylight model that sits on top of the clock, the day and month rollover events, the NPC-schedule contract, and how everything is persisted.

## 2. Clock state

The clock is five small fields, each of which the engine treats as an unsigned counter inside a fixed range.

| Field   | Range    | Meaning                                                              |
|---------|----------|----------------------------------------------------------------------|
| year    | 0–65535  | In-world year. Stored as a 16-bit little-endian word.                |
| month   | 1–13     | One of thirteen months in the Britannian year.                       |
| day     | 1–28     | Day-of-month. Every month has exactly twenty-eight days.             |
| hour    | 0–23     | Hour-of-day, 24-hour. The display 12-hour value is derived from this.|
| minute  | 0–59     | Minute-of-hour.                                                      |

Day, month, hour, and minute are bytes; year is a word. Two derived values that the engine maintains alongside the primary fields:

- A 12-hour display hour, recomputed whenever the hour changes. It is `12` when the underlying hour is `0`, the hour itself when the hour is in `1..12`, and `hour − 12` when the hour is in `13..23`. There is no separate AM/PM flag — the caller that displays the time uses the underlying hour to decide which suffix to print.
- A pre-cascade snapshot of the hour, taken at the start of every cleanup pass. It is compared against the post-cascade hour to detect "the hour just ticked over" so that hour-driven side effects fire exactly once per crossing.

Several other variables sit alongside the clock in the save image (transport marker, timing/state tag, scene byte, party Z, and so on). Those are not part of the time system; the time system only reads them where noted below.

## 3. The per-turn cleanup contract

Every mode loop in the game — overworld, town, dungeon, combat — finishes each consumed turn by calling the per-turn cleanup routine. The same routine is also called at certain points where no turn has been consumed but where the daylight or hour-driven state needs to be brought up to date (for example when an outdoor view is being entered from a town).

The routine takes one word argument that is both the *minute increment for this turn* and a *mode tag* selecting how the call should behave. Three values are observed:

| Argument | Increment | Caller behaviour                                                                                  |
|----------|-----------|---------------------------------------------------------------------------------------------------|
| 0        | none      | Recompute the daylight value and refresh the visible clock; do not advance time.                  |
| 1        | 1 minute  | Town turn, dungeon turn, or combat round wrap.                                                    |
| 2        | 2 minutes | Overworld turn (one outdoor cell takes twice as long as one indoor cell).                         |

A larger argument is also legitimate: rest/wait paths can pass a twenty-minute
increment and can call the cleanup repeatedly while simulated rest advances
outside the normal mode loop. The cleanup routine has no special case for these
larger values; it simply adds them to the minute counter and lets the cascade
handle any resulting hour or day rolls.

The mode-zero call exists because daylight is a function of hour and scene, and crossing scene boundaries can change daylight without consuming a turn. Mode-zero turns are also the way the engine forces a fresh repaint after entry to overworld view from town or dungeon.

## 4. State-tag modifiers

Two single-character state tags can change the per-turn minute cost before the minute counter is touched. This tag byte sits near the saved player-state fields, but it is not the same byte as the party's boarded vehicle/transport tile used by B-Board, X-Xit, movement, and rendering. Public specs should therefore treat it as a timing/state tag, not as a complete vehicle identity table.

- **`Q` tag.** The minute increment is *halved* before being applied. If the original increment was non-zero but halving rounds it down to zero, it is forced back to one. Existing notes associate this with skiff or raft-like water travel, so a v1 implementation should use it for the slow-water transport timing contract without treating `Q` as the whole vehicle table. The overworld epilogue also uses the same tag as an alternate-turn gate for active-object animation and random-encounter probes; `systems/overworld.md` and `systems/encounters.md` own that cadence effect.
- **`T` tag.** The minute counter and the light-source counters are not advanced on this cleanup pass. The rest of cleanup still runs, especially daylight recomputation and visibility-dirty detection. Other mode-loop notes also use `T` as a town/transition-pending or scene-type tag, so this spec no longer maps it to the magic carpet or any named vehicle.

No other value in this tag byte alters the increment. Horses, ships, carpet travel, and on-foot travel use the unmodified increment supplied by the caller unless a separate movement handler explicitly sets one of the timing tags above.

The tag modifier is applied *before* the minute counter is touched. The cascade then runs against the modified value. There are also a few non-time per-turn counters that get the same effective increment after the tag modifier has been applied (light-source timers; see Section 6); those are bumped via a saturating-byte-arithmetic helper that the time system shares with the lighting system, except that the `T` tag skips that bump along with the minute write.

## 5. The cascade

Once the per-turn cleanup has the effective minute increment, it runs the cascade. The cascade has four wrap thresholds, each strictly greater than the highest valid value of the field below it.

The cascade order is:

1. Add the effective increment to the minute field.
2. If minutes reach or exceed 60, subtract 60 and advance the hour by one.
3. If the hour reaches or exceeds 24, reset it to 0, advance the day by one, and run the midnight daily events described in Section 7.
4. If the day becomes greater than 28, reset it to 1 and advance the month by one.
5. If the month becomes greater than 13, reset it to 1 and advance the year by one.

Several things follow from the exact form of this cascade.

**Wrap thresholds are constants and never change.** Sixty minutes per hour, twenty-four hours per day, twenty-eight days per month, thirteen months per year. The engine has no notion of leap days, daylight saving, or variable month lengths. Britannia's calendar is regular by design.

**The day check is "greater than 28", not "greater than or equal to 28".** Days are numbered `1..28`, and the rollover happens when the increment carries `day` from `28` to `29` — at which point the value `29` triggers reset to `1` and the month advances. Symmetric statements hold for month-to-year (`month > 13` triggers reset to `1` and year increments) and for hour-to-day (`hour >= 24` triggers reset to `0` and day increments). Day and month are one-based; hour and minute are zero-based.

**Multi-hour rests loop at the caller.** A multi-hour rest is advanced by a
caller-owned loop, not by handing the cleanup a single large "sleep N hours"
operation. Matching the original means the rest command owns the accepted
duration, the interruption checks, and any repeated cleanup/world-tick calls.

**Hour tick triggers a side bundle.** At the moment the hour changes, three things happen in addition to the day check above:

1. A 12-hour display value is recomputed from the new hour (Section 2).
2. If the active scene is in the surface/town-family range and the party is not
   at dungeon depth, the engine refreshes the lower sky/status presentation
   row. This resolves the older hourly gameplay-hook note: the work is display
   refresh for the sky/status strip, not a gameplay event dispatcher and not the
   natural-moongate placer.
3. The displayed hour and the current fixed hour marker, Trammel, and Felucca
   presentation are therefore brought up to date at the top of the hour. The
   sky-strip display contract is specified in `moons.md`.

The hour-change check is made *after* the cascade has had its chance to bump the hour, and uses the pre-cascade snapshot from Section 2 as its baseline. So a turn that increments minutes from 55 to 5 will fire the bundle once (hour changed); a turn from 30 to 31 will not.

**A separate hourly status/provision pass also observes hour changes.** The
party-status tick keeps its own previous-hour snapshot and only runs its food
and starvation branch when the current hour differs from that snapshot. This
means repeated rest/wait cleanup calls naturally apply the branch once for each
crossed hour, while ordinary turns inside the same hour do not spend food.

The pass counts provision consumers as active party members who are neither
Dead nor Sleeping. Poisoned members take a small poison tick during the same
pass, but they still count as provision consumers unless their status is Dead
or Sleeping.

If the food/provision counter is already zero when an hour change is observed,
the party receives the starvation warning and living members can take random
starvation damage. If the counter is nonzero, provisions are decremented only
at 06:00, 12:00, and 18:00. The decrement amount is the consumer count from
the active party scan, and the counter floors at zero rather than wrapping. No
food is spent at other hour changes. After the branch is handled, the
status/provision pass updates its previous-hour snapshot so the branch cannot
repeat until the clock crosses another hour.

After the food/starvation/status work, the same hourly party pass runs the
Ring of Regeneration check. For each active party member who is not Dead and
whose ring equipment slot contains Ring of Regeneration, the engine rolls a
1-in-8 chance; on success, that member gains exactly 1 current HP capped at
maximum HP. This check is tied to hour crossings, not to a rest state. Rest,
wait, movement, and town-bed sleeps can all expose it by advancing the clock.

## 6. Daylight

The daylight value is a single byte that the cleanup routine recomputes on every call (mode 0 included). It represents how much ambient light the world has right now and is consumed by the visibility system to decide what cells the player can see and how the screen should look.

The recompute proceeds in three stages.

**Stage one — base value from hour and scene.** The base value is determined by the current hour and by the player's location:

- If the player is on a fixed-dark scene type (the underworld is the obvious case) **or** at any dungeon depth (Z is positive), the base value is the *full-darkness* level. The hour does not matter; the underworld and dungeons are always dark.
- Otherwise, if the hour is before five in the morning or after seven in the evening, the base value is again the full-darkness level. Britannia is dark at night.
- Otherwise, if the hour is exactly five, the base value is read from a small dawn-gradient table indexed by `minute / 10`. The table interpolates between full darkness and full daylight across the six tens of minutes in the hour, so 5:00 starts at dark and 5:59 ends at near-daylight.
- Otherwise, if the hour is exactly nineteen, the base value is read from the same gradient table indexed by `(59 - minute) / 10`. This interpolates from near-daylight at the top of the hour to full darkness at 19:59, making dusk the reverse of dawn.
- Otherwise — that is, between six and eighteen inclusive on the surface — the base value is the *full-daylight* level.

Three particular values matter to consumers on the original light scale: full
daylight is 50, full darkness is 2, and values 51 or higher are treated as
"skip recompute" sentinels. If the cached ambient value is already in that
sentinel range before cleanup runs, the daylight recompute is skipped entirely.
The sentinel mechanism is therefore part of the compatibility contract, but the
current writer audit has not found a normal gameplay scene that deliberately
writes one as a lighting-freeze request. Treat it as defensive compatibility
behavior for imported or corrupted runtime state, not as evidence for a named
scene with frozen lighting.

The dawn/dusk gradient levels are:

| Minute range | Dawn value at hour 5 | Dusk value at hour 19 |
|---|---:|---:|
| `00..09` | 2 | 49 |
| `10..19` | 5 | 34 |
| `20..29` | 10 | 20 |
| `30..39` | 20 | 10 |
| `40..49` | 34 | 5 |
| `50..59` | 49 | 2 |

**Stage two — light-source floors.** Two byte counters track the time remaining on the player's torch and on the active light spell. Either being non-zero raises the cached ambient value to at least a fixed personal-light floor: the torch floor is 18 and the light-spell floor is 10 on the original light scale. When both counters are zero, no floor applies. These floors only raise a darker value below their threshold; they do not lower daylight or other brighter ambient values. The visibility and dungeon renderers also read the light-source counters as state, so an implementation should preserve the counters separately rather than modelling personal light solely as a rewritten ambient byte.

**Stage three — change detection.** The pre-recompute daylight value is saved on the local stack before stage one runs. After the personal-light floors, the new value is compared against the saved one; if they differ, a visibility-dirty flag is set so that the next render runs the full visibility recompute rather than reusing the cached one. Daylight that *did not* change does not force a visibility repaint.

The light-source counters themselves are advanced as part of the per-turn cleanup, with the same effective increment after the state-tag modifier described in Section 4, via the saturating-arithmetic helper. They count down toward zero; reaching zero ends the effect. An hour-rollover-only counter (used by the once-per-hour spell timer) is also incremented at the moment of hour change, before the daylight recompute runs, so that "this spell expires at the top of the hour" effects work correctly.

This cleanup path is not the owner of every magical countdown. The shared
combat active-effect/runtime counter (`P`, `Q`, `C`, `N`, and Negate Time's
`T`/10 state) ages at command/combat cleanup endpoints. The per-turn cleanup
does not decrement that counter; it only observes the `T` tag to suppress
minute advancement while Negate Time is active.

## 7. Per-day events

When the day rolls over (the hour-to-day path in Section 5), the cleanup routine
runs the midnight Shadowlord-location maintenance before the normal end-of-pass
daylight recompute and before any month rollover side effects.

**Shadowlord hideout maintenance.** Three persistent one-byte slots track the
current hideout scene for Faulinei, Astaroth, and Nosfentor. A living slot holds
a compact hideout id in the range `1..8`. These values are not the dungeon-mode
scene-byte range `33..40`; consumers interpret them as the Shadowlord hideout
ids used by the Yell, town-entry, and view/sextant paths. A vanquished slot
holds `0xFF`; the daily walker skips those high-bit-set values, so vanquishing a
Shadowlord is sticky across future days.

For each living Shadowlord, the midnight pass chooses a new hideout in `1..8`.
The choice is rejection-sampled until it is distinct from the party's current
scene and distinct from the other living Shadowlord slots already assigned for
that pass. This is the state read by the Sextant Shadowlord report, town-entry
Shadowlord spawning, and the Doom-entrance gate described in
`catalogs/quest-graph.md`.

This table is not NPC schedule state. Ordinary NPC schedules are driven by each
NPC's own schedule record and the current hour byte; they do not receive a
separate midnight slot rotation from this cleanup path.

After the Shadowlord maintenance, the day field is tested against the 28-day
month length. If it remains in range, no character counters or long-period flags
are touched. If it has advanced past 28, the month rollover bundle in Section 8
runs.

## 8. Per-month and per-year events

When the day field advances past 28, cleanup resets it to 1 and runs a small month-boundary bundle before incrementing the month.

**Long-period flag clears.** A small set of saved byte flags is cleared at the
month boundary, including the fortunes-of-war encounter reroll flag documented
in `systems/encounters.md` and `formats/saved-gam.md`. These flags are consumed
by other gameplay systems, so the time system's contract is only that they are
reset when the day wraps from 28 to 1, not at ordinary midnight.

**Per-character month counter.** Each of the sixteen character record slots
carries a one-byte counter. The month rollover increments it, capped at 25.
This is the same field the inn uses as a lodged guest's stay counter: leaving a
companion at an inn zeroes the field in the copied guest record; each later
28-day rollover adds one billable unit up to the cap; pickup treats zero as one
billable unit. The traced baseline has no separate active-party or non-lodged
consumer for this byte. Implementations should still preserve and age it on all
character records, because New Order, inn leave/pickup, and save/load move
whole records rather than special-casing this field.

After this bundle, the month field increments. If it advances past 13, it resets to 1 and the year word increments. No separate year-boundary side effects are currently identified.

## 9. NPC schedules and time

Every NPC carries a four-byte time-window field in its schedule record (the schedule format is described in `npc-schedules.md`). The four bytes are hour-of-day boundaries that divide the twenty-four-hour day into four segments, and each segment maps to one of three waypoints (the NPC's morning, work, and home positions, in typical use):

| Hour range                | Active waypoint |
|---------------------------|-----------------|
| `[time[0], time[1])`      | 0               |
| `[time[1], time[2])`      | 1               |
| `[time[2], time[3])`      | 2               |
| `[time[3], time[0])`      | 1 (wraparound)  |

The wraparound segment — the night-time band that crosses midnight from `time[3]` back to `time[0]` — selects waypoint 1, not waypoint 0. In typical NPC routines the second boundary `time[1]` corresponds to "go home for the evening", and waypoint 1 is the home/sleep location, so the wrap-back-to-1 rule means an NPC who has gone home at, say, 8 PM stays home until the next morning's `time[0]`.

The selection is computed against the current hour byte at every NPC tick. Because the same hour byte is used by every NPC and is updated by the per-turn cleanup, all NPCs see identical time-of-day for every tick of a given turn — there is no per-NPC clock.

The NPC scheduler itself runs once per turn from the town turn loop (and from one specific time-elapsing command handler that operates outside the normal mode loops); it reads the hour byte fresh each call. The overworld and dungeon mode loops do not invoke the NPC scheduler — there are no scheduled NPCs to advance outdoors or in dungeons — but they do still call the per-turn cleanup, so the hour and the daylight stay accurate when you walk back into town.

The relationship between the time system and NPC schedules is therefore simple: time updates a single shared hour byte; the scheduler reads that byte to pick a waypoint. The scheduler's internal state machine, pathfinding, and waypoint-coordinate tables are described in the NPC-schedule spec.

## 10. Per-turn time costs by command

The per-turn cleanup is called from each mode loop with the increment shown in Section 3 — one minute indoors, two minutes outdoors. Special command handlers may pass their own argument:

- **Movement.** Move one cell using the standard mode-loop turn cost. Indoor moves are one minute and outdoor moves are two minutes. Water transport uses the `Q` timing tag's half-increment rule. Carpet movement is not proven to use the `T` tag; implement it with the standard committed-turn cost unless a separate movement trace supplies a different modifier.
- **Hole up / camp.** The rest command prompts for an hours count, then advances
  elapsed rest through its own loop rather than by passing one large value to the
  cleanup routine. The cleanup routine accepts larger rest/wait increments, and
  the traced town H-Hole-Up hours path advances elapsed rest through repeated
  ten-minute cleanup calls until the target hour is reached. That same town path
  also runs one bounded schedule/world-tick burst after a nonzero duration digit
  is accepted; it is not repeated once per requested hour. If the rest path stops
  early, already-applied time and tick side effects are not rolled back. The
  command-level contract is in `systems/rest-and-camp.md`.
- **Wait / pass-time commands.** Where a command wants to advance the clock without consuming a movement turn, it calls the cleanup directly with whatever increment it wants.
- **Combat round.** Combat rounds end with a one-minute increment, applied once when the round counter wraps (rather than once per actor-turn within the round).
- **Town arrest surrender.** The ordinary town arrest path relocates the party
  to the Yew jail scene, then advances time in repeated twenty-minute cleanup
  calls until the hour byte reaches 08:00. The loop does not roll back partial
  time side effects if the start time is not aligned to the target hour.
- **Mode entry / exit.** Some mode boundaries invoke the cleanup with a zero
  increment to refresh daylight against the new scene without spending a turn.
  This is confirmed for overworld entry and the town map-load path. It is not
  a universal combat or save/load rule: the combat framer restores the previous
  world scene and marks visibility dirty on exit, while the small combat-exit
  wrapper refreshes lighting through the resident light helper instead of
  calling the full cleanup; the Journey Onward save-load path reads state and
  returns to the top-level dispatcher without its own cleanup call.

A handful of conversations and prompts (talking to an NPC, opening a door, looking at a tile) take *no* time — they do not invoke the cleanup at all, and the clock is unaffected by the time spent on the prompt.

## 11. Persistence

The clock is part of the runtime save image and is flushed verbatim when the player saves the game. The calendar fields sit in a resident-state neighbourhood that also contains movement, mode, combat, and display bookkeeping. Do not treat the span as a packed clock record; preserve adjacent bytes unless the owning system deliberately changes them.

| Save offset | Width | Time-system role |
|-------------|------:|------------------|
| `0x02CE` | 2 bytes | Year, little-endian. |
| `0x02D0..0x02D3` | 4 bytes | Focus/direction scratch owned by movement, combat, look, and cutscene callers. Not clock state. |
| `0x02D4` | 1 byte | Timing/state tag read by cleanup: `Q` halves the minute increment and `T` skips minute and light-counter writes. |
| `0x02D5` | 1 byte | Active-player slot. Not clock state. |
| `0x02D6` | 1 byte | Transport/action marker. Not clock state. |
| `0x02D7` | 1 byte | Month, one-based `1..13`. |
| `0x02D8` | 1 byte | Day of month, one-based `1..28`. |
| `0x02D9` | 1 byte | Hour of day, zero-based `0..23`. |
| `0x02DA` | 1 byte | Pre-cascade hour snapshot used to detect an hour crossing. |
| `0x02DB` | 1 byte | Minute of hour, `0..59`. |
| `0x02DC` | 1 byte | Combat round counter; combat advances time when this wraps. |
| `0x02DD` | 1 byte | Adjacent per-turn state byte; preserve byte-for-byte in save tools. |
| `0x02DE` | 1 byte | Twelve-hour display value recomputed on hour changes. |

Only `0x02CE`, `0x02D7`, `0x02D8`, `0x02D9`, and `0x02DB` are the canonical calendar fields. The derived and adjacent bytes are still persistent engine state, so compatibility implementations should round-trip them rather than regenerating the whole span from the calendar alone.

There is no separate "in-game time" file. The save image is the canonical store; loading the save reads the five fields back into the runtime variables, and the next per-turn cleanup uses them as-is.

The seed save (copied to the player's save slot at "new game") starts the campaign at a specific date encoded in its bytes, not in any code path. Implementations should preserve that date.

## 12. Time Boundaries And Caller Census

This section separates the confirmed cleanup caller census from compatibility
boundaries that are already fixed for engine behavior.

- **Mode-zero recompute call sites.** Mode-zero cleanup calls are confirmed from
  overworld entry (twice, around viewport rebuild), the overworld special
  underfoot-light latch clear, and town entry (once, after the entry
  tile-render). The traced dungeon turn loop advances time with the ordinary
  indoor increment, and the traced dungeon room-entry path is combat-room setup
  rather than a daylight recompute. Combat exit uses the resident combat
  wrapper's direct lighting refresh plus the combat framer's visibility-dirty
  restore, not a zero-minute cleanup call. Journey Onward save-load performs
  save/OOL reads and mirror writes, then returns to top-level mode dispatch; it
  does not own a separate mode-zero cleanup. The current direct caller census
  adds the ordinary town arrest wait-to-morning loop as a twenty-minute
  advancing caller, not as a zero-minute recompute caller.

- **Thirteen-month calendar.** Britannia's calendar has thirteen 28-day months,
  totalling 364 days per year. This is authored game-calendar structure, not an
  engine uncertainty. Implementations must not normalize it to twelve months.

- **Time during prompts and idle waits.** Prompt waits and open command-cursor
  waits do not advance in-world time by themselves. Idle redraw work is visual
  and animation-facing only; the clock advances only when an action commits and
  a mode loop or time-elapsing command calls the per-turn cleanup.

- **Year overflow.** The year is a 16-bit word. The original game makes no
  provision for multi-millennial overflow, so this is not a normal play
  compatibility target. Implementations may clamp rather than modelling wrap.

- **`Q` and `T` state-tag naming.** The time cleanup's local contract is fixed:
  `Q` halves the minute increment and `T` skips the minute and light-counter
  writes. Broader mode meaning belongs to the movement and mode-loop specs.
  Do not map `T` to the magic carpet or any other specific vehicle identity at
  the time-system layer.

- **Natural moongates.** The traced time cleanup does not own natural-gate
  placement or teleport handling. Its hour-change hook refreshes the
  sky/status strip, while the separate redraw tick only animates moongate
  frames when another owner has supplied temporary coordinates. Natural-gate
  schedule and landing behavior therefore belong to the overworld transition
  inventory, not to the clock/calendar or moon-display contract.

## 13. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The daylight sentinel writer audit and absence of a confirmed normal gameplay
  high-sentinel writer - derived from
  `u5-decomp/notes/critical_state_lifecycles.md` and cross-checked against
  `systems/lighting.md`.

- The per-turn cleanup routine itself — its mode-argument handling, the state-tag modifiers, the minute-to-year cascade, the day-rollover bundle, the daylight recompute, and the hour-change hooks — derived from `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The resolved hour-change presentation call - formerly suspected as
  overworld gameplay logic, now identified as the sky/status row renderer -
  derived from `u5-decomp/functions/ULTIMA_EXE/0x4A84_combat_status_grid.md`.
- The hourly party-status and provision cadence - including the Dead/Sleeping
  consumer exclusion, poison tick, starvation branch, and 06:00/12:00/18:00
  food decrement - derived from
  `u5-decomp/functions/ULTIMA_EXE/0x2AE8_per_turn_party_damage.md`.
- The hourly Ring of Regeneration predicate and +1 HP capped-add effect -
  derived from `u5-decomp/functions/ULTIMA_EXE/0x400C_party_random_jolt.md`.
- The Shadowlord-location table consumed by the day-rollover bundle — derived from `u5-decomp/formats/data-ovl.md` and cross-checked against `u5-decomp/functions/CAST_OVL/0x15B4_cast_destroy_shadowlord.md`.
- The distinction between the timing/state tag byte and the boarded vehicle/transport byte — derived from `u5-decomp/formats/ds-bss-map.md` and `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The selection of an NPC's active waypoint from the four-byte time field, including the wrap-back-to-waypoint-1 behaviour — derived from `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md`.
- The per-tick NPC scheduler's consumption of the shared hour byte — derived from `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The overworld mode loop's per-turn invocation of the cleanup with the two-minute increment, including the mode-zero entry calls used for daylight refresh — derived from `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The overworld special-underfoot latch clear zero-minute refresh - derived
  from
  `u5-decomp/functions/MAINOUT_OVL/0x0A1A_mainout_pre_loop_water_check.md`.
- The town mode loop's per-turn invocation of the cleanup with the one-minute increment, the rest/wait command's twenty-minute call, and the entry-time mode-zero refresh — derived from `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The ordinary town arrest surrender path's wait-to-morning loop - derived
  from `u5-decomp/functions/TOWN_OVL/0x12AE_town_arrest_or_unconscious.md`.
- The dungeon mode loop's per-turn invocation of the cleanup with the one-minute increment — derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The combat-exit non-cleanup lighting path - derived from
  `u5-decomp/functions/ULTIMA_EXE/0x6360_exit_combat.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The Journey Onward save-load path's handoff back to top-level dispatch -
  derived from `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- The Hole-up command's repeated cleanup invocations and town-hours scheduler burst — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md` and `u5-decomp/functions/CMDS_OVL/0x0552_cmds_holeup_hours.md`.
- The save-image layout for year/month/day/hour/minute, including adjacent persistent state in the same resident neighbourhood — derived from `u5-decomp/formats/saves.md`.
- The runtime byte assignments for the clock fields and the surrounding per-turn variables — derived from `u5-decomp/formats/ds-bss-map.md`.
