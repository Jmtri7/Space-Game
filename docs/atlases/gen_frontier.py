"""Generate docs/atlases/past-the-reach.html.

A mockup atlas: seven proposed cultures for the edge of the map, each with a
detailed exotic-silhouette ship and a signature outfit built on the shared
figure_parts body - plus an opening spread that carries the "every culture
its own kit, not the same lego" idea back to the three shipped cultures
(Vherathi / Drossholt / Sol Federation).

Nothing here is in config. Run from the repo root:
    python docs/atlases/gen_frontier.py
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import figure_parts, poly, GRID
from frontier_ships import SHIPS
from frontier_outfits import OUTFITS

GRIDDEF = ('<defs><pattern id="grid" width="16" height="16" patternUnits="userSpaceOnUse">'
           '<circle cx="1.5" cy="1.5" r="1" fill="#ffffff" fill-opacity="0.05"/>'
           '</pattern></defs>')
DEFS = ('<svg width="0" height="0" aria-hidden="true" style="position:absolute">'
        + GRIDDEF + '</svg>')


# ------------------------------------------------------------------ data
CULTURES = {
 "deeprock": dict(
   name="Deeprock Mining Consortium", tab="Deeprock",
   pal=dict(hull="#5c524a", hull_lo="#413a34", glass="#ffe078", thrust="#ff9646",
            trim="#d6b03c", shadow="#332f2b"),
   h2="Built around the job",
   blurb="Already a faction in <code class=\"f\">pilots.json</code> (Oskar Lindqvist, "
         "<code class=\"f\">mining_foreman</code>) with no look yet. Hardware built "
         "around the job it does, painted only where a warning is needed.",
   rubric=[
     ("Front-heavy, functional.", "One dominant forward volume - a crusher jaw or ore scoop - a fat segmented tank body behind it, ancillary boxes (cabin, chute) clamped on wherever they cleared the load. Never tidy."),
     ("Almost no windows.", "Light is a few harsh floodlamps clustered at the working end, drawn from <code class=\"f\">glass_color</code>. The crew works by them, not by a view."),
     ("Hazard, not livery.", "Trim-yellow striping and chevrons (<code class=\"f\">wall_trim_color</code>) edge every intake, hatch and thruster. Everything else stays bare, seamed, riveted <code class=\"f\">metal_color</code>."),
     ("Industrial plant that flies.", "Segment seams and rivet rows on every barrel, a conveyor ridge down the spine, blunt quad-thruster housings. It reads as machinery first."),
   ],
   ship="A short front-heavy hauler: an interlocking toothed rock-crusher jaw at the nose, three riveted tank-barrel segments, a rung conveyor ridge on the spine, an asymmetric ore chute, forward floodlamp masts, a chevron-striped quad-thruster block.",
   outfit_role="mining_foreman - belt crews",
   outfit="A hard hat with side ear-defenders, a shoulder floodlamp throwing a cone, an oversized angular ore-scoop gauntlet, a hi-vis band across a bolted chest plate. The signature is the lamp and the ear cans - no other culture's kit carries them.",
 ),
 "kessari": dict(
   name="The Ashfall Rite", tab="Kessari",
   pal=dict(hull="#22201e", hull_lo="#33302c", glass="#ff823c", thrust="#dc4628",
            trim="#8a7a5c", shadow="#141216"),
   h2="The ember in the stone",
   blurb="A close order that keeps to the burnt worlds. Where the Vherathi grow "
         "their hulls and the Drossholt bolt theirs, the Kessari <b>fire</b> theirs "
         "- dark ceramic carved like a reliquary, lit only where the material is "
         "still cooling.",
   rubric=[
     ("One carved mass.", "A tall base-heavy monolith with stepped flying-buttress flanks, recessed relief grooves across the face, and a finial spire cluster at the nose. Roughly symmetric, one edge always left hand-irregular."),
     ("The ember seam.", "A bright ladder of <code class=\"f\">glass_color</code> down the spine with cross-ribs, a radial rose-window aperture cluster near the nose, a matching glow through the exhaust. Everything else is near-black <code class=\"f\">metal_color</code>."),
     ("Ceremonial fittings.", "The exhaust is an ornate perforated censer housing, not a nozzle; buttress edges carry an ash-grey trim line."),
     ("Cell, not cabin.", "Interiors stay narrow, dim, high-contrast: black floor and walls, one bright line of light down the centre of every room."),
   ],
   ship="A tall dark reliquary: a carved base-heavy monolith with three stepped flying-buttress flanks a side, an ember spine ladder with cross-ribs, a radial rose-window aperture cluster, a finial spire, and a perforated censer exhaust glowing through its holes.",
   outfit_role="kessari crew - pilgrims",
   outfit="A smooth full ceramic face-mask with a single vertical ember slit, ash-cloth wrappings banding the forearms and shins, a perforated censer pendant on a chain, and the ember sash the ships carry, worn. No eyes, no visor - the mask is the whole face.",
 ),
 "meridian": dict(
   name="The Meridian Free Ports", tab="Meridian",
   pal=dict(hull="#96744a", hull_lo="#6a5030", glass="#ffeec8", thrust="#ffd282",
            trim="#e8ce96", shadow="#3a2c1c"),
   h2="Seen arriving",
   blurb="A loose confederation of independent trading ports, rich and fond of "
         "showing it. Brass and cream, layered decks, swept sail-fins and lantern "
         "light - built to look good coming down the ramp.",
   rubric=[
     ("A banded lantern hull.", "One long tapering hull divided into decks by brass bands, not stacked balls. Symmetric and centred - not the Vherathi organic asymmetry."),
     ("Ornament is the point.", "Brass filigree scrollwork framing the fore hull, a stylised sunburst figurehead prow, a crowning lantern finial - every edge is trimmed (<code class=\"f\">wall_trim_color</code>)."),
     ("Windows and lanterns on show.", "An arched row of warm windows per deck plus a lantern pair at each end - a Meridian captain wants to be seen."),
     ("Swept sail-fins.", "Two large decorative fins sweep well aft from mid-hull, scalloped along the trailing edge, brass-ribbed."),
   ],
   ship="A tall ornate galleon: a long tapering lantern hull banded into four decks with brass trim and rivet seams, arched window rows with lantern pairs, filigree scrollwork on the fore hull, a sunburst figurehead prow, a crowning finial, and two scallop-edged sail-fins swept aft.",
   outfit_role="meridian captains - factors",
   outfit="A brocade over-mantle with a scalloped hem, a gold gorget and squared epaulettes, three braid-bar frogging runs across the chest, a badge of office, and a long feather plume sweeping off the folded cap. Dressed to step off the ramp.",
 ),
 "theln": dict(
   name="The Theln Drift", tab="Theln",
   pal=dict(hull="#c8c0b0", hull_lo="#9a9384", glass="#7fe8e8", thrust="#6fd0d0",
            trim="#bfe6df", shadow="#2a3230"),
   h2="Never makes port",
   blurb="Nomads who never stay anywhere long. Ships are tensioned membrane on a "
         "light frame - translucent, kite-like, asymmetric - strung with running "
         "lights like rigging.",
   rubric=[
     ("Membrane on frame.", "Sail panels (a lit membrane tint) stretched over a light exoskeleton of thin <code class=\"f\">metal_color</code> struts. Trailing edges ripple - never a straight cut, never a solid hull."),
     ("Asymmetric spars.", "Booms and struts of uneven length; one side always reaches further. A long tail boom trails aft with its own small fin."),
     ("Lights on the rigging.", "Running lights (<code class=\"f\">glass_color</code>) strung in lines along every spar and down the spine."),
     ("Sensory tendrils.", "Thin trailing lines off the nose, tipped with a light - part antenna, part streamer."),
   ],
   ship="A ragged moth-kite: a thin spine with four uneven struts carrying rippled-edge membrane sails, a long asymmetric tail boom and fin, running lights down every spar, three light-tipped sensory tendrils off the nose, a cockpit blister and two small accent pods.",
   outfit_role="theln crew - riggers",
   outfit="A translucent membrane cape on a Y-frame of struts that echoes the ship's wings, thin spar struts rising from the shoulders, a running-light strand along every edge, a visor, a one-sided half-harness and a hip pod. Built to move around a membrane hull.",
 ),
 "kaethar": dict(
   name="The Kaethar Directorate", tab="Kaethar",
   pal=dict(hull="#3a3f47", hull_lo="#282c33", glass="#cfd6de", thrust="#9fc0d8",
            trim="#d6402c", shadow="#191c21"),
   h2="Correct, and armed",
   blurb="<span class=\"newmark\">NEW CULTURE</span> A cold, hierarchical military "
         "power that garrisons the lanes and expects its transponder logs read back "
         "to it. Hard angles, gunmetal, one warning colour and nothing else.",
   rubric=[
     ("Arrowhead and rail.", "A sharp narrow nose widening to a blocky midbody, a raised spinal rail running its full length to a muzzle at the tip. Every corner is a hard angle - no fillet, no curve."),
     ("Forward-swept everything.", "Wing pylons and turret nacelles sweep <em>forward</em>, toward the target, not back. Blocky hardpoint pods on the wings."),
     ("One warning colour.", "Sharp red chevrons (<code class=\"f\">wall_trim_color</code>) along every wing leading edge, a hard geometric unit sigil on the nose, red rank/sensor bars. The hull itself stays flat gunmetal, recessed panel seams and nothing more."),
     ("Interiors: rank and file.", "A straight spine, identical cells, a painted line you walk between - the Standard Issue plan with the warmth removed."),
   ],
   ship="A stern angular warship: a hard arrowhead hull with recessed panel seams, forward-swept wing pylons with hardpoint pods and red chevron trim, a full-length raised spinal rail with a nose muzzle, two shoulder turret nacelles with stub barrels, a hard diamond unit sigil, an inline quad-thruster block.",
   outfit_role="kaethar officers - line crew",
   outfit="An angular full helm with a horizontal red sensor bar and a peaked crest, a gorget and squared pauldrons, a rigid breastplate with a hard geometric unit sigil, a straight-edged greatcoat skirt, and gold rank bars on the sleeve. Stern by construction.",
 ),
 "vetl": dict(
   name="The Vetl", tab="Vetl",
   pal=dict(hull="#6b4a35", hull_lo="#4a3122", glass="#7ce0c4", thrust="#ffb060",
            trim="#e6ddc8", shadow="#2c1d14"),
   h2="Grown, not built",
   blurb="<span class=\"newmark\">NEW CULTURE</span> A shamanistic people whose "
         "ships read as sea-creatures - broad, boneless, whip-tailed - and whose "
         "crews wear antler, hide and bead. Spirit-teal light where another culture "
         "would put a running lamp.",
   rubric=[
     ("A creature silhouette.", "A broad flat manta body - a smooth wide lens, widest at mid, tapering both ways - with forward cephalic horn-prongs and a long tapering whip tail ending in a barb."),
     ("Bone and hide.", "A fan of pale <code class=\"f\">wall_trim_color</code> rib-veins from the spine to the wing edge, a dorsal ridge of small spines, mottled darker hide patches for texture. No panel lines - it isn't panelled."),
     ("Spirit light.", "A constellation of <code class=\"f\">glass_color</code> motes on the back joined by thin lines, two large bio eye-spots near the nose. The exhaust is a soft glow at the tail, not a nozzle."),
     ("Worn, not issued.", "Crew wear antler headdresses, layered hide with a feathered hem, bead-strand necklaces, face paint, and carry a bound staff. The kit is personal - no two identical."),
   ],
   ship="A manta creature-ship: a broad flat lens body with mottled hide texture, forward-sweeping cephalic horn-prongs, a long barbed whip tail, a fan of bone rib-veins, a dorsal spine ridge, a spirit-glow constellation and two bio eye-spots, exhaust as a soft tail glow.",
   outfit_role="vetl crew - bone-speakers",
   outfit="A branching antler headdress, a layered hide mantle with a ragged feathered hem, two bead-strand necklace arcs, vertical face-paint marks, and a carried bound staff topped with feathers and a spirit mote. Spirit-teal motes drift around the figure.",
 ),
 "salt_crows": dict(
   name="The Salt Crows", tab="Salt Crows",
   pal=dict(hull="#7a3b2c", hull_lo="#4a241b", glass="#ffd24a", thrust="#ff7a2a",
            trim="#c98a3c", shadow="#1c110c"),
   h2="Cut from three other ships",
   blurb="<span class=\"newmark\">NEW CULTURE</span> Scavengers and raiders. Nothing "
         "they fly or wear was built as a whole - it's rust, tar, and scavenged "
         "brass, with a ram on the front and a crow daubed on the side.",
   rubric=[
     ("Asymmetric and kinked.", "A bent spine, wider to one side, a heavy pointed ram prow with reinforcement plates. Deliberately lopsided."),
     ("Three ships' worth of wings.", "Each wing is scavenged from a different culture and bolted on crooked - a tapered Vherathi one, a riveted Drossholt box, a clean Federation panel - in their original colours."),
     ("Mismatched everything.", "Two oversized bolted engine housings, one much bigger, both with visible bolt rings and patch plates. Rust streaks, brass patches, trophy trinkets hung along the rail."),
     ("The mark.", "A crude asymmetric bone-white crow glyph daubed on the hull. It's the only thing that's theirs."),
   ],
   ship="An asymmetric raider: a kinked rust hull wider to port, a plated ram prow, three mismatched scavenged wings in their original culture colours, two oversized bolted engine housings with bolt rings, a folded boarding gantry with a grapnel, trophy trinkets, and a daubed crow mark.",
   outfit_role="salt crew - deck hands",
   outfit="A tied headwrap with a trailing tail and a salvaged monocle-visor over one eye, a scavenged green Vherathi shoulder curve, a riveted chest patch, a hook-hand, a bandolier sash of tools, trophy trinkets at the belt, and the crow mark stencilled on the chest.",
 ),
}

# The three shipped cultures - redesign recommendations only (they'd land back
# in Resin & Rivets / Standard Issue, not here).
SHIPPED = {
 "vherathi": ("Vherathi Concord", "Reef-Diver",
   "A helmet dome carrying <b>asymmetric clusters of circular eye-bubbles</b> - "
   "three or four on one side, one or two on the other - instead of a single "
   "face circle, and a branching resin-vein glow tracing up the torso and one "
   "arm. The grown guard-blade stays.",
   "resin-and-rivets.html"),
 "drossholt": ("Drossholt Company", "Rust-Hand",
   "<b>Riveted patch-plates</b> - three or four mismatched rectangles bolted on "
   "at odd angles, each a different shade - plus a bolted box respirator with a "
   "hose to a hip canister, and one big pauldron over one bare shoulder.",
   "resin-and-rivets.html"),
 "federation": ("Sol Federation", "Issue Rating",
   "A regulation helmet with a <b>horizontal visor slit and a chin guard</b> "
   "(not a bubble), a white contrast centreline stripe, an amber hazard-chevron "
   "shoulder flash, and a stencilled <code class=\"f\">SF-###</code> registration "
   "on the chest.",
   "standard-issue.html"),
}

SWATCH_LABELS = [("hull / wall", "hull"), ("hull shadow", "hull_lo"),
                 ("glass / lights", "glass"), ("thrust", "thrust"), ("trim", "trim")]


# ------------------------------------------------------------------ builders
def ship_svg(key):
    fn, name = SHIPS[key]
    inner = fn(CULTURES[key]["pal"])
    aria = CULTURES[key]["ship"].replace('"', "'")
    return (f'<div class="viewport diagram"><svg viewBox="0 0 240 200" role="img" '
            f'aria-label="Top-down {name}: {aria}">{GRIDDEF}{inner}</svg>'
            f'<span class="vlabel">{key} &middot; ship &middot; top</span>'
            f'<span class="isnew">Mockup</span></div>')


def outfit_svg(key):
    fn, name = OUTFITS[key]
    base, pre, post = fn()
    body = "".join(figure_parts(**base))
    inner = (poly([(0, 0), (140, 0), (140, 210), (0, 210)], GRID)
             + pre + body + post)
    return (f'<div class="viewport fig"><svg viewBox="0 0 140 210" role="img" '
            f'aria-label="Front view of the {name} on the shared body.">{GRIDDEF}{inner}</svg>'
            f'<span class="vlabel">{key} &middot; outfit &middot; front</span>'
            f'<span class="isnew">Mockup</span></div>')


def swatches(pal):
    return "".join(
        f'<div class="sw"><i style="background:{pal[k]}"></i>'
        f'<span><b>{label}</b>{pal[k].upper()}</span></div>'
        for label, k in SWATCH_LABELS)


def directives(rubric):
    return "".join(f"<li><b>{t}</b> {d}</li>" for t, d in rubric)


def chapter(i, key):
    c = CULTURES[key]
    n = f"{i:02d}"
    _fn, ship_name = SHIPS[key]
    _ofn, outfit_name = OUTFITS[key]
    sub = ('font-family:\'IBM Plex Mono\',monospace;font-size:.74rem;letter-spacing:.2em;'
           'text-transform:uppercase;color:var(--ink-3);margin:44px 0 4px;padding-bottom:10px;'
           'border-bottom:1px solid var(--line)')
    return f"""
  <section class="chapter" id="{key}">
    <p class="chapter-kicker">Chapter {n} &mdash; {c['name']}</p>
    <h2>{c['h2']}</h2>
    <p class="lead">{c['blurb']}</p>

    <div class="identity">
      <div><div class="swatches">{swatches(c['pal'])}</div>
        <p style="margin:14px 0 0;font-size:.8rem;color:var(--ink-3);font-family:'IBM Plex Mono',monospace">
        cultures.json &rarr; <code class="f">{key}</code> &mdash; proposed, not in config</p></div>
      <ol class="directives">{directives(c['rubric'])}</ol>
    </div>

    <p class="subhead" style="{sub}">{n}&middot;A &mdash; Ship: {ship_name}</p>
    <article class="plate">
      {ship_svg(key)}
      <div class="plate-body">
        <h3>{ship_name} <span class="mk">MOCKUP</span></h3>
        <p class="role">ship_types.json &middot; graphics.json &rarr; ship type</p>
        <p>{c['ship']}</p>
        <dl class="spec">
          <dt>silhouette</dt><dd>{c['rubric'][0][0].rstrip('.')}</dd>
          <dt>colours</dt><dd>hull <code class="f">metal_color</code> &middot; lights <code class="f">glass_color</code> &middot; exhaust <code class="f">thrust_color</code> &middot; trim <code class="f">wall_trim_color</code></dd>
          <dd class="full">Strokeless <code class="f">&lt;polygon&gt;</code>/<code class="f">&lt;circle&gt;</code>, so this could be extracted into <code class="f">parts</code> the way Resin &amp; Rivets was (<code class="f">extract_atlas.py</code> / <code class="f">apply_parts.py</code>). The <code class="f">class="flame"</code> jet stays procedural (<code class="f">Ship._draw_thrusters</code>).</dd>
        </dl>
        <div class="keys"><span>Rubric: <b>1</b> &middot; <b>2</b> &middot; <b>3</b></span></div>
      </div>
    </article>

    <p class="subhead" style="{sub}">{n}&middot;B &mdash; Outfit: {outfit_name}</p>
    <article class="plate">
      {outfit_svg(key)}
      <div class="plate-body">
        <h3>{outfit_name} <span class="mk">MOCKUP</span></h3>
        <p class="role">{c['outfit_role']}</p>
        <p>{c['outfit']}</p>
        <dl class="spec">
          <dt>on</dt><dd>the shared <code class="f">Person</code> body + standard kit</dd>
          <dt>signature</dt><dd>{c['rubric'][3][0].rstrip('.') if len(c['rubric']) > 3 else c['rubric'][-1][0].rstrip('.')}</dd>
          <dd class="full">The recoloured base uses existing <code class="f">graphics.json</code> keys; the <em>signature</em> pieces are new geometry, so a full redraw waits on a parts-style figure renderer (same caveat as the Standard Issue / R&amp;R outfit chapters). The signature elements generalise across this culture's other roles &mdash; a Kessari guard and pilot both wear the ember-slit mask.</dd>
        </dl>
        <div class="keys"><span>Signature: rubric <b>{len(c['rubric'])}</b></span></div>
      </div>
    </article>
  </section>"""


def shipped_section():
    figs = []
    for key, (cname, oname, desc, doc) in SHIPPED.items():
        fn, _ = OUTFITS[key]
        base, pre, post = fn()
        body = "".join(figure_parts(**base))
        inner = (poly([(0, 0), (140, 0), (140, 210), (0, 210)], GRID) + pre + body + post)
        figs.append(f"""
      <article class="plate">
        <div class="viewport fig"><svg viewBox="0 0 140 210" role="img"
          aria-label="Front view of the redesigned {oname} for {cname}.">{GRIDDEF}{inner}</svg>
          <span class="vlabel">{key} &middot; redesign</span></div>
        <div class="plate-body">
          <h3>{cname} &mdash; {oname}</h3>
          <p class="role">redesign &middot; lands in <code class="f">{doc}</code></p>
          <p>{desc}</p>
        </div>
      </article>""")
    return "".join(figs)


def build():
    chapters = "".join(chapter(i + 1, k) for i, k in enumerate(CULTURES))
    return f"""<meta charset="utf-8">
