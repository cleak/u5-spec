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

The resident engine also has a separate helper that computes an equipped-item
weight statistic from the six readied slot bytes using a different lookup table
from the R-Ready burden gate. That lookup is item-id keyed and is listed in
`catalogs/item-list.md`. The helper treats empty equipment slots as zero and
adds 3 when the shared active-effect/status tag is Protection. In the traced
baseline, its only identified call is after the resident "remove first matching
readied item" helper used by combat-side ring removal, and that caller discards
the computed return value before returning its own hit/miss result. Do not add
non-R-Ready encumbrance, readiness enforcement, or combat-defense
recalculation from this helper.

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

Character pages have two alternating forms:

- **Stats page.** Shows class, status, level, Strength, Dexterity, Intellect,
  current and maximum hit points, magic points, and experience for the selected
  character. Class and status are looked up through label tables rather than
  printed from the raw record byte. Numeric fields use the resident number
  printer, with HP and XP rendered at their wider field widths.
- **Equipment page.** Reads the six readied-equipment bytes in record order and
  prints each non-empty abbreviated equipment name. The empty equipment value
  is `0xFF`; if all six slots are empty, the page prints the ordinary nothing-
  equipped fallback instead of a blank list.

The party-wide inventory pages use the same eight-row panel and row renderer as
the R-Ready picker. The traced pages are raw reagents, premixed spell charges,
special/use items, and the weapons/armour equipment stock band. The row scanner
walks a caller-supplied counter band forward or backward from a mutable cursor,
skipping zero-count rows for ordinary inventory browsing. When a character
slot is supplied for R-Ready, a row is also displayable if that character
already has the item readied, which lets the picker offer unequip rows even
when the carried counter is zero. When no displayable row exists, the panel
prints the normal none placeholder and waits for a key before returning to the
page loop.

Inventory line rendering is table-driven. Ordinary item names print verbatim.
Names with a leading marker request one of three special layouts: a one-shot
quest-item indicator, a counted-special prefix using the matching value table,
or a parenthesized/single-character count prefix. The marker is a display
prefix convention in the name table; it does not change the underlying counter
band or item id.

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
   Page movement advances by a full eight-row window where the translated key
   code is available. Enter confirms the current row. Escape exits and
   restores the HUD.
5. After a successful or refused selection, the picker remains open until the
   player exits, so several items can be attempted in one R-Ready invocation.

The picker is shared infrastructure. In R-Ready mode it walks the equipment
stock band; another caller can reuse the same picker against a different item
band and name table.

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
  cascade without mutation. Bow and Magic Bow readiness requires at least one
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
  active living combat actor. The traced combat-scene-specific refusal is the
  body-armour lock: the party is in a combat scene, the selected item is in
  the body-armour class range, and the internal ready guard for that branch is
  clear. This is not a blanket refusal for every R-Ready item during combat.
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

U-Use is the non-combat item-activation command. Surface, town, keep, castle,
and dungeon-exploration modes route `U` to the CAST-owned item-use handler.
Combat mode does not: combat `U` only prints the verb label and aborts through
the combat scene-message path.

The item-use handler opens an item picker over usable carried stock. If the
party has no usable item, it prints the no-usable-items refusal and exits. A
selected row dispatches by the handler's use-item enumeration rather than by
the forty-eight-entry equipment id space.

Confirmed U-Use families:

| Family | Behaviour |
|---|---|
| Spell scrolls | Eight scroll counters dispatch to spell-like effects: light, wind change, Protection, Negate Magic, View, Summon Daemon, Resurrection, and Negate Time. A scroll counter is decremented before its branch-specific scene gate, target prompt, or helper return. Scrolls share the spell-code labels but have item-specific constants: `LV` starts light with value 240, `IS` installs `P`/100, `AI` installs `N`/20, and `AT` installs `T`/20 except in Stonegate and Doom, where it reports no effect. |
| Potions | Eight colour-coded potion counters dispatch through a party-member target path. Display order is Blue, Yellow, Red, Green, Orange, Purple, Black, White, with normal effects wake, heal, cure poison, poison, sleep, combat-only "Poof" presentation, combat invisibility, and a surface/town visibility-sweep animation. A consumed potion normally applies the selected colour's effect, but a variation roll gives one chance in sixteen to force the Orange sleep effect and one chance in sixteen to replace the effect with a random potion row. |
| Magic Carpet | Usable outside dungeon/combat scenes when the party is on foot and the current tile accepts carpet boarding. On success it changes the party transport marker to a carpet state and decrements the carried carpet counter. If the party is aboard a ship or otherwise not on foot, it prints the matching refusal instead. |
| Skull Key | Decrements the skull-key/special-key counter, then runs the adjacent-lock helper in non-combat scenes that support it. Dungeon exploration refuses through this path. This is separate from `J` Jimmy's ordinary key use. |
| Regalia | Amulet of Lord British and Crown of Lord British toggle through a shared worn-regalia state: using the item while it is already active removes it; otherwise the handler prints the wearing message and installs the corresponding state. The Black Badge uses the same remove-if-active helper and can install its own worn state. The Sceptre of Lord British is not worn through that state; in eligible non-dungeon scenes it scans the party-centered nearby square for the top-down `0x70..0x7F` barrier/field family, rewrites accepted cells to ordinary open ground with redraw/effect presentation, counts dissolved cells, and otherwise reports no effect or the alternate helper result. |
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
  mutating counters.
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
opaque save/runtime bytes are delegated to their own specs.

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
