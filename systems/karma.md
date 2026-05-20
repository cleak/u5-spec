# Karma

## 1. Overview

Karma is Britannia's measure of the avatar's moral standing across the eight virtues. The shrine and Codex quest paths are virtue-specific, and the text that presents those paths names the active virtue. The traced numeric standing used by verdict, threshold, and penalty paths is a shared capped selector, not a confirmed eight-score runtime table.

The cleanroom model should therefore expose the eight virtue quest paths and the
shared moral-standing selector as separate concepts. The save image confirms two
per-virtue quest masks and one capped scalar standing/progression byte used by
the traced verdict, shrine, conversation-threshold, resurrection-penalty, and
selected action paths. A full per-virtue numeric standing layout has not been
identified in the traced save image or current BSS writer census.

Adjustments are spread across the owning action handlers rather than through a
central karma manager. The public contract lists only traced scalar writes and
explicit negative boundaries; do not infer extra per-virtue deltas from manual
expectations, visible warnings, or dialogue text alone.

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

The eight virtues sit alongside three "principles" (Truth, Love, Courage) and
an eighth-virtue meta-principle. The principles are referenced indirectly by
the mantras at certain shrines and by the Codex narrative. The traced runtime
state does not expose them as separate numeric standing axes.

## 3. Karma storage

The storage picture has two confidence levels.

The save image carries two adjacent bitmask bytes recording per-shrine quest progress: an "ordained" mask and a "Codex visited" mask. They are quest flags, not karma scores. For each virtue, the pair encodes not started, ordained, Codex-read, or complete. `formats/saved-gam.md` gives the byte offsets and bit order.

The shrine meditation handler updates the shared moral-standing selector. Shrine
increases clamp to ninety-nine: a completed-shrine gold offering adds the
offered digit, a Codex turn-in adds three, and the Humility turn-in adds another
three. The Blackthorn rescue/refuge path consumes the same one-byte selector and
clamps it upward after printing, while the Lord British-in-disguise camp event
consumes the same tier scale with a different top-band text choice.

That selector is persisted at save offset `0x02E2`. It is a gameplay field, not
a text-resource field and not a food counter. The action paths traced so far use
it as a scalar moral-standing/progression byte. This does not prove a complete
per-virtue numeric layout; keep the per-virtue shrine quest masks separate from
the scalar selector. Unknown saved bytes in nearby mixed-state regions should
be preserved as opaque state unless another owning system names them.

One older private hypothesis placed karma in the byte immediately after the
low byte of the party gold counter. That candidate is ruled out for the public
spec: the current save-format and inventory traces identify the two-byte word
at `0x0204..0x0205` as party gold. Do not treat the high byte of gold as a
standing value, and do not infer a karma layout from that location.

## 4. Karma-adjusting actions

The engine adjusts moral standing in response to specific player actions. Each
action's delta is hardcoded into the handler that processes it; there is no
central data table of action-to-karma effects. Confirmed scalar changes are
listed below. Some rows still identify likely virtue relationships for game
design purposes, but the traced persistent field is the shared selector unless
a separate per-virtue writer is later identified.

Confirmed shrine-handler standing changes:

| Action | Trigger | Standing effect |
|---|---|---|
| Complete-shrine gold offering | Shrine meditation after the virtue quest is already complete | Shared moral-standing selector + offered digit, for digits one through nine; clamps at ninety-nine |
| Codex shrine turn-in | Shrine meditation after the Codex page has been read while the ordained bit is still set | Shared moral-standing selector +3, clamped at ninety-nine; Humility receives an additional +3 |
| Recite the wrong mantra at a shrine | Shrine meditation mantra mismatch | No confirmed standing change |

Confirmed non-shrine scalar changes:

| Action | Trigger | Standing effect |
|---|---|---|
| Town-family chest opening | Opening a matching surface/town object-table chest | Shared moral-standing selector -2, floored at zero |
| Crop or table-food taking | Picking crop cells or eating reachable table food | Shared moral-standing selector -1 when nonzero |
| Town-family cannon hit | F-Fire local cannon path after a successful active-object hit | Shared moral-standing selector -5, floored at zero |
| Helped/pickpocket-style NPC thank-you path | Jimmy/NPC path that reaches the thankful response | Shared moral-standing selector +2, capped at ninety-nine |
| Toll-style gold-payment milestone | Three-digit conversation gold payment when the toll-progress counter has reached its milestone | Shared moral-standing selector +1, capped at ninety-nine; if the payment leaves the party with zero gold, add another +2 under the same cap |

