# Hidden Treasures

## 1. Scope

This file specifies the fixed S-Search treasure table used outside the ordinary
active-object scan. It is implementation data: a compatible engine needs these
records, their matching order, their one-shot rules, and the pickup classes they
stage. It is not a dump of the original resident tables.

The runtime behavior is specified in `systems/containers.md`. In short, Search
matches the current scene, floor/Z, and searched coordinate against this table.
Accepted records acquire an active-object slot at the searched coordinate,
stage the listed pickup class and state, mark the inventory/status panel dirty,
and narrate the pickup class. A later Get interaction performs the inventory
transfer where the pickup class is Get-compatible.

## 2. Rule Notes

Most records are ordinary one-shot finds. The save-backed found bitmap prevents
the same record from being staged again after a successful Search.

Three records have special gates. None of the three sets a found-bitmap bit, and
none of the three has a persistence field of its own. Each reads a byte that a
different system already owns, so an implementation must alias the existing
field rather than allocate a private cookie:

| Record | Gate field | Rule |
|---:|---|---|
| 13 | The party's Keys counter | Stages only when the party owns **no** keys and the searched tile is not occupied by an NPC. Acquiring any key closes the record; spending every key opens it again. The scan does not modify the keys counter. |
| 14 | An otherwise-unused byte in the special/quest-item band | Stages only when the current day-of-month differs from the byte's value; success writes the current day into it. So the record can stage at most once per in-game day, indefinitely. Nothing resets the byte at day rollover; it simply stops matching. Factory value is zero, which matches no calendar day, so the record is available on the first search. |
| 15 | The equipment-inventory counter for the item it grants | Stages only when that counter is zero and the searched tile is not occupied by an NPC. The skip condition is therefore "counter non-zero **or** an NPC is present". The scan never writes the counter; the ordinary inventory grant for the item does, and that is exactly what makes the record single-use. |

Record 15's granted item is the Glass Sword (equipment item id `39` in
`catalogs/item-list.md`), and its gate is that same item's carried counter. An
engine that models the gate as a separate flag the scan never sets will hand out
an unlimited supply of Glass Swords. Likewise, a party that discards or loses
its Glass Sword makes the record available again — that is original behaviour,
not a defect. `formats/saved-gam.md` Sections 7 and 10 carry the field offsets.

`Z/floor` is the active floor/depth byte. For overworld entries, `0` is
Britannia and `255` is the Underworld plane. For town-style interiors it is the
local floor. The `State` column is the per-record pickup state staged into the
active-object record; Get interprets it according to the pickup class.

## 3. Fixed Table

