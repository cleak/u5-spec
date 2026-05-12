# Next Steps for u5-spec

A durable handoff document for resuming specification work. Updated after each meaningful chunk of progress.

**Last updated:** 2026-05-11 - Active-target attack-wrapper damage math, Polymorph Giant Rat replacement, Tremor exact damage/reward formula and actor-scan behavior, shared active-effect tag/counter values, high-circle spell handler details, spell handler-family mapping, directed spell target-walk duplicate/prefilter cleanup, combat default drop-marker byte cleanup, intro story rectangle-transition contract, intro story rectangle helper boundary, shrine meditation state-machine cleanup, intro story-step transition/draw mapping, intro title tick/menu idle contract, intro title tick destination/source ownership, vehicles/ship-fire spec, containers/pickups spec, command routing cleanup, input idle-redraw timing cleanup, active-object idle animator placement, input blink/key mapping cleanup, text-output control/gate cleanup, visibility viewport-buffer cleanup, dungeon entry/data-record order, dungeon trap/pit subtype cleanup, magic field-placement byte cleanup, lighting counter duration cleanup, display rendering contract, spell parser correction, location floor-page rules, MISCMAPS record/trailer cleanup, MISCMAPS Return-to-View stream binding, MISCMAPS Return-to-View command table, MISCMAPS Return-to-View helper schedule, NPC chair-search marker IDs, OOL save-staging/mirror correction, OOL lifecycle cross-reference cleanup, U4 transfer source filename cleanup, directed spell target-walk friendly-fire boundary cleanup, combat active-object restore/loot-reconciliation boundary cleanup, combat reward-unit caller-propagation cleanup, combat descriptor-vs-active-object byte cleanup, dungeon active-object boundary cleanup, PTH open-question cleanup, save active-object persistence boundary cleanup, NPC schedule-Z unsigned cleanup, vehicle timing state-tag cleanup, save transport/status byte cleanup, and vehicle transport-marker family cleanup added.

**Latest local addendum:** 2026-05-11 - Protection defense bonus, Quickness player-dispatch gate, Mass Charm class-threshold target-selection remap, Negate Magic combat-cast absorption, remaining active-effect gap cleanup, S-Search surface/dungeon semantics, the combat field-contact post-step boundary, the arena-field helper placement/application split, combat field active-object marker contact, non-consuming field contact, combat field-kind mapping, coordinate-lookup slot/flag eligibility, accepted-placement redraw/lifetime non-ownership, combat field lifetime until combat exit, Poison/Sleep field-contact status gates, Fire/Energy field damage inputs, directed wind/sleep friendly-fire behavior, monster combat-AI boundary cleanup, monster death-flag asset verification cleanup, time/light-scale endpoint cleanup, dawn/dusk gradient and personal-light floor correction, saved wind-byte preservation, Rel Hur wind-transition boundary cleanup, natural-moongate hour-hook boundary cleanup, overlay dispatch and low-level call wording cleanup, save-file runtime-address cleanup, saved-scene scratch byte layout cleanup, `EXTRACTION.md` partial-row gap summaries, spell-list open-work cleanup, cleanroom provenance wording, source-provenance boilerplate cleanup, manifest-reference audit cleanup, stale encounter arena-reference cleanup, source-like layout-fence cleanup, shared runtime countdown cleanup, karma non-shrine action hypothesis cleanup, KARMA.DAT standing terminology cleanup, X-it escape-helper routing cleanup, magic-lock spell-name cleanup, NPC cached-waypoint/stuck-threshold cleanup, conversation keyword-match/table-scan cleanup, and chargen duplicate-pair/STR-floor/loser-delta cleanup added.

**Current shop/save cleanup:** 2026-05-07 - `SHOPPE.DAT` NUL-terminator/token-range correction, shop inventory bitmap uncertainty cleanup, tavern state-byte wording, sage table-index/boundary cleanup, pending-action state wording, reagent availability boundary, inn registry shifted-view ownership, inn marker/clear/death-source behavior, and inn month-counter billing added.

**Current horse/ship broker cleanup:** 2026-05-07 - superseded by the later shop-dispatch and shipwright-sale cleanups: horse-trader purchase is now Talk-entered and places a horse object, the ship-broker Talk trigger is identified, and shipwright payment is traced into overworld active-object placement with Frigate/Skiff payload semantics and duplicate-purchase handling.

