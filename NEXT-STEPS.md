# Next Steps for u5-spec

A durable handoff document for resuming specification work. Updated after each meaningful chunk of progress.

**Last updated:** 2026-05-06 - first verification slice landed.

## Repository status

- **Branch:** `master` (private — to be flipped public once content is ready)
- **Latest spec commit:** `bdf28bc Correct Lord British castle binding`
- **Previous priority commits:** `015430e Add endgame and world data specs`; `8665799 Add intro and priority catalog specs`
- **Push target:** `https://github.com/cleak/u5-spec`

### What is done

- README documenting purpose, structure, and specification style guidelines.
- [`EXTRACTION.md`](EXTRACTION.md) — master inventory derived from the actual GOG release file listing. Catalogs every code module, data file, algorithm, and cross-cutting reference table the engine will need to reproduce.
- 58 cleanroom spec docs: 26 system specs, 25 format specs, and 7 catalogs (~173,500 words).
- Major game-mode and first-playable systems are covered: launcher/startup, main loop, input, text, save/load, overworld, town mode, dungeon mode, combat, visibility, time, magic, karma, doors/Z transitions, active objects, animation, shops, NPC schedules, encounters, conversation, intro, endgame, lighting, weather, and U4 transfer.
- Recent additions: `systems/launcher.md`, `systems/animation.md`, `formats/font-ch.md`, `formats/font-hcs.md`, `formats/font-pcs.md`, `formats/bit.md`, `formats/look2-dat.md`, `formats/signs-dat.md`, `formats/question-dat.md`, `formats/karma-dat.md`, `formats/story-dat.md`, `formats/endmsg-dat.md`, `formats/miscmsg-dat.md`, `formats/shoppe-dat.md`, `formats/end-dat.md`, `catalogs/gazetteer.md`, and `catalogs/quest-graph.md`.

### Remaining high-value gaps

- Non-optional Priority A prose docs are now covered for the analyzed DOS baseline.
- `formats/ega-driver.md` remains optional unless exact display-driver behaviour becomes in scope.
- The first verification slice now runs in `..\u5-engine` against local game
  data and logs corrections. The first run bound Lord British's castle evidence
  to `CASTLE:0` and corrected the older "fifth castle slot" wording.

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
|-- README.md
|-- NEXT-STEPS.md       # this file
|-- EXTRACTION.md       # master inventory of everything to be specified
|-- systems/            # coherent gameplay systems
|-- formats/            # data file formats
`-- catalogs/           # cross-cutting reference tables
```

## Specification style (reiterated from README)

- **Implementation-agnostic.** Describe what is true about the original; do not prescribe Rust types or memory layouts for the engine.
- **Complete.** Every number has a range and unit; every state transition has every condition.
- **Self-contained.** Readable cold by someone who has not seen the game or its code.
- **Sourced.** Every nontrivial claim names where it was derived from (file offset, function address, or empirical observation). When derived from `..\u5-decomp`, cite the function or file that was analyzed without reproducing decompiled code.

## Recommended next session

Continue with one of these narrow batches:

- Extend the `..\u5-engine` verification slice from a data-loading/pathfinding
  smoke test into an interactive first-playable room loop if exact movement and
  conversation parity becomes required.
- Analyze EGA.DRV only if exact display-driver behaviour becomes a required public spec.

## Long-running open questions

Tracked so they don't get lost:

1. **Hybrid prose-and-tables** vs. pure prose. Probably hybrid: prose for behavior, tables for layouts. Decide once the first format spec is written.
2. **Versioning baseline.** Ultima V had multiple releases (Apple II, C64, Amiga, IBM PC, with patches). Default baseline tag: "IBM PC EGA / Origin v1.x". Note version-specific behavior even if we never plan to support other versions.
3. **In-game vs. generic naming.** Use Ultima V's in-game names ("Britannia", "Lord British", "the Codex"). This is documentation of a specific game, not a generic CRPG engine.
4. **License flip timing.** Repo is private until content is ready. README declares CC-BY-4.0 license intent for spec prose. Decide when to publish — probably after the first system + format spec are complete and the style settles.