The toll-progress counter is a single saved byte adjacent to the shared moral-standing selector (`SAVED.GAM 0x02E5`, in the same per-turn cluster as the selector at `0x02E2`). Every successful three-digit `0x85` gold payment increments this counter by one. When the counter reaches `100`, the gold-payment helper resets it to zero and applies the standing bump above. This means the milestone fires once per hundred successful payments rather than once per payment.

The counter is not specific to "tolls" versus "bribes" or "donations": the public TLK control byte family does not distinguish payment intent, and every accepted three-digit `0x85` payment routes through the same helper and the same counter. The semantic naming as "toll" reflects the most common shipped use of the byte; bribes and donations also count toward the milestone. The reset/bump path is the only traced writer for the counter. New games seed the counter at zero from the factory save image; nothing else writes it.

The "if the payment leaves the party with zero gold, add another +2" leg is a separate post-debit test inside the same helper. It fires on every paid `0x85` whose debit clears party gold to zero, regardless of whether the milestone reset also fired on the same call. Both clamps share the same ninety-nine cap on the shared selector.

Negative boundaries for unpromoted action families:

| Action family | Likely trigger | Public status |
|---|---|---|
| Theft or dishonest object action | Field object, shop, or conversation side-effect path | Town-family chests, crops, table food, and cannon hits have confirmed scalar penalties; the traced borrowed-furniture Get branch mutates the tile and plays feedback without a confirmed selector debit. TALK can display stolen-action warnings and run presentation/transient-signal cleanup, but those warnings are not the scalar writer. |
| False dialogue answer | Conversation keyword path with a known-false answer | No traced direct scalar or per-virtue writer is promoted from the decoded conversation runner. |
| Profanity at the conversation prompt | Conversation reserved-keyword table default/rebuke branch | Rebuke and bounded pause/timing behavior confirmed; no direct virtue-standing write confirmed in the decoded branch |
| Refusing requested aid | Conversation refusal branch | No separate traced writer is promoted. Branch text may express virtue judgement without proving a runtime standing delta. |
| Giving to a needy NPC | Conversation "give" path with gold or food | The traced three-digit conversation gold-payment control byte debits party gold and has a toll-milestone scalar selector bump, but it is not itself a per-virtue Compassion writer. Do not turn every conversation gold debit into a charity-karma delta. |
| Third-party healing | Healer shop or dialogue path for curing a stranger | Shop treatment costs and no-price exceptions are shop/town-scene rules. No karma-owned healer price or standing writer is promoted. |
| Attacking a non-hostile NPC | Combat-mode strike on a peaceful or friendly actor | No combat-overlay write to the scalar selector or a per-virtue standing byte is promoted in the current census. Town-family cannon hits are the covered hostile/destructive scalar penalty. |
| Initiating or refusing combat | Combat engagement or combat-end stay-and-fight branch | Combat framer, ordinary combat exit, reward, and flee paths have no traced post-combat virtue delta. |
| Fleeing a winnable combat | Combat-end flee branch while advantaged | No scalar or per-virtue writer is promoted from the traced flee/exit paths. |
| Completing or defaulting on a stated quest | Quest-flag-setting, quest-fail, or betrayal branch | Quest flags are owned by their quest systems. A flag mutation is not automatically a standing mutation. |
| Boasting or claiming glory | Conversation boast branch | No separate traced scalar or per-virtue writer is promoted from decoded conversation control flow. |

Characteristics that are firm even where non-shrine magnitudes are not:

- **Shrine offerings are not stat rewards.** They consume party gold and raise the shared moral-standing selector only after that virtue's shrine quest is already complete.
- **Shrine quest turn-in is the stat reward.** Returning after the Codex page clears the ordained bit, raises the shared selector, and may increment Avatar stats according to the shrine stat table in Section 7.
- **Attack and flee karma are not inferred.** Striking peaceful citizens or
  fleeing combat may be judged by dialogue or by the player-facing fiction, but
  the traced combat and town attack paths do not publish a separate virtue delta
  beyond the confirmed cannon-hit scalar penalty.
- **Profanity is not currently a confirmed karma mutator.** The reserved-keyword default branch prints its chastisement and repeatedly invokes a resident timing/presentation helper after a pause. The wrapped helper target is not a stats-panel or virtue-standing writer, so the public contract should not model profanity as a standing change unless a separate producer is traced.
- **Conversation gold demands are not automatically Compassion changes.** The
  traced three-digit gold-payment control byte decodes a demanded amount,
  debits party gold on success, and can raise the shared moral-standing
  selector when the toll-progress counter has reached its milestone. It does
  not write a per-virtue Compassion standing in that helper. Any positive
  Compassion effect for charitable giving must be traced in a separate action
  branch rather than inferred from every conversation gold debit.
