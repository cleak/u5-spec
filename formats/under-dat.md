# UNDER.DAT

Format specification for `UNDER.DAT`, the static Underworld map. Runtime movement, lighting, encounters, plane transitions, and rendering are covered by the overworld and related system specs; this document covers the file shape and the map-reader contract.

## 1. Overview

`UNDER.DAT` represents the Underworld, the dark lower plane beneath Britannia. It uses the same logical surface-map geometry as `BRIT.DAT`: a 256-by-256 grid of one-byte tile indices, divided into 256 chunks arranged as a 16-by-16 chunk grid. Each chunk is 16 cells wide by 16 cells tall, for 256 bytes per chunk.

Unlike `BRIT.DAT`, `UNDER.DAT` is dense. All 256 logical chunks are present in the file in logical order. A reader can reconstruct any tile by arithmetic alone; no sparse chunk-index table is needed for the on-disk layout, and none exists in resident data - the single resident chunk-index table accounts for the 205 stored `BRIT.DAT` chunks and nothing else. The runtime does route both surfaces through the same loader, and it tells them apart by the **first letter of the map filename** it is handed: the Britannia arm looks each chunk up in that table and synthesizes an all-deep-water chunk for a sentinel entry, while the underworld arm uses the caller's descriptor directly as a file offset. The file format itself is direct: logical chunk slot `n` is stored block `n`.

The file stores terrain only. It does not store active monsters, vehicles, dropped items, party position, visibility state, transition metadata, or encounter definitions.

## 2. File Shape

The file is exactly 65,536 bytes:

| Quantity | Value |
|----------|------:|
| Stored chunk count | 256 |
| Bytes per stored chunk | 256 |
| Total file size | 65,536 |
| Logical chunk count | 256 |
| Logical world size | 256 x 256 cells |
| Cell size | 1 byte |

There is no file header, footer, checksum, compression envelope, per-chunk header, or row padding. The 256-byte chunk is the only disk block unit described by this format. It is sector-sized, but the file carries no sector metadata. The file is a dense sequence of 256 chunk blocks:

```text
chunk_start = chunk_slot * 256
```

Because every logical chunk is stored, `chunk_slot` and stored-block index are the same value.

## 3. Chunk Organization

The logical world is a 16-by-16 grid of chunks. Chunk slots are ordered west-to-east within a row, then north-to-south across rows:

```text
chunk_x = floor(x / 16)
chunk_y = floor(y / 16)
chunk_slot = chunk_y * 16 + chunk_x
```

Each chunk is a 16-by-16 row-major grid:

```text
local_x = x mod 16
local_y = y mod 16
offset_in_chunk = local_y * 16 + local_x
file_offset = chunk_slot * 256 + offset_in_chunk
```

To read tile `(x, y)`, wrap both coordinates into `0..255`, compute the chunk slot and local offset, then read the byte at `file_offset`.

## 4. Coordinate Wrapping

Underworld coordinates are byte-sized world coordinates and wrap modulo 256 on both axes. Terrain sampling, viewport construction, and chunk-window loading should use wrapped coordinates:

- `x = -1` samples column `255`.
- `x = 256` samples column `0`.
- The same rule applies to `y`.
- Chunk coordinates wrap modulo 16 after world coordinates wrap.
- A viewport centered near a world edge can draw from chunks on both sides of the logical grid.

Movement legality remains separate from coordinate sampling. Tile class, vehicle state, active objects, chasms, dungeon entrances, and scripted handlers decide whether the party can move or transition after a wrapped coordinate has been resolved.

## 5. Tile Encoding

Every cell byte is a tile index in the lower half of the shared tile space, `0..255`. These are map-cell tiles: terrain, walls, paths, special static features, and other world tiles. The upper half of the tile space is reserved for sprites and active objects and is not stored directly in the map file.

The file stores tile identity only. It does not encode:

- graphics pixels, which come from `TILES.16` or `TILES.4`;
- passability or sight-blocking attributes;
- light level or visited state;
- random-encounter probabilities;
- active monsters, vehicles, objects, or the party;
- plane-transition or scripted transition targets.

Preserve unknown or uninterpreted tile values as raw tile indices. Gameplay semantics belong to the tile catalogue and consuming systems.

## 6. Surface Differences

`UNDER.DAT` and `BRIT.DAT` share the same logical dimensions, chunk size, coordinate wrapping, tile-byte encoding, viewport model, and overworld-mode loop. The important format and runtime differences are:

| Aspect | Britannia (`BRIT.DAT`) | Underworld (`UNDER.DAT`) |
|--------|------------------------|--------------------------|
| On-disk chunks | Sparse, water-only chunks omitted | Dense, all chunks stored |
| File size | 52,480 bytes | 65,536 bytes |
| Chunk lookup | Requires chunk-index table | Direct logical chunk order |
| Default omitted terrain | Deep water synthesized by loader | No omitted terrain |
| Ambient light | Day-night surface model | Forced dark underworld model |
| Fixed features | Towns, keeps, castles, shrines, moongates, dungeon entrances, falls | Cavern terrain, dungeon entrances, the single underworld-only keep (Ararat), and underworld-specific transitions - but no ascent terrain |
| Object seed | Surface object layer | Underworld object layer |

The differences after loading are mostly system behavior, not file structure. The same renderer and visibility producer can consume both planes once the proper chunks are in the live buffer.

## 7. Relationship To Location Entry And Plane Transitions

The party's current plane selects whether the overworld loader samples `BRIT.DAT` or `UNDER.DAT`. Britannia uses the surface plane value; the Underworld uses the underworld plane value. The set of plane transitions is closed and is published in `systems/overworld.md` Section 2 and `catalogs/gazetteer.md` Section 8.3: the surface falls path, the whirlpool forced-underworld path, town-family interior exits, dungeon exits, and the saved Moonstone-slot warp shared by natural moongates and Gate Travel. Each of them writes the plane state, and arriving on the overworld of the destination plane reseeds the chunk window and the active-object layer for that plane. A save-state restore also sets the plane, but it replays a previously recorded position rather than performing a transition. What remains owned by `systems/overworld.md` is the moongate *placement* state - which gates are currently live and where a buried moonstone has moved one - not the destination handler, which simply copies the recorded plane and coordinates of the selected Moonstone slot.

`UNDER.DAT` itself does not name transition coordinates, destination points, or scene identities. It stores only the terrain bytes at those cells. The overworld system and resident coordinate tables decide which underworld cells lead to dungeon or special scenes and how the active-object table is reseeded. No underworld cell returns the party to the surface by itself: the plane-writer census is closed and contains no outdoor ascent, so a decoder must not reserve an "ascent cell" meaning for any underworld terrain byte.

The Underworld dispatches into the location files far more sparsely than the surface does, but it is not excluded from them: one keep, Ararat, stands on the underworld map and enters its interior from the keep class file like any surface keep, and its exit returns the party underground. Apart from that single settlement, leaving the 256-by-256 map means a plane transition, a dungeon-mode scene, combat, or a scripted scene rather than an interior chosen from a named surface settlement. `catalogs/gazetteer.md` Section 8.3 carries the full destination inventory.

## 8. Relationship To Visibility And Rendering

The Underworld uses the same 2-by-2 live chunk window and 11-by-11 viewport model as Britannia. The renderer receives tile indices from the live chunk buffer, not directly from disk on every frame.

Visibility is not stored in `UNDER.DAT`. The visibility producer reads terrain tiles from the chunk buffer, applies the centre-out visibility carve, light-radius rules, and local-light mask state, and writes a separate viewport grid for the renderer. The Underworld differs from Britannia because its ambient light is forced to the dark model. Torches, spells, and special light sources can affect the visible region, but the map bytes remain unchanged.

Active objects are composited after terrain visibility. Monsters, vehicles, items, effects, and the party do not live in `UNDER.DAT`.

## 9. Relationship To Encounters

The Underworld participates in the overworld random-encounter system. The encounter probe uses the tile under the party and runtime state to decide whether to spawn a hostile active object. `UNDER.DAT` supplies terrain classification but no encounter records.

When combat begins, the tactical terrain is loaded from the combat arena data, not from the local Underworld map slice. The encounter and combat systems may treat the Underworld plane as a variant for placement, lighting, or monster selection, but the `UNDER.DAT` file itself remains a static terrain source.

## 10. Persistence

`UNDER.DAT` is read-only static content during play. Saves persist runtime state such as the party's coordinates, current plane, vehicle state, active objects, and object-layer state. The Underworld's mutable active-object layer is handled outside the map file.

Runtime changes should be modeled as overlays or live-buffer mutations:

- active monsters and objects live in active-object state;
- opened or temporary effects belong to live runtime buffers;
- visibility and light are recalculated each frame or turn;
- combat setup uses separate arena files.

No save/load path should rewrite `UNDER.DAT`.

The shared overworld chunk loader applies its substitution pass to Underworld
chunks on exactly the same terms as surface chunks. **Both substitutions are
conditional on save-backed quest state; neither is unconditional.** A cell
holding a dungeon-entrance tile (`0x16`, `0x17`, `0x18`) is rewritten to the
collapsed-entrance tile `0xDF` only while the Word of Power owning that chunk
is still unspoken, and a cell holding the shrine tile `0x19` is rewritten to
the ruined-shrine tile `0x1A` only while that chunk's shrine is marked ruined.
The full rule, including the two opposite defaults for chunks that own neither,
is specified once in `formats/brit-dat.md` Section 9.1; `systems/commands.md`
Sections 11.1 and 11.2 own the command-side contract. An engine that applies
either rewrite unconditionally leaves every dungeon entrance permanently
sealed.

