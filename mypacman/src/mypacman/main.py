import sys
import time
from mypacman.game import Game

def main():
    game = Game()
    game.start_game()
    
    while game.is_running():
        game.update_game()
        time.sleep(0.1)  # Control the game loop speed

    game.end_game()

if __name__ == "__main__":
    main()