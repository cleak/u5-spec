# Quest Graph

Cleanroom catalog of the main quest dependencies encoded by the conversation
files, resident word tables, and the already-specified conversation engine.
This is not a dialogue transcript. It records which NPCs, keywords, items,
places, passwords, and clues unlock other quest facts, while deliberately
omitting response text, private file offsets, bytecode, and raw dialogue blobs.

## 1. Scope

The quest graph is the data layer above `systems/conversation.md` and
`formats/tlk.md`. The conversation system explains how the engine finds an NPC,
loads a keyword tree, matches the player's input, and runs response bytecode.
This catalog describes the higher-level progression information carried by
those keyword trees.

The graph is intentionally semantic. A modern engine does not need to preserve
the original byte layout to reproduce the quest; it needs to preserve the same
reachable knowledge, gates, rewards, and dependencies. If a player can learn a
password, dungeon word, artifact location, shrine route, or reagent source in
the original, the equivalent edge should exist in the reimplementation.

The catalog uses these node classes:

| Node class | Meaning |
|---|---|
| NPC | A speaking character from `catalogs/npc-roster.md`. |
| Keyword | A player-typed conversation topic. |
| Knowledge | A fact that can guide later action, such as a dungeon word. |
| Password | A typed answer that unlocks a branch. |
| Item | A recoverable, buyable, or granted inventory object. |
| Place | A named location from `catalogs/gazetteer.md`. |
| Gate | A condition such as Resistance trust, a yes/no answer, gold, or virtue. |
| Action | A world command outside Talk, such as shrine meditation or yelling a word. |

The graph is not a save-state model. It does not list every flag set by the TLK
bytecode. It names a branch as gated when the shipped data clearly requires
trust, payment, a password, an answer, or another conversation fact before the
useful response is reached. The mechanical split between durable quest flags,
per-scene TALK branch flags, and one-conversation signal arrays belongs to
`systems/quest-flags.md`.

For compatibility, the graph gates below should be implemented as authored
conversation branches rather than as a separate quest-log script. A trust or
answer gate is a keyword/label path in the NPC's `.TLK` data; a payment gate is
the three-digit gold-payment control path; an item grant is the global
action-letter dispatch described by `systems/conversation.md`; a karma gate is
the moral-standing threshold branch. These mechanisms can appear inside
follow-up prompts as well as top-level keywords, so reachability depends on the
conversation VM's label-scoped prompt rules, not just on the header-indexed
keyword list.

## 2. Global Progression Shape

Ultima V's main quest is deliberately web-shaped rather than linear. The player
can enter many branches in any order, but the branches converge on four major
requirements:

1. Recover the royal artifacts: Crown, Sceptre, and Amulet.
2. Learn and use the dungeon Words of Power.
3. Recover and destroy the three evil shards by using the Eternal Flames and
   the Shadowlords' names.
4. Preserve and use the hidden sandalwood-box object that enables Lord
   British's return.

Conversation provides most of the route-finding for those requirements. The
Talk command does not enforce a single quest log. Instead, NPC keyword branches
teach reusable facts: which NPC knows a word, which password proves trust,
which dungeon hides a shard, which item crosses mountains, and which enemy name
must be spoken carefully.

## 3. Password Gates

Two passwords are central enough to model as graph gates.

| Password | Graph role | Typical effect |
|---|---|---|
| `DAWN` | Resistance trust | Opens anti-Blackthorn branches, Council-member help, and some useful item grants. |
| `IMPERA` | Oppression or Blackthorn-aligned infiltration | Grants access to hostile or dangerous Blackthorn-side branches. |

`DAWN` is the positive main-quest trust token. Zachariah, Chamfort, Thentis,
and related Resistance NPCs route the player toward it. Once known, it unlocks
branches such as Landon's Crown clue, Felespar's Word of Power clue, and
Thrud's item grant.

`IMPERA` is not a Resistance substitute. Blackthorn and Saduj use it as an
Oppression-side password, and Flain can route the player into Elistaria's
Blackthorn-aligned branch. A reimplementation should preserve the difference:
the same "typed password" mechanic can be used, but the two passwords belong to
opposite social graphs.

## 4. Dungeon Words

The Great Council chain teaches that eight Words of Power correspond to the
eight dungeons. The resident word order and the TLK clues establish this table:

| Dungeon | Word of Power | Primary clue source |
|---|---|---|
| Deceit | `FALLAX` | Malifora |
| Despise | `VILIS` | Annon |
| Destard | `INOPIA` | Trian and Goeth |
| Wrong | `MALUM` | Felespar |
| Covetous | `AVIDUS` | Fiona |
| Shame | `INFAMA` | Sindar |
| Hythloth | `IGNAVUS` | Hassad |
| Doom | `VERAMOCOR` | Resident word table and Yell Word-of-Power handler; no clean TLK clue identified in this pass |

The graph around these words has three layers:

- Annon gives the premise: the Council derived eight words to seal the eight
  dungeons, and Blackthorn is hunting Council members to undo that seal.
- Individual Council survivors or clue chains expose specific dungeon words.
- World commands consume the words outside conversation, especially dungeon
  entry and shrine restoration.

Some sources are indirect. Trian points toward the person in Jhelom who searches
for what is not there, and Goeth speaks in reversed wording. The usable edge is
still simple: Jhelom contains the route to Destard's word. Hassad's Hythloth
branch is prison- and trust-shaped. Felespar's Wrong branch is explicitly
Resistance gated.

Doom's final mechanical route is split across systems rather than conversation
alone. The same Yell Word-of-Power path that handles the seven cardinal dungeon
words also accepts `VERAMOCOR`, but Doom's exterior entrance is not opened by
that word. After the Shadowlords are vanquished, the party can enter Doom; once
inside, `VERAMOCOR` opens the Doom-side chamber seal at its authored target
cell. The party must then reach the deepest room-id-fifteen trigger and resolve
the final-room combat absorption handoff described in `systems/endgame.md`. The
Sandalwood Box remains a separate saved story-item flag checked by the terminal
overlay's victory branch.

## 5. Shards And Shadowlords

The three evil shards are a separate but intertwined chain. Conversation
identifies both the shards and the Shadowlord names needed to destroy them.

| Shadowlord | Name | Name or shard clue sources | Opposed principle | Destruction target |
|---|---|---|---|---|
| Falsehood | `FAULINEI` | Lord Shalineth, Ava, Leona, Lady Janell | Truth | Flame of Truth |
| Hatred | `ASTAROTH` | Sin'Vraal, Lord Michael | Love | Flame of Love |
| Cowardice | `NOSFENTOR` | Lord Malone, Gardner | Courage | Flame of Courage |

Sutek is the key rule source: the shards must be recovered from the Underworld
and cast into the Eternal Flame associated with the principle opposed by the
matching Shadowlord, while that Shadowlord is nearby. The names matter because
yelling a name can summon or draw the associated Shadowlord, but NPCs also warn
that speaking those names carelessly is dangerous.

At runtime, using a shard is not enough by itself. The party must be standing at
the matching interior destruction position, and the matching Shadowlord must be
the active named encounter. The Yell/name path supplies that active encounter;
the shard handler then checks that the Shadowlord marker is immediately north
of the party and that the active Shadowlord index matches the shard.

| Shard / Shadowlord | Destruction scene | Party floor | Party X | Party Y | Additional gate |
|---|---|---:|---:|---:|---|
| Falsehood / Faulinei | The Lycaeum | 2 | 15 | 9 | Active Faulinei encounter immediately north |
| Hatred / Astaroth | Empath Abbey | 1 | 15 | 3 | Active Astaroth encounter immediately north |
| Cowardice / Nosfentor | Serpent's Hold | basement marker | 15 | 16 | Active Nosfentor encounter immediately north |

Therefore a compatible implementation should not allow shard use at the flame
coordinate alone to retire a Shadowlord slot. The matching Shadowlord must have
been made active through the name/encounter path first.

The three shard-location branches are intentionally different:

- Falsehood is tied to Deceit and to visions from Cove's hidden sisters.
- Hatred is tied to Sin'Vraal's Underworld clue and the eastern-desert daemon
  route mentioned by Lord Michael.
- Cowardice is tied to Gardner's vision beneath the Isle of the Avatar dungeon.

The public implementation contract is that the player should be able to learn
all three names, all three shard goals, and the flame pairing without external
knowledge. Exact coordinate-like wording from the original clues is deferred to
a future clean coordinate catalog.

### Runtime Shadowlord State

