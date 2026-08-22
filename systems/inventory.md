# Inventory And Equipment

## 1. Scope

This document specifies the shared inventory model, Z-stats inventory browsing,
and the R-Ready equipment flow. It complements `catalogs/item-list.md`, which
names item families, and `formats/saved-gam.md`, which owns the persisted byte
layout.

The important compatibility rule is that carried equipment stock and currently
readied equipment are separate stores. Carried stock is a shared party counter
band keyed by equipment item id. Readied equipment is six bytes inside each
character record. Moving an item between those stores is the job of R-Ready and
related helper paths; the stock bytes are inventory quantities, not spell or
combat effect timers.

## 2. Shared Inventory Stores

The party inventory consists of several counter families:

- Food and gold are word-sized shared counters.
- Keys, gems, torches, the Grapple/legacy-magic-powder byte, special items,
  equipment, spell charges, scroll/potion/use-items, and reagents are byte-sized
  counters or flags.
- The equipment stock band is forty-eight entries. Item id `N` addresses the
  carried stock for equipment row `N`; arms shops, Z-stats inventory pages, and
  R-Ready all use that same id space.
- The spell-charge band is also forty-eight entries, but it is a separate
  spell-stock store. C-Cast and M-Mix own that band.

A zero byte in a carried-counter band means the party owns none of that item.
Nonzero values are quantities, unless the consuming system documents that a
particular item behaves as a present/absent flag.

Shared counter mutation uses the common capped-add / floor-subtract family
described in `stat-arithmetic.md` when callers route through that resident
helper family. Storage width is not the gameplay cap. Known caps should be
specified by the owning system: examples include gold's normal `9999` cap,
spell charges and R-Ready equipment stock at `99`, and the inn
stay/month counter at `25`. Do not infer a global `255` cap merely because a
field is stored in one byte.

## 2.1 Equipment Burden And Weight

R-Ready has a real strength gate. Before an item is written into a readied
slot, the command sums the selected character's current readied-equipment
burden, adds the candidate item's R-Ready burden, and compares the result to
that character's Strength byte. If the total is greater than Strength, R-Ready
prints the "not strong enough" refusal and makes no inventory or equipment
change.

The R-Ready burden values are item metadata and are listed in
`catalogs/item-list.md`. Empty equipment slots contribute zero. The check is a
total-readied-burden check: a legal slot family can still refuse if the member
is not strong enough to carry the resulting readied set.

The resident engine also has a separate helper that was intended to compute a
per-item defence contribution from the six readied slot bytes, using a
different lookup table from the R-Ready burden gate. That lookup is item-id
keyed and is listed in `catalogs/item-list.md`. As designed, the helper would
treat empty equipment slots as zero and add a small bonus while the shared
timed-effect code is Protection. As shipped, it produces nothing: each per-slot
accumulation is guarded by a comparison that is always true and therefore
always skipped, and the helper's result is never consumed by any reachable
caller — one call site discards it, and the other is reached only through an
attribute-selector arm that nothing in the game ever selects. Do not add
non-R-Ready encumbrance, readiness enforcement, or combat-defense
recalculation from this helper. See `systems/combat.md` and `systems/magic.md`.

## 3. Character Equipment Slots

Each character record has a six-byte readied-equipment block. The live engine
uses `0xFF` as the empty-slot sentinel; all other values are equipment item ids
that refer back to the shared equipment id space.

| Record offset | Slot |
|---:|---|
| `+0x19` | Helm / head slot |
| `+0x1A` | Body armour slot |
| `+0x1B` | Weapon hand |
| `+0x1C` | Shield / off hand |
| `+0x1D` | Ring slot |
| `+0x1E` | Amulet / neck slot |

The ownership test used by inventory browsing is simple: scan these six bytes
for a matching item id. If any slot matches, that character is already wearing
or wielding that item.

### 3.1 Equipment Class Tags

Every equipment item id also has a compact class tag used by R-Ready. These
tags are item metadata, not display families: several visible families share a
hand-equipment tag, and ammunition rows have no readied-equipment tag.

