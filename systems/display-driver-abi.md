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

The separate resident far pointer used by the disk-error handler is not a
driver dispatch cell. It points back into the resident executable and should
not be treated as part of the `*.DRV` ABI. Its public behaviour is specified in
`disk-prompt.md`. (Earlier revisions of this paragraph called it the
"screen-mode handler"; that name is withdrawn — see
`systems/screen-mode-dispatch.md`.)

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
front buffer, by leaving the render-target selector on the visible page rather
than by any inability of those entries to reach the hidden one: the tile, glyph,
pixel-plot and rectangle-fill entries all have working back-buffer bodies
(sections 6, 8 and 9.2). Back-buffer use in the shipped game is limited to
whole-screen or effect-oriented paths such as compressed bitmap staging,
silhouette stamping, screen dissolves, and title/menu animation.

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
| `0x18` | 8 | Carry-flag-gated rectangle copy between the two drawing surfaces. With carry set it copies the requested rectangle from the hidden surface to the visible one; with carry clear it only points the driver's working segment register at the hidden surface and returns. See section 9.4. |
| `0x1B` | 9 | Two-direction full-screen plane copy used by back-buffer-touching paths to refresh or seed the alternate buffer. |
| `0x1E` | 10 | Full-screen front-buffer and back-buffer in-place swap, row by row, using a driver-internal scanline scratch. This is a swap, not a one-way transfer. |
| `0x21` | 11 | No-op. |
| `0x24` | 12 | Read one pixel and return its 4-bit colour. |
| `0x27` | 13 | Scroll a rectangle vertically by a signed row distance, on whichever surface the render-target selector names, blanking the vacated band. A hardwired fast path handles the message panel's eight-scanline scroll-up without blanking. See section 9.5. |
| `0x2A` | 14 | No-op. |
| `0x2D` | 15 | Set the current 4-bit drawing colour. |
| `0x30` | 16 | Plot one pixel with the current drawing colour, on whichever surface the descriptor's render-target selector currently names. The back-buffer path is a real write: it modifies the pixel's bit in all four back-buffer plane slices. See section 9.2. |
| `0x33` | 17 | Draw an arbitrary-direction integer line between two pixel endpoints. |
| `0x36` | 18 | No-op. |
| `0x39` | 19 | Fill a single horizontal scanline in either buffer. The row coordinate is the entry's Y argument; there is no row loop. |
| `0x3C` | 20 | Fill a rectangle in either buffer using the earlier-generation rectangle helper. |
| `0x3F` | 21 | Fill a clipped rectangle with the current colour, on whichever surface the descriptor's render-target selector currently names. See section 6. |
| `0x42` | 22 | Prepare a decompressed paired graphics archive for blitting: an in-place, size-preserving conversion of every image in the segment from packed four-bits-per-pixel storage into the per-row planar layout the EGA blitters expect. Not a codec, not a decompressor, and not a draw call; see section 7. The CGA, Hercules and Tandy drivers implement this entry as a no-op because their blitters read the archive in its packed form. |
| `0x45` | 23 | No-op. |
| `0x48` | 24 | Register a loaded asset segment as the active tile/sprite asset and prepare it for blitting by converting its embedded pixel payload from packed to planar layout in place. Despite the historical working name "pack to back buffer", this entry does not touch the back buffer; it operates on the asset segment. |
| `0x4B` | 25 | General tile or sprite blit. Accepts a render-flags word whose low bits choose between an opaque blit and a transparency-mask blit. |
| `0x4E` | 26 | Stamp one record of a one-bit-per-pixel record archive into the back buffer. Takes the archive segment, the record index, and a destination pixel `(x, y)`. The index is bounds-checked against the archive's record count and an out-of-range index returns without drawing. Set source bits are written into all four planes, so the stamped shape reads as the brightest palette index in the back buffer; clear source bits leave the destination untouched, so the stamp is an overlay rather than a rectangle overwrite. This is the entry the intro uses for every `TITLE.BIT` and `BRITISH.BIT` draw. |
| `0x51` | 27 | Draw one 16-by-16 tile on whichever surface the descriptor's render-target selector currently names. The entry has a separate, complete back-buffer body; see section 8. Ordinary viewport painting leaves the selector on the front buffer. |
| `0x54` | 28 | No-op. |
| `0x57` | 29 | No-op. |
| `0x5A` | 30 | Release the current asset segment back to DOS. |
| `0x5D` | 31 | Draw one 8-by-8 fixed-cell glyph on whichever surface the descriptor's render-target selector currently names. The entry has a separate, complete back-buffer body; see section 8. Ordinary text painting leaves the selector on the front buffer. |
| `0x60` | 32 | Carry clear mutates loaded tile graphics for animated shimmer effects. Carry set temporarily constructs and paints one row-spliced 16-by-16 cell, then restores the shared tile bytes; see section 10. |
| `0x63` | 33 | Tile blit with the transparency-mask flag forced on. Equivalent to dispatch offset `0x4B` with the caller-supplied flag word bitwise-ORed with the transparency bit. |
| `0x66` | 34 | Carry clear copies a back-buffer rectangle to the front buffer in pseudo-random dissolve order. Carry set writes one source-tile pixel into one viewport cell per call; see section 9.6 for both visit-order contracts. |
| `0x69` | 35 | Two entries selected by the carry flag on entry. Carry clear: advance and draw the title/menu idle animation strip. Carry set: play the subtitle ignition transition using the one-bit resource segment passed in the primary register. |
| `0x6C` | 36 | Loaded-tile graphics palette-plane mutation, save, restore, byte-parameterized substitution, and an extended mode reached only by alternate paths. The combat framer reaches this entry with mode value `1` when the resident tile-restoration flag is set. |
| `0x6F` | 37 | Play a driver-resident byte-stream animation script, pacing each presentation step with a CPU-calibrated busy wait. This is the entry that plays the title flourish. |

