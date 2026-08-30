"""Generate the per-culture split atlases: Sol Federation, Vherathi Concord,
Drossholt Company.

Ships / station / buildings / furniture / decorations / layouts are pulled
verbatim from the current shipped atlases (standard-issue.html /
resin-and-rivets.html) via atlas_plates.grab - they're already detailed and
extracted-to-parts, no reason to redraw them. The OUTFITS are new: redrawn on
the cinched-waist body with each culture's signature (federation_outfits /
vherathi_outfits / drossholt_outfits).

    python docs/atlases/gen_split.py            # all three
    python docs/atlases/gen_split.py vherathi   # just one
"""
import importlib
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import figure_parts, poly, GRID
from atlas_shell import css, DEFS, GRIDDEF
from atlas_plates import grab


def rgb(t):
    return f"#{t[0]:02x}{t[1]:02x}{t[2]:02x}"


CULTURES = {
 "federation": dict(
   file="sol-federation.html", title="Sol Federation", mark="Sol <em>Federation</em>",
   accent="#8fb9c8", accent_rgb="143,185,200",
   src="standard-issue.html", outfits="federation_outfits",
   pal=dict(hull="#41506a", hull_lo="#2a3444", glass="#cfe0f0", thrust="#8cb9ff",
            trim="#f2b23a", shadow="#1c2430"),
   tagline="Not grown, not scavenged &mdash; <em>issued</em>",
   dek="The civil authority that runs the neutral stations and licenses the ships. "
       "Where the Vherathi grow their hardware and the Drossholt bolt theirs, the "
       "Federation <b>issues</b> it &mdash; factory-painted, colour-coded, built "
       "from interchangeable modules to one spec and stencilled with a "
       "registration number.",
   rubric=[
     ("Prefab modules.", "A hull is a spine of identical bays; a station is identical rings on a spine; a building is identical floors stacked. Interchangeable, replaceable, numbered."),
     ("One corner radius.", "Rounded rectangles everywhere &mdash; a consistent small fillet, not the Vherathi organic curve or the Drossholt raw right angle."),
     ("Painted livery.", "Body colour + a white contrast stripe along the centreline + amber hazard chevrons at every thruster, hatch and edge; a stencilled <code class=\"f\">SF-###</code> on the hull."),
     ("Clean symmetry.", "Mirrored, flush, evenly spaced &mdash; no visible patch plates, windows in a regular grid."),
   ],
   ships=["Issue Shuttle", "Issue Lighter", "Issue Cutter", "Issue Tender"],
   station=["Standard Ring station"],
   buildings=["Issue Block", "Issue Shed", "Issue Bollard", "Issue Bench", "Issue Service Counter"],
   deco=["floor decal of alternating amber and dark hazard chevrons"],
   layouts=["Standard Issue station interior"],
   status="<b>The <code class=\"f\">standard_issue</code> culture shipped</b> "
          "(<code class=\"f\">config/stories/default</code>, story <code class=\"f\">1.10.0</code>) "
          "&mdash; Procyon Ring station, Garrison Row moon, every ship / station / "
          "building silhouette extracted into <code class=\"f\">parts</code>. The "
          "hardware plates below are those shipped SVGs. The <b>crew outfit "
          "redraws are a MOCKUP</b> &mdash; the Federation signature (visor slit, "
          "centreline stripe, SF-### stencil) is new figure geometry.",
 ),
 "vherathi": dict(
   file="vherathi-concord.html", title="Vherathi Concord", mark="Vherathi <em>Concord</em>",
   accent="#78ffc8", accent_rgb="120,255,200",
   src="resin-and-rivets.html", outfits="vherathi_outfits",
   pal=dict(hull="#483060", hull_lo="#2f1e3c", glass="#78ffc8", thrust="#dc5aff",
            trim="#96789e", shadow="#241830"),
   tagline="Ships and cities <em>grown</em>, not assembled",
   dek="A spacefaring people whose ships and cities are grown from living "
       "resin-crystal rather than assembled from plate metal. The Vherathi shape "
       "architecture the way coral shapes a reef: <b>asymmetric</b>, load-bearing "
       "ridges tapering toward one dominant point, with structural stress traced "
       "by thin veins of bioluminescent glass instead of punched-out windows.",
   rubric=[
     ("Grown, not machined.", "Tapering asymmetric silhouettes &mdash; one side always subtly longer or sharper than the other, echoing a grown crystal, never a mirror-symmetric machined part."),
     ("Veins, not windows.", "No uniform window grid; a handful of lit apertures clustered off-centre along the tallest ridge, tracing a vein of light through the material (<code class=\"f\">glass_color</code>)."),
     ("Odd counts.", "Thrusters and fittings mounted in odd counts or uneven spacing where possible, not perfectly mirrored pairs."),
     ("One grown structure.", "Interiors are rounded and flowing &mdash; many-sided circle rooms and wide organic corridors joined by overlap; each room's rim traced with a thread of bioluminescent glass."),
   ],
   ships=["Resin Skiff", "Reliquary Hauler", "Thornwing Corvette", "Spinewing Skiff",
          "Chorus Tender", "Pale Ark"],
   station=["redesigned Vherathi station"],
   buildings=["Concord Spire", "Vherathi Bloompod", "Vherathi Gathering Hall", "Dock Antler"],
   deco=["Vherathi Light Column", "Vherathi Fern Basin", "Vherathi Lounge Pod",
         "Vherathi Concierge Desk", "Vherathi Resin Bench", "Vein Arch"],
   layouts=["floor plan of a Vherathi station", "plan of a Vherathi moon city",
            "curved Vherathi room corner", "Vherathi concourse circle with furniture"],
   status="<b>The <code class=\"f\">vherathi</code> culture shipped</b> "
          "(story <code class=\"f\">1.10.0</code>) &mdash; Alpha Station and its "
          "moon rebuilt to the grown floor-plan model, every hull / building / "
          "furniture silhouette extracted into <code class=\"f\">parts</code>. The "
          "hardware plates below are those shipped SVGs. The <b>outfit redraws "
          "are a MOCKUP</b> &mdash; the eye-bubble helm clusters and resin-vein "
          "tracery are new figure geometry.",
 ),
 "drossholt": dict(
   file="drossholt-company.html", title="Drossholt Company", mark="Drossholt <em>Company</em>",
   accent="#ffc850", accent_rgb="255,200,80",
   src="resin-and-rivets.html", outfits="drossholt_outfits",
   pal=dict(hull="#c89664", hull_lo="#5a4130", glass="#ffc850", thrust="#ff8c3c",
            trim="#5a4130", shadow="#2c2018"),
   tagline="Bolted together from <em>whatever</em> a supply run can carry",
   dek="A frontier trading and salvage outfit running the outposts at the edge of "
       "known space. Where the Vherathi grow their architecture, Drossholt "
       "<b>bolts</b> it together out of whatever plate and scavenged hull "
       "segments a supply run can carry &mdash; blunt, riveted, and built to be "
       "patched rather than beautiful.",
   rubric=[
     ("Blunt volumes.", "Rectangular masses bolted together along visible seams &mdash; no tapering or asymmetry for its own sake, the functional opposite of a grown structure."),
     ("Rows on the seams.", "Windows and warning lights run in even, evenly-spaced rows along structural seams; thrusters and fixtures come in mirrored evenly-spaced pairs."),
     ("Rivets and patches.", "Every edge studded with bolt ticks; a repair is a mismatched plate welded on, not hidden. Weathered, practical, patched."),
     ("Right angles inside.", "Interiors are plain rectangles and wide straight corridors joined at right angles; every room edge studded with evenly-spaced bolt ticks."),
   ],
   ships=["Drossholt Hauler", "Drossholt Cutter", "Sledge Tug", "Ratchet Prospector",
          "Bulwark Gunship"],
   station=["redesigned Drossholt station"],
   buildings=["Drossholt Watch Tower", "Drossholt Bunker", "Drossholt Warehouse", "Gantry Rig"],
   deco=["Drossholt Work Light", "Drossholt Cargo Stack", "Drossholt Drum",
         "Drossholt Scrub Tub", "Drossholt Plate Bench", "Drossholt Trade Counter", "Pipe Rail"],
   layouts=["floor plan of a Drossholt outpost", "plan of a Drossholt moon city"],
   status="<b>The <code class=\"f\">drossholt</code> culture shipped</b> "
          "(story <code class=\"f\">1.10.0</code>) &mdash; the outpost and its moon "
          "rebuilt to the bolted floor-plan model, every hull / building / "
          "furniture silhouette extracted into <code class=\"f\">parts</code>. The "
          "hardware plates below are those shipped SVGs. The <b>outfit redraws "
          "are a MOCKUP</b> &mdash; the riveted patch-plates and box respirator "
          "are new figure geometry.",
 ),
}

