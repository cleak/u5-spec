# Karma

## 1. Overview

Karma is Britannia's measure of the avatar's moral standing across the eight virtues. Player-facing checks are virtue-specific: the shrine meditation handler speaks about the virtue whose shrine is active, NPC dialogue can branch on the relevant virtue's standing, and quest flags track the eight shrine paths independently.

The cleanroom model should therefore expose karma as eight virtue standings, not as one global "good vs. evil" axis. The exact persistent byte layout for those standings is still being recovered; the shrine handler confirms a capped standing byte for the active shrine path and the save image confirms two per-virtue quest masks.

Adjustments are spread across many overlays: the steal command in the field-action handler, the attack-non-hostile path in the combat AI, the "give" response in the conversation overlay, the shrine meditation handler, and so on. There is no central karma manager; each overlay knows the deltas it owns and applies them in place.

## 2. The eight virtues

Britannia's eight virtues, in the canonical order the engine numbers them (zero through seven) and the order they appear in every per-virtue table the engine indexes:

1. **Honesty** — truthfulness in word and deed; kept by Mariah, embodied by the mage discipline of disciplined speech.
2. **Compassion** — care for the weak, the hungry, the wounded; kept by Iolo, embodied by the bard's empathy.
3. **Valor** — courage in the face of danger; kept by Geoffrey, embodied by the fighter's willingness to engage.
4. **Justice** — application of fair principle to disputes; kept by Jaana, embodied by the druid's balance between persons and the world.
5. **Sacrifice** — the willingness to give up what one values for another's gain; kept by Julia, embodied by the tinker's craft for the common good.
6. **Honor** — adherence to one's word and to a chosen cause; kept by Dupre, embodied by the paladin's oath.
7. **Spirituality** — pursuit of inner truth; kept by Shamino, embodied by the ranger's solitary contemplation.
8. **Humility** — recognition that no one virtue is a virtue alone, and that pride in any of the others is itself a flaw; kept by Katrina, embodied by the shepherd's quiet labour.

The set, the order, and the companion-virtue pairings are inherited from Ultima IV with no changes; the in-engine virtue index zero through seven matches the order above. Every per-virtue table the engine indexes — mantras, shrine coordinates, prefix strings, virtue-failing curse phrases, virtue-aphorism paragraphs, the symmetric pair table the questionnaire reads — uses this same eight-entry layout in this same order.

The eight virtues sit alongside three "principles" (Truth, Love, Courage) and an eighth-virtue meta-principle. The principles are referenced indirectly by the mantras at certain shrines and by the Codex narrative, but they are not themselves karma-bearing axes; only the eight virtues have per-axis standing.

## 3. Karma storage

The storage picture has two confidence levels.

The save image carries two adjacent bitmask bytes recording per-shrine quest progress: an "ordained" mask and a "Codex visited" mask. They are quest flags, not karma scores. For each virtue, the pair encodes not started, ordained, Codex-read, or complete. `formats/saved-gam.md` gives the byte offsets and bit order.

The shrine meditation handler also updates a one-byte standing value for the active shrine path. Shrine increases clamp this value to ninety-nine: a completed-shrine gold offering adds the offered digit, a Codex turn-in adds three, and the Humility turn-in adds another three. Whether this byte is one entry in an eight-byte per-virtue bank, a selected-current-virtue cache, or a view over a larger karma region is not yet confirmed. A reimplementation should keep the public model per-virtue, while treating the exact save layout for those standings as provisional until more action handlers are mapped.

## 4. Karma-adjusting actions

The engine adjusts virtue standings in response to specific player actions. Each action's delta is hardcoded into the handler that processes it; there is no central data table of action-to-karma effects. The only numeric standing changes currently confirmed in the public cleanroom scope are the shrine-handler changes described below. Non-shrine rows are a behavior inventory for follow-up handler tracing: they identify likely triggers and affected virtues, but not parity-ready delta magnitudes.

Confirmed shrine-handler standing changes:

| Action | Trigger | Standing effect |
|---|---|---|
| Complete-shrine gold offering | Shrine meditation after the virtue quest is already complete | Active shrine standing + offered digit, for digits one through nine; clamps at ninety-nine |
| Codex shrine turn-in | Shrine meditation after the Codex page has been read while the ordained bit is still set | Active shrine standing +3, clamped at ninety-nine; Humility receives an additional +3 |
| Recite the wrong mantra at a shrine | Shrine meditation mantra mismatch | No confirmed standing change |

Non-shrine behavior inventory still awaiting per-handler confirmation:

| Action family | Likely trigger | Public status |
|---|---|---|
| Theft or dishonest shop action | Shop/tile command success path | Expected to affect Honesty negatively; exact handler, delta, and clamp policy open |
| False dialogue answer | Conversation keyword path with a known-false answer | Expected to affect Honesty negatively; exact covered branches and delta open |
| Refusing requested aid | Conversation refusal branch | Expected to affect Compassion negatively; exact covered branches and delta open |
| Giving to a needy NPC | Conversation "give" path with gold or food | Expected to affect Compassion positively; exact recipient classes, resources, and delta open |
| Third-party healing | Healer shop or dialogue path for curing a stranger | Expected to affect Compassion positively if present; exact branch and delta open |
| Attacking a non-hostile NPC | Combat-mode strike on a peaceful or friendly actor | Expected to affect Compassion, and possibly Justice; exact victim test and magnitudes open |
| Initiating or refusing combat | Combat engagement or combat-end stay-and-fight branch | Expected to affect Valor; exact tests and sign/magnitude open |
| Fleeing a winnable combat | Combat-end flee branch while advantaged | Expected to affect Valor negatively; exact advantage threshold and delta open |
| Completing or defaulting on a stated quest | Quest-flag-setting, quest-fail, or betrayal branch | Expected to affect Justice, Sacrifice, or Honor depending on the quest; exact coverage and deltas open |
| Boasting or claiming glory | Conversation boast branch | Expected to affect Humility negatively; exact covered branches and delta open |

Characteristics that are firm even where non-shrine magnitudes are not:

- **Shrine offerings are not stat rewards.** They consume party gold and raise the active shrine standing only after that virtue's shrine quest is already complete.
- **Shrine quest turn-in is the stat reward.** Returning after the Codex page clears the ordained bit, raises standing, and may increment Avatar stats according to the shrine stat table in Section 6.
- **Attack actions are the likely Compassion/Justice overlap.** Striking a peaceful citizen offends both the duty of care and the principle of fair conduct, but the exact victim classification and whether both virtues always change remain open.
- **Honesty appears mostly penalty-driven in normal play.** One preserves Honesty by avoiding falsehood and theft; any positive Honesty inputs outside chargen are still unverified.
- **Valor appears to swing in both directions.** Standing ground and fleeing are expected to use different signs, but the exact "winnable fight" test and delta magnitudes are not public-spec-ready.

These deltas accumulate over a campaign. The thresholds the shrine handler uses to map a standing to a tier verdict (Section 5) define the player-visible interpretation of the bands.

## 5. KARMA.DAT — the tier-verdict file

The data file `KARMA.DAT` (761 bytes) holds six NUL-terminated text records, each a paragraph of speech the shrine handler prints during meditation. Despite the file name, it does **not** hold numeric karma deltas — those live in code, distributed across the action handlers. `KARMA.DAT` is purely player-visible verdict text the shrine speaks back when the engine compares the relevant virtue's standing against a threshold.

The six records cluster by tier, in ascending order of standing:

1. **Lowest** — addressed to an avatar who has strayed from the path of the virtue. Spoken at the floor.
2. **Low** — addressed to an avatar who has erred but is offered a chance to do better. Corrective rather than condemnatory.
3. **Middle** — the standard "you have potential" speech: seeds of greatness, not yet the practice.
4. **High** — praises the work done but flags that more remains.
5. **Highest** — declares the destiny that awaits, bids the player return to the work.
6. **Highest (variant)** — a near-duplicate of record five. Whether this is an endgame-only variant, an in-game variant at certain quest milestones, or dead text is open.

When the meditation handler needs a verdict, it computes a tier index from the avatar's standing for the active virtue and prints that record. The file has no header and no offset table — records are sequentially packed, so the seek to record `n` is "skip past `n` NUL terminators". A modern reimplementation can keep the same layout or swap to a structured table without altering player-facing behaviour, since the engine's only contract is "give me the text for tier `n`".

The threshold table that maps standing to tier index is **not** in `KARMA.DAT`. It lives inside the meditation handler in the spell-effects overlay (the same overlay that owns urn reading and the in-game save). The handler's shrine-side increases clamp the active standing at ninety-nine; the exact score-to-record breakpoints are still open.

## 6. Shrine meditation

The flow that exposes `KARMA.DAT` to the player is the shrine meditation handler. Meditation runs when the player presses `M` while the party is standing on one of the shrine coordinates. The handler matches the party position to the shrine table, renders the kneeling avatar tile, prompts for a mantra, and reads up to twelve characters.

The eight expected mantras are fixed:

| Virtue | Mantra |
|---|---|
| Honesty | `Ahm` |
| Compassion | `Mu` |
| Valor | `Ra` |
| Justice | `Beh` |
| Sacrifice | `Cah` |
| Honor | `Summ` |
| Spirituality | `Om` |
| Humility | `Lum` |