The most important correction from the full driver pass is that dispatch
offset `0x3F` is the filled-rectangle entry. An earlier revision called
dispatch offset `0x42` a compressed bitmap/font-strip decoder; that is
withdrawn in full, and section 7 gives what the entry really does. No driver
entry decodes the one-bit-per-pixel `.BIT` and `.PCS` resources at all: those
are parsed by the caller and drawn through the ordinary point, span, stamp and
blit entries, on every driver family.

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

**Correction: this entry is render-target aware.** An earlier revision of this
document said dispatch offset `0x3F` was "front-buffer only", that it skipped
its per-scanline fill when the descriptor's render-target selector named the
back buffer, and that back-buffer fills were owned by dispatch offsets `0x39`
and `0x3C` instead. All three statements are withdrawn. The entry reads the
render-target selector before filling and writes whichever surface the selector
names; it has a distinct row loop for each surface, and both loops fill for
real. The visible contract above therefore applies to the front buffer and the
back buffer alike, and the choice of surface is made entirely by the render-target
selector the caller set beforehand.

This matters beyond bookkeeping: the endgame's fade to black
(`systems/endgame.md` section 7) and the map-viewport fades listed in
section 9.6 all work by pointing the render target at the hidden surface,
filling it through `0x3F`, and then dissolving the result forward. An
implementation that made `0x3F` a no-op on the hidden surface would leave those
transitions dissolving stale pixels.

## 7. Packed-To-Planar Graphics Preparation

Dispatch offset `0x42` is **not** a bitmap decoder, not a decompressor, and not
a blitter. Earlier revisions of this document described it as the driver entry
that decoded `TITLE.BIT`, `BRITISH.BIT`, `WD.BIT`, and `PROPORT.PCS` from a
sparse pointer table. That description is withdrawn in full: no driver entry
consumes those files, and they carry no pointer table. Their real container is
specified in `formats/bit.md` and `formats/font-pcs.md`, and it is read by the
caller, not by the driver.

What `0x42` actually does is an **in-place, size-preserving** conversion of an
already-decompressed paired `.16`/`.4` graphics container, from packed
four-bits-per-pixel storage into the per-row planar layout the blitters want.
It receives only the segment holding that container. It touches no video
memory, takes no destination rectangle, reads no screen descriptor, does not
consult the front/back render-target selector, and changes no buffer's size.

The container it walks is the one specified in `formats/tiles.md`: an image
count followed by that many 32-bit image offsets, then image records of
`width`, `height`, and `stride * height` bytes, where `stride` is half the width
rounded up to a multiple of four. Records are stored back to back.

Compatibility requirements:

- Treat this entry as a preparation pass over a decompressed `.16`/`.4`
  container, not as a codec and not as a draw call.
- Read the directory offsets as 32-bit values. The high half is zero in every
  shipped archive, which is why an earlier reading mistook the pair for a
  pointer word plus a metadata word.
- The conversion is a pure permutation of the bytes already present; total size
  is unchanged.
- A driver-internal scratch buffer caps the maximum convertible image width at
  320 pixels.
- A modern renderer that stores decoded images in its own form does not need
  this entry at all. It exists to serve the original blitters' plane-major
  expectations, and it is an implementation convenience of the original driver
  rather than a property of any on-disk data.
- The CGA, Hercules, and Tandy drivers stub this entry in the analyzed
  baseline.

Because no driver entry reads them, `TITLE.BIT`, `BRITISH.BIT`, `WD.BIT`, and
`PROPORT.PCS` are decoded entirely on the caller side: unwrap the shared LZW
envelope where present, parse the one-bit-per-pixel sub-image list, then draw
records with the ordinary point, span, and blit entries in the caller's
currently selected colour.

