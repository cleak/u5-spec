# BRIT.DAT

Format specification for `BRIT.DAT`, the static Britannia surface map. Runtime movement, lighting, encounters, vehicles, and mode transitions are covered by the overworld and related system specs; this document covers the file shape and the map-reader contract.

## 1. Overview

`BRIT.DAT` represents the 256-by-256 tile grid of Britannia, the surface world. Each logical map cell is one byte: a tile index in the shared world tile catalogue. The logical grid is divided into 256 chunks arranged as a 16-by-16 chunk grid. Each chunk is 16 cells wide by 16 cells tall, for 256 bytes per chunk.

The file does not store all 256 logical chunks. Pure open-ocean chunks are omitted and synthesized by the loader. The missing chunks are identified by a 256-entry chunk-index table in resident data: each logical chunk slot either names a stored 256-byte block in `BRIT.DAT` or carries the all-water sentinel. The sentinel is the all-ones byte, decimal `255`; valid stored-block entries are therefore `0..204`. A reader needs both `BRIT.DAT` and the decoded chunk-index table to reconstruct the full 256-by-256 surface grid.

`BRIT.DAT` is static terrain. It does not contain active monsters, vehicles, dropped items, moongate schedule or animation state, party position, visibility state, or location-entry metadata. Those are supplied by runtime state, companion object files, or resident tables.

## 2. File Shape

The file is exactly 52,480 bytes:

| Quantity | Value |
|----------|------:|
| Stored chunk count | 205 |
| Bytes per stored chunk | 256 |
| Total file size | 52,480 |
| Logical chunk count | 256 |
| Logical world size | 256 x 256 cells |
| Cell size | 1 byte |

There is no file header, footer, checksum, compression envelope, per-chunk header, or row padding. The 256-byte chunk is the only disk block unit described by this format. It is sector-sized, but the file carries no sector metadata. The file is a dense sequence of stored chunk blocks:

```text
stored_block_start = stored_block_index * 256
```

The stored block index is not the same as the logical chunk slot. The chunk-index table performs that translation.

## 3. Chunk Organization

The logical world is a 16-by-16 grid of chunks. Chunk slots are ordered west-to-east within a row, then north-to-south across rows:

```text
chunk_x = floor(x / 16)
chunk_y = floor(y / 16)
chunk_slot = chunk_y * 16 + chunk_x
```

Each stored chunk is a 16-by-16 row-major grid:

```text
local_x = x mod 16
local_y = y mod 16
offset_in_chunk = local_y * 16 + local_x
```

To read tile `(x, y)`:

1. Wrap `x` and `y` into the byte-coordinate range `0..255`.
2. Compute `chunk_slot`.
3. Look up `chunk_slot` in the Britannia chunk-index table.
4. If the table entry is decimal `255`, return the deep-water tile.
5. Otherwise, treat the table entry as a stored-block index and read:

```text
file_offset = table_entry * 256 + offset_in_chunk
```

The deep-water tile is tile index `1` in the tile catalogue. The all-water fill is a loader behavior, not bytes present in `BRIT.DAT`.

## 4. Coordinate Wrapping

Britannia coordinates are byte-sized world coordinates. Arithmetic that moves, scrolls, or samples the world wraps modulo 256 on both axes. Consequences for readers:

- `x = -1` is the same column as `x = 255`.
- `x = 256` is the same column as `x = 0`.
- The same rule applies to `y`.
- Chunk coordinates wrap modulo 16 after the world coordinate has wrapped.
- A viewport centered near any world edge can span chunks from both sides of the file's logical chunk grid.

This wrapping applies to terrain sampling and chunk loading. It does not mean that every movement mode allows every edge crossing; movement legality still depends on tile class, vehicle state, active objects, and scripted transitions.

## 5. Tile Encoding

Every cell byte is a tile index in the lower half of the shared tile space, `0..255`. These are the map-cell tiles: water, terrain, paths, walls, furniture, doors, decorations, and special static terrain. Sprite-only tiles such as NPCs, monsters, vehicles, items, effects, and the avatar are not stored in `BRIT.DAT`; they are overlaid through active-object state.

The file carries tile identity only. It does not encode:

- sprite pixels, which come from `TILES.16` or `TILES.4`;
- passability, sight blocking, or interaction flags, which come from tile attribute data;
- animation phase, which is applied to live buffers and rendered output;
- look text, which is supplied by the look-table data;
- location names or entrance identities, which come from resident location tables.

An implementation should preserve tile bytes exactly when decoding. Interpretation belongs to the tile catalogue and the consuming systems.

## 6. Relationship To Location Entry

Named locations on Britannia are not embedded as submaps inside `BRIT.DAT`. The surface map contains only the overworld terrain cell at each entrance coordinate. When the player uses the entry command or steps onto a transition handled by the overworld loop, the runtime compares the party's wrapped world coordinate against resident location-coordinate tables. A match selects a scene byte and loads the corresponding location file, such as `TOWNE.DAT`, `DWELLING.DAT`, `CASTLE.DAT`, or `KEEP.DAT`.

The location files use a different format: fixed 32-by-32 floor grids, grouped by location class. `BRIT.DAT` never stores those interior grids. It only provides the surface cell from which the transition is recognized.

Dungeon entrances, shrines, chasms, wells, and other static surface behavior follow the same split: the map supplies a terrain tile and coordinate; the runtime tables and system logic decide whether that cell triggers a mode change, prompt, teleport, or other effect.

Natural moongate frames are different. Current shipped-map scans find no static
moongate tile cells in `BRIT.DAT`, so the traced moongate presentation and
saved-slot live-terrain refresh are supplied by runtime state rather than by
source terrain cells. The live-terrain landing and entry hook is specified in
`systems/overworld.md`.

