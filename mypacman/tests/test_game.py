import unittest
from src.mypacman.game import Game

class TestGame(unittest.TestCase):

    def setUp(self):
        self.game = Game()

    def test_start_game(self):
        self.game.start_game()
        self.assertTrue(self.game.is_running)

    def test_update_game(self):
        self.game.start_game()
        initial_state = self.game.state
        self.game.update_game()
        self.assertNotEqual(initial_state, self.game.state)

    def test_end_game(self):
        self.game.start_game()
        self.game.end_game()
        self.assertFalse(self.game.is_running)

if __name__ == '__main__':
    unittest.main()