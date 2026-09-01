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

### Host-clock seed transform

Every host-clock seeding event performs one time-of-day read that returns all
four fields together: hour `h`, minute `m`, second `s`, and hundredths `c`.
The fields are not read separately. Treat each field and each shifted result as
an unsigned byte, so `byte(x)` below means `x modulo 256`.

Form two unsigned 16-bit words:

```text
seconds_and_hundredths = (byte(s << 3) << 8) | byte(c)
hours_and_minutes      = (byte(h << 1) << 8) | byte(m << 2)
```

Then compute:

```text
sum16 = (seconds_and_hundredths + hours_and_minutes) modulo 65536
seed  = (sum16 XOR 0x91EB) AND 0x0FFF
```

Thus the shifts are hour by one bit, minute by two, second by three, and
hundredths by zero. The byte-width shifts happen before the fields are packed;
in particular, shifting seconds can discard high bits. The packed-word
addition is 16-bit and wraps, including an ordinary carry from the low byte
into the high byte. The twelve-bit mask is applied only after the XOR, and the
result is in `0..4095`.

Reference vectors:

| Host time | Seconds/hundredths word | Hour/minute word | Wrapped sum | Seed |
|---|---:|---:|---:|---:|
| `00:00:00.00` | `0x0000` | `0x0000` | `0x0000` | `0x1EB` (491) |
| `12:34:56.78` | `0xC04E` | `0x1888` | `0xD8D6` | `0x93D` (2365) |
| `23:59:59.99` | `0xD863` | `0x2EEC` | `0x074F` | `0x6A4` (1700) |

The last vector exercises both truncation of the shifted seconds byte and
overflow of the 16-bit packed-word addition.

### Boot placement

The program applies this transform and assigns the resulting state once per
run in the intro controller. On the normal path, the sample occurs after title
and start-screen preparation; the early Journey-Onward path jumps directly to
the same sample rather than bypassing it. In both cases it is before the first
intro-menu draw and key poll. Returning to the menu from a menu sub-flow resumes
after the seed assignment and does not sample again.

Two consequences follow, and both are part of the contract:

- Fresh games are *not* identical, but they are only 4,096 ways distinct. The
  state word holds sixteen bits; only twelve of them are ever seeded at boot.
- Two runs that reach the intro menu within the same host clock tick receive
  the same seed and replay the same roll sequence. (The underlying DOS clock
  advances in roughly 55-millisecond steps, so the effective resolution is
  coarser than the hundredth-of-a-second field suggests.)

### Play-time placement

Four further event classes re-assign the state during a session; the last of
them assigns twice around its terrain walk:

| Event | Seed source | Effect |
|---|---|---|
| Camping hour-change interruption | Host clock | When a wilderness-camp step observes that the game hour changed, it first consumes `random(0, 63)` from the state already in force. Results `1..63` continue without a clock read. Only result `0` samples the host clock, assigns the new seed, and immediately consumes `random(0, 7)` to select the sleep-ambush row. It therefore does **not** re-seed on every elapsed hour. This path is unrelated to the later completed-camp Lord British gate: the final `random(0, 99)` draw has no adjacent clock sample or seed assignment. |
| Stranger-conversation opener | Host clock | After printing the NPC description, the opener tests whether that NPC knows the party. A known NPC goes directly to its greeting without sampling. A stranger samples and assigns immediately before the `random(0, 1)` introduction coin flip. |
| Falsehood theft cleanup | Host clock | Only in the settlement where the Shadowlord of Falsehood is resident. After the stolen-goods line and fixed sound, cleanup samples and assigns before it tests the party's inventory categories. The re-seed therefore occurs even when the eventual loss is selected by a deterministic descending scan rather than a random choice. |
| Shadowlord farmland/orchard blight | Calendar day-of-month, then host clock | The gated pass first assigns the in-game day-of-month, walks all 1,024 terrain cells, and marks the viewport dirty. It then performs one fresh host-clock read and assignment immediately before returning. Each invocation samples afresh; this is not a restoration of the state that preceded the pass. The entire pair is skipped when no living Shadowlord is resident. |

