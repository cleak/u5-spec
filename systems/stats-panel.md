# Stats Panel

## 1. Scope

The stats panel is the fixed side/status area that summarizes the active party
and the counter, date and timed-effect rows beneath them. It is presentation state, not a
separate gameplay store: it reads party records, inventory counters, combat
presentation state, time/date bytes, and vehicle state owned by other systems.

This document specifies the panel refresh contract so systems that mutate HP,
status, gold, food, light, combat state, or transport know what must become
visible after a refresh.

## 2. Refresh Model

The original refresh path repaints the whole panel. It does not maintain a
per-row dirty list. A refresh:

1. Selects the stats text window.
2. Repaints all six party rows in order, including rows for absent party slots.
3. Repaints the counters row, then the date row.
4. Repaints the timed-effect slot in the upper divider band, or repaints that
   band as plain chrome when no effect is running.
5. Selects the message window before returning.

The panel does **not** repaint the sky strip, the wind banner, or the
game-screen frame. Those have their own owners and their own cadences.

Callers therefore request "refresh the panel", not "refresh HP for slot N".
Systems that heal, damage, poison, resurrect, change active player, age light
counters, or leave combat should assume the next refresh can redraw everything
visible in the panel.

## 3. Panel Geometry

The panel lives in the stats text window, cell columns 24 through 39, rows 1
through 9 (`text-output.md` section 10.1). Inside that window it writes a
**fifteen-column** field, absolute columns 24 through 38. Column 39 is never
written by the panel, because the roster and counter boxes drawn by the
game-screen frame are fifteen cells wide: their right rule sits at pixel
`x = 312`, the first pixel of column 39 (`display-driver.md` section 7).

| Absolute row | Contents |
|---:|---|
| 1..6 | The six party rows (section 4). |
| 7 | The upper divider band, carrying the timed-effect slot (section 8). Not part of the stats window; written through the full-screen window. |
| 8 | The counters row: food, and either gold or ship hull (section 6). |
| 9 | The date row (section 7). |
| 10 | The lower divider band. Plain chrome; nothing is written into it. |

Row 0, the top ribbon to the right of the centre divider, is the panel's label
strip (section 9). The sky strip in the top ribbon *left* of the centre divider
is not a stats-panel element at all; it belongs to the sky renderer specified in
`systems/moons.md` and is repainted on a different cadence.

Every cursor position the refresh uses is window-relative, so an implementation
that models windows must add the window origin; the tables in this document give
absolute screen columns and rows.

## 4. Party Rows

The panel has six character rows, one for each possible active party slot, at
absolute rows 1 through 6 for slots 0 through 5 in roster order.

If a row index is at or beyond the current travelling-party size, the row is
filled with **fifteen spaces** and nothing else is drawn. This is how the panel
removes stale companions after party-size changes, and it is the direct evidence
that the row field is fifteen columns wide rather than sixteen.

For a live party row the field layout is fixed:

| Absolute columns | Width | Field | Presentation |
|---|---:|---|---|
| 24..32 | 9 | Name | Printed from the character record, then space-padded out to nine cells. A name longer than nine characters is not truncated by the panel; the pad loop simply contributes nothing. |
| 33 | 1 | Active-player marker | The fixed-cell font's right-pointing arrow, glyph code `0x1A`, or a space. |
| 34..37 | 4 | Current HP | Decimal, right-justified in a four-column space-padded field. |
| 38 | 1 | Status | The character record's status byte, emitted verbatim as a glyph. |

A worked example: a nine-column name `BAFF` padded with five spaces, a blank
marker cell, `  60` right-justified, and the status letter `G` produce the
fifteen-cell row `BAFF      60G`.

### 4.1 The active-player marker

The marker is drawn on the row whose slot equals the resident active-player
selector, with one exception: if that member's status byte is `'D'` (dead) or
`'S'` (sleeping), a space is drawn instead **and the selector is reset to the
none sentinel**. All other rows always get a space in column 33.

An earlier revision of this document said the selector is consumed by whichever
refresh displays the marker, so a later refresh would show no marker unless a
command set it again. That is withdrawn. The marker is persistent: it survives
any number of refreshes and is cleared only by an explicit selection change or
by the dead/sleeping rule above.

## 5. Combat Row Overlays

In combat-class scenes, each party row can receive extra combat presentation
from the combat actor/effect descriptor table. The panel does not maintain a
separate row-overlay table; it reads the same per-slot descriptors that the
combat round walker, actor dispatcher, spell paths, and death/despawn cleanup
own.

