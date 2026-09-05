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

Last reconciled: 2026-09-04. The `trace` items were **not** re-traced in the
pass that built this index; the shipped binary set was not available to it.

## 1. Owner decisions

| Item | Where | What would settle it |
|---|---|---|
| **How much shipped text this specification reproduces.** Interface strings (prompts, refusals, labels, names) are published throughout; four items sit outside that justification: the Avatarhood certificate prose, two inline intro doorway narration lines, the eight Words of Power, and the common-word token vocabulary. This repository is now public, so the question is live. | `EXTRACTION.md`, "Shipped-Text Policy" | `owner`: keep, replace with structural descriptions plus placeholders, or describe layout and read the strings from the player's own copy at run time. |

## 2. Needs a live capture

| Item | Where | Notes |
|---|---|---|
| Wall-clock durations of every PC-speaker effect. The loop structures are exact; the per-iteration cycle model that converts them to seconds is a static estimate with a stated error band. | `systems/audio.md` Sections 5.4, 10; `systems/timing.md` | One cycle-accurate emulator run with an audio capture settles all of them at once. The two figures most worth checking first are the Stonegate trapdoor sweep (about 26.5 s derived) and the long Blackthorn envelope. |
| The audible waveform and timbre of the envelope generator. | `systems/audio.md` Section 5.4 | Same run as above. |
| Whether the mode loop or an interrupt handler drains the keyboard buffer after the whirlpool sequence. Established only by absence inside the two traced paths. | `systems/audio.md` Section 8.9 | Sail into a whirlpool once. |
| The per-tone install cost used by the calibrated-wait model (17.4 inner units derived, against a fitted 12). | `systems/timing.md` Section 7.6, item 9 | A measured tone on the reference machine class. |
| The per-step wall clock of the publisher flourish, published as a calibration-derived target rather than a measurement. | `systems/timing.md`; `systems/intro.md` | Frame-timed capture of the intro. |
| The intro title ink reported as "pale yellow" by observation, where both the code path and the shipped palette say white. | `systems/intro.md` | Capture on period hardware or a palette-faithful emulator. |
| The world-tick rate, and therefore every wall-clock statement derived from per-tick cadence: the autonomous wind-drift interval and the decay time of the twelve-hour save byte. | `systems/weather.md` Section 2.1; `formats/saved-gam.md` Section 5 | Time the idle loop once. |
| Whether the active-object animator runs during dungeon and combat *play* (it runs on dungeon entry). Matters because the dungeon overlay reuses two table records as scratch. | `systems/active-objects.md` Section 13; `systems/npc-schedules.md` Section 12 | Observe frame changes in a dungeon and an arena. |
| What the compositor's neighbouring-row probe reads at arena rows 0 and 10, where it reaches outside the arena record. Published as residue with a recommended engine behaviour of *no match*. | `systems/visibility.md` Section 8.5 | Read the byte in a running game; no shipped arena can act on it. |
| The visual appearance of the ship broadside burst and the dragon-breath spark cloud along a projectile line. | `systems/overworld.md` Section 6.2.6 | Screen capture during either attack. |
| Three suspected defects in the shipped NPC pursuit stepper - a lateral-step selection that spends the turn without moving, a harmless out-of-bounds score read, and a swapped-axis clamp check. Read off the program statically, **deliberately unpublished** as behaviour until reproduced live, because a port should not inherit a bug the original may not exhibit. | `systems/npc-schedules.md` Sections 5 and 9 (contract as published) | Reproduce in an emulator with a pursuing NPC blocked on its best axis. |
| That Lord British has no throne-room conversation. Every static search supports it (no roster entry, no dialogue strings); a live check would close it definitively. | `systems/conversation.md`; `catalogs/npc-roster.md` | Talk to him in the throne room. |
| Tile-id partition boundaries for water, mountain, lava and door classes against runtime behaviour, if independent re-authored data is ever the goal. | `catalogs/tile-catalog.md` Section 16, item 8 | Optional; movement contracts already own passability. |

## 3. Needs a further static trace

