"""Schema and leakage checks for the theory benchmark."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = ROOT / "data" / "theory_benchmark_v1"
LEGACY_DATA_DIR = ROOT / "data" / "theory_benchmark_v1"
MIXED_DATA_DIR = ROOT / "data" / "theory_benchmark_v2"

V1_COUNTS = {
    "total": 100,
    "by_level": {"1": 34, "2": 33, "3": 33},
    "by_domain": {"Theoretical Chemistry": 50, "Theoretical Biology": 50},
}
V2_COUNTS = {
    "total": 300,
    "by_level": {"1": 100, "2": 100, "3": 100},
    "by_domain": {"Theoretical Chemistry": 150, "Theoretical Biology": 150},
}
V3_COUNTS = {
    "total": 300,
    "by_level": {"1": 100, "2": 100, "3": 100},
    "by_domain": {"Theoretical Chemistry": 300, "Theoretical Biology": 0},
}

PUBLIC_FIELDS = {
    "task_id", "difficulty_level", "domain", "subdomain", "theory_name",
    "theoretical_background", "assumptions", "problem_statement",
    "mathematical_model", "given_parameters", "expected_reasoning",
    "difficulty_justification", "estimated_reasoning_steps", "source_type",
    "source_reference",
}
ANSWER_FIELDS = {
    "task_id", "ground_truth", "derivation", "verification_method",
    "verification_code", "scoring_rubric", "alternative_solutions",
    "common_failure_modes", "source_type", "source_reference",
    "verification_status", "checker",
}
LEAKAGE_MARKERS = (
    "ground_truth", "verification_code", "answer_key", "标准推导",
    "verification_status",
)
FORBIDDEN_WET_TERMS = ("湿实验", "细胞培养", "动物实验", "真实生物培养", "分子合成")


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_benchmark(data_dir: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    folder = Path(data_dir or DATA_DIR)
    public = _read(folder / "public_tasks.json")
    answers_list = _read(folder / "answer_key.json")
    manifest = _read(folder / "manifest.json")
    answers = {row["task_id"]: row for row in answers_list}
    validate_benchmark(public, answers, manifest)
    return public, answers, manifest


def load_public_benchmark(data_dir: Path | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Load only model-visible tasks and manifest; never reads the answer key."""

    folder = Path(data_dir or DATA_DIR)
    public = _read(folder / "public_tasks.json")
    manifest = _read(folder / "manifest.json")
    validate_public_tasks(public, manifest)
    return public, manifest


