# Moons

## 1. Scope

This document covers the sky strip: the twelve-cell display in the **top**
border of the world viewport that shows a fixed hour marker and the two moons,
Trammel and Felucca. Natural moongate placement, entry, and teleport
destinations are mode-level behaviour owned by `overworld.md`; this file
specifies the strip and the display values it exposes.

**Correction.** Earlier revisions of this document called the strip a "lower
status-strip" and treated it as part of the stats panel. Both readings are
withdrawn. The strip sits in the top chrome ribbon, in the gap directly above
the world viewport, and it is painted by its own renderer on its own cadence —
not by the stats-panel refresh. Its place inside the game-screen frame is
specified in `display-driver.md` section 7.

## 2. Sky Strip Renderer

The sky renderer paints a twelve-cell strip for outdoor/town-family scenes.
Each refresh starts from a blank strip, then attempts to plot up to three
markers:

- A fixed marker derived directly from the current hour.
- Trammel's glyph, read from the first resident moon table for the current
  calendar day.
- Felucca's glyph, read from the second resident moon table for the current
  calendar day.

The hour determines whether a marker is visible in the twelve-cell horizon and,
if so, which cell receives it. The fixed marker uses an hour-derived position
directly. The two moon markers use separate hour offsets, so Trammel and
Felucca can be above the visible horizon at different times of day. If a
computed position falls outside the visible twelve-cell range, that marker is
not printed for this refresh.

Cells are numbered left to right from `0` through `11`. Cell `11` is the rising
edge and cell `0` the setting edge, so every body tracks right to left across
the strip as the hours advance. The renderer plots in fixed order: hour marker
first, then Trammel, then Felucca. If two markers select the same cell, the
later marker replaces the earlier one for that refresh — so on a collision
Felucca wins over Trammel, and either moon wins over the hour marker.

The strip is a plain twelve-character text run, not a pixel overlay. It is
printed into the full-screen text window at **row `0`, starting at column `6`**,
so it occupies columns `6` through `17` of the top text row. Blank cells are
spaces.

### 2.1 Strip geometry

The strip lives in a gap in the frame's top chrome ribbon, bracketed by the
ordinary end-caps specified in `display-driver.md` section 7:

| Absolute column | Content |
|---:|---|
| 5 | Right-pointing bracket end-cap |
| 6..17 | The twelve marker cells; strip cell `i` is at column `6 + i` |
| 18 | Left-pointing bracket end-cap |

All of it is written through the full-screen text window at row `0`, so window
coordinates and absolute grid cells coincide.

Two routines share the strip. A **slate** painter runs once per mode entry: it
positions the cursor at column 5, draws the right cap, prints a stored run of
**twelve spaces**, and draws the left cap. That run is a literal in the shared
data overlay and is never modified at runtime; it exists only to blank the gap
and to place the two caps. The **marker** painter then builds a twelve-character
buffer in memory, plots up to three markers into it, positions the cursor at
column 6, and emits the buffer one cell at a time, changing the text foreground
per cell.

Because the two caps' outline strokes terminate on the ribbon's rule row, the
white rule at `y = 7` appears interrupted over `x = 41..150` rather than over the
caps' full cell extents.

### 2.2 Glyph bank and colours

**The strip does not render in the main text font.** The marker painter switches
the active font to the **runic** font (font slot 1, `RUNES.CH`, or its Hercules
equivalent) for the duration of the render and restores the main font before it
returns. The character codes it emits are the ASCII bytes for the digits `'0'`
through `'7'` for the eight moon phases, and the ASCII byte for `*` for the hour
marker — but in the runic font those code positions hold moon-phase artwork and
an eight-point starburst, not digits. An implementation that renders these codes
in the main fixed-cell font will draw literal digits and an asterisk on screen.

Each cell is emitted in one of two foreground colours drawn from the
user-interface colour table published in `display-driver.md` section 2: the hour
marker uses slot 5 (EGA value 14, bright yellow) and both moons use slot 6 (EGA
value 7, light grey). Blank cells inherit whatever foreground was last set. The
painter restores the accent foreground (slot 1) before it returns, so following
text is unaffected. Because these are table entries rather than literals, a clean
implementation should expose them as configurable indices.

There are two distinct non-drawing cases, and they behave differently:

- **Scenes outside the surface/town family** (combat, intro, and every scene id
  at or above the location range) never reach the renderer at all. Nothing is
  drawn and nothing is cached.
