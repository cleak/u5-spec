# Ultima V Extraction Inventory

Master tracking checklist for the decompilation and documentation phase, derived from the actual GOG release file listing.

Status legend:

- ⬜ Not started
- 🟡 In progress / partial reference exists
- ✅ Spec complete
- 🟢 Spec verified by parallel implementation slice
- 🚫 Out of scope (modern engine will not reproduce)

When a row references existing work in `../ninth-virtue`, that is a starting reference and not a finished spec — material from there must be re-derived in this repository's own words and verified against fresh decompilation in `../u5-decomp`.

---

## 1. Code

### 1a. Resident core

| File | Role | Status | Spec doc |
|------|------|--------|----------|
| ULTIMA.EXE | Resident core: main loop, dispatch, stats panel, overlay loader | 🟡 | `systems/main-loop.md` |
| ULTIMA5.COM | Top-level launcher / configuration handoff | ⬜ | `systems/launcher.md` |

ninth-virtue has a function map for ~10 functions in ULTIMA.EXE; bottom-up decomp will extend this to full coverage.

### 1b. Game-mode overlays

Grouped by what they implement, not by alphabetical order.

| File | Role | Status | Spec doc |
|------|------|--------|----------|
| MAINOUT.OVL | Outdoor (overworld and underworld) loop | ⬜ | `systems/overworld.md` |
| OUTSUBS.OVL | Outdoor shared subroutines | ⬜ | `systems/overworld.md` |
| TOWN.OVL | Town and keep interior loop | ⬜ | `systems/town-mode.md` |
| DUNGEON.OVL | First-person dungeon loop | ⬜ | `systems/dungeon-mode.md` |
| DNGLOOK.OVL | Dungeon look / inspection | ⬜ | `systems/dungeon-mode.md` |
| COMBAT.OVL | Combat mode | ⬜ | `systems/combat.md` |
| TALK.OVL | NPC conversation runtime | ⬜ | `systems/conversation.md` |
| NPC.OVL | NPC behavior, scheduling, pathfinding | ⬜ | `systems/npc-schedules.md` |
| SHOPPES.OVL, SHOPPES2.OVL, SHOPPES3.OVL | Shop and trade UI/logic (split across three overlays) | ⬜ | `systems/shops.md` |
| INTRO.OVL | Title sequence and intro story | ⬜ | `systems/intro.md` |
| ENDGAME.OVL | Endgame sequence | ⬜ | `systems/endgame.md` |
| FLAMES.OVL | Fire/torch animation effect | ⬜ | `systems/flame-effect.md` |
| BLCKTHRN.OVL | Blackthorn-related (likely the dream/encounter) | ⬜ | `systems/blackthorn.md` |
| CMDS.OVL | A–Z command dispatch | 🟡 | `systems/commands.md` |
| ZSTATS.OVL | Z-stats character sheet | ⬜ | `systems/character-sheet.md` |
| FONT.OVL | Text rendering and font handling | ⬜ | `systems/font.md` |
| LOOKOBJ.OVL | Look-at-object / inspection text | ⬜ | `systems/look.md` |
| COMSUBS.OVL | Common shared subroutines | ⬜ | `systems/common-subs.md` |
| CAST.OVL, CAST2.OVL | Character creation / questionnaire | ⬜ | `systems/chargen.md` |
| SJOG.OVL | Unknown — investigate during decomp | ⬜ | — |

### 1c. Display drivers

| File | Hardware | Status | Spec doc |
|------|----------|--------|----------|
| CGA.DRV | CGA 4-color | 🚫 | — |
| EGA.DRV | EGA 16-color | 🟡 | `formats/ega-driver.md` |
| HER.DRV | Hercules monochrome | 🚫 | — |
| T1K.DRV | Tandy 1000 16-color | 🚫 | — |

The modern engine will render in software/GPU and ignore CGA/Hercules/Tandy. Only EGA logic is worth documenting (palette, dirty rectangles, page flipping if any).

### 1d. Sound drivers

