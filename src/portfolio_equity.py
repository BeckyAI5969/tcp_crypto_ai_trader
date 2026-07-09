import pandas as pd


class PortfolioEquity:

    def __init__(self):
        self.records = []

    def add(
        self,
        timestamp,
        cash,
        equity,
        exposure,
        open_positions,
    ):
        self.records.append(
            {
                "time": timestamp,
                "cash": cash,
                "equity": equity,
                "exposure": exposure,
                "open_positions": open_positions,
            }
        )

    def dataframe(self):

        if len(self.records) == 0:
            return pd.DataFrame(
                columns=[
                    "time",
                    "cash",
                    "equity",
                    "exposure",
                    "open_positions",
                ]
            )

        return pd.DataFrame(self.records)

    def save(self, path):

        df = self.dataframe()

        df.to_csv(
            path,
            index=False,
        )

        return df