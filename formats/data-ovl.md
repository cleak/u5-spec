# DATA.OVL

## 1. Scope

`DATA.OVL` is Ultima V's resident shared data image. Despite the `.OVL`
extension, it is not a callable overlay like `TOWN.OVL` or `COMBAT.OVL`.
The program loads it once during startup and uses it as the shared data
segment for the resident executable and the code overlays.

This document is a cleanroom format and behaviour spec. It describes the
information families that live in the resident image and how the rest of the
engine consumes them. It deliberately does not publish byte-exact offsets,
private address tables, assembly details, decompiler output, implementation
listings, or copied string dumps from the private analysis workspace.

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
  combat scratch, NPC schedule state, disk I/O buffers, the display-driver
  dispatch cell, the separate resident screen-mode dispatch cell,
  disk-prompt/mode-loop scratch, redraw flags, and other per-session working
  memory.
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
| Transient buffers | Zero-initialized or runtime-populated blocks | Active map tiles, visibility rows, combat grids, text windows, NPC runtime queues, I/O buffers, disk-prompt/mode-loop scratch, and other session state. |
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
- Wind-status labels, stored in the public presentation order Calm, North,
  South, East, and West, plus the shared suffix used by the overworld
  wind-message helper.
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
- A `WorldLocationTable` used to map overworld cells to named towns,
  dwellings, castles, keeps, dungeons, and other fixed world features. The
  first thirty-two entries are the town-mode location entries; overworld entry
  uses the matched row index plus one as the scene byte. Rows thirty-two
  through thirty-nine are the normal dungeon entries; the same row-plus-one
  rule yields dungeon scenes thirty-three through forty, and
  `matched row - 32` is the `DUNGEON.DAT` record index. The ordered rows
  supply the resident location-name strings published semantically in
  `catalogs/gazetteer.md`, `formats/npc.md`, and `formats/dungeon-dat.md`.
- Per-scene entry data used when entering or leaving town-mode locations. The
  town-mode spec treats this as semantic entry-position data rather than a raw
  byte table. The required entry-position resource for named locations is a
  `LocationEntryYTable`: one Y coordinate per town/dwelling/castle/keep scene.
  Town-mode entry fixes X at fifteen and Z at zero when using this default.
- A location floor-base table used by town mode. Each scene's entry is a
  1,024-byte floor-page index within the selected town/dwelling/castle/keep
  file; the signed current-floor byte is added to it before loading a floor.
- Two compact moon glyph tables read by the lower sky/status strip renderer.
  They are independent day-indexed presentation tables for Trammel and Felucca,
  not the saved-slot natural-moongate live-terrain schedule.
- A three-slot Shadowlord state table, one slot each for Faulinei, Astaroth,
  and Nosfentor. A living slot stores that Shadowlord's current hideout id in
  the compact `1..8` hideout range; the vanquished marker retires the slot from
  future midnight rerolls. Consumers use the same state for the Sextant/view
  report, town-entry Shadowlord installation, Stonegate atmospheric
  presentation rows, Yell's live-vs-vanquished gate, and Doom's all-vanquished
  entrance gate.

`UNDER.DAT` is dense from the map-format point of view. The source notes have
not established a separate public underworld chunk-index table in DATA.OVL.
Implementations should use the overworld spec's dense-underworld rule unless
future analysis proves an additional resident table is required.

### 5.3 Tile Metadata

DATA.OVL carries lookup data that turns tile bytes into behaviour:

- A thirty-two-byte base terrain bitset for map-tile ids `0..255`. The byte is
  selected by `tile_id >> 3`, and bits are read most-significant first. A set
  bit rejects that tile for the base terrain predicate; a clear bit accepts it,
  subject to the caller-specific query selected by the tile-class dispatcher,
  vehicle rules, and occupancy gates. Sprite-only ids are represented through
  active-object records and do not need static terrain bits. Combat arenas use
  distinct tile-class passability lookups.
