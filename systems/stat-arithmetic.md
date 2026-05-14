# Shared Counter Arithmetic

## 1. Scope

This document specifies the original engine's shared integer mutation helpers
used for counters, character statistics, resources, and rewards. It does not
assign every caller to a field; owning systems still document their own caps,
costs, and reward amounts. The purpose here is to make the common overflow and
underflow behavior explicit so systems do not invent incompatible arithmetic
rules.

The original uses fixed-width integer fields. Storage width is not itself the
gameplay cap: a one-byte field may clamp at `99`, `25`, or another
caller-supplied value, and a word field may clamp at `9999` or a character's
current maximum.

## 2. Helper Families

The resident arithmetic family has four observable shapes:

| Shape | Field width | Upper or lower bound | Comparison model | Result |
|-------|-------------|----------------------|------------------|--------|
| Capped add, byte field | 8-bit storage | Caller-supplied upper cap | Unsigned | Increase by the requested amount unless the resulting value reaches or exceeds the cap; in that case store the cap. |
| Capped add, word field | 16-bit storage | Caller-supplied upper cap | Signed | Increase by the requested amount unless the resulting value reaches or exceeds the cap; in that case store the cap. |
| Floor subtract, byte field | 8-bit storage | Zero | Unsigned | Decrease by the requested amount only when the current value is greater than the amount; otherwise store zero. |
| Floor subtract, word field | 16-bit storage | Zero | Signed | Decrease by the requested amount only when the current value is greater than the amount; otherwise store zero. |

For byte fields, callers should supply byte-range caps and deltas unless a
documented compatibility case says otherwise. With normal byte-range inputs, the
result of a capped byte add is always in `0..cap`, and the result of a byte
subtract is always in `0..old_value`. Do not substitute wraparound arithmetic
for these helpers.

For word fields, comparisons are signed. This matters for fields that can pass
through negative states, especially hit points and other character-record words.
Caller docs should state whether the field itself permits negative values; this
shared helper only defines what happens when the helper is invoked.

## 3. Caller-Owned Caps

The helper family does not define a global cap table. Each caller supplies or
implies the bound appropriate to the field it is mutating. Public examples
already specified in owning systems include:

| Field family | Public cap or floor | Owning spec |
|--------------|---------------------|-------------|
| Gold and several reward counters | Usually capped at `9999` when routed through the reward or payment helper that names that cap | `systems/inventory.md`, `systems/combat.md`, `systems/shops.md` |
| Spell charges from M-Mix | Capped at `99` | `systems/magic.md`, `catalogs/spell-list.md` |
| R-Ready carried equipment stock | Capped at `99` on unequip return | `systems/inventory.md` |
| Shrine-side virtue standing increases | Capped at `99` | `systems/karma.md` |
| Torch and light counters | Floor at zero during decay; specific light sources name their own add caps | `systems/lighting.md`, `systems/dungeon-mode.md` |
| Character healing | Capped at that character's current maximum HP unless the spell explicitly sets HP | `systems/magic.md` |

The private caller census currently identifies fifty calls into this helper
family across the analyzed resident and overlay code: fifteen byte capped-add
calls, sixteen word capped-add calls, thirteen byte floor-subtract calls, and
six word floor-subtract calls. At clean-spec level those calls group into these
publicly named families:

