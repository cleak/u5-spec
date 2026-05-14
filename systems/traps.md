# Traps

## 1. Scope

Ultima V has several trap families that share visible effects but are reached
from different systems:

- chest and container traps reached through `O` Open, `J` Jimmy, `S` Search,
  and dungeon chest handling;
- dungeon floor traps reached by stepping on trap cells;
- combat post-pass effects that use their own driver-facing flag instead of
  this resident party-effect resolver.

This document owns the shared resident trap-effect resolver: the path that
plays the trap sting, prints one of the trap-effect messages, and applies a
party HP or status-side effect. It does not own the tables that decide whether
a given chest is trapped, how hard a trap is to detect or disarm, or how
dungeon room cells select combat arenas.

## 2. Shared Trap-Effect Resolver

When a caller resolves to the shared trap-effect path, the engine performs
three steps:

1. Play the short trap audio sting.
2. Select an effect id. Outside combat this selection rolls uniformly over an
   eight-entry resident lookup table. During combat-class scenes the resolver
   bypasses that lookup and chooses uniformly from the first two effect ids
   only.
3. Print the selected trap message and apply the matching party mutation.

The resolver takes the triggering party slot as its context argument. Effects
that target only one character use that slot. Effects that target the whole
party iterate the first six party slots and ignore empty roster positions
through the called party-status helpers.

## 3. Effect Families

The shared resolver has four effect families:

| Effect id | Family | Behaviour |
|---:|---|---|
| 0 | Acid / single-slot damage | Prints the acid trap message, rolls a short random damage amount in the `1..30` range, applies it to the triggering party slot, and refreshes party stats. If HP reaches zero, the normal damage helper marks the character dead and clears the active-member hint when needed. |
| 1 | Poison / single-slot revive helper | Prints the poison trap message and runs the revive helper for the triggering party slot. The helper only changes slots currently marked dead; living slots are left unchanged. |
| 2 | Bomb / party damage | Prints the bomb trap message and rolls `1..8` damage separately for each living member in the six-slot party band. Each accepted member is routed through the ordinary party-damage helper. |
| 3 | Gas / party revive helper | Prints the gas trap message and runs the revive helper across slots `0..5`. As with single-slot revive, living members are not rewritten. |

The revive helper used by effect ids 1 and 3 is intentionally narrow. It tests
whether the target slot is within the current party count and currently has
Dead status; only then does it write raw status `P` and redraw the stats panel.
It does not restore HP, recompute maximum HP, rebuild MP, or run the spell
resurrection path. Compatible implementations should preserve this trap-helper
edge exactly rather than replacing it with the broader resurrection spell
contract.

The non-combat lookup table maps the eight equiprobable roll outcomes to
effect ids in this distribution:

| Effect id | Non-combat outcomes | Probability |
|---:|---:|---:|
| 0 | 3 | `3/8` |
| 1 | 2 | `2/8` |
| 2 | 2 | `2/8` |
| 3 | 1 | `1/8` |

Combat-class scenes do not use that table. They roll between effect ids `0`
and `1`, so combat traps can produce only the acid or poison labelled branches.

The original strings give these effects their in-game flavour, but the gameplay
contract is the state mutation above. Implementations should keep the effect
families separate from trap selection: a chest, door, Search result, or combat
post-pass may choose a trap differently while still using the same four
effect handlers once a shared trap effect is selected.

## 4. Relationship To Other Trap Systems

**Chest and container traps.** Container and lock helpers decide whether an
interaction is safe, empty, grants loot, or invokes a trap. Once they enter the
shared resolver, the four effect families above apply. The caller selection
layer is documented with the command/container helpers: surface chest content
pools live in `systems/containers.md`, and dungeon room combat arena selection
lives in `systems/dungeon-mode.md` and `formats/cbt.md`.

**Search traps and feature traps.** Search can classify traps and features
before it grants inventory or rewrites a live tile. Per-map object slots with
trap metadata have their own no-trap/simple/complex/generic narration based on
slot difficulty, the selected member's trap-detection stat family, and a
`1..30` threshold roll specified in `systems/containers.md`. That narration is
not the damage/status resolver. The surface Search probe itself is an
active-object coordinate lookup: it returns the matched slot's tile/type byte,
and the Search command owns the resulting feature narration or pickup staging.
Any Search outcome that actually invokes the resident resolver should use this
document's effect contract.

**M-Mix wrong recipes.** The reagent mixer also uses this resolver after a
wrong recipe. The mixer owns the reagent loss and no-charge result; before
calling the trap-effect resolver it refreshes its target scratch slot to the
first travelling member currently marked Good or Poisoned when such a member
exists. The trap resolver then applies the ordinary four-family effect contract
above.

**Dungeon floor traps.** Dungeon pit and bomb traps are direct cell effects,
not the shared resolver. Fall traps move the party down the dungeon stack;
bomb traps fire their own dungeon post-action branch. Their byte-level cell
families are specified in `systems/dungeon-mode.md` and
`systems/doors-and-z-transitions.md`.

**Combat post-pass tile restoration.** The combat wrapper samples a resident
tile-restoration flag as it restores the suspended world state. That
driver-facing call reaches the display-driver tile-graphics
save/restore/mutation entry with mode value `1`, which restores driver-saved
tile bytes before the ordinary world redraw. It is distinct from this resident
party-effect resolver, even when older private notes use broader trap-effect
wording for the same wrapper.

## 5. Caller Boundaries

The shared resolver has no remaining effect-family gap in this document. Caller
selection remains owned by the invoking systems:

- `systems/containers.md` owns surface/town chest class handling, trapped-chest
  flow, and the primary and secondary chest result pools.
- `systems/containers.md` also owns Search's per-object trap/detail narrator,
  including the trap-detection threshold and false-positive/missed-trap cases.
- `systems/dungeon-mode.md` and `systems/doors-and-z-transitions.md` own
  dungeon floor pit/bomb trap cells.
- Combat restore-time driver effects are presentation cleanup, not calls into
  this party-effect resolver.

## 6. Sources

This cleanroom spec was derived from private analysis notes. It intentionally
does not reproduce decompiled code, assembly, raw tables, string dumps, or
private address maps.

- `u5-decomp/functions/ULTIMA_EXE/0x2FD0_trap_effect.md`.
- `u5-decomp/functions/CMDS_OVL/0x1AD8_cmds_mix_reagents.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x39FC_find_paladin_or_shepherd.md`.
- `u5-decomp/functions/SJOG_OVL/0x02EA_sjog_search_object_handler.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x3702_lookup_object_at.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x2A52_party_take_damage.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x2AA8_party_random_damage.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x2FA6_party_revive_slot.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x3ABE_random_short_delay.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x3AAE_prng_roll_max.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x6FBC_post_combat_trap.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
