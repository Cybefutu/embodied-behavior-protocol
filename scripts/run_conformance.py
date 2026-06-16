#!/usr/bin/env python3
"""Run the deterministic OEBP conformance suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from oebp import OEBPConformanceSuite  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    args = parser.parse_args()

    report = OEBPConformanceSuite(ROOT).run()
    payload = report.to_dict()
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        status = "PASS" if report.passed else "FAIL"
        print(f"[{status}] OEBP conformance suite")
        print(f"Lifecycle scenarios: {report.lifecycle_scenarios}")
        print(f"Failure/recovery scenarios: {report.failure_recovery_scenarios}")
        for check in report.checks:
            check_status = "PASS" if check.passed else "FAIL"
            print(f"[{check_status}] {check.id}: {check.message}")
    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
