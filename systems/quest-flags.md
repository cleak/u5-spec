# Quest And Conversation Flags

## 1. Scope

Ultima V uses several different flag stores for quest and conversation state.
They should not be collapsed into one generic "quest flag" table. This spec
separates the stores that are visible from the conversation runtime:

- durable save-backed quest and item flags;
- durable shrine/Codex progress masks;
- durable NPC interaction facts, such as met/killed-style state;
- the TALK overlay's per-scene branch flag bank;
- transient one-conversation signal fields cleared during conversation exit.

The quest graph names story dependencies and rewards. This system spec defines
the flag mechanics those stories can use.

## 2. Durable Save-Backed State

The save image owns long-lived quest state. Loading a save restores these flags
in place; saving writes their current values back out without a separate
serialization pass.

Confirmed durable families include:

| Family | Owner | Role |
|---|---|---|
| Special item flags and counters | `formats/saved-gam.md` and `systems/inventory.md` | Carried story items, equipment-like use items, shard flags, and the Sandalwood Box flag. |
| Shrine/Codex masks | `formats/saved-gam.md` and `systems/karma.md` | One bit per virtue for ordained and Codex-read progress. |
| NPC interaction facts | `systems/conversation.md`, `systems/town-mode.md`, and save-backed state | Persistent named-NPC facts are semantic state written by their owning systems, such as town-side killed/cleared NPC state. Do not model the entire mixed save band before the active-object table as a dense NPC flag array. |
| Shadowlord state | `catalogs/quest-graph.md` and related systems | Current hideout town or vanquished state for each Shadowlord, plus the active-Shadowlord handshake. |
| Word-of-Power seal flags | `systems/commands.md` and `formats/saved-gam.md` | One durable flag per dungeon recording whether its Word of Power has been spoken. Region loading re-derives the sealed entrance tile from these flags, so they are world state, not presentation scratch. |
| Shrine ruin flags | `systems/karma.md` and `formats/saved-gam.md` | One durable flag per shrine recording whether that shrine currently stands ruined; region loading re-derives the ruined tile from it. |

These fields are ordinary game state, not conversation scratch. If a branch
grants an item, marks a shrine path complete, vanquishes a Shadowlord, or sets
the Sandalwood Box ownership flag, that result must survive conversation exit,
mode changes, save, and reload.

## 3. TALK Per-Scene Branch Flags

The TALK runtime also maintains a per-scene branch flag bank used by the `.TLK`
byte runner. Each town, dwelling, castle, or keep scene has one 32-bit slot.
Conversation bytecode can address a bit index inside the active scene's slot.

The public contract is:

1. The active scene id selects the slot. This is per scene, not merely per
   `.TLK` file class.
2. **The bit index is the roster slot of the NPC currently being spoken to**, in
   the range zero through thirty-one. It is supplied by the engine from the
   Talk target, never chosen by the dialogue script. One scene word therefore
   holds one bit per NPC slot in that scene.
3. The setter builds a one-bit thirty-two-bit mask from that index and ORs it
   into the active scene's slot. The tester builds the same mask and returns
   true when the bit is already set.
4. **The setter is reachable from the byte runner.** The ASK-WHO control code
   (`0x88`) calls it after the player types a line that names a live party
   member. That is the only in-stream writer, and it is the only writer traced
   anywhere.
5. The IF-ELSE control code (`0x8C`) calls the tester. Its argument byte is the
   **branch target label**, not a flag identifier: when the bit is clear the
   runner falls through in-stream, and when it is set the runner transfers to
   the labelled record named by the argument (or, for the reserved argument
   value `0xFF`, ends the response and returns to the keyword prompt).
6. **The tester has a second caller outside the byte runner.** The conversation
   opener reads the same bit before any script byte executes, to decide whether
   the addressed NPC greets the party as an acquaintance or behaves as a
   stranger; see `systems/conversation.md` section 9 step 3. The bank is
   therefore engine-visible state, not a private script variable.

Because the index is engine-supplied and bounded by the thirty-two-slot NPC
roster, it is always in range. The mask builder is a plain thirty-two-bit left
shift with no wrap or clamp, so an out-of-range index would produce a zero mask —
a setter that changes nothing and a tester that always reads clear — but no
content, shipped or custom, can reach that case through the `.TLK` byte stream.
Implementations should still floor the behaviour defensively rather than
indexing out of bounds.

Two earlier public statements about this bank are withdrawn: that the bit index
comes from the script, and that the bank has no setter opcode and is written only
by out-of-band quest-progression side effects. Both are wrong.