## 8. Tile And Glyph Rendering

The 16-by-16 tile entry is the viewport tile workhorse, and in ordinary use it
draws to the front buffer. It accepts only 16-pixel width and 16-pixel height
requests; other sizes are ignored by this entry and belong to the general
blitter. The entry is render-target aware: it reads the descriptor's
render-target selector and, when the selector holds the back-buffer value `1`,
branches to a separate 16-row back-buffer body that writes each row's four
plane bytes into the four 8,000-byte back-buffer plane slices, advancing one
scanline (40 bytes) per row in the destination and eight bytes per row in the
source. Any other selector value takes the front-buffer body. Both bodies stamp
the tile opaquely over the destination and neither clips, so the caller is
responsible for keeping the 16-by-16 cell on screen. Each tile consumes 128
bytes in the EGA asset segment:

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

The fixed-cell glyph entry draws one 8-by-8 glyph. The source glyph is eight
bytes, one byte per row, with the most-significant bit as the leftmost pixel.
The caller supplies foreground and background colours through the text
renderer's attribute path. The resulting cell must contain the foreground
colour where the glyph bit is set and the background colour where it is clear.
As with the tile entry, this entry is render-target aware: a zero selector
takes the front-buffer body, and any non-zero selector takes a separate
back-buffer body that produces the same cell in the four back-buffer plane
slices. That body makes two passes over the glyph's eight rows — a background
pass that overwrites each plane byte of the cell, setting the inverted glyph
mask in the planes the background colour selects and clearing the others, then
a foreground pass that ORs the glyph mask into the planes the foreground colour
selects. The visible contract is identical on both surfaces: the whole 8-by-8
cell is replaced, foreground where the bit is set and background where it is
clear. Ordinary fixed-cell text is drawn with the selector on the visible page.

**Correction: both entries have real back-buffer paths.** An earlier revision
of this section said the tile entry returned without drawing when the back
buffer was selected, that there was no separate back-buffer tile path, and that
selecting the back buffer made the glyph entry a no-op. All three statements
are withdrawn: each entry branches to a dedicated back-buffer body, and both
bodies draw for real. What survives from that revision is only the usage
observation, which is a separate claim: ordinary viewport tiles and fixed-cell
text are painted with the render-target selector naming the front buffer, and
only staging and transition sequences point it at the hidden surface
(`display-driver.md` section 7). A cleanroom implementation must nevertheless
support both surfaces for both entries, exactly as it must for the clipped
rectangle fill in section 6.

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
non-zero. The tile entry is the one exception to that reading: it takes its
back-buffer body only for the exact value `1`. Not every entry consults the
selector at all; entries explicitly noted as front-buffer-only — the pixel read
at `0x24` and the line rasteriser at `0x33` — ignore it and always address the
visible page.

Dispatch offset `0x2D` stores a 4-bit drawing colour into a driver-resident
single-byte register. Later entries that fill, plot, or rasterise without an
explicit colour argument use that register. Setting the colour does not
itself touch the framebuffer.

### 9.2 Pixel-Level Primitives

Dispatch offset `0x24` reads one pixel from the front buffer and returns the
4-bit colour value through the third register. It always reads from the
visible page and ignores the render-target selector. The colour is reassembled
by selecting each colour-plane in turn and bit-testing the relevant byte.

Dispatch offset `0x30` writes one pixel using the current drawing colour, on
whichever surface the render-target selector names. The entry first rejects
coordinates outside the 320-by-200 screen, then consults the selector: with the
front buffer selected it writes through the adapter's plane-masked write path,
and with the back buffer selected it takes a distinct four-pass body that sets
or clears the pixel's bit in each of the four 8,000-byte back-buffer plane
slices according to the current colour. A carry flag set on entry selects an
exclusive-or plot instead of a replace plot; both surfaces honour that mode, and
the entry returns the driver to replace mode before it exits. Both paths write
for real; an earlier
revision of this document called the back-buffer branch a silent no-op and
described the entry as front-buffer only, and both statements are withdrawn.
This is the same render-target awareness section 6 records for the clipped
rectangle fill.

Dispatch offset `0x33` draws an integer line between two pixel endpoints. The
implementation uses a textbook integer Bresenham step over the major axis with
plus-or-minus-one minor-axis steps, so the line includes both endpoints and
covers all eight octants. Each plotted pixel goes through the same single-pixel
writer as dispatch offset `0x30`, but this entry re-points that writer at the
visible page before every pixel, so lines are front-buffer-only regardless of
the render-target selector. The entry does not optimise horizontal or vertical
lines into rectangle fills.