- A tile-class query predicate table keyed by caller class/query bytes, plus
  auxiliary per-tile masks used by specialized movement and interaction
  predicates. The named movement callers currently include foot/avatar, horse,
  carpet, ship, and skiff transport families; other active-object and
  interaction callers remain data-driven until their consumers are fully
  promoted. These tables are used by movement, rendering, active-object
  animation, special trigger checks, and town dawn/dusk substitution.
- A separate NPC pathfinding bitmap used by the town schedule flood-fill
  workspace. It is one bit per tile id: a set bit marks a tile open for NPC
  pathfinding, and a clear bit marks it as an obstacle. This resource is
  distinct from both the base terrain bitset and the caller-query dispatcher;
  `systems/npc-schedules.md` owns the public pathfinding ranges and special
  waypoint/chair-marker rules.
- The six-level daylight gradient consumed by the time cleanup at dawn and
  dusk. On the original light scale it steps through 2, 5, 10, 20, 34, and
  49 before the separate full-daylight value of 50 takes over.
- A thirty-six-byte folded squared-distance lookup for eleven-by-eleven
  viewport coordinates. Consumers fold each coordinate around centre cell five,
  index the resulting 6x6 table, and receive `(5 - folded_x)^2 + (5 -
  folded_y)^2`. The fog post-pass uses this to choose clear versus dim
  renderer markers. Combat target scoring uses a separate computed range
  primitive, not this lookup.
- A visibility tile-classifier resource: a small adjacent-only special-case set
  plus a nineteen-entry tile-id propagation-blocker list. Its public owner is
  `systems/visibility.md`; do not conflate it with movement passability, LOOK
  strings, or active-object sprite ids.
- A local-light-source candidate resource used by the visibility system's
  thirty-two by thirty-two local-light mask refresh. Public source ids are
  grouped as `0xB0..0xB3`, `0xBC..0xBF`, `0xDC`, and `0xDE`; the refresh
  scans the active map window for those candidates and carves fixed-radius
  nonzero mask regions around them.

The tile graphics themselves live in the tile sheet files. DATA.OVL supplies
the behavioural side of the tile catalog, not the pixels.

### 5.4 Magic and Virtue Tables

The magic system reads several resident tables:

- The fixed rune syllable vocabulary.
- Forty-eight compact spell tokens, plus a separate sparse long-incantation
  display phrase table. The compact tokens are sorted selector-letter strings;
  the shared spell prompt sorts typed selector letters before comparing against
  the token table. The long phrases are display evidence, not the authoritative
  spell-id mapping for the final high-circle entries.
- Per-spell recipe masks, scene allow masks, and other cast/mix support data.
- A four-entry field-byte lookup used by the create-field spells. Semantically
  it maps Fire Field to the wall-of-fire byte, Poison Field to the poison-gas
  byte, Sleep Field to the sleep-field byte, and Energy Field to the electric
  field byte; the spell handler may preserve the map's visit marker bit when
  writing the live dungeon image.
- A sibling arena-field lookup for the same four spells. It does not write the
  dungeon map byte; it selects the combat field kind consumed by the arena
  helper, where Poison Field routes to poison status, Sleep Field routes to
  sleep status, Fire Field uses a raw damage cap of 21 before defense, and
  Energy Field uses a raw damage value of zero in the same path.
- Reagent names and abbreviated reagent labels.
- Eight virtue names and the corresponding shrine mantras.
- Small virtue-prefix or name-match tables used by shrine, keyword, or prompt
  logic.
- Two parallel four-entry Blackthorn challenge tables. One selects the virtue
  or Word-of-Power term printed in each prompt, and the other selects the
  accepted response term. Both tables point into the resident virtue/mantra
  vocabulary. The traced live prompt ordinals are Honesty/Ahm,
  Compassion/Mu, Valour/Ra, and Justice/Beh; `systems/blackthorn.md` owns the
  prompt-loop behaviour and answer-matching rules.
- Character-creation virtue tables: per-virtue stat deltas and the symmetric
  `QUESTION.DAT` pair-to-record selector. The public record-ordinal mapping is
  listed in `formats/question-dat.md`.