These flags are conversation branch memory with a specific shipped meaning:
"this NPC has been told who the party is". The idiom is an IF-ELSE with the
reserved `0xFF` argument placed immediately before an ASK-WHO in an NPC's Name or
Greeting entry, so the introduction happens once and is skipped thereafter. They
let an NPC avoid repeating a line, remember that a local answer was given, or
gate an immediate follow-up inside the active scene's conversation set. Do not
model them as global quest completion flags unless a separate durable writer is
also traced.

**Lifetime.** "Per-scene" describes the bank's *indexing*, not its durability.
The whole thirty-two-slot bank lives inside the flat save image and is written
and restored with everything else in it; the factory seed has all slots zero, and
no traced path clears a slot on scene exit, mode change, save, or reload. A bit,
once set, stays set for the rest of that savegame. This matters beyond
line-skipping: shipped dialogue also uses the bank to make a reward
non-repeatable, with two IF-ELSE tests around one ASK-WHO selecting between a
plain record and a near-duplicate bonus record (`systems/conversation.md`, "The
introduce-yourself idiom", and `systems/karma.md` section 4). An implementation
that treats the bank as per-visit scratch turns every such reward into a farm.
`formats/saved-gam.md` gives the band the bank occupies.

## 4. Generic Conversation Action Flags

The `0x86` action-dispatch control code has two broad families.

Small numeric arguments write into a generic transient conversation flag array.
The write uses a nonzero marker value rather than a Boolean bit. These generic
flags are scanned by the final conversation cleanup and are candidates for
one-shot reconciliation against the theft/covert-action pipeline.

Letter arguments use a fixed global action table. The table can write resource
or special-item fields, redraw the gold panel, or stamp fixed marker bytes.
The table is global: the effect comes from the letter embedded in the script,
not from the identity of the NPC currently speaking. Public item/catalog specs
should name only the letter effects whose semantic item or resource identity has
been confirmed.

The confirmed public letter effects are:

| Letter | Effect family |
|--------|---------------|
| `A` | Food counter raised to the capped grant value. |
| `B` | Gold counter raised to the capped grant value. |
| `C` | Ordinary key counter raised to the capped grant value. |
| `D` | Gem counter raised to the capped grant value. |
| `E` | Torch counter raised to the capped grant value. |
| `F` | Outdoor Klimb gear/Grapple gate set. |
| `G` | Magic-carpet carried counter raised to the capped grant value. |
| `H` | Sextant carried-item flag set. |
| `I` | Spyglass carried-item flag set. |
| `J` | Black Badge carried-item flag set. |
| `K` | Skull/special-key counter raised to the capped grant value. |

## 5. Conversation Exit: The Falsehood Theft

Every normal conversation calls a final cleanup pass after the keyword loop and
Bye text finish. The pass is not quest-state reconciliation at all: it is the
Shadowlord of Falsehood's theft, and it is gated on which Shadowlord, if any,
is resident in the settlement the party is in — the value town entry records on
arrival (`systems/town-mode.md` Section 13).

- If the recorded value is anything but the Shadowlord of Falsehood — the
  Hatred value, the Cowardice value, or the no-host marker that every ordinary
  settlement carries — the cleanup returns immediately. Nothing is printed and
  nothing is taken.
- If the Shadowlord of Falsehood is resident, the cleanup prints the
  stolen-goods line, plays a fixed descending PC-speaker glissando, and removes
  exactly one carried thing from the party.

**Retraction.** Earlier revisions of this section described the pass as
"reconciling one pending transient conversation signal" out of a three-slot
special band, a generic signal array, and two eight-slot signal arrays. That
reading is withdrawn. The bands it walks are ordinary inventory: the three-slot
band is the party's keys, gems, and torches; the "generic array" is the
forty-eight-entry carried-equipment band described in `systems/inventory.md`;
and the two eight-slot arrays are two further carried-item bands. The pass
subtracts one unit of a carried item; it does not consume conversation signals,
and no conversation-signal band is published from it.

The theft order is fixed:

1. If the party carries any keys, gems, or torches, the shared random stream
   picks among those three counters, re-drawing until it lands on one the party
   actually has, and subtracts one with a zero floor.
2. Otherwise the forty-eight-entry carried-equipment band is scanned from the
   highest item id downward and the first nonzero entry is reduced by one.
3. Otherwise the two eight-entry carried-item bands are scanned the same way,
   highest index first, and the first nonzero entry is reduced by one.
4. Only when no carried item was found does the cleanup subtract a random
   `1..15` gold from the party's gold total, floored at zero.

The pass then redraws the visible stats/gold panel. At most one item, or one
gold amount, is lost per conversation.

The same resident-Shadowlord value gates the shop surcharge, where any value
other than Falsehood likewise suppresses the extra post-transaction gold debit.
Any non-empty value — not just Falsehood — also gates the farmland and orchard
blight applied to the hosting town's floor buffer (`systems/town-mode.md`
Section 3) and the town-wide NPC state sweep selected by which Shadowlord is
hosted (`systems/town-mode.md` Section 13).
It is per-visit mode state, not a durable quest flag; keep the surcharge
behaviour in `systems/shops.md` and the presentation in
`systems/conversation.md`.

