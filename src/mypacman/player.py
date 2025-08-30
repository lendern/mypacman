class Player:
    def __init__(self, initial_position=(0, 0)):
        x, y = initial_position
        self.x = int(x)
        self.y = int(y)

    def get_position(self):
        return (self.x, self.y)

    def set_position(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def move(self, dx, dy):
        self.x += int(dx)
        self.y += int(dy)