**Current combat spell-prereq cleanup:** 2026-05-11 - combat, magic, and DATA.OVL docs now correct the C-Cast pre-gate as an adjacent-target interference check: a mapped valid visible/awake adjacent target prints `<name> interferes!` and aborts before the spell prompt, while resource gates remain in the shared dispatcher.

**Current SJOG/Jimmy cleanup:** 2026-05-07 - command, door, and DATA.OVL docs now narrow failed NPC-pickpocket consequences, distinguish key-consuming door/chest failures from the NPC pocket failure path, and publish the S/J/O/G tile-redraw versus inventory/status dirty-hint split.

**Current SJOG/Get cleanup:** 2026-05-07 - command and container docs now document Get's accepted pickup-slot filter shape, skipped non-pickup object rows, and tile-consumable redraw/inventory side effects while leaving the exact inventory-add code map open.

**Current SJOG/Open cleanup:** 2026-05-07 - command, door, and container docs now separate Open's already-open, too-heavy, locked, openable, and chest-helper fallthrough outcomes, and narrow guarded/plot override wording to an open metadata question.

**Current SJOG/Search cleanup:** 2026-05-07 - command and container docs now clarify Search result ownership: object-table/treasure results feed inventory, ordinary feature hits narrate, and hidden-door, bomb-trap, chest, or treasure fallbacks own the live-tile/inventory side effects.

**Current DNGLOOK cleanup:** 2026-05-07 - dungeon-mode docs now clarify that fountain drinking is the only identified state-mutating L-Look class, and that V-View uses a centered scratch flood map with row queues before clearing/restoring the side-panel view.

**Current LOOKOBJ cleanup:** 2026-05-07 - world/town Look docs now separate active-object overlay-marker resolution, special Look handler bypasses, and `LOOK2.DAT` base-description cases that append clock, shrine, or dungeon-entrance context.

**Current combat AI staging cleanup:** 2026-05-11 - combat and monster-bestiary docs now publish the class-flag monster special hook: possess, blink/phase, and summon-daemon branch semantics, with the v1 baseline assigning only possess to Blackthorn, Gazer, Wisp, Daemon, and Shadow Lord.

**Current K-Klimb cleanup:** 2026-05-07 - doors/Z-transition docs now publish the outdoor Klimb per-living-member 1..30 stat roll and 1..5 fall-damage roll while keeping the gear byte and stat identity open.

**Current M-Mix cleanup:** 2026-05-07 - magic and item docs now publish the owned-reagent-only selection list, selection/toggle/finish/cancel controls, and two-digit quantity prompt with zero-cancel behavior before inventory change.

**Current B-Board cleanup:** 2026-05-07 - vehicle docs now narrow the immediate dungeon refusal to the stock dungeon scene range and separate handled boardable-family refusals from the non-boardable `What?` no-action fallthrough.

**Current healer cleanup:** 2026-05-07 - shop docs now document the healer/sanctum yes/no entry, C/H/R/exit menu, post-selection condition checks, ordinary paid cure/heal/resurrection costs, The Healers Mission Cure/Heal no-price branch, and resurrection-to-maximum-HP effect.

**Current reagent-shop cleanup:** 2026-05-07 - herbalist menus now document the resident price/availability matrix: zero entries are omitted from the compact letter menu, nonzero entries are purchasable per-ounce prices, and the stale unavailable-reagent open question is removed.

**Current sage cleanup:** 2026-05-07 - sage rumours now document the fixed twenty-six-topic list model, per-topic fee, subject/destination substitutions, random rumour-template selection, remove the stale karma-quality claim, and close the live-input boundary rule: a matched topic must be followed by input end or a space.

**Current shipwright sale cleanup:** 2026-05-07 - supersedes the earlier commodity-shop wording: the shared outdoor pending-action state belongs to the shipwright sale flow, not a separate commodity-shop trigger, and overworld entry consumes it into a placed watercraft active object. Frigate purchases create a full-hull ship with two skiffs, standalone Skiff purchases create a skiff, Skiff purchases before Frigate delivery increment the queued ship's skiff count, second standalone Skiffs are refused, and second Frigate attempts do not alter the pending delivery.

