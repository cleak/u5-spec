# Moons

## 1. Scope

This document covers the lower status-strip sky display for the fixed hour
marker and the two moons, Trammel and Felucca. Natural moongate placement,
entry, and teleport destinations are mode-level behaviour owned by
`overworld.md`; this file only specifies the display values exposed to the
status panel.

## 2. Sky Strip Renderer

The status panel renders a twelve-cell strip for outdoor/town-family scenes.
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

Cells are numbered left to right from `0` through `11`. The renderer plots in
fixed order: hour marker first, then Trammel, then Felucca. If two markers
select the same cell, the later marker replaces the earlier one for that
refresh.

The strip is a plain twelve-character text run, not a pixel overlay. It is
printed into the full-screen text window at **row `0`, starting at column `6`**,
so it occupies columns `6` through `17` of the top text row. Blank cells are
spaces. The fixed hour marker is the character `*`; the two moon markers are the
phase digits from the tables below. Each cell is emitted in the ordinary strip
colour except the `*` cell, which uses a second, distinct colour; both come from
the resident per-display-mode chrome slots rather than from literals, so a clean
implementation should expose them as two configurable indices.

There are two distinct non-drawing cases, and they behave differently:

- **Scenes outside the surface/town family** (combat, intro, and every scene id
  at or above the location range) never reach the renderer at all. Nothing is
  drawn and nothing is cached.
- **Scene 25, Ararat** reaches the renderer but paints the strip's footprint
  flat instead of printing it: a filled rectangle from `(40, 0)` to `(152, 6)`
  in one chrome colour and a single pixel row from `(40, 7)` to `(152, 7)` in
  another. The two glyph bytes are still cached in this case. The renderer
  carries the same flat-fill branch for below-surface map levels, but the only
  live caller already declines to call it there, so that arm is unreachable in
  the shipped build.

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

Natural moongates remain separate from the sky/status renderer: the overworld
moongate animator paints any currently active gate, the saved Moonstone slots
drive live-terrain placement/waning, and the overworld loop has a separate live
entry hook plus the fixed narrative gate branch. Do not treat the hourly
sky/status refresh by itself as evidence for natural-moongate placement or
entry behavior.

The renderer is suppressed for dungeon-class views and the underworld status
presentation. Those scenes use their own lower-row presentation instead of the
surface sky strip, even though the same saved clock continues to advance.

## 4. Sources

This public description is a cleanroom prose rewrite from private status-panel
analysis. It does not reproduce decompiled source, assembly listings, raw bytes,
glyph dumps, or private address tables.

- Status-panel moon glyph lookup, day-of-month indexing, and the published
  twenty-eight-day table --
  `u5-decomp/functions/ULTIMA_EXE/0x4A84_combat_status_grid.md` and
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 3.
- Strip placement (twelve cells at columns six through seventeen of text row
  zero), the `*` hour-marker character, the per-cell colour selection, and the
  flat fill used when the strip is suppressed --
  `u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 6.6.
- Calendar bounds (day one through twenty-eight, reset after twenty-eight) and
  the single hour-change trigger --
  `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md` and
  `u5-decomp/notes/system-trace_turn-cycle.md`.
