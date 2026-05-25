# Standalone Bitmap Files (`.BIT`)

Format specification for Ultima V's standalone `.BIT` image resources in the
IBM PC DOS display-driver path.

## 1. Overview

The `.BIT` files are not members of the paired `.16`/`.4` graphics archive
family, and they do not use the shared LZW envelope described in
`formats/tiles.md`. The updated EGA driver analysis shows that the `.BIT`
family uses the display driver's sparse strip resource format. The driver
walks a pointer table inside the loaded file, decodes each nonempty strip, and
converts the strip to the active display representation.

Known `.BIT` files:

| File | Role | Driver-resource form |
|---|---|---|
| `TITLE.BIT` | Main title-screen lettering/artwork resource | Sparse strip table |
| `BRITISH.BIT` | Lord British title-sequence portrait/signature artwork | Sparse strip table |
| `WD.BIT` | "Warriors of Destiny" story lettering | Sparse strip table with one populated strip |

The same high-level resource family is also used by `PROPORT.PCS`; see
`formats/font-pcs.md`.

## 2. Relationship To Other Graphics

Ultima V has two separate compressed graphics families:

| Family | Files | Compression/container owner |
|---|---|---|
| Paired graphics archives | `TILES.16`, `STARTSC.16`, `STORY1.16`, matching `.4` files, etc. | Shared LZW envelope plus archive-specific post-LZW layout. |
| Driver bitmap resources | `TITLE.BIT`, `BRITISH.BIT`, `WD.BIT`, `PROPORT.PCS` | Display-driver sparse strip table. |

Do not feed `.BIT` files to the LZW decoder. Their first word is an entry
count for the driver resource table, not a decoded-length field.

Some local re-release or tool-produced asset folders may contain pre-decoded
bitmap bodies under the same filenames. Those files are not the canonical
Ultima V on-disk `.BIT` format and are not required for the v1 clean resource
contract. A strict original-data validator should identify them as
noncanonical rather than trying to reinterpret this format. Engines that choose
to support such local packaging variants may add an implementation-local
fallback loader, but this spec does not define a byte-compatible predicate or
body layout for those variants because they are outside the shipped sparse
resource format.

## 3. File Layout

Every identified `.BIT` file starts with a sparse pointer table:

| Field | Width | Meaning |
|---|---:|---|
| Entry count | 2 bytes | Number of pointer-table entries scanned by the driver. |
| Entries | `entry_count * 4` bytes | Each entry is a pointer word followed by a metadata word. |
| Strip bodies | variable | Pixel strip records pointed to by nonzero pointer words. |

Pointer-table entry:

| Field | Width | Meaning |
|---|---:|---|
| Strip pointer | 2 bytes | Byte offset from the start of the file to a strip body; zero means no strip. |
| Metadata | 2 bytes | Not consumed during pointer-table scanning. Preserve when round-tripping; if a strip pointer targets this word, treat it as part of that strip body. |

Strip body:

| Field | Width | Meaning |
|---|---:|---|
| Width-related word | 2 bytes | Source width parameter converted by the driver into packed bytes per row. |
| Row count | 2 bytes | Number of rows in this strip. |
| Pixel payload | variable | Packed source bytes consumed by the display-driver decoder. |

For the EGA baseline, the width-related word is converted to the number of
packed bytes per row across the four planes, rounded up to a four-byte
boundary. The strip payload is then transformed into planar EGA data by the
driver.

## 4. File-Specific Notes

### 4.1 `TITLE.BIT`

`TITLE.BIT` is a sparse multi-strip resource. Its entry count is much larger
than the number of strips that visibly draw; zero pointer entries are skipped.
The title intro loads the file, hands the loaded segment to the display-driver
bitmap path, and lets the driver walk the table.

The title sequence still owns the visible flow: clear/configure the title
surface, draw the title resource, draw the Lord British resource and path
animation, then enter the menu/start-screen flow. The file format does not
encode menu timing, input handling, or the title/menu idle animation.

For intro-title compatibility, the resource's decoded records are not a
standalone draw list. `systems/intro.md` names the only title records that
become visible and the order in which they are drawn. In particular, the intro
title helper draws `TITLE.BIT` records `0..6` cumulatively onto one cleared
title surface, then the later title phase draws only the explicitly named
records `7`, `8`, and `9` around the signature sequence. A renderer that draws
every decoded record from this file as a simultaneous sprite layer will produce
spliced duplicate title marks.

### 4.2 `BRITISH.BIT`

`BRITISH.BIT` uses the same sparse strip resource model as `TITLE.BIT`. It is
drawn during the title sequence as a caller-selected record, not as an
automatic overlay for every decoded record. In the intro title flow,
`BRITISH.PTH` supplies the animated pen movement first, and `BRITISH.BIT`
record `0` is drawn afterward as the completed bitmap overlay. A renderer
should not put `BRITISH.BIT` under the path strokes unless it is deliberately
rendering a non-compatible preview.

### 4.3 `WD.BIT`

`WD.BIT` is no longer treated as a separate raw bitmap header. Its leading
words fit the same sparse strip model:

| Resource fact | Meaning |
|---|---|
| Entry count is one | The driver scans one pointer-table entry. |
| First pointer targets offset 4 | In this single-entry file, the pointed strip body starts at the entry's metadata word. |
| The metadata word also serves as the strip width word | This overlap is valid for this resource because the EGA decoder follows the pointer and reads the strip body from there. |
| The strip row count is 49 | The visible lettering is 49 rows tall. |

The practical visible role is unchanged: the resource supplies the "Warriors
of Destiny" lettering used by the story/intro presentation.

## 5. Rendering Behaviour

The resident intro and story code load a `.BIT` file into memory and call the
display-driver bitmap entry. The EGA driver implements this entry and then:

1. Reads the resource entry count.
2. Iterates pointer-table entries in order.
3. Skips entries with a zero strip pointer.
4. For each nonzero strip pointer, reads the strip width parameter and row
   count.
5. Converts the strip payload into the driver's native pixel representation.
6. Draws the strip according to the current driver/caller state.

The caller does not interpret `.BIT` as a `.16`/`.4` archive and does not
field-walk the strip bodies itself in normal gameplay.

The CGA, Hercules, and Tandy driver entries for this compressed-bitmap path are
stubs in the analyzed baseline. On those historical backends, callers can reach
the same high-level flow but the compressed bitmap entry returns without drawing
the title, portrait, poster, proportional-font, or end-scroll resources. A
modern clean implementation may still render substitute assets for those modes,
but binary-compatible driver behaviour treats the non-EGA compressed-bitmap
entry as no-op.

## 6. Validation And Error Handling

A strict loader or inspection tool should:

- Require the file to contain at least the entry-count word.
- Treat the entry count as the number of four-byte table entries.
- Permit zero pointers as skipped entries.
- Require nonzero strip pointers to land inside the file or inside the loaded
  resource image prepared for driver decoding.
- Require every decoded strip to have nonzero row count before rendering.
- Preserve pointer-entry metadata even if the EGA renderer ignores it.

The original driver can encounter over-allocated pointer tables where most
entries are zero. A clean implementation should not reject a resource merely
because the entry count is larger than the number of populated strips. When
emulating the original heap-load path, the loaded resource image may include
zero-filled padding beyond the byte-exact file; over-allocated table entries
that read as zero remain skipped. Inspection tools may enforce stricter bounds
for nonzero strip pointers, but they should not use file length alone to reject
large entry counts in known resources.

## 7. Implementation Notes

- Keep the `.BIT` loader separate from the paired `.16`/`.4` LZW decoder.
- Use `systems/display-driver-abi.md` for the corrected dispatch mapping:
  `0x3F` fills a rectangle; `0x42` decodes/draws driver bitmap resources.
- A modern renderer can convert populated strips directly to an RGBA or indexed
  surface, but the result must match the EGA baseline's strip order, row count,
  clipping, and colour interpretation.
- Treat decoded records as addressable resources. The caller decides which
  records are drawn, where they are placed, and whether earlier screen contents
  remain visible.
- Replacement title/menu idle frames are not stored in `.BIT`; those are
  driver-local animation frames described in `systems/display-driver.md`.

## 8. Boundaries And Residuals

**Pointer-entry metadata.** The EGA bitmap decoder does not consume the second
word in each pointer-table entry. Preserve it when round-tripping resources,
but do not give it runtime rendering semantics unless a separate authoring-tool
spec is added.

**Non-EGA substitute art.** The analyzed CGA, Hercules, and Tandy drivers stub
the compressed-bitmap entry. Rendering substitute art for those backends is a
modern enhancement, not a baseline driver-codec rule.

**Title and story presentation.** This format owns the sparse strip container
and strip decode contract. The intro system owns the higher-level title flow,
story slide sequence, rectangle transitions, waits, and input handling.

## 9. Cross-References

- EGA display-driver ABI and driver bitmap entry:
  `systems/display-driver-abi.md`.
- Semantic display contract and title/menu idle animation:
  `systems/display-driver.md`.
- Intro title, menu, and story flow: `systems/intro.md`.
- Lord British path animation: `formats/pth.md`.
- Paired `.16`/`.4` screen-panel graphics: `formats/tiles.md`.
- Proportional font sibling resource: `formats/font-pcs.md`.

## 10. Sources

Cleanroom prose derived from private analysis notes. This document does not
include decompiled source, assembly excerpts, raw address tables, or raw bitmap
data.

- Driver-compressed bitmap entry and sparse strip resource:
  `u5-decomp/functions/EGA_DRV/0x1226_draw_compressed_bitmap.md`.
- EGA driver ABI overview and corrected dispatch mapping:
  `u5-decomp/formats/ega-driver.md`.
- Intro title and story consumers:
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md` and
  `u5-decomp/functions/INTRO_OVL/0x014E_intro_slide_loop.md`.
- Intro title record visibility and ordering:
  `u5-decomp/functions/INTRO_OVL/0x0986_intro_main.md` and fresh local
  resident display-helper verification.
