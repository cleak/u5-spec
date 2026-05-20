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

| Marker | Visible hours | Cell position |
|--------|---------------|---------------|
| Fixed hour marker | `06:00..17:59` | `17 - hour` |
| Trammel | `00:00..08:59` | `8 - hour` |
| Trammel | `21:00..23:59` | `32 - hour` |
| Felucca | `00:00..02:59` | `2 - hour` |
| Felucca | `15:00..23:59` | `26 - hour` |

At all other hours, the corresponding marker is below the strip's visible
horizon and leaves the blank cell contents unchanged.

The glyph identity for each moon is table-driven, **indexed by the current hour of day** (not by the calendar day as earlier wording suggested). The renderer reads the two parallel byte tables and writes the resulting ASCII glyph digit to the corresponding cell.

**Table contents** (extracted from shipped `DATA.OVL` resident bytes, 24 entries each, indexed by `hour ∈ 0..23`):

| Hour | Trammel | Felucca |
|---:|:---:|:---:|
| 0 | `0xF0` (off-horizon) | `0x80` (off-horizon) |
| 1 | `'0'` | `'0'` |
| 2 | `'1'` | `'0'` |
| 3 | `'1'` | `'1'` |
| 4 | `'2'` | `'2'` |
| 5 | `'2'` | `'3'` |
| 6 | `'3'` | `'4'` |
| 7 | `'3'` | `'5'` |
| 8 | `'4'` | `'6'` |
| 9 | `'5'` | `'7'` |
| 10 | `'5'` | `'0'` (off-horizon) |
| 11 | `'6'` | `'0'` (off-horizon) |
| 12 | `'6'` | `'1'` |
| 13 | `'7'` | `'2'` |
| 14 | `'7'` | `'3'` |
| 15 | `'0'` | `'4'` |
| 16 | `'1'` | `'5'` |
| 17 | `'1'` | `'6'` |
| 18 | `'2'` | `'7'` |
| 19 | `'2'` | `'0'` (off-horizon) |
| 20 | `'3'` | `'0'` (off-horizon) |
| 21 | `'3'` | `'1'` |
| 22 | `'4'` | `'2'` |
| 23 | `'5'` | `'3'` |

Each phase digit `'0'..'7'` corresponds to a Moonstone slot index `0..7`, which the natural-moongate entry hook uses (after stripping `'0'`) to look up the saved Moonstone destination. High-bit sentinels (`0xF0`, `0x80`) mean the moon is below the horizon for that hour; the entry hook treats high-bit cached glyphs as "no gate for this slot".

Trammel cycles through all eight phases roughly twice per day (the larger, slower moon); Felucca cycles once per day with off-horizon gaps near hours 10-11 and 19-20.

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
themselves, advance time, place moongates, or mutate save data. They should be
refreshed whenever the stats panel is redrawn and whenever the per-turn cleanup
observes an hour change in a scene that shows the surface/town status strip.

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

- Status-panel moon glyph lookup and phase cadence --
  `u5-decomp/functions/ULTIMA_EXE/0x4A84_combat_status_grid.md`.
