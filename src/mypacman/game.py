import time
import shutil
import sys
import random

from .board import Board
from .player import Player
from .ghost import Ghost
from .renderer import Renderer
from .input_handler import InputHandler


class Game:
    def __init__(self, width=40, height=12, tick=0.05, cell_aspect=1.0, maze=False, maze_seed=None, speed_scale=1.0, ghosts_count=0, freeze_on_win=False):
        # cell_aspect = character height (pixels) / character width (pixels)
        # used to scale vertical movement so pixels/sec match horizontal.
        self.board = Board(width=width, height=height, generate_maze=maze, seed=maze_seed)
        self.renderer = Renderer(width=self.board.width, height=self.board.height)
        self.player = None
        self.input = InputHandler()
        self.is_running = False
        self.tick = tick
        self.state = 0
        # cell_aspect = character height / width; used to equalize pixel-per-second speed
        self.cell_aspect = float(cell_aspect)
        self.speed_scale = float(speed_scale)
        self.ghosts_count = int(ghosts_count)
        # Super mode state
        self.super_active = False
        self.super_until = 0.0
        self._last_super_active = False
        # Whether to freeze with overlay on win (CLI) or end immediately (tests)
        self.freeze_on_win = bool(freeze_on_win)

        # fractional movement accumulators (do not change player's integer pos until >= 1)
        self._acc_x = 0.0
        self._acc_y = 0.0
        self._speed_acc = 0.0
        self._ghost_acc = 0.0
        self._last_axis = None  # 'h' or 'v' of last applied move
        # Ghosts move 20% slower than previous setting (now 0.512x PM speed)
        self.ghost_speed_scale = self.speed_scale * 0.512

        # Deprecated movement smoothing/repeat state (kept for backward compatibility references)
        self._prev_dir = (0, 0)
        self._moves_per_second = 8.0
        self._last_move_time = 0.0
        self._last_input_time = 0.0
        self._holding_dir = (0, 0)
        self._hold_timeout = 0.0  # immediate stop on release
        self._pressed_dir = (0, 0)
        # Buffered movement state
        self._desired_dir = (0, 0)
        self._current_dir = (0, 0)
        # Score and pellets tracking
        self.score = 0
        self.level_complete = False
        self.caught_by_ghost = False
        self.ghosts = []
        self.is_frozen = False

    def _ensure_terminal_size(self):
        size = shutil.get_terminal_size(fallback=(80, 24))
        cols, lines = size.columns, size.lines
        # Need one extra line below the board for score HUD
        min_lines = self.board.height + 1
        if cols < self.board.width or lines < min_lines:
            print(f"Terminal too small: need at least {self.board.width}x{min_lines} (cols x lines).")
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
        self._speed_acc = 0.0
        self._ghost_acc = 0.0
        self._last_axis = None
        self.is_running = True
        self.state = 0
        try:
            self.input.start()
        except Exception:
            # tests or restricted envs may not allow termios changes
            pass
        # place power pellets (6) on maze maps before rendering
        if self.board and getattr(self.board, 'generated_maze', False):
            try:
                self._place_power_pellets(6)
            except Exception:
                pass
        # spawn ghosts
        self._spawn_ghosts()
        # initial full render with ghosts overlay
        try:
            # At start, normal mode => PM yellow, ghosts green
            self.renderer.render_board(self.board, self.player, ghosts=self.ghosts, ghost_color='green', player_color='yellow')
        except TypeError:
            self.renderer.render_board(self.board, self.player)
        # Draw initial HUD: score + remaining power pellets
        try:
            power_left = self.board.count_power() if hasattr(self.board, 'count_power') else 0
            hud = f"Score: {self.score} | Power: {power_left}"
            self.renderer.draw_score(hud)
        except Exception:
            pass
        return True

    def _place_power_pellets(self, count):
        """Place power pellets at visually distributed locations.

        Tries deterministic seeds near the four corners and along the central corridor,
        falling back to random pellet cells if necessary.
        """
        count = max(0, int(count))
        if count == 0:
            return
        # Helper: find nearest pellet from a seed using BFS on walkable cells
        from collections import deque

        def nearest_pellet(seed):
            sx, sy = seed
            vis = set()
            q = deque([seed])
            vis.add(seed)
            while q:
                x, y = q.popleft()
                if 1 <= x <= self.board.width - 2 and 1 <= y <= self.board.height - 2:
                    if self.board.tiles[y][x] == self.board.TILE_PELLET:
                        return (x, y)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = self.board.apply_move(x, y, dx, dy)
                    if (nx, ny) != (x, y) and (nx, ny) not in vis:
                        vis.add((nx, ny))
                        q.append((nx, ny))
            return None

        w, h = self.board.width, self.board.height
        cx, cy = self.board.center_position()
        # Preferred seeds: near corners and along center row
        seeds = [
            (2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3),
            (w // 4, cy), (3 * w // 4, cy)
        ]
        # Exclude player's starting position
        if self.player is not None:
            ppos = self.player.get_position()
            seeds = [s for s in seeds if s != ppos]
        placed = set()
        for s in seeds:
            if len(placed) >= count:
                break
            tgt = nearest_pellet(s)
            if tgt and tgt not in placed:
                x, y = tgt
                self.board.set_power(x, y)
                placed.add(tgt)
        # Fallback: random pellets if not enough placed
        remaining = count - len(placed)
        if remaining > 0:
            cells = [(x, y) for y in range(1, self.board.height - 1)
                     for x in range(1, self.board.width - 1)
                     if self.board.tiles[y][x] == self.board.TILE_PELLET and (x, y) not in placed]
            random.shuffle(cells)
            for (x, y) in cells[:remaining]:
                self.board.set_power(x, y)

    def _spawn_ghosts(self):
        # Choose candidate spawn positions: corners first, then random walkable cells
        candidates = []
        corners = [(1, 1), (self.board.width - 2, 1), (1, self.board.height - 2), (self.board.width - 2, self.board.height - 2)]
        for pos in corners:
            x, y = pos
            if self.board.is_walkable(x, y):
                candidates.append(pos)
        # Fallback to scan inner area for walkable spots
        if len(candidates) < self.ghosts_count:
            for y in range(1, self.board.height - 1):
                for x in range(1, self.board.width - 1):
                    if self.board.is_walkable(x, y):
                        candidates.append((x, y))
        # ensure player position excluded
        if self.player is not None:
            ppos = self.player.get_position()
            candidates = [c for c in candidates if c != ppos]
        # Deduplicate while keeping order
        seen = set()
        uniq = []
        for c in candidates:
            if c not in seen:
                uniq.append(c)
                seen.add(c)
        # Create ghosts up to requested count
        self.ghosts = []
        for i in range(max(0, self.ghosts_count)):
            if i < len(uniq):
                gx, gy = uniq[i]
            else:
                # default to center offsets if not enough candidates
                gx, gy = self.board.center_position()
            self.ghosts.append(Ghost(initial_position=(gx, gy)))
        # initialize ghost directions toward player if possible
        target = self.player.get_position()
        for g in self.ghosts:
            self._init_ghost_dir(g, target)

    def update_game(self):
        try:
            # wait up to one tick for input so a key press is handled immediately
            dir_vec = self.input.get_direction(timeout=self.tick)
        except Exception:
            dir_vec = (0, 0)
        # If game is frozen (game over), only allow quit with 'q'
        if self.is_frozen:
            if dir_vec is None:
                self.is_running = False
            return
        # Expire super mode based on wall clock, even if PM is idle
        if self.super_active and time.time() >= self.super_until:
            self.super_active = False
            # Redraw immediately to keep PM/Ghosts colors in sync
            try:
                self._redraw_state()
            except Exception:
                pass
            self._last_super_active = self.super_active
        # Ghost movement: independent cadence, runs every tick regardless of PM speed
        if self.ghosts:
            self._ghost_acc += max(0.0, self.ghost_speed_scale)
            if self._ghost_acc >= 1.0:
                self._ghost_acc -= 1.0
                self._update_ghosts()
                # During super mode, force a full redraw to avoid trails/ghosting artifacts
                if self.super_active:
                    try:
                        self.renderer.draw_full(self.board, self.player, ghosts=self.ghosts,
                                                 ghost_color='blue', player_color='red')
                        power_left = self.board.count_power() if hasattr(self.board, 'count_power') else 0
                        hud = f"Score: {self.score} | Power: {power_left}"
                        self.renderer.draw_score(hud)
                    except Exception:
                        pass
                # Robust collision check even if AI didn't flag it
                if self._check_collisions():
                    self.state += 1
                    return
                # if a collision happened, we freeze; keep overlay, await 'q'
                if self.is_frozen:
                    self.state += 1
                    return
        if dir_vec is None:
            self.is_running = False
            return
        # Buffered input: remember desired direction when non-zero
        dx, dy = dir_vec
        if dx != 0 or dy != 0:
            self._desired_dir = (dx, dy)

        # Movement speed control with cell aspect equalization
        # Determine intended axis for this tick (desired auto-turn if possible)
        intended_axis = None
        ddx, ddy = self._desired_dir
        if (ddx, ddy) != (0, 0) and self.board.can_move(self.player.x, self.player.y, ddx, ddy):
            intended_axis = 'h' if ddx != 0 else 'v'
        else:
            cdx, cdy = self._current_dir
            if (cdx, cdy) != (0, 0):
                intended_axis = 'h' if cdx != 0 else 'v'
        # Accumulate time
        self._speed_acc += max(0.0, self.speed_scale)
        # If switching to vertical movement, grant a one-time credit to preserve smooth turns
        if intended_axis and self._last_axis and intended_axis != self._last_axis:
            if intended_axis == 'v' and self.cell_aspect > 1.0:
                self._speed_acc += (self.cell_aspect - 1.0)
        # Threshold depends on axis
        threshold = 1.0 if intended_axis != 'v' else max(1.0, self.cell_aspect)
        if self._speed_acc < threshold:
            # no movement this tick
            self.state += 1
            return
        self._speed_acc -= threshold

        prev_pos = self.player.get_position()
        moved = False
        # Auto-turn if possible
        if self._desired_dir != self._current_dir:
            ddx, ddy = self._desired_dir
            if ddx != 0 or ddy != 0:
                if self.board.can_move(self.player.x, self.player.y, ddx, ddy):
                    self._current_dir = self._desired_dir
                    moved = True
        # Move in current direction if possible
        cdx, cdy = self._current_dir
        if cdx != 0 or cdy != 0:
            if self.board.can_move(self.player.x, self.player.y, cdx, cdy):
                nx, ny = self.board.apply_move(self.player.x, self.player.y, cdx, cdy)
                if (nx, ny) != (self.player.x, self.player.y):
                    self.player.set_position(nx, ny)
                    self._last_axis = 'h' if cdx != 0 else 'v'
                    moved = True

        if moved:
            # pellet consumption and base update before rendering next leave
            px, py = self.player.get_position()
            points = self.board.consume_pellet(px, py)
            if points:
                self.score += points
                # Activate super mode on power pellet (>=50 points)
                if points >= 50:
                    self.super_active = True
                    self.super_until = time.time() + 10.0
                    # Redraw immediately so PM/Ghosts switch colors together
                    try:
                        self._redraw_state()
                    except Exception:
                        pass
                    self._last_super_active = self.super_active
                # update renderer base so that when player leaves the cell is empty
                try:
                    self.renderer.set_base_cell(px, py, ' ')
                except Exception:
                    pass
                # update the HUD score line
                try:
                    power_left = self.board.count_power() if hasattr(self.board, 'count_power') else 0
                    hud = f"Score: {self.score} | Power: {power_left}"
                    self.renderer.draw_score(hud)
                except Exception:
                    pass
            # update player on screen (yellow)
            try:
                self.renderer.update_player(prev_pos, self.player.get_position(), color=('red' if self.super_active else 'yellow'))
            except TypeError:
                self.renderer.update_player(prev_pos, self.player.get_position())
            # collision check after player move too
            if self._check_collisions():
                self.state += 1
                return

        # Ghosts already updated earlier in the tick
        
        # Check collisions and level completion
        # Secondary guard: if state toggled for any reason, redraw once
        if (self.super_active and time.time() >= self.super_until):
            self.super_active = False
        if self._last_super_active != self.super_active:
            try:
                self._redraw_state()
            except Exception:
                pass
            self._last_super_active = self.super_active
        if self.caught_by_ghost:
            # keep running (frozen) until user quits
            pass
        # Win conditions: all pellets eaten OR all ghosts eaten
        if (self.board.count_pellets() == 0) or (len(self.ghosts) == 0):
            self.level_complete = True
            if self.freeze_on_win:
                # Show win overlay in green and freeze; wait for 'q' to quit
                try:
                    self.renderer.show_popup("You win", color='green')
                except Exception:
                    pass
                self.is_frozen = True
                return
            else:
                self.is_running = False
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
        # clear terminal on quit (always clear on explicit quit)
        try:
            sys.stdout.write('\x1b[2J')
            sys.stdout.write('\x1b[H')
            sys.stdout.flush()
        except Exception:
            pass
        if self.caught_by_ghost:
            print("Game over: caught by ghosts!")
        elif self.level_complete:
            print("You win!")
        else:
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

    # --- Ghost AI ---
    def _update_ghosts(self):
        # Flee during super mode; otherwise chase via LOS or wander
        target = self.player.get_position()
        for g in self.ghosts:
            if not self.is_running:
                break
            gx, gy = g.get_position()
            gdx, gdy = g.get_direction()
            moved = False
            tx, ty = target
            if self.super_active:
                # Flee: choose step that maximizes Manhattan distance
                best = None
                best_dist = -1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if not self.board.can_move(gx, gy, dx, dy):
                        continue
                    nx, ny = self.board.apply_move(gx, gy, dx, dy)
                    if (nx, ny) == (gx, gy):
                        continue
                    dist = abs(nx - tx) + abs(ny - ty)
                    if dist > best_dist:
                        best_dist = dist
                        best = (dx, dy, nx, ny)
                if best is not None:
                    dx, dy, nx, ny = best
                    g.set_position(nx, ny)
                    g.set_direction(dx, dy)
                    try:
                        self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False, color=('blue' if self.super_active else 'green'))
                    except TypeError:
                        self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False)
                    moved = True
                # No collision game-over during super; PM may still eat them later
            else:
                # 0) If adjacent to player and path is open, step directly into player
                ddx, ddy = tx - gx, ty - gy
                if abs(ddx) + abs(ddy) == 1:
                    if self.board.can_move(gx, gy, ddx, ddy):
                        nx, ny = self.board.apply_move(gx, gy, ddx, ddy)
                        if (nx, ny) != (gx, gy):
                            g.set_position(nx, ny)
                            g.set_direction(ddx, ddy)
                            try:
                                self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False, color=('blue' if self.super_active else 'green'))
                            except TypeError:
                                self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False)
                            moved = True
                            # collision will be handled below
                if moved:
                    # collision check
                    if g.get_position() == target:
                        self.caught_by_ghost = True
                        try:
                            self.renderer.show_popup("Game Over")
                        except Exception:
                            pass
                        self.is_frozen = True
                        return
                else:
                    # 1) If line of sight on same row/col, chase directly towards PM
                    los = self._los_direction((gx, gy), target)
                    if los is not None:
                        dx, dy = los
                        if self.board.can_move(gx, gy, dx, dy):
                            nx, ny = self.board.apply_move(gx, gy, dx, dy)
                            if (nx, ny) != (gx, gy):
                                g.set_position(nx, ny)
                                g.set_direction(dx, dy)
                                try:
                                    self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False, color=('blue' if self.super_active else 'green'))
                                except TypeError:
                                    self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False)
                                moved = True
                    # 2) Otherwise, wander randomly
                    if not moved:
                        dx, dy = self._ghost_random_step((gx, gy), (gdx, gdy))
                        if dx is not None:
                            nx, ny = self.board.apply_move(gx, gy, dx, dy)
                            if (nx, ny) != (gx, gy):
                                g.set_position(nx, ny)
                                g.set_direction(dx, dy)
                                try:
                                    self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False, color=('blue' if self.super_active else 'green'))
                                except TypeError:
                                    self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False)
                                moved = True
            # 1) If line of sight on same row/col, chase directly towards PM
            los = self._los_direction((gx, gy), target)
            if los is not None:
                dx, dy = los
                if self.board.can_move(gx, gy, dx, dy):
                    nx, ny = self.board.apply_move(gx, gy, dx, dy)
                    if (nx, ny) != (gx, gy):
                        g.set_position(nx, ny)
                        g.set_direction(dx, dy)
                        try:
                            self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False, color=('blue' if self.super_active else 'green'))
                        except TypeError:
                            self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False)
                        moved = True
            # 2) Otherwise, wander randomly
            if not moved:
                dx, dy = self._ghost_random_step((gx, gy), (gdx, gdy))
                if dx is not None:
                    nx, ny = self.board.apply_move(gx, gy, dx, dy)
                    if (nx, ny) != (gx, gy):
                        g.set_position(nx, ny)
                        g.set_direction(dx, dy)
                        try:
                            self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False, color=('blue' if self.super_active else 'green'))
                        except TypeError:
                            self.renderer.update_player((gx, gy), (nx, ny), player_char='●', white_color=False)
                        moved = True
            # collision check
            if g.get_position() == target:
                if self.super_active:
                    # Eat ghost: clear its previous cell and remove
                    try:
                        self.renderer.update_player((gx, gy), None)
                    except Exception:
                        pass
                    self.ghosts = [gg for gg in self.ghosts if gg is not g]
                else:
                    self.caught_by_ghost = True
                    # show popup and freeze loop; require user to press 'q' to quit
                    try:
                        self.renderer.show_popup("Game Over")
                    except Exception:
                        pass
                    self.is_frozen = True
                    return
            # if couldn't move, try to initialize direction again
            if not moved:
                self._init_ghost_dir(g, target)

    def _ghost_next_step(self, start, goal, prefer_dir=(0, 0)):
        if start == goal:
            return start
        from collections import deque
        q = deque()
        visited = set()
        parents = {}

        def ordered_dirs(x, y):
            # Prefer current direction, then directions that reduce Manhattan distance
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            cdx, cdy = prefer_dir
            # move preferred dir to front if present
            if (cdx, cdy) in dirs:
                dirs.remove((cdx, cdy))
                dirs.insert(0, (cdx, cdy))
            # secondary sort by resulting manhattan distance
            tx, ty = goal
            dirs.sort(key=lambda d: abs(self.board.apply_move(x, y, d[0], d[1])[0] - tx) + abs(self.board.apply_move(x, y, d[0], d[1])[1] - ty))
            return dirs

        q.append(start)
        visited.add(start)
        found = None
        while q:
            cur = q.popleft()
            if cur == goal:
                found = cur
                break
            cx, cy = cur
            for dx, dy in ordered_dirs(cx, cy):
                nx, ny = self.board.apply_move(cx, cy, dx, dy)
                npos = (nx, ny)
                if npos == cur:
                    continue
                if npos in visited:
                    continue
                visited.add(npos)
                parents[npos] = cur
                if npos == goal:
                    found = npos
                    q.clear()
                    break
                q.append(npos)
        if not found:
            return start
        # reconstruct first step from start
        cur = found
        while parents.get(cur) and parents[cur] != start:
            cur = parents[cur]
        return cur

    def _check_collisions(self):
        """Return True if a collision was detected and handled (popup/freeze)."""
        if not self.ghosts or self.is_frozen:
            return False
        ppos = self.player.get_position()
        eaten = []
        for g in list(self.ghosts):
            if g.get_position() == ppos:
                if self.super_active:
                    eaten.append(g)
                else:
                    self.caught_by_ghost = True
                    try:
                        self.renderer.show_popup("Game Over")
                    except Exception:
                        pass
                    self.is_frozen = True
                    return True
        for g in eaten:
            try:
                self.renderer.update_player(g.get_position(), None)
            except Exception:
                pass
        if eaten:
            self.ghosts = [gg for gg in self.ghosts if gg not in eaten]
            return False
        return False

    def _init_ghost_dir(self, g, target):
        gx, gy = g.get_position()
        tx, ty = target
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        # sort by distance to target after moving
        dirs.sort(key=lambda d: abs((self.board.apply_move(gx, gy, d[0], d[1])[0]) - tx) + abs((self.board.apply_move(gx, gy, d[0], d[1])[1]) - ty))
        for dx, dy in dirs:
            if self.board.can_move(gx, gy, dx, dy):
                g.set_direction(dx, dy)
                return
        g.set_direction(0, 0)

    def _ghost_dir_candidates(self, pos, cur_dir, target):
        x, y = pos
        cdx, cdy = cur_dir
        # If no current direction, choose based on closest to target
        if (cdx, cdy) == (0, 0):
            tx, ty = target
            dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            dirs.sort(key=lambda d: abs((self.board.apply_move(x, y, d[0], d[1])[0]) - tx) + abs((self.board.apply_move(x, y, d[0], d[1])[1]) - ty))
            return dirs
        # build relative directions: straight, left, right, reverse
        left = (-cdy, cdx)
        right = (cdy, -cdx)
        straight = (cdx, cdy)
        reverse = (-cdx, -cdy)
        # Prefer straight; if blocked, follow a wall: choose side that is closer to target
        tx, ty = target
        side_dirs = [left, right]
        side_dirs.sort(key=lambda d: abs((self.board.apply_move(x, y, d[0], d[1])[0]) - tx) + abs((self.board.apply_move(x, y, d[0], d[1])[1]) - ty))
        candidates = [straight] + side_dirs + [reverse]
        return candidates

    def _los_direction(self, start, goal):
        """Return (dx,dy) towards goal if on same row/col with no walls between; else None."""
        (x1, y1) = start
        (x2, y2) = goal
        if y1 == y2:
            if x1 < x2:
                rng = range(x1 + 1, x2)
                step = (1, 0)
            else:
                rng = range(x2 + 1, x1)
                step = (-1, 0)
            for xx in rng:
                if self.board.tiles[y1][xx] == self.board.TILE_WALL:
                    return None
            return step
        if x1 == x2:
            if y1 < y2:
                rng = range(y1 + 1, y2)
                step = (0, 1)
            else:
                rng = range(y2 + 1, y1)
                step = (0, -1)
            for yy in rng:
                if self.board.tiles[yy][x1] == self.board.TILE_WALL:
                    return None
            return step
        return None

    def _ghost_random_step(self, pos, cur_dir):
        x, y = pos
        cdx, cdy = cur_dir
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        options = []
        for dx, dy in dirs:
            if self.board.can_move(x, y, dx, dy):
                options.append((dx, dy))
        if not options:
            return (None, None)
        reverse = (-cdx, -cdy)
        if len(options) > 1 and reverse in options:
            options = [d for d in options if d != reverse] or [reverse]
        return random.choice(options)

    def _redraw_state(self):
        # Full redraw with coherent colors based on current state
        ghost_color = 'blue' if self.super_active else 'green'
        player_color = 'red' if self.super_active else 'yellow'
        self.renderer.draw_full(self.board, self.player,
                                player_char='●', white_color=True,
                                ghosts=self.ghosts,
                                ghost_char='●', ghost_color=ghost_color,
                                player_color=player_color)
        # refresh HUD
        power_left = self.board.count_power() if hasattr(self.board, 'count_power') else 0
        hud = f"Score: {self.score} | Power: {power_left}"
        self.renderer.draw_score(hud)
