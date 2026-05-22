# Dungeon mode

## 1. Overview

Ultima V's dungeon mode is the third top-level world mode, after the overworld and the town/dwelling/castle/keep family. Where those modes paint top-down tile views of the world, dungeon mode paints a sparse first-person three-dimensional view of a small grid the player walks through cell by cell. There are eight such grids — the named dungeons of Britannia, in resident entry and `DUNGEON.DAT` record order: Deceit, Despise, Destard, Wrong, Covetous, Shame, Hythloth, and Doom. Each dungeon is a stack of eight levels, and each level is a square eight-by-eight grid of cells. The player enters from a fixed surface or underworld location, descends or ascends through ladders, fights room encounters that swap into combat mode, and either climbs back out the way they came in or wins the dungeon's deepest reward and exits.

Structurally, dungeon mode is a sibling of town mode: it has its own per-turn loop, its own special tile reactions, its own command handler that forwards letter inputs to the resident A-Z dispatcher, and its own per-turn epilogue that advances the world clock. It differs in three important ways. First, the floor is not a tile grid the player sees from above — it is a 3D first-person view of what the party would see standing inside the dungeon. Second, the renderer is not a raycaster and not a line renderer; it plots sparse precomputed pixel constellations for visible wall and feature cues. Third, NPC schedules do not run in dungeons — there are no scheduled inhabitants underground — so the per-turn loop never invokes the NPC scheduler.

This spec describes the scene byte that selects which dungeon and entry mode is active, the on-disk and in-memory layout of dungeon levels, the per-turn loop, the special tile reactions, the sparse first-person renderer, the lighting model, movement and turn commands, Z-axis ladder transitions, the look and view commands, camp/sleep, the room-encounter combat trigger, time integration, and how the player exits a dungeon.

The original binary splits this public dungeon-mode contract across two overlay
families. DNGLOOK owns view/lifecycle helpers such as view setup, teardown,
room layout, L-Look, and V-View; DUNGEON owns the steady-state first-person turn
loop and dungeon-local tile reactions. A clean implementation can expose one
`dungeon` module, but it should preserve the same call-order boundaries: setup
and teardown bracket the turn loop, and command-specific view helpers are not
part of OUTSUBS or the overworld helper library.

## 2. The dungeon scene byte

The engine's scene byte is a single resident state byte that every world-mode loop reads to know what kind of scene is being played. The value zero is the overworld; values one through thirty-two are towns and other location interiors; values from thirty-three through one-hundred-twenty-seven are treated as dungeon-class by the gameplay dispatcher when reached from normal play; the observed combat-class marker is `0xFF`. The stock game uses eight normal dungeon scenes, thirty-three through forty. The dungeon turn loop runs while the scene byte is greater than thirty-two and below the combat-class marker, and exits when it drops to thirty-two or below — that is the engine's signal that the player has climbed back out and the overworld should re-engage.

Within the dungeon range, the scene byte selects the active dungeon. Subtract thirty-three to get the zero-based `DUNGEON.DAT` record index, or subtract thirty-two to get the one-based index used by the dungeon loop's flavour picker. The normal stock binding is:

| Scene | `DUNGEON.DAT` record | Resident name | Presentation flavour |
|---:|---:|---|---|
| 33 | 0 | Deceit | Flavour byte 3 |
| 34 | 1 | Despise | Normal |
| 35 | 2 | Destard | Normal |
| 36 | 3 | Wrong | Flavour byte 3 |
| 37 | 4 | Covetous | Flavour byte 3 |
| 38 | 5 | Shame | Mine |
| 39 | 6 | Hythloth | Mine |
| 40 | 7 | Doom | Normal |

The flavour drives cosmetic divergences in corner glyphs, dungeon-view resource selection, class-`0xC?` wall/corpse descriptions, normal-flavour wall decoration, and a Doom-flavour rare text easter egg. The flavour label is a presentation class, not the dungeon's in-world name; for example, the named dungeon Doom uses the normal presentation class in the stock table above. The flavour byte does not change geometry, tile semantics, encounter selection, fountain effects, or trap difficulty. The current dungeon for geometry and room-arena selection is the scene / `DUNGEON.DAT` record; fountain effects come from the fountain tile subtype. Treat any extra entry, facing, or flavour state bytes as runtime auxiliaries rather than as an independent public dungeon index.

## 3. Coordinate system and floor layout

The player's position is a triple: level index Z in `0..7`, X in `0..7`, and Y in `0..7`. Z increases downward — Z equal to zero is the top floor where the surface entrance lands you; Z equal to seven is the deepest level. X is west-to-east, Y is north-to-south. A separate facing direction byte records the cardinal the party is looking down: zero north, one east, two south, three west.

Dungeon entry seeds this runtime position after the selected 512-byte dungeon record has been loaded. Surface-plane entry starts at `(Z=0, X=1, Y=1)` facing east. Underworld-plane entry into non-Doom dungeons starts at `(Z=7, X=7, Y=7)` facing west. Doom is the exception: it uses the surface-style `(0, 1, 1)` east-facing seed even when reached from the underworld.

The full set of dungeon tile data is the file `DUNGEON.DAT`: eight dungeons × eight levels × eight × eight cells. The overworld entry helper loads the selected 512-byte dungeon record into the active dungeon tile buffer on entry. On disk, indexing is dungeon-major, then level-major, then row-major Y-then-X. The byte at `(dungeon, Z, Y, X)` lives at file offset `dungeon * 512 + Z * 64 + Y * 8 + X`. Once the player has entered a dungeon, runtime tile reads need only Z, Y, X within the loaded 512-byte record.

Each cell byte packs two four-bit fields. The high nibble selects the tile class; the low nibble selects a sub-type or attribute. The class encoding:

| High nibble | Class                          | Notes |
|------------:|--------------------------------|-------|
| `0x0`       | Open passage / nothing of note | The dominant cell type. |
| `0x1`       | Up ladder                      | K-Klimb moves Z to Z−1. |
| `0x2`       | Down ladder                    | K-Klimb moves Z to Z+1. |
| `0x3`       | Two-way ladder                 | K-Klimb prompts up or down. |
| `0x4`       | Wooden chest                   | Open / Search interaction. |
| `0x5`       | Fountain                       | L-Look triggers drink Y/N (§ 8). |
| `0x6`       | Pit / trap family              | Exact bytes drive fall traps versus bomb traps. |
| `0x7`       | Passage / corridor variant     | Renders as passage. |
| `0x8`       | Energy field                   | Sub-types: sleep, poison gas, fire, electric (§ 8). |
| `0x9`       | Energy field (secondary)       | Generic energy field. |
| `0xA`       | Room-helper / cleared-room state | Routed through the same underfoot helper as room triggers (§ 5). Reloaded cleared rooms use this high nibble. |
| `0xB`–`0xD` | Wall variants                  | Solid movement blockers (with one debug "SPEC WALL ERR" sentinel at `0xD`). |
| `0xE`       | Door presentation variant      | Door-like rendering/search variant. It is not the room-clear reload state and is not produced by the room-clear demotion pass. |
| `0xF`       | Room trigger                   | Walkable; low nibble is the room id `0..15` selecting the `DUNGEON.CBT` arena. Stepping onto a `0xF?` cell fires the room-entry helper and rewrites the cell in the loaded image to `0xA?` (room-helper state, same low nibble) for the rest of the visit. |

The high nibble drives wall checks in the renderer and the cell-description string in L-Look. The low nibble varies per class — for fountains it picks cure/heal/poison/bad-taste; for energy fields it picks the four sub-types; for ladders and walls it carries decorative or direction flags. For L-Look only, exact byte `0x61` is normalised to `0x00` before description, so it reports as passage even though the underlying cell byte remains a pit-family variant. Other observed `0x6?` trap bytes, including `0x69`, `0x62`, and `0x6A`, keep their `0x6` class description.