| Class tag | Public meaning | R-Ready consequence |
|---:|---|---|
| `0x80` | Helm / head equipment | Uses the helm slot and refuses if another helm is already readied. |
| `0x40` | Body armour | Uses the body-armour slot and participates in the combat armour lock. |
| `0x20` | One-hand hand equipment | Covers shields and one-handed weapons. The hand branch resolves whether the weapon hand or off hand can accept the item. |
| `0x30` | Two-hand hand equipment | Requires both hands to be free when selected; a currently readied item with this tag blocks shield/off-hand readiness. |
| `0x02` | Ring equipment | Uses the ring slot. Ring of Invisibility and Ring of Regeneration also have random vanish checks after a successful ready action; Ring of Regeneration is also read by the non-combat regeneration check in the shared party status pass, which runs once per turn-consuming action rather than hourly. |
| `0x04` | Amulet / neck equipment | Uses the amulet/neck slot. |
| `0x00` | Ammunition stock | Not an ordinary readied-equipment class; used as carried ammunition for compatible weapons. |

The class tag determines the slot family and hand-occupancy branch. It does not
decide whether the character is strong enough for the resulting equipment set;
that is the separate burden-versus-Strength check.

## 4. Z-Stats Inventory Browsing

Z-stats has two roles:

1. It displays per-character stats and readied equipment.
2. It browses inventory pages over shared counter bands.

The first two pages are character-specific: page 1 is the primary stat page and
page 2 is the equipment page. Later inventory pages walk shared counter bands
for reagents, spell charges, special/use items, and the weapons/armour stash.
The inventory list renderer skips zero-count entries unless the caller provides
a character slot and that character already has the item in the six-slot
equipment block. R-Ready uses that form so the picker can show both carried
items that can be equipped and currently readied items that can be unequipped.

Inventory rows render from a caller-selected name table. Some name strings use
a leading marker to request a special row layout, such as a one-shot quest-item
indicator or an alternate numeric prefix. These are display conventions only;
the counter band remains the source of ownership.

The command starts by choosing a character. In combat scenes, Z-stats and
R-Ready bind to the currently active living combat actor when that actor maps
to a party slot; outside combat they use the normal party-member selector.
Escape cancels the selector, while the explicit none/retry result only redraws
the prompt path and does not select a character.

The Z-stats page loop preserves a single page index. Space or Escape exits and
restores the HUD. Direction-style navigation moves backward or forward through
the visible page sequence; number keys `1..6` jump to the corresponding active
party slot while preserving whether the current character page is the stats
page or the equipment page. Jumps beyond the active party size are rejected.

### 4.1 The panel's cell rectangle

The display is a forty-column by twenty-five-row grid of eight-by-eight-pixel
character cells, and the engine maintains four independent text windows over it
(`text-output.md` sections 2 to 4). Three of the four carry the standing layout:

| Window | Cell rectangle (inclusive) | Role |
|---|---|---|
| 0 | `(0,0)` to `(39,24)` | Whole screen: chrome, border bands, viewport labels. |
| 1 | `(24,1)` to `(39,9)` | The **roster / stats panel**. |
| 2 | `(24,11)` to `(39,23)` | The **message window**. |

The panel is therefore **sixteen columns by nine rows**. Earlier revisions of
this section guessed columns 24 through 38 and rows 1 through 6; both figures
are corrected. Columns 24 through 38 - **fifteen cells** - is the *content*
width that the roster rows and the picker frame use; column 39 is reached only
by the stats page, which re-widens the window's right edge to 39 before drawing.
Rows 1 through 9 - **nine rows** - is the full height, because the food/gold
line and the date line live below the six member rows.

Every surface in this section draws inside window 1 unless it is explicitly
described as going to the message window.

### 4.2 The resting roster layout

A full panel refresh paints, in order, six member rows on panel rows 1 through
6, then the food-and-gold line on panel row 8, then the date line on panel
row 9. In window-relative terms those are window rows 0 through 5, 7 and 8.

Each member row is exactly **fifteen cells** wide:

| Window cells | Screen columns | Content |
|---|---|---|
| 0 to 8 | 24 to 32 | Member name, printed then space-padded to a width of nine. |
| 9 | 33 | Marker column: a right-pointing arrow glyph when this row is the one the active-player selector names *and* the member's status letter is neither the dead letter nor the sleeping letter; a space otherwise. |
| 10 to 13 | 34 to 37 | Current hit points, right-aligned in a four-cell field padded with spaces. |
| 14 | 38 | One-letter status code. |

Rows past the end of the travelling party are blanked with exactly **fifteen
spaces**, which is what fixes the content width at fifteen.

In a combat scene the acting combatant's row is preceded by the text system's
**inverse-video control byte**, not by an extra glyph. Control bytes do not
render pixels and do not advance the cursor, so the row stays fifteen cells
wide and is simply drawn inverted. See `stats-panel.md` section 4.

