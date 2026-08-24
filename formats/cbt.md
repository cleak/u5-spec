# CBT Combat Arenas

Format specification for the combat-arena files `BRIT.CBT` and `DUNGEON.CBT`. These files provide the small tactical maps used by combat mode: one outdoor arena bank and one dungeon-room arena bank. Combat rules, monster AI, turn order, attacks, escape, and post-combat restoration are described in `systems/combat.md`; this document covers the arena records they consume.

## 1. Overview

Each `.CBT` file is a bank of fixed-size arena records. Every record has the same shape:

- Eleven rows.
- Thirty-two bytes per row.
- The first eleven bytes of each row are visible terrain cells.
- The remaining twenty-one bytes of each row are combat metadata.

The visible terrain is therefore an eleven-by-eleven grid. The row stride is already the same stride the runtime terrain grid uses, so the engine can copy an arena row into its in-memory combat terrain with minimal reshaping. The metadata band is loaded with the arena. Several outdoor-combat slices are now identified, but the remaining bytes should still be preserved until their consumers are traced.

The files have no header, no arena table, no compression, and no per-record names. Arena identity comes from the index used by the caller. A complete arena record is three hundred fifty-two bytes: eleven rows times a thirty-two-byte row stride.

## 2. The Two Files

`BRIT.CBT` contains the outdoor arena bank of sixteen records. The record index is chosen by the terrain-combat entry step from the **ground the fight starts on** and the party's transport state — the world terrain tile under the hostile object, a water/river predicate, whether the party is aboard a ship, and one test on the triggering object itself: whether it belongs to the ship family. Apart from that single ship-family test, the object's own sprite byte is not an input to the arena choice, and the arena is never derived from the object's class. Section 6 summarises the selection and `systems/encounters.md` Section 4 carries the full ordered table. The selected record begins at `arena_index * 352`.

An earlier revision of this document said the engine "derives an arena index from the object's tile class". That is wrong and is withdrawn: the quantity computed from the object's sprite byte is the encounter's **combat class id**, which drives spawn count, spawn stats, banner text, and spawned sprites, and is independent of the arena index. Two of the sixteen records (index 0, used by the scripted duel entry, and index 9) are never produced by the terrain selector at all.

`DUNGEON.CBT` contains the dungeon-room arena bank. It is much larger, with seven dungeon banks of sixteen records each: one arena slot for every possible low nibble of a room-trigger cell in the dungeons that have authored room triggers. The file size is exactly one hundred twelve records. Older third-party summaries sometimes say one hundred eleven; the room-entry lookup reaches the final record as Doom slot fifteen, so treat all one hundred twelve records as real.

Doom slot fifteen is the stock final-room arena. It is selected by Doom's
deepest room-id-fifteen trigger and is not optional filler. Its metadata band
contains the special setup marker that feeds the combat absorption handoff into
ENDGAME. In the shipped record, the first dungeon-room setup source cell read by
the room-NPC setup pass is the `0x3C` absorbable-field family marker. A loader that
keeps only the visible eleven-by-eleven terrain cells will render the room but
will not preserve the terminal quest route.

Both files use the same record layout. A decoder should be parameterised by file name and record count, not by a separate structure per file.

| File | Expected size | Records | Role |
|------|--------------:|--------:|------|
| `BRIT.CBT` | 5,632 bytes | 16 | Outdoor and terrain-triggered combat arenas. |
| `DUNGEON.CBT` | 39,424 bytes | 112 | Dungeon-room arena banks: seven banks times sixteen low-nibble slots. |

## 3. Arena Record Shape

An arena record is a fixed eleven-row block. Each row is thirty-two bytes:

- Columns zero through ten: terrain cells visible on the tactical map.
- Columns eleven through thirty-one: row-local metadata.

The terrain grid's coordinate system is:

- X in `0..10`, west-to-east.
- Y in `0..10`, north-to-south.
- Row-major storage.

The runtime also treats the grid as eleven-by-eleven inside a padded thirty-two-byte row. This is why combat code can address cells by row stride rather than by multiplying by eleven. A reader should preserve the full thirty-two-byte row even if it initially exposes only the terrain cells.

The file arithmetic is:

```text
arena_start = arena_index * 352
row_start = arena_start + row * 32
terrain_cell = row_start + x
metadata_byte = row_start + column
```

Here `x` is a visible terrain coordinate in `0..10`, and `column` is a metadata-band coordinate in `11..31`. These formulas describe both the file layout and the row stride used by the runtime terrain grid. They do not imply that actors are stored in the arena record.

