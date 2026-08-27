# Commands

## 1. Overview

Ultima V has two command-dispatch layers during normal play. The input system
turns keyboard events into one translated byte. The active mode loop then
handles mode-local controls first: movement directions, digits where the mode
uses them, sound toggles, explicit quit prompts, and any other control bytes
below the printable range. Printable command letters that survive this
pre-routing go to the resident world-command dispatcher.

This spec covers that resident dispatcher: the A-Z and Space command surface
shared by the overworld, town-family locations, and dungeons. Combat has its own
dispatcher and command table inside the combat overlay; see `combat.md`.

The dispatcher is not a user-interface loop. It does not poll the keyboard. It
receives one already-translated byte from the active mode loop, prints the
command's verb prefix, chooses the correct handler from the current scene byte,
and returns a status word to the caller.

## 2. Inputs And Scene Routing

The dispatcher expects one byte from the input pipeline:

- `Space`, uppercase `A..Z`, and a small number of printable punctuation bytes
  are legal dispatcher inputs.
- Lowercase letters should already have been folded to uppercase by the input
  system.
- Direction codes never reach this dispatcher. Every mode loop consumes the four
  cardinal direction codes in its own pre-dispatch stage, so the rule is
  unconditional rather than a normal-case convention.
- Exactly one non-letter code is accepted: the typeahead-buffer toggle described
  in Section 9. It is a typed Control character — Control held with the second
  letter of the alphabet — not a translated cursor or numpad code.
- Everything else is rejected with the stock refusal and reported as "no
  action": every other control character, the four diagonal codes produced by
  the corner keys, and the ten function-key codes. No gameplay dispatcher in the
  game accepts a diagonal *step*; the only consumer of diagonal input is the
  combat targeting cursor (`combat.md`), and the corner keys otherwise act as
  paging keys inside the full-screen stats/inventory and shop lists.

Scene routing uses the resident scene byte:

| Scene byte range | Dispatcher meaning |
|---:|---|
| `0` | Overworld branch. |
| `1..32` | Town/dwelling/castle/keep branch. |
| `33..127` | Dungeon branch when the dungeon mode loop forwards a letter. |
| `0xFF` | Combat-class marker; not a normal caller of this dispatcher. |

Mode loops may intercept a key before it reaches this dispatcher. For example,
dungeon mode handles its own explicit "Exit to DOS?" prompt before forwarding
ordinary letters, and overworld mode has a control-code quit prompt in its
pre-dispatch table. Those paths are separate from the resident `Q` save-game
letter described below.

## 3. Return Contract

The returned status is a loop-control hint, not a gameplay result. It is a
four-member enum, and there is no global "turn consumed" flag anywhere in the
engine: turn cost travels entirely in this status word.

| Status | Meaning | Producers |
|---:|---|---|
| `1` | Acted. The default; the mode loop runs its per-turn epilogue. | The dispatcher's initial value, kept by every letter that does not forward or refuse. |
| `0` | No action. The loop skips its epilogue, so no world time passes. | Unknown input, the two stock-refusal letters `D` and `W`, the save route `Q`, the typeahead toggle, dungeon `P`, and any forwarded handler that refused. |
| `2` | Request arrest cleanup after a failed Blackthorn guard demand. | One producer only: `T` in a town-family scene when the reserved guard-demand conversation reports refusal or failure. Ordinary NPC conversations, shops, canned replies, and successful payment/password outcomes do not produce this status. |
| `3` | Re-prompt immediately, without advancing the world. | One producer only: the town digit handler while the party stands at the harpsichord tile, so a player can key in a tune without burning turns. |

Only the town loop reads all four values. The other loops collapse the status to
a boolean:

- **Overworld.** Tests only "is it zero". Zero skips the whole per-turn
  epilogue; every non-zero value is treated identically.
- **Dungeon.** Tests only "is it non-zero", which selects the dungeon's
  post-action pass. Note that the dungeon loop advances its own clock at the
  head of the iteration, before the command is even parsed, so no dungeon
  command is distinguished by this status for timekeeping purposes.
- **Town.** `3` jumps straight back to the input parser with no turn and no
  epilogue; `0` skips the epilogue; `1` runs the epilogue *including* the
  NPC schedule step; `2` runs the common time/underfoot epilogue but skips the
  NPC schedule step and fires town post-action cleanup with the arrest
  discriminator. The clock still advances by one minute. In the shipped
  command set no value above `3` is a designed producer.
- **Combat.** Never calls this dispatcher at all; the combat parser keeps its
  own re-prompt flag (`combat.md`).

Most letters discard whatever their handler returned and report the default
"acted". Exactly six routes forward the handler's own value: `A` Attack,
`B` Board, `C` Cast, overworld `E` Enter, town and dungeon `K` Klimb, and
`Y` Yell. Each forwarded value is itself only "acted" or "no action":

| Forwarded route | Value on each path |
|---|---|
| `A` overworld | Always "no action", including the successful attack that enters combat. |
| `A` town | "Acted", except the on-foot refusal, which is "no action". The nothing-to-attack message still counts as acted. |
| `A` dungeon | Always "no action". |
| `B` Board | "Acted" on every path — all four mounts and both refusals — except the final unknown-target fallthrough, which is "no action". |
| `C` Cast | "Acted", except one sub-handler branch that reports "no action". |
| `E` overworld Enter | "Acted" by default, "no action" after its refusal, otherwise whatever the location-entry path returned. |
| `K` town | "No action" by default, so both refusals cost nothing; "acted" for both ladder directions, for the no-actor early-out, and for a successful step. |
| `K` dungeon | "Acted" when a climb, a pit fall, or a cancel is applied; "no action" on both "nothing to klimb here" refusals. Climbing where there is nothing to climb therefore costs the party nothing, and the two refusals are distinct: one for a cell that holds a climbable feature the party lacks the gear for, one for a cell with no feature at all. |
| `Y` Yell | "Acted" for the word-of-power branch and its refusal; forwarded for the town Shadowlord branch. Three paths — hoisting sail, furling sail, and an empty yell — report an *undefined* status in the original: those paths never set a status of their own, so the caller observes whatever value the shared string printer most recently produced. |

The undefined Yell paths are an original-game defect, not designed status codes. An
implementation must not attempt to reproduce them; treat all three as "acted".
Because the sail shortcut accepts every scene below `0x80`, defensive ship
state can expose a sail path to the town loop as well as to the overworld and
dungeon loops. The town loop's numeric distinctions must not turn the leaked
text-renderer value into cursor-dependent gameplay.

Beyond those six routes, a modern implementation should preserve each command's
observable turn cost rather than depend on numeric equality everywhere. Mode
specs document the visible turn-cost rules for their command families.

## 4. Command Table

The table below is the dispatcher-level contract. Individual handler specs own
the detailed prompts, item consumption, stat writes, tile rewrites, and combat
handoffs.

