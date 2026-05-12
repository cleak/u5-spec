# Display Driver ABI

## 1. Scope

This document specifies the public, cleanroom contract for the IBM PC display
driver interface used by the DOS version of Ultima V, with the EGA driver as
the binary-compatibility baseline. It complements `display-driver.md`, which
describes the renderer at a semantic level.

The ABI described here is enough for a compatible engine, loader, or test
harness to reproduce the original driver-facing behaviour without copying the
driver code. It intentionally omits decompiled source, assembly, private target
addresses inside the driver body, and raw binary data.

## 2. Driver Loading And Dispatch

The selected `*.DRV` file is loaded as a raw 16-bit code overlay rather than as
an MZ executable. Startup selects one of the driver filenames from the
resident driver-name table, loads it into a segment, and stores that segment in
the resident driver-dispatch cell.

There is one driver-dispatch far pointer:

| Half | Ownership | Behaviour |
|---|---|---|
| Offset | Patched before each driver call | The caller writes a byte offset into the driver's jump table. |
| Segment | Patched once after driver load | The loader writes the selected driver's load segment. |

The dispatch offset is not a C function pointer and not an array index. It is a
byte offset into a table of three-byte near-jump cells at the beginning of the
driver. Therefore:

| Quantity | Rule |
|---|---|
| Slot number | `dispatch_offset / 3` |
| Dispatch offset | `slot_number * 3` |
| Valid offsets | Multiples of 3 only |

Callers preserve their own data segment around driver calls because driver
entries may change segment registers. Arguments are passed in registers or in
driver-resident state, not through a public stack frame.

The separate resident far pointer used by the screen-mode handler is not a
driver dispatch cell. It points back into the resident executable and should
not be treated as part of the `*.DRV` ABI.

## 3. EGA Baseline Mode

The EGA-compatible baseline uses the IBM EGA 320-by-200, 16-colour planar
graphics mode.

| Property | Contract |
|---|---|
| Visible size | 320 pixels wide by 200 pixels high |
| Pixel coordinate range | X `0..319`, Y `0..199` |
| Scanline byte stride | 40 bytes per plane |
| Colour value | 4-bit value `0..15` |
| Colour-plane bits | Bit 0 plane 0, bit 1 plane 1, bit 2 plane 2, bit 3 plane 3 |
| Front buffer | Hardware-visible EGA framebuffer |
| Back buffer | Driver-managed EGA-page memory used for full-screen and transition effects |

The driver back buffer is EGA page memory organised as four sequential
8,000-byte plane images: one full 320-by-200 plane slice for each of the four
colour bits. It is not laid out like an interleaved chunky image. Entries that
copy between the back buffer and the front buffer select and transfer the
corresponding plane slices.

The back buffer is not a general double buffer for world tiles or text cells.
The original driver renders ordinary viewport tiles and fixed-cell text to the
front buffer. Back-buffer use is limited to whole-screen or effect-oriented
paths such as compressed bitmap staging, silhouette stamping, screen dissolves,
and title/menu animation.

## 4. Screen Descriptor State

One driver entry receives a pointer to the resident screen descriptor and
caches it for later entries. The EGA driver reads at least these semantic
fields:

| Field | Meaning |
|---|---|
| Clip minimum | Minimum visible coordinate used by generic clipped draw paths. |
| Clip maximum | Maximum visible coordinate used by generic clipped draw paths. |
| Render target selector | `0` selects the front buffer; `1` selects the driver back buffer for entries that support it. |
| Palette table | Sixteen display palette entries loaded during mode setup. |

The full resident descriptor layout belongs to `formats/data-ovl.md`. A
cleanroom implementation should expose the semantic fields above rather than
reproducing the original memory layout unless it is intentionally loading the
original drivers.

## 5. Dispatch Slot Inventory

The EGA jump table has 38 slots. The table below gives the public dispatch
surface by slot and byte offset. Entries marked no-op deliberately return
without visible effect.

