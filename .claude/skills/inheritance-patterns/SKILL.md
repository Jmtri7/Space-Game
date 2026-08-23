---
name: inheritance-patterns
description: Use template method pattern and inheritance to consolidate duplicated behavior across classes
---

# Inheritance-Based Pattern Consolidation

Refactoring pattern for eliminating code duplication by moving common behavior into base classes using the **Template Method Pattern**.

## When to Use

- Multiple classes have identical methods (e.g., `_cycle_target()`, `handle_input()`)
- Classes share the same algorithm structure but differ in implementation details
- You're duplicating control flow (e.g., "if key is L, do X; if key is T, do Y")
- Cross-cutting concerns appear in multiple places (e.g., drawing entrance markers, handling exit logic)

## The Pattern

**Base Class (Template):**
- Define the overall algorithm/structure
- Mark variable parts as abstract methods
- Provide helper methods for common operations
- Let subclasses fill in the details

**Subclass (Implementation):**
- Override abstract methods with specific behavior
- Reuse helper methods from base class
- Only implement what's different

## Example from Space Game

**Before (Duplication):**
```python
# StationInterior
def _cycle_target(self):
    if not self.npcs: return
    if self.current_target is None:
        self.current_target = 0
    else:
        self.current_target = (self.current_target + 1) % len(self.npcs)

# MoonCity
def _cycle_target(self):  # Identical code
    if not self.npcs: return
    if self.current_target is None:
        self.current_target = 0
    else:
        self.current_target = (self.current_target + 1) % len(self.npcs)
```

**After (Template Method):**
```python
# ScreenBase (template)
def _cycle_target(self):
    targetable = self._get_targetable_list()
    if not targetable: return
    if self.current_target is None:
        self.current_target = 0
    else:
        self.current_target = (self.current_target + 1) % len(targetable)

def _get_targetable_list(self):
    """Override in subclass"""
    return []

# StationInterior (implementation)
def _get_targetable_list(self):
    return self.npcs

# MoonCity (implementation)
def _get_targetable_list(self):
    return self.npcs
```

## Refactoring Steps

1. **Identify Duplication**
   - Find identical or nearly-identical methods across classes
   - Look for repeated `if`/`elif` chains handling the same keys/events
   - Search for repeated drawing code (entrance markers, player rendering)

2. **Extract to Base Class**
   - Move the common method to the base class
   - Replace hardcoded values with calls to abstract methods
   - Create helper methods for reusable operations

3. **Define Extension Points**
   - Mark abstract methods that subclasses must implement
   - Document what data each subclass should provide

4. **Update Subclasses**
   - Remove duplicate methods
   - Implement only the abstract methods
   - Reuse helper methods instead of duplicating drawing/logic

5. **Test**
   - Verify each subclass still behaves identically
   - Ensure polymorphism works (calling base method gets right subclass behavior)

## Pattern Combinations

This pattern often appears alongside:

- **Strategy Pattern** - extracting behaviors into helper methods subclasses can reuse
- **Polymorphism** - base class calls virtual methods, subclasses provide implementations
- **DRY Principle** - single source of truth for control flow/algorithm
- **Inversion of Control** - base class calls subclass methods, not the other way around

## Common Mistakes

❌ **Over-abstraction** - making too many things abstract; if only one subclass uses it, keep it concrete

❌ **Breaking existing behavior** - refactoring changes how subclasses work; test thoroughly

❌ **Ignoring edge cases** - when consolidating, ensure all subclass variations are preserved

✅ **Incremental** - refactor one pattern at a time, test between steps

✅ **Name clearly** - abstract methods should describe *what* (e.g., `_get_targetable_list()`), not *how*

## Related Patterns

- **Template Method** - base class defines algorithm skeleton
- **Strategy** - algorithms as pluggable objects
- **Factory** - creating subclass instances
- **Decorator** - adding behavior dynamically
