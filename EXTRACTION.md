# Ultima V Extraction Inventory

Master tracking checklist for the cleanroom specification phase. This file maps
the original DOS/GOG asset and code inventory to the public specification docs
in this repository.

Last updated: 2026-05-07.

## Status Legend

| Status | Meaning |
|--------|---------|
| Complete | Covered by cleanroom prose in this repository at v1 depth. |
| Verified slice | Covered by cleanroom prose and exercised by the first playable verification slice. |
| Partial | Covered enough for v1 orientation, with visible parity details still called out in the doc. |
| Deferred | Intentionally outside the v1 visible-MVP spec or waiting on more reverse engineering. |
| Out of scope | Original DOS/runtime implementation detail that a modern engine is not expected to reproduce. |

## V1 Baseline

The v1 visible-MVP baseline covers the IBM PC DOS gameplay contract: startup,
intro, character creation, save/load, overworld, town interiors, dungeon mode,
combat, conversation, NPC schedules/pathfinding, shops, time, visibility,
lighting, weather, karma, magic, vehicles, active objects, animation, endgame,
and the primary asset/data formats needed by those systems.

The public spec set currently contains:

- 30 system specs in `systems/`.
- 25 file-format specs in `formats/`.
- 7 cross-cutting catalogs in `catalogs/`.

The specs are cleanroom prose. They may cite private analysis notes by path, but
they must not include source code, assembly excerpts, copied decompiler output,
or raw copyrighted data dumps.

## Known V1 Deferrals

These items are intentionally not treated as blockers for the v1 visible-MVP
baseline, but they remain important for exact parity:

- Exact binary display-driver ABI and hardware page-flip behaviour (`EGA.DRV`).
  The public v1 rendering contract is covered in `systems/display-driver.md`.
- Music/audio playback for distributions that ship external music resources.
  The analyzed clean DOS baseline at `C:\Games\U5-Clean` contains no `.XMI`
  files, so XMIDI is not a v1 asset-format requirement for this baseline.
- Exact CGA/Hercules/Tandy rendering differences.
- Return-to-View resident helper internals in `MISCMAPS.DAT`. The cutscene
  maps, Return-to-View map strips, section-C runtime owner, 655-byte command
  stream command/argument table, effect step loops, fixed rectangle sequence,
  and preview tick counts are specified; the remaining gap is the low-level
  display helper implementation behind special actor draws, local cell-effect
  rastering, and the short fixed wait.
