# SAVED.GAM

## 1. Overview

`SAVED.GAM` is the on-disk image of an Ultima V save. It is fixed at four thousand one hundred ninety-two bytes, holds no header or magic number, carries no version word, and pretends to no record-by-record structure. What the file *is*, structurally, is a verbatim memory dump: a contiguous slab from the engine's data segment, written and read in one operation. Live state and save state are the same bytes; a save is the act of flushing them.

Everything described below is therefore a *layout* rather than a *protocol*. Each field has a fixed location, fixed width, and fixed meaning. There are no length prefixes, no string terminators that must be honoured, no padding the writer can vary, and no out-of-line storage — strings are fixed-width, arrays are inline, and records are packed back-to-back at known offsets. An implementation that wants to read or write a byte-compatible `SAVED.GAM` works at the level of "which byte holds which field," nothing more.

The save is paired with three companion files. `SAVED.OOL` holds five hundred twelve bytes of active-object state for both world planes - the part of the runtime cast that lives outside the save image. `BRIT.OOL` and `UNDER.OOL` ship as seeds for those tables and are mirror-written by the load path; the save path reads them instead, and writes `UNDER.OOL` back out only when it entered with a disk-prompt mode other than mode 1. The save and load semantics are described in `systems/save-load.md`; this spec covers the byte layout of `SAVED.GAM` itself, with `SAVED.OOL`/`BRIT.OOL`/`UNDER.OOL` covered where the two formats touch (Section 13).

A second seed file, `INIT.GAM`, carries the identical layout. It is a frozen "first save" the chargen flow clones into `SAVED.GAM` for new games. It is read-only at runtime, byte-for-byte identical to `SAVED.GAM` on a clean install, and obeys every layout statement made about `SAVED.GAM` below.

All offsets in this spec are file-relative, given as hexadecimal addresses from the start of the file. Multi-byte integer fields are unsigned and little-endian unless noted otherwise. Unused fields are zero.

## 2. Top-level layout

The four-thousand-one-hundred-ninety-two-byte file contains a set of persistent
regions and save-backed resident views. Most rows below are contiguous regions;
the inn-guest registry is a legacy view with character-record stride that
overlaps adjacent save bytes and should not be treated as an independent block
after the roster.

| Region                              | Offset range          | Size        | Section |
|-------------------------------------|-----------------------|-------------|---------|
| Leading save-image bytes            | `0x0000` – `0x0001`   | 2 bytes     | 2       |
| Character roster (16 × 32 bytes)    | `0x0002` – `0x0201`   | 512 bytes   | 3       |
| Inn-guest registry (16 × 32 bytes)  | `0x0021` – `0x0220`   | 512 bytes   | 3.3     |
| Inventory and consumables           | `0x0202` – `0x02A9`   | ~168 bytes  | 7       |
| Moonstone gate slots                | `0x028A` – `0x02A9`   | 32 bytes    | 7.2     |
| Reagents (8 bytes)                  | `0x02AA` – `0x02B1`   | 8 bytes     | 7       |
| Party size                          | `0x02B5`              | 1 byte      | 4       |
| Calendar (year/month/day/hour/min)  | `0x02CE` – `0x02DE`   | ~17 bytes   | 5       |
| Party status / active-player bytes  | `0x02D4` – `0x02D6`   | 3 bytes     | 4       |
| Food gauge / mode scratch           | `0x02DF` – `0x02EB`   | 13 bytes    | 10      |
| — of which: moongate presence phase | `0x02E1`              | 1 byte      | 10      |
| Wind state                          | `0x02EC`              | 1 byte      | 6       |
| Scene byte and saved-scene scratch  | `0x02ED` – `0x02EE`   | 2 bytes     | 6, 10   |
| Party position (z/x/y)              | `0x02EF` – `0x02F1`   | 3 bytes     | 6       |
| Per-turn flags and combat scratch   | `0x02F2` – `0x0325`   | ~52 bytes   | 10      |
| Quest progress bitmasks             | `0x0326` – `0x0328`   | 3 bytes     | 9       |
| Tail of resident state              | `0x0329` – `0x03B3`   | ~139 bytes  | 10      |
| Dungeon room-clear bitmap           | `0x033A` – `0x0349`   | 16 bytes    | 10      |
| Active map / dungeon tile buffer    | `0x03B4` – `0x05B3`   | 512 bytes   | 8.2     |
| Per-location NPC bitmasks (removed, then name-known) | `0x05B4` – `0x06B3` | 256 bytes | 9.2 |
| Active-object table (32 × 8 bytes)  | `0x06B4` – `0x07B3`   | 256 bytes   | 8.1     |
| Reserved / NPC and tile scratch     | `0x07B4` – `0x105F`   | 2,220 bytes | 12      |

The two leading bytes precede the roster in the resident save image. They are
zero in the factory seed and should be preserved by byte-compatible tools.

The inn-guest registry is a save-backed resident view with the same thirty-two-byte stride as character records. Its overlap with the canonical roster and adjacent inventory range is intentional: the inn helper reads this shifted view as a sixteen-slot guest table, not as ordinary padding. Treat the range as owned by the inn helper when reproducing inn behaviour, and preserve it byte-for-byte in compatible save tools unless intentionally implementing the inn flow. The factory-seed `INIT.GAM` is zero in every region whose value depends on play; only the roster records, starting inventory, starting date/location, weather, and a small set of control bytes carry non-zero values out of the box.

The next several sections describe each region in detail. The byte-offset
tables are exhaustive for the regions whose contents have been verified
directly. Some mixed runtime-state bands are intentionally preserved as opaque
bytes where only their owning system, not every bit-level subfield, is known.

## 3. Character roster

The party roster begins two bytes into the file and holds sixteen records of thirty-two bytes each, packed back-to-back, no separator. Record zero is the Avatar. In the factory seed, records one through fifteen hold the canonical companion list — Shamino, Iolo, Mariah, Geoffrey, Jaana, Julia, Dupre, Katrina, Sentri, Gwenno, Johne, Gorn, Maxwell, Toshi, and Saduj — in that order, and those companions exist in the roster from the moment a new game starts whether or not they have been recruited. During play, the travelling party order is represented by the order of the first `party-size` records: New Order can exchange any two active non-leader records as whole thirty-two-byte records. Slots beyond the party-size index hold characters who exist in Britannia but are not currently travelling with the player.

### 3.1 Record layout

Each thirty-two-byte record is laid out as follows.

| Field offset | Width    | Meaning                                                                                                  |
|--------------|----------|----------------------------------------------------------------------------------------------------------|
| `0x00`       | 9 bytes  | Name. ASCII, NUL-padded. The first character is the leading byte of the record and may be zero on an unused slot. |
| `0x09`       | 1 byte   | Gender. `0x0B` for male, `0x0C` for female. Not ASCII; the values are private to the engine.             |
| `0x0A`       | 1 byte   | Class. ASCII letter — `'A'` Avatar, `'B'` Bard, `'F'` Fighter, `'M'` Mage, `'D'` Druid, `'T'` Tinker, `'P'` Paladin, `'R'` Ranger, `'S'` Shepherd. |
| `0x0B`       | 1 byte   | Status. ASCII letter. Shipped new-game and gameplay paths write `'G'` good/alive, `'P'` poisoned, `'S'` sleeping, and `'D'` dead. `'C'` charmed is a stats-panel display override, not a stored status. `'A'` ashes is accepted and preserved when already present in an external, edited, or legacy U5 save, but no shipped path produces it. |
| `0x0C`       | 1 byte   | Strength.                                                                                                |
| `0x0D`       | 1 byte   | Dexterity.                                                                                               |
| `0x0E`       | 1 byte   | Intelligence.                                                                                            |
| `0x0F`       | 1 byte   | Magic points (current).                                                                                  |
| `0x10`       | 2 bytes  | Hit points current. Little-endian word.                                                                  |
| `0x12`       | 2 bytes  | Hit points maximum. Little-endian word.                                                                  |
| `0x14`       | 2 bytes  | Experience points. Little-endian word.                                                                   |
| `0x16`       | 1 byte   | Level. Every shipped seed record carries a real level in the range 1..5, and across all sixteen seeds the value is maximum hit points divided by thirty. Earlier wording calling `0xFF` an unset / not-yet-computed level here is **withdrawn**: no shipped record carries `0xFF` in this byte, and the `0xFF` unset sentinel of a seed record sits in the per-character month counter at `+0x17`. |
| `0x17`       | 1 byte   | Per-character month counter. The time system increments every character-record slot at the 28-day month rollover, capped at 25. The traced gameplay consumer is inn billing for lodged guest records; no separate active-party consumer is identified. |
| `0x18`       | 1 byte   | Party-member combat defense byte used by the combat damage path's random defense subtraction. Factory-seed records carry value `7`; no traced writer currently recomputes this byte from readied equipment. |
| `0x19`       | 6 bytes  | Equipment slot bytes: helm, body armour, weapon hand, shield/off hand, ring, and amulet/neck item. Each non-empty slot byte is an equipment item id (see Section 7). The live empty-slot sentinel is `0xFF`. |
| `0x1F`       | 1 byte   | Inn-registry marker byte when this record is viewed through the shifted inn guest table; zero for an empty/cleared guest marker. Opaque padding for ordinary active-character behaviour. |

