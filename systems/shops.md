# Shops

## 1. Overview

Ultima V's settled locations are populated by shopkeepers — weaponsmiths,
armourers, magic-shop guildmasters, healers, herbalists, tavernkeepers,
meal-counter operators, sages, innkeepers, horse traders, and ship merchants.
Ordinary shop commerce is opened through Talk rather than through a dedicated shop command:
when the player talks to a shop-capable resident, the Talk entry path invokes a
*shop overlay* directly instead of loading a normal `.TLK` keyword
conversation. The overlay runs a small kind-specific menu loop until the player
exits, then returns to the surrounding game mode. Horse-trader sales use the
same Talk-entry shop dispatch family, but their handler is vehicle-oriented: it
sells and places a boardable horse object rather than opening a reusable stock
menu. Ship-broker text is present in the shop bark resource and shipwrights have
their own Talk-entry shop trigger; a paid sale queues an overworld vehicle
placement rather than writing an inventory counter.

The Talk-driven shop flows are split across three overlay files, grouped by
interaction shape rather than by trade type. Horse traders share the shop bark
resource and enter through Talk, but use a vehicle-sale helper rather than the
ordinary inventory loops:

- **Stationary stock with a fixed inventory** — weaponsmith / armourer, magic-shop guildmaster, healer / sanctum, herbalist (reagent vendor). One overlay handles all four.
- **Interactive talk/menu shops** — tavern or meal counter, sage rumour lookup,
  and shipwright sale flow. A second overlay handles these flows.
- **Innkeeper** — three-mode (rest / leave a companion / pick up a companion). A third overlay handles the inn alone, because it is the only shop that maintains persistent multi-*character* state across saves. (The shipwright also leaves saved state behind — a queued vessel delivery — but that is a single pending record, not a registry.)

Horse-trader dialogue and purchase barks, while included in the shop bark file,
are reached through a Talk shop arm. The purchase flow is vehicle-oriented: it
quotes a local horse price, asks for confirmation, checks gold, debits on
success, and writes a horse active-object record at the sale location. This is
not B-Board; B-Board only boards an already-present boardable object.
Ship-broker dialogue records are reached through their own Talk shop arm; a
paid sale queues a pending vehicle acquisition that the next overworld entry
turns into a placed watercraft active object.

A single shared dialogue resource — `SHOPPE.DAT`, a 10-kilobyte file holding 195 token-compressed records — provides every bark, item description, room-rate quote, and farewell flourish any overlay prints. It shares the 128-entry phrase-token dictionary published in `catalogs/common-word-dictionary.md` with the conversation engine, but its records are addressed by integer record id rather than by keyword.

This spec describes how a shop is entered from a Talk session, how the conversation engine selects which overlay handles a given shopkeeper, the on-disk layout of `SHOPPE.DAT` and the token expansion that decodes its records, the pricing model, the per-shop inventory model, the per-shop-kind interaction loops, the karma effects, and the hooks the shop overlays make back into the rest of the engine.

## 2. Triggering a shop

Conversation is the entry path, but shopkeepers do not use the ordinary `.TLK`
keyword-response byte runner. The player walks up to a shopkeeper NPC and
presses `T` to Talk. The Talk entry gate sees resident shop metadata for that
NPC, validates that the resident is currently a shop-capable target, and routes
directly to the matching shop overlay. Ordinary named residents continue down
the normal `.TLK` blob path described in `conversation.md`.

The shop-kind selector is resident conversation/shop state set by the
shopkeeper's high-range `.NPC` dialog-index byte. For Talk-driven shops, that
selector chooses one arm of the shop-dispatch table. The same setup also
resolves the current local shop instance from the active scene, preparing the
shop-name, vendor-name, and instance selectors before the overlay renders text
or lists stock.

Commerce terms such as `BUY`, `SELL`, `ROOM`, `REST`, `RUMOUR`, and `LORE` are
shop-kind inputs or prompts after the overlay has started; they are not a
generic `.TLK` keyword interception layer.

A shopkeeper NPC carries one shop kind at a time — weaponsmith *or* tavernkeeper
*or* sage, never two at once. The engine has no concept of a general store with
multiple commerce types; players who want a weapon and a drink must talk to two
different NPCs.

Shop entry includes a transport gate, and it is the only precondition between
the Talk dispatch and the shop arm. If the party's transport marker is either of
the two horse values, the dispatcher prints a fixed two-line refusal and returns
without entering any shop:

```text
A merchant says:
"GET THAT HORSE OUT OF HERE!"
```

The horse-trader trigger is exempt, so a mounted party can still buy another
horse. No other transport state is blocked: on foot and magic carpet both pass,
and the watercraft markers cannot occur in a scene that has shopkeepers.

Every Talk shop arm receives the same one-word caller context. Decoded
member-sensitive price paths use it as the speaking party member's roster slot;
other shop kinds receive the word even when their own flow does not need it. The
shopkeeper's name (for `$` substitution), the shop's display name (for `#`), and
the current shop-instance selectors are already resident work state by the time
the overlay renders text or lists stock — the dispatcher resolves all three from
the active scene, as described in Section 8.0.

## 3. Shop-kind dispatch

Dispatch from the conversation engine to the shop overlay goes through an
eight-arm Talk-entry shop table. In the shipped `.NPC` rosters, ordinary
dialogue ids are below the high shop-trigger range; the high values below are
shop triggers rather than `.TLK` npc ids. The trigger value is public asset
data, not an implementation enum invented for this spec:

| `.NPC` dialog byte | Public role | Dispatch family | Notes |
|--------------------|-------------|-----------------|-------|
| `0x81` | Weaponsmith / armourer | Arms stock arm | Shared Buy/Sell handler; current shop instance separates weapon and armour stock. |
| `0x82` | Tavern / meal counter / sage-style rumour flow | Interactive tavern arm | Drinks and meal-style prompts; the shared arm can enter the sage rumour lookup for locations whose shop state selects that flow. |
| `0x83` | Horse trader | Vehicle-sale arm | Talk-entered helper; places a horse active object. |
| `0x84` | Ship broker / shipwright | Shipwright sale arm | Talk-entered ship sale flow; payment queues overworld active-object placement for a purchased watercraft. |
| `0x85` | Herbalist | Reagent arm | Sells a compact menu of stocked reagents. |
| `0x86` | Guildmaster | Guild arm | Magic-shop inventory for keys, gems, and torches. |
| `0x87` | Healer / sanctum | Healer arm | Treats wounds, poison, and death. |
| `0x88` | Innkeeper | Inn arm | Three-mode; persistent guest registry. |

The shipped roster also uses special high dialogue bytes outside the shop
range; for example `0xFF` appears on some non-shop residents. Those values are
conversation/town special cases, not shop triggers.

The horse-trader row differs from ordinary stock shops because the successful
purchase writes vehicle state instead of an inventory counter. It searches the
nearby sale position, quotes the local horse price, uses the standard
affordability model, debits the party gold word, and leaves a boardable horse
object for the party. The ship-broker row differs after payment: the Talk
trigger and sale flow are identified, and the successful sale queues a pending
vehicle acquisition. On the next overworld entry, that pending state allocates a
vehicle active-object slot at the *delivery coordinate stored for the
shipwright the player bought from* — a fixed per-shipwright overworld cell
published in Section 8.7, not the town exit cell and not a cell derived from
the scene-to-exit mapping. Frigate purchases place a ship-family active object
carrying the queued skiff count; standalone Skiff purchases place a
skiff-family active object. The pending state is then cleared.

The stock horse-trader sale rows are:

| Scene | Location | Stable | Sale object | Base price |
|---:|---|---|---|---:|
| `6` | Trinsic | `Horse & Rider` | Horse active object | 100 |
| `20` | North Britanny | `The Stablehouse` | Horse active object | 130 |
| `22` | Paws | `Wishing Well Horses` | Horse active object | 160 |

The shipped resident horse-trader tables carry a **fourth** row: scene `30`
(The Lycaeum), base price `190`, with a vendor name but a null shop-name
reference — the row has no shop name at all. No `0x83` horse-trader trigger
exists in that scene's shipped NPC roster, so the row is unreachable in ordinary
play. Treat the three triggered
rows above as the public horse-trader contract, and do not treat scene `30` as
a fourth stable; the scene-byte table in Section 8.0 lists only the three
reachable rows for the same reason.

The confirmed Talk-driven shop arms all receive the caller's Talk context and
the resident shop buffers prepared before dispatch. On return, the Talk action
is complete regardless of whether the shop completed a purchase, refused
service, or exited without acting.

## 4. `SHOPPE.DAT` structure

`SHOPPE.DAT` holds the token-compressed text of every shopkeeper bark, item description, menu prompt, follow-up, room-rate quote, refusal, and farewell. The file is fixed at 10,135 bytes and contains exactly 195 NUL-terminated records, addressed by 0-based integer record id `0`..`194`; the final byte of the file is the final record's terminator. Records are stored back-to-back with no per-record header or in-file offset table; the consumer supplies a record id and resolves it to the corresponding sequential record.

Each record is a sequence of bytes terminated by a NUL byte. Within a record:

- **Low-ASCII bytes other than NUL** are emitted literally, except for substitution placeholders (Section 4.1) that the renderer expands inline.
- **Bytes `0x80`–`0xFF`** are phrase-token indices, each replaced by a word from the shared 128-entry common-word dictionary (Section 4.2, contents in `catalogs/common-word-dictionary.md`). `0xFF` is a valid token byte, not a record terminator.
- **Byte `0x00`** ends the record.

Records are not labelled in the file; the engine's per-shop-kind tables hardcode which record-id ranges belong to which shop kind. The cluster ranges are fixed and shipped:

| Records      | Shop kind / role                                                                       |
|--------------|----------------------------------------------------------------------------------------|
| 0–7          | Shared barks: short flourish lines like "Thanks for nothing!", "Have a nice day!"      |
| 8–48         | Weapon and armour item descriptions.                                                   |
| 49–56        | Arms `S`-menu sell-back haggle and confirmation barks.                                 |
| 57–88        | Tavern, meal-counter, and related interactive menus, prompts, and barks.               |
| 84–88, 91    | Sage rumour records (an overlap sub-cluster inside the tavern range: fee quote, four success templates, and the paying-customers refusal). |
| 89–90        | Tavern branch refusals that sit between the sage records: a secondary-branch stock refusal and the provision branch's table-scraps brush-off. |
| 92–104       | Horse-trader barks.                                                                    |
| 105–126      | Ship-broker barks.                                                                     |
| 127–146      | Reagent (herbalist) menu and barks.                                                    |
| 148–162      | Guild (magic shop) menu, item prompts, and barks.                                      |
| 163, 165–173 | Healer / sanctum menu, treatment prompts, and cure flourishes.                         |
| 174–193      | Innkeeper menu prompts, registry header, sleep tick, "Wilt thou take it?".             |

A few record-id slots are unused NUL-only records; their presence does not affect overlay logic.

### 4.1 Substitution placeholders

Within a record, certain printable-ASCII bytes are reserved as placeholders the renderer expands inline from runtime variables in resident memory:

| Byte | Placeholder | Substitution                                                                |
|------|-------------|-----------------------------------------------------------------------------|
| `%`  | gold amount | The current price or total being quoted.                                    |
| `^`  | quantity    | A count (bottles, ounces, hours, etc.).                                     |
| `$`  | vendor name | The shopkeeper's display name.                                              |
| `&`  | item name   | The name of the item being bought, sold, or referenced.                    |
| `*`  | place name  | A town, landmark, or location (used by sage rumours).                       |
| `#`  | shop name   | The shop's display name (e.g. "The Paladin's Protectorate").                |
| `@`  | time of day | "morning" if hour < 12, "afternoon" if hour < 18, otherwise "evening".      |

The substitution buffers are populated before any records are rendered.
Shop name (`#`) and vendor name (`$`) are set by the Talk shop dispatcher, not
by the shop overlay and not from the NPC being spoken to: both are read from
resident per-kind name tables using the shop-instance row resolved from the
active scene, and both are published per row in Section 8.0. Gold-amount,
quantity, and item-name are filled mid-loop by the shop arm as the player picks
items and prices are computed; the time-of-day byte is read fresh from the world
clock on every render.

