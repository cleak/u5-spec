# Time

## 1. Overview

Ultima V keeps a single in-world clock that advances during play and is consulted by every system that cares about when something happens — NPC schedules, lighting, hour-prompted events, the date displayed on the look-at-the-sky tile, and per-day book-keeping like character ageing. The clock is driven from one cleanup routine that every active mode loop calls once per consumed turn; that routine takes a "minute increment" argument from its caller, advances minutes, and cascades minute → hour → day → month → year through fixed wrap thresholds. The same routine is also called with a zero increment as a "recompute, do not advance" form so that systems whose state depends on the current time (most notably ambient light) can be brought up to date when the player crosses between modes without spending a turn.

The clock is part of the saved game. Year, month, day, hour, and minute are persistent fields in the save image and survive every save/load cycle.

This spec describes the clock's state, the cascade rules, the per-mode minute costs, the daylight model that sits on top of the clock, the per-day events that run at midnight, the NPC-schedule contract, and how everything is persisted.

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

Several other variables sit alongside the clock in the save image (vehicle byte, scene byte, party Z, and so on). Those are not part of the time system; the time system only reads them where noted below.

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

## 4. Vehicle modifiers

Two vehicles change the per-turn minute cost. The engine inspects a single byte that records the current vehicle (it is one of the player-state bytes, with a single ASCII letter as its value); the time system only checks two values:

- **Skiff / raft.** When the player is in a skiff or raft, the minute increment is *halved* before being applied. If the original increment was non-zero but halving rounds it down to zero, it is forced back to one. This makes water-cell movement take half as long as land-cell movement, but never instantaneous.
- **"Tower" vehicle.** When the vehicle byte indicates the "tower" state, the minute counter is *not advanced at all* this turn. (The exact in-game vehicle this corresponds to — the magic carpet is a strong candidate — is not yet pinned down and is flagged in Section 12.) Other per-turn work (daylight refresh, daily events on hour change) still happens, because trips of this kind can still cross hour boundaries indirectly via mode-zero recomputes.

No other vehicle alters the increment. Horses, ships, and on-foot travel all use the unmodified increment supplied by the caller.

The vehicle modifier is applied *before* the minute counter is touched. The cascade then runs against the modified value. There are also a few non-time per-turn counters that get the unmodified increment (light-source timers; see Section 6); those are bumped via a saturating-byte-arithmetic helper that the time system shares with the lighting system.

## 5. The cascade

Once the per-turn cleanup has the effective minute increment, it runs the cascade. The cascade has four wrap thresholds, each strictly greater than the highest valid value of the field below it.

```
minute += increment
if minute >= 60:
    minute -= 60
    hour   += 1
    if hour >= 24:
        hour = 0
        day  += 1
        run "midnight" daily events     (Section 7)
        if day > 28:
            day   = 1
            month += 1
            if month > 13:
                month = 1
                year += 1
```

Several things follow from the exact form of this cascade.

**Wrap thresholds are constants and never change.** Sixty minutes per hour, twenty-four hours per day, twenty-eight days per month, thirteen months per year. The engine has no notion of leap days, daylight saving, or variable month lengths. Britannia's calendar is regular by design.

**The day check is "greater than 28", not "greater than or equal to 28".** Days are numbered `1..28`, and the rollover happens when the increment carries `day` from `28` to `29` — at which point the value `29` triggers reset to `1` and the month advances. Symmetric statements hold for month-to-year (`month > 13` triggers reset to `1` and year increments) and for hour-to-day (`hour >= 24` triggers reset to `0` and day increments). Day and month are one-based; hour and minute are zero-based.

**Multi-hour rests loop at the caller.** A multi-hour rest is requested by issuing one cleanup per game-hour rather than handing the cleanup a single large argument; the cascade subtracts a single sixty per call. Implementations are free to do either — the visible behaviour is the same — but matching the original means the rest command, not the cleanup, owns the outer loop.

**Hour tick triggers a side bundle.** At the moment the hour changes, three things happen in addition to the day check above:

1. A 12-hour display value is recomputed from the new hour (Section 2).
2. If the player is on the surface (overworld, no dungeon depth), an "hour event" callback fires. This is the hook used for moongate phasing and for any other once-per-hour world event — the time system itself does not care what the callback does, only that it fires exactly once per hour change while on the surface.
3. The full HUD repaint flag is set so that the next render shows the new hour.

The hour-change check is made *after* the cascade has had its chance to bump the hour, and uses the pre-cascade snapshot from Section 2 as its baseline. So a turn that increments minutes from 55 to 5 will fire the bundle once (hour changed); a turn from 30 to 31 will not.

