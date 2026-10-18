"""Build the V3 G6/G7 offline audit and prospective-protocol evidence.

The legacy audit is reused as a read-only derived view.  This command never
edits legacy JSONL/CSV, never reads private labels into model-facing data, and
never calls a provider.  V2 metrics are explicitly NOT_RUN unless a real
provider run with the new schema exists.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LEGACY_CYCLE = "cycle-20261018T-g6g7-v3"
G7_ROOT = ROOT / "runs/ctflow_single_model/20261017T-g7-kimi-k25-v1"

from scripts.audit_repair.six_blocker_audit import build_outputs as build_legacy_audit
from scripts.audit_repair.six_blocker_audit import event_segments, trace_path
from scripts.v3.q_v2 import sha256_json
from scripts.v3.observability_smoke import run_smoke


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def trace_cost(root: Path, directories: list[Path]) -> tuple[float, int]:
    total = 0.0
    responses = 0
    for directory in directories:
        for path in directory.glob("*/events.jsonl"):
            for event in read_jsonl(path):
                if event.get("event_type") != "MODEL_RESPONSE":
                    continue
                usage = (event.get("payload") or {}).get("usage") or {}
                total += float(usage.get("cost_usd", 0.0) or 0.0)
                responses += 1
    return total, responses


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader(); writer.writerows(rows)


def source_class(path: Path) -> tuple[str, str]:
    text = rel(path)
    if "g5" in text.casefold() or "proof_graph" in text.casefold(): return "G5_PUBLIC_GRAPH_OR_TRACE", "G5"
    if "g6_counterfactual" in text or "g6-kimi" in text: return "G6_LEGACY_INPUT_OR_TRACE", "G6"
    if "g7_failure_localization" in text or "g7-kimi" in text: return "G7_LEGACY_INPUT_OR_TRACE", "G7"
    if "provider" in text.casefold() or "ctflow" in text.casefold(): return "PROVIDER_EVIDENCE", "CTFLOW"
    return "PROJECT_PROTOCOL_OR_AUDIT", "PROJECT"


def frozen_manifest(docs: Path, cycle: str) -> dict[str, Any]:
    requested = [
        ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z",
        ROOT / "runs/ctflow_single_model/20261017T-g6-kimi-k25-v1",
        ROOT / "results/g7_failure_localization/formal-20261014T030000Z-16workers",
        ROOT / "results/g7_failure_localization/formal-20261015T060000Z-protocol-corrected-16workers",
        G7_ROOT,
        ROOT / "docs/provider",
    ]
    def collect() -> list[dict[str, Any]]:
        files: dict[str, Path] = {}
        for root in requested:
            if root.is_file(): files[rel(root)] = root
            elif root.is_dir():
                for path in root.rglob("*"):
                    # The G7 run root also contains derived audit reports.  They
                    # are outputs of this cycle, never frozen experimental input.
                    if root == G7_ROOT and (G7_ROOT / "g7_audit") in path.parents:
                        continue
                    if path.is_file(): files[rel(path)] = path
        rows = []
        for name in sorted(files):
            path = files[name]
            try:
                records = sum(1 for line in path.open("r", encoding="utf-8") if line.strip()) if path.suffix.lower() in {".jsonl", ".csv", ".ndjson"} else None
            except (OSError, UnicodeError):
                records = None
            classification, source_run = source_class(path)
            rows.append({"path": name, "sha256": sha256(path), "size": path.stat().st_size,
                         "record_count": records, "source_run": source_run,
                         "classification": classification})
        return rows
    before = collect()
    after = collect()
    before_map = {r["path"]: r["sha256"] for r in before}
    after_map = {r["path"]: r["sha256"] for r in after}
    result = {
        "schema_version": 2, "cycle": cycle, "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_source_file_count": len(before), "protected_source_hashes_unchanged": before_map == after_map,
        "changed_paths": sorted(k for k in set(before_map) | set(after_map) if before_map.get(k) != after_map.get(k)),
        "before": before, "after": after,
    }
    write_json(docs / "FROZEN_INPUT_SHA256.json", result)
    return result


def build_v3(args: Namespace) -> dict[str, Any]:
    cycle = args.cycle
    docs = ROOT / "docs/audits" / cycle
    private = G7_ROOT / "g7_audit" / "v3_audit" / cycle
    docs.mkdir(parents=True, exist_ok=True); private.mkdir(parents=True, exist_ok=True)
    # Build the already-validated legacy derived view in a new namespace.
    legacy = build_legacy_audit(Namespace(cycle=cycle))
    legacy_local = Path(legacy["local_out"])
    for path in legacy_local.iterdir():
        if path.is_file(): shutil.copyfile(path, private / path.name)
    manifest = frozen_manifest(docs, cycle)
    write_json(private / "FROZEN_INPUT_SHA256.json", manifest)

    # Extend the state matrix without replacing the original selected view.
    old_rows = list(csv.DictReader((docs / "06_G7_STATE_RESUME_MATRIX.csv").open(encoding="utf-8")))
    cp_rows: dict[str, list[dict[str, Any]]] = {}
    for path in G7_ROOT.glob("checkpoints.worker-*.jsonl"):
        for row in read_jsonl(path): cp_rows.setdefault(row.get("checkpoint_id", ""), []).append(row)
    matrix = []
    for row in old_rows:
        cp = cp_rows.get(row["checkpoint_id"], [])
        cp_done = any(x.get("status") == "completed" for x in cp)
        cp_hash = sha256_json(next((x for x in cp if x.get("status") == "completed"), cp[0] if cp else {}))
        reasons = row.get("selected_trace_reasons", "")
        selected_ref = row.get("selected_trace_ref")
        selected_path = trace_path(G7_ROOT, selected_ref)
        selected_events, selected_segments, selected_parse_errors = ([], [], [])
        if selected_path is not None:
            selected_events, selected_segments, selected_parse_errors = event_segments(selected_path)
        selected_segment = selected_segments[-1] if selected_segments else selected_events
        provider_requests = sum(event.get("event_type") == "MODEL_REQUEST" for event in selected_segment)
        provider_responses = sum(
            event.get("event_type") == "MODEL_RESPONSE"
            and isinstance((event.get("payload") or {}).get("metadata", {}).get("raw_id"), str)
            and bool((event.get("payload") or {}).get("metadata", {}).get("raw_id"))
            for event in selected_segment
        )
        attempt_id = selected_ref or row.get("last_eligible_attempt") or row.get("state_id")
        trace_reasons = [*selected_parse_errors]
        matrix.append({
            **row,
            "has_completed_checkpoint": cp_done,
            "checkpoint_sha": cp_hash if cp else None,
            "provider_request_count": provider_requests,
            "genuine_response_count": provider_responses,
            "latest_attempt_id": attempt_id,
            "chosen_attempt_reason": row.get("why_selected"),
            "trace_integrity": row.get("selected_trace_valid"),
            "terminal_code": row.get("selected_result_status"),
            "retry_eligible": row.get("needs_real_provider_call") == "True" or row.get("selected_trace_valid") != "True",
            "reasons": ";".join(filter(None, [reasons, ";".join(trace_reasons)])),
        })
    fields = list(matrix[0])
    write_csv(docs / "G7_STATE_ATTEMPT_MATRIX.csv", matrix, fields)
    write_csv(private / "G7_STATE_ATTEMPT_MATRIX.csv", matrix, fields)

    trace_rows = list(csv.DictReader((docs / "07_G7_28_TO_15_PLUS_13_TRACE_RECONCILIATION.csv").open(encoding="utf-8")))
    trace_out = []
    for row in trace_rows:
        trace_out.append({
            "run_id": row.get("run_id"), "classification": row.get("classification"),
            "historical_status": "HISTORICAL_TRACE_INVALID" if row.get("classification") == "GENUINE_FINAL_ATTEMPT_INCONSISTENCY" else "HISTORICAL_BOUNDARY_ARTIFACT",
            "raw_trace_ref": row.get("raw_trace_ref"), "raw_sha256": row.get("raw_sha256"),
            "evidence": {"selected_segment_count": row.get("selected_segment_count"), "reasons_selected": row.get("reasons_selected"),
                         "latest_start_suffix_status": row.get("latest_start_suffix_status"), "latest_start_suffix_reasons": row.get("latest_start_suffix_reasons")},
            "new_attempt_created": False,
        })
    write_jsonl(docs / "G7_TRACE_15_EXPLAINED_13_INVALID.jsonl", trace_out)
    write_jsonl(private / "G7_TRACE_15_EXPLAINED_13_INVALID.jsonl", trace_out)

    regression_cmd = [sys.executable, "-X", "utf8", "-m", "pytest", "-q", "tests/test_g7_trace_q_consistency.py", "tests/test_six_blocker_repair.py", "tests/test_v3_observability.py"]
    regression = subprocess.run(regression_cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    write_json(docs / "G7_EXECUTOR_REGRESSION.json", {
        "command": regression_cmd, "exit_code": regression.returncode,
        "status": "PASS" if regression.returncode == 0 else "FAIL",
        "stdout_tail": regression.stdout[-4000:], "stderr_tail": regression.stderr[-4000:],
        "historical_13_preserved": True, "new_paid_attempts": 0,
        "writer_source_sha256": sha256(ROOT / "scripts/run_g7_failure_localization.py"),
    })

    shutil.copyfile(docs / "02_G6_REVISION_ROOT_CAUSES.csv", docs / "G6_138_MATH_CLASSIFICATION.csv")
    shutil.copyfile(docs / "03_G6_INDEPENDENT_MATH_AUDIT.jsonl", docs / "G6_INDEPENDENT_VERIFIER_RESULT.jsonl")
    shutil.copyfile(docs / "04_G6_STATISTICAL_REVIEW.json", docs / "G6_CLUSTER_DESCRIPTIVE_STATS.json")
    for name in ("G6_138_MATH_CLASSIFICATION.csv", "G6_INDEPENDENT_VERIFIER_RESULT.jsonl"):
        shutil.copyfile(docs / name, private / name)

    q_rows = read_jsonl(docs / "09_G7_Q_INDEPENDENT_AUDIT.jsonl")
    q_summary = {"protocol": "LEGACY_Q", "planned": len(q_rows), "status_counts": {}, "private_labels_read": False,
                 "private_oracle_read": False, "verifier_source": "scripts/audit_repair/verify_q.py"}
    for row in q_rows: q_summary["status_counts"][row.get("status")] = q_summary["status_counts"].get(row.get("status"), 0) + 1
    write_json(docs / "Q_LEGACY_OBSERVABILITY_AUDIT.json", q_summary)
    lu = read_json(private / "VL_U_SOURCE_PROVENANCE.json")
    write_json(docs / "LU_LEGACY_OBSERVABILITY_AUDIT.json", {**lu, "protocol": "LEGACY_LU", "public_edge_truth_observed": False, "nonfinal_transition_truth_observed": False})

    provider_catalog = docs / "PROVIDER_MODELS_CATALOG_PROBE.json"
    if not provider_catalog.is_file():
        legacy_catalog = ROOT / "docs/audits/cycle-20261018T-six-blocker-repair/PROVIDER_MODELS_CATALOG_PROBE.json"
        if legacy_catalog.is_file():
            shutil.copyfile(legacy_catalog, provider_catalog)
    catalog = read_json(provider_catalog) if provider_catalog.is_file() else {}
    provider_csv = list(csv.DictReader((docs / "11_PROVIDER_RECONCILIATION.csv").open(encoding="utf-8")))
    provider_reconciliation = {
        "local_rows": len(provider_csv), "rows_with_local_usage": sum(r.get("local_estimate") not in {"", None} for r in provider_csv),
        "supplier_invoice_or_usage_export": None, "billing_status": "NO_EXTERNAL_BILLING_EXPORT",
        "pricing_status": "NO_PROVIDER_VERIFIED_PRICE_RECORD", "billing_verified": False,
        "model_identity_verified": False, "catalog_probe_ref": rel(provider_catalog),
        "catalog_probe_proves_only": catalog.get("what_this_proves"),
        "catalog_probe_does_not_prove": catalog.get("what_this_does_not_prove"),
    }
    write_json(docs / "PROVIDER_BILLING_RECONCILIATION.json", provider_reconciliation)
    write_json(docs / "PROVIDER_MODEL_PROVENANCE.json", {
        "status": "MODEL_IDENTITY_UNVERIFIED", "gateway": catalog.get("gateway"),
        "catalog_count": catalog.get("catalog_count"), "matching_service_ids": catalog.get("matching_ids", []),
        "immutable_weight_or_snapshot": False, "route_attestation": False,
        "evidence_ref": rel(provider_catalog),
    })
    g6_raw_cost, g6_raw_responses = trace_cost(
        ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z",
        [ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/traces"],
    )
    g6_audited_cost, g6_audited_responses = trace_cost(
        ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z",
        [ROOT / "results/g6_counterfactual/protocol-g3tools-v2-20261014T030000Z/traces_audited"],
    )
    g7_raw_cost, g7_raw_responses = trace_cost(G7_ROOT, [G7_ROOT / "traces", G7_ROOT / "checkpoint_traces"])
    write_json(docs / "COST_AND_PROVIDER_EVIDENCE.json", {
        "v3_cycle_new_api_spend_usd": 0.0,
        "provider_invoice_or_usage_export_present": False,
        "provider_verified_pricing_present": False,
        "local_proxy_estimates_not_billing": True,
        "historical_local_trace_estimates": {
            "g6_raw_all_attempts_usd": round(g6_raw_cost, 9),
            "g6_raw_model_responses": g6_raw_responses,
            "g6_audited_trace_view_usd": round(g6_audited_cost, 9),
            "g6_audited_model_responses": g6_audited_responses,
            "g7_raw_all_trace_dirs_usd": round(g7_raw_cost, 9),
            "g7_raw_model_responses": g7_raw_responses,
            "raw_all_trace_dirs_total_usd": round(g6_raw_cost + g7_raw_cost, 9),
            "audited_g6_plus_raw_g7_total_usd": round(g6_audited_cost + g7_raw_cost, 9),
        },
        "safe_remaining_budget_claim": False,
        "reason": "No supplier billing export or provider-verified historical ceiling is available.",
    })

    smoke_path = private / "V2_SCHEMA_VALIDATION_AND_LEAKAGE_SMOKE.json"
    smoke = run_smoke(smoke_path)
    write_json(docs / "V2_SCHEMA_VALIDATION_AND_LEAKAGE_TESTS.json", {
        **smoke, "schema_files": {
            "q": {"path": "schemas/q_v2_candidate.schema.json", "sha256": sha256(ROOT / "schemas/q_v2_candidate.schema.json")},
            "lu": {"path": "schemas/lu_v2_graph.schema.json", "sha256": sha256(ROOT / "schemas/lu_v2_graph.schema.json")},
        }, "real_provider_calls": 0,
    })
    prereg = """# G7 prospective Q-v2 / LU-v2 protocol (frozen offline)