The overlay rules are:

- A matched current action/effect descriptor renders the row's main fields in
  inverse video. The refresh emits the text system's inverse-video control
  before the name when the current combat slot selector is not the none
  sentinel, that selected descriptor is party-side, and the descriptor's
  target/owner field names this party row.
- The status glyph is replaced by `C` when combat is active and the row's own
  combat descriptor has the party-side marker set, the monster-side marker
  clear, is not marked dead, carries the controlled/charmed bit, and names this
  same party row in its owner/character field. All five conditions are
  required, and only those five: the asleep/magically-disabled bit is not part
  of the test, so a sleeping party member still shows the ordinary roster
  status letter. Placement makes the party-side and monster-side markers
  mutually exclusive, so the monster-side term never changes the outcome for a
  well-formed descriptor, but it is part of the condition the panel actually
  evaluates and is listed here to match `systems/combat.md` Section 6.1a.
  Earlier revisions of this document described the glyph as marking a party
  member "casting and self-targeted"; that reading of the bit is withdrawn — it
  is the controlled/charmed state specified in `systems/combat.md`
  Section 6.1a, set by monster possession, by the Charm spell, and by the Sword
  of Chaos compulsion. This overlay is separate from the persistent character
  status byte and from the shared Mass Charm active-effect tag, which also
  displays `C` in the timed-effect slot (section 8).
- Under the same selected-descriptor match, the refresh emits the inverse-video
  control again after the status glyph, restoring the following output to the
  previous style. The two controls do not consume visible cells; they bracket
  the name, active-player cursor cell, HP field, and status cell.

These overlays are panel presentation only. Combat actor state, casting queues,
and damage/status resolution are owned by `systems/combat.md` and
`systems/magic.md`. A compatible implementation should therefore derive these
row overlays at refresh time from the live combat descriptors and current-slot
selector, not from a second presentation cache that can diverge from combat.

## 6. The Counters Row

Absolute row 8, columns 24..38. It is written left to right in one pass and
always fills all fifteen cells.

**Food.** The literal `F:` occupies columns 24 and 25. The saved food counter
follows immediately at its natural decimal width, with no field padding. Spaces
are then emitted until the cursor reaches column 32, so the food group always
occupies columns 24..31 whatever the counter's magnitude.

**Gold, ordinary case.** Starting at column 32:

1. One space if gold is below 1000, another if it is below 100, another if it is
   below 10 — zero to three leading spaces.
2. The literal ` G:` — note the **leading space**, which is part of the stored
   label, giving three cells.
3. The gold value at its natural decimal width, with no field padding.

The arithmetic works out so that the ladder of leading spaces shifts the `G:`
prefix left as the number grows, while the digits stay put: for every gold value
from 0 to 9999 the group occupies exactly columns 32..38 and the **last digit
sits in column 38**, the last cell of the field. A trailing pad loop runs to the
end of the field and contributes nothing for in-range values.

Worked examples, showing which of the seven cells 32..38 each character lands
in:

| Gold | 32 | 33 | 34 | 35 | 36 | 37 | 38 |
|---:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| `5` | space | space | space | space | `G` | `:` | `5` |
| `150` | space | space | `G` | `:` | `1` | `5` | `0` |
| `9999` | space | `G` | `:` | `9` | `9` | `9` | `9` |

(The single space that always immediately precedes `G` is the label's own
leading space; the ones before it come from the ladder.)

**Gold slot, ship variant.** When the scene is not combat-class and the
transport/action marker is in the ship family `0x20..0x27`, the gold group is
replaced in place by the ship's hull condition: the literal `Ship:` in columns
32..36, then the hull value at its natural width, then one extra space when the
hull is below ten. The result fills columns 32..38 for hull values 0..99. This
variant does not use the gold group's leading-space ladder.

## 7. The Date Row

Absolute row 9, columns 24..38. The row is reached by emitting a line feed,
which in this text system also returns the carriage, so the cursor lands in
column 24. Then:

1. Three fixed spaces.
2. A fourth space when **both** the month and the day are below ten.
3. Month at natural width, a hyphen, day at natural width, a hyphen, and the
   year **zero-padded to three digits**.
4. Spaces to the end of the field.

