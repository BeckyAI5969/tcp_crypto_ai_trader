import json
import sys
from pathlib import Path
from datetime import datetime

STATUS = {
    "timestamp": datetime.now().isoformat(),
    "status": "PASS",
    "checks": {}
}

root = Path(".")

def check(name, condition, detail=""):
    STATUS["checks"][name] = {
        "ok": bool(condition),
        "detail": detail,
    }
    if not condition:
        STATUS["status"] = "FAIL"

check("start.py", (root / "start.py").exists(), "Application entry point")
check(".env", (root / ".env").exists(), "Runtime configuration")
check("requirements.txt", (root / "requirements.txt").exists(), "Dependencies")
check("logs", (root / "logs").exists(), "Log directory")
check("src", (root / "src").exists(), "Source directory")

state = root / "logs" / "paper_state.json"
check("paper_state", state.exists(), "Recovery state file")

print(json.dumps(STATUS, indent=4))

if STATUS["status"] != "PASS":
    sys.exit(1)