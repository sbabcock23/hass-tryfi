"""Fail if any single integration module is below the coverage floor.

--cov-fail-under checks the total, which is exactly the number that hides the
problem: one module can rot to nothing while the average stays comfortable,
and the quality-scale rule this repo claims to meet asks for the figure per
module rather than overall. So the aggregate gate stays and this runs after
it, against the same run's JSON report.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FLOOR = 95.0
PACKAGE = "custom_components/tryfi"


def main(report: str = "coverage.json") -> int:
    path = Path(report)
    if not path.exists():
        print(f"no coverage report at {path}; did pytest run with --cov-report=json?")
        return 1

    files = json.loads(path.read_text())["files"]
    mine = {
        name: data["summary"]["percent_covered"]
        for name, data in files.items()
        if PACKAGE in name.replace("\\", "/")
    }
    if not mine:
        print(f"the coverage report names no files under {PACKAGE}")
        return 1

    below = {name: pct for name, pct in mine.items() if pct < FLOOR}
    for name, pct in sorted(mine.items()):
        mark = "FAIL" if name in below else "ok  "
        print(f"{mark} {pct:6.2f}%  {name}")

    if below:
        print(f"\n{len(below)} module(s) below the {FLOOR:.0f}% floor:")
        for name, pct in sorted(below.items()):
            print(f"  {name} at {pct:.2f}%")
        return 1

    print(f"\nall {len(mine)} modules at or above {FLOOR:.0f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
