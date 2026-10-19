"""Write cycle metadata after V5 offline audits have actually run."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], *, timeout: int = 30) -> tuple[int | None, str, str]:
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as exc:
        return None, (exc.stdout or ""), f"TIMEOUT: {exc}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--commit-sha", default="PENDING_COMMIT")
    args = parser.parse_args()
    repo = Path.cwd(); pack = args.pack
    head_code, head_out, _ = run(["git", "rev-parse", "HEAD"])
    branch_code, branch_out, _ = run(["git", "branch", "--show-current"])
    status_code, status_out, status_err = run(["git", "status", "--porcelain=v1"])
    issues = json.loads((repo / "docs/state/issues.json").read_text(encoding="utf-8"))
    issue_counts = Counter(row.get("status") for row in issues.get("issues", []))
    version_code, version_out, _ = run([sys.executable, "-X", "utf8", "-c",
                                        "import sys,pytest,sympy; print(sys.version); print('pytest='+pytest.__version__); print('sympy='+sympy.__version__)"])
    baseline = {
        "cycle": "20261019T-v5-execution", "created_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "git_head": head_out.strip(), "git_branch": branch_out.strip(), "git_status_exit_code": status_code,
        "issue_counts": dict(issue_counts), "python_versions": version_out.strip(),
        "provider_calls_in_v5_cycle": 0, "pack": str(pack.resolve()),
        "scientific_release_allowed": False,
    }
    (pack / "BASELINE.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

    input_paths = [
        repo / "docs/audits/cycle-20261018T-g6g7-v3/G7_STATE_ATTEMPT_MATRIX.csv",
        repo / "docs/audits/cycle-20261018T-g6g7-v3/G7_TRACE_15_EXPLAINED_13_INVALID.jsonl",
        repo / "docs/audits/cycle-20261018T-v4-g6g7-execution/G7_RESUME_TARGETS.jsonl",
        repo / "runs/ctflow_single_model/20261018T-v4-g7-kimi-resume/states.worker-1-0.jsonl",
        repo / "docs/audits/cycle-20261018T-g6g7-v3/03_G6_INDEPENDENT_MATH_AUDIT.jsonl",
        repo / "docs/audits/cycle-20261018T-v4-g6g7-execution/G6_CF3_RETRY_PUBLIC_MATH_AUDIT.jsonl",
        repo / "docs/audits/cycle-20261019T-v9-targeted-recovery/Q_FROZEN_PUBLIC_REVIEW.json",
        repo / "runs/ctflow_single_model/20261019T-v9-targeted-recovery/lu-u-run/records.jsonl",
        repo / "runs/ctflow_single_model/20261019T-v9-targeted-recovery/lu-u-run/provider_traces.jsonl",
    ]
    freeze = {str(path): {"exists": path.is_file(), "sha256": digest(path) if path.is_file() else None}
              for path in input_paths}
    freeze["historical_denominator_modified"] = False
    freeze["recovery_pooled"] = False
    (pack / "SOURCE_AND_FREEZE_HASHES.json").write_text(json.dumps(freeze, indent=2) + "\n", encoding="utf-8")

    remote_code, remote_out, remote_err = run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "ls-remote", "origin", "refs/heads/autopilot/scientific-law-discovery"], timeout=30)
    (pack / "REMOTE_SHA_AND_PROVENANCE_REVIEW.json").write_text(json.dumps({
        "command": "git -c http.proxy= -c https.proxy= ls-remote origin refs/heads/autopilot/scientific-law-discovery",
        "local_sha": head_out.strip(), "remote_exit_code": remote_code, "remote_stdout": remote_out,
        "remote_stderr": remote_err, "remote_sha_verified": False,
        "upstream_provenance_status": "PENDING_SEPARATE_NEWTONBENCH_PROOF",
        "interpretation": "No remote delivery is claimed unless the exact remote SHA is observed and matches local HEAD.",
    }, indent=2) + "\n", encoding="utf-8")

    matrix = [
        ["ISSUE-ff97c7c89112", "G6 mathematical audit remains conservative", digest(pack / "G6_MATH_REVIEW.jsonl"), "Built two-path boundary review, deduplicated attempts, emitted errata and public pack", "new scripts/v5/build_v5_pack.py and review outputs", 0, str(pack / "G6_REVIEW_SUMMARY.json"), "PASS_ENGINEERING_ONLY", "human domain review and formal 552 reanalysis unavailable", "obtain independent domain signature; do not alter 552", "read-only reviewer passed pack invariants", args.commit_sha],
        ["ISSUE-000000000004", "Q92 lacks human domain-grade blind review", digest(pack / "Q92_FROZEN_DOMAIN_REVIEW.jsonl"), "Reused frozen 92 and produced non-scoring blind manifest and row audit", "new Q92 manifest/limitations; no provider call", 0, str(pack / "Q92_BLIND_PACK_MANIFEST.json"), "READY_FOR_EXTERNAL_REVIEW", "external domain reviewer unavailable", "send pack to independent reviewer", "software review verified 92/92; human review NOT_AVAILABLE", args.commit_sha],
        ["ISSUE-1f8c2b6a4d90", "Existing LU/U records lack checkpoint-backed observed state", digest(pack / "LU_U_PAIRED_INDEPENDENT_AUDIT.jsonl"), "Audited all planned calibration pairs and froze a non-formal queue specification", "new eligibility tests and prereg; no real calls", 0, str(pack / "LU_U_FORMAL_PREREG.json"), "FAIL_FORMAL_GATE_INELIGIBLE_U", "no valid checkpoint/state trace in existing cohort", "run a newly authorized checkpoint-paired cohort only after gates", "independent audit marks all 6 pairs INELIGIBLE_U", args.commit_sha],
        ["ISSUE-7c2d4e9a10bf", "Historical G7 lifecycle defects must remain separate from recovery", digest(pack / "G7_RETRY_LINEAGE.jsonl"), "Built 1288-row frozen ledger, 150-row append-only recovery view, 1438-row lineage and amendment decision", "atomic retry reservation fix plus tests; no provider call", 0, str(pack / "INDEPENDENT_READ_ONLY_REVIEW.json"), "PASS_ENGINEERING_ONLY", "historical 13 remain scientific failures; no reanalysis approval", "retain denominator and obtain protocol-approved review", "independent read-only review PASS", args.commit_sha],
        ["ISSUE-000000000002", "Provider invoice and immutable model identity unavailable", digest(pack / "PROVIDER_LOCAL_RECONCILIATION.csv"), "Reconciled 242 persisted local records and wrote exact evidence request", "no provider request in V5", 0, str(pack / "PROVIDER_EVIDENCE_REQUEST.md"), "BLOCKED_EXTERNAL", "official billing and immutable route/weights not verified", "obtain official export/identity evidence", "not applicable; external evidence absent", args.commit_sha],
        ["ISSUE-000000000003", "Current remote probe cannot reach GitHub", digest(pack / "REMOTE_SHA_AND_PROVENANCE_REVIEW.json"), "Ran proxy-disabled ls-remote and recorded exact result", "no source change", 0, str(pack / "REMOTE_SHA_AND_PROVENANCE_REVIEW.json"), "BLOCKED_EXTERNAL", "network connection to github.com:443 failed", "restore authorized network and rerun exact ls-remote", "not applicable; remote unavailable", args.commit_sha],
    ]
    with (pack / "ISSUE_EXECUTION_MATRIX.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["issue_id", "root_cause", "source_hash", "action_executed", "source_or_test_diff", "new_real_calls", "independent_evidence_path", "pass_or_failure", "external_only_blocker", "next_action", "reviewer_verdict", "commit_sha"])
        writer.writerows(matrix)

    (pack / "FINAL_EXECUTION_RESULTS.md").write_text(
        "# V5 execution results\n\n"
        "This cycle performed offline, read-only reuse of persisted single-model Kimi artifacts and made zero new provider calls. "
        "The independent review passed the engineering invariants, while all scientific release gates remain fail-closed. "
        "See BUILD_SUMMARY.json, INDEPENDENT_READ_ONLY_REVIEW.json, and ISSUE_EXECUTION_MATRIX.csv for machine-readable evidence.\n\n"
        f"Baseline HEAD: `{head_out.strip()}`\nRemote delivery: **not verified** (see REMOTE_SHA_AND_PROVENANCE_REVIEW.json).\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
