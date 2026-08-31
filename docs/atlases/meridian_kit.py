"""The Meridian Free Ports - full frontier atlas content. Brass, lantern hulls, ornamented. Strokeless. See culture_common.py."""
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, opoly, ocirc, bar, ngon
from culture_common import grid_bg, ribbon, opoly_s, dot_run, groove, stencil, label
from frontier_ships import meridian
from frontier_outfits import meridian as outfit_fn

BRASS = "#e8ce96"
SHIPS = {"meridian": (meridian, "Meridian Argosy", "galleon")}
STATION = {"station": (lambda P: meridian(P), "Trade-Port Ring", "station")}
BUILDINGS = {
    "counting_house": (lambda P: grid_bg() + opoly(rrect(52, 80, 96, 88, 3), P["hull"], d=1.6) + opoly(rrect(66, 94, 68, 60, 2), P["hull_lo"], d=1.0) + bar(56, 80, 144, 80, 1.4, P["trim"]), "Counting House", "trade"),
    "mansion": (lambda P: grid_bg() + opoly(rrect(46, 70, 108, 100, 4), P["hull"], d=1.8) + bar(50, 70, 150, 70, 1.6, P["trim"]), "Factor Mansion", "admin"),
}
FURNITURE = {
    "trade_counter": (lambda P: grid_bg() + opoly(rrect(50, 110, 100, 24, 2), P["hull_lo"], d=1.2) + opoly(rrect(56, 78, 88, 20, 1), P["glass"], d=0.8), "Trade Counter", "desk"),
    "display_plinth": (lambda P: grid_bg() + opoly(rrect(80, 120, 40, 40, 2), P["hull"], d=1.3) + bar(78, 120, 122, 120, 1.2, P["trim"]), "Display Plinth", "pedestal"),
}
OUTFITS = {"meridian": (outfit_fn, "Free-Port Factor", "captain")}
LAYOUTS = {
    "port": (lambda P: grid_bg(320, 200) + opoly(rrect(40, 60, 240, 100, 4), "#8a6a44", d=1.4) + bar(160, 50, 160, 170, 3, P["trim"]) + label([(100, 30, "CONCOURSE"), (220, 30, "WAREHOUSES")], "#c9bfae"), "Trade-Port interior", "station floor plan"),
    "city": (lambda P: grid_bg(320, 200) + opoly(rrect(50, 50, 80, 70, 2), "#96744a", d=1.2) + opoly(rrect(180, 70, 100, 80, 2), "#96744a", d=1.2) + ribbon([(90, 85), (180, 110)], 2.8, "#8a7a5c") + label([(90, 30, "MANSIONS"), (230, 40, "DOCKS")], "#c9bfae"), "Meridian colony", "moon settlement plan"),
}
