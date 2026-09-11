# Mining 101

A short, standalone tutorial story with no arc beyond its one lesson: dock at
Prospect Ring with a ship already in hand, let Harlan Cobb (the dock chief)
walk you through buying and mounting a laser cannon, then fly out into the
belt to mine ore and sell it back at the ring.

Built as the first user of [`system-events`](../../modules/system-events)
(see [docs/architecture/config-formats.md](../../../docs/architecture/config-formats.md#system-events)):
`systems/prospect_belt.json`'s `"events"` block lists `rich_ore_vein` at a
12%-per-chunk chance, so a rare, richer-colored asteroid sometimes turns up
alongside the ordinary gray rock - the mission's third stage calls it out,
but finding one isn't required to complete the tutorial.

One mission (`mining_101`, see `missions.json`), five stages, all driven by
generic gameplay-event flags (`bought_outfit:laser_cannon`,
`installed_outfit:laser_cannon`, `collected_ore`, `landed_on_landing_site`,
`sold_commodity:ore`) - no story-specific Python, same pattern as
`default`'s `first_flight`.

Reuses `orbital-std` (the trade-ring station art, the courier ship) and
`figures-human` wholesale; the only story-owned config is `story.json`,
`missions.json`, `commodities.json` (just `"ore"`), and the one system.