- **Stolen-action warnings are not themselves the Honesty delta.** TALK entry
  can print a stolen-action warning when the active scene/NPC and shared
  stolen-action status match, and final cleanup can print a matching warning,
  play the fixed presentation sound, reconcile one-shot conversation signals,
  or refresh the gold panel. The visible warning text, sound, and cleanup
  envelope do not by themselves identify the per-virtue standing byte, delta
  magnitude, or clamp policy. The warning sound is a pure PC-speaker glissando,
  not a hidden standing writer. No direct scalar or per-virtue standing write is
  promoted from those warning paths.

These deltas accumulate over a campaign in the shared selector. The verdict
consumers that load `KARMA.DAT` use twenty-point bands for player-visible moral
interpretation, but shrine meditation itself does not print those verdict
records.

## 5. Standing Consumers

The scalar selector is read by several systems in addition to the writers above:

- **Blackthorn rescue/refuge verdict.** Selects one of five `KARMA.DAT` verdict
  bands, then raises the selector to at least seventy-five.
- **Lord British-in-disguise camp event.** Selects a `KARMA.DAT` verdict band,
  using the sixth text record for the top band.
- **Conversation thresholds.** The TALK bytecode threshold branch compares a
  staged threshold against the scalar selector and conditionally jumps to a
  label. The traced branch reads the scalar selector; it does not read an
  eight-entry per-virtue score array.
- **Resurrection penalty.** Resurrection checks the scalar selector. If it is
  below ninety-eight, the revived member's experience is scaled down by the
  selector percentage; at ninety-eight or higher, this penalty is skipped.

## 6. KARMA.DAT — the tier-verdict file

The data file `KARMA.DAT` (761 bytes) holds six NUL-terminated text records, each a paragraph of verdict speech. Despite the file name, it does **not** hold numeric karma deltas; those live in code, distributed across the action handlers. `KARMA.DAT` is player-visible text selected by presentation paths after the engine has already computed a moral-standing tier.

The six records cluster by tier, in ascending order of standing:

1. **Lowest** - addressed to an avatar who has strayed from the path of the virtue. Spoken at the floor.
2. **Low** - addressed to an avatar who has erred but is offered a chance to do better. Corrective rather than condemnatory.
3. **Middle** - the standard "you have potential" speech: seeds of greatness, not yet the practice.
4. **High** - praises the work done but flags that more remains.
5. **Highest** - declares the destiny that awaits, bids the player return to the work.
6. **Highest (camp-event variant)** - a shorter near-variant of record five, reached by the Lord British-in-disguise camp event's top band.

The confirmed Blackthorn rescue/refuge selector maps its one-byte verdict input into five bands: zero through nineteen selects record zero, twenty through thirty-nine selects record one, forty through fifty-nine selects record two, sixty through seventy-nine selects record three, and eighty through ninety-nine selects record four. After the rescue path prints its selected record, it raises that selector to at least seventy-five if it was lower.

The confirmed Lord British-in-disguise camp selector uses the same twenty-point scale for lower values but has a different top-band choice: values below eighty select records zero through three, while values eighty and above select record five. That camp event does not select record four.

The file has no header and no offset table; records are sequentially packed, so the seek to record `n` is "skip past `n` NUL terminators". A modern reimplementation can keep the same layout or swap to a structured table without altering player-facing behaviour, since the engine's only contract is "give me the text for tier `n`".

The live shrine meditation handler does not load `KARMA.DAT` in the traced CAST2 path. Shrine meditation uses shrine-local prompt/response text and `MISCMSG.DAT` for the urn/Codex prophecy path; its mechanical state machine updates and clamps the shared moral-standing selector without printing these verdict records.

## 7. Shrine meditation

Meditation runs when the player presses `M` while the party is standing on one of the shrine coordinates. The handler matches the party position to the shrine table, renders the kneeling avatar tile, prompts for a mantra, and reads up to twelve characters.

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
| 1 | 1 | Codex-read turn-in | Clears the ordained bit, adds three to the shared moral-standing selector, clamps at ninety-nine, and applies the stat rewards below. Humility adds another three standing after the stat step. |
| 0 | 1 | Complete | Runs the ordinary offering path. A digit one through nine costs `digit * 100` gold and adds that digit to the shared moral-standing selector, clamped at ninety-nine. Digit zero is a no-effect exit. If the party lacks enough gold, the prompt repeats. |

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

