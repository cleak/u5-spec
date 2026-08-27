# Next Steps for u5-spec

> **Supersession notice — 2026-08-22.** Everything dated 2026-05-xx below is a
> historical log. Where an entry conflicts with the current `systems/`,
> `formats/` or `catalogs/` prose, **the spec docs are authoritative and the log
> entry is superseded.** The 2026-08-22 pass re-derived every contested claim
> from the shipped binaries and withdrew, among others: the per-frame natural
> moongate animator and its "moongate frames" model (gates are ordinary live
> terrain); the tile-`0x59` town exit threshold (that tile is the telescope Look
> trigger); the Saduj roster-name letter rule (it is a shipped-template rule
> keyed to the last roster record, and the letter comparison is not published);
> combat `U`-Use as a label-only abort (it routes into the item-use handler) and
> combat `Q`-Quit as an abandon-party defeat path (it is a plain refusal with no
> save route); the caller-provided Blackthorn death-route marker (entry is the
> town arrest path); and the "arena-keyed" combat spawn count and replacement
> tile (both are keyed to the combat class id). See the closing comments on
> `cleak/u5-spec` issues #1-#77 for the full retraction list.

A durable handoff document for resuming specification work. Updated after each meaningful chunk of progress.

**Retraction convention — 2026-08-26.** Reversals are now tracked in
`RETRACTIONS.md` at the repository root: an append-only, commit-ordered table of
every published statement this repository has withdrawn or inverted, naming the
document, the section, the withdrawn claim and its replacement. Issue #149
asked for it after an audit found that most of the clean engine's 106 missing
contracts were faithful implementations of spec revisions that were later
reversed with no signal. The first backfill publishes 230 rows and carries an
explicit completeness caveat; it is not proven exhaustive.

Two consequences for work in this file. First, the 2026-08-22 supersession
notice above is no longer the only place withdrawn claims are recorded — every
item it lists now has a row in `RETRACTIONS.md` with the affected sections named
individually, and new withdrawals belong there rather than in a fresh prose
notice here. Second, `CLAUDE.md` and `AGENTS.md` now require a `RETRACTIONS.md`
row plus a one-line inline note in the affected section whenever an edit
withdraws or inverts published text, including text published only in an issue
answer.

**Addendum — 2026-08-26, issue #150 and the #146 install-cost follow-up.**
Issue #150's two orphan effects are both attributed and both reachable; neither
was an unreachability finding. The descending two-tone pair is the **combat
command refused as inapplicable** - twelve verbs, every kind of combat scene,
text before sound, no cancellation, no turn cost - and the long descent has
**two** triggers, drowning and whirlpool engagement, which are the only two
users of that recipe in the shipped game (`audio.md` sections 8.8 and 8.9).
Three further headlines. **No sweep ever reaches its nominal target**: the
integer increment is computed once and the loop stops one step short, so the
long descent ends at 272 Hz rather than 150 Hz and a second shipped recipe ends
at 1005 Hz rather than 800 (`audio.md` section 5.2). **The per-tone install cost
and the rumble's per-iteration cost are now published as derived quantities**
(`timing.md` sections 7.4.1 and 7.4.2); the install cost is 17.4 inner units
against the 12 the implementation side fitted, a 45 percent disagreement that
only a cycle-accurate run can settle, and the rumble's cost is **linear in the
step**, so the fitted 53 is right only for the one recipe it was fitted against.
And **the refusal beep is a movement-rejection cue only**: a missed melee or
weapon attack does not produce it (`audio.md` section 7.4). Failed *spell*
attacks were not traced and remain the one gap that could change that answer for
a subset of misses. One reversal was found while confirming where the real
attack roll lives and is filed as `RETRACTIONS.md` R232: the to-hit comparison
in `combat.md` section 11 runs the other way.

**Addendum — 2026-08-26, calibrated-unit delay contexts and wall-clock anchor.**
Issue #146 is answered by `systems/timing.md` sections 6 and 7 and
`systems/audio.md` sections 4, 5.4, and 10. Four of the five questions are
answered; one sub-question is closed as unresolved. Headlines: there is exactly
**one** live delay context and its shift is **zero**, so the selector should be
dropped from any engine interface; one outer calibrated unit is **0.88 ms plus
or minus 10 percent**, a static derivation rather than a measurement; the
software envelope is a **high whistle at about 3.13 kHz**, not a growl, and the
nine variants' pitch ratios are exact even though the absolute scale is banded;
and the two potion viewport inversions are **not derivable from timing analysis
at all** and need a separate pass over the display driver's invert path.

The single highest-value follow-up in this area is now a **cycle-accurate
emulator run that reads the boot calibration value after startup**. It would
collapse most of the band in `timing.md` section 7 in one shot. An audio capture
would settle the envelope carrier outright. Two derived figures are worth
checking in play because they are much longer than they sound: the 26.5-second
Stonegate trapdoor sweep and a 6.9-second long glissando. Two audio effects were
also found that `audio.md` section 8 did not attribute to a trigger; they were
recorded in `audio.md` section 10.6 and filed as issue #150. **Both are now
attributed** - see the issue #150 addendum above - and section 10.6 now records
what is left instead: seven further glissando recipes with no known trigger.

**Addendum — 2026-08-25, PC-speaker effect contract.** Issue #145 is covered
by `systems/audio.md`. The public contract now centralizes the procedural
PC-speaker primitives, calibrated CPU versus BIOS timing, Ctrl-S mute behavior,
sound-only versus gameplay-random jitter, all nine shared potion/wind/spell
envelope rows, and the exact priority boundaries for WD.BIT ignition, accepted
potions, accepted wind changes, and blocked steps. It also inventories the
confirmed trap, spell, dungeon-decoration, theft, ring, summon/possession,
moongate, Stonegate, Return-to-View, and endgame effects and explicitly keeps
ordinary menus, typing, successful movement, generic pickup, and generic
successful commands silent.

## Current state — 2026-08-22

The engine issue queue is empty (ninety-six filed, ninety-six closed). The
spec now carries every contract the clean engine has asked for, including the
intro title/menu sequence, the gameplay screen frame and panel layout, the
per-scene base floor-page table, command echo and dungeon presentation, the
endgame/chargen/transfer geometry, and the light byte as an inclusive
squared-distance threshold.

**What is worth doing next, in order:**

1. **Wait for the engine to file again.** The black-box observations coming from
   the clean side have been the single most productive source of spec defects —
   more productive than re-reading the private notes, because they catch places
   where the spec is confidently wrong rather than merely silent.
2. **Residuals that need a live capture, not more static tracing.** The per-step
   wall-clock of the publisher flourish (published as a calibration-derived
   target, not a measurement); the intro "pale yellow" ink discrepancy, where
   code and shipped palette both say white; and the alternate-depth (CGA and
   Hercules) art paths, published as geometry only and never checked against
   captures.
3. **The remaining open reverse-engineering questions** are catalogued in the
   private analysis workspace at `../u5-decomp/`. The gameplay-visible ones were closed on
   2026-08-22; what is left is presentation parity and dead-code curiosity, none
   of it blocking a port.

**Addendum — 2026-08-23, adversarial re-verification of four engine questions.**
Four traced answers were independently re-derived from the shipped binaries and
published. Two previously published gaps are now **closed**: whether Open clears
a surface/town container's persisted trap flag (it does — the whole container
record is cleared as part of opening, after the handler has copied the flag byte,
so the trap fires once and the square then holds nothing), and which cancel
literal R-Ready prints on Escape (`Done`; `None!` belongs to the shared picker's
other caller). Two published claims were **withdrawn as wrong**: the premise
behind that first gap, and two phrases in `systems/traps.md` § 4 describing the
post-trap combat cleanup as removing a combatant record and blanking a
world-object entry — it flags the record and stamps a constant. Three points were
newly published as explicit gaps rather than left silent: what that stamped
constant denotes, whether anything in the R-Ready subtree advances the clock a
second time, and the vertical placement of the shared coordinate line. Two
existing gaps were re-confirmed under stronger method without being cleared: the
absence of any producer of the Ashes status, and the inertness of the
combat-class scene boundary disagreement. The `R`-costs-a-turn rule and the
Sextant's Underworld refusal both survived challenge unchanged.

**Addendum — 2026-08-24, R-Ready exact clock cost.** Issue #113 closed the
remaining double-charge gap. Every path inside one R-Ready invocation has no
clock call of its own. Overworld and town pay exactly one ordinary post-action
charge (nominally two and one minutes respectively), dungeon pays its single
one-minute loop-head charge, and repeated picker attempts add nothing. The
shared Quickness and Negate Time modifiers still apply to those nominal
increments. Combat Ready spends the live actor's action and adds no
command-specific clock advance; combat's independent one-minute modulo-ten
wrap occurs before actor dispatch and is unaffected by the chosen command.

**Addendum — 2026-08-24, combat overlay raster geometry.** Issue #114 replaced
the provisional cursor-corner and palette-11-plus rendering with the exact
EGA/Tandy-equivalent contract. The combat cursor is the complete white
two-pixel outer ring of its sixteen-by-sixteen cell. The secondary overlay is a
white-and-black twelve-by-twelve stroke pattern with exact inclusive relative
coordinates. `systems/combat.md` now also fixes base/cursor/marker draw order,
shared blink and active-player eligibility, solid replacement rather than XOR,
ordinary display clipping, and erasure by the following base repaint.

**Addendum — 2026-08-24, potion presentation rasters and timing.** Issue #115
replaced three provisional presentation models. Every accepted potion target
first gets a selected-colour, blocking PC-speaker sequence bracketed by paired
palette-mask-15 XOR passes over the complete EGA/Tandy playfield; randomized
effect substitution happens afterward. Orange has no `Z` overlay: combat sleep
selects ordinary tile `0x1E` until the one-in-seventeen scheduled wake path
restores the actor. Purple has no one-frame magenta star: it rewrites both tile
fields of the combat-instance object record to ordinary asset `0x90` with no
timer or Purple-owned restoration. White has no growing disc or white raster:
it computes one inclusive squared-distance-threshold-32 visibility field, then
runs twenty ordinary compositor/repaint frames with one-tick pacing. The final
idle redraw follows normal visibility-dirty policy, and none of this adds a
second gameplay turn.

**Addendum — 2026-08-24, complete potion flash timing table.** Issue #116
filled the five timing rows omitted by #115. `catalogs/item-list.md` now gives
the rumble accumulator target and both envelope iteration counts for all eight
selected bottle colours. Blue, Yellow, Red, Green, and Black use the same
rumble/XOR/two-sweep/XOR-restore control flow and the same sound-disabled busy
timing as Orange, Purple, and White; none has an exceptional structure.

**Addendum — 2026-08-23, outdoor ranged-attack contract re-verified and
published.** Three gaps around the outdoor creature ranged attacks were traced
and adversarially re-derived from the shipped binaries, and the result is now in
`systems/overworld.md` Section 6.2, which is the **single normative owner** of
both the trace procedure and the damage payload;
`systems/active-objects.md` Section 8, `systems/vehicles.md` and
`systems/encounters.md` point at it rather than restating it.

Newly published: the two-stage payload (impact presentation, then an
impact-absorption stage that branches only on the party transport marker), the
frigate hull roll over the closed interval `[1, 30]` with its strictly-less-than
survival test, the whole-party damage pass with an independent closed-interval
`[1, 8]` draw per living member, the exact field list the per-member helper
writes, the sub-tile line generation with its column-driven accumulator, the
fixed sampling interval and the never-tested last sample, and the exact-equality
breath recognition.

Withdrawn as wrong: "tested cell by cell for obstructions" in Section 6.2; the
claim that line-of-fire rules are symmetric between party and creatures; the
on-foot whirlpool "no-op" and "no drowning damage is applied by the whirlpool
branch" in Section 8 and in `systems/active-objects.md` Section 8; the label
"outdoor sea-serpent adjacency family" for `0xE0..0xE3` in
`systems/encounters.md` and `systems/movement.md` (it is the Sand Trap run,
bestiary class 40); and three probability figures that carried an
inclusive/exclusive off-by-one in the shared range draw — the surface tile-1
special is one-in-eight, the parched-desert special one-in-four, and the
low-water allowance die sixteen-in-sixty-five.

Ten items were published as **explicit named gaps** in a new Section 6.2.5
rather than left silent, including the unread tail of the stats-panel repaint
(the one hole in the "these fields and no others" claim), the status-byte
domain, the drowning loop's exit-test asymmetry, the two impact-absorption call
sites whose triggers are unestablished (a sailing collision and a per-turn
"rough seas" event), and the near-call-only limit of every caller census on this
path. Interior, dungeon and combat modes are explicitly out of scope: the
sampling interval differs there and none of Section 6.2.2 may be carried across.



**Last updated:** 2026-05-13 - Weapon range/effect table cleanup, CMDS meditate status sync, Balloon baseline negative closure, Item/combat attack-routing cleanup, Endgame END.DAT fixed-window correction, endgame refusal-tableau random local wander, Active-target attack-wrapper damage math, Polymorph Giant Rat replacement, Tremor exact damage/reward formula and actor-scan behavior, shared active-effect tag/counter values, high-circle spell handler details, spell handler-family mapping, directed spell wind-cone duplicate/prefilter cleanup, combat cursor/marker tail cleanup (listed before 2026-08-23 as "combat post-round terrain/effect maintenance"; that framing is withdrawn), proportional paragraph renderer cleanup, endgame final-presentation cleanup, EGA driver primitive cleanup, combat default drop-marker byte cleanup, intro story rectangle-transition contract, intro story rectangle helper boundary, shrine meditation state-machine cleanup, intro story-step transition/draw mapping, intro title tick/menu idle contract, intro title tick destination/source ownership, vehicles/ship-fire spec, containers/pickups spec, command routing cleanup, input idle-redraw timing cleanup, active-object idle animator placement, input blink/key mapping cleanup, text-output control/gate cleanup, visibility viewport-buffer cleanup, dungeon entry/data-record order, dungeon trap/pit subtype cleanup, magic field-placement byte cleanup, lighting counter duration cleanup, display rendering contract, spell parser correction, location floor-page rules, MISCMAPS record/trailer cleanup, MISCMAPS Return-to-View stream binding, MISCMAPS Return-to-View command table, MISCMAPS Return-to-View helper schedule, NPC floor-link marker IDs, OOL save-staging/mirror correction, U4 transfer source filename cleanup, U4 transfer exact mapping cleanup, overworld underfoot-latch cleanup, directed spell wind-cone friendly-fire boundary cleanup, combat active-object restore/loot-reconciliation boundary cleanup, combat reward-unit caller-propagation cleanup, combat descriptor-vs-active-object byte cleanup, dungeon active-object boundary cleanup, PTH open-question cleanup, save active-object persistence boundary cleanup, NPC schedule-Z unsigned cleanup, vehicle timing state-tag cleanup, save transport/status byte cleanup, vehicle transport-marker range cleanup, Blackthorn audience-entry predicate cleanup, rest/camp ambush presentation cleanup, shared arithmetic caller-census cleanup, shared arithmetic boundary cleanup, presentation/quest boundary cleanup, END.DAT format boundary cleanup, SHOPPE.DAT format-boundary cleanup, BIT format-boundary cleanup, boot sentinel boundary cleanup, movement predicate boundary cleanup, Blackthorn conversation-signal boundary cleanup, screen-mode write-error handler ownership cleanup, font high-bit caller-policy cleanup, LOOK2.DAT open-heading cleanup, weather ownership-boundary cleanup, conversation runtime-boundary cleanup, QUESTION.DAT variant-boundary cleanup, lighting/TLK boundary-label cleanup, Search trap caller-boundary cleanup, M-command split cleanup, OOL open-item cleanup, balloon negative-boundary cleanup, inventory runtime-boundary cleanup, SIGNS.DAT macro-boundary cleanup, input variation-boundary cleanup, text-output gate/eraser cleanup, time boundary cleanup, DUNGEON.DAT format-boundary cleanup, CBT format-boundary cleanup, NPC format-boundary cleanup, location DAT format-boundary cleanup, OOL format-boundary cleanup, save-format boundary cleanup, vehicle boundary cleanup, U4 transfer boundary cleanup, view boundary cleanup, command dispatcher boundary cleanup, doors/Z boundary cleanup, main-loop boundary cleanup, visibility boundary cleanup, shop boundary cleanup, overworld boundary cleanup, screen-mode boundary cleanup, animation boundary cleanup, SIGNS.DAT content-boundary cleanup, Blackthorn boundary cleanup, chargen boundary cleanup, inventory boundary cleanup, display ABI boundary cleanup, graphics archive boundary cleanup, DATA.OVL cleanroom-boundary cleanup, intro visual-boundary cleanup, encounter boundary cleanup, karma storage-boundary cleanup, magic effect-boundary cleanup, and town data-boundary cleanup added.

**Latest local addendum:** 2026-05-13 - Natural moongate live-tile refresh is now traced as saved-Moonstone-slot driven: eligible slots stamp terrain `0xDC` at night, wane back to terrain `5` by day, dirty visibility on tile changes, and remain separate from the render-frame animator scratch. The outdoor loop's live `0xDC` entry hook is also traced: it shimmers and clears the tile, routes midnight's first ten minutes to the shrine/urn kneel overlay, and otherwise uses the cached moon glyph to choose the saved Moonstone slot warp path. Conversation gold-payment karma boundary now records that the three-digit TALK gold-payment path debits party gold and can raise the shared moral-standing selector on a toll-progress milestone, but does not directly write per-virtue standing. Recent natural-moongate scratch writer census records outdoor chunk-loader coordinate reuse, town bright-light beacon-coordinate reuse, and combat phase reset as the traced writers around the animator scratch; no natural schedule storage writer is promoted. Low-circle status restore cleanup now records Awaken as a first-Sleeping roster scan rather than a selected-member prompt, Cure as a selected-member Poisoned-to-Good gate, and Great Heal's dungeon combat-active refusal. Active-object allocator cleanup now identifies the protected `0xB5` byte as a monster-variant actor class from the NPC roster, not the natural-moongate renderer. Get-side karma cleanup now separates borrowed-furniture feedback, which has no traced moral-standing debit, from the confirmed crop, table-food, and town-family chest penalties. Karma seed cleanup now records that the scalar moral-standing selector is factory-image seeded and character-creation preserved; no separate per-virtue numeric save layout is promoted, and neighboring unknown bytes stay opaque until an explicit writer or reader is traced. Dungeon pit-chain stock-data cleanup now records that shipped `DUNGEON.DAT` has no level-seven fall trap and no same-column fall-trap chain reaching level seven, so off-bottom pit-chain state is defensive compatibility for custom or mutated dungeon data. Combat class-flag cleanup now promotes COMBAT.OVL and the Combat system to complete by treating compound-only or readerless class-flag component bits as opaque metadata rather than missing behavior labels. P-Push stamp cleanup now corrects `0x90..0x93` as chairs, `0xB4..0xB7` as cannons, and records that `0x44` and `0x45` both resolve to cobble through LOOK2 while remaining distinct Push-family matching bytes.

**Current item-list closure cleanup:** 2026-05-13 -
`catalogs/item-list.md`, `systems/inventory.md`, and extraction now promote
Item list to complete at catalog depth. The catalog owns item identities,
equipment ids, prices, attack metadata, carried counters, U-Use families, and
quest-item flags; object pickup visuals and fixed Search placements remain
owned by `systems/containers.md` and `systems/hidden-treasures.md`, dialogue
reactions by quest-graph validation, and vehicle markers by vehicle/save specs.
The Sandalwood Box wording now keeps the gettable object visual separate from
inventory-add code `0x0E` instead of treating item-to-tile mapping as an
item-list blocker.

**Current monster-bestiary closure cleanup:** 2026-05-13 -
`catalogs/monster-bestiary.md` and extraction now promote Monster bestiary to
complete at class-catalog depth. The catalog owns class ids, sprite runs,
stat rows, side-table values, traits, reward/drop inputs, and special class
assignments; dungeon room arena selection, per-arena spawn counts, replacement
tiles, final sprite-sheet tile ids, and pixel-level special-death visuals stay
with encounter, `.CBT`, tile-catalog, combat, or presentation specs.

**Current tile-catalog closure cleanup:** 2026-05-13 -
`catalogs/tile-catalog.md` and extraction now promote Tile catalog to complete
at gameplay-catalog depth. All five hundred and twelve top-down tile indices
have class assignments and storage-domain contracts; passability, LOOK2
ownership, special-trigger routing, active-object classing, and file-format
boundaries are covered. Per-frame visual attribution, marker-label polish,
render-only sentinel naming, field-frame duration checks, and pixel/runtime
trace cross-checks are presentation/catalog QA rather than extraction blockers.

**Current quest-graph closure cleanup:** 2026-05-13 -
`catalogs/quest-graph.md` and extraction now promote Quest graph to complete
at main-quest dependency depth. Major artifact, word, shard, mantra,
shrine/Codex urn, social, utility-item, companion, and endgame dependencies
are public without dialogue text or TLK bytecode. Shipped-TLK reachability
comparison and embedded/trailing-record triage remain QA/data-authoring aids,
not gameplay-spec blockers.

**Current overworld residual narrowing:** 2026-05-13 -
`systems/overworld.md` and extraction now cover the saved-slot ordinary
natural-moongate live-tile placement/waning schedule and the live `0xDC`
entry hook. The former two partial rows are promoted to complete; tile naming,
opaque timing/transport values, and chunk-substitution labels are catalog,
opaque-data, or QA work rather than unresolved outdoor loop control flow.

**Current moongate negative-census cleanup:** 2026-05-13 -
`systems/overworld.md` now removes the stale wording that grouped visible
moongate frames with active-object slots. The completed disassembly scan still
finds only outdoor chunk-loader coordinate reuse, town bright-light beacon-coordinate reuse,
and combat animation-phase reset around the animator scratch block; moon-table
and hour/minute readers belong to status presentation, item utilities, or spell
utilities, not a natural-gate placer. A read-only binary direct-write scan over
the installed program and overlay files agrees for the narrow static-writer
class: no additional animator-coordinate natural-gate writer was found. The
ordinary live-terrain refresh is now specified separately from saved Moonstone
slots. `formats/under-dat.md` and `catalogs/gazetteer.md` also avoid publishing
untraced moongate outcomes or outdoor underworld ascents as plane writers.

**Current live moongate-helper boundary:** 2026-05-13 -
`systems/overworld.md`, `systems/moons.md`, and extraction now record that the
resident moongate-tile shimmer helper is live through the outdoor loop's raw
resident call. The earlier generated caller table missed that wrapped MAINOUT
call; the separate CAST-overlay negative delta remains relevant only for CAST
overlay callers, not for MAINOUT. The helper reads the sky/status moon-glyph
cache only after confirming live moongate terrain, then either reports the
midnight shrine/urn branch or calls the saved-slot warp helper. Shipped-map
scans still find no static natural-moongate tile cells in `BRIT.DAT`, so source
terrain remains separate from live natural-gate refresh. The private `0x48A8`
note has been corrected away from the older lockpick/unlock-door label, while
its historical filename remains unchanged.

**Current moongate tile-domain boundary:** 2026-05-13 - `systems/active-objects.md`,
`systems/overworld.md`, and `catalogs/tile-catalog.md` now separate terrain byte
`0xDC` from active-object type byte `0xDC`. A committed outdoor active-object
step onto live terrain byte `0xDC` clears the moving slot, while active-object
type byte `0xDC` names the first Dragon frame for monster movement rules. This
does not own the entry hook, which is now specified as an overworld loop hook.
The resident generic animated-tile helper was also rechecked: it cycles
the adjacent `0xD8..0xDB` tile-state family and wraps before `0xDC`, so it is
not a live-terrain `0xDC` natural-gate producer. A LOOK2-backed tile-catalog
cross-check also corrected the stale `0x80..0x87` moongate-family wording:
that range is pendulum/restraint/grate/archway fixtures, not the traced
natural-moongate terrain byte.

**Current Moonstone slot-writer boundary:** 2026-05-13 -
`systems/overworld.md`, `systems/inventory.md`, `formats/saved-gam.md`, and
`catalogs/item-list.md` now point at the direct CAST Moonstone U-Use helper
trace. That helper validates the current scene and underfoot terrain, then
writes only the selected saved Gate Travel/Search destination slot. It does not
write the moongate animator scratch, choose ordinary natural-gate coordinates,
or teleport the party. Follow-up resident tracing now shows those saved slots
also drive the ordinary natural-gate live-terrain refresh and are consumed by
the live entry hook's saved-slot warp path.

**Current DATA.OVL intro-metadata boundary:** 2026-05-13 -
`formats/data-ovl.md` now stops describing the compact bytes adjacent to the
story/menu string region as moongate or world-transition lookup data. The
traced INTRO consumer uses that band as story-slide presentation metadata for
per-step art, placement, text, and local display-effect parameters. This narrows
the remaining moongate work by removing a stale resident-data false lead; it
does not own the live entry hook, which is specified by the overworld loop.

**Current fixed-gate branch detail:** 2026-05-13 -
`systems/overworld.md` now records the live fixed-coordinate gate branch at
source-free behavioral depth. **Exact transcript update 2026-08-25:** the
shared fragment is only a leading LF plus opening quote; the nonzero ordained
arm prints `Pass, Seeker!`, while the zero arm prints the Sacred Quest and
Passage denied refusal and moves the party one cell south. Exact embedded LF
placement, the absence of a live-tile equality guard or special presentation,
the slot-zero mirror rule, and the single ordinary-turn cleanup boundary are
now normative. This remains a fixed narrative branch, not the saved-slot
live-terrain refresh or live `0xDC` entry handler.

**Current random-wind cleanup:** 2026-05-13 -
`systems/weather.md` and extraction now include the idle-redraw random wind
selector. Eligible redraw ticks make a rare outer roll, then choose a wind
candidate where cardinal directions are accepted immediately and Calm requires
a follow-up high roll; accepted values route through the existing wind
display/setter helper and clear the cached wind-cadence byte. This path is
weather state/presentation, not natural-moongate placement.

**Current dungeon flavour-boundary cleanup:** 2026-05-13 -
`systems/dungeon-mode.md` and `EXTRACTION.md` now close the former
dungeon-flavour gameplay question. The flavour byte is presentation-facing:
corner glyphs, dungeon-view resource selection, class-`0xC?` wall/corpse
look text, normal-flavour wall decoration, and the Doom-flavour rare text
easter egg. It does not select encounter tables, fountain effects, trap
difficulty, geometry, or tile semantics; those remain owned by the scene /
`DUNGEON.DAT` record, tile subtype, and the relevant command/transition specs.

**Current dungeon pit-chain handoff cleanup:** 2026-05-13 -
`systems/dungeon-mode.md`, `systems/doors-and-z-transitions.md`,
`systems/main-loop.md`, and extraction now specify the chained-pit
off-bottom state at the traced boundary. When a fall chain increments beyond
the deepest dungeon level, it clears the dungeon scene byte while leaving the
incremented off-bottom level byte and the trap-chain X/Y in resident state; it
does not call the dungeon surface-reset helper or exterior-coordinate tables.
The later stock-data scan found no level-seven fall traps and no same-column
vertical fall-trap chain reaching level seven, so the off-bottom path is now
documented as defensive compatibility for custom or mutated dungeon data. This
is not a remaining local DUNGEON.OVL mutation question.

**Current SAVED.GAM status cleanup:** 2026-05-13 - `EXTRACTION.md` now
promotes the `SAVED.GAM` / `INIT.GAM` / `BRIT.GAM` row to complete at
flat-image and seed-producer depth, matching `formats/saved-gam.md` and the
chargen/U4-transfer specs. Remaining unnamed mixed-band bytes and opaque
transport/action marker values are preservation/runtime ownership work, not
base save-image layout blockers.

