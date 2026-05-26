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
an MZ executable. Boot startup selects one of the driver filenames from the
resident driver-name table, loads it into a segment, and stores that segment in
the resident driver-dispatch cell. Hardware detection and command-line
reconciliation are specified in `boot.md`; this document starts at the
driver-facing ABI.

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
not be treated as part of the `*.DRV` ABI. Its public behaviour is specified in
`screen-mode-dispatch.md`.

## 3. EGA Baseline Mode

The EGA-compatible baseline uses the IBM EGA 320-by-200, 16-colour planar
graphics mode. The mode is shared by VGA-compatible adapters at the firmware
level, so there is no separate VGA driver and no separate VGA code path; VGA
hosts run this same driver in this same mode. The mode-initialisation
sequence, the planar buffer layout, the back-buffer four-plane arrangement,
and the palette mechanics are specified in
[`display-driver-mode.md`](display-driver-mode.md); the table below summarises
the dispatch-facing properties only.

| Property | Contract |
|---|---|
| Visible size | 320 pixels wide by 200 pixels high |
| Pixel coordinate range | X `0..319`, Y `0..199` |
| Scanline byte stride | 40 bytes per plane |
| Colour value | 4-bit value `0..15` |
| Colour-plane bits | Bit 0 plane 0, bit 1 plane 1, bit 2 plane 2, bit 3 plane 3 |
| Front buffer | Hardware-visible EGA framebuffer |
| Back buffer | Driver-managed EGA-page memory used for full-screen and transition effects |

During EGA mode setup the driver selects the hardware-visible page zero. The
later back-buffer paths do not implement ordinary hardware page flipping for
world or text updates. They copy or dissolve pixels from driver-managed page
memory into the visible front buffer when a full-screen or transition effect
requires it.

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
| `0x18` | 8 | Carry-flag-gated dispatcher to whole-screen plane-copy helpers. Under the resident core's `clc`-bracketed dispatch convention this entry is effectively a no-op; older calling conventions could set carry to request a flush. |
| `0x1B` | 9 | Two-direction full-screen plane copy used by back-buffer-touching paths to refresh or seed the alternate buffer. |
| `0x1E` | 10 | Full-screen front-buffer and back-buffer in-place swap, row by row, using a driver-internal scanline scratch. This is a swap, not a one-way transfer. |
| `0x21` | 11 | No-op. |
| `0x24` | 12 | Read one pixel and return its 4-bit colour. |
| `0x27` | 13 | Scroll the right-side text panel upward by exactly eight scanlines. See section 9.5 for the precise region and exposed-band policy. |
| `0x2A` | 14 | No-op. |
| `0x2D` | 15 | Set the current 4-bit drawing colour. |
| `0x30` | 16 | Plot one pixel. The back-buffer override path silently no-ops, so this is effectively a front-buffer operation. |
| `0x33` | 17 | Draw an arbitrary-direction integer line between two pixel endpoints. |
| `0x36` | 18 | No-op. |
| `0x39` | 19 | Fill a single horizontal scanline in either buffer. The row coordinate is the entry's Y argument; there is no row loop. |
| `0x3C` | 20 | Fill a rectangle in either buffer using the earlier-generation rectangle helper. |
| `0x3F` | 21 | Fill a clipped rectangle with the current colour. Front-buffer only; back-buffer fills go through dispatch offset `0x39` or `0x3C`. |
| `0x42` | 22 | Decode and draw a driver-compressed bitmap/font-strip resource. |
| `0x45` | 23 | No-op. |
| `0x48` | 24 | Register a loaded asset segment as the active tile/sprite asset and prepare it for blitting by converting its embedded pixel payload from packed to planar layout in place. Despite the historical working name "pack to back buffer", this entry does not touch the back buffer; it operates on the asset segment. |
| `0x4B` | 25 | General tile or sprite blit. Accepts a render-flags word whose low bits choose between an opaque blit and a transparency-mask blit. |
| `0x4E` | 26 | Stamp a one-bit silhouette sprite into the back buffer. |
| `0x51` | 27 | Draw one 16-by-16 tile directly to the front buffer. |
| `0x54` | 28 | No-op. |
| `0x57` | 29 | No-op. |
| `0x5A` | 30 | Release the current asset segment back to DOS. |
| `0x5D` | 31 | Draw one 8-by-8 fixed-cell glyph directly to the front buffer. |
| `0x60` | 32 | Mutate loaded tile graphics for animated shimmer effects. The mutation phase is followed by a propagation/composite phase, so the body of this entry is substantially larger than just the noise step. |
| `0x63` | 33 | Tile blit with the transparency-mask flag forced on. Equivalent to dispatch offset `0x4B` with the caller-supplied flag word bitwise-ORed with the transparency bit. |
| `0x66` | 34 | Copy a rectangle from back buffer to front buffer in pseudo-random dissolve order. The visit order is driven by a Galois-style LFSR; see section 9.6 for the public visit-order contract. |
| `0x69` | 35 | Advance and draw the title/menu flame-style animation strip. |
| `0x6C` | 36 | Loaded-tile graphics palette-plane mutation, save, restore, byte-parameterized substitution, and an extended mode reached only by alternate paths. The combat framer reaches this entry with mode value `1` when the resident tile-restoration flag is set. |
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

