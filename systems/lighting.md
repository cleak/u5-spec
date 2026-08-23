# Lighting

## 1. Overview

Ultima V has one shared lighting model with two layers:

- **Ambient daylight**, derived from the world clock and from where the party is.
- **Personal light**, supplied by a torch or by a light spell.

The same state is read by surface visibility, dungeon rendering, dungeon Look, the night-time light beacon, and the stats panel. The important distinction is that daylight is environmental and recalculated from time and scene, while torches and light spells are finite counters that decay as turns pass.

Lighting is not a separate weather system. Wind does not brighten or darken the
world, and weather does not extinguish light sources in the currently mapped
behavior. The mapped dungeon movement and post-action cell-effect dispatchers
also do not define a wind/breeze cell that blows out a torch; do not treat that
secondary claim as part of the baseline weather, lighting, or dungeon contact
model.

## 2. State

Lighting state consists of three runtime values:

| State | Meaning |
|-------|---------|
| Ambient light | The current daylight or darkness level used by surface visibility. |
| Torch counter | Remaining duration, in game minutes, while the party has a burning torch. |
| Light-spell counter | Remaining duration, in game minutes, while magic light is active. |

The torch and spell counters are independent. A torch can expire while the spell remains active, and a spell can expire while a torch remains active. The dungeon renderer treats either one as sufficient to see; both being zero is the blackout state.

The original stores these as byte-sized duration counters. A modern implementation should expose them as turn durations or visibility profiles, not as raw memory bytes, but the starting values and saturation behavior are part of the compatibility contract.

## 3. Ambient Daylight

Ambient daylight is recomputed by the per-turn cleanup routine, including calls that intentionally advance zero minutes. This matters when the party crosses between modes: the engine can refresh lighting for the new scene without spending a turn.

**What the numbers on this scale mean.** Every value in this section is a
**squared-distance threshold** on exactly the scale `systems/visibility.md`
Section 3 defines: the cached value is handed to the visibility carve unchanged
and compared, inclusively, against each viewport cell's squared distance from
the player. It is **not** a sight radius, **not** a tile count, and **not** a
brightness level. Nothing squares, scales, or table-maps it on the way. The
geometry - how many cells each value lights and how far it reaches - belongs to
visibility Section 3 and is not restated here; use that table rather than
reading these numbers as distances.

The ambient model is:

- On Britannia's surface, the clock drives a day-night cycle.
- Before dawn and after dusk, the surface is dark.
- Dawn and dusk use a short stepped gradient rather than an instant switch.
- During the daytime band, the surface reaches full daylight.
- The Underworld plane and below-entry (basement) floors force dark ambient light regardless of the hour. The test is on the party's Z value, not on the scene family, and ordinary dungeon levels are outside it - see the scope note below.
- One location, scene twenty-five (Ararat), is pinned to the dark value regardless of the hour.

On the original light scale, full daylight is 50 and full darkness is 2. The
complete clock schedule is:

| Clock window | Ambient value |
|---|---|
| Hours 6 through 18 inclusive | 50 (full daylight) |
| Hour 5, the dawn ramp | Six ten-minute steps rising through `2, 5, 10, 20, 34, 49` - minutes 0-9 give 2, 10-19 give 5, 20-29 give 10, 30-39 give 20, 40-49 give 34, 50-59 give 49 |
| Hour 19, the dusk ramp | The same six steps in reverse - minutes 0-9 give 49, 10-19 give 34, 20-29 give 20, 30-39 give 10, 40-49 give 5, 50-59 give 2 |
| Hours 20 through 4 inclusive | 2 (full dark) |

**Scope of the forced-dark tests.** Both tests run *before* the clock is
consulted, and there are exactly two of them.

