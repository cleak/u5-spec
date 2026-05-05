# Magic

## 1. Overview

Ultima V has the richest magic system of the early Ultima series. The player can cast forty-eight distinct spells, organised into eight ascending circles of six spells each. Every spell is named by a short sequence of one to four runic syllables drawn from a fixed twenty-four-syllable vocabulary; every spell's effect requires a specific recipe of two or more of the eight reagents to be combined ahead of time into a "charge" that the cast itself consumes. A spell's circle determines its mana cost (a circle-N spell costs N magic points), the minimum experience level required to cast it, and roughly its power.

Magic is therefore a chain of three preparations and one act:

1. **Buy or find reagents.** The eight reagents are sold by herbalists in towns, can be picked up from despoiled enemies, or grown in certain locations. Each is an item the player carries in inventory in a per-reagent counter.
2. **Mix reagents into spell charges.** The `M` command opens a per-spell mixing prompt. The player picks a spell, chooses a quantity, and the engine debits the recipe's reagents from inventory once per charge while incrementing the per-spell charge counter.
3. **Have enough mana and experience level.** The active caster must be alive and awake, must have at least N mana points where N is the spell's circle, and must be at least level N. Casting outside these bounds either silently rejects ("None mixed!") or accepts the cast but fails it after debiting mana ("M.P. too low!") — the second case is a real penalty for a low-level character attempting a high-circle spell.
4. **Cast.** The `C` command opens the cast pipeline. The player types the spell's rune-name in compact letter-coded form; the engine parses it against a forty-eight-entry table, runs the prerequisite gate, debits a charge, debits mana, and dispatches to the spell's effect handler.

This spec describes the reagents, the rune vocabulary, the eight circles and their forty-eight spells, the cast and mix command flows, the prerequisite gates, the effect categories, the differences between casting in the overworld and casting in combat, and the linkage between spells and the eight virtue shrines that bestow stat boosts on meditation.

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
| Nightshade   | `Nightshade` | Rare; specific outdoor patches at night       |
| Mandrake Root| `Mandrake`   | Rare; specific outdoor patches at full moon   |

The order is canonical: every per-spell recipe is implicitly indexed against the same eight slots. The shorter abbreviations are used in tight UI lines (the M-Mix prompt, combat narration); the long forms are used on the dedicated reagent inventory panel.

The reagent inventory is part of the persistent save image. Each reagent is a single byte counter; the cap is the same as for ordinary inventory items (the engine treats unsigned overflow conservatively, so an implementer can settle on a 99-or-255 ceiling without breaking anything visible). The counter is decremented by mixing (Section 6) and incremented by herbalist purchases and by occasional plot-driven gifts.

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
| Jux      | harm, danger (rare)           |
| Kal      | summon, invoke                |
| Lor      | light                         |
| Mani     | life, healing                 |
| Nox      | poison                        |
| Ort      | magic (rare)                  |
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

(The rune dictionary in the resident data segment contains exactly twenty-four entries; Jux and Ort are listed here for completeness because they appear in lore but are seldom or never used by spell names.)

A spell name is the concatenation of its syllables in order. "Mani" alone is *Heal* (circle 1); "Vas Mani" is *Great Heal* (circle 5; same root, "great" prefix); "In Mani Corp" is the resurrection family; "An Xen Corp" is the slay-undead family. Most U5 spells follow this pattern, with subject-verb-object readable as the chain of runes. A few have conventional names (*Vas Rel Por* — "Great Change Movement" — is the marquee gate-travel teleport).

The rune vocabulary is also used outside the spell system: NPC dialogue mentions runes by name; the Words of Power that disable Stonegate's doors are runic. The syllable table is shared, but the spell-name parser is its own pipeline.

## 4. The eight circles and forty-eight spells

