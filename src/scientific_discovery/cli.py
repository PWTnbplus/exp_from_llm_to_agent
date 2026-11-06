"""Command-line entry points for the controlled experiment."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Any

from .benchmark.base import TaskSpec
from .benchmark.task_registry import enumerate_newtonbench_tasks, stratified_select
from .benchmark.newtonbench_adapter import NewtonBenchOracle
from .environment.budget import BudgetLedger, BudgetLimits
from .evaluation.metrics import summarize_by, vldr
from .evaluation.figures import render_three_panel
from .evaluation.statistics import paired_bootstrap_ci
from .evaluation.validation import ValidationEnvironment
from .experiment.recorder import ResultRecorder
from .experiment.runner import run_one
from .models.provider import MockLLMProvider, OpenAICompatibleProvider


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "third_party" / "NewtonBench"


def _task_from_dict(data: dict[str, Any]) -> TaskSpec:
    return TaskSpec(**data)


def _mock_law() -> dict[str, Any]:
    return {
        "hypothesis": "The response is proportional to the product of the two masses and inversely proportional to distance to a non-integer power.",
        "equation": "F = C * mass1 * mass2 / distance**1.5",
        "variables": ["mass1", "mass2", "distance"],
        "parameters": {"C": 6.674e-5, "distance_exponent": 1.5},
        "evidence": ["Mock smoke-test response; not a scientific result."],
        "predictions": [],
        "limitations": ["Mock provider; do not use as formal evidence."],
        "code": "def discovered_law(mass1, mass2, distance):\n    return 6.674e-5 * mass1 * mass2 / (distance ** 1.5)",
    }


def _generic_engineering_provider(task: TaskSpec, repo_root: Path, runner_name: str) -> MockLLMProvider:
    """Return a valid-protocol Mock response for every direct task.

    The zero-law is intentionally not a scientific result. It exercises task
    loading, action validation, simulator execution, persistence and blind
    evaluation across the full manifest while preserving a failed score.
    """
    probe_budget = BudgetLedger(BudgetLimits(max_experiments=1, max_api_calls=1))
    probe = NewtonBenchOracle(task, repo_root, probe_budget)
    names = list(probe.get_action_schema().get("required", []))
    action = {name: 1.0 for name in names}
    code = "def discovered_law(" + ", ".join(names) + "):\n    return 0.0"
    law = {"hypothesis": "engineering-validation placeholder", "equation": "0", "variables": names, "parameters": {}, "evidence": [], "predictions": [], "limitations": ["Mock engineering validation only"], "code": code}
    if runner_name == "llm_only":
        return MockLLMProvider([{"experiments": [action]}, law])
    return MockLLMProvider([{"action": action, "hypothesis": "engineering validation"}, {"final_law": law}])


def _load_manifest(path: Path, repo_root: Path, limit: int | None = None) -> list[TaskSpec]:
    if path.exists():
        raw = json.loads(path.read_text(encoding="utf-8"))
        tasks = [_task_from_dict(row) for row in raw]
    else:
        tasks = stratified_select(enumerate_newtonbench_tasks(repo_root), limit or 12, 42)
    return tasks[:limit] if limit else tasks


def engineering_validation(repo_root: Path, manifest: Path, output_dir: Path, limit: int = 12) -> dict[str, Any]:
    tasks = _load_manifest(manifest, repo_root, limit)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for task in tasks:
        for runner_name in ("llm_only", "single_agent"):
            target = output_dir / f"{runner_name}_{task.task_id.replace(':', '__')}.json"
            if target.exists():
                continue
            provider = _generic_engineering_provider(task, repo_root, runner_name)
            result, validation = run_one(task, repo_root, provider, runner_name, BudgetLimits(max_experiments=1, max_api_calls=4), output_dir)
            rows.append({"task_id": task.task_id, "runner": runner_name, "status": result.status, "validated_success": validation.get("validated_success", False), "provider_calls": len(provider.calls)})
    for path in output_dir.glob("*.json"):
        if path.name == "engineering_summary.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            rows.append({"task_id": data.get("task_id"), "runner": data.get("runner"), "status": data.get("status"), "validated_success": data.get("validation", {}).get("validated_success", False), "provider_calls": len(data.get("metadata", {}).get("provider_trace", []))})
        except (OSError, json.JSONDecodeError):
            continue
    unique = {(row["task_id"], row["runner"]): row for row in rows}
    rows = list(unique.values())
    summary = {"engineering_only": True, "mock_only": True, "tasks": len(tasks), "runner_rows": len(rows), "completed_rows": sum(row["status"] == "completed" for row in rows), "rows": rows}
    (output_dir / "engineering_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def smoke_test(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    task = TaskSpec(
        task_id="newtonbench:m0_gravity:easy:v0:vanilla_equation",
        source="NewtonBench", module="m0_gravity", domain="gravitation",
        law_complexity="easy", system_complexity="vanilla_equation", law_variant="v0",
        split="smoke", seed=42,
    )
    actions = [
        {"mass1": 1.0, "mass2": 2.0, "distance": 1.0},
        {"mass1": 2.0, "mass2": 3.0, "distance": 2.0},
        {"mass1": 4.0, "mass2": 1.5, "distance": 3.0},
    ]
    plan_response = {"experiments": actions}
    llm_provider = MockLLMProvider([plan_response, _mock_law()])
    llm_result, llm_validation = run_one(task, repo_root, llm_provider, "llm_only", BudgetLimits(max_experiments=3, max_api_calls=4), output_dir)

    agent_provider = MockLLMProvider([
        {"action": actions[0], "hypothesis": "initial hypothesis"},
        {"action": actions[1], "hypothesis": "updated hypothesis"},
        {"final_law": _mock_law()},
    ])
    agent_result, agent_validation = run_one(task, repo_root, agent_provider, "single_agent", BudgetLimits(max_experiments=3, max_api_calls=4), output_dir)
    summary = {
        "mock_only": True,
        "task_id": task.task_id,
        "llm_only": {"status": llm_result.status, "validation": llm_validation, "provider_calls": len(llm_provider.calls)},
        "single_agent": {"status": agent_result.status, "validation": agent_validation, "provider_calls": len(agent_provider.calls)},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "smoke_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="scientific-discovery")
    parser.add_argument("--repo-root", type=Path, default=UPSTREAM)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("audit")
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--limit", type=int, default=12)
    prepare.add_argument("--seed", type=int, default=42)
    prepare.add_argument("--output", type=Path, default=Path("task_manifest.json"))
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--output", type=Path, default=Path("results/smoke"))
    engineering = sub.add_parser("engineering-test")
    engineering.add_argument("--manifest", type=Path, default=Path("task_manifest.json"))
    engineering.add_argument("--limit", type=int, default=12)
    engineering.add_argument("--output", type=Path, default=Path("results/engineering_validation"))
    pilot = sub.add_parser("pilot")
    pilot.add_argument("--manifest", type=Path, default=Path("task_manifest.json"))
    pilot.add_argument("--runner", choices=["llm_only", "single_agent", "both"], default="both")
    pilot.add_argument("--provider", choices=["mock", "openai"], default="mock")
    pilot.add_argument("--allow-paid", action="store_true")
    pilot.add_argument("--resume", action="store_true")
    pilot.add_argument("--limit", type=int, default=12)
    pilot.add_argument("--max-cost-usd", type=float, default=None)
    pilot.add_argument("--output", type=Path, default=Path("results/pilot"))
    run = sub.add_parser("run")
    run.add_argument("--runner", choices=["llm_only", "single_agent"], required=True)
    run.add_argument("--task-id", required=True)
    run.add_argument("--provider", choices=["mock", "openai"], default="mock")
    run.add_argument("--allow-paid", action="store_true")
    run.add_argument("--output", type=Path, default=Path("results/run"))
    run.add_argument("--max-experiments", type=int, default=6)
    run.add_argument("--max-cost-usd", type=float, default=None)
    analyze = sub.add_parser("analyze")
    analyze.add_argument("--input", type=Path, default=Path("results"))
    analyze.add_argument("--output", type=Path, default=Path("figures"))
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--result", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    if args.command == "audit":
        required = ["modules/common/physics_base.py", "modules/common/evaluation.py", "modules/m0_gravity/core.py", "utils/vanilla_agent.py", "run_experiments.py"]
        checks = {path: (repo_root / path).exists() for path in required}
        print(json.dumps({"upstream_commit": "912a4ba5f4356ddd06acc16e44460ca30be4abc2", "required_paths": checks, "audit_document": str((ROOT / "docs" / "open_source_audit.md").resolve())}, indent=2))
        return 0
    if args.command == "prepare":
        tasks = stratified_select(enumerate_newtonbench_tasks(repo_root, seed=args.seed), args.limit, args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps([t.__dict__ for t in tasks], ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"prepared {len(tasks)} tasks -> {args.output}")
        return 0
    if args.command == "smoke-test":
        summary = smoke_test(repo_root, args.output)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if all(v["status"] == "completed" for k, v in summary.items() if isinstance(v, dict) and "status" in v) else 1
    if args.command == "engineering-test":
        summary = engineering_validation(repo_root, args.manifest, args.output, args.limit)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["tasks"] == args.limit and summary["completed_rows"] == summary["runner_rows"] else 1
    if args.command == "pilot":
        if args.provider == "openai" and not args.allow_paid:
            raise SystemExit("refusing real API pilot without --allow-paid")
        tasks = _load_manifest(args.manifest, repo_root, args.limit)
        runners = ("llm_only", "single_agent") if args.runner == "both" else (args.runner,)
        args.output.mkdir(parents=True, exist_ok=True)
        rows = []
        for task in tasks:
            for runner_name in runners:
                target = args.output / f"{runner_name}_{task.task_id.replace(':', '__')}.json"
                if target.exists():
                    if args.resume:
                        rows.append({"task_id": task.task_id, "runner": runner_name, "status": "resumed"})
                        continue
                    raise SystemExit(f"result already exists; use --resume: {target}")
                if args.provider == "mock":
                    provider = _generic_engineering_provider(task, repo_root, runner_name)
                else:
                    provider = OpenAICompatibleProvider()
                max_cost = args.max_cost_usd if args.max_cost_usd is not None else (0.0 if args.provider == "mock" else float(os.getenv("LLM_MAX_COST_USD", "10.0")))
                result, validation = run_one(task, repo_root, provider, runner_name, BudgetLimits(max_experiments=6, max_api_calls=20, max_cost_usd=max_cost), args.output)
                rows.append({"task_id": task.task_id, "runner": runner_name, "status": result.status, "validated_success": validation.get("validated_success", False)})
        (args.output / "pilot_summary.json").write_text(json.dumps({"mock_only": args.provider == "mock", "rows": rows}, indent=2), encoding="utf-8")
        print(json.dumps({"n": len(rows), "output": str(args.output), "mock_only": args.provider == "mock"}, indent=2))
        return 0
    if args.command == "run":
        if args.provider == "openai" and not args.allow_paid:
            raise SystemExit("refusing real API run without --allow-paid")
        task = next((t for t in enumerate_newtonbench_tasks(repo_root) if t.task_id == args.task_id), None)
        if task is None:
            raise SystemExit(f"task not found or unsupported: {args.task_id}")
        if args.provider == "mock":
            provider = MockLLMProvider([{"experiments": []}, _mock_law()])
        else:
            provider = OpenAICompatibleProvider()
        max_cost = args.max_cost_usd if args.max_cost_usd is not None else (0.0 if args.provider == "mock" else float(os.getenv("LLM_MAX_COST_USD", "10.0")))
        result, validation = run_one(task, repo_root, provider, args.runner, BudgetLimits(max_experiments=args.max_experiments, max_api_calls=20, max_cost_usd=max_cost), args.output)
        print(json.dumps({"status": result.status, "validation": validation}, indent=2, default=str))
        return 0 if result.status == "completed" else 1
    if args.command == "evaluate":
        payload = json.loads(args.result.read_text(encoding="utf-8"))
        task_id = payload["task_id"]
        task = next(t for t in enumerate_newtonbench_tasks(repo_root) if t.task_id == task_id)
        validation = ValidationEnvironment(repo_root).validate(task, payload["law"])
        print(json.dumps(validation, indent=2, default=str))
        return 0
    if args.command == "analyze":
        rows = []
        for path in args.input.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "validation" in data:
                    row = {"validation": dict(data["validation"]), "result": data, "runner": data.get("runner"), "task_id": data.get("task_id")}
                    rows.append(row)
            except (OSError, json.JSONDecodeError):
                continue
        flat_rows = [dict(row["validation"], runner=row.get("runner"), task_id=row.get("task_id")) for row in rows]
        rendered = render_three_panel(rows, args.output, mock=True)
        grouped: dict[str, dict[str, bool]] = {}
        for row in flat_rows:
            grouped.setdefault(str(row.get("task_id")), {})[str(row.get("runner"))] = bool(row.get("validated_success"))
        deltas = [int(pair.get("single_agent", False)) - int(pair.get("llm_only", False)) for pair in grouped.values() if "single_agent" in pair and "llm_only" in pair]
        ci = paired_bootstrap_ci(deltas) if deltas else (float("nan"), float("nan"))
        resource_summary: dict[str, dict[str, float | int]] = {}
        for row in rows:
            runner = str(row.get("runner"))
            used = row.get("result", {}).get("metadata", {}).get("budget", {}).get("used", {})
            totals = resource_summary.setdefault(runner, {"n": 0, "api_calls": 0, "experiments": 0, "measurements": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            totals["n"] += 1
            for key in ("api_calls", "experiments", "measurements", "input_tokens", "output_tokens"):
                totals[key] += int(used.get(key, 0))
            totals["cost_usd"] += float(used.get("cost_usd", 0.0))
        summary = {"n": len(rows), "vldr": vldr(flat_rows), "by_runner": summarize_by(flat_rows, "runner"), "paired": {"n_pairs": len(deltas), "mean_delta": sum(deltas) / len(deltas) if deltas else float("nan"), "bootstrap_95_ci": ci}, "resource_summary": resource_summary, "mock_data_warning": True, "figures": rendered}
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(json.dumps(summary, indent=2, default=str))
        return 0
    return 1


if __name__ == "__main__":
    main()
