# AGENTS.md

This file provides guidance to Codex and other coding agents working in the
clean Ultima V specification repository inside the dirty workspace.

## What this repo is

`u5-spec` is the clean specification layer for an Ultima V engine recreation.
It describes original game behavior, data formats, catalogs, and compatibility
requirements without reproducing original source, decompiled output, assembly,
or raw copyrighted data.

This repo is allowed to live beside the private decompilation repository in
`C:\Projects\Rust\u5-dirty`, but its contents must remain clean. The separate
engine implementation must be able to use this repository without ever seeing
`u5-decomp`.

## Cleanroom rule

Specs describe behavior and structure, not code.

Allowed in this repo:

- Implementation-agnostic prose.
- Tables of semantic fields, ranges, states, commands, and named cases.
- Source provenance that names private analysis notes by path.
- Empirical verification summaries that describe observed behavior.

Forbidden in this repo:

- Decompiled C, pseudocode copied from Ghidra, or renamed source-like logic.
- Assembly excerpts.
- Raw byte dumps, large verbatim string dumps, or copyrighted data extracts.
- Private runtime address tables or offset-heavy transcriptions.
- Rust engine types, storage decisions, or implementation-specific design.

When deriving a spec from `..\u5-decomp`, write the spec from scratch in your
own words. Cite the private note or analysis artifact as provenance, but do not
copy its text.

## Local paths

This checkout is nested inside the dirty workspace:

| Resource | Path | Notes |
|---|---|---|
| Dirty workspace | `C:\Projects\Rust\u5-dirty` | Contains both private analysis and clean spec repos. |
| Private analysis | `..\u5-decomp` (`C:\Projects\Rust\u5-dirty\u5-decomp`) | May contain decompiled code and copyrighted-derived notes. Use only as provenance. |
| This spec repo | `C:\Projects\Rust\u5-dirty\u5-spec` | Clean prose and semantic tables only. |
| Clean engine | outside this dirty workspace | Must consume this spec, not dirty analysis. Do not edit it from here unless the user explicitly redirects. |

If older docs mention `C:\Projects\Rust\u5-spec`,
`C:\Projects\Rust\u5-decomp`, or sibling `..\u5-engine`, treat those as older
checkout paths and update them to the current layout when editing related text.

## Repo layout

```text
u5-spec/
|-- README.md
|-- NEXT-STEPS.md       # durable handoff and current priorities
|-- EXTRACTION.md       # master inventory and status table
|-- RETRACTIONS.md     # append-only index of withdrawn/inverted claims
|-- OPEN-QUESTIONS.md   # index of published open/unverified items and what settles each
|-- scripts/            # mechanical checks (contamination, cross-references)
|-- systems/            # behavior specs for gameplay systems
|-- formats/            # file-format specs
`-- catalogs/           # cross-cutting reference catalogs
```

## Writing standards

- Be implementation-agnostic. Describe what the original does, not how the new
  engine should store it.
- Be complete enough to implement against. Give ranges, units, state
  transitions, scene boundaries, and failure cases.
- Be self-contained. A clean-room implementer should not need private notes to
  understand the contract.
- Be sourced. Every nontrivial claim should name semantic evidence, such as a
  private analysis note path, public file-format observation, or verification
  result.
- Keep wording semantic. Prefer "the actor chooses a visible target" over
  source-shaped branch descriptions.
- Do not introduce raw examples from game files unless they are transformed
  into clean semantic descriptions.

## Recommended workflow

1. Read `NEXT-STEPS.md` for current state and open gaps.
2. Read `EXTRACTION.md` to place the work in the inventory.
3. Read the relevant existing `systems/`, `formats/`, or `catalogs/` docs.
4. If private analysis is needed, inspect `..\u5-decomp` separately, then close
   that context and write clean prose here.
5. Add or update source provenance without copying private text.
6. Check for contamination before finishing: no source code, assembly, raw
   dumps, or address-heavy tables. Run the checker - it is mechanical and
   takes a second:

   ```text
   python scripts/check_contamination.py
   ```

   It must print `clean`. Exit 1 means contamination; exit 2 means the checker
   itself is broken and the result means nothing.

7. Check the references the same way - every `systems/`, `formats/` or
   `catalogs/` path and every "Section N" pointer must resolve, `RETRACTIONS.md`
   ids must be contiguous, and `EXTRACTION.md`'s document counts must match the
   tree:

   ```text
   python scripts/check_crossrefs.py
   ```

   Same exit convention. If an edit leaves a claim open, unverified or
   disputed, add it to `OPEN-QUESTIONS.md` with what would settle it; remove
   the row when the owning document is updated.

## Citing private analysis

Cite the **directory**, never the note filename:

```text
Source provenance: derived from private analysis in
`u5-decomp/functions/<OVERLAY>/`.
```

Private note filenames encode a routine's load offset and its private label, so
a list of them is a private address table however scholarly it reads. This is
not hypothetical: 1056 such citations across 77 files once exposed 440 distinct
private entry points here, and they were introduced by a repair pass that was
improving the document's sourcing. Put the real provenance in the prose - say
what was established and how - and let the path name only the directory.

## Retractions are mandatory

When an edit **withdraws or inverts** a statement this repository has already
published, two things MUST land in the same change:

1. **A row appended to `RETRACTIONS.md`,** taking the next free `Row` id.
   Ids are permanent and never reused or renumbered, so a consumer can record
   an "audited through" watermark. The table is append-only and ordered
   by spec commit. Give the commit (or the issue number, if the withdrawn text
   was only ever published in an issue answer), the document, the section, what
   was withdrawn, and what replaced it. Quote the withdrawn claim closely enough
   that a consumer can grep their own code for it.
2. **A one-line inline note in the affected section**, in that document's own
   voice, at the point of the change. `systems/timing.md` section 4 is the model:
   the corrected contract is stated, then one sentence says the earlier text said
   the opposite and is retracted. Do not restructure the section to make room for
   it - one line is the whole convention.

This applies whether the earlier statement lived in spec prose or in a closing
comment on an issue. Issue answers are this project's delivery channel to the
implementation, so a withdrawn answer strands an implementation exactly the same
way a withdrawn paragraph does.

It does **not** apply to a clarification: added detail, a narrowed scope that
leaves the old text still true, a gap filled for the first time, or a rename
with no behavioural consequence. Be strict. A row that sends a consumer to
re-audit a section that did not change costs them real work and erodes trust in
the whole index, so when in doubt, leave it out and say why in the commit
message.

The reason the convention exists: an audit against spec HEAD found 106 contracts
the clean engine did not implement, and most were not oversights. The engine had
faithfully implemented a spec revision that was later reversed, its tests pinned
the retracted behaviour, and nothing signalled the reversal. `RETRACTIONS.md` is
the signal.

## Status and open questions

Use `EXTRACTION.md` for public inventory status and `NEXT-STEPS.md` for durable
handoff notes. When closing a gap, update both if the status or recommended
next work changes.

## Git and artifacts

Do not commit original Ultima V data, binaries, saves, Ghidra output, or dirty
analysis artifacts in this repo. If such a file appears in `git status`, stop
and investigate before staging anything.
