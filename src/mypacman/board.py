class Board:
    """Pure board state. No I/O here.

    Provides a matrix with a double-line border and helpers to get the
    center and clamp positions to the inner area.
    """

    BORDER = {
        'tl': '╔', 'tr': '╗', 'bl': '╚', 'br': '╝', 'h': '═', 'v': '║'
    }

    def __init__(self, width=80, height=24):
        self.width = max(3, int(width))
        self.height = max(3, int(height))
        self._build_board()

    def _build_board(self):
        self.inner_width = self.width - 2
        self.inner_height = self.height - 2
        self._board = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        # horizontal lines
        for x in range(1, self.width - 1):
            self._board[0][x] = self.BORDER['h']
            self._board[self.height - 1][x] = self.BORDER['h']
        # vertical lines
        for y in range(1, self.height - 1):
            self._board[y][0] = self.BORDER['v']
            self._board[y][self.width - 1] = self.BORDER['v']
        # corners
        self._board[0][0] = self.BORDER['tl']
        self._board[0][self.width - 1] = self.BORDER['tr']
        self._board[self.height - 1][0] = self.BORDER['bl']
        self._board[self.height - 1][self.width - 1] = self.BORDER['br']

    def get_matrix(self):
        """Return a shallow copy of the board matrix (rows copied)."""
        return [row.copy() for row in self._board]

    def center_position(self):
        cx = 1 + (self.inner_width // 2)
        cy = 1 + (self.inner_height // 2)
        return (cx, cy)

    def clamp_to_inner(self, x, y):
        x = max(1, min(self.width - 2, int(x)))
        y = max(1, min(self.height - 2, int(y)))
        return (x, y)