A literal `&`, `%`, `*`, `$`, `#`, or `@` cannot be emitted as itself — none of the shipped record text uses these as literal punctuation, so the renderer always expands.

### 4.2 The phrase-token dictionary

The 128 phrase tokens (`0x80`–`0xFF`) index the shared one-hundred-twenty-eight-entry common-word dictionary, whose full contents and validation invariants are published in `catalogs/common-word-dictionary.md`. Shop token `t` selects catalog index `t - 0x7F`, so `0x80` is catalog index one (`the`) and `0xFF` is catalog index one hundred twenty-eight (`work`).

The same dictionary serves both the shop bark renderer and the conversation engine's byte runner. The two engines disagree only on the *byte range* they treat as token codes: the conversation engine uses the catalog index directly as its token byte (`0x01`–`0x80`), while the shop renderer applies the `0x7F` bias above. The two ranges resolve to the same physical entries — conversation token `0x01` and shop token `0x80` both expand to `the`. A single loaded table serves both renderers.

Ten catalog entries are empty. They are not word-boundary sentinels and they are not `SHOPPE.DAT` record terminators; the shop renderer has no empty-entry handling at all. No shipped `SHOPPE.DAT` record references an empty entry, so treat an empty-entry token in shop text as malformed content rather than as a spacing hint.

**Spacing.** The shop renderer emits one space before the expanded word. It emits a trailing space after the word only when the next record byte is ordinary text — that is, when the next byte exists, is not the record terminator, and is not itself a token byte. Consecutive tokens therefore produce exactly one space between words, and a token at the end of a record adds no trailing space. This is not the same rule the conversation runner uses; see `systems/conversation.md` section 8.1 for that one.

The vocabulary is heavily slanted toward Britannian function words and common nouns — *the, thou, of, and, for, thee, dost, art, ye, hast, canst, Blackthorn, British, Shadowlords, Mantra* — and contributes heavily to the shipped game's tone, because every shopkeeper draws from the same pool.

## 5. The bark renderer

A single shared renderer takes a record id and produces formatted text. All three shop overlays route through this resident renderer. The render pass:

1. **Resolve the record id** to the corresponding sequential record in the file.
2. **Read bytes from the file** until the NUL record terminator. The file is held open by the shop subsystem.
3. **Classify each byte**:
   - End-of-record → flush, terminate.
   - Phrase-token (`0x80`+) → look up the dictionary entry, copy the word into the output buffer.
   - Substitution placeholder → call the corresponding sub-renderer (decimal digits for `%`/`^`, copy-from-buffer for `$`/`&`/`*`/`#`, time-of-day word for `@`).
   - Plain ASCII → emit literally.
4. **Hand the output to the text-output system** for word-wrap and on-screen rendering.

The `%` substitution prints decimal digits with no thousands separator. The `@` substitution is the only one that consults the world clock; the hour byte is read fresh on every render, so a record rendered just before midnight may say "evening" while the same record rendered seconds later (after midnight) says "morning".

## 6. Pricing model

Shop headline prices come from resident asset tables and small deterministic
adjustments. They are *not* karma-modulated, *not* time-of-day-modulated, and
not haggled. Five paths are stat-sensitive: arms buy and sell quotes, the
horse-trader sale, inn room rates, both shipwright vessel classes, and the
tavern/meal-counter provision unit price. In each of those the speaking party
member's Intelligence changes the quoted price, so the same purchase costs
different amounts depending on who is doing the talking. Every other decoded
shop headline price is fixed by the relevant shop, commodity, or treatment
table.

Several read-only pricing tables live in the resident data segment:

- **Arms stock, sell-back, and price records** (weaponsmith, armourer). The
  `B` buy path uses a per-shop eight-entry candidate table. Each non-sentinel
  candidate is the equipment item id used directly to select the displayed
  item name, shared equipment counter, and canonical base price. The shop's
  buy quote is the canonical base price plus the integer-truncated adjustment
  `base * (100 - 3 * speaker_intelligence) / 100`. The same item can therefore
  quote differently when a different party member is doing the talking. The
  `S` sell path scans the party's carried equipment counters rather than shop
  stock; accepted items use a separate offer formula,
  `floor(base * 3 * speaker_intelligence / 100) + 1`, then add gold and
  decrement the equipment counter.
- **Guild stock and price records** (guildmaster). Guild shops use fixed
  per-shop records for keys, gems, and torches. The selected item's unit price
  is multiplied by the requested quantity before the affordability check.
- **Per-treatment cost tables** (healer). Cure, heal, and resurrection prices
  are keyed by the current healer or sanctum instance and treatment kind.
  Cure and heal use ordinary per-instance price entries on the normal paid
  branch, while the Minoc healer instance, **The Healers Mission**, bypasses
  the ordinary price path for Cure and Heal. Resurrection uses a wider
  per-instance fee. Healer prices do not depend on which party member is
  treated.
- **Per-room-rate table** (innkeeper). A per-inn base/minimum-rate table feeds
  the room quote and affordability checks. Inn charges use this adjustment:
  `adjusted(raw, Intelligence) = raw + trunc(raw * (100 - 3 * Intelligence) / 100)`.
  The division truncates toward zero. Rest uses
  `raw = base_rate * travelling_party_size`. Leave deposits use
  `raw = base_rate * 10`. Pickup first computes that same adjusted ten-unit
  lodging charge, then multiplies it by the selected guest's stored stay
  counter, with a stored zero billed as one unit. The time system increments
  that stored counter on each 28-day month rollover, capped at 25.
- **Horse-trader rows** (stable sales). The three shipped Talk-triggered horse
  traders use the base prices listed in Section 3, then apply the same
  adjustment shape as inn charges:
  `adjusted(base, Intelligence) = base + trunc(base * (100 - 3 * Intelligence) / 100)`.
  The division truncates toward zero. The resulting quote is checked against
  party gold before the horse object is placed.

Shipwright purchases use fixed local base-price rows before the ordinary quote,
confirmation, affordability, and payment flow. The tables below list base
headline values before any stat-sensitive quote adjustment and before the
random post-transaction surcharge.

Reagent vendors use a fixed price/availability matrix keyed by the current
herbalist and the underlying reagent id. A nonzero entry means the herbalist
stocks that reagent and gives its per-ounce price; a zero entry means the
reagent is not sold there. The same reagent can therefore cost different
amounts at different herbalists, but the value is still fixed per-shop and not
karma-driven.

The stock reagent price matrix is:

| Herbalist | Sulfur Ash | Ginseng | Garlic | Spider Silk | Blood Moss | Black Pearl | Nightshade | Mandrake |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| The Herbalist | — | 20 | 18 | 12 | — | — | 12 | 13 |
| Healers Herbs | 12 | 16 | 16 | 8 | 20 | — | — | — |
| The Alchemist | 14 | 16 | — | — | 30 | 18 | — | — |
| Mysticism | — | — | — | 6 | 8 | 8 | 10 | 15 |
| The Sharper Mage | — | — | — | — | 50 | — | 30 | 40 |

The stock tavern/meal-counter provision base prices are listed below. One
provision *unit* is a twenty-five-serving pack: a purchased unit raises the
shared food counter by `25`. The quoted per-unit price is **not** a flat table
read — it is Intelligence-adjusted from the speaking party member with the same
shape used by inn charges, horse sales, and shipwright sales:
`adjusted(base, Intelligence) = base + trunc(base * (100 - 3 * Intelligence) / 100)`,
truncating toward zero. The adjusted value is what the quote text shows and what
each unit costs in the pay loop.

| Tavern or meal counter | Provision unit base |
|---|---:|
| The Honest Meal | 10 |
| The Wayfarer Tavern | 15 |
| The Sword and Keg | 20 |
| The Slaughtered Lamb | 25 |
| The Humble Palate | 30 |
| The Blue Boar Tavern | 25 |
| The Cat's Lair | 20 |
| The Fallen Virgin | 25 |
| The Folley Tap | 30 |

The stock tavern drink branch has two pricing surfaces. The primary round
branch charges the listed base once per living party member and has no traced
durable inventory effect:

| Tavern or meal counter | Menu letter | Round base per living party member |
|---|---|---:|
| The Honest Meal | M | 3 |
| The Wayfarer Tavern | M | 4 |
| The Sword and Keg | M | 5 |
| The Slaughtered Lamb | B | 3 |
| The Humble Palate | F | 2 |
| The Blue Boar Tavern | C | 5 |
| The Cat's Lair | M | 3 |
| The Fallen Virgin | B | 4 |
| The Folley Tap | M | 5 |

The Blue Boar Tavern also exposes a special drink-list branch under its `W`
menu letter. It presents six fixed choices and debits the selected price
directly:

| Blue Boar `W` choice | Price |
|---|---:|
| A | 18 |
| B | 192 |
| C | 79 |
| D | 30 |
| E | 275 |
| F | 98 |

A shop purchase deducts the price (or price × quantity) from the party's gold
word — the shared resident counter every gold-handling system reads and writes,
including the conversation engine's bribe handler and the find-treasure
handler. Most successful paid purchases then consult the post-transaction
surcharge gate described below, which charges nothing unless the Shadowlord of
Falsehood is hiding in that settlement. Arms sell-back runs in the other direction: it increases the
gold word, capped by the normal gold limit, and decrements the sold equipment
counter.

The shared `0x82` tavern/meal-counter/sage arm selects one of four menu states
per tavern row. These states choose the visible letters for round drinks,
secondary tavern actions, provisions, and sage lore:

| Scene | Tavern or meal counter | State | Round/meal letter | Secondary tavern letter | Provision letter | Sage/lore letter |
|---:|---|---:|---|---|---|---|
| `1` | The Honest Meal | 0 | `M` | `A` | `R` | `C` |
| `2` | The Wayfarer Tavern | 0 | `M` | `A` | `R` | `C` |
| `3` | The Sword and Keg | 0 | `M` | `A` | `R` | `C` |
| `4` | The Slaughtered Lamb | 2 | `B` | `R` | none | `H` |
| `8` | The Humble Palate | 3 | `F` | `S` | `P` | `A` |
| `19` | The Blue Boar Tavern | 1 | `C` | `W` | none | `T` |
| `22` | The Cat's Lair | 0 | `M` | `A` | `R` | `C` |
| `24` | The Fallen Virgin | 2 | `B` | `R` | none | `H` |
| `30` | The Folley Tap | 0 | `M` | `A` | `R` | `C` |

Only four distinct letter sets exist, one per state, and every letter is the
initial of the menu item the state's shipped list text advertises. That is the
easiest way to remember which is which:

| State | Round/meal | Secondary | Provision | Sage/lore |
|---:|---|---|---|---|
| 0 | `M` Mutton | `A` Ale | `R` Rations | `C` Chat |
| 1 | `C` Cheese | `W` Wines | none | `T` Talk |
| 2 | `B` Boar | `R` Rum | none | `H` Help |
| 3 | `F` Fruits | `S` Stout | `P` Provisions | `A` Advice |

The Blue Boar's fixed six-choice drink list is the state-1 secondary tavern
letter `W`, so at that one tavern the drinks are on the secondary letter and
the per-head round is the food letter `C`. Other secondary tavern letters
remain in the tavern service family; they are not provisions and do not enter
sage lore. There is no fixed `A`-for-drinks, `F`-for-food, `M`-for-provisions,
or `B`-for-bye key: the four letters above are the whole visible key set for a
given tavern, plus the exit keys.

Post-list dispatch checks exit keys first, then the round/meal letter, then the
secondary tavern letter, then the provision letter, and finally the sage/lore
letter. A state has exactly one sage/lore letter. The sage/lore letter is gated
by the tavern continuation state: if it is pressed before a prior accepted menu
branch has established continuation, it is ignored and the menu waits for
another post-list key. Blue Boar therefore has no `C` lore conflict: `C` is its
round/meal letter, while its lore letter is `T`.

The gate matches what the player is shown. The post-`Y` list text advertises
only the round/meal, secondary, and provision items; the sage/lore letter is
advertised only by the follow-up text that appears after a branch has been
accepted, which is the same moment continuation is established. An
implementation that renders the shipped list and follow-up records therefore
never offers the lore letter before it works.

### 6.1 The affordability check