The quest state for the three Shadowlords is a three-slot table, one slot per
Shadowlord in the order above:

| Slot | Shadowlord | Runtime meaning |
|---|---|---|
| 0 | Faulinei / Falsehood | Current hideout scene while alive; sticky vanquished marker after destruction. |
| 1 | Astaroth / Hatred | Current hideout scene while alive; sticky vanquished marker after destruction. |
| 2 | Nosfentor / Cowardice | Current hideout scene while alive; sticky vanquished marker after destruction. |

While a Shadowlord is alive, its slot holds one of eight compact hideout ids.
These are not the dungeon-mode scene-byte values used by the dungeon loop; they
are the values consumed by the Shadowlord view, Yell, and town-entry paths. At
midnight, the time cleanup rerolls each living Shadowlord's hideout
so that no living Shadowlord remains in the party's current scene and no two
living Shadowlords are assigned the same hideout in that pass. When the player
destroys a Shadowlord through the shared shard/spell destruction path, that
slot becomes vanquished and is no longer rerolled. The same success path also
ORs a per-Shadowlord bit into the save-backed quest-progress word:
Falsehood/Faulinei sets `0x02`, Hatred/Astaroth sets `0x04`, and
Cowardice/Nosfentor sets `0x08` in the low byte of `SAVED.GAM 0x0624`. The
three Shadowlord slot bytes remain the authoritative alive/vanquished state for
gameplay gates.

Several user-visible behaviours consume the same state:

- The Sextant/view path can mark or report the current hideout state for each
  living Shadowlord.
- Entering a town-family scene that matches a living Shadowlord's current slot
  can install that Shadowlord into the scene.
- Entering Stonegate reads the same three slots as presentation state: every
  non-vanquished slot contributes that Shadowlord's "air of" atmospheric line,
  while vanquished slots are silent.
- Yelling a Shadowlord's name checks whether that Shadowlord is still alive
  before creating the summoned encounter state.
- Doom's entrance requires all three Shadowlord slots to be vanquished.

This table replaces older wording that treated the midnight table as NPC
schedule or day-rollover pointer state. NPC schedules are separate per-NPC
records and are not advanced by this Shadowlord reroll.

## 6. Royal Artifacts

Sir Simon gives the top-level artifact objective: Crown, Sceptre, and Amulet
must be recovered. Other NPCs expand each branch.

| Artifact | Main clue chain | Required behavior |
|---|---|---|
| Crown | Chamfort or Resistance path -> Landon -> Blackthorn's castle | Located in Blackthorn's castle; blocks or absorbs magic while relevant. |
| Sceptre | Froed -> Greymarch -> Sir Simon, plus Stonegate clues | Dispels magical barriers, including barriers in ethereal or Shadowlord-held places. |
| Amulet | Sir Simon -> Lady Tessa | Found in the Underworld among graves of warriors; needed for passage through unholy darkness. |

The artifact chain overlaps with mobility. To reach Stonegate, Sir Sean points
the player to the southern Lost Hope Bay route and the grapple. Bidney points to
Lord Michael for the grapple, and Lord Michael grants it. To navigate
Blackthorn's castle, Gorn and Weblock provide internal escape and route clues,
while Toede identifies the castle's volcanic island and trap-door hazards. The
separate capture audience, challenge, and rescue/refuge cinematics are
specified in `systems/blackthorn.md`; this catalog owns only the conversation
and quest-dependency edges around them.

## 7. Lord British And The Sandalwood Box

NPC rumor establishes that Lord British entered the Underworld and is presumed
dead or lost. Margaret and Stephen provide the public castle-facing version of
that story. Johne gives the stronger quest framing: the Shadowlords hold Lord
British in the Underworld and manipulate Blackthorn.

Saduj provides the crucial hidden-object branch. He is Blackthorn-aligned and
therefore not a trustworthy ally, but his branch reveals that Lord British's
chamber contains a hidden object in a sandalwood box, and that destroying it
would prevent Lord British's return. This connects conversation data to the
endgame requirement described in `systems/endgame.md`.

