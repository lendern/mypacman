def get_input():
    import sys
    import tty
    import termios

    def get_char():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

    return get_char()

def process_input(input_char):
    movement = {
        'w': 'up',
        's': 'down',
        'a': 'left',
        'd': 'right',
    }
    return movement.get(input_char, None)