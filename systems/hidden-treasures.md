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
| 14 | An otherwise-unused byte in the special/quest-item band | Stages only when the current day-of-month differs from the byte's value; success writes the current day into it. So the record can stage at most once per in-game day, indefinitely. Ordinary midnight does not touch the byte — it simply stops matching once the day advances. The 28-day **month** rollover does clear it to zero, along with the rare-reagent harvest cookies and the early-game encounter-size damper (`systems/time.md` Section 8; the older "fortunes of war" name for that damper is withdrawn). Factory value is zero, which matches no calendar day, so the record is available on the first search. |
| 15 | The equipment-inventory counter for the item it grants | Stages only when that counter is zero and the searched tile is not occupied by an NPC. The skip condition is therefore "counter non-zero **or** an NPC is present". The scan never writes the counter; the ordinary inventory grant for the item does, and that is exactly what makes the record single-use. |

Record 15's granted item is the Glass Sword (equipment item id `39` in
`catalogs/item-list.md`), and its gate is that same item's carried counter. An
engine that models the gate as a separate flag the scan never sets will hand out
an unlimited supply of Glass Swords. Likewise, a party that discards or loses
its Glass Sword makes the record available again — that is original behaviour,
not a defect. `formats/saved-gam.md` Sections 7 and 10 carry the field offsets.

## 2.1 What a found record prints

A staged record is narrated with one line from a fixed seventeen-name
vocabulary, selected by the record's pickup class, on the row after the Search
preamble of `systems/commands.md` Section 5.8:

| Pickup class in Section 3 | Narrated row |
|---|---|
| Sack of gold | `a sack of gold!` |
| Potion | `a potion!` |
| Scroll | `a scroll!` |
| Weapon | `a weapon!` |
| Ring of keys | `a ring of keys!` |
| Gem | `a gem!` |
| Ring | `a ring!` |
| Armour | `some armour!` |
| Amulet | `an amulet!` |
| Torches | `some torches!` |
| Food | `some food!` |
| Rotting body | `a rotting body!` |
| Moldy corpse | `a moldy corpse!` |

The selector is a **thirty-one-slot jump table** indexed directly by the pickup
class, so classes `1` through `31` each have a slot whether or not a name was
authored for it; the unused slots and every class outside `1..31` fall to the
capitalised default below. That structure is what makes "lands on one of its
unused slots" a case distinct from "outside the vocabulary".

The vocabulary also holds `a chest!`, `a shield!`, `a helm!` and its own copy of
`a strange rock!`, but **no shipped record reaches them** - the thirteen rows
above are the whole reachable set, and the strange rock a player actually sees
comes from the buried-Moonstone table rather than from here. A record whose
class falls outside the vocabulary, or lands on one of its unused slots, prints
the capitalised `Nothing of note.` - a different stored string from the treasure
scan's own lower-case `nothing of note.`, and the only place the capitalised
form appears on the surface path.

