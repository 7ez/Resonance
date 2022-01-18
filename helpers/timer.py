import time

class Timer:
    def __init__(self) -> None:
        self.start_time = 0
        self.end_time = 0

    def start(self) -> None:
        self.start_time = time.time()

    def end(self) -> float:
        if not self.end_time: self.end_time = time.time()
        return self.end_time - self.start_time

    def reset(self) -> None:
        self.start = 0
        self.end = 0

    def time(self) -> str:
        time = self.end()
        if time < 1:
            return str(round(time * 1000, 2)) + "ms"
        else:
            return str(round(time, 2)) + "s"