The name is NUL-padded rather than NUL-terminated. A nine-byte slot can hold a nine-character name with no terminator at all, and shorter names are padded with zero bytes. Players who entered an empty name will see all nine bytes of zero. The engine's empty-save guard (see `systems/save-load.md`) tests the first byte of record zero's name field. In file-relative terms that byte is `0x0002`, because the roster begins after the two leading save-image bytes.

### 3.2 Roster invariants

Three invariants are worth flagging. Slot zero is structurally the Avatar: chargen writes only into slot zero, New Order refuses to move slot zero, and other gameplay code keys "is this character the player?" off slot index, not record contents. Non-leader companion slots are not immutable once play begins; New Order swaps entire active records, so the current non-leader marching order is the current record order rather than a permanent factory-slot identity. The class letter at `+0x0A` moves with its record: a save with no companions recruited still lists all sixteen seed records with their classes, but after New Order the active non-leader slot that holds a given companion also holds that companion's class, status, stats, equipment, and per-record counters.

The gender byte at `+0x09` is not ASCII, but the class and status bytes at `+0x0A` and `+0x0B` are: visual inspection of a save will see, for the recruited Avatar, a record whose tenth and eleventh bytes look like `'A' 'G'` for "Avatar class, alive". Earlier external references that swap the gender and class positions are wrong: the order is gender-then-class-then-status. Because the roster starts at file offset `0x0002`, the Avatar's class and status bytes are file offsets `0x000C` and `0x000D` respectively.

The status byte is separate from the class byte. In particular, status `'P'`
does not mean class Paladin; Paladin is class `'P'` at `+0x0A`. Status `'P'`
means poisoned, and only that. Earlier drafts of this document described a
revive-style helper that writes `'P'` when transitioning a dead slot back to a
live state; that reading is retracted. The helper in question is a poison
primitive: it skips a member marked `'D'` and stamps `'P'` on **every other**
status, so no path in the game moves a character from `'D'` to `'P'`, while a
member holding any other letter is overwritten with `'P'`. (An earlier revision
said the helper "stamps `'P'` on living members only", which reads as though it
distinguishes living members from otherwise-incapacitated ones. It does not;
that wording is withdrawn. The full contract is in `systems/traps.md` § 3.)
Compatible tools should still preserve the raw status letter.

**`'C'` is not a stored status, and `'A'` has no shipped producer.**
*Corrected:* an earlier revision of the `+0x0B` row listed `'C'` charmed and
`'A'` ashes among the byte's gameplay-produced values. That wording is
withdrawn.

- `'C'` charmed is a **presentation override**. During combat-class scenes the
  stats-panel row builder substitutes the literal `C` for display when the
  per-combatant controlled/charmed descriptor bit is set for that slot, and
  otherwise prints the raw status byte; the Charm spell writes `'G'`, never
  `'C'`, into a party target's status byte. `systems/combat.md` Section 6.1a
  owns that rule, and this row now agrees with it rather than contradicting it.
- `'A'` ashes has **no producer in the shipped game**. The factory image starts
  all sixteen roster slots at Good. Character creation retains Good, and the
  Ultima IV transfer path assigns Good rather than importing its source status.
  The complete gameplay-writer census found only Good, Poisoned, Sleeping, and
  Dead assignments; death has no cause-specific Ashes branch. Save/load, New
  Order, inn storage, recruitment, and other whole-record copies can preserve
  an already-present byte but do not synthesise one.

The earlier immediate-operand scan was independently repeated on 2026-08-23 by
exhaustively enumerating every encoding of the immediate-operand compare and
store forms with a memory operand, over the executable, every overlay and every
driver, which unlike a linear sweep cannot lose synchronisation on embedded data
and silently skip real instructions. It reached the same result: no compare
against the ashes letter and no store of it anywhere in the status band, and the
only write of that letter value into a party record at all is into the **class**
field during character creation, one byte away from the status field. That is
corroborated by the broader writer and whole-record dataflow census.

An external, edited, or legacy U5 save may nevertheless contain `'A'`, because
the engine loads and saves the image verbatim. Preserve and round-trip that
value. Its existing consumers remain normative: Resurrection requires exactly
Dead and therefore refuses an Ashes target, while the shared poison helper
skips exactly Dead and therefore overwrites Ashes with Poisoned. Do not infer a
producer from those consumer behaviours, and do not invent one. Ultima IV
transfer is specifically not an import route for Ashes because it forces Good.

### 3.3 The inn-guest registry

A second sixteen-by-thirty-two-byte guest-table view sits in the resident save image. The inn-guest registry stores a copy of each character record that is currently checked into one of the in-world inns. Each guest entry uses the same stride and record-shaped payload as a character record, but it is not a second ordinary roster: the leading byte of each registry slot is an inn-scene marker used to decide whether the guest belongs to the inn currently being visited. The registry interpretation is opaque to other gameplay systems; only the inn helper is known to read or write the scene marker as guest state. It survives saves because it lives inside the resident state region. Leave initializes the guest's stored stay counter to zero; the time system increments that shared character counter on each 28-day month rollover, capped at 25; pickup treats a zero counter as one billable unit and clears the returned slot's marker to zero after moving the guest back into the active roster. Active and non-lodged records age the same byte, but current traced readers do not give those aged values a separate effect.

## 4. Active player and party

A handful of bytes later in the save image track party control state, transport/status presentation, and who is currently the "active" character — the one whose stats appear in the side panel and who issues player-controlled commands.

| Offset   | Width  | Field                  | Meaning                                                                                                        |
|----------|--------|------------------------|----------------------------------------------------------------------------------------------------------------|
| `0x02B5` | 1 byte | Party size             | Number of slots `1..6` that are currently in the travelling party. Iteration cap for any "for each party member" pass, and one of the inputs to inn rest quotes and pickup capacity checks. |
| `0x02D4` | 1 byte | Timed magic-effect code | The single shared timed-magic-effect slot specified in `systems/magic.md`: it names the one magic effect, scroll effect, or worn regalia aura currently active, and zero means none. The stats panel draws the code as its bottom glyph when nonzero, and the time cleanup reads the Quickness and Negate Time codes as timing modifiers. Not a boarded-vehicle enum of any kind. |
| `0x02D5` | 1 byte | Active player index    | Slot index `0..7` of the currently selected character. `0xFF` for "none selected" (overworld default).         |
| `0x02D6` | 1 byte | Transport/action marker | Avatar or vehicle transport/action marker. B-Board writes this when the party boards horses, carpet, skiffs, or ships; other systems also mask it for light-source and alternate-turn presentation states. |
| `0x02E8` | 1 byte | Timed magic-effect duration | Remaining world turns for the effect at `0x02D4`. `0x00` is inert and `0xFF` is the permanent sentinel used by the Amulet of Lord British, Crown of Lord British, and Black Badge. |

The active-player byte is `0xFF` in the overworld and is set to a slot index when the player picks a character (typically on town entry, or at the start of a combat round). Town and combat modes update it as the player navigates; saving and loading preserves it as-is. The party-size field is the iteration cap that every "for each party member" pass uses; it is the number of records at the front of the roster that hold travelling characters, not the size of the roster (which is always sixteen), and not an inn-stay or calendar counter. New Order changes which active non-leader records occupy those front-of-roster positions, but it does not change party-size.

