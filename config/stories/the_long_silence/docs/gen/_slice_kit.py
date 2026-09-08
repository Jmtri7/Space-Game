"""Shared helpers for the Phase 6.2-6.6 slice generators (gen_kiln / gen_verdance
/ gen_ossuary / gen_span / gen_carriers). The per-system scripts own their
culture's geometry and content; this module only holds the pure plumbing they
all repeat - file IO, the free-drawn wardrobe-article builders (same approach as
gen_halcyon: no body fitting, they sit the same on either cut), and a
connected-floor-plan helper.

Run order and ownership live in docs/gen/README.md.
"""
import json

S = "config/stories/the_long_silence"
G = f"{S}/graphics"


def w(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def r(path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------- floor plans
def rect(x0, y0, x1, y1, label):
    return {"label": label, "polygon": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]}


def concourse_plan(spine_label, bays):
    """One connected walkable area: a west-east concourse spine (x 120..1480,
    y 560..740) plus bays that each overlap it by ~30u so the walkable union
    has no zero-width seams for the nav grid to miss. `bays` is a list of
    (x0, y0, x1, y1, label). Mirrors gen_halcyon's HUB_ROOMS.
    """
    rooms = [rect(120, 560, 1480, 740, spine_label)]
    for x0, y0, x1, y1, label in bays:
        rooms.append(rect(x0, y0, x1, y1, label))
    return rooms


# north bays clear the spine's top edge (560) by overlapping to 590;
# south bays clear its bottom edge (740) by starting at 710.
BAY_N = lambda x0, x1, label: (x0, 360, x1, 590, label)
BAY_S = lambda x0, x1, label: (x0, 710, x1, 980, label)


# ---------------------------------------------------------------- wardrobe
def down_chevron(cx, cy, half, drop, th):
    """A downward-pointing > chevron, apex toward the feet (larger y)."""
    return [[cx - half, cy], [cx, cy + drop], [cx + half, cy],
            [cx + half, cy - th], [cx, cy + drop - th], [cx - half, cy - th]]


def _geom(masc, femme, m_det, f_det):
    g = {"masc": {"points": masc, "fits": []}, "femme": {"points": femme, "fits": []}}
    if m_det is not None:
        g["masc"]["details"] = m_det
    if f_det is not None:
        g["femme"]["details"] = f_det
    return g


def region(group, tag, note, color, shade, masc, femme, m_det=None, f_det=None):
    """One free-drawn article region, both body cuts. `masc`/`femme` are the
    outline point lists (authored in body space - feet y=0, up is -y,
    centre-line x=0); `m_det`/`f_det` optional per-cut detail lists."""
    return {"group": group, "tag": tag, "note": note, "color": color,
            "shade": shade, "geometry": _geom(masc, femme, m_det, f_det)}


def article(identity, palette, regions):
    return {"identity": identity, "tier": "person", "palette": palette, "regions": regions}


# stock free-drawn shapes reused across cultures (recoloured per palette) ------
def sash_region(color, shade, tag="bandolier", note="sash"):
    """A wide band from the near shoulder down across the chest to the far
    hip - shoulder-of-office / militia / mourning, depending on colour."""
    return region("torso", tag, note, color, shade,
                  [[2.9, -25.5], [3.5, -25.1], [-2.7, -18.6], [-3.3, -19.2]],
                  [[1.6, -25.6], [2.1, -25.2], [-1.8, -19.5], [-1.95, -20.1]])


def shoulder_slab_region(color, shade, note="shoulder slab"):
    """Heavy squared pauldrons, one per shoulder (bigger, harder than epaulettes)."""
    return region("arm_near", "epaulette", "near " + note, color, shade,
                  [[1.7, -25.2], [4.9, -25.0], [4.9, -23.4], [1.8, -23.6]],
                  [[1.2, -25.0], [3.6, -24.85], [3.6, -23.3], [1.25, -23.45]])


def far_shoulder_slab_region(color, shade, note="shoulder slab"):
    return region("arm_far", "epaulette", "far " + note, color, shade,
                  [[-2.4, -25.1], [-4.8, -25.2], [-4.8, -23.5], [-2.45, -23.4]],
                  [[-1.65, -24.95], [-3.55, -25.05], [-3.55, -23.45], [-1.7, -23.35]])


def bib_region(color, shade, note="bib", tag="work vest"):
    """A squared chest bib hanging from the collar to mid-torso."""
    return region("torso", tag, note, color, shade,
                  [[-3.1, -25.0], [3.1, -25.0], [3.1, -20.2], [-3.1, -20.2]],
                  [[-2.7, -25.1], [2.7, -25.1], [2.5, -20.6], [-2.5, -20.6]])


def pendant_region(color, shade, note="pendant", tag="badge"):
    """A small tablet on a cord at the sternum."""
    return region("torso", tag, note, color, shade,
                  [[-0.7, -23.2], [0.7, -23.2], [0.7, -21.6], [-0.7, -21.6]],
                  [[-0.6, -23.6], [0.6, -23.6], [0.6, -22.1], [-0.6, -22.1]],
                  m_det=[{"group": "torso", "color": "metal", "shade": "metal", "note": note + " cord",
                          "points": [[-0.1, -25.3], [0.1, -25.3], [0.5, -23.2], [-0.5, -23.2]]}],
                  f_det=[{"group": "torso", "color": "metal", "shade": "metal", "note": note + " cord",
                          "points": [[-0.1, -25.5], [0.1, -25.5], [0.45, -23.6], [-0.45, -23.6]]}])


def hip_seal_region(color, shade, note="seal", tag="hip accessory"):
    """A disc worn at the near hip - a wax contract-seal, a name-token, a hub mark."""
    return region("torso", tag, note, color, shade,
                  [[1.6, -19.9], [2.9, -19.9], [2.9, -18.4], [1.6, -18.4]],
                  [[1.3, -20.4], [2.5, -20.4], [2.5, -19.0], [1.3, -19.0]])


def brassard_region(band_color, band_shade, mark_color, note="arm band"):
    """A wide upper-arm band with a lit mark (chevron by default)."""
    return region("arm_near", "armband", note, band_color, band_shade,
                  [[2.42, -24.3], [4.62, -24.18], [4.62, -21.5], [2.5, -21.62]],
                  [[1.6, -21.5], [3.42, -21.62], [3.3, -24.28], [1.62, -24.05]],
                  m_det=[{"group": "arm_near", "color": mark_color, "shade": "glow", "note": note + " mark",
                          "points": [[2.7, -23.3], [3.55, -22.6], [4.4, -23.3], [4.4, -22.85],
                                     [3.55, -22.15], [2.7, -22.85]]}],
                  f_det=[{"group": "arm_near", "color": mark_color, "shade": "glow", "note": note + " mark",
                          "points": [[1.85, -23.2], [2.55, -22.55], [3.25, -23.2], [3.25, -22.78],
                                     [2.55, -22.13], [1.85, -22.78]]}])


def gorget_region(ground_color, ground_shade, lamp_color, note="gorget"):
    """A stiff throat collar with a lit bar / disc - the culture's identity mark."""
    return region("torso", "collar", note, ground_color, ground_shade,
                  [[-2.0, -24.4], [2.0, -24.4], [2.2, -26.4], [-2.2, -26.4]],
                  [[-1.8, -24.5], [1.8, -24.5], [2.0, -26.2], [-2.0, -26.2]],
                  m_det=[{"group": "torso", "color": lamp_color, "shade": "glow", "note": note + " lamp",
                          "points": [[-1.4, -25.9], [1.4, -25.9], [1.4, -25.3], [-1.4, -25.3]]}],
                  f_det=[{"group": "torso", "color": lamp_color, "shade": "glow", "note": note + " lamp",
                          "points": [[-1.3, -25.75], [1.3, -25.75], [1.3, -25.2], [-1.3, -25.2]]}])


def hood_region(color, shade, note="hood"):
    """A raised hood over the head. Carries hides_hair upstream (set on the
    article dict by the caller)."""
    return region("head", "hood back", note, color, shade,
                  [[-3.0, -28.0], [3.0, -28.0], [3.4, -32.0], [1.6, -34.4],
                   [-1.6, -34.4], [-3.4, -32.0]],
                  [[-2.9, -28.2], [2.9, -28.2], [3.3, -32.1], [1.5, -34.4],
                   [-1.5, -34.4], [-3.3, -32.1]])


def apron_region(color, shade, note="apron", tag="skirt"):
    """A work apron from the waist to the knee."""
    return region("torso", tag, note, color, shade,
                  [[-2.6, -19.6], [2.6, -19.6], [3.0, -10.0], [-3.0, -10.0]],
                  [[-2.3, -20.2], [2.3, -20.2], [2.7, -10.4], [-2.7, -10.4]])


def stole_region(color, shade, note="stole", tag="long coat"):
    """Two long narrow panels hanging from the shoulders past the waist."""
    return region("torso", tag, note, color, shade,
                  [[-2.4, -25.4], [-1.2, -25.4], [-1.4, -13.0], [-2.8, -13.0]],
                  [[-2.1, -25.3], [-1.0, -25.3], [-1.2, -13.4], [-2.5, -13.4]],
                  m_det=[{"group": "torso", "color": color, "shade": shade, "note": note + " near panel",
                          "points": [[1.2, -25.4], [2.4, -25.4], [2.8, -13.0], [1.4, -13.0]]}],
                  f_det=[{"group": "torso", "color": color, "shade": shade, "note": note + " near panel",
                          "points": [[1.0, -25.3], [2.1, -25.3], [2.5, -13.4], [1.2, -13.4]]}])


def numeral_plate_region(color, shade, note="ration plate"):
    """A stencil-numeral plate on the chest - Combine ration marking."""
    return region("torso", "chest plate", note, color, shade,
                  [[-2.4, -24.2], [2.4, -24.2], [2.4, -21.0], [-2.4, -21.0]],
                  [[-2.1, -24.4], [2.1, -24.4], [2.1, -21.4], [-2.1, -21.4]],
                  m_det=[{"group": "torso", "color": "lamp", "shade": "glow", "note": note + " numerals",
                          "points": [[-1.8, -23.4], [-1.2, -23.4], [-1.2, -21.8], [-1.8, -21.8]]},
                         {"group": "torso", "color": "lamp", "shade": "glow", "note": note + " numerals 2",
                          "points": [[-0.3, -23.4], [0.3, -23.4], [0.3, -21.8], [-0.3, -21.8]]},
                         {"group": "torso", "color": "lamp", "shade": "glow", "note": note + " numerals 3",
                          "points": [[1.2, -23.4], [1.8, -23.4], [1.8, -21.8], [1.2, -21.8]]}],
                  f_det=[{"group": "torso", "color": "lamp", "shade": "glow", "note": note + " numerals",
                          "points": [[-1.6, -23.6], [-1.0, -23.6], [-1.0, -22.1], [-1.6, -22.1]]},
                         {"group": "torso", "color": "lamp", "shade": "glow", "note": note + " numerals 2",
                          "points": [[1.0, -23.6], [1.6, -23.6], [1.6, -22.1], [1.0, -22.1]]}])


# ---------------------------------------------------------------- wardrobe wiring
def write_wardrobe(gfx, pfx, dress_palette, articles, sets, role_set):
    """articles: {id: article-dict}; sets: {id: {identity, articles:[...]}};
    role_set: {outfit-role -> set-id}. Writes the article + set files and
    repoints the ten <pfx>_<role>_<cut> outfit entries at their set."""
    for aid, design in articles.items():
        w(f"{G}/articles/{aid}.json", design)
    for sid, design in sets.items():
        design.setdefault("palette", dress_palette)
        w(f"{G}/sets/{sid}.json", design)
    for role, sid in role_set.items():
        for cut in ("femme", "masc"):
            gfx["outfits"][f"{pfx}_{role}_{cut}"] = {
                "body": f"human_{cut}", "set": sid, "palette": dress_palette}


def say(sender, text):
    return {"sender": sender, "text": text}


# ---------------------------------------------------------------- station shell
# Per-culture floor tessellation - the pattern each culture would lay a deck in.
_STATION_STYLE = {
    "authority": ("square", 64, 2.0),   # ranked deck panels
    "combine": ("square", 92, 3.0),     # big riveted plates
    "drift": ("hex", 56, 2.0),          # woven / organic
    "vigil": ("triangle", 80, 2.0),     # austere, angular
    "warden": ("hex", 76, 2.5),         # monumental
    "carrier": ("rhombus", 54, 2.0),    # patchwork diamonds
}


def station_shell(pfx, star_seed):
    """Interior keys shared by every finished station concourse: no room
    borders or labels (`seamless`), the Space View starfield behind it
    (`space_backdrop`), and a culture-tiled floor (`floor_pattern`)."""
    pattern, tile, gap = _STATION_STYLE.get(pfx, ("hex", 64, 2.0))
    return {"seamless": True, "space_backdrop": True, "star_seed": star_seed,
            "floor_pattern": {"pattern": pattern, "tile": tile, "gap": gap}}