<title>Past the Reach</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap">
<style>
:root{{
  --void:#0a0a0e;--panel:#131319;--ink:#ece9f4;--ink-2:#a5a2b6;--ink-3:#6d6a7e;
  --line:#292935;--line-2:#35333f;--accent:#d9a441;
  --skin:#e1b491;--skin-hi:#f4d0ab;--skin-lo:#bd8f6a;--body-out:#141219;
  --maxw:1120px;
}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--void);color:var(--ink);
  font-family:"Archivo","Segoe UI",system-ui,sans-serif;font-size:16px;line-height:1.65;
  background-image:radial-gradient(1000px 560px at 84% -10%,rgba(217,164,65,.12),transparent 60%),
    radial-gradient(880px 520px at 6% 106%,rgba(127,232,232,.07),transparent 62%);
  background-repeat:no-repeat;}}
.wrap{{max-width:var(--maxw);margin:0 auto;padding:0 24px}}
::selection{{background:rgba(217,164,65,.28);color:#fff}}
.topbar{{position:sticky;top:0;z-index:40;background:#0c0c11;border-bottom:1px solid var(--line)}}
.topbar .wrap{{display:flex;align-items:center;gap:20px;height:56px}}
.mark{{font-family:"Instrument Serif",Georgia,serif;font-size:1.28rem}}
.mark em{{font-style:italic;color:var(--ink-2)}}
.navlinks{{display:flex;gap:16px;margin-left:auto;flex-wrap:wrap;justify-content:flex-end}}
.navlinks a{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:.68rem;text-transform:uppercase;
  letter-spacing:.14em;color:var(--ink-3);text-decoration:none;padding:4px 0;border-bottom:1px solid transparent}}
.navlinks a:hover{{color:var(--ink);border-color:var(--line-2)}}
@media (max-width:820px){{.navlinks{{display:none}}}}
.tag-wip{{font-family:"IBM Plex Mono",monospace;font-size:.6rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--accent);border:1px solid rgba(217,164,65,.35);border-radius:2px;padding:3px 7px;white-space:nowrap}}
.hero{{padding:76px 0 40px}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:.7rem;text-transform:uppercase;letter-spacing:.22em;
  color:var(--ink-3);margin:0 0 20px}}
.hero h1{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(2.9rem,8vw,5.2rem);
  line-height:1;margin:0 0 18px;letter-spacing:-.005em}}
