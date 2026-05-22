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
- **Innkeeper** — three-mode (rest / leave a companion / pick up a companion). A third overlay handles the inn alone, because it is the only shop that maintains persistent multi-NPC state across saves.

Horse-trader dialogue and purchase barks, while included in the shop bark file,
are reached through a Talk shop arm. The purchase flow is vehicle-oriented: it
quotes a local horse price, asks for confirmation, checks gold, debits on
success, and writes a horse active-object record at the sale location. This is
not B-Board; B-Board only boards an already-present boardable object.
Ship-broker dialogue records are reached through their own Talk shop arm; a
paid sale queues a pending vehicle acquisition that the next overworld entry
turns into a placed watercraft active object.

A single shared dialogue resource — `SHOPPE.DAT`, a 10-kilobyte file holding 196 token-compressed records — provides every bark, item description, room-rate quote, and farewell flourish any overlay prints. It shares a 128-entry phrase-token dictionary with the conversation engine, but its records are addressed by integer record id rather than by keyword.

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

Shop entry includes a transport gate. If the party is already mounted on a
horse, ordinary shop arms refuse before opening their menu; the horse-trader
vehicle-sale arm remains available.

Every Talk shop arm receives the same one-word caller context. Decoded
member-sensitive price paths use it as the speaking party member's roster slot;
other shop kinds receive the word even when their own flow does not need it. The
shopkeeper's name (for `$` substitution), the shop's display name (for `#`), and
the current shop-instance selectors are already resident work state by the time
the overlay renders text or lists stock.

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
vehicle active-object slot at the stored sale coordinates. Frigate purchases
place a ship-family active object with a standard full-hull auxiliary value and
the queued skiff count; standalone Skiff purchases place a skiff-family active
object. The pending state is then cleared.

The stock horse-trader base prices are:

| Stable | Horse base price |
|---|---:|
| Horse & Rider | 100 |
| The Stablehouse | 130 |
| Wishing Well Horses | 160 |

The confirmed Talk-driven shop arms all receive the caller's Talk context and
the resident shop buffers prepared before dispatch. On return, the Talk action
is complete regardless of whether the shop completed a purchase, refused
service, or exited without acting.

## 4. `SHOPPE.DAT` structure

`SHOPPE.DAT` holds the token-compressed text of every shopkeeper bark, item description, menu prompt, follow-up, room-rate quote, refusal, and farewell. The file is fixed at 10,135 bytes and contains exactly 196 NUL-terminated record slots, addressed by 0-based integer record id. Records are stored back-to-back with no per-record header or in-file offset table; the consumer supplies a record id and resolves it to the corresponding sequential record.

Each record is a sequence of bytes terminated by a NUL byte. Within a record:

- **Low-ASCII bytes other than NUL** are emitted literally, except for substitution placeholders (Section 4.1) that the renderer expands inline.
- **Bytes `0x80`–`0xFF`** are phrase-token indices, each replaced by a NUL-terminated word from a 128-entry common-word dictionary (Section 4.2). `0xFF` is a valid token byte, not a record terminator.
- **Byte `0x00`** ends the record.

Records are not labelled in the file; the engine's per-shop-kind tables hardcode which record-id ranges belong to which shop kind. The cluster ranges are fixed and shipped:

| Records      | Shop kind / role                                                                       |
|--------------|----------------------------------------------------------------------------------------|
| 0–7          | Shared barks: short flourish lines like "Thanks for nothing!", "Have a nice day!"      |
| 8–48         | Weapon and armour item descriptions.                                                   |
| 49–56        | Arms `S`-menu sell-back haggle and confirmation barks.                                 |
| 57–88        | Tavern, meal-counter, and related interactive menus, prompts, and barks.               |
| 84–91        | Sage rumour records (an overlap sub-cluster).                                          |
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

The substitution buffers are populated by the shop overlay before any records are rendered. Shopkeeper-name and shop-name come from the per-shopkeeper NPC data and the per-scene shop-name table; gold-amount, quantity, and item-name are filled mid-loop as the player picks items; the time-of-day byte is read fresh from the world clock on every render.