**Current runtime countdown cadence cleanup:** 2026-05-11 - magic, combat, spell-list, and extraction docs now separate the shared active-effect/runtime tag counter from clock/light cleanup: zero and 255 are inert, other values decrement at reached command/combat cleanup endpoints, expiry clears the tag and requests redraw, and Time Stop is the explicit `T`/10 user whose active tag suppresses minute advancement.

**Current arms-shop pricing cleanup:** 2026-05-07 - arms buy-side pricing now documents the canonical equipment-price plus speaking-member Intelligence rule, corrects purchase inventory writes to shared counters, narrows the Talk context wording, aligns karma cross-references, and closes the `B` stock-table mapping as direct equipment item ids.

**Current arms S-menu cleanup:** 2026-05-07 - the arms `S` menu is restored as party-to-shop sell-back: it scans nonzero carried equipment counters, refuses unsellable rows and used ammunition, applies its own Intelligence-based offer formula, adds gold, and decrements the sold counter.

**Current inn-registry cleanup:** 2026-05-07 - shop/save/time docs now publish the inn registry's leading scene-marker match, no/one/multiple guest selection behavior, zero clear marker, leave-time stay-counter reset, pickup billing's stored-counter minimum, month-rollover counter increment capped at 25, and stored-status death conversion.

**Current extraction shop-gap sync:** 2026-05-07 - `EXTRACTION.md` now reflects the narrowed shop gaps: healer/sanctum flow, inn marker/clear/death-source/month-counter behavior, arms `B` stock-table indexing, arms `S` sell-back behavior, shop dispatch, and shipwright placement/payload/duplicate-purchase semantics are covered.

**Current healer scene-label cleanup:** 2026-05-07 - healer docs now tie the Cure/Heal no-price branch to the public Minoc town scene and the shipped shop display name `The Healers Mission`.

**Current shop-dispatch cleanup:** 2026-05-07 - shop/conversation/TLK/NPC/vehicle docs now identify Talk-entry shop dispatch outside the normal `.TLK` keyword-response path, shipped `.NPC` shop-trigger bytes, shared caller context, current shop-instance setup, mounted-horse ordinary-shop refusal, horse-trader Talk purchase that places a horse object, shipwright Talk sale trigger, and the overworld active-object placement/payload handoff; remaining vehicle-sale gaps are numeric vehicle-marker tables rather than shop dispatch.

**Current cleanroom wording cleanup:** 2026-05-07 - shop overlay dispatch wording, door/NPC occupancy marker wording, remaining routing phrasing, loop setup labels, input nested-prompt wording, and visibility row-buffer wording cleaned up to avoid source-like implementation terms.

**Current monster-AI cleanup:** 2026-05-11 - public combat/magic/DATA.OVL wording now replaces the stale general runner gap with the bounded class-flag special hook and ordinary target/direction/command synthesis; remaining AI work is helper labels and edge cases, not class-state field semantics.

**Current chargen cleanup:** 2026-05-07 - chargen persistence wording now separates canonical `SAVED.OOL` interpretation from the still-unverified writer scratch order, removes stale questionnaire-class uncertainty, and aligns the transfer summary with the `PARTY.SAV` source path.

**Current weather/save cleanup:** 2026-05-07 - wind-byte wording now separates byte-preservation from the still-open saved-byte-to-label mapping, publishes the DATA.OVL wind-label presentation order, and avoids implying a verified dense enum.

**Current vehicle sail cleanup:** 2026-05-07 - vehicle docs now specify the Y-Yell ship sail branch semantically and the command table points to that contract: hoisted sails use wind control, furled sails use manual handling, X-Xit refuses the under-sail case, and the exact heading/sail byte encoding remains in the transport-table gap.

**Current transport-marker cleanup:** 2026-05-07 - vehicle docs now publish the clean semantic transport-marker families for foot/avatar, mounted horse, carpet, ship, and skiff, while preserving the exact numeric subranges, ship facing/sail encoding, balloon write path, and terrain rules as open compatibility details.

**Current boarding-family cleanup:** 2026-05-07 - B-Board now has public semantic object-family shapes for horse, carpet, skiff, and ship, with the remaining tile-catalog work narrowed to per-sprite ID and variant verification.

