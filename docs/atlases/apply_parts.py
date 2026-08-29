"""Extract each detailed asset's shapes from the atlases and inject them as
compact `parts` (and, for ships, `local_points`) fields into the config
JSON - targeted text edits, so nothing else in the file is reformatted.

Run from repo root:  python docs/atlases/apply_parts.py
(reads the .html beside this file; writes config/stories/default/*.json)
"""
import subprocess, sys, os, json, re

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.getcwd()
RR = os.path.join(HERE, "resin-and-rivets.html")
SI = os.path.join(HERE, "standard-issue.html")
EX = os.path.join(HERE, "extract_atlas.py")

B = "config/stories/default/building_types.json"
G = "config/stories/default/graphics.json"

# key, atlas, needle, cx, cy, scale, flipy, mode, dest
T = [
    ("vherathi_dock_antler", RR, "dock-antler", 120, 184, 1.1, 0, "parts", B),
    ("vherathi_vein_arch",   RR, "vein-arch",   120, 182, 1.0, 0, "parts", B),
    ("drossholt_gantry_rig", RR, "gantry-rig",  120, 178, 1.2, 0, "parts", B),
    ("drossholt_pipe_rail",  RR, "pipe-rail",   120, 146, 1.0, 0, "parts", B),
    ("station_alpha", RR, "station-alpha", 121, 108, 0.44, 0, "hull", G),
    ("station_delta", RR, "station-delta", 120, 100, 0.36, 0, "hull", G),
    ("station_ring",  SI, "standard ring", 120, 100, 0.42, 0, "hull", G),
    ("vherathi_courier", RR, "spinewing", 120, 100, 0.0125, 0, "hull", G),
    ("vherathi_tender",  RR, "chorus-tender", 120, 100, 0.0125, 0, "hull", G),
    ("vherathi_ark",     RR, "pale-ark", 120, 105, 0.0110, 0, "hull", G),
    ("vherathi_skiff",   RR, "resin-skiff", 120, 100, 0.0125, 0, "hull", G),
    ("vherathi_reliquary", RR, "reliquary-hauler", 120, 100, 0.0120, 0, "hull", G),
    ("vherathi_thornwing", RR, "thornwing", 120, 100, 0.0125, 0, "hull", G),
    ("drossholt_freighter", RR, "drossholt-hauler", 120, 100, 0.0120, 0, "hull", G),
    ("drossholt_patrol", RR, "drossholt-cutter", 120, 100, 0.0125, 0, "hull", G),
    ("drossholt_tug",    RR, "sledge-tug", 120, 100, 0.0125, 0, "hull", G),
    ("drossholt_miner",  RR, "ratchet-prospector", 120, 100, 0.0115, 0, "hull", G),
    ("drossholt_gunship", RR, "bulwark-gunship", 120, 102, 0.0125, 0, "hull", G),
    ("issue_shuttle", SI, "issue shuttle · top", 100, 100, 0.0130, 0, "hull", G),
    ("issue_lighter", SI, "issue lighter", 100, 100, 0.0115, 0, "hull", G),
    ("issue_cutter",  SI, "issue cutter", 100, 100, 0.0130, 0, "hull", G),
    ("issue_tender",  SI, "issue tender", 100, 108, 0.0130, 0, "hull", G),
]


def run(atlas, needle, cx, cy, scale, flipy, mode):
    r = subprocess.run([sys.executable, EX, atlas, needle, str(cx), str(cy),
                        str(scale), str(flipy), mode], capture_output=True, text=True)
    if r.returncode:
        print("  ! ", (r.stderr.strip().splitlines() or ["?"])[-1])
        return None
    return json.loads(r.stdout.strip().splitlines()[0])


def block_span(text, key):
    m = re.search(r'\n(\s*)"' + re.escape(key) + r'"\s*:\s*\{', text)
    if not m:
        return None
    i = m.end() - 1
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return m.start() + 1, m.end(), j, m.group(1)
    return None


def inject(text, key, fields):
    span = block_span(text, key)
    if not span:
        print(f"  ! {key} not found")
        return text
    _, open_end, close_i, indent = span
    field_indent = indent + "  "
    body = text[open_end:close_i]
    # remove any existing copy of the target fields (single-line values,
    # arrays nested up to 3 deep, or a flat object)
    arr = r'\[(?:[^\[\]]|\[(?:[^\[\]]|\[[^\[\]]*\])*\])*\]'
    for fk in fields:
        body = re.sub(r'\n[^\n]*"' + re.escape(fk) + r'"\s*:\s*(?:' + arr + r'|\{[^{}]*\}),?(?=\s*\n)', "", body)
    new_fields = "".join(
        f'\n{field_indent}"{k}": {json.dumps(v, separators=(", ", ": "))},'
        for k, v in fields.items())
    return text[:open_end] + new_fields + body + text[close_i:]


for dest in {t[8] for t in T}:
    path = os.path.join(REPO, dest)
    text = open(path, encoding="utf-8").read()
    for key, atlas, needle, cx, cy, scale, flipy, mode, d in T:
        if d != dest:
            continue
        data = run(atlas, needle, cx, cy, scale, flipy, mode)
        if data is None:
            continue
        fields = {}
        if mode == "hull":
            fields["local_points"] = data["local_points"]
        if mode in ("hull", "nohull"):
            fields["parts"] = data["parts"]
            if data.get("outline_color"):
                fields["outline_color"] = data["outline_color"]
            print(f"  {key}: {mode} {len(data.get('local_points', []))}pts + "
                  f"{len(data['parts'])} parts outline={data.get('outline_color')}")
        else:
            fields["parts"] = data
            print(f"  {key}: {len(data)} parts")
        text = inject(text, key, fields)
    json.loads(text)  # validate
    open(path, "w", encoding="utf-8").write(text)
    print(f"wrote {dest}")