## 4. Terrain Cells

Terrain cells are one-byte tile indices drawn from the game's global tile vocabulary. They identify walls, floors, water, swamp, bridges, doors, ladders, open exit edges, hazards, and other combat-map scenery.

Combat uses terrain in three ways:

- **Rendering.** The combat renderer paints each visible terrain byte as a top-down tile, then composites actors over it.
- **Movement.** The step-or-attack primitive rejects impassable cells and allows walkable cells.
- **Round safety.** The round loop defensively skips any actor whose record says it is standing on a wall-class terrain cell.

The terrain byte alone is not the entire collision model. Metadata, resident tables, and tile-class tables may refine edge exits, hazards, placement, and special encounter behaviour.

## 5. Metadata Band

The twenty-one metadata bytes after each terrain row are combat-specific annotations. The full sub-layout is not complete, but the outdoor arena loader consumes four fixed slices from each selected `BRIT.CBT` record after loading the whole three-hundred-fifty-two-byte block:

| Record row | Metadata columns | Known role |
|---:|---:|---|
| 3 | 11-16 | Six party entry X coordinates, indexed by party slot. |
| 3 | 17-22 | Six party entry Y coordinates, indexed by party slot. |
| 6 | 11-26 | Sixteen monster placement-slot X coordinates. |
| 7 | 11-26 | Sixteen monster placement-slot Y coordinates. |

Rows and columns in this table are zero-based within the arena record. The two sixteen-byte coordinate slices are indexed by the terrain-combat placement-slot array. Ordinary terrain combat walks the slots in identity order. The terrain setup helper contains a placement-slot shuffle branch, but the traced ordinary terrain caller does not set it; live ambush and rest/camp setup must be specified from their own helpers rather than inferred from this dormant branch.

The two six-byte slices are the outdoor arena's **party entry coordinates**, and
they use exactly the convention the `DUNGEON.CBT` party rows use below: for
party slot `i`, X comes from column `11 + i` and Y from column `17 + i`.
Outdoor combat always reads them from record row 3, with no facing seed. The
terrain setup pass seats the party from these coordinates before it places any
monster, so party seats never consume a monster placement slot and never move
when the monster count changes. In the shipped wilderness arenas the six party
seats sit on the southern rows (typically rows 7-10) while the sixteen monster
placement slots occupy the northern rows (typically rows 0-5). Three shipped
records are worth knowing about when validating a loader: the scripted-duel
arena 0 seats the party in the middle with monster slots in the four corners,
arena 10 puts every one of its sixteen monster slots on the single centre cell
(5, 5), and arena 9 has all-zero monster placement rows because no live selector
chooses it.

The resident placement-coordinate tables are load-time scratch. A selected
`BRIT.CBT` record overwrites them before ordinary terrain setup places actors,
and the setup helper then reads those resident copies. Therefore the selected
arena record is the authoritative placement source; a fixed resident coordinate
array is only a cached copy of the last loaded arena record, not independent
global placement data.

Do not treat the metadata band as the complete actor-placement model. Terrain combat also consults resident per-class tables outside the `.CBT` file for spawn counts and for the companion-class substitution applied to early spawn slots. Placement-slot coordinates are arena-local metadata copied from the selected record into resident tables before placement. That means not every placement detail is encoded in `.CBT`; the file provides arena-local terrain and placement geometry, while resident tables provide global class and spawning parameters.

The `DUNGEON.CBT` room loader is confirmed to load the same complete record
shape into the combat terrain buffer. Dungeon-room setup then performs its own
metadata pass. For stock `0xF?` room-trigger entries, that pass first reads
party-entry coordinates from a facing-selected metadata row, then scans sixteen
room source cells:

| Record row | Metadata columns | Dungeon-room role |
|---:|---:|---|
| 1 | 11-16 and 17-22 | Party X/Y coordinates for one room-entry facing seed. |
| 2 | 11-16 and 17-22 | Party X/Y coordinates for one room-entry facing seed. |
| 3 | 11-16 and 17-22 | Party X/Y coordinates for room-entry facing seeds `0` and `5`. |
| 4 | 11-16 and 17-22 | Party X/Y coordinates for the default room-entry facing seed. |
| 5 | 11-26 | Sixteen room source cells. |
| 6 | 11-26 | X coordinate for each room source cell. |
| 7 | 11-26 | Y coordinate for each room source cell. |

