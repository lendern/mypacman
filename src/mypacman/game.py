import time
import shutil

from .board import Board
from .player import Player
from .renderer import Renderer
from .input_handler import InputHandler


class Game:
    def __init__(self, width=80, height=24, tick=0.05, cell_aspect=2.0):
        # cell_aspect = character height (pixels) / character width (pixels)
        # used to scale vertical movement so pixels/sec match horizontal.
        self.board = Board(width=width, height=height)
        self.renderer = Renderer(width=self.board.width, height=self.board.height)
        self.player = None
        self.input = InputHandler()
        self.is_running = False
        self.tick = tick
        self.state = 0
        self.cell_aspect = float(cell_aspect)
        # fractional movement accumulators (do not change player's integer pos until >= 1)
        self._acc_x = 0.0
        self._acc_y = 0.0
        # previous non-zero direction seen (used to detect new press vs repeat)
        self._prev_dir = (0, 0)

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
        # reset fractional accumulators on start
        self._acc_x = 0.0
        self._acc_y = 0.0
        self.is_running = True
        self.state = 0
        try:
            self.input.start()
        except Exception:
            # tests or restricted envs may not allow termios changes
            pass
        # initial full render
        self.renderer.render_board(self.board, self.player)
        return True

    def update_game(self):
        try:
            # wait up to one tick for input so a key press is handled
            # immediately (select wakes as soon as data is available)
            dir_vec = self.input.get_direction(timeout=self.tick)
        except Exception:
            dir_vec = (0, 0)
        if dir_vec is None:
            self.is_running = False
            return
        dx, dy = dir_vec
        if dx != 0 or dy != 0:
            prev_pos = self.player.get_position()
            moved = False

            # If this is a new press (different from previous non-zero dir),
            # apply one immediate move so the player responds instantly.
            if dir_vec != self._prev_dir:
                if dx != 0:
                    new_x = self.player.x + dx
                    new_y = self.player.y
                    new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
                    self.player.set_position(new_x, new_y)
                    self.renderer.update_player(prev_pos, self.player.get_position())
                    prev_pos = self.player.get_position()
                    moved = True
                if dy != 0:
                    new_x = self.player.x
                    new_y = self.player.y + dy
                    new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
                    self.player.set_position(new_x, new_y)
                    self.renderer.update_player(prev_pos, self.player.get_position())
                    prev_pos = self.player.get_position()
                    moved = True
                # reset accumulators so pacing starts after initial immediate move
                self._acc_x = 0.0
                self._acc_y = 0.0
            else:
                # repeat: accumulate fractional movement; vertical is scaled
                self._acc_x += dx
                self._acc_y += (dy / self.cell_aspect)

                # apply integer X moves for each whole unit in accumulator
                while abs(self._acc_x) >= 1.0:
                    step_x = 1 if self._acc_x > 0 else -1
                    new_x = self.player.x + step_x
                    new_y = self.player.y
                    new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
                    self.player.set_position(new_x, new_y)
                    self._acc_x -= step_x
                    self.renderer.update_player(prev_pos, self.player.get_position())
                    prev_pos = self.player.get_position()
                    moved = True

                # apply integer Y moves for each whole unit in accumulator
                while abs(self._acc_y) >= 1.0:
                    step_y = 1 if self._acc_y > 0 else -1
                    new_x = self.player.x
                    new_y = self.player.y + step_y
                    new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
                    self.player.set_position(new_x, new_y)
                    self._acc_y -= step_y
                    self.renderer.update_player(prev_pos, self.player.get_position())
                    prev_pos = self.player.get_position()
                    moved = True

            # update prev_dir tracking: if we saw a non-zero vector this tick
            self._prev_dir = dir_vec
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
        finally:
            self.end_game()