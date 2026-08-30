"""Generate docs/atlases/common-kit.html - the shared Person body and the
culture-neutral civilian / service outfits from graphics.json, redrawn on the
current cinched-waist body with a role-distinguishing detail each.

Split out of Standard Issue (which keeps the Sol Federation hardware). Run
from the repo root:  python docs/atlases/gen_common.py
"""
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import figure_parts, poly, circ, bar, dashed_bar, GRID
from atlas_shell import css, DEFS, GRIDDEF
from common_kit import OUTFITS

ACCENT, ACCENT_RGB = "#8fb9c8", "143,185,200"

CHAPTERS = [
 ("The working kit", "working",
  "The suits an NPC wears to do a job. Colour tells you the department; the "
  "<b>detail</b> tells you the trade - a mechanic's tool belt and knee pads, a "
  "dockworker's hi-vis tabard, a miner's lamp and drill.",
  ["space_suit", "flight_suit", "mechanic", "dockworker", "miner", "security"]),
 ("Civil service", "civil",
  "The station's own authority tier - not a culture's navy, the neutral "
  "administration that runs the neutral ports. Braid, boards and a badge of "
  "office.",
  ["station_command", "marshal"]),
 ("Care &amp; the fringe", "fringe",
  "Medicine, research, and the people who'd rather not be identified at all. "
  "The white coats read as care; the hoods read as the opposite.",
  ["medic", "surgeon", "researcher", "civilian", "smuggler", "ranger", "bounty_hunter"]),
]

KEYLINES = {
 "space_suit": "helmet · suit · boot",
 "flight_suit": "helmet · suit · boot · +harness",
 "mechanic": "helmet · suit · boot · belt · +hardhat lamp · knee pads",
 "dockworker": "helmet · suit · boot · chest_plate · +hi-vis tabard",
 "miner": "helmet · suit · boot · +lamp · backpack · drill",
 "security": "helmet · suit · boot · visor · +vest · baton",
 "station_command": "helmet · suit · boot · collar · shoulders · +braid · cap",
 "marshal": "hat · suit · boot · coat · +star · holster",
 "medic": "helmet · suit · boot · badge(cross) · +armband · satchel",
 "surgeon": "helmet · suit · boot · visor · +mask · scrub cap · gloves",
 "researcher": "suit · boot · coat · visor · +pens · specimen case",
 "civilian": "suit · boot · +soft collar · satchel",
 "smuggler": "suit · boot · +hood · long coat",
 "ranger": "suit · boot · coat · +trek pack · slung rifle · compass",
 "bounty_hunter": "helmet · suit · boot · visor · backpack · +plates · bandolier",
}


def outfit_inner(key):
    fn, _n, _r = OUTFITS[key]
    base, pre, post = fn()
    return (poly([(0, 0), (140, 0), (140, 210), (0, 210)], GRID)
            + pre + "".join(figure_parts(**base)) + post)


def outfit_card(key):
    _fn, name, role = OUTFITS[key]
    return f"""<figure class="card">
      <svg viewBox="0 0 140 210" role="img" aria-label="Front view of the {name} on the shared body.">{GRIDDEF}{outfit_inner(key)}</svg>
      <figcaption><b>{name}</b><p class="role">{role}</p>
        <div class="keyline">{KEYLINES.get(key, "")}</div></figcaption>
    </figure>"""