**Current ship-boarding cleanup:** 2026-05-07 - ship boarding now documents the broader accepted-state gate and its stock refusal semantically, while leaving the exact accepted numeric marker variants to the transport-marker table.

**Current input function-key cleanup:** 2026-05-07 - input docs now separate the F1-F10 remap block from the resident A-Z dispatcher and avoid assigning untraced menu/save/music meanings to those codes.

**Current DATA.OVL input-table cleanup:** 2026-05-07 - DATA.OVL now publishes the semantic shape of the extended-key translation table: Up/Down pre-translation, Home/End/PgUp/PgDn diagonals, two no-op sentinel entries, and F1-F10 remapping kept separate from the table.

**Current questionnaire cleanup:** 2026-05-07 - `QUESTION.DAT` now publishes the clean virtue-pair-to-record ordinal mapping and removes the stale pair-table transcription gap without exposing private offsets or questionnaire prose.

**Current save/chargen seed cleanup:** 2026-05-07 - `SAVED.GAM` now documents the two leading bytes before the roster, the questionnaire-created Avatar's seed-preserved HP/max HP/experience/level fields, and the narrower remaining equipment-slot mapping gap.

**Current seed inventory cleanup:** 2026-05-07 - fresh `INIT.GAM`/clean `SAVED.GAM` seed values now cover starting supplies, reagent counters, party-size, clock, active-player sentinel, transport marker, wind byte preservation, and Iolo's Hut scene tuple without publishing raw seed bytes.

**Current save I/O primitive cleanup:** 2026-05-07 - save/load now documents the resident read/write primitive edges: optional absolute seek, zero-count read default, create-or-truncate overwrite semantics, zero-on-error retry signals, ignored close-time failures, and nonzero short-read/short-write compatibility edges without exposing implementation text.

**Current FLAMES ownership cleanup:** 2026-05-07 - animation and extraction docs now clarify that `FLAMES.OVL` is not a gameplay/title flame animator; its public role is screen-preservation scratch for the font/Return-to-View path, while title idle animation is display-driver-owned.

**Current combat target-picker cleanup:** 2026-05-07 - combat, magic, and monster-bestiary docs now publish the target-picker's separate phase/hidden suppression filter, ordinary invisibility filter, first-five-party-slot fallback guard, centre fallback, pending-action marker behavior, and monster-spell separation from the party C-Cast dispatcher.

**Current combat fleeing cleanup:** 2026-05-11 - combat, spell-list, monster-bestiary, and extraction docs now reconcile Cause Fear as the confirmed public fleeing-flag writer while narrowing the remaining flee gap to non-Cause-Fear writers such as morale or non-hook class decisions; the decoded possess/blink/summon-daemon hook does not set flee.

**Current combat command-dispatch cleanup:** 2026-05-11 - combat and extraction docs now clarify that the dispatcher-level combat command map is complete for all twenty-six letters plus seven special inputs; most delegated overlay targets are named (SJOG Get/Jimmy/Open/Search/Klimb, CMDS X-it/Yell/Push, ZSTATS Ready/Z-stats), and combat X-it is distinguished from out-of-bounds fleeing. Remaining command work is the exact CAST continuation and item effects reached by combat U-Use, P-Push combat-scene edge cases, and shared command-family edge cases.

**Current monster AI state cleanup:** 2026-05-11 - combat, magic, DATA.OVL, spell-list, monster-bestiary, and extraction docs now remove the older class-scoped AI-storage interpretation. Slot-local facts stay in the combat actor/effect tables; ordinary AI is target selection, step-vector synthesis, optional movement/teleport helpers, and shared command-parser reuse.

**Current inventory/R-Ready cleanup:** 2026-05-11 - `systems/inventory.md`, save-format, item-list, command, DATA.OVL, and extraction docs now publish the ZSTATS/R-Ready equipment contract: six equipment-slot order, `0xFF` empty sentinel, equipment id reuse across shops/counters/readied slots, R-Ready picker filtering, hand-occupancy gates, combat armour lock boundary, and accepted-equip counter mutation. Remaining item exactness is class-table values, ring vanish details, and combat-time ready parity outside the confirmed armour lock.

## Repository status