Most purchases are gated by an affordability check against the gold word. If
the player can't pay, the shop refuses with a kind-specific bark ("Beat it!" at
the tavern, "Highwaymen!" at an upmarket inn, "Thou canst afford only N" at a
vehicle broker) and returns to the main menu without deducting.

The tavern/meal-counter provision branch is the exception: it processes a
requested quantity one unit at a time. Each pass compares party gold against
the adjusted per-unit price; if it is affordable, gold is reduced by that price
with the ordinary zero floor and the shared food counter is raised by `25` with
the ordinary `9999` ceiling, and only then is the next unit considered. If the
party runs out of gold partway through the requested quantity, the
already-served units remain purchased and the shop reports the smaller
affordable quantity. Compatible implementations must not roll this branch back
as an all-or-nothing purchase.

Two loop terminations are worth stating exactly:

- If the food counter reaches `9999` mid-loop, the branch stops immediately and
  takes the completed-purchase exit even though units remain owed. The party is
  not refunded for the unserved remainder, because no gold was taken for it.
- The random post-transaction surcharge of Section 6.2 runs on the
  completed-purchase exit only. A partially served purchase — one that ended
  because gold ran out — returns without charging it.

The shipwright sale flow has a second gate before the ordinary gold check. It
tests the outdoor pending-action / vehicle-acquisition queue, which is consumed
by the overworld entry pass before the next outdoor turn begins. A successful
Frigate purchase records the ship-family acquisition class plus an initial
skiff-count payload; a successful standalone Skiff purchase records the
skiff-family acquisition class. The outdoor consumer allocates a free
active-object slot at the pending delivery coordinate, chooses ship versus
skiff from the acquisition class, writes the initial hull condition and the
carried-skiff count, and clears the pending state. The exact field values are
in Section 8.7. The owner is the outdoor pending-action handshake, not a
standalone commodity-stock field. The pending class byte and the pending
coordinate pair all live inside the saved game image, so a queued delivery that
has not yet been consumed survives a save and reload.

### 6.2 Post-transaction surcharge (a Falsehood effect only)

After a successful paid shop transaction, the shop family can deduct an extra
random `1..64` gold. **This is not a universal sales tax, and in ordinary play
it never runs.** It is one of the two effects of the Shadowlord of Falsehood:
the extra charge is made only while Faulinei is hiding in the settlement the
shop stands in.

Town entry records which of the three Shadowlords, if any, is resident in the
settlement being entered, by matching the three Shadowlord hideout slots
against that settlement (`systems/town-mode.md` Section 13). The recorded value
is the resident Shadowlord's identity, and every settlement that hosts none —
which is every settlement but at most three, at any moment in a playthrough —
records the no-host marker. The shop reader charges the extra gold only for the
Falsehood value; the Hatred and Cowardice values and the no-host marker all
suppress it, so the player normally pays exactly the displayed price. Hatred
and Cowardice have their own, non-shop effects, described in the same
town-mode section. The companion Falsehood effect — one carried item stolen at
the end of a conversation — is specified in `systems/conversation.md`.

The extra charge is independent of the quoted headline price and never scales
with it: the player sees and confirms the table/stat-derived price, the
ordinary affordability gate and main debit run, and only then is the extra
amount subtracted from the same party gold word.

Compatibility code should not model the gate as karma, shop kind, healer
identity, or a shop-local transaction flag. The Minoc no-price Cure/Heal branch
remains separate: it bypasses the ordinary paid branch before the surcharge
point.

Known traced surcharge callers — the branches that consult the gate, whether
or not a Shadowlord is resident — include:

| Shop family | Surcharge reach |
|-------------|-----------------|
| Arms buy / horse-trader paid branch | After successful purchase |
| Healer paid branch | After the headline treatment charge |
| Tavern, sage, and shipwright paid branches | After successful payment |
| Innkeeper room/guest charges | After successful payment |

Because the surcharge is applied after the ordinary affordability check, a
player shopping in Faulinei's hiding place with exactly enough gold for the
quoted price can still lose additional gold afterward, floored by the shared
word-subtract helper. This is a gold-side
effect only; it does not change shop stock, item quantities, or the quoted
record text.

## 7. Inventory model

The stocked shop kinds carry per-shop-instance inventories that vary by location. A weaponsmith in Britain stocks different weapons than one in Buccaneer's Den; the herbalist in Cove sells different reagents than the one in Yew. The variation is encoded in read-only resident stock and price tables — what changes is which item ids the table mentions and what their prices are.

A shop's inventory is *not* depleted by player purchases. The same weaponsmith stocks the same weapons after the player has bought them all; the engine never restocks because it never removes. Multiple visits yield the same selection.

Weapons and armour use resident equipment-price records and menu-selection
tables rather than mutable per-shop stock. The canonical equipment-price table
is item-keyed; zero-price entries are not purchasable or sellable. The `B` buy
menu's per-shop table stores up to eight equipment item ids and ends early at a
sentinel. No translation layer sits between that table and the item-name,
price, and equipment-counter rows. The `S` sell path is not shop stock at all:
it browses the party's nonzero equipment counters and refuses item ids the arms
shop cannot buy. Reagent vendors use the separate price/availability matrix
described above: zero entries are not displayed, and nonzero entries are
displayed as purchasable stock. The healer has no inventory in the shop sense;
the stock is the three treatment kinds (cure, heal, resurrect), always
available.

The one exception to the read-only model is the **inn registry**, which *is* per-instance per-game state and *does* survive saves (Section 8.4).

## 8. Per-shop-kind flow

Each Talk-driven shop kind follows a common shape: a randomised entry greeting, a Y/N or letter-driven menu, a per-action sub-loop, an "anything else?" re-prompt for shops that allow multiple sub-actions, and a randomised closing bark. The kinds vary in their inner steps. The closing bark is chosen by how the visit ended rather than by where it sits in the flow: a visit that bought nothing draws from a curt no-sale row, a completed purchase draws from a courteous farewell row, and one exit path renders nothing at all.

### 8.A Live dialogue selection, waits, and mutation timing

Shop dialogue draws from two kinds of text source:

- `SHOPPE.DAT` records, selected by the active shop overlay and expanded through
  the shared shop text renderer.
- Resident literals, printed directly by the active overlay. These include
  short echoes, prompt wrappers, menu labels, and many refusal/success lines.

The renderer accepts a record-start selector. For records whose ordinal ids are
listed in this document, implementations may treat the selector as that
published ordinal. Shared random-bark rows are selected by the normalized shop
trigger byte: `.NPC` dialog byte `0x81` uses row `0`, `0x82` uses row `1`, and
so on through `0x88` row `7`. Each visible shared row selection draws one
uniform ordinal `0..3` at the moment that flow point is rendered. The selected
ordinal is not retained in shared state; a caller that re-polls input without
recalling the bark dispatcher reuses the visible text already on screen, while
a later dispatcher call draws again.

| Shop trigger / role | Entry-greeting records | Exit records, nothing bought | Exit records, purchase completed |
|---|---|---|---|
| `0x81` Weaponsmith / armourer | Not used by the ordinary arms entry path | `0, 1, 2, 3` | `4, 5, 6, 7` |
| `0x82` Tavern / meal counter / sage | `57, 58, 59, 60` | `61, 62, 63, 64` | `65, 66, 67, 68` |
| `0x83` Horse trader | `92, 93, 94, 95` | `96, 97, 98, 99` | `100, 101, 102, 103` |
| `0x84` Ship broker / shipwright | `105, 106, 107, 108` | `109, 110, 111, 112` | `113, 114, 115, 116` |
| `0x85` Herbalist | `127, 128, 129, 130` | `131, 132, 133, 134` | `135, 136, 137, 138` |
| `0x86` Guildmaster | `148, 149, 150, 151` | `152, 153, 154, 155` | `156, 157, 158, 159` |
| `0x87` Healer / sanctum | `165, 166, 167, 168` | `169, 170, 171, 172` | `169, 170, 171, 172` |
| `0x88` Innkeeper | `174, 175, 176, 177` | `178, 179, 180, 181` | `182, 183, 184, 185` |

**Correction, 2026-08-22.** Earlier revisions of this table headed the middle
column "initial-greeting records" and described it as text a shop prints on
arrival. That was wrong. Only the first column is entry text. The second and
third columns are both *exit* rows, rendered by one shared closing-bark step at
the end of a visit and selected by a transaction-outcome code: the middle
column when the party leaves without buying anything, the right column after a
completed purchase, and neither when the flow passes the silent outcome. The
middle column's shipped text makes the reading unambiguous - the weaponsmith
row snubs the party for buying nothing, the guildmaster row tells it to get
lost in guild slang, and the ship broker row calls it a landlubber. No shop
greets an arriving party that way. The genuine arrival text is the first column, whose
records are full welcome lines naming the shop, the shopkeeper, and the time of
day.

