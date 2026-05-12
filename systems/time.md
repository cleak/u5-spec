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

A larger argument is also legitimate: the rest/wait command passes twenty minutes per *Hole-up* iteration, and the rest command issues several such calls in a row to advance the clock by hours at a time without re-entering the per-mode loop. The cleanup routine has no special-case for these larger values; it simply adds them to the minute counter and lets the cascade handle multi-hour rolls.

The mode-zero call exists because daylight is a function of hour and scene, and crossing scene boundaries can change daylight without consuming a turn. Mode-zero turns are also the way the engine forces a fresh repaint after entry to overworld view from town or dungeon.

## 4. State-tag modifiers

Two single-character state tags can change the per-turn minute cost before the minute counter is touched. This tag byte sits near the saved player-state fields, but it is not the same byte as the party's boarded vehicle/transport tile used by B-Board, X-Xit, movement, and rendering. Public specs should therefore treat it as a timing/state tag, not as a complete vehicle identity table.

- **`Q` tag.** The minute increment is *halved* before being applied. If the original increment was non-zero but halving rounds it down to zero, it is forced back to one. Existing notes associate this with skiff or raft-like water travel, so a v1 implementation should use it for the slow-water transport timing contract without treating `Q` as the whole vehicle table.
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

**Multi-hour rests loop at the caller.** A multi-hour rest is requested by issuing one cleanup per game-hour rather than handing the cleanup a single large argument; the cascade subtracts a single sixty per call. Implementations are free to do either — the visible behaviour is the same — but matching the original means the rest command, not the cleanup, owns the outer loop.

**Hour tick triggers a side bundle.** At the moment the hour changes, three things happen in addition to the day check above:

1. A 12-hour display value is recomputed from the new hour (Section 2).
2. If the player is on the surface (overworld, no dungeon depth), an "hour event" callback fires. The current public contract is the hook boundary: it fires exactly once per hour change while on the surface. Natural moongate phasing is the leading expected consumer, but the callback body is not yet mapped to public semantic depth.
3. The full HUD repaint flag is set so that the next render shows the new hour.

The hour-change check is made *after* the cascade has had its chance to bump the hour, and uses the pre-cascade snapshot from Section 2 as its baseline. So a turn that increments minutes from 55 to 5 will fire the bundle once (hour changed); a turn from 30 to 31 will not.

## 6. Daylight

The daylight value is a single byte that the cleanup routine recomputes on every call (mode 0 included). It represents how much ambient light the world has right now and is consumed by the visibility system to decide what cells the player can see and how the screen should look.

The recompute proceeds in three stages.

**Stage one — base value from hour and scene.** The base value is determined by the current hour and by the player's location:

- If the player is on a fixed-dark scene type (the underworld is the obvious case) **or** at any dungeon depth (Z is positive), the base value is the *full-darkness* level. The hour does not matter; the underworld and dungeons are always dark.
- Otherwise, if the hour is before five in the morning or after seven in the evening, the base value is again the full-darkness level. Britannia is dark at night.
- Otherwise, if the hour is exactly five, the base value is read from a small dawn-gradient table indexed by `minute / 10`. The table interpolates between full darkness and full daylight across the six tens of minutes in the hour, so 5:00 starts at dark and 5:59 ends at near-daylight.
- Otherwise, if the hour is exactly nineteen, the base value is read from the same gradient table indexed by `(59 - minute) / 10`. This interpolates from near-daylight at the top of the hour to full darkness at 19:59, making dusk the reverse of dawn.
- Otherwise — that is, between six and eighteen inclusive on the surface — the base value is the *full-daylight* level.

Three particular values matter to consumers on the original light scale: full daylight is 50, full darkness is 2, and values 51 or higher are treated as "skip recompute" sentinels. If the caller sets the daylight to a sentinel value before calling cleanup, the recompute is skipped entirely - that is how special scenes (cutscenes, shrines, and so on) freeze the lighting at whatever they set.

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
combat active-effect/runtime counter (`P`, `Q`, `C`, `N`, and Time Stop's
`T`/10 state) ages at command/combat cleanup endpoints. The per-turn cleanup
does not decrement that counter; it only observes the `T` tag to suppress
minute advancement while Time Stop is active.

## 7. Per-day events

When the day rolls over (the hour-to-day path in Section 5), the cleanup routine runs the midnight NPC-schedule maintenance before the normal end-of-pass daylight recompute and before any month rollover side effects. The daily bundle has one confirmed piece.

**NPC-schedule slot maintenance.** A small three-row table — used by the NPC scheduler to track which schedule slot is currently active across day boundaries — is walked once per day. Each row's high bit is a "pinned" flag; rows without the bit are advanced through their slot rotation. The rotation logic is described in detail in `npc-schedules.md`; from the time system's point of view, the only thing that matters is that the table is touched at the moment of day rollover and not at any other time.

After the daily schedule maintenance, the day field is tested against the 28-day month length. If it remains in range, no character counters or long-period flags are touched. If it has advanced past 28, the month rollover bundle in Section 8 runs.

## 8. Per-month and per-year events

When the day field advances past 28, cleanup resets it to 1 and runs a small month-boundary bundle before incrementing the month.

**Long-period flag clears.** A small set of saved byte flags is cleared at the month boundary. These flags are consumed by other gameplay systems, so the time system's contract is only that they are reset when the day wraps from 28 to 1, not at ordinary midnight.

