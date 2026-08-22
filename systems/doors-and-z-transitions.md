# Doors and Z transitions

## 1. Overview

Almost every non-trivial cell in Ultima V's interior maps is bounded — by a wall, a door, a ladder up, a ladder down, a chasm, a vehicle. The interactions that move the party past those bounds form a small, very visible cluster: open a door, pick a lock, climb or descend, exit a vehicle, or trigger a dungeon exit. Most command paths share a common shape — verb prefix, direction prompt, tile probe, deterministic per-tile reaction. Scene-class transitions converge on the *scene byte*; floor, dungeon-level, and world-plane changes also use the position and plane bytes owned by their active mode.

This spec describes that cluster: the door tile family and the J-Jimmy and O-Open commands that act on it, the K-Klimb command and the automatic-descent triggers it complements, the X-Xit vehicle command, and how scene byte, floor/level index, and world plane divide ownership for transitions between overworld, town floors, dungeon levels, and the underworld.

## 2. The door tile family

Doors live in two parallel encodings — one for the surface and town tile maps, the other for the packed-nibble dungeon grid. Both distinguish *closed-and-unlocked*, *closed-and-locked*, *closed-and-magic-locked*, and *open*; both encode the lock state in adjacent tile bytes so that toggling the lock is a one-byte rewrite.

In the surface and town encoding, the tile codes J-Jimmy and O-Open care about fall into these groups:

- **Closed door pair.** Each door orientation has an adjacent code pair: the lower byte is closed-and-unlocked and the next is closed-and-locked, so a successful Jimmy simply decrements the byte one rung and reaches the openable form. `0xB8`/`0xB9` is the north-south pair and `0xBA`/`0xBB` the east-west pair. The magic-locked forms live outside that pair, at `0x97` for north-south and `0x98` for east-west; Jimmy refuses them without rolling (though it still breaks a key doing so), and only the Unlock Magic spell converts them back (see § 7). O-Open on an unlocked closed door does not write the standing open-door code below; it writes the shared cleared-cell tile `0x44` — the same byte that fills ordinary interior floor — and the auto-close tracker restores the saved door byte a few turns later.
- **Open door.** A single code drawn as the open-door sprite. Both Jimmy and Open recognise this as already-open and consume the turn without acting. The renderer paints it identically to a passage.
- **Restraint tiles.** Stocks and a set of manacles. These are not containers and not doors: J-Jimmy treats them as prisoner releases (§ 3.1), and they never convert to an "unlocked" counterpart tile.
- **NPC occupancy marker.** A non-rendered marker returned by the tile-probe path when the target cell is occupied by an NPC. J-Jimmy uses it only to find the prisoner standing on a restraint tile; there is no pickpocket interaction.

Surface and town chests are **not** part of this locked/unlocked tile pairing.
A chest is a per-map container *object*, and its lock, trap, and contents state
lives on the object record rather than in the tile grid. J-Jimmy in particular
never matches a chest through its tile cascade at all — chests reach it only
through the object scan (§ 3.2). Earlier drafts listed a locked-versus-closeable
"chest-on-floor tile pair" here alongside the door pair; treat the object record,
not a tile pair, as the authority for whether a container is locked.

The dungeon grid packs the tile class into the high four bits of the cell byte and a sub-type into the low four bits. One high-nibble value identifies "heavy door"; another identifies "secret door / room trigger". The low nibble selects per-class variant — open versus closed, orientation. The dungeon Open handler matches purely on the high nibble; the dungeon Jimmy and Search handlers consult the low nibble for variant-specific narration.

A separate set of tile codes encodes *secret doors* — see § 8.

## 3. The J-Jimmy command

J-Jimmy is the engine's lockpick verb, dispatched from the A-Z router via the
verb prefix `Jimmy-` and a single direction prompt. There are exactly **two**
lock-pick rolls in the command, and they apply to disjoint families of targets.
The target family is decided from the target tile before any roll happens:

- **Locked doors** take *roll one*, the flat Dexterity test.
- **Restraints** — stocks and a set of manacles — take *roll one* as well, from
  a second, independent copy of the same test, but their success outcome is a
  prisoner release rather than an unlocking.
- **Magically locked doors** are refused with no roll at all, and the refusal
  still costs a key.
- **Everything else** falls through to the per-map container scan and takes
  *roll two*, the difficulty-versus-Dexterity threshold. A tile with no
  container object on it draws the generic no-lock refusal.

Both rolls read the same character statistic: the acting party member's
**Dexterity**. Neither reads a class or profession byte, so there is no sense in
which different character classes are better at doors than at chests. Earlier
drafts of this document called that byte a "lock-pick class byte"; that reading
is retracted.

Two further corrections to earlier drafts are worth stating plainly, because
they change what an implementer builds:

- **There is no pickpocketing in the Jimmy command.** No branch of it takes gold
  or items from an NPC. The thank-you line and moral-standing increase that
  earlier drafts attributed to a pickpocket belong to the restraint case below,
  which frees a prisoner and transfers nothing.
- **Floor and town chests are not tiles this command matches on.** The handler
  reads the target tile as a single byte, and the chest tile identity lies above
  the range a single byte can express, so a chest can never reach the tile
  cascade. Surface and town chests are per-map *container objects*, and they
  always take roll two. Applying the flat Dexterity test to a floor chest is
  wrong.

The handler first checks the scene byte. Dungeon scenes route to a
dungeon-specific inner handler that uses the packed-nibble grid. Other scenes
check key inventory up front: if the key inventory is zero, Jimmy prints
"No keys!" and returns before the shared tile preflight gate.