| Record | Location | Z/floor | X | Y | Pickup class | State | Rule |
|---:|---|---:|---:|---:|---|---:|---|
| 0 | Underworld | 255 | 233 | 233 | Armour | 15 | One-shot |
| 1 | Underworld | 255 | 233 | 233 | Weapon | 41 | One-shot |
| 2 | Underworld | 255 | 233 | 233 | Armour | 15 | One-shot |
| 3 | Underworld | 255 | 233 | 233 | Weapon | 41 | One-shot |
| 4 | Underworld | 255 | 233 | 233 | Armour | 15 | One-shot |
| 5 | Underworld | 255 | 233 | 233 | Weapon | 41 | One-shot |
| 6 | Underworld | 255 | 233 | 233 | Armour | 15 | One-shot |
| 7 | Underworld | 255 | 233 | 233 | Weapon | 41 | One-shot |
| 8 | Underworld | 255 | 233 | 233 | Armour | 15 | One-shot |
| 9 | Underworld | 255 | 233 | 233 | Weapon | 41 | One-shot |
| 10 | Underworld | 255 | 233 | 233 | Armour | 15 | One-shot |
| 11 | Underworld | 255 | 233 | 233 | Weapon | 41 | One-shot |
| 12 | East Britanny | 0 | 2 | 15 | Scroll | 255 | One-shot |
| 13 | Lord Blackthorn's Castle | 255 | 6 | 8 | Ring of keys | 9 | Key/NPC-gated |
| 14 | Minoc | 0 | 2 | 2 | Ring of keys | 133 | Daily cache |
| 15 | Overworld | 0 | 80 | 64 | Weapon | 39 | Single-use/NPC-gated |
| 16 | Lord Blackthorn's Castle | 1 | 6 | 7 | Weapon | 35 | One-shot |
| 17 | Lord Blackthorn's Castle | 1 | 6 | 23 | Weapon | 40 | One-shot |
| 18 | Moonglow | 0 | 5 | 8 | Gem | 1 | One-shot |
| 19 | Moonglow | 0 | 6 | 25 | Armour | 10 | One-shot |
| 20 | Moonglow | 0 | 8 | 25 | Armour | 10 | One-shot |
| 21 | Moonglow | 0 | 5 | 23 | Potion | 5 | One-shot |
| 22 | Moonglow | 0 | 13 | 13 | Potion | 6 | One-shot |
| 23 | Moonglow | 0 | 13 | 14 | Potion | 7 | One-shot |
| 24 | Moonglow | 0 | 13 | 16 | Scroll | 5 | One-shot |
| 25 | Moonglow | 0 | 13 | 17 | Scroll | 7 | One-shot |
| 26 | Moonglow | 1 | 19 | 24 | Food | 10 | One-shot |
| 27 | Moonglow | 0 | 3 | 27 | Torches | 3 | One-shot |
| 28 | Moonglow | 0 | 29 | 27 | Ring | 42 | One-shot |
| 29 | Britain | 0 | 1 | 2 | Food | 5 | One-shot |
| 30 | Britain | 0 | 26 | 6 | Weapon | 20 | One-shot |
| 31 | Britain | 1 | 6 | 24 | Ring | 43 | One-shot |
| 32 | Jhelom | 0 | 16 | 21 | Scroll | 1 | One-shot |
| 33 | Jhelom | 0 | 10 | 20 | Food | 5 | One-shot |
| 34 | Jhelom | 0 | 1 | 29 | Food | 10 | One-shot |
| 35 | Jhelom | 0 | 23 | 30 | Weapon | 38 | One-shot |
| 36 | Jhelom | 0 | 29 | 1 | Torches | 4 | One-shot |
| 37 | Yew | 0 | 11 | 29 | Weapon | 18 | One-shot |
| 38 | Yew | 0 | 26 | 22 | Potion | 3 | One-shot |
| 39 | Yew | 0 | 26 | 1 | Scroll | 4 | One-shot |
| 40 | Yew | 0 | 2 | 13 | Moldy corpse | 0 | One-shot |
| 41 | Yew | 0 | 2 | 14 | Moldy corpse | 0 | One-shot |
| 42 | Yew | 0 | 4 | 14 | Rotting body | 0 | One-shot |
| 43 | Yew | 0 | 3 | 16 | Rotting body | 0 | One-shot |
| 44 | Yew | 0 | 2 | 18 | Rotting body | 0 | One-shot |
| 45 | Yew | 0 | 3 | 16 | Weapon | 21 | One-shot |
| 46 | Yew | 255 | 22 | 27 | Weapon | 37 | One-shot |
| 47 | Yew | 255 | 22 | 20 | Ring of keys | 5 | One-shot |
| 48 | Minoc | 0 | 8 | 27 | Sack of gold | 99 | One-shot |
| 49 | Minoc | 1 | 11 | 13 | Scroll | 1 | One-shot |
| 50 | Minoc | 1 | 11 | 12 | Scroll | 1 | One-shot |
| 51 | Minoc | 1 | 21 | 8 | Potion | 1 | One-shot |
| 52 | Minoc | 1 | 23 | 8 | Potion | 2 | One-shot |
| 53 | Minoc | 1 | 23 | 7 | Scroll | 6 | One-shot |
| 54 | Trinsic | 1 | 6 | 24 | Gem | 4 | One-shot |
| 55 | Skara Brae | 0 | 2 | 5 | Rotting body | 0 | One-shot |
| 56 | Skara Brae | 0 | 7 | 6 | Potion | 1 | One-shot |
| 57 | New Magincia | 1 | 18 | 21 | Potion | 3 | One-shot |
| 58 | New Magincia | 1 | 21 | 25 | Ring of keys | 7 | One-shot |
| 59 | Fogsbane | 0 | 12 | 10 | Torches | 9 | One-shot |
| 60 | Greyhaven | 0 | 15 | 21 | Potion | 0 | One-shot |
| 61 | Greyhaven | 0 | 9 | 14 | Gem | 5 | One-shot |
| 62 | Greyhaven | 0 | 12 | 16 | Sack of gold | 50 | One-shot |
| 63 | Iolo's Hut | 0 | 2 | 24 | Potion | 7 | One-shot |
| 64 | DWELLING:5 | 0 | 12 | 16 | Scroll | 5 | One-shot |
| 65 | DWELLING:5 | 0 | 16 | 14 | Amulet | 45 | One-shot |
| 66 | DWELLING:5 | 0 | 12 | 17 | Scroll | 7 | One-shot |
| 67 | DWELLING:5 | 0 | 12 | 14 | Potion | 4 | One-shot |
| 68 | Lord British's Castle | 0 | 7 | 20 | Armour | 10 | One-shot |
| 69 | Lord British's Castle | 0 | 7 | 21 | Armour | 11 | One-shot |
| 70 | Lord British's Castle | 0 | 7 | 22 | Armour | 9 | One-shot |
| 71 | Lord British's Castle | 0 | 7 | 23 | Armour | 12 | One-shot |
| 72 | Lord British's Castle | 1 | 13 | 21 | Weapon | 30 | One-shot |
| 73 | Lord British's Castle | 255 | 18 | 7 | Ring of keys | 7 | One-shot |
| 74 | Lord British's Castle | 255 | 23 | 20 | Ring | 44 | One-shot |
| 75 | Lord Blackthorn's Castle | 1 | 18 | 17 | Potion | 3 | One-shot |
| 76 | Lord Blackthorn's Castle | 2 | 6 | 13 | Scroll | 5 | One-shot |
| 77 | Lord Blackthorn's Castle | 2 | 6 | 14 | Scroll | 5 | One-shot |
| 78 | Lord Blackthorn's Castle | 2 | 6 | 16 | Scroll | 2 | One-shot |
| 79 | Lord Blackthorn's Castle | 2 | 6 | 17 | Scroll | 7 | One-shot |
| 80 | Lord Blackthorn's Castle | 2 | 7 | 19 | Ring | 43 | One-shot |
| 81 | West Britanny | 0 | 2 | 3 | Rotting body | 0 | One-shot |
| 82 | West Britanny | 0 | 7 | 5 | Rotting body | 0 | One-shot |
| 83 | West Britanny | 0 | 7 | 7 | Rotting body | 0 | One-shot |
| 84 | West Britanny | 0 | 2 | 7 | Rotting body | 0 | One-shot |
| 85 | West Britanny | 0 | 7 | 5 | Scroll | 6 | One-shot |
| 86 | West Britanny | 0 | 2 | 3 | Ring | 44 | One-shot |
| 87 | North Britanny | 0 | 25 | 18 | Gem | 3 | One-shot |
| 88 | East Britanny | 0 | 2 | 13 | Scroll | 1 | One-shot |
| 89 | East Britanny | 0 | 2 | 14 | Scroll | 1 | One-shot |
| 90 | East Britanny | 0 | 2 | 16 | Scroll | 1 | One-shot |
| 91 | Paws | 0 | 13 | 13 | Ring | 42 | One-shot |
| 92 | Paws | 0 | 12 | 3 | Ring of keys | 5 | One-shot |
| 93 | Cove | 0 | 1 | 15 | Amulet | 47 | One-shot |
| 94 | Buccaneer's Den | 0 | 22 | 19 | Ring of keys | 1 | One-shot |
| 95 | Buccaneer's Den | 0 | 22 | 19 | Potion | 3 | One-shot |
| 96 | Ararat | 0 | 16 | 25 | Scroll | 1 | One-shot |
| 97 | Bordermarch | 0 | 4 | 11 | Amulet | 46 | One-shot |
| 98 | Farthing | 0 | 17 | 11 | Potion | 5 | One-shot |
| 99 | Farthing | 0 | 17 | 10 | Potion | 4 | One-shot |
| 100 | Windemere | 0 | 22 | 19 | Scroll | 5 | One-shot |
| 101 | The Lycaeum | 2 | 9 | 23 | Ring | 42 | One-shot |
| 102 | The Lycaeum | 2 | 7 | 23 | Amulet | 46 | One-shot |
| 103 | The Lycaeum | 2 | 7 | 20 | Potion | 7 | One-shot |
| 104 | The Lycaeum | 1 | 19 | 22 | Weapon | 18 | One-shot |
| 105 | The Lycaeum | 1 | 17 | 22 | Amulet | 46 | One-shot |
| 106 | Empath Abbey | 0 | 3 | 6 | Potion | 1 | One-shot |
| 107 | Empath Abbey | 0 | 7 | 19 | Food | 20 | One-shot |
| 108 | Serpent's Hold | 1 | 21 | 8 | Potion | 7 | One-shot |
| 109 | Moonglow | 1 | 24 | 19 | Food | 16 | One-shot |
| 110 | Moonglow | 1 | 24 | 20 | Food | 13 | One-shot |
| 111 | Lord British's Castle | 2 | 12 | 12 | Potion | 6 | One-shot |
| 112 | Lord British's Castle | 2 | 12 | 12 | Scroll | 7 | One-shot |

## 4. Sources

This cleanroom table was derived from private analysis and rewritten as
semantic records. It does not reproduce decompiled source, assembly, raw data
dumps, or private address tables.

- `u5-decomp/functions/SJOG_OVL/0x0514_sjog_hidden_treasure_scan.md`.
- `u5-decomp/functions/SJOG_OVL/0x012A_sjog_print_object_name.md`.
- `u5-decomp/functions/ULTIMA_EXE/0xB8A4_init_object_slot.md`.
- `u5-spec/catalogs/gazetteer.md`.
