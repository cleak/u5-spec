# PTH files

Format specification for `BRITISH.PTH`, the only `.PTH` file shipped with Ultima V. It is a 2,783-byte byte stream of nibble-encoded movement deltas that drives the title-screen "Lord British" calligraphic-signature animation. The file is a stream of pen movements rather than a list of waypoints or coordinates: each byte advances a pen position by a small vector and (optionally) sets a pixel at the new position, building the cursive "Lord British" inscription one tiny stroke at a time.

## 1. Overview

The file's role is purely cosmetic. It is read once per game session — during the title sequence — by the introduction overlay, walked end-to-end while the player watches the signature draw itself, and never consulted again. Nothing in the simulation, the gameplay loops, or the save image references the path data; the file's contents have no effect on play.

Although the `.PTH` extension suggests a generic "path" format that might also describe NPC schedules or quest routes, no other `.PTH` file ships in the game directory. The four NPC-class roster files (`*.NPC`) carry their own per-NPC schedule encoding (see `formats/npc.md`); they do not share the byte stream layout described here. `BRITISH.PTH` is a one-off used only for the title-screen flourish.

The file is a flat byte stream with no header, no magic number, no version word, no length prefix, no offset table, and no embedded text. There is also no padding: every byte is consumed by the walker. The file's only structural feature beyond the per-byte delta encoding is segmentation by NUL bytes — three mid-file NUL terminators plus one at the file end split the stream into four contiguous "stroke" segments, each rendered from a different starting screen position.

A reader writing a `.PTH` decoder works at the level of "which nibble of which byte does what to the pen", and that is the entire format. There is no out-of-line storage, no escape sequence, and no mode change beyond what the byte values themselves trigger.

## 2. File-level layout

The file is a contiguous run of two thousand seven hundred eighty-three bytes:

```
.PTH file:
  uint8 stream[2783]    // pen-delta byte stream, NUL-segmented
```

There is no per-file header. The walker reads the file's bytes from offset zero up through the final byte, treating each non-zero byte as a delta-pair and each zero byte as a segment terminator. The stream contains exactly four NUL bytes, three at internal offsets and one as the final byte of the file, dividing the run into four segments.

The file's size is not encoded inside the file. The walker tracks how many bytes it has consumed against a fixed buffer-size constant (about four kilobytes in the engine's working buffer; the file is shorter than the buffer and ends before the buffer does). A reader that does not have an out-of-band file size can detect end of stream by reaching the fourth NUL byte (Section 4).

## 3. Per-byte encoding

Each byte in the stream is split into two four-bit nibbles:

| Bit position | Nibble | Role                                          |
|--------------|--------|-----------------------------------------------|
| `7..4`       | High   | Horizontal motion delta for the pen.          |
| `3..0`       | Low    | Vertical motion delta for the pen.            |

The two nibbles are decoded independently using the same scheme. Each nibble splits further into a sign bit and a three-bit magnitude:

| Bit position within nibble | Field      | Meaning                                                          |
|----------------------------|------------|------------------------------------------------------------------|
| Bit 3 (`0x8`)              | Sign       | `0` for positive, `1` for negative.                              |
| Bits 2..0 (`0x0..0x7`)     | Magnitude  | Unsigned three-bit count of pixels to advance along this axis.   |

Concretely, given a byte `b`:

- Horizontal nibble: `hi = (b >> 4) & 0x0F`. Magnitude `mh = hi & 0x07`. Sign-aware delta `dx = (hi & 0x08) ? -mh : +mh`.
- Vertical nibble: `lo = b & 0x0F`. Magnitude `mv = lo & 0x07`. Sign-aware delta `dy = (lo & 0x08) ? -mv : +mv`.

The pen's screen position advances by `(dx, dy)` for each byte processed. The convention is screen-space: positive `dx` moves the pen rightward, positive `dy` moves the pen downward (toward the bottom of the screen), which means the sign bit being clear corresponds to "right" or "down" and being set corresponds to "left" or "up".

The maximum per-axis delta is therefore `±7` pixels per byte. In practice the shipped file uses much smaller deltas: a histogram of the nibble values shows `0` and `1` together accounting for over four thousand of the file's roughly five thousand five hundred nibbles, with `9` (which is `1` with the sign bit set, i.e. a delta of `-1`) the next most common. The file is dominated by single-pixel steps in any of four diagonal-or-cardinal directions, with a small admixture of larger jumps.

## 4. Segmentation

Four NUL bytes (`0x00`) appear in the stream. They sit at file offsets `856`, `1405`, `1817`, and `2782`. The fourth NUL is the file's last byte; the first three are internal segment terminators. The four NULs partition the stream into four contiguous segments:

| Segment | Byte range (inclusive) | Length    |
|---------|------------------------|-----------|
| 1       | `0..855`               | 856 bytes |
| 2       | `857..1404`            | 548 bytes |
| 3       | `1406..1816`           | 411 bytes |
| 4       | `1818..2781`           | 964 bytes |