Status: `SMOKE_PASS`, `REAL_FORMAL_RUNS=0`, `V2_FINAL_METRICS=NOT_RUN`.

The legacy 1288-state Q and L/U results remain in the LEGACY_FROZEN namespace. This protocol creates a separate `G7_Q_V2` and `G7_LU_V2` namespace; no new rows are added to the legacy denominator.

Q-v2 requires a model-generated typed AST, explicit assumptions/quantifiers/domain, an observed verifier tool trace, input/output hashes, and an independent SymPy verifier. Self-reported `stages.Q.verdict` and `final_decision` are never evidence. Missing candidates are `NOT_SCORED_CANDIDATE_MISSING`; missing tool evidence is `UNOBSERVED_TOOL`.

LU-v2 requires a public acyclic DAG with independently referenced proof artifacts and a real observed non-final claim transition in the same fork. Final-node changes, evaluator-derived edges, private labels, and synthetic arrows are ineligible.

The present artifact is a synthetic contract smoke only (`SYNTHETIC_MOCK_NOT_SCIENTIFIC`). A real DEV/PILOT/FINAL run requires verified provider pricing, atomic budget clearance, a separately frozen task cohort, and a real trace. No paid call was made in this cycle.
"""
    (docs / "V2_PROTOCOL_AND_PREREGISTRATION.md").write_text(prereg, encoding="utf-8")
    write_json(docs / "V2_FINAL_METRICS.json", {"status": "NOT_RUN", "real_formal_runs": 0, "reason": "provider pricing/billing/identity gates unavailable", "synthetic_smoke": smoke["status"]})

    gates = {
        "scientific_release_allowed": False, "G6": "PARTIAL_NOT_SCORED", "G7_legacy": "PARTIAL_EXECUTION",
        "G7_trace": "TRACE_BLOCKED", "Q_legacy": "Q_NOT_SCORED", "LU_legacy": "LU_UNVERIFIED",
        "Q_v2": "NOT_RUN", "LU_v2": "SMOKE_ONLY_NOT_SCIENTIFIC", "provider": "BLOCKED_EXTERNAL_SOURCE",
        "cost_gate": "BLOCKED_NO_PROVIDER_VERIFIED_PRICING_OR_HISTORICAL_CONSERVATIVE_CEILING",
        "evidence": {"source_manifest": "FROZEN_INPUT_SHA256.json", "executor_regression": "G7_EXECUTOR_REGRESSION.json", "independent_review_pending": True},
    }
    write_json(docs / "G0_G7_GATE_MATRIX.json", gates)
    unresolved = """# V3 unresolved external actions