The loaded dungeon image does not carry a separate persistent visibility or
automap state. The commonly seen `0x08` bit is class-sensitive runtime variant
data, not a global visited or currently-visible bit. The shared dungeon cell
reader clears that bit for returned cells below the wall/door band, so low
classes such as passages, ladders, chests, fountains, pits, and fields do not
expose it as a first-person visibility flag through the renderer-facing read
path. For wall/door/room-like classes (`0x9?` and above), the renderer can use
the bit as an extra-glyph or active-object overlay marker. Individual
interaction handlers may still preserve, set, clear, or mask the bit as part
of their own runtime state; those writes remain visit-local mutations of the
loaded dungeon image, not durable exploration memory.

## 4. Per-turn loop

Each consumed turn runs the dungeon turn loop once. Its structure is parallel to the town turn loop's:

**Initialisation.** Set a "rendering-pending" visibility flag, run a one-shot boot-tick on the first turn after entry, read the underfoot tile, and cache its high nibble.

**Status painting.** Paint the side panel border and the status row showing the current level number and facing direction ("Dungeon Level N", "Facing North"). Repainted each turn because the player may have changed level or direction during the previous turn.

**Flavour selection.** Read the scene byte, pick one of the three flavour values (§ 2), and write the corner-glyph pair and flavour byte that the renderer and L-Look will consume.

**Underfoot reaction.** If the cached high nibble is room-helper state (`0xA`) or room trigger (`0xF`), run the room-entry helper — which loads a combat arena from `DUNGEON.CBT` and hands off to combat mode (§ 5, § 14). Otherwise run a brief re-init pass: a visibility hint, the torch burn-down call, and a view-renderer initialise.

**Inner loop.**
1. **Pendulum tick.** In Q-quest mode the loop alternates between running and skipping the time-advance call so quest scenes pass time at half rate. Normal play keeps the pendulum disabled.
2. **Render and poll.** Paint the sparse first-person view (§ 6) and wait for a keystroke. If input idled long enough that the player slept through one tick, the primitive returns a special "idle slept" sentinel.
3. **Dispatch.** The keystroke goes to the dungeon command handler, which routes numpad direction keys to the dungeon movement dispatcher, digit keys to a digit helper, control-S to a sound toggle, the Q letter to an "Exit to DOS?" prompt, and any letter A-Z to the resident command dispatcher (§ 10).
4. **Scene-byte exit check.** If the scene byte has dropped to thirty-two or below, the player has climbed out (§ 13) and the loop breaks.
5. **Refresh tile cache.** Re-read the underfoot tile and update the cached high nibble.
6. **Post-action hook.** If the dispatch did anything, call a post-action helper for end-of-turn cleanup.
7. **Idle slot.** If the dispatch did nothing (unrecognised key), enter a short polling step that prints "Zzzzzz..." at the appropriate cadence and re-polls input.

**Epilogue.** Toggle the appropriate visibility flag bit so the next render runs a full repaint, call the per-turn redraw primitive, and call the world-clock advance routine — the same routine town and combat call — with a one-minute increment. Time in dungeons advances at the indoor rate. If the input poll reported end-of-stream / quit, run the dungeon-exit teardown.

The loop then iterates, checking the scene byte; if it is still in the dungeon range, the next turn begins.

### 4.1 Presentation and Input Helpers

The dungeon loop owns a small amount of presentation state around the
first-person renderer:

**Viewport frame.** On mode entry and refresh, dungeon mode paints the side
panel's frame, the dungeon header, and the command prompt row before the
first-person viewport is composited. The frame uses the resident dim and bright
presentation pens; exact pixel coordinates are display-driver presentation
data, not gameplay state.

**Status row.** The status redraw saves the current text colour, clears the
target row, prints the one-based dungeon level, then prints the current facing
name from the four cardinal directions. Invalid facing values fall through to
the same resident fallback string path as the original presentation layer. The
saved colour is restored before control returns to the turn loop.

**Render and poll.** Each poll pass first services any pending cursor/status
redraw request, emits the normal line-feed/flush boundary, and asks the shared
input layer for a raw key event. The raw event is translated through the shared
game-key mapper before dispatch. Low raw directional events with no buffered
character are remapped into the dungeon command range so keypad-style movement
can reach the same movement dispatcher as letter commands. While no accepted
key is available, the helper renders the 3D viewport, blits the appropriate
viewport rectangle, runs the local presentation tick, and polls again. The
initial pass may request a full viewport blit; later passes can suppress
redundant blits when the current dungeon presentation flavour does not require
them.

**Active-object setup.** Dungeon view initialisation can either reuse the
current active dungeon object or roll a fresh one. A fresh roll selects one of
eight dungeon monster presentation records, installs the matching primary and
secondary sprite ids, resets the visibility flag, stamps the current Z level,
and lazily loads the sprite source if placement succeeds. Placement makes up
to eight random attempts on the current 8-by-8 level, accepting only cells in
the pit/corridor spawn families (`0x6?` or `0x7?`) and rejecting the party's
current cell. On success the same X/Y is written to the active-object slot and
the first dungeon creature slot. On failure the active-object coordinates and
sprite marker are cleared so no wandering object is drawn. Two traced sprite
ids have an additional approximately even chance to start invisible; the exact
monster names remain catalog data.

## 5. Special underfoot reactions

Two underfoot tile classes have *immediate* effects that fire before the player can act:

**Room-helper state (high nibble `0xA`).** The turn loop routes `0xA?` cells through the same helper as `0xF?` room triggers. The shipped `DUNGEON.DAT` records contain no `0xA?` cells; this class appears as runtime state created after a room trigger resolves, not as ordinary stock geometry. Keep the low nibble intact because the helper still treats it as the room-arena slot.

**Room trigger (high nibble `0xF`).** A subset of cells flagged as "room cells" trigger a room encounter when the party walks onto them. The same room-entry helper used by the `0xA?` state loads the appropriate arena from `DUNGEON.CBT`, sets combat-entry state, and hands off to combat. After combat resolves, the player re-emerges in the dungeon at the room cell. The helper patches the loaded dungeon image for that visit by changing `0xF?` to `0xA?`; the on-disk source cell is unchanged.

Cleared room state also has an overlay-side bitmap keyed by dungeon and room
id. This bitmap is part of the save image. When a level is loaded or reloaded,
room-marker cells whose clear bit is set are demoted from `0xF?` to `0xA?`,
preserving the room id low nibble. They are not demoted to `0xE?`. This keeps
the cleared-room runtime state consistent across save/load without changing
`DUNGEON.DAT`.

A third class of effect — **energy fields** (high nibble `0x8` or `0x9`) — fires not from the underfoot reaction but as part of *moving into* the cell. Stepping into a field-bearing cell triggers the effect *before* the move completes, applying status or damage to the moving party member or the whole party. The four sub-types are sleep, poison gas, wall of fire, and electric.

No mapped dungeon contact path defines a stock **wind tile** that extinguishes
torches. The traced movement-into-cell and post-action tile-effect dispatchers
cover room triggers, sleep/poison/fire/electric fields, pits, and
fountains/bombs, but do not write the torch counter through a breeze or gust
cell. Baseline-compatible implementations should not add a
`DUNGEON.DAT` wind-contact behavior; wind/gust artwork belongs to transient
presentation effects unless a variant handler is explicitly being modeled.

## 6. The Sparse First-Person Renderer

Dungeon mode's defining feature is its first-person three-dimensional view,
painted into the side panel each turn. The renderer is *not* a raycaster and it
does not draw continuous wall lines. It plots a sparse set of precomputed pixels
for wall edges and feature cues; the player perceives these dot constellations as
the dungeon corridor view.

**Distance bands.** The view is composed of a small fixed set of forward depth
bands. The renderer walks the facing direction, using nearby floor cells to
select which sparse pixel groups to plot. Distant or off-end bands can collapse
to degenerate draws rather than a smooth projected line system.

**Direction-delta tables.** To compute "what cell is N steps ahead", the renderer indexes two small four-entry tables — one for the X delta and one for the Y delta — by the facing direction byte. Each table holds the per-step offset for each cardinal direction. The renderer reads the cell at `(player_X + dx * (band + 1), player_Y + dy * (band + 1))` for each band.

