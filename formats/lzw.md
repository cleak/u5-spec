# Shared LZW Envelope

## 1. Scope

Several Ultima V graphics resources use a shared LZW-compressed envelope before
their format-specific payload begins. This document specifies only that
envelope and compression dialect. The decompressed payload layout is owned by
the consuming file-format spec, such as `formats/tiles.md`.

This envelope applies to the paired `.16` and `.4` graphics archive family and
to the standalone bitmap family: `TITLE.BIT`, `BRITISH.BIT`, and
`PROPORT.PCS`. The one documented exception is `WD.BIT`, which stores its
payload raw with no envelope. Earlier revisions of this document excluded the
whole `.BIT` and `.PCS` family from the envelope; that exclusion was wrong.

## 2. Envelope

Each compressed resource starts with a four-byte little-endian unsigned length,
followed immediately by the LZW code stream.

| Field | Size | Meaning |
|---|---:|---|
| Decoded length | 4 bytes | Exact number of bytes expected after decompression. |
| LZW stream | remaining bytes | Variable-width packed codes. |

There is no magic number, version field, checksum, per-file flag byte, or
trailing footer. A compatible reader should allocate or bounds-check against the
declared decoded length before interpreting the decompressed payload.

## 3. Code Stream

The dialect is the GIF-style LZW variant used by contemporary CompuServe GIF
decoders:

- Codes start at nine bits.
- Code width grows by one bit as the dictionary fills.
- Code width is capped at twelve bits.
- Codes are packed least-significant-bit first within the byte stream.
- The dictionary can hold 4096 entries.

The reserved codes are:

| Code | Meaning |
|---:|---|
| 256 | Clear dictionary and return to nine-bit codes. |
| 257 | End of stream. |
| 258 and above | First dynamically built dictionary entries. |

After a clear code, the next newly emitted dictionary entry uses the first
dynamic code. A decoder must handle the standard self-reference case where a
code names the next dictionary entry being created.

## 4. Completion Rules

The end code terminates decoding. The decoded byte count must match the
four-byte decoded length in the envelope. Extra unread bytes after a valid end
code are not part of the decompressed payload; missing bytes, a missing end
code, an overlong expansion, or a decoded-length mismatch are content errors.

A clean implementation does not need to reproduce the original loader or driver
memory layout. It only needs to reproduce the byte-level code interpretation
above and feed the exact decoded payload to the owning format parser.

## 5. Consumers

- `formats/tiles.md` owns the paired `.16` and `.4` graphics archive payloads
  after this envelope is removed.
- `systems/display-driver.md` and `systems/display-driver-abi.md` own the
  display conversion after graphics payloads are decoded.
- `formats/bit.md` owns the one-bit-per-pixel sub-image list carried by
  `TITLE.BIT`, `BRITISH.BIT`, and (raw, without this envelope) `WD.BIT`.
- `formats/font-pcs.md` owns the same sub-image list as used for the
  proportional font glyphs in `PROPORT.PCS`.

## 6. Sources

Source provenance: derived from private analysis notes
`u5-decomp/formats/tile-graphics.md` and
`u5-decomp/notes/retrace_view-vis-font_2026-08-22.md` section 1 (which
validates the decoder against a `.16` archive and then against the three
enveloped `.BIT`/`.PCS` files), cross-checked against the later generic
file-read correction in
`u5-decomp/functions/ULTIMA_EXE/`, which confirms that
plain `.DAT`, `.GAM`, and `.OOL` file reads are not LZW decoding paths.

This public spec describes the compression contract in clean prose and does not
include decompiled code, assembly excerpts, raw compressed data, or private
address tables.
