"""Strict public-DAG and non-final transition checks for LU-v2."""
from __future__ import annotations

import hashlib
import json
from typing import Any

FORBIDDEN = ("expected_decision", "private_oracle", "g7_vlu_private", "hidden_true", "correct_revised_claim")


def _scan(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if any(t in str(key).casefold() for t in FORBIDDEN): hits.append(f"{path}.{key}")
            hits.extend(_scan(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for i, child in enumerate(value): hits.extend(_scan(child, f"{path}[{i}]"))
    elif isinstance(value, str) and any(t in value.casefold() for t in FORBIDDEN):
        hits.append(path)
    return hits


def graph_sha256(graph: dict[str, Any]) -> str:
    canonical = json.loads(json.dumps(graph, ensure_ascii=False))
    for edge in canonical.get("edges", []):
        if isinstance(edge, dict): edge["graph_sha256"] = ""
    return hashlib.sha256(json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate_public_dag(graph: Any) -> dict[str, Any]:
    if not isinstance(graph, dict) or _scan(graph):
        raise ValueError("public graph contains invalid/private material")
    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise ValueError("graph requires nodes and edges")
    node_ids = [n.get("claim_id") for n in nodes if isinstance(n, dict)]
    if len(node_ids) != len(nodes) or len(set(node_ids)) != len(node_ids):
        raise ValueError("graph node IDs must be unique")
    node_set = set(node_ids)
    adjacency = {n: [] for n in node_set}
    for edge in edges:
        if not isinstance(edge, dict) or set(edge) != {"source_claim_id", "target_claim_id", "inference_rule", "assumptions", "independent_proof_ref", "graph_sha256"}:
            raise ValueError("edge schema mismatch")
        if edge["source_claim_id"] not in node_set or edge["target_claim_id"] not in node_set:
            raise ValueError("edge references unknown node")
        if not isinstance(edge["independent_proof_ref"], str) or not edge["independent_proof_ref"]:
            raise ValueError("edge proof reference required")
        if not isinstance(edge["graph_sha256"], str) or len(edge["graph_sha256"]) != 64:
            raise ValueError("edge graph hash required")
        if edge["graph_sha256"] != graph_sha256(graph):
            raise ValueError("edge graph hash mismatch")
        adjacency[edge["source_claim_id"]].append(edge["target_claim_id"])
    visiting: set[str] = set(); visited: set[str] = set()
    def visit(node: str) -> None:
        if node in visiting: raise ValueError("graph cycle detected")
        if node in visited: return
        visiting.add(node)
        for child in adjacency[node]: visit(child)
        visiting.remove(node); visited.add(node)
    for node in node_set: visit(node)
    return {"graph_sha256": graph_sha256(graph), "node_count": len(nodes), "edge_count": len(edges), "acyclic": True}


def validate_nonfinal_transition(graph: dict[str, Any], transition: dict[str, Any]) -> dict[str, Any]:
    validate_public_dag(graph)
    if _scan(transition): raise ValueError("transition contains private material")
    required = {"state_before", "state_after", "claim_id", "to_status", "trace_ref", "source"}
    if not isinstance(transition, dict) or set(transition) != required:
        raise ValueError("transition schema mismatch")
    claim = transition["claim_id"]
    nodes = {n["claim_id"]: n for n in graph["nodes"]}
    if claim not in nodes: raise ValueError("transition claim is not in graph")
    if nodes[claim].get("kind") in {"conclusion", "final", "target"}:
        raise ValueError("final node cannot be used as U transition")
    if transition["source"] != "OBSERVED_MODEL_STATE":
        raise ValueError("transition must be observed, not evaluator-derived")
    if transition["state_before"] == transition["state_after"]:
        raise ValueError("transition must change state")
    if transition["to_status"] not in {"supported", "refuted", "unresolved"}:
        raise ValueError("invalid transition status")
    return {"eligible": True, "claim_id": claim, "to_status": transition["to_status"], "trace_ref": transition["trace_ref"]}
