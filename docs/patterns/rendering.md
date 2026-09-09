# Patterns: Rendering & HUD

Coordinate conversion, rotation, draw order, the AA wrapper, and HUD zone
discipline. Hub + working principles: [DESIGN_PATTERNS.md](../DESIGN_PATTERNS.md).

---

## Pattern: Coordinate Conversion

**Problem:** Graphics deform on window resize, objects render at wrong positions.

**Solution:** Separate game-space and screen-space with explicit conversion functions.

**Implementation:**
```python
# Store all positions in game-space (800x600)
self.x, self.y = 400, 300

# Convert only when drawing
def to_screen(x, y):
    scale = get_scale()  # Aspect ratio preserving scale
    offset_x, offset_y = get_offset()  # Letterbox offset
    return (int(round(x * scale + offset_x)), int(round(y * scale + offset_y)))

# In draw()
pygame.draw.circle(surface, color, to_screen(self.x, self.y), radius)
```

**Why this works:**
- Physics operates in stable game-space
- All calculations use same coordinate system
- Resize just recalculates scale/offset
- No coordinate conversion errors

**Use case:** Any game with resizable window.

---

## Pattern: 2D Rotation with Matrix

**Problem:** Rotated polygons deform when using separate sin/cos per point.

**Solution:** Pre-compute cos/sin once, reuse for all vertices.

**Implementation:**
```python
rad = math.radians(angle)
cos_a = math.cos(rad)
sin_a = math.sin(rad)

points = []
for lx, ly in local_points:
    # 2D rotation matrix: [cos -sin] [x]
    #                     [sin  cos] [y]
    rotated_x = lx * cos_a - ly * sin_a
    rotated_y = lx * sin_a + ly * cos_a
    world_x = center_x + rotated_x
    world_y = center_y + rotated_y
    points.append((world_x, world_y))

pygame.draw.polygon(surface, color, points)
```

**Why this works:**
- All points use same rotation matrix (consistent)
- Trig functions computed once (performance)
- Polygon stays rigid under rotation

**Use case:** Any rotating sprite/polygon (ships, objects).

---

## Pattern: Y-Sorted Draw Order (Painter's Algorithm)

**Problem:** In a top-down view where some objects have real height (buildings,
structures) and others walk around among them (NPCs, the player), drawing them
in separate fixed layers (all structures, then all people) is wrong whenever
one has to occlude the other - a person "in front of" a tall structure should
draw on top of it, and one "behind" it should draw underneath, but a fixed
layer order can only ever pick one of those, globally, for every position.

**Solution:** Collect everything that has height into one list, each paired
with its own ground-level depth (typically a person's feet position, or a
structure's base/front edge - not its center or top), sort that list by
depth, and draw in that order every frame. Purely flat/ground-level things
(floor tiles, wall decals, room labels) don't need this - they never occlude
anyone and can stay in their own earlier, unsorted pass.

**Implementation:** (`LocationScreen.draw()`, `_structure_depth()`)
```python
def _structure_depth(self, structure):
    # ... return the structure's own base/front-edge y, not its top or center

def draw(self, surface):
    # flat/ground layers first (floor, wall decals) - never need sorting
    drawables = [(self._structure_depth(s), self._make_structure_drawer(s, scale)) for s in self.structures]
    drawables += [(character.person.y, character.person.draw) for character in self.npcs]
    drawables.append((self.player.y, self.player.draw))
    drawables.sort(key=lambda item: item[0])
    for _, draw_fn in drawables:
        draw_fn(surface)
```

**Why this works:**
- One sort replaces having to special-case every pairwise "is A in front of
  B?" relationship
- Depth key is just "how close to the camera" (larger y = closer, in a
  standard top-down screen-space y-axis) - the same idea `get_distance()`
  already uses for proximity checks, just applied to draw order instead
- Rebuilt fresh every frame from current positions, so it's automatically
  correct as things move - no manual re-layering needed

**Benefits:**
- Correct occlusion for any layout, without hand-authoring z-order per object
- New tall structure types (or new character types) just need a depth key,
  not a new fixed layer to slot into the right place by hand

**Use case:** Any 2D top-down scene mixing static tall scenery with moving
characters - the same idea generalizes to any renderer with a fixed camera
angle and objects of varying height (isometric games use exactly this,
usually called Y-sorting).

---

## Pattern: Drop-In Draw Wrapper (mode-dispatched primitives)

**Problem:** A rendering option (anti-aliasing, a debug tint, a colour-blind
remap) needs to change *how* shapes are drawn at dozens of scattered call
sites. Threading a flag through every `draw()` signature, or branching on it
at each site, spreads the same `if` everywhere and makes the "off" path pay
for a feature nobody enabled.

**Solution:** A tiny module whose functions mirror the `pygame.draw`
primitives you actually use (`polygon(surface, color, points, width=0)`,
`circle(...)`) one-for-one — same argument order, same defaults — so adopting
it at a call site is a pure rename (`pygame.draw.polygon` → `aa.polygon`). The
mode check lives *once*, inside the wrapper; when the feature is off the
wrapper is a straight pass-through to `pygame.draw`. Always end with a
`pygame.draw` fallback so a call site can adopt the wrapper unconditionally
even for inputs the fancy path can't handle.

**Implementation** (`game/aa_draw.py`, dispatched on `constants.AA_MODE`):
```python
def polygon(surface, color, points, width=0):
    if _gfx_active() and len(points) >= 3:
        ipts = [(round(x), round(y)) for x, y in points]
        if _fits(...):                       # gfxdraw's int16 range
            try:
                col = _color(color)
                if width:
                    pygame.draw.polygon(surface, color, points, width)
                else:
                    pygame.gfxdraw.filled_polygon(surface, ipts, col)
                pygame.gfxdraw.aapolygon(surface, ipts, col)   # the smoothed edge
                return
            except _GFX_ERRORS:
                pass
    pygame.draw.polygon(surface, color, points, width)          # fallback / "off"
```
Call sites just swap the primitive: `world_object.draw_parts`,
`Ship._draw_windows`, `LandingSite._draw_station`, `Person._emit`,
`LocationScreen`'s building/decoration drawers, … Only the world/asset layer
opts in; menus and the HUD keep calling `pygame.draw` directly, so the mode
scopes itself without a single conditional at those sites.

**Why this works:**
- The "off" cost is one attribute compare per primitive — no measurable
  regression, so the wrapper can be adopted broadly without a perf argument.
- New modes (a third AA method, a debug outline) are added in one file; no
  call site changes.
- The unconditional fallback means "route this site through the wrapper" is
  never a risk decision — worst case it draws exactly as before.

**Watch out for:** keep the wrapper's signature a strict superset of the
primitive it replaces (so the rename is mechanical), and capture any
exception classes you catch (`pygame.error`) at import so a mocked-out
`pygame` in tests can't turn the `except` tuple into a `TypeError`.

**Use case:** Any cross-cutting change to low-level drawing that would
otherwise be a flag threaded through the whole render tree.

---

## Pattern: HUD Zone Width Discipline

**Problem:** A HUD panel that sizes itself purely from its own content
(`draw_status_pane`, `draw_info_panel`, the bottom-left Messages log, a
top-center banner) can grow arbitrarily wide once that content is free-form
text - a long status sentence, an NPC's one-way hail message, a story
config's interior label. `get_ui_scale()` doesn't prevent this either: it's
`min(width/800, height/600)`, so a wide-but-short window is scaled by
*height*, not width - text renders proportionally larger than the window is
wide, and a panel that was comfortably narrow at a normal aspect ratio can
overflow into a neighboring panel's space at an unusual one (a real bug: a
long "drifting from the system" status line overlapping the Messages pane
at the bottom-left on a 1859x1024 window).

