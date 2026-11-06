from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .common import append_jsonl, extract_json, read_jsonl, sha_obj


def _compact(value: Any, limit: int = 2400) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return text[:limit]


def run_g7(provider: Any, base: Path) -> dict[str, Any]:
    public = read_jsonl(base / "public_cases.jsonl")
    out = base / "records.jsonl"; out.parent.mkdir(parents=True, exist_ok=True); out.touch(exist_ok=True)
    existing = {(r.get("task_id"), r.get("stage")) for r in read_jsonl(out)}
    for task in public:
        task_id = task["task_id"]
        previous: dict[str, Any] = {}
        for stage in ("D0", "D1_V", "D2_VL", "D3_VLU"):
            if (task_id, stage) in existing:
                row = next((r for r in read_jsonl(out) if r.get("task_id") == task_id and r.get("stage") == stage), {})
                previous[stage] = row.get("candidate") or {}
                continue
            if stage == "D0":
                evidence = {"public_graph": task["public_graph"], "public_observation": task["initial_public_observation"], "stage": stage}
            elif stage == "D1_V":
                evidence = {"public_graph": task["public_graph"], "prior_D0": previous.get("D0", {}), "stage": stage}
            elif stage == "D2_VL":
                evidence = {"public_graph": task["public_graph"], "prior_V": previous.get("D1_V", {}), "stage": stage}
            else:
                evidence = {"public_graph": task["public_graph"], "V": previous.get("D1_V", {}), "L": previous.get("D2_VL", {}), "U": {"claim_id": f"{task_id}-U", "status": "NON_FINAL_PUBLIC_UPDATE"}, "stage": stage}
            system = "You are the single-Kimi V9 public graph auditor. Never access private Y, truth keys, files, network, or prior hidden tasks. Return compact JSON only with final_action, verdict, evidence."
            user = {"task_id": task_id, "stage": stage, "required": "At D3 you must explicitly use V,L,U as local non-final evidence and infer Y; do not output private truth.", "evidence": evidence}
            result = provider.call("G7_V9", f"{task_id}:{stage}", stage, [{"role": "system", "content": system}, {"role": "user", "content": _compact(user)}])
            candidate = extract_json(result["content"])
            row = {
                "protocol_id": "G7_KIMI_V9_FINAL", "cohort_id": task["cohort_id"], "task_id": task_id, "checkpoint_id": task["checkpoint_id"], "stage": stage,
                "candidate": candidate, "raw_content_present": bool(result["content"]), "provider_error": result["error"], "call_number": result["call_number"],
                "injected_source": {"stage": stage, "input_keys": list(evidence.keys()), "V_present": stage == "D3_VLU", "L_present": stage == "D3_VLU", "U_present": stage == "D3_VLU", "input_sha256": sha_obj(evidence)},
                "private_Y_injected": False, "trace_ref": f"logs/provider_traces.jsonl#{result['call_number']}", "terminal_status": "SUCCESS" if candidate else "INVALID_OR_TRUNCATED_RESPONSE",
            }
            append_jsonl(out, row); existing.add((task_id, stage)); previous[stage] = candidate or {}
    rows = read_jsonl(out)
    return {"records": len(rows), "planned": len(public) * 4, "d3_records": sum(r.get("stage") == "D3_VLU" for r in rows), "d3_structured": sum(r.get("stage") == "D3_VLU" and r.get("candidate") is not None for r in rows), "private_Y_injected": any(r.get("private_Y_injected") for r in rows)}