### 3.1 Roll one — the flat Dexterity test

The handler prompts for which party member is picking, then rolls a uniform die
with **thirty outcomes beginning at zero**. The attempt succeeds when that
member's Dexterity is **strictly greater** than the roll.

The cleanest statement of the contract is the resulting probability: success
chance is the acting member's Dexterity divided by thirty, clamped at both ends.
A member with Dexterity zero never picks; a member at Dexterity thirty or above
always picks. Note that the die's lowest outcome is zero — an earlier draft's
"uniform `1..29` die" is off by one at the top of the curve, and would deny a
maximum-Dexterity character the guaranteed success the original gives.

Success consumes **no** key. Only failure consumes one, printing the broken-key
result.

**Locked doors.** Success converts the door to its unlocked counterpart, sets
the tile-changed dirty bit, and prints "Unlocked!". Each locked door form has
exactly one paired unlocked form — a locked plain door becomes a plain wooden
door, and a locked door with a window becomes a wooden door with a window — so
implement the conversion as that pairing rather than as arithmetic on a tile
number. Jimmy does not open the door; a subsequent Open turns the cell into an
open door. On failure the key counter is decremented, the broken-key result is
printed, and the door's tile is *unchanged*: the lock still stands and the door
may be attempted again while keys remain.

**Restraints — stocks and manacles.** This is a prisoner release, not a
container pick, and it should be read as its own interaction. It uses its own
copy of the flat Dexterity test with the same thirty-outcome die and the same
strictly-greater comparison, but the success tail is entirely different.

On success the engine probes for an NPC standing on the restraint tile. If no
NPC is there it prints "No one is there!" and stops. Otherwise it walks that
NPC's record chain, sets that NPC's state bytes to the freed value, prints the
NPC's thanks line, and raises the shared moral-standing selector by `+2` with
the normal ninety-nine cap (see `systems/karma.md`).

On the large outdoor maps the same success takes a different tail: it stamps the
restraint tile to plain cobble and prints a differently worded, unpunctuated
unlocked message — a distinct string from the door case's "Unlocked!" — and
frees nobody.

A restraint never converts to an "unlocked restraint" form: the success tail
never steps its tile down a rung the way the door case does, and the tile one
rung below stocks is an unrelated feature. A restraint also never yields loot,
gold, or any inventory change.

**Magically locked doors.** The magic-locked forms are refused inside this
command, with no roll, no Dexterity read, and no member prompt. The refusal is
real and it lives here — an earlier draft's suggestion that it must originate in
the command dispatcher or the tile classifier is retracted. What that draft got
wrong is the refusal's narration and its cost: it prints the **broken-key**
result and it **does** consume one key. It does not print a distinct "magic
lock" message and it is not free. Only the Unlock Magic spell converts a
magic-locked door back (§ 7).

### 3.2 Roll two — the difficulty-versus-Dexterity threshold

Every target the tile cascade does not claim falls through to a scan of the
per-map container objects at the target coordinates. If no container is there,
Jimmy prints the generic "No lock!" refusal and returns. If one is there, the
handler prompts for a member and computes a threshold as

difficulty minus the member's Dexterity, plus thirty, halved.

The halving is an unsigned halving of a word value, so out-of-range Dexterity or
difficulty values wrap the way the original does; preserve that rather than
clamping. The handler then rolls `1..30`, and the pick succeeds when the roll is
**strictly greater** than the threshold. Earlier statements of this comparison —
for the per-map container, for the dungeon chest, and in the inventory summary
below — all had it inverted.

The difficulty term is the only difference between the two places this roll is
used:

| Instance | Difficulty term |
|---|---|
| Surface / town container object | The container's own difficulty, carried in the same byte as its lock/trap flag. |
| Dungeon chest cell | Twice the current dungeon level. |

The doubling exists **only** underground. A surface or town container never
inherits it, and its difficulty never depends on where the party is.

**Success** clears the container's locked/trapped flag while preserving the
content class, prints the success result, and consumes **no** key and plays no
sound. **Failure** prints the broken-key result, plays the key-snap sound,
decrements the key counter, and leaves the container's state completely
untouched: same lock, same contents, and it may be attempted again for as long
as keys remain.

**Container contents can never be lost by Jimmy.** The content class and the
lock/trap flag share one byte but occupy different parts of it, and the only
write Jimmy ever makes to that byte is the success write that clears the flag.
A broken key changes nothing, so there is no "broken-lock state" and no way for
a failed pick to destroy loot. Earlier drafts of this document and of
`systems/containers.md` described such a state; it does not exist, and every
mention of it is retracted.

Because the flag Jimmy clears on success is simultaneously the **trap** flag, a
successful Jimmy both unlocks and disarms. A later Open on that container skips
the trap narration and the shared trap-effect resolver entirely and goes
straight to the contents. Jimmy-then-Open is therefore the game's intended
disarm loop; see `systems/traps.md` for what an armed container does instead.

**Already-unlocked short-circuit.** A container whose lock/trap flag is already
clear — equivalently, a dungeon chest cell whose lock/trap sub-type is already
zero — is not re-rolled. Jimmy prints the broken-key result and **consumes one
key** for nothing. That wasteful outcome is the correct behaviour on both the
surface and the dungeon path; an earlier draft's claim that the dungeon
short-circuit "returns without changing keys" is wrong. The reason a
successfully picked container reaches this state at all is that the lock
difficulty and the trap flag are the same field, and a successful pick zeroes
it.

There is no reachable state in which a container exists but cannot be opened.
Open consumes the container object outright — it clears the object record before
generating contents — so every container is either still lockable and openable,
or gone.

