# TLK files

Format specification for the four shared per-class dialogue files: `TOWNE.TLK`, `DWELLING.TLK`, `CASTLE.TLK`, and `KEEP.TLK`. These hold the per-NPC keyword-tree dialogue scripts for every speaking character in the game's named non-overworld locations. The file format is a small header table followed by a concatenated run of NPC blobs; the blobs are byte streams of obfuscated text interleaved with one-byte control codes that drive the conversation engine.

## 1. Overview

Ultima V's NPC dialogue is data-driven. The conversation engine — the runtime that prints what an NPC says, prompts the player for a keyword, runs branch logic on conversation flags, and accepts gold or party-join transactions — is the same small interpreter for every NPC. What distinguishes one NPC from another (name, answers, accepted keywords, gold demands, quest hints) lives entirely in the per-NPC blob. The four `.TLK` files are the on-disk store of those blobs.

The world's speaking NPCs are distributed across thirty-two named non-overworld locations: eight towns, eight dwellings, eight castles, and eight keeps. The locations partition by class, with one `.TLK` file per class. A given NPC's blob lives in exactly one of the four files, picked by the location class of the NPC's scene. Scene class is computed at runtime as `(scene − 1) >> 3`.

Each file begins with a fixed-size header table indexing the NPCs in that file, followed by the variable-size blob region. There is no per-file magic number, no version word, no padding, and no length prefix on individual blobs. The blobs are NUL-terminated subentry sequences using a uniform XOR obfuscation: every printable text byte has bit 7 set on disk, and the same bit lets the byte runner distinguish text bytes from control codes and dictionary indices without escape sequences.

The four files are paired one-for-one with their per-class NPC roster files (`*.NPC`) and per-class location data files (`*.DAT`). A live NPC carries a one-byte *dialog index* loaded from the `.NPC` file; the engine looks that index up in the matching `.TLK` to find the NPC's blob.

## 2. The four files and the scene-byte partition

The class-to-file mapping mirrors the `.NPC` and `.DAT` partition exactly:

| Scene byte range | Class    | File           |
|------------------|----------|----------------|
| 1–8              | Town     | `TOWNE.TLK`    |
| 9–16             | Dwelling | `DWELLING.TLK` |
| 17–24            | Castle   | `CASTLE.TLK`   |
| 25–32            | Keep     | `KEEP.TLK`     |

Scene byte zero is overworld; no `.TLK` file is loaded outdoors. Values outside `1..32` do not select one of the four dialogue files. That includes dungeon-class gameplay values and transient intro/combat-class markers, so the Talk command has no `.TLK` file to consult there.

The four files differ only in size and in the per-NPC content they carry; the on-disk format is uniform across them. A reader writing a viewer can treat the four files interchangeably.

## 3. Per-class NPC counts

Each file's first sixteen-bit word records the NPC count for that file. The shipped values are:

| File           | NPC count | Approximate file size |
|----------------|----------:|----------------------:|
| `TOWNE.TLK`    |        48 | ~26.8 KB              |
| `DWELLING.TLK` |        15 | ~7.9 KB               |
| `CASTLE.TLK`   |        40 | ~21.8 KB              |
| `KEEP.TLK`     |        32 | ~17.9 KB              |

The count is the number of real NPC blobs in the file; every id from `1` to the count addresses a real blob (Section 6). The format imposes no fixed cap; the count is a sixteen-bit unsigned integer used as a loop limit. The engine's working buffer holds five hundred twelve bytes of header data — enough for up to one hundred twenty-seven NPC entries plus the count word, well above the largest shipped count of forty-eight. The four files together hold one hundred thirty-five NPC blobs.

## 4. File-level layout

Every `.TLK` file is laid out as a fixed-size header followed by a concatenated run of variable-size NPC blobs:

| Region | Width / count | Meaning |
|--------|---------------|---------|
| NPC count | 2 bytes | Number of NPC entries in this file, and equally the number of blobs. |
| NPC entries | 4 bytes each, `npc_count` entries | One entry per NPC, ordered by ascending id `1..npc_count`. |
| Blob data | Remainder of file | Concatenated NPC blobs containing XOR-obfuscated text and control bytes. |

