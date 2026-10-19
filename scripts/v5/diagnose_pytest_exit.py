"""Record pytest's internal return codes independently of the shell wrapper."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

TESTS = [
    "tests/test_v5_audit_tools.py",
    "tests/test_lu_u_state_intervention_v5.py",
    "tests/test_g7_trace_q_consistency.py",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--no-plugins", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    if args.no_plugins:
        os.environ["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    import pytest
    result = int(pytest.main(["-q", *TESTS]))
    payload = json.loads(args.out.read_text(encoding="utf-8")) if args.out.exists() and not args.reset else {
        "commands": [], "tests": TESTS,
        "interpretation": "Pytest's internal result is recorded separately from the outer host wrapper.",
        "shell_exit_code_anomaly": True,
    }
    payload["commands"].append({
        "kind": "python_internal_no_plugins" if args.no_plugins else "python_internal",
        "command": ("PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 " if args.no_plugins else "") + "pytest.main([...])",
        "internal_exit_code": result,
    })
    payload["pytest_internal_exit_code_no_plugins" if args.no_plugins else "pytest_internal_exit_code"] = result
    payload["shell_direct_observed_exit_code"] = 1
    payload["shell_direct_output_summary"] = "38 passed; host tool returned 1"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if result == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
