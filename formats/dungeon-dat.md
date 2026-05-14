# DUNGEON.DAT

Format specification for `DUNGEON.DAT`, the compact geometry file for the eight first-person dungeons. The file describes dungeon cells only: walls, ladders, fields, fountains, pits, doors, rooms, and similar cell classes. Rendering, movement, combat entry, lighting, and look-text are runtime behaviours described in `systems/dungeon-mode.md`.

## 1. Overview

`DUNGEON.DAT` is a fixed-size bank of dungeon floor plans. It contains eight dungeons. Each dungeon contains eight levels. Each level is an eight-by-eight grid. Each grid cell is a single packed byte whose upper four bits select the broad cell class and whose lower four bits carry a class-specific variant.

There is no file header, dungeon header, level header, checksum, compression, or terminator. A reader can split the file by arithmetic alone:

- Eight dungeon records.
- Eight level records per dungeon.
- Sixty-four cell bytes per level, stored row-major.
- Eight columns per row, with X increasing eastward and Y increasing southward.

The game loads the selected 512-byte dungeon record into a resident working image on entry and then indexes the current cell by level, row, and column within that loaded record. The on-disk bytes are not rewritten during ordinary play. Temporary changes such as opened doors, cleared fields, Search rewrites, fired trap markers, or room-trigger state are runtime state; they are never persisted by modifying `DUNGEON.DAT`. If the player saves while still inside that dungeon scene, the flat `SAVED.GAM` image preserves the current working-copy bytes; leaving and re-entering rebuilds from the static `DUNGEON.DAT` record plus durable overlays such as the room-clear bitmap.

For on-disk indexing, a dungeon record is 512 bytes and a level record is 64 bytes:

```text
dungeon_start = dungeon_index * 512
level_start = dungeon_start + level_index * 64
cell_index = level_start + y * 8 + x
```

The 512-byte unit is the whole dungeon, not one level. Runtime code may perform equivalent arithmetic against the loaded working image rather than seeking in the file for every cell access; keep the full-file byte layout separate from the runtime copy.

## 2. Dungeon And Level Ordering

The file is dungeon-major. All eight levels of dungeon zero appear first, followed by all eight levels of dungeon one, and so on through dungeon seven. Each dungeon block is 512 bytes. Within a dungeon, level zero is the surface-entry level and level seven is the deepest level. Each level block is 64 bytes.

Within a level, cells are row-major:

- The first eight bytes are row zero.
- The next eight bytes are row one.
- The last eight bytes are row seven.

The runtime position triple is `(level, x, y)`. Level increases downward. X increases west-to-east, and Y increases north-to-south. The facing direction used by the first-person renderer is not stored in `DUNGEON.DAT`; it is runtime state.

The file does not store dungeon names in-line. The engine binds dungeon records to names through the resident world-location table and the scene byte that selected the dungeon. The stock record order is:

| Record | Scene | Resident name |
|---:|---:|---|
| 0 | 33 | Deceit |
| 1 | 34 | Despise |
| 2 | 35 | Destard |
| 3 | 36 | Wrong |
| 4 | 37 | Covetous |
| 5 | 38 | Shame |
| 6 | 39 | Hythloth |
| 7 | 40 | Doom |

This is also the load order: entering the dungeon at scene thirty-three loads record zero, scene thirty-four loads record one, and so on.

## 3. Cell Byte

Each cell byte is split into two nibbles:

- The upper nibble is the broad dispatch class.
- The lower nibble is an attribute, subtype, decoration, direction flag, or sentinel depending on the class.

The upper nibble is the first branch most runtime systems take, but it is not a complete semantic type by itself. The dungeon renderer uses it to decide whether a cell blocks sight and whether to paint a wall, passage, or door. The movement handler uses it to reject blocked movement, climb ladders, trigger fields, or enter rooms. The Look handler uses it to choose the broad cell description printed to the message window.