**Solution:** Divide the HUD horizontally into three zones - a left
quarter, a right quarter, and a center band - and give every panel a hard
cap matching whichever zone it's anchored to, derived from the *real*
window width rather than `ui_scale`. Edge-anchored panes take a *fixed*
`side_panel_width()` (the quarter minus the shared `hud_margin()`), so they
all line up on the quarter line rather than each shrinking to its own
content. Centered panes (status pane, the top-centre popup stack, modal
menu panels via `modal_panel_rect()`) cap at `center_panel_max_width()`,
which is `screen//2 - 2*hud_margin()` - so at max width a centred pane
still leaves a full `hud_margin()` gap before the quarter line, the same
gap the side panes leave from the screen edge. Nothing centred can touch a
side pane. Any free-form text wraps (`_wrap_text`) to fit its zone.

**Implementation:** (`game/ui/ui_theme.py`)
```python
def side_panel_max_width():
    return utils.screen_width // 4

def hud_margin(ui_scale):
    return int(HUD_MARGIN_BASE * ui_scale)

# Edge-anchored: fill the quarter from the edge margin to the quarter line.
def side_panel_width(ui_scale):
    return max(1, side_panel_max_width() - hud_margin(ui_scale))

# Centred: a full margin's gap from the quarter line on each side.
def center_panel_max_width(ui_scale):
    return max(1, utils.screen_width // 2 - 2 * hud_margin(ui_scale))

# Modal menu panels re-centre on the real screen and cap at the centre band.
def modal_panel_rect(ui_scale, y_frac, w_frac, h_frac):
    width = min(int(800 * ui_scale * w_frac), center_panel_max_width(ui_scale))
    ...

def draw_controls_pane(surface, x, y, title, items, ui_scale):
    ...
    panel_width = side_panel_width(ui_scale)   # not "shrink to content"
```

**Why this works:**
- One pair of functions defines what "side" and "center" mean in pixels;
  every panel - `draw_status_pane`, `draw_info_panel`, `draw_message_log`,
  `draw_controls_pane`, `draw_glow_message`, `SpaceScreen._draw_minimap` -
  reads from the same two numbers, so the zones can never drift out of
  sync with each other the way five independently-tuned pixel budgets
  would.
- Every edge-anchored pane is a fixed `side_panel_width()` (the quarter
  minus the shared `hud_margin()`), not sized to its own content, so the
  Controls / info / Messages / minimap panes all share one vertical edge on
  the quarter line instead of each stopping at a different ragged width.
- The bottom-left Message Log and the top-right info/targeting pane both
  additionally have a fixed *height* cap (`MESSAGE_LOG_VISIBLE_LINES` /
  `INFO_PANEL_VISIBLE_LINES`) and mouse-wheel scrolling for the overflow
  (`SpaceScreen.message_log_scroll` / `info_panel_scroll`, wheel routed to
  whichever pane the cursor is over), with blue `^`/`v` `(scroll)` hints -
  so neither can grow into the pane above/below it.
- The top-centre transient popups (hail banner, "too close to jump"
  warning, mission/jump toast) render as a downward stack of individual
  `draw_glow_message` panes, so two showing at once never overlap.
- Derived from `utils.screen_width` directly (not `ui_scale`), so the cap
  tracks the window's actual shape instead of a scale factor that can grow
  disproportionately to width on an unusual aspect ratio.
- Shared functions mean `LocationScreen`'s HUD (which reuses
  `draw_controls_pane`/`draw_status_pane`/`draw_info_panel`) gets the same
  discipline for free, without its own screen needing to know the rule
  exists.

**Use case:** Any HUD panel anchored to a screen edge or the horizontal
center, especially one whose content can include story/dialogue text
rather than only fixed, short UI labels.
