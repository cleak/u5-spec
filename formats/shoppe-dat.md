# SHOPPE.DAT

## 1. Scope

`SHOPPE.DAT` is the shared text resource for shopkeepers, trade menus, item
descriptions, price quotes, rumours, vehicle-purchase barks, healer prompts,
and innkeeper messages. It does not store the shop inventories or prices
themselves; those are resident tables consumed by the shop overlays and
described at the system level in `systems/shops.md`.

The file is token-compressed prose addressed by record id.

## 2. File Structure

The shipped file is 10,135 bytes. Counting NUL terminators gives exactly **195**
records, ordinals `0` through `194`; the file's last byte is the terminator of
the last record, so there is no unterminated tail and no trailer beyond it. A
handful of those slots are empty (a lone terminator), which is why earlier
descriptions gave 194 "non-empty" records. Parsers should split on the
terminator and stop at end of file rather than expecting a fixed slot count.

| Property | Value |
|---|---|
| Header | None |
| In-file offset table | None |
| Record count | 195 records, ordinals `0`..`194`; a few are empty slots |
| Record addressing | By record id selected by the shop renderer |
| Literal encoding | Low-ASCII text |
| Compression | One-byte phrase tokens in the high-byte range |

The original consumer passes a selector that identifies the start of a
NUL-terminated record in `SHOPPE.DAT`. Public catalogs may also refer to the
same records by their sequential ordinal ids for readability. The renderer
locates the selected record, expands tokens and placeholders, and prints the
result. Records are not named in the file. Some record ids are effectively
unused or empty.

## 3. Record Byte Semantics

Within a record, bytes are interpreted by the shop text renderer:

| Byte class | Meaning |
|---|---|
| Printable low-ASCII except NUL | Literal text, except for substitution placeholders |
| Bytes with the high bit set | Phrase-token id; expands through the shared common-word dictionary |
| NUL | End of the current shop record |

The high-byte range is available for phrase tokens; it should not be treated as
an end-of-record marker. This includes `0xFF`, which is a valid token byte in
the shared dictionary. Records end at NUL, matching the sequential string
layout observed in the file survey.

## 4. Substitution Placeholders

Several literal ASCII bytes are placeholders. The renderer substitutes runtime
values before sending text to the normal output pipeline.

| Placeholder | Substitution |
|---|---|
| `%` | Current gold amount, price, or total |
| `^` | Current quantity |
| `$` | Vendor name |
| `&` | Item, subject, or asked-about name |
| `*` | Place or location name |
| `#` | Shop name |
| `@` | Time-of-day word: morning, afternoon, or evening |

The original records do not require escaping these bytes as literal
punctuation. A content tool that needs literal characters should define an
explicit modern escape rather than relying on original behavior.

## 5. Phrase Tokens

Record bytes `0x80` through `0xFF` are phrase tokens. They expand through the
same resident common-word dictionary used by NPC conversation text; the full
one-hundred-twenty-eight-entry table is published in
`catalogs/common-word-dictionary.md`.

The two renderers apply different biases to the same physical table. A shop
token `t` selects catalog index `t - 0x7F`, so `0x80` is catalog index one and
`0xFF` is catalog index one hundred twenty-eight; a conversation token is the
catalog index itself. Shop token `0x80` and conversation token `0x01` are the
same entry.

The dictionary contains common Britannian function words, pronouns, titles, and
a few recurring proper nouns. Ten entries are empty. They are **not**
word-boundary sentinels, and the shop renderer has no handling for them at all;
no shipped record references one, so an empty-entry token in `SHOPPE.DAT` should
be treated as malformed content.

Spacing is supplied by the renderer, not by the stored words. One space is
emitted before every expanded word, and a trailing space is emitted after it
only when the following record byte is ordinary text rather than another token
or the record terminator. `systems/shops.md` section 4.2 owns the renderer-side
statement of the same rule.

## 6. Record Families

Known shipped record clusters are:

| Records | Role |
|---|---|
| 0-7 | Shared short barks and farewells |
| 8-48 | Weapon and armour item descriptions |
| 49-56 | Arms `S`-menu haggle, confirmation, and refusal lines |
| 57-91 | Tavern, meal-counter, and related interactive prompts and menus, including the four state list records `69-72`, the four state follow-up records `73-76`, the six provision-quote records `77-82`, and the table-scraps outcome `90` |
| 84-88 and 91 | Sage rumour records, interleaved inside the tavern/interactive cluster: `84` fee quote, `85-88` success templates, `91` paying-customers refusal. Records `89` and `90` between them belong to tavern branches, not to the sage |
| 92-104 | Horse-trader barks |
| 105-126 | Ship-broker barks |
| 127-146 | Reagent vendor records |
| 148-162 | Guild or magic-shop records |
| 163 and 165-173 | Healer or sanctum records |
| 174-193 | Innkeeper records |

