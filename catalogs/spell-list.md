# Spell List

A reference catalog of every spell in Ultima V: its compact parser token, runic
incantation, player-facing effect label, circle, reagent recipe, scene mask,
and broad effect category. The cast and mix command flows live in
`systems/magic.md`; this file is the lookup table those systems consume.

## 1. Overview

Ultima V has exactly forty-eight spells. The resident spell tables are ordered
as eight circles of six spells each. A spell's circle is also its mana cost and
minimum caster level:

- `circle(id) = (id / 6) + 1`, using integer division.
- `mana_cost(id) = circle(id)`.
- `minimum_level(id) = circle(id)`.

The spell-name parser uses the compact token column, not the full runic
incantation. The parser sorts the typed selector letters before table lookup,
so token order is canonical here but player input order is not significant.
The compact token table, recipe masks, and scene allow masks are resident data.
Player-facing labels and short effect summaries are aligned with the published
spellbook/manual names and the decoded handler behaviour.

**Correction (supersedes earlier revisions).** Earlier revisions of this
section described the resident long-incantation display phrase table as sparse:
forty-seven entries for forty-eight parser ids, with `Frotz` intruding in the
high-circle area and the final Negate Time id left without a phrase. That was
an artefact of reading the phrase strings as one packed run and starting two
strings too late. The phrases are not reached by scanning the string area; they
are reached through a **forty-eight-entry pointer table**, one pointer per spell
id, sitting immediately after the eight reagent-name pointers. Under that
anchor the phrase table is dense and exactly one-to-one with parser ids `0..47`:
id `0` is `In Lor` and id `47` is `An Tym`. `Frotz` is simply the next string
after id 47 and is not a spell incantation at all. The alignment is confirmed
independently: for all forty-eight ids the compact parser token equals the
alphabetically sorted initials of that id's phrase words, which holds
forty-eight times out of forty-eight under the pointer-table anchor and fails
under the old one. Id 46 is `PRV` / `Vas Rel Por` / Gate Travel — that
attribution was always correct and is unaffected.

**This check is reproducible from the table in Section 3 alone**, without any
private analysis: for every id, sort the letters of the parser token and compare
them with the sorted initials of the phrase's words. It holds forty-eight times
out of forty-eight. A reader who doubts the anchor can therefore falsify it here
rather than taking it on trust - which is the point of stating it, since an
anchor slip of a fixed number of entries produces a table that is internally
consistent and wrong, and is the most common failure in this specification.

## 2. Rune Syllables

The spell incantations use this twenty-four-syllable vocabulary.

| Syllable | Loose meaning |
|---|---|
| An | negate, dispel, undo |
| Bet | small, lesser, minor |
| Corp | death, dead, mortality |
| Des | down, lower, descend |
| Ex | freedom, release, set loose |
| Flam | flame, fire, heat |
| Grav | field, energy field, contained area |
| Hur | wind, weather, breath |
| In | create, make, cause |
| Kal | summon, invoke, call forth |
| Lor | light, illumination |
| Mani | life, healing, restoration |
| Nox | poison, toxin |
| Por | movement, motion, transport |
| Quas | illusion, image, deception |
| Rel | change, alter |
| Sanct | protection, ward |
| Tym | time |
| Uus | up, raise, ascend |
| Vas | great, large, increased |
| Wis | knowledge, sight, awareness |
| Xen | creature, being, animal |
| Ylem | matter, substance, raw stuff |
| Zu | sleep, stillness |

`Jux` and `Ort` appear in wider Britannian magic lore, but they are not
resident U5 spell-prompt selectors and are not needed to spell any of U5's
forty-eight spell incantations.

## 3. Reagents and Masks

The M-Mix command compares the player's selected reagent set against a
one-byte recipe mask. The bit order is:

| Bit | Reagent |
|---:|---|
| `0x80` | Sulfur Ash |
| `0x40` | Ginseng |
| `0x20` | Garlic |
| `0x10` | Spider Silk |
| `0x08` | Blood Moss |
| `0x04` | Black Pearl |
| `0x02` | Nightshade |
| `0x01` | Mandrake |

The table below lists recipes semantically rather than dumping the raw bytes.
To reconstruct the exact resident recipe byte, OR the listed reagent bits.

Recipes are not unique. Several distinct spells share an identical reagent set,
so a recipe alone does not identify a spell. That is why M-Mix asks the player
to name the spell first and then compares the chosen reagents against that one
spell's recipe: the mixer matches a recipe, it never searches for one.

## 4. Scene Mask

