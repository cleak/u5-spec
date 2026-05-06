# DATA.OVL

## 1. Scope

`DATA.OVL` is Ultima V's resident shared data image. Despite the `.OVL`
extension, it is not a callable overlay like `TOWN.OVL` or `COMBAT.OVL`.
The program loads it once during startup and uses it as the shared data
segment for the resident executable and the code overlays.

This document is a cleanroom format and behaviour spec. It describes the
information families that live in the resident image and how the rest of the
engine consumes them. It deliberately does not publish byte-exact offsets,
private address tables, assembly details, or copied string dumps from the
private decompilation workspace.

Byte-exact offsets, runtime address conversions, and unresolved raw tables live
only in `u5-decomp`. Public specs should refer to DATA.OVL content by semantic
name, such as "common-word dictionary", "Britannia chunk index", or
"text-window descriptor array", rather than by private byte address.

## 2. Runtime Role

The original engine is a resident core plus rotating overlays. The overlays do
not each carry their own copy of game-wide tables. Instead, they share one
resident data segment containing:

- Read-only table data: names, message fragments, dictionaries, class tables,
  placement tables, tile-class metadata, driver/file-name pools, and lookup
  records.
- Save-backed live state: the flat memory slab that becomes `SAVED.GAM`,
  plus state that is mirrored through the `.OOL` object-overlay files.
- Transient runtime buffers: map tiles, visibility grids, text-window state,
  combat scratch, NPC schedule state, disk I/O buffers, driver dispatch cells,
  redraw flags, and other per-session working memory.
- Compiler/runtime support data emitted by the Microsoft C runtime. This data
  is part of the loaded image but is not gameplay data.

Because every gameplay overlay shares this segment, a table discovered in
DATA.OVL may be read by several unrelated systems. For example, the same word
dictionary is used by conversation and shop text, the same tile-class metadata
is used by movement and visibility, and the same active-object table is
swapped through overworld, town, dungeon, and combat flows.

## 3. Addressing Caveats

DATA.OVL should not be treated as "file offset equals data-segment address".
The loaded data segment has a small compiler/runtime prefix and a fixed
runtime-to-file bias. The private notes document the exact conversion, but this
public spec does not reproduce it.

Practical rules:

- Treat DATA.OVL references in public specs as semantic references, not raw
  byte addresses.
- Do not mix code-segment address rules with data-segment references. Overlay
  code addresses, resident executable code addresses, and DATA.OVL data
  references use different translation conventions.
- If a byte-compatible tool needs original offsets, derive them inside
  `u5-decomp` and cite the resulting semantic finding here in prose.
- Multi-byte scalar data in the original image follows the DOS little-endian
  convention, but most public consumers should expose named fields rather than
  raw words.

## 4. Top-Level Content Model

DATA.OVL is best understood as a set of overlapping families rather than one
typed record. The original binary indexes it by fixed addresses; a modern
engine should instead split it into named resources and state structs.

| Family | Shape | Purpose |
|---|---|---|
| Runtime/compiler support | Small records, file buffers, runtime diagnostics | Startup and C library support; not gameplay semantics. |
| Vocabulary pools | NUL-terminated strings plus pointer tables | Shared names, UI labels, command prefixes, location names, NPC names, monster names, item names, and compact text dictionaries. |
| Game-data lookup tables | Byte arrays, word arrays, fixed-stride records, bitmaps | Tile metadata, item/class/combat data, spell data, encounter data, map indexes, coordinate tables, and placement rules. |
| Save-backed state | Contiguous live state, byte-for-byte persisted by save/load | Character roster, inventory, clock, scene, party position, quest flags, object table, and related state. |
| Transient buffers | Zero-initialized or runtime-populated blocks | Active map tiles, visibility rows, combat grids, text windows, NPC runtime queues, I/O buffers, and scratch. |
| Driver and overlay glue | Driver filenames, dispatch cells, active callback pointers | Display-driver selection and call routing. |

## 5. Table Families

### 5.1 Text and Vocabulary

The resident image holds most short, reusable engine strings. These are not one
monolithic script file. They are grouped by consumer and are often paired with
pointer tables or token dictionaries.

Important vocabulary families:

- Item, weapon, armour, equipment, reagent, class, status, NPC role, monster,
  virtue, mantra, location, shop, and landmark names.
- Abbreviated labels for narrow UI columns, especially equipment and reagent
  views.
- Command verb prefixes and short refusal or prompt fragments used by the
  A-Z command dispatcher.