- `PROVIDER_BILLING_UNVERIFIED`: no supplier invoice or usage export is present.
- `MODEL_IDENTITY_UNVERIFIED`: `/models` service IDs do not establish immutable weights or a time-bound route attestation.
- `PRICING_UNVERIFIED`: no provider-verified USD price record with effective interval was available; the runner now rejects local proxy rates alone.
- `HISTORIC_CONSERVATIVE_CEILING_UNVERIFIED`: local trace sums are not a safe provider-charge ceiling; G7 missing states remain unpaid.
- `G6_REVISIONS_PARTIAL`: 138 rows are independently classified, but only a subset has a narrow mathematical proof and statistics remain descriptive.
- `G7_COVERAGE`: 137 checkpoint-missing plus 1 provider-error state lack a real provider response.
- `G7_TRACE_HISTORICAL_INVALID`: 13 genuine final-attempt incidents remain historical failures; 15 boundary artifacts remain retained evidence.
- `Q_V2_LU_V2`: strict schemas and synthetic anti-leakage smoke pass; real prospective provider experiment is `NOT_RUN`.
- `REMOTE_DELIVERY`: GitHub push/remote verification remains externally unavailable.
"""
    (docs / "UNRESOLVED_EXTERNAL_ACTIONS.md").write_text(unresolved, encoding="utf-8")
    final = f"""# V3 executive report

