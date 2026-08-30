"""Generate docs/atlases/past-the-reach.html from scratch.

Companion to Resin & Rivets / Standard Issue: mockups for the FOUR proposed
frontier cultures (Deeprock, Kessari, Meridian, Theln) that don't exist in
config yet - one ship and one outfit each, eight specimens total. Same visual
system, same strokeless rule (only <polygon> + <circle>, no stroke), same
shared Person body via gen_si.figure_parts.

Run from the repo root:  python docs/atlases/gen_frontier.py
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import (poly, circ, ngon, rrect, offset_poly, opoly, ocirc, bar,
                    figure_parts, GRID, OUT)

VB_SHIP = "0 0 240 200"
CX, CY = 120.0, 100.0


# ------------------------------------------------------------------ helpers
def grid_bg(w=240.0, h=200.0):
    return poly([(0, 0), (w, 0), (w, h), (0, h)], GRID)


def seg_dots(x0, y0, x1, y1, n, r, col):
    """n small circles evenly spaced along a segment - running lights, rivets."""
    return "".join(circ(x0 + (x1 - x0) * i / (n - 1),
                        y0 + (y1 - y0) * i / (n - 1), r, col)
                   for i in range(n))


def scallop(cx, cy, rx, ry, n, r, col, a0=0.0):
    """A ring of n bump-circles on the rim of an ellipse - a scalloped edge."""
    return "".join(circ(cx + rx * math.cos(a0 + 2 * math.pi * k / n),
                        cy + ry * math.sin(a0 + 2 * math.pi * k / n), r, col)
                   for k in range(n))


def arc_dots(cx, cy, rx, ry, n, r, col, a_from=math.pi, a_to=2 * math.pi):
    """n circles along an elliptical arc - an arched window row."""
    return "".join(circ(cx + rx * math.cos(a_from + (a_to - a_from) * i / (n - 1)),
                        cy + ry * math.sin(a_from + (a_to - a_from) * i / (n - 1)), r, col)
                   for i in range(n))


def svg(inner, vb, aria, vlabel):
    return (f'<div class="viewport diagram"><svg viewBox="{vb}" role="img" '
            f'aria-label="{aria}">{inner}</svg>'
            f'<span class="vlabel">{vlabel}</span><span class="isnew">New</span></div>')


# ------------------------------------------------------------------ palettes
CULTURES = {
 "deeprock": {
   "name": "Deeprock Mining Consortium",
   "hull": "#5c524a", "hull_lo": "#413a34", "glass": "#ffe078",
   "thrust": "#ff9646", "trim": "#d6b03c", "shadow": "#332f2b",
 },
 "kessari": {
   "name": "The Ashfall Rite",
   "hull": "#22201e", "hull_lo": "#17161a", "glass": "#ff823c",
   "thrust": "#dc4628", "trim": "#c8602c", "shadow": "#141216",
 },
 "meridian": {
   "name": "The Meridian Free Ports",
   "hull": "#96744a", "hull_lo": "#6a5030", "glass": "#ffeec8",
   "thrust": "#ffd282", "trim": "#e8ce96", "shadow": "#3a2c1c",
 },
 "theln": {
   "name": "The Theln Drift",
   "hull": "#c8c0b0", "hull_lo": "#9a9384", "glass": "#7fe8e8",
   "thrust": "#6fd0d0", "trim": "#bfe6df", "shadow": "#2a3230",
 },
}


# ------------------------------------------------------------------ ships
def ship_deeprock():
    c = CULTURES["deeprock"]
    H, L, G, T, Y, S = c["hull"], c["hull_lo"], c["glass"], c["thrust"], c["trim"], c["shadow"]
    out = [grid_bg()]
    # exhaust flames (before the housings so the ports occlude their roots)
    for hx in (100, 140):
        out.append(poly([(hx - 3, 176), (hx, 196), (hx + 3, 176)], T, cls="flame"))
    # fat tank body
    out.append(opoly(ngon(120, 120, 42, 48, 20), H, d=1.6))
    # forward intake maw - wide, flat, front-heavy, asymmetric to port
    out.append(opoly([(74, 44), (170, 44), (156, 82), (86, 82)], H, d=1.6))
    out.append(poly([(90, 48), (152, 48), (142, 72), (100, 72)], S))         # mouth
    # offset cabin box clamped to one side near the front
    out.append(opoly(rrect(60, 64, 26, 30, 4), L, d=1.4))
    # two mirrored riveted thruster housings, aft
    for hx in (100, 140):
        out.append(opoly(rrect(hx - 11, 150, 22, 28, 3), L, d=1.4))
        for rx in (hx - 6, hx + 6):
            for ry in (156, 166, 174):
                out.append(circ(rx, ry, 1.3, S))
    # floodlights clustered around the working end
    for fx, fy in ((92, 50), (120, 46), (148, 50), (120, 66)):
        out.append(circ(fx, fy, 3.2, G))
    # hazard striping on the maw lip and housing tops
    out.append(bar(74, 45, 170, 45, 1.6, Y))
    for hx in (100, 140):
        out.append(bar(hx - 11, 151, hx + 11, 151, 1.4, Y))
    return "".join(out)


def ship_kessari():
    c = CULTURES["kessari"]
    H, L, G, T, S = c["hull"], c["hull_lo"], c["glass"], c["thrust"], c["shadow"]
    out = [grid_bg()]
    out.append(poly([(114, 168), (126, 168), (124, 182), (116, 182)], T, cls="flame"))
    # one dark slab: narrow blunt nose, heavier toward the base, one edge
    # left deliberately irregular (hand-shaped, not machined)
    slab = [(104, 34), (137, 34), (145, 96), (150, 150), (150, 166),
            (90, 166), (90, 150), (93, 96)]
    out.append(opoly(slab, H, d=1.7, ol=S))
    # the single defining feature: a bright ember seam down the spine
    out.append(bar(120, 38, 120, 162, 2.4, G))
    out.append(bar(120, 38, 120, 162, 0.9, "#ffd9a0"))
    # two tiny apertures near the top, off the spine
    out.append(circ(111, 52, 2.4, G))
    out.append(circ(129, 52, 2.4, G))
    # base thruster port, ember glow
    out.append(opoly([(110, 158), (130, 158), (127, 176), (113, 176)], L, d=1.3, ol=S))
    out.append(circ(120, 164, 3.0, T))
    return "".join(out)


def ship_meridian():
    c = CULTURES["meridian"]
    H, L, G, T, Y, S = c["hull"], c["hull_lo"], c["glass"], c["thrust"], c["trim"], c["shadow"]
    out = [grid_bg()]
    for hx in (104, 136):
        out.append(poly([(hx - 3, 168), (hx, 192), (hx + 3, 168)], T, cls="flame"))
    # two mirrored fluted thruster housings, aft
    for hx in (104, 136):
        out.append(opoly(rrect(hx - 10, 150, 20, 22, 3), L, d=1.3))
        for fx in (hx - 5, hx, hx + 5):
            out.append(bar(fx, 152, fx, 170, 0.9, S))
    # three stacked rounded tiers, largest aft, symmetric and centred -
    # wider than deep so each reads as a plate, not a ball
    tiers = [(140, 30, 46), (108, 24, 37), (78, 19, 27)]
    for ty, ry, rx in tiers:
        out.append(opoly(ngon(120, ty, rx, ry, 24), H, d=1.5))
    # a fluted brass rim + an arched window row per tier
    for ty, ry, rx in tiers:
        out.append(scallop(120, ty, rx, ry, max(12, int(rx / 1.8)), 1.3, Y))
        out.append(arc_dots(120, ty, rx * 0.68, ry * 0.72, 6, 1.9, G,
                            a_from=math.pi * 1.15, a_to=math.pi * 1.85))
    # a lantern finial at the nose
    out.append(opoly([(114, 60), (126, 60), (123, 46), (120, 40), (117, 46)], H, d=1.3))
    out.append(ocirc(120, 50, 4.0, G, d=1.3))
    return "".join(out)


def ship_theln():
    c = CULTURES["theln"]
    F, L, G, T, M = c["hull"], c["hull_lo"], c["glass"], c["thrust"], c["trim"]
    out = [grid_bg()]
    out.append(poly([(118, 158), (120, 178), (122, 158)], T, cls="flame"))
    # translucent membrane sails on a light asymmetric frame - one boom longer
    out.append(poly([(120, 58), (52, 108), (120, 150)], M, op=0.30))
    out.append(poly([(120, 58), (186, 92), (120, 150)], M, op=0.20))
    out.append(poly([(120, 150), (74, 176), (120, 130)], M, op=0.24))
    # frame: a thin spine + strut spars
    out.append(bar(120, 42, 120, 160, 2.6, F))
    for x1, y1 in ((52, 108), (186, 92), (74, 176), (168, 166)):
        out.append(bar(120, 58 if y1 < 130 else 150, x1, y1, 1.4, F))
    # running lights strung along the boom edges
    out.append(seg_dots(120, 58, 52, 108, 6, 1.3, G))
    out.append(seg_dots(120, 58, 186, 92, 5, 1.3, G))
    out.append(seg_dots(120, 150, 74, 176, 5, 1.3, G))
    # cockpit blister at the nose
    out.append(ocirc(120, 52, 5.0, L, d=1.2))
    out.append(circ(120, 52, 2.6, G))
    return "".join(out)


SHIPS = {
 "deeprock": (ship_deeprock, "Deeprock Gnaw",
   "Top-down Deeprock ore-hauler: a wide flat intake maw at the nose, a fat "
   "cylindrical tank body, an offset cabin box, two mirrored riveted thruster "
   "housings, floodlights clustered at the working end, hazard striping."),
 "kessari": (ship_kessari, "Kessari Cairn",
   "Top-down Kessari ship: a single dark blunt slab, heavier toward the base, "
   "one edge left irregular, a bright ember seam running the length of the "
   "spine, two tiny apertures near the nose, one thruster at the base."),
 "meridian": (ship_meridian, "Meridian Argosy",
   "Top-down Meridian trader: three stacked rounded tiers decreasing toward "
   "the nose, each with a scalloped brass rim and an arched row of warm "
   "windows, a lantern finial, two mirrored fluted thrusters aft."),
 "theln": (ship_theln, "Theln Kite",
   "Top-down Theln skiff: a thin central spine with translucent teal membrane "
   "sails spread asymmetrically over a light bone frame, running lights strung "
   "along the booms, a cockpit blister at the nose."),
}


# ------------------------------------------------------------------ outfits
OUTFITS = {
 "deeprock": dict(
   hat="#c9b083", suit="#8a7a68", boot="#3a342e", sleeve="#7a6a58",
   chest="#5c524a", rivets="#3a342e", backpack="#5c524a", torch="#5c524a",
   belt="#3a342e", buckle="#d6b03c", band="#d6b03c"),
 "kessari": dict(
   coat=True, torso_long=True, cap="#1e1c22", suit="#2a2730", boot="#1e1c22",
   leg="#242229", sleeve="#2a2730", collar="#3a3540", sash="#ff823c"),
 "meridian": dict(
   coat=True, cap="#4a3826", suit="#96744a", boot="#4a3826", sleeve="#8a6a44",
   collar="#e8ce96", sash="#e8ce96", shoulders="#7a5c38", badge="#ffeec8",
   belt="#4a3826", buckle="#e8ce96"),
 "theln": dict(
   helmet="#d8d2c4", visor="#7fe8e8", suit="#c8c0b0", boot="#8a857a",
   sleeve="#bfb8a8", harness="#9a9384", harness_side="left", pod="#a8a294",
   band="#7fe8e8", accent_dot=True, accent="#7fe8e8"),
}


def outfit_svg(opts):
    body = "".join(figure_parts(**opts))
    vw, vh = 160.0, 200.0
    bg = poly([(0, 0), (vw, 0), (vw, vh), (0, vh)], GRID)
    g = (f'<g transform="translate({vw / 2 - 70 * 0.92:.1f},'
         f'{vh - 205 * 0.92:.1f}) scale(0.92)">{body}</g>')
    return bg + g


OUTFIT_META = {
 "deeprock": ("Pit Foreman rig", "mining_foreman · belt crews",
   "A hard hat, a hi-vis band across a scuffed work suit, a bolted chest plate, "
   "an air-and-tool pack, a hip lamp. Everything that matters is painted "
   "trim-yellow; nothing else is painted at all.",
   ("hat", "suit", "boot", "sleeve", "chest", "rivets", "backpack", "torch", "belt", "band")),
 "kessari": ("Ashfall Adept habit", "kessari crew · pilgrims",
   "A long dark hooded habit, near-black, ascetic. One ember sash is the only "
   "colour on the whole figure - the same seam the ships carry, worn.",
   ("cap", "coat", "torso_long", "suit", "leg", "boot", "sleeve", "collar", "sash")),
 "meridian": ("Free-Port Factor coat", "meridian captains · factors",
   "A brass merchant's coat with a gold collar and sash, epaulettes, a badge of "
   "office, a buckled belt, a folded cap. A Meridian captain dresses to be seen "
   "stepping off the ramp.",
   ("cap", "coat", "suit", "boot", "sleeve", "collar", "sash", "shoulders", "badge", "belt", "buckle")),
 "theln": ("Drift Rigger kit", "theln crew · riggers",
   "Light layered bone-cloth over a half-harness worn on one side only, a teal "
   "running-light band, a visor, a single hip pod. Built to move around a "
   "membrane hull, not to impress anyone.",
   ("helmet", "visor", "suit", "boot", "sleeve", "harness", "harness_side", "pod", "band", "accent_dot")),
}


# ------------------------------------------------------------------ rubrics
RUBRICS = {
 "deeprock": [
   ("Built around the job.", "One dominant forward volume - an intake maw or ore scoop - a fat tank body behind it, and small ancillary boxes (cabin, mast) clamped on wherever they cleared the load. Front-heavy and asymmetric, not tidy."),
   ("Almost no windows.", "Light is a few harsh floodlights clustered at the working end, drawn from <code class=\"f\">glass_color</code>. The crew works by them, not by a view."),
   ("Hazard, not livery.", "Trim-yellow striping (<code class=\"f\">wall_trim_color</code>) edges every intake, hatch and thruster. It's a warning, not a paint job - everything else stays bare <code class=\"f\">metal_color</code>."),
   ("Heavy industrial plant.", "Blunt rectangular housings, visible rivets, mirrored thruster pairs at the back. It reads as machinery that happens to fly."),
 ],
 "kessari": [
   ("One solid mass.", "A tall blunt slab, wider and heavier toward the base like a standing stone. Roughly bilaterally symmetric but never mechanically precise - one edge is always slightly hand-irregular."),
   ("The ember seam.", "The single defining feature: a thin bright line of <code class=\"f\">glass_color</code> tracing the hull's central spine end to end, plus a matching glow at each thruster. Everything else is near-black <code class=\"f\">metal_color</code>."),
   ("Almost sealed.", "No panel lines, no patch plates, no rows of windows - at most one or two tiny apertures near the top."),
   ("Cell, not cabin.", "Interiors are narrow, dim, high-contrast: black floor and walls, one bright line of light down the centre of every room, rooms kept small and rectangular."),
 ],
 "meridian": [
   ("Stacked tiers.", "Two or three rounded volumes of decreasing size, each with a scalloped or fluted rim, symmetric and centred - not the Vherathi organic asymmetry."),
   ("Ornament is the point.", "Repeated edge detailing, brass trim (<code class=\"f\">wall_trim_color</code>) framing every opening, a lantern finial at the nose."),
   ("Windows on show.", "Plentiful, in even arched rows along each tier - a Meridian captain wants to be seen arriving."),
   ("Warm and bright inside.", "Wide oval or many-sided rooms joined by broad archways, gold trim on every edge - the opposite of a Kessari cell."),
 ],
 "theln": [
   ("Membrane on frame.", "Tensioned translucent sail (low-opacity <code class=\"f\">wall_trim_color</code>) over a light exoskeleton of thin <code class=\"f\">metal_color</code> struts. Kite-like, never a solid hull."),
   ("Asymmetric spars.", "Booms and struts of uneven length - one side always reaches further than the other."),
   ("Lights on cables.", "Running lights (<code class=\"f\">glass_color</code>) strung in lines along the boom edges, like fairy lights on rigging."),
   ("Tent, not room.", "Interiors are soft and low-walled, hanging lights, fabric dividers - a camp that packs down, not a built space."),
 ],
}


# ------------------------------------------------------------------ page
CSS = """
:root{
  --void:#0a0a0e;--panel:#131319;--ink:#ece9f4;--ink-2:#a5a2b6;--ink-3:#6d6a7e;
  --line:#292935;--line-2:#35333f;--accent:#d9a441;
  --skin:#e1b491;--skin-hi:#f4d0ab;--skin-lo:#bd8f6a;--body-out:#141219;
  --maxw:1120px;
}
*{box-sizing:border-box}
body{margin:0;background:var(--void);color:var(--ink);
  font-family:"Archivo","Segoe UI",system-ui,sans-serif;font-size:16px;line-height:1.65;
  background-image:radial-gradient(1000px 560px at 84% -10%,rgba(217,164,65,.12),transparent 60%),
    radial-gradient(880px 520px at 6% 106%,rgba(127,232,232,.08),transparent 62%);
  background-repeat:no-repeat;}