**Not a third formula.** Dungeon Search reuses the identical threshold
expression as a pure *detection* roll, with no lock semantics and no effect on
keys or lock state (see `systems/dungeon-mode.md`). That reuse is why a third
lock-pick variant appeared to exist; there are only two.

### 3.3 Dungeon Jimmy specifics

The dungeon inner handler prompts for a member before checking keys for the
relevant cell. A lockable dungeon chest cell takes roll two with the doubled
depth term above; on success the cell is rewritten to the closed-chest class
with its lock/trap sub-type cleared and its variant bit preserved, and the
unlocked message is printed. A chest cell whose sub-type is already zero takes
the wasteful short-circuit described above. Already-open dungeon chest classes
report already open, and non-lockable classes report the generic refusal.

## 4. The O-Open command

O-Open is the lighter cousin of Jimmy: it acts only on already-unlocked doors and chests, and never consumes a key. The dispatcher prints `Open-`, prompts for direction, and then runs the Open handler. As with Jimmy, scene byte routes between a dungeon-mode inner variant (which consults the *underfoot* tile rather than the tile in front — see § 9) and a non-dungeon variant.

The non-dungeon Open handler always begins with one piece of bookkeeping: the door auto-close pass (§ 5). It then runs the shared pre-flight reachability gate, computes target coordinates, fetches the front-tile byte, and cascades:

- **Already-open door** — "It's open!" and return.
- **Too-heavy target** — "Too heavy!" and return. This is a refusal distinct
  from a locked target; Open does not try to pick or force it.
- **Locked door / chest / lockable NPC** — "Locked!" and return. Open does not pick.
- **Closed-and-unlocked door / closeable chest** — open path: snapshot the previous tile id, X, and Y into the door-close-tracker, set the tracker countdown to four, rewrite the cell to the open-container byte, set the tile-changed bit, and print "Opened!".
- **Magic-locked door** — treated as locked.
- **Anything else** — route to the chest-on-floor helper, which scans the location's per-map object table for a chest at the target cell and grants its contents, invokes the shared trap-effect resolver when a trap outcome is selected, prints "Trapped!", "Nothing to open!", or another container line.

Open writes the same open-container tile for both doors and closeable
chest-like tiles, so a freshly opened door and a freshly opened closeable
container can be visually indistinguishable in the live tile buffer. The traced
command-layer refusal for a guarded or otherwise blocked openable tile is the
too-heavy branch: it prints the heavy-object refusal and stops before key,
magic, trap, or chest-content handling. If the tile cascade does not recognise
the target as a door/openable/locked/heavy case, ownership passes to the
chest-on-floor helper; that helper owns object-table matching, traps, empty
chests, content grants, and its own "nothing" or "can't" refusals.

## 5. The auto-close timer

Every door opened with O resets a four-byte resident block holding the previous tile, X, Y, and a countdown initialised to four. Each turn that consumes a turn decrements the countdown; when it hits zero the engine writes the previous-tile byte back to the saved cell and the door silently re-closes. The player has roughly four turns to pass through before it shuts.

Three observations:

- The block holds *one* door's state at a time. Opening a second door before the first auto-closes overwrites the saved state; the first door stays open for the rest of the visit.
- Doors closed by the auto-close pass do not re-lock — the snapshot is the unlocked closed form, not the locked form. A door the player Jimmied open and walked through stays unlocked across the visit.
- The pass is suppressed in dungeon mode; dungeon doors are toggled by Open and stay in whatever state Open last left them in until the player leaves the dungeon.

## 6. The "BOOOM!" outcome

The "BOOOM! Door destroyed!" string pair belongs not to Jimmy or Open but to the F-Fire ship-cannon handler. Firing a ship's cannon at a door (or wall) prints "BOOOM!" with the cannon's hit narration; on a hit at a door cell, the engine rewrites the cell to the open-door tile (or rubble) and prints "Door destroyed!".

Two consequences: ship-fire is a third unlock path, and it does not route
through Open or Jimmy's key, magic-lock, heavy-object, or chest-helper refusal
cascade. A door that those command paths refuse can still be cannon-blasted
when the cannon handler accepts the target. The destruction is non-persistent
across save / load: the location's tiles are reloaded from disk on every entry,
so "Door destroyed!" is undone the next time the player walks back into that
town.

## 7. Magic-locked doors

Some doors carry a magical lock that no key can pick — the lower byte of the door pair (§ 2). Magic-locked doors appear mostly in plot-critical locations: a sealed throne room, the entrance to a quest reward, a story-gated dungeon cell.

J-Jimmy on a magic-locked door refuses without rolling: no member is prompted
and no Dexterity is read. The refusal is not free, though — it prints the
ordinary broken-key result and consumes one key (§ 3.1). Earlier drafts of this
document reported a distinct "Magic lock!" message at no cost; both halves of
that claim are retracted. The paths through are:

- **Unlock Magic** cast on the door rewrites the cell from magic-locked straight to the closed-and-*unlocked* form for that orientation (`0x97` becomes `0xB8`, `0x98` becomes `0xBA`), so O-Open works on it immediately and no Jimmy roll is needed.
- **Magic Lock** is the inverse and the only writer of the magic-locked forms. It collapses both the unlocked and the ordinary-locked byte of an orientation onto that orientation's magic-locked byte (`0xB8` or `0xB9` becomes `0x97`, `0xBA` or `0xBB` becomes `0x98`), so magic-locking an ordinary locked door and then unlocking it magically leaves the door merely closed.
- **Open** (the *An Sanct* spell, not the O-Open command) steps a door one rung *down* the ordinary lock ladder: `0xB9` becomes `0xB8` and `0xBB` becomes `0xBA`. It does not recognise the magic-locked bytes, so it cannot substitute for Unlock Magic.
- **Blink** can place the caster on the cell on the far side when the destination is legal, bypassing the lock; the door stays locked but the party is past it.
- **Cannon fire** (§ 6) destroys magic-locked doors as readily as regular ones.

