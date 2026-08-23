# Overlay ABI

## 1. Scope

Ultima V's DOS executable is a resident core plus raw overlay files loaded on
demand by the Phoenix PLINK86 runtime. This spec describes the public
compatibility contract of that overlay ABI: how resident code and overlays call
overlay entry points, how overlay residency works, and what a modern engine must
preserve semantically.

This document does not publish the private trampoline bytes, runtime addresses,
or the full linker descriptor table. Public system specs should cite overlay
entry ownership by semantic module name, not by private loader addresses.

## 2. Overlay Set

The analyzed baseline uses one resident executable plus these callable overlay
families:

| Family | Role |
|---|---|
| Mode overlays | `TOWN`, `MAINOUT`, `DUNGEON`, `INTRO` |
| Presentation/helper overlays | `FLAMES`, `LOOKOBJ`, `DNGLOOK`, `FONT` |
| Actor and combat overlays | `NPC`, `COMBAT`, `COMSUBS` |
| Command and magic overlays | `SJOG`, `CMDS`, `CAST`, `CAST2`, `ZSTATS` |
| Conversation and shop overlays | `TALK`, `SHOPPES`, `SHOPPES2`, `SHOPPES3`, `BLCKTHRN` |
| Special sequence overlay | `ENDGAME` |
| Outdoor helper overlay | `OUTSUBS` |

The resident core owns shared state, file I/O, text output, input, timing,
scene routing, and many rendering primitives. The overlays own larger mode,
command, conversation, shop, spell, combat, intro, and endgame bodies.

## 3. Call Surface

Every reachable overlay entry exposed outside its own overlay is reached
through a resident trampoline emitted by the overlay linker. The trampoline has
three semantic pieces:

1. A call into the overlay runtime loader.
2. A one-based overlay identity telling the loader which overlay must be
   resident.
3. A final transfer to the requested entry point inside that overlay.

The caller does not call the overlay file directly. It calls the trampoline as
if it were an ordinary near function. The loader ensures the target overlay is
resident and then transfers control to the overlay entry. When the overlay
entry returns, control resumes at the original caller as if no module boundary
had been crossed.

The same mechanism is used for resident-to-overlay calls and overlay-to-overlay
calls. Cross-overlay calls are therefore normal application calls at the system
spec level; they do not imply a separate scripting VM or message queue.

## 4. Residency And Buffers

Overlays are assigned to a small set of shared load buffers. At any moment, one
overlay per buffer can be resident. Loading an overlay into a buffer evicts the
previous occupant of that buffer and marks the new one resident.

The public buffer groups are:

| Buffer group | Members |
|---|---|
| A | `TOWN`, `MAINOUT`, `DUNGEON`, `INTRO` |
| B | `FLAMES`, `NPC`, `COMBAT`, `BLCKTHRN`, `LOOKOBJ`, `DNGLOOK`, `OUTSUBS`, `SHOPPES`, `ENDGAME` |
| C | `SJOG`, `CMDS`, `CAST`, `TALK` |
| D | `CAST2`, `ZSTATS`, `COMSUBS`, `SHOPPES2`, `SHOPPES3`, `FONT` |

This grouping is a loading constraint, not a gameplay rule. It explains why
large systems are split the way they are and why a call may reload a file, but
it does not change the observable result of a successful call. A modern engine
can link all modules permanently, provided it preserves the same entry
ownership, side effects, and call order.

## 5. Loader Behaviour

On each trampoline call, the loader:

1. Reads the overlay identity from the trampoline metadata.
2. Looks up the overlay's loader descriptor.
3. If the overlay is already resident, skips disk I/O.
4. If it is not resident, reads the overlay file into that overlay's buffer,
   updates the residency marker, and evicts any sibling occupant of the same
   buffer.
5. Returns to the trampoline, which transfers to the requested overlay entry.

If loading fails in the original environment, the overlay runtime takes the
same disk-error and critical-error path used by the rest of startup and file
I/O. A modern implementation can report an asset-load error directly, but it
must treat missing required overlays as fatal for the attempted flow.

## 6. Entry Ownership