.hero h1 em{{font-style:italic;color:var(--accent)}}
.dek{{font-size:1.14rem;color:var(--ink-2);max-width:64ch;margin:0 0 26px}}
.status{{border:1px solid var(--line);border-left:2px solid var(--accent);background:var(--panel);
  border-radius:3px;padding:14px 18px;max-width:70ch;font-size:.92rem;color:var(--ink-2)}}
.status b{{color:var(--ink);font-weight:600}}
code.f{{font-family:"IBM Plex Mono",monospace;font-size:.84em;color:var(--accent)}}
.legend{{margin:44px 0 8px;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:4px;overflow:hidden}}
.legend div{{background:var(--panel);padding:16px 18px}}
.legend dt{{font-family:"IBM Plex Mono",monospace;font-size:.66rem;letter-spacing:.14em;text-transform:uppercase;
  color:var(--ink-3);margin-bottom:6px}}
.legend dd{{margin:0;font-size:.92rem;color:var(--ink-2)}}
.chapter{{padding:88px 0 8px;scroll-margin-top:72px}}
.chapter-kicker{{font-family:"IBM Plex Mono",monospace;font-size:.72rem;letter-spacing:.2em;text-transform:uppercase;
  color:var(--ink-3);margin:0 0 10px}}
.chapter h2{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(2.1rem,5vw,3.4rem);
  line-height:1.02;margin:0 0 20px}}
