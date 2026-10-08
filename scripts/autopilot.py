#!/usr/bin/env python3
"""Bounded Codex build/review/test/commit/push supervisor.

This is a local orchestrator, not a hosted background service. Never runs paid
scientific API experiments by itself. Needs authenticated Codex + Git credentials.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Any

REPO = "PWTnbplus/exp_from_llm_to_agent"
BRANCH = "autopilot/scientific-law-discovery"
SKILL = ".agents/skills/scientific-law-autopilot/SKILL.md"
DEVELOPMENT = ".agents/skills/scientific-law-autopilot/references/development_original.md"
SUPERVISION = ".agents/skills/scientific-law-autopilot/references/supervision_original.md"
SENSITIVE_PATH = re.compile(r"(^|/)(\.env(?:\..*)?|.*\.(?:pem|p12|pfx|key)|id_rsa|id_ed25519|credentials(?:\.[^/]*)?|secrets?(?:\.[^/]*)?)$", re.I)
SENSITIVE_CONTENT = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|\b(?:ghp_|github_pat_|sk-proj-|sk_live_)[A-Za-z0-9_-]{8,}|(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*[:=]\s*['\"][^'\"]{12,}['\"]", re.I)


def run(argv: list[str], *, cwd: Path, timeout: int = 1800, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    # The repository includes UTF-8 Chinese source specifications.  Do not
    # decode Git/model output with the Windows locale (often GBK), or the
    # safety gate itself can crash before it inspects staged content.
    p = subprocess.run(argv, cwd=cwd, text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       timeout=timeout, env=env)
    if check and p.returncode:
        raise RuntimeError(f"Command failed ({p.returncode}): {shlex.join(argv)}\n{p.stdout[-3500:]}")
    return p


def git(root: Path, *args: str, check: bool = True) -> str:
    return run(["git", *args], cwd=root, timeout=120, check=check).stdout.strip()


def verify_origin(root: Path, remote: str) -> None:
    url = git(root, "remote", "get-url", remote)
    valid = {
        f"https://github.com/{REPO}.git", f"https://github.com/{REPO}",
        f"git@github.com:{REPO}.git", f"ssh://git@github.com/{REPO}.git",
    }
    if url not in valid:
        raise RuntimeError(f"Refusing to push to unexpected remote: {url!r}, expected {REPO}")


def ensure_branch(root: Path, branch: str) -> None:
    current = git(root, "branch", "--show-current")
    if current == branch:
        return
    # Do not silently switch away from an unrelated feature branch.
    if current not in {"", "main", "master"}:
        raise RuntimeError(f"Already on unrelated branch {current!r}; switch manually")
    has_branch = run(["git", "show-ref", "--verify", f"refs/heads/{branch}"], cwd=root, check=False).returncode == 0
    if has_branch:
        git(root, "switch", branch)
    else:
        git(root, "switch", "-c", branch)


def staged_files(root: Path) -> list[str]:
    raw = run(["git", "diff", "--cached", "--name-only", "-z"], cwd=root).stdout
    return [x for x in raw.split("\0") if x]


def check_staged_safety(root: Path) -> None:
    files = staged_files(root)
    bad = [f for f in files if SENSITIVE_PATH.search(f)]
    if bad:
        raise RuntimeError(f"Sensitive paths staged, refusing commit: {bad}")
    for f in files:
        p = root / f
        if p.exists() and p.is_file() and p.stat().st_size > 5 * 1024 * 1024:
            raise RuntimeError(f"Oversized artifact staged (>5 MiB): {f}")
    patch = git(root, "diff", "--cached", "--unified=0", "--no-ext-diff", check=True)
    additions = "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
    if SENSITIVE_CONTENT.search(additions):
        raise RuntimeError("Potential credential/private key detected in staged additions; aborting commit")
    git(root, "diff", "--cached", "--check")


def codex(root: Path, prompt: str, out: Path, *, read_only: bool, timeout: int) -> str:
    # The CLI flag is verified locally by the operator, not assumed available on all versions.
    cmd = ["codex", "exec", "--sandbox", "read-only" if read_only else "workspace-write",
           "--output-last-message", str(out), prompt]
    result = run(cmd, cwd=root, timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"Codex exit {result.returncode}: {result.stdout[-5000:]}")
    if not out.exists() or not out.read_text(encoding="utf-8").strip():
        raise RuntimeError("Codex did not return an auditable final message")
    return out.read_text(encoding="utf-8")


def parse_review(raw: str) -> dict[str, Any]:
    content = raw.strip()
    if content.startswith("```"):
        content = "\n".join(content.splitlines()[1:-1])
    try:
        obj = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Reviewer did not produce strict JSON: {e}") from e
    if not isinstance(obj, dict) or obj.get("status") not in {"PASS", "FAIL", "BLOCKED"}:
        raise ValueError("Review requires status PASS, FAIL or BLOCKED")
    if not isinstance(obj.get("findings"), list) or not isinstance(obj.get("project_complete"), bool):
        raise ValueError("Review requires findings[] and project_complete boolean")
    for f in obj["findings"]:
        if not isinstance(f, dict) or f.get("severity") not in {"P0", "P1", "P2", "P3"}:
            raise ValueError("Each finding must include severity P0/P1/P2/P3")
        if not f.get("evidence") or not f.get("remediation"):
            raise ValueError("Each finding needs evidence and remediation")
    if obj["status"] == "PASS" and any(f["severity"] in {"P0", "P1"} for f in obj["findings"]):
        raise ValueError("Reviewer contradiction: PASS with blocking P0/P1")
    return obj


def test_project(root: Path, test_cmd: str, timeout: int) -> dict[str, Any]:
    # Command is trusted as the operator's explicit CLI argument; never derived from LLM output.
    argv = shlex.split(test_cmd)
    if not argv:
        raise RuntimeError("Empty test command")
    result = run(argv, cwd=root, timeout=timeout, check=False)
    return {"command": argv, "exit_code": result.returncode, "output_tail": result.stdout[-6000:]}


def commit_push(root: Path, *, remote: str, branch: str, cycle: int, wip: bool, push: bool) -> dict[str, Any]:
    git(root, "add", "-A")
    check_staged_safety(root)
    files = staged_files(root)
    if not files:
        return {"status": "NO_CHANGES", "push": "NOT_APPLICABLE"}
    msg = f"{'wip' if wip else 'feat'}: scientific discovery autopilot cycle {cycle:02d} audit"
    git(root, "commit", "-m", msg)
    sha = git(root, "rev-parse", "HEAD")
    result: dict[str, Any] = {"status": "COMMITTED", "sha": sha, "files": files, "push": "SKIPPED"}
    if push:
        verify_origin(root, remote)
        p = run(["git", "push", "-u", remote, f"HEAD:refs/heads/{branch}"], cwd=root, timeout=120, check=False)
        if p.returncode:
            result["push"] = "BLOCKED"
            result["error"] = p.stdout[-3000:]
            raise RuntimeError(f"Commit {sha} created locally, but push BLOCKED:\n{p.stdout[-3000:]}")
        result["push"] = "PUSHED"
    return result


def develop_prompt(cycle: int, feedback: str = "") -> str:
    return f"""You are the DEV phase of the scientific-law-autopilot skill (cycle {cycle}).