Each spell also has a one-byte scene allow mask. The cast dispatcher computes a
single scene bit from the active scene byte, then requires that bit to be set
in the spell's mask.

| Bit | Short | Scene class |
|---:|:---:|---|
| `0x01` | C | Combat |
| `0x02` | D | Dungeon scenes |
| `0x04` | I | Indoor/town-mode scenes, including towns, dwellings, castles, keeps, and special indoor states |
| `0x08` | O | Overworld |

The `Allowed` column uses those short labels. For example, `D/I/O` means the
spell can be cast in dungeons, indoor scenes, and the overworld, but not in
combat.

The active scene byte maps to those bits as follows:

- `0`: overworld (`O`).
- `1..32`: indoor/town-mode (`I`), covering towns, dwellings, castles, and
  keeps.
- `33..127`: dungeon (`D`).
- `0xFF`: combat-class (`C`). Several readers treat any value at or above
  `0x80` as combat-class, but the traced gameplay writers use `0xFF` for
  combat and combat-like freezes.

Two indoor scene states short-circuit before the mask comparison:

- Lord Blackthorn's Castle absorbs casts while the Crown of Lord British
  ownership flag is clear.
- Stonegate absorbs casts unconditionally.

In those states the dispatcher prints `Absorbed!` and aborts before consuming a
charge or mana.

**Correction (supersedes earlier revisions of this section).** Earlier
revisions of this catalog published the dungeon and combat bits transposed,
as `0x01` = dungeon and `0x02` = combat. That was wrong, and it is the mapping
a reader would have used when decoding the resident mask table directly. The
dispatcher's scene gate classifies the scene byte first and then tests exactly
one bit per class: overworld selects `0x08`, combat-class selects `0x01`,
indoor/town-mode selects `0x04`, and the dungeon-class band selects `0x02`.
The corrected assignment is the one in the table above. The scene-byte
classification bands and every `Allowed` entry in the Section 5 table were
published correctly throughout and are unchanged by this correction — the
defect was confined to the bit legend, so any reader who stayed inside the
`C`/`D`/`I`/`O` labels was unaffected, while any reader who decoded the
resident mask bytes through the old legend would have swapped the
combat-only and dungeon-only spells.

## 5. Spell Table