| Caller family | Helper shape | Public contract |
|---------------|--------------|-----------------|
| Party food/provision cadence | Word floor-subtract | Hourly provision use subtracts the number of active eaters and floors at zero. Starvation is caller-owned when the counter is already zero. |
| Party HP recovery and healing | Word capped-add | Rest, small-heal spells, and probabilistic recovery add HP up to the member's current maximum HP. |
| Party damage | Word floor-subtract | Damage paths that route through the shared word subtract floor HP at zero before caller-owned death/status handling runs. |
| Combat and spell experience credit | Word capped-add | Experience rewards that use the helper cap at `9999`; eligibility, reward unit, and narration remain caller-owned. |
| Inventory and equipment stock grants | Byte capped-add | Spell charges, equipment stock, torches, gems, keys, reagents, potions, scrolls, and similar byte counters cap at the caller's stock maximum, most commonly `99`. |
| Inventory and shop spending | Byte or word floor-subtract | Purchases, reagent use, key/gem/torch spending, and similar debit paths floor at zero only when routed through the helper; affordability/refusal checks remain caller-owned. |
| Virtue standing increases | Byte capped-add | Shrine-side standing increases clamp at `99`; non-shrine virtue deltas still belong to `systems/karma.md`. |
| Light, spell, and rest timers | Byte capped-add or floor-subtract | Per-turn cleanup and schedule/timer paths age byte counters without wrapping; the owning time/lighting specs define cadence and terminal effects. |
| Modal selection cursors | Word capped-add or floor-subtract | Some UI selectors reuse the word helpers to keep a selection index within caller-supplied bounds. These calls are presentation control, not gameplay resource mutation. |
| Blackthorn rescue/story floors | Byte or word caller-local clamp plus helper-family arithmetic where routed | Blackthorn rescue raises selected story/standing state to a minimum before continuing; the Blackthorn spec owns those scene-specific state meanings. |

Unknown caps must remain open in the caller's document. A clean implementation
should not infer `255` for byte counters or `65535` for word counters unless a
caller is known to use raw storage-width wraparound rather than this shared
family.

## 4. Compatibility Rules

- Use capped addition for reward, healing, stock-increment, and timer-extension
  paths only when the owning system routes through the shared helper family.
- Use floor subtraction for spending, damage, decay, and depletion paths only
  when the owning system routes through the shared helper family.
- If a caller has custom arithmetic, that caller's system spec overrides this
  shared document.
- Preserve the signed word comparison model for signed character fields. A
  modern unsigned clamp can disagree with the original near negative values.
- Treat the helper as mutating the target field in place and producing no
  gameplay result value of its own. Any caller-visible success, failure,
  narration, redraw, or reward result belongs to the caller.

## 5. Boundaries And Caller-Owned Work

The shared-helper contract is complete at clean-spec level: the four helper
shapes, comparison models, in-place mutation behavior, module-level call
census, and public caller-family inventory are all specified above. This
document intentionally stops short of becoming a global field table.

Exact field/cap pairings belong in the owning gameplay specs. When a system
needs byte-compatible behavior for a specific shop price, reward, timer,
counter, or character-record field, that system should state the field, cap,
cost, and success/failure rule in source-free prose. It should cite this
document only for the common overflow or underflow behavior.

Custom arithmetic also remains caller-owned. Some systems assign fields
directly, perform caller-local min/max checks, or use arithmetic that is not
routed through this helper family. Those paths override this shared document
and should be specified where the caller's visible behavior is specified.

For byte helpers, clean implementations should use byte-range caps and deltas
unless an owning spec documents a traced exception. Do not infer compatibility
behavior for oversized byte-helper arguments from storage width alone; if such
a caller matters publicly, document that caller rather than broadening this
shared rule.

## 6. Sources

This is a cleanroom behavioral rewrite from the resident shared arithmetic
helper notes. It does not reproduce private source, decompiler output,
assembly excerpts, raw dumps, private address tables, or implementation
listings.

- Byte capped-add behavior: `u5-decomp/functions/ULTIMA_EXE/0x3EF0_sat_add_byte.md`.
- Word capped-add behavior and signed comparison: `u5-decomp/functions/ULTIMA_EXE/0x3F14_sat_add_word.md`.
- Byte floor-subtract behavior: `u5-decomp/functions/ULTIMA_EXE/0x3F36_sat_sub_byte.md`.
- Word floor-subtract behavior and signed comparison: `u5-decomp/functions/ULTIMA_EXE/0x3F54_sat_sub_word.md`.
- Module-level caller census and helper idiom inventory:
  `u5-decomp/notes/engine_idioms.md`.
- Publicly named caller-family evidence:
  `u5-decomp/functions/ULTIMA_EXE/0x2AE8_per_turn_party_damage.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x2D7A_input_party_select.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x400C_party_random_jolt.md`,
  `u5-decomp/functions/ULTIMA_EXE/0x475A_npc_schedule_tick.md`,
  `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`, and
  `u5-decomp/functions/CAST2_OVL/0x03C2_heal_one_member.md`.
