#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Create only novelKR/docs-actions and push an independent initial source commit.

Without --apply, this command performs local checks and prints a plan only.
It does not activate Pages, modify consumers, create tags, change permissions,
install software, delete a repository, or force-push. Requires Python 3.11+.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REPO = 'novelKR/docs-actions'
URL = 'https://github.com/' + REPO + '.git'


def run(command, *, cwd=None, stdin=None):
    result = subprocess.run(command, cwd=cwd, input=stdin, capture_output=True, text=True, check=False)
    if result.returncode:
        # Avoid dumping arbitrary command/API output into logs.
        raise RuntimeError(f'{command[0]} operation failed (exit {result.returncode}); no automatic rollback or deletion')
    return result.stdout


def api(endpoint, method='GET', body=None):
    command = ['gh', 'api', '--hostname', 'github.com', '--method', method, endpoint]
    if body is not None:
        command += ['--input', '-']
    return json.loads(run(command, stdin=json.dumps(body) if body is not None else None))


def selected_files(root):
    entries = json.loads((root / 'bootstrap/source-files.json').read_text(encoding='utf-8'))
    if not isinstance(entries, list) or not entries or len(entries) != len(set(entries)):
        raise ValueError('Invalid public file inventory')
    files = []
    for name in entries:
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name or not path.parts:
            raise ValueError('Unsafe public file path')
        if any(part.startswith('.') and part not in {'.github', '.gitignore', '.gitattributes'} for part in path.parts):
            raise ValueError('Reserved private/configuration path in public inventory')
        full = root / name
        if any(p.is_symlink() for p in [full, *list(full.parents)[:len(path.parts)]]):
            raise ValueError('Symlinks are not publishable')
        if not full.is_file() or full.stat().st_size > 256 * 1024:
            raise ValueError('Missing or oversized public source file')
        full.read_text(encoding='utf-8')
        files.append(name)
    return sorted(files)


def verify_owner(profile):
    if str(profile.get('login', '')).lower() != 'novelkr':
        raise ValueError('The active github.com account must be novelKR')


def verify_repo(repo):
    if repo.get('full_name', '').lower() != REPO.lower() or repo.get('private') is not False or repo.get('archived'):
        raise ValueError('Expected the public, unarchived novelKR/docs-actions repository')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Create a public repository and push only these selected sources')
    parser.add_argument('--existing-empty', action='store_true', help='Use an explicitly pre-created PUBLIC repository with no refs')
    args = parser.parse_args(argv)
    try:
        paths = selected_files(ROOT)
        run([sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT)
        run([sys.executable, '-B', 'scripts/check_contract.py'], cwd=ROOT)
        print(f'Plan: publish {len(paths)} selected source files to {REPO}; independent main history.')
        print('No Pages activation, consumer edit, release/tag creation or branch-protection changes.')
        if not args.apply:
            print('Dry run complete. Use --apply only after reviewing this source package.')
            return 0
        if not shutil.which('gh') or not shutil.which('git'):
            raise RuntimeError('Git and an authenticated GitHub CLI are required')
        verify_owner(api('user'))
        work = ROOT / '.local/initial-repository'
        if work.exists():
            raise ValueError('The preserved .local/initial-repository already exists; inspect/recover it before retrying')
        # Validate the user-configured author identity, never invent a name/email.
        for field in ('user.name', 'user.email'):
            if not run(['git', 'config', '--global', '--get', field]).strip():
                raise ValueError('Configure your Git author identity before publishing')
        if args.existing_empty:
            verify_repo(api('repos/' + REPO))
            refs = run(['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential', 'ls-remote', URL])
            if refs.strip():
                raise ValueError('Refusing to overwrite a repository that already has refs')
        work.mkdir(parents=True)
        for name in paths:
            target = work / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        run(['git', 'init', '-b', 'main'], cwd=work)
        run(['git', 'add', '--all'], cwd=work)
        run(['git', 'commit', '-m', 'ci: initialize caller-owned reusable Pages deployment infrastructure'], cwd=work)
        commit = run(['git', 'rev-parse', 'HEAD'], cwd=work).strip()
        if not args.existing_empty:
            created = api('user/repos', 'POST', {'name': 'docs-actions',
                'description': 'Reusable caller-owned GitHub Pages deployments with least-privilege contracts',
                'private': False, 'auto_init': False, 'has_issues': True,
                'has_wiki': False, 'has_projects': False})
            verify_repo(created)
        run(['git', 'remote', 'add', 'origin', URL], cwd=work)
        run(['git', '-c', 'credential.helper=', '-c', 'credential.helper=!gh auth git-credential',
             'push', 'origin', 'HEAD:refs/heads/main'], cwd=work)
        remote = api('repos/' + REPO + '/git/ref/heads/main')
        if remote['object']['sha'] != commit:
            raise ValueError('Remote main does not match the uploaded commit; inspect the repository')
        (ROOT / '.local/published.json').write_text(json.dumps({'repository': REPO, 'commit': commit}, indent=2) + '\n', encoding='utf-8')
        print(f'Published source: https://github.com/{REPO}/commit/{commit}')
        print('CI result and Pages deployment have NOT been asserted. Inspect central CI before migrating the consumer.')
        print(f'After central CI succeeds: python3 scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --central-commit {commit}')
        return 0
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        print('Bootstrap stopped: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
