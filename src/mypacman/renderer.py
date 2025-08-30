import sys


class Renderer:
    """Efficient terminal renderer.

    - Uses buffered writes to print the full board once.
    - Keeps a base matrix (board without player) and supports incremental
      updates for the player cell to avoid clearing the whole screen every frame.
    - Hides the cursor while drawing to reduce flicker.
    """

    CSI = '\x1b['

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

    def draw_full(self, board, player=None, player_char='●', white_color=True):
        """Draw the entire board buffered and store base matrix for incremental updates."""
        matrix = self._board_to_matrix(board)
        # store base (without player overlay) for future restores
        self._base_matrix = [row.copy() for row in matrix]

        # overlay player for initial draw
        if player is not None:
            if hasattr(player, 'get_position'):
                px, py = player.get_position()
            else:
                px, py = player
            if 0 <= py < len(matrix) and 0 <= px < len(matrix[0]):
                if white_color:
                    WHITE = '\x1b[97m'
                    RESET = '\x1b[0m'
                    matrix[py][px] = f"{WHITE}{player_char}{RESET}"
                else:
                    matrix[py][px] = player_char
                self._player_pos = (px, py)

        # buffered write
        self._hide_cursor()
        self._move_cursor(0, 0)
        out = '\n'.join(''.join(row) for row in matrix)
        sys.stdout.write(out)
        sys.stdout.flush()

    def update_player(self, prev_pos, new_pos, player_char='●', white_color=True):
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
                if white_color:
                    WHITE = '\x1b[97m'
                    RESET = '\x1b[0m'
                    disp = f"{WHITE}{player_char}{RESET}"
                else:
                    disp = player_char
                self._move_cursor(nx, ny)
                sys.stdout.write(disp)
        sys.stdout.flush()

    def finalize(self):
        # restore cursor
        self._show_cursor()

    # Backwards compatible wrapper
    def render_board(self, board, player=None, player_char='●', white_color=True):
        # draw full for compatibility
        self.draw_full(board, player=player, player_char=player_char, white_color=white_color)

    def render_player(self, player):
        if hasattr(player, 'get_position'):
            x, y = player.get_position()
        else:
            x, y = player
        print(f"Player is at position: ({x}, {y})")