def validate_public_tasks(public: list[dict[str, Any]], manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate the public side without opening or requiring answer_key.json."""

    version = manifest.get("version")
    expected = {"theory-benchmark-v1": V1_COUNTS, "theory-benchmark-v2": V2_COUNTS, "theory-benchmark-v3": V3_COUNTS}.get(version)
    if expected is None:
        raise ValueError(f"unsupported theory benchmark version: {version}")
    if not isinstance(public, list) or len(public) != expected["total"]:
        raise ValueError(f"public benchmark must contain exactly {expected['total']} tasks")
    ids = [row.get("task_id") for row in public]
    if len(set(ids)) != len(public):
        raise ValueError("public task IDs must be unique")
    if len({row.get("problem_statement", "") for row in public}) != len(public):
        raise ValueError("public problem statements must be unique")
    if len({row.get("mathematical_model", "") for row in public}) != len(public):
        raise ValueError("public mathematical models must be unique")
    for row in public:
        missing = PUBLIC_FIELDS - row.keys()
        if missing:
            raise ValueError(f"{row.get('task_id')}: missing public fields {sorted(missing)}")
        marker = _contains_marker(row)
        if marker:
            raise ValueError(f"{row.get('task_id')}: answer leakage marker {marker}")
    counts = {
        "total": len(public),
        "by_level": {str(level): sum(row["difficulty_level"] == level for row in public) for level in (1, 2, 3)},
        "by_domain": {domain: sum(row["domain"] == domain for row in public) for domain in ("Theoretical Chemistry", "Theoretical Biology")},
    }
    if counts != expected or manifest.get("counts") != counts:
        raise ValueError(f"public benchmark counts do not match manifest: {counts}")
    return counts


def _contains_marker(value: Any) -> str | None:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True).lower()
    for marker in LEAKAGE_MARKERS:
        if marker.lower() in text:
            return marker
    return None


def validate_benchmark(public: list[dict[str, Any]], answers: dict[str, dict[str, Any]], manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(public, list) or not isinstance(answers, dict):
        raise ValueError("public tasks and answer key must be list/dict")
    version = (manifest or {}).get("version", "theory-benchmark-v2")
    if version == "theory-benchmark-v1":
        expected = V1_COUNTS
    elif version == "theory-benchmark-v2":
        expected = V2_COUNTS
    elif version == "theory-benchmark-v3":
        expected = V3_COUNTS
    else:
        raise ValueError(f"unsupported theory benchmark version: {version}")
    total = expected["total"]
    if len(public) != total or len(answers) != total:
        raise ValueError(f"benchmark must contain exactly {total} tasks, got {len(public)}/{len(answers)}")
    public_ids = [row.get("task_id") for row in public]
    if len(set(public_ids)) != total or set(public_ids) != set(answers):
        raise ValueError("public and answer task IDs must be unique and match")
    statements = [row.get("problem_statement", "") for row in public]
    if len(set(statements)) != total:
        raise ValueError("substantive duplicate problem statements detected")
    models = [row.get("mathematical_model", "") for row in public]
    if len(set(models)) != total:
        raise ValueError("duplicate mathematical models detected; use a distinct reasoning task")
    for row in public:
        missing = PUBLIC_FIELDS - row.keys()
        if missing:
            raise ValueError(f"{row.get('task_id')}: missing public fields {sorted(missing)}")
        if row["difficulty_level"] not in (1, 2, 3):
            raise ValueError(f"{row['task_id']}: invalid difficulty")
        marker = _contains_marker(row)
        if marker:
            raise ValueError(f"{row['task_id']}: answer leakage marker {marker}")
        text = json.dumps(row, ensure_ascii=False)
        for term in FORBIDDEN_WET_TERMS:
            if term in text:
                raise ValueError(f"{row['task_id']}: forbidden wet-lab term {term}")
    for task_id, row in answers.items():
        missing = ANSWER_FIELDS - row.keys()
        if missing:
            raise ValueError(f"{task_id}: missing answer fields {sorted(missing)}")
        if row.get("verification_status") != "已验证":
            raise ValueError(f"{task_id}: answer is not verified")
        if row.get("task_id") != task_id:
            raise ValueError(f"answer key mismatch for {task_id}")
    counts = {
        "total": total,
        "by_level": {str(level): sum(row["difficulty_level"] == level for row in public) for level in (1, 2, 3)},
        "by_domain": {domain: sum(row["domain"] == domain for row in public) for domain in ("Theoretical Chemistry", "Theoretical Biology")},
    }
    if counts != expected:
        raise ValueError(f"invalid benchmark counts: {counts}")
    if version in ("theory-benchmark-v2", "theory-benchmark-v3"):
        cell_counts = {
            (domain, level): sum(row["domain"] == domain and row["difficulty_level"] == level for row in public)
            for domain in ("Theoretical Chemistry", "Theoretical Biology")
            for level in (1, 2, 3)
        }
        expected_cell_counts = {
            (domain, level): (
                50 if version == "theory-benchmark-v2"
                else (100 if domain == "Theoretical Chemistry" else 0)
            )
            for domain in ("Theoretical Chemistry", "Theoretical Biology")
            for level in (1, 2, 3)
        }
        if cell_counts != expected_cell_counts:
            raise ValueError(f"{version} domain-level cells are not balanced: {cell_counts}")
    if manifest and manifest.get("counts") != counts:
        raise ValueError("manifest counts do not match data")
    return counts