The class letter and the status letter are each one character selected by index
from a fixed alphabet. Publish both in order: the class alphabet is
`A M B F D T P R S` and the status alphabet is `G P D S C`. Both are looked up
by scanning the alphabet for the record byte's position, so an out-of-range
byte yields no letter rather than a wrong one.

The food-and-gold line and the date line use these literals (underscore is a
literal space, `\n` a newline):

| Literal | Use |
|---|---|
| `F:` | Food label; the count follows immediately, then spaces out to window column 8. |
| `_G:` | Gold label, with a **leading** space. |
| `Ship:` | Replaces the gold label while the party is aboard a vessel; the hull condition follows. |
| `\n___` | Newline plus three spaces - the date line's own indent. |
| `Starving!\n` | The out-of-food warning. |

The date is printed as month, a hyphen, day, a hyphen, then the year in a
three-digit zero-padded field.

### 4.3 Member selection: the framed label and the inverted row

Every command that needs a party member - Z-stats, R-Ready, New Order, and the
rest - shares one selection surface. Its contract is:

- The message window shows the `Player:_` prompt (`commands.md` section 5.6).
- The panel's **top border band** carries the framed label `Select:`. The
  stored literal is the bare word with its colon; the brackets a reader sees are
  the two end-cap glyphs the label writer draws around it (`text-output.md`
  section 10.7).
- The currently indicated member is shown by **inverting a rectangle covering
  the full fifteen content cells of that row** - an exact-width video inversion
  of screen columns 24 through 38 across the whole of that text row. It is not
  a cursor character and it does not extend to column 39.
- Moving the indicator inverts the old row back and inverts the new one, so the
  inversion is its own undo.
- Number keys `1` through `6` select directly, bounded by the current party
  size; the four direction keys move the indicator.

**Nothing in the panel is cleared during member selection.** The six roster
rows, the food-and-gold line and the date line all stay on screen; only the
border label changes and one row inverts. The message window is untouched apart
from the prompt itself. Cancelling prints the universal cancel word into the
message window.

### 4.4 The item picker frame

The item picker is a different contract from member selection, because it
**does** clear the panel.

The frame builder takes a row count. It first narrows window 1 to
`(24,1)-(38,count+1)` and clears it, then re-widens the window to
`(24,1)-(39,9)` and draws an ornamental border out of seven text-font frame
glyphs: a top-left ornament, thirteen top-edge glyphs, a top-right ornament;
then, on each interior row, a vertical rule in window column 0 and another in
window column 14; then a newline, a bottom-left ornament, thirteen bottom-edge
glyphs, and a bottom-right ornament. The top edge is a single rule and the
bottom edge is a double rule; the four corners are curved ornaments.

The `U`-Use path calls it with a row count of **eight**, which yields the
picker every caller in the game uses:

| Property | Value |
|---|---|
| Frame width | 15 cells, screen columns 24 to 38 |
| Frame height | 9 rows, screen text rows 1 to 9 |
| Vertical rules | window columns 0 and 14 (screen columns 24 and 38) |
| Interior item rows | 7 (window rows 1 to 7, screen rows 2 to 8) |
| Interior content columns | 13 (window columns 1 to 13, screen columns 25 to 37) |

Because the clear covers the whole panel, **the food-and-gold line and the date
line are erased for the duration of the picker**, and both are restored by a
full roster redraw when the picker closes. The message window and the map
viewport are genuinely untouched.

The `U`-Use flow is the reference sequence: refuse with `No_usable_items!\n`
if nothing is usable; print `Item:_` into the message window; select the panel;
write the framed border label `Items:`; draw the eight-row frame; run the
picker; restore the message-window frame; redraw the full roster.

### 4.5 Picker row format

A picker row is **`[two-cell quantity][one-cell selector][name]`**, i.e. window
columns 1 and 2 hold the quantity right-aligned, window column 3 holds the
selector character, and window columns 4 through 13 hold the name.

| Quantity case | Rendered |
|---|---|
| Zero | The two-character literal `--` |
| One to ninety-nine | The number, right-aligned in two cells, space-padded |
| "No quantity" marker | Neither the quantity nor the selector cell is emitted; the row prints only its name |

Selector characters below the printable range are drawn from the **runic** font
rather than the text font; the renderer switches fonts for that one cell and
switches back.

Name strings may carry a leading sentinel that requests a decorated row:

| Sentinel | Rendered |
|---|---|
| quest-item marker | A runic symbol glyph, a space, a plus sign and a space, then the rest of the name in the text font |
| counted-special marker | A second runic symbol glyph with the same spaced plus sign, then a count word |
| moonstone marker | The word `Moonstone_`, then a single runic letter naming the stone |
| none | The name verbatim |

