from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v9.common import read_jsonl, write_json
from .run_single_kimi_autonomous import score_all


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    parser.add_argument("--audit-root", type=Path, required=True)
    args = parser.parse_args()
    run_root = args.run_root.resolve()
    audit_root = args.audit_root.resolve()
    scores = score_all(run_root, audit_root)
    summary_path = run_root / "execution_summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["scores"] = scores
    write_json(summary_path, summary)
    manifest_path = run_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["scores"] = scores
    write_json(manifest_path, manifest)
    print(json.dumps(scores, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