Magic-lock clears are sticky for the visit but revert on location reload. Plot progress that opens such a door permanently is encoded outside the tile grid — in the per-character flag table or the world flag table — and consulted on location load to walk the door's tile byte down a slot before painting.

The three door-facing spells share one shape and none of them is the O-Open
command or the Word-of-Power dungeon-door path. Each runs the shared spell
direction prompt, resolves the single adjacent cell, and rewrites its tile as
listed in § 7; Space/Pass is a silent no-effect result, a match marks the tile
dirty, and any other target tile is a failure/no-op. All three bypass keys but
are narrower than O-Open: they do not check chests, do not invoke traps, do not
use per-map guarded-container metadata, and do not install the auto-close
tracker — none of them produces an *open* door, only a different lock state.
The full spell-side contract, including their behaviour in combat scenes where
the same helpers act on combat-arena terrain, lives in `systems/magic.md`
under *Directed utility tile helpers*.

## 8. Secret doors

Secret doors are walls that look like walls until the player searches the cell.

- **In dungeons**, Search owns several visit-local reveal rewrites rather than
  one generic "secret door" bit. Exact pit-family byte `0x61` reports a found
  secret door, clears the searched pit to `0x60`, and marks the same X/Y one
  level below with the visit bit when there is a deeper level. Flavour-class
  cells `0xC?` narrate only for flavour values one and two; other flavour
  values convert to `0xB0` or `0xB8`. Wall-class cells `0xD?` print the
  hidden-wall result and convert to `0xE0` or `0xE8`. These rewrites preserve
  only the visit marker bit and affect the loaded dungeon image for the current
  dungeon entry.
- **In towns and dwellings**, secret doors are wall tiles flagged in the location's per-map object table. Search matches the target cell's coordinates to the table and replaces the wall tile with a normal door tile.

Search is the only way to find these authored hidden passages. Once revealed,
town/dwelling secret doors respond like ordinary unlocked doors. Dungeon reveal
cells instead follow the movement/opening rules of the replacement dungeon byte
named above. Walking into an unrevealed wall-style secret fails the same way
walking into a wall fails. Reveals are sticky for the visit but revert on
location reload.

## 9. The K-Klimb command

K-Klimb is the climb / descend verb, mode-aware: the resident dispatcher routes K through one of three handlers depending on scene byte — overworld, town, or dungeon — each with its own interpretation.

**Overworld K.** On the surface and underworld planes, K is the outdoor climb
verb. The handler first requires the Grapple quest flag; if the party does not
have it, it prints "With what?" and exits. It then requires the party to be on
foot; any vehicle state prints "On foot!" and exits. After the shared
pre-action gate, it probes the target tile in the current facing direction.
The climbable outdoor target is the mountain tile family. A separate blocked
mountain/impassable variant prints "Impassable!", non-climbable classes print
"Not climbable!", and the confirmed climbable mountain class continues. For
each living party member, the handler rolls `1..30` against that character's
Dexterity; if Dexterity is lower than the roll, it prints "Fell!" and applies
`1..5` fall damage to that member. Dead party members skip this risk roll.
After all living members are checked, the successful path calls the resident
climb/move helper with the original direction vector, advancing the party one
cell without changing Z. Falling through a chasm to the underworld is a
separate underfoot trigger, not a Klimb path (§ 10).

**Town K and stair movement.** Inside a town, dwelling, castle, or keep,
K is "climb the ladder". The handler consults the underfoot tile of the leader
or prompted member: an up-ladder moves to the floor above, a down-ladder to the
floor below, and a two-way ladder prompts up-or-down. Facing-sensitive
walk-on stairs are the separate `0xC4..0xC7` tile family: their low two bits
match the town movement wrapper's normalized facing value for an upward
transition, match that value's opposite-facing partner for a downward
transition, and do nothing on side crossings. Both paths implement the Z change
by rewriting the active floor index and reloading the tile buffer with a
different 1024-byte slice from the location's per-floor pair, then re-running
the per-map NPC linker so that NPCs on the new floor become visible while NPCs
on the old floor are unlinked from the active-object table. X and Y are
preserved; only the floor index and the surrounding 32-by-32 tile content
shift. Non-ladder underfoot tiles print "Not climbable!" and consume no turn.
There is no falling within a town's floor structure.

**Dungeon K.** In a dungeon scene, K reads the underfoot dungeon tile's high
nibble and offers whichever directions that cell provides. Up is offered on an
up-ladder or two-way cell, and also on a cell marked climbable-with-equipment
while the party carries the climbing gear; down is offered on a down-ladder,
two-way, or pit cell; when both are available the handler prompts for a
direction. Up decrements the level Z, down increments it, and X and Y on the new
level are the same as on the old. Exact pit byte `0x60` is the special
non-ladder K path: it bypasses the ladder apply helper and invokes the dungeon
surface-reset helper. Other cells return without a level change, and they
consume no turn: the two "nothing to klimb here" refusals - one for a
climbable-with-equipment cell the party lacks the gear for, one for a cell with
no climbable feature - both report "no action" to the dungeon loop, while every
applied climb, pit fall, or cancel at the direction prompt counts as an action.