| ID | Code | Rune-Name | Common Name | C | Recipe | Allowed | Category |
|---:|:---:|---|---|:-:|---|:---:|---|
| 0 | `IL` | In Lor | Light | 1 | Sulfur Ash | D/I/O | utility |
| 1 | `GP` | Grav Por | Magic Missile | 1 | Sulfur Ash + Black Pearl | C | damage; single target, raw roll 1..16 before target defense |
| 2 | `AZ` | An Zu | Awaken | 1 | Ginseng + Garlic | C/D/I/O | healing; wakes the first Sleeping party member found in roster order |
| 3 | `AN` | An Nox | Cure | 1 | Ginseng + Garlic | C/D/I/O | healing; selected-member Poisoned-to-Good status gate |
| 4 | `M` | Mani | Heal | 1 | Ginseng + Spider Silk | C/D/I/O | healing; selected-member HP add from halved 0..60 roll with minimum 1, skips only Dead targets, clamps at maximum HP |
| 5 | `AY` | An Ylem | Vanish | 1 | Garlic + Blood Moss | C/I | utility; directed tile helper, clears a removable-object tile to the shared cleared-cell tile `0x44` and prints `POOF!`; works on combat-arena terrain too |
| 6 | `AS` | An Sanct | Open | 2 | Sulfur Ash + Blood Moss | C/D/I/O | utility; directed tile helper, unlocks a locked door (`0xB9`→`0xB8`, `0xBB`→`0xBA`) or clears the lock/trap bit on a co-located kind-1 chest object — including a monster's combat drop; separate dungeon-cell arm in dungeon scenes |
| 7 | `ACX` | An Xen Corp | Repel Undead | 2 | Sulfur Ash + Garlic | C | buff/debuff; drives every undead-class monster-side actor that fails the resistance check to combat HP 1 and sets its fleeing bit; protected classes 14/15/47 excluded; creates and repurposes nothing |
| 8 | `HR` | Rel Hur | Wind Change | 2 | Sulfur Ash + Blood Moss | O | utility |
| 9 | `IW` | In Wis | Locate | 2 | Nightshade | O | utility; prints the shared sextant-style Y-then-X coordinate line |
| 10 | `KX` | Kal Xen | Conjure | 2 | Spider Silk + Mandrake | C | summon; sixteen-outcome selector, 6 Giant Rat / 5 Giant Spider / 3 Bat / 2 Python, one actor on the first of up to eight legal random arena probes |
| 11 | `IMX` | In Xen Mani | Create Food | 2 | Ginseng + Garlic + Mandrake | C/D/I/O | utility; adds random 1..3 food/provisions, capped at 9999 |
| 12 | `LV` | Vas Lor | Great Light | 3 | Sulfur Ash + Mandrake | D/I/O | utility |
| 13 | `FV` | Vas Flam | Fireball | 3 | Sulfur Ash + Black Pearl | C | damage; single target, raw roll 1..30 before target defense |
| 14 | `FGI` | In Flam Grav | Fire Field | 3 | Sulfur Ash + Spider Silk + Black Pearl | C/D | field |
| 15 | `GIN` | In Nox Grav | Poison Field | 3 | Spider Silk + Black Pearl + Nightshade | C/D | field |
| 16 | `GIZ` | In Zu Grav | Sleep Field | 3 | Ginseng + Spider Silk + Black Pearl | C/D | field |
| 17 | `IP` | In Por | Blink | 3 | Spider Silk + Blood Moss | C/O | utility |
| 18 | `AG` | An Grav | Dispel Field | 4 | Sulfur Ash + Black Pearl | C/D | field |
| 19 | `IS` | In Sanct | Protection | 4 | Sulfur Ash + Ginseng + Garlic | C/D/I/O | buff/debuff; shared timed-effect slot, tag `P`, 20 turns; no mechanical consequence in the shipped game |
| 20 | `GIS` | In Sanct Grav | Energy Field | 4 | Spider Silk + Black Pearl + Mandrake | C/D | field |
| 21 | `PU` | Uus Por | Up | 4 | Spider Silk + Blood Moss | D | utility; moves the party one dungeon level up from wherever it stands, no ladder needed; refuses a destination cell in the base or wall/door classes; cast on the topmost level it leaves the dungeon to Britannia; refused outright in Doom |
| 22 | `DP` | Des Por | Down | 4 | Spider Silk + Blood Moss | D | utility; the mirror of id 21 - one level down, no ladder needed, same destination-cell refusal; cast on the lowest level it leaves the dungeon into the Underworld; refused outright in Doom |
| 23 | `QW` | Wis Quas | Reveal | 4 | Spider Silk + Nightshade | C | utility |
| 24 | `BIX` | In Bet Xen | Swarm | 5 | Sulfur Ash + Spider Silk + Blood Moss | C | summon; up to eight probes find one legal cell, then up to four Insect Swarm actors are placed at that single coordinate |
| 25 | `AEP` | An Ex Por | Magic Lock | 5 | Sulfur Ash + Garlic + Blood Moss | C/I | utility; directed tile helper, `0xB8`/`0xB9`→`0x97` and `0xBA`/`0xBB`→`0x98`; works on combat-arena terrain too |
| 26 | `EIP` | In Ex Por | Unlock Magic | 5 | Sulfur Ash + Blood Moss | C/I | utility; directed tile helper, the only magic-lock removal: `0x97`→`0xB8` and `0x98`→`0xBA`; works on combat-arena terrain too |
| 27 | `MV` | Vas Mani | Great Heal | 5 | Ginseng + Spider Silk + Mandrake | C/D/I/O | healing; selected-member current HP restore to maximum, refuses Dead targets and the dungeon combat-active substate |
| 28 | `IZ` | In Zu | Sleep | 5 | Ginseng + Spider Silk + Nightshade | C | buff/debuff |
| 29 | `RT` | Rel Tym | Quickness | 5 | Sulfur Ash + Blood Moss + Mandrake | C/D/I/O | buff/debuff; shared timed-effect slot, tag `Q`, 30 turns; halves the per-turn minute increment and gates the automatic actor driver, so hostiles act about half as often while the player's own prompt is unaffected |
| 30 | `IPVY` | In Vas Por Ylem | Tremor | 6 | Sulfur Ash + Blood Moss + Mandrake | C | damage |
| 31 | `AQW` | Quas An Wis | Mass Charm | 6 | Nightshade + Mandrake | C | buff/debuff; shared timed-effect slot, tag `C`, 20 turns; AI target remap |
| 32 | `AI` | In An | Negate Magic | 6 | Sulfur Ash + Garlic + Mandrake | C/D/I/O | marquee; shared timed-effect slot, tag `N`, 10 turns; absorbs combat casts |
| 33 | `AWY` | Wis An Ylem | X-Ray | 6 | Sulfur Ash + Mandrake | I/O | utility |
| 34 | `AEX` | An Xen Ex | Charm | 6 | Spider Silk + Black Pearl + Nightshade | C | buff/debuff; toggles the controlled/charmed descriptor bit `0x01` on the picked creature (a second cast clears it), sets a party-side target's roster status letter back to Good, prints `<name> charmed!` and suppresses the shared epilogue; it does not change faction |
| 35 | `BRX` | Rel Xen Bet | Polymorph | 6 | Sulfur Ash + Spider Silk + Nightshade + Mandrake | C | buff/debuff |
| 36 | `LS` | Sanct Lor | Invisibility | 7 | Blood Moss + Nightshade + Mandrake | C | buff/debuff; caster-only hidden flag with no duration at all, and no use of the shared timed-effect slot |
| 37 | `CX` | Xen Corp | Kill | 7 | Black Pearl + Nightshade | C | damage; creature-target instant kill; classes 14/15/47 reject after charge, 7 MP, and pre-effect but before resistance, consume the turn, then report `Failed!` without gameplay randomness or a re-prompt |
| 38 | `IQX` | In Quas Xen | Clone | 7 | Sulfur Ash + Ginseng + Spider Silk + Blood Moss + Mandrake | C | summon |
| 39 | `IQW` | In Quas Wis | Peer | 7 | Nightshade + Mandrake | D/I/O | utility |
| 40 | `HIN` | In Nox Hur | Poison Wind | 7 | Sulfur Ash + Blood Moss + Nightshade | C | damage |
| 41 | `CIQ` | In Quas Corp | Cause Fear | 7 | Garlic + Nightshade + Mandrake | C | buff/debuff; drives every monster-side actor that fails the resistance check to combat HP 1 and sets its fleeing bit; protected classes 14/15/47 excluded; no undead condition |
| 42 | `CIM` | In Mani Corp | Resurrect | 8 | Sulfur Ash + Ginseng + Garlic + Spider Silk + Blood Moss + Mandrake | D/I/O | healing |
| 43 | `CKX` | Kal Xen Corp | Summon | 8 | Garlic + Spider Silk + Blood Moss + Mandrake | C | summon; places one Daemon (class 38) on the first of up to eight random arena probes whose cell passes the shared spawn-cell validator (Summon re-tests the impassable void terrain byte itself, duplicating a rejection the validator already makes, so it changes no outcome), through the ordinary monster placement path (hostile, AI-driven); then the caster self-check rolls `1..30` against the caster's Intelligence and, on roll at or above that value, prints `Oops...`, returns the silent-failure result and leaves the Daemon uncontrolled; on success it stamps the controlled bit `0x01` |
| 44 | `CGIV` | In Vas Grav Corp | Death Wind | 8 | Sulfur Ash + Nightshade + Mandrake | C | damage |
| 45 | `FHI` | In Flam Hur | Flame Wind | 8 | Sulfur Ash + Blood Moss + Mandrake | C | damage |
| 46 | `PRV` | Vas Rel Por | Gate Travel | 8 | Sulfur Ash + Black Pearl + Mandrake | D/I/O | marquee |
| 47 | `AT` | An Tym | Negate Time | 8 | Garlic + Blood Moss + Mandrake | C/D/I/O | marquee; shared timed-effect slot, tag `T`, 10 turns; freezes the clock, and in combat makes the automatic actor driver return at once so every self-acting actor's turn is skipped |

