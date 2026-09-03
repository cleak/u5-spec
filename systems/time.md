# Time

## 1. Overview

Ultima V keeps a single in-world clock that advances during play and is consulted by every system that cares about when something happens — NPC schedules, lighting, hour-prompted events, the date displayed on the look-at-the-sky tile, daily schedule maintenance, and month-boundary character counters. The clock is driven from one cleanup routine that every active mode loop calls once per turn (once per consumed turn outdoors, in town, and in combat; once per loop iteration in a dungeon — see Section 3); that routine takes a "minute increment" argument from its caller, advances minutes, and cascades minute → hour → day → month → year through fixed wrap thresholds. The same routine is also called with a zero increment as a "recompute, do not advance" form so that systems whose state depends on the current time (most notably ambient light) can be brought up to date when the player crosses between modes without spending a turn.

The clock is part of the saved game. Year, month, day, hour, and minute are persistent fields in the save image and survive every save/load cycle.

This spec describes the clock's state, the cascade rules, the per-mode minute costs, the daylight model that sits on top of the clock, the day and month rollover events, the NPC-schedule contract, and how everything is persisted.

## 2. Clock state

The clock is five small fields, each of which the engine treats as an unsigned counter inside a fixed range.

| Field   | Range    | Meaning                                                              |
|---------|----------|----------------------------------------------------------------------|
| year    | 0–65535  | In-world year. Stored as a 16-bit little-endian word.                |
| month   | 1–13     | One of thirteen months in the Britannian year.                       |
| day     | 1–28     | Day-of-month. Every month has exactly twenty-eight days.             |
| hour    | 0–23     | Hour-of-day, 24-hour. The cached twelve-hour value is derived from this.|
| minute  | 0–59     | Minute-of-hour.                                                      |

Day, month, hour, and minute are bytes; year is a word. Two derived values that the engine maintains alongside the primary fields:

- A cached twelve-hour value, rewritten whenever the cleanup finds an hour crossing. It is `12` when the underlying hour is `0`, the hour itself when the hour is in `1..12`, and `hour − 12` when the hour is in `13..23`. **Nothing in the shipped game renders it.** Every visible twelve-hour presentation — the Pocket Watch, the view-time line — recomputes the value from the hour byte on demand and does not read this cache; and there is no separate AM/PM flag, because those callers take the suffix from the underlying hour. Section 11 gives the byte's actual consumer and its decay rule. *Corrected (issue #184): earlier revisions of this bullet and of Section 11 called this a "12-hour display hour"; the word* display *is withdrawn — see* `RETRACTIONS.md` *row R338.*
- A pre-cascade snapshot of the hour. It is compared against the post-cascade hour to detect "the hour just ticked over" so that hour-driven side effects fire exactly once per crossing. It is taken only on a cleanup call that is actually advancing time: a **mode-zero call does not refresh it**, though a mode-zero call still performs the comparison. That asymmetry is load-bearing after a load — Section 11 works it through.

Several other variables sit alongside the clock in the save image (transport marker, timing/state tag, scene byte, party Z, and so on). Those are not part of the time system; the time system only reads them where noted below.

## 3. The per-turn cleanup contract

Every mode loop in the game — overworld, town, dungeon, combat — advances the clock through one shared per-turn cleanup routine. The same routine is also called at certain points where no turn has been consumed but where the daylight or hour-driven state needs to be brought up to date (for example when an outdoor view is being entered from a town).

The overworld, town, and combat loops make the call only for a turn that was actually consumed. **The dungeon loop does not.** Its single cleanup call sits at the top of each loop iteration, ahead of the input read and the command dispatch, and is not gated on the previous command's status word, so every dungeon iteration costs a minute — including commands the dispatcher reports as "no action". `systems/commands.md` Section 3 and `systems/dungeon-mode.md` own that detail; the effect on the clock is the same one minute per iteration.

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

Two effect codes can change the per-turn minute cost before the minute counter
is touched. The byte the cleanup reads is the single shared timed-magic-effect
slot specified in `systems/magic.md` — the same byte that carries Protection,
Mass Charm, Negate Magic, and the worn regalia auras, and that the stats panel
displays. It is emphatically *not* the party's boarded vehicle/transport tile
used by B-Board, X-Xit, movement, and rendering, and it is not a vehicle
identity table of any kind; earlier drafts that associated these tags with
skiffs, rafts, or the magic carpet were mistaken and that reading is retracted.