.chapter h2 em{{color:var(--accent);font-style:italic}}
.lead{{max-width:66ch;color:var(--ink-2);margin:0 0 12px}}
.lead b{{color:var(--ink);font-weight:600}}
.newmark{{font-family:"IBM Plex Mono",monospace;font-size:.6rem;letter-spacing:.14em;color:var(--accent);
  border:1px solid rgba(217,164,65,.4);border-radius:2px;padding:2px 6px;margin-right:8px;white-space:nowrap;
  vertical-align:middle}}
.identity{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1.15fr);gap:34px;margin:8px 0 20px;align-items:start}}
@media (max-width:820px){{.identity{{grid-template-columns:1fr;gap:24px}}}}
.swatches{{display:flex;flex-wrap:wrap;gap:10px}}
.sw{{width:104px}}
.sw i{{display:block;height:50px;border-radius:3px;border:1px solid rgba(255,255,255,.09)}}
.sw span{{display:block;margin-top:6px;font-family:"IBM Plex Mono",monospace;font-size:.58rem;color:var(--ink-3)}}
.sw span b{{display:block;color:var(--ink-2);letter-spacing:.1em;text-transform:uppercase;font-size:.56rem;font-weight:500}}
.directives{{margin:0;padding:0;list-style:none;counter-reset:d}}
.directives li{{position:relative;padding:10px 0 10px 42px;border-top:1px solid var(--line);font-size:.92rem;color:var(--ink-2)}}
.directives li:last-child{{border-bottom:1px solid var(--line)}}
.directives li::before{{counter-increment:d;content:counter(d);position:absolute;left:0;top:9px;
  font-family:"IBM Plex Mono",monospace;font-size:.7rem;width:26px;height:22px;display:grid;place-items:center;
  border:1px solid rgba(217,164,65,.3);border-radius:2px;color:var(--accent)}}
