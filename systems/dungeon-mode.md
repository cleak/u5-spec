# Dungeon mode

## 1. Overview

Ultima V's dungeon mode is the third top-level world mode, after the overworld and the town/dwelling/castle/keep family. Where those modes paint top-down tile views of the world, dungeon mode paints a first-person three-dimensional view of a small grid the player walks through cell by cell. There are eight such grids — the named dungeons of Britannia, in resident entry and `DUNGEON.DAT` record order: Deceit, Despise, Destard, Wrong, Covetous, Shame, Hythloth, and Doom. Each dungeon is a stack of eight levels, and each level is a square eight-by-eight grid of cells. The player enters from a fixed surface or underworld location, descends or ascends through ladders and through the two dungeon level-change spells, fights room encounters that swap into combat mode, and leaves by passing the top or the bottom of the level stack - which always returns the party to that dungeon's own outdoor entrance cell, on Britannia from the top and in the Underworld from the bottom.

Structurally, dungeon mode is a sibling of town mode: it has its own per-turn loop, its own special tile reactions, its own command handler that forwards letter inputs to the resident A-Z dispatcher, and its own per-turn epilogue that advances the world clock. It differs in three important ways. First, the floor is not a tile grid the player sees from above — it is a 3D first-person view of what the party would see standing inside the dungeon. Second, the renderer is not a raycaster and not a line renderer; it composites pre-drawn billboard bitmaps chosen by cell class and depth band. Third, NPC schedules do not run in dungeons — there are no scheduled inhabitants underground — so the per-turn loop never invokes the NPC scheduler.

This spec describes the scene byte that selects which dungeon and entry mode is active, the on-disk and in-memory layout of dungeon levels, the per-turn loop, the special tile reactions, the billboard first-person renderer, the lighting model, movement and turn commands, Z-axis ladder transitions, the look and view commands, camp/sleep, the room-encounter combat trigger, time integration, and how the player exits a dungeon.

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
| `0x7`       | Open chest                     | Produced at runtime by dungeon Open on a wooden chest; Get loots it and consumes it. Renders as passage, but L-Look, Search, Open, and Get all treat it as an open chest, not as floor. It never occurs in the shipped dungeon file. |
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

**Status painting.** Repaint the two chrome bands and the two framed labels they carry: the four-cell level label in the top band and the twelve-cell facing label in the bottom band. Their exact cells and their exact stored literals are specified in section 4.1 — the labels are terse field abbreviations, not sentences. Repainted each turn because the player may have changed level or direction during the previous turn.

**Flavour selection.** Read the scene byte, pick one of the three flavour values (§ 2), and write the corner-glyph pair and flavour byte that the renderer and L-Look will consume.

**Underfoot reaction.** If the cached high nibble is room-helper state (`0xA`) or room trigger (`0xF`), run the room-entry helper — which loads a combat arena from `DUNGEON.CBT` and hands off to combat mode (§ 5, § 14). Otherwise run a brief re-init pass: a visibility hint, the torch burn-down call, and a view-renderer initialise.

**Inner loop.**
1. **Pendulum tick.** In Q-quest mode the loop alternates between running and skipping the time-advance call so quest scenes pass time at half rate. Normal play keeps the pendulum disabled.
2. **Render and poll.** Paint the first-person view (§ 6) and wait for a keystroke. The primitive blocks until an accepted key arrives; if it returns a negative sentinel rather than a dispatchable key, the loop skips step 3 for that iteration. The sleep line is not produced here — it belongs to the party-capability check of step 7.
3. **Dispatch.** The keystroke goes to the dungeon command handler, which routes the four cardinal direction codes — and Enter and the period key, which mean "advance" here — to the dungeon movement dispatcher; digits to the solo-member selector, always reporting "no action" afterwards; the four shared Control bindings (exit-to-DOS prompt, moral-standing readout, sound toggle, version banner) to their own arms; and everything else, letters included, to the resident command dispatcher (§ 10). The handler's own default is "acted", so an unrecognised byte forwarded to the dispatcher reports whatever the dispatcher decides.
4. **Scene-byte exit check.** If the scene byte has dropped to thirty-two or below, the player has climbed out (§ 13) and the loop breaks.
5. **Refresh tile cache.** Re-read the underfoot tile and update the cached high nibble.
6. **Post-action hook.** If the dispatch did anything, call a post-action helper for end-of-turn cleanup.
7. **Party-capability check.** The iteration then ends by running the shared party-capability check specified in `systems/main-loop.md` Section 6 — the same check town and overworld mode run, with the same three-way result mapping — before the loop reads another command. The check also runs once on entry, ahead of the first command read, and it runs on every iteration regardless of what the dispatch reported, so a command that took no turn (a refused Klimb, say) skips the post-action helper of step 6 but still passes through the check. If at least one member can act, the loop proceeds to the next iteration. If nobody can act but at least one member is asleep, the loop pauses briefly, prints the sleep line ("Zzzzzz..."), and re-runs the check without reading a command, repeating for as long as that result holds; the dungeon takes this pass without running the post-action helper. If nobody can act and nobody is asleep, the inner loop stops and the epilogue runs the total-party-defeat sequence (§ 13.4). Dungeon mode contributes no condition of its own to the check.

**Epilogue.** Toggle the appropriate visibility flag bit so the next render runs a full repaint, call the per-turn redraw primitive, and call the world-clock advance routine — the same routine town and combat call — with a one-minute increment. Time in dungeons advances at the indoor rate. If the party-capability check of step 7 reported that nobody can act and nobody is asleep, the epilogue's last act is to run the total-party-defeat sequence of `systems/blackthorn.md` Section 7; the per-turn redraw/view-helper pass named above runs immediately before it, as bookkeeping rather than as a condition on it. An earlier revision described this tail call as a dungeon-exit teardown fired by an end-of-stream / quit poll result; that reading is withdrawn.

The loop then iterates, checking the scene byte; if it is still in the dungeon range, the next turn begins.

### 4.1 Presentation and Input Helpers

The dungeon loop owns a small amount of presentation state around the
first-person renderer:

**The two chrome bands.** On dungeon-mode entry the loop paints the viewport's
static chrome once. It consists of two horizontal bands drawn in the resident
chrome pen, each with an accent rule along its inner edge:

| Band | Filled span | Accent rule |
|---|---|---|
| Top | x 40 to 152, y 0 to 7 | a horizontal line at y = 7 |
| Bottom | x 48 to 152, y 185 to 191 | a horizontal line at y = 184 |

Both labels are written in **whole-screen character cells** - text window 0,
which spans the entire forty-by-twenty-five grid, so window cells equal screen
cells. The top band is text row 0 and the bottom band is text row 23.

**The level label.** The top band carries a framed level label occupying
**four cells, 10 through 13**:

| Cell | Content |
|---|---|
| 10 | right end-cap glyph |
| 11 | the capital letter `L` |
| 12 | one digit: the one-based level |
| 13 | left end-cap glyph |

The stored literal is the letter followed by **one space**, but that space is a
**placeholder**. It exists only to advance the cursor past cell 11 when the
panel is first drawn; the status redraw seeks back to cell 12 and prints the
digit over it. The rendered result therefore has **no space between the letter
and the digit**, and the label is always exactly four cells wide. The level
byte is stored zero-based and displayed as one more than its stored value, in a
one-wide space-padded field, so the displayed range is one through eight.

**The facing label.** The bottom band carries a framed facing label occupying
**twelve cells, 6 through 17**:

| Cell | Content |
|---|---|
| 6 | right end-cap glyph |
| 7 to 10 | `D` `i` `r` `:` |
| 11 | a pad space that is never overwritten |
| 12 to 16 | the five-character facing field |
| 17 | left end-cap glyph |

The stored prefix literal is `Dir:` followed by **six** spaces - ten characters
in all - and the redraw overwrites only the last five of those with the facing
name.

The subtlety that makes the rendered spacing look uneven is that **two of the
four facing names carry their own leading space** and the other two do not.
All five are five characters wide, so the label never changes length:

| Facing code | Stored name | Rendered label |
|---:|---|---|
| 0 | `North` | `North` after one space |
| 1 | `_East` (leading space) | `East` after two spaces |
| 2 | `South` | `South` after one space |
| 3 | `_West` (leading space) | `West` after two spaces |
| anything else | `_????` (leading space, four question marks) | `????` after two spaces |

The last row is the **invalid-facing fallback** and is a real, reachable
presentation state; it is the same five-character width as a real name, so the
label geometry is unchanged. The facing encoding is north, east, south, west in
that order.

**Cell-arithmetic correction.** The facing label's gap between its two end caps
is **ten cells (7 through 16), not eleven**. The surface wind banner's gap is
eleven cells (7 through 17), because its content is a five-character wind name
plus the six-character suffix ` Winds`. Both labels begin at the same cell 6 and
share the same band, the same pixel spans and the same accent rule row, but the
dungeon label's closing cap sits one cell to the left of the wind banner's.
The two are not an identical ribbon and must not be specified as one. The
padding conventions are mirror images as well: wind names pad on the **right**
and their suffix carries a leading space, so a short wind name yields two spaces
*before* the word `Winds`; facing names pad on the **left** behind a prefix that
carries trailing pad, so a short facing name yields two spaces *after* the
colon. The surface producers for the same two slots are specified in
`systems/moons.md` (top slot, the sky strip) and `systems/weather.md` section
2.1 (bottom slot, the wind banner); the shared frame and end-cap contract is in
`systems/display-driver.md` section 7.

