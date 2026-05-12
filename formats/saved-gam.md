# SAVED.GAM

## 1. Overview

`SAVED.GAM` is the on-disk image of an Ultima V save. It is fixed at four thousand one hundred ninety-two bytes, holds no header or magic number, carries no version word, and pretends to no record-by-record structure. What the file *is*, structurally, is a verbatim memory dump: a contiguous slab from the engine's data segment, written and read in one operation. Live state and save state are the same bytes; a save is the act of flushing them.

Everything described below is therefore a *layout* rather than a *protocol*. Each field has a fixed location, fixed width, and fixed meaning. There are no length prefixes, no string terminators that must be honoured, no padding the writer can vary, and no out-of-line storage — strings are fixed-width, arrays are inline, and records are packed back-to-back at known offsets. An implementation that wants to read or write a byte-compatible `SAVED.GAM` works at the level of "which byte holds which field," nothing more.

The save is paired with three companion files. `SAVED.OOL` holds five hundred twelve bytes of active-object state for both world planes - the part of the runtime cast that lives outside the save image. `BRIT.OOL` and `UNDER.OOL` ship as seeds for those tables and are mirror-written by the load path; the save path reads them as staging sources and conditionally updates the underworld mirror. The save and load semantics are described in `systems/save-load.md`; this spec covers the byte layout of `SAVED.GAM` itself, with `SAVED.OOL`/`BRIT.OOL`/`UNDER.OOL` covered where the two formats touch (Section 13).

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
| Wind state                          | `0x02EC`              | 1 byte      | 6       |
| Scene byte and saved-scene scratch  | `0x02ED` – `0x02EE`   | 2 bytes     | 6, 10   |
| Party position (z/x/y)              | `0x02EF` – `0x02F1`   | 3 bytes     | 6       |
| Per-turn flags and combat scratch   | `0x02F2` – `0x0325`   | ~52 bytes   | 10      |
| Quest progress bitmasks             | `0x0326` – `0x0328`   | 3 bytes     | 9       |
| Tail of resident state              | `0x0329` – `0x03B3`   | ~139 bytes  | 10      |
| Dungeon-map dump                    | `0x03B4` – `0x03FF`   | 76 bytes    | 8       |
| Reserved / zero                     | `0x0400` – `0x05B3`   | 436 bytes   | 12      |
| NPC interaction flags               | `0x05B4` – `0x06B3`   | 256 bytes   | 9       |
| Active-object table (32 × 8 bytes)  | `0x06B4` – `0x07B3`   | 256 bytes   | 8       |
| Reserved / NPC and tile scratch     | `0x07B4` – `0x105F`   | 2,220 bytes | 12      |

The two leading bytes precede the roster in the resident save image. They are
zero in the factory seed and should be preserved by byte-compatible tools.

The inn-guest registry is a save-backed resident view with the same thirty-two-byte stride as character records. Its overlap with the canonical roster and adjacent inventory range is intentional: the inn helper reads this shifted view as a sixteen-slot guest table, not as ordinary padding. Treat the range as owned by the inn helper when reproducing inn behaviour, and preserve it byte-for-byte in compatible save tools unless intentionally implementing the inn flow. The factory-seed `INIT.GAM` is zero in every region whose value depends on play; only the roster records, starting inventory, starting date/location, weather, and a small set of control bytes carry non-zero values out of the box.

The next several sections describe each region in detail. The byte-offset tables are exhaustive for the regions whose contents have been verified directly; for regions verified only against external references (the dungeon-map dump and the NPC interaction flags), the section says so and the layout is a working hypothesis flagged in the open-questions section.

## 3. Character roster

The party roster begins two bytes into the file and holds sixteen records of thirty-two bytes each, packed back-to-back, no separator. Record zero is the Avatar; records one through fifteen hold the canonical companion list — Shamino, Iolo, Mariah, Geoffrey, Jaana, Julia, Dupre, Katrina, Sentri, Gwenno, Johne, Gorn, Maxwell, Toshi, and Saduj — in slot order. Companions exist in the roster from the moment a new game starts, whether or not they have been recruited. The party-size byte (Section 4) gives the number of slots that are *active* in the current party; slots beyond that index hold characters who exist in Britannia but are not currently travelling with the player.