| Input | Dispatcher route | Scene-specific contract |
|---|---|---|
| `Space` | Pass / wait inline path. | Prints the pass feedback and consumes a pass action unless a mode/vehicle-specific refusal applies. |
| `A` | Attack. | Routes to overworld, town, or dungeon attack handlers by scene. Combat attack is handled by the combat dispatcher instead. |
| `B` | Board. | Routes to the vehicle-boarding handler; succeeds only when the local vehicle/object context allows boarding. See `vehicles.md`. |
| `C` | Cast. | Routes to the spell-casting overlay. Spell prerequisites, parser rules, charge use, mana use, and scene masks live in `magic.md`. |
| `D` | Default refusal. | No resident world-command handler is currently confirmed; it falls through to the stock "What?" response when it reaches this dispatcher. |
| `E` | Enter. | Overworld routes to the location/dungeon entry helper. Non-overworld scenes use the resident refusal prompt path. |
| `F` | Fire. | Routes to the fire/cannon handler family. Overworld ship broadsides use a sub-handler; dungeon mode refuses. Door-destruction messages belong to this family, not to Open or Jimmy. See `vehicles.md`. |
| `G` | Get. | Routes to the Search/Jimmy/Open/Get overlay's Get handler. Dungeon mode skips the surface/town Get prefix and falls into the underfoot chest path. |
| `H` | Hole up / rest. | Overworld and dungeon use the rest-with-watch path. Town mode uses the inn/bed-hours path and refuses off bed tiles. The shared rest handler owns the hours prompt, sleep cleanup, HP recovery, rest-interruption checks, and the rare outdoor Lord British camp event; see `rest-and-camp.md`. |
| `I` | Ignite. | Routes to the torch-lighting handler. It consumes one torch if available and then sets or extends the torch duration as described in `lighting.md`. |
| `J` | Jimmy. | Routes to the lockpick handler for doors, restraint tiles, and locked containers. |
| `K` | Klimb. | Mode-aware: overworld, town-family locations, and dungeons each have their own climb/Z-transition handler; the gear gate, on-foot check, ladder cases, and dungeon level rules are specified in `doors-and-z-transitions.md`. |
| `L` | Look. | Dungeon scenes route to DNGLOOK. Overworld and town-family scenes route to LOOKOBJ and `LOOK2.DAT`; see `view.md`. |
| `M` | Mix / shrine-command family. | Ordinary field use routes to CMDS reagent mixing. Shrine-family special tiles route through CAST2's shrine/urn entry handler, which then dispatches internally to virtue meditation or Codex urn reading. |
| `N` | New order. | Routes to the party-order swap handler described in Section 6. |
| `O` | Open. | Routes to the Open handler for doors, chests, and dungeon underfoot cases. |
| `P` | Push. | Refuses in dungeons; otherwise routes to the push/movable-tile handler described in Section 8. |
| `Q` | Save game. | Routes to the save-game handler, which prompts whether to save. On `N`, it returns without writing. On `Y`, it writes the save files, acknowledges completion, and returns to the caller. This letter is not the DOS-terminate path by itself. Combat `Q` is refused outright by the combat parser: it neither saves nor ends the fight, as specified in `combat.md`. |
| `R` | Ready. | Routes to the equipment-ready handler in the status/equipment overlay. The picker, slot mapping, stock-counter mutations, and hand-occupancy gates are specified in `inventory.md`. |
| `S` | Search. | Routes to the Search handler, including secret-door and searchable-object paths. |
| `T` | Talk. | Town-family scenes route to the conversation engine. Overworld and dungeon scenes refuse; the overworld path may still prompt for a direction before printing its refusal. |
| `U` | Use. | Routes to the non-combat item-use handler. The implementation lives with the spell/item overlays rather than in the command dispatcher; usable-item families are specified in `inventory.md` and `catalogs/item-list.md`. |
| `V` | View / gem. | The dispatcher checks gem count first. If none remain, it prints the no-gem refusal. Otherwise it decrements the count and routes to LOOKOBJ for overworld/town view or DNGLOOK for dungeon view. Combat `V` is refused by the combat parser at no cost and does not consume a gem; see `view.md` and `combat.md`. |
| `W` | Default refusal. | No resident world-command handler is currently confirmed; it falls through to the stock "What?" response when it reaches this dispatcher. |
| `X` | X-it. | Routes to the vehicle-exit/dismount handler outside combat. Ordinary dungeon `X` is a refusal/no-op. Combat `X` is refused outright by the combat parser and does not leave a fight; the combat-only escape handler is bound to Escape instead, as specified in `combat.md`. |
| `Y` | Yell. | Routes to the Yell handler described in Section 11. Shipboard Y toggles sails as specified in `vehicles.md` and `weather.md`; non-ship branches handle words of power and Shadowlord-name effects. |
| `Z` | Z-stats. | Routes to the character/status display overlay. Character stat pages, equipment display, and shared-inventory browsing are specified in `inventory.md` and `text-output.md`. |

`R` Ready and `Z` Z-stats are worth calling out against the return contract of
Section 3: the status/equipment overlay produces no status word of its own, and
the dispatcher discards whatever it returns, so both letters always report the
default "acted". Opening either panel and immediately backing out therefore
costs a turn in every non-combat mode, and a refused ready costs exactly what a
successful one costs.

## 5. Verb Prefixes And Prompts

Every dispatcher arm prints a **verb echo** into the message window before it
invokes its handler or its refusal path. The echo is a fixed literal per letter,
and the literal's trailing punctuation is part of the contract rather than
decoration. This section publishes the rendered literals, the punctuation rule,
the line prompt, the direction prompt, the shared selection prompts, and the
entry narration.

Throughout this section an underscore stands for a literal space and `\n` for a
newline. Spaces at the start or end of a literal are load-bearing; they are the
reason the original's spacing looks uneven in places.

### 5.1 The line prompt is a glyph, not a character

Observers commonly transcribe the marker at the head of each echoed line as a
greater-than sign. **There is no greater-than character anywhere in the game's
output.** The marker is a *glyph*: the right-pointing solid triangle of the
fixed eight-by-eight text font - the same glyph the framed border labels use as
their **right** end cap - drawn on its own with no closing cap.

Every mode's turn loop opens its input line with the same two steps: emit a
newline into the message window, then draw that one triangle. The rule has
consequences an implementation must reproduce:

- The marker belongs to the turn loop, not to any verb literal. **No verb
  literal contains it.**
- It is emitted exactly once per input line, so it persists in the
  message-window scrollback exactly where it was drawn.
- The wrap-aware string printer emits no prefix of its own, so wrapped
  continuation lines carry no marker.
- A second line printed by the same command - a refusal, a follow-up prompt -
  also carries no marker. `Z-stats...` already ends in a newline, so the
  `Player:_` prompt that follows it starts a fresh **unmarked** line. A renderer
  that prefixes every message-window line with the triangle renders that case
  wrongly.

The **input cursor is a separate mechanism and is not the prompt marker.** It is
a four-frame animation over four consecutive text-font glyphs - a diagonal
barber-pole pattern shifted two pixels per frame - painted in the cell
immediately to the right of the prompt triangle, and erased with a space the
moment a key arrives. Neither the blink draw nor the erase advances the cursor
cell, so the verb echo begins in the cell the cursor occupied, one cell right of
the triangle. The animation's start glyph and its frame count are fixed data
that no code ever rewrites; an implementation may treat both as constants. The
blink loop itself is specified in `input.md`; the message-window echo cycle is
specified in `text-output.md` section 10.2, and the end-cap composite itself in
`display-driver.md` section 7.

### 5.2 Verb echo literals

The resident dispatcher owns one literal per letter. Each arm loads its own
literal; there is no key-indexed pointer array, and the literals are stored as a
plain block of text rather than as a table addressed by the key code.

| Key | Rendered echo | Notes |
|---|---|---|
| `Space` | `Pass\n` | Also the adjacent-direction-prompt cancel word. Escape is ignored by that prompt. |
| `A` | `Attack-` outside dungeons; `Attack\n` in a dungeon | Dungeon attacks are always straight ahead, so the dungeon form takes no direction and needs no hyphen. Each mode overlay carries its own copy of this literal. |
| `B` | `Board_` | Becalmed refusal: `Sheets_in_irons!\n` |
| `C` | `Cast...\n` | |
| `D` | `D-What?\n` | |
| `E` | `Enter_` followed by a place noun (section 5.5) | Off the overworld: `Enter_what?\n` |
| `F` | `Fire-` | |
| `G` | `Get-` | |
| `H` | `Hole_up-_` | Hyphen **then** a space. Bed refusal: `Only_in_bed!\n`. Shipboard and camp forms in section 5.5. |
| `I` | `Ignite_torch!\n` | |
| `J` | `Jimmy-` | |
| `K` | `Klimb-` | Dungeon form `Klimb-U/D-`, then `Up!\n`, `Down!\n` or `Failed!\n`. Gearless dungeon form: `Klimb-\nWith_What?\n` |
| `L` | `Look` then either `-` or `...\n` | See section 5.3. |
| `M` | `Mix_Reagents\n\n` | |
| `N` | `New_Order` | **No** trailing newline. |
| `O` | `Open-` | |
| `P` | `Push-` | Dungeon refusal replaces the echo entirely: `Push\nNot_here!\n`. Ordinary source/path refusals continue the direction echo; see Section 8.1. |
| `Q` | `Quit:` | |
| `R` | `Ready...\n\n` | |
| `S` | `Search-` (direction form) or `Search...\n` (in-place form) | |
| `T` | `Talk-` | Refusal tail `Funny,_no_response!\n`; one arm uses the combined literal `Talk-Funny,_no_response!\n` |
| `U` | `Use_item\n\n` | |
| `V` | `View_a_gem!\n` | Refusal on the **next** line: `You_have_none!\n` |
| `W` | `W-What?\n` | |
| `X` | `X-it_` | |
| `Y` | `Yell_` | |
| `Z` | `Z-stats...\n` | |
| `0` | `Set_Active_Plr:\n` | Cancelled: `None!\n`; rejected: `Invalid!\n` |
| buffer toggle | `Buffer_O` followed by `ff\n` or `n\n` | Prefix and suffix are separate literals. |
| any unmapped key | `What?\n` | The same text answers a key that is recognised but meaningless in the current mode. |

