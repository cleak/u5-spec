# Runtime Architecture

## 1. Scope

This document records low-level runtime facts that affect compatibility but do
not belong to a single gameplay system. It is intentionally semantic: it does
not reproduce private linker tables, runtime addresses, disassembly, or raw
binary metadata.

## 2. Toolchain And Overlay Runtime

The DOS executable is a small-model MS C 5.x program using Phoenix PLINK86 for
overlay management. The overlay runtime owns swap-in, slot management,
critical-error integration, and process-exit support. Public specs should refer
to this as the PLINK86 overlay runtime, not as the Microsoft Overlay Linker.

Modern implementations do not need to reproduce PLINK86. They do need to
preserve the observable overlay boundaries already captured in the system specs:
which command family or shop family owns a flow, which data file is loaded, and
which resident systems remain shared across overlays. The public call and
residency contract for those overlay boundaries is specified in
`overlay-abi.md`.

## 3. Runtime Library Profile

The game-logic runtime is integer-only and statically partitioned:

- No floating-point arithmetic is used for gameplay math.
- Text rendering uses the resident text-output primitives, not `printf`-style
  formatted output.
- Disk I/O uses direct DOS handle-style wrappers, not C `stdio` streams.
- Gameplay data lives in static resident state, overlay-local state, or fixed
  buffers; there is no C heap allocator for gameplay objects.

The only dynamic memory-style behaviour relevant to the original binary is the
overlay runtime's own slot management. A clean implementation can use modern
allocation internally, but the public gameplay contract should not infer heap
objects, floating-point intermediates, or formatted-output parsing where the
original used fixed integer/state helpers.

## 4. Hot Shared Primitives

Two resident helpers dominate cross-overlay behaviour:

- The wrap-aware string printer is the central text primitive. Overlays call the
  resident text system directly; there is no per-overlay text thunk layer.
- The per-turn cleanup is the central time/light/state cleanup primitive reached
  by every active gameplay mode. The overworld, town, and combat loops reach it
  after a consumed turn; the dungeon loop reaches it unconditionally at the head
  of each iteration, so its call is not gated on the previous command having
  consumed a turn (`systems/main-loop.md` Section 6, `systems/time.md`
  Section 3).

These are architectural facts for prioritising compatibility: most visible
gameplay eventually crosses one or both of these shared helpers.

## 5. Sources

This public description is a cleanroom prose rewrite from private architecture
and library-fingerprint analysis. It does not reproduce decompiled source,
assembly listings, raw bytes, linker tables, or private address tables.

- PLINK86 overlay-runtime identification and trampoline architecture --
  `u5-decomp/notes/engine-architecture.md` and
  `u5-decomp/notes/full_call_graph.md`.
- MS C runtime-library absence/presence fingerprint --
  `u5-decomp/functions/ULTIMA_EXE/_LIBRARY_FIDB.md`.
- Hot-path call analysis for text output and per-turn cleanup --
  `u5-decomp/notes/hot_path_analysis.md`.