Note that the pair around the blight walk is a deterministic seed followed by a
clock re-seed, **not** a save-and-restore of the previous stream position. The
state in effect before the walk is lost. `systems/town-mode.md` section 3 owns
the blight's gate and call sites.

**Determinism contract.** Because ordinary gameplay events re-seed from
the host clock, the roll stream is not reproducible from game state alone. The
state word is not part of the saved game, and even if it were, re-seeding would
destroy reproducibility at the next qualifying camp interruption, stranger
opener, Falsehood theft, or blight pass. An
implementation cannot promise save-deterministic randomness and simultaneously
match the original's behaviour; a port that wants a reproducible stream is
making a deliberate, documented divergence.

## 4. Usage Notes

The public name `make_tag` in some private notes is misleading. The routine is
the engine-wide PRNG range primitive. A call such as `random(1, 30)` consumes one
state advance and returns one value from the inclusive 30-sided range.

**The random-rumble audio jitter source is a separate stream and must not be
conflated with the game PRNG.** That effect carries its own private copy of the
same state-advance formula operating on its own state word. The word ships with
a non-zero value in the initialised data image and is never seeded, so this
particular speaker jitter is deterministic from boot and shares nothing with
game-logic randomness. A deterministic port may replace that stream without
affecting gameplay RNG parity, but must not reuse the game PRNG for it.

This separation does not apply to every randomized sound. The major-event
full-viewport flash/rumble consumes one gameplay-PRNG draw for each of its
1,856 drawing bands, including when sound is muted. Those draws are part of
gameplay RNG parity and must be preserved even by a silent frontend. See
`audio.md` for the event and mute contract.

Conversely, the clock-sampling helper described in section 3 is not an audio
helper at all: every one of its uses feeds the game PRNG's seed primitive. A
compatible implementation must not skip that seeding on the mistaken
assumption that it is presentation-only.

**Rendering and idling perturb the gameplay stream, so it is not reproducible
from the player's action sequence alone.** Two per-pass consumers run on the
idle path, before any command is entered:

- Every viewport composite pass consumes **one draw per qualifying actor** —
  each actor standing on the furniture terrain that selects a four-frame merged
  sprite (`systems/visibility.md` Section 8.1). That is one draw per such actor
  per idle pass, on the order of eighteen passes a second.
- The per-pass wind check draws once in the common case. On an
  uncommon result it enters a retry loop that draws in pairs until it settles, so
  its draw count per invocation is one, two, or an unbounded sequence above that.
  **No maximum is published, and an engine must not assume one** - the loop has no
  static bound and its real-world distribution needs live capture
  (`systems/animation.md` Section 13.2).

Neither is gated on player input, so how long the player stood at a prompt
changes the stream position of the next combat roll. Any engine aiming at
deterministic replay must either reproduce those idle draws exactly, with the
same idle cadence, or accept that its stream will diverge from the original's;
it cannot get parity by seeding alone.

The generator is entirely integer arithmetic. No floating point, heap allocation,
or formatted I/O is involved.

## 5. Sources

This public description is a cleanroom prose rewrite from private analysis. It
does not reproduce decompiled source, assembly listings, raw bytes, or private
address tables.

- PRNG range helper semantics and state-advance formula -- `u5-decomp/functions/ULTIMA_EXE/`.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/` -- the state-assignment
  primitive, its shipped zero initial value, the complete list of seeding
  events, and the boot-seed placement in the intro sequence.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/` -- the clock-derived
  seed value and its twelve-bit width. This note supersedes the earlier
  "sound-only jitter" characterisation of that helper.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/ULTIMA_EXE/` -- the
  separate, never-seeded audio jitter state.
- Source provenance: derived from private analysis note
  `u5-decomp/functions/TOWN_OVL/` -- the
  deterministic day-of-month seed taken by the farmland blight pass, its
  resident-Shadowlord gate, and the clock re-seed that follows it.
- Source provenance: derived from private analysis in `u5-decomp/notes/`.
- Earlier engine-wide call-site identification for the routine historically named `make_tag` -- `u5-decomp/functions/ULTIMA_EXE/`.
- Library fingerprint confirming integer-only game logic and absence of floating-point/runtime allocation dependencies -- `u5-decomp/functions/ULTIMA_EXE/`.