**Current OOL status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes the
`SAVED.OOL` / `INIT.OOL` / `BRIT.OOL` / `UNDER.OOL` row to complete at
table-layout and lifecycle depth, matching `formats/ool.md` and
`systems/save-load.md`. Remaining uncommon family auxiliary-byte meanings,
future mirror-reader census, and underworld population-source questions are
runtime/catalog ownership work rather than `.OOL` file-layout or mirror-contract
blockers.

**Current save/load status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
the cross-cutting Save/load row to complete at the original four-file
byte-image contract depth. `systems/save-load.md`, `formats/saved-gam.md`, and
`formats/ool.md` cover the read/write order, empty-save guard, mirror writes,
fresh-save `.OOL` first-load behavior, primitive I/O edges, and single-slot
overwrite semantics; opaque saved bytes and optional modern backup/versioning
policies remain outside the original save/load contract.

**Current MISCMAPS.DAT status cleanup:** 2026-05-13 - `EXTRACTION.md` now
promotes `MISCMAPS.DAT` to complete at file-layout and command-stream depth,
matching `formats/location-dat.md`. Cutscene map sectioning, Return-to-View map
strips, the 655-byte stream, command/argument behavior, loop rule, actor/map
side effects, local cell-effect loops, fixed rectangle sequence, and preview
tick counts are public; resident helper pixel/raster/wait parity remains
intro/display-driver presentation work.

**Current chargen/U4 transfer status cleanup:** 2026-05-13 - `EXTRACTION.md`
now promotes Character creation and U4 transfer entry to complete at
fresh-save producer and preview-region depth. `systems/chargen.md` and
`systems/u4-transfer.md` cover the questionnaire producer, seed preservation,
transfer validation and mapping, `.OOL` emission/first-load mirror behavior,
abort/commit boundaries, preview regions, and intro/menu return; exhaustive
transfer preview cursor, attribute, and redraw-timing parity remains
presentation work.

**Current LOOKOBJ status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
`LOOKOBJ.OVL` to complete at gameplay-command depth, matching
`systems/view.md`. Look routing, LOOK2 domains, object/sign/poster text,
special clock/shrine/dungeon/fountain/well branches, death vision, Britannia
map view, local V-View overlay, party marker, visual-class mapping, and
per-class renderers are public; pixel-perfect V-View screenshots and palette
details remain visual QA.

**Current rest/camp status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
Rest and camp to complete at gameplay-contract depth, matching
`systems/rest-and-camp.md`. H-Hole-up routing, terrain and bed gates, duration
input, town-hour loop, watch validation, interruption, recovery, sleep-ambush
handoff, dormant helper non-use, Lord British camp event, and hourly
food/provision delegation are public; low-level string-window, audio/delay, and
refresh-helper parity remains presentation work.

**Rest/camp caller-gate closure:** 2026-08-23 - The camp-event context gate is
now public without exposing private addresses. Ordinary overworld camp is the
only shipped caller context that consumes the event draw; dungeon camp is
suppressed before PRNG consumption, town-bed rest uses another handler, and the
second suppression condition has no shipped public setter and remains reserved.
Cooldown refusal and durations of five hours or less bypass the context gate,
event draw, and cooldown write entirely. Issue #96 is closed by this contract.

**Current display-driver status cleanup:** 2026-05-13 - `EXTRACTION.md` now
promotes both `EGA.DRV` and Display driver/rendering contract to complete at
the EGA/v1 compatibility depth, matching `systems/display-driver.md` and
`systems/display-driver-abi.md`. The semantic renderer, EGA dispatch ABI,
front/back-buffer boundary, rectangle fill, compressed-bitmap decode, tile and
glyph paths, and title/dissolve entries are public; alternate-driver
conversion and non-load-bearing hardware parity remain outside the v1 contract.

**Current endgame status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
both `ENDGAME.OVL` and the cross-cutting Endgame row to complete at
terminal-state contract depth, matching `systems/endgame.md`. Entry trigger,
Doom handoff, overlay confirmations, box-flag gate, resource reads, refusal
tableau, final narrative, certificate date/elapsed-time output, no-save
boundary, and no-return behavior are public; pose mapping, helper taxonomy, and
resource-slot/panel parity remain presentation QA.

**Current NPC roster status cleanup:** 2026-05-13 - `EXTRACTION.md` now
promotes NPC roster to complete at roster-catalog depth, matching
`catalogs/npc-roster.md`. Location rosters, scene/place crosswalk, schedules,
AI/mode meanings, keyword counts, occupied tag bytes, named NPCs, and authored
punctuation-only display entries are public; full keyword graph integration
belongs to quest/conversation catalog validation.

**Current OUTSUBS status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
`OUTSUBS.OVL` to complete at overlay-helper contract depth. Chunk loading and
scrolling, live-buffer substitutions, filename/plane selection, town-entry
checks, confirmed falls transition, per-plane active-object setup, and the
outdoor-camp Lord British level-up service are public. Broader outdoor
transition/catalog, timing-tag, transport-marker, and chunk-substitution naming
outliers remain catalog, opaque-data, or QA work rather than OUTSUBS helper
blockers.

**Current town status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes both
`TOWN.OVL` and Town/interior mode to complete at behavioral-contract depth,
matching `systems/town-mode.md`. Entry/load, marker harvest, dawn/dusk and
cosmetic rewrites, exits/stairs, command hooks, alarm/arrest, NPC scheduling,
active-object ownership, free-roaming objects, Stonegate producers, entry-mode
preservation, secret-room mechanism delegation, and save/load reconstruction
are public; Stonegate presentation, authored secret-location inventory, and
rare nested script-return checks remain presentation/data/empirical work.

**Current Blackthorn status cleanup:** 2026-08-27 - `EXTRACTION.md` now
promotes both `BLCKTHRN.OVL` and Blackthorn capture/rescue to complete at
cinematic-overlay contract depth, matching `systems/blackthorn.md`. Audience
setup, challenge prompts and answers, punishment/release, local byte-script
movement, rescue/refuge restoration, `KARMA.DAT` verdict selection, durable
state writes, exact town/overworld/dungeon entry predicates, direct town-side
captive entry, and the rescue tail's zero-only Food grant and existing
moral-standing floor are public. The alleged captive counter, parallel rescue
progression byte, and capture-context field do not exist. Pixel-level cutscene
effects remain presentation work.

**Current CBT runtime closure:** 2026-08-27 - `formats/cbt.md`,
`systems/combat.md`, and `systems/dungeon-mode.md` now publish every traced
metadata slice, the roster-slot meaning of both outdoor six-byte coordinate
tables, every shipped dungeon special-source identity and state write,
geometric edge behavior, individual leave/escape removal and restore semantics,
the dormant fifteen-swap terrain branch, both live wandering-monster callers,
the distinct sixteen-swap arena synthesis, exact PRNG order, caller-owned
presentation, and deterministic vectors. Unread metadata bytes remain opaque
round-trip material; no runtime blocker remains under the earlier CBT heading.

**Current ZSTATS status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
`ZSTATS.OVL` to complete at overlay-contract depth. The covered Z-stats page
families, inventory browsing, and shared R-Ready storage/eligibility flow no
longer carry an overlay-owned atomic-swap, displaced-equipment, or status-page
routing parity gap; remaining item-use, catalog, combat-consumer, and
save-format gaps stay delegated to their respective specs.

**Current shop status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes the
SHOPPES overlay-family row and the cross-cutting Shops row to complete at
gameplay-control depth, matching `systems/shops.md`. Remaining shop-adjacent
publication work is catalog/data-table detail for item stats and resident
tables, not a shop menu, payment, persistence, or dispatch gap.

**Current lighting status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
Lighting to complete at counter, ambient-light, and scene-gate depth, matching
`systems/lighting.md`. The high ambient skip-recompute value remains defensive
compatibility behavior because no normal gameplay writer is identified, not a
remaining lighting-system question.

**Current spell-list status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
the Spell list row to complete at player-spell-table depth. Residual magic work
stays with per-effect exactness and item/equipment consumers, while combat-AI
monster-special row assignments belong to combat/bestiary specs rather than the
forty-eight-entry public spell table.

**Current container status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
Containers and pickups to complete at container/pickup-system depth. Remaining
item-use effects stay with the item and magic specs; consumed-object
persistence, ordinary counter caps, and inventory-add subtypes no longer carry
a container-owned gap.

**Current vehicle status cleanup:** 2026-05-13 - `EXTRACTION.md` now promotes
Vehicles and ship fire to complete at command and state-transition depth,
matching `systems/vehicles.md`. Remaining vehicle art-frame naming and opaque
transport/action values outside known ranges stay catalog or opaque-state work,
not live vehicle command gaps.

**Current save transport/status terminology cleanup:** 2026-05-13 -
`formats/saved-gam.md` and extraction now use the settled field split:
`0x02D4` is the timing/status glyph byte consumed by the stats panel and
timing tags, while `0x02D6` is the transport/action marker whose known
vehicle ranges live in `systems/vehicles.md`. Remaining save exactness is
unnamed mixed-band bytes plus opaque transport/action marker values outside
the known ranges, not a combined transport/status enum.

**Current active-object status cleanup:** 2026-05-13 - `systems/active-objects.md`
now states the shared table lifecycle is complete for known traced users, and
`EXTRACTION.md` promotes Active objects to complete at table-lifecycle depth.
Any future uncommon non-projectile dynamic-object caller is caller-owned work,
not a projectile lifecycle or core table gap.

**Current rest target-hour cleanup:** 2026-05-13 - `systems/rest-and-camp.md`
and `EXTRACTION.md` now publish the town bed H-Hole-up target-hour wrap edge:
after a `1` through `9` digit is accepted, current hour plus digit values above
23 subtract 23 rather than using ordinary modulo-24 wrapping. The rest/camp row
is now complete at gameplay-contract depth; low-level presentation parity is
tracked separately.

**Current ship repair-boundary cleanup:** 2026-05-13 - `systems/vehicles.md`
and `catalogs/item-list.md` no longer list ship repair as a live vehicle
command gap. Hull condition is consumed by boarding warnings and broadside
depletion; no traced B-Board, X-Xit, Y-Yell, F-Fire, U-Use, or shipwright sale
path repairs it in the analyzed baseline. Any future repair-service evidence is
shop/item acquisition work.

**Current magic status-boundary cleanup:** 2026-05-13 - `EXTRACTION.md` now
marks the Magic/spells/reagents row complete at player-spell contract depth,
matching `systems/magic.md`: the dispatcher, scene gate, spell-charge model,
shrine/urn split, wrong-mix helper, effect-family contracts, and
forty-eight-entry player spell table are public. Equipment counters, visual
tile labels, and monster combat-AI state are delegated to their owning specs.

**Current EGA status-boundary cleanup:** 2026-05-13 - `EXTRACTION.md` now
spells out the `EGA.DRV` partial status using the same boundary as
`systems/display-driver-abi.md`: remaining work is historical hardware or
visual parity around non-load-bearing helper-slot meanings, unreached
tile-mutator modes, alternate-driver conversion, and metadata-word use outside
the EGA compressed-bitmap decode path.

**Current LOOKOBJ tile-0x59 cleanup:** 2026-05-13 - `systems/view.md`,
`formats/look2-dat.md`, and `EXTRACTION.md` now separate the traced tile
`0x59` special route from its unresolved catalog label. Ordinary Look on that
tile enters the full Britannia chunk-map renderer; whether the in-world label
belongs with wells, a map/sextant-like object, or another catalog name remains
tile/LOOK2 catalog reconciliation, not a renderer or command-flow gap.

**Latest local addendum:** 2026-05-12 - Magic absorption pre-gate naming added: Lord Blackthorn's Castle absorbs casts while the Crown of Lord British flag is clear, and Stonegate absorbs casts unconditionally. Lighting docs now cover the ambient skip-recompute sentinel as defensive compatibility behavior, the current absence of any normal gameplay writer that deliberately sets it, and the separate overworld zero-light override. Container docs now publish the top-level inventory-add class mapping for pickups/chests/Search results plus the surface/town chest primary and secondary content pools. A new `systems/traps.md` specifies the shared resident party trap-effect resolver and its non-combat effect distribution, while encounter/CBT docs now separate traced dungeon room arena indexing from the absence of any traced dungeon chest arena caller. Jimmy docs now cover ordinary door/visible-chest/NPC rolls, NPC failed-key consumption, per-map object chest broken-lock state, and dungeon chest formulas. The item catalog now reconciles V-View gem consumption: non-combat View consumes one gem before LOOKOBJ/DNGLOOK dispatch, while combat View is label-only and consumes nothing. A new `systems/view.md` consolidates LOOKOBJ/DNGLOOK Look and View behavior, including surface/town Look dispatch, temporary gem-view overlays, dungeon Look darkness/cell-class handling, and dungeon minimap restore semantics. The equipment catalog now publishes the full forty-eight-row equipment item-id order, and `systems/chargen.md` enumerates the factory-seed readied equipment for every roster slot without copying raw seed bytes. Endgame entry wording now separates the terminal overlay's Lord British confirmation dialogue from what was then an unresolved final gameplay handoff, and it no longer models the trigger as an ordinary Lord British throne-room keyword conversation. `formats/end-dat.md` and `formats/endmsg-dat.md` now publish the shipped END.DAT text-window and ENDMSG.DAT eleven-record structures and delegate endgame caller/timing gaps back to the endgame system. `formats/karma-dat.md` now separates the six-record verdict-text layout from the traced Blackthorn five-band selector and preserves the unreached sixth record as authored data. `formats/question-dat.md` now documents the shipped plain-ASCII/no-high-bit profile and treats unsupported markup bytes as strict-mode asset errors rather than runtime semantics. `formats/signs-dat.md` now uses the traced scene-directory, coordinate-record, and formatter-stream model instead of the stale rectangular-grid interpretation. `formats/miscmsg-dat.md` now names the traced Blackthorn, shrine, and urn/Codex consumer families instead of carrying stale caller-mapping uncertainty. `formats/story-dat.md` now points story-step timing and secondary draws to the intro system contract instead of treating them as file-format uncertainty. Earlier 2026-05-11 work covered Protection defense bonus, Quickness player-dispatch gate, Mass Charm class-threshold target-selection remap, Negate Magic combat-cast absorption, active-effect gap cleanup, S-Search surface/dungeon semantics, the combat field-contact post-step boundary, the arena-field helper placement/application split, combat field active-object marker contact, non-consuming field contact, combat field-kind mapping, coordinate-lookup slot/flag eligibility, accepted-placement redraw/lifetime non-ownership, combat field lifetime until combat exit, Poison/Sleep field-contact status gates, Fire/Energy field damage inputs, directed wind/sleep cone geometry and friendly-fire behavior, monster combat-AI boundary cleanup, monster death-flag asset verification cleanup, time/light-scale endpoint cleanup, dawn/dusk gradient and personal-light floor correction, saved wind-byte preservation, Rel Hur wind-transition boundary cleanup, natural-moongate placement-boundary cleanup, overlay dispatch and low-level call wording cleanup, save-file runtime-address cleanup, saved-scene scratch byte layout cleanup, `EXTRACTION.md` partial-row gap summaries, spell-list open-work cleanup, cleanroom provenance wording, source-provenance boilerplate cleanup, manifest-reference audit cleanup, stale encounter arena-reference cleanup, source-like layout-fence cleanup, shared runtime countdown cleanup, karma non-shrine action hypothesis cleanup, KARMA.DAT standing terminology cleanup, X-it escape-helper routing cleanup, magic-lock spell-name cleanup, NPC cached-waypoint/stuck-threshold cleanup, conversation keyword-match/table-scan cleanup, and chargen duplicate-pair/STR-floor/loser-delta cleanup.

**Current DATA.OVL shared-scratch cleanup:** 2026-05-13 -
`formats/data-ovl.md`, `catalogs/gazetteer.md`, and `formats/brit-dat.md`
now avoid treating the resident coordinate scratch read by the moongate
animator as durable natural-gate state. The same words are reused by outdoor chunk
loading and town marker harvest, so public specs describe natural moongate
placement as unresolved schedule/transition metadata, separate from transient
animation scratch.

**Current NPC format-boundary follow-up:** 2026-05-13 -
`formats/npc.md` now says the `.NPC` file-format contract is complete at
file-structure and schedule-consumer depth. The remaining blank-location-name
and sprite-class-label work is explicitly catalog naming work, matching the
extraction inventory's treatment of `.NPC` layout as closed.

**Current dungeon pit/Klimb transition cleanup:** 2026-05-13 -
`systems/dungeon-mode.md`, `systems/doors-and-z-transitions.md`, and
extraction now split the three dungeon pit/exit paths: ordinary ladders are
capped at levels 0..7, exact `0x60` under K-Klimb invokes the surface-reset
helper, and automatic `0x61`/`0x69` chained pits keep the separate off-bottom
scene-clear edge. The older Hythloth bottom-ladder handoff wording is no
longer a public route contract.

**Current PROPORT.PCS boundary cleanup:** 2026-05-13 -
`formats/font-pcs.md`, `systems/text-output.md`, and extraction now retire the
old width-table-plus-glyph-blob hypothesis. `PROPORT.PCS` is specified as a
driver sparse-strip resource that supplies glyph artwork, while the
proportional renderer's 128-entry advance table is resident runtime data.

**Current Blackthorn DATA.OVL table cleanup:** 2026-05-13 -
`formats/data-ovl.md` now matches the current Blackthorn spec: the resident
challenge tables' live four-prompt mapping is public at semantic level
(Honesty/Ahm, Compassion/Mu, Valour/Ra, Justice/Beh), while raw resident table
layout remains private provenance.

**Current magic target-family boundary cleanup:** 2026-05-13 -
`systems/magic.md` no longer frames the formerly unique high-circle target
families as an active blocker. Directed wind/sleep scans, active-target attack
wrappers, table-wide sweeps, creature prompts, and Mass Charm's active-effect
consumer are public. Monster-special variant behavior remains outside the party
C-Cast dispatcher and is published through combat/bestiary ownership.

**Current summon/clone lifetime cleanup:** 2026-05-13 - magic, spell-list, and
extraction now avoid inventing a per-spell duration countdown for summoned or
cloned combat actors. The traced summon/conjuration helpers place, activate,
repurpose, or clone actor records; ordinary combat death/record-clear paths can
remove those actors during the fight, and combat exit restores the pre-combat
actor tables. The later summon placement cleanup promotes the live Conjure,
Swarm, and Summon placement paths, so the player-spell contract does not carry
an unresolved summon-duration gap.

**Current summon placement cleanup:** 2026-05-13 - the public magic,
spell-list, and extraction docs now distinguish Conjure's fixed weighted animal
selector plus independent `0..10` X/Y placement attempts, Swarm's eight target
cells with short placement retries, Clone's paired-slot copy, the spell-side
summon/tame actor-repurpose helper using descriptor bit `0x01`, and Summon's Daemon-class placement helper, which probes
**eight independent random cells** (**corrected 2026-08-23**: this entry said
"ordered eight-cell ... placement helper"; the ordered-ring reading is withdrawn
and `catalogs/spell-list.md` already carries the correction). The CAST2
shrine/urn active-object pattern helper remains shrine/urn kneel presentation
rather than a party C-Cast summon row, so its private visual pattern must not be
published or reused as Conjure/Swarm/Summon placement data.

**Current doors/Z guarded-refusal wording cleanup:** 2026-05-13 -
`systems/doors-and-z-transitions.md` no longer implies an unpromoted hidden
override flag as public contract. Non-dungeon Open now frames the traced
blocked-openable case as the too-heavy tile refusal, then delegates unmatched
object-table outcomes to the chest helper; ship fire is described as a separate
door/wall mutation path outside the Open/Jimmy refusal cascade.

**Superseded 2026-08-22:** the stationary-display purchase reading below is retracted; `systems/shops.md` section 8.10 now specifies the helper as the horse-trader sale placement arm (adjacent-cell probe, accepted placement tiles, horse active-object write) with no display-stock row. See issue #28.

**Current stationary-display shop cleanup:** 2026-05-13 -
`systems/shops.md` now promotes the misnamed SHOPPES `find_shopkeeper` helper
as a stationary-display purchase flow rather than a shopkeeper-recognition or
karma gate. The flow scans nearby display markers, confirms purchase, debits
gold plus any normal surcharge, and writes the bought display item into the
speaking member's carried-item state.

**Current NPC type-byte wording cleanup:** 2026-05-13 -
`formats/npc.md` and `catalogs/npc-roster.md` no longer invent a generic
"townsfolk" meaning for an example type byte. They now separate type bytes as
stable sprite classes from schedule AI, and publish only the safe behavioural
bands: empty/default-person/player mirror, guard-like alarm handling, and
hostile/corpse-state activation or death-mask eligibility.

**Current item Moonstone acquisition wording cleanup:** 2026-05-13 -
`catalogs/item-list.md` no longer says the Moonstone has both a full
acquisition-path gap and a fully known acquisition path. It now separates the
known bury/Gate-Travel/Search-Get recovery contract from still-open
initial/story acquisition outside those paths. A follow-up private-note check
confirmed the SJOG "strange rock" lookup walks the saved Moonstone destination
slots, not a fixed DATA.OVL spawn table; the analyzed DATA.OVL initial bytes
for that runtime region are all zero. The same pass repaired the
quest/utility item table so the shard-grant note no longer breaks the table
before the Spyglass row.

**Current save/load extension-boundary wording cleanup:** 2026-05-13 -
`systems/save-load.md` no longer calls versioning and multi-slot saves open
questions. It now matches the body of the spec: the original save image has no
version marker, the original engine exposes one save slot, and modern format
extensions, backups, and slot directories are compatibility policies layered
outside the byte-image contract.

**Current rest/watch prompt cleanup:** 2026-05-13 -
`systems/rest-and-camp.md`, `systems/encounters.md`, and extraction now promote
the resident overworld/dungeon H-Hole-up watch flow: duration digit input,
optional watch prompt when more than one eligible participant exists,
Good-status watcher validation, and dungeon handoff through the combined
rest/camp alternate combat-framer mode. The remaining rest/camp gap is
presentation parity around string-window boundaries, audio/delay timing, and
refresh helper identity.

**Current startup boundary cleanup:** 2026-05-13 -
`systems/boot.md` now treats MZ relocation and startup-stack arithmetic as a
process-loader compatibility boundary, not gameplay state. `systems/launcher.md`
now delegates no-selector display fallback and EGA sentinel policy to boot, and
it corrects the old extra dispatch-cell wording by pointing the resident
disk-error handler to `systems/disk-prompt.md` and the loaded
driver ABI to `systems/display-driver-abi.md`. (Superseded 2026-08-22: that
second cell was called the "resident screen-mode controller" here; the name is
withdrawn.)

**Current boot sentinel boundary cleanup:** 2026-05-13 -
`systems/boot.md` now treats the EGA sentinel as a startup-environment edge:
the traced loader has a no-driver-load outcome if the sentinel reaches it
unchanged, while modern engines should either normalize the display selection
deliberately or fail with a clear unsupported-display error before driver
loading. This is a compatibility boundary, not a remaining boot gap.

**Current movement predicate boundary cleanup:** 2026-05-13 -
`systems/movement.md` now treats final art/catalog naming for still-generic
non-vehicle query families as catalog ownership. The movement-system contract
is complete at predicate depth: direction routing, candidate sampling,
tile-class dispatch, named vehicle/foot accepted ranges, generic predicate
families, dynamic occupancy, and commit/redraw ordering are public.

**Current overlay ABI boundary cleanup:** 2026-05-13 -
`systems/overlay-abi.md` no longer treats the two SHOPPES leaf utility entries
as an overlay ABI gap; their visible roles are already covered by the shop
greeting and post-transaction surcharge contracts in `systems/shops.md`. The
remaining uncalled FONT exports and opaque loader descriptor fields are framed
as byte-loader-harness boundaries, not ordinary clean-engine gameplay work.

**Current karma storage-boundary cleanup:** 2026-05-13 -
`systems/karma.md` and extraction now rule out the older hypothesis that the
byte after the low byte of party gold is a karma field; the current save and
inventory specs identify that word as party gold. The traced scalar
moral-standing selector is save offset `0x02E2`, used by shrine rewards,
Blackthorn/Lord British verdict selectors, and several non-shrine action
deltas. The remaining karma-storage gap is any separate still-unidentified
per-virtue numeric standing layout and seed, not `KARMA.DAT`, shrine quest
masks, the scalar selector, or the inventory gold word.

**Current karma closure cleanup:** 2026-05-13 -
`systems/karma.md` and extraction now promote Karma/virtues/shrines to
complete at traced moral-standing depth. The shared selector now covers shrine
rewards, verdict selectors, TALK threshold reads, resurrection XP penalties,
selected object/action deltas, and the known negative boundaries. No separate
per-virtue numeric save layout or ordinary combat/flee standing writer is
promoted for the traced baseline; future explicit writers should be added with
their own trigger and clamp/floor rule rather than inferred from dialogue text.

**Current karma combat-exit cleanup:** 2026-05-13 - karma and extraction now
align with the combat/encounter reward boundary: no traced combat-exit path
adds a virtue delta. The later karma closure also declines to infer ordinary
attack, victory, or flee deltas from combat fiction without an explicit scalar
or per-virtue writer.

**Current conversation gold-payment karma-boundary cleanup:** 2026-05-13 -
`systems/conversation.md`, `systems/karma.md`, and extraction now separate the
TALK three-digit gold-payment control byte from charitable-giving karma. The
traced helper decodes the demanded amount, debits party gold when affordable,
and can raise the shared moral-standing selector on a toll-progress milestone;
no direct per-virtue standing write is present in that helper, so any
Compassion reward for giving must be traced in a different action branch.

**Current stolen-action karma-boundary cleanup:** 2026-05-13 -
`systems/karma.md` and extraction now separate TALK's stolen-action warning and
cleanup envelope from any non-promoted Honesty-standing writer. Conversation
entry can display the warning and final cleanup can print the matching warning,
play presentation audio, reconcile one-shot signals, or refresh the gold panel,
but no scalar or per-virtue standing writer is promoted from those visible
warning paths.

**Current stolen-action cleanup wording:** 2026-05-13 - karma and conversation
docs now avoid treating TALK final cleanup as a confirmed theft-karma pipeline.
The visible warning, fixed sound, transient-signal cleanup, and gold-panel
refresh are public; any later theft-karma effect requires a separate explicit
standing writer.

**Current dungeon pit-exit cleanup:** 2026-05-13 - `systems/dungeon-mode.md`,
`systems/main-loop.md`, `systems/doors-and-z-transitions.md`, and extraction
now separate the dungeon surface-reset helper from pit-chain off-bottom exits.
The surface-reset helper is the coordinate-restoring path; chained pit falls
that run past level seven clear the dungeon scene byte while preserving the
trap-chain X/Y and leaving the level byte at the incremented off-bottom value.
Production reachability and any later outer-loop recovery for that off-bottom
case remain open.

**Current Yell presentation-effect cleanup:** 2026-05-13 -
`systems/commands.md` and extraction now distinguish recognized
Word-of-Power feedback from successful door transmutation. Any recognized
Word-of-Power match plays the shared low-rumble / full-viewport flash
presentation effect before the location-specific door check; only matching the
current room's door metadata mutates the live tile and dirties visibility.

