"""Fail-closed internal evidence gate for the single-Kimi V9/G8/G8.5 work.

This gate is deliberately different from the historical scientific-release gate.
It qualifies only append-only, internally machine-verifiable evidence so that
automated follow-up experiments can continue.  It never rewrites historical
denominators, promotes a prospective cohort to historical confirmation, or
turns provider attestation gaps into a PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


MODEL_ID = "kimi-k2.5"
HISTORICAL_DENOMINATORS = {
    "g6_formal": 552,
    "g6_machine_rows": 276,
    "g7_frozen": 1288,
    "g7_recovery": 150,
    "g7_historical_defects": 13,
    "q92": 92,
    "lu_legacy_pairs": 6,
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object JSONL row: {path}")
            rows.append(value)
    return rows


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def check(name: str, condition: bool, detail: Any) -> dict[str, Any]:
    return {"name": name, "status": "PASS" if condition else "FAIL", "detail": detail}


def all_pass(checks: Iterable[dict[str, Any]]) -> bool:
    return all(item["status"] == "PASS" for item in checks)


def check_ledger(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"path": str(path), "exists": path.exists()}
    if not path.exists():
        result.update({"status": "FAIL", "integrity": "MISSING"})
        return result
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=0.25) as connection:
            integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
            tables = [str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        result.update({"status": "PASS" if integrity == "ok" else "FAIL", "integrity": integrity, "tables": tables})
    except sqlite3.Error as exc:
        result.update({"status": "FAIL", "error_type": type(exc).__name__, "error": str(exc)})
    return result


def resolve_repo_path(repo: Path, value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else repo / path


def inspect_v9(repo: Path, audit_path: Path, v9_run: Path) -> dict[str, Any]:
    audit = load_json(audit_path)
    accounting = audit["api_accounting"]
    result: dict[str, Any] = {"source": str(audit_path), "checks": []}
    checks = result["checks"]
    checks.append(check("single model", accounting["model_id"] == MODEL_ID and accounting["only_model"] is True, accounting))
    checks.append(check("real non-mock provider", accounting["mock"] is False and not accounting["provider_errors"], {"mock": accounting["mock"], "provider_errors": accounting["provider_errors"]}))
    checks.append(check("historical denominators unchanged", audit["historical_denominators_unchanged"] == HISTORICAL_DENOMINATORS, audit["historical_denominators_unchanged"]))
    checks.append(check("planned V9 calls terminal", accounting["real_provider_calls"] == 104, accounting["real_provider_calls"]))

    g6_replay = load_jsonl(resolve_repo_path(repo, audit["audit_paths"]["g6_math_replay"]))
    checks.append(check("G6 independent numeric certificates", len(g6_replay) == 32 and all(row.get("independent_match") is True for row in g6_replay), {"rows": len(g6_replay), "matches": sum(row.get("independent_match") is True for row in g6_replay)}))

    q_review = audit["new_metrics"]["q"]["review_summary"]
    checks.append(check("Q truth-first independent review", q_review["rows"] == 8 and q_review["schema_valid"] == 8 and q_review["state_correct"] == 8 and q_review["truth_key_sent_to_model"] is False, q_review))

    lu_review = audit["new_metrics"]["lu_u"]["review_summary"]
    checks.append(check("LU/U shared checkpoint and three arms", lu_review["checkpoint_count"] == 4 and lu_review["arm_counts"] == {"CONTROL": 4, "REAL": 4, "SHAM": 4} and lu_review["shared_checkpoint_hashes_present"] is True and lu_review["truth_key_sent_to_model"] is False, lu_review))
    checks.append(check("LU/U arm result retained", lu_review["semantic_correct"] == {"CONTROL": 0, "REAL": 4, "SHAM": 0}, lu_review["semantic_correct"]))

    g7_path = resolve_repo_path(repo, audit["audit_paths"]["g7_repair_scored"])
    g7_rows = load_jsonl(g7_path)
    d3_rows = [row for row in g7_rows if row.get("stage") == "D3_VLU"]
    semantic = sum(row.get("final_semantic_correct") is True for row in d3_rows)
    strict = sum(row.get("final_correct") is True for row in d3_rows)
    g7_clean = all(row.get("provider_error") is None and row.get("terminal_status") == "SUCCESS" and row.get("private_Y_injected_verified_false") is True for row in g7_rows)
    checks.append(check("G7 repair provider/privacy trace", len(g7_rows) == 16 and g7_clean, {"rows": len(g7_rows), "clean": g7_clean}))
    checks.append(check("G7 D3 semantic diagnostic available", len(d3_rows) == 4 and semantic == 3, {"d3_rows": len(d3_rows), "semantic_correct": semantic, "strict_correct": strict}))
    result["g7_d3"] = {"rows": len(d3_rows), "semantic_correct": semantic, "strict_correct": strict, "interpretation": "partial semantic diagnostic; strict status-token metric remains zero"}
    result["status"] = "PASS" if all_pass(checks) else "FAIL"
    return result


def inspect_history_pair(audit_path: Path) -> dict[str, Any]:
    audit = load_json(audit_path)
    checks = [
        check("two prospective pairs", audit.get("pair_count") == 2 and audit.get("record_count") == 4, {"pair_count": audit.get("pair_count"), "record_count": audit.get("record_count")}),
        check("same-state/same-evidence structural audit", audit.get("all_structural_checks_pass") is True, audit),
        check("private truth not injected", audit.get("private_truth_injected") is False, audit.get("private_truth_injected")),
        check("not historical confirmation", audit.get("confirmatory_eligibility") == "NO_PROSPECTIVE_NOT_HISTORICAL", audit.get("confirmatory_eligibility")),
    ]
    return {"source": str(audit_path), "checks": checks, "status": "PASS" if all_pass(checks) else "FAIL", "confirmatory_eligibility": audit.get("confirmatory_eligibility")}


def inspect_g8(g8_manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(g8_manifest_path)
    sections = (manifest["pilot"], manifest["formal_primary_intent_to_treat"], manifest["formal_adapter_repair_sensitivity"])
    checks: list[dict[str, Any]] = [
        check("G8 single Kimi manifest", manifest.get("model_id") == MODEL_ID and manifest.get("only_model") is True, {"model_id": manifest.get("model_id"), "only_model": manifest.get("only_model")}),
        check("G8 public truth boundary", all(section["audit"].get("private_oracle_loaded") is False and section["audit"].get("audit_status_counts", {}).get("PASS") == section["audit"].get("n_planned") for section in sections), "all three audit sections pass process audit"),
        check("G8 technical failures retained", manifest["formal_primary_intent_to_treat"]["audit"]["execution_status_counts"].get("TECHNICAL_FAILURE", 0) == 24, manifest["formal_primary_intent_to_treat"]["audit"]["execution_status_counts"]),
        check("G8 private request scan clean", all(section["manifest"].get("model_requests_private_truth_scan", -1) == 0 for section in sections), "all sections scan=0"),
    ]
    calls = sum(int(section["manifest"].get("real_provider_calls", 0)) for section in sections)
    cost = sum(float(section["manifest"].get("total_cost_usd", 0.0)) for section in sections)
    return {"source": str(g8_manifest_path), "checks": checks, "status": "PASS" if all_pass(checks) else "FAIL", "calls": calls, "cost_usd": cost}


def inspect_g85(repo: Path, g85_root: Path) -> dict[str, Any]:
    manifest = load_json(g85_root / "G85_FINAL_MANIFEST.json")
    prospective = manifest["prospective_pilot"]
    audit = load_json(g85_root / "prospective_results" / "g85_private_truth_audit.json")
    plan_path = g85_root / "plans" / "g85_prospective_pilot_plan.jsonl"
    plan_rows = load_jsonl(plan_path)
    forbidden_keys = {"expected_decision", "private_truth", "truth_key", "oracle", "proof"}
    public_key_hits = sorted({key for row in plan_rows for key in row if key.casefold() in forbidden_keys})
    checks = [
        check("G8.5 prospective only Kimi", manifest.get("model_id") == MODEL_ID and manifest.get("only_model") is True and prospective["execution"].get("model_id") == MODEL_ID, {"model_id": manifest.get("model_id"), "only_model": manifest.get("only_model")}),
        check("G8.5 prospective complete", audit.get("planned") == 8 and audit.get("result_files") == 8 and audit.get("model_requests_private_truth_scan_hits") == 0, audit),
        check("G8.5 private truth scorer boundary", audit.get("private_truth_loaded_only_in_scorer") is True and audit.get("scientific_use") == ["PROSPECTIVE_NOT_HISTORICAL_CONFIRMATION"], audit),
        check("G8.5 public plan has no private fields", not public_key_hits and all(row.get("history_provenance") == "prospective_controlled" for row in plan_rows), {"rows": len(plan_rows), "forbidden_key_hits": public_key_hits}),
        check("G8.5 prospective arms all correct", all(item.get("correct") == item.get("planned") == 2 for item in prospective["scores"]["arm_scores"]), prospective["scores"]["arm_scores"]),
    ]
    return {"source": str(g85_root), "checks": checks, "status": "PASS" if all_pass(checks) else "FAIL", "prospective": {"calls": prospective["execution"].get("real_provider_calls"), "cost_usd": prospective["execution"].get("total_cost_usd"), "arm_scores": prospective["scores"]["arm_scores"]}}


def inspect_ledgers(repo: Path, v9_run: Path, g85_root: Path, history_root: Path, g8_root: Path) -> dict[str, Any]:
    paths = [
        v9_run / "cost_ledger.sqlite",
        g8_root / "pilot" / "cost_ledger.sqlite",
        g8_root / "formal" / "cost_ledger.sqlite",
        g8_root / "formal_adapter_repair1" / "cost_ledger.sqlite",
        g85_root / "run" / "cost_ledger.sqlite",
        g85_root / "run_adapter_repair1" / "cost_ledger.sqlite",
        g85_root / "prospective_run" / "cost_ledger.sqlite",
        history_root / "run" / "cost_ledger.sqlite",
        history_root / "repair_run" / "cost_ledger.sqlite",
    ]
    rows = [check_ledger(path) for path in paths]
    return {"status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL", "lock_free_read_only_integrity_checks": rows}


def build_gate(repo: Path, v9_audit: Path, v9_run: Path, g8_manifest: Path, g85_root: Path, history_audit: Path, history_root: Path, out: Path, report: Path | None = None) -> dict[str, Any]:
    v9 = inspect_v9(repo, v9_audit, v9_run)
    history = inspect_history_pair(history_audit)
    g8 = inspect_g8(g8_manifest)
    g85 = inspect_g85(repo, g85_root)
    ledgers = inspect_ledgers(repo, v9_run, g85_root, history_root, g8_manifest.parent)
    internal_checks = {
        "V9_G6_Q_LU_G7": v9["status"] == "PASS",
        "G7_PROSPECTIVE_HISTORY_PAIR": history["status"] == "PASS",
        "G8_SINGLE_KIMI": g8["status"] == "PASS",
        "G8_5_PROSPECTIVE": g85["status"] == "PASS",
        "ENGINEERING_LEDGER_LOCK": ledgers["status"] == "PASS",
    }
    result: dict[str, Any] = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "gate_id": "V9_INTERNAL_MACHINE_EVIDENCE_GATE_V1",
        "model_id": MODEL_ID,
        "only_model": True,
        "internal_machine_status": "UNLOCKED" if all(internal_checks.values()) else "BLOCKED",
        "internal_checks": internal_checks,
        "v9": v9,
        "history_pair": history,
        "g8": g8,
        "g8_5": g85,
        "engineering_lock": ledgers,
        "historical_denominators_unchanged": HISTORICAL_DENOMINATORS,
        "formal_scientific_release": {
            "status": "RETAINED_BLOCKED",
            "scientific_release_allowed": False,
            "overridden": False,
            "blocking_reasons": [
                "historical G6/G7 denominators and historical trace defects remain unchanged and are not replaced by prospective evidence",
                "provider billing/immutable route or weight attestation remains unavailable",
                "G7 repair is semantically partial (3/4) and strict status-token accuracy is 0/4",
                "prospective G7 history pairs and G8.5 data are not historical confirmation",
            ],
        },
        "interpretation": "Internal prospective machine work may continue automatically; this artifact is not a formal historical scientific release or an overall Agent-superiority claim.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report is not None:
        report.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# V9 内部机器证据闸门",
            "",
            f"- 生成时间：`{result['generated_at_utc']}`",
            f"- 基础模型：`{MODEL_ID}`（only_model=true）",
            f"- 内部机器状态：`{result['internal_machine_status']}`",
            f"- 正式历史科学发布：`{result['formal_scientific_release']['status']}`",
            "",
            "## 内部闸门",
            "",
        ]
        lines.extend(f"- `{name}`: `{status}`" for name, status in internal_checks.items())
        lines.extend([
            "",
            "## 实际结果",
            "",
            f"- V9：104 次真实 Kimi 调用；G6 独立数值证书 32/32；Q 8/8；LU/U REAL=4/4、CONTROL=0/4、SHAM=0/4；G7 repair D3 语义 3/4、严格 token 指标 0/4。",
            f"- G7 前瞻性 history pair：2 对、4 条记录，same-state/same-evidence 结构审计通过；资格为 `{history['confirmatory_eligibility']}`。",
            f"- G8：真实 Kimi 工程队列已完成；正式 ITT 的 24 个技术失败保留，未从分母删除。",
            f"- G8.5：前瞻 pilot 8/8 完成，四臂各 2/2；private truth 扫描 0；不作为历史确认。",
            "",
            "## 锁定边界",
            "",
            "工程执行锁已通过只读 SQLite integrity_check；正式科学发布锁仍保留，因为历史证据与外部供应商证明不能由内部重跑伪造替代。",
            "",
            "## 复算",
            "",
            f"- 机器 JSON：`{out.as_posix()}`",
            f"- 源码：`scripts/v9/internal_machine_gate.py`",
        ])
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--v9-audit", type=Path, required=True)
    parser.add_argument("--v9-run", type=Path, required=True)
    parser.add_argument("--g8-manifest", type=Path, required=True)
    parser.add_argument("--g85-root", type=Path, required=True)
    parser.add_argument("--history-audit", type=Path, required=True)
    parser.add_argument("--history-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result = build_gate(args.repo.resolve(), args.v9_audit, args.v9_run, args.g8_manifest, args.g85_root, args.history_audit, args.history_root, args.out, args.report)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["internal_machine_status"] == "UNLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