The `0x02D4` and `0x02D6` bytes are deliberately separated here because they are unrelated fields. The byte at `0x02D4` is the timed magic-effect code: the timing system reads its Quickness and Negate Time values as minute-increment modifiers, and the stats panel draws the same code directly in the bottom glyph slot when it is nonzero. Its paired remaining-duration counter is the non-adjacent byte at `0x02E8`. Regalia installation writes the item's exact code (`0x0E`, `0x1C`, or `0x1D`) at `0x02D4` and permanent sentinel `0xFF` at `0x02E8`; re-using the same worn item clears both bytes. The boarding and dismount paths manipulate the transport/action marker, and the stats panel also reads that marker to choose the ship-hull middle-counter presentation when the marker is in the ship family `0x20..0x27`. Marker values outside that ship family do not select the stats-panel hull counter. A compatible save reader should preserve all three bytes exactly even if its own engine keeps cleaner internal models.

Known `0x02D6` families and ranges are documented in `systems/vehicles.md`:
mounted horse, carpet, foot/avatar, ship under sail, furled ship, and skiff.
Byte-compatible readers must preserve unrecognized marker values; deterministic
engines can map recognized families to semantic transport, facing, and sail
state internally.

## 5. Calendar and clock

The world clock lives in a small group of bytes shared with movement, mode, combat, and display bookkeeping (see `systems/time.md`). All five calendar fields are persisted directly; loading restores the clock to the exact instant of the save. Adjacent bytes in the same span are persistent engine state too, but they are not calendar fields.

| Offset | Width | Field | Meaning |
|--------|------:|-------|---------|
| `0x02CE` | 2 bytes | Year | In-world year. Little-endian word. |
| `0x02D0..0x02D3` | 4 bytes | Focus/direction scratch | Owned by movement, combat, look, and cutscene callers; preserve on round trip. |
| `0x02D4` | 1 byte | Timed magic-effect code | Read by the time cleanup for its Quickness and Negate Time values; owned by `systems/magic.md`. |
| `0x02D5` | 1 byte | Active-player slot | Not clock state. |
| `0x02D6` | 1 byte | Transport/action marker | Not clock state. |
| `0x02D7` | 1 byte | Month | One-based, range `1..13`. |
| `0x02D8` | 1 byte | Day | One-based, range `1..28`. |
| `0x02D9` | 1 byte | Hour | Zero-based, twenty-four-hour, range `0..23`. |
| `0x02DA` | 1 byte | Saved-hour snapshot | Used by the time cleanup to detect hour crossings. |
| `0x02DB` | 1 byte | Minute | Range `0..59`. |
| `0x02DC` | 1 byte | Combat round counter | Combat advances time when this counter wraps. |
| `0x02DD` | 1 byte | Adjacent per-turn state | Preserve byte-for-byte; no public calendar meaning. |
| `0x02DE` | 1 byte | 12-hour display | Display-hour value derived from the hour and recomputed on hour changes. |
| `0x02E8` | 1 byte | Timed magic-effect duration | Paired with the effect code at `0x02D4`; not clock state. `0xFF` means permanent. |

The cascade rules - minute to hour to day to month to year - are described in detail in `systems/time.md`. From this spec's perspective the calendar fields are simple little-endian unsigned integers in fixed ranges; the neighbouring bytes are separate save-backed state.

## 6. Scene and party position

The five bytes after wind form the persisted location cluster: active scene, saved-scene / mode scratch, and party Z/X/Y. Scene byte and party Z together pin which map (overworld, underworld, named town, dungeon level) the party occupies; party X and Y give the cell within that map. The scratch byte sits inside the same cluster and must round-trip exactly, but it is not a coordinate. These fields are read by the post-load mode dispatcher to decide which gameplay overlay to bring up.

| Offset   | Width  | Field        | Meaning                                                                                                                     |
|----------|--------|--------------|-----------------------------------------------------------------------------------------------------------------------------|
| `0x02EC` | 1 byte | Wind         | Wind state byte. Values `0..4` map to Calm, North, South, East, and West as specified in `systems/weather.md`; the byte drives the overworld wind banner, Rel Hur state, hoisted-sail player-ship cadence, and non-player water-creature/pirate active-object cadence. Preserve unrecognised values exactly for round-trip writes rather than clamping them. |
| `0x02ED` | 1 byte | Scene        | Active map. `0x00` overworld, `0x01..0x20` named town/castle/keep/dwelling, `0x21..0x7F` dungeon-class range (stock dungeons use `0x21..0x28`), `0xFF` transient combat-class marker. Values `0x40..0x42` are intro/Return-to-View states and should not appear in an ordinary gameplay save. |
| `0x02EE` | 1 byte | Saved scene / mode scratch | Adjacent mode scratch byte. Combat entry uses it to save the pre-combat scene for later restore; other mode code may reuse it as transition or redraw state. Preserve exactly and do not treat it as a party coordinate. |
| `0x02EF` | 1 byte | Party Z      | Signed byte whose meaning is selected by the scene byte. On the overworld it is the world plane: `0x00` Britannia, `0xFF` Underworld. Inside a town-family location it is the floor index added to that location's base map page: `0x00` is the entry floor, positive values are storeys above it, `0xFF` is a basement (`formats/location-dat.md` Section 4). In a dungeon it is the level index, zero at the top. Earlier wording calling `0xFF` a "no active map" sentinel is withdrawn: `0xFF` is a real, reachable value in two of the three roles. |
| `0x02F0` | 1 byte | Party X      | Cell column on the active map.                                                                                              |
| `0x02F1` | 1 byte | Party Y      | Cell row on the active map.                                                                                                 |

The scene byte is the most-cited field in the entire save image: every gameplay dispatch keys off its value. The post-load reader inspects scene and party Z together to decide whether to enter the surface overworld, the underworld overworld, a named indoor scene, or a dungeon. The stable party-position tuple is therefore scene plus Z/X/Y; `0x02EE` is persisted mode scratch next to that tuple.

## 7. Inventory and consumables

A long band of bytes after the inn-guest registry holds the party's shared inventory. Most fields are single bytes; a few are little-endian words for counters that exceed two hundred fifty-five.

| Offset   | Width   | Field              | Meaning                                                                                                       |
|----------|---------|--------------------|---------------------------------------------------------------------------------------------------------------|
| `0x0202` | 2 bytes | Food               | Little-endian word. Not touched by the per-turn clock cleanup: the separate party status/provision pass subtracts the eating-member count from it on an hour change, and only at 06:00, 12:00, and 18:00 (`systems/time.md` Section 5). Grants cap it at 9999.                                         |
| `0x0204` | 2 bytes | Gold               | Little-endian word. Range `0..9999` in normal play.                                                           |
| `0x0206` | 1 byte  | Keys               | Skeleton keys carried.                                                                                        |
| `0x0207` | 1 byte  | Gems               | Vision gems.                                                                                                  |
| `0x0208` | 1 byte  | Torches            | Torches.                                                                                                      |
| `0x0209` | 1 byte  | Grapple / legacy magic-powder byte | Traced gameplay reads this byte as the outdoor Klimb gear gate: Lord Michael's conversation grant sets it, and overworld K-Klimb refuses without it. Older references label the same byte magic powder; no separate magic-powder consumer is currently traced. |
| `0x020A..0x0219` | 16 bytes | Special / quest items | One-byte counters or flags for carried/useable special items. Confirmed members include Magic Carpet at `0x020A`, skull/special key stock at `0x020B`, Amulet/Crown/Sceptre of Lord British at `0x020D..0x020F`, shard flags at `0x0210..0x0212`, Spyglass at `0x0214`, HMS Cape plans at `0x0215`, Sextant at `0x0216`, Pocket Watch at `0x0217`, Black Badge at `0x0218`, and the Wooden/Sandalwood Box story flag at `0x0219`. The byte at `0x0219` is the save-backed box flag: item acquisition sets it and the endgame reads it. **`0x020C` is not a carried-item counter**: it is the fixed hidden-treasure daily cooldown cookie described in Section 10, and it happens to live in this band. Other individual meanings remain cross-system. |
| `0x021A..0x0249` | 48 bytes | Equipment inventory | One byte per equipment item id. Arms shops, Z-stats, and R-Ready use the same id to index the shop stock table, base-price table, display-name row, carried counter, and readied-equipment slot value. The span covers ammunition and carried weapons/armour/helms/shields/rings/amulets. |
| `0x024A..0x0279` | 48 bytes | Spell-charge stock | One byte per pre-mixed spell charge. See Section 7.1.                                                         |
| `0x027A..0x0281` | 8 bytes | Scroll counters | One byte per usable scroll row, in the same order as the U-Use scroll dispatch: `LV`, `HR`, `IS`, `AI`, `IQW`, `CKX`, `CIM`, `AT`. |
| `0x0282..0x0289` | 8 bytes | Potion counters | One byte per potion row, in display order: Blue, Yellow, Red, Green, Orange, Purple, Black, White. |
| `0x02AA` | 8 bytes | Reagents           | Black pearl, blood moss, garlic, ginseng, mandrake, nightshade, spider silk, sulfurous ash. One byte each.    |

