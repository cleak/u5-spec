# Retractions

This file records every published statement in this repository that a later
revision **withdrew or inverted**. A clarification that only adds detail is not
listed here; a statement an implementer could already have built against, and
which is now wrong, is.

The convention exists because this repository's corrections have historically
arrived inside otherwise-routine edits, where a reader who had already
implemented the earlier text had no reason to re-read the section. Each row
names the affected section, and each affected section also carries a one-line
inline note at the point of the change.

| Date | Document and section | Withdrawn statement | What replaces it |
|---|---|---|---|
| 2026-08-26 | `systems/town-mode.md` section 13 | The harpsichord's ten keys are a **descending** major scale, digit `1` highest and digit `0` lowest. | The scale **ascends**: digit `1` is the lowest note, digit `8` is an octave **above** it, and `9` and `0` continue two whole tones further. The interval structure (semitone steps between `3`/`4` and `7`/`8`, major-scale pattern) is unchanged; only the direction is inverted. See `town-mode.md` section 13.1. |
| 2026-08-26 | `systems/audio.md` section 3 | Ctrl-S changes output, not cadence, for every resident effect; a muted software envelope still runs its iteration loop. | Still true of every effect reached through the generator, but **not** of the harpsichord, whose handler skips the sound call entirely when sound is off and therefore loses the whole of each note's hold. See `audio.md` section 3 and `town-mode.md` section 13.1. |
| 2026-08-26 | `systems/audio.md` section 6 | Variant 6's confirmed uses include "Kill/Slay Living". | The combat-only attack spells play **no shared variant at all**. Kill is a circle-7 spell and never reaches the shared dispatcher; it plays a circle-scaled rumble lead plus a descending impact glissando. See `audio.md` section 6.1. |
| 2026-08-26 | `systems/audio.md` section 7.3 | The **previous wind state** selects the variant: Calm-to-direction plays variant 2, direction-to-anything plays variant 1. | The selector is a **caller tag**, not the old wind. Every accepted wind change cast as the *spell* plays variant 2; the *scroll* plays variant 1. The old and new compass directions do not participate. See `audio.md` section 7.3 and `weather.md` section 3, which carried the same wrong sentence. |
| 2026-08-26 | `systems/audio.md` section 7.3 | The accepted setter is a silent no-op when both the old and requested wind are Calm. | The silent no-op is a property of the spell path requesting direction "none"; whether it is additionally conditioned on the current wind already being calm is now marked **unresolved**. See `audio.md` section 7.3. |
| 2026-08-26 | `systems/audio.md` section 7.4 | A rejected **town** movement and a rejected **combat** step-or-attack beep. | A rejected **overworld** step beeps too, with the identical recipe; the earlier sentence under-scoped by one mode. A rejected **dungeon** step is silent and must not be given the beep. See `audio.md` section 7.4. |
| 2026-08-26 | `systems/audio.md` section 8.1 | The ring-vanishes cue is skipped by "a cancelled confirmation". | There is no confirmation prompt. Destruction is a 1-in-16 random roll with no player interaction, on both the Ready path and the terrain-combat-entry path. See `audio.md` section 8.1. |
| 2026-08-26 | `systems/display-driver-abi.md` section 9.6 | On each checked visit the gated dissolve "emits one short percussive speaker click", and an abort leaves "the speaker silenced" as part of the per-click behaviour. | The speaker is enabled at the first click and **nothing disables it until the dissolve exits**. Each click *retunes* a continuously running square wave; it is one continuous waveform whose frequency is randomised at the click cadence, not a train of discrete clicks. The single silencing point is the dissolve's shared exit, reached by both abort and completion. See `audio.md` section 8.6.1. |
| 2026-08-26 | `systems/timing.md` section 4 | The start/menu logo reveal "has no wait of any kind in its inner loop" and is close to instantaneous on a modern host. | True of the ungated dissolve. The **first, gated** dissolve pays a short calibrated hold per click — roughly 50 to 60 microseconds on every second visited pixel — plus the retune, and is modelled at several seconds for the full-width rectangle. See `audio.md` section 8.6.1. |
