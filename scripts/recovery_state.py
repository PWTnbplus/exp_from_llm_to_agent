#!/usr/bin/env python3
"""Durable issue ledger and evidence-based handoff for Scientific Law Autopilot.

No model/API calls. The verified state, not chat history, is the source of truth.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from typing import Any

SCHEMA = 2
SEVERITIES = ('P0', 'P1', 'P2', 'P3')
ACTIVE = {'OPEN', 'IN_PROGRESS', 'BLOCKED', 'RESOLVED_UNVERIFIED'}
STATUSES = ACTIVE | {'VERIFIED'}
STATE_PATH = Path('docs/state/issues.json')
REPORT_PATH = Path('docs/state/UNRESOLVED_REPORT.md')
HANDOFF_PATH = Path('docs/state/HANDOFF.md')
GATES_PATH = Path('docs/state/gates.json')
GATES = ('G0','G1','G2','G3','G4','G5','G6','G7')
GATE_STATUSES = {'PASS', 'FAIL', 'BLOCKED', 'NOT TESTED'}


def timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')


def new_state() -> dict[str, Any]:
    return {'schema_version': SCHEMA, 'updated_at': timestamp(), 'issues': [],
            'completed_work': [], 'ingested_audits': [], 'current_focus': None}


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def load(root: Path) -> dict[str, Any]:
    path = root / STATE_PATH
    if not path.exists():
        return new_state()
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('schema_version') != SCHEMA or not isinstance(data.get('issues'), list):
        raise ValueError('Unknown/corrupt recovery ledger; do not silently overwrite it')
    return data


def save(root: Path, data: dict[str, Any]) -> None:
    data['updated_at'] = timestamp()
    _atomic_write(root / STATE_PATH, json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def _fingerprint(finding: dict[str, Any]) -> str:
    stable_id = str(finding.get('id') or '').strip()
    if re.fullmatch(r'ISSUE-[0-9a-f]{12}', stable_id):
        return stable_id
    # Prefer reviewer's explicit stable key for deduplication between audits.
    key = str(finding.get('fingerprint') or '').strip()
    if not key:
        key = '|'.join([str(finding.get('severity', '')),
                        str(finding.get('evidence', '')).strip().lower(),
                        str(finding.get('remediation', '')).strip().lower()])
    return 'ISSUE-' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:12]


def get_issue(data: dict[str, Any], issue_id: str) -> dict[str, Any]:
    for issue in data['issues']:
        if issue['id'] == issue_id:
            return issue
    raise KeyError(f'Issue {issue_id} not found')


def ingest_findings(data: dict[str, Any], findings: list[dict[str, Any]], *, source: str) -> list[str]:
    changed = []
    for finding in findings:
        if finding.get('severity') not in SEVERITIES or not finding.get('evidence') or not finding.get('remediation'):
            raise ValueError('Finding requires severity, concrete evidence and remediation')
        issue_id = _fingerprint(finding)
        existing = next((x for x in data['issues'] if x['id'] == issue_id), None)
        if existing is None:
            issue = {'id': issue_id, 'severity': finding['severity'],
                     'title': str(finding.get('title') or finding['evidence'])[:160],
                     'status': 'OPEN', 'evidence': finding['evidence'],
                     'remediation': finding['remediation'], 'first_seen': timestamp(),
                     'last_seen': timestamp(), 'source': source, 'attempts': 0,
                     'blocked_reason': None, 'verification': None,
                     'history': [{'time': timestamp(), 'event': 'OPENED', 'source': source}]}
            data['issues'].append(issue)
        else:
            issue = existing
            if issue['status'] == 'VERIFIED':
                issue['status'] = 'OPEN'
                issue['verification'] = None
                issue['history'].append({'time': timestamp(), 'event': 'REOPENED', 'source': source})
            issue['evidence'] = finding['evidence']
            issue['remediation'] = finding['remediation']
            issue['last_seen'] = timestamp()
        changed.append(issue_id)
    return changed


def update_status(data: dict[str, Any], issue_id: str, status: str, *, reason: str,
                  evidence: str = '', proof_command: str = '', host_test_passed: bool = False) -> None:
    if status not in STATUSES:
        raise ValueError(f'Invalid issue state: {status}')
    issue = get_issue(data, issue_id)
    if not reason.strip():
        raise ValueError('Status change requires a nonempty reason')
    if status == 'VERIFIED':
        if not host_test_passed or not evidence.strip() or not proof_command.strip():
            raise ValueError('VERIFIED requires independent passing host test, command, and concrete evidence')
        issue['verification'] = {'time': timestamp(), 'command': proof_command,
                                 'evidence': evidence, 'reason': reason}
        issue['blocked_reason'] = None
    elif status == 'BLOCKED':
        issue['blocked_reason'] = reason
        issue['verification'] = None
    elif status == 'OPEN':
        issue['blocked_reason'] = None
        issue['verification'] = None
    else:
        issue['verification'] = None
        if status != 'IN_PROGRESS':
            issue['blocked_reason'] = None
    if status == 'IN_PROGRESS':
        issue['attempts'] += 1
    issue['status'] = status
    issue['history'].append({'time': timestamp(), 'event': status, 'reason': reason,
                             'evidence': evidence[:1500]})


def record_completed(data: dict[str, Any], *, name: str, evidence: str,
                     verification_command: str, commit: str = '') -> None:
    if not (name.strip() and evidence.strip() and verification_command.strip()):
        raise ValueError('Completed work must have name, evidence, and verification command')
    prior = next((x for x in data['completed_work'] if x['name'] == name), None)
    item = {'name': name, 'evidence': evidence, 'verification_command': verification_command,
            'commit': commit, 'verified_at': timestamp()}
    if prior is not None:
        prior.update(item)
    else:
        data['completed_work'].append(item)


def ingest_review(root: Path, review: dict[str, Any], *, test: dict[str, Any], source: str) -> dict[str, Any]:
    data = load(root)
    ingest_findings(data, review.get('findings', []), source=source)
    # Silence is NOT resolution. Only explicit reviewer approval plus independently
    # executed host tests can verify a formerly open issue.
    test_ok = test.get('exit_code') == 0
    host_command = ' '.join(test.get('command', []))
    reported_ids = set(_fingerprint(f) for f in review.get('findings', []))
    for resolution in review.get('resolutions', []):
        if not isinstance(resolution, dict):
            continue
        issue_id = str(resolution.get('id', ''))
        if not any(x['id'] == issue_id for x in data['issues']):
            continue
        verdict = resolution.get('verdict')
        # Never simultaneously accept a live defect and a fixed verdict.
        if issue_id in reported_ids and verdict == 'VERIFIED':
            continue
        if verdict == 'VERIFIED' and test_ok and resolution.get('evidence') and host_command:
            update_status(data, issue_id, 'VERIFIED', reason='Independent reviewer verification',
                          evidence=str(resolution['evidence']), proof_command=host_command,
                          host_test_passed=True)
        elif verdict == 'BLOCKED':
            update_status(data, issue_id, 'BLOCKED', reason=str(resolution.get('reason') or 'External blocker'))
        elif verdict == 'FIXED_UNVERIFIED':
            update_status(data, issue_id, 'RESOLVED_UNVERIFIED', reason=str(resolution.get('reason') or 'Fix not proven'))
    save(root, data)
    write_reports(root, data)
    return data


def ingest_audits(root: Path) -> tuple[int, dict[str, Any]]:
    data = load(root)
    seen = set(data['ingested_audits'])
    n = 0
    for path in sorted((root / 'docs/audits').glob('cycle-*/audit.json')):
        rel = path.relative_to(root).as_posix()
        if rel in seen:
            continue
        try:
            audit = json.loads(path.read_text(encoding='utf-8'))
            findings = audit.get('review', {}).get('findings', [])
            ingest_findings(data, findings, source=rel)
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Incomplete logs must not cause silent issue erasure.
            ingest_findings(data, [{'severity': 'P1',
                'evidence': f'Could not ingest audit {rel}: {type(e).__name__}: {str(e)[:160]}',
                'remediation': 'Repair malformed audit and re-ingest; do not discard evidence.'}], source=rel)
        data['ingested_audits'].append(rel)
        n += 1
    save(root, data)
    write_reports(root, data)
    return n, data


def priority(issue: dict[str, Any]) -> tuple[int, int, str]:
    return (SEVERITIES.index(issue['severity']),
            0 if issue['status'] in {'OPEN','IN_PROGRESS'} else 1,
            issue['first_seen'])


def active_issues(data: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted((x for x in data['issues'] if x['status'] in ACTIVE), key=priority)


def unverified_gates(root: Path) -> list[str]:
    path = root / GATES_PATH
    if not path.is_file():
        return list(GATES)
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        gates = payload.get('gates', {})
        return [g for g in GATES if gates.get(g, {}).get('status') != 'PASS'
                or not gates.get(g, {}).get('evidence')
                or not gates.get(g, {}).get('verification_command')]
    except (json.JSONDecodeError, AttributeError, TypeError):
        return list(GATES)


def summary(data: dict[str, Any], max_items: int = 12) -> str:
    pending = active_issues(data)
    verified = [x for x in data['issues'] if x['status'] == 'VERIFIED']
    lines = [f'开放/未验证：{len(pending)}。已验证：{len(verified)}。',
             '不要在没有回归证据的情况下重复已验证工作。',
             '不要把审查报告中的沉默视为问题已解决。']
    if pending:
        lines.append('下一优先级问题：')
        for x in pending[:max_items]:
            lines.append(f"- {x['id']} {x['severity']} {x['status']} 尝试次数={x['attempts']}："
                         f"{x['title'][:100]}；修复={x['remediation'][:220]}")
    if data['completed_work']:
        lines.append('已验证的已完成工作（避免重复）：')
        for x in data['completed_work'][-12:]:
            lines.append(f"- {x['name']}：{x['evidence'][:180]}")
    return '\n'.join(lines)


def write_reports(root: Path, data: dict[str, Any] | None = None) -> None:
    data = data if data is not None else load(root)
    active = active_issues(data)
    done = [x for x in data['issues'] if x['status'] == 'VERIFIED']
    gates_pending = unverified_gates(root)
    header = ['# 科学定律自动驾驶——未解决问题报告', '',
              f"生成时间（UTC）：{timestamp()}", '',
              f'- 开放/阻塞/未验证：**{len(active)}**',
              f'- 已验证修复：**{len(done)}**',
              f"- 已验证完成里程碑：**{len(data['completed_work'])}**",
              f"- 未验证科学门禁：**{', '.join(gates_pending) if gates_pending else '无'}**", '',
              '## 未解决和阻塞问题', '']
    if not active:
        header += ['当前没有记录的未解决问题。这不代表所有项目门禁均已通过。', '']
    for x in active:
        header += [f"### {x['id']} — {x['severity']} — {x['status']}",
                   f"- 描述：{x['title']}",
                   f"- 证据：{x['evidence']}",
                   f"- 必需修复：{x['remediation']}",
                   f"- 尝试次数：{x['attempts']}",
                   f"- 来源：{x['source']}",
                   f"- 阻塞原因：{x['blocked_reason'] or '未记录'}", '']
    header += ['## 已验证解决的问题', '']
    if not done:
        header += ['目前没有已验证的问题。', '']
    for x in done:
        proof = x['verification'] or {}
        header += [f"- **{x['id']}**（{x['severity']}）：{x['title']}——"
                   f"`{proof.get('command', '无测试')}`；{proof.get('evidence', '')}"]
    header += ['', '## 可复用的已验证完成工作（不要重新构建）', '']
    for item in data['completed_work']:
        header += [f"- {item['name']}：{item['evidence']} | 验证："
                   f"`{item['verification_command']}` | 提交：`{item['commit'] or '未固定'}`"]
    if not data['completed_work']:
        header += ['没有已验证里程碑记录。开发前请先检查现有仓库。', '']
    header += ['', '## 科学性注意事项', '',
               '绿色单元测试只能验证工程门禁，不能证明 Agent 在科学发现上优于其他方法。',
               'Mock 输出不是科学证据。不得使用正式测试任务进行提示词调优。', '']
    _atomic_write(root / REPORT_PATH, '\n'.join(header).rstrip('\n') + '\n')
    top = active[0] if active else None
    handoff = ['# 下一位 Codex Agent 的交接说明', '',
               '## 从这里开始——不要重复最初的实现过程', '',
               '1. 检查 `git status`、分支、远程仓库和最近提交；保留用户未提交的工作。',
               '2. 阅读 `docs/state/issues.json` 和 `docs/state/UNRESOLVED_REPORT.md`。',
               '3. 阅读本交接说明和已验证完成工作。除非有证据要求，否则不要重复已固定的上游审计、适配器和测试。',
               '4. 修复**一个最高优先级的未解决问题**；运行定向检查、对抗测试，然后运行宿主回归测试。',
               '5. 审查者必须明确验证问题 ID。沉默不是修复。更新状态台账和问题报告。',
               '6. 将已审查更新提交并推送到获授权的特性分支；报告推送失败。',
               '7. 仅当没有遗留问题时，才继续下一个未验证的原始项目门禁。', '',
               f"**下一问题（Next issue:）：** {top['id'] + ' / ' + top['severity'] + ' / ' + top['title'] if top else '没有已知开放问题；请检查未验证门禁'}", '',
               '## 当前状态摘要', '', summary(data), '',
               '## 权威参考', '',
               '- `.agents/skills/scientific-law-recovery/SKILL.md`（当前 V2 指令）',
               '- `.agents/skills/scientific-law-autopilot/SKILL.md`（保留的 V1 指令）',
               '- V1 `references/` 下的两份原始完整规范',
               '- `docs/audits/`（周期级证据）', '',
               '**重要：**状态文件只报告已验证事实；不要假设当前运行的 Codex 能访问之前的聊天记录。', '']
    _atomic_write(root / HANDOFF_PATH, '\n'.join(handoff).rstrip('\n') + '\n')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=['bootstrap', 'status', 'report', 'next', 'start', 'block', 'claim-fixed', 'verify', 'milestone', 'gate-pass'])
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--id', default='')
    p.add_argument('--reason', default='')
    p.add_argument('--evidence', default='')
    p.add_argument('--command-run', default='')
    p.add_argument('--name', default='')
    p.add_argument('--commit', default='')
    p.add_argument('--gate', default='')
    args = p.parse_args()
    root = args.root.resolve()
    if args.command == 'bootstrap':
        n, data = ingest_audits(root)
        print(f'Imported {n} unseen audit reports. {summary(data)}')
        return 0
    data = load(root)
    if args.command == 'status':
        print(summary(data))
    elif args.command == 'report':
        write_reports(root, data)
        print(f'Wrote {REPORT_PATH} and {HANDOFF_PATH}')
    elif args.command == 'next':
        active = active_issues(data)
        print(json.dumps(active[0] if active else {}, ensure_ascii=False, indent=2))
    elif args.command in {'start', 'block', 'claim-fixed', 'verify'}:
        states = {'start': 'IN_PROGRESS', 'block': 'BLOCKED', 'claim-fixed': 'RESOLVED_UNVERIFIED', 'verify': 'VERIFIED'}
        if args.command == 'verify':
            raise ValueError('Manual VERIFY is intentionally disabled: independent executed review required')
        update_status(data, args.id, states[args.command], reason=args.reason)
        save(root, data)
        write_reports(root, data)
    elif args.command == 'gate-pass':
        if args.gate not in GATES or not args.evidence.strip():
            raise ValueError('Known gate ID and concrete evidence required')
        argv = shlex.split(args.command_run)
        if not (len(argv) >= 3 and Path(argv[0]).name.startswith('python')
                and argv[1] == '-m' and argv[2] in {'pytest', 'unittest'}):
            raise ValueError('Gate PASS requires an executable python -m pytest/unittest command')
        result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=300)
        if result.returncode:
            raise ValueError('Gate test failed: ' + result.stdout[-800:] + result.stderr[-800:])
        path = root / GATES_PATH
        payload = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'gates': {}}
        payload.setdefault('gates', {})[args.gate] = {
            'status': 'PASS', 'evidence': args.evidence, 'verification_command': args.command_run,
            'checked_at': timestamp(), 'commit': args.commit}
        _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False) + '\n')
        write_reports(root, data)
    elif args.command == 'milestone':
        # A human/agent cannot manufacture a completed milestone simply by claiming it.
        argv = shlex.split(args.command_run)
        if not (len(argv) >= 3 and Path(argv[0]).name.startswith('python')
                and argv[1] == '-m' and argv[2] in {'pytest', 'unittest'}):
            raise ValueError('Milestone requires an executable python -m pytest/unittest command')
        result = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise ValueError('Milestone verification command failed: ' + result.stdout[-800:] + result.stderr[-800:])
        record_completed(data, name=args.name, evidence=args.evidence,
                         verification_command=args.command_run, commit=args.commit)
        save(root, data)
        write_reports(root, data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