**Current Blackthorn challenge-table cleanup:** 2026-05-13 -
`systems/blackthorn.md` and extraction now publish the exact four live
challenge prompt/answer pairs from the resident tables: Honesty/Ahm,
Compassion/Mu, Valour/Ra, and Justice/Beh. Later virtue/mantra table entries
remain authored data, but the traced challenge loop does not iterate them.

**Current Blackthorn script-VM cleanup:** 2026-05-13 -
`systems/blackthorn.md` and extraction now publish the cutscene VM's clean
modal contract: repeat counts, paired movement, per-step pause mode,
actor-indexed cardinal steps, and the five traced script beats. **Superseded
2026-08-27:** the remaining visual work is closed. The supposed output-byte
operation is a redraw pause with no text effect, the supposed clear is one world
tick, and the exact tile identities and direct-screen boundaries are now in
Sections 6 and 7. The same pass also corrects the actor roles: slots 6 and 7
are guards, while slot 8 is the seated-Blackthorn tableau; the mobile
punishment and release role is a guard, not Blackthorn.

**Current Blackthorn audience-entry cleanup:** 2026-05-13 -
`systems/blackthorn.md`, `systems/town-mode.md`, and extraction now pin the
direct town-side entry predicate for the audience/capture sequence: the ordinary
town post-scheduler event cleanup reaches the arrest/unconscious handler, and
the Blackthorn captive scene branches from that handler into the audience
cinematic instead of the ordinary Yew-arrest prompt. Remaining entry exactness
is the upstream defeat/capture condition that creates the captive context and
any death-route marker, plus the rescue/refuge per-mode trigger predicates.

**Current Blackthorn conversation-signal boundary cleanup:** 2026-05-13 -
`systems/blackthorn.md` now separates the transient TALK-produced Blackthorn
conversation signal from the durable captive context, death-route marker, and
rescue/refuge trigger predicates. The signal belongs to the conversation
cleanup band in `systems/quest-flags.md`; it is not enough by itself to enter a
Blackthorn cinematic.

**Current Blackthorn rescue caller-family audit:** 2026-05-13 -
`systems/blackthorn.md` and extraction now state the rescue/refuge entry at the
right precision: the traced cross-call evidence proves town, overworld, and
dungeon reachability, but not the local story predicates inside those mode
callers. That predicate work remains open rather than being inferred from the
overlay entry itself.

**Current Blackthorn boundary cleanup:** 2026-08-27 -
`systems/blackthorn.md` now frames the traced overlay behavior as complete at
cinematic-contract depth: audience setup, challenge matching, punishment and
release branches, byte-script movement semantics, rescue/refuge restoration,
`KARMA.DAT` verdict selection, durable state writes, and the direct town-side
audience entry predicate are public. The exploration-mode rescue entry predicate
and all persistent fields are also closed. A later same-day presentation pass
also closes pixel-level exactness: every terrain/actor tile identity and cell,
all pause/redraw semantics, the blocking cell reveals, paired flash, and both
rectangle dissolves now have deterministic vectors. The alleged output-byte
glyph and screen-clear commands are withdrawn. The former slot-role reading is
withdrawn as well: both mobile throne-side actors are guards, and seated
Blackthorn occupies the separately revealed tableau slot.

**Current rest/camp ambush presentation cleanup:** 2026-05-13 -
`systems/rest-and-camp.md`, `systems/encounters.md`, and extraction now publish
the clean ordering inside the H-Hole-up sleep-ambush branch: sleep narration
precedes the interruption test; an interrupt picks the eight-row monster entry,
prints the ambush message, restores the rest-local party status snapshot, and
then hands the selected row to the CMDS alternate rest/camp setup path.
Remaining rest/camp exactness is low-level sound, delay, or prompt-control
helper identity, not row selection, status restoration, or the dormant terrain
placement shuffle.

**Current shared arithmetic caller-census cleanup:** 2026-05-13 -
`systems/stat-arithmetic.md` now promotes the finished helper-family caller
census at cleanroom granularity: fifty total calls split across byte/word
capped-add and floor-subtract helpers, plus public caller families for food,
HP, damage, experience, inventory stock, spending, virtue standing, timers,
modal selectors, and Blackthorn/story floors. That cleanup established the
helper behavior and module-level census; the boundary cleanup below assigns
exact field/cap pairings to the owning gameplay specs.

**Current shared arithmetic boundary cleanup:** 2026-05-13 -
`systems/stat-arithmetic.md` now treats the four helper shapes, comparison
models, in-place mutation rule, module-level call census, and public
caller-family inventory as the complete shared-helper contract. Exact
field/cap pairings, direct assignments, and caller-local arithmetic exceptions
belong in the owning gameplay specs; extraction now reflects that this is not a
central runtime gap.

**Current presentation/quest boundary cleanup:** 2026-05-13 -
`systems/stats-panel.md` and `systems/quest-flags.md` now use boundary sections
instead of stale Open Work headings where no layer-specific gap remains.
Transport-marker, combat-descriptor, text-rendering, unnamed save-band, and
named-NPC lifecycle questions stay with their owning specs.

**Current END.DAT format boundary cleanup:** 2026-05-13 -
`formats/end-dat.md` now treats the six fixed caller-windowed narrative pages,
plain-text marker rules, and separation from `ENDMSG.DAT` as complete file
format coverage. Extraction marks `END.DAT` complete; any remaining visual
page/panel parity belongs to `systems/endgame.md`.

**Current SHOPPE.DAT format boundary cleanup:** 2026-05-13 -
`formats/shoppe-dat.md` now treats dispatch, stock, pricing, side effects, and
per-id caller inventory as caller-owned shop-system questions rather than
on-disk text-container uncertainty. The format contract remains the sequential
NUL-terminated record set with token and placeholder expansion.

**Current BIT format boundary cleanup:** 2026-05-13 -
`formats/bit.md` now treats pointer-entry metadata as preserved but
non-rendering data for the EGA baseline, and moves non-EGA substitute art plus
title/story timing back to display and intro ownership. Extraction now marks
`TITLE.BIT` and `BRITISH.BIT` complete at the file-format layer.

**Current endgame tableau-animation cleanup:** 2026-05-13 -
`systems/endgame.md` and extraction now close the stale facing-animation gap
for the terminal refusal tableau. The helper is specified as throttled random local
wander over the authored endgame tableau's walkable cells, with up to eight
four-direction candidate attempts per call and one display/palette tick after
the attempt. Remaining endgame exactness is visual page/panel parity and
low-level helper identity, not party-sprite facing animation.

**Current endgame END.DAT fixed-window correction:** 2026-05-13 -
`systems/endgame.md`, `formats/end-dat.md`, and extraction now replace the
stale roster/retirement interpretation of the post-rite helper. The traced
consumer opens endgame presentation graphics and the proportional font, then
loads six fixed caller-selected `END.DAT` windows for the return-home and
Blackthorn judgment/gate narrative sequence. It does not scan six party slots,
resolve character homes from location data, or use `END.DAT` as per-character
retirement text. Remaining endgame exactness is visual page/panel parity and
low-level helper identity.

**Current SIGNS/CBT cleanup:** 2026-05-12 - `formats/signs-dat.md`
now treats `0x26`/`0x27` as decorative separator controls and narrows
the remaining macro gap to byte-exact resident decoration fragments.
`formats/cbt.md`, `systems/combat.md`, `catalogs/tile-catalog.md`,
`catalogs/monster-bestiary.md`, `formats/data-ovl.md`, and extraction
now identify the `BRIT.CBT` metadata slices copied by the outdoor arena
loader: two six-byte resident setup tables plus the sixteen X/Y placement-slot
coordinate tables. The placement slices are the confirmed arena-local monster
arrival coordinates; the six-byte table entry meanings remain unnamed. Spawn
counts and replacement-tile rolls remain resident combat data, and no traced
dungeon chest path currently selects a `DUNGEON.CBT` arena.

**Current town-mode cleanup:** 2026-05-12 - `systems/town-mode.md`
and extraction now cover the remaining promoted TOWN.OVL slice at behavioral
depth: per-scene NPC activation/death masks, deterministic terrain variation,
movement direction/exit/stair handling, town-local Open and Attack policy,
Lord British basement chord state, Stonegate and underfoot effects, alarm
forced-pursuit / forced-flight schedule-rewrite sweeps, arrest/jail outcome, post-scheduler event dispatch,
and the free-roaming animal/object walker. Remaining town exactness is mostly
data-table naming and byte-for-byte sequence verification, not the public
mode contract.

**Current town data-boundary cleanup:** 2026-05-13 - `systems/town-mode.md`
now frames the former variation list as data and empirical parity work. Entry,
map load, marker harvest, dawn/dusk substitution, cosmetic variation,
movement/floor/exit transitions, command hooks, alarm/arrest handling,
NPC schedule integration, active-object ownership, free-roaming object movement,
and save/load entry reconstruction are public at mode depth. Remaining town
work is Stonegate presentation-asset parity, authored secret-location
inventory, and rare nested script-return setup parity.
The system inventory row
now uses the same former partial boundary instead of the older first-slice
label.

**Current town attach-sentinel cleanup:** 2026-05-13 - `systems/town-mode.md`
and extraction now identify the traced writer for the town-entry `Y == 4`
attach bypass: the surrender branch of the town arrest flow sends the party to
Yew jail at `(25, 4, 0)`, after which the attach helper skips the
permanent-location queue search and returns before allocating a fresh phantom
NPC. Remaining town exactness no longer includes this writer; it is back to
Stonegate presentation-asset parity, authored secret-location inventory, and
rare nested script-return setup parity.

**Current town re-entry boundary cleanup:** 2026-05-13 -
`systems/town-mode.md` and extraction now publish the entry-mode preservation
mechanism: the preserving setup skips the ordinary active-object tail clear,
and player attach can short-circuit against an existing player slot. The later
entry-caller census cleanup below assigns the traced fresh versus preserving
callers.

**Current town entry-caller census cleanup:** 2026-05-13 -
`systems/town-mode.md` and extraction now assign the traced setup argument
callers. Fresh setup is used after overworld-to-town entry, after a
dungeon-wrapper return that leaves a town-family scene active, and by the
resident NPC-location warp helper when it changes town-family scenes.
Preserving setup is the direct already-in-town/save-load dispatch path.
Remaining work is only rare nested script-return empirical parity.

**Current dungeon overlay cleanup:** 2026-05-12 - `systems/dungeon-mode.md`
and extraction now cover the remaining promoted DUNGEON/DNGLOOK slice at
behavioral depth: local command-parser intercepts, active-monster collision,
movement turn-around fallback, electric-field force-step presentation, K-Klimb
prompt/apply and surface-reset exits, attack-forward combat entry,
post-action monster engagement, room-clear bitmap demotion, room layout and
NPC seeding, and the DNGLOOK minimap/room painter helper family. Later cleanup
publishes the minimap class-to-glyph ids and flood-return table, so remaining
dungeon minimap exactness is visual glyph/pixel parity rather than flood
ownership. The wind-tile torch-extinguish claim is now resolved negatively for
the analyzed baseline contact paths. Room completion durability is now tied to
the saved room-clear bitmap plus reload-time demotion, not patched dungeon
geometry.

**Current dungeon transition-boundary cleanup:** 2026-05-13 -
`systems/dungeon-mode.md` now frames the former variation list as low-nibble,
visual, and transition parity work. Scene/record binding, first-person
rendering gates, command parsing, movement/turning, L-Look/V-View,
Search/Open/Get handoffs, K-Klimb, room combat triggers, post-action monster
engagement, trap effects, room-clear persistence, and save/load behavior are
public at dungeon-loop depth. Low-nibble presentation/catalog naming outside
published gameplay subtypes and V-View visual parity are now framed as
catalog/presentation QA, not dungeon-loop behavior gaps.
Open/Get chest trap and reward ownership is
delegated to the door/container specs rather than kept as a dungeon-mode gap.
Later pit/Klimb cleanup removes the older deepest-level underworld handoff from
the public route contract.

**Current dungeon low-nibble boundary cleanup:** 2026-05-13 -
`systems/dungeon-mode.md` and extraction now separate packed-cell gameplay
subtypes from residual catalog naming. Fountains, energy fields, room ids,
named pit/trap bytes, visit-local marker bits, and Search/Open/Get rewrites are
covered; ordinary wall/door visual naming, trap marker variants outside the
named Search/post-action bytes, secondary field-family visuals, and V-View
pixel parity are catalog/presentation QA. The Dungeon mode extraction row is
now complete at dungeon-loop behavior depth.

**Current LOOKOBJ cleanup:** 2026-05-12 - `systems/view.md` and extraction
now cover the promoted LOOKOBJ slice: LOOK2 terrain/object lookup domains,
object-description line cleanup, fixed wanted-poster branch, SIGNS.DAT
scene-directory and coordinate-record lookup plus token rendering, overworld fountain no-heal boundary, wishing-well keyword and scene
gate flow, death-vision local overlay, Britannia chunk-map overlay, local
32-by-32 modal view overlay, party marker, view-origin scaling, and the
per-class surface/town V-View renderer contracts. Remaining LOOKOBJ exactness
is fine pixel placement/glyph screenshots, not the command, tile-id
visual-class table, or overlay ownership contract.

**Current FONT cleanup:** 2026-05-12 - `systems/intro.md`,
`systems/chargen.md`, and extraction now cover the remaining promoted
FONT.OVL helpers: Return-to-View entry setup, map-strip loading, per-frame
active-object/tile animation bridge, screen save/restore bracket, chargen's
rejection-sampled virtue picker, and the corrected questionnaire principle
delta mapping. Remaining Return-to-View exactness is still the resident/display
helper raster and pacing internals already tracked under intro visual parity,
not the FONT-owned control-flow contract.

**Current INTRO checklist cleanup:** 2026-05-12 - the remaining INTRO.OVL
function-note status boxes now align with already-public specs: boot/menu/title
flow, BRITISH.PTH signature walking, story slide sequencing, Journey Onward
load and OOL mirroring, and U4 transfer/continue roster handling are covered in
`systems/intro.md`, `systems/save-load.md`, and `systems/u4-transfer.md`.
Residual exactness remains the public visual-helper and transfer UI capture
work, not the high-level intro control contract.

**Current intro visual-boundary cleanup:** 2026-05-13 - `systems/intro.md`
now frames the former open questions as renderer/content boundaries: gameplay
entry, menu/story flow, Journey/transfer handoffs, and Return-to-View preview
ownership are complete at public contract depth. Remaining intro work is
pixel-perfect helper parity for Return-to-View and the story rectangle wipe,
source-free acknowledgement pagination, independently authored title tick
replacement frames, and alternate-driver parity.

**Current OUTSUBS checklist cleanup:** 2026-05-12 - the remaining OUTSUBS.OVL
status boxes now align with already-public overworld/rest specs: two-plane
world filename selection, 2-by-2 chunk loading and in-buffer scroll shuffling,
terrain-class helper boundaries, E-Enter town entry, the fixed surface falls
transition, underworld active-object reinitialization, overworld party-status
poison tick, and the superseded camp/save structural note are covered in
`systems/overworld.md`, `systems/rest-and-camp.md`, and the world-map format
docs. The chunk-loader's fixed live-buffer substitutions are now covered; the
remaining OUTSUBS exactness is helper classification detail and semantic naming
of those substituted tile ids, not the mode contract.

**Current MAINOUT checklist cleanup:** 2026-05-12 - the remaining MAINOUT.OVL
status boxes now align with already-public overworld, encounter, and
active-object specs: mode entry/init, command-loop turnover, random encounter
spawn and terrain monster selection, outdoor hostile-slot engagement, per-slot
animation/movement, off-screen pruning, and the per-turn random-encounter probe
are covered in `systems/overworld.md`, `systems/encounters.md`, and
`systems/active-objects.md`. Remaining MAINOUT exactness is the helper-level
damage and classifier detail already tracked in private notes, not the public
mode contract.

**Current CAST dispatcher checklist cleanup:** 2026-05-12 - the CAST.OVL
dispatcher status box now aligns with already-public magic specs:
C-Cast prompting, compact spell-token lookup, charge/mana/level gates, scene
allow-mask gating, shared combat/out-of-combat dispatch, forty-eight-entry
handler routing, success/failure narration, and persistent charge/mana side
effects are covered in `systems/magic.md`, `catalogs/spell-list.md`, and
`formats/saved-gam.md`. Later cleanup promotes the player-spell effect
families as a complete public contract at behavioral depth.

**Current CMDS checklist cleanup:** 2026-05-12 - the remaining CMDS.OVL status
boxes now align with public command, karma, and combat specs. The legacy
mantra-style Yell branch is documented as unreachable shipped behavior in
`systems/commands.md`, with live shrine meditation owned by `systems/karma.md`;
the CMDS escape routine is now correctly bounded as combat-only X-it cleanup in
`systems/combat.md`. Stale door/Z-transition wording that treated the same
routine as a dungeon spell escape helper has been removed pending separate
spell-path evidence.

**Current COMSUBS checklist cleanup:** 2026-05-12 - the remaining COMSUBS.OVL
status boxes now align with public combat, magic, DATA.OVL, and bestiary specs:
the combat C-Cast pre-gate is the adjacent-target interference check, not an
MP/resource gate, and the monster special hook is bounded to possess,
blink/phase, and summon-daemon branches with baseline class assignments.
Residual COMSUBS private-analysis work is branch runtime capture and internal
helper-label polish; it is not part of the public combat or spell contract.

**Current COMBAT checklist cleanup:** 2026-05-12 - the remaining COMBAT.OVL
status boxes now align with public combat and bestiary specs: round-loop
phase/dispatch/exit behavior, combat command routing and monster command
synthesis, target-picker filtering/fallback/direction synthesis, and the
damage/status/death helper are covered in `systems/combat.md` and
`catalogs/monster-bestiary.md`. Remaining COMBAT exactness is residual
class-flag component labels and presentation-edge visual parity. The
ranged/effect selector, payload, scene-resistance row values, and no-target
centre fallback flee writer are now published.
Post-combat reward/loot ownership is now a
negative boundary: no traced combat-exit gold/karma/victory-bonus write or
post-fight SJOG loot sweep is part of the core combat contract.

**Current summon-edge cleanup:** 2026-05-13 - `systems/magic.md`,
`catalogs/spell-list.md`, and extraction now promote the completed CAST summon
edge details: Conjure's fixed weighted animal selector plus independent
`0..10` X/Y placement attempts, Swarm's eight target cells with short placement
retries, Summon's eight independent random placement probes (**corrected 2026-08-23** from "ordered eight-cell placement ring"), and the continued
separation of Conjure/Swarm/Summon from the CAST2 shrine/urn presentation
pattern.

**Current combat class-flag boundary cleanup:** 2026-05-13 -
`systems/combat.md` now frames the former variation list as an opaque
class-flag metadata policy. Entry modes, actor
rounds, command dispatch, target selection, ordinary AI, damage/death,
experience credit, active-effect consumers, field contact, terrain/effect
maintenance, escape/victory exits, and post-combat reconciliation are public at
combat-loop depth. Component bits that only appear in combined tests or lack
independent behavioral consumers are intentionally not named as separate public
traits. Attack-time ammunition,
thrown-stock, and glass-breakage
consumption are closed negative boundaries in the item catalog for the analyzed
baseline.

**Current combat ranged-side-table cleanup:** 2026-05-13 -
`systems/combat.md`, `catalogs/monster-bestiary.md`, and extraction now publish
the ranged/effect selector and payload side-table rows for hostile and special
classes, plus the Mage party-row boundary, the scene-resistance rows, the
Gremlin cast-like branch row, and the Mimic pre-gate bypass row. Later cleanup
records that compound-only or readerless class-flag component bits are opaque
metadata, not a remaining combat behavior gap.

**Current CAST2 checklist cleanup:** 2026-05-12 - the CAST2.OVL status boxes
now align with public save and shrine specs: Quit-and-Save writes,
per-plane OOL staging/mirroring, shrine mantra/state-machine handling,
post-completion offerings, Codex turn-in rewards, and shrine/Codex mask updates
are covered in `systems/save-load.md`, `formats/saved-gam.md`,
`systems/karma.md`, and `systems/magic.md`. Caller trampolines and private
helper/table labels are not part of the public save or shrine contract.

**Current SJOG checklist cleanup:** 2026-05-12 - the remaining SJOG.OVL status
boxes now align with public command, container, inventory, dungeon, magic, and
combat specs. Search/Jimmy/Open/Get routing, object-table action semantics,
hidden treasure and rare-reagent scans, dungeon chest rewards, inventory-add
families, Moonstone recovery, and the combat step-or-attack primitive are
covered in `systems/commands.md`, `systems/containers.md`,
`systems/hidden-treasures.md`, `systems/dungeon-mode.md`,
`catalogs/item-list.md`, `systems/magic.md`, and `systems/combat.md`.
Remaining SJOG inventory-add subtype exactness is closed.
The known container/Search grant caps and non-equipment subtypes are now
public: potion and scroll grants use the same eight catalog rows and cap at 99,
ordinary key grants update skeleton keys, marked odd-key grants update the
skull/special-key stock, torch/gem/key byte counters cap at 99, and valid shard
grant subtypes map to the three Shadowlord shards. Equipment grants use the
forty-eight public equipment ids; Arrows and Quarrels award five-unit bundles,
while other equipment awards add one carried unit.

**Current moongate hook boundary cleanup:** 2026-05-12 -
`systems/main-loop.md`, `systems/moons.md`, and `systems/overworld.md` now
resolve the older hourly gameplay-hook wording as hour-change sky/status
row refresh. The corrected `0x4A84` trace is a moon/status renderer, so the
public contract separates that display-only refresh and the render-frame
moongate animator from the saved-slot natural live-tile refresh.

**Current sky/status strip cleanup:** 2026-05-13 - `systems/moons.md`,
`systems/time.md`, `systems/stats-panel.md`, DATA.OVL, and extraction now
describe the corrected lower-row sky renderer: a twelve-cell strip plots an
hour-derived fixed marker plus independent day-indexed Trammel and Felucca
glyphs, with exact visible-hour windows, left-to-right cell formulas, marker
overwrite order, and out-of-horizon markers omitted. This is still display-only;
the later overworld cleanup owns the natural-moongate entry hook.

**Current monster spawn-table boundary cleanup:** 2026-05-13 -
`catalogs/monster-bestiary.md` and extraction now stop treating all spawn
distribution tables as a monster-catalog gap. The outdoor random-spawn terrain
buckets are already specified in `systems/encounters.md`; the later
monster-bestiary closure cleanup also delegates dungeon-room and other
non-outdoor cross-indexing to encounter/arena specs rather than keeping it as a
monster-catalog gap.

**Current moongate tile-animation cleanup:** 2026-05-13 -
`catalogs/tile-catalog.md` no longer describes moongate frames using the old
lunar-pair tile-cycle model. The clean contract now follows the
overworld animator trace: moongate graphics are a bespoke transient frame plate
driven by the animator's sixteen-phase counter, separate from status-strip moon
glyphs and from the saved-slot live-terrain placement/waning schedule.

**Current transition-inventory wording cleanup:** 2026-05-13 -
`systems/doors-and-z-transitions.md` now matches the overworld transition
inventory: surface/underworld open work is limited to routes outside the traced
surface chasm, whirlpool forced-underworld engagement, and scene-`0x19`
interior-exit plane-selection writers.

**Current NPC scene-index cleanup:** 2026-05-13 -
`formats/npc.md`, `systems/npc-schedules.md`, and extraction now make the
NPC loader's scene-byte arithmetic explicit as a scoped one-based-to-zero-based
index conversion for `.NPC` file/sub-map selection. The public scene id remains
one-based before and after roster loading; this is not a scene transition or
alternate persistent numbering scheme.

**Current M-Mix wrong-recipe boundary cleanup:** 2026-05-13 -
`systems/magic.md` and extraction now separate the exact resource contract for
wrong M-Mix recipes from the helper effect: selected reagents are spent and no
spell charges are granted. A later cleanup promoted the helper path as the
shared trap-effect resolver.

**Current NPC file-format status cleanup:** 2026-05-13 -
Extraction now marks the four `.NPC` roster/schedule files complete at file
layout depth. Remaining NPC naming work is catalog interpretation in
`catalogs/npc-roster.md`, not an unresolved `.NPC` format field.

**Current stats-panel miniature-glyph cleanup:** 2026-05-13 -
`systems/stats-panel.md` now identifies the bottom timing/status glyph as
rendered through the resident miniature tile-glyph path described by
`formats/tiles.md`, separate from both `TILES.16` atlas crops and fixed-cell
text rendering.

**Current M-Mix wrong-helper cleanup:** 2026-05-13 -
`systems/magic.md`, `systems/traps.md`, and extraction now close the
wrong-recipe helper path: after selected reagents are spent and no spell charges
are granted, the mixer refreshes the trap target slot from the first
Good/Poisoned travelling member when one exists and invokes the shared
trap-effect resolver.

**Current EGA page-boundary cleanup:** 2026-05-13 -
`systems/display-driver.md`, `systems/display-driver-abi.md`, and extraction
now stop listing hardware page flipping as an open v1 gap. The EGA baseline
selects visible page zero at mode setup; later transition paths copy or dissolve
from driver-managed page memory into that front buffer instead of using ordinary
hardware page flips for world/text frames.

**Current item-cap and equipment-stat cleanup:** 2026-05-13 -
`catalogs/item-list.md` and extraction now treat non-equipment inventory counter
limits, equipment base prices, ordinary attack max-damage values, shared combat
attack-routing shape, guild commodity prices, herbalist reagent prices, healer
treatment fees, tavern drink and provision prices, horse and shipwright base
prices, and inn base/minimum rates as closed catalog coverage. The traced caps
for gold, food, keys, gems, torches, spell charges, scrolls, potions, and
equipment grants are public. The later item-list closure cleanup promotes
object visual mapping, Search placement, story acquisition, and transport
marker residuals to their owning specs rather than item-catalog blockers.
Opaque transport/action marker values outside known ranges are
save/vehicle opaque-state work rather than item rows. The later
equipment-defense cleanup closes live armour-to-combat-defense recomputation as
a negative boundary: combat uses the cached character defense byte.

**Current item vehicle-boundary cleanup:** 2026-05-13 -
`catalogs/item-list.md` and extraction now delegate ordinary vehicle terrain
rules to `systems/movement.md` and normal transport-marker ranges to
`systems/vehicles.md`. The item catalog no longer carries vehicle terrain
rules as an item-list gap; balloon is now an art-only boundary for the analyzed
baseline rather than a live item-side transport gap.

**Current Ankh use-boundary cleanup:** 2026-05-13 -
`catalogs/item-list.md` and extraction now treat Ankh as an equipment-row item
with amulet/neck class metadata, not as a traced CAST U-Use, quest ritual, or
consumable item. The same cleanup separates the CAST Box U-Use prompt from the
Sandalwood Box's Lord British endgame confirmation handoff. The later item-list
closure keeps prompt/report details with the owning U-Use or presentation specs
and variant-only evidence with any later binary that adds attack-time equipment
consumption.

**Current pickup visual/code boundary cleanup:** 2026-05-13 -
`systems/containers.md`, `catalogs/item-list.md`, and extraction now separate
the `G` Get per-map object visual filter from the inventory-add class code.
Sandalwood Box acquisition reaches the inventory-add code `0x0E` only after a
gettable object-tile family has matched; the class code itself is not published
as a gettable object-tile id. The later item-list closure treats broader
object visual mapping as tile/containers ownership, not an item-list blocker.

