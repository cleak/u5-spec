# Karma

## 1. Overview

Karma is Britannia's measure of the avatar's moral standing across the eight virtues. Every virtue carries an independent score; together those scores form the avatar's reputation. Karma is read in three places: the shrine meditation handler, which prints a tier-keyed verdict speech reflecting how well the avatar has lived up to a virtue; the conversation system, where some NPCs gate dialogue or refuse service based on the player's standing; and the endgame's quest gating, where shrine ordainment and certain virtue-related side-quests are required before Lord British's final dialogue will play.

Karma is not a single hidden number. It is a small bag of per-virtue counters, each adjusted independently by the action that invokes it. Stealing degrades only Honesty; donating to a beggar lifts only Compassion; giving alms at a shrine lifts only that shrine's virtue. There is no global "good vs. evil" axis — a player can be a paragon of Compassion and a habitual liar at the same time, and the engine treats those facts independently.

Each virtue's counter is a one-byte field in the save image. Adjustments are spread across many overlays: the steal command in the field-action handler, the attack-non-hostile path in the combat AI, the "give" response in the conversation overlay, the donate-at-shrine path in the shrine handler, and so on. There is no central karma manager; each overlay knows the deltas it owns and applies them in place.

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

The eight virtues sit alongside three "principles" (Truth, Love, Courage) and an eighth-virtue meta-principle. The principles are referenced indirectly by the mantras at certain shrines and by the Codex narrative, but they are not themselves karma-bearing fields; only the eight virtues have per-axis counters.

## 3. Karma storage

The eight per-virtue scores live as eight bytes in the save image, alongside the other per-party totals (food, gold, keys, gems) in the run of single-byte fields between the character roster and the active-object table. See `save-load.md` for the surrounding layout.

Each byte holds an unsigned value. The conventional Ultima-IV bound was zero to ninety-nine, and the engine's tier dispatch (Section 5) is consistent with that range, but a byte can hold up to two hundred fifty-five and the engine may permit overflow if no caller clamps. Treat "zero through ninety-nine" as the working assumption pending confirmation.

A single tentatively-named byte in the data segment near the gold field is currently flagged as the "karma byte" in the working notes; it is most likely the field through which the shrine handler reads the active virtue's score. Whether the engine maintains all eight counters at adjacent offsets, or one "active karma" byte whose meaning depends on which shrine is active, has not been verified. The Ultima-IV-style "all eight, always present" model is the conservative implementation choice.

The save image also carries two adjacent bitmask bytes recording per-shrine quest progress: an "ordained" mask (one bit per virtue, set on quest completion) and a "Codex visited" mask (one bit per virtue, set as Codex pages are seen). These are quest flags, not karma scores — permanent achievement rather than fluctuating reputation.

## 4. Karma-adjusting actions

The engine adjusts virtue scores in response to specific player actions. Each action's per-virtue delta is hardcoded into the handler that processes it — there is no data-table of "action-id to per-virtue-delta" — and the deltas vary by action: most are plus or minus one, some are larger.

The table below lists every karma-adjusting action observed in the working notes so far. The exact deltas are working-best-guess values for many entries; per-action confirmation is pending the relevant overlay's decompilation. Where the magnitude is uncertain, "−" in the delta column means "no change to this virtue", and a numeric value means "adjustment in this direction by this magnitude (working hypothesis)".

