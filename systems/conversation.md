# Conversation

## 1. Overview

Ultima V's NPC conversations are driven by a small interpreter that runs a per-NPC byte-code stream. Each NPC carries a "blob" of interleaved obfuscated text and one-byte control codes; the engine prints the text with substitutions for common words and the player's name, prompts the user for a keyword, checks a fixed engine keyword table, then scans the NPC blob's ordinary keyword pairs and runs the selected response through the same interpreter. The interpreter also handles flag-driven branches, party-recruitment prompts, gold transactions, the town alarm sweep, GOTO labels, and two ways of asking the player a name.

Almost all observable conversation behaviour — the questions an NPC will ask, the gold they want, who joins the party, which quest flags get set — is encoded in the blob, not the engine. The engine itself is small and re-entrant: a single byte runner, a single keyword loop, a single loader. Anything richer than "speak text and accept keywords" is built up by combining the dozen or so control codes the runner recognises.

This spec describes the Talk command's entry path, the on-disk `.TLK` file structure, the in-memory keyword tree, the byte runner's complete dispatch table, the conversation flow including BYE handling and party-name prompts, and the hooks into the rest of the engine (text output, free-text input, the party module, and the quest/conversation flag stores).

## 2. The Talk command

The Talk command is one of the per-letter actions accepted by the town/dwelling/castle/keep mode loop; it is *not* available outdoors or in dungeons (there are no scheduled NPCs to address there) and is not available during combat. When the dispatcher routes the keystroke to the conversation overlay, the entry handler performs five steps before the engine proper takes over:

1. **Direction prompt.** After the `Talk-` echo, the handler runs the shared adjacent-direction prompt (`systems/commands.md` Section 5.4, `systems/input.md` Section 10), the same one Search, Jimmy, Open, Get and Push use. A cardinal direction echoes its word and a line feed, and Talk continues. Space echoes `Pass` and a line feed, so the row reads `Talk-Pass`, and Talk ends there with the ordinary acted outcome: the clock advances exactly as for the bed and mirror aborts of step 4. Escape, letters, diagonals and unshifted top-row digits print nothing and the prompt reads again. This is the only early exit. Talk tests no provisions, party status (asleep, poisoned, dead), combat state or conversation state, so a party whose provision counter is zero talks normally; starvation means only the hourly warning and damage of `systems/time.md` Section 5. Outside town-family scenes the resident dispatcher never reaches this handler and decides by scene alone: on the overworld it prints `Talk-`, runs the same prompt, then prints `Funny, no response!`; in a dungeon-band scene it prints the combined `Talk-Funny, no response!`; combat has its own `T` arm (`systems/commands.md` Section 5.2, the `T` row). None of those arms reads provisions either (static reading). *(Corrected 2026-10-25, issue #300 Q12: executed with provisions at 0, 1 and 250 - identical output, and the provision counter was never read; the claim about unshifted digits is static reading of the prompt.)* This step previously described a resident "can talk now" liveness gate that refused silently when in combat, asleep, starving or already in a conversation; no such gate exists, and that text is retracted (`RETRACTIONS.md` R596).

2. **Player position and the chosen direction.** The handler reads the party's tile coordinates and the direction just chosen at the step 1 prompt, a signed `dx, dy` step. The prompt clears the shared direction vector before setting it, so an earlier movement has no effect. *(Corrected 2026-10-25, issue #300 Q12: executed with a stale East vector left in place; choosing North, West or South targeted that cell.)* This step previously said the direction was the facing written by the most recent movement command; that is retracted (`RETRACTIONS.md` R597).

3. **NPC lookup in the chosen direction.** The target cell is `(player_x + dx, player_y + dy)`. The resident NPC-occupancy structure is consulted to find an NPC whose live tile matches. If no NPC is at that tile, the handler tests whether the tile is a *talk-through* tile — a fixed white-list of counter-height and waist-height furniture. The shipped white-list is the tile ids `0x29`, `0x94..0x9C`, `0xA5`, `0xAE`, `0xBA..0xBB`, `0xBE` and `0xCA..0xCB`; every other tile id is opaque to Talk. If the tile is talk-through, the handler advances `(dx, dy)` once more and queries again. If still no NPC is found, the handler prints a "Nobody's here!" message and returns. Note that the mirror tile `0x9D` sits immediately outside this range, so Talk never reaches past a mirror — it can only resolve *onto* one.

4. **Status-tile gate.** With an NPC located, the handler reads the **live map tile occupying the resolved cell** and compares it against exactly two values:

   | Live map tile | Shipped description of that tile | Result |
   |---|---|---|
   | `0x9D` | a mirror | Print `\nNo response!\n` without quotation marks and return. |
   | `0xAB` | a bed | Print `\n"Zzzzzz..."\n`, including both quotation marks, and return. |

   Here `\n` denotes an explicit line feed. The bed response has five lowercase
   z's after its capital Z and three dots. The earlier transcription that
   omitted its displayed quotation marks is withdrawn (R431). Fresh original
   Talk dispatch and literal checks in `u5-decomp/functions/TALK_OVL/` confirm
   both rows; the author's Paws capture agrees with the bed response.

   Every other value falls through to step 5. The comparison is a single byte test with no ranges: only these two ids divert the command, and neighbouring ids such as the mirror-with-reflection and broken-mirror tiles do not.

   Three points that are easy to get wrong:

   - **The test object is a map tile, not an NPC sprite.** Both ids are furniture ids in the terrain-description domain of `LOOK2.DAT`, and the byte comes from the same live-map tile query that movement and Look use. The gate fires because the NPC's schedule has parked it on a bed cell or a mirror cell, not because the NPC has a distinct sleeping or praying appearance. An implementation that stores a per-NPC "asleep" flag and tests that instead will diverge.
   - **The cell tested is the resolved cell**, which may be the adjacent cell in the chosen direction or, when that cell is a talk-through tile, the cell one step further along the same direction.
   - **Both branches abort before dispatch.** Neither branch enters the conversation engine, uses the NPC's dialogue index, or reaches shop-trigger dispatch, and both return the ordinary zero Talk outcome. This holds in every town, dwelling, castle and keep scene; the gate has no scene-specific behaviour. The resident `T` arm maps that outcome to the normal acted status, so the town loop advances the clock and runs its scheduler pass; an aborted Talk is not a free action. `systems/town-mode.md` and `systems/time.md` own the exact clock accounting.

5. **Dialog-index dispatch.** Each live NPC carries a *dialog index*, expanded from the location's `.NPC` byte into a runtime word when the scene is entered. The handler reads the dialog index for this NPC and hands it to the conversation engine, which uses it as the key for looking up the NPC's blob in the matching `.TLK` file.

   **The guard gate, and where the two refusal lines come from** *(added 2026-09-06, issues #198 and #206; read from the dispatcher and checked live)*. Before the index is used, the dispatcher looks at the behaviour value of the NPC's **current** waypoint - the waypoint it last reached, not the one the hour selects - and at the NPC's sprite:

   - If that waypoint's behaviour is the approach-and-converse mode (`npc-schedules.md` Section 9, value `4`), the dispatcher first **rewrites that waypoint's behaviour to the bounded-wander mode** (value `1`, a persisted schedule edit: the guard stands down for the rest of the period and the edit travels with the save) and then dispatches on the dialog index. An index of zero prints the bare `No response!` line; anything else proceeds.
   - Otherwise, if the NPC's live sprite is the guard sprite, the NPC answers `The guard offers` on one row and `no response!` on the next, unless *both* its current waypoint index is **odd** *and* its dialog index is non-zero, in which case it dispatches normally. The two rows are one stored literal; it is not composed from the NPC's Look description, and nothing else prints it.

     *Corrected 2026-09-12 (issue #262).* This bullet previously gave the escape as "its current waypoint is waypoint 1". The test is on the **parity** of the current waypoint index, not equality with one: an even index always gives the guard refusal and an odd index with a non-zero dialogue index always dispatches. The two readings agree at the waypoint indices `0`, `1` and `2` that ordinary schedules use, and diverge at any higher index. The same parity bit separately gates the shop path in `systems/shops.md` Section 2, which the published text did not describe as waypoint-conditioned at all. See `RETRACTIONS.md` R479.
   - Any other NPC dispatches on its dialog index; index zero prints the bare `No response!`.

   *Decision tree, restated 2026-10-12 (issue #216; executed on the original).* The inputs are the **live** dialogue word of the resolved NPC record, its current waypoint index, that waypoint's behaviour value, and the type of the linked active object. (1) Behaviour `4`: rewrite it to `1`, then a live word of zero prints the bare `No response!` and anything else dispatches. (2) Otherwise, linked object is the guard sprite: an **even** waypoint index prints the guard line; an **odd** index with a nonzero word dispatches; an odd index with a **zero** word also prints the guard line, not the bare one. (3) Otherwise: word zero prints the bare line, anything else dispatches. (4) Dispatch: below `0x80` loads that TLK blob; `0xFD` the cowering line; `0xFE` the begone helper; `0xFF` the Blackthorn regime handler (`systems/blackthorn.md` Section 7a); `0x80..0xFC` the shop gate or the merchant brush-off. **The bare `No response!` is therefore printed only when the live dialogue word is zero, or when no NPC record owns the faced object** (below); a live word of `0xFF` never produces it. The `0xFF` in the shipped file is a byte; the live word is a runtime copy.

   **No-owner Talk.** If no occupied, non-idle NPC record is linked to the faced active object, Talk does not stop with `Nobody's here!`: it runs the dispatcher with an unrelated adjacent record that reads as all zero, so the bare `No response!` is printed for any sprite. The owning record is the lowest-numbered occupied record linked to the faced object with a nonzero type and state; the faced object is the highest-numbered active object at that cell. *(Added 2026-10-16, issue #216.)*

   The bare line comes from the mirror check or a zero live dialogue index
   reached through the dispatcher. A valid reserved index `0xFF` is not treated
   as zero: it enters the regime handler of `systems/blackthorn.md` Section 7a
   from both explicit Talk and automatic conversation contact, subject to the
   gates above. In particular, a guard at an **odd reached waypoint
   index** (waypoint 1 included) with nonzero dialogue can pass even when its
   behavior is no longer 4. The earlier
   assertion that its approach period was the only route is withdrawn (R401).
   The conflicting bare-refusal capture in issue #216 remains unresolved;
   Section 7a records the earlier reproduction method and the stock runtime
   evidence needed to compare the two observations.

   **Shop and automatic-contact entry.** The dispatcher in step 5 is also
   called by the NPC's automatic conversation-contact event, without steps
   1–4. Its behavior-4-to-1 rewrite applies to shopkeepers as well as guards,
   before a shop can open or refuse. Both entry routes require the shopkeeper's
   reached waypoint and current hour-selected waypoint to be 1, followed by
   the horse restriction; `systems/shops.md` Section 2 gives the complete
   predicate, fixed refusal and turn accounting. `systems/npc-schedules.md`
   Section 9.2 gives event production and routing. These facts were established
   by shared-caller and gate traces in `u5-decomp/functions/TALK_OVL/`.

   **The dispatcher's own lines.** Five branches replace the ordinary
   description-and-greeting entry with a stored line, and every one of them
   follows the dispatcher's own leading line feed. None of them prints a
   description, a greeting, a name, or the keyword prompt.

   | Branch | Rows |
   |---|---|
   | Guard sprite, refused by the parity/index test above | `The guard offers` ⏎ `no response!` |
   | Dialogue index zero | `No response!` |
   | The silent-figure index | `"` then `Don't hurt me!` ⏎ `Please go away!` then `"` and a line feed |
   | A shop index whose gate does not pass | `A merchant says:` ⏎ `"Come see me at` ⏎ `my shoppe, when` ⏎ `it's open!"` |
   | The scare index (`0xFE`) | `"Begone,` ⏎ `vermin!"` ⏎ - the double quotes are part of the literal and its own line feed ends the second row - then the whole-party damage pass, then the forced-flight helper (`systems/town-mode.md` Section 14); the ordinary zero outcome |
   | The reserved regime index (`0xFF`), not one of the five | hands off to the regime handler of `systems/blackthorn.md` Section 7a |

   *(Added 2026-10-25, issue #300 Q19.)* The damage pass is the shared one
   of `systems/overworld.md` Section 6.2.4 and the starvation branch of
   `systems/time.md` Section 5: each party slot below the party count whose
   status is not Dead takes its own uniform `1..8`. A `0xFE` Talk is
   therefore an ordinary acted turn with no arrest and no conflict. On
   automatic conversation contact the flight helper receives the contacting
   NPC. **On an explicit typed Talk it does not receive the talked-to NPC's
   number**, and which record, if any, it rewrites there is not established
   (`OPEN-QUESTIONS.md` section 2). The number it gets is caller state that
   neither Talk's entry, the resident `T` arm nor the town loop sets; executed,
   the talked-to NPC was rewritten only when that leftover happened to equal
   its index. Static reading (not executed) suggests the leftover is never a
   valid NPC number: at the first explicit Talk of a session it is a value left
   from program start-up, well above any NPC number, and after any explicit
   `0xFE` Talk it is another out-of-range value left by that brush-off itself.
   If so, an explicit Talk never rewrites the talked-to NPC, and the flight
   helper instead tests an out-of-range record and may write its flight values
   outside the NPC table. The automatic-contact route restores its own number
   and is not affected. Executed on the original dispatcher with
   only the random draw and the per-member damage routine stubbed, so the
   per-member flash and rumble on this route are the shared damage path's
   and were not observed here.

   The merchant brush-off is two stored strings printed back to back, the first
   ending with a space after the comma; `systems/shops.md` Section 2 owns it.
   The silent-figure line is framed by two separately emitted double-quote
   characters. The waypoint behaviour rewrite described above happens **before**
   any of these lines, and applies to shopkeepers as well as guards.

   **The typed Talk command's own three lines never reach the dispatcher** and
   each carries its leading line feed inside the stored string: `Nobody's here!`
   when the reached cell holds no NPC, `"Zzzzzz..."` on the bed tile, and
   `No response!` on the mirror tile - which is a *different* stored string from
   the dispatcher's bare `No response!`, because it begins with its own line
   feed where the dispatcher's does not.

   **What loading a save does to this.** The runtime NPC table, including each NPC's dialog index and current waypoint, sits inside `SAVED.GAM` (`formats/saved-gam.md`), and a save the shipped game writes inside a location restores it, so Talk works after Journey Onward exactly as it did before the save (checked live in Skara Brae). A save written by another program that leaves that region zero makes every NPC in the location answer `No response!` until the location is re-entered from outside - that is a property of the save, not of the game.

The dialog index is a 1-based identifier shared between the `.NPC` and `.TLK` files of the same location class. Index 0 means "no dialogue at all" (the NPC is a non-speaker — a guard, a child too young to talk to, an animal). Index 1 is an ordinary dialogue id like any other: each class file's blob 1 is a fully authored NPC, and one occupied roster slot per class file points at it. Earlier revisions of this spec called index 1 a universal sentinel that no live NPC uses; that is withdrawn (`formats/tlk.md` Section 6).

### 2.1 The reserved "not a real NPC" index

One dialog index value is reserved to mean "this figure has no dialogue file at
all". When the dispatcher sees it, it does not load a `.TLK` blob, does not run
the keyword loop, and does not touch the conversation engine. Instead it calls a
small scene-keyed handler and passes that handler's result straight out as the
conversation's own result, with nothing running afterwards.

The handler is a Blackthorn-regime shakedown, not a service counter. Its three
branches are specified in `systems/blackthorn.md`. What matters at the
conversation layer is the shape of the contract:

- The handler's only durable side effect is on the party's gold. It writes no
  character status byte, no hit points, and no karma, and it calls no healing,
  resting, or curing routine.
- It returns exactly two outcomes, "paid or passed" and "refused". The Talk
  command surfaces that outcome as the conversation result. Paid/passed is the
  ordinary zero outcome; refusal, insufficient gold, a missing Badge aura, or
  a wrong password is the sole positive Talk outcome.
- There is no follow-on path. A reimplementation must not attach healing,
  lodging, resurrection, or any other service to this index — there is nowhere
  for one to hide, because the caller jumps straight to its exit with the
  handler's return value.

The distinction is not "conversation did or did not run." Ordinary NPC
dialogue, shops, canned replies, and no-response paths all use the ordinary
zero Talk outcome. In an explicit town `T` command, the resident dispatcher
converts only the positive guard-demand failure into the town loop's
arrest-cleanup status. The same reserved handler may also be invoked by an
automatic guard-contact event; its positive outcome reaches the same arrest
sequence without a typed Talk command.

Inns, healers, and every other paid service are reached through the ordinary
shop-trigger dialog-index values instead, and are owned by `systems/shops.md`.

## 3. The four `.TLK` files

Conversation data is split across exactly four files, one per location class — `TOWNE.TLK`, `DWELLING.TLK`, `CASTLE.TLK`, `KEEP.TLK`. The class is determined by the current scene byte: it is `(scene_id − 1) >> 3`, mapping scenes `1..8` to towns, `9..16` to dwellings, `17..24` to castles, and `25..32` to keeps. The mapping is fixed; a given NPC's dialog index resolves only against the file matching their location class.

Each `.TLK` file contains a header (a count word followed by a fixed-size index of NPC entries) followed by the variable-size blob data. The file-level layout is:

| Region | Width / count | Meaning |
|--------|---------------|---------|
| NPC count | 2 bytes | Number of NPC entries in this file, and equally the number of blobs. |
| NPC entries | 4 bytes each, `npc_count` entries | One entry per NPC, ordered by ascending id `1..npc_count`. |
| Blob data | Remainder of file | Concatenated NPC blobs containing XOR-obfuscated text and control bytes. |

Each NPC entry is four bytes, **id first**:

| Entry field | Width | Meaning |
|-------------|-------|---------|
| NPC id | 2 bytes | One-based identifier matching `dialog_index`. |
| Blob offset | 2 bytes | Absolute file offset of this NPC's blob. |

The shipped files declare 48 (TOWNE), 15 (DWELLING), 40 (CASTLE), and 32 (KEEP)
entries, one hundred thirty-five blobs in all, and every id from `1` to the
count addresses a real authored NPC. The header occupies `4 × npc_count + 2`
bytes, which is exactly where the first blob starts in each of the four files.

An earlier revision of this spec described the entries as `(blob_offset, npc_id)`
pairs behind a leading degenerate pair `(npc_count, 0x0001)`, with index `1` a
structural sentinel that "no live NPC uses" and a compatibility edge aliasing
index `1` to the first real blob. All of that is withdrawn: it left two header
bytes and one whole blob per file unaccounted for, and it bound every id to the
previous id's blob. `formats/tlk.md` Section 6 owns the corrected contract.

When the engine asks to talk to dialog index `D`, the loader reads the first 512 bytes of the file (enough to cover any class's header) into a working buffer, walks the entries linearly comparing id words, and on the first match takes the word immediately after the matched id as the file offset of the NPC's blob. The loader issues a second fixed-window read of 1024 bytes at that offset into the same buffer, overwriting the header with the blob. From the engine's perspective, the buffer now begins with the NPC's keyword tree.

The loader does not compute a runtime blob length from the next header entry.
For most shipped entries the fixed window contains the whole nominal blob span
plus some following file data that is never reached because the current blob's
own terminators stop the scans. No shipped blob is long enough for the window to
truncate it — the largest nominal span in any of the four files is 704 bytes —
so the 1024-byte cap is a compatibility contract rather than an observable
truncation. A binary-compatible implementation should still preserve the
fixed-window behavior rather than reading the full header span.

## 4. NPC blob structure

A single NPC's blob is a stream of obfuscated bytes representing alternating text spans and control codes. It begins with five fixed entries — the *mandatory leading entries* — followed by zero or more (keyword, response) pairs.

The five leading entries are, in order:

1. **Name.** The NPC's display name, e.g. "Jennifer".
2. **Description.** A short prose phrase describing the NPC's appearance, e.g. "a weathered girl".
3. **Greeting.** What the NPC says when first addressed, e.g. "Hello, Avatar".
4. **Job.** What the NPC says in response to the keyword `JOB`. By convention the keyword loop reaches the same entry when the player asks `JOB`.
5. **Bye.** What the NPC says when the player exits the conversation (typed empty input, or the keyword `BYE`).

Each entry is a NUL-terminated stream of post-obfuscation bytes. After the five mandatory entries comes the variable-size keyword body. Each keyword body is a pair: a NUL-terminated keyword string followed by a NUL-terminated response stream. The pairs are found by position alone: counting the five leading entries as records 0-4, keyword k (k = 0, 1, 2, ...) is record 2k+5 and its response is record 2k+6. Nothing in a record marks it as a keyword or a response. The pairs continue only up to the blob's first label declaration (Section 7.7); the labelled blocks that follow are never part of the ordinary keyword list, and no keyword inside or after them is ever tested at the top-level prompt (executed, on a synthetic blob and on shipped NPCs). Because pairing is positional, an odd number of records between the five leading entries and the first declaration shifts every pair after the extra record by one; one shipped NPC has this shape (Section 7.7). Counted this way, shipped NPCs have between zero and twenty-four ordinary keyword/response pairs, and six have none at all (among them `DWELLING.TLK` id 10, `KEEP.TLK` id 10 and `CASTLE.TLK` ids 8, 10 and 11). *(Corrected 2026-10-19, issue #299 Q22: this said the pairs continue until the end of the blob; retracted, R582.)*

Both keywords and response text use a single obfuscation scheme: every printable text byte has the high bit (`0x80`) set on disk. A literal `'A'` (`0x41`) is stored as `0xC1`. The engine strips bit 7 when comparing keywords and when rendering text. This is *not* an encryption — it's a simple bit flag — but it has the side effect that the on-disk text is not casually readable as ASCII strings. The same flag distinguishes text bytes (high bit set) from control codes and dictionary indices (high bit clear), which is how the byte runner classifies each byte without any escape sequences.

Control codes (Section 7) appear inline in any text stream. They are *not* required to live at the start of an entry — they can punctuate text mid-line. A response stream is therefore a possibly long mix of obfuscated text bytes, common-word indices, and control codes, terminated by an end-of-response sentinel.

## 5. Keyword scan model

Keyword input uses two distinct scans, and they should not be collapsed into one data structure.

First, the engine checks a fixed reserved-keyword table that lives outside the `.TLK` files. That table has thirty-four entries. Five are functional conversation words: `NAME`, `JOB`, `WORK`, `BYE`, and `THANK`. The remaining entries are profanity/default rebuke words that route to a chastisement and bounded pause loop. This table is engine-owned vocabulary, not a per-NPC pointer table.

The fixed reserved table is:

| Index | Keyword | Behavior |
|---:|---|---|
| 0 | `NAME` | Run the Name entry preceded by `My name is ` (one trailing space), inside the response quote framing described in Section 6. |
| 1 | `JOB` | Run the Job entry. |
| 2 | `WORK` | Alias for `JOB`. |
| 3 | `BYE` | Run the Bye entry and exit the conversation. |
| 4 | `THANK` | Alias for `BYE`. |
| 5 | `FUCK` | Rebuke branch. |
| 6 | `SHIT` | Rebuke branch. |
| 7 | `DAMN` | Rebuke branch. |
| 8 | `DICK` | Rebuke branch. |
| 9 | `PRICK` | Rebuke branch. |
| 10 | `PUSSY` | Rebuke branch. |
| 11 | `CUNT` | Rebuke branch. |
| 12 | `ASS` | Rebuke branch. |
| 13 | `BUTT` | Rebuke branch. |
| 14 | `BOOGER` | Rebuke branch. |
| 15 | `PISS` | Rebuke branch. |
| 16 | `JACK OFF` | Rebuke branch. |
| 17 | `MASTURBATE` | Rebuke branch. |
| 18 | `SUCK` | Rebuke branch. |
| 19 | `FART` | Rebuke branch. |
| 20 | `TITS` | Rebuke branch. |
| 21 | `BOOB` | Rebuke branch. |
| 22 | `MELONS` | Rebuke branch. |
| 23 | `BLOW` | Rebuke branch. |
| 24 | `PENIS` | Rebuke branch. |
| 25 | `BREAST` | Rebuke branch. |
| 26 | `CLIT` | Rebuke branch. |
| 27 | `BALLS` | Rebuke branch. |
| 28 | `SCROTUM` | Rebuke branch. |
| 29 | `NUTS` | Rebuke branch. |
| 30 | `BULLSHIT` | Rebuke branch. |
| 31 | `CUM` | Rebuke branch. |
| 32 | `CROTCH` | Rebuke branch. |
| 33 | `MOTHERFUCKER` | Rebuke branch. |

Second, if the fixed table does not handle the input, the engine scans the ordinary keyword/response pairs in the loaded NPC blob. The blob still has five mandatory leading entries (Name, Description, Greeting, Job, Bye), and those entries are reached by fixed ordinal paths when the conversation envelope needs them. Ordinary player keywords begin after those five entries. On match, the engine keeps the matched ordinary keyword index and seeks to that keyword's paired response stream.

`JOIN` and `WHO ART THOU` are not engine-reserved keywords. If an NPC supports a visible `JOIN` topic, it is an ordinary keyword in that NPC's blob. The recruitment and "ask who" mechanics are then driven by control bytes embedded in the response stream.

## 6. The keyword input loop

After the loader has read the NPC blob and the greeting has been emitted, control passes to the keyword input loop. Each iteration:

1. **Print the prompt.** The string `Your interest?\n:` is printed into the active text window, leaving the cursor on the next line ready to accept input.

2. **Read a line of free-text input.** The free-text input pipeline (described in `input.md`) accepts up to fifteen characters with backspace handling. The line is stored uppercased in a small buffer. Function keys, direction codes, and other non-printable bytes are silently discarded; Enter terminates the line.

3. **Empty-input shortcut.** If the player pressed Enter on an empty line, the engine prints `BYE\n\n`, runs the NPC's `Bye` entry through the byte runner, and returns to the caller. This is the most common way conversations end. **The shortcut belongs to this prompt alone.** The ASK-WHO name prompt of Section 7.6 applies its own empty test to the same shared buffer and never reaches the farewell path: an empty line there prints the dismissive acknowledgement and returns to the stream, exactly as a non-matching word does. *(Settled 2026-09-12, issue #266.)*

4. **Reserved-keyword scan.** The engine compares the input against the fixed thirty-four-entry reserved table. The match uses the same normalized string comparison style as ordinary keyword matching: typed input is uppercased, the table is walked in order, and each reserved word is accepted by the same rule as step 5 - its first occurrence in the line must start the line or follow a literal space, and nothing after it is checked. So `JOBS` runs the Job entry and `WELL BYE` takes the BYE path (executed on the original). *(Corrected 2026-10-18, issue #299 Q20: this step said a reserved word must be followed by end of input or a space; retracted, R578.)* `NAME` runs the Name entry with the fixed `My name is ` prefix and framing specified below, `JOB` and `WORK` run the fixed Job entry, `BYE` and `THANK` run the fixed Bye path, and the profanity/default entries print the rebuke path and run the bounded pause loop described below. A typed `BYE` or `THANK` runs the Bye entry **without** printing the `BYE` line; only the empty-line shortcut of step 3 prints it *(added 2026-10-18, issue #299 Q20; executed)*.

5. **Ordinary keyword scan.** If the reserved table does not handle the input, the engine walks the NPC blob's variable keyword/response pairs after the five mandatory leading entries. Each keyword, in blob order, is looked for in the typed line with the shared text matcher of `systems/commands.md` Section 11.3, which strips bit 7 from both sides (so obfuscated keyword bytes match plain ASCII), folds both sides to upper case and keeps its restart rule. The **first** occurrence the matcher finds is accepted if it starts the line or immediately follows a literal space. Nothing after the occurrence is checked. If that first occurrence is mid-word the keyword fails, even when a clean occurrence comes later in the line. The first keyword accepted wins. This is the same rule as the ASK-WHO name match of Section 7.6. Executed examples: `JOINED` and `I WANT TO JOIN` match `join`; `REJOIN` and `JO IN` do not. *(Corrected 2026-10-18, issue #299 Q20: this step said the compare was space-boundary with an end check and "no substring search"; retracted, R577.)* The walk is by record position (Section 4) and ends at the blob's first label declaration. When the ordinary records pair up evenly, the record that begins at the declaration is tested once as a keyword, but it begins with a value no typed line can contain, so it never matches; an implementation may stop at the declaration without loss. A keyword that lives inside a labelled block, such as a scoped `y`, gets `I cannot help thee with that.` at this prompt (executed). If an NPC has an odd number of records after its five leading entries and before its first declaration, every pair after the extra record is shifted by one; the shipped case is `TOWNE.TLK` id 23, described in Section 7.7. *(Added 2026-10-19, issue #299 Q22.)*

6. **Match found.** When an ordinary keyword matches, the engine runs the selected response stream through the byte runner. After the response finishes, the loop returns to step 1 to prompt for the next keyword. *(Clarified 2026-10-17, issue #299 Q1.)* "Finishes" means the response reaches its NUL. If it reports a stop, the loop returns that stop at once and the conversation ends without a `BYE` (Section 7.2).

7. **No match.** When both scans complete without a match, the engine prints `I cannot help thee with that.\n\n` and returns to step 1.

The match has a start boundary and no end boundary. A typed `grandpa` matches a `gran` keyword, so when an NPC has both `gran` and `grandpa`, which of them answers is decided by their order in the blob: the earlier one wins for any line it matches. *(Corrected 2026-10-18, issue #299 Q20: this paragraph said `grandpa` does not match `gran`; retracted, R577.)* The keyword's actual length is whatever the NUL terminator says it is; the four-character "U4 convention" is a player-side discipline, not an engine constraint. The fifteen-character input limit on the typed side caps the longest entered phrase.

**NAME response prefix and framing.** Whenever the ordinary reserved `NAME`
response runs, its fixed words are exactly `My name is `, including one
trailing space. The fixed output also supplies the opening double quote
immediately before `My`; it contains no closing quote or newline. The Name
entry then runs through the ordinary dialogue byte runner. On normal completion
at the entry terminator, the response handler requests a closing double quote
and two newline operations, using the shared conversation output rules. If the
Name stream instead signals a stop, that normal closing-quote/newline suffix is
skipped. Any output or control actions authored inside the Name entry retain
their usual effects.

The two newline operations preceding a nonempty keyword's response belong to
the input loop after the answer is read and before keyword dispatch. They are
not part of the NAME prefix. For an ordinary plain-text Name entry, the visible
response is therefore the quoted words `My name is ` followed by the NPC's
name, with shared response spacing before and after it. Line wrapping belongs
to the active text window, not to a newline embedded between the prefix and name.

There is no NPC, location, acquaintance, clock or random variation in this
prefix on the ordinary reserved NAME path. The scoped sub-prompts in Section
7.7 suppress the entire global NAME response while they handle their local
keywords; they do not run the ordinary Name entry without its prefix. The
opening self-introduction in Section 9 is a separate path and uses `I am
called ` instead, also with one trailing space and an opening quote.

Source provenance: fresh private analysis in `u5-decomp/notes/` and
`u5-decomp/functions/TALK_OVL/`, with 520 original-code dispatcher, input-loop
and opener cases. Response-body/rendering hooks were controlled; these checks
establish output boundaries and state gates rather than pixel wrapping.

The fixed-table profanity/default branch is presentation-confirmed but no
longer public as a confirmed karma mutator. Matching one of those fixed words
prints `With language like that, how did you become an Avatar?`, emits the same
quote/newline framing used by other reserved responses, then runs a bounded
pause loop. The loop attempts at most twenty-eight redraw/pause/status passes;
an early key-abort path runs the same final pause-screen helper and exits the
loop early. In either case the branch returns to the same keyword prompt rather
than ending the conversation. The branch does not write a confirmed karma,
curse, conversation-progress, toll, or quest-state field. If profanity changes
karma in another cleanup path, that producer remains untraced.

## 7. The byte runner

Every byte of every text stream — the five mandatory leading entries, every keyword response, the bodies of branched IF/ELSE arms, the bodies of GOTO targets — is fed through a single dispatcher. The dispatcher classifies the byte by value range and either emits printable output, runs a control action, or stops the current stream.

The dispatcher's classification, in order:

- **Bytes `0x01..0x80`.** These are *common-word dictionary tokens*. The byte is itself the index into the shared one-hundred-twenty-eight-entry dictionary published in `catalogs/common-word-dictionary.md`, and the word is expanded inline into the output. The classifier is a single comparison — anything below `0x81` takes this path — so the top token, `0x80`, has its high bit set and is still a dictionary token. See Section 8.
- **Bytes `0x91..0x9F`.** These are GOTO-LABEL codes; they participate in label dispatch. See Section 7.7.
- **Byte `0x90`.** This is the structural LABEL-RECORD marker used by scanners,
  but the ordinary byte runner has no control case for it. If sequential
  execution reaches it, it takes the printable fall-through described in
  Section 7.7.
- **Bytes `0xA0..0xFD` (high bit set, in the printable range).** These bytes enter the printable text path. The word-buffer flush strips the high bit before glyph output; whether the queued byte still carries that bit is what the `0x8E` toggle controls, and it decides both which font the character renders in and whether it acts as a word-buffer break marker. See Section 7.1.
- **Bytes `0x81..0x8F`.** Engine control codes. The dispatch table is in
  Sections 7.2–7.6.

  *Corrected:* an earlier revision gave this band as `0x80..0x9F`, which
  contradicted the dictionary-token bullet above in the same list. **`0x80`
  is a dictionary token, not a control code** — the classifier is a single
  comparison and anything below `0x81` takes the token path. The control band
  begins at `0x81`.

  Confirmed from the shipped conversation files, independently of any code
  reading: `0x80` occurs thirteen times across the four files, always between
  ordinary text, and each occurrence reads as English only if it expands to a
  word — for example "I ‹token› hard", "We ‹token› long days", and
  "I compiled reference ‹token› known as ...". The arithmetic agrees: a
  one-hundred-twenty-eight-entry dictionary needs one hundred twenty-eight
  token values, and `0x01..0x7F` supplies only one hundred twenty-seven,
  leaving the final entry unreachable by any token.

  **Do not derive either band's boundary from the other.** They are adjacent
  as a fact about the original, not as a rule either enforces on the other.
  Defining one as "one past" the other propagates an error in the first
  silently into the second, in a different subsystem, and removes the only
  independent check that could have caught it.

  *Corrected:* the earlier upper bound `0x9F` also classified `0x90` as an
  engine control code. **That classification is retracted.** `0x90` is
  structural to the label scanners but is an accidental printable fall-through
  if the ordinary runner receives it.
- **Byte `0xFE`.** A multi-byte command introducer that behaves as an alias for `0x8C` (IF/ELSE).
- **Byte `0xFF`.** End-of-response. The byte runner flushes any pending word and opens a fresh keyword prompt nested where the stream stands; leaving that prompt ends the conversation. See Section 7.2. *(Corrected 2026-10-17, issue #299 Q1: this bullet said `0xFF` signals the existing keyword loop to start a new iteration; that is retracted, R561.)*

The byte runner has a small amount of per-conversation state: a "multi-byte command in progress" flag (set by `0x85`, `0x86`, `0x8C`, and `0xFE`), an argument-collection buffer for the multi-byte arguments, a print mask that may be toggled mid-stream, a record of the last printable byte emitted (used to suppress a doubled double-quote), and a pending-space flag armed by successful dictionary expansions. All of this state is reset at the start of each conversation.

### 7.1. Printable text emission

Bytes that classify as printable text (`0xA0..0xFD` with bit 7 stripped) are passed through a small word-boundary buffer and on to the text-output system's wrap-aware string printer. The buffer accumulates characters until it sees a soft break (a space byte) or a forced flush (a control code that performs one), at which point it emits the accumulated word.

The intermediate buffer exists for two reasons. First, the output respects the active text window's word-wrap rules — long sentences wrap at word boundaries rather than mid-word, even though the byte runner emits one byte at a time. Second, dictionary expansions (Section 8) need to merge with surrounding text *as a single word*; without the buffer, "the" expanded between two letters would be three separate writes that the wrap engine could not coalesce.

A pending-space flag is armed after a *successful* dictionary expansion — never by an empty entry — and it forces a single space to precede the next printable text byte, after which it is cleared. Only the printable-text path reads and clears it; a following dictionary token neither consumes nor clears it, which is why adjacent tokens produce exactly one space between words. Section 8 gives the full emission order.

The print mask is a one-byte output-mode flag that selects which of two fonts a
queued character renders in, and as a side effect whether the word buffer breaks
inside a run. In its default state it preserves the high bit on queued printable
bytes; at flush time a queued byte whose high bit is set renders in the ordinary
font, and the encoded space and literal-newline values still match the buffer's
soft-break and forced-break sentinels. The `0x8E` toggle flips the mask's high
bit. While the mask is flipped, printable bytes are queued without their high
bit, and at flush time such bytes render in the **alternate (runic) font**;
because the queued values no longer match the space and newline sentinels, the
run is also never split at its internal spaces. Shipped dialogue uses matched
`0x8E` pairs around mantras and Words of Power, which the original displays in
runic script.

### 7.2. Player-name and stream-control codes

| Code  | Mnemonic           | Effect                                                                                                                          |
|-------|--------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x81  | PRINT-AVATAR-NAME  | Emit the player's saved name (the name chosen during character creation) into the output stream. Used in greetings like "Hail, ${name}!". |
| 0x82  | END-STREAM         | Stop the current stream and report a **stop** to whatever ran it, without flushing the pending word. Every caller treats a stop as the end of the whole conversation (see the paragraph below). In shipped content it is always the last byte of its record and never appears in a Name, Description, Greeting or Job entry. *(Corrected 2026-10-17, issue #299 Q1: this row said `0x82` terminates the leading entries "without ending the whole conversation"; that is retracted, R560.)* |

`0x81` interpolates the avatar's name as if it were a literal text run, including word-boundary handling. **It occurs sixty times across the four shipped
dialogue files** - sixteen, thirty-five, seven and two - and always in a vocative
position: after a comma in a greeting, or after an address like "again,". An
implementation that fails to dispatch it renders those sixty lines with the name
simply missing ("Greetings, , nice"), which is visible to the player but
produces no error, no crash and no failing assertion unless a test compares
rendered output against a shipped blob. That count is a usable regression
target: a correct implementation substitutes a name sixty times over a full
sweep of the shipped dialogue.

**Stops, `0x82` and `0xFF`** *(corrected 2026-10-17, issue #299 Q1)*. A
stream ends in one of two ways: it runs to its NUL, or the byte runner reports
a stop. The level that ran the stream decides what a stop means, and every
level of the conversation treats it the same way: the conversation is over.

- **`0x82` is the plain stop.** It does not flush the pending word first.
  - On the opener path (the Description, the Greeting and the
    self-introduction's Name run of Section 9) a stop makes the opener return
    at once. No keyword prompt, `BYE` or Bye entry follows. Only the final
    cleanup of Section 10 runs.
  - In a keyword answer or a scoped-prompt answer (Section 7.7), a stop ends
    the conversation with no `BYE` and no Bye entry. For example, if a scoped
    yes/no question's "no" answer ends in `0x82`, answering "no" puts the
    player straight back in the command loop.
  - A stopped reserved `NAME` or `JOB` response has the same effect (static
    reading only).
  - Inside the Bye entry, a stop only skips the closing quote and the two row
    breaks (static reading only).
- **`0xFF` is not a stop.** It flushes the pending word, then opens a fresh
  keyword prompt (Section 6) right where the stream stands, nested inside it.
  - Nothing is printed between the flush and `Your interest?`. The closing
    quote and the two row breaks that normally come before the prompt are
    added only when a response ends at its NUL, so a stream ending in `0xFF`
    must carry its own. Shipped streams do.
  - When the player leaves the nested prompt, that prompt runs the Bye entry
    (printing the `BYE` line first only when the player left with an empty
    line, Section 6 step 3), then reports a stop. Every outer level passes the
    stop up and does nothing else, so a conversation prints `BYE` at most once
    however deep the nesting goes. *(Corrected 2026-10-18, issue #299 Q20:
    this bullet said leaving always prints `BYE`; a typed `BYE` or `THANK`
    does not; retracted, R579.)*
  - This is the same stop propagation that the unaffordable-payment prompt
    already follows (Section 7.6, "On an unaffordable payment").
- **A response that ends at its NUL** goes back to the prompt that ran it,
  with the closing quote and two row breaks.
- **An IF-ELSE that passes with the reserved argument `0xFF`** also opens a
  fresh nested keyword prompt, with one difference: it does **not** flush the
  pending word first (static reading only; no executed probe took this path).
  All fourteen shipped uses come right after a row break (thirteen) or a key
  wait (one), so no word is pending and shipped play shows no difference.

*(The earlier text said `0x82` is read at the end of a leading entry that runs
as a unit and that `0xFF` "returns control to the keyword input loop"; both
are retracted, R560 and R561.)*

Why it matters: an implementation that treats `0xFF` as "return to the
existing prompt" looks the same in most of play, because a prompt opens either
way. On the opener path it goes wrong. It runs the rest of the opener (the
blank rows, the acquaintance test, the reseed and coin flip, the greeting),
then opens a second prompt, which prints a second `BYE` when it ends.

Shipped census:
- Seven Descriptions, two Name entries and one Job entry contain the `0xFF`
  code.
- Thirty-three Descriptions contain a path that can stop or nest: a GOTO, the
  `0xFF` code, or a label byte that is an IF-ELSE operand.
- `0x82` occurs 93 times, always as the last byte of its record. Eighty-six of
  those come right after a line break, so shipped content never loses a
  pending word to it.
- Among the leading entries, `0x82` appears only in four Bye entries. Every
  other occurrence ends a labelled-block head or a scoped answer.

Source provenance: private analysis in `u5-decomp/notes/`. The opener, the
label handler, the keyword loop and the byte runner's return values were read
statically. The original conversation code was then executed under emulation
on the shipped blobs: a wizard with the party unknown and known, a dwelling
rat, an ordinary control NPC, a scoped answer ending in `0x82`, and a
synthetic greeting with `0x82` appended. The census was read from the four
shipped `.TLK` files.

### 7.3. Pause and key-wait codes

| Code  | Mnemonic     | Effect                                                                                                                          |
|-------|--------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x83  | PAUSE        | A **timed** pause of up to 28 passes. Each pass redraws the world view and polls the keyboard **without blocking**: a waiting key is consumed and ends the pause at once; otherwise the pass waits one BIOS tick (subject to the shared one-tick slow-machine shortcut of `timing.md`) and the next begins; after the 28th pass the pause ends by itself, key or no key. The keyboard type-ahead buffer is emptied on either exit. No party-panel work is done. The pause never terminates the stream and has no cancel key. *(Corrected 2026-10-12, issue #284; `RETRACTIONS.md` R520.)* |
| 0x8F  | WAIT-KEY     | Block for exactly one command keystroke (any key; its value is discarded); a key already waiting in the type-ahead buffer satisfies it at once. No world or panel redraw. The stream then continues. |

Every response stream - descriptions, greetings, keyword answers, label-scoped sub-answers and ask-sub-prompt continuations - goes through the same byte runner, so both codes behave identically on every path; an implementation must not block indefinitely on `0x83`, because the timeout is part of the contract. Example (a dwelling rat's greeting): the description line, `"Squeek..."`, a PAUSE, then the `0x88` ask-who prompt - with no key sent the prompt appears by itself after about two seconds at a fixed 3000-cycle emulator setting, and a key ends the pause at once and is consumed by it rather than typed into the prompt. Neither code ever stops a response.

Both codes are used to chunk long responses into reader-friendly pages. The conventional use is to insert one `0x8F` after every screen-full of text, and one `0x83` after a more substantial transition (such as just before announcing a quest reward).

### 7.4. Newline and moral-standing codes

| Code  | Mnemonic           | Effect                                                                                                                          |
|-------|--------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x89  | STANDING-UP        | Raise the shared moral-standing selector by one through the ordinary capped-add writer, clamped at ninety-nine. Emits no text and does not touch the word buffer. |
| 0x8A  | STANDING-DOWN      | Lower the shared moral-standing selector by one through the ordinary capped-subtract writer, floored at zero. Emits no text and does not touch the word buffer. |
| 0x8D  | LITERAL-NEWLINE    | Force-emit a literal newline through the text-output system. Used to end a line when no natural break would fall there. |

`0x89` and `0x8A` are the byte runner's only direct writers of the shared
moral-standing selector; `systems/karma.md` section 4 lists them alongside the
other traced standing writers. Scripts stack them to move standing by more than
one — a run of five consecutive `0x89` bytes is a `+5` reward.

How shipped content uses them is worth stating, because neither code sits on a
path every conversation takes:

- Both shipped `0x89` runs are five bytes long and both sit on the **bonus arm
  of the introduce-yourself branch** described later in this section, so each is
  reachable only until the speaking NPC's branch-flag bit is set — once per NPC
  per savegame. Neither is a per-visit or per-payment reward. In one of the two
  the bonus arm is a duplicate of a gold-payment record: the plain arm has the
  payment code and no standing bytes, the bonus arm has the payment code
  followed by the five raise bytes.
- All eight shipped `0x8A` bytes are reaction records. Five head the "no" arm of
  a scoped prompt that asks the party for something (including two gold
  requests), two head `"y"` answer records where "yes" is the boastful answer to
  a virtue question, and one follows the `0x8B` alarm code inside a
  caught-stealing line.

The practical rule for an implementation: standing movement from dialogue is a
property of *which record ran*, not of which keyword was typed or which
transaction succeeded. Reproduce the label transfers, the branch-flag test, and
the scoped prompt's default arm exactly, and the standing deltas follow.
Declining a gold request can cost standing even though paying it never grants
any by itself.

Earlier revisions of this spec described `0x8A` as a newline that also flushed
the party panel, and omitted `0x89` entirely. That was a misreading. The
literal-newline code is `0x8D` and only `0x8D`; the value `0x8A` acquires its
newline meaning only *inside* the word buffer, because the printable-text path
rewrites a `0x8D` to `0x8A` after control-code dispatch has already been passed.

### 7.5. Print-mask and alarm codes

| Code  | Mnemonic        | Effect                                                                                                                          |
|-------|-----------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x8B  | ALARM           | Run the town alarm sweep of `systems/town-mode.md` Section 14: forced pursuit for every occupied guard, lich/death-mage and Shadowlord slot, and one fair inclusive `0..255` draw for every other occupied slot, below 128 calling the forced-flight rewrite. Every shipped use sits at a beat where the speaker calls the guards or turns on the party; in two records the code comes just before that line. *(Corrected 2026-10-16, issue #298 Q14.)* |
| 0x8E  | ALTERNATE-FONT  | Toggle the print mask's high bit, switching queued printable bytes between the ordinary font and the alternate (runic) font and, as a side effect, suppressing word-buffer breaks inside the run. Used in matched pairs around mantras and Words of Power. |

`0x8B` does not affect the stream; its only effects are the alarm sweep's persisted schedule rewrites and its random draws. The sweep takes no arguments, prints nothing, reseeds nothing and leaves the text stream alone. The speaking NPC is in the roster too, so its own line can rewrite it: a guard speaker then pursues, and another speaker may answer the next Talk with the cowering line. No curse or per-character state is involved. Source provenance: derived from private analysis in `u5-decomp/notes/` - the conversation code's call was read through the resident overlay thunk into the town overlay's alarm sweep, whose own analysis independently lists conversation as a caller - plus a scan of the shipped `.TLK` files. In the shipped dialogue the code occurs 14 times in 9 NPC records across the castle, town and keep conversation files, and none in the dwelling file; none of those records belongs to a cursed-item NPC. Earlier revisions called `0x8B` a curse check that ticked per-character counters; it is the town alarm sweep, and that reading is retracted (R531). *(Added 2026-10-16, issue #298 Q14.)* `0x8E` is the only code that mutates the byte runner's print-mask state, and is used in matched pairs (one to enter the alternate font, one to leave it). Every occurrence in shipped dialogue wraps a mantra or a Word of Power.

### 7.6. Branching, recruitment, and transactional codes

These codes are the most semantically rich. Several of them introduce a *multi-byte command*: the introducer code is followed by one or more argument bytes that are not interpreted as ordinary stream bytes but are collected into an argument buffer and consumed by the introducer's handler.

| Code  | Mnemonic        | Argument bytes following | Effect                                                                                                                          |
|-------|-----------------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x84  | RECRUIT-SPEAKER | none                    | Recruit the speaking NPC into the active party. **There is no free-text prompt and no line input; on the party-full path one keystroke is consumed (the `0x8F` WAIT-KEY wait) before the refusal.** *(Corrected 2026-10-29, issue #311 Q2: this row said "There is no player prompt and no input read", which the full-party key wait contradicts; that wording is retracted, `RETRACTIONS.md` R655.)* The engine takes the speaker's *own* name from the Name entry of the loaded blob, and matches its opening characters — case-insensitively, with bit 7 stripped — against the reserve portion of the sixteen-slot character roster, scanned from the last slot downwards. On a match the matched roster record is swapped into the active-party insertion slot, that record's inn-lodging marker is cleared, and the party-size byte is incremented; the engine then removes the NPC from the live scene. If the party is already at the six-member cap the engine prints nothing, first waits for one keystroke through the same single-keystroke wait `0x8F` WAIT-KEY uses (any key, value discarded, world ticks as for WAIT-KEY), then prints the two-part refusal and recruits nobody. *(Added 2026-10-29, issue #311 Q2.)* In this row spaces are written literally, not as underscores: the first part is `"Thou hast no room for me in thy party! ` (an opening double quote, the sentence and one trailing space, no line feed), and the second follows at once as `Seek me again if one of thy members doth leave`, a hard line feed, then `thee.` (no closing quote and no trailing line feed). Both are fixed engine strings, not `.TLK` records, and go through the ordinary wrapping printer. The closing `"` and two line feeds come from the ordinary record-end framing when the stream reaches its NUL; because the shipped response text before `0x84` ends in a closing quote and two line feeds (Toshi's answer, for example), the refusal appears as its own quoted paragraph ending `thee."` and a blank line. The text was read from the shipped data file; the key wait, the print order and the no-stop return are static reading only (the emulation run, party of six, `JOIN`, `Y`, stubbed the key routine and the line reader, so it confirms the on-screen framing and the return to `Your interest?` but not the wait); wrapping in the sixteen-column window is inferred, not observed. If no reserve record matches the speaker's name the engine prints its no-match diagnostic. This is the whole of the JOIN mechanism: the visible `JOIN` topic is an ordinary per-NPC keyword whose response stream emits this code. *(Added 2026-10-18, issue #299 Q20; executed.)* A successful recruit reports a stop: the conversation ends at once with no `BYE` and no Bye entry. The party-full refusal does **not** stop; the stream runs on to its NUL, and a scoped answer then falls back to the top-level `Your interest?` prompt (Section 7.7). The no-match diagnostic stops. Where each shipped companion's recruit sits is listed in Section 7.7.1. |
| 0x85  | GOLD-PAYMENT    | three                   | Collect three argument bytes, mask each to seven bits, interpret them as ASCII decimal digits, and run the gold-payment routine against that three-digit amount. Used for tolls, bribes, and donations. |
| 0x86  | ACTION-DISPATCH | one                     | Collect one argument byte and mask it to seven bits. Letters `A..K` dispatch through one global fixed-slot action table; small values below the letter range set generic one-conversation signal flags. |
| 0x87  | KEYWORD-ALIAS   | none                    | Save the current stream position; skip forward past the remainder of the current record, past any run of terminators, and past the whole record that follows; run the record after that as a nested stream. If the nested stream signals stop, the outer stream stops too; otherwise the saved position is restored and the outer stream continues where it left off. No keyword matching, no player input, no flag write. |
| 0x88  | ASK-WHO         | none                    | Prompt the player for a name and read a typed line. Every visible byte of the exchange is the engine's own stored text; the code consumes no text from the stream. In order: an opening double quote the handler emits itself, the question `What is thy name?` with its own closing quote, a blank row, `You respond-`, and a `:` row that the typed answer echoes onto. On a match against a roster slot within the current party count, **set the active scene's branch-flag bit for the NPC currently speaking** and print the affirmative acknowledgement; on empty input, and again on a completed scan that matched nothing, print the dismissive one. Section 7.6 "What ASK-WHO prints" gives both acknowledgements, their leading feeds, their missing closing quote, and which quotes the stream supplies. This is the in-stream setter for the bank that `0x8C` tests. *(Corrected 2026-09-12, issue #266: the earlier "four-row literal" count, the claim that "the stream around it carries only the closing and opening quotes", and the qualifier "live party member" are withdrawn - R486 and R487.)* |
| 0x8C  | IF-ELSE         | one                     | Collect one argument byte, which is the **branch target label**, then test the active scene's branch-flag bit for the NPC currently speaking. If the bit is clear, fall through in-stream with the byte after the argument. If it is set, transfer to the labelled record named by the argument — or, for the reserved argument `0xFF`, open a fresh keyword prompt nested at that point without flushing the pending word; leaving that prompt ends the conversation (Section 7.2). The tested bit is chosen by the engine, never by the script. *(Corrected 2026-10-17, issue #299 Q1: the `0xFF` arm was given as "end the response and return to the keyword prompt"; retracted, R562.)* |
| 0xFE  | IF-ELSE-ALT     | two                     | Multi-byte alternative branch form. Collects a moral-standing threshold byte and a target-label byte; if the shared moral-standing selector is at or above the threshold, the runner branches to the target label. |

#### The keyword-alias idiom (`0x87`)

In shipped content `0x87` is *always* the entire body of a response record —
across the four dialogue files there are six hundred forty-one occurrences of the
code and every one of them is a one-byte record standing alone between two
keyword records. Because a response record is preceded by its keyword record,
skipping one record forward from a lone `0x87` lands on the next keyword's
response. The observable meaning is therefore "this keyword is an alias for the
next keyword's response". Aliases chain: three keywords in a row whose responses
are each a lone `0x87` all resolve to the fourth keyword's response, because each
nested run re-enters the same handler.

An implementation may therefore treat the alias reading as the whole of the
shipped contract, but it should still implement the skip rule literally — skip
one byte, skip any run of terminators, skip past the next record terminator, run
from there — because that is what decides the outcome for custom content in which
`0x87` is not the last byte of its record.

The historical mnemonic for `0x87` was SET-FLAG, and earlier revisions of this
spec described it as a recursive keyword *scan*. Both are wrong. `0x87` does no
string comparison, reads no player input, consumes no argument byte, and writes
no flag. An implementation that models it as a keyword search will produce the
right answer for the common alias case by accident and the wrong answer whenever
the aliased keyword is not the immediately following record.

#### The introduce-yourself idiom (`0x88` with `0x8C`)

`0x88` and `0x8C` are two halves of one mechanism. The bank they share is the
per-scene branch-flag bank described in `systems/quest-flags.md` section 3: one
thirty-two-bit word per scene, one bit per NPC roster slot in that scene. The
bit index is always supplied by the engine — it is the slot of the NPC currently
being spoken to — so a script can neither choose nor forge it.

- `0x88` **sets** the current NPC's bit, but only after the player types a line
  that names a member occupying a roster slot below the current party count.
  Member status is never consulted.
- `0x8C` **tests** the current NPC's bit and branches on it.

The bank has one further reader outside the script language: the conversation
opener consults the same bit before any script byte runs, to decide whether the
NPC greets the party as an acquaintance or behaves as a stranger. See Section 9
step 3. An implementation must therefore treat the bit as engine-visible state,
not as a private script variable.

The `0x88` match rule is worth stating exactly, because it is looser than the
top-level keyword match. For each party slot below the current party-count byte,
in order, the engine takes the **first four characters** of that member's name
and searches for them as a substring of the typed line, folding case on both
sides, through the shared matcher of `systems/commands.md` Section 11.3, whose
restart rule decides which occurrence is found first. Only the **first** occurrence found is tested. It is accepted at the start
of the line or immediately after a literal space; when it is rejected - a hit in
the middle of a longer word - the engine abandons that member and moves on to the
next slot rather than looking for a later, qualifying occurrence of the same name
in the same line. A typed line whose first hit is mid-word therefore fails even
when a clean hit follows it later in the line. The first accepted hit ends the
scan, sets the bit, and prints the affirmative line. The bit is written at the
moment of the match, in the same bank `0x8C` reads, so an IF-ELSE later in the
same stream - even the next code in the same block head - sees it and
transfers *(added 2026-10-18, issue #299 Q21; executed on the Britain wizard's
stranger block: `AVATAR` and `I AM AVATAR` set the bit and the following
IF-ELSE transferred, while `XAVATAR` and an empty line left it clear and the
IF-ELSE fell through)*. Empty input is its own early
exit and never sets the bit; a line containing only a space is *not* empty, runs
the scan normally, and ends on the no-match arm.

Four characters is a cap, not a requirement. A roster name shorter than four
characters contributes only its own characters, so a two-character name matches
any word beginning with those two letters and a one-character name matches any
word beginning with that letter, while a zero-length name never matches at all.
Party member names are typed by the player at character creation, so short names
are reachable content, not a theoretical edge.

The party-count byte is the only bound on the scan, and it is re-read on every
iteration: a roster record sitting past the count is invisible, and a count of
zero examines no slot at all, so every non-empty line takes the no-match arm.
**Member status is never read.** The walk touches only the name field, so a dead,
poisoned, sleeping or charmed member matches exactly as a healthy one does.
Earlier revisions of this section said the match was against a *live* party
member; that qualifier is withdrawn (R486).

One condition drives both effects, and there is no second path to either. When a
slot matches, the engine sets the speaking NPC's bit and prints the affirmative,
in that order, with no status test, no scene test and no test of the bit's
previous value in between. On empty input and on a completed scan that matched
nothing, no bit is written anywhere. The bit set is the one selected by the
speaking NPC's roster slot, in the current scene's word only, and no other
scene's word changes. Slots zero through thirty-one are reachable; at slot index
thirty-two - the first value out of range, and the only out-of-range value
exercised - the mask built is zero, so nothing is written and nothing wraps onto
bit zero (`systems/quest-flags.md` section 3).

The shipped idiom guards the `0x88` with an IF-ELSE carrying the reserved `0xFF`
argument, usually in the NPC's Name or Greeting entry: if the NPC already knows
the party, the `0x8C 0xFF` opens the keyword prompt right there, nested in the
entry, and leaving it ends the conversation (Section 7.2); if not, execution
falls through to the `0x88` prompt, which asks and then remembers. *(Corrected
2026-10-17, issue #299 Q1: this said the guard "ends the entry and drops
straight to the keyword prompt"; retracted, R562.)* Forty-six of the one hundred thirty-five shipped blobs contain an
ASK-WHO, and forty-three of those also contain an IF-ELSE. Of the forty-eight
ASK-WHO occurrences, **twenty** are immediately preceded by an IF-ELSE and its
argument byte, and in **nine** of those twenty the argument is the reserved
`0xFF` - the guard form described here. No shipped occurrence carries the two
codes in the opposite order. *(The figure of nine was previously published
without saying that it counts only the reserved-argument form; both counts are
now given.)*

A second, richer shipped form uses **two** IF-ELSE tests around one ASK-WHO to
make a one-time reward. Reached by a GOTO from a keyword response, the routing
record is:

1. IF-ELSE with a *plain* target label — if the bit is already set, transfer
   there immediately and the rest of this record never runs;
2. otherwise print a welcome line, optionally PAUSE, then ASK-WHO;
3. IF-ELSE with a *bonus* target label — if the bit is set now (that is, the
   prompt just matched a party member), transfer to the bonus record;
4. otherwise GOTO the plain target label.

The plain and bonus records are near-duplicates of each other; the bonus record
carries whatever the reward is. Both shipped uses put a five-byte run of
raise-standing codes there (`systems/karma.md` section 4). Because a failed
prompt leaves the bit clear, step 4 is a retry path, not a permanent loss: the
bonus stays reachable on a later attempt. Once the prompt succeeds, step 1
routes every later visit to the plain record forever.

"Forever" is exact. The branch-flag bank is part of the durable save image, not
per-visit scratch: nothing clears it on scene exit, mode change, or reload, and
a new game starts with every bit clear. An implementation that rebuilds the bank
on entering a location will make every one-time introduction reward repeatable.
`systems/quest-flags.md` section 3 owns the bank; `formats/saved-gam.md` gives
the band it occupies.

Consequently a clean implementation must not model `0x8C`'s argument as a flag
id, and must not conclude that the bank has no setter. Both errors were present
in earlier public answers and are withdrawn.

#### What ASK-WHO prints (`0x88`)

*(Added 2026-09-12, issue #266. Both acknowledgements are now established byte
for byte; neither was published before.)*

The question, the lead-in and both acknowledgements are stored engine text. One
ASK-WHO produces, in order:

1. **An opening double quote emitted by the handler itself**, before any other
   output, through the same path ordinary stream text takes.
2. **The question**: the words `What is thy name?`, a closing double quote, and
   one line feed. The stored text carries no opening quote of its own - step 1
   supplies it.
3. **The lead-in**: one line feed, the words `You respond-`, a second line feed,
   and a colon.
4. **The player's typed line**, echoed after the colon by the free-text input
   routine as the characters arrive. Nothing is emitted for the Enter that ends
   the line, so the cursor is still on the answer row when the handler resumes.
5. **One acknowledgement**, selected by the arm the handler took:

   | Arm | Stored text |
   |---|---|
   | A roster slot below the party count matched the typed line | two line feeds, an opening double quote, then `A pleasure!` |
   | The typed line was empty | two line feeds, an opening double quote, then `If you say so...` |
   | The scan completed and matched nothing | the same three elements again, from a second stored copy |

Three properties of the acknowledgements are load-bearing, and each is a
property of the stored text rather than of how the rendering happens to look:

- **Each acknowledgement begins with two line feeds of its own.** The first
  closes the answer row the player's typing left the cursor on; the second makes
  the blank row above the acknowledgement. That blank row belongs to the
  acknowledgement, not to anything around it.
- **Neither acknowledgement closes its quote, and neither ends in a line feed.**
  Each stops on its last visible character - the exclamation mark, or the third
  full stop. An implementation that appends a closing quote, or a trailing feed,
  diverges immediately.
- **The blank row that follows is never the acknowledgement's.** It is made by
  whatever the stream carries next, and at the shipped sites that is two line
  feeds at thirty-four of the forty-eight occurrences, one line feed followed by
  a stream-stop code at three, and nothing at all at the eleven where the record
  ends on the ASK-WHO byte itself. An implementation must emit no trailing feed
  of its own and let the stream supply what follows, or it will add a blank row
  at fourteen of the forty-eight sites.

The empty-input arm and the no-match arm print the **same text from two separate
stored copies**: the empty test is an early exit taken before the scan begins,
and the no-match text is reached by falling out of the completed scan. The
rendering is identical, so one dismissive line reproduces both; the two arms
matter because an implementation must not route empty input into the scan, where
a zero party count or a zero-length roster name could behave differently.

**Which quotes are the stream's.** The handler prints every quote the player
sees: the one before the question at step 1, and the one inside whichever
acknowledgement runs at step 5. The stream *does* carry a double quote
immediately after the ASK-WHO byte at thirty-seven of the forty-eight shipped
occurrences, but the player never sees it: the byte runner drops a quote whenever
the last printable byte it recorded was already a quote (Section 7, and the
renderer note in Section 9), and the handler's own opening quote leaves exactly
that state behind, because the stored-text path used for the question and the
acknowledgements does not update that record. Removing the single ASK-WHO byte
from a shipped record makes the swallowed quote appear as a stray lone row -
which is precisely the symptom an implementation shows if it emits neither the
handler's opening quote nor the duplicate-quote guard. Nor does the stream
reliably carry a closing quote *before* the control byte: only eleven of the
forty-eight occurrences are directly preceded by a quote and two line feeds, the
rest being preceded by IF-ELSE guards, pauses, key-waits or label-record headers.
The earlier statement that "the stream around it carries only the closing and
opening quotes" is withdrawn on both halves (R487).

**How many rows this is.** At the message window's width the quoted question
wraps, so the prompt is not the fixed four rows an earlier revision claimed
(R487): it is the opening quote and the first words of the question, then the
remainder of the question with its closing quote, then a blank row, then
`You respond-`, then the colon row. The row split follows the window's own
word-break rule (Section 9) applied to the character sequence above. The
sequence is the contract; the rows are what that rule makes of it.

**Where the census stops.** The counts above walk each shipped blob linearly.
The six occurrences whose control byte has no predecessor inside its own record
were traced back to the records that jump to them, and thirty-one of the
forty-eight were then executed from their record start: every one opened with
the handler's own quote, and every one of those carrying a following quote had
it suppressed. The shipped contract is therefore settled. Custom content that
reached an ASK-WHO from a record ending on a quote would instead have the
handler's own opening quote suppressed; exactly one shipped record of the four
thousand-odd ends on a quote, and nothing jumps from it to an ASK-WHO.

#### The gold-payment envelope (`0x85`)

**Neither outcome of `0x85` transfers control to a label.** Not a fixed label
byte, not a computed one, on either the accepted or the refused arm. An
implementation that pairs `0x85` with paid/refused label bytes is carrying an
invention and should remove it rather than re-tune it.

`0x85` itself reads **no player confirmation**. The three digit characters are
the complete command arguments. The surrounding shipped dialogue puts each
demand in an authored yes-answer record, so reaching the command already means
that the player consented. Refusal means only that the decoded amount is
greater than the party's current gold; an equal balance is affordable.

**On an accepted payment the runner keeps emitting in place.** It debits the
party's gold, refreshes the status panel, reports "continue" to the byte runner,
and the response run fetches the byte immediately after the third digit, from the
same record. The success line is ordinary prose sitting right there in the
stream - which is why a label transfer is not merely absent but impossible: a
fixed paid-label would leave every shipped success line unreachable.

This is confirmed from the shipped dialogue files independently of any code
reading. Across all four files there are **thirteen gold demands in nine
conversation blobs**, and in **every one** the byte following the third digit is
ordinary text, an item-grant introducer, or a raise-standing byte - never a label
declaration, never a label byte, never a record terminator. In all thirteen the
demand also heads a *yes*-answer record, which is the shape that makes an outcome
label impossible.

**An accepted payment can also raise moral standing**, which the earlier wording
did not record. The rise is conditional: it happens only when the speaker's actor
class matches one specific value **and** an internal counter has reached its
threshold, at which point the counter resets and standing rises by one - and by a
further two if the payment has emptied the party's purse.

**On an unaffordable payment the exact fixed output is
`"Thou hast not enough gold!"`, followed by two line feeds.** The quotes are
part of the presentation framing. Before emitting them, the routine sets the
pending-word count to zero: a partial word queued before `0x85` disappears and
is not flushed. It then clears the multi-byte command and argument count and
calls the ordinary top-level keyword loop as a nested call. The next fixed
prompt is therefore `Your interest?`, a line feed, and `:` in that order.

This is not the labelled-block scoped prompt of Section 7.7 and it is not a
single forced turn. Each turn uses the ordinary reserved-word scan followed by
the speaking NPC's ordinary keyword scan:

| Nested input or response | Result inside the refusal prompt |
|---|---|
| `NAME`, `JOB`, or `WORK` | Run the ordinary fixed response, then print `Your interest?` again. |
| A profanity | Run the ordinary rebuke and pause, then reprompt. |
| An unmatched keyword | Print the ordinary no-match line, then reprompt. |
| A per-NPC response that reaches its NUL without signalling stop | Finish its ordinary quote/newline framing, then reprompt. |
| Empty input | Print `BYE` followed by two line feeds, run the NPC's mandatory Bye response in quotes, and return stop. |
| `BYE` or `THANK` | Run that same mandatory Bye response and return stop. |
| A per-NPC response that signals stop | Return stop without inventing an additional Bye line. |

Nonterminating turns never return to the refused response; they stay inside
the nested loop. Every path that actually returns from that loop returns stop.
The stop propagates through the gold handler, the byte runner, the original
response, and the enclosing keyword loop, so **every possible nested-loop
return closes the whole conversation**. The bytes after the refused command's
third digit are never resumed. The outer conversation owner also skips its
fallback Bye call on this stop result: empty input and `BYE`/`THANK` therefore
run the mandatory Bye response exactly once, while another stop-producing NPC
response receives no synthetic Bye output. Final conversation cleanup follows.

Compact compatibility vectors:

| Case | Initial state and stream shape | Required result |
|---|---|---|
| Affordable | Gold is 5; the standing-milestone gate is false; `0x85` is followed by digit characters `0`, `0`, `5`, then ordinary success prose and a record terminator. | Read no input; set gold to 0; refresh the panel; continue with the first success-prose character. |
| Unaffordable | Gold is 4; a partial word is pending; `0x85` is followed by digit characters `0`, `0`, `5`, then trailing prose. At the nested prompt enter `NAME`, then enter an empty line on the reprompt. | Discard the partial word; emit the exact quoted refusal and prompt; run the ordinary Name response and reprompt; emit `BYE` plus the quoted mandatory Bye response once; close the enclosing conversation; never emit the trailing prose. |

The rare moral-standing side effect of an accepted payment remains gated on
the speaking NPC's sprite class and a turn-based cooldown; `systems/karma.md`
section 4 owns that contract, and `0x85` itself is not a general karma writer.

The action-dispatch handler (`0x86`) is the engine's main extension point. The
letter verbs cover joining the party, refusing to talk, granting items, and
adjusting mood. The dispatch table is global; per-NPC variation comes from the
argument byte emitted by the NPC's response stream.

Known public letter effects are:

| Argument | Public effect | Grant per call |
|----------|---------------|----------------|
| `A` | Raise the shared food counter through the normal capped counter writer and refresh the food/gold presentation. | `+1` (cap `9999`) |
| `B` | Raise the shared gold counter through the normal capped counter writer. | `+1` (cap `9999`) |
| `C` | Raise the ordinary key counter through the normal capped byte writer. | `+1` (cap `99`) |
| `D` | Raise the gem counter through the normal capped byte writer. | `+1` (cap `99`) |
| `E` | Raise the torch counter through the normal capped byte writer. | `+1` (cap `99`) |
| `F` | Set the outdoor Klimb gear byte used as the Grapple gate. This is the gameplay role of the save byte that older notes labelled magic powder. | `+1` (cap `99`) |
| `G` | Raise the magic-carpet carried counter through the normal capped byte writer. | `+1` (cap `99`) |
| `H` | Set the Sextant carried-item flag. | Direct write `0xFF` |
| `I` | Set the Spyglass carried-item flag. | Direct write `0xFF` |
| `J` | Set the Black Badge carried-item flag. | Direct write `0xFF` |
| `K` | Raise the skull/special-key counter through the normal capped byte writer. | `+1` (cap `99`) |

Every counter-style letter (`A..G`, `K`) adds exactly **one** to its target slot per `0x86 X` invocation, using the shared capped-add helper (see `systems/stat-arithmetic.md`). A TLK script that wants to grant a larger amount embeds the same `0x86 X` sequence multiple times. Counter letters never assign a fixed final value; they always perform a saturating add by one. The three carried-item letters (`H`, `I`, `J`) instead write the sentinel `0xFF` directly into the carried-item flag byte, since the Sextant, Spyglass, and Black Badge are owned or not-owned rather than stocked.

Small numeric argument bytes below the letter range (values `< 0x40`) take a separate path: they target the generic per-conversation signal-flag bank — a sixty-four-byte array used by quest scripts that need "the player has done X" booleans without consuming a fixed slot — and also perform a saturating add of one (cap `99`) at index `N` of the bank. The bank is shared per conversation rather than per NPC; readers test the same bank by index later in the same blob.

Shop entry sits beside this byte-runner path rather than inside it. When Talk
resolves a shop-capable resident, resident shop metadata can route directly to
the shop dispatcher before a normal `.TLK` keyword blob is loaded. That dispatch
sets the current shop-kind selector, resolves the local shop instance from the
active scene, prepares vendor/shop substitution state, and calls the matching
shop arm with the same Talk context word. The shop overlay returns to the game
mode after purchase, refusal, or exit. The shipped shop-trigger byte inventory
is owned by `formats/npc.md` and `systems/shops.md`; conversation owns the
handoff boundary and shared caller context.

### 7.7. Labels, GOTO, and scoped prompts

The byte runner supports up to fifteen label bytes per blob, identified by the
values `0x91..0x9F`. Encountering one of these bytes is an active control path:
the runner records the label byte, rewinds the stream pointer to the start of
the loaded NPC blob, and enters the label handler.

The label handler searches byte-for-byte for records associated with the active
label. A label is *declared* by the two-byte marker `0x90 <label>`: the scan
looks for `0x90`, checks whether the byte after it equals the active label, and
on a match resumes the stream immediately past the label byte; otherwise it keeps
scanning. It does not compare text, fold case, or normalize label ids. Labelled
records are part of the blob data, and shipped blobs commonly reuse the same
label byte multiple times: once as the control transfer and again as one or more
records inside the labelled block. Implementations must therefore preserve the
engine's scan discipline rather than treating label values as unique symbols in
a map. In shipped content the value `0x9F` is conventionally the blob's final
record marker.

The ordinary runner does **not** recognise the declaration as an inert
two-byte unit. If execution is positioned on `0x90`, that byte follows the
printable path: under the default print mode it is queued as `0x90`, and the
later buffer flush strips the high bit and sends glyph codepoint `0x10` to the
text sink. It neither ends the stream nor skips its successor. The following
label byte is then processed independently as an active GOTO, so it rewinds to
the matching declaration and enters the normal scoped-label handler.

There is no declaration-boundary buffer operation. `0x90` joins the pending
word, and entering the GOTO handler preserves that word; later quotes, target
text, spaces, newlines, capacity limits, or response termination perform their
ordinary queue and flush behavior. If a dictionary expansion had armed the
pending-space flag, the printable path inserts its ordinary space before
`0x90`; that space can flush the preceding word, but this is not label-specific.

A minimal synthetic example is `C1 90 91`: ordinary execution queues `A`, then
queues the value that will flush as codepoint `0x10`, then treats `91` as a GOTO
to label `91`. It does not consume `90 91` as a silent separator.

Ordinary sequential execution never reaches this edge: every label declaration
in the four shipped conversation files directly follows a NUL, and the stream
driver stops at that NUL before dispatching the marker. Shipped content reaches
it in exactly one place, through a keyword match. `TOWNE.TLK` id 23 (Mario, in
the stocks) has an odd number of records after his five leading entries and
before his first declaration: one extra text record after his `crim` answer
moves every later record over by one position (Section 4). As a result:

- his `caug` and `tort` keywords sit in response positions and can never
  match; typing either gets `I cannot help thee with that.`;
- his last keyword-position record is the text `Don't ask!`, and its
  "response" is the record that begins at the first label declaration.

Typing `DON'T ASK!` therefore matches. The apostrophe and the exclamation mark
can be typed (the line reader accepts the printable range and the phrase fits
the fifteen-character limit), and the whole keyword is required: `DON'T ASK`
without the `!` does not match, while `X DON'T ASK!XYZ` does (Section 6 step
5). The response opens with the ordinary quote, then the runner is positioned on
the declaration marker, which it prints as glyph codepoint `0x10` by the rule
above; the label byte after it is a live GOTO, so his block 1 runs (its head,
then the `You respond-` prompt). Because a GOTO always reports a stop, the
keyword prompt at which `DON'T ASK!` was typed ends once block 1 is finished
and prints no `BYE` of its own; any farewell comes from block 1's own prompts.
Executed on the original conversation code with the shipped blob; the glyph was
observed only as the byte the text sink received, not on screen.
*(Corrected 2026-10-19, issue #299 Q22: this paragraph said the edge is
unreachable in the shipped response streams and is a compatibility rule only,
"not a normal shipped transcript path"; retracted, R583.)*

**The label range is `0x91..0x9F`, and that is confirmed by the shipped
content itself.** Scanning the four shipped conversation files for the
two-byte declaration marker followed by a byte in that range finds **eleven
distinct labels in use**, spanning the full range end to end. The distribution
is steeply skewed toward the low end: the first label accounts for over a
hundred declarations, the next three for most of the remainder, and several
mid-range labels appear only once or twice. `0x9F` is the other heavily used
value, consistent with its role as the conventional final record marker.

An implementation that recognises only the top of the range will therefore
fail on the overwhelming majority of shipped conversations rather than on a
rare edge case. Fifteen label values are addressable (`0x9F` minus `0x91`,
inclusive), matching the fifteen-label limit stated above; eleven are
exercised by shipped content, and the four unused values are not evidence of a
narrower range.

Labelled blocks can do more than skip an IF/ELSE arm: a block whose head
reaches its NUL opens a **scoped sub-prompt**, which is how an NPC asks a
follow-up question and routes the answer. *(Added 2026-10-18, issue #299 Q20;
the rules below were executed on the original conversation code against the
shipped blobs and spot-checked in a DOSBox run of the original game.)*

**Block layout.** A labelled block runs from its declaration to the next
declaration. Its records, each ending at a NUL, are in order:

1. the **head** (the stream after the declaration, up to its first NUL; see
   "What a GOTO runs first" below);
2. the **default arm** - the one record immediately after the head. It has no
   keyword;
3. zero or more **keyword/answer pairs**: a keyword record, then its answer
   record. Records are paired by position only, as at the top level (Section
   4). *(Added 2026-10-19, issue #299 Q22.)* Of the 313 shipped blocks, 260
   have records after the head and 53 do not. Of the 260, 259 open a scoped
   prompt; the other is the final block of `KEEP.TLK` id 9, whose head stops
   with `0x82` and is followed by one stray record that can never be reached.
   Of the 259 prompt-opening blocks, 258 have an odd number of records after
   the head (a default arm plus whole pairs). The one even case is
   `DWELLING.TLK` id 15, block 3 (the "true Avatar?" question): after its
   default arm comes a single unpaired record in keyword position. That record
   can never match, because it contains a value that folds to a carriage
   return, which the line reader never accepts, and it is longer than the
   fifteen-character input limit. (Containing dictionary codes is not by itself
   a reason: dictionary values at or above `0x20` compare as typeable
   characters.) So every non-empty, non-rebuke answer there runs the default
   arm, and the block's intended `'Tis indeed an honor!` path can never be
   reached in play. An implementation that pairs records by position and stops
   at the next declaration needs no special case for either block.

The scoped keyword scan stops at the next declaration. The record scans also
treat the final-marker value `0x9F` as a record end, but no shipped head or
default arm contains that value, so in shipped data every record ends at its
NUL. A label byte repeated inside a block is not a record separator; met as a
code it is an ordinary live GOTO. *(Corrected 2026-10-18, issue #299 Q20: this
paragraph said the scoped prompt prints "a prompt such as Your interest?" and
that a separator byte and the final label value mark records and sub-records
inside the block; retracted, R573 and R574.)*

**The scoped state machine.** "Quote" is the ordinary closing-quote sentinel
(`formats/tlk.md` Section 9.2); "a row break" is one literal newline. Every
way out of the machine reports a stop to whatever ran the GOTO (the 2026-10-17
rule below).

1. **HEAD.** Emit the quote, then run the head through the byte runner.
   - If the head stops (`0x82`, a successful `0x84`, a GOTO, an IF-ELSE that
     transfers or nests, `0xFF`, or any other stop), the block is finished and
     reports a stop. No prompt opens.
   - If the head reaches its NUL, emit the quote and two row breaks and go to
     PROMPT.
2. **PROMPT.** Mark the scoped state, which makes the five functional reserved
   words inert (step 3). Print `You respond-`, a row break and `:`, then read
   a free-text line of up to fifteen characters through the same input
   pipeline as the keyword prompt. This is **not** `Your interest?`. Escape
   only erases what has been typed (`systems/input.md`); only Enter submits.
   - **Empty line** (including Enter after Escape): print two row breaks,
     `"What didst thou say?` (an opening quote and no closing one), and two
     row breaks, then repeat PROMPT. The head is **not** re-run, nothing ends,
     and no `BYE` is printed. The scoped prompt cannot be left with an empty
     line.
   - **Non-empty line:** print two row breaks and go to RESERVED.
3. **RESERVED.** Scan the fixed thirty-four-word table (Section 5) in order with
   the keyword-match rule of Section 6 step 5.
   - `NAME`, `JOB`, `WORK`, `BYE` and `THANK` do nothing here. The scan moves
     on, and the typed line is left intact, so these words can still match a
     scoped keyword as text: `NAME` matches a scoped keyword `n`.
   - A rebuke word prints the rebuke and runs its bounded pause loop exactly as
     at the top level (Section 5), then the block restarts at HEAD: the head is
     printed again and a fresh scoped prompt opens.
   - Otherwise go to SCOPED.
4. **SCOPED.** Test the block's keyword/answer pairs in blob order with the
   same keyword-match rule; the first keyword accepted wins.
   - **Match:** emit the quote, then run that keyword's answer record.
   - **No match:** emit the quote, then run the **default arm**. The default
     arm is a whole record - text, a stop, a GOTO, or any mix - not an engine
     "I cannot help thee" reply.
   - If the record that ran stops, the block reports a stop (the conversation
     ends, or a GOTO inside it has already run its own block to completion). If
     it reaches its NUL, go to FALLBACK.
5. **FALLBACK.** Emit the quote and two row breaks, then run a fresh top-level
   keyword loop (Section 6) nested inside the block. It starts with
   `Your interest?`, and `NAME`, `JOB`, `BYE` and the other reserved words work
   normally again. When the player leaves it, it runs the Bye entry, printing
   the `BYE` line first only if the player left with an empty line (a typed
   `BYE` or `THANK` prints none; Section 6 steps 3 and 4). A stopping answer
   inside it also ends it. The block then reports a stop, so the conversation
   runs its farewell at most once.

**After a scoped answer completes, the scoped prompt does not repeat.** A
scoped answer or default arm that reaches its NUL always leads to the top-level
keyword loop of step 5; that is the only point where the fallback happens. It
never happens straight after a failed match, because a failed match runs the
default arm first. Only three things make the same question appear again:

- an empty line, which repeats the prompt but not the head;
- a rebuke word, which repeats the head and the prompt;
- a GOTO back to the block. Shipped blocks do this with a default arm that is
  nothing but the block's own label (twenty-two blocks), which repeats the head
  and opens a fresh prompt.

A GOTO met in an answer or in a default arm runs the target block in full;
because a block always reports a stop, the outer block is finished at that
point.

Executed matcher examples against a block whose keywords are `n` then `y`:

| Line typed | Record that runs |
|---|---|
| `Y`, `YES`, `YONDER`, `GO YES` | the `y` answer |
| `NAY`, `NO`, `NAME` | the `n` answer |
| `OKAY`, `MAYBE`, `BYE`, `MAYBE YES` | the default arm (in `MAYBE YES` the first `Y` is mid-word, so the later clean one is never tried) |

**Recruitment inside a scoped answer.** A successful `0x84` stops: the
conversation ends at once with no `BYE` and no Bye entry, and the speaker
leaves the scene. When the party is full the refusal is printed and nothing
stops; the answer runs on to its NUL and play continues at the top-level
`Your interest?` prompt of step 5. When no reserve roster record matches the
speaker, the diagnostic is printed and the stream stops.

**What a GOTO runs first.** *(Added 2026-10-16, issue #298 Q20.)* The labelled
block's head is the stream from the byte after the first declaration of the
label (searching from the start of the NPC's blob) up to the first NUL, run by
the ordinary byte runner. It ends early only if a control code stops the stream;
the NUL that ends it hands over to the scoped-prompt handling described above. A
repeated label is not a boundary. Inside the head every byte keeps its ordinary
meaning: a label byte in `0x91..0x9F` met as a code is a live GOTO at that
point, including one to the block's own label, which restarts the block; a
label byte that is the operand of the IF-ELSE code `0x8C` (or the target operand
of the `0xFE` threshold code) is consumed as that operand and is neither a GOTO
nor a boundary. A self-GOTO re-enters the label handler as a nested call, and
the outer call returns as soon as the inner one stops, so a retry loop never
opens a second scoped prompt for the outer level.
*(Added 2026-10-17, issue #299 Q1.)* The label handler reports a stop to
whatever ran the GOTO on every way out of a labelled block: when the head
stops, when the head reaches its NUL and the scoped prompt then finishes, and
when the scoped prompt falls back to the ordinary keyword prompt and that
prompt ends. So a GOTO is always the last thing its calling stream does. A GOTO
in the Description or the Greeting ends the conversation once its block is done
(Section 9).
The declaration search also
accepts the final-marker value `0x9F` in place of the declaration marker before
the label; no shipped record contains that pairing, so shipped content behaves
as if only the declaration marker counts.

Shipped census: 448 declared blocks, and no label is declared twice in any blob.
Seventeen heads contain label bytes (GOTOs to other blocks or IF-ELSE operands).
Exactly one head contains its own label: a castle NPC's name-challenge block,
whose head asks the player's name (ASK-WHO), branches to another block if the
name was right, and otherwise prints a retry line and ends with a GOTO to its
own label, so a wrong name re-asks the challenge rather than opening the scoped
prompt. A rule that ended each head at its first repeated label would cut that
head before the self-GOTO, drop the loop, and send a wrong answer to the scoped
prompt; in the other 447 heads the first NUL comes first, so such a rule happens
to give the same split. Labels do repeat after the head in 27 blocks; in 22 of
them the label is the whole of the default arm, the "ask again" arm of a yes/no
question - so "a block whose label never repeats" and "a block whose head
contains its own label" are different counts. *(Corrected 2026-10-18, issue
#299 Q20: a recount gives 27 where this said 28, and 22 where it said "nearly
all"; a census figure only, with no behavioural consequence, so no
`RETRACTIONS.md` row. The one-block difference is not itemised;
`OPEN-QUESTIONS.md` carries it.)*

*Shipped shape (added 2026-10-18, issue #299 Q20).* The 448 declarations are
313 labelled blocks and 135 final markers. Of the 313 heads, 259 reach their
NUL and open a scoped prompt; the other 54 stop first (53 with nothing after
the head, one with a stray record after it). The 259 default arms divide as
follows: 169 end at their NUL and fall back to the top level; 35 end with
`0x82`, ending the conversation; 22 are a bare self-GOTO ("ask again"); 31 GOTO
another block, 17 bare and 14 after some text; and 2 end with `0xFF`.
*(Corrected 2026-10-19, issue #299 Q22: this listed "one is malformed" as a
default-arm ending beside 168 fall-backs. The block meant, `DWELLING.TLK` id 15
block 3, has an ordinary default arm that reaches its NUL and falls back; what
is unusual is the unpaired record after it (Block layout, item 3). A census
correction with no behavioural consequence, so no `RETRACTIONS.md` row.)* 191 blocks have exactly
one scoped keyword and 29 have none; in a keyword-less block every non-empty
line that is not a rebuke word runs the default arm. Scoped keywords are
overwhelmingly `y` (183) and `n` (31). The 27 scoped answers that are a lone
keyword-alias code behave exactly as at the top level (Section 7.6). The
counts of blocks, final markers, self-GOTO default arms and `y`/`n` keywords
were recounted independently; the remaining splits come from one census pass
over the shipped `.TLK` files. Source provenance: derived from private analysis in `u5-decomp/notes/` (static reading of the label handler and the byte runner) and a scan of the shipped `.TLK` files.

The scoped prompt is not a second copy of the top-level conversation loop.
Before reading its inner answer, it marks the reserved-word handler as already
inside a BYE-like prompt state. As a result, top-level reserved words such as
`NAME`, `JOB`, `WORK`, `BYE`, and `THANK` do not run their ordinary global
responses from inside the scoped prompt; they stay in the typed line and can
still match scoped keywords as text. Empty input is also local to the scoped
prompt: it prints two row breaks, `"What didst thou say?` and two row breaks,
then reissues `You respond-` without re-running the head; no `BYE` is printed
and nothing ends. A rebuke word restarts the block from its head. If no scoped
keyword matches, the default arm runs. *(Corrected 2026-10-18, issue #299 Q20:
this paragraph said empty input "prints the prompt's BYE line" and that control
falls back to the top-level keyword loop when no scoped keyword response can be
run; retracted, R575 and R576.)*

The label-response helpers use the same stream-driver result as ordinary
responses. A nested response that reaches a byte-runner stop condition reports
stop to the label handler; a response that simply reaches its NUL terminator
reports no-stop. After an answer or default arm that reaches its NUL, the
handler emits the closing quote and two row breaks and opens a fresh top-level
keyword loop, in which the reserved words work again; when that loop ends the
block reports a stop. An unmatched line is not a fallback by itself: it runs the
default arm, and only that arm's own NUL leads to the top-level loop
*(corrected 2026-10-18, issue #299 Q20; R576)*.

IF/ELSE branches reuse the same machinery. The IF-ELSE introducer falls through
in-stream when the tested flag is clear, and transfers to the labelled record
named by its argument byte when the flag is set; the reserved argument `0xFF`
opens a nested keyword prompt instead of transferring (Section 7.2). *(Corrected
2026-10-17, issue #299 Q1: this said `0xFF` "ends the response instead of
transferring"; retracted, R562.)* The fall-through arm can end with its
own label transfer past the taken arm so that the runner does not also execute
it. The fifteen-label range is per blob, but labels are byte-level flow markers,
not globally unique names.

#### 7.7.1 Shipped recruitment paths

*(Added 2026-10-18, issue #299 Q20.)* Twelve of the thirteen recruitable
companions carry their recruit code (`0x84`) only inside a scoped answer, so
recruitment depends on the state machine of Section 7.7. Every row below was
run to a successful join on the original conversation code with the shipped
records - party size up, conversation ended with no `BYE` - by 21 paths in all,
each with the acquaintance bit both clear and set; Julia was also recruited in
a DOSBox run of the original game (the save afterwards held her in the party).
"Block k" means the block of the k-th label value in that NPC's blob. The path
given is the shortest; any line the keyword-match rule accepts works the same,
and `Y` stands for any line the rule matches to the scoped `y` keyword.

| Companion | File, dialog index (location) | Record holding the recruit | Keystroke path that recruits |
|---|---|---|---|
| Saduj | `CASTLE.TLK` 7 (Lord British's castle) | answer to `y` in block 6 | `JOIN`, `Y` |
| Gorn | `CASTLE.TLK` 11 (Blackthorn's castle) | answer to `y` in block 4 | `Y`, `Y`, `Y`. The Description jumps to block 1; blocks 1 and 2 accept only `y` and their default arms end the conversation; block 3's head jumps straight to block 4, so no prompt opens in block 3. Gorn has no ordinary keywords. |
| Geoffrey | `CASTLE.TLK` 40 (Buccaneer's Den) | answer to `y` in block 4 | `Y` or `N` at the Description's block 1, which leads to block 2, whose head opens the top-level prompt; then `JOIN`, `Y`. Alternatively `EVIL` (to block 3), `Y` (to block 4), `Y`. |
| Gwenno | `TOWNE.TLK` 11 (Britain) | the **head** of block 4 - the only recruit outside a scoped answer | `JOIN`: the top-level answer jumps to block 4, which recruits at once. Alternatively leave with an empty line: the Bye entry jumps to block 3, and `Y` there leads to block 4. |
| Jaana | `TOWNE.TLK` 35 (Yew) | answer to `y` in block 4 | `Y` (to block 1), then any non-empty line that is not a rebuke word (to block 2, whose three arms all lead on through block 3 to block 4), then `Y`. Or `JOIN`, `Y` at the top-level prompt. |
| Katrina | `TOWNE.TLK` 47 (New Magincia) | answer to `y` in block 2 | `Y`, `Y`. Or any other non-empty line, then `JOIN`, `Y`. |
| Johne | `KEEP.TLK` 1 (Ararat) | answer to `y` in block 2 | `SHAD` (or `FEAR`), then `Y`, `Y`, through two blocks reached only by scoped answers. He has no `join` keyword; any other answer in blocks 1 or 2 ends the conversation. |
| Mariah | `KEEP.TLK` 27 (Lycaeum) | answer to `y` in block 3 | `JOIN`, `Y`. Or `SHAD`, `Y`, `Y`, `Y`. |
| Toshi | `KEEP.TLK` 28 (Empath Abbey) | answer to `y` in block 1 | `JOIN`, `Y` |
| Maxwell | `KEEP.TLK` 29 (Serpent's Hold) | answer to `y` in block 1 | Already acquainted: the Greeting jumps to block 1, so `Y`. Otherwise `JOIN`, `Y`. |
| Dupre | `KEEP.TLK` 30 (Bordermarch) | answer to `y` in block 3 | `Y`, `Y`, `Y` through the Description's chain; an `N` in block 1 ends the conversation. Or `JOIN`, `Y` once at the top-level prompt. |
| Sentri | `KEEP.TLK` 31 (Bordermarch) | answer to `y` in block 4 | Any non-empty line that is not a rebuke word at block 1, which has no keywords and whose default arm jumps to block 2; then `Y`, `Y`, `Y`. Or `JOIN`, `Y`, `Y` at the top-level prompt. |
| Julia | `KEEP.TLK` 32 (Empath Abbey) | answer to `y` in block 3 | Any non-empty line that is not a rebuke word at block 1, whose arms both fall back to the top-level prompt; then `JOIN`, `Y`. (DOSBox: `NO`, `JOIN`, `Y`.) |

At block 1 of Julia and Sentri, as at any scoped prompt, an empty line only
re-asks and a rebuke word restarts the head (Section 7.7). Under these rules
every shipped recruitment is reachable. A wrong answer either re-asks the
question or drops back to the top-level prompt, where the player can try
again; Gorn's and Johne's chains instead end the conversation, and the player
Talks again. With a full party, a recruit inside a scoped answer prints the
refusal and play continues at the top-level prompt (Section 7.6, `0x84`).

Source provenance: private analysis in `u5-decomp/notes/` and
`u5-decomp/functions/TALK_OVL/` - static reading of the label handler, its
scoped matcher and record helpers, the reserved handler, the keyword loop and
recruit, confirmed by executing the original conversation code under emulation
on the shipped `.TLK` and `.NPC` files with the original text matcher and case
folder, an independent re-run with its own trace of every transition and all
21 recruitment paths, and a DOSBox run of the original game at Empath Abbey.

## 8. The common-word dictionary

A one-hundred-twenty-eight-entry table of common English words is shared by
`.TLK` dialogue and the shop bark renderer. Its full contents, the two token
biases, its empty slots, and its validation invariants are published in
`catalogs/common-word-dictionary.md`; the vocabulary itself is a resident data
resource, not part of the `.TLK` files.

On the dialogue side the token byte *is* the catalog index: `0x01` through
`0x80`, with `0x01` mapping to entry one and `0x80` to entry one hundred
twenty-eight. The shop renderer reaches the same entries from the byte range
`0x80`..`0xFF`. Tokens are replaced *inline* during emission, character by
character through the same word buffer that carries ordinary text, so an
expansion wraps and breaks exactly as if the word had been spelled out in the
blob. There is no pre-pass that flattens a blob into a string.

### 8.1 Emission order

For each dictionary token the runner does three things, in this order:

1. **Emit one space**, unconditionally — before every token, populated or not.
2. **Emit the entry's characters**, if the entry is populated.
3. **Arm the pending-space flag**, but only if the entry was populated.

The pending-space flag is read and cleared by the next *printable text byte*,
which emits one space ahead of itself (Section 7.1). Nothing else consumes it. So:

- `token token` renders as ` word1 word2` and leaves the flag armed.
- `token letter` renders as ` word1 letter`, with the single space coming from
  the flag.
- A token followed by punctuation gets the same leading space and no special
  handling; content that needs punctuation tight against a dictionary word uses
  one of the vocabulary's punctuation-bearing entries instead.

### 8.2 Empty entries

Ten catalog indices are empty. They are **not** word-boundary sentinels, and
they do **not** arm the pending-space flag — earlier revisions of this spec said
both, and both are withdrawn. An empty entry emits the leading space from step 1
and then queues the raw token byte itself as a literal character; because that
byte has its high bit clear, it renders in the alternate font (Section 7.1).

No shipped `.TLK` blob or shop record references an empty entry: across all four
dialogue files the set of tokens used is exactly the one hundred eighteen
populated indices. The behaviour above is stated for completeness and for custom
content, not because the original ever exercises it.

## 9. Conversation flow

Putting the pieces together, a single conversation runs through a fixed envelope:

1. **Entry.** The Talk command resolves an NPC and a dialog index. The conversation overlay loads the matching `.TLK` file's header, finds the right entry, and reads the blob.

2. **Opening preamble.** The dispatcher first emits a single line feed. The
   entry preamble then prints the fixed `You see ` lead-in (with its trailing
   space), runs the Description entry (entry 2 of the five mandatory leading
   entries), and emits the blank-line spacing before the NPC greeting.
   *Corrected 2026-09-06 (R393): this step previously named the lead-in "Thou
   seest"; the stored literal is `You see `.* If the Description entry signals a
   stop, the opener returns and nothing further is printed.

   *(Added 2026-10-17, issue #299 Q1.)* After an opener stop:
   - the conversation skips the keyword prompt, `BYE` and the Bye entry, and
     runs only the final cleanup (step 6);
   - the blank rows after the description are not printed;
   - the acquaintance test, the host-clock reseed and the coin flip of step 3
     do not happen.

   The same holds when the Greeting or the self-introduction's Name run of
   step 3 reports a stop. A Description reports a stop when it reaches `0x82`,
   when a GOTO it runs finishes (Section 7.7), or when the player leaves a
   keyword prompt opened by `0xFF` or by an IF-ELSE with argument `0xFF`
   (Section 7.2).

   Two shipped examples:
   - **The Britain wizard** (`TOWNE.TLK` id 12), party unknown. The
     Description's GOTO block asks the name, misses its IF-ELSE, prints
     `Good day!"` and one line break, and stops. The conversation is over,
     with the cursor at the start of the next row, and the next key is a
     command. With the party known, the IF-ELSE jumps to a block whose head
     prints the known-party greeting and ends in `0xFF`, so the keyword prompt
     opens there.
   - **The dwelling rat** (`DWELLING.TLK` id 12). The Description ends in
     `0xFF` after its ASK-WHO and more text. The keyword prompt opens inside
     the Description and play goes on normally. Leaving the prompt ends the
     conversation with one `BYE`, and the greeting never runs.

   Both cases were executed on the original under emulation, and no clock
   read or coin flip happened on the stop paths.

   *(Added 2026-10-19, issue #299 Q22.)* Shipped census: 26 Descriptions end
   with a live GOTO as their last byte, either a bare GOTO or an IF-ELSE
   followed by one; `TOWNE.TLK` id 23 (Section 7.7) is one of them. None of
   those NPCs ever prints its Greeting or introduces itself, whatever the
   acquaintance bit, and the conversation ends when the Description's block is
   finished, with at most one `BYE`. Executed with the bit clear and with
   it set for `TOWNE.TLK` id 4 (whose Greeting `Good day!` is never printed;
   each branch of his IF-ELSE goes to its own block), `CASTLE.TLK` id 11 and
   `KEEP.TLK` id 32: no Greeting, no host-clock read, reseed or coin flip, and
   the opener returns a stop. A control NPC with no Description GOTO showed
   the clock read, reseed and coin flip with the bit clear, and its Greeting
   with the bit set.

3. **Opening: acquaintance test, then greeting or introduction.** After the
   description, the engine consults the same per-scene "this NPC has been told
   the party's name" bit that the ASK-WHO / IF-ELSE pair uses (Section 7 and
   `systems/quest-flags.md` section 3). This is the bank's *second* reader, and
   it runs before any script byte does.

   - **Bit set (the NPC knows the party).** The engine opens the quote wrapper
     and runs the Greeting entry (entry 3 of the five mandatory leading
     entries) through the byte runner. No shipped Greeting contains `0x82`,
     and the stream driver never runs on from the Greeting into the next
     entry. Most Greetings run to their NUL.

     Eleven shipped Greetings end in a GOTO instead: `CASTLE.TLK` ids 3 and
     18, `TOWNE.TLK` ids 3, 5, 8, 9, 16, 19, 22 and 34, and `KEEP.TLK` id 29.
     A GOTO always comes back as a stop (Section 7.7), so for these NPCs the
     labelled block's scoped prompt, or the keyword prompt it falls back to,
     is the conversation's only prompt. The opener opens no second prompt
     afterwards, and one `BYE` is printed. This was executed on the original
     for `TOWNE.TLK` ids 34 and 8 and `CASTLE.TLK` id 3 with the bit set.
     *(Corrected 2026-10-17, issue #299 Q1: this bullet said most greetings
     end with `0x82`; retracted, R563.)*
   - **Bit clear (a stranger).** After the description has completed and this
     bit test has found the bit clear, the engine makes one fresh host-clock
     read, assigns the transformed value as the shared random-generator state,
     and immediately takes one draw from the inclusive range `0..1` (the
     `random(0, 1)` coin of `systems/prng.md` section 3). On result `0` the
     conversation simply proceeds to the keyword prompt with nothing said
     after the description. On result `1` the NPC introduces itself: the engine prints the
     stored lead-in `"I am called ` — a single string whose **own** opening
     quote and one trailing space are part of it, unlike the Greeting, whose
     surrounding quotes the renderer emits separately — and runs the **Name** entry (entry 1 of the five
     mandatory leading entries) instead of the Greeting, then closes the quote.
     *(Added 2026-10-26, issue #304 Q2.)* This draw is the opener's only one.
     Executed on the original for two shipped `TOWNE.TLK` strangers (ids 1
     and 2) with each result forced: one clock read, the state assignment,
     one draw over `0..1`; `0` printed nothing after the description and `1`
     printed the introduction. The known-NPC arm (no clock read, no draw) was
     not executed and rests on static reading.

   So a stranger volunteers its name roughly half the time and is otherwise
   silent after the description, while an NPC that already knows the party
   always goes straight to its greeting. Note the consequence for
   reproducibility: this is one of the sites that re-seeds the generator from
   wall-clock time (`systems/prng.md` section 3).

   An earlier revision of this spec described this step as a "stolen-action"
   or theft check that printed a warning when the just-addressed NPC should
   react. That is withdrawn: nothing in the opening step concerns stealing, and
   the acquaintance test's sense is the opposite of what the older text
   implied. The stolen-action warning belongs to the end-of-conversation
   cleanup, not to the opener.

4. **Keyword loop.** Section 6's loop runs until the player exits.

5. **Bye sequence.** When the player leaves the keyword prompt, the engine runs the Bye entry (entry 5 of the five mandatory leading entries). Leaving with an empty line prints `BYE\n\n` first; leaving with the `BYE` or `THANK` reserved word prints no `BYE` line (Section 6 steps 3 and 4). *(Corrected 2026-10-18, issue #299 Q20: this step said both ways out emit `BYE\n\n`; retracted, R579.)* A keyword or scoped answer that stops (`0x82`) ends the conversation without `BYE` and without the Bye entry. The same is true of any prompt nested by `0xFF`: it runs the farewell itself, and no outer level repeats it (Section 7.2). *(Corrected 2026-10-17, issue #299 Q1: this step said a keyword response that ends the stream leads to `BYE` and the Bye entry; retracted, R564.)*

**The complete shape of an ordinary entry** *(added 2026-09-12, issue #262)* is
therefore: a blank row, `You see ` plus the description, a blank row, the
greeting inside double quotes, a blank row, then `Your interest?` on its own row
and a colon on the next. **There is no engine-composed sentence anywhere in it.**
There is no name before the description, no `Talked to` lead-in, no engine-added
period after the description, and no unquoted greeting; a line of the form
`Talked to <name>: <description>. <legacy text> Your interest?` is wrong on
every element, and it also leaks what the original withholds - at entry the
original never volunteers the NPC's name except through the stranger's
coin-flip self-introduction.

Three mechanical points matter to anyone reproducing the rows:

- The dispatcher's leading line feed is an ordinary line-feed character through
  the shared character printer, but the blank rows and both double quotes are
  emitted through the conversation overlay's own script-character renderer,
  using its high-bit control codes. The renderer rewrites the row-break code
  into a line feed before handing it on, and the shared printer masks the high
  bit off anything it is not told to treat as an escape, so the quote code
  arrives as an ordinary double quote. A row-break byte routed straight to the
  shared printer instead would produce a carriage return, so the renderer's
  rewrite is load-bearing.
- The renderer drops a quote that would immediately follow another quote, so a
  Greeting entry that ends with its own closing quote does not produce a doubled
  one.
- Conversation text passes through a word accumulator that breaks the row when
  the current column plus the pending word would reach column eighteen.

The closing quote and its two row breaks are skipped when the entry that ran
signals a stop. This describes the opener path only: a conversation pre-empted
by the Talk command's own tile cases (Section 2) prints one of those lines
instead and never reaches any of this.

6. **Cleanup.** A final per-conversation cleanup pass runs, then output is flushed and control returns to the caller. That pass is *not* a general side-effect reconciliation: it is the Shadowlord of Falsehood's theft and nothing else, and away from Faulinei's hiding place it returns immediately without touching party state. Section 10 gives its full contract. Any gold movement, party-roster change, or signal-flag write has already happened inline, at the control code that performed it.

The conversation engine itself is therefore single-shot — one Talk command produces one full envelope. The per-conversation state cluster (active multi-byte command, argument buffer, print mask, etc.) is reset at entry, so a previous conversation cannot bleed into a later one.

## 10. Hooks into the rest of the engine

The conversation engine touches several other systems through narrow, well-defined interfaces.

**Text output.** Every emission goes through the wrap-aware string printer described in `text-output.md`. The conversation overlay neither reaches around the print system nor maintains a parallel renderer. The active window is the main text window at conversation entry; some stub messages and prompts may switch windows briefly. Word-wrap behaviour, colour, and style flags are owned by the text-output system.

When Talk resolves a shopkeeper, the shop dispatcher inherits this same
conversation-owned output state instead of configuring a new shop window. The
ordinary shop entry path preserves active window selector `2` and whatever
cursor the main text descriptor has at the moment of dispatch, after the shared
Talk entry newline has been emitted. Shop-specific clear, append, or side-panel
behaviour is therefore owned by the selected shop flow, not by a separate
conversation-to-shop window setup layer.

**Free-text input.** The keyword prompt and the ASK-WHO name prompt use the free-text input variant described in `input.md`. (RECRUIT-SPEAKER reads no free-text input and is not a prompt, but on the party-full path it consumes one keystroke through the single-keystroke wait; see Section 7.6. *Corrected 2026-10-29, issue #311 Q2: this said RECRUIT-SPEAKER "reads no input", retracted, `RETRACTIONS.md` R655.*) The engine clears the buffer-flush gate on entry to allow type-ahead and restores it on exit. The fifteen-character cap is the engine's invariant; the input pipeline itself does not know about it. **The two prompts share one input path and one fifteen-character line buffer**, so a name typed at the ASK-WHO prompt overwrites whatever the keyword prompt last held; only the empty-line test differs between them, and Section 6 step 3 gives the consequence. The reader echoes only ordinary printable characters and emits nothing for the Enter that ends the line, which is why the acknowledgement's own first feed is what closes the answer row. *(Added 2026-09-12, issue #266.)*

**Single-keystroke input.** WAIT-KEY uses the shared single-keystroke wait that drives the per-mode loops, so the world tick runs on each no-key pass exactly as at the command prompt, under the scene band (`systems/input.md` Section 2). PAUSE is the bounded loop of Section 7.3 and runs one world tick per pass. The keyword and ask-who prompts and the conversation yes/no prompt also wait through the shared routine. No game-clock time passes while the player reads, but outside dungeon scenes the world view keeps animating and drawing random numbers. *(Corrected 2026-10-26, issue #303 Q3: this paragraph previously said PAUSE and WAIT-KEY run in a prompt mode with the world tick suppressed; withdrawn, see `RETRACTIONS.md` R626.)*

**Party state.** The JOIN sequence is scripted by NPC responses that emit the
recruit-speaker code; the engine matches the speaking NPC against the reserve
roster itself and never asks the player to name anybody. Action-dispatch side
effects may accompany a recruitment in the same response. The gold-payment
routine (triggered by `0x85`) and the action-dispatch handler (triggered by
`0x86`) also mutate party state. The gold-payment path decodes a three-digit
demand and debits party gold when affordable. It can also raise the shared
moral-standing selector, but only through the narrowly gated milestone described
in `systems/karma.md` section 4.1 — the speaking NPC must belong to one specific
sprite class and a shared per-turn counter must have reached one hundred — and it
is not a per-virtue standing writer. The action-dispatch path owns item grants, member changes,
generic signals, and mood-style side effects. These operations update the
party state described by the save-image, roster, item, karma, and chargen
specs. The conversation engine itself does not manage the party roster; it
only invokes those party operations.

**Quest flags and karma branches.** The `0x8C` IF-ELSE branch tests the active
scene's TALK branch-flag bit for the NPC currently speaking, and the ASK-WHO
code (`0x88`) is what sets that bit. The `0xFE` branch is different: it consumes
a moral-standing threshold and a target label, then branches when the shared
moral-standing selector is at or above that threshold. The action-dispatch path
can also set generic one-conversation signal flags or fixed durable
resource/item fields. Implementations should keep the per-scene TALK branch
bank, generic transient signals, durable save-backed flags, and karma-threshold
branch semantics separate. The branch-flag bit index is engine-supplied from the
NPC roster slot and so is always within the thirty-two-bit slot; an
implementation that can nonetheless produce an out-of-range index should make it
build a zero mask, so such tests read as clear and such setters are no-ops.
`quest-flags.md` owns the non-karma branch flag boundary, while `karma.md` owns
the moral-standing selector.

**Conversation cleanup: the Falsehood theft.** Final conversation cleanup
first checks which Shadowlord, if any, is resident in the settlement the party
is in — the value town entry records on arrival (`systems/town-mode.md`
Section 13). Unless that value names the Shadowlord of Falsehood, the cleanup
returns immediately and nothing is taken. This is the same gate the shop
surcharge reads, so in ordinary play, away from Faulinei's hiding place, no
conversation costs the party anything.

While Faulinei is resident there, every completed conversation in that
settlement ends with a theft. The cleanup prints the stolen-goods line - the
single stored line `Something was stolen!`, with no leading spaces, which
begins and ends with its own line feed, so one blank row separates it from the
conversation's last row and the cursor is left at column 0 of the row below
it - then plays a
fixed descending PC-speaker glissando, makes one fresh host-clock read, and
assigns the transformed value as the shared random-generator state. Only then
does it inspect the inventory categories and remove exactly one thing, taking
the first case that applies. Thus the re-seed occurs even when the applicable
category uses a deterministic descending scan rather than a random pick. This
is one of the re-seed sites listed in `systems/prng.md` section 3, so what is
taken is not reproducible from game state:

1. If the party carries any keys, gems, or torches, the cleanup takes one
   draw from the inclusive range `0..2`: `0` picks keys, `1` gems, `2`
   torches. If the party has none of the picked item it draws again from
   `0..2`, one draw per attempt, until it picks a counter the party holds,
   and that counter is reduced by one. The loop always ends, because it is
   entered only when at least one of the three is nonzero. *(Added
   2026-10-26, issue #304 Q3.)* Executed on the original cleanup with
   scripted draw results and inventories: with only torches held, the
   results 0, 1, 2 took three draws and removed a torch. Which counter is
   keys, gems or torches rests on static reading of their other users
   (lockpicking, the gem view, lighting a torch), not on execution. That
   every attempt advances the generator follows from `systems/prng.md`
   section 4 (each call advances the state once); the run replaced the
   generator with a stub.
2. Otherwise the forty-eight-entry carried-equipment band is scanned from the
   highest item id downward and the first nonzero entry is reduced by one.
3. Otherwise the two eight-entry carried-item bands are scanned the same way,
   highest index first, and the first nonzero entry is reduced by one.
4. Only if the party has none of those does the thief take gold: a random
   `1..15` is subtracted from the party's gold, floored at zero.
   *(Added 2026-10-26, issue #304 Q3.)* The scans of items 2 and 3 take no
   draw, and the gold fallback takes exactly one draw over `1..15`
   (executed with no keys, gems or torches held).

The pass then redraws the gold/stats panel (whether this holds on the
item paths as well as the gold path is open; see `OPEN-QUESTIONS.md`,
issue #304 Q3). Exactly one item, or one gold
amount, is lost per conversation, and the loss is silent beyond the single
stolen-goods line — the game never names what was taken. The warning line and
sound are not a virtue-standing write, and none of this is karma-driven; it is
purely a consequence of the resident Shadowlord. `quest-flags.md` owns the
ordering summary and `systems/shops.md` owns the paired overcharge.

*(Added 2026-10-25, issue #300 Q20.)* Executed on the original opener,
keyword loop, farewell and final cleanup with a shipped blob: with the
selector naming Falsehood the farewell row was followed by a line feed,
`Something was stolen!`, a line feed and then the glissando; with the
selector naming another Shadowlord or none, nothing was printed. The line is
printed before the sound. The printer was stubbed, so "one blank row" is
inferred from the rule that a line feed arriving in a later call always costs
a row (`systems/text-output.md` Section 10.4).

**Town alarm.** The ALARM code (`0x8B`) runs the town alarm sweep owned by `systems/town-mode.md` Section 14; conversation passes no arguments and reads no result. Earlier revisions said this code ticked a resident curse logic that owned per-character byte counters; no such counters exist on this path, and that reading is retracted (R531). *(Corrected 2026-10-16, issue #298 Q14.)*

## 11. Boundaries and variations

The conversation runtime contract in this document is complete at byte-runner
depth. Remaining conversation-adjacent data packing questions, such as
persistent NPC interaction flag layout, are tracked by the owning format or
quest-state specs.

## 12. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The Talk command's entry handler — the direction prompt and the absence of any food, status or conversation gate (issue #300 Q12, executed with a memory-read watch on the provision counter), target-cell resolution, talk-through-tile fallback, status-tile gate, and dialog-index dispatch — derived from `u5-decomp/functions/TALK_OVL/`.
- The reserved "not a real NPC" dialog index, the shape of the scene-keyed
  handler it dispatches, that handler's complete write set (party gold only),
  its two-valued result, and the absence of any follow-on path — derived from
  `u5-decomp/functions/TALK_OVL/` and private analysis in
  `u5-decomp/notes/`. Those notes
  also retire the earlier reading that this index reached a healer or an
  innkeeper; there is no cure, rest, or status write anywhere on the path.
- The two concrete status-tile ids, their message assignment, the fact that the gate reads a live map tile rather than an NPC sprite, and the talk-through tile set — derived from private analysis in `u5-decomp/notes/`, which re-derives both from the shipped binaries and reconciles an internal inconsistency in the earlier handler note.
- The byte runner's full dispatch table, the multi-byte-command machinery, the GOTO-label semantics, the printable-text path, and the per-conversation state cluster — derived from `u5-decomp/functions/TALK_OVL/`.
- The gold-payment, action-dispatch, and karma-threshold branch handlers -- derived from `u5-decomp/functions/TALK_OVL/`, and `u5-decomp/functions/TALK_OVL/`.
- The Spyglass, Sextant, and Black Badge action-letter identities --
  cross-checked against the Z-stats special-item display path in
  `u5-decomp/functions/ZSTATS_OVL/`, and shipped `.TLK`
  action usage.
- The Talk-entry shop dispatch and shared shop caller context -- cross-checked
  against `u5-decomp/functions/ULTIMA_EXE/`.
- The `.TLK` file loader, the four-class dispatch by scene byte, the header walk, the two-byte count prefix ahead of the `(id, offset)` entries, and the 1024-byte blob read — derived from `u5-decomp/functions/TALK_OVL/`.
- The keyword input loop, the empty-input-as-BYE shortcut, the fixed reserved-keyword table, the ordinary per-NPC keyword scan, the profanity rebuke/pause branch, and the no-match diagnostic -- derived from `u5-decomp/functions/TALK_OVL/`, and `u5-decomp/functions/ULTIMA_EXE/`, cross-checked against the correction ledger in `u5-decomp/`.
- The labelled-block and scoped-prompt mechanics -- derived from
  `u5-decomp/functions/TALK_OVL/`, and
  `u5-decomp/functions/TALK_OVL/`, cross-checked
  against `u5-decomp/functions/TALK_OVL/`.
- The final cleanup pass, its Falsehood gate, the theft cascade, and the
  warning glissando -- derived from
  `u5-decomp/functions/TALK_OVL/` and
  `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: derived from private analysis in `u5-decomp/notes/` --
  the cleanup gate is the resident-Shadowlord selector, so the cleanup pass is
  the Shadowlord of Falsehood's conversation theft rather than a generic
  transient-signal reconciliation.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/TALK_OVL/` (2026-08-22
  re-read) -- the opening step is the conversation opener, not a theft check;
  it tests the acquaintance bit, and a stranger takes a coin flip between
  introducing itself by name and saying nothing. That note's original
  "stolen-action warning" and inverted-polarity readings are superseded.
  Cross-checked against
  `u5-decomp/functions/TALK_OVL/` and `u5-decomp/notes/`.
- The case-insensitive bit-7-stripping string-equality routine used by the JOIN-name compare and similar match operations — derived from `u5-decomp/functions/TALK_OVL/`.
- The on-disk `.TLK` file structure — blob obfuscation, mandatory leading entries, common-word dictionary substitution — derived from `u5-decomp/formats/`. The earlier private header reading is superseded.
- The corrected `.TLK` header contract of Section 3 — `(npc_id, blob_offset)` entry order, ids running `1..npc_count`, dialog index `1` as an ordinary NPC, and the withdrawal of the sentinel/alias reading — re-derived from the shipped `.TLK` and `.NPC` files against the header walk in `u5-decomp/functions/TALK_OVL/`, and cross-checked against the sprite-class description strings of `LOOK2.DAT`.
- The resident common-word dictionary and its shop-renderer token order -- derived from `u5-decomp/formats/`, with the published word list in `catalogs/common-word-dictionary.md`.
- The 2026-08-22 retrace that corrected the `0x87` keyword-alias semantics, identified `0x88` as the in-stream setter for the per-scene branch-flag bank, re-read the `0x8C` argument as a branch target label, reclassified `0x89`/`0x8A` as moral-standing writers, identified `0x8E` as the alternate-font toggle, and fixed the dictionary token range and emission order -- derived from `u5-decomp/notes/` and `u5-decomp/functions/TALK_OVL/`.

- **Issue #266, the ASK-WHO acknowledgement pass (2026-09-12).** Both
  acknowledgement texts, the question and lead-in texts, their leading feeds and
  absent closing quote, the two separate stored copies behind the empty-input and
  no-match arms, the single match condition shared by the flag write and the
  affirmative, the handler's own opening quote and the byte runner's suppression
  of the stream's following quote, the name-match rule including short names and
  first-occurrence-only acceptance, the irrelevance of member status, and the
  party-count bound - established by executing the original handler and the
  surrounding stream runner over forty-five input cases, with the stored text
  read back from the shipped data file and a census of all forty-eight shipped
  occurrences across the four dialogue files. Derived from private analysis in
  `u5-decomp/notes/`, `u5-decomp/functions/TALK_OVL/` and
  `u5-decomp/functions/ULTIMA_EXE/`. The row splits are the window's word-break
  rule applied to an executed character sequence, not a measurement of the
  renderer against real cursor state; see `OPEN-QUESTIONS.md`.

- **Issue #262 follow-up, the conversation-entry pass (2026-09-12).** The entry
  sequence and its stored lead-ins, the dispatcher's leading line feed, the five
  dispatcher branch lines and the typed command's own three, the waypoint-parity
  gate shared with the shop path, and the renderer's row-break rewrite,
  quote-suppression rule and column-eighteen word break were re-derived and
  re-executed from private analysis in `u5-decomp/notes/`,
  `u5-decomp/functions/TALK_OVL/` and `u5-decomp/functions/ULTIMA_EXE/`, with
  the stored text read back from the shipped data file. The renderer's
  column-dependent flush rules were read but not fully exercised; see
  `OPEN-QUESTIONS.md`.
