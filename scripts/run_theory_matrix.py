#!/usr/bin/env python3
"""Launch a complete theory-benchmark matrix for a registered G1--G4 mode.

G2 and G3 use the repository's executable fairness contract: G2 has only the
fixed calculator and G3 has exactly two fixed reflection calls.  Each model
gets its own child process, key passed only through the child environment, a
positive local cost cap, and durable stdout/stderr logs.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MODEL_MATRIX = ROOT / "configs" / "ctflow_model_matrix.json"
ALLOWLIST = ROOT / "configs" / "recovery_model_allowlist_20261011.json"
DATA_DIR = ROOT / "data" / "theory_benchmark_v2"
SKILL_ZIP = Path(r"D:\硕士\prj1_ai_cal\exp\exp1_from_llm_to_agent\prompt\whole_pros_g5.zip")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_models(matrix_path: Path, allowlist_path: Path | None) -> list[dict[str, str]]:
    matrix = read_json(matrix_path)
    allowed = None
    if allowlist_path:
        data = read_json(allowlist_path)
        allowed = {str(x) for x in (data.get("models", []) if isinstance(data, dict) else data)}
    rows = []
    for group_name, group in (matrix.get("groups") or {}).items():
        for item in group.get("models") or []:
            if allowed is None or str(item["model_id"]) in allowed:
                rows.append({"provider_group": str(group_name), "key_dir": str(group["key_dir"]), "model_id": str(item["model_id"]), "key_file": str(item["key_file"])})
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("G2", "G3"), required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--model-config", type=Path, default=MODEL_MATRIX)
    parser.add_argument("--model-allowlist", type=Path, default=ALLOWLIST)
    parser.add_argument("--key-root", type=Path, default=ROOT / "api_key")
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--max-cost-usd-per-model", type=float, default=200.0)
    parser.add_argument("--max-output-tokens", type=int, default=512)
    parser.add_argument("--input-price-usd-per-1k", type=float, default=0.001)
    parser.add_argument("--output-price-usd-per-1k", type=float, default=0.003)
    parser.add_argument("--max-workers", type=int, default=14)
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--skill-zip", type=Path, default=SKILL_ZIP)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def launch(args: argparse.Namespace, run_root: Path, model: dict[str, str]) -> dict[str, Any]:
    model_dir = run_root / "models" / model["model_id"]
    model_dir.mkdir(parents=True, exist_ok=True)
    key_path = args.key_root.resolve() / model["key_dir"] / model["key_file"]
    key = key_path.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise RuntimeError(f"invalid key file for {model['model_id']}")
    env = os.environ.copy()
    env.update({
        "LLM_API_KEY": key,
        "LLM_BASE_URL": args.base_url,
        "LLM_MODEL": model["model_id"],
        "LLM_MAX_RETRIES": "0",
        "LLM_COST_PER_1K_INPUT_TOKENS": str(args.input_price_usd_per_1k),
        "LLM_COST_PER_1K_OUTPUT_TOKENS": str(args.output_price_usd_per_1k),
        "LLM_MAX_OUTPUT_TOKENS": str(args.max_output_tokens),
        "PYTHONPATH": str(ROOT / "src"),
        "PYTHONUTF8": "1",
    })
    argv = [
        str(os.fspath(Path(sys.executable))), "-m", "scientific_discovery.cli", "theory-batch",
        "--data-dir", str(args.data_dir.resolve()), "--mode", args.mode, "--provider", "openai",
        "--allow-paid", "--max-cost-usd", str(args.max_cost_usd_per_model),
        "--max-output-tokens", str(args.max_output_tokens), "--limit", "300", "--output", str(model_dir),
    ]
    if args.resume:
        argv.append("--resume")
    stdout_path = model_dir / "host_stdout.log"
    stderr_path = model_dir / "host_stderr.log"
    with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
        process = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=stdout, stderr=stderr, text=True)
        exit_code = process.wait()
    env.pop("LLM_API_KEY", None)
    return {"model_id": model["model_id"], "provider_group": model["provider_group"], "exit_code": exit_code, "output_dir": str(model_dir)}


def main() -> int:
    args = parse_args()
    if not args.allow_paid or args.max_cost_usd_per_model <= 0:
        raise SystemExit("real G2/G3 runs require --allow-paid and a positive per-model cap")
    if args.max_workers <= 0:
        raise SystemExit("max-workers must be positive")
    models = load_models(args.model_config.resolve(), args.model_allowlist.resolve() if args.model_allowlist else None)
    if args.models:
        selected = set(args.models)
        models = [model for model in models if model["model_id"] in selected]
    if not models:
        raise SystemExit("no models selected")
    run_id = args.run_id or f"{args.mode.lower()}-matrix-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    run_root = args.output_root.resolve() / run_id
    provenance = run_root / "provenance"
    skill_zip = args.skill_zip.resolve()
    if args.resume:
        if not args.run_id or not (run_root / "run_manifest.json").is_file():
            raise SystemExit("--resume requires --run-id pointing to an existing matrix run")
        saved = read_json(run_root / "run_manifest.json")
        if saved.get("mode") != args.mode:
            raise SystemExit("resume mode does not match the saved matrix run")
        models = list(saved.get("models") or models)
        # On a resumed matrix, allow a capability-blocked model to be
        # excluded without changing the saved run manifest.  This keeps the
        # blocked model's raw failures auditable while allowing other models
        # to finish in the same run.
        if args.models:
            selected = set(args.models)
            models = [model for model in models if model["model_id"] in selected]
    else:
        run_root.mkdir(parents=True, exist_ok=False)
        provenance.mkdir()
        if skill_zip.is_file():
            shutil.copy2(skill_zip, provenance / skill_zip.name)
        atomic_json(run_root / "run_manifest.json", {
            "run_id": run_id,
            "benchmark": "theory_benchmark_v2",
            "mode": args.mode,
            "group": args.mode,
            "models": models,
            "tasks_per_model": 300,
            "concurrent_models": True,
            "base_url": args.base_url,
            "max_cost_usd_per_model": args.max_cost_usd_per_model,
            "cost_interpretation": "local input/output proxy; provider billing not independently verified",
            "transport_retries": 0,
            "skill_zip": str(skill_zip),
            "data_dir": str(args.data_dir.resolve()),
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "resume_safe": True,
        })
    print(json.dumps({"run_id": run_id, "mode": args.mode, "models": [model["model_id"] for model in models], "output": str(run_root)}, ensure_ascii=False), flush=True)
    results = []
    with ThreadPoolExecutor(max_workers=min(args.max_workers, len(models))) as pool:
        futures = {pool.submit(launch, args, run_root, model): model["model_id"] for model in models}
        for future in as_completed(futures):
            model_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"model_id": model_id, "exit_code": None, "status": "LAUNCH_ERROR", "error_type": type(exc).__name__, "error": str(exc)}
            results.append(result)
            atomic_json(run_root / "parallel_progress.json", {"mode": args.mode, "results": results, "updated_at_utc": datetime.now(timezone.utc).isoformat()})
            print(json.dumps(result, ensure_ascii=False), flush=True)
    summary = {"run_id": run_id, "mode": args.mode, "results": results, "all_processes_exit_zero": all(row.get("exit_code") == 0 for row in results), "finished_at_utc": datetime.now(timezone.utc).isoformat()}
    atomic_json(run_root / "parallel_launcher_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0 if summary["all_processes_exit_zero"] else 3


if __name__ == "__main__":
    raise SystemExit(main())
