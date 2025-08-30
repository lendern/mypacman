import time
import shutil
import sys

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

        # software repeat parameters: moves per second for horizontal axis
        self._moves_per_second = 8.0
        # last time we applied a software-move
        self._last_move_time = 0.0
        # last raw input timestamp and holding dir
        self._last_input_time = 0.0
        self._holding_dir = (0, 0)
        # how long since last raw input we still consider the key held
        # must be >= typical OS key repeat initial delay to avoid spuriously
        # considering the key released between repeats
        self._hold_timeout = 0.6
        # pressed_dir is the effective direction we're simulating while held
        self._pressed_dir = (0, 0)

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
        now = time.time()
        if dir_vec is None:
            self.is_running = False
            return
        # determine pressed_dir based on raw input + timeout
        dx, dy = dir_vec
        if dx != 0 or dy != 0:
            # record raw input time and set pressed dir
            self._last_input_time = now
            self._pressed_dir = (dx, dy)
        else:
            # if input hasn't been updated recently, treat as released
            if (now - self._last_input_time) > self._hold_timeout:
                self._pressed_dir = (0, 0)

        pdx, pdy = self._pressed_dir
        if pdx != 0 or pdy != 0:
            prev_pos = self.player.get_position()
            moved = False
            # new press detection
            if self._pressed_dir != self._prev_dir:
                # force immediate move by setting last_move_time so a step is available
                self._last_move_time = now - (1.0 / self._moves_per_second)
                self._prev_dir = self._pressed_dir

            # compute elapsed since last applied move and apply integer steps
            elapsed = now - self._last_move_time
            if elapsed > 0:
                # horizontal
                if pdx != 0:
                    rate_x = self._moves_per_second
                    steps_x = int(elapsed * rate_x)
                    for _ in range(steps_x):
                        new_x = self.player.x + (1 if pdx > 0 else -1)
                        new_y = self.player.y
                        new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
                        self.player.set_position(new_x, new_y)
                        self.renderer.update_player(prev_pos, self.player.get_position())
                        prev_pos = self.player.get_position()
                        moved = True
                    if steps_x > 0:
                        self._last_move_time += steps_x / rate_x

                # vertical (scaled rate)
                if pdy != 0:
                    rate_y = self._moves_per_second / self.cell_aspect
                    steps_y = int(elapsed * rate_y)
                    for _ in range(steps_y):
                        new_x = self.player.x
                        new_y = self.player.y + (1 if pdy > 0 else -1)
                        new_x, new_y = self.board.clamp_to_inner(new_x, new_y)
                        self.player.set_position(new_x, new_y)
                        self.renderer.update_player(prev_pos, self.player.get_position())
                        prev_pos = self.player.get_position()
                        moved = True
                    if steps_y > 0:
                        self._last_move_time += steps_y / rate_y
        self.state += 1

    def end_game(self):
        self.is_running = False
        try:
            self.input.stop()
        except Exception:
            pass
        # restore renderer state (show cursor) if available
        try:
            if hasattr(self, 'renderer') and self.renderer is not None:
                self.renderer.finalize()
        except Exception:
            pass
        # clear terminal on quit
        try:
            sys.stdout.write('\x1b[2J')
            sys.stdout.write('\x1b[H')
            sys.stdout.flush()
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