The meditation handler does not require a minimum standing to run. The mechanical state transitions are governed by the ordained and Codex bit pair. No traced shrine-side `KARMA.DAT` verdict speech selection participates in this branch.

The shrine/word presentation primitive is a visual-and-audio effect, not a
quest-state mutator by itself. The traced resident helper produces a turbulent
full-viewport flash paired with a low, randomized PC-speaker rumble, then
returns with no direct save-state writes. It is confirmed as the feedback used
by the Word-of-Power path in `commands.md` and by the older unreachable
CMDS-side shrine-restoration branch. The live CAST2 shrine meditation handler
owns the actual shrine quest-state changes above; whether every successful
live shrine branch also calls this exact resident presentation helper remains a
presentation-parity verification item, not a different shrine-state machine.

Blackthorn rescue/refuge handling reuses `KARMA.DAT` as verdict text, but
the Blackthorn overlay does not make the file a numeric karma table and does
not publish a traced in-overlay virtue-score adjustment before selection. See
`systems/blackthorn.md`.

## 8. Codex Urn Reading

The same `M` command family also owns the Codex urn interaction. When the party
kneels on the urn/Codex special tile instead of an ordinary virtue shrine, the
handler suspends the normal active-object presentation, loads the Codex message
cluster, and dispatches to the urn reader rather than the shrine-mantra flow.
The saved scene and active-object state are restored afterward and the screen is
fully redrawn.

Urn reading is gated by the ordained mask set at the virtue shrines. The reader
walks the eight virtues in the standard virtue order and considers only virtues
whose ordained bit is set. For the selected ordained virtue, the reader sets the
matching Codex-read bit and displays that virtue's prophecy/Codex text. If all
Codex-read bits are already set, the reader takes its completed branch instead
of stamping another virtue.

This is the middle state in the shrine quest cycle:

1. Correct shrine mantra at a not-started shrine sets the ordained bit.
2. Reading the corresponding Codex urn/page sets the Codex-read bit.
3. Returning to the shrine with both bits set clears the ordained bit, applies
   the virtue's stat/standing reward, and leaves the Codex-read bit as the
   durable completed marker.

The urn text is supplied by `MISCMSG.DAT`; the file format spec owns the record
cluster, while this spec owns the quest-bit transition.

## 9. Virtue-to-class linkage and the avatar's class

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

## 10. Endgame karma and quest gating

The endgame is gated primarily by quest flags, not by fluctuating virtue standing itself. The two shrine masks encode a four-state path per virtue:

| Ordained bit | Codex bit | State |
|---:|---:|---|
| 0 | 0 | Not started |
| 1 | 0 | Ordained, must visit the Codex |
| 1 | 1 | Codex page read, must return to the shrine |
| 0 | 1 | Complete |

The shrine turn-in transition is important: returning after the Codex page clears the ordained bit and leaves the Codex bit set. Therefore "all virtues complete" is represented by all Codex bits set and all ordained bits clear, not by an all-set ordained mask.

Side-quest completion flags are scattered through the save image; each major
virtue arc sets its own flag on completion. The traced endgame overlay branch
checks the saved Sandalwood Box completion flag together with the visible final
confirmation answer; if either gate fails, it enters the non-victory ending
tableau rather than the certificate path. No per-virtue karma-standing read is
currently traced inside the endgame overlay. Karma standings may still gate
earlier NPC or quest interactions indirectly, but the shrine meditation handler
itself uses quest-mask state rather than a standing threshold to decide its
mechanical branch.

## 11. NPC dialogue gating

Some NPC conversation branches are gated on moral standing. The traced
conversation bytecode threshold branch compares the shared scalar selector to a
staged threshold and selects a response label. This is moral-standing gating,
not proof of a separate active-virtue numeric array. Observed examples and
negative boundaries:

- **Healer service.** Healers do not modulate prices on karma; the treatment tables determine ordinary costs, and the Minoc / The Healers Mission Cure/Heal no-price branch is keyed to town-scene identity rather than virtue standing. Current shop evidence does not show a karma-owned healer price or treatment-text branch.
- **Begging or gift responses.** Conversation text can vary by moral-standing
  threshold, and gold-payment control bytes can debit party gold. Only the
  toll-milestone scalar bump is promoted as a traced standing write.
