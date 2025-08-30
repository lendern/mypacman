class Board:
    def __init__(self, width=128, height=96):
        self.width = width
        self.height = height
        self.board = [[' ' for _ in range(width)] for _ in range(height)]

    def draw_board(self):
        for row in self.board:
            print(''.join(row))

    def update_board(self, player_position):
        # Clear the board
        self.board = [[' ' for _ in range(self.width)] for _ in range(self.height)]
        # Update the player's position on the board
        x, y = player_position
        self.board[y][x] = 'O'  # Representing the player with 'O'
        self.draw_board()