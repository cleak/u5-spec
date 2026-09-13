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

### 2.1 Complete side-effect census

The full-panel parent is read-only with respect to character records, party
resources, vehicle and hull state, combat descriptors, calendar state, and the
timed-effect code and duration. The footer reads those owners only. The sole
gameplay-state write anywhere in the refresh is in the per-row painter: if the
row being drawn is both the active-player selection and stored as Dead or
Sleeping, the painter replaces the marker with a space and resets the selector
to the none sentinel. A selected row in any other stored status keeps the
selector. No other gameplay mutation occurs.

The remaining writes are presentation state. Text emission updates the stats
window's saved cursor and the rendered cells; the divider step updates its
pixels; and window selection updates the active-window bookkeeping. The refresh
always leaves the message window selected, but does not reposition that
window's saved cursor. Temporary inverse-video and cap-rendering style changes
are balanced before return. The stats window's own cursor ends at local
`(9, 6)` after the three-cell cap/effect/cap sequence, or local `(6, 6)` when a
zero effect code selects the graphics-only plain-band repaint.

The refresh emits no message-window text, death line, or status narration, and
plays no sound. Its text consists only of the panel fields specified below. It
also **requests no scroll** and issues no display command against the message
window's rectangle, which is what lets a caller repaint the panel in the middle
of an unfinished message-window frame without disturbing it - the rescue
cinematic of `systems/blackthorn.md` Section 7 does exactly that, once per
restored member. One executed repaint issued 122 driver commands, all of them
glyph blits or single-scanline fills and none of them a scroll. *(Added
2026-09-12, issue #269. Whether a panel fill's coordinates can ever fall inside
the message-window rectangle is separately open; `OPEN-QUESTIONS.md`.)*

The panel does **not** repaint the sky strip, the wind banner, or the
game-screen frame. Those have their own owners and their own cadences.

Callers therefore request "refresh the panel", not "refresh HP for slot N".
Systems that heal, damage, poison, resurrect, change active player, age light
counters, or leave combat should assume the next refresh can redraw everything
visible in the panel.

### 2.2 Refresh cadence: immediate repaint versus deferred request

Sections 2 and 2.1 say what a refresh paints and what it touches. This section
says **when** it runs.

The original has two refresh mechanisms and chooses between them **per call
site**, not by any general rule:

- **Immediate repaint.** The routine that changed the state paints the whole
  panel itself, so the panel is already correct before that routine returns,
  and before any narration, animation or key wait that follows inside it.
- **Deferred request.** The routine instead raises a one-byte *panel refresh
  request*. The panel stays stale until a mode loop's command prompt consumes
  the request (Section 2.3).

Nothing refreshes the panel at a turn boundary. The per-turn cleanup does not
refresh it except on a day rollover (Section 2.4), and no idle world tick and no
per-frame sprite animator refreshes it at all.

Census of the shipped program. The full-panel refresh has eighty direct call
sites: seventy-four immediate repaints inside a command, a shop or inn
sub-screen, a cutscene or a shared helper; the four mode-loop consumers of
Section 2.3; the boot-time first paint; and the day-rollover repaint of
Section 2.4. Twenty-three further sites raise the deferred request instead of
painting. Nine of the eighty painting sites are resident and the rest live in
overlays; five code overlays never paint the panel at all.

**The same counter goes both ways.** Which mechanism a site uses is not
predictable from the counter that changed, from the command class, or from the
scene, so an implementation must carry the mechanism per caller rather than
derive it. Four worked cases:

| Change | Mechanism |
|---|---|
| Damage applied to a party slot through the shared party-damage path | immediate repaint, as that path's last act |
| The shared healing helper's hit-point gain | deferred request |
| The troll-bridge toll's gold debit | deferred request |
| The shop, healer, guild, inn, resurrection and conversation-payment gold debits | immediate repaint, a few steps after the debit |

There is a tendency, useful as a sanity check and not as a rule: a flow that
holds the screen before returning — shop and inn menus, the stats browser, the
camp hour loop, mix-reagents, conversations, cutscenes, blocking narration
pages — repaints inline, while a command that ends promptly tends to file a
request.

**The request is a plain boolean.** It is written only "set" or "clear", is
only ever tested against "clear", and has no second value, no bitmask, no
priority and no partial-refresh encoding. No shipped binary reaches it through
a computed pointer, so there is no indirect writer. Its initial value is clear.
Do not model it as a queue of regions or as a count of pending refreshes.

**A raise does not depend on the change surviving.** The troll-bridge toll
raises the request before it tests whether the party can afford the toll, and
does not lower it when an unaffordable debit is rolled back. A raise can
therefore outlive the change that prompted it; the only consequence is one
redundant repaint of an unchanged panel.

### 2.3 Where the deferred request is consumed

Exactly four places consume the request, one per mode loop, and all four do the
same three things in the same order: test the request, refresh the whole panel
if it is set, clear it. All four sit at the **head of that loop's command
prompt**, not at the end of a turn:

| Mode | Consumption point |
|---|---|
| Overworld | in the shared input helper, after that helper's world-tick call and before the prompt newline and the key read |
| Town | the same helper at the same position, but only on its full-prompt arm; the quick-poll arm does not test the request at all |
| Dungeon | the first thing the render-and-poll step does, before the newline and the input poll |
| Combat | at the top of a human-controlled actor's command prompt, so combat drains once per acting character rather than once per round |

What an implementation must reproduce:

1. **A deferred change becomes visible one prompt late.** The command's own
   narration prints first, against the stale panel; the repaint lands as the
   *next* command prompt comes up.
2. **Combat drains on the acting character's first keystroke only.** A refused
   command, or one that needs a further keystroke, re-enters the prompt below
   the test-and-clear, so a request raised by that command waits for a later
   drain point — a later actor, a later round, or another mode's prompt.
3. **Town consumes but never raises.** Town mode's own files raise no request;
   every request it drains was raised by a shared or overlay routine.
4. **The request survives a change of scene.** Nothing else in the program
   clears it — not scene entry, not scene exit, not save, not load — so a
   request raised in one mode is still pending when a different mode's command
   prompt comes up, and is drained there. Scene entry repaints inline without
   clearing the request, so a request left pending across a scene change costs
   one extra, redundant repaint at the following prompt.

### 2.4 Held pages, state that is never refreshed, and the day rollover

**A held page never suppresses a refresh.** No key wait anywhere in the game
gates a panel refresh. Where a held reaction page appears to freeze the panel,
the cause is the order of that routine's own work:

- **Blackthorn's punishment** prints its reaction page, runs its two-phase
  blade animation, and only then erases the victim's on-screen actor, lifts the
  roster record and decrements the party count — with the full-panel repaint as
  the very next step. The acknowledgement wait comes after that repaint and
  gates nothing. So the panel legitimately lists the whole party for the whole
  narration-and-animation hold, and on the wrong-answer branch the victim leaves
  the panel **between** the pendulum-narration page and the page that names
  them, which is the page that waits for the key. `systems/blackthorn.md`
  Section 5.
- **The shrine offering** repaints inline immediately after the gold debit and
  before the announcement page is printed, and raises no request at all; its key
  waits are all earlier. `systems/karma.md` Section 7.

The observable that separates this model from a "suppressed until
acknowledgement" model is **which page the change lands on**, not whether a key
was pressed. Deferring the durable gameplay change to the acknowledgement
reproduces neither case, and moves a roster edit for a presentation reason.

**Some changes are simply never refreshed.** The wishing-well handler neither
repaints nor raises the request on any arm. The coin is spent exactly where
`systems/view.md` Section 3 puts it, and nothing on the way out — the Look
dispatcher, the town loop's epilogue, its post-action cleanup — repaints
either, so the next command prompt finds the request clear and paints nothing.
The debited gold stays invisible until some unrelated event repaints the panel:
any inline repaint, any request raised by a later command and drained at a
prompt, or the day rollover below. Do not move the debit to make it appear.

**The only time-driven refresh is the day rollover.** The shared per-turn clock
repaints the whole panel exactly once per in-game day boundary. A call that
advances no time, one that leaves the minute count short of an hour, and one
that leaves the hour short of a day all bypass the repaint; only when the hour
wraps do the day-in-range, month-roll and year-roll arms converge on it
(`systems/time.md` Section 7). It is a backstop only where and when the clock is
actually called, and every mode loop gates its own call — the overworld and town
loops on a consumed turn, combat on a round cadence — so a party that stops
taking turns never reaches it. Do not model it as a per-turn or wall-clock
repaint. How often the dungeon loop reaches the shared clock is recorded as open
in `OPEN-QUESTIONS.md`; nothing in this section depends on the answer.

## 3. Panel Geometry

The panel lives in the stats text window, cell columns 24 through 39, rows 1
through 9 (`text-output.md` section 10.1). Inside that window it writes a
**fifteen-column** field, absolute columns 24 through 38. Column 39 is never
written by *this* panel content, because the roster and counter boxes drawn by
the game-screen frame are fifteen cells wide: their right rule sits at pixel
`x = 312`, the first pixel of column 39 (`display-driver.md` section 7). That is
a statement about the resting roster, counters and date rows, not about the
window: the item picker borrows the same window and a list row whose label ends
on the window's last writable cell does write column 39
(`inventory.md` Sections 4.4 and 4.5). The earlier unqualified "column 39 is
never written by the panel" is withdrawn (R485).

| Absolute row | Contents |
|---:|---|
| 1..6 | The six party rows (section 4). |
| 7 | The upper divider band, carrying the timed-effect slot (section 8). The text glyph and caps are emitted through the still-active stats window. |
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
| 38 | 1 | Status | The character record's status byte, forwarded verbatim to the ordinary cell emitter. Shipped statuses render as their letter glyphs. |