The resident layer wraps this entry twice: a line-from-two-endpoints call that
also records the second endpoint as the current point, and a line-to-point call
that starts from that recorded point. A polyline is therefore one of the former
followed by any number of the latter, and that is how the game-screen frame's
box outlines and the bracket end-cap strokes are issued (`display-driver.md`
section 7). Purely horizontal rules are also sometimes issued through the
single-scanline entry at dispatch offset `0x39` instead, which produces the same
pixels; both spellings appear in the chrome-repaint helpers.

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

Dispatch offset `0x18` is a carry-flag-gated entry with two behaviours.

**Correction: this entry is not a no-op, and it is not whole-screen.** An
earlier revision of this document said the entry dispatched between two
whole-screen plane-copy helpers, that the resident core always cleared carry
before the far call, and that implementations therefore "need not expose this
entry at all". All three statements are withdrawn.

With carry **set**, the entry copies a **rectangle** — the same inclusive
left/top/right/bottom rectangle the fill entries take — from the hidden
surface to the visible one, using the same edge-mask and row-table machinery
as the rectangle fill, and restores the plane-select state it disturbed before
returning. With carry **clear**, it performs no copy; it only loads the
driver's working segment register with the hidden surface's segment and
returns, which is inert for any caller that does not go on to use that
register.

Carry is not fixed by the calling convention. The resident core reaches this
entry through a wrapper that takes the rectangle plus a source-surface and a
destination-surface index, rejects calls where the two indices are equal or
where either exceeds one, and sets carry exactly when the source surface is
the hidden one. That carry-set path is live in the shipped game: it is how the
intro's start/menu loader reveals the title logo rectangle immediately on the
path where the player has already pressed a key and the pseudo-random dissolve
is skipped — `intro.md` section 3, loader step 4, "the plain caller path copies
the rectangle in one step". An implementation that treats this entry as a no-op
loses that reveal and leaves the logo region blank on the skipped path.

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

### 9.5 Vertical Rectangle Scroll

Dispatch offset `0x27` is the vertical scroll entry. It has two bodies, chosen
by the rectangle's left edge.

**Correction: this is a general scroll-rectangle entry.** An earlier revision
of this document said the entry checked that its primary argument named the
message panel's left edge and that "calls with any other left-edge value return
without visible effect", concluding that the entry was "strictly a
right-side-text-panel scroll, not a general scroll-rectangle helper", and that
any per-call distance argument was "vestigial". Those statements are withdrawn.
The left-edge test selects between two live bodies; it does not gate the entry.

**General path — every left edge except the message panel's.** The entry takes
an inclusive rectangle and a **signed row distance**: positive moves the
rectangle's contents one way, negative the other, and the sign is folded into
the row-walk direction so the copy never overlaps itself destructively. The
horizontal extent is resolved through the same sub-byte edge-mask machinery the
rectangle fill uses, so unaligned left and right edges are honoured. The entry
reads the descriptor's render-target selector and has a **separate, complete
body for the hidden surface**, exactly like the fill, tile and glyph entries.
When the copy finishes, the entry **blanks the vacated band**: it saves the
current drawing colour, fills the band the contents moved out of with colour
index `0`, and restores the colour. The band is computed from the distance and
its sign, so it is the correct edge of the rectangle in either direction.

**Message-panel fast path — left edge at pixel column 192.** This path is
hardwired and ignores both the rest of the rectangle and the distance argument:

| Property | Value |
|---|---|
| Horizontal extent | Pixel columns 192 through 319 inclusive (a 128-pixel-wide right-side text panel, 16 character cells wide). |
| Vertical extent | Pixel rows 88 through 199, advanced one row per inner iteration; iterations that reach beyond the visible 200 rows write to non-visible video memory and are harmless. |
| Scroll distance | Exactly eight scanlines upward, hardcoded. The caller's distance argument is not read on this path. |
| Exposed band | Not blanked. After the scroll, the bottom eight scanlines of the panel inherit whatever pixels happened to lie immediately below the panel before the scroll. The caller paints fresh content into the bottom row immediately after the scroll, which masks the un-blanked content. |
| Caller responsibility | Callers that need a clear bottom row must request a fill or a fresh glyph draw for those scanlines after the scroll completes. |

The panel this fast path serves is the gameplay message window, text cells
columns 24..39 rows 11..23 — see `text-output.md` sections 10.1 and 10.5. The
resident text layer converts its scroll requests to pixel rectangles before
dispatching, and the message window's rectangle always presents that same left
edge, so on the shipped EGA baseline the fast path is the one the text layer
observes and every text scroll moves exactly one cell row regardless of the
distance the resident helper computed.

A compatible engine should implement the general signed-distance,
render-target-aware, band-blanking scroll and then special-case the message
panel to the eight-scanline, no-blank behaviour above. Implementing only the
panel case — or treating other rectangles as no-ops — is not ABI-faithful.

### 9.6 Rectangle Dissolve Visit Order