**Current U-Use utility/regalia narrowing:** 2026-05-13 -
`systems/inventory.md`, `catalogs/item-list.md`, and extraction now promote the
family-level CAST U-Use utility boundaries: Sceptre scans eligible non-dungeon
nearby cells for the top-down `0x70..0x7F` barrier/field family and dissolves
accepted cells, Spyglass is an item gate into the LOOKOBJ full Britannia
chunk-map renderer, Pocket Watch prints only a twelve-hour AM/PM hour, Black
Badge uses the shared worn-item helper, and Amulet/Crown remain shared
worn-regalia toggles. Dialogue reactions to carried or worn story items are
quest-graph branch-validation work rather than item activation.

**Current consumed-object persistence cleanup:** 2026-05-12 -
`systems/containers.md` now separates the persistence mechanisms for consumed
container/pickup results: ordinary object-table grants and surface/town chests
clear the live object-table slot, fixed hidden treasures use the saved
already-found bitmap, Moonstone pickups invalidate the matching saved Gate
Travel slot, and tile consumables persist by live-tile rewrites rather than
object-slot clearing.

**Current SJOG table-food cleanup:** 2026-05-12 - `systems/containers.md`
now publishes the table-food reach matrix for the traced Get fallback. The
two table-food tile variants are vertical-only targets, with horizontal and
diagonal reaches producing the cannot-reach-plate refusal and no mutation.
Successful reaches mutate the live tile, credit one food unit, set the
eating-action bookkeeping, and debit the shared moral-standing selector when
nonzero.

**Current TALK checklist cleanup:** 2026-05-12 - the remaining TALK.OVL status
boxes now align with public conversation and TLK specs: Talk entry lookup,
talk-through fallback, sleeping/no-response stubs, four-class `.TLK` loading,
fixed 1024-byte blob windows, top-level keyword loop, reserved-keyword scan,
ordinary per-NPC keyword matching, byte-runner control codes, label blocks, and
quest/action side effects are covered in `systems/conversation.md`,
`formats/tlk.md`, `systems/quest-flags.md`, and `catalogs/quest-graph.md`.
Remaining TALK exactness is live verification of minor print-mask behavior and
full quest-graph branch enumeration, not the runtime contract.

**Current U4 transfer mapping cleanup:** 2026-05-12 -
`systems/u4-transfer.md`, `systems/chargen.md`, `systems/intro.md`, and
extraction now publish the exact mapped transfer behavior: `PARTY.SAV`
validation, slot-0-only import, source gender/class/status translation,
three-region STR/DEX/INT conversion, Strength-only floor, MP from converted
INT, XP divided by ten, level from scaled XP, and current/max HP from level.
The gate over eight consecutive candidate words inside the second source block
is now fixed as the Avatarhood test, not a no-transferable-data gate; later
cleanup identifies those candidate words as the predecessor virtue/karma
standings, and static dispatch cleanup fixes post-commit control as intro/menu
redraw. Remaining transfer gaps are preview pixel coverage.

**Current overworld underfoot cleanup:** 2026-05-12 -
`systems/overworld.md`, `systems/lighting.md`, vehicles, and extraction now
replace the stale underfoot-damage interpretation with the traced pre-loop
underfoot latch: overworld tile state `0xFF`, unless exempted by state tag
`0x0E`, forces cached light/radius to zero, dirties the view on first entry,
blocks outdoor movement commit while latched, and runs a zero-minute cleanup
when cleared.

**Combat post-round maintenance - WITHDRAWN 2026-08-23.** This entry read, as
current: *"`systems/combat.md` and extraction now promote the resident combat
post-round pass: it sweeps the eleven-by-eleven runtime arena terrain/effect
grid, dispatches normal, cooldown-sensitive, and table-mapped cell effects..."*
**There is no such pass.** A complete re-read of the routine, and of both
helpers it calls per cell, establishes that it is the engine's single viewport
rasterizer: it runs from the idle tick in *every* scene, not once per combat
round; the eleven-by-eleven buffer it walks is the viewport, not the arena
terrain grid; and both per-cell helpers are display-driver blit wrappers that
dispatch no effect and mutate no game state. Only its tail - the cursor-box
blink and an optional second marker - is combat-gated. `systems/combat.md`
Section on the round loop carries the full withdrawal and the corrected
description; `EXTRACTION.md` was corrected to match on the same date. Anyone who
implemented a per-round arena effect sweep from this entry should delete it.

**Current proportional paragraph renderer cleanup:** 2026-05-12 -
`systems/text-output.md` and extraction now separate the FONT overlay's
proportional paragraph renderer from the resident fixed-cell text-window
printer. The public contract covers NUL termination, width-table glyph
advances, space lookahead wrapping, hard newlines, underscore soft-hyphen
breaks, brace page/paragraph markers, and caller-owned keypress pacing.

**Current endgame final-presentation cleanup:** 2026-05-12 -
Superseded by the 2026-05-13 END.DAT fixed-window correction above. The durable
part of this entry is the certificate-scroll work: the endgame computes elapsed
campaign time from year 139, month 4, day 5 with thirteen-month/twenty-eight-day
borrowing, and then remains in the scroll's no-return final state. The older
roster/location interpretation is no longer the public contract.

**Current endgame handoff wording cleanup:** 2026-05-13 -
`systems/endgame.md` and extraction now separate the overlay-owned
Lord-British-styled box confirmation from ordinary throne-room TALK routing.
This entry is superseded by the caller and Doom final-room route cleanups below:
the low-level dungeon-room/post-combat callers and stock route reachability are
now resolved there.

**Current endgame caller cleanup:** 2026-05-13 - `systems/endgame.md`,
`formats/endmsg-dat.md`, and extraction now use the newer overlay-loader caller
census: the ENDGAME export is statically reached from dungeon-room and
post-combat cleanup paths gated by the special combat absorption marker. The
remaining reachability gap was later closed by the Doom final-room route cleanup
below; this entry remains the low-level caller provenance.

**Current endgame absorption-marker cleanup:** 2026-05-13 - combat, dungeon,
endgame, and extraction now publish the producer/consumer split for the terminal
handoff marker: a special combat absorption effect writes the marker from the
committed non-digit action tail when its fixed actor/renderer predicates match,
and dungeon room/post-combat cleanup
consumes it by entering ENDGAME. The remaining reachability gap was later
closed by the Doom final-room route cleanup below; this entry remains the
producer/consumer provenance.

**Current Doom final-room route cleanup:** 2026-05-13 -
`systems/endgame.md`, `systems/dungeon-mode.md`, `systems/combat.md`,
`formats/cbt.md`, `formats/dungeon-dat.md`, `formats/endmsg-dat.md`,
`catalogs/quest-graph.md`, and extraction now close the stock endgame
reachability gap. Doom level seven's room-id-fifteen trigger at local
`(X=5, Y=7)` selects Doom `DUNGEON.CBT` slot fifteen, the final arena record;
that arena's metadata participates in the special absorbable-class combat
handoff consumed by ENDGAME. The later metadata conversion cleanup below
identifies the room setup scan and final absorbable-field source marker, so
remaining endgame exactness is visual final-presentation parity, not the final
room route or a Lord British TALK caller.

**Current Doom final-room metadata conversion cleanup:** 2026-05-13 -
`formats/cbt.md`, `systems/dungeon-mode.md`, `systems/combat.md`,
`systems/endgame.md`, and extraction now identify the dungeon-room metadata
scan used by room-trigger setup. For room-trigger entries, DNGLOOK setup reads
sixteen source cells from the loaded arena metadata band; in Doom slot fifteen,
the first scanned source cell is the `0x3C` absorbable-field family marker. The
setup places that source through the special active-object path, preserving the
family consumed through the renderer companion band by the combat absorption
hook. The scan boundary now
separates ordinary class-derived combatant sources from special-placement
sources. Remaining Doom-room metadata work is per-subtype labels for unrelated
special-placement values and the non-final opaque slices, not the terminal
handoff conversion; broader `.CBT` runtime work still includes arena-edge
behavior and any future ambush or non-room dungeon arena callers.

**Current endgame END.DAT consumer cleanup:** 2026-05-13 -
`formats/end-dat.md`, `systems/endgame.md`, and extraction now identify
`END.DAT` as final-presentation narrative text consumed after the Lord British
dialogue, not as the source of the opening confirmation or certificate body.
The later fixed-window correction above supersedes the older per-character
retirement interpretation.

**Current END.DAT seek-window cleanup:** 2026-05-13 -
Superseded by the fixed-window correction above. The durable part of this entry
is that brace markers are text-layout/page markers inside caller-selected
windows rather than an ordinal section index parsed by the runtime.

**Current encounter double-flag cleanup:** 2026-05-13 - combat, encounter, and
extraction docs now separate the double-encounter/fortunes-of-war flag's proven
read, save-image persistence, and 28-day month-boundary clear from its
unresolved gameplay setter. Current static sweeps found no setter. Sleep
ambushes are no longer described as a confirmed writer until a traced write
site supports that claim.

**Current encounter flag persistence cleanup:** 2026-05-13 -
`formats/saved-gam.md` now names the save-image tail byte that carries the
fortunes-of-war encounter count-reroll flag. `systems/encounters.md` and
`systems/combat.md` now state that explicit save/load preserves the flag's
resident value, the 28-day month rollover clears it, and no gameplay setter is
currently traced.

**Current EGA driver primitive cleanup:** 2026-05-12 -
`systems/display-driver-abi.md` and extraction now make the corrected EGA slot
boundaries explicit: dispatch offset `0x3F` is a clipped front-buffer rectangle
fill, dispatch offset `0x42` is the sparse-strip bitmap/font resource decoder,
and ordinary 16-by-16 tiles plus 8-by-8 fixed-cell glyphs render directly to the
front buffer. Back-buffer fills are owned by the earlier span/rectangle entries,
not by the corrected slot-21 path.

**Current input direction-prompt cleanup:** 2026-05-12 -
`systems/input.md` and extraction now distinguish the resident adjacent-tile
command direction prompt from the spell direction prompt. Command handlers such
as Search/Jimmy/Open/Get/Push/Talk/Fire use a cardinal-only vector selector
after their verb prefix; diagonals and unrelated keys re-prompt, while
Space/Pass returns the no-direction result. The extended-scancode mapping now
publishes all four arrow keys: left/right map to West/East and up/down map to
North/South, matching the numpad cardinal path.

**Current conversation keyword cleanup:** 2026-05-12 - `systems/conversation.md`, `formats/tlk.md`, `systems/karma.md`, and extraction now separate TALK's fixed thirty-four-entry reserved-word table from ordinary per-NPC `.TLK` keyword pairs. NAME/JOB-WORK/BYE-THANK aliases, the profanity/default rebuke route, and the fact that JOIN/WHO flows are response control-byte mechanics rather than reserved keywords are now explicit. The stale reserved-table gap has been removed.

**Current conversation print-mask cleanup:** 2026-05-12 - `systems/conversation.md`, `formats/tlk.md`, and extraction now specify `0x8E` as a protected-run toggle rather than an unresolved output mode. The default print mask preserves high-bit queued bytes so spaces and literal newlines trigger normal word-buffer breaks; the flipped mask strips that bit before queuing, so short uppercase runs such as mantras, spell syllables, Words of Power, passwords, and coordinate-letter notations render the same but are not split by ordinary soft-break handling.

**Current TLK fixed-window cleanup:** 2026-05-12 - `systems/conversation.md`, `formats/tlk.md`, and extraction now document that TALK loads a fixed 1024-byte window from the matched `.TLK` blob offset rather than computing a length from the next header entry. This is an observable compatibility edge: the last `DWELLING.TLK` entry has a 1139-byte nominal span, so binary-compatible engines must preserve the fixed-window cap instead of exposing the full file span.

**Current TALK label-block cleanup:** 2026-05-12 - conversation, TLK, and extraction now replace the stale "unique label target" model with the traced label-record contract. `0x90` is documented as labelled-block record structure, `0x91..0x9F` enter the label handler and may repeat inside a blob, and labelled blocks can run scoped "Your interest?" prompts with their own keyword matching. Inner empty-input behavior, reserved-word suppression inside that scoped prompt, and the label-response stop-versus-NUL return contract are now public.

**Current TALK scoped-prompt exit cleanup:** 2026-05-12 -
`systems/conversation.md`, `formats/tlk.md`, and extraction now cover the
observable scoped-prompt exit behavior: empty input inside the label prompt is
local to that prompt and reissues it, while top-level reserved words such as
NAME/JOB/BYE/THANK are suppressed before label-scoped keyword matching. The
label-response helpers' stop-versus-NUL return contract is now promoted, and
extraction marks the conversation runtime complete.

**Current TALK NPC-1 sentinel cleanup:** 2026-05-12 -
`systems/conversation.md`, `formats/tlk.md`, and `formats/npc.md` now specify
the corrupted-data edge for dialog index `1`. **Superseded 2026-08-22:** the
"leading sentinel id" reading is withdrawn. A `.TLK` header is a two-byte count
followed by that many id/offset entries with no sentinel row, and every id from
one to the count addresses a real blob — so index `1` is an ordinary, occupied
dialogue id rather than a corrupted-data edge. See `formats/tlk.md` Section 6.

**Current TALK warning-presentation cleanup:** 2026-05-12 - conversation, quest-flags, and extraction now split the opening conversation preamble from exit cleanup: Talk entry prints the description lead-in before greeting and only then applies the opening stolen-action warning check, while final cleanup's zero-sentinel stolen-action presentation is a fixed descending PC-speaker glissando followed by the already-specified one-signal reconciliation or random gold fallback. The warning presentation is now specified, and the shared sentinel producer path is covered by the town-entry active-slot audit.

**Current dungeon renderer provenance cleanup:** 2026-05-12 - `systems/dungeon-mode.md`, dungeon/tile formats, lighting, movement, tile catalog, and extraction now consistently describe the first-person dungeon renderer from the dedicated render trace: sparse point plotting from resident coordinate tables, not raycasting or continuous line drawing, with a binary torch/light-spell gate. This pass removed stale wireframe terminology and aligned provenance/status wording with the correction log. The previously asserted wind-tile torch-extinguish rule is resolved negatively for the analyzed baseline contact paths because the mapped movement and post-action tile-effect dispatchers do not identify a stock breeze contact branch, and the tile catalog now separates wind/gust graphics from any dungeon-contact claim. Dungeon L-Look now closes its focus-coordinate gap: it uses the shared relative ahead/right/left/here chooser, and Space/Pass aborts before tile description. `formats/dungeon-dat.md` now treats Search-revealed passages and wall/flavour rewrites as runtime behavior over preserved cell variants instead of a separate unresolved secret-door encoding. The later dungeon byte-visibility cleanup also separates class-sensitive `0x08` variant/overlay handling from persistent visibility memory.

**Current dungeon renderer helper cleanup:** corrected 2026-08-23 -
`systems/dungeon-mode.md` now publishes the backward pass at implementation
contract depth: `ITEMS` is the five-family, twenty-sprite dungeon-object bank;
each `MONn` resource is one named wandering-monster family with two poses and
three visible depths; energy-field subtype selects the pen while depth selects
the exact randomized stroke geometry; and normal-flavour decoration includes a
reachable transient state 5 with an exact 4/65 stage-0 gate. Earlier generic
Codex/Shadowlord active-object, quest-scene sprite-table, per-field geometry,
and five-state/clamped decoration readings are withdrawn. Mod-8 cell reads,
forward/backward sweep ordering, blocker and side-wall classification, and the
composite redraw bracket remain unchanged.

**Current dungeon presentation/input helper cleanup:** 2026-05-13 -
`systems/dungeon-mode.md` now covers the small DUNGEON overlay helpers around
the turn loop: viewport frame paint, level/facing status redraw,
render-and-poll key translation and blit cadence, dungeon active-object
initialisation, eight-attempt spawn placement on `0x6?`/`0x7?` cells, lazy
sprite-source loading, the Giant Spider/Slime upper-placement variant, and the
room-entry state snapshot before `DUNGEON.CBT` combat handoff. Exact
title/prompt text and movement feedback text are verified against DATA.OVL;
the eight wandering-monster names and `MONn` mappings are now closed in the
dungeon renderer contract.

**Current dungeon hazard/contact helper cleanup:** 2026-05-13 -
`systems/dungeon-mode.md` now promotes the remaining DUNGEON hazard/contact
helpers into clean prose: sleep fields are per-member one-shot contact hazards
that rewrite the live field cell to its visit marker, poison fields are
per-member repeat hazards, pit chains can immediately enter a room trigger
after landing, and the active dungeon monster uses wrapped randomized greedy
movement before the auto-facing dungeon-combat launch bracket. Exact direction
strings and distance-threshold parity remain verification-only items; the later
pit-chain handoff cleanup covers the off-bottom state mutation.

**Current dungeon attack/status verification cleanup:** 2026-05-13 -
`systems/dungeon-mode.md` now spells out the dungeon A-Attack handler as a
wrapped one-cell forward probe against the single active dungeon monster,
including the stock refusal path, the dungeon-combat launch handoff, and the
post-combat level-change result codes. The private DATA.OVL check also
confirms the four facing labels and fallback status label; the public spec
keeps those as presentation labels rather than a raw string table.

**Current timing/input helper cleanup:** 2026-05-13 -
`systems/timing.md` now names the calibrated busy-wait, hardware-tick wait, and
bounded prompt/input wait contracts without exposing ISR bytes or code-shaped
loops. `systems/input.md` now spells out the resident free-text reader's
printable-byte, Backspace, Enter, Escape, echo, and NUL-termination behavior.
These helpers remain presentation/input timing boundaries and do not advance
gameplay time.

**Current resident helper checklist cleanup:** 2026-05-13 -
The remaining ULTIMA helper checkboxes were reconciled against existing public
specs: the LZW bit reader belongs to `formats/lzw.md`/`formats/tiles.md`, the
trap resolver to `systems/traps.md`, the sky/status renderer to
`systems/moons.md`, the NPC/light refresh caller to `systems/visibility.md`,
and the global tile selector to `systems/animation.md`. `systems/input.md`
now also captures the direct-digit/navigation/confirm/cancel party selector.
The DOS exit/vector-restoration notes are startup/library glue and have no
gameplay spec target.

**Current remaining spec-checkbox audit:** 2026-05-13 -
The repo-wide unchecked `Spec` scan is now reduced to the function-note
template only. Aggregate SJOG and COMSUBS checklist rows were closed as
consolidated coverage in `systems/combat.md`, `systems/magic.md`, and related
command specs rather than as separate one-file-per-helper public specs.

**Current shrine presentation-effect cleanup:** 2026-05-13 -
`systems/karma.md` now captures the shared shrine/Word-of-Power presentation
primitive as a turbulent full-viewport flash plus low randomized PC-speaker
rumble with no direct quest-state mutation. The live CAST2 shrine state machine
remains the owner of ordained/Codex/standing changes; whether every successful
live shrine branch calls this exact helper is left as presentation parity, not
a separate state-machine gap.

**Current visibility classifier cleanup:** 2026-05-12 - `systems/visibility.md`, tile catalog, DATA.OVL, and extraction now describe the visibility carve as a queue-based centre-out helper rather than a per-cell ray caster, publish the ordinary propagation-blocker set plus the adjacent-only special-case propagation rule, and identify the 32x32 local-light mask refresh. The active-object compositor now covers direct companion-band branches and default-helper terrain remaps. The later marker/local-light cleanup resolved the dim/clear marker reader question, renderer grid-write parity, moongate-mask writer ordering, and the negative-light full-fill branch as a non-production compatibility path; remaining 2D visibility exactness is display-driver palette/art parity for marker bytes if required and external-reader synchronization policy. Dungeon visual exactness is owned by the dungeon-mode spec.

**Current magic metadata cleanup:** 2026-05-12 - `catalogs/spell-list.md`, `systems/magic.md`, `formats/data-ovl.md`, and extraction now separate the dense forty-eight-entry spell token, recipe, and scene-mask tables from the sparse resident long-incantation display phrase table. Recipe enforcement remains documented as M-Mix-time only; C-Cast consumes premixed charges and does not revalidate reagents.

**Current magic effect-boundary cleanup:** 2026-05-13 - `systems/magic.md`
now frames the former open section as boundary work. The public contract is
complete for the C-Cast dispatcher, parser, charge/mana/level gates, scene
masks, handler-family map, active-effect counters, arena field placement and
contact lifetime, shrine/urn split, and save-image ownership. Delegated
equipment, tile-label, and monster combat-AI details belong to their owning
specs and are mentioned here only as separation boundaries.

**Current magic monster-special ownership cleanup:** 2026-05-13 -
`systems/magic.md` and extraction now remove the stale implication that blink
and summon-daemon are unassigned magic variants. The analyzed baseline
possess/blink/summon-daemon row assignments are public in
`catalogs/monster-bestiary.md`; magic keeps only the separation boundary between
those combat-AI hooks and the forty-eight player spell handlers.

**Current save spell-charge cleanup:** 2026-05-12 - `formats/saved-gam.md`
now indexes the 48-byte premixed spell-charge stock by the canonical public
spell id in `catalogs/spell-list.md`: byte `0x024A + spell_id` stores the
counter used by both C-Cast and M-Mix. The stale external-reference caveat for
spell-charge slot enumeration has been removed.

**Current shop food/shipwright correction:** 2026-05-12 - `systems/shops.md`,
`catalogs/item-list.md`, and extraction now remove the stale claim that the
SHOPPES2 `F`/`S` flow is a food/provisions merchant. The traced `F`/`S` menu is
the shipwright Frigate/Skiff sale path, and its state byte is the outdoor
pending-vehicle queue. The tavern/meal-counter provision branch is now
specified as the confirmed food purchase route, including per-unit debit,
food-counter write, and partial-affordability behavior. Any separate provisions
merchant route remains unlocated.

**Current shop surcharge gate correction:** 2026-05-12 - `systems/shops.md`,
`systems/conversation.md`, `systems/quest-flags.md`, and extraction now stop
treating the random post-transaction surcharge gate as a dedicated shop-local
bypass flag. The helper checks shared town/conversation state also used by
active-player setup and theft cleanup. Town setup produces a no-slot marker or
one of three tracked town/Shadowlord slot indices; the shop and TALK cleanup
readers only test zero versus nonzero, so slot `0` allows the extra debit or
cleanup while the other known values suppress it. The current writer audit found
no non-town writer in the analyzed baseline.

**Current conversation action-letter cleanup:** 2026-05-12 -
`systems/conversation.md`, `systems/quest-flags.md`, `formats/tlk.md`,
`formats/saved-gam.md`, item/inventory catalogs, quest graph, and extraction now
publish the confirmed semantic effects for the global `0x86` action-letter
table: food, gold, keys, gems, torches, Grapple/Klimb gear, magic-carpet stock,
skull/special-key stock, Spyglass, Sextant, and Black Badge. The byte formerly
documented only as magic powder is now named as the Grapple/Klimb gear gate in
traced gameplay, with no separate magic-powder consumer confirmed. Conversation
now owns the fixed grant mechanics; quest graph validation owns shipped-data
reachability for branches that invoke them.

**~~Current screen-mode cell wording cleanup~~ (SUPERSEDED 2026-08-22):** 2026-05-12 - `formats/data-ovl.md` and extraction now avoid grouping the second resident dispatch cell with the display-driver ABI cell. That separation still holds, but the cell is the **disk-prompt / disk-error handler** cell, now owned by `systems/disk-prompt.md`; there is no "screen-mode controller".

**~~Current screen/prompt mode-state cleanup~~ (SUPERSEDED 2026-08-22):** 2026-05-13 - the "session-only, not a save-backed world flag" half was right. The rest is withdrawn: the dispatch input is the **required-disk index**, and the table it selects holds **drive letters**, not presentation state. There is no "per-mode setup/prompt branch table" left to decode. See `systems/disk-prompt.md`.

**Current disk-prompt cleanup:** 2026-05-13, corrected 2026-08-22 -
`systems/disk-prompt.md` specifies the disk request and retry layer: the
required-disk index selects a per-disk drive-letter entry, two historical alias
disk indices normalize onto the Britannia index, visible prompts are conditional
on that entry being the unknown marker, retry helpers bypass the prompt when the
drive is already known, and file semantics remain owned by
`systems/save-load.md`. The historical disk labels are now decoded and published
in `systems/disk-prompt.md`.

**Current write-error handler cleanup:** 2026-05-13, corrected 2026-08-22 -
`systems/disk-prompt.md` and `systems/save-load.md` identify the
dispatch cell's alternate resident target as the write-side critical-error
handler installed only around inner file writes; it prints a write-protect
message and waits for a key. There is no "per-mode setup/prompt table" left
open — that item is withdrawn.

**Current font high-bit caller-policy cleanup:** 2026-05-13 -
`formats/font-ch.md` and `formats/font-hcs.md` no longer treat high-bit
character handling as a font-format gap. Both formats define only the lower
seven-bit glyph range; `systems/text-output.md` owns the runtime rule that
ordinary cell output ignores high-bit bytes unless an adjacent extended-control
path consumes them. Their former open-question sections are now runtime
boundary sections, matching their complete format status.

**Current LOOK2.DAT open-heading cleanup:** 2026-05-13 -
`formats/look2-dat.md` no longer has an open-question section for the shipped
IBM PC baseline. Its former open-question text is now a variant boundary:
future variants should re-run the same validation rules against their asset and
should not treat different prose strings as new runtime semantics.

**Current weather ownership-boundary cleanup:** 2026-05-13 -
`systems/weather.md` no longer labels its active-object handoff as an open
weather question. Weather owns wind state, wind presentation, player-ship
gating, and eligible non-player water-actor cadence; the post-cadence movement
planner remains owned by `systems/active-objects.md`.

**Current conversation runtime-boundary cleanup:** 2026-05-13 -
`systems/conversation.md` no longer labels the runtime boundary section as open
work. The conversation byte-runner contract has no tracked runtime gap there;
remaining conversation-adjacent packing questions are delegated to the owning
format or quest-state specs.

**Current QUESTION.DAT variant-boundary cleanup:** 2026-05-13 -
`formats/question-dat.md` no longer frames absent markup edge cases as shipped
format open work. The spec now treats repeated markers, terminal markers, and
high-bit bytes as strict-mode asset-validation failures for variants, not as
new runtime semantics for the baseline questionnaire.

**Current lighting/TLK boundary-label cleanup:** 2026-05-13 -
`systems/lighting.md` now labels its sentinel-writer caveat as an evidence
boundary rather than an open lighting question. `formats/tlk.md` now labels its
verified file-structure handoff to conversation runtime as a validation
boundary rather than an open-question section.

**Current Search trap caller-boundary cleanup:** 2026-05-13 -
`systems/traps.md`, `systems/containers.md`, and `systems/commands.md` no
longer carry the stale “untraced caller-side trap selection table” residual for
Search. The former trap probe is now described as an active-object coordinate
lookup returning the matched slot's tile/type byte; Search and containers own
the feature narration, chest pools, and pickup staging, while `traps.md` owns
only the shared party-effect resolver.

**Current M-command split cleanup:** 2026-05-13 -
`systems/commands.md` no longer treats the M-family shrine split as open work.
The command summary now separates ordinary CMDS reagent mixing from CAST2's
shrine/urn entry handler, which internally dispatches to virtue meditation or
Codex urn reading as specified by `systems/magic.md` and `systems/karma.md`.
The private CMDS `0x1202` mantra-style meditate note is tracked as an
unreachable Yell-era branch, not an alternate M-command route.

**Current OOL open-item cleanup:** 2026-05-13 -
`formats/ool.md` no longer lists the entry-mode-gated `UNDER.OOL` re-flush as
an open question. The file-side branch is already specified; remaining `.OOL`
open work is limited to naming, uncommon auxiliary byte meanings, mirror-file
reader census, and underworld population provenance.

