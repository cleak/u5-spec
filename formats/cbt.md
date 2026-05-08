# CBT Combat Arenas

Format specification for the combat-arena files `BRIT.CBT` and `DUNGEON.CBT`. These files provide the small tactical maps used by combat mode: one outdoor arena bank and one dungeon-room arena bank. Combat rules, monster AI, turn order, attacks, escape, and post-combat restoration are described in `systems/combat.md`; this document covers the arena records they consume.

## 1. Overview

Each `.CBT` file is a bank of fixed-size arena records. Every record has the same shape:

- Eleven rows.
- Thirty-two bytes per row.
- The first eleven bytes of each row are visible terrain cells.
- The remaining twenty-one bytes of each row are opaque combat metadata.

The visible terrain is therefore an eleven-by-eleven grid. The row stride is already the same stride the runtime terrain grid uses, so the engine can copy an arena row into its in-memory combat terrain with minimal reshaping. The metadata band is loaded with the arena, but its exact sub-layout is still open; preserve it as opaque bytes until individual fields are re-derived.

The files have no header, no arena table, no compression, and no per-record names. Arena identity comes from the index used by the caller. A complete arena record is three hundred fifty-two bytes: eleven rows times a thirty-two-byte row stride.

## 2. The Two Files

`BRIT.CBT` contains the outdoor arena bank. It has sixteen records, matching the sixteen outdoor terrain or encounter classes selected by the terrain-combat setup path. When a hostile overworld object triggers combat, the engine derives an arena index from the object's tile class and loads the matching record from this bank. The selected record begins at `arena_index * 352`.

`DUNGEON.CBT` contains the dungeon-room arena bank. It is much larger, with seven dungeon banks of sixteen records each: one arena slot for every possible low nibble of a room-trigger cell in the dungeons that have authored room triggers. The file size is exactly one hundred twelve records. Older third-party summaries sometimes say one hundred eleven; the room-entry lookup reaches the final record as Doom slot fifteen, so treat all one hundred twelve records as real.

Both files use the same record layout. A decoder should be parameterised by file name and record count, not by a separate structure per file.

| File | Expected size | Records | Role |
|------|--------------:|--------:|------|
| `BRIT.CBT` | 5,632 bytes | 16 | Outdoor and terrain-triggered combat arenas. |
| `DUNGEON.CBT` | 39,424 bytes | 112 | Dungeon-room arena banks: seven banks times sixteen low-nibble slots. |

## 3. Arena Record Shape

An arena record is a fixed eleven-row block. Each row is thirty-two bytes:

- Columns zero through ten: terrain cells visible on the tactical map.
- Columns eleven through thirty-one: row-local opaque metadata.

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

The twenty-one metadata bytes after each terrain row are combat-specific annotations, but the exact sub-layout is not yet specified. Some bytes appear to participate in arena setup, exits, hazards, or special-cell handling, but individual byte positions should not be named until they are re-derived.

Do not treat the metadata band as the complete actor-placement model. Terrain combat also consults resident per-arena tables outside the `.CBT` file for spawn counts, leader monster replacement, and fixed placement-slot coordinates. That means not every placement detail is encoded in `.CBT`; the file provides arena-local terrain and metadata, while resident tables provide global per-arena spawning parameters.

A clean implementation should preserve all metadata bytes even if it does not initially decode them. Dropping the metadata band will make combat maps renderable but not behaviourally faithful.

## 6. Outdoor Arena Selection

Outdoor combat enters through the terrain-combat setup path. The triggering active object's tile class is reduced to one of sixteen outdoor arena indices. The selected `BRIT.CBT` record supplies the arena terrain. Separate resident tables determine:

- The maximum or exact monster count for that arena.
- Whether the monster count is randomised.
- The sixteen fixed placement-slot coordinates.
- Which leader replacement tile to use for the first subset of monsters.

The arena record and those resident tables are therefore a pair. `BRIT.CBT` answers "what does the battlefield look like?" The resident tables answer "how many things appear, where do they stand, and which tile class should represent them?"

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