Read {SKILL}, {DEVELOPMENT} and {SUPERVISION} IN FULL before editing. Check repo state.
Implement the next highest-value concrete missing deliverable in the development spec; prioritize NewtonBench real adapter, LLM-only nonadaptive frozen-plan isolation, single Agent, independent scoring and adversarial tests. Do not rebuild upstream simulators. Run meaningful targeted tests. Never run paid experiment batches or touch main. No git commit/push yourself: the trusted host supervisor handles committing every cycle. This cycle must create measurable code/tests/doc improvements; do not merely plan or claim DONE. Preserve existing changes. Blockers need reproducible evidence and explicit next step.
Previous independent review/test feedback: {feedback[:9000] or 'No prior findings.'}
Conclude with a brief summary of changed paths and actually run tests."""


def reviewer_prompt(test: dict[str, Any], cycle: int) -> str:
    return f"""You are the INDEPENDENT ADVERSARIAL REVIEW phase of scientific-law-autopilot cycle {cycle}.
Read {SKILL} and both complete reference specifications at {DEVELOPMENT} and {SUPERVISION}.
Inspect the actual source code, diff and executed test report; DO NOT edit files or stage/commit anything.
Actively try to falsify correctness: frozen-plan observation-swap LLM isolation, no tools, Agent feedback branching, NewtonBench simulator really called, hidden answer access, evaluator edge cases, matched budget, mock-vs-real labels, data/credentials, running tests, experimental statistics. An untested or absent feature is NOT TESTED / incomplete, NOT PASS.
Independent deterministic test result supplied by host: {json.dumps(test, ensure_ascii=False)[:7000]}
Return ONLY a strict JSON object with exactly these required keys:
{{"status":"PASS|FAIL|BLOCKED", "project_complete":false, "findings":[{{"severity":"P0|P1|P2|P3","evidence":"path:line, command output, or explicit NOT TESTED", "remediation":"specific fix + test"}}], "verified_commands":["commands actually run"], "summary":"evidence-based audit"}}.
If missing anything from all hard gates G0-G7, project_complete MUST be false. Do not set PASS on P0/P1. Do not invent executed commands or green tests."""



MANDATORY_COMPLETION_PATHS = (
    "src/scientific_discovery/benchmark/newtonbench_adapter.py",
    "src/scientific_discovery/runners/llm_only.py",
    "src/scientific_discovery/runners/single_agent.py",
    "src/scientific_discovery/evaluation/validation.py",
    "tests/test_llm_isolation.py",
    "tests/test_agent_actions.py",
    "tests/test_budget.py",
    "tests/test_no_leakage.py",
    "tests/test_evaluator.py",
    "tests/test_reproducibility.py",
    "docs/open_source_audit.md",
    "docs/llm_non_agent_guarantee.md",
    "docs/experiment_protocol.md",
    "docs/evaluation_protocol.md",
    "docs/reproducibility.md",
    "docs/limitations.md",
)


def completion_inventory(root: Path) -> list[str]:
    """Necessary but not sufficient for passing all scientific gates."""
    return [x for x in MANDATORY_COMPLETION_PATHS if not (root / x).is_file() or not (root / x).stat().st_size]


def create_pr_if_available(root: Path, branch: str) -> str:
    """Open a draft PR after verified completion; never merge it."""
    if not shutil.which("gh"):
        return "BLOCKED: gh CLI unavailable; open PR manually on GitHub"
    argv = ["gh", "pr", "create", "--repo", REPO, "--head", branch, "--base", "main", "--draft",
            "--title", "Scientific-law discovery: reviewed autonomous experiment platform",
            "--body", "Self-audited Codex implementation. See docs/audits/ and reproducibility protocol. Human review required before merging."]
    result = run(argv, cwd=root, timeout=120, check=False)
    if result.returncode:
        return "BLOCKED: " + result.stdout[-1000:]
    return "CREATED: " + result.stdout.strip()

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycles", type=int, default=12)
    p.add_argument("--repairs", type=int, default=1)
    p.add_argument("--test-cmd", default="python -m pytest -q")
    p.add_argument("--timeout", type=int, default=1800, help="per Codex/test command seconds")
    p.add_argument("--branch", default=BRANCH)
    p.add_argument("--remote", default="origin")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-push", action="store_true", help="ONLY for local testing; violates remote-delivery goal")
    args = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.cycles < 1 or args.repairs < 0:
        p.error("cycles >= 1 and repairs >= 0 required")
    if not (root / ".git").exists():
        raise RuntimeError("Install this bundle in a git clone (root must contain .git)")
    if not (root / SKILL).exists() or not (root / DEVELOPMENT).exists() or not (root / SUPERVISION).exists():
        raise RuntimeError("Missing skill or original reference documents")
    verify_origin(root, args.remote)
    if args.dry_run:
        print(json.dumps({"repo": str(root), "remote": git(root, "remote", "get-url", args.remote),
                          "planned_branch": args.branch, "cycles": args.cycles,
                          "codex_present": bool(shutil.which("codex")), "dry_run": True}, ensure_ascii=False, indent=2))
        return 0
    if not shutil.which("codex"):
        raise RuntimeError("codex CLI is not installed/authenticated; see AUTOPILOT_SETUP.md")
    if staged_files(root):
        raise RuntimeError("Preexisting staged changes: commit or unstage them before autopilot")
    ensure_branch(root, args.branch)
    audits = root / "docs" / "audits"
    audits.mkdir(parents=True, exist_ok=True)
    feedback = ""
    completed = False
    for n in range(1, args.cycles + 1):
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        cycle_dir = audits / f"cycle-{stamp}-{n:02d}"
        cycle_dir.mkdir(parents=True, exist_ok=True)
        test: dict[str, Any] = {"exit_code": 999, "output_tail": "NOT TESTED"}
        review: dict[str, Any] = {"status": "BLOCKED", "project_complete": False, "findings": []}
        phases: list[str] = []
        try:
            codex(root, develop_prompt(n, feedback), cycle_dir / "developer.txt", read_only=False, timeout=args.timeout)
            phases.append("DEVELOPED")
            test = test_project(root, args.test_cmd, args.timeout)
            phases.append("TESTED")
            for attempt in range(args.repairs + 1):
                raw = codex(root, reviewer_prompt(test, n), cycle_dir / f"review-{attempt}.txt",
                            read_only=True, timeout=args.timeout)
                review = parse_review(raw)
                phases.append(f"REVIEWED_{attempt}")
                blockers = [f for f in review["findings"] if f["severity"] in {"P0", "P1"}]
                if (test["exit_code"] == 0 and not blockers) or attempt >= args.repairs:
                    break
                detail = json.dumps({"test": test, "review": review}, ensure_ascii=False)
                codex(root, develop_prompt(n, "MANDATORY FIX BEFORE NEXT AUDIT: " + detail),
                      cycle_dir / f"repair-{attempt}.txt", read_only=False, timeout=args.timeout)
                test = test_project(root, args.test_cmd, args.timeout)
                phases.append(f"REPAIRED_{attempt}")
        except (RuntimeError, ValueError, subprocess.TimeoutExpired) as e:
            phases.append("BLOCKED")
            feedback = f"Last cycle blocked: {type(e).__name__}: {str(e)[:2000]}"
            review = {"status": "BLOCKED", "project_complete": False,
                      "findings": [{"severity": "P1", "evidence": feedback,
                                    "remediation": "Resolve environment/format/test blocker; rerun audit"}]}
        missing = completion_inventory(root)
        if review["project_complete"] and missing:
            review["status"] = "FAIL"
            review["project_complete"] = False
            review["findings"].append({
                "severity": "P1", "evidence": "Mandatory completion artifacts missing: " + ", ".join(missing),
                "remediation": "Implement and run the missing actual source/test/doc artifacts; do not create placeholders"})
        wip = not (test["exit_code"] == 0 and review["status"] == "PASS" and not any(
            f["severity"] in {"P0", "P1"} for f in review["findings"]))
        summary = {"cycle": n, "timestamp_utc": stamp, "phases": phases, "test": test,
                   "review": review, "ready": not wip,
                   "mock_is_not_science_evidence": True, "paid_experiments_launched_by_runner": False,
                   "mandatory_completion_missing": missing}
        (cycle_dir / "audit.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        try:
            pushed = commit_push(root, remote=args.remote, branch=args.branch, cycle=n,
                                 wip=wip, push=not args.no_push)
        except RuntimeError as e:
            print(f"CYCLE {n} PUSH/COMMIT BLOCKED: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"cycle": n, "commit": pushed, "review_status": review["status"],
                          "tests_exit": test["exit_code"], "complete": review["project_complete"]}, ensure_ascii=False))
        feedback = json.dumps({"review": review, "test": test}, ensure_ascii=False)[-8500:]
        if not wip and review["project_complete"]:
            completed = True
            break
    if completed:
        if args.no_push:
            print("LOCAL ONLY: cannot create remote PR when --no-push was used")
        else:
            print("PR STATUS:", create_pr_if_available(root, args.branch))
        print("ALL GATES REPORTED PASS. Human review remains required; do NOT merge main automatically.")
        return 0
    print("BOUNDED RUN INCOMPLETE: see pushed audit reports; rerun for more supervised cycles.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"AUTOPILOT BLOCKED: {exc}", file=sys.stderr)
        raise SystemExit(2)