| Flow point | Text source | Selection timing | Wait, clear, and retry behavior | State effects |
|---|---|---|---|---|
| Shared non-arms entry greeting | One of four `SHOPPE.DAT` records from the current shop-kind entry-greeting row, followed by resident tail text | Uniform `0..3` draw when the entry greeting is rendered | Printed once on entry for guild, reagent, healer, and horse-trader flows; arms does not use this shared entry greeting | No inventory, gold, or object mutation |
| Shared closing bark, nothing bought | One of four `SHOPPE.DAT` records from the current shop-kind nothing-bought exit row | Uniform `0..3` draw when the closing-bark step runs with the nothing-bought outcome | Rendered at the tail of a visit that completed no purchase, including a refused entry prompt or a declined quote | No inventory, gold, or object mutation |
| Shared closing bark, purchase completed | One of four `SHOPPE.DAT` records from the current shop-kind purchase-completed exit row | Uniform `0..3` draw when the closing-bark step runs with the purchase-completed outcome | Rendered at the tail of a visit that completed a purchase. A third, silent outcome code renders no bark and no attribution tail | No inventory, gold, or object mutation |
| Shared `Y`/`N` prompt primitive | Resident literals for the accepted echo | No `SHOPPE.DAT` selection | Loops until uppercase `Y` or `N`; `Y` echoes the resident `Yes` literal and `N` echoes the resident `No` literal; other keys are ignored and do not redraw or advance | Returns only the accepted key |
| Arms entry | Resident/tokenized greeting plus a resident long-greeting variant | Long-greeting variant draws uniform `0..1` after the initial wait | Prints the entry greeting, waits for one key, then asks for `B`, `S`, or exit input | No inventory or gold mutation |
| Arms `B` branch | Resident `Buy` echo and resident affirmation | Affirmation draws uniform `0..3` only after `B` is accepted | Renders the current stock list; Space or Escape exits the buy list; letters outside the displayed stock count are ignored without a refusal bark | No mutation until an item confirmation passes |
| Arms buy quote | Deterministic `SHOPPE.DAT` record from the selected equipment id; mapping is published in Section 8.1 | Selected immediately after a valid stock letter is accepted | Renders the quote and a resident confirmation prompt; `N` declines and returns without a fresh quote, other non-accepted keys keep waiting at the same prompt | No mutation before confirmation, cap check, and affordability check |
| Arms buy confirmation | Resident prompt chosen from four variants | Uniform `0..3` after the deterministic item quote | `N` prints the resident decline echo and returns. Counter-cap refusal prints a fixed resident refusal and waits for a key. Short funds prints one fresh resident no-credit bark from a four-entry pool and exits the shop flow | Successful payment deducts gold, runs the Section 6.2 surcharge gate, and then increments the equipment counter or fills arrows/quarrels to `99` |
| Arms `S` branch | Resident/menu literals and deterministic sell-back quote text | Selection is driven by the carried item being browsed | Empty inventory, unsellable items, and excluded ammunition are refused without changing inventory; accepted `N` responses leave the selected item unchanged | Successful sale adds gold and decrements the carried counter |
| Guildmaster entry | Shared non-arms preamble, then resident affirmation or refusal | Preamble draws once on entry; no fresh random bark is drawn for invalid keys | `Y` enters the guild stock menu. `N` or Space prints the resident refusal and exits. Other keys re-poll the same entry prompt | No mutation before an accepted stock purchase |
| Reagent-vendor entry | Shared non-arms preamble, then resident affirmation or refusal | Preamble draws once on entry; no fresh random bark is drawn for invalid keys | `Y` enters the reagent stock menu. `N` or Space prints the resident refusal and exits. Other keys re-poll the same entry prompt | No mutation before an accepted reagent purchase |
| Healer entry and service menu | Shared non-arms preamble, resident entry response, resident service prompts, treatment records/literals | Preamble draws once on entry. Service text is branch-deterministic by `C`, `H`, or `R` | Entry accepts `Y`/`N`; other keys re-poll. The service menu accepts Cure, Heal, Resurrect, Space, or Enter; other keys re-prompt. Invalid or untreatable member choices return to the menu without a charge | Treatment effects and gold debit occur only after member validation, quoted cost, confirmation, and affordability |
| Horse-trader sale | Shared non-arms entry greeting, deterministic horse quote record, resident confirmation/refusal text | Entry greeting draws once on entry; the quote record is selected from the current horse-shop row and adjusted price | `N` or Space exits through the nothing-bought closing bark. `Y` renders the quote and enters an inner `Y`/`N` confirmation loop. Inner `N` declines without selecting a new quote and also exits through the nothing-bought bark. Short funds prints resident refusal text and takes the silent exit, rendering no closing bark at all | Successful payment deducts gold, runs the Section 6.2 surcharge gate, and places a horse active object adjacent to the player |
| Tavern drink flow | Tavern entry bark and list `SHOPPE.DAT` records selected by the active tavern state | Entry/list records are deterministic from the current tavern state; sage-style success records draw only in the sage subflow described below | The tavern clears the conversation text window before its greeting. `N` or Space prints the resident pardon/refusal and exits. After a list is rendered, Space, Escape, or Enter exits the post-list menu; other accepted letters follow the current tavern-state table | Gold changes only after an accepted quantity/action passes affordability |
| Tavern provision branch | Six-record quote pool, `SHOPPE.DAT` ordinals `77..82`, plus resident quantity prompt, refusal, and partial-purchase literals; the table-scraps outcome renders ordinal `90` | Uniform `0..5` draw when the quote is rendered, once per entry into the branch. The quantity prompt, the pay loop, and every outcome line are deterministic | The quote and quantity prompt append to the tavern text already on screen. The typed-quantity prompt waits for the number; the outcome line does not wait for a key before the branch returns | Gold and food move one unit at a time inside the pay loop. The surcharge runs only on the completed-purchase exit. The two nothing-served outcomes end the visit |
| Sage rumour flow | `SHOPPE.DAT` record `84` for fee quote, records `85..88` for paid success, record `91` for short funds | Record `84` is deterministic after topic match. Paid success draws uniform `0..3` across records `85..88` only after confirmation and successful debit. Short funds deterministically uses record `91` | Refusal does not consume a success draw. Short funds does not consume a success draw | Gold is deducted before the success rumour record is drawn and rendered |
| Shipwright sale | Resident/menu text plus deterministic quote text for Frigate or Skiff | Selection is driven by accepted `F` or `S` branch and current shipwright row | The branch prompts for confirmation and affordability before queueing delivery | Successful payment deducts gold, runs the Section 6.2 surcharge gate, and queues the pending watercraft placement |
| Inn flow | Resident innkeeper text and `SHOPPE.DAT` records from the inn record table | Room quote and registry text are deterministic from the current inn and branch | Room, leave-companion, and pickup-companion branches use branch-local prompts and registry screens; failed eligibility checks print resident refusal text and return without a fresh room quote | Rest charges and registry mutations occur only after the corresponding branch validation and accepted payment/selection |

For frame-oriented rendering, the live transcript contract is:

| Flow state | Text source | Clear or append | Cursor movement | Wait / ignored input |
|---|---|---|---|---|
| Arms entry | Resident/tokenized shop greeting, resident shopkeeper-intro literal, two-entry resident long-greeting pool, then a resident closing quote/space | Appends to the inherited conversation window; no shop-local clear | No explicit shop cursor setter; output advances from the inherited cursor | Waits once after the first greeting, then waits for `B`, `S`, Space, or another exit key |
| Arms buy stock list | Resident `Buy` echo, four-entry resident affirmation pool, four-entry resident stock-call pool, current stock item names | Appends after the entry transcript | Natural text advance only | Invalid stock letters leave the stock list visible and keep waiting; they do not redraw the list or consume a random draw |
| Arms item quote and confirmation | Deterministic `SHOPPE.DAT` quote by equipment id, then one of four resident confirmation prompts | Appends after the stock list | Natural text advance only | Only `Y` and `N` advance. Other keys leave the quote/prompt visible and do not redraw or consume a random draw |
| Arms sell browser | Resident sell-side literals plus deterministic sell-back quote records for the browsed carried item | Installs its own framed side panel in text window `1` (geometry below), then restores window `2` | Fixed panel cursor origins while the panel is up; natural text advance afterwards | Empty, unsellable, and declined items return through the browser without a fresh shared bark |
| Guild entry | Shared non-arms preamble row, resident acceptance/refusal literals, then guild stock menu | Appends; no shop-local clear | Natural text advance only | `Y`, `N`, and Space are accepted. Other keys leave the prompt visible and keep polling |
| Reagent entry | Shared non-arms preamble row, resident acceptance/refusal literals, then reagent stock menu | Appends; no shop-local clear | Natural text advance only | Same as guild entry; ignored keys do not redraw or consume a random draw |
| Healer entry and service menu | Shared non-arms preamble row, resident entry literals, service prompts, and deterministic treatment text | Appends; no shop-local clear | Natural text advance only | Entry waits for `Y`/`N`; the service menu accepts `C`, `H`, `R`, Space, or Enter. Invalid service choices re-prompt from the service menu rather than selecting a new shared preamble |
| Tavern / meal entry | Per-shop tavern greeting and menu records selected by the tavern state | Clears the inherited conversation text window before the greeting, then appends | No shop-local cursor origin after the clear | Entry accepts `Y`, `N`, or Space. Other keys leave the greeting visible and keep polling |
| Tavern / meal post-list menu | Deterministic state menu/list record, then branch-local quantity, provision, follow-up, or drink text | Appends after the list | Natural text advance only | Space, Escape, or Enter exits. Invalid letters leave the list visible; the gated sage/lore letter is ignored until the tavern continuation state allows it |
| Sage topic flow | Resident sage prompt, free-text input, record `84` fee quote, success records `85..88`, or no-credit record `91` | Appends in the tavern-owned transcript | Natural text advance only | Empty input returns; unknown topics print the no-help line and re-prompt. `N` exits before a success draw; short funds exits without a success draw |
| Horse-trader entry and quote | Shared non-arms entry-greeting row, deterministic local horse quote, resident confirmation/refusal literals | Appends; no shop-local clear | Natural text advance only | Outer `N` or Space echoes the resident `No` literal and exits through the nothing-bought closing bark, not silently. Outer `Y` prints the quote and enters an inner `Y`/`N` wait; ignored inner keys leave the quote visible |
| Shipwright entry and branch | Shared shipwright bark rows, resident Frigate/Skiff menu text, deterministic local quote text | The shipwright body clears the inherited conversation text window before its prompt body, then appends branch text | No shop-local cursor origin after the clear | Invalid outer choices re-poll the menu. Delivery-pending and short-funds refusals print branch text and return without queueing a vehicle |
| Inn main menu | Inn preamble/greeting rows, resident room/leave/pickup prompts, deterministic inn record table | Ordinary inn prompts append in the inherited conversation window | Natural text advance only | Branch-local prompts wait according to the selected room, leave, or pickup path; failed eligibility checks print their refusal and return to the inn prompt path |
| Inn multi-guest pickup register | Resident register frame/list text and guest names copied from the inn registry | Temporarily selects and clears window `1`, draws the register panel, then restores window `2` | Uses the fixed register cursor positions in Section 8.4 only for the register panel | After the register is drawn, selection continues in the ordinary inn prompt path |

The short resident literal pools that affect prompt parity are:

| Use | Literal contract |
|---|---|
| Shared Y/N prompt echo | `Y` echoes `Yes` plus newline; `N` echoes `No` plus newline. Other keys print nothing and keep polling. |
| Arms buy confirmation prompts | One prompt is selected uniformly from: `Wouldst thou buy one?`, `Wilt thou take it?`, `Wish ye it?`, `May I get one for thee?` |
| Arms buy decline echo | `N` prints `No` followed by a blank line, then returns from that quote without changing gold or inventory. |
| Arms carry-cap refusal | Prints the fixed carry-cap refusal followed by the shopkeeper suffix, waits for one key, then returns from the quote. |
| Arms no-credit barks | One no-credit bark is selected uniformly from the four-entry resident pool listed below, wrapped in the shopkeeper-attribution tail; this exits the shop flow without changing gold or inventory. |
| Arms successful sale tail | Prints the fixed sold line, then the post-item "anything else" prompt addressed by the speaking member's gender field, or a neutral variant when no transaction has completed. |
| Arms no-credit bark pool (verbatim) | `Can't pay?! Out with ye, orc-face!`, `What be ye trying to pull? OUT!`, `OUT, SLIME!`, `BEAT IT!` — one chosen uniformly, wrapped by the attribution tail `yells <shopkeeper>.` |
| Arms stock-call pool (verbatim) | Printed once above the stock list, chosen uniformly from: `What may I show thee?`, `Which wouldst thou like to see?`, `What is thine interest?`, `Which would ye see?` |
| Arms carry-cap refusal (verbatim) | `"Thou canst not carry any more!"` followed by the attribution tail `says <shopkeeper>.` |
| Shipwright post-sale tail | Renders the post-sale record, then addresses the buyer. The gender test in this branch compares a field against a value that field never holds, so the feminine form is unreachable and the shipped build always prints the masculine form. Implementations targeting frame parity should always print the masculine form here; the arms tail, by contrast, selects correctly. |

Prompt redraw rules are intentionally narrow. A prompt redraw occurs only when
the flow explicitly calls the prompt/menu renderer again, such as healer service
re-prompting or sage no-match re-prompting. Plain ignored-key waits do not clear
the inherited window, do not re-render the visible quote or menu, and do not
consume a random bark draw. The shared entry-greeting and closing-bark
selections are not retained in hidden state: the visible text remains only
because the caller keeps polling without calling the bark dispatcher again.
A later dispatcher call selects a fresh row ordinal.

The traced ordinary arms *buy* path, guild, reagent, healer, tavern, sage,
meal/provision, horse-trader, and shipwright overlay paths do not install
shop-local text-window rectangles or cursor origins. They render into the active
text window inherited from the conversation/text system, with the clear/append
ordering captured above where it affects dialogue behavior.

There are exactly **two** shop-owned geometry exceptions, and they share one
shape: a framed side panel drawn in text window `1` and then handed back to
window `2`.

- **Inn multi-guest pickup register** (Section 8.4). Selects window `1`, sets
  it to `(24, 1)..(38, 9)` and clears it, widens to `(24, 1)..(39, 9)` for the
  frame, draws row borders at window-local `(0, row)` and `(14, row)` over rows
  `1..7`, places a heading at `(1, 1)` and a subheading at `(1, 2)`, prints the
  matching guest lines, then restores window `2`.
- **Arms `S` sell browser** (Section 8.1). Selects window `1`, sets it to
  `(24, 1)..(38, 6)` and clears it, widens to `(24, 1)..(39, 9)` for the frame,
  draws row borders at window-local `(0, row)` and `(14, row)` over rows
  `1..4`, and pages the party's carried equipment counters inside the panel.
  It prints no heading or subheading. When the browser finishes it restores
  window `2` before the ordinary confirm/prompt path resumes.

Both use the same `(24, 1)..(38, N)` clear / `(24, 1)..(39, 9)` frame idiom that
the character-sheet and inventory panels elsewhere in the game use, so a clean
engine can implement one panel primitive and parameterise the cleared height
and the number of bordered rows. All coordinates are text cells in the fixed
40-by-25 grid, not pixels.

For the ordinary Talk-to-shop entry path, the inherited caller-owned state is
active text window selector `2` together with that window's descriptor and
current cursor. The concrete contents of that descriptor are now settled, and
the answer is that **nothing configures it**: across the whole analyzed build,
the text-window rectangle setter is only ever called for window `0` (twice by
the resident inverse-text banner helper, twice by the dungeon view) and window
`1` (the framed side panel used by the character sheet, the command overlay,
the inn register and the arms sell browser). Window `2` is never passed to it,
and neither is window `3`.

