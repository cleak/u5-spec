# EGA Mode Setup, Planar Buffer, And Palette

## 1. Scope

This document specifies the EGA-compatible video mode that the Ultima V
display driver initialises, the planar pixel layout that the driver and its
callers operate on, and the palette setup that produces visible colour. It
sits below the public rendering contract in `display-driver.md` and the public
dispatch surface in `display-driver-abi.md`, and it is the implementation
contract that an engine targeting binary-asset compatibility must satisfy.

Like the rest of the spec, this document describes behaviour in
implementation-agnostic prose. It does not reproduce driver source, assembly
excerpts, raw byte sequences, or port-write traces. Where the original
hardware mechanism is observable through gameplay or asset semantics it is
named here; details that matter only to a real-hardware-driver clone are
deferred to private analysis.

## 2. Video Mode

The driver runs the adapter in the IBM EGA 320-by-200-pixel, 16-colour planar
graphics mode. The same mode is preserved by VGA-compatible adapters at the
firmware level, so VGA hardware runs the EGA driver in this same mode without
any separate VGA code path.

| Property | Value |
|---|---|
| Horizontal resolution | 320 pixels |
| Vertical resolution | 200 scanlines |
| Colour depth | 4-bit indexed (16 simultaneous colours) |
| Pixel coordinate range | X `0..319`, Y `0..199` |
| Scanline byte stride | 40 bytes per plane |
| Plane count | 4 (one bit per colour channel) |
| Pixel container size | One byte per eight horizontal pixels per plane |
| Display pages | The adapter's page memory at the graphics base; this driver uses the first page as the visible page and reserves the 32-KB region immediately above it for the driver back buffer, which holds four sequential 8,000-byte plane images (Section 4.3) |

The visible page is hardware page zero. There is no ordinary world or text
update path that flips pages; presentation effects copy or dissolve from the
driver back buffer into page zero rather than swapping the visible page.

## 3. Mode Initialisation Sequence

The mode-set entry performs these steps in order when invoked with its
do-real-mode-set flag asserted:

1. **Cache the screen descriptor.** The driver records the caller-supplied
   resident descriptor pointer in a driver-internal slot so that later
   entries can read clipping bounds, the render-target selector, and the
   palette table.
2. **Switch the adapter to the EGA-compatible 320-by-200-by-16 mode.** The
   driver issues the firmware mode-set call for that mode. As a side effect
   of the mode change the adapter clears its video memory and selects its
   default attribute-controller palette.
3. **Load the resident palette.** The driver issues the firmware
   palette-load call against the sixteen-entry palette table held inside the
   resident screen descriptor. This replaces the firmware default palette
   with the game's palette for the current scene.
4. **Select hardware page zero.** The driver issues the firmware select-page
   call with page index zero. From this point forward the front buffer
   refers to page zero.
5. **Initialise the driver-resident lookup tables (one-time only).** On the
   first invocation, the driver builds a scanline-row byte-offset table and
   a single-bit-set lookup table inside its own code segment and marks them
   ready. Subsequent invocations reuse the same tables without rebuilding.
6. **Reset the sequencer plane-write mask, the graphics-controller bit mask,
   and the graphics-controller function-select fields to their pass-through
   values.** This guarantees that any per-call latch-modify-write idiom
   inside a later entry starts from a known state.

When invoked with the do-real-mode-set flag clear, the entry still caches the
descriptor pointer but skips the firmware mode-set, palette-load, and
page-select. It is used by alternate entry paths that re-attach to an already
initialised display.

A modern implementation that does not run on the original adapter only needs
to satisfy the observable post-conditions: the front buffer is in 320-by-200,
16-colour mode; the palette matches the descriptor table; subsequent draws
target the visible page; and per-entry state (drawing colour, plane masks,
clip bounds) is in a defined initial state. The firmware-call sequencing and
the driver-resident lookup tables are not part of the observable contract.

## 4. Planar Pixel Layout

### 4.1 Plane assignment

A four-bit colour index `c ∈ {0..15}` is decomposed into four single-bit
streams, one per plane. The mapping is:

| Plane | Bit of the colour index | Conventional colour role |
|---|---|---|
| 0 | bit 0 (least significant) | Blue |
| 1 | bit 1 | Green |
| 2 | bit 2 | Red |
| 3 | bit 3 (most significant) | Intensity |

To draw colour `c` at a given pixel, the four corresponding plane bits are set
to the bits of `c`. The attribute-controller palette table then maps each of
the sixteen possible plane-bit tuples to one of the adapter's available
colours; the in-driver code path always works in the planar 4-bit-index
domain, never in displayed-colour space.

