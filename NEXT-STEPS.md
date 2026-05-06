# Next Steps for u5-spec

A durable handoff document for resuming specification work. Updated after each meaningful chunk of progress.

**Last updated:** 2026-05-06 — priority spec batches landed.

## Repository status

- **Branch:** `master` (private — to be flipped public once content is ready)
- **Latest commit:** `015430e Add endgame and world data specs`
- **Previous priority commit:** `8665799 Add intro and priority catalog specs`
- **Push target:** `https://github.com/cleak/u5-spec`

### What is done

- README documenting purpose, structure, and specification style guidelines.
- [`EXTRACTION.md`](EXTRACTION.md) — master inventory derived from the actual GOG release file listing. Catalogs every code module, data file, algorithm, and cross-cutting reference table the engine will need to reproduce.
- 41 cleanroom spec docs: 24 system specs, 12 format specs, and 5 catalogs (~153,000 words).
- Major game-mode and first-playable systems are covered: main loop, input, text, save/load, overworld, town mode, dungeon mode, combat, visibility, time, magic, karma, doors/Z transitions, active objects, shops, NPC schedules, encounters, conversation, intro, endgame, lighting, weather, and U4 transfer.
- Recent additions: `systems/intro.md`, `systems/endgame.md`, `systems/lighting.md`, `systems/weather.md`, `systems/u4-transfer.md`, `formats/brit-dat.md`, `formats/under-dat.md`, `formats/dungeon-dat.md`, `formats/cbt.md`, `formats/ool.md`, `formats/data-ovl.md`, `catalogs/npc-roster.md`, `catalogs/monster-bestiary.md`, and `catalogs/item-list.md`.

### Remaining high-value gaps

- `systems/launcher.md` needs fresh `ULTIMA5.COM` analysis before it can be written.
- `systems/animation.md` remains open, though it may be folded into `systems/active-objects.md`.
- Medium/low format specs remain for fonts, bitmap images, LOOK2, signs, questions, shop text, story/end/misc/karma text, and optionally the EGA driver.
- `catalogs/gazetteer.md` and `catalogs/quest-graph.md` remain. The quest graph is the expensive one because it needs bulk TLK decoding and keyword-chain analysis.
- The first-playable verification slice still needs a concrete pass against Lord British's throne room.

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

- Write the medium-priority graphics/text format specs: `formats/font-ch.md`, `formats/font-hcs.md`, `formats/font-pcs.md`, `formats/bit.md`, `formats/look2-dat.md`, `formats/signs-dat.md`, and `formats/question-dat.md`.
- Write the remaining low-priority text data specs: `formats/story-dat.md`, `formats/endmsg-dat.md`, `formats/miscmsg-dat.md`, `formats/karma-dat.md`, and `formats/end-dat.md`.
- Write `catalogs/gazetteer.md` from the already specced map/location systems.
- If more decomp work is preferred first, analyze `ULTIMA5.COM` so `systems/launcher.md` can be written, or analyze EGA.DRV if display-driver behavior becomes in scope.

## Long-running open questions

Tracked so they don't get lost:

1. **Hybrid prose-and-tables** vs. pure prose. Probably hybrid: prose for behavior, tables for layouts. Decide once the first format spec is written.
2. **Versioning baseline.** Ultima V had multiple releases (Apple II, C64, Amiga, IBM PC, with patches). Default baseline tag: "IBM PC EGA / Origin v1.x". Note version-specific behavior even if we never plan to support other versions.
3. **In-game vs. generic naming.** Use Ultima V's in-game names ("Britannia", "Lord British", "the Codex"). This is documentation of a specific game, not a generic CRPG engine.
4. **License flip timing.** Repo is private until content is ready. README declares CC-BY-4.0 license intent for spec prose. Decide when to publish — probably after the first system + format spec are complete and the style settles.
