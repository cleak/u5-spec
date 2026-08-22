# Magic

## 1. Overview

Ultima V has the richest magic system of the early Ultima series. The player can cast forty-eight distinct spells, organised into eight ascending circles of six spells each. Every spell is named by a short sequence of one to four runic syllables drawn from a fixed twenty-four-syllable vocabulary; every spell's effect requires a specific recipe of one or more of the eight reagents to be combined ahead of time into a "charge" that the cast itself consumes. A spell's circle determines its mana cost (a circle-N spell costs N magic points), the minimum experience level required to cast it, and roughly its power.

Magic is therefore a chain of three preparations and one act:

1. **Buy or find reagents.** The eight reagents are sold by herbalists in towns, can be picked up from despoiled enemies, or grown in certain locations. Each is an item the player carries in inventory in a per-reagent counter.
2. **Mix reagents into spell charges.** The `M` command opens a per-spell mixing prompt. The player picks a spell, selects reagents, and chooses a quantity. The engine debits the selected reagents; it increments the per-spell charge counter only if the selected reagent mask exactly matches the spell's recipe.
3. **Have a mixed charge, enough mana, and enough experience level.** The active caster must be alive and awake, must have at least N mana points where N is the spell's circle, and must be at least level N. Once the scene accepts the spell and a charge exists, the charge is spent before mana and level are checked. Low mana loses the charge only; low level loses both charge and mana.
4. **Cast.** The `C` command opens the cast pipeline. The player types the spell's rune-name in compact selector-letter form; the engine parses it against a forty-eight-entry table, runs the context, charge, mana, and level gates, then dispatches to the spell's effect handler.

This spec describes the reagents, the rune vocabulary, the eight circles and their forty-eight spells, the cast and mix command flows, the prerequisite gates, the effect categories, the differences between casting in the overworld and casting in combat, and the narrow linkage between magic and the virtue-shrine stat rewards that can raise the Avatar's intelligence.

## 2. The eight reagents

Every spell recipe is built from some subset of eight reagents. The reagents are carried in inventory, displayed in a fixed order on the M-Mix screen and on the Z-stats reagent panel, and have both a long display name and a short abbreviation:

| Reagent      | Abbreviation | Common source                                |
|--------------|--------------|----------------------------------------------|
| Sulfur Ash   | `Sulfur Ash` | Britain, Skara Brae herbalists                |
| Ginseng      | `Ginseng`    | Cove, Yew herbalists                          |
| Garlic       | `Garlic`     | Most large-town herbalists                    |
| Spider Silk  | `Sp. Silk`   | Specialist shops, occasional drops            |
| Blood Moss   | `Blood Moss` | Swamp regions, certain herbalists             |
| Black Pearl  | `Blk. Pearl` | Coastal-town shops, certain dungeon drops     |
| Nightshade   | `Nightshade` | Rare; specific midnight outdoor Search points |
| Mandrake Root| `Mandrake`   | Rare; specific midnight outdoor Search points |

The order is canonical: every per-spell recipe is implicitly indexed against the same eight slots. The shorter abbreviations are used in tight UI lines (the M-Mix prompt, combat narration); the long forms are used on the dedicated reagent inventory panel.

The reagent inventory is part of the persistent save image. Each reagent is a
single byte counter. Mixing floors selected reagent counters at zero by
validating the requested quantity before subtraction; purchases and gifts
increase the same counters through their owning inventory/shop paths. Do not
infer a global `255` gameplay cap from the one-byte storage width.

There is no on-the-fly cast that consumes raw reagents. Reagents are only ever consumed by the M-Mix command, never by the C-Cast command. The two are decoupled: mix once now, cast later. This means a player can stockpile pre-mixed charges of every spell from a single shopping trip and not need reagents at all on the road, and conversely it means a player who runs out of pre-mixed charges of a critical spell cannot cast it even with full reagents in inventory until they sit down and mix.

## 3. The rune-syllable vocabulary

Every spell's name is a phrase built from one to four syllables drawn from a fixed twenty-four-syllable vocabulary. Each syllable, individually, is a tiny semantic unit; their combinations spell out the effect. The vocabulary is the canonical Britannian magic alphabet:

| Syllable | Loose meaning                |
|----------|------------------------------|
| An       | negate, dispel               |
| Bet      | small, lesser                 |
| Corp     | death, dead                   |
| Des      | down, lower                   |
| Ex       | freedom, release              |
| Flam     | flame, fire                   |
| Grav     | field, energy field           |
| Hur      | wind, weather                 |
| In       | create, make, cause           |
| Kal      | summon, invoke                |
| Lor      | light                         |
| Mani     | life, healing                 |
| Nox      | poison                        |
| Por      | movement, motion              |
| Quas     | illusion, image               |
| Rel      | change                        |
| Sanct    | protection                    |
| Tym      | time                          |
| Uus      | up, raise                     |
| Vas      | great, large                  |
| Wis      | knowledge, sight              |
| Xen      | creature, being               |
| Ylem     | matter, substance             |
| Zu       | sleep                         |

Jux and Ort appear in broader Ultima lore, but they are not resident U5 spell selectors and are not accepted by this prompt.

A spell name is the concatenation of its syllables in order. "Mani" alone is *Heal* (circle 1); "Vas Mani" is *Great Heal* (circle 5; same root, "great" prefix); "In Mani Corp" is the resurrection family; "An Xen Corp" is the repel-undead family. Most U5 spells follow this pattern, with subject-verb-object readable as the chain of runes. A few have conventional names (*Vas Rel Por* — "Great Change Movement" — is the marquee gate-travel teleport).

The rune vocabulary is also used outside the spell system: NPC dialogue mentions runes by name; the Words of Power that disable Stonegate's doors are runic. The syllable table is shared, but the spell-name parser is its own pipeline.

## 4. The eight circles and forty-eight spells

The forty-eight spells are organised into eight circles of six spells each. The circle determines the mana cost (circle-N costs N mana) and the minimum caster level (a level-N character cannot cast circle-(N+1) spells reliably — the level gate accepts the cast and debits mana but fails the effect). Within a circle, spells have similar power but different *kinds* of effect.

The full table:

| Circle | Spell name (runes)        | Common name        | Effect summary                                            |
|:------:|---------------------------|--------------------|-----------------------------------------------------------|
| 1      | In Lor                    | Light               | Set the light-spell counter to 100 units.                   |
| 1      | Grav Por                  | Magic Missile       | Single-target combat attack: roll 1..16, then target defense. |
| 1      | An Zu                     | Awaken              | Wake the first Sleeping party member found in roster order. |
| 1      | An Nox                    | Cure                | Cure Poisoned status on a selected party member.            |
| 1      | Mani                      | Heal                | Restore moderate HP to a party member.                     |
| 1      | An Ylem                   | Vanish              | Remove or vanish an object/effect.                         |
| 2      | An Sanct                  | Open                | Safely open a trapped chest.                               |
| 2      | An Xen Corp               | Repel Undead        | Repel or dispel undead.                                    |
| 2      | Rel Hur                   | Wind Change         | Change the prevailing wind state.                          |
| 2      | In Wis                    | Locate              | Read the caster's current location.                        |
| 2      | Kal Xen                   | Conjure             | Summon an animal.                                          |
| 2      | In Xen Mani               | Create Food         | Create food/rations.                                       |
| 3      | Vas Lor                   | Great Light         | Set the light-spell counter to 255 units.                   |
| 3      | Vas Flam                  | Fireball            | Single-target ranged fire damage: roll 1..30, then target defense. |
| 3      | In Flam Grav              | Fire Field          | Place a burning-tile field at a chosen cell.               |
| 3      | In Nox Grav               | Poison Field        | Place a poison-tile field at a chosen cell.                |
| 3      | In Zu Grav                | Sleep Field         | Place a sleep-tile field at a chosen cell.                 |
| 3      | In Por                    | Blink               | Short teleport to a same-map cell.                         |
| 4      | An Grav                   | Dispel Field        | Remove a placed field at a chosen cell.                    |
| 4      | In Sanct                  | Protection          | Install a `P`/20 timed effect. The defense bonus it was meant to grant is never applied (Section 8). |
| 4      | In Sanct Grav             | Energy Field        | Create an impenetrable field.                              |
| 4      | Uus Por                   | Up                  | Move the party up one dungeon level; at the topmost level, out of the dungeon to Britannia. |
| 4      | Des Por                   | Down                | Move the party down one dungeon level; at the lowest level, out of the dungeon into the Underworld. |
| 4      | Wis Quas                  | Reveal              | Undo invisibility/illusion effects.                        |
| 5      | In Bet Xen                | Swarm               | Summon insects.                                            |
| 5      | An Ex Por                 | Magic Lock          | Apply a magical lock.                                      |
| 5      | In Ex Por                 | Unlock Magic        | Unlock magical locks.                                      |
| 5      | Vas Mani                  | Great Heal          | Strong HP restoration.                                     |
| 5      | In Zu                     | Sleep               | Single-target sleep.                                       |
| 5      | Rel Tym                   | Quickness           | Install a `Q`/30 active effect that randomly gates player-side combat dispatch. |
| 6      | In Vas Por Ylem           | Tremor              | Table-wide damage check against eligible combat actors.    |
| 6      | Quas An Wis               | Mass Charm          | Install a `C`/20 active effect that gates monster target-remap rolls. |
| 6      | In An                     | Negate Magic        | Install an `N`/10 active effect that absorbs combat casts. |
| 6      | Wis An Ylem               | X-Ray               | X-ray / remote-view effect.                                |
| 6      | An Xen Ex                 | Charm               | Charm an enemy.                                            |
| 6      | Rel Xen Bet               | Polymorph           | Transform a target into a Giant Rat.                       |
| 7      | Sanct Lor                 | Invisibility        | Single-target invisibility buff.                           |
| 7      | Xen Corp                  | Kill                | Single-target combat instant-kill attack.                  |
| 7      | In Quas Xen               | Clone               | Clone a person or creature.                                |
| 7      | In Quas Wis               | Peer                | Reveal the map.                                            |
| 7      | In Nox Hur                | Poison Wind         | Area poison-effect with wind-direction shape.              |
| 7      | In Quas Corp              | Cause Fear          | Make targets flee.                                         |
| 8      | In Mani Corp              | Resurrect           | Bring a dead party member back to life.                    |
| 8      | Kal Xen Corp              | Summon              | Summon a daemon.                                           |
| 8      | In Vas Grav Corp          | Death Wind          | High-power death/energy attack.                            |
| 8      | In Flam Hur               | Flame Wind          | Wide-area fire attack.                                     |
| 8      | Vas Rel Por               | Gate Travel         | Long-range teleport via saved Moonstone slot.               |
| 8      | An Tym                    | Negate Time         | Freeze the passage of time for actors.                     |

The parser tokens, public canonical incantations, circles, recipes, and table order are fixed for all forty-eight spell ids. The compact parser-token table is the dispatch key. The resident long-incantation display phrase table has only forty-seven entries and is not a reliable one-to-one id map for the last few high-circle entries; the public spell list is aligned to the parser ids and handler behaviour.

The mana cost for any spell is `(spell_index / 6) + 1` (integer division, zero-based index 0..47). Equivalently, the circle number. Circle 1 costs 1 MP, circle 8 costs 8 MP. There are no half-costs, no cost-reduction items, and no per-class cost adjustments — magic is uniform across casters.

## 5. The C-Cast command

The `C` (Cast) command is the player's gateway to the spell system. It is available from every world mode loop (overworld, town, dungeon) and from combat; the implementation routes through the same dispatcher in all four cases.

**Step 1 — active-player resolve.** The dispatcher first asks "who is casting?" by reading the active-player slot. If no party member is selected, the cast aborts silently. Outside combat, the active-player byte is whatever the player most recently set with the digit keys. Inside combat, the active-player byte is whichever party-slot the round walker is currently dispatching.

