# Conversation

## 1. Overview

Ultima V's NPC conversations are driven by a small interpreter that runs a per-NPC byte-code stream. Each NPC carries a "blob" of interleaved obfuscated text and one-byte control codes; the engine prints the text with substitutions for common words and the player's name, prompts the user for a keyword, checks a fixed engine keyword table, then scans the NPC blob's ordinary keyword pairs and runs the selected response through the same interpreter. The interpreter also handles flag-driven branches, party-recruitment prompts, gold transactions, NPC-curse checks, GOTO labels, and two ways of asking the player a name.

Almost all observable conversation behaviour — the questions an NPC will ask, the gold they want, who joins the party, which quest flags get set — is encoded in the blob, not the engine. The engine itself is small and re-entrant: a single byte runner, a single keyword loop, a single loader. Anything richer than "speak text and accept keywords" is built up by combining the dozen or so control codes the runner recognises.

This spec describes the Talk command's entry path, the on-disk `.TLK` file structure, the in-memory keyword tree, the byte runner's complete dispatch table, the conversation flow including BYE handling and party-name prompts, and the hooks into the rest of the engine (text output, free-text input, the party module, and the quest/conversation flag stores).

## 2. The Talk command

The Talk command is one of the per-letter actions accepted by the town/dwelling/castle/keep mode loop; it is *not* available outdoors or in dungeons (there are no scheduled NPCs to address there) and is not available during combat. When the dispatcher routes the keystroke to the conversation overlay, the entry handler performs five steps before the engine proper takes over:

1. **Liveness gate.** A resident "can talk now" predicate decides whether a conversation is allowed at all. If the gate refuses (the most likely reasons are "in combat", "asleep", "starving", or "already in a conversation"), the command returns immediately without printing anything.

2. **Player position and facing.** The handler reads the party's tile coordinates and the current facing direction (a signed `dx, dy` pair written by the most recent movement command).

3. **NPC lookup at the facing tile.** The party's facing tile is `(player_x + dx, player_y + dy)`. The resident NPC-occupancy structure is consulted to find an NPC whose live tile matches. If no NPC is at that tile, the handler tests whether the tile is a *talk-through* tile — a small white-list of tile types representing shop counters, low fences, and similar pass-through barriers. If the tile is talk-through, the handler advances `(dx, dy)` once more and queries again. If still no NPC is found, the handler prints a "Nobody's here!" message and returns.

4. **Stub-state filter on the NPC's tile byte.** With an NPC located, the handler reads the NPC's current tile byte to detect two transient states. A "sleeping" tile prints a "Zzzzzz..." message and returns without entering the conversation engine. A "no response" tile (the NPC is praying, meditating, or otherwise unavailable) prints a "No response!" message and returns. Any other tile falls through.

5. **Dialog-index dispatch.** Each live NPC carries a one-byte *dialog index* loaded into RAM from the location's `.NPC` file when the scene was entered. The handler reads the dialog index for this NPC and hands it to the conversation engine, which uses it as the key for looking up the NPC's blob in the matching `.TLK` file.

The dialog index is a 1-based identifier shared between the `.NPC` and `.TLK` files of the same location class. Index 0 means "no dialogue at all" (the NPC is a non-speaker — a guard, a child too young to talk to, an animal). Index 1 is the universal *sentinel* in shipped data: no live NPC uses it, and the first slot in every `.TLK` file is reserved as a placeholder.

## 3. The four `.TLK` files

Conversation data is split across exactly four files, one per location class — `TOWNE.TLK`, `DWELLING.TLK`, `CASTLE.TLK`, `KEEP.TLK`. The class is determined by the current scene byte: it is `(scene_id − 1) >> 3`, mapping scenes `1..8` to towns, `9..16` to dwellings, `17..24` to castles, and `25..32` to keeps. The mapping is fixed; a given NPC's dialog index resolves only against the file matching their location class.