**Shared border slots.** The surface sky strip and the dungeon level label are
the same top slot; the surface wind banner and the dungeon facing label are the
same bottom slot. All three producers use the same pixel spans (x 40 to 152 on
top, x 48 to 152 on the bottom), the same accent rule rows (y = 7 and y = 184)
and the same whole-screen text window. They differ only in how many cells of the
band their label occupies and in which columns the caps land. There is never a
conflict, because both surface renderers test the scene byte and return
immediately in dungeon mode.

**Status row refresh cadence.** The status redraw selects the whole-screen text
window, seeks to the level digit cell, prints the one-based level, seeks to the
facing field, prints the facing name, and restores the previously active window
before returning. It runs immediately after the chrome is first drawn, and again
after **every** three-dimensional repaint - which includes the return from the
map view, so both labels are rewritten on exiting the map even though the map
never damaged them.

**The entry facing seed is walk-in-only.** Walking into a dungeon from the
overworld sets the facing explicitly as part of the entry seed (Section 3).
**Loading a saved game never runs that code**, so a saved facing survives
untouched and the party resumes facing whatever the save recorded. A
spec-conformant engine must apply the seed on walk-in entry and must **not**
apply it on load; a save whose facing field is zero starts the party facing
north, not east.

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
eight dungeon monster presentation records, installs that record's display
sprite byte and its **combat class id**, resets the visibility flag, stamps the
current Z level, and lazily loads the sprite source if placement succeeds. The
two per-record bytes are distinct: one is presentation, the other is the combat
class the wandering-monster combat path consumes directly (§ 14.1). The eight
classes are Giant Rat, Bat, Giant Spider, Ghost, Slime, Gremlin, Gazer, and
Reaper. Placement makes up
to eight random attempts on the current 8-by-8 level, accepting only cells in
the pit and open-chest spawn families (`0x6?` or `0x7?`) — both of which the
renderer paints as passage — and rejecting the party's
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
id. This bitmap is part of the save image. It has one bit per dungeon-room arena
record - one hundred twelve bits, fourteen bytes - and the bit index is the same
`arena_bank * 16 + room_id` value used to select the `DUNGEON.CBT` record
(§ 14). When a level is loaded or reloaded, room-marker cells whose clear bit is
set are demoted from `0xF?` to `0xA?`, preserving the room id low nibble. They
are not demoted to `0xE?`. This keeps the cleared-room runtime state consistent
across save/load without changing `DUNGEON.DAT`.

The bitmap **writer** consults a small resident deny-list before setting a bit.
The list holds six `(dungeon, room)` pairs; when the room being resolved matches
one of them, the writer returns without setting anything. In shipped data the
deny-listed rooms are rooms one, six, eleven, and twelve of the Wrong bank and
rooms zero and eleven of the Covetous bank - three of which are among the rooms
that carry randomised `0xEC..0xEF` sources. Those six rooms therefore never
persist as cleared and re-arm on every visit. The bitmap
**reader** applies no deny-list, so it simply always reports those rooms as not
cleared. Note that the deny-list is keyed by the raw dungeon record number,
while the bit index uses the collapsed arena bank, so an implementation must not
reuse one for the other.

A third class of effect — **energy fields** (high nibble `0x8` or `0x9`) — fires not from the underfoot reaction but as part of *moving into* the cell. Stepping into a field-bearing cell triggers the effect *before* the move completes, applying status or damage to the moving party member or the whole party. The four sub-types are sleep, poison gas, wall of fire, and electric.

No mapped dungeon contact path defines a stock **wind tile** that extinguishes
torches. The traced movement-into-cell and post-action tile-effect dispatchers
cover room triggers, sleep/poison/fire/electric fields, pits, and
fountains/bombs, but do not write the torch counter through a breeze or gust
cell. Baseline-compatible implementations should not add a
`DUNGEON.DAT` wind-contact behavior; wind/gust artwork belongs to transient
presentation effects unless a variant handler is explicitly being modeled.

## 6. The First-Person Renderer

**Correction to earlier revisions.** Earlier revisions of this section described
the corridor as a *sparse* renderer that plots precomputed pixel constellations
taken from four coordinate-pair tables named forward wall, side door, side wall
and corner. **That reading is withdrawn.** The corridor is drawn from
**billboard bitmaps** held in the dungeon art files, which is why the shipped
game shows a textured brick corridor with mortar courses, darker recessed side
openings at each depth band, and dithered floor and ceiling planes converging on
a small far wall - rather than an outline of dots. The four sparse
coordinate-pair tables are real, but they are the **animated fountain water**
(Section 6.7); they have nothing to do with walls, doors or corners.

The renderer is not a raycaster either. There is no projection arithmetic and no
depth buffer. It classifies each cell, selects a bitmap by role and depth band,
blits it at a fixed destination, and relies on painter's-algorithm ordering.
Depth shading is baked into the artwork, not applied by the renderer.

### 6.1 Screen geometry and the frustum

The renderer draws into the back buffer and then composites a rectangle to the
front buffer. Three rectangles matter and they are not the same:

| Rectangle | Extent | Role |
|---|---|---|
| Composite rectangle | x 16 to 175, y 14 to 178 | What the renderer blits from the back buffer to the front buffer each repaint. |
| Pixel-plot clip rectangle | x 40 to 152, y 42 to 183 | Installed before drawing; it bounds the point-plotting primitive only. |
| Visible art | x 16 to 175, y 16 to 175 | The nearest band's aperture: a 160-pixel square. Its corners are the outermost non-transparent pixels the player can see. |

The rows between the composite rectangle and the visible art are the
billboards' transparent margin. A black-box raster measurement of the lit view
therefore reports approximately `(16,16)` to `(175,175)`, and that is correct;
an earlier estimate of `(16,17)` to `(174,174)` is superseded.

The **vanishing point is (96, 96)**, the centre of the visible art.

Every placement constant in the renderer falls out of one sequence, the
**per-band half-aperture**. The view is a nest of concentric squares centred on
the vanishing point; the opening at band `b` is the square whose edges lie
`hw[b]` pixels either side of the vanishing point in both axes.

| Band `b` | Cell it describes | `hw[b]` | Wall x-edges | Ceiling line y | Floor line y |
|---:|---|---:|---|---:|---:|
| 0 | the party's own cell | 80 | 16 and 176 | 16 | 176 |
| 1 | one cell ahead | 56 | 40 and 152 | 40 | 152 |
| 2 | two cells ahead | 24 | 72 and 120 | 72 | 120 |
| 3 | three cells ahead | 8 | 88 and 104 | 88 | 104 |

**Band 0 is the party's own cell, not the cell ahead.** The side cells of band 0
are the cells immediately left and right of the party, and they frame the view
at its outer edge; the "forward" test at band 0 is the party's own cell, which
is normally open. An earlier revision that computed each band's cell as the
party's position plus the facing delta times `band + 1` is off by one and is
withdrawn.

The original pre-fills only the right half of the composite rectangle with black
before drawing. The left half is always fully covered by opaque billboards, so
the asymmetry is an artefact of the original's mirrored-blit path. An
implementation that clears the whole rectangle and draws both halves opaquely is
conformant and will not differ visibly.

### 6.2 The billboard banks

There are **three interchangeable corridor art files**, one per presentation
flavour byte (Section 2): flavour 1 selects the first, flavour 2 the second,
flavour 3 the third. The file is chosen once, on dungeon-mode entry, from a
three-entry filename table indexed by the flavour byte, and the object sprite
file is loaded alongside it.

**All three corridor files have byte-identical directories**; only the pixels
differ. That is the whole of the "different dungeons look different" mechanism:
a clean implementation needs one geometry and three texture sets. Both banks are
released and the world tile atlas reloaded when dungeon mode ends.

The directory holds **twenty-eight entries**, of which **two are deliberately
absent** (Section 6.4 explains why). Every image is **164 rows tall** and is
drawn at a **fixed vertical origin of y = 14**, so the only per-image variable
is horizontal placement.

| Role | Band 0 | Band 1 | Band 2 | Band 3 |
|---|---|---|---|---|
| Side wall | 24 wide | 32 wide | 16 wide | 8 wide |
| Side door | 24 | 32 | 16 | 8 |
| Side opening | 24 | 32 | 16 | 8 |
| Side flavour wall | 24 | 32 | 16 | 8 |
| Forward wall | *absent* | 56 | 24 | 8 |
| Forward door | **80** | 56 | 24 | 8 |
| Forward flavour wall | *absent* | 56 | 24 | 8 |

Two invariants make the widths self-checking:

- A **side** image's width is `hw[b] - hw[b+1]` - the thickness of the ring
  between its own band's aperture and the next band's (80-56, 56-24, 24-8,
  8-0).
- A **forward** image's width is `hw[b]` itself, because each forward billboard
  is a *half* wall drawn twice.

The forward-door family's band-0 entry is an **80-wide image that stands in for
every blocker family at band 0** - wall, door and flavour wall alike, because
the renderer overrides the family selection at that range (Section 6.4). That is
why the band-0 entries of the forward wall and forward flavour wall families are
absent from the directory: nothing ever asks for them. Those are the two empty
slots a reader of the shipped files will notice.

A second art file holds the object sprites (Section 6.6). A third bank is
allocated on demand for the active wandering object. Neither the corridor bank
nor the object bank is used by the map view (Section 12).

### 6.3 The placement rule

Every corridor image is drawn **twice**: once at its left position and once
horizontally mirrored. The rule is one sentence:

> `x_right = 192 - x_left - width`