**Step 2 — prompt for the spell name.** The dispatcher prints `Spell name:` and a colon-prompt, switches the input pipeline into prompt mode, and reads the spell name. The name is typed as a compact letter-coded form: the player types selector letters for the spell, not the rune syllables in full. Examples: `IL` for *In Lor* (Light — circle 1); `GP` for *Grav Por* (Magic Missile — circle 1); `IPVY` for *In Vas Por Ylem* (Tremor — circle 6); `PRV` for *Vas Rel Por* (Gate Travel — circle 8); and `M` for *Mani* (Heal — circle 1). The forty-eight legal codes are stored in a small token table.

The compact letter-coded form is convenient for fast typing: there are forty-eight legal codes, each one to four letters, and the parser sorts the typed letters before lookup. Order therefore does not matter for the selector itself: `FV` and `VF` both resolve to *Vas Flam*. The echo shown while typing is friendlier than the stored token: each letter prints its associated rune word followed by a space, but that echo is not a long-form input alias. Typing full words such as `VAS FLAM` does not invoke a separate long-form parser; it just feeds selector letters until the four-letter cap or a terminating space/Return is reached.

Return or Space completes the prompt, Backspace erases one selector, and Escape cancels. `J` and `O` are ignored because no rune selector is keyed by those letters. An empty completed buffer returns `None!`; a nonempty selector that does not match any of the forty-eight tokens prints `No effect!`.

**Step 3 — context gate.** Each spell carries a four-bit allow-mask describing which scene-types the spell may be cast in: combat, dungeon, indoor/town-mode, or overworld. The dispatcher reads the current scene byte, computes the matching mask bit, and tests it against the spell's mask. If the spell is not allowed in this scene (for example, a combat-only attack spell outside combat), the dispatcher prints `Not here!` and aborts. Time is *not* consumed on this rejection — the player can change scenes and try again. The complete per-spell scene masks and scene-byte-to-mask mapping are in `catalogs/spell-list.md`.

Two special indoor scene states bypass the normal mask test:

- Lord Blackthorn's Castle absorbs casts while the Crown of Lord British ownership flag is still clear.
- Stonegate absorbs casts unconditionally.

Both cases print `Absorbed!` and abort before charge or mana consumption.

**Step 4 — charges gate.** The dispatcher reads the per-spell charge counter. If the counter is zero, the dispatcher prints `None mixed!` and aborts. Otherwise the counter is decremented immediately, before any further checks — the charge is "spent" the moment the dispatcher commits to the cast.

**Step 5 — mana gate.** The dispatcher reads the active player's current mana points and compares against the spell's mana cost. If insufficient, the dispatcher prints `M.P. too low!` and aborts. The charge has already been spent, but no mana is debited.

**Step 6 — debit mana and check level.** Mana is subtracted from the active player's record, then the dispatcher compares the player's experience level against the same cost. If the level is below the cost, the dispatcher also prints `M.P. too low!` and aborts without refunding mana or the charge. This is a deliberate penalty: a level-3 character attempting a circle-7 spell loses seven points of mana and watches the cast fail.

**Step 7 — dispatch to the effect handler.** The dispatcher computes the spell's index (0..47) into a forty-eight-entry dispatch table and calls the matching handler. Handlers fall into a small set of families described in Section 8.

**Step 8 — narrate the result.** Most handlers print a short success message: `Light!`, `Wind change!`, `Protection!`, `View!`, `Resurrection!`, `Negate magic!`, `Summon Daemon!`. A handful print nothing on success (the projectile spells, the field placements), and Negate Time has a special absorption message when it is blocked by a magic-absorber in the scene. A failure path prints `Failed!`; a success without a spell-specific message prints `Success!`.

The command then returns to the calling mode loop. Time advances by the standard per-mode increment. A spell cast costs one turn regardless of the spell's power.

## 6. The M-Mix command

The world-mode `M` (Mix Reagents) command is the player's tool for converting raw reagents into pre-mixed charges. It is available from the overworld and town mode loops; from a dungeon mode loop the command exists but is rarely useful (the player typically mixes between dungeon expeditions). It is *not* available inside combat: the combat command handler still recognizes the letter `M`, but prints `Mix-Not here` and returns instead of entering the reagent mixer.

**Step 1 — pre-flight check.** The handler verifies the player has at least one of any reagent. With an empty reagent inventory, it prints `No reagents owned!` and aborts.

**Step 2 — pick a spell.** The handler prints `For what spell?` and uses the same compact letter-coded prompt as the C-Cast command. The spell name is parsed against the forty-eight-entry token table, returning the spell index 0..47. Blank input or Escape prints `None!` and aborts before reagent selection. A nonblank selector with no table match returns the shared parser's no-match value, which is distinct from the blank/cancel value; M-Mix does not print C-Cast's `No effect!` at this point, so the player can still enter reagent selection. That no-match value then takes the same path as a wrong recipe in Step 7: if the player chooses a nonzero mix and quantity, the selected reagents are consumed, no charges are added, **and the trap fires**. A mistyped incantation is therefore as expensive as a wrong recipe, not a free cancel.

**Step 3 — select reagents.** The handler shows only the reagent rows whose
inventory counters are nonzero and lets the player toggle a selected set. The
selection cursor moves with the same four directional keys used by compact
menus, Return or Space toggles the highlighted reagent, `M` accepts the current
mask, and Escape cancels before any inventory change. The returned value is an
eight-bit mask in the reagent order documented in `catalogs/spell-list.md`.

**Step 4 — pick a quantity.** The handler prints `How much?` and reads a
two-digit unsigned quantity. Zero cancels through the cleanup path before any
inventory change. Nonzero quantities are validated against every selected
reagent counter. If any selected reagent has less than the requested quantity,
it prints `Insufficient reagents!` and repeats the quantity prompt before any
inventory change.

**Step 5 — reject empty selection.** If the selected reagent mask is zero, the handler prints `Nothing to mix!` and exits through the cleanup path.

**Step 6 — debit selected reagents.** The handler prints `Mixing...`, pauses
briefly, then subtracts the requested quantity from each selected raw reagent
counter. The pause is presentation only: outside combat and dungeon scenes it
runs the animated-tile delay when tile animation is enabled, and elsewhere it
runs a plain timer delay. Neither branch advances the clock.

Mixing costs no game time at all. This matters because almost every other
world action advances the clock, and a port that charges a turn for M-Mix will
drift on NPC schedules, light counters, and timed magic effects.

**Step 7 — recipe match and charge increment.** Only after debiting reagents does the handler compare the selected mask to the spell's recipe mask. If the masks match exactly, it prints the completion message and adds the requested quantity to the per-spell charge counter, then clamps that counter to a maximum of 99. The order is add-then-clamp, so an over-large mix is capped rather than refused; the player still loses the full reagent quantity for charges the cap discards. If the masks do not match, the selected reagents are already spent and no spell charges are added. The wrong-mix branch then emits a line break, refreshes a scratch target slot by scanning the travelling party for the first member whose status is Good or Poisoned, and invokes the shared trap-effect resolver described in `systems/traps.md` with that slot. If the scan finds no Good or Poisoned member, it does not replace the existing scratch slot before the trap-effect call, so the trap lands on whatever party index that scratch slot last held; preserve that stale-slot edge rather than inventing a new fallback, and treat it as undefined behaviour that a port should handle deliberately.

The player-visible cost of a wrong mix is therefore: the reagents are gone, no charges are gained, an explosion sound plays, and one of the four trap effects lands. In non-combat scenes the trap rolls acid damage of one to thirty points on the chosen member with probability three-eighths, poisoning of that member with probability one-quarter, a blast dealing one to eight points to every living member with probability one-quarter, and a gas cloud poisoning the whole party with probability one-eighth. `systems/traps.md` owns the effect families and the combat-scene variant.

The recipe list is fixed in the resident data segment. The full decoded recipe table is in `catalogs/spell-list.md`.

The per-spell charge counters are part of the persistent save image: forty-eight bytes, one per spell. The counters survive saving, loading, dying, and combat. They are consumed only by C-Cast and replenished only by M-Mix; no other path writes to them.

## 7. Casting prerequisites in detail

Combat introduces an additional interference gate that runs *before* the C-Cast command's own checks; outside combat, only the dispatcher's checks apply. The combined gate hierarchy is:

**Combat-only interference gate.** Reached when the player presses `C` inside a combat round. Before the dispatcher even prompts for the spell name, combat asks whether the caster's current target can interfere:

1. **Mapped target.** The per-slot combat target map must contain a target other than the all-ones sentinel.
2. **Target validity.** The target slot must hold a valid live actor and pass the actor-group validity helper.
3. **Target state.** The target must be visible/revealed and awake; targets with the hidden/not-yet-revealed or asleep/disabled bits do not interfere.
4. **Runtime tag.** Negate Time's `T` tag suppresses interference. While that tag is active, this gate returns clear and the cast may continue to the dispatcher.
5. **Adjacency.** The caster and target must be at distance one in the eleven-by-eleven arena coordinate space.

Only when all five conditions pass does the gate block the cast: it prints a newline, the target actor's name, and ` interferes!`, then returns to combat command input before the spell prompt. If any condition fails, the spell dispatcher runs normally. This gate is therefore not a combat-side MP, reagent, level, or spell-allowed check; those resource checks remain in the shared dispatcher below.

**Dispatcher gates** (run after the combat pre-gate, or as the only gate outside combat):

5. **Scene gate** — per-spell allow-mask matches the current scene byte, otherwise `Not here!`.
6. **Charges gate** — `[per-spell charge] > 0`, otherwise `None mixed!`; on success, the charge is decremented immediately.
7. **Mana gate** — `[active-player mana] >= circle`, otherwise `M.P. too low!` (no mana spent, but the charge has already been consumed).
8. **Level gate** — `[active-player level] >= circle`, otherwise `M.P. too low!` (mana and charge are both spent).

The two-stage failure for "M.P. too low!" is a player-visible artefact: a low-mana character loses a premixed charge but no mana, while a low-level character loses both the charge and the mana. The intended message is the same; the underlying penalties differ.

The *order* of the gates matters:

- The scene gate runs before charge consumption, so `Not here!` does not spend a charge.
- The charge counter is decremented before mana and level validation. A failed mana gate does not refund the charge. A failed level gate happens after mana debit and does not refund either resource. Implementations targeting period-faithful behaviour should preserve this asymmetry.

## 8. Spell effects

The forty-eight spell effects fall into seven broad categories. Each handler takes the active-player slot and the dispatcher's per-spell context as input; each returns a success/failure code that the dispatcher uses to print the trailing `Failed!` if appropriate.

**Utility effects.** Light, Open, Vanish, Wind Change, Locate, Create Food, Great Light, Blink, Up, Down, Reveal, Magic Lock, Unlock Magic, X-Ray, and Peer. These are scene-altering or single-step interactions: they place a flag, write a value, redraw a panel, or move the party. *In Lor* writes a 100-unit light-spell duration and *Vas Lor* writes a 255-unit duration; `lighting.md` owns the shared counter decay and visibility consequences. Create Food (*In Xen Mani*) rolls a uniform food/provisions delta in `[1, 3]`, adds it to the shared party food word with the normal 9999 cap, marks the stats panel dirty, and returns through the ordinary success path. Because the lower bound is 1, there is no successful zero-food Create Food cast in the traced baseline. Most utility effects have a short narration message and finish in a single handler call.

**Directed utility tile helpers.** Four utility spells — Vanish (*An Ylem*),
Open (*An Sanct*), Magic Lock (*An Ex Por*) and Unlock Magic (*In Ex Por*) —
share one shape: prompt for a direction, resolve the single cell one step away
in that direction, test that cell's live tile against a fixed set, rewrite it,
and mark the view dirty. They are the reason those four spells carry the combat
bit in their scene masks, and their combat behaviour is described in
Section 9's *Directed utility tile spells in combat*.

