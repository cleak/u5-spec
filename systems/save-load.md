# Save and Load

## 1. Overview

Ultima V persists the entire run-time game state by writing one contiguous slab of memory directly to disk. The save is not a structured serialisation — no record header, no field-by-field marshalling, no version stamp. It is a byte-image dump of a fixed-length region of the engine's data segment, paired with a smaller companion buffer holding the per-map active-object table. Loading is the inverse: read the same bytes back into the same memory region and let the running engine pick up where it left off.

Four files participate in this round trip. `SAVED.GAM` and `SAVED.OOL` are the canonical save image and its object-table companion. `BRIT.OOL` and `UNDER.OOL` were shipped as seed object tables for Britannia and the Underworld, and the load path refreshes them from `SAVED.OOL` so older plane-entry paths can read the per-plane files directly. The save path stages data through the per-plane files and conditionally updates the underworld mirror, but the traced original save handler does not prove an unconditional refresh of both mirror files on every save. A separate read-only seed, `INIT.GAM`, holds the factory image the chargen flow clones into `SAVED.GAM` when a new game starts; the engine never writes `INIT.GAM`.

The save flow is gated by Quit-and-Save (`Q`) and returns to the caller after the save prompt completes; it is not the DOS-exit path by itself. The load flow is the `J` "Journey Onward" branch of the title-menu dispatcher. A second variant — `T` for the Ultima IV character transfer — re-uses the byte-image read primitive but pulls character stats from a Ultima IV save disk rather than from a `SAVED.GAM`.

This spec describes the on-disk format, the byte-image save and load contracts, the role of each save-related file, the I/O layer's disk-prompt and retry behaviour, the empty-save guard, the underworld disk-swap path, the U4-Transfer variant, and open questions about versioning and multi-slot saves.

## 2. The save image

### 2.1 What is in it

The save image is a fixed 4192-byte region of memory whose contents reflect the full state of an active game. Every field the engine needs to resume play sits inside that region; nothing outside it is part of the save. The region holds, in roughly the order it appears in the file:

- The **character roster.** Sixteen records of thirty-two bytes each, totalling 512 bytes. The first record is the Avatar; the remaining fifteen hold every companion who can join the party, whether or not they have been recruited yet. Each record carries a name (null-padded), a gender byte, a class letter, a status letter (`G` for "Good"/alive being the typical case), the four primary stats (strength, dexterity, intelligence, magic-points), current and maximum hit points as little-endian words, an experience word, a level byte, and an eight-byte equipment-and-padding tail.

- **Inventory and runtime state.** Word counters for food, gold, and other consumables, byte counters for keys and gems, and a span of single-byte fields covering the timing/status tag, active-player index, transport/action marker, wind direction, scene id, and party Z/X/Y. The day, month, hour, and minute fields of the world clock live in this region (see `time.md`).

- **Quest progress.** Two bitmasks tracking which shrines have been ordained and which Codex pages have been visited.

- **Dungeon-map dumps and NPC met/killed flags.** Two further spans documented by third-party material as holding the dungeon-map state and per-NPC interaction flags. These regions are zero in the factory seed; their structure is verified only against external references.

- **The active object/vehicle table.** Thirty-two records of eight bytes each — `(tile, frame, x, y, z, depends1, depends2, depends3)` — holding whichever movable objects are currently live on the player's map.

The remainder of the 4192 bytes is zero in every shipped seed and may be reserved for engine state not yet identified. The exact byte offsets of each region are documented in the project's working notes; the spec's contract is "save-image is 4192 bytes of fixed-layout state, region-by-region structured as above". An implementation may store its own state in any layout, but to be byte-compatible with the original `SAVED.GAM` it must place each documented field at the documented offset.

### 2.2 Why a flat image works

