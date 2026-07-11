import asyncio
import os
import signal
from pathlib import Path

from dotenv import load_dotenv

from src.daily_scheduler import DailyScheduler
from src.market_stream_engine import MarketStreamEngine


class Application:

    def __init__(self):
        load_dotenv()

        self.timezone = os.getenv(
            "APP_TIMEZONE",
            "Asia/Bangkok",
        )

        self.report_hour = int(
            os.getenv(
                "DAILY_REPORT_HOUR",
                "0",
            )
        )

        self.report_minute = int(
            os.getenv(
                "DAILY_REPORT_MINUTE",
                "5",
            )
        )

        self.engine = MarketStreamEngine()

        self.scheduler = DailyScheduler(
            report_callback=self._send_daily_report,
            timezone_name=self.timezone,
            report_hour=self.report_hour,
            report_minute=self.report_minute,
        )

        self.shutdown_event = asyncio.Event()
        self.tasks = []

    async def run(self):
        self._prepare_directories()
        self._register_signals()

        print("=" * 72)
        print("TCP CRYPTO AI TRADER")
        print("Mode: PAPER LEVERAGED")
        print("Timezone:", self.timezone)
        print("=" * 72)

        self._notify_system_started()

        self.tasks = [
            asyncio.create_task(
                self.engine.run_forever(),
                name="market_stream",
            ),
            asyncio.create_task(
                self.scheduler.run_forever(),
                name="daily_scheduler",
            ),
        ]

        try:
            await self.shutdown_event.wait()

        finally:
            await self.shutdown()

    async def shutdown(self):
        print("Application shutdown started...")

        for task in self.tasks:
            task.cancel()

        if self.tasks:
            await asyncio.gather(
                *self.tasks,
                return_exceptions=True,
            )

        await self.engine.close()

        print("Application stopped safely.")

    async def _send_daily_report(self):
        paper_trader = (
            self.engine
            .execution_engine
            .router
            .paper_trader
        )

        return paper_trader.send_daily_report()

    def request_shutdown(self):
        if not self.shutdown_event.is_set():
            self.shutdown_event.set()

    def _register_signals(self):
        loop = asyncio.get_running_loop()

        for signal_name in (
            signal.SIGINT,
            signal.SIGTERM,
        ):
            try:
                loop.add_signal_handler(
                    signal_name,
                    self.request_shutdown,
                )
            except NotImplementedError:
                pass

    def _notify_system_started(self):
        try:
            paper_trader = (
                self.engine
                .execution_engine
                .router
                .paper_trader
            )

            paper_trader.line_alert.system_started()

        except Exception as error:
            print(
                "System-start LINE alert failed:",
                error,
            )

    @staticmethod
    def _prepare_directories():
        Path("logs").mkdir(
            parents=True,
            exist_ok=True,
        )


async def main():
    application = Application()
    await application.run()


if __name__ == "__main__":
    asyncio.run(main())