The implementation contract is not "Saduj must be helpful." It is that the
player can discover the box's importance through the original hostile-trap
conversation path, that obtaining the Sandalwood Box sets the story flag read
by the endgame, and that the terminal Lord British scene gates victory on that
flag after the endgame state has been entered. The shipped pickup is the
non-speaking `CASTLE:0` object slot 31 at local `(18,12,2)` with object tag
`0x0E`; `G` Get dispatches that object into the shared item-add path. No traced
acquisition branch requires Saduj's conversation as a prerequisite, so the
dialogue graph owns the clue and the item/container specs own the pickup
mechanics.

## 8. Shrine, Codex, And Mantras

The shrine/Codex chain is the virtue-side counterpart to the dungeon and shard
chains. Greyson explains that shrine meditation grants the sacred quest and is
the path toward the Codex. Glinkie explains restoration of destroyed shrines:
use the appropriate Word of Power and meditate with the proper mantra. Lady
Janell and Kindor connect Spirituality to a midnight moongate route.

At runtime, each virtue path advances through the shrine and Codex urn masks:
correct mantra at an unstarted shrine sets the ordained bit; reading the
corresponding Codex urn/page sets the Codex-read bit; returning to the shrine
with both bits set completes that virtue by clearing ordained and leaving the
Codex-read bit as the durable completed marker. The full mechanics live in
`systems/karma.md`; this catalog tracks the quest dependency edge.

Town NPCs provide individual mantra clues. The graph should preserve at least
these confirmed conversation edges:

| Virtue | Mantra | Source |
|---|---|---|
| Compassion | `MU` | Greyson |
| Valor | `RA` | Thorne |
| Justice | `BEH` | Chamfort |
| Honor | `SUMM` | Gruman |
| Spirituality | `OM` | Kindor |
| Humility | `LUM` | Katrina |

Other mantra and shrine details belong primarily in `systems/karma.md` and the
shrine portions of `systems/overworld.md`. This catalog's role is to ensure the
conversation graph exposes the facts the player needs to find those systems.

## 9. Mobility And Utility Chains

Several side chains are not optional flavor; they provide tools or knowledge
needed to traverse the map, survive the Underworld, or reach quest locations.

| Chain | Main route | Result |
|---|---|---|
| Moongate stones | Zachariah -> Goeth | Search below a waned moongate to find its stone; moving the stone moves the gate. |
| Stonegate route | Leof -> Sir Sean -> Balinor | Locate Stonegate and understand its daemon-guarded entrance. |
| Grapple | Bidney -> Lord Michael | Obtain the mountain-crossing tool/flag consumed by outdoor K-Klimb. |
| Magic carpet | Treanna or Loubet -> Bandaii -> Smith/Iolo route | Connect the carpet to Lord British's chamber and the talking-horse clue. |
| Mystic arms | Telila -> Bullwier -> Ambrose | Learn the Underworld route to mystic equipment. |
| Glass/crystal weapon | Eb -> Malik -> Buccaneer clues -> Sven | Learn the pirate and airship-loss chain for powerful crystalline weapons. |
| Reagents | Malik -> Saul | Learn Mandrake and Nightshade gathering locations and timing. |
| Skull keys | Kristi -> Shenstone clue | Buy keys and learn the armourer connection. |
| Spyglass | Dufus -> Lord Seggallion | Obtain spyglass after the virtue-planets answer. |
| Sextant | Scally -> David | Obtain the sextant from David. |
| Black Badge | Elistaria | Obtain the Black Badge through a conversation branch. |

These edges should be modeled as discoverable knowledge even when the actual
inventory side effect is implemented elsewhere. For the grapple, Lord Michael's
conversation branch sets the flag that outdoor K-Klimb tests before allowing a
mountain climb; the command and item specs own the resulting movement and fall
risk rules.

The utility-item grants are not per-NPC engine hooks. They are authored TLK
responses that choose one of the global action-letter effects. The public graph
therefore records the semantic edge, such as Lord Michael leading to Grapple or
Elistaria leading to Black Badge, while `systems/conversation.md` and
`systems/inventory.md` own the exact fixed-slot mutation. When a grant is
behind a password, payment, moral-standing threshold, or scoped answer, that
gate remains part of the graph edge even though the mutation itself is shared.

## 10. Companion Edges

Recruitable companions use the same TLK machinery but a special conversation
handler path for joining. This catalog does not duplicate the full party-join
rules from `systems/conversation.md`; it only records that companion
conversation branches are part of the quest graph.