which is the reflection of the left rectangle about the vertical centre line at
x = 95.5. For both families the left position is `96 - hw[b]`:

| Band | Left x | Side image right x | Forward image right x |
|---:|---:|---:|---:|
| 0 | 16 | 152 | 96 |
| 1 | 40 | 120 | 96 |
| 2 | 72 | 104 | 96 |
| 3 | 88 | 96 | 96 |

The forward family's mirrored copy therefore always begins exactly at the
centre line, and the two halves meet seamlessly. Every destination rectangle in
the corridor reproduces exactly from the half-aperture sequence and these two
rules; no further tables are needed.

### 6.4 Cell class to image

**Side cells.** For each band the renderer paints the cell to the left and the
cell to the right, using the perpendicular of the facing direction. The image is
chosen from the side cell's high nibble:

| Side cell | Image family |
|---|---|
| Any class below the door families - passage, ladders, chest, fountain, pit, open chest, energy field, and the unused `0x9?` class | Side **opening** |
| `0xA?` heavy door, `0xE?` heavy door, `0xF?` room trigger | Side **door** |
| `0xC?` flavour wall | Side **flavour wall**, plus the decoration of Section 6.8 |
| `0xB?`, `0xD?` plain wall | Side **wall** |

Note that class `0x9?` selects the *opening* image, not the wall image; every
class below the door families does.

**The forward cell.** The forward test reports "see-through" for any cell below
the door families, and the sweep continues to the next band. Otherwise it paints
a blocker twice - left copy then mirrored copy - and reports "blocked":

| Forward cell | Band 1 | Band 2 | Band 3 |
|---|---|---|---|
| `0xA?` heavy door | forward door | forward door | forward door |
| `0xB?` wall | forward wall | forward wall | forward wall |
| `0xC?` flavour wall | forward flavour wall | forward flavour wall | forward flavour wall |
| `0xD?` wall | same as `0xB?` | same | same |
| `0xE?` heavy door | forward door | forward door | forward door |
| `0xF?` room trigger | forward door | forward door | forward door |

**At band 0 every blocker family uses the single point-blank image**, whatever
its class - the override is unconditional, and it is the reason the three band-0
forward directory entries do not exist.

Two special cases at band 0:

- A `0xE?` heavy door in the party's own cell paints the point-blank door image
  and then reports **see-through anyway**, so the sweep advances one more cell
  and the doorway shows depth behind it. It also sets the renderer's
  point-blank flag, which suppresses the band-0 side walls so the door frame is
  not boxed in.
- A `0xF?` room trigger has no such pass-through. (In practice the player never
  sees it, because stepping onto a room-trigger cell enters combat.)

The band-0 side cells are also skipped when the caller's point-blank gate
argument is clear, which is how the composite redraw of Section 6.9 forces the
near frame on.

Two flavour-conditional extras hang off the forward test:

- A `0xB?` wall one cell ahead whose low nibble is non-zero routes to the
  per-dungeon scenery-text handler, which is what prints the dripping-stalactite
  family of ambient lines.
- A `0xC?` flavour wall one cell ahead in a **flavour-3** dungeon has a rare
  decorative flourish: on roughly a one-in-sixteen roll it draws four short
  strokes near the vanishing point in a bright accent pen. It is visual only,
  and it is the visual half of the flavour-3 easter egg noted in Section 2.

### 6.5 Sweep order

The renderer performs two sweeps over the same four cells.

1. **Forward sweep**, band 0 through 3. Band 0 is the party's own cell; each
   subsequent band steps one cell along the facing direction. At each band the
   renderer runs the forward test, then - if the band is not skipped - paints the
   two side cells. The sweep stops at the first band whose forward test reports
   "blocked".
2. **Backward sweep**, from the deepest accepted band back to band 0, painting
   forward-facing objects, sprites, fields and active-object overlays. This is
   the renderer's entire depth sorting: nearer bands paint over farther ones,
   with no depth buffer.

Every cell read wraps X and Y independently to the range `0..7` before indexing
the level image, so a sweep that steps off the edge of the eight-by-eight floor
tiles seamlessly into the opposite side.

**Light gate.** Before any of the above runs, the renderer reads the torch
counter and the light-spell counter as **booleans only**. Either non-zero
renders the full corridor; both zero fills the viewport interior with black and
draws nothing else. There is no progressive dimming and no radius: the counters'
numeric values never reach the renderer.

The unlit fill covers the **viewport interior only** - the square x 8 to 183,
y 8 to 183. The viewport's frame outline, both border bands and therefore the
level and facing labels of Section 4.1, the right-hand roster panel and the
message window all lie outside it and stay lit. Igniting a torch restores the
corridor on the next redraw with no transition effect.

### 6.6 Object sprites

Objects standing in a cell are drawn from a separate art file holding **twenty
sprites in five families of four**, one sprite per depth band. Each sprite is
stored as a colour image **plus a separate one-bit transparency mask of the same
dimensions**, so objects composite over the corridor art rather than punching
opaque rectangles through it.

| Family | Band 0 | Band 1 | Band 2 | Band 3 |
|---|---|---|---|---|
| Ladder | 40 x 80 | 24 x 56 | 16 x 24 | 8 x 8 |
| Fountain | 40 x 80 | 24 x 56 | 16 x 24 | 8 x 8 |
| Pit | 40 x 24 | 24 x 32 | 16 x 16 | 8 x 8 |
| Chest | 40 x 24 | 24 x 32 | 16 x 16 | 8 x 8 |
| Open chest | 40 x 24 | 24 x 32 | 16 x 16 | 16 x 16 |

Cell class selects the family and the drawing mode:

| Cell class | Rising sprite | Floor sprite |
|---|---|---|
| `0x1?` up ladder | ladder | - |
| `0x2?` down ladder | - | ladder |
| `0x3?` both ladders | ladder | ladder |
| `0x4?` closed chest | - | chest |
| `0x5?` fountain | - | fountain, plus the water animation of Section 6.7 |
| `0x6?` pit | - | pit |
| `0x7?` open chest | - | open chest |

Closed and open chests are visually distinct sprites, and the bidirectional
ladder genuinely draws both a rising and a descending sprite in the same cell.

Placement follows three rules, all of which reproduce exactly from the
half-aperture sequence:

- Like corridor images, every sprite is drawn as a **left half at x 56, 72, 80
  or 88** for bands 0 to 3 and a **mirrored right half beginning at the centre
  line**, so the two halves meet at x = 96.
- **Floor-standing objects** - pit, chest, open chest - are positioned so their
  **bottom edge sits on the floor line of their band**: y = 176, 152, 120, 104.
- A **rising ladder** is positioned so its **bottom edge sits on the horizon**
  at y = 95, so it climbs from the vanishing row up to the ceiling. A
  **descending ladder and a fountain** hang from the horizon downward, starting
  at y = 96.

An extra overlay sprite is drawn for cells in the active-object classes when the
cell's overlay bit is set, using the pit sprite family in rising mode. Energy
fields (class `0x8?`) are drawn by their own animated strobe helper rather than
from this sprite bank; the field's low nibble selects the flavour. Where the
level's dropped-item coordinates match a swept cell at a band other than 0, the
dropped-item painter also runs.

### 6.7 The fountain water animation

The four sparse coordinate-pair tables that earlier revisions attributed to
walls are the **animated water of a fountain**. Each is a three-frame point
animation, one point set per depth band. The frame counter advances by one,
modulo three, once per band-0 paint, so the whole view shares a single
animation phase.

Each point is plotted **once at the coordinate given and once mirrored about the
vertical centre line**, i.e. at `190 - x`. Points are plotted individually;
there is no line drawing. The animation is drawn in a single blue pen, with the
nearest band re-issuing a brighter blue, and it is **suppressed entirely on
two-colour adapters**, where the pen resolves to the background.

Absolute left-hand screen coordinates, per band and per frame. Each point also
appears at its mirror.

**Band 0** (18 points per frame including the mirrors):

| Frame | Points |
|---|---|
| 0 | (90,115) (82,119) (95,123) (87,125) (91,131) (80,133) (80,133) (80,133) (89,145) |
| 1 | (87,115) (94,119) (81,122) (93,125) (95,129) (85,130) (89,135) (80,139) (80,144) |
| 2 | (84,117) (90,117) (90,124) (80,126) (85,136) (89,138) (89,138) (89,138) (85,143) |

**Band 1** (10 points per frame including the mirrors):

| Frame | Points |
|---|---|
| 0 | (94,103) (91,106) (85,107) (95,116) (85,123) |
| 1 | (90,102) (89,111) (95,111) (84,112) (87,122) |
| 2 | (87,104) (94,107) (88,115) (83,117) (90,124) |

**Band 2** (8 points per frame including the mirrors):

| Frame | Points |
|---|---|
| 0 | (91,97) (95,100) (89,102) (91,104) |
| 1 | (90,98) (94,98) (92,106) (92,106) |
| 2 | (93,97) (89,100) (89,105) (89,105) |

**Band 3** (2 points per frame including the mirror):

| Frame | Point |
|---|---|
| 0 | (94,96) |
| 1 | (93,97) |
| 2 | (95,98) |

Two readability notes. The repeated trailing coordinates - band 0 frames 0 and
2, band 2 frames 1 and 2 - are genuine padding: the original's loop runs a fixed
byte count, so the last coordinate is simply re-plotted. An implementation may
deduplicate them freely. And the geometry is self-consistent: band 3's points
sit within a pixel of the vanishing point, band 2's within a small box around
it, and band 0's span x 80 to 110 and y 115 to 145, which is the near
fountain's spray sitting on the floor plane directly over its sprite.