A NUL byte's encoding under the per-byte rule of Section 3 is degenerate: both nibbles are zero, so the per-byte delta is `(0, 0)` — neither axis advances. The walker treats a NUL byte specially: rather than processing it as a no-op delta, it interprets the NUL as an end-of-segment marker, halts processing of the current segment, and returns to its caller. The caller resumes walking with the next segment when it next invokes the walker, supplying a fresh pen origin (Section 6).

A byte whose two nibbles are individually zero but which is not the byte value `0x00` cannot exist — both nibbles being zero implies the whole byte is zero. A `0x00` byte is therefore unambiguously a segment terminator and is never consumed as a delta-pair. Conversely, no other byte value triggers segment termination.

The four-segment structure is the file's only non-flat structural feature. It is plausibly aligned with the four major letter-groups of "Lord British" (the four words "Lord" and "British" if one counts a stylised flourish, or the four pen-lift boundaries in a calligraphic ductus), but the title-screen rendering is fast enough to make a precise letter-to-segment mapping a matter of inspection rather than format spec. See Section 9.

## 5. Pen-up signalling

A second mechanism modulates the per-byte delta: when a nibble's magnitude exceeds two, the byte is treated as a pen-up move. The walker advances the pen position by the decoded `(dx, dy)` as usual, but suppresses the pixel-set at the new position. The next byte resumes ordinary pen-down behaviour unless it, too, has a magnitude greater than two.

Concretely, the pen-state rule is:

- Magnitude `0..2` on either axis: pen-down step. The walker paints a pixel at the new position before continuing.
- Magnitude `3..7` on either axis: pen-up step. The walker advances the pen but does not paint.

The check is independent per byte: a magnitude-five byte does not set a sticky pen-up flag, only a per-byte one. The next byte (assuming both its nibble magnitudes are two or smaller) returns the pen to drawing.

The pen-up rule lets the file encode visible discontinuities — one part of the signature ends and another begins, so the pen lifts and moves to the new origin without leaving a trail. Without it, the only way to lift the pen would be to terminate a segment (Section 4), which would commit the walker to a fresh origin from the caller. Pen-up bytes are the format's way of saying "skip this short distance without drawing", typically used for the inter-letter gaps within one segment.

The threshold `> 2` (rather than `> 1` or `> 3`) is verified empirically against the walker's disassembly. Implementations should use the same cutoff to reproduce the original animation faithfully.

## 6. Worked example — the file's first sixteen bytes

The first sixteen bytes of `BRITISH.PTH` are `10 10 01 10 10 01 90 10 …`. Decoded byte-by-byte:

| Byte  | Hex   | High nibble (dx)              | Low nibble (dy)              | Pen action       |
|-------|-------|-------------------------------|------------------------------|------------------|
| 0     | `10`  | `1` → `+1`                    | `0` → `0`                    | Down: paint at `(x+1, y)` |
| 1     | `10`  | `1` → `+1`                    | `0` → `0`                    | Down: paint at `(x+2, y)` |
| 2     | `01`  | `0` → `0`                     | `1` → `+1`                   | Down: paint at `(x+2, y+1)` |
| 3     | `10`  | `1` → `+1`                    | `0` → `0`                    | Down: paint at `(x+3, y+1)` |
| 4     | `10`  | `1` → `+1`                    | `0` → `0`                    | Down: paint at `(x+4, y+1)` |
| 5     | `01`  | `0` → `0`                     | `1` → `+1`                   | Down: paint at `(x+4, y+2)` |
| 6     | `90`  | `9` → `-1` (sign bit + mag 1) | `0` → `0`                    | Down: paint at `(x+3, y+2)` |
| 7     | `10`  | `1` → `+1`                    | `0` → `0`                    | Down: paint at `(x+4, y+2)` |

All eight bytes have nibble magnitudes of at most one, so the pen stays down throughout and the walker paints a pixel on every step. The trace describes a small zigzag — two rightward steps, a step down, two more rightward, another step down, a leftward step, then another rightward — which is the start of one of the cursive strokes on the title screen.

A reader can sanity-check a decoder by reproducing this trace against the file's first sixteen bytes and confirming that no NUL appears in that span, that the running pen position matches the table above, and that the pen never lifts (no nibble magnitude exceeds two).

## 7. Consumer

The file has a single consumer: the introduction overlay's path-walker, invoked four times during the title sequence — once per segment — to draw the four pieces of the signature at four different starting screen positions. The walker reads the file from a four-kilobyte buffer that holds the entire file (plus trailing zeros into the buffer's tail), maintains a rolling byte index, and advances through the stream until it hits a NUL terminator. Each call to the walker consumes one segment.