- **Branch:** `master` (private — to be flipped public once content is ready)
- **Latest spec commit:** `bdf28bc Correct Lord British castle binding`
- **Uncommitted local update:** current `EXTRACTION.md` inventory rewrite, stale cross-reference cleanup, raw byte-example removal, `.PCS`/compressed-`.BIT` LZW format recovery, single-image `.BIT` marker-word verification, sprite-mask polarity verification, title bitmap/path placement recovery, intro title/menu idle contract, intro title tick destination/source ownership, intro story-step transition/draw mapping, intro story rectangle-transition contract, intro story rectangle helper boundary, input idle-redraw timing cleanup, active-object idle animator placement, input blink/key mapping cleanup, text-output control/gate cleanup, visibility viewport-buffer cleanup, public display/rendering contract, engine-aligned spell token/incantation/recipe/scene-mask table cleanup, exact compact spell parser acceptance rules, magic field-placement byte mapping, spell handler-family mapping, active-target attack-wrapper damage math, directed spell target-walk duplicate/prefilter cleanup, Tremor exact damage/reward formula and actor-scan behavior, Polymorph Giant Rat replacement, shared active-effect tag/counter values, high-circle spell handler details, shrine meditation state-machine cleanup, torch/light-spell duration mapping, time/light-scale endpoint cleanup, dawn/dusk gradient and personal-light floor correction, exact town-location marker/daytime rewrite rules, signed floor-page selection for named locations, default town-entry Y table semantics, DATA.OVL world-location scene/name binding, overworld E-Enter handoff semantics, dungeon scene/name/`DUNGEON.DAT` record binding, exact dungeon fall/bomb trap subtype behaviour, vehicle/ship-fire command extraction, MISCMAPS record/trailer cleanup, MISCMAPS Return-to-View stream binding, MISCMAPS Return-to-View command table, MISCMAPS Return-to-View helper schedule, NPC chair-search marker IDs, combat default drop-marker byte cleanup, monster death-flag asset verification cleanup, OOL save-staging/mirror correction, OOL lifecycle cross-reference cleanup, U4 transfer `PARTY.SAV` source filename cleanup, directed spell target-walk friendly-fire boundary cleanup, combat active-object restore/loot-reconciliation boundary cleanup, combat reward-unit caller-propagation cleanup, combat descriptor-vs-active-object byte cleanup, dungeon active-object boundary cleanup, PTH open-question cleanup, save active-object persistence boundary cleanup, NPC schedule-Z unsigned cleanup, vehicle timing state-tag cleanup, save transport/status byte cleanup, saved wind-byte preservation, Rel Hur wind-transition boundary cleanup, natural-moongate hour-hook boundary cleanup, overlay dispatch and low-level call wording cleanup, save-file runtime-address cleanup, saved-scene scratch byte layout cleanup, source-provenance boilerplate cleanup, shared runtime countdown cleanup, karma non-shrine action hypothesis cleanup, KARMA.DAT standing terminology cleanup, X-it escape-helper routing cleanup, magic-lock spell-name cleanup, NPC cached-waypoint/stuck-threshold cleanup, conversation keyword-match/table-scan cleanup, chargen duplicate-pair/STR-floor/loser-delta cleanup, questionnaire pair-to-record mapping cleanup, save/chargen seed-field cleanup, and fresh seed inventory/location cleanup.
- **Previous priority commits:** `015430e Add endgame and world data specs`; `8665799 Add intro and priority catalog specs`
- **Push target:** `https://github.com/cleak/u5-spec`

### What is done