- **Scene 25 (Ararat, the underworld-only keep)** reaches the marker painter but
  makes it paint the strip's footprint flat instead of printing it: a filled
  rectangle from `(40, 0)` to `(152, 6)` in the chrome colour (colour-table slot
  2), then a single scanline from `(40, 7)` to `(152, 7)` in the accent colour
  (slot 1). This erases both end-caps as well as the markers, leaving a plain
  ribbon. The two glyph bytes are still cached in this case, because the cache is
  written before the visibility test. The slate painter tests the same
  conditions and, when either holds, draws nothing at all rather than erasing —
  the erase is the marker painter's job.

  The marker painter's erase branch also tests for a **below-surface map level**,
  but that arm is unreachable in the shipped game: the strip's only caller is the
  hour-change hook of the per-turn cleanup, whose own gate already excludes a
  party Z with the high bit set (`systems/time.md` Section 5). Earlier wording
  here listing below-surface levels alongside Ararat as cases that reach the
  painter is withdrawn — below the surface, nothing is drawn, nothing is erased,
  and nothing is cached, exactly as for combat and dungeon scenes. Keep the arm
  as defensive breadth if you reproduce the routine; do not derive behaviour from
  it. (The *wind banner* in the bottom ribbon is different: its own callers do
  reach it below the surface, and its erase branch is live — see
  `systems/weather.md` Section 2.1.)

| Marker | Visible hours | Cell position |
|--------|---------------|---------------|
| Fixed hour marker | `06:00..17:59` | `17 - hour` |
| Trammel | `00:00..08:59` | `8 - hour` |
| Trammel | `21:00..23:59` | `32 - hour` |
| Felucca | `00:00..02:59` | `2 - hour` |
| Felucca | `15:00..23:59` | `26 - hour` |

At all other hours, the corresponding marker is below the strip's visible
horizon and leaves the blank cell contents unchanged.

The glyph identity for each moon is table-driven, **indexed by the calendar
day of the month, one through twenty-eight**. It is not indexed by the hour.
Two earlier statements in this document were wrong and are retracted: the
tables are not twenty-four-entry hour tables, and they contain no off-horizon
sentinel entries at all.

Hour and day play distinct roles, and both are needed:

- The **hour** decides whether each marker is on the visible horizon and, if
  so, which of the twelve cells it lands in. That is the table above, and it is
  correct.
- The **day of the month** decides which phase glyph each moon shows. That is
  the table below.

**Table contents.** Two parallel byte tables, twenty-eight entries each, read
with the day of the month as the index. Every entry is an ASCII digit in the
range `'0'` through `'7'`.

| Day | Trammel | Felucca | Day | Trammel | Felucca |
|---:|:---:|:---:|---:|:---:|:---:|
| 1 | `'0'` | `'0'` | 15 | `'0'` | `'4'` |
| 2 | `'1'` | `'0'` | 16 | `'1'` | `'5'` |
| 3 | `'1'` | `'1'` | 17 | `'1'` | `'6'` |
| 4 | `'2'` | `'2'` | 18 | `'2'` | `'7'` |
| 5 | `'2'` | `'3'` | 19 | `'2'` | `'0'` |
| 6 | `'3'` | `'4'` | 20 | `'3'` | `'0'` |
| 7 | `'3'` | `'5'` | 21 | `'3'` | `'1'` |
| 8 | `'4'` | `'6'` | 22 | `'4'` | `'2'` |
| 9 | `'5'` | `'7'` | 23 | `'5'` | `'3'` |
| 10 | `'5'` | `'0'` | 24 | `'5'` | `'4'` |
| 11 | `'6'` | `'0'` | 25 | `'6'` | `'5'` |
| 12 | `'6'` | `'1'` | 26 | `'6'` | `'6'` |
| 13 | `'7'` | `'2'` | 27 | `'7'` | `'7'` |
| 14 | `'7'` | `'3'` | 28 | `'7'` | `'0'` |

Each phase digit `'0'` through `'7'` corresponds to a Moonstone slot index zero
through seven, obtained by subtracting `'0'`. **There is no sentinel byte in
either table.** An implementation that reserves a high-bit value for
"off horizon" is modelling something the tables do not contain; whether a moon
is drawn is decided solely by the hour-driven visibility rule above.

The two sequences are exactly periodic within the twenty-eight-day month:

- **Trammel** repeats every fourteen days, so it runs the full eight-phase
  cycle twice per month. Its fourteen-day pattern is
  `0, 1, 1, 2, 2, 3, 3, 4, 5, 5, 6, 6, 7, 7`.
- **Felucca** repeats every nine days with the pattern
  `0, 0, 1, 2, 3, 4, 5, 6, 7`. Twenty-eight is not a multiple of nine, so the
  month ends part-way through the fourth repetition and day twenty-eight is
  `'0'`, the first entry of the next repetition.

Because the calendar wraps day twenty-eight back to day one, the Felucca
sequence is not continuous across a month boundary; the original does not
smooth that discontinuity and neither should an implementation.

**Worked example, to settle the hour-versus-day question.** On a save reading
date `4-5-139` at hour 8: the hour marker's position is `17 - 8 = 9`, so it
occupies strip cell 9 (absolute column 15); Trammel's position is `8 - 8 = 0`,
so it occupies strip cell 0 (absolute column 6); Felucca's position is
`2 - 8 = -6`, which is outside `0..11`, so Felucca is not drawn. Trammel's
**glyph** comes from day 5, not hour 8, and the day-5 row of the table above
gives `'2'`. Any implementation that indexes the phase table by the hour will
draw `'4'` there and be visibly wrong.