### 3.1 Record layout

Each thirty-two-byte record is laid out as follows.

| Field offset | Width    | Meaning                                                                                                  |
|--------------|----------|----------------------------------------------------------------------------------------------------------|
| `0x00`       | 9 bytes  | Name. ASCII, NUL-padded. The first character is the leading byte of the record and may be zero on an unused slot. |
| `0x09`       | 1 byte   | Gender. `0x0B` for male, `0x0C` for female. Not ASCII; the values are private to the engine.             |
| `0x0A`       | 1 byte   | Class. ASCII letter — `'A'` Avatar, `'B'` Bard, `'F'` Fighter, `'M'` Mage, `'D'` Druid, `'T'` Tinker, `'P'` Paladin, `'R'` Ranger, `'S'` Shepherd. |
| `0x0B`       | 1 byte   | Status. ASCII letter — `'G'` good (alive), `'P'` poisoned, `'S'` sleeping, `'C'` charmed, `'D'` dead, `'A'` ashes. |
| `0x0C`       | 1 byte   | Strength.                                                                                                |
| `0x0D`       | 1 byte   | Dexterity.                                                                                               |
| `0x0E`       | 1 byte   | Intelligence.                                                                                            |
| `0x0F`       | 1 byte   | Magic points (current).                                                                                  |
| `0x10`       | 2 bytes  | Hit points current. Little-endian word.                                                                  |
| `0x12`       | 2 bytes  | Hit points maximum. Little-endian word.                                                                  |
| `0x14`       | 2 bytes  | Experience points. Little-endian word.                                                                   |
| `0x16`       | 1 byte   | Level. `0xFF` on unset / not yet computed.                                                               |
| `0x17`       | 1 byte   | Per-character month counter. The time system increments every roster slot at the 28-day month rollover, capped at 25. The inn uses this as a lodged guest's stay counter. |
| `0x18`       | 1 byte   | Reserved / padding.                                                                                      |
| `0x19`       | 6 bytes  | Equipment slot bytes: helm, body armour, weapon hand, shield/off hand, ring, and amulet/neck item. Each non-empty slot byte is an equipment item id (see Section 7). The live empty-slot sentinel is `0xFF`. |
| `0x1F`       | 1 byte   | Inn-registry marker byte when this record is viewed through the shifted inn guest table; zero for an empty/cleared guest marker. Opaque padding for ordinary active-character behaviour. |

The name is NUL-padded rather than NUL-terminated. A nine-byte slot can hold a nine-character name with no terminator at all, and shorter names are padded with zero bytes. Players who entered an empty name will see all nine bytes of zero. The engine's empty-save guard (see `systems/save-load.md`) tests an interior byte of record zero's name field — not the leading byte — because a packed control field may legitimately be zero even in a populated save, while a typed name has at least one non-zero byte past its first character.

### 3.2 Roster invariants

Three invariants are worth flagging. Slot zero is structurally the Avatar: chargen writes only into slot zero, and other gameplay code keys "is this character the player?" off slot index, not record contents. Slot order is fixed and stable — companions occupy predetermined slot indices regardless of party order — and the engine never compacts or reorders. The class letter at `+0x0A` is part of the canonical layout, not per-save state: a save with no companions recruited still lists all sixteen with their classes; only status, stats, and equipment slots change through play.

The gender byte at `+0x09` is not ASCII, but the class and status bytes at `+0x0A` and `+0x0B` are: visual inspection of a save will see, for the recruited Avatar, a record whose tenth and eleventh bytes look like `'A' 'G'` for "Avatar class, alive". Earlier external references that swap the gender and class positions are wrong: the order is gender-then-class-then-status.

### 3.3 The inn-guest registry