- **NPC service refusal.** Certain NPCs can refuse to deal with low-standing
  avatars through dialogue labels. The refusal is dialogue-only; no guard alarm
  or criminal flag is set by the threshold branch itself.

These branches are scattered across the conversation overlay (TALK.OVL) and
data-authored dialogue labels. There is no central NPC karma gate; each branch
implements its own threshold. The sage rumour shop path is not listed as a
karma-gated branch: the decoded shop flow is a topic, fee, destination, and
template lookup.

Shop pricing in Ultima V is **not** karma-modulated. Arms purchases do have a decoded speaking-member Intelligence adjustment, but karma standing does not change gold cost. Karma affects some dialogue branches and virtue outcomes, not price tags.

## 12. Karma Boundaries

The public karma contract is complete for the traced baseline at moral-standing
system depth: shrine meditation, Codex return, the save-backed scalar selector,
`KARMA.DAT` verdict text, Blackthorn rescue/refuge selection, Lord
British-in-disguise camp-event selection, resurrection penalty consumption,
conversation threshold reads, selected non-shrine scalar deltas, conversation
profanity/default negative boundary, conversation gold-payment boundary,
stolen-action warning boundary, combat-exit negative boundary, and shop-pricing
negative boundary are covered.

- **Future action writers.** If later analysis finds another explicit writer,
  add it to Section 4 with its own trigger, sign, magnitude, and clamp/floor
  rule. Do not model untraced manual-facing virtue expectations as runtime
  deltas. `KARMA.DAT` cannot answer this because it only stores verdict text.
- **Conversation profanity boundary.** The reserved-keyword default branch is
  confirmed as a rebuke plus repeated pause/timing path, not as a direct
  standing writer. If profanity has a karma effect, it must be found in a
  separate cleanup or signal path rather than inferred from the presentation
  helper call.
- **Conversation gold-payment boundary.** The traced three-digit
  gold-payment control byte belongs to conversation/quest payment handling:
  it debits party gold and can raise the shared moral-standing selector on a
  toll-progress milestone, but no per-virtue standing write is present in that
  helper. Charitable-giving karma, if any, must be found in a different action
  path.
- **Stolen-action warning boundary.** Conversation entry can recognize a
  previously stolen-action state for the addressed NPC and print the warning
  before the normal greeting. Final conversation cleanup can also print the
  warning and perform presentation/transient-signal/gold-panel cleanup. Neither
  visible TALK branch is enough to publish an Honesty delta; no direct scalar
  or per-virtue standing write is promoted from those warning paths.
- **Karma byte layout.** Save offset `0x02E2` is the traced scalar
  moral-standing selector. It is raised by shrine paths, consumed by the
  Blackthorn and Lord British-in-disguise verdict paths, and changed by several
  non-shrine actions. The party-gold word in the inventory band is not a karma
  field. No separate per-virtue numeric save layout is promoted for the traced
  baseline; preserve unknown neighbouring bytes as opaque owner-specific state.
- **Combat-action karma branches.** The combat framer and ordinary encounter
  exit path do not apply a post-combat virtue delta. Current traced combat
  command and exit coverage does not promote a scalar or per-virtue standing
  writer for ordinary attack, victory, or flee outcomes.
- **Initial standing seed.** The scalar selector is seeded by the factory save
  image and preserved by character creation except for normal gameplay
  mutations. No character-creation path derives a new scalar or per-virtue
  standing layout from the questionnaire in the traced baseline.

## 13. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The shrine meditation flow (mantra prompt, quest-mask state machine, post-completion offering path, Codex-turn-in reward table, standing clamp, and kneeling-tile animation) — derived from `u5-decomp/functions/CAST2_OVL/0x0966_shrine_meditate.md` and the local CAST2 shrine-handler trace.
- The shared shrine/word presentation effect boundary -- low randomized rumble
  plus turbulent viewport flash, no direct quest-state mutation -- derived from
  `u5-decomp/functions/CMDS_OVL/0x70F2_shrine_effect.md` and cross-checked
  against the Word-of-Power path in `systems/commands.md`.
- The M-command shrine/urn dispatcher and urn reader's Codex-read bit stamping,
  prophecy display, completed branch, active-object suspension, and restore/redraw
  wrapper -- derived from
  `u5-decomp/functions/CAST2_OVL/0x0E76_enter_shrine_or_urn.md` and
  `u5-decomp/functions/CAST2_OVL/0x0D24_read_urn.md`.
