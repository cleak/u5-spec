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
trapped dungeon chest cell, and mixing a wrong reagent recipe. The scope of that
census - what it covered and what it could not - is stated in § 5. Search narration,
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
party iterate the first six party slots; each of those two effects performs its
own party-count check per slot, so roster positions outside the current party
are skipped. The single-slot damage effect (effect id `0`) is the exception: it
performs **no** party-count check at all, which matters only if a caller can
deliver an out-of-range slot. See Section 3 for the per-effect detail.

### 2.1 How the container callers choose the triggering slot

Both container call sites choose the triggering slot the same way, and they
choose it *before* they test whether the container is trapped. They use the
game's shared acting-member selection - the same selection that decides who
performs Search, Jimmy, Get, Open, Look and Cast. That selection resolves in
priority order:

1. **During a combat-class scene**, the slot is the party member bound to the
   combatant whose turn is currently in progress. It is chosen silently: no
   prompt, no status test, and no check that the named party position is inside
   the party.
2. **Otherwise, when a single active character is set**, that character is
   returned directly and silently, with **no** status re-check. The
   active-character setting screens only for Dead and Asleep at the moment it is
   made, so the character delivered here can be one who has since become
   disabled - a member who is Asleep or Charmed by the time the container is
   opened can still be the trap victim.
3. **Otherwise**, the game considers the roster positions inside the current
   party count whose status is Good or Poisoned. If exactly one qualifies it is
   chosen silently: no prompt appears **and the chosen member's name is not
   echoed**. That matters for output parity, because a prompted pick *does*
   echo the chosen member's name after the pick is confirmed; an engine that
   echoes the name in the single-qualifier case prints a line the original does
   not. If none qualifies, the command reports that
   nobody is able and aborts - before the trap can fire. If two or more qualify,
   the player is prompted to pick one; a confirmed pick that is not Good or
   Poisoned is rejected with the short "disabled" notice and the prompt repeats;
   cancelling the prompt aborts the command, again before the trap fires.

The prompt in branch 3 has exactly two non-selection outcomes, not three. The
shared picker can also answer "no active player" when the key for it is pressed,
but it only accepts that answer in the mode its *other* callers open it in; the
acting-member selection opens it in the mode that does not, so cancellation is
the only way out without a member. That is why both container sites test for a
single "nobody was chosen" answer and are still correct. A port that lets the
"no active player" key answer this prompt introduces a case the original does not
have.

The slot so chosen is the resolver's context argument, and it is the only
argument the resolver receives. Effect ids `0` and `1` consume it; effect ids
`2` and `3` ignore it entirely, so for those two the choice is unobservable.

Scoped consequence: **when the party is not in a combat-class scene and no
single active character is set**, a party with no Good-or-Poisoned member can
never spring a container trap, because the command aborts before reaching the
resolver. The two override cases above do not consult status at all and are
therefore *not* covered by that guarantee. An earlier draft of this rule was
circulated without that scope; the unscoped form is wrong and is withdrawn.

`systems/containers.md` describes the surface/town container path as asking for
"the party member who opens it". That is the same selection, but the prompt is
only one of its three outcomes; see the priority list above.

**Open gaps in this selection, stated rather than left silent.**

- Whether the combatant index the first branch reads really means "the
  combatant whose turn is in progress" is **not established**. It is used as an
  index into the live combatant records by several systems and is advanced like
  a turn cursor, but the combat round engine itself has not been traced. The
  container contract does not depend on the interpretation - the slot is
  whatever party position that combatant record names - but an implementation
  should not treat the phrase as derived fact. Tracing the combat round engine
  would settle it.
- The combat branch neither range-checks that index nor tests the "is a party
  member" flag on the record it reads, although the interactive picker tests
  exactly that flag. Some entry paths park an all-ones sentinel in that index in
  the same breath as they set a combat-class scene, and in that window the
  selection would read past the end of the combatant records. Whether a
  container can actually be opened inside that window is **UNVERIFIED**; it
  would be settled by tracing which scenes accept an Open while the index holds
  the sentinel. A port that range-checks the index is safe against every
  reachable case published here.