Rows and columns are zero-based. For party slot `i`, the setup helper reads X
from column `11 + i` and Y from column `17 + i` of the selected party row, for
as many party slots as are currently active. The selected row comes from the
room-entry facing seed: seed `3` selects row 1, seed `1` selects row 2, seeds
`0` and `5` select row 3, and all other seeds select row 4.

The sixteen source cells are consumed in index order `0..15`. Source index `i`
uses the source byte from row 5 column `11 + i`, X from row 6 column `11 + i`,
and Y from row 7 column `11 + i`. A zero source byte is empty. Nonzero source
bytes are converted as follows:

- Ordinary source: if the source is at least `0x40`, and its masked family is
  neither `0xB4` nor `0xE8`, the setup class is `(source - 0x40) / 4` and the
  actor is placed through the ordinary room-combat path. **The `0xEC..0xEF`
  family is not excluded by this test and therefore takes this path.**
- Special source: all lower values and the excluded `0xB4`/`0xE8` families use
  the special room-placement path with the source value as the setup id.
- Random-special family: source values whose masked family is `0xEC` are
  reclassified *after* the ordinary/special decision above. They keep the
  **ordinary** placement path, and only their derived setup class is replaced
  by one of four pre-rolled room-special setup ids, chosen by the source's low
  two bits.

The two placement paths differ in what they create, and this is the difference
an engine must reproduce:

- **Ordinary path.** Allocates a combat actor descriptor (from the first free
  monster slot, above the six party slots) *and* a renderer-facing active-object
  record, links them, and sets the active-object tile pair to
  `setup_class * 4 + 0x40`. Its auxiliary byte receives the class's starting HP.
  These are real, actable combatants.
- **Special path.** Allocates only the renderer-facing active-object record. No
  combat descriptor is created and no descriptor back-link is written, so the
  round loop never gives these placements a turn. The active-object tile pair
  and auxiliary byte both receive the raw setup id.

Both paths write the source-owned X and Y into the active-object record and
stamp the current dungeon level into it.

Special setup ids have one additional post-placement rule that overwrites the
placed active object's auxiliary byte (byte five of the record):

| Setup id | Auxiliary-byte rule |
|---:|---|
| `1` | Write `Z * 3 + 7`, where `Z` is the current dungeon level. |
| `2` | Write `random_range(1, 10 * Z + 10)`. |
| `3` | Write `random_range(0, 7)`. |
| `4` | Write `random_range(0, 7)`. |
| `5` | Write `30 + random_range(0, 3)`. |
| `6` | Write `4 + random_range(0, 2)`. |
| `7` | Write `1 + random_range(0, 7)`. |
| `8` | Write `1 + random_range(0, 7)`. |
| `9` | Write `random_range(0, 3)`. |
| `10` | Write `42 + random_range(0, 2)`. |
| `11` | Write `9 + random_range(0, 5)`. |
| `12` | Write `45 + random_range(0, 2)`. |
| `13` | Write `1 + random_range(0, 7)`. |
| `14` | Write `1`. |
| `15` | Write `1 + random_range(0, 7)`. |
| `16+` | No auxiliary-byte post-write in this helper. |

The auxiliary-byte post-write above applies **only to special placements**. It
is gated on the placement path, not on the numeric value of the id, and it is
the only write this helper performs after the placer returns. A special
placement whose id is `16` or higher therefore keeps whatever the placer itself
stored in that byte, which for the special path is the setup id.

**The random-special family `0xEC..0xEF` is an ordinary placement, not a
marker.** Before the sixteen-source scan, the helper pre-rolls four setup ids by
sampling this eight-entry palette four times with `random_range(0, 7)`:
`[20, 21, 22, 34, 33, 24, 31, 24]`. All four draws happen once per setup call,
before any source is examined. During the scan, a source in this family is
classified as ordinary (it is at least `0x40` and its masked family is neither
`0xB4` nor `0xE8`), and then its setup class is overwritten with the pre-rolled
id selected by the source's low two bits. It is placed on the ordinary path with
a full combat actor and the tile derived from the substituted class, exactly
like any other ordinary source. It receives no auxiliary-byte post-write because
that post-write is gated on the special path, **not** because it is inert.

Reading a `0xEC..0xEF` source with the ordinary class rule would yield setup
class forty-three, which is one of the two reserved all-zero identity gaps in the
class table (`catalogs/monster-bestiary.md` Section 1). That is the point of the
substitution: the family exists precisely so a room author can ask for "some
random vermin" instead of naming a class. The excluded `0xE8..0xEB` family
decodes to the other reserved gap, class forty-two, and is handled by sending it
to the special path instead.