## 6. Notes for Implementers

- The table is ordered by engine spell id, not alphabetically and not by the
  manual's display grouping.
- The long rune-name strings in this catalog agree with the resident display
  phrase table, which is dense and one-to-one with spell ids `0..47` when read
  through its pointer table. They are also independently corroborated by the
  parser tokens, the manual spell names, and handler behaviour.
- The compact code is the exact token used by both C-Cast and M-Mix. Examples:
  `IL` is `In Lor`, `GP` is `Grav Por`, `IPVY` is `In Vas Por Ylem`,
  `PRV` is `Vas Rel Por`, and `AT` is `An Tym`.
- The parser accepts up to four selector letters, ignores input order by
  sorting before lookup, and does not accept full incantation text as an alias.
- M-Mix succeeds only when the selected reagent mask exactly equals the recipe
  mask for the chosen spell id. A superset is not accepted.
- M-Mix debits the selected reagents before checking whether the selected mask
  matches the recipe. A wrong mix consumes reagents, adds no spell charges,
  and invokes the shared trap-effect resolver described in `systems/traps.md`.
- In M-Mix, a nonblank selector that matches no spell can still proceed into
  reagent selection; if the player completes a nonzero mix, it behaves as a
  wrong recipe and follows the same reagent-loss and trap-effect path.