**Current balloon negative-boundary cleanup:** 2026-05-13 -
`systems/vehicles.md`, `systems/movement.md`, `systems/overworld.md`, and
`catalogs/tile-catalog.md` now keep balloon claims at the art/manual boundary:
the traced B-Board and movement-marker contracts do not publish a balloon
boarding branch, live transport marker, landing rule, or wind-drift rule.
Later vehicle/item cleanup extends that negative boundary across X-Xit, U-Use,
shipwright delivery, ordinary movement, item-list, and extraction: for the
analyzed baseline, balloon is preserved as art/catalog data rather than modeled
as an unspecified live vehicle.

**Current inventory runtime-boundary cleanup:** 2026-05-13 -
`systems/inventory.md` no longer labels the magic-ring and Amulet/Turning
negative evidence as an open inventory question. Ring vanish/regeneration and
Amulet/Turning effects remain combat/readied-slot boundaries; the remaining
inventory U-Use exactness is delegated to item-specific rows in
`catalogs/item-list.md` and `systems/view.md`; dialogue reactions to carried or
worn story items are quest-graph branch-validation work. The
section heading now treats shared stock/R-Ready behavior as complete at
inventory-system depth and names item-specific U-Use exactness as the residual.

**Current SIGNS.DAT macro-boundary cleanup:** 2026-05-13 -
`formats/signs-dat.md` now names the formatter macro selector range
`0x29..0x31` and frames exact decoration fragment identities as visual-parity
work that must not copy shipped sign text or resident string dumps into the
clean spec. The separate scene/coordinate inventory remains a future
source-free content pass.

**Current SIGNS.DAT content-boundary cleanup:** 2026-05-13 -
`formats/signs-dat.md` now treats scene-directory lookup,
coordinate-record scanning, alias bridges, formatter controls, pause handling,
high-bit presentation toggles, and wanted-poster separation as complete
reader-depth coverage. Remaining work is explicitly source-free content
cataloguing: macro decoration identities and the scene/coordinate inventory
without copied shipped sign text.

**Current input variation-boundary cleanup:** 2026-05-13 -
`systems/input.md` now separates input-backend variation from true open work.
NumLock top-row digit promotion, unused remapped function-key codes, prompt-byte
consolidation, and blink-counter sharing are compatibility/backend boundaries;
the remaining input-facing open work is the full recognised set for the
entry-mode hint stamp beyond the observed town case. The section heading now
names that entry-stamp gap directly.

**Current text-output gate/eraser cleanup:** 2026-05-13 -
`systems/text-output.md` now includes the resident typed-input space eraser used
for destructive Backspace and Escape-clears, and it reframes the old
cursor-advance writer question as presentation-state ownership. Confirmed gate
users are cursor blink painting, typed-input erase/padding, and intro-frame
cell decoration; remaining exactness is pixel parity, not gameplay state.

**Current time boundary cleanup:** 2026-05-13 -
`systems/time.md` separates mode-zero recompute caller-census from fixed
compatibility boundaries: the thirteen-month calendar, prompt/idle
non-advancement, year-overflow policy, and `Q`/`T` state-tag effects are no
longer framed as open time-system questions. Later cleanup bounds the caller
census to traced mode-loop families and any obscure direct callers.

**Current DUNGEON.DAT format-boundary cleanup:** 2026-05-13 -
`formats/dungeon-dat.md` no longer labels the fixed file layout as open. The
format contract is complete at byte-layout depth; remaining lower-nibble names
belong to runtime consumers such as dungeon rendering, doors, traps, and field
handlers, while custom room-id persistence is variant-content policy.

**Current CBT format-boundary cleanup:** 2026-08-27 - the fixed layout and all
traced runtime consumers are closed. Bytes outside the published outdoor and
dungeon slices have no traced reader and are preserved without invented
semantics. Arena edges are geometric, the dormant outdoor shuffle has no live
caller, and the live dungeon ambush synthesis/caller/PRNG contract is published
in the combat and dungeon-mode specs.

**Current NPC format-boundary cleanup:** 2026-05-13 -
`formats/npc.md` now labels blank location names and sprite-class labels as
catalog/naming work. The `.NPC` format contract is complete at file-structure
depth: file size, sub-map stride, schedule stride, slot-zero sentinel,
waypoint selection, AI-byte behaviour values, type-byte occupancy, and
dialog-index binding are covered.

**Current NPC roster catalog cleanup:** 2026-05-13 -
`catalogs/npc-roster.md` and extraction now treat schedule `m0..m7` AI/mode
byte meanings as covered by `systems/npc-schedules.md` and `formats/npc.md`.
The roster now includes a public scene/place crosswalk for all thirty-two
town-mode scene keys, preserving blank resident-name rows as stable unnamed
keys, and a complete occupied tag-byte catalogue with conservative role labels.
The punctuation-only `CASTLE:1` slot is now treated as an authored display
entry to preserve rather than a missing name. The roster row is now complete at
roster-catalog depth; source-free keyword graph integration belongs to
quest/conversation catalog validation.

**Current NPC schedule-boundary cleanup:** 2026-05-13 -
`systems/npc-schedules.md` now frames the former variation list as plot-data
and runtime-exactness boundaries. Roster loading, hour-to-waypoint selection,
runtime block ownership, cached-waypoint transition memory, per-turn walking,
boundary state handling, pathfinding workspace construction, dynamic-obstacle
avoidance, floor-link marker handling, sprite placement, persistence omission,
state-8 parked off-floor semantics, hidden-mask visual suppression distinct
from the activation/death mask, hardcoded dynamic-obstacle radius, exact
scene-byte file/sub-map indexing, stairway route-selection ownership, and
town/rest invocation cadence are public at scheduler depth. Remaining NPC
scheduler work is long-stall visual parity only if later observed. The system
inventory row now uses the
same former partial boundary instead of the older first-slice label.

**Current NPC out-of-town ownership cleanup:** 2026-05-13 -
`systems/npc-schedules.md` and extraction now separate town-mode `.NPC`
schedules from out-of-town actors. Outdoor monsters, vehicles, whirlpools,
and world props are active-object/overworld users with no `.NPC` schedule,
waypoint selector, AI-mode byte, runtime descriptor, or flood-fill queue.
Title-signature motion is intro/display path data. Remaining NPC scheduler
work is low-visibility presentation/catalog parity, not an outdoor scheduler
variant.

**Current NPC hidden-mask cleanup:** 2026-05-13 - `systems/npc-schedules.md`,
`systems/town-mode.md`, and extraction now separate the two per-scene NPC masks:
the town activation/death mask decides whether a rostered slot enters the
scheduler, while the hidden-NPC mask only changes the sprite tile for an
already-active, linked NPC. The shipped hidden-mask catalogue now names the
nonempty public scene/slot rows: Moonglow, Minoc, Trinsic, Stonegate, and The
Lycaeum. The later hidden-role cleanup closes the anonymous-slot label
boundary through the roster catalog.

**Current NPC hidden-role cleanup:** 2026-05-13 -
`systems/npc-schedules.md`, `catalogs/npc-roster.md`, and extraction now close
the anonymous hidden-actor naming gap: unnamed hidden slots use the conservative
sprite-tag role labels already published in the roster catalog, and no hidden
mask has an additional scheduler behavior behind those labels. Remaining NPC
scheduler work is presentation parity only: long-stall visibility if later
observed.

**Current NPC long-stall cleanup:** 2026-05-13 -
`systems/npc-schedules.md` now distinguishes the short stuck-counter replanning
threshold from the high-range stall guard. The gameplay contract is that more
than three failed-progress ticks invalidates the active move queue and clears
the counter. The higher guard prevents runaway accumulation and passes through
a last-resort stalled-actor helper; no separate durable gameplay state is
currently specified for it, and no alternate scheduler/pathfinding state is
assigned to that helper. Remaining work is visual/sound parity only if that
helper proves presentation-visible.

**Current NPC stairway-ownership cleanup:** 2026-05-13 -
`systems/npc-schedules.md` now states the ownership split directly: the
scheduler selects routes to floor-link markers, while town movement and the
location tile catalogue own visible stairway facings and player-facing
floor-change presentation. The later stair-facing cleanup publishes the
`0xC4..0xC7` facing-sensitive town stair contract, so this is no longer an NPC
route-selection gap.

**Current town stair-facing cleanup:** 2026-05-13 -
`systems/town-mode.md`, `systems/doors-and-z-transitions.md`,
`formats/location-dat.md`, `catalogs/tile-catalog.md`, and extraction now
publish the town stair family as `0xC4..0xC7`: low two bits select the
authored facing in the town movement wrapper's normalized direction space;
entering along that facing moves up, entering from the opposite facing moves
down, and side crossings do not change floors. NPC schedules retain only route
selection to floor-link markers.

**Current NPC radius/index cleanup:** 2026-05-13 -
`systems/npc-schedules.md` now treats the dynamic-obstacle overlay radius as a
hardcoded compatibility constant: only active objects or the player at
destination-relative Manhattan distance less than four are stamped as
obstacles. The spec also now states the exact `.NPC` roster selector formula:
`(scene - 1) >> 3` chooses the file family and `(scene - 1) & 7` chooses the
sub-map, while gameplay keeps the original one-based scene id.

**Superseded 2026-08-22:** "block/floor stride" below refers to the withdrawn
per-location block-stride model. A class file is a flat sixteen-page array and
the entry page comes from the per-scene base-page table published in
`formats/location-dat.md` Section 4.1; it is not twice the sub-map index.

**Current location DAT format-boundary cleanup:** 2026-05-13 -
`formats/location-dat.md` now separates the fixed per-class location file
layout from catalog, validation, and visual-parity work. File partitioning,
block/floor stride, signed floor-page selection, marker harvest, dawn/dusk
substitution, cosmetic variation, NPC floor-link markers, and `MISCMAPS.DAT`
sectioning are file/runtime contract; reachable-floor inventory, secret-room
tile lists, marker-roster audits, and Return-to-View helper pixels remain
separate work.
The extraction table now treats the four per-class location tile-grid files as
complete at base layout depth and `MISCMAPS.DAT` as complete at file-layout and
command-stream depth; resident display-helper pixel parity remains runtime
presentation work.

**Current BRIT.DAT format-boundary cleanup:** 2026-05-13 -
`formats/brit-dat.md` now states the sparse Britannia map-file layout boundary:
stored block count/size, chunk-index table use, all-water synthesis, coordinate
wrapping, tile-byte preservation, static terrain ownership, and loader
live-buffer substitution are fixed. The extraction row is now complete for the
map-file layout; remaining transition-coordinate, encounter, tile-catalog, and
mutation-audit items are runtime/catalog work.

**Current UNDER.DAT format-boundary cleanup:** 2026-05-13 -
`formats/under-dat.md` now mirrors the same boundary for the dense Underworld
map-file layout: direct chunk ordering, fixed file size, coordinate wrapping,
tile-byte preservation, static terrain ownership, and shared loader
live-buffer substitution are fixed. Remaining ascent/dungeon/scripted
transition, encounter, tile-catalog, and mutation-audit work is runtime/catalog
scope.

**Current TLK format/interpreter cleanup:** 2026-05-13 -
The extraction table now treats `CASTLE.TLK`, `KEEP.TLK`, `TOWNE.TLK`, and
`DWELLING.TLK` as complete for file grammar and conversation interpreter
contract: per-class selection, header/count/sentinel layout, fixed-window blob
loading, obfuscation, mandatory entry order, keyword-pair grammar,
reserved-keyword split, byte-runner/control semantics, and dictionary
substitution are public. Remaining catalog reachability checks stay in
quest-graph validation.

**Current graphics archive format-boundary cleanup:** 2026-05-13 -
The extraction table now treats `TILES.16`/`TILES.4` and the paired `.16`/`.4`
graphics archive family as complete at archive-decoding depth. `formats/tiles.md`
and `formats/lzw.md` cover the LZW envelope, flat atlas layout, image-directory
layouts, sprite-and-mask layout, EGA/CGA pixel encodings, sprite mask polarity,
body-size checks, file roster, and the resident miniature tile-glyph boundary.
Remaining per-id visual attribution, per-slot semantic naming, scene-palette
policy, and renderer slicing conventions stay in catalog/renderer work.

**Current NPC overlay boundary cleanup:** 2026-05-13 -
The extraction table now treats `NPC.OVL` as complete at scheduler/pathfinding
contract depth: roster loading, scene-to-file/sub-map arithmetic, runtime
initialization, hour-to-waypoint selection, town/rest-loop walker cadence,
boundary states, flood-fill queue replay, dynamic obstacles, floor-link marker
goals, hidden-sprite masks, active-object linkage, and persistence omission are
public. The stale `formats/pth.md` cross-reference was removed because `.PTH`
is title-signature data, not NPC scheduling. Remaining role labels and
low-visibility helper polish stay in roster/presentation validation.

**Current town overlay tracker cleanup:** 2026-05-13 -
The extraction table now replaces the stale `TOWN.OVL` verified-slice status
with a complete behavioral-contract boundary. The town loop, entry/load, marker
harvest, dawn/dusk rewrite, cosmetic variation, movement/floor/exit
transitions, Open and Attack hooks, alarm/arrest cleanup, scheduler integration,
active-object ownership, free-roaming object movement, and save/load entry
reconstruction are public. Stonegate presentation-asset parity, authored
secret-location inventory, and rare nested script-return checks remain
presentation/data/empirical work.

**Current town secret-location boundary cleanup:** 2026-05-13 -
`systems/town-mode.md` and extraction now stop treating hidden rooms as a
separate town-mode mechanism. Search-revealed passages, P-Push blockers,
hidden pickups, and floor transitions are covered by their owning command,
door, container, and transition specs. Remaining work is only an authored
secret-location inventory for parity atlases.

**Current town exit-threshold cleanup:** 2026-05-13 -
`systems/town-mode.md`, `systems/doors-and-z-transitions.md`, and extraction
now publish the traced town-family exit threshold as tile id `0x59`: accepting
its prompt clears the scene byte, writes the exterior coordinate from the
per-scene tables, clears the town-local state latch, and selects the
underworld plane only for scene `0x19`. Boundary-tile cataloguing is no longer
a town-mode remaining gap.

**Current town Stonegate scene-binding cleanup:** 2026-05-13 -
`systems/town-mode.md` and extraction now correct the old Lord-British
audience-pending label. The entry-time presentation path belongs to
Stonegate's setup path, while Lord British's Castle keeps only the basement
chord hook in town mode. This pass fixed scene ownership; the later producer
cleanup below fixes the state-source model.

**Current town Stonegate producer cleanup:** 2026-05-13 -
`systems/town-mode.md`, `catalogs/quest-graph.md`, `formats/data-ovl.md`, and
extraction now replace the stale Stonegate trigger-queue model. Stonegate entry
presentation is produced by the Sceptre carried-item flag for one prelude row
and by the three Shadowlord hideout slots for per-living-Shadowlord "air of"
rows. Remaining Stonegate work is presentation-asset/tone parity, not producer
identity or an audience mechanism.

**Current outdoor overlay tracker cleanup:** 2026-05-13 -
The extraction table now replaces stale verified-slice labels for
`MAINOUT.OVL` with a boundary later promoted to complete and `OUTSUBS.OVL` as complete
at overlay-helper contract depth. Outdoor scene entry, redraw/chunk refresh, sparse/dense chunk loading, live-buffer
substitutions, movement commit, special underfoot latch, confirmed surface
chasm fall, active-object per-turn handling/setup, encounter probe inputs,
ship-combat trigger, save/object-overlay ownership, mode hooks, per-turn
cleanup linkage, town-entry checks, and the outdoor-camp Lord British level-up
service are public. Later cleanup covers the saved-slot natural moongate
live-tile schedule and live entry path; encounter payloads, tile names,
timing/transport outliers, and chunk-substitution labels are catalog,
opaque-data, or QA work.

**Current outdoor pendulum cleanup:** 2026-05-13 -
`systems/overworld.md` and extraction now align on the traced outdoor
active-object/encounter cadence gates: `T` skips the epilogue, `Q` alternates
it through one local pendulum, and the traced horse/carpet transport-marker
pairs alternate it through a second local pendulum. Remaining work is
writer/catalog ownership for unusual state tags and transport markers, not an
unresolved encounter-suppression or double-roll rule.

**Current endgame gap cleanup:** 2026-05-13 -
`systems/endgame.md` and extraction now name the remaining endgame work
concretely: exact character-animation pose mapping for the terminal
tableau/follow helper, display-helper taxonomy, and resource-slot/panel parity.
The terminal sequence, Doom final-room handoff route, Sandalwood Box gate,
two-prompt confirmation with final-answer-plus-flag branching, final `END.DAT`
presentation, certificate date/elapsed-time calculation, and no-return final
loop remain public. The system inventory row now uses this same detailed
former partial boundary instead of the older visual-helper-only wording.

**Current endgame confirmation cleanup:** 2026-05-13 -
`systems/endgame.md` and extraction no longer carry first-confirmation
live-branch verification as an endgame gap. The public contract keeps both
visible confirmations and their echoed answers, but the branch into the victory
rite is specified from the final confirmation plus the saved Sandalwood Box
flag.

**Current OOL format-boundary cleanup:** 2026-05-13 -
`formats/ool.md` now separates the fixed object-overlay table layout and
load/save lifecycle from runtime caller census and uncommon object-family
auxiliary-byte meanings. The remaining `.OOL` work is mirror-reader inventory
outside the traced OUTSUBS transition paths, underworld population sources, and
rare family-specific byte roles, not record shape or mirror-write order.

**Current OOL mirror-reader cleanup:** 2026-05-13 - `formats/ool.md`,
`systems/save-load.md`, and extraction now promote the traced OUTSUBS
mirror-file consumers: the world-plane filename helper selects `BRIT.OOL` or
`UNDER.OOL`, town-entry passes that selected mirror into resident object-table
refresh/setup before scene handoff, and the confirmed falls transition names
both per-plane mirrors while changing to the underworld plane. Remaining
mirror-reader work is any caller outside those traced overworld transition
paths.

**Current main-loop disk-prompt cross-reference cleanup:** 2026-05-13 -
`systems/main-loop.md` no longer describes between-mode disk handling as a
generic file-probe callback. The outer loop now delegates visible disk-prompt
state to `systems/disk-prompt.md` and read/write retry semantics to
`systems/save-load.md`, preserving only the between-mode boundary at this
layer.

**Current KARMA.DAT selector cleanup:** 2026-05-13 - `formats/karma-dat.md`, `systems/karma.md`, `systems/rest-and-camp.md`, and extraction now publish both traced verdict selectors: Blackthorn rescue/refuge selects records zero through four, while the Lord British-in-disguise camp event selects records zero through three for lower bands and the sixth record for the top band. The stale shrine-side `KARMA.DAT` caller gap has been removed; traced shrine/urn paths use shrine-local text and `MISCMSG.DAT`.

**Current Sandalwood Box cleanup:** 2026-05-12 - item-list, quest-graph, containers, endgame, tile-catalog, and extraction now identify the static castle pickup route: Saduj's hostile conversation remains a clue, while the non-speaking `CASTLE:0` object slot 31 at local `(18,12,2)` with tag `0x0E` is the Get-compatible pickup that dispatches the shared inventory-add writer and sets the save-backed Sandalwood Box flag read by the endgame. No traced acquisition handler requires Saduj's conversation as a mechanical prerequisite.

**Current New Order cleanup:** 2026-05-12 - `systems/commands.md`, `formats/saved-gam.md`, and extraction now publish N-New Order as a whole-record active-party swap: cancel paths do not consume a turn, slot zero must remain leader, same nonzero slot self-swaps are accepted and consume the turn, party size is unchanged, and non-leader roster identity is current record order rather than immutable factory slot index.

**Current Yell cleanup:** 2026-05-12 - `systems/commands.md` and extraction now publish Y-Yell as three visible command families: shipboard sail toggling, Shadowlord-name encounter setup, and Word-of-Power utterance/live-tile transmutation. The abandoned mantra-style Yell branch is documented as unreachable from the shipped word table. The traced per-word scratch marker has no identified live reader, so the public contract treats it as non-contractual bookkeeping rather than save-backed quest progress or a repeat-utterance gate.

**Current X-it vehicle cleanup:** 2026-05-12 - `systems/vehicles.md`, `systems/doors-and-z-transitions.md`, movement, and extraction now align X-Xit with the dedicated CMDS handler notes: successful exits park the abandoned vehicle at the party's current cell, not at a searched landing cell; horse, carpet, skiff, furled-ship, hoisted-sail refusal, carried-skiff launch, stowed-carpet redeploy, and the four-cell nearby landing-support predicate are covered. Ordinary vehicle terrain-query families are now named through the shared movement dispatcher, including exact accepted static tile ranges for foot/avatar, horse, carpet, ship, and facing-sensitive skiff queries. B-Board object-byte to transport-state transitions are now public for horse, carpet, ship, and skiff, and the ship-boarding carpet edge is now narrowed to accepted north/east carpet markers `0x14`/`0x15`. Later balloon cleanup treats balloon as art/catalog data rather than live vehicle behavior for the analyzed baseline; remaining vehicle exactness is transport/action values outside the known ranges and vehicle art-frame naming.

**Current movement/passability cleanup:** 2026-05-12 - a new
`systems/movement.md` specifies the shared movement layer: cardinal direction
routing before A-Z command dispatch, mode-specific destination sampling,
world/town base terrain bitset shape, caller-query tile-class dispatcher
boundary, vehicle layering, the separate NPC pathfinding bitmap/ranges,
dynamic occupancy,
and commit/redraw rules. Tile catalog, DATA.OVL, NPC schedule, vehicle,
overworld, town-mode, and extraction docs now use the corrected resident
terrain bitset plus caller-query dispatcher model instead of the stale
per-mover matrix wording, and NPC scheduling now explicitly stays outside the
foot/avatar terrain-query family. The foot/avatar, horse, carpet, ship, skiff,
non-vehicle active-object predicate families, and NPC pathfinding families are
now named at predicate-family depth, with exact accepted static tile ranges
where applicable. The lava/chair compatibility edge is now tied to LOOK2 tile
names: `0x8F` is molten lava and `0x90..0x93` are chair variants.
Remaining exactness is final art/catalog naming for the still-generic
non-vehicle query families; movement now names the families already identified
by the encounter and bestiary specs.

**Current rest/camp cleanup:** 2026-05-12 - a new
`systems/rest-and-camp.md` specifies H-Hole-up scene routing, outdoor camp and
town bed gates, the hours prompt boundary, repeated simulated-time rest loop,
interruption/ambush handoff, party recovery, and the Lord British-in-disguise
outdoor camp-event level-up. The older OUTSUBS generic camp/save identity is
kept only as a superseded structural note; the public contract now treats that
function as the camp-event stat reward, not a throne-room Talk path.
Low-level CMDS alternate setup presentation helper identity after sleep-ambush
row selection is now presentation QA, while later ambush-branch and rest/watch
cleanup pins message/status-restoration ordering, duration/watch prompting,
Good-status watcher validation, and the dungeon rest/camp alternate handoff.
The alternate setup target is pinned to the CMDS H-Hole-up helper rather than
SJOG or a separate scripted-fight dispatcher.

**Current combat placement-shuffle cleanup:** 2026-08-27 - `systems/combat.md`,
`systems/dungeon-mode.md`, `systems/rest-and-camp.md`, and `EXTRACTION.md`
separate the dormant fifteen-full-range-swap terrain branch from the live
sixteen-swap dungeon wandering-monster synthesis and the CMDS rest/camp path.
The sole terrain caller leaves its branch inactive; both live dungeon callers,
PRNG order, banner boundary, and deterministic state-zero vectors are public.

**Current hourly food/status cleanup:** 2026-05-12 - `systems/time.md`,
`systems/rest-and-camp.md`, and extraction now specify the shared hourly
status/provision cadence. Food is decremented only on observed hour crossings
to 06:00, 12:00, and 18:00, by the count of active party members who are not
Dead or Sleeping, with a floor at zero. Zero food on any observed hour crossing
triggers the starvation warning and living-party random damage. H-Hole-up does
not own a separate food decrement rule; its repeated cleanup calls merely
cross hours that the shared time cadence observes.

**Current town rest-hours cleanup:** 2026-05-12 - `systems/rest-and-camp.md`,
`systems/time.md`, and extraction now correct the town bed H-Hole-up hours
path: it accepts one nonzero digit, runs one bounded sixteen-pass NPC
schedule/world-tick burst, then advances elapsed rest in repeated ten-minute
cleanup calls until the target hour or thrown-out branch. The previous
"sixteen NPC ticks per requested hour" wording was a scratch-note overread and
has been removed.

**Current Blackthorn cleanup:** 2026-05-12 - a new
`systems/blackthorn.md` specifies the BLCKTHRN capture audience, local
cutscene script VM, the four-prompt mantra interrogation, the failed-demand
punishment beat, rescue/refuge restoration sequence, `MISCMAPS.DAT` /
`MISCMSG.DAT` / `KARMA.DAT` data boundaries, the rescue five-band verdict
selector, temporary cinematic active-object reuse, durable shrine-ruin /
roster-removal / moral-standing / progression state, and post-scene handoff
coordinates. (Corrected 2026-08-22: this entry previously said "four-question
challenge shape" and "durable jail/progression state". There are no jail flags;
the eight-byte band is the shrine ruin flags, the four prompts are four
wordings of one question, and the punishment is an irreversible execution.) Later challenge-table, script-VM, audience-entry, and
status passes complete the BLCKTHRN overlay contract at cinematic depth. Any
formerly remaining caller-predicate and pixel-level tile/output questions are
now closed by later 2026-08-27 passes; the supposed output bytes are pause
counts and do not enter the text system. Those passes also correct the actor
roles from a mobile Blackthorn/attendant pair to two guards plus a distinct
seated-Blackthorn tableau.

**Current shop surcharge cleanup:** 2026-05-12 - `systems/shops.md` and
extraction now distinguish quoted headline prices from the traced
post-transaction surcharge: most successful paid shop transactions can subtract
an additional random `1..64` gold from the shared party gold word after the
ordinary affordability gate and main debit. Superseded by the later surcharge
gate correction for the exact gate identity.

**Current DATA.OVL combat-class cleanup:** 2026-05-12 -
`formats/data-ovl.md` and extraction now publish the clean table shape for the
shared combat-class metadata: a fixed 48-row, eight-byte class table used across
party, special actor, NPC-role, and monster classes, plus adjacent per-class
flags modeled as traits rather than scripts. The row fields are now named as
combat tier, speed seed, HP-comparison byte, defense rating, attack cap,
maximum HP, spawn count, and kill/drop cap. The later monster-bestiary stat-row
cleanup publishes the hostile/special per-row values and confirms both monster
identity gaps as all-zero unnamed rows; remaining class-table exactness is
limited to unnamed flag bits. The later ranged/effect side-table cleanup
publishes the selector, payload, and scene-resistance row values.

**Current monster stat-row cleanup:** 2026-05-13 -
`catalogs/monster-bestiary.md` now publishes the full eight-field stat rows for
hostile and special combat classes, including tier, speed, endurance rating
(published as "team-flip HP byte" in the original entry; that name is
withdrawn), defense, attack cap, HP, spawn count, and drop cap. The older wording that class
43 had unresolved nonzero stat bytes is corrected: classes 42 and 43 are both
unnamed all-zero reserved rows in the analyzed table.