- **`Q` — Quickness.** The minute increment is *halved* before being applied. If the original increment was non-zero but halving rounds it down to zero, it is forced back to one. Because everything downstream of the minute write scales with the applied increment, the clock, the NPC schedules, and both light counters all advance at half rate while Quickness is running. The overworld epilogue also reads the same code as an alternate-turn gate for active-object animation and random-encounter probes; `systems/overworld.md` and `systems/encounters.md` own that cadence effect.
- **`T` — Negate Time.** The minute counter and the light-source counters are not advanced on this cleanup pass. The rest of cleanup still runs, especially daylight recomputation and visibility-dirty detection. A torch or light spell therefore burns no duration at all while time is negated.

No other value in this byte alters the increment. Horses, ships, carpet travel, and on-foot travel use the unmodified increment supplied by the caller; a vehicle never sets one of these codes.

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

1. The cached twelve-hour value is rewritten from the new hour (Section 2). It is not displayed; Section 11 owns what reads it.
2. If the active scene is in the surface/town-family range and the party is not
   at dungeon depth, the engine refreshes the sky strip in the top viewport
   border. This resolves the older hourly gameplay-hook note: the work is
   display refresh for that strip, not a gameplay event dispatcher and not the
   natural-moongate placer. The strip is not part of the stats panel; see
   `systems/moons.md`.
3. The displayed hour and the current fixed hour marker, Trammel, and Felucca
   presentation are therefore brought up to date at the top of the hour. The
   sky-strip display contract is specified in `moons.md`. The same renderer,
   before it decides whether either moon glyph is on screen, also rewrites the
   two cached moon-phase digits in the save image
   (`formats/saved-gam.md` Section 5.1) from the day of the month. Those digits
   are what natural-moongate transit reads, so this step has a gameplay
   consequence beyond the strip.

The hour-change check is made *after* the cascade has had its chance to bump the hour, and uses the pre-cascade snapshot from Section 2 as its baseline. So a turn that increments minutes from 55 to 5 will fire the bundle once (hour changed); a turn from 30 to 31 will not.

Because a mode-zero call performs the comparison without refreshing the snapshot, **a stale snapshot fires the bundle once at scene entry**, with no turn consumed. The shipped factory seed is exactly such a save — its snapshot is zero against a start hour of eight — so the first town-family entry after a new game or a Journey Onward writes the twelve-hour value and refreshes the moon digits before the player has taken a step. From the first time-advancing turn or party-upkeep pass onward the snapshot equals the hour and the bundle stops firing until the next real crossing.

**A separate party status/provision pass runs alongside the cleanup.** This
pass is a distinct routine from the per-turn cleanup described above, and its
cadence is different from what earlier drafts of this section claimed. Only the
food and starvation branch is gated on an hour change; everything else in the
pass runs on every invocation.

*When the pass runs.* Once per turn-consuming action in overworld mode, town
mode, and dungeon mode, invoked from each mode's per-turn epilogue after the
cleanup call has already advanced the clock. It also runs once per ten-minute
step of the town-bed rest loop. It does **not** run in combat mode, and it does
not run inside the wilderness camp loop, which advances the clock in
five-minute steps without entering this pass. Actions that do not consume a
turn, such as Look, do not trigger it.

*Unconditional part, every invocation.* The pass walks the active party in slot
order and, per member:

- If the member is Dead and is also the currently selected active member, the
  active-member selector is cleared to its no-selection sentinel.
- Dead and Sleeping members are skipped entirely: they take no poison damage
  and are not counted as provision consumers.
- A member whose status is exactly Poisoned loses **exactly 1 current hit
  point**, applied through the shared party-damage path. This is per member per
  turn, independently, not a shared roll and not an hourly effect. Poison
  damage that brings a member to zero sets that member's status to Dead and
  clears the active-member selector if it pointed at that member.
  An earlier revision of this section placed the poison tick inside the
  hour-gated part; that is retracted, and the difference is visible - a
  town-bed hour costs a poisoned member six points, not one.
- Every member that was neither Dead nor Sleeping increments the
  provision-consumer count, Poisoned members included.

*Hour-gated part.* The pass keeps its own previous-hour snapshot and compares it
with the current hour. The two branches below are mutually exclusive, and
neither runs when the hour has not changed:

- **Provision counter already zero.** The party receives the starvation
  warning, and then each party slot below the active party count, capped at six
  slots, that is not Dead takes an independently rolled uniform `1..8` hit
  points of damage through the same shared party-damage path. Different members
  can therefore take different amounts in the same hour. Sleeping and Poisoned
  members are eligible starvation targets; only Dead members are skipped. Note
  the asymmetry with the consumer count above: Sleeping members do not eat, but
  they do starve.
- **Provision counter nonzero.** Provisions are decremented only at 06:00,
  12:00, and 18:00. The decrement amount is the consumer count from the
  unconditional walk, and the counter floors at zero rather than wrapping. No
  food is spent at other hour changes.

After the branch is handled, the pass updates its previous-hour snapshot so the
branch cannot repeat until the clock crosses another hour. Because the pass runs
once per action, repeated rest or wait steps naturally apply the branch once for
each crossed hour, while several ordinary turns inside the same hour spend food
only once.

*The shared party-damage path.* Both the poison point and each starvation roll
are applied through one common routine, and it behaves identically for both. It
plays the standard damage feedback — a brief highlight of the affected member's
roster row and a short noise burst — subtracts the amount from that member's
current hit points, and, if the result is zero or below, stores zero, sets that
member's status to Dead, and clears the active-member selector when the selector
pointed at that member. It then marks the stats panel for repaint. A poisoned,
starving member can therefore be killed by either effect in the same pass, and
no separate "death check" step is needed anywhere else in the pass.

*Trailing part, every invocation.* The pass advances its own two counters — a
step counter that saturates at 255, and a countdown that, on reaching zero,
clears a temporary state byte and forces a stats-panel repaint — and then runs
the Ring of Regeneration check. For each active party member who is not Dead and
whose ring equipment slot holds Ring of Regeneration, roll a 1-in-8 chance; on
success that member gains exactly 1 current hit point, capped at maximum hit
points. Like the poison tick, this is per invocation, not per hour: a wearer
gets one roll per turn-consuming action, one roll per ten-minute town-bed rest
step, and one roll per five-minute wilderness camp step, the last of these
issued directly by the camp loop rather than through this pass.

*Worked consequence.* A poisoned member walking through town loses one hit point
per turn, so poison is a strong pressure on movement rather than a slow hourly
drip. A poisoned member in a town bed loses six hit points per simulated hour,
because the rest loop steps every ten minutes. A poisoned member in a wilderness
camp loses nothing from poison while the camp loop runs.

## 6. Daylight

The daylight value is a single byte that the cleanup routine recomputes on every call (mode 0 included). It represents how much ambient light the world has right now and is consumed by the visibility system to decide what cells the player can see and how the screen should look. Note what the number *is*: a squared-distance threshold compared inclusively against each viewport cell's squared distance from the player, handed to the visibility carve unmodified. It is not a sight radius and nothing squares or scales it. `systems/lighting.md` Section 3 and `systems/visibility.md` Section 3 own that contract; this section owns only when the value is recomputed and what the clock puts in it.

The recompute proceeds in three stages.

**Stage one — base value from hour and scene.** The base value is determined by the current hour and by the player's location:

- If the party's Z value has its high bit set when read as an unsigned byte — under the Z convention of `formats/saved-gam.md` Section 6 that is the Underworld plane on the outdoor map and a below-entry (basement) floor inside a town-family location — the base value is the *full-darkness* level and the hour does not matter. Ordinary dungeon levels are **not** in this set: a dungeon level index counts up from zero at the top of the stack and never sets the high bit, so the clock still drives the ambient value there; it simply has no effect, because the first-person dungeon view does not read it (`systems/lighting.md` Sections 3 and 6). Earlier wording here saying "any dungeon depth" is withdrawn. One surface-reachable location, scene twenty-five (Ararat), is tested by scene number and is likewise dark at every hour.
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

**Stage two — light-source floors.** Two byte counters track the time remaining on the player's torch and on the active light spell. Either being non-zero raises the cached ambient value to at least a fixed personal-light floor: the light-spell floor is 18 and the torch floor is 10 on the original light scale, so magic light is the brighter of the two. When both counters are zero, no floor applies. These floors only raise a darker value below their threshold; they do not lower daylight or other brighter ambient values. The visibility and dungeon renderers also read the light-source counters as state, so an implementation should preserve the counters separately rather than modelling personal light solely as a rewritten ambient byte.