SW = [("hull / wall", "hull"), ("hull shadow", "hull_lo"), ("glass / lights", "glass"),
      ("thrust", "thrust"), ("trim", "trim")]


def plate(svg, label, vlabel, badge="Shipped"):
    return (f'<article class="plate"><div class="viewport diagram">{svg}'
            f'<span class="vlabel">{vlabel}</span><span class="isnew">{badge}</span></div>'
            f'<div class="plate-body">{label}</div></article>')


def plate_grid(items):
    return ('<div class="grid-outfits">'
            + "".join(f'<figure class="card"><svg viewBox="0 0 240 200" role="img" '
                      f'aria-label="{cap}">{GRIDDEF}{inner}</svg>'
                      f'<figcaption><b>{cap}</b></figcaption></figure>'
                      for cap, inner in items) + '</div>')


def strip_svg(svg):
    """viewBox + inner of an extracted <svg>, for re-wrapping in a card."""
    import re
    vb = re.search(r'viewBox="([^"]*)"', svg).group(1)
    inner = re.sub(r'^<svg[^>]*>', '', svg)
    inner = re.sub(r'</svg>\s*$', '', inner)
    return vb, inner


def card_from_plate(src, label):
    svg = grab(src, label)
    vb, inner = strip_svg(svg)
    return (f'<figure class="card"><svg viewBox="{vb}" role="img" aria-label="{label}">'
            f'{inner}</svg><figcaption><b>{label}</b></figcaption></figure>')