- The claim that only death clears the active-character hint - the hazard in
  branch 2 - rests on a scan of direct-addressing writes only; a write made
  through a computed pointer would not have been seen. Treat "a disabled active
  character can be the trap victim" as strongly indicated by the control flow
  but **not** proven reachable.

## 3. Effect Families

The shared resolver has four effect families:

| Effect id | Family | Behaviour |
|---:|---|---|
| 0 | Acid / single-slot damage | Prints the acid trap message, rolls a random damage amount bounded by `1..30`, applies it to the triggering party slot, and refreshes party stats. The roll is an inclusive `0..60` roll halved with truncation and floored to one - the same shape `systems/magic.md` publishes for Mani - so it is **not** uniform over `1..30`: low values are markedly more likely. This path applies **no status gate and no party-count check**: the caller-supplied slot is damaged whatever its status, so an Ashes member can be damaged here, and on reaching zero hit points the damage helper marks the character Dead, zeroes hit points, and clears the active-member hint when it named that slot. |
| 1 | Poison / single-slot poisoning | Prints the poison trap message and applies Poisoned status to the triggering party slot. The status helper acts only on a slot inside the current party count, and it skips **only** a member marked Dead; every other status, Ashes included, is overwritten with Poisoned. |
| 2 | Bomb / party damage | Prints the bomb trap message and rolls an inclusive `1..8` damage separately for each in-party member of the six-slot band that is not marked Dead - the only status excluded is Dead. Each accepted member is routed through the ordinary party-damage helper. The sweep applies the same two gates the status helper applies: an unsigned party-count check, then a Dead skip. It takes no context argument. |
| 3 | Gas / party poisoning | Prints the gas trap message and applies Poisoned status across slots `0..5` using the same status helper, so every in-party member of the six-slot band except those marked Dead ends up Poisoned. Ashes members are overwritten with Poisoned along with the rest. It takes no context argument. |

The status helper used by effect ids 1 and 3 is a poison primitive, not a
revival primitive. It applies exactly two gates.

1. The target slot must be below the current party count. The comparison is
   **unsigned**, so any slot index at or above the count - including a value
   that has wrapped or was never initialised - is silently ignored and nothing
   is written.
2. It compares the member's status against exactly one value, **Dead**, and
   skips the member on a match.

Dead is the *only* status it inspects. Every other status - including Ashes,
Sleeping, Charmed, and an existing Poisoned - falls through both gates and is
overwritten with Poisoned. An Ashes member in an in-party slot is therefore
converted to Poisoned, and no Ashes-specific handling exists anywhere on this
path. Read that as a conditional rather than as an observed event: whether the
shipped game ever *produces* an Ashes status is itself an open question, recorded
as a gap in `formats/saved-gam.md`. The contract established here is "if a status
byte holds Ashes when this path runs, it is overwritten with Poisoned" - not that
the conversion is reachable in normal play. *Corrected:* an earlier revision of this paragraph said the helper "skips
a member already marked Dead; a living member is left Poisoned", which reads as
though the helper distinguishes living members from otherwise-incapacitated
ones. It does not; that wording is withdrawn. The set of statuses it compares
against is exactly {Dead}, and that negative is bounded by the whole routine,
which was read end to end.

The write sets the member's status to Poisoned and redraws the stats panel. It
changes **no other field of the party record**: no hit points, no maximum hit
points, no magic points, and no relation to the resurrection spell path. That
negative is scoped to the party record deliberately. The stats redraw the helper
invokes can itself clear the active-member hint when the currently-active member
is already Dead or Asleep - a property of the redraw, not of this helper, and
one this helper's own write can never trigger, since Poisoned is neither of
those states. An earlier revision said the helper "changes nothing else" without
that scope; the unqualified form invites a port to assert more than has been
established, and is withdrawn. The redraw's deeper text and cursor primitives
were bounded only by a reference scan for the status field, so a status mutation
two or three levels below the redraw has been narrowed but not excluded.

