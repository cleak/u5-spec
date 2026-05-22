# SHOPPE.DAT

## 1. Scope

`SHOPPE.DAT` is the shared text resource for shopkeepers, trade menus, item
descriptions, price quotes, rumours, vehicle-purchase barks, healer prompts,
and innkeeper messages. It does not store the shop inventories or prices
themselves; those are resident tables consumed by the shop overlays and
described at the system level in `systems/shops.md`.

The file is token-compressed prose addressed by record id.

## 2. File Structure

The shipped file is 10,135 bytes. The source notes describe 196 record slots,
of which 194 are non-empty in the shipped data, followed by an empty trailer.

| Property | Value |
|---|---|
| Header | None |
| In-file offset table | None |
| Record count | 196 record slots; 194 non-empty records in the shipped data |
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

High-byte tokens expand through the same resident common-word dictionary used
by NPC conversation text. The shop renderer and conversation byte runner use
different byte biases, but both reach the same physical dictionary.

The dictionary contains common Britannian function words, pronouns, titles,
and recurring proper nouns. Some dictionary entries are null sentinels used as
word-boundary hints. The exact dictionary contents belong to the resident data
resource, not to `SHOPPE.DAT` itself.

## 6. Record Families

Known shipped record clusters are:

| Records | Role |
|---|---|
| 0-7 | Shared short barks and farewells |
| 8-48 | Weapon and armour item descriptions |
| 49-56 | Arms `S`-menu haggle, confirmation, and refusal lines |
| 57-88 | Tavern, meal-counter, and related interactive prompts and menus |
| 84-91 | Sage rumour records, overlapping the tavern/interactive record cluster |
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

## 7. Consumer Behavior

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

## 8. Validation and Error Handling

A reader should validate that every record id requested by the shop system
resolves to a NUL-terminated record inside the file and that token expansion
cannot overrun the output buffer. The lookup mechanism may be implemented by a
precomputed index table, a scan over sequential records, or another equivalent
reader; that mechanism is outside the on-disk `SHOPPE.DAT` format. Missing
dictionary entries should be treated as word-boundary sentinels only where the
resident dictionary marks them as such; unexpected null dictionary entries
should be surfaced in debugging builds.

For byte-compatible tooling, preserve unknown high-byte tokens rather than
guessing English text. For a modern runtime, a missing record should produce a
clear asset error rather than a partial shop menu.

## 9. Boundaries And Caller Ownership

The Talk-entry shop dispatcher, shipped shop-trigger values, stock tables,
pricing, and side effects are documented in `formats/npc.md`,
`formats/data-ovl.md`, and `systems/shops.md`; this file only owns the
text-record container.

Some record ids in the shipped range are unused or overlap between shop
families. That is a caller inventory question, not an on-disk format rule:
records remain sequential NUL-terminated text slots addressed by id regardless
of which shop flow, if any, selects a given id.

## 10. Sources

This is a cleanroom prose specification derived from:

- `u5-decomp/formats/data-tables.md` (`SHOPPE.DAT` section).
- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md`.
- `u5-decomp/functions/SHOPPES2_OVL/_OVERVIEW.md`.
- `u5-decomp/functions/SHOPPES3_OVL/_OVERVIEW.md`.
- `u5-spec/systems/shops.md`.
- `u5-spec/formats/data-ovl.md`.