**Current combat grouping cleanup:** 2026-05-12 - `systems/combat.md` and
extraction now publish the slot-to-group faction helper at a clean behavioral
level: ordinary party and monster actors start in opposite groups, a low
team-toggle flag can invert that default for charm-like effects, and the
Saduj override is a literal roster-name data rule: any party-class combat actor
whose referenced roster name has lowercase `j` as its fifth character is forced
into the monster-side group during target selection. The stock initial roster
uses that edge for Saduj, but custom or edited roster entries should retain the
same compatibility behavior.

**Current LZW cleanup:** 2026-05-12 - a new `formats/lzw.md` makes the shared
paired-graphics LZW envelope available as its own clean format contract:
four-byte decoded
length, GIF-style variable-width code stream, clear/end codes, 9-to-12-bit
growth, LSB-first packing, decoded-length validation, and explicit separation
from driver-compressed `.BIT` / `.PCS` resources. `formats/tiles.md` remains
the owner of post-decompression graphics containers.

**Current endgame file-read cleanup:** 2026-05-12 - `systems/endgame.md`,
`systems/save-load.md`, `formats/end-dat.md`, and extraction now reflect the
later `read_file_seek` correction: the endgame retry wrapper sits above a
generic file-read helper, and `END.DAT`, `MISCMAPS.DAT`, `ENDMSG.DAT`, save
images, and `.OOL` files are plain on disk rather than LZW-decoded by that
path.

**Current moongate animator cleanup:** 2026-05-12 - `systems/overworld.md` and
extraction now correct the natural-moongate animator scratch-input shape: four
coordinate words plus one phase byte, with all-ones sentinels for missing
origin/destination and a render-frame animator that marks visibility dirty
before stamping frames into the rendered tile buffer. The same pass now
separates the fixed overworld narrative gate branch from the saved-slot
live-terrain refresh and the live entry hook later traced in MAINOUT. The
previously suspected gameplay body is now resolved as display-only sky/status
row refresh.

**Current moongate scratch-reuse cleanup:** 2026-05-13 - overworld, DATA.OVL,
and extraction docs now state that the coordinate words consumed by the
moongate animator are shared mode-local scratch. Current writer coverage shows
chunk-loader scroll-position reuse, town bright-light beacon-coordinate reuse, and
combat phase-byte reset, not the traced saved-slot live-terrain refresher, so
the public contract no longer treats those words as durable natural-moongate
schedule storage.

**Current natural-gate schedule boundary cleanup:** 2026-05-13 -
`systems/overworld.md` and extraction now specify the saved-slot
live-terrain placement/waning schedule and the later traced live entry hook.
The public contract keeps the traced animator, scratch reuse, fixed
ordained-bitmask narrative branch, saved Moonstone slot refresh, and entry
handling separate.
The corrected hour-change moon/status renderer rules out the older surface-only
gameplay-hook hypothesis. The follow-up time/moon cleanup promotes
Time/calendar/moons to complete by treating entry as overworld transition work,
not as a clock, calendar, or status-strip display gap.

**Current ship-fire durability cleanup:** 2026-05-12 - `systems/vehicles.md`, `formats/ool.md`, `systems/active-objects.md`, and extraction now align ship hull/skiff state across boarding, X-it parking, shipwright delivery, and broadside fire: ship/frigate active-object byte `+5` is hull condition, byte `+7` is skiffs aboard, purchased Frigates start at hull `100` with two skiffs, boarding warns below ten hull, and broadsides subtract `1..20` from target byte `+5`. Superseded by the later broadside byte cleanup for non-ship hit semantics.

**Current broadside byte cleanup:** 2026-05-12 - vehicles, active-object, OOL,
and extraction docs now specify broadside hit resolution for all struck active
objects: F-Fire treats byte `+5` as an unsigned depletion counter, subtracts
`1..20`, and clears the slot when the subtraction wraps into the high-bit
range. Ship/frigate targets therefore lose hull condition, while non-ship
families keep their ordinary class-specific byte meaning outside the F-Fire hit
boundary.

**Current OOL auxiliary-byte cleanup:** 2026-05-13 - `formats/ool.md` and
extraction now separate confirmed persisted active-object roles from remaining
unknowns: ship/frigate byte `+5` is hull condition, byte `+7` is skiffs aboard,
F-Fire applies the generic byte-`+5` depletion rule to struck objects, and byte
`+6` is the packed animator phase/direction byte. The remaining OOL exactness
is uncommon family-specific meanings for bytes `+5` and `+7` outside those
roles.

**Current party-selector cleanup:** 2026-05-12 - `systems/input.md` and extraction now publish the shared party-member selector contract: active-party slot selection is zero-based internally, cancel and explicit-none are distinct negative results, most callers collapse negative results to no target, and the wrapper echoes the selected displayed name or none result.

**Current Codex urn cleanup:** 2026-05-12 - `systems/karma.md`, `systems/magic.md`, `catalogs/quest-graph.md`, `catalogs/tile-catalog.md`, `formats/miscmsg-dat.md`, and extraction now publish the M-command shrine/urn split and the Codex urn's quest-mask role: ordained virtues become Codex-read when the corresponding urn/page is read, then shrine return clears ordained and leaves Codex-read as the completed marker. The old tile-catalog claim that stepping onto a shrine directly triggers meditation was removed.

**Current resurrection cleanup:** 2026-05-12 - `systems/magic.md`, `systems/shops.md`, `catalogs/item-list.md`, and extraction now publish the shared resurrection helper's clean contract: Dead-only gating, spell/scroll revival to Good with 1 current HP, class-based mana rebuild, conditional experience rescale, level recomputation, maximum HP as thirty times recomputed level, and the healer distinction that paid resurrection invokes those side effects but then restores current HP to maximum.

**Current heal-helper cleanup:** 2026-05-12 - `systems/magic.md`, `catalogs/spell-list.md`, `catalogs/item-list.md`, and extraction now publish the low-circle restore helpers: Awaken scans the roster and wakes only the first Sleeping member found, Cure prompts for one member and only changes Poisoned targets back to Good, and selected-member Heal skips only Dead status, leaves status unchanged, adds HP from an inclusive 0..60 roll halved with integer truncation and floored to one, clamps at maximum HP, and marks stats dirty. Great Heal is separated as the selected-member full-current-HP restore path that refuses Dead targets and the dungeon combat-active substate.

**Current Locate/Sextant cleanup:** 2026-05-12 - `systems/magic.md`, `catalogs/spell-list.md`, `catalogs/item-list.md`, and extraction now publish the shared coordinate-printer contract for In Wis Locate and Sextant-style output: split each party coordinate into nibbles, map 0..15 to `A`..`P`, print Y before X, and keep the effect display-only.

**Current spell-direction cleanup:** 2026-05-12 - `systems/input.md`, `systems/magic.md`, `systems/weather.md`, and extraction now publish the shared spell direction prompt: world scenes start from party position, combat scenes start from the active combat actor targeting coordinate, cardinal choices cache the adjacent target and echo a direction label, Space is the visible `Pass`/no-direction result, and other keys re-prompt. Wind Change wording now uses Space/Pass as the no-effect route rather than Escape.

**Current magic Open/Unlock door cleanup:** 2026-05-12 - `systems/magic.md`, `systems/doors-and-z-transitions.md`, and extraction now separate the magic ordinary-door helper from O-Open, magic-lock demotion, and Word-of-Power dungeon doors. The helper uses the shared spell direction prompt, treats Space/Pass as no effect, opens only ordinary closed wooden surface/town door variants, marks the tile dirty, bypasses keys, and does not use O-Open's chest/trap/auto-close machinery.

**Current fixed Search-table cleanup:** 2026-05-12 - `systems/containers.md`, `systems/hidden-treasures.md`, `catalogs/item-list.md`, `systems/magic.md`, and extraction now publish Search's fixed hidden-treasure database plus rare-reagent harvest mechanics. Hidden treasures use 113 pickup-class/state/scene/floor/X/Y records, a save-backed already-found bitmap for normal records, pickup staging through the active-object table, and three special-gated record families. Rare reagent harvests cover two mandrake-root points at overworld `(182,54)` and `(97,165)` plus one nightshade point at `(44,137)`, midnight-only, once per in-game day, 2..15 quantity, capped at 99.

**Current Search trap/detail cleanup:** 2026-05-12 - `systems/commands.md`, `systems/containers.md`, `systems/traps.md`, `systems/dungeon-mode.md`, and extraction now separate Search's caller-side trap/detail narration from the shared trap-effect resolver. Surface/town per-object slots can report no trap, simple trap, complex trap, or generic trap from slot trap metadata, member-stat threshold math, and a `1..30` roll, including false positives and missed traps. Surface/town Search also now publishes the post-object fallback order: reverse-priority slot treasure, live-tile location-prefix classification, hidden-door reveal, Moonstone, rare reagent, and fixed hidden treasure. Dungeon Search is now light-gated, classifies the packed cell high nibble for feature narration, publishes exact chest trap-tier narration, covers exact pit-family secret/bomb Search bytes, and documents flavour/wall visit-local rewrites. The later Search trap caller-boundary cleanup resolves the former caller-side trap selection-table residual as an active-object coordinate lookup.

**Current dungeon chest generator cleanup:** 2026-05-12 - `systems/commands.md`, `systems/containers.md`, `systems/dungeon-mode.md`, and extraction now correct dungeon Get from a vague six-category chest roll to the traced open-chest contract: closed chest refuses until opened, open chest consumption rewrites only the loaded dungeon image while preserving the visit marker, and rewards iterate seven table rows. The public table now names food, gold, keys, gems, torches, random potion, and random scroll rows with thresholds `2/4/5/10/20/25/25`, their quantity/subtype rules, possible multi-row awards, and the depth-zero gold-row helper edge.

**Current corrections propagation:** 2026-05-12 - All headings in the private correction ledger under `u5-decomp/` have been reconciled into clean public prose, the new PRNG, timing, moon-display, and runtime specs are tracked in `EXTRACTION.md`, and exact-parity follow-up remains concentrated in the declared partial rows rather than the closed corrections backlog.

**Current shop/save cleanup:** 2026-05-07 - `SHOPPE.DAT` NUL-terminator/token-range correction, shop inventory bitmap uncertainty cleanup, tavern state-byte wording, sage table-index/boundary cleanup, pending-action state wording, reagent availability boundary, inn registry shifted-view ownership, inn marker/clear/death-source behavior, and inn month-counter billing added.

**Current horse/ship broker cleanup:** 2026-05-07 - superseded by the later shop-dispatch and shipwright-sale cleanups: horse-trader purchase is now Talk-entered and places a horse object, the ship-broker Talk trigger is identified, and shipwright payment is traced into overworld active-object placement with Frigate/Skiff payload semantics and duplicate-purchase handling.

**Current combat spell-prereq cleanup:** 2026-05-11 - combat, magic, and DATA.OVL docs now correct the C-Cast pre-gate as an adjacent-target interference check: a mapped valid visible/awake adjacent target prints `<name> interferes!` and aborts before the spell prompt, while resource gates remain in the shared dispatcher.

**Current SJOG/Jimmy cleanup:** 2026-05-12 - command and door docs now publish non-dungeon door/visible-chest/NPC lock-pick rolls, failed NPC-pickpocket key consumption, the successful NPC thank-you path as picked/thanked state plus capped shared moral-standing `+2` rather than gold, per-map object chest broken-lock state, dungeon chest formulas, and the S/J/O/G tile-redraw versus inventory/status dirty-hint split.

**Current SJOG/Get cleanup:** 2026-05-07 - command and container docs now document Get's accepted pickup-slot filter shape, skipped non-pickup object rows, and tile-consumable redraw/inventory side effects while leaving the exact inventory-add code map open.

**Current SJOG/Open cleanup:** 2026-05-07 - command, door, and container docs now separate Open's already-open, too-heavy, locked, openable, and chest-helper fallthrough outcomes. Later 2026-05-13 cleanup treats the blocked-openable case as the traced too-heavy tile refusal and leaves unmatched object-table outcomes with the chest helper.

**Current SJOG/Search cleanup:** 2026-05-07 - command and container docs now clarify Search result ownership: object-table/treasure results feed inventory, ordinary feature hits narrate, and hidden-door, bomb-trap, chest, or treasure fallbacks own the live-tile/inventory side effects.

**Current DNGLOOK cleanup:** 2026-05-07 - dungeon-mode docs now clarify that fountain drinking is the only identified state-mutating L-Look class, and that V-View uses a centered scratch flood map with row queues before clearing/restoring the side-panel view.

**Current LOOKOBJ cleanup:** 2026-05-07 - world/town Look docs now separate active-object overlay-marker resolution, special Look handler bypasses, and `LOOK2.DAT` base-description cases that append clock, shrine, or dungeon-entrance context.

**Current combat AI staging cleanup:** 2026-05-11 - combat and monster-bestiary docs now publish the class-flag monster special hook: possess, blink/phase, and summon-daemon branch semantics, with v1 baseline row assignments now published in the bestiary and branch priority retained for classes or variants carrying multiple turn-special bits.

**Current K-Klimb cleanup:** 2026-05-12 - doors/Z-transition docs, item-list, and quest-graph now identify the outdoor Klimb gate as the Grapple flag granted by Lord Michael's conversation branch. Outdoor K-Klimb requires the party to be on foot, facing the climbable mountain family, then rolls each living member's Dexterity against `1..30`; failed rolls print the fall message and apply `1..5` damage before the party advances one cell.

**Current overworld falls cleanup:** 2026-05-12 - overworld, doors/Z-transition,
tile-catalog, gazetteer, and extraction docs now narrow the traced surface
falls handler to the confirmed Britannia chasm at `(54, 138)`. A later writer
census found no additional outdoor underworld-to-surface writer beyond the
traced chasm, whirlpool, and interior-exit cases; any future route should be
added as a new writer rather than implied by the falls path alone.

**Current plane-writer census cleanup:** 2026-05-13 - overworld,
doors/Z-transition, and extraction now bound plane writes to the traced surface
fall, whirlpool forced-underworld branch, scene-`0x19` interior exit, and
dungeon-owned exit/reset helpers. No separate outdoor underworld-to-surface
writer is identified in current function notes or disassembly sweeps.

**Current whirlpool plane-transition cleanup:** 2026-05-13 -
`systems/overworld.md`, `systems/active-objects.md`, and extraction now promote
the MAINOUT whirlpool adjacent-engagement branch as a second traced
surface-to-underworld writer: accepted whirlpool engagement while not on foot
moves the party to underworld coordinate `(34, 18)` and re-enters overworld
setup. The later plane-writer census found no separate outdoor
underworld-to-surface writer outside the traced chasm, whirlpool, and
interior-exit cases.

**Current display ABI cleanup:** 2026-05-12 - display-driver ABI, display
contract, and combat docs now identify driver dispatch offset `0x6C` as the
loaded-tile graphics palette-plane save/restore/mutation entry. The combat
framer samples a resident tile-restoration flag and, when set, reaches mode
value `1` as a tile-graphics restoration step before ordinary world redraw.
Known flag setup is owned by dungeon room-layout state, not by a post-combat
trap or loot path.

**Current display ABI boundary cleanup:** 2026-05-13 -
`systems/display-driver-abi.md` now frames the EGA-facing ABI as complete for
the v1 target: dispatch-cell loading, EGA buffer layout, rectangle fill,
compressed bitmap decode, front-buffer tile/glyph entries, title/dissolve
animation entries, and combat-exit tile-graphics restoration are public.
Remaining work is historical hardware or exact visual parity: non-load-bearing
helper slots, alternate tile-mutator modes, non-EGA conversion rules, and any
non-EGA interpretation of the compressed-bitmap metadata word.

**Current graphics archive boundary cleanup:** 2026-05-13 -
`formats/tiles.md` now treats the paired `.16`/`.4` archive family as complete
at structural depth: shared LZW envelope, container layouts, image/mask block
headers, row strides, sprite-mask polarity, and byte-budget checks are public.
Remaining work is catalog or renderer ownership: CGA palette choices, TEXT
strip slicing, dungeon billboard slot semantics, monster/item slot mappings,
sprite frame slicing, and optional compression-ratio cross-checks.

**Current shared arithmetic cleanup:** 2026-05-12 - A new
`systems/stat-arithmetic.md` centralizes the resident capped-add and
floor-subtract contract for byte and word counters, including byte unsigned
comparisons, word signed comparisons, caller-owned caps, and the no-result
in-place mutation boundary. Inventory and extraction now point at this shared
contract instead of carrying the arithmetic rule only as local prose.

**Current food-merchant cleanup:** 2026-05-12 - Superseded by the later
shop food/shipwright correction: the SHOPPES2 `F`/`S` flow is shipwright-owned,
not a food/provisions merchant.

**~~Current screen-mode boundary cleanup~~ (SUPERSEDED 2026-08-22):** 2026-05-13 -
the separation of the second resident dispatch cell from the display-driver ABI
still holds, and so does the recursion guard and the session-only lifetime.
Everything else in this entry is withdrawn: there is no "screen-mode
controller", no "presentation-mode/state-cache transition rule", and no
remaining "presentation parity" work. See `systems/disk-prompt.md` and the
withdrawal notice in `systems/screen-mode-dispatch.md`.

**Current stats-panel cleanup:** 2026-05-12 - A new
`systems/stats-panel.md` specifies the full-panel refresh model, six party-row
layout, active-player cursor consumption, combat row overlays, bottom
information block, vehicle/status glyph framing and empty-slot placeholder, and
cross-system refresh hooks. Exact bottom-block food/gold/month/day/year mapping
is now public; the combat row action/effect presentation is now described as an
inverse-video span sourced from the live combat descriptor. Save-format wording
now keeps the timing/status glyph byte distinct from the
transport/action marker byte, and the `0x20..0x27` middle-counter branch is
identified as the ship hull-condition display.

**Current M-Mix cleanup:** 2026-05-07 - magic and item docs now publish the owned-reagent-only selection list, selection/toggle/finish/cancel controls, and two-digit quantity prompt with zero-cancel behavior before inventory change.

**Current B-Board cleanup:** 2026-05-07 - vehicle docs now narrow the immediate dungeon refusal to the stock dungeon scene range and separate handled boardable-family refusals from the non-boardable `What?` no-action fallthrough.

**Current healer cleanup:** 2026-05-07 - shop docs now document the healer/sanctum yes/no entry, C/H/R/exit menu, post-selection condition checks, ordinary paid cure/heal/resurrection costs, The Healers Mission Cure/Heal no-price branch, and resurrection-to-maximum-HP effect.

**Current reagent-shop cleanup:** 2026-05-07 - herbalist menus now document the resident price/availability matrix: zero entries are omitted from the compact letter menu, nonzero entries are purchasable per-ounce prices, and the stale unavailable-reagent open question is removed.

**Current sage cleanup:** 2026-05-07 - sage rumours now document the fixed twenty-six-topic list model, per-topic fee, subject/destination substitutions, random rumour-template selection, remove the stale karma-quality claim, and close the live-input boundary rule: a matched topic must be followed by input end or a space.

**Current shipwright sale cleanup:** 2026-05-07 - supersedes the earlier commodity-shop wording: the shared outdoor pending-action state belongs to the shipwright sale flow, not a separate commodity-shop trigger, and overworld entry consumes it into a placed watercraft active object. Frigate purchases create a full-hull ship with two skiffs, standalone Skiff purchases create a skiff, Skiff purchases before Frigate delivery increment the queued ship's skiff count, second standalone Skiffs are refused, and second Frigate attempts do not alter the pending delivery.

**Current runtime countdown cadence cleanup:** 2026-05-11 - magic, combat, spell-list, and extraction docs now separate the shared active-effect/runtime tag counter from clock/light cleanup: zero and 255 are inert, other values decrement at reached command/combat cleanup endpoints, expiry clears the tag and requests redraw, and Negate Time is the explicit `T`/10 user whose active tag suppresses minute advancement.

**Current arms-shop pricing cleanup:** 2026-05-07 - arms buy-side pricing now documents the canonical equipment-price plus speaking-member Intelligence rule, corrects purchase inventory writes to shared counters, narrows the Talk context wording, aligns karma cross-references, and closes the `B` stock-table mapping as direct equipment item ids.

**Current arms S-menu cleanup:** 2026-05-07 - the arms `S` menu is restored as party-to-shop sell-back: it scans nonzero carried equipment counters, refuses unsellable rows and used ammunition, applies its own Intelligence-based offer formula, adds gold, and decrements the sold counter.

**Current inn-registry cleanup:** 2026-05-07 - shop/save/time docs now publish the inn registry's leading scene-marker match, no/one/multiple guest selection behavior, zero clear marker, leave-time stay-counter reset, pickup billing's stored-counter minimum, month-rollover counter increment capped at 25, and stored-status death conversion.

**Current extraction shop-gap sync:** 2026-05-07 - `EXTRACTION.md` now reflects the narrowed shop gaps: healer/sanctum flow, inn marker/clear/death-source/month-counter behavior, arms `B` stock-table indexing, arms `S` sell-back behavior, shop dispatch, and shipwright placement/payload/duplicate-purchase semantics are covered.

**Current healer scene-label cleanup:** 2026-05-07 - healer docs now tie the Cure/Heal no-price branch to the public Minoc town scene and the shipped shop display name `The Healers Mission`.

**Current shop-dispatch cleanup:** 2026-05-07 - shop/conversation/TLK/NPC/vehicle docs now identify Talk-entry shop dispatch outside the normal `.TLK` keyword-response path, shipped `.NPC` shop-trigger bytes, shared caller context, current shop-instance setup, mounted-horse ordinary-shop refusal, horse-trader Talk purchase that places a horse object, shipwright Talk sale trigger, and the overworld active-object placement/payload handoff; remaining vehicle-sale gaps are unpromoted edge variants rather than shop dispatch.

**Current cleanroom wording cleanup:** 2026-05-07 - shop overlay dispatch wording, door/NPC occupancy marker wording, remaining routing phrasing, loop setup labels, input nested-prompt wording, and visibility row-buffer wording cleaned up to avoid source-like implementation terms.

**Current monster-AI cleanup:** 2026-05-11 - public combat/magic/DATA.OVL wording now replaces the stale general runner gap with the bounded class-flag special hook and ordinary target/direction/command synthesis. Later cleanup records compound-only or readerless class-flag component bits as opaque metadata, not class-state field semantics, and records the no-target centre fallback as another direct flee-flag writer.

**Current chargen cleanup:** 2026-05-07 - chargen persistence wording now separates canonical `SAVED.OOL` interpretation from the still-unverified writer scratch order, removes stale questionnaire-class uncertainty, and aligns the transfer summary with the `PARTY.SAV` source path.

**Current chargen boundary cleanup:** 2026-05-13 -
`systems/chargen.md` now frames the questionnaire and save-image producer as
fixed: seed reads, Avatar record customization, seed class/equipment/world
state preservation, `SAVED.GAM` commit, traced `SAVED.OOL` ordering, intro-menu
return, Journey Onward handoff, and first-load no-normalization mirror behavior
are public. Remaining exactness is not in the questionnaire producer or
first-load file lifecycle.

**Current weather/save cleanup:** 2026-05-12 - weather docs now publish the wind saved-byte mapping for values 0..4, Wind Change's direction-prompt-to-state mapping, source-direction compass convention, calm no-op handling, wind sound trigger boundary, preservation for out-of-range save bytes, out-of-range wind banner behavior, ship sail-state markers, hoisted-sail player-ship wind cadence including calm/stalled feedback and HMS Cape wait-pass timing, and the non-player water-creature/pirate active-object wind cadence table. Post-cadence active-object step selection is owned by active-object movement, not weather. The former wrapped-call candidate in MAINOUT has been resolved as a world-tick pause helper, not a wind-cadence routine.

**Current outdoor active-object movement cleanup:** 2026-05-12 - private MAINOUT notes now promote the range-check, slot-advance, tile-walkability, target-cell, and apply-step helpers, and `systems/active-objects.md`, `systems/movement.md`, `systems/overworld.md`, and extraction publish the clean behavior: the outdoor per-turn walker handles adjacent engagement, Sea Serpent/Dragon first-frame near-range effects, aligned water-creature attacks, wind-gated ship-like movement, randomized X/Y directed-step priority toward the player, random-wander fallback, validation through the shared tile-class dispatcher and reverse active-object lookup, destination-tile movement chance gates, exact special mover bypass classes, the `0xFC` proximity mask, per-pass last-vacated-cell guard, water-creature facing rewrite, committed-coordinate updates, and redraw dirtying. Town NPC pathfinding now also distinguishes the player-as-NPC mirror from live player collision blocking, visibility enumerates the direct companion-band compositor branches plus the default helper's terrain-sensitive remaps, and projectile/impact visuals are now bounded as direct scratch-buffer/render-helper effects rather than active-object lifecycles. No projectile lifecycle gap remains in the active-object table; remaining questions, if any, belong to non-projectile dynamic-object users.

**Current vehicle sail cleanup:** 2026-05-12 - vehicle docs now specify the Y-Yell ship sail branch and marker encoding: hoisted sails use the `0x20..0x23` wind-control range, furled sails use the `0x24..0x27` manual range, low two bits carry north/east/south/west facing, and X-Xit refuses the under-sail case.

**Current transport-marker cleanup:** 2026-05-12 - vehicle, save-format, weather, stats-panel, movement, and extraction docs now publish the known transport-marker ranges for mounted horse, carpet, foot/avatar, ship under sail, furled ship, and skiff, with low-bit facing semantics and ordinary static terrain predicates for those families. The stats-panel glyph byte is separated from the transport/action marker, and the marker family `0x20..0x27` selects the ship hull-condition middle counter. Remaining compatibility details are opaque values outside the known marker ranges, not ordinary horse/carpet/ship/skiff terrain rules and not an identified balloon-state writer.

**Current item vehicle-row cleanup:** 2026-05-13 - `catalogs/item-list.md`
now mirrors the movement/vehicle ownership boundary: horse, skiff, and carpet
rows no longer list normal terrain predicates as item-catalog gaps. Remaining
carpet source edges are owned by conversation/Search/Get/container paths;
balloon is an art-only boundary for the analyzed baseline. The later item
transport-marker ownership cleanup broadens the source-edge wording and leaves
opaque marker values with save/vehicle opaque-state ownership.

**Current item transport-marker ownership cleanup:** 2026-05-13 -
`catalogs/item-list.md`, extraction, and this log now treat transport/action
marker values outside known live ranges as save/vehicle opaque-state work
rather than item-catalog rows. The later item-list closure delegates object
visual mapping, item-use presentation, acquisition edges, and vehicle source
details to their owning systems rather than leaving them as item-list
residuals.

**Current ship-repair wording cleanup:** 2026-05-13 -
`catalogs/item-list.md` no longer carries future repair-service discovery as
an item-catalog gap. The analyzed baseline has no traced command-level ship
repair path; vehicle acquisition/source coverage belongs to shop, vehicle, and
Search/Get/container specs rather than the item catalog.

**Current vehicle cadence cleanup:** 2026-05-12 - `systems/vehicles.md`,
`systems/overworld.md`, `catalogs/tile-catalog.md`, and extraction now resolve
the horse/cadence boundary. The traced `0x12`/`0x13` and `0x14`/`0x15`
transport-marker pendulum is actor/encounter cadence evidence only; it does
not alter the time cleanup's minute increment and does not define a player
movement-speed table. Mounted-horse directional movement is now specified as
the ordinary one-cell overland step using the horse passability predicate and
the standard overworld turn cost; no separate player rough-terrain stride table
is part of the traced baseline.

**Current boarding-family cleanup:** 2026-05-12 - B-Board now has public object-byte family transitions for horse, carpet, ship, and skiff: horse objects `0x10..0x11` board to mounted horse markers `0x12..0x13`, carpet object `0x1B` boards to carpet marker `0x14`, and ship/skiff facing runs `0x24..0x27`/`0x28..0x2B` board by preserving the selected facing byte. Remaining catalog work is visual art-frame naming, not command-byte transition behavior.

