"""Generate docs/atlases/common-kit.html - the shared Person body and the
culture-neutral civilian / service outfits from graphics.json, redrawn on the
current cinched-waist body with a role-distinguishing detail each.

Split out of Standard Issue (which keeps the Sol Federation hardware). Run
from the repo root:  python docs/atlases/gen_common.py
"""
import math
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from gen_si import figure_parts, poly, circ, bar, dashed_bar, GRID, fig_remap
from atlas_shell import css, DEFS, GRIDDEF
from common_kit import OUTFITS, DETAILS

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
 "mechanic": "helmet(lamp) · suit · boot · belt · +tool belt · knee pads",
 "dockworker": "helmet · suit · boot · chest_plate · +hi-vis tabard",
 "miner": "helmet · suit · boot · +lamp · backpack · drill",
 "security": "helmet · suit · boot · visor · +vest · baton",
 "station_command": "suit · boot · collar · shoulders · badge · +braid · cap",
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
    # the signature layers are authored against the pre-Grounded figure;
    # fig_remap puts them on the new body's anchor lines (see gen_si)
    with fig_remap():
        base, pre, post = fn()
    return (poly([(0, 0), (140, 0), (140, 210), (0, 210)], GRID)
            + pre + "".join(figure_parts(**base)) + post)


def _code(s):
    return re.sub(r"`([^`]+)`", r'<code class="f">\1</code>', s)


def outfit_card(key):
    _fn, name, role = OUTFITS[key]
    detail = _code(DETAILS.get(key, ""))
    return f"""<figure class="card">
      <svg viewBox="0 0 140 210" role="img" aria-label="Front view of the {name} on the shared body.">{GRIDDEF}{outfit_inner(key)}</svg>
      <figcaption><b>{name}</b><p class="role">{role}</p>
        <div class="keyline">{KEYLINES.get(key, "")}</div>
        <p class="detail" style="font-size:.72rem;line-height:1.55;margin:.55rem 0 0;opacity:.92">{detail}</p></figcaption>
    </figure>"""


def anatomy_svg():
    fig = "".join(figure_parts(suit="#565660", boot="#3f3f48", no_helmet=True, hipline=True))
    g = f'<g transform="translate(66,6) scale(1.0)">{fig}</g>'
    lab = ('<g fill="#8b97ab" font-family="IBM Plex Mono, monospace" font-size="7">'
           '<text x="6" y="46">almond eyes, tapered brow,</text>'
           '<text x="6" y="55">under-nose shadow, D-ears</text>'
           '<text x="6" y="96">narrow rounded shoulder,</text><text x="6" y="105">domed arm top</text>'
           '<text x="6" y="140">cinched waist —</text><text x="6" y="149">belts anchor here</text>'
           '<text x="196" y="150" text-anchor="end">hip flares back to</text>'
           '<text x="196" y="159" text-anchor="end">near the chest width</text>'
           '<text x="196" y="196" text-anchor="end">longer legs, two boots</text></g>')
    lines = (dashed_bar(58, 136, 118, 136, 0.8, ACCENT, dash=2.4, gap=2.2)
             + dashed_bar(118, 100, 150, 100, 0.8, ACCENT, dash=2.4, gap=2.2)
             + dashed_bar(122, 52, 150, 52, 0.8, ACCENT, dash=2.4, gap=2.2)
             + dashed_bar(126, 152, 150, 152, 0.8, ACCENT, dash=2.4, gap=2.2))
    return (f'<svg viewBox="0 0 240 210" role="img" aria-label="Labelled anatomy of the shared Person body: '
            f'a head with almond eyes, a fine tapered brow, a bridge-and-tip nose, two-part lips and low D-ears; '
            f'narrow rounded shoulders with a domed arm top connecting flush; a cinched waist where belts sit; '
            f'a hip that flares back to near the chest width; and longer legs on two boots.">{GRIDDEF}'
            f'<polygon points="0,0 240,0 240,210 0,210" fill="url(#grid)"/>{lines}{g}{lab}</svg>')