Confirmed conversation join paths include Gwenno, Jaana, Katrina, Johne,
Mariah, Toshi, Dupre, Sentri, Maxwell, and other rostered companions cataloged
in `catalogs/npc-roster.md`. Some join branches are virtue- or story-flavored,
but the general implementation requirement is uniform: the relevant keyword
must route into the party-join prompt and obey party capacity and acceptance
rules.

## 11. Validation Rules

A reimplementation can validate its quest graph without matching the original
binary layout. These are regression checks for the clean data authored from
this catalog, not additional VM features:

1. Every dungeon word in Section 4 is learnable or otherwise present in the
   shipped rule data and accepted by the Word-of-Power command path.
2. `DAWN` and `IMPERA` unlock distinct social branches and are not
   interchangeable.
3. The three Shadowlord names, three shard goals, and three flame pairings are
   all discoverable through conversation.
4. The Crown, Sceptre, Amulet, sandalwood box, grapple, moongate-stone rule,
   and key reagent locations are each connected to at least one NPC route.
5. Branches that require trust, payment, virtue, an answer, or another keyword
   remain gated in the authored data.
6. Follow-up prompts and label-scoped records are included in reachability
   analysis; do not validate only the top-level keyword table.
7. No public data file needs to reproduce raw TLK bytecode, private offsets, or
   full dialogue text to satisfy this graph.

## 12. Quest Graph Completion And QA

The public quest graph covers the major artifact, word, shard, mantra,
shrine/Codex, social, utility-item, and endgame dependencies without
reproducing dialogue text or TLK bytecode. The TLK control VM is now specified
well enough for graph validation: per-scene branch flags, karma-threshold
branches, gold-payment gates, action-letter grants, and label-scoped follow-up
prompts all have public behavioral owners in `systems/conversation.md` and
`systems/quest-flags.md`.

- The graph is complete at main-quest dependency depth. A clean implementation
  should preserve the edges and gates named here, while allowing dialogue text,
  record layout, and internal bytecode representation to differ from the
  original shipped files.
- A future QA verifier can execute or statically interpret the shipped `.TLK`
  records through the public VM contract and compare them against this catalog.
  That verifier is a consistency and data-authoring aid, not a missing gameplay
  rule.
- Doom's word is present in the resident word table and accepted by the same
  Word-of-Power command path as the other seven dungeon words. This pass did
  not find a clean NPC keyword branch that teaches it, so the public graph
  treats the Doom word as mechanically authored rule data rather than as a
  required conversation edge.
- Decoded trailing or embedded records are non-required unless a public
  conversation, roster, or quest edge names them. They should not become
  mandatory graph nodes without a clean reachability proof.

## Sources

- Derived from `u5-decomp/notes/tlk-quest-graph.md`.
- Action-letter item grants are cross-checked against
  `u5-decomp/functions/TALK_OVL/0x0682_action_command_dispatch.md`,
  `u5-decomp/functions/ZSTATS_OVL/0x099A_snapshot_inventory_to_overlay_ds.md`,
  `u5-decomp/functions/ZSTATS_OVL/0x0A3A_zstats_main.md`, and shipped `.TLK`
  action usage.
- TLK file structure and keyword semantics: `u5-decomp/formats/npc-tlk-pth.md`,
  `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md`,
  `u5-decomp/functions/TALK_OVL/0x0B04_conversation_loop.md`,
  `u5-decomp/functions/TALK_OVL/0x0682_action_command_dispatch.md`,
  `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`, and
  `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`.
- Resident word and name pools: `u5-decomp/formats/data-ovl.md`.
- Runtime Shadowlord hideout, vanquish, Yell, Word-of-Power, and Doom-gate
  semantics:
  `u5-decomp/formats/data-ovl.md`,
  `u5-decomp/functions/CMDS_OVL/0x1418_cmds_yell.md`, and
  `u5-decomp/functions/CAST_OVL/0x15B4_cast_destroy_shadowlord.md`; the
  Doom-side `VERAMOCOR` route is also summarized in
  `u5-decomp/notes/system-trace_quest-endgame.md`.
- Public cross-references: `formats/tlk.md`, `systems/conversation.md`,
  `systems/endgame.md`, `systems/karma.md`, `systems/containers.md`,
  `catalogs/item-list.md`, `catalogs/npc-roster.md`, and `catalogs/gazetteer.md`.