- Successful mixing increments the chosen spell's premixed charge counter by
  the selected quantity and caps the result at 99.
- C-Cast consumes one premixed charge before the mana and level checks. A
  failed mana or level gate does not restore that charge. The level failure
  happens after mana debit, so an under-level caster also loses mana.
- `In Lor` starts or refreshes the light-spell counter at 100 counter units.
  `Vas Lor` starts or refreshes the same counter at 255 units. Neither spell
  consumes a torch; torch inventory and torch duration belong to I-Ignite.
- Dungeon field placement uses exact terrain bytes: Fire Field writes `0x82`
  or `0x8A`, Poison Field writes `0x81` or `0x89`, Sleep Field writes `0x80`
  or `0x88`, and Energy Field writes `0x83` or `0x8B`. The second form is the
  same field with the existing dungeon visit marker bit preserved. Placement
  succeeds only on live dungeon passage bytes `0x00` or `0x08`; all other
  selected cells fail with no live-map write.
- Non-combat Blink is direction-prompted and deterministic. It scans from the
  adjacent cell in the chosen cardinal direction through the active 32-by-32
  loaded world window and lands on the farthest grass tile (`0x05`) found on
  that ray. It does not choose a random target, does not retry candidate cells,
  and does not use the ordinary movement passability or active-object
  occupancy checks. If no grass tile is found, the spent cast fails without
  moving the party.
- `AY`, `AS`, `AEP` and `EIP` form one directed-tile family. Each prompts for a
  direction, resolves the single orthogonally adjacent cell, tests that cell's
  live tile and rewrites it. The prompt origin is the party's map cell outside
  combat and the **acting combat actor's arena cell** inside combat, and the
  live-tile lookup resolves to the combat-arena terrain grid whenever the scene
  is combat-class, so all four really do mutate arena terrain during a fight.
  Answering the prompt with Space prints `Pass` and ends the cast silently; the
  premixed charge and mana were already debited and are not refunded. A matched
  tile prints `Success!` — except Vanish and the dungeon arm of Open, which
  print their own line (`POOF!`, and the disarm/chest-opened pair) and suppress
  the shared epilogue — and a non-matching tile prints `Failed!` with the
  failure sound. The tile maps are: Vanish accepts `0x5B`, `0x90`, `0x91`,
  `0x92`, `0x93`, `0x9D`, `0xA5`, `0xA6`, `0xA8`, `0xA9`, `0xAD`, `0xAE`, `0xAF`
  and writes `0x44`; Open (non-dungeon arm) turns `0xB9` into `0xB8` and `0xBB`
  into `0xBA`, else clears the lock/trap high bit on a kind-1 chest object at
  the target cell, skipping that object's Z test in combat scenes; Magic Lock
  turns `0xB8`/`0xB9` into `0x97` and `0xBA`/`0xBB` into `0x98`; Unlock Magic
  performs the inverse `0x97`→`0xB8` and `0x98`→`0xBA`. Vanish and Magic Lock
  play their cast effect as soon as the direction is accepted, and Unlock
  Magic's is played for any outcome other than Space/Pass, so a failed cast of
  those three is still audible/visible before `Failed!`; only Open holds its
  effect until a success branch. Earlier guidance that
  these four are unmodelled combat no-ops that always print `Failed!` without
  prompting is withdrawn.
- Combat eligibility for that family is uneven by arena family. Outdoor combat
  arenas contain no door tiles, and exactly one of them carries Vanish-family
  object tiles. Open is the exception to that scarcity: its object arm matches
  the kind-1 chest record a dying monster drops, so combat Open has a reachable
  success case in every arena regardless of terrain. Dungeon-room arenas contain door tiles in eighteen arenas — the
  magic-locked, ordinary-locked and unlocked forms all appear — and
  Vanish-family object tiles in seven. Combat Open always takes the non-dungeon
  arm, because the arm split keys on the dungeon-exploration scene class rather
  than on which arena file the fight loaded. Off-arena directions are not
  clamped by the original; treat them as non-matching and report `Failed!`.