A worked example: a nine-column name `BAFF` padded with five spaces, a blank
marker cell, `  60` right-justified, and the status letter `G` produce the
fifteen-cell row `BAFF      60G`.

**Correction for imported status bytes.** An earlier revision said every raw
status byte was emitted "as a glyph". The byte is actually handed to the shared
cell emitter. Shipped Good, Poisoned, Sleeping, and Dead letters are ordinary
glyphs, but an edited or legacy save containing one of the emitter's control
bytes receives the corresponding presentation behavior from
`systems/text-output.md` Section 5, such as a style change or window clear.
This still does not mutate a character, party, vehicle, or combat field.

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

Absolute row 7, in the upper divider band, written through the stats text
window:

| Absolute column | Content |
|---:|---|
| 30 | Right-pointing bracket end-cap |
| 31 | The effect glyph |
| 32 | Left-pointing bracket end-cap |

**Correction.** An earlier revision said the slot was written through the
full-screen window. It is not. The refresh keeps the stats window selected,
positions that window's cursor at local cell `(6, 6)`, emits the cap/glyph/cap
sequence there, and only afterward selects the message window. With the stats
window origin this still lands at absolute columns 30..32, row 7, but the saved
cursor and style state belong to the stats descriptor.

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
- the total-party-defeat rescue cinematic's restoration step, once per restored
  member (`systems/blackthorn.md` Section 7);
- inventory/resource changes that affect food, gold, light, or transport
  display.

The panel does not decide whether those state changes are legal. It only reads
the resulting state and paints it.

Whether a given trigger repaints immediately or only files a deferred request
is a property of the calling routine, not of the trigger class. Section 2.2
gives the rule and the worked cases; Section 2.3 gives the four places a
deferred request is consumed.

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
- Apart from clearing a selected Dead or Sleeping member, treat refresh-time
  reads as non-destructive. Leave the message cursor intact and return with the
  message window selected.

## 12. Boundaries And Owned Work

The refresh cadence of Sections 2.2 to 2.4 leaves three soft edges, all indexed
in `OPEN-QUESTIONS.md`: how often the dungeon loop reaches the shared clock, and
therefore how often the day-rollover backstop can fire there; whether the extra
repaint a request pending across a scene change causes is observable, which was
reasoned from the census rather than measured; and the weaker form of the
"no other route to the refresh" negative for the display-driver images, which
were searched for the relevant references rather than read through. Remaining
transport-marker, combat-descriptor, and text-rendering questions live in
`systems/vehicles.md`, `systems/combat.md`, and `systems/text-output.md`.

## 13. Sources

This is a cleanroom behavioral rewrite from private resident UI notes. It does
not reproduce private source, decompiler output, assembly excerpts, raw dumps,
private address tables, or implementation listings.

- Full-panel refresh, per-row rendering, combat row overlays, and the middle
  value block: the resident user-interface function notes under
  `../u5-decomp/functions/ULTIMA_EXE/`.
- Cadence of the poison, ring-regeneration, and camp-recovery refresh triggers
  in Section 10: private analysis under `../u5-decomp/notes/`.
- Source provenance: the fifteen-column field, the exact column bindings of
  every party-row and counters-row field, the leading-space mechanisms behind the
  gold and date alignment, the persistence of the active-player marker, the
  timed-effect slot's cells, driving byte, code table and font, the plain-band
  repaint, the panel label strip, and the exhaustive refresh side-effect census
  are derived from private analysis under `../u5-decomp/notes/`, cross-checked
  against a fresh local re-read of the shipped executable and shared data
  overlay. Two claims in earlier revisions of this document are withdrawn there:
  that the effect glyph goes through the miniature tile-glyph path, and that its
  brackets sit above and below it.
- The exact condition behind the combat `C` status override (party-side set,
  monster-side clear, dead clear, controlled/charmed bit set, descriptor owner
  field matching the drawn row) and the withdrawal of the earlier "casting and
  self-targeted" reading:
  private analysis under `../u5-decomp/notes/`.
- The refresh cadence of Sections 2.2 to 2.4 - the two mechanisms and the split
  between them, the eighty painting sites and twenty-three request sites, the
  boolean nature and initial value of the request, the four consumers and their
  exact positions in each mode's command prompt, the combat first-keystroke and
  town quick-poll narrowings, the survival of a request across a scene change,
  the Blackthorn and shrine orderings, the wishing well's total absence of both
  mechanisms, and the day-rollover backstop with its three bypasses - is derived
  from private analysis under `../u5-decomp/notes/`, combining an exhaustive
  positional census of the shipped program with execution of the original code
  over thirty cases covering both polarities of all four consumers, both
  punishment arms, the shrine offering, the well on five arms, the toll on three
  arms, and six clock arms. Issue #267.
- Text-window primitives used by the panel: `systems/text-output.md`.
- Saved calendar, food, gold, transport/action, and character-record fields:
  `formats/saved-gam.md`.
