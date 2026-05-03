# Next Steps for u5-spec

A durable handoff document for resuming specification work. Updated after each meaningful chunk of progress.

**Last updated:** 2026-05-03 — initial scaffolding and extraction inventory complete.

## Repository status

- **Branch:** `master` (private — to be flipped public once content is ready)
- **Latest commit:** initial extraction inventory and repo scaffolding
- **Push target:** `https://github.com/cleak/u5-spec`

### What is done

- README documenting purpose, structure, and specification style guidelines
- [`EXTRACTION.md`](EXTRACTION.md) — master inventory derived from the actual GOG release file listing. Catalogs every code module, data file, algorithm, and cross-cutting reference table the engine will need to reproduce. ~150+ files categorized into code (resident, overlays, drivers), data (maps, NPCs/dialogue, text, graphics, audio), saves, algorithms, and cross-cutting catalogs.

### What is not yet started

- Any actual specification document. `systems/` and `formats/` directories do not exist yet.
- The shared format spec for the four-class location grouping (CASTLE / KEEP / TOWNE / DWELLING)
- The first-playable verification slice (Lord British's throne room)

## Locations

### Sibling repositories

| Repo | Path | Role |
|------|------|------|
| u5-decomp | `..\u5-decomp` (`C:\Projects\Rust\u5-decomp`) | Private. Holds Ghidra projects, raw decompiled output, analysis notes. **Do not reference its contents from any spec** — the entire point of the split is that this repo could be written by a different person without ever seeing decompilation output. |
| ninth-virtue | `..\ninth-virtue` (`C:\Projects\Rust\ninth-virtue`) | Partial reverse engineering of `ULTIMA.EXE` from a separate companion-app project. Treated as a starting reference; material there must be re-derived in this repo's own words. |

### External resources

This repo deliberately has no external dependencies. Specs are written from decompilation work that happens in `..\u5-decomp`. Game files are not needed here.

### Repo layout (current)

```
u5-spec/
├── .gitignore
├── README.md
├── NEXT-STEPS.md       # this file
└── EXTRACTION.md       # master inventory of everything to be specified
```

### Repo layout (planned)

```
u5-spec/
├── systems/            # one spec per coherent gameplay system
│   ├── main-loop.md
│   ├── overworld.md
│   ├── town-mode.md
│   ├── npc-schedules.md
│   ├── conversation.md
│   ├── combat.md
│   ├── visibility.md
│   ├── time.md
│   ├── doors.md
│   └── ...
├── formats/            # one spec per data file format
│   ├── tiles.md
│   ├── location-dat.md     # shared format for CASTLE/KEEP/TOWNE/DWELLING DAT
│   ├── npc.md
│   ├── tlk.md
│   ├── saved-gam.md
│   └── ...
└── catalogs/           # cross-cutting reference tables
    ├── tile-catalog.md
    ├── npc-roster.md
    ├── spell-list.md
    └── ...
```

## Specification style (reiterated from README)

- **Implementation-agnostic.** Describe what is true about the original; do not prescribe Rust types or memory layouts for the engine.
- **Complete.** Every number has a range and unit; every state transition has every condition.
- **Self-contained.** Readable cold by someone who has not seen the game or its code.
- **Sourced.** Every nontrivial claim names where it was derived from (file offset, function address, or empirical observation). When derived from `..\u5-decomp`, cite the function or file that was analyzed without reproducing decompiled code.

## Recommended next session

The first real spec should fall out of u5-decomp's first decomp work, not be written speculatively. Two natural first specs depending on which decomp path is taken:

### If u5-decomp goes Option A (Ghidra walkthrough on a Phase 1 leaf)

Write `systems/text-output.md` covering:

- The print primitives (`putchar`, `print_string`, `print_number`)
- The cursor model (`set_cursor_pos`, `get_cursor_x`)
- The display-mode flag (`set_display_mode`)
- How text rendering interacts with the overlay loader
- What font is used and how characters map to bitmaps (will cross-reference `formats/font-ch.md` when that exists)

### If u5-decomp goes Option B (DATA.OVL dissection)

Write `formats/data-ovl.md` covering:

- File structure overview
- Identified tables (string pools, lookup tables, etc.)
- Per-table format with offsets, types, and meaning
- Cross-references to which overlays consume which tables

## Long-running open questions

Tracked so they don't get lost:

1. **Hybrid prose-and-tables** vs. pure prose. Probably hybrid: prose for behavior, tables for layouts. Decide once the first format spec is written.
2. **Versioning baseline.** Ultima V had multiple releases (Apple II, C64, Amiga, IBM PC, with patches). Default baseline tag: "IBM PC EGA / Origin v1.x". Note version-specific behavior even if we never plan to support other versions.
3. **In-game vs. generic naming.** Use Ultima V's in-game names ("Britannia", "Lord British", "the Codex"). This is documentation of a specific game, not a generic CRPG engine.
4. **License flip timing.** Repo is private until content is ready. README declares CC-BY-4.0 license intent for spec prose. Decide when to publish — probably after the first system + format spec are complete and the style settles.