These ranges are consumer conventions. The file does not include range
headers, shop-kind ids, item ids, or price fields.
The healer/sanctum cluster supplies the yes/no treatment prompt, the Cure/Heal/
Resurrect service menu, condition refusals, ordinary paid-service quotes, the
sanctum Cure/Heal treatment lines, and the exit line; the treatment eligibility,
gold debit, status writes, and HP writes are owned by the shop overlay rather
than by `SHOPPE.DAT`.

## 7. Record Selection And Timing

The shop overlays select records; `SHOPPE.DAT` only stores the text. The public
contract should therefore treat record selection as caller-owned runtime
behavior, with these traced shared rules:

| Flow point | Selection rule | Random draw timing |
|---|---|---|
| Shared shop entry greeting | Pick one of four records from the current shop-kind row of the entry-greeting table. | One uniform `0..3` draw when the entry greeting is rendered. |
| Shared closing bark, nothing bought | Pick one of four records from the current shop-kind row of the nothing-bought exit table. | One uniform `0..3` draw when the closing-bark step runs with the nothing-bought outcome. |
| Shared closing bark, purchase completed | Pick one of four records from the current shop-kind row of the purchase-completed exit table. | One uniform `0..3` draw when the closing-bark step runs with the purchase-completed outcome. A third, silent outcome renders nothing. |
| Arms long greeting | Pick one of two resident literal greeting variants, then print the fixed arms prompt literals. | One uniform `0..1` draw during arms entry. |
| Arms buy affirmation | Pick one of four resident literal affirmation variants before entering the buy menu. | One uniform `0..3` draw only after the player selects Buy. |
| Arms buy item quote | Select the item-description record from the chosen equipment id; the public mapping is in `systems/shops.md`. | No random draw. |
| Tavern list | Select the tavern/menu record from the current tavern state, not from the tavern instance: states `0..3` map to records `69, 70, 71, 72`. The visible letter table for each state is in `systems/shops.md`. | No random draw for list selection. |
| Tavern post-branch follow-up | After an accepted branch and a `Y` answer to the "anything else" prompt, render the current state's follow-up record: states `0..3` map to records `73, 74, 75, 76`. | No random draw. |
| Tavern provision quote | Pick one of six interchangeable provision-quote records `77..82`. `%` is the Intelligence-adjusted per-unit price; every one of the six states the same twenty-five-serving pack size. | One uniform `0..5` draw when the provision branch renders its quote. |
| Tavern table-scraps outcome | Render record `90` when the party cannot afford a single provision pack and its food counter is below `3`. | No random draw. The accompanying food gift is a fixed one unit. |
| Horse-trader quote | Render record `104` with the Intelligence-adjusted local price in `%`. | No random draw. |
| Shipwright menu body | Render record `119` at the top of each pass of the Frigate/Skiff menu loop. | No random draw. |
| Shipwright quote | Render record `117` for a Frigate or `118` for a Skiff, then the shared take-it confirmation record `126`. | No random draw. |
| Shipwright pending-delivery cases | Render `125` when a Frigate is requested while a delivery is pending, `120` when a Skiff is stowed as cargo on a pending Frigate, `121` when a Skiff is requested while a standalone Skiff is pending. | No random draw. |
| Shipwright post-sale | Render `123` at the moment the delivery is queued, then `124` for the post-sale "anything else" body. | No random draw. |
| Sage fee quote | Render record 84 after a topic row matches. `%` is the row fee. | No random draw. |
| Sage paid success | Pick one of records 85-88 after confirmation and successful gold debit. `&` is the subject and `*` is the location. | One uniform `0..3` draw after payment only. Refusal and short funds do not consume this draw. |
| Sage short funds | Render record 91 and exit the sage flow. | No success-template draw. |

The shared `Y`/`N` prompt primitive echoes resident literals rather than
selecting a `SHOPPE.DAT` record. Individual shop arms may also print resident
literals before or after a `SHOPPE.DAT` record, so a clean implementation
should not assume every visible shop line comes from this file.

