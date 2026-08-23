# Disk Prompt And Disk-Error Recovery

## 1. Scope

This document specifies the resident **"please insert the right disk" prompt**
and the disk-error recovery path it belongs to. In the DOS baseline the game
shipped on several floppy disks, and any file operation could fail because the
wrong disk was in the drive. This is the contract for what the game does when
that happens.

It is **not** a display-mode controller, and it is not a gameplay mode loop.

> **Withdrawal notice.** This document replaces `systems/screen-mode-dispatch.md`,
> which described the same resident routine as a "resident presentation
> controller" driven by a "presentation-mode byte" and a "per-mode state table".
> **That was wrong.** Its "presentation-mode byte" is the index of the game disk
> currently required; its "per-mode state table" is a table of drive letters; its
> "mode-setup helper" is the operating system's *select default drive* call; its
> "mode-query helper" is the operating system's *get default drive* call; and its
> "low-bit toggle path controlled by resident presentation flags" is the handler
> trying the machine's other floppy drive. The old document also inverted the
> containment: it made the disk prompt a narrow sub-case of a screen-mode
> controller, when the disk prompt is the entire routine. Readers who remember
> the old wording should discard it. See §8.

## 2. The Two Pieces Of State

The resident core keeps exactly two things for this subsystem, plus one cache.

| State | Meaning |
|-------|---------|
| **Required-disk index** | Which of the game's distribution disks is currently needed. |
| **Per-disk drive letter table** | One entry per disk, holding the drive letter where that disk was last found, or an *unknown* marker meaning "we have never found this disk; we must ask". |
| **Already-prompted cache** | Remembers which disk the handler last dealt with, so a silent retry can be distinguished from a first attempt. |

The required-disk index takes these values:

| Index | Disk |
|-------|------|
| 0 | the Program disk |
| 1, 3 | the Britannia disk |
| 4 | the *Ultima IV* Player disk (used only by the character-transfer flow) |
| 2, 5 | folded to 1 by the disk requester before being stored |

A second byte, separate from all of the above, records only **how the prompt
should be presented**: either "plain console" or "we are currently showing a
picture, so open a small text window over it and restore the picture
afterwards". This is presentation context for the prompt. It is not what the
handler keys off, and nothing else in the subsystem depends on it.

**Lifetime.** None of this state is part of the saved game. All of it is
session-only scratch that is rebuilt at boot.

## 3. The Dispatch Cell

The resident core keeps a far-call cell holding the current disk-error handler.
That cell points back into the resident executable, not into the loaded display
driver, so it is separate from the driver dispatch cell documented in
`display-driver-abi.md`.

The cell has three observable states:

| State | Meaning |
|-------|---------|
| Insert-disk prompt handler | Normal state. This is the handler specified below. |
| Immediate-return guard | Temporary state installed while the handler is already running. A disk error raised during the prompt does nothing. |
| Write-protect error prompt | Temporary state installed by the save/write wrapper while an inner file write is active. It reports "your disk may be write-protected, try again" and waits for a key; the wrapper then restores the normal handler and retries. |

File read, file write, and drive-select failures all reach the disk layer
through this cell.

## 4. Recursion Guard

On entry the handler installs the immediate-return guard into its own dispatch
cell, and restores the normal handler before returning. A compatible
implementation must preserve this: a disk error raised *while the user is being
prompted about a disk error* is swallowed, not queued and not recursed into.

## 5. Handler Behaviour

The handler reads the required-disk index, looks up that disk's recorded drive
letter, and takes the **first** of the following that applies.

1. **Try the other floppy first.** If the recorded letter names a floppy drive
   *and* the machine is known to have more than one floppy drive, the handler
   switches to the *other* floppy, asks the operating system to make it the
   current drive, and — if this disk had not already been prompted for —
   returns without showing the user anything. This is a silent retry.

2. **Fixed-disk fallback.** If the recorded letter names a fixed disk and is not
   the unknown marker, the handler rewrites that disk's entry to the first
   floppy drive, selects it, invalidates the already-prompted cache, and
   returns. *(What the original does here is settled; whether this was intended
   as an error fallback for hard-disk installs is not asserted.)*

