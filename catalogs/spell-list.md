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

The resident long-incantation display phrase table is not a reliable one-to-one
map for the last few spell ids: it has forty-seven entries for forty-eight
parser ids, includes `Frotz` in the high-circle area, and leaves the final
Time/Negate-Time handler without a matching phrase in that table. Treat the
compact token table plus handler behaviour as authoritative for ids 44 through
47. In particular, id 46 is `PRV` / `Vas Rel Por` / Gate Travel, not Codex
Vision or a spell named `Frotz`.

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

## 4. Scene Mask

Each spell also has a one-byte scene allow mask. The cast dispatcher computes a
single scene bit from the active scene byte, then requires that bit to be set
in the spell's mask.

| Bit | Short | Scene class |
|---:|:---:|---|
| `0x01` | D | Dungeon scenes |
| `0x02` | C | Combat |
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

## 5. Spell Table

| ID | Code | Rune-Name | Common Name | C | Recipe | Allowed | Category |
|---:|:---:|---|---|:-:|---|:---:|---|
| 0 | `IL` | In Lor | Light | 1 | Sulfur Ash | D/I/O | utility |
| 1 | `GP` | Grav Por | Magic Missile | 1 | Sulfur Ash + Black Pearl | C | damage; single target, raw roll 1..16 before target defense |
| 2 | `AZ` | An Zu | Awaken | 1 | Ginseng + Garlic | C/D/I/O | healing; wakes the first Sleeping party member found in roster order |
| 3 | `AN` | An Nox | Cure | 1 | Ginseng + Garlic | C/D/I/O | healing; selected-member Poisoned-to-Good status gate |
| 4 | `M` | Mani | Heal | 1 | Ginseng + Spider Silk | C/D/I/O | healing; selected-member HP add from halved 0..60 roll with minimum 1, skips only Dead targets, clamps at maximum HP |
| 5 | `AY` | An Ylem | Vanish | 1 | Garlic + Blood Moss | C/I | utility |
| 6 | `AS` | An Sanct | Open | 2 | Sulfur Ash + Blood Moss | C/D/I/O | utility |
| 7 | `ACX` | An Xen Corp | Repel Undead | 2 | Sulfur Ash + Garlic | C | buff/debuff |
| 8 | `HR` | Rel Hur | Wind Change | 2 | Sulfur Ash + Blood Moss | O | utility |
| 9 | `IW` | In Wis | Locate | 2 | Nightshade | O | utility; prints the shared sextant-style Y-then-X coordinate line |
| 10 | `KX` | Kal Xen | Conjure | 2 | Spider Silk + Mandrake | C | summon; weighted Giant Rat/Giant Spider/Bat/Python placement |
| 11 | `IMX` | In Xen Mani | Create Food | 2 | Ginseng + Garlic + Mandrake | C/D/I/O | utility; adds random 1..3 food/provisions, capped at 9999 |
| 12 | `LV` | Vas Lor | Great Light | 3 | Sulfur Ash + Mandrake | D/I/O | utility |
| 13 | `FV` | Vas Flam | Fireball | 3 | Sulfur Ash + Black Pearl | C | damage; single target, raw roll 1..30 before target defense |
| 14 | `FGI` | In Flam Grav | Fire Field | 3 | Sulfur Ash + Spider Silk + Black Pearl | C/D | field |
| 15 | `GIN` | In Nox Grav | Poison Field | 3 | Spider Silk + Black Pearl + Nightshade | C/D | field |
| 16 | `GIZ` | In Zu Grav | Sleep Field | 3 | Ginseng + Spider Silk + Black Pearl | C/D | field |
| 17 | `IP` | In Por | Blink | 3 | Spider Silk + Blood Moss | C/O | utility |
| 18 | `AG` | An Grav | Dispel Field | 4 | Sulfur Ash + Black Pearl | C/D | field |
| 19 | `IS` | In Sanct | Protection | 4 | Sulfur Ash + Ginseng + Garlic | C/D/I/O | buff/debuff; +3 party defense |
| 20 | `GIS` | In Sanct Grav | Energy Field | 4 | Spider Silk + Black Pearl + Mandrake | C/D | field |
| 21 | `PU` | Uus Por | Up | 4 | Spider Silk + Blood Moss | D | utility |
| 22 | `DP` | Des Por | Down | 4 | Spider Silk + Blood Moss | D | utility |
| 23 | `QW` | Wis Quas | Reveal | 4 | Spider Silk + Nightshade | C | utility |
| 24 | `BIX` | In Bet Xen | Swarm | 5 | Sulfur Ash + Spider Silk + Blood Moss | C | summon; eight random target cells with short placement retries |
| 25 | `AEP` | An Ex Por | Magic Lock | 5 | Sulfur Ash + Garlic + Blood Moss | C/I | utility |
| 26 | `EIP` | In Ex Por | Unlock Magic | 5 | Sulfur Ash + Blood Moss | C/I | utility |
| 27 | `MV` | Vas Mani | Great Heal | 5 | Ginseng + Spider Silk + Mandrake | C/D/I/O | healing; selected-member current HP restore to maximum, refuses Dead targets and the dungeon combat-active substate |
| 28 | `IZ` | In Zu | Sleep | 5 | Ginseng + Spider Silk + Nightshade | C | buff/debuff |
| 29 | `RT` | Rel Tym | Quickness | 5 | Sulfur Ash + Blood Moss + Mandrake | C/D/I/O | buff/debuff; player-dispatch gate |
| 30 | `IPVY` | In Vas Por Ylem | Tremor | 6 | Sulfur Ash + Blood Moss + Mandrake | C | damage |
| 31 | `AQW` | Quas An Wis | Mass Charm | 6 | Nightshade + Mandrake | C | buff/debuff; AI target remap |
| 32 | `AI` | In An | Negate Magic | 6 | Sulfur Ash + Garlic + Mandrake | C/D/I/O | marquee; absorbs combat casts |
| 33 | `AWY` | Wis An Ylem | X-Ray | 6 | Sulfur Ash + Mandrake | I/O | utility |
| 34 | `AEX` | An Xen Ex | Charm | 6 | Spider Silk + Black Pearl + Nightshade | C | buff/debuff |
| 35 | `BRX` | Rel Xen Bet | Polymorph | 6 | Sulfur Ash + Spider Silk + Nightshade + Mandrake | C | buff/debuff |
| 36 | `LS` | Sanct Lor | Invisibility | 7 | Blood Moss + Nightshade + Mandrake | C | buff/debuff |
| 37 | `CX` | Xen Corp | Kill | 7 | Black Pearl + Nightshade | C | damage; single-target instant kill |
| 38 | `IQX` | In Quas Xen | Clone | 7 | Sulfur Ash + Ginseng + Spider Silk + Blood Moss + Mandrake | C | summon |
| 39 | `IQW` | In Quas Wis | Peer | 7 | Nightshade + Mandrake | D/I/O | utility |
| 40 | `HIN` | In Nox Hur | Poison Wind | 7 | Sulfur Ash + Blood Moss + Nightshade | C | damage |
| 41 | `CIQ` | In Quas Corp | Cause Fear | 7 | Garlic + Nightshade + Mandrake | C | buff/debuff |
| 42 | `CIM` | In Mani Corp | Resurrect | 8 | Sulfur Ash + Ginseng + Garlic + Spider Silk + Blood Moss + Mandrake | D/I/O | healing |
| 43 | `CKX` | Kal Xen Corp | Summon | 8 | Garlic + Spider Silk + Blood Moss + Mandrake | C | summon |
| 44 | `CGIV` | In Vas Grav Corp | Death Wind | 8 | Sulfur Ash + Nightshade + Mandrake | C | damage |
| 45 | `FHI` | In Flam Hur | Flame Wind | 8 | Sulfur Ash + Blood Moss + Mandrake | C | damage |
| 46 | `PRV` | Vas Rel Por | Gate Travel | 8 | Sulfur Ash + Black Pearl + Mandrake | D/I/O | marquee |
| 47 | `AT` | An Tym | Negate Time | 8 | Garlic + Blood Moss + Mandrake | C/D/I/O | marquee |

