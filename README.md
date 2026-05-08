# u5-spec

System-level specifications and file format documentation for an Ultima V engine recreation.

## Purpose

This repository is the contract between private analysis and implementation. It describes how Ultima V works without reproducing its code.

Each document explains one system or one file format clearly enough that an implementer can build it without ever seeing the original executable or game data.

## Structure

- [EXTRACTION.md](EXTRACTION.md) — Master inventory of code, data, and algorithms to be documented. Tracks progress.
- `systems/` — One spec per coherent gameplay system (e.g., NPC schedules, combat, conversation engine).
- `formats/` — One spec per data file format (e.g., TILES.16, SCHEDULE.DAT, *.TLK).

## Specification style

Specs describe behavior and structure, not code. They should be:

- **Implementation-agnostic** — no Rust types, no C structs, no opinions about data layout in the engine. Describe what is true about the original; leave how to represent it to the engine.
- **Complete enough to implement against** — if a number is involved, document its range, units, and where it changes. If a transition is involved, document every condition.
- **Self-contained** — a reader who has never seen the game or its code should be able to follow.
- **Sourced** — every nontrivial claim names the semantic evidence it was derived from, such as a private analysis note, a public asset/file-format observation, or an empirical verification result. Do not publish private source, decompiler output, assembly excerpts, raw byte dumps, or private address tables.

## License

The specifications themselves (prose and tables in this repository) are licensed CC-BY-4.0. They may be used by anyone wishing to build a compatible engine.

The original game and its data files are © Origin Systems / Electronic Arts. Nothing in this repository is a substitute for owning the original game.

## Sibling repositories

- `../u5-decomp` — private analysis workspace. Public specs may cite analysis-note paths as provenance, but implementation work should rely on this repository's cleanroom prose rather than private analysis content.
- `../ninth-virtue` — companion app for the original game; private analysis reference
