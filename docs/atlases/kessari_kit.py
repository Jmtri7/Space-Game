"""The Ashfall Rite - full frontier atlas content. Carved dark reliquary, ember seam, ceremonial. Strokeless. See culture_common.py."""
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, opoly, ocirc, bar, ngon
from culture_common import grid_bg, ribbon, opoly_s, dot_run, groove, stencil, label
from frontier_ships import kessari
from frontier_outfits import kessari as outfit_fn

G = "#ff823c"
SHIPS = {"kessari": (kessari, "Kessari Reliquary", "reliquary")}
STATION = {"station": (lambda P: kessari(P), "Void Reliquary", "station")}
BUILDINGS = {
    "shrine": (lambda P: grid_bg() + opoly(ngon(100, 140, 24, 32, 18), P["hull"], d=1.6) + ribbon([(76, 126), (100, 100), (124, 126)], 2, P["trim"]), "Shrine Monolith", "temple"),
    "cell": (lambda P: grid_bg() + opoly(rrect(60, 100, 80, 80, 2), P["hull"], d=1.6), "Pilgrim Cell", "hab"),
}
FURNITURE = {
    "ember_brazier": (lambda P: grid_bg() + opoly(ngon(100, 120, 18, 12, 16), P["hull_lo"], d=1.2) + circ(100, 120, 6, G, op=0.4), "Ember Brazier", "fire"),
    "kneeling_rail": (lambda P: grid_bg() + bar(60, 120, 140, 120, 3, P["hull_lo"]), "Kneeling Rail", "altar"),
}
OUTFITS = {"kessari": (outfit_fn, "Ashfall Adept", "pilgrim")}
LAYOUTS = {
    "station": (lambda P: grid_bg(320, 200) + circ(160, 100, 60, "#2a2432") + bar(50, 100, 270, 100, 2, G) + label([(100, 50, "CHAPEL"), (220, 50, "CELLS")], "#8a7a5c"), "Reliquary interior", "station floor plan"),
    "pilgrimage": (lambda P: grid_bg(320, 200) + circ(80, 80, 30, "#3a3240") + circ(160, 140, 32, "#3a3240") + circ(240, 90, 28, "#3a3240") + ribbon([(80, 110), (160, 110), (240, 118)], 2.2, "#5a4a5c"), "Pilgrimage route", "moon settlement plan"),
}