Two ordering details are easy to get wrong and are part of the contract:

- The echo is printed **before** the handler's precondition check. `V` prints
  `View_a_gem!\n` and only then discovers the party has no gem, so the refusal
  always appears as a *second* line rather than replacing the echo. The same
  shape applies to every other verb-then-refusal pair except the ones whose
  refusal literal folds the verb in.
- Refusal literals that begin with a verb word (`Push\nNot_here!\n`,
  `Talk-Funny,_no_response!\n`) replace the echo entirely; the ordinary echo is
  not printed first in those arms.

### 5.3 The trailing-punctuation contract

| Suffix | Meaning | Verbs |
|---|---|---|
| `-` | A **direction** is awaited. The chosen direction's name is appended on the same line. | Attack (outside dungeons), Fire, Get, Jimmy, Klimb, Open, Push, Search (direction form), Talk, Look (surface and town) |
| `...` | A **sub-selection** is awaited on another surface - a party member, an item, a spell, a page. | Cast, Ready, Z-stats, Search (in-place form), Look (dungeon) |
| trailing space | A further keystroke or a typed argument continues the **same** line. | Board, X-it, Yell, Hole up (hyphen then space) |
| newline, or nothing | The command completes immediately. | Pass, Ignite torch, Mix Reagents (two newlines), New Order (no newline at all), Use item (two newlines) |

**`Look` is the one dynamic case.** The stored literal is the bare word with no
punctuation. The dispatcher prints it and then takes one of two arms: in a
dungeon scene it prints the three-dot suffix and hands off to the dungeon look
overlay; everywhere else it emits a single hyphen **character** directly and
runs the direction prompt. That hyphen is the only echo punctuation in the game
produced dynamically rather than baked into a literal.

### 5.4 The direction prompt has no text

The shared direction prompt prints **nothing** before waiting. The hyphen at the
end of the verb echo *is* the prompt. The prompt loop accepts only the four
directions and Space:

| Key | Printed | Effect | Result to the caller |
|---|---|---|---|
| West | `West\n` | target X decreases by one | direction chosen |
| East | `East\n` | target X increases by one | direction chosen |
| North | `North\n` | target Y decreases by one | direction chosen |
| South | `South\n` | target Y increases by one | direction chosen |
| `Space` | `Pass\n` | none | cancelled |

The cancel word is the same word the Pass command echoes. A cancelled Look
therefore renders as the verb, the hyphen and the cancel word on one line.
Escape does not reach a cancellation arm: it emits nothing and the prompt reads
again. An earlier revision of this table listed `Space` **or** `Esc` as producing
`Pass` and a cancelled result, and section 8 said Escape at the P-Push prompt
cancels silently; both are retracted. This is the same adjacent-tile prompt contract published in `input.md`
Section 10.

**Movement keys echo the same four words.** On the overworld and in town-family
scenes, a movement key prints the direction's name followed by a newline, on its
own prompted line - the same four words the direction prompt appends. Several
mode overlays carry their own copy of the four-word block; they are identical.
Dungeon movement is the exception and uses its own verb set instead: `Advance`,
`Turn left`, `Turn right`, `Back up`, `Turn around.` and the refusal `Blocked!`,
each followed by a newline. See `dungeon-mode.md` section 9.

### 5.5 Entry narration and the location line

The overworld E handler first prints exactly `Enter_`, where `_` denotes one
ASCII space. It then reads the live tile under the party. That tile selects the
narration class and one of the two coordinate-table halves; the storage-family
key does not select the noun.

| Underfoot location class | Printed after `Enter_` |
|---|---|
| hut | `hut` |
| keep | `keep` |
| village | `village` |
| towne | `towne` |
| castle | `castle` |
| cave | `cave` |
| mine | `mine` |
| dungeon | `dungeon` |
| ruins | `ruins` with no newline; this is a direct non-transition arm |
| lighthouse | `lighthouse` |
| Codex shrine | `the_Shrine_of_the_Codex!\n` |
| virtue shrine | `the_shrine_of\n` followed by the coordinate-matched virtue name and `\n`. The seven stock surface cells are Honesty, Compassion, Valour, Justice, Sacrifice, Honor, and Humility; Spirituality has no stock surface `0x19` cell. |
| Blackthorn's palace | `the_palace_of_Blackthorn!` |
| Lord British's castle | `the_Castle_of_Lord_British!` |
| anything else | `What?\n`, producing `Enter_What?\n`; no action |

For most successful stock rows, the noun is followed by `\n\n`, the resident
uppercase proper name on a horizontally centered line, and `\n`. The centering
controls reposition the cursor; they emit no glyph and no ASCII padding bytes.
The three unnamed dwelling rows print only `hut\n`. The Lord British and
Blackthorn rows also omit the separate name line because their tile-selected
phrases already contain the name. Non-Doom dungeons print the same centered
uppercase name envelope; Doom success is only `Enter_cave\n`.

The authoritative forty-row plane, coordinate, class, exact continuation,
center column, and live-tile guard table is in `catalogs/gazetteer.md` Section
5.1. A line such as `Entered CASTLE:0 from BRITANNIA` or one containing raw
coordinates has no counterpart in the original and must not appear in the
production transcript. An earlier revision of this section stated the broader
absolute that the town's proper name is *never* printed and that any
`Entered <name> ...` line should be dropped or hidden behind a debug flag; that
is retracted — the proper name is printed, and only the bracketed diagnostic
form with a level number and raw coordinates is prohibited (`RETRACTIONS.md`
R271).

#### Entry failure, extension, and ordering contract

The two coordinate helpers have different no-match tails:

| Situation | Exact command transcript | Echo relationship | Result |
|---|---|---|---|
| Town-helper tile, but no row 1..32 matches | `Enter_<class>\nWhat_town?\n` | The live-tile class continues the normal `Enter_` prefix; the refusal follows on the next line | Acted; ordinary overworld turn |
| Dungeon-helper tile, but no row 33..40 matches | `Enter_<class>\nWhat_dungeon?\n` | Same envelope, with the dungeon-helper refusal | Acted; ordinary overworld turn |
| Live tile is not an accepted E-Enter tile | `Enter_What?\n` | `What?\n` continues the normal prefix on the same line | No action |
| Custom clean sidecar row has no narration class | `Enter_What?\n` | Treat the incomplete extension row as unrecognized; do not derive a noun from its key, coordinate, or storage family | No action; no transition |
| Dungeon row matches, but the party is not on foot | `Enter_<class>\nOn_foot!\n` | The transport refusal follows the tile-selected class | Acted; no transition |
| Doom row matches before all three Shadowlords are destroyed | `Enter_cave\nAttacked_at_entrance!\n` | Doom omits its proper-name line; the refusal follows `cave` | Acted; no transition; spawn the entrance ambush |

A coordinate and narration class are independent inputs. If a row matches and
the live tile is a different member of the **same** helper set, entry still
succeeds and the actual tile's noun is printed; there is no expected-class
comparison. If the live tile selects the opposite helper set, that helper does
not find the coordinate and prints its corresponding `What town?` or `What
dungeon?` refusal. This compatibility edge is why custom sidecar rows must name
their narration class explicitly.

