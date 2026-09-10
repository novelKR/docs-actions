#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Validate deployment capabilities, source evidence and documentation offline."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = '.github/workflows/reusable-pages-deploy.yml'
CONTRACT = 'contracts/pages-deploy-v1.json'
GUARD = "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == format('refs/heads/{0}', inputs.publication-branch)"
HISTORICAL = {
    'tests/fixtures/gateway-reusable.yml': '3e8d92e678397e5b7ffbeb2b10ddf27f3bb002f5',
    'licensing/historical/AGPL-3.0.txt': 'be3f7b28e564e7dd05eaf59d64adba1a4065ac0e',
    'licensing/historical/PROVENANCE-v1.json': '4587df748fbd06459862285c3584ded361771ebf',
}
MIT_SHA256 = 'a16963eff65be1e04e4309e762a0185f83e5d126e77cd72fbe8f78c1be2b266f'


class WorkflowLoader(yaml.SafeLoader):
    """Keep 'on' a string; only true/false are booleans; reject duplicate keys."""


WorkflowLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in rules if tag != 'tag:yaml.org,2002:bool']
    for key, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver('tag:yaml.org,2002:bool', re.compile(r'^(?:true|false)$', re.I), list('tTfF'))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        require(isinstance(key, str) and key not in result, 'Mapping keys must be unique strings')
        result[key] = value
    return result


def mapping(loader, node, deep=False):
    return unique_pairs((loader.construct_object(k, deep=deep), loader.construct_object(v, deep=deep))
                        for k, v in node.value)


WorkflowLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def load(text):
    # No aliases are needed for this small policy. Reject cycles and merge tricks.
    require(not any(isinstance(event, yaml.AliasEvent) for event in yaml.parse(text)), 'YAML aliases are not permitted')
    value = yaml.load(text, Loader=WorkflowLoader)
    require(isinstance(value, dict), 'Expected a workflow object')
    return value


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_pairs)


def equal(actual, expected, message):
    # Unlike Python equality, this distinguishes false from 0 and 10 from 10.0.
    require(json.dumps(actual, sort_keys=True, allow_nan=False) ==
            json.dumps(expected, sort_keys=True, allow_nan=False), message)


def keys(value, expected, message):
    require(isinstance(value, dict) and set(value) == set(expected), message)


def nonempty(value, message):
    require(isinstance(value, str) and bool(value.strip()), message)


def validate_machine(machine):
    require(isinstance(machine, dict), 'Expected a machine-readable contract')
    runtime = machine.get('runtime')
    require(isinstance(runtime, dict), 'Missing runtime contract')
    action = runtime.get('action')
    require(isinstance(action, str) and re.fullmatch(r'actions/deploy-pages@[0-9a-f]{40}', action),
            'Deploy action must be official and full-SHA pinned; review its source separately')
    expected = {
        'schema': 'docs-pages-deploy/v1', 'workflow': WORKFLOW,
        'inputs': {
            'artifact-name': {'type': 'string', 'default': 'github-pages', 'required': False},
            'publication-branch': {'type': 'string', 'default': 'main', 'required': False},
        },
        'output': 'page-url', 'permissions': {'pages': 'write', 'id-token': 'write'},
        'events': ['push', 'workflow_dispatch'], 'environment': 'github-pages',
        'artifact_scope': 'caller-current-run', 'site_scope': 'caller-repository', 'build_owner': 'caller',
        'forbidden': ['cross-repository-deploy', 'cross-run-artifact', 'build-command',
                      'secrets-inherit', 'preview', 'environment-override'],
        'runtime': {'runner': 'ubuntu-24.04', 'timeout_minutes': 10, 'action': action},
        'concurrency': {'group': 'github-pages', 'cancel_in_progress': False},
    }
    equal(machine, expected, 'Machine contract changed capabilities, types or metadata')
    return machine