### 4.2 Front buffer (hardware-visible page zero)

The front buffer is the visible adapter page at the EGA framebuffer base.
Within each plane, pixel `(x, y)` lives in the byte at offset
`y * 40 + (x / 8)`, in the bit selected by `7 - (x mod 8)` (the leftmost pixel
is the most-significant bit). The plane the byte belongs to is selected by
the sequencer plane-write mask at the moment of the store; a single CPU write
to that byte updates the corresponding bit position in every plane whose mask
bit is set.

A modern implementation may use any internal storage strategy as long as the
following invariants hold:

- A pixel at `(x, y)` is updated atomically with respect to other pixels.
- Operations specified as "preserve other pixels" do not disturb pixels
  outside the named rectangle.
- The four-bit colour index of a pixel can be both read and written through
  the public entries (`0x24` for read, `0x30` for write, `0x33` for line,
  `0x39`/`0x3C`/`0x3F` for rectangle fill, the tile and glyph entries for
  region updates).

### 4.3 Driver back buffer

The back buffer is reserved by dispatch offset `0x06`. It is **not**
laid out the same way as the front buffer. Instead it holds four sequential
plane images, each one a full 320-by-200 monochrome slice. The plane images
are arranged contiguously:

| Region | Length | Plane it represents |
|---|---:|---|
| First 8,000 bytes | 8,000 | Plane 0 |
| Next 8,000 bytes | 8,000 | Plane 1 |
| Next 8,000 bytes | 8,000 | Plane 2 |
| Final 8,000 bytes | 8,000 | Plane 3 |

Within a single plane slice, pixel `(x, y)` of that plane lives in the byte
at offset `y * 40 + (x / 8)`, in the bit selected by `7 - (x mod 8)` — the
same packing as the front buffer, but only for that one plane.

This layout is what dispatch offsets that read or write the back buffer
expect. Entries that copy back-to-front or front-to-back walk one plane slice
at a time, selecting the plane on the front-buffer side through the sequencer
plane-write mask. Entries that only need to stamp a single plane (the
silhouette stamp at dispatch offset `0x4E` is the canonical example) write
the same source byte into all four plane slices to produce a uniform
high-intensity colour.

A modern implementation that does not need to honour this exact layout can
hold the back buffer in any equivalent representation. The public contract is
that the entries which name the back buffer as their source or destination
behave correctly relative to the dissolves, silhouette stamps, full-screen
swaps, and animation-strip copies described in `display-driver-abi.md`.

### 4.4 Asset segment layout

After dispatch offset `0x48` registers an asset segment, the driver expects
each tile or sprite entry in that segment to be laid out as byte-interleaved
plane bytes for the row, not as the chunky packed-nibble layout that the
`.16` tile-graphics file uses on disk. The dispatch-`0x48` entry is the
helper that performs this in-place rewrite from the on-disk layout to the
in-memory layout. Once the rewrite is complete, the tile-blit entries
(`0x4B`, `0x51`, `0x63`) and the glyph entry (`0x5D`) consume the asset bytes
directly in the byte-interleaved-plane order described in
`display-driver-abi.md` section 8.

The on-disk packed-nibble layout itself is specified in `formats/tiles.md`;
the in-memory rewritten layout is implementation detail of the EGA driver and
need not match for engines that draw tiles through their own renderer.

## 5. Palette And Colour Encoding

### 5.1 Sixteen-entry palette

The active palette is a sixteen-entry table held inside the resident screen
descriptor at a fixed offset from the descriptor pointer. Each entry assigns
a displayed colour to one 4-bit colour index `c ∈ {0..15}`. The driver loads
this table into the adapter's attribute-controller palette registers when the
mode-set entry runs with its do-real-mode-set flag asserted; subsequent draws
through any dispatch entry that references the current drawing colour or a
direct colour argument refer to indices into this table, never to displayed
colour values directly.

The palette is data, not code. A modern engine reads the sixteen entries from
the resident descriptor and uses them to map every 4-bit colour index that
the driver produces into a visible colour for its output target.

### 5.2 Default palette

For the v1 baseline, the palette loaded during mode setup is the
sixteen-entry table that ships in the resident image. It is the stock set for
the mode in fifteen of its sixteen slots; the one deviation is index six,
which the shipped table sets to dark yellow rather than the stock brown
(`formats/tiles.md` section 7). This is the palette that title art, world
tiles, text glyphs, and every cutscene draw against.