.wrap{max-width:var(--maxw);margin:0 auto;padding:0 24px}
::selection{background:rgba(217,164,65,.28);color:#fff}
.topbar{position:sticky;top:0;z-index:40;background:#0c0c11;border-bottom:1px solid var(--line)}
.topbar .wrap{display:flex;align-items:center;gap:20px;height:56px}
.mark{font-family:"Instrument Serif",Georgia,serif;font-size:1.28rem}
.mark em{font-style:italic;color:var(--ink-2)}
.navlinks{display:flex;gap:18px;margin-left:auto;flex-wrap:wrap;justify-content:flex-end}
.navlinks a{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.7rem;text-transform:uppercase;
  letter-spacing:.16em;color:var(--ink-3);text-decoration:none;padding:4px 0;border-bottom:1px solid transparent}
.navlinks a:hover{color:var(--ink);border-color:var(--line-2)}
@media (max-width:720px){.navlinks{display:none}}
.tag-wip{font-family:"IBM Plex Mono",monospace;font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);border:1px solid rgba(217,164,65,.35);border-radius:2px;padding:3px 7px;white-space:nowrap}
.hero{padding:76px 0 40px}
.eyebrow{font-family:"IBM Plex Mono",monospace;font-size:.7rem;text-transform:uppercase;letter-spacing:.22em;
  color:var(--ink-3);margin:0 0 20px}
.hero h1{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(2.9rem,8vw,5.2rem);
  line-height:1;margin:0 0 18px;letter-spacing:-.005em}
.hero h1 em{font-style:italic;color:var(--accent)}
.dek{font-size:1.14rem;color:var(--ink-2);max-width:64ch;margin:0 0 26px}
.status{border:1px solid var(--line);border-left:2px solid var(--accent);background:var(--panel);
  border-radius:3px;padding:14px 18px;max-width:68ch;font-size:.92rem;color:var(--ink-2)}
.status b{color:var(--ink);font-weight:600}
code.f{font-family:"IBM Plex Mono",monospace;font-size:.84em;color:var(--accent)}
.legend{margin:44px 0 8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden}
.legend div{background:var(--panel);padding:16px 18px}
.legend dt{font-family:"IBM Plex Mono",monospace;font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);margin-bottom:6px}
.legend dd{margin:0;font-size:.92rem;color:var(--ink-2)}
.chapter{padding:92px 0 8px;scroll-margin-top:72px}
.chapter-kicker{font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 10px}
.chapter h2{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(2.1rem,5vw,3.4rem);
  line-height:1.02;margin:0 0 20px}
