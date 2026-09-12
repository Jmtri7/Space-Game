"""Mission-computer missions - randomized haul/bounty/scan offers rolled up
at a terminal (see game/ui/mission_board_menu.py), as opposed to the
hand-authored, fixed-parameter missions in a story's missions.json (see
game/world/mission.py). This module stays pygame/UI-free, same discipline
as mission.py.

A generated mission is a plain dict - there's no static config to define it
against (that's the whole point: its parameters are rolled per-offer), so
the dict itself is the definition *and* is what gets persisted (see
Possessions.generated_missions/completed_generated_missions). Shape, all
types:
    {"uid", "kind" ("haul"/"bounty"/"scan"), "title", "description", "reward"}
plus per-kind fields:
    haul:   "commodity_id", "qty", "dest_system_id", "dest_label"
    bounty: "system_id", "system_label"
    scan:   "system_id", "system_label", "x", "y"

Completion is driven by whichever gameplay event matches the kind - docking
with enough cargo at the right place (see complete_haul_if_delivered,
called from SpaceScreen._mark_landed), destroying a hostile ship in the
right system (see complete_bounty_on_kill, called from
combat.py._destroy_ship), or flying within range of the right coordinate
(see complete_scan_in_range, called each frame from
SpaceScreen.update_physics). Each returns the list of mission dicts it just
completed, so the caller can toast/announce them - mirrors mission.py's
check_mission_progress() returning newly-advanced stages for the same
reason.
"""
import math
import random
import uuid
from game.constants import GAME_WIDTH, GAME_HEIGHT
from game.utils import get_star_systems, get_commodity, load_json
from game.config_source import story_catalogue
from game.world.asteroid_field import CHUNK_SIZE, CHUNK_MARGIN, CHUNK_KEEP_RADIUS

HAUL_PRICE_PER_UNIT_BONUS = 6   # on top of the commodity's own base_price, per unit hauled
BOUNTY_REWARD_RANGE = (300, 700)
SCAN_REWARD_RANGE = (150, 350)
SCAN_RANGE = 200          # world units - how close counts as "at the anomaly"
SCAN_COORD_SPREAD = 2200  # world units from system center a scan target can roll


def _system_has_dock(story, system_id):
    """True if system_id's own config actually defines a "station" or
    "moon" block - get_star_systems() always reports a station_name/
    moon_name (defaulted to "Station"/"Moon"), so it can't be used to tell
    a real landing site from a system that has none (see
    docs/architecture/config-formats.md)."""
    data = load_json(f"config/stories/{story}/systems/{system_id}.json")
    return bool(data and (data.get("station") or data.get("moon")))


def _dockable_systems(story):
    """{system_id: (label, kind)} for every system in the story that has an
    actual station or moon to land on and haul cargo to - kind is
    "station"/"moon" (a system with both counts as "station", matching
    which one a haul mission names)."""
    out = {}
    for system_id, info in get_star_systems(story).items():
        if not _system_has_dock(story, system_id):
            continue
        data = load_json(f"config/stories/{story}/systems/{system_id}.json")
        if data.get("station"):
            out[system_id] = (data["station"].get("name", info["name"]), "station")
        else:
            out[system_id] = (data["moon"].get("name", info["name"]), "moon")
    return out


def _roll_haul(story, cargo_capacity, current_system_id):
    """A haul offer to some *other* dockable system, or None if this story
    has nowhere else to haul to (e.g. a single-station lesson like
    mining_101 - see generate_missions)."""
    docks = _dockable_systems(story)
    docks.pop(current_system_id, None)
    if not docks:
        return None
    commodities = story_catalogue(story, "commodities.json")
    if not commodities:
        return None
    commodity_id = random.choice(list(commodities.keys()))
    commodity = get_commodity(story, commodity_id)
    qty = random.randint(1, max(1, cargo_capacity))
    dest_system_id, (dest_label, _kind) = random.choice(list(docks.items()))
    reward = qty * (commodity.get("base_price", 10) + HAUL_PRICE_PER_UNIT_BONUS)
    name = commodity.get("name", commodity_id)
    return {
        "kind": "haul",
        "title": f"Haul {qty} {name} to {dest_label}",
        "description": f"Deliver {qty} unit(s) of {name} to {dest_label} in the "
                        f"{get_star_systems(story).get(dest_system_id, {}).get('name', dest_system_id)} system.",
        "reward": reward,
        "commodity_id": commodity_id,
        "qty": qty,
        "dest_system_id": dest_system_id,
        "dest_label": dest_label,
    }