For the corrected EGA slot-21 path, the active rectangle loop is a front-buffer
operation. If the descriptor's render-target selector names the driver back
buffer, this entry does not perform the per-scanline fill. Back-buffer fills are
owned by the earlier horizontal-span and rectangle entries, not by dispatch
offset `0x3F`. Compatibility tests should therefore treat `0x3F` as the
clipped front-buffer rectangle fill even though the broader descriptor state has
a back-buffer selector used by other entries.

## 7. Driver-Compressed Bitmap Resources

Dispatch offset `0x42` consumes a loaded bitmap/font resource segment. This
format is used by `TITLE.BIT`, `BRITISH.BIT`, `WD.BIT`, and `PROPORT.PCS`; it
is not the shared LZW envelope used by the paired `.16`/`.4` graphics files.
This compressed-bitmap entry is implemented by the EGA baseline driver. The
corresponding CGA, Hercules, and Tandy driver entries are no-op stubs in the
analyzed baseline, so those historical backends do not draw these resources
through this codec.

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

## 9. Additional Public Entries

The earlier sections cover the main draw surface (rectangle fill, compressed
bitmap, tile, glyph). The remaining entries are documented below at the same
public-contract depth.

### 9.1 Mode And State Setup

Dispatch offset `0x03` performs the one-time graphics-mode entry. When invoked
with a non-zero primary-argument flag the entry switches the adapter to the
EGA-compatible 320-by-200, 16-colour mode, loads sixteen attribute-controller
palette entries from the resident screen descriptor's palette table, selects
hardware page zero as the visible page, and resets the sequencer plane-write
mask, the graphics-controller bit mask, and the graphics-controller function
select to their pass-through values. When invoked with a zero flag the entry
skips the BIOS mode change and the palette load but still caches the
descriptor pointer for later entries. After the first successful invocation,
the entry treats its scanline-row table and edge-mask lookup table as one-time
initialised and does not rebuild them.

Dispatch offset `0x06` reserves the driver back buffer and zeroes its contents,
then returns the back-buffer segment to the caller for later use by other
entries that need to address it. Dispatch offset `0x0C` is a release entry
with mismatched semantics relative to `0x06`; the resident core does not call
it on its main exit path, so it should be treated as historical scaffolding.

Dispatch offset `0x0F` updates the resident screen descriptor's render-target
selector. Subsequent entries that consult that selector route their output to
the front buffer when the field is zero and to the back buffer when it is
non-zero. Not every entry honours the selector; entries explicitly noted as
front-buffer-only ignore it.

Dispatch offset `0x2D` stores a 4-bit drawing colour into a driver-resident
single-byte register. Later entries that fill, plot, or rasterise without an
explicit colour argument use that register. Setting the colour does not
itself touch the framebuffer.

### 9.2 Pixel-Level Primitives

Dispatch offset `0x24` reads one pixel from the front buffer and returns the
4-bit colour value through the third register. It always reads from the
visible page and ignores the render-target selector. The colour is reassembled
by selecting each colour-plane in turn and bit-testing the relevant byte.

Dispatch offset `0x30` writes one pixel to the front buffer using the current
drawing colour. The entry has a code path that consults the render-target
selector, but the inner pixel-write helper rejects non-front-buffer segments,
so back-buffer plotting is silently a no-op. Modern implementations may
collapse the back-buffer branch and document the entry as front-buffer only.

Dispatch offset `0x33` draws an integer line between two pixel endpoints. The
implementation uses a textbook integer Bresenham step over the major axis with
plus-or-minus-one minor-axis steps, so the line includes both endpoints and
covers all eight octants. Each plotted pixel uses the same single-pixel
front-buffer writer as dispatch offset `0x30`; the entry does not optimise
horizontal or vertical lines into rectangle fills.