**Per-character month counter.** Each of the sixteen character record slots carries a one-byte counter. The month rollover increments it, capped at 25. This is the same field the inn uses as a lodged guest's stay counter: leaving a companion at an inn zeroes the field in the copied guest record; each later 28-day rollover adds one billable unit up to the cap; pickup treats zero as one billable unit. Outside the inn billing consumer, the meaning of this counter for active or non-lodged roster records remains open.

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
- **Hole up / camp.** The rest command prompts for an hours count, and per hour requested it issues several cleanup calls in series at twenty minutes each, advancing the clock by sixty minutes per requested in-world hour. Resting outdoors may roll an ambush, which interrupts the elapsing without rolling back the time that has already elapsed.
- **Wait / pass-time commands.** Where a command wants to advance the clock without consuming a movement turn, it calls the cleanup directly with whatever increment it wants.
- **Combat round.** Combat rounds end with a one-minute increment, applied once when the round counter wraps (rather than once per actor-turn within the round).
- **Mode entry / exit.** Crossing between mode-loops invokes the cleanup with a zero increment at least once, to refresh the daylight recompute against the new scene before the first frame of the new mode is drawn.

A handful of conversations and prompts (talking to an NPC, opening a door, looking at a tile) take *no* time — they do not invoke the cleanup at all, and the clock is unaffected by the time spent on the prompt.

## 11. Persistence

The clock is part of the runtime save image and is flushed verbatim when the player saves the game. The five fields appear in a contiguous span of the save image:

| Field   | Width  |
|---------|--------|
| year    | word   |
| (gap)   | word   |
| month   | byte   |
| day     | byte   |
| hour    | byte   |
| (gap)   | byte   |
| minute  | byte   |

The "gap" bytes are not part of the clock itself; they hold the AM/PM display value, the round counter, and other small per-turn state that the engine wants to checkpoint. Implementations should treat the layout above as "the year, month, day, hour, and minute are at known offsets in the save image" and not rebuild the gap bytes from scratch — they carry information the rest of the engine reads.

There is no separate "in-game time" file. The save image is the canonical store; loading the save reads the five fields back into the runtime variables, and the next per-turn cleanup uses them as-is.

The seed save (copied to the player's save slot at "new game") starts the campaign at a specific date encoded in its bytes, not in any code path. Implementations should preserve that date.

## 12. Open questions and variations

This section records places where the picture is not yet complete or where evidence is not fully nailed down.

- **Surface hour-event callback body.** The cleanup routine calls an hour-event hook when the hour changes while the player is on the surface, but the hook's full body has not been mapped. Natural moongate phase advancement is the leading expected consumer, and once-per-hour world events may also live there. An implementer can scaffold the hook as "moongate phase plus reserved future hooks" and fill it in when the handler is mapped.

- **Per-character month counter — non-inn interpretation.** The byte that increments on every character record at month rollover, capped at 25, is now identified as the inn stay counter when a record is lodged. Its meaning for active or non-lodged roster records is still open; a high value might be consumed by a hunger, rest-debt, or generic days-since-event mechanic outside the inn.

- **Mode-zero recompute call sites.** Mode-zero cleanup calls are confirmed from overworld entry (twice, around viewport rebuild) and town entry (once, after the entry tile-render). Combat enter, dungeon enter, and save-restore have not been exhaustively mapped. Conservative assumption: every mode entry should fire one mode-zero cleanup before the first frame of the new mode.

- **Why exactly thirteen months.** Britannia's calendar has thirteen 28-day months, totalling 364 days per year. The design choice — neither the lunar 12 nor the solar 12 — is part of the game's lore (a thirteen-month "lunar" calendar suits the moongate cycle), not an engine quirk. Implementations should not "fix" this to twelve months.

- **Time during prompts and idle waits.** When a prompt is active (Y/N, hours-to-rest, NPC keyword), the input system suppresses the idle world-tick redraw path. That redraw path itself is visual/animation work and does not advance the clock; the clock advances only when an action commits and a mode loop or time-elapsing command calls the per-turn cleanup. Sitting at a prompt or at the open command cursor does not pass in-world time by itself.

- **Year overflow.** The year is a 16-bit word; the cascade overflows after 65,535 years. The original game makes no provision for that. Implementations targeting modern playthroughs need not either; the cleanest behaviour is to clamp.

- **Full meaning of the `Q` and `T` state tags.** The time cleanup's local contract is fixed: `Q` halves the minute increment and `T` skips the minute and light-counter writes. The broader mode meaning of those letters belongs to the movement and mode-loop specs. Current public evidence is strong enough to avoid mapping `T` to the magic carpet or any other specific vehicle identity.

## 13. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The per-turn cleanup routine itself — its mode-argument handling, the state-tag modifiers, the minute-to-year cascade, the day-rollover bundle, the daylight recompute, and the hour-change hooks — derived from `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The distinction between the timing/state tag byte and the boarded vehicle/transport byte — derived from `u5-decomp/formats/ds-bss-map.md` and `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The selection of an NPC's active waypoint from the four-byte time field, including the wrap-back-to-waypoint-1 behaviour — derived from `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md`.
- The per-tick NPC scheduler's consumption of the shared hour byte — derived from `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The overworld mode loop's per-turn invocation of the cleanup with the two-minute increment, including the mode-zero entry calls used for daylight refresh — derived from `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The town mode loop's per-turn invocation of the cleanup with the one-minute increment, the rest/wait command's twenty-minute call, and the entry-time mode-zero refresh — derived from `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The dungeon mode loop's per-turn invocation of the cleanup with the one-minute increment — derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The Hole-up command's repeated cleanup invocations to advance the clock by hours-many-times-sixty minutes — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The save-image layout for year/month/day/hour/minute, including the gap bytes that share the span — derived from `u5-decomp/formats/saves.md`.
- The runtime byte assignments for the clock fields and the surrounding per-turn variables — derived from `u5-decomp/formats/ds-bss-map.md`.