A literal `&`, `%`, `*`, `$`, `#`, or `@` cannot be emitted as itself — none of the shipped record text uses these as literal punctuation, so the renderer always expands.

### 4.2 The phrase-token dictionary

The 128 phrase tokens (`0x80`–`0xFF`) index a 128-entry pointer table held in the resident data segment. Each entry is a 16-bit data-segment-relative pointer to a NUL-terminated word in a common-word vocabulary. When the renderer encounters a token byte, it reads the pointer at index `(token - 0x80)` and inlines the word.

Eleven entries are NUL pointers used by the text consumers as word-boundary sentinels. These are dictionary entries, not `SHOPPE.DAT` record terminators.

The same dictionary serves both the shop bark renderer and the conversation engine's byte runner. The two engines disagree only on the *byte range* they treat as token codes: the conversation engine reads low control-byte indices in its blob text, while the shop renderer reads high-byte tokens in `SHOPPE.DAT`. The two byte ranges resolve to the same physical pointer entries — conversation token `0x01` and shop token `0x80` both expand to `the`. The arithmetic differs by the bias each engine applies, but the table is a single shared block of 128 pointers.

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
not haggled. The arms equipment paths and inn room-rate paths are the notable
stat-sensitive cases: the speaking party member's Intelligence changes the
quoted equipment or room price. Other decoded shop headline prices are fixed
by the relevant shop, commodity, or treatment table.

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
  the room quote and affordability checks. Rest quotes multiply the base rate
  by the travelling party size, then apply the speaking member's Intelligence
  adjustment. Leave deposits use an Intelligence-adjusted local lodging charge
  derived from ten room-rate units. Pickup bills use that same adjusted lodging
  charge times the selected guest's stored stay counter, with a stored zero
  billed as one unit. The time system increments that stored counter on each
  28-day month rollover, capped at 25.

Horse-trader and shipwright purchases also use fixed local base-price rows
before the ordinary quote, confirmation, affordability, and payment flow. The
tables below list the base headline values before any stat-sensitive quote
adjustment and before the random post-transaction surcharge.

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

The stock tavern/meal-counter provision base prices are:

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
handler. Most successful paid purchases then run the post-transaction surcharge
described below. Arms sell-back runs in the other direction: it increases the
gold word, capped by the normal gold limit, and decrements the sold equipment
counter.

### 6.1 The affordability check

Most purchases are gated by an affordability check against the gold word. If
the player can't pay, the shop refuses with a kind-specific bark ("Beat it!" at
the tavern, "Highwaymen!" at an upmarket inn, "Thou canst afford only N" at a
vehicle broker) and returns to the main menu without deducting.

The tavern/meal-counter provision branch is the exception: it processes a
requested quantity one unit at a time. Each affordable unit debits gold and
adds to the shared food counter before the next unit is checked. If the party
runs out of gold partway through the requested quantity, the already-served
units remain purchased and the shop reports the smaller affordable quantity.
Compatible implementations must not roll this branch back as an all-or-nothing
purchase.

The shipwright sale flow has a second gate before the ordinary gold check. It
tests the outdoor pending-action / vehicle-acquisition queue, which is consumed
by the overworld entry pass before the next outdoor turn begins. A successful
Frigate purchase records the ship-family acquisition class plus an initial
skiff-count payload; a successful standalone Skiff purchase records the
skiff-family acquisition class. The outdoor consumer allocates a free
active-object slot at the pending coordinates, chooses ship versus skiff from
the acquisition class, initializes the ship-family hull auxiliary value where
applicable, copies the skiff-count payload for a frigate, and clears the pending
state. The owner is the outdoor pending-action handshake, not a standalone
commodity-stock field.

### 6.2 Post-transaction surcharge

After a successful paid shop transaction, the shop family can charge an extra
random surcharge of `1..64` gold. This surcharge is independent of the quoted
headline price: the player sees and confirms the table/stat-derived price, the
ordinary affordability gate and main debit run, then the extra charge is
subtracted from the same party gold word.