.directives li b{{color:var(--ink);font-weight:600}}
.plate{{display:grid;grid-template-columns:300px minmax(0,1fr);gap:34px;padding:26px 0;border-top:1px solid var(--line)}}
@media (max-width:760px){{.plate{{grid-template-columns:1fr;gap:20px}}}}
.viewport{{position:relative;border:1px solid var(--line);border-radius:3px;
  background:radial-gradient(circle at 50% 40%,#16161f 0%,#0c0c11 72%,#090a0d 100%);overflow:hidden}}
.viewport.diagram{{aspect-ratio:6/5}}
.viewport.fig{{aspect-ratio:2/3}}
.viewport svg{{position:absolute;inset:0;width:100%;height:100%}}
.viewport .vlabel{{position:absolute;left:10px;bottom:8px;font-family:"IBM Plex Mono",monospace;font-size:.56rem;
  letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}}
.isnew{{position:absolute;right:0;top:0;font-family:"IBM Plex Mono",monospace;font-size:.54rem;letter-spacing:.12em;
  text-transform:uppercase;padding:4px 8px;background:var(--accent);color:#1c1305;font-weight:600;border-bottom-left-radius:3px}}
.plate-body h3{{font-family:"Archivo",sans-serif;font-weight:600;font-size:1.32rem;margin:2px 0 3px}}
.mk{{color:var(--accent);font-family:"IBM Plex Mono",monospace;font-size:.58em;letter-spacing:.12em}}
.role{{font-family:"IBM Plex Mono",monospace;font-size:.68rem;letter-spacing:.14em;text-transform:uppercase;
  color:#c99a4f;margin:0 0 14px}}
.plate-body p{{margin:0 0 14px;font-size:.95rem;color:var(--ink-2);max-width:60ch}}
.plate-body p b{{color:var(--ink);font-weight:600}}
.spec{{margin:16px 0 0;padding:14px 16px;border:1px solid var(--line);border-radius:3px;background:var(--panel);
  display:grid;grid-template-columns:auto 1fr;gap:4px 16px;font-family:"IBM Plex Mono",monospace;font-size:.73rem}}
.spec dt{{color:var(--ink-3)}}
.spec dd{{margin:0;color:var(--ink)}}
.spec .full{{grid-column:1/-1;color:var(--ink-2);padding-top:8px;margin-top:4px;border-top:1px solid var(--line)}}
.keys{{margin:14px 0 0;display:flex;flex-wrap:wrap;gap:6px}}
.keys span{{font-family:"IBM Plex Mono",monospace;font-size:.63rem;padding:3px 7px;border:1px solid var(--line-2);
  border-radius:2px;color:var(--ink-2)}}
.keys span b{{color:var(--ink);font-weight:500}}
.wiring{{padding:88px 0 40px}}
.wiring h2{{font-family:"Instrument Serif",Georgia,serif;font-weight:400;font-size:clamp(1.9rem,4.4vw,2.9rem);margin:0 0 22px}}
.wiring-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1px;background:var(--line);
  border:1px solid var(--line);border-radius:4px;overflow:hidden}}
.wiring-grid section{{background:var(--panel);padding:20px}}
.wiring-grid h4{{margin:0 0 8px;font-size:.95rem;font-weight:600}}
.wiring-grid p{{margin:0;font-size:.9rem;color:var(--ink-2)}}
.risk{{margin:26px 0 0;border:1px solid rgba(217,164,65,.35);border-left:2px solid var(--accent);background:var(--panel);
  border-radius:3px;padding:16px 18px;max-width:72ch;font-size:.94rem;color:var(--ink-2)}}
.risk b{{color:var(--ink);font-weight:600}}
footer{{border-top:1px solid var(--line);padding:26px 0 60px;font-family:"IBM Plex Mono",monospace;font-size:.66rem;
  letter-spacing:.1em;color:var(--ink-3);text-transform:uppercase}}
</style>
{DEFS}
<header class="topbar"><div class="wrap">
  <span class="mark">Past the <em>Reach</em></span>
  <nav class="navlinks">
    <a href="#read">Read</a>
    <a href="#signature">Signature kit</a>
    {"".join(f'<a href="#{k}">{CULTURES[k]["tab"]}</a>' for k in CULTURES)}
    <a href="#wiring">Wiring in</a>
  </nav>
  <span class="tag-wip">Proposal &middot; nothing in config</span>
</div></header>

<main class="wrap">
  <section class="hero">
    <p class="eyebrow">Seven proposed cultures &middot; distinct silhouettes, distinct kit</p>
    <h1>Past the <em>Reach</em></h1>
    <p class="dek">
      The default story has three cultures and they read as three &mdash; grown,
      bolted, issued. This atlas proposes <b>seven more</b> for the edge of the
      map, and holds each to a harder standard: an <b>exotic ship silhouette</b>
      you'd know in one frame, and an outfit with a <b>signature piece no other
      culture wears</b> &mdash; an ember-slit mask, an antler headdress, a helm of
      eye-bubbles.
    </p>
    <div class="status">
      <b>None of this is in the game.</b> Every plate is a <span style="color:var(--accent)">MOCKUP</span>.
      Ships are strokeless <code class="f">&lt;polygon&gt;</code>/<code class="f">&lt;circle&gt;</code>
      and could be extracted into <code class="f">parts</code>; the outfit redraws
      wait on a parts-style figure renderer, the same as the Standard Issue outfit
      chapters. Three of these cultures are brand new (Kaethar, Vetl, Salt Crows);
      the other four refine the earlier frontier sketches with far more detail.
      The shared body here carries the <b>cinched waist</b> now in
      <code class="f">gen_si.figure_parts</code> / <code class="f">person_figure.py</code>
      &mdash; belts sit at the waist, roughly halfway up, and every torso is an
      hourglass whether or not an outfit covers it.
    </div>
    <dl class="legend" id="read">
      <div><dt>Left &mdash; specimen</dt><dd>Ship top-down (<code class="f">240&times;200</code>) or figure front-view (<code class="f">140&times;210</code>) on void-black, so silhouettes and palettes compare directly.</dd></div>
      <div><dt>Shapes only</dt><dd>Every specimen is <code class="f">&lt;polygon&gt;</code> + <code class="f">&lt;circle&gt;</code>, no stroke &mdash; outline is a larger offset shape behind, curves are many-sided polygons, thick lines are filled ribbons.</dd></div>
      <div><dt>Identity spread</dt><dd>Each chapter opens with the proposed palette (swatches keyed to <code class="f">cultures.json</code> fields) and a numbered rubric of silhouette directives.</dd></div>
      <div><dt>MOCKUP</dt><dd>Nothing here is wired in. Spec blocks name real fields but are suggestions, never patches.</dd></div>
    </dl>
  </section>

  <section class="chapter" id="signature">
    <p class="chapter-kicker">Before the chapters &mdash; the principle</p>
    <h2>Every culture its <em>own</em> kit</h2>
    <p class="lead">
      The shared <code class="f">Person</code> body is colour-key driven: an outfit
      recolours it and toggles a fixed set of accessory pieces &mdash; a collar, a
      sash, a backpack, a visor. It's efficient, but it means a Vherathi hardsuit
      and a Drossholt vacsuit are the <em>same silhouette</em> in different colours.
      The fix is a small set of <b>culture-signature shapes</b> &mdash; new
      geometry, one or two per culture, that nobody else uses. This section shows
      the idea applied back to the three <b>shipped</b> cultures; the seven
      chapters below each carry their own.
    </p>
    {shipped_section()}
  </section>
{chapters}

  <section class="wiring" id="wiring">
    <h2>Wiring in</h2>
    <div class="wiring-grid">
      <section><h4>cultures.json</h4><p>Seven new entries &mdash; <code class="f">name</code>, <code class="f">description</code>, the colour keys shown, an <code class="f">interior_decoration</code> generator, a <code class="f">theme</code> string. Self-contained; assets reference them by key.</p></section>
      <section><h4>ship_types.json + graphics.json</h4><p>One ship type + graphics entry per culture. Each ship silhouette can be <b>extracted</b> from its plate into <code class="f">parts</code> via <code class="f">extract_atlas.py</code> / <code class="f">apply_parts.py</code> &mdash; add a row to the <code class="f">T</code> table. The Vetl's soft tail glow and the Theln's translucent membrane have no engine support yet (<code class="f">Ship.draw</code> draws flat opaque polygons) &mdash; they'd ship as solid tinted shapes until a translucency / additive layer exists.</p></section>
      <section><h4>graphics.json &rarr; outfits &amp; the figure renderer</h4><p>The recoloured base of each outfit is buildable now (existing <code class="f">*_color</code> keys). The <b>signature pieces are new geometry</b> &mdash; an ember-slit mask, antlers, eye-bubble clusters &mdash; so they need a parts-style figure renderer (the <code class="f">gen_si.figure_parts</code> generator already produces exactly this kind of data; <code class="f">build_person_figure.py</code> bakes it into <code class="f">person_figure.py</code>). Adding a <code class="f">figure_signature</code> table keyed by culture would land all ten redesigns, shipped cultures included.</p></section>
      <section><h4>routines &amp; pilots</h4><p>Kaethar wants a patrol/picket routine, the Salt Crows a raider, Deeprock a mining loop, the Vetl an explorer. A culture is half a faction without a routine and a pilot roster &mdash; see the routine proposals discussed alongside this atlas.</p></section>
    </div>
    <div class="risk">
      <b>Adding cultures is additive; adding ship types and outfits is not free.</b>
      A new ship type shows up in every shipyard list and a new outfit in every
      outfitter &mdash; an old save loading into a shop sees the new stock. That's a
      story-version bump (see <code class="f">SAVE_SYSTEM.md</code>), not a
      breakage: NPCs and outfits are rebuilt from story config on load, never
      stored.
    </div>
    <p class="lead" style="margin-top:30px">
      Companion atlases: <b>Resin &amp; Rivets</b> (Vherathi + Drossholt) and
      <b>Standard Issue</b> (the shared body + Sol Federation) &mdash; the shipped
      record. Same visual system, same strokeless rule, same
      <code class="f">figure_parts</code> body.
    </p>
  </section>
</main>
<footer><div class="wrap">Past the Reach &middot; seven proposed cultures &middot; mockup, nothing in config &middot; default story</div></footer>
"""


if __name__ == "__main__":
    out = pathlib.Path("docs/atlases/past-the-reach.html")
    html = build()
    out.write_text(html, encoding="utf-8")
    for bad in ('feGaussianBlur', 'backdrop-filter', 'background-attachment:fixed',
                'IntersectionObserver', 'stroke="', 'stroke-width', '<ellipse', '<line ',
                '<path ', '<rect ', '@keyframes'):
        assert bad not in html, f"forbidden construct: {bad}"
    print("wrote", out, len(html), "bytes;",
          html.count("<svg"), "svgs;", html.count('class="chapter"'), "chapters")
