# Among Us Clone - Repository Documentation

## Overview

An unofficial Python clone of the popular multiplayer social deduction game **Among Us**. Built using Pygame with support for LAN multiplayer (up to 5+ players) and experimental voice chat functionality. Game assets are ripped from the original game.

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.x | Core language |
| Pygame | 2.5.2 | Game engine, graphics, audio |
| pytmx | 3.32 | Tiled map (.tmx) loading |
| PyAudio | 0.2.14 | Voice chat (optional) |
| cx_Freeze | 6.15.16 | Executable packaging |
| Socket/Asyncore | stdlib | Multiplayer networking |

## Project Structure

```
Among-Us-clone/
├── main.py              # Entry point - game loop
├── game.py              # Core game class (3278 lines) - state, UI, multiplayer sync
├── server.py            # Multiplayer game server
├── server_voice.py      # Voice chat server
├── voice.py             # Voice chat client
├── sprites.py           # Player and Bot sprite classes
├── tilemap.py           # Map loading (TiledMap) and Camera system
├── menu.py              # Menu navigation and UI
├── board.py             # UI surface rendering
├── tasks.py             # Task system implementation
├── gamefunctions.py     # Ambient sounds, glowing objects
├── settings.py          # Game configuration (571 lines)
├── drawable.py          # Base Drawable class for UI elements
├── func.py              # Utility functions, bot positions
├── setup.py             # cx_Freeze build configuration
├── requirements.txt     # Python dependencies
└── Assets/
    ├── Fonts/           # Custom fonts (Rubik-ExtraBold)
    ├── Images/
    │   ├── Alerts/      # Victory/defeat screens
    │   ├── credits/     # Credits screen
    │   ├── Environment/ # Map decorations
    │   ├── help/        # Help screen images (9 pages)
    │   ├── Items/       # Interactive objects
    │   ├── Meeting/     # Voting UI elements
    │   ├── menu/        # Menu UI elements
    │   ├── Player/      # 10 color variants with animations
    │   │   ├── Black/, Blue/, Brown/, Green/, Orange/
    │   │   ├── Pink/, Purple/, Red/, White/, Yellow/
    │   │   └── (each with walk animations, ghost, dead sprites)
    │   ├── Tasks/       # Task mini-game assets (12 tasks)
    │   └── UI/          # Buttons, icons
    ├── Maps/            # Tiled map files (.tmx)
    └── Sounds/
        ├── Ambience/    # Room ambient sounds
        ├── Background/  # Menu/game music
        ├── Footsteps/   # 8 footstep variants
        ├── General/     # Game events (kill, alarm, victory)
        ├── Tasks Backgrounds/
        └── UI/          # Menu sounds
```

## Architecture

### Core Modules

| Module | Description |
|--------|-------------|
| `game.py` | Central `Game` class managing game state, player positions, multiplayer sync, sabotage timers, voting system, and all UI windows |
| `sprites.py` | `Player` and `Bot` sprite classes with movement, collision, animation, and color variants |
| `tilemap.py` | `TiledMap` for loading .tmx maps, `Camera` for viewport following player |
| `menu.py` | `Menu` class handling main menu, character selection, name/IP input |
| `board.py` | `Board` class for screen surface and drawing menu backgrounds |
| `gamefunctions.py` | `GameFunctions` handling ambient sounds per room and glowing interactive objects |
| `tasks.py` | `Task` class with task completion logic |

### Networking

- **Game Server** (`server.py`): Uses `asyncore` for async socket handling. Maintains `minionmap` dict of connected players with position/state sync via pickle serialization.
- **Voice Server** (`server_voice.py`): TCP broadcast server for voice data on port 4322.
- **Client**: Game connects via TCP socket, sends/receives serialized player state at each frame.

## Game Features

### Game Modes
- **Freeplay**: Single-player with 9 AI bots
- **Multiplayer**: LAN-based, up to 5+ players

### Player Colors
Black, Blue, Brown, Green, Orange, Pink, Purple, Red, White, Yellow

### Tasks (12 mini-games)
| Task | Location |
|------|----------|
| Align Engine Output | Engine Room |
| Clear Asteroids | Weapons |
| Divert Power | Electrical |
| Empty Garbage | Storage |
| Enter ID Code | Admin |
| Fix Wiring | Electrical |
| Fuel Engines | Storage → Engines |
| Reboot Wifi | Communications |
| Stabilize Steering | Navigation |
| Start Reactor | Reactor |
| Swipe Card | Admin |
| Become Imposter | (Special) |

### Imposter Mechanics
- **Kill**: Press `Enter` near crewmate
- **Vent**: Press `Space` at vent locations, `Alt` to move between vents
- **Sabotage Lights**: Press `Ctrl`
- **Sabotage Reactor**: Press `Shift`

### Map Rooms
Cafeteria, MedBay, Security, Reactor, Upper/Lower Engine, Electrical, Storage, Admin, Communications, O2, Cockpit, Weapons

Each room has proximity-based ambient sounds with configurable detection radius.

## Configuration

Key settings in `settings.py`:

```python
WIDTH = 1280
HEIGHT = 640
FPS = 60
TILESIZE = 32
PLAYER_SPEED = 400
NO_OF_MISSIONS = 8
NO_OF_BOTS = 9
```

## How to Run

### Prerequisites
```bash
pip install -r requirements.txt
```

### Single Player
```bash
python main.py
# Select "Freeplay" from menu
```

### Multiplayer
```bash
# Terminal 1 - Start server
python server.py

# Terminal 2+ - Start clients
python main.py
# Select "Local" → Enter server IP (127.0.0.1 for localhost)
```

### Voice Chat (Experimental)
```bash
# Terminal 1 - Voice server
python server_voice.py

# Terminal 2+ - Voice clients
python voice.py
# Enter server IP
```

## Controls

### Menu
| Key | Action |
|-----|--------|
| W/S/↑/↓ | Navigate |
| A/D/←/→ | Navigate |
| Enter | Select |
| Esc | Back |

### In-Game
| Key | Action |
|-----|--------|
| W/A/S/D or Arrows | Move |
| Space | Interact / Use Vent |
| Tab | View Map |
| Alt | Change Vent (while in vent) |
| Enter | Kill (Imposter) |
| Ctrl | Sabotage Lights (Imposter) |
| Shift | Sabotage Reactor (Imposter) |
| Left Click | View Tasks / Complete Tasks / Vote |

## Build Executable

```bash
python setup.py build
```

Uses cx_Freeze to package into standalone executable with Assets folder.

## Network Protocol

Player state is serialized via `pickle` with 26 fields:
- Position (x, y)
- Player ID and color
- Alive status
- Sprite animation indices
- Tasks completed
- Sabotage sync flags
- Voting data
- Emergency meeting sync

Buffer size: 8192 bytes

## File Statistics

| File | Lines |
|------|-------|
| game.py | 3,278 |
| settings.py | 571 |
| sprites.py | 570 |
| gamefunctions.py | 408 |
| menu.py | 292 |
| board.py | 234 |
| server.py | 142 |
| tilemap.py | 71 |
| voice.py | 57 |
| server_voice.py | 53 |
| tasks.py | 54 |
| main.py | 20 |
| **Total** | ~5,750 |

## Dependencies

```
pygame==2.5.2
pytmx==3.32
pyaudio==0.2.14
cx_Freeze==6.15.16
```

Standard library: `socket`, `asyncore`, `threading`, `pickle`, `select`, `random`, `sys`, `os`, `time`, `math`
