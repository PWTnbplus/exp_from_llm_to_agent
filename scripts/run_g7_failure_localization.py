#!/usr/bin/env python3
"""Real-provider G7 checkpoint/fork runner.

The runner is intentionally separate from ``g7_offline.py``.  It reads public
cases and the independently reviewed G7 local labels only to apply the
diagnostic intervention; it never sends the G6 private oracle or prior G6
model answers to the provider.  Checkpoints are actual new provider calls and
are never backfilled from G6.

The response contract below is deliberately explicit because malformed stage
objects are recorded as invalid provider attempts, not silently repaired.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from src.scientific_discovery.models.provider import OpenAICompatibleProvider, ProviderResponse
from run_g6_counterfactual import TOOLS, execute_tool, parse_tool_args, extract_json


DECISIONS = {"MAINTAIN", "REJECT", "REVISE", "UNDETERMINED"}
FORBIDDEN_MODEL_KEYS = (
    "expected_decision",
    "affected_claim_ids",
    "oracle_affected_claim_ids",
    "oracle_reason",
    "correct_revised_claim",
    "counterexample",
    "private_oracle",
    "g6_private_oracle",
    "source_g6_oracle",
    "ground_truth",
    "answer_key",
    "verification_code",
    "verification_status",
    "verification_grade",
    "verifier_ref",
    "u_ineligibility_reason",
    "eligible_u",
    "verifier_status",
    "V_true",
    "L_true_impacted_nodes",
    "U_true_node_changes",
)
ROUTING_METADATA_KEYS = ("cf_type", "theory_family_id")
FORMAT_RETRY_INSTRUCTION = (
    "The previous response failed the required JSON contract. Return only one JSON object with the required fields; "
    "do not call tools or add hidden information. For a diagnostic fork, put V, L, U, and Q as objects in the "
    "top-level stages field (not inside supporting_evidence): stages must contain stages.V={verdict}, "
    "L={nodes,edges}, U={node_changes}, and stages.Q={verdict,reason}; use empty arrays for genuinely empty L/U fields."
)
G7_GROUPS = {"G3", "G4"}
G7_STAGES = {"V", "L", "U"}
G7_ARM_CONTRACT = {
    "D0": (),
    "D1": ("V",),
    "D2": ("V", "L"),
    "D3": ("V", "L", "U"),
    "L_ONLY": ("L",),
    "U_ONLY": ("U",),
    "V_ONLY": ("V",),
}
G7_PUBLIC_METADATA_FIELDS = (
    "paired_set_id", "source_task_id", "theory_family_id", "domain", "cf_type",
    "split", "quantifier", "source_g5_graph_sha256", "verification_grade",
)
G7_LABEL_METADATA_FIELDS = (
    "source_public_case_sha256", "verification_grade", "verification_method",
    "verifier_ref",
)
G7_PLAN_METADATA_FIELDS = (
    "paired_set_id", "theory_family_id", "cf_type", "split", "source_g6_arm_id",
    "source_run_id", "source_checkpoint_id", "profile", "protocol_version",
    "retry_scope", "retry_protocol",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def readl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: expected JSON object")
            rows.append(value)
    return rows


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def sha256_file(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def validate_paid_evidence(model_id: str, snapshot_manifest: Path | None,
                            billing_export: Path | None) -> dict[str, Any]:
    """Validate local evidence required before any real G7 provider call.

    This is a fail-closed machine gate, not an external attestation. The raw
    manifest/export contents are never copied into the run report; only
    structural checks and file hashes are retained. Structurally valid local
    files remain explicitly marked as PRESENT_UNVERIFIED_EXTERNAL until an
    independent reviewer verifies them.
    """

    def load_object(path: Path | None, kind: str) -> tuple[dict[str, Any] | None, list[str], str | None]:
        errors: list[str] = []
        if path is None:
            errors.append(f"{kind}_required")
            return None, errors, None
        if not path.is_file():
            errors.append(f"{kind}_not_found")
            return None, errors, None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            errors.append(f"{kind}_invalid_json")
            return None, errors, sha256_file(path)
        if not isinstance(value, dict):
            errors.append(f"{kind}_must_be_object")
            return None, errors, sha256_file(path)
        return value, errors, sha256_file(path)

    snapshot, snapshot_errors, snapshot_file_sha256 = load_object(snapshot_manifest, "model_snapshot_manifest")
    billing, billing_errors, billing_file_sha256 = load_object(billing_export, "billing_export")
    errors = [*snapshot_errors, *billing_errors]

    snapshot_checks = {
        "file_sha256": snapshot_file_sha256,
        "model_id_matches": False,
        "gateway_weight_fingerprint_present": False,
        "snapshot_sha256_valid": False,
    }
    if snapshot is not None:
        snapshot_checks["model_id_matches"] = snapshot.get("model_id") == model_id
        if not snapshot_checks["model_id_matches"]:
            errors.append("model_snapshot_model_id_mismatch")
        fingerprint = snapshot.get("gateway_weight_fingerprint")
        false_like = {"", "false", "none", "null", "n/a", "na", "unknown", "missing"}
        snapshot_checks["gateway_weight_fingerprint_present"] = (
            isinstance(fingerprint, str) and fingerprint.strip().casefold() not in false_like
        )
        if not snapshot_checks["gateway_weight_fingerprint_present"]:
            errors.append("model_snapshot_gateway_weight_fingerprint_missing")
        snapshot_checks["snapshot_sha256_valid"] = _valid_sha256(snapshot.get("snapshot_sha256"))
        if not snapshot_checks["snapshot_sha256_valid"]:
            errors.append("model_snapshot_sha256_invalid")

    billing_checks = {
        "file_sha256": billing_file_sha256,
        "receipt_id_present": False,
        "currency_usd": False,
        "total_cost_usd_valid": False,
        "exported_at_utc_valid": False,
    }
    if billing is not None:
        receipt_id = billing.get("receipt_id")
        billing_checks["receipt_id_present"] = isinstance(receipt_id, str) and bool(receipt_id.strip())
        if not billing_checks["receipt_id_present"]:
            errors.append("billing_receipt_id_missing")
        currency = billing.get("currency")
        billing_checks["currency_usd"] = isinstance(currency, str) and currency.upper() == "USD"
        if not billing_checks["currency_usd"]:
            errors.append("billing_currency_must_be_usd")
        total_cost = billing.get("total_cost_usd")
        billing_checks["total_cost_usd_valid"] = (
            isinstance(total_cost, (int, float))
            and not isinstance(total_cost, bool)
            and math.isfinite(float(total_cost))
            and float(total_cost) >= 0
        )
        if not billing_checks["total_cost_usd_valid"]:
            errors.append("billing_total_cost_invalid")
        exported_at = billing.get("exported_at_utc")
        try:
            parsed_exported_at = datetime.fromisoformat(exported_at) if isinstance(exported_at, str) else None
        except ValueError:
            parsed_exported_at = None
        billing_checks["exported_at_utc_valid"] = (
            parsed_exported_at is not None
            and parsed_exported_at.tzinfo is not None
            and parsed_exported_at.utcoffset() == timezone.utc.utcoffset(parsed_exported_at)
        )
        if not billing_checks["exported_at_utc_valid"]:
            errors.append("billing_exported_at_utc_invalid")

    return {
        "required": True,
        "evidence_status": "PRESENT_UNVERIFIED_EXTERNAL" if not errors else "MISSING_OR_INVALID",
        "local_evidence_schema_valid": not errors,
        "errors": errors,
        "model_snapshot_manifest": {
            "path": str(snapshot_manifest) if snapshot_manifest is not None else None,
            "checks": snapshot_checks,
        },
        "billing_export": {
            "path": str(billing_export) if billing_export is not None else None,
            "checks": billing_checks,
        },
        "external_verification_claimed": False,
        "scientific_truth_decision_made": False,
    }


def existing_trace_sequence(path: Path) -> int:
    """Return the last persisted sequence for an append-only retry trace."""
    if not path.is_file():
        return 0
    values = readl(path)
    sequences: list[int] = []
    for index, value in enumerate(values, 1):
        sequence = value.get("seq")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise RuntimeError(f"existing trace has invalid sequence at line {index}: {path}")
        sequences.append(sequence)
    if len(sequences) != len(set(sequences)):
        raise RuntimeError(f"existing trace has duplicate sequence values: {path}")
    return max(sequences, default=0)


def emit(path: Path, seq: int, run_id: str, event_type: str, status: str,
         payload: dict[str, Any]) -> int:
    seq += 1
    event = {
        "seq": seq,
        "event_id": f"{run_id}:event-{seq:06d}",
        "step_id": f"{run_id}:step-{seq:06d}",
        "parent_step_id": (
            f"{run_id}:step-{seq - 1:06d}"
            if event_type in {"MODEL_RESPONSE", "TOOL_RESULT", "TOOL_ERROR"}
            else None
        ),
        "ts_utc": utc_now(),
        "run_id": run_id,
        "event_type": event_type,
        "status": status,
        "payload": payload,
    }
    append_jsonl(path, event)
    return seq


def parse_payload(content: str) -> dict[str, Any]:
    value = extract_json(content)
    if not isinstance(value, dict):
        raise ValueError("provider response did not contain a JSON object")
    decision = str(value.get("decision", value.get("final_decision", ""))).upper().strip()
    if decision not in DECISIONS:
        raise ValueError(f"invalid decision {decision!r}")
    value["decision"] = decision
    return value


def normalize_stages(value: dict[str, Any]) -> dict[str, Any]:
    stages = value.get("stages")
    if not isinstance(stages, dict):
        raise ValueError("missing stages object")
    for stage in ("V", "L", "U", "Q"):
        if stage not in stages or not isinstance(stages[stage], dict):
            raise ValueError(f"missing stage {stage}")
    if (
        set(stages["V"]) != {"verdict"}
        or stages["V"].get("verdict") not in {"SUPPORTED", "CONTRADICTED", "INDETERMINATE"}
    ):
        raise ValueError("invalid V verdict")
    l_stage = stages["L"]
    if (
        set(l_stage) != {"nodes", "edges"}
        or not isinstance(l_stage.get("nodes"), list)
        or not all(isinstance(node, str) and bool(node.strip()) for node in l_stage["nodes"])
        or not isinstance(l_stage.get("edges"), list)
        or not all(
            isinstance(edge, dict)
            and set(edge) == {"from", "to"}
            and isinstance(edge["from"], str)
            and bool(edge["from"].strip())
            and isinstance(edge["to"], str)
            and bool(edge["to"].strip())
            for edge in l_stage["edges"]
        )
    ):
        raise ValueError("invalid L stage")
    u_stage = stages["U"]
    if (
        set(u_stage) != {"node_changes"}
        or not isinstance(u_stage.get("node_changes"), list)
        or not all(
            isinstance(change, dict)
            and set(change) == {"claim_id", "to_status"}
            and isinstance(change["claim_id"], str)
            and bool(change["claim_id"].strip())
            and change["to_status"] in {"supported", "rejected", "uncertain"}
            for change in u_stage["node_changes"]
        )
    ):
        raise ValueError("invalid U stage")
    q_stage = stages["Q"]
    if set(q_stage) != {"verdict", "reason"}:
        raise ValueError("invalid Q stage")
    q_verdict = q_stage.get("verdict")
    q_reason = q_stage.get("reason")
    if (not isinstance(q_verdict, str) or not q_verdict.strip()
            or not isinstance(q_reason, str) or not q_reason.strip()):
        raise ValueError("invalid Q stage")
    return stages


def system_prompt(group: str) -> str:
    if group == "G3":
        protocol = ("You are the frozen G3 Tools+Iteration checkpoint/fork arm. Use only the bounded public-expression tools, "
                    "and use a fixed second synthesis pass. Do not change the workflow based on hidden information.")
    else:
        protocol = ("You are the adaptive G4 checkpoint/fork arm. You may use only the bounded public-expression tools "
                    "and may condition later public tool calls on their observable outputs.")
    return f"""You are a real-provider participant in experiment g7_failure_localization, profile theory_benchmark.
{protocol}
The case is public and contains a scientific problem, claim, intervention, and public proof graph.
Never access files, network, hidden answers, G6 private oracle records, prior G6 responses, or answer keys.
For a checkpoint, reason from the public case only and return JSON with decision, affected_claim_ids,
revised_claim, supporting_evidence. For a diagnostic fork, the user message may contain staged V/L/U
diagnostic information. Apply only the stages explicitly supplied, then return JSON with exactly:
decision, affected_claim_ids, revised_claim, supporting_evidence, stages. stages must contain:
V={{"verdict":"SUPPORTED|CONTRADICTED|INDETERMINATE"}},
L={{"nodes":[claim_id strings],"edges":[{{"from":claim_id,"to":claim_id}}]}},
U={{"node_changes":[{{"claim_id":claim_id,"to_status":"supported|rejected|uncertain"}}]}},
and Q={{"verdict":string,"reason":string}}. Use empty arrays when there are no edges or
node changes. Do not use decision labels such as REJECT in V.verdict, do not use arrow strings
for L edges, and do not use an object/map for U.node_changes. decision values are MAINTAIN,
REJECT, REVISE, or UNDETERMINED. Do not reveal hidden chain-of-thought."""


def case_prompt(case: dict[str, Any]) -> str:
    # cf_type and theory_family_id are runner/statistical metadata.  They are
    # intentionally not exposed in the model-facing prompt: the G7 protocol
    # allows them for routing and stratification, but not as predictive hints.
    model_visible = case.get("model_visible")
    if not isinstance(model_visible, dict):
        raise ValueError("case model_visible must be an object")
    return json.dumps({"g7_public_case": model_visible, "case_id": case["case_id"]},
                      ensure_ascii=False)


def _key_hits(text: str, keys: tuple[str, ...]) -> dict[str, int]:
    folded = text.casefold()
    return {key: folded.count(key.casefold()) for key in keys if key.casefold() in folded}


def _valid_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-fA-F]{64}", value))


def _row_identifier(value: Any, index: int) -> str:
    return value if isinstance(value, str) and value else f"row-{index}"


def _label_contract_valid(row: dict[str, Any]) -> bool:
    """Validate private V/L/U label shape before any provider can be called."""
    v = row.get("v")
    l = row.get("l")
    u = row.get("u")
    if not (
        isinstance(v, dict)
        and set(v) == {"verdict"}
        and v.get("verdict") in {"SUPPORTED", "CONTRADICTED", "INDETERMINATE"}
        and isinstance(l, dict)
        and set(l) == {"nodes", "edges"}
        and isinstance(l.get("nodes"), list)
        and all(isinstance(node, str) and bool(node.strip()) for node in l["nodes"])
        and isinstance(l.get("edges"), list)
        and all(
            isinstance(edge, dict)
            and set(edge) == {"from", "to"}
            and isinstance(edge["from"], str)
            and bool(edge["from"].strip())
            and isinstance(edge["to"], str)
            and bool(edge["to"].strip())
            for edge in l["edges"]
        )
        and isinstance(u, dict)
        and set(u) == {"node_changes"}
        and isinstance(u.get("node_changes"), list)
        and all(
            isinstance(change, dict)
            and set(change) == {"claim_id", "to_status"}
            and isinstance(change["claim_id"], str)
            and bool(change["claim_id"].strip())
            and change["to_status"] in {"supported", "rejected", "uncertain"}
            for change in u["node_changes"]
        )
    ):
        return False
    return (
        isinstance(row.get("eligible_u"), bool)
        and isinstance(row.get("verifier_ref"), str)
        and bool(row.get("verifier_ref"))
    )


def _formal_public_contract_valid(row: dict[str, Any]) -> bool:
    return (
        all(_valid_identifier(row.get(field)) for field in G7_PUBLIC_METADATA_FIELDS[:-2])
        and _valid_sha256(row.get("source_g5_graph_sha256"))
        and row.get("verification_grade") in {"A", "B", "C"}
        and isinstance(row.get("model_visible"), dict)
    )


def _formal_label_contract_valid(row: dict[str, Any]) -> bool:
    return (
        _label_contract_valid(row)
        and all(_valid_identifier(row.get(field)) for field in G7_LABEL_METADATA_FIELDS[1:])
        and _valid_sha256(row.get("source_public_case_sha256"))
        and row.get("verification_grade") in {"A", "B", "C"}
        and row.get("independent_verified") is True
        and row.get("synthetic_demo") is False
        and isinstance(row.get("verification_method"), str)
        and bool(row.get("verification_method"))
    )


def _formal_plan_contract_valid(row: dict[str, Any]) -> bool:
    return (
        all(_valid_identifier(row.get(field)) for field in G7_PLAN_METADATA_FIELDS)
        and isinstance(row.get("replicate"), int)
        and not isinstance(row.get("replicate"), bool)
        and row.get("replicate") >= 0
        and isinstance(row.get("arm_eligible_for_diagnostic"), bool)
    )


def _public_case_sha256(row: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(row, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def protocol_preflight(
    public_rows: list[dict[str, Any]],
    label_rows: list[dict[str, Any]],
    plan_rows: list[dict[str, Any]],
    worker_count: int,
    require_complete_plan: bool = False,
) -> dict[str, Any]:
    """Validate the exact model-facing G7 contract before provider creation."""

    public = {row.get("case_id"): row for row in public_rows if _valid_identifier(row.get("case_id"))}
    labels = {row.get("case_id"): row for row in label_rows if _valid_identifier(row.get("case_id"))}
    prompt_parts: list[str] = []
    diagnostic_prompt_parts: list[str] = []
    invalid_model_visible: list[Any] = []
    for index, row in enumerate(plan_rows):
        case_id = row.get("case_id")
        if not _valid_identifier(case_id) or case_id not in public:
            continue
        try:
            prompt_parts.append(case_prompt(public[case_id]))
        except (KeyError, TypeError, ValueError):
            invalid_model_visible.append(_row_identifier(case_id, index))
            continue
        if case_id in labels and _label_contract_valid(labels[case_id]):
            try:
                injection = injection_for(row, labels[case_id])
                diagnostic_prompt_parts.append(json.dumps({
                    "diagnostic_arm": row.get("diagnostic_arm"),
                    "inject_stages": row.get("inject_stages"),
                    "diagnostic_information": model_visible_diagnostic_information(injection),
                }, ensure_ascii=False))
            except (KeyError, TypeError, ValueError):
                pass
    prompt_text = "\n".join(prompt_parts)
    model_visible_text = "\n".join(prompt_parts + diagnostic_prompt_parts)
    missing_cases = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(plan_rows)
        if not _valid_identifier(row.get("case_id")) or row.get("case_id") not in public
    })
    missing_labels = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(plan_rows)
        if not _valid_identifier(row.get("case_id")) or row.get("case_id") not in labels
    })
    required_plan_fields = ("run_id", "checkpoint_id", "case_id")
    missing_required_plan_fields = sorted(
        field for field in required_plan_fields if any(not row.get(field) for row in plan_rows)
    )
    invalid_plan_rows: list[str] = []
    for index, row in enumerate(plan_rows):
        run_id = _row_identifier(row.get("run_id"), index)
        stages = row.get("inject_stages")
        stages_valid = (
            isinstance(stages, list)
            and all(isinstance(stage, str) for stage in stages)
            and len(stages) == len(set(stages))
            and set(stages).issubset(G7_STAGES)
        )
        arm_name = row.get("diagnostic_arm")
        arm_contract = G7_ARM_CONTRACT.get(arm_name) if isinstance(arm_name, str) else None
        arm_matches = (
            arm_contract is not None
            and isinstance(row.get("group_id"), str)
            and row.get("group_id") in G7_GROUPS
            and stages_valid
            and tuple(stages) == arm_contract
        )
        if (
            any(field in row and not _valid_identifier(row.get(field))
                for field in ("run_id", "checkpoint_id", "case_id"))
            or
            not isinstance(row.get("group_id"), str)
            or row.get("group_id") not in G7_GROUPS
            or not isinstance(row.get("diagnostic_arm"), str)
            or not stages_valid
            or not arm_matches
        ):
            invalid_plan_rows.append(run_id)
    invalid_label_cases = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(label_rows)
        if not _valid_identifier(row.get("case_id")) or not _label_contract_valid(row)
    })
    invalid_design_public_cases = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(public_rows)
        if not _valid_identifier(row.get("case_id")) or not _formal_public_contract_valid(row)
    })
    invalid_design_label_cases = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(label_rows)
        if not _valid_identifier(row.get("case_id")) or not _formal_label_contract_valid(row)
    })
    invalid_design_plan_rows = sorted({
        _row_identifier(row.get("run_id"), index)
        for index, row in enumerate(plan_rows)
        if not _formal_plan_contract_valid(row)
    })
    design_plan_mapping_mismatches = sorted({
        _row_identifier(row.get("run_id"), index)
        for index, row in enumerate(plan_rows)
        if (
            _valid_identifier(row.get("case_id"))
            and row.get("case_id") in public
            and any(row.get(field) != public[row["case_id"]].get(field)
                    for field in ("paired_set_id", "theory_family_id", "cf_type", "split"))
        )
    })
    design_label_public_hash_mismatches = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(label_rows)
        if (
            _valid_identifier(row.get("case_id"))
            and row.get("case_id") in public
            and row.get("source_public_case_sha256") != _public_case_sha256(public[row["case_id"]])
        )
    })
    ineligible_u_diagnostic_rows = sorted({
        _row_identifier(row.get("run_id"), index)
        for index, row in enumerate(plan_rows)
        if (
            isinstance(row.get("inject_stages"), list)
            and "U" in row.get("inject_stages", [])
            and _valid_identifier(row.get("case_id"))
            and row.get("case_id") in labels
            and labels[row["case_id"]].get("eligible_u") is not True
            and row.get("arm_eligible_for_diagnostic") is not False
        )
    })
    plan_label_eligibility_mismatches = sorted({
        _row_identifier(row.get("run_id"), index)
        for index, row in enumerate(plan_rows)
        if (
            _valid_identifier(row.get("case_id"))
            and row.get("case_id") in labels
            and isinstance(labels[row["case_id"]].get("eligible_u"), bool)
            and isinstance(row.get("inject_stages"), list)
            and row.get("arm_eligible_for_diagnostic") is not (
                "U" not in row.get("inject_stages", [])
                or labels[row["case_id"]]["eligible_u"] is True
            )
        )
    })
    checkpoint_arms: dict[str, list[str]] = {}
    for row in plan_rows:
        checkpoint_id = row.get("checkpoint_id")
        arm = row.get("diagnostic_arm")
        if (
            _valid_identifier(checkpoint_id)
            and isinstance(arm, str)
            and arm in G7_ARM_CONTRACT
        ):
            checkpoint_arms.setdefault(checkpoint_id, []).append(arm)
    expected_arms = sorted(G7_ARM_CONTRACT)
    incomplete_arm_checkpoints = sorted(
        checkpoint_id for checkpoint_id, arms in checkpoint_arms.items()
        if sorted(arms) != expected_arms
    )
    invalid_public_cases = sorted({
        _row_identifier(row.get("case_id"), index)
        for index, row in enumerate(public_rows)
        if not _valid_identifier(row.get("case_id"))
    })
    run_ids = [row.get("run_id") for row in plan_rows if _valid_identifier(row.get("run_id"))]
    duplicate_plan_ids = len(run_ids) - len(set(run_ids))
    public_case_ids = [row.get("case_id") for row in public_rows if _valid_identifier(row.get("case_id"))]
    label_case_ids = [row.get("case_id") for row in label_rows if _valid_identifier(row.get("case_id"))]
    duplicate_public_case_ids = len(public_case_ids) - len(set(public_case_ids))
    duplicate_label_case_ids = len(label_case_ids) - len(set(label_case_ids))
    errors: list[str] = []
    if not public_rows or not label_rows or not plan_rows:
        errors.append("public_labels_plan_must_be_nonempty")
    if invalid_public_cases:
        errors.append("invalid_public_case_ids")
    if missing_cases:
        errors.append("plan_case_missing_from_public")
    if missing_labels:
        errors.append("plan_case_missing_from_labels")
    if missing_required_plan_fields:
        errors.append("plan_required_fields_missing")
    if invalid_plan_rows:
        errors.append("invalid_plan_contract")
    if invalid_label_cases:
        errors.append("invalid_label_contract")
    if require_complete_plan and invalid_design_public_cases:
        errors.append("invalid_g7_public_metadata")
    if require_complete_plan and invalid_design_label_cases:
        errors.append("invalid_g7_label_metadata")
    if require_complete_plan and invalid_design_plan_rows:
        errors.append("invalid_g7_plan_metadata")
    if require_complete_plan and design_plan_mapping_mismatches:
        errors.append("g7_plan_public_mapping_mismatch")
    if require_complete_plan and design_label_public_hash_mismatches:
        errors.append("g7_label_public_hash_mismatch")
    if require_complete_plan and ineligible_u_diagnostic_rows:
        errors.append("ineligible_u_diagnostic_arm")
    if require_complete_plan and plan_label_eligibility_mismatches:
        errors.append("g7_plan_label_eligibility_mismatch")
    if require_complete_plan and incomplete_arm_checkpoints:
        errors.append("incomplete_arm_coverage")
    if duplicate_plan_ids:
        errors.append("duplicate_run_id")
    if duplicate_public_case_ids:
        errors.append("duplicate_public_case_id")
    if duplicate_label_case_ids:
        errors.append("duplicate_label_case_id")
    if invalid_model_visible:
        errors.append("invalid_model_visible")
    if worker_count < 1 or worker_count > 16:
        errors.append("worker_count_out_of_range")
    routing_hits = _key_hits(model_visible_text, ROUTING_METADATA_KEYS)
    forbidden_hits = _key_hits(model_visible_text, FORBIDDEN_MODEL_KEYS)
    if routing_hits:
        errors.append("routing_metadata_in_model_prompt")
    if forbidden_hits:
        errors.append("private_oracle_metadata_in_model_prompt")
    return {
        "audit_version": "g7-protocol-preflight-v2",
        "provider_calls_made": False,
        "formal_run_allowed_by_protocol": not errors,
        "errors": errors,
        "counts": {
            "public_cases": len(public_rows),
            "labels": len(label_rows),
            "plan_rows": len(plan_rows),
            "missing_cases": len(missing_cases),
            "missing_labels": len(missing_labels),
            "missing_required_plan_fields": missing_required_plan_fields,
            "invalid_plan_rows": sorted(set(invalid_plan_rows)),
            "invalid_public_case_ids": invalid_public_cases,
            "invalid_label_cases": invalid_label_cases,
            "invalid_g7_public_metadata": invalid_design_public_cases,
            "invalid_g7_label_metadata": invalid_design_label_cases,
            "invalid_g7_plan_metadata": invalid_design_plan_rows,
            "g7_plan_public_mapping_mismatches": design_plan_mapping_mismatches,
            "g7_label_public_hash_mismatches": design_label_public_hash_mismatches,
            "ineligible_u_diagnostic_rows": ineligible_u_diagnostic_rows,
            "g7_plan_label_eligibility_mismatches": plan_label_eligibility_mismatches,
            "incomplete_arm_checkpoints": incomplete_arm_checkpoints,
            "expected_arms_per_checkpoint": expected_arms,
            "require_complete_plan": require_complete_plan,
            "duplicate_run_ids": duplicate_plan_ids,
            "duplicate_public_case_ids": duplicate_public_case_ids,
            "duplicate_label_case_ids": duplicate_label_case_ids,
            "invalid_model_visible_cases": sorted(set(invalid_model_visible)),
            "unique_checkpoint_ids": len({
                row.get("checkpoint_id") for row in plan_rows
                if _valid_identifier(row.get("checkpoint_id"))
            }),
        },
        "routing_metadata_model_prompt_hits": routing_hits,
        "forbidden_model_prompt_hits": forbidden_hits,
        "scientific_truth_decision_made": False,
    }


def public_tool_loop(provider: OpenAICompatibleProvider, messages: list[dict[str, Any]],
                     group: str, limits: "Limits", event_path: Path, trace_id: str,
                     seq: int, checkpoint: bool) -> tuple[dict[str, Any], int]:
    max_calls = 2 if group == "G3" else 8
    tools = TOOLS
    parsed = None
    normal_calls = 0
    request_calls = 0
    format_retry_used = False
    format_retry_pending = False
    while normal_calls < max_calls or format_retry_pending:
        is_format_retry = format_retry_pending
        format_retry_pending = False
        if not is_format_retry:
            normal_calls += 1
        request_calls += 1
        if group == "G3" and normal_calls == 2 and not is_format_retry:
            messages.append({"role": "user", "content": "Perform the fixed second synthesis pass. Return only the required JSON."})
        limits.before_model()
        seq = emit(event_path, seq, trace_id, "MODEL_REQUEST", "RUNNING",
                   {"call_index": request_calls, "checkpoint": checkpoint, "format_retry": is_format_retry,
                    "messages": messages, "tools": tools})
        response = provider.complete(messages, tools=tools)
        limits.consume(response)
        seq = emit(event_path, seq, trace_id, "MODEL_RESPONSE", "COMPLETED",
                   {"call_index": request_calls, "checkpoint": checkpoint, "format_retry": is_format_retry,
                    "content": response.content,
                    "tool_calls": response.tool_calls, "usage": response.usage.__dict__,
                    "metadata": response.metadata})
        if response.tool_calls:
            messages.append({"role": "assistant", "content": response.content, "tool_calls": response.tool_calls})
            for tool_call in response.tool_calls:
                fn = tool_call.get("function", tool_call)
                name = str(fn.get("name", ""))
                args = parse_tool_args(fn.get("arguments", {}))
                limits.before_tool()
                seq = emit(event_path, seq, trace_id, "TOOL_CALL", "RUNNING",
                           {"tool_name": name, "tool_arguments": args})
                try:
                    result = execute_tool(name, args)
                    tool_status = "COMPLETED"
                except Exception as exc:
                    result = {"error_type": type(exc).__name__, "error": str(exc)}
                    tool_status = "FAILED"
                seq = emit(event_path, seq, trace_id, "TOOL_RESULT", tool_status,
                           {"tool_name": name, "tool_result": result})
                messages.append({"role": "tool", "tool_call_id": tool_call.get("id", f"tool-{limits.tool_calls}"),
                                 "name": name, "content": json.dumps(result, ensure_ascii=False)})
            if normal_calls >= max_calls and not format_retry_used:
                format_retry_used = True
                messages.append({"role": "user", "content": FORMAT_RETRY_INSTRUCTION})
                seq = emit(event_path, seq, trace_id, "FORMAT_RETRY_SCHEDULED", "COMPLETED",
                           {"reason": "tool_loop_reached_workflow_call_limit"})
                format_retry_pending = True
            continue

        try:
            candidate = parse_payload(response.content)
            if not checkpoint:
                normalize_stages(candidate)
            parsed = candidate
        except ValueError as exc:
            if format_retry_used:
                raise
            format_retry_used = True
            messages.append({"role": "user", "content": FORMAT_RETRY_INSTRUCTION})
            seq = emit(event_path, seq, trace_id, "FORMAT_RETRY_SCHEDULED", "COMPLETED",
                       {"reason": str(exc)})
            format_retry_pending = True
            continue

        if group == "G3" and normal_calls < 2:
            continue
        if checkpoint or normal_calls >= 2:
            break
    if parsed is None:
        raise ValueError("no valid JSON response")
    return parsed, seq


@dataclass
class Limits:
    max_model_calls: int
    max_tool_calls: int
    max_total_tokens: int
    max_cost_usd: float
    model_calls: int = 0
    tool_calls: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0

    def before_model(self) -> None:
        if self.model_calls >= self.max_model_calls:
            raise RuntimeError("global model-call hard limit exceeded")
        if self.total_tokens >= self.max_total_tokens or self.cost_usd >= self.max_cost_usd:
            raise RuntimeError("G7 hard budget exceeded before model call")
        self.model_calls += 1

    def before_tool(self) -> None:
        if self.tool_calls >= self.max_tool_calls:
            raise RuntimeError("global tool-call hard limit exceeded")
        self.tool_calls += 1

    def consume(self, response: ProviderResponse) -> None:
        self.total_tokens += int(response.usage.input_tokens) + int(response.usage.output_tokens)
        self.cost_usd += float(response.usage.cost_usd)
        if self.total_tokens > self.max_total_tokens or self.cost_usd > self.max_cost_usd:
            raise RuntimeError("G7 hard budget exceeded")


def effective_worker_cost_cap(worker_count: int, worker_cap_usd: float,
                              aggregate_cap_usd: float | None) -> float:
    """Return a worker cap whose sum cannot exceed the declared aggregate cap.

    A multi-worker paid run must state its aggregate ceiling explicitly.  The
    historical runner only enforced ``worker_cap_usd`` independently, which
    could multiply the intended ceiling by the worker count.
    """
    if worker_count < 1:
        raise ValueError("worker_count must be positive")
    if not math.isfinite(worker_cap_usd) or worker_cap_usd <= 0:
        raise ValueError("worker cost cap must be a finite positive number")
    if worker_count > 1 and aggregate_cap_usd is None:
        raise ValueError("multi-worker G7 requires an explicit aggregate cost cap")
    if aggregate_cap_usd is None:
        return worker_cap_usd
    if not math.isfinite(aggregate_cap_usd) or aggregate_cap_usd <= 0:
        raise ValueError("aggregate cost cap must be a finite positive number")
    return min(worker_cap_usd, aggregate_cap_usd / worker_count)


def persisted_usage(out: Path, input_rate: float, output_rate: float, max_output_tokens: int,
                    trace_ids: set[str] | None = None) -> dict[str, float | int]:
    usage = {"model_calls": 0, "tool_calls": 0, "total_tokens": 0, "cost_usd": 0.0, "reserved_cost_usd": 0.0}
    for path in out.glob("**/*.jsonl"):
        for event in readl(path):
            if trace_ids is not None and str(event.get("run_id", "")) not in trace_ids:
                continue
            typ = event.get("event_type")
            if typ == "MODEL_REQUEST":
                usage["model_calls"] += 1
                messages = event.get("payload", {}).get("messages", [])
                usage["reserved_cost_usd"] += (max(1, len(json.dumps(messages, ensure_ascii=False).split())) / 1000) * input_rate
                usage["reserved_cost_usd"] += (max_output_tokens / 1000) * output_rate
            elif typ == "TOOL_CALL":
                usage["tool_calls"] += 1
            elif typ == "MODEL_RESPONSE":
                u = event.get("payload", {}).get("usage", {})
                usage["total_tokens"] += int(u.get("input_tokens", 0)) + int(u.get("output_tokens", 0))
                usage["cost_usd"] += float(u.get("cost_usd", 0.0))
    return usage


def injection_for(row: dict[str, Any], label: dict[str, Any]) -> dict[str, Any]:
    stages = row["inject_stages"]
    injection: dict[str, Any] = {
        "applied_stages": [],
        "source": "ORACLE_ASSISTED_DIAGNOSIS" if stages else "D0_NEUTRAL_PLACEHOLDER",
    }
    if stages:
        injection["label_source"] = "independently_verified_g7_local_labels"
    if "V" in stages:
        injection["V"] = {"verdict": label["v"]["verdict"], "verifier_ref": label["verifier_ref"]}
        injection["applied_stages"].append("V")
    if "L" in stages:
        injection["L"] = {"nodes": label["l"]["nodes"], "edges": label["l"]["edges"], "verifier_ref": label["verifier_ref"]}
        injection["applied_stages"].append("L")
    if "U" in stages:
        injection["U"] = {"node_changes": label["u"]["node_changes"], "eligible": label["eligible_u"],
                           "reason": label.get("u_ineligibility_reason"), "verifier_ref": label["verifier_ref"]}
        injection["applied_stages"].append("U")
    return injection


def model_visible_diagnostic_information(injection: dict[str, Any]) -> dict[str, Any]:
    """Return only the preregistered V/L/U labels for the model-facing message.

    Provenance, eligibility, and source markers are retained in the append-only
    ``INJECTION_APPLIED`` audit event, but are not experimental information
    supplied to the model. This keeps oracle-assisted diagnosis limited to the
    requested intermediate labels rather than exposing audit metadata.
    """
    visible: dict[str, Any] = {}
    if isinstance(injection.get("V"), dict):
        visible["V"] = {"verdict": injection["V"].get("verdict")}
    if isinstance(injection.get("L"), dict):
        visible["L"] = {
            "nodes": injection["L"].get("nodes", []),
            "edges": injection["L"].get("edges", []),
        }
    if isinstance(injection.get("U"), dict):
        visible["U"] = {"node_changes": injection["U"].get("node_changes", [])}
    return visible


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--public", type=Path, required=True)
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--model-id", required=True)
    p.add_argument("--key-file", type=Path, required=True)
    p.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    p.add_argument("--allow-paid", action="store_true")
    p.add_argument("--model-snapshot-manifest", type=Path)
    p.add_argument("--billing-export", type=Path)
    p.add_argument("--worker-index", type=int, default=0)
    p.add_argument("--worker-count", type=int, default=1)
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--provider-retries", type=int, default=0)
    p.add_argument("--provider-timeout", type=float, default=60)
    p.add_argument("--input-cost-per-1k", type=float, default=0.001)
    p.add_argument("--output-cost-per-1k", type=float, default=0.003)
    p.add_argument("--max-model-calls", type=int, default=4608)
    p.add_argument("--max-tool-calls", type=int, default=3456)
    p.add_argument("--max-total-tokens", type=int, default=4608000)
    p.add_argument("--max-cost-usd", type=float, default=200.0)
    p.add_argument("--aggregate-max-cost-usd", type=float)
    args = p.parse_args()
    if not args.allow_paid:
        raise SystemExit("real G7 requires explicit --allow-paid")
    if args.worker_count < 1 or args.worker_count > 16 or not 0 <= args.worker_index < args.worker_count:
        raise SystemExit("worker_count must be between 1 and 16 and worker_index must be in range")
    try:
        effective_max_cost_usd = effective_worker_cost_cap(
            args.worker_count, args.max_cost_usd, args.aggregate_max_cost_usd
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    public_rows = readl(args.public)
    label_rows = readl(args.labels)
    plan = readl(args.plan)
    preflight = protocol_preflight(public_rows, label_rows, plan, args.worker_count,
                                   require_complete_plan=True)
    paid_evidence = validate_paid_evidence(args.model_id, args.model_snapshot_manifest, args.billing_export)
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "g7_protocol_preflight.json", {
        **preflight,
        "paid_evidence": paid_evidence,
        "input_hashes": {
            "public": sha256_file(args.public),
            "labels": sha256_file(args.labels),
            "plan": sha256_file(args.plan),
        },
        "runner_contract": "scripts/run_g7_failure_localization.py::case_prompt",
        "budget_policy": {
            "worker_count": args.worker_count,
            "configured_worker_max_cost_usd": args.max_cost_usd,
            "aggregate_max_cost_usd": args.aggregate_max_cost_usd,
            "effective_worker_max_cost_usd": effective_max_cost_usd,
            "sum_of_worker_caps_usd": effective_max_cost_usd * args.worker_count,
        },
    })
    if preflight["errors"]:
        raise SystemExit("G7 protocol preflight failed: " + ", ".join(preflight["errors"]))
    if paid_evidence["errors"]:
        raise SystemExit("G7 paid-evidence preflight failed: " + ", ".join(paid_evidence["errors"]))
    public = {x["case_id"]: x for x in public_rows}
    labels = {x["case_id"]: x for x in label_rows}
    for row in plan:
        if row["case_id"] not in public or row["case_id"] not in labels:
            raise SystemExit(f"plan row lacks public case or G7 label: {row.get('run_id')}")
    state_path = out / f"states.worker-{args.worker_count}-{args.worker_index}.jsonl"
    checkpoint_path = out / f"checkpoints.worker-{args.worker_count}-{args.worker_index}.jsonl"
    selected = plan if args.limit <= 0 else plan[:args.limit]
    checkpoints: dict[str, dict[str, Any]] = {}
    for row in selected:
        checkpoints.setdefault(row["checkpoint_id"], row)
    selected_cps = {cp: row for cp, row in checkpoints.items()
                    if int(hashlib.sha256(cp.encode()).hexdigest(), 16) % args.worker_count == args.worker_index}
    trace_ids = {"checkpoint_" + cp_id for cp_id in selected_cps}
    trace_ids.update(row["run_id"] for row in selected if row["checkpoint_id"] in selected_cps)
    prior_states = {x["run_id"]: x for x in readl(state_path)}
    prior_cp = {x["checkpoint_id"]: x for x in readl(checkpoint_path) if x.get("status") == "completed"}
    usage = persisted_usage(out, args.input_cost_per_1k, args.output_cost_per_1k, 1024, trace_ids)
    limits = Limits(args.max_model_calls, args.max_tool_calls, args.max_total_tokens, effective_max_cost_usd,
                    int(usage["model_calls"]), int(usage["tool_calls"]), int(usage["total_tokens"]), float(usage["cost_usd"]))
    provider = OpenAICompatibleProvider(api_key=args.key_file.read_text(encoding="utf-8").strip(), base_url=args.base_url,
                                        model_name=args.model_id, timeout=args.provider_timeout, max_retries=args.provider_retries,
                                        input_cost_per_1k=args.input_cost_per_1k, output_cost_per_1k=args.output_cost_per_1k,
                                        max_cost_usd=effective_max_cost_usd, max_output_tokens=1024)
    # Checkpoints are assigned as units, so all diagnostic forks from one
    # checkpoint remain on exactly one worker and have one immutable initial answer.
    for cp_id, row in selected_cps.items():
        if cp_id in prior_cp:
            continue
        trace_id = "checkpoint_" + cp_id
        event_path = out / "checkpoint_traces" / trace_id / "events.jsonl"
        seq = existing_trace_sequence(event_path)
        started = time.monotonic()
        try:
            seq = emit(event_path, seq, trace_id, "RUN_START", "RUNNING",
                       {"checkpoint_id": cp_id, "case_id": row["case_id"], "group_id": row["group_id"],
                        "model_id": args.model_id, "public_only": True})
            messages = [{"role": "system", "content": system_prompt(row["group_id"])},
                        {"role": "user", "content": case_prompt(public[row["case_id"]])}]
            payload, seq = public_tool_loop(provider, messages, row["group_id"], limits, event_path, trace_id, seq, True)
            record = {"checkpoint_id": cp_id, "case_id": row["case_id"], "group_id": row["group_id"],
                      "initial_decision": payload["decision"], "checkpoint_payload": payload,
                      "trace_ref": str(event_path.relative_to(out)), "status": "completed",
                      "elapsed_seconds": round(time.monotonic() - started, 3), "public_only": True}
            append_jsonl(checkpoint_path, record)
            emit(event_path, seq, trace_id, "RUN_END", "COMPLETED", {"status": "completed"})
            prior_cp[cp_id] = record
        except Exception as exc:
            emit(event_path, seq, trace_id, "ERROR", "FAILED", {"error_type": type(exc).__name__, "error": str(exc)})
            emit(event_path, seq + 1, trace_id, "RUN_END", "FAILED", {"status": "provider_error"})
            append_jsonl(checkpoint_path, {"checkpoint_id": cp_id, "case_id": row["case_id"], "group_id": row["group_id"],
                                            "status": "provider_error", "trace_ref": str(event_path.relative_to(out))})
            continue
    rows_for_worker = [row for row in selected if row["checkpoint_id"] in selected_cps]
    for index, row in enumerate(rows_for_worker, 1):
        if row["run_id"] in prior_states and prior_states[row["run_id"]].get("status") == "completed":
            continue
        cp = prior_cp.get(row["checkpoint_id"])
        if not cp or cp.get("status") != "completed":
            state = {"run_id": row["run_id"], "checkpoint_id": row["checkpoint_id"], "status": "checkpoint_missing",
                     "trace_ref": cp.get("trace_ref") if cp else None, "injection_audit": {"applied_stages": row["inject_stages"]}}
            append_jsonl(state_path, state)
            prior_states[row["run_id"]] = state
            continue
        trace_id = row["run_id"]
        event_path = out / "traces" / trace_id / "events.jsonl"
        seq = existing_trace_sequence(event_path)
        injection: dict[str, Any] = {"applied_stages": row["inject_stages"]}
        try:
            seq = emit(event_path, seq, trace_id, "RUN_START", "RUNNING",
                       {"run_id": trace_id, "checkpoint_id": row["checkpoint_id"], "case_id": row["case_id"],
                        "diagnostic_arm": row["diagnostic_arm"], "group_id": row["group_id"], "public_only": True})
            case = public[row["case_id"]]
            label = labels[row["case_id"]]
            injection = injection_for(row, label)
            seq = emit(event_path, seq, trace_id, "INJECTION_APPLIED", "COMPLETED", injection)
            messages = [{"role": "system", "content": system_prompt(row["group_id"])},
                        {"role": "user", "content": case_prompt(case)},
                        {"role": "assistant", "content": json.dumps(cp["checkpoint_payload"], ensure_ascii=False)},
                        {"role": "user", "content": json.dumps({"diagnostic_arm": row["diagnostic_arm"],
                           "inject_stages": row["inject_stages"],
                           "diagnostic_information": model_visible_diagnostic_information(injection),
                           "instruction": "Re-evaluate the case with only these supplied diagnostic stages. Return the required JSON."}, ensure_ascii=False)}]
            payload, seq = public_tool_loop(provider, messages, row["group_id"], limits, event_path, trace_id, seq, False)
            stages = normalize_stages(payload)
            state = {"run_id": trace_id, "checkpoint_id": row["checkpoint_id"], "status": "completed",
                     "initial_decision": cp["initial_decision"], "final_decision": payload["decision"],
                     "stages": stages, "trace_ref": str(event_path.relative_to(out)),
                     "checkpoint_trace_ref": cp["trace_ref"], "injection_audit": injection,
                     "usage": {"model_calls": limits.model_calls, "tool_calls": limits.tool_calls,
                               "total_tokens": limits.total_tokens, "cost_usd": limits.cost_usd},
                     "public_only_checkpoint": True}
            append_jsonl(state_path, state)
            prior_states[trace_id] = state
            emit(event_path, seq, trace_id, "RUN_END", "COMPLETED", {"status": "completed"})
        except Exception as exc:
            emit(event_path, seq, trace_id, "ERROR", "FAILED", {"error_type": type(exc).__name__, "error": str(exc)})
            emit(event_path, seq + 1, trace_id, "RUN_END", "FAILED", {"status": "provider_error"})
            state = {"run_id": trace_id, "checkpoint_id": row["checkpoint_id"], "status": "provider_error",
                     "trace_ref": str(event_path.relative_to(out)), "injection_audit": injection if "injection" in locals() else {"applied_stages": row["inject_stages"]}}
            append_jsonl(state_path, state)
            prior_states[trace_id] = state
        if index % 10 == 0 or state.get("status") != "completed":
            print(f"G7 progress {index}/{len(rows_for_worker)}: {state.get('status')} calls={limits.model_calls} tools={limits.tool_calls} tokens={limits.total_tokens}", flush=True)
    summary = {"experiment_id": "g7_failure_localization", "worker_index": args.worker_index,
               "worker_count": args.worker_count, "plan_count": len(plan), "selected_rows": len(rows_for_worker),
               "states_count": len(readl(state_path)), "checkpoints_count": len(readl(checkpoint_path)),
               "limits": limits.__dict__, "model_id": args.model_id, "base_url": args.base_url,
               "budget_policy": {"configured_worker_max_cost_usd": args.max_cost_usd,
                                 "aggregate_max_cost_usd": args.aggregate_max_cost_usd,
                                 "effective_worker_max_cost_usd": effective_max_cost_usd,
                                 "sum_of_worker_caps_usd": effective_max_cost_usd * args.worker_count},
               "public_sha256": sha256_file(args.public), "labels_sha256": sha256_file(args.labels),
               "plan_sha256": sha256_file(args.plan), "completed_at_utc": utc_now()}
    write_json(out / f"runner_summary.worker-{args.worker_count}-{args.worker_index}.json", summary)
    print(f"G7 RUN COMPLETE: states={summary['states_count']} checkpoints={summary['checkpoints_count']} worker={args.worker_index}/{args.worker_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
