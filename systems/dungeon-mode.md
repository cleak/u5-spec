# Dungeon mode

## 1. Overview

Ultima V's dungeon mode is the third top-level world mode, after the overworld and the town/dwelling/castle/keep family. Where those modes paint top-down tile views of the world, dungeon mode paints a first-person three-dimensional wireframe view of a small grid the player walks through cell by cell. There are eight such grids — the named dungeons of Britannia, in resident entry and `DUNGEON.DAT` record order: Deceit, Despise, Destard, Wrong, Covetous, Shame, Hythloth, and Doom. Each dungeon is a stack of eight levels, and each level is a square eight-by-eight grid of cells. The player enters from a fixed surface or underworld location, descends or ascends through ladders, fights room encounters that swap into combat mode, and either climbs back out the way they came in or wins the dungeon's deepest reward and exits.

Structurally, dungeon mode is a sibling of town mode: it has its own per-turn loop, its own special tile reactions, its own command handler that forwards letter inputs to the resident A-Z dispatcher, and its own per-turn epilogue that advances the world clock. It differs in three important ways. First, the floor is not a tile grid the player sees from above — it is a 3D wireframe of what the party would see standing inside the dungeon. Second, the renderer is not a raycaster but a table-driven 2D line-drawing pass that paints precomputed wall segments per distance band. Third, NPC schedules do not run in dungeons — there are no scheduled inhabitants underground — so the per-turn loop never invokes the NPC scheduler.

This spec describes the scene byte that selects which dungeon and entry mode is active, the on-disk and in-memory layout of dungeon levels, the per-turn loop, the special tile reactions, the wireframe renderer, the lighting model, movement and turn commands, Z-axis ladder transitions, the look and view commands, camp/sleep, the room-encounter combat trigger, time integration, and how the player exits a dungeon.

## 2. The dungeon scene byte

The engine's scene byte is a single resident state byte that every world-mode loop reads to know what kind of scene is being played. The value zero is the overworld; values one through thirty-two are towns and other location interiors; values from thirty-three through one-hundred-twenty-seven route through the dungeon dispatcher; values from one-hundred-twenty-eight upward are combat. The stock game uses eight normal dungeon scenes, thirty-three through forty. The dungeon turn loop runs while the scene byte is greater than thirty-two, and exits when it drops to thirty-two or below — that is the engine's signal that the player has climbed back out and the overworld should re-engage.

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

The flavour drives a few cosmetic divergences in dungeon wall/corpse descriptions and corner glyphs. The flavour label is a presentation class, not the dungeon's in-world name; for example, the named dungeon Doom uses the normal presentation class in the stock table above. The flavour byte does not change geometry or tile semantics — it only changes a small number of presentation strings. The current dungeon for geometry and room-arena selection is the scene / `DUNGEON.DAT` record. Treat any extra entry, facing, or flavour state bytes as runtime auxiliaries rather than as an independent public dungeon index.

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
| `0xA`       | Room-helper state              | Routed through the same underfoot helper as room triggers (§ 5). |
| `0xB`–`0xE` | Wall variants                  | Solid blockers (with one debug "SPEC WALL ERR" sentinel at `0xD`). |
| `0xF`       | Heavy door / room trigger      | Sub-types: door, trigger. |

The high nibble drives wall checks in the renderer and the cell-description string in L-Look. The low nibble varies per class — for fountains it picks cure/heal/poison/bad-taste; for energy fields it picks the four sub-types; for ladders and walls it carries decorative or direction flags. For L-Look only, exact byte `0x61` is normalised to `0x00` before description, so it reports as passage even though the underlying cell byte remains a pit-family variant. Other observed `0x6?` trap bytes, including `0x69`, `0x62`, and `0x6A`, keep their `0x6` class description.

## 4. Per-turn loop

Each consumed turn runs the dungeon turn loop once. Its structure is parallel to the town turn loop's:

**Initialisation.** Set a "rendering-pending" visibility flag, run a one-shot boot-tick on the first turn after entry, read the underfoot tile, and cache its high nibble.

**Status painting.** Paint the side panel border and the status row showing the current level number and facing direction ("Dungeon Level N", "Facing North"). Repainted each turn because the player may have changed level or direction during the previous turn.

**Flavour selection.** Read the scene byte, pick one of the three flavour values (§ 2), and write the corner-glyph pair and flavour byte that the renderer and L-Look will consume.