The overlay ABI is primarily useful as a map of ownership. A command or mode
spec should name the subsystem that owns a behaviour, even when a resident
dispatcher is the immediate caller.

Examples:

- The main loop reaches top-level overworld, town, dungeon, and intro entries
  through overlay trampolines.
- The resident A-Z command dispatcher reaches command families such as Search,
  Jimmy, Open, Get, Push, Yell, Ready, Z-stats, Cast, Use, and Talk through
  overlay trampolines.
- Combat-side commands can reuse non-combat command overlays through the same
  trampoline layer when the combat dispatcher delegates to them.
- TALK owns shop-kind dispatch at the conversation boundary and reaches the
  shop overlays through ordinary overlay entries. SHOPPES also provides shared
  renderer/helper entries used by SHOPPES2 and SHOPPES3.

This is why public specs should not infer subsystem ownership only from the
resident caller. The resident dispatcher may route a key, while the overlay
entry owns the behaviour.

## 7. Entry Table Completeness

The private analysis classifies the trampoline table into resident-called
entries, overlay-only cross entries, and a tiny number of apparently unreachable
linker exports. Public compatibility rules are:

- Treat documented resident-called and cross-overlay entries as reachable
  behaviour when their callers are reachable.
- Do not invent gameplay for apparently unreachable linker exports without a
  traced caller.
- Do not model "return stubs" as a separate public concept. The re-derived
  call graph shows ordinary overlay entries and cross-overlay entries; earlier
  return-stub interpretations were artifacts of using the wrong overlay base.

## 8. Modern Implementation Contract

A clean engine does not need a PLINK86 emulator. It should preserve:

- the same module ownership for behaviours;
- the same call ordering across mode, command, shop, conversation, spell, and
  combat boundaries;
- the same fatal/missing-resource semantics for required overlay files if it
  loads original assets dynamically;
- the same shared resident state model, where overlays read and write common
  world state rather than owning isolated copies.

It may replace the trampoline layer with direct function calls, dynamic module
dispatch, or ordinary language modules. The replacement must not introduce
extra persistence, extra turns, or additional prompts at overlay boundaries.

## 9. Boundaries And Residuals

No public overlay-ABI work remains for ordinary gameplay compatibility. The
load-bearing contract is the trampoline-mediated call surface, four shared
residency buffers, reachable entry ownership, ordinary return semantics, and
fatal missing-overlay handling described above.

The following details are intentionally outside the clean engine contract unless
a future target is a byte-compatible loader harness for the original executable:

- **Uncalled FONT exports.** Two linker exports target valid FONT overlay
  entries but have no confirmed caller in the analyzed binary set. The
  behaviours behind those entries are already specified through the intro and
  chargen systems where they are actually reached. Do not expose the uncalled
  exports as extra gameplay routes.
- **SHOPPES leaf helper shape.** Two SHOPPES utility entries omit the common
  stack-frame shape, but their visible roles are the post-transaction surcharge
  and shop greeting preamble covered by `systems/shops.md`. Their low-level
  register/stack shape is not load-bearing for a clean engine.
- **Loader descriptor auxiliary fields.** Descriptor counters and
  dependency-like state are not known to produce gameplay-visible effects in
  the analyzed flows. A clean engine should preserve residency and buffer
  semantics; it does not need to model opaque descriptor bookkeeping.

## 10. Sources

This public spec is a cleanroom behavioral rewrite from private overlay
analysis. It does not reproduce private source, decompiler output, assembly
excerpts, raw dumps, linker tables, private address tables, or implementation
listings.

- Overlay loader and trampoline analysis:
  `u5-decomp/functions/ULTIMA_EXE/`.
- Architecture orientation and PLINK86 attribution:
  `u5-decomp/notes/engine-architecture.md`.
- Overlay call graph cross-check:
  `u5-decomp/notes/full_call_graph.md`.
- Public consumers: `systems/main-loop.md`, `systems/commands.md`,
  `systems/shops.md`, `systems/conversation.md`, and `systems/runtime.md`.
- SHOPPES helper roles: `systems/shops.md` and
  `u5-decomp/functions/SHOPPES_OVL/_OVERVIEW.md`.
