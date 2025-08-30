import shutil
import time

from src.mypacman.game import Game


def _mock_terminal_large(fallback=(80, 24)):
    import os
    return os.terminal_size((200, 200))


class FakeInputOneRight:
    """Returns (1,0) once, then (0,0) to simulate a single right press."""

    def __init__(self):
        self._first = True

    def start(self):
        pass

    def stop(self):
        pass

    def get_direction(self, timeout=0.0):
        if self._first:
            self._first = False
            return (1, 0)
        return (0, 0)


class DummyRenderer:
    """Renderer stub that avoids terminal I/O for tests."""

    def __init__(self, *args, **kwargs):
        self.calls = []

    def render_board(self, board, player, *args, **kwargs):
        self.calls.append(("render_board", player.get_position()))

    def update_player(self, prev_pos, new_pos, *args, **kwargs):
        self.calls.append(("update_player", prev_pos, new_pos))

    def finalize(self):
        self.calls.append(("finalize",))


def test_single_step_right_moves_player(monkeypatch):
    # Ensure terminal size is sufficient
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): _mock_terminal_large())
    game = Game(width=11, height=7, tick=0.0)
    # Replace I/O components with fakes
    game.input = FakeInputOneRight()
    game.renderer = DummyRenderer()

    assert game.start_game() is True
    start_x, start_y = game.player.get_position()

    # One update should apply one right movement from software repeat logic
    game.update_game()

    x, y = game.player.get_position()
    assert (x, y) == (start_x + 1, start_y)

    game.end_game()


def test_clamp_prevents_exiting_right_border(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): _mock_terminal_large())
    game = Game(width=11, height=7, tick=0.0)
    game.input = FakeInputOneRight()
    game.renderer = DummyRenderer()
    assert game.start_game() is True

    # Place player at the rightmost inner cell (width - 2)
    game.player.set_position(game.board.width - 2, game.player.y)
    right_edge = (game.board.width - 2, game.player.y)

    # Attempt to move right; position must remain clamped at the edge
    game.update_game()

    assert game.player.get_position() == right_edge
    game.end_game()

