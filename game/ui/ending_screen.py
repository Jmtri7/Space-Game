"""The end-of-game epilogue screen.

Shown by main.py when an `"end_story:<id>"` dialogue action has set the
`story_over` / `ending:<id>` flags (see game/world/dialogue.py,
utils.resolve_ending). It's a `ReportMenu` - the same full-panel scrolling
text frame the Possessions / Mission Log use - with one **Return to Menu**
button instead of Close. `ending_report()` assembles the text from the
story's `endings.json` entry plus the player's final standing with each
faction, so the same ending reads differently depending on how the run
went. A faction block may also carry `"flag:<name>"` lines that win over
the standing band when that flag is set (e.g. `the_long_silence`'s
`front_to_*` / `signal:*` choices).
"""
from game.constants import WHITE
from game.ui.report_menu import ReportMenu
from game.utils import get_endings, get_factions

# Standing -> which per-faction epilogue line to use (see endings.json's
# "faction_epilogue"). Mirrors report_menu.REP_BANDS but collapsed to the
# three buckets an ending actually distinguishes.
_BAND = [(-25, "hostile"), (25, "neutral"), (1e9, "allied")]

HEAD_COLOR = (200, 220, 255)
BODY_COLOR = (215, 215, 215)
FACTION_COLOR = (200, 210, 190)


def _band(standing):
    for ceiling, name in _BAND:
        if standing < ceiling:
            return name
    return "neutral"


def ending_report(story, ending_id, possessions):
    """`(title, columns)` for a one-column `ReportMenu` - the ending's
    title + epilogue paragraphs, then one line per faction chosen by the
    player's final standing with it. Falls back to a generic finish for an
    unknown ending id or a story with no endings.json."""
    ending = get_endings(story).get(ending_id, {})
    title = ending.get("title", "The End")

    sections = []
    epilogue = ending.get("epilogue", ["The story ends here."])
    if isinstance(epilogue, str):
        epilogue = [epilogue]
    sections.append(("", [(para, BODY_COLOR) for para in epilogue]))

    faction_epilogue = ending.get("faction_epilogue", {})
    lines = []
    for faction_id, faction in get_factions(story).items():
        band = _band(possessions.reputation_with(faction_id))
        entry = faction_epilogue.get(faction_id, {})
        # A "flag:<name>" key wins over the standing band when its flag is
        # set (first such key in file order wins - e.g. the Phase 3/4
        # front_to_* / signal:* choices in the_long_silence). The three
        # band keys are always present as the fallback.
        text = next((val for key, val in entry.items()
                     if key.startswith("flag:") and possessions.flags.get(key[5:])), None)
        if text is None:
            text = entry.get(band)
        if text:
            lines.append((f"{faction.get('name', faction_id)}: {text}", FACTION_COLOR))
    if lines:
        sections.append(("How they remember you", lines))

    return title, [sections]


class EndingScreen(ReportMenu):
    """A `ReportMenu` whose only action returns to the main menu."""
    def buttons(self):
        return [("menu", "Return to Menu", WHITE, False)]


def game_over_report(cargo_lost):
    """`(title, columns)` for the Game Over screen shown by main.py when
    SpaceScreen.update() returns "game_over" (see
    SpaceScreen._on_player_destroyed). Same one-column `ReportMenu` shape as
    `ending_report()`, just not story/endings.json-driven - the run ends on
    hull loss, no faction epilogue to show."""
    lines = [("Your ship was destroyed.", BODY_COLOR)]
    if cargo_lost:
        lines.append((f"Cargo lost: {cargo_lost}.", BODY_COLOR))
    return "Game Over", [[("", lines)]]