The four starting positions are baked into the introduction overlay as constants — one `(x, y)` pair per call site. Concretely the four origins are at title-screen coordinates roughly corresponding to the four corners of the inscribed phrase, with each segment laying down one stroke or letter group from its starting origin outward. The walker also polls the keyboard between bytes and aborts the animation if the player presses any key, so the introduction can be skipped without waiting for all four segments to complete.

The walker's full behaviour — its cooperation with the per-driver paint primitive, its keyboard-poll cadence, its interaction with the title-screen palette, and its exit-on-keypress contract — is described under `systems/intro.md`. From the format's perspective, the only contract that matters is that a segment ends at the first NUL byte after a fresh origin and that the four segments collectively consume the entire file.

## 8. Cross-references

- The introduction sequence and its title-screen orchestration — `systems/intro.md`.
- The display drivers that the walker calls to paint each pixel — `drivers/display.md`.
- The per-driver palette and mode setup that gates whether pixels are emitted at all — `systems/text-output.md`.
- The other "path"-themed format in the game (the per-NPC schedule waypoints inside the four `.NPC` files) — `formats/npc.md`. The two formats share only their extension family; the NPC schedule format is a fixed-stride waypoint record, not a delta stream.
- The save image, which does not reference `BRITISH.PTH` directly — `formats/saved-gam.md`. The signature animation runs once per game launch, not per save load.

## 9. Open questions

The format is verified by direct byte inspection at the file-structure level (the four-NUL segmentation, the file size, the dominance of small-magnitude nibbles in the histogram) and by behavioural inspection at the walker level (the per-byte nibble decode, the sign-and-magnitude split, the `> 2` pen-up threshold). The following points remain open.

- **Exact pen-up threshold rule.** The walker's disassembly shows the cutoff as "magnitude greater than two", consistent across both nibbles of a byte. Whether the rule is "either nibble magnitude > 2 ⇒ pen-up" or "the maximum of the two nibble magnitudes > 2 ⇒ pen-up" produces identical observable behaviour for the encoded file (no nibble within an otherwise-pen-down byte exceeds two), so the two readings are not distinguishable from the data alone. The walker's flow has the per-nibble check applied independently, with the pen-up state being write-once per byte, which suggests "either nibble triggers pen-up for this byte" is the operative semantics. An implementation that treats it as a logical-OR across nibbles is safe.

- **Segment-to-letter mapping.** The four segments of the file are presumably aligned with four pen-lift boundaries in the calligraphic rendering of "Lord British" — possibly the spaces between word groups, possibly the boundaries between major loops in the cursive script. Mapping each segment to the letter group it draws would require playback against the title screen with the pen position annotated. The format spec does not constrain the mapping; any segmentation that draws the same pixels in the same screen positions is equivalent.

- **Existence of `.PTH` files beyond `BRITISH.PTH`.** No other `.PTH` file ships with the game. The walker's invocation site is the introduction overlay; no other overlay or system reads the file, and no external reference attests another `.PTH`. The format is therefore a one-shot, despite the generic-sounding extension. Whether the original developers contemplated a broader use is not known.

- **Pen-up versus segment-break distinction.** Both pen-up bytes (Section 5) and NUL segment terminators (Section 4) lift the pen, but they differ in whether the walker continues internally (pen-up) or returns to the caller for a fresh origin (segment-break). The encoded file uses both mechanisms. Whether they correspond to qualitatively different visual events — a small inter-letter gap versus a major stroke restart — is consistent with the four-segment-as-major-stroke reading but not directly verifiable from the format alone.

- **Title-screen origin coordinates.** The four `(x, y)` origins for the four segments are baked into the introduction overlay rather than into the file. An implementation reproducing the title screen needs the origin coordinates as a sibling input; they are not part of the `.PTH` format and are documented under `systems/intro.md`.

## 10. Sources

The format described above was derived from the analysis notes listed below. None of the byte offsets, function addresses, or implementation-specific identifiers from those notes appear in this spec; the spec is a re-derivation from observed file structure and observed runtime behaviour.

- The first-pass survey of `BRITISH.PTH`, the nibble-histogram observation, the discovery of exactly four NUL bytes at internal offsets and end-of-file, and the conjectural mapping to four-stroke segmentation — `u5-decomp/formats/npc-tlk-pth.md`.
- The path walker's full disassembly — the per-byte nibble decode, the sign-and-magnitude split, the `> 2` pen-up threshold, the keyboard-poll early-exit contract, the sole-caller analysis showing four invocation sites with four distinct starting origins, and the resolution of the "consumer is INTRO.OVL" open question — `u5-decomp/functions/INTRO_OVL/0x0050_pth_walker.md`.
- The introduction overlay's title-screen orchestration, which supplies the four origin coordinates and drives the walker once per segment — `u5-decomp/functions/INTRO_OVL/` (the introduction-overlay function notes).