Dispatch offset `0x66` copies pixels from the back buffer to the front buffer
in pseudo-random order until every pixel in the requested rectangle has been
copied exactly once. The original implementation uses a Galois-style LFSR
indexed by the rectangle's pixel count to select the next visited pixel; the
visible contract is:

1. On uninterrupted completion, every pixel inside the inclusive rectangle is
   visited exactly once.
2. After uninterrupted completion, the front buffer matches the back buffer
   inside the rectangle. An input abort has the partial-transfer rule below.
3. The visit order is deterministic and reproducible across calls with the
   same rectangle dimensions.
4. The visit order is not row-major, not column-major, and not a clean spiral;
   it should appear as scattered single-pixel updates to a viewer.

**Abort gate and sound.** The entry carries a driver-local gate that is enabled
when the driver image is first loaded and is cleared permanently the first time
any character is drawn through the driver's fixed-cell glyph entry. Nothing
ever re-enables it. While the gate is enabled, the dissolve does extra work on
alternating visited pixels, and only there. The alternating flag starts at
zero in a freshly loaded driver; each copied pixel toggles it, and the extra
work runs when the new value is one. The first gated dissolve therefore checks
visits `1, 3, 5, ...`, not `2, 4, 6, ...`. On each checked visit it **retunes the
speaker** and samples keyboard status. Both the retune and the poll sit behind
the same alternating flag, so neither happens on every pixel. **Earlier
revisions of this section said the speaker effect was per-pixel and that its
pitch tracked progress through the rectangle; both halves are withdrawn.** The
frequency is drawn from a driver-internal scrambling sequence rather than
rising monotonically, and the width of the range it is drawn from grows as the
transfer advances, so the effect reads as a rising, broadening rasp rather than
a glissando.

> **Withdrawal.** A further revision of this paragraph called each checked visit
> "one short percussive speaker click" and treated the abort's silencing as part
> of that per-click behaviour. Both are withdrawn (see `RETRACTIONS.md`). The
> speaker is enabled at the first checked visit and **nothing disables it until
> the dissolve exits**: what each checked visit does is retune one continuously
> running square wave, whose pitch is randomised across a band whose upper edge
> grows. Each visit also pays a short calibrated hold of roughly 50 to 60
> microseconds, so the gated dissolve is not free-running like the ungated one.
> `audio.md` section 8.6.1 owns the frequency contract, the band growth, and the
> exact per-click arithmetic.

A pending keystroke aborts the
call immediately, leaving the rectangle **partly** transferred; the speaker is
silenced at the dissolve's shared exit block, which both the abort path and
normal completion reach. The four-plane copy of the checked pixel happens before its click and
status test. Thus a key already pending when the first start/menu dissolve
begins leaves exactly one pixel transferred before abort: the first visit,
`(1,0)`. The driver's status test does not consume the key, so it is still
queued for whatever the caller reads next. The start/menu loader immediately
uses the normal consuming keyboard reader and removes that same key. Once the
gate has been cleared, the dissolve is silent, never polls, and runs to
completion regardless of input.

In practice that makes exactly one dissolve in a normal session interruptible:
the first start/menu screen reveal, which happens before any menu text has been
drawn. Every later dissolve in the run — the intro story step-1 transition and
every repeat of the menu reveal — is silent and uninterruptible. An engine that
wants the historical behaviour should model the gate rather than hard-coding
"the first one", because a path that draws text earlier changes which call is
affected.

**Single-cell use, and why it must not be confused with the rectangle
dissolve.** Dispatch offset `0x66` is really two operations selected by the
carry flag on entry. Carry clear is the rectangle dissolve specified above.
Carry set is a different sub-entry that converges one 16-by-16 viewport cell to
a requested tile; it takes a cell position and a tile, not a rectangle, and it
advances one pixel per call. The EGA and Tandy entries have the same decoded
pixel contract. Call 0 writes source pixel `(0,0)`. Calls 1 through 255 begin
with eight-bit state 1, write `(x = state >> 4, y = state & 15)`, then shift
the state right and XOR the result with `0xB8` when the old low bit was one.
The maximal sequence visits every nonzero state once, so the complete run is a
256-position permutation of the cell. The requested tile is read directly and
every source palette index, including zero, replaces the destination pixel;
there is no transparent colour.

The resident wrapper invokes this entry exactly 256 times. After completed
pixel counts `8,16,...,248` it runs one mode-dependent tick, exactly 31 tick
boundaries, and it does not tick or poll after count 256. In Return-to-View the
boundary operation is the complete one-budget preview tick: active-object and
animated-tile advance, intro title tick, actor scatter, revealed-span repaint,
reveal-cursor update, one consuming read through the normal keyboard input
path, then — only when no key was read — one BIOS-tick wait and strip-specific
ambient sound. A key is consumed and discarded as an abort signal before that
wait, leaving the already-written permutation prefix intact. The preview
command also bypasses its actor cleanup on this abort, so its two suppression
fields and the zero/suppression preview-plane pair remain until later
replacement.
The outer saved-surface restore hides the partial raster but does not roll back
those memory changes. Return-to-View's terrain-versus-overlay source choice is
specified in `formats/location-dat.md` section 11.