The fourth band of the animation draws nothing beyond its single point; the
fountain sprite itself is always drawn first by the object pass.

### 6.8 Wall decorations

Flavour walls in **flavour-1 (normal) dungeons only** carry a five-stage
decoration animation - the falling droplet the player sees on a mossy wall. It
is drawn as a three-pixel cross (one horizontal run and one vertical run through
the same centre) with a brighter centre pixel, in the same blue pen family as
the fountain water.

Horizontal position is fixed per band and side:

| Placement | Band 0 | Band 1 | Band 2 |
|---|---:|---:|---:|
| Side cell, left | x = 33 | x = 67 | - |
| Side cell, right | x = 157 | x = 123 | - |
| Forward cell | - | x = 95 | x = 95 |

Vertical position advances through the five stages:

| Placement | Stage 0 | 1 | 2 | 3 | 4 |
|---|---:|---:|---:|---:|---:|
| Side cell, band 0 | y = 28 | 37 | 64 | 112 | 173 |
| Side cell, band 1 | y = 54 | 59 | 74 | 98 | 133 |
| Forward cell, band 1 | y = 54 | 61 | 80 | 114 | 160 |
| Forward cell, band 2 | y = 60 | 64 | 76 | 96 | 123 |

The stage is stored in the **low three bits of the level cell itself**, and the
painter writes the next stage back, so the animation's state persists in the
live level map for the duration of the visit. Stage 0 advances only on a
one-in-sixteen roll; stages 1 through 4 advance on every paint; stage 4 uses a
brighter pen and omits the extra centre pixel; the stage after 4 draws nothing,
plays a short falling-pitch tone whose pitch depends on the band, and resets the
cycle to 0.

Only stages 0 through 4 are producible by the animation. An implementation
should treat each placement as exactly five entries and clamp; the original's
tables run into their neighbours past stage 4, but that region is unreachable.

### 6.9 Cell reads, active objects and the composite redraw

**Cell reads.** Every renderer-facing cell read wraps X and Y independently to
the range `0..7`, then reads the current Z-level image. For cell bytes below
`0x90`, bit `0x08` is ignored by clearing it before class interpretation. For
classes `0x9?` and higher, bit `0x08` remains meaningful as a render-side
overlay/extra-glyph flag. This bit is not persistent visibility memory.

**Fields.** Energy-field cells draw animated horizontal strobe lines. The strobe
uses per-field resident parameters for vertical band, row count, and row
spacing, plus a field-specific pen choice. The exact row coordinates are
randomized within the configured bands each render pass.

**Active objects.** Active monster, Codex, Shadowlord, and similar dungeon
sprites are drawn by an animated sprite helper keyed to the global dungeon
animation phase and the current creature record. The helper can apply small
random flicker/direction variants, has a special quest-scene sprite-table path,
and paints a paired sprite/mask result when the dungeon sprite source is loaded.
If the sprite source is unavailable, it falls back to text presentation rather
than silently painting a blank object.

**Composite redraw.** Commands that mutate dungeon state use a composite redraw
helper: reset the prompt/status presentation, render the viewport with the
point-blank gate forced on, blit the composite rectangle from the back buffer to
the front buffer, run the local presentation tick, and redraw the two border
labels of Section 4.1. This is a repaint helper, not a game-state transition,
and it is the path the map view returns through.

Source provenance: derived from private analysis note
`../u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`, and
re-verified against the shipped dungeon art directories.

## 7. Light sources

Two state bytes track the player's light:

- **Torch counter.** A remaining-duration counter for a burning torch. It is
  spent as the party takes dungeon turns, and when it reaches zero the torch
  goes out. The I-Ignite command consumes one torch from inventory and refuses
  when none are carried; in dungeon scenes it adds a random 112..127 counter
  units to the current torch counter, capped at 255.
- **Light-spell counter.** A separate remaining-duration counter for magic
  light. *In Lor* sets it to 100 counter units, *Vas Lor* sets it to 255, and
  the Light scroll sets it to 240. It drains on the same cadence as the torch
  counter.

Neither byte is a radius. Both are durations; the lighting system recomputes an
ambient value every turn and merely raises it to a floor while either counter
is burning, and inside the dungeon renderer the two counters are consulted only
as a binary lit/unlit gate. The first-person view never reads the ambient value
at all: the dawn/dusk curve and the squared-distance thresholds of
`systems/lighting.md` have no effect underground. A dungeon turn spends one counter unit; the exact
decay cadence, the counter unit, and the ambient floors are specified in
`systems/lighting.md` sections 4 and 5.

Either counter being non-zero "lights" the dungeon — the renderer paints, L-Look describes the selected focus cell, and movement proceeds normally. Both counters being zero darkens the dungeon: the renderer paints nothing, L-Look returns "darkness" regardless of what is actually in front of you, and the player must light a torch (or cast the light spell) to see again.

No dungeon feature writes either counter. Shrine glow strips, Codex glow, and
decorative tiles such as the "gargoyle eyes" of one or two dungeons are
presentation only: they brighten what is drawn without touching the light
state, so they never make an unlit dungeon visible. An earlier draft of this
section claimed that spellbook lighting items bump the torch counter at every
per-turn cleanup; that claim is withdrawn. The torch counter is written only by
I-Ignite, by the G-Get "borrow a lit fixture" branch (100 counter units, see
`systems/containers.md`), and by the Blackthorn restoration, which zeroes both
counters; the light-spell counter is written only by *In Lor*, *Vas Lor*, the
Light scroll, and that same Blackthorn clear. The analyzed dungeon contact
paths do not include a wind/breeze tile that extinguishes only the torch
counter. The decay of the two counters is part of the world-clock advance call, not the dungeon mode loop's own logic; the time system shares a saturating-byte helper that the dungeon and overworld both use.

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

The three chest commands form one lifecycle built from a single rewrite idiom:
keep the cell's variant bit, then replace the class and the remaining low bits.
A successful dungeon Jimmy rewrites a locked chest cell to the variant bit plus
the closed-chest class, which clears the lock/trap sub-type. Open rewrites that
cell to the variant bit plus the open-chest class. Get rewrites it to the
variant bit alone, which is a plain passage cell. Get therefore leaves floor
behind rather than promoting the cell to some further "looted chest" state,
because the class it is looting from already *is* the open-chest class — there
is nothing above it to promote to. There is exactly one write per command and no
second write elsewhere corrects it.

On stock data the post-loot cell value is always the plain passage byte with no
variant bit set: the shipped dungeon file contains no cell in the open-chest
class at all — that class exists only as runtime state — and every static chest
cell it does contain has the variant bit clear. The variant-bit preservation
must still be implemented, because the same bit is read by the dungeon view's
painter and by a dungeon overlay test, and the same preserve-bit-then-replace-
class idiom is used by other feature-consuming rewrites; custom or mutated
dungeon data can set it on a chest cell.

Dungeon Search also recognizes the chest class. In light, Search applies a
party-member stat roll against the current depth's trap difficulty and prints
no-trap, simple-trap, complex-trap, or generic-trap narration. The threshold is
`(2 * Z - member Dexterity + 30) / 2`, using the same unsigned halving
convention as the dungeon Jimmy chest path. This is the identical threshold
expression the dungeon lock-pick uses, borrowed purely as a detection roll; it
carries no lock semantics here and does not make Search a third lock-pick
formula. Search rolls `1..30` against that
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
| `0x62` | Rolls `1..30` against `(2 * Z - member Dexterity + 30) / 2`. A roll above the threshold springs the bomb, reports it, and clears the searched cell to `0x00`; a roll at or below the threshold reports nothing on the pit and leaves the cell unchanged. |
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

The dungeon Open command operates on the **underfoot tile** (not the cell in front). It can affect `0x4?` wooden chest cells and `0x7?` open-chest cells, but no traced Open or Jimmy mechanism mutates `0xA?`, `0xE?`, or `0xF?` dungeon door/room presentation cells. Room-trigger durability is handled by the room helper and the room-clear bitmap instead.

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

Dungeon movement does **not** echo the four direction words the surface and town
loops use. It has its own verbs, each printed into the message window and each
followed by a newline: `Advance`, `Back up`, `Turn left`, `Turn right`,
`Turn around.`, and the refusals `Blocked!` and `Not in doorway!` - the latter
belonging to the movement family and reachable from more than one arm, so a spec
should treat it as a movement refusal rather than binding it to one key.
Attacking straight ahead echoes
`Attack` with a newline and no direction hyphen, because a dungeon attack takes
no direction argument (`commands.md` section 5.2).

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

Letters that are no-ops in dungeons print "What?" or a stock refusal: **B** Board, **D**, **E** Enter, **F** Fire, **P** Push, **X** X-it. **Q** is the ordinary save-game route; the "Exit to DOS?" prompt is a Control binding in the mode-local table, not a letter.

The dungeon-mode A-Attack handler is a point-blank forward probe. It prints
the attack label, computes the wrapped cell one step ahead of the party's
current facing, and compares that coordinate with the single active dungeon
monster record. If the active monster is not exactly in that forward cell, the
handler uses the stock refusal response and does not launch combat.

