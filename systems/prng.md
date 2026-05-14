# PRNG

## 1. Scope

Ultima V uses a shared integer range generator for game-logic randomness:
encounter rolls, Shadowlord relocation, combat placement and AI choices, random
damage, shop and dialogue flourishes, and similar small decisions. It is a
deterministic resident-state generator, not a cryptographic RNG and not a
floating-point routine.

## 2. Range Contract

Callers request an inclusive integer range `[low, high]`. For ordinary valid
ranges where `low <= high`, the generator advances one 16-bit resident state
word, masks the advanced state to a non-negative 15-bit value, reduces it by
modulo `high - low + 1`, and adds `low`. The result is therefore always in the
requested inclusive range.

The state advance has two steps. First, add `0x9248` to the current 16-bit
state, rotate that 16-bit sum right by three bits, and XOR the rotated value
with `0x9248`. Second, add `0x0011` to that intermediate value, keeping the
result as the new 16-bit state word.

The returned value is the low endpoint plus the advanced state's low
fifteen-bit non-negative value reduced modulo the inclusive range width:
`low + ((state & 0x7FFF) modulo (high - low + 1))`.

The modulo step means ranges whose size does not divide 32768 have the normal
small modulo bias. Compatible implementations should preserve that bias for
byte-for-byte gameplay parity.

The helper has no caller-argument guard. It stores the advanced PRNG state
before the range-width reduction. If a caller supplies endpoints whose 16-bit
inclusive width is zero, the original helper reaches its integer division with
a zero divisor after consuming that state advance. Parity code should not
silently clamp, swap, or repair such a range unless it intentionally diverges
from the original edge behavior.

## 3. Usage Notes

The public name `make_tag` in some private notes is misleading. The routine is
the engine-wide PRNG range primitive. A call such as `random(1, 30)` consumes one
state advance and returns one value from the inclusive 30-sided range.

Sound effects have a separate randomness source for short PC-speaker jitter and
ambient rumble variation. That source samples the live DOS clock and derives a
small one-shot value for audio variation; it is not the iterating game-logic
range PRNG, does not share this state word, and must not be used for encounter,
combat, NPC, shop, or quest randomness. A deterministic port may replace the
sound-only jitter source without changing gameplay RNG parity.

The generator is entirely integer arithmetic. No floating point, heap allocation,
or formatted I/O is involved.

## 4. Sources

This public description is a cleanroom prose rewrite from private analysis. It
does not reproduce decompiled source, assembly listings, raw bytes, or private
address tables.

- PRNG range helper semantics and state-advance formula -- `u5-decomp/functions/ULTIMA_EXE/0x2092_prng_range.md`.
- Sound-only DOS-clock jitter source used by PC-speaker effects -- `u5-decomp/functions/ULTIMA_EXE/0x2056_prng_time_seed.md`.
- Earlier engine-wide call-site identification for the routine historically named `make_tag` -- `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- Library fingerprint confirming integer-only game logic and absence of floating-point/runtime allocation dependencies -- `u5-decomp/functions/ULTIMA_EXE/_LIBRARY_FIDB.md`.
