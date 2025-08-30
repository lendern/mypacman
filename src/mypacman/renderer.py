import sys


class Renderer:
    """Efficient terminal renderer.

    - Uses buffered writes to print the full board once.
    - Keeps a base matrix (board without player) and supports incremental
      updates for the player cell to avoid clearing the whole screen every frame.
    - Hides the cursor while drawing to reduce flicker.
    """

    CSI = '\x1b['
    RESET = '\x1b[0m'
    FG_WHITE = '\x1b[37m'
    FG_BRIGHT_WHITE = '\x1b[97m'
    FG_DIM_WHITE = '\x1b[90m'
    FG_BLUE = '\x1b[34m'
    FG_YELLOW = '\x1b[33m'
    FG_BRIGHT_YELLOW = '\x1b[93m'
    FG_BRIGHT_GREEN = '\x1b[92m'
    FG_ORANGE = '\x1b[38;5;208m'
    FG_BRIGHT_RED = '\x1b[91m'
    BG_BLACK = '\x1b[40m'

    def __init__(self, width=80, height=24):
        self.width = width
        self.height = height
        self._base_matrix = None
        self._player_pos = None

    def _board_to_matrix(self, board):
        if hasattr(board, 'get_matrix'):
            board = board.get_matrix()
        if not board:
            return []
        matrix = []
        for row in board:
            if isinstance(row, str):
                matrix.append(list(row))
            else:
                matrix.append([str(c) for c in row])
        return matrix

    def _hide_cursor(self):
        sys.stdout.write(self.CSI + '?25l')

    def _show_cursor(self):
        sys.stdout.write(self.CSI + '?25h')

    def _move_cursor(self, x, y):
        # x,y are 0-indexed; ANSI is 1-indexed and row;col => y+1;x+1
        sys.stdout.write(f"{self.CSI}{y+1};{x+1}H")

    def draw_full(self, board, player=None, player_char='●', white_color=True, ghosts=None, ghost_char='●', ghost_color='blue', player_color=None):
        """Draw the entire board buffered and store base matrix for incremental updates."""
        matrix = self._board_to_matrix(board)
        # store base (without player overlay) for future restores
        # Apply colorization to base matrix: walls/borders blue, others default fg on black bg
        def _is_border_char(ch):
            # Colorize all double-line box-drawing glyphs used for walls
            return ch in {'╔', '╗', '╚', '╝', '═', '║', '╦', '╩', '╠', '╣', '╬'}

        colored = []
        for row in matrix:
            crow = []
            for ch in row:
                if ch == '#':
                    crow.append(f"{self.FG_BLUE}{ch}{self.RESET}")
                elif _is_border_char(ch):
                    crow.append(f"{self.FG_BLUE}{ch}{self.RESET}")
                elif ch == '·':
                    # regular pellet: strong white for visibility
                    crow.append(f"{self.FG_WHITE}{ch}{self.RESET}")
                elif ch == '○':
                    # power pellet: bright white
                    crow.append(f"{self.FG_BRIGHT_WHITE}{ch}{self.RESET}")
                else:
                    crow.append(ch)
            colored.append(crow)
        self._base_matrix = [row.copy() for row in colored]

        # Prepare display matrix (base + optional player/ghost overlays) WITHOUT mutating base
        display_matrix = [row.copy() for row in self._base_matrix]
        if player is not None:
            if hasattr(player, 'get_position'):
                px, py = player.get_position()
            else:
                px, py = player
            if 0 <= py < len(display_matrix) and 0 <= px < len(display_matrix[0]):
                if player_color is not None:
                    if player_color == 'red':
                        col = self.FG_BRIGHT_RED
                    elif player_color == 'yellow':
                        col = self.FG_BRIGHT_YELLOW
                    elif player_color == 'blue':
                        col = self.FG_BLUE
                    elif player_color == 'green':
                        col = self.FG_BRIGHT_GREEN
                    else:
                        col = self.FG_BRIGHT_YELLOW
                    matrix_char = f"{col}{player_char}{self.RESET}"
                else:
                    if white_color:
                        # default behavior: bright yellow Pac-Man
                        matrix_char = f"{self.FG_BRIGHT_YELLOW}{player_char}{self.RESET}"
                    else:
                        matrix_char = player_char
                display_matrix[py][px] = matrix_char
                self._player_pos = (px, py)
        # overlay ghosts with requested color
        if ghosts:
            for g in ghosts:
                if hasattr(g, 'get_position'):
                    gx, gy = g.get_position()
                else:
                    gx, gy = g
                if 0 <= gy < len(display_matrix) and 0 <= gx < len(display_matrix[0]):
                    if ghost_color == 'green':
                        col = self.FG_BRIGHT_GREEN
                    elif ghost_color == 'blue':
                        col = self.FG_BLUE
                    else:
                        col = self.FG_BLUE
                    display_matrix[gy][gx] = f"{col}{ghost_char}{self.RESET}"

        # buffered write
        self._hide_cursor()
        # Set black background and default white foreground for the board
        sys.stdout.write(self.BG_BLACK + self.FG_WHITE)
        self._move_cursor(0, 0)
        out = '\n'.join(''.join(row) for row in display_matrix)
        sys.stdout.write(out)
        sys.stdout.flush()

    def update_player(self, prev_pos, new_pos, player_char='●', white_color=True, color=None):
        """Update only the previous and new player positions to avoid full redraw.

        prev_pos/new_pos are (x,y) tuples (0-indexed).
        """
        if self._base_matrix is None:
            # fallback to no-op if we don't have base
            return
        # restore previous cell
        if prev_pos is not None:
            px, py = prev_pos
            if 0 <= py < len(self._base_matrix) and 0 <= px < len(self._base_matrix[0]):
                ch = self._base_matrix[py][px]
                self._move_cursor(px, py)
                sys.stdout.write(ch)
        # draw new cell
        if new_pos is not None:
            nx, ny = new_pos
            if 0 <= ny < len(self._base_matrix) and 0 <= nx < len(self._base_matrix[0]):
                if color == 'green':
                    disp = f"{self.FG_BRIGHT_GREEN}{player_char}{self.RESET}"
                elif color == 'orange':
                    disp = f"{self.FG_ORANGE}{player_char}{self.RESET}"
                elif color == 'blue':
                    disp = f"{self.FG_BLUE}{player_char}{self.RESET}"
                elif color == 'red':
                    disp = f"{self.FG_BRIGHT_RED}{player_char}{self.RESET}"
                elif color == 'yellow' or white_color:
                    disp = f"{self.FG_BRIGHT_YELLOW}{player_char}{self.RESET}"
                else:
                    disp = player_char
                self._move_cursor(nx, ny)
                sys.stdout.write(disp)
        sys.stdout.flush()

    def finalize(self):
        # reset colors and restore cursor
        try:
            sys.stdout.write(self.RESET)
            sys.stdout.flush()
        except Exception:
            pass
        self._show_cursor()

    def set_base_cell(self, x, y, ch):
        """Update the cached base matrix without drawing immediately."""
        if self._base_matrix is None:
            return
        if 0 <= y < len(self._base_matrix) and 0 <= x < len(self._base_matrix[0]):
            self._base_matrix[y][x] = ch

    def show_popup(self, message, min_width=20, color='red'):
        """Draw a centered popup with double-line blue border and colored message.

        color in {'red','green','blue'}
        """
        if not message:
            return
        msg = str(message)
        # Compute box size
        inner_w = max(len(msg) + 2, min_width - 2)
        box_w = min(max(min_width, inner_w + 2), self.width)
        box_h = 5  # top, blank, msg, blank, bottom
        box_w = max(4, box_w)
        # Center within current board area (origin 0,0)
        x0 = max(0, (self.width - box_w) // 2)
        y0 = max(0, (self.height - box_h) // 2)

        # Helpers
        TL, TR, BL, BR, H, V = '╔', '╗', '╚', '╝', '═', '║'
        BLUE = self.FG_BLUE
        RED = self.FG_BRIGHT_RED
        GREEN = self.FG_BRIGHT_GREEN
        RESET = self.RESET
        if color == 'green':
            MSGC = GREEN
        elif color == 'blue':
            MSGC = BLUE
        else:
            MSGC = RED

        def draw(x, y, s):
            self._move_cursor(x, y)
            sys.stdout.write(s)

        # Top border
        draw(x0, y0, f"{BLUE}{TL}{H * (box_w - 2)}{TR}{RESET}")
        # Blank line
        draw(x0, y0 + 1, f"{BLUE}{V}{RESET}{' ' * (box_w - 2)}{BLUE}{V}{RESET}")
        # Message line centered
        pad = max(0, (box_w - 2 - len(msg)) // 2)
        extra = (box_w - 2) - (pad + len(msg))
        draw(x0, y0 + 2, f"{BLUE}{V}{RESET}{' ' * pad}{MSGC}{msg}{RESET}{' ' * extra}{BLUE}{V}{RESET}")
        # Blank line
        draw(x0, y0 + 3, f"{BLUE}{V}{RESET}{' ' * (box_w - 2)}{BLUE}{V}{RESET}")
        # Bottom border
        draw(x0, y0 + 4, f"{BLUE}{BL}{H * (box_w - 2)}{BR}{RESET}")
        sys.stdout.flush()

    # Backwards compatible wrapper
    def render_board(self, board, player=None, player_char='●', white_color=True, ghosts=None, ghost_char='●', ghost_color='blue', player_color=None):
        # draw full for compatibility
        self.draw_full(board, player=player, player_char=player_char, white_color=white_color, ghosts=ghosts, ghost_char=ghost_char, ghost_color=ghost_color, player_color=player_color)

    def render_player(self, player):
        if hasattr(player, 'get_position'):
            x, y = player.get_position()
        else:
            x, y = player
        print(f"Player is at position: ({x}, {y})")

    def draw_score(self, text):
        """Render a score/status line just below the board area."""
        if text is None:
            text = ""
        # Move to first column of the line below the board
        self._move_cursor(0, self.height)
        line = str(text)
        # Pad or truncate to board width
        if len(line) < self.width:
            line = line.ljust(self.width)
        else:
            line = line[: self.width]
        try:
            sys.stdout.write(self.BG_BLACK + self.FG_WHITE + line + self.RESET)
            sys.stdout.flush()
        except Exception:
            pass
