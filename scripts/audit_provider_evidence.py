"""Read-only probe for provider evidence surfaces.

The probe never sends a generation request and never writes or prints the API
key.  It records only HTTP status, response hashes, bounded JSON shape, and
whether candidate billing/usage/fingerprint fields are exposed.  A 404 here
is evidence about the probed endpoint, not a universal claim about a vendor's
private account systems.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("redirect blocked")


def validate_base(value: str) -> str:
    parsed = urlsplit(value.rstrip("/"))
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("base URL must be HTTPS without credentials, query, or fragment")
    return value.rstrip("/")


def summarize_body(body: bytes) -> dict[str, object]:
    summary: dict[str, object] = {
        "body_sha256": hashlib.sha256(body).hexdigest(),
        "body_bytes": len(body),
        "json": False,
        "top_level_type": None,
        "top_level_keys": [],
        "record_count": None,
        "record_keys": [],
        "fingerprint_like_keys": [],
    }
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return summary
    summary["json"] = True
    summary["top_level_type"] = type(value).__name__
    if isinstance(value, dict):
        summary["top_level_keys"] = sorted(str(key) for key in value.keys())[:100]
        records = value.get("data") if isinstance(value.get("data"), list) else value.get("models")
        if isinstance(records, list):
            summary["record_count"] = len(records)
            keys: set[str] = set()
            for record in records[:100]:
                if isinstance(record, dict):
                    keys.update(str(key) for key in record.keys())
            summary["record_keys"] = sorted(keys)[:100]
    elif isinstance(value, list):
        summary["record_count"] = len(value)
        keys = set()
        for record in value[:100]:
            if isinstance(record, dict):
                keys.update(str(key) for key in record.keys())
        summary["record_keys"] = sorted(keys)[:100]
    all_keys = set(summary["top_level_keys"]) | set(summary["record_keys"])
    needles = ("fingerprint", "weight", "route", "revision", "version", "usage", "billing", "invoice", "cost")
    summary["fingerprint_like_keys"] = sorted(
        key for key in all_keys if any(needle in key.casefold() for needle in needles)
    )
    return summary


def get(url: str, key: str, timeout: float) -> tuple[int | None, bytes, str | None]:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "Authorization": f"Bearer {key}"},
        method="GET",
    )
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=timeout) as response:
            return response.status, response.read(2_000_000), None
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(2_000_000), None
    except (OSError, RuntimeError) as exc:
        return None, b"", type(exc).__name__


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://token.ctflow.cn/v1")
    parser.add_argument("--key-file", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()
    base = validate_base(args.base_url)
    key = args.key_file.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("key file is empty")
    # These are conservative read-only OpenAI-compatible/account endpoint
    # probes. They do not assert that undocumented paths exhaust the vendor's
    # authenticated billing surface.
    paths = ("models", "usage", "billing", "account/usage")
    endpoints = []
    for path in paths:
        status, body, error = get(f"{base}/{path}", key, args.timeout)
        endpoints.append({
            "path": f"/{path}",
            "http_status": status,
            "transport_error": error,
            "response": summarize_body(body),
        })
    result = {
        "schema_version": 1,
        "protocol_id": "PROVIDER_EVIDENCE_READ_ONLY_ENDPOINT_PROBE",
        "base_url": base,
        "authenticated": True,
        "generation_request_sent": False,
        "endpoints": endpoints,
        "interpretation": {
            "billing_or_usage_export_verified": any(
                item["path"] in {"/usage", "/billing", "/account/usage"}
                and item["http_status"] == 200
                for item in endpoints
            ),
            "immutable_weight_or_route_fingerprint_verified": any(
                item["http_status"] == 200 and item["response"]["fingerprint_like_keys"]
                for item in endpoints
            ),
            "scope": "only the listed authenticated read-only endpoints; not a vendor-wide absence claim",
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