A wrong or blank mantra prints the no-effect meditation branch and returns to field mode. No shrine-handler standing penalty is confirmed for a mantra mismatch.

A correct mantra enters the shrine quest state machine for that virtue:

| Ordained bit | Codex bit | Meaning | Shrine result |
|---:|---:|---|---|
| 0 | 0 | Not started | Sets the ordained bit. No gold prompt, stat increase, or standing increase is applied. |
| 1 | 0 | Ordained, Codex not yet read | Leaves the ordained bit set. No gold prompt, stat increase, or standing increase is applied. |
| 1 | 1 | Codex-read turn-in | Clears the ordained bit, adds three to active shrine standing, clamps at ninety-nine, and applies the stat rewards below. Humility adds another three standing after the stat step. |
| 0 | 1 | Complete | Runs the ordinary offering path. A digit one through nine costs `digit * 100` gold and adds that digit to active shrine standing, clamped at ninety-nine. Digit zero is a no-effect exit. If the party lacks enough gold, the prompt repeats. |

The Codex-read turn-in rewards always write to the Avatar record, not to whichever companion is currently active. Each touched stat increments by one and clamps at thirty.

| Virtue | Avatar stat reward on Codex turn-in |
|---|---|
| Honesty | Intelligence |
| Compassion | Dexterity |
| Valor | Strength |
| Justice | Dexterity, Intelligence |
| Sacrifice | Strength, Dexterity |
| Honor | Strength, Intelligence |
| Spirituality | Strength, Dexterity, Intelligence |
| Humility | None |

The meditation handler does not require a minimum standing to run. Standing affects the verdict speech selected from `KARMA.DAT`; the mechanical state transitions are governed by the ordained and Codex bit pair.

## 7. Virtue-to-class linkage and the avatar's class

Each of Britannia's eight virtues is associated with a companion character class:

| Virtue | Companion | Class |
|---|---|---|
| Honesty | Mariah | Mage |
| Compassion | Iolo | Bard |
| Valor | Geoffrey | Fighter |
| Justice | Jaana | Druid |
| Sacrifice | Julia | Tinker |
| Honor | Dupre | Paladin |
| Spirituality | Shamino | Ranger |
| Humility | Katrina | Shepherd |

This pairing is inherited from Ultima IV, where the avatar's class was selected at chargen by the questionnaire's "winning virtue". Ultima V breaks that link: the avatar is always class "Avatar" regardless of which virtue won (see `chargen.md`). The class byte is set to the Avatar letter by the seed save (`INIT.GAM`) and is never overwritten by chargen.

The eight class letters that appear in the character roster therefore belong only to the companions: Shamino's slot carries the ranger letter, Iolo's the bard letter, Mariah's the mage letter, and so on. The avatar's slot carries the Avatar letter for the entire campaign.

This decoupling matters: in Ultima V, the avatar's karma standings are independent of class and may evolve in any direction. Companion stats and abilities reflect their class but are not adjusted by karma at runtime.

## 8. Endgame karma and quest gating

The endgame is gated primarily by quest flags, not by the fluctuating shrine standing byte itself. The two shrine masks encode a four-state path per virtue:

| Ordained bit | Codex bit | State |
|---:|---:|---|
| 0 | 0 | Not started |
| 1 | 0 | Ordained, must visit the Codex |
| 1 | 1 | Codex page read, must return to the shrine |
| 0 | 1 | Complete |

The shrine turn-in transition is important: returning after the Codex page clears the ordained bit and leaves the Codex bit set. Therefore "all virtues complete" is represented by all Codex bits set and all ordained bits clear, not by an all-set ordained mask.

Side-quest completion flags are scattered through the save image; each major virtue arc sets its own flag on completion. Lord British's endgame dialogue reads these broader quest flags and substitutes a not-ready branch if prerequisites are missing. Karma standings may still gate earlier NPC or quest interactions indirectly, but the shrine meditation handler itself uses quest-mask state rather than a standing threshold to decide its mechanical branch.

## 9. NPC dialogue gating

Some NPC conversation branches are gated on karma. The conversation overlay reads the active virtue's standing and selects a response based on whether it is above or below a threshold. Observed examples:

- **Healer service.** Healers do not modulate prices on karma; the treatment tables determine ordinary costs, and the Minoc / The Healers Mission Cure/Heal no-price branch is keyed to town-scene identity rather than virtue standing. Current shop evidence does not show a karma-owned healer price or treatment-text branch.
- **Begging response.** When the player uses "give" on a beggar, the response varies on Compassion: high-Compassion avatars receive a thankful response, low-Compassion ones a suspicious one.
- **NPC service refusal.** Certain NPCs refuse to deal with avatars whose karma in a virtue is too low. The refusal is dialogue-only; no guard alarm or criminal flag is set, so the practical effect is that the player seeks the same service elsewhere.