Every gameplay system reads and writes its state in place inside the 4192-byte region. The engine does not maintain a parallel "save buffer" that gets serialised at save time; live state and save state are the same bytes. Saving is a memory-to-disk write; loading is a disk-to-memory read. Once the read completes, every system finds its state already correct in memory and resumes work without any per-field rebinding step. This is why there is no version marker — the engine never has to interpret the save, only blit it — and why the save is exactly the size of the resident state region.

### 2.3 The factory seed: `INIT.GAM`

`INIT.GAM` is the read-only image used by the new-game path. When the player picks "Create New Character", the chargen UI works against an in-memory copy of `INIT.GAM`, patches in the player's chosen name, gender, class, and starting virtue tallies, and writes the result out as the first `SAVED.GAM`. From that point onward, the engine never touches `INIT.GAM` again.

In a clean install, `SAVED.GAM` is byte-for-byte identical to `INIT.GAM`. The Origin build pipeline produced `INIT.GAM` by capturing one frozen snapshot of the very first save the engine emitted (with no chargen patches yet applied) and shipped that snapshot as the seed. There is no runtime path that re-creates `INIT.GAM`; implementations should treat it as a static bundled asset.

## 3. The object-overlay companion

### 3.1 The `.OOL` family

Alongside the save image, the engine maintains a smaller buffer for the active-object table — the list of movable objects (skiffs, frigates, horses, magic carpets, free-standing items the player has dropped) currently live on the active map. The on-disk story uses six files because the surface and underworld are two different maps with two different object populations:

| File | Size | Role |
|---|---|---|
| `SAVED.OOL` | 512 bytes | Runtime working copy. Surface object table in the first 256 bytes; underworld in the second 256 bytes. |
| `BRIT.OOL` | 256 bytes | Surface seed and load-time mirror of the surface half of `SAVED.OOL`; the traced save path reads it as a staging source. |
| `UNDER.OOL` | 256 bytes | Underworld seed and load-time mirror of the underworld half of `SAVED.OOL`; the traced save path reads it as a staging source and conditionally writes it. |
| `INIT.OOL` | 256 bytes | Factory seed for the surface (companion to `INIT.GAM`). Read-only at runtime. |

The on-disk record layout matches the in-memory eight-byte layout exactly: `(tile, frame, x, y, z, depends1, depends2, depends3)`, with `z = 0xFF` as the "above-ground / no z" sentinel. The surface seed contains a small fixed set of pre-placed objects — canonical Britannia ferry-skiffs and a few clustered objects — and the rest of its records are zero. The underworld seed is all zeros: there are no objects on the seed underworld map.

The mnemonic "Object Overlay Layer" is a working guess; the actual extension expansion is unknown. The role, however, is unambiguous: an object-table companion to the save image, split by world plane.

### 3.2 Why three files for two halves

Naively, the engine could carry only `SAVED.OOL` and never touch `BRIT.OOL` / `UNDER.OOL` after the install. Empirically, the load path does refresh both per-plane files from `SAVED.OOL`: the surface half is written to `BRIT.OOL`, the underworld half is written to `UNDER.OOL`, and the underworld half may be written again after the underworld disk-swap probe. The save path is different. It refreshes the staging buffers from the per-plane files, conditionally writes the underworld mirror, and writes the canonical `SAVED.OOL`.

The likely reason for the file split is that gameplay overlays read from `BRIT.OOL` or `UNDER.OOL` (rather than from the in-memory copy) when bringing a map online - when the player crosses from one world plane to the other, or when the engine needs to re-seed the active object table after a transient mode (combat, dungeon) clobbered it. The load-time mirror contract makes the per-plane files reflect the most recently loaded canonical save. A modern engine that funnels all object-table reads through a single in-memory cache can collapse the three files into one internally, but a byte-compatible file set must preserve all four save-related files and document any deliberate post-save mirror refresh policy.

## 4. The load flow

### 4.1 Trigger

The load flow is invoked from the title-screen menu when the player presses `J` for "Journey Onward". The intro overlay's main menu dispatcher maps the keystroke to an inline block of load-time code, which runs the entire load sequence before the engine transitions to the gameplay mode loop. The load is structurally not a callable function — it is embedded inline inside the intro menu's command dispatcher. There is no "load game" entry point that other code can call; the only path through the load flow is via the title-menu `J` keystroke.

