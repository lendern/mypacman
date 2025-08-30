class Ghost:
    def __init__(self, initial_position=(0, 0)):
        x, y = initial_position
        self.x = int(x)
        self.y = int(y)
        # current direction (dx,dy); defaults to 0,0 until set by game
        self.dx = 0
        self.dy = 0

    def get_position(self):
        return (self.x, self.y)

    def set_position(self, x, y):
        self.x = int(x)
        self.y = int(y)

    def move(self, dx, dy):
        self.x += int(dx)
        self.y += int(dy)
        self.dx, self.dy = int(dx), int(dy)

    def get_direction(self):
        return (self.dx, self.dy)

    def set_direction(self, dx, dy):
        self.dx, self.dy = int(dx), int(dy)
