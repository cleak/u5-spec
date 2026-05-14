# Lighting

## 1. Overview

Ultima V has one shared lighting model with two layers:

- **Ambient daylight**, derived from the world clock and from where the party is.
- **Personal light**, supplied by a torch or by a light spell.

The same state is read by surface visibility, dungeon rendering, dungeon Look, moongates, and the stats panel. The important distinction is that daylight is environmental and recalculated from time and scene, while torches and light spells are finite counters that decay as turns pass.

Lighting is not a separate weather system. Wind does not brighten or darken the
world, and weather does not extinguish light sources in the currently mapped
behavior. The mapped dungeon movement and post-action cell-effect dispatchers
also do not define a wind/breeze cell that blows out a torch; do not treat that
secondary claim as part of the baseline weather, lighting, or dungeon contact
model.

## 2. State

Lighting state consists of three runtime values:

| State | Meaning |
|-------|---------|
| Ambient light | The current daylight or darkness level used by surface visibility. |
| Torch counter | Nonzero while the party has an active torch. |
| Light-spell counter | Nonzero while a light spell is active. |

The torch and spell counters are independent. A torch can expire while the spell remains active, and a spell can expire while a torch remains active. The dungeon renderer treats either one as sufficient to see; both being zero is the blackout state.

The original stores these as byte-sized duration counters. A modern implementation should expose them as turn durations or visibility profiles, not as raw memory bytes, but the starting values and saturation behavior are part of the compatibility contract.

## 3. Ambient Daylight

Ambient daylight is recomputed by the per-turn cleanup routine, including calls that intentionally advance zero minutes. This matters when the party crosses between modes: the engine can refresh lighting for the new scene without spending a turn.

The ambient model is:

- On Britannia's surface, the clock drives a day-night cycle.
- Before dawn and after dusk, the surface is dark.
- Dawn and dusk use a short stepped gradient rather than an instant switch.
- During the daytime band, the surface reaches full daylight.
- The Underworld and dungeons force dark ambient light regardless of the hour.

On the original light scale, full daylight is 50 and full darkness is 2. Values
51 or higher are special "do not recompute" sentinels: if the cached ambient
value is already in that range when the cleanup routine reaches the daylight
stage, it leaves the value alone. Dawn uses six ten-minute levels:
`2, 5, 10, 20, 34, 49`; dusk uses the same levels in reverse.

Current writer analysis has not found any normal gameplay scene that
deliberately sets one of those sentinel values as a lighting freeze. Treat the
sentinel as a defensive compatibility rule for imported or corrupted runtime
state rather than as evidence that a specific cutscene, shrine, or town uses
frozen lighting.

One mapped overworld environmental branch can force ambient light to zero when
the party is standing on the overworld loop's special underfoot `0xFF` tile
state, unless an opaque `0x0E` state tag exempts the pass. That is an ordinary
darkening override, not a high-value skip-recompute sentinel. When the
underfoot state clears, the overworld loop runs a zero-minute cleanup call so
ambient light is recomputed from the clock and scene without spending time.

The cleanup routine marks visibility dirty when the recomputed ambient value changes. Rendering then rebuilds the visible grid instead of reusing the previous one.

Ambient daylight also gates moongate presentation: moongates only animate when the ambient level is high enough for the daytime condition. That gate is a consumer of lighting, not a lighting rule in its own right.

## 4. Personal Light

Torches and light spells modify visibility after the base ambient value has been chosen. They do not replace the clock. Outdoors at noon, daylight is already sufficient; at night, in the Underworld, and in dungeons, a personal light source is what lets the party see around itself.

The original engine applies the torch and spell effects as separate minimum-light floors on the cached ambient value. On the original light scale, the torch floor is 18 and the spell-light floor is 10. The torch and spell profiles are different, which is why implementations should keep two counters rather than collapsing them into one boolean "has light" flag.

For modern gameplay purposes, the contract is:

- If both counters are zero, personal light contributes nothing.
- If the torch counter is nonzero, the party has torch lighting until the counter decays to zero; the cached ambient value is raised to the torch floor when it would otherwise be darker than that floor.
- If the spell counter is nonzero, the party has spell lighting until the counter decays to zero; the cached ambient value is raised to the spell-light floor when it would otherwise be darker than that floor.
- If both are nonzero, the torch floor dominates this cached ambient value because it is applied first and is brighter than the spell-light floor; do not stack them into an unlimited radius.

## 5. Counter Decay

The counters decay through the same turn cadence that advances time. A normal town, dungeon, or combat turn spends one counter unit; a normal overworld turn spends two. Longer waits spend their requested increment. The per-turn cleanup applies the same vehicle adjustments that it applies to time before it decays the counters.

This section covers only torches and light spells. Combat active effects
(`P`, `Q`, `C`, `N`) and Negate Time are non-light spell state with separate
decrement paths.

Decay is saturating subtraction: if the remaining counter is greater than the spent increment, subtract the increment; otherwise set the counter to zero. Counters never underflow or wrap.

Mode-zero lighting refreshes do not spend counter duration. They recompute ambient lighting only.

