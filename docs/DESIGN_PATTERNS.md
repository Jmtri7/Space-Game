# Design Patterns & Reusable Solutions

The hub for proven patterns discovered during development. The working
principles below apply everywhere; each concrete pattern lives in one of five
cluster pages — open the one your work touches, not all five.

| Cluster | Patterns |
|---|---|
| [patterns/rendering.md](patterns/rendering.md) | Coordinate Conversion · 2D Rotation with Matrix · Y-Sorted Draw Order · Drop-In Draw Wrapper · HUD Zone Width Discipline |
| [patterns/movement.md](patterns/movement.md) | Thrust & Momentum · Fixed-Timestep Accumulator · Always-On Metrics · Walkability-Oracle Navigation · One Movement Primitive |
| [patterns/entities.md](patterns/entities.md) | Base Class for Reusable Entity Logic · Compose Don't Inherit · Role → Routine Registry |
| [patterns/ui-screens.md](patterns/ui-screens.md) | Scrollable Menu List · Scrollable List Handler · 2D Grid Sibling · Screen State Machine · Config-Driven Screen Dispatch · Menu vs. Dialog |
| [patterns/persistence.md](patterns/persistence.md) | State Persistence (get_state/restore_state) · Data-Driven Configuration |

## Working Principles

### Cross-Cutting Concerns: Handle at the Source

When a behavior needs to apply everywhere (window close, event filtering,
startup logic), handle it **once** in the main loop or a base class, not
repeated in every subclass.

- **Benefit:** new screens inherit correct behavior by default; nobody has to
  remember to add it.
- **Example:** `pygame.QUIT` is handled in the main event loop, so any new
  screen works without modification.
- **Anti-pattern:** duplicated QUIT checks in ten different screen classes.

### Generalization Strategy

When you notice the same pattern appearing in multiple places:

1. **Extract to a helper function** if it's utility code
   (`_handle_scrolling_input()`).
2. **Move to a base class** if it's core to the entity type (`get_state()` on
   `ScreenBase`).
3. **Handle centrally** if it's a cross-cutting concern (QUIT in the main loop).
4. **Document it** in the matching cluster page if it's a reusable principle
   other parts of the game should follow — see "Contributing Patterns" below.

When implementing a feature or fix, watch for a clever solution other code
could reuse, or repeated logic that wants extracting, and raise it.

## Contributing Patterns

When you discover a reusable solution:

1. **Recognize the pattern:** Notice repeated code or design that could generalize
2. **Name it:** Pick a short, descriptive name (e.g., "Coordinate Conversion")
3. **Document it** in the cluster page it belongs to (rendering / movement /
   entities / ui-screens / persistence — add a new cluster page only if it fits
   none), with:
   - Problem (what issue it solves)
   - Solution (how to implement)
   - Implementation (code example)
   - Why this works (explanation)
   - Use case (when to apply it)
4. **Register it** in the routing table at the top of this hub.
5. **Link from relevant docs:** Update other docs (ARCHITECTURE.md, etc.) to reference the pattern

**Example:**
When fixing a bug or implementing a feature, if you notice:
- Code being repeated in multiple classes
- A general solution that other code might need
- A design decision that took thought and worked well

...document it as a pattern so future code can reuse the solution.