Two corrections to earlier revisions of this paragraph. First, a **climb never
tests the cell it lands on** - the ladder or pit under the party is treated as
sufficient, and the destination-cell test described here previously belongs to
the dungeon level-change spells, not to K. Second, **boundary ladders do define
a plane transition**: attempting to climb above the topmost level or below the
lowest one is not refused, it leaves the dungeon through the shared exit
contract, surfacing on Britannia from the top and in the Underworld from the
bottom. `systems/dungeon-mode.md` Section 13 owns both contracts.

## 10. Automatic descent: chutes, pits, and falls

Three movement events change Z without a Klimb:

- **Dungeon fall traps.** Exact bytes `0x61` and `0x69` trigger an automatic drop. Each fired step prints the pit/fall messages, increments Z by one, and lands the party at the same X and Y on the next level. The handler rewrites the loaded dungeon image as it falls: it clears marker bits on the departure cell and, when the destination byte is below the wall/door band (`< 0x90`), marks bit `0x08` in that destination cell. If the destination is another `0x61` or `0x69`, the fall repeats, so multi-level drops are vertical trap chains rather than a direct subtype-to-distance table. If the chain increments past the deepest level, the dungeon scene byte is cleared with the off-bottom level byte and same X/Y still in resident state; this is not the surface-reset helper. Exact `0x60` is the K-Klimb surface-reset pit path. Bomb traps `0x62` and `0x6A` share the high-nibble family but do not change Z.
- **Overworld chasms.** The traced surface chasm trigger is Britannia
  coordinate `(54, 138)`. Walking onto it prints the falls/underworld
  transition messages, applies fall-damage, swaps the world plane to the
  underworld value, and re-initialises the active-object table. There is no
  mirror outdoor underworld-to-surface ascent cell anywhere - the plane-writer
  census is complete - so do not infer one from the traced falls handler.
- **Town and dwelling trap-doors.** A few interiors have trap-door cells in their floor (an oubliette, a basement entry); walking onto one triggers the same Z-down behaviour as a dungeon pit.

In all three cases the trigger is an *underfoot reaction*, not a command, run as part of the per-turn epilogue's tile-effect pass — the same pass that handles damage tiles, energy fields, and moongate landings.

## 11. X-Xit Boundaries

The ordinary X-Xit command is the vehicle dismount command. Do not treat the
player's `X` key in normal dungeon mode as a dungeon escape spell:
dungeon-mode `X` is routed as a refusal/no-op, and combat `X` is refused by the
combat parser as well. The command-overlay routine with "Escape" refusal wording
is the combat-only escape handler, bound to the Escape key rather than to `X`,
and is specified in `systems/combat.md`; it is not a dungeon ladder or spell
escape path.

**Vehicle dismount.** When the party is on a horse, in a skiff, on a carpet, or
aboard a ship, X-Xit dismounts or transfers to a carried craft. It refuses in
dungeon/combat-class scenes before testing vehicle state. If the party is
already walking, the command prints the no-vehicle continuation after the X-it
prefix and returns.

The handler validates nearby landing support but does not move the party to a
different coordinate. Successful exits park the abandoned vehicle as an
active-object at the party's current cell so it can be boarded later:

- Horse exits always park a riderless horse and return the party to foot travel.
- Carpet exits require either passable ground under the party or nearby
  landing support; otherwise they refuse as no-land-nearby.
- Skiff exits require nearby landing support and reject the
  deep-water tile family under the skiff; on success the parked skiff preserves
  facing.
- Furled-ship exits park the ship hull. With nearby landing support, the party
  leaves on foot. Without that support, a carried skiff is launched if
  available; failing that, a stowed carpet is redeployed if available. If none
  of those routes exists, the command refuses as no skiffs being available.
- Hoisted-sail ships refuse until the player uses Y-Yell to furl sails.

The nearby-support probe checks the four rendered cardinal neighbours for
terrain passable by an on-foot avatar or for selected companion/overlay vehicle
and party cells that can support leaving the vehicle. It is a support test, not
a relocation target.

Parked ship objects preserve auxiliary state such as hull condition and the
remaining carried-skiff count. The broader vehicle contract, including B-Board,
F-Fire ship broadsides, exact transport marker families, and parked-vehicle
persistence, lives in `vehicles.md`.


## 12. Z transitions across modes

The scene byte ties everything together. The value zero is the overworld; values one through thirty-two are towns, dwellings, castles, and keeps; values from thirty-three through one-hundred-twenty-seven route through dungeon-class handling when reached during gameplay, with the stock dungeons occupying thirty-three through forty; the observed combat-class marker is `0xFF`. Within town scenes the floor index is a separate byte; within dungeon scenes the level index is in Z.

The transitions across the major boundaries are:

- **Overworld → town / dungeon.** Enter on a fixed location coordinate sets the scene byte to the location's index and triggers entry. Town scenes seed the ground floor through their entry table; dungeon scenes load the selected dungeon record and seed the level/X/Y/facing entry state: surface entries use `(0, 1, 1)` facing east, underworld non-Doom entries use `(7, 7, 7)` facing west, and Doom uses the surface entry seed.
- **Town / dungeon to overworld.** The town-family exit is a map-boundary
  event and not a tile effect: a step that would carry the party off the
  thirty-two-by-thirty-two interior grid raises a leave prompt instead of
  committing, and accepting that prompt clears the scene byte. (The former
  claim that the trigger is "tile id `0x59`" is withdrawn; that id is the
  telescope Look trigger catalogued in `catalogs/tile-catalog.md`, which occurs
  in three interior cells and never on a boundary.) The ordinary passability
  and occupancy tests run before the prompt, so a blocked boundary step reports
  blocked rather than offering the exit. A dungeon
  surface-reset helper, pit-chain off-bottom path, or total-party-wipe path can
  also clear the scene byte. The mode loop's general contract is "if the scene
  byte is no longer in my range, exit"; the one exit not signalled that way is
  the total-party wipe, where the exploration loop's party-capability check ends
  the loop from inside and the rescue/refuge sequence rewrites the scene byte
  afterwards (`systems/dungeon-mode.md` § 13.4, `systems/blackthorn.md`
  Section 7). Town-family exits also write the destination
  plane: ordinary exits select Britannia, while scene byte `0x19` - Ararat, the
  one location that exists only underground - selects the Underworld. The
  dungeon surface-reset helper restores the exterior coordinate and writes the
  destination plane from the level the party was on: off the topmost level they
  surface on Britannia, off the bottom of the lowest level they arrive in the
  Underworld. Deepest-level ladders therefore **do** publish an underworld
  handoff, and an earlier statement to the contrary is withdrawn. Pit-chain
  off-bottom is the one exception: it clears the scene after incrementing beyond
  the deepest dungeon level and keeps the trap-chain X/Y; it does not call the
  exterior-coordinate reset table.
- **Town floor ↔ town floor.** Klimb on a ladder cell rewrites the active floor index and reloads the tile buffer from the corresponding slice of the location's per-floor pair. The scene byte does not change. NPCs on the new floor are linked into the active-object table; NPCs on the old floor are unlinked. Quick and stateless: a single tile-buffer reload, a single NPC re-link, no save-game write.
- **Dungeon level ↔ dungeon level.** Klimb on an up-ladder, down-ladder, or two-way cell, casting either of the two dungeon level-change spells, stepping on an automatic fall-trap pit, or standing on a scripted teleport changes the level index. The new level's eight-by-eight slice of DUNGEON.DAT becomes active. The scene byte does not change unless the change would carry the party past the top or bottom of the stack, in which case the exit contract runs; a fall-trap chain running past the deepest level is the separate off-bottom case.
- **Surface and underworld.** The confirmed outdoor plane swap is the surface
  fall at `(54, 138)`, which writes the underworld plane and re-initialises the
  active-object table while leaving the scene byte at the overworld value.
  The overworld spec also owns the later-traced whirlpool forced-underworld
  writer and the town-family exit branch that selects the underworld plane for
  scene byte `0x19`. The writer census is complete and identifies no outdoor
  underworld-to-surface writer at all. The dungeon exit helper does write the
  surface plane when the party leaves off the topmost level, but it is a
  dungeon-owned scene clear reached from inside a dungeon, not an outdoor
  ascent tile.
- **Any mode → combat.** A movement step onto a hostile, an encounter roll firing in the per-turn block, or a room-cell trigger inside a dungeon swaps the scene byte to the combat-class marker. Combat saves the active-object table, reloads it with combatants from a `.CBT` arena file, and runs the combat loop; exit restores the saved table and resets the scene byte to its pre-combat value. Coordinates are preserved.

## 13. Hooks into the rest of the engine

- **Active-object table.** Vehicle dismount allocates a slot for the abandoned vehicle; `vehicles.md` owns the broader parked-vehicle persistence contract. Town floor changes re-link the NPC table. Combat enter/exit replaces and restores the table wholesale.
- **Per-turn epilogue.** Door auto-close runs from the tile-effect pass. Pit triggers, chasm triggers, and energy-field triggers run from the same pass.
- **Visibility.** Door state changes mark the dirty flag so the renderer rebuilds the visibility set. Z transitions reset visibility entirely — the new floor or level paints from scratch.
- **Save image.** Scene byte, floor or level index, party chunk-X / chunk-Y, the four-byte door-close-tracker block, and the per-character Dexterity values that drive both lockpick rolls are all persisted. Loaded saves resume mid-floor, mid-dungeon, mid-vehicle, or mid-combat.
- **Spells.** Unlock Magic clears magic locks, Magic Lock applies them, and the
  Open spell steps an ordinary locked door down to its unlocked form — all three
  change lock state without keys and without arming O-Open's auto-close tracker,
  and none of them leaves an open door behind. Blink can bypass doors by
  movement when its destination is legal. The spell handlers live in a different
  overlay but write into or consult the same tile grid the door commands read,
  and in combat scenes that same lookup addresses the combat-arena terrain grid,
  so the door-facing spells can rewrite arena door tiles during a fight; see
  `systems/magic.md`.
- **Inventory.** Non-dungeon Jimmy checks key stock up front and refuses when
  it is zero. Key accounting is uniform across both rolls and both target
  families: **success never consumes a key; failure always consumes exactly
  one.** The refusal on a magic-locked door and the short-circuit on an
  already-unlocked container both take the failure path, so each of those costs
  a key too. Nothing Jimmy does can add or remove any other inventory item, and
  a failed pick never destroys a container's contents. Open does not touch
  inventory. Overworld Klimb reads the Grapple flag before it will attempt an
  outdoor climb.
- **Traps.** Chest and dungeon feature helpers can enter the shared resident
  trap-effect resolver documented in `traps.md`. This document owns the door
  and container routes that may precede that resolver; `traps.md` owns the
  common party HP/status effects once selected.
- **Time.** Door open / close, vehicle dismount, and an *applied* Klimb each consume one turn at the current mode's rate (two minutes outdoor, one minute indoor / dungeon). Jimmy attempts that reach a door, restraint, or container outcome also consume a turn, including failed attempts. A refused Klimb is the exception, and only in two of the three modes: the town handler's non-ladder refusal and both of the dungeon handler's "nothing to klimb here" refusals report "no action" and cost nothing (Section 9), whereas the overworld handler's value is not forwarded at all, so its gear and on-foot refusals still report "acted" and still cost the outdoor turn (`systems/commands.md` Section 3).

