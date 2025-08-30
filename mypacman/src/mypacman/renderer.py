class Renderer:
    def __init__(self, width=128, height=96):
        self.width = width
        self.height = height

    def render_board(self, board):
        for row in board:
            print("".join(row))

    def render_player(self, player):
        x, y = player.get_position()
        print(f"Player is at position: ({x}, {y})")