The palette entries are ordinary monster classes: `20` Giant Rat, `21` Bat,
`22` Giant Spider, `34` Python, `33` Skeleton, `24` Slime (twice), and `31`
Insect Swarm. Because the four ids are rolled once per setup and then indexed by
the source's low two bits, all sources sharing a low-bit value in one room draw
the same class, while the four low-bit values can draw four different classes.

This family is present in shipped content: across the one hundred twelve stock
dungeon-room records it accounts for one hundred forty-four source bytes spread
over fifteen records - rooms one through six of the Wrong bank and rooms zero
through six, eight, and ten of the Covetous bank.
Modelling it as an inert marker leaves those fifteen stock rooms empty of the
randomised vermin they are supposed to spawn.

The final Doom marker is a genuine special placement in the `16+` category:
source `0x3C` is placed on the special active-object path. Viewport composition
projects that family into the renderer companion band recognized by the
committed-action combat absorption hook. The source is not converted into an
ordinary monster kind. Genuine special placements do
stay on the special active-object path and never become ordinary monster setup
classes or party slot descriptors; only the `0xEC..0xEF` family, which is not a
special placement at all, appears to contradict that rule.

**Special ids present in shipped rooms.** Every id from `1` through `15` except
`14` occurs in the stock records, so their auxiliary post-writes are all
behavior-visible: `1` and `8` are the most common (roughly seventy occurrences
each), `2` and `4` next, and `6`, `7`, `9`, `13` are rare. Ids `0x1E`, `0x1F`,
the single Doom `0x3C`, and the excluded `0xE8` family (`0xE8` and `0xEB`) also
occur and fall in the `16+` no-post-write category.

The placement scan runs for stock room-trigger bytes `0xF0..0xFF` in the
dungeon room-enter path. Runtime `0xA?` room-helper cells use the same arena
selection and party-entry readback but skip the sixteen-source placement scan.
This dungeon-room metadata pass is separate from the outdoor arena loader. Do
not infer it from the outdoor placement-coordinate slices alone.

A clean implementation should preserve all metadata bytes even if it only consumes the identified slices. Dropping the metadata band will make combat maps renderable but not behaviourally faithful.

## 6. Outdoor Arena Selection

Outdoor combat enters through a terrain-combat entry step that runs *before* the
combat framer. That step chooses the `BRIT.CBT` record from the world terrain
tile under the triggering active object, a water/river predicate, whether the
party is aboard a ship, and whether the triggering object belongs to the ship
family. Apart from that one ship-family test, the triggering object's own sprite
byte is not an input to the arena choice.
The full selection table is published in `systems/encounters.md` Section 4; in
outline, ship-versus-ship and party-aboard-ship cases take dedicated arenas,
water takes a water arena, the Shadow Lord takes his own arena, and everything
else takes the arena matching the ground type (swamp, grass, brush, desert,
forest, hills, bridge, cobble), with a scene-dependent fallback.

The triggering object's own sprite byte selects something different: the
encounter's **combat class id**, which drives the spawn count, spawn stats, and
spawned sprites. Arena index and class id are independent; do not derive either
from the other. The ship family is the single point of contact between the two
selections - it forces combat class 1, and it also steers the arena choice to
index 14 when the party is itself aboard a ship, or index 12 otherwise.

The selected `BRIT.CBT` record supplies the arena terrain, the six party entry
coordinate pairs, and the sixteen monster placement-slot coordinate pairs from
its metadata band, as described above. Separate resident class tables determine:

- The maximum or exact monster count for the encounter's class.
- Whether that count is randomised.
- Which companion class eligible early-spawn monsters can roll into.

The arena record and those resident tables are therefore a pair. `BRIT.CBT` answers "what does the battlefield look like, and where does everyone start?" The resident class tables answer "how many things appear, and what are they?"

## 7. Dungeon Arena Selection

Dungeon combat enters through the dungeon room-entry helper. The current dungeon scene and the low nibble of the trigger cell identify a `DUNGEON.CBT` record. The selected arena uses the same eleven-by-eleven terrain and metadata layout as an outdoor arena, but its content represents a fixed dungeon room encounter.