The forty-eight spells are organised into eight circles of six spells each. The circle determines the mana cost (circle-N costs N mana) and the minimum caster level (a level-N character cannot cast circle-(N+1) spells reliably — the level gate accepts the cast and debits mana but fails the effect). Within a circle, spells have similar power but different *kinds* of effect.

The full table:

| Circle | Spell name (runes)        | Common name        | Effect summary                                            |
|:------:|---------------------------|--------------------|-----------------------------------------------------------|
| 1      | An Zu                     | Awaken              | Wake a sleeping party member.                              |
| 1      | An Nox                    | Cure                | Cure poison on a party member.                             |
| 1      | Mani                      | Heal                | Restore moderate HP to a party member.                     |
| 1      | An Ylem                   | Light               | Bright light around the party.                             |
| 1      | An Sanct                  | Unlock Magic        | Open a magically locked door.                              |
| 1      | An Xen Corp               | Repond              | Calm/dispel one undead.                                    |
| 2      | Rel Hur                   | Wind Change         | Rotate the prevailing wind one quarter.                    |
| 2      | In Wis                    | Locate              | Read the party's current X, Y, Z position.                 |
| 2      | Kal Xen                   | Summon Creature     | Tame a single small creature (rabbit, etc.).               |
| 2      | In Xen Mani               | Heal Animal         | Heal one tame mount or summoned creature.                  |
| 2      | Vas Lor                   | Great Light         | Bright, long-duration light.                               |
| 2      | Vas Flam                  | Fireball            | Single-target ranged fire damage.                          |
| 3      | In Flam Grav              | Fire Field          | Place a burning-tile field at a chosen cell.               |
| 3      | In Nox Grav               | Poison Field        | Place a poison-tile field at a chosen cell.                |
| 3      | In Zu Grav                | Sleep Field         | Place a sleep-tile field at a chosen cell.                 |
| 3      | In Por                    | Blink               | Short teleport to a same-map cell.                         |
| 3      | An Grav                   | Dispel Field        | Remove a placed field at a chosen cell.                    |
| 3      | In Sanct                  | Protection          | Single-target magic armour buff.                           |
| 4      | In Sanct Grav             | Mass Protection     | Party-wide magic armour buff.                              |
| 4      | Uus Por                   | Up                  | Move the party up one dungeon level.                       |
| 4      | Des Por                   | Down                | Move the party down one dungeon level.                     |
| 4      | Wis Quas                  | Reveal              | Make hidden / illusion creatures visible.                  |
| 4      | In Bet Xen                | Insect Swarm        | Summon a small insect cloud as ranged attacker.            |
| 4      | An Ex Por                 | Negate Field        | Open a magically barred passage.                           |
| 5      | In Ex Por                 | Magic Lock          | Magically lock a door against a passer-by.                 |
| 5      | Vas Mani                  | Great Heal          | Strong HP restoration.                                     |
| 5      | In Zu                     | Sleep               | Single-target sleep.                                        |
| 5      | Rel Tym                   | Quickness           | Speed-up buff (acts more often per round).                 |
| 5      | In Vas Por Ylem           | Earthquake          | Area damage, all on-screen.                                |
| 5      | Quas An Wis               | Mass Confuse        | Confuse all visible enemies.                               |
| 6      | In An                     | Negate Magic        | Suppress active enchantments and spells in scene.          |
| 6      | Wis An Ylem               | View                | Open the world-map view from current location.             |
| 6      | An Xen Ex                 | Dispel Monster      | Remove one specific summon/illusion.                       |
| 6      | Rel Xen Bet               | Polymorph           | Change a target into a small creature.                     |
| 6      | Sanct Lor                 | Invisibility        | Single-target invisibility buff.                           |
| 6      | Xen Corp                  | Slay Living         | Single-target instant-kill against living creatures.       |
| 7      | In Quas Xen               | Conjure             | Summon a creature to fight on the party's side.            |
| 7      | In Quas Wis               | Confuse             | Single-target confusion.                                   |
| 7      | In Nox Hur                | Poison Wind         | Area poison-effect with wind-direction shape.              |
| 7      | In Quas Corp              | Fear                | Make targets flee.                                         |
| 7      | In Mani Corp              | Resurrection        | Bring a dead party member back to life (with cost).        |
| 7      | Kal Xen Corp              | Summon Daemon       | Summon a demon as ally.                                    |
| 8      | In Vas Grav Corp          | Cataclysm           | Heavy area damage.                                         |
| 8      | In Flam Hur               | Fire Storm          | Wide-area fire damage.                                     |
| 8      | Vas Rel Por               | Gate Travel         | Long-range teleport via moongate phase.                    |
| 8      | An Tym                    | Time Stop           | Freeze monster turns for several rounds.                   |
| 8      | (eighth slot; resurrection long form) | Resurrection (rare) | Alternate, more reliable resurrection.        |
| 8      | (eighth slot; final negate) | Negate Time      | Stronger Time Stop.                                        |

