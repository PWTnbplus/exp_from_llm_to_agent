"""Command-line entry points for the controlled experiment."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
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
from .evaluation.statistics import clustered_paired_bootstrap_ci, law_family_key, paired_bootstrap_ci
from .evaluation.validation import ValidationEnvironment
from .experiment.recorder import ResultRecorder
from .experiment.runner import run_one
from .models.provider import MockLLMProvider, OpenAICompatibleProvider
from .theory_benchmark.analysis import analyze as analyze_theory
from .theory_benchmark.runner import MODES as THEORY_MODES, run_task as run_theory_task
from .theory_benchmark.contamination import contamination_manifest, generate_private_dynamic_cases
from .theory_benchmark.schema import DATA_DIR, load_benchmark, load_public_benchmark, validate_benchmark
from .theory_benchmark.verification import verify_candidate


ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "third_party" / "NewtonBench"
STATISTICAL_PLAN = ROOT / "configs" / "statistical_plan.json"


def _load_statistical_plan() -> dict[str, Any]:
    return json.loads(STATISTICAL_PLAN.read_text(encoding="utf-8"))


def _manifest_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_design_manifest(tasks: list[TaskSpec], design: str, repo_root: Path) -> dict[str, Any]:
    plan = _load_statistical_plan()
    source = plan["source"]
    expected_count = int(source[f"{design}_tasks"])
    if len(tasks) != expected_count or len({task.task_id for task in tasks}) != expected_count:
        raise SystemExit(f"{design} design requires exactly {expected_count} unique tasks")
    if any(
        task.source != source["benchmark"]
        or task.split != source["split"]
        or task.system_complexity != source["supported_system"]
        or task.seed != int(source["selection_seed"])
        for task in tasks
    ):
        raise SystemExit("manifest violates frozen benchmark, split, or supported-system constraints")
    domain_counts = Counter(task.domain for task in tasks)
    expected_per_domain = 1 if design == "pilot" else 6
    if len(domain_counts) != 12 or set(domain_counts.values()) != {expected_per_domain}:
        raise SystemExit(f"{design} design requires {expected_per_domain} task per each of 12 domains")
    expected_tasks = stratified_select(
        enumerate_newtonbench_tasks(
            repo_root,
            split=source["split"],
            seed=int(source["selection_seed"]),
            supported_system=source["supported_system"],
        ),
        expected_count,
        int(source["selection_seed"]),
    )
    expected_by_id = {task.task_id: task for task in expected_tasks}
    if {task.task_id for task in tasks} != set(expected_by_id):
        raise SystemExit("manifest is not the frozen outcome-blind selection from the pinned benchmark registry")
    if any(task != expected_by_id[task.task_id] for task in tasks):
        raise SystemExit("manifest metadata does not exactly match the frozen benchmark registry")
    return plan


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
    return tasks if path.exists() else tasks[:limit] if limit else tasks


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
    pilot.add_argument("--design", choices=["pilot", "formal"], default="pilot")
    pilot.add_argument("--limit", type=int, default=None, help="must equal the frozen design task count")
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
    analyze.add_argument("--manifest", type=Path, default=None, help="frozen task manifest for complete task-run denominators")
    analyze.add_argument("--design", choices=["pilot", "formal"], default=None)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--result", type=Path, required=True)
    theory_validate = sub.add_parser("theory-validate")
    theory_validate.add_argument("--data-dir", type=Path, default=DATA_DIR)
    theory_list = sub.add_parser("theory-list")
    theory_list.add_argument("--data-dir", type=Path, default=DATA_DIR)
    theory_list.add_argument("--level", type=int, choices=[1, 2, 3])
    theory_list.add_argument("--domain", choices=["Theoretical Chemistry", "Theoretical Biology"])
    theory_verify = sub.add_parser("theory-verify")
    theory_verify.add_argument("--task-id", required=True)
    theory_verify.add_argument("--answer-file", type=Path, required=True)
    theory_verify.add_argument("--data-dir", type=Path, default=DATA_DIR)
    theory_run = sub.add_parser("theory-run")
    theory_run.add_argument("--task-id", required=True)
    theory_run.add_argument("--mode", choices=list(THEORY_MODES), default="G1")
    theory_run.add_argument("--provider", choices=["mock", "openai"], default="mock")
    theory_run.add_argument("--allow-paid", action="store_true")
    theory_run.add_argument("--max-cost-usd", type=float)
    theory_run.add_argument("--max-output-tokens", type=int, default=2048)
    theory_run.add_argument("--output", type=Path, default=Path("results/theory"))
    theory_run.add_argument("--data-dir", type=Path, default=DATA_DIR)
    theory_batch = sub.add_parser("theory-batch")
    theory_batch.add_argument("--mode", choices=list(THEORY_MODES), default="G1")
    theory_batch.add_argument("--provider", choices=["mock", "openai"], default="mock")
    theory_batch.add_argument("--allow-paid", action="store_true")
    theory_batch.add_argument("--max-cost-usd", type=float)
    theory_batch.add_argument("--max-output-tokens", type=int, default=2048)
    theory_batch.add_argument("--level", type=int, choices=[1, 2, 3])
    theory_batch.add_argument("--domain", choices=["Theoretical Chemistry", "Theoretical Biology"])
    theory_batch.add_argument("--limit", type=int)
    theory_batch.add_argument("--output", type=Path, default=Path("results/theory_batch"))
    theory_batch.add_argument("--data-dir", type=Path, default=DATA_DIR)
    theory_analyze = sub.add_parser("theory-analyze")
    theory_analyze.add_argument("--input", type=Path, default=Path("results/theory"))
    theory_analyze.add_argument("--output", type=Path, default=Path("figures/theory"))
    contamination = sub.add_parser("theory-contamination-audit")
    contamination.add_argument("--data-dir", type=Path, default=DATA_DIR)
    contamination.add_argument("--private-seed", default=None, help="operator-provided seed; answers are never printed")
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
        if not args.manifest.exists():
            raise SystemExit("pilot/formal design requires an existing frozen task manifest")
        if args.design == "formal" and (args.provider != "openai" or args.runner != "both"):
            raise SystemExit("formal design requires the real provider and both matched arms")
        if args.provider == "openai" and (args.max_cost_usd is None or args.max_cost_usd <= 0):
            raise SystemExit("real provider runs require an explicit positive --max-cost-usd hard cap")
        plan = _load_statistical_plan()
        target_tasks = int(plan["source"][f"{args.design}_tasks"])
        if args.limit is not None and args.limit != target_tasks:
            raise SystemExit(f"{args.design} design requires --limit {target_tasks} or no --limit")
        tasks = _load_manifest(args.manifest, repo_root, target_tasks)
        _validate_design_manifest(tasks, args.design, repo_root)
        manifest_sha256 = _manifest_sha256(args.manifest)
        runners = ("llm_only", "single_agent") if args.runner == "both" else (args.runner,)
        repeats = int(plan["repeats_per_task_per_arm"][args.design])
        expected_runs = len(tasks) * len(runners) * repeats
        total_cost = args.max_cost_usd if args.max_cost_usd is not None else (0.0 if args.provider == "mock" else float(os.getenv("LLM_MAX_COST_USD", "10.0")))
        if args.provider == "openai" and total_cost <= 0:
            raise SystemExit("real provider runs require a positive --max-cost-usd hard cap")
        per_run_cost = total_cost / expected_runs if expected_runs else 0.0
        args.output.mkdir(parents=True, exist_ok=True)
        rows = []
        for replicate_index in range(repeats):
            for task in tasks:
                for runner_name in runners:
                    target = args.output / f"{runner_name}_{task.task_id.replace(':', '__')}__replicate-{replicate_index:03d}.json"
                    if target.exists():
                        if args.resume:
                            rows.append({"task_id": task.task_id, "runner": runner_name, "replicate_index": replicate_index, "status": "resumed"})
                            continue
                        raise SystemExit(f"result already exists; use --resume: {target}")
                    if args.provider == "mock":
                        provider = _generic_engineering_provider(task, repo_root, runner_name)
                    else:
                        provider = OpenAICompatibleProvider(max_cost_usd=per_run_cost)
                    result, validation = run_one(
                        task, repo_root, provider, runner_name,
                        BudgetLimits(max_experiments=6, max_api_calls=20, max_cost_usd=per_run_cost),
                        args.output,
                        replicate_index=replicate_index,
                        design=args.design,
                        manifest_sha256=manifest_sha256,
                    )
                    rows.append({"task_id": task.task_id, "runner": runner_name, "replicate_index": replicate_index, "status": result.status, "validated_success": validation.get("validated_success", False)})
        (args.output / "pilot_summary.json").write_text(json.dumps({"design": args.design, "mock_only": args.provider == "mock", "manifest_sha256": manifest_sha256, "tasks": len(tasks), "repeats_per_task_per_arm": repeats, "expected_runs": expected_runs, "rows": rows}, indent=2), encoding="utf-8")
        print(json.dumps({"n": len(rows), "expected_runs": expected_runs, "design": args.design, "output": str(args.output), "mock_only": args.provider == "mock"}, indent=2))
        return 0
    if args.command == "run":
        if args.provider == "openai" and not args.allow_paid:
            raise SystemExit("refusing real API run without --allow-paid")
        if args.provider == "openai" and (args.max_cost_usd is None or args.max_cost_usd <= 0):
            raise SystemExit("real provider runs require an explicit positive --max-cost-usd hard cap")
        task = next((t for t in enumerate_newtonbench_tasks(repo_root) if t.task_id == args.task_id), None)
        if task is None:
            raise SystemExit(f"task not found or unsupported: {args.task_id}")
        if args.provider == "mock":
            provider = MockLLMProvider([{"experiments": []}, _mock_law()])
        else:
            provider = OpenAICompatibleProvider(max_cost_usd=args.max_cost_usd)
        max_cost = args.max_cost_usd if args.max_cost_usd is not None else (0.0 if args.provider == "mock" else float(os.getenv("LLM_MAX_COST_USD", "10.0")))
        result, validation = run_one(task, repo_root, provider, args.runner, BudgetLimits(max_experiments=args.max_experiments, max_api_calls=20, max_cost_usd=max_cost), args.output)
        print(json.dumps({"status": result.status, "validation": validation, "run_id": result.run_id, "log": result.trace_path}, indent=2, default=str))
        return 0 if result.status == "completed" else 1
    if args.command == "evaluate":
        payload = json.loads(args.result.read_text(encoding="utf-8"))
        task_id = payload["task_id"]
        task = next(t for t in enumerate_newtonbench_tasks(repo_root) if t.task_id == task_id)
        validation = ValidationEnvironment(repo_root).validate(task, payload["law"])
        print(json.dumps(validation, indent=2, default=str))
        return 0
    if args.command == "theory-validate":
        public, answers, manifest = load_benchmark(args.data_dir)
        for task_id, answer in answers.items():
            check = verify_candidate(task_id, {"final_answer": answer["ground_truth"]["answer"]}, data_dir=args.data_dir)
            if check["status"] != "PASS":
                raise SystemExit(json.dumps(check, ensure_ascii=False))
        print(json.dumps({"status": "PASS", "tasks": len(public), "counts": manifest["counts"], "answer_self_checks": len(answers)}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "theory-contamination-audit":
        public, manifest = load_public_benchmark(args.data_dir)
        report = contamination_manifest(public, version=str(manifest["version"]))
        if args.private_seed:
            cases = generate_private_dynamic_cases(public, seed=args.private_seed)
            report["private_dynamic_cases_generated"] = len(cases)
            report["private_seed_fingerprint"] = __import__("hashlib").sha256(args.private_seed.encode("utf-8")).hexdigest()[:16]
        else:
            report["private_dynamic_cases_generated"] = 0
            report["private_dynamic_status"] = "NOT_RUN: provide --private-seed outside committed logs"
        # The report intentionally contains no private answer values.
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    if args.command == "theory-list":
        public, _, _ = load_benchmark(args.data_dir)
        rows = [row for row in public if (args.level is None or row["difficulty_level"] == args.level) and (args.domain is None or row["domain"] == args.domain)]
        print(json.dumps({"n": len(rows), "tasks": [{"task_id": x["task_id"], "level": x["difficulty_level"], "domain": x["domain"], "subdomain": x["subdomain"]} for x in rows]}, ensure_ascii=False, indent=2))
        return 0
    if args.command == "theory-verify":
        candidate = json.loads(args.answer_file.read_text(encoding="utf-8"))
        result = verify_candidate(args.task_id, candidate, data_dir=args.data_dir)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["status"] == "PASS" else 1
    if args.command == "theory-run":
        if args.provider == "openai" and not args.allow_paid:
            raise SystemExit("refusing real theory API run without --allow-paid")
        if args.provider == "mock":
            responses = [{"task_id": args.task_id, "final_answer": {}}]
            if args.mode in ("G3", "g3", "iterative_reflection"):
                responses = [{"task_id": args.task_id, "final_answer": {}}, {"task_id": args.task_id, "final_answer": {}}]
            provider = MockLLMProvider(responses)
        else:
            if args.max_cost_usd is None or args.max_cost_usd <= 0:
                raise SystemExit("real theory runs require a positive --max-cost-usd")
            provider = OpenAICompatibleProvider(max_cost_usd=args.max_cost_usd, max_output_tokens=args.max_output_tokens)
        result = run_theory_task(args.task_id, provider, args.mode, data_dir=args.data_dir, output_dir=args.output)
        print(json.dumps({"task_id": args.task_id, "mode": args.mode, "status": result["status"], "validation": result["validation"], "run_id": result["run_id"], "log": result["trace_path"], "output": str(args.output)}, ensure_ascii=False, indent=2, default=str))
        return 0 if result["status"] == "COMPLETED" else 1
    if args.command == "theory-batch":
        if args.provider == "openai":
            if not args.allow_paid:
                raise SystemExit("refusing real theory API batch without --allow-paid")
            if args.max_cost_usd is None or args.max_cost_usd <= 0:
                raise SystemExit("real theory batches require a positive --max-cost-usd")
        public, _, _ = load_benchmark(args.data_dir)
        tasks = [row for row in public if (args.level is None or row["difficulty_level"] == args.level) and (args.domain is None or row["domain"] == args.domain)]
        if args.limit is not None:
            tasks = tasks[:args.limit]
        if not tasks:
            raise SystemExit("theory batch filter selected no tasks")
        rows = []
        per_task_cap = args.max_cost_usd / len(tasks) if args.provider == "openai" and args.max_cost_usd is not None else None
        for task in tasks:
            if args.provider == "mock":
                responses = [{"task_id": task["task_id"], "final_answer": {}}]
                if args.mode in ("G3", "g3", "iterative_reflection"):
                    responses *= 2
                provider = MockLLMProvider(responses)
            else:
                provider = OpenAICompatibleProvider(max_cost_usd=per_task_cap, max_output_tokens=args.max_output_tokens)
            rows.append(run_theory_task(task["task_id"], provider, args.mode, data_dir=args.data_dir, output_dir=args.output))
        summary = {"n": len(rows), "mode": args.mode, "provider": args.provider, "completed": sum(row["status"] == "COMPLETED" for row in rows), "correct": sum(row.get("validation", {}).get("answer_correct", False) for row in rows), "output": str(args.output)}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    if args.command == "theory-analyze":
        summary = analyze_theory(args.input, args.output)
        print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
        return 0
    if args.command == "analyze":
        if args.manifest is None:
            raise SystemExit("analysis requires --manifest so the frozen task-run denominator is explicit")
        rows = []
        for path in args.input.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if "validation" in data:
                    task_metadata = data.get("metadata", {}).get("task", {})
                    row = {
                        "validation": dict(data["validation"]),
                        "result": data,
                        "runner": data.get("runner"),
                        "task_id": data.get("task_id"),
                        "domain": task_metadata.get("domain"),
                        "law_complexity": task_metadata.get("difficulty"),
                        "replicate_index": data.get("metadata", {}).get("replicate_index"),
                    }
                    rows.append(row)
            except (OSError, json.JSONDecodeError):
                continue
        expected_plan: dict[str, Any] | None = None
        expected_task_runs = 0
        missing_registered_runs = 0
        manifest_sha256: str | None = None
        if args.manifest is not None:
            design = args.design or "pilot"
            if not args.manifest.exists():
                raise SystemExit("analysis requires an existing frozen task manifest")
            manifest_sha256 = _manifest_sha256(args.manifest)
            expected_tasks = _load_manifest(args.manifest, repo_root)
            expected_plan = _validate_design_manifest(expected_tasks, design, repo_root)
            repeats = int(expected_plan["repeats_per_task_per_arm"][design])
            expected_task_runs = len(expected_tasks) * repeats * 2
            registered_keys = {
                (task.task_id, runner_name, replicate_index)
                for task in expected_tasks
                for runner_name in ("llm_only", "single_agent")
                for replicate_index in range(repeats)
            }
            actual_keys: set[tuple[str, str, int]] = set()
            for row in rows:
                replicate_index = row.get("replicate_index")
                if isinstance(replicate_index, bool) or not isinstance(replicate_index, int) or replicate_index not in range(repeats):
                    raise SystemExit("result has a missing or invalid replicate_index for manifest analysis")
                key = (str(row.get("task_id")), str(row.get("runner")), replicate_index)
                if key not in registered_keys:
                    raise SystemExit(f"result is outside the registered manifest task-run grid: {key}")
                if key in actual_keys:
                    raise SystemExit(f"duplicate result for registered manifest task-run: {key}")
                result_sha = row.get("result", {}).get("metadata", {}).get("manifest_sha256")
                if result_sha != manifest_sha256:
                    raise SystemExit(f"result manifest SHA mismatch for {key}")
                actual_keys.add(key)
            for task in expected_tasks:
                for replicate_index in range(repeats):
                    for runner_name in ("llm_only", "single_agent"):
                        key = (task.task_id, runner_name, replicate_index)
                        if key in actual_keys:
                            continue
                        missing_registered_runs += 1
                        rows.append({
                            "validation": {"validated_success": False, "error": "missing registered task-run"},
                            "result": {
                                "task_id": task.task_id,
                                "runner": runner_name,
                                "run_id": f"missing-{runner_name}-{replicate_index:03d}",
                                "metadata": {"task": {"task_id": task.task_id, "difficulty": task.law_complexity, "domain": task.domain}, "budget": {"used": {}}},
                                "missing_result": True,
                            },
                            "runner": runner_name,
                            "task_id": task.task_id,
                            "domain": task.domain,
                            "law_complexity": task.law_complexity,
                            "replicate_index": replicate_index,
                        })
        flat_rows = [
            dict(
                row["validation"],
                runner=row.get("runner"),
                task_id=row.get("task_id"),
                domain=row.get("domain"),
                law_complexity=row.get("law_complexity"),
                replicate_index=row.get("replicate_index"),
                result=row.get("result"),
            )
            for row in rows
        ]
        rendered = render_three_panel(rows, args.output, mock=True)
        grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for row in flat_rows:
            task_id = str(row.get("task_id"))
            runner = str(row.get("runner"))
            grouped.setdefault(task_id, {}).setdefault(runner, []).append(row)
        paired_records: list[dict[str, Any]] = []
        for task_id, arms in grouped.items():
            if expected_plan is not None:
                design = args.design or "pilot"
                repeats = int(expected_plan["repeats_per_task_per_arm"][design])
                llm_by_replicate = {int(row["replicate_index"]): row for row in arms.get("llm_only", []) if row.get("replicate_index") is not None}
                agent_by_replicate = {int(row["replicate_index"]): row for row in arms.get("single_agent", []) if row.get("replicate_index") is not None}
                indexed_rows = [(index, llm_by_replicate.get(index), agent_by_replicate.get(index)) for index in range(repeats)]
            else:
                llm_rows = sorted(arms.get("llm_only", []), key=lambda row: str(row.get("result", {}).get("run_id", "")))
                agent_rows = sorted(arms.get("single_agent", []), key=lambda row: str(row.get("result", {}).get("run_id", "")))
                indexed_rows = [(index, llm_rows[index] if index < len(llm_rows) else None, agent_rows[index] if index < len(agent_rows) else None) for index in range(max(len(llm_rows), len(agent_rows)))]
            # A missing arm is retained as a failed task-run, rather than
            # silently disappearing from the paired denominator.
            for index, llm_row, agent_row in indexed_rows:
                llm_success = bool(llm_row.get("validated_success")) if llm_row is not None else False
                agent_success = bool(agent_row.get("validated_success")) if agent_row is not None else False
                paired_records.append({
                    "task_id": task_id,
                    "replicate_index": index,
                    "cluster": law_family_key(task_id),
                    "delta": int(agent_success) - int(llm_success),
                    "missing_llm_only": llm_row is None or bool(llm_row.get("result", {}).get("missing_result")),
                    "missing_single_agent": agent_row is None or bool(agent_row.get("result", {}).get("missing_result")),
                })
        statistical_plan = expected_plan or _load_statistical_plan()
        uncertainty = statistical_plan["uncertainty"]
        deltas = [record["delta"] for record in paired_records]
        ci = paired_bootstrap_ci(deltas) if deltas else (float("nan"), float("nan"))
        clustered_ci = clustered_paired_bootstrap_ci(
            ((record["cluster"], record["delta"]) for record in paired_records),
            seed=int(uncertainty["seed"]),
            repeats=int(uncertainty["repeats"]),
        ) if paired_records else (float("nan"), float("nan"))
        resource_summary: dict[str, dict[str, float | int]] = {}
        for row in rows:
            runner = str(row.get("runner"))
            used = row.get("result", {}).get("metadata", {}).get("budget", {}).get("used", {})
            totals = resource_summary.setdefault(runner, {"n": 0, "api_calls": 0, "experiments": 0, "measurements": 0, "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            totals["n"] += 1
            for key in ("api_calls", "experiments", "measurements", "input_tokens", "output_tokens"):
                totals[key] += int(used.get(key, 0))
            totals["cost_usd"] += float(used.get("cost_usd", 0.0))
        summary = {
            "n": len(rows),
            "expected_task_runs": expected_task_runs or None,
            "missing_registered_runs": missing_registered_runs,
            "vldr": vldr(flat_rows),
            "by_runner": summarize_by(flat_rows, "runner"),
            "by_domain": summarize_by(flat_rows, "domain"),
            "by_complexity": summarize_by(flat_rows, "law_complexity"),
            "paired": {
                "n_pairs": len(deltas),
                "n_law_family_clusters": len({record["cluster"] for record in paired_records}),
                "mean_delta": sum(deltas) / len(deltas) if deltas else float("nan"),
                "bootstrap_95_ci": ci,
                "cluster_bootstrap_95_ci": clustered_ci,
                "missing_arm_pairs": sum(record["missing_llm_only"] or record["missing_single_agent"] for record in paired_records),
            },
            "statistical_plan": {
                "version": statistical_plan["version"],
                "cluster_key": statistical_plan["law_family_cluster"]["key"],
                "failures_in_denominator": statistical_plan["denominator"]["include_all_registered_task_runs"],
                "design": args.design,
                "manifest_sha256": manifest_sha256 if args.manifest is not None else None,
            },
            "resource_summary": resource_summary,
            "mock_data_warning": True,
            "figures": rendered,
        }
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
        print(json.dumps(summary, indent=2, default=str))
        return 0
    return 1


if __name__ == "__main__":
    main()