**Stage three — change detection.** The pre-recompute daylight value is saved on the local stack before stage one runs. After the personal-light floors, the new value is compared against the saved one; if they differ, a visibility-dirty flag is set so that the next render runs the full visibility recompute rather than reusing the cached one. Daylight that *did not* change does not force a visibility repaint.

The light-source counters themselves are advanced as part of the per-turn cleanup, with the same effective increment after the state-tag modifier described in Section 4, via the saturating-arithmetic helper. They count down toward zero; reaching zero ends the effect. One further byte is touched at the moment of hour change, before the daylight recompute runs: the camp cooldown counter is reduced by one through the same saturating helper, floored at zero. That counter is armed at 14 by a completed wilderness camp and gates whether a later camp recovers anything; `systems/rest-and-camp.md` Section 5 owns it. Earlier wording here calling this an *incremented* "once-per-hour spell timer" is withdrawn — the hour rollover decrements it, and no spell timer is aged by this path (see the paragraph below).

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
current hideout for Faulinei, Astaroth, and Nosfentor. A living slot holds a
hideout id in the range `1..8`, and that id **is the town scene byte** of the
town hosting the Shadowlord: `1` Moonglow, `2` Britain, `3` Jhelom, `4` Yew,
`5` Minoc, `6` Trinsic, `7` Skara Brae, `8` New Magincia. The eight rows are
therefore the town rows of `catalogs/gazetteer.md`; dwellings, castles, keeps,
and the dungeon-mode scene bytes `33..40` are never hideouts. A vanquished slot
holds `0xFF`; the daily walker skips any slot whose high bit is set, so
vanquishing a Shadowlord is sticky across future days.

A slot value of `0` means "not yet placed". A newly created game starts with
all three slots at `0`, so no Shadowlord is anywhere until the first midnight
pass assigns hideouts. Implementations should treat `0` as neither "in a town"
nor "vanquished": it matches no town scene, and the reroll walker rewrites it on
the first day rollover.

For each slot whose high bit is clear, the midnight pass draws a candidate id
uniformly from `1..8` inclusive and rejects it when either of these holds, then
draws again:

- the candidate equals the party's current scene byte, or
- the candidate equals the value currently stored in **any** of the three slots,
  including the slot being rerolled and any slot already rewritten earlier in
  the same pass.

Because a slot's own previous value participates in the rejection test, a living
Shadowlord never stays in the same town two days running, and no two living
Shadowlords share a town. Vanquished slots hold `0xFF` and never collide with a
`1..8` candidate, so they do not constrain the draw. The party-scene exclusion
only bites when the party is standing inside one of the eight towns at midnight;
outdoors, in a dungeon, or in any other interior the party's scene byte is
outside `1..8` and the exclusion never fires.

This is the state read by the Shadowlord view/report path, town-entry Shadowlord
installation, the Shadowlord-name Yell gate, Stonegate atmosphere, and the
Doom-entrance gate described in `catalogs/quest-graph.md`.

This table is not NPC schedule state. Ordinary NPC schedules are driven by each
NPC's own schedule record and the current hour byte; they do not receive a
separate midnight slot rotation from this cleanup path.

After the Shadowlord maintenance, the day field is tested against the 28-day
month length. If it remains in range, no character counters or long-period flags
are touched. If it has advanced past 28, the month rollover bundle in Section 8
runs.

## 8. Per-month and per-year events

When the day field advances past 28, cleanup resets it to 1 and runs a small month-boundary bundle before incrementing the month.

**Long-period flag clears.** A small, fixed set of saved bytes is zeroed at the
month boundary. The traced set is exactly:

- the three rare-reagent harvest cooldown cookies (one per fixed harvest point,
  `systems/containers.md`);
- the cycling fixed hidden-treasure record's daily cooldown cookie
  (`systems/hidden-treasures.md`, record 14);
- the early-game encounter-size damper (`systems/encounters.md` Section 5). The
  older names "fortunes of war" and "double encounter" for this byte are
  withdrawn; it lowers spawn counts rather than raising them.