**Correction.** An earlier revision of this section said the resident core
wraps *the rectangle dissolve* in an outer loop that re-invokes the world tick
every few visits, "so the dissolve does not freeze gameplay timing for the
duration of a full-screen transition". That is withdrawn. The stepped,
tick-interleaved wrapper belongs to the carry-set single-cell sub-entry only.
Every caller of the rectangle dissolve issues it as **one blocking call**: no
world tick, no title tick, and no gameplay time advance runs while a rectangle
dissolve is in progress, whatever the rectangle's size. Its wall-clock duration
is whatever the machine needs to visit that many pixels.

**Real-time compatibility policy.** Historical wall-clock duration is not a
stable contract. The driver has no timer read, retrace wait, explicit frame
publication, or intermediate callback in this loop. It writes video memory as
fast as the CPU, bus, adapter, and selected driver permit; period scanout may
therefore reveal partial states, but the program defines no frame boundaries
among them. The first gated dissolve also performs its alternating speaker and
keyboard-status work, so even equal-sized calls need not take equal time.

The normative modern baseline is consequently **atomic presentation at the
blocking-call boundary**: preserve the required visit order internally where
tests or abort-prefix behavior observe it, and publish the completed rectangle
when the call returns. A frontend may instead animate successive prefixes, but
its duration, cadence, and visits per frame are presentation choices rather
than compatibility claims. Such an animation must preserve the published
order and final pixels and must not add gameplay/title ticks, consuming input,
or abort points beyond the one historical gated status test. No timing
tolerance is specified for optional animation; automated compatibility tests
should compare the ordered prefix rules and final raster, not elapsed time.

A compatible engine that wants exact frame-by-frame visual parity with the
original can reuse the original tap-set inventory, indexed by the integer
log2 of the rectangle's pixel count; the size-class taps are stored in the
driver as 16-bit Galois polynomials. An engine that does not need exact
frame-by-frame parity may substitute any other order that satisfies the four
bullet points above.

**Callers.** For engine authors who want the complete picture, the rectangle
dissolve has six call sites in the shipped program, spanning four rectangles
(the map-viewport rectangle accounts for three of the six sites):

| Rectangle (inclusive) | Where | Specified in |
|---|---|---|
| `(40, 86)..(75, 120)` | Intro story step 1 | `systems/intro.md` section 10 |
| `(0, 0)..(319, 100)` | Intro start/menu loader, animated path only | `systems/intro.md` section 10 |
| `(0, 0)..(319, 199)` | Endgame, entering the final narrative presentation | `systems/endgame.md` sections 7 and 8 |
| `(8, 8)..(183, 183)` | Rescue/refuge entry after the unending-darkness line | `systems/blackthorn.md` section 7 |
| `(8, 8)..(183, 183)` | Rescue/refuge exit after party restoration and the vertigo line | `systems/blackthorn.md` section 7 |
| `(8, 8)..(183, 183)` | Dungeon Search after one of its three reveal rewrites | `systems/dungeon-mode.md` section 8 |

The rectangle `(8, 8)..(183, 183)` is exactly the 176-by-176 world map viewport.

The three viewport sites are not shared audience or Search/Open effects. Both
Blackthorn sites belong exclusively to the total-party-defeat rescue/refuge
sequence. The earlier one dissolves out to a black hidden viewport. The later
one dissolves in a black viewport with the on-foot party sprite at centre cell
`(5,5)`. The command site belongs exclusively to lit dungeon S-Search. Three
outcomes reach it: revealing exact `0x61`, crumbling a Doom-flavour `0xC?`
skeleton, and revealing a `0xD?` hidden door. After the outcome's cell rewrite,
the ordinary first-person renderer composes the resulting view on the hidden
surface and the call dissolves that new view in. Open never reaches it.

**The fade idiom.** Four of the six sites are instances of one caller-side
idiom that an engine should recognise, because the dissolve alone does not
describe it:

1. Point the render target at the hidden surface.
2. Either fill the rectangle with a flat colour (index `0` for a fade to
   black), or compose the new scene into it.
3. Point the render target back at the visible page.
4. Dissolve that rectangle from the hidden surface to the visible page.

Filling first gives a dissolve **out** to a flat colour; composing first gives
a dissolve **in** to new art. The dissolve entry itself always reads the hidden
surface and always writes the visible page; it ignores the render-target
selector entirely. The selector changes around it exist only so that steps 2
and 4 land on the right surfaces.

