import time
import shutil

from .board import Board
from .player import Player
from .renderer import Renderer
from .input_handler import InputHandler


class Game:
    def __init__(self, width=80, height=24, tick=0.05):
        self.board = Board(width=width, height=height)
        self.renderer = Renderer(width=self.board.width, height=self.board.height)
        self.player = None
        self.input = InputHandler()
        self.is_running = False
        self.tick = tick
        self.state = 0

    def _ensure_terminal_size(self):
        size = shutil.get_terminal_size(fallback=(80, 24))
        cols, lines = size.columns, size.lines
        if cols < self.board.width or lines < self.board.height:
            print(f"Terminal too small: need at least {self.board.width}x{self.board.height} (cols x lines).")
            return False
        return True

    def start_game(self):
        if not self._ensure_terminal_size():
            return False
        center = self.board.center_position()
        self.player = Player(initial_position=center)
        self.is_running = True
        self.state = 0
        try:
            self.input.start()
        except Exception:
            # tests or restricted envs may not allow termios changes
            pass
        self.renderer.render_board(self.board, self.player)
        return True

    def update_game(self):
        try:
            dir_vec = self.input.get_direction(timeout=0.0)
        except Exception:
            dir_vec = (0, 0)
        if dir_vec is None:
            self.is_running = False
            return
        dx, dy = dir_vec
        if dx != 0 or dy != 0:
            new_x = self.player.x + dx
            new_y = self.player.y + dy
            new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
            self.player.set_position(new_x, new_y)
            self.renderer.render_board(self.board, self.player)
        self.state += 1

    def end_game(self):
        self.is_running = False
        try:
            self.input.stop()
        except Exception:
            pass
        print("Game ended.")

    def run(self):
        started = self.start_game()
        if not started:
            return
        try:
            while self.is_running:
                self.update_game()
                time.sleep(self.tick)
        finally:
            self.end_game()