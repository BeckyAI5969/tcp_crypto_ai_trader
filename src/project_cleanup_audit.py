from pathlib import Path


class ProjectCleanupAudit:

    def __init__(self, project_root: str = "."):
        self.root = Path(project_root).resolve()

    def run(self):
        print("=" * 76)
        print("TCP PROJECT CLEANUP AUDIT")
        print("=" * 76)

        self._check_start_files()
        self._scan_generation_artifacts()

    def _check_start_files(self):
        start_file = self.root / "start.py"
        mistaken_file = self.root / "start.py.py"

        print("\n[START FILE CHECK]")

        if start_file.exists():
            print("PASS: start.py exists")
        else:
            print("FAIL: start.py is missing")

        if mistaken_file.exists():
            print("FOUND: start.py.py")
            print(
                "ACTION NEEDED: rename start.py.py -> start.py"
            )

    def _scan_generation_artifacts(self):
        print("\n[GENERATION ARTIFACT SCAN]")

        patterns = [
            "py_compile.compile(",
            "Path(\"/mnt/data/",
            "Path('/mnt/data/",
            "write_text(code",
            "Created and syntax-checked:",
        ]

        found_any = False

        for file_path in self.root.rglob("*.py"):
            if any(
                part in {
                    ".git",
                    ".venv",
                    "venv",
                    "__pycache__",
                    "logs",
                }
                for part in file_path.parts
            ):
                continue

            try:
                lines = file_path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).splitlines()
            except OSError:
                continue

            matches = []

            for line_number, line in enumerate(
                lines,
                start=1,
            ):
                if any(pattern in line for pattern in patterns):
                    matches.append(
                        (line_number, line.strip())
                    )

            if matches:
                found_any = True
                print()
                print(file_path.relative_to(self.root))

                for line_number, line in matches:
                    print(
                        f"  Line {line_number}: {line}"
                    )

        if not found_any:
            print("PASS: no generation artifacts found")


def main():
    ProjectCleanupAudit().run()


if __name__ == "__main__":
    main()