def slotmap_svg():
    fig = "".join(figure_parts(
        helmet="#3a3a44", suit="#55555f", leg="#3f3f48", boot="#333333",
        backpack="#3a3a44", spikes="#4a4a55", antenna="#4a4a55", collar="#6a6a75",
        shoulders="#6a6a75", chest="#63636e", sash="#75757f", badge="#8a8a94",
        belt="#4a4a54", buckle="#7a7a84", visor="#5a5a64"))
    g = f'<g transform="translate(66,6)">{fig}</g>'
    lab = ('<g fill="#8b97ab" font-family="IBM Plex Mono, monospace" font-size="6.5">'
           '<text x="6" y="20">antenna_color</text>'
           '<text x="6" y="34">helmet_color</text>'
           '<text x="6" y="58">spike_color</text>'
           '<text x="6" y="74">shoulder_color</text>'
           '<text x="6" y="98">chest_plate_color</text>'
           '<text x="234" y="44" text-anchor="end">visor_color</text>'
           '<text x="234" y="64" text-anchor="end">collar_color</text>'
           '<text x="234" y="80" text-anchor="end">badge_color</text>'
           '<text x="234" y="96" text-anchor="end">sash_color</text>'
           '<text x="234" y="112" text-anchor="end">belt_color / buckle</text>'
           '<text x="234" y="140" text-anchor="end">backpack_color (behind)</text></g>')
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
  <span class="tag-wip">Body &amp; outfit signatures shipped</span>
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
      <b>The body and the outfit redraws both ship.</b>
      The shared <code class="f">Person</code> now stands on two legs, walks
      (<code class="f">person.py</code>'s <code class="f">_leg_stance</code> /
      <code class="f">_arm_swing</code>), has a <b>cinched waist</b> with the
      belts moved up to it, <b>narrow rounded shoulders</b> with a domed arm
      top, and the Grounded <b>face kit</b> &mdash; almond eyes with an iris,
      a pupil and a catchlight under a lash line, a fine tapered brow, a nose
      built from a bridge shadow into a soft tip, two-part lips and low D-ears,
      over a head that carries the same one-direction side plane the limbs do.
      The whole body is now the Grounded study's, not an approximation of it:
      the head came down and up over a slimmer neck, the torso is shorter and
      higher, the legs run the lower 47% of the figure with thigh / knee /
      calf stops, the boot is a foot and the hand a tapered mitt, and every
      limb, the torso and the neck carry the same one-direction shade. The
      <b>hairstyles</b> and the <b>hard hat</b> come off the skull's own
      profile too &mdash; hair and helmet alike are the head's outline pushed
      out by a lift and closed by a hairline (see the Grounded Person study).
      All of it is ahead of <code class="f">person_figure.py</code> until
      <code class="f">build_person_figure.py</code> is re-run. The <em>role-detail</em> pieces
      below (tool belt, tabard, hood, mask) are baked by
      <code class="f">build_figure_signatures.py</code> into
      <code class="f">game/world/figure_signatures.py</code>, and
      <code class="f">Person.draw()</code> renders them from each outfit's
      <code class="f">"signature"</code> key.
    </div>
    <dl class="legend" id="read">
      <div><dt>Left &mdash; specimen</dt><dd>Front-view figure at a fixed height on void-black, so silhouettes and palettes compare directly.</dd></div>
      <div><dt>Shapes only</dt><dd>Every specimen is <code class="f">&lt;polygon&gt;</code> + <code class="f">&lt;circle&gt;</code>, no stroke &mdash; outline is a larger offset shape behind, curves are many-sided polygons.</dd></div>
      <div><dt>Body vs. detail</dt><dd>The recoloured base uses existing <code class="f">*_color</code> keys; the role detail is baked geometry emitted from the outfit's <code class="f">"signature"</code> key.</dd></div>
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
      where every belt sits, a hip that flares back to near the chest width, and
      <b>narrow rounded shoulders</b> the domed arm top connects flush to. The
      face carries the Grounded kit: almond eyes with an iris, a pupil and a
      catchlight under a lash line, a fine tapered brow, a bridge-and-tip nose
      and two-part lips, with low D-ears and a leaf of shade across the far
      cheek. A helmet no longer replaces it &mdash; the shell is drawn
      <em>over</em> a full-size head, so the face still reads under the brim.
    </p>

    <article class="plate">
      <div class="viewport diagram">{anatomy_svg()}
        <span class="vlabel">person &middot; anatomy</span>
        <span class="isnew">Shipped</span></div>
      <div class="plate-body">
        <h3>Anatomy <span class="mk">SHIPPED</span></h3>
        <p class="role">person.py &middot; person_figure.py</p>
        <p>
          The cinched waist, narrow rounded shoulders and the Grounded face kit
          (almond eyes, tapered brow, bridge-and-tip nose, two-part lips,
          low D-ears) are in
          <code class="f">gen_si.figure_parts</code> and baked to
          <code class="f">person_figure.py</code> by
          <code class="f">build_person_figure.py</code>. <b>Belts, sashes, hip
          pouches and torches moved up to the waist</b>; the arm is drawn with a
          domed cap that tucks under the torso's shoulder point (no armpit gap,
          nothing sticking out); a hip pouch draws <em>behind</em> the arm.
        </p>
        <dl class="spec">
          <dt>FIG_HIP_Y</dt><dd>139 &nbsp; (legs join here)</dd>
          <dt>FIG_FOOT_Y</dt><dd>194 &nbsp; (ankle line)</dd>
          <dt>waist_y</dt><dd>103 &nbsp; belt at 99</dd>
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
          exception: they're baked shapes emitted from the outfit's
          <code class="f">"signature"</code> key (see Wiring in).
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
      <section><h4>The body &mdash; shipped</h4><p><code class="f">person.py</code> / <code class="f">person_figure.py</code>: legs, boots, walk cycle, the cinched waist + belts-at-the-waist, and now the <b>Grounded pass</b> &mdash; narrow rounded shoulders with a domed arm top, oval eyes, a straight brow, an under-nose shadow and D-ears &mdash; all baked from <code class="f">gen_si.figure_parts</code>. Re-run <code class="f">build_person_figure.py</code> after editing the atlas figure; don't hand-edit <code class="f">person_figure.py</code>.</p></section>
      <section><h4>Recolour-only outfits</h4><p>Any outfit that only sets <code class="f">*_color</code> keys is a one-line <code class="f">graphics.json</code> entry. The existing <code class="f">space_suit</code> / <code class="f">flight_suit</code> / <code class="f">mechanic</code> / … already are.</p></section>
      <section><h4>Role detail &mdash; shipped</h4><p>The tool belt, tabard, hood, mask, star, bandolier are baked geometry. <code class="f">build_figure_signatures.py</code> turns each signature function into a part list in <code class="f">game/world/figure_signatures.py</code>; <code class="f">Person.draw</code> emits it behind / over the body when the outfit carries a <code class="f">"signature"</code> key. Same path for the culture atlases' signature pieces.</p></section>
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
<footer><div class="wrap">Common Kit &middot; shared body &amp; culture-neutral outfits &middot; body &amp; outfit signatures shipped &middot; default story</div></footer>
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