**Underfoot reaction.** If the cached high nibble is room-helper state (`0xA`) or room trigger (`0xF`), run the room-entry helper — which loads a combat arena from `DUNGEON.CBT` and hands off to combat mode (§ 5, § 14). Otherwise run a brief re-init pass: a visibility hint, the torch burn-down call, and a view-renderer initialise.

**Inner loop.**
1. **Pendulum tick.** In Q-quest mode the loop alternates between running and skipping the time-advance call so quest scenes pass time at half rate. Normal play keeps the pendulum disabled.
2. **Render and poll.** Paint the 3D wireframe (§ 6) and wait for a keystroke. If input idled long enough that the player slept through one tick, the primitive returns a special "idle slept" sentinel.
3. **Dispatch.** The keystroke goes to the dungeon command handler, which routes numpad direction keys to the dungeon movement dispatcher, digit keys to a digit helper, control-S to a sound toggle, the Q letter to an "Exit to DOS?" prompt, and any letter A-Z to the resident command dispatcher (§ 10).
4. **Scene-byte exit check.** If the scene byte has dropped to thirty-two or below, the player has climbed out (§ 13) and the loop breaks.
5. **Refresh tile cache.** Re-read the underfoot tile and update the cached high nibble.
6. **Post-action hook.** If the dispatch did anything, call a post-action helper for end-of-turn cleanup.
7. **Idle slot.** If the dispatch did nothing (unrecognised key), enter a short polling step that prints "Zzzzzz..." at the appropriate cadence and re-polls input.

**Epilogue.** Toggle the appropriate visibility flag bit so the next render runs a full repaint, call the per-turn redraw primitive, and call the world-clock advance routine — the same routine town and combat call — with a one-minute increment. Time in dungeons advances at the indoor rate. If the input poll reported end-of-stream / quit, run the dungeon-exit teardown.

The loop then iterates, checking the scene byte; if it is still in the dungeon range, the next turn begins.

## 5. Special underfoot reactions

Two underfoot tile classes have *immediate* effects that fire before the player can act:

**Room-helper state (high nibble `0xA`).** The turn loop routes `0xA?` cells through the same helper as `0xF?` room triggers. The shipped `DUNGEON.DAT` records contain no `0xA?` cells; this class appears as runtime state created after a room trigger resolves, not as ordinary stock geometry. Keep the low nibble intact because the helper still treats it as the room-arena slot.

**Room trigger (high nibble `0xF`).** A subset of cells flagged as "room cells" trigger a room encounter when the party walks onto them. The same room-entry helper used by the `0xA?` state loads the appropriate arena from `DUNGEON.CBT`, sets combat-entry state, and hands off to combat. After combat resolves, the player re-emerges in the dungeon at the room cell. The helper patches the loaded dungeon image for that visit by changing `0xF?` to `0xA?`; the on-disk source cell is unchanged.

A third class of effect — **energy fields** (high nibble `0x8` or `0x9`) — fires not from the underfoot reaction but as part of *moving into* the cell. Stepping into a field-bearing cell triggers the effect *before* the move completes, applying status or damage to the moving party member or the whole party. The four sub-types are sleep, poison gas, wall of fire, and electric.

A fourth — **wind tiles** — extinguishes any active torch on contact ("A breeze blows out the torch."), leaving the light-spell counter unaffected.

## 6. The 3D wireframe renderer

Dungeon mode's defining feature is its first-person three-dimensional wireframe view, painted into the side panel each turn. The renderer is *not* a raycaster. It is a table-driven 2D line-drawing pass that paints a fixed, precomputed set of wall segments per distance band, with per-band geometry chosen by the cells' high nibbles in the eight-by-eight floor grid.

**Distance bands.** The view is composed of five distance bands, indexed zero through four. Band zero is the cell directly under the party's feet (the floor in front of you); band four is four cells ahead. The renderer walks bands nearest to farthest, painting each band's geometry on top of the previous one. Bands beyond four are not rendered — the dungeon visibility budget is exactly four cells of forward depth.

**Direction-delta tables.** To compute "what cell is N steps ahead", the renderer indexes two small four-entry tables — one for the X delta and one for the Y delta — by the facing direction byte. Each table holds the per-step offset for each cardinal direction. The renderer reads the cell at `(player_X + dx * (band + 1), player_Y + dy * (band + 1))` for each band.

