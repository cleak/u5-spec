# Shops

## 1. Overview

Ultima V's settled locations are populated by shopkeepers — weaponsmiths, armourers, magic-shop guildmasters, healers, herbalists, tavernkeepers, food merchants, sages, innkeepers, horse traders, and ship merchants — every one of which is, mechanically, an NPC the player Talks to. There is no dedicated shop command in the per-letter dispatcher; commerce is opened through conversation. When the player asks a commerce keyword (typically `BUY`, `SELL`, or one of a handful of class-specific tokens) the conversation engine hands control to a *shop overlay*, which runs a small kind-specific menu loop until the player exits, and then returns to the keyword input loop where the conversation resumes.

The eleven shop kinds are split across three overlay files, grouped by interaction shape rather than by trade type:

- **Stationary stock with a fixed inventory** — weaponsmith / armourer, magic-shop guildmaster, healer / sanctum, herbalist (reagent vendor). One overlay handles all four.
- **Interactive consumables** — tavern (drink), food merchant (provisions), sage (rumour by keyword). A second overlay handles the three.
- **Innkeeper** — three-mode (rest / leave a companion / pick up a companion). A third overlay handles the inn alone, because it is the only shop that maintains persistent multi-NPC state across saves.

Horse-trader and ship-broker dialogue, while included in the shop bark file, is reached through a different path: when the player walks onto and presses Enter on a vehicle that has been put on the market, the vehicle-purchase logic in the command dispatcher collects payment and assigns the vehicle to the party. The shared bark renderer is reused, but the dispatch is not through the conversation engine.

A single shared dialogue resource — `SHOPPE.DAT`, a 10-kilobyte file holding 196 token-compressed records — provides every bark, item description, room-rate quote, and farewell flourish any overlay prints. It shares a 128-entry phrase-token dictionary with the conversation engine, but its records are addressed by integer record id rather than by keyword.

This spec describes how a shop is entered from a Talk session, how the conversation engine selects which overlay handles a given shopkeeper, the on-disk layout of `SHOPPE.DAT` and the token expansion that decodes its records, the pricing model, the per-shop inventory model, the per-shop-kind interaction loops, the karma effects, and the hooks the shop overlays make back into the rest of the engine.

## 2. Triggering a shop

Conversation is the entry path. The player walks up to a shopkeeper NPC, presses `T` to Talk, and types a keyword to indicate the trade. From the shopkeeper's perspective, every shop interaction is just another keyword response; from the engine's perspective, a small set of *commerce keywords* are intercepted before the byte runner emits the keyword's response, and instead invoke the matching shop overlay.

The intercepted keywords are conventional and per-kind — most weaponsmiths know `BUY` and `SELL`, most innkeepers know `ROOM` and `REST`, most sages know `RUMOUR` or `LORE`. The keyword strings are stored in the NPC's blob and matched by free-text equality (described in `conversation.md`); the engine does not hard-code them. What it hard-codes is a *commerce flag* attached to the keyword's response in the blob — when the byte runner sees that flag, it suspends the response, calls the shop overlay corresponding to the shop-kind selector held by the engine, and on the overlay's return, finishes the response normally.

The shop-kind selector is a one-byte resident value the conversation engine sets up when the shopkeeper's blob is loaded. The byte distinguishes the eleven shop kinds and selects which overlay the commerce-flag jump lands in. Its source — whether it lives in the `.NPC` roster file, in the conversation blob, or is computed from the dialogue index — is one of the open questions in Section 12; what is certain is that by the time the keyword loop is running, the byte has been resolved.

A shopkeeper NPC carries one shop kind at a time — weaponsmith *or* tavernkeeper *or* sage, never two at once. The engine has no concept of a general store with multiple commerce types; players who want a weapon and a drink must talk to two different NPCs.

The overlay receives one piece of context: the shopkeeper's runtime NPC slot index, passed as a word argument. From this slot the overlay reads the NPC's name (for `$` substitution), the shop's display name (for `#`), and any per-NPC state. The shop-instance index used to look up per-instance inventory and pricing tables is derived from the slot index and the current scene byte.

## 3. Shop-kind dispatch

Dispatch from the conversation engine to the shop overlay goes through a small per-shop-kind table in resident memory. The eleven selector values index into this table, each entry a far pointer to one of the shop-overlay entry points:

