from __future__ import annotations

import json
import subprocess
import sys


def test_terminal_retry_manifest_counts_missing_state(tmp_path) -> None:
    plan = tmp_path / "plan.jsonl"
    states = tmp_path / "states.jsonl"
    out = tmp_path / "retry.jsonl"
    manifest = tmp_path / "manifest.json"
    plan.write_text(
        json.dumps({"run_id": "run-present", "checkpoint_id": "cp-1"}) + "\n"
        + json.dumps({"run_id": "run-missing", "checkpoint_id": "cp-2"}) + "\n",
        encoding="utf-8",
    )
    states.write_text(json.dumps({"run_id": "run-present", "status": "provider_error"}) + "\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_g7_terminal_retry.py",
            "--plan",
            str(plan),
            "--states",
            str(states),
            "--out",
            str(out),
            "--manifest",
            str(manifest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["retry_rows"] == 2
    assert data["source_terminal_status_counts"] == {"provider_error": 1, "missing_state": 1}
    assert data["pooling_prohibited"] is True
    assert result.returncode == 0