def _roll_bounty(story, current_system_id):
    """A "clear out hostiles in <system>" offer - any system in the story
    (including the current one) is fair game; a system tagged
    "hazard": "pirates" (see get_star_systems) is favored since that's
    where a pirate_ambush event actually spawns something to fight."""
    systems = get_star_systems(story)
    if not systems:
        return None
    hazardous = [sid for sid, info in systems.items() if info.get("hazard") == "pirates"]
    system_id = random.choice(hazardous) if hazardous and random.random() < 0.7 else random.choice(list(systems))
    label = systems[system_id]["name"]
    reward = random.randint(*BOUNTY_REWARD_RANGE)
    return {
        "kind": "bounty",
        "title": f"Bounty: hostiles in {label}",
        "description": f"Destroy a hostile ship in the {label} system.",
        "reward": reward,
        "system_id": system_id,
        "system_label": label,
    }


def _roll_scan(story, current_system_id):
    """A "fly to this empty coordinate and scan" offer - always in the
    system the terminal is in, since there's no in-world way to point the
    player at a coordinate in a system they haven't jumped to yet (see
    game/screens/space_screen/hud.py's mission-arrow handling)."""
    systems = get_star_systems(story)
    label = systems.get(current_system_id, {}).get("name", current_system_id)
    angle = random.uniform(0, 2 * math.pi)
    dist = random.uniform(SCAN_COORD_SPREAD * 0.4, SCAN_COORD_SPREAD)
    x = GAME_WIDTH / 2 + dist * math.cos(angle)
    y = GAME_HEIGHT / 2 + dist * math.sin(angle)
    reward = random.randint(*SCAN_REWARD_RANGE)
    return {
        "kind": "scan",
        "title": f"Scan anomaly in {label}",
        "description": f"Fly to the marked coordinate in {label} and scan the anomaly - "
                        f"press T to cycle to the MISSIONS targeting mode and home in on it.",
        "reward": reward,
        "system_id": current_system_id,
        "system_label": label,
        "x": x,
        "y": y,
    }


def generate_missions(story, cargo_capacity, current_system_id, count=3):
    """A fresh batch of up to `count` mission offers (haul/bounty/scan, one
    roll each in that order, skipping a kind that can't be rolled - e.g.
    haul on a single-station story) for the mission board to show. Offers
    are plain dicts with no "uid" yet - accept_mission() assigns one only
    once the player actually takes it, so browsing the board never mutates
    Possessions."""
    rollers = [
        lambda: _roll_haul(story, cargo_capacity, current_system_id),
        lambda: _roll_bounty(story, current_system_id),
        lambda: _roll_scan(story, current_system_id),
    ]
    offers = []
    for roll in rollers[:count]:
        offer = roll()
        if offer:
            offers.append(offer)
    return offers


def accept_mission(possessions, offer):
    """Commit one offer (from generate_missions) into
    possessions.generated_missions under a fresh uid. Returns the uid."""
    uid = uuid.uuid4().hex[:10]
    mission = dict(offer)
    mission["uid"] = uid
    possessions.generated_missions[uid] = mission
    return uid


def abandon_mission(possessions, uid):
    """Drop an active generated mission without paying out or completing
    it - the mission-board counterpart to mission.py's abandon_mission()."""
    possessions.generated_missions.pop(uid, None)


def _finish(possessions, uid, mission):
    del possessions.generated_missions[uid]
    mission = dict(mission, status="complete")
    possessions.completed_generated_missions.append(mission)
    possessions.earn(mission.get("reward", 0))
    return mission


def complete_haul_if_delivered(possessions, system_id, dock_kind):
    """Call when the player docks (dock_kind "station"/"moon") in
    system_id - completes and pays out every active haul mission whose
    destination matches and whose cargo qty is on hand, consuming that
    cargo. Returns the list of completed mission dicts."""
    completed = []
    for uid, mission in list(possessions.generated_missions.items()):
        if mission.get("kind") != "haul":
            continue
        if mission.get("dest_system_id") != system_id:
            continue
        commodity_id, qty = mission.get("commodity_id"), mission.get("qty", 0)
        if possessions.cargo.get(commodity_id, 0) < qty:
            continue
        possessions.remove_cargo(commodity_id, qty)
        completed.append(_finish(possessions, uid, mission))
    return completed


