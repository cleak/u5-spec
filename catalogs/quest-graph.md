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
useful response is reached.

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
| Doom | `VERAMOCOR` | Resident word table; no clean TLK clue identified in this pass |

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

## 5. Shards And Shadowlords

The three evil shards are a separate but intertwined chain. Conversation
identifies both the shards and the Shadowlord names needed to destroy them.

| Shadowlord | Name | Opposed principle | Shard clue source | Destruction target |
|---|---|---|---|---|
| Falsehood | `FAULINEI` | Truth | Ava, Leona, Lady Janell | Flame of Truth |
| Hatred | `ASTAROTH` | Love | Sin'Vraal, Lord Michael | Flame of Love |
| Cowardice | `NOSFENTOR` | Courage | Gardner, Lord Malone | Flame of Courage |

Sutek is the key rule source: the shards must be recovered from the Underworld
and cast into the Eternal Flame associated with the principle opposed by the
matching Shadowlord, while that Shadowlord is nearby. The names matter because
yelling a name can summon or draw the associated Shadowlord, but NPCs also warn
that speaking those names carelessly is dangerous.

The three shard-location branches are intentionally different:

- Falsehood is tied to Deceit and to visions from Cove's hidden sisters.
- Hatred is tied to Sin'Vraal's Underworld clue and the eastern-desert daemon
  route mentioned by Lord Michael.
- Cowardice is tied to Gardner's vision beneath the Isle of the Avatar dungeon.

The public implementation contract is that the player should be able to learn
all three names, all three shard goals, and the flame pairing without external
knowledge. Exact coordinate-like wording from the original clues is deferred to
a future clean coordinate catalog.

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
while Toede identifies the castle's volcanic island and trap-door hazards.

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
conversation path, and that destroying or preserving the object has endgame
consequences.

## 8. Shrine, Codex, And Mantras

The shrine/Codex chain is the virtue-side counterpart to the dungeon and shard
chains. Greyson explains that shrine meditation grants the sacred quest and is
the path toward the Codex. Glinkie explains restoration of destroyed shrines:
use the appropriate Word of Power and meditate with the proper mantra. Lady
Janell and Kindor connect Spirituality to a midnight moongate route.

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
| Grapple | Bidney -> Lord Michael | Obtain mountain-crossing tool. |
| Magic carpet | Treanna or Loubet -> Bandaii -> Smith/Iolo route | Connect the carpet to Lord British's chamber and the talking-horse clue. |
| Mystic arms | Telila -> Bullwier -> Ambrose | Learn the Underworld route to mystic equipment. |
| Glass/crystal weapon | Eb -> Malik -> Buccaneer clues -> Sven | Learn the pirate and airship-loss chain for powerful crystalline weapons. |
| Reagents | Malik -> Saul | Learn Mandrake and Nightshade gathering locations and timing. |
| Skull keys | Kristi -> Shenstone clue | Buy keys and learn the armourer connection. |
| Spyglass | Dufus -> Lord Seggallion | Obtain spyglass after the virtue-planets answer. |
| Sextant | Scally -> David | Probable item grant; action side effect still needs engine confirmation. |

These edges should be modeled as discoverable knowledge even when the actual
inventory side effect is implemented elsewhere. For example, the Talk graph can
say that Lord Michael grants or offers the grapple, while the item system owns
how that object is added to the party.

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
binary layout:

1. Every dungeon word in Section 4 is learnable or otherwise present in the
   shipped rule data.
2. `DAWN` and `IMPERA` unlock distinct social branches and are not
   interchangeable.
3. The three Shadowlord names, three shard goals, and three flame pairings are
   all discoverable through conversation.
4. The Crown, Sceptre, Amulet, sandalwood box, grapple, moongate-stone rule,
   and key reagent locations are each connected to at least one NPC route.
5. Branches that require trust, payment, virtue, an answer, or another keyword
   remain gated in the authored data.
6. No public data file needs to reproduce raw TLK bytecode, private offsets, or
   full dialogue text to satisfy this graph.

## 12. Open Questions

- The TLK control VM was decoded enough to align and classify quest edges, but
  not fully executed for every branch. Item side effects such as the sextant
  should be confirmed against the action-letter table before they are treated
  as hard inventory grants.
- Doom's word is present in the resident word table, but this pass did not find
  a clean NPC keyword branch that teaches it. If gameplay requires an in-world
  speaker for Doom specifically, that edge needs another targeted pass.
- Some decoded trailing records appear embedded rather than ordinary
  header-indexed TLK entries. These should not be used as required graph nodes
  until their reachability is confirmed.

## Sources

- Derived from `u5-decomp/notes/tlk-quest-graph.md`.
- TLK file structure and keyword semantics: `u5-decomp/formats/npc-tlk-pth.md`,
  `u5-decomp/functions/TALK_OVL/0x041C_talk_main.md`,
  `u5-decomp/functions/TALK_OVL/0x0B04_conversation_loop.md`,
  `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`, and
  `u5-decomp/functions/TALK_OVL/0x127E_load_npc_blob.md`.
- Resident word and name pools: `u5-decomp/formats/data-ovl.md`.
- Public cross-references: `formats/tlk.md`, `systems/conversation.md`,
  `systems/endgame.md`, `systems/karma.md`, `catalogs/npc-roster.md`, and
  `catalogs/gazetteer.md`.
