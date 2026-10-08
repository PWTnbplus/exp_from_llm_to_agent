#!/usr/bin/env python3
"""Select model IDs from a CTFlow-like gateway without storing API credentials.

CTFlow's actual API docs endpoint was not reachable during package authoring.
All endpoint conventions below are explicitly PROVISIONAL and runtime-verified.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlsplit

DEFAULT_BASE = 'https://token.ctflow.cn/v1'  # unverified hypothesis; probe before credential use
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SELECTED = ROOT / 'configs' / 'selected_models.json'
DEFAULT_PREFLIGHT = ROOT / 'configs' / 'model_preflight.json'


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('HTTP redirect blocked; refusing credential forwarding')


def read_env(path: Path) -> dict[str, str]:
    """Read simple KEY=VALUE env entries; never print values or run shell code."""
    if not path.is_file():
        return {}
    result = {}
    for raw in path.read_text(encoding='utf-8').splitlines():
        s = raw.strip()
        if not s or s.startswith('#'):
            continue
        if s.startswith('export '):
            s = s[7:].lstrip()
        if '=' not in s:
            raise ValueError('Malformed .env assignment')
        k, v = s.split('=', 1)
        k = k.strip()
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', k):
            raise ValueError('Invalid environment key')
        v = v.strip()
        if v.startswith(('"', "'")):
            if len(v) < 2 or v[-1] != v[0]:
                raise ValueError('Unclosed .env quote')
            v = v[1:-1]
        result[k] = v
    return result


def settings(env_file: Path) -> dict[str, str]:
    config = read_env(env_file)
    # Explicit process environment takes precedence over .env.
    for key in ('CTFLOW_API_KEY', 'CTFLOW_BASE_URL'):
        if key in os.environ:
            config[key] = os.environ[key]
    config.setdefault('CTFLOW_BASE_URL', DEFAULT_BASE)
    return config


def validate_base(url: str) -> str:
    u = urlsplit(url.rstrip('/'))
    if u.scheme != 'https' or not u.netloc or u.username or u.password or u.query or u.fragment:
        raise ValueError('Base URL must be HTTPS with no credentials/query/fragment')
    if not u.hostname or not re.fullmatch(r'[a-zA-Z0-9.\-]+', u.hostname):
        raise ValueError('Invalid host')
    return url.rstrip('/')


def http_get(url: str, api_key: str | None = None, timeout: float = 12) -> tuple[int, bytes]:
    headers = {'Accept': 'application/json'}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    req = urllib.request.Request(url, headers=headers, method='GET')
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(req, timeout=timeout) as response:
            return response.status, response.read(2_000_000)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise RuntimeError('Redirect blocked, no credential forwarded') from None
        return exc.code, exc.read(2000)


def http_post(url: str, payload: dict, api_key: str, timeout: float = 25) -> tuple[int, bytes]:
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json',
               'Authorization': f'Bearer {api_key}'}
    request = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers=headers, method='POST')
    opener = urllib.request.build_opener(NoRedirect())
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.status, response.read(500000)
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            raise RuntimeError('Redirect blocked; credentials were not forwarded') from None
        return exc.code, exc.read(2000)


def verify_model(base_url: str, model_id: str, key: str, *, poster=http_post) -> bool:
    if not key:
        raise ValueError('Missing local key')
    validate_ids([model_id])
    # OpenAI-style request is PROVISIONAL, not a confirmed CTFlow contract.
    request = {'model': model_id, 'messages': [{'role': 'user', 'content': 'Reply OK.'}],
               'max_tokens': 8, 'stream': False}
    status, body = poster(validate_base(base_url) + '/chat/completions', request, key)
    if status != 200:
        return False
    try:
        response = json.loads(body)
        return isinstance(response, dict) and isinstance(response.get('choices'), list) and bool(response['choices'])
    except (ValueError, TypeError):
        return False


def catalog_endpoint(base_url: str) -> str:
    return validate_base(base_url) + '/models'


def probe(base_url: str, getter=http_get) -> tuple[bool, str]:
    """No credentials are transmitted in this first safety probe."""
    url = catalog_endpoint(base_url)
    try:
        status, _ = getter(url, None)
    except (OSError, ValueError, RuntimeError) as e:
        return False, f'Endpoint unverified: {type(e).__name__}'
    if status in (200, 401, 403):
        return True, f'Candidate model catalog responded HTTP {status}; protocol still requires validation'
    return False, f'Candidate /models not validated (HTTP {status}); explicitly supply CTFLOW_BASE_URL from provider documentation'


def parse_catalog(body: bytes) -> list[str]:
    raw = json.loads(body)
    if isinstance(raw, dict):
        models = raw.get('data', raw.get('models'))
    else:
        models = raw
    if not isinstance(models, list):
        raise ValueError('Unsupported catalog payload; use manual model IDs')
    ids = []
    for m in models:
        name = m.get('id', m.get('name')) if isinstance(m, dict) else m
        if isinstance(name, str) and name.strip():
            ids.append(name.strip())
    return list(dict.fromkeys(ids))


def discover(config: dict[str, str], getter=http_get) -> list[str]:
    key = config.get('CTFLOW_API_KEY')
    if not key:
        raise RuntimeError('CTFLOW_API_KEY missing. Put it in local .env, never in git.')
    base = validate_base(config['CTFLOW_BASE_URL'])
    valid, message = probe(base, getter=getter)
    if not valid:
        raise RuntimeError(message)
    code, body = getter(catalog_endpoint(base), key)
    if code != 200:
        raise RuntimeError(f'Model catalog HTTP {code}; check provider endpoint/permissions without exposing API Key')
    ids = parse_catalog(body)
    if not ids:
        raise RuntimeError('No discoverable model IDs; provider may require manual IDs')
    return ids


def validate_ids(ids: list[str]) -> list[str]:
    result = []
    for id_ in ids:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:/@+\-]{0,199}', id_):
            raise ValueError(f'Invalid model ID: {id_!r}')
        if id_ not in result:
            result.append(id_)
    if not result:
        raise ValueError('Select at least one model')
    return result


def save_selected(ids: list[str], path: Path, *, base_url: str, source: str) -> dict:
    payload = {'schema_version': 1, 'provider': 'ctflow', 'models': validate_ids(ids),
               'base_url': validate_base(base_url), 'source': source,
               'selected_at_utc': datetime.now(timezone.utc).isoformat(),
               'catalog_availability_not_guaranteed': True}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return payload


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='CTFlow model catalog / model selection (credentials stay local)')
    ap.add_argument('action', choices=['probe', 'list', 'select', 'show', 'verify'])
    ap.add_argument('--env-file', type=Path, default=ROOT / '.env')
    ap.add_argument('--selected-file', type=Path, default=DEFAULT_SELECTED)
    ap.add_argument('--models', nargs='+', help='Exact provider model IDs (manual selection without catalog)')
    ap.add_argument('--interactive', action='store_true')
    ap.add_argument('--allow-paid', action='store_true', help='Mandatory before any generation preflight call')
    ap.add_argument('--preflight-file', type=Path, default=DEFAULT_PREFLIGHT)
    args = ap.parse_args(argv)
    config = settings(args.env_file)
    try:
        if args.action == 'probe':
            valid, message = probe(config['CTFLOW_BASE_URL'])
            print(message)
            return 0 if valid else 2
        if args.action == 'verify':
            if not args.allow_paid:
                raise ValueError('Generation preflight may incur charges: pass --allow-paid')
            if not args.selected_file.exists():
                raise ValueError('No selected models; select first')
            key = config.get('CTFLOW_API_KEY')
            if not key:
                raise ValueError('CTFLOW_API_KEY missing')
            selected = json.loads(args.selected_file.read_text(encoding='utf-8'))
            ids = validate_ids(selected.get('models', []))
            all_results = {}
            for model_id in ids:
                try:
                    all_results[model_id] = verify_model(config['CTFLOW_BASE_URL'], model_id, key)
                except (OSError, RuntimeError, ValueError):
                    all_results[model_id] = False
                print(f'{model_id}: {"PASS" if all_results[model_id] else "FAILED"}')
            payload = {'base_url': validate_base(config['CTFLOW_BASE_URL']), 'models': all_results,
                       'verified_at_utc': datetime.now(timezone.utc).isoformat(),
                       'protocol': 'provisional_openai_chat_completions'}
            args.preflight_file.parent.mkdir(parents=True, exist_ok=True)
            args.preflight_file.write_text(json.dumps(payload, indent=2) + '\n', encoding='utf-8')
            return 0 if all(all_results.values()) else 3
        if args.action == 'show':
            if not args.selected_file.exists():
                print('No models selected yet')
                return 2
            data = json.loads(args.selected_file.read_text(encoding='utf-8'))
            print(json.dumps({'models': data['models'], 'base_url': data['base_url']}, ensure_ascii=False, indent=2))
            return 0
        if args.models:
            models = validate_ids(args.models)
            source = 'manual_unverified'
        else:
            models = discover(config)
            source = 'api_catalog'
        if args.action == 'list':
            for i, m in enumerate(models, 1):
                print(f'{i:>3}. {m}')
            return 0
        if args.interactive and not args.models:
            for i, m in enumerate(models, 1):
                print(f'{i:>3}. {m}')
            indexes = input('Select model numbers separated by commas: ')
            nums = [int(x.strip()) for x in indexes.split(',')]
            if any(i < 1 or i > len(models) for i in nums):
                raise ValueError('Selected index out of range')
            chosen = [models[i-1] for i in nums]
        else:
            chosen = models
        payload = save_selected(chosen, args.selected_file, base_url=config['CTFLOW_BASE_URL'], source=source)
        print(f'Saved {len(payload["models"])} selected model IDs to {args.selected_file}')
        if source == 'manual_unverified':
            print('Warning: manual model IDs not checked against provider; run a controlled preflight before paid tests')
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