- README documenting purpose, structure, and specification style guidelines.
- [`EXTRACTION.md`](EXTRACTION.md) — master inventory derived from the actual GOG release file listing. Catalogs every code module, data file, algorithm, and cross-cutting reference table the engine will need to reproduce.
- 64 cleanroom spec docs: 32 system specs, 25 format specs, and 7 catalogs.
- `EXTRACTION.md` now reflects the current v1 status in ASCII status terms rather than the stale first-pass emoji checklist.
- Major game-mode and first-playable systems are covered: launcher/startup, main loop, commands, input, text, save/load, overworld, town mode, dungeon mode, combat, visibility, time, magic, karma, doors/Z transitions, vehicles/ship fire, containers/pickups, active objects, animation, shops, NPC schedules, encounters, conversation, intro, endgame, lighting, weather, and U4 transfer.
- Recent additions: `systems/inventory.md`, `systems/display-driver-abi.md`,
  `systems/vehicles.md`, `systems/containers.md`, `systems/commands.md`,
  `systems/launcher.md`, `systems/animation.md`, `systems/display-driver.md`,
  `formats/font-ch.md`, `formats/font-hcs.md`, `formats/font-pcs.md`,
  `formats/bit.md`, `formats/look2-dat.md`, `formats/signs-dat.md`,
  `formats/question-dat.md`, `formats/karma-dat.md`, `formats/story-dat.md`,
  `formats/endmsg-dat.md`, `formats/miscmsg-dat.md`,
  `formats/shoppe-dat.md`, `formats/end-dat.md`, `catalogs/gazetteer.md`,
  and `catalogs/quest-graph.md`.
- Local verification separates paired LZW graphics archives from the
  driver-compressed sparse-strip resources. The `.16`/`.4` family remains the
  LZW archive family; `PROPORT.PCS`, `TITLE.BIT`, `BRITISH.BIT`, and `WD.BIT`
  are not LZW resources in the current display-driver model.

### Remaining high-value gaps

- Non-optional Priority A prose docs are now covered for the analyzed DOS baseline.
- The EGA display-driver ABI and driver-compressed sparse strip resource family
  for `PROPORT.PCS`, `TITLE.BIT`, `BRITISH.BIT`, and `WD.BIT` are now
  specified, replacing the older shared-LZW hypothesis for those files. The
  EGA baseline now covers the back-buffer plane layout, front-buffer-only
  tile/glyph entries, compressed-bitmap pointer-table over-allocation, title
  tick strip, tile-shimmer source mutation, and dissolve final-pixel contract.
  Text output now documents the `0xFD`/`0xFE` inverse/underline controls and
  the `0xFF` clear-active-window path. Fixed
  title/menu idle ticking, `BRITISH.PTH` pen origins, intro story-step
  transition/draw mapping, intro story rectangle-transition region/order and
  helper handoff, Return-to-View `MISCMAPS.DAT` stream ownership, command
  table, helper-effect schedule, and the public display/rendering contract are
  now specified. Remaining exact visual parity gaps are the story
  rectangle-transition resident helper wipe curve, Return-to-View resident
  helper raster/pacing internals, alternate-driver conversion details, and the
  already-called-out per-table semantic enumerations. `.XMI` music is not
  present in the analyzed clean DOS baseline; add it only for a different
  audio-enabled distribution.
- The spell table is now aligned to the resident incantation order (`In Lor`, `Grav Por`, ...), with all 48 parser tokens, parser acceptance rules, recipe masks, scene masks, light-spell durations, the 99-charge mix cap, major CAST handler families, active-target attack-wrapper damage math for Magic Missile/Fireball/Kill, Tremor exact damage/reward and no-faction-filter actor scan, shared active-effect tag/counter values and expiry behavior, Time Stop `T`/10 countdown semantics, combat C-Cast adjacent-target interference gating, Protection's active-effect defense bonus, Quickness's player-dispatch random gate, Mass Charm's class-threshold target-selection remap, Negate Magic's combat-cast absorption path, Charm/Polymorph/Clone/Fear/Gate/Time Stop high-circle handler semantics, Polymorph's Giant Rat replacement, Clone's paired-slot allocation, random legal arena placement, no-partial-copy capacity failure, undefined original capacity result, shrine-meditation linkage to Avatar intelligence, dungeon field no-write failure, the combat post-step boundary for field/hazard contact, the arena-field helper placement/application split, combat field-kind bytes, coordinate-lookup slot/flag eligibility, active-object marker contact for placed combat fields, non-consuming field contact, accepted-placement redraw/lifetime non-ownership, combat field lifetime until combat exit, no friend/foe gate in the shared field-contact scan, Poison/Sleep field-contact status gates, Fire Field raw 1..21 damage before defense, Energy Field raw zero damage/value input, directed In Zu/Poison Wind/Death Wind/Flame Wind target-walk friendly-fire behavior, and monster possess/blink/summon-daemon hook separation documented semantically. Remaining magic parity gap is indoor absorption state naming, not the forty-eight-entry player spell table, ordinary combat AI, or the equipment counter band now covered in `systems/inventory.md`.
- The first verification slice now runs in `..\u5-engine` against local game
  data and logs corrections. The first run bound Lord British's castle evidence
  to `CASTLE:0` and corrected the older "fifth castle slot" wording.

