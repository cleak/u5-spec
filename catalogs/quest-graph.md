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

`IMPERA` also has one gate outside the dialogue system: the guard at Lord
Blackthorn's palace gate, which the party can only reach while wearing the
Black Badge. That gate reads only the first four typed letters, folding case,
so the full word passes and so does any word sharing that prefix.
`systems/blackthorn.md` Section 7a owns the exchange.

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

**What the words actually do.** Each word is bound to one dungeon entrance
cell. Until that dungeon's word has been spoken, the entrance renders and
behaves as a collapsed, impassable entrance, so the party cannot stand on the
cell and therefore cannot use the Enter command there. Speaking the word beside
the cell restores the entrance to its ordinary passable form. The state is
per-dungeon, saved, and survives reload; the full predicate, the toggle
behaviour, and the tile mapping are specified in `systems/commands.md`
Section 11, and the eight entrance coordinates are published in
`catalogs/gazetteer.md` Section 5.1. Because the same eight coordinates carry a
dungeon entrance on both world surfaces, unsealing a dungeon opens it on both.

Doom's final mechanical route is split across systems rather than conversation
alone. `VERAMOCOR` behaves exactly like the other seven words: it unseals the
Doom **entrance**, which sits at the centre of the Underworld surface rather
than on Britannia. It is not a seal inside the dungeon and it is not spoken from
a dungeon interior — the word path runs only in outdoor scenes. Doom therefore
has two independent gates: `VERAMOCOR` must have been spoken to make the
entrance passable, and all three Shadowlords must be vanquished for the Enter
command to admit the party rather than ambush it. Inside, the party must reach
the deepest room-id-fifteen trigger and resolve the final-room combat absorption
handoff described in `systems/endgame.md`. The Sandalwood Box remains a separate
saved story-item flag checked by the terminal overlay's victory branch.

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

The four gates, in the order the handler applies them, are:

1. **Position.** The party's X, Y, scene, and floor must all equal the row for
   the shard's index in the table below. Any mismatch refuses before anything
   else is tested.
2. **Shadowlord present on the flame.** The handler queries the *active-object*
   layer — not the terrain — at the cell one row north of the party, and
   requires it to return the Shadow Lord actor tile (`0xFC`; see
   `catalogs/monster-bestiary.md`). It does not test the flame terrain tile
   itself. The flame is authored terrain (`0xDE`, the "Flame of" tile) that the
   summoned Shadowlord is standing on.
3. **Handshake.** The active-Shadowlord id recorded by the name/Yell path must
   equal the shard's own index. Using the Shard of Falsehood on a summoned
   Astaroth refuses.
4. Only then does the destruction run.

Note the two different offsets: the name/Yell path drops the Shadowlord **two**
cells north of wherever the party was standing, while the destruction gate reads
the cell **one** north of the fixed destruction position. The Shadowlord is a
moving actor, so the player summons it somewhere in the keep and then has to be
at the destruction cell at a moment when the Shadowlord occupies the flame cell.

| Shard / Shadowlord | Destruction scene | Party floor | Party X | Party Y | Eternal Flame cell | Additional gate |
|---|---|---:|---:|---:|---|---|
| Falsehood / Faulinei | The Lycaeum | 2 | 15 | 9 | `(15, 8)`, same floor | Active Faulinei encounter immediately north |
| Hatred / Astaroth | Empath Abbey | 1 | 15 | 3 | `(15, 2)`, same floor | Active Astaroth encounter immediately north |
| Cowardice / Nosfentor | Serpent's Hold | basement (`0xFF`) | 15 | 16 | `(15, 15)`, same floor | Active Nosfentor encounter immediately north |

The destruction position is one cell **south of** the Eternal Flame in each of
those three scenes: the flame occupies the cell one row north, and it is that
cell the summoned Shadowlord stands on. The Eternal Flames are interior fixtures
of the three keeps. They are not overworld landmarks, they have no surface
coordinates, and there is no overworld shard-use path.

Therefore a compatible implementation should not allow shard use at the flame
coordinate alone to retire a Shadowlord slot. The matching Shadowlord must have
been made active through the name/encounter path first, and the party's scene,
floor, and cell must match the row exactly.

**A successful destruction consumes the shard.** The shared destruction path
clears the used shard's carried flag in the same step that it writes the
vanquished value into the Shadowlord slot and ORs the quest bit. After success
the party no longer owns that shard, and it will not appear in the U-Use item
list or the character inventory panel. Nothing else about the party's inventory
changes: no counter for any other item is touched, and a refused attempt (wrong
cell, wrong floor, wrong scene, no active Shadowlord, or a mismatched active
Shadowlord index) leaves the shard in the party's possession.

**Presentation order.** The narration is not gated behind the position test, so a
misfired shard use is still visibly a shard use:

