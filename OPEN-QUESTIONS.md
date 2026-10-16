# Open Questions

This file indexes every statement in this repository that is published as
**open, unverified, inferred or disputed**, so that a consumer can find the soft
edges of the contract without reading eighty-six documents, and so that the next
analysis pass has a queue rather than a search. It is the forward-looking
complement of `RETRACTIONS.md`, which records what was withdrawn.

Two rules govern what belongs here:

- **An entry is a gap in the evidence, not a gap in the prose.** Each row names
  a claim the owning document already flags in place. If a document is merely
  silent on something, that is inventory work for `EXTRACTION.md`, not an open
  question.
- **Each row says what would settle it.** The kinds are: `owner` (a decision
  for the repository owner, not an analyst), `capture` (an emulator run or a
  measurement on real hardware; static tracing cannot settle it), `trace` (a
  further static trace of the shipped program; settleable without a live run)
  and `scope` (deliberately outside the v1 target). Items are moved out of this
  file when the owning document is updated, with a `RETRACTIONS.md` row if the
  answer reverses published text.

Last reconciled: 2026-09-13. The 2026-09-05 reconciliation had closed every
`trace` item; the issue #262 Klimb and dungeon-object passes opened nine new
ones (section 3) and one new capture item (section 2), and the issue #262
text passes (Blink, moonstone bury/recover, Get/Search/eat, conversation
entry) opened eleven more trace items and one more capture item. The issue #263
monster arena-exit pass and the issue #264 U-Use shard-row pass then opened six
more trace items (section 3) and two more capture items (section 2). The issue #259
picker-overflow pass closed one of those trace items - how many items a page holds
once a row wraps - narrowed two capture items, and opened two trace items and two
capture items of its own. The issue #266 ASK-WHO pass opened one trace item and
extended one capture item. The issue #267 panel-refresh-cadence
pass opened four more trace items (section 3), and the issue #268
Blackthorn audience-exit pass opened four more trace items and two capture
items (sections 3 and 2). The issue #271 shrine-entry pacing pass then opened
four trace items (section 3) and one capture item (section 2), and extended the
calibration-threshold capture item with a second dependent. The issue #269
rescue-narration pass opened four trace items and one capture item and moved the
`Not dead!` branch to section 1 as an owner decision; the issue #270
prompt-cadence pass opened four trace items and one capture item, and the issue
#270 exit-handoff follow-up opened seven more trace items (section 3) and two
capture items (section 2). The issue #272 mixer-prompt pass then opened two
trace items (section 3) and one capture item (section 2), and extended the town
re-poll trace item with a second dependent. The issue #273 shrine-pose pass
then closed nothing and opened three trace items (section 3), and narrowed the
issue #271 item about what the compositor draws under the avatar. The issue #273
party-sprite band audit then **closed** one of those three - whether mounting
moves the party's sprite out of the `320..335` run, answered no - and opened
eight trace items (section 3) in its place. The issue #298 dungeon pass (2026-10-16) opened two capture items (section 2), and the issue #298 Blackthorn and conversation pass opened one more and narrowed a section 3 swell item. The issue #298 objects and NPC pass (2026-10-16) closed the issue #273 item on the other ten frame-script rows, and opened one capture item (section 2) and one trace item (section 3). The issue #298 magic and combat pass (2026-10-16) opened one owner item (section 1) and two trace items (section 3), narrowed the Blackthorn ambient-tick item and extended the world-tick-rate capture item. The issue #298 commands-misc pass (2026-10-16) opened one owner item (section 1), one capture item (section 2) and four trace items (section 3), and narrowed the Codex interred-party item. The issue #298 Q31 Blackthorn panel-drop pass (2026-10-16) opened three capture items (section 2). The issue #298 Q32 ship-cadence pass (2026-10-16) opened three trace items (section 3) and narrowed the section 3 item on what produces the second ship run. The issue #298 Q33 dungeon monster-step pass (2026-10-16) opened two trace items (section 3). The issue #298 Q40 town-attack pass (2026-10-16) opened one capture item (section 2) and one trace item (section 3); the issue #298 Q41-44 endgame and rescue pacing pass opened two capture items (section 2). What else
remains needs an owner decision (section 1) or a change of scope (section 4).

## 1. Owner decisions