The lower nibble is deliberately class-specific and can change how a high-nibble family behaves. For fountains, it selects the drinking effect. For energy fields, it selects the field type and may also carry the visit marker bit. For ladders, it refines the Z-transition behaviour. For the `0x6?` trap family, the full byte distinguishes observed fall traps, bomb traps, and fired/hidden marker variants. For wall, door, and flavour classes, it carries presentation and runtime-rewrite variants interpreted by the renderer, Search, or Open handlers. A generic reader should preserve the lower nibble even if it does not understand it.

The currently documented high-nibble dispatch families are:

| Upper nibble | Cell class | Format-level note |
|-------------:|------------|-------------------|
| `0x0` | Open passage or empty cell | Usually walkable and often described as nothing special. |
| `0x1` | Up ladder | Consumed by K-Klimb and Z-transition logic. |
| `0x2` | Down ladder | Consumed by K-Klimb and Z-transition logic. |
| `0x3` | Two-way ladder | Prompts for climb direction. |
| `0x4` | Chest | Static cell; contents and traps are generated by the Open/Search handlers. |
| `0x5` | Fountain | Low nibble selects the drink effect. |
| `0x6` | Pit / trap family | Observed runtime bytes `0x61`/`0x69` are fall traps and `0x62`/`0x6A` are bomb traps. |
| `0x7` | Passage variant | Treated as passage by Look and rendering paths. |
| `0x8` | Energy field | Low nibble distinguishes sleep, poison gas, fire, and electric field variants. |
| `0x9` | Secondary field family | Generic energy-field handling in current notes. |
| `0xA` | Room-helper state | Routed through the same underfoot helper as room triggers; not authored in the shipped records. |
| `0xB`-`0xE` | Wall families | Solid blockers with variant-specific presentation. |
| `0xF` | Heavy door or room trigger | Blocks movement unless opened, or hands off to dungeon-room combat for trigger variants. |

The complete low-nibble enumeration is still not fully pinned down. Treat it as opaque variant data unless a system spec names a specific subtype, and do not infer full behaviour from the upper nibble alone.

The energy-field family has one exact mapping already established. Base bytes `0x80`, `0x81`, `0x82`, and `0x83` are sleep, poison gas, wall of fire, and electric field respectively. Runtime spell placement can preserve the map's `0x08` marker bit, producing `0x88`, `0x89`, `0x8A`, and `0x8B` variants in the loaded dungeon image. These marker variants are runtime state and do not imply that the static file was rewritten.

The `0x08` bit is not a file-level visibility or exploration flag. Runtime
readers interpret it by cell class. The shared dungeon cell reader suppresses
that bit for classes below the wall/door band before handing a cell to the
first-person renderer, while wall/door/room-like classes can use it as an
extra-glyph or active-object overlay marker. V-View uses its own temporary
visited grid outside the dungeon record, so implementations must not persist
or infer automap discovery from this bit in `DUNGEON.DAT`.

## 4. Runtime Semantics

### Rendering

Dungeon mode renders `DUNGEON.DAT` as a sparse first-person view. The renderer is table-driven rather than a raycaster or line renderer. It walks a fixed number of cells forward from the party's current position, reads each cell's class nibble, and plots precomputed wall and door cues for the visible distance bands.

The renderer checks light before drawing. If neither torch light nor spell light is active, the dungeon view is black even though the geometry remains loaded and movement still reads the same cell bytes.

### Movement

Numpad and arrow-key movement consult the destination cell. Wall and closed-door classes block movement. Open passage classes allow movement. Field classes apply their effect as part of entry. Ladder classes are consumed by K-Klimb rather than ordinary forward movement.

The file does not encode the party's current position, facing, active scene, or current light state. Those are runtime state and save-image fields.

### Look And View

The L-Look command reads the dungeon focus cell selected by the dungeon relative-focus helper and prints a class-specific description. The helper can select ahead, right, left, or the party's current cell relative to the current facing, and Space/Pass aborts before any cell byte is read. That coordinate-selection contract belongs to `systems/dungeon-mode.md`; the format layer only supplies the packed cell byte at the chosen level/X/Y.