def outfit_card(mod, key):
    fn, name, role = mod.OUTFITS[key]
    base, pre, post = fn()
    inner = (poly([(0, 0), (140, 0), (140, 210), (0, 210)], GRID)
             + pre + "".join(figure_parts(**base)) + post)
    return (f'<figure class="card"><svg viewBox="0 0 140 210" role="img" '
            f'aria-label="Front view of the {name} on the shared body.">{GRIDDEF}{inner}</svg>'
            f'<figcaption><b>{name}</b><p class="role">{role}</p></figcaption></figure>')


def build(key):
    c = CULTURES[key]
    src = c["src"]
    mod = importlib.import_module(c["outfits"])
    pal = c["pal"]

    def section(sid, title, cards_html):
        return (f'<section class="chapter" id="{sid}"><p class="chapter-kicker">{title}</p>'
                f'<h2>{title}</h2>{cards_html}</section>')

    ships = "".join(card_from_plate(src, s) for s in c["ships"])
    stations = "".join(card_from_plate(src, s) for s in c["station"])
    buildings = "".join(card_from_plate(src, b) for b in c["buildings"])
    deco = "".join(card_from_plate(src, d) for d in c["deco"])
    layouts = "".join(card_from_plate(src, l) for l in c["layouts"])
    outfits = "".join(outfit_card(mod, k) for k in mod.OUTFITS)

    swatches = "".join(f'<div class="sw"><i style="background:{pal[k]}"></i>'
                       f'<span><b>{lbl}</b>{pal[k].upper()}</span></div>' for lbl, k in SW)
    directives = "".join(f"<li><b>{t}</b> {d}</li>" for t, d in c["rubric"])

    nav = "".join(f'<a href="#{i}">{n}</a>' for i, n in
                  [("ships", "Ships"), ("station", "Station"), ("buildings", "Buildings"),
                   ("furniture", "Furniture"), ("outfits", "Outfits"), ("layouts", "Layouts"),
                   ("wiring", "Wiring in")])

    return f"""<meta charset="utf-8">
<title>{c['title']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap">
{css(c['accent'], c['accent_rgb'])}
{DEFS}
<header class="topbar"><div class="wrap">
  <span class="mark">{c['mark']}</span>
  <nav class="navlinks">{nav}</nav>
  <span class="tag-wip">Hardware shipped &middot; outfit redraws mockup</span>
</div></header>

<main class="wrap">
  <section class="hero">
    <p class="eyebrow">Default story &mdash; culture design atlas</p>
    <h1>{c['tagline']}</h1>
    <p class="dek">{c['dek']}</p>
    <div class="status">{c['status']}</div>
    <dl class="legend" id="read">
      <div><dt>Hardware &mdash; shipped</dt><dd>Ship / station / building / furniture / layout plates are the current in-game SVGs, silhouettes extracted into <code class="f">parts</code>.</dd></div>
      <div><dt>Outfits &mdash; mockup</dt><dd>Redrawn on the cinched-waist body with this culture's <b>signature</b> geometry. The recolour is buildable now; the signature waits on a <code class="f">figure_signature</code> table.</dd></div>
      <div><dt>Shapes only</dt><dd>Every specimen is <code class="f">&lt;polygon&gt;</code> + <code class="f">&lt;circle&gt;</code>, no stroke.</dd></div>
      <div><dt>Identity spread</dt><dd>The <code class="f">cultures.json</code> palette + a numbered rubric of silhouette directives from the <code class="f">theme</code> string.</dd></div>
    </dl>

    <div class="identity" style="margin-top:40px">
      <div><div class="swatches">{swatches}</div>
        <p style="margin:14px 0 0;font-size:.8rem;color:var(--ink-3);font-family:'IBM Plex Mono',monospace">cultures.json &rarr; <code class="f">{key if key != 'federation' else 'standard_issue'}</code></p></div>
      <ol class="directives">{directives}</ol>
    </div>
  </section>

  {section("ships", "Ships", plate_grid_from(ships))}
  {section("station", "Station", plate_grid_from(stations))}
  {section("buildings", "Buildings", plate_grid_from(buildings))}
  {section("furniture", "Furniture &amp; decorations", plate_grid_from(deco))}
  {section("outfits", "Outfits", '<p class="lead">Every role redrawn on the current body, each carrying the culture signature &mdash; ' + c['rubric'][0][0].lower().rstrip('.') + ', ' + c['rubric'][1][0].lower().rstrip('.') + '. <span class="mk">MOCKUP</span></p><div class="grid-outfits">' + outfits + '</div>')}
  {section("layouts", "Station &amp; city layouts", plate_grid_from(layouts))}

  <section class="wiring" id="wiring">
    <h2>Wiring in</h2>
    <div class="wiring-grid">
      <section><h4>Hardware &mdash; shipped</h4><p>Ships (<code class="f">graphics.json</code>), station (<code class="f">graphics.json</code> &rarr; <code class="f">space_stations</code>), buildings (<code class="f">building_types.json</code>), furniture, decorations and both layouts are in <code class="f">config/stories/default</code>, silhouettes extracted from these plates into <code class="f">parts</code> by <code class="f">apply_parts.py</code>.</p></section>
      <section><h4>Outfits &mdash; the redraw</h4><p>Each outfit's recoloured base is a <code class="f">graphics.json</code> &rarr; <code class="f">outfits</code> entry (buildable now). The <b>signature geometry</b> is new &mdash; it needs a <code class="f">figure_signature</code> table keyed by outfit id, fed the way <code class="f">gen_si.figure_parts</code> already produces data. That one addition lands every culture's redraws at once.</p></section>
      <section><h4>The body</h4><p>The cinched waist / rounded shoulders / belts-at-the-waist are shipped in <code class="f">person_figure.py</code>. See the <b>Common Kit</b> atlas.</p></section>
      <section><h4>Retires</h4><p>This atlas + <b>Common Kit</b> (+ the other culture atlases) replace <code class="f">{src}</code> once all are built. Same visual system, same strokeless rule, same body.</p></section>
    </div>
  </section>
</main>
<footer><div class="wrap">{c['title']} &middot; hardware shipped, outfit redraws mockup &middot; default story</div></footer>
"""


def plate_grid_from(cards_html):
    return f'<div class="grid-outfits">{cards_html}</div>'


if __name__ == "__main__":
    keys = sys.argv[1:] or list(CULTURES)
    for k in keys:
        html = build(k)
        for bad in ('feGaussianBlur', 'backdrop-filter', 'IntersectionObserver', '@keyframes'):
            assert bad not in html, f"{k}: forbidden {bad}"
        out = pathlib.Path("docs/atlases") / CULTURES[k]["file"]
        out.write_text(html, encoding="utf-8")
        print("wrote", out, len(html), "bytes;", html.count("<svg"), "svgs")