If the active monster is in that forward cell, the handler sets the combat kind
byte to the ambush value, tears down the first-person view, synthesises a combat
arena and its metadata band in the room buffer, and calls the combat framer on
its ambush entry mode with the active monster's class byte. Section 14.1 owns
that contract in full; note in particular that no `DUNGEON.CBT` record is read
on this path and that the monster's class byte is used directly rather than
being derived from a sprite id. After combat returns, result code five moves the
party one level **up** — it decrements the level byte, and when the party is
already on the topmost level it instead takes the surface-exit path out to
Britannia; result code six moves the party one level **down** — it increments
the level byte, and when the party is already on the bottom level it takes the
same surface-exit helper, which in that case drops them into the Underworld.
Other combat results keep the party on the current level. This is the same
polarity as K-Klimb in Section 13: a smaller level byte is nearer the surface.
If the scene is still a dungeon after this post-combat step, the handler
re-initialises the dungeon view, rolls a replacement active monster, and
redraws the first-person view. Both surface-exit arms clear the dungeon scene,
which is exactly why that gate exists.

Before letters reach that dispatcher, the dungeon command parser intercepts
mode-local controls: the four cardinal direction codes plus Enter and the period
key as forward movement, the four shared Control bindings (exit-to-DOS prompt,
moral-standing readout, sound toggle, version banner), digits as a solo-member
select that always reports "no action", and idle/sleep notifications. The
exit-to-DOS prompt is one of those Control bindings, not the `Q` letter — `Q`
reaching the resident dispatcher is the ordinary save-game route. This is why
ordinary shared commands such as M-Mix still work in dungeons: they are not
handled by the local parser and fall through to the resident command dispatcher.

Dungeon mode is also the one mode that does not run the shifted-digit-to-
direction translation of `input.md` Section 5. Shifted or NumLock-ed top-row
digits stay ordinary digits underground and select a solo party member like any
other digit.

## 11. Camp / sleep (H-Hole-up)

H in dungeons follows the overworld code path (the resident "rest with watch"
wrapper) rather than the town's inn-tile hours-prompt. The wrapper:

1. Prompts for a rest duration in hours.
2. Elapses the accepted duration by calling the world-clock advance routine
   repeatedly in five-minute steps, twelve steps per simulated hour. This loop
   does **not** enter the shared party status pass, so no poison damage,
   provision spend, or starvation accrues while it runs. It does issue one Ring
   of Regeneration roll per five-minute step, directly rather than through the
   status pass. See `systems/time.md` section 5 and `systems/rest-and-camp.md`
   section 5.
3. Applies recovery only on the completed long-camp path, and only once at the
   end of the rest rather than once per hour. The dungeon H path reaches the
   same shared hole-up handler as the overworld, so the guard set, the `1..63`
   hit-point roll, the class-keyed magic-point write, and the fourteen-game-hour
   camp cooldown specified in `systems/rest-and-camp.md` section 5 apply here
   unchanged. An earlier revision of this section described step 3 as a per-hour
   "small random HP gain" applied to every living member; that was wrong on both
   cadence and guards and is withdrawn.
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

The handler clears the viewport normally used by the first-person view and
paints a top-down map centred on the party.

### 12.1 Map geometry

The map is a **twenty-two by twenty-two grid of eight-by-eight-pixel cells** -
484 cells in all. Grid cell `(0,0)` begins at the top-left corner of the
published clear rectangle, and a cell's pixel origin is

> `x = 8 * grid_x + 8`, `y = 8 * grid_y + 8`

so cell `(0,0)` occupies pixels `(8,8)` to `(15,15)` and cell `(21,21)` ends at
`(183,183)`. Twenty-two cells of eight pixels **exactly fill** the clear
rectangle `(8,8)` to `(183,183)`, which is the same viewport interior the
first-person view uses, so the two views cover identical ground.

**Correction.** Earlier revisions of this section described a twelve-row cell
whose "lower four rows" were left untouched. That is wrong in both directions:
the cell is eight rows tall and every row of it is drawn. The twelve-row reading
came from a misread of two unused values in the original and is withdrawn here
so it is not re-derived later. Every per-cell geometry below spans rows `y`
through `y + 7` of an eight-row cell.

The party always occupies the **centre cell `(11,11)`**, which is pre-marked as
visited before the flood begins, so the flood never paints over the party
marker.

**The wrap rule** is what makes a twenty-two-cell window possible over an
eight-by-eight floor: the dungeon coordinate of a grid cell is the party's
coordinate plus the cell's offset from the centre, taken **modulo eight in both
axes**. The level therefore tiles about two and three-quarter times across the
window. What the player sees is a view onto a wrapped torus, not a single copy
of the floor - this is deliberate and matches how the first-person sweep wraps.

### 12.2 The flood

The painter is an **eight-connected breadth-first walk** seeded at the party's
centre cell, using a visited grid so each cell is painted at most once. Diagonal
steps are permitted and there is **no corner-cutting test**: the walk can slip
between two diagonally touching walls. The neighbour order is northwest, north,
northeast, west, east, southwest, south, southeast.

A cell stops the walk if it is outside the grid, already visited, or one of the
three solid wall classes. Every other class paints its glyph and continues.

The frontier queue is a fixed ring of **two hundred fifty-six entries with no
occupancy check**. Shipped data never approaches that bound, but an
implementation should treat "the frontier never exceeds 256 pending cells" as a
requirement of the contract rather than as an incidental property, and should
not substitute an unbounded queue that would paint a differently shaped map on
hand-authored data.

### 12.3 The glyph source

The map does **not** use the corridor billboards or the object sprites of
Section 6. It uses the engine's two fixed **eight-by-eight one-bit fonts** - the
text font and the runic font. Each holds one hundred twenty-eight glyphs of
eight bytes, one byte per row, most significant bit leftmost. Every published
glyph identifier below is an index into whichever of the two fonts the class
selects.

Most classes select the **runic** font. Four deliberately select the **text**
font instead: three of them for directional arrows the runic font does not have,
and one for a solid block - the runic font's slot at that index is blank, which
is precisely why the bedrock class does not switch fonts.

Each cell is drawn opaquely in a foreground/background pair, so a painted cell
fully replaces whatever was underneath it.

Two classes are not font characters at all but small vector drawings; their
geometry is published below.

### 12.4 Floodability and the class-to-glyph table

Minimap floodability is its own presentation rule, not dungeon movement
passability. The per-cell painter returns "expand" for most classes after
painting their glyph. Only the wall presentation classes `0xB?`, `0xC?`, and
`0xD?` stop expansion. Heavy-door and room-trigger families (`0xA?`, `0xE?`,
and `0xF?`) paint door glyphs but still return expand to the flood walker.
The open-chest class paints nothing and still returns expand.

| Dungeon high nibble / exact byte | Font | Minimap output | Flood expands past cell |
|---|---|---|---|
| `0x0?` with bit `0x08` set | text | Up-arrow glyph `0x18`. | Yes. |
| `0x0?` without bit `0x08` | - | No glyph; the cell stays black. | Yes. |
| `0x1?` | runic | Up-ladder glyph `0x2E` (bar at the top). | Yes. |
| `0x2?` | runic | Down-ladder glyph `0x2D` (bar at the bottom). | Yes. |
| `0x3?` | runic | Two-way-ladder glyph `0x2F` (both bars). | Yes. |
| `0x4?` | runic | Closed-chest glyph `0x70`. | Yes. |
| `0x5?` | vector | Fountain drawing; see below. | Yes. |
| Exact `0x60` | text | Down-arrow glyph `0x19`. | Yes. |
| Exact `0x61` or `0x69` | runic | Hidden/fall-pit glyph `0x71`. | Yes. |
| Exact `0x68` | text | Up-and-down-arrow glyph `0x12`. | Yes. |
| Other `0x6?` | runic | Trap/blocker glyph `0x72`. | Yes. |
| `0x7?` | - | No glyph; the open chest is not drawn on the map. | Yes. |
| `0x8?` | vector | Energy-field drawing; see below. | Yes. |
| `0x9?` | - | No glyph. | Yes. |
| `0xA?` or `0xF?` | runic | Heavy-door glyph `0x73`. | Yes. |
| Exact `0xB0` | **text** | Solid block glyph `0x7F` - bedrock. The runic font's slot at this index is blank, so this class deliberately keeps the text font. | **No.** |
| Other `0xB?` | runic | Latticed wall glyph `0x74`. | **No.** |
| `0xC?` | runic | Speckled diagonal wall glyph `0x75`, drawn with a background pen rather than a foreground pen, which is what gives it its filled look. | **No.** |
| `0xD?` | runic | Arch wall glyph `0x76`, likewise drawn with a background pen; which pen depends on the display adapter. | **No.** |
| `0xE?` | runic | Filled rounded block glyph `0x77`. | Yes. |
| party marker | runic | Arrowhead glyph `0x60`, drawn unconditionally at the centre cell `(11,11)`. | - |

**Withdrawal.** Earlier revisions described a peer-spell tint branch inside the
V-View painter and a "source-selector reset" after the `0xC?` glyph. Both
readings are withdrawn. The value they were reading is the **display-adapter
identifier**, not a peer-spell flag, and the "reset" is the painter's ordinary
epilogue restoring the default foreground pen and the text font. V-View has no
peer-spell branch of its own; the peer spell's own presentation is specified in
`magic.md`.

### 12.5 The two vector glyphs

Let `(x, y)` be the accepted cell's pixel origin. All ranges are inclusive.

The **fountain** first draws its basin in the bright foreground pen:

| Fountain stroke | Geometry |
|---|---|
| Lower lip | `x + 1..x + 6` at `y + 4` |
| Middle lip | `x + 2..x + 5` at `y + 5` |
| Left foot | `x + 1..x + 2` at `y + 6` |
| Right foot | `x + 5..x + 6` at `y + 6` |

