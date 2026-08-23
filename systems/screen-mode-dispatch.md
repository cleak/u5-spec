# Screen-Mode Dispatch — WITHDRAWN

**This document has been withdrawn in full. Its subject did not exist.**

Everything previously published on this page — the "resident screen/prompt
presentation controller", the "presentation-mode byte", the "per-mode state
table", the "mode-setup helper", the "mode-query helper", the "low-bit toggle
path controlled by resident presentation flags", and the "remaining
presentation-parity work" items chasing a per-mode table — described a
subsystem that the original game does not have. The document was built on a
private analysis name that asserted an owner (the display subsystem) and a
mechanism (dispatch on a screen-mode index) that re-derivation from the shipped
binaries showed to be false.

The resident routine it described is the game's **"please insert the right
disk" prompt and disk-error recovery handler**. Point by point:

| Old claim on this page | What it actually is |
|---|---|
| "presentation-mode byte" | the index of the game distribution disk currently required |
| "per-mode state table" | one drive letter per disk, with a marker meaning "unknown, must ask" |
| "mode-setup helper" | the operating system's *select default drive* call |
| "mode-query helper" | the operating system's *get default drive* call |
| "low-bit toggle path controlled by resident presentation flags" | the handler switching to the machine's other floppy drive |
| "the disk prompt is a narrow sub-case of this controller" | inverted — the disk prompt is the whole routine |
| "per-mode table mapping presentation-mode values to visible setup branches" | no such table exists; there is nothing left to decode here |

Only two claims from the old page survive: the dispatch cell is separate from
the display-driver dispatch cell, and the handler installs an immediate-return
guard so that an error raised during the prompt is suppressed rather than
recursed into. Both are restated in the replacement document.

The one genuinely display-related input in the routine is a two-valued
presentation-context byte that decides whether the prompt is drawn over a
picture or on a plain console. That is presentation context *for the prompt*,
not a mode index.

**Replacement: [`systems/disk-prompt.md`](disk-prompt.md).**

Provenance for the withdrawal: re-derivation from the shipped binaries recorded
in `u5-decomp/functions/ULTIMA_EXE/`,
`u5-decomp/notes/disk_insert_prompt_2026-08-23.md`, and `u5-decomp/CORRECTIONS.md`.