The leading-space rule is what centres the result; there is no measurement or
centring arithmetic. A date such as `4-5-139` is seven characters and gets four
leading spaces, so it occupies columns 28..34 — exactly centred on column 31, the
field's middle cell. A date such as `12-25-139` is nine characters and gets
three, occupying columns 27..35, also centred. Mixed-width dates such as
`12-5-139` sit one cell left of true centre, which is what the original shows.

## 8. The Timed-Effect Slot

Absolute row 7, in the upper divider band, written through the full-screen text
window rather than the stats window:

| Absolute column | Content |
|---:|---|
| 30 | Right-pointing bracket end-cap |
| 31 | The effect glyph |
| 32 | Left-pointing bracket end-cap |

**Correction.** An earlier revision of this document said the slot is framed
"above and below" the glyph. It is not: the two end-caps flank it **left and
right** in the same row, and they are the ordinary bracket end-caps specified in
`display-driver.md` section 7, the same composite used by the sky strip, the
wind banner and the message-window prompt.

**Correction.** An earlier revision said the effect glyph is rendered through
the resident miniature tile-glyph path rather than the fixed-cell font. That is
withdrawn. The byte is emitted as an ordinary character through the text system,
in whatever font slot is active — which at this point is always the main
fixed-cell font (`IBM.CH`), because the only routine that switches to the runic
font restores the main font before it returns. An implementation that renders
this slot through a tile path, or in the runic font, will draw the wrong shape.

The byte driving the slot is the game's **single global timed-magic-effect
code**, paired with a single remaining-duration counter in turns. A reserved
duration value means "permanent" and never decays. The slot does **not** stack:
installing a new effect displaces whatever was there.

| Effect code | Rendered as | Effect | Duration when installed |
|---|---|---|---|
| `0x00` | — | No effect. The band is repainted as plain chrome instead. | — |
| `'P'` | letter P | Protection (`In Sanct`) | 20 turns from the spell, 100 from the scroll |
| `'Q'` | letter Q | Quickness (`Rel Tym`) | 30 turns |
| `'C'` | letter C | Mass Charm / Confusion (`Quas An Wis`) | 20 turns |
| `'N'` | letter N | Negate Magic (`In An`) | 10 turns from the spell, 20 from the scroll |
| `'T'` | letter T | Negate Time (`An Tym`) | 10 turns from the spell, 20 from the scroll |
| `0x0E` | pictogram | Amulet of Lord British worn | permanent |
| `0x1C` | pictogram | Crown of Lord British worn | permanent |
| `0x1D` | pictogram | Black Badge worn | permanent |

When the code is zero the refresh repaints the band instead of drawing anything:
fill `(191, 57) - (312, 62)` in the chrome colour, then stroke the two single
scanlines `(192, 56) - (311, 56)` and `(192, 63) - (311, 63)` in the accent
colour. That is why a freshly loaded save shows a plain chrome-coloured band — blue on
the sixteen-colour drivers — and a slot only appears once an effect is
running.

The countdown is driven by the shared per-turn party pass: a non-zero,
non-permanent counter is decremented, and when it reaches zero the effect code is
cleared and a panel refresh is requested. The code is also cleared outright on
entry to the command overlay and on entry to two of the shop/audience scenes.
This is the same code owned by `systems/magic.md`; it is adjacent to, but
distinct from, the transport/action marker used by boarding and movement.

## 9. The Panel Label Strip

Absolute row 0, columns 24..38 — the top ribbon to the right of the centre
divider — is a repaintable label strip belonging to the panel. Its plain state is
produced by filling `(192, 0) - (311, 6)` in the chrome colour and stroking the
single scanline `(192, 7) - (311, 7)` in the accent colour.

Panel-driven flows write a bracketed label into it: `Select:` during the Z-stats
party-member selection, and `Items:` during the U-Use item browser, each between
a right-pointing and a left-pointing end-cap. This is the one label on the whole
screen that is **genuinely centred** by measurement. Given a label of `L`
characters:

- The opening cap goes in column `left = 30 - (L / 2)`, integer division.
- The label occupies columns `left + 1` through `left + L`.
- The closing cap goes in column `left + L + 1`.
- The chrome to either side is repainted first: fill `(192, 0)` to
  `(left * 8, 6)` and `((left + L + 2) * 8, 0)` to `(311, 6)` in the chrome
  colour, then stroke the two rule fragments `(192, 7)` to `(left * 8, 7)` and
  `((left + L + 2) * 8, 7)` to `(311, 7)` in the accent colour.

