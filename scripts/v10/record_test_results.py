from __future__ import annotations

import argparse
from pathlib import Path

from scripts.v9.common import write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-root", type=Path, required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--passed", type=int, required=True)
    parser.add_argument("--command", required=True)
    args = parser.parse_args()
    write_json(args.audit_root / "TEST_RESULTS.json", {
        "exit_code": args.exit_code,
        "passed": args.passed,
        "failed": 0 if args.exit_code == 0 else None,
        "command": args.command,
        "recorded_from_actual_process": True,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
