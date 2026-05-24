# Sage Rumours

Cleanroom catalog for the sage rumour lookup used by tavern-style sage menus.
This is authored gameplay data, not a transcript dump. The row strings below
are the semantic keyword, subject, location, and price values needed to
reproduce the original lookup.

## 1. Runtime Contract

The sage prompt accepts up to fifteen typed characters. Empty input exits. A
non-empty input is compared case-insensitively against the fixed topic table
below. Each topic key is a four-letter keyword. The key must either consume the
whole input or be followed by a space; longer words that merely start with the
four-letter key do not match.

On a match, the sage quotes the row's fee with SHOPPE.DAT record 84. If the
player refuses, the shop exits. If the player accepts but lacks enough gold, the
sage renders SHOPPE.DAT record 91, the paying-customers refusal, and exits. If
the player accepts and can pay, the fee is deducted, the row subject fills the
`&` placeholder, the row location fills the `*` placeholder, and one of the four
shared success templates is selected randomly. The success-template random draw
happens only after confirmation and a successful gold debit; refusal and
short-funds exits do not consume a success-template draw.

The same 26-row table is shared by the sage flow. There is no per-sage
16-entry rumour table in the traced handler. Tavern/menu state only selects the
visible action letter that reaches the sage prompt.

## 2. Menu Entry Mapping

The sage prompt is entered from the tavern-style menu state machine. Four menu
states expose the sage action under different visible letters, but all four
letters enter the same 26-row topic table.

| Menu state | Sage action letter | Rumour table selected |
|---:|---|---|
| 0 | `C` | Shared 26-row table |
| 1 | `T` | Shared 26-row table |
| 2 | `H` | Shared 26-row table |
| 3 | `A` | Shared 26-row table |

The tavern row selects the state as follows:

| Tavern or meal counter | Menu state | Sage action letter |
|---|---:|---|
| The Honest Meal | 0 | `C` |
| The Wayfarer Tavern | 0 | `C` |
| The Sword and Keg | 0 | `C` |
| The Slaughtered Lamb | 2 | `H` |
| The Humble Palate | 3 | `A` |
| The Blue Boar Tavern | 1 | `T` |
| The Cat's Lair | 0 | `C` |
| The Fallen Virgin | 2 | `H` |
| The Folley Tap | 0 | `C` |

The enclosing tavern menu checks ordinary tavern actions before the sage
letter. The sage letter is also a continuation action: pressing it before a
prior accepted tavern branch has put the menu into its continuation state does
not enter the keyword prompt.

## 3. SHOPPE.DAT Records

The original selector table stores SHOPPE.DAT record starts; the ordinal record
ids below are the equivalent sequential record numbers used by the public
SHOPPE.DAT catalog.

Fixed sage records:

| Record | Template meaning |
|---:|---|
| 84 | Fee quote and confirmation prompt. The `%` placeholder is the matched row fee. |
| 91 | Insufficient-gold / paying-customers refusal. This branch exits the sage flow. |

Paid-success records:

| Record | Template meaning |
|---:|---|
| 85 | "Seek ye & in *!" |
| 86 | Rumour says `&`, who lives in `*`, has knowledge. |
| 87 | It may be that `&`, of `*`, can help. |
| 88 | Mayhap `&` in `*` will aid the party. |

All matched rows use the same four-template random selection. The row does not
choose a specific success record.

## 4. Topic Rows

| Row | Keyword | Subject (`&`) | Location (`*`) | Fee |
|---:|---|---|---|---:|
| 0 | `hone` | Malik | Moonglow | 50 |
| 1 | `comp` | Greyson | Britain | 75 |
| 2 | `valo` | Trian | Jhelom | 50 |
| 3 | `just` | Jeremy | Yew | 50 |
| 4 | `sacr` | Rew | Minoc | 75 |
| 5 | `hono` | Gruman | Trinsic | 75 |
| 6 | `spir` | Saul | Skara Brae | 25 |
| 7 | `humi` | Shirita | New Magincia | 50 |
| 8 | `dece` | Malifora | Moonglow | 100 |
| 9 | `desp` | Annon | Britain | 150 |
| 10 | `dest` | Trian | Jhelom | 75 |
| 11 | `wron` | Felespar | Yew | 150 |
| 12 | `cove` | the mother of Rew | Minoc | 75 |
| 13 | `sham` | Sindar | Trinsic | 100 |
| 14 | `hyth` | Kaiko | New Magincia | 100 |
| 15 | `crow` | Terrance | Britain | 200 |
| 16 | `scep` | Greymarch | Yew | 200 |
| 17 | `amul` | Simon and Tessa | a hidden mountain keep | 200 |
| 18 | `fals` | Shalineth | the Lycaeum | 250 |
| 19 | `hatr` | a daemon | the desert | 250 |
| 20 | `cowa` | Lord Malone | Serpent's Hold | 250 |
| 21 | `astr` | Zachariah | Moonglow | 100 |
| 22 | `oppr` | Tactus | Minoc | 50 |
| 23 | `brit` | a daemon | the desert | 50 |
| 24 | `resi` | Terrance | Britain | 200 |
| 25 | `unde` | Jotham | a lighthouse south of Britain | 100 |

## 5. Sources

Source provenance: derived from private analysis note
`u5-decomp/functions/SHOPPES2_OVL/0x0508_sage_main.md`. The clean table
contains only semantic topic data and published SHOPPE.DAT record identities.