A second sixteen-by-thirty-two-byte guest-table view sits in the resident save image. The inn-guest registry stores a copy of each character record that is currently checked into one of the in-world inns. Each guest entry uses the same stride and record-shaped payload as a character record, but it is not a second ordinary roster: the leading byte of each registry slot is an inn-scene marker used to decide whether the guest belongs to the inn currently being visited. The registry interpretation is opaque to other gameplay systems; only the inn helper is known to read or write the scene marker as guest state. It survives saves because it lives inside the resident state region. Leave initializes the guest's stored stay counter to zero; the time system increments that shared character counter on each 28-day month rollover, capped at 25; pickup treats a zero counter as one billable unit and clears the returned slot's marker to zero after moving the guest back into the active roster.

## 4. Active player and party

A handful of bytes later in the save image track party control state, transport/status presentation, and who is currently the "active" character — the one whose stats appear in the side panel and who issues player-controlled commands.

| Offset   | Width  | Field                  | Meaning                                                                                                        |
|----------|--------|------------------------|----------------------------------------------------------------------------------------------------------------|
| `0x02B5` | 1 byte | Party size             | Number of slots `1..6` that are currently in the travelling party. Iteration cap for any "for each party member" pass, and one of the inputs to inn rest quotes and pickup capacity checks. |
| `0x02D4` | 1 byte | Timing/status tag      | Multi-consumer state byte. Non-zero values can draw the bottom-panel transport/status glyph; `Q` and `T` are also consumed by timing and mode-loop pendulum logic. Not the full boarded-vehicle enum. |
| `0x02D5` | 1 byte | Active player index    | Slot index `0..7` of the currently selected character. `0xFF` for "none selected" (overworld default).         |
| `0x02D6` | 1 byte | Transport/action marker | Avatar or vehicle transport/action marker. B-Board writes this when the party boards horses, carpet, skiffs, or ships; other systems also mask it for light-source and alternate-turn presentation states. |

The active-player byte is `0xFF` in the overworld and is set to a slot index when the player picks a character (typically on town entry, or at the start of a combat round). Town and combat modes update it as the player navigates; saving and loading preserves it as-is. The party-size field is the iteration cap that every "for each party member" pass uses; it is the number of slots that hold travelling characters, not the size of the roster (which is always sixteen), and not an inn-stay or calendar counter.

The `0x02D4` and `0x02D6` bytes are deliberately separated here because different subsystems read them for different reasons. The timing system reads the `Q` and `T` values from the status-tag byte; the boarding and dismount paths manipulate the transport/action marker; the stats panel may use either surrounding state for display decisions. A compatible save reader should preserve both bytes exactly even if its own engine keeps a cleaner internal transport model.

Known `0x02D6` families are documented semantically in
`systems/vehicles.md`: foot/avatar, mounted horse, carpet, ship, and skiff.
Byte-compatible readers must preserve unrecognized marker values; deterministic
engines can map recognized families to semantic transport, facing, and sail
state internally.

## 5. Calendar and clock

The world clock lives in a small group of bytes shared with the time system (see `systems/time.md`). All five fields are persisted directly; loading restores the clock to the exact instant of the save.