### V1 deferrals

The long-running open questions below are explicitly deferred to follow-up
implementation/parity work. They are useful next investigations, but they no
longer block the first cleanroom spec release: the non-optional prose inventory
exists, the first verification slice runs, and the remaining exactness gaps are
called out where they matter.

## Locations

### Sibling repositories

| Repo | Path | Role |
|------|------|------|
| u5-decomp | `..\u5-decomp` (`C:\Projects\Rust\u5-decomp`) | Private analysis workspace. Specs may cite note paths as provenance, but must not copy source, assembly, decompiler output, raw dumps, or private implementation text. |
| ninth-virtue | `..\ninth-virtue` (`C:\Projects\Rust\ninth-virtue`) | Private companion-app analysis reference for `ULTIMA.EXE`. Treated as a starting reference; material there must be re-derived in this repo's own words. |

### External resources

This repo deliberately has no external dependencies. Specs are written from private analysis work that happens in `..\u5-decomp`. Game files are not needed here.

### Repo layout (current)

```text
u5-spec/
|-- README.md
|-- NEXT-STEPS.md       # this file
|-- EXTRACTION.md       # master inventory of everything to be specified
|-- systems/            # coherent gameplay systems
|-- formats/            # data file formats
`-- catalogs/           # cross-cutting reference tables
```

## Specification style (reiterated from README)

- **Implementation-agnostic.** Describe what is true about the original; do not prescribe Rust types or memory layouts for the engine.
- **Complete.** Every number has a range and unit; every state transition has every condition.
- **Self-contained.** Readable cold by someone who has not seen the game or its code.
- **Sourced.** Every nontrivial claim names semantic evidence such as a private analysis note, a public asset/file-format observation, or an empirical verification result. When derived from `..\u5-decomp`, cite the analysis note or file that was analyzed without reproducing decompiled code, assembly, raw bytes, or private address tables.

## Recommended next session

Continue with one of these narrow batches:

- If exact original-asset visual parity becomes the next target, trace or capture the resident/display helper invoked for the story step-1 rectangle transition, then update `systems/intro.md` and `systems/display-driver.md` as needed.
- If Return-to-View visual parity becomes the next target, trace the resident special actor draw, local cell-effect raster, and short fixed wait helpers or capture their output, then update `formats/location-dat.md`, `systems/intro.md`, and `systems/display-driver.md` as needed.
- If audio/music asset compatibility for a different distribution becomes in scope, add a future XMIDI format spec from primary XMIDI/Miles documentation or a fresh local asset dissection.
- Extend the `..\u5-engine` verification slice from its current
  data-loading/render-hash/pathfinding/door/conversation smoke test into an
  interactive first-playable room loop if exact movement and conversation
  parity becomes required.
- Analyze non-load-bearing EGA helper slots or alternate display drivers only if historical hardware parity becomes a required public target.
- If combat parity becomes the next target, continue with ordinary AI helper labels, caller-side reward/loot consumers and tables, the exact CAST continuation and item effects reached by combat U-Use, P-Push combat-scene edge cases, and shared command-family edge cases. If inventory parity becomes the next target, continue with equipment class-table values, ring vanish details, and combat-time ready edges outside the confirmed armour lock.

## Long-running open questions

Tracked so they don't get lost:

1. **Hybrid prose-and-tables** vs. pure prose. Probably hybrid: prose for behavior, tables for layouts. Decide once the first format spec is written.
2. **Versioning baseline.** Ultima V had multiple releases (Apple II, C64, Amiga, IBM PC, with patches). Default baseline tag: "IBM PC EGA / Origin v1.x". Note version-specific behavior even if we never plan to support other versions.
3. **In-game vs. generic naming.** Use Ultima V's in-game names ("Britannia", "Lord British", "the Codex"). This is documentation of a specific game, not a generic CRPG engine.
4. **License flip timing.** Repo is private until content is ready. README declares CC-BY-4.0 license intent for spec prose. Decide when to publish — probably after the first system + format spec are complete and the style settles.