**Nothing reprograms the palette after mode setup.** The palette-register
load happens once, inside the mode-set entry, and no other entry in any of the
four drivers and no code path in the resident image or in any overlay — the
intro included — issues a further palette request or writes palette hardware
directly. An earlier revision of this section said scene-specific palette
changes were "confined to the intro"; that is withdrawn, because the intro
makes none either. Apparent recolouring in the shipped presentation is always
one of two other things: a draw performed under a restricted plane write mask,
so the pixels land at a different index (`systems/intro.md` section 3), or a
display-effect entry that mutates the *loaded asset data* — the red/green
plane-swap mode of `display-driver-abi.md` section 10 — rather than the
palette.

A compatible engine may either reproduce the same sixteen entries verbatim
for exact visual parity, or remap them to a representation that matches its
output target (for example, by converting EGA palette indices to sRGB triples
through a fixed lookup). The semantic contract is that any displayed pixel
whose driver-internal index is `c` maps to the same displayed colour each
time it is drawn, until the descriptor's palette table is replaced.

### 5.3 Drawing-colour register

Dispatch offset `0x2D` stores a single 4-bit colour index into a
driver-resident register. Later entries that need a drawing colour without an
explicit argument (the rectangle fills, the line, the pixel plot, the
horizontal-span fill) read it from this register. The text and glyph entries
do not consult this register; they take their foreground and background
colours directly through their register arguments.

This register is part of the public contract. Setting it does not itself
trigger a draw; the next draw call that needs a colour observes its current
value.

### 5.4 No partial-channel palette mutation

The driver does not perform incremental palette changes (one channel at a
time, single-index updates, palette-rotation effects) on its mainline paths.
Any visible "palette" or "colour shift" effect in the game is implemented by
mutating the loaded asset bytes (dispatch offsets `0x60` and `0x6C`) and
relying on the next ordinary tile draw to bring the new bytes onto the
screen, not by changing the attribute-controller registers.

This is significant for a modern engine: it means a renderer can treat the
palette as essentially static for the duration of a scene, and need not
implement per-frame palette upload logic to reproduce the original visible
behaviour. It also means the "shimmer" or "scorched-terrain" effects must be
modelled as tile-asset mutations, not as colour-channel mutations.

## 6. CGA, Hercules, And Tandy Notes

The CGA, Hercules, and Tandy driver families implement the same dispatch table
at the same offsets but target their own hardware modes. None of them shares
the EGA pixel layout, and **Tandy is not an EGA equivalent at pixel level**
despite using the same sixteen palette indices.

| Family | Mode | Surface | Pixel storage |
|---|---|---|---|
| EGA | Firmware mode `0x0D` | 320 x 200, 16 colours | Four bit planes, one plane byte per eight pixels |
| Tandy | Firmware mode `0x09` | 320 x 200, 16 colours | **Packed** four bits per pixel, one contiguous row per scanline |
| CGA | Firmware mode `0x04` | 320 x 200, 4 colours | Packed two bits per pixel, with the even and odd scanlines held in two separate halves of the adapter's memory |
| Hercules | No firmware mode; the driver programs the display controller directly | 720 x 348, 1 bit per pixel | Packed one bit per pixel, with the scanlines interleaved across four banks by row number modulo four |

Consequences that are part of the public contract:

- **Asset family.** The high-colour `.16` family is selected for EGA and
  Tandy; the low-colour `.4` family for CGA and Hercules. That split is stated
  in `display-driver.md` section 2 and follows colour depth, not resolution.
  Any statement that Tandy shares CGA's family, or that Hercules shares EGA's,
  is wrong. There is no separate Hercules screen-art family; the only other
  per-driver asset difference in the whole distribution is the glyph pair.
- **Archive preparation.** The packed-to-planar preparation entry
  (`display-driver-abi.md` section 7) exists only in the EGA driver. The other
  three families implement it as a no-op, because their blitters read the
  decompressed archive in its packed form directly. This is correct behaviour,
  not a missing feature, and it does not blank any screen.
- **One-bit resources.** The standalone one-bit bitmap and proportional-font
  resources are parsed by the caller and drawn through the ordinary point,
  span, stamp and blit entries, so they are available on every driver family.
- **Title band.** The title/menu idle band keeps the same four-frame cycle on
  every family. EGA, CGA and Tandy place it identically; Hercules uses a taller
  band pitch and a lower destination row to suit its 348-line display, and
  copies 640 of the 720 pixels in a row. The table in `display-driver.md`
  section 8 gives the numbers.
