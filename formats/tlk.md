# TLK files

Format specification for the four shared per-class dialogue files: `TOWNE.TLK`, `DWELLING.TLK`, `CASTLE.TLK`, and `KEEP.TLK`. These hold the per-NPC keyword-tree dialogue scripts for every speaking character in the game's named non-overworld locations. The file format is a small header table followed by a concatenated run of NPC blobs; the blobs are byte streams of obfuscated text interleaved with one-byte control codes that drive the conversation engine.

## 1. Overview

Ultima V's NPC dialogue is data-driven. The conversation engine — the runtime that prints what an NPC says, prompts the player for a keyword, runs branch logic on quest flags, and accepts gold or party-join transactions — is the same small interpreter for every NPC. What distinguishes one NPC from another (name, answers, accepted keywords, gold demands, quest hints) lives entirely in the per-NPC blob. The four `.TLK` files are the on-disk store of those blobs.

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

Scene byte zero is overworld; no `.TLK` file is loaded outdoors. Scene bytes above thirty-two are dungeon and combat states; the Talk command is not available in those states, so no `.TLK` is consulted there either.

The four files differ only in size and in the per-NPC content they carry; the on-disk format is uniform across them. A reader writing a viewer can treat the four files interchangeably.

## 3. Per-class NPC counts

Each file's first sixteen-bit word records the NPC count for that file. The shipped values are:

| File           | NPC count | Approximate file size |
|----------------|----------:|----------------------:|
| `TOWNE.TLK`    |        48 | ~26.8 KB              |
| `DWELLING.TLK` |        15 | ~7.9 KB               |
| `CASTLE.TLK`   |        40 | ~21.8 KB              |
| `KEEP.TLK`     |        32 | ~17.9 KB              |

The counts include the universal sentinel slot at index one (Section 6); the number of *real* NPCs per file is therefore one less than the count word. The format imposes no fixed cap; the count is a sixteen-bit unsigned integer used as a loop limit. The engine's working buffer holds five hundred twelve bytes of header data — enough for up to one hundred twenty-eight NPC entries, well above the largest shipped count of forty-eight.

## 4. File-level layout

Every `.TLK` file is laid out as a fixed-size header followed by a concatenated run of variable-size NPC blobs:

| Region | Width / count | Meaning |
|--------|---------------|---------|
| NPC count | 2 bytes | Total NPC slots in the file, including the sentinel. |
| Sentinel | 2 bytes | Always `0x0001`. |
| Real NPC entries | 4 bytes each, `npc_count - 1` entries | One entry per real NPC, sorted by id ascending. |
| Blob data | Remainder of file | Concatenated NPC blobs containing XOR-obfuscated text and control bytes. |

The first four bytes form a special leading pair `(npc_count, 0x0001)`: the count value occupies the slot a regular entry would use for its blob offset, and the sentinel `1` occupies the slot a regular entry would use for its NPC id. After this pair, the remaining `npc_count − 1` entries describe real NPCs, sorted by ascending NPC id starting at id `2`.

The blob region begins immediately after the header. There is no separator, no length prefix per blob, and no end-of-region marker. Each blob's start is given by its header entry's `blob_offset` field; each blob ends at an end-of-response control byte (or the start of the next blob, or end of file). Typical blobs run a few hundred bytes; the longest shipped blobs are around five hundred bytes.

The header is sized so a single five-hundred-twelve-byte read covers any class's full header — even TOWNE's forty-eight-NPC header is only one hundred ninety-two bytes. The engine performs that fixed-size header read once, then issues a second read of up to one thousand twenty-four bytes at the matched blob offset.

## 5. The HeaderEntry record

Each header entry is exactly four bytes:

| Field offset | Width   | Field        | Meaning                                                                                                                |
|--------------|---------|--------------|------------------------------------------------------------------------------------------------------------------------|
| `+0x00`      | 2 bytes | `blob_offset` | Absolute file offset (little-endian unsigned word) of this NPC's blob in the file.                                    |
| `+0x02`      | 2 bytes | `npc_id`      | One-based identifier (little-endian unsigned word) matching `dialog_index` in the paired `.NPC` file's roster record. |