**Wall checks.** For each band, the renderer reads the cell's tile byte and consults the high nibble. If the nibble identifies a wall class (`0xB` through `0xE`, plus door sub-cases of `0xF`), the band paints a wall cue at the appropriate viewer-relative depth. Open-passage cells are painted as a void: the sparse view shows the floor and ceiling cues extending farther forward. Closed doors paint a door rectangle; open doors paint as a passage.

**Side-wall mirroring.** The renderer also reads cells to the left and right of
the forward path and mirrors the corresponding sparse pixel groups. This gives
the side walls their bilateral shape without runtime projection math.

**Precomputed pixel tables.** The wall and feature cues come from compact
resident coordinate tables. The renderer selects a table entry from the dungeon
cell class and facing context, then emits individual pixel plots. There is no
runtime ray projection and no call to a 2D line primitive for ordinary dungeon
wall geometry.

**Far-wall extras.** After painting the near-to-far primary walls, the renderer walks back outward, painting the symmetric far-wall counterparts and the ceiling and floor outline corners that connect them. The result is a complete sparse outline of the corridor or chamber the player is looking down.

**Light gate.** Before any of the above runs, the renderer checks the torch radius and the light-spell radius. If both are zero, the renderer paints nothing — the side panel goes black, and the player sees only the status row and message panel. This "pitch dark" state is the gating reason torches and light-spells are gameplay-critical underground. The renderer is otherwise purely a function of the eight-by-eight floor data, the party's position and facing, and the lighting state.

Dungeon visibility is binary at the first-person renderer boundary: with no
torch and no light spell, the viewport is black; with either counter nonzero,
the renderer walks the current geometry and paints until blocked by wall/door
classes. There is no top-down eleven-by-eleven fog grid, no per-cell remembered
visibility, and no gradual numeric radius inside the dungeon renderer. Depth
cueing and far/near brightness are presentation state owned by the renderer,
not stored in `DUNGEON.DAT` cells.

### 6.1 Renderer Helper Contract

The first-person renderer is a deterministic helper pipeline over the current
8-by-8 dungeon level image.

**Cell reads.** Every renderer-facing cell read wraps X and Y independently to
the range `0..7`, then reads the current Z-level image. For cell bytes below
`0x90`, bit `0x08` is ignored by clearing it before class interpretation. For
classes `0x9?` and higher, bit `0x08` remains meaningful as a render-side
overlay/extra-glyph flag. This bit is not persistent visibility memory.

**Top-level render pass.** A render pass clears the dungeon viewport in the
back buffer, installs the plot-pixel clip rectangle, applies the binary light
gate, then performs two sweeps:

1. The forward sweep walks up to four depth slots in the current facing
   direction. At each slot, it classifies the forward cell, paints the centered
   blocker/decor cue if needed, and stops when the helper reports an opaque
   cell. If the slot remains open, the renderer paints the left and right side
   cells for that depth.
2. The backward sweep walks from the deepest accepted slot back toward the
   party and paints front-facing objects, walls, fields, and active-object
   overlays in far-to-near order. This ordering is the renderer's depth sorting:
   closer objects intentionally overpaint farther objects.

Depth slot three is structurally reachable only when nearer slots are open.
The wall-coordinate tables are effectively authored for the visible near and
middle bands; implementations should preserve the table-driven behavior rather
than invent a fourth projected wall band.

**Blocker and side-wall classification.** The centered renderer blocker and
the movement gate are related but not identical. For movement, the solid
wall/flavour classes are `0xB?`, `0xC?`, and `0xD?`; door-like `0xA?`,
`0xE?`, and room-trigger `0xF?` cells use pass-through or special underfoot
paths. The first-person renderer can still paint `0xA?`, `0xE?`, and `0xF?`
with door-like frames so the player sees the room doorway context. Class
`0xB?` wall decoration at the observed near depth may print per-dungeon
scenery text from resident tables. Class `0xC?` flavour walls can draw an
extra decoration glyph in the normal-flavour case. Doom-flavour class-`0xC?`
near walls also have a rare decorative skeleton-chamber presentation; this is
visual only.

Side-wall classification uses the side cell at the same depth. Passages paint
the side-flat marker, heavy-door and room-trigger families paint the door
silhouette, class `0xC?` can add the normal-flavour decoration glyph, and other
wall classes paint the ordinary side-wall cue. Decoration glyph painting may
update the cell's low-bit animation substate in the live image for the current
visit; it does not rewrite the static dungeon record.

**Sparse wall points.** Wall geometry comes from resident coordinate-pair
tables, selected by wall role:

| Wall role | Contract |
|---|---|
| Forward wall | Emit the full mirrored point set for a wall directly ahead at the selected depth. |
| Side door | Emit the smaller mirrored point set used by side-door silhouettes. |
| Side wall | Emit the side-wall point set around the side-cell anchor. |
| Corner | Emit the single mirrored corner point pair that connects adjacent wall cues. |

The renderer mirrors each point pair around the role's fixed axis and modulates
the pen through the current brightness toggle. These tables are resident
rendering data; the public spec describes their role without reproducing their
raw coordinate contents.

**Object and glyph painting.** Small dungeon features use the dungeon glyph
source image, while larger creature/Codex/role sprites use the dungeon sprite
source image. Glyph-like feature ids select a depth/subclass screen-position
table, with point-blank door and chest families forced to the viewport centre.
Larger sprite ids select a separate source and a separate depth-position table.
The renderer passes a mirror flag to support left/right side drawing.

The single-glyph helper has three visible families:

- standard four-sided decoration glyphs, with a small random chance to advance
  their animation phase;
- shrine-flavoured bright glyphs using the same shape with a brighter pen;
- Codex/shrine glow strips drawn at a fixed viewport location with vertical
  phase adjustment and a short presentation tone/pause.

**Fields and active objects.** Energy-field cells draw animated horizontal
strobe lines. The strobe uses per-field resident parameters for vertical band,
row count, and row spacing, plus a field-specific pen choice. The exact row
coordinates are randomized within the configured bands each render pass.

Active monster, Codex, Shadowlord, and similar dungeon sprites are drawn by an
animated sprite helper keyed to the global dungeon animation phase and the
current creature record. The helper can apply small random flicker/direction
variants, has a special quest-scene sprite-table path, and paints a paired
sprite/overlay result when the dungeon sprite source is loaded. If the sprite
source is unavailable, it falls back to text presentation rather than silently
painting a blank object.

**Composite redraw.** Commands that mutate dungeon state use a composite redraw
helper: reset the prompt/status presentation, render the 3D viewport with the
point-blank wall gate forced on, blit the viewport rectangle from back buffer to
front buffer, run the local presentation tick, and redraw the dungeon status
row. This is a repaint helper, not a game-state transition.

## 7. Light sources

Two state bytes track the player's light:

- **Torch radius.** A counter that decrements once per dungeon turn while a torch is lit. When it reaches zero, the torch goes out. The I-Ignite command consumes one torch; in dungeon scenes it adds 112..127 turns to the current torch counter, capped at 255.
- **Light-spell radius.** A separate counter tracking the duration of the light spells. *In Lor* sets it to 100 turns; *Vas Lor* sets it to 255 turns. It ticks down per turn alongside the torch counter.

Either counter being non-zero "lights" the dungeon — the renderer paints, L-Look describes the selected focus cell, and movement proceeds normally. Both counters being zero darkens the dungeon: the renderer paints nothing, L-Look returns "darkness" regardless of what is actually in front of you, and the player must light a torch (or cast the light spell) to see again.

Other observed sources: **spellbook lighting** items can bump the torch counter at every per-turn cleanup; **shrines** in some levels emit light; certain decorative tiles (the "gargoyle eyes" of one or two dungeons) are visual flavour only. The analyzed dungeon contact paths do not include a wind/breeze tile that extinguishes only the torch counter. The decay of the two counters is part of the world-clock advance call, not the dungeon mode loop's own logic; the time system shares a saturating-byte helper that the dungeon and overworld both use.