def complete_bounty_on_kill(possessions, system_id):
    """Call when a hostile ship is destroyed in system_id (see
    combat.py._destroy_ship) - completes and pays out one matching active
    bounty mission (first match; a player running several bounties in the
    same system clears them one kill at a time). Returns the list (0 or 1
    items) of completed mission dicts."""
    for uid, mission in possessions.generated_missions.items():
        if mission.get("kind") == "bounty" and mission.get("system_id") == system_id:
            return [_finish(possessions, uid, mission)]
    return []


def _chunk_of(v):
    return math.floor(v / CHUNK_SIZE)


def anomaly_marker_visible(mission_x, mission_y, player_x, player_y):
    """Whether a scan-anomaly's glow orb (see
    game/world/anomaly_marker.py) should still be drawn this frame.

    An *active* (not-yet-scanned) mission's marker is never gated by this -
    it's always drawn while its system is the one in view (see
    SpaceScreen.draw), so an anomaly can never disappear before its
    mission actually completes. This function only decides how long the
    marker lingers *after* completion: it reuses AsteroidField's own
    chunk-keep math (CHUNK_SIZE/CHUNK_MARGIN/CHUNK_KEEP_RADIUS - see
    asteroid_field.py) so a freshly-scanned anomaly fades out of the world
    exactly the way any other piece of local scenery would once you fly
    far enough away, rather than blinking out the instant it's scanned."""
    keep = CHUNK_MARGIN + CHUNK_KEEP_RADIUS
    return (abs(_chunk_of(mission_x) - _chunk_of(player_x)) <= keep
            and abs(_chunk_of(mission_y) - _chunk_of(player_y)) <= keep)


def complete_scan_in_range(possessions, system_id, player_x, player_y):
    """Call every frame (see SpaceScreen.update_physics) - completes and
    pays out every active scan mission in system_id whose coordinate the
    player is currently within SCAN_RANGE of. Returns the list of
    completed mission dicts.

    Completion (moving the mission to completed_generated_missions, paying
    the reward) happens the instant the player is in range - only the
    marker's on-screen *lingering* afterward is deferred, and only for as
    long as the player stays nearby (see anomaly_marker_visible)."""
    completed = []
    for uid, mission in list(possessions.generated_missions.items()):
        if mission.get("kind") != "scan" or mission.get("system_id") != system_id:
            continue
        dx, dy = mission["x"] - player_x, mission["y"] - player_y
        if (dx * dx + dy * dy) ** 0.5 <= SCAN_RANGE:
            completed.append(_finish(possessions, uid, mission))
    return completed


class MissionWaypoint:
    """Duck-typed stand-in for a real WorldObject, so a scan mission's
    coordinate - nothing is actually there - can be targeted, bracketed,
    and pointed at by the arrow through the exact same code every real
    targetable object goes through (see space_screen/targeting.py's
    "MISSIONS" target mode and hud.py's _draw_target_arrow)."""
    size = 24

    def __init__(self, x, y, name):
        self.x, self.y, self.name = x, y, name

    def get_distance(self, target_x, target_y):
        return ((self.x - target_x) ** 2 + (self.y - target_y) ** 2) ** 0.5


def scan_waypoints(possessions, system_id):
    """[(label, MissionWaypoint)] for every active scan mission whose
    coordinate is in system_id - the "MISSIONS" target mode's entries (see
    space_screen/targeting.py._filtered_targets). Only scan missions have
    an actual point to aim at; haul missions' destination is already
    targetable as an ordinary landing site once you're in that system, and
    a bounty has no single point (it's "any hostile in this system")."""
    out = []
    for mission in possessions.generated_missions.values():
        if mission.get("kind") == "scan" and mission.get("system_id") == system_id:
            out.append((mission["title"], MissionWaypoint(mission["x"], mission["y"], mission["title"])))
    return out


def mission_status_lines(possessions):
    """[(title, [description], None)] for every active + completed
    generated mission - shaped like mission.py's mission_status_lines() (a
    single "stage" per mission, since these don't have multi-step stages)
    so report_menu.mission_report() can merge the two without knowing the
    difference."""
    lines = []
    for mission in possessions.generated_missions.values():
        lines.append((mission["title"], [mission.get("description", "")], 0))
    for mission in possessions.completed_generated_missions:
        lines.append((mission["title"] + " (Complete)", [mission.get("description", "")], None))
    return lines
