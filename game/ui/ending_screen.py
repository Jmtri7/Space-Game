"""The end-of-game epilogue screen.

Shown by main.py when an `"end_story:<id>"` dialogue action has set the
`story_over` / `ending:<id>` flags (see game/world/dialogue.py,
utils.resolve_ending). It's a `ReportMenu` - the same full-panel scrolling
text frame the Possessions / Mission Log use - with one **Return to Menu**
button instead of Close. `ending_report()` assembles the text from the
story's `endings.json` entry plus the player's final standing with each
faction, so the same ending reads differently depending on how the run
went.
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
        text = faction_epilogue.get(faction_id, {}).get(band)
        if text:
            lines.append((f"{faction.get('name', faction_id)}: {text}", FACTION_COLOR))
    if lines:
        sections.append(("How they remember you", lines))

    return title, [sections]


class EndingScreen(ReportMenu):
    """A `ReportMenu` whose only action returns to the main menu."""
    def buttons(self):
        return [("menu", "Return to Menu", WHITE, False)]
