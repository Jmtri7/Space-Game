"""Extract the shared Person body + every outfit accessory from the Standard
Issue atlas (gen_si.figure_parts) into game/world/person_figure.py - the same
"atlas is the source of truth for the silhouette" pipeline ships and buildings
use (docs/atlases/apply_parts.py), but for the figure.

figure_parts is parametric (helmet vs bare head, each accessory on/off), so we
run it a few times and diff:
  BASE       - parts common to the helmeted and bare runs (torso, arms, hands,
               legs, boots), carrying the animation `group`
  BARE_HEAD  - the big bare face (drawn when the outfit has no helmet_color)
  HELMET_RING/HELMET_FACE - the helmet ring (behind) and the smaller face it
               frames (drawn when helmet_color is set)
  EYES_BARE / EYES_HELM - the eye pair for each head, skipped under a visor
  ACC[key]   - the parts one accessory colour-key adds, by diff against BASE

Everything is mapped to Person game units: centre-line at x, feet at y, y
negative going up (matching person.py's constants). Re-run after editing the
atlas figure; do not hand-edit person_figure.py.
"""
import sys, pathlib, json
from collections import Counter

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
import gen_si

S = 0.19
GROUND = 201.0            # figure-y the boots stand on -> Person self.y

def g(x, y):
    return round((x - 70.0) * S, 3), round((y - GROUND) * S, 3)

# The atlas arm hangs a hair outboard of the narrow torso; at in-game zoom
# that reads as a detached rectangle, so pull the arm/hand groups toward the
# centre-line until their inner edge clearly overlaps the torso.
ARM_INSET = 1.3   # game units, toward centre

def _inset(gx, gy, group):
    if group in ("arm_l", "hand_l"):
        gx += ARM_INSET
    elif group in ("arm_r", "hand_r"):
        gx -= ARM_INSET
    return round(gx, 3), round(gy, 3)

def to_parts(shapes, keep_group=True):
    out = []
    for sh in shapes:
        grp = sh["group"]
        if "points" in sh:
            geom = {"points": [list(_inset(*g(x, y), grp)) for x, y in sh["points"]]}
        else:
            cx, cy, r = sh["circle"]
            gx, gy = _inset(*g(cx, cy), grp)
            geom = {"circle": [gx, gy, round(r * S, 3)]}
        p = {**geom, "color": sh["color"]}
        if keep_group:
            p["group"] = grp
        out.append(p)
    return out

def ident(p):
    """Geometry+colour identity, ignoring group - for diffing runs."""
    return json.dumps(["p" if "points" in p else "c",
                       p.get("points") or p["circle"], p["color"]], sort_keys=True)

BODY = dict(suit="suit", boot="boot", leg="leg", sleeve="sleeve")
def run(**kw):
    return to_parts(gen_si.figure_shapes(**BODY, **kw))

bare      = run()                                          # big face + eyes
bare_ne   = run(eyes=False)                                # big face, no eyes
helm      = run(helmet="helmet_color", helmet_r=18)        # ring + small face + eyes
helm_ne   = run(helmet="helmet_color", helmet_r=18, eyes=False)

bare_ne_k = {ident(p) for p in bare_ne}
helm_ne_k = {ident(p) for p in helm_ne}

BASE       = [p for p in bare_ne if ident(p) in helm_ne_k]
BARE_HEAD  = [p for p in bare_ne if ident(p) not in helm_ne_k]      # big face (+outline)
HELMET     = [p for p in helm_ne if ident(p) not in bare_ne_k]      # ring + small face
# split the helmet run: circles at the head centre with the largest radius are
# the ring; the rest is the face it frames (drawn later, over the chest pieces).
_ring_r = max(p["circle"][2] for p in HELMET if "circle" in p)
HELMET_RING = [p for p in HELMET if "circle" in p and p["circle"][2] >= _ring_r - 2.0 * S]
HELMET_FACE = [p for p in HELMET if p not in HELMET_RING]