Twelve of the 113 records (`0` through `11`) all sit on one Underworld cell:
scene `0`, Z `255`, `(233, 233)`, directly beneath the Shrine of the Codex tile
on Britannia. *(Corrected 2026-10-30, issue #314 Q2.)* Search compares each
record's scene, Z, X and Y for exact equality with the current scene, the
current plane and the searched cell; the scan starts at record `0`, and the only
extra conditions are those of records 13, 14 and 15 (Section 2), so there is no
record-range start and no plane exclusion. On the world planes the
fixed-treasure scan is the last step of the surface Search cascade, after the
buried-Moonstone and reagent checks, and it runs on the Underworld exactly as on
Britannia. A Search of that cell therefore stages the twelve records one per
Search in table order, by the shared-cell rule of Section 3. Executed on the
original with the stock tables (the party placed on the Underworld at
`(232, 233)`, searching east): the three Searches printed `Thou dost find` and
then `some armour!`, `a weapon!` and `some armour!` in turn; Get then printed
`Mystic Armour!`; the saved Mystic Armour count went from 0 to 1, Mystic Sword
stayed 0, and the found bits of records 0, 1 and 2 were set. Each turn there
also printed `Burning!`, because the party stood on lava
(`catalogs/tile-catalog.md` Section 6). The claim is scoped to the stock boot-time
tables: no census of runtime writers to the record arrays was made. The cell is
the centre of a thirteen-cell pool of molten lava (`0x8F`). On foot it lies in a
33-cell pocket of that lava and 20 hill cells, with no grass, closed off by
mountains (`0x0C`) and peaks (`0x0D`); even counting every mountain as passable
the enlarged 262-cell region, which holds 24 grass cells, is still closed off by
peaks, which Klimb refuses with `Impassable!`. Whether ordinary play can bring a
party into the pocket is not established (`OPEN-QUESTIONS.md` section 3). This
paragraph previously said the records sat "at an impossible floor and cannot be
reached by an ordinary Search"; Z `255` is the Underworld plane, and that text is
retracted (`RETRACTIONS.md` R659).

`Z/floor` is the active floor/depth byte. For overworld entries, `0` is
Britannia and `255` is the Underworld plane. For town-style interiors it is the
local floor. The `State` column is the per-record pickup state staged into the
active-object record; Get interprets it according to the pickup class.

## 3. Fixed Table

*(Corrected 2026-10-25, issue #300 Q1: earlier revisions printed every record's
X in the Y column and its Y in the X column; the columns below are the
corrected ones, and the transposed table is retracted, `RETRACTIONS.md` R584.)*
X is the east-west column and Y the north-south row, in the same convention as
the party position: Search compares the searched cell's column (the party's
column plus the direction's east-west step) with the value in the X column, the
staged object's own column field receives that value, and Get later finds the
object by comparing that field with the party's column plus its step. The 18
records whose X equals Y are unaffected; all other 95 rows were transposed.

**How the grant is formed.** *(Added 2026-10-25, issue #300 Q1.)* A staged
record carries two values into its active-object slot: its pickup class and its
state. Get hands both to the inventory-add dispatcher of `systems/containers.md`
Section 8. The class selects the arm, and the state is that arm's single
argument:

| Pickup class (class value) | Meaning of the state | Grant |
|---|---|---|
| Sack of gold (2) | quantity | gold + state, capped at 9999 |
| Potion (3) | potion id, used unmasked | one potion of that colour, capped at 99 |
| Scroll (4) | scroll id, or 255 for the plans | one scroll of that id (capped at 99); at 255, the HMS Cape plans flag is set instead and no scroll counter changes |
| Weapon (5), Ring (10), Armour (11), Amulet (12) | equipment id in `catalogs/item-list.md` Section 5.1 | one of that item, capped at 99 (Arrows and Quarrels would add five, but no record names them) |
| Ring of keys (7) | key quantity; a value above 127 is the odd-key marker | below 128, ordinary keys + state; above 127, the marker is dropped (only the low seven bits are kept) and that quantity is added to the skull-key counter instead. Capped at 99 |
| Gem (8) | quantity | gems + state, capped at 99 (gems share the torch adder and its cap) |
| Torches (13) | quantity | torches + state, capped at 99 |
| Food (15) | quantity | food + state, capped at 9999 |
| Rotting body (30), Moldy corpse (31) | unused (always 0) | none: Get's acceptance filter rejects both classes, so the dispatcher is never reached (`systems/containers.md` Section 3) |

The table's "Get grants" column applies that rule to each record, and "Get line"
is the row Get prints after its leading line feed, in the forms of
`systems/commands.md` Section 5.8 (a scroll's mnemonic is drawn in the alternate
typeface). Two consequences an implementation can check directly: record 12
sets the HMS Cape plans and adds no scroll, printing
`The plans for the HMS Cape!`; record 14's state 133 is the odd-key marker plus
5, so it adds **five skull keys** and prints `5 odd keys!` (the singular/plural
test also uses the unmarked quantity). The potion article never changes, so the
Orange records read `A orange potion!`. Records 0 to 11 are the Underworld
lava-pool cell of Section 2.1; record 0's grant was seen in play, and the
others follow the same dispatcher (the odd records' Mystic Sword is that
dispatcher reading, not a pickup observed in play). *(Corrected 2026-10-30,
issue #314 Q2: this called them unreachable filler, `RETRACTIONS.md` R659.)*

| Record | Location | Z/floor | X | Y | Pickup class | State | Rule | Get grants | Get line after the leading feed |
|---:|---|---:|---:|---:|---|---:|---|---|---|
| 0 | Underworld | 255 | 233 | 233 | Armour (11) | 15 | One-shot | one Mystic Armour (equipment id 15) | `Mystic Armour!` |
| 1 | Underworld | 255 | 233 | 233 | Weapon (5) | 41 | One-shot | one Mystic Sword (equipment id 41) | `Mystic Sword!` |
| 2 | Underworld | 255 | 233 | 233 | Armour (11) | 15 | One-shot | one Mystic Armour (equipment id 15) | `Mystic Armour!` |
| 3 | Underworld | 255 | 233 | 233 | Weapon (5) | 41 | One-shot | one Mystic Sword (equipment id 41) | `Mystic Sword!` |
| 4 | Underworld | 255 | 233 | 233 | Armour (11) | 15 | One-shot | one Mystic Armour (equipment id 15) | `Mystic Armour!` |
| 5 | Underworld | 255 | 233 | 233 | Weapon (5) | 41 | One-shot | one Mystic Sword (equipment id 41) | `Mystic Sword!` |
| 6 | Underworld | 255 | 233 | 233 | Armour (11) | 15 | One-shot | one Mystic Armour (equipment id 15) | `Mystic Armour!` |
| 7 | Underworld | 255 | 233 | 233 | Weapon (5) | 41 | One-shot | one Mystic Sword (equipment id 41) | `Mystic Sword!` |
| 8 | Underworld | 255 | 233 | 233 | Armour (11) | 15 | One-shot | one Mystic Armour (equipment id 15) | `Mystic Armour!` |
| 9 | Underworld | 255 | 233 | 233 | Weapon (5) | 41 | One-shot | one Mystic Sword (equipment id 41) | `Mystic Sword!` |
| 10 | Underworld | 255 | 233 | 233 | Armour (11) | 15 | One-shot | one Mystic Armour (equipment id 15) | `Mystic Armour!` |
| 11 | Underworld | 255 | 233 | 233 | Weapon (5) | 41 | One-shot | one Mystic Sword (equipment id 41) | `Mystic Sword!` |
| 12 | East Britanny | 0 | 15 | 2 | Scroll (4) | 255 | One-shot | HMS Cape plans flag set (no scroll counter) | `The plans for the HMS Cape!` |
| 13 | Lord Blackthorn's Castle | 255 | 8 | 6 | Ring of keys (7) | 9 | Key/NPC-gated | Keys +9 | `9 keys!` |
| 14 | Minoc | 0 | 2 | 2 | Ring of keys (7) | 133 | Daily cache | Skull (odd) keys +5 | `5 odd keys!` |
| 15 | Overworld | 0 | 64 | 80 | Weapon (5) | 39 | Single-use/NPC-gated | one Glass Sword (equipment id 39) | `Glass Sword!` |
| 16 | Lord Blackthorn's Castle | 1 | 7 | 6 | Weapon (5) | 35 | One-shot | one Sword of Chaos (equipment id 35) | `Sword of Chaos!` |
| 17 | Lord Blackthorn's Castle | 1 | 23 | 6 | Weapon (5) | 40 | One-shot | one Jeweled Sword (equipment id 40) | `Jeweled Sword!` |
| 18 | Moonglow | 0 | 8 | 5 | Gem (8) | 1 | One-shot | Gems +1 | `1 gem!` |
| 19 | Moonglow | 0 | 25 | 6 | Armour (11) | 10 | One-shot | one Leather Armour (equipment id 10) | `Leather Armour!` |
| 20 | Moonglow | 0 | 25 | 8 | Armour (11) | 10 | One-shot | one Leather Armour (equipment id 10) | `Leather Armour!` |
| 21 | Moonglow | 0 | 23 | 5 | Potion (3) | 5 | One-shot | one Purple potion (potion id 5) | `A purple potion!` |
| 22 | Moonglow | 0 | 13 | 13 | Potion (3) | 6 | One-shot | one Black potion (potion id 6) | `A black potion!` |
| 23 | Moonglow | 0 | 14 | 13 | Potion (3) | 7 | One-shot | one White potion (potion id 7) | `A white potion!` |
| 24 | Moonglow | 0 | 16 | 13 | Scroll (4) | 5 | One-shot | one Summon Daemon scroll (scroll id 5) | `A scroll: KXC!` |
| 25 | Moonglow | 0 | 17 | 13 | Scroll (4) | 7 | One-shot | one Negate Time scroll (scroll id 7) | `A scroll: AT!` |
| 26 | Moonglow | 1 | 24 | 19 | Food (15) | 10 | One-shot | Food +10 | `10 food!` |
| 27 | Moonglow | 0 | 27 | 3 | Torches (13) | 3 | One-shot | Torches +3 | `3 torches!` |
| 28 | Moonglow | 0 | 27 | 29 | Ring (10) | 42 | One-shot | one Ring of Invisibility (equipment id 42) | `Ring of Invisibility!` |
| 29 | Britain | 0 | 2 | 1 | Food (15) | 5 | One-shot | Food +5 | `5 food!` |
| 30 | Britain | 0 | 6 | 26 | Weapon (5) | 20 | One-shot | one Main Gauche (equipment id 20) | `Main Gauche!` |
| 31 | Britain | 1 | 24 | 6 | Ring (10) | 43 | One-shot | one Ring of Protection (equipment id 43) | `Ring of Protection!` |
| 32 | Jhelom | 0 | 21 | 16 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 33 | Jhelom | 0 | 20 | 10 | Food (15) | 5 | One-shot | Food +5 | `5 food!` |
| 34 | Jhelom | 0 | 29 | 1 | Food (15) | 10 | One-shot | Food +10 | `10 food!` |
| 35 | Jhelom | 0 | 30 | 23 | Weapon (5) | 38 | One-shot | one Magic Axe (equipment id 38) | `Magic Axe!` |
| 36 | Jhelom | 0 | 1 | 29 | Torches (13) | 4 | One-shot | Torches +4 | `4 torches!` |
| 37 | Yew | 0 | 29 | 11 | Weapon (5) | 18 | One-shot | one Club (equipment id 18) | `Club!` |
| 38 | Yew | 0 | 22 | 26 | Potion (3) | 3 | One-shot | one Green potion (potion id 3) | `A green potion!` |
| 39 | Yew | 0 | 1 | 26 | Scroll (4) | 4 | One-shot | one View scroll (scroll id 4) | `A scroll: IQW!` |
| 40 | Yew | 0 | 13 | 2 | Moldy corpse (31) | 0 | One-shot | nothing: Get skips it; a later Search of the cell runs the corpse branch | - |
| 41 | Yew | 0 | 14 | 2 | Moldy corpse (31) | 0 | One-shot | nothing: Get skips it; a later Search of the cell runs the corpse branch | - |
| 42 | Yew | 0 | 14 | 4 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 43 | Yew | 0 | 16 | 3 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 44 | Yew | 0 | 18 | 2 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 45 | Yew | 0 | 16 | 3 | Weapon (5) | 21 | One-shot | one Spear (equipment id 21) | `Spear!` |
| 46 | Yew | 255 | 27 | 22 | Weapon (5) | 37 | One-shot | one Silver Sword (equipment id 37) | `Silver Sword!` |
| 47 | Yew | 255 | 20 | 22 | Ring of keys (7) | 5 | One-shot | Keys +5 | `5 keys!` |
| 48 | Minoc | 0 | 27 | 8 | Sack of gold (2) | 99 | One-shot | Gold +99 | `99 gold!` |
| 49 | Minoc | 1 | 13 | 11 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 50 | Minoc | 1 | 12 | 11 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 51 | Minoc | 1 | 8 | 21 | Potion (3) | 1 | One-shot | one Yellow potion (potion id 1) | `A yellow potion!` |
| 52 | Minoc | 1 | 8 | 23 | Potion (3) | 2 | One-shot | one Red potion (potion id 2) | `A red potion!` |
| 53 | Minoc | 1 | 7 | 23 | Scroll (4) | 6 | One-shot | one Resurrection scroll (scroll id 6) | `A scroll: IMC!` |
| 54 | Trinsic | 1 | 24 | 6 | Gem (8) | 4 | One-shot | Gems +4 | `4 gems!` |
| 55 | Skara Brae | 0 | 5 | 2 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 56 | Skara Brae | 0 | 6 | 7 | Potion (3) | 1 | One-shot | one Yellow potion (potion id 1) | `A yellow potion!` |
| 57 | New Magincia | 1 | 21 | 18 | Potion (3) | 3 | One-shot | one Green potion (potion id 3) | `A green potion!` |
| 58 | New Magincia | 1 | 25 | 21 | Ring of keys (7) | 7 | One-shot | Keys +7 | `7 keys!` |
| 59 | Fogsbane | 0 | 10 | 12 | Torches (13) | 9 | One-shot | Torches +9 | `9 torches!` |
| 60 | Greyhaven | 0 | 21 | 15 | Potion (3) | 0 | One-shot | one Blue potion (potion id 0) | `A blue potion!` |
| 61 | Greyhaven | 0 | 14 | 9 | Gem (8) | 5 | One-shot | Gems +5 | `5 gems!` |
| 62 | Greyhaven | 0 | 16 | 12 | Sack of gold (2) | 50 | One-shot | Gold +50 | `50 gold!` |
| 63 | Iolo's Hut | 0 | 24 | 2 | Potion (3) | 7 | One-shot | one White potion (potion id 7) | `A white potion!` |
| 64 | DWELLING:5 | 0 | 16 | 12 | Scroll (4) | 5 | One-shot | one Summon Daemon scroll (scroll id 5) | `A scroll: KXC!` |
| 65 | DWELLING:5 | 0 | 14 | 16 | Amulet (12) | 45 | One-shot | one Amulet/Turning (equipment id 45) | `Amulet/Turning!` |
| 66 | DWELLING:5 | 0 | 17 | 12 | Scroll (4) | 7 | One-shot | one Negate Time scroll (scroll id 7) | `A scroll: AT!` |
| 67 | DWELLING:5 | 0 | 14 | 12 | Potion (3) | 4 | One-shot | one Orange potion (potion id 4) | `A orange potion!` |
| 68 | Lord British's Castle | 0 | 20 | 7 | Armour (11) | 10 | One-shot | one Leather Armour (equipment id 10) | `Leather Armour!` |
| 69 | Lord British's Castle | 0 | 21 | 7 | Armour (11) | 11 | One-shot | one Ring Mail (equipment id 11) | `Ring Mail!` |
| 70 | Lord British's Castle | 0 | 22 | 7 | Armour (11) | 9 | One-shot | one Cloth Armour (equipment id 9) | `Cloth Armour!` |
| 71 | Lord British's Castle | 0 | 23 | 7 | Armour (11) | 12 | One-shot | one Scale Mail (equipment id 12) | `Scale Mail!` |
| 72 | Lord British's Castle | 1 | 21 | 13 | Weapon (5) | 30 | One-shot | one Long Sword (equipment id 30) | `Long Sword!` |
| 73 | Lord British's Castle | 255 | 7 | 18 | Ring of keys (7) | 7 | One-shot | Keys +7 | `7 keys!` |
| 74 | Lord British's Castle | 255 | 20 | 23 | Ring (10) | 44 | One-shot | one Ring of Regeneration (equipment id 44) | `Ring of Regeneration!` |
| 75 | Lord Blackthorn's Castle | 1 | 17 | 18 | Potion (3) | 3 | One-shot | one Green potion (potion id 3) | `A green potion!` |
| 76 | Lord Blackthorn's Castle | 2 | 13 | 6 | Scroll (4) | 5 | One-shot | one Summon Daemon scroll (scroll id 5) | `A scroll: KXC!` |
| 77 | Lord Blackthorn's Castle | 2 | 14 | 6 | Scroll (4) | 5 | One-shot | one Summon Daemon scroll (scroll id 5) | `A scroll: KXC!` |
| 78 | Lord Blackthorn's Castle | 2 | 16 | 6 | Scroll (4) | 2 | One-shot | one Protection scroll (scroll id 2) | `A scroll: IS!` |
| 79 | Lord Blackthorn's Castle | 2 | 17 | 6 | Scroll (4) | 7 | One-shot | one Negate Time scroll (scroll id 7) | `A scroll: AT!` |
| 80 | Lord Blackthorn's Castle | 2 | 19 | 7 | Ring (10) | 43 | One-shot | one Ring of Protection (equipment id 43) | `Ring of Protection!` |
| 81 | West Britanny | 0 | 3 | 2 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 82 | West Britanny | 0 | 5 | 7 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 83 | West Britanny | 0 | 7 | 7 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 84 | West Britanny | 0 | 7 | 2 | Rotting body (30) | 0 | One-shot | nothing: Get skips it | - |
| 85 | West Britanny | 0 | 5 | 7 | Scroll (4) | 6 | One-shot | one Resurrection scroll (scroll id 6) | `A scroll: IMC!` |
| 86 | West Britanny | 0 | 3 | 2 | Ring (10) | 44 | One-shot | one Ring of Regeneration (equipment id 44) | `Ring of Regeneration!` |
| 87 | North Britanny | 0 | 18 | 25 | Gem (8) | 3 | One-shot | Gems +3 | `3 gems!` |
| 88 | East Britanny | 0 | 13 | 2 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 89 | East Britanny | 0 | 14 | 2 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 90 | East Britanny | 0 | 16 | 2 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 91 | Paws | 0 | 13 | 13 | Ring (10) | 42 | One-shot | one Ring of Invisibility (equipment id 42) | `Ring of Invisibility!` |
| 92 | Paws | 0 | 3 | 12 | Ring of keys (7) | 5 | One-shot | Keys +5 | `5 keys!` |
| 93 | Cove | 0 | 15 | 1 | Amulet (12) | 47 | One-shot | one Ankh (equipment id 47) | `Ankh!` |
| 94 | Buccaneer's Den | 0 | 19 | 22 | Ring of keys (7) | 1 | One-shot | Keys +1 | `1 key!` |
| 95 | Buccaneer's Den | 0 | 19 | 22 | Potion (3) | 3 | One-shot | one Green potion (potion id 3) | `A green potion!` |
| 96 | Ararat | 0 | 25 | 16 | Scroll (4) | 1 | One-shot | one Wind Change scroll (scroll id 1) | `A scroll: RH!` |
| 97 | Bordermarch | 0 | 11 | 4 | Amulet (12) | 46 | One-shot | one Spiked Collar (equipment id 46) | `Spiked Collar!` |
| 98 | Farthing | 0 | 11 | 17 | Potion (3) | 5 | One-shot | one Purple potion (potion id 5) | `A purple potion!` |
| 99 | Farthing | 0 | 10 | 17 | Potion (3) | 4 | One-shot | one Orange potion (potion id 4) | `A orange potion!` |
| 100 | Windemere | 0 | 19 | 22 | Scroll (4) | 5 | One-shot | one Summon Daemon scroll (scroll id 5) | `A scroll: KXC!` |
| 101 | The Lycaeum | 2 | 23 | 9 | Ring (10) | 42 | One-shot | one Ring of Invisibility (equipment id 42) | `Ring of Invisibility!` |
| 102 | The Lycaeum | 2 | 23 | 7 | Amulet (12) | 46 | One-shot | one Spiked Collar (equipment id 46) | `Spiked Collar!` |
| 103 | The Lycaeum | 2 | 20 | 7 | Potion (3) | 7 | One-shot | one White potion (potion id 7) | `A white potion!` |
| 104 | The Lycaeum | 1 | 22 | 19 | Weapon (5) | 18 | One-shot | one Club (equipment id 18) | `Club!` |
| 105 | The Lycaeum | 1 | 22 | 17 | Amulet (12) | 46 | One-shot | one Spiked Collar (equipment id 46) | `Spiked Collar!` |
| 106 | Empath Abbey | 0 | 6 | 3 | Potion (3) | 1 | One-shot | one Yellow potion (potion id 1) | `A yellow potion!` |
| 107 | Empath Abbey | 0 | 19 | 7 | Food (15) | 20 | One-shot | Food +20 | `20 food!` |
| 108 | Serpent's Hold | 1 | 8 | 21 | Potion (3) | 7 | One-shot | one White potion (potion id 7) | `A white potion!` |
| 109 | Moonglow | 1 | 19 | 24 | Food (15) | 16 | One-shot | Food +16 | `16 food!` |
| 110 | Moonglow | 1 | 20 | 24 | Food (15) | 13 | One-shot | Food +13 | `13 food!` |
| 111 | Lord British's Castle | 2 | 12 | 12 | Potion (3) | 6 | One-shot | one Black potion (potion id 6) | `A black potion!` |
| 112 | Lord British's Castle | 2 | 12 | 12 | Scroll (4) | 7 | One-shot | one Negate Time scroll (scroll id 7) | `A scroll: AT!` |

**Shared cells.** *(Added 2026-10-25, issue #300 Q1.)* Several records share a
cell: records 0 to 11 (the Underworld lava-pool cell), 43 and 45, 81 and 86, 82 and 85, 94 and
95, and 111 and 112. One Search stages at most one record: the first record in
table order on that cell that is not yet found. On a two-record cell the first
Search therefore stages the lower-numbered record, the second Search stages the
other, and a third prints `nothing of note.`. On the twelve-record cell each
further Search stages the next record in turn, so the third stages record 2
(`some armour!`); executed on the original *(corrected 2026-10-30, issue #314
Q2: this was conditional on the cell being reachable, R659)*. Each staged record takes the
lowest empty active-object slot, so both objects of a two-record cell can sit on
the cell together, and Get takes the first acceptable one in slot order.

**Body cells with an item.** On the three cells where a rotting body shares the
cell with an item (Yew 43 and 45, West Britanny 81 and 86, West Britanny 82 and
85), Get skips the body and takes the item, printing `Spear!`,
`Ring of Regeneration!` or `A scroll: IMC!` respectively. The body stays on the
cell; a second Get there prints the tile cascade's `Nothing to get!` on ordinary
terrain.

**What a Search at a corrected cell shows.** The record 12 cell in East
Britanny, the record 88 to 90 cells beside it, and the record 68 to 71 cells in
Lord British's Castle are all dresser tiles, so a Search there carries the
dresser location prefix of `systems/commands.md` Section 5.8 before the find:
`In the dresser` ⏎ `thou dost find` ⏎ `a scroll!` (or `some armour!`). A
stock-run check of record 12 would show that transcript, then
`The plans for the HMS Cape!` on Get, while a Search at the old transposed cell
would stage nothing. That run has not been made; it is a confirmation, not a
dependency of the correction.

## 4. Sources

This cleanroom table was derived from private analysis and rewritten as
semantic records. It does not reproduce decompiled source, assembly, raw data
dumps, or private address tables.

- `u5-decomp/functions/SJOG_OVL/`.
- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-spec/catalogs/gazetteer.md`.

- The found-object vocabulary of Section 2.1, its four unreachable names and the
  capitalised no-result line — private analysis in `u5-decomp/notes/` and
  `u5-decomp/functions/SJOG_OVL/`, issue #262 follow-up, 2026-09-12.
- The X/Y correction, the grant rule and the per-record grants and Get lines of
  Section 3, and the shared-cell rules (issue #300 Q1, 2026-10-25): private
  analysis in `u5-decomp/notes/` and `u5-decomp/functions/SJOG_OVL/`. The
  transposition was established three ways: a static reading of the original
  Search's coordinate comparison and of Get's matching test; the shipped map
  data, in which the corrected cells of records 12, 68 to 71 and 88 to 90 all
  hold the dresser tile while the transposed cells hold unrelated tiles; and a
  row-by-row comparison showing every row with X different from Y exactly
  transposed, with location, floor, class and state agreeing on all 113 rows.
  The grants and Get lines come from executed original code: the original
  treasure scan followed by the original Get, inventory-add dispatcher, slot
  initializer and capped adders, with the text sink, number printer and font
  switch captured and the tile-interaction gate (forced to pass), the live-tile
  read, the NPC-occupancy test and the slot acquirer stubbed; the acquirer stub
  reproduces the original lowest-empty-slot rule, checked statically. The scan
  was run directly rather than through the whole Search command, so the
  location prefix above is from the published prefix table and the map data,
  not from that run. For the second record of each shared cell (records 1, 3, 5,
  7, 9, 11, 45, 85, 86, 95 and 112) the row comes from the sequential-Search runs
  or from decoding the class and state, not from a run of that record alone.
  The 9999 food cap, the shared gem/torch adder with its 99 cap and the
  above-127 odd-key test were confirmed by static reading. Re-run by an
  independent verifier.
- Records 0 to 11 on the Underworld cell of Section 2.1 (issue #314 Q2,
  2026-10-30): private analysis in `u5-decomp/notes/` and
  `u5-decomp/functions/SJOG_OVL/`. The record values were read from the shipped
  shared data overlay; the exact four-field match, the scan's start at record 0
  with extra conditions only on records 13 to 15, and the scan's place in the
  surface Search cascade are static reading; the three Searches, the Get line
  and the inventory and found-bit changes were executed on the stock game under
  DOSBox and checked against the screen and the saved game afterwards; the lava
  pool, the pocket and its enclosure were read from the shipped Underworld map.
  Re-checked by an independent verifier. The Mystic Sword grant of the odd
  records is static, and runtime writers to the record arrays were not
  enumerated.