Earlier drafts of this document described the helper as a narrow revive that
only rewrote dead members; that reading was backwards and is retracted. The
correct polarity is what gives effect ids 1 and 3 their in-game poison and gas
labelling.

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
Neither passes a trap *flavour* along - but both nevertheless pass a **victim
slot**, chosen by the shared acting-member selection of § 2.1 before either site
tests the trap condition. *Corrected:* an earlier revision said only "neither
passes any trap-class information along", which was read as though the resolver
received no caller context at all. It receives exactly one argument, and that
argument is the triggering party slot. Once they enter the shared resolver, the
four effect families above apply and the flavour is chosen here.

The two container sites are not otherwise identical. Three differences are
confirmed:

- The surface/town site prints its own "trapped" notice before the resolver
  runs; the dungeon chest site prints no trap line of its own and lets the
  resolver's effect message stand alone.
- The surface/town site alone performs a combat-scene cleanup after the resolver
  returns: if the chosen member is then Dead, it (a) finds that member's live
  combatant record and **sets a marker bit on it**, (b) **stamps a fixed
  non-zero marker value into the leading bytes of the world-object entry that
  record points at**, and (c) clears the active-character hint when that hint
  named the member. The dungeon chest site has no such step.

  *Corrected:* an earlier revision described the first two of those three steps
  as "removes that member from the live combatant records" and "blanks the
  associated world-object entry". Both descriptions are withdrawn as wrong. The
  combatant record is **not** removed, cleared, or freed - it stays in place with
  one additional bit set - and the world-object entry is **not** blanked: a
  specific constant is written into it. The third step is correct as previously
  published and was re-derived.

  **The constant is now established, and the gap is closed.** An earlier revision
  called it opaque and guessed it was "plausibly a remains or corpse marker". The
  guess was right, and it is now derived rather than guessed: the value is
  **decimal thirty**, written as two separate byte stores of the same value into
  **both leading bytes** of the record, and it is a **corpse**.

  **It is an object/actor class id, not a terrain tile id** - and that
  distinction is the whole point, because this specification has twice published
  errors from conflating those two spaces. The shipped description table settles
  it directly, since it holds the two domains separately: in the **object**
  domain that value reads "a corpse", while in the **terrain** domain the same
  number reads an unrelated landscape description. Three independent consumers
  key on the object reading, two of them by way of shipped data files, and the
  L-Look chain resolves it end to end through the object domain.

  So a port should write the value **as a corpse-class object**, not as an opaque
  stamp and not as a tile. The step is fully implementable.
- The trap conditions differ in kind, matching the two storage forms named
  above: a single flag on the container object versus a non-zero lock/trap
  sub-type on the dungeon chest cell.

A fourth difference is easy to miss and matters for § 2.1: the `O` Open
dispatcher routes to the dungeon chest handler **only** for the narrow band of
dungeon scenes, and routes every other scene - combat-class scenes included - to
the surface/town handler. Combat-class scene values sit far above the dungeon
band. The combat override in § 2.1 can therefore fire at the surface/town
container site and can **never** fire at the dungeon chest site. (Consistently,
only the surface/town handler carries combat-scene code at all.)