.chapter h2 em{color:var(--accent);font-style:italic}
.lead{max-width:66ch;color:var(--ink-2);margin:0 0 12px}
.lead b{color:var(--ink);font-weight:600}
.identity{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:34px;margin:8px 0 20px;align-items:start}
@media (max-width:820px){.identity{grid-template-columns:1fr;gap:24px}}
.swatches{display:flex;flex-wrap:wrap;gap:10px}
.sw{width:104px}
.sw i{display:block;height:50px;border-radius:3px;border:1px solid rgba(255,255,255,.09)}
.sw span{display:block;margin-top:6px;font-family:"IBM Plex Mono",monospace;font-size:.58rem;color:var(--ink-3)}
.sw span b{display:block;color:var(--ink-2);letter-spacing:.1em;text-transform:uppercase;font-size:.56rem;font-weight:500}
.directives{margin:0;padding:0;list-style:none;counter-reset:d}
.directives li{position:relative;padding:10px 0 10px 42px;border-top:1px solid var(--line);font-size:.92rem;color:var(--ink-2)}
.directives li:last-child{border-bottom:1px solid var(--line)}
.directives li::before{counter-increment:d;content:counter(d);position:absolute;left:0;top:9px;
  font-family:"IBM Plex Mono",monospace;font-size:.7rem;width:26px;height:22px;display:grid;place-items:center;
  border:1px solid rgba(217,164,65,.3);border-radius:2px;color:var(--accent)}