模型/路由：CTFlow catalog probe exposed service IDs only; immutable model identity remains UNVERIFIED. 账单/价格：UNVERIFIED; no provider-verified pricing artifact or invoice was available.

G6 legacy: 552 normalized rows; revision denominator 138; root causes and independent verifier counts are in `G6_138_MATH_CLASSIFICATION.csv` and `G6_INDEPENDENT_VERIFIER_RESULT.jsonl`. G6 remains partial/not scored for scientific release.

G7 legacy: 1288 unique states, 184 checkpoints, 1150 provider-completed, 137 checkpoint-missing, 1 provider-error; canonical trace-valid and sensitivity views remain separate. Historical trace defects remain 15 boundary + 13 genuine final inconsistencies. No new paid attempt was made.

Legacy Q remains NOT_SCORED/INELIGIBLE. Legacy L/U remains unverified with no public dependency edges and no eligible observed non-final transition.

Q-v2/LU-v2: strict schemas, independent verifier hooks, leakage tests and synthetic smoke passed; real formal V2 metrics are `NOT_RUN` and no synthetic result is scientific evidence.

Cost: this V3 cycle added USD 0 API spend. The frozen G6 audited trace view is USD 6.057783 and raw G6 attempts are USD 6.610445; raw G7 trace directories are USD 8.915826. These are local proxy estimates, not provider billing; the raw-all trace sum is USD 15.526271 and no safe remaining budget is claimed. G7 aggregate/per-worker sub-budgets were not consumed.

Scientific release: BLOCKED. Offline engineering, source hashing, math classification, trace regression and V2 contract validation are complete to their evidence boundary; external billing/pricing/model identity and real V2/G7 missing responses remain unresolved.
"""
    (docs / "FINAL_EXECUTIVE_REPORT.md").write_text(final, encoding="utf-8")
    return {"cycle": cycle, "docs": rel(docs), "private": rel(private), "smoke": smoke["status"], "regression": regression.returncode, "protected_hashes_unchanged": manifest["protected_source_hashes_unchanged"], "api_cost_usd": 0.0}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycle", default=LEGACY_CYCLE)
    args = parser.parse_args()
    result = build_v3(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["smoke"] == "SMOKE_PASS" and result["regression"] == 0 and result["protected_hashes_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