## 8. Special cells in detail

This section enumerates the dungeon's interactive cell types beyond plain walls and passages.

**Fountains.** A fountain cell (high nibble `0x5`) responds to L-Look with "a fountain" followed by "Will you drink?". The look handler has already selected a party member before describing the cell; on Y it applies the fountain's effect to that selected member based on the low nibble:

- **Sub-type 0 (Cure).** Sets status to `'G'` (Good) — clears poison and other curable status. "Cured!".
- **Sub-type 1 (Heal).** Sets current HP to max without changing status. "Healed!".
- **Sub-type 2 (Poison).** Sets status to `'P'` (Poisoned). "Poisoned!".
- **Sub-types 3+ (Bad taste).** Applies a random HP-damage roll in the inclusive range `0..7` via the standard apply-damage primitive. "Bad taste.".

Flavour-class divergence applies to the L-Look description in non-normal dungeons, but the four effects themselves are the same.

**Energy fields.** Sub-typed by low nibble:

- **Sub-type 0: Sleep field.** "A sleep field." Walking into it sets status to `'S'`.
- **Sub-type 1: Poison gas.** "A poison gas field." Walking in poisons the party.
- **Sub-type 2: Wall of fire.** "A wall of fire." Walking in applies fire damage.
- **Sub-type 3: Electric field.** "An electric field." Walking in applies electric damage.

The exact base bytes are `0x80` sleep, `0x81` poison, `0x82` fire, and `0x83` electric. Magic field placement preserves the dungeon visit marker bit when it writes into the live dungeon image, so the corresponding marker variants are `0x88`, `0x89`, `0x8A`, and `0x8B`. L-Look names only exact bytes `0x80..0x83` with the distinct field descriptions; other `0x8?` values collapse to the generic energy-field description.

The fields can be dispelled by *An Grav* / Dispel Field. The field check is part of the movement primitive: stepping into a field cell triggers the effect *before* the move completes, so the party receives the hit even though they're now standing on the field.

Dungeon field resolution applies to each living party member, not just the
front member. Sleep and poison fields roll `1..30` against the member's current
HP-derived save threshold; a roll above that threshold changes the member's
status unless the member is already dead. Sleep fields set status to `'S'`,
redraw the affected status slot, mark the dungeon presentation as needing a
redraw, and rewrite the live field cell to keep only its visit-marker bit. A
sleep field therefore behaves as a one-shot contact hazard for the current
dungeon visit. Poison fields set status to `'P'` and draw the status-effect
presentation, but do not rewrite the field cell, so standing on or re-entering
the same poison field can trigger it again.

Electric-field contact has a forced-step presentation path: the display flashes,
the party is pushed relative to its current facing, and status presentation is
refreshed afterward. The exact HP-loss side effect behind that presentation is
still an open verification point.

**Chests.** A chest cell (high nibble `0x4`) prints "a wooden chest" on look.
The Open command changes it into an open chest for the current visit; the
closed-cell byte does not encode the eventual contents. Dungeon chest contents
are generated later by Get while standing on the open chest. That Get path
consumes the open chest by clearing its chest class in the loaded dungeon image
while preserving the visit-marker bit, then runs the seven-row reward generator
specified in `containers.md`.

Dungeon Search also recognizes the chest class. In light, Search applies a
party-member stat roll against the current depth's trap difficulty and prints
no-trap, simple-trap, complex-trap, or generic-trap narration. The threshold is
`(2 * Z - member lock-pick class + 30) / 2`, using the same unsigned halving
convention as the dungeon Jimmy chest path. Search rolls `1..30` against that
threshold. If the roll is above the threshold and the searched cell is the
plain closed chest byte, Search reports no trap. Otherwise it derives a trap
tier: a fresh `1..8` roll when the first roll is at or below the threshold, or
the current Z value when the searched chest byte is already marked. Tier values
below `4` report a simple trap, values `7` or higher report a complex trap, and
the middle band reports a generic trap. This is a Search description and
detection path; the later chest Open/Get content generator and shared
trap-effect resolver remain separate systems.

**Pit, secret-passage, and bomb traps.** The `0x6?` family is a trap family,
not a uniform Z-transition class. Exact byte `0x60` is a plain pit for
inspection, but K-Klimb treats it as a direct fall/exit cell: it bypasses the
ordinary ladder apply path and invokes the dungeon surface-reset helper
described in Section 13.

Exact bytes `0x61` and `0x69` are automatic fall traps. Stepping on either
prints the pit/fall messages, clears the fired marker bits on the departure
cell in the loaded dungeon image, increments dungeon level by one, and lands
the party at the same X/Y on the next level. If the destination cell is below
the wall/door band (`< 0x90`), the engine marks bit `0x08` in that destination
cell before continuing. If the destination cell is another `0x61` or `0x69`,
the handler repeats, so the practical drop depth is the length of the vertical
trap chain at that X/Y, not a direct low-nibble-to-distance table. If the chain
increments the level past seven, the dungeon scene byte is cleared and the mode
loop exits. This pit-chain off-bottom path is distinct from the surface-reset
helper described below: it leaves the level byte at the incremented off-bottom
value and leaves X/Y at the trap-chain column. No exterior-coordinate table is
consulted on this path; any later outer-loop recovery is outside the dungeon
loop's local handoff. If the chain lands within the dungeon on a room-helper or room-trigger cell,
dungeon mode immediately runs the same room-entry helper as ordinary underfoot
room triggers, then reinitialises the first-person view.

A stock `DUNGEON.DAT` reachability scan found fall-trap cells, but no level
seven fall trap and no same-column vertical fall-trap run that reaches level
seven. The off-bottom mutation is therefore a defensive compatibility path for
custom or mutated dungeon data in the analyzed baseline, not a route produced
by the shipped static dungeon records.
Exact bytes `0x62` and `0x6A` are bomb traps: they print the bomb
messages, clear the current trap cell to its fired marker form, and do not
change Z.

Dungeon Search handles the pit/trap family as an inspectable feature as well.
It first prints the generic "nothing of note" search preamble, then applies
extra handling only for exact unmarked pit-family bytes:

| Searched byte | Search result |
|---:|---|
| `0x60` | Reports nothing in the pit; no state change. |
| `0x61` | Reports a found secret door, rewrites the searched cell to `0x60`, and, unless already on the deepest level, marks the same X/Y cell one level below with the visit bit. This is a visit-local reveal in the loaded dungeon image. |
| `0x62` | Rolls `1..30` against `(2 * Z - member lock-pick class + 30) / 2`. A roll above the threshold springs the bomb, reports it, and clears the searched cell to `0x00`; a roll at or below the threshold reports nothing on the pit and leaves the cell unchanged. |
| Other `0x6?` values | No extra Search-specific handling beyond the generic preamble. |

The `0x61` and `0x62` Search branches are local dungeon mechanics: they do not
grant inventory, do not use the surface object table, and do not invoke the
shared chest trap-effect resolver.

**Ladders.** Three classes:

- **Up ladder (`0x1`).** K-Klimb moves Z to Z-1 when the current level is above zero.
- **Down ladder (`0x2`).** K-Klimb moves Z to Z+1 when the current level is below seven.
- **Two-way (`0x3`).** K-Klimb prompts up or down.

The level cap is seven; the traced K-Klimb apply path rejects attempts to move
above level zero or below level seven. Ordinary dungeon ladders do not publish
a deepest-level underworld handoff. The only traced K-command dungeon exit
outside ordinary ladders is exact pit byte `0x60`, which invokes the
surface-reset helper.

**Door-like dungeon classes.** High nibbles `0xA`, `0xE`, and `0xF` all have door-like presentation in parts of the dungeon renderer and minimap, but they are not interchangeable storage states. `0xF?` is the stock room-trigger family, with the low nibble selecting the `DUNGEON.CBT` room id. `0xA?` is the runtime room-helper / cleared-room state produced both after room combat and by the save-image room-clear demotion pass on reload. `0xE?` is a separate door-presentation variant used by other runtime wall/search paths; it is not produced by cleared-room replay.