- **The plane / floor test is on the party's Z value, read as an unsigned
  byte**: any Z with its high bit set - that is, any value above one hundred
  twenty-seven - pins the ambient value at 2 for every hour. Under the Z
  convention published in `formats/saved-gam.md` Section 6, that selects the
  **Underworld plane** on the outdoor map, where Z is `0xFF`, and a
  **below-entry floor** inside a town-family location, where a basement is also
  `0xFF`. It does **not** select ordinary dungeon levels: a dungeon level index
  counts upward from zero at the top of the stack, so it never sets the high
  bit, and the ambient value computed while the party is inside a dungeon is
  simply whatever the clock produces. That has no visible consequence, because
  the first-person dungeon view never reads the ambient value at all
  (Section 6) - underground darkness comes from the two personal-light counters,
  not from this test. Earlier wording in this document and in `systems/time.md`
  that placed "any dungeon depth" inside the forced-dark scope is **withdrawn**;
  it was inconsistent with the Z convention the spec publishes elsewhere.
- **The scene test** pins scene twenty-five (Ararat) to 2 at every hour,
  independently of Z.

The torch and light-spell floors of Section 4 then apply normally on top of a
forced-dark result, which is why a personal light source behaves identically at
night outdoors and in the Underworld.

Towns, dwellings, castles, keeps and the outdoor world all draw the ambient
value from this one computation. **There is no per-location ambient override and
no second lighting source anywhere in the 2D modes.** A location that looks lit
at night is lit by the local-light mask owned by `systems/visibility.md`
Section 12, not by a different ambient value.

Values 51 or higher are special "do not recompute" sentinels: if the cached
ambient value is already in that range when the cleanup routine reaches the
daylight stage, it leaves the value alone. A writer census across every shipped
code file finds **no site anywhere that writes a value at or above 51**, so this
guard cannot fire in normal play; the largest value any writer produces is the
full-daylight 50. Treat the sentinel as a defensive compatibility rule for
imported or corrupted runtime state rather than as evidence that a specific
cutscene, shrine, or town uses frozen lighting.

That same census fixes the complete writer set for the ambient value: the dark
value, the full-daylight value, the dawn/dusk gradient step, the two
personal-light floors of Section 4, and the single zero-value override below.
Nothing else in the game writes it.

One mapped overworld environmental branch forces ambient light to **zero** - a
state distinct from the dark value of 2, and the only way zero is ever reached.
The overworld loop tests the tile under the party at the top of every iteration;
when that tile is the void tile (`0xFF`) and the Amulet of Lord British's code
does not occupy the shared timed-effect slot, ambient light is forced to zero and
a latch is raised that also prevents the pending movement step from committing.
See `systems/magic.md` and `catalogs/item-list.md` for the Amulet side of that
exemption, and Section 7 below for what zero looks like on screen. This is an
ordinary darkening override, not a high-value skip-recompute sentinel. On
iterations where the condition does not hold, the overworld loop clears the latch
and runs a zero-minute cleanup call, so ambient light returns to its
clock-and-scene value without spending time.

The cleanup routine marks visibility dirty **whenever the recomputed ambient
value differs from the cached one** - from any cause, including a torch being
ignited or burning out and every step of the dawn and dusk ramps. Rendering then
rebuilds the visible grid instead of reusing the previous one. An implementation
that recomputes visibility only on movement will show stale lighting through
dawn and dusk and will not react to a new light source until the party next
steps.

Ambient daylight also gates the night-time rotating light beacon
(`systems/visibility.md` Section 12.6): the beacon runs only while the ambient
value is **strictly below the full-daylight value of 50**, and at or above that
value the beacon draws nothing and its bearing resets. When the beacon does run
it marks visibility dirty, so it is one of the recompute triggers. That gate is a
consumer of lighting, not a lighting rule in its own right, and it is the **one
place outside the visibility carve that reads the ambient value at all** - it
reads it as a day/night flag, never as a distance (Section 7.2). It has nothing to do
with moongates: earlier wording here said ambient daylight gates "moongate
presentation" and that moongates "only animate" above a daylight threshold. Both
halves are withdrawn - gates are ordinary live terrain placed by the clock hour
alone (`systems/overworld.md` Section 9), and the light gate's sense is the
opposite of what that wording implied.