*Implementation footnote, not a contract.* The acting-member selection and the
resolver/container/picker layers do not use quite the same comparison for "is
this a combat-class scene": the two tests differ by one at the very bottom of
the combat-class range. Entering a combat-class scene saves the outgoing scene
value aside and writes a single all-ones marker into the scene byte; leaving it
restores the saved value. Every write of a literal scene value anywhere in the
shipped game writes one of a small fixed set, and of that set exactly one value
lies above the disagreement point - the all-ones combat marker itself. Every
other write of the scene byte copies either the saved outgoing value or a value
taken off the location stack, and both of those are themselves fed from the scene
byte, so the reachable set is closed. Consequently **no reachable scene value is
known to fall inside the disagreement**, and a port may pick either boundary and
match the original on every state that has been observed. Do not treat this as a
behavioural requirement; it is recorded so that a reader who finds the
inconsistency knows it was seen and judged inert. Scope: the enumeration behind
it covers direct-addressing writes to the scene byte only - a write made through
a register or base pointer, or through a segment override, would not have been
seen - and the closure argument assumes the saved-scene byte and the location
stack only ever receive values that came from the scene byte, which was not
separately verified. It is therefore strong evidence, not proof, and a
hand-edited or corrupt save could violate it.

Because the flag doubles as the lock flag, a successful Jimmy disarms the
container as well as unlocking it, so a Jimmy-then-Open sequence never reaches
this resolver at all. Jimmy writes the persisted flag itself.

**Neither container site can spring twice; the trap condition is consumed by
opening.** The surface/town site clears the entire matched container record - its
kind, its position, and the byte that carries the trap flag - as part of opening
it, and it does so *after* taking its own local copy of that byte. That ordering
is why the trap still fires on this open: the decision is made from the copy, the
record is already gone. The record lives inside the persisted save image, so the
clear survives a save and reload, and a later Open of the same square matches no
container and simply reports that there is nothing to open. The dungeon chest
site behaves consistently: it rewrites its cell to the opened form and clears the
trap sub-type bits **whether or not the trap fired**, so that cell cannot re-arm
either; the cell's later state is owned by `systems/dungeon-mode.md`.

*Corrected:* an earlier revision published this as an open gap, on the premise
that "the surface/town container handler masks the trap bit out of its own
working copy of the object's status byte only" and "does not rewrite" the
persisted record. **That premise is false and is withdrawn.** The handler does
rewrite the record - it zeroes the record's leading fields between choosing the
acting member and testing the trap condition - and the gap is closed in the
direction `systems/containers.md` already stated. Do not reintroduce the
uncertainty: a trapped surface or town container does **not** re-spring on a
second Open, because there is no second Open to make.

The caller selection layer is documented with the command/container helpers:
surface chest content pools live in `systems/containers.md`, the lock rolls live
in `systems/doors-and-z-transitions.md`, and dungeon room combat arena selection
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
share one implementation. Note that the mixer does **not** use the § 2.1
acting-member selection; it supplies its victim slot itself. The mixer owns the
reagent loss and no-charge result; before calling the trap-effect resolver it
refreshes its target slot to the first travelling member currently marked Good
or Poisoned when such a member exists. When no such member exists the slot is
left holding whatever it last held, and the trap lands on that stale value; a
port should treat that as undefined behaviour and decide deliberately rather
than inventing a fallback.

Two things bound the damage that stale value can do. The status helper behind
effect ids 1 and 3 gates its slot with an **unsigned** party-count comparison,
so a stale value at or above the party count is a silent no-op there and cannot
corrupt anything; the undefined-behaviour framing applies to a stale value that
happens to land *below* the party count, which poisons an arbitrary member. The
single-slot damage effect (effect id 0) has no such gate, so a stale value out
of range would be written through by that path.

*Corrected, and flagged as needing its own trace:* an earlier revision called
the mixer's target a "scratch slot" whose stale content is "whatever party index
it last held". That is true in letter but misleading in substance. The word the
mixer writes is not dedicated scratch: it is the same resident word the
world-coordinate bookkeeping uses as a map origin, incremented and decremented
by movement handling and added to the party's local coordinate to form a world
coordinate. When no Good-or-Poisoned member exists, the value the trap lands on
is therefore most likely a map coordinate rather than a previous party index.
**UNVERIFIED:** whether the mixer's overwrite of that word also disturbs the
party's world position - that is, whether the map origin is recomputed
afterwards - has not been traced, and it should be settled before anyone writes
a confident sentence about wrong-mix side effects.