Dungeon mode also runs a dungeon-local torch/light upkeep hook before drawing the first-person view. The observable contract is still turn-based: active light sources burn down as the party takes dungeon turns, and no-light dungeon rendering blacks out.

The mapped dungeon and weather paths do not extinguish a torch through a
wind/breeze contact tile. Torch state changes through Ignite, spellbook light
bumps, and ordinary counter decay/upkeep; light-spell state changes through the
light-spell writers and the same decay cadence.

## 6. Dungeon Blackout

Dungeon mode has the strictest lighting gate. Before the first-person dungeon view is drawn, the renderer checks the torch and spell counters. If both are zero, it does not draw the corridor view at all. The side/status UI can still exist, but the dungeon scene itself is black.

Dungeon L-Look follows the same rule: with no torch and no light spell, the player receives darkness instead of the true focus-cell description. With either counter nonzero, Look can describe the selected dungeon focus cell and the renderer can draw the sparse first-person view.

This means dungeon light is gameplay-critical. Ambient daylight does not reach dungeon levels, and the dungeon view does not use the surface dawn/day/dusk curve.

## 7. Surface Visibility

Surface visibility uses the ambient light value as an input to the visibility producer. At full daylight, the visible area is broad. At night or in forced-dark scenes, visibility is reduced unless a torch or light spell is active.

The surface renderer does not have the dungeon's all-or-nothing first-person blackout. Instead, it rebuilds the 11-by-11 visibility grid from the current light value, terrain blockers, and the separate local-light mask maintained by the visibility system. A zero or dark light state leaves cells obscured unless local-light state applies; a positive light state lets the centre-out visibility producer carve visible cells.

## 8. Commands And Spells

The I-Ignite command is the player-facing torch entry point. It consumes one torch from inventory; with no torches available it refuses and leaves the light state unchanged.

Ignite has two duration rules:

- Outside dungeon scenes, it sets the torch counter to 240 counter units.
- In dungeon scenes, it adds a random 112..127 counter units to the current torch counter, capped at 255.

This means re-lighting a torch in a dungeon can extend an already-burning torch, while non-dungeon use refreshes to a fixed 240-unit value. Since normal dungeon and town turns spend one unit and normal overworld turns spend two, a counter unit is not always the same as one player-visible turn.

Light spells are cast through the normal C-Cast pipeline. The magic system owns charge, mana, level, and scene gating. Once the spell succeeds, lighting owns the resulting light-spell counter and its decay.

The ordinary Light spell, *In Lor*, sets the light-spell counter to 100 counter units. Great Light, *Vas Lor*, sets the same counter to 255 counter units. These spells overwrite the spell-light duration rather than adding to it, and they do not consume torches.

## 9. Persistence

Lighting state lives in the runtime game state and is saved with the rest of the game image. On load, the next mode entry or per-turn cleanup recomputes ambient light from the loaded clock and scene, while the torch and spell counters resume from their saved values.

Implementations should persist the counters, the clock, and the scene/position state. Ambient light itself can be recomputed, but keeping it cached is harmless as long as mode-zero refreshes update it before rendering.

## 10. Evidence Boundary

The lighting contract in this document is complete at counter, ambient-light,
and scene-gate depth. New claims that assign the high-value skip-recompute
sentinel to a named scene should still be backed by fresh writer evidence.

## 11. Sources

The behavior described here was derived from cleanroom reading of the following notes and sibling specs. No assembly excerpts, raw offsets, or implementation-specific byte tables are reproduced here.

- Ambient daylight recomputation, dawn/dusk behavior, forced darkness in Underworld/dungeons, torch and spell counter decay, and visibility dirtying - `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- Daylight writer inventory, high-sentinel writer audit, and the overworld
  zero-light override -
  `u5-decomp/notes/critical_state_lifecycles.md`.
- Overworld entry and loop behavior relevant to lighting refresh and the
  special-underfoot zero-light override -
  `u5-decomp/functions/MAINOUT_OVL/0x0000_mainout_entry.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`, and
  `u5-decomp/functions/MAINOUT_OVL/0x0A1A_mainout_pre_loop_water_check.md`.
- Saturating counter decrement and Ignite's torch debit/start rules - local helper analysis of the resident counter helpers and the CMDS Ignite command path.
- Light spell counter writes for *In Lor* and *Vas Lor* - `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`, `u5-decomp/functions/CAST2_OVL/_OVERVIEW.md`, and the CAST2 helper reached through the overlay dispatch map in `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- Dungeon first-person blackout when both light counters are zero, plus dungeon-local light upkeep - `u5-decomp/functions/DUNGEON_OVL/0x0E2E_dungeon_turn_loop.md`.
- Shared resident data model and relevant string/table regions - `u5-decomp/formats/data-ovl.md`.
- Existing cleanroom descriptions of time, dungeon lighting consumers, magic
  spell categories, overworld visibility integration, and the surface
  local-light mask boundary - `u5-spec/systems/time.md`,
  `u5-spec/systems/dungeon-mode.md`, `u5-spec/systems/magic.md`,
  `u5-spec/systems/overworld.md`, and `u5-spec/systems/visibility.md`.