## 10. Transitions And Animation Entries

The EGA driver owns several visual effects that are not gameplay systems:

- Title/menu idle animation: a four-frame strip drawn at `(0, 65)` with size
  `320 x 49`, advanced by dispatch offset `0x69` with carry clear. The entry
  owns only the frame counter and the copy; the frame pixels are staged into
  the back buffer beforehand by the caller (see `intro.md` section 5). Each
  call copies 49 rows at full 320-pixel width from back-buffer row
  `50 x frame_index`, then advances the counter modulo four. Correction: an
  earlier revision described the frames as produced inside the driver and
  unavailable to a clean engine; they are ordinary shipped archive records.
- Subtitle ignition transition: dispatch offset `0x69` with carry set and a
  loaded one-bit resource segment in the primary register. The entry saves the
  back buffer to a scratch allocation, clears it, runs a pseudo-random
  two-pass masked reveal, then restores the back buffer and releases the
  scratch. Each pass resets its 128-position publication countdown, or 256
  below calibration 250; successful completion adds an uncounted `(0,0)`
  fixup, and no partial tail is published. Each publication draws the current
  idle-strip frame before incrementing its free-running counter. Sound and the
  45/50-unit calibrated wait occur only at publications. Keyboard status is
  tested after every nonzero LFSR state, after any restore and publication for
  that state; it is not tested after the corner fixup. It is paced by a
  CPU-calibrated busy wait rather than a timer tick and is not a cursor-blink
  entry. `intro.md` section 5 owns the exact pass counts, gate recurrence,
  speaker burst, poll, abort, and post-effect loader tick.
- Rectangle dissolve: copies pixels from the back buffer to the front buffer
  in pseudo-random order until the rectangle matches. The EGA implementation
  uses a deterministic LFSR-style visit order; after the entry completes, the
  destination rectangle's front-buffer pixels match the back buffer. It always
  reads the back buffer and always writes the front buffer, regardless of the
  descriptor's render-target selector. It is always issued as a single blocking
  call, and it is the carry-clear half of dispatch offset `0x66`; the carry-set
  half is the stepped single-cell entry. See section 9.6.
- Animated tile shimmer and moongate row splice: mutates selected loaded tile graphics entries rather
  than writing framebuffer pixels directly, then runs its own propagation and
  composite pass. In the ordinary world path the effect becomes visible when the
  viewport redraws those tiles. **The behavioural contract for the carry-clear
  body — which tiles it rotates, which it composites and through which masks,
  and how it flickers the fire fixtures — is `systems/animation.md` Section 12.**
  That body writes tile pixels **exclusively** into the loaded tile asset: never
  to the visible screen and never to the back buffer, re-checked by decoding the
  whole body and by scanning it for the video-memory address constant with zero
  hits. The one exception is a few bytes parked in a driver-private scratch area
  to carry a wrapping pixel row across each rotation, shared with this entry's
  other body. The entry also takes a target cell as a screen
  tile row and column plus the current viewport pixel origin and a step value,
  and the Return-to-View preview and endgame gate drive it that way for a local cell effect,
  stepping `1..15` to open a cell and `15..1` to close it. The caller marks the
  cell as skipped in its own repaint for the duration, so the shimmer entry owns
  that cell while the effect runs. Carry set selects a separate direct-cell
  body rather than the large randomizer. For Return-to-View step `n` in 1..15,
  it builds a temporary 16-by-16 tile from base tile `0x05`: destination rows
  `0..15-n` retain the same base rows, and destination rows `16-n..15` receive
  portal-tile `0xDC` rows `0..n-1`. The endgame uses the identical operation
  with chamber-floor tile `0x44` as its base. It then paints all 256 pixels opaquely with
  no palette transform and restores every byte of the shared loaded scratch
  tile before returning. EGA and Tandy have the same decoded palette-index
  result. Reverse playback is the identical rasters for `n=15..1`, not a
  second operation. The command-level final plane write supplies the complete
  portal or base tile; step 15 itself still retains base row 0. See
  `formats/location-dat.md` section 11 for the command schedule and abort rule.