The sealed dungeon-mouth tile `0xDF` is not an E-Enter tile and is also
impassable. Ordinary play cannot stand on it; a forced/debug invocation prints
`Enter_What?\n`, reports no action, and never reaches dungeon narration.

All successful entry narration is emitted **before** disk availability work,
the canonical write of the current plane's full live active-object table to its
`.OOL`, and the destination scene/arrival writes. Dungeon entry reads the
selected dungeon record after the `.OOL` write and before installing its scene.
A file retry therefore occurs after the narration is already visible. Direct or
debug construction of an interior/dungeon scene prints no entry narration,
because no E-Enter handler ran.

A successful scene transition exits the overworld loop before ordinary
post-action time and cleanup. Descending or climbing inside a dungeon prints
only the climb echo and a one-word result; the new level appears in the dungeon
frame label specified in `dungeon-mode.md` Section 4.1.

Two dungeon-specific narration lines do exist:

- Stepping onto a room-trigger cell prints `Entering_room...\n`.
- Leaving the level stack prints `\nExit_to_` followed by `Britannia!\n\n` or
  `Underworld!\n\n`.

The `H`-Hole-up family carries its own literals: `Hole_up_&_` plus
`\nrepair...\n\n` and `Hull_now_` plus `!\n\n` at sea, `camp!\n\n` on
land, `Sails_must_be\n` plus `lowered!\n\n` and `On_land_or_ship!\n\n` for
its refusals, and the prompts `For_how_many_hours?_(1-9)_`,
`\nWilt_thou_set_a_watch?_` (answered `Yes\n\n` or `No\n\n`),
`Who_will_stand_guard?_` and `None_posted!\n\n`. `On_foot!\n` is shared by
the Attack-family and dungeon-entry transport refusals.

### 5.6 Selection prompts and the cancel word

| Literal | Where it goes | Notes |
|---|---|---|
| `Player:_` | message window | Colon then exactly one trailing space. |
| `Item:_` | message window | Colon then exactly one trailing space. One caller uses a variant preceded by two newlines. |
| `None!\n` | message window | The universal cancel response. |
| `Nothing!\n` | message window | The empty-selection variant used where there was nothing to choose from. |
| `Invalid!\n` | message window | A selection outside the valid range. |
| `Done\n` | message window | Leaving an inventory page. The shared item picker's single Escape arm prints this when it was opened in R-Ready's mode, and prints `None!` when opened in its other caller's mode; the choice is made from the mode value alone. `systems/inventory.md` § 5.1 owns that attribution, which was settled on 2026-08-23 after being published as unverified. |

Several independent copies of the cancel word exist and one of them omits the
newline, so a compatible implementation should treat the newline as belonging to
the surrounding flow rather than to the word itself.

There is **no** `Player`, `Item` or `Select` heading string in the data that
carries angle-bracket characters. Where a panel's top border shows a framed
label, the brackets are the two end-cap glyphs drawn around a plain literal; see
`text-output.md` section 10.7 and `inventory.md` sections 4 and 5.

### 5.7 Prompt reentrancy

Handlers are allowed to re-enter the input system for follow-up prompts. The
input spec owns the cursor, prompt-character, typeahead, and reentrancy rules.
The command spec's contract is simply that prompts are synchronous: a handler
does not return to the mode loop until its prompt sequence has completed or been
cancelled.

Source provenance: derived from private analysis note
`../u5-decomp/notes/`.

## 6. N-New Order Party Command

N-New Order is a party-roster command for changing the travelling order. It is
available from the resident world-command dispatcher; combat has its own `N`
label and does not inherit this party-order effect.

The command prompts for two party members through the shared party-member
selector. Cancelling either prompt prints the no-selection result and returns
without consuming a turn. If either selected slot is slot zero, the command
refuses because the leader must remain first, and it returns without consuming
a turn.

On a successful non-leader selection pair, the command exchanges the two
selected roster records as whole thirty-two-byte character records. Name,
status, stats, class letter, equipment, and per-record counters all move
together. The party-size field is not changed, no world object or tile state is
touched, and the command marks the turn as consumed after the exchange. Picking
the same nonzero slot twice is accepted: the whole-record exchange is a
behavioural no-op, but the turn is still consumed.

The selector owns membership and cancellation validation; the New Order handler
trusts the non-cancel slot indices it receives except for its explicit slot-zero
leader check. Compatible implementations should therefore model New Order as a
swap of the current active party records, not as a rewrite of a separate
canonical companion-order table.

## 7. Search/Jimmy/Open/Get Tile Commands

The `S`, `J`, `O`, and `G` letters share one tile-interaction overlay. They are
mode-aware command handlers, not simple dispatcher stubs:

- **Overworld and town-family scenes** use the target cell in front of the party.
  The handlers run the shared reachability gate, compute the adjacent target
  from the current position plus the cached direction step, and read or rewrite
  the live map tile at that coordinate.
- **Dungeon scenes** route to smaller dungeon-specific inner handlers. Dungeon
  Get and Open act on the underfoot dungeon cell; dungeon Search and Jimmy use
  the dungeon chunk-grid representation rather than the surface/town map tile
  fetch.
- **Combat scenes** do not use this resident route. Combat has separate
  same-letter parser branches; matching labels in combat must not be assumed to
  inherit these world-mode effects.

`G` Get picks up things from the target cell. In surface/town scenes it first
scans the current map's object table for a matching pickup slot, but it does not
accept every record at that coordinate. The accepted set is limited to special
pickup-category markers and the loose-object visual family; actor, blocker,
already-handled, and unrelated object entries are skipped even if their
coordinates match. Accepted slots dispatch the slot's item code into the
inventory-add routine. If that object is a Search-surfaced Moonstone "strange
rock", the pickup grants the Moonstone and invalidates the associated Gate
Travel slot. If no accepted object slot matches, Get falls back to tile-specific
cases such as borrowing a table item, picking crops, or eating from a reachable
plate; otherwise it prints the nothing-to-get refusal. In dungeons, Get reads
the underfoot cell: closed chest cells refuse until opened, open chest cells are
consumed in the loaded dungeon image and roll the seven-row reward generator
described in `containers.md`, and unrelated cells refuse.

`J` Jimmy is the key-and-lock handler. Non-dungeon Jimmy checks key stock first
and refuses outright when it is zero. It then splits by target into exactly two
rolls, both of which read the acting member's Dexterity and neither of which
reads any class or profession field:

- A **flat Dexterity test** for locked doors (`0xB9`, `0xBB`) and for restraint
  tiles (stocks `0x84`, manacles `0x85`). Success chance is Dexterity divided
  by thirty, clamped. A door becomes its unlocked counterpart. In ordinary
  town-family scenes, a restraint first requires a live occupant; an empty
  restraint exits before the member prompt or roll. First successful release
  clears that NPC's dialogue/awareness field, changes every schedule period to
  AI mode 5, grants the thanks line and moral-standing increase, and records a
  persistent removal for the next location entry. The actor remains in the
  current visit, pursuing without its adjacent attack event. Magically locked
  doors (`0x97`, `0x98`) are refused before this roll and still cost a key.
- A **difficulty-versus-Dexterity threshold** for containers, used both for
  per-map container objects on the surface and for dungeon chest cells. Success
  clears the container's combined lock/trap flag, so a successful Jimmy also
  disarms.

Key accounting depends on where the attempt ends. Successful picks spend no
key. Failed rolls and the magic-lock refusal break one. An empty restraint, a
cancelled member selection, the generic no-lock result, and other pre-roll exits
spend none. A failed pick changes nothing else, so container contents are never
lost. There is no pickpocket branch in this command, and floor and town chests
are container objects rather than tiles, so they always take the threshold
roll. Key cost does not determine turn cost: the world-mode dispatcher reports
the normal committed-action result after every Jimmy exit, including those
zero-key exits, and combat Jimmy ends the acting combatant's action.
Detailed lock-state and prisoner-lifecycle rules live in
`doors-and-z-transitions.md`.

