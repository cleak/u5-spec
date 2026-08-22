# Common-Word Dictionary

The shared common-word vocabulary used by two text renderers: the `.TLK`
conversation byte runner (`systems/conversation.md`, `formats/tlk.md`) and the
shop bark renderer (`systems/shops.md`, `formats/shoppe-dat.md`). Both expand
their token bytes from this single table, so an implementation loads it once and
hands the same table to both consumers.

## 1. Where the table lives

The table is a resident data resource, not part of `.TLK` or `SHOPPE.DAT`. It
ships as part of the resident data image described in `formats/data-ovl.md`: a
run of one hundred twenty-eight sixteen-bit entries, each either a reference to
a NUL-terminated word in a nearby packed string pool or a null reference marking
an unused slot. The words themselves are plain ASCII with no obfuscation - the
bit-seven text encoding used inside `.TLK` blobs does not apply to the
vocabulary.

Nothing else in the game reads or writes the table. It is read-only content.

## 2. Index space and the two token biases

The catalog is indexed `1` through `128`. Index `0` is not part of the
dictionary: the entry ahead of index one is a null reference, and a zero byte in
either consumer terminates the record before any dictionary lookup happens.

| Consumer | Token byte range | Catalog index |
|---|---|---|
| `.TLK` conversation byte runner | `0x01`..`0x80` | the token byte itself |
| `SHOPPE.DAT` bark renderer | `0x80`..`0xFF` | token byte minus `0x7F` |

So dialogue token `0x01` and shop token `0x80` are the same entry (`the`), and
dialogue token `0x80` and shop token `0xFF` are the same entry (`work`).

Note the boundary carefully on the conversation side: the highest dictionary
token, `0x80`, has bit seven **set**. "Bit seven clear means dictionary token"
is off by one at the top of the range. The runner's actual classifier is a
single comparison - a stream byte below `0x81` takes the dictionary path,
everything from `0x81` upward takes the control-code or printable path. Shipped
dialogue uses token `0x80` thirteen times.

Immediately past index `128` the resident data continues with unrelated
asset-filename strings. Index `129` and above are not dictionary entries, and a
consumer must not follow them.

## 3. Empty slots

Ten interior indices carry a null reference: decimal `8`, `28`, `50`, `65`, `67`,
`70`, `72`, `73`, `74`, `75` — that is, `0x08`, `0x1C`, `0x32`, `0x41`, `0x43`,
`0x46`, `0x48`, `0x49`, `0x4A`, `0x4B` — shown as *(empty)* in the table below.
They are not word-boundary sentinels, and they are not record terminators.
Counting the unreachable index-zero slot ahead of the table, eleven null
references exist in the pointer run; only ten of them are addressable.

No shipped content references an empty slot. Across all four `.TLK` files the
set of dictionary tokens actually used is exactly the one hundred eighteen
populated indices, and `SHOPPE.DAT` likewise uses only populated indices. The
empty slots are dead vocabulary entries, most plausibly words that were edited
out of the vocabulary late in development.

An implementation still needs a defined behaviour for them, because custom
content could emit one. The conversation byte runner's behaviour is specified in
`systems/conversation.md` section 8: it emits a space and then the raw token
byte as a literal character in the alternate font, and it does *not* arm the
pending-space flag. The shop renderer has no empty-slot handling at all; treat an
empty-slot token there as malformed content.

## 4. Spacing

The dictionary words themselves carry no leading or trailing whitespace. Each
consumer adds its own spacing:

- **Conversation.** A space is emitted before *every* expansion, then the word,
  then a pending-space flag is armed that inserts one space before the next
  printable character. Full rules in `systems/conversation.md` section 8.
- **Shop barks.** A space is emitted before the word, and a trailing space is
  added only when the byte following the token is ordinary record text rather
  than another token or the record terminator. Full rules in `systems/shops.md`
  section 4.2.

Neither consumer suppresses the leading space before punctuation, so a token
followed by a comma renders with the space before the word and the comma tight
against the word's last letter. Some entries bake punctuation into the word
itself for exactly this reason - index `0x39` is `thee,` and index `0x2F` is
`Blackthorn's`.

## 5. The table