| Selector | Shop kind     | Overlay         | Notes                                          |
|----------|---------------|-----------------|------------------------------------------------|
| 0        | weaponsmith   | shop overlay 1  | Same handler as armourer.                      |
| 1        | armourer      | shop overlay 1  | Same handler as weaponsmith.                   |
| 2        | guildmaster   | shop overlay 1  | Magic shop.                                    |
| 3        | healer        | shop overlay 1  | Treats wounds, poison, and death.              |
| 4        | herbalist     | shop overlay 1  | Sells the eight reagents.                      |
| 5        | tavernkeeper  | shop overlay 2  | Drinks; multi-step pick-quantity menu.         |
| 6        | food merchant | shop overlay 2  | Provisions; carrying-capacity gate.            |
| 7        | sage          | shop overlay 2  | Rumours; free-text keyword match.              |
| 8        | innkeeper     | shop overlay 3  | Three-mode; persistent guest registry.         |
| 9        | horse trader  | not a Talk path | Enter-vehicle handler in the command dispatcher.|
| 10       | ship broker   | not a Talk path | Enter-vehicle handler in the command dispatcher.|

The horse-trader and ship-broker rows differ in that the *vehicle*, not the trader NPC, is the dispatch trigger. A skiff or horse parked outside a stable is a purchasable in the active-object table: pressing Enter on it reads the per-vehicle price, prompts for payment, and either installs the vehicle in the party or refuses. The same shared bark renderer prints the dialogue. So the data model is unified — every shop kind speaks `SHOPPE.DAT` records — but the entry path for vehicle purchases is the dispatcher rather than the conversation engine.