The arena bank is not arranged as eight equal dungeon groups. It is arranged as seven sixteen-record banks because the stock Despise dungeon record has no room-trigger cells. The runtime computes a dungeon-arena bank from the scene byte using these rules:

1. Subtract 33 from the scene byte to get the zero-based `DUNGEON.DAT` record number.
2. Records 0 and 1 both select arena bank 0.
3. Records 2 and higher select `record_number - 1`.
4. The low nibble of the room-trigger cell is the arena slot within that bank.
5. The final `DUNGEON.CBT` record number is `arena_bank * 16 + arena_slot`; each record is 352 bytes.

For stock data this yields the following binding:

| `DUNGEON.DAT` record | Scene | Dungeon | Arena bank | `DUNGEON.CBT` records |
|---:|---:|---|---:|---:|
| 0 | 33 | Deceit | 0 | 0-15 |
| 1 | 34 | Despise | 0 | None in stock geometry |
| 2 | 35 | Destard | 1 | 16-31 |
| 3 | 36 | Wrong | 2 | 32-47 |
| 4 | 37 | Covetous | 3 | 48-63 |
| 5 | 38 | Shame | 4 | 64-79 |
| 6 | 39 | Hythloth | 5 | 80-95 |
| 7 | 40 | Doom | 6 | 96-111 |

Despise shares the bank-zero arithmetic path, but the shipped `DUNGEON.DAT` record contains no `0xF?` room-trigger cells, so stock play never uses a Despise room arena. A custom Despise trigger would use the same formula and therefore select bank zero.

For stock Doom, arena slot fifteen is reached from the deepest level's final
room marker and maps to record `111`. That record's metadata band participates
in combat setup for the terminal absorption handoff. This is currently the
only dungeon-room arena with a confirmed endgame handoff role. In compatibility
terms, record `111` must preserve the absorbable-field marker in the first
source cell consumed by the dungeon-room setup scan.

Dungeon mode itself does not run the combat round loop. It loads or selects the arena, stamps combat-entry state, and calls the combat framer. When combat returns, the dungeon loop resumes at the original dungeon cell.

## 8. Runtime Copy

On combat entry, the selected arena is copied into a combat terrain grid with the same thirty-two-byte row stride. The round loop and AI then read the runtime grid. The original `.CBT` file is not touched again until the next combat.

Actors are not stored in `.CBT`. They are placed into combat's active-object and combat-effect tables by setup helpers after the arena is loaded. Because that runtime grid and its metadata band are just a resident buffer, a caller can also **synthesise** a record there without reading either `.CBT` file. Dungeon wandering-monster combat does exactly that: the dungeon room painter writes an eleven-by-eleven terrain grid plus a full party-entry and source metadata band into the buffer, then the framer's ambush entry mode runs the same room-combat setup helper over it. The layouts in Section 5 therefore describe both on-disk records and synthesised ones; see `systems/dungeon-mode.md` Section 14.1. The actor tables hold party members, monsters, summons, and transient effects; the arena record only supplies the battlefield.

## 9. Validation And Invariants

A byte-compatible reader should enforce these invariants:

- `BRIT.CBT` is exactly 5,632 bytes and splits into sixteen records.
- `DUNGEON.CBT` is exactly 39,424 bytes and splits into one hundred twelve records: seven banks of sixteen records.
- Every record is exactly three hundred fifty-two bytes.
- Every row in a record is exactly thirty-two bytes.
- Terrain coordinates are valid only for X and Y in `0..10`; bytes outside the first eleven columns of a row are metadata, not visible terrain cells.
- The file does not encode actors. Party members, monsters, projectiles, and effects are runtime table entries placed after the arena is loaded.
- Unknown or currently unconsumed metadata bytes must be preserved byte-for-byte on round trip.

A tolerant inspection tool may accept any file whose size is divisible by three hundred fifty-two, but a compatibility-mode loader should use the expected sizes above so a truncated or overlong arena bank is caught early.

## 10. Implementation Notes

A minimal `.CBT` decoder should:

1. Verify that file size is divisible by the fixed arena-record size.
2. Split the file into records.
3. For each record, split eleven thirty-two-byte rows.
4. Expose the first eleven bytes of each row as terrain.
5. Preserve the twenty-one metadata bytes per row as opaque data until the full sub-layout is decoded.

A renderer can display an arena using only the terrain grid and the global tile catalogue. A gameplay engine must additionally interpret the metadata band, the resident per-class spawn tables, and the active-object placement rules.

## 11. Cross-References