This matters more on the Underworld than on the surface, because the
Underworld grid carries **eight** dungeon-entrance cells, not seven: the same
seven coordinates as the surface plane, plus Doom's entrance at the centre of
the plane. The per-word flag is shared between the two planes, so speaking a
word unseals that dungeon's cell on both. The Underworld grid carries no shrine
cells and, like the surface grid, no `0xDF` or `0x1A` cell of its own.

The file remains a dense, direct map source; these substitutions belong to the
runtime window and are never written back.

## 11. Validation

A reader should enforce or check the following:

- The file length is exactly 65,536 bytes.
- The file contains exactly 256 chunks.
- Each chunk is exactly 256 bytes.
- Chunk slots are dense and logical-order: `chunk_slot == stored_block_index`.
- Local chunk offsets are row-major 16-by-16 offsets.
- Coordinate sampling wraps modulo 256 before chunk-slot selection.
- Every byte is a map-cell tile index in `0..255`.

For visual or gameplay audits:

- Rendering the materialized 256-by-256 grid through the tile catalogue should produce a continuous underworld map with no chunk-boundary decoding seams.
- Viewports crossing world edges should wrap cleanly.
- Tiles that appear impassable, opaque, damaging, or transitional should be verified through tile attributes and system specs rather than inferred from file position.

## 12. Implementation Notes

A complete materializing decoder is straightforward:

1. Verify the file is 65,536 bytes.
2. Split it into 256 consecutive 256-byte chunks.
3. For each chunk slot, map it to `(chunk_x, chunk_y)` with `chunk_x = slot mod 16` and `chunk_y = floor(slot / 16)`.
4. Copy the chunk's 16 row-major rows into the corresponding region of a 256-by-256 output grid.
5. Render or analyze the output grid through the shared tile catalogue.

An engine can instead stream four chunks at a time, exactly as for Britannia, with the simplification that every requested chunk maps directly to a stored file block.

## 13. Format Boundary And Runtime Work

The dense `UNDER.DAT` map-file contract is complete at byte-layout depth:
direct 256-chunk ordering, fixed file size, coordinate wrapping, tile-byte
preservation, static terrain ownership, and the shared chunk-loader
live-buffer substitution boundary are fixed. Remaining items belong to runtime
transitions, tile cataloguing, encounter behavior, or mutation-audit work rather
than the base file layout.

- The Underworld's transition coordinates are published in
  `catalogs/gazetteer.md` rather than here. Note in particular that there is no
  outdoor ascent: no underworld terrain feature lifts the party to the surface,
  and the routes up are a dungeon's top exit, a moongate or Gate Travel to a
  surface Moonstone slot, and a saved-position reload.
- The full tile-attribute tables for underworld passability, sight blocking, damage, and special triggers are not fully enumerated in the tile specs yet.
- The semantic names for the chunk-loader substitution tile ids, and the
  classifier flags that gate the `0x19` case, remain tile-catalog and
  helper-level work.
- Underworld-specific encounter probabilities, monster selection, and arena variant behavior remain partially open in the encounter system spec.
- It is not yet fully audited whether any long-lived world mutation can patch the live terrain layer across saves. Current evidence points to static `UNDER.DAT` plus mutable active-object/object-layer state.
- The exact relationship between every underworld special tile and first-person dungeon entry remains to be tied to the dungeon-mode and gazetteer specs.

## 14. Sources

This spec is a cleanroom prose rewrite derived from the project notes and existing specs below. It intentionally omits decompiled code, assembly, raw private addresses, and copied byte dumps.

- `u5-decomp/formats/maps.md`
- `u5-spec/systems/overworld.md`
- `u5-spec/formats/location-dat.md`
- `u5-spec/systems/visibility.md`
- `u5-spec/systems/encounters.md`
- `u5-spec/formats/tiles.md`
- `u5-spec/catalogs/tile-catalog.md`
- `u5-decomp/functions/OUTSUBS_OVL/0x0098_outsubs_load_chunk.md`
- `u5-decomp/functions/OUTSUBS_OVL/0x004A_outsubs_chunk_classify.md` (retargeted as the shrine-ruin gate)
- `u5-decomp/functions/OUTSUBS_OVL/0x0000_outsubs_water_check.md` (retargeted as the Word-of-Power seal gate)
- `u5-decomp/notes/2026-08-22_quest-world-retrace.md`
- Source provenance: the dense-layout confirmation, the filename-letter loader
  discriminator, and the closed no-outdoor-ascent result are derived from
  private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