`O` Open is the no-key counterpart. Non-dungeon Open runs the door auto-close
tracker before probing the target tile. Already-open targets acknowledge that
state, heavy targets refuse without a lock-pick roll, locked targets refuse,
openable targets snapshot their previous tile and rewrite the live cell to the
open tile, and unclassified chest-like fallthroughs are delegated to the chest
helper. Dungeon Open checks the underfoot dungeon class: door cells route to the
dungeon door opener, chest cells open, and unrelated cells refuse.

`S` Search probes for hidden objects, traps, secret features, and buried
Moonstones. In surface/town scenes, Search first runs the shared pre-search
gate and direction prompt. A failed gate or cancelled direction exits without a
map, inventory, or object-table change. A successful prompt computes the
adjacent target cell, then scans the live runtime object table for a hidden
entry at that coordinate. Multi-floor locations also require the hidden entry
to belong to the active floor/chunk. A matching hidden object prints the found
result and dispatches the object through the same inventory-add path used by
pickup/container commands.

If no hidden object is found, surface/town Search checks for a slot-indexed
treasure marker at the target coordinate. That coordinate lookup scans the
active-object table in reverse priority order and only the treasure marker
short-circuits into an immediate found-object grant. Other active-object
classes do not drive the fallback narration; Search uses the live tile byte
read before the coordinate lookup.

The live-tile fallback table supplies fixed furniture/location prefixes such
as stump, shelf, bookshelf, wall, desk, barrel, vanity, bed, dresser, trunk,
brazier, and fireplace. The hidden-door marker is the mutating case: it prints
the hidden-door result, rewrites the live tile to the revealed variant, marks
the map dirty, and stops. Otherwise, Search continues through the saved
Moonstone table, rare-reagent harvest table, and fixed hidden-treasure table
in that order; one live-tile marker skips only the Moonstone table before
continuing. Object-table, slot-indexed treasure, Moonstone, reagent, and fixed
hidden-treasure results feed their owning inventory or pickup-staging paths.
Ordinary feature descriptions are narration only. Per-map object slots that
carry trap-class metadata use a member-stat threshold roll only to choose the
visible no-trap/simple/complex/generic-trap narration, including possible
missed traps and false positives. Actual trap effects are owned by the later
trap resolver when a caller selects one.

Dungeon Search does not use the surface object-table scan. It routes to the
dungeon inner handler, which first enforces the dungeon light gate: with no
torch light and no light-spell duration remaining, Search reports that it is too dark and
does not inspect the cell. In light, it reads the packed dungeon cell ahead of
the party and classifies by high nibble. Ordinary ladders, doors, walls, pits,
fountains, open chests, fields, and flavour objects print feature-specific
search descriptions. Chest cells use the dungeon chest trap/detail branch.
Exact pit-family Search bytes cover ordinary pit, secret-passage reveal, and
bomb detection/springing, while flavour/wall classes can rewrite only the
visit-local loaded dungeon image. Those dungeon Search rewrites are specified
in `dungeon-mode.md`. Three of them—exact `0x61`, the Doom-flavour `0xC?`
skeleton branch, and the `0xD?` hidden-door branch—also redraw the changed
first-person view on the hidden surface and dissolve it into the visible
viewport before Search returns. This presentation tail belongs only to Search;
no Open outcome calls it. Inventory grants and chest contents belong to
`containers.md` and `catalogs/item-list.md`.

When an Open or container outcome selects the shared resident trap-effect
resolver, the common party damage and poisoning effects are specified in
`systems/traps.md`. The command layer owns routing and prompt/refusal text; the
trap spec owns the selected effect once the routing layer has chosen it. The
routing layer passes no trap flavour: a container is trapped or it is not, and
the resolver picks the flavour itself. Search narration classifies traps but
never enters that resolver, and Jimmy does not either — a successful Jimmy
clears the same flag that marks the container trapped, so it disarms as well as
unlocks.

## 8. P-Push Movable-Tile Command

P-Push is a direction-prompt command for movable static map furniture. Before
waiting for the direction, the handler runs the same last-opened-door cleanup
used by other directional CMDS commands, so a previously opened door may close
even when Space later cancels the command or Escape leaves the prompt waiting.

The command samples the adjacent source cell in the chosen direction. In every
noncombat scene this coordinate is relative to the party. In combat, the
acting combatant's arena coordinate temporarily becomes the command anchor;
after a success both that combat descriptor and its linked active-object
coordinate advance, the party coordinate globals are restored, and the arena
receives a full redraw.

A source cell is pushable only when no non-player active object occupies that
coordinate and its static tile is in the known pushable set:

| Pushable tile family | Behaviour |
|---|---|
| `0x5B` | Single non-rotating pushable class. |
| `0x90..0x93` | Four-facing chair family; successful movement rewrites the facing bits. |
| `0xA5`, `0xA6`, `0xA8`, `0xA9` | Non-rotating pushable classes. |
| `0xAD..0xAF` | Non-rotating pushable run. |
| `0xB4..0xB7` | Four-facing cannon family; successful movement rewrites the facing bits. |

An active object at the source is an immediate refusal; P-Push never moves an
active-object record. If the source is unoccupied but its static tile is not in
the table, the same refusal applies.

The cell one tile farther in the same direction decides whether the command is
a push or a pull:

- **Push.** If the far cell has no active object and its static tile is the
  expected floor/occupancy stamp for the source object family, the source object
  moves into the far cell and the source cell receives that stamp. Directional
  families are rotated to face the movement direction.
- **Pull.** If the push path is blocked but the avatar's current cell already
  carries the matching stamp, the object is dragged into the avatar's old cell
  and the source cell receives the old player-cell stamp. Directional families
  are rotated with the opposite-facing rule used for pulling.
- **Final refusal.** If neither path is legal, the command prints the shorter
  "won't budge" refusal and exits.

On any successful push or pull, the avatar—or the acting combatant in an
arena—advances one tile in the prompted direction and the map is marked dirty.
The command mutates the live tile buffer; implementations should not model it
as an overlay-only animation.

### 8.1 Exact transcript and result table

The strings below begin with the command echo; they exclude the turn loop's
preceding newline and prompt glyph. `<Dir>` stands for exactly one of `North`,
`South`, `East`, or `West`. The `\n` after it is part of the direction echo.
There is no distinct Pass input: Space is the key and `Pass` is its echo.