1. The handler first prints a heading naming the shard family and a line
   describing the party holding the evil shard aloft, completed by the shard's
   own virtue word (Falsehood, Hatred, or Cowardice). This happens before any
   gate is evaluated.
2. It then plays a rising pitch sweep, followed by a falling one, again
   unconditionally.
3. Only the **position** gate produces the shared no-effect result. If the
   party's cell, floor, or scene is wrong, the handler prints that result and
   returns with no state change.
4. Once the position matches, it pauses, prints a line describing the shard
   being cast into the Eternal Flame completed by the opposed principle's word
   (Truth, Love, or Courage), and pauses again — **before** testing whether a
   Shadowlord is on the flame and whether the handshake matches.
5. If either of those two gates fails, the handler simply returns. It prints no
   refusal line, so from the player's side the sequence stops after the
   cast-into-the-flame line with nothing further happening.
6. On success it runs a short repeated flash effect over the flame cell with an
   accompanying sound, applies the three state writes, and closes with a line
   naming the destroyed Shadowlord.

Two divergences an implementation should avoid: evaluating the gates before any
output (in the original, a wrong-position shard use still produces the heading
and the sound before refusing), and printing a refusal for the actor/handshake
failures (in the original those are silent).

### Where the shards are: fixed Underworld placement

The three shards are not hidden-treasure records and are not conversation
grants. They are ordinary active objects placed at fixed Underworld coordinates
by the outdoor setup pass that runs whenever the party is on a non-surface
outdoor plane. The same pass places the Amulet of Lord British. Every record it
writes is on the Underworld plane (floor byte `255`):

| Object | Underworld X | Underworld Y | Placed only while |
|---|---:|---:|---|
| Amulet of Lord British | 105 | 225 | the party does not already carry the Amulet |
| Shard of Falsehood | 192 | 80 | the party does not carry it **and** Faulinei's slot is not vanquished |
| Shard of Hatred | 130 | 65 | the party does not carry it **and** Astaroth's slot is not vanquished |
| Shard of Cowardice | 176 | 184 | the party does not carry it **and** Nosfentor's slot is not vanquished |

Getting one of these objects runs the ordinary inventory-add path, which prints
the shard's own narration and sets that shard's carried flag. The pass is a
placement pass, not a respawn: once the carried flag is set the object is never
emitted again.

**This is a real spawn consumer of the Shadowlord slot table**, and it is not
decorative. Earlier public wording said the Shadowlord slots drive nothing but
town installation and the Doom gate; that was incomplete. The alive test exists
because destruction *consumes* the shard by clearing exactly the carried flag
this pass reads: after a successful destruction the shard's carried flag is
clear again, so the carried-flag test alone would happily re-place the shard in
the Underworld on the party's next visit and hand the player an infinite supply.
The alive test is what suppresses that. An engine that implements the placement
with only the carried-flag half of the gate will respawn every spent shard.

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

A slot takes exactly three kinds of value:

| Slot value | Meaning |
|---|---|
| `0` | Not yet placed. This is the value a newly created game starts with for all three slots; the Shadowlord is nowhere until the first midnight pass. It matches no scene. |
| `1..8` | Alive, hiding in the town whose **town scene byte** equals this value. |
| `0xFF` | Vanquished. Sticky: no later pass rewrites it. Consumers test the high bit, so any value with the high bit set reads as vanquished. |

**The hideout id is the town scene byte, not a private enumeration.** Id `1` is
Moonglow, `2` Britain, `3` Jhelom, `4` Yew, `5` Minoc, `6` Trinsic, `7` Skara
Brae, `8` New Magincia — the eight town rows of `catalogs/gazetteer.md`. Only
towns are eligible; dwellings, castles, keeps, and the dungeon-mode scene bytes
are never hideouts. The town-entry consumer literally compares the slot value
against the scene byte of the town being entered, which is what fixes this
identity.

**Do not confuse hideout towns with the three Shadowlord confrontation
scenes.** The scenes where a Shadowlord can be named and destroyed are the three
fixed Eternal Flame keeps listed in Section 5 — The Lycaeum, Empath Abbey, and
Serpent's Hold. Those are a separate axis: they are where the endgame of the
shard chain happens, they never appear in a hideout slot, and entering a town
that matches a hideout slot does not turn that town into one of them. Town entry
installs a Shadowlord actor into the town scene the party is already in; the
scene identity is unchanged.

At midnight, the time cleanup rerolls each living Shadowlord's hideout. The
exact rejection rule is specified in `systems/time.md` Section 7: the new id is
drawn uniformly from `1..8` and rejected when it equals the party's current
scene byte or the value currently held by any of the three slots, including the
slot being rerolled. When the player destroys a Shadowlord through the shared
shard/spell destruction path, that slot becomes vanquished and is no longer
rerolled. The same success path also marks that Shadowlord's NPC roster slot in
Stonegate as permanently removed, so the vanquished Shadowlord is never placed
there again, and it clears the used shard's carried flag. The removal record
lives in the per-location removed-NPC bitmask table described in
`formats/saved-gam.md` section 9.2; earlier revisions of this document called
those bytes a "quest-progress word", which is withdrawn. The three Shadowlord
slot bytes remain the authoritative alive/vanquished state for gameplay
gates.

