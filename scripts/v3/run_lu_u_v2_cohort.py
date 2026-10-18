"""Run a public-only LU-v2 observed non-final-state transition cohort.

The cohort is separate from the frozen G7 denominator.  It supplies only
public graphs and a public premise intervention to the single base model.  A
transition is recorded only when it is present in the model response and in
the immutable provider trace; no private label or evaluator-derived arrow is
created after the call.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

try:
    from scripts.v3.lu_v2 import FORBIDDEN, validate_nonfinal_transition
except ModuleNotFoundError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from scripts.v3.lu_v2 import FORBIDDEN, validate_nonfinal_transition

try:
    from src.scientific_discovery.models.provider import OpenAICompatibleProvider
except ImportError:  # pragma: no cover
    OpenAICompatibleProvider = None  # type: ignore[assignment,misc]


BASE_URL = "https://token.ctflow.cn/v1"
REQUIRED_RESPONSE = {"claim_id", "state_before", "state_after", "to_status", "evidence"}
ALLOWED_STATUS = {"supported", "refuted", "unresolved"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def scan_forbidden(value: Any) -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if any(term in str(key).casefold() for term in FORBIDDEN):
                hits.append(str(key))
            hits.extend(scan_forbidden(child))
    elif isinstance(value, list):
        for child in value:
            hits.extend(scan_forbidden(child))
    elif isinstance(value, str):
        folded = value.casefold()
        if any(term in folded for term in FORBIDDEN):
            hits.append("string")
    return hits


def extract_json(content: str) -> dict[str, Any]:
    text = str(content or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("response is not an object")
    return value


def public_prompt(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = graph.get("nodes") or []
    intermediate = next((node for node in nodes if node.get("kind") == "intermediate"), None)
    if not isinstance(intermediate, dict):
        raise ValueError("graph has no non-final intermediate node")
    assumptions = []
    for edge in graph.get("edges", []):
        if edge.get("target_claim_id") == intermediate.get("claim_id"):
            assumptions.extend(edge.get("assumptions", []))
    return {
        "graph_id": graph["graph_id"],
        "intermediate_node": intermediate,
        "incoming_public_assumptions": assumptions,
        "public_intervention": "Remove only the first incoming assumption from the intermediate claim. Do not add data or use any hidden label.",
        "state_before": "supported",
    }


def messages(payload: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are in a public-only LU-v2 transition cohort. Return only one compact JSON object with exactly "
                "claim_id, state_before, state_after, to_status, evidence. Use the supplied intermediate claim ID. "
                "state_before must be supported; to_status and state_after must each be supported, refuted, or unresolved. "
                "Report only the result of the public premise intervention. Do not mention hidden labels, answer keys, "
                "private files, or routing metadata."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--graphs", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--model-id", default="kimi-k2.5")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--key-file", type=Path, default=Path("api_key/kimi/kimi-k2.5.txt"))
    parser.add_argument("--allow-paid", action="store_true")
    parser.add_argument("--allow-user-authorized-unverified-pricing", action="store_true")
    parser.add_argument("--cost-ledger", type=Path)
    parser.add_argument("--max-cost-usd", type=float, default=10.0)
    parser.add_argument("--max-output-tokens", type=int, default=256)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()

    graphs = read_jsonl(args.graphs)
    selected = []
    for graph in graphs:
        payload = public_prompt(graph)
        if scan_forbidden(payload):
            raise ValueError(f"public graph contains forbidden material: {graph.get('graph_id')}")
        selected.append((graph, payload))
    plan = {
        "protocol_id": "LU_V2_PUBLIC_U_TRANSITION_COHORT",
        "model_id": args.model_id,
        "base_url": args.base_url,
        "graphs_sha256": sha256_file(args.graphs),
        "graph_count": len(selected),
        "private_labels_read": False,
        "answer_key_read": False,
        "pooling_with_frozen_g7": False,
        "formal_scientific_run_allowed": False,
        "pricing_override_used": bool(args.allow_user_authorized_unverified_pricing and not args.preflight_only),
        "execution_status": "PREFLIGHT_ONLY" if args.preflight_only else "READY",
    }
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "cohort_plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.preflight_only:
        print(json.dumps({**plan, "status": "PREFLIGHT_PASS"}, ensure_ascii=False))
        return 0
    if not args.allow_paid:
        raise SystemExit("real LU U cohort requires --allow-paid")
    if not args.cost_ledger:
        raise SystemExit("real LU U cohort requires --cost-ledger")
    if OpenAICompatibleProvider is None:
        raise SystemExit("provider adapter unavailable")
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("provider key is empty")
    from scripts.audit_repair.cost_ledger import CostLedger

    ledger = CostLedger(args.cost_ledger, global_cap=200.0, g7_cap=60.0, worker_cap=args.max_cost_usd)
    provider = OpenAICompatibleProvider(
        api_key=key,
        base_url=args.base_url,
        model_name=args.model_id,
        timeout=args.timeout,
        max_retries=0,
        input_cost_per_1k=0.001,
        output_cost_per_1k=0.003,
        max_cost_usd=args.max_cost_usd,
        max_output_tokens=args.max_output_tokens,
        reservation_output_tokens=args.max_output_tokens,
        cost_ledger=ledger,
        ledger_scope="g7",
        ledger_worker="lu-u-v2",
        ledger_ref_prefix="lu-u-v2",
        require_cost_ledger=True,
    )
    records: list[dict[str, Any]] = []
    traces_path = args.out / "provider_traces.jsonl"
    records_path = args.out / "u_records.jsonl"
    traces_path.write_text("", encoding="utf-8")
    records_path.write_text("", encoding="utf-8")
    for graph, payload in selected:
        provider_error = None
        response = None
        try:
            response = provider.complete(messages(payload))
            candidate = extract_json(response.content)
        except Exception as exc:  # preserve a typed non-success record
            provider_error = f"{type(exc).__name__}:{str(exc)[:240]}"
            candidate = None
        trace = provider.audit_trace()[-1] if provider.audit_trace() else {"error": provider_error}
        trace = {**trace, "graph_id": graph["graph_id"]}
        with traces_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(trace, ensure_ascii=False, separators=(",", ":")) + "\n")
        transition = None
        validation_error = None
        if candidate is not None:
            if set(candidate) != REQUIRED_RESPONSE:
                validation_error = "response schema mismatch"
            elif candidate.get("claim_id") != next(node["claim_id"] for node in graph["nodes"] if node.get("kind") == "intermediate"):
                validation_error = "response claim is not the public intermediate node"
            elif candidate.get("state_before") != "supported" or candidate.get("state_after") not in ALLOWED_STATUS or candidate.get("to_status") not in ALLOWED_STATUS:
                validation_error = "response state/status invalid"
            elif candidate.get("state_after") == "supported":
                validation_error = "no observed state change"
            else:
                transition = {
                    "state_before": candidate["state_before"],
                    "state_after": candidate["state_after"],
                    "claim_id": candidate["claim_id"],
                    "to_status": candidate["to_status"],
                    "trace_ref": f"provider_traces.jsonl:{len(records) + 1}",
                    "source": "OBSERVED_MODEL_STATE",
                }
                try:
                    validate_nonfinal_transition(graph, transition)
                except ValueError as exc:
                    validation_error = str(exc)
                    transition = None
        record = {
            "protocol_id": "LU_V2_PUBLIC_U_TRANSITION_COHORT",
            "graph_id": graph["graph_id"],
            "candidate": candidate,
            "transition": transition,
            "provider_usage": response.usage.__dict__ if response is not None else {},
            "provider_error": provider_error,
            "validation_error": validation_error,
            "private_labels_read": False,
        }
        records.append(record)
        with records_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
    result = {
        **plan,
        "execution_status": "USER_AUTHORIZED_UNVERIFIED_PRICING_NONCONFIRMATORY",
        "provider_calls_made": len(records),
        "provider_successful_responses": sum(bool(record["provider_usage"]) for record in records),
        "observed_transition_count": sum(record["transition"] is not None for record in records),
        "validation_error_counts": {},
    }
    for record in records:
        key = record["validation_error"] or "none"
        result["validation_error_counts"][key] = result["validation_error_counts"].get(key, 0) + 1
    (args.out / "cohort_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