def validate_reusable(text, machine=None):
    policy = validate_machine(read_json(ROOT / CONTRACT) if machine is None else machine)
    w = load(text)
    keys(w, {'name', 'on', 'permissions', 'jobs'}, 'Unexpected workflow capability')
    nonempty(w['name'], 'Missing workflow name')
    keys(w['on'], {'workflow_call'}, 'Only workflow_call is allowed')
    call = w['on']['workflow_call']
    keys(call, {'inputs', 'outputs'}, 'Secrets or unknown call capabilities are forbidden')
    keys(call['inputs'], policy['inputs'], 'Unexpected inputs')
    for key, expected in policy['inputs'].items():
        entry = call['inputs'][key]
        keys(entry, {'description', *expected}, 'Unexpected input settings')
        nonempty(entry['description'], 'Missing input description')
        equal({k: entry[k] for k in expected}, expected, 'Input contract drift')
    keys(call['outputs'], {'page-url'}, 'Output contract drift')
    output = call['outputs']['page-url']
    keys(output, {'description', 'value'}, 'Unexpected output settings')
    nonempty(output['description'], 'Missing output description')
    equal(output['value'], '${{ jobs.deploy.outputs.page-url }}', 'Incorrect output binding')
    equal(w['permissions'], policy['permissions'], 'Deployment permission drift')
    keys(w['jobs'], {'deploy'}, 'Only one deployment job is permitted')
    job = w['jobs']['deploy']
    keys(job, {'if', 'runs-on', 'timeout-minutes', 'concurrency', 'environment', 'outputs', 'steps'}, 'Unexpected job capability')
    nonempty(job['if'], 'Missing deployment guard')
    equal(' '.join(job['if'].split()), GUARD, 'Unsafe event or branch guard')
    equal(job['runs-on'], policy['runtime']['runner'], 'Runner drift')
    equal(job['timeout-minutes'], policy['runtime']['timeout_minutes'], 'Timeout drift')
    equal(job['concurrency'], {'group': policy['concurrency']['group'], 'cancel-in-progress': False}, 'Deployment concurrency drift')
    equal(job['environment'], {'name': policy['environment'], 'url': '${{ steps.deployment.outputs.page_url }}'}, 'Environment drift')
    equal(job['outputs'], {'page-url': '${{ steps.deployment.outputs.page_url }}'}, 'Job output drift')
    require(isinstance(job['steps'], list) and len(job['steps']) == 1, 'Only one privileged step is permitted')
    step = job['steps'][0]
    keys(step, {'name', 'id', 'uses', 'with'}, 'Unexpected deployment step capability')
    nonempty(step['name'], 'Missing step name')
    equal(step['id'], 'deployment', 'Deployment ID drift')
    equal(step['uses'], policy['runtime']['action'], 'Workflow action differs from the reviewed contract pin')
    equal(step['with'], {'artifact_name': '${{ inputs.artifact-name }}'}, 'No token or preview overrides allowed')
    return w


def validate_ci(text):
    w = load(text)
    keys(w, {'name', 'on', 'permissions', 'concurrency', 'jobs'}, 'Unexpected CI capability')
    equal(w['on'], {'push': {'branches': ['main']}, 'pull_request': None, 'workflow_dispatch': None}, 'Unexpected CI trigger or filter')
    equal(w['permissions'], {'contents': 'read'}, 'CI must be read-only')
    equal(w['concurrency'], {'group': 'contracts-${{ github.event.pull_request.number || github.ref }}',
                            'cancel-in-progress': True}, 'CI concurrency drift')
    keys(w['jobs'], {'contracts'}, 'Central CI must not publish a site')
    job = w['jobs']['contracts']
    keys(job, {'runs-on', 'timeout-minutes', 'permissions', 'steps'}, 'Unexpected CI job capability')
    equal(job['runs-on'], 'ubuntu-24.04', 'Unexpected CI runner')
    equal(job['timeout-minutes'], 10, 'Unexpected CI timeout')
    equal(job['permissions'], {'contents': 'read'}, 'CI job must be read-only')
    steps = job['steps']
    require(isinstance(steps, list) and len(steps) == 5, 'Unexpected CI steps')
    for step, name, settings in zip(steps[:2], ['checkout', 'setup-python'],
                                     [{'persist-credentials': False}, {'python-version': '3.14'}]):
        keys(step, {'uses', 'with'}, 'Unexpected CI action capability')
        require(isinstance(step['uses'], str) and re.fullmatch(r'actions/' + name + r'@[0-9a-f]{40}', step['uses']),
                'CI action must use an official full SHA')
        equal(step['with'], settings, 'Unexpected CI action inputs')
    commands = ['python -m pip install --disable-pip-version-check -r requirements-ci.txt',
                'python -B -m unittest discover -s tests -v', 'python -B scripts/check_contract.py']
    for step, command in zip(steps[2:], commands):
        keys(step, {'name', 'run'}, 'CI checks cannot be skipped or ignore errors')
        nonempty(step['name'], 'Missing CI step name')
        equal(step['run'], command, 'Unexpected CI command')
    return w


