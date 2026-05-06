# Lighting

## 1. Overview

Ultima V has one shared lighting model with two layers:

- **Ambient daylight**, derived from the world clock and from where the party is.
- **Personal light**, supplied by a torch or by a light spell.

The same state is read by surface visibility, dungeon rendering, dungeon Look, moongates, and the stats panel. The important distinction is that daylight is environmental and recalculated from time and scene, while torches and light spells are finite counters that decay as turns pass.

Lighting is not a separate weather system. Wind does not brighten or darken the world, and weather does not extinguish light sources in the currently mapped behavior. The one observed environmental exception is a dungeon wind tile that blows out a torch; that tile effect belongs to dungeon cell handling, not to the overworld weather model.

## 2. State

Lighting state consists of three runtime values:

| State | Meaning |
|-------|---------|
| Ambient light | The current daylight or darkness level used by surface visibility. |
| Torch counter | Nonzero while the party has an active torch. |
| Light-spell counter | Nonzero while a light spell is active. |

The torch and spell counters are independent. A torch can expire while the spell remains active, and a spell can expire while a torch remains active. The dungeon renderer treats either one as sufficient to see; both being zero is the blackout state.

The exact numeric counter values are implementation detail. A modern implementation should expose them as durations or radii, not as raw memory bytes.

## 3. Ambient Daylight

Ambient daylight is recomputed by the per-turn cleanup routine, including calls that intentionally advance zero minutes. This matters when the party crosses between modes: the engine can refresh lighting for the new scene without spending a turn.

The ambient model is:

- On Britannia's surface, the clock drives a day-night cycle.
- Before dawn and after dusk, the surface is dark.
- Dawn and dusk use a short stepped gradient rather than an instant switch.
- During the daytime band, the surface reaches full daylight.
- The Underworld and dungeons force dark ambient light regardless of the hour.

The cleanup routine marks visibility dirty when the recomputed ambient value changes. Rendering then rebuilds the visible grid instead of reusing the previous one.

Ambient daylight also gates moongate presentation: moongates only animate when the ambient level is high enough for the daytime condition. That gate is a consumer of lighting, not a lighting rule in its own right.

## 4. Personal Light

Torches and light spells modify visibility after the base ambient value has been chosen. They do not replace the clock. Outdoors at noon, daylight is already sufficient; at night, in the Underworld, and in dungeons, a personal light source is what lets the party see around itself.

The original engine applies the torch and spell effects as clamps on the shared light value. The spell and torch clamps are different, which is why implementations should keep two counters rather than collapsing them into one boolean "has light" flag.

For modern gameplay purposes, the contract is:

- If both counters are zero, personal light contributes nothing.
- If the torch counter is nonzero, the party has torch lighting until the counter decays to zero.
- If the spell counter is nonzero, the party has spell lighting until the counter decays to zero.
- If both are nonzero, the stronger or more restrictive original visibility profile should win; do not stack them into an unlimited radius.

## 5. Counter Decay

The counters decay through the same turn cadence that advances time. A normal town, dungeon, or combat turn spends the indoor increment; a normal overworld turn spends the outdoor increment. The per-turn cleanup applies the same vehicle adjustments that it applies to time before it decays the counters.

Mode-zero lighting refreshes do not spend counter duration. They recompute ambient lighting only.

Dungeon mode also runs a dungeon-local torch/light upkeep hook before drawing the first-person view. The observable contract is still turn-based: active light sources burn down as the party takes dungeon turns, and no-light dungeon rendering blacks out.

## 6. Dungeon Blackout

Dungeon mode has the strictest lighting gate. Before the first-person wireframe view is drawn, the renderer checks the torch and spell counters. If both are zero, it does not draw the corridor view at all. The side/status UI can still exist, but the dungeon scene itself is black.

Dungeon L-Look follows the same rule: with no torch and no light spell, the player receives darkness instead of the true cell description. With either counter nonzero, Look can describe the cell ahead and the renderer can draw the wireframe.

This means dungeon light is gameplay-critical. Ambient daylight does not reach dungeon levels, and the dungeon view does not use the surface dawn/day/dusk curve.

## 7. Surface Visibility

Surface visibility uses the ambient light value as an input to the visibility producer. At full daylight, the visible area is broad. At night or in forced-dark scenes, visibility is reduced unless a torch or light spell is active.

The surface renderer does not have the dungeon's all-or-nothing wireframe blackout. Instead, it rebuilds the 11-by-11 visibility grid from the current light value and terrain blockers. A zero or dark light state leaves cells obscured; a positive light state lets the line-of-sight producer carve visible cells.

## 8. Commands And Spells

The I-Ignite command is the player-facing torch entry point. It consumes a torch and starts or refreshes the torch counter. The precise inventory debit path is outside this spec because the cited command notes have not yet isolated the Ignite handler.

Light spells are cast through the normal C-Cast pipeline. The magic system owns charge, mana, level, and scene gating. Once the spell succeeds, lighting owns the resulting light-spell counter and its decay.

The spell list currently identifies the light family as the ordinary Light spell and the stronger Great Light spell. Exact duration values should be confirmed when the individual spell-effect handlers are fully decoded.

## 9. Persistence

Lighting state lives in the runtime game state and is saved with the rest of the game image. On load, the next mode entry or per-turn cleanup recomputes ambient light from the loaded clock and scene, while the torch and spell counters resume from their saved values.

Implementations should persist the counters, the clock, and the scene/position state. Ambient light itself can be recomputed, but keeping it cached is harmless as long as mode-zero refreshes update it before rendering.

## 10. Open Questions

- **Exact torch and spell durations.** The counter behavior and consumers are known, but the starting values written by Ignite and by each light spell still need per-handler confirmation.
- **Torch inventory debit.** The command dispatcher proves there is an Ignite command, but the exact handler has not been separated into a dedicated note.
- **Spell strength mapping.** The original keeps separate torch and spell profiles. The exact modern radius/brightness interpretation should be tuned after the light spell handlers are decoded.
- **Special scene lighting.** The time system supports a "do not recompute" style sentinel for special scenes. Which scenes deliberately freeze lighting has not been exhaustively catalogued.

## 11. Sources

The behavior described here was derived from cleanroom reading of the following notes and sibling specs. No assembly excerpts, raw offsets, or implementation-specific byte tables are reproduced here.

- Ambient daylight recomputation, dawn/dusk behavior, forced darkness in Underworld/dungeons, torch and spell counter decay, and visibility dirtying - `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- Dungeon first-person blackout when both light counters are zero, plus dungeon-local light upkeep - `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- Shared resident data model and relevant string/table regions - `u5-decomp/formats/data-ovl.md`.
- Existing cleanroom descriptions of time, dungeon lighting consumers, magic spell categories, and overworld visibility integration - `u5-spec/systems/time.md`, `u5-spec/systems/dungeon-mode.md`, `u5-spec/systems/magic.md`, and `u5-spec/systems/overworld.md`.