### 4.2 Step-by-step

1. **Read `SAVED.GAM` into the save image region.** The full 4192 bytes are read in one operation through the I/O layer's retry-and-prompt wrapper (see Section 7). On success, the save image is in memory and every gameplay system's state is correct.

2. **Test for an empty save.** A specific byte inside the save image — by convention, an interior byte of the first character record's name field — is checked against zero. If the byte is zero, the save is treated as uninitialised. The intro prints a three-line message ("No active game", "Please create a character", "or transfer one from Ultima IV"), waits for any keystroke, and returns to the title menu. The test on an interior name byte rather than the first byte is intentional: the very first byte of the save is the leading byte of a packed control field that may be zero even for a valid save, while a player-typed name is reliably non-zero past its first character.

3. **Read `SAVED.OOL` into the dual-half object-overlay region.** The full 512 bytes are read into memory in one operation. The first 256 bytes land in the surface object overlay; the next 256 in the underworld object overlay.

4. **Mirror-write the surface half back to `BRIT.OOL`.** The 256 bytes just loaded into the surface object overlay are written out to `BRIT.OOL` through the I/O layer's write wrapper. This step is unconditional: it runs on every load, regardless of which world plane the player is on.

5. **Mirror-write the underworld half back to `UNDER.OOL`.** Symmetric to step 4. Also unconditional.

6. **Underworld disk-swap (conditional).** If the loaded save indicates the player was standing on the underworld surface at save time — scene byte is the overworld scene and party Z is non-zero — the load enters a disk-swap loop. It sets a "swap disk" wait cursor, polls for the presence of the underworld data file, and waits until detected. Once the disk is present, it re-writes the underworld half of the object overlay to `UNDER.OOL` once more to ensure the mirror is consistent. The disk-swap loop exists because the original game shipped on multiple floppies, with the underworld data on a separate disk.

7. **Final commit.** A display-mode flag is set to indicate "transition to gameplay", and the intro overlay returns to the main game loop. The next iteration reads the loaded scene byte and dispatches to the correct mode-loop overlay (overworld, town, or dungeon).

The load flow does not load the world map data files (`BRIT.DAT`, `UNDER.DAT`, `LOOK.DAT`, `.TLK`, `.NPC`, `.PTH`). Those are loaded on demand by the gameplay mode loops when the player crosses scene boundaries. If the empty-save guard fires, the intro returns to its menu loop and the title menu re-renders. There is no "auto-create" fallback — a fresh install or a wiped save requires the player to explicitly pick `C` or `T`.

## 5. The save flow

### 5.1 Trigger

The save flow is invoked when the player presses `Q` for Quit-and-Save while a game is active. The keystroke is routed by the gameplay mode loops to the resident command dispatcher, which loads the save-handler overlay (the same overlay that holds several spell effects) and calls into its save entry point.

The save handler is a callable function, distinct from the inline load flow. The asymmetry reflects the boot architecture: at the title screen, the intro overlay is already resident and embedding the load is cheap; at gameplay time, the save handler lives in a rotating overlay slot and must be brought into memory on demand.

### 5.2 Step-by-step

1. **Confirm.** The handler prints a `Save game?` prompt and blocks on a keystroke. Only `Y` and `N` are accepted. On `N`, it prints `No`, returns to gameplay, and the player remains in the same scene with no disk activity.

2. **Announce.** On `Y`, it prints `Yes` followed by `Saving...`, signalling that disk activity is about to begin.

3. **Open the save channel.** The handler asks the I/O layer to set up the save-disk channel. On a system that requires a disk swap to the player disk, this is where the swap prompt fires.

4. **Refresh object-overlay staging buffers.** The handler reads the underworld and surface per-plane `.OOL` files into the two staging halves that will become the canonical `SAVED.OOL` payload.

