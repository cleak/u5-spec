# OOL Object Tables

Format specification for the `.OOL` object-table files: `SAVED.OOL`, `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL`. These files store the movable-object tables for Britannia and the Underworld: skiffs, ships, horses, carpets, dropped objects, and other dynamic map entities. The save/load lifecycle is described in `systems/save-load.md`; the active-object runtime model is described in `systems/active-objects.md`.

## 1. Overview

An `.OOL` file is a flat array of active-object records. Each record is eight bytes. Each plane table is thirty-two records, for two hundred fifty-six bytes total. `SAVED.OOL` concatenates two plane tables: surface first, underworld second. `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL` each contain one plane table.

There is no header, magic number, version word, checksum, compression, or footer. Empty records are all zero by convention. Non-empty records have a non-zero type byte in the first position.

The file extension's expansion is not attested. "Object Overlay Layer" is a useful mnemonic, but the extension should be treated as opaque.

| File | Expected size | Plane tables | Role |
|------|--------------:|-------------:|------|
| `SAVED.OOL` | 512 bytes | 2 | Canonical saved surface and underworld object-overlay state. |
| `BRIT.OOL` | 256 bytes | 1 | Surface plane mirror and seed. Ships empty. |
| `UNDER.OOL` | 256 bytes | 1 | Underworld plane mirror and seed. Ships populated. |
| `INIT.OOL` | 256 bytes | 1 | Factory underworld seed paired with `INIT.GAM`. Byte-identical to the shipped `UNDER.OOL`. |

## 2. File Roles

### `SAVED.OOL`

`SAVED.OOL` is the canonical saved object-overlay companion to `SAVED.GAM`. It stores both world-plane object tables:

- First plane table: Britannia surface.
- Second plane table: Underworld.

On load, both halves are read into memory. On save, both halves are written back out.

### `BRIT.OOL`

`BRIT.OOL` is the per-plane surface file. It ships as the surface seed object table, and in a clean install that seed is empty: all two hundred fifty-six bytes are zero, so every one of its thirty-two slots is free. The confirmed load flow rewrites it so it mirrors the surface half of `SAVED.OOL`. The save flow runs the other way: it **reads** this file into the surface staging half and never writes it. A confirmed save therefore leaves `BRIT.OOL` byte-unchanged.

### `UNDER.OOL`

`UNDER.OOL` is the per-plane underworld file. It ships as the underworld seed object table, and in a clean install that seed is populated: five non-empty records occupy slots 23 through 27 and the remaining twenty-seven slots are zero. The confirmed load flow rewrites it so it mirrors the underworld half of `SAVED.OOL`. The save flow **reads** this file into the underworld staging half, and then writes that same half straight back out again on a disk-prompt-mode branch — the one and only per-plane write on the save path, and one that reproduces the bytes it just read. If the save handler entered with disk-prompt mode already set to mode 1, even that write is skipped and a confirmed save leaves `UNDER.OOL` untouched as well.

### `INIT.OOL`