Entries are sorted by `npc_id` ascending. Real entries start at `npc_id = 2`; the sentinel entry at the head of the file carries `npc_id = 1` and a `blob_offset` field reused as the NPC count. The last entry's `blob_offset` is simply the start of the final blob; there is no terminator entry.

Lookup is by linear scan: walk the entries in order, comparing each entry's `npc_id` against the desired dialog index, stop at the first match. The lookup is O(N) but N is small (forty-eight at most) and the header is in cache after the initial header read.

## 6. The leading pair and NPC 1 sentinel

The first four bytes of every `.TLK` file form a special pair:

| Field | Value                            |
|-------|----------------------------------|
| Word 0 | NPC count for this file         |
| Word 1 | `0x0001` — the sentinel NPC id  |

Two design facts make this work. First, dialog index `1` is reserved as a universal stub — no live NPC in any scene carries dialog index `1`. Real NPCs use dialog indices `2..npc_count`. The convention is enforced by the `.NPC` file content, not by the format. Second, because the sentinel NPC is never resolved, its header entry's `blob_offset` slot is structurally unused; the format reuses it to hold the NPC count.

This is a small space optimisation. An external reference describing the header as "a sorted list of `(offset, id)` pairs with no count prefix" is partially correct: the layout *is* a sorted list of pairs, but the first pair's offset slot is overloaded as the count. The header is `4 × N` bytes total, with the first four bytes serving the dual count/sentinel role and the remaining `4 × (N − 1)` bytes covering the real NPC entries.

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

Both sides use the same obfuscation and byte-runner semantics. Keywords are matched against the player's typed input by a bit-7-stripping, case-insensitive space-boundary compare: the keyword must end at the match point, and the typed input must either end there or have a literal space there. There is no arbitrary substring or fuzzy match. There is no explicit "end of blob" sentinel; the engine walks the keyword pointer table populated at load time and stops when it has visited each scan slot. A reader can use the next NPC's `blob_offset` (or end-of-file for the last blob) as the implicit terminator.

The conversation engine reserves thirty-four pointer-table slots for the in-memory scan. The five mandatory leading entries are fixed blob ordinals used by the conversation envelope; variable keyword/response pairs fill the matchable body after them. The exact slot-population routine is engine-side and remains open, but shipped content stays within the thirty-four-slot scan ceiling. The pointer-table semantics are covered in `systems/conversation.md`.

## 8. XOR obfuscation

Every printable text byte has bit 7 (`0x80`) set on disk. The byte runner strips bit 7 before emitting; equivalently, a reader recovers low-ASCII by XOR-ing each text byte with `0x80`. A literal space (`0x20`) is stored as `0xA0`; a literal `'A'` (`0x41`) as `0xC1`.

This is a one-bit flag, not encryption. Its consequence is that the high bit serves as a *type tag*: bit 7 set means text byte (in the range `0xA0..0xFD`), bit 7 clear means dictionary index or NUL terminator (`0x01..0x9D` or `0x00`), and the engine-control range `0x80..0x9F` plus `0xFE` and `0xFF` carry the dispatch codes. The format has no escape sequences — every byte is classified by value range alone.

The cost is that the printable-text range is `0xA0..0xFD` on disk (`0x20..0x7D` after strip — ASCII space through right-curly-brace). Lower-case letters are reachable. The tilde character (`0x7E`/`0xFE`) is *not* reachable as ordinary text because its on-disk encoding collides with the multi-byte introducer.

NUL (`0x00`) terminates each entry. The runner treats `0x00` as end-of-entry and proceeds to the next entry in the blob's structure.

## 9. Control bytes

Bytes with bit 7 clear (excluding NUL) are dictionary indices in the range `0x01..0x9D`; the engine looks them up in a 256-entry pointer table and expands them inline. Bytes with bit 7 set in the range `0x80..0xFF` are either engine control codes or printable text (after bit-7 strip). The full dispatch table:

| Code   | Mnemonic            | Effect (concise)                                                                                                         |
|--------|---------------------|--------------------------------------------------------------------------------------------------------------------------|
| `0x80` | (NUL on disk)       | The high-bit-clear NUL is the entry terminator; `0x80` itself is unused.                                                 |
| `0x81` | PRINT-AVATAR-NAME   | Emit the player's saved name (the name chosen during character creation) into the output stream.                         |
| `0x82` | END-STREAM          | Stop the current stream and signal the caller "this stream is finished". Used to terminate the fixed leading entries.   |
| `0x83` | PAUSE               | Redraw the world view and wait for any key. After the key, refresh the party panel for every member.                    |
| `0x84` | ASK-PARTY-NAME      | Prompt the player to type a party member's name. Used by the JOIN sequence and similar "name a companion" prompts.       |
| `0x85` | GOLD-PAYMENT        | Multi-byte introducer (three argument bytes follow): collect a gold amount and run the gold-payment routine.             |
| `0x86` | ACTION-DISPATCH     | Multi-byte introducer (one argument byte follows): collect a letter `A..K` and dispatch to the per-letter action handler. |
| `0x87` | SET-FLAG            | Save stream pointer, walk the keyword scan against the next stream segment, run any matched response, restore on miss.   |
| `0x88` | ASK-WHO             | Variant of ASK-PARTY-NAME used for "who is the X?" replies that produce a name.                                          |
| `0x89` | (unused)            | Falls through to the printable-text path; effectively a no-op.                                                           |
| `0x8A` | PANEL-NEWLINE       | Mark a newline boundary that also flushes the party-panel state.                                                          |
| `0x8B` | CURSE-CHECK         | Run the resident curse-check routine. Used in dialog with cursed-item NPCs.                                              |
| `0x8C` | IF-ELSE             | Multi-byte introducer (one argument byte follows): test the corresponding NPC quest flag and branch.                     |
| `0x8D` | LITERAL-NEWLINE     | Force-emit a literal newline through the text-output system.                                                              |
| `0x8E` | TOGGLE-MASK         | XOR the print-mask byte with `0x80`. Toggles between two output modes (see `systems/conversation.md`).                   |
| `0x8F` | WAIT-KEY            | Block for one keystroke. Unlike PAUSE, no redraw work is done.                                                            |
| `0x91`–`0x9F` | LABEL targets | Up to fifteen named labels per blob, addressed as GOTO targets by the label-search routine.                              |
| `0xFE` | IF-ELSE-ALT         | Multi-byte introducer (two argument bytes follow): alternative form of IF-ELSE indexing into a wider state cluster.       |
| `0xFF` | END-OF-RESPONSE     | Flush the word buffer and return control to the keyword input loop.                                                      |

Multi-byte introducers (`0x85`, `0x86`, `0x8C`, `0xFE`) consume one or more bytes following the introducer as arguments, not as ordinary stream bytes. The number of argument bytes is fixed per introducer (Section 9.1 below). Argument bytes themselves are passed through to the introducer's handler as raw byte values; they are not subject to bit-7 strip or dictionary expansion.

The full runtime semantics of each code — how PAUSE redraws, how IF-ELSE walks its arms, how ASK-PARTY-NAME interacts with party state — belong in `systems/conversation.md`. This format spec restricts itself to the on-disk arrangement and the byte-by-byte type tags.

### 9.1 Multi-byte introducer argument counts

| Introducer | Argument bytes | Argument purpose                                                                                |
|------------|----------------|-------------------------------------------------------------------------------------------------|
| `0x85`     | 3              | Encode gold amount and flags for the gold-payment prompt.                                       |
| `0x86`     | 1              | Letter `A..K` selecting the per-letter action verb.                                             |
| `0x8C`     | 1              | NPC quest-flag identifier; tested against the per-NPC flag cluster.                             |
| `0xFE`     | 2              | Wider-state-cluster index pair; tested against an external state cluster.                       |

The exact encoding of the three argument bytes for `0x85` is not pinned down in the format; an implementation must inspect the gold-payment handler. The single argument byte for `0x86` is a printable letter (typically `'A'` through `'K'`) drawn from the printable-text range without obfuscation — that is, the argument byte is consumed *after* the introducer's bit-7 transparency, so the on-disk byte may already carry the high bit set or clear depending on the per-NPC blob's authoring convention.

Shop entry is not encoded as a `.TLK` keyword-response control stream. When a
Talk target is a shop-capable resident, a high-range `.NPC` dialog-index value
can route to the shop system before loading the resident's normal `.TLK` blob.
`formats/npc.md` owns those trigger byte values, and `systems/shops.md` owns
the semantic shop-kind dispatch and current shop-instance resolution.