Each `.TLK` file contains a header (a fixed-size index of NPC entries) followed by the variable-size blob data. The file-level layout is:

| Region | Width / count | Meaning |
|--------|---------------|---------|
| NPC count | 2 bytes | Number of NPC slots in this file, including the sentinel slot. |
| Sentinel | 2 bytes | Always `0x0001`, the structural "NPC 1" sentinel. |
| Real NPC entries | 4 bytes each, `npc_count - 1` entries | One entry per real NPC, sorted by id. |
| Blob data | Remainder of file | Concatenated NPC blobs containing XOR-obfuscated text and control bytes. |

Each real NPC entry is four bytes:

| Entry field | Width | Meaning |
|-------------|-------|---------|
| Blob offset | 2 bytes | Absolute file offset of this NPC's blob. |
| NPC id | 2 bytes | One-based identifier matching `dialog_index`. |

The first four bytes of every file are read as the special pair `(npc_count, 0x0001)` — that is, the count occupies the slot a regular entry would use for `blob_offset`, and the sentinel `1` occupies the slot a regular entry would use for `npc_id`. After this leading pair, the remaining `npc_count − 1` entries describe real NPCs, sorted by ascending `npc_id`. The shipped files contain 48 (TOWNE), 15 (DWELLING), 40 (CASTLE), and 32 (KEEP) entries respectively.

The leading sentinel exists because dialog index `1` is never a real NPC in
the shipped rosters; the slot is structural. The runtime dispatcher does not
special-case index `1`, however. If corrupted or custom roster data assigns
dialog index `1` to a talkable NPC, the normal loader path matches the leading
sentinel id and reads the following entry's blob offset, effectively aliasing
index `1` to the first real NPC blob in that `.TLK` file. Binary-compatible
implementations should preserve that edge rather than treating index `1` like
index `0`. Live shipped NPCs use indices `2..npc_count`.