For the seven-character `Select:` that puts the caps in columns 27 and 35 and
the text in columns 28 through 34 — centred on column 31, the panel field's
middle cell. An odd-length label always lands exactly on column 31; an
even-length one straddles columns 30 and 31, because the integer division
truncates.

Every other bracketed label on the screen (sky strip, wind banner, effect slot,
dungeon level and facing) sits at a fixed column and is "centred" only because
its content is a fixed width.

What happens to the panel *body* while a label is up differs by flow and is
owned by those flows, not by this document. Member selection leaves the body
alone — the six roster rows, the counters row and the date row all stay on
screen and the indicated member's fifteen content cells are simply inverted —
while the item picker erases the counters and date rows and draws its own rows
over the roster, restoring both with a full refresh when it closes. Both are
specified in `inventory.md` sections 4.3 and 4.4. The panel contract here covers
only the strip and the frame around it.

## 10. Hooks From Other Systems

Common refresh triggers include:

- startup or mode-entry UI assembly;
- party damage, trap damage, poison, disease, cure, heal, resurrection,
  completed-camp recovery, and the Ring of Regeneration tick. None of these is
  an hourly effect: the poison point and the ring roll both fire once per shared
  party status pass, as specified in `systems/time.md` section 5, while camp
  recovery fires once at the end of a completed long camp, as specified in
  `systems/rest-and-camp.md` section 5;
- active-player selection changes;
- torch or light-spell counter updates;
- combat entry/exit and combat action presentation;
- inventory/resource changes that affect food, gold, light, or transport
  display.

The panel does not decide whether those state changes are legal. It only reads
the resulting state and paints it.

## 11. Compatibility Rules

- Always clear unused party rows during a full refresh.
- Preserve the fixed-width name and HP columns so stale characters cannot
  remain after shorter names or smaller numbers.
- Draw the active-player marker on every refresh while a member is selected; it
  is persistent, not consumed by the refresh. Clear the selector only when the
  selected member is dead or sleeping, or when a command changes the selection.
- Reproduce the counters row exactly: the leading-space ladder shifts the gold
  label rather than padding the number, so the last gold digit always lands in
  the field's final column.
- In combat scenes, apply combat presentation overlays from the live combat
  actor/effect descriptors after reading the base party row, so casting can
  replace the ordinary status and the selected target row can be inverse-video
  highlighted.
- Do not model the panel as the owner of HP, status, food, gold, light, combat,
  or vehicle state. It is a read-side presentation surface.

## 12. Boundaries And Owned Work

No stats-panel-specific open work is currently known at this layer. Remaining
transport-marker, combat-descriptor, and text-rendering questions live in
`systems/vehicles.md`, `systems/combat.md`, and `systems/text-output.md`.

## 13. Sources

This is a cleanroom behavioral rewrite from private resident UI notes. It does
not reproduce private source, decompiler output, assembly excerpts, raw dumps,
private address tables, or implementation listings.

- Full-panel refresh, per-row rendering, combat row overlays, and the middle
  value block: the resident user-interface function notes under
  `u5-decomp/functions/ULTIMA_EXE/`.
- Cadence of the poison, ring-regeneration, and camp-recovery refresh triggers
  in Section 10: `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.
- Source provenance: the fifteen-column field, the exact column bindings of
  every party-row and counters-row field, the leading-space mechanisms behind the
  gold and date alignment, the persistence of the active-player marker, the
  timed-effect slot's cells, driving byte, code table and font, the plain-band
  repaint, and the panel label strip are derived from private analysis note
  `../u5-decomp/notes/gameplay_screen_layout_2026-08-22.md`, cross-checked
  against a fresh local re-read of the shipped executable and shared data
  overlay. Two claims in earlier revisions of this document are withdrawn there:
  that the effect glyph goes through the miniature tile-glyph path, and that its
  brackets sit above and below it.
- The exact condition behind the combat `C` status override (party-side set,
  monster-side clear, dead clear, controlled/charmed bit set, descriptor owner
  field matching the drawn row) and the withdrawal of the earlier "casting and
  self-targeted" reading:
  `u5-decomp/notes/2026-08-22_combat-status-magic-verify.md`.
- Text-window primitives used by the panel: `systems/text-output.md`.
- Saved calendar, food, gold, transport/action, and character-record fields:
  `formats/saved-gam.md`.
