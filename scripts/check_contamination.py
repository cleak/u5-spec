#!/usr/bin/env python3
"""Cleanroom contamination checker for u5-spec.

The spec may describe original behaviour in prose and semantic tables, and it
may cite private analysis by DIRECTORY. It may not carry private runtime
addresses, private routine labels, assembly, or raw byte dumps.

This exists because 1056 offset-bearing provenance citations, exposing 440
distinct private entry points, accumulated across 77 files without anyone
noticing. They arrived a few at a time, in a shape that reads like diligent
sourcing, and they were introduced by a repair pass that was improving the
document's rigour. No single line looked like an address table. The aggregate
was one.

Ordinary prose about shipped DATA files is deliberately not flagged: bare hex
such as `0xDC` for a terrain byte, `SAVED.GAM` offset `0x02E1`, or tile `0x116`
are public observations about files the user already owns, not private code
addresses.

Usage, from the repo root:

    python scripts/check_contamination.py              # self-test, then scan
    python scripts/check_contamination.py --self-test  # verify the rules only

Exit status: 0 clean, 1 contamination found, 2 the checker itself is broken.
"""
import os
import re
import sys

# Each rule: (name, compiled pattern, why it is forbidden)
RULES = [
    ("offset-bearing provenance citation",
     re.compile(r'[A-Za-z0-9_]+(?:_OVL|_EXE|_DRV)/0x[0-9A-Fa-f]{3,4}_[A-Za-z_0-9]+\.md'),
     "Private note filenames encode a routine's load offset and its private "
     "label. Cite the directory instead: `u5-decomp/functions/<OVERLAY>/`."),

    ("segment-relative runtime address",
     re.compile(r'\b(?:DS|CS|ES|SS):0x[0-9A-Fa-f]+'),
     "Private runtime address."),

    ("binary-relative entry point",
     re.compile(r'\b[A-Z0-9]{2,}\.(?:OVL|EXE|DRV):\+?0x[0-9A-Fa-f]+'),
     "Private entry point."),

    ("overlay-relative offset",
     re.compile(r'(?:_OVL|_EXE|_DRV)\s*[:+]\s*0x[0-9A-Fa-f]{3,4}'),
     "Private entry point."),

    # The operand must LOOK like an operand: a register, a bracket, or hex.
    # An earlier draft accepted any lowercase word, so ordinary prose beginning
    # "call immediately..." or "call copies 49 rows..." tripped it. A checker
    # with false positives gets ignored, which is worse than no checker at all.
    ("assembly instruction with operand",
     re.compile(
         r'^[ \t]*(?:mov|movzx|movsx|push|pop|call|jmp|jne|jnz|je|jz|ja|jb|jg|jl'
         r'|cmp|test|lea|xor|and|or|add|sub|adc|sbb|inc|dec|shl|shr|sar|neg|not'
         r'|mul|imul|div|idiv|int|ret)[ \t]+'
         r'(?:(?:byte|word|dword)[ \t]+)?(?:ptr[ \t]+)?'
         r'(?:\[|0x[0-9A-Fa-f]|(?:[abcd][xhl]|si|di|bp|sp|cs|ds|es|ss|ip)(?![a-z0-9_]))',
         re.M | re.I),
     "Assembly excerpt."),

    # String and flag instructions carry no operand, so the rule above cannot
    # see them. Anchored to a whole line to stay clear of prose.
    ("operandless assembly instruction",
     re.compile(
         r'^[ \t]*(?:rep|repe|repz|repne|repnz)?[ \t]*'
         r'(?:movs|stos|lods|scas|cmps)[bwd]?[ \t]*$'
         r'|^[ \t]*(?:cld|std|cli|sti|nop|pushf|popf|cbw|cwd|leave|iret|retf)[ \t]*$',
         re.M | re.I),
     "Assembly excerpt."),

    ("raw byte dump",
     re.compile(r'(?:\b[0-9A-Fa-f]{2}[ \t]+){7,}[0-9A-Fa-f]{2}\b'),
     "Raw byte sequence."),
]

SKIP_DIRS = {".git", "capture", "scripts"}