Source provenance: derived from private analysis note
`u5-decomp/notes/oq-closures_2026-08-22_blackthorn-town.md`, section Q3.

## 6. Relationship To TLK Branches

The `.TLK` format records control bytes and their argument widths. It does not
own the flag stores. Runtime handling belongs here and in
`systems/conversation.md`:

- `0x8C` tests the active scene's per-scene 32-bit branch slot at the speaking
  NPC's roster-slot bit, and uses its argument byte as the branch target label.
- `0x88` (ASK-WHO) sets that same bit, for that same NPC, on a successful name
  match. It is the bank's only setter.
- `0xFE` is a separate karma-threshold branch; it compares the shared
  moral-standing selector to a threshold and jumps to a label when the
  comparison succeeds. `systems/karma.md` owns that selector.
- `0x86` is an action dispatch. Some actions write transient generic flags;
  others write durable game state through fixed resource/item paths.

Keeping these separated avoids a common compatibility bug: treating every TLK
branch argument as a save-backed quest bit.

## 7. Compatibility Rules

- Preserve the distinction between per-scene TALK branch flags and save-backed
  NPC interaction facts.
- Preserve the distinction between transient one-conversation signal arrays and
  durable item, shrine, NPC, and Shadowlord state.
- Model the per-scene TALK flag bank as 32-bit slots indexed by NPC roster slot.
  The index is engine-supplied and cannot exceed thirty-one through normal
  content; if an implementation can produce an out-of-range index anyway, make
  it build a zero mask so setters become no-ops and tests read as clear.
- Keep ASK-WHO wired to the setter. Removing it leaves a bank that is tested but
  never set, which silently breaks every "have we met" branch in the shipped
  dialogue.
- Run the end-of-conversation cleanup even when the player exits with an empty
  input/BYE path, because side effects may have occurred before exit.
- Preserve the cleanup pass's shared-sentinel early return. Do not force
  one-shot signal decrementing or gold redraw when the sentinel suppresses this
  cleanup.

## 8. Boundaries And Owned Work

No quest-flag-specific open work is currently known at this layer. Remaining
save-format exactness for unnamed bytes in the mixed world/quest/mode band
belongs to `formats/saved-gam.md`; remaining named-NPC lifecycle details belong
to `systems/town-mode.md`, `systems/npc-schedules.md`, and
`systems/conversation.md`.

## 9. Sources

This is a cleanroom behavioral rewrite from the private TALK overlay notes. It
does not reproduce private source, decompiler output, assembly excerpts, raw
dumps, private address tables, or implementation listings.

- Per-scene branch flag setter: `u5-decomp/functions/TALK_OVL/0x0D42_set_npc_quest_flag.md`.
- The in-stream setter's call site, the engine-supplied bit index, and the
  corrected IF-ELSE argument role:
  `u5-decomp/notes/talk_group_retrace_2026-08-22.md` and
  `u5-decomp/functions/TALK_OVL/0x0E78_ask_who_join_loop.md`.
- Per-scene branch flag tester: `u5-decomp/functions/TALK_OVL/0x0D7A_test_npc_quest_flag.md`.
- Branch-mask shift helper identity:
  `u5-decomp/functions/ULTIMA_EXE/_LIBRARY_FIDB.md`.
- Action-dispatch transient and fixed action paths: `u5-decomp/functions/TALK_OVL/0x0682_action_command_dispatch.md`.
- Special-item action-letter identities: `u5-decomp/functions/ZSTATS_OVL/0x099A_snapshot_inventory_to_overlay_ds.md`,
  `u5-decomp/functions/ZSTATS_OVL/0x0A3A_zstats_main.md`, and shipped `.TLK`
  action usage.
- Multi-byte branch/action dispatch context: `u5-decomp/functions/TALK_OVL/0x0DBE_multi_byte_command_handler.md`.
- Final conversation cleanup: `u5-decomp/functions/TALK_OVL/0x1180_final_conversation_cleanup.md`.
- Shared town-entry sentinel producer:
  `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`,
  `u5-decomp/functions/TOWN_OVL/0x02AE_town_attach_player_slot.md`, and
  `u5-decomp/formats/data-ovl.md`.
- Warning sound presentation:
  `u5-decomp/functions/ULTIMA_EXE/0x43AE_pc_speaker_glissando.md`.
- Public save-backed state cross-checks: `formats/saved-gam.md`, `systems/karma.md`, `systems/inventory.md`, and `catalogs/quest-graph.md`.