Two clarifications, because this withdrawal has been over-read in both
directions. First, it is a withdrawal of the *daylight* link only: a gate's
appearance does change over time, through the presence phase in
`systems/overworld.md` Section 9.1, and nothing here says a gate is a static
tile. Second, there is no surviving "moongate render-eligibility" gate of any
kind - not here, not under another name, and not with the sense flipped. An
implementation still carrying a symbol for one is carrying a retracted contract
and should delete it rather than repoint it. Ambient light has **no** input to
moongate placement, appearance, or entry at any point.

## 4. Personal Light

Torches and light spells modify visibility after the base ambient value has been chosen. They do not replace the clock. Outdoors at noon, daylight is already sufficient; at night, in the Underworld, and in dungeons, a personal light source is what lets the party see around itself.

The original engine applies the torch and spell effects as separate
minimum-light **floors** on the cached ambient value, in a fixed order. On the
original light scale, the **spell-light floor is 18** and the **torch floor is
10** - magic light is the brighter of the two. The two profiles differ, which is
why implementations should keep two counters rather than collapsing them into
one boolean "has light" flag.

The combining rule is a **maximum**, expressed as two ordered floor-raises. The
ambient value for the current hour and scene is computed first (Section 3); the
light spell then raises it to at least 18 if it is below that; the torch then
raises it to at least 10 if it is below that. Equivalently:

```text
effective = max(ambient, 18 if light spell active, 10 if torch active)
```

For modern gameplay purposes, the contract is:

- If both counters are zero, personal light contributes nothing.
- If the spell counter is nonzero, the party has spell lighting until the counter decays to zero; the cached ambient value is raised to the spell-light floor of 18 when it would otherwise be darker than that floor.
- If the torch counter is nonzero, the party has torch lighting until the counter decays to zero; the cached ambient value is raised to the torch floor of 10 when it would otherwise be darker than that floor.
- If both are nonzero, the spell-light floor dominates, because it is applied first and is the higher of the two; the torch floor is then a complete no-op. Do not stack the two into a brighter combined value.
- **Neither source ever lowers the ambient value.** Both are floors, never ceilings and never clamps downward. In daylight, where the ambient value is already 50, lighting a torch or casting a light spell changes nothing at all.

**Both counters are read as booleans here.** The recomputation tests only whether
each counter is nonzero; the remaining duration never influences the value. A
torch with one minute left lights exactly as far as a freshly lit one, and the
light simply stops the turn the counter reaches zero.

Neither counter is itself a radius, and neither floor is a radius. Each counter
is a remaining-duration count that the per-turn recomputation consults; each
floor is a squared-distance threshold on the scale of Section 3, handed to the
visibility carve unchanged. Section 7 gives the two floors' concrete on-screen
consequences.

## 5. Counter Decay

The counters decay through the same turn cadence that advances time. A normal town, dungeon, or combat turn spends one counter unit; a normal overworld turn spends two. Longer waits spend their requested increment. A counter unit is one game minute: the per-turn cleanup decays the counters by the same effective increment it just applied to the clock, after the Quickness and Negate Time adjustments described below.

This section covers only torches and light spells. The timed magic effects
(`P`, `Q`, `C`, `N`, `T`) live in the single shared timed-effect slot specified
in `systems/magic.md`; that slot counts world turns, not the game minutes these
two light counters count, and it ages on a completely separate path. Do not
merge the three.

Two of those effects do reach into this cadence, because they change how much
time the turn spends:

- While Negate Time (`T`) is active, the per-turn cleanup skips the whole time
  advance. The clock is frozen, and neither light counter is decayed at all, so
  a torch or light spell burns no duration for as long as time is negated.
- While Quickness (`Q`) is active, the per-turn minute increment is halved with
  a floor of one minute, so both counters drain at half rate along with the
  clock and the NPC schedules.

Decay is saturating subtraction: if the remaining counter is greater than the spent increment, subtract the increment; otherwise set the counter to zero. Counters never underflow or wrap.

Mode-zero lighting refreshes do not spend counter duration. They recompute ambient lighting only.

Dungeon mode consults the two counters before drawing the first-person view,
but it does not maintain them: the decay happens in the shared per-turn cleanup
the dungeon loop calls at the end of each turn, exactly as in town and
overworld mode. Underground the counters are read as a plain lit/unlit gate.
The observable contract is still turn-based: active light sources burn down as
the party takes dungeon turns, and no-light dungeon rendering blacks out.