- Loaded-tile palette-plane mutation: dispatch offset `0x6C` mutates tile
  graphics in the loaded asset segment rather than drawing directly to the
  framebuffer. Publicly confirmed modes are save-original tile bytes, restore
  saved tile bytes, a byte-parameterized mutation mode, a batch red/green
  plane-swap mode, and a whole-tileset remap. The combat framer's reached call
  uses mode value `1`, so it is a restoration step before ordinary world redraw
  rather than an independent presentation effect.

  **Caller correction.** An earlier revision described the red/green plane-swap
  mode as "used for combat-style terrain coloration", and the entry as reached
  from three resident dispatch sites. Both are withdrawn. Those three sites are
  thin trampolines, not callers. The five real callers and the modes they
  select are: the dungeon look/view code, twice — one mode that saves eight
  bytes of two unrelated tiles and sets a flag, and the red/green plane-swap
  mode itself; the **per-turn clock advance**, which selects the moon/sun phase
  painter and edits only the moon/sun phase tiles (this runs once per game turn,
  not at a scene transition, so "this entry fires only on scene transitions" is
  also withdrawn); the post-combat restore path, which selects the
  restore-eight-bytes mode gated on the flag the dungeon path set; and the
  endgame sequence, which selects the whole-tileset remap. Only the last of
  these touches fire fixtures, and only `0xB0`, `0xB1` and `0xBF` of them,
  through a fixed sixteen-entry nibble map; it is one-shot at the endgame and is
  not an animation.

  **One interaction worth knowing.** The plane-swap mode covers tiles `0x05`,
  `0x1E`, `0x1F`, `0x4C`, `0xCA`, `0x20..0x26`, `0x30..0x37` and `0x60..0x6F`.
  It touches no water tile and no fire fixture directly, but `0x34..0x37` and
  `0x60..0x6F` are two of the three destination groups of the per-step water
  composite (`systems/animation.md` Section 12.3), so the swap and the water
  animation write to the same bitmaps and interact. This entry is not irrelevant
  to water. *Scope: the mode-to-caller mapping rests on the pushed argument at
  each of the five call sites, each disassembled; the caller enumeration is a
  rebased near-call and near-jump census across the resident image and all code
  overlays and would miss a far or indirect call. What resident state causes the
  dungeon path to run at all was not traced.*
- Animation-script playback: dispatch offset `0x6F` takes the boot CPU
  calibration value in its primary register, holds the plane write mask at the
  blue-plus-intensity pair for the whole call, and walks a driver-resident byte
  stream. The script is a frame count followed by per-frame records of
  `(source top row, destination top row, row count, row-group list)`, where the
  group list is a separator-delimited sequence of source-row indices. Per
  presentation step the entry performs one calibrated wait and then repaints
  the frame's whole destination band: the currently selected source rows are
  copied from the back buffer packed contiguously and centred in the band, and
  the rest of the band is blanked, with the odd leftover blank row placed below
  the copied rows. Only one plane of the back-buffer image is read, and the
  write mask means each set source pixel is presented as palette index `9`;
  everything else in the band becomes index `0`. The band is always repainted
  at the full screen width, not at the source artwork's width. The fill
  direction alternates per frame: even frames fill downward from the
  destination top row, odd frames fill upward starting one row below the band,
  so odd frames are drawn vertically mirrored and one row lower.
  Any keystroke aborts, and the abort is not a bare early return: the entry
  makes the whole final frame visible with the even-frame fill direction and
  presents it once before returning, so an aborted run and a completed run
  leave the same picture. The return value reports which happened, and its
  caller uses that as the intro's skip flag. Correction: this is the
  title-flourish player, not a credits or death-screen player; `intro.md`
  section 3 publishes the shipped script's frame table and group sets.

These effects do not advance saved-game time, NPC schedules, combat rounds, or
active-object simulation.

## 11. ABI Boundaries And Remaining Hardware Parity

The EGA-facing ABI contract is complete for the v1 compatibility target:
dispatch-cell loading, EGA buffer layout, rectangle fill, packed-to-planar
archive preparation, the render-target-aware tile and glyph entries,
title/dissolve animation entries,
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
  historical-hardware parity work.
- The packed-to-planar preparation entry is a no-op in the CGA, Hercules and
  Tandy drivers. That is correct behaviour rather than a missing feature: only
  the EGA blitters need the plane-major permutation, and the other three
  families read the decompressed archive in its packed form. It does **not**
  mean those backends fail to draw archive art, and it has no effect at all on
  the one-bit `.BIT`/`.PCS` resources, which never pass through this entry.
- The per-record metadata word carried in the paired-archive directory is not
  consumed by the EGA path. If another driver uses it for placement or palette
  selection, that is an alternate-driver compatibility detail.

## 12. Sources

Cleanroom prose is derived from the private presentation, dissolve, caller
census, Return-to-View, driver-family, and raster retraces under
`u5-decomp/notes/`; the resident wrapper and preview-runtime analyses under
`u5-decomp/functions/ULTIMA_EXE/` and `u5-decomp/functions/FONT_OVL/`; the EGA
and Tandy entry/helper analyses under `u5-decomp/functions/EGA_DRV/` and
`u5-decomp/functions/T1K_DRV/`; and the private driver inventories under
`u5-decomp/formats/`. The EGA and Tandy carry-set cell paths were re-read
directly from both shipped driver binaries for the exact row-splice,
pixel-permutation, zero-colour, checkpoint, restoration, and abort contracts.