EYES_BARE = [p for p in bare if ident(p) not in {ident(q) for q in bare_ne}]
EYES_HELM = [p for p in helm if ident(p) not in {ident(q) for q in helm_ne}]

SPECS = {
    "backpack_color":    dict(backpack="backpack_color"),
    "spike_color":       dict(spikes="spike_color"),
    "antenna_color":     dict(antenna="antenna_color"),
    "chest_plate_color": dict(chest="chest_plate_color"),
    "sash_color":        dict(sash="sash_color"),
    "collar_color":      dict(collar="collar_color"),
    "belt_color":        dict(belt="belt_color", buckle="buckle"),
    "shoulder_color":    dict(shoulders="shoulder_color"),
    "badge_color":       dict(badge="badge_color"),
    "visor_color":       dict(visor="visor_color"),
}
ACC = {}
for k, kw in SPECS.items():
    variant = run(eyes=False, **kw)
    ACC[k] = [p for p in variant if ident(p) not in bare_ne_k]

# animation pivots + limb spans, Person game units, feet at (0, 0)
_arm_l_piv = list(_inset(*g(46, 76), "arm_l"))
_arm_r_piv = list(_inset(*g(94, 76), "arm_r"))
PIVOTS = {"leg_l": list(g(63.5, 150)), "leg_r": list(g(76.5, 150)),
          "arm_l": _arm_l_piv, "arm_r": _arm_r_piv}
LEG_HIP_Y, _   = g(0, 150)[1], None
LEG_ANKLE_Y    = g(0, 190)[1]
ARM_SHOULDER_Y = g(0, 76)[1]
ARM_WRIST_Y    = g(0, 121)[1]

def d(v):
    return json.dumps(v, separators=(",", ":"))

def block(name, parts):
    lines = [f"{name} = ["]
    for p in parts:
        lines.append(f"    {d(p)},")
    lines.append("]")
    return "\n".join(lines)

groups = ["S = %s" % S,
          "LEG_HIP_Y = %s" % g(0, 150)[1],
          "LEG_ANKLE_Y = %s" % LEG_ANKLE_Y,
          "ARM_SHOULDER_Y = %s" % ARM_SHOULDER_Y,
          "ARM_WRIST_Y = %s" % ARM_WRIST_Y,
          "PIVOTS = %s" % d(PIVOTS),
          block("BASE", BASE),
          block("BARE_HEAD", BARE_HEAD),
          block("HELMET_RING", HELMET_RING),
          block("HELMET_FACE", HELMET_FACE),
          block("EYES_BARE", EYES_BARE),
          block("EYES_HELM", EYES_HELM),
          "ACC = {"]
for k in SPECS:
    groups.append(f"    {json.dumps(k)}: [")
    for p in ACC[k]:
        groups.append(f"        {d(p)},")
    groups.append("    ],")
groups.append("}")

hdr = ('"""Generated by docs/atlases/build_person_figure.py from gen_si.figure_parts.\n'
       'The shared Person body + every outfit accessory, in Person game units\n'
       '(feet at the origin, y negative going up). Do not hand-edit; re-run the\n'
       'builder. See docs/DESIGN_ATLAS.md."""\n')
dest = pathlib.Path("game/world/person_figure.py")
dest.write_text(hdr + "\n" + "\n".join(groups) + "\n", encoding="utf-8")

print("wrote", dest)
for n, v in [("BASE", BASE), ("BARE_HEAD", BARE_HEAD), ("HELMET_RING", HELMET_RING),
             ("HELMET_FACE", HELMET_FACE), ("EYES_BARE", EYES_BARE), ("EYES_HELM", EYES_HELM)]:
    print(f"  {n:12} {len(v):2}  groups={dict(Counter(p.get('group') for p in v))}")
for k in SPECS:
    print(f"  ACC[{k}] = {len(ACC[k])}")