### 9.3 Asset Segment Lifecycle

Dispatch offset `0x48` registers a caller-supplied DOS segment as the active
asset segment and prepares it for tile and glyph blits. The entry walks the
segment's embedded pixel payload and rewrites it in place from the on-disk
chunky packed-nibble layout into the byte-interleaved planar layout that the
tile and glyph entries consume. After this entry returns successfully, the
driver-resident asset-segment pointer names the supplied segment and the
tile-blit entries can read tile data from it directly.

Dispatch offset `0x5A` releases the current asset segment back to DOS. It
issues a DOS free-block call against the driver-resident asset-segment pointer
and ignores any DOS error. The pointer is not explicitly cleared after the
call; consumers should treat the driver as having no active asset segment and
must call dispatch offset `0x48` again before the next tile blit.

A caller that wants to swap one asset segment for another therefore issues
release-then-prepare in sequence; there is no atomic replace.

### 9.4 Buffer Maintenance

Dispatch offset `0x18` is a carry-flag-gated entry that dispatches between two
internal whole-screen plane-copy helpers. The resident core's dispatch sites
clear carry before issuing the far call, so the entry as it is reached in
practice is a no-op. Modern implementations need not expose this entry at all
unless they intend to drive an alternate carry-set path that the shipped
binary does not exercise.

Dispatch offset `0x1B` performs a two-direction full-screen plane copy. It is
used after back-buffer effects to refresh or seed the alternate buffer so a
subsequent front-or-back-targeted draw observes a coherent starting image.

Dispatch offset `0x1E` is a full-screen in-place swap of the front and back
buffers, performed scanline by scanline with a driver-resident scratch row.
After this entry returns, every pixel that was on the front buffer is on the
back buffer and vice versa. The entry is not a one-way transfer; modern
implementations must preserve the swap semantics for any caller path that
relies on it. The shipped resident core does not appear to call this entry on
its mainline paths, but its presence in the dispatch table is part of the
public ABI.

### 9.5 Text Panel Scroll

Dispatch offset `0x27` is the text-panel scroll entry. It scrolls a fixed
window upward by eight scanlines:

| Property | Value |
|---|---|
| Horizontal extent | Pixel columns 192 through 319 inclusive (a 128-pixel-wide right-side text panel, 16 character cells wide). |
| Vertical extent | Pixel rows 88 through 199, advanced one row per inner iteration; iterations that reach beyond the visible 200 rows write to non-visible video memory and are harmless. |
| Scroll distance | Exactly eight scanlines upward. The distance is a driver-internal constant; any per-call distance argument is vestigial and is not honoured by the entry. |
| Exposed band | Not blanked by this entry. After the scroll, the bottom eight scanlines of the panel inherit whatever pixels happened to lie immediately below the panel before the scroll. The caller paints fresh content into the bottom row immediately after the scroll, which masks the un-blanked content. |
| Caller responsibility | Callers that need a clear bottom row must request a fill or a fresh glyph draw for those scanlines after the scroll completes. |

The entry checks that the primary register argument names the panel's left
edge before proceeding; calls with any other left-edge value return without
visible effect. This makes the entry strictly a right-side-text-panel scroll,
not a general scroll-rectangle helper. A compatible engine may either match
the hardcoded extent and exposed-band policy exactly, or expose a more general
scroll-rectangle operation and reduce it to this one when the resident core
asks for it.

### 9.6 Rectangle Dissolve Visit Order

Dispatch offset `0x66` copies pixels from the back buffer to the front buffer
in pseudo-random order until every pixel in the requested rectangle has been
copied exactly once. The original implementation uses a Galois-style LFSR
indexed by the rectangle's pixel count to select the next visited pixel; the
visible contract is:

1. Every pixel inside the inclusive rectangle is visited exactly once.
2. After the entry returns, the front buffer matches the back buffer inside
   the rectangle.
3. The visit order is deterministic and reproducible across calls with the
   same rectangle dimensions.
4. The visit order is not row-major, not column-major, and not a clean spiral;
   it should appear as scattered single-pixel updates to a viewer.

