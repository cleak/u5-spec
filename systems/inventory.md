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
a leading marker to request a scroll, potion or moonstone row layout.
These are display conventions only;
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

- The caller supplies the message-window question. Ordinary command callers
  use `Player:_` (`commands.md` Section 5.6); inn Leave instead supplies its
  vendor-attributed Who-will-stay question (`shops.md` Section 8.C).
- The panel's **top border band** carries the framed label `Select:`. The
  stored literal is the bare word with its colon; the brackets a reader sees are
  the two end-cap glyphs the label writer draws around it (`text-output.md`
  section 10.7).
- The currently indicated member is shown by **inverting a rectangle covering
  the full fifteen content cells of that row** - an exact-width video inversion
  of screen columns 24 through 38 across the whole of that text row. It is not
  a cursor character and it does not extend to column 39.
- **A digit moves the indicator; it does not commit.** `1` through `6`, bounded
  by the party size, reposition the inverted row exactly as the direction keys
  do and leave the prompt open. Only Return or Space commits the indicated row,
  Escape cancels, and `0` commits the explicit "no one" answer only in the
  callers that allow it (the active-player prompt); elsewhere `0` is ignored.
  This is one shared routine, so the rule is the same for Z-stats, R-Ready, New
  Order, the fountain, Search and every other caller. *(Clarified 2026-09-06,
  issue #192; the earlier "select directly" wording was read as a commit.)*
- Moving the indicator inverts the old row back and inverts the new one, so the
  inversion is its own undo.
- Number keys `1` through `6` select directly, bounded by the current party
  size; the four direction keys move the indicator.

**Nothing in the panel is cleared during member selection.** The six roster
rows, the food-and-gold line and the date line all stay on screen; only the
border label changes and one row inverts. The message window is untouched apart
from the caller's prompt itself. Cancellation returns to that caller, which
supplies its own response; inn Leave prints `Nobody\n\n`. The earlier
claim that every caller uses `Player:` and a universal cancellation word is
withdrawn (R439).

Fresh inn-Leave and shared-selector traces in
`u5-decomp/functions/SHOPPES3_OVL/` and
`u5-decomp/functions/ULTIMA_EXE/` confirm this separation. Twelve isolated
original-selector cases verify the inn's digit, commit, cancellation and
ignored-key behavior; input delivery and panel drawing are observation
boundaries, not a live keyboard or pixel capture.

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

**Selection and scrolling.** The selected item is drawn with its ordinary
label and padding in inverted glyph pixels. Its text is not replaced by a
row of cursor characters. Selection starts at the first visible item on
interior row one. Moving Down through a long list first moves the highlight
through rows one to four. Further Down steps scroll the list while the
highlight stays on row four. Once the final seven-item window is visible,
the remaining steps move the highlight through rows five to seven. Up uses
the corresponding behavior toward the beginning. When all carried entries
fit in the panel, the list stays fixed and the highlight moves among them.
Movement skips absent entries and stops at the first or last selectable item.

Home selects the first item; End selects the last, showing up to seven items
ending there. Page Up and Page Down move seven selectable items, stopping at
the relevant endpoint. These navigation rules are shared with R-Ready in
Section 5. Enter or Space confirms the selected U-Use row; Escape cancels.

Source provenance: fresh original shared-picker and row-scanner execution in
`u5-decomp/functions/ZSTATS_OVL/` and `u5-decomp/notes/`, issue #246;
glyph inversion independently traced in `u5-decomp/functions/ULTIMA_EXE/`.

### 4.5 Picker row format

A counted picker row is **`[two-cell quantity][one-cell selector][name]`**:
window columns 1 and 2 hold the quantity right-aligned, window column 3
holds the selector, and the name has ten cells in columns 4 through 13.
A no-quantity row instead starts its name in column 1 and has all thirteen
interior cells available. These widths describe the ordinary row layout;
the picker does not derive labels by truncating long item names.

| Quantity case | Rendered |
|---|---|
| Zero | The two-character literal `--` |
| One to ninety-nine | The number, right-aligned in two cells, space-padded |
| "No quantity" marker | Neither the quantity nor the selector cell is emitted; the row prints only its name |

Selector characters below the printable range are drawn from the **runic** font
rather than the text font; the renderer switches fonts for that one cell and
switches back.

Name strings may carry a leading sentinel that requests a decorated row.
The markers describe presentation families, not quest status or ownership:

| Marker | Rendered name portion, after the independent quantity/selector cells |
|---|---|
| Scroll (formerly called quest-item) | Runic-font glyph `0x1C`, space, plus, space, then the scroll's compact rune label in the **runic font**; restore the text font afterward. |
| Potion (formerly called counted-special) | Runic-font glyph `0x1D`, space, plus, space; restore the text font, then print the potion's short colour name. |
| Moonstone | `Moonstone` followed by a space in the text font, then one runic phase glyph. |
| None | The name verbatim in the text font. |

The plus uses glyph code `0x2B` in the selected runic font; neither scroll nor
potion prefix switches to the text font for it. The moonstone phase glyph is
`RUNES.CH` code `0x30` plus the zero-based phase, as on the sky strip.
The earlier potion-without-decoration rule, count-word interpretation of the
potion suffix, and text-font claims for the prefix/scroll label are withdrawn
(R403).

**Which names carry each marker.** This is the complete classification of the
38-entry U-Use/Items name family; ownership and usability still determine which
entries a particular picker shows:

| Items | Marker |
|---|---|
| All eight scrolls: Light, Wind Change, Protection, Negate Magic, View, Summon Daemon, Resurrection, Negate Time | Scroll |
| All eight potions: Blue, Yellow, Red, Green, Orange, Purple, Black, White | Potion |
| All eight Moonstones, phases 0 through 7 | Moonstone |
| Magic Carpet; Skull Keys; Amulet of Lord British; Crown of Lord British; Sceptre of Lord British | None |
| Shard of Falsehood; Shard of Hatred; Shard of Cowardice | None |
| Spyglass; HMS Cape Plans; Sextant; Pocket Watch; Black Badge; Wooden Box | None |

All 48 equipment names, eight reagent names and 48 spell-charge names also
have **no decoration marker**. Thus a spell-charge row and a scroll of a
related spell are different presentation cases. The Sceptre and Skull Keys
are plain-name rows, despite being special items in gameplay. Grapple and the
food/gold/ordinary-key/gem/torch counters do not add entries to this 38-name
U-Use family.

Decoration is decided by the name table independently of the numeric count
and selector. Zero quantity still prints `--`; a marked potion row has its
quantity on the left and its colour after the potion symbol. The selector
cell holds whatever character the caller passes: a space for an unreadied
carried item in R-Ready, a runic glyph for a readied one, and the small solid
diamond (selector code `0x0F`) when marked in M-Mix (`magic.md` Section 6).
The marker changes no item id or counter band.

**Complete U-Use labels.** The family table above identifies the items; its
long names are not literal row labels. The following table gives every
undecorated entry in the 38-entry family. Use these labels verbatim, including
abbreviations and the singular `Plan`.

| Carried item | Plain name in the picker |
|---|---|
| Magic Carpet | `Magic Crpt` |
| Skull Keys | `Skull Keys` |
| Amulet of Lord British | `Amulet` |
| Crown of Lord British | `Crown` |
| Sceptre of Lord British | `Sceptre` |
| Shard of Falsehood | `Shard/Falsehd` |
| Shard of Hatred | `Shard/Hatred` |
| Shard of Cowardice | `Shard/Cowrdce` |
| Spyglass | `Spyglass` |
| HMS Cape Plans | `HMS Cape Plan` |
| Sextant | `Sextant` |
| Pocket Watch | `Pocket Watch` |
| Black Badge | `Black Badge` |
| Wooden Box | `Wooden Box` |

The eight scrolls use the scroll decoration above followed by these compact
rune labels, still in the runic font:

| Scroll | Rune label after the decoration |
|---|---|
| Light | `VL` |
| Wind Change | `RH` |
| Protection | `IS` |
| Negate Magic | `IA` |
| View | `IQW` |
| Summon Daemon | `KXC` |
| Resurrection | `IMC` |
| Negate Time | `AT` |

The eight potions use the potion decoration followed by their text-font
colour names: `Blue`, `Yellow`, `Red`, `Green`, `Orange`, `Purple`, `Black`,
`White`. The eight moonstones use the phase composition below. Together,
these cases specify all 38 labels. The row renderer prints each authored
label and then pads short rows; it does not abbreviate or truncate a longer
name at runtime.

**Which U-Use rows omit quantity.** Quantity suppression is independent of
name decoration. In the picker stock, value 255 is the no-quantity marker;
zero means absent from U-Use, and ordinary positive quantities produce the
counted layout. The shared renderer can print a zero row as `--` when another
caller requests one. A plain-name row means only that it has no scroll,
potion or moonstone decoration; it does not imply a numeric quantity.

For items carried through normal game acquisition or initial party state:

| Items | Quantity presentation |
|---|---|
| Eight scrolls, eight potions, Magic Carpet, Skull Keys | Counted: two quantity cells and a selector space before the name |
| Amulet, Crown, Sceptre | No quantity or selector |
| Eight carried moonstone phases | No quantity or selector |
| Three shards | No quantity or selector |
| Spyglass, HMS Cape Plans, Sextant, Pocket Watch, Black Badge, Wooden Box | No quantity or selector |

Thus the normal full family contains 18 counted entries and 20 uncounted
entries. Only entries actually carried and usable are shown.

The saved value matters. Apart from moonstone and plans conversion, the
picker preserves the carried item's stored value. A saved Amulet, Crown or
Sceptre value of one therefore produces the counted row with one leading
space, `1`, another space, and its short name; normal acquisition gives each
of these the no-quantity value instead. The same distinction applies to the
copied shard and utility values. The plans row becomes uncounted for any
nonzero plans value. A moonstone appears only when its placement state is
carried, and its picker value is then uncounted. See `formats/saved-gam.md`
Section 7 for the saved inventory fields.
The earlier unconditional statement that the Amulet, Crown and Sceptre use
normal quantity cells is withdrawn; that result applies to quantity-one
saved values, not their normal acquisition state (R456).

An uncounted `Shard/Falsehd` or `Shard/Cowrdce` is twelve text cells followed
by one padding space; `Shard/Hatred` is eleven cells followed by two spaces.
`HMS Cape Plan` occupies all thirteen cells. Each begins in the first
interior column. A quantity-one carpet starts with one space, `1`, one
space, and `Magic Crpt`, then one padding space. Short rows are padded to the
thirteen-cell interior and end with a newline.

**Moonstone composition.** A carried moonstone's complete visible content is
the ten text-font cells `Moonstone ` followed by the single runic phase
glyph specified above, then two padding spaces. No number or selector
precedes it. There is no literal opening parenthesis, parenthesised suffix,
or `phase` plus decimal number to clip off at the frame edge. The phase
glyph is part of the row's rendered content; an apparent parenthesis in a
text transcription does not establish a longer hidden label.

Source provenance: fresh original compact-name, inventory snapshot,
acquisition and initial-party-state inspection in
`u5-decomp/functions/ZSTATS_OVL/`, `u5-decomp/functions/SJOG_OVL/`,
`u5-decomp/functions/TALK_OVL/` and `u5-decomp/notes/`, issue #255.
All 38 name mappings, 256 snapshot cases covering every source-byte value,
38 typical carried rows and 152 row cases covering values 0, 1, 99 and 255
were checked. Glyph/font output, numeric output and cursor coordinates were
controlled observation boundaries, not a fresh complete-game pixel capture.
The earlier eight original navigation scenarios for issue #246 still verify
Section 4.4.

**R-Ready's readied selector is item-specific.** If the selected character
has the row's item in any equipment slot, use the following `RUNES.CH` glyph;
otherwise use a space. The glyph does not depend on which hand or slot holds
the item, and is not calculated from its equipment-class tag.

| Item or group | Selector glyph |
|---|---:|
| All four helms | `0x01` |
| All five shields | `0x02` |
| All seven body armours | `0x03` |
| Dagger; Main Gauche | `0x04` |
| Sling | `0x05` |
| Club | `0x06` |
| Flaming Oil | `0x07` |
| Spear | `0x08` |
| Throwing Axe | `0x09` |
| Short Sword; Long Sword | `0x0B` |
| Mace | `0x0C` |
| Morning Star | `0x1E` |
| Bow | `0x0F` |
| Crossbow | `0x10` |
| Two-handed Hammer | `0x11` |
| Two-handed Axe | `0x12` |
| Two-handed Sword | `0x13` |
| Halberd | `0x14` |
| Sword of Chaos; Silver Sword; Glass Sword; Jeweled Sword; Mystic Sword | `0x15` |
| Magic Bow | `0x16` |
| Magic Axe | `0x17` |
| All three magic rings | `0x18` |
| Amulet of Turning | `0x19` |
| Spiked Collar | `0x1A` |
| Ankh | `0x1B` |

The two ammunition entries also have assigned glyph `0x17`, but ordinary
R-Ready cannot put ammunition into a readied slot; their normal selector is
therefore a space. The reported Chain Coif, Chain, Long Sword and Ankh
selectors are examples of this item mapping, not evidence for a slot table.
Source provenance: fresh item-selector and ownership trace under
`u5-decomp/functions/ZSTATS_OVL/` and `u5-decomp/notes/`, issue #225.

Source provenance: fresh name-table census, R-Ready/U-Use table selection and
row-renderer font changes in `u5-decomp/functions/ZSTATS_OVL/`, with font-slot
loading checked in `u5-decomp/functions/INTRO_OVL/` and font selection in
`u5-decomp/functions/ULTIMA_EXE/`. Issue #211; no new emulator capture.

### 4.6 Border labels

A border label is not a printed heading inside the panel. It is written by a
shared label routine whose contract is:

- Centre the text on the panel's top border band.
- Blank the band either side of the text.
- Redraw the horizontal rule beneath the band.
- Bracket the text with the right-pointing end-cap glyph on the left and the
  left-pointing end-cap glyph on the right.

The stored literals are the bare words with their punctuation - `Select:`,
`Items:`, `Reagents`, `Spells`, `Items`, `Armaments`, `Equipment`, and the
M-Mix list's `Reagents:` - and the two triangles are chrome, not characters.
When neither a picker nor a member selection is active, the panel's top border
carries no label. *Corrected 2026-09-06 (R392): this roster previously stopped
at five. `Items:` with the colon is the U-Use picker's label; the Z-stats items
page uses the bare `Items`; `Equipment` is the counters screen's label; and
the M-Mix reagent list uses `Reagents:` with a colon where the Z-stats reagent
page uses the bare `Reagents`. They are distinct stored literals, and sharing
one constant between a pair gets one of the pair wrong.*

Note that this writer is a **different** slot from the two border bands around
the dungeon viewport: it centres on a different column and blanks a different
pixel span. See `dungeon-mode.md` section 4.1 and `text-output.md` section 10.7.

### 4.7 Pages, field labels and placeholders

There are **seven** screens in the cycle, walked in this order by the
direction keys and wrapping from the last back to the first:

| Screen | Border label | Slots |
|---|---|---:|
| Attributes | the member's name | - |
| Arms (readied equipment) | the member's name | 6 |
| Equipment (the counters: food, gold, keys, gems, torches, grapple) | `Equipment` | - |
| Reagents | `Reagents` | 8 |
| Spells | `Spells` | 48 |
| Items | `Items` | 38 |
| Armaments | `Armaments` | 48 |

*Corrected 2026-09-06 (R392, issue #202).* This table previously said six
pages in the order attributes, equipment, armaments, spells, reagents, items,
with the Arms and counters halves on one page. The shipped navigator keeps two
per-member screens - the readied-equipment half headed `Arms` and the counters
half headed `Equipment` - and then walks the four shared inventory pages in
the order reagents, spells, items, armaments; the literals below were already
right, only the page count and order were wrong. The four inventory screens
are drawn inside the Section 4.4 frame with the same page badge. The items
page catalogues **all eight** moonstones by phase glyph whether or not any is
carried, whereas the U-Use picker lists only carried stones; the two surfaces
use different predicates.

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
| `_Lv-` | Level, followed by one space and then the member's **class name** on the same line (see below) |
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

*Added 2026-09-06 (issue #193).* The second line of the attribute page is the
record's gender glyph, the `_Lv-` literal, the level value, a single space,
and the member's class name looked up from the record's class letter through
the nine-entry class table - `Avatar`, `Mage`, `Bard`, `Fighter`, `Druid`,
`Tinker`, `Paladin`, `Ranger`, `Shepherd` for letters `A`, `M`, `B`, `F`,
`D`, `T`, `P`, `R`, `S` in that order (`catalogs/npc-roster.md`, the roster
class letters). A fresh Shamino therefore reads `Lv-2 Fighter` after his glyph
and the Avatar `Lv-2 Avatar`; the name is not repeated on that line. The
status name follows on the next line after the `\nStatus:_` literal, from the
five-entry status table keyed by the status letter.

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

Source provenance: derived from private analysis in
`../u5-decomp/notes/`.

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
   Home and End select the first and last displayable items; PgUp and PgDn
   move seven displayable items toward the relevant endpoint. The input layer
   delivers these four corner keys, including their numpad equivalents, as
   four distinct diagonal codes. The earlier claim that all four keys page
   an eight-row window is withdrawn (R444). This and the shop list navigator are the only places
   outside combat's targeting cursor that consume those codes at all. **Enter
   or Space** confirms the current row - the picker tests the two keys
   separately and both reach the same eligibility cascade. (*Corrected:* an
   earlier revision of this step named Enter alone.) Escape exits and restores
   the HUD.
5. After a successful or refused selection, the picker remains open until the
   player exits, so several items can be attempted in one R-Ready invocation.

The picker is shared infrastructure. In R-Ready mode it walks the equipment
stock band; another caller can reuse the same picker against a different item
band and name table.

**Timing contract.** R-Ready consumes one exploration action in overworld,
town and dungeon modes. In combat it consumes the live combatant's action
instead. A refusal costs exactly what a success costs — there is no free retry
after the command has reached the equipment handler.

The equipment overlay reports no status of its own. The eligibility cascade
returns the same value for every refusal and for every successful equip and
unequip — the one exception is the magic-ring vanish path, which returns the
other value — the picker consumes that value only as a "close the panel"
signal, and the command layer discards it before the mode loop ever sees it. No
outcome inside R-Ready can therefore change the turn cost.

Outside combat the dispatcher reports its default "acted" status for `R`
whatever the overlay did: the `R` arm never writes the status word and is not
one of the arms that overwrite it from its handler's return value. The exact
exploration charge is therefore:

| Mode | Where the sole charge occurs | Nominal clock increment |
|---|---|---:|
| Overworld | Once in the post-action mode epilogue | 2 minutes |
| Town | Once in the post-action mode epilogue | 1 minute |
| Dungeon | Once at the head of the loop iteration, before input | 1 minute |

These are the nominal increments before the shared time modifiers in
`systems/time.md` apply. Quickness changes the overworld increment from two
minutes to one and leaves either one-minute indoor increment at one; Negate
Time suppresses the minute write. Neither modifier changes the fact that the
action or dungeon iteration was consumed. Town mode additionally skips its
whole epilogue when no party member is able to act; that is an
all-incapacitated edge case in which the command is never dispatched, not an
`R` exemption.

In combat, `R` runs through the labelled prompt with the party-side gate, so it
ends the acting combatant's action. Only an actor that fails that gate escapes
the cost, with a short refusal and a free re-prompt. *(**Corrected.** That gate
was previously described here and in `systems/combat.md` as a **live-actor**
test. It reads the acting descriptor's **party-side bit**; no dead actor ever
reaches this handler, and the population it actually refuses is a monster acting
under player control - `RETRACTIONS.md` R381.)* The shared verb helper
discards whatever the ready cascade returned and reports success on every
dispatched path, so an equipment refusal and a successful change end the action
identically.

Ready has no command-specific world-clock advance in combat. Combat owns a
separate counter that invokes the ordinary one-minute clock cleanup on every
tenth phase refresh. That wrap occurs before the corresponding actor is
dispatched and is independent of which command that actor later chooses. A
Ready command can therefore be entered immediately after the normal combat
cadence has advanced the clock, but Ready neither triggers nor duplicates that
advance.

In exploration, every applicable outcome receives that single mode-owned
charge: cancelling the member prompt before an item is shown; the empty-handed
refusal; the silent ammunition row; the strength refusal; the occupied-slot and
hand-occupancy refusals; the ammunition-prerequisite refusal; a successful
equip; a successful unequip; the ring vanish; and opening the picker and
immediately pressing Escape. In combat every path reached for a **party-side** actor,
including the combat-only body-armour lock, spends that actor's action instead;
a monster acting under player control fails the gate and escapes the cost
(`RETRACTIONS.md` R381).

There is no double charge. A complete call-form audit of every function
reachable from R-Ready found no far or computed call and no path to the shared
clock cleanup; walking the resident helpers to their returns produced the same
negative result. A reverse audit of the clock cleanup's callers likewise found
no Ready or equipment helper. Because the panel stays open without returning to
the mode loop, several items may be equipped, unequipped or refused within the
same invocation without accumulating time. The cost is strictly once per
command invocation, not once per attempted row; the ring-vanish path merely
closes that invocation early.

### 5.1 R-Ready presentation

R-Ready reuses both surfaces specified in Section 4 without modification. Its
member selection is the shared surface of Section 4.3: the framed `Select:`
label on the panel's top border, the `Player:_` prompt in the message window,
and the fifteen-cell inverse-video row. Its item list is the eight-row frame of
Section 4.4 with the row format of Section 4.5.

The literals R-Ready owns for itself are the first three below; the fourth
belongs to the shared picker's other caller and is listed only for contrast,
because the two were previously described the wrong way round:

| Literal | Meaning |
|---|---|
| `Item:_` | The item prompt, in the message window. Colon then one trailing space. |
| `Thou_art_empty-\nhanded!\n` | Nothing to ready. The embedded newline is part of the literal, so the word "handed" always starts a new line. |
| `Done\n` | **What R-Ready prints when the player leaves the picker with Escape.** |
| `None!\n` | Printed by the *other* caller of the same shared picker on its Escape, never by R-Ready. Listed here only so the pair is not confused. |

**Those last two literals are now settled.** The shared picker has exactly one
Escape arm, and it chooses between the two literals purely from the mode value it
was opened with: R-Ready's mode selects `Done`, and the other caller's mode
selects `None!`. *Corrected:* an earlier revision of this table glossed `None!`
as "the picker was cancelled" and `Done` as "the picker was closed after use" —
which reads as though R-Ready prints `None!` on Escape. Both glosses are
withdrawn; they had the two the wrong way round for R-Ready. A further revision
recorded the attribution as **UNVERIFIED**; that flag is now cleared, and the
point should no longer be treated as an open question.

The magic-ring vanish closes the picker without printing either literal, so a
port must not attach `Done` to every close — only to the Escape exit. Neither
literal affects any state.

Scope of the settlement: it rests on locating every load of either literal's
address across the equipment overlay and nineteen other shipped code overlays,
which found exactly two, both inside that single Escape arm. That scan covers
loads of the address as an immediate; a pointer fetched from memory instead would
not have been seen.

Closing the picker restores the message-window frame and then triggers a full
roster redraw, which is what puts the six member rows, the food-and-gold line
and the date line back on the panel.

### 5.2 R-Ready result and refusal text

Each ordinary voiced refusal below prints **two line feeds, the listed
message, then two line feeds and `Item:_`**. Here and in Section 7.1,
`\n` denotes a line feed and `_` makes a space explicit. The listed refusal
text contains no additional line feed of its own.

| Cause | Message |
|---|---|
| Body-armour change during undecided combat | `Thou canst not change armour in heated battle!` |
| Required arrows or quarrels absent | `Thou hast no ammunition for that weapon!` |
| Different helm already readied | `Remove first thy present helm!` |
| Different body armour already readied | `Thou must first remove thine other armour!` |
| No hand available for a one-handed item, including a two-handed weapon already held | `Thou must free one of thy hands first!` |
| Two-handed item selected while either hand is occupied | `Both hands must be free before thou canst wield that!` |
| Different amulet already readied | `Thou must remove thine other amulet!` |
| Different ring already readied | `Only one magic ring may be worn at a time!` |
| Resulting burden exceeds Strength | `Thou art not strong enough!` |

The combat armour lock applies before the already-readied unequip test.
An applicable ammunition prerequisite precedes slot occupancy, and an
occupied-slot or hand-conflict message precedes the strength refusal when
both would apply. Selecting an ammunition row itself is silent.

Ordinary successful equip and unequip print **no result message**, no item
name echo and no fresh `Item:_` prompt. The picker remains active. The ring
vanish instead prints `\n\nRing vanishes!\n` and closes without `Done`.
There is no `No carried <item> to ready.` or general `<item> cannot be readied.`
message: the picker omits absent items except those already readied by the
selected member, and the ammunition rejection is silent.

Source provenance: freshly traced refusal wrapper, cascade, selection path
and functional message literals under `u5-decomp/functions/ZSTATS_OVL/`
and `u5-decomp/notes/`, issue #225.

Issue #231 reports a silent arena armour refusal. The traced body-armour
gate above is explicitly voiced while combat remains undecided. An arena
that starts empty already has its announcement guard set (combat Section 7),
so that gate is lifted and ordinary equip/unequip rules apply. The reported
unchanged equipment still needs the selected item, equipped-slot before/after
state and initial foe census to distinguish it from another outcome. The
published voiced refusal is retained pending that reconciliation.

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
  to empty, plays the short vanish sound, and returns the cascade's *other*
  return value — which the picker reads as "close the panel", and nothing else.
  This is the only path in the cascade that produces that value. *Corrected:* an
  earlier revision described it as returning "a consumed-action result to its
  caller". That is withdrawn: it is not a turn-cost signal, the turn cost of the
  vanish path is identical to every other path (see Section 5), and the value
  never leaves the picker. On any nonzero roll, the ring remains readied.

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
combatant is a **party-side** descriptor - not, as this section previously said,
that it is still alive (`RETRACTIONS.md` R381) - and then enters the same
handler. An earlier revision
of this section said combat `U` was label-only and aborted before reaching the
handler; that is withdrawn. What differs in combat is not the routing but the
per-family gates — several item families test the scene and refuse in an arena,
as the family table below and `catalogs/item-list.md` record.

The item-use handler opens an item picker over usable carried stock. If the
party has no usable item, it prints the no-usable-items refusal and exits. A
selected row dispatches by the handler's use-item enumeration rather than by
the forty-eight-entry equipment id space.

The panel title is `Items:`. Sections 4.4 and 4.5 specify its seven visible
rows, selection and scrolling, short regalia labels, and the uncounted
`Moonstone ` plus runic phase-glyph row. The selected label remains drawn
under inversion; it is not replaced by a separate cursor-glyph string.

In non-combat exploration, dispatching U-Use always commits one normal action.
The outer command layer does not distinguish a successful item effect from an
item-specific refusal or an early picker exit. The current mode therefore runs
its ordinary per-turn processing after all of these outcomes: using an item
successfully, receiving a refusal, cancelling the picker, or having no usable
item to select. The mode still owns the contents of that processing -- outdoor,
town, and dungeon turns advance and update their usual mode-specific systems.
The item handler does not decide the turn cost by writing the clock itself.

**The picker's row order is the use-item enumeration order** *(added
2026-09-06, issues #195, #196)*: the eight spell scrolls, the eight potions in
their display order, the Magic Carpet, the Skull Key, the Amulet, the Crown,
the Sceptre, the eight moonstones by phase, the three shards, the Spyglass,
the HMS Cape plans, the Sextant, the Pocket Watch, the Black Badge and the
Sandalwood Box - thirty-eight rows in all, of which the picker shows only
those the party carries. The family table below is in that same order.

Confirmed U-Use families:

| Family | Behaviour |
|---|---|
| Spell scrolls | Eight scroll counters dispatch to spell-like effects: light, wind change, Protection, Negate Magic, View, Summon Daemon, Resurrection, and Negate Time. A scroll counter is decremented before its branch-specific scene gate, target prompt, or helper return. Scrolls share the spell-code labels but have item-specific constants: `LV` sets the magic-light counter to 240 minutes, while `IS`, `AI`, and `AT` write the single shared timed-effect slot in `systems/magic.md` with `P`/100, `N`/20, and `T`/20 turns respectively — replacing whatever effect was already there. `AT` reports no effect in Stonegate and Doom. |
| Potions | Eight colour-coded potion counters dispatch through a party-member target path. Display order is Blue, Yellow, Red, Green, Orange, Purple, Black, White, with normal effects wake, heal, cure poison, poison, sleep, combat-only "Poof" presentation, combat invisibility, and a surface/town visibility repaint sequence. A consumed potion normally applies the selected colour's effect, but a variation roll gives one chance in sixteen to force the Orange sleep effect and one chance in sixteen to replace the effect with a random potion row. Before that roll, the selected colour drives a blocking EGA/Tandy full-playfield invert/sound/restore presentation, so a substituted effect retains the selected bottle's presentation. All eight selected-colour timing rows use the same rumble and paired-sweep structure; the complete numeric table is in `catalogs/item-list.md` Section 7.2. Orange uses an ordinary persistent sleep tile with a one-in-seventeen scheduled wake check; Purple rewrites the combat record to ordinary tile `0x90` without a timer; White reveals the whole eleven-by-eleven viewport window straight from the map, with no distance or line-of-sight test, and repaints that unchanged grid twenty times (**corrected, R318**: the earlier "inclusive squared-distance-threshold-32 visibility grid" wording is withdrawn). Exact rasters, timing, restoration, and no-extra-turn rules are normative in that catalog section. |
| Magic Carpet | Usable in scene ids `0x00..0x20` when the party has exact on-foot transport marker `0x1C` and the current map tile is anything except mountains `0x0C`. This boarding test is independent of movement passability; Section 7.1 gives its precedence and outcomes. On success it chooses carpet marker `0x14` or `0x15` with equal probability and consumes one carried carpet. |
| Skull Key | Decrements the skull-key/special-key counter, then asks for a cardinal target and runs the lock helper in town/overworld or combat. Dungeon exploration refuses through this path. This is separate from `J` Jimmy's ordinary key use. The earlier non-combat-only scope is withdrawn (R415). |
| Regalia | The Amulet of Lord British, the Crown of Lord British, and the Black Badge all behave identically, and all three occupy the single shared timed-effect slot specified in `systems/magic.md` with the permanent duration. Using one of them while its own code already occupies the slot prints a short removal acknowledgement and vacates the slot; otherwise the handler prints the wearing message and installs that item's code. Their only difference is presentational: donning the Amulet or the Crown plays a sound cue, donning the Badge does not. Because the slot is shared and holds one effect at a time, donning any of them cancels an active buff spell, and every path that clears the slot — camping, entering an innkeeper menu, the Blackthorn rescue restoration — silently strips the worn aura until the item is used again. The Sceptre of Lord British is not worn through that state; in eligible non-dungeon scenes it scans the party-centered nearby square for the top-down `0x70..0x7F` barrier/field family, rewrites accepted cells to ordinary open ground with redraw/effect presentation, counts dissolved cells, and otherwise reports no effect or the alternate helper result. |
| Shards | The three Shadowlord shard rows dispatch to the Shadowlord-destruction handler with shard index `0..2`; the handler succeeds only at the matching interior destruction position and only when the matching Shadowlord is the active named encounter, as specified in `catalogs/quest-graph.md`. The U-Use dispatch itself does not decrement or clear anything, so a refused attempt keeps the shard. **A successful destruction consumes the shard**: the destruction handler clears that shard's carried flag as part of the same success step that retires the Shadowlord and sets the quest bit. |
| Moonstones | Rows `1..8` record the current valid location into the matching saved Moonstone slot. Burying is accepted only outside dungeon/combat scenes and only on accepted terrain; Search/Get recovery later invalidates the slot. |
| Spyglass | Night utility, surface plane only. It permits a look when all three of these hold: the party is on the surface plane, the scene is the outdoor world or a town-class scene (dungeon-class and combat-class scenes are excluded), and the hour is in the night window `19..23` or `0..5`. The Underworld fails the plane condition, exactly as the Sextant does. A scene or plane failure prints the "not here" refusal; a daytime hour prints the no-stars refusal; the successful path prints the looking message and enters the same LOOKOBJ sky renderer specified in `systems/view.md` section 4.2. |
| HMS Cape plans | Shipboard-only utility. When used aboard ship, it marks the ship-rigging flag so the ship is rigged for double speed; otherwise it refuses. `weather.md` owns the resulting hoisted-sail wait-pass timing change. |
| Sextant | Outdoor night-only utility, surface plane only. It permits a reading only when all three of these hold: the party is on the **surface** world plane, the scene is the outdoor world scene, and the hour is in the night window `19..23` or `0..5`. **The Underworld does not qualify**: it is the outdoor world scene on the other world plane, so it fails the plane condition and produces the same "only outdoors" refusal an indoor scene produces — there is no Underworld-specific message and no coordinate readout. The item label prints before any of the three tests, so it is emitted even on a refusal. The branch consumes nothing and writes nothing on any of its paths, but every outcome still commits one normal U-Use action and runs the current mode's ordinary per-turn processing. Coordinate formatting is in `catalogs/item-list.md`. |
| Pocket Watch | Prints the current time as a twelve-hour reading with **hour, minutes and AM/PM suffix**. See `catalogs/item-list.md`; an earlier revision of both documents said no minute display was present, and that is withdrawn. |
| Sandalwood Box | The direct U-Use path asks how to use the box and does not perform the endgame handoff. The successful quest handoff is owned by the terminal endgame overlay path, which reads the saved box flag during its Lord British confirmation sequence. |

### 7.1 U-Use family echoes, prompts and utility results

The picker shows usable carried items only. There are **no separate
item-specific ownership refusals** such as `No Sceptre!`, `No Potion!` or
`No Skull Keys!` in the ordinary U-Use flow. An absent item is not selectable;
if every usable item is absent, the command prints `No usable items!\n`.
Cancelling the picker prints `None!\n` after the open `Item:_` prompt.

On acceptance the item's handler completes that same prompt with its family
word, not the decorated picker-row name. The following table gives the exact
completion, including its following line breaks:

| Family | Completion after `Item:_` |
|---|---|
| Any scroll | `Scroll\n\n` |
| Any potion | `Potion\n` |
| Magic Carpet | `Carpet\n\n` |
| Skull Keys | `Skull Key\n` |
| Amulet; Crown; Sceptre of Lord British | `Amulet\n\n`; `Crown\n\n`; `Sceptre\n\n` respectively |
| Any Moonstone | `Moonstone_`, followed immediately by its outcome below; no phase glyph |
| Any shard | `Gem Shard\n\n`, followed by the shard text below |
| Spyglass | `Spyglass\n\n` |
| HMS Cape Plans | `Plans\n\n` |
| Sextant | `Sextant\n\n` |
| Pocket Watch | `Watch\n\n` |
| Black Badge | `Badge\n\n` |
| Wooden/Sandalwood Box | `Box\n\n` |

Utility results follow those completions:

| Item and outcome | Result text |
|---|---|
| Carpet boarded | `Boarded!\n` |
| Carpet while aboard a ship | `X-it ship first!\n` |
| Carpet while on another non-foot transport | `Only on foot!\n` |
| Carpet scene or terrain refusal | `Not here!\n` |
| Skull Key in dungeon exploration | `Not here!\n`; other accepted scenes ask `Direction-` as described below |
| Amulet donned | `Wearing the Amulet of Lord British...\n` |
| Crown donned | `Thou dost don the Crown of Lord British...\n` |
| Badge donned | `Badge worn!\n` |
| Amulet, Crown or Badge removed | `Removed!\n` |
| Sceptre, every accepted selection | `Wielding the Sceptre of Lord British...\n`, before its sound and field checks |
| Sceptre clears one or more nearby top-down fields | No additional result; no count is printed |
| Sceptre fallback reports a dissolved field | `Field dissolved!\n` |
| Sceptre fallback reports no effect | `No effect!\n` |
| Sceptre fallback returns its other result | No additional result |
| Moonstone buried | `buried!\n`, completing `Moonstone_` |
| Moonstone refusal | `cannot be buried here!\n`, completing `Moonstone_` |
| Spyglass accepted | `Looking...\n`, then the sky view |
| Spyglass daytime refusal | `No stars!\n` |
| Spyglass scene or plane refusal | `Not here!\n` |
| Plans used aboard ship | `Ship rigged for double speed!\n` |
| Plans used elsewhere | `Only usable on shipboard!\n` |
| Sextant scene or plane refusal | `Only outdoors!\n` |
| Sextant daytime refusal | `Only at night!\n` |
| Sextant accepted | `Position:`, then the existing coordinate formatter in `catalogs/item-list.md` |
| Pocket Watch | `The pocket watch reads_`, hour, colon, two-digit minute, then `_AM.\n` or `_PM.\n`; hours are 1 through 12 without a leading zero |
| Box | `How?\n` |

**Carpet boarding terrain and precedence** *(clarified 2026-09-09, issue
#251)*. Activating a carried carpet uses its own terrain rule: it accepts
map tile ids `0x00..0x0B` and `0x0D..0xFF`, and rejects only mountains
`0x0C`. Neither the on-foot nor the carpet movement predicate is consulted.
The tested tile is the current map cell at the party's coordinates, not the
party's displayed sprite. There is no surface-versus-Underworld plane gate.

The family completion `Carpet\n\n` precedes every result. Scene ids
`0x21..0xFF` produce `Not here!\n` without a terrain lookup. In an eligible
scene, mountains produce that same refusal before transport is considered.
On other tiles, exact transport marker `0x1C` permits boarding; ship markers
`0x20..0x27` produce `X-it ship first!\n`, and every other marker produces
`Only on foot!\n`. Thus a ship marker on mountains receives `Not here!\n`.

Success prints `Boarded!\n`, selects one of the two carpet frames with equal
probability, and removes one carpet from carried stock. It leaves the map cell,
scene and party coordinates unchanged. Refusals preserve the carpet stock and
transport. The ordinary U-Use action cost described in Section 7 still applies.
This is activation of a carried item; B-Board of a carpet object already on
the map is separately specified in `systems/vehicles.md` Section 3.

Consequently, chair tiles `0x90..0x93` permit boarding even though subsequent
carpet movement rejects them. The boarding rule also accepts tiles excluded
from foot movement, such as `0x0D`. Controlled placement proves that handler
behavior; it does not establish that every accepted tile is ordinarily
reachable on foot. Fresh original-handler traces and 1,284 isolated executions
cover all tile, scene and transport byte values, both successful frame choices,
and refusal precedence. Picker, rendering and random endpoints were controlled;
the original coordinate lookup and boarding decisions executed. Source
provenance: private analysis in `u5-decomp/functions/CAST_OVL/` and
`u5-decomp/functions/ULTIMA_EXE/`.

The shard continuation is `Thou dost hold above thee the evil Shard of_`
followed by `Falsehood...`, `Hatred...` or `Cowardice...`. A wrong destruction
position adds `\n\nNo effect!\n`. At the matching position, the next text is
`\n\n...and cast it into the Flame of_` followed by `Truth!\n`, `Love!\n`
or `Courage!\n` respectively. The later actual Shadowlord destruction adds
`\nThe doom of the Shadowlord_`, the matching name Faulinei, Astaroth or
Nosfentor, then `_is wrought!\n`. The flame sentence precedes the
Shadowlord-presence test; it alone does not establish successful destruction.

The Resurrection scroll and non-combat potion share **`On who:_`**. The
selected member's name completes that line; cancellation completes it with
`None!`. A line feed follows only if the cursor is not already at column
zero, so automatic wrapping does not create an extra empty row. Combat
potion use binds the current party combatant without this prompt.

The Wind Change scroll prints its existing banner and then **`Direction-`**.
Accepted directions append `North\n`, `East\n`, `South\n` or `West\n`;
Space appends `Pass\n`. Other unrecognized keys wait for another input.
This prompt occurs before the scroll's scene gate. Scroll banners and their
effects remain in `catalogs/item-list.md`.

**Skull Key targeting.** After `Item: Skull Key\n`, the shared `Direction-`
prompt accepts a cardinal direction with its ordinary word and newline;
Space completes `Direction-Pass\n`. It does not use the party's facing
without asking. A selected target of tile `0x97` becomes `0xB8`, and `0x98`
becomes `0xBA`; either success dirties the map and adds no result sentence.
Other target tiles print `Failed!\n` with the ordinary Use failure sound,
not Jimmy's `No lock!`. Cancellation adds no generic `Failed!`. One skull
key is already spent before the prompt or the dungeon refusal. Combat runs
this same directed unlock helper; only its later noncombat target aftermath
is omitted. The catalog's combat refusal is withdrawn (R415).

Source provenance: fresh Skull Key caller, shared target helper and Use
completion traces under `u5-decomp/functions/CAST_OVL/` and
`u5-decomp/functions/CAST2_OVL/`, issue #234.

### 7.2 Potion result text

Results belong to the effective colour after the existing variation roll.
They do not repeat the bottle name or the recipient's name/party number.

| Effective potion and outcome | Text after target selection/presentation |
|---|---|
| Blue, accepted wake | No result message |
| Yellow, accepted healing | `Healed!\n` |
| Red, accepted poison cure | `Poison cured!\n` |
| Green, accepted poisoning | `POISONED!\n` |
| Orange, accepted sleep | `Slept!\n` |
| Purple in combat | `Poof!\n` |
| Black in combat | `Invisible!\n` |
| Purple or Black outside combat | `\nNo noticeable effect now!\n` |
| White in an outdoor or town-class scene | No result message; the visibility presentation runs |
| White in dungeon/combat-class scenes | `\nNo noticeable effect now!\n` |
| Blue/Yellow/Red/Green/Orange effect rejects its recipient or status | `Failed!\n`, with the ordinary Use failure sound |

Cancelling the potion target prints the shared `On who: None!` completion
and adds no `Failed!`. The generic U-Use failure tail is also available to
scroll/lock helpers that report failure; it is not an extra suffix on every
item-specific refusal or every effectless outcome.

Source provenance for Sections 7.1 and 7.2: fresh item-picker, handler,
shared-target/direction-prompt and functional-literal traces under
`u5-decomp/functions/CAST_OVL/`, `u5-decomp/functions/CAST2_OVL/`,
`u5-decomp/functions/ZSTATS_OVL/` and `u5-decomp/notes/`, issue #225.

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
- Charge one turn per R-Ready invocation regardless of outcome — including a
  cancelled member prompt, the empty-handed refusal, a silently refused
  ammunition row, every gate refusal, the magic-ring vanish, and opening the
  picker and immediately backing out — and keep the picker open across repeated
  attempts within that turn, **except** after the magic-ring vanish, which
  closes it. In combat the same rule spends the acting combatant's action;
  only an actor that fails the party-side gate escapes the cost.
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
R-Ready's turn cost was re-challenged and re-derived from the shipped binaries
on 2026-08-23 — twice, the second time by an independent adversarial pass that
read the dispatcher, the entry point, the eligibility cascade, the picker, the
combat verb helper and all three mode loops end to end — and stands as published,
so an engine that treats `R` as free is wrong in every mode. The `None!` / `Done`
cancel-literal attribution that was previously listed here as unsettled is
**closed**; Section 5.1 now states it, and `Done` is R-Ready's Escape literal.
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
inventory picker, forward/backward inventory scans, the six-slot
already-equipped check (which tests the six equipment slots of one character,
not what the party owns), the free-hand classifier (which reports which of a
character's hands are free, and is not a test of whether an item is
two-handed), and the equip/unequip cascade. It also cross-checks the
public save-image and item-catalog specs. No decompiled source, assembly
listing, or raw binary dump is reproduced here.

Additional provenance for the equipment-weight note: the resident
`compute_party_member_weight` analysis in
`u5-decomp/functions/ULTIMA_EXE/` and the
inventory trace in `u5-decomp/notes/`; the discarded
call return is visible in the resident
`u5-decomp/functions/ULTIMA_EXE/` note.

R-Ready burden and strength-refusal provenance: the ZSTATS equip/unequip
cascade at `u5-decomp/functions/ZSTATS_OVL/`,
cross-checked against the clean local resident item metadata table.

Combat R-Ready provenance: the combat command dispatcher and prompt helper at
`u5-decomp/functions/COMBAT_OVL/`, cross-checked
with the ZSTATS active-actor selector at
`u5-decomp/functions/ZSTATS_OVL/`.

Magic-ring vanish provenance: the same ZSTATS equip/unequip cascade, corrected
with the Buffer-D `prng_range` thunk mapping in
`u5-decomp/notes/`, and the resident combat ring consumers in
`u5-decomp/functions/ULTIMA_EXE/`, and
`u5-decomp/functions/ULTIMA_EXE/`.

Counter saturation provenance: resident byte/word capped-add and floor-subtract
helper analysis in `u5-decomp/functions/ULTIMA_EXE/` and
sibling helpers, summarized publicly in `systems/stat-arithmetic.md`.

U-Use provenance: CAST overlay use-item dispatch at
`u5-decomp/functions/CAST_OVL/`, scroll/potion
subhandlers in the same overlay, the Shadowlord shard handler at
`u5-decomp/functions/CAST_OVL/`, and the
Moonstone slot writer at
`u5-decomp/functions/CAST_OVL/`, cross-checked against
Search/Get Moonstone recovery notes.

Combat-lock scope, silent-ammunition, and turn-cost provenance: the in-combat
restriction applies to the body-armour family only and lifts once the battle's
outcome has been announced; ammunition rows exit the cascade silently; and a
refused R-Ready costs exactly what a successful one costs in the same mode.
Source provenance: derived from private analysis in
`../u5-decomp/notes/`, with
`../u5-decomp/functions/ZSTATS_OVL/`.

Turn-cost re-derivation provenance (2026-08-23 and the 2026-08-24 double-charge
closure): the `R` dispatcher arm's
unconditional "acted" status, the R-Ready entry point's single exit with no
return value, the eligibility cascade's two return values and which paths reach
each, the ammunition rows' silent exit, the combat verb helper's discarded
delegate result, all three exploration mode loops' clock placement, an
exact-boundary call-form audit of the complete R-Ready subtree, a walk of its
resident helpers to return, and a reverse census of the clock routine's callers.
Together these establish that R-Ready never reaches the clock itself and cannot
double-charge. Re-derived directly from the shipped binaries; private analysis in
`u5-decomp/functions/ZSTATS_OVL/`, `u5-decomp/functions/COMBAT_OVL/` and
`u5-decomp/functions/ULTIMA_EXE/`, with audit records in
`u5-decomp/notes/`, was used only to locate starting points. One
private note describes the R-Ready item prompt with the wrong literal; the
published Section 5.1 wording matches the binary and that note does not.

### Message text and shipped assets

Sections 5.2, 7.1 and 7.2 supply the short functional interface messages
previously described only by their meanings. These are parity contracts;
descriptive names such as "the only-outdoors refusal" do not authorize
inventing substitute wording.

**Every one of these strings ships inside `DATA.OVL`, which any user running
this engine already owns.** An implementation should **read them from the
shipped file at runtime** rather than embedding transcribed copies in its own
source. Doing so is both more faithful - the text matches whatever edition the
user has, including its typographic quirks - and avoids carrying game content
in an engine repository.

The strings are NUL-terminated and sit in a contiguous run of command messages.
For the two this section refers to, and their immediate neighbours, the file
offsets in `DATA.OVL` are:

| File offset | Message |
|---|---|
| `0x49D2` | the ship-rigged-for-double-speed line |
| `0x49F1` | the only-usable-on-shipboard refusal |
| `0x4A0C` | the Sextant label |
| `0x4A16` | the only-outdoors refusal |
| `0x4A26` | the only-at-night refusal |

**The label carries its own trailing blank line.** The Sextant label string ends
with two newlines, so the coordinate pair lands on a separate line from the
label with one blank line between. An implementation that prints the label and
the coordinates on one line has dropped the string's own formatting - which is
the concrete reason to emit the shipped bytes rather than a transcription.

Where a refusal is shared between causes, it is genuinely the **same string**:
the Underworld and an indoor scene both take the only-outdoors refusal, and
neither has an Underworld-specific message.

Sextant and Spyglass gate provenance (2026-08-23): the three-part
plane/scene/night test on each item, the shared refusal text, and the
Underworld's exclusion by the plane condition; re-derived from the shipped
binaries, with `u5-decomp/functions/CAST_OVL/` used to locate the U-Use item
dispatch. A private data-access table for that dispatch mis-attributes the
minutes byte to the coordinate formatter; that attribution is wrong and is not
followed here.

Combat U-Use correction provenance: combat routes `U` into the same item-use
handler the world modes use, after the party-side gate. Source provenance:
derived from private analysis in
`../u5-decomp/notes/` and
`../u5-decomp/functions/COMBAT_OVL/`.
