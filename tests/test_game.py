import os
import shutil
import pytest
from src.mypacman.game import Game


class FakeInputNoop:
    def start(self):
        pass

    def stop(self):
        pass

    def get_direction(self, timeout=0.0):
        return (0, 0)


class FakeInputQuit:
    def start(self):
        pass

    def stop(self):
        pass

    def get_direction(self, timeout=0.0):
        return None


def _mock_terminal_large(fallback=(80, 24)):
    return os.terminal_size((200, 200))


def test_start_game_centers_player(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): _mock_terminal_large())
    game = Game(width=20, height=10, tick=0)
    game.input = FakeInputNoop()
    started = game.start_game()
    assert started is True
    assert game.is_running is True
    assert game.player.get_position() == game.board.center_position()
    game.end_game()


def test_q_quit_stops_game(monkeypatch):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): _mock_terminal_large())
    game = Game(width=20, height=10, tick=0)
    game.input = FakeInputQuit()
    started = game.start_game()
    assert started is True
    assert game.is_running is True
    game.update_game()
    assert game.is_running is False
    game.end_game()