When the engine asks to talk to dialog index `D`, the loader reads the first 512 bytes of the file (enough to cover any class's header) into a working buffer, walks the entries linearly, and finds the entry whose `npc_id == D`. The matched entry's `blob_offset` field is then the file offset of the NPC's blob. The loader issues a second fixed-window read of 1024 bytes at that offset into the same buffer, overwriting the header with the blob. From the engine's perspective, the buffer now begins with the NPC's keyword tree.

The loader does not compute a runtime blob length from the next header entry.
For most shipped entries the fixed window contains the whole nominal blob span
plus some following file data that is never reached because the current blob's
own terminators stop the scans. The final `DWELLING.TLK` entry is the important
edge case: its nominal span to end-of-file is 1139 bytes, so the original engine
can only see the first 1024 bytes. A binary-compatible implementation should
preserve that fixed-window behavior rather than reading the full header span.

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

## 5. Keyword scan model

Keyword input uses two distinct scans, and they should not be collapsed into one data structure.

First, the engine checks a fixed reserved-keyword table that lives outside the `.TLK` files. That table has thirty-four entries. Five are functional conversation words: `NAME`, `JOB`, `WORK`, `BYE`, and `THANK`. The remaining entries are profanity/default rebuke words that route to a chastisement and bounded pause loop. This table is engine-owned vocabulary, not a per-NPC pointer table.

The fixed reserved table is:

| Index | Keyword | Behavior |
|---:|---|---|
| 0 | `NAME` | Run the Name entry with the fixed name prefix. |
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

3. **Empty-input shortcut.** If the player pressed Enter on an empty line, the engine prints `BYE\n\n`, runs the NPC's `Bye` entry through the byte runner, and returns to the caller. This is the most common way conversations end.

4. **Reserved-keyword scan.** The engine compares the input against the fixed thirty-four-entry reserved table. The match uses the same normalized string comparison style as ordinary keyword matching: typed input is uppercased, table keywords are compared by their NUL-terminated length, and a match accepts either exact end-of-input or a literal space immediately after the reserved word. `NAME` runs the Name entry with the engine's prefix, `JOB` and `WORK` run the fixed Job entry, `BYE` and `THANK` run the fixed Bye path, and the profanity/default entries print the rebuke path and run the bounded pause loop described below.

5. **Ordinary keyword scan.** If the reserved table does not handle the input, the engine walks the NPC blob's variable keyword/response pairs after the five mandatory leading entries. Each keyword is compared against the typed input using a bit-7-stripping, case-insensitive, space-boundary compare. The compare strips bit 7 from both sides (so obfuscated keyword bytes match plain ASCII) and folds both sides to upper case. A match requires the keyword to end cleanly and the typed input either to end at the same point or to have a literal space there; there is no substring search or fuzzy matching.

6. **Match found.** When an ordinary keyword matches, the engine runs the selected response stream through the byte runner. After the response finishes, the loop returns to step 1 to prompt for the next keyword.

7. **No match.** When both scans complete without a match, the engine prints `I cannot help thee with that.\n\n` and returns to step 1.

The match is space-boundary prefix matching, not arbitrary prefix matching. An NPC with separate `gran` and `grandpa` keywords resolves them independently: `grandpa` does not match `gran` because there is no boundary after `gran`, while `gran something` may match `gran` and leave the remaining words available to the surrounding handler. The keyword's actual length is whatever the NUL terminator says it is; the four-character "U4 convention" is a player-side discipline, not an engine constraint. The fifteen-character input limit on the typed side caps the longest entered phrase.

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

- **Nonzero high-bit-clear dictionary tokens.** These are *common-word dictionary tokens*. The byte is normalized into an index into the shared 128-entry common-word pointer table; the pointer targets a NUL-terminated word in the engine's common-word vocabulary, which is expanded inline into the output. See Section 8.
- **Bytes `0x9E..0x9F`.** These are GOTO-LABEL codes; their high bit is set and they participate in label dispatch. See Section 7.7.
- **Bytes `0xA0..0xFD` (high bit set, in the printable range).** These bytes enter the printable text path. The word-buffer flush strips the high bit before glyph output, with the `0x8E` print-mask toggle controlling whether the queued byte keeps that high bit long enough to act as a soft-break marker. See Section 7.1.
- **Bytes `0x80..0x9F` (with the exception of the GOTO range above).** Engine control codes. The dispatch table is in Sections 7.2–7.6.
- **Byte `0xFE`.** A multi-byte command introducer that behaves as an alias for `0x8C` (IF/ELSE).
- **Byte `0xFF`.** End-of-response. The byte runner flushes any pending word buffer and signals the keyword input loop to start a new iteration.

The byte runner has a small amount of per-conversation state: a "multi-byte command in progress" flag (set by `0x85`, `0x86`, `0x8C`, and `0xFE`), an argument-collection buffer for the multi-byte arguments, a print mask that may be toggled mid-stream, a few sentinel bytes used to suppress accidental double-quote artefacts, and a leading-space flag set by certain dictionary expansions. All of this state is reset at the start of each conversation.

### 7.1. Printable text emission

Bytes that classify as printable text (`0xA0..0xFD` with bit 7 stripped) are passed through a small word-boundary buffer and on to the text-output system's wrap-aware string printer. The buffer accumulates characters until it sees a soft break (a space byte) or a forced flush (a control code that performs one), at which point it emits the accumulated word.

The intermediate buffer exists for two reasons. First, the output respects the active text window's word-wrap rules — long sentences wrap at word boundaries rather than mid-word, even though the byte runner emits one byte at a time. Second, dictionary expansions (Section 8) need to merge with surrounding text *as a single word*; without the buffer, "the" expanded between two letters would be three separate writes that the wrap engine could not coalesce.

A leading-space flag may be set when an empty dictionary entry was encountered; the flag forces a single space to precede the next emitted character. This is how the dictionary handles word boundaries when the dictionary itself supplies a multi-word phrase.

The print mask is a one-byte output-mode flag. In its default state it preserves
the high bit on queued printable bytes until the word buffer flushes; this lets
encoded spaces and literal-newline bytes act as the buffer's soft-break and
forced-break sentinels. The `0x8E` toggle flips the mask's high bit. While the
mask is flipped, printable bytes are queued without the high bit, so they render
the same after flush but spaces and literal-newline characters inside the run do
not trigger the normal immediate flush. Shipped dialogue uses matched `0x8E`
pairs around short protected uppercase strings such as mantras, spell syllables,
Words of Power, passwords, and coordinate-letter notations so those runs are not
split by ordinary word-boundary handling.

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
| 0x8E  | PROTECT-RUN     | Toggle the print mask's high bit. Used in matched pairs around short literal runs whose spaces should not act as ordinary word-buffer breakpoints. |

`0x8B` does not directly affect the stream; it is a side-effect-only code that ensures the player's curse state is updated at a specific narrative beat. `0x8E` is the only code that mutates the byte runner's print-mask state, and is typically used in matched pairs (one to enter protected-run mode, one to leave it).

### 7.6. Branching, recruitment, and transactional codes

These codes are the most semantically rich. Several of them introduce a *multi-byte command*: the introducer code is followed by one or more argument bytes that are not interpreted as ordinary stream bytes but are collected into an argument buffer and consumed by the introducer's handler.

| Code  | Mnemonic        | Argument bytes following | Effect                                                                                                                          |
|-------|-----------------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------|
| 0x84  | ASK-PARTY-NAME  | none                    | Prompt the player to type a party member's name. The typed name is matched against each live member with a case-insensitive, bit-7-stripping compare; the match index (0 if no match) is available to the surrounding response. Used by the JOIN sequence and any "name a companion" prompt. |
| 0x85  | GOLD-PAYMENT    | three                   | Collect three argument bytes, mask each to seven bits, interpret them as ASCII decimal digits, and run the gold-payment routine against that three-digit amount. Used for tolls, bribes, and donations. |
| 0x86  | ACTION-DISPATCH | one                     | Collect one argument byte and mask it to seven bits. Letters `A..K` dispatch through one global fixed-slot action table; small values below the letter range set generic one-conversation signal flags. |
| 0x87  | SET-FLAG        | none (consumes follow-up) | Save the current stream pointer, walk the same keyword scan the input loop would walk against the next stream segment, run any matched response, and on no-match restore the saved pointer and continue. This is how an NPC inserts a conditional side-clause that recurses into another keyword's response. |
| 0x88  | ASK-WHO         | none                    | Variant of `0x84` used for "who is the X?" replies that produce a name. |
| 0x8C  | IF-ELSE         | one                     | Collect one argument byte (a flag identifier) and test the active scene's TALK branch flag for that bit. If set, branch into the *else* arm; if clear, fall through to the *then* arm. Arms are delimited by label codes (Section 7.7) so the runner skips the not-taken arm. |
| 0xFE  | IF-ELSE-ALT     | two                     | Multi-byte alternative branch form. Collects a moral-standing threshold byte and a target-label byte; if the shared moral-standing selector is at or above the threshold, the runner branches to the target label. |

The gold-payment introducer (`0x85`) interacts with conversation flow, not just emission: depending on whether the player can pay, the surrounding response may take different paths, so implementations need to model it as a re-entrant prompt that returns a result code.

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
label. It does not compare text, fold case, or normalize label ids. Labelled
records are part of the blob data, and shipped blobs commonly reuse the same
label byte multiple times: once as the control transfer and again as one or more
records inside the labelled block. Implementations must therefore preserve the
engine's scan discipline rather than treating label values as unique symbols in
a map.

Labelled blocks can do more than skip an IF/ELSE arm. They may open a scoped
sub-prompt, print a prompt such as "Your interest?", read another free-text
answer, scan the fixed reserved-word table, and then match label-scoped
keywords inside the labelled block. Within these blocks, a separator byte marks
labelled records, and the final label value also participates as an internal
sub-record separator. This is how an NPC can ask a follow-up question and route
the answer without returning to the top-level keyword list.

The scoped prompt is not a second copy of the top-level conversation loop.
Before reading its inner answer, it marks the reserved-word handler as already
inside a BYE-like prompt state. As a result, top-level reserved words such as
`NAME`, `JOB`, `WORK`, `BYE`, and `THANK` do not run their ordinary global
responses from inside the scoped prompt. Empty input is also local to the
scoped prompt: it prints the prompt's BYE line and reissues the scoped prompt
rather than ending the NPC conversation. After reserved-word handling is
suppressed or missed, matching continues against the label-scoped keyword
records. If no scoped keyword response can be run, control falls back through
the ordinary top-level keyword loop before the label handler returns to the
byte runner.

The label-response helpers use the same stream-driver result as ordinary
responses. A nested response that reaches a byte-runner stop condition reports
stop to the label handler; a response that simply reaches its NUL terminator
reports no-stop. After an unmatched scoped keyword or a NUL-ended nested
response, the handler opens the ordinary top-level keyword loop as the fallback
path rather than treating the scoped prompt as a permanent terminal state.

IF/ELSE branches use the same machinery for ordinary branch skips. The
IF-ELSE introducer chooses, based on the flag test, whether to fall through (the
*then* arm) or enter a labelled block that opens the *else* arm. The *then* arm
can end with its own label transfer past the else arm so that the runner does
not also execute it. The fifteen-label range is per blob, but labels are
byte-level flow markers, not globally unique names.

## 8. The common-word dictionary

A 128-entry pointer table targets a vocabulary of common English words shared across `.TLK` dialogue and the shop renderer. Dialogue dictionary tokens and shop phrase tokens apply different byte-range biases to the same logical table; the first dialogue token and shop token `0x80` both resolve to the first entry. Matching tokens are replaced *inline* by the corresponding word during emission.

The vocabulary is fixed and shipped with the engine (in the resident data segment, not the `.TLK` files). It contains common articles, pronouns, and connectives — `the`, `thou`, `of`, `and`, `you`, etc. — plus Britannian proper nouns such as `Blackthorn`, `Britannia`, `Lord British`, and the major-city names. Proper nouns in the table let many NPCs share canonical references without restating the full string in each blob.

Some dictionary entries are intentionally empty. An empty entry does not expand
to visible text; instead, it sets a "leading space needed" flag for the next
emission, which is the encoder's way of hinting at a word boundary without an
explicit space byte.

The exact word at each index belongs in a data spec, not here.

## 9. Conversation flow

Putting the pieces together, a single conversation runs through a fixed envelope:

1. **Entry.** The Talk command resolves an NPC and a dialog index. The conversation overlay loads the matching `.TLK` file's header, finds the right entry, and reads the blob.

2. **Opening preamble.** The entry preamble prints the fixed "Thou seest"
   lead-in, runs the Description entry (entry 2 of the five mandatory leading
   entries), and emits the blank-line spacing before the NPC greeting.

3. **Opening theft check and greeting.** After the description, the engine
   checks the active scene's TALK branch flag for this NPC and the shared
   stolen-action status/target helpers. If both indicate that the just-addressed
   NPC should react, it prints the stolen-action warning before continuing.
   Otherwise it opens the normal quote wrapper. The Greeting entry (entry 3 of
   the five mandatory leading entries) is then run through the byte runner. Most
   greetings end with `0x82` (END-STREAM) so the runner returns control without
   proceeding into the Job entry.

4. **Keyword loop.** Section 6's loop runs until the player exits.

5. **Bye sequence.** When the player exits (typed empty input, or a keyword response that ends the stream), the engine emits `BYE\n\n` and runs the Bye entry (entry 5 of the five mandatory leading entries).

6. **Cleanup.** A final per-conversation cleanup pass settles party-state side effects (gold transactions, transient conversation signals, recently-joined party members, mood adjustments), flushes any pending output, and returns to the caller.

The conversation engine itself is therefore single-shot — one Talk command produces one full envelope. The per-conversation state cluster (active multi-byte command, argument buffer, print mask, etc.) is reset at entry, so a previous conversation cannot bleed into a later one.

## 10. Hooks into the rest of the engine

The conversation engine touches several other systems through narrow, well-defined interfaces.

**Text output.** Every emission goes through the wrap-aware string printer described in `text-output.md`. The conversation overlay neither reaches around the print system nor maintains a parallel renderer. The active window is the main text window at conversation entry; some stub messages and prompts may switch windows briefly. Word-wrap behaviour, colour, and style flags are owned by the text-output system.

**Free-text input.** The keyword prompt and the ASK-PARTY-NAME / ASK-WHO prompts use the free-text input variant described in `input.md`. The engine clears the buffer-flush gate on entry to allow type-ahead and restores it on exit. The fifteen-character cap is the engine's invariant; the input pipeline itself does not know about it.

**Single-keystroke input.** The PAUSE and WAIT-KEY codes use the single-keystroke "wait for the next command" routine — the same one that drives the per-mode loops — but in *prompt mode*, with the prompt-character byte set so that the world tick is suppressed. Time does not pass while the player is reading.

**Party state.** The JOIN sequence is scripted by NPC responses that ask for a
party member name and then run action-dispatch side effects. The gold-payment
routine (triggered by `0x85`) and the action-dispatch handler (triggered by
`0x86`) also mutate party state. The gold-payment path decodes a three-digit
demand, debits party gold when affordable, and can run toll-style side effects
including a capped shared moral-standing selector increase when the
toll-progress counter reaches its milestone; it is not a confirmed per-virtue
standing writer. The action-dispatch path owns item grants, member changes,
generic signals, and mood-style side effects. These operations update the
party state described by the save-image, roster, item, karma, and chargen
specs. The conversation engine itself does not manage the party roster; it
only invokes those party operations.

**Quest flags and karma branches.** The `0x8C` IF-ELSE branch tests a bit in
the active scene's TALK branch-flag slot. The `0xFE` branch is different: it
consumes a moral-standing threshold and a target label, then branches when the
shared moral-standing selector is at or above that threshold. The
action-dispatch path can also set generic one-conversation signal flags or
fixed durable resource/item fields. Implementations should keep the per-scene
TALK branch bank, generic transient signals, durable save-backed flags, and
karma-threshold branch semantics separate. Branch bit indices `32` and above
build a zero mask rather than wrapping, so such tests read as clear and such
setters are no-ops. `quest-flags.md` owns the non-karma branch flag boundary,
while `karma.md` owns the moral-standing selector.

**Conversation cleanup sentinel.** Final conversation cleanup also consults a
shared town/conversation sentinel before running its stolen-action cleanup
envelope. Nonzero suppresses the cleanup pass entirely; zero can run the
stolen-action warning, play a fixed descending PC-speaker glissando, decrement
at most one pending conversation signal with a zero floor, or fall through to a
random gold adjustment and panel redraw. The visible warning and sound are not
themselves a confirmed virtue-standing write. The byte is produced by town
active-slot setup as a no-slot marker or one of three tracked town/Shadowlord
slot indices; this cleanup reader only performs a zero-versus-nonzero test, and
the current writer audit found no non-town writer. The same sentinel is visible
to the shop surcharge helper, so implementations should keep it as shared
mode/conversation state rather than creating a shop-only gate. `quest-flags.md`
owns the cleanup ordering and producer summary.

**Curse state.** The CURSE-CHECK code (`0x8B`) ticks the resident curse logic. The conversation engine simply prods the routine; the curse logic itself owns the per-character byte counters.

## 11. Boundaries and variations

The conversation runtime contract in this document is complete at byte-runner
depth. Remaining conversation-adjacent data packing questions, such as
persistent NPC interaction flag layout, are tracked by the owning format or
quest-state specs.

## 12. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The Talk command's entry handler — the liveness gate, facing-tile resolution, talk-through-tile fallback, sleeping/no-response stubs, and dialog-index dispatch — derived from `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md`.
- The byte runner's full dispatch table, the multi-byte-command machinery, the GOTO-label semantics, the printable-text path, and the per-conversation state cluster — derived from `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`.
- The gold-payment, action-dispatch, and karma-threshold branch handlers -- derived from `u5-decomp/functions/TALK_OVL/0x05B6_process_gold_payment.md`, `u5-decomp/functions/TALK_OVL/0x0682_action_command_dispatch.md`, and `u5-decomp/functions/TALK_OVL/0x0DBE_multi_byte_command_handler.md`.
- The Spyglass, Sextant, and Black Badge action-letter identities --
  cross-checked against the Z-stats special-item display path in
  `u5-decomp/functions/ZSTATS_OVL/0x099A_snapshot_inventory_to_overlay_ds.md`,
  `u5-decomp/functions/ZSTATS_OVL/0x0A3A_zstats_main.md`, and shipped `.TLK`
  action usage.
- The Talk-entry shop dispatch and shared shop caller context -- cross-checked
  against `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md`.
- The `.TLK` file loader, the four-class dispatch by scene byte, the header walk, the leading-pair-as-count encoding, and the 1024-byte blob read — derived from `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`.
- The keyword input loop, the empty-input-as-BYE shortcut, the fixed reserved-keyword table, the ordinary per-NPC keyword scan, the profanity rebuke/pause branch, and the no-match diagnostic -- derived from `u5-decomp/functions/TALK_OVL/0x0B04_conversation_loop.md`, `u5-decomp/functions/TALK_OVL/0x09D8_tlk_find_keyword_match.md`, `u5-decomp/functions/TALK_OVL/0x0A54_ask_party_join_logic.md`, and `u5-decomp/functions/ULTIMA_EXE/0x20FA_delay_with_int1c.md`, cross-checked against `u5-decomp/CORRECTIONS.md`.
- The labelled-block and scoped-prompt mechanics -- derived from
  `u5-decomp/functions/TALK_OVL/0x0C5C_tlk_seek_to_label_then_run.md`,
  `u5-decomp/functions/TALK_OVL/0x0BD4_ask_npc_name_loop.md`, and
  `u5-decomp/functions/TALK_OVL/0x0728_scan_to_byte.md`, cross-checked
  against `u5-decomp/functions/TALK_OVL/0x0A54_ask_party_join_logic.md`.
- The final cleanup pass, transient signal reconciliation, theft/covert-action
  hook, warning glissando, and shared sentinel cross-use -- derived from
  `u5-decomp/functions/TALK_OVL/0x111C_init_check_for_steal.md`,
  `u5-decomp/functions/TALK_OVL/0x1180_final_conversation_cleanup.md`, and
  `u5-decomp/functions/ULTIMA_EXE/0x43AE_pc_speaker_glissando.md`.
- The case-insensitive bit-7-stripping string-equality routine used by the JOIN-name compare and similar match operations — derived from `u5-decomp/functions/TALK_OVL/0x0000_strncmp_uppercase.md`.
- The on-disk `.TLK` file structure — header layout, blob obfuscation, mandatory leading entries, common-word dictionary substitution — derived from `u5-decomp/formats/npc-tlk-pth.md`.
- The resident common-word dictionary and its shop-renderer token order -- derived from `u5-decomp/formats/data-ovl.md`.
