"""Create an immutable, hash-only source inventory for a repair cycle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def record_count(path: Path) -> int | None:
    if path.suffix.lower() not in {".jsonl", ".ndjson", ".csv"}:
        return None
    try:
        return sum(1 for line in path.open("r", encoding="utf-8") if line.strip())
    except (OSError, UnicodeError):
        return None


def git_commit(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def inventory(root: Path, paths: Iterable[Path], run_id: str, cycle: str) -> dict[str, object]:
    files: dict[str, Path] = {}
    for requested in paths:
        path = requested if requested.is_absolute() else root / requested
        if path.is_file():
            files[str(path.resolve().relative_to(root.resolve())).replace("\\", "/")] = path
        elif path.is_dir():
            for child in path.rglob("*"):
                if child.is_file():
                    rel = str(child.resolve().relative_to(root.resolve())).replace("\\", "/")
                    files[rel] = child
    rows = []
    for rel in sorted(files):
        path = files[rel]
        stat = path.stat()
        rows.append({
            "source_path": rel,
            "sha256": sha256(path),
            "size": stat.st_size,
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "record_count": record_count(path),
            "run_id": run_id,
            "private_content_exposed": False,
        })
    return {
        "schema_version": 1,
        "cycle": cycle,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(root),
        "run_id": run_id,
        "file_count": len(rows),
        "files": rows,
        "raw_files_modified": False,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--cycle", required=True)
    p.add_argument("--run-id", default="g6-g7-six-blocker-repair")
    p.add_argument("paths", nargs="+")
    args = p.parse_args()
    result = inventory(args.root.resolve(), [Path(x) for x in args.paths], args.run_id, args.cycle)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"file_count": result["file_count"], "git_commit": result["git_commit"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