The per-spell recipe and scene allow-mask tables are decoded semantically in
`catalogs/spell-list.md`. That catalog lists the recipe as reagent names and
the scene mask as scene-class labels rather than raw resident bytes.

### 5.5 Item, Class, and Equipment Tables

Several compact numeric tables sit near the item and class vocabulary. Their
known or likely roles include:

- Item-name and abbreviation pointer tables. The equipment abbreviation table
  gives the public forty-eight-row equipment item-id order listed in
  `catalogs/item-list.md`.
- Per-item or per-equipment records for cost, combat value, armour value,
  R-Ready burden, carried/equipped constraints, and shop or inventory display.
- Equipment-class metadata consumed by R-Ready. The public slot/counter
  contract and class-tag meanings are in `systems/inventory.md` and
  `catalogs/item-list.md`. The same specs also list the R-Ready burden values
  used by the Strength gate.
- Character-class and party-class lookup data used by stats, equipment, magic,
  and combat.
- Read-only shop stock and pricing resources. Arms shops combine a canonical
  equipment-price table with the speaking party member's Intelligence to
  compute displayed equipment buy prices. Zero entries in that canonical table
  suppress arms sale/buyback for that item, and a separate per-shop
  eight-candidate table feeds the arms `B` buy menu. Candidate bytes are direct
  equipment item ids: the same id selects the item-name row, the base-price
  row, and the save-backed equipment counter. The arms `S` sell menu instead
  scans the party's nonzero equipment counters and applies the sell-back offer
  path. Guild shops consume fixed per-shop stock and unit-price records.
  Healers use per-instance cure, heal, and resurrection price tables; the
  Minoc healer instance, `The Healers Mission`, bypasses the ordinary price
  path for Cure and Heal.
  Herbalists use a reagent price/availability matrix: nonzero cells are the
  per-ounce prices shown in the compact reagent menu, and zero cells mean that
  herbalist does not sell that reagent. Tavern and meal-counter flows use
  resident drink-list, menu-record, and price selectors before `SHOPPE.DAT`
  renders the visible menu prose. `SHOPPE.DAT` supplies the prose, but these
  resident tables supply the stock identity, availability, selectors, and
  prices.
- Sage rumour resources: a fixed topic list, per-topic fee table, per-topic
  displayed subject, destination selector, destination-name pool, and rumour
  template selectors. The sage shop flow combines these tables with
  `SHOPPE.DAT` substitutions after the player pays for a matched topic; the
  clean row catalog is `catalogs/sage-rumours.md`.

The presence and broad purpose of these tables is clear, but not every field is
publicly named yet. Item and equipment tables should remain semantic until the
corresponding command, shop, and combat consumers have been fully re-derived.

### 5.6 Combat and Encounter Tables

Combat consumes resident data alongside `.CBT` arena records. DATA.OVL provides
global combat metadata that is not stored in arena files:

- Monster, NPC-role, and special-actor names.
- A fixed 48-row combat-class stat table shared by party combat classes,
  special actor classes, NPC-role classes, and monster classes. Each row is
  eight bytes wide. The public row schema is: combat tier, speed seed used for
  phase timing, an HP-comparison byte used by chest/encounter team-flip
  checks, defense rating, attack-damage cap, maximum HP, default spawn count,
  and default kill/drop cap. Maximum HP also supplies the monster spawn HP and
  the raw reward-unit input. A separate per-class flag table immediately
  follows the class records and should be modeled as class traits, not as
  executable scripts.