All five are day-of-month cookies or one-shot flags owned by other gameplay
systems, so the time system's contract is only that they are zeroed when the day
wraps from 28 to 1, never at ordinary midnight. Zeroing matters because zero
matches no calendar day (days run `1..28`), so every once-per-day gate that
compares against one of these cookies is guaranteed open on the first day of a
new month. `formats/saved-gam.md` Section 10 carries the field offsets.

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

The NPC scheduler itself runs once per ordinary consumed turn from the town turn loop (and from one specific time-elapsing command handler that operates outside the normal mode loops); it reads the hour byte fresh each call. A failed explicit Talk against a Blackthorn guard demand is the sole town result that still advances the one-minute clock but skips this scheduler before entering arrest. The overworld and dungeon mode loops do not invoke the NPC scheduler — there are no scheduled NPCs to advance outdoors or in dungeons — but they do still call the per-turn cleanup, so the hour and the daylight stay accurate when you walk back into town.

The relationship between the time system and NPC schedules is therefore simple: time updates a single shared hour byte; the scheduler reads that byte to pick a waypoint. The scheduler's internal state machine, pathfinding, and waypoint-coordinate tables are described in the NPC-schedule spec.

## 10. Per-turn time costs by command

The per-turn cleanup is called from each mode loop with the increment shown in Section 3 — one minute indoors, two minutes outdoors. Special command handlers may pass their own argument:

- **Movement.** Move one cell using the standard mode-loop turn cost. Indoor moves are one minute and outdoor moves are two minutes. **No vehicle changes that cost.** Skiffs, ships, horses, and the magic carpet all move on the unmodified mode increment; the `Q` half-increment applies only while the Quickness effect of Section 4 is running, and the `T` suppression only while Negate Time is. Earlier wording here attributing the `Q` half-increment to water transport, and the `T` suppression to carpet travel, is withdrawn.
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
| `0x02D4` | 1 byte | The shared timed-magic-effect code (see `systems/magic.md`). The time cleanup reads it for two values: `Q` halves the minute increment and `T` skips the minute and light-counter writes. |
| `0x02D5` | 1 byte | Active-player slot. Not clock state. |
| `0x02D6` | 1 byte | Transport/action marker. Not clock state. |
| `0x02D7` | 1 byte | Month, one-based `1..13`. |
| `0x02D8` | 1 byte | Day of month, one-based `1..28`. |
| `0x02D9` | 1 byte | Hour of day, zero-based `0..23`. |
| `0x02DA` | 1 byte | Pre-cascade hour snapshot used to detect an hour crossing. Written at the head of the time-advancing path, before the minute increment, and again by the per-turn party-upkeep pass; **not** written by a mode-zero call. A load-and-save with no turn consumed therefore leaves it exactly as the file had it. |
| `0x02DB` | 1 byte | Minute of hour, `0..59`. |
| `0x02DC` | 1 byte | Combat round counter; combat advances time when this wraps. |
| `0x02DD` | 1 byte | Adjacent per-turn state byte; preserve byte-for-byte in save tools. It is the cached wind-cadence byte, and the wind setter clears it whenever the wind actually changes (`systems/weather.md` Section 2.1). |
| `0x02DE` | 1 byte | Cached twelve-hour value; also the ambient-audio repeat countdown. See below. |
| `0x02FF` | 1 byte | Ambient light level. Recomputed by every cleanup call, mode zero included, per Section 6. Not a calendar field, but the clock is its only ordinary writer. |

Only `0x02CE`, `0x02D7`, `0x02D8`, `0x02D9`, and `0x02DB` are the canonical calendar fields. The derived and adjacent bytes are still persistent engine state, so compatibility implementations should round-trip them rather than regenerating the whole span from the calendar alone.

**The twelve-hour byte at `0x02DE` is written by the clock and consumed by the audio system.** Its full contract, and the reason a save almost never shows the live twelve-hour hour there:

- **Write.** On a cleanup call whose snapshot at `0x02DA` disagrees with the hour at `0x02D9`, the byte takes the twelve-hour form of the hour (Section 2). That is the whole write rule; there is no second writer.
- **Read.** The ambient-audio tick is its only consumer. It reads the byte as a count of remaining loud repeats — non-zero selects the loud envelope for one class of ambient effect — and decrements it toward zero on **two of every eight** of its own calls, using a small free-running sub-tick counter that is not part of the save image. It never writes any other value.
- **Cadence.** The audio tick runs once per idle world tick, and only while the master redraw-enable byte at `0x02FE` is non-zero; when that byte is clear the world tick skips its whole body and no decrement happens. The world tick is *not* one call per keyboard poll — the idle key-wait loop reaches it on one iteration in four, and many other sites drive it besides (`systems/main-loop.md` Section 9).
- **Consequence for a save.** A save taken any appreciable time after the last hour crossing reads zero here. An engine that stores a live twelve-hour value and never decays it diverges from the original on essentially every daylight save. The byte-compatible behaviour is: write on a snapshot mismatch, then decay on the audio cadence above.
- **Confidence.** The write rule, the single-consumer finding, the two-in-eight decrement and the cadence gates are **established** for the scan scope in `formats/saved-gam.md` Section 15 — the shipped executable, all twenty-three code overlays and all four display drivers, searched for direct and indexed references to the byte, with the hit list enumerated in the private note. **How long the byte takes to reach zero in wall-clock terms is inferred, not measured**: no timing run was made and the world-tick rate itself is unmeasured. Do not publish a seconds figure.

