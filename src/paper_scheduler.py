from datetime import datetime, timedelta


class PaperScheduler:

    def __init__(self):

        self.last_report = None

        self.report_interval = timedelta(hours=1)

    def should_generate_report(self):

        now = datetime.now()

        if self.last_report is None:
            self.last_report = now
            return True

        if now - self.last_report >= self.report_interval:

            self.last_report = now

            return True

        return False

    def should_close_candle(self, candle):

        """
        candle คือข้อมูลจาก Binance kline

        Return True เมื่อแท่งปิดแล้ว
        """

        return candle.get("x", False)

    def next_report_time(self):

        if self.last_report is None:
            return datetime.now()

        return self.last_report + self.report_interval