- Class-name pointers for the same actor-class namespace.
- Decoded damage/death flags. The analyzed baseline's class-flag table confirms
  split-on-damage, halve-physical-damage, physical immunity, faction override,
  turnable attacks, ranged/effect branch selection, the magic-immune
  ranged/effect gate, teleport-capable movement, poison/status attacks,
  vanish-on-death, and the Gazer/Gargoyle special-death branches through their
  consumers. Neighboring per-class side tables supply attack range caps and
  effect kinds for the ranged/effect helper. The same flag table also drives
  the monster-turn special hook:
  `0x0040` is possess/charm-on-turn, `0x0800` is blink/phase, and `0x0400` is
  summon-daemon. The analyzed v1 baseline assigns possess, blink/phase,
  summon-daemon, teleport-capable movement, poison/status attack, and
  vanish-on-death rows as published in `catalogs/monster-bestiary.md`.
  Remaining unknowns are limited to residual component-bit labels and
  source-free publication of the ranged/effect side-table values and row
  assignments, not to the eight-byte stat-row layout or the published
  class-trait assignments. Current COMSUBS re-decode
  removed the older class-script-table hypothesis: the ordinary monster AI path
  uses combat actor/effect records, target-selection scratch, helper outputs,
  and the per-class flag/stat tables rather than a separate mutable per-class
  script state table. Do not treat the eight-byte rows as a flat hit-chance or
  damage matrix; their bytes are read by distinct consumers.
- Combat target mapping: a per-combat-slot byte map from caster slot to the
  current target slot. The all-ones sentinel means no target is mapped. The
  combat C-Cast interference gate reads this before the shared spell dispatcher
  runs; an adjacent valid visible/awake mapped target can interrupt casting.
  Writers and exact lifetime are still open.
- Random-encounter terrain-bucket tables. The encounter selector consumes four
  ordered weighted resources: surface default/aquatic, underworld
  default/aquatic, surface land, and underworld land. `systems/encounters.md`
  owns the public row weights and active-object payload families; this spec
  records DATA.OVL as the resident owner of the tables.
- Per-arena or per-terrain spawn-count and leader-replacement data.
- Combat placement coordinate tables populated from the selected arena record's
  metadata, plus placement-shuffle support state.
- Ambush/camp reveal records. This resident table has eight logical records
  consumed by the combat reveal helper. Each record supplies a trigger
  coordinate, the terrain tile to reveal, and up to two target coordinates in
  the live eleven-by-eleven arena grid. When the active combat mode permits
  reveals and an actor steps on a trigger coordinate, the helper consumes that
  trigger so the record cannot fire twice, stamps the reveal tile into each
  in-range target coordinate, treats out-of-range target coordinates as
  "unused", and redraws the arena. These are runtime arena mutations, not
  persistent world-map edits. The shipped record values are asset data and are
  not reproduced here.
- Distance or range lookup data used by target selection.
- Narration fragments and command labels used by the combat command parser.
- A compact trap-effect lookup used by the shared non-combat trap resolver.
  Semantically it maps a random trap roll onto the four resident trap-effect
  families specified in `systems/traps.md`; the public format spec names the
  role rather than publishing raw resident bytes.

The combat-class stat row is interpreted field-by-field:

| Byte | Clean field | Consumer-facing meaning |
|------|-------------|--------------------------|
| `+0` | Combat tier | Class level used by the chest/encounter team-flip comparison. |
| `+1` | Speed seed | Base input for combat phase timing when an actor is placed. Higher values refresh the phase counter sooner after randomization and clamping. |
| `+2` | HP comparison | Class endurance input used by the chest/encounter team-flip comparison. It is separate from maximum HP. |
| `+3` | Defense rating | Target-side defense input for attack resolution and a team-flip comparison arm. Higher values make ordinary damage harder to land. |
| `+4` | Attack cap | Attacker-side maximum for ordinary monster attack damage; the boss-scale maximum has its own special hit behavior in combat. |
| `+5` | Maximum HP | Spawn HP for monsters, wound-threshold basis, and raw reward-unit input. |
| `+6` | Default spawn count | Terrain and dungeon encounter count seed, with special exact-count sentinels handled by encounter setup. |
| `+7` | Default kill/drop cap | Default kill-path drop marker input before the combat framer restores the world object table. |

The arena files answer "what terrain is this fight on?" Resident DATA.OVL
tables answer "what actors appear, how many, where do they stand, and how do
their classes behave?"

### 5.7 Driver, Disk, and Asset Tables

The startup and I/O layers also use DATA.OVL:

- Display-driver filename pool and driver-selection labels.
- Runtime dispatch cells patched after the selected display driver is loaded.
- Disk-swap prompt fragments and data-file names used by loaders.
- Ultima IV transfer media labels and the `PARTY.SAV` source-save filename
  consumed by intro transfer; `systems/u4-transfer.md` owns the behavior.