3. **Prompt the user.** Otherwise the handler shows the visible prompt:

   - If the presentation context says a picture is on screen, it opens a small
     text window over the picture first.
   - It prints "please insert the Ultima ..." followed by the name of the
     required disk, assembled from the required-disk index: the *Ultima IV*
     Player disk case additionally emits the extra numeral so the line reads
     "Ultima IV" rather than "Ultima V".
   - If the disk's drive letter is still unknown, it asks the user to press a
     drive letter. If the letter is already known, it ends the sentence with a
     full stop and waits for any key instead.
   - It waits for a keypress with no timeout, uppercases it, and asks the
     operating system to make that the current drive. **It loops back to the
     prompt whenever the operating system refuses the drive.**
   - On acceptance it records the letter as that disk's drive letter, notes
     "this machine has two floppy drives" if the user answered with the second
     floppy letter, and propagates the letter to the companion Britannia-disk
     entry when the required disk is index 3.
   - Finally it emits a newline on the console path, or closes the text window
     and restores the picture on the graphics path.

**Polarity, stated explicitly.** The handler asks for a *drive letter* when the
required disk's table entry is the unknown marker. It asks *again* whenever the
operating system refuses the drive the user chose.

## 6. Boot Initialisation

At boot the engine sets the required disk to the Program disk, the presentation
context to plain console, and the floppy count to one. It then asks the
operating system for the current drive and records it as the Program disk's
drive letter. If that drive is a fixed disk, the same letter is copied into the
other disks' entries — a hard-disk install already knows where everything is.
If it is a floppy, the other entries are set to the unknown marker, so the first
time each disk is needed the user is asked for it.

This is a floppy-versus-hard-disk install decision, and it is the clearest
single piece of evidence for what this subsystem is.

## 7. Disk Request And Read Retry

Two callers sit above the handler.

**The disk requester** records which disk is now needed. It folds the two
historical alias indices onto the Britannia index, stores the result as the
required-disk index, and — if that disk's drive letter is already known —
selects that drive immediately and invalidates the already-prompted cache. It
does not prompt.

**The read-with-retry helper** consumes the required-disk index before each
attempted read. If the required disk is the second Britannia index and its drive
letter is unknown, it enters the prompt handler directly. It then selects the
recorded drive and loops on the underlying open/seek/read until it succeeds.

Neither of these defines file semantics. The open/read/seek/count behaviour, the
zero-return retry signal, and the unbounded retry loop are specified in
`systems/save-load.md`.

## 8. Compatibility Rules

- Keep the disk-error dispatch cell separate from the display-driver dispatch
  cell.
- Suppress disk errors raised while the prompt is already running.
- Treat the required-disk index and the drive-letter table as session-only
  state. They do not round-trip through saved-game files.
- A modern single-directory installation may make the visible prompt a no-op,
  but should preserve the retry and error semantics owned by the I/O layer, and
  should preserve the write-protect error path as a distinct family from the
  read/insert-disk path.
- **Do not model this as a screen-mode or presentation controller.** The only
  display-related input is the two-valued presentation context that decides
  whether the prompt is drawn over a picture. There is no per-mode table and no
  scene repaint.

## 9. Notes On The Shipped Copy

The copy of the resident executable examined for this specification is a
hard-disk install in which the visible prompt block has been patched out: the
handler answers itself with the current drive instead of displaying the
question, and the routine that consumed the typed drive letter has been removed.
The prompt block is present in the image but unreachable in that build. The
behaviour specified in §5 is therefore the behaviour of the unpatched routine as
reconstructed from the surviving instructions and the surviving prompt strings.
Attributing the patch to the original installer program is **not** asserted.

## 10. Sources

This is a cleanroom behavioral rewrite from private resident function analysis.
It does not reproduce private source, decompiler output, assembly excerpts, raw
dumps, private address tables, or implementation listings.

- Handler, requester, read-retry, and boot initialisation:
  `u5-decomp/functions/ULTIMA_EXE/`,
  `u5-decomp/notes/disk_insert_prompt_2026-08-23.md`.
- Required-disk index identification and the retraction of the earlier
  "screen-mode" and "world-state" readings:
  `u5-decomp/CORRECTIONS.md`,
  `u5-decomp/notes/dosbox_probes_2026-05-07.md`.
- Write-side error handler ownership:
  `u5-decomp/notes/system-trace_save-load.md`.
- *Ultima IV* Player-disk case: `u5-decomp/functions/INTRO_OVL/`.
- Display-driver dispatch separation: `systems/display-driver-abi.md`.
- I/O semantics: `systems/save-load.md`.