## 6. Daylight

The daylight value is a single byte that the cleanup routine recomputes on every call (mode 0 included). It represents how much ambient light the world has right now and is consumed by the visibility system to decide what cells the player can see and how the screen should look.

The recompute proceeds in three stages.

**Stage one — base value from hour and scene.** The base value is determined by the current hour and by the player's location:

- If the player is on a fixed-dark scene type (the underworld is the obvious case) **or** at any dungeon depth (Z is positive), the base value is the *full-darkness* level. The hour does not matter; the underworld and dungeons are always dark.
- Otherwise, if the hour is before five in the morning or after seven in the evening, the base value is again the full-darkness level. Britannia is dark at night.
- Otherwise, if the hour is exactly five, the base value is read from a small dawn-gradient table indexed by `minute / 10`. The table interpolates between full darkness and full daylight across the six tens of minutes in the hour, so 5:00 starts at dark and 5:59 ends at near-daylight.
- Otherwise, if the hour is exactly nineteen, the base value is read from a dusk-gradient table indexed by `(60 − minute) / 10`. This interpolates from full daylight at the top of the hour to full darkness at 19:59. The table is the same one the dawn lookup uses, indexed in reverse, so dawn and dusk are mirror images of each other.
- Otherwise — that is, between six and eighteen inclusive on the surface — the base value is the *full-daylight* level.

Three particular values matter to consumers: full daylight is the highest value the system produces, full darkness is the lowest non-zero value, and a sentinel "skip recompute" value sits one above full daylight. If the caller sets the daylight to the sentinel before calling cleanup, the recompute is skipped entirely — that is how special scenes (cutscenes, shrines, and so on) freeze the lighting at whatever they set.

**Stage two — light-source clamps.** Two byte counters track the time remaining on the player's torch and on the active light spell. Either being non-zero clamps the daylight value down to a fixed ceiling (the torch ceiling is more permissive; the spell ceiling is tighter still). When both are zero, no clamp applies. The clamps are minimum-only — they reduce a too-bright value but do not raise a darker one — so the torch and spell genuinely "let you see in the dark" rather than overriding daylight outdoors.

**Stage three — change detection.** The pre-recompute daylight value is saved on the local stack before stage one runs. After the clamps, the new value is compared against the saved one; if they differ, a visibility-dirty flag is set so that the next render runs the full visibility recompute rather than reusing the cached one. Daylight that *did not* change does not force a visibility repaint.

The light-source counters themselves are advanced as part of the per-turn cleanup, with the unmodified minute increment, via the saturating-arithmetic helper mentioned in Section 4. They count down toward zero; reaching zero ends the effect. An hour-rollover-only counter (used by the once-per-hour spell timer) is also incremented at the moment of hour change, before the daylight recompute runs, so that "this spell expires at the top of the hour" effects work correctly.

## 7. Per-day events

When the day rolls over (the hour-to-day path in Section 5), the cleanup routine runs a small bundle of "midnight" events before the normal end-of-pass daylight recompute. The bundle has three pieces.

**NPC-schedule slot maintenance.** A small three-row table — used by the NPC scheduler to track which schedule slot is currently active across day boundaries — is walked once per day. Each row's high bit is a "pinned" flag; rows without the bit are advanced through their slot rotation. The rotation logic is described in detail in `npc-schedules.md` (the NPC-schedule spec, when written); from the time system's point of view, the only thing that matters is that the table is touched at the moment of day rollover and not at any other time.

**Per-character daily counter.** Each of the sixteen character record slots in the party roster carries a one-byte counter, and the day rollover increments it. The counter is capped at 25 (it stops climbing past that), so a character does not "rot" indefinitely once their counter reaches the cap. The most likely interpretation is a *days-since-fed* hunger meter — incremented daily, reset by eating, with downstream systems reading the value to apply starvation-style penalties — but the time system itself only increments it. Whatever consumes it belongs in another spec.

**Day-scope flag clears.** A small set of byte flags that govern once-per-day behaviour are cleared at midnight. The known cases include a "double encounter" flag used by sleep ambushes, a flag that the inn check-in logic uses to enforce "one stay per night", and a pair of bytes that gate certain endgame and quest events. These are not exhaustively enumerated here because they are consumed by gameplay systems that themselves belong in other specs; the time system's contract is that *they are reset at the moment of day rollover* and stay reset until something writes them again.

After the bundle, the day rollover continues with the day → month → year cascade and finally with the daylight recompute.

## 8. Per-month and per-year events

