import asyncio
from datetime import datetime, time, timedelta
from typing import Awaitable, Callable, Optional
from zoneinfo import ZoneInfo


class DailyScheduler:
    """
    Runs the daily reporting callback once per day in the selected timezone.

    Default:
        Timezone: Asia/Bangkok
        Report time: 00:05

    The five-minute delay avoids generating the report exactly at midnight
    while log files may still be receiving the final events of the day.
    """

    def __init__(
        self,
        report_callback: Callable[[], bool | Awaitable[bool]],
        timezone_name: str = "Asia/Bangkok",
        report_hour: int = 0,
        report_minute: int = 5,
        retry_minutes: int = 10,
        maximum_retries: int = 3,
    ):
        if not 0 <= report_hour <= 23:
            raise ValueError(
                "report_hour must be between 0 and 23"
            )

        if not 0 <= report_minute <= 59:
            raise ValueError(
                "report_minute must be between 0 and 59"
            )

        if retry_minutes <= 0:
            raise ValueError(
                "retry_minutes must be greater than zero"
            )

        if maximum_retries < 0:
            raise ValueError(
                "maximum_retries cannot be negative"
            )

        self.report_callback = report_callback
        self.timezone = ZoneInfo(timezone_name)
        self.report_time = time(
            hour=report_hour,
            minute=report_minute,
        )

        self.retry_minutes = retry_minutes
        self.maximum_retries = maximum_retries

        self.last_run_date = None
        self.last_run_at = None
        self.last_success = None
        self.last_error = None

    def next_run_at(
        self,
        now: Optional[datetime] = None,
    ) -> datetime:

        now = now or datetime.now(self.timezone)

        if now.tzinfo is None:
            now = now.replace(tzinfo=self.timezone)
        else:
            now = now.astimezone(self.timezone)

        candidate = datetime.combine(
            now.date(),
            self.report_time,
            tzinfo=self.timezone,
        )

        if candidate <= now:
            candidate += timedelta(days=1)

        return candidate

    async def run_once(self) -> bool:
        self.last_run_at = datetime.now(
            self.timezone
        ).isoformat()

        self.last_error = None

        try:
            result = self.report_callback()

            if asyncio.iscoroutine(result):
                result = await result

            self.last_success = bool(result)

            if self.last_success:
                self.last_run_date = datetime.now(
                    self.timezone
                ).date().isoformat()

            return self.last_success

        except Exception as error:
            self.last_success = False
            self.last_error = (
                f"{type(error).__name__}: {error}"
            )

            print(
                "Daily report failed:",
                self.last_error,
            )

            return False

    async def run_with_retry(self) -> bool:
        attempts = self.maximum_retries + 1

        for attempt in range(1, attempts + 1):
            success = await self.run_once()

            if success:
                print(
                    "Daily report sent successfully:",
                    self.last_run_at,
                )
                return True

            if attempt < attempts:
                print(
                    "Retrying daily report in",
                    self.retry_minutes,
                    "minutes",
                )

                await asyncio.sleep(
                    self.retry_minutes * 60
                )

        print(
            "Daily report failed after",
            attempts,
            "attempt(s)",
        )

        return False

    async def run_forever(self):
        print(
            "Daily Scheduler started:",
            self.timezone.key,
            self.report_time.strftime("%H:%M"),
        )

        while True:
            now = datetime.now(self.timezone)
            next_run = self.next_run_at(now)

            wait_seconds = max(
                (next_run - now).total_seconds(),
                1.0,
            )

            print(
                "Next daily report:",
                next_run.isoformat(),
            )

            await asyncio.sleep(wait_seconds)
            await self.run_with_retry()

    def summary(self) -> dict:
        return {
            "timezone": self.timezone.key,
            "report_time":
                self.report_time.strftime("%H:%M"),
            "next_run_at":
                self.next_run_at().isoformat(),
            "last_run_date":
                self.last_run_date,
            "last_run_at":
                self.last_run_at,
            "last_success":
                self.last_success,
            "last_error":
                self.last_error,
            "retry_minutes":
                self.retry_minutes,
            "maximum_retries":
                self.maximum_retries,
        }


async def main():
    from src.paper_trader import PaperTrader

    trader = PaperTrader()

    scheduler = DailyScheduler(
        report_callback=trader.send_daily_report,
        timezone_name="Asia/Bangkok",
        report_hour=0,
        report_minute=5,
    )

    await scheduler.run_forever()


if __name__ == "__main__":
    asyncio.run(main())