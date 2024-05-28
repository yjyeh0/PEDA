class QMemory:
    def __init__(self, capacity):
        self.capacity = capacity
        self.reset()

    def append(self, critic):
        if self.capacity > 0:
            self._append(critic)
    def _append(self, critic):
        if len(self.buffer) < self.capacity:
            self.buffer.append(critic)
        else:
            self.buffer[self._p] = critic
        self._n = min(self._n + 1, self.capacity)
        self._p = (self._p + 1) % self.capacity

    def reset(self):
        self._n = 0
        self._p = 0
        self.full = False
        self.buffer = []
    def sample(self):
        return self.buffer