then switches to a brighter blue for the jet and spray:

| Fountain detail | Geometry |
|---|---|
| Upper-left spray dot | pixel at `(x + 2, y + 1)` |
| Upper-right spray dot | pixel at `(x + 5, y + 1)` |
| Left side spray dot | pixel at `(x + 1, y + 2)` |
| Right side spray dot | pixel at `(x + 6, y + 2)` |
| Upper jet | `x + 3..x + 4` at `y + 2` |
| Lower jet | `x + 3..x + 4` at `y + 3` |

The **energy field** draws eight full-width horizontal runs covering **all eight
rows** of the cell, in four two-row colour bands:

| Band | Geometry |
|---|---|
| A | `x + 1..x + 6` at `y` and `y + 1` |
| B | `x + 1..x + 6` at `y + 2` and `y + 3` |
| C | `x + 1..x + 6` at `y + 4` and `y + 5` |
| D | `x + 1..x + 6` at `y + 6` and `y + 7` |

Each band carries its own pen, taken from the boot-time user-interface colour
table of `display-driver.md` Section 2 rather than from a literal: band A uses
slot 4, band B slot 0, band C slot 2 and band D slot 3, each biased into the
bright half of the palette by adding eight. An implementation should resolve
these through the same colour table the rest of the interface uses, so the
low-colour drivers inherit their own values.

The energy-field drawing **reads no sub-type**, so all four field flavours look
identical on the map — the four bands are a fixed decorative pattern, not one
band per flavour. That is a genuine behaviour of the original, not an omission
in this spec.

### 12.6 Frame contract

The V-View visited map is temporary scratch memory only. It starts filled as
unvisited for the overlay, marks scratch cells as visited during that one flood
walk, and is discarded when the viewport is restored. It does not write
exploration bits into the loaded dungeon image and does not change what the
first-person renderer or future V-View calls can see.

The map view clears **only the viewport interior** `(8,8)` to `(183,183)`, so
the top and bottom border bands - and therefore the level and facing labels of
Section 4.1 - are never damaged. It switches the active text window to the
message window, waits for any key, clears the viewport again, and returns
through the composite redraw of Section 6.9, which repaints the first-person
view and rewrites both labels even though they were never touched.

The map is therefore an inspect overlay, not a persistent panel that waits for
the next turn loop to erase it, and not an automap: it is recomputed from the
current dungeon record every time the player spends a gem.

