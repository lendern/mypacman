import shutil

from src.mypacman.board import Board
from src.mypacman.game import Game


def _mock_terminal_large(fallback=(80, 24)):
    import os
    return os.terminal_size((200, 200))


class FakeInputSeq:
    def __init__(self, seq):
        self.seq = list(seq)

    def start(self):
        pass

    def stop(self):
        pass

    def get_direction(self, timeout=0.0):
        if not self.seq:
            return (0, 0)
        return self.seq.pop(0)


class DummyRenderer:
    def __init__(self, *args, **kwargs):
        pass

    def render_board(self, board, player, *args, **kwargs):
        pass

    def update_player(self, prev_pos, new_pos, *args, **kwargs):
        pass

    def finalize(self):
        pass

    def set_base_cell(self, x, y, ch):
        pass


def setup_game(monkeypatch, w=11, h=9):
    monkeypatch.setattr(shutil, "get_terminal_size", lambda fallback=(80, 24): _mock_terminal_large())
    g = Game(width=w, height=h, tick=0)
    g.renderer = DummyRenderer()
    return g


def test_wall_blocks(monkeypatch):
    g = setup_game(monkeypatch)
    # place a wall to the right of spawn
    sx, sy = g.board.center_position()
    g.board.set_wall(sx + 1, sy)
    g.input = FakeInputSeq([(1, 0)])
    assert g.start_game()
    start = g.player.get_position()
    g.update_game()
    # should not move due to wall
    assert g.player.get_position() == start
    g.end_game()


def test_wrap_tunnel(monkeypatch):
    g = setup_game(monkeypatch, w=13, h=9)
    # enable tunnel on the player's row
    _, sy = g.board.center_position()
    g.board.tunnel_rows.add(sy)
    g.input = FakeInputSeq([(-1, 0)])
    assert g.start_game()
    # place player at left inner edge
    g.player.set_position(1, sy)
    g.update_game()
    # should wrap to right inner edge
    assert g.player.get_position() == (g.board.width - 2, sy)
    g.end_game()


def test_pellet_consumption_and_level_end(monkeypatch):
    g = setup_game(monkeypatch, w=5, h=5)
    # Small board: clear all pellets except one in front
    for y in range(1, g.board.height - 1):
        for x in range(1, g.board.width - 1):
            g.board.set_empty(x, y)
    # Put a single pellet to the right of center
    cx, cy = g.board.center_position()
    g.board.set_pellet(cx + 1, cy)
    g.input = FakeInputSeq([(1, 0), (0, 0)])
    assert g.start_game()
    # starting on center (empty), move right to consume last pellet
    g.update_game()
    assert g.score == 10
    # After consuming last pellet, game should end on next update tick
    g.update_game()
    assert g.level_complete is True
    assert g.is_running is False
    g.end_game()


def test_buffered_turn(monkeypatch):
    g = setup_game(monkeypatch, w=9, h=9)
    # Build a corridor shaped like a T: from center, right is free, and up from x+1 is free, but up from center is a wall
    for y in range(1, g.board.height - 1):
        for x in range(1, g.board.width - 1):
            g.board.set_empty(x, y)
    cx, cy = g.board.center_position()
    g.board.set_wall(cx, cy - 1)  # block up at current cell
    # place a wall to the right-up path edge to keep it simple? No, keep free
    # simulate pressing right, then before reaching the intersection, request up
    g.input = FakeInputSeq([(1, 0), (0, -1), (0, -1)])
    assert g.start_game()
    # Tick 1: move right
    g.update_game()
    assert g.player.get_position() == (cx + 1, cy)
    # Tick 2: desired_dir becomes up; since from (cx+1,cy) going up is walkable, auto-turn and move up
    g.update_game()
    assert g.player.get_position() == (cx + 1, cy - 1)
    g.end_game()

