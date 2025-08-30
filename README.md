# Pac-Man-like Game

## Overview
Terminal-based Pac-Man-like game. The player (PP) moves inside a double-line bordered area. Default terminal resolution target is 80x24.

## Requirements
- Python 3.8+
- Unix-like terminal supporting ANSI escapes and Unicode (●)
- No runtime third-party dependencies
- Tests: `pytest` (dev-only; see `requirements.txt`)

## Project Structure
```
mypacman
├── src
│   └── mypacman
│       ├── __init__.py
│       ├── main.py
│       ├── game.py
│       ├── board.py
│       ├── player.py
│       ├── input_handler.py
│       └── renderer.py
├── tests
│   ├── __init__.py
│   ├── test_game.py
│   └── test_movement.py
├── specifications
│   └── hld.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation
Clone the repository. Runtime has no external dependencies; installing `pytest` is only needed to run tests.

```bash
git clone <repository-url>
cd mypacman
pip install -r requirements.txt   # optional: for tests
```

## Usage
Run the game from the repo root:

```bash
python -m src.mypacman.main

# Or using the provided CLI launcher at repo root:
chmod +x mypacman-cli
./mypacman-cli
```

Notes:
- Ensure the terminal is at least 80x24; otherwise the game refuses to start.
- Controls: arrow keys to move, `q` to quit.

## Gameplay
- The game draws the full board once, then updates only the player cell to reduce flicker.
- The player appears centered at start and moves within the inner area (clamped to borders).

## Running Tests
Execute the test suite with `pytest` from the repo root:

```bash
pytest -q
```

Included tests validate initial spawn, quit behavior, single-step movement, and border clamping.

## Contributing
Issues and pull requests are welcome.

## License
MIT License. See `LICENSE` if present.