Several user-visible behaviours consume the same state:

- Entering a town whose scene byte matches a living Shadowlord's slot installs
  that Shadowlord as an actor in that town's live cast. The town's scene
  identity, map, and NPC roster are unaffected. The install obeys the same
  one-at-a-time rule as the Yell summon: it is abandoned if any active-object
  record already carries the Shadow Lord actor tile `0xFC`. It is **not**
  abandoned for lack of a free record. One coordinate guard precedes all of
  this: a party entering on row `4` skips the hideout comparison entirely, so
  no Shadowlord is installed and the accompanying NPC sweep does not run. See
  `systems/town-mode.md` Section 13.
- The same recorded host drives a terrain effect in the hosting town: most of
  its standing crops and fruit trees are rewritten to a plowed patch and a
  hollow stump when the floor is brought up, so a hideout town's farmland looks
  blighted while its Shadowlord lives. No other town is touched. See
  `systems/town-mode.md` Section 3.
- Entering Stonegate reads the same three slots as presentation state: every
  non-vanquished slot contributes that Shadowlord's "air of" atmospheric line,
  while vanquished slots are silent.
- Yelling a Shadowlord's name in one of the three confrontation scenes checks
  whether that Shadowlord is still alive before creating the summoned encounter
  state, and records which Shadowlord is now active.
- Doom's entrance requires all three Shadowlord slots to be vanquished. The
  entrance check ANDs the three slot bytes together and admits the party only
  when the result still has the high bit set, which happens only when all three
  are `0xFF`. Attempting to enter Doom with any Shadowlord still living does not
  merely refuse: the party is ambushed at the entrance and stays outside.
- The Underworld outdoor setup pass places a Shadowlord's shard only while that
  Shadowlord's slot is alive, as described in Section 5. This is the one traced
  object-spawn consumer of the slots.
- A view/report path marks the current hideout state for each living
  Shadowlord. The exact readout geometry is not yet published; see Section 12.

There is still no traced effect on random-encounter rate or on ordinary monster
spawning: living Shadowlords do not make the overworld more dangerous. The
spawn-side consumer above is a fixed quest-object placement, not an encounter
rule.

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
| Humility | `LUM` | Wartow |

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
Mariah, Toshi, Dupre, Sentri, Maxwell, Geoffrey, and Julia, plus other rostered
companions cataloged in `catalogs/npc-roster.md`. Geoffrey and Julia are two of
the four NPCs the withdrawn `.TLK` header reading dropped entirely
(`catalogs/npc-roster.md` Section 1), so earlier revisions of this list omitted
them. Some join branches are virtue- or story-flavored, but the general
implementation requirement is uniform: the relevant keyword
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
- **Open: the Shadowlord location readout.** The three hideout slots are
  consumed by a view-side renderer that walks eight rows and overlays a marker
  on the row whose index matches a living slot's value. That much is settled.
  What the eight rows are laid out as on screen, and therefore whether the
  readout presents as a town list, a coarse world map, or something else, is not
  established, and no text line is emitted from that loop. Implementations
  should treat the readout's presentation as unspecified and drive it from the
  slot values rather than inventing a wording for it. The hideout semantics
  themselves are not affected: the slot value is a town scene byte.

## Sources

- Derived from `u5-decomp/notes/tlk-quest-graph.md`.
- Action-letter item grants are cross-checked against
  `u5-decomp/functions/TALK_OVL/`,
  `u5-decomp/functions/ZSTATS_OVL/`, and shipped `.TLK`
  action usage.
- TLK file structure and keyword semantics: `u5-decomp/formats/npc-tlk-pth.md`,
  `u5-decomp/functions/TALK_OVL/`, and
  `u5-decomp/functions/TALK_OVL/`.
- Resident word and name pools: `u5-decomp/formats/data-ovl.md`.
- Runtime Shadowlord hideout, vanquish, Yell, Word-of-Power, and Doom-gate
  semantics:
  `u5-decomp/formats/data-ovl.md`,
  `u5-decomp/functions/CMDS_OVL/`, and
  `u5-decomp/functions/CAST_OVL/`; the
  Doom-side `VERAMOCOR` route is also summarized in
  `u5-decomp/notes/system-trace_quest-endgame.md`.
- Public cross-references: `formats/tlk.md`, `systems/conversation.md`,
  `systems/endgame.md`, `systems/karma.md`, `systems/containers.md`,
  `catalogs/item-list.md`, `catalogs/npc-roster.md`, and `catalogs/gazetteer.md`.
