import sys
import tty
import termios
import select
import os


class InputHandler:
    """Non-blocking input handler using termios + select.

    Recognizes arrow keys and 'q' to quit. Call start() before use and stop()
    to restore terminal state.
    """

    ARROW_MAP = {
        b'\x1b[A': (0, -1),  # up
        b'\x1b[B': (0, 1),   # down
        b'\x1b[C': (1, 0),   # right
        b'\x1b[D': (-1, 0),  # left
    }

    def __init__(self):
        self._orig_settings = None
        # don't call fileno() at construction time; tests may redirect stdin
        self._fd = None
        # last real direction seen (dx,dy)
        self._last_dir = None
        # if True, emit one extra movement on next poll to bridge OS repeat delay
        self._pending_gap_fill = False
        # last raw sequence seen for the last_dir (bytes), used to adjust counts
        self._last_seq = None
        # True if we emitted a gap-fill movement (so next real read should
        # ignore one occurrence to avoid double-counting)
        self._gap_filled_applied = False

    def start(self):
        # obtain fd lazily (safer for pytest where stdin may be redirected)
        if self._fd is None:
            try:
                self._fd = sys.stdin.fileno()
            except Exception:
                self._fd = None
        if self._fd is not None:
            self._orig_settings = termios.tcgetattr(self._fd)
            tty.setcbreak(self._fd)

    def stop(self):
        if self._orig_settings is not None and self._fd is not None:
            termios.tcsetattr(self._fd, termios.TCSADRAIN, self._orig_settings)
            self._orig_settings = None

    def get_direction(self, timeout=0.0):
        dr, _, _ = select.select([sys.stdin], [], [], timeout)
        if not dr:
            # if we recently saw a real key press, provide one extra movement to
            # bridge the OS repeat delay, then stop until real repeats arrive
            if self._pending_gap_fill and self._last_dir is not None:
                # mark that we applied the gap-fill so the next real read can
                # ignore one occurrence to avoid double-counting
                self._pending_gap_fill = False
                self._gap_filled_applied = True
                return self._last_dir
            return (0, 0)

        # Read and drain all available bytes so we don't process repeat
        # events across multiple ticks. Read a large chunk to capture queued
        # repeats (arrow keys produce 3-byte sequences repeated).
        try:
            b = os.read(self._fd, 4096)
        except Exception:
            try:
                b = sys.stdin.buffer.read1(4096)
            except Exception:
                b = sys.stdin.read(4096).encode('utf-8', errors='ignore')

        if not b:
            return None

        # If multiple sequences are present, pick the last arrow sequence seen.
        last_vec = None
        last_idx = -1
        prev_last_seq = self._last_seq
        for seq, vec in self.ARROW_MAP.items():
            occ = b.count(seq)
            if occ <= 0:
                continue
            idx = b.rfind(seq)
            if idx > last_idx:
                last_idx = idx
                last_vec = (seq, vec)

        if last_vec is not None:
            seq, vec = last_vec
            # If we just applied a gap-fill and this read corresponds to the
            # same sequence, consume it without emitting movement, but reset
            # flags so subsequent ticks continue smoothly.
            if self._gap_filled_applied and prev_last_seq == seq:
                self._gap_filled_applied = False
                self._pending_gap_fill = True
                self._last_dir = vec
                self._last_seq = seq
                return (0, 0)
            # Normal path: emit movement and schedule a gap-fill for the next tick
            self._last_dir = vec
            self._last_seq = seq
            self._gap_filled_applied = False
            self._pending_gap_fill = True
            return vec

        # handle single chars: q to quit (check bytes for 'q' or 'Q')
        if b.find(b'q') != -1 or b.find(b'Q') != -1:
            return None

        return (0, 0)
