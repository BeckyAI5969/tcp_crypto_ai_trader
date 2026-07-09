import json
from pathlib import Path
from datetime import datetime

import pandas as pd


class FeatureImportanceLab:

    def __init__(self):
        self.dataset_path = Path("research/market_dataset.csv")
        self.importance_path = Path("research/feature_importance.csv")
        self.strategy_path = Path("research/best_strategy.json")
        self.report_path = Path("research/best_strategy_report.txt")

        self.target_col = "label_16"

    def run(self):
        print("=" * 70)
        print("TCP AI FEATURE IMPORTANCE LAB")
        print("=" * 70)

        if not self.dataset_path.exists():
            print("market_dataset.csv not found.")
            return

        df = pd.read_csv(self.dataset_path)

        features = [
            "ema20_gt_ema50",
            "ema50_gt_ema200",
            "price_gt_ema200",
            "macd_gt_signal",
            "macd_hist_positive",
            "volume_gt_ma20",
            "rsi_oversold",
            "rsi_neutral",
            "rsi_overbought",
            "atr_pct",
            "bb_width_pct",
        ]

        features = [f for f in features if f in df.columns]

        df = df.dropna(subset=features + ["future_return_16"])

        rows = []

        for feature in features:
            active = df[df[feature] == 1]
            inactive = df[df[feature] == 0]

            if len(active) == 0:
                continue

            active_return = active["future_return_16"].mean()
            inactive_return = inactive["future_return_16"].mean() if len(inactive) > 0 else 0

            buy_edge_rate = (
                len(active[active[self.target_col] == "BUY_EDGE"]) / len(active) * 100
            )

            score = active_return - inactive_return

            rows.append({
                "feature": feature,
                "active_rows": len(active),
                "active_return_16": round(active_return, 6),
                "inactive_return_16": round(inactive_return, 6),
                "edge_score": round(score, 6),
                "buy_edge_rate": round(buy_edge_rate, 2),
            })

        result = pd.DataFrame(rows)
        result = result.sort_values(
            by=["edge_score", "buy_edge_rate"],
            ascending=False
        )

        result.to_csv(self.importance_path, index=False)

        top_features = result.head(5)["feature"].tolist()

        strategy = {
            "created_at": datetime.now().isoformat(),
            "strategy_name": "TCP_AI_FEATURE_SELECTED_V1",
            "timeframe": "15m",
            "target": "future_return_16",
            "top_features": top_features,
            "logic": "BUY when majority of top features are active",
            "minimum_active_features": max(2, len(top_features) // 2),
        }

        self.strategy_path.write_text(
            json.dumps(strategy, indent=4),
            encoding="utf-8"
        )

        report = f"""
======================================================================
TCP AI FEATURE IMPORTANCE REPORT
======================================================================

Dataset        : {self.dataset_path}
Rows           : {len(df)}
Features Tested: {len(features)}

Top Features
{result.head(20).to_string(index=False)}

Best Strategy
{json.dumps(strategy, indent=4)}

Files
Feature CSV    : {self.importance_path}
Strategy JSON  : {self.strategy_path}
Report TXT     : {self.report_path}

======================================================================
"""

        self.report_path.write_text(report, encoding="utf-8")

        print(report)


def main():
    FeatureImportanceLab().run()


if __name__ == "__main__":
    main()