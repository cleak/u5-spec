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

## 3. Seeding and Re-seeding

The generator has exactly one state word, and exactly one primitive that
assigns it. That primitive performs a plain assignment: it takes a 16-bit value
and installs it as the new state with no mixing, validation, or return value.
Every seeding event in the game is a call to that primitive; nothing else
writes the state except the generator's own advance step.

**Shipped initial value.** In the shipped initialised data image the state word
is zero. If nothing seeded it, every fresh run would replay an identical roll
sequence.

**Boot seed.** The program seeds the state once per run, during the intro
sequence, on the straight-line path into the intro menu — that is, before the
player chooses New Game, Journey Onward, or Transfer. The seed value is derived
from the host time-of-day clock: the hour, minute, second, and
hundredth-of-a-second fields are shifted by differing amounts, summed, combined
with a fixed mixing constant, and then **masked to twelve bits**. The seed is
therefore a value in `0..4095`.

Two consequences follow, and both are part of the contract:

- Fresh games are *not* identical, but they are only 4,096 ways distinct. The
  state word holds sixteen bits; only twelve of them are ever seeded at boot.
- Two runs that reach the intro menu within the same host clock tick receive
  the same seed and replay the same roll sequence. (The underlying DOS clock
  advances in roughly 55-millisecond steps, so the effective resolution is
  coarser than the hundredth-of-a-second field suggests.)

**Play-time re-seeds.** Four further events re-assign the state during a
session; the last of them seeds twice, in immediate succession:

| Event | Seed source | Effect |
|---|---|---|
| An hour elapses while camping | Host clock | Fresh entropy immediately before the camp-event roll. |
| A conversation's script runner reaches its coin-flip step | Host clock | Fresh entropy immediately before that coin flip. |
| A conversation in the settlement where the Shadowlord of Falsehood is hiding reaches its theft step | Host clock | Fresh entropy immediately before the roll that chooses which item is stolen. This is that one Shadowlord's conversation effect, not a generic conversation teardown. |
| A location that is currently hiding a Shadowlord is entered, or one of its floors is loaded | Calendar day-of-month | Deterministic; it makes that location's farmland and orchard blight a pure function of the day byte and the floor content, so the pattern is identical for every load of that floor on the same in-game day. It does not fire on entry to an ordinary location: the pass that seeds it returns immediately when no Shadowlord is resident. Immediately after the blight walk the same pass re-seeds from the host clock, so the deterministic seed does not leak into later gameplay rolls. |

Note that the pair around the blight walk is a deterministic seed followed by a
clock re-seed, **not** a save-and-restore of the previous stream position. The
state in effect before the walk is lost. `systems/town-mode.md` section 3 owns
the blight's gate and call sites.

**Determinism contract.** Because ordinary gameplay events re-seed from
the host clock, the roll stream is not reproducible from game state alone. The
state word is not part of the saved game, and even if it were, re-seeding would
destroy reproducibility at the next camp hour or conversation. An
implementation cannot promise save-deterministic randomness and simultaneously
match the original's behaviour; a port that wants a reproducible stream is
making a deliberate, documented divergence.

## 4. Usage Notes

The public name `make_tag` in some private notes is misleading. The routine is
the engine-wide PRNG range primitive. A call such as `random(1, 30)` consumes one
state advance and returns one value from the inclusive 30-sided range.

**The audio jitter source is a separate stream and must not be conflated with
the game PRNG.** The PC-speaker rumble effect carries its own private copy of
the same state-advance formula operating on its own state word. That word ships
with a non-zero value in the initialised data image and is *never* seeded by
anything, so speaker jitter is fully deterministic from boot, is identical on
every run, and shares nothing with game-logic randomness. Conversely, the
clock-sampling helper described in section 3 is not an audio helper at all:
every one of its uses feeds the game PRNG's seed primitive. A deterministic
port may replace the speaker jitter stream freely without affecting gameplay
RNG parity, but must not reuse the game PRNG for it, and must not skip the
clock seeding of the game PRNG on the mistaken assumption that it is
presentation-only.

The generator is entirely integer arithmetic. No floating point, heap allocation,
or formatted I/O is involved.

## 5. Sources

This public description is a cleanroom prose rewrite from private analysis. It
does not reproduce decompiled source, assembly listings, raw bytes, or private
address tables.

- PRNG range helper semantics and state-advance formula -- `u5-decomp/functions/ULTIMA_EXE/0x2092_prng_range.md`.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/0x207E_prng_seed.md` -- the state-assignment
  primitive, its shipped zero initial value, the complete list of seeding
  events, and the boot-seed placement in the intro sequence.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/0x2056_prng_time_seed.md` -- the clock-derived
  seed value and its twelve-bit width. This note supersedes the earlier
  "sound-only jitter" characterisation of that helper.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/0x223C_pc_speaker_random_rumble.md` -- the
  separate, never-seeded audio jitter state.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/TOWN_OVL/0x0212_town_load_npc_waypoints.md` -- the
  deterministic day-of-month seed taken by the farmland blight pass, its
  resident-Shadowlord gate, and the clock re-seed that follows it.
- Source provenance: derived from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_shrine-prng-look-saduj.md`.
- Earlier engine-wide call-site identification for the routine historically named `make_tag` -- `u5-decomp/functions/ULTIMA_EXE/0xCDAC_per_turn_cleanup.md`.
- Library fingerprint confirming integer-only game logic and absence of floating-point/runtime allocation dependencies -- `u5-decomp/functions/ULTIMA_EXE/_LIBRARY_FIDB.md`.