The count word is followed immediately by `npc_count` four-byte entries, each an
`(npc_id, blob_offset)` pair, in ascending id order starting at id `1`. The
header therefore occupies exactly `4 × npc_count + 2` bytes, and the first blob
begins at that offset: one hundred ninety-four in `TOWNE.TLK`, sixty-two in
`DWELLING.TLK`, one hundred sixty-two in `CASTLE.TLK`, one hundred thirty in
`KEEP.TLK`. Each of those numbers is exactly `4N + 2` for that file's count, so
the header ends where the blob region begins with no padding and no gap.

**Retraction.** Earlier revisions of this spec described the header the other way
round — four-byte `(blob_offset, npc_id)` pairs behind a leading degenerate pair
`(npc_count, 0x0001)`, with id `1` a structural sentinel and only `npc_count − 1`
real NPCs. That reading is withdrawn. It leaves two bytes of the header
unexplained in every file, leaves the final blob of every file unreferenced by
any header entry, and binds each id to the blob that actually belongs to the
previous id. The corrected reading accounts for every header byte, for every
blob, and matches the runtime lookup exactly.

The blob region begins immediately after the header. There is no separator, no length prefix per blob, and no end-of-region marker. Each blob's start is given by its header entry's `blob_offset` field. For static file inspection, the next NPC's `blob_offset` (or end-of-file for the last entry) gives the nominal span occupied by that entry in the concatenated region. At runtime, however, the engine does not use that span as a read length.

The header is sized so a single five-hundred-twelve-byte read covers any class's full header — even TOWNE's forty-eight-NPC header is only one hundred ninety-four bytes. The engine performs that fixed-size header read once, then issues a second fixed-window read of one thousand twenty-four bytes at the matched blob offset. The fixed window is the compatibility contract: for shorter blobs it reads past the blob's own end into following file data, which is harmless because the blob's own terminators stop every scan first. No shipped blob is long enough for the window to truncate it: the largest shipped nominal span is seven hundred four bytes (`TOWNE.TLK`), and the largest in the other three files are six hundred ninety-three, six hundred sixty-eight, and six hundred thirty-eight. The one-thousand-twenty-four-byte cap is therefore a compatibility contract that shipped data never exercises.

## 5. The HeaderEntry record

Each header entry is exactly four bytes:

| Field offset | Width   | Field        | Meaning                                                                                                                |
|--------------|---------|--------------|------------------------------------------------------------------------------------------------------------------------|
| `+0x00`      | 2 bytes | `npc_id`      | One-based identifier (little-endian unsigned word) matching `dialog_index` in the paired `.NPC` file's roster record. |
| `+0x02`      | 2 bytes | `blob_offset` | Absolute file offset (little-endian unsigned word) of this NPC's blob in the file.                                    |

Entries are sorted by `npc_id` ascending and run `1..npc_count` with no gaps.
The last entry's `blob_offset` is simply the start of the final blob; there is
no terminator entry.

Lookup is by linear scan: walk the entries in order, comparing each entry's `npc_id` against the desired dialog index, and on the first match take the word that immediately follows the matched id. The lookup is O(N) but N is small (forty-eight at most) and the header is in cache after the initial header read.

Note the field order, because it is what makes the lookup a two-word walk: the
id comes first and its blob offset second, so "match the id, then read the next
word" is the whole of the runtime algorithm.

## 6. The count word and dialog index 1

The first two bytes of every `.TLK` file are the NPC count, and the four bytes
after them are an ordinary header entry for `npc_id = 1`:

| Field | Value                                    |
|-------|------------------------------------------|
| Word 0 | NPC count for this file                 |
| Word 1 | `0x0001` — the id of the first NPC entry |
| Word 2 | that NPC's blob offset                   |

