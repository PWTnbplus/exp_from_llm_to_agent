from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.v7.common import read_jsonl, write_json


def audit(graphs: Path, out: Path) -> dict:
    rows = read_jsonl(graphs); failures = []
    for graph in rows:
        node_ids = {node.get("claim_id") for node in graph.get("nodes", [])}
        for edge in graph.get("edges", []):
            if edge.get("from_claim_id") not in node_ids or edge.get("to_intermediate_claim_id") not in node_ids: failures.append(graph.get("graph_id"))
            if not edge.get("proof_certificate_ref"): failures.append("missing_proof:" + str(graph.get("graph_id")))
    result = {"graph_count": len(rows), "edge_count": sum(len(x.get("edges", [])) for x in rows), "failures": failures, "independent_edge_audit": True}
    write_json(out, result); return result


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--graphs", type=Path, required=True); parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(); result = audit(args.graphs, args.out); print(json.dumps(result, ensure_ascii=False, indent=2)); return 0 if not result["failures"] else 2


if __name__ == "__main__": raise SystemExit(main())