The direction prompt is the shared spell direction prompt specified in
`systems/input.md`. Its origin cell depends on scene class: outside combat it is
the party's map cell; **inside combat it is the acting combat actor's arena
cell**. A cardinal choice caches the orthogonally adjacent cell as the target
and echoes the direction name; Space echoes `Pass` and returns the no-direction
branch; any other key re-prompts, and the prompt cannot be escaped except by a
cardinal or Space.

Each helper reports one of three results, and the dispatcher's shared epilogue
turns them into narration: a *handled-silently* result prints neither `Success!`
nor `Failed!` (the helper has already said whatever there is to say), a
*success* result prints `Success!`, and a *no-match* result prints `Failed!`
with the failure sound. Space/Pass always yields the handled-silently result, so
declining the prompt is quiet — but the premixed charge and mana were already
spent by the dispatcher and are **not** refunded.

The cast's audio/visual effect does not wait for the tile test in three of the
four cases. Vanish and Magic Lock play their effect as soon as a direction is
accepted, before the target tile is examined, and Unlock Magic's effect is
played by the dispatcher for any outcome other than Space/Pass. Only Open plays
its effect inside its success branches. So a failed Vanish, Magic Lock or
Unlock Magic still shows and sounds like a cast before printing `Failed!`,
while a failed Open is silent up to the failure line. Space/Pass suppresses the
effect in every case.

- **Vanish.** On a matching cell the helper overwrites the tile with the shared
  cleared-cell tile `0x44` — the same value O-Open writes when it opens a door —
  prints `POOF!`, marks the view dirty, forces a redraw, and plays a sound. It
  returns handled-silently, so `POOF!` is the only line. The removable-object
  tile set is exactly thirteen ids: `0x5B`, `0x90`, `0x91`, `0x92`, `0x93`,
  `0x9D`, `0xA5`, `0xA6`, `0xA8`, `0xA9`, `0xAD`, `0xAE`, `0xAF`. Any other tile
  is a no-match and prints `Failed!`.
- **Open.** Outside dungeon scenes (and therefore in combat, see Section 9) it
  first tests the target tile for the two ordinary *locked* door forms `0xB9`
  and `0xBB` and, on a match, steps each down one rung to its unlocked form
  `0xB8` or `0xBA`, marks the view dirty, plays a sound and returns success. If
  the tile is not a locked door it scans the dynamic-object table for a record
  of object kind 1 — the chest object class — whose stored X and Y equal the
  target cell, and clears that record's lock/trap high bit, which is the high
  bit of the same byte whose low seven bits hold the chest's contents/difficulty
  value. Outside combat the scan also requires the
  object's stored Z to match the party's; in combat-class scenes the Z test is
  skipped, so any matching kind-1 object at that cell qualifies. No match at all
  returns `Failed!`. This second arm is the reason Open has a real effect in
  ordinary combat: the drop a dying monster leaves behind is written into the
  combat-instance object table as exactly a kind-1 chest record whose lock/trap
  bit may be set (`systems/combat.md` Section 6.3), so casting Open at an
  adjacent dropped chest unlocks it for the combat J-Jimmy and S-Search
  commands. The spell only clears the lock/trap bit; it never grants contents,
  and it is not the O-Open command.
  Inside a dungeon scene Open takes a different arm entirely:
  it acts on the party's own dungeon cell when that cell is a door/urn-class
  cell, otherwise on the direction-biased neighbour, prints a disarm line when
  the cell carries the trapped variant bit, rewrites the cell to the opened form
  while preserving its visited marker, prints the chest-opened line and returns
  handled-silently.
- **Magic Lock.** Applies a magic lock to a surface-style door. Both the
  unlocked and the ordinary-locked forms of an orientation collapse onto that
  orientation's magic-locked form: `0xB8` or `0xB9` becomes `0x97`, and `0xBA`
  or `0xBB` becomes `0x98`. Success marks the view dirty and prints `Success!`.
  Any other tile prints `Failed!`.
- **Unlock Magic.** The exact inverse, and the only path that removes a magic
  lock: `0x97` becomes `0xB8` and `0x98` becomes `0xBA`, leaving an ordinary
  *unlocked* closed door that O-Open can then open. Success plays its effect
  sound and prints `Success!`; any other tile prints `Failed!`.

None of the four consumes keys, runs chest or trap handling, arms O-Open's
auto-close tracker, or touches Y-Yell's Word-of-Power dungeon-door path. The
door lock-state ladder itself is owned by `systems/doors-and-z-transitions.md`.

Locate uses the shared sextant-style coordinate printer. It reads the party's
current map coordinates, splits each coordinate byte into high and low nibbles,
maps nibble values 0 through 15 to letters `A` through `P`, and prints the
Y-coordinate first, then a comma and the X-coordinate. Each coordinate is
rendered as high-letter, apostrophe, low-letter; the helper ends the line with
a trailing double-quote character and a newline. This is presentation only: it
does not move the party, consume gems, reveal map cells, or alter the saved
position.

Blink's non-combat path is deterministic and direction-prompted, not a random
teleport. After the normal cast gates spend the premixed charge and mana, the
spell asks for a cardinal direction through the shared spell direction prompt.
Space/Pass produces no movement and no ordinary success/failure narration, but
the charge and mana have already been spent. For a cardinal direction, Blink
builds a straight ray from the adjacent cell in that direction through the
currently loaded 32-by-32 world window. The accepted landing cells are exactly
grass terrain cells, tile id `0x05`; fields, mountains, water, walls, doors,
occupied cells, and all other tile ids are ignored rather than treated as
obstacles. The scan continues after a match, so the party lands on the farthest
grass cell on that ray before the ray exits the loaded window. If the ray
contains no grass cell, the party does not move and the dispatcher prints the
ordinary failure message. No random displacement, retry budget, active-object
occupancy check, vehicle-specific refusal, or generic movement passability
query is part of the non-combat Blink path.

**Healing effects.** Heal, Great Heal, Cure, Awaken, and Resurrect. These read party-member character records, modify HP / status / mana fields, and update the displayed stats. Most healing endpoints accept a target party-member slot, asked separately or supplied by the caller. Awaken is the exception: it scans the party roster in order, changes the first Sleeping member it finds back to Good status, plays the common success effect, marks the stats display dirty, and stops. If no Sleeping member is found, it leaves the roster unchanged and returns failure to the dispatcher. Cure prompts for a party member and succeeds only when that member is Poisoned; on success it changes the member back to Good, plays the same success effect, and marks stats dirty. A non-Poisoned Cure target is left unchanged and fails the effect gate. Resurrection only succeeds on a target whose status is Dead and writes back Good on success.

The ordinary Heal endpoint is a small, selected-member HP recovery helper. It
skips only Dead targets; every other status remains eligible for the HP add, and
the status byte itself is not changed. On success it rolls one random value in
the inclusive range zero through sixty, divides that value by two with integer
truncation, and promotes zero to one. The resulting heal amount is therefore
one through thirty, with one also covering rolls whose halved result is zero.
The helper adds
that amount to current HP, clamps at the member's maximum HP, marks the stats
display dirty, and returns success to the dispatcher. A member already at
maximum HP still follows the successful helper path; the clamp simply leaves
current HP unchanged. Great Heal is a separate selected-member path: it refuses
Dead targets and also fails during the dungeon combat-active substate. On
accepted targets it restores current HP to maximum instead of using the small
random Heal delta.

Resurrection is a record-rebuild helper, not just a status toggle. A successful
spell resurrection changes the selected dead member to Good, sets current HP to
1, rebuilds mana from Intelligence and class, may apply the resurrection
experience adjustment described below, recomputes level from the resulting
experience, and sets maximum HP to thirty times that recomputed level. Avatar,
Mage, and the default class branch receive mana equal to Intelligence; Bard
receives half Intelligence. The helper treats only Dead as a valid target:
Ashes and all other non-Dead statuses fail the dead-status gate. Some callers
use a verbose mode that prints the `Not dead!` refusal for a non-Dead target;
the ordinary spell/scroll path records a failed result and lets the dispatcher
own the trailing failure narration.

The resurrection experience adjustment is conditional on the shared
moral-standing selector described in `systems/karma.md`. When that selector is
below 98, the helper rescales the target's experience by multiplying by 100 and
dividing by the selector before recomputing level. When the selector is 98 or
greater, no experience rescale is applied. The level recomputation is
the standard halving ladder over `experience / 100`: start at level 1, halve the
quotient until it reaches zero, and increment the level once for each halving
step. Compatibility implementations should preserve the current-HP result of
the spell path: the resurrected member stands up with 1 HP, even though healer
shops may immediately top the same member back up after invoking this helper.

**Buff and debuff effects.** Repel Undead, Protection, Sleep, Quickness,
Mass Charm, Negate Magic, Charm, Polymorph, Invisibility, and Cause Fear.
These either mutate combat actor state directly or occupy the single shared
timed-effect slot described next.

**The shared timed-effect slot.** Ultima V has exactly one global timed
magic-effect slot, not a bank of per-spell timers. The slot is a pair of
values: an effect code naming the currently active effect (with a reserved
"none" value), and a remaining duration counted in world turns, with a second
reserved value meaning "permanent, never ages". Every timed magic effect in the
game writes that same pair — the four timed buff spells, Negate Time, three of
the spell scrolls, and the three worn regalia items. Three consequences follow,
and all three must be reproduced:

- **Effects never stack.** Installing a new effect overwrites whatever was in
  the slot. Casting Quickness while Negate Magic is running simply replaces it,
  and donning a permanent-aura item silently cancels an active buff.
- **Exactly one effect code is active and visible at a time.** The installer
  refreshes the stats panel, which displays that code.
- **Nothing but the expiry tick reads the remaining duration.** A
  reimplementation may store the countdown however it likes, as long as the
  observable turn counts match.

The confirmed codes and durations are:

| Source | Code | Duration in turns | Sound cue on install |
|---|:---:|---|---|
| *In Sanct* — Protection (spell) | `P` | 20 | yes |
| *Rel Tym* — Quickness (spell) | `Q` | 30 | yes |
| *Quas An Wis* — Mass Charm (spell) | `C` | 20 | yes |
| *In An* — Negate Magic (spell) | `N` | 10 | yes |
| *An Tym* — Negate Time (spell) | `T` | 10 | none |
| Protection scroll | `P` | 100 | yes |
| Negate Magic scroll | `N` | 20 | yes |
| Negate Time scroll | `T` | 20 | yes |
| Amulet of Lord British (U-Use) | its own reserved code | permanent | yes |
| Crown of Lord British (U-Use) | its own reserved code | permanent | yes |
| Black Badge (U-Use) | its own reserved code | permanent | none |

**Aging.** The countdown has an exact rule: the "none" value and the permanent
sentinel are both inert, any other value decrements by one when an aging
endpoint is reached, and expiry clears the effect code and requests a stats
redraw. In effect the countdown loses exactly one unit per world turn. The
traced endpoints are the per-turn cleanup that follows command dispatch outside
combat and the combat active-player/selection cleanup path — not the
clock/light cleanup.
The Search/Jimmy/Open/Get mode loop carries its own behaviourally identical
copy of the same tick for its own turns; that is a separate routine that
behaves the same way rather than a shared one, so a port needs only one
implementation of the rule. Do not model these units as one decrement per game
minute, one light-counter unit, or one complete combat actor-table pass. Do not
conflate this runtime code/counter with the carried equipment/use-item counter
band used by inventory, R-Ready, and some combat/spell helper paths; those item
counters are inventory stock, not effect timers.

**Clear sites.** Three paths zero the whole slot outright, which also cancels
the otherwise permanent regalia auras:

- H-Hole up (camp or rest) clears it before the camp sequence begins; see
  `systems/rest-and-camp.md`.