The sentinel is a display convention in the name table; it does not change the
counter band or the item id.

### 4.6 Border labels

A border label is not a printed heading inside the panel. It is written by a
shared label routine whose contract is:

- Centre the text on the panel's top border band.
- Blank the band either side of the text.
- Redraw the horizontal rule beneath the band.
- Bracket the text with the right-pointing end-cap glyph on the left and the
  left-pointing end-cap glyph on the right.

The stored literals are the bare words with their punctuation - `Select:`,
`Items:`, `Reagents`, `Spells`, `Armaments` - and the two triangles are chrome,
not characters. When neither a picker nor a member selection is active, the
panel's top border carries no label.

Note that this writer is a **different** slot from the two border bands around
the dungeon viewport: it centres on a different column and blanks a different
pixel span. See `dungeon-mode.md` section 4.1 and `text-output.md` section 10.7.

### 4.7 Pages, field labels and placeholders

There are **six** pages in all: the attribute page, the equipment page, and four
inventory pages.

| Page | Border label | Slots |
|---|---|---:|
| Attributes | none | - |
| Equipment | none | 6 |
| Armaments | `Armaments` | 48 |
| Spells | `Spells` | 48 |
| Reagents | `Reagents` | 8 |
| Items | `Items` | 38 |

Leaving the pages prints `Done\n` in the message window. Long pages **do not
paginate**: the navigator scans forward or backward for the next slot with a
non-zero count, so empty slots are skipped rather than shown as blank rows.

The attribute page clears the panel, re-widens the window's right edge to column
39, centres the member's name by emitting leading spaces, emits the record's
leading glyph, and then appends value after value. Its layout is
**label-driven, not column-driven**: each label carries its own line breaks and
its own interior spacing, and each value is printed immediately after its label
at whatever cursor column the label left behind.

| Literal | Field |
|---|---|
| `_Lv-` | Level |
| `Str=` | Strength |
| `__HP:` | Hit points |
| `\nInt=` | Intelligence |
| `__HM:` | Magic points |
| `\nDex=` | Dexterity |
| `__Ex:` | Experience |
| `\n\n____Magic:` | Magic heading |
| `Arms\n\n` | Arms heading |
| `Equipment` | Equipment heading |
| `\n_Food:_` | Food |
| `\n_Gold:_` | Gold |
| `\n\n_Keys.......` | Keys, dotted leader |
| `\n_Gems.......` | Gems, dotted leader |
| `\n_Torches....` | Torches, dotted leader |
| `\n_Grapple` | Grapple |
| `\nStatus:_` | Status |

`Str=`, `Int=` and `Dex=` form the left column, and `__HP:`, `__HM:` and
`__Ex:` sit on the same three rows to their right. The dotted leaders are
**literal runs of periods inside the label strings** - seven for keys and gems,
four for torches - which is why the three counts land in the same column with
no padding logic anywhere. All three labels are twelve characters long after
their newline, so the counts align at the thirteenth cell of the line.

Empty-state placeholders, both parenthesised:

| Literal | Used when |
|---|---|
| `(None ready)` | The equipment list has nothing readied. |
| `(None owned!)` | An inventory page has no slot with a non-zero count. |

The empty equipment value in the six-slot block is the all-bits-set byte; if all
six slots are empty the page prints the `(None ready)` placeholder rather than a
blank list.

The party-wide inventory pages use the same eight-row frame and row renderer as
the R-Ready picker. The row scanner walks a caller-supplied counter band forward
or backward from a mutable cursor, skipping zero-count rows for ordinary
inventory browsing. When a character slot is supplied for R-Ready, a row is also
displayable if that character already has the item readied, which lets the
picker offer unequip rows even when the carried counter is zero. When no
displayable row exists, the panel prints the none placeholder and waits for a
key before returning to the page loop.

