# The Long Silence — story bible

The narrative source of truth. `PLAN.md` is the build checklist; this file is
what we're building. Keep them in step.

## Premise

Two centuries ago the **Relay** — a network of jump-beacons that let ships cross
between stars in hours instead of lifetimes — went dark, all at once, for
reasons no one alive remembers. The linked systems drifted into isolation and
grew strange. Now the beacons are flickering back on, one by one, and the
player flies between worlds that have spent 200 years becoming foreign to each
other. Every system re-contacted has to decide what the Relay coming back
*means* — reunion, invasion, or a debt finally coming due.

**The through-line:** someone, or something, is switching the beacons back on
deliberately, working outward from the old network core. The player is usually
one jump ahead of that signal, arriving just before a system realises it is no
longer alone.

## The systems

### Halcyon — start
Well-kept orbital stations around a yellow star, run by the **Harbor
Authority**, descendants of the Relay's original traffic controllers. They kept
their records, their uniforms, and their sense of being the rightful centre of
a civilisation that no longer exists. Polite, bureaucratic, quietly desperate
to matter again. They give the player the first job: go find out what is on the
other end of the beacon that just lit.

### Kiln
A red-dwarf system — one scorched inner world, deep-mine settlements under the
moons. The **Ninefold Combine**, a guild-state where every person belongs to a
trade lineage and a contract is sacred to the point of religion. They survived
isolation by rationing everything and enforcing it brutally. They do not want
the Relay back; reconnection means outside competition, and they have already
voted on how to handle ships that will not leave.

### Verdance
A gas giant with a single enormous cloud-city and a ring of agricultural
habitats. The **Drift**, a loose, consensus-run culture that went the opposite
way from Kiln: no fixed hierarchy, decisions by rolling assembly, deeply
suspicious of anyone who gives orders. The most welcoming system and the least
able to actually commit to anything — which becomes a problem when Kiln's
warships arrive.

### Ossuary
A dead system. One habitable moon, abandoned stations, and the **Vigil**: a
monastic order of maybe three hundred people who stayed behind to maintain the
graves and the archives of everyone who did not survive the first decades of
the Silence. They know the most true history of anyone. They believe the Relay
went dark on purpose, to contain something, and that turning it back on is a
catastrophe. They may be right.

### The Span — the old network core
A ringworld fragment around a blue-white star, still powered, mostly automated,
sparsely inhabited by the **Wardens** — not a government but a maintenance cult
grown up around machinery they operate and no longer understand. This is where
the reactivation signal originates. Whether there is a person behind it, an AI,
or just a 200-year-old script finishing its run is the story's central question.

## Factions (cross-system)

- **The Harbor Authority** wants a restored Relay with itself at the hub — a
  second empire, administered from Halcyon.
- **The Ninefold Combine** wants the beacons destroyed and the systems sealed,
  each to its own star.
- **Free carriers** — independent traders and salvagers (the wandering AI ships
  already in the sim) — want the Relay open and *ungoverned*. They have run
  slow-boat routes between systems for generations; the fast lanes returning is
  either their golden age or the end of their livelihood.
- **The Vigil** wants the reactivation stopped and the reason for the original
  shutdown understood before anyone acts.

The player is courted by all of them and can end up carrying water for any.

## Act structure

1. **Contact.** Follow the newly-lit beacons outward. Each system is a
   self-contained arrival: learn the culture, do work for locals, decide how
   much to tell them about what is coming behind you.
2. **Pressure.** The reactivation signal keeps moving. Kiln mobilises. The
   Drift dithers. Refugees and opportunists start moving between systems on the
   half-restored network, and the player runs cargo, people, and messages
   through a region deciding whether to have a war.
3. **The Span.** Reach the core. Find out what is turning the lights back on
   and what the Silence was hiding.

## The reason for the Silence

The Vigil's archive and the Span's machinery together reveal *why* the Relay
shut down. The honest options — pick one in Phase 8, or leave it a genuine
dialogue-reveal the player weighs:

- **Quarantine** — something came through the Relay and the network was severed
  to trap it. Reconnecting frees it.
- **Scorched earth** — a civil war's final act; the shutdown was an atrocity
  everyone has spent two centuries mythologising.
- **Accident** — it just broke, and 200 years of isolation built a religion
  around the silence.

## The ending fork

The player's final choice, gated by standing with each faction:

- **Restore it** — fast travel returns, and with it whichever faction is
  positioned to control the hub. A connected region, unequal and unstable.
- **Sever it for good** — destroy the core. The systems stay islands, each
  keeping its own strange culture; trade returns to the slow carriers and their
  decades-long loops.
- **Hold the middle** — keep the beacons but break the hub, so no single system
  can dominate the network. The hardest to reach; requires having kept enough
  factions trusting the player through Act II.

The player's reputation with each culture — built through the small
station-and-moon work the game already models — decides who backs which ending
and whether it holds.

## Beacon / system unlock order

```
Halcyon (start, Beacon 1 already lit)
  → Kiln       (Beacon 2 — lit by finishing Halcyon's anchor mission)
  → Verdance   (Beacon 3)
  → Ossuary    (Beacon 4)
  → The Span   (Hub — lit mid-Act II once the player has real standing with >=1 faction)
```

Free carriers are a faction, not a system — their pilots appear across all five.