- Graphics and data asset filenames for intro, story, world, dungeon, and
  endgame loads.
- Intro/story presentation metadata used by the story-slide loop to select
  per-step art, placement, text, and local display-effect parameters. This
  compact metadata belongs to intro presentation, not to natural moongate or
  world-transition behavior.

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
- Runtime spell/effect counters, including personal-light counters and the
  shared active-effect/runtime tag plus countdown.
- Carried equipment/use-item counters: a byte-indexed inventory band used by
  Z-stats/R-Ready, arms shops, and some combat/spell helper paths. These are
  inventory quantities, not spell effect timers.
- Quest progress bitmasks, shrine progress, save-backed NPC flags, TALK
  per-scene branch flags, one-conversation signal arrays, and per-turn state
  that happens to sit inside the saved slab.
- Dungeon-map memory and other persistent exploration records.
- The active-object table for the current live scene.

`formats/saved-gam.md` owns byte-compatible save offsets. This spec owns the
higher-level fact that the save image is a slice of DATA.OVL's live memory.

### 6.2 Object Overlay State

The active-object table is resident state. The save family pairs it with
`.OOL` companion files:

- `SAVED.OOL` holds the current per-plane object overlays.
- `BRIT.OOL` and `UNDER.OOL` are the per-plane files refreshed by the load
  path from the surface and underworld halves of `SAVED.OOL`.
- The save path stages object-overlay data through the per-plane files and
  writes the canonical `SAVED.OOL`; only the underworld mirror has a traced
  conditional save-time write. The detailed lifecycle belongs to
  `systems/save-load.md` and `formats/ool.md`.

These object overlays are not static map data. They represent vehicles, dropped
items, movable objects, and other persistent world actors outside the immediate
map tile grid.

### 6.3 Map and Visibility Working Buffers

DATA.OVL also provides reusable runtime buffers:

- A 32-by-32 active tile buffer. In overworld mode it holds a 2-by-2 set of
  streamed 16-by-16 chunks. In town mode it holds one floor of a named
  location. Dungeon and combat modes reuse compatible row-stride buffers for
  their own terrain views.
- A viewport visibility grid with eleven active cells per row and resident row
  padding. Visibility producers, fog refinement, active-object compositing, and
  the renderer exchange terrain bytes, sprite stamps, and renderer marker bytes
  through this grid.
- A parallel terrain companion band with a narrower row stride. Water-bound
  objects and water-creature compositor branches place the underlying or
  companion tile here while the visibility grid receives the "use companion"
  marker.
- A player/avatar active-object mirror refreshed from scene, map-position,
  floor/plane, and avatar-tile state immediately before object compositing.
- Scroll-origin, dirty/redraw, daylight, light-radius, torch, and spell-light
  flags. The Search/Jimmy/Open/Get command family distinguishes at least two
  redraw-hint roles: tile-map mutations that require the visible map to be
  refreshed, and inventory or party-state changes that require status refresh.
  The exact bit-level encoding is an implementation-compatibility detail, but
  the semantic split is visible in command behavior.
- A shared coordinate/animation scratch block that the moongate animator
  interprets as origin, optional destination, and phase state when active. The
  same resident words are reused by chunk-loading and mode-entry contexts, so
  they are transient subsystem scratch rather than durable saved-slot
  natural-gate schedule storage.

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

The resident image also holds the active-window index, cached style fields, the
display-driver dispatch cell, and the separate resident screen-mode dispatch
cell. `systems/text-output.md` owns text behaviour, `display-driver-abi.md`
owns the driver ABI, `screen-mode-dispatch.md` owns the resident screen-mode
controller, and DATA.OVL owns the storage.

### 6.5 Disk-Prompt And Presentation Scratch