| Files | Hardware | Status |
|-------|----------|--------|
| ADLIB.{ADD,ADV}, ADLIBG.{ADD,ADV} | AdLib / AdLib Gold | 🚫 |
| SBFM, SBP1FM, SBP2FM, SBAWE32 | Sound Blaster family | 🚫 |
| MT32MPU, SC32MPU | Roland MT-32 / Sound Canvas via MPU-401 | 🚫 |
| GENMID, GF1MIDI, VESAMID | Generic MIDI / Gravis Ultrasound / VESA | 🚫 |
| PASFM, PASOPL | Pro Audio Spectrum | 🚫 |
| PCSPKR | PC speaker | 🚫 |
| WSS | Windows Sound System | 🚫 |
| SENSAT, MULTISND, ARIAXMID | Other AIL drivers | 🚫 |
| MIDPAK.{COM,AD,ADV}, T/S/P/CMIDPAK.COM | Miles AIL MIDPAK family | 🚫 |
| FAT.OPL | AdLib instrument bank | 🚫 |

The modern engine will render audio with a contemporary stack; only the music data format (XMI) needs to be specified.

### 1e. DOS extender / runtime (out of scope)

| Files | Role | Status |
|-------|------|--------|
| CWSDPMI, CWSDPR0, CWSDSTR0, CWSDSTUB, CWSPARAM | Causeway DPMI server / stubs | 🚫 |
| SETM.EXE | Sound configuration utility | 🚫 |
| u5cfg.exe, u5data.exe, unins000.* | GOG installer/config tools (not original) | 🚫 |

---

## 2. Data — maps and combat arenas

