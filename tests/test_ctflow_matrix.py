"""Provider/matrix non-paid adversarial tests; no real CTFlow credential required."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    obj = importlib.util.module_from_spec(spec)
    sys.modules[name] = obj
    spec.loader.exec_module(obj)
    return obj


m = _load('ctflow_models')
x = _load('model_matrix')


def test_settings_key_local_not_in_selected_file(tmp_path, monkeypatch):
    monkeypatch.delenv('CTFLOW_API_KEY', raising=False)
    secret = 'example-not-a-real-api-secret-123'
    env = tmp_path / '.env'
    env.write_text('CTFLOW_API' + '_KEY=' + secret + '\n', encoding='utf-8')
    settings = m.settings(env)
    file = tmp_path / 'selected.json'
    m.save_selected(['abc/def', 'qwen-model'], file, base_url=m.DEFAULT_BASE, source='manual')
    assert settings['CTFLOW_API_KEY'] == secret
    assert secret not in file.read_text(encoding='utf-8')


def test_endpoint_probe_never_sends_api_key():
    calls = []
    def getter(url, key):
        calls.append((url, key))
        return 401, b''
    okay, message = m.probe(m.DEFAULT_BASE, getter)
    assert okay and '401' in message
    assert calls == [('https://token.ctflow.cn/v1/models', None)]


def test_failed_endpoint_prevents_key_sent():
    calls = []
    def getter(url, key):
        calls.append((url, key))
        return 404, b'404'
    with pytest.raises(RuntimeError, match='unverified|validated|Candidate'):
        m.discover({'CTFLOW_API_KEY': 'private_key', 'CTFLOW_BASE_URL': m.DEFAULT_BASE}, getter)
    assert all(k is None for _, k in calls)


def test_catalog_models_exact_provider_ids():
    raw = json.dumps({'data': [{'id': 'qwen/foo:32b'}, {'id': 'deepseek-r1'}, {'id': 'deepseek-r1'}]}).encode()
    assert m.parse_catalog(raw) == ['qwen/foo:32b', 'deepseek-r1']
    assert m.validate_ids(['qwen/foo:32b']) == ['qwen/foo:32b']
    with pytest.raises(ValueError):
        m.validate_ids(['name; rm -rf /'])


def test_https_only_no_redirect_cross_host():
    for url in ('http://token.ctflow.cn/v1', 'https://x@y.example/v1',
                'https://example.com/v1?key=secret'):
        with pytest.raises(ValueError):
            m.validate_base(url)
    h = m.NoRedirect()
    with pytest.raises(ValueError, match='redirect'):
        h.redirect_request(None, None, 302, 'redirect', None, 'https://evil.invalid/')


def test_three_models_yield_six_paired_scopes(tmp_path):
    models = ['alpha/a', 'alpha-a', 'third']
    paths = [x.slug_model(a) for a in models]
    assert len(set(paths)) == 3
    assert len(models) * len(x.RUN_MODES) == 6
    command = ['runner', '--mode', '{mode}', '--model', '{model}', '--output', '{output}']
    generated = [x.argv_for(command, model=mod, mode=mode,
                output=tmp_path / x.slug_model(mod) / mode,
                manifest=tmp_path / 'manifest.json', experiments=6)
                for mod in models for mode in x.RUN_MODES]
    assert len({g[-1] for g in generated}) == 6
    assert generated[0][-1] != generated[2][-1]
    with pytest.raises(ValueError):
        x.argv_for(['{unknown}'], model=models[0], mode='agent', output=tmp_path,
                   manifest=tmp_path/'manifest.json', experiments=6)


def test_paid_runs_fail_closed(tmp_path):
    config = {'runner_command': [], 'runner_supports_budget_enforcement': False,
              'manifest': str(tmp_path / 'manifest.json'), 'max_total_cost_usd': 0}
    selection = {'models': ['a', 'b']}
    assert len(x.prepare(config, selection, max_parallel=2, paid=False)[0]) == 2
    with pytest.raises(ValueError, match='preflight|No validated'):
        x.prepare(config, selection, max_parallel=2, paid=True)
    with pytest.raises(ValueError, match='max_parallel'):
        x.prepare(config, selection, max_parallel=20, paid=False)


def test_cost_cap_and_result_contract(tmp_path):
    fake = tmp_path / 'fake.py'
    fake.write_text('''import json, os, pathlib, sys
out=pathlib.Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
mode=os.environ["SCIENTIFIC_RUN_MODE"]
assert os.environ["SCIENTIFIC_ENFORCE_COST_CAP"] == "1"
assert float(os.environ["SCIENTIFIC_MAX_COST_USD"]) == 0.12
result=dict(status="COMPLETED", model_id=os.environ["LLM_MODEL"], runner=mode,
  protocol_valid=True, evaluator_valid=True, mock=False, cost_usd=0.01, budget_enforced=True)
(out/"result.json").write_text(json.dumps(result))
print("simulated tool secret="+os.environ["CTFLOW_API_KEY"])
''', encoding='utf-8')
    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{}')
    # subprocess runs in repo root, fake uses absolute path to avoid dependencies.
    report = x.run_pair(model='model/1', argv_template=[sys.executable, str(fake), '{output}'],
                         root=ROOT, batch_dir=tmp_path, manifest=manifest, experiments=6,
                         key='test-key-not-real', base_url=m.DEFAULT_BASE, timeout=30,
                         batch_no=0, per_job_cost=0.12)
    assert report['paired']
    for mode in x.RUN_MODES:
        log = (tmp_path / x.slug_model('model/1') / mode / 'host_runner.log').read_text()
        assert 'test-key-not-real' not in log
        assert '[REDACTED_API_KEY]' in log


def test_mock_result_not_accepted_as_science(tmp_path):
    fake = tmp_path / 'mock.py'
    fake.write_text('''import json, os, pathlib, sys
p=pathlib.Path(sys.argv[1]); p.mkdir(parents=True, exist_ok=True)
(p/"result.json").write_text(json.dumps(dict(status="COMPLETED", model_id=os.environ["LLM_MODEL"],
 runner=os.environ["SCIENTIFIC_RUN_MODE"], protocol_valid=True,
 evaluator_valid=True,mock=True,cost_usd=0,budget_enforced=True)))
''', encoding='utf-8')
    manifest = tmp_path / 'manifest.json'; manifest.write_text('{}')
    report = x.run_pair(model='model_1', argv_template=[sys.executable, str(fake), '{output}'],
                         root=ROOT, batch_dir=tmp_path, manifest=manifest, experiments=6,
                         key='abc', base_url=m.DEFAULT_BASE, timeout=30,
                         batch_no=0, per_job_cost=0.12)
    assert not report['paired']
    assert len(report['modes']) == 1
    assert 'mock' in next(iter(report['modes'].values()))['reason']


def test_cli_plan_offline(tmp_path):
    selection = tmp_path / 'chosen.json'
    selection.write_text(json.dumps({'models': ['m1', 'm2', 'm3']}))
    p = subprocess.run([sys.executable, str(ROOT/'scripts/model_matrix.py'), 'plan',
                        '--selected-file', str(selection)], capture_output=True, text=True, cwd=ROOT)
    assert p.returncode == 0, p.stderr
    data = json.loads(p.stdout)
    assert len(data['models']) == 3
    assert data['pairs_per_model'] == ['llm_only', 'agent']
    assert not data['runner_integrated']


def test_verify_model_preflight_handles_supported_and_unsupported():
    calls = []
    def poster(url, payload, key):
        calls.append((url, payload, key))
        return 200, b'{"choices":[{"message":{"content":"OK"}}]}'
    assert m.verify_model(m.DEFAULT_BASE, 'model-abc', 'unit-secret', poster=poster)
    assert calls[0][0] == 'https://token.ctflow.cn/v1/chat/completions'
    assert calls[0][1]['max_tokens'] == 8
    assert calls[0][1]['stream'] is False
    assert calls[0][2] == 'unit-secret'
    assert not m.verify_model(m.DEFAULT_BASE, 'model-abc', 'unit-secret', poster=lambda *_: (500, b''))
    assert not m.verify_model(m.DEFAULT_BASE, 'model-abc', 'unit-secret', poster=lambda *_: (200, b'{"error":"unavailable"}'))


def test_model_matrix_live_preflight_contract(tmp_path, monkeypatch):
    path = tmp_path / 'preflight.json'
    monkeypatch.setattr(x, 'PREFLIGHT', path)
    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{}')
    opts = dict(runner_command=['python', 'research.py'],
                runner_supports_budget_enforcement=True, manifest=str(manifest),
                max_total_cost_usd=1.2)
    selected = dict(models=['a','b'], base_url=m.DEFAULT_BASE)
    with pytest.raises(ValueError, match='Missing real model preflight'):
        x.prepare(opts, selected, max_parallel=2, paid=True)
    path.write_text(json.dumps(dict(base_url=m.DEFAULT_BASE,models={'a':True,'b':False})))
    with pytest.raises(ValueError, match='verified protocol'):
        x.prepare(opts, selected, max_parallel=2, paid=True)
    path.write_text(json.dumps(dict(base_url=m.DEFAULT_BASE,models={'a':True,'b':True})))
    result=x.prepare(opts, selected,max_parallel=2,paid=True)
    assert result[0]==['a','b']


def test_no_model_credentials_committed_in_example():
    sample = (ROOT / '.env.example').read_text(encoding='utf-8')
    assert 'CTFLOW_API_KEY=\n' in sample
    assert (ROOT / '.gitignore').read_text(encoding='utf-8').find('configs/model_preflight.json') >= 0
    assert '.env' in (ROOT / '.gitignore').read_text(encoding='utf-8')


def test_autopilot_allows_safe_env_example_but_rejects_real_env(tmp_path):
    import subprocess
    spec = importlib.util.spec_from_file_location('autopilot_skill_matrix', ROOT / 'scripts/autopilot.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules['autopilot_skill_matrix'] = module
    spec.loader.exec_module(module)
    def git(*args):
        return subprocess.run(['git', *args], cwd=tmp_path, check=True, capture_output=True, text=True).stdout
    git('init', '-b', 'main')
    git('config', 'user.name', 'Unit Test')
    git('config', 'user.email', 'unit@example.test')
    (tmp_path / '.env.example').write_text('CTFLOW_API_KEY=\n')
    git('add', '.env.example')
    module.check_staged_safety(tmp_path)
    (tmp_path / '.env').write_text('CTFLOW_API_KEY=fake-unit-key')
    git('add', '.env')
    with pytest.raises(RuntimeError, match='Sensitive paths'):
        module.check_staged_safety(tmp_path)