### 9.2 The `0xA2` quote sentinel

The byte runner inspects each incoming byte against the previous byte to detect repeated `0xA2` sequences. A `0xA2` byte (which decodes to `"`) immediately following another `0xA2` is silently suppressed. The most likely interpretation is paired-quote artefact suppression — the `0x82` END-STREAM emit followed by a newly-opened quoted phrase would otherwise produce a doubled close-quote character. Implementations targeting byte-exact output should reproduce this suppression to avoid doubled quotes in the rendered text.

## 10. The common-word dictionary substitution

Bytes in the range `0x01..0x9D` (high bit clear, NUL excluded) are *common-word dictionary indices*. Each such byte is used as a sixteen-bit pointer-table lookup: the engine indexes a 256-entry near-pointer table, fetches the pointer at slot `byte`, and emits the NUL-terminated word at the pointed-to address inline as if it had been written out as ordinary text.

The 256-entry pointer table sits in the engine's resident data region (technically in `DATA.OVL`, the resident data slab). The vocabulary it targets — the actual word strings — is concatenated immediately afterwards as a run of NUL-terminated strings. The vocabulary contains common English articles, pronouns, and connectives such as `the`, `thou`, `of`, `and`, `you`, plus Britannian proper nouns such as `Blackthorn`, `Britannia`, `Lord British`, and the major-city names. Proper nouns in the table let many NPCs share canonical references without restating the full string in each blob.

Of the 256 pointer-table slots, only roughly the first one hundred fifty are populated; the remaining slots target a NULL pointer. When the byte runner encounters a NULL slot, it does not abort — instead, it sets a "leading space needed" flag that is consumed by the next emitted character. This is the format's way of indicating a soft word boundary without consuming a byte for an explicit space. The flag is reset after the next character is emitted.

The dictionary substitution happens *during* text emission, character by character. There is no pre-pass that expands a blob into a flat string; each dictionary index is expanded on the fly through the same word-buffer queue that handles ordinary text bytes, so dictionary expansions interact correctly with word-wrap, the active text window, and the leading-space flag.

The exact word at each dictionary index belongs in a separate data spec (the resident `DATA.OVL` content); this format spec records only the substitution mechanism. Implementations that want to render `.TLK` blobs to plain text need access to the dictionary as a sibling input.

## 11. Worked example — `TOWNE.TLK`'s leading bytes

The first four bytes of `TOWNE.TLK` are the leading pair: the count word `0x0030` (forty-eight) followed by the sentinel id `0x0001`. A reader interprets this as "forty-eight slots, with the slot at id one being the universal sentinel."

The next four bytes are the first real header entry: a blob offset followed by the NPC id `0x0002`. Subsequent four-byte entries cover NPC ids three, four, and so on, sorted ascending, up to the last real NPC at id `0x0030` (forty-eight).

After the header — at the offset given by the first real entry — the first NPC's blob begins. The first byte is an obfuscated text byte encoding the first letter of the NPC's name. For "Iolo", the first byte is `0xC9` (obfuscated `'I'`); for "Mariah", `0xCD`. Subsequent bytes encode the rest of the name, terminated by NUL.

After the Name entry's NUL comes Description, then Greeting, then Job, then Bye, each NUL-terminated. Greetings typically carry control bytes — many start with `0x81` (PRINT-AVATAR-NAME) or end with `0x82` (END-STREAM). After the five leading entries comes the keyword body: a keyword string (e.g. `JOIN`, encoded as `0xCA 0xCF 0xC9 0xCE`), a NUL, the response stream, an `0xFF` END-OF-RESPONSE, and so on for additional pairs.

A reader can sanity-check a `.TLK` decoder by:

1. Reading the first four bytes as `(npc_count, sentinel)` and confirming the sentinel equals `0x0001`.
2. Reading `(npc_count − 1) × 4` more bytes as header entries and confirming the NPC ids are sorted ascending starting at `2`.
3. Picking any entry, seeking to its `blob_offset`, reading until end-of-response, and XOR-ing the printable-range bytes with `0x80` to recover ASCII.
4. Confirming the recovered text begins with a recognisable NPC name (e.g. "Iolo", "Mariah", "Jennifer", "Lord British").