The day index is the saved day-of-month byte, which the per-turn clock keeps in
the range one through twenty-eight and resets to one after it passes
twenty-eight. There is no day zero, so an implementation should treat a
zero or out-of-range day as a save-data error rather than looking up a
twenty-ninth entry.

The strip is presentation only. It caches the selected moon glyph bytes for the
current render pass, but those cached bytes are not gameplay state and are not
the saved-slot natural-moongate live-terrain schedule.

The overworld moongate entry hook reads the same cached glyph bytes after it
has confirmed the party is standing on live moongate terrain. Before noon it
uses the first cached glyph, and from noon onward it uses the second, to select
the saved Moonstone slot for ordinary natural-gate travel. Do not use the
status-strip cache by itself to derive natural moongate placement; placement
and entry are specified in `overworld.md`.

## 3. Integration

The moon glyphs and fixed hour marker are display state. They do not, by
themselves, advance time, place moongates, or mutate save data.

**Refresh cadence.** The strip renderer runs from exactly one place: the
per-turn cleanup pass, and only when that pass observes the hour changing, and
only in a scene that shows the surface/town status strip. It is **not** driven
by ordinary stats-panel redraws, and an earlier statement in this document that
it should be refreshed on every stats-panel redraw is retracted.

The two cadences are different, and both matter:

- The **cell position** of each marker changes every hour, which is why an
  hour change is the trigger.
- The **glyph identity** changes only when the day rolls over. Between day
  rollovers, every hourly refresh reads the same two glyph bytes.

Each refresh caches the two glyph bytes for the current day *before* it tests
whether either marker is on the visible horizon, so the cache holds the current
day's phase for both moons even when neither marker is drawn. Consumers of the
cache must not infer "no phase" from "not drawn".

Natural moongates remain separate from the sky/status renderer. The saved
Moonstone slots drive live-terrain placement and waning, and the overworld loop
has a separate live entry hook; the Shrine of the Codex approach gate is a third
and unrelated branch. Do not treat the hourly sky/status refresh by itself as
evidence for natural-moongate placement or entry behaviour.

Two further separations matter, because the phase glyphs above are easy to
over-read:

- **The moon phase does not place gates.** Placement is gated on the hour alone,
  so every eligible gate opens together at nightfall and fades together after
  dawn. The glyph the strip shows decides only which Moonstone slot an entered
  gate leads to.
- **There is no moongate animator.** An earlier revision of this document
  referred to one; that reading is withdrawn in full. Gates are ordinary live
  terrain, and the render-frame scratch block once attributed to a gate animator
  belongs to the night-time light beacon in `systems/visibility.md` Section
  12.6.

The renderer is suppressed for dungeon-class views, combat, and the underworld
presentation, even though the same saved clock continues to advance. The dungeon
view puts its own bracketed level label in the same top-ribbon gap and its own
bracketed facing label in the bottom-ribbon gap; see `systems/dungeon-mode.md`
and `display-driver.md` section 7. Combat and the underworld leave both gaps as
plain chrome.

## 4. Sources

This public description is a cleanroom prose rewrite from private screen-layout
and status analysis. It does not reproduce decompiled source, assembly listings, raw bytes,
glyph dumps, or private address tables.

- Sky-strip moon glyph lookup, day-of-month indexing, and the published
  twenty-eight-day table -- the sky-strip renderer note among the resident
  user-interface function notes under `u5-decomp/functions/ULTIMA_EXE/`
  (whose filename is a misnomer: the routine paints the top sky strip, not a
  combat grid), and `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md`
  section 3.
- Strip placement (twelve cells at columns six through seventeen of text row
  zero), the `*` hour-marker character, the per-cell colour selection, and the
  flat fill used when the strip is suppressed --
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 6.6.
- Source provenance: the separation of moon phase from moongate placement, and
  the withdrawal of the moongate animator, are derived from private analysis
  note `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- Calendar bounds (day one through twenty-eight, reset after twenty-eight), the
  single hour-change trigger, and that trigger's own scene-and-floor gate --
  which is what makes the painter's below-surface erase arm unreachable -- the
  per-turn cleanup note under `u5-decomp/functions/ULTIMA_EXE/`,
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 3, and
  `u5-decomp/notes/system-trace_turn-cycle.md`.
- Source provenance: the strip's location in the top viewport border, the two
  bracket end-cap cells, the stored twelve-space slate, the runic font slot used
  for the render, the identification of the two foreground colours with the
  user-interface colour table, the right-to-left travel direction and collision
  priority, and the erase branch's exact rectangles are derived from private
  analysis note `../u5-decomp/notes/gameplay_screen_layout_2026-08-22.md`,
  cross-checked against a fresh local re-read of the shipped executable and
  shared data overlay. The day-indexed phase table was re-read byte for byte
  from the shipped data during that check and matches the table published above.
