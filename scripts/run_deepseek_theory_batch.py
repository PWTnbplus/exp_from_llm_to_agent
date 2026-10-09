#!/usr/bin/env python3
"""Run the six local DeepSeek Level-1 G1 batches concurrently.

Keys are read only into child-process environments.  They are never placed in
argv, output files, or the process status report.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time


MODELS = (
    ("deepseek-r1-distill-qwen-1.5b.txt", "deepseek-r1-distill-qwen-1.5b"),
    ("deepseek-v3point2.txt", "deepseek-v3.2"),
    ("deepseek-v4.1-flash.txt", "deepseek-v4.1-flash"),
    ("exp1-deepseek-r1-distill-qwen-14b.txt", "deepseek-r1-distill-qwen-14b"),
    ("exp1-deepseek-r1-distill-qwen-32b.txt", "deepseek-r1-distill-qwen-32b"),
    ("exp1-deepseek-r1-distill-qwen-7b.txt", "deepseek-r1-distill-qwen-7b"),
)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=root / "data" / "theory_benchmark_v2")
    parser.add_argument("--key-dir", type=Path, default=root / "api_key" / "deepseek")
    parser.add_argument("--max-cost-usd", type=float, default=2.0)
    parser.add_argument("--max-output-tokens", type=int, default=512)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    run_dir = args.run_dir.resolve()
    data_dir = args.data_dir.resolve()
    key_dir = args.key_dir.resolve()
    processes: list[tuple[str, subprocess.Popen[str], object, object]] = []
    started = datetime.now(timezone.utc).isoformat()
    for key_name, model_id in MODELS:
        output_dir = run_dir / "models" / model_id
        output_dir.mkdir(parents=True, exist_ok=True)
        key = (key_dir / key_name).read_text(encoding="utf-8").strip()
        if not key.startswith("sk-"):
            raise RuntimeError(f"invalid local key format for {key_name}")
        env = os.environ.copy()
        env.update(
            {
                "LLM_API_KEY": key,
                "LLM_BASE_URL": "https://token.ctflow.cn/v1",
                "LLM_MODEL": model_id,
                "LLM_MAX_RETRIES": "0",
                "LLM_COST_PER_1K_INPUT_TOKENS": "0.005",
                "LLM_COST_PER_1K_OUTPUT_TOKENS": "0.015",
                "LLM_MAX_OUTPUT_TOKENS": str(args.max_output_tokens),
                "PYTHONPATH": str(root / "src"),
                "PYTHONUTF8": "1",
            }
        )
        argv = [
            "python",
            "-m",
            "scientific_discovery.cli",
            "theory-batch",
            "--data-dir",
            str(data_dir),
            "--level",
            "1",
            "--limit",
            "100",
            "--mode",
            "G1",
            "--provider",
            "openai",
            "--allow-paid",
            "--max-cost-usd",
            str(args.max_cost_usd),
            "--max-output-tokens",
            str(args.max_output_tokens),
            "--output",
            str(output_dir),
        ]
        stdout_handle = (output_dir / "host_stdout.log").open("w", encoding="utf-8")
        stderr_handle = (output_dir / "host_stderr.log").open("w", encoding="utf-8")
        process = subprocess.Popen(
            argv,
            cwd=root,
            env=env,
            stdout=stdout_handle,
            stderr=stderr_handle,
            text=True,
        )
        del env["LLM_API_KEY"]
        del key
        processes.append((model_id, process, stdout_handle, stderr_handle))
        print(f"STARTED {model_id} pid={process.pid}", flush=True)

    while any(process.poll() is None for _, process, _, _ in processes):
        running = [model for model, process, _, _ in processes if process.poll() is None]
        print("RUNNING " + ", ".join(running), flush=True)
        time.sleep(15)

    finished = datetime.now(timezone.utc).isoformat()
    results = []
    for model_id, process, stdout_handle, stderr_handle in processes:
        stdout_handle.close()
        stderr_handle.close()
        results.append(
            {
                "model_id": model_id,
                "pid": process.pid,
                "exit_code": process.returncode,
                "output_dir": str(Path("models") / model_id),
            }
        )
    summary = {
        "run_id": run_dir.name,
        "started_at_utc": started,
        "finished_at_utc": finished,
        "parallel": True,
        "models": results,
        "all_processes_exit_zero": all(row["exit_code"] == 0 for row in results),
    }
    (run_dir / "parallel_launcher_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["all_processes_exit_zero"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
