"""Build a clean public repository from a safe Git base plus an explicit allowlist.

This script never deletes or rewrites the research checkout. It creates a
separate output directory, starts from ``main`` (which contains the public
baseline), overlays only public engineering files, scans paths/content, and
optionally initializes a local Git repository for review and publication.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_PARTS = {
    "api_key", "secrets", "credentials", "private", "private_data",
    "private_oracle", "ground_truth_private", "runs", "checkpoints",
    "cache", "logs", "local_archive",
}
FORBIDDEN_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".pt", ".pth", ".ckpt", ".safetensors", ".sqlite"}
SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}"),
)
OVERLAY_FILES = (
    "README.md", "AGENTS.md", ".gitignore", "pyproject.toml", "requirements.lock",
    "LICENSE", "CITATION.cff", "configs/experiment_registry.yaml", "configs/global.yaml",
    "configs/models.example.yaml", "scripts/reproduce.py", "scripts/verify_results.py",
    "scripts/check_environment.py", "scripts/generate_figures.py", "scripts/build_public_release.py",
    "docs/EXPERIMENT_OVERVIEW.md", "docs/ARCHITECTURE.md",
    "docs/DATA_ACCESS.md", "docs/PUBLISHING.md",
    "docs/audits/20261106_engineering_cycle.md",
    ".github/workflows/tests.yml",
    "scripts/run_g5_answer_given.py", "scripts/run_g6_counterfactual.py",
    "scripts/run_g7_failure_localization.py", "scripts/run_g8_causal_mechanism.py",
    "scripts/run_g8_checkpoint_replicates.py", "scripts/g8_5_mechanism_identification.py",
    "scripts/run_g85_parallel.py", "scripts/run_single_kimi_g1_g3_canonical.py",
    "scripts/run_single_kimi_g1_g5_incremental.py",
)
OVERLAY_DIRS = (
    "experiments", "tests/unit", "tests/integration", "tests/security",
    "src/scientific_discovery/project", "scripts/v7", "scripts/v8", "scripts/v9",
)


def _copy_path(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    else:
        shutil.copy2(source, target)


def _git_archive(base_ref: str, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(["git", "archive", "--format=tar", base_ref], cwd=ROOT, stdout=subprocess.PIPE)
    assert archive.stdout is not None
    extract = subprocess.run(["tar", "-xf", "-", "-C", str(output)], stdin=archive.stdout, check=True)
    del extract
    return_code = archive.wait()
    if return_code:
        raise SystemExit(f"git archive failed for {base_ref}: {return_code}")


def _iter_files(root: Path) -> Iterable[Path]:
    yield from (path for path in root.rglob("*") if path.is_file())


def _security_scan(root: Path) -> dict[str, object]:
    forbidden_paths: list[str] = []
    secret_hits: list[str] = []
    file_hashes: dict[str, str] = {}
    for path in _iter_files(root):
        relative = path.relative_to(root).as_posix()
        parts = set(relative.lower().split("/"))
        if parts & FORBIDDEN_PARTS or path.suffix.lower() in FORBIDDEN_SUFFIXES:
            forbidden_paths.append(relative)
        try:
            data = path.read_bytes()
        except OSError:
            continue
        file_hashes[relative] = hashlib.sha256(data).hexdigest()
        if len(data) <= 2_000_000:
            text = data.decode("utf-8", errors="ignore")
            for pattern in SECRET_PATTERNS:
                if pattern.search(text):
                    secret_hits.append(relative)
                    break
    report = {"forbidden_paths": sorted(forbidden_paths), "secret_hits": sorted(secret_hits), "file_count": len(file_hashes), "sha256": file_hashes}
    (root / "PUBLIC_RELEASE_SECURITY_SCAN.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if forbidden_paths or secret_hits:
        raise SystemExit(f"public release security scan failed: {len(forbidden_paths)} forbidden paths, {len(secret_hits)} secret hits")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--init-git", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        raise SystemExit("refusing to build public release inside the research checkout")
    if output.exists() and any(output.iterdir()):
        raise SystemExit(f"refusing to overwrite non-empty output: {output}")
    _git_archive(args.base_ref, output)
    for relative in OVERLAY_FILES:
        source = ROOT / relative
        if source.exists():
            _copy_path(source, output / relative)
    for relative in OVERLAY_DIRS:
        source = ROOT / relative
        if source.exists():
            _copy_path(source, output / relative)
    report = _security_scan(output)
    if args.init_git:
        subprocess.run(["git", "init", "-b", "main"], cwd=output, check=True)
        subprocess.run(["git", "add", "-A"], cwd=output, check=True)
        subprocess.run(["git", "commit", "-m", "chore: publish safe engineering package"], cwd=output, check=True)
    print(json.dumps({"output": str(output), "base_ref": args.base_ref, "file_count": report["file_count"], "security": "PASS"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