The resident image keeps session-only prompt and mode-loop bytes alongside the
screen-mode dispatch cell. This family includes the running disk-prompt context
used by disk-swap and retry paths, the small prompt-state table read by the
presentation controller, and the cached rendered-mode marker used to suppress
redundant setup. These bytes are live orchestration state only: they survive
across calls during one process, but they are not part of the saved-game image.
The disk-prompt request path normalizes historical prompt modes two and five to
mode one before updating this context; the storage remains a resident
presentation table, not saved-game or scene state.

`systems/screen-mode-dispatch.md` owns the presentation-controller behaviour,
and `systems/save-load.md` owns the disk-prompt and retry contract.

### 6.6 Input Runtime State

The input pipeline keeps its own transient resident state alongside the text
windows:

- Cursor-blink base glyph, blink modulus, and current blink phase.
- The cursor-advance gate shared with the text output primitive, so cursor
  blink frames can be painted in place.
- The prompt-character byte whose printable/non-printable range decides whether
  idle polling advances the world tick.
- The one-keystroke buffer-flush gate and the numpad-equivalent flag used
  between the low-level keyboard reader and the top-level command translator.
- A small extended-key translation table. The traced DOS table accepts the four
  arrow keys plus Home, End, PgUp, and PgDn.
- A first-idle-tick or redraw hint stamped by the command-input loop for at
  least town-mode entry.

The extended-key translation table is eight entries wide:

| Physical key family | Stored translation role |
|---|---|
| Left arrow | West cardinal pre-translation; the input layer converts it to the final west direction code. |
| Right arrow | East cardinal pre-translation; the input layer converts it to the final east direction code. |
| Up arrow | North cardinal pre-translation; the input layer converts it to the final north direction code. |
| Down arrow | South cardinal pre-translation; the input layer converts it to the final south direction code. |
| Home | Northwest diagonal direction code. |
| End | Southwest diagonal direction code. |
| PgUp | Northeast diagonal direction code. |
| PgDn | Southeast diagonal direction code. |

Function-key remapping does not use this table. The keyboard reader converts
F1 through F10 from their contiguous scancode range into the separate
function-key block described in `systems/input.md`.

`systems/input.md` owns the behavioural translation rules. DATA.OVL owns the
resident state and lookup storage.

### 6.6 NPC and Conversation Runtime

Town mode and conversation maintain several resident working areas:

- NPC schedule and runtime descriptor tables derived from the active
  location's `.NPC` block.
- Pathfinding queues and flood-fill scratch for the schedule walker.
- Per-conversation reserved-keyword scan state, ordinary keyword-scan scratch,
  and byte-runner scratch.
- Per-scene TALK branch flags and one-conversation signal arrays used by the
  conversation byte runner and cleanup path.
- Current conversation/shop selector state, including the shop-kind value
  resolved from the high-range `.NPC` dialog-index shop trigger at Talk entry,
  the current local shop-instance index resolved from the active scene, and the
  vendor/shop substitution buffers prepared before a shop overlay runs.

Most NPC runtime state is re-derived on location entry or load. Persistent
conversation and quest facts live in the save-backed flag regions instead;
`systems/quest-flags.md` separates those durable fields from TALK's branch and
cleanup scratch.

### 6.7 Combat Runtime

Combat uses resident working memory for:

- The live combat terrain grid copied from a `.CBT` arena.
- Four small combat setup tables copied from the selected outdoor arena
  record: two six-byte resident setup tables and two sixteen-byte placement
  coordinate tables. The placement tables supply arena-local monster arrival
  coordinates; the six-byte table entries remain unnamed.
- A combat actor/effect table parallel to the active-object table. Its per-slot
  descriptor row carries HP/wound state, base-step, flags/faction,
  owner/target/class, active-object back-reference, phase counter, and arena
  coordinates.
- A backup copy of world active-object state while combat is running.
- Per-slot pending combat-cast target bytes used by the combat C-Cast pre-gate.
- The ambush/camp reveal table's trigger state while a fight is live. A fired
  reveal entry is invalidated in this runtime copy so later movement over the
  same coordinate does not restamp the arena.
- Per-round flags, target-selection scratch, AI direction scratch, damage and
  status narration buffers, and leave/victory/defeat state.

