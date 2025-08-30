# Pac-Man-like Game

## Overview
This project is a terminal-based Pac-Man-like game where players control a character navigating through a game board. The game is designed to be played in a shell environment with a resolution of 80x24 characters by default.

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
│       ├── renderer.py
│       └── constants.py
├── tests
│   ├── __init__.py
│   └── test_game.py
├── specifications
│   └── hld.md
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation
To set up the project, clone the repository and install the required dependencies:

```bash
git clone <repository-url>
cd mypacman
pip install -r requirements.txt
```

## Usage
To start the game, run the following command:

```bash
python src/mypacman/main.py

# Or using the provided CLI launcher at repo root:
## make it executable once:
chmod +x mypacman-cli
## then run:
./mypacman-cli
```

## Gameplay
- The game area is displayed in a terminal window, bordered by double-bar characters.
- The main character (PP) is represented as a white ball and starts at the center of the game area.
- Players can move the character using the arrow keys.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.