def anatomy_svg():
    fig = "".join(figure_parts(suit="#565660", boot="#3f3f48", no_helmet=True, hipline=True))
    g = f'<g transform="translate(66,6) scale(1.0)">{fig}</g>'
    lab = ('<g fill="#8b97ab" font-family="IBM Plex Mono, monospace" font-size="7">'
           '<text x="6" y="52">head — unchanged</text>'
           '<text x="6" y="90">rounded shoulder,</text><text x="6" y="99">arm connects flush</text>'
           '<text x="6" y="132">cinched waist —</text><text x="6" y="141">belts anchor here</text>'
           '<text x="196" y="150" text-anchor="end">hip flares back to</text>'
           '<text x="196" y="159" text-anchor="end">near the chest width</text>'
           '<text x="196" y="196" text-anchor="end">longer legs, two boots</text></g>')
    lines = (dashed_bar(58, 128, 118, 128, 0.8, ACCENT, dash=2.4, gap=2.2)
             + dashed_bar(126, 86, 150, 86, 0.8, ACCENT, dash=2.4, gap=2.2)
             + dashed_bar(126, 152, 150, 152, 0.8, ACCENT, dash=2.4, gap=2.2))
    return (f'<svg viewBox="0 0 240 210" role="img" aria-label="Labelled anatomy of the shared Person body: '
            f'head, rounded shoulders with the arm connecting flush, a cinched waist where belts sit, a hip that '
            f'flares back to near the chest width, and longer legs on two boots.">{GRIDDEF}'
            f'<polygon points="0,0 240,0 240,210 0,210" fill="url(#grid)"/>{lines}{g}{lab}</svg>')


def slotmap_svg():
    fig = "".join(figure_parts(
        helmet="#3a3a44", suit="#55555f", leg="#3f3f48", boot="#333333",
        backpack="#3a3a44", spikes="#4a4a55", antenna="#4a4a55", collar="#6a6a75",
        shoulders="#6a6a75", chest="#63636e", sash="#75757f", badge="#8a8a94",
        belt="#4a4a54", buckle="#7a7a84", visor="#5a5a64", pod="#5a5a64"))
    g = f'<g transform="translate(66,6)">{fig}</g>'
    lab = ('<g fill="#8b97ab" font-family="IBM Plex Mono, monospace" font-size="6.5">'
           '<text x="6" y="28">antenna_color</text>'
           '<text x="6" y="66">helmet_color</text>'
           '<text x="6" y="86">spike_color</text>'
           '<text x="6" y="120">shoulder_color</text>'
           '<text x="6" y="150">chest_plate_color</text>'
           '<text x="234" y="70" text-anchor="end">visor_color</text>'
           '<text x="234" y="100" text-anchor="end">collar_color</text>'
           '<text x="234" y="120" text-anchor="end">sash_color</text>'
           '<text x="234" y="140" text-anchor="end">badge_color</text>'
           '<text x="234" y="162" text-anchor="end">belt_color / buckle</text>'
           '<text x="234" y="182" text-anchor="end">backpack_color (behind)</text></g>')
    return (f'<svg viewBox="0 0 240 210" role="img" aria-label="Accessory slot map: every optional outfit colour '
            f'key shown at once in grey - antenna, helmet, spikes, shoulders, chest plate, visor, collar, sash, '
            f'badge, belt, backpack.">{GRIDDEF}'
            f'<polygon points="0,0 240,0 240,210 0,210" fill="url(#grid)"/>{g}{lab}</svg>')