## 6. Notes for Implementers

- The table is ordered by engine spell id, not alphabetically and not by the
  manual's display grouping.
- The long rune-name strings in this catalog are canonical public spell names
  aligned from parser tokens, manual spell names, and handler behaviour. They
  are not a dump of a dense resident phrase table; the resident long-phrase
  table is sparse at the final spell id.
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
- The CAST dispatcher table follows this exact public order. Handler-family
  classification is now known for the major shared cases: `IL`/`LV` write the
  light counter, `GP`/`FV`/`CX` are active-target attack wrappers using the
  combat aiming/projectile path; `GP` rolls 1..16 raw damage, `FV` rolls
  1..30 raw damage, and `CX` uses the shared decimal 99 instant-kill sentinel,
  with non-instant rolls reduced by target defense before damage/status.
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
  The `IS` `P` tag adds 3 to party-member combat defense after equipment
  defense is summed. The `RT` `Q` tag gates player-side combat command
  dispatch with an inclusive 0..1 random roll: zero consumes the ready dispatch
  without input, while one continues normally.
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
  lifetime is bounded by the combat framer's table restore. `CIQ`
  sweeps hostile combat actors and forces each accepted target into the
  critical-HP flee setup; the combat wound-score morale classifier performs the
  actual fleeing-flag write from that state. A separate lower-tier
  summon/tame-style helper repurposes eligible live non-party, non-humanoid
  actors using descriptor bit `0x01`, the same team/control bit used by charm;
  that is a summon activation side effect rather than the `CIQ` fear path and
  not a write to the flee bit `0x02`.
  Conjure selects Giant Rat, Giant Spider, Bat, or Python from a fixed weighted
  animal selector before making up to eight independent `0..10` X/Y random
  arena placement attempts. Swarm walks the eight-cell ring around the caster
  and gives each target cell up to four placement probes, with the first probe
  testing the target cell itself. Clone duplicates an accepted creature into
  paired free combat actor and dynamic-object slots, and Summon uses the
  self-checking per-tile placement helper to create a Daemon-class combat actor
  at the first accepted cell from up to eight independent random arena-coordinate
  probes. It does not use the direction prompt, an adjacent cached target
  coordinate, or an ordered eight-cell ring. A
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
  placement gate. Contact is bounded to
  the post-step effect hook that runs after a
  successful step-or-attack commits its new coordinate, then matches marker
  coordinates against that actor. The contact scan skips the current active
  actor slot but does not run the creature-prompt friend/foe lookup, and it
  applies without consuming the matched marker. Poison Field skips linked
  active-object classes `>= 0x80`; accepted party targets are poisoned only if
  currently Good, while monsters and already non-Good party targets fall
  through to poison damage with no field-contact XP credit. Sleep Field skips
  dead party members, otherwise writing party sleep status or the non-party
  combat sleep/disabled bit without seeding a sleep countdown. Fire Field rolls raw damage in `[1, 21]` before
  the target's random defense subtraction. Energy Field supplies raw zero to
  the same damage/value path.
  The traced placement/contact/redraw path, generic active-object tick, and
  monster death/record-clear path show no field countdown/decrement or
  pre-exit removal; placed field markers persist until combat exit restores
  the pre-combat active-object table.

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
  forty-seven-entry display aid, not the authoritative spell-id table.
- Reagent bit order and charge cap.
- Scene mask bit order and scene-byte classification, including the `0xFF`
  combat marker.

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
