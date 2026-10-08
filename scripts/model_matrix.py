#!/usr/bin/env python3
"""Safe concurrent model-paired research experiment orchestration.

Does not implement scientific experiment runners: Codex must integrate the real
validated NewtonBench research CLI. Dry-run requires neither API key nor runner.
Never pass a key on the command line or write it to logs/config.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
from typing import Any

try:
    from ctflow_models import settings, validate_base, validate_ids
except ModuleNotFoundError:
    from scripts.ctflow_models import settings, validate_base, validate_ids

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/model_matrix.json'
SELECTED = ROOT / 'configs/selected_models.json'
PREFLIGHT = ROOT / 'configs/model_preflight.json'
MAX_PARALLEL = 8
RUN_MODES = ('llm_only', 'agent')
ALLOWED_FIELDS = {'model', 'mode', 'output', 'manifest', 'max_experiments', 'provider'}


def load_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError(f'Expected JSON object: {path}')
    return obj


def slug_model(model_id: str) -> str:
    prefix = re.sub('[^a-zA-Z0-9_-]', '_', model_id)[:42]
    digest = hashlib.sha256(model_id.encode('utf-8')).hexdigest()[:10]
    return f'{prefix}-{digest}'


def safe_hash(path: Path) -> str | None:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() and path.is_file() else None


def prepare(config: dict, selected: dict, *, max_parallel: int, paid: bool) -> tuple[list[str], list[str], Path]:
    ids = validate_ids(selected.get('models', []))
    if not 1 <= max_parallel <= MAX_PARALLEL:
        raise ValueError(f'max_parallel_models must be between 1 and {MAX_PARALLEL}')
    argv = config.get('runner_command')
    if not isinstance(argv, list) or any(not isinstance(x, str) for x in argv):
        raise ValueError('runner_command must be argv list, never a shell string')
    manifest = ROOT / config.get('manifest', 'configs/task_manifest.json')
    if paid:
        if not PREFLIGHT.is_file():
            raise ValueError('Missing real model preflight evidence. Run ctflow_models.py verify --allow-paid')
        checked = load_json(PREFLIGHT)
        if checked.get('base_url') != selected.get('base_url') or any(checked.get('models', {}).get(i) is not True for i in ids):
            raise ValueError('Selected models must all have verified protocol preflight for exact base URL')
        if not argv:
            raise ValueError('No validated project scientific runner configured; Codex must implement adapter first')
        if not config.get('runner_supports_budget_enforcement'):
            raise ValueError('No verified budget enforcement contract; paid runs prohibited')
        if not manifest.is_file():
            raise ValueError('Formal task manifest missing; paid run prohibited')
        cap = config.get('max_total_cost_usd')
        if not isinstance(cap, (int, float)) or cap <= 0:
            raise ValueError('Explicit positive maximum cost budget required')
    return ids, argv, manifest


def argv_for(template: list[str], *, model: str, mode: str, output: Path,
             manifest: Path, experiments: int) -> list[str]:
    if mode not in RUN_MODES:
        raise ValueError('Unknown experiment mode')
    params = {'model': model, 'mode': mode, 'output': str(output),
              'manifest': str(manifest), 'max_experiments': str(experiments), 'provider': 'ctflow'}
    result = []
    for token in template:
        # Only permit known placeholders to avoid typos in silent path interpolation.
        fields = re.findall(r'{([a-zA-Z_][a-zA-Z_0-9]*)}', token)
        if not set(fields).issubset(ALLOWED_FIELDS):
            raise ValueError('Unsupported runner command placeholder')
        for field in fields:
            token = token.replace('{' + field + '}', params[field])
        if '{' in token or '}' in token:
            raise ValueError('Unresolved runner placeholder')
        result.append(token)
    return result


def redact(text: str, key: str) -> str:
    if key:
        text = text.replace(key, '[REDACTED_API_KEY]')
    return re.sub(r'Bearer\s+[a-zA-Z0-9_.:-]{15,}', 'Bearer [REDACTED]', text, flags=re.IGNORECASE)


def run_pair(*, model: str, argv_template: list[str], root: Path, batch_dir: Path,
             manifest: Path, experiments: int, key: str, base_url: str,
             timeout: int, batch_no: int, per_job_cost: float) -> dict[str, Any]:
    model_folder = batch_dir / slug_model(model)
    model_folder.mkdir(parents=True, exist_ok=False)
    pairs: dict[str, Any] = {}
    # Counterbalance run order across model IDs so one protocol is not always first.
    digest = int(hashlib.sha256((model + ':' + str(batch_no)).encode()).hexdigest(), 16)
    order = RUN_MODES if digest % 2 == 0 else RUN_MODES[::-1]
    for mode in order:
        out = model_folder / mode
        out.mkdir()
        argv = argv_for(argv_template, model=model, mode=mode,
                        output=out, manifest=manifest, experiments=experiments)
        env = dict(os.environ)
        env.update({'CTFLOW_API_KEY': key, 'LLM_API_KEY': key,
                    'LLM_BASE_URL': base_url, 'CTFLOW_BASE_URL': base_url,
                    'LLM_MODEL': model, 'SCIENTIFIC_RUN_MODE': mode,
                    'SCIENTIFIC_TASK_MANIFEST': str(manifest),
                    'SCIENTIFIC_MAX_EXPERIMENTS': str(experiments),
                    'SCIENTIFIC_MAX_COST_USD': str(per_job_cost),
                    'SCIENTIFIC_ENFORCE_COST_CAP': '1'})
        try:
            p = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True,
                               text=True, timeout=timeout, check=False)
            output_text = redact((p.stdout or '') + '\n' + (p.stderr or ''), key)
            rc = p.returncode
        except subprocess.TimeoutExpired:
            output_text = 'TIMEOUT: scientific runner exceeded configured deadline'
            rc = 124
        (out / 'host_runner.log').write_text(output_text[-50000:], encoding='utf-8')
        result_file = out / 'result.json'
        quality = False
        explanation = 'No evaluator proof sidecar result.json'
        if rc == 0 and result_file.exists():
            try:
                raw = load_json(result_file)
                quality = (raw.get('status') == 'COMPLETED'
                           and raw.get('model_id') == model
                           and raw.get('runner') == mode
                           and raw.get('protocol_valid') is True
                           and raw.get('evaluator_valid') is True
                           and raw.get('mock') is False
                           and isinstance(raw.get('cost_usd'), (float, int))
                           and 0 <= raw['cost_usd'] <= per_job_cost
                           and raw.get('budget_enforced') is True)
                explanation = 'Verified runner result contract' if quality else 'Result contract invalid or mock'
            except (ValueError, OSError, json.JSONDecodeError):
                explanation = 'Malformed scientific evaluation result'
        pairs[mode] = {'exit_code': rc, 'verified': quality, 'reason': explanation,
                       'output_dir': str(out.relative_to(batch_dir))}
        if not quality:
            break  # fail closed; do not publish an incomplete pair as a result
    return {'model_id': model, 'paired': len(pairs) == 2 and all(x['verified'] for x in pairs.values()),
            'modes': pairs, 'order': list(order)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description='Parallel model matrix for scientific law discovery')
    ap.add_argument('action', choices=['plan', 'run'])
    ap.add_argument('--config', type=Path, default=CONFIG)
    ap.add_argument('--selected-file', type=Path, default=SELECTED)
    ap.add_argument('--env-file', type=Path, default=ROOT / '.env')
    ap.add_argument('--max-parallel-models', type=int)
    ap.add_argument('--allow-paid', action='store_true', help='Required for real API calls; must also configure cost cap and validated runner')
    ap.add_argument('--timeout-seconds', type=int, default=1800)
    args = ap.parse_args(argv)
    try:
        cfg, chosen = load_json(args.config), load_json(args.selected_file)
        parallel = args.max_parallel_models or cfg.get('max_parallel_models', 1)
        models, template, manifest = prepare(cfg, chosen, max_parallel=parallel, paid=(args.action == 'run' and args.allow_paid))
        preview = {'models': models, 'pairs_per_model': list(RUN_MODES),
                   'parallel_models': parallel, 'manifest': str(manifest),
                   'manifest_sha256': safe_hash(manifest),
                   'max_experiments_per_task': cfg.get('max_experiments_per_task', 6),
                   'cost_cap_warning': 'Global cap is split into per-run hard caps; verified runner MUST enforce each cap before API calls',
                   'runner_integrated': bool(template) and cfg.get('runner_supports_budget_enforcement') is True,
                   'paid_runs_require_explicit_authorization': True}
        if args.action == 'plan':
            print(json.dumps(preview, ensure_ascii=False, indent=2))
            return 0
        if not args.allow_paid:
            raise ValueError('Live runs blocked: pass --allow-paid after configuring validated runner and cost ceiling')
        config = settings(args.env_file)
        key = config.get('CTFLOW_API_KEY')
        if not key:
            raise ValueError('CTFLOW_API_KEY not found in local .env or process environment')
        base_url = validate_base(config['CTFLOW_BASE_URL'])
        if args.timeout_seconds < 1:
            raise ValueError('timeout must be positive')
        batch_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + secrets.token_hex(4)
        batch = ROOT / 'runs' / 'ctflow_matrix' / batch_id
        batch.mkdir(parents=True, exist_ok=False)
        per_job_cost = float(cfg['max_total_cost_usd']) / (2 * len(models))
        public = {**preview, 'batch_id': batch_id,
                  'api_base_url': base_url, 'mode': 'LIVE', 'cost_ceiling_usd': cfg['max_total_cost_usd']}
        (batch / 'manifest.json').write_text(json.dumps(public, indent=2, ensure_ascii=False), encoding='utf-8')
        reports = []
        with ThreadPoolExecutor(max_workers=parallel) as pool:
            futures = {pool.submit(run_pair, model=m, argv_template=template, root=ROOT,
                                   batch_dir=batch, manifest=manifest,
                                   experiments=int(cfg.get('max_experiments_per_task', 6)),
                                   key=key, base_url=base_url,
                                   timeout=args.timeout_seconds, batch_no=i, per_job_cost=per_job_cost): m
                       for i, m in enumerate(models)}
            for f in as_completed(futures):
                m = futures[f]
                try:
                    reports.append(f.result())
                except Exception as e:
                    reports.append({'model_id': m, 'paired': False, 'error_type': type(e).__name__})
        reports.sort(key=lambda x: models.index(x['model_id']))
        final = {'batch_id': batch_id, 'results': reports,
                 'all_paired_verified': all(x.get('paired') for x in reports)}
        (batch / 'summary.json').write_text(json.dumps(final, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps({'batch_id': batch_id, 'summary': str(batch / 'summary.json'),
                          'all_paired_verified': final['all_paired_verified']}, ensure_ascii=False))
        return 0 if final['all_paired_verified'] else 3
    except (ValueError, OSError, KeyError, json.JSONDecodeError) as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