def build():
    chapters = ""
    for title, cid, lead, keys in CHAPTERS:
        cards = "".join(outfit_card(k) for k in keys)
        chapters += f"""
  <section class="chapter" id="{cid}">
    <p class="chapter-kicker">{title}</p>
    <h2>{title}</h2>
    <p class="lead">{lead}</p>
    <div class="grid-outfits">{cards}</div>
  </section>"""

    return f"""<meta charset="utf-8">
<title>Common Kit</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap">
{css(ACCENT, ACCENT_RGB)}
{DEFS}
<header class="topbar"><div class="wrap">
  <span class="mark">Common <em>Kit</em></span>
  <nav class="navlinks">
    <a href="#read">Read</a>
    <a href="#body">The body</a>
    <a href="#working">Working kit</a>
    <a href="#civil">Civil service</a>
    <a href="#fringe">Care &amp; fringe</a>
    <a href="#wiring">Wiring in</a>
  </nav>
  <span class="tag-wip">Body shipped &middot; outfit redraws mockup</span>
</div></header>

<main class="wrap">
  <section class="hero">
    <p class="eyebrow">The shared body &amp; the culture-neutral kit</p>
    <h1>One body, <em>worn</em> a hundred ways</h1>
    <p class="dek">
      Every character in the game &mdash; the player on foot, every station NPC,
      every ship's pilot &mdash; is drawn from a <b>single <code class="f">Person</code>
      body</b>. An outfit only recolours it and bolts on flat accessory pieces.
      This atlas holds that body and the <code class="f">graphics.json</code>
      outfits that <b>aren't tied to a culture</b> &mdash; the standard suit, the
      station trades, the civil service, the fringe. The three cultures each get
      their own atlas.
    </p>
    <div class="status">
      <b>The body shipped; the outfit redraws are a <span style="color:var(--accent)">MOCKUP</span>.</b>
      The shared <code class="f">Person</code> now stands on two legs, walks
      (<code class="f">person.py</code>'s <code class="f">_leg_stance</code> /
      <code class="f">_arm_swing</code>), has a <b>cinched waist</b> with the
      belts moved up to it, and rounded shoulders the arm connects to
      &mdash; all baked from <code class="f">gen_si.figure_parts</code> into
      <code class="f">person_figure.py</code>. The <em>role-detail</em> pieces
      below (tool belt, tabard, hood, mask) are new geometry, so the redraws
      wait on a parts-style figure renderer, the same as the earlier outfit
      chapters.
    </div>
    <dl class="legend" id="read">
      <div><dt>Left &mdash; specimen</dt><dd>Front-view figure at a fixed height on void-black, so silhouettes and palettes compare directly.</dd></div>
      <div><dt>Shapes only</dt><dd>Every specimen is <code class="f">&lt;polygon&gt;</code> + <code class="f">&lt;circle&gt;</code>, no stroke &mdash; outline is a larger offset shape behind, curves are many-sided polygons.</dd></div>
      <div><dt>Body vs. detail</dt><dd>The recoloured base uses existing <code class="f">*_color</code> keys (buildable now). The role detail is the mockup part.</dd></div>
      <div><dt>Keyline</dt><dd>Under each figure: the <code class="f">graphics.json</code> keys it sets, then <code class="f">+</code> the new detail.</dd></div>
    </dl>
  </section>

  <section class="chapter" id="body">
    <p class="chapter-kicker">Chapter 01 &mdash; The shared body</p>
    <h2>The body every outfit <em>starts</em> from</h2>
    <p class="lead">
      Three shapes shaded from one skin tone, plus legs, plus a set of optional
      accessory pieces an outfit switches on by naming a colour. It stands on two
      boots and walks with them; it has a <b>cinched waist</b> about halfway up
      where every belt sits, and a hip that flares back to near the chest width.
    </p>

    <article class="plate">
      <div class="viewport diagram">{anatomy_svg()}
        <span class="vlabel">person &middot; anatomy</span>
        <span class="isnew">Shipped</span></div>
      <div class="plate-body">
        <h3>Anatomy <span class="mk">SHIPPED</span></h3>
        <p class="role">person.py &middot; person_figure.py</p>
        <p>
          The cinched waist and rounded shoulders are in
          <code class="f">gen_si.figure_parts</code> and baked to
          <code class="f">person_figure.py</code> by
          <code class="f">build_person_figure.py</code>. <b>Belts, sashes, hip
          pouches and torches moved up to the waist</b>; the arm is drawn with a
          rounded cap that tucks against the torso side (no armpit gap); a hip
          pouch draws <em>behind</em> the arm.
        </p>
        <dl class="spec">
          <dt>FIG_HIP_Y</dt><dd>146 &nbsp; (legs join here)</dd>
          <dt>FIG_FOOT_Y</dt><dd>194 &nbsp; (ankle line)</dd>
          <dt>waist_y</dt><dd>111 &nbsp; belt at 104</dd>
          <dd class="full">Collision / arrival-distance checks still read <code class="f">self.x</code>/<code class="f">self.y</code> (the ground point) &mdash; unchanged. No save impact: NPCs and outfits are rebuilt from story config on load, never stored.</dd>
        </dl>
        <div class="keys"><span><b>affects</b> player &middot; every NPC &middot; every AI pilot</span></div>
      </div>
    </article>

    <article class="plate">
      <div class="viewport diagram">{slotmap_svg()}
        <span class="vlabel">outfit &middot; accessory slot map</span></div>
      <div class="plate-body">
        <h3>Accessory slots</h3>
        <p class="role">graphics.json &rarr; outfits &middot; optional keys</p>
        <p>
          Every optional piece, switched on by naming its colour. An outfit is a
          <code class="f">suit_color</code> plus <code class="f">boot_color</code>
          plus any of these. <b>No new draw code per outfit</b> &mdash; just more
          colours in the JSON. The role details in the chapters below are the
          exception: they're new shapes that would need a <code class="f">figure_signature</code>
          table (see Wiring in).
        </p>
        <div class="keys">
          <span>helmet &middot; hat &middot; cap</span><span>visor</span><span>collar</span>
          <span>shoulder</span><span>chest_plate + rivets</span><span>sash</span>
          <span>belt + buckle</span><span>badge</span><span>backpack</span>
          <span>spike &middot; antenna</span><span>band</span><span>leg &middot; sleeve</span>
        </div>
      </div>
    </article>
  </section>
{chapters}

  <section class="wiring" id="wiring">
    <h2>Wiring in</h2>
    <div class="wiring-grid">
      <section><h4>The body &mdash; shipped</h4><p><code class="f">person.py</code> / <code class="f">person_figure.py</code>: legs, boots, walk cycle, and now the cinched waist + rounded shoulders + belts-at-the-waist, all baked from <code class="f">gen_si.figure_parts</code>. Re-run <code class="f">build_person_figure.py</code> after editing the atlas figure; don't hand-edit <code class="f">person_figure.py</code>.</p></section>
      <section><h4>Recolour-only outfits &mdash; buildable now</h4><p>Any outfit that only sets <code class="f">*_color</code> keys is a one-line <code class="f">graphics.json</code> entry. The existing <code class="f">space_suit</code> / <code class="f">flight_suit</code> / <code class="f">mechanic</code> / … already are.</p></section>
      <section><h4>Role detail &mdash; needs a figure renderer</h4><p>The tool belt, tabard, hood, mask, star, bandolier are <b>new geometry</b>. <code class="f">Person.draw</code> is colour-key driven, so these need a parts-style path &mdash; a <code class="f">figure_signature</code> table keyed by outfit id, fed the same way <code class="f">figure_parts</code> already produces data. That one addition lands every redraw here <em>and</em> the culture atlases' signature pieces.</p></section>
      <section><h4>The other atlases</h4><p><b>Sol Federation</b> (the <code class="f">standard_issue</code> hardware &mdash; ships, station, buildings, interior, Federation crew), <b>Vherathi Concord</b> and <b>Drossholt Company</b> (Resin &amp; Rivets, split in two). All four reference this body.</p></section>
    </div>
    <p class="lead" style="margin-top:30px">
      Companion atlases: <b>Sol Federation</b>, <b>Vherathi Concord</b>,
      <b>Drossholt Company</b>, and <b>Past the Reach</b> (seven proposed
      cultures). Same visual system, same strokeless rule, same
      <code class="f">figure_parts</code> body.
    </p>
  </section>
</main>
<footer><div class="wrap">Common Kit &middot; shared body &amp; culture-neutral outfits &middot; body shipped, redraws mockup &middot; default story</div></footer>
"""


if __name__ == "__main__":
    out = pathlib.Path("docs/atlases/common-kit.html")
    html = build()
    for bad in ('feGaussianBlur', 'backdrop-filter', 'background-attachment:fixed',
                'IntersectionObserver', 'stroke="', 'stroke-width', '<ellipse', '<line ',
                '<path ', '<rect ', '@keyframes'):
        assert bad not in html, f"forbidden construct: {bad}"
    out.write_text(html, encoding="utf-8")
    print("wrote", out, len(html), "bytes;", html.count("<svg"), "svgs")