- **Drawing colour.** The CGA and Hercules drawing-colour entries reduce the
  requested index to two bits before translating it, which is why the
  low-colour user-interface colour set in `display-driver.md` section 2 uses
  only values `0..3`. The EGA entry stores the index unchanged.
- **Mode switching.** No driver triggers an extra disk-swap or memory-downgrade
  path. The one memory-conditional path is at startup: a Tandy selection on a
  machine reporting too little memory falls back to the CGA driver, which also
  moves that session to the low-colour asset family.

What remains outside the v1 contract is the exact per-driver pixel conversion:
how a given `.4` record is expanded onto CGA's two-bit or Hercules' one-bit
surface, and what the resulting image looks like. No conversion table and no
dithering pass exists anywhere in the original for this; the low-colour art is
authored at its own depth, and each driver's blitters consume it directly. Any
per-driver palette-mapping or ordered-dither table offered for these backends is
a modern reconstruction, not an original behaviour.

## 7. Known Uncertainties

- **Exact CGA palette policy.** *Closed.* An earlier revision of this bullet
  said the v1 contract "does not constrain which selection is used" and asked a
  future CGA implementation to pick a policy. That is withdrawn: the choice is
  not open. The CGA driver's mode-set entry requests the four-colour
  320-by-200 mode and then issues one palette-select call for **palette one** —
  black, cyan, magenta, white — with the background and border black at low
  intensity, and it never issues another. `formats/tiles.md` section 7 and
  `catalogs/tile-catalog.md` section 13 publish the same selection, and this
  document's Section 5.2 rule that nothing reprograms a palette after mode setup
  applies to that driver too. What remains genuinely open is only the *pixel*
  conversion: there is no index-mapping table from the sixteen-colour palette
  down to the four-colour one anywhere in the original, so no such mapping can be
  published as historical behaviour, and the low-colour art is authored at its
  own depth instead.
- **Mode-set fast path.** Some entry paths invoke the mode-set entry with
  the do-real-mode-set flag cleared so that the firmware mode change and
  palette upload are skipped. These paths assume the adapter is already in
  the correct mode; the safe-from-cold-boot path always asserts the flag.
  This is observable through gameplay only in the form of which scenes
  re-issue a mode-set as part of their entry.
- **Page-zero side-effects of firmware mode-set.** Firmware mode-set clears
  video memory as a side effect, so the visible page is blank immediately
  after every full mode-set. Whether a modern implementation reproduces this
  clear is a visual-parity question, not a contract question.

## 8. Sources

This document is a cleanroom prose rewrite from private analysis notes. It
omits assembly, decompiled code, raw lookup tables, driver-internal addresses,
and any source-shaped representation of the original code.

- EGA dispatch ABI, slot inventory, and slot-1 mode-set semantics:
  `u5-decomp/formats/ega-driver.md` and
  `u5-decomp/functions/EGA_DRV/`.
- Back-buffer allocation, plane-image layout, and release semantics:
  `u5-decomp/functions/EGA_DRV/`.
- Asset-segment registration and the in-place packed-to-planar rewrite:
  `u5-decomp/functions/EGA_DRV/` and the
  packed-to-plane helper notes referenced therein.
- Drawing-colour register and pixel-level primitives:
  `u5-decomp/functions/EGA_DRV/`, and
  `u5-decomp/functions/EGA_DRV/`.
- Front-buffer scanline-fill helper (rectangle inner loop):
  `u5-decomp/functions/EGA_DRV/`.
- Packed-to-planar preparation entry and asset-segment layout:
  `u5-decomp/functions/EGA_DRV/` (the note file
  keeps its original filename; the entry is not a codec) and
  `u5-decomp/CORRECTIONS.md`.
- Per-driver hardware modes, framebuffer shapes, drawing-colour reduction,
  asset-family selection, title-band geometry, and the status of the
  packed-to-planar entry in each family:
  `u5-decomp/formats/cga-driver.md`, `u5-decomp/formats/tandy-driver.md`,
  `u5-decomp/formats/hercules-driver.md`,
  `u5-decomp/notes/driver_asset_family_and_ui_colours_2026-08-22.md`, and
  `u5-decomp/functions/INTRO_OVL/`.
- Tile-blit and glyph entries:
  `u5-decomp/functions/EGA_DRV/`.
- Resident screen-descriptor palette table field:
  `u5-decomp/formats/data-ovl.md` (descriptor layout) and
  `u5-decomp/formats/ega-driver.md` (palette-load step in slot 1).
