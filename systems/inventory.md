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
- Keys, gems, torches, magic powder, special items, equipment, spell charges,
  scroll/potion/use-items, and reagents are byte-sized counters or flags.
- The equipment stock band is forty-eight entries. Item id `N` addresses the
  carried stock for equipment row `N`; arms shops, Z-stats inventory pages, and
  R-Ready all use that same id space.
- The spell-charge band is also forty-eight entries, but it is a separate
  spell-stock store. C-Cast and M-Mix own that band.

A zero byte in a carried-counter band means the party owns none of that item.
Nonzero values are quantities, unless the consuming system documents that a
particular item behaves as a present/absent flag.

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

## 4. Z-Stats Inventory Browsing

Z-stats has two roles:

1. It displays per-character stats and readied equipment.
2. It browses inventory pages over shared counter bands.

The first two pages are character-specific: page 1 is the primary stat page and
page 2 is the equipment page. Later inventory pages walk shared counter bands
for reagents, spell charges, special/use items, and the weapons/armour stash.
The inventory list renderer skips zero-count entries. When the caller provides
a character slot, it can also skip items already present in that character's
six-slot equipment block, which is how R-Ready avoids listing equipment the
selected character already has readied.

Inventory rows render from a caller-selected name table. Some name strings use
a leading marker to request a special row layout, such as a one-shot quest-item
indicator or an alternate numeric prefix. These are display conventions only;
the counter band remains the source of ownership.

## 5. R-Ready Flow

R-Ready is the equipment selection command; no separate inventory command owns
these readied-equipment writes.

1. The player selects a party member with the same party-member selection
   surface used by Z-stats.
2. The command scans the forty-eight-entry equipment stock band for the first
   nonzero item that the selected member is not already wearing or wielding.
   If none exists, it prints the normal "nothing to ready" refusal and exits.
3. Otherwise it opens an eight-row picker over the equipment stock band.
4. Up/down movement scrolls to the previous or next owned, not-already-readied
   equipment id. Page movement advances by a full eight-row window where the
   translated key code is available. Enter confirms the current row. Escape
   exits and restores the HUD.
5. After a successful or refused selection, the picker remains open until the
   player exits, so several items can be attempted in one R-Ready invocation.

The picker is shared infrastructure. In R-Ready mode it walks the equipment
stock band; another caller can reuse the same picker against a different item
band and name table.

## 6. R-Ready Eligibility And Writes

After an item is selected, R-Ready classifies it by the item's equipment-class
metadata and applies these gates before writing a slot:

- **Already readied by this character.** If the chosen item id is already in
  any of the selected character's six equipment slots, the cascade
  short-circuits rather than consuming another carried copy.
- **Class or strength refusal.** The character class is mapped through the
  equipment-compatibility table. If the item is not legal for that class or
  capability result, the command prints the parameterized refusal and does not
  change inventory.
- **Combat armour lock.** Body armour cannot be changed in the traced combat
  lock case. Other combat-time ready behaviour is routed through the same
  R-Ready entry point, but exact weapon-swap restrictions still need empirical
  parity testing.
- **Occupied-slot refusal.** Helm, body armour, ring, and amulet classes require
  their corresponding slot to be empty before a different item can be readied.
- **Hand occupancy.** Weapon and shield classes share the weapon-hand/off-hand
  pair. A two-handed item requires both hand slots to be empty. A shield cannot
  be readied while the weapon hand holds a two-handed item. If both hands are
  occupied, hand equipment refuses.
- **Ring vanish path.** One ring-family path consumes the chosen ring after
  acceptance, prints the ring-vanish feedback, and returns a consumed-action
  result to its caller.

When an ordinary equip succeeds, the chosen item id is written into the target
equipment slot and the shared equipment counter for that item id is decremented.
When the original flow removes or displaces an existing readied item, the
shared counter-increment helper is used to return that item to party stock. The
helper evidence supports mass conservation, but the exact swap timing is still
an open parity edge and should be tested against the original before relying on
it for bug-compatible intermediate states.

## 7. Implementation Contract

For a compatible recreation:

- Keep carried equipment counters separate from readied-equipment slots.
- Treat `0xFF` as the empty value in readied-equipment slots.
- Use equipment item ids consistently across shop stock, shop prices, carried
  counters, display names, and readied slots.
- Filter R-Ready candidates to nonzero carried counters not already present in
  the selected character's equipment block.
- Apply class/capability, combat-armour, occupied-slot, and hand-occupancy
  gates before mutating counters.
- Decrement carried stock only after the equip is accepted.
- Return displaced equipment to carried stock when the original flow does so;
  do not drop it on the map or delete it.

## 8. Open Questions

- Exact class-compatibility table values and public names for every equipment
  class are not yet transcribed into `catalogs/item-list.md`.
- Exact combat-time R-Ready behaviour beyond the confirmed body-armour lock
  needs runtime parity testing.
- Ring-family vanish duration, activation trigger, and which ring rows use that
  path need item-by-item confirmation.
- Swap mass-conservation is strongly indicated by the traced helper calls but
  still needs original-game verification for intermediate refusal and repeat
  selection cases.

## 9. Sources

This is a cleanroom prose rewrite derived from semantic notes in the updated
ZSTATS overlay analysis: the overlay overview, R-Ready top-level handler,
inventory picker, forward/backward inventory scans, six-slot ownership helper,
two-handed classifier, and equip/unequip cascade. It also cross-checks the
public save-image and item-catalog specs. No decompiled source, assembly
listing, or raw binary dump is reproduced here.