The surcharge helper first checks a shared town/conversation sentinel produced
by town active-slot setup and also read by conversation cleanup. Town setup uses
the byte as a no-slot marker or as one of three tracked town/Shadowlord slot
indices, but the shop reader applies only a zero-versus-nonzero gate: the extra
charge runs only for slot value `0`; slot values `1` and `2` and the no-slot
marker suppress it. The current writer audit found no non-town writer for this
shared byte in the analyzed baseline. This is not a shop-local transaction flag, and
compatibility code should not model it as karma, shop kind, or healer identity.
The Minoc no-price Cure/Heal branch remains separate: it bypasses the ordinary
paid branch before the surcharge point.

Known traced surcharge callers include:

| Shop family | Surcharge reach |
|-------------|-----------------|
| Arms buy / horse-trader paid branch | After successful purchase |
| Healer paid branch | After the headline treatment charge |
| Tavern, sage, and shipwright paid branches | After successful payment |
| Innkeeper room/guest charges | After successful payment |

Because the surcharge is applied after the ordinary affordability check, a
player with exactly enough gold for the quoted price can still lose additional
gold afterward, floored by the shared word-subtract helper. This is a gold-side
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

Each Talk-driven shop kind follows a common shape: a randomised greeting, a Y/N or letter-driven menu, a per-action sub-loop, an "anything else?" re-prompt for shops that allow multiple sub-actions, and a randomised farewell. The kinds vary in their inner steps.

### 8.0 Scene-byte to shop-instance row mapping

Every Talk-triggered shop kind resolves its per-location row through the active scene byte (`SAVED.GAM 0x02ED`) by indexing a per-kind scene-byte lookup table in the resident shop-data region. The eight per-kind tables, in their full byte-traced form, are:

**Arms shops** (9 rows):

| Scene | Location | Row |
|---:|---|---|
| `2` | Britain | `Iolo's Bows` |
| `3` | Jhelom | `Naughty Nomaan's` |
| `4` | Yew | `Arms of Justice` |
| `5` | Minoc | `Darkwatch Armoury` |
| `6` | Trinsic | `The Paladin's Protectorate!` |
| `17` | Lord British's Castle | `North Star Armoury` |
| `24` | Buccaneer's Den | `Buccaneers Booty` |
| `26` | Bordermarch | `The Shattered Shield` |
| `32` | Serpent's Hold | `Siege Crafters` |

**Taverns / meal counters** (9 rows):

| Scene | Location | Row |
|---:|---|---|
| `1` | Moonglow | `The Honest Meal` |
| `2` | Britain | `The Wayfarer Tavern` |
| `3` | Jhelom | `The Sword and Keg` |
| `4` | Yew | `The Slaughtered Lamb` |
| `8` | New Magincia | `The Humble Palate` |
| `19` | West Britanny | `The Blue Boar Tavern` |
| `22` | Paws | `The Cat's Lair` |
| `24` | Buccaneer's Den | `The Fallen Virgin` |
| `30` | The Lycaeum | `The Folley Tap` |

**Horse traders** (3 rows):

| Scene | Location | Row |
|---:|---|---|
| `6` | Trinsic | `Horse & Rider` |
| `20` | North Britanny | `The Stablehouse` |
| `22` | Paws | `Wishing Well Horses` |

**Shipwrights** (4 rows):

| Scene | Location | Row |
|---:|---|---|
| `3` | Jhelom | `Island Shipwrights` |
| `5` | Minoc | `The Crow's Nest` |
| `21` | East Britanny | `The Oaken Oar` |
| `24` | Buccaneer's Den | `The Rusty Bucket` |

**Reagent vendors** (5 rows):

| Scene | Location | Row |
|---:|---|---|
| `1` | Moonglow | `The Herbalist` |
| `4` | Yew | `Healers Herbs` |
| `7` | Skara Brae | `The Alchemist` |
| `23` | Cove | `Mysticism` |
| `30` | The Lycaeum | `The Sharper Mage` |

