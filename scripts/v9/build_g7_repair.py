from __future__ import annotations

import argparse
import json
from pathlib import Path

from .claim_ir import ClaimIR
from .common import write_json, write_jsonl
from .math_verifier import verify_claim


def build(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    specs = [("G7R-A", "2*x+1", "increasing", "x>=0"), ("G7R-B", "-x**2", "decreasing", "x>=0"), ("G7R-C", "x**2", "increasing", "x>=0"), ("G7R-D", "3-2*x", "decreasing", "all_real")]
    public, truth = [], []
    for task_id, expression, relation, domain in specs:
        excerpt = f"Public equation f(x)={expression}; public domain {domain}; public candidate says f is {relation}."
        ir = ClaimIR("monotonicity", expression, relation, "x", domain, excerpt); proof = verify_claim(ir)
        public.append({"cohort_id": "G7_KIMI_V9_REPAIR_PUBLIC_EQUATION", "task_id": task_id, "checkpoint_id": f"repair-checkpoint-{task_id}", "initial_public_observation": {"public_equation": f"f(x)={expression}", "public_domain": domain, "public_candidate": f"f(x)={expression} is {relation} on {domain}", "private_Y_injected": False}, "public_graph": {"nodes": [{"node_id": "V", "claim_id": f"{task_id}-V", "kind": "verdict", "statement": f"f(x)={expression} is {relation} on {domain}"}, {"node_id": "L", "claim_id": f"{task_id}-L", "kind": "lemma", "statement": "The derivative-sign lemma must support V."}, {"node_id": "U", "claim_id": f"{task_id}-U", "kind": "intermediate", "statement": "U is a non-final derivative-status update."}], "edges": [["V", "L"], ["L", "U"]], "version": 2}, "stages": ["D0", "D1_V", "D2_VL", "D3_VLU"], "private_Y_injected": False})
        truth.append({"cohort_id": "G7_KIMI_V9_REPAIR_PUBLIC_EQUATION", "task_id": task_id, "claim_ir": ir.to_dict(), "proof": proof, "expected_relation": relation, "private_Y_injected": False})
    write_jsonl(out / "public_cases.jsonl", public); write_jsonl(out / "private_truth.jsonl", truth); write_json(out / "plan.json", {"protocol": "G7_V9_REPAIR_PUBLIC_EQUATION_D0_D3", "model_id": "kimi-k2.5", "task_ids": [x["task_id"] for x in public], "private_Y_injected": False})
    return {"public_count": len(public), "planned_stage_records": len(public) * 4}


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--out", type=Path, required=True); args = parser.parse_args(); print(json.dumps(build(args.out), ensure_ascii=False, indent=2)); return 0


if __name__ == "__main__": raise SystemExit(main())