The V-View command reads the same cell bytes to flood-paint a top-down side-panel map centered on the party. It is not a separate minimap file or table; every glyph comes from the current level's packed cell bytes and runtime presentation state. Neither Look nor View changes the on-disk file.

V-View's visited/unvisited bookkeeping is scratch state for one invocation of
the overlay. It is initialized before the flood walk, prevents repeated work
inside that one view, and is discarded when the first-person panel is restored.
No exploration state is stored in this format.

One command-specific display exception is known: dungeon L-Look treats exact byte `0x61` as `0x00` for the description path only, so that byte is described as passage. It does not apply that normalisation to `0x69`, `0x62`, or `0x6A`. Format readers and gameplay systems must still preserve the original trap byte.

### Rooms And Combat

Room-trigger cells hand control to the dungeon room-entry helper. That helper chooses a combat arena from `DUNGEON.CBT`, sets up combat state, and calls the combat framer. `DUNGEON.DAT` marks that a room trigger exists; `DUNGEON.CBT` supplies the tactical arena used for the fight.

For stock room triggers, the high nibble is `0xF` and the low nibble is the arena slot. The selected `DUNGEON.CBT` record is:

```text
dungeon_record = scene - 33
arena_bank = 0 if dungeon_record <= 1 else dungeon_record - 1
arena_slot = cell_byte & 0x0F
arena_index = arena_bank * 16 + arena_slot
```

The shipped Despise record contains no `0xF?` room-trigger cells. The other seven room-bearing dungeons use all sixteen low-nibble slots somewhere in their geometry; repeated cells with the same low nibble share the same arena.

Room-trigger durability is split between a saved room-clear bitmap and runtime
cell rewrites. The original engine patches the loaded dungeon image after
combat by changing a `0xF?` trigger into `0xA?`, preserving the low nibble. It
also sets a saved room-clear bit keyed by dungeon and room id. On later load or
entry, the demotion pass uses that bitmap to rewrite matching `0xF?` cells in
the loaded image back to `0xA?`. The source file still contains the trigger
cell and is not rewritten.

The stock Doom record uses room id fifteen as the terminal final-room trigger.
It appears on the deepest level at local coordinate `(X=5, Y=7)`. By the
standard room-arena arithmetic, that cell selects Doom `DUNGEON.CBT` slot
fifteen, the final record in the arena file. That room's combat metadata is
part of the endgame handoff contract, so format readers and compatibility
tests should not treat the last Doom arena record as unused padding.

## 5. Loading And Persistence

`DUNGEON.DAT` is static content. On dungeon entry, the game reads the selected 512-byte dungeon record into a working image and gameplay systems read from that image while dungeon mode is active. The save file persists the scene byte, level, X/Y position, light counters, related runtime flags, and the current 512-byte working copy if the save is made while that dungeon scene is active. It does not patch or rewrite the source dungeon file.

Consequences:

- A byte-compatible fresh-entry loader should derive dungeon cells from
  `DUNGEON.DAT`, then replay durable overlays such as cleared-room demotion.
  A byte-compatible save loader that resumes an active dungeon scene should
  preserve the saved 512-byte working copy.
- Temporary effects, such as opened doors or dispelled fields, should be modelled as runtime overlays over the static cell byte.
- Saving and loading does not require writing or modifying `DUNGEON.DAT`.

## 6. Validation And Invariants

A byte-compatible reader should enforce these invariants:

- The file is exactly 4,096 bytes.
- The file contains eight dungeon records.
- Each dungeon record is exactly 512 bytes.
- Each dungeon record contains eight levels.
- Each level contains exactly sixty-four bytes, interpreted as an eight-by-eight row-major grid.
- The on-disk byte index for a cell is `dungeon_index * 512 + level_index * 64 + y * 8 + x`.
- X, Y, dungeon index, and level index are all three-bit quantities in normal content: `0..7`.
- Every cell byte is meaningful as a packed class/variant value, even when the variant is not yet decoded.
- Unknown low-nibble values must be preserved rather than normalised.

