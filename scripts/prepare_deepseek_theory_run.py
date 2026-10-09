#!/usr/bin/env python3
"""Prepare a provenance-safe output directory for one DeepSeek difficulty run."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil


MODELS = (
    "deepseek-r1-distill-qwen-1.5b",
    "deepseek-v3.2",
    "deepseek-v4.1-flash",
    "deepseek-r1-distill-qwen-14b",
    "deepseek-r1-distill-qwen-32b",
    "deepseek-r1-distill-qwen-7b",
)

PROMPT_FILES = (
    Path(r"D:\硕士\prj1_ai_cal\exp\exp1_from_llm_to_agent\prompt\whole_pros.md"),
    Path(r"D:\硕士\prj1_ai_cal\exp\exp1_from_llm_to_agent\prompt\whole_pros.zip"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--target-dir", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--level", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--reference-run-dir", type=Path)
    parser.add_argument("--mode", choices=("G1", "G4"), default="G1")
    parser.add_argument("--max-cost-usd", type=float, default=2.0)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--input-price-usd-per-1k", type=float, default=0.001)
    parser.add_argument("--output-price-usd-per-1k", type=float, default=0.003)
    parser.add_argument("--data-dir", type=Path, default=root / "data" / "theory_benchmark_v2")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    run_dir = (args.target_dir / args.run_id).resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    provenance = run_dir / "provenance"
    provenance.mkdir()

    prompt_records = []
    for source in PROMPT_FILES:
        record = {"source": str(source), "copied": source.is_file()}
        if source.is_file():
            destination = provenance / ("prompt_" + source.name)
            shutil.copy2(source, destination)
            record.update({"destination": destination.name, "sha256": sha256(destination)})
        prompt_records.append(record)

    copied_data = []
    for name in ("public_tasks.json", "manifest.json"):
        source = args.data_dir.resolve() / name
        destination = provenance / ("benchmark_v2_" + name)
        if source.is_file():
            shutil.copy2(source, destination)
            copied_data.append({"source": str(source), "destination": destination.name, "sha256": sha256(destination)})

    if args.reference_run_dir:
        source_preflight = args.reference_run_dir.resolve() / "preflight"
        if source_preflight.is_dir():
            shutil.copytree(source_preflight, run_dir / "preflight")

    is_agent = args.mode == "G4"
    manifest = {
        "run_id": args.run_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "theory_benchmark_v2",
        "difficulty_level": args.level,
        "difficulty_label": {1: "easy", 2: "mid", 3: "diff"}[args.level],
        "mode": args.mode,
        "group": args.mode,
        "runner": "single_agent" if is_agent else "llm_only",
        "provider": "openai-compatible",
        "base_url": "https://token.ctflow.cn/v1",
        "models": list(MODELS),
        "tasks_expected_per_model": 100,
        "concurrent_models": True,
        "max_output_tokens": args.max_output_tokens,
        "max_cost_usd_per_model": args.max_cost_usd,
        "cost_control": "positive hard cap enforced by the CLI; usage cost is a local proxy, not confirmed CTFlow billing",
        "input_price_usd_per_1k_proxy": args.input_price_usd_per_1k,
        "output_price_usd_per_1k_proxy": args.output_price_usd_per_1k,
        "transport_retries": 0,
        "tools_enabled": is_agent,
        "allowed_tools": ["calculate_expression"] if is_agent else [],
        "max_model_calls_per_task": 8 if is_agent else 1,
        "answer_key_copied": False,
        "prompt_provenance": prompt_records,
        "benchmark_provenance": copied_data,
        "local_key_directory": "api_key/deepseek (keys read only into child process environment)",
    }
    (run_dir / "run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"run_dir": str(run_dir), "manifest": manifest}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