| Row | Source/destination outcome | Exact rendered command text | Echo relationship | Door cleanup | Completed-result status |
|---|---|---|---|---|---|
| A | Escape pressed at the direction prompt | `Push-` remains open; Escape emits no byte | Prompt remains active; there is no cancellation or continuation | Already ran before the prompt | No command result yet in overworld, town, or combat |
| B | Space pressed at the direction prompt | `Push-Pass\n` | `Pass\n` completes the normal `Push-` echo; no result line follows | Yes | Default acted status in overworld/town; ends the combatant's action |
| C | No active object at source; source static tile is not pushable | `Push-<Dir>\nWon't budge!\n` | Emphatic refusal continues after the normal direction echo | Yes | Default acted status in overworld/town; ends the combatant's action |
| D | Source or far coordinate outside a playable interior/combat grid | No separate bounds literal or status; apply Section 8.2 | Normal echo remains; the sampled tile/object predicates choose the continuation | Yes | No analogous finite-grid edge in the overworld; default acted status in town/interiors; ends the combatant's action |
| E | Static source is pushable; push is blocked; actor cell is not the matching pull stamp | `Push-<Dir>\nWon't budge\n` | Short refusal continues after the normal direction echo | Yes | Default acted status in overworld/town; ends the combatant's action |
| F | Active object occupies the source; far cell also has an actor/object | `Push-<Dir>\nWon't budge!\n` | Emphatic refusal continues after the normal direction echo | Yes | Default acted status in overworld/town; ends the combatant's action |
| G | Active object occupies the source; far terrain is not legal | `Push-<Dir>\nWon't budge!\n` | Same as F; the far coordinate is never tested | Yes | Default acted status in overworld/town; ends the combatant's action |
| H | Successful static push | `Push-<Dir>\nPushed!\n` | Success line continues after the normal direction echo | Yes | Default acted status in overworld/town; ends the combatant's action |
| I | Successful static pull | `Push-<Dir>\nPulled!\n` | Success line continues after the normal direction echo | Yes | Default acted status in overworld/town; ends the combatant's action |
| J | Successful dynamic-object push | Unreachable. A dynamic source takes F/G's `Won't budge!\n` result and its record is unchanged | No success continuation exists | Yes | No distinct status; the actual refusal uses F/G's status |
| K | Dungeon P refusal, before direction handling | `Push\nNot here!\n` | Combined refusal replaces `Push-`; there is no direction prompt | No; the shared handler is bypassed | Resident dispatcher reports no action |

Rows F, G, and J deliberately correct the earlier dynamic-source description.
The source active-object test occurs before the far coordinate is computed, so
far occupancy and terrain cannot distinguish those rows and no production path
prints a dynamic-object success.

The combined dungeon refusal applies to the ordinary dungeon scene range. Its
no-action result skips the dungeon post-action pass, but dungeon time has
already advanced by one minute at that loop iteration's head. Outside dungeons,
the resident dispatcher discards the Push handler's return: every completed
row B through J therefore consumes the ordinary action—two minutes plus normal
post-action work in the overworld, one minute plus normal underfoot and NPC
work in town. Combat's direct P route ends the acting combatant's action for
every completed row B through J, including both refusals.

The command never prints tile ids, coordinates, active-object slot numbers,
terrain-class names, or the word `blocked`. It does print the exact success
words `Pushed!` and `Pulled!` shown above; there is no other diagnostic success
line.

### 8.2 Out-of-grid and combat-reveal edge cases

P-Push has no command-local playable-grid bounds test.

- The overworld uses a streamed map rather than the finite interior or arena
  grid in row D, so that row has no analogous overworld boundary transcript.
- In a town-family/interior scene, an out-of-range tile sample aliases the
  loaded grid's southeast cell `(31,31)`, while the true out-of-range
  coordinate cannot match a normal active-object record. Every shipped page in
  the town, castle, dwelling, and keep map families has a southeast tile that
  is not pushable. A stock out-of-range **source** therefore takes row C. For an
  out-of-range **far** coordinate, the stock southeast tile never matches the
  required push stamp: the command takes row I if the actor cell supplies the
  matching pull stamp, otherwise row E.
- In combat, an off-playable-grid tile sample reaches temporary arena backing
  state rather than a bounds sentinel. Its transcript is selected by that
  sampled byte and the ordinary source/far/pull predicates; there is no single
  extra combat bounds result and no `Blocked!` line. Tests of this original
  edge must supply the sampled temporary byte as part of their fixture.
- In ambush or camp combat, a pre-placed reveal marker at the chosen adjacent
  coordinate preempts the ordinary source test. It consumes/reveals that marker
  and leaves the transcript at exactly `Push-<Dir>\n`, with no `Pushed!`,
  `Pulled!`, or refusal continuation. The combatant's action still ends.

**The stamp is never persistent.** This is now a certainty rather than a
negative bound. The push writes through the shared tile accessor, which can
only hand back a cell inside one of three live buffers: the combat arena grid,
the overworld sliding chunk window, or the single location grid. Nothing the
game ever writes to disk covers any of those three: the persisted state is the
saved-state window, the two per-world object tables, and the live object list,
and the saved-state window ends immediately below the live tile buffer. The load
side matches — a load restores exactly the window that was written and nothing
above it, location tiles are re-read wholesale from read-only location data on
every entry, and overworld tiles are streamed a quadrant at a time from the
read-only world data files. A stamp therefore lasts exactly as long as the
current occupancy of the live tile buffer: until the location is re-entered,
until the overworld window streams that region in again, until another command
rewrites the cell, or until the combat framer tears the arena down. A pushed
chair's trail cannot survive a save/load round trip in any scene class, and no
tile mutation of any kind is durable. The generic stamp `0x44` and the cannon-family
stamp `0x45` both resolve to the same cobble description in the
LOOK2-backed tile catalog. The separate stamp byte is still load-bearing for
P-Push's family-matching rule, but it does not require a distinct public
visual label.

Combat is a supported caller of this same handler. The combat command parser
prints the `Push-` label and enters P-Push directly, without the live-actor gate
used by the combat Get/Jimmy/Open/Search prompt helper. Because combat runs with
an actor-anchor scene frame, a successful push/pull advances the currently
acting combat actor in the arena and mutates only the temporary combat tile and
object state that the combat framer later tears down.

## 9. Special Non-Letter Dispatcher Input

The dispatcher accepts exactly one non-letter code: the typeahead-buffer toggle,
produced by typing Control with the second letter of the alphabet. The
dispatcher flips the typeahead setting, prints the corresponding Buffer On /
Buffer Off message, and reports "no action", so the toggle never consumes a
game turn. Combat owns a second, independent copy of the same toggle that writes
the same setting (`combat.md`).

This code is a typed Control character, not a cursor or numpad code. The
keyboard layer's rewrite of typed Control characters into the high pseudo-code
range is suppressed for any key that arrived through the scancode table, so an
arrow or numpad key can never be delivered as the toggle. Cursor and numpad
direction keys produce the four cardinal movement codes, which the active mode
loop consumes; the corner keys produce the four diagonal codes, and the function
keys produce their own block. None of those reach letter dispatch, and all of
them fall to the dispatcher's stock refusal if they somehow do.

Every mode loop owns a small pre-dispatch control-code table of its own. The
four shared bindings, all of them typed Control characters, are:

| Binding | Behaviour |
|---|---|
| Control + `E` | Prompts "Exit to DOS?"; a yes answer leaves the game, anything else prints the refusal and continues. |
| Control + `K` | Prints the party's scalar moral-standing value as a number. |
| Control + `S` | Toggles sound, printing the new on/off state. |
| Control + `V` | Prints the version banner. |

None of the four consumes a turn in any mode. Beyond them the tables agree on
the four cardinal direction codes, which route to that mode's movement handler,
and differ only in the surrounding detail: which unrecognised codes are silent
and which print the stock refusal, and what extra pre-dispatch stages the loop
runs first — the overworld's water and moongate probes and its under-sail
cadence, town's drunkenness scrambler, dungeon's inlined render-and-poll. The
party-capability check is not one of those differences: all three exploration
loops run it identically ahead of the input block, as `systems/main-loop.md`
Section 6 specifies.
Dungeon mode also accepts Enter and the period key as movement, and treats
digits as a solo-member select that always reports "no action". Combat replaces
the scheme entirely with its own parser, which adds Escape, Space, the
actor-select digits and its own buffer toggle. Per-mode detail belongs to
`input.md`, `overworld.md`, `town-mode.md`, `dungeon-mode.md`, and `combat.md`.

## 10. H-Hole-Up Rest Contract

H-Hole-Up is routed by scene before the detailed rest handler runs:

- **Overworld and dungeon.** The dispatcher calls the resident rest-with-watch
  wrapper. That wrapper performs the wilderness/dungeon rest flow and can turn a
  rest interruption into an ambush-style combat.
- **Town-family locations.** The dispatcher first requires the party to be on a
  bed/inn-style tile. If the tile gate fails, the command is refused. If it
  succeeds, control enters the hours-prompt rest path.
- **Combat.** Combat has its own H label and refuses the action; world-mode rest
  is not available inside an arena.

The rest handler saves the current input mode, probes whether the current tile
allows rest, walks the party slots, prints the sleep narration, and prompts for
the number of hours when the path requires an explicit duration. Poisoned and
dead members are not treated like healthy sleepers. Sleeping party members are
restored to good status during cleanup.

Recovery is not part of this routing contract and is not a per-hour drip. The
town-bed path has no recovery block of its own at all. Only a *completed long
camp* recovers anything, and it does so once, at the end, under the guard set
and with the `1..63` hit-point roll and class-keyed magic-point rules specified
in `systems/rest-and-camp.md` section 5. An earlier revision of this section
described a "small random HP gain" with a "class-aware regeneration gate";
that was a conflation of the camp block's hit-point roll with its separate
class-keyed magic-point write, and it is withdrawn.

The town hours path advances elapsed rest with a caller-owned loop rather than
by handing the clock one large "N hours" value. It accepts one nonzero digit,
runs one bounded burst of up to sixteen schedule/world-tick passes, then
advances elapsed rest in repeated ten-minute cleanup calls until the target hour
is reached or the rest surface rejects the party. If an interruption or refusal
fires, the command stops early and hands control to the ambush/refusal path;
elapsed time already applied is not rolled back. If the duration completes, the
command prints the normal rested result and stamps the current camp/rest marker.

## 11. Y-Yell Command

Y-Yell is a mode-sensitive command with three visible families.

The no-input sail branch has two exact gates: the party transport marker must
be any frigate value, and the unsigned scene byte must be below `0x80`. It is
not restricted to scene zero or to a top-down world scene. Consequently it
accepts scene `0` on either world plane, all town-family scenes `1..32`, and
defensive/custom scenes `33..127`. In any accepted scene, Yell toggles the ship
between hoisted and furled sail states while preserving heading, prints the
corresponding short sail command, and does not move the ship immediately.
Wind-driven movement and X-it's under-sail refusal remain vehicle-system
behaviour; this command only changes the sail state.

| Transport and unsigned scene | Yell behavior |
|---|---|
| Frigate, scene `0` | Toggle sails on either Britannia or Underworld; the plane is separate from the scene byte. |
| Frigate, scene `1..32` | Toggle sails. |
| Frigate, scene `33..127` | Toggle sails, including defensive dungeon/custom state. |
| Frigate, scene `128..255` | Do not toggle; enter the ordinary word prompt. |
| Any non-frigate marker | Enter the ordinary word prompt, regardless of scene. |

The accepted sail branch prints `FURL!` when changing from hoisted to furled
and `HOIST!` for the inverse change. The toggle is a committed action and must
be reported to the active mode loop as **acted**, so it consumes that mode's
action/turn. The shipped executable accidentally forwards an incidental text-
renderer value on this path instead of a normalized command status; that
register leak is the same original defect described in Section 3 and is not an
additional sail rule to reproduce.

When the party is not in the ship-sail branch, Yell prompts for a free-text
word of up to thirty characters using the same style of line input as the
conversation keyword path. Empty input prints the nothing-said result and
returns without a command-specific world mutation. Nonempty input is routed by
scene context:

- **Shadowlord-name contexts.** Only the three Eternal Flame keeps — The
  Lycaeum, Empath Abbey, and Serpent's Hold — accept Shadowlord names. In one of
  those three scenes the typed word is compared with the three Shadowlord names.
  A matching name summons that Shadowlord only when all three of these hold:
  that Shadowlord's slot is not vanquished; the party's Y coordinate is at least
  `2`, so there is room two rows north of the party; and **no Shadowlord actor is
  already present in the scene** — the handler rejects the summon if any live
  active-object slot already carries the Shadowlord actor tile (`0xFC`, the
  Shadow Lord row of `catalogs/monster-bestiary.md`). That last test is a
  one-at-a-time rule, not a "table is full" rule: an engine that instead checks
  for a free slot will let the player stack Shadowlords.
  On success the handler records which Shadowlord is now active (the handshake
  the destruction path checks), installs the Shadowlord as an active object
  **exactly two cells north of the party** in the party's current floor and
  region, and plays the appearance line together with the long warble and the
  fade-in effect. The actor takes the highest free active-object slot, searching
  downward from the last slot.
  Any of the three names works in any of the three keeps; the pairing is enforced
  later by the destruction position, not here. Wrong names, any other scene, a
  vanquished Shadowlord, a party standing within one row of the north edge, or a
  Shadowlord already present all produce no effect.
- **Word-of-Power contexts.** Only the outdoor scene accepts Words of Power.
  Both world surfaces qualify, because both use the outdoor scene with the
  plane distinguished by the party's floor/depth byte. There is no
  dungeon-interior, town, or keep Word-of-Power route. The full predicate is
  given below.
- **Other contexts.** Prompted scenes that are not accepted by either
  Shadowlord-name or Word-of-Power routing produce no effect after the prompt.

This prompt path also supplies the exact rejected-ship behavior. A frigate
marker with scene `0x80..0xFF` does not print an immediate sail refusal: it
asks the ordinary `Yell what?` question and accepts up to thirty characters.
Empty input prints the ordinary nothing-said result. Nonempty input in this
range prints the ordinary no-effect result. Both outcomes count as acted under
the clean return contract. Combat is a reachable example: its parser calls the
shared Yell handler with scene `0xFF`, so even a defensive frigate marker in
combat follows the prompt, never the sail toggle.

### 11.1 The Word-of-Power seal predicate

The command scans the eight dungeon Words of Power in their fixed order and
takes the first prefix match. A recognised word immediately prints the
uttered-word result and plays the shared low-rumble / full-viewport flash
presentation effect, before any location test. An unrecognised word prints the
no-effect result and nothing else happens.

After a recognised match the handler picks a direction, then checks a
coordinate, then mutates one cell:

1. **Direction.** It inspects the four cells cardinally adjacent to the party in
   the currently visible map, in the order west, south, east, north, and takes
   the first one whose tile is any of: that word's own dungeon-entrance tile,
   the sealed collapsed-entrance tile, or the ruined-shrine tile. If no
   neighbour qualifies, the command additionally prints the no-effect result and
   stops. **The party stands next to the sealed cell, never on it** — the sealed
   tile is impassable, so standing on it is not possible anyway.
2. **Ruined-shrine branch.** If the neighbour selected in step 1 is a ruined
   shrine, the handler hands off to the shrine restoration prompt with the
   word's index and that adjacent cell's coordinates. It then exits without
   running the ordinary entrance-coordinate check, entrance-tile toggle, or
   Word-of-Power seal-flag toggle. This branch is reachable in normal play;
   earlier public wording that called the mantra-style Yell branch unreachable
   was wrong. `systems/karma.md` Section 7.1 owns the direct word-to-virtue
   mapping, four mandatory text responses, messages, state writes, and acted
   result.
3. **Coordinate.** Otherwise the handler requires the selected neighbour's
   world coordinate to equal that word's published dungeon entrance coordinate
   (`catalogs/gazetteer.md` Section 5.1). Speaking a valid word anywhere else
   still produces the utterance feedback and presentation effect, but changes
   nothing. Note that the check compares only the horizontal coordinate pair, so
   the same word works at the same coordinate on either world surface.
4. **Mutation.** On a coordinate match the handler toggles the cell between the
   sealed collapsed-entrance tile and that dungeon's own entrance tile, and
   toggles that word's saved seal flag. The mutation dirties visibility so the
   changed cell is redrawn.

The per-word entrance tile is fixed data:

| Word | Dungeon | Entrance tile shown when unsealed |
|---|---|---|
| `FALLAX` | Deceit | `0x18` dungeon |
| `VILIS` | Despise | `0x16` dark cave |
| `INOPIA` | Destard | `0x16` dark cave |
| `MALUM` | Wrong | `0x18` dungeon |
| `AVIDUS` | Covetous | `0x18` dungeon |
| `INFAMA` | Shame | `0x17` abandoned mine |
| `IGNAVUS` | Hythloth | `0x17` abandoned mine |
| `VERAMOCOR` | Doom | `0x16` dark cave |

The sealed form is tile `0xDF` for all eight. Equivalently, the mutation in step
4 flips the cell by the difference between the two ids, which is why a single
rule covers all eight words.

All three unsealed variants are ordinary passable terrain; the single sealed
tile shared by all eight is impassable. `catalogs/tile-catalog.md` carries the
tile identities.

### 11.2 Seal persistence

The per-word marker is **not** scratch. Earlier public wording that called it
non-contractual bookkeeping with no live reader was wrong and is retracted.

Eight save-backed flags, one per word, record whether that word has been
spoken. They are durable state in the save image (`formats/saved-gam.md`
Section 9.1) and start clear on a new game, so **every dungeon entrance begins
sealed**. The shipped world maps always store the unsealed entrance tile; the
sealed presentation is re-derived from these flags every time a map region is
loaded into the live view. Concretely, when a map chunk is loaded, any cell
holding one of the three dungeon-entrance tiles is rewritten to the
collapsed-entrance tile if the word owning that chunk is still unspoken. The
same pass rewrites shrine cells to the ruined-shrine tile according to a
parallel set of eight saved shrine flags. The gating is per chunk, not per cell:
each word owns exactly one of the 256 map chunks, and the two rules take
opposite defaults for a chunk that owns no word or no shrine. The loader-side
statement of the rule, with those defaults, is in `formats/brit-dat.md`
Section 9.1, and it applies identically to both world surfaces
(`formats/under-dat.md`, `systems/overworld.md` Section 3).

Two consequences an implementation must honour:

- Unsealing survives save, reload, and leaving and re-entering the region. An
  engine that mutates only its live tile buffer will silently re-seal the
  dungeon when the region reloads.
- The mutation is a genuine toggle. Speaking the same word again while standing
  beside an already-open entrance clears the flag and re-seals the entrance.

## 12. Cross-References

- `input.md` describes keyboard polling, uppercase folding, direction-code
  translation, prompt reentrancy, and the handoff to this dispatcher.
- `main-loop.md` describes where the resident dispatcher sits in the four
  top-level mode loops.
- `overworld.md`, `town-mode.md`, and `dungeon-mode.md` document the mode-local
  pre-routing that happens before printable letters are forwarded.
- `combat.md` documents the separate combat command dispatcher.
- `vehicles.md`, `weather.md`, `magic.md`, `doors-and-z-transitions.md`,
  `conversation.md`, `shops.md`, `save-load.md`, `lighting.md`, and
  `catalogs/quest-graph.md` document major command families after dispatch.

## 13. Dispatcher Boundaries And Remaining Work

The resident command-dispatch contract is complete at A-Z routing depth: mode
pre-routing, scene-aware letter families, no-action fallthroughs, command
prompt ownership, typeahead toggle, save route, major CMDS/SJOG/CAST/ZSTATS
delegates, per-handler return values, mode-local control-code tables, and
P-Push stamp durability are all fixed. The items below are the residual
boundaries.

- **Per-handler return values — closed.** The status is the four-member enum of
  Section 3, only six routes forward a handler's own value, and each forwarded
  value is itself only "acted" or "no action". The single wrinkle is the trio of
  Yell paths that return an undefined value in the original; an implementation
  treats those as "acted" and never reproduces the residue. There is no global
  turn-consumed flag to model: an earlier reading that treated a shared resident
  byte as a cross-mode turn sentinel is withdrawn — that byte is a stats-panel
  repaint request, a rendering concern rather than a timekeeping one.
- **Full control-code pre-routing — closed.** Each mode loop owns its own small
  control-code table; the four tables agree on the four shared bindings and the
  cardinal direction codes, and combat replaces the scheme with its own parser
  (Section 9). The mode specs carry the per-mode detail.
- **P-Push stamp durability — closed.** The stamp is a live-buffer mutation
  only and can never survive a save/load round trip (Section 8). The remaining
  question is presentational: the generic `0x44` stamp and the cannon-family
  `0x45` stamp both resolve to cobble through LOOK2, and why the chair-style
  family gets its own byte is a rendering question rather than a dispatch one.
  The byte distinction is still load-bearing for P-Push's family-matching rule.

## 14. Sources

This cleanroom spec was derived from the private analysis notes listed below.
No decompiled code, assembly, raw address tables, or copied data strings are
reproduced here.

- The resident A-Z dispatcher, scene-aware letter routing, verb-prefix scheme,
  gem gate, save-game route, typeahead toggle, and return-value categories:
  `u5-decomp/functions/ULTIMA_EXE/`.
- The save-game handler reached by `Q`, including its prompt, save/cancel
  branches, file writes, and return-to-caller behaviour:
  `u5-decomp/functions/CAST2_OVL/`.
- The overworld mode loop's pre-dispatch control-code table and separate quit
  prompt path: `u5-decomp/functions/MAINOUT_OVL/`.
- The dungeon mode loop's pre-dispatch handling of digits, sound toggle, and
  explicit exit prompt:
  `u5-decomp/functions/DUNGEON_OVL/`.
- The CMDS overlay command-family inventory and corrected F/J/O/G/S ownership:
  `u5-decomp/functions/CMDS_OVL/`, and
  `u5-decomp/functions/CMDS_OVL/`.
- The M-family split between CMDS reagent mixing and CAST2 shrine/urn entry:
  `u5-decomp/functions/CMDS_OVL/` and
  `u5-decomp/functions/CAST2_OVL/`.
- The New Order active-party record exchange, leader refusal, cancel paths, and
  same-slot self-swap behaviour:
  `u5-decomp/functions/CMDS_OVL/`.
- The Y-Yell unsigned sail-scene gate, sail-result action status, free-text
  fallback, Shadowlord-name branch,
  Word-of-Power seal predicate, saved per-word seal flags and the region-load
  pass that re-applies them, and the ruined-shrine mantra hand-off:
  `u5-decomp/notes/`,
  `u5-decomp/functions/CMDS_OVL/`,
  `u5-decomp/functions/OUTSUBS_OVL/`,
  `u5-decomp/functions/CMDS_OVL/`, and
  `u5-decomp/functions/CMDS_OVL/`.
- The P-Push direction prompt, pushable tile families, push/pull branch
  conditions, facing rewrite, combat actor-anchor side effects, and
  live-tile mutations:
  `u5-decomp/functions/CMDS_OVL/`. The non-durable
  save/load boundary for top-down live buffers also uses
  `u5-decomp/notes/` and
  `u5-decomp/functions/TOWN_OVL/`.
- The exact Push strings, Escape-versus-Space prompt result, active-object
  refusal polarity, bounds behavior, combat reveal preemption, caller status,
  and door-cleanup ordering are derived from private analysis in
  `u5-decomp/functions/CMDS_OVL/`, `u5-decomp/functions/ULTIMA_EXE/`,
  `u5-decomp/functions/COMBAT_OVL/`, `u5-decomp/functions/DUNGEON_OVL/`, and
  `u5-decomp/notes/`.
- The Search/Jimmy/Open/Get overlay overview and public command handlers:
  `u5-decomp/functions/SJOG_OVL/`.
- The two-roll J-Jimmy contract, its corrected target families, the Dexterity
  operand shared by both rolls, branch-specific key accounting, the restraint
  actor lifecycle, and the fact that no trap flavour is chosen by any caller.
  Source provenance: derived from private analysis in
  `u5-decomp/functions/SJOG_OVL/`, `u5-decomp/functions/TOWN_OVL/`, and
  `u5-decomp/notes/`.
- The Search coordinate-object fallback:
  `u5-decomp/functions/ULTIMA_EXE/`.
- Corrected entry notes for the shared Look/View and Ready/Z-stats command
  families: `u5-decomp/functions/LOOKOBJ_OVL/`,
  `u5-decomp/functions/ZSTATS_OVL/`, and
  `u5-decomp/functions/ZSTATS_OVL/`.
- The CAST-owned U-Use item route:
  `u5-decomp/functions/CAST_OVL/`.
- The four-member status enum of Section 3, the per-route forwarded values, the
  undefined Yell paths, the per-mode control-code tables and the single accepted
  non-letter code of Sections 2 and 9, and the established save/load boundary
  for the P-Push stamp in Section 8. Source provenance: derived from private
  analysis in `../u5-decomp/notes/`, with
  `../u5-decomp/functions/ULTIMA_EXE/`,
  `../u5-decomp/functions/DUNGEON_OVL/`, and
  `../u5-decomp/functions/CMDS_OVL/`.
- The withdrawal of the global "turn consumed" flag reading, and the fact that
  Ready and Z-stats always report the default status. Source provenance:
  derived from private analysis in `../u5-decomp/notes/`.
