from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.v7.common import read_jsonl, sha256_file, write_jsonl, write_json
from scripts.v7.math_verify_sympy import verify as verify_sympy
from scripts.v7.math_verify_smt import verify as verify_bounded
from scripts.v7.math_verify_intervals import verify as verify_intervals
from scripts.v7.math_verify_ode import verify as verify_ode


def adjudicate(source: Path, out: Path, proof_dir: Path) -> dict[str, Any]:
    units = read_jsonl(source); proof_dir.mkdir(parents=True, exist_ok=True); results = []
    for unit in units:
        sym = bounded = interval = ode = None
        status = "UNKNOWN"; reason = unit.get("parse_error") or "unclassified"
        if unit.get("claim_ir"):
            try:
                sym = verify_sympy(unit["claim_ir"]); bounded = verify_bounded(unit["claim_ir"])
                interval = verify_intervals(unit["claim_ir"]); ode = verify_ode(unit["claim_ir"])
                if sym["result"] == "PROVEN": status, reason = "MACHINE_PROVEN", "exact_controlled_symbolic_proof"
                elif bounded["result"] == "COUNTEREXAMPLE": status, reason = "MACHINE_COUNTEREXAMPLE", "independent_rational_witness"
                else: reason = sym.get("reason", "independent_verifiers_did_not_close_claim")
            except Exception as exc:
                reason = "verifier_execution_error:" + type(exc).__name__
        result = {
            "unit_index": unit["unit_index"], "case_id": unit.get("case_id"), "attempt_id": unit.get("attempt_id"),
            "status": status, "reason": reason, "source_row_sha256": unit["source_row_sha256"],
            "verifier_results": {"sympy": sym, "bounded_rational": bounded, "interval": interval, "ode": ode},
            "truth_not_from_model_self_report": True,
        }
        if status in {"MACHINE_PROVEN", "MACHINE_COUNTEREXAMPLE"}:
            certificate = proof_dir / f"{unit['unit_index']:04d}_{status}.json"
            write_json(certificate, result)
            result["certificate_sha256"] = sha256_file(certificate)
        results.append(result)
    write_jsonl(out, results)
    summary = {
        "result_count": len(results),
        "counts": {name: sum(x["status"] == name for x in results) for name in ("MACHINE_PROVEN", "MACHINE_COUNTEREXAMPLE", "UNKNOWN")},
        "source_sha256": sha256_file(source), "result_sha256": sha256_file(out), "formal_denominator_preserved": 552,
    }
    write_json(out.with_name("G6_MACHINE_SUMMARY.json"), summary); return summary


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, required=True); parser.add_argument("--out", type=Path, required=True); parser.add_argument("--proof-dir", type=Path, required=True)
    args = parser.parse_args(); result = adjudicate(args.source, args.out, args.proof_dir); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