5. **Conditionally refresh `UNDER.OOL`.** A disk/phase-state branch can write the underworld staging half back to `UNDER.OOL`. No matching unconditional save-time write to `BRIT.OOL` has been proven in the traced handler.

6. **Write `SAVED.GAM`.** The full 4192 bytes of the save image are written from memory to disk in one operation.

7. **Write `SAVED.OOL`.** The full 512 bytes - surface and underworld halves concatenated - are written from the staging region to disk in one operation.

8. **Close and acknowledge.** The handler closes the file handles, prints `Done.`, and returns. Control returns to the gameplay mode loop; the player is back in the same scene with the in-memory state unchanged. The resident Q save command saves and continues play; exit-to-DOS is a separate mode-loop control path handled by different code.

### 5.3 What does not happen on save

The save flow does not write `INIT.GAM` or `INIT.OOL` — those are shipped read-only. It does not write the world data files. It does not write a temporary or backup copy before overwriting; a save is an immediate destructive overwrite of `SAVED.GAM` and `SAVED.OOL`. An implementation that wants crash-safety should add an out-of-band copy step.

## 6. The Ultima IV character-transfer load

The title menu's `T` key is a variant of the load flow for players who have completed Ultima IV and want to import their Avatar. It shares the byte-image read primitive with the `J` flow, but its sources differ: rather than reading `SAVED.GAM` from the player's save disk, it reads the U4-format party save from the U4 disk and stat-translates it into the U5 character-record layout.

The transfer flow loads a U5 factory seed (a `BRIT.GAM` template is referenced as a transfer-time source) into the save-image region, paints the character-roster preview screen, and accepts the player's confirmation. Once committed, the transferred Avatar's stats overwrite the seed Avatar's stats in record 0, and the result is written out as the first `SAVED.GAM` of the new game. From that point onward, the player's progress is saved and loaded through the standard `J` / `Q` paths.

The transfer flow is part of the chargen contract; see `chargen.md` for the U4-to-U5 stat translation. From the save-load system's perspective, the transfer is just one way of producing the first `SAVED.GAM`.

## 7. The I/O layer

The save and load paths sit on top of two small disk-I/O wrappers in the resident core. Both wrappers are also used by other systems — the bitmap loader for the endgame cinematic, the character-roster preview for the U4 transfer, and the look-and-talk overlays for in-mission `.DAT` reads.

### 7.1 The read wrapper

The read wrapper is a four-argument routine: filename, target buffer, expected byte count, and a flags word. Its job is the read-with-retry contract: ask the inner I/O primitive to read the requested bytes, and if the primitive returns "error" (typically because no disk is in the drive, or the wrong disk is), wait for the disk-swap prompt to be acknowledged and retry. The retry loop is unbounded — the wrapper spins until the read succeeds.

The inner primitive opens the existing file, optionally seeks to an absolute sub-file offset, reads up to a count of bytes, closes the handle, and reports either the byte count read or zero on error. Passing a zero seek offset skips the seek step and reads from the start of the file. Passing a zero byte count means "read as much as this primitive can hold", capped at 65,535 bytes. The primitive returns the operating system's byte count directly: a nonzero short read is success, while a zero return is treated by the wrapper as retry-needed. The read result is preserved across close, so close-time failures are not surfaced through this primitive.

On open, seek, or read error, the primitive records the error and dispatches to the resident critical-error handler — the disk-swap prompt routine. The wrapper re-invokes the primitive after the prompt returns, until a non-zero count comes back.

### 7.2 The write wrapper

The write wrapper is a three-argument routine: byte count, source buffer, and filename. Like the read wrapper, it provides retry-with-prompt. It also momentarily swaps the resident critical-error handler to a write-specific variant for the duration of the write, restoring the read variant afterward. The write-specific handler is presumed to print a disk-full or write-protected message rather than the read variant's "please insert disk" message. The wrapper retries while the inner writer reports zero bytes written.