def check_links(root):
    docs = [root / name for name in ('README.md', 'README.ko.md', 'AGENTS.md', 'SECURITY.md')]
    docs += sorted((root / 'docs').glob('*.md'))
    for doc in docs:
        for target in re.findall(r'\[[^\]]*\]\(([^)\s]+)\)', doc.read_text(encoding='utf-8')):
            p = urlsplit(target)
            if p.scheme or p.netloc or not p.path:
                continue
            file = (doc.parent / unquote(p.path)).resolve()
            require(file.is_relative_to(root.resolve()) and file.is_file(), 'Missing or escaping documentation link')
    for source in [root / 'README.md', *sorted((root / 'docs').glob('*.md'))]:
        if source.name.endswith('.ko.md'):
            continue
        translated = source.with_name(source.stem + '.ko.md')
        require(translated.is_file(), 'Missing Korean document edition')
        # Checks technical examples, not semantic translation or editorial approval.
        blocks = lambda p: re.findall(r'^```[^\n]*\n(.*?)^```', p.read_text(encoding='utf-8'), re.M | re.S)
        equal(blocks(source), blocks(translated), 'English/Korean code example drift')


def check_provenance(root):
    p = read_json(root / 'PROVENANCE.json')
    require(p['schema'] == 'docs-actions-provenance/v2' and p['license'] == 'MIT', 'Current license metadata drift')
    require(p['runtime_contract'] == CONTRACT, 'Runtime contract path drift')
    require(p['license_transition']['historical_grants_revoked'] is False, 'Historical grants must be preserved')
    equal(p['license_transition'], {'date': '2026-09-10', 'from': 'AGPL-3.0-only', 'to': 'MIT',
                                   'scope_document': 'docs/licensing.md', 'historical_grants_revoked': False},
          'License transition metadata drift')
    records = p['historical_artifacts']
    require(isinstance(records, list) and len(records) == len(HISTORICAL), 'Historical inventory drift')
    equal({r['path']: r['git_blob_sha'] for r in records}, HISTORICAL, 'Historical provenance drift')
    equal({r['path']: r['license'] for r in records}, {
        'tests/fixtures/gateway-reusable.yml': 'AGPL-3.0-only',
        'licensing/historical/AGPL-3.0.txt': 'License document; preserve its own verbatim-copy notice.',
        'licensing/historical/PROVENANCE-v1.json': 'AGPL-3.0-only'}, 'Historical license scope drift')
    inventory = read_json(root / 'bootstrap/source-files.json')
    require(isinstance(inventory, list) and len(inventory) == len(set(inventory)), 'Invalid source inventory')
    require({*HISTORICAL, 'LICENSE', 'PROVENANCE.json', 'tests/fixtures/gateway-reusable.yml.license',
             'docs/licensing.md', 'docs/licensing.ko.md'}.issubset(inventory), 'Source archive would omit license evidence')
    for path, expected in HISTORICAL.items():
        file = root / path
        require(file.is_file() and not file.is_symlink(), 'Missing historical evidence')
        raw = file.read_bytes()
        require(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == expected,
                'Historical evidence bytes changed')
    require(hashlib.sha256((root / 'LICENSE').read_bytes()).hexdigest() == MIT_SHA256, 'Maintained MIT license text drift')
    sidecar = (root / 'tests/fixtures/gateway-reusable.yml.license').read_text()
    require(sidecar.startswith('SPDX-License-Identifier: AGPL-3.0-only\n'), 'Missing historical fixture license')
    sources = [*root.glob('scripts/*.py'), *root.glob('bootstrap/*.py'), *root.glob('tests/*.py'),
               *root.glob('.github/workflows/*.yml'), root / 'examples/caller-job.yml.example']
    for file in sources:
        require('# SPDX-License-Identifier: MIT' in file.read_text().splitlines()[:3], 'Missing maintained MIT source header')


def main():
    try:
        validate_reusable((ROOT / WORKFLOW).read_text(encoding='utf-8'))
        validate_ci((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
        check_provenance(ROOT)
        check_links(ROOT)
        print('Workflow contract, license/provenance, YAML and bilingual documentation checks passed')
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        print('Contract validation failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