- The CAST dispatcher table follows this exact public order. Handler-family
  classification is now known for the major shared cases: `IL`/`LV` write the
  light counter, while `GP`/`FV` are active-target attack wrappers using the
  combat aiming/projectile path; `GP` rolls 1..16 raw damage and `FV` rolls
  1..30 raw damage, with both rolls reduced by target defense before
  damage/status. `CX` is a separate `Creature: ` cursor handler: it applies the
  protected-class and shared-resistance gates before its death helper rather
  than using the projectile wrapper or decimal-99 damage sentinel.
  `FGI`/`GIN`/`GIZ`/`GIS` share the field-placement helper, `IPVY` scans the
  whole combat actor table for Tremor damage checks, rolls 1..20 damage per
  accepted actor, and credits returned monster-kill reward units to the
  caster's experience with a 9999 cap. `IZ`/`HIN`/`CGIV`/`FHI` share the
  directed wind-cone helper: the spell prompts for a cardinal direction, builds
  the widening clipped cone from the caster's adjacent cell, de-duplicates
  selected cells, and writes up to 63 arena coordinates before scanning actors.
  Neither the shared scan nor the per-effect branches perform a friend/foe
  lookup or same-faction exclusion. `IZ` applies party sleep status or the
  non-party combat sleep/disabled bit; non-party wake uses the combat actor's
  later 1-in-17 own-turn wake check rather than a seeded countdown. `HIN` applies a
  resistance/random gate before poison status, `CGIV` uses the decimal 99
  instant-kill sentinel through the shared damage/status path, and `FHI` rolls
  raw 1..30 through that same path. The two damage winds credit returned
  monster-kill reward units to the caster with the normal 9999 experience cap.
  `IS`/`RT`/`AQW`/`AI` route through the shared active-effect display helper
  with cast-time tag/counter pairs `P`/20, `Q`/30, `C`/20, and `N`/10.
  All four write the one shared timed-effect slot, so a new effect replaces the
  previous one rather than stacking; the three timed scrolls and the three
  regalia auras share that same slot. The `IS` `P` tag has no effective
  consumer: the party-member defence bonus it was meant to add rides on a
  per-item defence total that is unreachable and never read, so Protection
  changes no combat number in the shipped game. The `RT` `Q` tag also halves
  the per-turn game-minute increment outside combat, with a floor of one
  minute, and in combat gates the **automatic actor driver** with an inclusive
  0..1 random roll: zero consumes that dispatch without acting, while one
  continues normally. The round walker sends self-acting actors to that driver
  and the player's turns to the keystroke parser, so the gate slows hostiles
  and leaves the player's own prompt alone; the `AT` `T` tag makes the same
  driver return immediately, skipping self-acting turns entirely. Earlier
  wording here said `Q` gated "player and enemy turns" and that `T` "skips
  enemy turns" as a separate mechanism from the clock freeze; both are
  withdrawn in favour of the single pair of tests described in
  `systems/combat.md` Section 9.
  The `AQW` `C` tag is consumed by monster AI target selection; while active,
  each target pick rolls one uniform byte in `[0, 255]` against the acting
  monster's class charm threshold. A roll strictly greater than that threshold
  remaps the acting monster to neutral group 0 before friend/foe filtering.
  The `AI` `N` tag absorbs combat casts before the shared spell dispatcher
  spends a premixed charge or MP.
  `AEX`/`BRX`/`IQX` use the `Creature:` target prompt; `BRX` replaces the
  accepted target with a class 20 Giant Rat, while `IQX` duplicates the target
  into paired free combat/dynamic-object slots and places the copy at a random
  legal arena coordinate. Clone writes no partial record if either table is
  full; the original capacity-failure result word is undefined, so exact bug
  compatibility may expose unpredictable success/failure narration. No traced
  Clone helper installs a separate per-spell duration counter; combat-exit
  lifetime is bounded by the combat framer's table restore. `CIQ` (Cause Fear)
  sweeps all thirty-two combat slots and, for every monster-side actor that
  fails the shared resistance check, drives its combat HP to one and sets the
  flee bit `0x02` directly; the combat wound-score morale classifier then keeps
  re-asserting the flag from that critical-HP state. `ACX` (Repel Undead) is the same
  critical-HP flee setup narrowed to monster-side actors whose class carries the
  undead flag, with the three protected special classes (14 Blackthorn, 15 Lord
  British, 47 Shadow Lord) excluded from both spells' sweeps: it drives the accepted actor's combat HP to one
  and sets the flee bit `0x02`. It is not a summon or tame effect and does not
  write the controlled bit `0x01`; earlier text describing it as a
  "summon/tame-style repurpose helper" is withdrawn.
  Conjure, Swarm, and Summon share one random placement probe: each probe draws
  X and Y independently and uniformly over the inclusive range `0..15` and
  rejects the whole candidate unless both are at most 10, consuming that attempt
  rather than re-rolling, so the per-probe acceptance chance is `(11/16)^2`.
  Accepted candidates then go to the shared combat spawn-cell validator.
  Conjure rolls one inclusive `0..15` value — sixteen outcomes — and selects
  Giant Rat (class 20) on six of them, Giant Spider (class 22) on five, Bat
  (class 21) on three and Python (class 34) on two, then makes up to eight
  probes and places one actor on the first legal cell; its terrain-suitability
  query always uses the Giant Rat movement family regardless of the rolled
  class. Swarm makes up to eight probes to find a **single** legal cell, then
  places up to four Insect Swarm actors (class 31) at that one coordinate; there
  is no caster-centred ring and no jitter retry. Every actor placed by Conjure or
  Swarm is stamped with the controlled/charmed descriptor bit `0x01`, and Summon
  stamps it only when its caster self-check succeeds, but all three place through
  the ordinary monster path, so the creature is a monster-side, AI-driven
  actor. The bit does not hand the creature to the player, but it is the team
  toggle the combat slot-to-group helper reads, so a stamped creature groups
  with the party rather than with the monsters for the same-faction filter
  (`systems/combat.md` Section 6.1a); it also redirects that actor's attack
  action into the fixed magic-strike branch, which additionally requires an
  adjacent target.
  Clone duplicates an accepted creature into
  paired free combat actor and dynamic-object slots, and Summon uses the
  self-checking per-tile placement helper to create a Daemon-class combat actor
  (class 38) at the first accepted cell from up to eight of the shared probes.
  Summon also re-tests the candidate cell's live terrain byte against the
  arena's impassable void byte itself, but the shared spawn-cell validator
  already rejects that byte, so the duplicate test changes no outcome. It does not use the
  direction prompt, an adjacent cached target coordinate, or an ordered
  eight-cell ring. Summon's self-check threshold is a concrete stat — the
  caster character's **Intelligence** for a party caster (the only case a player
  C-Cast can reach), or the class row's **endurance rating**, the third of the
  eight class-stat fields, for a monster caster (this field was published as
  "flip-HP" in earlier revisions; that name is withdrawn along with the
  team-flip mechanic it referred to) — compared against a
  uniform inclusive `0..60` roll halved with the fraction discarded and floored
  to one, i.e. `1..30`. On `roll >= threshold` the cast prints `Oops...`,
  returns the silent-failure result, and leaves the Daemon placed but
  **without** the controlled bit. A
  previously suspected CAST2 placement helper is now attributed to shrine/urn
  kneel presentation. It prepares temporary active-object records from a
  private visual pattern and is not a traced party C-Cast row for Conjure,
  Swarm, or Summon. Do not publish or reuse that private pattern as spell
  placement data.
  `PRV` prompts `To phase:` and accepts digits `1`..`8`,
  mapping the digit to the matching persisted moonstone slot before teleporting
  to that slot's saved scene/X/Y/Z destination. Moonstone burying writes those
  slots only outside dungeon/combat scenes and only from underfoot tile ids
  `4..10`, `44`, or `45`; Search/Get recovery invalidates the matching slot.
  `AT` starts Negate Time with shared runtime tag `T` and a 10-count countdown
  unless blocked by magic absorption. Command-dispatch cleanup and the combat
  active-player/selection cleanup path age nonzero/non-255 countdowns and clear
  the tag on expiry; ordinary clock cleanup only observes `T` to skip minute
  advancement while stopped time is active. Tremor does not run a friend/foe lookup; party actors and
  monsters are eligible alike after the common damageability and resistance
  gates. The directed wind-cone path de-duplicates actors for the current spell
  pass and skips common empty/status-masked records. Its
  Sleep/Poison Wind/Death Wind/Flame Wind branches also do not perform the
  friend/foe lookup or reject same-faction actors. Combat field
  casting maps Fire/Poison/Sleep/Energy to combat field-kind bytes
  `0x35`/`0x33`/`0x34`/`0x36`, then delegates the field kind and active target
  slot to the arena-field helper rather than the dungeon byte writer. Player
  combat C-Cast uses the arena cursor followed by the ordinary
  projectile/impact resolver, not an adjacent direction prompt. Cursor moves
  outside the eleven-by-eleven arena or beyond range are ignored; Escape
  cancels after charge and mana debit but before spell sound, coordinate
  lookup, impact resolution, or marker placement. The helper splits placement
  from field-contact/application work. Placement uses active-object field
  markers in the temporary combat table once impact resolution confirms an
  in-arena cell. The coordinate lookup scans slots low-to-high for the first
  selected-coordinate descriptor with `0x80` or `0x40` set, without `0x20` or
  `0x04`, and without linked active-object tile byte `0xF4`; that lookup
  reports the immediate hit/contact target and does not gate marker
  materialization. Fire, Poison, Sleep, and Energy have no extra random
  placement gate. Contact runs from the common post-dispatch hook for the
  current actor descriptor. That same actor is the effect target; the scan
  skips only its linked renderer record while looking for a separate colocated
  marker. The rule is shared by player and AI dispatch and applies without
  consuming the matched marker. Poison Field skips linked
  active-object classes `>= 0x80`; accepted party targets are poisoned only if
  currently Good, while monsters and already non-Good party targets fall
  through to poison damage with no field-contact XP credit. Sleep Field skips
  dead party members, otherwise writing party sleep status or the non-party
  combat sleep/disabled bit without seeding a sleep countdown. An accepted
  Good-party Poison result consumes no random value; its damage fallback rolls
  raw `0..20` with no defense draw. Fire Field rolls raw `0..10` with no defense
  draw. Energy Field blocks movement and has no contact-result arm.
  The traced placement/contact/redraw path, generic active-object tick, and
  monster death/record-clear path show no field countdown/decrement or
  pre-exit removal; placed field markers persist until combat exit restores
  the pre-combat active-object table.