These branches are scattered across the conversation overlay (TALK.OVL) and the shop overlays (SHOPPES.OVL and siblings). There is no central NPC karma gate; each branch implements its own threshold. The sage rumour shop path is not currently listed as a karma-gated branch: the decoded shop flow is a topic, fee, destination, and template lookup. If karma affects rumour truthfulness elsewhere, that branch remains unverified.

Shop pricing in Ultima V is **not** karma-modulated. Arms purchases do have a decoded speaking-member Intelligence adjustment, but karma standing does not change gold cost. Karma affects some dialogue branches and virtue outcomes, not price tags.

## 10. Open questions

- **Non-shrine action coverage and magnitudes.** Section 4 lists likely trigger and virtue relationships, but exact covered branches, sign, magnitude, and clamp behavior require per-handler analysis. `KARMA.DAT` cannot answer this because it only stores verdict text.

- **Karma byte layout.** The shrine handler confirms one capped active-standing byte, but the full per-virtue save layout is still unconfirmed. The public model remains eight virtue standings; the byte-level persistence should remain provisional until more action handlers are mapped.

- **Tier threshold values.** The standing-to-tier mapping is in code, not data. Shrine-side increases clamp at ninety-nine, but the exact record breakpoints and whether they vary per virtue are open.

- **The duplicate top-tier verdict.** Two near-identical records at the top of the tier ladder. Whether one is an endgame-only variant, dead text, or both reachable will be settled by tracing the meditation handler's record-index computation.

- **Combat karma branches.** The "attack non-hostile" path is the most karma-rich combat case; exact deltas (how much Compassion lost, whether Justice is also lost, scaling on victim status) are open until the combat handler is traced in detail.

- **Endgame karma checks.** Whether Lord British's endgame reads any per-virtue standing in addition to quest flags is open. The simplest model, quest flags only, is consistent with the notes but not confirmed.

- **Karma in the chargen seed.** Whether the engine writes initial karma values matching the questionnaire's stat tallies, or whether all virtues start at a neutral midpoint, is open. `INIT.GAM` contains the answer.

- **Non-shrine overflow policy.** Shrine-side increases clamp at ninety-nine. Other karma-adjusting handlers still need confirmation for their own clamp or overflow behavior.

## 11. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The shrine meditation flow (mantra prompt, quest-mask state machine, post-completion offering path, Codex-turn-in reward table, standing clamp, verdict dispatch, kneeling-tile animation) — derived from `u5-decomp/functions/CAST2_OVL/0x0966_shrine_meditate.md` and the local CAST2 shrine-handler trace.
- The `KARMA.DAT` six-record tier-verdict layout, the lack of numeric deltas in the file, and the duplicate top-tier record — derived from `u5-decomp/formats/data-tables.md` (`KARMA.DAT` section).
- The active shrine standing byte and unresolved broader karma storage layout — derived from `u5-decomp/formats/saves.md`, `u5-decomp/formats/ds-bss-map.md`, and the shrine handler.
- The ordained / Codex visited bitmasks following the inventory section — derived from `u5-decomp/formats/saves.md` (shrine quest progress region).
- The eight-virtue ordering, per-virtue mantra and prefix tables — derived from `u5-decomp/formats/data-ovl.md` and the shrine handler note.
- The chargen-time seeding of stat tallies and the lack of avatar-class write — derived from `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` and `u5-decomp/functions/FONT_OVL/0x09C8_questionnaire_iter.md`.
- The shop pricing model (not karma-modulated, with arms Intelligence adjustment handled in the shop spec) — derived from `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md` (Karma / reputation interactions section).
- The sage topic/fee/destination/template path, and the absence of a confirmed sage-shop karma selector — derived from `u5-decomp/functions/SHOPPES2_OVL/0x0508_sage_main.md`.
- The Blackthorn audience flow's lack of in-overlay karma adjustment — derived from `u5-decomp/functions/BLCKTHRN_OVL/OVERVIEW.md`.
- The per-companion class assignments and the avatar-as-class-Avatar invariant — derived from `u5-decomp/formats/saves.md` (character roster) and cross-checked against the shrine handler note.
- The MISCMSG.DAT virtue-aphorism and "failing of virtue" record clusters printed during meditation and certain dialogue branches — derived from `u5-decomp/formats/data-tables.md` (MISCMSG.DAT section, records twelve through twenty-seven).
