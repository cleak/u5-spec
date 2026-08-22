# OOL Object Tables

Format specification for the `.OOL` object-table files: `SAVED.OOL`, `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL`. These files store the movable-object tables for Britannia and the Underworld: skiffs, ships, horses, carpets, dropped objects, and other dynamic map entities. The save/load lifecycle is described in `systems/save-load.md`; the active-object runtime model is described in `systems/active-objects.md`.

## 1. Overview

An `.OOL` file is a flat array of active-object records. Each record is eight bytes. Each plane table is thirty-two records, for two hundred fifty-six bytes total. `SAVED.OOL` concatenates two plane tables: surface first, underworld second. `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL` each contain one plane table.

There is no header, magic number, version word, checksum, compression, or footer. Empty records are all zero by convention. Non-empty records have a non-zero type byte in the first position.

The file extension's expansion is not attested. "Object Overlay Layer" is a useful mnemonic, but the extension should be treated as opaque.

| File | Expected size | Plane tables | Role |
|------|--------------:|-------------:|------|
| `SAVED.OOL` | 512 bytes | 2 | Canonical saved surface and underworld object-overlay state. |
| `BRIT.OOL` | 256 bytes | 1 | Surface plane mirror and seed. |
| `UNDER.OOL` | 256 bytes | 1 | Underworld plane mirror and seed. |
| `INIT.OOL` | 256 bytes | 1 | Factory surface seed paired with `INIT.GAM`. |

## 2. File Roles

### `SAVED.OOL`

`SAVED.OOL` is the canonical saved object-overlay companion to `SAVED.GAM`. It stores both world-plane object tables:

- First plane table: Britannia surface.
- Second plane table: Underworld.

On load, both halves are read into memory. On save, both halves are written back out.

### `BRIT.OOL`

`BRIT.OOL` is the per-plane surface file. It ships as the surface seed object table. The confirmed load flow rewrites it so it mirrors the surface half of `SAVED.OOL`. The traced save flow reads it into the surface staging buffer and writes that staging half back as the surface save-time mirror on every confirmed save.

### `UNDER.OOL`

`UNDER.OOL` is the per-plane underworld file. It ships as the underworld seed object table. In a clean install, the seed table is empty. The confirmed load flow rewrites it so it mirrors the underworld half of `SAVED.OOL`. The traced save flow reads it into the underworld staging buffer, writes it back as the underworld save-time mirror, and may write that same underworld half a second time on a defensive disk-prompt-mode branch.

### `INIT.OOL`

`INIT.OOL` is the factory seed paired with `INIT.GAM`. It contains one plane table and matches the clean surface seed. The runtime treats it as read-only; it is used when creating the first playable save state.

## 3. Plane Table Shape

A plane table is a fixed thirty-two-slot array. Each slot is one active-object record. Slot order is stable: the engine does not compact the table on disk, and a record's slot index is meaningful to systems that restore or compare object state.

An empty slot has a zero type byte. The remaining bytes of an empty slot are normally zero. A non-empty slot is interpreted using the active-object record layout below.

There is no count field. Readers must scan all thirty-two records.

## 4. Record Layout

Each record has eight bytes:

1. **Type.** Object type or tile-class byte. Zero means the slot is empty.
2. **Frame tile.** Usually initialised to the same value as the type byte, then changed by animation or rendering code.
3. **X coordinate.** Cell column on the relevant world plane.
4. **Y coordinate.** Cell row on the relevant world plane.
5. **Z or plane marker.** For surface and underworld world objects, the common sentinel means "no local building floor"; other values are used by modes that carry vertical state.
6. **Auxiliary byte one.** Class-specific state. For ship/frigate objects this is hull condition; the F-Fire broadside path also treats it as a generic depletion counter for any struck active object.
7. **Auxiliary byte two.** Packed animation state: the low nibble is the per-slot animation phase and the high nibble is a direction or step counter for animator-owned movement.
8. **Auxiliary byte three.** Class-specific state. For ship/frigate objects this is the count of skiffs aboard; other families may use it for their own durable or transient state.

The first two bytes are often equal in seed files because objects begin on their base animation frame. They should not be assumed to stay equal after play begins.

Coordinates are byte-sized world coordinates. For `BRIT.OOL` and the first half of `SAVED.OOL`, they refer to the Britannia surface. For `UNDER.OOL` and the second half of `SAVED.OOL`, they refer to the Underworld.

## 5. Relationship To `SAVED.GAM`

`SAVED.GAM` also contains a thirty-two-record active-object table. That table is the live cast for the player's current map at the instant of save. The `.OOL` files hold the persistent per-plane overworld object tables outside the main save image.

The distinction matters:

- The main save image stores current scene state, party state, inventory, and the current active-object table.
- `SAVED.OOL` stores the two overworld-plane object tables that need to survive map transitions.
- `BRIT.OOL` and `UNDER.OOL` are per-plane mirrors of the two halves of `SAVED.OOL`, with mirror refresh confirmed during both load and save. The save handler also uses them as staging sources and writes `UNDER.OOL` a second time unless the save handler entered with disk-prompt mode already set to mode 1. Traced overworld helper paths select one of these filenames from the current world-plane byte, then pass that filename into resident object-table refresh/setup calls when entering a town-family scene or changing world plane.

A modern implementation can keep a single in-memory object-overlay cache, but a byte-compatible implementation must preserve the file split and the confirmed load-time and save-time mirror-write behaviour.

## 6. Load And Save Semantics

On load, the engine unconditionally refreshes the per-plane mirrors:

1. Reads `SAVED.GAM` into the save-image region.
2. Reads all of `SAVED.OOL` into the two in-memory plane tables.
3. Writes the surface half back out to `BRIT.OOL`.
4. Writes the underworld half back out to `UNDER.OOL`.
5. If the loaded save resumes on the underworld surface, runs an underworld disk-swap probe and rewrites the underworld mirror once the data disk is present.

On save, the engine reads `UNDER.OOL` and `BRIT.OOL` into the two staging halves, writes the underworld staging half to `UNDER.OOL`, writes the surface staging half to `BRIT.OOL`, checks the disk-prompt mode captured on entry, then writes the underworld half to `UNDER.OOL` a second time unless that entry mode was already mode 1. It then writes `SAVED.GAM` and the concatenated `SAVED.OOL`. Byte-compatible implementations should preserve this file set and write order at semantic depth; modern safe-save wrappers may add their own crash-safety outside the original contract.

## 7. Seed-State Observations

The clean surface seed contains a small set of non-empty object records and otherwise zero slots. These records correspond to pre-placed world objects such as ferry-skiffs and clustered static objects on Britannia. The underworld seed is empty in a clean install.

`SAVED.OOL` in a clean install begins as the surface seed followed by an empty underworld table. `INIT.OOL` matches the surface seed. As the player moves vehicles, drops or removes objects, or otherwise changes overworld object state, the object-overlay tables become the durable record of those changes.

The questionnaire and Ultima IV transfer writers have a traced fresh-game
exception: they emit a blank 256-byte half followed by the surface seed, and
**both** of them read that seed from `INIT.OOL`. (An earlier revision of this
paragraph named `BRIT.OOL` as the transfer path's seed; that is withdrawn — the
transfer reads the same `INIT.GAM` / `INIT.OOL` pair the questionnaire uses, and
no `BRIT.GAM` exists in the shipped data at all.) That emitted
order is documented with the writer flows in `systems/chargen.md` and
`systems/u4-transfer.md`. The canonical load/save interpretation in this
format remains surface first, underworld second.

There is no special first-load repair for that fresh-game exception. When the
player later chooses Journey Onward, the load path reads the first half of
`SAVED.OOL` as the surface table and the second half as the underworld table,
then mirrors those two halves to `BRIT.OOL` and `UNDER.OOL` exactly as read.
Byte-compatible implementations should preserve this sequence rather than
trying to detect or rotate the fresh-game writer's half order.

## 8. Validation And Invariants

A byte-compatible reader should enforce these invariants:

- `SAVED.OOL` is exactly 512 bytes: one surface plane table followed by one underworld plane table.
- `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL` are exactly 256 bytes each.
- Each plane table contains exactly thirty-two records.
- Each record is exactly eight bytes.
- A zero type byte means the slot is empty. The remaining bytes of an empty slot should normally be zero, but a conservative reader should preserve them if they are not.
- Slot order is stable and must not be compacted on write.
- Coordinates are byte-sized. Map-level validity depends on the owning plane and should be checked by the map system, not by the `.OOL` decoder alone.
- The common surface-object Z sentinel should be preserved as a byte value, not converted to a nullable field unless the original byte can be reconstructed.
- After the confirmed load sequence, the surface half of `SAVED.OOL` should match `BRIT.OOL`, and the underworld half should match `UNDER.OOL`. This applies even to fresh saves whose writer emitted a blank first half followed by a surface seed; load does not reinterpret that exception.
- After save, `SAVED.OOL` is the canonical object-overlay file, and both per-plane mirrors are refreshed from the same staging halves. `UNDER.OOL` receives a second identical defensive flush unless the entry disk-prompt mode was already mode 1.

## 9. Implementation Notes

A decoder should:

1. Verify file size by role: one plane table for `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL`; two concatenated plane tables for `SAVED.OOL`.
2. Split each plane table into thirty-two eight-byte records.
3. Treat a zero type byte as empty.
4. Preserve every byte of every record, including unknown auxiliary bytes. For
   ship/frigate records, preserve zero-based byte `+5` as hull condition and
   byte `+7` as skiffs aboard. Preserve zero-based byte `+6` exactly as the
   animator-owned packed phase/direction byte; do not recompute it while
   merely decoding or rewriting an `.OOL` file.