The shared entry-greeting and closing-bark rows have public record-id tables
in `systems/shops.md`. **Correction, 2026-08-22:** this section previously
called the middle row an "initial greeting". It is not entry text. Of the three
shared rows, only the first is rendered on arrival; the other two are both
rendered on the way out of a shop by one closing-bark step, chosen by whether
the visit completed a purchase. The rows in that table are taken from the
shipped selector tables as they stand, including the healer/sanctum kind, which
names the same four records in both of its exit rows - which is consistent
rather than anomalous once both rows are understood as exits.

Selector tables in the resident data hold each record's start position rather
than its ordinal. The two are interchangeable because records are stored
back-to-back in ordinal order, so an implementation that addresses records by
ordinal — as this document and `systems/shops.md` do throughout — reproduces the
original selection exactly.

**Wording policy.** Text stored in this file is addressed by ordinal and is
never transcribed into the public specs; the shipped asset is the source of the
words. Resident literals, which are not in this file, are published verbatim in
`systems/shops.md` where an engine must reproduce them for frame parity, and
described behaviourally otherwise. When a spec passage names a line in quotes,
it is a resident literal; when it names a number, it is a record in this file.

`systems/shops.md` owns any further per-flow record ids that have been
promoted.

## 8. Consumer Behavior

The shop overlays select records by id, expand tokens and substitutions into a
scratch buffer, and print the result through the text-output system. Different
shop kinds populate different substitution values before rendering:

- Arms shops set item names and prices.
- Reagent vendors set quantity and gold totals.
- Sages set the rumour fee, asked-about subject, and destination place. The
  sage success templates are ordinal records 85-88; the original selector
  table stores their record-start positions rather than only those ordinals.
- Innkeepers set room-rate or guest-list values.
- Generic greetings use vendor name, shop name, and time of day.

Purchases, sales, inventory updates, karma checks, and inn registry updates are
not encoded here. `SHOPPE.DAT` only supplies the text those flows display.

## 9. Validation and Error Handling

A reader should validate that every record id requested by the shop system
resolves to a NUL-terminated record inside the file and that token expansion
cannot overrun the output buffer. The lookup mechanism may be implemented by a
precomputed index table, a scan over sequential records, or another equivalent
reader; that mechanism is outside the on-disk `SHOPPE.DAT` format. An empty dictionary entry is not a
word-boundary sentinel on the shop side and no shipped record reaches one;
surface such a token as a content error in debugging builds rather than
rendering it.

For byte-compatible tooling, preserve unknown high-byte tokens rather than
guessing English text. For a modern runtime, a missing record should produce a
clear asset error rather than a partial shop menu.

## 10. Boundaries And Caller Ownership

The Talk-entry shop dispatcher, shipped shop-trigger values, stock tables,
pricing, and side effects are documented in `formats/npc.md`,
`formats/data-ovl.md`, and `systems/shops.md`; this file only owns the
text-record container.

Some record ids in the shipped range are unused or overlap between shop
families. That is a caller inventory question, not an on-disk format rule:
records remain sequential NUL-terminated text slots addressed by id regardless
of which shop flow, if any, selects a given id.

Presentation geometry is also not owned here. Ordinary shop output renders into
the inherited conversation text window, whose descriptor is never reconfigured
by any caller in the analyzed build; the two shop flows that do install their
own framed side panel are specified in `systems/shops.md`. See
`systems/text-output.md` Sections 9 and 10.1 for the window model and for the
message-window rectangle the inherited window actually carries (it is shaped
once by the gameplay-screen assembly; it does not keep the boot-time
full-screen default).

## 11. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`SHOPPE.DAT` section).
- `u5-decomp/functions/SHOPPES_OVL/0x0026_format_record_with_tokens.md` and
  `u5-decomp/notes/talk_group_retrace_2026-08-22.md` (the token bias, the
  published dictionary contents and empty-slot census, and the renderer's
  leading/trailing space rule).
- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md`.
- `u5-decomp/functions/SHOPPES2_OVL/_OVERVIEW.md`.
- `u5-decomp/functions/SHOPPES3_OVL/_OVERVIEW.md`.
- `u5-decomp/notes/shoppe_random_bark_tables_2026-05-24.md` (shared bark rows
  and the record-start to ordinal conversion).
- `u5-decomp/functions/SHOPPES2_OVL/0x0ABC_shipwright_main.md` and
  `u5-decomp/functions/SHOPPES2_OVL/0x066C_tavern_main.md` (per-flow record
  ids for the shipwright, horse-trader and tavern flows).
- `u5-spec/systems/shops.md`.
- `u5-spec/formats/data-ovl.md`.