The inventory region holds two-byte words for the two counters that need them (food and gold) and single bytes for everything else. Carry caps are enforced by the gameplay code; the save format places no upper bound, and an editor that sets values past the in-game maximum will produce a save the engine will read but that may behave oddly on display or arithmetic. The arms-shop equipment block is item-id keyed: item id `N` reads or writes byte `0x021A + N`. Ordinary equipment grants increment that byte and cap it at ninety-nine.

Two entries in these two bands are read by systems outside inventory, and an
implementation that gives them private storage will diverge:

- `0x0206` (Keys) is also the gate for fixed hidden-treasure record 13.
- `0x0241` — the equipment counter for item id `39`, the Glass Sword — is also
  the gate for fixed hidden-treasure record 15. It is the same byte, not a
  parallel cookie. See Section 10.

The reagent block is small enough to enumerate as a fixed eight-byte record at `0x02AA`. The order matches the in-world spell-mixing UI, with black pearl in the first byte and sulfurous ash in the last. The block is exactly eight bytes: the three bytes immediately after it are the rare-reagent harvest cooldown cookies described in Section 10, not a ninth through eleventh reagent.

### 7.1 Spell-charge stock

A separate block of forty-eight bytes at file offset `0x024A` holds the
per-spell pre-mixed charge stock. Each entry is a byte counter for how many
doses of that spell the player has mixed in advance. Normal play keeps the
counter in the range `0..99`: `M`/Mix adds the requested quantity after a
matching recipe and caps the stored counter at 99, while `C`/Cast decrements
the selected spell's counter immediately after the nonzero-stock gate.

The stock block is indexed by the canonical engine spell id documented in
`catalogs/spell-list.md`: spell id `0` reads byte `0x024A`, spell id `1` reads
byte `0x024B`, and so on through spell id `47` at byte `0x0279`. The same id is
returned by the player spell-token parser used by both `C`/Cast and `M`/Mix,
and the same order keys the public spell recipe and scene-mask metadata.

An empty inventory has all forty-eight bytes zero. The same region serves the
player spell table only; chant-driven shrine quests, Codex urn reading, and
monster special abilities do not use these counters.

### 7.2 Moonstone gate slots

Thirty-two bytes at `0x028A..0x02A9` hold the eight saved Moonstone
destinations used by *Vas Rel Por* / Gate Travel, Search/Get recovery, the
natural moongate live-tile refresh, and ordinary natural-gate entry warps. The
layout is four parallel eight-byte
arrays:

| Offset range | Width | Meaning |
|--------------|-------|---------|
| `0x028A..0x0291` | 8 bytes | Destination X, one byte per moonstone slot. |
| `0x0292..0x0299` | 8 bytes | Destination Y, one byte per moonstone slot. |
| `0x029A..0x02A1` | 8 bytes | Destination scene byte. `0xFF` means the slot is not a valid Gate Travel target. |
| `0x02A2..0x02A9` | 8 bytes | Destination Z / floor byte. |

The spell prompt's digits `1` through `8` select these slots directly. The
Use-item Moonstone action selects the same slot numbers: a successful bury
records the party's current scene, X, Y, and Z/floor into the chosen slot.
Burying is accepted only outside dungeon/combat scenes and only when the tile
under the party is one of these world-tile ids: `4..10`, `44`, or `45`.

Recovery is Search/Get driven rather than a direct spell action. Non-dungeon
Search compares the target coordinate against all valid saved Moonstone slots.
When a slot matches, the engine creates a visible "strange rock" pickup tagged
with that slot. Collecting that pickup grants the Moonstone and invalidates the
slot by writing the invalid scene sentinel, so later Gate Travel casts to that
slot fail instead of moving the party. If multiple Moonstone slots name the
same coordinate, Search considers the highest-numbered matching slot first and
prevents duplicate visible rocks for a slot that has already been surfaced.

## 8. Map Buffer And Active Objects

### 8.1 Active-Object Table

Two hundred fifty-six bytes at file offset `0x06B4` hold the active-object table — the engine's runtime cast on the player's current map, described in detail in `systems/active-objects.md`. The table is thirty-two records of eight bytes each.

| Field offset | Meaning                                                                                                                                    |
|--------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `+0x00`      | Tile / type byte. Zero on an unused slot. Non-zero is a tile class (see `systems/active-objects.md`).                                      |
| `+0x01`      | Per-frame tile byte. Updated by the per-tick animator.                                                                                     |
| `+0x02`      | Cell X coordinate.                                                                                                                         |
| `+0x03`      | Cell Y coordinate.                                                                                                                         |
| `+0x04`      | Floor / Z coordinate. `0xFF` is the "above-ground / no z" sentinel for surface objects.                                                    |
| `+0x05`      | Auxiliary byte. For frigates this is the hull's hit-point count; for other vehicles it carries class-specific state.                       |
| `+0x06`      | Auxiliary byte. Animation phase / direction-step counter; compositor reads it for water creatures.                                         |
| `+0x07`      | Auxiliary byte. For frigates this counts skiffs aboard; for other classes carries hit points or other class-specific state.                |

Slot zero is the player. Slots one through thirty-one hold any other on-map cast — vehicles parked or in motion, NPCs that have stepped onto the player's floor, dropped items, summoned creatures, and so on. Most saves zero out most slots; the canonical seed save has the entire region zero. Any pre-placed objects a fresh game starts with come from the per-plane object overlays rather than from the save image, and in the shipped data those are underworld objects: the surface overlay ships empty (Section 13).

The active-object table in the save image is the snapshot of the live global table at flush time. In top-down scenes this is the player's current map cast: overworld and underworld saves hold vehicles, dropped objects, and spawned creatures; town, castle, keep, and dwelling saves hold the on-floor NPC/object cast. Dungeon exploration does not use this table as its first-person actor list, so dungeon saves preserve the global table as ambient state rather than as dungeon-renderer contents. Saves taken in combat are not supported: the gameplay loops do not honour `Q` mid-combat, and the combat framer's temporary combat table is restored before control returns to a saveable loop.

### 8.2 Dungeon / Map-Cell Working Buffer

The 512-byte region at file offset `0x03B4..0x05B3` is the saved part of the
dungeon/map-cell working image. In a dungeon scene it holds the selected
512-byte dungeon record currently being played, including visit-local edits
such as opened doors, dispelled fields, trap rewrites, and immediate
room-trigger patches.

The size is exactly one dungeon record and no more: a dungeon record is the
eight levels of one dungeon, each an eight-by-eight grid of cells, one byte per
cell, so the working buffer is exactly one of the eight records in the shipped
dungeon file. Private descriptions that gave this buffer a two-kilobyte or
four-kilobyte extent are wrong; a larger extent would overrun the per-location
NPC bitmask tables of Section 9.2, which begin immediately afterwards.

This region is saved because `SAVED.GAM` is a flat runtime image. It should not
be interpreted as a cumulative automap or "all dungeons explored" record. On a
fresh entry into a scene, the engine can rebuild the buffer from the static map
files plus durable state such as the room-clear bitmap. On a byte-compatible
save/load round trip, however, the bytes themselves are preserved exactly, so a
save made inside a dungeon can resume with that dungeon's current working
buffer. Town and other 32-by-32 location floors use a separate runtime tile
buffer outside this file range; they are rebuilt from their location data and
mode state on load.

## 9. World flags

The save image carries shrine progress masks plus other save-backed quest and
NPC interaction facts for cross-session world state.

### 9.1 Quest progress

Shadowlord and shrine quest progress live in several small save-backed fields in
the resident image.

