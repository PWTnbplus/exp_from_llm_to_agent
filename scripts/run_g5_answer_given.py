#!/usr/bin/env python3
"""Run the isolated G5 answer-given reverse-derivation Agent experiment.

The runner is deliberately separate from the historical G0--G5 theory runner.
It exposes only a public task and the explicitly revealed answer, never the
private answer-key row or verifier.  Every observable model/tool event is
written append-only and each task is checkpointed atomically so an interrupted
run can be resumed without overwriting an earlier attempt.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
import traceback
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scientific_discovery.models.provider import (  # noqa: E402
    LLMProvider,
    MockLLMProvider,
    OpenAICompatibleProvider,
    ProviderResponse,
)


MODEL_ALLOWLIST_DEFAULT = ROOT / "configs" / "recovery_model_allowlist_20261011.json"
MODEL_MATRIX_DEFAULT = ROOT / "configs" / "ctflow_model_matrix.json"
DATA_DEFAULT = ROOT / "data" / "theory_benchmark_v2"
BASE_URL_DEFAULT = "https://token.ctflow.cn/v1"
SKILL_ZIP_DEFAULT = Path(r"D:\硕士\prj1_ai_cal\exp\exp1_from_llm_to_agent\prompt\whole_pros_g5.zip")

MAX_MODEL_CALLS = 8
MAX_TOOL_CALLS = 6
MAX_REVISION_ROUNDS = 3
MAX_TOTAL_TOKENS = 8000
MAX_WALL_SECONDS = 300

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "safe_sympy",
            "description": "Evaluate a supplied finite symbolic expression with supplied numeric values.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "values": {"type": "object"},
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "safe_scipy",
            "description": "Run a bounded numerical calculation on a supplied expression and interval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "variable": {"type": "string"},
                    "lower": {"type": "number"},
                    "upper": {"type": "number"},
                    "target": {"type": "number"},
                },
                "required": ["expression", "variable", "lower", "upper"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sandbox_python",
            "description": "Evaluate a single arithmetic expression without imports, files, network, or code execution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "values": {"type": "object"},
                },
                "required": ["expression"],
                "additionalProperties": False,
            },
        },
    },
]

_SECRET_TEXT = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+|\bsk-[A-Za-z0-9_-]{12,}")
_PRIVATE_TEXT = re.compile(r"(?i)ground_truth|answer_key|verification_code|verification_status")
_JSON_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.IGNORECASE | re.DOTALL)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def sha256_value(value: Any) -> str:
    raw = json.dumps(json_safe(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def json_safe(value: Any) -> Any:
    """Keep observable non-finite tool values JSON-valid without hiding them."""
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    return value


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f".tmp-{os.getpid()}-{threading.get_ident()}")
    with tmp.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(json_safe(value), handle, ensure_ascii=False, indent=2, allow_nan=False, default=str)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def append_jsonl(path: Path, value: Any) -> None:
    """Append one durable JSONL record without rewriting earlier records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def scrub(value: Any, known_secret: str = "") -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            key_text = str(key)
            if re.search(r"api[_-]?key|authorization|access[_-]?token|password|cookie|secret", key_text, re.I):
                result[key_text] = "[REDACTED]"
            else:
                result[key_text] = scrub(item, known_secret)
        return result
    if isinstance(value, list):
        return [scrub(item, known_secret) for item in value]
    if isinstance(value, str):
        text = value.replace(known_secret, "[REDACTED]") if known_secret else value
        text = _SECRET_TEXT.sub("[REDACTED]", text)
        return _PRIVATE_TEXT.sub("[PRIVATE_FIELD]", text)
    return value


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_models(matrix_path: Path, allowlist_path: Path | None) -> list[dict[str, str]]:
    matrix = read_json(matrix_path)
    allowed: set[str] | None = None
    if allowlist_path:
        allow = read_json(allowlist_path)
        allowed = {str(x) for x in (allow.get("models", []) if isinstance(allow, dict) else allow)}
    rows: list[dict[str, str]] = []
    for provider_group, group in (matrix.get("groups") or {}).items():
        for item in group.get("models") or []:
            model = str(item["model_id"])
            if allowed is not None and model not in allowed:
                continue
            rows.append({
                "provider_group": str(provider_group),
                "key_dir": str(group["key_dir"]),
                "model_id": model,
                "key_file": str(item["key_file"]),
            })
    if not rows:
        raise ValueError("no model in the configured matrix passed the allowlist")
    return rows


