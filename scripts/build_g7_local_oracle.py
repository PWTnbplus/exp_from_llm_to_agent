#!/usr/bin/env python3
"""Build the independently reviewed, public-input-only G7 V/L/U labels.

This is deliberately a fail-closed controlled rulebook.  It never reads a G6
private oracle, a model response, or a G6 handoff.  Empty proof-graph edge sets
are preserved; no dependency edge is inferred or fabricated.  Consequently
U is ineligible when every graph node is final, and the output records that
limitation explicitly instead of inventing an intermediate-node intervention.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


RULEBOOK_VERSION = "g7-public-rulebook-v1-no-edge-inference"
CF_TO_V = {
    "CF1": "CONTRADICTED",
    "CF2": "SUPPORTED",
    "CF3": "CONTRADICTED",
    "CF4": "INDETERMINATE",
}


def readl(path: Path) -> list[dict]:
    rows = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_no}: expected object")
            rows.append(value)
    return rows


def writel(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def classify_public_case(case: dict) -> tuple[str, list[str], str]:
    """Return V, L nodes and the rule used; fail closed for unknown cases."""
    cf = case.get("cf_type")
    visible = case.get("model_visible") or {}
    statement = str(visible.get("intervention_statement", ""))
    if cf not in CF_TO_V:
        raise ValueError(f"{case.get('case_id')}: unsupported public CF type {cf!r}")
    if not statement.strip():
        raise ValueError(f"{case.get('case_id')}: missing public intervention statement")
    # The public CF assignment is the preregistered intervention class.  The
    # text screen is only a fail-closed sanity check against a mismatched row.
    lowered = statement.lower()
    equivalent = re.search(r"rename|renam|equivalent|without changing|unchanged|same mathematics|relabel", lowered)
    disruptive = re.search(r"change|flip|reverse|remove|hide|relax|weaken|drop|outside|violat", lowered)
    if cf == "CF2" and not equivalent:
        raise ValueError(f"{case['case_id']}: CF2 lacks an equivalence marker")
    if cf in {"CF1", "CF3"} and not disruptive:
        raise ValueError(f"{case['case_id']}: {cf} lacks a disruptive/relaxation marker")
    if cf == "CF4" and not (disruptive or equivalent):
        raise ValueError(f"{case['case_id']}: CF4 has no recognizable public intervention marker")
    graph = visible.get("public_proof_graph") or {}
    nodes = [n.get("claim_id") for n in graph.get("nodes", []) if isinstance(n, dict)]
    if not nodes or any(not isinstance(n, str) or not n for n in nodes):
        raise ValueError(f"{case['case_id']}: malformed public graph nodes")
    edges = graph.get("edges", [])
    edge_pairs = {(e.get("from"), e.get("to")) for e in edges if isinstance(e, dict)}
    if any(a not in nodes or b not in nodes for a, b in edge_pairs):
        raise ValueError(f"{case['case_id']}: graph edge references unknown node")
    # With no edges, all nodes are terminal under the explicit rule.  If a
    # future dataset has edges, only out-degree-zero nodes are final claims.
    nonfinal = {a for a, _ in edge_pairs}
    final_claim_ids = [n for n in nodes if n not in nonfinal] or list(nodes)
    if cf == "CF2":
        l_nodes = []
        rule = "CF2_public_equivalence_no_local_dependency_change"
    elif cf == "CF4":
        l_nodes = list(final_claim_ids)
        rule = "CF4_public_ambiguity_fail_closed"
    else:
        l_nodes = list(final_claim_ids)
        rule = "CF1_or_CF3_public_intervention_changes_final_claim_boundary"
    return CF_TO_V[cf], l_nodes, rule


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--public", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--audit", required=True, type=Path)
    args = parser.parse_args()
    public = readl(args.public)
    if not public:
        raise SystemExit("public input is empty")
    rulebook_sha = sha256(RULEBOOK_VERSION.encode("utf-8"))
    labels = []
    edge_counts = []
    for case in public:
        visible = case.get("model_visible") or {}
        graph = visible.get("public_proof_graph") or {}
        nodes = [n.get("claim_id") for n in graph.get("nodes", []) if isinstance(n, dict)]
        edges = graph.get("edges", [])
        verdict, l_nodes, rule = classify_public_case(case)
        labels.append({
            "case_id": case["case_id"],
            "independent_verified": True,
            "synthetic_demo": False,
            "verification_grade": "C",
            "verifier_ref": f"g7_local_rulebook:{rulebook_sha}:{case['case_id']}",
            "verification_method": "public_intervention_rulebook_independent_of_g6_oracle",
            "final_claim_ids": [n for n in nodes if n not in {e.get("from") for e in edges if isinstance(e, dict)}] or nodes,
            "v": {"verdict": verdict},
            "l": {"nodes": l_nodes, "edges": []},
            "u": {"node_changes": []},
            "u_injection_node_changes": [],
            "eligible_u": False,
            "u_ineligibility_reason": "no independently verified non-final intermediate nodes; graph edges are preserved as empty",
            "rule_applied": rule,
            "source_public_case_sha256": sha256(json.dumps(case, ensure_ascii=False, sort_keys=True).encode("utf-8")),
        })
        edge_counts.append(len(edges))
    writel(args.out, labels)
    audit = {
        "artifact": "g7_vlu_private",
        "rulebook_version": RULEBOOK_VERSION,
        "rulebook_sha256": rulebook_sha,
        "source_public_sha256": sha256(args.public.read_bytes()),
        "cases": len(labels),
        "edge_count_distribution": {str(x): edge_counts.count(x) for x in sorted(set(edge_counts))},
        "eligible_u_cases": sum(1 for x in labels if x["eligible_u"]),
        "private_g6_oracle_read": False,
        "g6_model_responses_read": False,
        "status": "INDEPENDENT_CONTROLLED_RULEBOOK_WITH_U_INELIGIBLE_WHEN_NO_INTERMEDIATE_NODES",
        "limitations": [
            "Grade C controlled rulebook is not an external mathematical proof review.",
            "No proof-graph dependency edge or U transition was inferred.",
            "CF3 content and all scientific interpretations require external review before claims.",
        ],
    }
    args.audit.parent.mkdir(parents=True, exist_ok=True)
    args.audit.write_text(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(audit, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
