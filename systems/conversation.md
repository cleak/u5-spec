# Conversation

## 1. Overview

Ultima V's NPC conversations are driven by a small interpreter that runs a per-NPC byte-code stream. Each NPC carries a "blob" of interleaved obfuscated text and one-byte control codes; the engine prints the text with substitutions for common words and the player's name, prompts the user for a keyword, walks an in-memory pointer table to find the matching keyword, and runs that keyword's response through the same interpreter. The interpreter also handles flag-driven branches, party-recruitment prompts, gold transactions, NPC-curse checks, GOTO labels, and two ways of asking the player a name.

Almost all observable conversation behaviour — the questions an NPC will ask, the gold they want, who joins the party, which quest flags get set — is encoded in the blob, not the engine. The engine itself is small and re-entrant: a single byte runner, a single keyword loop, a single loader. Anything richer than "speak text and accept keywords" is built up by combining the dozen or so control codes the runner recognises.

This spec describes the Talk command's entry path, the on-disk `.TLK` file structure, the in-memory keyword tree, the byte runner's complete dispatch table, the conversation flow including BYE handling and party-name prompts, and the hooks into the rest of the engine (text output, free-text input, the party module, the quest-flag store).

## 2. The Talk command

The Talk command is one of the per-letter actions accepted by the town/dwelling/castle/keep mode loop; it is *not* available outdoors or in dungeons (there are no scheduled NPCs to address there) and is not available during combat. When the dispatcher routes the keystroke to the conversation overlay, the entry handler performs five steps before the engine proper takes over:

1. **Liveness gate.** A resident "can talk now" predicate decides whether a conversation is allowed at all. If the gate refuses (the most likely reasons are "in combat", "asleep", "starving", or "already in a conversation"), the command returns immediately without printing anything.

2. **Player position and facing.** The handler reads the party's tile coordinates and the current facing direction (a signed `dx, dy` pair written by the most recent movement command).

3. **NPC lookup at the facing tile.** The party's facing tile is `(player_x + dx, player_y + dy)`. The resident NPC-occupancy structure is consulted to find an NPC whose live tile matches. If no NPC is at that tile, the handler tests whether the tile is a *talk-through* tile — a small white-list of tile types representing shop counters, low fences, and similar pass-through barriers. If the tile is talk-through, the handler advances `(dx, dy)` once more and queries again. If still no NPC is found, the handler prints a "Nobody's here!" message and returns.

4. **Stub-state filter on the NPC's tile byte.** With an NPC located, the handler reads the NPC's current tile byte to detect two transient states. A "sleeping" tile prints a "Zzzzzz..." message and returns without entering the conversation engine. A "no response" tile (the NPC is praying, meditating, or otherwise unavailable) prints a "No response!" message and returns. Any other tile falls through.

5. **Dialog-index dispatch.** Each live NPC carries a one-byte *dialog index* loaded into RAM from the location's `.NPC` file when the scene was entered. The handler reads the dialog index for this NPC and hands it to the conversation engine, which uses it as the key for looking up the NPC's blob in the matching `.TLK` file.

The dialog index is a 1-based identifier shared between the `.NPC` and `.TLK` files of the same location class. Index 0 means "no dialogue at all" (the NPC is a non-speaker — a guard, a child too young to talk to, an animal). Index 1 is the universal *sentinel* — the first slot in every `.TLK` file is reserved as a placeholder and is never resolved as real dialogue.

## 3. The four `.TLK` files

Conversation data is split across exactly four files, one per location class — `TOWNE.TLK`, `DWELLING.TLK`, `CASTLE.TLK`, `KEEP.TLK`. The class is determined by the current scene byte: it is `(scene_id − 1) >> 3`, mapping scenes `1..8` to towns, `9..16` to dwellings, `17..24` to castles, and `25..32` to keeps. The mapping is fixed; a given NPC's dialog index resolves only against the file matching their location class.

Each `.TLK` file contains a header (a fixed-size index of NPC entries) followed by the variable-size blob data:

```
.TLK file:
  uint16  npc_count               // number of NPC slots in this file
  uint16  sentinel                // always 0x0001 — the "NPC 1" sentinel
  Entry   entries[npc_count − 1]  // one entry per real NPC, sorted by id
  uint8   blob_data[...]          // concatenated NPC blobs, XOR-obfuscated text
```

```
Entry (4 bytes):
  uint16  blob_offset             // absolute file offset of this NPC's blob
  uint16  npc_id                  // 1-based identifier matching dialog_index
```

The first four bytes of every file are read as the special pair `(npc_count, 0x0001)` — that is, the count occupies the slot a regular entry would use for `blob_offset`, and the sentinel `1` occupies the slot a regular entry would use for `npc_id`. After this leading pair, the remaining `npc_count − 1` entries describe real NPCs, sorted by ascending `npc_id`. The shipped files contain 48 (TOWNE), 15 (DWELLING), 40 (CASTLE), and 32 (KEEP) entries respectively.

The leading sentinel exists because dialog index `1` is never a real NPC; the slot is structural. Any NPC carrying dialog index `1` would silently fail to find a real blob and produce empty conversation. Live NPCs use indices `2..npc_count`.

When the engine asks to talk to dialog index `D`, the loader reads the first 512 bytes of the file (enough to cover any class's header) into a working buffer, walks the entries linearly, and finds the entry whose `npc_id == D`. The matched entry's `blob_offset` field is then the file offset of the NPC's blob. The loader issues a second read of up to 1024 bytes at that offset into the same buffer, overwriting the header with the blob. From the engine's perspective, the buffer now begins with the NPC's keyword tree.

The 1024-byte cap is comfortable for shipped data — the longest known blob is a few hundred bytes — but is a hard ceiling. A blob longer than 1024 bytes would silently truncate. Implementations targeting a modern engine should size the read for the largest blob in the data set or do a length-aware read.

## 4. NPC blob structure

A single NPC's blob is a stream of obfuscated bytes representing alternating text spans and control codes. It begins with five fixed entries — the *mandatory leading entries* — followed by zero or more (keyword, response) pairs.

The five leading entries are, in order:

1. **Name.** The NPC's display name, e.g. "Jennifer".
2. **Description.** A short prose phrase describing the NPC's appearance, e.g. "a weathered girl".
3. **Greeting.** What the NPC says when first addressed, e.g. "Hello, Avatar".
4. **Job.** What the NPC says in response to the keyword `JOB`. By convention the keyword loop reaches the same entry when the player asks `JOB`.
5. **Bye.** What the NPC says when the player exits the conversation (typed empty input, or the keyword `BYE`).

Each entry is a NUL-terminated stream of post-obfuscation bytes. After the five mandatory entries comes the variable-size keyword body. Each keyword body is a pair: a NUL-terminated keyword string followed by a NUL-terminated response stream. The pairs continue until the end of the blob.

Both keywords and response text use a single obfuscation scheme: every printable text byte has the high bit (`0x80`) set on disk. A literal `'A'` (`0x41`) is stored as `0xC1`. The engine strips bit 7 when comparing keywords and when rendering text. This is *not* an encryption — it's a simple bit flag — but it has the side effect that the on-disk text is not casually readable as ASCII strings. The same flag distinguishes text bytes (high bit set) from control codes and dictionary indices (high bit clear), which is how the byte runner classifies each byte without any escape sequences.

Control codes (Section 7) appear inline in any text stream. They are *not* required to live at the start of an entry — they can punctuate text mid-line. A response stream is therefore a possibly long mix of obfuscated text bytes, common-word indices, and control codes, terminated by an end-of-response sentinel.

## 5. The keyword pointer table

When a blob is loaded, the engine populates an in-memory pointer table — one near-pointer per keyword in the blob — so that keyword matching does not have to re-scan from the blob start every time. The table holds up to thirty-four entries: the five mandatory leading entries occupy fixed slots, and up to twenty-nine additional (keyword, response) pairs fill the rest. An NPC with fewer keywords leaves later slots unused; those slots either point to an empty string or are sentinel-flagged so the keyword loop skips them.

The first five slots of the table cover the mandatory leading entries (Name, Description, Greeting, Job, Bye). Slots six through thirty-four cover the variable keywords in the order they appear in the blob. Each pointer targets the start of the *keyword* string; the corresponding response is the byte immediately following that string's NUL terminator.

## 6. The keyword input loop

After the loader has populated the keyword pointer table and the greeting has been emitted, control passes to the keyword input loop. Each iteration:

1. **Print the prompt.** The string `Your interest?\n:` is printed into the active text window, leaving the cursor on the next line ready to accept input.

2. **Read a line of free-text input.** The free-text input pipeline (described in `input.md`) accepts up to fifteen characters with backspace handling. The line is stored uppercased in a small buffer. Function keys, direction codes, and other non-printable bytes are silently discarded; Enter terminates the line.

3. **Empty-input shortcut.** If the player pressed Enter on an empty line, the engine prints `BYE\n\n`, runs the NPC's `Bye` entry through the byte runner, and returns to the caller. This is the most common way conversations end.

4. **Keyword scan.** The engine walks the keyword pointer table in order, skipping the first five slots (the mandatory leading entries are *not* re-matched here — the player cannot type "DESCRIPTION" to retrigger them; the loop matches only the variable keywords starting at slot six, with the exceptions noted below). For each populated slot, the engine compares the slot's keyword string against the typed input using a bit-7-stripping, case-insensitive, full-string equality test. The compare strips bit 7 from both sides (so the obfuscated keyword bytes match plain ASCII) and folds both sides to upper case before testing each byte. Both sides must reach a NUL terminator simultaneously for a match.

5. **Match found.** When a keyword matches, the engine first checks for special early-handled cases (the JOIN-related keywords listed below), then runs the keyword's response stream through the byte runner. After the response finishes, the loop returns to step 1 to prompt for the next keyword.

6. **No match.** When the loop completes without a match, the engine prints `I cannot help thee with that.\n\n` and returns to step 1.

The match is whole-string equality, *not* prefix matching. An NPC with separate `gran` and `grandpa` keywords resolves them independently — `grandpa` does not prefix-match `gran`. The keyword's actual length is whatever the NUL terminator says it is; the four-character "U4 convention" is a player-side discipline, not an engine constraint. The fifteen-character input limit on the typed side caps the longest matchable keyword at fifteen characters.

The special early-handled keywords are the ones that drive party recruitment. When the keyword index is one of a small reserved range (corresponding to `NAME`, `JOIN`, and `WHO ART THOU`), the response is intercepted by the party-join handler before the byte runner sees it; the handler may run the response itself with extra side effects (asking the player which slot the NPC should join, decrementing gold, validating party size). After the join handler returns, the keyword loop either continues normally or terminates the conversation depending on whether a join completed.

## 7. The byte runner

Every byte of every text stream — the five mandatory leading entries, every keyword response, the bodies of branched IF/ELSE arms, the bodies of GOTO targets — is fed through a single dispatcher. The dispatcher classifies the byte by value range and either emits printable output, runs a control action, or stops the current stream.

The dispatcher's classification, in order:

- **Bytes `0x01..0x9D` (high bit clear).** These are *common-word dictionary indices*. The byte is used as an index into a 256-entry pointer table; the pointer targets a NUL-terminated word in the engine's common-word vocabulary, which is expanded inline into the output. See Section 8.
- **Bytes `0x9E..0x9F`.** These are GOTO-LABEL codes; their high bit is set and they participate in label dispatch. See Section 7.7.
- **Bytes `0xA0..0xFD` (high bit set, in the printable range).** The high bit is stripped and the resulting low-ASCII byte is emitted as a glyph through the text-output system. See Section 7.1.
- **Bytes `0x80..0x9F` (with the exception of the GOTO range above).** Engine control codes. The dispatch table is in Sections 7.2–7.6.
- **Byte `0xFE`.** A multi-byte command introducer that behaves as an alias for `0x8C` (IF/ELSE).
- **Byte `0xFF`.** End-of-response. The byte runner flushes any pending word buffer and signals the keyword input loop to start a new iteration.

The byte runner has a small amount of per-conversation state: a "multi-byte command in progress" flag (set by `0x85`, `0x86`, `0x8C`, and `0xFE`), an argument-collection buffer for the multi-byte arguments, a print mask that may be toggled mid-stream, a few sentinel bytes used to suppress accidental double-quote artefacts, and a leading-space flag set by certain dictionary expansions. All of this state is reset at the start of each conversation.

### 7.1. Printable text emission

Bytes that classify as printable text (`0xA0..0xFD` with bit 7 stripped) are passed through a small word-boundary buffer and on to the text-output system's wrap-aware string printer. The buffer accumulates characters until it sees a soft break (a space byte) or a forced flush (a control code that performs one), at which point it emits the accumulated word.

The intermediate buffer exists for two reasons. First, the output respects the active text window's word-wrap rules — long sentences wrap at word boundaries rather than mid-word, even though the byte runner emits one byte at a time. Second, dictionary expansions (Section 8) need to merge with surrounding text *as a single word*; without the buffer, "the" expanded between two letters would be three separate writes that the wrap engine could not coalesce.

A leading-space flag may be set when an empty dictionary entry was encountered; the flag forces a single space to precede the next emitted character. This is how the dictionary handles word boundaries when the dictionary itself supplies a multi-word phrase.

The print mask — stored in a single byte that the `0x8E` toggle XORs against `0x80` — modulates how printable bytes flow through the runner. With the mask in its default state, printable bytes go to the buffer and are eventually emitted. With the mask flipped, printable bytes are gated differently (the most likely interpretation is "switch to a literal-vs-substitute mode" but the exact effect is flagged in Section 11).

### 7.2. Player-name and stream-control codes

| Code  | Mnemonic           | Effect                                                                                                                          |
|-------|--------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x81  | PRINT-AVATAR-NAME  | Emit the player's saved name (the name chosen during character creation) into the output stream. Used in greetings like "Hail, ${name}!". |
| 0x82  | END-STREAM         | Stop the current stream and signal the caller "this stream is finished". Used to terminate the fixed leading entries (Name, Description, Greeting, Job, Bye) without ending the whole conversation. |

`0x81` interpolates the avatar's name as if it were a literal text run, including word-boundary handling. `0x82` is distinct from `0xFF` (end-of-response): `0x82` is what the engine reads at the end of a leading entry that runs as a unit (e.g. when the engine emits the greeting at conversation start), while `0xFF` returns control to the keyword input loop after a keyword response completes.

### 7.3. Pause and key-wait codes

| Code  | Mnemonic     | Effect                                                                                                                          |
|-------|--------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x83  | PAUSE        | Redraw the world view, then wait for any key. After the key, redraw the party panel for every member to refresh state that may have changed. If the player presses a designated cancel key, terminate the current stream. |
| 0x8F  | WAIT-KEY     | Block for one keystroke. Unlike `0x83`, no redraw work is done — the byte runner simply blocks until the player presses a key. |

Both codes are used to chunk long responses into reader-friendly pages. The conventional use is to insert one `0x8F` after every screen-full of text, and one `0x83` after a more substantial transition (such as just before announcing a quest reward).

### 7.4. Newline and panel-flush codes

| Code  | Mnemonic           | Effect                                                                                                                          |
|-------|--------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x8A  | PANEL-NEWLINE      | Mark a newline boundary that also flushes the party-panel state. The most likely use is to ensure the panel is up to date after multi-line content has scrolled. |
| 0x8D  | LITERAL-NEWLINE    | Force-emit a literal newline through the text-output system. Used to end a line when no natural break would fall there. |

### 7.5. Print-mask and curse codes

| Code  | Mnemonic        | Effect                                                                                                                          |
|-------|-----------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x8B  | CURSE-CHECK     | Run the resident curse-check routine. Used in dialog with cursed-item NPCs (e.g. the snake in Despise) to tick the curse state. |
| 0x8E  | TOGGLE-MASK     | XOR the print-mask byte with `0x80`. Toggles between the two output modes described in Section 7.1. |

`0x8B` does not directly affect the stream; it is a side-effect-only code that ensures the player's curse state is updated at a specific narrative beat. `0x8E` is the only code that mutates the byte runner's print-mask state, and is typically used in matched pairs (one to switch mode, one to switch back).

### 7.6. Branching, recruitment, and transactional codes

These codes are the most semantically rich. Several of them introduce a *multi-byte command*: the introducer code is followed by one or more argument bytes that are not interpreted as ordinary stream bytes but are collected into an argument buffer and consumed by the introducer's handler.

| Code  | Mnemonic        | Argument bytes following | Effect                                                                                                                          |
|-------|-----------------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x84  | ASK-PARTY-NAME  | none                    | Prompt the player to type a party member's name. The typed name is matched against each live member with a case-insensitive, bit-7-stripping compare; the match index (0 if no match) is available to the surrounding response. Used by the JOIN sequence and any "name a companion" prompt. |
| 0x85  | GOLD-PAYMENT    | three                   | Collect three argument bytes encoding a gold amount and associated flags, then run the gold-payment routine: prompt the player, validate against current party gold, deduct on success. Used for tolls, bribes, and donations. |
| 0x86  | ACTION-DISPATCH | one                     | Collect one argument byte (a letter `A..K`) and dispatch to a per-letter action handler. Side effects include mood adjustments, score increments, granting items, and marking a per-NPC flag. The letter-to-effect mapping is per-NPC. |
| 0x87  | SET-FLAG        | none (consumes follow-up) | Save the current stream pointer, walk the same keyword scan the input loop would walk against the next stream segment, run any matched response, and on no-match restore the saved pointer and continue. This is how an NPC inserts a conditional side-clause that recurses into another keyword's response. |
| 0x88  | ASK-WHO         | none                    | Variant of `0x84` used for "who is the X?" replies that produce a name. |
| 0x8C  | IF-ELSE         | one                     | Collect one argument byte (a flag identifier) and test the corresponding NPC quest flag. If set, branch into the *else* arm; if clear, fall through to the *then* arm. Arms are delimited by label codes (Section 7.7) so the runner skips the not-taken arm. |
| 0xFE  | IF-ELSE-ALT     | two                     | Multi-byte alternative to `0x8C`. Collects two argument bytes indexing into a wider external state cluster (cross-NPC quest progress, scene-level flags). Branch logic is otherwise identical to `0x8C`. |

The gold-payment introducer (`0x85`) interacts with conversation flow, not just emission: depending on whether the player can pay, the surrounding response may take different paths, so implementations need to model it as a re-entrant prompt that returns a result code.

The action-dispatch handler (`0x86`) is the engine's main extension point. The per-letter verbs cover joining the party, refusing to talk, granting items, and adjusting mood; new verbs are added by extending the per-letter dispatch.

### 7.7. Labels and GOTO

The byte runner supports up to fifteen named labels per blob, identified by the byte values `0x91..0x9F`. A label byte appearing directly in the stream is *not* a control action — it is a *target*, treated as a soft no-op so subsequent bytes continue to interpret normally.

A GOTO is encoded by storing the desired label in a pending-GOTO slot and calling the label-search routine. The routine rewinds the stream pointer to the *start of the current NPC's blob* and scans forward for a matching label byte; when found, the runner resumes from the byte immediately after the match.

IF/ELSE branches use this to skip the not-taken arm. The IF-ELSE introducer chooses, based on the flag test, whether to fall through (the *then* arm) or GOTO a label that opens the *else* arm. The *then* arm ends with its own GOTO past the *else* arm so that the runner does not also execute it. The fifteen-label limit is per blob; the same number may be reused across non-overlapping branches, but the rewind-and-scan rule means the *first* occurrence after the blob start always wins.

## 8. The common-word dictionary

A 256-entry pointer table targets a vocabulary of common English words shared across all `.TLK` files. Bytes `0x01..0x9D` in any text stream are replaced *inline* by the corresponding word during emission.

The vocabulary is fixed and shipped with the engine (in the resident data segment, not the `.TLK` files). It contains common articles, pronouns, and connectives — `the`, `thou`, `of`, `and`, `you`, etc. — plus Britannian proper nouns such as `Blackthorn`, `Britannia`, `Lord British`, and the major-city names. Proper nouns in the table let many NPCs share canonical references without restating the full string in each blob.

Only roughly the first hundred and fifty of the 256 slots are populated; an index pointing at a NULL slot does not expand, but instead sets a "leading space needed" flag for the next emission — the encoder's way of hinting at a word boundary without an explicit space byte.

The exact word at each index belongs in a data spec, not here.

## 9. Conversation flow

Putting the pieces together, a single conversation runs through a fixed envelope:

1. **Entry.** The Talk command resolves an NPC and a dialog index. The conversation overlay loads the matching `.TLK` file's header, finds the right entry, reads the blob, and populates the keyword pointer table.

2. **Steal/give-gold check.** Before any text is emitted, the engine checks a one-shot flag set by the previous turn's actions. If the flag indicates the NPC has just witnessed the player committing a transgression (stealing from a chest, drawing a weapon in town, attacking another NPC), the engine prepends an admonition message before falling through to the greeting.

3. **Greeting.** The Greeting entry (entry 3 of the five mandatory leading entries) is run through the byte runner. Most greetings end with `0x82` (END-STREAM) so the runner returns control without proceeding into the Job entry.

4. **Keyword loop.** Section 6's loop runs until the player exits.

5. **Bye sequence.** When the player exits (typed empty input, or a keyword response that ends the stream), the engine emits `BYE\n\n` and runs the Bye entry (entry 5 of the five mandatory leading entries).

6. **Cleanup.** A final per-conversation cleanup pass settles party-state side effects (gold transactions, quest-flag updates, recently-joined party members, mood adjustments), flushes any pending output, and returns to the caller.

The conversation engine itself is therefore single-shot — one Talk command produces one full envelope. The per-conversation state cluster (active multi-byte command, argument buffer, print mask, etc.) is reset at entry, so a previous conversation cannot bleed into a later one.

## 10. Hooks into the rest of the engine

The conversation engine touches several other systems through narrow, well-defined interfaces.

**Text output.** Every emission goes through the wrap-aware string printer described in `text-output.md`. The conversation overlay neither reaches around the print system nor maintains a parallel renderer. The active window is the main text window at conversation entry; some stub messages and prompts may switch windows briefly. Word-wrap behaviour, colour, and style flags are owned by the text-output system.

**Free-text input.** The keyword prompt and the ASK-PARTY-NAME / ASK-WHO prompts use the free-text input variant described in `input.md`. The engine clears the buffer-flush gate on entry to allow type-ahead and restores it on exit. The fifteen-character cap is the engine's invariant; the input pipeline itself does not know about it.

**Single-keystroke input.** The PAUSE and WAIT-KEY codes use the single-keystroke "wait for the next command" routine — the same one that drives the per-mode loops — but in *prompt mode*, with the prompt-character byte set so that the world tick is suppressed. Time does not pass while the player is reading.

**Party state.** The JOIN sequence (triggered by the reserved keyword indices and routed through the party-join handler), the gold-payment routine (triggered by `0x85`), and the action-dispatch handler (triggered by `0x86`) all mutate party state — adding or removing members, deducting gold, granting items, adjusting mood. These operations cross-call into the party module (which is the subject of a future spec). The conversation engine itself does not manage the party roster; it only invokes the party module's operations.

**Quest flags.** The IF-ELSE branches (`0x8C` and `0xFE`) test bits in two flag clusters: a per-NPC table tracking small progressions, and a wider external table tracking game-wide quest progress. The SET-FLAG and multi-byte-argument forms write to the same clusters. Both clusters are part of the saved game and are persisted across save/load. Implementations should model them as bit arrays addressable by the argument byte the multi-byte introducer collects.

**Curse state.** The CURSE-CHECK code (`0x8B`) ticks the resident curse logic. The conversation engine simply prods the routine; the curse logic itself owns the per-character byte counters.

## 11. Open questions and variations

This section records places where the picture is not yet complete or where evidence is internally inconsistent.

- **Print-mask semantics.** The `0x8E` toggle flips a single bit in the print mask, and the printable-byte path consults that mask. Two readings are consistent with observed behaviour: (a) it switches between dictionary-expansion and literal-pass-through, so `0x8E` lets a stream embed a verbatim byte that would otherwise be a dictionary index; (b) it switches case folding, so subsequent text is rendered as-typed rather than uppercased. Implementations should pick the conservative reading and verify against in-game playthroughs.

- **The `0xA2` double-quote sentinel.** The byte runner suppresses a `0xA2` (which decodes to `"`) that follows another `0xA2`. The most likely interpretation is suppression of paired-quote artefacts arising from a close-stream code immediately following a quoted phrase, but the exact trigger is uncertain. The mis-fire is cosmetic if not handled.

- **Reserved keyword indices.** The keyword loop intercepts certain indices for the JOIN handler before the byte runner sees them. NAME, JOIN, and WHO ART THOU are confirmed; the full reserved set is not yet traced.

- **`0x86` action-letter table.** The letter `A..K` argument is dispatched to a per-NPC action handler. The mapping is partially uniform across NPCs (e.g. `'J'` for "join the party") but not globally; a full enumeration belongs in the action-handler spec when written.

- **Multi-byte-argument layouts for `0x85`.** The three argument bytes encode the gold amount and flags, but the exact field split is not yet settled. Reverse-engineer from the gold-payment routine during implementation.

- **Nested IF/ELSE.** The label-search routine rewinds to the blob start and takes the first match, so nested branches need label allocations that avoid collisions. Whether the shipped data uses nesting at all is unknown.

- **NPC 1 sentinel.** Dialog index 1 is reserved and is never resolved as real dialogue. Whether the engine refuses entry or walks an empty blob is not pinned down; implementations can safely treat indices 0 *and* 1 as "no dialogue".

- **Keyword pointer table population.** The thirty-four-slot table is populated between blob load and conversation entry; the exact populator is unconfirmed. The behaviour is the same whether it walks the blob's NUL terminators or stores fixed offsets.

- **Maximum blob size.** The loader caps the blob at 1024 bytes. Whether any shipped NPC hits this cap is unverified. A length-aware load belongs in any robust implementation.

## 12. Sources

The behaviour described here was derived by reading the disassembly notes for the following functions and format dissections in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- The Talk command's entry handler — the liveness gate, facing-tile resolution, talk-through-tile fallback, sleeping/no-response stubs, and dialog-index dispatch — derived from `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md`.
- The byte runner's full dispatch table, the multi-byte-command machinery, the GOTO-label semantics, the printable-text path, and the per-conversation state cluster — derived from `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`.
- The `.TLK` file loader, the four-class dispatch by scene byte, the header walk, the leading-pair-as-count encoding, and the 1024-byte blob read — derived from `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`.
- The keyword input loop, the empty-input-as-BYE shortcut, the keyword pointer table layout, the early party-join interception, and the no-match diagnostic — derived from `u5-decomp/functions/TALK_OVL/0x0B04_conversation_loop.md`.
- The case-insensitive bit-7-stripping string-equality routine used by the JOIN-name compare and similar match operations — derived from `u5-decomp/functions/TALK_OVL/0x0000_strncmp_uppercase.md`.
- The on-disk `.TLK` file structure — header layout, blob obfuscation, mandatory leading entries, common-word dictionary substitution — derived from `u5-decomp/formats/npc-tlk-pth.md`.