**Wall checks.** For each band, the renderer reads the cell's tile byte and consults the high nibble. If the nibble identifies a wall class (`0xB` through `0xE`, plus door sub-cases of `0xF`), the band paints a wall segment at the appropriate viewer-relative depth. Open-passage cells are painted as a void: the wireframe shows the floor and ceiling outlines extending farther forward. Closed doors paint a door rectangle; open doors paint as a passage.

**Side-wall mirroring.** The renderer also reads the two cells immediately to the left and right of the centre cell at that depth, and paints the corresponding side walls. The right-wall X pixel is computed as `panel_width − margin − left_X`, so the renderer paints bilateral wall geometry per band, not just a single wall ahead.

**Precomputed line tables.** The actual line endpoints for each wall segment at each distance band live in small lookup tables in the data segment — one table per wall variant, with entries giving start and end pixel coordinates for each line in the segment. The renderer's inner loop is a tight sequence of "look up segment, draw line, advance" calls into a 2D line primitive. There is no per-pixel projection math.

**Far-wall extras.** After painting the near-to-far primary walls, the renderer walks back outward, painting the symmetric far-wall counterparts and the ceiling and floor outline corners that connect them. The result is a complete cell-by-cell wireframe of the corridor or chamber the player is looking down.

**Light gate.** Before any of the above runs, the renderer checks the torch radius and the light-spell radius. If both are zero, the renderer paints nothing — the side panel goes black, and the player sees only the status row and message panel. This "pitch dark" state is the gating reason torches and light-spells are gameplay-critical underground. The renderer is otherwise purely a function of the eight-by-eight floor data, the party's position and facing, and the lighting state.

## 7. Light sources

Two state bytes track the player's light:

- **Torch radius.** A counter that decrements once per dungeon turn while a torch is lit. When it reaches zero, the torch goes out. The I-Ignite command consumes one torch; in dungeon scenes it adds 112..127 turns to the current torch counter, capped at 255.
- **Light-spell radius.** A separate counter tracking the duration of the light spells. *In Lor* sets it to 100 turns; *Vas Lor* sets it to 255 turns. It ticks down per turn alongside the torch counter.

Either counter being non-zero "lights" the dungeon — the renderer paints, L-Look describes the selected focus cell, and movement proceeds normally. Both counters being zero darkens the dungeon: the renderer paints nothing, L-Look returns "darkness" regardless of what is actually in front of you, and the player must light a torch (or cast the light spell) to see again.

Other observed sources: **wind tiles** extinguish a lit torch on contact, leaving the spell counter alone; **spellbook lighting** items can bump the torch counter at every per-turn cleanup; **shrines** in some levels emit light; certain decorative tiles (the "gargoyle eyes" of one or two dungeons) are visual flavour only. The decay of the two counters is part of the world-clock advance call, not the dungeon mode loop's own logic; the time system shares a saturating-byte helper that the dungeon and overworld both use.

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

**Chests.** A chest cell (high nibble `0x4`) prints "a wooden chest" on look. The Open command opens it; the chest may yield treasure, be empty, or trigger a trap. Chest contents are generated on open — the dungeon-tile byte does not encode contents.

**Pit and bomb traps.** The `0x6?` family is a trap family, not a uniform Z-transition class. Exact bytes `0x61` and `0x69` are fall traps. Stepping on either prints the pit/fall messages, clears the fired marker bits on the departure cell in the loaded dungeon image, increments dungeon level by one, and lands the party at the same X/Y on the next level. If the destination cell is below the wall/door band (`< 0x90`), the engine marks bit `0x08` in that destination cell before continuing. If the destination cell is another `0x61` or `0x69`, the handler repeats, so the practical drop depth is the length of the vertical trap chain at that X/Y, not a direct low-nibble-to-distance table. If the chain increments the level past seven, the dungeon scene byte is cleared and the mode loop exits. Exact bytes `0x62` and `0x6A` are bomb traps: they print the bomb messages, clear the current trap cell to its fired marker form, and do not change Z.

**Ladders.** Three classes:

- **Up ladder (`0x1`).** K-Klimb moves Z to Z−1 (or exits to the overworld if Z is already zero — § 13).
- **Down ladder (`0x2`).** K-Klimb moves Z to Z+1.
- **Two-way (`0x3`).** K-Klimb prompts up or down.