Source provenance: derived from private analysis note
`../u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.

## 13. Z transitions and exiting

### 13.1 The two deliberate ways to change level

A dungeon's level index changes deliberately by exactly two routes, and they are
gated quite differently.

**K-Klimb.** K reads the cell the party is standing on and offers whichever
directions that cell provides:

- **Up** is offered when the cell is an up ladder or a two-way ladder, and also
  when the cell is marked climbable-with-equipment and the party is carrying the
  climbing gear.
- **Down** is offered when the cell is a down ladder, a two-way ladder, or a pit.
- When both are available the handler prompts for up or down, accepting the
  explicit up and down selections and the standard cancel/pass keys.
- Any other cell returns with no level change.

A climb **never inspects the cell it lands on.** The ladder or pit under the
party is treated as proof enough that the destination is reachable, so a climb
cannot be blocked by what is on the level above or below. An earlier revision of
this section said the destination cell is tested for passability before the
level index is written; that is withdrawn - it belongs to the spell route below.

**What a K costs.** A K that applies something - a climb up, a climb down, a pit
fall, or a cancel at the up-or-down prompt - reports "acted" to the dungeon
loop, so the turn's post-action pass runs. Both "nothing to klimb here"
refusals report "no action" instead: the post-action pass is skipped and
klimbing where there is nothing to climb costs the party nothing. The two
refusals are also distinct from each other - one is given for a cell that holds
a climbable feature the party is not carrying the climbing gear for, the other
for a cell with no climbable feature at all - so a player can tell "you need
equipment here" from "there is nothing here". `systems/commands.md` Section 3
owns the status enum these values belong to and lists this route among the six
that forward their handler's own value.

**The dungeon level-change spells.** The Up and Down pair (`catalogs/spell-list.md`
ids 21 and 22) are castable only inside a dungeon, and they move the party one
level from wherever they stand with **no ladder, pit, or equipment required**.
They are the stricter of the two routes in one respect only: they do test the
destination cell and refuse it when it is in the base `0x0` class or in the wall
and door-presentation families `0xB?` through `0xE?`. Both spells refuse Doom
outright.

Two further routes change the level without being asked to: automatic pit falls
(Section 8 and `systems/doors-and-z-transitions.md` Section 10), and the
post-combat result codes described in Section 10, which move the party one level
up or down through the same machinery. An up-or-down movement request raised
inside a dungeon **room** is handled identically: it is queued as the same
movement intent and applied by the same code.

### 13.2 Leaving the dungeon

Whichever of the routes above is taken, hitting a level edge leaves the dungeon,
and every exit goes through **one** shared contract - the routine other sections
of this spec set call the *surface-reset helper*. There is no second
dungeon-to-outdoor path in the build and no per-dungeon special case:

- The destination X and Y are the dungeon's own **outdoor entrance
  coordinate**, taken from the same per-scene location table that entry used.
  Both arms use the identical cell.
- The destination **world plane** comes from the level the party was standing on
  when the edge was reached. Level zero means they left off the top, so they
  surface on Britannia; any other level - in practice the lowest one - means
  they went out through the bottom, so they arrive in the Underworld. The two
  arms narrate an exit to Britannia and an exit to the Underworld respectively.
- The dungeon scene byte is then cleared, which is what returns the game to
  outdoor mode.

Because seven of the eight dungeon mouths carry an entrance tile at the same
coordinate on **both** world maps, one coordinate serves both arms. Entry is the
mirror image: from the surface the party starts on the top level in the
north-west corner; from the Underworld they start on the bottom level in the
south-east corner - which is exactly where the five dungeons that have one place
their bottom-level down-ladder, so the climbed round trip is reciprocal. Doom is
the exception in both directions (Section 13.3). Only foot travel may enter a
dungeon at all.

The practical consequence, and the reason this matters: **every dungeon except
Doom can be left at either end**, because the level-change spells reach the edge
without needing a ladder. What the shipped map data decides is only which
dungeons can be left by **climbing** alone, and by that measure the two ends are
not symmetric - `catalogs/gazetteer.md` Section 6.1 carries the per-dungeon
table. An earlier revision of this document treated the climbable-exit set as
the set of dungeons that have a bottom handoff at all, and singled Hythloth out
as an open question; both readings are withdrawn.

Two further mechanical notes on the exit path:

- The exact pit byte `0x60` is the special non-ladder K-Klimb case: it bypasses
  the ordinary level-step helper and invokes the exit contract directly.
- The **pit-chain off-bottom path** is genuinely separate. When a chain of
  automatic fall traps increments the level past the deepest one, the scene byte
  is cleared with the off-bottom level and the party's current X/Y still in
  resident state; it does not run the exit contract and does not consult the
  exterior coordinate table. Stock data cannot produce this, and it is retained
  as defensive compatibility behaviour.

An earlier revision of this document also described an "exit-dungeon tile" - a
set of cells in some dungeons that dump the party outdoors regardless of level.
No such cell class exists; that claim is withdrawn.

### 13.3 Doom

Doom is the exception to nearly every rule above:

- Its mouth exists in the Underworld only. On the Britannia surface that
  position falls inside open ocean, so Doom has no surface entrance.
- Entry is refused unless all three Shadowlords have been destroyed. A party
  that tries earlier is told it is attacked at the entrance, an ambush is
  spawned, and entry does not happen.
- Uniquely among dungeons entered from below, Doom seeds the party on its
  **topmost** level in the north-west corner rather than the bottom level.
- Doom cannot be left. Its top level carries neither an up ladder nor a
  climbing-gear cell, and both level-change spells refuse to run inside it, so
  the "exit to Britannia" arm - which would otherwise strand the party in
  mid-ocean - is unreachable. Doom is a one-way descent.

### 13.4 The other ways dungeon mode ends

Beyond the level-edge exit, dungeon mode terminates through a **total party
wipe** and through the **endgame** hand-off.

A wipe is detected by the shared party-capability check of § 4, step 7, not by
any dungeon-local test: when that check reports that nobody can act and nobody
is asleep, the turn loop stops and its epilogue runs the rescue/refuge sequence
specified in `systems/blackthorn.md` Section 7. That sequence restores every
member, reads out a moral-standing verdict, and resumes ordinary play in Lord
British's Castle, so an ordinary wipe underground is **not** a terminal
game-over. An earlier revision of this section routed the wipe to a "death
sequence" and a "game-over flow"; no such dungeon-side path exists and that
claim is withdrawn. Losing a fight in a dungeon room reaches the same place
indirectly: combat returns to the dungeon loop that framed it, and the loop's
next capability check sees the result (`systems/combat.md` Section 14).

The endgame hand-off is separate: dungeon-room and post-combat cleanup can
consume the special combat absorption marker and enter the endgame overlay
instead of restoring ordinary dungeon play. In stock data the authored route is Doom level
seven's room-id-fifteen trigger at local coordinate `(X=5, Y=7)`, which selects
the final Doom room arena.

The dungeon turn loop has two exits: *if the scene byte drops to thirty-two or
below, the loop exits* — how it got there is the caller's concern — and the
capability check's wipe result ends the loop from inside, before the sequence
that then resets the scene runs.

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

Room setup also builds the temporary combat actor layout from the loaded
`DUNGEON.CBT` metadata. Party entry is independent of monster placement: a
room-entry facing seed chooses one metadata row, and party slot `i` receives X
from that row's column `11 + i` and Y from column `17 + i`. The monster/special
scan then walks sixteen source slots in order. Source slot `i` reads its source
byte from row 5 column `11 + i`, X from row 6 column `11 + i`, and Y from row 7
column `11 + i`. Ordinary source bytes become deterministic setup classes and
produce real combat actors; genuine special source bytes produce active-object
markers only, with no combat descriptor and no turn in the round loop, plus the
special-derived auxiliary values described in the CBT format spec. There is no
separate dungeon-room monster-count roll: the scan attempts one placement for
each nonzero source cell, with only special subtypes adding their own small
random post-placement choices.

One family is easy to mis-classify. Sources in the `0xEC..0xEF` family are **not**
special placements: they pass the ordinary/special test, take the ordinary path,
and only have their derived setup class replaced by one of four setup ids
pre-rolled from a small vermin palette (Giant Rat, Bat, Giant Spider, Python,
Skeleton, Slime, Insect Swarm). They therefore spawn ordinary randomised
combatants. They receive no auxiliary-byte post-write only because that
post-write is gated on the special placement path. This family occurs in fifteen
shipped dungeon-room records, so treating it as an inert marker leaves those
rooms empty. Genuine special placements do stay on the special active-object
path and are never converted into ordinary monster setup classes.

That generated actor setup is combat-local; it is not a persistent rewrite of
the dungeon cell grid.

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
combat encounter through the wandering-monster path below.

### 14.1 Wandering-monster combat: arena, setup, and slot handling

Both wandering-monster triggers - the A-Attack forward probe (§ 10) and the
post-action contact/auto-face path above - use the same four-step launch, and it
is **not** the room-trigger `DUNGEON.CBT` path. No arena record is read from disk
on this path.

1. **Set the combat kind byte to the ambush value.** The contact path also
   clears the combat result code first.
2. **Tear down the first-person view resources.**
3. **Synthesise the arena in the room buffer.** The dungeon room painter is
   called with the combat kind byte already set to the ambush value. It fills the
   eleven-by-eleven terrain grid with the current corridor fill byte, stamps the
   outline, corner markers, the underfoot-class centre icon, and the four
   passage strokes, and then writes the same metadata band that the room-combat
   setup helper reads (see `formats/cbt.md` Section 5 for the row/column layout):

   - **Party-entry rows.** Metadata rows one through four receive fixed
     six-entry X and Y sequences. On this path the entry-facing seed the setup
     helper later reads is simply the party's current dungeon facing, and the
     four rows are arranged so that the row that facing selects (facing north
     picks row three, east row two, south row four, west row one) places the
     party on the side of the arena *behind* its facing. The published values
     are `X = [6,7,7,8,8,8]`, `[4,3,3,2,2,2]`, `[5,4,6,3,5,7]`, `[5,4,6,3,5,7]`
     for rows one through four, and `Y = [5,4,6,3,5,7]`, `[5,4,6,3,5,7]`,
     `[6,7,7,8,8,8]`, `[4,3,3,2,2,2]` for the same rows.
   - **Source coordinate rows.** Metadata rows six and seven receive sixteen-entry
     X and Y sequences chosen by the party's facing, arranged so monsters start
     on the side the party is facing. Facing north uses
     `X = [5,4,6,3,7,2,8,5,2,8,3,7,2,4,6,8]` with
     `Y = [2,2,2,3,3,4,4,1,2,2,1,1,0,0,0,0]`; facing east uses
     `X = [8,8,8,7,7,6,6,9,8,8,9,9,10,10,10,10]` with
     `Y = [5,4,6,3,7,2,8,5,2,8,7,3,2,4,6,8]`; facing south swaps the east pair;
     facing west swaps the north pair. A facing value outside zero through three
     leaves both rows untouched.
   - **Source band.** All sixteen source cells are cleared, a shuffled
     permutation of the sixteen slot indices is built, and then `count` copies of
     the ordinary source byte `class * 4 + 0x40` are written into the first
     `count` permuted slots. `class` is the active dungeon monster's stored
     class byte. `count` is a uniform integer in `[1, spawn_count]` where
     `spawn_count` is the class's spawn-count stat byte, except that a
     spawn-count of eight or sixteen is taken as an exact count with no roll.

4. **Call the combat framer with the ambush entry mode**, passing the active
   monster's class byte. The framer's ambush branch performs no arena load and
   discards the class argument; it simply invokes the room-combat setup helper
   with an entry mode that passes the helper's placement gate. The helper then
   reads the band just synthesised: party slots take their coordinates from the
   facing-selected party row, and each nonzero source is placed on the ordinary
   path, recovering the same class the painter encoded.

**Monster class derivation.** The active dungeon monster's class byte is not a
sprite id and needs no shift arithmetic. Dungeon view initialisation rolls one of
eight presentation records and copies that record's combat class directly into
the active-object slot; the eight classes are Giant Rat, Bat, Giant Spider,
Ghost, Slime, Gremlin, Gazer, and Reaper. Their spawn-count stat bytes are ten,
sixteen, four, six, sixteen, thirteen, four, and three respectively, so Bat and
Slime always place the full sixteen while the others roll.

**Active-object slot handling.** The dungeon active-object slot is **not** cleared
before the framer runs. The framer backs up the whole active-object table on
entry and restores it on exit, so the dungeon monster's record is byte-identical
when combat returns. The replacement happens afterwards, in the post-combat view
re-initialisation, and the order matters: it rolls a new presentation record
first and **overwrites** the slot with the new monster's class, sprite, and
level bytes, then attempts a random placement. Only if that placement fails are
the slot's tile bytes zeroed and its link byte set to the all-ones sentinel. The
slot is never blanked on the success path, and the previous monster's class byte
is read during re-initialisation - before it is overwritten - to decide whether
the old sprite source needs releasing, so an implementation that clears the slot
first loses information it still needs. The practical contract is that the
monster the party fought is always replaced by a freshly rolled random one after
a wandering-monster fight, whatever the outcome, rather than being preserved or
specifically removed.

**Post-combat bracket.** The two triggers differ here. Only the **A-Attack** path
applies the combat result code, and it applies it in the same polarity K-Klimb
uses (Section 13): a smaller level byte is nearer the surface.

- **Result code five - go up one level.** Decrement the level byte. If the
  party is already on the topmost level, do not decrement; take the
  surface-exit helper instead, which restores the dungeon's exterior
  coordinates, clears the dungeon scene, and leaves the party on the Britannia
  overworld.
- **Result code six - go down one level.** Increment the level byte. If the
  party is already on the bottom (eighth) level, do not increment; take the
  same surface-exit helper, which in this case leaves the party in the
  Underworld rather than on the Britannia surface. The helper distinguishes the
  two cases by whether the level byte was zero when it was entered.
- **Any other result code** leaves the level byte alone.

The **contact** path clears the combat result code *before* launching the fight
and never reads it afterwards, so a wandering-monster fight that begins by being
walked into can never change the party's level.

Both paths then re-initialise the dungeon view and roll the replacement active
monster. The A-Attack path gates both the replacement roll and the viewport
redraw on the scene byte still reporting a dungeon; the contact path rolls
unconditionally and gates only the redraw. The difference is not observable in
normal play, because the scene byte only stops reporting a dungeon when a
surface-exit arm has already ejected the party. Neither handler advances the
world clock itself and neither touches the room-clear bitmap - those belong to
the per-turn epilogue and to the room-trigger path respectively.

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
  bomb branch, and `0xC?`/`0xD?` rewrites are covered, and so is the caller
  layer above them. There is no caller-side trap-selection table: a container is
  trapped or not — one flag on a surface or town container object, a non-zero
  lock/trap sub-type on a dungeon chest cell — and the trap's flavour is chosen
  entirely by the shared resolver's four-way distribution published in
  `systems/traps.md`. Nothing further is outstanding here.
- **V-View visual parity.** Resolved. The map's cell size and origin, the
  twenty-two by twenty-two grid, the wrap rule, the flood bound, the glyph
  source fonts, the per-class font selection, and the pixel geometry of both
  vector glyphs are published in Section 12. What remains is screenshot
  comparison, not unknown rules.
- **Open/Get chest traps.** Search's chest trap narration is covered here, while
  Open owns the trap-springing gameplay path and Get owns the seven-row
  open-chest reward generator specified in `containers.md`. The caller layer is
  fully covered: Open passes only "trapped" or "not trapped" into the shared
  resolver, and because the same sub-type is both the lock difficulty and the
  trap flag, a successful Jimmy makes the following Open trap-free.
- **Room-mediated level changes.** The uniform exit contract, the two
  deliberate level-change routes and their differing gates are published in
  Section 13. The one narrow item left open is which dungeon *room* maps place a
  ladder cell under the party, since an up-or-down request raised inside a room
  feeds the same machinery as K-Klimb.
- **Random-encounter cadence and monster sets per level** — see `encounters.md`.
- **Pit-chain off-bottom stock-data boundary.** Chained pit falls that run past
  level seven clear the dungeon scene byte with the off-bottom level byte and
  same X/Y still in resident state. The dungeon-side state mutation is covered,
  and a stock `DUNGEON.DAT` scan found no shipped fall-trap placement or
  vertical chain that can produce it. Preserve the covered state mutation as
  defensive compatibility behavior for custom or mutated dungeon data.

## 18. Sources

The behaviour described here was derived by reading the private function notes listed below. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The withdrawal of the per-hour "HP regeneration" step in Section 11, and the confirmation that the dungeon H path converges on the same shared hole-up handler as the overworld, derived from `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.