**Guildmasters** (3 rows):

| Scene | Location | Row |
|---:|---|---|
| `8` | New Magincia | `The Den` |
| `22` | Paws | `The Guild` |
| `24` | Buccaneer's Den | `The Nemesis` |

**Healers / sanctums** (7 rows):

| Scene | Location | Row |
|---:|---|---|
| `5` | Minoc | `The Healers Mission` |
| `6` | Trinsic | `Wounds of Honour` |
| `7` | Skara Brae | `The Spirit Healers` |
| `21` | East Britanny | `Healers' Sanctum` |
| `23` | Cove | `Sanctuary` |
| `30` | The Lycaeum | `The Shield of Truth` |
| `31` | Empath Abbey | `The Empath` |

**Inns** (6 rows):

| Scene | Location | Row |
|---:|---|---|
| `2` | Britain | `The Wayfarer Inn` |
| `3` | Jhelom | `The Warrior's Stead` |
| `7` | Skara Brae | `The Haunting Inn` |
| `20` | North Britanny | `Hotel Brittany` |
| `22` | Paws | `The Smugglers' Inn` |
| `24` | Buccaneer's Den | `The King's Ransom Inn` |

Each scene-byte appears in exactly one shop kind's table — there is no scene that hosts two shops of the same kind. When the Talk shop trigger fires for a kind whose table does not include the active scene, the shop overlay falls through to the standard "no shop here" feedback rather than defaulting to row zero.

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
- *Space* (or any other input) — Exit with a randomised farewell.

Both sub-menus re-prompt after each completed action. The buy side refuses
capped counters and insufficient gold without changing inventory. The sell
side refuses empty, unsellable, or explicitly excluded equipment without
changing inventory. Either side can exit when the player walks away.

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
as dead. An untreatable selection prints the shared healer refusal and
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

The main menu accepts three actions:

- `R` (Rest for the night) — the party sleeps in the inn's beds. The world clock
  advances through the inn/rest pipeline and sleeping status is cleared. The
  town-bed path does not contain its own HP/MP recovery block; any HP change
  during the stay comes from time-driven effects such as the hourly Ring of
  Regeneration check, poison, or starvation. Food is consumed at the per-night
  rate. The quote is based on the inn's adjusted room
  rate and the travelling party size. This is a paid, safe town rest rather than
  a wilderness ambush-risk camp.
- `L` (Leave a companion) — the player picks a party member to leave. The chosen member's 32-byte slot record (name, gender, class, status, stats, hit points, experience, level, equipment) is moved into the inn registry view, that guest slot's leading marker is set to the current inn scene, the stored stay counter is cleared to zero, the active roster is compacted, and the party-size byte is decremented. A quoted deposit based on ten local room-rate units is debited before the transfer completes.
- `P` (Pick up a companion) — the inn's registry is rendered as a guest list when more than one guest at this inn can be chosen. The pickup bill uses the adjusted local lodging charge times the selected guest's stored stay counter, treating zero as one billable unit. The guest's record is copied into the next active roster slot, the party-size byte is incremented, the registry view is compacted as needed, and the returned slot's former guest marker is cleared to zero.

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

The drink menu is state-driven. One state-specific letter buys a round for each
living party member using the stock per-person table in Section 6. The Blue
Boar Tavern's `W` branch instead opens a six-choice fixed-price drink list. A
paid drink branch deducts gold and prints the tavern success line; the drink
itself has no traced persistent effect on party state. Failed payment returns
to the menu without changing gold.

One tavern/meal-counter menu branch sells provisions rather than flavour
drinks. It quotes a per-unit food price, asks for a quantity, and processes the
requested units sequentially. For every affordable unit, the party gold counter
is debited and the shared food/provisions counter is adjusted under the normal
food floor and cap. If gold runs out before the requested quantity is complete,
the already-afforded units remain purchased and the shop reports the quantity
the party could afford. A zero quantity or "no need" case takes the refusal
text path instead of changing gold or food.

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

The stock shipwright base prices are:

| Shipwright | Frigate | Skiff |
|---|---:|---:|
| Island Shipwrights | 600 | 200 |
| The Crow's Nest | 753 | 175 |
| The Oaken Oar | 650 | 125 |
| The Rusty Bucket | 700 | 100 |

Unlike ordinary inventory shops, a successful shipwright purchase does not write
a simple carried-item counter. It writes a shared pending vehicle-acquisition
state used by the outdoor loop. The next overworld entry consumes that state,
places a watercraft active object at the stored sale coordinates, initializes
its purchased-vehicle auxiliary state, and clears the pending queue.

The two purchase classes use different pending payloads:

- **Frigate.** Queues a ship-family active object with a full-hull starting
  condition and an initial cargo of two skiffs. If a Skiff is bought while that
  frigate is still pending delivery, the queued frigate's skiff count is
  incremented rather than placing a second object.
- **Skiff.** Queues a standalone skiff-family active object when no frigate is
  pending.

Duplicate purchases before the queued delivery is consumed are handled inside
the shipwright menu:

- Selecting **Frigate** while any shipwright delivery is already pending shows a
  limited-dock-space / special-delivery quote and asks for confirmation. A Yes
  answer runs only the affordability/refusal gate for that quote; it does not
  debit gold, queue a second Frigate, or alter the pending watercraft.
- Selecting **Skiff** while a Frigate is pending treats the Skiff as ship cargo:
  after the ordinary confirmation and affordability check, gold is debited, no
  second active object is queued, and the pending Frigate's skiff count is
  incremented.
- Selecting **Skiff** while a standalone Skiff is pending refuses the extra
  Skiff purchase and leaves the pending state and gold unchanged.

Exact numeric marker values, ship facing, and sail-state encodings remain with
the vehicle marker table rather than the shop flow.

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
When a topic matches, the sage quotes the fee and asks for confirmation. If the
party cannot pay, the sage refuses with a paying-customers bark and no rumour
is given. If the player confirms and has enough gold, the fee is deducted, the
topic's subject fills the `&` substitution, the selected destination fills the
`*` substitution, and one of the four shared success templates is selected at
random from SHOPPE.DAT records 85-88.

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

### 8.10 Stationary display purchase

One Talk-entered SHOPPES helper is a stationary-display purchase flow rather
than a Buy/Sell menu. It is used when the item being sold is represented by a
nearby map display object, such as a stock item placed on a counter or floor.

On entry, the flow scans the active-object table for a sale marker adjacent to
the player. Candidate markers are resolved through the same map-tile reader used
by other town interactions, and the NPC/occupancy classifier rejects candidates
that are not usable shop displays. The first accepted display marker selects
the current shop instance and therefore the base unit price and rendered item
description.

The purchase loop is Y/N driven:

- Space or `N` exits without a purchase and returns through the shop farewell
  path.
- `Y` prints the item offer, asks for confirmation, and aborts cleanly on a
  negative answer.
- If the confirmed price exceeds party gold, the shop prints its insufficient
  funds line and exits without changing the displayed item or party inventory.
- On success, the price is deducted, the normal post-transaction surcharge
  helper may run, and the purchased display item is written into the speaking
  party member's carried-item state. The local view is then redrawn to reflect
  the taken item.

This flow is distinct from arms/guild/reagent stock. It does not browse a
lettered stock table and it does not deplete a shop inventory row; the visible
nearby display object is the sale target.

## 9. Karma effects

The karma system does not directly modulate shop headline pricing or inventory.
Arms purchases and inn room quotes can vary with the speaking party member's
Intelligence, but not with virtue standing. Reagent, treatment, guild, and
other decoded headline prices come from their resident tables rather than from
karma. The random post-transaction surcharge is also not a karma price
modifier; it is gated by shared town/conversation state rather than by virtue
standing. This is a deliberate departure from Ultima IV, where shopkeepers
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
  stay completes. It uses the same status-cleanup semantics as town H-Hole-up,
  but without the wilderness ambush risk or the completed long-camp recovery
  block.
- **The inn pickup mode** computes the bill from the inn's local lodging charge
  and the selected guest's stored stay counter. A zero counter is billed as one
  unit. The time system increments the counter on each 28-day month rollover,
  capped at 25.

Shop overlays do not consume turns themselves; the time the player spends in a shop menu does not advance the clock. Only the inn rest mode advances time as part of its action.

### 10.3 Save / load

Two pieces of shop state are part of the save image:

- **The party gold word** is debited by shop purchases and services and is
  persisted with the rest of the resident state.
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
object; stationary-display purchases write the displayed item into the speaking
member's carried-item state.
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
sage topics, stationary-display purchases, horse-trader sale, shipwright
pending delivery, inn rest and guest registry behavior, shop surcharge,
persistence, and karma non-modulation are fixed.

- Remaining equipment class restrictions and armour defence values are tracked
  by `catalogs/item-list.md` and `formats/data-ovl.md`.

## 12. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x019A_charge_random_tax.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x04A2_guild_main.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x075E_reagent_main.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x07BE_find_shopkeeper.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x0B30_arms_buy_menu.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x0F64_arms_sell_inventory.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x14F8_healer_main.md`,
  `u5-decomp/functions/SHOPPES_OVL/0x12B2_arms_main.md`, and the private
  SHOPPES healer-main trace — weaponsmith / armourer, guildmaster, healer /
  sanctum, herbalist, stationary-display purchase, and post-transaction
  surcharge behavior.