The mapped dungeon and weather paths do not extinguish a torch through a
wind/breeze contact tile. Torch state changes through Ignite, through the
G-Get "borrow a lit fixture" branch, through the Blackthorn clear, and through
ordinary counter decay/upkeep; light-spell state changes through the three
light-spell writers listed in section 8, the same Blackthorn clear, and the same
decay cadence. Nothing else writes either counter — in particular no spellbook
item, shrine, or decorative light tile bumps them during per-turn cleanup.

## 6. Dungeon Blackout

Dungeon mode has the strictest lighting gate. Before the first-person dungeon view is drawn, the renderer checks the torch and spell counters. If both are zero, it does not draw the corridor view at all. The side/status UI can still exist, but the dungeon scene itself is black.

Dungeon L-Look follows the same rule: with no torch and no light spell, the player receives darkness instead of the true focus-cell description. With either counter nonzero, Look can describe the selected dungeon focus cell and the renderer can draw the first-person view.

This means dungeon light is gameplay-critical. The first-person dungeon view **never reads the ambient value**, so the surface dawn/day/dusk curve has no effect underground: the ambient value keeps being recomputed from the clock while the party is inside a dungeon (the Z-based forced-dark test of Section 3 does not catch dungeon level indices), and nothing in dungeon mode looks at the result. Only the two personal-light counters decide whether the view is drawn.

## 7. Surface Visibility

**The explicit statement.** The cached ambient light value, and the light-spell
and torch floors of 18 and 10, **are squared-distance thresholds**, expressed on
the same scale as the visibility system's cell distances. They are handed to the
visibility carve unmodified. No mapping of any kind is applied - the value is not
squared, not halved, not shifted, not scaled, and not passed through a lookup
table between this system and the comparison in `systems/visibility.md`
Section 5. A cell is inside the lighting threshold when the sum of the squares of
its row and column offsets from the player is less than or equal to the value.

The two personal-light cases are worth stating concretely, because they are what
distinguish this reading from a sight-radius reading in play:

| Situation | Effective value | Viewport cells inside the gate (of 121) | Farthest cell along a row or column |
|---|---:|---:|---:|
| A light spell burning in the dark | 18 | 61 | 4 |
| A torch burning in the dark, no spell | 10 | 37 | 3 |
| Full dark, no personal light | 2 | 9 | 1 |
| Full daylight | 50 | 121 | 5 |

Those counts are the distance gate only; terrain blockers and the carve's
propagation rules can reduce what is actually seen, never increase it.

Surface visibility uses the ambient light value as an input to the visibility producer. At full daylight, the visible area is broad. At night or in forced-dark scenes, visibility is reduced unless a torch or light spell is active.

The surface renderer does not have the dungeon's all-or-nothing first-person blackout. Instead, it rebuilds the 11-by-11 visibility grid from the current light value, terrain blockers, and the separate local-light mask maintained by the visibility system. A zero light value leaves every cell obscured; any positive value lets the centre-out visibility producer carve visible cells, and cells beyond the threshold can still be shown when the local-light mask covers them.

### 7.1 The two darkness presentations

A port must keep these two states separate; they look different on screen and
they are reached differently.

**Ordinary full dark - threshold 2.** The player's own tile plus all eight
surrounding cells are inside the threshold, so the party stands in a lit
three-by-three neighbourhood; everything beyond it is dark unless a local light
source covers it. This is what the player sees outdoors at night with no torch
and no spell, on a dungeon or Underworld level in the 2D modes, and in the
permanently dark location of Section 3. It is **not** a single visible cell: the
surrounding ring is visible, and any part of that ring that blocks sight is still
drawn, because a cell inside the threshold is shown whether or not its terrain is
opaque.

**Total blackout - threshold 0.** The carve is skipped outright. The entire
viewport renders as obscured, the player's own cell included, and because the
sprite compositor refuses to draw into an obscured cell the player's own figure
disappears with it. This is the only state in which the player's tile is not
drawn. It is reachable in normal play through the void-tile override of
Section 3: while the party stands on the void tile without the Amulet of Lord
British, the overworld loop forces the value to zero each iteration and the same
latch blocks the pending movement from committing; when the condition clears,
lighting is recomputed immediately without advancing time.

