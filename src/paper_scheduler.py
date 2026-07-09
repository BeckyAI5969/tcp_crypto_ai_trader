from datetime import datetime
import time


class PaperScheduler:

    def __init__(self, interval_seconds=60):
        self.interval_seconds = interval_seconds
        self.running = False
        self.iteration = 0

    def start(self):
        self.running = True
        print("=" * 70)
        print("TCP PAPER TRADING SCHEDULER STARTED")
        print("=" * 70)

    def stop(self):
        self.running = False
        print("=" * 70)
        print("TCP PAPER TRADING SCHEDULER STOPPED")
        print("=" * 70)

    def tick(self):
        self.iteration += 1

        return {
            "iteration": self.iteration,
            "timestamp": datetime.utcnow().isoformat(),
        }

    def run(self, callback):

        self.start()

        try:
            while self.running:

                event = self.tick()

                callback(event)

                time.sleep(self.interval_seconds)

        except KeyboardInterrupt:

            self.stop()