| Offset   | Width  | Field            | Meaning                                                                                                                       |
|----------|--------|------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `0x0322..0x0324` | 3 bytes | Shadowlord hideout / vanquished slots | Slot order is Falsehood/Faulinei, Hatred/Astaroth, Cowardice/Nosfentor. `0` means "not yet placed" and is the factory value for all three slots; `1..8` is the **town scene byte** of the town currently hosting that Shadowlord; successful shard/flame destruction writes `0xFF`. Doom entry and Shadowlord spawn/report paths treat high-bit-set values as vanquished. |
| `0x0325` | 1 byte | Active Shadowlord id | Runtime handshake set by the Shadowlord-name Yell path and checked by shard/spell destruction. Values `0..2` identify the active named Shadowlord. The factory value is `0xFF`, meaning "none active"; preserve other values byte-for-byte. |
| `0x0326` | 1 byte | Ordained mask    | Bit per virtue: 0 Honesty, 1 Compassion, 2 Valor, 3 Justice, 4 Sacrifice, 5 Honor, 6 Spirituality, 7 Humility. Bit set = "ordained, must visit Codex". |
| `0x0328` | 1 byte | Codex-visited mask | Same eight-bit layout. Bit set = "Codex page read for this virtue".                                                          |
| `0x032A..0x0331` | 8 bytes | Word-of-Power seal flags | One byte per Word of Power, in the fixed word order Deceit, Despise, Destard, Wrong, Covetous, Shame, Hythloth, Doom. Zero means the word has not been spoken and that dungeon's entrance is sealed; a successful utterance toggles the byte's high bit. Region loading re-derives the sealed entrance tile from these flags, so they are the durable "dungeon opened" state, not scratch. Factory: all zero. See `systems/commands.md` Section 11. |
| `0x0332..0x0339` | 8 bytes | Shrine ruin flags | One byte per shrine, in shrine order. A high-bit-set byte makes that shrine render and behave as a ruined shrine when its region is loaded. Factory: all zero. |
| `0x0624..0x0625` | 2 bytes | *(not a quest word -- see below)* | These two bytes are **not** an independent quest-progress field. They are the low half of Stonegate's entry in the removed-NPC bitmask table of Section 9.2. Successful Shadowlord destruction sets the bit for that Shadowlord's NPC roster slot in Stonegate, which is what keeps the vanquished Shadowlord from being placed there again: roster slot 1 for Falsehood/Faulinei, slot 2 for Hatred/Astaroth, slot 3 for Cowardice/Nosfentor. Preserve the whole four-byte slot, and read it as a removal mask, not as a quest bitfield. |

The two bitmasks together encode a four-state virtue quest: not started (both zero), ordained (ordained set, codex clear), codex-read (both set), complete (ordained clear, codex set — the ordained bit is cleared on shrine turn-in). All eight virtues use the same encoding, with the same bit-to-virtue map, so the layout is uniform. Ordinary post-completion shrine offerings leave these masks unchanged; they update gold and shrine standing instead.

The Shadowlord slot bytes are the gameplay-visible vanquish state: they gate
Shadowlord re-rolls, name summons, town-entry Shadowlord installation, the
Underworld shard placement, a view-side location marker, Stonegate atmosphere,
and Doom entry. They are **not** read by the Sextant: the Sextant prints the
party's own coordinates and has no Shadowlord readout.

An earlier revision of this spec described the two bytes at `0x0624` as a
save-backed "quest progress" word written alongside the destruction. That
framing is withdrawn. Those bytes lie inside the removed-NPC bitmask table of
Section 9.2, and the write is an ordinary NPC-removal record against Stonegate:
the destruction path marks the vanquished Shadowlord's roster slot in that
location as permanently gone. It is hard-wired there because a Shadowlord's
sprite class is rejected by the general removal filter (see
`systems/town-mode.md`). Shadowlord alive/vanquished state remains owned by the
three dedicated slot bytes above; the removal bit is a placement consequence,
not a second source of truth.

A successful destruction touches one further field: it clears the matching
shard's carried flag in the special/quest-item band (`0x0210..0x0212`, Section
7). The shard is consumed by the act of destroying its Shadowlord. Slot byte,
quest bit, and shard flag are written together in the same success step, so any
save produced after a destruction has all three consistent.

### 9.2 NPC Interaction Boundary

Named-NPC interaction persistence is handled by the quest and NPC-state fields
documented in `systems/quest-flags.md` and `systems/conversation.md`.

The 256-byte block at `0x05B4..0x06B3` is **two back-to-back per-location
bitmask tables**, each thirty-two slots of four bytes, ending flush against the
active-object table at `0x06B4`. Both are indexed by the one-based location id
of a town-mode scene (one through thirty-two), and within a slot the bit number
is the NPC's roster slot in that location, zero through thirty-one:

| Range              | Table | Meaning of a set bit |
|--------------------|-------|----------------------|
| `0x05B4` – `0x0633` | NPC removed | Roster slot *n* is permanently gone from this location and must not be placed on entry. |
| `0x0634` – `0x06B3` | NPC name known | Roster slot *n* has been told the party's name. This is the TALK branch-flag bank of `systems/quest-flags.md` section 3. |

An earlier revision of this section said the trace did not support treating the
span as an NPC flag table and described it as mixed world, quest, and mode
state. That is withdrawn: the decomposition above is exact, the two tables meet
at `0x0634` with no gap, and no other system owns bytes inside the span. What
the earlier caution got right is that neither table is a met/killed table in the
sense external descriptions use — the first is a *placement suppression* mask
written by NPC death and by a small number of scripted world events, and the
second is a conversation memory bit written only by the dialogue name prompt.

The factory seed has all 256 bytes zero. Implementations should still preserve
the span byte-for-byte for save compatibility, and should read the semantics
from the owning system specs rather than inventing per-bit meanings.

### 9.3 Pending shipwright delivery

A purchased watercraft is queued in three save-backed bytes until the next
overworld entry materializes it as an active object. The coordinate pair and
class byte are not contiguous:

| Offset | Width | Field | Meaning |
|---:|---:|---|---|
| `0x03AD` | 1 byte | Pending delivery X | Overworld X coordinate copied from the shipwright row when the delivery is first queued. |
| `0x03AE` | 1 byte | Pending delivery Y | Matching overworld Y coordinate. |
| `0x105F` | 1 byte | Pending acquisition class/payload | Presence, vessel family, and carried-Skiff payload. This is the final byte of the 4,192-byte save image. |

The shipwright produces these canonical class values:

| Class byte | Meaning |
|---:|---|
| `0x00` | No pending delivery. |
| `0x40` | One standalone Skiff. |
| `0x82` | One Frigate carrying two Skiffs. |
| `0x83` | That pending Frigate after one additional Skiff purchase; its delivered carried-Skiff count is three. |

This is a packed byte rather than a closed four-value enum. A value below
`0x40` is inactive. Any value from `0x40` through `0x7F` is consumed as a
Skiff-family delivery; any value from `0x80` through `0xFF` is consumed as a
Frigate-family delivery. The low six bits become the delivered object's
carried-Skiff/class-specific auxiliary count. The shipwright increments the
whole byte for each additional Skiff bought while a Frigate is pending, without
a separate cap, so further successful purchases continue to `0x84`, `0x85`,
and so on.

Loading does not validate or normalize any of these bytes. An otherwise-unused
value below `0x40` remains inert and survives unchanged; an otherwise-unused
value at or above `0x40` is interpreted by the delivery rules above on the next
overworld entry. After a delivery, the consumer writes `0x00` only to the class
byte. The X and Y bytes retain their old values but are inert while the class
byte is below `0x40`.

All three bytes lie inside the ordinary 4,192-byte slab and therefore
round-trip verbatim through Journey Onward and Q-save. A pending delivery is
not an `.OOL` record until the overworld consumer creates one; save code must
not materialize the queue into `BRIT.OOL` or `SAVED.OOL` as a persistence
side-channel.

## 10. Per-turn flags and combat scratch

A loosely packed band of bytes before the dungeon/map-cell working buffer holds per-turn and per-mode bookkeeping. Most are single-byte flags whose meaning is owned by one or two systems. They survive saves because they live inside the resident state region; whether they have semantic meaning for an implementation depends on which gameplay modes are reproduced.