**Current ship-boarding cleanup:** 2026-05-12 - ship boarding now documents the broader accepted-state gate and its stock refusal semantically; the normal ship marker ranges are public, and the carpet-compatible edge is narrowed to accepted north/east carpet markers `0x14`/`0x15`, with the other carpet facing markers refused by the same precondition.

**Current input function-key cleanup:** 2026-05-12 - input docs now separate the F1-F10 remap block from the resident A-Z dispatcher, traced gameplay mode loops, and free-text prompts. No ordinary gameplay command meaning is assigned; preserve the keyboard-layer remapped range for any menu-specific or still-untraced consumer and otherwise ignore it in gameplay dispatch.

**Current DATA.OVL input-table cleanup:** 2026-05-12 - DATA.OVL now
publishes the semantic shape of the extended-key translation table:
Left/Right/Up/Down pre-translation, Home/End/PgUp/PgDn diagonals, and F1-F10
remapping kept separate from the table. The input spec now separates the
eight-code direction vocabulary from cardinal-only world/town/dungeon/combat
movement consumers and records diagonal fallthrough behavior.

**Current DATA.OVL cleanroom-boundary cleanup:** 2026-05-13 -
`formats/data-ovl.md` now labels byte-exact offsets and resident string dumps
as intentional cleanroom exclusions, while compact table families remain
delegated to their owning specs and catalogs. Extraction already marks
`DATA.OVL` complete at resident-data inventory depth; remaining work is
semantic table publication by owner, not raw resident-image transcription.

**Current questionnaire cleanup:** 2026-05-07 - `QUESTION.DAT` now publishes the clean virtue-pair-to-record ordinal mapping and removes the stale pair-table transcription gap without exposing private offsets or questionnaire prose.

**Current save/chargen seed cleanup:** 2026-05-07 - `SAVED.GAM` now documents the two leading bytes before the roster and the questionnaire-created Avatar's seed-preserved HP/max HP/experience/level fields. The later inventory cleanup resolved the older equipment-slot ambiguity.

**Current seed inventory cleanup:** 2026-05-07 - fresh `INIT.GAM`/clean `SAVED.GAM` seed values now cover starting supplies, reagent counters, party-size, clock, active-player sentinel, transport marker, wind byte preservation, and Iolo's Hut scene tuple without publishing raw seed bytes.

**Current chargen/transfer seed-stock cleanup:** 2026-05-13 -
`systems/chargen.md`, `systems/u4-transfer.md`, and extraction now treat
starting item, spell, and quest stock as seed-preserved flat save-image bands
owned by `formats/saved-gam.md`, inventory, item-list, and quest specs. The
fresh-save producers do not generate a separate stock table; they preserve the
seed bytes while patching only the Avatar-facing fields and `.OOL` companion
order. Later U4 no-data cleanup removes the source-field label gap, later
transfer dispatch cleanup removes the post-commit routing uncertainty, and
later `.OOL` first-load cleanup fixes the no-normalization mirror behavior.
Remaining chargen/transfer parity work is now transfer preview pixel layout.

**Current save I/O primitive cleanup:** 2026-05-07 - save/load now documents the resident read/write primitive edges: optional absolute seek, zero-count read default, create-or-truncate overwrite semantics, zero-on-error retry signals, ignored close-time failures, and nonzero short-read/short-write compatibility edges without exposing implementation text.

**Current FLAMES ownership cleanup:** 2026-05-07 - animation and extraction docs now clarify that `FLAMES.OVL` is not a gameplay/title flame animator; its public role is screen-preservation scratch for the font/Return-to-View path, while title idle animation is display-driver-owned.

**Current animation boundary cleanup:** 2026-05-13 -
`systems/animation.md` now removes the stale projectile-as-active-object scope
wording and closes the generic Open Questions section into owner boundaries.
Projectile/impact visuals are direct scratch/render effects owned by combat,
spell, ship-fire, and display callers; first-person dungeon exploration uses
dungeon position/cell state rather than active-object actors until it hands off
to combat. Remaining animation-adjacent work is catalog promotion for
class-attribute entries and special movement-gate visual identities.

**Current combat target-picker cleanup:** 2026-05-07 - combat, magic, and monster-bestiary docs now publish the target-picker's separate phase/hidden suppression filter, ordinary invisibility filter, first-five-party-slot fallback guard, centre fallback with monster-side flee marking, and monster-spell separation from the party C-Cast dispatcher.

**Current combat fleeing cleanup:** 2026-05-12 - combat, magic, spell-list, monster-bestiary, and extraction docs now separate Cause Fear/fear-panic spell handling from the actual morale writer: those spell routes force accepted hostile actors into the critical-HP state, while the wound-score morale classifier writes or clears the fleeing flag from current HP. A lower-tier summon/tame-style spell helper is now recorded as a descriptor bit `0x01` actor-repurpose path, not a flee-bit writer. The docs also specify the out-of-arena leave/escape helper including ship-style refusal and constrained same-direction exits. The no-target centre fallback is now recorded as another direct writer of the fleeing flag plus the critical-HP marker for eligible monster-side slots; the decoded possess/blink/summon-daemon hook still does not set flee.

**Current combat reward cleanup:** 2026-05-12 - combat, encounters, containers, monster-bestiary, and extraction now close the automatic post-combat reward gap: ordinary attack and spell/effect callers with a living party attacker credit the damage/status helper's returned damage or monster-kill reward unit directly to that attacker's experience, capped at `9999`, before the combat framer restores the world table. The ordinary terrain-target caller restores the saved world-object table again, then clears the original trigger slot or rewrites a `0x2C..0x2F` body-family trigger into persistent body/retrieval state. No traced combat-exit path promotes arbitrary killed-monster drops, adds party gold, changes karma, or grants a separate victory bonus; later food/gold/plague results belong to Search/Get on the rewritten body-like slot.

**Current post-combat SJOG boundary cleanup:** 2026-05-12 - combat, encounters, and extraction now explicitly reject the older post-fight SJOG loot-sweep hypothesis. COMBAT reaches SJOG for in-round command delegates and combat helpers, not for an after-victory durable loot handoff. The separate resident terrain-target caller does invoke SJOG's post-combat object reconciler for the original trigger slot after the framer returns; keep this as caller-owned reconciliation, not a COMBAT sweep.

**Current combat command-dispatch cleanup:** 2026-05-12 - combat and extraction docs now clarify that the dispatcher-level combat command map is complete for all twenty-six letters plus seven special inputs; most delegated overlay targets are named (SJOG Get/Jimmy/Open/Search/Klimb, CMDS X-it/Yell/Push, ZSTATS Ready/Z-stats), combat U-Use is a label-only abort rather than a CAST item-use continuation, combat Yell enters CMDS but falls through the no-effect scene path, combat Q-Quit abandons the fight through the defeat path rather than saving, combat X-it is distinguished from out-of-bounds fleeing, and combat P-Push directly enters the shared movable-tile handler using the active actor's combat coordinate anchor. Remaining command work is shared command-family edge cases.

**Current encounter probability cleanup:** 2026-05-12 - overworld, encounters, and extraction docs now align on the resolved random-encounter probability contract: a 1..30 roll spawns only when the tile/Z/hour threshold exceeds the roll; the traced formula does not include transport state or the fortunes-of-war flag. The same cleanup now publishes the outdoor spawn-coordinate retry loop, terrain selector, weighted active-object payload picker, active-object payload family names including the whirlpool and parched-desert Sand Trap special cases (the latter was published as a "sea-serpent" family and corrected on 2026-08-23), shore sea-creature filter, active-object initialization, sea-creature animation seed, and H-Hole-Up rest-loop interruption boundary including caller-side status restoration and selected-row handoff. Later rest/camp cleanup moves low-level CMDS alternate setup sound, delay, or prompt-control helper identity after sleep-ambush row selection to presentation QA.

**Current encounter boundary cleanup:** 2026-05-13 - `systems/encounters.md`
now treats the former partial-information section as a boundary list. Random
encounter probability, spawn placement, terrain buckets, sleep ambushes,
town-hostility non-encounter ownership, dungeon room arena selection,
combat-framer ownership, and original trigger-slot reconciliation are public at
system depth. The encounter extraction row is now complete: source-free ambush
reveal values are needed only for a non-original-data publication target,
ambiguous payload-frame verification belongs to tile/catalog and presentation
QA, and the fortunes-of-war flag has a bounded read/save/load/month-clear/count
reroll rule unless future evidence identifies a live producer. No traced
dungeon chest path currently selects `DUNGEON.CBT`; add one only if a future
caller is identified.

**Current encounter residual narrowing cleanup:** 2026-05-13 - extraction and
encounter docs now distinguish encounter behavior coverage from optional
data-publication and future-evidence work. Ambush reveal lifecycle semantics
and the clean record shape are covered; only a source-free reauthored-data
target needs curated reveal row values. The double-encounter flag is a bounded
opaque runtime flag in the current public contract: read/save/load/month-clear
and count-reroll behavior are specified, and no gameplay setter has been found
in current sweeps.

**Current town-hostility encounter correction:** 2026-05-13 - encounter and
combat docs now separate hostile-NPC town routing from the ordinary terrain
setup helper. The resolved `0x7C3E` target is DNGLOOK room-NPC setup, while the
traced town overlay handles hostile NPCs through attack, alarm, arrest, forced flight,
death, and slot-clear paths without arena combat. The terrain helper's indoor
single-attacker override remains documented only as a bounded helper behavior.

**Current dungeon-room setup correction:** 2026-05-23 - `formats/cbt.md` and
`systems/dungeon-mode.md` now specify the DNGLOOK room setup pass at metadata
row/column level: party-entry rows, sixteen source cells, per-source X/Y rows,
ordinary versus special source conversion, and the lack of a separate
dungeon-room monster-count roll. The remaining non-final gap is naming the
unrelated special setup ids; the final Doom absorbable marker and room-clear
`0xF?` to `0xA?` behavior are already covered.

**Current combat field-placement correction:** 2026-05-23 - `systems/magic.md`
and `systems/combat.md` now state that Fire/Sleep/Energy field marker
materialization has no random acceptance gate once impact resolution confirms an
in-arena cell. The coordinate lookup determines the returned contact target,
not whether the marker is placed.

**Current combat terrain-hazard correction:** 2026-08-24 -
`systems/combat.md` now publishes the common post-dispatch hook's exact terrain
arms: swamp reuses the Poison result, while molten lava and fireplace reuse the
Fire result, with their target gates and exact PRNG consumption. Terrain
selection suppresses the placed-marker scan even when the later swamp class
gate rejects the effect. Doom's `0x3C..0x3F` absorption family is explicitly a
separate committed-action hook over the renderer companion band, not combat
arena terrain and not part of the terrain-over-marker priority rule.

**Current encounter flag rollover cleanup:** 2026-05-13 - encounters,
save-format, time, and extraction docs now correct the fortunes-of-war clear
boundary: ordinary midnight/day rollover does not clear the flag; the 28-day
month-boundary bundle does. The public compatibility rule is to preserve the
resident byte through save/load, clear it only at that boundary, and treat any
non-zero value as the terrain-combat count-reroll modifier.

**Current active-object render-effect cleanup:** 2026-05-13 - active-object,
overworld, and extraction docs now keep natural moongate frames with the direct
render-buffer animator, alongside projectile/impact visuals and terrain
animation, rather than treating them as active-object slot lifecycles. The
saved-slot natural moongate schedule and live entry path remain separate from
both the active-object allocator and the render-frame animator.

**Current random-spawn bucket cleanup:** 2026-05-12 - `systems/encounters.md`,
`formats/data-ovl.md`, and extraction now publish the corrected random-spawn
terrain selector, the four ordered weighted bucket memberships, and the direct
special branches for whirlpool/forced-underworld, parched-desert Sand Trap
(named "outdoor sea-serpent adjacency" in that 2026-05-12 cleanup and corrected
on 2026-08-23 - the run is `0xE0..0xE3`, bestiary class 40), and Rot Worm
payloads. The three probability figures published alongside them were also
corrected on 2026-08-23 for an inclusive/exclusive off-by-one in the shared
range draw. The outdoor arena selection range table is also now
public for trigger class bytes `0x40..0x7F` plus the skiff/pirate-ship special
case. Later rest/camp cleanup moves the low-level CMDS alternate setup
presentation helper identity after sleep-ambush row selection to presentation
QA. Source-free reauthored ambush reveal rows, if needed, are a
data-publication target, and visual atlas verification for ambiguous outdoor
animated families belongs to tile/catalog presentation work.

**Current rest-interruption cleanup:** 2026-05-12 - rest/camp and encounter
docs now publish the dangerous wilderness/dungeon sleep-interruption predicate:
after rest entry and surface gates accept, the rest helper rolls one shared-PRNG
64-outcome check; only the zero outcome interrupts. The sleep-ambush monster
chooser is an eight-row table with Giant Rat duplicated and Troll, Bat, Slime,
Giant Spider, Gremlin, and Headless appearing once each. The traced path does
not use a terrain probability table, and the alternate setup callee is the CMDS
H-Hole-up helper rather than SJOG or a separate scripted-fight dispatcher.

**Current Lord British camp-event cleanup:** 2026-05-12 - rest/camp and
extraction now publish the camp-event exactness: eligible normal camp success
rolls `random(0, 99)` and runs the old-man event on results `0..24`; each
non-dead member recomputes level from experience, receives the level/HP update
only when the stored level changes, then gets one uniformly selected capped
primary-stat reward. Avatar/Mage MP refreshes from Intelligence, Bard MP from
half Intelligence, and other classes leave MP unchanged.

**Current ambush reveal cleanup:** 2026-05-12 - combat, encounters, and
extraction now publish the ambush/camp reveal helper at semantic level: active
only in ambush/camp-attack modes, up to eight one-shot trigger coordinates,
optional one or two terrain stamps inside the arena, and immediate redraw.
`formats/data-ovl.md` now also names the clean eight-record table shape. A
byte-compatible engine that loads the original resident data should consume
the shipped reveal rows from `DATA.OVL`; only a source-free reauthored-data
target still needs curated reveal coordinates and tile identities.

**Current monster AI state cleanup:** 2026-05-11 - combat, magic, DATA.OVL, spell-list, monster-bestiary, and extraction docs now remove the older class-scoped AI-storage interpretation. Slot-local facts stay in the combat actor/effect tables; ordinary AI is target selection, step-vector synthesis, optional movement/teleport helpers, and shared command-parser reuse.

**Current combat AI movement cleanup:** 2026-05-12 - combat, monster-bestiary, and extraction docs now specify the ordinary movement fallback helpers: teleport-capable classes can attempt a random legal arena cell, ordinary stepping uses the surrounded check and in-arena step test, and no-target centre fallback now includes the traced flee-flag/critical-HP marker writer. The teleport-capable class-row assignments are now published in the monster bestiary.

**Current combat status-attack cleanup:** 2026-05-12 - combat and extraction
now publish the monster attack-resolver status branches: poison/status-flagged
monster attacks can route through the shared party-status/damage helper before
ordinary melee damage, Good party targets are poisoned with zero damage and no
attacker XP credit, non-Good or non-party targets fall through to small raw
damage, and Gazer/magic-effect attacks can enter stoning-style branches. Exact
poison/status class-row assignments are now published in the monster bestiary.

**Current target-picker exception cleanup:** 2026-05-12 - combat, monster-bestiary, and extraction now label the target-picker phase/hidden suppression-filter exceptions as Doom combat and acting Shadow Lord. The ordinary invisibility filter still applies after that exception.

**Current inventory/R-Ready cleanup:** 2026-05-12 - `systems/inventory.md`, save-format, item-list, command, DATA.OVL, and extraction docs now publish the ZSTATS/R-Ready equipment contract: combat-aware character selection, stats/equipment page families, page navigation, inventory band browsing and row-prefix rendering, six equipment-slot order, `0xFF` empty sentinel, equipment id reuse across shops/counters/readied slots, equipment class-tag meanings, R-Ready picker filtering for carried-or-already-readied rows, combat `R` routing through the same ready cascade with an active-actor selection shortcut, already-readied unequip returns up to the `99` equipment-stock cap, ranged-weapon ammunition readiness gates, burden-versus-Strength refusal, hand-occupancy gates, the narrowed combat armour lock boundary, accepted-equip counter mutation, Ring of Invisibility/Ring of Regeneration equip-time vanish checks, and the separate equipment-weight helper's non-enforcing boundary. The CAST U-Use dispatch is also now promoted for scroll families with branch gates and item-specific active-effect constants, potion counter order and colour/effect mapping including White potion visibility sweep, Moonstone burying, carpet boarding, skull keys, Lord British regalia, shards, Spyglass, HMS Cape plans, Sextant, Watch, Badge, and Sandalwood Box refusal. No known R-Ready atomic-swap or displaced-equipment parity gap remains.

**Current magic-ring/amulet cleanup:** 2026-05-12 - inventory, combat, item-list, monster-bestiary, and extraction docs now correct the prior one-shot-ring interpretation: Ring of Invisibility and Ring of Regeneration are ring-slot equipment, but accepted R-Ready has a 1-in-16 immediate vanish check; combat also consumes either worn ring on a separate 1-in-16 round-loop check, with Invisibility tied to the hidden/suppressed combat flag and Regeneration tied to wearer healing. Amulet/Turning is an amulet/neck equipment row with a combat-passive target-side branch: against flagged ranged/effect attackers, half of attempts are forced into the scattered-impact path rather than the ordinary hit-roll result.

**Current combat vanish cleanup:** 2026-08-27 - combat, monster-bestiary, and
extraction assign the vanish-on-death branch to Wanderer, Blackthorn, Lord
British, and Shadow Lord. `systems/combat.md` now also publishes the exact
narration/result/marker/reveal/release/faint-scan order; the shared action-result
bit's readers, clears, save-image boundary, and sleep-overwrite edge; the EGA
256-pixel reveal order and 31-tick blocking cadence; partial slot-clear fields;
and the Sword-of-Chaos removal and sleep mutations in the final party scan. The
older fade and post-turn-flush descriptions are retracted. Component-bit labels
remain opaque metadata when they have no independent behavioral consumer.

**Current combat class-flag cleanup:** 2026-05-13 - combat, DATA.OVL,
monster-bestiary, and extraction docs now promote the traced ranged/effect
attack consumers: a class trait can route attacks into the cast-like
ranged/effect branch, a separate magic-immune/boss-resistance gate can abort
that helper in special combat contexts, and poison/status attacks are documented
as a combined flag cluster rather than separately named component bits.

**Current combat Mage turnable-boundary cleanup:** 2026-05-13 -
`catalogs/monster-bestiary.md` and extraction now keep the Mage row's
turnable-attack flag as a shared combat-table trait without inventing a hostile
Mage monster entry. The later ranged/effect side-table cleanup publishes the
selector, payload, and scene-resistance row values, so the published
Amulet/Turning set is complete at behavioral-trait depth.

**Current item/combat attack-routing cleanup:** 2026-05-13 - `systems/combat.md`,
`catalogs/item-list.md`, and extraction now publish the clean shared attack
shape: zero-damage rows route to spell or special effect handling, nonzero rows
route to target selection and attack application, range-gated non-adjacent
attacks use the ranged/projectile/effect path, adjacent attacks use melee
damage, and the ordinary hit helper uses special always-hit action/effect cases
or the `(attacker - defender + 30) / 2` score against a random byte. The later
weapon range/effect table cleanup publishes the item-id keyed non-adjacent
range caps and effect-code rows for Dagger, Sling, Flaming Oil, Spear, Throwing
Axe, Morning Star, Bow, Crossbow, Halberd, Magic Bow, and Magic Axe. A later
equipment-consumer pass closes attack-time ammunition, thrown-stock, and
glass-breakage consumption as negative boundaries for the analyzed baseline.

**Current ammunition/breakage negative-boundary cleanup:** 2026-05-13 -
`catalogs/item-list.md`, `systems/combat.md`, and extraction now record that
the traced combat attack stack does not decrement arrows or quarrels, does not
decrement a readied weapon's carried stock, and does not clear the readied slot
for thrown or glass-family attacks.

**Current item ammunition-gap narrowing:** 2026-05-13 - item catalog and
extraction now frame ammunition, thrown-item, and glass-family mutation as a
closed negative boundary for the analyzed baseline, not as a mechanic to guess
inside the weapon dispatcher. The item completion checklist also removes the
duplicate combat-restriction bullet by grouping remaining restrictions with
shared attack routing, weapon range/effect rows, attack max damage, and R-Ready
gates.

**Current weapon range/effect table cleanup:** 2026-05-13 -
`catalogs/item-list.md`, `systems/combat.md`, and extraction now publish the
item-id keyed non-adjacent weapon caps and projectile/effect codes for the
traced weapon-dispatch path. The cleanup also removes the stale per-weapon
accuracy-table gap: the traced dispatcher uses the shared combat to-hit helper
after range/effect routing rather than a separate item hit-chance row.

**Current P-Push cleanup:** 2026-08-25 - commands, input, town-mode, combat,
dungeon-mode, and text-output docs now publish the shared P-Push
movable-static-tile contract: Escape is ignored while Space/`Pass` cancels;
door cleanup precedes the prompt; active-object sources are refused rather than
moved; both refusal literals and both success literals are exact; the
push-versus-pull branch, facing rewrite, live-tile mutation, combat actor-anchor
invocation, out-of-grid alias/scratch behavior, caller turn results, and the
combat ambush-reveal preemption are explicit. The save/load boundary keeps the
top-down stamps visit-local, and both `0x44` and `0x45` resolve to cobble through
LOOK2 while remaining distinct Push-family matching bytes.

**Current E-Enter narration cleanup:** 2026-08-25 - commands, overworld, and
gazetteer docs now publish the complete forty-row stock join from scene/key to
accepted plane/coordinate, live-tile narration class, exact visible
continuation, centered-name placement, and helper guard. The contract also
closes the town/dungeon no-coordinate failures, opposite-helper guard failure,
missing-sidecar-class policy, sealed-mouth behavior, acted/no-action results,
and narration ordering before `.OOL` persistence and destination setup. It
withdraws the earlier claim that successful entry omits the proper location
name.

**Current P-Push stamp-catalog narrowing:** 2026-05-13 - `systems/commands.md`,
`systems/doors-and-z-transitions.md`, and extraction now use the LOOK2-backed
tile catalog for the generic stamp: `0x44` is cobble. The only P-Push
stamp-label residual is the exact visual/catalog name for the chair-family
`0x45` stamp during the current visit.

**Current quest-flag cleanup:** 2026-05-12 - a new `systems/quest-flags.md` separates durable save-backed quest/NPC/shrine/item flags from TALK's per-scene 32-bit branch flag bank and one-conversation signal arrays. Conversation, TLK, save/load, DATA.OVL, quest-graph, and extraction cross-references now keep IF/ELSE branch flags, karma-threshold branches, transient generic action flags, durable resource/item writers, and final-cleanup stolen-action reconciliation distinct. The final cleanup's sentinel predicate, town-entry producer path, warning glissando, one-byte-at-a-time saturating decrement order, time-reseeded three-slot selection, random `1..15` gold fallback, and out-of-range TALK branch bit zero-mask behavior are public.

**Current quest-flag save-band cleanup:** 2026-05-13 -
`systems/quest-flags.md` now matches the later save-format cleanup: it no
longer points to a working-hypothesis dense NPC flag block, and instead treats
named NPC interaction persistence as semantic state owned by conversation,
town, and NPC systems. Remaining byte-level exactness for unnamed mixed-band
state belongs to `formats/saved-gam.md`.

**Current boot cleanup:** 2026-05-12 - a new `systems/boot.md` specifies the low-level startup layer: DOS MZ entry into the resident main path, machine-class probing, graphics-capability probing, command-line display reconciliation, Tandy low-memory fallback boundary, early text/timer/error-handler setup, BIOS conventional-memory capture, and display-driver load handoff. Launcher, intro, display-driver ABI, DATA.OVL, and extraction now link to this boot contract. The EGA sentinel is now narrowed to a startup-selection state where the traced display-driver loader takes no driver-load path if it arrives unchanged; remaining exactness is live hardware policy for any pre-load sentinel normalization. MZ relocation and startup-stack arithmetic belong to byte-compatible DOS-loader harnesses, not gameplay state.

**Current ULTIMA startup checklist cleanup:** 2026-05-12 - the analyzed startup entry, resident main loop, machine/graphics probe, display-driver load handoff, timer calibration, and active text-window style-cache reset notes now point to their existing clean specs in `systems/boot.md`, `systems/main-loop.md`, `systems/display-driver-abi.md`, `systems/timing.md`, and `systems/text-output.md`.

**Current ULTIMA stats-panel checklist cleanup:** 2026-05-12 - the resident full stats refresh and per-row renderer notes now point to the existing clean `systems/stats-panel.md` contract. The public spec already separates the read-side panel from the owning food, gold, calendar, combat descriptor, active-player, and transport systems.

**Current ULTIMA active-object checklist cleanup:** 2026-05-12 - `systems/active-objects.md` now explicitly covers the resident active-object acquisition cascade and initialiser alongside the existing lookup, animation tick, and outdoor movement contracts. The allocator wording was corrected from a simple first-empty scan to the traced ordinary-slot, off-screen-priority, and protected-class eviction behavior.

**Current ULTIMA visibility/render checklist cleanup:** 2026-05-12 - `systems/visibility.md` is the current clean owner for the resident world-tile getter, its cross-overlay alias, the visibility producer, and the fog/active-object post-pass. The stale private checklist target `systems/rendering.md` was treated as an older name for this visibility/render pipeline.

**Current visibility marker/local-light cleanup:** 2026-05-13 - visibility now specifies that the viewport renderer/effect walker is read-only on the eleven-by-eleven grid, that cheap-path zero cells are left by the active-object compositor rather than by post-render clearing, that `0x1C` and `0xDD` have no traced non-render gameplay reader, and that the local-light mask order is refresh first, transient moongate frame stamps second, visibility carve third. Remaining 2D visibility exactness is visual palette/art parity for marker bytes if required and external-reader synchronization policy.

**Current moongate boundary cleanup:** 2026-05-13 - overworld and extraction
docs now identify the fixed surface coordinate `(233, 235)` gate branch as an
ordained-progress bitmask branch reached from the post-action special-tile
pass, not a Codex-read-mask branch, natural moongate phase reader, or
animator-origin collision test. The natural moongate animator remains specified
separately; later cleanup specifies saved-slot natural placement and the live
entry path.

**Current mode-zero cleanup census:** 2026-05-13 - time and extraction now
separate confirmed zero-minute cleanup callers from a broad "every mode entry"
assumption. Overworld entry, overworld underfoot-light latch clear, and town
entry are the traced zero-minute refresh cases. Combat exit uses a direct
lighting refresh plus visibility dirtying, dungeon room entry is combat-room
setup, and Journey Onward save-load hands the loaded state back to top-level
dispatch without owning a separate zero-minute cleanup. The current direct
cleanup caller pass also promotes the ordinary town arrest surrender path as a
twenty-minute advancing loop until 08:00; it is not a zero-minute recompute
caller.

**Current month-counter boundary cleanup:** 2026-05-13 - time, save-format,
dungeon, and extraction docs now narrow the per-character month counter: the
time system ages every character-record slot at the 28-day rollover with a cap
of 25, inn leave/pickup is the traced consumer for lodged records, and current
evidence shows no separate active-party or non-lodged gameplay reader.