| Offset | Slot | Public operation |
|---:|---:|---|
| `0x00` | 0 | Return the screen height constant, 200. |
| `0x03` | 1 | Enter graphics mode and cache the screen descriptor. |
| `0x06` | 2 | Initialise the driver back buffer and return its segment. |
| `0x09` | 3 | No-op. |
| `0x0C` | 4 | Release or deactivate the back buffer. |
| `0x0F` | 5 | Set the descriptor render-target selector. |
| `0x12` | 6 | No-op. |
| `0x15` | 7 | No-op. |
| `0x18` | 8 | Prepare back-buffer segment state for resident helper paths. |
| `0x1B` | 9 | Back-buffer or presentation state helper; exact visible role is not yet load-bearing. |
| `0x1E` | 10 | Full-screen back-buffer/front-buffer transfer helper. |
| `0x21` | 11 | No-op. |
| `0x24` | 12 | Read one pixel and return its 4-bit colour. |
| `0x27` | 13 | Scroll the screen/text region upward by one 8-pixel text row. |
| `0x2A` | 14 | No-op. |
| `0x2D` | 15 | Set the current 4-bit drawing colour. |
| `0x30` | 16 | Plot one pixel. |
| `0x33` | 17 | Draw a line. |
| `0x36` | 18 | No-op. |
| `0x39` | 19 | Fill a horizontal span into the back-buffer path. |
| `0x3C` | 20 | Fill a rectangle through the older rectangle path. |
| `0x3F` | 21 | Fill a clipped rectangle with the current colour. |
| `0x42` | 22 | Decode and draw a driver-compressed bitmap/font-strip resource. |
| `0x45` | 23 | No-op. |
| `0x48` | 24 | Pack or transfer screen data into the back-buffer representation. |
| `0x4B` | 25 | General tile or sprite blit. |
| `0x4E` | 26 | Stamp a one-bit silhouette sprite into the back buffer. |
| `0x51` | 27 | Draw one 16-by-16 tile directly to the front buffer. |
| `0x54` | 28 | No-op. |
| `0x57` | 29 | No-op. |
| `0x5A` | 30 | Release the current asset segment. |
| `0x5D` | 31 | Draw one 8-by-8 fixed-cell glyph directly to the front buffer. |
| `0x60` | 32 | Mutate loaded tile graphics for animated shimmer effects. |
| `0x63` | 33 | General tile blit with an additional flag set. |
| `0x66` | 34 | Copy a rectangle from back buffer to front buffer in pseudo-random dissolve order. |
| `0x69` | 35 | Advance and draw the title/menu flame-style animation strip. |
| `0x6C` | 36 | Save/restore or swap tile palette/graphics state for animated terrain effects. |
| `0x6F` | 37 | CPU-calibrated delay with byte-stream animation playback. |

The most important correction from the full driver pass is that dispatch
offset `0x3F` is the filled-rectangle entry, not the compressed-bitmap entry.
The compressed bitmap/font-strip decoder is dispatch offset `0x42`.

## 6. Rectangle Fill

The rectangle-fill entry receives an inclusive pixel rectangle that has already
been normalised and clamped by the resident caller. Its visible contract is:

1. Fill every pixel in the inclusive rectangle.
2. Use the current 4-bit drawing colour set by the colour entry.
3. Preserve pixels outside the rectangle, including sub-byte pixels to the left
   and right of non-byte-aligned edges.
4. Treat the EGA baseline as 40 bytes per scanline per plane.

The original EGA implementation achieves sub-byte edges with plane masks and
latch-modify-write behaviour. A modern renderer only needs to preserve the
resulting pixels.

## 7. Driver-Compressed Bitmap Resources

Dispatch offset `0x42` consumes a loaded bitmap/font resource segment. This
format is used by `TITLE.BIT`, `BRITISH.BIT`, `WD.BIT`, and `PROPORT.PCS`; it
is not the shared LZW envelope used by the paired `.16`/`.4` graphics files.

The resource begins with a sparse pointer table:

| Field | Width | Meaning |
|---|---:|---|
| Entry count | 2 bytes | Number of pointer-table entries to scan. |
| Pointer-table entries | 4 bytes each | A body pointer word followed by one metadata word. |

For each entry, a zero pointer means "skip". A nonzero pointer is a byte offset
within the same loaded resource segment. The metadata word is not consumed as
part of the pointer-table scan. If a pointer targets that byte range, as in a
compact single-strip resource, the strip decoder simply treats the pointed
bytes as the strip body.

Each pointed-to strip has this shape:

| Field | Width | Meaning |
|---|---:|---|
| Width-related word | 2 bytes | Converted by the driver into the packed bytes-per-row value. |
| Row count | 2 bytes | Number of rows in the strip. |
| Pixel payload | variable | Packed 4-bit source data in byte-interleaved plane order for the strip. |