- The `KARMA.DAT` six-record tier-verdict layout, the lack of numeric deltas in the file, the Blackthorn five-band selector, and the Lord British-in-disguise camp-event top-band selector for the sixth record — derived from `u5-decomp/formats/data-tables.md` (`KARMA.DAT` section), `u5-decomp/functions/BLCKTHRN_OVL/0x0910_blackthorn_rescue.md`, and `u5-decomp/functions/OUTSUBS_OVL/0x0658_lord_british_dialogue.md`.
- The save-backed scalar moral-standing selector, shrine standing adjustments,
  Blackthorn rescue selector, Lord British-in-disguise selector, ruled-out
  party-gold high-byte hypothesis, and broader per-virtue storage
  boundary -- derived from `u5-decomp/formats/saves.md`,
  `u5-decomp/formats/ds-bss-map.md`,
  `u5-decomp/notes/system-trace_inventory.md`, the shrine handler,
  `u5-decomp/functions/BLCKTHRN_OVL/0x0910_blackthorn_rescue.md`, and
  `u5-decomp/functions/OUTSUBS_OVL/0x0658_lord_british_dialogue.md`.
- The ordained / Codex visited bitmasks following the inventory section — derived from `u5-decomp/formats/saves.md` (shrine quest progress region).
- The eight-virtue ordering, per-virtue mantra and prefix tables — derived from `u5-decomp/formats/data-ovl.md` and the shrine handler note.
- The chargen-time seeding of stat tallies and the lack of avatar-class write — derived from `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md` and `u5-decomp/functions/FONT_OVL/0x09C8_questionnaire_iter.md`.
- The shop pricing model (not karma-modulated, with arms Intelligence adjustment handled in the shop spec) — derived from `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md` (Karma / reputation interactions section).
- The sage topic/fee/destination/template path, and the absence of a confirmed sage-shop karma selector — derived from `u5-decomp/functions/SHOPPES2_OVL/0x0508_sage_main.md`.
- The conversation profanity/default reserved-keyword rebuke and negative karma-write boundary -- derived from `u5-decomp/functions/TALK_OVL/0x0A54_ask_party_join_logic.md`, `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`, and `u5-decomp/functions/ULTIMA_EXE/0x20FA_delay_with_int1c.md`, and cross-checked against `u5-decomp/CORRECTIONS.md`.
- The conversation gold-payment toll/scalar boundary -- derived from
  `u5-decomp/functions/TALK_OVL/0x05B6_process_gold_payment.md` and
  `u5-decomp/functions/TALK_OVL/0x0DBE_multi_byte_command_handler.md`.
- The TALK moral-standing threshold branch -- derived from
  `u5-decomp/functions/TALK_OVL/0x0DBE_multi_byte_command_handler.md` and
  `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`.
- The resurrection moral-standing XP penalty -- derived from
  `u5-decomp/functions/CAST2_OVL/0x05E0_resurrect_member.md`.
- The Get-side object-taking scalar boundaries -- town-family chest debit,
  crop/table-food debit, and borrowed-furniture no-debit behavior -- are
  derived from `u5-decomp/functions/SJOG_OVL/0x112C_sjog_inner_chest_open.md`,
  `u5-decomp/functions/SJOG_OVL/0x18CE_sjog_get.md`, and
  `u5-decomp/notes/system-trace_object-interaction.md`.
- The stolen-action warning and no-promoted-standing-writer boundary --
  derived from `u5-decomp/functions/TALK_OVL/0x111C_init_check_for_steal.md`
  and `u5-decomp/functions/TALK_OVL/0x1180_final_conversation_cleanup.md`,
  with the presentation-sound boundary cross-checked against
  `u5-decomp/functions/ULTIMA_EXE/0x43AE_pc_speaker_glissando.md`.
- The Blackthorn audience flow's lack of in-overlay karma adjustment and the rescue/refuge `KARMA.DAT` reuse — derived from `u5-decomp/functions/BLCKTHRN_OVL/OVERVIEW.md` and summarized in `systems/blackthorn.md`.
- The per-companion class assignments and the avatar-as-class-Avatar invariant — derived from `u5-decomp/formats/saves.md` (character roster) and cross-checked against the shrine handler note.
- The MISCMSG.DAT virtue-aphorism and "failing of virtue" record clusters printed during meditation and certain dialogue branches — derived from `u5-decomp/formats/data-tables.md` (MISCMSG.DAT section, records twelve through twenty-seven).
