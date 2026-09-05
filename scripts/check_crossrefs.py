#!/usr/bin/env python3
"""Cross-reference checker for the clean spec tree.

Verifies the things a reader relies on that no prose review catches:

1. Every `systems/…`, `formats/…` or `catalogs/…` document path mentioned in
   any tracked markdown file exists. Private provenance paths that name the
   sibling analysis workspace (`u5-decomp/…`, `../u5-decomp/…`) are ignored.
2. Every "`<doc>` Section N[.M]" or "`<doc>` §N[.M]" reference points at a
   numbered heading that actually exists in that document.
3. `RETRACTIONS.md` row ids are contiguous from R001 with no duplicates, and
   every document a row names exists.
4. The document counts stated in `EXTRACTION.md` match the tree.

Exit 0 = clean, 1 = defects found, 2 = the checker itself failed its
self-test (and its verdict means nothing).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOC_DIRS = ("systems", "formats", "catalogs")

PATH_RE = re.compile(r"(?<![\w/.-])((?:systems|formats|catalogs)/[A-Za-z0-9_.-]+?\.md)")
PRIVATE_PREFIX_RE = re.compile(r"u5-decomp/")
# "`systems/foo.md` Section 3", "`systems/foo.md` Sections 3 and 4",
# "`systems/foo.md` §3.1", "systems/foo.md section 12.2"
SECTION_REF_RE = re.compile(
    r"`?((?:systems|formats|catalogs)/[A-Za-z0-9_.-]+?\.md)`?"
    r"(?:'s)?\s*(?:,\s*)?(?:[Ss]ections?|§)\s*(\d+(?:\.\d+)*)"
)
HEADING_RE = re.compile(r"^#{1,6}\s+(\d+(?:\.\d+)*)[.:)]?\s", re.M)
RETRACTION_ROW_RE = re.compile(r"^\|\s*R(\d{3})\s*\|(.*)$")
EXTRACTION_COUNT_RE = re.compile(r"^- (\d+) (?:system specs|file-format specs|cross-cutting catalogs) in `(systems|formats|catalogs)/`\.", re.M)


def tracked_markdown() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if ".git" not in p.parts)


def headings_of(doc: Path, cache: dict[Path, set[str]]) -> set[str]:
    if doc not in cache:
        text = doc.read_text(encoding="utf-8", errors="replace")
        cache[doc] = set(HEADING_RE.findall(text))
    return cache[doc]


CHECKED = {"paths": 0, "sections": 0}


def check_paths(files: list[Path]) -> list[str]:
    problems = []
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in PATH_RE.finditer(text):
            # ignore private provenance: the 40 chars before the match name the sibling repo
            head = text[max(0, m.start() - 40):m.start()]
            if PRIVATE_PREFIX_RE.search(head):
                continue
            CHECKED["paths"] += 1
            if not (ROOT / m.group(1)).is_file():
                line = text.count("\n", 0, m.start()) + 1
                problems.append(f"{f.relative_to(ROOT)}:{line}: references missing document `{m.group(1)}`")
    return problems


def check_sections(files: list[Path]) -> list[str]:
    problems = []
    cache: dict[Path, set[str]] = {}
    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for m in SECTION_REF_RE.finditer(text):
            doc = ROOT / m.group(1)
            if not doc.is_file():
                continue  # reported by check_paths
            head = text[max(0, m.start() - 40):m.start()]
            if PRIVATE_PREFIX_RE.search(head):
                continue
            number = m.group(2)
            CHECKED["sections"] += 1
            if number not in headings_of(doc, cache):
                line = text.count("\n", 0, m.start()) + 1
                problems.append(
                    f"{f.relative_to(ROOT)}:{line}: `{m.group(1)}` has no numbered heading {number}"
                )
    return problems


def check_retractions() -> list[str]:
    problems = []
    path = ROOT / "RETRACTIONS.md"
    if not path.is_file():
        return ["RETRACTIONS.md is missing"]
    expected = 1
    seen: set[int] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        m = RETRACTION_ROW_RE.match(line)
        if not m:
            continue
        rid = int(m.group(1))
        if rid in seen:
            problems.append(f"RETRACTIONS.md:{lineno}: duplicate row id R{rid:03d}")
        elif rid != expected:
            problems.append(f"RETRACTIONS.md:{lineno}: row id R{rid:03d} breaks the sequence (expected R{expected:03d})")
        seen.add(rid)
        expected = max(expected, rid) + 1
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) >= 2:
            for doc in PATH_RE.findall(cells[1]):
                if not (ROOT / doc).is_file():
                    problems.append(f"RETRACTIONS.md:{lineno}: R{rid:03d} names missing document `{doc}`")
    if not seen:
        problems.append("RETRACTIONS.md: no rows parsed - table format changed?")
    return problems


def check_extraction_counts() -> list[str]:
    problems = []
    path = ROOT / "EXTRACTION.md"
    text = path.read_text(encoding="utf-8")
    stated = {d: int(n) for n, d in EXTRACTION_COUNT_RE.findall(text)}
    if set(stated) != set(DOC_DIRS):
        problems.append(f"EXTRACTION.md: expected count lines for {DOC_DIRS}, found {sorted(stated)}")
    for d in DOC_DIRS:
        actual = len(list((ROOT / d).glob("*.md")))
        if d in stated and stated[d] != actual:
            problems.append(f"EXTRACTION.md: says {stated[d]} docs in `{d}/`, tree has {actual}")
    return problems


def self_test() -> None:
    assert PATH_RE.findall("see `systems/combat.md` and formats/tlk.md.") == ["systems/combat.md", "formats/tlk.md"]
    assert PATH_RE.findall("u5-decomp/formats/maps.md ../u5-decomp/systems/x.md") == [], "a slash before the path means it is a private provenance path"
    refs = [(a, b) for a, b in SECTION_REF_RE.findall("`systems/moons.md` Section 3, `systems/time.md` §11.2 and catalogs/x.md section 4")]
    assert refs == [("systems/moons.md", "3"), ("systems/time.md", "11.2"), ("catalogs/x.md", "4")], refs
    assert HEADING_RE.findall("## 3. Title\n### 3.1 Sub\n#### 3.1.2 Deep\n## Notes\n") == ["3", "3.1", "3.1.2"]
    m = RETRACTION_ROW_RE.match("| R012 | `abc123` | `systems/a.md`, `formats/b.md` | 2 | x | y |")
    assert m and m.group(1) == "012"
    assert PATH_RE.findall(m.group(2).split("|")[1]) == ["systems/a.md", "formats/b.md"]
    assert EXTRACTION_COUNT_RE.findall("- 49 system specs in `systems/`.\n- 26 file-format specs in `formats/`.\n- 9 cross-cutting catalogs in `catalogs/`.\n") == [("49", "systems"), ("26", "formats"), ("9", "catalogs")]


def main() -> int:
    try:
        self_test()
    except AssertionError as exc:
        print(f"self-test FAILED: {exc}")
        return 2
    files = tracked_markdown()
    problems = []
    problems += check_paths(files)
    problems += check_sections(files)
    problems += check_retractions()
    problems += check_extraction_counts()
    summary = f"{len(files)} markdown files, {CHECKED['paths']} document references, {CHECKED['sections']} section references"
    if CHECKED["paths"] < 100 or CHECKED["sections"] < 100:
        print(f"checker FAILED: implausibly few references found ({summary}); the patterns no longer match the prose")
        return 2
    if problems:
        for p in problems:
            print(p)
        print(f"{len(problems)} cross-reference defect(s) in {summary}")
        return 1
    print(f"clean: {summary}, all resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main())
