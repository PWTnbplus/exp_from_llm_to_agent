#!/usr/bin/env python3
"""Resume and supervise the unlimited CTFlow model matrix.

This watcher is deliberately explicit about the already-started run IDs.  It
only starts a successor after the predecessor has a complete launcher summary
and the expected result files.  Existing results are never removed or
overwritten; the batch runner's resume mode is used when a run directory is
partially populated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCHMARK_ROOT = Path(r"D:\硕士\prj1_ai_cal\exp\exp1_from_llm_to_agent\benchmark")
CONFIG = ROOT / "configs" / "ctflow_model_matrix.json"


def utc_run_id() -> str:
    return "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_models(group: str) -> list[str]:
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    return [str(row["model_id"]) for row in payload["groups"][group]["models"]]


def model_count(run_dir: Path, model: str) -> int:
    model_dir = run_dir / "models" / model
    if not model_dir.exists():
        return 0
    return sum(1 for path in model_dir.glob("*.json") if path.is_file())


def complete(run_dir: Path, group: str) -> bool:
    summary = run_dir / "parallel_launcher_summary.json"
    if not summary.exists():
        return False
    try:
        json.loads(summary.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return all(model_count(run_dir, model) >= 100 for model in load_models(group))


def run_command(command: list[str], log_path: Path) -> subprocess.Popen[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handle = log_path.open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=handle,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return process


def prepare_run(target: Path, run_id: str, level: int, mode: str, group: str) -> Path:
    run_dir = target / run_id
    if (run_dir / "run_manifest.json").exists():
        return run_dir
    command = [
        sys.executable,
        str(ROOT / "scripts" / "prepare_deepseek_theory_run.py"),
        "--target-dir",
        str(target),
        "--run-id",
        run_id,
        "--level",
        str(level),
        "--mode",
        mode,
        "--max-cost-usd",
        "200",
        "--model-config",
        str(CONFIG),
        "--provider-group",
        group,
    ]
    subprocess.run(command, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)
    return run_dir


def start_batch(run_dir: Path, mode: str, level: int, group: str, benchmark_root: Path) -> subprocess.Popen[str]:
    key_dir = ROOT / "api_key" / ("MiniMax" if group == "minimax" else group)
    command = [
        sys.executable,
        str(ROOT / "scripts" / "run_deepseek_theory_batch.py"),
        "--run-dir",
        str(run_dir),
        "--mode",
        mode,
        "--level",
        str(level),
        "--max-cost-usd",
        "200",
        "--key-dir",
        str(key_dir),
        "--model-config",
        str(CONFIG),
        "--provider-group",
        group,
        "--resume",
    ]
    log_path = benchmark_root / "_supervisor_logs" / f"{run_dir.name}__{mode}.log"
    return run_command(command, log_path)


def audit(run_dir: Path, level: int, mode: str) -> None:
    audit_path = run_dir / "independent_readonly_audit.json"
    if audit_path.exists():
        return
    command = [
        sys.executable,
        str(ROOT / "scripts" / "audit_deepseek_theory_run.py"),
        "--run-dir",
        str(run_dir),
        "--level",
        str(level),
        "--mode",
        mode,
        "--expected-tasks",
        "100",
    ]
    with (run_dir / "audit_stdout.log").open("a", encoding="utf-8") as handle:
        subprocess.run(command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False, text=True)
    timeout_command = [
        sys.executable,
        str(ROOT / "scripts" / "check_matrix_timeouts.py"),
        "--run-dir",
        str(run_dir),
    ]
    with (run_dir / "timeout_check_stdout.log").open("a", encoding="utf-8") as handle:
        subprocess.run(timeout_command, cwd=ROOT, stdout=handle, stderr=subprocess.STDOUT, check=False, text=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-root", type=Path, default=DEFAULT_BENCHMARK_ROOT)
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args()
    benchmark = args.benchmark_root.resolve()
    processes: dict[str, subprocess.Popen[str]] = {}
    prepared: dict[str, Path] = {
        "glm_llm_mid": benchmark / "pure_llm" / "glm_without_lim" / "mid" / "run-20261009T113000Z",
        "glm_agent_mid": benchmark / "agent" / "glm_without_lim" / "mid" / "run-20261009T113000Z",
        "kimi_llm_mid": benchmark / "pure_llm" / "kimi_without_lim" / "mid" / "run-20261009T113000Z",
        "kimi_agent_mid": benchmark / "agent" / "kimi_without_lim" / "mid" / "run-20261009T113000Z",
        "qwen_llm_diff": benchmark / "pure_llm" / "qwen_without_lim" / "diff" / "run-20261009T112000Z",
        "qwen_agent_diff": benchmark / "agent" / "qwen_without_lim" / "diff" / "run-20261009T112000Z",
        "minimax_llm_mid": benchmark / "pure_llm" / "minimax_without_lim" / "mid" / "run-20261009T111500Z",
        "minimax_agent_mid": benchmark / "agent" / "minimax_without_lim" / "mid" / "run-20261009T111500Z",
        "deepseek_llm_diff": benchmark / "pure_llm" / "deepseek_without_lim" / "diff" / "run-20261009T111500Z",
    }

    # These runs were already started manually and are monitored here.
    active: dict[str, tuple[Path, str, int, str]] = {
        "glm_llm_easy": (benchmark / "pure_llm" / "glm_without_lim" / "easy" / "run-20261009T102600Z", "G1", 1, "glm"),
        "kimi_llm_easy": (benchmark / "pure_llm" / "kimi_without_lim" / "easy" / "run-20261009T102700Z", "G1", 1, "kimi"),
        "deepseek_llm_diff": (prepared["deepseek_llm_diff"], "G1", 3, "deepseek"),
        "minimax_llm_mid": (prepared["minimax_llm_mid"], "G1", 2, "minimax"),
        "minimax_agent_mid": (prepared["minimax_agent_mid"], "G4", 2, "minimax"),
        "qwen_llm_diff": (prepared["qwen_llm_diff"], "G1", 3, "qwen"),
        "qwen_agent_diff": (prepared["qwen_agent_diff"], "G4", 3, "qwen"),
    }
    successors = {
        "glm_llm_easy": ("glm_llm_mid", "glm_llm_mid", "glm_agent_mid"),
        "kimi_llm_easy": ("kimi_llm_mid", "kimi_llm_mid", "kimi_agent_mid"),
        "minimax_llm_mid": ("minimax_diff", "minimax_diff", "minimax_diff"),
        "minimax_agent_mid": ("minimax_diff", "minimax_diff", "minimax_diff"),
    }
    audited: set[str] = set()
    while True:
        for name, (run_dir, mode, level, group) in list(active.items()):
            if complete(run_dir, group):
                if name not in audited:
                    audit(run_dir, level, mode)
                    audited.add(name)
                if name in successors and name.endswith("llm_easy"):
                    # Start the matched mid pair only after the pure-LLM easy run is complete.
                    prefix, llm_key, agent_key = successors[name]
                    if prefix == "glm_llm_mid":
                        keys = ("glm_llm_mid", "glm_agent_mid")
                        group_name = "glm"
                    else:
                        keys = ("kimi_llm_mid", "kimi_agent_mid")
                        group_name = "kimi"
                    for key in keys:
                        if key not in processes and not complete(prepared[key], group_name):
                            mode_to_run = "G1" if "llm" in key else "G4"
                            processes[key] = start_batch(prepared[key], mode_to_run, 2, group_name, benchmark)
                            active[key] = (prepared[key], mode_to_run, 2, group_name)
                if name in ("minimax_llm_mid", "minimax_agent_mid"):
                    if all(complete(active[key][0], "minimax") for key in ("minimax_llm_mid", "minimax_agent_mid")):
                        run_id = utc_run_id()
                        for mode_name, mode_to_run in (("llm", "G1"), ("agent", "G4")):
                            key = f"minimax_{mode_name}_diff"
                            if key not in active:
                                target = benchmark / ("pure_llm" if mode_name == "llm" else "agent") / "minimax_without_lim" / "diff"
                                run_dir_new = prepare_run(target, run_id, 3, mode_to_run, "minimax")
                                active[key] = (run_dir_new, mode_to_run, 3, "minimax")
                                processes[key] = start_batch(run_dir_new, mode_to_run, 3, "minimax", benchmark)
        # Start GLM/Kimi mid successors only after both modes are present and complete, then their diff pairs.
        for group in ("glm", "kimi"):
            llm_mid = f"{group}_llm_mid"
            agent_mid = f"{group}_agent_mid"
            if llm_mid in active and agent_mid in active and complete(active[llm_mid][0], group) and complete(active[agent_mid][0], group):
                audit(active[llm_mid][0], 2, "G1")
                audit(active[agent_mid][0], 2, "G4")
                for mode_name, mode_to_run in (("llm", "G1"), ("agent", "G4")):
                    key = f"{group}_{mode_name}_diff"
                    if key not in active:
                        run_id = utc_run_id()
                        target = benchmark / ("pure_llm" if mode_name == "llm" else "agent") / f"{group}_without_lim" / "diff"
                        run_dir_new = prepare_run(target, run_id, 3, mode_to_run, group)
                        active[key] = (run_dir_new, mode_to_run, 3, group)
                        processes[key] = start_batch(run_dir_new, mode_to_run, 3, group, benchmark)
        if all(complete(run_dir, group) for run_dir, _, _, group in active.values()):
            for name, (run_dir, mode, level, _) in active.items():
                if name not in audited:
                    audit(run_dir, level, mode)
            print(json.dumps({"status": "complete", "runs": len(active)}, ensure_ascii=False), flush=True)
            return 0
        time.sleep(max(5, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