### 7.2 What does and does not consume the lighting value

- **The visibility carve is the only place the value is used as a distance
  threshold.** In the whole engine there is exactly one comparison that treats
  the value as a threshold on squared distance, and it is the carve's. No second
  system re-derives a radius, a brightness or a fade from it.
- **There is exactly one other reader, and it is a day/night gate, not a
  threshold.** The night-time rotating beacon of `systems/visibility.md`
  Section 12.6 compares the ambient value against the full-daylight value of 50
  before it does anything else, and takes the clear-and-draw-nothing path at or
  above it (Section 3 above). An implementation that skips this gate leaves the
  beacon stamping its lit cells in broad daylight. Apart from the carve and that
  gate, everything else in the engine works from the finished visibility grid.
- **The fog and sprite-compositing pass never reads it.** Its near/far marker
  refinement uses its own fixed squared distance of five (a twenty-one-cell
  core) that does not vary with time of day, torch, or spell, and its sprite
  gate reads only the grid cell's existing verdict. See
  `systems/visibility.md` Section 7.
- **The 3D dungeon view ignores the ambient value entirely.** It reads the two
  personal-light counters as a single on-or-off gate between a fully drawn view
  and a black one, exactly as Section 6 describes. The dawn/dusk curve and the
  thresholds tabulated here have no effect underground.
- **Any change to the value marks visibility dirty**, so the grid is rebuilt on
  the next redraw. Section 3 lists the triggers.

The local-light mask is not part of this system: it is owned by
`systems/visibility.md` section 12, which specifies the source tile set, the
per-source carve, the squared-distance threshold of ten (a thirty-seven-cell
Euclidean disc reaching three cells along a row or column, not a Chebyshev box,
not a seven-by-seven square, and not the dungeon light gate), and the three
points at which the mask is rebuilt. Overlapping sources union. In particular the
local-light source threshold is unrelated to the ambient, torch and spell values
tabulated in this document; do not reuse a value from here for it, and note that
its numeric coincidence with the torch floor of 10 is exactly that - a
coincidence.

## 8. Commands And Spells

The I-Ignite command is the player-facing torch entry point. It consumes one torch from inventory; with no torches available it refuses and leaves the light state unchanged.

Ignite has two duration rules:

- Outside dungeon scenes, it sets the torch counter to 240 counter units.
- In dungeon scenes, it adds a random 112..127 counter units to the current torch counter, capped at 255.

This means re-lighting a torch in a dungeon can extend an already-burning torch, while non-dungeon use refreshes to a fixed 240-unit value. Since normal dungeon and town turns spend one unit and normal overworld turns spend two, a counter unit is not always the same as one player-visible turn.

Light spells are cast through the normal C-Cast pipeline. The magic system owns charge, mana, level, and scene gating. Once the spell succeeds, lighting owns the resulting light-spell counter and its decay.

The ordinary Light spell, *In Lor*, sets the light-spell counter to 100 counter units. Great Light, *Vas Lor*, sets the same counter to 255 counter units. The Light scroll sets the same counter to 240 counter units. These three are the only writers that start spell light; all of them overwrite the spell-light duration rather than adding to it, and none of them consumes a torch.

Two other paths write light state without being spells. The G-Get "borrow"
branch, which lifts a lit fixture out of a town or castle cell, sets the torch
counter to 100 counter units and consumes no carried torch; it is specified in
`systems/containers.md`. And the Blackthorn rescue/refuge restoration zeroes
both counters outright as it hands control back to ordinary play, so that
scene transition extinguishes torch and spell light together; see
`systems/blackthorn.md`.

## 9. Persistence

Lighting state lives in the runtime game state and is saved with the rest of the game image. On load, the next mode entry or per-turn cleanup recomputes ambient light from the loaded clock and scene, while the torch and spell counters resume from their saved values.

Implementations should persist the counters, the clock, and the scene/position state. Ambient light itself can be recomputed, but keeping it cached is harmless as long as mode-zero refreshes update it before rendering.