The inner write primitive creates or truncates the target file, writes the requested buffer, closes the handle, and returns the operating system's written-byte count. A create or write failure records the error, invokes the current critical-error handler, and returns zero so the wrapper retries. The writer preserves the write result across close and does not report close-time failures. It also does not compare the returned byte count against the requested byte count, so a nonzero short write is treated as success by callers that only test for zero.

The save handler also uses save-overlay open/write helpers to manage its multi-file sequence. At the file-contract level the same overwrite semantics apply: `SAVED.GAM` and `SAVED.OOL` are immediately replaced by the emitted byte images, without a temporary file, backup, post-write byte-count verification, or close-error recovery path. A compatibility mode should preserve those edge cases; a modern safe-save mode can add write-then-rename and explicit length checks outside the original contract.

### 7.3 Disk swapping

The original game shipped on multiple floppy disks. The boot disk holds the executables; one or more data disks hold the world data, talk files, dungeon files, and graphics; the player save lives on a separate player disk. Every disk-related operation has a wait-cursor phase — the engine displays a different cursor shape for "loading a graphics file", "loading a world file", "saving the player disk", and "swap to the underworld disk". The disk-prompt routine prints a "please insert disk" message and waits for any keystroke to acknowledge. A modern reimplementation that runs against a single mounted directory can treat all disk-swap prompts as no-ops.

## 8. The empty-save guard

The empty-save guard (Section 4.2 step 2) doubles as the "first run" guard. A fresh install ships with `SAVED.GAM` byte-equal to `INIT.GAM`, in which the first character record's name is all zeros. The guard catches this state and prints the three-line "no active game" message, redirecting the player to chargen.

The guard is the engine's mechanism for detecting "the player has not yet created a character" without needing a separate flag. As long as `SAVED.GAM` exists and is the right size, the engine reads it; the guard then decides whether the read produced something playable or something that needs the player to go through chargen first.

A consequence is that there is no distinction between "no save" and "save was deleted" in the engine's model. If `SAVED.GAM` is missing, the read wrapper's retry loop spins forever; if it is present but empty, the guard fires. An implementation that wants to distinguish these cases should test for file existence before invoking the read wrapper.

## 9. Versioning, slots, and compatibility

The save image carries no version marker. The first byte of the save is the leading byte of the first character record's name and may legitimately be zero; nothing in the save pretends to be a magic header or format-version word. The engine relies on filename and fixed size as the contract: a file named `SAVED.GAM` of size 4192 is treated as a save image.

This is workable because the engine never changed in production — Ultima V shipped, was patched a small number of times, and the save format never moved. A modern reimplementation that wants to extend the save has two options: append a versioned trailer past the original 4192 bytes (old binaries ignore it; new binaries recognise it by a sentinel byte), or use a separate sidecar file with the original `SAVED.GAM` untouched.

The original game has a single save slot. There is one `SAVED.GAM`, one `SAVED.OOL`, one pair of mirror seeds, and any save replaces the previous one. The engine does not maintain a slot index, does not expose a "save as" flow, and does not support quick-save / quick-load. Players who wanted multiple slots did so at the file-system level. A modern reimplementation can add multi-slot saves by maintaining a list of slot directories, each holding its own quartet of files; the engine's contracts above are slot-agnostic.

## 10. Hooks into other systems

- **Time.** The world clock — year, month, day, hour, and minute — sits inside the save image at fixed offsets, alongside per-turn bookkeeping bytes. Saving and loading is a verbatim flush and reload. See `time.md` Section 11.

- **NPC schedules.** The scheduler's per-day slot-rotation table sits inside the save image. The next per-turn scheduler tick after load picks up where it left off.

- **Conversation flags.** The "have I met" / "have I killed" bitmasks live in the save image's NPC-flag region. A loaded save restores them in place; the conversation engine reads them as-is. See `conversation.md`.

- **Combat.** Combat state is *not* in the save image. Combat has its own Q/Quit parser branch, but that branch is separate from the resident save writer. An implementation that wants to allow mid-combat saves must extend the save format.