| Item | Where | Notes |
|---|---|---|
| **Re-catalogue the nominal index ranges of the tile catalogue against the shipped description table.** Both halves carry provisional range names that are wrong in places (the "NPC" band of the terrain half is scenery; two "monster" bands of the actor half are person sprites). Individually confirmed ids take precedence today; a full per-id table is the highest-value item in this file. | `catalogs/tile-catalog.md` Sections 2, 3, 3.1, 16 (item 0); `formats/look2-dat.md` | Decode the whole description table and the atlas once; publish a per-id class table and retire the nominal ranges. |
| Whether the caller's light value also reaches the visibility producer's carve as the squared-distance threshold, or only selects the branch. | `systems/visibility.md` Section 3 (the note under the light-value table) | Trace the producer's threshold source. |
| Whether a controlled actor's fixed attack-flavour id reaches the rating selector as the neutral value, so that its to-hit also collapses to 15. | `systems/combat.md` Section 11 | Trace the flavour id through the rating selector. |
| Whether the controlled/charmed bit has any reachable writer at all; the encoding-level scan found none. | `systems/combat.md` Sections 6.1 and 11 | Widen the writer census to pointer-through-memory writes. |
| Whether a readied item is consumed on shatter; two analyses conflict. | `systems/combat.md` Section 12 | Trace the shatter arm's inventory write. |
| For a controlled monster actor: what the roster picker accepts, what the cast/effect arm does for a non-melee class (reachability is published, contents are not), and the arena-exit helper's own rules beyond the party-side gate. | `systems/combat.md` Sections 8, 8.1, 16.1 | Trace the three arms with a monster-side slot. |
| The dragged-under turn arm (the `ARGH!` line and the regurgitation line) appears in neither the command table nor the special-attack census; and which status bit a landed Corpser drag writes - asleep or dragged-under - which gives the victim different next turns. | `systems/combat.md` Sections 8 and 11.1 | Trace the Corpser hit arm and the dragged victim's next-turn path. |
| Whether any shipped location map places a down-stair, trapdoor or grate that would drive the floor byte below the location's lowest owned page (the handlers apply no bound). | `systems/doors-and-z-transitions.md`; `systems/town-mode.md` | Walk every location's floor pages for the three tiles. |
| Whether the six inn bed cells and the cells east of them are walkable tiles on the shipped pages. | `systems/shops.md` Section 8.4 | Read the six cells from the location maps. |
| The meaning of the guard on the arrest handler's already-in-the-castle arm. | `systems/blackthorn.md`; `systems/town-mode.md` | Trace the guard's operand. |
| The "combat scenes" gloss on the scene-byte threshold shared by the visibility post-pass and the world tick. | `systems/visibility.md`; `systems/main-loop.md` | Enumerate every scene value the threshold admits. |
| The bodies of the two consumers of the resident-Shadowlord selector behind the Falsehood price and the conversation gates. | `systems/shops.md`; `systems/conversation.md` | Trace both consumers. |
| The body of the NPC runtime-state initialiser, and the waypoint-index arithmetic for any scene whose waypoints differ by hour. | `systems/npc-schedules.md` Sections 4 and 13 | Trace the initialiser and one hour-varying schedule. |
| The walkability of the four Iolo's Hut roster cells, and the animation-script bytes for the whirlpool marker class (reachability traced, script not). | `systems/active-objects.md`; `catalogs/npc-roster.md` | Read the cells and the script. |
| Whether anything rewrites the scratch behind the arena record while a fight is live; two overlay paths were not traced through the overlay manager. | `systems/visibility.md` Section 8.5 | Trace the two paths. |
| The starting points and ceilings of the strength and intelligence questionnaire tallies; only dexterity's floor was re-derived. | `systems/chargen.md` Sections 6 and 7 | Trace the two tallies' seeds. |
| How the Shadowlord location readout lays out its eight rows on screen (town list, coarse map, or other). | `catalogs/quest-graph.md`, Section "Open" bullets | Trace the readout renderer's row placement. |
| Whether any later gameplay path adds underworld object records beyond the five seeded ones. | `formats/ool.md` Section 11 | Census of underworld-plane record writers. |
| The 39-byte record stride and eight-record count of the imported Ultima IV party file, carried on the authority of the published Ultima IV format. | `systems/u4-transfer.md` Section 5.4 | Trace the importer past the first record. |
| Attribution of the two three-unit blips in the Return-to-View strip census. | `systems/audio.md` Sections 7.4 and 8.6 | Trace the strip-3 sound calls. |
| The exact labels of the resident display, sound and wait helpers the endgame sequence uses (order and blocking boundaries are published; helper taxonomy is inferred). | `systems/endgame.md` Section 12 | Trace the helper identities. |

## 4. Deferred by scope

| Item | Where | Notes |
|---|---|---|
| Exact CGA, Hercules and Tandy rendering, timing and audio-wait parity. EGA is the sole pixel-exact target; the other three drivers are labelled modern approximations. | `EXTRACTION.md`, "Known V1 Deferrals"; `systems/display-driver-mode.md` Section 6; `systems/timing.md` Section 7.6, item 8 | Revisit only if historical hardware parity becomes a target. |
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