## 10. Evidence Boundary

The lighting contract in this document is complete at counter, ambient-light,
scene-gate, and threshold-semantics depth. New claims that assign the high-value
skip-recompute sentinel to a named scene should still be backed by fresh writer
evidence; the current census finds no writer of any such value at all.

One identification carries less weight than the rest: the permanently dark
location is named as Ararat by joining the forced-dark scene number against the
scene-to-location table in `catalogs/gazetteer.md`, not by a fresh trace of that
location's scene byte. The forced-dark rule for that scene number is firm; the
name attached to it inherits the gazetteer's accuracy.

## 11. Sources

The behavior described here was derived from cleanroom reading of the following notes and sibling specs. No assembly excerpts, raw offsets, or implementation-specific byte tables are reproduced here.

- Ambient daylight recomputation, dawn/dusk behavior, the Z-based forced-dark test, torch and spell counter decay, and visibility dirtying - `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: the finding that the ambient value and the two personal-light
  floors are squared-distance thresholds passed to the visibility carve
  unmodified, the hour-by-hour clock schedule and the ten-minute dawn/dusk step
  values, the scene-twenty-five forced-dark case, the maximum/ordered-floor
  combining rule and the boolean reading of the two counters, the whole-binary
  writer census establishing that nothing writes a value at or above fifty-one
  and that no per-location ambient override exists, the distinction between the
  dark value of two and the void-tile zero blackout, the beacon's
  below-full-daylight gate, and the finding that the visibility carve is the
  only place that uses the lighting value as a distance threshold - derived from
  private analysis note
  `u5-decomp/notes/light_threshold_semantics_2026-08-22.md`. The assignment of
  the eighteen floor to the light spell and the ten floor to the torch is
  independently confirmed against the counter writers cited below; the same
  private note narrates that pairing the other way round, and that narration is
  the stale one.
- Daylight writer inventory, high-sentinel writer audit, and the overworld
  zero-light override -
  `u5-decomp/notes/critical_state_lifecycles.md`.
- Overworld entry and loop behavior relevant to lighting refresh and the
  special-underfoot zero-light override -
  `u5-decomp/functions/MAINOUT_OVL/`, and
  `u5-decomp/functions/MAINOUT_OVL/`.
- Saturating counter decrement and Ignite's torch debit/start rules - local helper analysis of the resident counter helpers and the CMDS Ignite command path.
- Light spell counter writes for *In Lor* and *Vas Lor* - `u5-decomp/functions/CAST_OVL/`, `u5-decomp/functions/CAST2_OVL/_OVERVIEW.md`, and the CAST2 helper reached through the overlay dispatch map in `u5-decomp/functions/ULTIMA_EXE/`.
- The corrected assignment of the two floors to their counters (spell light 18,
  torch 10), the Light scroll's 240-minute write, the complete writer census
  for both counters including the G-Get borrow branch and the Blackthorn
  restoration clear, the minute-based drain, and the Negate Time / Quickness
  interaction with that drain -
  `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` and
  `u5-decomp/functions/CAST2_OVL/`. This supersedes
  the counter labelling in the private DS/BSS map notes, in which the two
  counter names were swapped and both were misdescribed as radii.
- Dungeon first-person blackout when both light counters are zero, and the
  finding that the dungeon overlay only reads the two counters as a gate while
  the shared per-turn cleanup does all the decay - a whole-binary scan for
  readers and writers of both counters, recorded in
  `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md`, together
  with `u5-decomp/functions/DUNGEON_OVL/`. An
  earlier reading here described a dungeon-local light upkeep hook; that is
  withdrawn.
- Shared resident data model and relevant string/table regions - `u5-decomp/formats/data-ovl.md`.
- Existing cleanroom descriptions of time, dungeon lighting consumers, magic
  spell categories, overworld visibility integration, and the surface
  local-light mask boundary - `u5-spec/systems/time.md`,
  `u5-spec/systems/dungeon-mode.md`, `u5-spec/systems/magic.md`,
  `u5-spec/systems/overworld.md`, and `u5-spec/systems/visibility.md`.
