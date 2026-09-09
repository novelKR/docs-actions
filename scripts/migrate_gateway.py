#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare a SHA-pinned gateway migration after the central repository passes CI.

This tool reads GitHub through the user's gh session. By default it prints a
patch only. --apply changes only a clean local PR checkout, never commits,
pushes, merges or deploys it. Unknown upstream changes fail closed.
"""
from __future__ import annotations

import argparse
import base64
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'bootstrap'))
from publish import api, run, verify_repo
from check_contract import validate_reusable

REPO = 'novelKR/docs-actions'
WORKFLOW = '.github/workflows/reusable-pages-deploy.yml'
CI = '.github/workflows/ci.yml'
TEST = 'scripts/tests/test_docs_publication.py'
FIXTURE = 'scripts/tests/fixtures/docs-actions-reusable.yml'
LOCK = '.github/docs-pages-deploy.lock.json'
BASE_BLOBS = {
    CI: '3efe605797c7dd2b1f3bb23c4613141524a4ddfc',
    WORKFLOW: '3e8d92e678397e5b7ffbeb2b10ddf27f3bb002f5',
    TEST: 'dd0ffb14d7f0896cd76bcc6b803553549d827cf7',
}


def sha40(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Use an actual reviewed full 40-character central commit SHA, not main or a tag')
    return value


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def verify_run(response, sha):
    runs = [r for r in response.get('workflow_runs', [])
            if r.get('head_sha') == sha and r.get('event') == 'push' and r.get('head_branch') == 'main'
            and r.get('path') == '.github/workflows/ci.yml']
    if not runs:
        raise ValueError('No central main-push CI run exists for this exact commit')
    latest = max(runs, key=lambda r: r['id'])
    if latest.get('status') != 'completed' or latest.get('conclusion') != 'success':
        raise ValueError('Latest central CI for this commit has not completed successfully')
    return latest['id']


def verified_central(sha):
    sha40(sha)
    verify_repo(api('repos/' + REPO))
    record = api(f'repos/{REPO}/contents/{WORKFLOW}?ref={sha}')
    if record.get('type') != 'file' or record.get('encoding') != 'base64':
        raise ValueError('Expected a regular central workflow file')
    raw = base64.b64decode(''.join(record['content'].split()), validate=True)
    if blob(raw) != record.get('sha'):
        raise ValueError('Central Git blob integrity mismatch')
    if raw != (ROOT / WORKFLOW).read_bytes():
        raise ValueError('Central workflow differs from this reviewed source package; review an updated package')
    validate_reusable(raw.decode('utf-8'))
    runs = api(f'repos/{REPO}/actions/workflows/ci.yml/runs?head_sha={sha}&event=push&branch=main&per_page=100')
    run_id = verify_run(runs, sha)
    jobs = api(f'repos/{REPO}/actions/runs/{run_id}/jobs?per_page=100')
    contracts = [job for job in jobs.get('jobs', []) if job.get('name') == 'contracts']
    if len(contracts) != 1 or contracts[0].get('conclusion') != 'success' or contracts[0].get('status') != 'completed':
        raise ValueError('Central contracts job is not verified successful')
    return raw.decode('utf-8')


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('Gateway migration anchor changed; rebase and review instead of guessing')
    return text.replace(old, new, 1)


def changes_for(files, sha, central):
    sha40(sha)
    validate_reusable(central)
    for path, expected in BASE_BLOBS.items():
        if blob(files[path].encode('utf-8')) != expected:
            raise ValueError('Gateway baseline changed: ' + path)
    return render_changes(files, sha, central)


def render_changes(files, sha, central):
    """Pure transformation; callers must first verify baseline and remote source."""
    sha40(sha)
    ref = f'{REPO}/{WORKFLOW}@{sha}'
    ci = replace_once(files[CI], 'uses: ./.github/workflows/reusable-pages-deploy.yml', 'uses: ' + ref)
    tests = replace_once(files[TEST], 'import json\n', 'import json\nimport hashlib\n')
    old = '        cls.reusable = (ROOT / ".github/workflows/reusable-pages-deploy.yml").read_text(encoding="utf-8")'
    new = '''        cls.lock = json.loads((ROOT / ".github/docs-pages-deploy.lock.json").read_text(encoding="utf-8"))
        cls.reusable = (ROOT / "scripts/tests/fixtures/docs-actions-reusable.yml").read_text(encoding="utf-8")
        if (cls.lock.get("repository") != "novelKR/docs-actions" or
                cls.lock.get("workflow") != ".github/workflows/reusable-pages-deploy.yml" or
                not re.fullmatch(r"[0-9a-f]{40}", cls.lock.get("commit", "")) or
                hashlib.sha256(cls.reusable.encode()).hexdigest() != cls.lock.get("workflow_sha256")):
            raise ValueError("Central workflow lock or verified snapshot has drifted")'''
    tests = replace_once(tests, old, new)
    tests = replace_once(tests, 'self.assertIn("uses: ./.github/workflows/reusable-pages-deploy.yml", deploy)',
                        'self.assertIn("uses: " + self.lock["repository"] + "/" + self.lock["workflow"] + "@" + self.lock["commit"], deploy)')
    lock = {'schema': 'docs-pages-consumer-lock/v1', 'repository': REPO, 'workflow': WORKFLOW,
            'commit': sha, 'workflow_sha256': hashlib.sha256(central.encode()).hexdigest(),
            'fixture': FIXTURE}
    return {CI: ci, TEST: tests, WORKFLOW: None,
            FIXTURE: central, LOCK: json.dumps(lock, indent=2) + '\n'}


def patch_for(files, changes):
    parts = []
    for path, new in sorted(changes.items()):
        old = files.get(path)
        parts.extend(difflib.unified_diff((old or '').splitlines(keepends=True), (new or '').splitlines(keepends=True),
                     fromfile='a/' + path if old is not None else '/dev/null',
                     tofile='b/' + path if new is not None else '/dev/null'))
    return ''.join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gateway', type=Path, required=True, help='Clean local checkout of the existing gateway PR branch')
    parser.add_argument('--central-commit', help='Actual central SHA; otherwise use bootstrap .local/published.json')
    parser.add_argument('--apply', action='store_true', help='Apply locally only; no commit, push, merge or deployment')
    args = parser.parse_args(argv)
    try:
        sha = args.central_commit
        if not sha:
            record = json.loads((ROOT / '.local/published.json').read_text())
            if record.get('repository') != REPO:
                raise ValueError('Unexpected bootstrap repository')
            sha = record['commit']
        sha40(sha)
        checkout = args.gateway.resolve()
        if Path(run(['git', 'rev-parse', '--show-toplevel'], cwd=checkout).strip()).resolve() != checkout:
            raise ValueError('Pass the gateway repository root')
        if run(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=checkout).strip():
            raise ValueError('The gateway working tree must be clean; preserve your work before migrating')
        if run(['git', 'branch', '--show-current'], cwd=checkout).strip() != 'codex/docs-pages-deployment':
            raise ValueError('Expected codex/docs-pages-deployment; never apply directly to main')
        origin = run(['git', 'remote', 'get-url', 'origin'], cwd=checkout).strip()
        if origin not in {'https://github.com/novelKR/agent-response-gateway.git',
                          'https://github.com/novelKR/agent-response-gateway',
                          'git@github.com:novelKR/agent-response-gateway.git'}:
            raise ValueError('Unexpected gateway origin')
        central = verified_central(sha)
        files = {path: (checkout / path).read_text(encoding='utf-8') for path in BASE_BLOBS}
        for path in (FIXTURE, LOCK):
            if (checkout / path).exists():
                raise ValueError('Existing migration file would be overwritten: ' + path)
        changes = changes_for(files, sha, central)
        patch = patch_for(files, changes)
        run(['git', 'apply', '--check', '-'], cwd=checkout, stdin=patch)
        if not args.apply:
            print(patch, end='')
            return 0
        run(['git', 'apply', '-'], cwd=checkout, stdin=patch)
        run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'scripts/tests', '-p', 'test_docs_publication.py', '-v'], cwd=checkout)
        print('Migration applied and focused tests passed in the local gateway checkout only.')
        print('Review git diff, run the full required checks, then commit/push to the existing PR. No remote gateway changes were made.')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as error:
        print('Migration stopped: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
