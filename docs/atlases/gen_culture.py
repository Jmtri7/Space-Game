"""Build a full per-culture frontier atlas.

    python docs/atlases/gen_culture.py             # all built kits
    python docs/atlases/gen_culture.py kaethar     # just one

Culture meta (name / palette / rubric / prose) lives in CULTURES below; the
drawn content lives in `<key>_kit.py` (SHIPS / STATION / BUILDINGS / FURNITURE
/ OUTFITS / LAYOUTS). Output: `docs/atlases/<key>.html`.
"""
import importlib
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from culture_common import build_page, FORBIDDEN

# key -> (module name, output html basename)
KITS = {
    "deeprock": ("deeprock_kit", "deeprock-consortium"),
    "kessari": ("kessari_kit", "ashfall-rite"),
    "meridian": ("meridian_kit", "meridian-free-ports"),
    "theln": ("theln_kit", "theln-drift"),
    "kaethar": ("kaethar_kit", "kaethar-directorate"),
    "vetl": ("vetl_kit", "the-vetl"),
    "salt_crows": ("salt_crows_kit", "salt-crows"),
}

CULTURES = {
 "kaethar": dict(
   key="kaethar", name="Kaethar Directorate", tab="Kaethar",
   mark="Kaethar <em>Directorate</em>",
   accent="#d6402c", accent_rgb="214,64,44",
   tagline="Correct, and <em>armed</em>",
   pal=dict(hull="#3a3f47", hull_lo="#282c33", glass="#cfd6de", thrust="#9fc0d8",
            trim="#d6402c", shadow="#191c21"),
   dek="A cold, hierarchical military power that garrisons the lanes and expects "
       "its transponder logs read back to it. Hard angles, gunmetal, one warning "
       "colour and nothing else &mdash; from the warships down to the mess-hall bench.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span> for a proposed eighth "
          "culture. The ships are strokeless and extractable; the outfit signatures "
          "would bake through <code class=\"f\">build_figure_signatures.py</code> like "
          "the shipped cultures'.",
   rubric=[
     ("Arrowhead and rail.", "A sharp narrow nose widening to a blocky midbody, a raised spinal rail its full length to a muzzle at the tip. Every corner a hard angle &mdash; no fillet, no curve, anywhere."),
     ("Forward-swept everything.", "Wing pylons, turret nacelles, antenna masts sweep <em>forward</em>, toward the target, not back. Blocky hardpoint pods."),
     ("One warning colour.", "Sharp red chevrons along every leading edge, a hard diamond unit sigil, red rank and sensor bars. The hull stays flat gunmetal &mdash; recessed panel seams and nothing else."),
     ("Rank and file inside.", "A straight spine, identical cells, a painted line you walk between. The Standard Issue plan with the warmth removed."),
   ],
   ship="A stern angular warship: a hard arrowhead hull with recessed panel seams, "
        "forward-swept wing pylons with hardpoint pods and red chevron trim, a "
        "full-length raised spinal rail with a nose muzzle, two shoulder turret "
        "nacelles with stub barrels, a hard diamond unit sigil, an inline "
        "quad-thruster block.",
   station="A cross-plan fortress ring: a square gunmetal core with four forward-swept "
           "docking spurs, red chevron trim on every spur edge, a spinal-rail comms "
           "mast, and a hard-edged hangar mouth. No curve on the whole structure.",
   ships_lead="A picket, a line cruiser and a heavy siege carrier &mdash; the nose "
              "angle and the spinal rail carry across all three.",
   buildings_lead="Bunkers and blockhouses: flat gunmetal masses, recessed seams, "
                  "red chevron at every doorway and vent, a unit sigil over the entrance.",
   furniture_lead="Issue furniture stripped to the frame &mdash; a bolted bench, a "
                  "muster post, a rack, a floor-set sigil marker. Nothing upholstered.",
   outfits_lead="Line crew to fleet command on one silhouette: the angular red-barred "
                "helm and the hard unit sigil recur; rank shows only in the sleeve bars "
                "and the coat length.",
   signature_line="an angular full helm with a horizontal red sensor bar and a peaked crest",
   routine_line="Kaethar wants a patrol / picket routine &mdash; hold a lane, "
                "challenge every transponder, escalate on a bad reply.",
 ),
 "vetl": dict(
   key="vetl", name="The Vetl", tab="Vetl", mark="The <em>Vetl</em>",
   accent="#7ce0c4", accent_rgb="124,224,196",
   tagline="Grown, not <em>built</em>",
   pal=dict(hull="#6b4a35", hull_lo="#4a3122", glass="#7ce0c4", thrust="#ffb060",
            trim="#e6ddc8", shadow="#2c1d14"),
   dek="A shamanistic people whose ships read as sea-creatures &mdash; broad, "
       "boneless, whip-tailed &mdash; and whose crews wear antler, hide and bead. "
       "Spirit-teal light where another culture would bolt on a running lamp.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span> for a proposed culture. "
          "The soft tail glow and the bone-white rib-veins would ship as solid "
          "tinted shapes until an additive layer exists.",
   rubric=[
     ("A creature silhouette.", "A broad flat manta body &mdash; a smooth wide lens, widest at mid, tapering both ways &mdash; with forward cephalic horn-prongs and a long tapering whip tail ending in a barb. No panel lines; it isn't panelled."),
     ("Bone and hide.", "A fan of pale rib-veins from the spine to the wing edge, a dorsal ridge of small spines, mottled darker hide patches for texture."),
     ("Spirit light.", "A constellation of teal motes on the back joined by thin lines, two large bio eye-spots near the nose. The exhaust is a soft glow at the tail, not a nozzle."),
     ("Worn, not issued.", "Crew wear antler headdresses, layered hide with a feathered hem, bead-strand necklaces, face paint, and carry a bound staff. No two identical."),
   ],
   ship="A manta creature-ship: a broad flat lens body with mottled hide texture, "
        "forward-sweeping cephalic horn-prongs, a long barbed whip tail, a fan of "
        "bone rib-veins, a dorsal spine ridge, a spirit-glow constellation and two "
        "bio eye-spots, exhaust as a soft tail glow.",
   station="A living reef-node: a rounded hide-brown shell grown in overlapping "
           "plates, teal spirit-motes strung across it, three soft berthing lobes "
           "instead of hard spurs, a bone-white rib arch over the mouth.",
   ships_lead="A scout, the manta itself, and a broad gather-ship &mdash; the lens "
              "body, the horn-prongs and the whip tail carry across all three.",
   buildings_lead="Grown mounds, not built blocks: rounded hide-brown shells with "
                  "bone-rib arches, spirit-mote strings, a woven-frame doorway.",
   furniture_lead="Hide mats, a bound-staff rack, a bead curtain, a spirit-fire "
                  "bowl &mdash; personal, hand-made, teal-lit.",
   outfits_lead="Scout to elder on one figure: the antler headdress and the "
                "spirit-mote motif recur; rank shows in the antler spread and the "
                "number of bead strands.",
   signature_line="a branching antler headdress and a drift of spirit-teal motes",
   routine_line="The Vetl want an explorer / wander routine &mdash; drift the deep "
                "field, never make port for long.",
 ),
 "salt_crows": dict(
   key="salt_crows", name="The Salt Crows", tab="Salt Crows",
   mark="The Salt <em>Crows</em>",
   accent="#ffd24a", accent_rgb="255,210,74",
   tagline="Cut from three <em>other</em> ships",
   pal=dict(hull="#7a3b2c", hull_lo="#4a241b", glass="#ffd24a", thrust="#ff7a2a",
            trim="#c98a3c", shadow="#1c110c"),
   dek="Scavengers and raiders. Nothing they fly or wear was built as a whole &mdash; "
       "it's rust, tar and scavenged brass, with a ram on the front and a crow "
       "daubed on the side.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span> for a proposed culture. "
          "The scavenged wings keep their donor cultures' colours on purpose &mdash; "
          "the raider reads as three ships bolted together.",
   rubric=[
     ("Asymmetric and kinked.", "A bent spine, wider to one side, a heavy pointed ram prow with reinforcement plates. Deliberately lopsided &mdash; nothing mirrors."),
     ("Three ships' worth of wings.", "Each wing scavenged from a different culture and bolted on crooked &mdash; a tapered Vherathi one, a riveted Drossholt box, a clean Federation panel &mdash; in their original colours."),
     ("Mismatched everything.", "Oversized bolted engine housings, one much bigger, both with visible bolt rings and patch plates. Rust streaks, brass patches, trophy trinkets on the rail."),
     ("The mark.", "A crude asymmetric bone-white crow glyph daubed on the hull. It's the only thing that's theirs."),
   ],
   ship="An asymmetric raider: a kinked rust hull wider to port, a plated ram prow, "
        "three mismatched scavenged wings in their original culture colours, two "
        "oversized bolted engine housings with bolt rings, a folded boarding gantry "
        "with a grapnel, trophy trinkets, and a daubed crow mark.",
   station="A lashed-together hulk: three scavenged hull sections roped at odd "
           "angles around an open core, mismatched dock arms, brass patches, a "
           "trophy line of running lights, one big crow daubed across the front.",
   ships_lead="A cutter, the raider, and a hulking breacher &mdash; all lopsided, "
              "all wearing other cultures' parts, all marked with the crow.",
   buildings_lead="Shacks welded from hull plate: mismatched panels, tar seams, a "
                  "brass-patched door, the crow mark on every one.",
   furniture_lead="A barrel table, a rope hammock, a loot rack, a scrap brazier "
                  "&mdash; nothing bought, everything found.",
   outfits_lead="Deck hand to captain on one figure: the headwrap, the salvaged "
                "monocle-visor and the daubed crow mark recur; a captain just has "
                "more brass and more trophies.",
   signature_line="a tied headwrap, a salvaged monocle-visor over one eye, and the "
                  "crow mark stencilled on the chest",
   routine_line="The Salt Crows want a raider routine &mdash; shadow a lane, close "
                "on a lone hull, hail once, then board.",
 ),
 "deeprock": dict(
   key="deeprock", name="Deeprock Mining Consortium", tab="Deeprock",
   mark="Deeprock <em>Consortium</em>",
   accent="#d6b03c", accent_rgb="214,176,60",
   tagline="Built around the <em>job</em>",
   pal=dict(hull="#5c524a", hull_lo="#413a34", glass="#ffe078", thrust="#ff9646",
            trim="#d6b03c", shadow="#332f2b"),
   dek="A working consortium of belt crews and ore haulers &mdash; already a faction "
       "in <code class=\"f\">pilots.json</code> with no look yet. Hardware built "
       "around the job it does, painted only where a warning is needed.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span>. Deeprock already exists "
          "as <code class=\"f\">mining_foreman</code> pilots &mdash; this gives the "
          "faction a silhouette.",
   rubric=[
     ("Front-heavy, functional.", "One dominant forward volume &mdash; a crusher jaw or ore scoop &mdash; a fat segmented tank body behind it, ancillary boxes clamped on wherever they cleared the load. Never tidy."),
     ("Almost no windows.", "Light is a few harsh floodlamps clustered at the working end. The crew works by them, not by a view."),
     ("Hazard, not livery.", "Trim-yellow striping and chevrons edge every intake, hatch and thruster. Everything else stays bare, seamed, riveted."),
     ("Industrial plant that flies.", "Segment seams and rivet rows on every barrel, a conveyor ridge down the spine, blunt quad-thruster housings. It reads as machinery first."),
   ],
   ship="A short front-heavy hauler: an interlocking toothed rock-crusher jaw at the "
        "nose, three riveted tank-barrel segments, a rung conveyor ridge on the "
        "spine, an asymmetric ore chute, forward floodlamp masts, a chevron-striped "
        "quad-thruster block.",
   station="A processing platform: a stack of riveted ore-tank drums around a "
           "central conveyor spine, floodlamp masts, hazard-striped dock claws, an "
           "asymmetric tailings chute. Plant first, station second.",
   ships_lead="A prospector, the crusher-hauler, and a bulk ore barge &mdash; the "
              "front-heavy working volume and the segmented tanks carry across all three.",
   buildings_lead="Prefab plant: riveted drum silos, a girder headframe, a bolted "
                  "processing shed &mdash; hazard yellow at every opening.",
   furniture_lead="A pipe bench, a tool board, an ore-sample bin, a floodlamp stand "
                  "&mdash; all steel, all scuffed.",
   outfits_lead="Pit crew to consortium boss on one figure: the ear-defender hard "
                "hat and the shoulder floodlamp recur; a boss just has a cleaner "
                "coat and a tally board.",
   signature_line="a hard hat with side ear-defenders and a shoulder floodlamp "
                  "throwing a cone",
   routine_line="Deeprock wants a mining-loop routine &mdash; run out to a belt, "
                "work a rock, haul back to the platform.",
 ),
 "kessari": dict(
   key="kessari", name="The Ashfall Rite", tab="Kessari",
   mark="The Ashfall <em>Rite</em>",
   accent="#ff823c", accent_rgb="255,130,60",
   tagline="The ember in the <em>stone</em>",
   pal=dict(hull="#22201e", hull_lo="#33302c", glass="#ff823c", thrust="#dc4628",
            trim="#8a7a5c", shadow="#141216"),
   dek="A close order that keeps to the burnt worlds. Where the Vherathi grow their "
       "hulls and the Drossholt bolt theirs, the Kessari <b>fire</b> theirs &mdash; "
       "dark ceramic carved like a reliquary, lit only where the material is still cooling.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span> for a proposed culture. "
          "Near-black hull, ember-orange seam &mdash; the contrast is the whole look.",
   rubric=[
     ("One carved mass.", "A tall base-heavy monolith with stepped flying-buttress flanks, recessed relief grooves across the face, and a finial spire cluster at the nose. Roughly symmetric, one edge always left hand-irregular."),
     ("The ember seam.", "A bright ladder of ember light down the spine with cross-ribs, a radial rose-window aperture cluster near the nose, a matching glow through the exhaust. Everything else near-black."),
     ("Ceremonial fittings.", "The exhaust is an ornate perforated censer housing, not a nozzle; buttress edges carry an ash-grey trim line."),
     ("Cell, not cabin.", "Interiors stay narrow, dim, high-contrast: black floor and walls, one bright line of light down the centre of every room."),
   ],
   ship="A tall dark reliquary: a carved base-heavy monolith with three stepped "
        "flying-buttress flanks a side, an ember spine ladder with cross-ribs, a "
        "radial rose-window aperture cluster, a finial spire, and a perforated "
        "censer exhaust glowing through its holes.",
   station="A void-black reliquary station: a carved octagonal core with buttressed "
           "corners, an ember seam ring, rose-window aperture clusters, censer "
           "exhaust vents, and a single bright dock throat.",
   ships_lead="A pilgrim skiff, the reliquary, and a great ossuary barge &mdash; the "
              "carved monolith, the ember ladder and the finial spire carry across all three.",
   buildings_lead="Carved black shrines: base-heavy monoliths with buttress flanks, "
                  "ember-seam faces, a rose-window over each door.",
   furniture_lead="An ember brazier, a kneeling rail, a relic niche, an ash-strewn "
                  "floor mark &mdash; dim, carved, ember-lit.",
   outfits_lead="Novice to hierarch on one figure: the smooth ceramic ember-slit "
                "mask and the censer pendant recur; rank shows in the robe length "
                "and the number of ash bands.",
   signature_line="a smooth full ceramic face-mask with a single vertical ember "
                  "slit and no eyes",
   routine_line="The Kessari want a pilgrimage routine &mdash; slow circuits between "
                "burnt worlds, never hurrying, never trading.",
 ),
 "meridian": dict(
   key="meridian", name="The Meridian Free Ports", tab="Meridian",
   mark="Meridian <em>Free Ports</em>",
   accent="#e8ce96", accent_rgb="232,206,150",
   tagline="Seen <em>arriving</em>",
   pal=dict(hull="#96744a", hull_lo="#6a5030", glass="#ffeec8", thrust="#ffd282",
            trim="#e8ce96", shadow="#3a2c1c"),
   dek="A loose confederation of independent trading ports, rich and fond of showing "
       "it. Brass and cream, layered decks, swept sail-fins and lantern light &mdash; "
       "built to look good coming down the ramp.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span> for a proposed culture. "
          "Brass filigree and lantern rows &mdash; the most ornamented of the seven.",
   rubric=[
     ("A banded lantern hull.", "One long tapering hull divided into decks by brass bands, not stacked balls. Symmetric and centred &mdash; not the Vherathi organic asymmetry."),
     ("Ornament is the point.", "Brass filigree scrollwork framing the fore hull, a stylised sunburst figurehead prow, a crowning lantern finial &mdash; every edge trimmed."),
     ("Windows and lanterns on show.", "An arched row of warm windows per deck plus a lantern pair at each end &mdash; a Meridian captain wants to be seen."),
     ("Swept sail-fins.", "Two large decorative fins sweep well aft from mid-hull, scalloped along the trailing edge, brass-ribbed."),
   ],
   ship="A tall ornate galleon: a long tapering lantern hull banded into decks with "
        "brass trim and rivet seams, arched window rows with lantern pairs, "
        "filigree scrollwork on the fore hull, a sunburst figurehead prow, a "
        "crowning finial, and two scallop-edged sail-fins swept aft.",
   station="A trade-port ring: a brass-banded toroid hull with an arched window "
           "arcade, filigree scrollwork at the cardinal points, lantern finials, "
           "and a wide welcoming dock mouth framed by a sunburst.",
   ships_lead="A cutter-yacht, the argosy galleon, and a broad merchant carrack "
              "&mdash; the banded lantern hull and the swept sail-fins carry across all three.",
   buildings_lead="Show-front counting houses: brass-banded facades, arched "
                  "window arcades, filigree cornices, a lantern over every door.",
   furniture_lead="A brass-inlaid trade counter, a velvet settle, a standing "
                  "lantern, a display plinth &mdash; every piece dressed for the customer.",
   outfits_lead="Clerk to port-master on one figure: the brocade over-mantle, the "
                "gold frogging and the plumed cap recur; rank shows in the braid "
                "runs and the plume length.",
   signature_line="a brocade over-mantle with gold frogging and a long plumed cap",
   routine_line="Meridian wants a trader routine &mdash; run a circuit between "
                "ports, buy low, sell high, dock in style.",
 ),
 "theln": dict(
   key="theln", name="The Theln Drift", tab="Theln", mark="The Theln <em>Drift</em>",
   accent="#7fe8e8", accent_rgb="127,232,232",
   tagline="Never makes <em>port</em>",
   pal=dict(hull="#c8c0b0", hull_lo="#9a9384", glass="#7fe8e8", thrust="#6fd0d0",
            trim="#bfe6df", shadow="#2a3230"),
   dek="Nomads who never stay anywhere long. Ships are tensioned membrane on a light "
       "frame &mdash; translucent, kite-like, asymmetric &mdash; strung with running "
       "lights like rigging.",
   status="<b>Nothing here is in the game.</b> Every plate is a "
          "<span style=\"color:var(--accent)\">MOCKUP</span> for a proposed culture. "
          "The membrane sails are drawn semi-transparent; in the engine they'd ship "
          "as solid tinted shapes until a translucency layer exists.",
   rubric=[
     ("Membrane on frame.", "Sail panels stretched over a light exoskeleton of thin struts. Trailing edges ripple &mdash; never a straight cut, never a solid hull."),
     ("Asymmetric spars.", "Booms and struts of uneven length; one side always reaches further. A long tail boom trails aft with its own small fin."),
     ("Lights on the rigging.", "Running lights strung in lines along every spar and down the spine."),
     ("Sensory tendrils.", "Thin trailing lines off the nose, tipped with a light &mdash; part antenna, part streamer."),
   ],
   ship="A ragged moth-kite: a thin spine with four uneven struts carrying "
        "rippled-edge membrane sails, a long asymmetric tail boom and fin, running "
        "lights down every spar, three light-tipped sensory tendrils off the nose, "
        "a cockpit blister and two small accent pods.",
   station="A drifting rig: a slender frame ring hung with membrane panels, running "
           "lights strung along every spar, three trailing tail booms, tendril "
           "antennae, and a soft-lit berthing gap rather than a hard dock.",
   ships_lead="A skiff, the kite, and a broad barge-sail &mdash; the membrane-on-frame "
              "build and the trailing tail boom carry across all three.",
   buildings_lead="Tent-frames, not buildings: membrane stretched on strut arches, "
                  "running-light strands along every edge, a soft-lit doorway.",
   furniture_lead="A hammock sling, a folding strut stool, a light-strand curtain, "
                  "a low membrane table &mdash; everything packs flat.",
   outfits_lead="Rigger to drift-elder on one figure: the membrane cape on a Y-frame "
                "and the running-light strand recur; an elder's cape reaches further, "
                "like the ship's long side.",
   signature_line="a translucent membrane cape on a Y-frame of struts, strung with "
                  "running lights",
   routine_line="The Theln want a drift routine &mdash; slow wandering transits, "
                "rarely docking, following the field.",
 ),
}


def build_one(key):
    modname, basename = KITS[key]
    kit = importlib.import_module(modname)
    c = CULTURES[key]
    html = build_page(c, kit)
    for bad in FORBIDDEN:
        assert bad not in html, f"{key}: forbidden construct {bad!r}"
    out = pathlib.Path(f"docs/atlases/{basename}.html")
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out}  {len(html)} bytes; {html.count('<svg')} svgs")


if __name__ == "__main__":
    keys = sys.argv[1:] or [k for k in KITS if pathlib.Path(
        f"docs/atlases/{KITS[k][0]}.py").exists()]
    for k in keys:
        build_one(k)