Window `2` is therefore never reshaped *by a shop or conversation path*. That
is not the same as its keeping the boot-time full-screen rectangle: the
gameplay-screen assembly sets window `2` once, to the message-window rectangle
of `systems/text-output.md` Section 10.1, and no overlay changes it afterwards.
Shop and conversation text is consequently bounded by the message window, not
by the full screen. An earlier revision of this paragraph asserted the
full-screen boot rectangle here; that is withdrawn, and `systems/text-output.md`
Sections 9 and 10.1 are authoritative. What the shop overlays do leave
untouched is the descriptor's colour attribute — bright white on black — and
its cleared flags. Its
cursor is whatever previous output in window `2` left behind, advanced by the
Talk entry newline; no shop or conversation path homes it. The colour setters
are likewise never called by the town, overworld, conversation, or shop
overlays — the only callers in the build are the dungeon inspection overlay and
the resident framed-message-window helpers — so shop text renders in the
inherited attribute and no shop branch varies it by shop kind, scene, party
state, refusal reason, or resource availability.

The Talk shop dispatcher does not reset the selector, rectangle, cursor,
colour, or style before it calls the selected shop arm; in fact the
conversation overlay makes no window-selection, rectangle, or cursor call at
all on any path. It first emits the same conversation
entry newline used for all Talk dispatches, resolves the shop trigger, and then
hands control to the shop overlay. As a result, ordinary arms, guild, reagent,
healer, tavern/sage/meal, horse-trader, and shipwright output begins in the
conversation-owned main window unless the specific flow later clears or moves
within that inherited window.

The inherited state is shared by the normal facing-tile Talk path and the
counter/talk-through fallback; the fallback changes only which NPC is resolved.
No separate direct-tile shop trigger has been traced outside Talk dispatch.
Short-funds refusals, counter-cap refusals, post-purchase redraws, and
`SHOPPE.DAT`-missing fallback handling are inside shop or resource paths after
the same inherited entry state has already been established. The two side
panels above are the only departures: each temporarily selects window `1` and
restores window `2` before returning to its ordinary prompt path.

**Wording policy for literal text.** Two categories of shop text exist, and
this document treats them differently on purpose. Text held in `SHOPPE.DAT` is
addressed by record ordinal and never transcribed here: the shipped asset
supplies the wording, and an engine that reads the asset reproduces it exactly.
Resident literals are not in that asset, so the ones an engine must reproduce
to match a frame are published verbatim in this document — the shared `Yes`/`No`
echoes, the four arms confirmation prompts, the four arms stock-call lines, the
arms carry-cap refusal, the four arms no-credit barks, `Sold!`, and the arms
"anything else" tail with its gendered suffixes. Any other resident literal is described behaviourally
because its exact wording does not change engine behaviour or menu geometry.
Where the same wording is needed in a future flow, publish it here rather than
inventing an ordinal for it.

One shipped-data detail is worth calling out so it is not "fixed": the
healer/sanctum row names the same four records in both exit columns of the
table above. That is what the shipped selector tables hold, and under the
corrected reading it is not even anomalous - both columns are exits, so a
sanctum blesses the party on the way out either way, whether or not it was paid
for a treatment.

### 8.0 Scene-byte to shop-instance row mapping

Every Talk-triggered shop kind resolves its per-location row through the active
scene byte (`SAVED.GAM 0x02ED`) by searching a per-kind scene-byte lookup table
in the resident shop-data region. The search is a plain forward scan of that
kind's list, and the **index of the matching entry** is the shop-instance row
used by every other per-shop table in this document: prices, stock rows,
delivery cells, menu states, shop names, and vendor names all share it.

Two resident name tables are indexed by the same row and filled in before the
shop overlay runs: the shop's display name, which fills the `#` substitution,
and the vendor's name, which fills the `$` substitution and the
`says <shopkeeper>.` / `yells <shopkeeper>.` attribution tails. Both are
published as columns below. Neither name is read from the NPC roster or the
conversation blob, so the shopkeeper an implementation names in shop text is a
property of the location, not of the NPC the player happened to talk to.

The eight per-kind tables, in their full byte-traced form, are:

**Arms shops** (9 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `2` | Britain | `Iolo's Bows` | Gwenneth |
| `3` | Jhelom | `Naughty Nomaan's` | Nomaan |
| `4` | Yew | `Arms of Justice` | Ronan |
| `5` | Minoc | `Darkwatch Armoury` | Shenstone |
| `6` | Trinsic | `The Paladin's Protectorate!` | Paul |
| `17` | Lord British's Castle | `North Star Armoury` | Max |
| `24` | Buccaneer's Den | `Buccaneers Booty` | Kitiara |
| `26` | Bordermarch | `The Shattered Shield` | Steve |
| `32` | Serpent's Hold | `Siege Crafters` | Thol |

**Taverns / meal counters** (9 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `1` | Moonglow | `The Honest Meal` | Sam |
| `2` | Britain | `The Wayfarer Tavern` | Tika |
| `3` | Jhelom | `The Sword and Keg` | Nicole |
| `4` | Yew | `The Slaughtered Lamb` | Duclas |
| `8` | New Magincia | `The Humble Palate` | Felicity |
| `19` | West Britanny | `The Blue Boar Tavern` | Jaymes |
| `22` | Paws | `The Cat's Lair` | Dr. Cat |
| `24` | Buccaneer's Den | `The Fallen Virgin` | Nikki |
| `30` | The Lycaeum | `The Folley Tap` | Rob |

**Horse traders** (3 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `6` | Trinsic | `Horse & Rider` | Hettar |
| `20` | North Britanny | `The Stablehouse` | Theoan |
| `22` | Paws | `Wishing Well Horses` | Ferru |

The shipped horse-trader tables actually hold four rows. The fourth is scene
`30` (The Lycaeum): its shop-name entry is a null reference — there is no shop
name at all, not an empty one — while its vendor name (`Simplon`) and its base
price (`190`) are both present. No `0x83` trigger exists anywhere in the shipped
rosters for scene `30`, so the row is unreachable in ordinary play. It is
mentioned here for completeness only; implementations should publish and reach
the three rows above and must not treat scene `30` as a fourth stable.

**Shipwrights** (4 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `3` | Jhelom | `Island Shipwrights` | Bantral |
| `5` | Minoc | `The Crow's Nest` | Captain Blyth |
| `21` | East Britanny | `The Oaken Oar` | Master Hawkins |
| `24` | Buccaneer's Den | `The Rusty Bucket` | Jones |

**Reagent vendors** (5 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `1` | Moonglow | `The Herbalist` | Nilrem |
| `4` | Yew | `Healers Herbs` | Madam Pendra |
| `7` | Skara Brae | `The Alchemist` | Toama |
| `23` | Cove | `Mysticism` | Enlor |
| `30` | The Lycaeum | `The Sharper Mage` | Virden |

**Guildmasters** (3 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `8` | New Magincia | `The Den` | Braunam |
| `22` | Paws | `The Guild` | Danfits |
| `24` | Buccaneer's Den | `The Nemesis` | Daem |

**Healers / sanctums** (7 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `5` | Minoc | `The Healers Mission` | Regina |
| `6` | Trinsic | `Wounds of Honour` | Leila |
| `7` | Skara Brae | `The Spirit Healers` | Temptious |
| `21` | East Britanny | `Healers' Sanctum` | Milan |
| `23` | Cove | `Sanctuary` | Jessica |
| `30` | The Lycaeum | `The Shield of Truth` | Faye |
| `31` | Empath Abbey | `The Empath` | Jessip |

**Inns** (6 rows):

| Scene | Location | Shop name | Vendor |
|---:|---|---|---|
| `2` | Britain | `The Wayfarer Inn` | Donya |
| `3` | Jhelom | `The Warrior's Stead` | Gremnor |
| `7` | Skara Brae | `The Haunting Inn` | Rogi |
| `20` | North Britanny | `Hotel Brittany` | Terbor |
| `22` | Paws | `The Smugglers' Inn` | Lorien |
| `24` | Buccaneer's Den | `The King's Ransom Inn` | Ransack |

Each scene-byte appears at most once inside a single shop kind's table, so a
scene never hosts two shops of the same kind, and the search result is
unambiguous.

There is no graceful path for the opposite case. If a shop trigger ever fires
for a kind whose table does not list the active scene, the shipped search does
not refuse and does not fall back to row zero: it leaves the row index one past
the end of the kind's list, and every per-row table then reads a neighbouring
kind's data. The shipped rosters never produce that state — every shop NPC sits
in a scene its kind's table lists — so it is an error case rather than a
behaviour to reproduce. A clean implementation should reject the trigger and
leave the conversation alone.

### 8.1 Weaponsmith and armourer

After a randomised greeting ("Hail, friend! Wouldst thou Buy or Sell?"), the player presses one of three keys:

- `B` (Buy) — the overlay renders the shop's "We have:" line followed by an
  item listing built from the current shop's eight-entry stock table. Slots are
  assigned to menu letters `a` through `h`, but the row ends early at the
  `0xFF` terminator. The player picks a letter; the overlay confirms, refuses
  if the corresponding party inventory counter is already capped, runs the
  affordability check, deducts gold, increments the shared equipment counter,
  and re-prompts.
- `S` (Sell) — the overlay opens an inventory browser over the party's carried
  equipment counters. It skips empty counters, refuses item ids the arms shop
  does not buy, quotes the shop's offer, asks for `Y`/`N`, and on acceptance
  adds gold and decrements the selected equipment counter. Used ammunition is
  explicitly refused rather than bought back.
- *Space* — Exit with a randomised farewell. Any other key simply re-polls the
  Buy/Sell prompt without output.

Each sub-menu re-prompts internally after a completed action, so the player can
buy or sell repeatedly without leaving it. Leaving a sub-menu, however, ends
the visit: control goes to the farewell rather than back to the Buy/Sell
prompt. Only a key that is neither `B`, `S`, nor an exit key re-polls that
prompt. The buy side refuses capped counters and insufficient gold without
changing inventory. The sell side refuses empty, unsellable, or explicitly
excluded equipment without changing inventory.

The stock arms buy rows are scene-local and use the equipment item-id order in
`catalogs/item-list.md`. `0xFF` is the end-of-row marker. `0x00` is not empty in
this table; it is item id `0`, Leather Helm. In the shipped rows below, slot
`h` is the terminator for every shop, so the visible menu choices are `a`
through `g`.

| Scene | Location | Shop | a | b | c | d | e | f | g | h |
|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `2` | Britain | `Iolo's Bows` | 16 | 17 | 26 | 27 | 28 | 29 | 36 | `0xFF` |
| `3` | Jhelom | `Naughty Nomaan's` | 19 | 24 | 46 | 22 | 3 | 6 | 25 | `0xFF` |
| `4` | Yew | `Arms of Justice` | 0 | 9 | 10 | 18 | 21 | 37 | 38 | `0xFF` |
| `5` | Minoc | `Darkwatch Armoury` | 2 | 4 | 11 | 23 | 30 | 24 | 31 | `0xFF` |
| `6` | Trinsic | `The Paladin's Protectorate!` | 32 | 33 | 34 | 2 | 5 | 12 | 14 | `0xFF` |
| `17` | Lord British's Castle | `North Star Armoury` | 1 | 7 | 13 | 14 | 30 | 37 | 43 | `0xFF` |
| `24` | Buccaneer's Den | `Buccaneers Booty` | 0 | 10 | 16 | 20 | 23 | 19 | 42 | `0xFF` |
| `26` | Bordermarch | `The Shattered Shield` | 7 | 32 | 36 | 27 | 31 | 44 | 45 | `0xFF` |
| `32` | Serpent's Hold | `Siege Crafters` | 1 | 13 | 28 | 29 | 34 | 22 | 25 | `0xFF` |

When a valid buy letter is selected, the shop computes the adjusted price,
stores it in the `%` substitution, and renders the selected item's
SHOPPE.DAT description record. The item-description selector is keyed by
equipment item id:

| Equipment id(s) | SHOPPE.DAT buy quote record(s) |
|---|---|
| `0..7` | records `8..15` respectively |
| `9..14` | records `16..21` respectively |
| `16..34` | records `22..40` respectively |
| `36..38` | records `41..43` respectively |
| `42..46` | records `44..48` respectively |
| `8`, `15`, `35`, `39`, `40`, `41`, `47` | no arms-buy quote record in the traced selector; these ids are not present in the nine stock rows |

The stock list itself is rendered from the row above. Each visible slot prints
its menu letter followed by the item's display name. The display name is the
canonical equipment name from `catalogs/item-list.md`, *except* that a
canonical name of thirteen characters or more is replaced by that item's
shorter panel label, so the entry fits the shop's list column. The affected
equipment ids and their shorter labels are published in `catalogs/item-list.md`
Section 5.1.2. The list is preceded by a heading line and one of four resident
"what we have" call lines chosen with a uniform `0..3` draw:

| Draw | Stock-call line |
|---:|---|
| 0 | `What may I show thee?` |
| 1 | `Which wouldst thou like to see?` |
| 2 | `What is thine interest?` |
| 3 | `Which would ye see?` |

After the item description, the buy path chooses one of four literal
confirmation prompts uniformly: `Wouldst thou buy one?`, `Wilt thou take it?`,
`Wish ye it?`, or `May I get one for thee?`. The player must answer `Y` or
`N`; other keys re-prompt without changing gold or inventory. `N` echoes `No`
and exits that item quote back to the buy list. `Y` echoes `Yes` and first
checks whether the carried equipment counter for that item is already `99`; if
so it prints the fixed refusal `"Thou canst not carry any more!"` followed by
the shopkeeper-attribution tail `says <shopkeeper>.`, waits for one key, and
returns to the buy list.

It then checks party gold against the adjusted price. On short funds the shop
prints one line chosen uniformly from a four-entry resident pool, wrapped in
the shopkeeper-attribution tail `yells <shopkeeper>.`:

| Draw | No-credit bark |
|---:|---|
| 0 | `Can't pay?! Out with ye, orc-face!` |
| 1 | `What be ye trying to pull? OUT!` |
| 2 | `OUT, SLIME!` |
| 3 | `BEAT IT!` |

The short-funds branch leaves gold and inventory unchanged and **exits the
whole arms buy flow**, not just the item quote: unlike a decline, which returns
to the stock list, it leaves the buy list immediately, and because leaving the
buy list ends the visit the next thing the player sees is the farewell. This is
the same statement as the "exits the shop flow" wording in the Section 8.A
timing table and resident-literal table; the passages describe one behaviour.

A successful purchase debits the adjusted price, applies
the normal post-transaction surcharge, increments the carried equipment counter
or caps arrows/quarrels at `99`, and prints the fixed success line `Sold!`.
There is no separate successful-purchase item-name template. It then prints the
post-item prompt `"Anything else,` followed by `milady?` when the speaking
member's gender field is the female value and `sir?` otherwise, or `then?` when
no transaction has completed in this visit.

Invalid buy selectors, including letters at or beyond the `0xFF` terminator,
do not print a refusal line. The buy menu simply keeps waiting for a valid
letter, Space, or Escape. Item id `0` is ordinary stock: it uses the same
menu-name source as the other equipment ids and quote record `8`.

The `S` (Sell) branch is the one arms path that owns its own screen furniture;
its side-panel geometry is specified in Section 8.A.

### 8.2 Guildmaster (magic shop)

After the greeting, the player chooses from a three-item letter menu — typically `a` Keys (skeleton keys), `b` Gems (gem-of-vision), `c` Torches. The player picks a letter and a quantity, the affordability check runs, gold is deducted, and the item is added to inventory. The guildmaster does not buy back; commerce is one-way. There is no class restriction. Spells are *not* sold here; they are mixed by the player from reagents (see `magic.md`).

The stock guild prices are:

| Guild shop | Keys | Gems | Torches |
|---|---:|---:|---:|
| The Den | 190 | 255 | 12 |
| The Guild | 160 | 200 | 11 |
| The Nemesis | 185 | 225 | 25 |

### 8.3 Healer / sanctum

The healer entry first asks whether the party wants treatment. `Y` enters the
service menu, `N` exits to the farewell path, and other keys repeat the prompt.
The service menu accepts three treatment letters plus the normal exit keys:

- `C` (Cure) — removes the Poisoned status from a chosen party member.
- `H` (Heal) — restores the chosen party member's current hit points to
  maximum without changing status.
- `R` (Resurrect) — restores a Dead party member to living status through the
  same resurrection helper used by the spell system, then tops current hit
  points back up to the member's maximum.
- Space or Return — leaves the service menu and prints the exit line.

Each mode prompts for a party member first, then validates whether that member's
condition is treatable by the selected service. Cure requires Poisoned status.
Heal refuses Dead members and members already at maximum HP; it can heal a
Poisoned member's HP but does not cure the Poisoned status. Resurrect requires
Dead status; Ashes and other non-Dead statuses are refused rather than treated
as dead. That is a corollary of a single equality test against Dead, not a
separate Ashes check - see `systems/magic.md`, which owns the shared
resurrection gate. An untreatable selection prints the shared healer refusal and
returns to the service menu without quoting a price or changing gold, status,
or HP.

On the ordinary paid branch, the healer quotes the selected treatment's local
price, runs the standard affordability check against the party gold word,
deducts gold, applies the treatment, refreshes the visible character status,
and returns to the service menu. Paid resurrection uses the shared resurrection
side effects from `systems/magic.md` -- status restoration, mana rebuild, any
experience/level adjustment, and maximum-HP recomputation -- but the healer
then restores current HP to maximum instead of leaving the member at the spell
path's 1 HP. A Minoc branch is confirmed for Cure and Heal:
the shop-entry tables resolve that scene to **The Healers Mission** and Regina
as vendor, and the healer flow applies those two services with distinct text
without entering the ordinary price/affordability path. Resurrection does not
currently show that bypass in the traced flow.

The stock healer headline fees are:

| Healer | Cure | Heal | Resurrect |
|---|---:|---:|---:|
| The Healers Mission | bypass | bypass | 200 |
| Wounds of Honour | 25 | 40 | 215 |
| The Spirit Healers | 30 | 45 | 225 |
| Healers' Sanctum | 35 | 50 | 237 |
| Sanctuary | 40 | 55 | 247 |
| The Shield of Truth | 15 | 60 | 249 |
| The Empath | 10 | 65 | 262 |

The resident cost table also has an eighth unmatched row (`Cure 1`, `Heal 70`,
`Resurrect 270`), but no shipped healer scene maps to that shop-instance row.

### 8.4 Innkeeper

The inn is the most stateful shop in the system. On entry, it first scans the
save-backed inn registry for guests whose leading per-slot scene marker matches
the current inn scene. With no matching guests, Pickup refuses with the
"No one here is from thy party!" line. With exactly one matching guest, the
guest-selection display can be skipped because there is only one candidate.
With multiple guests, the inn renders a full-screen "Guest Register" list before
the player selects the action target.

The multi-guest pickup register uses a fixed text-window presentation. It
selects text window `1`, sets that window to cell rectangle `(24, 1)..(38, 9)`,
clears it, then widens the right edge to `(24, 1)..(39, 9)` for the framed
register. The frame/list renderer uses window-local cursor positions
`(0, row)` and `(14, row)` for the vertical row borders over rows `1..7`, places
the register heading at `(1, 1)` and subheading at `(1, 2)`, then prints each
matching guest line at a row-local cursor derived from the enumerated guest.
Before the post-register selection and prompt loop, the helper restores active
text window `2`. These are text-cell coordinates in the fixed 40-by-25 text
grid, not pixel coordinates.

Entering the inn's service menu unconditionally clears the single shared
timed-effect slot specified in `systems/magic.md`, before the innkeeper's
prompt is even printed. Because that slot holds one effect at a time, walking
up to an innkeeper cancels an active Protection, Quickness, Mass Charm, Negate
Magic, or Negate Time, and also strips the otherwise permanent Amulet of Lord
British, Crown of Lord British, and Black Badge auras. This happens on entry
and is not conditional on renting a room or on paying anything.

The main menu accepts three actions:

- `R` (Rest for the night) — the party sleeps in the inn's beds. The world clock
  advances through the inn/rest pipeline and the paid rest recovery pass runs.
  Non-dead party members have current hit points restored to maximum. Avatar
  and Mage set current MP to Intelligence; Bard sets current MP to half
  Intelligence; other classes do not receive this MP branch. Sleeping status is
  cleared to Good. Poisoned members die during the recovery pass and return
  with zero current hit points. The shared hourly provision cadence may apply
  as the clock advances. The quote is
  `adjusted(base_rate * travelling_party_size, speaker_intelligence)`. This is
  a paid, safe town rest rather than a wilderness ambush-risk camp.
- `L` (Leave a companion) — the player picks a party member to leave. The chosen member's 32-byte slot record (name, gender, class, status, stats, hit points, experience, level, equipment) is moved into the inn registry view, that guest slot's leading marker is set to the current inn scene, the stored stay counter is cleared to zero, the active roster is compacted, and the party-size byte is decremented. A quoted deposit of `adjusted(base_rate * 10, speaker_intelligence)` is debited before the transfer completes.
- `P` (Pick up a companion) — the inn's registry is rendered as a guest list when more than one guest at this inn can be chosen. The pickup bill first computes `adjusted(base_rate * 10, speaker_intelligence)`, then multiplies that adjusted local lodging charge by the selected guest's stored stay counter, treating zero as one billable unit. The guest's record is copied into the next active roster slot, the party-size byte is incremented, the registry view is compacted as needed, and the returned slot's former guest marker is cleared to zero.

The inn registry is the inn's persistent state: a 16-slot, save-backed resident
view with the same 32-byte stride as party records. It is a shifted legacy view
over the save image rather than an independent post-roster block. Each registry
slot begins with a scene marker indicating *which* inn the guest is at, followed
by the copied character payload used by pickup. To enumerate guests at the
current inn, the engine walks the 16 slots and compares each slot's leading
scene marker with the current scene. Pickup clears a returned slot by writing a
zero marker; guest enumeration treats any nonmatching marker as "not a guest at
this inn", so compatible writers should use zero for empty or cleared slots.

Because the registry is part of the save image, a player can leave a companion at an inn, save, reload weeks later, and pick up the companion. Each 28-day month rollover advances the stored stay counter, capped at 25, so a long-lodged guest can produce a larger bill.

The stock inn rate rows are:

| Inn | Base room rate | Minimum-gold gate |
|---|---:|---:|
| The Wayfarer Inn | 2 | 3 |
| The Warrior's Stead | 3 | 4 |
| The Haunting Inn | 2 | 3 |
| Hotel Brittany | 3 | 2 |
| The Smugglers' Inn | 2 | 2 |
| The King's Ransom Inn | 3 | 2 |

A morbid pickup path applies: lodged guests can be returned dead. If the stored guest status is Poisoned when the guest is picked up, the pickup path converts the returned record to Dead, clears current hit points, and prints "Thy friend has died, by the way." No separate lodging-death clock is visible in the pickup path; a companion left while Poisoned is enough to trigger the death conversion on pickup.

The inn refuses service in several cases: no guests from the party are registered at the current inn when picking up, the travelling party is already at the six-member cap ("one must first be left behind"), the party is down to one member when trying to leave someone, the selected record cannot be moved, or gold is below the minimum or quoted room charge.

### 8.5 Tavernkeeper

The tavern entry runs a smaller menu than the arms entry. The shopkeeper greets
and asks whether the Avatar wants a drink; `Y` enters the local menu, while
`N` or space leaves. Each tavern has its own menu text and state selector, so
the visible letters and flavour records vary by location.

The drink menu is state-driven, and the menu state comes from the tavern row,
not from a fixed key layout. There is no fixed `A` drinks key, no fixed `F`
food key, no fixed `M` provisions key, and no `B` "Bye" key anywhere in this
flow. The four action letters visible at a given tavern are the four
state-indexed letters in the Section 6 table, and the only exits from the
post-list menu are Space, Escape, and Return. Any key that is neither an exit
key nor one of that state's four letters is ignored, leaving the list on screen.

The list body itself is also selected by menu state rather than by tavern, so
all five state-`0` taverns print the same list record and differ only in their
prices. In `SHOPPE.DAT` ordinals the post-`Y` list records are `69`, `70`,
`71`, `72` for states `0..3`, and the post-branch "anything else" follow-up
records are `73`, `74`, `75`, `76` for the same states. Both sets sit
immediately after the shared tavern farewell row in Section 8.A, which is a
useful cross-check.

After any accepted branch completes, the tavern clears the text window, prints
the resident "anything else for thee?" line, and waits for `Y` or `N`. `N`
prints the resident decline echo, prints the beg-thy-pardon continuation, and
leaves. `Y` renders the state's follow-up record and returns to the post-list
key wait. Completing a branch also sets the tavern continuation state, which is
what makes the sage/lore letter reachable; before that, pressing the sage/lore
letter is ignored. One branch outcome is deliberately excluded: a branch that
reports "nothing was bought" — such as a provision purchase with a quantity of
zero — still runs the "anything else" tail but does not establish continuation,
so the lore letter stays inert until something is actually bought.

One state-specific letter buys a round for each
living party member using the stock per-person table in Section 6. The Blue
Boar Tavern's `W` branch instead opens a six-choice fixed-price drink list. A
paid drink branch deducts gold and prints the tavern success line; the drink
itself has no traced persistent effect on party state. Failed payment returns
to the menu without changing gold.

One tavern/meal-counter menu branch sells provisions rather than flavour
drinks. It is reached through the state's *provision* letter, which is `R`
(Rations) at the five state-`0` taverns and `P` (Provisions) at The Humble
Palate; states `1` and `2` have no provision letter, so the provision branch is
unreachable at The Blue Boar Tavern, The Slaughtered Lamb, and The Fallen
Virgin. Those three sell only their round/meal and secondary items.

The branch runs in this order:

1. Echo the pressed provision letter, then compute the Intelligence-adjusted
   per-unit price from the tavern's provision base in Section 6.
2. Render one quote record drawn uniformly from a six-record pool — `SHOPPE.DAT`
   ordinals `77` through `82` — with the adjusted price filling the `%`
   substitution. All six say the same thing in different words: one pack is
   twenty-five servings and costs that much gold. The draw happens once, when
   the quote is rendered.
3. Prompt for a quantity as a typed number.
4. Run the per-unit pay loop of Section 6.1.

The outcomes, and what each does to the visit, are:

| Outcome | Text | Effect on the tavern visit |
|---|---|---|
| Quantity of zero | A short resident dismissal | Stays in the tavern; the "anything else" tail runs but **continuation is not established**, so the sage/lore letter stays inert |
| At least one unit served, full quantity | Blank-line tail, then the post-transaction surcharge | Stays in the tavern; continuation established |
| At least one unit served, gold ran out | A resident line reporting the number actually afforded | Stays in the tavern; continuation established; no surcharge |
| Nothing served, party food is `3` or more | A resident refusal accusing the party of having neither gold nor need, attributed to the shopkeeper | **Ends the visit** — control leaves the tavern through the farewell path |
| Nothing served, party food is below `3` | The shopkeeper adds `1` to the food counter and renders `SHOPPE.DAT` ordinal `90`, a table-scraps brush-off | **Ends the visit** |

That last row is the only charitable food source in the shop family, and it is
one unit of food, not one pack. It fires only when the party could not afford a
single pack *and* is nearly out of food, so it cannot be farmed for provisions.

### 8.6 Food and provisions boundary

Food is a shared party counter. The confirmed shop-adjacent purchase route is
the tavern/meal-counter provision branch described above. It writes the same
food counter used by time, rest, starvation, search, and treasure systems.

The analyzed DOS baseline exposes no separate Talk-entered food/provisions
merchant arm. The earlier hypothesis that the SHOPPES2 `F`/`S` menu was a food
merchant is superseded: that same public menu is the shipwright sale flow
described in Section 8.7, where `F` buys a Frigate, `S` buys a Skiff, and the
resident state tested by the flow is the outdoor pending-vehicle queue rather
than a provisions capacity byte.

For compatibility, do not implement a food-merchant purchase path from the
shipwright `F`/`S` flow or add a standalone provisions merchant to the baseline
shop model. Tavern/meal-counter service is the shop-owned food-purchase route.

### 8.7 Ship broker / shipwright

The shipwright entry is a Talk-triggered vehicle sale flow. It opens with a
small letter menu: `F` offers Frigates and `S` offers Skiffs, while *space* or
Escape exits. Each current shipwright has local prices for both sale classes.
The flow quotes the selected price, asks for confirmation, runs the ordinary
affordability check, and debits gold on success.

Both quotes are Intelligence-adjusted from the speaking party member with the
same shape used by inn charges and horse sales:
`adjusted(base, Intelligence) = base + trunc(base * (100 - 3 * Intelligence) / 100)`,
truncating toward zero.

The stock shipwright rows carry the two base prices *and* a fixed delivery
coordinate. The delivery coordinate is a per-shipwright value held beside the
price rows in the same resident shop table; it is **not** the town's exterior
entrance or exit cell, and it is not derived from the scene-to-exit mapping in
`systems/town-mode.md` or `systems/doors-and-z-transitions.md`. It is an
overworld map cell in the same coordinate space as the location entrance
coordinates in `catalogs/gazetteer.md`, and in every row it is near — but not
equal to — the town's own entrance cell.

| Scene | Shipwright | Frigate | Skiff | Delivery cell (overworld X, Y) |
|---:|---|---:|---:|---|
| `3` (Jhelom) | Island Shipwrights | 600 | 200 | `(39, 221)` |
| `5` (Minoc) | The Crow's Nest | 753 | 175 | `(151, 21)` |
| `21` (East Britanny) | The Oaken Oar | 650 | 125 | `(79, 109)` |
| `24` (Buccaneer's Den) | The Rusty Bucket | 700 | 100 | `(138, 159)` |

Unlike ordinary inventory shops, a successful shipwright purchase does not write
a simple carried-item counter. It writes a shared pending vehicle-acquisition
state used by the outdoor loop, and copies the row's delivery coordinate into
the pending X and Y bytes at the same moment. The next overworld entry consumes
that state and places the watercraft.

The delivery pass, which runs once before the first overworld turn after the
purchase, does the following:

1. Acquire an active-object slot through the ordinary allocator described in
   `systems/active-objects.md`.
2. Write the vehicle tile into both the object's type byte and its frame byte:
   the ship-family tile for a Frigate, the skiff-family tile for a Skiff, in
   both cases the east-facing member of the family (facing index `1` in the
   transport-marker convention of `systems/vehicles.md`).
3. Write the row's delivery X and Y into the object's coordinate bytes and set
   its floor byte to the overworld plane.
4. Set the hull-condition auxiliary byte to `99`.
5. Set the carried-skiff auxiliary byte from the queued acquisition class: `2`
   for a plain Frigate, `3` for a Frigate that absorbed one extra purchased
   Skiff, `0` for a standalone Skiff.
6. Clear the pending state.

The two purchase classes use different pending payloads:

- **Frigate.** Queues a ship-family active object with hull condition `99` and
  an initial cargo of two skiffs. If a Skiff is bought while that frigate is
  still pending delivery, the queued frigate's skiff count is incremented
  rather than placing a second object.
- **Skiff.** Queues a standalone skiff-family active object when no frigate is
  pending.

Duplicate purchases before the queued delivery is consumed are handled inside
the shipwright menu:

- Selecting **Frigate** while any shipwright delivery is already pending shows a
  limited-dock-space / special-delivery quote and asks for confirmation. A Yes
  answer runs only the affordability/refusal gate for that quote; it does not
  debit gold, queue a second Frigate, or alter the pending watercraft. The
  amount that gate tests is a fixed `10000`, not the shipwright's Frigate price
  and not an Intelligence-adjusted value, and the gold counter's ordinary
  ceiling is `9999`. The check therefore always fails, and the visible result
  is always the shortfall refusal that names what the party can afford.
- Selecting **Skiff** while a Frigate is pending treats the Skiff as ship cargo:
  after the ordinary confirmation and affordability check, gold is debited, no
  second active object is queued, and the pending Frigate's skiff count is
  incremented.
- Selecting **Skiff** while a standalone Skiff is pending refuses the extra
  Skiff purchase and leaves the pending state and gold unchanged.

The shipwright dialogue is drawn from the ship-broker record cluster. Beyond
the shared entry-greeting and closing-bark rows in Section 8.A, the deterministic
records this flow renders are: the menu/prompt body at the top of each loop
pass (record `119`), the Frigate quote (`117`), the Skiff quote (`118`), the
shared take-it confirmation (`126`), the limited-dock-space quote used when a
delivery is already pending (`125`), the skiff-stowed-as-cargo line (`120`),
the already-have-a-skiff refusal (`121`), the delivery announcement printed
just before the delivery coordinate is queued (`123`), and the post-sale
"anything else" body (`124`).

Ship facing and sail-state encodings for the placed object are owned by the
vehicle marker table in `systems/vehicles.md` rather than by the shop flow.

### 8.8 Sage / rumour vendor

The sage uses free-text input rather than letter selection. After a banner ("Of
what wouldst thou hear my lore?") the player types a keyword of up to fifteen
characters. Empty input exits.

The sage checks the input against the fixed 26-row table in
`catalogs/sage-rumours.md`. Matching is case-insensitive and uses a strict
topic-boundary check: after the four-letter topic key matches, the next input
character must be either the end of the input or a space. Partial prefixes
therefore do not match longer stored topics, and longer words that merely start
with a topic are rejected. On no match, the sage replies "That, I cannot help
thee with." and the keyword input is re-prompted.

Every topic carries a gold fee, a subject string, and a destination selector.
When a topic matches, the sage renders SHOPPE.DAT record 84 to quote the fee
and ask for confirmation; the `%` placeholder is the row fee. If the player
refuses, the sage exits. If the player accepts but the party cannot pay, the
sage renders SHOPPE.DAT record 91, the paying-customers refusal, and exits
without giving a rumour. If the player confirms and has enough gold, the fee is
deducted, the topic's subject fills the `&` substitution, the selected
destination fills the `*` substitution, and one of the four shared success
templates is selected at random from SHOPPE.DAT records 85-88. The
success-template draw is reached only after confirmation and successful payment;
refusal and short-funds exits do not consume that draw.

The same topic table is used by the traced sage flow. There is no per-sage
16-row rumour table. The tavern/menu state only controls which visible action
letter reaches the sage prompt.

### 8.9 Reagent vendor

The reagent entry builds a compact letter menu from the current herbalist's
nonzero reagent entries. It scans the fixed reagent list in order, skips any
zero-priced reagent, and assigns menu letters only to the reagents actually
sold by that herbalist. In the analyzed DOS asset set, each herbalist stocks at
most five reagent types, so the visible choices fit in `A..E` even though there
are eight possible reagents globally.

The player picks one of the displayed letters and then a quantity. The
affordability check runs against quantity times per-ounce price; on success,
gold is deducted and the corresponding reagent counter is incremented. Invalid
letters do not purchase anything; exit keys leave the reagent loop and return to
the shop farewell path.

### 8.10 Horse-trader sale placement

The Talk-entered SHOPPES helper formerly described as a stationary-display
purchase is the horse-trader sale arm. It does not publish an arbitrary
display-stock table, sale item id, carried-item destination, or per-display
SHOPPE text selector. Its sale item is always a horse active object.

On entry, the flow first walks the active-object table from slot zero and takes
the first free slot. It then probes the four cardinal cells adjacent to the
party using a fixed four-entry offset pair, in the order **south, north, east,
west** (that is, `(0, +1)`, `(0, -1)`, `(+1, 0)`, `(-1, 0)` with world Y
increasing southward). Each candidate is first rejected by the shared
occupancy/NPC classifier for the current floor; a surviving candidate is
accepted only if its map tile is one of the three horse-sale placement tiles
`0x44`, `0x45`, or `0x05`. The first accepted candidate wins; probing does not
continue to compare candidates. If all four probes fail, or if no free object
slot was found, the shop prints the refusal line and exits without a purchase —
both failures take the same exit.

There is no display-marker ordinal, no per-marker stock row, and no marker-order
selector. The probe result supplies a placement *cell* and nothing else.

The local shop instance is already selected by the Talk shop dispatch from the
current scene. That scene-selected row supplies the stable name, vendor name,
and base horse price listed in Section 3; the nearby marker does not select a
different stock row.

The purchase loop is Y/N driven:

- Space or `N` exits without a purchase and returns through the shop farewell
  path.
- `Y` prints the item offer, asks for confirmation, and aborts cleanly on a
  negative answer.
- If the confirmed price exceeds party gold, the shop prints its insufficient
  funds line and exits without placing a horse.
- On success, the price is deducted, the normal post-transaction surcharge
  helper may run, and a horse-family active-object record is written into the
  free slot: the base horse tile `0x10` in both the type byte and the frame
  byte, the accepted probe cell in the coordinate bytes, the party's current
  floor in the floor byte, and all three auxiliary/animation bytes cleared to
  zero. The local view is then redrawn so the boardable horse is visible.

The exit path reports one of three outcomes to the shared farewell dispatcher:
a completed purchase, a short-funds refusal, or a plain decline. The quote text
is a single deterministic record from the horse-trader cluster (ordinal `104`),
rendered with the adjusted price substituted in.

This flow is distinct from arms/guild/reagent stock. It does not browse a
lettered stock table, does not deplete a shop inventory row, and does not write
a carried item into a party member record.

## 9. Karma effects

The karma system does not directly modulate shop headline pricing or inventory.
The five stat-sensitive paths of Section 6 — arms buy and sell quotes, the
horse-trader sale, inn room and lodging charges, both shipwright vessel classes,
and the tavern/meal-counter provision unit price — vary with the speaking party
member's Intelligence, but not with virtue standing. Reagent, treatment,
guild, and other decoded headline prices come from their resident tables rather
than from karma. The random post-transaction surcharge is also not a karma price
modifier; it is gated by the presence of the Shadowlord of Falsehood in the
settlement rather than by virtue standing. This is a deliberate departure from Ultima IV, where shopkeepers
cheated the dishonourable on prices and item availability.

Related boundaries:

- **Shopkeeper recognition.** Current shop-entry evidence does not show a
  karma-owned recognition gate before the shop overlay starts. Story or quest
  refusals by ordinary named NPCs belong to the conversation system, not to the
  shop pricing or inventory model.
- **Healer mission service.** The Minoc / The Healers Mission Cure/Heal branch
  is tied to town-scene identity, not to virtue standing. Current evidence does
  not show a karma price modifier for healer service.

The sage rumour path is also not currently treated as a karma-quality branch.
The decoded shop flow is a paid lookup by topic, fee, destination, and record
template. There is no "cheating the Avatar" mechanic: no shopkeeper
double-prices when reputation is low, and no decoded shop stock changes with
virtue standing.

## 10. Hooks to other systems

### 10.1 Conversation

Shop overlays are reached through the Talk entry gate described in Sections 2
and 3. The conversation system owns target resolution, the caller context word,
and the resident handoff state, but shopkeepers do not interrupt and resume a
normal `.TLK` keyword response. When a shop overlay returns, the Talk action is
finished. A shopkeeper has one resident shop trigger at a time, so all visible
commands inside that shop flow belong to the selected shop kind.

### 10.2 Time

Several shop interactions read or write the world clock:

- **The `@` time-of-day substitution** reads the hour byte on every record render. Greetings vary by morning / afternoon / evening.
- **The inn rest mode** advances the clock through the rest pipeline until the
  stay completes. It runs the paid inn recovery pass described above, without
  the wilderness ambush risk.
- **The inn pickup mode** computes an Intelligence-adjusted ten-unit local
  lodging charge first, then multiplies it by the selected guest's stored stay
  counter. A zero counter is billed as one unit. The time system increments the
  counter on each 28-day month rollover, capped at 25.

Shop overlays do not consume turns themselves; the time the player spends in a shop menu does not advance the clock. Only the inn rest mode advances time as part of its action.

### 10.3 Save / load

Three pieces of shop state are part of the save image:

- **The party gold word** is debited by shop purchases and services and is
  persisted with the rest of the resident state.
- **The queued shipwright delivery** — the pending vehicle-acquisition class
  byte and the pending delivery coordinate pair of Section 6.1 — sits in the
  saved band as well, so a vessel bought but not yet delivered survives a save
  and reload and is placed by the next overworld entry. An earlier revision of
  this section counted only two saved pieces and omitted it, which contradicted
  Section 6.1.
- **The inn registry** lives in the resident save image and is included in save/load. A player can leave a companion, save, reload, and pick the companion up — the registry's per-slot inn marker tells the inn-pickup logic which guest belongs to which inn. Leave clears the guest's stored stay counter to zero; pickup clears the returned slot's marker to zero after moving the guest back into the active roster.

Per-shop inventory tables, per-treatment cost tables, and `SHOPPE.DAT` itself are read-only resources baked into the resident data and the disk file. They do not change between save cycles.

### 10.4 Gold and inventory

The party's gold word is the shared resident counter every gold-handling system
reads and writes — shops, conversation gold gifts, combat treasure, NPC bribes,
the find-treasure handler. There is no per-character or per-shop sub-account.
Gold mutations that use the shared arithmetic helpers saturate or floor at the
caller-supplied boundary rather than wrapping; ordinary play uses the `9999`
gold limit documented in the save-format and inventory specs. The shop
surcharge uses the same gold word and is therefore part of the persisted
post-transaction state.

Each shop kind writes a slice of the inventory or save state: weaponsmith /
armourer write weapon and armour counters; guildmaster writes keys / gems /
torches; healer writes the chosen member's status byte, current HP, and for
resurrection the related mana/experience/level/maximum-HP fields owned by the
shared resurrection helper; herbalist
writes one of the eight reagent counters; innkeeper copies 32-byte party records
between the active table and the inn registry; sage-style rumour flows debit
gold for paid rumours; horse traders write a horse active object through the
Talk-entered vehicle-sale helper; ship brokers write a pending vehicle
acquisition state consumed by overworld entry to place a frigate or skiff active
object.
The tavern drink branch writes nothing persistent in the traced flavour-drink
flow. The tavern/meal-counter provision branch writes the shared food counter
and debits gold per served unit; this branch is intentionally not atomic across
the requested quantity because partially affordable purchases persist. The
analyzed baseline has no separate Talk-entered food merchant write; the formerly
suspected provisions/capacity state belongs to the shipwright pending-vehicle
queue. The decoded inventory writes are fixed-offset stores into the save
image's inventory region.

## 11. Shop Boundaries And Remaining Catalog Work

The analyzed shop-flow contract is complete at gameplay depth: Talk-entry shop
dispatch, stock-shop menus, arms buy/sell behavior, guild purchases, healer
treatments, reagent availability, tavern drinks, meal-counter provisions,
sage topics, horse-trader sale, shipwright pending delivery, inn rest and guest
registry behavior, shop surcharge, persistence, and karma non-modulation are
fixed.

- Remaining equipment class restrictions and armour defence values are tracked
  by `catalogs/item-list.md` and `formats/data-ovl.md`.
- Shop-owned transcript clear/append, prompt wait, and cursor-origin behavior
  is specified in Section 8.A, including both side-panel geometries. The
  inherited conversation window is also settled there: no shop or conversation
  path installs a rectangle, colour, or cursor origin on text window `2`, but
  the gameplay-screen assembly does shape it once to the message-window
  rectangle, so it does not keep the boot-time full-screen default. See
  `systems/text-output.md` Sections 9 and 10.1.
  What is left is not a shop question at all — it is how the display pipeline
  composites the viewport and status artwork underneath that full-screen text
  window, which belongs to the renderer specs.

## 12. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md`,
  `u5-decomp/functions/SHOPPES_OVL/`, and the private
  SHOPPES healer-main trace — weaponsmith / armourer, guildmaster, healer /
  sanctum, herbalist, horse-trader sale, and post-transaction surcharge
  behavior.
- `u5-decomp/functions/SHOPPES2_OVL/_OVERVIEW.md`,
  `u5-decomp/functions/SHOPPES2_OVL/`, and
  local SHOPPES2 shipwright control-flow analysis — tavernkeeper, ship broker,
  sage, and the correction that the traced `F`/`S` pending-action flow belongs
  to shipwright sales rather than a provisions merchant.
- `u5-decomp/functions/SHOPPES3_OVL/_OVERVIEW.md`,
  `u5-decomp/functions/SHOPPES3_OVL/`, and
  `u5-decomp/functions/SHOPPES3_OVL/` — innkeeper
  pricing, rest recovery, inn registry, and persistent guest-lodging state.
- `u5-decomp/notes/oq-closures_2026-08-22_magic-talk-services.md` — the inn
  menu's entry clear of the shared timed-effect slot.
- `u5-decomp/formats/data-tables.md` — `SHOPPE.DAT` record layout, substitution placeholders, shared bark renderer.
- `u5-decomp/formats/data-ovl.md` — 128-entry phrase-token dictionary; the
  published contents, biases, empty-slot census, and the shop renderer's own
  spacing rule were re-derived in
  `u5-decomp/notes/talk_group_retrace_2026-08-22.md` and
  `u5-decomp/functions/SHOPPES_OVL/`
  location, byte-range bias, shop-kind trigger table, and SHOPPES2 shipwright
  dispatch correction.
- `u5-decomp/functions/TALK_OVL/`, and
  `u5-decomp/functions/ULTIMA_EXE/` -- conversation-side
  shop dispatch, current shop selector, and shared caller context.
- `u5-decomp/notes/shop_instance_binding_2026-08-22.md` -- the mounted-party
  entry gate and its literal, the scene-to-row search and its out-of-range
  behaviour, and the two resident per-kind name tables that supply the shop-name
  and vendor-name substitutions published in Section 8.0.
- `u5-decomp/formats/ds-bss-map.md`,
  `u5-decomp/functions/TOWN_OVL/`,
  `u5-decomp/functions/SHOPPES_OVL/`, and
  `u5-decomp/functions/TALK_OVL/` --
  the resident-Shadowlord selector that gates the shop surcharge.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_blackthorn-town.md`, section Q3, for
  the surcharge's Falsehood-only gate.
- Private SHOPPES horse-trader sale trace -- horse-trader sale helper and horse-object placement.
- Shipped `.NPC` roster scan and resident shop name/scene tables -- high
  dialog-index shop triggers and local shop-instance resolution.
- `u5-decomp/functions/ULTIMA_EXE/`,
  `u5-decomp/functions/MAINOUT_OVL/`, and local
  MAINOUT outer-loop analysis -- command routing and overworld pending vehicle
  placement.
- `u5-decomp/functions/CMDS_OVL/` and direct
  `SHOPPE.DAT` record inspection -- Frigate/Skiff labels, boardable ship/skiff
  families, and ship hull/skiff-count auxiliary semantics.
- `u5-decomp/notes/shoppe_random_bark_tables_2026-05-24.md` -- shared
  entry-greeting and closing-bark random-bark record ordinals by shop trigger,
  including the 2026-08-22 correction of the row labels.
- `u5-decomp/notes/shoppe_window_geometry_call_sweep_2026-05-24.md` and
  `u5-decomp/notes/shop_window_geometry_recount_2026-08-22.md` -- overlay call
  sweep and the later whole-build census of the text-window selector,
  rectangle, cursor, and colour primitives; the census supersedes the earlier
  sweep's claim that the inn register was the only shop-owned panel.
- `u5-decomp/functions/SHOPPES2_OVL/` -- shipwright
  menu, per-row Frigate/Skiff prices, per-row delivery coordinates, pending
  acquisition encoding, and the post-sale tail.
- `u5-decomp/functions/SHOPPES2_OVL/` --
  tavern/meal-counter provision branch: state-indexed provision letter, the
  Intelligence-adjusted per-unit quote, the six-record quote pool, the
  twenty-five-serving pack size, the per-unit pay loop with its gold floor and
  food ceiling, surcharge timing, and the five outcome cases including the
  table-scraps gift.
- `u5-decomp/functions/SHOPPES_OVL/` -- arms sell
  browser and its side-panel geometry.