.directives li b{color:var(--ink);font-weight:600}
.plate{display:grid;grid-template-columns:300px minmax(0,1fr);gap:34px;padding:30px 0;border-top:1px solid var(--line)}
@media (max-width:760px){.plate{grid-template-columns:1fr;gap:20px}}
.viewport{position:relative;border:1px solid var(--line);border-radius:3px;
  background:radial-gradient(circle at 50% 40%,#16161f 0%,#0c0c11 72%,#090a0d 100%);overflow:hidden}
.viewport.diagram{aspect-ratio:6/5}
.viewport svg{position:absolute;inset:0;width:100%;height:100%}
.viewport .vlabel{position:absolute;left:10px;bottom:8px;font-family:"IBM Plex Mono",monospace;font-size:.58rem;
  letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}
.isnew{position:absolute;right:0;top:0;font-family:"IBM Plex Mono",monospace;font-size:.56rem;letter-spacing:.14em;
  text-transform:uppercase;padding:4px 8px;background:var(--accent);color:#1c1305;font-weight:600;border-bottom-left-radius:3px}
.plate-body h3{font-family:"Archivo",sans-serif;font-weight:600;font-size:1.32rem;margin:2px 0 3px}
.role{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.16em;text-transform:uppercase;
  color:#c99a4f;margin:0 0 14px}
.plate-body p{margin:0 0 14px;font-size:.96rem;color:var(--ink-2);max-width:60ch}
.plate-body p b{color:var(--ink);font-weight:600}
.spec{margin:16px 0 0;padding:14px 16px;border:1px solid var(--line);border-radius:3px;background:var(--panel);
  display:grid;grid-template-columns:auto 1fr;gap:4px 16px;font-family:"IBM Plex Mono",monospace;font-size:.74rem}
.spec dt{color:var(--ink-3)}
.spec dd{margin:0;color:var(--ink);font-variant-numeric:tabular-nums}
.spec .full{grid-column:1/-1;color:var(--ink-2);padding-top:8px;margin-top:4px;border-top:1px solid var(--line)}
.keys{margin:14px 0 0;display:flex;flex-wrap:wrap;gap:6px}
.keys span{font-family:"IBM Plex Mono",monospace;font-size:.63rem;padding:3px 7px;border:1px solid var(--line-2);
  border-radius:2px;color:var(--ink-2)}
.keys span b{color:var(--ink);font-weight:500}
.wiring{padding:90px 0 40px}
.wiring h2{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(1.9rem,4.4vw,2.9rem);margin:0 0 22px}
.wiring-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:4px;overflow:hidden}
.wiring-grid section{background:var(--panel);padding:20px}
.wiring-grid h4{margin:0 0 8px;font-size:.95rem;font-weight:600}
.wiring-grid p{margin:0;font-size:.9rem;color:var(--ink-2)}
.risk{margin:26px 0 0;border:1px solid rgba(217,164,65,.35);border-left:2px solid var(--accent);background:var(--panel);
  border-radius:3px;padding:16px 18px;max-width:72ch;font-size:.94rem;color:var(--ink-2)}
.risk b{color:var(--ink);font-weight:600}
footer{border-top:1px solid var(--line);padding:26px 0 60px;font-family:"IBM Plex Mono",monospace;font-size:.66rem;
  letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}
"""

DEFS = ('<svg width="0" height="0" aria-hidden="true" style="position:absolute">'
        '<defs><pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">'
        '<circle cx="1.5" cy="1.5" r="1" fill="#ffffff" fill-opacity="0.05"/>'
        '</pattern></defs></svg>')

CHAPTER_BLURB = {
 "deeprock": "Already a faction in <code class=\"f\">pilots.json</code> (Oskar Lindqvist, <code class=\"f\">mining_foreman</code>) with no look yet. The outfit that chews ore out of the belts: hardware built around the job it does, painted only where a warning is needed.",
 "kessari": "A close order that keeps to the burnt worlds. Where the Vherathi grow their hulls and the Drossholt bolt theirs, the Kessari <b>fire</b> theirs - single dark slabs of basalt-ceramic, no ornament, lit only by the seam where the stone is still cooling.",
 "meridian": "A loose confederation of independent trading ports, rich and fond of showing it. Stacked rounded tiers in brass and cream, arched windows because a Meridian captain wants to be seen arriving.",
 "theln": "Nomads who never make port for long. Ships are tensioned membrane over a light exoskeleton - translucent, kite-like, asymmetric - with running lights strung along the rigging.",
}

SWATCH_LABELS = [("hull / wall", "hull"), ("hull shadow", "hull_lo"),
                 ("glass / lights", "glass"), ("thrust", "thrust"), ("trim", "trim")]


def swatches(c):
    return "".join(
        f'<div class="sw"><i style="background:{c[k]}"></i>'
        f'<span><b>{label}</b>{c[k].upper()}</span></div>'
        for label, k in SWATCH_LABELS)


def directives(key):
    return "".join(f"<li><b>{t}</b> {d}</li>" for t, d in RUBRICS[key])


def chapter(i, key):
    c = CULTURES[key]
    n = f"{i:02d}"
    ship_fn, ship_name, ship_aria = SHIPS[key]
    o_name, o_role, o_intent, o_keys = OUTFIT_META[key]
    o_opts = OUTFITS[key]
    ship_svg = svg(ship_fn(), VB_SHIP, ship_aria, f"{key} · ship · top")
    o_inner = outfit_svg(o_opts)
    outfit_view = (f'<div class="viewport diagram" style="aspect-ratio:4/5">'
                   f'<svg viewBox="0 0 160 200" role="img" aria-label="Front view of the '
                   f'{o_name} on the shared body.">{o_inner}</svg>'
                   f'<span class="vlabel">{key} · outfit · front</span>'
                   f'<span class="isnew">New</span></div>')
    ship_keys = ", ".join(o_keys) if False else ""
    # ship spec
    ship_spec = {
        "deeprock": ("size 44", "front-heavy asymmetric maw + tank",
                     "thrusters mirrored riveted housings, aft",
                     "graphics.json space? no - ship_types.json + graphics.json entry. New."),
        "kessari": ("size 34", "single tall slab, base-heavy, one irregular edge",
                    "thrusters one, base centre; spine seam = glass_color",
                    "ship_types.json + graphics.json entry. New."),
        "meridian": ("size 40", "three centred rounded tiers, scalloped rims",
                     "thrusters mirrored fluted pair, aft",
                     "ship_types.json + graphics.json entry. New."),
        "theln": ("size 32", "thin spine + asymmetric membrane sails on a strut frame",
                  "thrusters one, base; sails = wall_trim_color at low opacity",
                  "ship_types.json + graphics.json entry. Membrane opacity is new - Ship.draw has no alpha layer yet."),
    }[key]
    return f"""
  <section class="chapter" id="{key}">
    <p class="chapter-kicker">Chapter {n} &mdash; {c['name']}</p>
    <h2>{['Built around the job','The ember in the stone','Seen arriving','Never makes port'][i-1]}</h2>
    <p class="lead">{CHAPTER_BLURB[key]}</p>

    <div class="identity">
      <div><div class="swatches">{swatches(c)}</div>
        <p style="margin:14px 0 0;font-size:.82rem;color:var(--ink-3);font-family:'IBM Plex Mono',monospace">
        cultures.json &rarr; <code class="f">{key}</code> &mdash; proposed, not in config</p></div>
      <ol class="directives">{directives(key)}</ol>
    </div>

    <p class="subhead" style="font-family:'IBM Plex Mono',monospace;font-size:.74rem;letter-spacing:.2em;text-transform:uppercase;color:var(--ink-3);margin:44px 0 4px;padding-bottom:10px;border-bottom:1px solid var(--line)">{n}&middot;A &mdash; Ship</p>
    <article class="plate">
      {ship_svg}
      <div class="plate-body">
        <h3>{ship_name} <span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:.6em;letter-spacing:.12em">MOCKUP</span></h3>
        <p class="role">ship_types.json &middot; graphics.json &rarr; ship type</p>
        <p>{ship_aria.split(':',1)[1].strip().capitalize()}</p>
        <dl class="spec">
          <dt>size</dt><dd>{ship_spec[0].split()[1]}</dd>
          <dt>silhouette</dt><dd>{ship_spec[1]}</dd>
          <dt>thrusters</dt><dd>{ship_spec[2]}</dd>
          <dd class="full">{ship_spec[3]} Colours: hull <code class="f">metal_color</code>, lights <code class="f">glass_color</code>, exhaust <code class="f">thrust_color</code>. The <code class="f">class="flame"</code> jet stays procedural (<code class="f">Ship._draw_thrusters</code>).</dd>
        </dl>
        <div class="keys"><span>Rubric: <b>1</b> &middot; <b>2</b> &middot; <b>3</b></span></div>
      </div>
    </article>

    <p class="subhead" style="font-family:'IBM Plex Mono',monospace;font-size:.74rem;letter-spacing:.2em;text-transform:uppercase;color:var(--ink-3);margin:44px 0 4px;padding-bottom:10px;border-bottom:1px solid var(--line)">{n}&middot;B &mdash; Outfit</p>
    <article class="plate">
      {outfit_view}
      <div class="plate-body">
        <h3>{o_name} <span style="color:var(--accent);font-family:'IBM Plex Mono',monospace;font-size:.6em;letter-spacing:.12em">MOCKUP</span></h3>
        <p class="role">{o_role}</p>
        <p>{o_intent}</p>
        <dl class="spec">
          <dt>on</dt><dd>the shared <code class="f">Person</code> body</dd>
          <dt>keys</dt><dd>{', '.join(o_keys)}</dd>
          <dd class="full">A <code class="f">graphics.json</code> &rarr; <code class="f">outfits</code> entry: each key is one more colour, no draw code &mdash; but the redraw here is a mockup, like the Standard Issue / R&amp;R outfit plates: <code class="f">Person.draw</code> is colour-key driven, so a genuinely new <em>silhouette</em> waits on a parts-style figure renderer.</dd>
        </dl>
        <div class="keys"><span>Rubric: <b>2</b> &middot; <b>3</b></span></div>
      </div>
    </article>
  </section>"""


def build():
    chapters = "".join(chapter(i + 1, k) for i, k in enumerate(CULTURES))
    nav = "".join(f'<a href="#{k}">{CULTURES[k]["name"].split()[-2] if len(CULTURES[k]["name"].split())>2 else CULTURES[k]["name"].split()[-1]}</a>'
                  for k in CULTURES)
    html = f"""<meta charset="utf-8">
<title>Past the Reach</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap">
<style>{CSS}</style>
{DEFS}
<header class="topbar"><div class="wrap">
  <span class="mark">Past the <em>Reach</em></span>
  <nav class="navlinks">
    <a href="#read">How to read</a>
    <a href="#deeprock">Deeprock</a>
    <a href="#kessari">Kessari</a>
    <a href="#meridian">Meridian</a>
    <a href="#theln">Theln</a>
    <a href="#wiring">Wiring in</a>
  </nav>
  <span class="tag-wip">Proposal &middot; nothing in config</span>
</div></header>

<main class="wrap">
  <section class="hero">
    <p class="eyebrow">Four proposed cultures beyond the default three</p>
    <h1>Past the <em>Reach</em></h1>
    <p class="dek">
      The default story has three cultures: the Vherathi <b>grow</b> their hulls,
      the Drossholt <b>bolt</b> theirs, the Sol Federation <b>issues</b> its own to
      spec. This atlas sketches four more for the edge of the map &mdash; one ship
      and one outfit each &mdash; so the silhouettes can be compared before any of
      it is built.
    </p>
    <div class="status">
      <b>None of this is in the game.</b> Every plate is a <span style="color:var(--accent)">MOCKUP</span>.
      The four <code class="f">cultures.json</code> entries, the ships, and the
      outfits are proposals; the ship silhouettes could be extracted into
      <code class="f">parts</code> the same way Resin &amp; Rivets was, but the
      outfit redraws would wait on a parts-style figure renderer (same as the
      Standard Issue outfit chapters). Palettes here are the ones proposed for
      each <code class="f">cultures.json</code> entry.
    </div>
    <dl class="legend" id="read">
      <div><dt>Left &mdash; specimen</dt><dd>Ship top-down (<code class="f">240&times;200</code>) or figure front-view (<code class="f">160&times;200</code>) on void-black, so silhouettes and palettes compare directly.</dd></div>
      <div><dt>Shapes only</dt><dd>Every specimen is <code class="f">&lt;polygon&gt;</code> + <code class="f">&lt;circle&gt;</code>, no stroke &mdash; outline is a larger offset shape behind, curves are many-sided polygons, the exhaust jet is a <code class="f">class="flame"</code> shape that stays procedural in-engine.</dd></div>
      <div><dt>Identity spread</dt><dd>Each chapter opens with the proposed palette as named hex swatches keyed to <code class="f">cultures.json</code> fields, and a numbered rubric of silhouette directives pulled from that culture's <code class="f">theme</code> string.</dd></div>
      <div><dt>MOCKUP</dt><dd>Nothing here is wired in. Spec blocks name real fields but are suggestions, never patches.</dd></div>
    </dl>
  </section>
{chapters}

  <section class="wiring" id="wiring">
    <h2>Wiring in</h2>
    <div class="wiring-grid">
      <section><h4>cultures.json</h4><p>Four new entries (<code class="f">deeprock</code>, <code class="f">kessari</code>, <code class="f">meridian</code>, <code class="f">theln</code>) &mdash; <code class="f">name</code>, <code class="f">description</code>, the colour keys shown, an <code class="f">interior_decoration</code> generator, and a <code class="f">theme</code> string. Self-contained; assets reference them by key.</p></section>
      <section><h4>ship_types.json + graphics.json</h4><p>One ship type + graphics entry per culture. A ship silhouette can be <b>extracted</b> from its plate into <code class="f">parts</code> via <code class="f">extract_atlas.py</code> / <code class="f">apply_parts.py</code> &mdash; add a row to the <code class="f">T</code> table. Theln's low-opacity membrane has no engine support yet (<code class="f">Ship.draw</code> draws flat opaque polygons) &mdash; it would ship as solid tinted panels until a translucency layer exists.</p></section>
      <section><h4>graphics.json &rarr; outfits</h4><p>One outfit entry per culture, each just a set of <code class="f">*_color</code> keys on the shared body. The <em>redraws</em> here are mockups &mdash; <code class="f">Person.draw</code> is colour-key driven, so a new outfit that only recolours + toggles existing accessory pieces is buildable now; a new silhouette is not.</p></section>
      <section><h4>routines &amp; pilots</h4><p>Deeprock and Theln want behaviours that don't exist yet (a mining loop, a drift). See the proposed <code class="f">MiningRoutine</code> / <code class="f">PicketRoutine</code> etc. &mdash; a culture is only half a faction without a routine and a pilot roster.</p></section>
    </div>
    <div class="risk">
      <b>Adding cultures is additive, but adding ship types and outfits is not free.</b>
      A new ship type shows up in every shipyard list and a new outfit in every
      outfitter &mdash; an old save loading into a shop sees the new stock. That's
      a story-version bump (see <code class="f">SAVE_SYSTEM.md</code>), not a
      breakage: NPCs and outfits are rebuilt from story config on load, never
      stored.
    </div>
    <p class="lead" style="margin-top:30px">
      Companion atlases: <b>Resin &amp; Rivets</b> (Vherathi + Drossholt) and
      <b>Standard Issue</b> (the shared body + Sol Federation). Same visual
      system, same strokeless rule, same <code class="f">figure_parts</code> body.
    </p>
  </section>
</main>
<footer><div class="wrap">Past the Reach &middot; four proposed cultures &middot; mockup, nothing in config &middot; default story</div></footer>
"""
    return html


if __name__ == "__main__":
    out = pathlib.Path("docs/atlases/past-the-reach.html")
    html = build()
    out.write_text(html, encoding="utf-8")
    # guard the hard rules
    for bad in ('feGaussianBlur', 'backdrop-filter', 'background-attachment:fixed',
                'IntersectionObserver', 'stroke="', 'stroke-width', '<ellipse', '<line ', '<path ', '<rect '):
        assert bad not in html, f"forbidden construct: {bad}"
    print("wrote", out, len(html), "bytes")
