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

Last reconciled: 2026-09-12. The 2026-09-05 reconciliation had closed every
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
pass opened four more trace items (section 3). What else
remains needs an owner decision (section 1) or a change of scope (section 4).

## 1. Owner decisions

| Item | Where | What settles it |
|---|---|---|
| Whether to rewrite shared history to purge the removed original-game screenshot, and whether to include historical provenance/author metadata cleanup. | Issue #249; `NEXT-STEPS.md` | Explicit owner scope decision and approval before rewriting and force-pushing shared history. Current-tree cleanup is already published; earlier commits still contain the image. |

The shipped-text policy (how much of the game's own text this
specification reproduces) was decided on 2026-09-04: the four items outside
the interface-string justification stay as published, for the functional
reasons recorded in `EXTRACTION.md`, "Shipped-Text Policy".

## 2. Needs a live capture

| Item | Where | Notes |
|---|---|---|
| Issue #259's reported run: which picker contents produced its zero/one/two-row completion gaps. The mechanism is now closed - the picker repaints rather than scrolls, one re-render costs one strip scroll exactly when the entry beginning on the panel's last list row wraps, and the strip copy destroys the message window's top row with nothing restoring it (`systems/inventory.md` Sections 4.4/4.5/7.1, `systems/display-driver-abi.md` Section 9.5). What is left is the specific run. | `systems/inventory.md` Section 7.1 | For each reported beat, the **complete picker panel with quantities** and the **number of navigation presses**, or a standalone original-game save with exact inputs. Both are needed: press counts alone cannot produce the reported gap pattern, because the highlight parks on the fourth visible row and the first four passes of a command all show the same page and cost the same. *Narrowed 2026-09-12 (issue #259): the earlier attribution of those beats to a stock special-items inventory is withdrawn on that ground; measured cumulative-gap tables for seven inventories are published in Section 7.1 for comparison.* |
| The conversation renderer's column-dependent flush rules - a leading space dropped at column zero and a row break swallowed at column fifteen or beyond - were read but only partly exercised, because the emulation harness has no real screen state. The entry sequence, the quote-suppression rule and the column-eighteen word break are established. *Extended 2026-09-12 (issue #266): the ASK-WHO prompt and acknowledgement **row splits** published in Section 7.6 are that word-break rule applied to an executed character sequence, not a measurement of the renderer. The character sequence itself - every feed, quote and stored word, and which arm prints which - is executed and settled; only where the rows break is modelled.* | `systems/conversation.md` Sections 6, 7.6 and 9 | A capture with real cursor state through an NPC entry, a long wrapped response, and an ASK-WHO prompt answered both ways. |
| Issue #231 reports a silent arena body-armour refusal, but the traced unresolved-combat gate prints the explicit heated-battle refusal. | `systems/inventory.md` Section 5.2 | Obtain the selected item, equipped-slot state before/after and whether a foe was present at arena initialization. An initially empty arena already lifts the combat-specific prohibition; ordinary slot rules still apply. |
| Issue #231 reports no invisibility completion; original-call traces and isolated execution emit `Success!`. | `systems/magic.md` Section 8 | Obtain the original save, canonical asset identity, exact spell inputs and frames from dispatch through the next input wait. Isolated probes establish emission, not full-game screen lifetime. |
| Rescue burst reported as 8.491 seconds in issue #220, shorter than the static six-row timing model; reported thunder flashes absent. | `systems/audio.md` Section 8.6.2; `systems/blackthorn.md` Section 7.1 | Obtain a complete recording through thunder and the castle handoff, its exact file length, row onsets/offsets and CPU/core/cycle settings. Existing samples do not establish completion of the final two rows. The trace confirms all six counts and places the flashes after two Guardian reveals and fourteen BIOS ticks. |
| Whether the reported 0.859/0.860-second EGA major flash transfers across emulator settings or non-EGA drivers. | `systems/audio.md` Section 8.4 | Repeat the issue #219 Word-of-Power capture with recorded CPU/core/cycle settings and each selected driver. All callers share the same 1,856-band workload; equal raster execution time across drivers is not established. |
| Issue #210 reports a first dungeon command echo on screen row 14 and two additional rows of later scrolling; the normal Journey path explicitly sets the message cursor to screen row 23. | `systems/save-load.md` Section 4; `systems/dungeon-mode.md` Section 8.1 | Obtain a stock save, exact command sequence and banner, and frames at first prompt, immediately after the first command and after room entry. The pit/fall/splat/room strings add no unlisted standalone line feeds; combat has separate banner and input separators. |
| Minoc/palace reserved-guard bare refusal reported in issue #216, despite the shared explicit-T route and a prior successful Minoc report. | `systems/blackthorn.md` Section 7a; `systems/conversation.md` Section 2 | A stock-written save immediately before the failing Talk, exact position/floor/time/direction and matched asset version; inspect the target's live dialogue word, reached waypoint and linked active-object ownership. Canonical Minoc slot 14 authors `[0, 4, 0]`, unlike the reported all-7 engine state. |
| Whether the "nothing further is printed" negatives of the Klimb and dungeon level-change contracts hold for the *whole screen* rather than for the message window. They were established with the repaint endpoints excluded; static reachability shows the town floor reload, the resident view routine and the dungeon level-entry routine all reach the shared text primitives somewhere in their call graphs, for roster, wind-banner and dungeon-panel content, and the outdoor step-commit chain leaves two cross-overlay thunks unfollowed. | `systems/doors-and-z-transitions.md` Section 9; `systems/dungeon-mode.md` Section 13.1; `systems/commands.md` Section 5.8 | Either a raster capture of an applied Klimb and an applied dungeon level change, or execution through those repaint chains rather than around them. |
| Wall-clock durations of every PC-speaker effect. The loop structures are exact; the per-iteration cycle model that converts them to seconds is a static estimate with a stated error band. *Narrowed 2026-09-05: two blocking tones (the blocked step and the combat refusal pair) and the calibrated unit itself were measured under DOSBox and sit inside the published bands (`systems/audio.md` 7.4, 8.8, 10.1; `systems/timing.md` 7.6, 8.7). DOSBox is not cycle-accurate, so the period-hardware figure stays open.* | `systems/audio.md` Sections 5.4, 10; `systems/timing.md` | One cycle-accurate emulator run with an audio capture settles all of them at once. The two figures most worth checking first are the Stonegate trapdoor sweep (about 26.5 s derived) and the long Blackthorn envelope. |
| The audible waveform and timbre of the envelope generator. | `systems/audio.md` Section 5.4 | Same run as above. |
| Whether the mode loop or an interrupt handler drains the keyboard buffer after the whirlpool sequence. Established only by absence inside the two traced paths. | `systems/audio.md` Section 8.9 | Sail into a whirlpool once. |
| The per-tone install cost used by the calibrated-wait model (17.4 inner units derived, against a fitted 12). | `systems/timing.md` Section 7.6, item 9 | A measured tone on the reference machine class. |
| The per-step wall clock of the publisher flourish, published as a calibration-derived target rather than a measurement. | `systems/timing.md`; `systems/intro.md` | Frame-timed capture of the intro. |
| The intro title ink reported as "pale yellow" by observation, where both the code path and the shipped palette say white. | `systems/intro.md` | Capture on period hardware or a palette-faithful emulator. |
| The world-tick rate, and therefore every wall-clock statement derived from per-tick cadence: the autonomous wind-drift interval and the decay time of the twelve-hour save byte. | `systems/weather.md` Section 2.1; `formats/saved-gam.md` Section 5 | Time the idle loop once. |
| Whether the active-object animator runs during dungeon and combat *play* (it runs on dungeon entry). Matters because the dungeon overlay reuses two table records as scratch. | `systems/active-objects.md` Section 13; `systems/npc-schedules.md` Section 12 | Observe frame changes in a dungeon and an arena. |
| What the compositor's neighbouring-row probe reads at arena rows 0 and 10, where it reaches outside the arena record. Published as residue with a recommended engine behaviour of *no match*. | `systems/visibility.md` Section 8.5 | Read the byte in a running game; no shipped arena can act on it. |
| The visual appearance of the ship broadside burst and the dragon-breath spark cloud along a projectile line. | `systems/overworld.md` Section 6.2.6 | Screen capture during either attack. |
| That Lord British has no throne-room conversation. Every static search supports it (no roster entry, no dialogue strings); a live check would close it definitively. | `systems/conversation.md`; `catalogs/npc-roster.md` | Talk to him in the throne room. |
| Tile-id partition boundaries for water, mountain, lava and door classes against runtime behaviour, if independent re-authored data is ever the goal. | `catalogs/tile-catalog.md` Section 16, item 8 | Optional; movement contracts already own passability. |
| What the display driver paints from a wrapped picker row. The character stream is now fully measured - which entries wrap, at which quantity widths, and the two resulting shapes (the word moved whole onto the next display line over the left rule, or a label ending on the window's last writable cell, over the right rule and into screen column 39) - but no raster was captured, and the glyph blitter and several resident graphics helpers remain returns-only endpoints whose call arguments were censused rather than executed. | `systems/inventory.md` Section 4.5; `systems/text-output.md` Section 6 | A raster capture of a `U`-Use picker holding a counted shard row, reconciled with the published glyph contract rather than asserted from the character stream. *Narrowed 2026-09-12 (issue #259): 1,562 single-row renders settle which rows wrap and how many entries a page then holds; only the pixels are open.* |
| The value of the active-object solidity marker for arena monsters, which decides whether an actor's own cell refuses its own zero-displacement step and therefore how the surrounded predicate reads. It was taken from the arena seeder's own writes rather than from a live game session. | `systems/combat.md` Section 9.1 | A capture of a live arena with monsters placed, reading the marker off the seeded records. |
| What the beyond-raster region of display memory holds after the EGA mode set. It decides whether the message window's vacated bottom row comes up blank on a session's second and later strip scrolls: the fast path does not blank the gutter row it leaves behind, and the next scroll lifts that row into the window. | `systems/display-driver-abi.md` Section 9.5; `systems/text-output.md` Sections 10.1 and 10.5 | A real display or a full emulator boot; a bare harness cannot supply it. The written range is already established to lie above the visible page and below the driver's back buffer, so only the contents are open, not the safety. |
| Whether anything repaints the displaced message band at the pixel level. Bounded, not closed: no character emitted while a non-message window was selected landed in the message rectangle, no driver dispatch after the picker returns names an overlapping rectangle, and every censused argument to the returns-only glyph blitter and resident graphics helpers lies above the message window's first scanline. Their bodies were not executed. | `systems/display-driver-abi.md` Section 9.5; `systems/inventory.md` Section 7.1 | A raster capture of a `U`-Use command whose picker page overflows, taken at the picker wait and after acceptance. |

Closed 2026-09-05 by live observation under DOSBox: the three suspected NPC pursuit-stepper defects. None has an observable effect; the stepper's real contract (gate below four, east/north/west/south first fit, no move when nothing improves, event on a later invocation after an NPC's own move creates adjacency) is now published in `systems/npc-schedules.md` Section 9.

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