The exact assignment of names and effects to the last two circle-8 slots is uncertain in the project's analysis (Section 13). Implementations should treat the table as a working framework and verify each circle-8 entry against the in-game manual when the per-handler decompilation completes.

The mana cost for any spell is `(spell_index / 6) + 1` (integer division, zero-based index 0..47). Equivalently, the circle number. Circle 1 costs 1 MP, circle 8 costs 8 MP. There are no half-costs, no cost-reduction items, and no per-class cost adjustments — magic is uniform across casters.

## 5. The C-Cast command

The `C` (Cast) command is the player's gateway to the spell system. It is available from every world mode loop (overworld, town, dungeon) and from combat; the implementation routes through the same dispatcher in all four cases.

**Step 1 — active-player resolve.** The dispatcher first asks "who is casting?" by reading the active-player slot. If no party member is selected, the cast aborts silently. Outside combat, the active-player byte is whatever the player most recently set with the digit keys. Inside combat, the active-player byte is whichever party-slot the round walker is currently dispatching.

**Step 2 — prompt for the spell name.** The dispatcher prints `Spell name:` and a colon-prompt, switches the input pipeline into prompt mode, and reads the spell name. The name is typed as a compact letter-coded form: the player types only the *distinguishing letters* of each rune in the spell, not the rune syllables in full. Examples: `IL` for *An Zu* (Awaken — circle 1); `IPVY` for *In Vas Por Ylem* (Earthquake — circle 5); `CGIV` for the eight-rune Gate Travel; just `M` for the lone-mani Heal. The forty-eight legal codes are stored in a small token table.

The compact letter-coded form is convenient for fast typing — there are forty-eight legal codes, each two to four letters — but it is unique only as a set: the player must know the code for the spell they want. The U5 manual lists the codes as part of each spell's entry, and the Z-stats spell-book panel displays them in-game. Typing a code that does not match prints `No effect!`; pressing Enter on an empty buffer prints `None!`; pressing Escape cancels with no time consumed.

**Step 3 — context gate.** Each spell carries a four-bit allow-mask describing which scene-types the spell may be cast in: overworld, town, shrine, or combat. The dispatcher reads the current scene byte, computes the matching mask bit, and tests it against the spell's mask. If the spell is not allowed in this scene (for example, an Earthquake cast in a town), the dispatcher prints `Not here!` and aborts. Time is *not* consumed on this rejection — the player can change scenes and try again.

**Step 4 — charges gate.** The dispatcher reads the per-spell charge counter. If the counter is zero, the dispatcher prints `None mixed!` and aborts. Otherwise the counter is decremented immediately, before any further checks — the charge is "spent" the moment the dispatcher commits to the cast.

**Step 5 — mana and level gate.** The dispatcher reads the active player's current mana points and compares against the spell's mana cost. If insufficient, the dispatcher prints `M.P. too low!` and aborts. A second comparison checks the player's experience level against the same cost. If the level is below the cost, the dispatcher *also* prints `M.P. too low!` — but only after debiting the mana. This is a deliberate penalty: a level-3 character attempting a circle-7 spell loses seven points of mana and watches the cast fail.