- Entering the innkeeper's service menu clears it; see `systems/shops.md`.
- The Blackthorn rescue/refuge restoration clears it, together with both light
  counters; see `systems/blackthorn.md`.

**What each code does.** The complete set of consumers is:

- **`Q` Quickness.** Outside combat, the per-turn cleanup halves the
  game-minute increment for the turn, with a floor of one minute, so the clock,
  NPC schedules, and both light counters all advance at half rate. Inside
  combat, each actor's turn is additionally subject to a coin flip, so enemies
  act about half as often. On the player side the same tag gates ready
  dispatch: each dispatch rolls an inclusive 0..1 value, and a zero consumes
  that ready dispatch without reading a command while a one continues through
  the normal command/status path.
- **`T` Negate Time.** The per-turn cleanup skips the entire time advance, so
  the clock is frozen and neither torches nor light spells burn down. In combat
  the affected actor's turn is skipped outright.
- **`N` Negate Magic.** The enemy-cast gate returns "no spell", and the combat
  C-Cast path absorbs casts before the shared cast dispatcher runs, so the
  premixed charge and MP debit gates are not reached.
- **`C` Mass Charm.** Consumed by monster AI target selection: each target pick
  rolls one uniform random byte in `[0, 255]` against the acting monster's
  class charm threshold. Rolls strictly greater than that threshold remap the
  acting monster to neutral group 0 before the friend/foe filter, making
  targets outside the monster's normal hostile set eligible for that AI
  decision. The player-visible result is a confused actor re-picking whom it
  attacks.
- **Crown of Lord British.** Shares the enemy-cast gate with `N`: while the
  Crown occupies the slot it acts as a permanent Negate Magic aura.
- **Amulet of Lord British.** Read by the overworld loop's void-tile handler,
  which forces the effective lighting threshold to zero on that tile unless the
  Amulet's code is in the slot. The Amulet is what lets the party keep any
  lighting at all in the void: with it, the lighting value stays at whatever the
  clock and scene produce; without it, the value is forced to zero every loop
  iteration, which is the total-blackout state of `systems/lighting.md`
  Section 7.1 rather than an ordinary darkening.
- **Black Badge.** Read only by the conversation system's non-NPC guard
  handler, where it is the disguise that unlocks the Blackthorn palace-gate
  password exchange; see `systems/blackthorn.md`.
- **`P` Protection.** No consumer with any effect — see immediately below.

**Protection has no mechanical consequence in the original game.** The only
place in the game that tests for the `P` value sits inside the party arm of the
combat defence-value computation, where it would have added a small bonus to a
summed defence total. That computation is dead twice over. Its per-item defence
accumulations are each guarded by a comparison that is tautologically true, so
none of them ever runs — the intended test was "this equipment slot does not
hold the not-equipped sentinel", and the shipped test always passes instead.
And the computed value is never consumed: one caller discards it outright, and
the other is reachable only through an attribute-selector arm that no call site
in the game ever selects. Protection and the Protection scroll therefore spend
a charge, play their sound, print their message, occupy the timed-effect slot
for 20 or 100 turns, and show `P` on the stat panel, while changing no combat
number at all. This is an original-game defect rather than a gap in the
analysis; a faithful reimplementation has to decide deliberately whether to
ship the bug or grant the intended bonus. Note the scope carefully: what is
established is that this particular per-item defence contribution is
unreachable and that its total is never read. It is *not* established that worn
equipment is irrelevant to combat generally — the surviving to-hit computation
reads other character-record fields whose relationship to equipment has not
been traced. See `systems/combat.md`.

Polymorph removes the accepted
creature target and places a class 20 Giant Rat at the target's same combat
coordinates.
Invisibility carries no timer of any kind and never touches the shared slot. It
is active-caster only: it marks the current combat actor hidden/phase-shifted,
updates the parallel visual actor state for that same slot, and sets a flag in
that actor's combat-effect descriptor. It lasts until that flag is cleared, so
any turn count a port assigns to Invisibility is invented.
Cause Fear is not a single-target prompt; it sweeps all thirty-two combat slots
and, for every monster-side actor that is not one of the three protected special
classes (14 Blackthorn, 15 Lord British, 47 Shadow Lord) and that fails the
shared resistance check, drives that actor's combat HP counter to one and sets
its fleeing flag directly. The monster wound-score morale classifier then keeps
re-asserting the flag from that critical-HP state on later turns.

**Direct damage and wind attacks.** Magic Missile, Fireball, Tremor, Kill, Poison Wind, Death Wind, and Flame Wind. Magic Missile, Fireball, and Kill are active-target attack wrappers: the spell prints the shared aiming prompt, uses the combat aiming/projectile path, and on an actor collision calls the combat spell-damage wrapper with the caster slot, target slot, and active spell tag. The projectile portion is presentation-only state: it builds and walks a temporary path, renders per-cell visual effects, and leaves no active-object slot or persistent projectile record behind. Magic Missile rolls raw damage in `[1, 16]`; Fireball rolls raw damage in `[1, 30]`; Kill uses the shared decimal `99` instant-kill sentinel. Magic Missile and Fireball then subtract a random defense roll from the target's applicable combat defense value; if the subtraction drives damage negative, the normal miss/no-damage path is used. Kill bypasses that defense subtraction by using the instant-kill sentinel. Tremor is a table-wide combat scan, not a directional spell: it walks every combat actor slot, skips empty or non-damageable records, applies the shared resistance/random gate, rolls 1..20 damage for each accepted actor, and calls the combat damage/status handler with that roll and actor slot. If that handler returns a raw monster-kill reward unit, Tremor adds it to the caster's experience word with the normal 9999 cap. Tremor does not run the friend/foe lookup; party actors and monsters are both eligible if they pass the common gates. Poison Wind, Death Wind, and Flame Wind share the directed wind-cone family described below. Poison Wind runs a per-target resistance/random gate and then routes accepted targets to the poison-status helper. Death Wind passes the decimal `99` instant-kill sentinel into the shared combat damage/status path. Flame Wind rolls raw damage in `[1, 30]` before the same damage/status path. Death Wind and Flame Wind add returned monster-kill reward units to the caster's experience with the normal 9999 cap. The shared directed scan and these per-effect branches do not run the friend/foe lookup or skip same-faction actors.

**Directed wind-cone geometry.** In Zu, In Nox Hur, In Vas Grav Corp, and In Flam Hur use the same combat cone enumerator. The spell prompts for a cardinal direction with the shared `Direction-` prompt; it does not open the arena cursor and it does not choose an arbitrary target cell. Starting from the cell adjacent to the caster in the chosen direction, the enumerator builds a widening forward cone and clips it to the eleven-by-eleven arena.

For a caster at `(cx, cy)`, the un-capped selected cells are:

| Direction | Selected cells before clipping |
|---|---|
| West | For each `d = 1..cx`, column `cx - d`, rows `cy - d .. cy + d`. |
| East | For each `d = 1..10 - cx`, column `cx + d`, rows `cy - d .. cy + d`. |
| North | For each `d = 1..cy`, row `cy - d`, columns `cx - d .. cx + d`. |
| South | For each `d = 1..10 - cy`, row `cy + d`, columns `cx - d .. cx + d`. |

Every row or column span is clipped to arena coordinates `0..10`. The caster's own cell is not part of the normal cone because enumeration starts one cell forward. The first band is three cells wide, the next band five cells wide, then seven, and so on until the arena edge or the output cap is reached. Example: from `(5,5)` west, the cone covers `x=4, y=4..6`; `x=3, y=3..7`; `x=2, y=2..8`; `x=1, y=1..9`; and `x=0, y=0..10`, for 35 cells.

The original raster path has twenty-one pixel lanes and a 63-coordinate output buffer. Cones whose clipped mathematical shape would exceed 63 cells stop after the first 63 de-duplicated coordinates emitted by that raster. The lane stepping uses the combat PRNG only to slice work into short bursts; for cones that fit within 63 cells the affected cell set is the clipped cone above, independent of burst order. For over-cap cones, only the tail beyond the first 63 raster-emitted cells is unstable, so clean engines may either reproduce the lane-raster order for presentation parity or use the clipped cone with a deterministic 63-cell cap as a compatibility simplification.

After the cone is built, the application layer scans combat actors whose arena coordinates match selected cells. It skips empty actors, actors masked by disqualifying status flags, and actors already processed by this same spell pass. It marks each considered actor with a temporary processed bit, so overlapping target cells cannot apply the same spell twice to one actor, and clears that bit across the actor table before returning. Neither the common wind-cone layer nor the per-effect branches run the friend/foe faction lookup used by creature prompts and monster AI. Same-faction actors are eligible if their cells are in the cone and they pass the non-faction gates. In Zu applies the sleep-status branch, In Nox Hur applies a resistance/random gate before the poison-status branch, In Vas Grav Corp uses the decimal `99` instant-kill sentinel through the shared damage/status path, and In Flam Hur rolls raw `[1, 30]` damage through that same damage/status path.

**Field placement.** Fire Field, Poison Field, Sleep Field, and Energy Field share a dungeon-map placement helper. In dungeon scenes, the spell selects a direction/target cell, accepts only an open passage byte in the live dungeon image (`0x00`) or the same passage with the visit marker bit set (`0x08`), and overwrites that live cell with the matching field byte while preserving bit `0x08`. The spell-to-byte mapping is:

| Spell | Base field byte | Marker-preserving byte |
|---|---:|---:|
| Fire Field (*In Flam Grav*) | `0x82` | `0x8A` |
| Poison Field (*In Nox Grav*) | `0x81` | `0x89` |
| Sleep Field (*In Zu Grav*) | `0x80` | `0x88` |
| Energy Field (*In Sanct Grav*) | `0x83` | `0x8B` |

These are visit-local mutations to the loaded map image, not writes to `DUNGEON.DAT`. If the selected dungeon cell is anything other than `0x00` or `0x08`, the helper fails and leaves the live map unchanged. The same four spells dispatch through one shared field helper with a field-kind argument; in combat/non-dungeon scenes that helper uses a separate field-kind table before entering the arena helper:

| Spell | Combat field-kind byte |
|---|---:|
| Fire Field (*In Flam Grav*) | `0x35` |
| Poison Field (*In Nox Grav*) | `0x33` |
| Sleep Field (*In Zu Grav*) | `0x34` |
| Energy Field (*In Sanct Grav*) | `0x36` |

The arena helper receives the field kind and active target slot instead of
writing dungeon terrain directly. It splits marker placement from later
field-contact/application work. Combat placement is not governed by the
dungeon byte-placement helper, and there is no Fire/Sleep/Energy random
acceptance gate for marker materialization.

For player combat C-Cast, these four field spells are not adjacent-direction
spells. The CAST field helper maps the spell to its combat field-kind byte and
then enters the standard combat arena cursor / impact path. The cursor starts
from the caster's current hinted target when that target is still valid and in
range; otherwise it starts on the caster's arena cell. The player moves the
cursor within the eleven-by-eleven arena. Movement that would leave the arena
or exceed the spell's range is ignored rather than clipped or wrapped, and the
cursor stage does not reject blocked terrain, occupied cells, or empty cells.
Escape cancels the targeting after the C-Cast charge and mana have already been
spent, but before the spell sound, coordinate lookup, projectile/impact
resolution, or marker placement.

After a cursor confirmation, the shared combat spell path plays the spell
sound, records the selected cursor cell, and resolves the actual impact through
the ordinary combat projectile/geometry helper. Marker materialization requires
that this resolver confirm an impact cell. Once it does, the field-kind switch
places the matching temporary active-object marker for Fire, Poison, Sleep, or
Energy at that impact coordinate. The helper also looks up the first combat
descriptor at the impact coordinate whose descriptor has either live/selectable
bit (`0x80` or `0x40`) set, has neither the marked-dead bit (`0x20`) nor the
hidden/not-yet-revealed bit (`0x04`) set, and whose linked renderer
active-object record does not have tile byte `0xF4`; that lookup controls the
returned hit/contact target and narration path, not whether the field marker is
placed. Actor contact with arena fields is handled later by the post-step
effect hook in `combat.md`: it runs only after a step-or-attack succeeds and
commits the actor's new coordinate.