The eight Talk-driven shop kinds all share the same overlay-entry calling convention: a single word argument (the shopkeeper's NPC slot index), callee-cleanup of that argument, and a 16-bit return value. The return is zero for "exit cleanly" and a non-zero diagnostic for "the shop refused service"; the keyword loop continues either way.

## 4. `SHOPPE.DAT` structure

`SHOPPE.DAT` holds the token-compressed text of every shopkeeper bark, item description, menu prompt, follow-up, room-rate quote, refusal, and farewell. The file is fixed at 10,135 bytes and contains exactly 196 records, addressed by 0-based integer record id. Records are stored back-to-back with no per-record header; a small in-resident table of record offsets maps record id to file offset.

Each record is a sequence of bytes terminated by an end-of-record sentinel (the byte `0xFF`). Within a record:

- **Bytes `0x20`–`0x7F`** are literal ASCII characters, emitted verbatim. A few are *substitution placeholders* (Section 4.1) the renderer expands inline.
- **Bytes `0x80`–`0xFE`** are phrase-token indices, each replaced by a NUL-terminated word from a 128-entry common-word dictionary (Section 4.2).
- **Byte `0xFF`** ends the record, flushing any pending word buffer.

Records are not labelled in the file; the engine's per-shop-kind tables hardcode which record-id ranges belong to which shop kind. The cluster ranges are fixed and shipped:

| Records      | Shop kind / role                                                                       |
|--------------|----------------------------------------------------------------------------------------|
| 0–7          | Shared barks: short flourish lines like "Thanks for nothing!", "Have a nice day!"      |
| 8–48         | Weapon and armour item descriptions.                                                   |
| 49–56        | Sell-back hagglers' barks (randomised "I'll give thee N gold" lines).                  |
| 57–88        | Tavern and food-merchant menus, item prompts, and barks.                               |
| 84–91        | Sage rumour records (an overlap sub-cluster).                                          |
| 92–104       | Horse-trader barks.                                                                    |
| 105–126      | Ship-broker barks.                                                                     |
| 127–146      | Reagent (herbalist) menu and barks.                                                    |
| 148–162      | Guild (magic shop) menu, item prompts, and barks.                                      |
| 163, 165–173 | Healer / sanctum menu, treatment prompts, and cure flourishes.                         |
| 174–193      | Innkeeper menu prompts, registry header, sleep tick, "Wilt thou take it?".             |

A few record-id slots are unused (a single `0xFF` byte); their presence does not affect overlay logic.

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

Eleven entries are NUL pointers — sentinels that signal "the previously emitted word needs a leading space when the next character arrives". They serve as the dictionary's word-boundary markers.

The same dictionary serves both the shop bark renderer and the conversation engine's byte runner. The two engines disagree only on the *byte range* they treat as token codes: the conversation engine reads indices `0x01`–`0x9D` (its blob text has the high bit set as obfuscation), the shop renderer reads indices `0x80`–`0xFE` (its records are plain ASCII). The two byte ranges resolve to the same physical pointer entries — conversation token `0x01` and shop token `0x80` both expand to `the`. The arithmetic differs by the bias each engine applies, but the table is a single shared block of 128 pointers.

The vocabulary is heavily slanted toward Britannian function words and common nouns — *the, thou, of, and, for, thee, dost, art, ye, hast, canst, Blackthorn, British, Shadowlords, Mantra* — and contributes heavily to the shipped game's tone, because every shopkeeper draws from the same pool.

## 5. The bark renderer

A single shared renderer takes a record id and produces formatted text. All three shop overlays call into it through a near-call into the resident image. The render pass:

1. **Look up the record offset** in the in-resident record-offset table by record id.
2. **Read bytes from the file** until the `0xFF` sentinel. The file is held open by the shop subsystem.
3. **Classify each byte**:
   - End-of-record → flush, terminate.
   - Phrase-token (`0x80`+) → look up the dictionary entry, copy the word into the output buffer.
   - Substitution placeholder → call the corresponding sub-renderer (decimal digits for `%`/`^`, copy-from-buffer for `$`/`&`/`*`/`#`, time-of-day word for `@`).
   - Plain ASCII → emit literally.
4. **Hand the output to the text-output system** for word-wrap and on-screen rendering.

The `%` substitution prints decimal digits with no thousands separator. The `@` substitution is the only one that consults the world clock; the hour byte is read fresh on every render, so a record rendered just before midnight may say "evening" while the same record rendered seconds later (after midnight) says "morning".

## 6. Pricing model

Prices are fixed per shop instance. They are *not* karma-modulated, *not* time-of-day-modulated, and *not* haggled — what the shop's table says is what the shop charges. This is a deliberate departure from Ultima IV's variable-price model.

Three pricing tables live in the resident data segment:

- **Per-shop-instance item table** (weaponsmith, armourer, guildmaster, herbalist). A 32-byte block per shop instance, indexed by shop instance id. Within each block, packed records describe each item the shop sells: tile id (which doubles as item identity), maximum quantity per visit, and a two-byte per-unit price. The 32-byte stride accommodates roughly six item records per shop, matching the shipped per-shop inventory size.
- **Per-treatment cost table** (healer). A flat table indexed by treatment kind (cure, heal, resurrect). Healer prices vary by treatment, not by who is being treated — resurrecting any party member costs the same as resurrecting any other.
- **Per-room-rate table** (innkeeper). A per-inn base byte multiplied by a per-stay-length multiplier, with rounding to the nearest gold piece. The base byte is per-inn, so the King's Ransom Inn is more expensive than the Wayfarer Inn.

Reagent prices use an eight-by-eight table (eight reagents × eight herbalist instances), indexed by the reagent letter chosen and the current shop instance — the same reagent costs different amounts at different herbalists. This is the closest U5 comes to a market, but prices are still fixed per-shop and not karma-driven.

A purchase deducts the price (or price × quantity) from the party's gold word — the shared resident counter every gold-handling system reads and writes, including the conversation engine's bribe handler and the find-treasure handler.

### 6.1 The affordability check

Every purchase is gated by an affordability check against the gold word. If the player can't pay, the shop refuses with a kind-specific bark ("Beat it!" at the tavern, "Highwaymen!" at an upmarket inn, "Thou canst afford only N" at the food merchant) and returns to the main menu without deducting. The check runs once per purchase, not once per item, so a player who picks five drinks and runs short on the fifth has no money debited and gets none of the drinks.

The food merchant has a second gate: a carrying-capacity check. Each party member can carry only so much food, and a purchase exceeding the cap is rejected before the gold check.

## 7. Inventory model

The eight Talk-driven shop kinds carry per-shop-instance inventories that vary by location. A weaponsmith in Britain stocks different weapons than one in Buccaneer's Den; the herbalist in Cove sells different reagents than the one in Yew. The variation is encoded in the per-shop-instance pricing tables — what changes is which item ids the table mentions and what their prices are.

A shop's inventory is *not* depleted by player purchases. The same weaponsmith stocks the same weapons after the player has bought them all; the engine never restocks because it never removes. Multiple visits yield the same selection.

A small per-shop-kind availability bitmap modulates which items in the master item list each shop instance carries. The bitmap holds one bit per (shop-instance × master-item-id); a set bit means the shop sells the item. Reagent vendors use a similar but simpler scheme: each herbalist's per-shop reagent-price table holds the eight prices, with sentinel bytes for "not sold here". The healer has no inventory in the shop sense; the stock is the three treatment kinds (cure, heal, resurrect), always available.

The one exception to the read-only model is the **inn registry**, which *is* per-instance per-game state and *does* survive saves (Section 8.4).

## 8. Per-shop-kind flow

Each Talk-driven shop kind follows a common shape: a randomised greeting, a Y/N or letter-driven menu, a per-action sub-loop, an "anything else?" re-prompt for shops that allow multiple sub-actions, and a randomised farewell. The kinds vary in their inner steps.

### 8.1 Weaponsmith and armourer

After a randomised greeting ("Hail, friend! Wouldst thou Buy or Sell?"), the player presses one of three keys:

- `B` (Buy) — the overlay renders the shop's "We have:" line followed by an `a..z` per-item listing, one item per letter, with each item's name and price. The player picks a letter; the overlay confirms, runs the affordability check, deducts gold, adds the item to the chosen party member's inventory, and re-prompts.
- `S` (Sell) — the overlay lists the player's current weapons and armours. For each candidate, it prints a randomised haggle bark from a four-record cluster, with the offered price computed as a fraction of the canonical buy price. The player accepts or refuses.
- *Space* (or any other input) — Exit with a randomised farewell.

Both sub-menus re-prompt after each successful action, exiting on space or when the player runs out of gold.

### 8.2 Guildmaster (magic shop)

After the greeting, the player chooses from a three-item letter menu — typically `a` Keys (skeleton keys), `b` Gems (gem-of-vision), `c` Torches. The player picks a letter and a quantity, the affordability check runs, gold is deducted, and the item is added to inventory. The guildmaster does not buy back; commerce is one-way. There is no class restriction. Spells are *not* sold here; they are mixed by the player from reagents (see `magic.md`).

### 8.3 Healer / sanctum

The healer entry runs a three-mode menu after the greeting:

- `C` (Cure) — removes the Poisoned status from a chosen party member.
- `H` (Heal) — restores the chosen party member's hit points to maximum.
- `R` (Resurrect) — restores a Dead party member at low hit points. Only available if at least one party member is Dead.

Each mode follows the same pattern: prompt for a target (presenting only members whose condition is treatable by this mode), quote the price, run affordability, deduct gold, apply the treatment, render a flourish line ("Receive now the Light!"), and re-prompt.

Healers at virtue shrines print slightly different flavour text — "Curing" versus "Receive now the Light!" — based on a scene byte the overlay inspects on entry. The mechanical effect is the same; only the bark differs.

### 8.4 Innkeeper

The inn is the most stateful shop in the system. After the randomised greeting, the player picks from three modes:

- `R` (Rest for the night) — the party sleeps in the inn's beds. The world clock advances to the next morning; HP and MP regenerate per resting rules; food is consumed at the per-night rate. The cost is per-bed × alive members (dead members do not need a bed). This is a paid version of the camp command — a guaranteed safe rest in a town.
- `L` (Leave a companion) — the player picks a party member to leave. The chosen member's full 32-byte slot record (name, gender, class, status, stats, hit points, experience, level, equipment) is copied into a free slot of the inn's persistent guest registry; the active party slot is freed. The first month's room rate is debited as the deposit.
- `P` (Pick up a companion) — the inn's registry is rendered as a guest list; the player picks a guest. The room-rate computation runs against the months elapsed since the guest was lodged, charging the full bill. The registry slot is freed and the guest's record is copied back into a free active party slot.

The inn registry is the inn's persistent state: a 16-slot table in the same resident memory used for the active-object table. Each registry slot holds one 32-byte party record plus a scene byte indicating *which* inn the guest is at. To enumerate guests at the current inn, the engine walks the 16 slots and matches each slot's scene byte against the current scene.

Because the registry is part of the save image, a player can leave a companion at an inn, save, reload weeks later, and pick up the companion — possibly with a heavy bill.

A morbid rare event applies: each in-world month, lodged guests run a small risk of dying. When the player returns to find a guest dead, "Thy friend has died, by the way" is printed on pickup; the slot still pays its accrued rate but the returned record's status byte is now Dead, requiring a resurrection.

The inn refuses service in three cases: no party members alive ("no-one to register"), already in a private bedroom scene ("one must first be left behind"), and gold below the minimum room rate ("we have no room available").

### 8.5 Tavernkeeper

The tavern entry runs a smaller menu than the arms entry. The shopkeeper greets and asks "wouldst thou like a drink?"; the player presses `Y` to enter the drink list, `N` or *space* to leave. The drink list is a six-letter menu (`a`–`f`) with each drink and per-bottle price. The player picks a letter and a quantity; total cost is bottle-price × quantity × alive-party (one drink per party member is the implicit assumption); the affordability check runs. On success, gold is deducted and "Enjoy!" is printed; on failure, "Beat it!" and the loop returns to the drink list.

Each tavern has its own drink list, picked from a per-tavern favorite-drink byte that selects the menu record — producing the tone variation between The Sword and Keg, The Slaughtered Lamb, and The Wayfarer Tavern. A drink has no mechanical effect on the party; it is flavour.

### 8.6 Food merchant

The food merchant entry mirrors the arms entry with one extra gate. `F` (Food) asks for a quantity, runs the carrying-capacity check, then the affordability check; on success, gold is deducted and food credited. `S` (Sell) asks how much food to sell, computes the sell-back price (a fraction of the buy price), credits gold, and decrements food. The food merchant has no per-item inventory — it sells one commodity at one price, varied per merchant. Food is a single integer counter in the save image, decremented by the per-day-per-party-member consumption loop in the time system.

### 8.7 Sage / rumour vendor

The sage uses free-text input rather than letter selection. After a banner ("Of what wouldst thou hear my lore?") the player types a 15-character keyword. The overlay walks the sage's 16-entry name table — a per-sage list of subjects this sage knows about — comparing the input case-insensitively. A match requires the typed string to equal the table entry up to a space-or-NUL boundary, so typing `MAGINCIA` matches "Magincia" but typing `MAG` does not.

On match, the corresponding rumour record is rendered. Rumour records typically follow the form "Seek ye & in *!" — `&` filled with the asked-about subject, `*` with the place name. The shipped sages know a fixed set of named NPCs and places drawn from the world's main quest. On no match, the sage replies "That, I cannot help thee with." and the keyword input is re-prompted. Empty input exits.

Each sage has a different name table — different sages know different things — so the player must visit several sages to gather the full rumour set.

### 8.8 Reagent vendor

The reagent entry runs an `a..h` letter menu of the eight reagents, with prices specific to the current vendor. The player picks a letter and a quantity; the affordability check runs against quantity × per-ounce price; on success, gold is deducted and the reagent count is incremented. A herbalist whose per-shop table marks a reagent as "not sold here" omits its letter — the menu has fewer than eight entries in that case.

## 9. Karma effects

The karma system does not directly modulate shop pricing or inventory. The shipped tables are flat: the same weaponsmith offers the same weapons at the same prices regardless of the Avatar's standing. This is a deliberate departure from Ultima IV, where shopkeepers cheated the dishonourable on prices and item availability.

What karma does affect, indirectly:

- **Shopkeeper recognition.** A few NPCs use the conversation engine's flag-based branching to refuse service to a heavily fallen Avatar — typically by failing to recognise the Avatar status when asked, causing the keyword loop to exit without ever reaching a commerce-flag keyword. The shop overlay is not invoked because the conversation never hands over.
- **Sage rumour quality.** A few rumours are gated by quest flags rather than by karma directly, but the gates can correlate with karma-driven story progress.
- **Healer behaviour at shrines.** The shrine variant uses different bark records, but the prices and treatment effectiveness are the same. Variation is purely flavour.

There is no "cheating the Avatar" mechanic: no shopkeeper double-prices when reputation is low, no shopkeeper short-changes on sell-backs.

## 10. Hooks to other systems

### 10.1 Conversation

Shop overlays are reached through the conversation engine's commerce-flag mechanism (Sections 2 and 3). When a shop overlay returns, the conversation engine resumes the keyword response that was interrupted, then re-prompts for the next keyword. A single shopkeeper can have multiple commerce-flagged keywords (`BUY`, `SELL`, `LIST`, `WARES`) all funnelling to the same shop overlay. The selector byte is per-NPC, not per-keyword, so all such keywords invoke the same overlay.

### 10.2 Time

Several shop interactions read or write the world clock:

- **The `@` time-of-day substitution** reads the hour byte on every record render. Greetings vary by morning / afternoon / evening.
- **The inn rest mode** advances the clock to the next morning, calling the per-turn cleanup with a multi-hour increment. The full HP/MP regen pipeline runs as it does for the camp command.
- **The inn pickup mode** computes the bill based on months elapsed since the guest was lodged, reading the saved-vs-current month delta from the world clock.

Shop overlays do not consume turns themselves; the time the player spends in a shop menu does not advance the clock. Only the inn rest mode advances time as part of its action.

### 10.3 Save / load

Two pieces of shop state are part of the save image:

- **The party gold word** is debited and credited by purchase and sell-back actions and is persisted with the rest of the resident state.
- **The inn registry** lives in the same active-object-table region of the resident data and is included in the save image. A player can leave a companion, save, reload, and pick the companion up — the registry's per-slot scene byte tells the inn-pickup logic which guest belongs to which inn.

Per-shop inventory tables, per-treatment cost tables, and `SHOPPE.DAT` itself are read-only resources baked into the resident data and the disk file. They do not change between save cycles.

### 10.4 Gold and inventory

The party's gold word is the shared resident counter every gold-handling system reads and writes — shops, conversation gold gifts, combat treasure, NPC bribes, the find-treasure handler. There is no per-character or per-shop sub-account. Gold is uncapped at the engine level except by the unsigned 16-bit range.

Each shop kind writes a slice of the inventory: weaponsmith / armourer write weapon and armour counters; guildmaster writes keys / gems / torches; healer writes the chosen member's status byte and HP/MP; herbalist writes one of the eight reagent counters; food merchant writes the food counter; innkeeper copies 32-byte party records between the active table and the inn registry; horse and ship traders write a vehicle into the active-object table via the dispatcher's vehicle-purchase logic. Tavernkeeper and sage write nothing (pure flavour). The inventory writes are fixed-offset stores into the save image's inventory region; each purchase or sale is atomic from the engine's perspective.

## 11. Open questions

- **Per-NPC shop-kind selector byte.** The eleven-slot dispatch table is verified; *where* the per-shopkeeper selector byte lives is not. Candidates include the high byte of the shopkeeper's name field, an extra byte in the per-location `.NPC` roster, or a fixed-position byte at the start of the blob.
- **Commerce-flag byte in the conversation byte runner.** Which control code (or set of codes) in the byte runner's dispatch table handles the commerce hand-off needs further reverse-engineering.
- **Per-shop inventory bitmap dimensions.** The bitmap is roughly 384 bytes (48 shops × 8 items / bit), but the indexing convention — single master shop list, or per-shop-kind sub-bitmaps — is not yet pinned down.
- **Sage record-id mapping.** Each sage's name table holds 16 entries; the parallel record-id table that maps "matched name index N" to "render record id" is not yet located.
- **Inn lodging death timer.** Lodged companions can die between leave and pickup. The tick rate and survival probability per tick are not yet measured.
- **Horse-trader and ship-broker dispatch.** The exact entry — Enter-vehicle handler, town-tile-step trigger, or hybrid — needs cross-referencing.
- **Carrying-capacity flag for food merchant.** The food-merchant carry check reads a byte whose exact bit semantics need direct measurement.
- **Sell-back price formula.** The arms shop's sell-back price is a fraction of the canonical buy price, but the exact fraction and whether it varies per item or per shop instance is not yet measured.
- **Reagent menu compaction.** When a herbalist does not sell a reagent, the menu omits its letter, but how the eight letter slots are compacted is not yet observed in live play.

## 12. Sources

The behaviour described here was derived by reading the disassembly notes and format dissections in the project's decompilation working area. None of those notes' assembly excerpts, file offsets, or implementation-specific identifiers appear in this spec; the spec is a re-derivation from observed behaviour.

- `u5-decomp/functions/SHOPPES_OVL/OVERVIEW.md` and `u5-decomp/functions/SHOPPES_OVL/0x12B2_arms_main.md` — weaponsmith / armourer, guildmaster, healer / sanctum, herbalist.
- `u5-decomp/functions/SHOPPES2_OVL/_OVERVIEW.md`, `u5-decomp/functions/SHOPPES2_OVL/0x066C_tavern_main.md`, `u5-decomp/functions/SHOPPES2_OVL/0x0508_sage_main.md`, `u5-decomp/functions/SHOPPES2_OVL/0x0000_accumulate_party_cost.md` — tavernkeeper, food merchant, sage.
- `u5-decomp/functions/SHOPPES3_OVL/_OVERVIEW.md` and `u5-decomp/functions/SHOPPES3_OVL/0x04E6_inn_main.md` — innkeeper, inn registry, persistent guest-lodging state.
- `u5-decomp/formats/data-tables.md` — `SHOPPE.DAT` record layout, substitution placeholders, shared bark renderer.
- `u5-decomp/formats/data-ovl.md` — 128-entry phrase-token dictionary location and byte-range bias.
- `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md` — conversation-side dispatch path that hands a Talk session over to a shop overlay.
