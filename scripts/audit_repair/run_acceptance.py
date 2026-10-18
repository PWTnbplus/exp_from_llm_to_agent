"""Run and persist the repair-cycle acceptance commands."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--root", type=Path, default=Path.cwd())
    args = p.parse_args()
    commands = [
        [sys.executable, "-X", "utf8", "-m", "pytest", "-q", "tests/test_six_blocker_repair.py", "tests/test_cost_ledger.py", "tests/test_provider_trace.py", "tests/test_g7_protocol.py", "tests/test_g7_trace_q_consistency.py", "tests/test_v3_observability.py"],
        [sys.executable, "-X", "utf8", "-m", "pytest", "-q"],
        [sys.executable, "-X", "utf8", "-m", "py_compile", "scripts/run_g7_failure_localization.py", "scripts/audit_repair/cost_ledger.py", "scripts/audit_repair/math_verifier.py", "scripts/audit_repair/verify_q.py", "scripts/audit_repair/six_blocker_audit.py", "scripts/audit_repair/review_six_blockers.py", "scripts/audit_repair/v3_audit.py", "scripts/audit_repair/review_v3_audit.py", "scripts/v3/q_v2.py", "scripts/v3/lu_v2.py", "scripts/v3/observability_smoke.py"],
    ]
    records = []
    all_pass = True
    for command in commands:
        proc = subprocess.run(command, cwd=args.root, text=True, capture_output=True, encoding="utf-8", errors="replace")
        all_pass = all_pass and proc.returncode == 0
        records.append({"command": command, "exit_code": proc.returncode, "stdout_tail": proc.stdout[-4000:], "stderr_tail": proc.stderr[-4000:], "status": "PASS" if proc.returncode == 0 else "FAIL"})
    source_files = [args.root / item for item in (
        "scripts/run_g7_failure_localization.py", "src/scientific_discovery/models/provider.py",
        "scripts/audit_repair/cost_ledger.py", "scripts/audit_repair/math_verifier.py",
        "scripts/audit_repair/verify_q.py", "scripts/audit_repair/six_blocker_audit.py",
        "scripts/audit_repair/review_six_blockers.py", "scripts/audit_repair/v3_audit.py",
        "scripts/audit_repair/review_v3_audit.py", "scripts/v3/q_v2.py", "scripts/v3/lu_v2.py",
        "scripts/v3/observability_smoke.py",
    )]
    result = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "pass": all_pass, "runs": records, "code_sha256": {str(path.relative_to(args.root)).replace("\\", "/"): sha(path) for path in source_files}}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"pass": all_pass, "runs": len(records), "out": str(args.out)}))
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