Arena field contact resolves the actor at the field coordinate, skips contact if that actor is the current active actor slot, and otherwise proceeds without the creature-prompt friend/foe lookup. Combat fields are materialized as active-object markers in the temporary combat table; the post-action hook later matches those marker coordinates against the actor's committed coordinate before applying the field result. Contact is non-consuming: the hook applies the mapped field result without clearing, aging, or rewriting the matched marker record. Poison Field contact has one extra hook-level gate: if the actor's linked active-object tile/class byte is `>= 0x80`, the poison result is skipped. Otherwise the poison helper sets party-member status to poisoned only when the target character is currently Good; monsters and already non-Good party targets fall through to the normal damage/status path with a 1..20-style poison damage roll. Field contact passes no caster-credit slot to that helper, so this fallback damage does not credit experience through the poison path. Sleep Field contact skips dead party members; otherwise it sets party-member status to asleep, or for non-party targets sets descriptor byte 2 bit `0x08` as the combat sleep/disabled flag and steadies the linked renderer animation. It does not seed a separate combat sleep duration counter; non-party wake timing is the own-turn random wake check described in `systems/combat.md`. Fire Field contact enters the normal combat damage/value path with a raw roll in `[1, 21]`, then subtracts the target's normal random defense roll before damage/status application. Energy Field uses the same damage/value path with a raw zero value, so it produces no positive damage through that endpoint. Field markers are placed in the temporary active-object table without a paired combat-effect descriptor, so the monster death/record-clear path does not age or remove them. The traced CAST/COMSUBS/COMBAT paths, the accepted-placement resident redraw helper, the post-action contact hook, and the generic active-object tick expose no field countdown, decrement, or pre-exit removal step. A placed combat field persists until combat exits, when the combat framer restores the pre-combat active-object table.

Dispel Field uses a separate removal helper rather than the four-spell
placement helper above. In dungeon scenes, it checks the cell in front of the
party using the party's facing direction and the current dungeon layer. If that
live cell is in the field family, the spell rewrites the live cell to preserve
only the visit-marker bit, prints the field-destroyed success message, and
returns success. This is a visit-local map-image mutation; it does not rewrite
`DUNGEON.DAT`. In combat/non-dungeon spell scenes, it uses the shared direction
prompt, scans the active-object field-marker family for a marker at the cached
target coordinate, and removes the matching slot through the common active
object removal helper. No matching field marker leaves the active-object table
unchanged and returns failure/no-effect. Broader Negate Magic is handled by its
own active-effect path and is not a field-removal spell.

**Summoning and conjuration.** Conjure, Swarm, Clone, and Summon use distinct
helper families rather than one shared spell effect.

*The shared random arena probe.* Conjure, Swarm, and Summon all place through
one common probe, and its exact shape matters for compatibility. A single probe
draws a candidate X and a candidate Y **independently and uniformly from the
inclusive range `0..15`** — a four-bit draw, not a draw over the arena's
`0..10` range — and then rejects the whole candidate unless *both* coordinates
are at most 10. A rejected candidate is not re-rolled: it consumes one of the
caller's attempts. The per-probe acceptance chance is therefore `(11/16)^2`,
about 47 percent, before the cell is even inspected. An accepted candidate is
then put to the shared combat spawn-cell validator, which requires terrain that
the placed creature's movement family can occupy, rejects the arena's
impassable void byte, and rejects any cell already holding a combat actor or a
dynamic object. Only a candidate that clears both steps is a legal placement
cell.

*Conjure* plays its summon effect, then rolls **one uniform value in the
inclusive range `0..15` — sixteen outcomes, not fifteen** — and maps it to a
creature class: six outcomes select Giant Rat (class 20), five select Giant
Spider (class 22), three select Bat (class 21), and the remaining **two**
select Python (class 34). It then makes up to eight probes as described above;
the first legal cell receives one actor of the rolled class, with a brief
placement flash before the creature's own tile settles. All-eight failure
reports ordinary spell failure after resource consumption. One quirk is
load-bearing for exact compatibility: the terrain-suitability question is always
asked using the Giant Rat movement family, whichever creature the roll actually
selected.

*Swarm* plays a stronger effect and then searches for **one** cell, not eight.
It makes up to eight probes and stops at the first legal cell; if all eight
probes fail it reports ordinary spell failure. Having found that one cell, it
places up to **four** Insect Swarm actors (class 31) **at that same
coordinate**, stopping early if the actor table runs out of free slots, and
succeeds if at least one actor was placed. There is no caster-centred ring and
no jitter retry; earlier drafts of this spec described both, and both are
withdrawn.

Every actor placed by Conjure or Swarm is stamped with the controlled bit
described in `systems/combat.md` Section 6.1a, so a freshly conjured creature
starts in the same controlled state a charmed monster occupies. Summon stamps
the same bit only when its caster self-check succeeds; the rebound branch
described below leaves the placed Daemon uncontrolled.

That bit is **not** an allegiance flag, and this is the single most important
thing to get right about these spells. All three place their creature through
the ordinary monster placement path, so the new actor's faction byte is the
monster-side one: the friend/foe resolver treats it as hostile, and monster AI
drives its turns exactly as it drives any other monster. Nothing routes a
summoned creature through the player command parser, and the player never gets
to move it. What the controlled bit changes is only the actor's *attack*: when
its turn produces an attack it resolves through the fixed magic-strike branch,
which also requires the chosen target to be adjacent (`systems/combat.md`
Section 6.1a). An earlier answer published against this spec said summoned
creatures take their turn through the player-command path so the player drives
their actions; that is withdrawn.

Repel Undead is not a summoning effect and does not create or repurpose
anything. It sweeps the whole combat actor table and, for each monster-side
actor that is not one of the three protected special classes (14 Blackthorn, 15
Lord British, 47 Shadow Lord), whose class carries the undead class flag, and
that fails the shared resistance check, drives that actor's combat HP counter to one and sets
the **fleeing** bit. That is the same critical-HP flee setup Cause Fear applies,
narrowed to undead classes; it never touches the controlled bit. Earlier drafts
called this a "lower-tier summon/tame-style helper" that set the controlled bit;
that description is withdrawn.

Clone is
target-derived: after the `Creature:` target is accepted, it searches for one
free combat actor slot and one free dynamic-object slot, copies the target's
paired records only after both slots exist, relinks the new combat record to the
new dynamic-object slot, then places the copy at a random legal coordinate in
the eleven-by-eleven arena. If either table has no free slot, Clone writes no
partial record. The original leaves the spell-result word undefined on that
capacity path, so compatibility layers may need to preserve the original's
unpredictable success/failure narration; deterministic engines should model it
as a no-op failure. Clone is not an adjacency-based spell.

Summon uses the per-tile placement/impact helper, not the shrine/urn helper and
not the shared direction prompt. It makes up to eight of the shared random arena
probes described above. It additionally re-tests, on its own, that the
candidate cell's live terrain byte is not the arena's impassable void byte; the
shared spawn-cell validator already rejects that byte, so this duplicate test
can never change an outcome and an implementation may omit it. The
first accepted cell receives a Daemon-class combat actor (class 38), plays the
temporary flame/daemon impact animation, and, on ordinary success, stamps the
placed slot with the controlled bit. There is no cached adjacent target
coordinate, ordered eight-cell ring, or off-arena direction case for this player
spell path.

This spell path uses the helper's self-checking mode after a Daemon has been
placed and animated. The threshold it checks against is a concrete stat: the
**Intelligence** value of the acting caster's character record when the caster
is a party member, or the class row's flip-HP field — the third of the eight
class-stat fields published in `catalogs/monster-bestiary.md` Section 2 — when
the caster is a monster. The party case is the only one a player C-Cast can
reach. The roll it compares is formed the same way the game forms
its other small rolls — a uniform inclusive `0..60` value halved with the
fraction discarded and floored to a minimum of one, giving `1..30`. The `Oops...`
branch fires when `roll >= threshold`, so a caster with Intelligence at or above
31 can never trigger it and a caster with Intelligence 1 always does. That branch
prints `Oops...`, returns the special silent-failure result, does **not** stamp
the placed slot with the controlled bit, and does not print the ordinary
`Success!` or `Failed!` epilogue message. The placed Daemon record is not
suppressed by this branch — a rebounded Summon still leaves a live, *uncontrolled*
Daemon on the arena, which is the point of the rebound.
Summoned or cloned combat actors then run through the standard combat
actor-table machinery. The traced summon, clone, combat tick, and
death/record-clear paths do not expose an independent per-spell duration
countdown; combat-exit lifetime is instead bounded by the combat framer
restoring the pre-combat actor tables.

A previously suspected CAST2 helper remains attributed to shrine/urn kneel
presentation. It prepares temporary active-object records from a private visual
pattern and is not reached as a party C-Cast summon row in the traced caller
census. Do not use that private pattern as the source for Conjure, Swarm, or
Summon placement.

**Special / marquee effects.** Negate Magic, Gate Travel, and Negate Time. These are the fewest-use spells with the largest gameplay impact. Negate Magic installs the shared `N`/10 active-effect tag; combat C-Cast checks that tag and routes to the absorption/refusal path before queueing the normal spell dispatcher. Gate Travel is a keyed moonstone teleport rather than a fixed astronomical moongate table: it requires the party not to be shipboard, prompts `To phase:`, accepts digits `1` through `8`, converts that to a zero-based moonstone slot, and invokes the world-transition helper for that saved slot. Each slot stores the destination's scene, X, Y, and Z/floor values; an invalid scene sentinel makes the helper return failure and the cast does not teleport. Burying a Moonstone records the current valid location into that slot when outside dungeon/combat scenes and on accepted world-tile ids `4..10`, `44`, or `45`; later Search/Get recovery invalidates it. Negate Time scans for a magic-absorption sentinel before starting; if one is present it prints `Magic absorbed!` and does not set the effect. Otherwise it writes the shared runtime tag as `T`, writes a countdown value of 10, and redraws. The same nonzero/non-255 aging rule decrements this countdown at command-dispatch cleanup and combat active-player/selection cleanup; when the countdown expires the tag is cleared and stats are marked for redraw. The ordinary per-turn clock cleanup does not age this counter. Instead, while the tag is `T`, that cleanup skips minute advancement, which is the stopped-time effect.

### Handler-family map

The cast dispatcher has one entry per spell id, but many entries are short wrappers around shared helpers. The public spell-order mapping is now known at the handler-family level:

| Handler family | Spells | Public contract now known |
|---|---|---|
| Light counter | In Lor, Vas Lor | Set the shared light-spell counter to 100 or 255, then return through the common cast-success path. |
| Active-target attack wrapper | Grav Por, Vas Flam, Xen Corp | Print the shared aiming prompt, use the combat aiming/projectile path, and on actor collision call the shared combat spell-damage wrapper. Grav Por rolls 1..16 raw damage, Vas Flam rolls 1..30 raw damage, and Xen Corp passes the decimal 99 instant-kill sentinel. Non-instant rolls subtract target defense before the shared damage/status path. |
| Party/character restore handlers | An Zu, An Nox, Mani, Vas Mani, In Mani Corp | Mutate party-member status/HP records through small helper families. An Zu scans the roster and wakes the first Sleeping member to Good status; it has no selected-member prompt. An Nox prompts for one member and changes only Poisoned targets back to Good. Mani skips only Dead targets, adds a random HP roll formed by halving an inclusive 0..60 roll and flooring zero to one, clamps at maximum HP, and leaves status unchanged. Vas Mani refuses Dead targets, fails during the dungeon combat-active substate, and otherwise restores current HP to maximum. Resurrection additionally requires Dead status, rejects Ashes and other non-Dead statuses, changes status to Good, sets current HP to 1 on the spell path, rebuilds mana from class and Intelligence, conditionally rescales experience, recomputes level from experience, and sets maximum HP to thirty times the recomputed level. |
| Shared field helper | In Flam Grav, In Nox Grav, In Zu Grav, In Sanct Grav | Pass a field-kind argument into one placement helper. Dungeon placement bytes and no-write failure are exact above. Combat dispatch maps Fire/Poison/Sleep/Energy to field-kind bytes `0x35`/`0x33`/`0x34`/`0x36`, then delegates the field kind plus active target slot to the arena-field helper. Player combat C-Cast uses the arena cursor followed by the ordinary projectile/impact resolver, not an adjacent direction prompt. Cursor moves outside the eleven-by-eleven arena or beyond range are ignored, Escape cancels after charge/mana debit but before marker placement, and the cursor does not reject empty or occupied cells. Combat marker placement requires a confirmed impact cell, but no Fire/Sleep/Energy random acceptance gate exists for marker materialization. The helper places the matching temporary active-object field marker, then separately reports a hit/contact target from the first selected-coordinate descriptor with `0x80` or `0x40` set, without `0x20` or `0x04`, and without linked active-object tile byte `0xF4`. Arena contact skips the current active actor but does not run the friend/foe lookup, and contact does not consume the marker. Poison Field skips linked active-object classes `>= 0x80`; for accepted targets it poisons Good party members and otherwise falls through to poison damage with no field-contact XP credit. Sleep Field skips dead party members, otherwise sleeps party targets or marks non-party targets with the combat sleep/disabled bit; it does not seed a separate combat sleep countdown. Fire Field rolls raw 1..21 before defense, and Energy Field supplies raw zero to the same damage/value path. The traced placement/contact/redraw path and generic active-object tick show no field countdown/decrement; placed markers persist until combat exit restores the pre-combat active-object table. |
| Directed utility tile helpers | An Ylem (Vanish), An Sanct (Open), An Ex Por (Magic Lock), In Ex Por (Unlock Magic) | Prompt for a direction, resolve the single adjacent cell, test its live tile against a fixed id set, rewrite it and mark the view dirty. The prompt's origin is the party cell outside combat and the acting combat actor's arena cell inside combat, and the live-tile lookup resolves to the combat-arena terrain grid in combat scenes, so all four genuinely mutate arena terrain. Vanish clears thirteen removable-object tile ids to the shared cleared-cell tile and prints `POOF!`; Open steps a locked door down to its unlocked form or clears the lock/trap bit on a co-located kind-1 chest object — which in combat includes the chest a dying monster drops, making Open's success case reachable in every arena — and takes a separate dungeon-cell arm in dungeon scenes; Magic Lock collapses both door forms of an orientation onto its magic-locked form; Unlock Magic performs the inverse. Space/Pass is silent, a matched tile prints `Success!` (or the helper's own line), and a non-matching tile prints `Failed!`. Section 8 has the exact tile ids. |
| Field removal helper | An Grav | Uses a separate Dispel Field path. Dungeon scenes inspect the faced adjacent live cell and turn recognized field cells back into open/visited-live-cell state while preserving only the visit marker. Combat/non-dungeon spell scenes use the shared direction prompt and remove a matching active-object field marker at the cached target coordinate. Failure leaves the map image or active-object table unchanged. |
| Directional Blink | In Por | Outside combat, prompts for a cardinal direction, scans that ray through the active 32-by-32 loaded world window, and moves the party to the farthest grass tile (`0x05`) found. No random target, retry budget, occupancy check, or generic passability query is used; no matching grass tile reports ordinary spell failure after the shared charge/mana spend. |
| Directed wind-cone effects | In Zu, In Nox Hur, In Vas Grav Corp, In Flam Hur | Prompt for a cardinal direction, build the widening clipped cone described in Section 8, and scan the combat actor table for actors whose arena coordinates match those cells. The normal cone starts one cell forward from the caster, widens by one cell on both sides per forward step, de-duplicates selected cells, and writes up to 63 coordinates. The common application layer skips empty actors, actors masked by disqualifying status flags, and actors already processed by this same spell pass. It marks each considered actor with a temporary processed bit, so overlapping target cells cannot apply the same spell twice to one actor, and clears that bit across the actor table before returning. Neither the common wind-cone layer nor the per-effect branches run the friend/foe faction lookup used by creature prompts and monster AI. Same-faction actors are eligible if their cells are in the directed area and they pass the non-faction gates. In Zu applies the sleep-status branch, In Nox Hur applies a resistance/random gate before the poison-status branch, In Vas Grav Corp uses the decimal `99` instant-kill sentinel through the shared damage/status path, and In Flam Hur rolls raw `[1, 30]` damage through that same damage/status path. The two damage winds credit returned monster-kill reward units to the caster's experience with the 9999 cap. |
| Table-wide tremor damage | In Vas Por Ylem | Scans all thirty-two combat actor slots. For each non-empty slot that passes the generic damageability and resistance/random gates, the spell rolls 1..20 damage and feeds that roll plus the actor slot to the shared combat damage/status handler. The handler applies HP damage, death effects, split checks, and temporary drop markers as usual. Any raw monster-kill reward unit returned by the handler is added to the caster's experience word, capped at 9999. Tremor does not run a faction filter, so friendly-fire is allowed for any party actor that passes the common gates. |
| Active-effect display wrapper | In Sanct, Rel Tym, Quas An Wis, In An | Pass an animation/effect kind, visible tag, and counter to a shared active-effect helper: In Sanct uses `P` / 20, Rel Tym uses `Q` / 30, Quas An Wis uses `C` / 20, and In An uses `N` / 10. The helper stores one global visible tag/counter pair, plays the common animation, and refreshes the stats panel; resident update helpers age the counter until expiry clears the tag. This aging is separate from torch/light-spell cleanup cadence. Confirmed consumers: `P` has no consumer with any mechanical effect (the defence bonus it was meant to grant is never applied — see Section 8), `Q` runs a 0..1 random gate before player-side combat command dispatch, `C` lets monster AI target selection roll a random byte against the acting monster's class charm threshold and remap the monster to neutral group 0 on a strictly greater roll, and `N` absorbs combat casts before the shared dispatcher consumes charge or MP. |
| Creature-prompt targeters | An Xen Ex, Rel Xen Bet, In Quas Xen | Prompt `Creature:`, resolve a creature at the selected cell, reject walls, empty cells, protected/immune classes, and same-faction targets, then apply the spell-specific result: Charm toggles the target's controlled/charmed marker — a second successful Charm on the same actor clears it, and the marker is not an allegiance change (`systems/combat.md` Section 6.1a) — Polymorph replaces the target with a class 20 Giant Rat at the same coordinates, and Clone duplicates the target into paired free actor/dynamic-object slots before placing the copy at a random legal arena coordinate. Clone writes no partial copy if either table is full; the original's capacity-failure result word is undefined. No traced Clone helper installs a separate per-spell duration counter. |
| Active-caster invisibility | Sanct Lor | Applies only to the current actor. It marks that combat actor hidden/phase-shifted and updates the linked visual actor state; no separate creature prompt runs. |
| Table-wide fear sweeps | In Quas Corp, An Xen Corp | Not a prompt-driven target family. Sweeps all thirty-two combat actor slots and accepts every monster-side actor that is not one of the three protected special classes (14 Blackthorn, 15 Lord British, 47 Shadow Lord) and that fails the shared resistance check. For each accepted actor **the spell itself** drives the combat HP counter to one and ORs in the fleeing bit `0x02`. The combat wound-score morale classifier does **not** perform that write; it only keeps re-asserting the flag from the resulting critical-HP state on later turns. Repel Undead (An Xen Corp) runs the identical sweep with one added condition, the undead class-flag bit, and writes the same two values. Neither spell places, re-types, tames, or repurposes an actor, and neither touches the controlled/charmed bit `0x01`. |
| Gate travel | Vas Rel Por | Refuses while the party is shipboard, prompts `To phase:`, accepts a digit `1`..`8`, maps that digit to the corresponding persisted moonstone slot, and teleports only if that slot has a valid saved scene/X/Y/Z destination. Moonstone bury/recovery owns the slot contents; see `formats/saved-gam.md`. |
| Negate Time | An Tym | If a magic-absorption sentinel is active, prints `Magic absorbed!` and fails. Otherwise stores the shared runtime tag `T` with countdown 10 and redraws. Command-dispatch cleanup and combat active-player/selection cleanup age nonzero/non-255 countdowns, clearing the tag on expiry; the clock cleanup only observes `T` to skip minute advancement. |

This closes the dispatcher-level target-family mapping for the major combat spells and several formerly unique high-circle handlers. The common directed-spell layer is also bounded through the per-effect branches: it de-duplicates actors, applies only status/common-scratch prefilters, applies each wind/sleep result without a faction gate, and clears its temporary processed marks before returning. Tremor's table-wide damage/reward path, the active-target attack-wrapper damage path, Protection's inert active-effect tag, Quickness's player-side dispatch gate, Mass Charm's class-threshold target-selection remap, Clone's paired-slot allocation and capacity failure, Negate Magic's combat-cast absorption consumer, and the combat post-step boundary plus active-object marker storage, placement gate, non-consuming contact, status-helper gates, and combat-exit lifetime for arena fields are now bounded separately.

## 9. Casting in combat

The C-Cast command is also bound in the combat command set. The implementation reuses the same dispatcher described in Section 5; the routing mechanism is a single combat-mode entry that validates combat prereqs, then invokes the dispatcher, then validates the result.

**Same dispatcher.** From the dispatcher's point of view, a combat cast is identical to an overworld cast. The same prompt is shown, the same forty-eight-entry table is consulted, the same charge / mana / level gates run. The dispatcher reads the same DS state — including the per-spell charge counters and the per-character mana — so the in-combat cast and the out-of-combat cast are perfectly interchangeable for state purposes.

**Combat-specific interference pre-gate.** Section 7 listed the combat-only
interference gate. It runs before the dispatcher prompts for the spell name; an
interfering adjacent target skips the dispatcher entirely.

**Active player and target.** Outside combat, the active player is whichever character the digit keys most recently selected; the cast applies to or originates from that character. Inside combat, the active player is whichever slot the round walker is currently dispatching — the cast happens on that character's turn and consumes that character's mana. The combat target map used by the interference gate is not a replacement for spell-specific targeting. Several spells still take an explicit target separately from the caster, and active-target combat spells still use their own aiming/targeting path.

**Scene gate selects spells.** The four-bit scene allow-mask uses `0x01` for dungeon scenes, `0x02` for combat-class scenes, `0x04` for indoor/town-mode scenes, and `0x08` for overworld. Spells without the active scene bit are rejected with `Not here!`; for example, combat-only attack spells reject outside combat, while overworld-only utility such as Wind Change rejects inside combat.

**Directed utility tile spells in combat.** Vanish, Open, Magic Lock and Unlock
Magic all carry the combat scene bit, and in combat they run their real handlers
rather than falling through to an unmodelled no-op. An earlier answer published
against this spec claimed the four were silent, prompt-free, always printed
`Failed!`, and could not touch arena state; every part of that is withdrawn.
What actually happens:

- **They prompt.** Each one runs the shared spell direction prompt, and in a
  combat scene the prompt's origin is the *acting combat actor's* arena cell, so
  the target is the cell one orthogonal step from the caster. Space answers the
  prompt with `Pass`, which ends the cast silently; the premixed charge and mana
  are already spent by then and are not refunded.
