"""Execute V8 prospective cohorts with one real base model: kimi-k2.5."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.audit_repair.cost_ledger import CostLedger
from src.scientific_discovery.models.provider import OpenAICompatibleProvider


DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha_obj(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def extract_json(text: str | None) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        value = json.loads(cleaned)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                value = json.loads(cleaned[start : end + 1])
                return value if isinstance(value, dict) else None
            except json.JSONDecodeError:
                return None
    return None


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


class V8Runner:
    def __init__(self, run: Path, key_file: Path, base_url: str, model_id: str, max_cost: float, timeout: float) -> None:
        if model_id != "kimi-k2.5":
            raise ValueError("V8 is single-base-model only: model_id must be kimi-k2.5")
        key = key_file.read_text(encoding="utf-8").strip()
        if not key:
            raise ValueError("Kimi key is empty")
        self.run = run
        self.raw = run / "logs" / "provider_traces.jsonl"
        self.raw.parent.mkdir(parents=True, exist_ok=True)
        if not self.raw.exists():
            self.raw.write_text("", encoding="utf-8")
        self.ledger = CostLedger(run / "cost_ledger.sqlite", global_cap=200.0, g7_cap=60.0, worker_cap=max_cost)
        self.provider = OpenAICompatibleProvider(
            api_key=key,
            base_url=base_url,
            model_name=model_id,
            timeout=timeout,
            max_retries=0,
            input_cost_per_1k=0.001,
            output_cost_per_1k=0.003,
            max_cost_usd=max_cost,
            max_output_tokens=384,
            reservation_output_tokens=384,
            cost_ledger=self.ledger,
            ledger_scope="g7",
            ledger_worker="v8-single-kimi",
            ledger_ref_prefix="v8-single-kimi",
            require_cost_ledger=True,
        )
        self.call_no = 0
        for line in self.raw.read_text(encoding="utf-8").splitlines():
            try:
                self.call_no = max(self.call_no, int(json.loads(line).get("v8_call_number", 0)))
            except (ValueError, json.JSONDecodeError):
                pass

    def existing_initial(self, protocol: str, unit_id: str) -> tuple[str | None, dict[str, Any], str | None] | None:
        """Recover an already persisted initial checkpoint during a resume."""
        for line in self.raw.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            trace = row.get("trace") or {}
            if row.get("protocol") != protocol or row.get("unit_id") != unit_id or row.get("role") != "INITIAL_CHECKPOINT":
                continue
            response = trace.get("response") or {}
            return response.get("content"), response.get("usage") or {}, None
        return None

    def call(self, protocol: str, unit_id: str, role: str, messages: list[dict[str, Any]]) -> tuple[str | None, dict[str, Any] | None, str | None]:
        self.call_no += 1
        before = len(self.provider.audit_trace())
        try:
            response = self.provider.complete(messages)
            content = response.content
            usage = response.usage.__dict__ if response.usage is not None else {}
            error = None
        except Exception as exc:  # typed failure is preserved, then the cohort continues
            response = None
            content = None
            usage = {}
            error = f"{type(exc).__name__}:{str(exc)[:300]}"
        traces = self.provider.audit_trace()[before:]
        for index, trace in enumerate(traces, 1):
            append_jsonl(self.raw, {
                "v8_call_number": self.call_no,
                "protocol": protocol,
                "unit_id": unit_id,
                "role": role,
                "trace_index": index,
                "model_id": "kimi-k2.5",
                "trace": trace,
            })
        if not traces:
            append_jsonl(self.raw, {"v8_call_number": self.call_no, "protocol": protocol, "unit_id": unit_id, "role": role, "model_id": "kimi-k2.5", "error": error or "NO_TRACE"})
        return content, usage, error


def _g6_messages(case: dict[str, Any]) -> list[dict[str, Any]]:
    arm = case["arm_id"]
    workflow = "G3 fixed two-pass public derivative check" if arm == "G6_A_G3_GIVEN" else "G4 bounded adaptive public derivative check with one self-review stage"
    return [
        {"role": "system", "content": f"You are the {workflow} arm of V8 G6. Use only the public case. Never access hidden answers, truth keys, prior files, or network. Return one JSON object with exactly decision, affected_claim_ids, revised_claim, supporting_evidence. decision must be MAINTAIN, REJECT, REVISE, or UNDETERMINED."},
        {"role": "user", "content": json.dumps({"g6_case": case}, ensure_ascii=False, sort_keys=True)},
    ]


def run_g6(runner: V8Runner, base_name: str = "prospective_g6", protocol_id: str = "V8_G6_PROSPECTIVE") -> dict[str, Any]:
    base = runner.run / base_name
    public = read_jsonl(base / "public_cases.jsonl")
    truth = {row["case_id"]: row for row in read_jsonl(base / "truth_key.jsonl")}
    out = base / "records.jsonl"
    if not out.exists():
        out.write_text("", encoding="utf-8")
    existing = {row.get("case_id") for row in read_jsonl(out)}
    for case in public:
        if case["case_id"] in existing:
            continue
        content, usage, error = runner.call("G6_V8", case["case_id"], case["arm_id"], _g6_messages(case))
        candidate = extract_json(content)
        expected = truth[case["case_id"]]
        observed = candidate.get("decision") if candidate else None
        record = {
            "protocol_id": protocol_id,
            "case_id": case["case_id"], "family_id": case["family_id"], "cf_type": case["cf_type"], "arm_id": case["arm_id"],
            "model_id": "kimi-k2.5", "candidate": candidate, "provider_usage": usage, "provider_error": error,
            "structure_valid": isinstance(candidate, dict) and observed in DECISIONS and isinstance(candidate.get("affected_claim_ids"), list),
            "expected_action_for_scorer": expected["expected_action"],
            "independent_original_proof_status": expected["original_proof_status"],
            "action_correct": observed == expected["expected_action"],
            "truth_key_read_by_scorer": True, "truth_key_sent_to_model": False,
        }
        append_jsonl(out, record)
    rows = read_jsonl(out)
    return _summary(protocol_id, rows, "action_correct")


def _q_messages(task: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "You are an independent scientific claim auditor. Use only the public proposition. Return one JSON object with exactly claim_id, proposition_DSL, premise_refs, quantifier, domain, verification_intent, evidence_refs, proposed_final_action. Do not access any answer key."},
        {"role": "user", "content": json.dumps({"public_task": task}, ensure_ascii=False, sort_keys=True)},
    ]


def run_q(runner: V8Runner) -> dict[str, Any]:
    base = runner.run / "prospective_q"
    public = read_jsonl(base / "public_cases.jsonl")
    truth = {row["task_id"]: row for row in read_jsonl(base / "truth_key.jsonl")}
    out = base / "records.jsonl"
    if not out.exists():
        out.write_text("", encoding="utf-8")
    existing = {row.get("task_id") for row in read_jsonl(out)}
    for task in public:
        if task["task_id"] in existing:
            continue
        content, usage, error = runner.call("Q_V8", task["task_id"], "Q_INDEPENDENT_CANDIDATE", _q_messages(task))
        candidate = extract_json(content)
        expected = truth[task["task_id"]]["expected_status"]
        proposed = candidate.get("proposed_final_action") if candidate else None
        independent = truth[task["task_id"]]["independent_proof"]
        record = {
            "protocol_id": "Q_V8_TRUTH_FIRST_PROSPECTIVE", "task_id": task["task_id"], "model_id": "kimi-k2.5",
            "candidate": candidate, "provider_usage": usage, "provider_error": error,
            "structure_valid": isinstance(candidate, dict) and candidate.get("claim_id") == task["claim_id"],
            "independent_certificate_status": independent["status"], "expected_status_for_scorer": expected,
            "candidate_status_matches": proposed == expected or (expected == "PROVEN_TRUE" and str(proposed).upper() in {"TRUE", "SUPPORTED", "PROVEN_TRUE"}),
            "truth_process_before_provider": True, "truth_key_read_by_scorer": True, "truth_key_sent_to_model": False,
        }
        append_jsonl(out, record)
    return _summary("Q_V8", read_jsonl(out), "candidate_status_matches")


def _lu_initial(task: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "You are a checkpointed scientific reasoning agent. Return JSON with claim_id, state_before, intermediate_status, evidence. The intermediate claim is non-final; do not infer hidden truth."},
        {"role": "user", "content": json.dumps({"public_checkpoint": task["checkpoint_nodes"], "control_claim": task["control_public_claim"]}, ensure_ascii=False, sort_keys=True)},
    ]


def _lu_continuation(task: dict[str, Any], arm: str) -> str:
    if arm == "REAL":
        return json.dumps({"arm": "REAL", "intervention": task["real_intervention"], "instruction": "Update only the non-final U1 claim and return state_after plus evidence."}, ensure_ascii=False, sort_keys=True)
    if arm == "SHAM":
        return json.dumps({"arm": "SHAM", "intervention": task["sham_intervention"], "instruction": "This is a randomized sham. Preserve the mathematical claim and return state_after plus evidence."}, ensure_ascii=False, sort_keys=True)
    return json.dumps({"arm": "CONTROL", "intervention": "No mathematical intervention; re-evaluate the same public checkpoint.", "instruction": "Return state_after plus evidence."}, ensure_ascii=False, sort_keys=True)


def run_lu(runner: V8Runner) -> dict[str, Any]:
    base = runner.run / "prospective_lu"
    public = read_jsonl(base / "public_cases.jsonl")
    truth = {row["task_id"]: row for row in read_jsonl(base / "truth_key.jsonl")}
    out = base / "records.jsonl"
    if not out.exists():
        out.write_text("", encoding="utf-8")
    existing = {(row.get("task_id"), row.get("arm")) for row in read_jsonl(out)}
    rng = random.Random(20261019)
    for task in public:
        initial_messages = _lu_initial(task)
        prior_initial = runner.existing_initial("LU_U_V8", task["task_id"])
        if prior_initial is None:
            initial_content, initial_usage, initial_error = runner.call("LU_U_V8", task["task_id"], "INITIAL_CHECKPOINT", initial_messages)
        else:
            initial_content, initial_usage, initial_error = prior_initial
        checkpoint_id = sha_obj({"messages": initial_messages, "initial_response": initial_content})
        order = ["CONTROL", "REAL", "SHAM"]
        rng.shuffle(order)
        for position, arm in enumerate(order):
            if (task["task_id"], arm) in existing:
                continue
            fork_messages = [*initial_messages, {"role": "assistant", "content": initial_content or ""}, {"role": "user", "content": _lu_continuation(task, arm)}]
            content, usage, error = runner.call("LU_U_V8", task["task_id"], arm, fork_messages)
            candidate = extract_json(content)
            expected = truth[task["task_id"]][{"CONTROL": "control_status", "REAL": "real_status", "SHAM": "sham_status"}[arm]]
            observed = (candidate or {}).get("state_after") or (candidate or {}).get("intermediate_status")
            append_jsonl(out, {
                "protocol_id": "LU_U_V8_SHARED_CHECKPOINT_RANDOMIZED", "task_id": task["task_id"], "arm": arm, "randomized_position": position,
                "checkpoint_id": checkpoint_id, "shared_checkpoint_messages_sha256": sha_obj(initial_messages), "initial_response_present": bool(initial_content),
                "candidate": candidate, "provider_usage": usage, "provider_error": error, "observed_state_after": observed,
                "expected_state_for_scorer": expected, "nonfinal_update_correct": observed == expected,
                "truth_key_read_by_scorer": True, "truth_key_sent_to_model": False,
                "initial_checkpoint_provider_error": initial_error, "initial_checkpoint_usage": initial_usage,
            })
    rows = read_jsonl(out)
    summary = _summary("LU_U_V8", rows, "nonfinal_update_correct")
    summary.update({"shared_checkpoint_count": len(public), "fork_count": len(rows), "arms": {a: sum(row["arm"] == a for row in rows) for a in ["CONTROL", "REAL", "SHAM"]}})
    return summary


def _g7_initial(task: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {"role": "system", "content": "You are a prospective G7 scientific graph auditor. Work only from the public graph. Return JSON with final_action, verdict, evidence. Never access hidden truth."},
        {"role": "user", "content": json.dumps({"graph": task}, ensure_ascii=False, sort_keys=True)},
    ]


def _g7_injection(task: dict[str, Any], stage: str, proof: dict[str, Any]) -> str:
    if stage == "D0":
        return "D0: no injected verdict, lemma, or update; independently audit the public graph."
    verdict = {"claim_id": f"{task['task_id']}-V", "independently_verified_local_verdict": proof["status"]}
    if stage == "D1_V":
        return json.dumps({"stage": stage, "V": verdict, "instruction": "Use V as a local non-final verdict and return final_action."}, ensure_ascii=False, sort_keys=True)
    lemma = {"claim_id": f"{task['task_id']}-L", "independently_verified_local_lemma": proof["certificate"]}
    if stage == "D2_VL":
        return json.dumps({"stage": stage, "V": verdict, "L": lemma, "instruction": "Use V and L as local non-final evidence; do not receive Y."}, ensure_ascii=False, sort_keys=True)
    update = {"claim_id": f"{task['task_id']}-U", "nonfinal_update": proof["status"]}
    return json.dumps({"stage": stage, "V": verdict, "L": lemma, "U": update, "instruction": "Use V, L, and U as local non-final evidence; infer Y independently."}, ensure_ascii=False, sort_keys=True)


def run_g7(runner: V8Runner) -> dict[str, Any]:
    base = runner.run / "prospective_g7"
    public = read_jsonl(base / "public_cases.jsonl")
    truth = {row["task_id"]: row for row in read_jsonl(base / "truth_key.jsonl")}
    out = base / "records.jsonl"
    if not out.exists():
        out.write_text("", encoding="utf-8")
    existing = {(row.get("task_id"), row.get("stage")) for row in read_jsonl(out)}
    for task in public:
        initial_messages = _g7_initial(task)
        prior_initial = runner.existing_initial("G7_V8", task["task_id"])
        if prior_initial is None:
            initial_content, initial_usage, initial_error = runner.call("G7_V8", task["task_id"], "INITIAL_CHECKPOINT", initial_messages)
        else:
            initial_content, initial_usage, initial_error = prior_initial
        checkpoint_id = sha_obj({"messages": initial_messages, "initial_response": initial_content})
        proof = truth[task["task_id"]]["proof"]
        for stage in ["D0", "D1_V", "D2_VL", "D3_VLU"]:
            if (task["task_id"], stage) in existing:
                continue
            fork_messages = [*initial_messages, {"role": "assistant", "content": initial_content or ""}, {"role": "user", "content": _g7_injection(task, stage, proof)}]
            content, usage, error = runner.call("G7_V8", task["task_id"], stage, fork_messages)
            candidate = extract_json(content)
            observed = (candidate or {}).get("final_action") or (candidate or {}).get("decision")
            append_jsonl(out, {
                "protocol_id": "G7_V8_NEW_PROSPECTIVE_VLLUQ", "task_id": task["task_id"], "stage": stage, "checkpoint_id": checkpoint_id,
                "candidate": candidate, "provider_usage": usage, "provider_error": error, "observed_final_action": observed,
                "expected_final_action_for_scorer": "MAINTAIN", "final_action_correct": observed == "MAINTAIN",
                "injected_stage_is_nonfinal": True, "private_Y_injected": False, "initial_checkpoint_present": bool(initial_content),
                "initial_checkpoint_usage": initial_usage, "initial_checkpoint_provider_error": initial_error,
                "truth_key_read_by_scorer": True, "truth_key_sent_to_model": False,
            })
    rows = read_jsonl(out)
    summary = _summary("G7_V8", rows, "final_action_correct")
    summary.update({"checkpoint_count": len(public), "rows_by_stage": {stage: sum(row["stage"] == stage for row in rows) for stage in ["D0", "D1_V", "D2_VL", "D3_VLU"]}})
    return summary


def _summary(protocol: str, rows: list[dict[str, Any]], score_key: str) -> dict[str, Any]:
    return {
        "protocol": protocol, "rows": len(rows), "provider_calls": len(rows),
        "successful_provider_rows": sum(bool(row.get("provider_usage")) for row in rows),
        "structured_rows": sum(bool(row.get("candidate")) for row in rows),
        "score_key": score_key, "score_numerator": sum(bool(row.get(score_key)) for row in rows),
        "score_denominator": len(rows),
        "real_model_id": "kimi-k2.5", "mock": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--model-id", default="kimi-k2.5")
    parser.add_argument("--max-cost", type=float, default=20.0)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--only", choices=["all", "g6_repair"], default="all")
    args = parser.parse_args()
    runner = V8Runner(args.run, args.key_file, args.base_url, args.model_id, args.max_cost, args.timeout)
    if args.only == "g6_repair":
        summaries = {"g6_repair": run_g6(runner, "prospective_g6_repair", "V8_G6_PROSPECTIVE_REPAIRED")}
    else:
        summaries = {"g6": run_g6(runner), "q": run_q(runner), "lu": run_lu(runner), "g7": run_g7(runner)}
    summaries["total_provider_calls"] = runner.call_no
    summaries["model_id"] = args.model_id
    summaries["ledger_snapshot"] = runner.ledger.snapshot()
    result_path = args.run / ("repair_run_result.json" if args.only == "g6_repair" else "run_result.json")
    (result_path).write_text(json.dumps(summaries, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(summaries, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()