## 14. Transition Boundaries

The door and Z-transition contract is fixed for the traced baseline at command
and scene-transition depth: ordinary door Open/Jimmy behavior, magic ordinary
door opening, dungeon Word-of-Power door transmutation, outdoor Grapple Klimb,
town-floor Klimb, dungeon level changes, vehicle X-Xit boundaries, combat
enter/exit state preservation, facing-sensitive town stair tiles, and the
confirmed surface-to-underworld chasm fall are public. The plane-writer set is
**closed**: the surface fall, the whirlpool forced-underworld branch, the
scene-`0x19` interior exit at Ararat, the dungeon exit helper, and the
Moonstone-slot warp shared by moongates and Gate Travel. There is no separate
outdoor underworld-to-surface writer, and that is an exhaustive negative rather
than an unexplored area. Door, magic-lock,
secret-door, cannon-destroyed-door, and dungeon Search rewrites are covered as
visit-local tile-buffer mutations unless a named quest flag or room-clear
bitmap owns durable state. The remaining notes in this section are catalog,
data-format, or compatibility boundaries rather than missing transition
behavior.

- **Magic-lock encoding details.** The transition behavior is the adjacent
  tile-state ladder described above. Exact art labels and broader per-tile
  catalogue names for magic-locked-versus-locked variants belong to
  `catalogs/tile-catalog.md`; no traced runtime path writes a magic-lock state
  back into a cell after load.
- **Town secret-door object metadata.** Dungeon Search's pit/flavour/wall
  reveal rewrites are specified in `dungeon-mode.md`; the exact town per-map
  object encoding beyond the observed Search behavior belongs to location/object
  data-format documentation, not this transition contract.
- **Auto-close-tracker multi-door interaction.** When a player opens a second door before the first auto-closes, the first stays open for the rest of the visit. Treat this as compatibility behavior; the engine records only one pending auto-close snapshot.
- **P-Push stamp rendering.** P-Push writes floor/occupancy stamp tiles into
  the live map buffer. Save/load durability is bounded by the Push command and
  save-format specs: top-down location and overworld buffer mutations are not
  durable local-map changes across reload. The generic `0x44` stamp and the
  cannon-family `0x45` stamp both resolve to cobble through LOOK2; the byte
  distinction remains a Push-family matching rule, not an ordinary door,
  secret-door, cannon-destruction, or visual-label gap.
- **Pit-chain and trap-door edge states.** Dungeon chained-pit off-bottom clears
  the scene byte with the incremented off-bottom level and same X/Y still in
  resident state. The transition-state mutation is covered, and stock
  `DUNGEON.DAT` has no level-seven fall trap or same-column vertical fall-trap
  run that reaches level seven, so this edge is defensive compatibility for
  custom or mutated dungeon data in the analyzed baseline. Trap-door / chute
  encoding in towns is similarly observed only by behaviour.
- **X-Xit vehicle landing predicates.** X-it's nearby-support predicate is now
  specified in `vehicles.md`; this document only owns the Z-transition boundary
  around ordinary vehicle dismounts.
- **Dungeon spell escape.** *Resolved, and the earlier negative is withdrawn.*
  The two dungeon level-change spells do clear the dungeon scene: cast at a
  level edge they hand off to the same surface-reset helper a ladder would, so
  Down on the lowest level exits to the Underworld and Up on the topmost level
  exits to Britannia, in every dungeon except Doom, where both spells refuse to
  run. `systems/dungeon-mode.md` Section 13 owns the contract and
  `catalogs/spell-list.md` the two spell rows.

## 15. Sources

The behaviour described here was derived from the private function notes listed below, with sibling specs used as cross-checks where noted. This public document paraphrases observed behaviour and field roles; it does not reproduce private source, decompiler output, assembly excerpts, raw dumps, private address tables, or implementation listings.

- The J-Jimmy command's tile cascade, dungeon-mode routing, and the encoding of the door tile pairs — derived from `u5-decomp/functions/SJOG_OVL/0x0D4A_sjog_jimmy.md`, `u5-decomp/functions/SJOG_OVL/0x0C3E_sjog_jimmy_inner.md`, and `u5-decomp/functions/SJOG_OVL/OVERVIEW.md`.
- The reconciliation of the two lock-pick rolls into one contract: that both read the acting member's Dexterity rather than any class field; the thirty-outcome zero-based die and its clamped Dexterity-over-thirty success chance; the corrected target families (locked doors and restraints on the flat test, containers on the threshold test, the magic-locked door refused with no roll, and no pickpocket anywhere in the command); the strictly-greater comparison on the threshold test; the depth doubling existing only on the dungeon path; the uniform "success spends no key, failure spends one" accounting; and the restraint case's prisoner-release outcome. Source provenance: derived from private analysis note `u5-decomp/notes/oq-closures_2026-08-22_sjog-traps-locks.md`.
- The per-map container's lock/trap flag, its threshold formula, and the fact
  that a failed pick leaves the container completely untouched while a
  successful pick clears the lock/trap flag and preserves the content class --
  derived from `u5-decomp/functions/SJOG_OVL/0x0BAA_sjog_object_table_action.md`
  and `u5-decomp/notes/oq-closures_2026-08-22_sjog-traps-locks.md`.
