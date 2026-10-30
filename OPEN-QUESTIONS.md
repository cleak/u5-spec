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
eight trace items (section 3) in its place. The issue #298 dungeon pass (2026-10-16) opened two capture items (section 2), and the issue #298 Blackthorn and conversation pass opened one more and narrowed a section 3 swell item. The issue #298 objects and NPC pass (2026-10-16) closed the issue #273 item on the other ten frame-script rows, and opened one capture item (section 2) and one trace item (section 3). The issue #298 magic and combat pass (2026-10-16) opened one owner item (section 1) and two trace items (section 3), narrowed the Blackthorn ambient-tick item and extended the world-tick-rate capture item. The issue #298 commands-misc pass (2026-10-16) opened one owner item (section 1), one capture item (section 2) and four trace items (section 3), and narrowed the Codex interred-party item. The issue #298 Q31 Blackthorn panel-drop pass (2026-10-16) opened three capture items (section 2). The issue #298 Q32 ship-cadence pass (2026-10-16) opened three trace items (section 3) and narrowed the section 3 item on what produces the second ship run. The issue #298 Q33 dungeon monster-step pass (2026-10-16) opened two trace items (section 3). The issue #298 Q40 town-attack pass (2026-10-16) opened one capture item (section 2) and one trace item (section 3); the issue #298 Q41-44 endgame and rescue pacing pass opened two capture items (section 2). The issue #299 Q20 and Q21 scoped-prompt pass (2026-10-18) closed the issue #298 scoped sub-prompt capture item (section 2) and the issue #266 reserved-scan trace item (section 3), and opened one trace item (section 3). The issue #299 Q23 and Q24 dungeon sleep and Klimb-chooser pass (2026-10-18) opened one capture item (section 2). The issue #299 Q25, Q26 and Q29 travel pass (2026-10-18) opened three capture items (section 2) and narrowed the section 3 Spirituality item to the town-loop route. The issue #299 Q22 top-level keyword-layout pass (2026-10-19) opened one capture item (section 2) and narrowed the section 3 labelled-block census item. The issue #300 Q4/Q17, Q5, Q7 and Q18 town pass (2026-10-25) opened six capture items (section 2) and four trace items (section 3). The issue #300 Q12, Q13, Q19, Q20 and Q21 Talk and signs pass (2026-10-25) closed the section 3 scare-hand-off item, and opened three capture items (section 2) and two trace items (section 3). The issue #302 Q2 and Q3 Z-stats and signs pass (2026-10-25) closed the section 3 sign read-window item, and opened two capture items (section 2) and one trace item (section 3). The issue #302 Q5 and Q6 dragged-under and Sleep Field pass (2026-10-25) extended the section 2 `>ARGH!` capture item to the two rumble durations, and opened one capture item (section 2) and two trace items (section 3). The issue #304 Q1 fall-chain pass (2026-10-26) opened one capture item (section 2) and two trace items (section 3). The issue #304 Q2 and Q3 conversation-draw pass (2026-10-26) opened one trace item (section 3). The issue #304 Q4 and Q5 wait-caller and preview-draw pass (2026-10-26) opened two capture items (section 2) and two trace items (section 3). The issue #304 Q8 shrine-kneel timing pass (2026-10-26) narrowed the issue #271 approach-walk wall-clock item (section 2) to the unexplained #271 sample and non-stock hosts, and added data points to the calibration-threshold, presentation-step and per-frame sting items. The issue #305 Q1 dungeon contact-launch pass (2026-10-27) opened one capture item (section 2) and one trace item (section 3). The issue #305 Q2 and Q3 walker and spawner-draw pass (2026-10-27) opened one capture item (section 2). The issue #305 Q4 contact-rule pass (2026-10-27) opened one capture item (section 2) and one trace item (section 3). The issue #306 Journey Onward load-path pass (2026-10-27) opened three capture items (section 2). The issue #307 Q2 mountain-reject pass (2026-10-27) opened two trace items (section 3). The issue #308 Q3 field-marker pass (2026-10-28) opened one capture item (section 2) and one trace item (section 3). The issue #310 Q1 and Q2 wake-ring and combat world-tick pass (2026-10-29) opened two capture items (section 2) and one trace item (section 3), and narrowed the issue #309 sleeper capture item. What else
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
| The sounding fraction of a drowning pass. The pass structure is static reading: the 300-update impact rumble, then one 160-update damage rumble per damaged member, with no calibrated wait. The model gives about 216 + 115 ms of sound in two bursts for a solo Avatar, about 331 ms (lower band about 316 ms), which leaves only about 6 ms of the measured 0.337 s period for every repaint and row invert, while the stock capture was reported as one burst of about 0.30 s plus a short gap. The period is consistent; the 216/115 split and the sounding time are unverified model values. *(Opened 2026-10-25, issues #300 Q27 and #301 Q3.)* | `systems/audio.md` Sections 8.9 and 10.2; `systems/overworld.md` Section 6.2.4 | A drowning-loop audio capture resolved finely enough to separate the two bursts within a solo pass, ideally paired with a four-member drowning to confirm the per-member increment. |
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
| Which side of the slow-CPU threshold a real install's boot calibration word lands on during gameplay, and whether it can land in the high half of the range at all. The gate itself is settled and signed (R491), and only the intro's own installed override is known to sit above the baseline. Every presentation pause in the program that requests a single BIOS tick depends on this. *Opened 2026-09-12 (issue #268).* | `systems/timing.md` Sections 4 and 5.2; `systems/blackthorn.md` Section 4.2; `systems/karma.md` Section 7 | Read back the calibration word at a gameplay prompt on a slow host, a period-typical host and a fast emulated host. *Extended 2026-09-12 (issue #271): the shrine entry's approach walk is the largest single consumer - fifty-five one-tick requests per entry - and this gate is what decides whether that hold is timer-bound or repaint-bound. The same reading is also the leading candidate for the gap between the issue's sampled interval and the executed count, so one calibration read-back settles two published items at once.* *Data point 2026-10-17 (issue #299 Q10): in DOSBox 0.74 at fixed 1500, 3000 and 10000 cycles the Blackthorn exit beat's one-tick delays were real waits (the sting cadence came in whole ticks), so an emulated host at those settings lands above the gate. No calibration word was read back, and no slow or period host was measured.* *Data point 2026-10-26 (issue #304 Q8): a shrine entry at DOSBox 3000 cycles ran its one-tick delays as real waits (a five-tick sting cadence on the video lattice). No calibration word was read back.* |
| Issue #271's sampled shrine-entry interval, and the seconds of a shrine entry on any host other than a stock emulator. *Narrowed 2026-10-26 (issue #304 Q8): the stock seconds are now measured - at DOSBox 3000 cycles (EGA) each paced walk step costs one tick, echo to Kneel is about 48.9 ticks and Kneel to the virtue question about 11.5 (`systems/karma.md` Section 7, "Measured stock timeline"). That capture is longer than the arithmetic floor, so it does not explain issue #271's `(1800, 2400]` ms sample, about one 600 ms sample below the floor; the #271 host and cycle count are unknown, and none of its three candidates - the capture's zero point trailing the keypress, the host on the skip side of the signed calibration gate (a repaint-bound hold), or an emulated timer service differing from the stock rate - is confirmed or excluded. Also still open: the keypress-to-echo latency, a period host's print and repaint costs, and the measured closing beat: `systems/karma.md` Section 7.2's floors (about 5.0, 11.5 and 11.0 s) remain arithmetic.* *Opened 2026-09-12 (issue #271).* | `systems/karma.md` Sections 7 and 7.2; `systems/timing.md` Sections 4 and 7.6 | Repeat the #271 capture with its host and cycle settings recorded, plus the boot calibration word; and one capture spanning a shrine entry and its exit on a period-typical host. |
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
| Period-hardware durations of the endgame's untimed entry block (dominated by the tileset remap) and of the Blackthorn rescue's three single-cell reveals. Both are CPU-bound; only emulator timings at fixed cycle settings exist, and disk time for the overlay and file reads is zero in the emulator. *(Issue #298 Q41, Q44.)* *Extended 2026-10-25 (issue #301 Q4, Q5): the same applies to the Blackthorn audience handoff and captive-cell entry setup (about 0.27 s at fixed 3000 cycles, CPU work plus the location's schedule, floor-page and overlay reads), to the rescue's span from fall end to the conditional repaint (disk-swap request, presence probe, possible overlay loads) and to its first rectangle dissolve (1.65 s at 3000, 3.05 s at 1500).* | `systems/endgame.md` Section 5.2; `systems/blackthorn.md` Sections 4.2, 6.2 and 7.1 | A measurement on a 4.77 MHz machine, or an emulator configuration validated against one. |

Opened 2026-10-17 by the issue #299 Q1 conversation stop-code pass:

| Item | Where | Notes |
|---|---|---|
| Three stop-code paths rest on static reading only: a passing IF-ELSE with argument `0xFF` opens a nested keyword prompt without flushing the pending word; a stopped reserved `NAME` or `JOB` response ends the conversation; inside the Bye entry a stop skips only the closing quote and the two row breaks. No executed probe took any of them. No shipped content depends on the flush difference or on a stopped `NAME`/`JOB`, because every shipped IF-ELSE `0xFF` follows a row break or key wait and no shipped Name or Job entry contains `0x82`. | `systems/conversation.md` Section 7.2 | Execute the original on a synthetic IF-ELSE `0xFF` with a pending word, a Name entry ending in `0x82`, and a Bye entry ending in `0x82`. |

Opened 2026-10-17 by the issue #299 Q5 camp-apparition pass:

| Item | Where | Notes |
|---|---|---|
| The one-flash-per-member camp apparition rests on static reading only: each world-tick pause is read as repainting the whole viewport, erasing the inversion. No live capture; the apparition is a random event behind camp conditions. *(Issue #299 Q5.)* | `systems/rest-and-camp.md` Section 7.1 | A paired capture of a camp apparition with two or more living members. |

Opened 2026-10-17 by the issue #299 Q3 dungeon active-record pass:

| Item | Where | Notes |
|---|---|---|
| That a reused dungeon record whose stamped level differs from the party's level behaves as if it stood on the current level rests on static reading only; no save image with a mismatched level was resumed. *(Issue #299 Q3.)* | `systems/dungeon-mode.md` Section 4.1 | Resume a dungeon save edited so the record's stamped level differs from the party's, and observe the corridor, the monster's steps and contact. |

Opened 2026-10-17 by the issue #299 Q8 sailing-prompt pass:

| Item | Where | Notes |
|---|---|---|
| That the shared cleanup, the world step, the outdoor per-turn epilogue and the turn tail emit no line feed of their own after a no-echo hoisted direction. Inferred only: the executed run of the overworld helper replaced those steps with stubs, and the static census covered the prompt gate, not line feeds. The claim rests on the issue's stock capture and the two issue #297 captures agreeing. *(Issue #299 Q8.)* | `systems/text-output.md` Section 10.2 | A static pass over those steps for line-feed output, or an unstubbed emulator run of a held voyage. |
| Where `Attacked!` and the other under-sail lines land relative to the pending marker row. Inferred from the gate behaviour, the literals' leading feeds and the point above; no new live run. *(Issue #299 Q8.)* | `systems/text-output.md` Section 10.2 | A DOSBox capture of an engagement during a held voyage after an accepted hoisted step. |

Opened 2026-10-17 by the issue #299 Q12 divider-band pass:

| Item | Where | Notes |
|---|---|---|
| That the timed-effect slot keeps drawing inverted on every later panel repaint while the leak is set, and that installing, changing or expiring an effect during the leak redraws the slot, or restores the plain band, under the same rule. Inferred from the leak's lifetime; no run installed, changed or expired an effect with the leak set. *(Issue #299 Q12.)* | `systems/inventory.md` Section 4.4 | A DOSBox capture that sets the leak, then casts or expires a timed effect and compares the row-7 frames. |
| How the arms sell browser's page-status badge, which also draws end caps in the slot, renders under the leak, and therefore whether a capture showing inverted caps on row 7 must have had a timed effect running. Untested. *(Issue #299 Q12.)* | `systems/inventory.md` Section 4.4 | A DOSBox capture of the arms sell browser entered with the leak set. |

Opened 2026-10-17 by the issue #299 Q14-Q16 inn and tavern pass:

| Item | Where | What settles it |
|---|---|---|
| How Leave adjusts the active-player index when it moves the leaving record to slot 15. Leave is known to adjust it; the rule is not published. *(Issue #299 Q14.)* | `systems/shops.md` Section 8.4; `formats/saved-gam.md` Section 4 | Execute Leave with the active-player byte set before, on and after the leaving slot, and record the byte afterwards. |
| Whether an ordinary (not poisoned) Pickup sets the returned companion's current HP to maximum and refills MP (Avatar and Mage to Intelligence, Bard to half), as Rest does. Reported as a side observation, not checked against the spec or verified; the `P` bullet says nothing either way. *(Issue #299 Q14.)* | `systems/shops.md` Section 8.4 | Execute paid Pickup of a healthy guest with reduced HP and MP, per class, and compare the returned record. |
| The Guest Register's highlight bar and the afford-only line after `-1` were observed at the print and key-wait call boundary only; their pixel layout is not captured, and the register's physical-key mapping is inferred from `systems/input.md` Section 5 rather than executed at the register. *(Issue #299 Q15, Q16.)* | `systems/shops.md` Sections 8.C and 8.5 | A DOSBox capture of a three-guest register driven by arrows, numpad and Shift-held top-row digits, and of a `-1` provision purchase that runs out of gold. |

Opened 2026-10-17 by the issue #299 Q13 and Q19 combat-refusal pass:

| Item | Where | What settles it |
|---|---|---|
| The combat refusal row layouts (controlled-monster R and U with a blank row before `Can't!`, the K `What?` and refused-departure rows) are emission-order results, not screen captures; the blank rows are derived from the published newline rendering rule. *(Issue #299 Q13, Q19.)* | `systems/combat.md` Section 8.4 | A DOSBox capture of a charmed monster pressing R in an arena, and of a refused K target, from a stock save. |
| That a K target on a rock pile holding an object gives the same `What?` rows rests on static reading; no run took that case. *(Issue #299 Q13.)* | `systems/combat.md` Section 8.4 | Execute the arena K handler toward a rock cell with an object on it. |

Opened 2026-10-17 by the issue #299 Q17 and Q18 clock and hours-prompt pass:

| Item | Where | What settles it |
|---|---|---|
| Which ordinary panel refresh first shows the repaired food value after a rescue clock spin that crossed midnight. That it is the next ordinary refresh is inferred; it was not traced. *(Issue #299 Q17.)* | `systems/blackthorn.md` Section 7, step 12 | Trace or capture the first panel repaint after the castle handoff from a wipe at hour 7 or later with zero food. |

Opened 2026-10-18 by the issue #299 Q23 and Q24 dungeon sleep and Klimb-chooser pass:

| Item | Where | What settles it |
|---|---|---|
| That keypad 8 and 2, and top-row `8` and `2` with NumLock on, answer the dungeon `Klimb-U/D-` chooser as up and down rests on static reading of the chooser and the shared reader's modifier test; the live run covered the letters, the arrows, Space and the ignored keys only. Shift with a top-row key types punctuation, which the chooser ignores; that is executed at the dungeon hours prompt through the same reader (issue #300 Q15, R589) but not at the chooser. *(Issue #299 Q24; narrowed 2026-10-25, issue #300 Q15.)* | `systems/dungeon-mode.md` Section 13.1 | A DOSBox run at the chooser pressing keypad 8/2 with NumLock off and on, and top-row 8/2 with NumLock on. |

Opened 2026-10-18 by the issue #299 Q28 rescue-spin pass (the Q17 row on the spin's midnight and month events is closed: those are now executed):

| Item | Where | What settles it |
|---|---|---|
| What the first castle turn does with the post-spin hour snapshot (5 against hour 6). It is inferred that the first party upkeep pass takes the 06:00 food decrement, and that a mode-zero cleanup at castle entry could refire the hour bundle once; neither was traced. *(Issue #299 Q28.)* | `systems/blackthorn.md` Section 7, step 11 | A trace or DOSBox capture of the first castle turn after a rescue from a non-06 hour, recording food, the snapshot and any hour-bundle work. |

Opened 2026-10-18 by the issue #299 Q25, Q26 and Q29 travel pass:

| Item | Where | What settles it |
|---|---|---|
| Whether a midnight-gate shrine visit always leaves the clock at minute `10` or later of hour `0`. If a visit can end earlier (for example one that a blank virtue answer ends early), the re-risen gate's next transit re-enters the shrine instead of warping. Only one visit was run, and it ended at 00:18. *(Issue #299 Q29.)* | `systems/overworld.md` Section 9.2 | A trace of what advances the clock during the presentation, or DOSBox runs from several starting minutes including a visit ended by a blank virtue answer, recording the clock at exit and the next transit. |
| That a party on a horse or carpet that arrives in a town by moongate leaves it by the edge still mounted, and that a Gate Travel cast teleports a mounted party without changing its marker. The first is inferred from the town-family round trip; the second rests on static reading of the shared warp. *(Issue #299 Q26.)* | `systems/overworld.md` Section 9.2; `systems/magic.md` Section 8, the Gate travel row; `systems/town-mode.md` Section 15.1 | A DOSBox run that moongates a mounted party into a town and walks it out by the edge, and one that casts Gate Travel while mounted and on a carpet, checking the marker after each. |
| What a frigate or skiff does on a gate cell. Gate cells are Moonstone burial cells and the hook has no transport test, so the case was not exercised. *(Issue #299 Q26.)* | `systems/overworld.md` Section 9.2 | A static check of whether a frigate or skiff can stand on any burial-set tile, or a DOSBox run that places one on a gate cell at night. |

Opened 2026-10-19 by the issue #299 Q22 top-level keyword-layout pass:

| Item | Where | What settles it |
|---|---|---|
| Mario's `DON'T ASK!` line (`TOWNE.TLK` id 23) was executed only on the original conversation code with a stand-in text sink: the glyph after the opening quote was seen as the byte the sink received (codepoint `0x10`), not as pixels, and typing the apostrophe and exclamation mark through the real keyboard path was not exercised. The line reader's accepted range is a static reading; its fifteen-character limit was observed in the executed runs. *(Issue #299 Q22.)* | `systems/conversation.md` Section 7.7 | A DOSBox run of the original game that types `DON'T ASK!` to Mario and captures the row showing the quote and the glyph. |

Opened 2026-10-25 by the issue #300 Q3, Q6, Q8 and Q15 rest, save and hours-prompt pass (the issue #299 Q18 row on modifier-held keys at the dungeon hours prompt is closed: those cases are now executed, R589):

| Item | Where | What settles it |
|---|---|---|
| That NumLock-on top-row and keypad `1`-`4` and `6`-`9` are discarded at the town-bed hours prompt. Inferred from the shared command reader it shares with the dungeon hours prompt, where it is executed; not run at the bed. *(Issue #300 Q8.)* | `systems/rest-and-camp.md` Section 4 | Press NumLock digits at an inn bed's hours prompt. |
| That the town-bed loop reseats the NPCs after every ten-minute step, before the bed test. Static reading of the bed loop, confirmed by a verifier; not executed. *(Issue #300 Q6, R586.)* | `systems/npc-schedules.md` Section 12; `systems/rest-and-camp.md` Section 4 | Sleep several hours in a town bed while watching a mid-route NPC, or log the reseat calls under emulation. |
| Whether the shared dawn/dusk pass does more than the archway/portcullis toggle. An unpublished static reading suggests that the same pass also rewrites bridge-class cells to shoals at 20:00 and back at 05:00, unless the party stands on one. That would conflict with the published reading of those cells as NPC start markers. This is not published as behaviour. *(Side finding of issue #300 Q6.)* | `systems/town-mode.md` Sections 2 and 6; `formats/location-dat.md` Sections 6 and 10 | A static trace of the whole pass, then a capture at a town bridge across 20:00 and 05:00. |

Opened 2026-10-25 by the issue #300 Q4/Q17, Q5, Q7 and Q18 town pass:

| Item | Where | What settles it |
|---|---|---|
| Stonegate's notices with a vanquished Shadowlord. Only the all-living case (cowardice, hatred, falsehood) was executed; that a vanquished Shadowlord's notice is skipped and the others keep the third-to-first order is static reading. *(Issue #300 Q4.)* | `systems/town-mode.md` Section 13 | Enter Stonegate from a save with one or two Shadowlords vanquished. |
| Stonegate's silent removal of the centre-cell Sceptre figure while the Sceptre flag is set, and its return after a reclaim. Static reading plus the shipped roster; not executed. *(Issue #300 Q4, R590.)* | `systems/town-mode.md` Section 13 | Enter Stonegate carrying the Sceptre, then again after a Shadow Lord fight has reclaimed it, and look at the centre cell. |
| That the Shadowlord notice, its tone and the resident-entry sweep are skipped when the party-capability check finds nobody able to act or asleep. Static reading only. *(Issue #300 Q4.)* | `systems/town-mode.md` Section 13 | Enter a hideout town with every member dead or otherwise unable to act and none asleep. |
| The endgame viewport bands beyond what was recorded. Observed only through the first box question's `No` and the second question's pending prompt, with facing `North`; the second answer, the refusal branch (endgame Section 6), the victory branch up to the fade, and other facings at the fall are static reading or inference. *(Issue #300 Q5.)* | `systems/endgame.md` Section 3.1 | Record the endgame through both refusal and victory, entering the final room with a facing other than North. |
| The arrest contracts not yet executed: the case-insensitive key, the hour-8 no-time case, and the refusal's `Attacked!` fight. A surrender at 14:39 was executed (row layout, the 08:19 wake, the silent fresh Yew entry; issue #300 Q33). *(Issue #300 Q7, R591, R592; narrowed 2026-10-25, Q33.)* | `systems/town-mode.md` Section 14 | Get arrested in an ordinary town during the 08:00 hour and surrender, then refuse on another arrest. |
| The A-Attack Shadowlord fight's aftermath: the post-fight re-install at the home cell (and the further blight pass) is static reading; the one run with the Sceptre carried could not finish the fight. *(Issue #300 Q18.)* | `systems/town-mode.md` Sections 10 and 14; `systems/encounters.md` Section 7 | Finish a town Shadowlord fight (win or flee) and check for the re-installed Shadowlord. |

Opened 2026-10-25 by the issue #300 Q33 and Q34 arrest-wake and digit pass:

| Item | Where | What settles it |
|---|---|---|
| The arrest wake under Quickness, 08:(arrest minute modulo 10). Static reading of the jail loop and the clock step's Quickness halving; only the twenty-minute case was executed. *(Issue #300 Q33.)* | `systems/town-mode.md` Section 14; `systems/time.md` | Get arrested with Quickness active at a minute whose modulo-10 and modulo-20 values differ, surrender, and read the wake time. |
| That digits typed with Shift or NumLock become directions in the input layer and never reach the active-player selector in town or on the overworld. Not re-executed. *(Issue #300 Q34.)* | `systems/town-mode.md` Section 7.2 | Type a shifted digit and a NumLock keypad digit at the town and overworld prompts and observe whether `Set Active Plr:` prints. |

Opened 2026-10-25 by the issue #300 Q9, Q10, Q26, Q30 and #301 Q1, Q2, Q6 combat pass:

| Item | Where | What settles it |
|---|---|---|
| `>ARGH!` on the marker row, and the blank row before the marker after a banner whose last row fills sixteen columns. The `ARGH!` order is executed on the original turn handler but no capture of a Corpser drag exists; the blank row rests on the issue #301 stock `Zzzzz...` capture plus the printer rule, not on a run of the window printer. The two dragged-under rumble durations (about 188 ms after `ARGH!`, about 1.29 s after the release line) are `audio.md` Section 10.2 model values with no capture *(extended 2026-10-25, issue #302 Q5)*. *(Issue #301 Q1, Q2.)* | `systems/combat.md` Section 8.1; `systems/audio.md` Sections 5.3 and 10.2 | Capture a party member dragged under by a Corpser, ideally one whose banner ends `with bare hands:`, through a held turn and a release, timing both rumbles. |
| The dungeon loop-head minute under Quickness and Negate Time: skipped outright under `T`, made on every other iteration under `Q`. Static reading only; which iteration of the pair spends the minute, and whether the alternation state carries across a fight or a level change, were not traced. *(Issue #300 Q10, R595.)* | `systems/dungeon-mode.md` Sections 4 and 15 | Cast Quickness, then Negate Time, in a dungeon and read the clock across several iterations of known commands (digits, refused Push). |

Opened 2026-10-25 by the issue #300 Q12, Q13, Q19, Q20 and Q21 Talk and signs pass:

| Item | Where | What settles it |
|---|---|---|
| Which NPC record, if any, the forced-flight helper rewrites after an **explicit typed** Talk on a `0xFE` NPC. The number it receives is caller state the Talk path never sets; executed, the talked-to NPC was rewritten only when that leftover equalled its index. Static reading (not executed) suggests the leftover is never a valid NPC number, so the talked-to NPC is never rewritten and the helper may write outside the NPC table. The literal, the damage pass and the automatic-contact and AI 6/7 targets are settled. *(Issue #300 Q19, R601.)* | `systems/conversation.md` Section 2; `systems/town-mode.md` Section 14 | A debugger read of that value at an explicit Talk on a `0xFE` NPC, or a stock capture: a save in a town with `0xFE` pursuers, explicit Talk to one (expect the brush-off and party damage), then Talk to the same NPC again. `Don't hurt me!` / `Please go away!` means it was rewritten; a second brush-off (log it, with its damage) means it was not. Note any other NPC that starts fleeing and any other state that changes. |
| Three line-feed layouts that rest on the printer being stubbed: no blank row between the six placard rows (from full-row suppression), one blank row between `Thou dost see` and a sign (from the later-call line-feed rule), and one blank row above `Something was stolen!` (same rule). The stored strings and the order of output are executed. *(Issue #300 Q13, Q20.)* | `formats/signs-dat.md` Section 6; `systems/view.md` Section 3; `systems/conversation.md` Section 10 | A screen capture of a Look at a sign, a Look at a coordinate with no record, and a completed conversation while the Shadowlord of Falsehood is resident. |
| The per-member flash and rumble of the `0xFE` damage pass. They were stubbed on this route; the shared damage path's presentation is assumed. *(Issue #300 Q19.)* | `systems/conversation.md` Section 2 | Capture an explicit Talk on a `0xFE` NPC, or execute the route with the per-member damage routine unstubbed. |

Opened 2026-10-25 by the issue #300 Q14, Q22, Q25, Q28 and Q29 turn-cost and command-layout pass (the issue #300 Q8 row on the turn cost of the town off-bed Hole-up refusal is closed: it was executed with the clock read back):

| Item | Where | What settles it |
|---|---|---|
| The turn cost of the C scene-gate `Not here!`. It reports acted by static reading of the dispatcher, and the one no-action C branch belongs to a scene-changing path. The cost was not measured. *(Issue #300 Q14, R604.)* | `systems/magic.md` Section 5; `systems/commands.md` Section 3 | Cast a spell outside its scenes in town and on the overworld, save at once, and read back the clock and turn-step counter. |
| The per-letter turn-cost rows marked *static* in the refusals-and-cancellations table: `B`, both `A` rows apart from town `Nothing to attack!`, town `K` `-On foot!`, overworld `K` `On foot!`, `P`, `W`, the typeahead toggle, and the `G` `I` `J` `L` `M` `O` `R` `S` `U` `X` `Z` group. *(Issue #300 Q14.)* | `systems/commands.md` Section 3 | The same save-readback probe per row. A mounted party (horse) settles town `K` and `A`; a carpet settles overworld `K`. |
| The New Order cancel at the second prompt and the same-slot no-op. They were reported executed, but the two scenarios actually keyed a first-prompt cancel and a leader refusal, so both rest on static reading. *(Issue #300 Q29, R607.)* | `systems/commands.md` Section 6 | Pick a non-leader, then press Escape. Separately, pick the same non-leader twice, moving the second highlight off the first slot. Read back the clock each time. |
| That `Klimb--On foot!` (town, horse) and `Klimb-On foot!` (overworld, not on foot) each fit one row. This is by arithmetic only: the first exactly fills the fifteen cells right of the marker. *(Issue #300 Q22.)* | `systems/commands.md` Section 5.8 | A screen capture of each refusal. |
| That a shipwright decline after a paid purchase in the same visit gives the sale-row bark (`113..116`). Static reading only; the clean-side capture covers only the fresh no-sale decline. *(Issue #300 Q25, R606.)* | `systems/shops.md` Section 8.C | Buy a Skiff, answer `Yes` to "anything else", decline the next offer, and note which bark row prints. |

Opened 2026-10-25 by the issue #301 Q4 and Q5 Blackthorn timing pass:

| Item | Where | What settles it |
|---|---|---|
| That the Blackthorn audience handoff and the captive-cell entry setup contain no tick-paced part. This rests on static reading; the timing fit over three cycle settings (each point ±17 ms) cannot on its own exclude a single one-tick edge wait of up to one tick period. *(Issue #301 Q4, R613.)* | `systems/blackthorn.md` Section 4.2 | Log every BIOS-tick delay request between the end of the exit script and the first town prompt in one executed run, or time the span at more cycle settings with a finer clock than video frames. |
| What makes up the rest of the reported ~0.5 s lead at the Blackthorn exit beyond the 0.34 s that a handoff at exactly 72 tick periods explains. A stock host slower than the 3000-cycle class, the lag between a physical key press and the original's key poll, and the reporter's capture method are all possible; attributing it to a slower host is inferred. *(Issue #301 Q4.)* | `systems/blackthorn.md` Section 4.2 | The reporter's cycle setting, and a paired capture that times both runs from the frame in which the key-wait cursor glyph is overwritten. |

Opened 2026-10-25 by the issue #300 Q31 and Q32 combat-hit and dungeon-footstep audio pass:

| Item | Where | What settles it |
|---|---|---|
| The wall-clock durations of the combat hit bursts (party about 188 ms, monster about 216 ms), the electric push-back rumble (about 92 ms) and the footstep bursts (about 2.8 / 2.0 / 1.3 / 0.55 ms). The parameters were executed; the durations are the static rumble model. | `systems/audio.md` Sections 5.3 and 10.2; `systems/combat.md` Section 11.1; `systems/dungeon-mode.md` Section 8.1 | A stock speaker capture of a combat exchange (one party hit, one monster hit) and of an electric-field step, with sound on. |
| When the footstep tail's 7 and 3 sound during an idle command wait. "Roughly 110 and 220 ms into the wait" is inferred from the loop shape: each idle iteration waits to the next BIOS tick edge and also pays a view raster, so the cadence is about one BIOS tick or more per iteration. | `systems/audio.md` Section 7.4; `systems/dungeon-mode.md` Section 8.1 | A stock capture of a single dungeon step followed by no key, timing the four bursts after the step pair. |

Opened 2026-10-25 by the issue #302 Q2 and Q3 Z-stats and signs pass (the issue #300 Q13 section 3 item on the `SIGNS.DAT` read-window length is closed: the window is 2000 bytes, `formats/signs-dat.md` Section 5):

| Item | Where | What settles it |
|---|---|---|
| The Z-stats message-window echo: that `\nStatus:_` is printed in the message window after the selector's `Player:_` echo and before the pages are drawn, and whether it is also printed on the `0` (shared Equipment) answer and on the combat entry that skips the selector. Static reading only. Also static: the attribute page's name centring on the frame line and the status-name centring (the executed probe stubbed both). *(Issue #302 Q2, R622.)* | `systems/inventory.md` Section 4.7 | A capture of the message window and panel across Z, a member choice, one page and Escape; and one Z answered with `0`. |
| What the original prints when a sign lookup with no match inside its 2000-byte window scans on into the memory after the window. It depends on that memory; executed probes showed both the placard and spurious matches past the window. *(Issue #302 Q3, R623.)* | `formats/signs-dat.md` Section 5 | A DOSBox memory capture at a Look on a sign tile with no record (which needs such a tile or a modified data file). |

Opened 2026-10-25 by the issue #302 Q6 Sleep Field pass:

| Item | Where | What settles it |
|---|---|---|
| A party member falling asleep on a Sleep Field in combat: no `slept!` line, the banner and `>Zzzzz...` on every own turn, and the immediate re-sleep after a successful wake draw, so the member stays asleep while the field lasts; the field dissolves at random during maintenance, which also runs on the sleeper's own asleep dispatches *(corrected 2026-10-28, issue #309: formerly "so the member never acts again that combat"; retracted, `RETRACTIONS.md` R651)*. Executed on the original routines with printer, generator and frame stubbed; no capture. *(Issue #302 Q6, R624.)* | `systems/combat.md` Sections 8.1 and 11 | A stock capture of a member stepping onto a cast In Zu Grav field and holding through several turns. |

Opened 2026-10-26 by the issue #303 Q2 Stonegate fall-timing pass:

| Item | Where | What settles it |
|---|---|---|
| Which Stonegate fall duration lies nearer period hardware: DOSBox 0.74-3 at fixed 3000 cycles measured 27.49 to 27.52 s with three members and 26.78 s with one; a reported DOSBox Staging run at 3000 cycles measured about 26.8 s with its party size unreported. That a one-member party explains the Staging figure, and that any remaining three-member shortfall (about 2.6 percent) is an emulator difference, is inferred; Staging was not run. The static period model (about 27.5 s or a little more for three members, panel drawing unpriced) and the calibrated unit's band (about 24 to 30 s) cannot separate the two. *(Issue #303 Q2, R625.)* | `systems/blackthorn.md` Section 7.1; `systems/audio.md` Section 10.5 | The party size of the Staging capture; then a period-hardware or cycle-accurate capture of a Stonegate fall with a known party size. |

Opened 2026-10-26 by the issue #303 Q3 prompt world-step pass:

| Item | Where | What settles it |
|---|---|---|
| A shop prompt (entry Y/N or a shop menu) and a Talk, Look or Search direction prompt holding live while the world keeps stepping. The shop Y/N and direction readers were executed with the keyboard poll and world step stubbed and counted; the one reproducible live run is the `Exit to DOS? ` wait in Skara Brae, and the Talk/Look/Search live run cannot be reproduced from its kept provenance. *(Issue #303 Q3, R626.)* | `systems/input.md` Section 2; `systems/timing.md` Section 8.2 | A stock capture at a shop prompt and at a direction prompt, from saves standing beside a shopkeeper and an NPC. |
| That every gameplay prompt keeps the command prompt's random draws, draw for draw. World steps were counted per no-key pass; draws were not, so this rests on the world step's published content. Whether the cadence of the view's animation at a prompt matches idle exactly (not just that it animates) was likewise not measured. *(Issue #303 Q3, R626.)* | `systems/input.md` Section 2; `systems/conversation.md` Section 10 | A capture of the random stream and frame timing across a held prompt and the same span at the command prompt. |
| Dungeon-room combat stepping the world at its prompts. It follows from combat's scene value lying outside the band; that value was executed in the reader probe, but that dungeon-room combat stores it rests on static reading of the dungeon code. *(Issue #303 Q3.)* | `systems/input.md` Section 2; `systems/timing.md` Section 8.2 | Execute a prompt inside dungeon-room combat with the scene value and world-step count observed. |

Opened 2026-10-26 by the issue #303 Q4 town horse-walker pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the ordinary per-turn schedule processor ever steps or re-places a schedule-stationary roster horse between reseats, which would snap a walked horse back to its waypoint mid-visit. The reseat triggers (entry, floor change, inn rest, each Hole-Up bed step) are published; only the ordinary per-turn walker is untraced. *(Issue #303 Q4, R627.)* | `systems/town-mode.md` Section 16 | A capture in a horse location over several turns and one hour boundary, without changing floor or resting, with the horse's sprite position and runtime coordinate observed. |
| That the inn-rest and H-Hole-Up bed reseats erase a riderless horse left by X-it dismount inside a town. It is the same clear-and-re-place pass whose floor-change case was executed (issue #308 Q1: the dismounted horse was moved one cell by the town walker on the next turn, a single observed step, and was gone after a ladder round trip); the inn and bed callers were not executed. *(Issue #303 Q4; narrowed 2026-10-28, issue #308 Q1.)* | `systems/town-mode.md` Section 16 | Dismount a horse inside a town, rest at an inn or in a town bed, and observe whether the riderless horse remains. |
| That walk-on stairs, the metal grate and the generic trapdoor drop run the same full reseat as the executed ladder Klimb, and that the same-floor reload after an NPC death skips it. All rest on static reading of the town overlay's floor-change and reload callers; floor changes owned by other overlays inside a location were not surveyed. *(Issue #308 Q1.)* | `systems/town-mode.md` Sections 3 and 11 | Park a carpet beside a staircase (for example in Moonglow), walk up and back down, and check whether the carpet remains; repeat across a trapdoor in Lord Blackthorn's Castle; kill an NPC with a carpet parked on the floor and check it survives. |

Opened 2026-10-26 by the issue #304 Q1 fall-chain pass:

| Item | Where | What settles it |
|---|---|---|
| The random draws taken by each fall-chain landing repaint, and whether the departure level's monster is painted in the landing view while the record still holds it. Static reading only; the repaint was stubbed in the executed runs, so the exact draw count per landing depends on what is in view and is not established. *(Issue #304 Q1.)* | `systems/dungeon-mode.md` Section 8; `systems/prng.md` Section 4 | A stock capture of the random stream at a fixed clock across a fall chain, compared against the engine's own repaint draw counts, first for landings whose views hold neither a flavour wall ahead nor the old monster, then for landings that do. |

Opened 2026-10-26 by the issue #304 Q4 and Q5 wait-caller and preview-draw pass:

| Item | Where | What settles it |
|---|---|---|
| The per-pass draw cost of the shrine and Codex prompts' extra world steps. Each no-key pass was shown to run one world step, but the draws were not counted; the cost is inferred from the published per-step content. *(Issue #304 Q4, R628.)* | `systems/karma.md` Sections 7 and 8.2 | A live random-stream capture at a fixed clock through a shrine entry with a known number of no-key passes at the virtue prompt. |
| That the endgame's six narrative page waits run no world step and no cursor blink. Static reading only. *(Issue #304 Q4.)* | `systems/endgame.md` Sections 8.3 and 8.4; `systems/input.md` Section 2 | A live capture of a narrative page wait from an endgame save, with viewport animation and the random stream observed. |
| The two unexecuted arms of the Blackthorn capture narration: the sound-off count of three {five-tick timer wait, sting} repetitions after the dragged-away line, and the cinematic-animation-off path, in which every quiet pause, world ticks included, does nothing. Both are static reading; only the sound-on, animation-on path was captured. *(Added 2026-10-26, issue #304 Q6.)* | `systems/blackthorn.md` Section 3 (capture narration timeline, steps 7 and 9 to 18); `systems/audio.md` Section 8.6 | One emulator capture with sound off and one with cinematic animation off, with the stings counted and the line times recorded. |

Opened 2026-10-27 by the issue #305 Q1 dungeon contact-launch pass:

| Item | Where | What settles it |
|---|---|---|
| That the active monster's two pose draws are the only extra draws before the room painter in issue #305's two black-box contacts. Those scenes were not reconstructed; the claim is inferred from their two-draw offset, and holds only if nothing else in view draws for the corridor painter. Also that the shared world tick never runs in a dungeon corridor scene beyond the executed contact, A-Attack and idle paths, which rests on a call census of both dungeon overlays and the scene-band rule. *(Issue #305 Q1.)* | `systems/dungeon-mode.md` Sections 4.1 and 14 | A stock random-stream capture at a fixed clock reproducing one of the issue's contacts with the view contents recorded, and one through a longer stretch of corridor play counting world ticks. |

Opened 2026-10-27 by the issue #305 Q2 and Q3 walker and spawner-draw pass:

| Item | Where | What settles it |
|---|---|---|
| That the encounter spawner's candidate coordinate (scroll base plus a `0..31` draw on each axis) wraps modulo 256 when the window straddles the map edge. Static reading only; the executed runs used scroll bases that never reached the wrap. *(Added 2026-10-27, issue #305 Q3.)* | `systems/encounters.md` Section 4, step 1 | An emulator capture of a spawn with the scroll base within thirty-one cells of the map's far edge on either axis, with the forced draws chosen to cross it. |

Opened 2026-10-27 by the issue #305 Q4 contact-rule pass:

| Item | Where | What settles it |
|---|---|---|
| The outdoor contact rule is static reading only: diagonal neighbours never engage, a party push into a monster prints `Blocked!` with no clock advance and no combat, and the reaction falls in the next walker pass that runs, which can be an extra difficult-terrain pass inside the step. The town half, that a blocked step counts as acted and the adjacent conflict NPC raises its contact in that epilogue, rests on the published `systems/npc-schedules.md` Section 9 rule, which this pass did not re-verify. *(Issue #305 Q4.)* | `systems/encounters.md` Section 2.1; `systems/active-objects.md` Section 8; `systems/movement.md` Section 7; `systems/town-mode.md` Section 14 | An emulator capture standing diagonal to a spawned monster for one turn (expect no combat), then pushing into an orthogonally adjacent one (expect `Blocked!`, no clock advance, combat only on the next pass), and one on forest to time the extra pass; plus a town push into a conflict NPC. |

Opened 2026-10-27 by the issue #305 Q5 first-world-tick pass:

| Item | Where | What settles it |
|---|---|---|
| The one black-box run in seven whose offset differs from the constant `+1` is not identified. From the issue's seed in daylight at sea neither a wind change nor a water encounter can fire in the first seventy or so draws, which leaves three inferred candidates: a Rough seas death changing the member count `N` on a later turn, a no-key poll count that differs from the model by one, or a spawn at night only (hours 0 to 4, where the water threshold of four is static reading). *(Added 2026-10-27, issue #305 Q5.)* | `systems/overworld.md` Section 5 (the draw-order list) | That run's per-prompt no-key poll counts or command log, its game hour, or its end-state stock save. |
| The `+1` attribution to the bare first tick assumes the engine already takes the Rough seas impact tick's wind draw (`systems/overworld.md` Section 6.2.5, R642) and that the offset stays constant across turns. An engine following the earlier "exactly `N`" text and still drawing at the first entry step would also sit one draw short at the first damage. *(Added 2026-10-27, issue #305 Q5.)* | `systems/animation.md` Section 13.2; `systems/overworld.md` Section 6.2.5 | A clean-engine draw log for one of the runs compared turn by turn against the executed trace in `systems/overworld.md` Section 5. |
| The gate byte's value in a save written on the Tandy adapter. No Tandy save was examined; one made before any no-key idle pass is expected to hold the Tandy sentinel, which would still take the wind draw. Also that mode entry never draws outside the executed case (open sea, no active objects in view), which is static reading. *(Added 2026-10-27, issue #305 Q5.)* | `formats/saved-gam.md` Section 10 (`0x02EB`); `systems/overworld.md` Section 5, step 1 | A Tandy-adapter save capture issued with no idle poll; a mode-entry draw capture with active objects in view. |
| The order of the step 6f party-status and provisions work relative to the step 6g underfoot arms. The draw-order list places the underfoot arms, then the Underworld earthquake check, then Rough seas; the private trace summary listed the underfoot arms before the party-status work, which disagrees with the published f/g order, and this pass did not settle which is right. *(Added 2026-10-27, issue #305 Q5.)* | `systems/overworld.md` Section 5, step 6 and the draw-order list | An executed consumed-turn trace on swamp or lava with a party-status effect pending. |

Opened 2026-10-27 by the issue #306 Journey Onward load-path pass:

| Item | Where | What settles it |
|---|---|---|
| Period-hardware duration of the Journey Onward path from the key read to the first command-wait pass, with and without the step 4 tile-archive load. The path has no waits, so it is pure host-speed work. It is published only as a DOSBox 0.74-3 timing at fixed 3000 cycles; no 1500-cycle run was taken to show how it scales. *(Added 2026-10-27, issue #306.)* | `systems/intro.md` Section 7 ("Timing of the load path"); `systems/timing.md` Section 8.2 | A cycle-accurate run or a frame-timed capture on 4.77 MHz EGA hardware; a 1500-cycle DOSBox run for the scaling. |
| That `A`, `U`, `C` and `T` reset the intro scene state to the menu state so that a later `J` reloads the tile archive, while only Return-to-View runs leave it moved on. Static reading of the menu dispatch only. The executed run covered step 4 with the scene state forced to the menu state, and the display driver's share of step 4 (the in-place conversion) is static only, because the driver was stubbed. *(Added 2026-10-27, issue #306.)* | `systems/intro.md` Section 7, step 4 | An emulator capture timing `J` after `R` and then after `R` followed by `A` (expect about 1.7 s more at 3000 cycles in the second case), and one with the stock display driver executed through step 4. |
| The reconciliation with the reporter's draw table is inferred. Subtracting their engine's 67 ms from the measured range gives 4 to 6 draws depending on the menu phase, so their constant 5 needs a boot that reaches the menu at a reproducible phase. Their "151 or 153" row could come from first-idle instants straddling a tick edge, or from an ambiguous HP-to-draw inversion with 152 excluded. *(Added 2026-10-27, issue #306.)* | `systems/intro.md` Section 7 ("Timing of the load path") | The reporter's per-run boot-to-menu timing, or the stock draw count read directly instead of being inverted from HP. |

Opened 2026-10-28 by the issue #308 Q3 field-marker pass:

| Item | Where | What settles it |
|---|---|---|
| No capture shows a combat field marker dissolving. The 1-in-16 removal pass was executed in isolation on the original code, and its place in the maintenance endpoint is static reading. *(Issue #308 Q3, R650.)* | `systems/combat.md` Section 11 ("Field markers dissolve at random") | A stock save in which a field is placed in combat, followed by several committed actions, with the marker records and draw count observed. |
| No capture shows a sleeper on a Sleep Field escaping. That the asleep, dragged-under and Sword of Chaos arms enter the maintenance endpoint was executed on the original chain, and the escape statistics (mean 31.6 asleep dispatches over 120 seeds) were executed with world ticks stubbed; the dragged-under release routine, the automatic driver body and the tail's post-action step were stubbed in every run, and the per-living-wearer regeneration rule ran with one wearer only *(narrowed 2026-10-29, issue #310 Q1: that rule has since been executed with two wearers, including the sweep on a sleeper's waking dispatch)*. *(Issue #309.)* | `systems/combat.md` Section 11 ("The three keyless arms enter the endpoint" and the sleeper paragraph) | A stock capture from a dungeon save: a member steps onto a cast In Zu Grav field while the others leave the arena, and the count of `>Zzzzz...` turns before the next prompt is observed over several trials (expected finite, about 31 on average). Shipped room data places no Sleep Field marker (issue #308), so the field must be cast. |

Opened 2026-10-29 by the issue #310 Q1 and Q2 wake-ring and combat world-tick pass:

| Item | Where | What settles it |
|---|---|---|
| Several per-dispatch world ticks in combat rest on static reading or inference, not execution: accepted Escape's tail tick, the dragged-under and Sword of Chaos tail ticks (reached only with ticks stubbed in the issue #309 runs), the applied in-arena rock climb, and the automatic driver's step tick on the step that leaves the arena. Only `K` then Space `Pass` at the adjacent prompt was executed among the Klimb paths. *(Issue #310 Q2.)* | `systems/combat.md` Section 11 ("Which combat dispatches run a world tick") | Execute those paths in a full original-code harness with every draw attributed to its world tick, or a stock capture of each. |
| The arena per-tick draw figures come from one grass-arena orc encounter on one seed, and the animator count scales with the combatant set and scripts. Not run in an arena: gazer pauses, mimic and corpser freezes, the two coinless classes, and party-side attack presentations (whether they run the same two presentation ticks as the one executed monster melee hit). *(Issue #310 Q2.)* | `systems/combat.md` Section 11 ("Which combat dispatches run a world tick") | Repeat the attributed-draw run with those monster classes and with party-side melee, missile and spell attacks. |

Opened 2026-10-29 by the issue #311 Q1 to Q3 literal pass:

| Item | Where | What settles it |
|---|---|---|
| The Yell print order for a recognised Word of Power (uttered line, then the flash / rumble, then `No effect!` only when no cardinal neighbour qualifies) and Yell's own line feed after a nonempty input line are static reading of the handler only; the literals themselves were read from the shipped data. *(Issue #311 Q1.)* | `systems/commands.md` Section 11.1 | A capture of the message window after a recognised word at a qualifying entrance, at a wrong coordinate and with no qualifying neighbour. |
| The full-party `0x84` keystroke wait before the refusal is static reading only, and the refusal's wrapping in the sixteen-column message window is inferred; the emulation run stubbed the key routine, the line reader and wrapping, and confirmed only the on-screen framing and the return to `Your interest?`. *(Issue #311 Q2, R655.)* | `systems/conversation.md` Section 7.6, the `0x84` row | Run `JOIN` with a six-member party under emulation with the real key routine and printer, and observe the pause and the wrapped rows. |
| The status-name start columns on the attribute page (26, 27, 29, 28, 28) are inferred from the published centring rule because centring was stubbed in the executed probe, and `Dead` and `Charmed` were never looked up in a run (data file only). What the page shows for a status letter outside the five is not established. *(Issue #311 Q3.)* | `systems/inventory.md` Section 4.7 (the status table) | A screen capture of the attribute page for members in each of the five states; a trace of the lookup for an unlisted letter. |

Opened 2026-10-29 by the issue #311 Q4 to Q6 literal pass:

| Item | Where | What settles it |
|---|---|---|
| The dungeon L-Look field lines and their exact-byte selection are static reading with the literals read from the shipped data; no live Look at a placed field cell, plain or visit-marked, has been made. *(Issue #311 Q4.)* | `systems/dungeon-mode.md` Section 12, step 5 | A live dungeon Look at each of `0x80..0x83` and at a visit-marked field cell. |
| The Doom absorption narration (line feed, dispatched slot's name, ` is absorbed!` and a line feed) is static reading; no capture of the absorption exists, and whether a controlled or charmed monster slot can ever stand on the qualifying cell in stock Doom data, and so be named by class, was not shown either way. *(Issue #311 Q5.)* | `systems/combat.md` Section 11 (the Doom absorption paragraph) | A capture of the absorption in the final Doom room; a census of which slots can reach arena row `2` under the Doom source in stock data. |

Opened 2026-10-29 by the issue #312 Q3 Wind Change scroll pass:

| Item | Where | What settles it |
|---|---|---|
| The Wind Change scroll's failure transcript outside the wind scenes (`Wind change!`, the `Direction-` prompt, then `Failed!` on its own row with the cast-failure glissando) and the prompt ignoring Escape are static reading plus shipped strings; no use of the scroll in a dungeon or in combat has been captured, and that Escape is ignored assumes the command reader never maps Escape to a cardinal key or Space. *(Issue #312 Q3.)* | `catalogs/item-list.md` Section 7.1, row 1 | One live use of a Wind Change scroll in a dungeon and one in combat, including an Escape press at the direction prompt. |

## 3. Needs a further static trace

The corridor mirror derivation was completed 2026-09-07: original EGA
blitter execution confirms the one-pixel-left phase and the caller's nominal
anchors produce the R394 coordinates. The orientation/mask distinction is
corrected in `systems/display-driver-abi.md` Section 5.1 (R421).

Opened 2026-09-12 by the issue #262 Klimb and dungeon-object passes:

| Item | Where | What settles it |
|---|---|---|
| Combat's own K-Klimb contract. The pass established only that combat is a fourth prefix owner - its handler prints its own `Klimb-`, then a separate two-way marker and one of the climb or refusal words, and tests the same two ladder tile identities the town handler uses. *Narrowed 2026-10-17 (issue #299 Q4): the current-cell order, the `U/D-` and adjacent-prompt keys, the adjacent targets and the turn costs are now published from an executed run of the handler plus a static reading of the parser (`systems/combat.md` Section 8.4); only the non-dungeon callers' use of codes 5 and 6 remains, indexed below.* *Narrowed 2026-10-17 (issue #299 Q13): the refused-departure cost (free, short re-prompt) and the refusal rows are published from an executed run with the real edge helper.* | `systems/doors-and-z-transitions.md` Section 9; `systems/combat.md` Section 8.4 | A dedicated pass over the combat climb handler and its combat-side caller, including the arena-exit path the published combat text mentions. |
| What reads the resident tile-restoration flag besides the combat framer. The census still counts two reads; the Klimb handler is no longer one of them (R471), so the second is unattributed. Whether the rest of that flag's published contract - its setter, its clears, the framer's restore - survives is untested. | `systems/dungeon-mode.md` Section 14.1; `systems/combat.md` Section 4 | A fresh reader census of the flag byte, separate from the retraction. |
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
| Which location and tile reach the shrine/urn presentation through the town/location turn loop's automatic entry arm, keyed on a different tile through a resident gate, and whether it lands the party on a shrine. *Narrowed 2026-10-18 (issue #299 Q29): the natural-moongate midnight route is settled (`systems/overworld.md` Section 9.2, `systems/karma.md` Section 7); it runs the Spirituality meditation where the party stands and leaves the party on that overworld cell.* Section 7's fall-through paragraph must not be read as if it answered the town-loop route. | `systems/karma.md` Section 7; `catalogs/gazetteer.md` Section 7 | Execute the town/location turn loop's automatic entry arm and establish which location and tile reach it. |
| The rendering cost and side effects of one world step inside a presentation hold. The hold's text-inertness is executed and closed, and its wind-draw count is published, but the per-step viewport rebuild, the ambient audio tick's contribution and the wind drift's own randomness were never priced for this path. Every seconds figure for a shrine entry rests on them. | `systems/karma.md` Section 7; `systems/animation.md` Section 13.5; `systems/audio.md` Section 11 | Price one world step against the loaded shrine display grid, the same run the Blackthorn ambient-tick item above needs for its own grid. *Extended 2026-09-12 (issue #271 follow-up): a completed meditation spends sixty-one more such steps after the closing record, seventy-three on the turn-in arm, so this one unpriced term is what keeps every figure in `systems/karma.md` Section 7.2 a floor rather than an estimate.* *Data point 2026-10-26 (issue #304 Q8): at DOSBox 3000 cycles (EGA) a full rebuild on the approach walk measured about 0.3 to 0.5 tick (approximate, ±0.3 tick, including up to one frame of display latency), inside one tick; the ambient tick and wind drift were not separated, and no period host was measured.* |
| What the compositor draws under the avatar during the approach walk. Both harnesses stub the terrain probe the sprite-stamp path consults before choosing its branch, so the walk's frame-by-frame sprite results are executed against a synthetic reading of the ground even though the display grid itself is real. *Narrowed 2026-09-13 (issue #273): the actor cell itself does not depend on it. The compositor's presentation branch skips the floor-match gate and both viewport bounds tests, and an executed control that forces the slot's layer value to disagree with the scene's for a whole presentation paints a byte-identical sequence; the shrine record's centre column is open grass from the rest cell down to the bottom row. What is still unexecuted is the ground the backdrop paints under the sprite, and the display driver itself, which is stubbed at its entry in this pass too.* | `systems/karma.md` Section 7 | Run the walk with the terrain probe live against the shrine display record. |
| Whether the keyboard queue behaves as modelled underneath the type-ahead result. "Nothing in a presentation hold consumes a key" is executed at the program's own fetch site and the no-flush negative is a whole-corpus census of the shipped images; the underlying BIOS and DOS key services themselves were read rather than run. | `systems/karma.md` Section 7; `systems/input.md` | Type ahead through a shrine entry on a real installation and confirm the queued answer reaches the virtue prompt. |

Opened 2026-09-12 by the issue #269 rescue-narration pass:

| Item | Where | What settles it |
|---|---|---|
| Whether a stats-panel repaint's two single-scanline fills can ever touch rows inside the message-window rectangle. The scroll half is closed - a repaint issues none, and no command against the message window's descriptor - but the fills were recorded by command index only, and their coordinates live in state the intercepted driver call never consumed. | `systems/stats-panel.md` Section 2.1; `systems/blackthorn.md` Section 7.2 | Execute a repaint with the fill coordinates captured, and compare them with the message window's rectangle. |
| The level-from-experience curve over the full experience range, and whether the level is clamped at the top. The rescue's recomputation was observed only over the experience values the executed standings produced. | `systems/blackthorn.md` Section 7; `formats/saved-gam.md` | Sweep the recomputation across the experience range, including values that would exceed the top level. |
| What the castle location load prints into or clears from the message window after the cinematic returns. The published handoff frame describes the instant the handler returns and nothing after it. | `systems/blackthorn.md` Section 7.2 | Continue the executed run through the castle location load with the message window observed. |

Opened 2026-09-12 by the issue #271 closing-sequence pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the whole-window counts of the closing beat hold when executed rather than derived. The handler's own contribution - the envelope runs, the inversion, the ten-step wait and the absence of any tick cost in the sound - was executed; the sixty-one and seventy-three world steps, and the matching delay requests, repaints and wind draws, were re-derived from the presentation's exit structure in the same pass rather than re-run on the frame harness. The exit's eleven-frame Codex variant is derived the same way. | `systems/karma.md` Sections 7 and 7.2 | Run all three completion arms and the Codex exit on the frame harness with the world step, the compositor and the real one-tick delay live, and count the steps. |
| Whether the shrine presentation's per-frame sting is the shared short two-part sting. `systems/karma.md` Section 7.2's wall-clock floors price it at that recipe's 27 ms, and `systems/timing.md` Section 7.6 item 10 still records the sting as unpriced; the identification was assumed in this pass, not established. *Data point 2026-10-26 (issue #304 Q8): a DOSBox 3000-cycle capture measured the per-frame sting's audio burst at about 20 to 25 ms, which does not by itself identify the recipe.* | `systems/karma.md` Section 7.2; `systems/audio.md` Sections 7.5 and 10.2; `systems/timing.md` Section 7.6 | Read the presentation's per-frame sound call through to its recipe and compare its parameters with the shared two-part sting's. |
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
| On the Underworld plane, whether anything repaints the two screen rows the dungeon's level and facing labels occupied, given that neither the top header band nor the wind banner is painted there. The viewport rasteriser is an endpoint in every probe on this path. *Narrowed 2026-10-25 (issue #300 Q35): executed in isolation, both painters take their erase arms for the underworld level value and the two erase rectangles cover the label cells (`systems/moons.md` Section 3); the arrival sequence itself was not stepped.* | `systems/doors-and-z-transitions.md` Section 12.1; `systems/dungeon-mode.md` Section 4.1 | Execute an underworld arrival with the full-screen window's cells recorded, with the rasteriser live. |
| The dungeon-entry advance count and the chrome-overwrite reasoning were not re-executed in the verification pass; the covering arithmetic was checked statically only. | `systems/doors-and-z-transitions.md` Section 12.1; `systems/commands.md` Section 5.5 | Re-execute the surface-to-dungeon entry beat and the overworld re-entry chrome in a second harness, as the exit beat was. |
| The dungeon turn loop's own post-climb break path is still read from the bytes rather than executed, in both passes. It needs an overlay-sharing arrangement neither harness provides. | `systems/dungeon-mode.md` Section 13.4 | An execution harness that can stage the two overlays sharing the loop's base, or a live capture across the break. |
| Whether the stats panel's ship row can reach the wrapping column through a transport marker outside the ship family that still satisfies the same test. Only the family members and a few non-members were exercised. | `systems/stats-panel.md` Section 6 | Sweep the whole marker byte range against the row's selection test. |

Opened 2026-09-13 by the issue #272 mixer-prompt pass:

| Item | Where | What settles it |
|---|---|---|
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
| Whether the three Blackthorn-overlay transport-marker writes behave as read. They are the only marker writers in the shipped set that were never executed; the claim that one of them reaches the screen as the description table's corpse tile rests on a byte read plus the established slot path. *Data point 2026-10-25 (issue #301 Q5): a DOSBox capture of a Stonegate wipe shows a single prone figure at the viewport centre after the rescue's conditional world tick, consistent with the corpse tile; the marker write itself was not observed.* | `systems/blackthorn.md` Section 6.1; `systems/vehicles.md` Section 2 | Execute the Blackthorn cutscene arms that write the marker and record the painted cell. |
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

Opened 2026-10-17 by the issue #299 Q2, Q4 and Q5 pass:

| Item | Where | What settles it |
|---|---|---|
| Whether a dungeon camp-attack fight can carry the two-way-ladder flag. The arena `U/D-` test accepts the mode bit that dungeon contact and dungeon camp-attack fights share; the published "only place the two-way prompt can appear" rests on the flag being set only by the contact room painter. *(Issue #299 Q4.)* | `systems/dungeon-mode.md` Section 14.1; `systems/combat.md` Section 8.4 | Trace the flag's writers and clears against the dungeon camp-attack entry. |
| What a town or overworld combat caller does with an Up/Down departure code (5 or 6). No stock `BRIT.CBT` arena can produce one; a custom arena with ladder tiles would. *(Issue #299 Q4.)* | `systems/combat.md` Section 8.4 | Read the town and overworld post-combat paths for exit codes 5 and 6. |
| Whether any viewport cell holds the companion band's paint-nothing sentinel during the camp member pass. Such a cell is not repainted by the world-tick pause and would keep its inverted pixels. *(Issue #299 Q5.)* | `systems/rest-and-camp.md` Section 7.1 | Trace the viewport buffers' contents from the old man's appearance through the member pass. |
| Whether the low-colour accent-pen value 3 inverts every pixel on the CGA and Hercules drivers, in particular on the one-bit Hercules mode. On the sixteen-colour drivers 15 is all ones; the low-colour drivers' mapping of 3 for an exclusive-or rectangle was not traced. *(Issue #299 Q5.)* | `systems/rest-and-camp.md` Section 7.1 | Read the CGA and Hercules rectangle routines' colour mapping in exclusive-or mode. |
| Whether the shipwright's ordinary-offer `No` returns to the F/S menu (record `119`). This rests on one static reading; the second reader confirmed the row placement but did not trace that jump. *(Issue #299 Q2.)* | `systems/shops.md` Section 8.C | Trace the ordinary-offer decline arm to its next print. |

Opened 2026-10-17 by the issue #299 Q3 and Q7 dungeon passes:

| Item | Where | What settles it |
|---|---|---|
| The display-mode condition under which the dungeon corridor painter reloads the active monster's sprite-state byte from the family's presentation record instead of using the stored byte. Its existence is established; the condition is not published. *(Issue #299 Q3.)* | `systems/dungeon-mode.md` Section 4.1 | A trace of the painter's sprite-state source, naming the condition in mode terms. |
| That no block or indirect write changes the transport state underground, and that loading does not normalize it. The underground-writer census counted direct writes only; the no-normalization claim rests on the earlier save-load analysis, and no direct write was found in the load path. *(Issue #299 Q7.)* | `systems/active-objects.md` Section 10 | A census of block and indirect writes covering the transport byte, including the save-load path. |

Opened 2026-10-18 by the issue #299 Q20 and Q21 scoped-prompt pass:

| Item | Where | What settles it |
|---|---|---|
| Two labelled-block census details. (a) An independent recount finds 27 blocks in which the label repeats after the head, where the earlier census said 28; 22 of the 27 are self-GOTO default arms, and neither the other five placements nor the one-block difference is itemised. (b) The splits of the 259 prompt-opening blocks by default-arm ending (168 / 35 / 22 / 31 / 2 / 1), the 54 heads that stop first, the 191 single-keyword and 29 keyword-less blocks and the 27 alias answers come from one census pass; only the block, final-marker, self-GOTO and `y`/`n` counts were recounted. No behaviour depends on either. *(Issue #299 Q20.)* *Narrowed 2026-10-19 (issue #299 Q22): a second census confirmed the 259 prompt-opening blocks and the 54 heads that stop first (53 with nothing after the head, one with a stray record), and corrected the fall-back split to 169 with no "malformed" arm; the 35 / 31 / 2 splits, the 191 and 29 counts and the 27 alias answers are still single-pass.* | `systems/conversation.md` Section 7.7 | A second census of the four shipped `.TLK` files that lists each block whose label repeats after the head, with the record position, and recounts the default-arm splits. |
| Get's cascade refusal and dirty marking. With a staged rotting body or moldy corpse on ordinary terrain, Get falls through to the tile cascade's `Nothing to get!` and the inventory and body object are unchanged (executed); whether that refusal marks the inventory/status view dirty or sets the turn sentinel was not checked separately. *(Issue #300 Q2.)* | `systems/containers.md` Section 3, the staged-body paragraph | Run the original Get on a body over a plain tile and record the dirty marking and turn sentinel after the refusal. |
| The class written into a combat-created body slot. Section 9 says the post-combat reconciler rewrites a restored body-family slot into the family "consumed by Search/Get"; Get never acts on classes 30 or 31, so if the reconciler writes one of those, only Search's corpse branch reaches the slot. Which class it writes was not checked. *(Issue #300 Q2.)* | `systems/containers.md` Section 9, combat-created body/retrieval slots | A static trace of the reconciler's rewrite, naming the class it stores, or a capture of Get and Search on a post-combat body. |
| Potion presentation and the gameplay generator. The potion probe stubbed the shared flash/sound presentation and the target selector, so "the presentation draws nothing from the gameplay generator" and "a cancelled target consumes no draw" rest on a static reading (no direct generator call found in those helpers) plus `systems/audio.md` Section 5.3, not on execution. *(Issue #300 Q23.)* | `catalogs/item-list.md` Section 7.2, draw order of the variation roll | Execute the original presentation and target selector unstubbed and compare the gameplay generator state before and after, including one cancelled target. |

Opened 2026-10-25 by the issue #300 Q5, Q7 and Q18 town pass:

| Item | Where | What settles it |
|---|---|---|
| That none of the endgame's resident helpers writes the top or bottom viewport band. The analyst's static claim; not re-audited independently. *(Issue #300 Q5.)* | `systems/endgame.md` Section 3.1 | An independent census of band writes over every helper the endgame calls before the full-screen phase. |
| Which NPC a refused arrest fights on the explicit-`T` route (town result `2`). The follow-up target is the roster index in the retained contact state, and on this route cleanup calls the arrest even when that index is `0` or stale. *(Issue #300 Q7, R591.)* | `systems/town-mode.md` Section 14 | A static trace of what Talk writes to that state, or a run that refuses a Blackthorn-regime demand through explicit `T` while another NPC's contact is retained. |
| Stonegate's three `0xFC` roster figures as A-Attack targets: valid, arena 10, no karma, alarm or removal mark, no re-install, repopulated on the next fresh entry. Static reading of the target rules and the shipped roster. *(Issue #300 Q18.)* | `systems/town-mode.md` Section 10 | Attack one of the figures in Stonegate and re-enter. |
| That a target standing on a terrain-arm cell (the stocks set) takes that arm rather than the conflict chain, for a Shadowlord included. Static reading. *(Issue #300 Q18.)* | `systems/town-mode.md` Section 10 | Trace the terrain arm's cell set against the Shadowlord home cells, or attack an NPC standing in the stocks. |

Opened 2026-10-25 by the issue #300 Q9 and #301 Q6 combat pass:

| Item | Where | What settles it |
|---|---|---|
| Three static parts of the split rule: that an off-arena draw redraws both axes (the executed corner case cannot tell this from a per-axis redraw), that a successful placement adds exactly one range draw for the speed variation (the speed roll was stubbed), and that the wound-grade result line follows `divides!` (the narrator was not run). *(Issue #300 Q9, R593, R594.)* | `systems/combat.md` Sections 11.1 and 12 | Execute the split with an unstubbed speed roll and narrator, and a corner case whose draws separate the two redraw readings (one axis in range, one out). |
| Whether outdoor hostiles ever stand on swamp tiles, which decides how often the swamp arena appears. The arena choice itself (the hostile's own tile, never the party's) is settled; the outdoor monster walkability rule for swamp was not examined. An implementation that fights in the swamp arena where the stock fights in grass should check both its arena tile source and its monster walkability on swamp. *(Issue #301 Q6.)* | `formats/cbt.md` Section 6; `systems/encounters.md` Section 4 | A static trace of the outdoor monster movement acceptance for tile `4`, or a census of outdoor hostiles' cells during a long swamp walk. |

Opened 2026-10-25 by the issue #300 Q12, Q13, Q19, Q20 and Q21 Talk and signs pass:

| Item | Where | What settles it |
|---|---|---|
| That unshifted top-row digits are ignored at Talk's direction prompt. Static reading of the shared prompt; Space, Escape, a letter and a diagonal were executed. *(Issue #300 Q12.)* | `systems/conversation.md` Section 2 | Execute the prompt with each unshifted digit. |

Opened 2026-10-25 by the issue #300 Q28 ruins pass:

| Item | Where | What settles it |
|---|---|---|
| That the overworld `Enter ruins` arm is unreachable in ordinary play. This was inferred from the facts that only Blackthorn's interrogation sets a ruin flag, the ruined-shrine tile exists only by region-load rewrite, and the tile is impassable. Two things were not checked: impassability for each transport (carpet and the vessels), and whether a teleport or blink path can place the party on the cell. *(Issue #300 Q28.)* | `systems/commands.md` Section 5.5 | A trace of the movement passability test per transport for that tile, plus a census of every party-placement path (Blink, gates, moongates, scripted moves) against it. |

Opened 2026-10-25 by the issue #300 Q24, Q27 and #301 Q3 dungeon and impact-audio pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the dungeon-view initialisation's inactivating arm (type and tile zero, X and Y 255, class `0xFF`) runs on resume and on the return from the character screen, the two paths on which the published contract reuses the wandering-monster record instead of re-rolling. It is established for dungeon view entry with the arm selected, including straight after an A-Attack fight, just before the fresh roll. *(Issue #300 Q24, R609.)* | `systems/dungeon-mode.md` Section 4.1 | List every caller of the view initialisation with the argument each passes, and match them to resume, the character-screen return, level change, dungeon entry and the post-fight return. |
| Which town-mode path calls the overworld impact presentation (stage one). One call site in the town overlay was not examined. The sound cannot differ, because stage one is a fixed routine; only the trigger is unpublished. *(Issue #301 Q3.)* | `systems/overworld.md` Section 6.2.4 | Identify that town-overlay caller and the event it serves. |

Opened 2026-10-25 by the issue #300 Q31 and Q32 combat-hit and dungeon-footstep audio pass:

| Item | Where | What settles it |
|---|---|---|
| That a combat party hit plays no second, 160-update damage rumble. This rests on a census of direct calls from the combat overlays (COMBAT, COMSUBS) to the resident party-damage routine, the trap effect and the viewport-flash rumble helper, none of which they call; indirect routes into the party-damage helper were not enumerated. | `systems/combat.md` Section 11.1; `systems/audio.md` Sections 5.3 and 8.2 | An enumeration of indirect calls into the party-damage helper from combat, or execution of a full combat party hit through damage application with every speaker call logged. |
| That after a plain dungeon step only the idle command wait ticks the footstep tail. The post-action handler's redraw arms (room class, trap and event) were not all enumerated, so another redraw could intervene and shift the tail's timing (not its order). | `systems/audio.md` Section 7.4 | A static enumeration of every redraw arm of the dungeon post-action handler after a committed step. |

Opened 2026-10-25 by the issue #300 Q34 digit pass:

| Item | Where | What settles it |
|---|---|---|
| Whether dungeon digits are "a solo-member select that always reports no action". Town and overworld digits reach one shared active-player selector whose `Invalid!` refusal reports "acted"; the dungeon digit route may reach the same selector, and whether the dungeon handler keeps or overrides that status was not re-examined. The dungeon advances its clock at the loop head, so the status there decides only the post-action pass. *(Issue #300 Q34.)* | `systems/dungeon-mode.md` Section 4 inner-loop step 3; `systems/commands.md` Section 9 | A static trace of the dungeon digit route through to the status it returns, or a dungeon capture of `Invalid!` showing whether the post-action pass runs. |

Opened 2026-10-25 by the issue #300 Q35 combat-chrome pass:

| Item | Where | What settles it |
|---|---|---|
| What a party wipe-out does to the two ribbon gaps. The resurrection path was not traced; it probably reloads a scene, which would not change the frozen-gap answer, but that is not established. *(Issue #300 Q35.)* | `systems/moons.md` Section 3 | Trace the party-death path out of combat to its first scene entry and record which gap painters it reaches. |
| The overworld exit cases (strip repainted on exit only when the fight's last minute crossed an hour; banner stale after an in-fight drift) rest on executed routines, not on a capture. *(Issue #300 Q35.)* | `systems/moons.md` Section 3 | A capture of an overworld fight started shortly before the hour and kept running two or more round-wrap minutes past it, checking that the sky markers have not moved on return. |
| The label refresh after a dungeon room reached at the end of a pit chain was not traced to its caller. *(Issue #300 Q35.)* | `systems/moons.md` Section 3; `systems/dungeon-mode.md` Section 14.1 | Follow the pit-chain room entry through to the redraw that follows its fight. |
| The negative that nothing reachable in combat writes either ribbon gap covers near calls only; far and register-indirect transfers were not censused. *(Issue #300 Q35.)* | `systems/moons.md` Section 3; `systems/combat.md` Section 4 | Extend the gap-writer census to far and indirect transfers. |

Opened 2026-10-25 by the issue #302 Q1 and Q4 turn-cost pass:

| Item | Where | What settles it |
|---|---|---|
| Which transports can reach a town water cell in ordinary play (a carpet flown over town water, a skiff or frigate inside a town). The town A-Attack on-foot refusal was exercised only with the party placed on water by an edited save. *(Issue #302 Q4.)* | `systems/commands.md` Section 5.8; `systems/town-mode.md` A-Attack paragraph | A play trace that boards a carpet or skiff in a town with water and moves onto it, or a static check of the carpet and vessel movement predicates against the town water tiles. |
| That the town object walker and NPC schedule step run after an M-Mix. The clock and upkeep counter were measured; the walkers follow from the acted status and the published town epilogue but were not watched. *(Issue #302 Q1.)* | `systems/magic.md` Section 6 | A capture of an NPC taking one schedule step across a Mix. |
| The dungeon M-Mix status (deciding only the post-action pass) and the cost of Escape at the town A-Attack direction prompt rest on static reading; neither was executed. *(Issue #302 Q1, Q4.)* | `systems/magic.md` Section 6; `systems/town-mode.md` A-Attack paragraph | A dungeon Mix capture showing the post-action pass, and a town capture of Escape at the `Attack-` direction prompt with the clock read back. |

Opened 2026-10-25 by the issue #302 Q3 signs pass:

| Item | Where | What settles it |
|---|---|---|
| Whether any `SIGNS.DAT` record whose header lies inside a scene's window but whose text runs past the window's end (one shipped case: scene 0 reaching a scene-1 sign) sits at a real sign tile in the reaching scene. *(Issue #302 Q3.)* | `formats/signs-dat.md` Section 5 | Cross-check each such record's coordinate against the sign-tile positions of the reaching scene's map. |

Opened 2026-10-25 by the issue #302 Q6 Sleep Field pass:

| Item | Where | What settles it |
|---|---|---|
| Whether any effect can move a sleeping combatant off its cell, which would end the Sleep Field re-sleep loop. Not enumerated. *(Issue #302 Q6.)* | `systems/combat.md` Section 11 | Census every combat path that changes an actor's arena position and check whether any applies to an actor with bit `0x08` set. |
| That nothing reads the sleep narration code between Sleep Field contact and the next dispatch, so contact prints no `slept!`. Static, from a direct-operand scan of the resident image and all overlays; accesses through a register or pointer were not censused. *(Issue #302 Q6.)* | `systems/combat.md` Sections 11 and 12 | Extend the narration-code reader census to indirect accesses, or capture field contact (section 2). |

Opened 2026-10-26 by the issue #303 Q3 prompt world-step pass:

| Item | Where | What settles it |
|---|---|---|
| The complete list of key readers that bypass the shared wait and so never run the world step. Character creation's name reader is executed; the disk-swap and disk-error prompts, intro and menu waits, Look print-and-wait loop, a dungeon-view wait, the endgame's raw-key loops and the mode loops' key-repeat poll are from static reading, and the list is not claimed to be exhaustive. The scene-value writer census likewise excludes block copies and indirect writes. *(Issue #303 Q3.)* | `systems/input.md` Section 2 | A census of every direct caller of the raw keyboard check and blink-and-key routine outside the shared wait, and a trace of block copies that can reach the scene cell. |

Opened 2026-10-26 by the issue #303 Q6 boot-seed placement pass:

| Item | Where | What settles it |
|---|---|---|
| The generator state when the automatic Return-to-View preview starts, presumed to be the shipped zero value. No range draw was found in the intro or title code ahead of it, but not every resident path reachable during the title was proved. Presentation only: the boot seed overwrites the state after the preview. The seed-after-preview order itself rests on static reading; nothing was executed. *(Issue #303 Q6.)* | `systems/prng.md` Section 3 | A census of every generator advance reachable before the automatic preview, or an executed unskipped start with the state word observed at the preview's first tick and at the seed. |

Opened 2026-10-26 by the issue #304 Q1 fall-chain pass:

| Item | Where | What settles it |
|---|---|---|
| Two fall-chain points that rest on static reading: the dungeon view initialiser running before the chain's setup on the room-landing path only, and the contact fight (when the turn's monster step reports contact before the fall) ending with its own view initialiser and fresh setup on the departure level, giving that turn two setups. The fight and the initialiser were stubbed in the executed runs. *(Issue #304 Q1.)* | `systems/dungeon-mode.md` Sections 4.1 and 8 | Execute a fall chain with a room landing and one with monster contact on the departure turn, with the initialiser and the contact fight left live and the setup calls logged. |
| Whether a room fight entered by stepping onto a room cell, not by falling, is followed by a fresh active-monster setup. Static reading of the turn step's ordinary room path found none; other routes were not checked, so the 4.1 "Return from a dungeon fight or encounter" row may be too broad for room fights. *(Issue #304 Q1.)* | `systems/dungeon-mode.md` Section 4.1 | Trace every path from dungeon room entry back to the turn loop for a setup call, or execute an ordinary room entry and log setup calls. |

Opened 2026-10-26 by the issue #304 Q2 and Q3 conversation-draw pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the Falsehood theft redraws the gold/stats panel on every path. Both documents say the pass "then redraws the gold/stats panel" unconditionally, but the cleanup's own redraw was seen only on the gold path; whether the key/gem/torch decrement or the band scans redraw the panel by some other route was not checked, so the unconditional wording may be too broad. *(Issue #304 Q3.)* | `systems/conversation.md` Section 10; `systems/quest-flags.md` Section 5 | Trace the item-decrement and band-scan paths for a panel redraw, or execute a theft of a torch and of an equipment item with panel draws logged. |

Opened 2026-10-26 by the issue #304 Q4 and Q5 wait-caller and preview-draw pass:

| Item | Where | What settles it |
|---|---|---|
| The endgame key-wait census (ten shared-wait sites, six raw-key sites) covered the endgame code and the resident routines it calls, but not the targets of its overlay far-stub calls, so a further key read there is not excluded. *(Issue #304 Q4.)* | `systems/input.md` Section 2; `systems/timing.md` Section 8.2; `systems/endgame.md` Section 8.3 | Trace every far-stub target the endgame calls for a key read. |
| Two Return-to-View points that rest on static reading: that the preview's entry path (data load, screen snapshot, setup before the first tick) takes no gameplay draw, and that the `R` command and the menu idle timeout enter the same preview routine. The executed runs started at the preview's in-run state. *(Issue #304 Q5.)* | `systems/prng.md` Section 3 | Execute the preview from each of its two menu entry points with generator calls logged from entry. |
| Two Q7 points about keys typed during the Blackthorn capture narration. The first is that the greeting acknowledgement uses the **oldest** queued key. The second is that this read is the **only** point where the queue is emptied before the greeting. Both rest on a static census of key calls that did not follow the display driver's far calls or the indirect calls. The Buffer-On control run cannot exclude a flush inside the narration that is gated on the same type-ahead setting. That exactly one key survives under Buffer Off is executed. *(Added 2026-10-26, issue #304 Q7.)* | `systems/blackthorn.md` Section 3 ("Keys typed during the capture narration"); `systems/input.md` Section 6 | Extend the census through the display driver and the indirect call targets. Alternatively, run Buffer-Off captures that type a single key at different points of the narration and check that the greeting is still acknowledged each time. |
| Whether the Blackthorn throne-approach envelope `(5, 100, 13000, 1, 2800)` is skipped by its caller when sound is off, or plays the generator's muted arm. Only the sound-on run was examined. *(Added 2026-10-26, issue #304 Q6.)* | `systems/audio.md` Sections 8.6 and 10.3; `systems/blackthorn.md` Section 3 (timeline step 16) | Read the caller for a sound-setting test, or time the hold in a sound-off capture. |

Opened 2026-10-27 by the issue #305 Q1 dungeon contact-launch pass:

| Item | Where | What settles it |
|---|---|---|
| Whether the extra room-layout stamp the A-Attack launch runs between the view teardown and the room painter has any observable effect. It takes no random draw; nothing else about it was examined. *(Issue #305 Q1, R632.)* | `systems/dungeon-mode.md` Section 14.1, "Per-caller order" | A static reading of the stamp against the state the painter and framer read next. |

Opened 2026-10-27 by the issue #305 Q4 contact-rule pass:

| Item | Where | What settles it |
|---|---|---|
| `systems/movement.md` Sections 2, 7 (Combat bullet) and 9 still say a combat move into a hostile occupied cell becomes an attack. `systems/combat.md` Sections 8.1 and 11 and `systems/audio.md` Section 7.4 say the arena step is refused with `Blocked!` and there is no bump attack. Outside issue #305 Q4's scope, so this pass changed neither side. *(Issue #305 Q4.)* | `systems/movement.md` Sections 2, 7 and 9; `systems/combat.md` Sections 8.1 and 11 | A pass that reconciles the movement text with the combat contract, with a `RETRACTIONS.md` row for whichever side is withdrawn. |

Opened 2026-10-27 by the issue #307 Q2 mountain-reject pass:

| Item | Where | What settles it |
|---|---|---|
| What share of Underworld spawn candidates the mountain and high-peak reject removes. Only the map-cell fraction is published (about seven in ten Underworld cells); candidates are drawn from the scroll window near the party, not uniformly over the map, so the candidate share depends on where the party is and was not measured. *(Issue #307 Q2, R644.)* | `systems/encounters.md` Section 4 | Log the step-3 candidate tiles of the original spawner over Underworld sessions at several party positions. |
| That the tile the encounter picker classifies is the plain map tile at the candidate cell on both planes, with no per-plane remapping before the test. This rests on static reading of the map accessor only. *(Issue #307 Q2.)* | `systems/encounters.md` Section 4 | Execute the spawner's map read on an Underworld cell and compare the passed tile with the Underworld map file. |

Opened 2026-10-28 by the issue #308 Q2 room-demotion pass:

| Item | Where | What settles it |
|---|---|---|
| Whether fleeing a dungeon room returns the room-combat loss result, in which case the room helper skips both the in-place `0xF?` to `0xA?` patch and the room-clear bit, so a fled room stays armed. Only the party-side-emptied-while-foes-remain case is established as the loss result. *(Issue #308 Q2.)* | `systems/dungeon-mode.md` Section 5 ("Room trigger") | Flee a dungeon room fight in the original and read the trigger cell and the room-clear bit afterwards, or trace the combat exit paths' return value. |
| That the tail of the K-Klimb path, after the level change is committed (status repaint, monster re-seed, view repaint), never reaches the demotion pass rests on the whole-game static call census; the executed probe stopped during the status repaint. *(Issue #308 Q2, R647.)* | `systems/dungeon-mode.md` Section 5 | Execute K-Klimb through to the next command prompt with the demotion entry watched. |

Opened 2026-10-29 by the issue #310 Q2 combat world-tick pass:

| Item | Where | What settles it |
|---|---|---|
| Whether an in-arena Klimb that accepts an Up/Down departure, and so leaves the arena, still runs the command handler's tail world tick. Not executed and not settled statically. *(Issue #310 Q2.)* | `systems/combat.md` Section 11 ("Which combat dispatches run a world tick") | Trace the accepted departure through to the handler's exit, or execute it with world ticks counted. |

Opened 2026-10-29 by the issue #311 Q6 Blackthorn name pass:

| Item | Where | What settles it |
|---|---|---|
| That no party member can die during the Blackthorn audience before the execution, so the two-member guard still holds when the victim is chosen, is inference: it assumes the audience's two-minute advances run the clock advance alone and not the poison and starvation upkeep pass. *(Issue #311 Q6.)* | `systems/blackthorn.md` Section 5 ("Execution text") | Trace the audience's time advances for any call into the upkeep pass, or run the audience with a poisoned, low-HP companion. |

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