There are no separate "per-month" or "per-year" event bundles. The month and year fields are tracked, persisted, and displayed (the look-at-the-sky tile prints the full date), but no gameplay event is gated on a month boundary or a year boundary. The cascade runs them only because the hierarchy demands it: day cannot exceed 28, so a thirty-day-month rollover would fall apart, but no game mechanic looks at "is it a new month" or "is it a new year" the way several mechanics look at "is it a new day" or "is it a new hour". Implementations may freely treat month and year as display-only.

The month and year increments themselves carry no side effects.

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

- **Movement.** Move one cell using the standard mode-loop turn cost. Indoor moves are one minute, outdoor moves are two minutes, water moves are halved by the skiff modifier, carpet moves cost zero.
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

- **Which hour-event callback fires on a surface hour change.** The cleanup routine calls a "hour event" hook when the hour changes while the player is on the surface, but the hook's full body has not been decompiled. Strong candidates are moongate phase advancement (the moongates move with the time of day) and once-per-hour random-encounter rolls. An implementer can scaffold the hook as "moongate phase + reserved future hooks" and fill it in when the hour-event handler is mapped.

- **Per-character daily counter — interpretation.** The byte that increments on every character record at midnight, capped at 25, is most consistent with a hunger meter, but might equally be a "rest debt" or a generic days-since-event counter consumed by a different system. The advance is correct; the response to a high value belongs in another spec.

- **The dawn/dusk gradient table.** The six-byte table that interpolates daylight between full dark and full daylight at hours 5 (dawn) and 19 (dusk) lives in the data segment. The exact byte values have not been transcribed into this spec — they are driver-side numerics. Implementations should pick a smooth six-step ramp and tune visually; matching the original requires reading the bytes.

- **Mode-zero recompute call sites.** Mode-zero cleanup calls are confirmed from overworld entry (twice, around viewport rebuild) and town entry (once, after the entry tile-render). Combat enter, dungeon enter, and save-restore have not been exhaustively mapped. Conservative assumption: every mode entry should fire one mode-zero cleanup before the first frame of the new mode.

- **Why exactly thirteen months.** Britannia's calendar has thirteen 28-day months, totalling 364 days per year. The design choice — neither the lunar 12 nor the solar 12 — is part of the game's lore (a thirteen-month "lunar" calendar suits the moongate cycle), not an engine quirk. Implementations should not "fix" this to twelve months.

- **Time during prompts.** When a prompt is active (Y/N, hours-to-rest, NPC keyword), the input system suppresses the world-tick that would otherwise advance time during idle polling. The clock advances only when an action commits; sitting at a prompt does not pass time. This is already true of the input system as described in `input.md`; flagged here because the contract is part of "what advances time".

- **Year overflow.** The year is a 16-bit word; the cascade overflows after 65,535 years. The original game makes no provision for that. Implementations targeting modern playthroughs need not either; the cleanest behaviour is to clamp.

- **Identity of the "tower" vehicle.** The vehicle byte that suppresses minute advance (Section 4) holds the letter `T` in that state, called "tower" in the source notes. Whether this is the magic carpet or some other zero-time-cost transit mode is not yet confirmed. The time system's contract — "this byte means do not advance minutes" — is unaffected.

## 13. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The per-turn cleanup routine itself — its mode-argument handling, the vehicle modifiers, the minute-to-year cascade, the day-rollover bundle, the daylight recompute, and the hour-change hooks — derived from `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- The selection of an NPC's active waypoint from the four-byte time field, including the wrap-back-to-waypoint-1 behaviour — derived from `u5-decomp/functions/NPC_OVL/0x12E0_time_to_waypoint.md`.
- The per-tick NPC scheduler's consumption of the shared hour byte — derived from `u5-decomp/functions/NPC_OVL/0x0DB4_npc_per_tick_walker.md`.
- The overworld mode loop's per-turn invocation of the cleanup with the two-minute increment, including the mode-zero entry calls used for daylight refresh — derived from `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`.
- The town mode loop's per-turn invocation of the cleanup with the one-minute increment, the rest/wait command's twenty-minute call, and the entry-time mode-zero refresh — derived from `u5-decomp/functions/TOWN_OVL/0x141E_town_turn_loop.md`.
- The dungeon mode loop's per-turn invocation of the cleanup with the one-minute increment — derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The Hole-up command's repeated cleanup invocations to advance the clock by hours-many-times-sixty minutes — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The save-image layout for year/month/day/hour/minute, including the gap bytes that share the span — derived from `u5-decomp/formats/saves.md`.
- The runtime byte assignments for the clock fields and the surrounding per-turn variables — derived from `u5-decomp/formats/ds-bss-map.md`.