Source provenance: derived from private analysis note
`../u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.

## 5. R-Ready Flow

R-Ready is the equipment selection command; no separate inventory command owns
these readied-equipment writes.

1. The player selects a party member with the same party-member selection
   surface used by Z-stats.
2. The command scans the forty-eight-entry equipment stock band for the first
   displayable item: either a nonzero carried counter or an item the selected
   member is already wearing or wielding. If none exists, it prints the normal
   "nothing to ready" refusal and exits.
3. Otherwise it opens an eight-row picker over the equipment stock band.
4. Up/down movement scrolls to the previous or next displayable equipment id.
   The four corner keys — Home, End, PgUp and PgDn, or the numpad corners, which
   the input layer delivers as the four diagonal codes — page the list by a full
   eight-row window. This and the shop list navigator are the only places
   outside combat's targeting cursor that consume those codes at all. Enter
   confirms the current row. Escape exits and restores the HUD.
5. After a successful or refused selection, the picker remains open until the
   player exits, so several items can be attempted in one R-Ready invocation.

The picker is shared infrastructure. In R-Ready mode it walks the equipment
stock band; another caller can reuse the same picker against a different item
band and name table.

**Turn cost.** R-Ready costs a turn in every mode, and a refusal costs exactly
what a success costs — there is no free retry. The equipment overlay reports no
status of its own: the cascade returns the same value for every refusal and for
every successful equip, the picker consumes that value only as a "close the
panel" signal, and the command layer discards it. Outside combat the dispatcher
reports its default "acted" status for `R` whatever the overlay did, so the
mode loop runs its per-turn epilogue and the clock advances even if the player
opens the panel and immediately backs out. In combat, `R` runs through the
labelled prompt with the live-actor gate, so it ends the acting combatant's
action; only a dead actor escapes the cost, with a short refusal and a free
re-prompt. Because the panel stays open until the player exits, the cost is per
invocation of the command, not per item readied: several items can be equipped,
unequipped or refused within one turn.

### 5.1 R-Ready presentation

R-Ready reuses both surfaces specified in Section 4 without modification. Its
member selection is the shared surface of Section 4.3: the framed `Select:`
label on the panel's top border, the `Player:_` prompt in the message window,
and the fifteen-cell inverse-video row. Its item list is the eight-row frame of
Section 4.4 with the row format of Section 4.5.

The literals R-Ready owns for itself are:

| Literal | Meaning |
|---|---|
| `Item:_` | The item prompt, in the message window. Colon then one trailing space. |
| `Thou_art_empty-\nhanded!\n` | Nothing to ready. The embedded newline is part of the literal, so the word "handed" always starts a new line. |
| `None!\n` | The picker was cancelled. |
| `Done\n` | The picker was closed after use. |

Closing the picker restores the message-window frame and then triggers a full
roster redraw, which is what puts the six member rows, the food-and-gold line
and the date line back on the panel.

## 6. R-Ready Eligibility And Writes

After an item is selected, R-Ready classifies it by the item's equipment-class
metadata and applies these gates before writing a slot:

- **Already readied by this character.** If the chosen item id is already in
  any of the selected character's six equipment slots, R-Ready unequips it
  instead of trying to equip another copy. It clears the first matching
  readied slot, then returns one copy to the shared equipment counter if that
  counter is below `99`. Unequipping the Ring of Invisibility in
  combat also clears the combat-side hidden/suppressed bookkeeping owned by
  the resident removal helper.
- **Ammunition and ranged-weapon readiness.** Arrows and quarrels are carried
  ammunition stocks, not readied equipment; selecting either row exits the
  cascade at the very top, with no mutation and **no message at all** — the
  refusal is silent, which is unique among the cascade's exits. Bow and Magic
  Bow readiness requires at least one
  arrow in the shared equipment counter band. Crossbow readiness requires at
  least one quarrel. Missing ammunition prints the ammunition refusal and
  leaves equipment and counters unchanged.
- **Strength refusal.** The candidate item's R-Ready burden is added to the
  selected character's current readied burden. If the result exceeds the
  character's Strength, the command prints the strength refusal and does not
  change inventory. Display category alone is not enough to decide whether a
  character can ready an item.
- **Combat armour lock.** Combat `R` routes through the same R-Ready entry
  point and cascade as non-combat `R`, after binding the selection to the
  active living combat actor. Exactly one combat-scene refusal exists, and it
  is narrow: the selected item belongs to the body-armour class, the scene is a
  combat arena, **and** the battle has not yet been decided. All three must hold.
  Helm, weapon, shield, ring and amulet swaps are therefore permitted during a
  fight; only the body-armour family is locked, and the lock lifts as soon as
  the outcome has been announced, even though the party is still standing in the
  arena. Nothing else about the cascade is scene-dependent — its other
  combat-scene tests are bookkeeping for the Ring of Invisibility's sprite
  handling, not restrictions.
- **Occupied-slot refusal.** Helm, body armour, ring, and amulet classes require
  their corresponding slot to be empty before a different item can be readied.
- **Hand occupancy.** Weapon and shield classes share the weapon-hand/off-hand
  pair. A two-handed item requires both hand slots to be empty. A shield cannot
  be readied while the weapon hand holds a two-handed item. If both hands are
  occupied, hand equipment refuses.
- **Magic-ring vanish check.** Ring of Invisibility and Ring of Regeneration
  are accepted through the ordinary ring-slot path. After the usual
  slot/conflict gates accept the selection, the command writes the ring slot
  and decrements the shared carried counter, then rolls an inclusive `0..15`
  random value. On zero, it prints vanish feedback, clears the ring slot back
  to empty, plays the short vanish sound, and returns a consumed-action result
  to its caller. On any nonzero result, the ring remains readied.

When an ordinary equip succeeds, the chosen item id is written into the target
equipment slot and the shared equipment counter for that item id is decremented.
R-Ready does not atomically replace a different item in an occupied slot. A
different helm, body armour, ring, amulet, or blocked hand item refuses until
the current item is explicitly unequipped through its own R-Ready row. The
mutation order is therefore mass-conserving and simple: unequip returns stock
after clearing a matching slot; equip consumes stock after writing the accepted
slot.

## 7. U-Use Item Flow

U-Use is the item-activation command in every mode. Surface, town, keep, castle,
and dungeon-exploration modes route `U` to the item-use handler, and so does
combat: the combat parser prints the verb label, checks that the acting
combatant is still alive, and then enters the same handler. An earlier revision
of this section said combat `U` was label-only and aborted before reaching the
handler; that is withdrawn. What differs in combat is not the routing but the
per-family gates — several item families test the scene and refuse in an arena,
as the family table below and `catalogs/item-list.md` record.

The item-use handler opens an item picker over usable carried stock. If the
party has no usable item, it prints the no-usable-items refusal and exits. A
selected row dispatches by the handler's use-item enumeration rather than by
the forty-eight-entry equipment id space.

Confirmed U-Use families:

| Family | Behaviour |
|---|---|
| Spell scrolls | Eight scroll counters dispatch to spell-like effects: light, wind change, Protection, Negate Magic, View, Summon Daemon, Resurrection, and Negate Time. A scroll counter is decremented before its branch-specific scene gate, target prompt, or helper return. Scrolls share the spell-code labels but have item-specific constants: `LV` sets the magic-light counter to 240 minutes, while `IS`, `AI`, and `AT` write the single shared timed-effect slot in `systems/magic.md` with `P`/100, `N`/20, and `T`/20 turns respectively — replacing whatever effect was already there. `AT` reports no effect in Stonegate and Doom. |
| Potions | Eight colour-coded potion counters dispatch through a party-member target path. Display order is Blue, Yellow, Red, Green, Orange, Purple, Black, White, with normal effects wake, heal, cure poison, poison, sleep, combat-only "Poof" presentation, combat invisibility, and a surface/town visibility-sweep animation. A consumed potion normally applies the selected colour's effect, but a variation roll gives one chance in sixteen to force the Orange sleep effect and one chance in sixteen to replace the effect with a random potion row. |
| Magic Carpet | Usable outside dungeon/combat scenes when the party is on foot and the current tile accepts carpet boarding. On success it changes the party transport marker to a carpet state and decrements the carried carpet counter. If the party is aboard a ship or otherwise not on foot, it prints the matching refusal instead. |
| Skull Key | Decrements the skull-key/special-key counter, then runs the adjacent-lock helper in non-combat scenes that support it. Dungeon exploration refuses through this path. This is separate from `J` Jimmy's ordinary key use. |
| Regalia | The Amulet of Lord British, the Crown of Lord British, and the Black Badge all behave identically, and all three occupy the single shared timed-effect slot specified in `systems/magic.md` with the permanent duration. Using one of them while its own code already occupies the slot prints a short removal acknowledgement and vacates the slot; otherwise the handler prints the wearing message and installs that item's code. Their only difference is presentational: donning the Amulet or the Crown plays a sound cue, donning the Badge does not. Because the slot is shared and holds one effect at a time, donning any of them cancels an active buff spell, and every path that clears the slot — camping, entering an innkeeper menu, the Blackthorn rescue restoration — silently strips the worn aura until the item is used again. The Sceptre of Lord British is not worn through that state; in eligible non-dungeon scenes it scans the party-centered nearby square for the top-down `0x70..0x7F` barrier/field family, rewrites accepted cells to ordinary open ground with redraw/effect presentation, counts dissolved cells, and otherwise reports no effect or the alternate helper result. |
| Shards | The three Shadowlord shard rows dispatch to the Shadowlord-destruction handler with shard index `0..2`; the handler succeeds only at the matching interior destruction position and only when the matching Shadowlord is the active named encounter, as specified in `catalogs/quest-graph.md`. The U-Use dispatch itself does not decrement or clear anything, so a refused attempt keeps the shard. **A successful destruction consumes the shard**: the destruction handler clears that shard's carried flag as part of the same success step that retires the Shadowlord and sets the quest bit. |
| Moonstones | Rows `1..8` record the current valid location into the matching saved Moonstone slot. Burying is accepted only outside dungeon/combat scenes and only on accepted terrain; Search/Get recovery later invalidates the slot. |
| Spyglass | Surface-only utility. It refuses in unsupported scenes and when the sky-state check says there are no stars; the successful path prints the looking message and enters the same LOOKOBJ sky renderer specified in `systems/view.md` section 4.2. |
| HMS Cape plans | Shipboard-only utility. When used aboard ship, it marks the ship-rigging flag so the ship is rigged for double speed; otherwise it refuses. `weather.md` owns the resulting hoisted-sail wait-pass timing change. |
| Sextant | Outdoor night-only utility. It refuses outside the overworld or during the daytime interval, and otherwise prints the party position. |
| Pocket Watch | Prints the current hour as a twelve-hour AM/PM time. |
| Sandalwood Box | The direct U-Use path asks how to use the box and does not perform the endgame handoff. The successful quest handoff is owned by the terminal endgame overlay path, which reads the saved box flag during its Lord British confirmation sequence. |

## 8. Implementation Contract

For a compatible recreation:

- Keep carried equipment counters separate from readied-equipment slots.
- Treat `0xFF` as the empty value in readied-equipment slots.
- Use equipment item ids consistently across shop stock, shop prices, carried
  counters, display names, and readied slots.
- Display R-Ready candidates when either the carried counter is nonzero or the
  selected character already has that item readied.
- Apply strength, combat-armour, occupied-slot, and hand-occupancy gates before
  mutating counters. Restrict the combat gate to the body-armour family and to
  an undecided battle; do not block other slot families during a fight.
- Charge one turn per R-Ready invocation regardless of outcome, and keep the
  picker open across repeated attempts within that turn.
- Refuse ammunition rows silently, with no message.
- Treat arrows and quarrels as carried ammunition stocks rather than readied
  slots, and apply the traced bow/crossbow ammunition prerequisites.
- Use the R-Ready burden table for the strength check; do not use the separate
  equipped-item weight-statistic table for readiness, and do not infer
  readiness from the displayed item family alone.
- Decrement carried stock only after the equip is accepted.
- Unequipping a readied item clears the matching slot and returns one carried
  copy up to the R-Ready equipment stock cap of `99`; do not drop it on the map
  or delete it.
- Use saturating add/subtract semantics for shared byte and word counters rather
  than native wrapping arithmetic; upper bounds are caller- or field-specific,
  not implied by storage width.

## 9. Inventory Boundaries

The R-Ready and stock-counter contract is complete at inventory-system depth:
equipment ids, slot ownership, picker visibility, class tags, strength gates,
combat routing, ammunition prerequisites, carried-counter mutation, unequip
returns, and magic-ring equip-time checks are public. The U-Use command family
is also complete at dispatch-family depth: scrolls, potions, Moonstones,
regalia, shards, magic carpet, skull keys, Spyglass, HMS Cape plans, Sextant,
Pocket Watch, Black Badge, and Box have public item-activation contracts.
No ZSTATS-owned page-routing or R-Ready storage gap remains at this layer;
object pickup visuals, combat-side equipment consumers, dialogue reactions, and
opaque save/runtime bytes are delegated to their own specs. The scope of the
combat restriction, the silent ammunition exit, and R-Ready's turn cost are all
settled; the one residual inside the cascade is the resident helper behind the
magic-ring vanish roll, whose internals are read only from its call shape.

- **Magic ring and Amulet/Turning boundary.** Ring of Invisibility and Ring of
  Regeneration both have confirmed equip-time and combat-time checks. The two
  rings differ outside combat. Ring of Regeneration is read by the shared party
  status/provision pass specified in `systems/time.md`: each time that pass
  runs, every non-Dead wearer gets a 1-in-8 chance of exactly 1 hit point,
  capped at maximum hit points. That pass runs once per turn-consuming action in
  world, town, and dungeon modes, not once per hour. For Ring of Invisibility,
  no non-combat periodic timer or effect-state writer is traced outside the
  readied slot; do not invent one for world-mode parity. Amulet/Turning is a
  combat-passive amulet/neck item: its target-side turning branch is documented
  in `systems/combat.md`; no R-Ready activation, U-Use activation, countdown,
  or non-combat timer is traced.
- **U-Use ownership.** Scroll gates, potion colour/effect order,
  broad regalia toggles, the Sceptre's exact top-down barrier/field family,
  Spyglass routing to the LOOKOBJ sky renderer, Sextant coordinate
  formatting, and Pocket Watch hour formatting are documented in
  `catalogs/item-list.md` and `systems/view.md`. Story-item acquisition
  mechanics are owned by Search/Get/container, conversation action-letter,
  fixed hidden-treasure, or cinematic specs; dialogue reactions to carried or
  worn story items are quest-graph branch-validation work rather than shared
  inventory or U-Use activation.

## 10. Sources

This is a cleanroom prose rewrite derived from semantic notes in the updated
ZSTATS overlay analysis: the overlay overview, R-Ready top-level handler,
inventory picker, forward/backward inventory scans, six-slot ownership helper,
two-handed classifier, and equip/unequip cascade. It also cross-checks the
public save-image and item-catalog specs. No decompiled source, assembly
listing, or raw binary dump is reproduced here.

Additional provenance for the equipment-weight note: the resident
`compute_party_member_weight` analysis in
`u5-decomp/functions/ULTIMA_EXE/0x6DA8_compute_party_member_weight.md` and the
inventory trace in `u5-decomp/notes/system-trace_inventory.md`; the discarded
call return is visible in the resident
`u5-decomp/functions/ULTIMA_EXE/0x6E60_remove_inventory_match.md` note.

R-Ready burden and strength-refusal provenance: the ZSTATS equip/unequip
cascade at `u5-decomp/functions/ZSTATS_OVL/0x0C5C_ready_apply_or_unequip.md`,
cross-checked against the clean local resident item metadata table.

Combat R-Ready provenance: the combat command dispatcher and prompt helper at
`u5-decomp/functions/COMBAT_OVL/0x063E_actor_ai_or_command.md` and
`u5-decomp/functions/COMBAT_OVL/0x0544_prompt_with_string.md`, cross-checked
with the ZSTATS active-actor selector at
`u5-decomp/functions/ZSTATS_OVL/0x0000_select_player_for_zstats.md`.

Magic-ring vanish provenance: the same ZSTATS equip/unequip cascade, corrected
with the Buffer-D `prng_range` thunk mapping in
`u5-decomp/notes/engine_idioms.md`, and the resident combat ring consumers in
`u5-decomp/functions/ULTIMA_EXE/0x6936_combat_round_engine.md`,
`u5-decomp/functions/ULTIMA_EXE/0x6794_combatant_set_carrier.md`, and
`u5-decomp/functions/ULTIMA_EXE/0x6E60_remove_inventory_match.md`.

Counter saturation provenance: resident byte/word capped-add and floor-subtract
helper analysis in `u5-decomp/functions/ULTIMA_EXE/0x3EF0_sat_add_byte.md` and
sibling helpers, summarized publicly in `systems/stat-arithmetic.md`.

U-Use provenance: CAST overlay use-item dispatch at
`u5-decomp/functions/CAST_OVL/0x1792_use_item.md`, scroll/potion
subhandlers in the same overlay, the Shadowlord shard handler at
`u5-decomp/functions/CAST_OVL/0x15B4_cast_destroy_shadowlord.md`, and the
Moonstone slot writer at
`u5-decomp/functions/CAST_OVL/0x153C_use_moonstone.md`, cross-checked against
Search/Get Moonstone recovery notes.

Combat-lock scope, silent-ammunition, and turn-cost provenance: the in-combat
restriction applies to the body-armour family only and lifts once the battle's
outcome has been announced; ammunition rows exit the cascade silently; and a
refused R-Ready costs exactly what a successful one costs, in every mode.
Source provenance: derived from private analysis note
`../u5-decomp/notes/oq-closures_2026-08-22_combat-encounter.md`, with
`../u5-decomp/functions/ZSTATS_OVL/0x0C5C_ready_apply_or_unequip.md` and
`../u5-decomp/functions/ZSTATS_OVL/0x1296_ready_main.md`.

Combat U-Use correction provenance: combat routes `U` into the same item-use
handler the world modes use, after the live-actor gate. Source provenance:
derived from private analysis note
`../u5-decomp/notes/oq-closures_2026-08-22_combat-encounter.md` and
`../u5-decomp/functions/COMBAT_OVL/0x0544_prompt_with_string.md`.