A spell name the parser cannot match takes the same wrong-recipe path, so a
mistyped incantation also springs the trap. The trap resolver then applies the
ordinary four-family effect contract above.

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
caller layer above it is covered: selection is a single trapped/not-trapped bit,
and the three call sites named in § 1 are the only ones that reach the resolver.
That census was re-run and widened on 2026-08-23. It now covers, in every shipped
code file, both direct near calls **and** direct near jumps, tested against every
overlay load base observed across the file set rather than one assumed base; a
whole-file search of every shipped file for the resolver's entry stored anywhere
as a data word, which found none, closing the far-call-with-immediate and
stored-function-pointer routes; and an inspection of the bytes immediately before
the resolver, which end in a return plus one alignment byte, closing entry by
fall-through. It remains a bounded negative in exactly one respect: a call
through a pointer computed at run time and never stored as a literal entry value
would still evade it.

These items are published as explicit gaps rather than omitted, and an
implementation should treat them as genuinely unspecified rather than as
oversights:

- The meaning of the combatant index in § 2.1.
- Whether a container can be opened while that index holds its sentinel.
- Whether the mixer's reuse of the map-origin word disturbs the party's world
  position.
- What the fixed constant stamped into the world-object entry by the
  surface/town combat cleanup in § 4 denotes.
- Whether the shipped game ever produces an Ashes status at all, which decides
  whether § 3's Ashes-to-Poisoned conversion is reachable in play or only a
  conditional. That gap is owned by `formats/saved-gam.md`.
- In the caller layer, the dungeon chest lock/trap sub-type is documented here
  only as "non-zero means trapped"; the claim that the sub-type is non-zero
  exactly when the chest is both locked and trapped has not been re-derived. The
  mechanical test and the post-open rewrite of those bits *have* been.

One item previously listed here has been **closed** and is no longer a gap:
whether Open clears a surface container's persisted trap flag. It does; § 4 now
specifies it, and the earlier gap wording is withdrawn there.

Caller selection remains owned by the invoking systems:

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

Source provenance for the 2026-08-23 revision - § 2.1's acting-member selection
and its scoped consequence, the per-site container differences and the Open
dispatcher's scene routing, the exact two gates and single status comparison in
the poison helper, the absence of any status or party-count gate on the
single-slot damage effect, the non-uniform shape of that effect's damage roll,
and the map-origin identity of the mixer's target word: re-derived directly from
the shipped binaries during that revision, with private analysis in
`u5-decomp/functions/SJOG_OVL/`, `u5-decomp/functions/CMDS_OVL/` and
`u5-decomp/functions/ULTIMA_EXE/` used only to locate starting points. The
private notes for the acting-member selection and for the surface container
handler mislabel that selection (as a party-join prompt and as a direction
prompt respectively) and read the status byte as a class byte; those private
notes are wrong against the binaries and this document does not follow them.

Source provenance for the later 2026-08-23 revision - the closure of the
Open-clears-the-trap-flag gap in § 4, the two corrected phrases in the
combat-cleanup bullet, the widened call-site census in § 5, the strengthened
scene-boundary footnote, and the no-name-echo detail in § 2.1 branch 3: an
adversarial re-verification pass that re-derived every load-bearing step directly
from the shipped binaries without relying on private notes, reading each of the
routines involved - both container handlers, the Open dispatcher, the
acting-member selector, the interactive picker, the trap-effect resolver, the
poison and damage helpers, the bomb sweep, the active-member setter and the
object-record writer - from entry to return rather than in filtered extracts.
Private analysis in `u5-decomp/functions/SJOG_OVL/`,
`u5-decomp/functions/CMDS_OVL/` and `u5-decomp/functions/ULTIMA_EXE/` was used
only to locate starting points; where those notes disagreed with the binaries the
binaries were followed. That pass also re-confirmed § 3's poison-helper gates and
the § 2 effect distribution independently.
