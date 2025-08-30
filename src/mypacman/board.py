import random


class Board:
    """Board state and walkability rules (no I/O).

    Maintains a tile grid for inner cells and renders a matrix including
    a double-line border. Provides helpers for center, clamp, walkability,
    and tunnel wrap.
    Also supports optional random maze generation at construction.
    """

    BORDER = {
        'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║'
    }

    # Tile types for inner area
    TILE_EMPTY = 0
    TILE_WALL = 1
    TILE_PELLET = 2
    TILE_POWER = 3

    def __init__(self, width=80, height=24, generate_maze=False, seed=None):
        self.width = max(3, int(width))
        self.height = max(3, int(height))
        self.generated_maze = bool(generate_maze)
        self.inner_width = self.width - 2
        self.inner_height = self.height - 2
        # inner tiles[y][x] for 1..width-2, 1..height-2
        self.tiles = [[self.TILE_PELLET for _ in range(self.width)] for _ in range(self.height)]
        # initialize outer area and default inner pellets
        self._init_tiles()
        # rows that act as tunnel wrap (empty set by default)
        self.tunnel_rows = set()
        # columns that act as vertical wrap (optional)
        self.tunnel_cols = set()
        # optional maze generation
        if generate_maze:
            self.generate_maze(seed=seed)

    def _init_tiles(self):
        # fill everything with empty first
        for y in range(self.height):
            for x in range(self.width):
                self.tiles[y][x] = self.TILE_EMPTY
        # set inner cells to pellets by default
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                self.tiles[y][x] = self.TILE_PELLET

    def get_matrix(self):
        """Render a matrix of display characters including border and tiles."""
        m = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        # draw borders
        for x in range(1, self.width - 1):
            m[0][x] = self.BORDER['h']
            m[self.height - 1][x] = self.BORDER['h']
        for y in range(1, self.height - 1):
            m[y][0] = self.BORDER['v']
            m[y][self.width - 1] = self.BORDER['v']
        m[0][0] = self.BORDER['tl']
        m[0][self.width - 1] = self.BORDER['tr']
        m[self.height - 1][0] = self.BORDER['bl']
        m[self.height - 1][self.width - 1] = self.BORDER['br']
        # carve visual openings for wrap tunnels (left/right on tunnel_rows, top/bottom on tunnel_cols)
        for y in range(1, self.height - 1):
            if y in getattr(self, 'tunnel_rows', set()):
                m[y][0] = ' '
                m[y][self.width - 1] = ' '
        for x in range(1, self.width - 1):
            if x in getattr(self, 'tunnel_cols', set()):
                m[0][x] = ' '
                m[self.height - 1][x] = ' '
        # helper to render inner wall segments using the same double-line style as the border
        def wall_glyph(x, y):
            # neighbors within inner area only
            def is_wall(nx, ny):
                if nx <= 0 or nx >= self.width - 1 or ny <= 0 or ny >= self.height - 1:
                    return False
                return self.tiles[ny][nx] == self.TILE_WALL

            u = is_wall(x, y - 1)
            r = is_wall(x + 1, y)
            d = is_wall(x, y + 1)
            l = is_wall(x - 1, y)

            # 4-way
            if u and r and d and l:
                return '╬'
            # 3-way tees
            if r and d and l and not u:
                return '╦'
            if u and d and l and not r:
                return '╣'
            if u and r and l and not d:
                return '╩'
            if u and r and d and not l:
                return '╠'
            # straight lines
            if (u and d) and not (l or r):
                return '║'
            if (l and r) and not (u or d):
                return '═'
            # corners (2-way)
            if u and r and not (d or l):
                return '╚'
            if r and d and not (u or l):
                return '╔'
            if d and l and not (u or r):
                return '╗'
            if l and u and not (r or d):
                return '╝'
            # endcaps / single neighbor
            if u or d:
                return '║'
            if l or r:
                return '═'
            # isolated
            return '═'

        # draw inner tiles
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                t = self.tiles[y][x]
                if t == self.TILE_WALL:
                    ch = wall_glyph(x, y)
                elif t == self.TILE_PELLET:
                    ch = '·'
                elif t == self.TILE_POWER:
                    ch = '○'
                else:
                    ch = ' '
                m[y][x] = ch
        return m

    def center_position(self):
        cx = 1 + (self.inner_width // 2)
        cy = 1 + (self.inner_height // 2)
        return (cx, cy)

    def clamp_to_inner(self, x, y):
        x = max(1, min(self.width - 2, int(x)))
        y = max(1, min(self.height - 2, int(y)))
        return (x, y)

    # --- Maze generation ---
    def _odd_within(self, v, lo, hi):
        v = max(lo, min(hi, int(v)))
        if v % 2 == 0:
            if v + 1 <= hi:
                v += 1
            elif v - 1 >= lo:
                v -= 1
        return v

    def generate_maze(self, seed=None):
        """Carve a random maze inside the inner area.

        Uses recursive backtracking (depth-first) on a grid of odd coordinates,
        marking corridors with pellets and walls elsewhere. Ensures the center
        cell is part of the maze.
        """
        rng = random.Random(seed)
        if self.inner_width < 1 or self.inner_height < 1:
            return

        # Set all inner cells as walls initially
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                self.tiles[y][x] = self.TILE_WALL

        # Start near center, snap to odd coordinates inside the inner area
        cx, cy = self.center_position()
        sx = self._odd_within(cx, 1, self.width - 2)
        sy = self._odd_within(cy, 1, self.height - 2)

        stack = [(sx, sy)]
        self.tiles[sy][sx] = self.TILE_PELLET

        # Neighbor directions (dx,dy) for cells two steps away
        dirs = [(2, 0), (-2, 0), (0, 2), (0, -2)]

        while stack:
            x, y = stack[-1]
            neighbors = []
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 1 <= nx <= self.width - 2 and 1 <= ny <= self.height - 2:
                    if self.tiles[ny][nx] == self.TILE_WALL:
                        neighbors.append((nx, ny, dx, dy))
            if neighbors:
                nx, ny, dx, dy = rng.choice(neighbors)
                # carve through the wall between (x,y) and (nx,ny)
                wx, wy = x + (dx // 2), y + (dy // 2)
                self.tiles[wy][wx] = self.TILE_PELLET
                self.tiles[ny][nx] = self.TILE_PELLET
                stack.append((nx, ny))
            else:
                stack.pop()

        # Add extra links to increase intersections and reduce dead-ends
        extra_link_prob = 0.30  # 30% of eligible separating walls will be opened
        candidates = []
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.tiles[y][x] != self.TILE_WALL:
                    continue
                # Horizontal separator: pellets on both sides left/right
                if 1 <= x - 1 and x + 1 <= self.width - 2:
                    if self.tiles[y][x - 1] == self.TILE_PELLET and self.tiles[y][x + 1] == self.TILE_PELLET:
                        candidates.append((x, y))
                        continue
                # Vertical separator: pellets on both sides up/down
                if 1 <= y - 1 and y + 1 <= self.height - 2:
                    if self.tiles[y - 1][x] == self.TILE_PELLET and self.tiles[y + 1][x] == self.TILE_PELLET:
                        candidates.append((x, y))
                        continue

        rng.shuffle(candidates)
        for (wx, wy) in candidates:
            if rng.random() < extra_link_prob:
                self.tiles[wy][wx] = self.TILE_PELLET

        # Do not place power pellets here; game startup will handle fixed count

        # Ensure visible, functional wrap tunnels on center row/column
        cx, cy = self.center_position()
        # carve full horizontal corridor on center row
        for x in range(1, self.width - 2 + 1):
            self.tiles[cy][x] = self.TILE_PELLET
        # carve full vertical corridor on center column
        for y in range(1, self.height - 2 + 1):
            self.tiles[y][cx] = self.TILE_PELLET
        # mark tunnels so movement wraps at borders
        self.tunnel_rows.add(cy)
        self.tunnel_cols.add(cx)

        # Avoid "double wall" look by clearing walls adjacent to outer border
        # on the rightmost inner column and bottommost inner row.
        # This keeps a one-cell corridor along these edges.
        right_inner = self.width - 2
        bottom_inner = self.height - 2
        for y in range(1, self.height - 1):
            if self.tiles[y][right_inner] == self.TILE_WALL:
                self.tiles[y][right_inner] = self.TILE_PELLET
        for x in range(1, self.width - 1):
            if self.tiles[bottom_inner][x] == self.TILE_WALL:
                self.tiles[bottom_inner][x] = self.TILE_PELLET

    # --- Tile utilities ---
    def set_wall(self, x, y):
        self.tiles[y][x] = self.TILE_WALL

    def set_empty(self, x, y):
        self.tiles[y][x] = self.TILE_EMPTY

    def set_pellet(self, x, y):
        self.tiles[y][x] = self.TILE_PELLET

    def set_power(self, x, y):
        self.tiles[y][x] = self.TILE_POWER

    def count_pellets(self):
        c = 0
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.tiles[y][x] in (self.TILE_PELLET, self.TILE_POWER):
                    c += 1
        return c

    def count_power(self):
        c = 0
        for y in range(1, self.height - 1):
            for x in range(1, self.width - 1):
                if self.tiles[y][x] == self.TILE_POWER:
                    c += 1
        return c

    def consume_pellet(self, x, y):
        """Consume pellet/power at (x,y). Return points earned, or 0.

        Does nothing if no pellet present.
        """
        if self.tiles[y][x] == self.TILE_PELLET:
            self.tiles[y][x] = self.TILE_EMPTY
            return 10
        if self.tiles[y][x] == self.TILE_POWER:
            self.tiles[y][x] = self.TILE_EMPTY
            return 50
        return 0

    # --- Movement helpers ---
    def is_walkable(self, x, y):
        if x <= 0 or x >= self.width - 1 or y <= 0 or y >= self.height - 1:
            return False
        return self.tiles[y][x] != self.TILE_WALL

    def can_move(self, x, y, dx, dy):
        nx, ny = x + dx, y + dy
        if self.is_walkable(nx, ny):
            return True
        # check tunnel wrap horizontally on designated rows
        if dy == 0 and y in self.tunnel_rows:
            if dx < 0 and x == 1 and self.is_walkable(self.width - 2, y):
                return True
            if dx > 0 and x == self.width - 2 and self.is_walkable(1, y):
                return True
        # check tunnel wrap vertically on designated columns
        if dx == 0 and hasattr(self, 'tunnel_cols') and x in self.tunnel_cols:
            if dy < 0 and y == 1 and self.is_walkable(x, self.height - 2):
                return True
            if dy > 0 and y == self.height - 2 and self.is_walkable(x, 1):
                return True
        return False

    def apply_move(self, x, y, dx, dy):
        nx, ny = x + dx, y + dy
        if self.is_walkable(nx, ny):
            return (nx, ny)
        # tunnel wrap horizontally on designated rows
        if dy == 0 and y in self.tunnel_rows:
            if dx < 0 and x == 1 and self.is_walkable(self.width - 2, y):
                return (self.width - 2, y)
            if dx > 0 and x == self.width - 2 and self.is_walkable(1, y):
                return (1, y)
        # tunnel wrap vertically on designated columns
        if dx == 0 and hasattr(self, 'tunnel_cols') and x in self.tunnel_cols:
            if dy < 0 and y == 1 and self.is_walkable(x, self.height - 2):
                return (x, self.height - 2)
            if dy > 0 and y == self.height - 2 and self.is_walkable(x, 1):
                return (x, 1)
        # blocked
        return (x, y)