- Mode-specific narration fragments for overworld, dungeon, combat, shops,
  character creation, intro, endgame, and status screens.
- Asset and data filenames used by loaders.
- A common-word dictionary shared by `.TLK` conversation text and
  `SHOPPE.DAT` shop text. The dictionary is addressed by token byte through a
  resident pointer table and expanded inline during text emission.

The actual words at each dictionary index are data content, not bytecode.
Conversation and shop specs describe how token bytes expand; this spec only
identifies DATA.OVL as the resident owner of the dictionary and pointer table.

### 5.2 Map and Location Metadata

The resident image contains metadata that makes the disk map files meaningful:

- A Britannia chunk-index table for the sparse overworld file. The table has
  one entry per 16-by-16 chunk in the surface world. A sentinel entry means the
  chunk is pure water and should be synthesized without disk I/O; other entries
  identify stored chunks in `BRIT.DAT`.
- Location coordinate tables used to map overworld cells to named towns,
  dwellings, castles, keeps, dungeons, shrines, and other fixed world features.
- Per-scene entry data used when entering or leaving town-mode locations. The
  town-mode spec treats this as semantic entry-position data rather than a raw
  byte table.
- Floor and subfloor lookup data used by multi-floor named locations,
  including locations that reuse an additional floor slice outside the normal
  two-floor pair.
- Small world-transition and moongate-related lookup tables. The exact table
  boundaries and all destinations remain partly open.

`UNDER.DAT` is dense from the map-format point of view. The source notes have
not established a separate public underworld chunk-index table in DATA.OVL.
Implementations should use the overworld spec's dense-underworld rule unless
future decompilation proves an additional resident table is required.

### 5.3 Tile Metadata

DATA.OVL carries lookup data that turns tile bytes into behaviour:

- A passability bitmap for map-tile ids. It covers the lower tile-id range used
  by map cells; sprite-only ids are represented through active-object records
  and do not need passability bits.
- Tile-class and animation-related tables used by movement, rendering,
  active-object animation, special trigger checks, and town dawn/dusk
  substitution.
- Likely line-of-sight or obstruction metadata, still not fully separated from
  class-derived rules.

The tile graphics themselves live in the tile sheet files. DATA.OVL supplies
the behavioural side of the tile catalog, not the pixels.

### 5.4 Magic and Virtue Tables

The magic system reads several resident tables:

- The fixed rune syllable vocabulary.
- Forty-eight compact spell tokens and the display names or incantation forms
  they identify.
- Per-spell recipe masks, scene allow masks, and other cast/mix support data.
- Reagent names and abbreviated reagent labels.
- Eight virtue names and the corresponding shrine mantras.
- Small virtue-prefix or name-match tables used by shrine, keyword, or prompt
  logic.

The exact per-spell recipe and allow-mask table layouts have not yet been
transcribed into public tables. The current public spell catalog records the
behavioural contract and points back to DATA.OVL as the source of the resident
spell metadata.

### 5.5 Item, Class, and Equipment Tables

Several compact numeric tables sit near the item and class vocabulary. Their
known or likely roles include:

- Item-name and abbreviation pointer tables.
- Per-item or per-equipment records for cost, combat value, armour value,
  carried/equipped constraints, and shop or inventory display.
- Character-class and party-class lookup data used by stats, equipment, magic,
  and combat.

The presence and broad purpose of these tables is clear, but not every field is
publicly named yet. Item and equipment tables should remain semantic until the
corresponding command, shop, and combat consumers have been fully re-derived.

### 5.6 Combat and Encounter Tables

Combat consumes resident data alongside `.CBT` arena records. DATA.OVL provides
global combat metadata that is not stored in arena files:

- Monster, NPC-role, and special-actor names.
- Per-class combat records: hit points, reward units, action flags, AI traits,
  death behaviour, and class-specific effect hooks.
- Per-arena or per-terrain spawn-count and leader-replacement data.
- Fixed combat placement slots or placement-shuffle support tables.
- Distance or range lookup data used by target selection.
- Narration fragments and command labels used by the combat command parser.

The arena files answer "what terrain is this fight on?" Resident DATA.OVL
tables answer "what actors appear, how many, where do they stand, and how do
their classes behave?"

### 5.7 Driver, Disk, and Asset Tables

The startup and I/O layers also use DATA.OVL:

- Display-driver filename pool and driver-selection labels.
- Runtime dispatch cells patched after the selected display driver is loaded.
- Disk-swap prompt fragments and data-file names used by loaders.
- Graphics and data asset filenames for intro, story, world, dungeon, and
  endgame loads.

