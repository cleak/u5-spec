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
| Shadowlord state | `catalogs/quest-graph.md` and related systems | Current hideout or vanquished state for each Shadowlord. |

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
2. A flag setter builds a one-bit 32-bit mask from the script-provided bit
   index and ORs it into the active scene's slot.
3. A flag tester builds the same mask and returns true when any matching bit is
   already set in the active scene's slot.
4. The `0x8C` IF/ELSE control code uses this tester for its one-byte flag
   argument. In the existing conversation spec, a set bit selects the branch
   described as the alternate/else arm; a clear bit falls through to the
   normal/then arm.

The mask builder is a plain 32-bit left shift of a one-bit value. It does not
wrap or clamp the bit index. Indices `0..31` address the expected bit
positions; indices `32` and above produce a zero mask. A setter with such an
out-of-range index therefore changes nothing, and a tester with such an index
always reports "not set" for the active scene.

These flags are conversation branch memory. They let an NPC avoid repeating a
line, remember that a local answer was given, or gate an immediate follow-up
inside the active scene's conversation set. Do not model them as global quest
completion flags unless a separate durable writer is also traced.

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

## 5. Conversation Exit Reconciliation

Every normal conversation calls a final cleanup pass after the keyword loop and
Bye text finish. The pass first checks the shared town/conversation sentinel:

- if the sentinel is nonzero, the cleanup returns immediately. No theft message,
  one-shot signal reconciliation, or gold redraw is performed from this pass;
- if the sentinel is zero, the cleanup prints the stolen-action warning, runs
  the fixed stolen-action warning sound, and then reconciles one pending field.

The sentinel is produced by town-entry active-slot setup, not by the
conversation cleanup itself. Town setup initializes it to a no-slot marker, then
may replace it with one of the three tracked town/Shadowlord slot indices when
the active scene matches the three-slot Shadowlord-location table. Town setup
treats the no-slot marker as special; the conversation cleanup does not. For
cleanup, only the byte value matters: slot index `0` is the traced
town-produced state that allows the warning/reconciliation pass, while slot
indices `1` and `2` and the no-slot marker suppress it. The current writer
audit found no non-town writer for this shared byte in the analyzed baseline.

The warning sound is a fixed descending PC-speaker glissando played immediately
after the warning text. It is presentation only; the state reconciliation below
is what mutates resources and transient signal fields.

The zero-sentinel reconciliation order is fixed. It first checks a three-slot
resource/special band. The band uses the shared random stream after a
time-derived reseed: while any of the three slots is nonzero, it chooses one of
the three slots until it lands on a nonzero entry, then subtracts one from that
slot with a zero floor. If the band has no nonzero slot, the pass scans the
generic conversation signal array from high index to low index and subtracts one
from the first nonzero entry, again floored at zero. If none exists, it scans
the two eight-slot conversation signal arrays, also high to low, and subtracts
one from the first nonzero entry. Only when no byte-sized signal was decremented
does the cleanup subtract a random `1..15` gold from the party's gold total,
floored at zero, and redraw the visible stats/gold panel.

This makes the ownership boundary explicit: transient conversation signals do
not themselves persist as durable quest state after the cleanup has processed
them, but at most one byte-sized signal is consumed per cleanup call. The same
sentinel is visible to the shop surcharge helper, where nonzero also suppresses
the extra post-transaction gold debit. This cross-use does not make the
sentinel a durable quest flag; treat it as transient mode/conversation state,
and keep the surcharge behavior in `systems/shops.md`.

## 6. Relationship To TLK Branches

The `.TLK` format records control bytes and their argument widths. It does not
own the flag stores. Runtime handling belongs here and in
`systems/conversation.md`:

- `0x8C` tests the active scene's per-scene 32-bit branch slot.
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
- Model the per-scene TALK flag bank as 32-bit slots. Bit indices outside the
  clean `0..31` range build a zero mask: setters become no-ops and tests read
  as clear.
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