The dungeon Open command operates on the **underfoot tile** (not the cell in front). It can affect `0x4?` wooden chest cells and `0x7?` passage/chest-style variants, but no traced Open or Jimmy mechanism mutates `0xA?`, `0xE?`, or `0xF?` dungeon door/room presentation cells. Room-trigger durability is handled by the room helper and the room-clear bitmap instead.

**Special walls / secret doors.** Some wall-style and flavour cells can be
rewritten by Search for the current dungeon visit. For flavour class `0xC?`,
flavour values one and two only narrate the inspected feature. Other flavour
values print the flavour-specific find text and convert the target cell to
`0xB0` or `0xB8`, preserving only the visit marker bit. For wall class `0xD?`,
Search prints the hidden-wall result and converts the target cell to `0xE0` or
`0xE8`, again preserving only the visit marker bit. These rewrites affect only
the loaded dungeon image; re-entering the dungeon reloads the original
`DUNGEON.DAT` cell.

**Wind/breeze non-behavior.** No stock contact branch is mapped for a tile that
extinguishes a lit torch while leaving the light-spell counter unaffected. The
baseline dungeon contract therefore has no wind-contact torch-extinguish cell;
only the ordinary light counter writers and decay paths change the torch and
light-spell counters.

## 9. Movement and turning

Dungeon mode's movement set is small and uses the numpad / arrow keys, *not* letter commands:

- **Forward.** Step one cell in the facing direction. The engine consults the cell at `(player_X + facing_dx, player_Y + facing_dy)`. If that cell's high nibble is one of the wall/flavour classes `0xB?`, `0xC?`, or `0xD?`, the move is rejected and "Blocked!" is printed. Otherwise the party advances one cell, the energy-field check fires (§ 8) if the destination is a field, and the turn ends. Door-like `0xA?`, `0xE?`, and `0xF?` cells are not rejected by the ordinary forward movement gate; their room/door semantics are handled by underfoot and presentation paths.
- **Back.** Step one cell in the opposite direction. It uses the same destination calculation, with a small room-trigger exception: back-stepping into `0xA?` or `0xF?` is rejected, while ordinary wall/flavour classes remain blocked and `0xE?` uses the pass-through branch.
- **Turn left.** Decrement the facing byte by one (modulo four). Status row updates; the first-person view is repainted on the next loop iteration.
- **Turn right.** Increment the facing byte by one (modulo four).

The floor wraps in the eight-by-eight coordinate plane for movement and look
sampling. Movement into the active monster's current cell is blocked; the player
must use A-Attack or be caught by the post-action monster step to enter combat.
Unrecognized movement subcodes fall through to a turn-around action, rotating
the party by 180 degrees.

The **L letter** in the resident A-Z dispatcher means *Look* (§ 12), not *turn left*; the dungeon's turn keys are separate numpad / arrow inputs handled before any letter dispatch. The fifth movement-related action is **K-Klimb**, which reads the underfoot ladder cell to decide direction (§ 13).

## 10. Letter commands in dungeon mode

When the dungeon command handler receives a printable letter, it forwards the letter to the resident A-Z dispatcher, which routes by the dispatcher's letter table. The dispatcher reads the scene byte and picks the dungeon-specific overlay handler for letters whose meaning depends on mode. Most letters behave as elsewhere: **C** Cast, **G** Get, **I** Ignite torch, **J** Jimmy, **M** Mix, **N** New order, **O** Open, **R** Ready, **S** Search, **U** Use, **Y** Yell, **Z** Z-stats. The dungeon-specific routes are:

- **A** — Attack a creature in front of the party (the dungeon-mode attack handler).
- **H** — Hole up & camp; runs the overworld-style camp/sleep flow (§ 11).
- **K** — Klimb the ladder under the party (§ 13).
- **L** — Look at the dungeon focus cell in front of the party (§ 12).
- **V** — View; paint a top-down minimap of the current level (§ 12).
- **T** — Talk; always prints "Funny, no response!" (no NPCs in dungeons).

Letters that are no-ops in dungeons print "What?" or a stock refusal: **B** Board, **D**, **E** Enter, **F** Fire, **P** Push, **X** X-it. **Q** runs the "Exit to DOS?" prompt path.

The dungeon-mode A-Attack handler is a point-blank forward probe. It prints
the attack label, computes the wrapped cell one step ahead of the party's
current facing, and compares that coordinate with the single active dungeon
monster record. If the active monster is not exactly in that forward cell, the
handler uses the stock refusal response and does not launch combat.

If the active monster is in that forward cell, the handler clears the
first-person active-object presentation, sets up the dungeon combat arena
kind, and launches combat using the active monster's sprite id. After combat
returns, result code five moves the party one level down when possible and
otherwise exits through the fall/surface path; result code six moves the party
one level up when possible and otherwise uses the same surface-exit path.
Other combat results keep the party on the current level. If the scene is
still a dungeon after this post-combat step, dungeon mode advances time through
the normal tile reread path and redraws the first-person view.

Before letters reach that dispatcher, the dungeon command parser intercepts
mode-local controls: movement keys, Enter/period as forward movement,
Ctrl-S/sound toggle, numeric digits for digit accumulation, Q/quit-to-DOS, and
idle/sleep notifications. This is why ordinary shared commands such as M-Mix
still work in dungeons: they are not handled by the local parser and fall
through to the resident command dispatcher.

## 11. Camp / sleep (H-Hole-up)

H in dungeons follows the overworld code path (the resident "rest with watch"
wrapper) rather than the town's inn-tile hours-prompt. The wrapper:

1. Prompts for a rest duration in hours.
2. For each hour, runs the world-clock advance routine multiple times to accumulate sixty minutes per hour.
3. Runs HP regeneration logic that gives a small random HP gain to each living,
   eligible party member, capped at that member's maximum HP.
4. Watches for a rest-interruption event; in dungeons, an interruption can
   replace the camp with a combat arena (the dungeon-camp arena, loaded through
   the same combat framing family as room triggers).
5. Cures the "asleep" status on every party member who was asleep at the start of the rest.

The rest concludes either with "Party rested!" or "Ambushed!" (and an immediate combat). The dungeon turn loop resumes when the rest finishes; the party's coordinates do not change.

A second H-path is involuntary: some sleep/ambush flows can interrupt rest without requiring the player to press H. The same regeneration and ambush logic applies, but stock `DUNGEON.DAT` room cells use the `0xF?` trigger family rather than authored `0xA?` cells.

## 12. Looking and viewing

Two letter commands give the player visibility into the dungeon beyond the first-person view:

**L-Look.** The L letter in dungeon mode routes to a dedicated dungeon-look overlay rather than the overworld/town look overlay. The handler:

1. Prompts for a party-member slot (the standard "by whom?" prompt; ESC cancels).
2. Checks the lighting gate: if both torch and light-spell counters are zero, prints "You see: darkness." and returns.
3. Invokes the shared dungeon relative-focus helper with the current facing
   direction. The helper prompts for a relative choice: ahead, right, left, or
   here. Ahead steps one cell in the current facing direction; right and left
   rotate that facing by one quarter turn before stepping; here uses the
   party's current cell. The focus coordinate starts from the party's current
   dungeon X/Y and wraps through the eight-by-eight level grid when the tile is
   read. Space/Pass returns no focus, so L-Look aborts before printing "You
   see:".
4. Reads the dungeon tile byte at `(Z, focus_y, focus_x)` from the loaded dungeon image. For description only, byte `0x61` is treated as `0x00`.
5. Prints "You see:" followed by a class-specific message. Energy-field bytes `0x80..0x83` have distinct sleep, poison-gas, fire, and electric descriptions, while other `0x8?` values share a generic energy-field description. Class `0xC?` is a flavour-presentation class whose text depends on the active dungeon flavour. The remaining high nibbles collapse to passage, ladder, chest, fountain, pit, open chest, nothing-of-note, wall, or heavy-door descriptions.
6. For the fountain class, runs the drink Y/N flow described in Section 8.