# Cases the checker MUST flag, and cases it must NOT. The checker is itself a
# repair-pass artefact, and repair passes in this project have a worse defect
# record than the errors they were cleaning up, so it gets a test of its own.
MUST_FLAG = [
    "mov al, byte ptr [0x5887]",
    "call 0x3ae6",
    "dec byte ptr [0x5887]",
    "or byte ptr [0x24e6], 2",
    "rep movsw",
    "cld",
    "DS:0x55A6",
    "ULTIMA.EXE:0x48A8",
    "CAST2_OVL:0x10FE",
    "`u5-decomp/functions/TOWN_OVL/0x1726_place_npc_at.md`",
    "A0 87 58 2A E4 50 B8 05 00 50",
]

MUST_NOT_FLAG = [
    "The call immediately returns, leaving the rectangle partly transferred.",
    "The call copies 49 rows at full 320-pixel width from the back buffer.",
    "Source provenance: `u5-decomp/functions/TOWN_OVL/`.",
    "Live terrain byte `0xDC` is the moon gate.",
    "The counter sits at `SAVED.GAM` offset `0x02E1`.",
    "Tile `0x116` is the composed-frame scratch slot. Terrain `5` is grass.",
    "Add the two values and test whether the result is below 50.",
    "Mode 3 and mode 12 both call the shared helper.",
    "The party may not test the lock while the door is already open.",
    "Increments continue until the counter reaches sixteen.",
]


def self_test():
    """Verify the rules catch what they must and ignore what they must not."""
    failures = []

    for text in MUST_FLAG:
        if not any(pat.search(text) for _, pat, _ in RULES):
            failures.append("MISSED (should flag): " + text)

    for text in MUST_NOT_FLAG:
        for name, pat, _ in RULES:
            m = pat.search(text)
            if m:
                failures.append(
                    "FALSE POSITIVE [%s] matched %r on: %s"
                    % (name, m.group(0), text))

    # Guard against mangled escapes. A literal control character silently turns
    # a rule into one that matches nothing, and the scan then reports "clean".
    # This has actually happened while authoring this file.
    for name, pat, _ in RULES:
        ctrl = [hex(ord(c)) for c in pat.pattern if ord(c) < 32]
        if ctrl:
            failures.append("MANGLED ESCAPE in rule [%s]: %s" % (name, ctrl))

    if failures:
        print("SELF-TEST FAILED (%d):" % len(failures))
        for f in failures:
            print("  " + f)
        return 1

    print("self-test passed: %d flagged, %d correctly ignored, %d rules intact"
          % (len(MUST_FLAG), len(MUST_NOT_FLAG), len(RULES)))
    return 0


def scan(root):
    """Return a list of (relpath, line_no, rule_name, why, snippet)."""
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if not fn.endswith(".md"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, root).replace("\\", "/")
            try:
                text = open(path, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError) as exc:
                print("warning: could not read %s: %s" % (rel, exc),
                      file=sys.stderr)
                continue
            lines = text.splitlines()
            for name, pat, why in RULES:
                for m in pat.finditer(text):
                    line_no = text.count("\n", 0, m.start()) + 1
                    snippet = lines[line_no - 1].strip() if line_no <= len(lines) else ""
                    hits.append((rel, line_no, name, why, snippet[:120]))
    return hits


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = scan(root)

    if not hits:
        print("clean: no contamination found")
        return 0

    by_rule = {}
    for rel, line_no, name, why, snippet in hits:
        by_rule.setdefault((name, why), []).append((rel, line_no, snippet))

    print("CONTAMINATION: %d occurrence(s)" % len(hits))
    print()
    for (name, why), items in sorted(by_rule.items(), key=lambda kv: -len(kv[1])):
        print("%s -- %d occurrence(s)" % (name, len(items)))
        print("  " + why)
        for rel, line_no, snippet in items[:10]:
            print("    %s:%d: %s" % (rel, line_no, snippet))
        if len(items) > 10:
            print("    ... and %d more" % (len(items) - 10))
        print()
    return 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    # The self-test always runs first. A checker that reports "clean" because
    # its own rules are broken is the exact failure this file exists to prevent.
    if self_test() != 0:
        sys.exit(2)
    sys.exit(main())