**Step 6 — debit mana.** Mana is subtracted from the active player's record. (At this point, both the charge counter and the mana have been spent.)

**Step 7 — dispatch to the effect handler.** The dispatcher computes the spell's index (0..47) into a forty-eight-entry jump table and calls the matching handler. Handlers fall into a small set of families described in Section 8.

**Step 8 — narrate the result.** Most handlers print a short success message: `Light!`, `Wind change!`, `Protection!`, `View!`, `Resurrection!`, `Negate magic!`, `Negate time!`, `Summon Daemon!`. A handful print nothing on success (the projectile spells, the field placements). A failure path prints `Failed!`; a success without a spell-specific message prints `Success!`.

The command then returns to the calling mode loop. Time advances by the standard per-mode increment. A spell cast costs one turn regardless of the spell's power.

## 6. The M-Mix command

The `M` (Mix Reagents) command is the player's tool for converting raw reagents into pre-mixed charges. It is available from the overworld and town mode loops; from a dungeon mode loop the command exists but is rarely useful (the player typically mixes between dungeon expeditions). The command is *not* available inside combat — there is no time to mix in a fight.

**Step 1 — pre-flight check.** The handler verifies the player has at least one of any reagent. With an empty reagent inventory, it prints `No reagents owned!` and aborts.

**Step 2 — pick a spell.** The handler prints `For what spell?` and uses the same compact letter-coded prompt as the C-Cast command. The spell name is parsed against the forty-eight-entry token table, returning the spell index 0..47. Cancel and unknown-name responses behave the same as in C-Cast.

**Step 3 — pick a quantity.** The handler prints `How much?` and reads a small unsigned digit. The quantity is the number of *charges* the player wants to mix; each charge consumes one full copy of the spell's recipe.

**Step 4 — verify reagents available.** The handler reads the spell's recipe — a per-spell mask of which of the eight reagents are needed — and checks the player's inventory against the requested quantity. If any reagent is short, the handler prints `Insufficient reagents!` and aborts (no reagents are consumed).

**Step 5 — mix.** The handler prints `Mixing...`, runs a short progress-style delay, and then for each requested charge: decrements one of each required reagent in inventory, increments the per-spell charge counter, and increments a per-iteration progress display. The reagent debits are done one at a time so a partially-completed mix can in principle be detected mid-loop, although with the pre-flight verification a partial mix is unreachable.

A `Nothing to mix!` rejection appears if the player names a spell they have no recipe-fit reagents for at all — the system distinguishes "you tried to mix but you had nothing" from "you have some but not enough".

The recipe list — which reagents each spell needs — is fixed and matches the U5 manual. Common patterns: heals tend to use Ginseng + Spider Silk; lights tend to use Sulfur Ash + Mandrake Root; fire spells use Sulfur Ash + Black Pearl; protections use Garlic + Ginseng + Mandrake; the rare top-circle spells (Resurrection, Cataclysm, Gate Travel) use four or five reagents and consume some of the rarer ones (Mandrake, Nightshade) — which is what makes them strategic.

The per-spell charge counters are part of the persistent save image: forty-eight bytes, one per spell. The counters survive saving, loading, dying, and combat. They are consumed only by C-Cast and replenished only by M-Mix; no other path writes to them.

## 7. Casting prerequisites in detail

Combat introduces an additional prerequisite gate that runs *before* the C-Cast command's own checks; outside combat, only the dispatcher's checks apply. The combined gate hierarchy is:

**Combat-only pre-gate.** Reached when the player presses `C` inside a combat round. Before the dispatcher even prompts for the spell name, a four-step combat prereq cascade runs:

1. **Target validity.** The combat target picker writes a target slot for the casting party member; the prereq checks the slot is non-empty (the all-ones sentinel value means "no target picked"). Failure aborts the cast silently — no time consumed.
2. **Target visibility and awakeness.** The target's combat-state flags must indicate alive, visible (not currently in an "unrevealed" or "invisible" state), and awake (not asleep). A spell at a sleeping or invisible target fails the gate.
3. **Vehicle gate.** The caster's current vehicle must permit casting. The "tower" vehicle (carpet at altitude, in U5's framing) blocks all spellcasting; the gate aborts the cast if the caster is currently in that state.
4. **Resource gate.** A separate per-class check verifies the caster has the basic resources (mana > 0, target type compatible with caster's class). On success the gate runs a small AI hook (the target reacts to being targeted) and prints a continuation message — typically combining with a name to read like "*<spell> interferes!*".

**Dispatcher gates** (run after the combat pre-gate, or as the only gate outside combat):

5. **Charges gate** — `[per-spell charge] > 0`, otherwise `None mixed!`.
6. **Scene gate** — per-spell allow-mask matches the current scene byte, otherwise `Not here!`.
7. **Mana gate** — `[active-player mana] >= circle`, otherwise `M.P. too low!` (no mana spent).
8. **Level gate** — `[active-player level] >= circle`, otherwise `M.P. too low!` (mana *is* spent).

The two-stage failure for "M.P. too low!" is a player-visible artefact: a low-mana character can re-cast after recovering mana with no penalty, but a low-level character casting a high-circle spell loses mana every attempt. The intended message is the same; the underlying penalties differ.

The *order* of the gates matters:

- The charges-gate runs before the mana-gate, so a player without a charge does not waste mana trying.
- The mana-gate runs before the level-gate, so a player without enough mana does not waste a charge — the charge has already been decremented at this point in the original implementation, and the engine refunds it on a mana-gate failure (the per-spell charge counter is bumped back up). The level-gate sees the post-decrement state, so a level-failure does *not* refund the charge or the mana. Implementations targeting period-faithful behaviour should preserve this asymmetry.

## 8. Spell effects

The forty-eight spell effects fall into seven broad categories. Each handler takes the active-player slot and the dispatcher's per-spell context as input; each returns a success/failure code that the dispatcher uses to print the trailing `Failed!` if appropriate.

**Utility effects.** Light, Great Light, Wind Change, Locate, Magic Lock, Magic Unlock, Protection, Mass Protection, Quickness, View, Reveal, Up, Down, Negate Field. These are scene-altering or single-step interactions: they place a flag, write a value, redraw a panel, or move the party. Most have a short narration message and finish in a single handler call.

**Healing effects.** Heal, Great Heal, Cure, Awaken, Heal Animal, Resurrection. These read the target's character record, modify HP / status / mana fields, and update the displayed stats. Healing accepts a target party-member slot (asked separately, or implicit via active player); resurrection only succeeds on a target whose status byte is `'D'` (dead) and writes back `'G'` (good) on success.

**Buff and debuff effects.** Protection, Mass Protection, Quickness, Polymorph, Invisibility, Confuse, Mass Confuse, Fear. These set or clear flags in the target's combat-state record. Most have per-round timers that the round walker consults.

**Direct damage attacks.** Fireball, Magic Missile equivalent (some circle-1/2 spells are simple ranged attacks — the project's analysis maps several to single-target damage spells), Slay Living, Earthquake, Cataclysm, Fire Storm. These walk the actor table, pick targets either by direction (line-of-effect) or by area (every visible enemy), and call the same damage-and-status handler combat uses for melee attacks (the unified attack primitive). Range and damage are per-spell; the AOE shape is per-spell.

**Field placement.** Fire Field, Poison Field, Sleep Field, Dispel Field. These place or remove a tile-effect entry on the active map at a chosen cell; the field persists for several turns (consumed by the per-turn world tick) and applies its effect to any actor that enters or starts a turn on the cell. Field-removal and Negate Field share an underlying dispel routine.

**Summoning and conjuration.** Summon Creature (small, peaceful), Conjure (combat ally), Insect Swarm, Summon Daemon. These insert a new entry into the actor table (or the world's dynamic-objects table) with a tile drawn from a per-spell summoned-class list. Summoned creatures are then run by the standard AI; they vanish when killed or after a per-spell duration.

**Special / marquee effects.** Negate Magic, Negate Time, Time Stop, Gate Travel, In Quas Wis Xen (the rune-codex visit). These are the fewest-use spells with the largest gameplay impact. Negate Magic suppresses every active enchantment and field within the scene, including buffs on enemies. Time Stop and Negate Time freeze monster turns for several rounds, allowing the party to reposition or attack freely. Gate Travel teleports the party to a moongate destination keyed to the current moon phase; it is the one spell whose target is the *world* map, not the caster's record. The In Quas Wis Xen path is a unique scripted spell that opens the codex view; it uses the same dispatcher but its handler has unique narration and effect.

The full per-handler effect map is incomplete in the current decompilation. Section 13 records the spells whose handlers have not yet been fully decoded.

## 9. Casting in combat

The C-Cast command is also bound in the combat command set. The implementation reuses the same dispatcher described in Section 5; the routing mechanism is a single combat-mode entry that validates combat prereqs, then invokes the dispatcher, then validates the result.

**Same dispatcher.** From the dispatcher's point of view, a combat cast is identical to an overworld cast. The same prompt is shown, the same forty-eight-entry table is consulted, the same charge / mana / level gates run. The dispatcher reads the same DS state — including the per-spell charge counters and the per-character mana — so the in-combat cast and the out-of-combat cast are perfectly interchangeable for state purposes.

**Combat-specific prereq pre-gate.** Section 7 listed the four-step combat-only pre-gate. It runs before the dispatcher prompts for the spell name; an aborted pre-gate skips the dispatcher entirely.

**Active player and target.** Outside combat, the active player is whichever character the digit keys most recently selected; the cast applies to or originates from that character. Inside combat, the active player is whichever slot the round walker is currently dispatching — the cast happens on that character's turn and consumes that character's mana. Several spells (the heal/restore family, the resurrect, the protection-target) take an explicit target separately from the caster; in combat the target picker has already chosen, and the spell handler reads the picked target slot.

**Scene gate selects spells.** The four-bit scene allow-mask uses bit 4 (combat) as one option; spells without that bit are rejected with `Not here!` even if the player names them inside combat. So Earthquake or Fire Storm — combat-allowed AOEs — fire normally inside combat; while a fireside utility like Wind Change, which is overworld-tagged, is silently rejected.

**Monster casters.** Monsters that have spell-like attacks do *not* go through the dispatcher. Their effects are hand-coded as part of the monster's per-class AI script and are gated by per-class flags rather than by the spell-cast pipeline. A Daemon's flame breath, a dragon's freeze gaze, a shadowlord's curse — these read no charge counter, consume no reagent, and obey no circle rule. The shared infrastructure is the damage-and-status handler at the end of the chain; the upstream dispatch differs.

**Combat ends with state preserved.** Spell-cast charges are decremented and mana is debited inside combat exactly as outside; both effects survive the combat exit and are part of the persistent save. A spell cast inside combat is real and permanent; the framer that brackets combat with save-and-restore preserves the cast's after-effects (just as it preserves damage).

## 10. Linkage to the eight virtue shrines

The eight virtue shrines (Honesty, Compassion, Valour, Justice, Honor, Sacrifice, Spirituality, Humility) are not part of the spell system proper, but they are the principal means of permanently increasing the active character's mana cap and other stats. The shrines are the indirect "level up your magic" mechanic.

When the active character kneels at a shrine and presses `M` (Meditate — distinct from the mix command of the same letter), the engine prompts for the shrine's mantra. The eight mantras are short fixed words: `Ahm`, `Mu`, `Ra`, `Beh`, `Cah`, `Summ`, `Om`, `Lum`. They map one-to-one with the eight virtues.

A correct mantra unlocks an offering prompt. The character offers gold from the shared party pool; a digit `0–9` is read, multiplied by 100, and debited from the gold counter. On a valid offering, the engine prints `ALAKAZAM` and applies the shrine's blessing — the active character's strength, dexterity, or intelligence (the choice depends on which shrine and on the exact karma state) is incremented by one. The intelligence stat is the one that drives mana cap, so a sustained pilgrimage to all eight shrines produces a meaningful per-cast budget.

A small per-virtue "ordained" bitmap in the save image records which shrines have been completed for the current character; many shrines accept only one stat-up per character, with subsequent visits providing the offering text but no stat change. Exceeding the karma threshold for a virtue gives a "no effect" rejection; falling below it gives a different rejection. The full karma logic is described in `karma.md` (when written); from the magic system's point of view, the shrines are an external income source for the intelligence stat that bounds mana, and the magic system itself is unaware of the meditation flow.

## 11. Z-stats integration

The Z-stats panel — the dedicated character-sheet command — is the player's view into the magic system's persistent state.

- **Spell book.** A per-character spell-book panel lists the spells the character can attempt to cast, displaying the spell name in runes, the rune-code, the circle, the mana cost, and the recipe. The list is filtered by the character's class and level (Mages and Druids have full access; other classes see a smaller subset). The list does *not* depend on charges — every spell the character is theoretically eligible for shows in the book even if not currently mixed.
- **Reagent panel.** A separate panel shows the current count of each of the eight reagents in the party's shared inventory.
- **Charge counter panel.** A third panel shows the per-spell charge counts, displayed as the spell name plus a small integer. Spells with zero charges are shown but greyed.
- **Stats line.** The character's intelligence stat and current/maximum mana points are shown on the main Z-stats line.

Z-stats is read-only with respect to the magic system: it shows the state but never changes it. The mana-recovery model — slow regeneration of mana over real game-time, plus full restoration on rest — is described in the world's per-turn system, not here. The magic system's only requirement is that the dispatcher reads the *current* mana value; any other system can write it.

## 12. Persistence

Every piece of persistent magic state is in the save image:

- **Reagent inventory** — eight per-reagent byte counters in the inventory block.
- **Spell charges** — forty-eight per-spell byte counters, one per spell index 0..47.
- **Per-character mana** — one byte per character record, in the stats quartet (STR, DEX, INT, MP).
- **Per-character intelligence** — one byte per character record (drives mana cap).
- **Per-character level** — one byte per character record (gates level-cost).
- **Shrine ordained bits** — two bitmasks of eight bits each (one for "ordained at this shrine", one for "Codex-visited or related").

There is no separate "magic state" file: every byte is part of the standard `.GAM` runtime image, flushed and loaded on save and restore. The same is true of the eight reagent counters and the forty-eight charge counters. There are no file-borne tables that the magic system reads at runtime — every per-spell datum (the rune-code table, the recipe table, the allow-mask) is interned in the resident `DATA.OVL` data segment and copied into RAM at startup.

## 13. Open questions

This section records places where the picture is not yet complete, where evidence is partially decoded, or where the project's analysis records uncertainty.

- **Per-spell handler effects beyond the well-known cases.** The dispatcher's forty-eight-entry jump table has been mapped to handler offsets, and the handler shapes have been classified into five recurring patterns. Roughly twelve handlers — those with print-on-success messages like `Light!`, `Negate Magic!`, `Resurrection!` — have confirmed effect mappings. The rest are best-guesses based on the rune-name and the manual; verification requires per-handler decompilation.

- **Tentative rune-code-to-name mappings at the high circles.** Several circle-7 and circle-8 entries are provisional. The compact letter-coded form is not always the literal first-letter sequence of the rune syllables — for some spells the encoding picks distinguishing letters. The forty-eight-entry token table is correctly aligned and the count is right, but the human-readable name attached to a few entries is uncertain.

- **Per-spell allow-mask byte-by-byte.** The forty-eight-byte mask in the resident data segment has not yet been transcribed into a public table. Each byte's bits — dungeon, town, shrine, overworld — should be enumerated against each spell. Combat is not one of the four bits; combat-only checks happen inside individual handlers via a scene-byte equality test.

- **Recipe table.** The forty-eight-entry recipe-mask table (which reagents each spell needs) lives in the resident data segment; the M-Mix handler reads it. The exact location and format have not been transcribed. Implementations should cross-check against the U5 manual.

- **Per-spell charge cap.** Charge counters are bytes, so the natural cap is 255. The U5 standard inventory cap is 99, which is the most likely intended cap. The M-Mix handler may clamp on increment; verification requires tracing the increment site.

- **Mana refund semantics.** The charge-gate runs before the mana-gate, with a refund on the latter and no refund on the level-gate. The exact refund semantics in the original code need cross-checking; this spec describes the simpler "each gate cleanly aborts before the next" model that an implementer can target without losing observable correctness.

- **Friendly-fire policy for AOE spells.** Earthquake, Cataclysm, Fire Storm, Mass Confuse, and the field-placement spells affect every cell within their radius. Whether the party's own slots are damaged by these spells when standing in the area is per-spell — some are coded to skip friendly slots, others damage everyone.

- **Target picking for area-effect spells.** Single-target spells (Heal, Sleep, Slay Living) prompt for a target either by direction (combat) or by an explicit slot prompt (overworld). Multi-target spells choose their targets by walking the actor table. The exact picker per spell is per-spell.

- **Monster spell effects.** Monsters that "cast" spells — daemons, dragons, shadowlords, certain liches — have hand-coded effects per monster class. The full map belongs in the combat-AI spec.

- **Karma effects on the shrines.** The shrines reject characters whose karma is too low for the virtue, with a different message than the "no effect" rejection. The threshold and the rejection text are part of the karma system; the magic system's contract is only that the meditate command exists and that successful offerings increment the active character's stat byte.

## 14. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions and format notes in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The C-Cast dispatcher itself — its prompt, the forty-eight-entry token table, the charges/mana/level gate cascade, the scene gate, the per-spell handler dispatch, the print-on-success and print-on-failure narration — derived from `u5-decomp/functions/CAST_OVL/0x0DBA_cast_main_loop.md`.
- The CAST.OVL function inventory and the misclassification correction (CAST is the spell-cast overlay, not character creation) — derived from `u5-decomp/functions/CAST_OVL/_OVERVIEW.md`.
- The combat-only spell-prereq cascade — target validity, target awakeness, vehicle gate, resource check — derived from `u5-decomp/functions/COMSUBS_OVL/0x09FC_check_spell_prereqs.md`.
- The M-Mix command's pre-flight check, spell-name prompt, quantity prompt, recipe verification, and per-charge mixing loop — derived from `u5-decomp/functions/CMDS_OVL/0x0000_cmds_dispatch.md`.
- The shrine meditation handler — its mantra prompt, gold-offering, stat increment, and ordained-bitmap update — derived from `u5-decomp/functions/CAST2_OVL/0x0966_shrine_meditate.md`.
- The forty-eight runic spell incantations, the twenty-four-entry rune-syllable dictionary, the eight reagent abbreviations and full names, the eight shrine mantras, and the forty-eight-entry compact rune-code table — derived from `u5-decomp/formats/data-ovl.md`.
- The character record fields read by the magic system — strength, dexterity, intelligence, mana, level, status — and the persistent layout of the per-spell charge counters, the eight reagent counters, the gold counter, and the shrine ordained bitmaps — derived from `u5-decomp/formats/saves.md`.
