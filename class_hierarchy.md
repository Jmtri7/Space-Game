# Class Hierarchy & Composition in Space Game

## Inheritance Hierarchies

### Ship Classes (ship.py)
```
Ship (base physics + autopilot)
├── PlayerController (composes Ship, handles input)
└── AIShip (autonomous behavior)
```

### Screen Classes (screens.py)
```
ScreenBase (base for all screens)
├── WalkableArea (explorable areas with camera)
│   └── Location (interior base class)
│       └── StationInterior (space station interiors)
└── GameScreen (main space exploration)

Independent Screens:
├── Menu (main menu)
├── StorySelector (story selection)
├── PilotNameDialog (name entry)
├── LocationSelector (moon location choice)
├── PauseMenu (pause menu)
├── SaveDialog (save management)
├── LoadMenu (load management)
└── ConfirmDialog (base confirmation dialog)
    ├── DeleteConfirmDialog
    └── OverwriteConfirmDialog
```

### Entity Classes (objects.py)
```
Person (base character)
└── NPC (interactive character, composes Dialogue)

Independent Classes:
├── SpaceStation (rotating station)
├── Moon (celestial body)
├── StarField (background stars)
└── Dialogue (conversation system)
```

## Composition Relationships

### GameScreen Composes:
- `PlayerController` → owns `Ship`
- `StarField` (background stars)
- `SpaceStation` (station object)
- `Moon` (moon object)
- `List<AIShip>` (multiple AI ships)
- `Dialogue` objects (through NPCs)

### PlayerController Composes:
- `Ship` (the player's ship with physics)

### StationInterior Composes:
- `List<NPC>` (interior NPCs)
- `Dialogue` objects (for NPC conversations)

### NPC Composes:
- `Dialogue` (conversation options)

### SpaceStation Composes:
- Graphics config (size, color, rotation_speed, shape points)

### Moon Composes:
- Graphics config (size, color, crater definitions)

## Class Responsibilities

| Class | Type | Purpose |
|-------|------|---------|
| **Ship** | Base | Physics engine, autopilot, movement |
| **PlayerController** | Wrapper | Input handling for player ship |
| **AIShip** | Subclass | Autonomous wandering behavior |
| **ScreenBase** | Base | Screen interface definition |
| **WalkableArea** | Base | Camera system, walkable mechanics |
| **Location** | Base | Interior locations (shared logic) |
| **GameScreen** | Screen | Space exploration & management |
| **StationInterior** | Screen | Station interior exploration |
| **Menu** | Screen | Main menu with options |
| **StorySelector** | Screen | Story/campaign selection |
| **SaveDialog** | Screen | Save file management UI |
| **LoadMenu** | Screen | Load file management UI |
| **PauseMenu** | Screen | In-game pause menu |
| **Person** | Base | Character position & sprite |
| **NPC** | Subclass | Interactive NPCs with dialogue |
| **Dialogue** | System | Conversation tree management |
| **SpaceStation** | Entity | Rotating space station rendering |
| **Moon** | Entity | Celestial body with craters |
| **StarField** | System | Background star generation |

## Data Flow

```
main.py (game loop)
    ↓
current_screen.handle_input(events) ← user input
    ↓
current_screen.update() ← game logic
    ↓
current_screen.draw(surface) ← rendering
    ↓
pygame.display.flip() ← display update
```

## Key Design Patterns

### 1. **Composition over Inheritance** (Ship classes)
- PlayerController owns a Ship rather than extending it
- Allows separation of input handling from physics

### 2. **Base Class Pattern** (Screens, Persons)
- ScreenBase, WalkableArea, Location, Person
- Common interface for subclasses

### 3. **Strategy Pattern** (AI Ships)
- AIShip has different states (accelerate/brake)
- Autonomous decision-making logic

### 4. **Component Pattern** (Graphics)
- Graphics data passed to SpaceStation/Moon constructors
- Reusable across stories via config

### 5. **Game Loop Pattern**
- handle_input() → update() → draw() cycle
- Consistent across all screen types

## Dependency Flow

```
main.py
├── constants.py (game configuration)
├── utils.py (rendering & file I/O)
├── ship.py
│   ├── constants.py
│   └── utils.py
├── objects.py
│   ├── constants.py
│   └── utils.py
├── screens.py
│   ├── constants.py
│   ├── utils.py
│   ├── ship.py (PlayerController, AIShip)
│   └── objects.py (all world objects)
└── pygame (rendering library)
```

## Class Ownership Tree

```
main.py
└── current_screen (one of):
    ├── GameScreen
    │   ├── PlayerController
    │   │   └── Ship
    │   ├── StarField
    │   ├── SpaceStation
    │   ├── Moon
    │   └── List<AIShip>
    ├── StationInterior
    │   ├── List<NPC>
    │   │   └── Dialogue
    │   └── SpaceStation
    ├── MoonCity / MoonOutdoor
    │   └── List<NPC>
    │       └── Dialogue
    ├── Menu
    ├── SaveDialog
    ├── LoadMenu
    ├── PauseMenu
    └── ... (other screens)
```

## Total Class Count: 22 Classes

**By File:**
- ship.py: 3 classes
- objects.py: 6 classes
- screens.py: 13 classes

**By Type:**
- Base classes: 5 (ScreenBase, WalkableArea, Location, Person, ConfirmDialog)
- Subclasses: 6 (AIShip, StationInterior, NPC, DeleteConfirmDialog, OverwriteConfirmDialog, + GameScreen, LocationSelector, etc.)
- Independent: 11