- The dungeon turn loop's structure -- initialisation, flavour selection, underfoot reaction, render-and-poll, dispatch, the status-gated post-action helper, the ungated party-capability check, and the epilogue -- derived from `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- The wandering-monster combat contract in Section 14.1 -- ambush entry mode,
  arena and metadata-band synthesis, party-entry and source coordinate tables,
  source-band construction, class derivation, active-object slot handling, and
  the post-combat bracket -- derived from private analysis note
  `u5-decomp/notes/2026-08-22_dungeon-ambush-arena.md` and the function notes it
  cites: `u5-decomp/functions/DUNGEON_OVL/0x1D4A_dungeon_attack_forward.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0B7E_dungeon_encounter_face.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0134_dungeon_view_init.md`,
  `u5-decomp/functions/DNGLOOK_OVL/0x0D3E_paint_room.md`,
  `u5-decomp/functions/DNGLOOK_OVL/0x117E_setup_room_npcs.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
- The room-clear bitmap's index derivation and the six-pair writer deny-list --
  derived from `u5-decomp/functions/DNGLOOK_OVL/0x0844_set_room_cleared.md`,
  `u5-decomp/functions/DNGLOOK_OVL/0x08D4_is_room_cleared.md`, and
  `u5-decomp/functions/DNGLOOK_OVL/0x093A_demote_cleared_room_markers.md`.
- The dungeon chrome bands, their exact cell layouts, the two border-label
  literals and the invalid-facing fallback, the status refresh cadence, and the
  walk-in-only entry facing seed -- derived from private analysis note
  `u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`.
- The dungeon viewport frame, status row redraw, render-and-poll helper,
  active-object setup and placement, and room-entry state handoff -- derived
  from `u5-decomp/functions/DUNGEON_OVL/0x0332_draw_view_panel.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x01D2_dungeon_status_redraw.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x03D6_dungeon_render_and_poll.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0134_dungeon_view_init.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x0252_dungeon_place_active_object.md`,
  and `u5-decomp/functions/DUNGEON_OVL/0x0000_dungeon_room_enter.md`.
- The first-person renderer's billboard model, half-aperture frustum, per-band
  destination rules, cell-class-to-image mapping, sprite families and placement,
  fountain-water and wall-decoration animations, two-sweep ordering, and binary
  light gate -- derived from private analysis note
  `u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`, which also
  withdraws the earlier sparse-point-plotting reading recorded in
  `u5-decomp/notes/`.
- The dungeon-entry scene/name/record binding, selected-record load, and entry seed coordinates — derived from the MAINOUT E-Enter helper and its dungeon-entry subhelper, cross-checked against `u5-decomp/formats/data-ovl.md`.
- Source provenance: the single shared exit contract and its plane rule, the
  four routes that reach it, the foot-travel entry gate, Doom's Shadowlord gate
  and one-way descent, the withdrawal of the "exit-dungeon tile" class, the
  klimb-versus-spell split on destination testing, and the per-dungeon
  climbable-exit table are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- The mode-aware letter dispatch table including the dungeon-specific routes for A-Attack, K-Klimb, L-Look, T-Talk, V-View, and the H-Hole-up overworld path — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- The dungeon Look handler's tile-class switch, light gate, `0x61` description normalisation, and fountain Y/N drink flow — derived from `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`. The relative focus prompt and coordinate writer used by dungeon Look and Search — derived from `u5-decomp/functions/SJOG_OVL/0x006C_sjog_dir_step.md` and `u5-decomp/functions/SJOG_OVL/0x002A_sjog_apply_dir_step.md`. The View handler's centred flood map, its twenty-two by twenty-two eight-pixel cell grid, wrap rule, flood bound, font-based glyph source, and wait/clear/restore flow — derived from the DNGLOOK function notes under `u5-decomp/functions/DNGLOOK_OVL/` and from private analysis note `u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`, which withdraws the earlier peer-spell tint reading.
- The wrapped dungeon cell reader's class-sensitive `0x08` normalization and
  the front-cell renderer's extra-glyph/active-object overlay use of that bit
  -- derived from `u5-decomp/functions/DUNGEON_OVL/0x10DC_dungeon_get_cell.md`,
  `u5-decomp/functions/DUNGEON_OVL/0x1952_dungeon_draw_outer_cell.md`, and
  `u5-decomp/notes/system-trace_dungeon-rendering.md`.
- The first-person renderer helper contracts -- billboard bank selection and
  directory roles, per-band destination placement and the mirror rule,
  cell-class-to-image mapping including the point-blank override and the
  heavy-door pass-through, object sprite families and their masked format,
  the fountain-water point animation, the flavour-wall decoration animation and
  its persisted stage, field strobe painting, active-object sprite painting,
  and composite redraw sequencing -- derived from the dungeon renderer function
  notes under `u5-decomp/functions/DUNGEON_OVL/`, consolidated and corrected in
  private analysis note
  `u5-decomp/notes/presentation_dungeon_zstats_echo_2026-08-22.md`. That note
  withdraws the earlier "sparse point-pair wall table" reading and reattributes
  those four tables to the fountain-water animation.
- The dungeon Search handler's light gate, high-nibble feature descriptions,
  chest trap-tier narration, pit-family secret reveal, `0xC?`/`0xD?`
  visit-local rewrites, and bomb branch - derived
  from `u5-decomp/functions/SJOG_OVL/0x0646_sjog_search_inner.md`.
- The dungeon Get open-chest consumption and seven-row reward-generator shape -
  derived from `u5-decomp/functions/SJOG_OVL/0x179E_sjog_get_dungeon_chest.md`.
- The closed/open/looted chest lifecycle as one preserve-variant-bit rewrite
  idiom, the identification of the `0x7?` class as the open chest rather than a
  passage variant, the absence of any second write that could re-promote a
  looted cell, the shipped-data facts that no static cell carries the open-chest
  class and that every static chest cell has the variant bit clear, and the
  absence of any caller-side trap-selection table above the shared trap
  resolver. Source provenance: derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_sjog-traps-locks.md`.
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
- The destination passability test shared by the dungeon level-change routes,
  which Section 13.1 records as enforced for the level-change spells and skipped
  by K-Klimb, is derived from
  `u5-decomp/functions/DUNGEON_OVL/0x1C0C_dungeon_cell_passable.md`.
- The DNGLOOK minimap cell painter, passage/room painters, room-clear bitmap reader/writer, cleared-room demotion pass, room NPC setup, and view teardown/init helpers - derived from `u5-decomp/functions/DNGLOOK_OVL/0x0340_v_view_paint_cell.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0284_paint_stair_glyph.md`, `u5-decomp/functions/DNGLOOK_OVL/0x097E_paint_passage_full.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0A48_paint_passage_short.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0AEE_paint_passage_medium.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0B9E_paint_passage_from_party.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0C6C_paint_room_layout.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0D3E_paint_room.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0FDA_apply_movement.md`, `u5-decomp/functions/DNGLOOK_OVL/0x0844_set_room_cleared.md`, `u5-decomp/functions/DNGLOOK_OVL/0x08D4_is_room_cleared.md`, `u5-decomp/functions/DNGLOOK_OVL/0x093A_demote_cleared_room_markers.md`, `u5-decomp/functions/DNGLOOK_OVL/0x109E_init_dungeon_view.md`, `u5-decomp/functions/DNGLOOK_OVL/0x1130_teardown_dungeon_view.md`, and `u5-decomp/functions/DNGLOOK_OVL/0x117E_setup_room_npcs.md`.
- The H-Hole-up code path's per-slot rest, ambush check, and HP regeneration — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The world-clock advance contract and the integration with combat for room-trigger and wandering-monster encounters — derived from sibling specs `u5-spec/systems/time.md` and `u5-spec/systems/combat.md`.

- The dungeon mode-local control-code table, the Enter/period movement
  bindings, the digit handler's "no action" result, the absence of the
  shifted-digit direction translation underground, and the corrected return
  values of dungeon Klimb. Source provenance: derived from private analysis note
  `../u5-decomp/notes/oq-closures_2026-08-22_commands-dispatch.md` and
  `../u5-decomp/functions/DUNGEON_OVL/0x1E10_dungeon_klimb_dispatch.md`.

- The Section 7 light-source correction: the two dungeon light bytes are
  remaining-duration counters rather than radii, the renderer consults them
  only as a binary lit/unlit gate, and the complete writer census for both
  counters (Ignite, the G-Get borrow branch, the three light-spell writers, and
  the Blackthorn clear) rules out the previously claimed per-turn spellbook
  bump. Source provenance: derived from private analysis notes
  `../u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` and
  `../u5-decomp/functions/CAST2_OVL/0x08EA_set_torch_radius.md`, and from the
  sibling spec `u5-spec/systems/lighting.md`.

- The Section 4 turn-loop tail and the Section 13.4 wipe route: the dungeon's
  per-iteration party-capability check, its ownership of the sleep line, the
  withdrawn "idle pump" / "dungeon-exit teardown" reading of that tail, and the
  routing of a total party wipe to the rescue/refuge sequence rather than to a
  death or game-over path. Source provenance: derived from private analysis note
  `../u5-decomp/notes/oq-closures_2026-08-22_blackthorn-town.md`, section Q2, and
  `../u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