- `CX` / Kill checks protected-target eligibility only after the shared cast
  dispatcher has spent one premixed charge and seven MP and after target
  confirmation has run Kill's normal audiovisual pre-effect. Classes 14
  (Blackthorn), 15 (Lord British), and 47 (Shadow Lord) fail before the shared
  resistance call, so this branch advances no gameplay PRNG and shows no
  target-death animation or target-cell effect. It prints `Failed!` plus a
  newline and plays the shared fifty-step speaker failure glissando. The cast
  consumes the combat action and completes without re-opening either the
  creature cursor or the same actor's command prompt. The pre-effect's separate
  speaker jitter is presentation state, not the gameplay PRNG.

- `IMX` / Create Food uses the standard cast gates and resource ordering. On
  an accepted cast it rolls a uniform `1..3` food/provisions delta, adds that
  delta to the shared party food word with the 9999 cap, marks the stats panel
  dirty, and returns through the ordinary success path. It does not roll
  `0..2`, cannot produce a zero-food successful cast in the traced baseline,
  and does not print the numeric grant.

## 7. Sources and Confidence

High-confidence engine-derived data:

- Forty-eight spell tokens, forty-eight recipe masks, forty-eight scene masks,
  circle formula, charge counter semantics, parser acceptance rules, and
  mix/cast gate order. The resident long-incantation phrase table is a separate
  display aid, but it is a dense forty-eight-entry table that agrees one-to-one
  with the spell ids; the compact parser-token table remains the dispatch key.