Dungeon mode itself does not run the combat round loop. It loads or selects the arena, stamps combat-entry state, and calls the combat framer. When combat returns, the dungeon loop resumes at the original dungeon cell.

## 8. Runtime Copy

On combat entry, the selected arena is copied into a combat terrain grid with the same thirty-two-byte row stride. The round loop and AI then read the runtime grid. The original `.CBT` file is not touched again until the next combat.

Actors are not stored in `.CBT`. They are placed into combat's active-object and combat-effect tables by setup helpers after the arena is loaded. The actor tables hold party members, monsters, summons, and transient effects; the arena record only supplies the battlefield.

## 9. Validation And Invariants

A byte-compatible reader should enforce these invariants:

- `BRIT.CBT` is exactly 5,632 bytes and splits into sixteen records.
- `DUNGEON.CBT` is exactly 39,424 bytes and splits into one hundred twelve records: seven banks of sixteen records.
- Every record is exactly three hundred fifty-two bytes.
- Every row in a record is exactly thirty-two bytes.
- Terrain coordinates are valid only for X and Y in `0..10`; bytes outside the first eleven columns of a row are metadata, not visible terrain cells.
- The file does not encode actors. Party members, monsters, projectiles, and effects are runtime table entries placed after the arena is loaded.
- Unknown metadata bytes must be preserved byte-for-byte on round trip.

A tolerant inspection tool may accept any file whose size is divisible by three hundred fifty-two, but a compatibility-mode loader should use the expected sizes above so a truncated or overlong arena bank is caught early.

## 10. Implementation Notes

A minimal `.CBT` decoder should:

1. Verify that file size is divisible by the fixed arena-record size.
2. Split the file into records.
3. For each record, split eleven thirty-two-byte rows.
4. Expose the first eleven bytes of each row as terrain.
5. Preserve the twenty-one metadata bytes per row as opaque data until the full sub-layout is decoded.

A renderer can display an arena using only the terrain grid and the global tile catalogue. A gameplay engine must additionally interpret metadata, resident per-arena spawn tables, and active-object placement rules.

## 11. Cross-References

- Combat-system arena loading, monster placement, round loop, actor table, AI, and enter/exit framing: `systems/combat.md`.
- Dungeon room triggers that select `DUNGEON.CBT` arenas: `systems/dungeon-mode.md`.
- The active-object table that receives placed actors: `systems/active-objects.md`.
- The global tile vocabulary used by terrain cells: `formats/tiles.md`.
- The static dungeon geometry that triggers dungeon-room combat: `formats/dungeon-dat.md`.

## 12. Open Questions

- **Metadata sub-layout.** The twenty-one row metadata bytes are known to exist and to be loaded with the arena, but their exact partition is not fully decoded. Existing third-party breakdowns do not match the record budget cleanly.
- **Arena edge semantics.** Open edges, blocked edges, and flee exits are runtime behaviours likely encoded in metadata plus tile-class tables; the exact split is still open.
- **Dungeon chest-trap arena selection.** Room-trigger selection is fixed by scene and low nibble. Chest traps may also select from the dungeon arena bank, but that Open-handler lookup is not described here yet.
- **Ambush setup.** The ambush-specific setup path appears to shuffle placement slots and may use metadata differently from ordinary terrain combat. That path needs deeper decoding.

## 13. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It intentionally omits decompiled code, assembly, implementation addresses, and raw private offset tables.

- First-pass map and arena survey, including `.CBT` record size, terrain-grid dimensions, row stride, outdoor record count, and dungeon record count: `u5-decomp/formats/maps.md`.
- Internal combat enter/exit framer and arena setup analysis.
- Internal terrain-combat setup analysis, including outdoor arena selection, monster-count lookup, placement-slot tables, and leader replacement rules.
- Internal combat round-loop analysis, including runtime terrain-grid consumption.
- Internal combat actor-command, AI, and target-selection analyses in the eleven-by-eleven arena coordinate space.
- Internal dungeon-mode room-trigger analysis for the exact scene/low-nibble relationship to `DUNGEON.CBT`.
- Existing combat-system prose used for cross-checking runtime semantics: `u5-spec/systems/combat.md`.
