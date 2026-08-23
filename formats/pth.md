# PTH files

Format specification for `BRITISH.PTH`, the only `.PTH` file shipped with Ultima V. It is a 2,783-byte stream of nibble-encoded pen movement deltas used by the title-screen "Lord British" signature animation. It is not a waypoint list and it is not related to NPC schedules.

## 1. Overview

The file's role is cosmetic. The intro loads it during the title sequence, walks it while the player watches the signature draw itself, and never consults it again. Nothing in the simulation, gameplay loops, or save image references the path data.

Although the `.PTH` extension sounds generic, no other `.PTH` file ships in the analyzed DOS baseline. NPC routes use the fixed-stride records in the four `.NPC` files, not this delta stream.

The file is a flat byte stream with no header, magic number, version word, length prefix, offset table, embedded text, or padding. Every byte is part of the stream. The only structural markers are four zero bytes: three internal segment terminators plus one terminator at end of file.

## 2. File-Level Layout

The whole file is:

```text
stream[2783]    NUL-segmented pen-delta byte stream
```

The walker consumes bytes from offset zero until it reaches a zero byte. Each call consumes one segment. The intro calls the walker four times, once per segment, with a different starting pen origin for each call.

The four zero bytes are at file offsets `856`, `1405`, `1817`, and `2782`. They divide the file into four non-empty segments:

| Segment | Byte range | Length |
|---:|---|---:|
| 1 | `0..855` | 856 bytes |
| 2 | `857..1404` | 548 bytes |
| 3 | `1406..1816` | 411 bytes |
| 4 | `1818..2781` | 964 bytes |

The final zero byte is the final byte of the file. A reader that has the file size should stop at end of file after the fourth terminator. A reader that only has a stream can treat the fourth terminator as the natural end for the shipped file.

## 3. Per-Byte Encoding

Each non-zero byte is split into two four-bit nibbles:

| Bits | Nibble | Role |
|---:|---|---|
| `7..4` | High | Horizontal movement delta. |
| `3..0` | Low | Vertical movement delta. |

Each nibble uses one sign bit and three magnitude bits:

| Nibble bit | Meaning |
|---:|---|
| `3` | Sign: clear for positive, set for negative. |
| `2..0` | Magnitude, unsigned range `0..7`. |

For a byte `b`:

- Horizontal magnitude is `(b >> 4) & 7`; horizontal sign is bit `7`.
- Vertical magnitude is `b & 7`; vertical sign is bit `3`.
- Positive X moves right. Positive Y moves down.
- The largest per-axis movement encoded by one byte is seven pixels.

The shipped stream is dominated by one-pixel and zero-pixel nibble movements, with occasional larger skip movements.

## 4. Segment Terminators

The byte value `0x00` is not processed as a `(0, 0)` delta. It terminates the current segment and returns control to the intro. The next intro call resumes at the following byte with a fresh pen origin.

No other byte terminates a segment. Because both nibbles being zero implies the whole byte is zero, `0x00` is unambiguous.

The four segment boundaries are part of the animation contract. They allow the intro to draw the signature in four stroke groups from four different origins.

## 5. Pen-Up Signalling

For each non-zero byte, the walker first decodes the movement delta, then decides whether the new pen position should be painted.

The pen-state rule is:

| Nibble magnitudes in the byte | Action |
|---|---|
| Both magnitudes `0..2` | Pen down: advance and paint at the new position. |
| Either magnitude `3..7` | Pen up for this byte: advance but do not paint. |

Equivalently, the byte is a pen-up move when the larger of its two nibble magnitudes is greater than two. This is not a sticky state. The next byte returns to pen-down behaviour if both of its nibble magnitudes are two or smaller.

Pen-up bytes encode short skips inside one segment. NUL terminators encode major segment breaks and return to the caller for a new origin.

## 6. Synthetic Decoding Example

This synthetic example illustrates the byte interpretation without reproducing original file-byte values from `BRITISH.PTH`.

| Byte meaning | High nibble | Low nibble | Pen action |
|---|---|---|---|
| Small positive X step | Magnitude one, positive sign | Magnitude zero | Move one pixel right and paint. |
| Small positive Y step | Magnitude zero | Magnitude one, positive sign | Move one pixel down and paint. |
| Small negative X step | Magnitude one, negative sign | Magnitude zero | Move one pixel left and paint. |
| Large X skip | Magnitude greater than two | Magnitude zero | Move without painting. |

A decoder can sanity-check itself by confirming that bytes whose two magnitudes are both `0..2` paint, while any byte with either magnitude `3..7` moves without painting.

## 7. Consumer

The file has a single consumer: the intro path walker. The intro loads the complete file into a scratch buffer and invokes the walker four times.

The four title-screen origins, in segment order, are:

| Segment | X | Y |
|---:|---:|---:|
| 1 | 68 | 44 |
| 2 | 94 | 64 |
| 3 | 78 | 143 |
| 4 | 105 | 167 |

Each call consumes one segment, drawing one stroke group from the supplied origin. The walker polls the keyboard between steps. Any key press aborts the remaining signature animation and lets the intro continue without waiting for all four segments to finish.

The intro system spec owns the title-screen orchestration and early-skip behaviour. This format spec owns only the stream layout and decode rule.

## 8. Cross-References

- `systems/intro.md` describes the title sequence that loads and walks `BRITISH.PTH`.
- `systems/display-driver.md` describes the display contract used to paint the signature pixels.
- `formats/npc.md` describes the unrelated NPC schedule records that should not be confused with `.PTH`.
- `formats/saved-gam.md` confirms the save image does not reference this title-only asset.

## 9. Limits and Non-Format Notes

The byte-format contract is closed for the analyzed DOS baseline: file size, segmentation, nibble signs, nibble magnitudes, pen-up threshold, consumer, and four origins are specified.

These points are intentionally outside the format contract:

- **Segment-to-letter mapping.** The four segments likely align with major pen-lift groups in the visual signature, but a renderer only needs to consume the four segments in order from the four specified origins.
- **Other `.PTH` files.** No other `.PTH` file ships in the analyzed baseline, and no traced system consumes one. The format is specified as a one-shot title asset.
- **Visual interpretation of pen-up skips.** Pen-up bytes and NUL terminators both lift the pen, but they have different mechanics. Pen-up continues inside the current segment; a NUL returns to the caller for a fresh origin.

## 10. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, implementation-specific identifiers, source code, disassembly, or original path bytes from those notes appear in this spec.

- The first-pass survey of `BRITISH.PTH`, the nibble-histogram observation, and the discovery of exactly four NUL bytes at internal offsets and end-of-file - `u5-decomp/formats/npc-tlk-pth.md`.
- The path walker's behavioural analysis - nibble decode, sign-and-magnitude split, pen-up threshold, keyboard early-exit, sole consumer, and four call-site origins - `u5-decomp/functions/INTRO_OVL/`.
- The intro title-screen orchestration that supplies the four origins and calls the walker once per segment - `u5-decomp/functions/INTRO_OVL/`.
- Fresh local title-sequence verification identified the four screen-space pen origins; no original path bytes or implementation excerpts are reproduced here.