| File | Contents | Status | Spec doc |
|------|----------|--------|----------|
| BRIT.DAT | Britannia overworld | ⬜ | `formats/brit-dat.md` |
| UNDER.DAT | Underworld | ⬜ | `formats/under-dat.md` |
| DATA.OVL | Shared map metadata / index (verify) | ⬜ | `formats/data-ovl.md` |
| CASTLE.DAT | Castle interior maps (Lord British's, Blackthorn's) | ⬜ | `formats/location-dat.md` |
| KEEP.DAT | Keep maps (Stonegate, Serpent's Hold, Lycaeum, etc.) | ⬜ | `formats/location-dat.md` |
| TOWNE.DAT | Town maps (Britain, Trinsic, Minoc, etc.) | ⬜ | `formats/location-dat.md` |
| DWELLING.DAT | Dwelling-class maps (Yew, Cove, Empath Abbey, etc.) | ⬜ | `formats/location-dat.md` |
| MISCMAPS.DAT | Miscellaneous small maps | ⬜ | `formats/miscmaps-dat.md` |
| DUNGEON.DAT | Dungeon levels (3D wireframe) | ⬜ | `formats/dungeon-dat.md` |
| BRIT.CBT | Combat arenas indexed by overworld terrain | ⬜ | `formats/cbt.md` |
| DUNGEON.CBT | Combat arenas for dungeon encounters | ⬜ | `formats/cbt.md` |

The four-class location grouping (CASTLE / KEEP / TOWNE / DWELLING) is shared structure: each class has DAT + NPC + TLK in lockstep. The format spec at `formats/location-dat.md` should describe the shared layout once, with per-class specifics as deltas.

## 3. Data — NPCs, schedules, dialogue

| File | Contents | Status | Spec doc |
|------|----------|--------|----------|
| CASTLE.NPC, KEEP.NPC, TOWNE.NPC, DWELLING.NPC | NPC roster, position, schedule, conversation index per location | ⬜ | `formats/npc.md` |
| CASTLE.TLK, KEEP.TLK, TOWNE.TLK, DWELLING.TLK | Keyword-driven dialogue trees per location class | ⬜ | `formats/tlk.md` |
| BRITISH.PTH | Path data, likely for Lord British's specific schedule | ⬜ | `formats/pth.md` |

Schedules and pathfinding probably live in `NPC.OVL` operating on `*.NPC` and `*.PTH` data. The format spec and the `systems/npc-schedules.md` engine spec must be co-developed.

## 4. Data — text and lookup tables

| File | Contents | Status | Spec doc |
|------|----------|--------|----------|
| LOOK2.DAT | Tile / terrain look strings | ⬜ | `formats/look2-dat.md` |
| SIGNS.DAT | Sign and placard text | ⬜ | `formats/signs-dat.md` |
| KARMA.DAT | Karma adjustment table per action | ⬜ | `formats/karma-dat.md` |
| STORY.DAT | Intro/story text screens | ⬜ | `formats/story-dat.md` |
| QUESTION.DAT | Character creation questionnaire | ⬜ | `formats/question-dat.md` |
| ENDMSG.DAT | Endgame messages | ⬜ | `formats/endmsg-dat.md` |
| END.DAT | Endgame narrative text | ⬜ | `formats/end-dat.md` |
| MISCMSG.DAT | Miscellaneous game messages | ⬜ | `formats/miscmsg-dat.md` |
| SHOPPE.DAT | Shop inventory and pricing tables | ⬜ | `formats/shoppe-dat.md` |

## 5. Data — graphics

### 5a. Tile sheets (paired EGA `.16` / CGA `.4`)

| Pair | Contents | Status | Spec doc |
|------|----------|--------|----------|
| TILES.16 / TILES.4 | Main world tile atlas | 🟡 | `formats/tiles.md` |
| ULTIMA.16 / ULTIMA.4 | Title screen art | ⬜ | `formats/title-art.md` |
| ITEMS.16 / ITEMS.4 | Item icons | ⬜ | `formats/items-art.md` |
| TEXT.16 / TEXT.4 | Bitmap font cells | ⬜ | `formats/text-art.md` |
| CREATE.16 / CREATE.4 | Character creation art | ⬜ | `formats/chargen-art.md` |
| DNG1, DNG2, DNG3 (.16 / .4) | Dungeon wall/floor sprites (three sets) | ⬜ | `formats/dungeon-art.md` |
| MON0..MON7 (.16 / .4) | Monster sprite sheets (eight sets) | ⬜ | `formats/monster-art.md` |
| STARTSC, ENDSC, END1, END2 (.16 / .4) | Title and end-sequence screens | ⬜ | `formats/sequence-art.md` |
| STORY1..STORY6 (.16 / .4) | Intro story slides | ⬜ | `formats/story-art.md` |

ninth-virtue's `src/tiles/` decoder works on TILES.16; lift the format spec out and re-derive against the file independently.

### 5b. Fonts and character sets

| File(s) | Contents | Status | Spec doc |
|---------|----------|--------|----------|
| IBM.CH, IBM.HCS | IBM character set (and high-color/strip companion) | ⬜ | `formats/font-ch.md` |
| RUNES.CH, RUNES.HCS | Runic font | ⬜ | `formats/font-ch.md` |
| PROPORT.PCS | Proportional font | ⬜ | `formats/font-pcs.md` |

### 5c. Bitmaps

| File | Contents | Status | Spec doc |
|------|----------|--------|----------|
| TITLE.BIT | Title bitmap | ⬜ | `formats/bit.md` |
| BRITISH.BIT | Lord British portrait or similar | ⬜ | `formats/bit.md` |
| WD.BIT | "Warriors of Destiny" subtitle bitmap | ⬜ | `formats/bit.md` |

## 6. Data — audio

### 6a. Music (XMIDI, `.XMI`)

Sixteen tracks; format is well-documented (Origin's XMIDI is a published convention).

| File | Track |
|------|-------|
| U5THEME.XMI | Main theme |
| RULEBRIT.XMI | Rule Britannia (overworld) |
| BRITLAND.XMI | Britain town theme |
| WRLDBLW.XMI | World Below (underworld) |
| MONARCH.XMI | Monarch (Lord British's chamber) |
| BLCKTHRN.XMI | Blackthorn |
| ENGGMNT.XMI | Engagement (combat) |
| FANFARE.XMI | Fanfare |
| HALLS.XMI | Halls (dungeon) |
| HORNPIPE.XMI | Hornpipe (sailing) |
| GREYSON.XMI | Greyson |
| LADYNAN.XMI | Lady Nan |
| REUNION.XMI | Reunion |
| STONES.XMI | Stones |
| AMIGA.XMI | Amiga track |
| trntlla.xmi, setm.xmi | Tarantella / sound test (verify) |

Spec doc: `formats/xmi.md` — covers XMIDI structure (XMI/CAT/INFO/EVNT chunks).

## 7. Save data

| File | Contents | Status | Spec doc | Notes |
|------|----------|--------|----------|-------|
| SAVED.GAM | Full game state at save time | 🟡 | `formats/saved-gam.md` | ninth-virtue `docs/memory-map.md` covers most of the runtime layout |
| INIT.GAM | Initial save state for new games | ⬜ | `formats/saved-gam.md` | Same format as SAVED.GAM, used by chargen |
| SAVED.OOL, INIT.OOL | Companion to .GAM — likely overworld object/NPC tables | ⬜ | `formats/ool.md` | |
| BRIT.OOL, UNDER.OOL | Static object/NPC initial state for each surface | ⬜ | `formats/ool.md` | |

The `.OOL` extension is unknown — best guess is "Object Overlay Layer" or similar (movable object table). Confirm during decomp.

## 8. Algorithms (no on-disk file)

These exist only in code and must be reverse-engineered. Each yields a system spec in `systems/`.

| System | Likely source | Status | Spec doc | Notes |
|--------|---------------|--------|----------|-------|
| Line of sight / visibility | MAINOUT.OVL / TOWN.OVL | 🟡 | `systems/visibility.md` | Starting reference: ninth-virtue `docs/visibility-re.md` |
| NPC scheduling and pathfinding | NPC.OVL | ⬜ | `systems/npc-schedules.md` | The marquee Ultima V feature |
| Time tick: turns, hours, days, moons, wind | ULTIMA.EXE / MAINOUT.OVL | ⬜ | `systems/time.md` | |
| Door interaction (locked, magic-locked, secret) | CMDS.OVL | ⬜ | `systems/doors.md` | |
| Z-level transitions (ladders, climb, descend) | CMDS.OVL / TOWN.OVL | ⬜ | `systems/z-transitions.md` | |
| Combat AI per monster type | COMBAT.OVL | ⬜ | `systems/combat-ai.md` | |
| Spell engine, reagents, mantras | CMDS.OVL / COMBAT.OVL | ⬜ | `systems/magic.md` | |
| Conversation keyword matcher | TALK.OVL | ⬜ | `systems/conversation.md` | Pairs with `*.TLK` format |
| Random encounter generation | MAINOUT.OVL | ⬜ | `systems/encounters.md` | |
| Karma adjustments per action | spread across overlays | ⬜ | `systems/karma.md` | Driven by KARMA.DAT |
| Tile animation page swap timing | ULTIMA.EXE | ⬜ | `systems/animation.md` | |
| Lighting and visibility at night | MAINOUT.OVL | ⬜ | `systems/lighting.md` | Torches, light spell, moongates |
| Weather and wind | MAINOUT.OVL | ⬜ | `systems/weather.md` | |
| Save and load logic | ULTIMA.EXE | 🟡 | `systems/save-load.md` | |
| Dungeon 3D wireframe view | DUNGEON.OVL | ⬜ | `systems/dungeon-view.md` | |
| Character creation questionnaire | CAST.OVL / CAST2.OVL | ⬜ | `systems/chargen.md` | Driven by QUESTION.DAT |
| Intro and end sequences | INTRO.OVL / ENDGAME.OVL | ⬜ | `systems/sequences.md` | |

## 9. Cross-cutting catalogs

These are reference tables compiled from the systems above. Useful both for the engine and for the eventual quality-of-life features (quest journal).

| Topic | Status | Spec doc | Notes |
|-------|--------|----------|-------|
| Tile catalog: every tile index → name + animation + flags | ⬜ | `systems/tile-catalog.md` | Bridge between TILES and LOOK2 |
| NPC roster: every named NPC, location, schedule, role | ⬜ | `systems/npc-roster.md` | Useful for the QoL quest journal |
| Quest graph: keyword chains across NPCs | ⬜ | `systems/quest-graph.md` | The candidate AI-extraction project |
| Britannia gazetteer: every town, keep, dungeon, shrine | ⬜ | `systems/gazetteer.md` | |
| Spell list: every spell, reagents, level, effect | ⬜ | `systems/spell-list.md` | |
| Item list: every inventory item, source, effect | ⬜ | `systems/item-list.md` | |
| Monster bestiary: every monster, stats, AI, drops | ⬜ | `systems/bestiary.md` | |

---

## First-playable verification slice

Before the inventory is complete, run a tiny end-to-end implementation slice in parallel to flush out spec errors. Suggested target: Lord British's throne room.

- [ ] Decode TILES.16 and render the throne room from CASTLE.DAT
- [ ] Walk the avatar around with collision against walls
- [ ] Open and close one door
- [ ] Tick time and watch Lord British follow his schedule (CASTLE.NPC + BRITISH.PTH)
- [ ] Trigger one keyword conversation against CASTLE.TLK

This slice exercises tile rendering, location map format, movement, doors, schedules, pathfinding, and conversation. If any of those specs are subtly wrong, this finds out within roughly one week instead of after months of writing.