| Item | Where | What settles it |
|---|---|---|
| Whether to rewrite shared history to purge the removed original-game screenshot, and whether to include historical provenance/author metadata cleanup. | Issue #249; `NEXT-STEPS.md` | Explicit owner scope decision and approval before rewriting and force-pushing shared history. Current-tree cleanup is already published; earlier commits still contain the image. |
| Whether a clean engine should reproduce the rescue cinematic's `Not dead!` branch or guard against reaching it. The branch is specified as executed - one line per in-party slot whose status is not Dead, between the intoned and vertigo beats - but it is unreachable in an unedited shipped save under the status-writer census, and reachable only for a roster carrying a preserved legacy Ashes status. *(Opened 2026-09-12, issue #269.)* | `systems/blackthorn.md` Section 7 | An owner decision about scope, not a byte-level question. The behaviour itself is settled. |
| Whether the two short narrative lines of the camp apparition - the level-up address `For thy valiant deeds, I shall reward thee!` and the closing `The strangely familiar old man vanishes...` - stay published. They are cinematic narrative, not interface text, though comparable fixed cinematic literals (Blackthorn, the karma walk) are already published and both are short. *(Opened 2026-10-16, issue #298 Q10.)* | `systems/rest-and-camp.md` Section 7.1 | An owner confirmation under the shipped-text policy; the alternative is a layout description with the text read from the user's own data. |
| Whether to publish the ambient minstrel tune's 53-step sequence (53 small indices into the published nine-value period palette, 40 notes and 13 rests) as numeric data, or to tell implementers to read it from the user's own shared data overlay; and to confirm that the nine-value period palette itself counts as a numeric audio recipe like the other published envelope parameters rather than as a shipped data table. *(Opened 2026-10-16, issue #298 Q16.)* | `systems/audio.md` Section 8.10 | An owner decision about shipped data, not a byte-level question. The mechanism, counts and palette are published; only the sequence is withheld. |

The shipped-text policy (how much of the game's own text this
specification reproduces) was decided on 2026-09-04: the four items outside
the interface-string justification stay as published, for the functional
reasons recorded in `EXTRACTION.md`, "Shipped-Text Policy".

## 2. Needs a live capture

| Item | Where | Notes |
|---|---|---|
| Issue #259's reported run: which picker contents produced its zero/one/two-row completion gaps. The mechanism is now closed - the picker repaints rather than scrolls, one re-render costs one strip scroll exactly when the entry beginning on the panel's last list row wraps, and the strip copy destroys the message window's top row with nothing restoring it (`systems/inventory.md` Sections 4.4/4.5/7.1, `systems/display-driver-abi.md` Section 9.5). What is left is the specific run. | `systems/inventory.md` Section 7.1 | For each reported beat, the **complete picker panel with quantities** and the **number of navigation presses**, or a standalone original-game save with exact inputs. Both are needed: press counts alone cannot produce the reported gap pattern, because the highlight parks on the fourth visible row and the first four passes of a command all show the same page and cost the same. *Narrowed 2026-09-12 (issue #259): the earlier attribution of those beats to a stock special-items inventory is withdrawn on that ground; measured cumulative-gap tables for seven inventories are published in Section 7.1 for comparison.* |
| The conversation renderer's column-dependent flush rules - a leading space dropped at column zero and a row break swallowed at column fifteen or beyond - were read but only partly exercised, because the emulation harness has no real screen state. The entry sequence, the quote-suppression rule and the column-eighteen word break are established. *Extended 2026-09-12 (issue #266): the ASK-WHO prompt and acknowledgement **row splits** published in Section 7.6 are that word-break rule applied to an executed character sequence, not a measurement of the renderer. The character sequence itself - every feed, quote and stored word, and which arm prints which - is executed and settled; only where the rows break is modelled.* | `systems/conversation.md` Sections 6, 7.6 and 9 | A capture with real cursor state through an NPC entry, a long wrapped response, and an ASK-WHO prompt answered both ways. |
| Whether the reported 0.859/0.860-second EGA major flash transfers across emulator settings or non-EGA drivers. | `systems/audio.md` Section 8.4 | Repeat the issue #219 Word-of-Power capture with recorded CPU/core/cycle settings and each selected driver. All callers share the same 1,856-band workload; equal raster execution time across drivers is not established. *Extended 2026-09-12 (issue #271 follow-up): that one reported figure now carries four further consumers - the shrine's Codex-turn-in arm once (`systems/karma.md` Section 7.2) and the Codex urn's completion beat three times (`systems/karma.md` Section 8.1) - so a mis-scaled flash mis-scales those intervals too.* |
| Where the two-row lag reported in issue #210 begins on the engine side; the original's ten-row chain and the row-adding mechanisms are published. | `systems/dungeon-mode.md` Section 8.1; `systems/save-load.md` Section 4 | The engine's own frames at the first combat prompt and the following beat. |
| Which state the reporter's Minoc session had (issue #216): an in-location seed save whose NPC records do not own the guard's object or zero its word, or a non-canonical `TOWNE.NPC`. | `systems/blackthorn.md` Section 7a; `formats/saved-gam.md` Section 12 | The seed `SAVED.GAM`, the tool that wrote it, and the asset version. |
| Whether the "nothing further is printed" negatives of the Klimb and dungeon level-change contracts hold for the *whole screen* rather than for the message window. They were established with the repaint endpoints excluded; static reachability shows the town floor reload, the resident view routine and the dungeon level-entry routine all reach the shared text primitives somewhere in their call graphs, for roster, wind-banner and dungeon-panel content, and the outdoor step-commit chain leaves two cross-overlay thunks unfollowed. | `systems/doors-and-z-transitions.md` Section 9; `systems/dungeon-mode.md` Section 13.1; `systems/commands.md` Section 5.8 | Either a raster capture of an applied Klimb and an applied dungeon level change, or execution through those repaint chains rather than around them. |
| Wall-clock durations of every PC-speaker effect. The loop structures are exact; the per-iteration cycle model that converts them to seconds is a static estimate with a stated error band. *Narrowed 2026-09-05: two blocking tones (the blocked step and the combat refusal pair) and the calibrated unit itself were measured under DOSBox and sit inside the published bands (`systems/audio.md` 7.4, 8.8, 10.1; `systems/timing.md` 7.6, 8.7). DOSBox is not cycle-accurate, so the period-hardware figure stays open.* | `systems/audio.md` Sections 5.4, 10; `systems/timing.md` | One cycle-accurate emulator run with an audio capture settles all of them at once. *Updated 2026-10-12: the Stonegate trapdoor sweep (26.4 to 26.5 s) and the Blackthorn rescue envelope sequence (11.56 s at a fixed 3000-cycle emulator setting) were captured and agree with the static model; the envelope duration is host-dependent (`systems/audio.md` Section 8.6.2).* The figure most worth checking first is now the long descent of Section 10.5. *Updated 2026-10-16 (issue #298 Q35): the first gated start/menu logo dissolve and its speaker carrier measured 2.90 s at fixed 3000 cycles and 4.55 s at fixed 1500 under DOSBox 0.74-3; its 8 to 14 s period-hardware estimate is re-scoped, not refuted, and stays open (`systems/timing.md` 5.1, `systems/audio.md` 8.6.1, R554).* |
| The audible waveform and timbre of the envelope generator. | `systems/audio.md` Section 5.4 | Same run as above. |
| Whether the mode loop or an interrupt handler drains the keyboard buffer after the whirlpool sequence. Established only by absence inside the two traced paths. | `systems/audio.md` Section 8.9 | Sail into a whirlpool once. |
| The per-tone install cost used by the calibrated-wait model (17.4 inner units derived, against a fitted 12). | `systems/timing.md` Section 7.6, item 9 | A measured tone on the reference machine class. |
| The per-step wall clock of the publisher flourish, published as a calibration-derived target rather than a measurement. | `systems/timing.md`; `systems/intro.md` | Frame-timed capture of the intro. |
| Period-hardware wall clocks of the later intro phases: the subtitle ignition's host-speed-dependent per-position work, the start/menu `ULTIMA` archive load and unpack that keeps the finished composition visible, and the automatic preview's tile-archive start-up after an aborted ignition. Each is published only as an emulator timing at fixed 3000 and 1500 cycles. *Opened 2026-10-16 (issue #298 Q36, Q37, Q39).* | `systems/intro.md` Sections 3 and 5; `systems/timing.md` Section 5.1 | A cycle-accurate run or real 4.77 MHz EGA hardware with a frame-timed capture of the intro. |
| The intro title ink reported as "pale yellow" by observation, where both the code path and the shipped palette say white. | `systems/intro.md` | Capture on period hardware or a palette-faithful emulator. |
| The world-tick rate, and therefore every wall-clock statement derived from per-tick cadence: the autonomous wind-drift interval and the decay time of the twelve-hour save byte. *Extended 2026-10-16 (issue #298 Q16): the ambient scenery tick's clock tick-tock tempo and hour-chime spacing (`systems/audio.md` Section 8.10) are per-call too, so a timed capture beside a town grandfather clock would settle them with the rest.* | `systems/weather.md` Section 2.1; `formats/saved-gam.md` Section 5 | Time the idle loop once. |
| Whether the active-object animator runs during dungeon and combat *play* (it runs on dungeon entry). Matters because the dungeon overlay reuses two table records as scratch. | `systems/active-objects.md` Section 13; `systems/npc-schedules.md` Section 12 | Observe frame changes in a dungeon and an arena. |
| What the compositor's neighbouring-row probe reads at arena rows 0 and 10, where it reaches outside the arena record. Published as residue with a recommended engine behaviour of *no match*. | `systems/visibility.md` Section 8.5 | Read the byte in a running game; no shipped arena can act on it. |
| The visual appearance of the ship broadside burst and the dragon-breath spark cloud along a projectile line. | `systems/overworld.md` Section 6.2.6 | Screen capture during either attack. |
| That Lord British has no throne-room conversation. Every static search supports it (no roster entry, no dialogue strings); a live check would close it definitively. | `systems/conversation.md`; `catalogs/npc-roster.md` | Talk to him in the throne room. |
| Tile-id partition boundaries for water, mountain, lava and door classes against runtime behaviour, if independent re-authored data is ever the goal. | `catalogs/tile-catalog.md` Section 16, item 8 | Optional; movement contracts already own passability. |
| What the display driver paints from a wrapped picker row. The character stream is now fully measured - which entries wrap, at which quantity widths, and the two resulting shapes (the word moved whole onto the next display line over the left rule, or a label ending on the window's last writable cell, over the right rule and into screen column 39) - but no raster was captured, and the glyph blitter and several resident graphics helpers remain returns-only endpoints whose call arguments were censused rather than executed. | `systems/inventory.md` Section 4.5; `systems/text-output.md` Section 6 | A raster capture of a `U`-Use picker holding a counted shard row, reconciled with the published glyph contract rather than asserted from the character stream. *Narrowed 2026-09-12 (issue #259): 1,562 single-row renders settle which rows wrap and how many entries a page then holds; only the pixels are open.* |
| The value of the active-object solidity marker for arena monsters, which decides whether an actor's own cell refuses its own zero-displacement step and therefore how the surrounded predicate reads. It was taken from the arena seeder's own writes rather than from a live game session. | `systems/combat.md` Section 9.1 | A capture of a live arena with monsters placed, reading the marker off the seeded records. |
| What the beyond-raster region of display memory holds after the EGA mode set. It decides whether the message window's vacated bottom row comes up blank on a session's second and later strip scrolls: the fast path does not blank the gutter row it leaves behind, and the next scroll lifts that row into the window. | `systems/display-driver-abi.md` Section 9.5; `systems/text-output.md` Sections 10.1 and 10.5 | A real display or a full emulator boot; a bare harness cannot supply it. The written range is already established to lie above the visible page and below the driver's back buffer, so only the contents are open, not the safety. |
| Whether anything repaints the displaced message band at the pixel level. Bounded, not closed: no character emitted while a non-message window was selected landed in the message rectangle, no driver dispatch after the picker returns names an overlapping rectangle, and every censused argument to the returns-only glyph blitter and resident graphics helpers lies above the message window's first scanline. Their bodies were not executed. | `systems/display-driver-abi.md` Section 9.5; `systems/inventory.md` Section 7.1 | A raster capture of a `U`-Use command whose picker page overflows, taken at the picker wait and after acceptance. |
| The wall-clock length of the Blackthorn audience exit beat. Its call counts are executed and exact — 36 stings, 73 world ticks, 72 one-BIOS-tick delay requests — and the published "floor of roughly five seconds" is arithmetic over those counts plus the already-published sting length. The 73 full viewport rebuild and render passes are not in that figure at all, so the true hold is longer by an unmeasured amount. *Opened 2026-09-12 (issue #268).* | `systems/blackthorn.md` Section 4.2 | One capture from the acknowledgement key to the first town prompt, with CPU/core/cycle settings recorded, plus a frame sampled a couple of seconds in to confirm the message window is still holding the terminating record unchanged. |
| Which side of the slow-CPU threshold a real install's boot calibration word lands on during gameplay, and whether it can land in the high half of the range at all. The gate itself is settled and signed (R491), and only the intro's own installed override is known to sit above the baseline. Every presentation pause in the program that requests a single BIOS tick depends on this. *Opened 2026-09-12 (issue #268).* | `systems/timing.md` Sections 4 and 5.2; `systems/blackthorn.md` Section 4.2; `systems/karma.md` Section 7 | Read back the calibration word at a gameplay prompt on a slow host, a period-typical host and a fast emulated host. *Extended 2026-09-12 (issue #271): the shrine entry's approach walk is the largest single consumer - fifty-five one-tick requests per entry - and this gate is what decides whether that hold is timer-bound or repaint-bound. The same reading is also the leading candidate for the gap between the issue's sampled interval and the executed count, so one calibration read-back settles two published items at once.* |
| The wall clock of the shrine entry's approach walk. Its counts are executed and exact - nine animation frames, forty-five world steps, forty-five one-tick delay requests, nine stings, and one further repaint step before the Kneel record - and the interval is forty-six world steps however long each takes. What is open is the seconds: the arithmetic floor from those counts is about one 600 ms sample longer than the `(1800, 2400]` ms bound issue #271 sampled, and three candidates remain - the capture's zero point trailing the keypress, the capture host landing on the skip side of the signed calibration gate (leaving the hold repaint-bound), or the emulated timer service differing from the stock rate at that cycle count. The last of the three is narrowed, not excluded: the game itself never programs the timer's counting channel or mode port in any shipped image. *Opened 2026-09-12 (issue #271).* | `systems/karma.md` Section 7; `systems/timing.md` Sections 4 and 7.6 | One capture of a shrine entry that also reports the host's boot calibration word, sampled finely enough to separate forty-five ticks from sixty. *Narrowed 2026-09-12 (issue #271 follow-up): the same open term now governs the other end of the meditation. `systems/karma.md` Section 7.2 publishes the closing beat's counts and its arithmetic floors - about 5.0 s on the ordination arm, 11.5 s on the offering arm and 11.0 s on the turn-in arm, from the acknowledging key to the next command prompt - and they are floors for exactly the reason this row is open. Ask for a capture that spans entry and exit rather than the approach alone; one recording then checks both intervals.* |
| The keyboard modifier gate as a real device sees it. That digits `1` and `2` vanish, `5` echoes and `4` erases at the reagent mixer's quantity prompt while NumLock is held is executed, but against a reconstruction of the shipped poll routine's own decisions with the reported modifier byte set and clear - not a capture on hardware or in an emulator. The same pass says nothing about the published dungeon-mode exception to the digit-to-direction rule, because the mixer reads through the shared command reader and no mode loop's own reader was run. *(Opened 2026-09-13, issue #272.)* | `systems/magic.md` Section 6 step 4; `systems/input.md` Section 5 | One end-to-end capture of the mixer's quantity prompt typed with NumLock held and again with it clear, plus the same two keys at a dungeon prompt. |
| No pitch or wall-clock figure is claimed for the rescue's per-member restoration envelope - only its exact parameters (idle 1, 30,000 iterations, initial comparison 2000, delta +2, per-slot phase increment). Reconciling it with the calibrated envelope tables is separate work, as is the still-open six-row capture reconciliation above. *(Opened 2026-09-12, issue #269.)* | `systems/audio.md` Section 8.6.2; `systems/blackthorn.md` Section 7 | A recording of the restoration step with CPU/core/cycle settings, or a calibration pass against the Section 10 duration tables. |
| The issue #270 prompt-cadence contract carries no raster validation, no timing reproduction and no stock-save replay; the reporter's capture harness and the point in the frame it sampled were not inspected. Everything published there is executed original code with an intercepted display driver. *(Opened 2026-09-12, issue #270.)* | `systems/text-output.md` Sections 10.2 and 10.4 | A stock save with the exact keystrokes for each reported beat and frames at the idle point, plus the harness's sampling rule. |

Closed 2026-09-05 by live observation under DOSBox: the three suspected NPC pursuit-stepper defects. None has an observable effect; the stepper's real contract (gate below four, east/north/west/south first fit, no move when nothing improves, event on a later invocation after an NPC's own move creates adjacency) is now published in `systems/npc-schedules.md` Section 9.

Opened 2026-09-13 by the issue #270 exit-handoff pass:

| Item | Where | Notes |
|---|---|---|
| How often the stats panel repaints while the party is aboard a vessel whose hull reads 100 or more, and therefore how visibly the message history creeps upward in play. The panel behaviour is executed; its cadence in a real session is not measured. | `systems/stats-panel.md` Sections 2.1 and 6 | A session capture with a three-digit hull, recording the message window across a sequence of repaints. |
| The exit-handoff row accounting is reproduced by mechanism from the reporter's stated screen state, not replayed from their save, and it carries no raster or timing validation. | `systems/doors-and-z-transitions.md` Section 12.1 | A stock save at a dungeon's entrance level with the exact key sequence, plus frames at the climb key and at the first overworld prompt. |

Opened 2026-10-16 by the issue #298 dungeon pass:

| Item | Where | Notes |
|---|---|---|
| The first-party-exit record's dungeon consequences - that an in-arena K on a ladder or room grate, or the first party edge departure, steps the party a cell or changes its level once a room or walked-into fight ends - are static only; no live run walked an actor onto an arena ladder or off an arena edge and checked the dungeon position afterwards. | `systems/dungeon-mode.md` Sections 14 and 14.1 | One room fight in which a party member climbs an arena ladder, and one contact fight left by an edge, with the dungeon level, cell and facing read afterwards. |
| The chamber-name banner and flavour-3 flourish colours on CGA, Hercules and Tandy, and the flourish's 4-in-65 rate, which is static (one hit in about fifteen live EGA frames is consistent with it but does not measure it). | `systems/dungeon-mode.md` Section 6.4 | A capture on each non-EGA driver facing a banner wall and a flavour-3 `0xC?` wall, and a longer EGA run counting flourish frames. |

Opened 2026-10-16 by the issue #298 Blackthorn and conversation pass:

| Item | Where | Notes |
|---|---|---|
| What a label block's scoped prompt does with the records after the head - which arm is the default and when it falls back to the top-level keyword loop. The head's extent (to the first NUL, with label bytes inside it live) is settled; the post-head state machine was not traced for issue #298 Q20 and rests on earlier static reading only. | `systems/conversation.md` Section 7.7 | An emulator capture of one yes/no label block answered yes, no and with an unmatched word. |

Opened 2026-10-16 by the issue #298 objects and NPC pass:

| Item | Where | Notes |
|---|---|---|
| What the pathfinding search reads and stamps when a probe reaches row 32, the bytes just past the 32-by-32 workspace. The bounds test that admits the index is settled; the bytes' contents are not, and they matter only for byte-level parity on a map whose south edge is open. | `systems/npc-schedules.md` Section 8.4 | A runtime memory map of the area immediately after the workspace, read while an NPC routes along an open south edge. |

Opened 2026-10-16 by the issue #298 commands-misc pass:

| Item | Where | Notes |
|---|---|---|
| The camp apparition as drawn: the old man's art at row 372, the converge fade-in and fade-out, the per-member viewport inversions and the class-tile restamping of the party sprite are static only. | `systems/rest-and-camp.md` Sections 7.1 and 7.2 | A capture of a camp event in which at least one member gains a level, from a save with enough experience for a level change. |

Opened 2026-10-16 by the issue #298 Q31 Blackthorn panel-drop pass:

| Item | Where | Notes |
|---|---|---|
| Why the clean side's paired `bt-correct` capture lists the executed companion on the held page and drops him only after the next key. The stock game, re-run live, drops him before the held page; the published explanation (a key pressed during the blade hold, or type-ahead, satisfying the exit beat's wait) is inferred, because the clean capture itself was not examined. *(Added 2026-10-16, issue #298 Q31.)* | `systems/blackthorn.md` Section 5; `systems/stats-panel.md` Section 2.4 | Re-capture `bt-correct` with no input sent until the key-wait cursor shows; if the drop still follows the key, supply the capture's frame times and input times. |
| Whether a key pressed during the wrong-answer branch's blade hold is buffered and satisfies the `... is sliced in half!` wait as soon as it begins. Type-ahead was executed on the correct-answer branch only. *(Added 2026-10-16, issue #298 Q31.)* | `systems/blackthorn.md` Section 5 | One fourth-wrong-answer run with a key sent during the blade hold. |
| The order of the panel repaint, the printed name and the key-wait cursor inside the final instant of the execution. Live screenshots were about half a second apart, so they show these in one sample only; the order is from static reading. *(Added 2026-10-16, issue #298 Q31.)* | `systems/blackthorn.md` Section 5 | A frame-rate capture of both execution branches. |

Opened 2026-10-16 by the issue #298 Q40 town-attack pass and the Q41-44 endgame and rescue pacing pass:

| Item | Where | Notes |
|---|---|---|
| Whether a town A-Attack fight costs exactly its round-wrap minutes plus one indoor minute, and whether a contact raised by the post-fight schedule pass really starts a second arena fight inside the same command. Both follow from static reading of straight-line code; neither was run. *(Issue #298 Q40.)* | `systems/town-mode.md` Section 7 | A live town fight reading the clock before and after; a fight arranged so a pursuing guard reaches the party on the post-fight schedule pass. |
| The reported 1.9 s lower bound for the endgame's settle-to-greeting hold. The original at fixed emulator cycles measures 2.38 to 2.39 s at 3000 cycles and matches only the reported upper bound. *(Issue #298 Q41.)* | `systems/endgame.md` Section 5.2 | The reporter's definition of "settle" and their emulator cycle setting. |
| Period-hardware durations of the endgame's untimed entry block (dominated by the tileset remap) and of the Blackthorn rescue's three single-cell reveals. Both are CPU-bound; only emulator timings at fixed cycle settings exist, and disk time for the overlay and file reads is zero in the emulator. *(Issue #298 Q41, Q44.)* | `systems/endgame.md` Section 5.2; `systems/blackthorn.md` Section 6.2 | A measurement on a 4.77 MHz machine, or an emulator configuration validated against one. |

## 3. Needs a further static trace

The corridor mirror derivation was completed 2026-09-07: original EGA
blitter execution confirms the one-pixel-left phase and the caller's nominal
anchors produce the R394 coordinates. The orientation/mask distinction is
corrected in `systems/display-driver-abi.md` Section 5.1 (R421).

Opened 2026-09-12 by the issue #262 Klimb and dungeon-object passes:

| Item | Where | What settles it |
|---|---|---|
| Combat's own K-Klimb contract. The pass established only that combat is a fourth prefix owner - its handler prints its own `Klimb-`, then a separate two-way marker and one of the climb or refusal words, and tests the same two ladder tile identities the town handler uses. | `systems/doors-and-z-transitions.md` Section 9; `systems/combat.md` Section 8.4 | A dedicated pass over the combat climb handler and its combat-side caller, including the arena-exit path the published combat text mentions. |
| What reads the resident tile-restoration flag besides the combat framer. The census still counts two reads; the Klimb handler is no longer one of them (R471), so the second is unattributed. Whether the rest of that flag's published contract - its setter, its clears, the framer's restore - survives is untested. | `systems/dungeon-mode.md` Section 14.1; `systems/combat.md` Section 4 | A fresh reader census of the flag byte, separate from the retraction. |
| Whether the dungeon entry path forces the on-foot transport state. The "no player-driven dungeon object placement" contract rests on it, because X-it executed with a mounted transport value in a dungeon scene does place an object. | `systems/active-objects.md` Section 10 | Trace the dungeon entry seed's writes to the transport marker. |
| Whether dungeon-mouth entry caches the party's outdoor position. "Entry caches nothing" is established for the location-entry helper only; the dungeon-entry seed is a separate routine that was not opened. | `catalogs/gazetteer.md` Section 5.1 | Read the dungeon-entry seed path. |
| Whether a "no action taken" result really skips the post-action pass on each Klimb route. The published per-arm turn costs are the handlers' own return values, executed per arm; the callers' use of them was not re-executed. | `systems/doors-and-z-transitions.md` Sections 9 and 13 | Execute each caller's post-action selection against the returned status. |
| Eight dispatcher letters (`C`, `H`, `O`, `Q`, `R`, `U`, `Y`, `Z`) faulted part-way through the dungeon-scene object-write sweep on state the harness does not build. They were clean up to the fault only. | `systems/active-objects.md` Section 10 | A fuller harness that can run those letters to completion in a dungeon scene. |
| Whether the room-combat backup and restore of the active-object table behaves as published. It is cited from existing text rather than re-derived, and the "a monster drop never surfaces in a corridor" negative depends on it. | `systems/active-objects.md` Sections 9 and 10 | Execute the framer's backup/restore across a room fight. |
| Whether the shared party-damage and poison primitives emit text of their own. They are hooked at entry on every executed chest-trap case, so any text they produce is unobserved; the four trap words themselves come from the resolver and were executed in full. | `systems/traps.md` Section 3; `systems/dungeon-mode.md` Section 8.1 | Execute the damage and poison primitives with the text printers live. |
| Dungeon Jimmy's success threshold uses an unsigned shift, so above a Dexterity of roughly twice the depth index plus thirty the expression appears to wrap to a value no roll can beat. Observed at two depth indices; it is an input to the disarm path the chest lifecycle depends on. | `systems/doors-and-z-transitions.md` Section 3.3 | A dedicated Jimmy pass across the full depth and Dexterity range. |

Opened 2026-09-12 by the issue #262 text passes (Blink, moonstone bury and
recovery, surface Get/Search/eat, conversation entry):

| Item | Where | What settles it |
|---|---|---|
| The dungeon-side Get and Search branches were not re-executed, so which of the dungeon band's two capitalised `Nothing of note.` copies each dungeon caller uses is unsettled. The surface band's lower-case and capitalised pair is settled. | `systems/commands.md` Section 5.8; `systems/dungeon-mode.md` Section 8.1 | Execute the dungeon Search and chest paths with the same string-pointer capture the surface pass used. |
| The identity of the further shared resident routine the wall-torch borrow calls in non-combat scenes. The branch's tile rewrite is established; what that call does is not. | `systems/containers.md` Section 7 | Follow the call and enumerate the readers of the state it touches. |
| What the byte the wall-torch borrow sets to one hundred actually is. The spec publishes it as the party's torch counter, which is the long-standing reading; a competing reading of the same store as a theft/alert counter is equally consistent with the branch itself, because its downstream readers were not followed. | `systems/containers.md` Section 7 | Enumerate every reader of that byte and decide which reading the readers support. |
| Whether the shared direction prompt can deliver a zero step to `G` Get. It decides whether the both-sides laden table's grant-without-rewrite case is reachable in play. | `systems/containers.md` Section 7 | Trace the direction prompt's output for a zero-delta answer. |
| Whether a party member's Intelligence can exceed thirty in ordinary play. Above thirty the untrapped container's assessment threshold underflows and every untrapped container reports a phantom trap. | `systems/containers.md` Section 5 | The stat-growth and shrine paths, not the container path. |
| Twelve of the 113 fixed-treasure records carry a filler coordinate at an impossible floor and cannot be reached by an ordinary Search; their narrated classes are unverified in play. | `systems/hidden-treasures.md` Section 2.1 | A writer census over that record array. |
| The three specially gated fixed-treasure records were not exercised against their key-stock, day-cookie and NPC-occupancy gates; only the ordinary records were driven. | `systems/hidden-treasures.md` Section 2 | Drive each gated record through both sides of its gate. |
| The scare hand-off and the reserved regime hand-off out of the conversation dispatcher were stubbed rather than entered, so no literals are established for either. | `systems/conversation.md` Section 2 | A pass over each handler in its own right. |
| Whether the combat arm of Blink's refusal state means anything beyond its effect. The seven-candidate budget and the refusal bit were executed; the state byte's meaning is interpretive and single-source. | `systems/magic.md` Section 8 | A reader census of that state byte. |
| The absorbing-scene interception ahead of the cast allow-mask was executed for Blink only. It sits in the shared gate, so it should apply to every spell. | `systems/magic.md` Section 8 | Run a second spell of a different circle through both absorbing scenes. |
| Writers of the saved Moonstone slot's scene byte other than burial and recovery were not enumerated; only its readers were. A save/load or story path that writes it would change the silent-invalidation contract. | `formats/saved-gam.md` Section 7.2 | A writer census over that byte. |
| Three Moonstone recovery edges were not executed: the lifetime of an unrecovered staged strange rock across leaving and re-entering a map, a Search of a cell whose live tile has mutated since burial, and a combat-scene Search of a cell whose coordinates match a slot. Burial cannot write a combat scene into a slot, but whether any other writer can was not checked. | `systems/commands.md` Section 5.8; `formats/saved-gam.md` Section 7.2 | Execute each edge; the third depends on the slot-writer census above. |

Opened 2026-09-12 by the issue #263 monster arena-exit pass and the issue #264
U-Use shard-row pass:

| Item | Where | What settles it |
|---|---|---|
| What the ordinary attack/target routine does when the driver's second fleeing arm dispatches into it - whether it narrates, draws random numbers, or ticks. Only the driver's own zero-tick behaviour on that path is established; the routine was stubbed at its entry. | `systems/combat.md` Section 9.1 | Execute the attack/target routine on that arm with the text printers and the tick counter live. |
| Hazard and blocked arena terrain on every self-acting movement and exit path. Each executed case ran on open floor, so only the in-bounds branch of the step-validity test is covered and the interaction between the exit arm and hazard terrain is unestablished. | `systems/combat.md` Section 9.1; `systems/combat.md` Section 7 | Re-run the exit and fallback cases on hazard and blocked arena floors. |
| Whether any shipped content ever passes a shard grant sub-index above 2. The two-bit mask is a property of the grant routine; whether the aliasing is reachable in play is not established, because the grant's callers were never enumerated. | `catalogs/item-list.md` Section 8; `systems/containers.md` Section 8 | Enumerate the callers of the shard grant class and read the sub-index each supplies. |
| Whether a consumed shard disappears from the **character inventory panel** as well as from the U-Use picker. The U-Use half is now established directly; the panel is a different renderer and was never executed, so that half rests on the cleared flag alone. | `catalogs/quest-graph.md` Section 5; `systems/inventory.md` Section 4 | Execute the panel renderer with a shard flag set and cleared. |
| The Shadowlord destruction handler's own gates - the fixed interior destruction position, the marker immediately north and the matching active-Shadowlord index - are carried from earlier analysis and were not re-executed in the shard passes. | `catalogs/quest-graph.md` Section 5; `systems/inventory.md` Section 7 | Drive the destruction handler through each gate in both directions. |

Opened 2026-09-12 by the issue #259 picker-overflow pass:

| Item | Where | What settles it |
|---|---|---|
| The general body of the vertical-scroll entry - every requested left edge except the message strip's - was read but not executed, because it needs driver initialisation state a bare harness cannot supply. Only its path selection is executed. Its signed-distance walk, its blanking of the vacated band and its separate hidden-surface body are therefore static readings. | `systems/display-driver-abi.md` Section 9.5 | A harness that can initialise the driver far enough to run the general path, or an equivalent live capture with a non-192 left edge. |
| The Z-stats list page's key dispatch appears, read from the shipped bytes, to send left and right out of the page and to move the selection with up and down - the reverse of the published navigation sentence for that page. Only the down, End, Page Down, right and cancel keys were executed. Flagged rather than concluded; it belongs to the shared-picker navigation question, not to issue #259. | `systems/inventory.md` Section 4.7 | Execute every key of the Z-stats list page's dispatch and re-derive the navigation sentence before publishing either reading. |

Opened 2026-09-12 by the issue #266 ASK-WHO acknowledgement pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the fixed reserved-keyword scan accepts a reserved word that begins a **later** typed word. Section 6 step 4 publishes the acceptance as exact end-of-input or a literal space immediately after the reserved word, which implies the reserved word must begin the typed line; a reading taken while tracing ASK-WHO suggests the scan reaches the same substring search and word-start acceptance that Section 7.6's name match uses, which would also accept `PLEASE BYE`. The reading is static only and nothing was changed on it. | `systems/conversation.md` Section 6 step 4 | Execute the reserved scan against a typed line whose reserved word is not the first word, and against one where it is a mid-word substring. |

Otherwise none open. The twenty-four items this section listed on 2026-09-04 were all
closed on 2026-09-04 and 2026-09-05 once the shipped files became available:
the tile-catalogue re-derivation (R383-R389), the Glass Sword slot consumption
(R390), the visibility threshold, the controlled actor's fixed strike and the
charmed-bit writers, the Corpser drag bit and release roll, the chargen stat
seeds, the NPC initialiser and waypoint rule, the inn bed cells, the Iolo's Hut
cells, the lowest-page descend tiles, the arrest guard, the Falsehood consumers,
the sky readout, the whirlpool script, the two blips, the endgame helpers, the
controlled monster's `Z` and cast arm, the arena-record scratch and the
underworld object writers. Each closure is recorded in its owning document with
the date, and in `EXTRACTION.md` and `NEXT-STEPS.md` under 2026-09-05.

Opened 2026-09-12 by the issue #267 panel-refresh-cadence pass:

| Item | Where | What settles it |
|---|---|---|
| How often the dungeon loop reaches the shared per-turn clock, and therefore how often the day-rollover panel repaint can fire in a dungeon. `systems/main-loop.md` Section 6 publishes an ungated per-iteration call; the call site read for this pass looks narrower than that (conditioned on a timed-effect state and then alternating). Neither reading was executed, and whether dungeon turns advance the calendar by some other route was not established, so the published ungated wording in `systems/main-loop.md` Section 6, `systems/dungeon-mode.md` Section 15 and `systems/input.md` Section 12 is left standing pending execution rather than amended on the strength of an unexecuted read; the cadence contract asserts nothing about the dungeon's rate. | `systems/main-loop.md` Section 6; `systems/time.md` Section 7; `systems/stats-panel.md` Section 2.4 | Execute the dungeon loop across ordinary turns with the calendar observed, or read that call site's guard through to the clock. |
| Whether the extra repaint caused by a refresh request left pending across a scene change is observable. Scene entry repaints inline without clearing the request, so the following prompt should repaint a second time. This was reasoned from the consumer and clear-site census, not measured. | `systems/stats-panel.md` Sections 2.3 and 2.4 | Execute a command that files a request, change scene, and count repaints at the next prompt. |
| The "nothing else reaches the full-panel refresh" negative is weaker for the display-driver images than for the rest of the program. The resident image and every code overlay were read exhaustively; the driver images were searched for the two relevant references and not read through. They are separate images that cannot make a near call to the resident refresh, but that is an argument, not a reading. | `systems/stats-panel.md` Sections 2.2 and 12 | Read the display-driver images through, or establish the call-form negative for them directly. |
| The shrine meditation handler's mantra-validation branch was not exercised. Only the offering path's ordering - debit, immediate repaint, standing increase, announcement - was executed, with the answer comparison forced to match. | `systems/karma.md` Section 7; `systems/stats-panel.md` Section 2.4 | Execute the handler through a mismatched mantra and through the quest-blessing arm, watching for any refresh. |

Opened 2026-09-12 by the issue #268 audience-exit pass:

| Item | Where | What settles it |
|---|---|---|
| What the ambient scenery tick (formerly called the shrine/flame tick) contributes inside a Blackthorn cinematic. It runs once per world tick, so 73 times inside the audience exit beat alone, and it is driven by the loaded cutscene terrain rather than by the live map. *Narrowed 2026-10-16 (issue #298 Q16): its four sources and its 11-by-11 window are now published (`systems/audio.md` Section 8.10), so it can sound only if the loaded cutscene grid places a grandfather clock, waterfall, fountain or drawn minstrel within five cells of the scan centre on each axis.* Until that grid is checked, "the Blackthorn VM scripts play only stingers" is out of scope as a statement about the scene. | `systems/audio.md` Sections 8.10 and 11; `systems/blackthorn.md` Section 4.2 | Inventory the loaded Blackthorn cutscene grid's cells inside that window for the four source classes. |
| What the glyph byte the town loop's command-row opener emits before drawing its chrome renders as. It was observed as the first output after the Blackthorn handoff, but its appearance on screen was not identified, so the published "one line feed, then one glyph byte, then the key wait" order names a byte it does not describe. | `systems/blackthorn.md` Section 4.2 | Resolve that byte through the text primitive's glyph handling, or capture the first town prompt after the handoff. |
| The arrest handler's palace arm between the audience's return and the captive-cell entry setup was not re-executed as one continuous run. The chain was driven as three separately entered shipped segments after a single-stack run hit emulator stack drift; the palace arm itself rests on the issue #244 arrest cases and on reading rather than on a fresh continuous execution. | `systems/blackthorn.md` Sections 2 and 4.2 | One continuous run from the terminating record through the handoff, the arrest handler's palace arm, entry setup and the first town prompt. |

Opened 2026-09-12 by the issue #271 shrine-entry pacing pass:

| Item | Where | What settles it |
|---|---|---|
| How the Shrine of Spirituality is physically reached. Section 7's `(0, 0)` fall-through says what happens when no coordinate row matches, and that is executed; it does not say what puts the party on a shrine that is not on the surface map. Further non-`E` routes into the same shrine/urn presentation exist and none has been run: the town/location turn loop reaches it keyed on a different tile through a resident gate, and `systems/overworld.md` Section 9.2 already publishes the natural-moongate midnight hook dispatching the same overlay. Whether either lands the party on a shrine, and which, is unestablished. Section 7's fall-through paragraph must not be read as if it answered this. | `systems/karma.md` Section 7; `catalogs/gazetteer.md` Section 7 | Execute the town/location turn loop's automatic entry arm and establish which location and tile reach it. |
| The rendering cost and side effects of one world step inside a presentation hold. The hold's text-inertness is executed and closed, and its wind-draw count is published, but the per-step viewport rebuild, the ambient audio tick's contribution and the wind drift's own randomness were never priced for this path. Every seconds figure for a shrine entry rests on them. | `systems/karma.md` Section 7; `systems/animation.md` Section 13.5; `systems/audio.md` Section 11 | Price one world step against the loaded shrine display grid, the same run the Blackthorn ambient-tick item above needs for its own grid. *Extended 2026-09-12 (issue #271 follow-up): a completed meditation spends sixty-one more such steps after the closing record, seventy-three on the turn-in arm, so this one unpriced term is what keeps every figure in `systems/karma.md` Section 7.2 a floor rather than an estimate.* |
| What the compositor draws under the avatar during the approach walk. Both harnesses stub the terrain probe the sprite-stamp path consults before choosing its branch, so the walk's frame-by-frame sprite results are executed against a synthetic reading of the ground even though the display grid itself is real. *Narrowed 2026-09-13 (issue #273): the actor cell itself does not depend on it. The compositor's presentation branch skips the floor-match gate and both viewport bounds tests, and an executed control that forces the slot's layer value to disagree with the scene's for a whole presentation paints a byte-identical sequence; the shrine record's centre column is open grass from the rest cell down to the bottom row. What is still unexecuted is the ground the backdrop paints under the sprite, and the display driver itself, which is stubbed at its entry in this pass too.* | `systems/karma.md` Section 7 | Run the walk with the terrain probe live against the shrine display record. |
| Whether the keyboard queue behaves as modelled underneath the type-ahead result. "Nothing in a presentation hold consumes a key" is executed at the program's own fetch site and the no-flush negative is a whole-corpus census of the shipped images; the underlying BIOS and DOS key services themselves were read rather than run. | `systems/karma.md` Section 7; `systems/input.md` | Type ahead through a shrine entry on a real installation and confirm the queued answer reaches the virtue prompt. |

Opened 2026-09-12 by the issue #269 rescue-narration pass:

| Item | Where | What settles it |
|---|---|---|
| Whether a stats-panel repaint's two single-scanline fills can ever touch rows inside the message-window rectangle. The scroll half is closed - a repaint issues none, and no command against the message window's descriptor - but the fills were recorded by command index only, and their coordinates live in state the intercepted driver call never consumed. | `systems/stats-panel.md` Section 2.1; `systems/blackthorn.md` Section 7.2 | Execute a repaint with the fill coordinates captured, and compare them with the message window's rectangle. |
| The level-from-experience curve over the full experience range, and whether the level is clamped at the top. The rescue's recomputation was observed only over the experience values the executed standings produced. | `systems/blackthorn.md` Section 7; `formats/saved-gam.md` | Sweep the recomputation across the experience range, including values that would exceed the top level. |
| What the castle location load prints into or clears from the message window after the cinematic returns. The published handoff frame describes the instant the handler returns and nothing after it. | `systems/blackthorn.md` Section 7.2 | Continue the executed run through the castle location load with the message window observed. |
| Which test selects the input reader's world-ticking idle arm. `systems/input.md` Section 12 publishes a prompt-character-byte gate; the rescue pass observed the cutscene scene value selecting that arm on its own path. Whether these are one test or two was not established, and neither document is amended on the strength of the other. | `systems/input.md` Section 12; `systems/blackthorn.md` Section 7 | Read the reader's idle arm through to the tick call and name every condition on it. |

Opened 2026-09-12 by the issue #271 closing-sequence pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the whole-window counts of the closing beat hold when executed rather than derived. The handler's own contribution - the envelope runs, the inversion, the ten-step wait and the absence of any tick cost in the sound - was executed; the sixty-one and seventy-three world steps, and the matching delay requests, repaints and wind draws, were re-derived from the presentation's exit structure in the same pass rather than re-run on the frame harness. The exit's eleven-frame Codex variant is derived the same way. | `systems/karma.md` Sections 7 and 7.2 | Run all three completion arms and the Codex exit on the frame harness with the world step, the compositor and the real one-tick delay live, and count the steps. |
| Whether the shrine presentation's per-frame sting is the shared short two-part sting. `systems/karma.md` Section 7.2's wall-clock floors price it at that recipe's 27 ms, and `systems/timing.md` Section 7.6 item 10 still records the sting as unpriced; the identification was assumed in this pass, not established. | `systems/karma.md` Section 7.2; `systems/audio.md` Sections 7.5 and 10.2; `systems/timing.md` Section 7.6 | Read the presentation's per-frame sound call through to its recipe and compare its parameters with the shared two-part sting's. |
| What the offering and turn-in arms' viewport inversion looks like on screen. That a single exclusive-or rectangle fill covers the gameplay viewport, and that nothing restores it, is established; the drawing colour it sets was captured as an argument and the result was never rendered, so how legible the viewport is during the swell that follows is unknown. | `systems/karma.md` Section 7.2; `systems/audio.md` Section 5.4.7 | Render the dispatch against the shrine display grid with the real driver, or capture an accepted offering. |
| Whether the shrine overlay's remaining envelope call sites form further named recipes. The shard-use caller (traced 2026-10-16, issue #296) and the Blackthorn execution caller (traced 2026-10-16, issue #298 Q24) both issue no inversion and no draw before their swell. | `systems/audio.md` Sections 5.4.7 and 11 | Trace the shrine overlay's other envelope call sites. |
| What a successful Shadowlord destruction plays and draws after the shard-use swell (the flame-cell effect, its sound and its world ticks), and whether it invokes the shared full-viewport flash at all. | `catalogs/quest-graph.md` Section 5; `systems/audio.md` Section 8.4 | Trace the shard handler's success arm. |

Opened 2026-09-12 by the issue #270 prompt-cadence pass:

| Item | Where | What settles it |
|---|---|---|
| Which command results can carry the town loop's re-poll code. The loop stores the return of exactly two callees - the shared command dispatcher and the harpsichord digit handler - and the dispatcher passes through whatever its overlay handler returned. The overlay handlers were not enumerated, so "only the harpsichord digit produces it" is an unverified negative. *Extended 2026-09-13 (issue #272): the mixer's row accounting has the same dependent. What follows the `How much? ` prompt once the command returns is the next command prompt's feed-and-marker pair, so a re-poll that emits no pair would leave the prompt row as the window's last written row for a further beat.* | `systems/town-mode.md` Section 7; `systems/commands.md` Section 3; `systems/text-output.md` Section 10.2 | Enumerate the overlay handlers the dispatcher forwards, and check which can return that value. |
| The combat loop's own prompt cadence. Only its single feed-and-marker site was located; nothing is claimed about when combat emits its pair. | `systems/text-output.md` Section 10.2; `systems/combat.md` Section 4.1 | Execute the combat prompt path and record where the pair is emitted and what gates it. |
| The scan behind the overworld prompt flag's locality negative - that every read and write of it lives in the overworld module - covers byte patterns only. An indirect write through a pointer, a register-indirect write, or a write that is not DS-relative was not searched. | `systems/text-output.md` Section 10.2 | Establish the write-site census for that flag by a means that covers indirect writes. |
| How many command-letter arms leave the message row open at a nonzero column. The executed sweep's figure is stub- and residency-dependent - every overlay handler was silenced and two letters emitted nothing because their overlays were not loaded - so no number is published. | `systems/text-output.md` Section 10.4; `systems/commands.md` Section 5.2 | Re-run the sweep with the real overlay handlers resident, per mode. |

Opened 2026-09-13 by the issue #270 exit-handoff pass:

| Item | Where | What settles it |
|---|---|---|
| Whether a hull condition of 100 or more is reachable for a vessel the **party** holds. The panel's overflow arm is executed and is a contract at that value, but the delivered Frigate starts at 99 and the published damage rule only lowers the byte, so the arm's reachability in stock play is unestablished. | `systems/stats-panel.md` Section 2.1; `systems/vehicles.md` | Census every writer of a vessel record's hull byte - shop delivery, spawners, boarding, combat and the shipped object tables of both planes - and report the value ranges each can produce for a party-held vessel. |
| Whether any dungeon mouth's exterior cell has a waterfall in the cell immediately south of it. If one does, the first overworld prompt after that dungeon's exit is suppressed and the beat costs five advances rather than six. The bypass was demonstrated by executing the branch, not by reaching it from a real exit. | `systems/doors-and-z-transitions.md` Section 12.1; `systems/overworld.md` Section 8 | Check the eight exterior entrance coordinates against the waterfall family on both shipped world maps. |
| What the falls hand-off itself emits when it is entered from the overworld input helper ahead of the prompt gate. It is an endpoint in both probes, so the bypass case shows only that the prompt block is skipped, not what replaces it. | `systems/text-output.md` Section 10.2; `systems/overworld.md` Section 8.1 | Execute the falls chain from that earlier entry point with every emission logged. |
| On the Underworld plane, whether anything repaints the two screen rows the dungeon's level and facing labels occupied, given that neither the top header band nor the wind banner is painted there. The viewport rasteriser is an endpoint in every probe on this path. | `systems/doors-and-z-transitions.md` Section 12.1; `systems/dungeon-mode.md` Section 4.1 | Execute an underworld arrival with the full-screen window's cells recorded, with the rasteriser live. |
| The dungeon-entry advance count and the chrome-overwrite reasoning were not re-executed in the verification pass; the covering arithmetic was checked statically only. | `systems/doors-and-z-transitions.md` Section 12.1; `systems/commands.md` Section 5.5 | Re-execute the surface-to-dungeon entry beat and the overworld re-entry chrome in a second harness, as the exit beat was. |
| The dungeon turn loop's own post-climb break path is still read from the bytes rather than executed, in both passes. It needs an overlay-sharing arrangement neither harness provides. | `systems/dungeon-mode.md` Section 13.4 | An execution harness that can stage the two overlays sharing the loop's base, or a live capture across the break. |
| Whether the stats panel's ship row can reach the wrapping column through a transport marker outside the ship family that still satisfies the same test. Only the family members and a few non-members were exercised. | `systems/stats-panel.md` Section 6 | Sweep the whole marker byte range against the row's selection test. |

Opened 2026-09-13 by the issue #272 mixer-prompt pass:

| Item | Where | What settles it |
|---|---|---|
| The tavern's provision question, the one other prompt that reaches the two-digit typed-number reader, was not executed by this pass. Its key rules are the reader's and are settled by inheritance, and its stored text is already published; what is untested is that its rendering behaves as the mixer's does, in particular that the reader adds nothing of its own there either. | `systems/text-output.md` Section 10.6; `systems/shops.md` Section 8.5 | Execute the tavern provision question from its own handler and compare the emitted character stream around the prompt with the mixer's. |
| Which reader the other numeric-looking prompts use - the hours-to-rest question above all. Two direct call sites of the two-digit reader were censused across the executable and every overlay, plus a search for its entry as a stored word; far and computed entries were not enumerated, so "only two prompts" is a census result and the remaining numeric prompts are unattributed rather than known to use something else. | `systems/text-output.md` Section 10.6; `systems/input.md` Section 8 | Trace the hours-to-rest prompt and any other numeric prompt to whichever reader it calls, and record its cap and key rules. |

Opened 2026-09-13 by the issue #273 shrine-pose pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the Codex's interred-party page disturbs the approach walk. The page is emitted inside the walk, between the frame that first draws the avatar and the stepping frames, and every run of this pass had nobody interred, so the walk's pose sequence and repaint counts are executed only for the skipped case. *Narrowed 2026-10-16 (issue #298 Q5): the page's literals, sentinel and name copy are now statically traced and published, it has no key wait or pause of its own, and the count scan and object placement were executed at counts 0, 1 and 3 by the issue #271 probe with no pacing effect; a rendered capture of the page needs a save with a Blackthorn execution.* | `systems/karma.md` Section 8 | Run the Codex arm with at least one interred member and compare the painted sequence and the frame counts against the published ones. |

Opened 2026-09-13 by the issue #273 party-sprite band audit (which closed the
mounting question above; see `RETRACTIONS.md` R505..R508):

| Item | Where | What settles it |
|---|---|---|
| What produces the second ship run - object bytes `0x2C..0x2F`, tiles `300..303`. Nothing in the shipped code's transport-marker writes, nothing in the four location rosters and nothing in the boarding path writes it, and boarding one is refused outright, yet the art is authored and the description table names all four frames a ship. Saved-game world-object data and a runtime ocean spawner are the remaining candidates; neither was examined. *Narrowed 2026-10-16 (issue #298 Q32): the outdoor encounter spawner is a producer - it places pirate ships on the north frame `0x2C`, and the step committer turns them to the other three frames as they move (`systems/encounters.md` Section 4, `systems/weather.md` Section 7). Saved-game and per-plane object data remain uncensused.* | `catalogs/tile-catalog.md` Sections 3 and 10; `systems/vehicles.md` Section 2 | Census the shipped saved-game and per-plane object data for the run, and trace the ocean-spawn path, until either a producer is found or every producer is excluded. |
| What tile `285` depicts and why marker value `0x1D` is accepted by both "party is on foot" predicates. The art is read - a hollow figure outline in blues and cyans, palette-disjoint from the on-foot sprite - and the writers of the corresponding frame byte are located, but the meaning is not established; the "second on-foot frame" reading is withdrawn (R508) without a replacement. | `systems/vehicles.md` Section 2; `catalogs/tile-catalog.md` Sections 3 and 3.1 | Trace every writer of that frame byte to the scene that runs it, and identify what the tile is drawn for. |
| Which frame the stocks, manacles and mirror substitution arms select. Each arm is bounded to its four-tile family and each takes a shipped random roll, but the distribution inside a family was not characterised, so an implementation can reproduce the family and not the sequence. | `systems/visibility.md` Section 8 and 8.1 | Characterise the roll for each of the three arms and publish the per-frame selection rule with its stream accounting. |
| Where terrain id `0x57` - the one substitution arm that routes through the visibility plane rather than the actor plane - occurs in shipped map data. The arm is executed and its behaviour is published, but its in-game occasion is unknown, so nobody can say whether the case is reachable in stock play. | `systems/visibility.md` Section 8 | Census the shipped world, location and arena grids for that terrain id. |
| Whether a seated party member reaches the screen as the sprite its class letter selects. The arena seating pass is executed only as far as the resulting slot bytes; no full arena was composited, so the last step of the claim rests on the already-established slot path rather than on a drawn frame. | `systems/combat.md` Section 5; `catalogs/tile-catalog.md` Section 3.1 | Run a combat arena through the compositor and record the atlas index painted for each seated member. |
| Whether the three Blackthorn-overlay transport-marker writes behave as read. They are the only marker writers in the shipped set that were never executed; the claim that one of them reaches the screen as the description table's corpse tile rests on a byte read plus the established slot path. | `systems/blackthorn.md` Section 6.1; `systems/vehicles.md` Section 2 | Execute the Blackthorn cutscene arms that write the marker and record the painted cell. |
| Whether `catalogs/tile-catalog.md`'s actor-half row for `348..351` ("bard") is the shipped string. `catalogs/npc-roster.md` reads the same description table and gives that tag "a minstrel" (a second minstrel class beside `0x44`), `systems/visibility.md` Section 8 names the family a minstrel, and this catalogue's own Section 2 class list says minstrel too, so the row is the outlier. It was not re-decoded in the pass that corrected the `320..335` names, so it is flagged rather than rewritten. | `catalogs/tile-catalog.md` Sections 3 and 3.1; `catalogs/npc-roster.md` Section 4 | Re-decode that run's description record and reconcile the two documents in one pass. |
| Whether the tile identities in this audit hold outside EGA. Every art reading behind the party-and-vehicle band - the rider added to the horse frames, the figure on the carpet, the rug's symmetry, the sail-state ink counts, the disjoint palettes of `284` and `285` - is a decode of the shipped 16-colour EGA atlas, and the display driver was stubbed throughout, so indices and viewport cells are executed but no pixels were rasterised. | `catalogs/tile-catalog.md` Sections 3.1 and 10 | Decode the CGA, Tandy and Hercules atlases for the same ids, or rasterise the executed frames through a live driver. |

Opened 2026-10-16 by the issue #298 objects and NPC pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the mimic's and the corpser's scripts ever run past their pause-15 freeze. Both show frame 1 and freeze; if gameplay releases the slot by clearing only the delay nibble, the position sits at step 2 and the later steps run, and if it resets the whole phase byte the script restarts and freezes again. The release writer was not traced. | `systems/active-objects.md` Section 3 | Trace every gameplay writer that releases a frozen slot of either class and record what it writes; optionally, a capture of a mimic or corpser slot staying on frame 1. |

Opened 2026-10-16 by the issue #298 magic and combat pass:

| Item | Where | What settles it |
|---|---|---|
| Which occupied cells the shared combat spawn-cell validator really admits. `systems/magic.md` Section 8 (the shared random arena probe) says it rejects "any cell already holding a combat actor or a dynamic object"; the issue #298 Q3 review found that absolute overstated - some object tiles, objects with a blank displayed tile and descriptors carrying certain absent or dead flags appear to pass - but the exceptions were not enumerated precisely enough to publish. The combat Blink text defers to the validator by name instead of repeating the absolute. A live caster's own cell is rejected either way. | `systems/magic.md` Section 8 | A dedicated pass over the validator that lists every occupant class it admits and rejects, then a correction of the shared probe paragraph. |
| That a party member under the Sword of Chaos is routed past the command handler's asleep arm to the self-acting driver's `0..16` wake draw. The two draws themselves are verified twice; this routing rests on one static reading. *(Issue #298 Q25.)* | `systems/combat.md` Sections 6.2 and 8.1 | Re-trace the Chaos gate's hand-off to the driver for an asleep compelled member. |

Opened 2026-10-16 by the issue #298 commands-misc pass:

| Item | Where | What settles it |
|---|---|---|
| Where the camp event's class tile lands after a combat. The record-0 (party sprite) outcome holds when every descriptor linked to a member has a zeroed object index; the actor-clear helper preserves the member/class link byte, so the table is not all-zero after combat, and a descriptor whose object index survives combat teardown would redirect the stamp. *(Issue #298 Q10.)* | `systems/rest-and-camp.md` Section 7.2 | Trace the combat-end descriptor teardown and record what remains in each descriptor's object index. |
| The camp inversion's highlight pen at event time, and whether the world-tick pauses after each member's unrestored inversion repaint the viewport. *(Issue #298 Q10.)* | `systems/rest-and-camp.md` Section 7.1 | Trace the pen slot's writers before the event and the world tick's repaint behaviour inside it. |
| The shrine/Codex presentation's per-count object positions on the 11-by-11 map, and what actor tile `0x03`'s art is meant to represent there. *(Issue #298 Q5.)* | `systems/karma.md` Section 8 | Read the position table and check the drawn art. |
| Whether any shipped turn runs two time-advancing calls between an hour crossing and the next party-upkeep pass, which would erase the shared snapshot's mismatch and skip that hour's starvation or meal branch (for example terrain's extra clock work). *(Issue #298 Q27.)* | `systems/time.md` Section 5 | Trace the per-mode turn sequence for the order of time-advancing calls and the upkeep pass. |

Opened 2026-10-16 by the issue #298 Q32 ship-cadence pass:

| Item | Where | What settles it |
|---|---|---|
| Whether ship moves made outside the overworld movement dispatch also rewrite both tile bytes to the step's heading. The rewrite is established only for the dispatch's two step paths (directed planner and random walker); other overlays were not checked. *(Issue #298 Q32.)* | `systems/weather.md` Section 7; `systems/active-objects.md` Section 8 | Census every caller of the step committer and every other writer of a `0x2C..0x2F` slot's position across all overlays. |
| What the pirate-ship cadence branch does with a wind value outside `0..4`, which a byte-compatible loader preserves. The cadence table holds sixteen entries, and such a value would index past them. *(Issue #298 Q32.)* | `systems/weather.md` Sections 2 and 7 | Trace the branch's index arithmetic for wind values 5..255 and record what data it reads. |
| Whether anything reaches record byte 7 of a `0x2C..0x2F` slot through a pointer. The ownership census of byte 7 counted direct references only. *(Issue #298 Q32.)* | `systems/active-objects.md` Section 3; `systems/weather.md` Section 7 | An indirect-access census of the active-object table's byte 7, or a watchpoint run over a session with pirate ships. |

Opened 2026-10-16 by the issue #298 Q33 dungeon monster-step pass:

| Item | Where | What settles it |
|---|---|---|
| Which of the eight dungeon monster families carries the single presentation value the step treats as stationary. The step's test of one value is established; the family it belongs to was not named. *(Issue #298 Q33.)* | `systems/dungeon-mode.md` Sections 4.1 and 14 | Match the step's stationary value against the eight presentation records' sprite-state bytes and publish the family name. |
| Whether the dungeon post-action hook has any adjacency trigger of its own besides the step's contact flag. The step fires contact only when the monster's current cell is the party's cell; earlier text said the hook fired when the step made the monster adjacent, and the hook itself was not re-read. *(Issue #298 Q33.)* | `systems/dungeon-mode.md` Section 14 | Read the post-action hook's path from the step call to the auto-face launch and record every condition that reaches it. |

Opened 2026-10-16 by the issue #298 Q40 town-attack pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the overworld and dungeon loops also re-run the party-capability check after an acted command, as town does ahead of its epilogue. Only the town loop was read for the recheck. *(Issue #298 Q40.)* | `systems/main-loop.md` Section 6; `systems/town-mode.md` Section 7 | Read the overworld and dungeon per-turn loops between dispatch and their clock calls. |

## 4. Deferred by scope

| Item | Where | Notes |
|---|---|---|
| Exact CGA, Hercules and Tandy rendering, timing and audio-wait parity. EGA is the sole pixel-exact target; the other three drivers are labelled modern approximations. (Narrowed 2026-09-04: the Tandy subtitle-ignition sequencing is now established as identical to EGA's - `systems/timing.md` Section 7.6, item 8.) | `EXTRACTION.md`, "Known V1 Deferrals"; `systems/display-driver-mode.md` Section 6; `systems/timing.md` Section 7.6, item 8 | Revisit only if historical hardware parity becomes a target. |
| XMIDI music. The analysed clean DOS baseline ships no music resources. | `EXTRACTION.md` | Add only for a distribution that ships them. |

## 5. Markers that read as open but are closed

These sentences still contain the words "open question" or "unverified", but
each records a closure. Listed so nobody re-audits them.

- `systems/dungeon-mode.md`: the Hythloth bottom-handoff reading is withdrawn
  in both directions, not left open.
- `systems/inventory.md`: the attribution once marked UNVERIFIED is cleared.
- `systems/view.md`: the earlier "open question" is retracted rather than
  answered; nothing remains to trace.
- `systems/visibility.md` Section 11: the combat-merge question was checked
  over both shipped paths and is closed.
- `systems/audio.md` Section 9: the 220/150 Hz pair is identified (the
  inapplicable-combat-command refusal) and is no longer open.
- `systems/u4-transfer.md` Section 5.4: the imported party file's 39-byte
  record stride and eight-record count cannot be settled from Ultima V at all -
  the transfer reads record 0 and then seeks straight to the party-wide block,
  so the program fixes only the product of the two, never either factor. They
  are Ultima IV format facts and are carried on that authority by design.