*Corrected (issue #184).* This table's `0x02DE` row previously read "Twelve-hour display value recomputed on hour changes". The value rule survives; the word *display* is withdrawn, because no shipped consumer renders the byte, and "on hour changes" is replaced by the snapshot-mismatch gate above. See `RETRACTIONS.md` row R338.

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

- **Party status pass caller census.** The status/provision pass of Section 5 is
  invoked from exactly four places: the overworld per-turn epilogue, the town
  per-turn underfoot handler, the dungeon post-action handler, and the town-bed
  rest loop's ten-minute step. All four sit after the clock advance for that
  step. Combat mode and the wilderness camp elapse loop never invoke it, so
  poison damage and provision consumption do not accrue there. Treating the
  pass as an hourly timer instead of a per-action pass is the single most
  common way to get poison, starvation, and ring regeneration all wrong at
  once.

- **Thirteen-month calendar.** Britannia's calendar has thirteen 28-day months,
  totalling 364 days per year. This is authored game-calendar structure, not an
  engine uncertainty. Implementations must not normalize it to twelve months.

- **Time during prompts and idle waits.** Prompt waits and open command-cursor
  waits do not advance in-world time by themselves. Idle redraw work is visual
  and animation-facing only; the clock advances only when a mode loop or a
  time-elapsing command calls the per-turn cleanup. In the overworld, town, and
  combat loops that call follows a committed action; in the dungeon loop it is
  ungated and happens once per iteration regardless of whether the previous
  command consumed a turn (Section 3). Earlier wording here that made the
  advance conditional on an action committing in every mode is withdrawn.

- **Year overflow.** The year is a 16-bit word. The original game makes no
  provision for multi-millennial overflow, so this is not a normal play
  compatibility target. Implementations may clamp rather than modelling wrap.

- **`Q` and `T` code naming.** Resolved. These are the Quickness and Negate
  Time codes of the single shared timed-magic-effect slot owned by
  `systems/magic.md`, not a vehicle or transport identity. The time cleanup's
  local contract is fixed: `Q` halves the minute increment and `T` skips the
  minute and light-counter writes. Do not map either code to the magic carpet,
  a skiff, or any other vehicle at the time-system layer.

- **Natural moongates.** The traced time cleanup does not own natural-gate
  placement or teleport handling. Its hour-change hook refreshes the
  sky/status strip, while the separate redraw tick advances the night-time
  light beacon whose source coordinates another owner has supplied. Natural-gate
  schedule and landing behavior therefore belong to the overworld transition
  inventory, not to the clock/calendar or moon-display contract.

## 13. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The daylight sentinel writer audit and absence of a confirmed normal gameplay
  high-sentinel writer - derived from
  `u5-decomp/notes/critical_state_lifecycles.md` and cross-checked against
  `systems/lighting.md`.

- The per-turn cleanup routine itself — its mode-argument handling, the state-tag modifiers, the minute-to-year cascade, the day-rollover bundle, the daylight recompute, and the hour-change hooks — derived from `u5-decomp/functions/ULTIMA_EXE/`.
- The resolved hour-change presentation call - formerly suspected as
  overworld gameplay logic, now identified as the sky/status row renderer -
  derived from `u5-decomp/functions/ULTIMA_EXE/`
  (that note's filename predates its 2026-08-22 naming correction; the routine
  is not combat-scoped and reads no status letters).
- The party status and provision pass - including the per-invocation walk, the
  Dead/Sleeping consumer exclusion, the one-point poison tick, the hour-gated
  starvation and 06:00/12:00/18:00 food branches, and the pass's own trailing
  counters - derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The starvation roll's range, per-slot independence, six-slot bound, and
  Dead-only exclusion - derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The shared party-damage path's damage feedback, zero-clamp, Dead-status
  write, active-member clear, and stats repaint - derived from
  `u5-decomp/functions/ULTIMA_EXE/` and
  re-verified in
  `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.
- The Ring of Regeneration predicate and +1 HP capped-add effect - derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The corrected cadence of the party status pass, its four call sites, and the
  combat and wilderness-camp exclusions - derived from
  `u5-decomp/notes/party_status_pass_cadence_2026-08-22.md`.
- The Shadowlord-location table consumed by the day-rollover bundle — derived from `u5-decomp/formats/data-ovl.md` and cross-checked against `u5-decomp/functions/CAST_OVL/`.
- The distinction between the timing/state tag byte and the boarded vehicle/transport byte — derived from `u5-decomp/formats/ds-bss-map.md` and `u5-decomp/functions/MAINOUT_OVL/`.
- The selection of an NPC's active waypoint from the four-byte time field, including the wrap-back-to-waypoint-1 behaviour — derived from `u5-decomp/functions/NPC_OVL/`.
- The per-tick NPC scheduler's consumption of the shared hour byte — derived from `u5-decomp/functions/NPC_OVL/`.
- The overworld mode loop's per-turn invocation of the cleanup with the two-minute increment, including the mode-zero entry calls used for daylight refresh — derived from `u5-decomp/functions/MAINOUT_OVL/`.
- The overworld special-underfoot latch clear zero-minute refresh - derived
  from
  `u5-decomp/functions/MAINOUT_OVL/`.
- The town mode loop's per-turn invocation of the cleanup with the one-minute increment, the rest/wait command's twenty-minute call, and the entry-time mode-zero refresh — derived from `u5-decomp/functions/TOWN_OVL/`.
- The ordinary town arrest surrender path's wait-to-morning loop - derived
  from `u5-decomp/functions/TOWN_OVL/`.
- The dungeon mode loop's per-turn invocation of the cleanup with the one-minute increment, its single call site at the head of the loop iteration ahead of the input read, and the fact that it is not gated on the command status word — derived from `u5-decomp/functions/DUNGEON_OVL/`.
- The hour-rollover decrement of the camp cooldown byte, and the withdrawal of
  the earlier "incremented once-per-hour spell timer" reading of the same site —
  derived from `u5-decomp/functions/ULTIMA_EXE/` and
  `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.
- The exhaustive writer census of the shared timed-magic-effect byte, which
  contains no vehicle, boarding, or movement writer and therefore withdraws the
  "skiff halves the increment" reading everywhere it appeared — derived from
  `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` section 27.
- The combat-exit non-cleanup lighting path - derived from
  `u5-decomp/functions/ULTIMA_EXE/`.
- The Journey Onward save-load path's handoff back to top-level dispatch -
  derived from `u5-decomp/functions/INTRO_OVL/`.
- The Hole-up command's repeated cleanup invocations and town-hours scheduler burst — derived from `u5-decomp/functions/CMDS_OVL/`.
- The save-image layout for year/month/day/hour/minute, including adjacent persistent state in the same resident neighbourhood — derived from `u5-decomp/formats/saves.md`.
- The runtime byte assignments for the clock fields and the surrounding per-turn variables — derived from `u5-decomp/formats/ds-bss-map.md`.
- Source provenance: the twelve-hour byte's snapshot-mismatch write gate, its
  single audio consumer, the two-in-eight decrement and the world-tick cadence
  gates behind it; the saved-hour snapshot's two writers and its non-refresh on
  a mode-zero call; and the moon-phase renderer's caching of the two glyph
  digits at every scene entry and hour change — derived from private analysis in
  `u5-decomp/notes/`, cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/` and `u5-decomp/functions/TOWN_OVL/`. The
  negative claim that nothing renders the twelve-hour byte is scoped to a
  reference census over the shipped executable, all twenty-three code overlays
  and all four display drivers; accesses computed through a pointer base outside
  the scanned window are not covered. No wall-clock timing was measured.