**Current plane-transition boundary cleanup:** 2026-05-13 - overworld,
doors/Z-transition, dungeon, and extraction docs now retract the unverified
mirror-ascent and Hythloth bottom-ladder assertions. The public contract keeps
the confirmed Britannia falls coordinate, whirlpool forced-underworld
engagement, town-family exit plane selection, and dungeon K-Klimb level-boundary
refusal/exit-helper split. A later writer census found no separate outdoor
underworld-to-surface writer in current function notes or disassembly sweeps.

**Current transition cross-reference cleanup:** 2026-05-13 - main-loop and
tile-catalog docs now stop treating natural moongate entry and outdoor
underworld ascent as already specified generic transition paths. Scene-byte
dispatch now names fixed location entry, interior boundary exits, traced
special scene branches, and combat framing, while confirmed surface falls are
kept as world-plane swaps inside overworld mode; tile ids are kept separate
from still-open transition handlers.

**Current tile-catalog dungeon-boundary cleanup:** 2026-05-13 -
`catalogs/tile-catalog.md` and extraction now keep the five-hundred-and-twelve
top-down tile-id space separate from `DUNGEON.DAT` packed class/variant cells.
The catalog still owns atlas visual IDs, LOOK2 surface/town strings, terrain
query families, actors, items, and effects; dungeon cell geometry remains owned
by `formats/dungeon-dat.md` and `systems/dungeon-mode.md`. Remaining tile work
is visual/name attribution and catalog-label alignment rather than unresolved
dungeon cell semantics.

**Current cleanroom leakage scan:** 2026-05-13 - scanned system, catalog,
format, extraction, and tracker docs for language-tagged source fences,
decompiler/disassembly wording, register/address-style notation, and raw helper
address leakage. No source-like fenced blocks were found. One NEXT-STEPS combat
checklist sentence was rewritten to use semantic helper names instead of
resident helper addresses; remaining hits are public file-format offsets,
tile/item ids, cleanroom boilerplate, or provenance paths.

**Current catalog verification-boundary cleanup:** 2026-05-13 -
`catalogs/tile-catalog.md` and `catalogs/quest-graph.md` now label their
remaining sections as verification queues rather than open system questions.
Tile catalog work is now presentation/catalog QA rather than a partial
gameplay-spec boundary.
Quest-graph reachability comparison through the public TLK VM contract is now
QA/data-authoring work rather than a partial gameplay-spec boundary.

**Current quest action-letter boundary cleanup:** 2026-05-13 -
`catalogs/quest-graph.md` and extraction now separate fixed Talk action-letter
effects from quest-graph validation. The public conversation spec owns the
common counter, Grapple, carpet, skull/special-key, Spyglass, Sextant, and Black
Badge effects. The quest graph now records the semantic item edges and their
possible password, payment, karma, or follow-up-answer gates; residual work is
QA comparison against shipped dialogue records, including embedded or trailing
records.

**Current Doom word quest-graph cleanup:** 2026-05-13 -
`catalogs/quest-graph.md` and extraction now treat `VERAMOCOR` as authored
Word-of-Power rule data consumed by the Yell command path, while preserving the
negative boundary that no clean NPC keyword branch teaching it has been
identified. Doom's exterior gate remains the Shadowlord-vanquish check; the
word opens the Doom-side chamber seal after entry.

**Current dungeon byte-visibility cleanup:** 2026-05-13 - dungeon docs now make the byte boundary explicit: live dungeon cells do not store persistent visibility or automap memory, V-View's visited map is temporary scratch state, dungeon first-person visibility is binary on torch/light-spell counters, and bit `0x08` is class-sensitive variant/overlay state rather than a global seen/currently-visible flag. The minimap class-to-glyph ids and flood-return table are now public, including the presentation-only distinction that `0xB?`/`0xC?`/`0xD?` stop expansion while heavy-door/room-trigger classes do not. V-View visual glyph/pixel parity is presentation QA; the wind-tile torch-extinguish claim is resolved negatively for the analyzed baseline contact paths, and room completion durability is handled by the saved room-clear bitmap.

**Current save-format mixed-band cleanup:** 2026-05-13 - `formats/saved-gam.md`,
`systems/save-load.md`, `systems/quest-flags.md`, and extraction now replace
the older third-party `0x03B4` dungeon-map / `0x05B4` dense NPC-flag block model
with the traced flat-image ownership: `0x03B4..0x05B3` is the active
map/dungeon tile working buffer, `0x05B4..0x06B3` is mixed world/quest/mode
state immediately before the active-object table, and dense NPC interaction
facts remain semantic conversation/quest state rather than a public block
layout for that whole range.

**Current save-format boundary cleanup:** 2026-05-13 -
`formats/saved-gam.md` now treats the `SAVED.GAM` flat-image layout as fixed
and narrows remaining work to opaque mixed-band byte ownership,
transport/action marker values outside known live ranges, and display/catalog
values that do not add new character-record fields. `systems/save-load.md` now frames disk-prompt labels,
format extensions, backups, mid-combat saves, and one-drive/two-drive disk
inventory as compatibility or port policy boundaries rather than save-layout
open questions.

**Current vehicle boundary cleanup:** 2026-05-13 -
`systems/vehicles.md` now treats horse, carpet, ship, and skiff command
transitions as fixed for the traced baseline: B-Board, X-Xit, F-Fire
broadsides, Y-Yell sail toggling, transport-marker ranges, active-object
persistence, ship hull/skiff bytes, and wind cadence ownership are public. The
remaining vehicle work is catalog art-frame naming and opaque values outside
known transport-marker ranges, not a live balloon command path for the analyzed
baseline.

**Current town-cannon F-Fire cleanup:** 2026-05-13 - `systems/vehicles.md` and
extraction now separate the town-family cannon active-object hit from overworld
ship broadsides: cannon hits run the local object-update path and reduce the
shared moral-standing selector by five, floored at zero, while overworld
broadsides own the target byte-`+5` depletion and slot-clear rule.

**Current moral-standing save cleanup:** 2026-05-13 - `formats/saved-gam.md`
and extraction now publish save offset `0x02E2` as the scalar moral-standing
selector, distinct from the party food word and party gold word. Table-food,
crop, chest, and town-cannon paths can debit it directly; shrine and selected
NPC/help paths can raise it. Adjacent bytes in the same band remain
preserve-only mode scratch until individually owned.

**Current U4 transfer boundary cleanup:** 2026-05-13 -
`systems/u4-transfer.md`, `systems/save-load.md`, and extraction now treat the
transfer path as fixed at fresh-save producer depth rather than a Journey
Onward load variant: entry, `PARTY.SAV` source, `BRIT.GAM` / `BRIT.OOL` seed
files, validation gate, imported Avatar fields, preview/confirmation boundary,
abort-before-write behavior, commit file set, and Journey Onward handoff are
public, including the fresh-save `.OOL` emission order. Later U4 no-data
cleanup identifies the already-shaped gate (later renamed the Avatarhood test)
as the predecessor
virtue/karma standings, and static dispatch cleanup fixes post-commit control
as an intro/menu redraw rather than direct gameplay entry. Remaining parity
work is exhaustive preview text-field cursor, attribute, and redraw-timing
parity.

**Current U4 no-data label cleanup:** 2026-05-13 -
`systems/u4-transfer.md` and extraction now identify the later transfer
gate as the eight predecessor virtue/karma standing words: Honesty,
Compassion, Valor, Justice, Sacrifice, Honor, Spirituality, and Humility.
**Superseded 2026-08-22:** this entry originally said that all eight zero
produces a "no-transferable-data" branch. That direction is withdrawn. All
eight zero is the *Avatar* success condition; it never rejects the transfer,
and the only effects are the class override and preview wording. See
`systems/u4-transfer.md` sections 5.3 and 5.4. Remaining transfer parity work
is exhaustive preview text-field cursor, attribute, and redraw-timing parity.

**Current U4 transfer post-commit cleanup:** 2026-05-13 -
`systems/intro.md`, `systems/main-loop.md`, `systems/u4-transfer.md`, and
extraction now align on the static transfer dispatch: successful `T` writes the
fresh save, restores intro/menu state, redraws the start/menu screen, and
requires a later Journey Onward load to enter gameplay. The older direct-entry
summary is no longer a public contract.

**Current U4 transfer `.OOL` ordering cleanup:** 2026-05-13 -
`systems/u4-transfer.md` and extraction now stop treating the transfer
fresh-save object companion order as an unresolved question. The writer emits a
blank half followed by the `BRIT.OOL` seed, matching the already-published
fresh-game exception in `formats/ool.md`; the remaining parity question is
closed by the later first-load cleanup: Journey Onward mirrors the halves
exactly as canonical surface and underworld data without rotating them.

**Current fresh-save OOL first-load cleanup:** 2026-05-13 -
`formats/ool.md`, `systems/save-load.md`, `systems/chargen.md`,
`systems/u4-transfer.md`, and extraction now specify the first Journey Onward
behavior after chargen or transfer. The loader performs no special
normalization for the fresh-save writer exception; it mirrors the first half to
`BRIT.OOL` and the second half to `UNDER.OOL` as ordinary canonical halves.

**Current U4 transfer preview-region cleanup:** 2026-05-13 -
`systems/u4-transfer.md` and extraction now narrow the transfer preview
remaining work. The eight-column heading strip, lower boxed prompt/status
window, and paired character-info panels are fixed at region level; remaining
parity is the exhaustive text-field cursor grid, text attributes, and redraw
timing.

**Current NPC schedule status cleanup:** 2026-05-13 -
`EXTRACTION.md` now promotes NPC schedules/pathfinding to complete at scheduler
contract depth, matching `systems/npc-schedules.md` and the already-complete
`NPC.OVL` module row. The long-stall high-counter helper remains only
conditional low-visibility presentation parity if a later trace shows a visible
effect, not a scheduler/pathfinding gap.

**Current view boundary cleanup:** 2026-05-13 -
`systems/view.md` now frames Look/View as complete at gameplay-command depth:
dispatcher routing, gem consumption, surface/town descriptions, sign/poster
handling, fountain and wishing-well specials, full-map and local overlays,
dungeon look descriptions, and dungeon minimap flood behavior are public. The
remaining Look/View work is pixel-perfect overlay parity for per-class V-View
glyph placement, source-bank selection, border restoration, modal palette
variants, and screenshots; it is not state, persistence, or surface/town
visual-class mapping behavior.

**Current command dispatcher boundary cleanup:** 2026-05-13 -
`systems/commands.md` now treats the resident A-Z dispatch table as complete at
routing depth: mode pre-routing, scene-aware letter families, no-action
fallthroughs, prompt ownership, typeahead toggle, save route, major overlay
delegates, and cross-references are public. Remaining command work belongs to
per-handler return values, mode-local control-code tables, and P-Push
persistence testing.

**Current doors/Z boundary cleanup:** 2026-05-13 -
`systems/doors-and-z-transitions.md` now frames ordinary door Open/Jimmy,
magic ordinary-door opening, dungeon Word-of-Power door transmutation, outdoor
Grapple Klimb, town-floor Klimb, dungeon level changes, vehicle X-Xit
boundaries, combat enter/exit state preservation, and the confirmed
surface-to-underworld chasm fall as public transition contracts. Tile encoding
labels and town secret-door object metadata are delegated to tile/catalog and
location/object data-format docs. A later writer census bounded outdoor plane
writers to the traced fall, whirlpool, and scene-`0x19` interior-exit cases,
while dungeon deepest-level edge cases remain dungeon-owned exit/reset behavior.
The system inventory row is now complete at transition-contract depth.

**Current doors/Z persistence narrowing:** 2026-05-13 -
`systems/doors-and-z-transitions.md` and extraction now separate covered
visit-local tile-buffer mutations from P-Push stamp rendering. Door opens,
magic-lock clears, secret-door reveals, cannon-destroyed doors, and dungeon
Search rewrites are treated as visit-local unless a named quest flag or
room-clear bitmap owns durable state. P-Push top-down live-buffer stamps are
now bounded negatively for save/load and ordinary map/floor reload durability;
the later LOOK2 pass resolves `0x44` and `0x45` as cobble descriptions, with
`0x45` retained as the cannon-family matching stamp rather than a separate
visual-label gap.

**Current main-loop boundary cleanup:** 2026-05-13 -
`systems/main-loop.md` now treats the scene router as fixed at playable
dispatch depth: startup handoff, scene-byte dispatch, mode-loop ownership,
combat's non-outer-loop status, world-tick/redraw placement, per-turn cleanup
placement, save/load resume, resident Q save routing, and explicit exit prompt
separation are public. Remaining main-loop items are defensive cleanup
branches, overlay-loader compatibility, and refresh-only entry cases.

**Current startup argv cleanup:** 2026-05-13 -
`systems/boot.md`, `systems/main-loop.md`, and `systems/launcher.md` now align
on the command-line display selector contract: only the first character of the
first argument is consumed, it is folded to uppercase, `C`/`E`/`T`/`H` request
the four shipped display families, missing or unsupported characters leave the
explicit request unset for automatic detection, and additional arguments have
no known engine meaning.

**Current visibility boundary cleanup:** 2026-05-13 -
`systems/visibility.md` now treats the visibility-grid pipeline as fixed at
gameplay depth: producer fill states, centre-out carve behavior, blocker rules,
marker refinement, active-object compositing, renderer/effect read contract,
cheap terrain refill, mode boundaries, local-light mask ownership, and
moongate-mask ordering are public. Remaining visibility work is visual parity,
and synchronization policy for external readers; these are display/tooling
boundaries rather than ordinary gameplay visibility-grid gaps.

**Current visibility status cleanup:** 2026-05-13 -
`EXTRACTION.md` now promotes Visibility to complete at the 2D visibility-grid
contract layer, matching `systems/visibility.md`. The negative-light full-fill
compatibility branch is already specified. Pixel parity for marker colours/art
is display-driver work, external-reader synchronization is tooling policy, and
dungeon visual parity is presentation QA outside the dungeon-loop behavior
contract.

**Current shop boundary cleanup:** 2026-05-13 -
`systems/shops.md` now treats the analyzed shop flows as complete at gameplay
depth: Talk-entry dispatch, stock menus, arms buy/sell, guild purchases, healer
treatments, reagents, tavern drinks, meal-counter provisions, sage topics,
horse-trader sale, shipwright delivery, inn guest registry, surcharge,
persistence, and karma non-modulation are public. Remaining shop-adjacent work
is catalog/data-table publication for equipment stats, class restrictions, and
public price listings.

**Current overworld boundary cleanup:** 2026-05-13 -
`systems/overworld.md` now treats the outdoor loop as fixed for the traced
baseline at outdoor-mode depth: scene entry, chunk loading, live-buffer
substitutions, movement commit, the special underfoot latch, confirmed surface
chasm fall, active-object per-turn handling, encounter probe inputs, save and
object-overlay ownership, and mode hooks are public. Encounter probe and
random-spawn behavior are complete at overworld-loop depth. The save/load hook
now matches the current `.OOL` mirror contract. The current writer census finds
no additional outdoor underworld-to-surface writer beyond traced
fall/whirlpool/interior-exit cases. Later cleanup covers the saved-slot natural
moongate live-tile schedule and live entry path; tile naming, timing-tag and
transport-marker outliers, and chunk-substitution labels are catalog,
opaque-data, or QA work. The extraction overworld rows are later promoted to
complete for that path.

**Current overworld encounter-residual narrowing:** 2026-05-13 - overworld and
extraction now align with the encounter spec's resolved random-probe and
random-spawn mechanics. Ambiguous outdoor animated-family frame verification is
tile/catalog presentation work, and optional reauthored data targets are
data-publication work; neither is missing MAINOUT probe, placement, bucket, or
payload-selection logic.

**Current conversation profanity-boundary correction:** 2026-05-13 -
`systems/conversation.md`, `systems/karma.md`, and extraction now remove the
unsupported profanity-standing-change claim. The reserved-keyword route is
public as a chastisement plus bounded pause/timing loop; the wrapped resident
target is not a stats-panel refresh or virtue-standing writer. Remaining karma
work is
the broader non-shrine action census, any separate per-virtue standing layout
or seed, combat branches, and non-shrine clamp policy.

**Current ULTIMA timing/overlay/moongate checklist cleanup:** 2026-05-12 - the resident redraw tick, overlay loader, natural-moongate animator, and per-turn cleanup notes now point to their current clean public owners. The older private targets `systems/render-loop.md` and `systems/moongates.md` map to the existing `systems/visibility.md`/`systems/input.md`/`systems/overworld.md` coverage and the overworld moongate section.

**Current ULTIMA combat checklist cleanup:** 2026-05-12 - the resident combat framer, terrain setup, monster placement, round helper, slot-to-group classifier, target-distance helper, and folded fog/range helper now point to current clean coverage. `systems/combat.md` owns the framer/setup/AI and combat-distance behavior; `systems/visibility.md` owns the folded fog/refinement distance helper, while combat target scoring uses its separate computed range helper.

**Current remaining checklist audit:** 2026-05-12 - after the ULTIMA checklist pass and SHOPPES2 tavern-provision reclassification, the only remaining unchecked `Spec drafted` box should be the function-note template. `SHOPPES2_OVL/` is now resolved as a tavern/meal-counter provision helper with clean prose in `systems/shops.md`.

**Current SHOPPES2 private-note correction:** 2026-05-12 - `SHOPPES2_OVL/_OVERVIEW.md`, `TALK_OVL/`, `ULTIMA_EXE/`, and `SHOPPES2_OVL/` now align with the clean shop contract: Talk trigger `0x84` enters the SHOPPES2 shipwright flow, not a food/provisions merchant, while the internal `0x0450` block belongs to the tavern/meal-counter provision branch.

**Current overlay ABI cleanup:** 2026-05-12 - a new `systems/overlay-abi.md` specifies the Phoenix PLINK86 public contract: trampoline-mediated overlay calls, one-based overlay identities, four shared residency buffer groups, ordinary return semantics for resident-to-overlay and overlay-to-overlay calls, reachable-versus-unreachable export treatment, and the TALK-to-shop overlay ownership boundary. Runtime, main-loop, DATA.OVL, and extraction now link to this contract. Remaining exactness is non-load-bearing descriptor fields and two uncalled FONT exports for byte-loader-harness parity, not ordinary clean-engine gameplay behavior.

## Repository status

- **Branch:** `master` (private — to be flipped public once content is ready)
- **Latest spec commit:** `bdf28bc Correct Lord British castle binding`
- **Uncommitted local update:** current `EXTRACTION.md` inventory rewrite, Blackthorn capture/rescue spec, shop random-surcharge correction, stale cross-reference cleanup, raw byte-example removal, `.PCS`/compressed-`.BIT` LZW format recovery, single-image `.BIT` marker-word verification, sprite-mask polarity verification, title bitmap/path placement recovery, intro title/menu idle contract, intro title tick destination/source ownership, intro story-step transition/draw mapping, intro story rectangle-transition contract, intro story rectangle helper boundary, input idle-redraw timing cleanup, active-object idle animator placement, input blink/key mapping cleanup, text-output control/gate cleanup, visibility viewport-buffer cleanup, public display/rendering contract, engine-aligned spell token/incantation/recipe/scene-mask table cleanup, exact compact spell parser acceptance rules, magic field-placement byte mapping, spell handler-family mapping, active-target attack-wrapper damage math, directed spell wind-cone duplicate/prefilter cleanup, Tremor exact damage/reward formula and actor-scan behavior, Polymorph Giant Rat replacement, shared active-effect tag/counter values, high-circle spell handler details, shrine meditation state-machine cleanup, torch/light-spell duration mapping, time/light-scale endpoint cleanup, dawn/dusk gradient and personal-light floor correction, exact town-location marker/daytime rewrite rules, signed floor-page selection for named locations, default town-entry Y table semantics, DATA.OVL world-location scene/name binding, overworld E-Enter handoff semantics, dungeon scene/name/`DUNGEON.DAT` record binding, exact dungeon fall/bomb trap subtype behaviour, vehicle/ship-fire command extraction, MISCMAPS record/trailer cleanup, MISCMAPS Return-to-View stream binding, MISCMAPS Return-to-View command table, MISCMAPS Return-to-View helper schedule, NPC floor-link marker IDs, combat default drop-marker byte cleanup, monster death-flag asset verification cleanup, OOL save-staging/mirror correction, OOL lifecycle cross-reference cleanup, U4 transfer `PARTY.SAV` source filename cleanup, directed spell wind-cone friendly-fire boundary cleanup, combat active-object restore/loot-reconciliation boundary cleanup, combat reward-unit caller-propagation cleanup, combat descriptor-vs-active-object byte cleanup, dungeon active-object boundary cleanup, PTH open-question cleanup, save active-object persistence boundary cleanup, NPC schedule-Z unsigned cleanup, vehicle timing state-tag cleanup, save transport/status byte cleanup, saved wind-byte preservation, Rel Hur wind-transition boundary cleanup, natural-moongate placement-boundary cleanup, overlay dispatch and low-level call wording cleanup, save-file runtime-address cleanup, saved-scene scratch byte layout cleanup, source-provenance boilerplate cleanup, shared runtime countdown cleanup, karma non-shrine action hypothesis cleanup, KARMA.DAT standing terminology cleanup, X-it escape-helper routing cleanup, magic-lock spell-name cleanup, NPC cached-waypoint/stuck-threshold cleanup, conversation keyword-match/table-scan cleanup, chargen duplicate-pair/STR-floor/loser-delta cleanup, questionnaire pair-to-record mapping cleanup, save/chargen seed-field cleanup, and fresh seed inventory/location cleanup.
- **Previous priority commits:** `015430e Add endgame and world data specs`; `8665799 Add intro and priority catalog specs`
- **Push target:** `https://github.com/cleak/u5-spec`

### What is done

- README documenting purpose, structure, and specification style guidelines.
- [`EXTRACTION.md`](EXTRACTION.md) — master inventory derived from the actual GOG release file listing. Catalogs every code module, data file, algorithm, and cross-cutting reference table the engine will need to reproduce.
- 81 cleanroom spec docs: 48 system specs, 26 format specs, and 7 catalogs.
- `EXTRACTION.md` now reflects the current v1 status in ASCII status terms rather than the stale first-pass emoji checklist.
- Major game-mode and first-playable systems are covered: launcher/startup, main loop, commands, input, text, save/load, overworld, town mode, dungeon mode, combat, visibility, time, magic, karma, doors/Z transitions, vehicles/ship fire, containers/pickups, active objects, animation, shops, NPC schedules, encounters, Blackthorn capture/rescue, conversation, intro, endgame, lighting, weather, and U4 transfer.
- Recent additions: `systems/inventory.md`, `systems/display-driver-abi.md`,
  `systems/vehicles.md`, `systems/containers.md`, `systems/commands.md`,
  `systems/launcher.md`, `systems/animation.md`, `systems/display-driver.md`,
  `systems/prng.md`, `systems/timing.md`, `systems/moons.md`,
  `systems/runtime.md`, `systems/stat-arithmetic.md`,
  `systems/disk-prompt.md`, `systems/stats-panel.md`,
  `systems/quest-flags.md`, `systems/boot.md`, `systems/overlay-abi.md`,
  `systems/movement.md`, `systems/rest-and-camp.md`,
  `systems/blackthorn.md`,
  `formats/font-ch.md`, `formats/font-hcs.md`, `formats/font-pcs.md`,
  `formats/bit.md`, `formats/lzw.md`, `formats/look2-dat.md`, `formats/signs-dat.md`,
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
  Text output now documents the `0xFB`/`0xFC` centre-output controls,
  `0xFD`/`0xFE` inverse/underline controls, and the `0xFF`
  clear-active-window path. Fixed
  title/menu idle ticking, `BRITISH.PTH` pen origins, intro story-step
  transition/draw mapping, intro story rectangle-transition region/order and
  helper handoff, Return-to-View `MISCMAPS.DAT` stream ownership, command
  table, helper-effect schedule, and the public display/rendering contract are
  now specified. The Return-to-View EGA/Tandy cell-effect rasters, single-cell
  convergence permutation, exact preview-tick/input cadence, and abort state
  are also public. Remaining exact visual parity gaps are alternate-driver
  conversion details and the already-called-out per-table semantic
  enumerations. `.XMI` music is not
  present in the analyzed clean DOS baseline; add it only for a different
  audio-enabled distribution.
- The spell table is now aligned to the resident incantation order (`In Lor`,
  `Grav Por`, ...), with all 48 parser tokens, parser acceptance rules, recipe
  masks, scene masks, light-spell durations, the 99-charge mix cap, major CAST
  handler families, and exact active-target and multi-target damage semantics.
  Combat field placement and contact are also closed: placement-time target
  lookup is separate from the common post-dispatch contact hook; that hook
  targets the current actor descriptor while skipping only its linked renderer
  record. Poison's status arm consumes no randomness and its damage fallback
  rolls raw 0..20 with no defense draw; Fire rolls raw 0..10 with no defense
  draw; Sleep applies its status result; and Energy blocks movement and has no
  contact-result arm. Contact is shared by player and AI dispatch, does not
  consume the marker, and field markers persist until combat exit. The spell
  contract also covers active-effect tags and expiry, combat C-Cast
  interference, Protection, Quickness, Mass Charm, Negate Magic and Negate
  Time, high-circle targeters and placement, Dispel Field, directed wind-cone
  geometry and friendly fire, and the separate monster
  possess/blink/summon-daemon hook.
- An earlier external verification slice against local game data logged clean
  corrections. The first run bound Lord British's castle evidence to `CASTLE:0`
  and corrected the older "fifth castle slot" wording. Do not create or update
  `u5-engine` directories from this dirty workspace; fold only clean public
  correction summaries back into `u5-spec`.

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
| u5-decomp | `..\u5-decomp` (`C:\Projects\Rust\u5-dirty\u5-decomp`) | Private analysis workspace. Specs may cite note paths as provenance, but must not copy source, assembly, decompiler output, raw dumps, or private implementation text. |
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

- If exact original-asset visual parity becomes the next target, concentrate on
  alternate-driver conversion differences; the story rectangle dissolve and
  Return-to-View EGA/Tandy cell rasters are now specified.
- If audio/music asset compatibility for a different distribution becomes in scope, add a future XMIDI format spec from primary XMIDI/Miles documentation or a fresh local asset dissection.
- If exact movement and conversation parity becomes required, run implementation
  verification outside this dirty workspace and bring back only clean public
  correction summaries for `u5-spec`.
- Analyze non-load-bearing EGA helper slots or alternate display drivers only if historical hardware parity becomes a required public target.
- If combat parity becomes the next target, continue with shared command-family edge cases and presentation QA. If inventory parity becomes the next target, validate the owning Search/Get, conversation, vehicle, and quest-graph paths rather than treating item-to-tile mapping or story acquisition as item-list gaps.

## Long-running open questions

Tracked so they don't get lost:

1. **Hybrid prose-and-tables** vs. pure prose. Probably hybrid: prose for behavior, tables for layouts. Decide once the first format spec is written.
2. **Versioning baseline.** Ultima V had multiple releases (Apple II, C64, Amiga, IBM PC, with patches). Default baseline tag: "IBM PC EGA / Origin v1.x". Note version-specific behavior even if we never plan to support other versions.
3. **In-game vs. generic naming.** Use Ultima V's in-game names ("Britannia", "Lord British", "the Codex"). This is documentation of a specific game, not a generic CRPG engine.
4. **License flip timing.** Repo is private until content is ready. README declares CC-BY-4.0 license intent for spec prose. Decide when to publish — probably after the first system + format spec are complete and the style settles.