The level cap is seven; attempts to descend below seven are rejected unless the cell carries scripted "deeper transition" semantics (e.g. Hythloth's bottom ladder leads to the underworld).

**Heavy doors.** A door cell (high nibble `0xF` sub-type matching door) blocks movement until opened. The Open command (or a Jimmy attempt) toggles the door state for the rest of the visit. Walls are not openable; only door cells respond to Open.

**Special walls / secret doors.** Some walls are marked as secret doors. Searching adjacent to a secret door reveals it, after which it behaves like a normal door. The exact encoding lives in the low nibble of certain wall cells; the discovery flow is mediated by the Search handler, not by the renderer.

**Wind tiles.** Extinguish a lit torch on contact; the light-spell counter is unaffected.

## 9. Movement and turning

Dungeon mode's movement set is small and uses the numpad / arrow keys, *not* letter commands:

- **Forward.** Step one cell in the facing direction. The engine consults the cell at `(player_X + facing_dx, player_Y + facing_dy)`. If that cell's high nibble is a wall class, the move is rejected and "Blocked!" is printed. Otherwise the party advances one cell, the energy-field check fires (§ 8) if the destination is a field, and the turn ends. Forward through a closed door fails; through an open door succeeds.
- **Back.** Step one cell in the opposite direction. Same wall and field checks.
- **Turn left.** Decrement the facing byte by one (modulo four). Status row updates; the wireframe is repainted on the next loop iteration.
- **Turn right.** Increment the facing byte by one (modulo four).

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

## 11. Camp / sleep (H-Hole-up)

H in dungeons follows the overworld code path (the resident in-resident "rest with watch" wrapper) rather than the town's inn-tile hours-prompt. The wrapper:

1. Prompts for a rest duration in hours.
2. For each hour, runs the world-clock advance routine multiple times to accumulate sixty minutes per hour.
3. Per turn-of-rest, runs HP regeneration logic that gives a small random HP gain to each living, eligible party member.
4. Optionally rolls an ambush — in dungeons, the ambush replaces the camp with a combat arena (the dungeon-camp arena, loaded the same way room triggers load).
5. Cures the "asleep" status on every party member who was asleep at the start of the rest.

The rest concludes either with "Party rested!" or "Ambushed!" (and an immediate combat). The dungeon turn loop resumes when the rest finishes; the party's coordinates do not change.

A second H-path is involuntary: some sleep/ambush flows can interrupt rest without requiring the player to press H. The same regeneration and ambush logic applies, but stock `DUNGEON.DAT` room cells use the `0xF?` trigger family rather than authored `0xA?` cells.

## 12. Looking and viewing

Two letter commands give the player visibility into the dungeon beyond the wireframe:

**L-Look.** The L letter in dungeon mode routes to a dedicated dungeon-look overlay rather than the overworld/town look overlay. The handler:

1. Prompts for a party-member slot (the standard "by whom?" prompt; ESC cancels).
2. Checks the lighting gate: if both torch and light-spell counters are zero, prints "You see: darkness." and returns.
3. Invokes the shared dungeon target/focus helper with the current facing direction, then consumes the focus coordinates that helper leaves for the command. Ordinary L-Look inspects the focus cell in front of the party; the exact coordinate-producing helper remains an implementation-compatibility item in Section 17.
4. Reads the dungeon tile byte at `(Z, focus_y, focus_x)` from the loaded dungeon image. For description only, byte `0x61` is treated as `0x00`.
5. Prints "You see:" followed by a class-specific message. Energy-field bytes `0x80..0x83` have distinct sleep, poison-gas, fire, and electric descriptions, while other `0x8?` values share a generic energy-field description. Class `0xC?` is a flavour-presentation class whose text depends on the active dungeon flavour. The remaining high nibbles collapse to passage, ladder, chest, fountain, pit, open chest, nothing-of-note, wall, or heavy-door descriptions.
6. For the fountain class, runs the drink Y/N flow described in Section 8.

The fountain prompt is the only state-mutating L-Look class currently identified: it can change the selected party member's status, HP, or both. Other L-Look classes narrate the inspected feature only. L-Look does *not* repaint the wireframe; the message appears in the message panel and the wireframe stays as it was. L-Look does *not* advance time; it is a free action.

**V-View.** The V letter routes through the resident dispatcher before it reaches the dungeon-look overlay. The dispatcher requires a *gem of vision*, prints the no-gem refusal if the count is zero, and decrements the gem count before dispatching to the dungeon view handler.

The handler clears the side-panel viewport normally used by the wireframe and paints a top-down map centered on the party. It seeds a scratch flood walk at a center cell representing the party, maintains a visited map plus two row queues, tries the eight neighbouring scratch cells for each dequeued cell, maps each accepted scratch coordinate back onto the current 8-by-8 dungeon level relative to the party with wrapping, reads the corresponding `DUNGEON.DAT` byte, and paints a glyph based on that byte's high-nibble class. Wall-like cells stop flood expansion; passage-like cells continue it. The exact glyph-to-class artwork and a few floodability edge cases remain open in Section 17.

When peer-spell view mode is active, V-View applies the same magic-vision tint branch used by the dungeon peer path. When the flood walk finishes, the handler waits for a key/poll result, clears the side panel again, and calls back into the dungeon renderer to restore the first-person view before returning. The minimap is therefore an inspect overlay, not a persistent panel that waits for the next turn loop to erase it.

## 13. Z transitions and exiting

The Z axis is moved through *only* by K-Klimb (and by certain pit cells that auto-descend without input). K-Klimb routes to the dungeon overlay's K handler:

1. Read the underfoot tile and check the high nibble.
2. **Up ladder (`0x1`).** If Z is greater than zero, decrement Z; the party moves up to the same X, Y on the level above. If Z equals zero, the up-ladder takes the party out of the dungeon: the scene byte resets to zero (overworld), the party returns to the surface entry tile resolved from the active dungeon scene, and the dungeon turn loop exits at its scene-byte check.
3. **Down ladder (`0x2`).** Increment Z (within `0..7`).
4. **Two-way (`0x3`).** Prompt up/down.
5. **Other cells.** Print "Not climbable!" and return.

A second exit path is the **exit-dungeon tile** — a small set of cells in some dungeons that the engine recognises as "exit immediately" and dumps the party back to the overworld regardless of Z. The third exit path is **death**: total party wipe routes to the death sequence and the dungeon mode terminates as part of the broader game-over flow. A fourth, scripted path exists for the endgame — certain dungeons' deepest cells trigger scripted teleports or end-of-quest events. The dungeon turn loop's only contract is that *if the scene byte drops to thirty-two or below, the loop exits*; how it got there is the caller's concern.

## 14. Combat triggers

Dungeon mode enters combat through fixed room triggers and through ordinary hostile-object contact or attack:

**Room cells (high nibble `0xF` sub-types, plus runtime `0xA` state).** Walking onto a room cell triggers the load of a `DUNGEON.CBT` arena. The arena is selected by the active dungeon scene and the room cell's low nibble. The combat framer (cf. the combat spec) takes over; on resolution the party returns to the room cell with whatever damage and status changes the fight produced.

**Wandering monsters.** Some non-room cells spawn random monsters at intervals — an encounter roll runs in the per-turn epilogue, and on success spawns monsters in adjacent cells. Combat begins on attack.

The `DUNGEON.CBT` arena file is much larger than the overworld combat file because each dungeon has many distinct rooms. The arena format is the same eleven-by-eleven terrain-grid-plus-metadata-band format described in the maps spec. The room-entry helper computes the arena index as:

```text
dungeon_record = scene - 33
arena_bank = 0 if dungeon_record <= 1 else dungeon_record - 1
arena_slot = trigger_cell & 0x0F
arena_index = arena_bank * 16 + arena_slot
```

This gives Deceit records `0..15`, Destard `16..31`, Wrong `32..47`, Covetous `48..63`, Shame `64..79`, Hythloth `80..95`, and Doom `96..111`. Despise shares the bank-zero arithmetic path, but the stock Despise dungeon record has no `0xF?` room-trigger cells.

## 15. Time integration

Dungeon turns advance the world clock at the indoor rate: one minute per consumed turn. The per-turn epilogue calls the same world-clock advance routine that town turns use. The clock cascades normally: daily NPC-schedule maintenance runs at midnight, and month-boundary character counters and long-period flag clears run when the day wraps past 28, even though the player is underground.

Two dungeon-specific consequences: **lighting decay** (the torch and light-spell counters tick down each turn — § 7), and **long-stay counters** (the per-character month counter advances on the same calendar boundary as it does in towns).

Time does *not* advance during prompts (camp duration, Y/N drink, etc.). The Q-mode pendulum mentioned in § 4 is a quest-mode feature; in normal dungeon play it stays disabled.

## 16. Persistence

The dungeon-mode state that survives save and load is small: the scene byte / dungeon record, the current Z/Y/X and facing, the torch and light-spell counters, the flavour byte (recomputable from the scene), and broader quest flags such as whether a dungeon's deepest reward has been claimed. The global active-object table is still part of the save image, but dungeon exploration does not use it as its first-person actor list; active-object replacement happens only when the dungeon hands off to combat.

The dungeon-tile data itself is reloaded from `DUNGEON.DAT` on every dungeon entry, one 512-byte dungeon record at a time; saves do not persist runtime modifications. Opened doors, dispelled fields, and room-trigger state are visit-local changes to the loaded dungeon image. *An Grav*-cleared energy fields re-appear after a save and reload.

The scene byte is persisted; on load, if the saved scene byte is in the dungeon range, the engine restores the above and re-enters the dungeon turn loop in the saved level and position.

## 17. Open questions and variations

- **Low-nibble sub-type semantics.** The high-nibble class table (§ 3) is well evidenced; low-nibble semantics for walls, doors, trap marker variants, and the secondary field family are still partially open. Treat the low nibble as opaque variant data unless a system spec names the subtype.
- **Secret-door encoding.** The mechanism marking a wall as a secret door (and how Search reveals it) has not been completely traced. The likely encoding is a particular low-nibble value within a wall class, with Search reading and overwriting it on success.
- **L-Look focus coordinate producer.** DNGLOOK consumes focus coordinates produced by a shared target helper after pushing the facing direction. Ordinary behaviour is "look in front of the party", but the helper should be traced before treating that as a closed arithmetic formula.
- **V-View glyphs and floodability.** The minimap painter is structurally decoded, but exact glyph artwork and a few wall/door flood-expansion edge cases still need visual or movement-handler confirmation.
- **Wind-tile encoding.** Wind tiles are observed but the exact tile byte is not yet identified.
- **Chest traps.** The trap roll is gameplay-system territory inside the Open handler. The dungeon-mode contract is "the cell is a chest; route to Open".
- **Random-encounter cadence and monster sets per level** — see `encounters.md`.
- **Hythloth's underworld transition** at its bottom level is plausible but not fully traced.
- **Room-cell durability across save/load** needs a save-image trace. Current evidence shows visit-local runtime image changes, not patched `DUNGEON.DAT` bytes.
- **Dungeon-flavour gameplay differences.** Whether flavour also affects encounter tables, fountain probabilities, or trap difficulty is unclear; current evidence is consistent with "purely cosmetic".

## 18. Sources

The behaviour described here was derived by reading the private function notes listed below. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The dungeon turn loop's structure — initialisation, flavour selection, underfoot reaction, render-and-poll, dispatch, epilogue — and the 3D wireframe renderer's distance-band model and direction-delta-table indexing — derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The dungeon-entry scene/name/record binding, selected-record load, and entry seed coordinates — derived from the MAINOUT E-Enter helper and its dungeon-entry subhelper, cross-checked against `u5-decomp/formats/data-ovl.md`.
- The mode-aware letter dispatch table including the dungeon-specific routes for A-Attack, K-Klimb, L-Look, T-Talk, V-View, and the H-Hole-up overworld path — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The dungeon Look handler's tile-class switch, light gate, `0x61` description normalisation, and fountain Y/N drink flow — derived from `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`. The View handler's centered flood map, wait/clear/restore flow, and peer-spell tint branch — derived from `u5-decomp/functions/DNGLOOK_OVL/0x06A8_dnglook_v_view.md`.
- The dungeon post-action tile-effect pass, including exact `0x61`/`0x69` fall traps, exact `0x62`/`0x6A` bomb traps, and visit-local trap-cell rewrites — derived from local DUNGEON post-action and fall-trap helper analysis.
- The DUNGEON.DAT layout (eight dungeons by eight levels by eight by eight cells, packed nibbles per cell) and the DUNGEON.CBT layout (combat arenas indexed by adjusted dungeon scene and room low nibble) — derived from `u5-decomp/formats/maps.md` and the dungeon room-entry helper.
- The per-scene tile buffer interpretation that dungeon mode shares with the rest of the engine for non-overworld scenes — derived from `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`.
- The H-Hole-up code path's per-slot rest, ambush check, and HP regeneration — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The world-clock advance contract and the integration with combat for room-trigger and wandering-monster encounters — derived from sibling specs `u5-spec/systems/time.md` and `u5-spec/systems/combat.md`.
