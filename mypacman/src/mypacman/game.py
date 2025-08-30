class Game:
    def __init__(self):
        self.is_running = False

    def start_game(self):
        self.is_running = True
        print("Game started!")

    def update_game(self):
        if self.is_running:
            print("Game is updating...")

    def end_game(self):
        self.is_running = False
        print("Game ended!")