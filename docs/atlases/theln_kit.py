"""The Theln Drift - full frontier atlas content. Membrane on frame, running lights, kite-like. Strokeless. See culture_common.py."""
import sys, pathlib, math
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import poly, circ, rrect, opoly, ocirc, bar, ngon
from culture_common import grid_bg, ribbon, opoly_s, dot_run, groove, stencil, label
from frontier_ships import theln
from frontier_outfits import theln as outfit_fn

TEAL = "#7fe8e8"
SHIPS = {"theln": (theln, "Theln Kite", "moth-kite")}
STATION = {"station": (lambda P: theln(P), "Drifting Rig", "station")}
BUILDINGS = {
    "tent_frame": (lambda P: grid_bg() + ribbon([(60, 140), (100, 80), (140, 140)], 3, P["hull_lo"]) + ribbon([(70, 140), (100, 90), (130, 140)], 1.5, P["hull"]) + dot_run(60, 140, 140, 140, 6, 1.2, P["glass"]), "Tent Frame", "hab"),
    "light_pavilion": (lambda P: grid_bg() + opoly([(50, 130), (100, 60), (150, 130), (100, 140)], P["hull"], d=1.4) + dot_run(40, 140, 160, 140, 8, 1.4, P["glass"]), "Light Pavilion", "gathering"),
}
FURNITURE = {
    "hammock_sling": (lambda P: grid_bg() + bar(60, 80, 60, 140, 2.4, "#9a9384") + bar(140, 80, 140, 140, 2.4, "#9a9384") + ribbon([(70, 110), (100, 120), (130, 110)], 2, "#5a5c54"), "Hammock Sling", "bed"),
    "light_curtain": (lambda P: grid_bg() + bar(80, 80, 120, 80, 1.6, "#7a7a70") + dot_run(80, 95, 120, 95, 6, 1.2, TEAL) + dot_run(80, 110, 120, 110, 6, 1.2, TEAL), "Light Curtain", "divider"),
}
OUTFITS = {"theln": (outfit_fn, "Drift Rigger", "crew")}
LAYOUTS = {
    "rig": (lambda P: grid_bg(320, 200) + circ(80, 80, 30, "#5a5c54") + circ(160, 130, 34, "#5a5c54") + circ(240, 80, 28, "#5a5c54") + dot_run(80, 110, 160, 120, 6, 1.4, TEAL) + dot_run(160, 164, 240, 120, 6, 1.4, TEAL) + label([(80, 45, "QUARTERS"), (160, 100, "RIGGING"), (240, 45, "SUPPLIES")], "#b8b0a0"), "Rig interior", "station floor plan"),
    "drift_camp": (lambda P: grid_bg(320, 200) + ribbon([(60, 70), (120, 60), (200, 80)], 3.2, "#6a6c60") + ribbon([(70, 140), (140, 150), (240, 130)], 2.8, "#5a5c54") + dot_run(60, 140, 240, 140, 10, 1.2, TEAL) + label([(100, 30, "ENCAMPMENT"), (180, 180, "DRIFT SITE")], "#b8b0a0"), "Drift camp", "moon settlement plan"),
}