- **They read and write arena terrain.** The engine's live-tile lookup resolves
  to the combat-arena terrain grid whenever the scene is combat-class, so the
  tile these helpers test and rewrite is the arena's own terrain cell. The write
  marks the view dirty and is visible for the rest of the fight. It is *not*
  persistent: the arena terrain grid is refilled from the arena definition on the
  next combat entry, and the arena files themselves are never written.
- **Matches genuinely exist.** Outdoor combat arenas contain no door tiles at
  all, so in outdoor combat Magic Lock and Unlock Magic can only fail, and Open
  can only reach its object branch. Exactly one shipped outdoor arena carries
  tiles from Vanish's removable-object set. Dungeon-room arenas are different:
  eighteen of them contain door tiles — including magic-locked, ordinary-locked
  and unlocked forms — and seven contain Vanish-family object tiles, so all four
  spells have reachable terrain success cases in dungeon-room combat.
- **Open's object branch is reachable in every arena.** Independently of arena
  terrain, the ordinary monster-death drop writes a kind-1 chest record into the
  combat-instance object table at the dead monster's cell, and that record's
  lock/trap bit is exactly what Open's second arm clears. A cast aimed at an
  adjacent dropped chest therefore succeeds and prints `Success!` wherever the
  fight is happening. The earlier published claim that combat drop markers are
  not Open-eligible is withdrawn.
- **Off-arena targets are undefined and should be treated as failures.** The
  direction prompt does not clamp its result to the arena, and the combat
  live-tile lookup does not bounds-check. A direction that steps off the eleven
  by eleven playfield addresses storage that is not arena terrain at all. A
  clean engine should treat any target outside the arena as a non-matching tile
  and report `Failed!`, rather than reproducing the original's out-of-range
  addressing.
- **Combat Open cannot reach the dungeon chest arm.** The dungeon arm of Open is
  selected only for dungeon-*exploration* scenes; the combat scene class routes
  to the non-dungeon arm even when the fight is a dungeon-room encounter. The
  earlier caveat suggesting combat Open might route through the dungeon trapped
  chest helper is withdrawn.

Section 8's *Directed utility tile helpers* carries the exact tile-id mappings
and result/narration rules; nothing about them changes between scenes except the
prompt origin and which grid the live-tile lookup addresses.

**Monster spell-like effects.** The traced dispatcher contract above is the
player/party C-Cast path. Monster turns use the combat AI path first: a
class-flag special hook may possess a party member, blink/phase the actor, or
summon a Daemon-class actor, then target selection, direction synthesis, and a
synthesized command byte enter the combat command parser. These three monster
branches are outside the forty-eight player spell definitions. They do not
route through the party C-Cast prompt or the forty-eight-entry player spell
dispatcher, and they do not consume the party's reagents, premixed charges, MP,
or circle gates.

**Combat ends with state preserved.** Charge and mana side effects follow the same order inside combat as outside: charge loss and any successful or under-level mana debit survive combat exit and are part of the persistent save. A spell cast inside combat is real and permanent; the framer that brackets combat with save-and-restore preserves the cast's after-effects (just as it preserves damage).

## 10. Linkage to the eight virtue shrines

The eight virtue shrines (Honesty, Compassion, Valor, Justice, Honor, Sacrifice, Spirituality, Humility) are not part of the spell system proper. Their only magic-facing consequence is that some shrine quest turn-ins permanently increase the Avatar's intelligence, which in turn raises the mana cap used by the cast dispatcher.

Meditation and Codex urn reading are driven by the `M` command while standing
on shrine-family special tiles, but they are distinct from reagent mixing. On a
virtue shrine, the engine prompts for the shrine mantra (`Ahm`, `Mu`, `Ra`,
`Beh`, `Cah`, `Summ`, `Om`, or `Lum`) and then branches on the shrine quest
masks described in `systems/karma.md`. On the urn/Codex special tile, the same
command family loads the Codex message cluster and sets the Codex-read bit for
an ordained virtue, also described in `systems/karma.md`.

Gold offerings are not the stat-up path. After a virtue's shrine quest is complete, a valid offering consumes party gold and raises the active shrine standing. The permanent stat rewards happen on the Codex-read turn-in state, when the ordained bit is cleared and the Codex bit remains set. Those rewards write to the Avatar record: Honesty raises intelligence; Justice, Honor, and Spirituality include intelligence among their rewards; the other shrines affect strength and/or dexterity or, for Humility, standing only.

From the magic system's point of view, the shrine system is an external writer of the Avatar intelligence byte. The cast dispatcher only reads the current intelligence-derived mana state; it does not know why the stat changed and it performs no shrine or karma checks of its own.

## 11. Z-stats integration

The Z-stats panel — the dedicated character-sheet command — is the player's view into the magic system's persistent state.

- **Spell book.** A per-character spell-book panel lists the spells the character can attempt to cast, displaying the spell name in runes, the rune-code, the circle, the mana cost, and the recipe. The list is filtered by the character's class and level (Mages and Druids have full access; other classes see a smaller subset). The list does *not* depend on charges — every spell the character is theoretically eligible for shows in the book even if not currently mixed.
- **Reagent panel.** A separate panel shows the current count of each of the eight reagents in the party's shared inventory.
- **Charge counter panel.** A third panel shows the per-spell charge counts, displayed as the spell name plus a small integer. Spells with zero charges are shown but greyed.
- **Stats line.** The character's intelligence stat and current/maximum mana points are shown on the main Z-stats line.

Z-stats is read-only with respect to the magic system: it shows the state but never changes it. The magic system's only requirement is that the dispatcher reads the *current* mana value; any other system can write it.

**There is no time-driven mana regeneration, and rest is not a full mana restore.** The shared party status pass in `systems/time.md` section 5 never writes a magic-point field, and neither ordinary rest, rest-with-watch, nor town-bed sleep contains a magic-point restore block of its own. Outside spell effects and resurrection, the only traced writer reached by resting is the completed long-camp recovery block specified in `systems/rest-and-camp.md` section 5, and it *assigns* rather than adds, and only for specific class rows: Avatar and Mage are set to Intelligence, Bard to half Intelligence rounded down, and every other class row is left untouched. Because the assignment has no cap test, a listed class whose current magic points were already above the target ends the camp with fewer. An earlier revision of this paragraph described the model as "slow regeneration of mana over real game-time, plus full restoration on rest"; both halves are wrong and are withdrawn.

## 12. Persistence

Every piece of persistent magic state is in the save image:

- **Reagent inventory** — eight per-reagent byte counters in the inventory block.
- **Spell charges** — forty-eight per-spell byte counters, one per spell index 0..47.
- **Per-character mana** — one byte per character record, in the stats quartet (STR, DEX, INT, MP).
- **Per-character intelligence** — one byte per character record (drives mana cap).
- **Per-character level** — one byte per character record (gates level-cost).
- **Shrine quest masks** — two bitmasks of eight bits each (ordained and Codex visited), owned by the karma/shrine system but relevant because shrine turn-ins can raise Avatar intelligence.

There is no separate "magic state" file: every byte is part of the standard `.GAM` runtime image, flushed and loaded on save and restore. The same is true of the eight reagent counters and the forty-eight charge counters. There are no file-borne tables that the magic system reads at runtime — every per-spell datum (the rune-code table, the recipe table, the allow-mask) is interned in the resident `DATA.OVL` data segment and copied into RAM at startup.

## 13. Magic Boundaries

The magic contract is complete at player-spell behavioral depth: the
forty-eight-entry player spell table, parser, charge/mana/level gates,
scene masks, handler families, per-effect damage/status math, the single
shared timed-effect slot with its full constant table and consumer census,
field placement and contact lifetime, shrine/urn split, and
save-image ownership are specified.

The question of where per-spell buff durations live is closed and had a
negative answer: there is no bank of per-spell timers to collect. Every timed
magic effect in the game shares the one slot specified in Section 8, so a
reimplementation should not build one countdown per spell.

For ownership, monster-special row assignments belong to combat and
monster-bestiary work and are public there for the analyzed baseline. This
document mentions the hook only to keep those effects separate from the
forty-eight player spell definitions.

- **Per-spell effect math.** The dispatcher's
  forty-eight-entry table has been mapped in public spell order, and the major
  shared handler families are identified: light counter writes, field
  placement and Dispel Field removal, active-target attack wrappers with exact
  Magic Missile, Fireball, and Kill damage, Tremor's table-wide damage/reward
  path, directed wind-cone effects including exact cone geometry and
  wind/sleep friendly-fire behavior,
  creature-prompt targeters including Polymorph's Giant Rat replacement and
  Clone's paired-slot capacity behavior, table-wide fear, Gate Travel
  moonstone-slot prompting, Negate Time setup and countdown aging, and shared
  active-effect display wrappers. The decoded monster
  possess/blink/summon-daemon hook is separate from these forty-eight player
  spell definitions.

- **Summon placement and clone lifetime.** The traced summon/conjuration
  helpers place, activate, repurpose, or clone actor records, but they do not
  install an independent per-spell duration counter. Conjure uses a sixteen-outcome
  weighted animal selector before up to eight shared random arena probes
  (four-bit per-axis draw, off-arena candidates rejected without a re-roll),
  Swarm uses up to eight of the same probes to find one cell and then stacks up
  to four Insect Swarm actors on it, Clone performs paired
  actor/object copying after a `Creature:` target is accepted, and Summon uses
  the self-checking per-tile placement helper's eight random arena-coordinate
  probes to create a Daemon-class combat actor. The CAST2 shrine/urn active-object
  pattern helper is explicitly not that path. Summoned and cloned combat actors
  live in the same temporary
  combat actor/dynamic-object
  tables as ordinary combat participants; ordinary death/record-clear paths can
  remove them during the fight, and combat exit restores the pre-combat table
  snapshot.

- **Field status-helper edges.** The combat field path has a clear faction boundary: the arena helper skips the current active actor slot, but no friend/foe lookup appears before Poison/Sleep status application or Fire/Energy damage/value dispatch. Fire and Energy damage inputs are fixed, Poison/Sleep routing is fixed, and the COMBAT post-action hook is confirmed to match active-object field markers by coordinate after movement commits. The hook does not consume the matched marker. Poison Field skips linked active-object classes `>= 0x80`; for accepted targets it poisons only Good party members, while monsters and already non-Good party members fall through to poison damage with no field-contact XP credit. Sleep Field skips dead party members, otherwise applies asleep status to party targets and the combat sleep/disabled bit to non-party targets without seeding a separate sleep countdown. Combat marker placement requires target selection and confirmed in-arena impact resolution, but no Fire/Sleep/Energy random acceptance gate exists for marker materialization. The coordinate lookup accepts the first selected-coordinate descriptor with `0x80` or `0x40` set, rejects descriptors marked by `0x20` or `0x04`, and also rejects linked active-object tile byte `0xF4`; that lookup controls the returned contact target, not marker placement. Field markers persist until combat exit restores the pre-combat active-object table; no traced placement, contact, redraw, generic active-object tick, or monster death/record-clear path decrements or removes them earlier.

- **Target picking for formerly unique spells.** Sleep, Poison Wind, Death Wind,
  and Flame Wind share the directed wind-cone family and now have fixed
  cone geometry, non-faction eligibility, and per-effect result semantics;
  Magic Missile,
  Fireball, and Kill are active-target attack wrappers with fixed damage
  semantics; Tremor and Cause Fear are full actor-table sweeps; Charm,
  Polymorph, and Clone use the `Creature:` target prompt; and Mass Charm enters
  the shared active-effect path whose `C` tag is consumed by combat AI target
  selection with a class-threshold random remap.