5. Keep slot index stable across read and write.

F-Fire broadsides can mutate zero-based byte `+5` before the table is written
back. A ship/frigate target loses hull condition. Other target families still
preserve their own byte meaning outside F-Fire, but the broadside command
treats the byte as a depletion counter and clears the slot if the subtraction
wraps into the high-bit range.

For a high-level engine, the record can be mapped to an object record or entity component. For byte compatibility, write the exact eight bytes back in the same slot order.

## 10. Cross-References

- Save/load system lifecycle, mirror writes, empty-save guard, and disk-swap behaviour: `systems/save-load.md`.
- Active-object table runtime semantics and record interpretation: `systems/active-objects.md`.
- Vehicle boarding/exiting and parked-vehicle persistence: `systems/vehicles.md`.
- Main save-image layout and its embedded active-object table: `formats/saved-gam.md`.
- Outdoor mode and world-plane transitions that consume the object overlays: `systems/overworld.md`.
- Combat's temporary backup and restore of the active-object table: `systems/combat.md`.

## 11. Format Boundary And Runtime Work

The `.OOL` file-format contract is complete at table-layout and lifecycle
depth: file roles, table sizes, record size, surface/underworld split, seed
roles, mirror writes, and known active-object auxiliary bytes are fixed.
The first-load behavior for fresh-save writer exceptions is also fixed: no
normalization pass rotates the two halves. Remaining items are naming, uncommon
family-specific runtime meanings, reader census, and gameplay population
sources.

- **Name expansion.** The meaning of "OOL" is unattested. Treat it as an opaque
  extension, not as a field or runtime semantic.
- **Auxiliary byte enumeration.** Ship/frigate zero-based byte `+5` hull
  condition, byte `+7` skiff count, broadside hit resolution for byte `+5`,
  and byte `+6` packed animation phase/direction semantics are public. The
  remaining gap is narrower: uncommon family-specific meanings for bytes `+5`
  and `+7` outside those roles are not fully enumerated.
- **Runtime readers of mirror files.** OUTSUBS owns a traced world-plane
  filename helper that chooses `BRIT.OOL` for the surface and `UNDER.OOL` for
  the underworld. The town-entry path passes that selected filename to the
  resident object-table refresh/setup helper before handing off to town mode;
  the confirmed falls transition names both per-plane files while changing the
  party to the underworld plane. The remaining census is only for additional
  mirror-file callers outside these traced overworld transition paths.
- **Underworld population.** The clean underworld seed is empty. Later gameplay
  may populate it; confirming every underworld object source requires played
  saves or targeted runtime probes.

## 12. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It intentionally omits decompiled code, assembly, implementation addresses, and raw private offset tables.

- First-pass save and `.OOL` survey, including file roles, sizes, record shape, seed observations, and the surface/underworld split: `u5-decomp/formats/saves.md`.
- Save-handler analysis, including per-plane `.OOL` staging reads, unconditional mirror writes, the entry-mode-gated second `UNDER.OOL` flush, and canonical `SAVED.OOL` write: `u5-decomp/functions/CAST2_OVL/0x10FE_save_game.md` and `u5-decomp/notes/dosbox_probes_2026-05-07.md`.
- Fresh-game `SAVED.OOL` writer exceptions: `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` and `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.
- Internal load-flow analysis, including `SAVED.OOL` read, unconditional mirror writes to `BRIT.OOL` and `UNDER.OOL`, and underworld disk-swap path.
- OUTSUBS runtime mirror-file selection and transition consumers:
  `u5-decomp/functions/OUTSUBS_OVL/0x0368_outsubs_world_filename.md`,
  `u5-decomp/functions/OUTSUBS_OVL/0x0388_outsubs_check_town_entry.md`, and
  `u5-decomp/functions/OUTSUBS_OVL/0x0458_outsubs_falls_handler.md`.
- Active-object runtime model used to interpret each eight-byte record: `u5-spec/systems/active-objects.md`.
- Save/load system prose used for cross-checking lifecycle semantics: `u5-spec/systems/save-load.md`.
- Vehicle byte interpretation for ship boarding, X-it parking, and broadside
  damage: `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md`,
  `u5-decomp/functions/CMDS_OVL/0x0EB4_cmds_xit_vehicle.md`, and
  `u5-decomp/functions/CMDS_OVL/0x0962_cmds_fire_broadsides.md`.
- Animator byte interpretation for the packed phase/direction field:
  `u5-decomp/functions/ULTIMA_EXE/0x4552_active_object_tick.md`.