## 12. Cross-references

- The conversation engine that consumes this format — the byte runner's full semantics, the keyword input loop, the multi-byte command machinery, the GOTO-label semantics, and the per-conversation state — `systems/conversation.md`.
- The per-class NPC roster file format providing the `dialog_index` field for each live NPC — `formats/npc.md` (a separate format spec).
- The per-class location data file format whose tile grids host the live NPCs — `formats/location-dat.md`.
- The text-output pipeline that ultimately renders the emitted bytes — `systems/text-output.md`.
- The free-text input pipeline that accepts the player's typed keyword — `systems/input.md`.
- The save image layout that persists the per-NPC quest flags toggled by IF-ELSE codes — `formats/saved-gam.md`.
- The party module whose state is mutated by the JOIN sequence and the gold-payment routine — described under `systems/conversation.md` cross-links.

## 13. Open questions

The format is verified by direct byte inspection at the file-structure level (header layout, NPC counts, sentinel mechanism, blob alignment) and by behavioural inspection at the byte-runner level (control-byte dispatch, dictionary substitution, obfuscation). The following points remain open.

- **Keyword pointer table populator.** The engine scans a thirty-four-slot pointer table during keyword input. The exact populator routine — whether it pre-walks every NUL terminator in the blob, stores a fixed-size map of entry ordinals, or is built lazily on first scan — is unconfirmed. The format does not constrain the populator.

- **The `0xA2` quote sentinel.** The byte runner suppresses a `0xA2` byte (which decodes to `"`) immediately following another `0xA2`. The most likely interpretation is paired-quote artefact suppression — close-quote bytes that appear adjacent because of a stream-control sequence between them. A content tool generating `.TLK` files should avoid `0xA2 0xA2` runs to be safe.

- **Multi-byte argument layout for `0x85`.** The three argument bytes following GOLD-PAYMENT encode a gold amount and associated flags, but the exact field split is not yet settled. The gold-payment handler is the source of truth.

- **Print-mask semantics.** The `0x8E` TOGGLE-MASK code XORs a print-mask byte with `0x80`. Two readings are consistent: (a) switching between dictionary-expansion and literal-pass-through; (b) switching case folding. Implementations should pick one and verify in play.

- **Reserved keyword indices.** The keyword input loop intercepts certain indices for the party-join handler. `NAME`, `JOIN`, and `WHO ART THOU` are confirmed reserved; the full reserved set is not yet traced. The reservation lives in the engine, not in the file.

- **`0x86` action-letter table.** The argument byte for ACTION-DISPATCH is dispatched per letter `A..K` with side effects. The mapping is partially uniform across NPCs (e.g. `'J'` for "join the party") but not globally; a full enumeration belongs in the action-handler spec.

- **Maximum blob size.** The engine reads at most one thousand twenty-four bytes per blob into the working buffer. Whether any shipped NPC's blob hits this cap is unverified; the longest known is around five hundred bytes. A length-aware load belongs in any robust implementation.

## 14. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of the four `.TLK` files, the per-class NPC counts, the leading-pair-as-count discovery, the obfuscation verification against decoded names, and the control-byte prevalence analysis — `u5-decomp/formats/npc-tlk-pth.md`.
- The conversation-engine entry point — the dialog-index dispatch from the Talk command, the dispatch into the file loader, and the conversation envelope — `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md`.
- The `.TLK` file loader — the four-class file dispatch by scene byte, the header read into a working buffer, the linear header walk for the matched NPC id, and the second blob read at the matched offset — `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`.
- The byte runner's full dispatch table — the control-code semantics, the multi-byte command machinery, the dictionary substitution, the GOTO-label search, and the per-conversation state cluster — `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`.
- The keyword input loop and the empty-input-as-BYE shortcut — `u5-decomp/functions/TALK_OVL/0x0B04_conversation_loop.md`.
- The case-insensitive bit-7-stripping string-equality routine used by the keyword match and the JOIN-name compare — `u5-decomp/functions/TALK_OVL/0x0000_strncmp_uppercase.md`.
- The conversation-system spec covering the runtime semantics this format spec only references — `u5-spec/systems/conversation.md`.
