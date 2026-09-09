#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate the narrow deployment contract, not GitHub's entire workflow schema."""
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
ACTION = 'actions/deploy-pages@d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e'
GUARD = "(github.event_name == 'push' || github.event_name == 'workflow_dispatch') && github.ref == format('refs/heads/{0}', inputs.publication-branch)"


class WorkflowLoader(yaml.SafeLoader):
    """Keep YAML's 'on' key a string; reject duplicate mapping keys."""


WorkflowLoader.yaml_implicit_resolvers = {
    key: [(tag, regexp) for tag, regexp in rules if tag != 'tag:yaml.org,2002:bool']
    for key, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
WorkflowLoader.add_implicit_resolver('tag:yaml.org,2002:bool', re.compile(r'^(?:true|false)$', re.I), list('tTfF'))


def mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise ValueError('Workflow mapping keys must be unique strings')
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


WorkflowLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)


def load(text):
    value = yaml.load(text, Loader=WorkflowLoader)
    require(isinstance(value, dict), 'Expected a workflow object')
    return value


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate_reusable(text):
    w = load(text)
    require(set(w) == {'name', 'on', 'permissions', 'jobs'}, 'Unexpected workflow capability')
    require(set(w['on']) == {'workflow_call'}, 'Only workflow_call is allowed')
    call = w['on']['workflow_call']
    require(set(call) == {'inputs', 'outputs'}, 'Secrets or unknown call capabilities are forbidden')
    expected = {'artifact-name': 'github-pages', 'publication-branch': 'main'}
    require(set(call['inputs']) == set(expected), 'Unexpected inputs')
    for key, default in expected.items():
        entry = call['inputs'][key]
        require(set(entry) == {'description', 'type', 'required', 'default'}, 'Unexpected input settings')
        require(entry['type'] == 'string' and entry['required'] is False and entry['default'] == default, 'Input contract drift')
        require(isinstance(entry['description'], str) and bool(entry['description']), 'Missing input description')
    require(set(call['outputs']) == {'page-url'}, 'Output contract drift')
    require(call['outputs']['page-url']['value'] == '${{ jobs.deploy.outputs.page-url }}', 'Incorrect output binding')
    require(w['permissions'] == {'pages': 'write', 'id-token': 'write'}, 'Deployment permission drift')
    require(set(w['jobs']) == {'deploy'}, 'Only one deployment job is permitted')
    job = w['jobs']['deploy']
    require(set(job) == {'if', 'runs-on', 'timeout-minutes', 'concurrency', 'environment', 'outputs', 'steps'}, 'Unexpected job capability')
    require(' '.join(job['if'].split()) == GUARD, 'Unsafe event or branch guard')
    require(job['runs-on'] == 'ubuntu-24.04' and job['timeout-minutes'] == 10, 'Runner or timeout drift')
    require(job['concurrency'] == {'group': 'github-pages', 'cancel-in-progress': False}, 'Deployment concurrency drift')
    require(job['environment'] == {'name': 'github-pages', 'url': '${{ steps.deployment.outputs.page_url }}'}, 'Environment drift')
    require(job['outputs'] == {'page-url': '${{ steps.deployment.outputs.page_url }}'}, 'Job output drift')
    require(len(job['steps']) == 1, 'No additional privileged execution steps are permitted')
    step = job['steps'][0]
    require(set(step) == {'name', 'id', 'uses', 'with'}, 'Unexpected deployment step capability')
    require(step['id'] == 'deployment' and step['uses'] == ACTION, 'Unreviewed deployment action')
    require(step['with'] == {'artifact_name': '${{ inputs.artifact-name }}'}, 'No token or preview overrides allowed')
    return w


def validate_ci(text):
    w = load(text)
    require(set(w['on']) == {'push', 'pull_request', 'workflow_dispatch'}, 'Unexpected CI trigger')
    require(w['on']['push'] == {'branches': ['main']}, 'Unexpected CI push filters')
    require(w['permissions'] == {'contents': 'read'}, 'CI must be read-only')
    require(set(w['jobs']) == {'contracts'}, 'Central CI must not publish a site')
    job = w['jobs']['contracts']
    require(job['permissions'] == {'contents': 'read'}, 'CI job must be read-only')
    require('uses' not in job and 'environment' not in job, 'CI must not call a deployment')
    for step in job['steps']:
        if 'uses' in step:
            require(re.fullmatch(r'actions/(?:checkout|setup-python)@[0-9a-f]{40}', step['uses']), 'CI action must use a full reviewed SHA')
            if step['uses'].startswith('actions/checkout@'):
                require(step.get('with', {}).get('persist-credentials') is False, 'Checkout must not persist credentials')
    return w


def check_links(root):
    for name in ('README.md', 'README.ko.md'):
        text = (root / name).read_text(encoding='utf-8')
        for target in re.findall(r'\[[^\]]*\]\(([^)\s]+)\)', text):
            p = urlsplit(target)
            if p.scheme or p.netloc or not p.path:
                continue
            file = (root / unquote(p.path)).resolve()
            require(file.is_relative_to(root.resolve()) and file.is_file(), 'Missing or escaping documentation link')


def main():
    try:
        validate_reusable((ROOT / WORKFLOW).read_text(encoding='utf-8'))
        validate_ci((ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8'))
        check_links(ROOT)
        print('Workflow contract, YAML mappings and local documentation links passed')
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        print('Contract validation failed: ' + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