| Action | Trigger | Honesty | Compassion | Valor | Justice | Sacrifice | Honor | Spirituality | Humility |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Steal an item from a shop | `S` command on a shop tile, success path | −1 | − | − | − | − | − | − | − |
| Lie to an NPC about quest knowledge | Conversation keyword path with a known-false answer | −1 | − | − | − | − | − | − | − |
| Refuse to help an NPC asking for aid | Conversation refusal branch | − | −1 | − | − | − | − | − | − |
| Give gold to a beggar | Conversation "give" path with a needy NPC | − | +1 | − | − | − | − | − | − |
| Donate food to a hungry NPC | Conversation "give" with food | − | +1 | − | − | − | − | − | − |
| Pay for a healer to cure a stranger | Healer shop, third-party patient | − | +1 | − | − | − | − | − | − |
| Attack a non-hostile (peaceful) NPC | Combat-mode strike on a friendly | − | −2 | − | −1 | − | − | − | − |
| Strike first against a hostile creature | Combat-engagement initiator | − | − | +1 | − | − | − | − | − |
| Refuse to flee from combat | Combat-end "ye stay and fight" branch | − | − | +1 | − | − | − | − | − |
| Flee from combat with weaker enemies | Combat-end "ye flee" branch on advantage | − | − | −1 | − | − | − | − | − |
| Fulfil a stated quest | Quest-flag-setting path on completion | − | − | − | +1 | +1 | +1 | − | − |
| Default on a stated quest | Quest-fail / NPC-betrayal path | − | − | − | −1 | − | −1 | − | − |
| Donate gold at a shrine | Shrine meditation, valid offering | − | − | − | − | +1 | − | +1 | +1 |
| Recite the wrong mantra at a shrine | Shrine meditation, mantra mismatch | − | − | − | − | − | − | −1 | − |
| Meditate at the shrine of a virtue | Shrine meditation, valid mantra and offering | (varies — the shrine's own virtue gets +1) | | | | | | | |
| Use Humility | "Use H. mantra at a shrine" cycle | − | − | − | − | − | − | − | +1 |
| Boast or claim glory through dialogue | Conversation, boast keyword | − | − | − | − | − | − | − | −1 |

Characteristics of the table that are firm even where individual numbers are not:

- **Most actions adjust a single virtue.** The shrine donation is the main exception, lifting three virtues at once because giving gold is simultaneously a sacrifice, an act of spirituality (gold dedicated to a holy place), and an act of humility.
- **Attack actions target Compassion and Justice together** when the victim was non-hostile, because striking a peaceful citizen offends both the duty of care and the principle of fair conduct. Combat with an evident enemy does not adjust either.
- **Honesty adjustments are exclusively negative in normal play.** There is no "be honest" gain — one preserves Honesty by not lying. The only positive Honesty input is the chargen questionnaire's initial seed.
- **Valor swings symmetrically.** Standing one's ground gains a point; fleeing from a winnable fight loses one. The "winnable fight" test compares party HP against enemy HP at the time of flight; the threshold is not yet decompiled.

These deltas accumulate over a campaign. The thresholds the shrine handler uses to map a score to a tier verdict (Section 5) define the player-visible interpretation of the bands.

## 5. KARMA.DAT — the tier-verdict file

The data file `KARMA.DAT` (761 bytes) holds six NUL-terminated text records, each a paragraph of speech the shrine handler prints during meditation. Despite the file name, it does **not** hold numeric karma deltas — those live in code, distributed across the action handlers. `KARMA.DAT` is purely player-visible verdict text the shrine speaks back when the engine compares the relevant virtue's score against a threshold.

The six records cluster by tier, in ascending order of standing:

1. **Lowest** — addressed to an avatar who has strayed from the path of the virtue. Spoken at the floor.
2. **Low** — addressed to an avatar who has erred but is offered a chance to do better. Corrective rather than condemnatory.
3. **Middle** — the standard "you have potential" speech: seeds of greatness, not yet the practice.
4. **High** — praises the work done but flags that more remains.
5. **Highest** — declares the destiny that awaits, bids the player return to the work.
6. **Highest (variant)** — a near-duplicate of record five. Whether this is an endgame-only variant, an in-game variant at certain quest milestones, or dead text is open.

When the meditation handler needs a verdict, it computes a tier index from the avatar's score for the active virtue and prints that record. The file has no header and no offset table — records are sequentially packed, so the seek to record `n` is "skip past `n` NUL terminators". A modern reimplementation can keep the same layout or swap to a structured table without altering player-facing behaviour, since the engine's only contract is "give me the text for tier `n`".

The threshold table that maps score to tier index is **not** in `KARMA.DAT`. It lives inside the meditation handler in the spell-effects overlay (the same overlay that owns urn reading and the in-game save). A working assumption — pending decompilation — is that bands are roughly even across zero-to-ninety-nine with each tier covering twenty units; precise breakpoints are open.

## 6. Shrine meditation

The flow that exposes `KARMA.DAT` to the player is the shrine meditation handler. Meditation runs when the player presses `M` while the party is standing on one of the eight shrine tiles. The handler matches party coordinates against an eight-entry shrine table and runs:

1. **Render the kneeling avatar.** The standing tile is briefly replaced with the kneeling tile.
2. **Mantra prompt.** Prints `Mantra:` and reads up to twelve characters. The eight expected mantras are `Ahm` (Honesty), `Mu` (Compassion), `Ra` (Valor), `Beh` (Justice), `Cah` (Sacrifice), `Summ` (Honor), `Om` (Spirituality), `Lum` (Humility); matched case-insensitively.
3. **Wrong mantra.** A "no effect" message prints and meditation ends. The avatar's score may be lightly penalised (working hypothesis: minus one to Spirituality) for the false attempt; not yet confirmed.
4. **Right mantra.** Prints `ALAKAZAM` and prompts for a gold offering. The player types a single decimal digit; the donation is `digit × 100` gold. Insufficient gold or a zero entry aborts.
5. **Apply the boost.** On a valid offering, prints the verdict speech (one of the six `KARMA.DAT` records, picked by tier from the avatar's current score for that shrine's virtue), increments strength, dexterity, or intelligence on the active player by one (the stat depends on the shrine), increments the relevant virtue's counter, and sets the corresponding "ordained" bit if a shrine quest completes.
6. **Restore the standing tile.** Control returns to the field-mode loop.

The meditation handler does not gate access to the shrine on a karma threshold. Any avatar may approach, recite the mantra, donate gold, and receive both a stat point and a verdict. The avatar's standing affects only the verdict speech, not the mechanical reward. (The "ordained" bitmask gates whether the shrine accepts the player as worthy of a quest, but that is a quest flag, not a karma test.)

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

This decoupling matters: in Ultima V, the avatar's karma scores are independent of class and may evolve in any direction. Companion stats and abilities reflect their class but are not adjusted by karma at runtime.

## 8. Endgame karma and quest gating

The endgame is gated not on karma scores themselves but on quest flags that record progress along each virtue path. Three permanent records are checked:

- **The "ordained" bitmask.** All eight bits set when the avatar has completed every shrine's ordainment ceremony. Each ceremony requires returning to the shrine after collecting the relevant rune, reciting the mantra, completing the meditation flow, and (in some shrines) demonstrating a karma score above a threshold. Exact requirements per shrine are open.
- **The "Codex visited" bitmask.** All eight bits set when every Codex page has been read in sequence. Codex pages are revealed by the endgame sequence rather than during regular play, so this is set late.
- **Side-quest completion flags.** Scattered through the save image; each major virtue arc sets its own flag on completion. Lord British's endgame dialogue reads these; if any are unset, the dialogue substitutes a "you are not yet ready" branch instead of the box-opening sequence.

Karma scores feed in indirectly. Several virtue quests cannot be completed without a high score in the relevant virtue — an NPC may refuse to give a quest item until Compassion is above a threshold, so karma gates the quest flag rather than the endgame directly. The meditation verdict at the highest tier reflects that the avatar is on track; the variant at record six is plausibly an endgame-only variant printed after Lord British's box is opened.

The endgame reads quest flags, not karma, but a player who never raises their karma will hit walls earlier in the quest tree.

## 9. NPC dialogue gating

Some NPC conversation branches are gated on karma. The conversation overlay reads the active virtue's score and selects a response based on whether it is above or below a threshold. Observed examples:

- **Sage rumours.** The sage shop's rumour branch reads karma to decide whether the rumour given is accurate or misleading. Low-karma players receive less helpful rumours; high-karma players may receive rumours pointing at quest items or NPC locations.
- **Healer service.** Healers do not modulate prices on karma (pricing is fixed per shop instance), but dialogue may choose between a friendly cure and a colder one based on Compassion. Exact branch behaviour is open.
- **Begging response.** When the player uses "give" on a beggar, the response varies on Compassion: high-Compassion avatars receive a thankful response, low-Compassion ones a suspicious one.
- **NPC service refusal.** Certain NPCs refuse to deal with avatars whose karma in a virtue is too low. The refusal is dialogue-only; no guard alarm or criminal flag is set, so the practical effect is that the player seeks the same service elsewhere.

These branches are scattered across the conversation overlay (TALK.OVL) and the shop overlays (SHOPPES.OVL and siblings). There is no central NPC karma gate; each branch implements its own threshold.

Shop pricing in Ultima V is **not** karma-modulated. The base price for a sword is the same regardless of standing; karma affects dialogue and rumour quality, not gold cost.

## 10. Open questions

- **Per-action delta magnitudes.** The deltas in Section 4 are best-guess values aligned with Ultima IV conventions and observed Ultima V dialogue. Each delta is hardcoded in the handler that owns the action; pinning down precise numbers requires per-handler decompilation. The shape of the table (which virtues each action touches, sign of the delta) is more confident than the magnitudes.

- **Karma byte layout.** Whether the eight scores are eight contiguous bytes, or whether the engine maintains them differently, is unconfirmed. The conservative model is "eight bytes adjacent at a fixed save offset"; actual layout will emerge from decompilation of the meditation handler's read site and any action handler's write sites.

- **Tier threshold values.** The score-to-tier mapping is in code, not data, and has not been decompiled. Working assumption: roughly twenty-unit bands across zero-to-ninety-nine. Whether breakpoints vary per virtue is open.

- **The duplicate top-tier verdict.** Two near-identical records at the top of the tier ladder. Whether one is an endgame-only variant, dead text, or both reachable will be settled by tracing the meditation handler's record-index computation.

- **Whether meditation itself adjusts karma.** A successful meditation increments a stat and sets the ordainment bit; whether it also increments the virtue's score is unconfirmed. A failed meditation plausibly decrements Spirituality, but this is unverified.

- **Combat karma branches.** The "attack non-hostile" path is the most karma-rich combat case; exact deltas (how much Compassion lost, whether Justice is also lost, scaling on victim status) are open until the combat handler is decompiled deeply.

- **Endgame karma checks.** Whether Lord British's endgame reads any per-virtue score (as opposed to only quest flags) is open. The simplest model — quest flags only — is consistent with the notes but not confirmed.

- **Karma in the chargen seed.** Whether the engine writes initial karma values matching the questionnaire's stat tallies, or whether all virtues start at a neutral midpoint, is open. `INIT.GAM` contains the answer.

- **Whether karma ever overflows.** A byte permits up to two hundred fifty-five; a saturating add would clamp to ninety-nine, a naive add would not. Empirical verification by repeated shrine donation would expose the clamp.

## 11. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions and format dissections in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, byte-level structure tables, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The shrine meditation flow (mantra prompt, gold offering, stat boost, ordainment bit, verdict dispatch, kneeling-tile animation) — derived from `u5-decomp/functions/CAST2_OVL/0x0966_shrine_meditate.md`.
- The `KARMA.DAT` six-record tier-verdict layout, the lack of numeric deltas in the file, and the duplicate top-tier record — derived from `u5-decomp/formats/data-tables.md` (`KARMA.DAT` section).
- The eight per-virtue counters and their save-image membership — derived from `u5-decomp/formats/saves.md` and `u5-decomp/formats/ds-bss-map.md` (tentative karma byte adjacent to the gold word).
- The ordained / Codex visited bitmasks following the inventory section — derived from `u5-decomp/formats/saves.md` (shrine quest progress region).
- The eight-virtue ordering, per-virtue mantra and prefix tables — derived from `u5-decomp/formats/data-ovl.md` and the shrine handler note.
- The chargen-time seeding of stat tallies and the lack of avatar-class write — derived from `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` and `u5-decomp/functions/FONT_OVL/0x09C8_questionnaire_iter.md`.
- The shop pricing model (fixed, not karma-modulated) and sage rumour-quality branch — derived from `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md` (Karma / reputation interactions section).
- The Blackthorn audience flow's lack of in-overlay karma adjustment — derived from `u5-decomp/functions/BLCKTHRN_OVL/OVERVIEW.md`.
- The per-companion class assignments and the avatar-as-class-Avatar invariant — derived from `u5-decomp/formats/saves.md` (character roster) and cross-checked against the shrine handler note.
- The MISCMSG.DAT virtue-aphorism and "failing of virtue" record clusters printed during meditation and certain dialogue branches — derived from `u5-decomp/formats/data-tables.md` (MISCMSG.DAT section, records twelve through twenty-seven).