**Dialog index `1` is a real NPC, not a sentinel.** Each class file's id `1`
addresses an ordinary blob with a name, a description, a greeting, a job line, a
bye line and a keyword body, exactly like every other id, and shipped rosters do
point live NPCs at it: one occupied roster slot per class file carries dialog
index `1`. Real ids run `1..npc_count`, and the count word counts blobs, not
slots-plus-a-placeholder.

Earlier revisions of this spec described index `1` as a universal stub that "no
live NPC in any scene carries", with real NPCs starting at index `2` and the
first pair's offset slot reused to hold the count. All of that is withdrawn.
There is no sentinel entry, no overloaded offset slot, and no aliasing edge for
index `1`: the count is a plain two-byte prefix ahead of `npc_count` ordinary
entries.

An external reference describing the header as "a sorted list of pairs with no
count prefix" is wrong on both halves for the same reason: there *is* a count
prefix, and the pairs are `(id, offset)` rather than `(offset, id)`. The header
is `4 × N + 2` bytes total.

## 7. Per-NPC blob structure

A blob is the engine's record of everything one NPC can say. It is a stream of obfuscated bytes representing alternating *entries* — each entry is a NUL-terminated text run with embedded control codes — concatenated in a fixed structure:

1. **Five mandatory leading entries** in fixed order:
   1. **Name** — the NPC's display name (e.g. "Jennifer", "Lord British", "Mariah").
   2. **Description** — a short prose phrase used by the L-Look command (e.g. "a weathered girl", "a cleric of much wisdom").
   3. **Greeting** — what the NPC says when the player first opens conversation.
   4. **Job** — what the NPC says in response to the keyword `JOB`.
   5. **Bye** — what the NPC says when the player exits conversation.
2. **Variable-length keyword body** — zero or more (keyword, response) pairs.