The fountain prompt is the only state-mutating L-Look class currently identified: it can change the selected party member's status, HP, or both. Other L-Look classes narrate the inspected feature only. L-Look does *not* repaint the first-person view; the message appears in the message panel and the view stays as it was. L-Look does *not* advance time; it is a free action.

**V-View.** The V letter routes through the resident dispatcher before it reaches the dungeon-look overlay. The dispatcher requires a *gem of vision*, prints the no-gem refusal if the count is zero, and decrements the gem count before dispatching to the dungeon view handler. The shared look/view contract, including combat's no-consume `V` branch, lives in `view.md`.

The handler clears the side-panel viewport normally used by the first-person view and paints a top-down map centered on the party. It seeds a scratch flood walk at a center cell representing the party, maintains a visited map plus two row queues, tries the eight neighbouring scratch cells for each dequeued cell, maps each accepted scratch coordinate back onto the current 8-by-8 dungeon level relative to the party with wrapping, reads the corresponding `DUNGEON.DAT` byte, and paints a glyph based on that byte's high-nibble class.

The V-View visited map is temporary scratch memory only. It starts filled as
unvisited for the overlay, marks scratch cells as visited during that one flood
walk, and is discarded when the side panel is restored. It does not write
exploration bits into the loaded dungeon image and does not change what the
first-person renderer or future V-View calls can see.

Minimap floodability is its own presentation rule, not dungeon movement
passability. The per-cell painter returns "expand" for most classes after
painting their glyph. Only the wall presentation classes `0xB?`, `0xC?`, and
`0xD?` stop expansion. Heavy-door and room-trigger families (`0xA?`, `0xE?`,
and `0xF?`) paint door glyphs but still return expand to the flood walker.
Open chest/no-op classes paint nothing and still return expand.

The class-to-glyph contract for the dungeon minimap is:

| Dungeon high nibble / exact byte | Minimap output | Flood expands past cell |
|---|---|---|
| `0x0?` with bit `0x08` set | Passage detail glyph `0x18`. | Yes. |
| `0x0?` without bit `0x08` | No glyph. | Yes. |
| `0x1?` | Up-ladder glyph `0x2E`. | Yes. |
| `0x2?` | Down-ladder glyph `0x2D`. | Yes. |
| `0x3?` | Two-way-ladder glyph `0x2F`. | Yes. |
| `0x4?` | Closed-chest glyph `0x70`. | Yes. |
| `0x5?` | Six-cell fountain icon rooted at the mapped cell. | Yes. |
| Exact `0x60` | Pit glyph `0x19`. | Yes. |
| Exact `0x61` or `0x69` | Hidden/fall-pit glyph `0x71`. | Yes. |
| Exact `0x68` | Fired/walked-through pit glyph `0x12`. | Yes. |
| Other `0x6?` | Trap/blocker glyph `0x72`. | Yes. |
| `0x7?` | No glyph. | Yes. |
| `0x8?` | Stair/field helper glyph family. | Yes. |
| `0x9?` | No glyph. | Yes. |
| `0xA?` or `0xF?` | Heavy-door glyph `0x73`. | Yes. |
| Exact `0xB0` | Wall glyph `0x7F`. | No. |
| Other `0xB?` | Wall glyph `0x74`. | No. |
| `0xC?` | Flavour-wall glyph `0x75` plus its paired terminator cell. | No. |
| `0xD?` | Extra-wall glyph `0x76`, with the peer-view tint source when active. | No. |
| `0xE?` | Heavy-door variant glyph `0x77`. | Yes. |

When peer-spell view mode is active, V-View applies the same magic-vision tint branch used by the dungeon peer path. When the flood walk finishes, the handler waits for a key/poll result, clears the side panel again, and calls back into the dungeon renderer to restore the first-person view before returning. The minimap is therefore an inspect overlay, not a persistent panel that waits for the next turn loop to erase it.

## 13. Z transitions and exiting

The Z axis is moved through *only* by K-Klimb (and by certain pit cells that auto-descend without input). K-Klimb routes to the dungeon overlay's K handler:

1. Read the underfoot tile and check the high nibble.
2. **Up ladder (`0x1`).** If Z is greater than zero, decrement Z; the party moves up to the same X, Y on the level above. If Z is already zero, the traced apply path refuses the level change rather than publishing a general plane-transition rule.
3. **Down ladder (`0x2`).** Increment Z when the current level is below seven; the traced apply path refuses descent below level seven.
4. **Two-way (`0x3`).** Prompt up/down.
5. **Exact pit byte `0x60`.** Bypass ordinary ladder apply and invoke the
   surface-reset helper.
6. **Other cells.** Return without a level change.

The up/down prompt accepts explicit up and down selections and the standard
cancel/pass keys. After a direction is chosen, the target level's same X/Y cell
is tested for passability; an obstructed destination prints the blocked
feedback and leaves Z unchanged.

The destination test is deliberately narrower than ordinary movement
passability. It reads the same X/Y cell on the target Z level and rejects plain
passage plus the major wall families (`0xB?`, `0xC?`, `0xD?`, and `0xE?`) when
strict checking is requested. Other feature families can be valid climb landing
cells; the check is a ladder-exit obstruction test, not a full terrain-effect
dispatcher.

Dungeon-to-overworld exits are split across two contracts:

- The surface-reset helper clears the dungeon scene and restores the party to
  the dungeon's exterior coordinate for exact `0x60` K-Klimb pit exits,
  explicit reset/edge paths, and combat-result level-change boundary paths.
- The pit-chain off-bottom path clears the scene after the chain increments the
  level past seven. It preserves the current X/Y and leaves the level byte at
  the incremented off-bottom value; it does not call the surface-reset helper
  or its exterior-coordinate tables.

A second exit path is the **exit-dungeon tile** — a small set of cells in some dungeons that the engine recognises as "exit immediately" and dumps the party back to the overworld regardless of Z. The third exit path is **death**: total party wipe routes to the death sequence and the dungeon mode terminates as part of the broader game-over flow. A fourth, terminal path exists for the endgame: dungeon-room and post-combat cleanup can consume the special combat absorption marker and enter the endgame overlay instead of restoring ordinary dungeon play. In stock data, the authored route is Doom level seven's room-id-fifteen trigger at local coordinate `(X=5, Y=7)`, which selects the final Doom room arena. The dungeon turn loop's only contract is that *if the scene byte drops to thirty-two or below, the loop exits*; how it got there is the caller's concern.

## 14. Combat triggers

Dungeon mode enters combat through fixed room triggers and through ordinary hostile-object contact or attack:

**Room cells (high nibble `0xF` sub-types, plus runtime `0xA` state).** Walking onto a room cell triggers the load of a `DUNGEON.CBT` arena. The arena is selected by the active dungeon scene and the room cell's low nibble. The combat framer (cf. the combat spec) takes over; on resolution the party returns to the room cell with whatever damage and status changes the fight produced.

Room entry also snapshots the dungeon-local active-object state before the
combat scene marker is installed. The helper prints the entering-room feedback,
sets the initial combat-facing byte from the active dungeon record, clears the
arena buffer, loads the selected `DUNGEON.CBT` arena, records the pre-room
scene and party X/Y, and then marks the scene as combat-class for the framer.
Those snapshots are handoff state for returning from the room; they are not a
second persistent dungeon monster list.

If the combat room returns with the special absorption result marker set, the
room cleanup does not perform the ordinary return-to-room path. It enters the
terminal endgame overlay. This is a post-combat room outcome, not a normal
dungeon movement command, not a TALK conversation, and not a generic room-cell
teleport. The combat spec owns the marker writer; the endgame spec owns the
terminal overlay sequence.