- **Monster spell effects.** Monsters may reach special-effect behavior through
  the combat AI class-flag hook. That hook is now bounded to
  possess/charm-on-turn, blink/phase, and summon-daemon branches, separate from
  the party C-Cast prompt/dispatcher. The analyzed baseline row assignments for
  possess, blink/phase, and summon-daemon are published in
  `catalogs/monster-bestiary.md`; unnamed component bits without independent
  behavioral consumers remain opaque combat/bestiary metadata, not
  player-spell effect gaps.

- **Delegated non-spell edges.** Equipment counters, carried-item consumption,
  combat AI state, and top-down tile catalog labels remain owned by
  `systems/inventory.md`, `systems/combat.md`, and `catalogs/tile-catalog.md`.
  They should not be treated as missing spell-dispatch behavior.

## 14. Sources

The behaviour described here was derived by reading the private function and format notes listed below. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The absence of any time-driven magic-point regeneration, and the withdrawal of the earlier "full restoration on rest" claim in Section 11, derived from `u5-decomp/notes/issue_retrace_saves_rest_2026-08-22.md`.

- The C-Cast dispatcher itself — its prompt, the forty-eight-entry token table, the charges/mana/level gate cascade, the scene gate, the per-spell handler dispatch, the light-spell duration writes, the field-placement byte mapping, the handler-family map, and the print-on-success and print-on-failure narration — derived from `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`, local CAST/CAST2 helper analysis, and the CAST2 overlay dispatch mapping in `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- The directed wind-cone and actor-scan family used by several combat spells,
  including the cardinal cone geometry, 63-coordinate cap, and absence of
  top-level and per-effect friend/foe filters in the Sleep/Poison Wind/Death
  Wind/Flame Wind branches, is derived from
  `u5-decomp/functions/CAST_OVL/0x1C36_spell_target_walk.md` and the clean
  semantic trace of the related COMBAT/COMSUBS helper calls.
- The local handlers for Tremor, Charm, Polymorph, Conjure, Swarm, Clone,
  Summon, Cause Fear, Repel Undead, Gate Travel,
  Negate Time, and Invisibility are derived from fresh local CAST.OVL and CAST2
  helper analysis summarized here without copying assembly or source. Cause
  Fear's critical-HP flee setup is cross-checked against the combat current-HP
  field and wound-score classifier in `u5-decomp/formats/data-ovl.md` and
  `u5-decomp/functions/COMBAT_OVL/0x1A5C_compute_wound_score.md`.
- The active-target attack wrapper path for Magic Missile, Fireball, and Kill — aiming/projectile routing, spell-tag damage lookup, defense subtraction, and instant-kill sentinel — is derived from local CAST, COMSUBS, and COMBAT helper analysis summarized without copying implementation text.
- Create Food's 1..3 food/provisions delta and 9999 cap are derived from
  `u5-decomp/functions/CAST_OVL/0x05B4_cast_create_food.md`.
- Source provenance: the identification of the Up and Down pair as the dungeon
  level-change spells, their ladder-free level step, their destination-cell
  refusal, their hand-off to the shared dungeon exit at a level edge, and their
  outright refusal inside Doom are derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- Arena-field placement, contact, non-consuming markers, Poison/Sleep status
  gates, Dispel Field's dungeon live-cell rewrite and combat active-object
  removal path, and combat-exit marker lifetime are derived from local CAST,
  COMSUBS, COMBAT, active-object tick, and combat-framer helper analysis plus
  `u5-decomp/functions/CAST2_OVL/0x07BC_dispel_field.md`.
- Mass Charm's active-effect target-selection consumer and class-threshold
  random remap are derived by linking the CAST2 active-effect helper to
  `u5-decomp/functions/COMBAT_OVL/0x0D30_target_picker.md` and the COMBAT
  damage/death note that identifies the same random-byte helper.
- The monster possess/blink/summon-daemon hook is derived from
  `u5-decomp/functions/COMSUBS_OVL/0x00F4_monster_special_ability_tick.md`
  and the `DATA.OVL` class-flag table; it is summarized here only to separate
  those effects from the player spell dispatcher.
- Protection's inertness, Quickness's player-side dispatch gate, Negate Magic's combat-cast absorption path, the combat C-Cast interference gate, the shared active-effect counter-aging rule, and Negate Time's `T`/10 runtime tag semantics are derived from local ULTIMA.EXE, COMBAT, COMSUBS, CAST, CAST2, and SJOG helper analysis summarized without copying implementation text.
- The single shared timed-effect slot: its code/duration pair, the permanent
  sentinel, the non-stacking replacement rule, the complete constant table for
  the four timed buff spells, Negate Time, the three timed scrolls and the three
  regalia auras, the per-turn aging rule and its duplicated mode-loop copy, the
  three clear sites, the complete consumer census for each code, Protection's
  two-fold deadness, and Invisibility's absence of any timer — derived from
  `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md`,
  `u5-decomp/notes/system-trace_magic.md`,
  `u5-decomp/functions/CAST2_OVL/0x08F8_set_scene_flag_with_redraw.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x6DA8_compute_party_member_weight.md`.
- The casting absorption pre-gate names combine `CAST.OVL` dispatcher analysis with the clean scene bindings in `catalogs/gazetteer.md` and the Crown ownership flag writer in `u5-decomp/functions/SJOG_OVL/0x1458_sjog_inventory_add.md`.
- Moonstone Search/Get recovery is derived from `u5-decomp/functions/SJOG_OVL/0x095C_sjog_search.md`, `u5-decomp/functions/SJOG_OVL/0x18CE_sjog_get.md`, and local SJOG helper analysis summarized without copying implementation text.
- The CAST.OVL function inventory and the misclassification correction (CAST is the spell-cast overlay, not character creation) — derived from `u5-decomp/functions/CAST_OVL/_OVERVIEW.md`.
- The shared spell-name input helper — accepted selector letters, order-insensitive compact-token matching, blank/cancel/no-match returns, and M-Mix's no-match fall-through — derived from local CAST2 helper analysis and the CAST2 overlay dispatch mapping in `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- The combat C-Cast adjacent-target interference gate - mapped target, target validity, target awakeness, Negate Time suppression, and adjacency - is derived from `u5-decomp/functions/COMSUBS_OVL/0x09FC_check_spell_prereqs.md`.
- The monster AI boundary correction is derived from the corrected COMSUBS
  actor-name note, the COMSUBS monster-special hook, and the COMBAT
  actor-dispatch/target-picker notes; current evidence does not support a
  general class-script table for player-spell purposes.
- The M-Mix command's pre-flight check, spell-name prompt, reagent-selection UI, quantity prompt, wrong-mix resource loss, recipe-mask comparison, charge cap, charge increment, and wrong-mix trap-effect handoff — derived from `u5-decomp/functions/CMDS_OVL/0x1AD8_cmds_mix_reagents.md`, `u5-decomp/functions/ULTIMA_EXE/0x39FC_find_paladin_or_shepherd.md`, and `u5-decomp/functions/ULTIMA_EXE/0x2FD0_trap_effect.md`.
- The three refinements to that flow — that a spell name the parser cannot match
  routes to the same wrong-recipe path and springs the trap, that the on-screen
  mixing pause is presentation only and advances no clock, and that the charge
  cap is an add-then-clamp rather than a refusal — derived from
  `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` and
  `u5-decomp/notes/system-trace_magic.md`.
- The low-circle status/HP restore helpers -- Awaken's first-Sleeping roster
  scan, Cure's selected-member Poisoned gate, selected-member Heal's Dead-only
  skip, small random HP recovery, maximum-HP clamp, status preservation,
  Great Heal's dungeon combat-active refusal, and stats-redraw dirty marking --
  are derived from
  `u5-decomp/functions/CAST2_OVL/0x03C2_heal_one_member.md` and the CAST spell
  map in `u5-decomp/functions/CAST_OVL/all_spells.md`.
- The Locate/sextant coordinate printer -- nibble-to-letter formatting,
  Y-before-X ordering, and display-only side effects -- is derived from
  `u5-decomp/functions/CAST2_OVL/0x06EC_print_party_position.md` and the CAST
  spell map in `u5-decomp/functions/CAST_OVL/all_spells.md`.
- The non-combat Blink contract -- direction prompt, straight-ray scan,
  farthest-grass landing rule, no random/retry/passability/occupancy checks,
  and no refund from handler failure -- is derived from
  `u5-decomp/functions/CAST_OVL/0x05DC_cast_in_por_blink.md`.
- The directed utility tile helpers -- Vanish, Open, Magic Lock and Unlock
  Magic: their shared direction prompt, the combat-versus-world prompt origin,
  the combat-arena terrain resolution, the exact accepted tile sets and
  rewrites, the Space/Pass silent branch, the Success/Failed narration split,
  and the arena tile census that shows which shipped arenas contain eligible
  tiles -- are derived from
  `u5-decomp/notes/2026-08-22_combat-status-magic-retrace.md`,
  `u5-decomp/functions/CAST_OVL/0x0230_cast_vanish.md`,
  `u5-decomp/functions/CAST_OVL/0x02D2_cast_open.md`,
  `u5-decomp/functions/CAST_OVL/0x0846_cast_magic_lock.md`,
  `u5-decomp/functions/CAST2_OVL/0x0768_open_door.md`,
  `u5-decomp/functions/CAST2_OVL/0x0306_prompt_direction.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x4402_get_world_tile.md`, and
  `u5-decomp/formats/maps.md`.
- The shared random arena probe, the sixteen-outcome Conjure selector, Swarm's
  single-cell-then-stack placement, the controlled-bit stamp on placed actors,
  the Summon self-check threshold and roll, the correction that spell id 7
  is Repel Undead rather than a summon/tame helper, and the finding that the
  shared exclusion filter used by Cause Fear and Repel Undead rejects the three
  protected special classes rather than "humanoids" are derived from
  `u5-decomp/notes/2026-08-22_combat-status-magic-verify.md`,
  `u5-decomp/notes/2026-08-22_combat-status-magic-retrace.md`,
  `u5-decomp/functions/CAST_OVL/all_spells.md`,
  `u5-decomp/functions/CAST2_OVL/0x04C2_spell_target_animate.md`,
  `u5-decomp/functions/COMBAT_OVL/0x120E_pick_random_arena_coord.md`,
  `u5-decomp/functions/COMBAT_OVL/0x0000_combat_damage_test_at_coord.md`,
  `u5-decomp/functions/COMBAT_OVL/0x13E2_slot_team_resolve.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x3ABE_random_short_delay.md`.
- The resurrection helper used by In Mani Corp and paid healer resurrection
  side effects -- dead-status gating, current-HP result, class-based mana
  rebuild, conditional experience rescale, level recomputation, and maximum-HP
  recomputation -- derived from
  `u5-decomp/functions/CAST2_OVL/0x05E0_resurrect_member.md` and the clean
  CAST/SHOPPES caller traces.
- The shrine meditation and Codex urn handlers -- their M-command dispatch,
  mantra prompt, quest-mask state machine, Codex-read bit stamping,
  post-completion offering path, Codex-turn-in reward table, and
  ordained/Codex bitmap updates -- derived from
  `u5-decomp/functions/CAST2_OVL/0x0E76_enter_shrine_or_urn.md`,
  `u5-decomp/functions/CAST2_OVL/0x0966_shrine_meditate.md`, and
  `u5-decomp/functions/CAST2_OVL/0x0D24_read_urn.md`.
- The twenty-four-entry rune-syllable dictionary, the sparse resident long-incantation display phrase table, the eight reagent abbreviations and full names, the eight shrine mantras, the forty-eight-entry compact rune-code table, and the resident recipe/scene-mask tables — derived from `u5-decomp/formats/data-ovl.md`, `u5-decomp/notes/system-trace_magic.md`, and local `DATA.OVL` table reads.
- The character record fields read by the magic system — strength, dexterity, intelligence, mana, level, status — and the persistent layout of the per-spell charge counters, the eight reagent counters, the gold counter, and the shrine quest masks — derived from `u5-decomp/formats/saves.md`.