The format itself has no invalid high-nibble value because all sixteen possible high nibbles are byte-representable. Validation should therefore focus on file size, coordinate range, and whether a gameplay system knows how to interpret a class/variant pair.

## 7. Implementation Notes

A decoder needs only the file bytes and the record ordering from Section 2:

1. Verify the file is exactly the expected size for eight dungeons, eight levels each, and sixty-four cells per level.
2. Split the file into 512-byte dungeon records, then 64-byte level records, then row-major cells.
3. For each cell, preserve the full byte and expose helper accessors for class nibble and variant nibble.
4. Let gameplay systems interpret class and variant; the format layer should not collapse unknown variants.

For rendering tools, it is useful to display both the class and variant. A map viewer that paints only walls versus passages can ignore most lower-nibble details, but a gameplay engine must keep them because fountains, fields, ladders, Search-revealed passages, doors, room triggers, and traps depend on them.

## 8. Cross-References

- The first-person dungeon runtime, including scene-byte selection, movement, lighting, Look/View, room triggers, and the sparse renderer: `systems/dungeon-mode.md`.
- The combat arenas used by room triggers: `formats/cbt.md`.
- The save-image fields that persist current scene and position: `formats/saved-gam.md`.
- The tile and wall rendering vocabulary used by the 2D tile renderer: `formats/tiles.md`.

## 9. Format Boundary And Runtime Work

The file-format contract is complete at byte-layout depth: size, record order,
level order, row-major cell order, and class/variant preservation are fixed.
Remaining work belongs to runtime consumers and custom-content policy.

- **Lower-nibble runtime interpretation.** The upper-nibble class split is well
  supported. The lower nibble's full meaning remains partially open for wall
  rendering, door rendering, trap marker variants, and the secondary field
  family. Format readers must preserve these bits even when a runtime system
  has not promoted a public subtype name yet.
- **Variant room compatibility.** The stock baseline persists room completion
  through the save-image room-clear bitmap and rebuilds cleared-room demotions
  from static `DUNGEON.DAT` cells. Custom content with room ids outside the
  stock room-clear writer's accepted set should define its own compatibility
  policy rather than assuming every possible low nibble is persisted.

## 10. Sources

This spec is a cleanroom prose rewrite derived from the project notes below. It intentionally omits decompiled code, assembly, implementation addresses, and raw private offset tables.

- First-pass map and arena survey, including the dungeon file dimensions and packed-nibble cell model: `u5-decomp/formats/maps.md`.
- Dungeon record/name/scene binding and selected-record load: derived from the MAINOUT E-Enter helper and the DATA.OVL world-location table in the private analysis workspace.
- Internal dungeon turn-loop analysis, including the loaded dungeon image, current-level indexing, renderer relationship, and room-trigger relationship to combat arenas: `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- Internal dungeon post-action and fall-trap helper analysis, including the exact observed fall-trap and bomb-trap bytes and visit-local trap rewrites: `u5-decomp/functions/DUNGEON_OVL/0x0C76_dungeon_post_action.md`.
- Internal dungeon movement destination-effect analysis: `u5-decomp/functions/DUNGEON_OVL/0x0502_dungeon_move_dispatch.md`.
- Internal dungeon Look analysis, including the relative-focus helper handoff, high-nibble class switch, and fountain/field subtype behaviour: `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`, `u5-decomp/functions/SJOG_OVL/0x006C_sjog_dir_step.md`, and `u5-decomp/functions/SJOG_OVL/0x002A_sjog_apply_dir_step.md`.
- Internal CAST overlay field-placement analysis, including the live-map field byte mapping and marker-bit preservation used by dungeon field spells.
- Internal dungeon View analysis, including the top-down level view relationship to the same dungeon cell data.
- Existing dungeon-mode system prose used for cross-checking runtime semantics: `u5-spec/systems/dungeon-mode.md`.