- The O-Open command's tile cascade, the auto-close countdown's record format and decrement, the pre-flight gate shared with Jimmy and Search, and the route to the chest-on-floor helper — derived from `u5-decomp/functions/SJOG_OVL/0x1374_sjog_open.md`.
- The magic Open/Unlock helper's ordinary wooden-door tile rewrites,
  Space/Pass no-effect branch, dirty marking, and separation from O-Open's
  auto-close/chest/trap handling -- derived from
  `u5-decomp/functions/CAST2_OVL/0x0768_open_door.md` and the CAST spell map in
  `u5-decomp/functions/CAST_OVL/all_spells.md`.
- The S-Search command's secret-door reveal path, the per-map object table layout, and the dungeon-mode high-nibble cascade — derived from `u5-decomp/functions/SJOG_OVL/0x095C_sjog_search.md`.
- The CMDS overlay's overworld K-Klimb handler, including its gear gate, on-foot check, target-tile refusals, fall rolls, and final climb/move call — derived from `u5-decomp/functions/CMDS_OVL/0x1C20_cmds_klimb.md`.
- The conversation byte-action mapping that sets the Grapple/Klimb gear flag
  and the conversation graph that points from Bidney to Lord Michael's grant --
  derived from `u5-decomp/functions/TALK_OVL/0x0682_action_command_dispatch.md`,
  `u5-decomp/functions/TALK_OVL/0x0F32_tlk_byte_runner.md`, and
  `u5-decomp/notes/tlk-quest-graph.md`.
- The CMDS overlay's X-Xit vehicle handler with its scene refusal, vehicle
  family branches, nearby-land validation, ship skiff/carpet transfer cases,
  and parked-object state preservation -- derived from
  `u5-decomp/functions/CMDS_OVL/0x0EB4_cmds_xit_vehicle.md`.
- The combat-only ownership of the "Escape" / "Not here!" / "Not yet!" wording,
  which belongs to the Escape-key handler rather than to the `X` letter, used
  here only to avoid conflating it with dungeon Z transitions -- derived from
  `u5-decomp/functions/CMDS_OVL/0x17EC_cmds_escape.md`.
- The mode-aware routing of K-Klimb across CMDS, TOWN, and DUNGEON overlays; the "BOOOM!" / "Door destroyed!" string association with F-Fire's ship-cannon path; and the verb-prefix scheme that the dispatcher prints before each per-letter handler — derived from `u5-decomp/functions/ULTIMA_EXE/0x3178_command_dispatcher.md`.
- Source provenance: the shared dungeon exit contract and its plane rule, the
  correction that a climb does not test its destination cell, the level-change
  spells' route to the same exit, and the closed plane-writer census are derived
  from private analysis note
  `u5-decomp/notes/oq-closures_2026-08-22_world-transitions.md`.
- The dungeon-tile high-nibble class table including up-ladder, down-ladder, two-way ladder, pit/trap, and heavy-door classes; the exact `0x61`/`0x69` fall-trap and `0x62`/`0x6A` bomb-trap post-action behaviour; and the dungeon Klimb's Z-axis behaviour with boundary refusals separated from surface-reset and pit-chain off-bottom exits, together with that handler's turn cost - applied climbs, pit falls, and a cancelled prompt count as an action while both "nothing to klimb here" refusals do not, and the two refusals are distinct (`systems/dungeon-mode.md` Section 13.1) — derived from `u5-decomp/functions/DUNGEON_OVL/0x1E10_dungeon_klimb_dispatch.md`, `u5-decomp/functions/DUNGEON_OVL/0x1C6A_dungeon_klimb_apply.md`, `u5-decomp/functions/DUNGEON_OVL/0x1D08_dungeon_fall_pit.md`, `u5-decomp/functions/DUNGEON_OVL/0x0A4C_dungeon_pit_chain.md`, `u5-decomp/functions/DUNGEON_OVL/0x0C76_dungeon_post_action.md`, and `u5-decomp/functions/DNGLOOK_OVL/0x0000_dnglook_l_look.md`.
- The shared resident trap-effect resolver used after a chest trap has been
  selected, including the fact that the caller passes no trap flavour -- derived
  from `u5-decomp/functions/ULTIMA_EXE/0x2FD0_trap_effect.md` and sibling
  resident party-damage and status helper notes.
- The town-mode floor-pair encoding and the per-location NPC re-linking on floor change — derived from `u5-decomp/functions/TOWN_OVL/0x11F0_town_entry_setup.md`.
- The town-family grid-boundary exit prompt (and the withdrawal of the earlier
  "exit threshold tile" reading of it), its scene clear, exterior coordinate
  lookup, and scene-`0x19` underworld-plane selection -- derived from
  `u5-decomp/functions/TOWN_OVL/0x0600_town_movement_handler.md`.
- The facing-sensitive town stair family and floor-change reload path --
  derived from `u5-decomp/functions/TOWN_OVL/0x052E_town_movement_log.md`,
  cross-checked against `u5-decomp/functions/TOWN_OVL/0x0600_town_movement_handler.md`.
- The chasm and underworld transition encoding — derived from sibling spec
  `u5-spec/systems/overworld.md` and the traced OUTSUBS falls-handler note in
  `u5-decomp/functions/OUTSUBS_OVL/0x0458_outsubs_falls_handler.md`.
- The active-object table contract that vehicle dismount and floor changes consult — derived from sibling spec `u5-spec/systems/active-objects.md`.
- The broader vehicle command and persistence contract — derived from sibling spec `u5-spec/systems/vehicles.md`.
- The world-clock advance contract that doors, climb, and dismount each consume — derived from sibling spec `u5-spec/systems/time.md`.
