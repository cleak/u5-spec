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

The "families" framing above is about where traps are *reached from*, not about
how many effect resolvers exist. Only three call sites in the shipped game reach
this resolver: opening a trapped surface or town container object, opening a
trapped dungeon chest cell, and mixing a wrong reagent recipe. Search narration,
dungeon floor pit and bomb cells, town underfoot damage tiles, and combat
post-pass tile restoration never enter it, even where their prose uses the word
trap.

There is also no caller-side trap-class table anywhere in the game. A caller
never chooses or passes a trap flavour. A container is simply trapped or not
trapped — a single flag on a surface or town container object, or a non-zero
lock/trap sub-type on a dungeon chest cell — and every flavour distinction is
made inside this resolver by the distribution published in § 3.

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
| 1 | Poison / single-slot poisoning | Prints the poison trap message and applies Poisoned status to the triggering party slot. The status helper acts only on a slot inside the current party count, and it skips a member already marked Dead; a living member is left Poisoned. |
| 2 | Bomb / party damage | Prints the bomb trap message and rolls `1..8` damage separately for each living member in the six-slot party band. Each accepted member is routed through the ordinary party-damage helper. |
| 3 | Gas / party poisoning | Prints the gas trap message and applies Poisoned status across slots `0..5` using the same status helper, so every living member of the six-slot band ends up Poisoned and members already marked Dead are skipped. |

The status helper used by effect ids 1 and 3 is a poison primitive, not a
revival primitive. It tests whether the target slot is within the current party
count and whether that member is already marked Dead. A slot outside the party
is ignored, and a member already Dead is skipped and left Dead. Only a living,
in-party member is written, and the write sets that member's status to the
Poisoned state and redraws the stats panel. It changes nothing else: no hit
points, no maximum hit points, no magic points, and no relation to the
resurrection spell path. Earlier drafts of this document described the helper as
a narrow revive that only rewrote dead members; that reading was backwards and
is retracted. The correct polarity is what gives effect ids 1 and 3 their
in-game poison and gas labelling.

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
families separate from the decision to spring a trap at all: a caller decides
only *whether* a trap fires, and this resolver decides *which*. No caller can
request a particular effect family, and no caller can weight the distribution.

## 4. Relationship To Other Trap Systems

**Chest and container traps.** Container and lock helpers decide whether an
interaction is safe, empty, grants loot, or invokes a trap. That decision is a
single yes/no: the surface and town container carries its lock/trap state as one
flag alongside its content class, and the dungeon chest cell carries it as a
lock/trap sub-type that is non-zero when the chest is both locked and trapped.
Neither passes any trap-class information along. Once they enter the shared
resolver, the four effect families above apply and the flavour is chosen here.
Because the flag doubles as the lock flag, a successful Jimmy disarms the
container as well as unlocking it, so a Jimmy-then-Open sequence never reaches
this resolver at all. The caller selection layer is documented with the
command/container helpers: surface chest content pools live in
`systems/containers.md`, the lock rolls live in
`systems/doors-and-z-transitions.md`, and dungeon room combat arena selection
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
wrong recipe, so the wrong-mix penalty and the chest/locked-door penalty must
share one implementation. The mixer owns the reagent loss and no-charge result;
before calling the trap-effect resolver it refreshes its target scratch slot to
the first travelling member currently marked Good or Poisoned when such a
member exists. When no such member exists the scratch slot is left holding
whatever party index it last held, and the trap lands on that stale index; a
port should treat that as undefined behaviour and decide deliberately rather
than inventing a fallback. A spell name the parser cannot match takes the same
wrong-recipe path, so a mistyped incantation also springs the trap. The trap
resolver then applies the ordinary four-family effect contract above.

**Dungeon floor traps.** Dungeon pit and bomb traps are direct cell effects,
not the shared resolver. Fall traps move the party down the dungeon stack;
bomb traps fire their own dungeon post-action branch. Their byte-level cell
families are specified in `systems/dungeon-mode.md` and
`systems/doors-and-z-transitions.md`.

**Town underfoot damage tiles.** Town mode's per-turn underfoot handler is not
this resolver either. Its trapdoor / loose-brick tile (`0x8C`) and its burning
family (`0xBC` a fireplace and `0x8F` molten lava) each apply an
independently rolled `1..8` hit points to every non-Dead party slot, and its
poison-gas terrain case applies a Dexterity save that sets Poisoned status
without dealing damage. All three run once per turn-consuming action while the
party occupies the tile, not once per step, and none of them selects an effect
family from this document. They are specified in `systems/town-mode.md`, with
the tile identities catalogued in `catalogs/tile-catalog.md`. (Earlier revisions
of this paragraph called these the "chair family" and the "rune/lever family".
Both names are **withdrawn**: the shipped description table names `0x8C` a loose
brick, the separate `0x90..0x93` chair family carries no step trigger at all, and
`0xBC`/`0x8F` are the fireplace and molten lava of the burning family.)

**Combat post-pass tile restoration.** The combat wrapper samples a resident
tile-restoration flag as it restores the suspended world state. That
driver-facing call reaches the display-driver tile-graphics
save/restore/mutation entry with mode value `1`, which restores driver-saved
tile bytes before the ordinary world redraw. It is distinct from this resident
party-effect resolver, even when older private notes use broader trap-effect
wording for the same wrapper.

## 5. Caller Boundaries

The shared resolver has no remaining effect-family gap in this document, and the
caller layer above it is fully covered: there is nothing left to trace on trap
selection, because selection is a single trapped/not-trapped bit and the three
call sites named in § 1 are the only ones. Caller selection remains owned by the
invoking systems:

- `systems/containers.md` owns surface/town chest class handling, trapped-chest
  flow, and the primary and secondary chest result pools.
- `systems/containers.md` also owns Search's per-object trap/detail narrator,
  including the trap-detection threshold and false-positive/missed-trap cases.
- `systems/dungeon-mode.md` and `systems/doors-and-z-transitions.md` own
  dungeon floor pit/bomb trap cells.
- `systems/town-mode.md` owns the town per-turn underfoot damage and
  poison-gas tiles.
- Combat restore-time driver effects are presentation cleanup, not calls into
  this party-effect resolver.

## 6. Sources

This cleanroom spec was derived from private analysis notes. It intentionally
does not reproduce decompiled code, assembly, raw tables, string dumps, or
private address maps.

- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/functions/CMDS_OVL/`.
- `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` — the
  wrong-mix branch's exact three steps, the stale victim-index edge, and the
  unmatched-spell-name route into the same branch.
- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/functions/SJOG_OVL/`.
- `u5-decomp/functions/ULTIMA_EXE/`.
- `u5-decomp/functions/ULTIMA_EXE/` (the note's
  filename predates the correction; the helper it describes applies Poisoned
  status and does not revive).
- `u5-decomp/functions/SJOG_OVL/`.
- `u5-decomp/functions/ULTIMA_EXE/`.

Source provenance: the effect-1/effect-3 polarity correction, the absence of
any caller-side trap-class table, and the three-call-site census are derived
from private analysis note
`u5-decomp/notes/oq-closures_2026-08-22_sjog-traps-locks.md`.