A compatible engine that wants exact frame-by-frame visual parity with the
original can reuse the original tap-set inventory, indexed by the integer
log2 of the rectangle's pixel count. The size-class taps are stored in the
driver as 16-bit Galois polynomials; the resident core's dissolve caller wraps
this entry in an outer loop that re-invokes the world tick every few visits,
so the dissolve does not freeze gameplay timing for the duration of a
full-screen transition. An engine that does not need exact frame-by-frame
parity may substitute any other order that satisfies the four bullet points
above.

## 10. Transitions And Animation Entries

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
- Loaded-tile palette-plane mutation: dispatch offset `0x6C` mutates tile
  graphics in the loaded asset segment rather than drawing directly to the
  framebuffer. Publicly confirmed modes are save-original tile bytes, restore
  saved tile bytes, a byte-parameterized mutation mode, and a batch red/green
  plane-swap mode used for combat-style terrain coloration. The combat framer's
  reached call uses mode value `1`, so it is a restoration step before ordinary
  world redraw rather than an independent presentation effect.
- Credits/death animation delay: uses a calibrated delay value and byte-stream
  animation playback so the effect runs at a stable apparent speed on different
  CPUs.

These effects do not advance saved-game time, NPC schedules, combat rounds, or
active-object simulation.

## 11. ABI Boundaries And Remaining Hardware Parity

The EGA-facing ABI contract is complete for the v1 compatibility target:
dispatch-cell loading, EGA buffer layout, rectangle fill, compressed bitmap
decode, front-buffer tile and glyph entries, title/dissolve animation entries,
the combat-exit tile-graphics restoration path, and the absence of ordinary
hardware page-flipping for world/text updates are public.

Remaining work is historical hardware and exact visual parity:

- The exact meanings of some non-load-bearing helper slots remain below the
  current public spec because no gameplay or asset format depends on them yet.
- The tile-mutator mode reached through dispatch offset `0x6C` is identified at
  public semantic depth, including the combat-exit mode-1 restore call. Exact
  alternate-mode asset byte coverage remains driver-side parity work.
- CGA, Hercules, and Tandy implement the same broad ABI with different pixel
  encodings and hardware details; their exact conversion rules remain separate
  historical-hardware parity work. The compressed-bitmap slot is already bounded
  as a no-op for those drivers.
- The driver-compressed bitmap metadata word is not consumed by the EGA decode
  path. If another driver uses it for placement or palette selection, that is
  an alternate-driver compatibility detail.

## 12. Sources

Cleanroom prose derived from these private analysis notes:

- `u5-decomp/formats/ega-driver.md`.
- `u5-decomp/functions/EGA_DRV/_OVERVIEW.md` (full per-slot index, 38 slots
  plus helper-routine notes, completed during the 2026-05-26 follow-up pass).
- Per-slot notes for every dispatch entry the engine reaches, including
  `0x0868_set_video_mode.md`, `0x08E4_alloc_back_buffer.md`,
  `0x093C_set_descriptor_render_target.md`,
  `0x0958_set_es_to_back_buffer.md`, `0x098A_back_buffer_invalidate.md`,
  `0x09AE_back_to_front_full_transfer.md`, `0x0A78_get_pixel.md`,
  `0x0AEA_scroll_screen_up_8.md`, `0x0E66_set_color.md`,
  `0x0E6C_plot_pixel.md`, `0x0F8E_draw_line_bresenham.md`,
  `0x1072_fill_horizontal_to_back.md`, `0x10FE_fill_rect_v1.md`,
  `0x1180_fill_rect_v2.md`, `0x1226_draw_compressed_bitmap.md`,
  `0x12B4_tile_blit_general.md`, `0x162E_tile_blit_general_flagged.md`,
  `0x1637_tile_blit_16x16.md`, `0x17A9_pack_to_back_buffer.md`,
  `0x18F6_free_asset_segment.md`, `0x190E_silhouette_stamp_back_buffer.md`,
  `0x19D2_glyph_8x8.md`, `0x1DE8_delay_with_animation_step.md`,
  `0x1F98_tile_pixel_randomize.md`, `0x256B_lfsr_pixel_dissolve.md`,
  `0x282D_animate_flames_strip.md`,
  `0x2AB3_tile_palette_swap_save_restore.md`.
- Load-bearing helper notes: `0x045C_compute_edge_masks.md`,
  `0x04F6_front_buffer_scanline_fill.md`,
  `0x263A_lfsr_pixel_copy_helper.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x0E94_load_display_driver.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x6FBC_post_combat_trap.md`.
- `u5-decomp/functions/ULTIMA_EXE/0x5F86_combat_enter_exit.md`.