- Reagent bit order and charge cap.
- Scene mask bit order and scene-byte classification, including the `0xFF`
  combat marker. The dungeon and combat bits were published transposed in
  earlier revisions; see the correction at the end of Section 4.
- Kill's protected-target resource, action, randomness, presentation, and
  prompt envelope, derived from private analysis in
  `u5-decomp/functions/CAST_OVL/`, `u5-decomp/functions/CAST2_OVL/`,
  `u5-decomp/functions/COMBAT_OVL/`, and `u5-decomp/notes/`.

Manual/player-facing data:

- Common labels and broad effect summaries.

Boundary notes:

1. Keep monster special abilities separate from this player spell table.
   Possess, blink/phase, and summon-daemon are class-flag combat-AI branches,
   not forty-eight-entry spell handlers; the v1 baseline class assignments are
   tracked in `catalogs/monster-bestiary.md`.
2. Exact-parity work outside the player spell table is delegated to the owning
   specs: item/equipment consumption to inventory, combat AI state to combat,
   and visual tile labels to the tile catalog. The shared P/Q/C/N active-effect
   counter shape, Negate Time's `T`/10 decrement/expiry path, and combat C-Cast
   adjacent-target interference gate are specified at public semantic depth.

## 8. Cross-References

- `systems/magic.md` - C-Cast and M-Mix command flows.
- `formats/data-ovl.md` - Resident owner of spell metadata.
- `formats/saved-gam.md` - Reagent counters, premixed spell-charge counters,
  and persisted moonstone gate slots.
- `systems/combat.md` - Combat target and actor flow used by combat spells.