The stock Doom final room is the concrete room that connects these pieces. Its
`DUNGEON.DAT` trigger is the deepest-level room marker whose low nibble is
fifteen. The scene/room arithmetic maps it to Doom arena slot fifteen, the last
record in `DUNGEON.CBT`. That arena carries the special room setup marker that
feeds the absorbable active-object path consumed by the special post-step
absorption hook. The room-trigger setup pass scans sixteen metadata source cells
from the loaded arena; in the final Doom record, the first scanned source cell
is the `0x3C` absorbable-field family marker. A compatible implementation must
preserve both the room-trigger selection and the final arena's metadata band;
treating the arena as visible terrain only loses the terminal handoff.

Room setup also builds a temporary eleven-by-eleven combat/view layout. The
layout starts from a corridor/room pattern, overlays facing-dependent
decorative glyphs, then seeds monster/NPC starting positions from room tables
and random placement. That generated layout is the combat/view input; it is not
a persistent rewrite of the dungeon cell grid.

While building the local room layout, the room painter also updates the
resident tile-restoration flag used later by the combat framer. A two-way
ladder cell sets the flag and dispatches the associated local presentation
helper; other non-empty icon classes clear it. If the following room combat
returns through the combat framer with the flag still set, the framer calls the
display-driver tile-graphics restore mode before redrawing the world view. This
flag is a room-layout/display handoff, not a trap-damage or loot signal.

**Wandering monsters.** Some non-room cells spawn random monsters at intervals — an encounter roll runs in the per-turn epilogue, and on success spawns monsters in adjacent cells. Combat begins on attack.

After a successful dungeon action, the active monster can step toward the
party. If that step makes it adjacent, the dungeon post-action hook can rotate
the party to face the threat and launch combat without waiting for an explicit
A-Attack.

The active monster step is a wrapped, randomized greedy move over the current
8-by-8 level. Stationary monster presentation ids skip movement. Otherwise the
helper tests a small randomized set of cardinal step candidates, rejects pit
cells, sleep-field cells, and wall/door-class cells, and prefers a candidate
that reduces distance to the party. A committed step updates the paired
dungeon active-object slots so the renderer sees the old and new positions
consistently. If the chosen candidate is the party's cell, the helper returns a
contact flag instead of merely moving the object.

When that contact flag is set, dungeon mode determines the cardinal direction
from the party to the active monster using wrapped adjacency, prints the
approach-direction feedback if the party was not already facing that way,
commits the new facing, redraws and pauses briefly, then launches a dungeon
combat encounter using the active monster's sprite id. After combat returns,
the mode runs the normal post-combat redraw/time/view-initialisation bracket
and redraws the first-person viewport if the scene is still a dungeon.

The `DUNGEON.CBT` arena file is much larger than the overworld combat file because each dungeon has many distinct rooms. The arena format is the same eleven-by-eleven terrain-grid-plus-metadata-band format described in the maps spec. The room-entry helper computes the arena index as:

```text
dungeon_record = scene - 33
arena_bank = 0 if dungeon_record <= 1 else dungeon_record - 1
arena_slot = trigger_cell & 0x0F
arena_index = arena_bank * 16 + arena_slot
```

This gives Deceit records `0..15`, Destard `16..31`, Wrong `32..47`, Covetous `48..63`, Shame `64..79`, Hythloth `80..95`, and Doom `96..111`. Despise shares the bank-zero arithmetic path, but the stock Despise dungeon record has no `0xF?` room-trigger cells. Doom room id fifteen reaches record `111`; this final record is part of the stock compatibility surface, not padding.

## 15. Time integration

Dungeon turns advance the world clock at the indoor rate: one minute per consumed turn. The per-turn epilogue calls the same world-clock advance routine that town turns use. The clock cascades normally: daily Shadowlord hideout maintenance runs at midnight, and month-boundary character counters and long-period flag clears run when the day wraps past 28, even though the player is underground.

Two dungeon-specific consequences: **lighting decay** (the torch and
light-spell counters tick down each turn — § 7), and **record month counters**
(the per-character month counter advances on the same calendar boundary as it
does in towns; `systems/time.md` owns the inn-billing consumer and the
no-separate-active-consumer boundary).

Time does *not* advance during prompts (camp duration, Y/N drink, etc.). The Q-mode pendulum mentioned in § 4 is a quest-mode feature; in normal dungeon play it stays disabled.

## 16. Persistence

The dungeon-mode state that survives save and load is small: the scene byte / dungeon record, the current Z/Y/X and facing, the torch and light-spell counters, the room-clear bitmap, the flavour byte (recomputable from the scene), and broader quest flags such as whether a dungeon's deepest reward has been claimed. The global active-object table is still part of the save image, but dungeon exploration does not use it as its first-person actor list; active-object replacement happens only when the dungeon hands off to combat.

The dungeon-tile data itself is reloaded from `DUNGEON.DAT` on fresh dungeon
entry, one 512-byte dungeon record at a time. While the party remains in that
dungeon scene, the loaded cell image is also part of the flat save image, so a
save/load round trip inside the dungeon preserves visit-local cell edits such
as opened doors, dispelled fields, trap rewrites, and the immediate
room-trigger cell patch. Leaving and later re-entering the dungeon rebuilds the
working image from `DUNGEON.DAT`; only durable state such as the room-clear
bitmap is then replayed. Cleared room completion persists separately in that
bitmap, and the reload-time demotion pass reconstructs the navigable `0xA?`
room-helper cells from the static `0xF?` source cells. *An Grav*-cleared energy
fields therefore survive an in-dungeon save/load, but reappear after leaving and
re-entering from the static dungeon record.

The scene byte is persisted; on load, if the saved scene byte is in the dungeon range, the engine restores the above and re-enters the dungeon turn loop in the saved level and position.

## 17. Dungeon Boundaries

Dungeon mode is complete at gameplay-loop depth: scene/record binding, first
person rendering gates, command parsing, movement and turning, L-Look/V-View,
Search/Open/Get handoffs, K-Klimb, room combat triggers, post-action monster
engagement, trap effects, room-clear persistence, and save/load behavior are
specified. Low-nibble names outside the published gameplay subtypes and
V-View/minimap pixel confirmation are catalog or presentation QA work, not
missing dungeon-loop behavior. The pit-chain off-bottom state mutation is
specified, and stock data cannot produce that edge.

- **Low-nibble sub-type boundary.** The high-nibble class table (§ 3) is well
  evidenced, and gameplay subtypes are published for fountains, energy fields,
  room ids, the named pit/trap bytes, visit-local marker bits, and Search/Open/Get
  rewrites. Unnamed ordinary wall and door variants, trap marker variants
  outside the named Search/post-action bytes, and secondary field-family visuals
  are catalog/presentation labels. Treat the low nibble as opaque variant data
  unless a system spec names the subtype.
- **Dungeon Search trap thresholds.** Dungeon Search's light gate,
  high-nibble feature classes, chest trap-tier narration, pit-family reveal,
  bomb branch, and `0xC?`/`0xD?` rewrites are now covered. Remaining trap
  exactness belongs to still-untraced caller-side trap selection tables, not to
  the local dungeon Search feature classifier.
- **V-View visual parity.** The minimap painter's class-to-glyph ids and flood
  expansion rules are specified. Visual confirmation of those glyph ids against
  the active font/tile bank and pixel placement of the multi-cell
  fountain/stair helper belongs to presentation QA, not the flood ownership
  rule.
- **Open/Get chest traps.** Search's chest trap narration is covered here, while
  Open owns the trap-springing gameplay path and Get owns the seven-row
  open-chest reward generator specified in `containers.md`.
- **Random-encounter cadence and monster sets per level** — see `encounters.md`.
- **Pit-chain off-bottom stock-data boundary.** Chained pit falls that run past
  level seven clear the dungeon scene byte with the off-bottom level byte and
  same X/Y still in resident state. The dungeon-side state mutation is covered,
  and a stock `DUNGEON.DAT` scan found no shipped fall-trap placement or
  vertical chain that can produce it. Preserve the covered state mutation as
  defensive compatibility behavior for custom or mutated dungeon data.

## 18. Sources

