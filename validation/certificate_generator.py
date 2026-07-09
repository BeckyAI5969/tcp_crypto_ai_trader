from pathlib import Path
import json
from datetime import datetime


class CertificateGenerator:

    def __init__(self):

        self.output = Path("validation")
        self.output.mkdir(exist_ok=True)

    def generate(self, validation_result):

        certificate = {

            "project": "TCP Crypto AI Trader",

            "version": "Sprint 10.5",

            "generated_at": datetime.now().isoformat(),

            "overall_pass": validation_result["score"] == 100,

            "score": validation_result["score"],

            "passed": validation_result["passed"],

            "total": validation_result["total"],

            "result": validation_result["result"],

            "issues": validation_result["issues"],

        }

        file = self.output / "Regression_Certificate.json"

        with open(file, "w", encoding="utf-8") as f:

            json.dump(
                certificate,
                f,
                indent=4,
                ensure_ascii=False,
            )

        print("=" * 70)
        print("TCP CRYPTO AI TRADER")
        print("REGRESSION CERTIFICATE")
        print("=" * 70)
        print(f"Score : {certificate['score']}%")
        print(f"Overall PASS : {certificate['overall_pass']}")
        print("=" * 70)

        return file