## 7. Relationship To Visibility And Rendering

Overworld rendering uses a live 2-by-2 chunk window, four chunks total, copied or synthesized from `BRIT.DAT` through the chunk-index table. The 11-by-11 viewport is centered on the party and samples from that live chunk window.

Visibility is not stored in `BRIT.DAT`. The visibility producer reads terrain tiles from the live chunk buffer, consults lighting and sight-blocking rules, and produces a separate viewport grid for the renderer. Active objects are composited over the terrain after visibility is evaluated.

The surface plane uses the overworld daylight model. Daylight, torch state, spells, moongates, and other light sources affect what can be seen, but they do not change the source terrain bytes in `BRIT.DAT`.

## 8. Relationship To Encounters

Random surface encounters use the tile under the party, party state, and other runtime conditions to decide whether to spawn a hostile active object. `BRIT.DAT` contributes the terrain tile; it does not contain encounter records or monster placement.

When combat starts from a surface active object, the tactical arena is loaded from the outdoor combat arena bank, not from the local 11-by-11 slice of `BRIT.DAT`. The surface map affects which encounter can arise and where active objects exist before combat, but it is not itself the combat map.

## 9. Persistence

`BRIT.DAT` is read-only static content during play. Saves persist the party's coordinates, current plane, vehicle state, active-object table, and other runtime state. The mutable surface-object layer is mirrored through the surface object data rather than by rewriting `BRIT.DAT`.

Runtime tile substitutions, animation-frame changes, moongate stamps, open-object overlays, and encounter spawns operate on live buffers or active-object records. They should not be written back into `BRIT.DAT`.

The chunk loader's fixed live-buffer substitution pass is part of that runtime
layer. After a stored or all-water chunk is copied into memory, tile ids
`0x16..0x18` cause the loader to write tile `0xDF` through the live world-tile
accessor, while tile id `0x19` writes tile `0x1A` only when the current chunk
descriptor passes the chunk high-byte classifier. These rewrites are not file
contents and do not change the sparse chunk-index mapping.

## 10. Validation

A format reader should enforce or check the following:

- The file length is exactly 52,480 bytes.
- The file length is an integer multiple of 256 bytes.
- The file contains exactly 205 stored chunk blocks.
- A complete Britannia decoder has a 256-entry chunk-index table.
- Each non-sentinel chunk-index entry is in `0..204`.
- All referenced stored blocks fit wholly inside the file.
- Sentinel entries synthesize tile index `1` for every cell in that logical chunk.
- Coordinate sampling wraps modulo 256 before chunk-slot selection.
- Local chunk offsets are row-major 16-by-16 offsets.

For an audit tool with access to the chunk-index table, stronger checks are useful:

- The number of non-sentinel entries should be 205.
- Each stored block should be referenced by at least one logical chunk slot.
- Duplicate stored-block references should be treated as suspicious unless independently explained by table analysis.
- A rendered world should not have seams at chunk boundaries except where the authored terrain changes.
- Viewports crossing world edges should wrap cleanly.

## 11. Implementation Notes

The simplest complete decoder materializes a 256-by-256 grid:

1. Allocate 65,536 output cells.
2. For each logical chunk slot `0..255`, read the chunk-index table.
3. If the entry is the all-water sentinel, fill the corresponding 16-by-16 output region with tile index `1`.
4. Otherwise, copy the addressed 256-byte chunk from `BRIT.DAT` into the corresponding output region row by row.
5. Render or analyze the output grid through the tile catalogue.

An engine does not need to materialize the whole grid. It can follow the original streaming model: keep a 2-by-2 chunk window around the player, update it when the scroll base crosses a chunk boundary, and synthesize all-water chunks on demand.

## 12. Format Boundary And Runtime Work

The sparse `BRIT.DAT` map-file contract is complete at byte-layout depth:
stored block count and size, chunk-index table use, all-water synthesis,
coordinate wrapping, tile-byte preservation, static terrain ownership, and the
chunk-loader live-buffer substitution boundary are fixed. Remaining items
belong to resident-data sourcing, runtime transitions, tile cataloguing,
encounter behavior, or mutation-audit work rather than the base file layout.

- The exact resident location of the Britannia chunk-index table is intentionally out of scope for this cleanroom format spec. A complete implementation still needs that table from the resident-data spec or an equivalent clean source.
- The full list of entrance, shrine, falls, scripted-transition coordinates, and saved Moonstone gate anchors belongs in system or gazetteer specs, not in this file-format spec.
- The precise tile-attribute tables for passability, sight blocking, special triggers, and animation are not fully enumerated in the tile specs yet.
- The semantic names for the chunk-loader substitution tile ids, and the
  classifier flags that gate the `0x19` case, remain tile-catalog and
  helper-level work.
- The random-encounter probability formula and terrain-to-monster mapping remain partially open in the encounter system spec.
- It is not yet fully audited whether any long-lived world mutation can patch the live terrain layer across saves. Current evidence points to static `BRIT.DAT` plus mutable active-object/object-layer state.

## 13. Sources

This spec is a cleanroom prose rewrite derived from the project notes and existing specs below. It intentionally omits decompiled code, assembly, raw private addresses, and copied byte dumps.

- `u5-decomp/formats/maps.md`
- `u5-spec/systems/overworld.md`
- `u5-spec/formats/location-dat.md`
- `u5-spec/systems/visibility.md`
- `u5-spec/systems/encounters.md`
- `u5-spec/formats/tiles.md`
- `u5-spec/catalogs/tile-catalog.md`
- `u5-decomp/functions/OUTSUBS_OVL/0x0098_outsubs_load_chunk.md`
- `u5-decomp/functions/OUTSUBS_OVL/0x004A_outsubs_chunk_classify.md`