The behaviour described here was derived by reading the private function notes listed below. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The dungeon turn loop's structure -- initialisation, flavour selection, underfoot reaction, render-and-poll, dispatch, epilogue -- derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The dungeon viewport frame, status row redraw, render-and-poll helper,
  active-object setup and placement, and room-entry state handoff -- derived
  from `u5-decomp/functions/DUNGEON_OVL/0x0332_draw_view_panel.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x01D2_dungeon_status_redraw.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x03D6_dungeon_render_and_poll.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0134_dungeon_view_init.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0252_dungeon_place_active_object.md`,
  and `u5-decomp/functions/DUNGEON_OVL/0x0000_dungeon_room_enter.md`.
- The first-person renderer's sparse point-plotting model, distance bands, direction-delta-table indexing, side/front wall pass order, helper pipeline, back-buffer redraw bracket, and binary light gate -- derived from `u5-decomp/functions/DUNGEON_OVL/0x1A90_dungeon_render_3d.md`, `u5-decomp/notes/system-trace_dungeon-rendering.md`, and cross-checked against `u5-decomp/CORRECTIONS.md`.
- The dungeon-entry scene/name/record binding, selected-record load, and entry seed coordinates — derived from the MAINOUT E-Enter helper and its dungeon-entry subhelper, cross-checked against `u5-decomp/formats/data-ovl.md`.
- The mode-aware letter dispatch table including the dungeon-specific routes for A-Attack, K-Klimb, L-Look, T-Talk, V-View, and the H-Hole-up overworld path — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The dungeon Look handler's tile-class switch, light gate, `0x61` description normalisation, and fountain Y/N drink flow — derived from `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`. The relative focus prompt and coordinate writer used by dungeon Look and Search — derived from `u5-decomp/functions/SJOG_OVL/0x006C_sjog_dir_step.md` and `u5-decomp/functions/SJOG_OVL/0x002A_sjog_apply_dir_step.md`. The View handler's centered flood map, wait/clear/restore flow, and peer-spell tint branch — derived from `u5-decomp/functions/DNGLOOK_OVL/0x06A8_dnglook_v_view.md`.
- The wrapped dungeon cell reader's class-sensitive `0x08` normalization and
  the front-cell renderer's extra-glyph/active-object overlay use of that bit
  -- derived from `u5-decomp/functions/DUNGEON_OVL/0x10DC_dungeon_get_cell.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x1952_dungeon_draw_outer_cell.md`, and
  `u5-decomp/notes/system-trace_dungeon-rendering.md`.
- The first-person renderer helper contracts -- active-object sprite painting,
  field strobe painting, glyph/sprite source selection, single-glyph
  decoration families, front blocker classification, side-wall classification,
  sparse point-pair wall painting, and composite redraw sequencing -- derived
  from `u5-decomp/functions/DUNGEON_OVL/0x111E_dungeon_draw_active_object.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x127E_dungeon_draw_field_object.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x134A_dungeon_draw_object_at_depth.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x145C_dungeon_draw_glyph.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x150A_dungeon_check_blocking.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x1682_dungeon_draw_wall_at_depth.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x1786_dungeon_draw_walls_for_cell.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x1952_dungeon_draw_outer_cell.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x1BE0_dungeon_redraw_after_action.md`,
  and `u5-decomp/functions/DUNGEON_OVL/0x104C_dungeon_handle_wall_decor.md`.
- The dungeon Search handler's light gate, high-nibble feature descriptions,
  chest trap-tier narration, pit-family secret reveal, `0xC?`/`0xD?`
  visit-local rewrites, and bomb branch - derived
  from `u5-decomp/functions/SJOG_OVL/0x0646_sjog_search_inner.md`.
- The dungeon Get open-chest consumption and seven-row reward-generator shape -
  derived from `u5-decomp/functions/SJOG_OVL/0x179E_sjog_get_dungeon_chest.md`.
- The dungeon post-action tile-effect pass, including exact `0x61`/`0x69`
  fall traps, exact `0x62`/`0x6A` bomb traps, visit-local trap-cell rewrites,
  sleep-field one-shot resolution, and poison-field repeat resolution --
  derived from `u5-decomp/functions/DUNGEON_OVL/0x0C76_dungeon_post_action.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0948_dungeon_field_sleep.md`, and
  `u5-decomp/functions/DUNGEON_OVL/0x09E6_dungeon_field_poison.md`.
- The dungeon movement destination-effect boundary and electric-field force-step path -- derived from `u5-decomp/functions/DUNGEON_OVL/0x0502_dungeon_move_dispatch.md` and `u5-decomp/functions/DUNGEON_OVL/0x0470_dungeon_field_force_step.md`.
- The DUNGEON.DAT layout (eight dungeons by eight levels by eight by eight cells, packed nibbles per cell) and the DUNGEON.CBT layout (combat arenas indexed by adjusted dungeon scene and room low nibble) — derived from `u5-decomp/formats/maps.md` and the dungeon room-entry helper.
- The stock `DUNGEON.DAT` fall-trap reachability boundary -- fall traps exist,
  but no level-seven trap or same-column vertical fall-trap run reaches level
  seven -- derived from a local semantic scan of
  `C:\Games\U5-Clean\DUNGEON.DAT`.
- The per-scene tile buffer interpretation that dungeon mode shares with the rest of the engine for non-overworld scenes — derived from `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The dungeon command parser, K-Klimb dispatch/apply paths, pit-chain fall path, dungeon attack-forward handler, and surface-reset exit helper - derived from `u5-decomp/functions/DUNGEON_OVL/0x06C4_dungeon_command_handler.md`, `u5-decomp/functions/DUNGEON_OVL/0x1E10_dungeon_klimb_dispatch.md`, `u5-decomp/functions/DUNGEON_OVL/0x1C6A_dungeon_klimb_apply.md`, `u5-decomp/functions/DUNGEON_OVL/0x0A4C_dungeon_pit_chain.md`, `u5-decomp/functions/DUNGEON_OVL/0x1D4A_dungeon_attack_forward.md`, and `u5-decomp/functions/DUNGEON_OVL/0x1D08_dungeon_fall_pit.md`.
- The dungeon active-monster step, auto-facing contact path, and automatic
  dungeon-combat launch bracket -- derived from
  `u5-decomp/functions/DUNGEON_OVL/0x07E2_dungeon_monster_step.md` and
  `u5-decomp/functions/DUNGEON_OVL/0x0B7E_dungeon_encounter_face.md`.
- The K-Klimb destination passability check is derived from
  `u5-decomp/functions/DUNGEON_OVL/0x1C0C_dungeon_cell_passable.md`.
- The DNGLOOK minimap cell painter, passage/room painters, room-clear bitmap reader/writer, cleared-room demotion pass, room NPC setup, and view teardown/init helpers - derived from `u5-decomp/functions/DNGLOOK_OVL/0x0340_v_view_paint_cell.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0284_paint_stair_glyph.md`, `u5-decomp/functions/DNGLOOK_OVL/0x097E_paint_passage_full.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0A48_paint_passage_short.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0AEE_paint_passage_medium.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0B9E_paint_passage_from_party.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0C6C_paint_room_layout.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0D3E_paint_room.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0FDA_apply_movement.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0844_set_room_cleared.md`, `u5-decomp/functions/DNGLOOK_OVL/0x08D4_is_room_cleared.md`, `u5-decomp/functions/DNGLOOK_OVL/0x093A_demote_cleared_room_markers.md`, `u5-decomp/functions/DNGLOOK_OVL/0x109E_init_dungeon_view.md`, `u5-decomp/functions/DNGLOOK_OVL/0x1130_teardown_dungeon_view.md`, and `u5-decomp/functions/DNGLOOK_OVL/0x117E_setup_room_npcs.md`.
- The H-Hole-up code path's per-slot rest, ambush check, and HP regeneration — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The world-clock advance contract and the integration with combat for room-trigger and wandering-monster encounters — derived from sibling specs `u5-spec/systems/time.md` and `u5-spec/systems/combat.md`.