`INIT.OOL` is the factory seed paired with `INIT.GAM`. It contains one plane table and is byte-identical to the shipped `UNDER.OOL`, so it is the **underworld** seed, not a surface seed. The runtime treats it as read-only; it is used when creating the first playable save state, where it supplies the underworld half of the new `SAVED.OOL`.

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
7. **Auxiliary byte two.** Packed animation state: the low nibble is a
   frame-delay countdown, whose all-ones value is the animator's "do not
   animate this slot" sentinel, and the high nibble is the slot's step within
   its animation script. **It carries no facing.** *Corrected (issue #184): an
   earlier revision called the high nibble "a direction or step counter for
   animator-owned movement"; the direction reading is withdrawn, see*
   `RETRACTIONS.md` *row R340 and* `systems/active-objects.md` *Section 3.*
8. **Auxiliary byte three.** Class-specific state. For ship/frigate objects this is the count of skiffs aboard; other families may use it for their own durable or transient state.

The first two bytes are often equal in seed files because objects begin on their base animation frame. They should not be assumed to stay equal after play begins.

Coordinates are byte-sized world coordinates. For `BRIT.OOL` and the first half of `SAVED.OOL`, they refer to the Britannia surface. For `UNDER.OOL` and the second half of `SAVED.OOL`, they refer to the Underworld.

## 5. Relationship To `SAVED.GAM`

`SAVED.GAM` also contains a thirty-two-record active-object table. That table is the live cast for the player's current map at the instant of save. The `.OOL` files hold the persistent per-plane overworld object tables outside the main save image.

The distinction matters:

- The main save image stores current scene state, party state, inventory, and the current active-object table.
- `SAVED.OOL` stores the two overworld-plane object tables that need to survive map transitions.
- `BRIT.OOL` and `UNDER.OOL` are per-plane mirrors of the two halves of `SAVED.OOL`. The mirror refresh runs **on load only**: load writes both files from the halves it just read out of `SAVED.OOL`. Save runs in the opposite direction — it reads both files into the two staging halves and composes `SAVED.OOL` from them, writing back only `UNDER.OOL`, and only when the save handler entered with disk-prompt mode other than mode 1. Traced overworld helper paths select one of these filenames from the current world-plane byte, then pass that filename into resident object-table refresh/setup calls when entering a town-family scene or changing world plane.

A modern implementation can keep a single in-memory object-overlay cache, but a byte-compatible implementation must preserve the file split, the load path's two mirror writes, and the save path's opposite direction: two per-plane reads and at most the one gated underworld write-back.

## 6. Load And Save Semantics

On load, the engine unconditionally refreshes the per-plane mirrors:

1. Reads `SAVED.GAM` into the save-image region.
2. Reads all of `SAVED.OOL` into the two in-memory plane tables.
3. Writes the surface half back out to `BRIT.OOL`.
4. Writes the underworld half back out to `UNDER.OOL`.
5. If the loaded save resumes on the underworld surface, runs an underworld disk-swap probe and rewrites the underworld mirror once the data disk is present.

On save, the handler **fills the two staging halves from the per-plane files
before composing the canonical pair**, in this order:

1. Reads all of `UNDER.OOL` into the underworld staging half.
2. Reads all of `BRIT.OOL` into the surface staging half.
3. Checks the disk-prompt mode captured on entry; unless that entry mode was
   already mode 1, writes the underworld staging half back out to `UNDER.OOL`.
   This is the only per-plane mirror write on the save path, and it reproduces
   the bytes read in step 1.
4. Writes `SAVED.GAM`.
5. Writes the concatenated 512-byte `SAVED.OOL` from the two staging halves,
   surface first.

Two consequences are part of the contract. `BRIT.OOL` is never written by a
save. And the saved object-overlay state is whatever the two per-plane files
held on disk at the moment of the save, not a snapshot taken from live gameplay
memory — the live overworld cast for the current map travels in the main save
image instead, and the per-plane files are kept current by the transition paths
of section 11. An earlier revision of this section described the save path as
two unconditional mirror writes with no read, and explicitly withdrew the read;
that revision had the direction of both per-plane transfers backwards and is
itself withdrawn. Byte-compatible implementations should preserve this file set
and operation order at semantic depth; modern safe-save wrappers may add their
own crash-safety outside the original contract.

## 7. Seed-State Observations

The clean **surface** seed is empty. Shipped `BRIT.OOL` is two hundred fifty-six
zero bytes, so a fresh Britannia has no pre-placed movable objects at all: every
skiff, ship, horse and carpet the player meets on the surface is placed by
gameplay, by a map's own static tile data, or by a scene-entry path, not by the
surface object overlay. (An earlier revision of this section described the
surface seed as holding "ferry-skiffs and clustered static objects on
Britannia"; that is withdrawn. Those records are in the underworld seed.)

The clean **underworld** seed is populated. Shipped `UNDER.OOL` carries five
non-empty records in slots 23 through 27, with all other slots zero:

| Slot | Type | Frame | X | Y | Z | Description |
|-----:|-----:|------:|--:|--:|--:|---|
| 23 | 0x29 | 0x29 | 14 | 242 | 0xFF | A skiff, on a shoals cell. |
| 24 | 0x1E | 0x1E | 103 | 226 | 0xFF | A corpse. |
| 25 | 0x1E | 0x1E | 105 | 227 | 0xFF | A corpse. |
| 26 | 0x1E | 0x1E | 107 | 227 | 0xFF | A corpse. |
| 27 | 0x1E | 0x1E | 108 | 225 | 0xFF | A corpse. |

All five have zero auxiliary bytes and the common above-ground Z sentinel. The
four corpses are a deliberate cluster: on the underworld map they stand on a
uniform grass clearing walled off inside a mountain field, and the skiff sits on
water. Read against the Britannia surface map instead, the same coordinates are
incoherent: the skiff cell falls inside an all-water region, and the four corpse
cells scatter across a mismatched run of water and shoreline tiles with no
enclosure and no shared terrain. The placements are meaningful on exactly one
plane, which independently confirms that these records belong to the underworld.

`SAVED.OOL` in a clean install therefore begins as an empty surface table
followed by the populated underworld seed. `INIT.OOL` is byte-identical to
`UNDER.OOL`, not to `BRIT.OOL`. As the player moves vehicles, drops or removes
objects, or otherwise changes overworld object state, the object-overlay tables
become the durable record of those changes.

The questionnaire and Ultima IV transfer writers follow that same canonical
order. Each emits a blank 256-byte first half followed by the 256 bytes of
`INIT.OOL`, which is exactly [empty surface table][underworld seed]. (An earlier
revision of this section called that a "fresh-game exception" whose half order
was the opposite of the canonical interpretation; that is withdrawn. The
mislabelling came from treating `INIT.OOL` as a surface seed. Once `INIT.OOL` is
correctly identified as the underworld seed, the writers are simply producing
surface-first, underworld-second like everything else, and there is no exception
to reconcile. A separate earlier claim, that the transfer path seeded from
`BRIT.OOL`, is also withdrawn: both writers read the same `INIT.GAM` /
`INIT.OOL` pair, and no `BRIT.GAM` exists in the shipped data at all.) Those
writer flows are documented in `systems/chargen.md` and
`systems/u4-transfer.md`.

No first-load repair or normalization is needed, and none exists. When the
player chooses Journey Onward, the load path reads the first half of `SAVED.OOL`
as the surface table and the second half as the underworld table, then mirrors
those two halves to `BRIT.OOL` and `UNDER.OOL` exactly as read. For a
fresh-game `SAVED.OOL` this restores precisely the shipped state: an empty
`BRIT.OOL` and an `UNDER.OOL` holding the five seed records. Byte-compatible
implementations should read and write the halves in this fixed order and must
never rotate or swap them.

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
- After the confirmed load sequence, the surface half of `SAVED.OOL` should match `BRIT.OOL`, and the underworld half should match `UNDER.OOL`. This holds for fresh saves too: the chargen and transfer writers emit a blank first half followed by the `INIT.OOL` underworld seed, which is already the canonical order, so load reproduces the shipped mirrors without reinterpreting anything.
- After save, `SAVED.OOL` is the canonical object-overlay file and equals the concatenation of the `BRIT.OOL` and `UNDER.OOL` contents as they stood when the save began. Save does not refresh the per-plane mirrors: `BRIT.OOL` is never written, and `UNDER.OOL` is rewritten with its own contents only when the entry disk-prompt mode was not mode 1.

## 9. Implementation Notes

A decoder should:

1. Verify file size by role: one plane table for `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL`; two concatenated plane tables for `SAVED.OOL`.
2. Split each plane table into thirty-two eight-byte records.
3. Treat a zero type byte as empty.
4. Preserve every byte of every record, including unknown auxiliary bytes. For
   ship/frigate records, preserve zero-based byte `+5` as hull condition and
   byte `+7` as skiffs aboard. Preserve zero-based byte `+6` exactly as the
   animator-owned packed frame-delay / script-step byte; do not recompute it while
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
The half order is also fixed in both directions: every writer, including the
fresh-game writers, emits surface first and underworld second, and no
normalization pass rotates the two halves on load. Remaining items are naming,
uncommon family-specific runtime meanings, reader census, and gameplay
population sources.

- **Name expansion.** The meaning of "OOL" is unattested. Treat it as an opaque
  extension, not as a field or runtime semantic.
- **Auxiliary byte enumeration.** Ship/frigate zero-based byte `+5` hull
  condition, byte `+7` skiff count, broadside hit resolution for byte `+5`,
  and byte `+6` packed frame-delay / animation-script-step semantics are public. The
  remaining gap is narrower: uncommon family-specific meanings for bytes `+5`
  and `+7` outside those roles are not fully enumerated.
- **Runtime readers of mirror files.** OUTSUBS owns a traced world-plane
  filename helper that chooses `BRIT.OOL` for the surface and `UNDER.OOL` for
  the underworld. Town entry writes the full live table to that selected file;
  town exit reloads the destination plane's full table over the live table.
  Both operations include slot zero and retain slot indices. Town actors are
  never merged into the plane table. The confirmed falls transition names both
  per-plane files while changing the party to the underworld plane. The
  remaining census is only for additional mirror-file callers outside these
  traced overworld transition paths.
- **Surface population.** The clean surface seed is empty, so every surface
  object overlay entry is created during play. Enumerating the full set of
  gameplay sources that write surface records - vehicle parking, dropped items,
  corpse creation, and any scripted placement - requires played saves or
  targeted runtime probes. The clean underworld seed's five records are fixed
  and enumerated in section 7; whether any later gameplay path adds more
  underworld records is the same open question on that plane.

## 12. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It intentionally omits decompiled code, assembly, implementation addresses, and raw private offset tables.

- First-pass save and `.OOL` survey, including file roles, sizes, record shape,
  seed observations, and the surface/underworld split: private analysis in
  `u5-decomp/formats/`.
- Save-handler operation order — the two per-plane reads that fill the staging
  halves, the entry-mode-gated single `UNDER.OOL` write-back, and the canonical
  `SAVED.GAM` / `SAVED.OOL` writes: re-derived 2026-08-22 directly from the
  shipped save overlay and from the two resident file wrappers it calls, whose
  read-versus-write identity was pinned by the DOS service each one issues and
  cross-checked against the load path's use of the same two wrappers. This
  supersedes the earlier private probe in `u5-decomp/notes/` and the
  "unconditional mirror writes, no per-plane read" reading previously carried
  here and in `u5-decomp/functions/CAST2_OVL/`, which had the
  direction of both per-plane transfers backwards.
- Fresh-game `SAVED.OOL` writer half order: `u5-decomp/functions/FONT_OVL/` and `u5-decomp/functions/INTRO_OVL/`.
- Seed-state contents in section 7 were read directly from the shipped `BRIT.OOL`, `UNDER.OOL`, and `INIT.OOL`, with the object type bytes resolved through the `LOOK2.DAT` object domain and the placements cross-checked against the shipped underworld and Britannia map data.
- Internal load-flow analysis, including `SAVED.OOL` read, unconditional mirror writes to `BRIT.OOL` and `UNDER.OOL`, and underworld disk-swap path.
- OUTSUBS runtime mirror-file selection and transition consumers:
  `u5-decomp/functions/OUTSUBS_OVL/`, and
  `u5-decomp/functions/OUTSUBS_OVL/`.
- The town round-trip's whole-table write/reload direction and slot-zero
  inclusion are derived from private analysis in
  `u5-decomp/functions/OUTSUBS_OVL/`, `u5-decomp/functions/ULTIMA_EXE/`, and
  `u5-decomp/notes/`.
- Active-object runtime model used to interpret each eight-byte record: `u5-spec/systems/active-objects.md`.
- Save/load system prose used for cross-checking lifecycle semantics: `u5-spec/systems/save-load.md`.
- Vehicle byte interpretation for ship boarding, X-it parking, and broadside
  damage: `u5-decomp/functions/CMDS_OVL/`, and
  `u5-decomp/functions/CMDS_OVL/`.
- Animator byte interpretation for the packed frame-delay / script-step field,
  including the corrected gate ordering and the withdrawal of the direction
  reading:
  `u5-decomp/functions/ULTIMA_EXE/`.