def load_tasks(data_dir: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    public = read_json(data_dir / "public_tasks.json")
    answers_list = read_json(data_dir / "answer_key.json")
    manifest = read_json(data_dir / "manifest.json")
    answers = {str(row["task_id"]): row for row in answers_list}
    if len(public) != 300 or len(answers) != 300 or len({row["task_id"] for row in public}) != 300:
        raise ValueError("G5 requires the complete 300-task theory benchmark")
    for task in public:
        if set(task) & {"ground_truth", "verification_code", "verification_status", "answer_key"}:
            raise ValueError(f"private field leaked into public task: {task.get('task_id')}")
        if task["task_id"] not in answers:
            raise ValueError(f"missing revealed answer for {task['task_id']}")
    return public, answers, manifest


def revealed_answer(answer_row: dict[str, Any]) -> dict[str, Any]:
    gt = answer_row.get("ground_truth") or {}
    if not isinstance(gt, dict) or "answer" not in gt:
        raise ValueError(f"answer row for {answer_row.get('task_id')} has no answer")
    # Only this explicitly revealed field is handed to the model.  Derivation,
    # verifier, rubric, and failure-mode fields remain operator-side.
    return {"answer": gt["answer"], "verification_level": gt.get("verification_level", "unknown")}


def parse_json_object(text: str) -> dict[str, Any] | None:
    candidate = text.strip()
    fenced = _JSON_FENCE.fullmatch(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    try:
        value = json.loads(candidate)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    start = candidate.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(candidate)):
        char = candidate[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    value = json.loads(candidate[start : index + 1])
                    return value if isinstance(value, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def validate_submission(task_id: str, payload: dict[str, Any] | None) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        errors.append("final model output is not a JSON object")
        return {"status": "MODEL_OUTPUT_PARSE_FAILURE", "errors": errors, "valid": False}
    if payload.get("task_id") not in (None, task_id):
        errors.append("task_id mismatch")
    if payload.get("final_assessment") not in {"SUPPORTED", "REFUTED", "UNPROVEN"}:
        errors.append("final_assessment must be SUPPORTED, REFUTED, or UNPROVEN")
    claims = payload.get("claims")
    if not isinstance(claims, list):
        errors.append("claims must be a list")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"claim {index} is not an object")
                continue
            for field in ("claim_id", "statement", "status", "evidence_refs"):
                if field not in claim:
                    errors.append(f"claim {index} missing {field}")
            if claim.get("status") not in {"proposed", "supported", "refuted", "unresolved"}:
                errors.append(f"claim {index} has invalid status")
            if not isinstance(claim.get("evidence_refs", []), list):
                errors.append(f"claim {index} evidence_refs must be a list")
    for field in ("backward_derivation", "forward_check", "answer_dependency_assessment"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            errors.append(f"missing {field}")
    return {"status": "PASS" if not errors else "MODEL_OUTPUT_SCHEMA_FAILURE", "errors": errors, "valid": not errors}


def safe_tool(name: str, arguments: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Execute only bounded deterministic math; no files, imports, or network."""
    try:
        import ast
        import math
        import operator

        expression = str(arguments.get("expression", ""))
        if len(expression) > 500:
            raise ValueError("expression too long")
        values = arguments.get("values") or {}
        if not isinstance(values, dict) or any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in values.values()):
            raise ValueError("values must contain numeric values only")
        if name == "safe_sympy":
            import sympy as sp
            symbols = {str(k): sp.Float(v) for k, v in values.items()}
            expr = sp.sympify(expression, locals=symbols)
            if expr.free_symbols:
                return {"expression": str(expr), "unresolved_symbols": sorted(map(str, expr.free_symbols))}, "COMPLETED"
            return {"expression": str(expr), "value": float(expr.evalf())}, "COMPLETED"
        if name == "safe_scipy":
            import scipy.optimize as optimize
            variable = str(arguments.get("variable", "x"))
            lower = float(arguments["lower"])
            upper = float(arguments["upper"])
            if not lower < upper or abs(upper - lower) > 1_000_000:
                raise ValueError("invalid bounded interval")
            import sympy as sp
            x = sp.Symbol(variable)
            expr = sp.sympify(expression, locals={variable: x})
            target = float(arguments.get("target", 0.0))
            fn = sp.lambdify(x, expr - target, modules=["math"])
            root = optimize.brentq(fn, lower, upper)
            return {"root": float(root), "expression": expression, "interval": [lower, upper], "target": target}, "COMPLETED"
        if name == "sandbox_python":
            tree = ast.parse(expression, mode="eval")
            allowed = (ast.Expression, ast.Constant, ast.Name, ast.BinOp, ast.UnaryOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod, ast.USub, ast.UAdd, ast.FloorDiv, ast.Load)
            if any(not isinstance(node, allowed) for node in ast.walk(tree)):
                raise ValueError("only arithmetic AST nodes are allowed")
            operations = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod, ast.FloorDiv: operator.floordiv}
            def evaluate(node: ast.AST) -> float:
                if isinstance(node, ast.Expression): return evaluate(node.body)
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool): return float(node.value)
                if isinstance(node, ast.Name) and node.id in values: return float(values[node.id])
                if isinstance(node, ast.UnaryOp) and type(node.op) in (ast.USub, ast.UAdd): return (-1 if isinstance(node.op, ast.USub) else 1) * evaluate(node.operand)
                if isinstance(node, ast.BinOp) and type(node.op) in operations: return float(operations[type(node.op)](evaluate(node.left), evaluate(node.right)))
                raise ValueError("unsupported arithmetic expression")
            value = evaluate(tree)
            if not math.isfinite(value): raise ValueError("non-finite result")
            return {"expression": expression, "value": value}, "COMPLETED"
        raise ValueError(f"unauthorized tool: {name}")
    except Exception as exc:  # tool errors are observable outcomes, not crashes
        return {"error_type": type(exc).__name__, "error": str(exc)}, "FAILED"


class EventWriter:
    def __init__(self, path: Path, *, experiment_id: str, run_id: str, task_id: str, model: str, known_secret: str = ""):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = path.open("a", encoding="utf-8", newline="\n")
        self.experiment_id = experiment_id
        self.run_id = run_id
        self.task_id = task_id
        self.model = model
        self.known_secret = known_secret
        self.seq = 0
        self.lock = threading.Lock()

    def emit(self, event_type: str, *, span_id: str | None = None, parent_span_id: str | None = None, status: str = "OK", payload: dict[str, Any] | None = None) -> dict[str, Any]:
        with self.lock:
            self.seq += 1
            row = {
                "experiment_id": self.experiment_id,
                "run_id": self.run_id,
                "task_id": self.task_id,
                "model": self.model,
                "seq": self.seq,
                "timestamp_utc": utc_now(),
                "event_type": event_type,
                "span_id": span_id or f"{self.run_id}:span-{self.seq:06d}",
                "parent_span_id": parent_span_id,
                "status": status,
                "payload": scrub(payload or {}, self.known_secret),
            }
            self.handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            self.handle.flush()
            os.fsync(self.handle.fileno())
            return row

    def close(self) -> None:
        with self.lock:
            self.handle.flush()
            os.fsync(self.handle.fileno())
            self.handle.close()


def system_prompt() -> str:
    return (
        "You are the G5 answer-given reverse-derivation Agent. This is a separate "
        "experiment from G0-G4. The public task and the explicitly revealed answer "
        "are evidence inputs, not a hidden proof. You must independently inspect the "
        "equations, derive consequences backward from the answer, and forward-check "
        "them with permitted math tools when useful. Never invent a tool result. "
        "Never claim certainty from the answer alone. Keep unresolved claims marked "
        "UNPROVEN. Do not request files, web access, private verifier data, or hidden "
        "ground truth. Return JSON only when submitting a stage or final package."
        " Ignore the legacy task request for a final_answer-only object; the G5 "
        "final response must use the claims/backward_derivation/forward_check schema below."
    )


def task_prompt(task: dict[str, Any], answer: dict[str, Any]) -> str:
    return json.dumps({
        "task_public": task,
        "revealed_answer": answer,
        "answer_exposure": "given_to_g5_only",
        "required_final_schema": {
            "task_id": "string",
            "final_assessment": "SUPPORTED|REFUTED|UNPROVEN",
            "claims": [{"claim_id": "string", "statement": "string", "status": "proposed|supported|refuted|unresolved", "evidence_refs": ["event/span/artifact ids"]}],
            "backward_derivation": "string",
            "forward_check": "string",
            "answer_dependency_assessment": "string",
            "unresolved_steps": ["string"],
        },
    }, ensure_ascii=False)


def compact_task_prompt(
    task: dict[str, Any],
    answer: dict[str, Any],
    stage_memory: list[dict[str, Any]],
    tool_memory: list[dict[str, Any]],
    instruction: str,
) -> str:
    """Build a bounded within-task memory context for later Agent calls.

    Full task JSON is sent only on the first call.  Later calls receive the
    scientifically relevant fields plus compact, observable stage/tool facts;
    this prevents prompt growth from silently consuming the G5 8000-token
    task budget while keeping cross-task memory disabled.
    """
    return json.dumps({
        "task_id": task["task_id"],
        "task_public": {
            "domain": task.get("domain"),
            "theory_name": task.get("theory_name"),
            "problem_statement": task.get("problem_statement"),
            "mathematical_model": task.get("mathematical_model"),
            "given_parameters": task.get("given_parameters"),
            "assumptions": task.get("assumptions"),
        },
        "revealed_answer": answer,
        "within_task_stage_memory": stage_memory[-3:],
        "within_task_tool_memory": tool_memory[-6:],
        "required_final_schema": {
            "task_id": "string",
            "final_assessment": "SUPPORTED|REFUTED|UNPROVEN",
            "claims": [{"claim_id": "string", "statement": "string", "status": "proposed|supported|refuted|unresolved", "evidence_refs": ["event/span/artifact ids"]}],
            "backward_derivation": "string",
            "forward_check": "string",
            "answer_dependency_assessment": "string",
            "unresolved_steps": ["string"],
        },
        "instruction": instruction,
    }, ensure_ascii=False)


def role_instruction(role: str, final: bool = False) -> str:
    instructions = {
        "planner": "Act as planner: decompose the task and identify what the revealed answer does and does not establish.",
        "hypothesis_manager": "Act as hypothesis manager: list candidate derivations and their assumptions; mark them proposed until evidenced.",
        "verifier": "Act as verifier: use safe math tools for independent forward checks and cite the resulting event or artifact ids.",
        "critic": "Act as critic: search for circular reasoning, dimension errors, unsupported steps, and answer-only acceptance.",
        "reviser": "Act as reviser: repair only claims supported by the task and recorded evidence; leave the rest unresolved.",
    }
    suffix = (
        " Perform the critic and reviser checks, then produce ONLY one complete compact JSON object now. "
        "Do not use Markdown fences, prose, headings, or a legacy final_answer-only object. "
        "Use exactly one of SUPPORTED, REFUTED, or UNPROVEN for final_assessment; if evidence is mixed, "
        "use UNPROVEN and describe the supported and unresolved parts in claims. "
        "Keep claims to at most 2 concise items, keep each text field to one short sentence, and keep the "
        "entire JSON under about 800 characters so the object closes within the output limit. Include every "
        "required key, including an array unresolved_steps."
    ) if final else " Return a JSON stage record or use an allowed tool if needed."
    return instructions[role] + suffix


def build_proof_graph(payload: dict[str, Any] | None) -> dict[str, Any]:
    claims = payload.get("claims", []) if isinstance(payload, dict) else []
    nodes = []
    edges = []
    for claim in claims if isinstance(claims, list) else []:
        if not isinstance(claim, dict):
            continue
        claim_id = str(claim.get("claim_id", f"claim-{len(nodes)+1}"))
        nodes.append({"claim_id": claim_id, "statement": claim.get("statement", ""), "status": claim.get("status", "unresolved"), "evidence_refs": claim.get("evidence_refs", [])})
        for ref in claim.get("depends_on", []) if isinstance(claim.get("depends_on", []), list) else []:
            edges.append({"from": str(ref), "to": claim_id, "type": "dependency"})
    return {"version": 1, "nodes": nodes, "edges": edges, "final_assessment": payload.get("final_assessment") if isinstance(payload, dict) else None}


def model_output_snapshot(response: ProviderResponse) -> dict[str, Any]:
    return {
        "content": response.content,
        "tool_calls": response.tool_calls,
        "usage": response.usage.__dict__,
        "metadata": response.metadata,
    }


def run_task(
    *,
    experiment_id: str,
    model_dir: Path,
    model: dict[str, str],
    task: dict[str, Any],
    answer_row: dict[str, Any],
    provider: LLMProvider,
    max_output_tokens: int,
    known_secret: str,
    resume: bool,
) -> dict[str, Any]:
    task_id = str(task["task_id"])
    task_dir = model_dir / "tasks" / task_id
    summary_path = task_dir / "summary.json"
    previous = None
    if summary_path.exists():
        try:
            previous = read_json(summary_path)
        except (OSError, json.JSONDecodeError):
            previous = None
    if resume and isinstance(previous, dict) and previous.get("status") == "COMPLETED" and previous.get("final_validation", {}).get("valid"):
        return {"task_id": task_id, "status": "RESUMED_COMPLETED", "previous_status": previous.get("status"), "attempt": previous.get("attempt")}
    attempt = int(previous.get("attempt", 0)) + 1 if isinstance(previous, dict) else 1
    attempt_dir = task_dir / "attempts" / f"attempt-{attempt:03d}"
    # A hard interruption can leave an attempt directory without its canonical
    # task summary.  Keep that partial attempt as raw evidence and allocate a
    # fresh attempt directory on resume instead of failing with FileExistsError.
    while attempt_dir.exists():
        attempt += 1
        attempt_dir = task_dir / "attempts" / f"attempt-{attempt:03d}"
    attempt_dir.mkdir(parents=True, exist_ok=False)
    steps_path = attempt_dir / "steps.jsonl"
    stderr_path = attempt_dir / "stderr.log"
    steps_path.touch()
    stderr_path.write_text("", encoding="utf-8", newline="\n")
    run_id = f"{experiment_id}-{model['model_id']}-{task_id}-attempt-{attempt:03d}"
    events = EventWriter(attempt_dir / "events.jsonl", experiment_id=experiment_id, run_id=run_id, task_id=task_id, model=model["model_id"], known_secret=known_secret)
    answer = revealed_answer(answer_row)
    task_manifest = {
        "experiment_id": experiment_id,
        "run_id": run_id,
        "task_id": task_id,
        "model_id": model["model_id"],
        "attempt": attempt,
        "answer_exposure": "given_to_g5_only",
        "no_private_answer_access": True,
        "task_public_sha256": sha256_value(task),
        "revealed_answer_sha256": sha256_value(answer),
        "private_answer_row_not_copied": True,
        "max_model_calls": MAX_MODEL_CALLS,
        "max_tool_calls": MAX_TOOL_CALLS,
        "max_revision_rounds": MAX_REVISION_ROUNDS,
        "max_total_tokens": MAX_TOTAL_TOKENS,
        "max_wall_time_seconds": MAX_WALL_SECONDS,
        "web_access": False,
        "cross_task_memory": False,
        "started_at_utc": utc_now(),
    }
    atomic_write_json(attempt_dir / "manifest.json", task_manifest)
    checkpoint = {"task_id": task_id, "status": "RUNNING", "attempt": attempt, "last_committed_seq": 0, "updated_at_utc": utc_now()}
    atomic_write_json(attempt_dir / "checkpoint.json", checkpoint)
    events.emit("RUN_START", status="RUNNING", payload={"workflow": "agentic_reverse", "answer_exposure": "given_to_g5_only", "task_public_sha256": task_manifest["task_public_sha256"], "revealed_answer_sha256": task_manifest["revealed_answer_sha256"]})
    messages: list[dict[str, Any]] = []
    roles = ["planner", "hypothesis_manager", "verifier", "critic", "reviser"]
    tool_calls = 0
    model_calls = 0
    revision_rounds = 0
    total_tokens = 0
    candidate: dict[str, Any] | None = None
    all_tool_artifacts: list[dict[str, Any]] = []
    stage_memory: list[dict[str, Any]] = []
    tool_memory: list[dict[str, Any]] = []
    started = time.monotonic()
    trace_start = len(provider.audit_trace())
    final_status = "FAILED"
    final_validation: dict[str, Any] = {"valid": False, "status": "NOT_SUBMITTED", "errors": []}
    error_info: dict[str, Any] | None = None
    try:
        # One evidence-gathering call plus one final critic/reviser call leave
        # room for the full observable context under the per-task 8000-token
        # gate.  The registered eight-call value remains an upper bound.
        workflow_call_limit = min(MAX_MODEL_CALLS, 2)
        while model_calls < workflow_call_limit and time.monotonic() - started < MAX_WALL_SECONDS:
            role = roles[min(model_calls, len(roles) - 1)]
            # Reserve a final no-tools call before the model can exhaust the
            # six-tool budget while still producing a submitted package.
            force_final = model_calls >= 1 or revision_rounds >= MAX_REVISION_ROUNDS or tool_calls >= MAX_TOOL_CALLS - 2
            step_start = events.emit("STEP_START", status="RUNNING", payload={"step_id": f"{role}-{model_calls+1}", "stage": role})
            append_jsonl(steps_path, step_start)
            instruction = role_instruction(role, final=force_final)
            if model_calls == 0:
                messages = [
                    {"role": "system", "content": system_prompt()},
                    {"role": "user", "content": task_prompt(task, answer)},
                    {"role": "user", "content": instruction},
                ]
            else:
                messages = [
                    {"role": "system", "content": system_prompt()},
                    {"role": "user", "content": compact_task_prompt(task, answer, stage_memory, tool_memory, instruction)},
                ]
            request_tools = TOOLS if not force_final and tool_calls < MAX_TOOL_CALLS else None
            model_calls += 1
            span = f"{run_id}:model-{model_calls:03d}"
            events.emit("MODEL_REQUEST", span_id=span, status="RUNNING", payload={"call_index": model_calls, "role": role, "messages": messages, "tools": request_tools, "max_output_tokens": max_output_tokens, "retry_id": None})
            try:
                response = provider.complete(messages, tools=request_tools)
            except Exception as exc:
                traces = provider.audit_trace()
                events.emit("MODEL_ERROR", span_id=f"{span}:error", parent_span_id=span, status="FAILED", payload={"call_index": model_calls, "error_type": type(exc).__name__, "error": str(exc), "provider_trace_tail": traces[-1:]})
                raise
            snapshot = model_output_snapshot(response)
            events.emit("MODEL_RESPONSE", span_id=f"{span}:response", parent_span_id=span, status="COMPLETED", payload={"call_index": model_calls, "role": role, "response": snapshot, "retry_id": None})
            total_tokens += int(response.usage.input_tokens) + int(response.usage.output_tokens)
            if total_tokens > MAX_TOTAL_TOKENS:
                raise RuntimeError("total token budget exceeded")
            for raw_call in response.tool_calls or []:
                if tool_calls >= MAX_TOOL_CALLS:
                    events.emit("POLICY_VIOLATION", status="FAILED", payload={"operation": "tool_call", "reason": "tool call budget exceeded"})
                    raise RuntimeError("tool call budget exceeded")
                function = raw_call.get("function", raw_call) if isinstance(raw_call, dict) else {}
                tool_name = str(function.get("name", ""))
                arguments = function.get("arguments", {})
                if isinstance(arguments, str):
                    try: arguments = json.loads(arguments)
                    except json.JSONDecodeError: arguments = {"expression": arguments}
                if not isinstance(arguments, dict) or tool_name not in {"safe_sympy", "safe_scipy", "sandbox_python"}:
                    events.emit("POLICY_VIOLATION", status="FAILED", payload={"operation": "tool_call", "tool_name": tool_name, "reason": "unauthorized tool or malformed arguments"})
                    raise RuntimeError("unauthorized tool call")
                tool_calls += 1
                call_id = str(raw_call.get("id", f"tool-{tool_calls:03d}"))
                tool_span = f"{run_id}:tool-{tool_calls:03d}"
                events.emit("TOOL_CALL", span_id=tool_span, parent_span_id=span, status="RUNNING", payload={"call_id": call_id, "tool_name": tool_name, "tool_arguments": arguments, "sandbox": True})
                output, status = safe_tool(tool_name, arguments)
                output = json_safe(output)
                artifact = {"artifact_id": f"artifact-{tool_calls:03d}", "tool_name": tool_name, "input": arguments, "output": output, "status": status, "created_at_utc": utc_now()}
                artifact_path = attempt_dir / "tool_artifacts" / f"tool-{tool_calls:03d}.json"
                atomic_write_json(artifact_path, artifact)
                artifact_ref = {"artifact_id": artifact["artifact_id"], "path": str(artifact_path.relative_to(attempt_dir)), "sha256": sha256_value(artifact), "tool_name": tool_name}
                all_tool_artifacts.append(artifact_ref)
                tool_memory.append({"tool_name": tool_name, "status": status, "output": output, "artifact": artifact_ref})
                events.emit("TOOL_RESULT" if status == "COMPLETED" else "TOOL_ERROR", span_id=f"{tool_span}:result", parent_span_id=tool_span, status=status, payload={"call_id": call_id, "tool_name": tool_name, "tool_output": output, "artifact": artifact_ref})
            parsed = parse_json_object(response.content)
            if parsed is not None:
                stage_memory.append({"stage": role, "parsed": scrub(parsed)})
                events.emit("CLAIM_UPDATE", status="COMPLETED", payload={"stage": role, "claims": parsed.get("claims", []), "final_assessment": parsed.get("final_assessment")})
                validation = validate_submission(task_id, parsed)
                if validation["valid"]:
                    candidate = parsed
                    if force_final:
                        final_validation = validation
                        final_status = "COMPLETED"
                        events.emit("PREDICTION", status="COMPLETED", payload={"final_package": parsed, "tool_artifacts": all_tool_artifacts})
                        break
                elif force_final:
                    final_validation = validation
            else:
                stage_memory.append({"stage": role, "raw_output": response.content[:3000]})
            step_end = events.emit("STEP_END", status="COMPLETED", payload={"step_id": f"{role}-{model_calls}", "stage": role, "candidate_valid": bool(candidate)})
            append_jsonl(steps_path, step_end)
            if role == "reviser":
                revision_rounds += 1
        if final_status != "COMPLETED":
            if time.monotonic() - started >= MAX_WALL_SECONDS:
                raise TimeoutError("task wall-time budget exceeded")
            final_validation = validate_submission(task_id, candidate)
            if final_validation["valid"]:
                final_status = "COMPLETED"
                events.emit("PREDICTION", status="COMPLETED", payload={"final_package": candidate, "tool_artifacts": all_tool_artifacts})
            else:
                final_status = "FAILED_MODEL_OUTPUT"
    except TimeoutError as exc:
        final_status = "TIMEOUT"
        error_info = {"error_type": type(exc).__name__, "error": str(exc)}
        events.emit("ERROR", status="FAILED", payload=error_info)
    except Exception as exc:
        final_status = "PROVIDER_ERROR" if isinstance(exc, (RuntimeError, OSError)) and "provider" in str(exc).lower() else "FAILED"
        error_info = {"error_type": type(exc).__name__, "error": str(exc)}
        events.emit("ERROR", status="FAILED", payload={**error_info, "traceback": traceback.format_exc(limit=3)})
    finally:
        trace = provider.audit_trace()[trace_start:]
        task_cost = sum(float(((item.get("response") or {}).get("usage") or {}).get("cost_usd", 0.0)) for item in trace)
        if error_info:
            with stderr_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(scrub(error_info), ensure_ascii=False, separators=(",", ":")) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
        summary = {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "task_id": task_id,
            "model_id": model["model_id"],
            "attempt": attempt,
            "status": final_status,
            "model_calls": model_calls,
            "tool_calls": tool_calls,
            "revision_rounds": revision_rounds,
            "total_tokens": total_tokens,
            "provider_cost_usd_proxy": task_cost,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "answer_exposure": "given_to_g5_only",
            "no_private_answer_access": True,
            "revealed_answer_sha256": task_manifest["revealed_answer_sha256"],
            "final_validation": final_validation,
            "error": error_info,
            "tool_artifacts": all_tool_artifacts,
            "final_package": candidate,
        }
        events.emit("EVALUATION", status="COMPLETED" if final_validation.get("valid") else "UNPROVEN", payload={"validation": final_validation, "private_evaluator_used": False, "answer_accuracy_scored": False})
        events.emit("CHECKPOINT", status="COMPLETED" if final_status == "COMPLETED" else "FAILED", payload={"task_status": final_status, "last_committed_seq": events.seq})
        events.emit("RUN_END", status=final_status, payload={"status": final_status, "model_calls": model_calls, "tool_calls": tool_calls})
        events.close()
        atomic_write_json(attempt_dir / "proof_graph.json", build_proof_graph(candidate))
        atomic_write_json(attempt_dir / "summary.json", summary)
        checkpoint.update({"status": final_status, "last_committed_seq": events.seq, "updated_at_utc": utc_now()})
        atomic_write_json(attempt_dir / "checkpoint.json", checkpoint)
        task_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(summary_path, summary)
        atomic_write_json(task_dir / "manifest.json", task_manifest)
    return {"task_id": task_id, "status": final_status, "attempt": attempt, "model_calls": model_calls, "tool_calls": tool_calls}


def model_worker(args: argparse.Namespace, experiment_id: str, model: dict[str, str], tasks: list[dict[str, Any]], answers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    model_dir = args.output_root / experiment_id / "models" / model["model_id"]
    model_dir.mkdir(parents=True, exist_ok=True)
    key_path = args.key_root / model["key_dir"] / model["key_file"]
    key = key_path.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise RuntimeError(f"invalid local key file for {model['model_id']}")
    existing_task_summaries = []
    for summary_path in sorted((model_dir / "tasks").glob("*/summary.json")):
        try:
            summary = read_json(summary_path)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(summary, dict):
            existing_task_summaries.append(summary)
    prior_model_summary = None
    try:
        prior_model_summary = read_json(model_dir / "model_summary.json")
    except (OSError, json.JSONDecodeError):
        prior_model_summary = None
    prior_cost = sum(float(row.get("provider_cost_usd_proxy", 0.0) or 0.0) for row in existing_task_summaries)
    remaining_cost = max(0.0, float(args.max_cost_usd_per_model) - prior_cost)
    atomic_write_json(model_dir / "model_manifest.json", {
        "experiment_id": experiment_id,
        "model_id": model["model_id"],
        "provider_group": model["provider_group"],
        "max_cost_usd_per_model": args.max_cost_usd_per_model,
        "prior_cost_usd_proxy": prior_cost,
        "remaining_cost_usd_proxy": remaining_cost,
        "cost_interpretation": "local input/output proxy; provider billing not independently verified",
        "base_url": args.base_url,
        "transport_retries": 0,
        "tasks_expected": len(tasks),
        "task_ids": [task["task_id"] for task in tasks],
        "answer_key_not_copied": True,
        "started_at_utc": utc_now(),
    })
    if args.provider == "mock":
        mock_payload = json.dumps({
            "final_assessment": "UNPROVEN",
            "claims": [{"claim_id": "claim-1", "statement": "Mock smoke claim", "status": "unresolved", "evidence_refs": []}],
            "backward_derivation": "Mock only.",
            "forward_check": "Mock only.",
            "answer_dependency_assessment": "Mock only; not a scientific result.",
            "unresolved_steps": ["mock"],
        })
        provider = MockLLMProvider([mock_payload for _ in range(len(tasks) * MAX_MODEL_CALLS)])
    else:
        provider = OpenAICompatibleProvider(
            api_key=key,
            base_url=args.base_url,
            model_name=model["model_id"],
            timeout=args.timeout_seconds,
            max_retries=0,
            input_cost_per_1k=args.input_price_usd_per_1k,
            output_cost_per_1k=args.output_price_usd_per_1k,
            # On resume, prior durable task costs are subtracted before any
            # new request.  A tiny positive cap deliberately causes the
            # provider to stop before transport when no budget remains.
            max_cost_usd=max(remaining_cost, 1e-9),
            max_output_tokens=args.max_output_tokens,
        )
    del key
    rows = []
    for task in tasks:
        row = run_task(experiment_id=experiment_id, model_dir=model_dir, model=model, task=task, answer_row=answers[task["task_id"]], provider=provider, max_output_tokens=args.max_output_tokens, known_secret="", resume=args.resume)
        rows.append(row)
        progress = {"model_id": model["model_id"], "completed": sum(r["status"] in {"COMPLETED", "RESUMED_COMPLETED"} for r in rows), "processed": len(rows), "total": len(tasks), "last": row, "updated_at_utc": utc_now()}
        atomic_write_json(model_dir / "progress.json", progress)
    usage = provider.audit_trace()
    current_cost = sum(float(((item.get("response") or {}).get("usage") or {}).get("cost_usd", 0.0)) for item in usage)
    total_cost = prior_cost + current_cost
    prior_calls = int((prior_model_summary or {}).get("provider_call_count", 0) or 0)
    summary = {
        "experiment_id": experiment_id,
        "model_id": model["model_id"],
        "tasks": len(rows),
        "status_counts": dict(__import__("collections").Counter(str(row["status"]) for row in rows)),
        "provider_call_count": prior_calls + len(usage),
        "provider_cost_usd_proxy": total_cost,
        "max_cost_usd_per_model": args.max_cost_usd_per_model,
        "finished_at_utc": utc_now(),
    }
    atomic_write_json(model_dir / "model_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, default=DATA_DEFAULT)
    parser.add_argument("--model-config", type=Path, default=MODEL_MATRIX_DEFAULT)
    parser.add_argument("--model-allowlist", type=Path, default=MODEL_ALLOWLIST_DEFAULT)
    parser.add_argument("--key-root", type=Path, default=ROOT / "api_key")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT)
    parser.add_argument("--skill-zip", type=Path, default=SKILL_ZIP_DEFAULT)
    parser.add_argument("--provider", choices=("mock", "openai"), default="mock")
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--experiment-id", default=None)
    parser.add_argument("--max-cost-usd-per-model", type=float, default=200.0)
    parser.add_argument("--max-output-tokens", type=int, default=2048)
    parser.add_argument("--input-price-usd-per-1k", type=float, default=0.001)
    parser.add_argument("--output-price-usd-per-1k", type=float, default=0.003)
    parser.add_argument("--timeout-seconds", type=float, default=60.0)
    parser.add_argument("--max-workers", type=int, default=1)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--models", nargs="*", default=None)
    args = parser.parse_args()
    args.output_root = args.output_root.resolve()
    if args.provider == "openai" and (not args.allow_paid or args.max_cost_usd_per_model <= 0):
        raise SystemExit("real G5 requires --allow-paid and a positive per-model hard cap")
    if args.max_workers <= 0 or args.max_output_tokens <= 0:
        raise SystemExit("max-workers and max-output-tokens must be positive")
    data_dir = args.data_dir.resolve()
    public, answers, benchmark_manifest = load_tasks(data_dir)
    tasks = public[: args.limit] if args.limit is not None else public
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    models = load_models(args.model_config.resolve(), args.model_allowlist.resolve() if args.model_allowlist else None)
    if args.models:
        wanted = set(args.models)
        models = [row for row in models if row["model_id"] in wanted]
    if not models:
        raise SystemExit("no selected models")
    experiment_id = args.experiment_id or f"g5-answer-given-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    run_root = args.output_root.resolve() / experiment_id
    skill_zip = args.skill_zip.resolve()
    if not skill_zip.is_file():
        raise SystemExit(f"G5 skill archive is missing: {skill_zip}")
    if args.resume:
        if not args.experiment_id:
            raise SystemExit("--resume requires --experiment-id for an existing G5 run")
        run_manifest = read_json(run_root / "manifest.json")
        if not isinstance(run_manifest, dict) or run_manifest.get("mode") != "answer_given_reverse_reasoning":
            raise SystemExit(f"cannot resume non-G5 or missing run: {run_root}")
        if run_manifest.get("provider") != args.provider:
            raise SystemExit("resume provider does not match the original run")
        task_map = {str(task["task_id"]): task for task in public}
        tasks = [task_map[task_id] for task_id in run_manifest.get("task_ids", []) if task_id in task_map]
        models = list(run_manifest.get("models") or models)
        if args.models:
            wanted = set(args.models)
            models = [row for row in models if row.get("model_id") in wanted]
        if len(tasks) != len(run_manifest.get("task_ids", [])):
            raise SystemExit("resume benchmark task set no longer matches the saved manifest")
        if not (run_root / "run_state.json").is_file():
            atomic_write_json(run_root / "run_state.json", {"status": "RUNNING", "processed_models": [], "updated_at_utc": utc_now()})
    else:
        run_root.mkdir(parents=True, exist_ok=False)
        provenance_dir = run_root / "provenance"
        provenance_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_zip, provenance_dir / skill_zip.name)
        run_manifest = {
            "experiment_id": experiment_id,
            "mode": "answer_given_reverse_reasoning",
            "group": "G5",
            "separate_from": "G0_G4_answer_hidden",
            "results_root": str(run_root),
            "provider": args.provider,
            "base_url": args.base_url,
            "models": models,
            "tasks": len(tasks),
            "benchmark_version": benchmark_manifest.get("version"),
            "benchmark_manifest_sha256": sha256_value(benchmark_manifest),
            "skill_zip": str(skill_zip),
            "skill_zip_sha256": hashlib.sha256(skill_zip.read_bytes()).hexdigest(),
            "answer_exposure": "given_to_g5_only",
            "no_private_answer_access": True,
            "web_access": False,
            "cross_task_memory": False,
            "max_model_calls": MAX_MODEL_CALLS,
            "max_tool_calls": MAX_TOOL_CALLS,
            "max_revision_rounds": MAX_REVISION_ROUNDS,
            "max_total_tokens": MAX_TOTAL_TOKENS,
            "max_wall_time_seconds": MAX_WALL_SECONDS,
            "max_cost_usd_per_model": args.max_cost_usd_per_model,
            "cost_interpretation": "local input/output proxy; provider billing not independently verified",
            "resume_safe": True,
            "task_ids": [task["task_id"] for task in tasks],
            "started_at_utc": utc_now(),
        }
        atomic_write_json(run_root / "manifest.json", run_manifest)
        atomic_write_json(run_root / "run_state.json", {"status": "RUNNING", "processed_models": [], "updated_at_utc": utc_now()})
    print(json.dumps({"experiment_id": experiment_id, "models": [row["model_id"] for row in models], "tasks": len(tasks), "output": str(run_root), "provider": args.provider}, ensure_ascii=False), flush=True)
    results = []
    workers = min(args.max_workers, len(models))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(model_worker, args, experiment_id, model, tasks, answers): model["model_id"] for model in models}
        for future in as_completed(futures):
            model_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"model_id": model_id, "status": "WORKER_ERROR", "error_type": type(exc).__name__, "error": str(exc)}
            results.append(result)
            atomic_write_json(run_root / "run_state.json", {"status": "RUNNING", "processed_models": results, "updated_at_utc": utc_now()})
            print(json.dumps(result, ensure_ascii=False), flush=True)
    final = {"experiment_id": experiment_id, "status": "COMPLETED", "models": results, "finished_at_utc": utc_now(), "all_workers_finished": len(results) == len(models)}
    atomic_write_json(run_root / "run_summary.json", final)
    atomic_write_json(run_root / "run_state.json", {"status": "COMPLETED", "processed_models": results, "updated_at_utc": utc_now()})
    print(json.dumps(final, ensure_ascii=False), flush=True)
    return 0 if final["all_workers_finished"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