| Idx | Word | Idx | Word | Idx | Word | Idx | Word |
|---:|---|---:|---|---:|---|---:|---|
| `0x01` | `the` | `0x21` | `am` | `0x41` | *(empty)* | `0x61` | `Great` |
| `0x02` | `thou` | `0x22` | `we` | `0x42` | `through` | `0x62` | `might` |
| `0x03` | `of` | `0x23` | `they` | `0x43` | *(empty)* | `0x63` | `those` |
| `0x04` | `to` | `0x24` | `he` | `0x44` | `once` | `0x64` | `old` |
| `0x05` | `and` | `0x25` | `would` | `0x45` | `can` | `0x65` | `hast` |
| `0x06` | `that` | `0x26` | `art` | `0x46` | *(empty)* | `0x66` | `ask` |
| `0x07` | `for` | `0x27` | `on` | `0x47` | `him` | `0x67` | `unto` |
| `0x08` | *(empty)* | `0x28` | `young` | `0x48` | *(empty)* | `0x68` | `wish` |
| `0x09` | `in` | `0x29` | `what` | `0x49` | *(empty)* | `0x69` | `man` |
| `0x0A` | `is` | `0x2A` | `see` | `0x4A` | *(empty)* | `0x6A` | `so` |
| `0x0B` | `have` | `0x2B` | `like` | `0x4B` | *(empty)* | `0x6B` | `knows` |
| `0x0C` | `with` | `0x2C` | `only` | `0x4C` | `ye` | `0x6C` | `still` |
| `0x0D` | `thee` | `0x2D` | `by` | `0x4D` | `Shadowlords` | `0x6D` | `Mantra` |
| `0x0E` | `this` | `0x2E` | `there` | `0x4E` | `tell` | `0x6E` | `out` |
| `0x0F` | `not` | `0x2F` | `Blackthorn's` | `0x4F` | `some` | `0x6F` | `help` |
| `0x10` | `my` | `0x30` | `good` | `0x50` | `believe` | `0x70` | `well` |
| `0x11` | `it` | `0x31` | `been` | `0x51` | `all` | `0x71` | `shall` |
| `0x12` | `me` | `0x32` | *(empty)* | `0x52` | `their` | `0x72` | `think` |
| `0x13` | `but` | `0x33` | `must` | `0x53` | `upon` | `0x73` | `where` |
| `0x14` | `dost` | `0x34` | `his` | `0x54` | `even` | `0x74` | `named` |
| `0x15` | `know` | `0x35` | `British` | `0x55` | `'tis` | `0x75` | `talking` |
| `0x16` | `be` | `0x36` | `fine` | `0x56` | `find` | `0x76` | `more` |
| `0x17` | `was` | `0x37` | `an` | `0x57` | `if` | `0x77` | `such` |
| `0x18` | `Blackthorn` | `0x38` | `great` | `0x58` | `about` | `0x78` | `very` |
| `0x19` | `from` | `0x39` | `thee,` | `0x59` | `don't` | `0x79` | `may` |
| `0x1A` | `thy` | `0x3A` | `our` | `0x5A` | `before` | `0x7A` | `lives` |
| `0x1B` | `one` | `0x3B` | `who` | `0x5B` | `these` | `0x7B` | `canst` |
| `0x1C` | *(empty)* | `0x3C` | `name` | `0x5C` | `just` | `0x7C` | `which` |
| `0x1D` | `are` | `0x3D` | `heard` | `0x5D` | `make` | `0x7D` | `since` |
| `0x1E` | `here` | `0x3E` | `as` | `0x5E` | `will` | `0x7E` | `need` |
| `0x1F` | `many` | `0x3F` | `at` | `0x5F` | `when` | `0x7F` | `I've` |
| `0x20` | `Lord` | `0x40` | `has` | `0x60` | `three` | `0x80` | `work` |

## 6. Validation invariants

A loader or content tool can check all of the following against a candidate
table:

1. **Entry count.** Exactly one hundred twenty-eight addressable indices,
   numbered `1` through `128`.
2. **Populated count.** Exactly one hundred eighteen non-empty words.
3. **Empty slots.** Exactly ten, at indices `0x08`, `0x1C`, `0x32`, `0x41`,
   `0x43`, `0x46`, `0x48`, `0x49`, `0x4A`, `0x4B` (decimal `8`, `28`, `50`,
   `65`, `67`, `70`, `72`, `73`, `74`, `75`), in that order and no others.
4. **Index ordering.** The catalog order above is the token order; it is not
   alphabetical and must not be re-sorted. Round-tripping must preserve index
   positions, including the empty ones.
5. **Word content.** Every populated entry is a NUL-terminated ASCII string of
   two to twelve characters, containing no whitespace and no byte with bit seven
   set. The longest entry is `Blackthorn's` at twelve characters, followed by
   `Shadowlords` at eleven and `Blackthorn` at ten; the shortest are the
   nineteen two-letter function words.
6. **Bias check.** Catalog index `1` must be reachable as dialogue token `0x01`
   and as shop token `0x80`; catalog index `128` as dialogue token `0x80` and
   shop token `0xFF`.
7. **Usage check (optional, content-side).** Every dictionary token appearing in
   a shipped `.TLK` blob or `SHOPPE.DAT` record resolves to a populated index.

## 7. Character of the vocabulary

The vocabulary is dominated by English function words and by the archaic second
person the game's dialogue uses throughout - `thou`, `thee`, `thy`, `dost`,
`hast`, `art`, `canst`, `'tis`, `ye`. A small number of high-frequency proper
nouns are included so that many NPC blobs can reference them without restating
the string: `Blackthorn`, `Blackthorn's`, `British`, `Lord`, `Great`,
`Shadowlords`, `Mantra`. There are no city names and no item names in the table,
contrary to earlier descriptions in this repository; those are spelled out in
full in each blob.

## 8. Cross-references

- Conversation-side token classification, emission order, and spacing -
  `systems/conversation.md` sections 7.1 and 8.
- `.TLK` on-disk classification of dictionary tokens against control codes -
  `formats/tlk.md` sections 8, 9, and 10.
- Shop-side token expansion and placeholder substitution - `systems/shops.md`
  section 4.2 and `formats/shoppe-dat.md` section 5.
- The resident data image that carries the table and the string pool -
  `formats/data-ovl.md`.

## 9. Sources

Source provenance: derived from private analysis notes
`../u5-decomp/notes/talk_group_retrace_2026-08-22.md` (the pointer-run walk, the
populated/empty census, the token-range boundary, and the emission order),
`../u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md` (the conversation
token path), `../u5-decomp/functions/SHOPPES_OVL/0x0026_format_record_with_tokens.md`
(the shop token path and its bias), and `../u5-decomp/formats/data-ovl.md` (the
resident data layout). The word list is a derived data extraction from the
shipped resident data resource, in the same class as the published item, spell,
and tile catalogs; no private addresses, decompiled excerpts, or byte dumps are
reproduced here.
