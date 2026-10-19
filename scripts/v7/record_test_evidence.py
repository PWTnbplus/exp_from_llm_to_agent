from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import event, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--events", type=Path, required=True)
    parser.add_argument("--command", required=True)
    parser.add_argument("--result", required=True)
    parser.add_argument("--exit-code", type=int, required=True)
    args = parser.parse_args()
    result = {"command": args.command, "result": args.result, "command_exit_code": args.exit_code, "executed_outside_scheduler": True, "pytest_plugin_autoload_disabled": True}
    write_json(args.output, result)
    event(args.events, "regression_tests_final", "external_test_execution_recorded", args.command, args.exit_code, args.output, None, {"result": args.result}, "independent_read_only_audit")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__": raise SystemExit(main())