- `u5-decomp/functions/SHOPPES2_OVL/_OVERVIEW.md`,
  `u5-decomp/functions/SHOPPES2_OVL/0x066C_tavern_main.md`,
  `u5-decomp/functions/SHOPPES2_OVL/0x0508_sage_main.md`,
  `u5-decomp/functions/SHOPPES2_OVL/0x0450_food_pay_and_serve.md`,
  `u5-decomp/functions/SHOPPES2_OVL/0x0000_accumulate_party_cost.md`, and
  local SHOPPES2 shipwright control-flow analysis — tavernkeeper, ship broker,
  sage, and the correction that the traced `F`/`S` pending-action flow belongs
  to shipwright sales rather than a provisions merchant.
- `u5-decomp/functions/SHOPPES3_OVL/_OVERVIEW.md` and `u5-decomp/functions/SHOPPES3_OVL/0x04E6_inn_main.md` — innkeeper, inn registry, persistent guest-lodging state.
- `u5-decomp/formats/data-tables.md` — `SHOPPE.DAT` record layout, substitution placeholders, shared bark renderer.
- `u5-decomp/formats/data-ovl.md` — 128-entry phrase-token dictionary
  location, byte-range bias, shop-kind trigger table, and SHOPPES2 shipwright
  dispatch correction.
- `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md` and
  `u5-decomp/functions/ULTIMA_EXE/0x75CC_overlay_loader.md` -- conversation-side
  shop dispatch, current shop selector, and shared caller context.
- `u5-decomp/formats/ds-bss-map.md`,
  `u5-decomp/functions/TOWN_OVL/0x02AE_town_attach_player_slot.md`, and
  `u5-decomp/functions/TALK_OVL/0x1180_final_conversation_cleanup.md` --
  shared town/conversation sentinel context for the shop surcharge gate.
- Private SHOPPES horse-trader sale trace -- horse-trader sale helper and horse-object placement.
- Shipped `.NPC` roster scan and resident shop name/scene tables -- high
  dialog-index shop triggers and local shop-instance resolution.
- `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`,
  `u5-decomp/functions/MAINOUT_OVL/0x0A84_mainout_main_loop.md`, and local
  MAINOUT outer-loop analysis -- command routing and overworld pending vehicle
  placement.
- `u5-decomp/functions/CMDS_OVL/0x07F6_cmds_board.md` and direct
  `SHOPPE.DAT` record inspection -- Frigate/Skiff labels, boardable ship/skiff
  families, and ship hull/skiff-count auxiliary semantics.