Each leading entry is a NUL-terminated stream of post-obfuscation bytes. The five entries live at fixed *positions* within the blob (counted by NUL terminators from the blob start) but at variable *offsets* (because each entry's length depends on its content). A reader walks the blob from its start, consuming bytes through the runner — Name, Description, Greeting, Job, Bye — to reach the keyword body.

The keyword body is a sequence of paired NUL-terminated streams: a keyword string followed by a response stream. The keyword string is obfuscated text representing a word the player can type, e.g. `JOIN`, `QUEST`, `HORSE`. The response stream is the engine's reply and may contain any control codes the format supports.

Both sides use the same obfuscation and byte-runner semantics. Ordinary per-NPC keywords are matched against the player's typed input by a bit-7-stripping, case-insensitive space-boundary compare: the keyword must end at the match point, and the typed input must either end there or have a literal space there. There is no arbitrary substring or fuzzy match. There is no explicit "end of blob" sentinel; the runtime walks successive keyword/response pairs in the loaded 1024-byte window until the seek for the next keyword fails. Offline validators can use the next NPC's `blob_offset` (or end-of-file for the last blob) as the nominal file-region terminator, but runtime behavior is governed by the fixed loaded window. Shipped blobs carry between two and twenty-six keyword/response pairs.

The thirty-four-entry table involved in keyword input is not a `.TLK` blob pointer table. It is the engine's fixed reserved-word table for `NAME`, `JOB`, `WORK`, `BYE`, `THANK`, and profanity/default rebukes. The five mandatory leading entries are fixed blob ordinals used by the conversation envelope; variable keyword/response pairs fill the matchable body after them. The full scan order is covered in `systems/conversation.md`.

## 8. XOR obfuscation

Every printable text byte has bit 7 (`0x80`) set on disk. The byte runner strips bit 7 before emitting; equivalently, a reader recovers low-ASCII by XOR-ing each text byte with `0x80`. A literal space (`0x20`) is stored as `0xA0`; a literal `'A'` (`0x41`) as `0xC1`.

This is a one-bit flag, not encryption. Its consequence is that the high bit is *almost* a type tag: text bytes have bit 7 set (range `0xA0..0xFD`), the engine-control range `0x81..0x9F` plus `0xFE` and `0xFF` carry the dispatch codes, and everything below `0x81` is either the NUL terminator or a dictionary token. The format has no escape sequences — every byte is classified by value range alone.

The one place the high bit is a misleading tag is the top of the dictionary range. The runner's classifier is the single test "below `0x81`", so `0x80` — a byte with bit 7 set — is a dictionary token (index one hundred twenty-eight), not text and not a control code. Section 10 covers the range in full.

The cost is that the printable-text range is `0xA0..0xFD` on disk (`0x20..0x7D` after strip — ASCII space through right-curly-brace). Lower-case letters are reachable. The tilde character (`0x7E`/`0xFE`) is *not* reachable as ordinary text because its on-disk encoding collides with the multi-byte introducer.

NUL (`0x00`) terminates each entry. The runner treats `0x00` as end-of-entry and proceeds to the next entry in the blob's structure.

## 9. Control bytes

Bytes in the range `0x01..0x80` enter the dictionary-token path; the byte is
the index into the shared one-hundred-twenty-eight-entry common-word dictionary
published in `catalogs/common-word-dictionary.md`, and the word is expanded
inline. Bytes in the range `0x81..0xFF` are either engine control codes or
printable text (after bit-7 strip). The full dispatch table:

| Code   | Mnemonic            | Effect (concise)                                                                                                         |
|--------|---------------------|--------------------------------------------------------------------------------------------------------------------------|
| `0x80` | DICTIONARY-TOKEN    | Not a control code. `0x80` is the highest common-word dictionary token (index one hundred twenty-eight). The entry terminator is the NUL byte `0x00`. |
| `0x81` | PRINT-AVATAR-NAME   | Emit the player's saved name (the name chosen during character creation) into the output stream.                         |
| `0x82` | END-STREAM          | Stop the current stream and signal the caller "this stream is finished". Used to terminate the fixed leading entries.   |
| `0x83` | PAUSE               | Redraw the world view and wait for any key. After the key, refresh the party panel for every member.                    |
| `0x84` | RECRUIT-SPEAKER     | Recruit the speaking NPC into the active party. No player prompt: the engine reads the speaker's own name out of the blob's Name entry and matches it against the reserve portion of the character roster. The historical mnemonic "ASK-PARTY-NAME" is wrong; `0x84` reads no player input. |
| `0x85` | GOLD-PAYMENT        | Multi-byte introducer (three argument bytes follow): collect a gold amount and run the gold-payment routine.             |
| `0x86` | ACTION-DISPATCH     | Multi-byte introducer (one argument byte follows): collect a letter `A..K` for the global action table, or a small generic flag index. |
| `0x87` | KEYWORD-ALIAS       | No argument byte. Save the stream position, skip forward past the rest of the current record and past the whole record that follows it, run the record after that as a nested stream, then restore the saved position and continue — unless the nested stream signalled stop, which propagates. Used as a whole response body to make one keyword an alias for the next keyword's response. The historical mnemonic "SET-FLAG" is wrong; `0x87` writes no flag and performs no keyword matching. |
| `0x88` | ASK-WHO             | No argument byte. Ask the player to name someone and read a typed line. On a match against a live party member, set the active scene's branch-flag bit for the NPC currently speaking — this is the in-stream setter that `0x8C` tests — and print the affirmative acknowledgement; otherwise print the dismissive one. |
| `0x89` | STANDING-UP         | Raise the shared moral-standing selector by one, clamped at ninety-nine. Emits no text. |
| `0x8A` | STANDING-DOWN       | Lower the shared moral-standing selector by one, floored at zero. Emits no text. Earlier drafts described this code as a newline/panel-flush; that was a misreading of the printable path, which rewrites `0x8D` to the value `0x8A` *after* control-code dispatch is already past. |
| `0x8B` | CURSE-CHECK         | Run the resident curse-check routine. Used in dialog with cursed-item NPCs.                                              |
| `0x8C` | IF-ELSE             | Multi-byte introducer (one argument byte follows). The argument is the branch **target label**. Test the active scene's branch-flag bit for the NPC currently speaking; if clear, fall through in-stream; if set, transfer to that label (or, for the argument `0xFF`, end the response and return to the keyword prompt). |
| `0x8D` | LITERAL-NEWLINE     | Force-emit a literal newline through the text-output system.                                                              |
| `0x8E` | ALTERNATE-FONT      | Toggle the print mask's high bit. While flipped, printable bytes are queued without their high bit, which selects the alternate (runic) font at flush time and also stops the run's internal spaces and newlines from forcing word-buffer breaks. Used in matched pairs around mantras and Words of Power. |
| `0x8F` | WAIT-KEY            | Block for one keystroke. Unlike PAUSE, no redraw work is done.                                                            |
| `0x90` | LABEL-RECORD        | Labelled-block record separator used by the label-search and scoped-prompt machinery. It is data structure, not ordinary printable text. |
| `0x91`-`0x9F` | LABEL / scoped prompt | Up to fifteen label bytes per blob. Encountered in a response stream, they enter the label handler; inside labelled blocks, repeated label bytes mark records and sub-records. Empty input inside the scoped prompt is local to that prompt, and top-level reserved words are suppressed there before label-scoped keyword matching. |
| `0xFE` | IF-ELSE-ALT         | Multi-byte introducer (two argument bytes follow): moral-standing threshold branch with a target label byte.              |
| `0xFF` | END-OF-RESPONSE     | Flush the word buffer and return control to the keyword input loop.                                                      |

Multi-byte introducers (`0x85`, `0x86`, `0x8C`, `0xFE`) consume one or more bytes following the introducer as arguments, not as ordinary stream bytes. The number of argument bytes is fixed per introducer (Section 9.1 below). Argument bytes themselves are passed through to the introducer's handler as literal argument values; they are not subject to bit-7 strip or dictionary expansion.

The full runtime semantics of each code — how PAUSE redraws, how IF-ELSE walks its arms, how RECRUIT-SPEAKER interacts with party state — belong in `systems/conversation.md`. This format spec restricts itself to the on-disk arrangement and the byte-by-byte type tags.

A label is *declared* by the two-byte record marker `0x90 <label>`. A transfer
to label `L` rewinds to the start of the blob and scans forward for the byte
`0x90`, checks whether the byte after it equals `L`, and resumes the stream
immediately past `L` on a match; otherwise it keeps scanning. This is a
byte-for-byte scan with no case folding and no id normalisation, and it is the
same mechanism used by the `0x91`..`0x9F` GOTO codes and by an `0x8C` branch
that is taken.

Label bytes are not unique declarations. Shipped blobs often contain repeated
instances of the same value because a response can transfer into a labelled
block and the block itself uses the same byte value to mark its records. A
decoder should preserve order and byte values rather than folding labels into a
dictionary keyed only by label id. In shipped content the value `0x9F` is
conventionally the blob's final record marker.

### 9.1 Multi-byte introducer argument counts

| Introducer | Argument bytes | Argument purpose                                                                                |
|------------|----------------|-------------------------------------------------------------------------------------------------|
| `0x85`     | 3              | Three ASCII digit bytes encoding a decimal gold amount for the gold-payment prompt.              |
| `0x86`     | 1              | Letter `A..K` selecting a global fixed-slot action, or a small numeric generic flag index.       |
| `0x8C`     | 1              | Branch **target label** taken when the tested flag is set, or `0xFF` meaning "end the response and return to the keyword prompt". It is *not* a flag identifier: the bit tested is chosen by the engine (the speaking NPC's roster slot), never by the script. |
| `0xFE`     | 2              | Moral-standing threshold byte and target-label byte for a karma-conditional branch.             |


For `0x85`, each of the three argument bytes is masked to seven bits and
interpreted as one ASCII decimal digit. The resulting three-digit number is the
gold amount tested against and deducted from the party. For `0x86`, the argument
byte is also masked to seven bits; letters `A..K` dispatch through one global
letter table, while small values below the letter range set generic
one-conversation signal flags.
The table is not per-NPC. Per-NPC variation comes from which argument byte a
given NPC's blob emits.

At the clean format level the letter values are stable bytecode arguments. The
runtime owns the effects: currently public mappings include food, gold, keys,
gems, torches, Grapple/Klimb gear, magic-carpet stock, and skull/special-key
stock, plus the Spyglass, Sextant, and Black Badge special-item flags. See
`systems/conversation.md` and `systems/quest-flags.md` for the behavioral table.

Shop entry is not encoded as a `.TLK` keyword-response control stream. When a
Talk target is a shop-capable resident, a high-range `.NPC` dialog-index value
can route to the shop system before loading the resident's normal `.TLK` blob.
`formats/npc.md` owns those trigger byte values, and `systems/shops.md` owns
the semantic shop-kind dispatch and current shop-instance resolution.

### 9.2 The `0xA2` quote sentinel

`0xA2` is not a control code. It is the normal obfuscated form of the printable
double quote (`"`). The byte runner remembers the previous emitted printable
byte and suppresses a quote when the previous printable byte was also a quote.
This collapses adjacent quoted segments from `""` to a single visible quote.
Implementations targeting byte-exact output should reproduce this suppression
to avoid doubled quotes in the rendered text.

## 10. The common-word dictionary substitution

A stream byte in the range `0x01`..`0x80` is a *common-word dictionary token*.
The byte is the index itself into the shared one-hundred-twenty-eight-entry
dictionary, whose full contents are published as
`catalogs/common-word-dictionary.md`. The referenced word is emitted inline as
if it had been written out as ordinary text.

Note the top of the range. The runner classifies with a single comparison: a
byte below `0x81` takes the dictionary path, everything from `0x81` upward takes
the control-code or printable path. Token `0x80` therefore has bit seven **set**
and is still a dictionary token - it is index one hundred twenty-eight. The
older framing "bit seven clear means dictionary token" is off by one at that
boundary, and shipped blobs do use token `0x80`.

The pointer run and its packed string pool live in the resident data image
described in `formats/data-ovl.md`, not in the `.TLK` files, so a renderer needs
the dictionary as a sibling input. The same physical table serves the shop bark
renderer under a different byte bias; see `catalogs/common-word-dictionary.md`
section 2 and `formats/shoppe-dat.md` section 5.

### 10.1 Emission order and spacing

Expansion happens *during* text emission, one character at a time through the
same word-buffer queue that handles ordinary text bytes, so expansions interact
correctly with word-wrap and the active text window. There is no pre-pass that
flattens a blob into a string.

The order for one dictionary token is fixed:

1. Emit a single space. This happens for **every** dictionary token, whether or
   not the entry is populated.
2. Emit the entry's characters, if any.
3. If the entry was populated, arm a *pending space* flag.

The pending-space flag is consumed - and cleared - by the next **printable text
byte**, which emits one space ahead of itself. It is not consumed by a following
dictionary token, because the token path neither reads nor clears the flag; a
run of adjacent tokens therefore produces exactly one space between words and
leaves the flag armed for whatever printable byte comes next.

Two consequences worth stating because earlier drafts of this spec had them
backwards:

- Empty entries are **not** word-boundary sentinels, and they do **not** set the
  pending-space flag. An empty entry emits the leading space and then the raw
  token byte as a literal character. See
  `catalogs/common-word-dictionary.md` section 3; no shipped content reaches
  this path.
- The pending-space flag is armed by a **successful** expansion, not by an empty
  one.

Punctuation is not special-cased. A token that should be followed immediately by
a comma is handled in the content, not the renderer: the vocabulary contains
punctuation-bearing entries such as `thee,` for exactly that purpose.

## 11. Engine-reserved keywords

The conversation engine first checks a fixed engine-side reserved-keyword table before
falling through to ordinary per-NPC keyword matching. This table has thirty-four
entries and is not stored in the `.TLK` files. Five entries have functional
conversation meanings: `NAME`, `JOB`, `WORK`, `BYE`, and `THANK`. `JOB` and
`WORK` are aliases for the Job entry; `BYE` and `THANK` are aliases for the Bye
entry. The remaining entries are profanity/default cases that route to the
engine's rebuke path.

`JOIN` and `WHO ART THOU` are not entries in this reserved table. Joining and
"ask who" flows are scripted by ordinary NPC responses and their control codes,
not by a reserved keyword match.

## 12. Worked example — `TOWNE.TLK`'s leading bytes

The first two bytes of `TOWNE.TLK` are the count word `0x0030` (forty-eight). A reader interprets this as "forty-eight NPC entries and forty-eight blobs."

The next four bytes are the first header entry: the NPC id `0x0001` followed by that NPC's blob offset. Subsequent four-byte entries cover NPC ids two, three, and so on, sorted ascending, up to the last NPC at id `0x0030` (forty-eight). The header ends at byte one hundred ninety-four (`4 × 48 + 2`), which is also the value in the first entry's offset field.

After the header — at the offset given by the first entry — the first NPC's blob begins. The first byte is an obfuscated text byte encoding the first letter of the NPC's name. `TOWNE.TLK`'s id-1 blob is "Zachariah", so its first byte is `0xDA` (obfuscated `'Z'`); `KEEP.TLK`'s "Mariah" blob starts with `0xCD` (obfuscated `'M'`). Subsequent bytes encode the rest of the name, terminated by NUL.

After the Name entry's NUL comes Description, then Greeting, then Job, then Bye, each NUL-terminated. Greetings typically carry control bytes such as PRINT-AVATAR-NAME or END-STREAM. After the five leading entries comes the keyword body: a keyword string such as `JOIN`, a NUL, the response stream, an END-OF-RESPONSE marker, and so on for additional pairs.

A reader can sanity-check a `.TLK` decoder by:

1. Reading the first two bytes as `npc_count` and confirming the first entry's id word equals `0x0001`.
2. Reading `npc_count × 4` more bytes as header entries and confirming the NPC ids are sorted ascending and run `1..npc_count` with no gaps.
3. Confirming that `4 × npc_count + 2` equals the first entry's `blob_offset`. If it does not, the reader has the two words of an entry swapped.
4. Picking any entry, seeking to its `blob_offset`, reading until end-of-response, and XOR-ing the printable-range bytes with `0x80` to recover ASCII.
5. Confirming the recovered text begins with a recognisable NPC name (e.g. "Mariah", "Jennifer", "Blackthorn", "Chuckles"), and that the last entry's blob is a real named NPC rather than an unreferenced tail.
6. Scanning nominal blob spans against the 1024-byte runtime window. No shipped
   span reaches it; the largest is seven hundred four bytes.

## 13. Cross-references

- The conversation engine that consumes this format — the byte runner's full semantics, the keyword input loop, the multi-byte command machinery, the GOTO-label semantics, and the per-conversation state — `systems/conversation.md`.
- The published contents of the shared common-word dictionary, its two token biases, its empty slots, and its validation invariants — `catalogs/common-word-dictionary.md`.
- The per-class NPC roster file format providing the `dialog_index` field for each live NPC — `formats/npc.md` (a separate format spec).
- The per-class location data file format whose tile grids host the live NPCs — `formats/location-dat.md`.
- The text-output pipeline that ultimately renders the emitted bytes — `systems/text-output.md`.
- The free-text input pipeline that accepts the player's typed keyword — `systems/input.md`.
- The runtime flag stores consumed by IF-ELSE and action-dispatch codes — `systems/quest-flags.md`; durable save-backed NPC and quest fields are cross-referenced from `formats/saved-gam.md`.
- The party module whose state is mutated by the JOIN sequence and the gold-payment routine — described under `systems/conversation.md` cross-links.
- The scene-byte lifecycle trace that distinguishes town-family scene ids from dungeon, intro, and combat-class markers — `u5-decomp/notes/critical_state_lifecycles.md`.

## 14. Validation Boundary

The format is verified by direct byte inspection at the file-structure level
(header layout, NPC counts, `(id, offset)` entry order, blob alignment,
fixed-window blob load) and by behavioural inspection at the byte-runner level (control-byte
dispatch, dictionary substitution, obfuscation). The file-structure contract is
complete in this spec; conversation runtime behavior is tracked in
`systems/conversation.md`.

## 15. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of the four `.TLK` files, the per-class NPC counts, the obfuscation verification against decoded names, and the control-byte prevalence analysis — `u5-decomp/formats/npc-tlk-pth.md`. That note's leading-pair-as-count reading of the header is superseded; see the retraction in Section 4.
- The corrected header contract — `(npc_id, blob_offset)` entry order, ids running `1..npc_count`, the `4N + 2` header size that matches the first blob offset in all four files, and the consequent withdrawal of the "index 1 sentinel" — re-derived directly from the shipped `.TLK` files and from the runtime header walk in `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`, cross-checked against the shipped `.NPC` dialog-index arrays and against the sprite-class description strings of `LOOK2.DAT`.
- The conversation-engine entry point — the dialog-index dispatch from the Talk command, the dispatch into the file loader, and the conversation envelope — `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md`.
- The `.TLK` file loader — the four-class file dispatch by scene byte, the header read into a working buffer, the linear header walk for the matched NPC id, and the second blob read at the matched offset — `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`.
- The byte runner's full dispatch table — the control-code semantics, the multi-byte command machinery, the dictionary substitution, the GOTO-label search, and the per-conversation state cluster — `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`.
- The labelled-block separator and scoped-prompt record mechanics —
  `u5-decomp/functions/TALK_OVL/0x0C5C_tlk_seek_to_label_then_run.md`,
  `u5-decomp/functions/TALK_OVL/0x0BD4_ask_npc_name_loop.md`, and
  `u5-decomp/functions/TALK_OVL/0x0728_scan_to_byte.md`.
- The multi-byte command handlers for gold payment, action dispatch, and karma-threshold branching — `u5-decomp/functions/TALK_OVL/0x05B6_process_gold_payment.md`, `u5-decomp/functions/TALK_OVL/0x0682_action_command_dispatch.md`, and `u5-decomp/functions/TALK_OVL/0x0DBE_multi_byte_command_handler.md`.
- The special-item identities named for action-dispatch letter arguments are
  cross-checked against the Z-stats special-item display path:
  `u5-decomp/functions/ZSTATS_OVL/0x099A_snapshot_inventory_to_overlay_ds.md`
  and `u5-decomp/functions/ZSTATS_OVL/0x0A3A_zstats_main.md`.
- The keyword input loop, reserved-keyword table, ordinary keyword scan, and profanity/default branch -- `u5-decomp/functions/TALK_OVL/0x0B04_conversation_loop.md`, `u5-decomp/functions/TALK_OVL/0x09D8_tlk_find_keyword_match.md`, `u5-decomp/functions/TALK_OVL/0x0A54_ask_party_join_logic.md`, and the summary correction in `u5-decomp/CORRECTIONS.md`.
- The case-insensitive bit-7-stripping string-equality routine used by the keyword match and the JOIN-name compare — `u5-decomp/functions/TALK_OVL/0x0000_strncmp_uppercase.md`.
- The resident common-word dictionary and shop-side use of the same logical token order — `u5-decomp/formats/data-ovl.md`.
- The 2026-08-22 retrace that corrected the `0x87`, `0x88`, `0x89`, `0x8A`, and `0x8E` control-code rows, the `0x8C` argument role, the dictionary token range, and the dictionary emission/spacing order — `u5-decomp/notes/talk_group_retrace_2026-08-22.md`, with the supporting per-function notes `u5-decomp/functions/TALK_OVL/0x0E78_ask_who_join_loop.md`, `u5-decomp/functions/TALK_OVL/0x0D42_set_npc_quest_flag.md`, and `u5-decomp/functions/TALK_OVL/0x0D7A_test_npc_quest_flag.md`.
- The conversation-system spec covering the runtime semantics this format spec only references — `u5-spec/systems/conversation.md`.