| Offset       | Field                          | Meaning                                                                                                                                         |
|--------------|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x02E1`     | Moongate presence phase        | One byte, range `0..16`. The single world-global rise/sink phase for **every** natural moongate, described in `systems/overworld.md` Sections 9.1 and 9.2. Zero means no gate is up; sixteen means fully open; one through fifteen are the intermediate frames the renderer composes. The once-per-turn placement refresh moves it by one per turn (up during night hours, down during day hours), and the blocking gate-transit sequence drives it from fifteen to zero within a single command. Because it is one shared byte, every visible gate is at the same phase. An implementation that treats this as scratch and reseeds it on load will show gates at the wrong height after restoring a save taken during a rise or a fade. Factory seed: `0` — the shipped save starts at hour eight, in daylight, with no gate up. |
| `0x02E2`     | Moral-standing selector        | One-byte capped standing/progression value used by shrine rewards, Blackthorn rescue/refuge verdict text, the Lord British camp event, and several action penalties. This is not the party food word at `0x0202`. The factory seed value is `75`. Preserve adjacent unnamed bytes in this band. |
| `0x02E5`     | Turn-step counter              | One-byte saturating counter. The resident per-turn party-upkeep pass advances it by one on every pass and clamps it at `255`; that pass runs once per turn-consuming action in overworld, town, and dungeon play, and once per ten simulated minutes of town-bed rest. Its only known reset is the conversation gold-payment milestone (`systems/karma.md` section 4.1), which zeroes it when it reads at least `100` and the payment's other gates pass; that exclusivity comes from a static census of the shipped code's direct references to the byte, so read it as "no other directly-referenced writer exists" rather than as a proof (see `systems/karma.md` section 4.1's confidence note). It is therefore a cooldown timer, not a payment tally — earlier revisions of this document called it a "toll-progress counter incremented on every successful gold payment", which was wrong on both counts. New games seed it at zero. |
| `0x02E6`     | Camp cooldown counter          | One byte. Set to fourteen when a camp completes and decremented by one at each hour rollover with a hard floor at zero; a camp attempted while it is non-zero recovers nothing. Zero in the shipped seed. See `systems/rest-and-camp.md` Section 5. |
| `0x02E7`     | Camp month cookie              | One byte, written on the apparition draw with the current calendar month and **never read anywhere in shipped code**. Structurally a month-scoped cookie of the same shape as the day cookie at `0x020C`, but its consumer is absent - so this is a **permanent gap**, not a contract. Preserve the byte; do not infer behaviour from the analogy. |
| `0x02B6..0x02C4` | Fixed hidden-treasure found bitmap | 15 bytes, 113 bits. Bit `N` (with `byte = N >> 3` and `bit = N & 7`, little-endian within each byte) is set when ordinary fixed hidden-treasure records are recovered by S-Search. Special records 13, 14, and 15 do not use this bitmap as their durable grant state. The 113 records' `(scene, Z, X, Y, code)` coordinates live in `DATA.OVL`. See `systems/hidden-treasures.md` for the search-and-grant flow. New games seed all 15 bytes to zero. |
| `0x020C`     | Record-14 daily cooldown cookie | One byte. Holds the day-of-month at the last grant of the cycling fixed hidden-treasure record (record index 14). The scan skips record 14 when `current_day == cookie` and writes the current day on grant. Bit 14 of the found bitmap above is NOT used; the cookie fully owns record 14's availability. This byte is **not an independent field of its own**: it sits inside the special/quest-item band of Section 7, at the one offset in `0x020A..0x0219` that no carried item claims. It is not a carried-item counter and must not be displayed or granted as one. The 28-day month rollover zeroes it (`systems/time.md` Section 8); ordinary midnight does not. Factory: `0x00`. |
| `0x02B2..0x02B4` | Rare-reagent harvest cooldown cookies | Three bytes, one per fixed rare-reagent Search harvest point, in the harvest-table order published in `systems/containers.md`. Each holds the day-of-month of that point's last successful harvest; a harvest is refused when the byte equals the current day, and success writes the current day into it. These sit between the reagent counters of Section 7 and the party-size byte, and they are not reagent counters — do not read or display them as inventory. The 28-day month rollover zeroes all three. Factory: all zero. |
| `0x0241`     | Record-15 gate — the Glass Sword equipment counter | Not a dedicated cookie. This is the **equipment-inventory counter for item id `39` (Glass Sword)** from Section 7, and record 15's granted item is that same Glass Sword. Record 15 grants only when the byte is zero and no NPC is present at the searched tile; the skip predicate is `byte != 0` OR an NPC is present. The scan itself never writes the byte and never sets bitmap bit 15 — the ordinary inventory grant increments the counter, and that is what makes the record single-use. An engine that gives record 15 a separate never-written cookie yields an infinitely repeatable Glass Sword. Factory: `0x00`. |
| `0x02EE`     | Saved scene / mode scratch     | See Section 6. Adjacent to the location tuple; combat uses it for pre-combat scene restore and mode code may reuse it as transition/redraw scratch. |
| `0x02F2..0x02FF` | Animation / cached light    | Animation, redraw, and cached ambient-light bytes. The active light-source duration counters start at `0x0300`.                                  |
| `0x0300`     | Light-spell counter         | Duration counter set by *In Lor* and *Vas Lor*.                                                                                                  |
| `0x0301`     | Torch counter               | Duration counter set or extended by I-Ignite.                                                                                                    |
| `0x0302..0x0321` | Combat interference-source map | Thirty-two bytes, one per combat slot. A value `0..31` names the most recently recorded ordinary adjacent attacker for that victim; `0xFF` means no source. Combat does not initialize this map on encounter entry or clear it on exit, so it is persistent gameplay state rather than disposable scratch. The shipped new-game seed contains zero in every entry. Zero is a valid slot number, not the sentinel, though a normal fresh encounter treats slot zero as party-side and therefore not a hostile interferer. |
| `0x0322..0x0327` | Per-mode scratch / casting flags | Cast-spell handshake, fall-through flags, and other transient mode state. Saved because they sit in resident memory. |
| `0x03A9`     | Door auto-close previous tile | One-byte snapshot of the closed tile replaced by O-Open. Zero means no pending auto-close. |
| `0x03AA`     | Door auto-close X            | One-byte X coordinate of the pending door cell. |
| `0x03AB`     | Door auto-close Y            | One-byte Y coordinate of the pending door cell. |
| `0x03AC`     | Door auto-close countdown    | One-byte turn countdown, initialized to four by O-Open. The previous-tile byte gates whether the tracker is active. |
| `0x03B3`     | Early-game encounter-size damper | Wilderness encounter spawn-count reroll flag, historically mislabelled the "fortunes of war" or "double encounter" flag. Terrain combat reads non-zero as "replace the first random monster-count roll with a second roll of the same shape", which can only lower the count. **The factory seed sets this byte to `1`** — it is the only non-zero byte in the tail of `INIT.GAM` — so every new game begins with the damper active, and save/load carries it. Nothing in gameplay ever sets it; the only write anywhere in the engine is the clear performed at the 28-day month rollover. Because the shipped calendar starts partway through a month, it survives the first twenty-four in-game days and is then off permanently. See `systems/combat.md` Section 5. |

The remaining per-turn flags are not part of the format's "stable" surface — different dot releases of the original game might have set or cleared bytes here for reasons not modelled in any external spec. An implementation that wants a byte-compatible save can pass these through unchanged: the engine reads the relevant ones during boot, ignores the rest, and rewrites them as it plays. The interference-source map is an explicit exception: preserve its exact bytes and apply the lifecycle in `systems/magic.md` Section 7. It has no encounter-entry, round-start, or combat-exit reset; each victim entry clears only after that victim completes an action. A source left uncleared at combat exit may therefore be written by Q-Save and restored by Journey Onward.

Several fields in the band have higher-level meaning:

- **Fixed hidden-treasure special gates.** Only the found bitmap at
  `0x02B6..0x02C4` is a field created for this system. The three special
  records reuse bytes that other systems already own: record 13 reads the Keys
  counter at `0x0206` and grants only when the party holds no keys, record 14
  uses the unclaimed special/quest-item byte at `0x020C` as its day cookie, and
  record 15 reads the Glass Sword equipment counter at `0x0241`. None of the
  three sets a bitmap bit. Treat all three as aliases of the existing fields,
  never as private copies.
- **Timing/status and transport/action bytes.** The three-byte control cluster at `0x02D4..0x02D6` is not a single enum. Preserve the timing/status tag, active-player index, and transport/action marker separately.
- **Active player sentinel.** A byte that is `0xFF` until the player picks a party member (typically inside towns and combat), then holds the slot index. Used by the gameplay loops as "is anyone currently selected to move".
- **NPC-occupied bitmask.** A byte stamped on town entry that records which of the location's NPCs have an active slot in the active-object table. Used by the town entry helper to decide what slots to allocate; refreshed every town entry, so its saved value matters only for the scene the player is currently in.
- **Dungeon room-clear bitmap.** Sixteen bytes at `0x033A..0x0349` persist
  which dungeon room encounters have already been cleared. Dungeon mode uses
  this bitmap to demote matching `0xF?` room-trigger cells to `0xA?`
  room-helper cells when rebuilding the loaded dungeon image from
  `DUNGEON.DAT`; the bitmap is durable, while the cell-byte rewrite itself is
  not stored as a patched dungeon map.
- **Early-game encounter-size damper.** The byte at `0x03B3` is part of the flat
  save image and round-trips through save/load like any other resident tail
  byte. Encounter setup reads it only as a non-zero count-reroll flag, and the
  28-day month-boundary cleanup clears it. There is no setter, and the absence
  is by design rather than a gap in the analysis: the factory seed ships the
  byte at `1`, character creation copies the seed image wholesale into the first
  save, and the month rollover is the engine's only write to it. A save tool
  should preserve whatever value it finds; a new-game producer must emit `1`
  here, or early wilderness encounters will be larger than the original's.

## 11. Worked example

A fresh save's roster view begins with the Avatar record at slot zero, followed
by the canonical companion roster at thirty-two-byte stride. The example below
describes the semantic interpretation without reproducing the raw save bytes.

The first record is the Avatar:

- Bytes `00..08`: the Avatar's name, NUL-padded to the fixed nine-byte name field. The questionnaire prompt accepts eight visible characters, so a questionnaire-created name leaves the ninth byte as padding.
- Byte `09`: gender; byte `0A`: class; byte `0B`: status.
- Bytes `0C..0F`: STR, DEX, INT, and MP.
- Bytes `10..15`: current HP, maximum HP, and experience.
- Byte `16`: level.
- Byte `17`: month counter / inn stay counter.
- Byte `18`: cached party combat-defense byte.
- Bytes `19..1E`: equipment fields.
- Byte `1F`: inn-registry marker / padding.

For a questionnaire-created Avatar, chargen overwrites the entered name,
gender, STR, DEX, INT, and MP. The class remains Avatar and the status remains
good from the seed. Current HP remains 60, maximum HP remains 60, experience
remains 150, and the level byte remains 2. (An earlier revision of this
paragraph rotated those three values — "maximum HP 150, experience 2, level
unset" — and is **withdrawn**; the seed's Avatar record carries 60 / 60 / 150
and a level byte of 2, matching `systems/chargen.md` section 8. The `0xFF`
unset sentinel in that record sits in the per-character month counter at
`+0x17`, not in the level byte at `+0x16`.) Equipment-slot
bytes are preserved from the seed and use the helm, body armour, weapon hand,
shield/off hand, ring, and amulet/neck order documented in Section 3.1. The
factory-seed readied equipment for all sixteen roster slots is enumerated in
`systems/chargen.md`; the equipment id-to-name order is in
`catalogs/item-list.md`.

The second record is Shamino in slot one, regardless of recruit state. Records
two through fifteen continue the canonical companion list at thirty-two-byte
stride.

In the factory seed used for a questionnaire-created game, the untouched
`INIT.GAM` and clean-install `SAVED.GAM` images are byte-identical. The starting
counters are food 63, gold 150, keys 2, gems 0, torches 4, and the
Grapple/legacy-magic-powder byte 0.
The reagent record starts as black pearl 4, blood moss 6, garlic 7, ginseng 6,
mandrake 0, nightshade 3, spider silk 0, and sulfurous ash 0. The party-size
byte is 3, matching Avatar, Shamino, and Iolo in the travelling party.

The same seed places the save clock at year 139, month 4, day 5, 08:35. The
active-player byte is `0xFF` ("no active party member selected"), the status tag
is 0, and the transport/action marker is 28, the clean on-foot/avatar marker in
the seed. The persisted map tuple is scene 13 (Iolo's Hut), saved-scene scratch
0, floor/Z 0, X 15, Y 15. The wind byte is 0, which maps to Calm; tools should
still preserve out-of-range wind values they do not understand.

In a chargen-only save with no active map yet, the active-object table at `0x06B4` is zero; the engine populates it on first overworld entry from the surface object overlay. The example is shown only as a guide to reading the layout; the exact bytes a fresh chargen produces depend on the entered name, chosen gender, and questionnaire stat rolls.

## 12. Reserved and zero-padded regions

Two spans are zero in the factory seed and in clean-state saves:

- `0x07B4..0x105F` — two thousand two hundred twenty bytes between the
  active-object table and the file end. In memory this region holds the NPC
  schedule blob, NPC runtime state, NPC path queues, and the world-tile render
  buffer, all of which are repopulated from the location's NPC files and the
  active-map loader on map entry. Their contents are transient for gameplay:
  a clean implementation may rebuild them on load, while a byte-compatible save
  editor should preserve unknown bytes when rewriting an existing save.

## 13. The object-overlay companions

The active-object table embedded in `SAVED.GAM` (Section 8) holds the cast on the *current* map. The other world plane's cast lives in the companion `.OOL` files.

| File         | Size      | Role                                                                                                |
|--------------|-----------|-----------------------------------------------------------------------------------------------------|
| `SAVED.OOL`  | 512 bytes | Runtime working copy. Surface in first 256 bytes, underworld in second 256 bytes.                   |
| `BRIT.OOL`   | 256 bytes | Surface object table. Seed and load-time mirror; a save reads it and never writes it.               |
| `UNDER.OOL`  | 256 bytes | Underworld object table. Seed and load-time mirror; a save reads it, then writes the same bytes back unless entry disk-prompt mode was already mode 1. |
| `INIT.OOL`   | 256 bytes | Factory seed for the underworld (companion to `INIT.GAM`); byte-identical to the shipped `UNDER.OOL`. Read-only at runtime. |

The on-disk record layout in every `.OOL` file matches the eight-byte active-object record from Section 8 exactly. The shipped surface seed `BRIT.OOL` is all zeros; the shipped underworld seed `UNDER.OOL` has the small handful of non-zero records — five of them, a skiff and a four-corpse cluster — with the rest zero. (An earlier revision of this paragraph had the two planes the other way round, attributing the records to a Britannia surface seed and calling the underworld seed empty; that is withdrawn. `formats/ool.md` section 7 enumerates the five records.) The "depends" auxiliary bytes use class-specific encodings; for these bare seed records, `+0x04` is `0xFF` and `+0x05..+0x07` are zero.

The roundtrip across `.OOL` files is owned by `systems/save-load.md`: load refreshes both per-plane mirrors from `SAVED.OOL`, while save reads both per-plane files into its staging halves, writes the underworld file back out only when the entry disk-prompt mode was not mode 1, never writes the surface file, and composes the canonical `SAVED.OOL` from those halves. The "OOL" extension's expansion is unattested; "Object Overlay Layer" is a plausible mnemonic, treated as opaque.

## 14. Format Boundary And Remaining Runtime Work

The `SAVED.GAM` layout contract is complete at flat-image depth: file size,
roster stride, inventory/counter regions, spell stocks, clock fields, scalar
moral-standing selector, map/dungeon working buffer, mixed runtime-state band
boundary, active-object table, room-clear bitmap, timing/status glyph byte,
transport/action marker, and companion `.OOL` relationship are fixed. The
remaining work is runtime ownership naming for the remaining opaque bytes, not a
change to the base file layout. The two items that previously headed this
section -- ownership of the `0x05B4..0x06B3` band and the transport/action
marker's value set -- are both closed below.

- **`0x05B4..0x06B3` ownership.** Resolved. The band is two back-to-back
  per-location bitmask tables — NPC removed, then NPC name known — each
  thirty-two four-byte slots, ending flush against the active-object table.
  Section 9.2 gives the split and the bit numbering, and withdraws the older
  "mixed world, quest, and mode state" framing for this span.

- **Transport/action marker values.** Resolved. Offsets `0x02D4` and `0x02D6`
  are separate fields, not one enum; `0x02D4` is the timed magic-effect code,
  which the stats panel draws as the bottom glyph byte. The byte at `0x02D6`
  is the sprite the party is drawn as: the viewport composer copies it verbatim into the tile and frame bytes of the
  party's own entry in the active-object table every time the view is composed.
  Its persistent value set is complete and closed, and `systems/vehicles.md`
  section 2 publishes it in full: on foot; mounted horse in two frames; magic
  carpet in two frames; frigate with sails hoisted in four facings; frigate with
  sails furled in four facings; skiff in four facings; and a sprite-suppressed
  value reached only by drowning. Four further values exist solely as
  single-frame animation overrides that one routine saves and restores around
  itself, so the save path can never observe them and a byte-compatible
  implementation never has to persist them. There is no balloon family and no
  sixth vehicle family. The factory seed carries the on-foot value. Only the
  ship family selects the stats-panel hull display from active-object byte `+5`.

- **Equipment and defense values.** The six equipment slot bytes per character
  record are mapped and hold equipment item ids or the empty sentinel.
  R-Ready's class tags and burden-versus-Strength gates live in
  `catalogs/item-list.md` and `systems/inventory.md`, and Amulet/Turning's
  combat-passive branch is specified in `systems/combat.md`. The adjacent
  `+0x18` byte is the combat defense value consumed by the damage path; current
  traced equipment helpers do not recompute it from readied armor. Do not map
  party combat defense to record byte `+0x0D`; that byte is Dexterity in the
  roster layout (Intelligence is `+0x0E`), while the combat reader resolves to
  `+0x18` at the thirty-two-byte character stride.

Historical third-party references sometimes swap the gender and class positions.
This spec's order is verified: gender at `+0x09`, class at `+0x0A`, and status
at `+0x0B`. Treat the mismatch as an external-source correction, not an open
format question.

## 15. Sources

The byte-level layout described here was derived from the project's private save-format notes, runtime-state map, and semantic summaries of the save/load handlers. This public spec paraphrases the resulting behaviour and field positions; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, or implementation listings.

- The Ashes reachability closure — factory status values, new-character and
  Ultima IV transfer initialization, gameplay status-writer census, and
  whole-record preservation boundary — is derived from private analysis in
  `u5-decomp/notes/`, `u5-decomp/functions/INTRO_OVL/`, and the status-owning
  overlay directories under `u5-decomp/functions/`.
- The first-pass byte-level survey of the save image, the `.OOL` family, the canonical companion roster, and the offset-by-offset verification of inventory and runtime fields — `u5-decomp/formats/`.
- The runtime-state map used to cross-check persistent field positions — `u5-decomp/formats/`.
- The combat interference-source map's saved position, factory-zero seed,
  adjacent-attack writer, completed-action clear, Cast-time revalidation, and
  cross-encounter lifetime — `u5-decomp/formats/`,
  `u5-decomp/functions/COMBAT_OVL/`,
  `u5-decomp/functions/COMSUBS_OVL/`,
  `u5-decomp/functions/ULTIMA_EXE/`, and `u5-decomp/notes/`.
- The turn-step counter at `0x02E5` — its single increment site and saturation
  cap, its single reset site, and the cadence of the pass that advances it —
  `u5-decomp/notes/` and
  `u5-decomp/functions/TALK_OVL/`.
- The fresh-seed counter, reagent, clock, and location values were cross-checked
  against a clean local asset image by reading the named fields documented
  above; this spec does not reproduce the raw seed bytes.
- The B-Board transport marker writes — `u5-decomp/functions/CMDS_OVL/`.
- The moral-standing selector byte and its distinction from the party food word --
  `u5-decomp/notes/`.
- The moongate presence phase at `0x02E1` — its identification within the
  previously unnamed mode-scratch band, its range and factory seed, the complete
  census of its readers and writers, and the confirmation that it is a single
  world-global byte rather than per-gate or per-mode scratch —
  `u5-decomp/notes/`.
- The N-New Order command's active non-leader whole-record swaps, slot-zero
  refusal, and party-size non-mutation are derived from
  `u5-decomp/functions/CMDS_OVL/`.
- The overworld per-turn animator's `Q`/`T` and transport-marker pendulum reads — `u5-decomp/functions/MAINOUT_OVL/`.
- The stats-panel transport/status glyph readers — `u5-decomp/functions/ULTIMA_EXE/`.
- The shared status helper that stamps status `'P'` (poisoned) on living party
  members and skips dead ones — `u5-decomp/functions/ULTIMA_EXE/`
  (the note's filename predates the correction). The correction retracting the
  earlier revive reading is source provenance: derived from private analysis
  notes in `u5-decomp/notes/`.
- The spell-charge stock index order is derived from the shared player
  spell-token parser used by C-Cast and M-Mix, the per-spell stock readers and
  writers in the CAST/CMDS overlay notes, and the public 48-row spell table:
  `u5-decomp/functions/CAST_OVL/`,
  `u5-decomp/functions/CMDS_OVL/`,
  `u5-decomp/formats/`, and
  `u5-spec/catalogs/spell-list.md`.
- The Moonstone gate-slot writer, special/use-item byte identities, and
  Search/Get recovery behaviour --
  `u5-decomp/functions/CAST_OVL/` plus local SJOG
  helper analysis summarized without copying implementation text.
- The status-byte letter space at `+0x0B`: which letters shipped code writes,
  the panel-side synthesis of `'C'`, and the absence of any confirmed producer
  or consumer of `'A'`. Re-derived from the shipped binaries on 2026-08-23 by
  scanning every shipped code file for immediate-operand compares and stores of
  each status letter, cross-checked against `systems/combat.md` Section 6.1a and
  the trap status helper in `systems/traps.md`.
- The Spyglass, Sextant, Pocket Watch, Black Badge, and Wooden/Sandalwood Box
  special-item byte identities are cross-checked from the Z-stats special-item
  snapshot and display path:
  `u5-decomp/functions/ZSTATS_OVL/`
  and `u5-decomp/functions/ZSTATS_OVL/`.
- The save handler's open-write-close sequence and byte-image flush to `SAVED.GAM` -- `u5-decomp/functions/CAST2_OVL/`. The per-plane `.OOL` half of that note (two unconditional mirror writes and no read) is superseded: a 2026-08-22 re-derivation from the shipped save overlay shows the two per-plane operations are reads and the single underworld write is the entry-mode-gated one. `systems/save-load.md` section 5 owns the corrected order.
- The load handler's byte-image read of `SAVED.GAM` into the same region, the empty-save guard, the `SAVED.OOL` read, and the mirror-write of `BRIT.OOL` and `UNDER.OOL` — `u5-decomp/functions/INTRO_OVL/`.
- The pending shipwright-delivery offsets, packed acquisition byte, purchase
  mutations, outdoor consumption, class-only clear, and complete code-reference
  census — `u5-decomp/functions/SHOPPES2_OVL/` and
  `u5-decomp/functions/MAINOUT_OVL/`.
- The chargen flow's per-record write to roster slot zero (name, gender, STR, DEX, INT, and MP) and preservation of seed class/status/HP/experience fields — `u5-decomp/functions/FONT_OVL/`.
- The equipment slot order, empty sentinel, carried-equipment counter band, and
  R-Ready stock mutations are derived from the updated ZSTATS overlay notes
  and summarized publicly in `u5-spec/systems/inventory.md`.
- The factory-seed readied equipment names were cross-checked from the clean
  seed image by reading the public equipment-slot fields through the equipment
  item-id order in `u5-spec/catalogs/item-list.md`.
- The save and load systems' overall semantics, file roles, and mirror-write contract — `u5-spec/systems/save-load.md`.
- The active-object record layout and the in-memory table semantics — `u5-spec/systems/active-objects.md`.
- Source provenance: derived from private analysis in
  `u5-decomp/notes/` -- the
  exhaustive attribution of the disputed band, the exact extent of the dungeon
  working buffer, the two per-location NPC bitmask tables, and the finding that
  the two bytes formerly called a quest-progress word are Stonegate's
  removed-NPC mask. Cross-checked against
  `u5-decomp/functions/TOWN_OVL/`,
  `u5-decomp/functions/TALK_OVL/`, and
  `u5-decomp/formats/`.
- The calendar and clock fields' cascade rules and persistence — `u5-spec/systems/time.md`.
- Source provenance: derived from private analysis in
  `u5-decomp/notes/` -- the
  identification of `0x03B3` as the early-game encounter-size damper, its
  factory-seed value, the absence of any gameplay setter, and the month-rollover
  clear as the engine's only write. Cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/`.