| Offset   | Width   | Field   | Meaning                                                                                                  |
|----------|---------|---------|----------------------------------------------------------------------------------------------------------|
| `0x02CE` | 2 bytes | Year    | In-world year. Little-endian word.                                                                       |
| `0x02D7` | 1 byte  | Month   | One-based, range `1..13`.                                                                                |
| `0x02D8` | 1 byte  | Day     | One-based, range `1..28`. (Britannia's calendar has thirteen months of twenty-eight days.)               |
| `0x02D9` | 1 byte  | Hour    | Zero-based, twenty-four-hour, range `0..23`.                                                             |
| `0x02DB` | 1 byte  | Minute  | Range `0..59`.                                                                                           |
| `0x02DE` | 1 byte  | AM/PM display | Twelve-hour-display value derived from the hour, recomputed on each hour change.                   |

The cascade rules — minute → hour → day → month → year — are described in detail in `systems/time.md`. From this spec's perspective the calendar fields are simple little-endian unsigned integers in fixed ranges.

## 6. Scene and party position

The five bytes after wind form the persisted location cluster: active scene, saved-scene / mode scratch, and party Z/X/Y. Scene byte and party Z together pin which map (overworld, underworld, named town, dungeon level) the party occupies; party X and Y give the cell within that map. The scratch byte sits inside the same cluster and must round-trip exactly, but it is not a coordinate. These fields are read by the post-load mode dispatcher to decide which gameplay overlay to bring up.

| Offset   | Width  | Field        | Meaning                                                                                                                     |
|----------|--------|--------------|-----------------------------------------------------------------------------------------------------------------------------|
| `0x02EC` | 1 byte | Wind         | Wind state byte. Drives the wind-message banner shown on overworld entry and is consulted by sail movement. Preserve the byte exactly; the saved-byte-to-label mapping is still open, so a byte-compatible reader must not clamp or rewrite unrecognised values before mapping recognised bytes to the five public wind labels. |
| `0x02ED` | 1 byte | Scene        | Active map. `0x00` overworld, `0x01..0x20` named town/castle/keep/dwelling, `0x21..0x7F` dungeon range (stock dungeons use `0x21..0x28`), `0x80+` combat. |
| `0x02EE` | 1 byte | Saved scene / mode scratch | Adjacent mode scratch byte. Combat entry uses it to save the pre-combat scene for later restore; other mode code may reuse it as transition or redraw state. Preserve exactly and do not treat it as a party coordinate. |
| `0x02EF` | 1 byte | Party Z      | World floor. `0x00` surface (Britannia), non-zero for underworld depth or building floor index. `0xFF` "no active map" sentinel. |
| `0x02F0` | 1 byte | Party X      | Cell column on the active map.                                                                                              |
| `0x02F1` | 1 byte | Party Y      | Cell row on the active map.                                                                                                 |

The scene byte is the most-cited field in the entire save image: every gameplay dispatch keys off its value. The post-load reader inspects scene and party Z together to decide whether to enter the surface overworld, the underworld overworld, a named indoor scene, or a dungeon. The stable party-position tuple is therefore scene plus Z/X/Y; `0x02EE` is persisted mode scratch next to that tuple.

## 7. Inventory and consumables

A long band of bytes after the inn-guest registry holds the party's shared inventory. Most fields are single bytes; a few are little-endian words for counters that exceed two hundred fifty-five.

| Offset   | Width   | Field              | Meaning                                                                                                       |
|----------|---------|--------------------|---------------------------------------------------------------------------------------------------------------|
| `0x0202` | 2 bytes | Food               | Little-endian word. Decremented periodically by the per-turn cleanup.                                         |
| `0x0204` | 2 bytes | Gold               | Little-endian word. Range `0..9999` in normal play.                                                           |
| `0x0206` | 1 byte  | Keys               | Skeleton keys carried.                                                                                        |
| `0x0207` | 1 byte  | Gems               | Vision gems.                                                                                                  |
| `0x0208` | 1 byte  | Torches            | Torches.                                                                                                      |
| `0x0209` | 1 byte  | Magic powder       | Powder of magic awakening.                                                                                    |
| `0x020A..0x0219` | 16 bytes | Special / quest items | Scroll-of-Sentry, Codex skull, Crown, Sceptre, Sandalwood box, Spyglass, magic carpet, hourglass, wooden box, and similar one-byte counters or flags. Individual meanings remain cross-system. |
| `0x021A..0x0249` | 48 bytes | Equipment inventory | One byte per equipment item id. Arms shops, Z-stats, and R-Ready use the same id to index the shop stock table, base-price table, display-name row, carried counter, and readied-equipment slot value. The span covers ammunition and carried weapons/armour/helms/shields/rings/amulets. |
| `0x024A..0x0279` | 48 bytes | Spell-charge stock | One byte per pre-mixed spell charge. See Section 7.1.                                                         |
| `0x027A..0x0289` | 16 bytes | Use-item / scroll-potion counters | Working span for carried use-items whose exact per-byte order is still being traced.                          |
| `0x02AA` | 8 bytes | Reagents           | Black pearl, blood moss, garlic, ginseng, mandrake, nightshade, spider silk, sulfurous ash. One byte each.    |

The inventory region holds two-byte words for the two counters that need them (food and gold) and single bytes for everything else. Carry caps are enforced by the gameplay code; the save format places no upper bound, and an editor that sets values past the in-game maximum will produce a save the engine will read but that may behave oddly on display or arithmetic. The arms-shop equipment block is item-id keyed: item id `N` reads or writes byte `0x021A + N`.

The reagent block is small enough to enumerate as a fixed eight-byte record at `0x02AA`. The order matches the in-world spell-mixing UI, with black pearl in the first byte and sulfurous ash in the last.

### 7.1 Spell-charge stock

A separate block of forty-eight bytes at file offset `0x024A` holds the per-spell pre-mixed charge stock. Each entry is a signed-byte count of how many doses of that spell the player has mixed in advance. Entries decrement when the spell is cast (so long as the cast is paid out of stock rather than freshly mixed) and increment when the player runs the mix-reagents command.

The forty-eight-entry stride implies a fixed spell-class enumeration; the order matches the spell-list documented under `systems/magic.md`. An empty inventory has all forty-eight bytes zero. The same region serves for both magic schools (reagent-mixed spells and the chant-driven shrine quests do not interact with this block).

### 7.2 Moonstone gate slots

Thirty-two bytes at `0x028A..0x02A9` hold the eight saved Moonstone
destinations used by *Vas Rel Por* / Gate Travel. The layout is four parallel
eight-byte arrays:

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

## 8. Active-object table

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

Slot zero is the player. Slots one through thirty-one hold any other on-map cast — vehicles parked or in motion, NPCs that have stepped onto the player's floor, dropped items, summoned creatures, and so on. Most saves zero out most slots; the canonical seed save has the entire region zero, because the Britannian surface seed objects come from the surface object overlay (Section 13) rather than from the save image.

The active-object table in the save image is the snapshot of the live global table at flush time. In top-down scenes this is the player's current map cast: overworld and underworld saves hold vehicles, dropped objects, and spawned creatures; town, castle, keep, and dwelling saves hold the on-floor NPC/object cast. Dungeon exploration does not use this table as its first-person actor list, so dungeon saves preserve the global table as ambient state rather than as dungeon-renderer contents. Saves taken in combat are not supported: the gameplay loops do not honour `Q` mid-combat, and the combat framer's temporary combat table is restored before control returns to a saveable loop.

### 8.1 Dungeon-map dump

A seventy-six-byte region at file offset `0x03B4..0x03FF` is documented by external references as holding the dungeon-map dump — the cumulative "what cells of which dungeon levels has the player seen". Empirical inspection of factory and clean-state saves shows the region zero, so the layout below is verified only against external material and is flagged as a working hypothesis (Section 14). The region is a fixed seventy-six bytes regardless of how many dungeons the player has explored.

## 9. World flags

The save image carries two flag regions for cross-session world state.

### 9.1 Quest progress

Two bytes at file offsets `0x0326` and `0x0328` hold the shrine-quest progress as parallel bitmasks.

| Offset   | Width  | Field            | Meaning                                                                                                                       |
|----------|--------|------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `0x0326` | 1 byte | Ordained mask    | Bit per virtue: 0 Honesty, 1 Compassion, 2 Valor, 3 Justice, 4 Sacrifice, 5 Honor, 6 Spirituality, 7 Humility. Bit set = "ordained, must visit Codex". |
| `0x0328` | 1 byte | Codex-visited mask | Same eight-bit layout. Bit set = "Codex page read for this virtue".                                                          |

The two bitmasks together encode a four-state virtue quest: not started (both zero), ordained (ordained set, codex clear), codex-read (both set), complete (ordained clear, codex set — the ordained bit is cleared on shrine turn-in). All eight virtues use the same encoding, with the same bit-to-virtue map, so the layout is uniform. Ordinary post-completion shrine offerings leave these masks unchanged; they update gold and shrine standing instead.

### 9.2 NPC interaction flags

A two-hundred-fifty-six-byte region at file offset `0x05B4..0x06B3` is documented by external references as the NPC kill / met flag table — one byte (or one bit) per per-named-NPC interaction across the world's full NPC roster. Like the dungeon-map dump, this region is zero in the factory seed and clean-install saves, and the layout below is a working hypothesis flagged in Section 14. Likely structure: one bit per NPC for "have I met you?" and one bit per NPC for "have I killed you?", packed across the two hundred fifty-six bytes.

The two flags are read by the conversation engine when an NPC is encountered: the `NAME` keyword response gates on the "met" bit; the "missing person" reports key off the "killed" bit. They are written by the conversation engine on first introduction and by the combat post-pass on monster death.

## 10. Per-turn flags and combat scratch

A loosely packed band of bytes between the runtime-state region and the dungeon-map dump holds per-turn and per-mode bookkeeping. Most are single-byte flags whose meaning is owned by one or two systems. They survive saves because they live inside the resident state region; whether they have semantic meaning for an implementation depends on which gameplay modes are reproduced.

| Offset       | Field                          | Meaning                                                                                                                                         |
|--------------|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `0x02EE`     | Saved scene / mode scratch     | See Section 6. Adjacent to the location tuple; combat uses it for pre-combat scene restore and mode code may reuse it as transition/redraw scratch. |
| `0x02F2..0x02FF` | Animation / cached light    | Animation, redraw, and cached ambient-light bytes. The active light-source duration counters start at `0x0300`.                                  |
| `0x0300`     | Light-spell counter         | Duration counter set by *In Lor* and *Vas Lor*.                                                                                                  |
| `0x0301`     | Torch counter               | Duration counter set or extended by I-Ignite.                                                                                                    |
| `0x0302..0x0327` | Per-mode scratch / casting flags | Combat round counter, cast-spell handshake, scene-tag pre-combat, fall-through flags. Most are transient; saved because they sit in resident memory. |

The per-turn flags are not part of the format's "stable" surface — different dot releases of the original game might have set or cleared bytes here for reasons not modelled in any external spec. An implementation that wants a byte-compatible save can pass these through unchanged: the engine reads the relevant ones during boot, ignores the rest, and rewrites them as it plays.

Two interesting fields in the band have higher-level meaning:

- **Timing/status and transport/action bytes.** The three-byte control cluster at `0x02D4..0x02D6` is not a single enum. Preserve the timing/status tag, active-player index, and transport/action marker separately.
- **Active player sentinel.** A byte that is `0xFF` until the player picks a party member (typically inside towns and combat), then holds the slot index. Used by the gameplay loops as "is anyone currently selected to move".
- **NPC-occupied bitmask.** A byte stamped on town entry that records which of the location's NPCs have an active slot in the active-object table. Used by the town entry helper to decide what slots to allocate; refreshed every town entry, so its saved value matters only for the scene the player is currently in.

## 11. Worked example

A fresh save's roster view begins with the Avatar record at slot zero, followed
by the canonical companion roster at thirty-two-byte stride. The example below
describes the semantic interpretation without reproducing the raw save bytes.

The first record is the Avatar:

- Bytes `00..08`: the Avatar's name, NUL-padded to the fixed nine-byte name field. The questionnaire prompt accepts eight visible characters, so a questionnaire-created name leaves the ninth byte as padding.
- Byte `09`: gender; byte `0A`: class; byte `0B`: status.
- Bytes `0C..0F`: STR, DEX, INT, and MP.
- Bytes `10..15`: current HP, maximum HP, and experience.
- Byte `16`: level or unset-level sentinel.
- Byte `17`: month counter / inn stay counter.
- Byte `18`: padding.
- Bytes `19..1E`: equipment fields.
- Byte `1F`: inn-registry marker / padding.

For a questionnaire-created Avatar, chargen overwrites the entered name,
gender, STR, DEX, INT, and MP. The class remains Avatar and the status remains
good from the seed. Current HP remains 60, maximum HP remains 150, experience
remains 2, and the level byte remains the unset-level sentinel. Equipment-slot
bytes are preserved from the seed and use the helm, body armour, weapon hand,
shield/off hand, ring, and amulet/neck order documented in Section 3.1.

The second record is Shamino in slot one, regardless of recruit state. Records
two through fifteen continue the canonical companion list at thirty-two-byte
stride.

In the factory seed used for a questionnaire-created game, the untouched
`INIT.GAM` and clean-install `SAVED.GAM` images are byte-identical. The starting
counters are food 63, gold 150, keys 2, gems 0, torches 4, and magic powder 0.
The reagent record starts as black pearl 4, blood moss 6, garlic 7, ginseng 6,
mandrake 0, nightshade 3, spider silk 0, and sulfurous ash 0. The party-size
byte is 3, matching Avatar, Shamino, and Iolo in the travelling party.

The same seed places the save clock at year 139, month 4, day 5, 08:35. The
active-player byte is `0xFF` ("no active party member selected"), the status tag
is 0, and the transport/action marker is 28, the clean on-foot/avatar marker in
the seed. The persisted map tuple is scene 13 (Iolo's Hut), saved-scene scratch
0, floor/Z 0, X 15, Y 15. The wind byte is 0; the saved-byte-to-label mapping
remains a weather-system compatibility detail, so tools should preserve values
they do not understand.

In a chargen-only save with no active map yet, the active-object table at `0x06B4` is zero; the engine populates it on first overworld entry from the surface object overlay. The example is shown only as a guide to reading the layout; the exact bytes a fresh chargen produces depend on the entered name, chosen gender, and questionnaire stat rolls.

## 12. Reserved and zero-padded regions

Two spans are zero in the factory seed and in clean-state saves:

- `0x0400..0x05B3` — four hundred thirty-six bytes between the dungeon-map dump and the NPC interaction flags. Function unknown; possibly conversation-state flags layered on top of the NPC-met mask, possibly reserved for unimplemented features.
- `0x07B4..0x105F` — two thousand two hundred twenty bytes between the active-object table and the file end. In memory this region holds the NPC schedule blob, NPC runtime state, NPC path queues, and the world-tile render buffer, all of which are repopulated from the location's NPC files and the active-map loader on map entry. Their contents are transient: an implementation does not need to preserve them across save and load, and the original engine writes them out as part of the flat memory dump only because they happen to live inside the resident region.

## 13. The object-overlay companions

The active-object table embedded in `SAVED.GAM` (Section 8) holds the cast on the *current* map. The other world plane's cast lives in the companion `.OOL` files.

| File         | Size      | Role                                                                                                |
|--------------|-----------|-----------------------------------------------------------------------------------------------------|
| `SAVED.OOL`  | 512 bytes | Runtime working copy. Surface in first 256 bytes, underworld in second 256 bytes.                   |
| `BRIT.OOL`   | 256 bytes | Surface object table. Seed and load-time mirror; read as a save-time staging source.                |
| `UNDER.OOL`  | 256 bytes | Underworld object table. Seed and load-time mirror; read as a save-time staging source and conditionally written during save. |
| `INIT.OOL`   | 256 bytes | Factory seed for the surface (companion to `INIT.GAM`). Read-only at runtime.                       |

The on-disk record layout in every `.OOL` file matches the eight-byte active-object record from Section 8 exactly. The canonical surface seed has a small handful of non-zero records (typically five or six — Britannia ferry-skiffs and a few clustered objects), with the rest zero; the underworld seed is all zeros. The "depends" auxiliary bytes use class-specific encodings; for bare ferry-skiff records, `+0x04` is `0xFF` and `+0x05..+0x07` are zero.

The roundtrip across `.OOL` files is owned by `systems/save-load.md`: load refreshes both per-plane mirrors from `SAVED.OOL`, while save writes the canonical `SAVED.OOL` from staged per-plane data and only has a traced conditional write to `UNDER.OOL`. The "OOL" extension's expansion is unattested; "Object Overlay Layer" is a plausible mnemonic, treated as opaque.

## 14. Open questions

The format is verified by direct byte inspection except where noted. The following points remain open.

- **Dungeon-map dump structure (`0x03B4..0x03FF`).** External references state these seventy-six bytes hold the cumulative dungeon-map exploration record. Zero in factory and clean-state saves, so the byte-level structure is unverified. Likely a packed bitmap: one bit per dungeon-level cell across all dungeons and levels. A captured mid-dungeon save is needed to verify.

- **NPC interaction flag layout (`0x05B4..0x06B3`).** External references state these two hundred fifty-six bytes hold the per-NPC met-and-killed flags. Two hundred fifty-six bytes is consistent with thirty-two NPCs per location across roughly eight major locations, or with a denser packing across the full NPC roster. A save with NPCs met and killed is needed to disambiguate.

- **Unidentified `0x0400..0x05B3`.** Four hundred thirty-six bytes whose function is not pinned down. Possibly conversation-state flags, possibly per-quest milestone bits, possibly per-location visit history.

- **Equipment class tables.** The six equipment slot bytes per character record
  are now mapped and hold equipment item ids or the empty sentinel. Remaining
  exactness work lives in the item metadata tables: per-class restrictions,
  strength/capability gates, combat values, and ring/amulet special effects.

- **Spell-charge slot enumeration.** The forty-eight-byte spell-charge stock is verified at the byte level, but the exact mapping between slot index and spell name has been derived from external references rather than from observation.

- **The "OOL" expansion.** "Object Overlay Layer" is a working mnemonic; no in-game string or external reference attests it.

- **Save-time mirror branch.** The save handler reads both per-plane `.OOL` files into staging, conditionally writes `UNDER.OOL`, and writes the canonical `SAVED.OOL`. The exact disk/phase-state value names that gate the conditional branch remain open (see `systems/save-load.md`).

- **Transport/status value table.** Offsets `0x02D4` and `0x02D6` are now separated by consumer, and the known transport-marker families are public in `systems/vehicles.md`. The exact numeric sub-mapping, stats-panel glyph interpretation, and remaining mode-loop readers still need reconciliation into one table. Treat unrecognized values as opaque and preserve them.

- **Historical class/gender byte order mismatch.** Earlier external references swap the gender and class positions. The verified order is gender at `+0x09`, class at `+0x0A`, status at `+0x0B`. Implementations using older third-party material should re-verify against actual save bytes.

## 15. Sources

The byte-level layout described here was derived from the project's private save-format notes, runtime-state map, and semantic summaries of the save/load handlers. This public spec paraphrases the resulting behaviour and field positions; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, or implementation listings.

- The first-pass byte-level survey of the save image, the `.OOL` family, the canonical companion roster, and the offset-by-offset verification of inventory and runtime fields — `u5-decomp/formats/saves.md`.
- The runtime-state map used to cross-check persistent field positions — `u5-decomp/formats/ds-bss-map.md`.
- The fresh-seed counter, reagent, clock, and location values were cross-checked
  against a clean local asset image by reading the named fields documented
  above; this spec does not reproduce the raw seed bytes.
- The B-Board transport marker writes — `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`.
- The overworld per-turn animator's `Q`/`T` and transport-marker pendulum reads — `u5-decomp/functions/MAINOUT_OVL/0x1A60_mainout_per_turn_epilogue.md`.
- The stats-panel transport/status glyph readers — `u5-decomp/functions/ULTIMA_EXE/0x2900_redraw_full_stats.md`.
- The Moonstone gate-slot writer and Search/Get recovery behaviour — local CAST and SJOG helper analysis summarized without copying implementation text.
- The save handler's open-write-close sequence, byte-image flush to `SAVED.GAM`, per-plane `.OOL` staging reads, conditional `UNDER.OOL` mirror write, and canonical `SAVED.OOL` write — `u5-decomp/functions/CAST2_OVL/0x10FE_save_game.md`.
- The load handler's byte-image read of `SAVED.GAM` into the same region, the empty-save guard, the `SAVED.OOL` read, and the mirror-write of `BRIT.OOL` and `UNDER.OOL` — `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.
- The chargen flow's per-record write to roster slot zero (name, gender, STR, DEX, INT, and MP) and preservation of seed class/status/HP/experience fields — `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.
- The equipment slot order, empty sentinel, carried-equipment counter band, and
  R-Ready stock mutations are derived from the updated ZSTATS overlay notes
  and summarized publicly in `u5-spec/systems/inventory.md`.
- The save and load systems' overall semantics, file roles, and mirror-write contract — `u5-spec/systems/save-load.md`.
- The active-object record layout and the in-memory table semantics — `u5-spec/systems/active-objects.md`.
- The calendar and clock fields' cascade rules and persistence — `u5-spec/systems/time.md`.