- Several per-table enumerations called out in their docs: full tile-id
  verification, remaining monster class metadata and AI state fields/effect
  selectors, some NPC type/AI-byte names (chair-search marker IDs are fixed),
  the monster combat-AI runner instruction set and class effect map, non-light
  active-effect helper body and Time Stop decrement path, combat reward/loot
  handoff (temporary drop-marker
  shape and Tremor's spell-side reward consumer are fixed), and a few
  combat metadata bits.

## 1. Code Modules

The public specs are organized by behavior rather than by binary module. A
single overlay may feed several specs, and a single spec may combine resident
and overlay behavior.

### Resident Core

| File | Role | Status | Spec docs |
|------|------|--------|-----------|
| `ULTIMA.EXE` | Main loop, command dispatch, text I/O, active objects, visibility, overlay loading, combat framing, save/load helpers, display dispatch contract | Complete | `systems/main-loop.md`, `systems/commands.md`, `systems/input.md`, `systems/text-output.md`, `systems/active-objects.md`, `systems/visibility.md`, `systems/time.md`, `systems/save-load.md`, `systems/display-driver.md`, `formats/data-ovl.md` |
| `ULTIMA5.COM` | Legacy launcher assumption | Complete | `systems/launcher.md` documents that the analyzed clean DOS baseline starts from `ULTIMA.EXE`; no canonical `ULTIMA5.COM` launcher is required for v1. |

### Game-Mode And Feature Overlays

| File | Role | Status | Spec docs |
|------|------|--------|-----------|
| `MAINOUT.OVL` | Outdoor/underworld loop and per-turn epilogue | Verified slice | `systems/overworld.md`, `systems/encounters.md`, `systems/weather.md`, `systems/time.md` |
| `OUTSUBS.OVL` | Outdoor chunking, entry checks, actor/object setup | Verified slice | `systems/overworld.md`, `systems/active-objects.md`, `formats/brit-dat.md`, `formats/under-dat.md` |
| `TOWN.OVL` | Town/keep interior setup and loop | Verified slice | `systems/town-mode.md`, `systems/npc-schedules.md`, `formats/location-dat.md` |
| `DUNGEON.OVL` | First-person dungeon loop | Complete | `systems/dungeon-mode.md`, `formats/dungeon-dat.md` |
| `DNGLOOK.OVL` | Dungeon look/view commands | Complete | `systems/dungeon-mode.md`, `systems/visibility.md` |
| `COMBAT.OVL` | Combat mode, actor rounds, target selection | Complete/partial | `systems/combat.md`, `systems/encounters.md`, `catalogs/monster-bestiary.md`; core loop/framer/death reward unit, target-picker filters/fallback, Gargoyle/Gazer special-death branch assignment, and unassigned vanish branch are covered, while durable reward/loot reconciliation and some metadata bits remain open. |
| `COMSUBS.OVL` | Shared combat/spell helpers | Complete | `systems/combat.md`, `systems/magic.md` |
| `TALK.OVL` | NPC conversation runtime | Verified slice | `systems/conversation.md`, `formats/tlk.md`, `catalogs/quest-graph.md` |
| `NPC.OVL` | NPC runtime state, schedules, pathfinding | Verified slice | `systems/npc-schedules.md`, `formats/npc.md`, `formats/pth.md`, `catalogs/npc-roster.md` |
| `SHOPPES.OVL`, `SHOPPES2.OVL`, `SHOPPES3.OVL` | Guilds, reagents, arms, healer, sage/tavern interactive flows, shipwrights, inn, horse-trader sale, companion pickup/dropoff | Complete/partial | `systems/shops.md`, `formats/shoppe-dat.md`, `catalogs/item-list.md`; core shop flows, text rendering, Talk-entry shop dispatch/caller context, shipped `.NPC` shop-trigger values, karma non-modulation, horse-trader Talk purchase, shipwright Talk sale trigger, shipwright active-object placement handoff, shipwright Frigate/Skiff payload semantics and duplicate-purchase edges, arms `B` buy stock indexing, arms `S` sell-back inventory browser, arms buy/sell Intelligence price formulas, zero-price suppression, reagent compact-menu availability, sage topic/fee/rumour substitution flow and input boundary, shipwright pending-action ownership, and inn registry marker/clear/death-source/month-counter behavior are covered. |
| `INTRO.OVL` | Menu, title, intro slides, saved-game load | Complete | `systems/intro.md`, `systems/launcher.md`, `systems/save-load.md`, `formats/story-dat.md`, `formats/bit.md`, `formats/tiles.md` |
| `ENDGAME.OVL` | Endgame roster load and narrative sequence | Complete | `systems/endgame.md`, `formats/end-dat.md`, `formats/endmsg-dat.md` |
| `FLAMES.OVL` | Screen-preservation scratch helper historically named like a flame overlay | Complete | `systems/animation.md`, `systems/intro.md`; title/menu flame-style animation is display-driver-owned, and this file is not a separate gameplay animation system in v1. |
| `BLCKTHRN.OVL` | Blackthorn audience/rescue/challenge scenes | Complete | `systems/conversation.md`, `systems/karma.md`, `systems/endgame.md`, `catalogs/quest-graph.md` |
| `CMDS.OVL` | A-Z world command handlers | Complete | `systems/main-loop.md`, `systems/commands.md`, `systems/overworld.md`, `systems/town-mode.md`, `systems/doors-and-z-transitions.md`, `systems/vehicles.md`, `systems/magic.md` |
| `SJOG.OVL` | Search/Jimmy/Open/Get command family | Complete | `systems/commands.md`, `systems/containers.md`, `systems/doors-and-z-transitions.md`, `systems/overworld.md`, `systems/town-mode.md`, `systems/dungeon-mode.md`, `catalogs/item-list.md` |
| `ZSTATS.OVL` | Character/inventory status display | Complete | `systems/text-output.md`, `formats/saved-gam.md`, `catalogs/item-list.md`, `catalogs/spell-list.md` |
| `FONT.OVL` | Proportional text and chargen renderer | Complete | `systems/chargen.md`, `systems/text-output.md`, `formats/font-pcs.md` |
| `LOOKOBJ.OVL` | Look-at-object/inspection text | Complete | `systems/conversation.md`, `systems/dungeon-mode.md`, `formats/look2-dat.md`, `catalogs/tile-catalog.md` |
| `CAST.OVL`, `CAST2.OVL` | Spell casting/effects, shrine meditation, save game | Complete/partial | `systems/magic.md`, `systems/karma.md`, `systems/save-load.md`, `catalogs/spell-list.md`; player spell dispatcher order, parser, recipes, scene masks, major handler families, active-target attack-wrapper damage, Tremor's table-wide damage/reward path, Protection/Quickness/Mass Charm/Negate Magic active-effect consumers, Clone's paired-slot capacity behavior, combat field marker/contact/lifetime semantics, Poison/Sleep field-contact status gates, Fire/Energy field damage inputs, and directed wind/sleep friendly-fire behavior are fixed. Remaining magic/combat parity gaps are the monster combat-AI class effect map and exact non-light countdown decrement cadence, not the forty-eight-entry player spell table. |

### Display Drivers

| File | Role | Status | Spec docs |
|------|------|--------|-----------|
| `EGA.DRV` | 16-colour IBM PC display backend | Partial/deferred | Public rendering contract and asset-facing EGA-compatible path are covered by `systems/display-driver.md`, `formats/tiles.md`, `formats/bit.md`, and font specs. Exact binary driver ABI/page-flip behaviour remains deferred. |
| `CGA.DRV`, `HER.DRV`, `T1K.DRV` | Alternate historical display backends | Out of scope | Modern v1 targets EGA-compatible visual assets; alternate hardware parity is deferred/out of scope. |

### Sound, DOS Runtime, And Installer Files

| Files | Role | Status | Notes |
|-------|------|--------|-------|
| Miles/AdLib/Sound Blaster/MT-32/MIDI driver files | Historical audio backend | Out of scope | These files are not present in the analyzed clean DOS baseline. |
| `.XMI` music tracks | XMIDI music resources | Out of scope for this baseline | No `.XMI` files are present in `C:\Games\U5-Clean`; add a future XMIDI format spec only if a different target distribution ships them. |
| Causeway/DOS extender/config/installer files | Runtime and packaging support | Out of scope | Not needed by a modern cleanroom engine. |

## 2. Data Formats

### Maps And Combat Arenas

| File(s) | Contents | Status | Spec doc |
|---------|----------|--------|----------|
| `BRIT.DAT` | Britannia overworld chunks | Verified slice | `formats/brit-dat.md` |
| `UNDER.DAT` | Underworld chunks | Complete | `formats/under-dat.md` |
| `DATA.OVL` | Resident data image, labels, lookup tables, string pools, runtime-state defaults | Complete | `formats/data-ovl.md` |
| `CASTLE.DAT`, `KEEP.DAT`, `TOWNE.DAT`, `DWELLING.DAT` | Location/interior tile grids | Verified slice | `formats/location-dat.md` |
| `MISCMAPS.DAT` | Cutscene maps plus Return-to-View map strips and command stream | Partial | Covered inside `formats/location-dat.md`; section C, stream length, command/argument table, loop rule, actor/map side effects, local cell-effect step loops, fixed rectangle sequence, and preview tick counts are specified. Exact resident display-helper internals remain partial. |
| `DUNGEON.DAT` | Dungeon level grid encoding | Complete | `formats/dungeon-dat.md` |
| `BRIT.CBT`, `DUNGEON.CBT` | Combat arena terrain and metadata | Complete/partial | `formats/cbt.md`; some metadata bytes remain unnamed. |

### NPCs, Schedules, Dialogue

| File(s) | Contents | Status | Spec doc |
|---------|----------|--------|----------|
| `CASTLE.NPC`, `KEEP.NPC`, `TOWNE.NPC`, `DWELLING.NPC` | NPC roster/schedule records | Verified slice | `formats/npc.md`, `systems/npc-schedules.md`, `catalogs/npc-roster.md` |
| `CASTLE.TLK`, `KEEP.TLK`, `TOWNE.TLK`, `DWELLING.TLK` | Keyword-driven dialogue blobs | Verified slice | `formats/tlk.md`, `systems/conversation.md`, `catalogs/quest-graph.md` |
| `BRITISH.PTH` | Path stroke/movement stream | Complete | `formats/pth.md` |

### Text And Lookup Tables

| File | Contents | Status | Spec doc |
|------|----------|--------|----------|
| `LOOK2.DAT` | Tile/look strings | Complete | `formats/look2-dat.md`, `catalogs/tile-catalog.md` |
| `SIGNS.DAT` | Sign/placard text | Complete | `formats/signs-dat.md` |
| `KARMA.DAT` | Karma verdict text | Complete | `formats/karma-dat.md`, `systems/karma.md` |
| `STORY.DAT` | Intro story text | Complete | `formats/story-dat.md`, `systems/intro.md` |
| `QUESTION.DAT` | Character creation questionnaire | Complete | `formats/question-dat.md`, `systems/chargen.md` |
| `ENDMSG.DAT` | Endgame message table | Complete | `formats/endmsg-dat.md`, `systems/endgame.md` |
| `END.DAT` | Endgame narrative text | Complete | `formats/end-dat.md`, `systems/endgame.md` |
| `MISCMSG.DAT` | Miscellaneous message table | Complete | `formats/miscmsg-dat.md` |
| `SHOPPE.DAT` | Shop text, menu, bark, item-description, rumour, and inn-message records; stock and pricing live in resident tables | Complete | `formats/shoppe-dat.md`, `systems/shops.md` |

### Graphics, Fonts, And Bitmaps

| File(s) | Contents | Status | Spec doc |
|---------|----------|--------|----------|
| `TILES.16`, `TILES.4` | Main 512-tile atlas | Verified slice | `formats/tiles.md`, `catalogs/tile-catalog.md` |
| `ULTIMA.*`, `ITEMS.*`, `TEXT.*`, `CREATE.*`, `DNG1.*`, `DNG2.*`, `DNG3.*`, `MON0.*`-`MON7.*`, `STARTSC.*`, `ENDSC.*`, `END1.*`, `END2.*`, `STORY1.*`-`STORY6.*` | Paired `.16`/`.4` graphics archive family | Complete/partial | `formats/tiles.md`; container/pixel encoding is covered, while some per-slot semantic mappings remain catalog work. |
| `IBM.CH`, `RUNES.CH` | 8x8 fixed-cell fonts | Complete | `formats/font-ch.md` |
| `IBM.HCS`, `RUNES.HCS` | 16x12 fixed-cell fonts | Complete | `formats/font-hcs.md` |
| `PROPORT.PCS` | Compressed proportional font | Complete | `formats/font-pcs.md` |
| `TITLE.BIT`, `BRITISH.BIT` | Compressed title/portrait bitmaps | Complete/partial | `formats/bit.md`; LZW codec, decoded bodies, intro placements, title/menu idle ticking, and the story step-1 rectangle-transition handoff are covered, while exact resident helper wipe timing for slide/sub-screen transitions remains a display/intro renderer concern. |
| `WD.BIT` | Raw monochrome title lettering bitmap | Complete | `formats/bit.md` |

### Save And Object State

| File(s) | Contents | Status | Spec doc |
|---------|----------|--------|----------|
| `SAVED.GAM`, `INIT.GAM` | Full save/initial party and world state | Complete/partial | `formats/saved-gam.md`, `systems/save-load.md`, `systems/chargen.md`; core save-image, roster, inventory, clock, location, active-object regions, and inn-registry marker/month-counter behavior are covered, while several third-party-only flag/map regions remain open. |
| `SAVED.OOL`, `INIT.OOL`, `BRIT.OOL`, `UNDER.OOL` | Persistent object/vehicle/NPC overlay layer | Complete/partial | `formats/ool.md`, `systems/active-objects.md`; save-side staging and conditional underworld mirror branch documented, disk-state value names remain open. |

## 3. System Specs

| System | Status | Spec doc |
|--------|--------|----------|
| Launcher/startup | Complete | `systems/launcher.md` |
| Intro/menu/story flow | Complete | `systems/intro.md` |
| Character creation and U4 transfer entry | Complete/partial | `systems/chargen.md`, `systems/u4-transfer.md`; questionnaire stat finalization, fixed Avatar class, seed-preserved HP/experience/level fields, starting counters/reagents/clock/location, abort-before-write behavior, questionnaire pair-to-record mapping, and `PARTY.SAV` transfer source are covered. Remaining parity gaps are seeded equipment and full item/spell/quest-stock enumeration, transfer stat/class/HP/level mapping, object-companion half order, and transfer post-commit UI details. |
| Main loop and command dispatch | Complete | `systems/main-loop.md`, `systems/commands.md` |
| Input pipeline | Complete | `systems/input.md` |
| Display driver/rendering contract | Complete/partial | `systems/display-driver.md`; v1 semantic rendering contract is covered, while exact binary driver ABI and page-flip behaviour remain deferred. |
| Text output/windowing | Complete | `systems/text-output.md` |
| Save/load | Complete/partial | `systems/save-load.md`, `formats/saved-gam.md`; byte-image save/load, `.OOL` companions, mirrors, empty-save guard, inn-registry round-trip behavior, and resident read/write primitive edge cases are covered. Remaining save-format gaps include unverified dungeon-map / NPC-flag region layouts. |
| Overworld/underworld | Verified slice | `systems/overworld.md` |
| Town/interior mode | Verified slice | `systems/town-mode.md` |
| Dungeon mode | Complete | `systems/dungeon-mode.md` |
| Combat | Complete/partial | `systems/combat.md`; core loop, framer, complete dispatcher-level command map, target selection including phase/invisibility filters and no-target fallback, class-script AI dispatch boundary and class-wide live-state ownership, combat C-Cast target mapping/pre-gate boundary, spell field contact, damage/death, Cause Fear flee-setting, and active-effect consumers are covered; Gargoyle/Gazer special deaths and unassigned vanish-branch reachability are separated. Remaining gaps are durable reward/loot reconciliation, delegated combat command branch bodies, unnamed class/metadata bits, non-Cause-Fear flee setters, AI state fields and runner instruction set, combat resource/allowed check body, target-reaction hook effect, and monster special-action/effect mapping. |
| Encounters | Complete/partial | `systems/encounters.md`; random/scripted/dungeon trigger families are covered; remaining gaps are exact random-encounter threshold formula, terrain/arena and monster distribution tables, sleep-ambush details, dungeon chest-trap arena indexing, and post-combat reward reconciliation. |
| Conversation | Verified slice | `systems/conversation.md` |
| NPC schedules/pathfinding | Verified slice | `systems/npc-schedules.md` |
| Doors and Z transitions | Verified slice | `systems/doors-and-z-transitions.md` |
| Containers and pickups | Complete/partial | `systems/containers.md`; command flow, pickup object matching, Moonstone recovery, and broad chest/container behaviour are covered; remaining gaps are dungeon chest reward/trap tables, found-item code mapping, table-food reach rules, and persistence of consumed object entries. |
| Vehicles and ship fire | Complete/partial | `systems/vehicles.md`; boarding/dismounting, ship-fire routing, Y-Yell sail toggling, active-object integration, semantic transport-marker families, boardable object-family shapes, ship boarding precondition boundary, horse-trader Talk purchase placement, ship-broker Talk purchase trigger, shipwright active-object placement handoff, shipwright Frigate/Skiff payload semantics, and save/transport state are covered; remaining gaps are exact numeric marker subranges including ship facing/sail encoding, per-sprite boarding ID verification and accepted ship-marker variants, X-it landing scan, ship durability, and balloon behaviour. |
| Active objects | Complete | `systems/active-objects.md` |
| Visibility | Complete/partial | `systems/visibility.md`; viewport buffer, fog post-pass, light-radius handling, and actor compositing are covered; remaining gaps are exact line-of-sight stepping, blocks-sight tile bitmap, dim-versus-obscured semantics, companion marker encoding, special light inflation, and dungeon visibility encoding. |
| Time/calendar/moons | Complete/partial | `systems/time.md`; minute/hour/day/month advancement, major per-turn callers, timing-tag effects, daylight endpoint/sentinel values, exact dawn/dusk gradient levels, torch/spell personal-light floors, and inn-owned month-counter billing are covered; remaining gaps are the surface hour-event callback body, non-inn interpretation of the per-character month counter, and overflow edges. |
| Lighting | Complete/partial | `systems/lighting.md`; daylight, original light-scale endpoints, exact dawn/dusk gradient levels, torch/spell personal-light floors, torches, light spells, and saturating counter decay are covered; remaining gap is special scene lighting override enumeration. |
| Weather/wind | Complete/partial | `systems/weather.md`; wind presentation states, DATA.OVL label order, saved wind-byte preservation, Wind Change identity, and ship wind cadence are covered; remaining gaps are Rel Hur transition order and calm handling, exact saved-byte-to-label mapping, compass convention naming, and player-ship versus active-object ship path. |
| Animation | Complete | `systems/animation.md` |
| Magic/spells/reagents | Complete/partial | `systems/magic.md`; player spell order, parser, resources, major handler families, combat fields, directed winds, active effects, shrine linkage, monster-spell separation from the party C-Cast dispatcher, and monster AI state ownership are covered; remaining gaps are the monster combat-AI state fields, runner instruction set, and class effect map, indoor absorption state naming, and the non-light active-effect helper body plus Time Stop decrement path. |
| Karma/virtues/shrines | Complete/partial | `systems/karma.md`; virtue order, shrine quest-state machine, confirmed shrine standing changes, offering/stat-reward boundary, and non-shrine action inventory are covered; remaining gaps are exact non-shrine action coverage and delta magnitudes, byte layout, tier thresholds, combat/endgame karma branches, chargen seed, and non-shrine clamp/overflow policy. |
| Shops | Complete/partial | `systems/shops.md`; shop text records, main menu flows, table-driven pricing, Talk-entry shop dispatch and caller context, shipped `.NPC` shop-trigger values, horse-trader Talk purchase and horse-object placement, shipwright Talk sale trigger, shipwright active-object placement handoff, shipwright Frigate/Skiff payload semantics and duplicate-purchase edges, arms `B` stock-table item-id mapping, arms `S` sell-back inventory browser, arms buy/sell Intelligence formulas and zero-price suppression, reagent compact-menu availability, sage topic/fee/rumour substitution flow and input boundary, shipwright pending-action ownership, karma non-modulation, healer/sanctum treatment flow including The Healers Mission no-price Cure/Heal branch, and inn registry marker/clear/death-source/month-counter behavior are covered. |
| Endgame | Complete | `systems/endgame.md` |

## 4. Catalogs

| Catalog | Status | Spec doc |
|---------|--------|----------|
| Tile catalog | Complete/partial | `catalogs/tile-catalog.md`; tile partitions, passability model, look strings, vehicles, fields, and broad sprite families are covered; remaining gaps are per-tile verification for monster/NPC/item frames, marker-byte mapping, blocks-sight metadata, field frame runs, render-only IDs, and partition-boundary verification. |
| NPC roster | Complete/partial | `catalogs/npc-roster.md`; location rosters, schedule summaries, keyword counts, and major named NPCs are covered; remaining gaps are sub-map place names, role tag semantics, AI/mode byte meanings, one punctuation-only name, and full keyword graph integration. |
| Quest graph | Complete/partial | `catalogs/quest-graph.md`; major artifact, word, shard, mantra, social, and endgame dependencies are covered without dialogue text; remaining gaps are full TLK VM branch execution, item-side-effect confirmation, Doom's in-world teaching edge, and reachability of embedded/trailing records. |
| Gazetteer | Complete | `catalogs/gazetteer.md` |
| Spell list | Complete/partial | `catalogs/spell-list.md`; all forty-eight player spells have parser tokens, recipes, scene masks, and broad/fixed handler semantics; remaining gaps are the monster combat-AI runner instruction set/class effect map and the non-light active-effect helper body plus Time Stop decrement path. |
| Item list | Complete/partial | `catalogs/item-list.md`; inventory families, equipment categories, arms-shop equipment item-id mapping, reagents/spell stocks, vehicles, and key quest items are named; remaining gaps are item-to-tile IDs outside the arms-shop equipment mapping, combat values, armour values, restrictions, prices, potion/scroll effects, U-Use dispatch, exact transport-marker numeric subranges and terrain rules, and byte-counter caps. |
| Monster bestiary | Complete/partial | `catalogs/monster-bestiary.md`; class IDs, sprite runs, HP, reward units, drop caps, Mass Charm thresholds, target-picker filter/fallback behaviour, AI class-state ownership, and decoded traits are covered; unsupported vanish traits were removed from the v1 baseline rows after asset-table verification. Remaining gaps are leftover stat/flag fields, vanish-branch variant reachability, AI state fields and runner instruction set, monster special-action/spell-like effect selection, spawn distribution tables, ordinary reward/drop consumers, sprite tile verification, and runtime verification of special deaths. |

## 5. Verification Slice

The first-playable verification slice lives in the sibling implementation
repository (`../u5-engine`) and is summarized in `NEXT-STEPS.md`. It exercises:

- Decoding `TILES.16` and rendering Lord British's throne room from
  `CASTLE.DAT`.
- Basic movement and collision against location tiles.
- Door interaction.
- Clock/NPC schedule sampling for Lord British's castle data.
- Conversation-envelope loading against `CASTLE.TLK`.

The first run corrected a public spec error by binding Lord British's castle to
`CASTLE:0`. Further verification should expand that slice rather than adding
private implementation details to this public spec repository.

## 6. Stop Condition For V1

The v1 visible-MVP spec is considered releasable when:

1. Every non-deferred system, format, and catalog row above has a public
   cleanroom prose document.
2. Every known partial row states its own remaining parity gaps.
3. The first verification slice runs and any resulting public-spec corrections
   are applied here.
4. No spec document contains source code, assembly excerpts, copied decompiler
   output, or raw copyrighted data dumps.

Current assessment: the v1 visible-MVP prose inventory exists, non-deferred
rows point to cleanroom specs, partial rows name their remaining parity gaps,
and the first verification slice has run. Exact-parity work remains in the
declared partial/deferred rows, but those gaps no longer block the first public
cleanroom spec release.