Modern engines usually collapse the four historical display drivers into one
backend, but the text-output and driver specs still need this data to explain
the original boot and rendering path.

## 6. Runtime State Families

### 6.1 Save-Backed Resident State

The original save/load design is a memory image, not a serializer. A contiguous
region of the resident data segment is written to `SAVED.GAM` and read back in
one operation. `INIT.GAM` uses the same layout as the factory seed.

At a behavioural level this save-backed region contains:

- Sixteen character records for the Avatar and companion roster.
- The inn guest registry, which reuses character-record-shaped slots with an
  inn scene marker.
- Party-level counters: food, gold, keys, gems, torches, special items,
  weapons, armour, reagents, and pre-mixed spell charges.
- Active player, party size, selected character, status bytes, and character
  equipment.
- World clock and calendar.
- Scene byte, party position, floor/plane value, wind, vehicle, and redraw
  hints.
- Quest progress bitmasks, shrine progress, conversation/NPC flags, and
  per-turn state that happens to sit inside the saved slab.
- Dungeon-map memory and other persistent exploration records.
- The active-object table for the current live scene.

`formats/saved-gam.md` owns byte-compatible save offsets. This spec owns the
higher-level fact that the save image is a slice of DATA.OVL's live memory.

### 6.2 Object Overlay State

The active-object table is resident state. The save family pairs it with
`.OOL` companion files:

- `SAVED.OOL` holds the current per-plane object overlays.
- `BRIT.OOL` and `UNDER.OOL` mirror the surface and underworld halves.
- The live active-object table is populated from these files on world entry and
  written back through the save/load flow.

These object overlays are not static map data. They represent vehicles, dropped
items, movable objects, and other persistent world actors outside the immediate
map tile grid.

### 6.3 Map and Visibility Working Buffers

DATA.OVL also provides reusable runtime buffers:

- A 32-by-32 active tile buffer. In overworld mode it holds a 2-by-2 set of
  streamed 16-by-16 chunks. In town mode it holds one floor of a named
  location. Dungeon and combat modes reuse compatible row-stride buffers for
  their own terrain views.
- Visibility and terrain companion grids for the 11-by-11 viewport, including
  row padding used by rendering and object compositing.
- Scroll-origin, dirty/redraw, daylight, light-radius, torch, and spell-light
  flags.
- Moongate origin, destination, and animation state.

These buffers are rebuilt from map files and resident state. Most should be
treated as transient even when the original flat save image happens to include
nearby scratch bytes.

### 6.4 Text Output State

The text system keeps four resident window descriptors. Each descriptor holds:

- Screen rectangle in 40-by-25 cell coordinates.
- Window-local cursor position.
- Packed foreground/background colour.
- Style flags for underline, centering, inverse video, and related output
  behaviour.

The resident image also holds the active-window index, cached style fields, and
display-driver dispatch cells. `systems/text-output.md` owns the behavioural
details; DATA.OVL owns the storage.

### 6.5 NPC and Conversation Runtime

Town mode and conversation maintain several resident working areas:

- NPC schedule and runtime descriptor tables derived from the active
  location's `.NPC` block.
- Pathfinding queues and flood-fill scratch for the schedule walker.
- Per-conversation keyword pointer table and byte-runner scratch.
- Current conversation/shop selector state, including the shop-kind value
  resolved before a shop overlay runs.

Most NPC runtime state is re-derived on location entry or load. Persistent
conversation and quest facts live in the save-backed flag regions instead.

### 6.6 Combat Runtime

Combat uses resident working memory for:

- The live combat terrain grid copied from a `.CBT` arena.
- A combat actor/effect table parallel to the active-object table.
- A backup copy of world active-object state while combat is running.
- Per-round flags, target-selection scratch, AI direction scratch, damage and
  status narration buffers, and leave/victory/defeat state.

Combat cannot be saved mid-fight in the original rules. Combat after-effects
are persisted only after the framer restores world state and returns to the
calling mode.

## 7. Public Consumers

Current specs that consume DATA.OVL facts:

| Spec | DATA.OVL dependency |
|---|---|
| `formats/saved-gam.md` | Save image is a resident memory slice; `.OOL` files mirror resident object state. |
| `systems/save-load.md` | Load reads bytes into resident state; save flushes the same state out. |
| `systems/main-loop.md` | Scene byte, overlay dispatch state, boot setup, time/redraw state. |
| `systems/text-output.md` | Text-window descriptors, active-window cache, display-driver dispatch cells. |
| `systems/active-objects.md` | Shared 32-slot active-object table and combat backup/restore. |
| `systems/overworld.md` | Chunk index, location/shrine coordinates, moongate state, tile buffer, object overlays. |
| `systems/town-mode.md` | Scene partition, per-scene entry data, active floor, location load buffers, NPC runtime state. |
| `formats/location-dat.md` | Resident location-name and floor/entry tables needed to interpret per-class map blocks. |
| `systems/dungeon-mode.md` | Dungeon scene selection, runtime terrain buffers, room/encounter metadata. |
| `systems/doors-and-z-transitions.md` | Scene byte, floor/plane state, special tile behaviour, quest-gated door state. |
| `systems/visibility.md` | Visibility grid, terrain band, dirty flag, light radius, map buffer selection. |
| `catalogs/tile-catalog.md` | Passability bitmap, tile-class metadata, animation and trigger tables. |
| `formats/tlk.md` | Common-word dictionary pointer table and vocabulary expansion target. |
| `systems/conversation.md` | Dictionary expansion, keyword runtime state, NPC and quest flags. |
| `systems/shops.md` | Shop text dictionary, pricing/inventory tables, shop selector, gold and inn registry state. |
| `catalogs/npc-roster.md` | Resident role/name data and scene/location mapping cross-checks. |
| `systems/magic.md` | Rune, spell-token, reagent, mantra, recipe, and scene-allow metadata. |
| `catalogs/spell-list.md` | Spell order, rune vocabulary, reagent labels, and spell display metadata. |
| `systems/karma.md` | Virtue order, mantras, shrine coordinates, shrine progress flags. |
| `systems/combat.md` | Per-class combat tables, spawn metadata, range tables, actor scratch state. |
| `formats/cbt.md` | Distinction between arena terrain in `.CBT` and resident spawn/placement tables. |
| `catalogs/monster-bestiary.md` | Monster names, class records, traits, rewards, and combat behaviour tables. |

Future specs for intro, endgame, display-driver ABI, item catalog, equipment,
LOOK data, and shop-data formats should also cite DATA.OVL where they consume
resident labels or lookup tables.

## 8. Implementation Guidance

For a modern engine, do not load DATA.OVL as one opaque memory blob unless the
goal is strict DOS-binary compatibility. Prefer named resources:

- `CommonWordDictionary`
- `WorldLocationTable`
- `BritanniaChunkIndex`
- `ShrineTable`
- `TilePassability`
- `SpellMetadata`
- `ItemMetadata`
- `CombatClassTable`
- `TextWindowState`
- `SaveState`
- `ActiveObjectState`

When preserving compatibility with original files:

- Keep `SAVED.GAM` and `.OOL` byte-compatible according to their dedicated
  specs.
- Treat the DATA.OVL-derived static tables as immutable during play.
- Model tile mutations by changing live tile buffers, not by mutating static
  passability or class tables.
- Rebuild transient map, NPC, visibility, and combat buffers on mode entry or
  load, matching the existing system specs.
- Keep DATA.OVL-derived dictionary indices stable if rendering original `.TLK`
  or `SHOPPE.DAT` content.

## 9. Limitations and Open Work

- Byte-exact DATA.OVL offsets are intentionally omitted. They remain private to
  `u5-decomp`.
- This spec does not reproduce resident string dumps. It names categories and
  consumers only.
- Several compact numeric table families are only broadly identified:
  item/equipment records, some class stat records, dungeon/encounter records,
  moongate/world-transition records, and parts of combat AI metadata.
- The exact public table form for per-spell recipe masks and scene allow masks
  is pending a dedicated transcription pass.
- The line-of-sight obstruction source is not fully separated between a
  resident bitmap, class table, and derived tile-class rule.
- The underworld map-index story is still provisional: current public specs
  treat `UNDER.DAT` as dense unless further decompilation proves a resident
  underworld index is used.
- Some runtime scratch bytes are saved only because the original engine writes
  a flat memory slice. Their semantic importance after load varies by mode and
  is documented in the relevant system specs.

## 10. Sources

This is a cleanroom prose rewrite derived from the private resident-data
dissection in `u5-decomp/formats/data-ovl.md`, cross-checked against the public
specs listed in Section 7. It omits decompiled code, assembly, private offsets,
raw address tables, and copied string dumps.

For byte-compatible offsets and unresolved raw table boundaries, work in
`u5-decomp` and cite only the resulting semantic finding here.
