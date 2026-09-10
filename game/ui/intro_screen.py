"""The post-story-selection intro screen.

Shown by main.py between the pilot-name dialog and the first playable screen,
for any story whose story.json carries an `"intro"` block
(`{"title": ..., "body": [paragraph, ...]}`). Mirrors EndingScreen: a
`ReportMenu` - the same full-panel scrolling text frame - with one **Begin**
button instead of Close. `intro_report()` pulls the paragraphs from the story
and substitutes `{pilot}` with the name the player just entered, so the
opening addresses them directly.
"""
from game.constants import WHITE
from game.ui.report_menu import ReportMenu
from game.utils import get_story

BODY_COLOR = (215, 215, 215)


def has_intro(story):
    """True when this story defines an `"intro"` block with at least one
    paragraph - main.py only routes through IntroScreen when it does."""
    intro = get_story(story).get("intro", {})
    body = intro.get("body", [])
    if isinstance(body, str):
        body = [body]
    return bool(body)


def intro_report(story, pilot_name):
    """`(title, columns)` for a one-column `ReportMenu` - the story's intro
    title and paragraphs, with `{pilot}` filled in."""
    intro = get_story(story).get("intro", {})
    title = intro.get("title", get_story(story).get("name", "A New Game"))
    body = intro.get("body", [])
    if isinstance(body, str):
        body = [body]
    paras = [(para.replace("{pilot}", pilot_name or "pilot"), BODY_COLOR)
             for para in body]
    return title, [[("", paras)]]


class IntroScreen(ReportMenu):
    """A `ReportMenu` whose only action starts the game."""
    def buttons(self):
        return [("begin", "Begin", WHITE, False)]
