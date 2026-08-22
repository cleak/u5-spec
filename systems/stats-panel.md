# Stats Panel

## 1. Scope

The stats panel is the fixed side/status area that summarizes the active party
and a small bottom block of session state. It is presentation state, not a
separate gameplay store: it reads party records, inventory counters, combat
presentation state, time/date bytes, and vehicle state owned by other systems.

This document specifies the panel refresh contract so systems that mutate HP,
status, gold, food, light, combat state, or transport know what must become
visible after a refresh.

## 2. Refresh Model

The original refresh path repaints the whole panel. It does not maintain a
per-row dirty list. A refresh:

1. Selects the stats-panel text window.
2. Repaints all six party rows, including rows for absent party slots.
3. Repaints the bottom information block.
4. Repaints the vehicle/transport glyph area.
5. Restores the main text window before returning.

Callers therefore request "refresh the panel", not "refresh HP for slot N".
Systems that heal, damage, poison, resurrect, change active player, age light
counters, or leave combat should assume the next refresh can redraw everything
visible in the panel.

## 3. Party Rows

The panel has six character rows, one for each possible active party slot.
Rows are indexed in roster order, slot `0` through slot `5`.

If a row index is outside the current travelling-party size, the row is cleared
with spaces. This is how the panel removes stale companions after party-size
changes.

For a live party row, the visible fields are:

| Field | Source | Presentation |
|-------|--------|--------------|
| Name | Character record name | Printed from the record and padded to a fixed name column. |
| Active-player cursor | Resident active-player selector | Drawn only for the selected slot when that member is not Dead or Asleep; otherwise blank. |
| Current HP | Character record current-HP word | Printed as a four-character right-justified decimal. |
| Status | Character record status byte | Printed as the raw status glyph in ordinary modes. |

The active-player cursor is single-shot presentation state. When the refresh
draws the cursor for the selected row, the active-player selector is cleared.
The next command that selects an active member must set it again if the cursor
should appear on a later refresh.

## 4. Combat Row Overlays

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
  displays `C` in the bottom block.
- Under the same selected-descriptor match, the refresh emits the inverse-video
  control again after the status glyph, restoring the following output to the
  previous style. The two controls do not consume visible cells; they bracket
  the name, active-player cursor cell, HP field, and status cell.

These overlays are panel presentation only. Combat actor state, casting queues,
and damage/status resolution are owned by `systems/combat.md` and
`systems/magic.md`. A compatible implementation should therefore derive these
row overlays at refresh time from the live combat descriptors and current-slot
selector, not from a second presentation cache that can diverge from combat.

## 5. Bottom Information Block

After repainting the six party rows, the refresh path paints a bottom block.
The confirmed semantic pieces are:

| Region | Meaning |
|--------|---------|
| Food/provisions area | Displays the saved party food counter with a short label. |
| Middle counter area | Displays the saved party gold word in ordinary and combat scenes, right-aligned in the middle block. When the transport/action marker byte is in the ship family `0x20..0x27`, this slot instead displays a short ship-status label and the current ship hull condition from active-object byte `+5`. |
| Calendar/year area | Displays month, day, and year from the saved calendar fields. Month and day are printed as a short `M-D` pair; the year is printed as a three-digit zero-padded value. |
| Sky/status strip | In surface and town-family views, renders the twelve-cell fixed-hour-marker and moon strip described in `systems/moons.md`; dungeon-class and underworld views use their own lower-row presentation instead. |
| Active-effect glyph area | Displays the shared timed-magic-effect code as a glyph when that code is nonzero, using the text-window border helpers to frame the slot above and below the glyph. When it is zero, draws the empty four-corner placeholder instead. This is the code owned by `systems/magic.md`, so the glyph is how the player sees which timed spell, scroll effect, or worn regalia aura is currently running; every installer and every clear site of that slot requests a stats redraw. It is adjacent to, but distinct from, the transport/action marker used by boarding and movement. |

The active-effect glyph is rendered through the resident miniature tile-glyph
path described in `formats/tiles.md`, not by cropping `TILES.16` and not by the
ordinary fixed-cell font. Its byte doubles as a tile/glyph selector for that
compact UI renderer; the transport/action marker byte remains a separate state
field.

The bottom-block layout pads fields to fixed columns, so shorter numbers do not
leave stale digits from earlier larger values. The middle block is padded to the
right edge of the sixteen-column stats window after gold or light/transport
counter rendering.

Current clean public specs already identify the underlying saved food, gold,
calendar, timing/status tag, transport/action marker, and active-object fields
in `formats/saved-gam.md`, `systems/time.md`, `systems/vehicles.md`, and
`systems/active-objects.md`; this panel spec does not redefine those fields.
The alternate middle counter is therefore ship-only in the currently mapped
marker space: the panel-side selector is the transport/action marker family
`0x20..0x27`, and the counter is the same hull-condition byte used by boarding,
X-it, shipwright delivery, and broadside damage. Values outside that ship
family do not select the hull counter for the stats panel, even if nearby
active-object auxiliary bytes contain nonzero ship-like data. Values inside the
family select the hull presentation by family; the stats panel does not perform
a separate parked-object validation before reading the current active vehicle
hull byte.

## 6. Hooks From Other Systems

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

## 7. Compatibility Rules

- Always clear unused party rows during a full refresh.
- Preserve the fixed-width name and HP columns so stale characters cannot
  remain after shorter names or smaller numbers.
- Treat the active-player cursor as consumed by the refresh that displays it.
- In combat scenes, apply combat presentation overlays from the live combat
  actor/effect descriptors after reading the base party row, so casting can
  replace the ordinary status and the selected target row can be inverse-video
  highlighted.
- Do not model the panel as the owner of HP, status, food, gold, light, combat,
  or vehicle state. It is a read-side presentation surface.

## 8. Boundaries And Owned Work

No stats-panel-specific open work is currently known at this layer. Remaining
transport-marker, combat-descriptor, and text-rendering questions live in
`systems/vehicles.md`, `systems/combat.md`, and `systems/text-output.md`.

## 9. Sources

This is a cleanroom behavioral rewrite from private resident UI notes. It does
not reproduce private source, decompiler output, assembly excerpts, raw dumps,
private address tables, or implementation listings.

- Full-panel refresh and bottom-block behavior:
  `u5-decomp/functions/ULTIMA_EXE/0x2900_redraw_full_stats.md`.
- Cadence of the poison, ring-regeneration, and camp-recovery refresh triggers
  in Section 6: `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.
- Per-row rendering and combat row overlays:
  `u5-decomp/functions/ULTIMA_EXE/0x2726_draw_stats_row.md`.
- Middle value block helper:
  `u5-decomp/functions/ULTIMA_EXE/0x2884_draw_gold_panel.md`.
- Resident miniature tile-glyph renderer:
  `u5-decomp/functions/ULTIMA_EXE/0x7040_render_2x16_sprite.md`.
- Vehicle/status glyph framing helpers:
  `u5-decomp/functions/ULTIMA_EXE/0x4C2A_draw_text_window_top.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x4CCE_draw_text_window_bottom.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x4F3C_draw_glyph_corners.md`.
- The exact condition behind the combat `C` status override (party-side set,
  monster-side clear, dead clear, controlled/charmed bit set, descriptor owner
  field matching the drawn row) and the withdrawal of the earlier "casting and
  self-targeted" reading:
  `u5-decomp/notes/2026-08-22_combat-status-magic-verify.md`.
- Text-window primitives used by the panel: `systems/text-output.md`.
- Saved calendar, food, gold, transport/action, and character-record fields:
  `formats/saved-gam.md`.