For the EGA baseline, the strip decoder rounds the packed bytes-per-row up to a
multiple of four, converts the strip data into planar form, and emits it to the
active driver destination. The exact source-to-screen placement is owned by
the caller's current draw state and the resource's strip ordering; callers do
not use the `.16`/`.4` LZW archive container for these files.

Compatibility requirements:

- Read the entry count as a count, not as a decoded-length field.
- Process pointer entries in order.
- Skip zero pointers.
- Treat nonzero pointers as byte offsets inside the loaded resource image.
- Treat the second word in each pointer-table entry as table metadata unless a
  strip pointer explicitly targets it.
- Stop each strip after its declared row count.
- Do not reject a resource solely because the entry count is much larger than
  the number of populated strips. Known resources rely on long runs of zero
  pointer entries, and original heap-load semantics can leave zero-filled space
  beyond the byte-exact file image for over-allocated tables.

## 8. Tile And Glyph Rendering

The 16-by-16 tile entry is the front-buffer viewport workhorse. It accepts only
16-pixel width and 16-pixel height requests; other sizes are ignored by this
entry and belong to the general blitter. If the current render-target selector
names the back buffer, the EGA tile entry returns without drawing; there is no
separate back-buffer tile path. Each tile consumes 128 bytes in the EGA asset
segment:

| Component | Size |
|---|---:|
| Rows | 16 |
| Bytes per row | 8 |
| Total per tile | 128 bytes |

Within each row, source bytes are grouped by four EGA planes for the first
eight pixels and then the second eight pixels. This is the driver-facing
layout produced from the `.16` tile assets before drawing. The public
file-format layout remains the chunky packed-nibble layout in
`formats/tiles.md`.

The fixed-cell glyph entry draws one 8-by-8 glyph to the front buffer. The
source glyph is eight bytes, one byte per row, with the most-significant bit as
the leftmost pixel. The caller supplies foreground and background colours
through the text renderer's attribute path. The resulting cell must contain
the foreground colour where the glyph bit is set and the background colour
where it is clear. As with the tile entry, selecting the back buffer makes this
entry a no-op in the EGA baseline; ordinary fixed-cell text is drawn directly
to the visible page.

Neither the 16-by-16 tile entry nor the fixed-cell glyph entry is used for
ordinary back-buffer updates in the EGA baseline.

## 9. Transitions And Animation Entries

The EGA driver owns several visual effects that are not gameplay systems:

- Title/menu idle animation: a four-frame driver-local strip drawn at
  `(0, 65)` with size `320 x 49`, advanced by dispatch offset `0x69`.
- Rectangle dissolve: copies pixels from the back buffer to the front buffer
  in pseudo-random order until the rectangle matches. The EGA implementation
  uses a deterministic LFSR-style visit order; after the entry completes, the
  destination rectangle's front-buffer pixels match the back buffer.
- Animated tile shimmer: mutates selected loaded tile graphics entries, not
  framebuffer pixels. The effect becomes visible when the normal viewport path
  later redraws those tiles.
- Credits/death animation delay: uses a calibrated delay value and byte-stream
  animation playback so the effect runs at a stable apparent speed on different
  CPUs.

These effects do not advance saved-game time, NPC schedules, combat rounds, or
active-object simulation.

## 10. Open Parity Gaps

- The exact meanings of some non-load-bearing helper slots remain below the
  current public spec because no gameplay or asset format depends on them yet.
- CGA, Hercules, and Tandy implement the same broad ABI with different pixel
  encodings and hardware details; their exact conversion rules remain separate
  historical-hardware parity work.
- The driver-compressed bitmap metadata word is not consumed by the EGA decode
  path. If another driver uses it for placement or palette selection, that is
  an alternate-driver compatibility detail.

## 11. Sources

Cleanroom prose derived from these private analysis notes:

- `u5-decomp/formats/ega-driver.md`.
- `u5-decomp/functions/EGA_DRV/_OVERVIEW.md`.
- `u5-decomp/functions/EGA_DRV/0x1180_fill_rect_v2.md`.
- `u5-decomp/functions/EGA_DRV/0x1226_draw_compressed_bitmap.md`.
- `u5-decomp/functions/EGA_DRV/0x1637_tile_blit_16x16.md`.
- `u5-decomp/functions/EGA_DRV/0x19D2_glyph_8x8.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