- Combat-system arena loading, monster placement, round loop, actor table, AI, and enter/exit framing: `systems/combat.md`.
- Dungeon room triggers that select `DUNGEON.CBT` arenas: `systems/dungeon-mode.md`.
- The active-object table that receives placed actors: `systems/active-objects.md`.
- The global tile vocabulary used by terrain cells: `formats/tiles.md`.
- The static dungeon geometry that triggers dungeon-room combat: `formats/dungeon-dat.md`.

## 12. Format Boundary And Runtime Work

The `.CBT` byte-layout contract is complete at arena-record depth: record size,
row stride, terrain-band width, metadata-band preservation, and stock record
counts are fixed. Remaining work belongs to runtime consumers of the metadata
band and to caller discovery.

- **Remaining metadata sub-layout.** The outdoor loader consumes the two
  six-byte setup tables and the two sixteen-byte placement-coordinate tables
  documented above. The remaining metadata bytes, and the per-entry meanings of
  the two six-byte setup tables, are not fully decoded. Existing third-party
  breakdowns do not match the record budget cleanly.
- **Dungeon-room setup scan.** The room-trigger setup pass that consumes
  dungeon metadata is now identified for the sixteen source cells beginning at
  row five, metadata column eleven, including the boundary between ordinary
  class-derived combatants and special-placement sources. Remaining work is
  per-subtype naming for the non-final special-placement sources, not the scan
  shape or terminal Doom handoff.
- **Arena edge semantics.** Open edges, blocked edges, and flee exits are
  runtime behaviours likely encoded in metadata plus tile-class tables; the
  exact split is still open.
- **Non-room dungeon combat callers.** Room-trigger selection is fixed by scene
  and low nibble. No traced dungeon chest path currently selects from the
  dungeon arena bank; add any future non-room caller here only after its arena
  lookup is identified.
- **Ambush setup callers.** The terrain setup helper has a placement-slot
  shuffle flag, but the traced ordinary terrain caller does not set it. The
  caller and presentation details for ambush-style setup remain separate open
  work.

## 13. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It intentionally omits decompiled code, assembly, implementation addresses, and raw private offset tables.

- Terrain-combat entry chain retrace of 2026-08-22 - outdoor arena selection from
  world terrain plus ship state, the class-id derivation and its separation from
  the arena index, the reachable spawn-count invariant, the forty-eight-entry
  companion-class table, and the party-seating pass that runs before monster
  placement. Source provenance: derived from private analysis in
  `../u5-decomp/notes/` and `../u5-decomp/functions/ULTIMA_EXE/`.
- First-pass map and arena survey, including `.CBT` record size, terrain-grid dimensions, row stride, outdoor record count, and dungeon record count: `../u5-decomp/formats/`.
- Outdoor combat arena loader analysis, including the four metadata slices copied from each selected `BRIT.CBT` record into resident combat setup tables: `u5-decomp/functions/ULTIMA_EXE/`.
- Internal combat enter/exit framer and arena setup analysis.
- Internal terrain-combat setup analysis, including outdoor arena selection, per-class monster-count lookup, party-entry and placement-slot tables, and companion-class roll rules.
- Internal combat round-loop analysis, including runtime terrain-grid consumption.
- Internal combat actor-command, AI, and target-selection analyses in the eleven-by-eleven arena coordinate space.
- Internal dungeon-mode room-trigger analysis for the exact scene/low-nibble relationship to `DUNGEON.CBT`.
- Internal DNGLOOK room setup analysis for the dungeon-room metadata scan and
  special active-object placement path. Source provenance: derived from private
  analysis notes `../u5-decomp/functions/DNGLOOK_OVL/`
  and `../u5-decomp/functions/ULTIMA_EXE/`, whose
  2026-08-22 retraces establish that the `0xEC..0xEF` family stays on the
  ordinary placement path and that the special path allocates an active-object
  record without a combat descriptor.
- Arena synthesis for the ambush entry mode: derived from private analysis in
  `../u5-decomp/functions/DNGLOOK_OVL/` and `../u5-decomp/notes/`.
- Stock-content census of the dungeon-room source band, counting the
  `0xEC..0xEF` family and each special setup id across all one hundred twelve
  shipped records, performed against the local clean install.
- Local binary verification against `C:\Games\U5-Clean\DUNGEON.CBT` for the
  final Doom record's absorbable-field setup marker.
- Existing combat-system prose used for cross-checking runtime semantics: `u5-spec/systems/combat.md`.
