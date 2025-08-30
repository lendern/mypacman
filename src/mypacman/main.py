import argparse
import random
from .game import Game


def main():
    parser = argparse.ArgumentParser(description="MyPacman CLI")
    parser.add_argument("--ghosts", type=int, default=4, help="Number of ghosts (AI)")
    parser.add_argument("--speed", type=float, default=0.5, help="Pac-Man and ghosts speed scale (1.0 = default, 0.5 = half)")
    parser.add_argument("--maze-seed", type=int, default=None, help="Seed for maze generation (default: random each run)")
    args = parser.parse_args()

    # Randomize seed if not provided to vary maps across runs
    seed = args.maze_seed if args.maze_seed is not None else random.randrange(1, 2**31)

    # Enable maze generation by default for the CLI game
    game = Game(maze=True, speed_scale=args.speed, ghosts_count=max(0, args.ghosts), maze_seed=seed, cell_aspect=2.0, freeze_on_win=True)
    game.run()


if __name__ == "__main__":
    main()