- **Chargen.** New games and U4 transfers both produce the first `SAVED.GAM` of a fresh playthrough. See `chargen.md`.

- **Inn registry.** Lodged companions are persisted in the shifted inn-guest
  view documented by `formats/saved-gam.md`. Save/load does not special-case
  that view; the marker byte, month/stay counter, and copied character payload
  round-trip as ordinary save-image bytes.

- **Bitmap and resource loading.** The same I/O layer is used by the endgame cinematic loader and the character-roster preview. The disk-prompt and retry contracts apply uniformly across all reads.

## 11. Open questions and variations

- **Save-time disk-state branch.** The save handler's v1 file targets are pinned at semantic depth: per-plane `.OOL` files are read into staging, `UNDER.OOL` has a conditional write, and `SAVED.GAM` / `SAVED.OOL` are written as the canonical save pair. The remaining open part is the exact naming of the disk/phase-state values that gate the underworld mirror write and channel setup.

- **The load-time underworld disk-swap condition.** The load flow's branch tests the saved scene and party floor before probing for the underworld data disk. The branch behaviour is clear, but the surrounding disk-inventory state machine is still documented only at compatibility depth.

- **Format versioning.** No version marker exists. An implementation that extends the save format must add a sentinel of its own and decide on a backward-compatibility policy.

- **The "OOL" expansion.** "Object Overlay Layer" is a working guess. The actual expansion is unattested; treat the name as opaque.

- **Backup-on-save.** The original game does not write a backup before overwriting `SAVED.GAM`. A power-loss or disk-error during the save can corrupt the player's save with no recovery path. Implementations should consider write-then-rename atomicity at minimum.

- **Mid-combat saves.** The resident save writer is not reached through the combat command parser. An implementation that wants to allow mid-combat saves must extend the save format with combat state and add an explicit combat-save route.

- **Two-drive vs one-drive original behaviour.** Disk-swap prompts originally fired differently on single- vs dual-floppy systems. A modern implementation against a single mounted directory can treat all prompts as no-ops; an emulator faithful to the original needs to model the per-drive disk inventory.

## 12. Sources

The behaviour described here was derived from the private function and format notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- Save handler — confirmation prompt, status messages, per-plane `.OOL` staging reads, conditional `UNDER.OOL` mirror write, canonical `SAVED.GAM` / `SAVED.OOL` writes, and disk-state branching — derived from `u5-decomp/functions/CAST2_OVL/0x10FE_save_game.md`, with helper roles cross-checked against `u5-decomp/functions/FONT_OVL/0x0B0A_chargen_main.md`.

- Load flow — byte-image read, empty-save guard, dual-half `SAVED.OOL` read, unconditional mirror-write of both per-plane seed files, underworld disk-swap loop, and final commit — derived from `u5-decomp/functions/INTRO_OVL/0x0EB4_load_saved_game.md`.

- U4-Transfer companion path and character-roster preview — derived from `u5-decomp/functions/INTRO_OVL/0x132A_continue_load.md`.

- Read-and-write retry wrapper, disk-prompt contract, wait-cursor phase signalling — derived from `u5-decomp/functions/ULTIMA_EXE/0x82DE_load_lzw_image.md`.

- Inner read primitive — open, optional absolute seek, zero-count default, byte-count result, zero-on-error retry signal, ignored close-time failure, and nonzero short-read edge — derived from `u5-decomp/functions/ULTIMA_EXE/0x7234_read_file_seek.md`.

- Inner write primitive — create-or-truncate, write, close, byte-count result, zero-on-error retry signal, ignored close-time failure, and nonzero short-write edge — derived from `u5-decomp/functions/ULTIMA_EXE/0xF0C6_write_file.md`.

- Save-image layout, `SAVED.OOL` split, the `BRIT.OOL` / `UNDER.OOL` / `INIT.OOL` / `INIT.GAM` family, and the object-record structure — derived from `u5-decomp/formats/saves.md`.