Combat cannot be saved mid-fight in the original rules. Combat after-effects
are persisted only after the framer restores world state and returns to the
calling mode.

## 7. Public Consumers

Current specs that consume DATA.OVL facts:

| Spec | DATA.OVL dependency |
|---|---|
| `formats/saved-gam.md` | Save image is a resident memory slice; `SAVED.OOL` is the canonical object-overlay companion and per-plane mirrors are refreshed by the load path. |
| `systems/save-load.md` | Load reads bytes into resident state; save flushes the same state out. |
| `systems/boot.md` | Machine/display probe outputs, startup runtime state, display-driver selection inputs. |
| `systems/overlay-abi.md` | Overlay residency metadata, shared-buffer grouping, and loader-facing state. |
| `systems/main-loop.md` | Scene byte, overlay dispatch state, time/redraw state. |
| `systems/display-driver.md` | Display-driver filename pool, the display-driver dispatch cell, text-cell state, and rendering contract. |
| `systems/screen-mode-dispatch.md` | Separate resident screen-mode dispatch cell and presentation controller. |
| `systems/text-output.md` | Text-window descriptors, active-window cache, and display-driver-facing text state. |
| `systems/input.md` | Cursor-blink state, keyboard translation tables, prompt-state gate, typeahead flush gate. |
| `systems/active-objects.md` | Shared 32-slot active-object table and combat backup/restore. |
| `systems/overworld.md` | Chunk index, location/shrine coordinates, shared coordinate scratch used by chunk loading and moongate animation, tile buffer, object overlays. |
| `systems/town-mode.md` | Scene partition, per-scene entry data, active floor, location load buffers, NPC runtime state. |
| `formats/location-dat.md` | Resident location-name and floor/entry tables needed to interpret per-class map blocks. |
| `systems/dungeon-mode.md` | Dungeon scene selection, runtime terrain buffers, room/encounter metadata. |
| `systems/doors-and-z-transitions.md` | Scene byte, floor/plane state, special tile behaviour, quest-gated door state. |
| `systems/visibility.md` | Visibility grid, terrain band, dirty flag, light radius, map buffer selection. |
| `catalogs/tile-catalog.md` | Base terrain bitset, caller-query tile-class metadata, animation and trigger tables. |
| `formats/tlk.md` | Common-word dictionary pointer table and vocabulary expansion target. |
| `systems/conversation.md` | Dictionary expansion, keyword runtime state, conversation bytecode execution. |
| `systems/quest-flags.md` | Durable quest/NPC flags versus TALK per-scene branch flags and one-conversation signals. |
| `systems/shops.md` | Shop text dictionary, pricing/inventory tables, shop selector, gold and inn registry state. |
| `catalogs/npc-roster.md` | Resident role/name data and scene/location mapping cross-checks. |
| `systems/magic.md` | Rune, spell-token, reagent, mantra, recipe, and scene-allow metadata. |
| `catalogs/spell-list.md` | Spell order, rune vocabulary, reagent labels, and spell display metadata. |
| `systems/karma.md` | Virtue order, mantras, shrine coordinates, shrine progress flags. |
| `systems/chargen.md` | Character-creation virtue stat deltas and questionnaire pair selector. |
| `systems/combat.md` | Per-class combat tables, spawn metadata, range tables, actor scratch state. |
| `formats/cbt.md` | Distinction between arena terrain/metadata in `.CBT` and resident spawn tables. |
| `catalogs/monster-bestiary.md` | Monster names, class records, traits, rewards, and combat behaviour tables. |
| `systems/u4-transfer.md` | Transfer seed filenames, media labels, and the `PARTY.SAV` source-save filename. |

The intro, endgame, item catalog, LOOK data, and shop-data specs also cite
DATA.OVL where they consume resident labels or lookup tables. Display-driver
ABI details remain outside the v1 gameplay spec except where they affect public
asset decoding.

## 8. Implementation Guidance

For a modern engine, do not load DATA.OVL as one opaque memory blob unless the
goal is strict DOS-binary compatibility. Prefer named resources:

- `CommonWordDictionary`
- `WorldLocationTable`
- `LocationEntryYTable`
- `LocationFloorBaseTable`
- `BritanniaChunkIndex`
- `ShrineTable`
- `TilePassability`
- `ViewportDistanceTable`
- `SpellMetadata`
- `ItemMetadata`
- `CombatClassTable`
- `CombatAmbushRevealTable`
- `TextWindowState`
- `InputRuntimeState`
- `KeyboardTranslationTable`
- `IntroStoryPresentationTable`
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

## 9. Cleanroom Boundaries And Delegated Table Work

- Byte-exact DATA.OVL offsets are intentionally omitted. They remain private to
  `u5-decomp`.
- This spec does not reproduce resident string dumps. It names categories and
  consumers only.
- Several compact numeric table families are only broadly identified:
  item/equipment records, remaining unnamed class-flag fields outside the
  published combat traits, dungeon/encounter records, and intro/story
  presentation records. The combat-class stat row schema is named, but not
  every per-row value is reproduced in this format spec.
- Per-spell recipe masks and scene allow masks are now transcribed in
  `catalogs/spell-list.md`. Remaining unidentified numeric table families are
  outside the spell metadata block.
- The squared-distance lookup used by fog refinement is identified. Combat
  target scoring is a separate computed range path. The visibility tile
  predicate's public tile identities are named in `systems/visibility.md`; only
  the caller-flag semantics remain open.
- The underworld map-index story is still provisional: current public specs
  treat `UNDER.DAT` as dense unless further analysis proves a resident
  underworld index is used.
- Some runtime scratch bytes are saved only because the original engine writes
  a flat memory slice. Their semantic importance after load varies by mode and
  is documented in the relevant system specs.

## 10. Sources

This is a cleanroom prose rewrite derived from the private resident-data
dissection in `u5-decomp/formats/data-ovl.md`, cross-checked against the public
specs listed in Section 7. The shared coordinate-scratch boundary was
cross-checked against
`u5-decomp/functions/OUTSUBS_OVL/0x01B4_outsubs_load_4chunks.md`,
`u5-decomp/functions/TOWN_OVL/0x0408_town_setup_load_map.md`, and
`u5-decomp/functions/ULTIMA_EXE/0x70A6_moongate_or_event.md`.
Moon sky-strip table ownership was cross-checked against
`u5-decomp/functions/ULTIMA_EXE/0x4A84_combat_status_grid.md`.
Intro/story presentation metadata ownership was cross-checked against
`u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
Viewport-buffer semantics were cross-checked against
`u5-decomp/functions/ULTIMA_EXE/0x5394_fog_post_pass.md`. Combat class-table
semantics were cross-checked against
`u5-decomp/functions/COMBAT_OVL/0x1574_narrate_status_change.md`,
`u5-decomp/functions/COMBAT_OVL/0x12B0_attacker_defender_score.md`,
`u5-decomp/functions/COMBAT_OVL/0x0D30_target_picker.md`, and
`u5-decomp/functions/COMSUBS_OVL/0x00F4_monster_special_ability_tick.md`.
Ambush/camp reveal-table shape was cross-checked against
`u5-decomp/functions/COMBAT_OVL/0x111A_reveal_ambush_at_coord.md`.
The removal of the old class-script-table hypothesis was cross-checked against
the corrected COMSUBS actor-name and monster-special notes plus the COMBAT
actor-dispatch, target-picker, and movement notes. Combat cast target mapping
was cross-checked against
`u5-decomp/functions/COMSUBS_OVL/0x09FC_check_spell_prereqs.md`. Input runtime
state was cross-checked against
`u5-decomp/functions/ULTIMA_EXE/0x266C_get_command.md`,
`u5-decomp/functions/ULTIMA_EXE/0x1B38_poll_with_blink_cursor.md`, and
`u5-decomp/functions/ULTIMA_EXE/0x1D5E_keyboard_poll.md`. It omits decompiled
code, assembly, private offsets, raw address tables, and copied string dumps.

For byte-compatible offsets and unresolved raw table boundaries, work in
`u5-decomp` and cite only the resulting semantic finding here.
