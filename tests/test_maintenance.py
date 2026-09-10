# SPDX-License-Identifier: MIT
"""Offline regressions for license scope and independently updatable policy."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_contract as contract


class MaintenanceTests(unittest.TestCase):
    def setUp(self):
        self.policy = contract.read_json(ROOT / contract.CONTRACT)
        self.workflow = contract.load((ROOT / contract.WORKFLOW).read_text())
        self.ci = contract.load((ROOT / '.github/workflows/ci.yml').read_text())

    def dump(self, value):
        return yaml.safe_dump(value, sort_keys=False)

    def test_all_machine_contract_fields_reject_drift(self):
        changes = {
            'schema': 'docs-pages-deploy/v2', 'workflow': 'other.yml', 'output': 'other',
            'permissions': {'contents': 'write'}, 'events': ['pull_request'],
            'environment': 'unprotected', 'artifact_scope': 'another-run',
            'site_scope': 'another-repository', 'build_owner': 'central', 'forbidden': [],
            'gateway_onboarding': 'stale-operational-status',
        }
        for field, value in changes.items():
            policy = {**self.policy, field: value}
            with self.subTest(field=field), self.assertRaises(ValueError):
                contract.validate_reusable(self.dump(self.workflow), policy)
        for field in self.policy:
            policy = copy.deepcopy(self.policy)
            del policy[field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                contract.validate_machine(policy)

    def test_input_types_defaults_and_required_flags_are_checked(self):
        for name in self.policy['inputs']:
            for field, value in [('type', 'boolean'), ('default', 'different'), ('required', True), ('required', 0)]:
                policy = copy.deepcopy(self.policy)
                policy['inputs'][name][field] = value
                with self.subTest(name=name, field=field, value=value), self.assertRaises(ValueError):
                    contract.validate_machine(policy)
                workflow = copy.deepcopy(self.workflow)
                workflow['on']['workflow_call']['inputs'][name][field] = value
                with self.subTest(yaml=name, field=field, value=value), self.assertRaises(ValueError):
                    contract.validate_reusable(self.dump(workflow), self.policy)

    def test_output_binding_and_unknown_settings_are_checked(self):
        output = self.workflow['on']['workflow_call']['outputs']['page-url']
        for field, value in [('value', '${{ secrets.TOKEN }}'), ('extra', True)]:
            changed = copy.deepcopy(self.workflow)
            changed['on']['workflow_call']['outputs']['page-url'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                contract.validate_reusable(self.dump(changed), self.policy)
        self.assertTrue(output['description'])

    def test_runtime_and_concurrency_contract_are_checked(self):
        for group, key, value in [('runtime', 'runner', 'self-hosted'), ('runtime', 'timeout_minutes', 10.0),
                                  ('runtime', 'action', 'actions/deploy-pages@v4'),
                                  ('runtime', 'action', 'other/deploy-pages@' + 'a' * 40),
                                  ('concurrency', 'group', 'other'), ('concurrency', 'cancel_in_progress', 0)]:
            policy = copy.deepcopy(self.policy)
            policy[group][key] = value
            with self.subTest(group=group, key=key, value=value), self.assertRaises(ValueError):
                contract.validate_machine(policy)

    def test_action_update_requires_workflow_and_contract_but_not_old_fixture(self):
        original = (ROOT / 'tests/fixtures/gateway-reusable.yml').read_bytes()
        replacement = 'actions/deploy-pages@' + 'c' * 40  # Synthetic; no claim this commit exists.
        changed = copy.deepcopy(self.workflow)
        changed['jobs']['deploy']['steps'][0]['uses'] = replacement
        with self.assertRaises(ValueError):
            contract.validate_reusable(self.dump(changed), self.policy)
        policy = copy.deepcopy(self.policy)
        policy['runtime']['action'] = replacement
        with self.assertRaises(ValueError):
            contract.validate_reusable(self.dump(self.workflow), policy)
        contract.validate_reusable(self.dump(changed), policy)
        self.assertEqual((ROOT / 'tests/fixtures/gateway-reusable.yml').read_bytes(), original)
        contract.check_provenance(ROOT)

    def test_ci_cannot_skip_checks_add_privileged_settings_or_ignore_errors(self):
        mutations = [
            lambda d: d['jobs']['contracts'].update({'if': 'false'}),
            lambda d: d['jobs']['contracts'].update({'continue-on-error': True}),
            lambda d: d['jobs']['contracts'].update({'environment': 'production'}),
            lambda d: d.update({'env': {'TOKEN': '${{ secrets.TOKEN }}'}}),
            lambda d: d['jobs']['contracts']['steps'][-1].update({'if': 'false'}),
            lambda d: d['jobs']['contracts']['steps'][-1].update({'continue-on-error': True}),
            lambda d: d['jobs']['contracts']['steps'][-1].update({'run': 'true'}),
            lambda d: d['jobs']['contracts']['steps'][0]['with'].update({'repository': 'other/repo'}),
            lambda d: d['on'].update({'pull_request_target': None}),
        ]
        for index, mutate in enumerate(mutations):
            changed = copy.deepcopy(self.ci)
            mutate(changed)
            with self.subTest(index=index), self.assertRaises(ValueError):
                contract.validate_ci(self.dump(changed))

    def test_yaml_aliases_and_wrong_shapes_are_rejected(self):
        for text in ('a: &a [*a]\n', 'a: &a {}\nb: *a\n', '[]', 'null'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                contract.load(text)

    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'policy.json'
            path.write_text('{"permissions": {}, "permissions": {"contents":"write"}}')
            with self.assertRaises(ValueError):
                contract.read_json(path)

    def test_current_license_and_historical_exceptions_pass_separately(self):
        contract.check_provenance(ROOT)
        self.assertTrue((ROOT / 'LICENSE').read_text().startswith('MIT License\n'))

    def copy_source(self, root):
        for name in json.loads((ROOT / 'bootstrap/source-files.json').read_text()):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_changed_history_is_rejected_without_blocking_current_code_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_source(root)
            for name in contract.HISTORICAL:
                file = root / name
                original = file.read_bytes()
                file.write_bytes(original + b'\n')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    contract.check_provenance(root)
                file.write_bytes(original)
            contract.check_provenance(root)

    def test_mit_header_and_fixture_notice_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_source(root)
            for name in ['scripts/check_contract.py', 'tests/fixtures/gateway-reusable.yml.license']:
                file = root / name
                old = file.read_bytes()
                file.write_text('notice omitted\n')
                with self.subTest(name=name), self.assertRaises(ValueError):
                    contract.check_provenance(root)
                file.write_bytes(old)

    def test_history_cannot_be_silently_relicensed_or_omitted_from_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_source(root)
            path = root / 'PROVENANCE.json'
            policy = contract.read_json(path)
            policy['historical_artifacts'][0]['license'] = 'MIT'
            path.write_text(json.dumps(policy))
            with self.assertRaises(ValueError):
                contract.check_provenance(root)
            shutil.copyfile(ROOT / 'PROVENANCE.json', path)
            path = root / 'bootstrap/source-files.json'
            inventory = contract.read_json(path)
            inventory.remove('licensing/historical/AGPL-3.0.txt')
            path.write_text(json.dumps(inventory))
            with self.assertRaises(ValueError):
                contract.check_provenance(root)

    def test_bilingual_examples_and_local_links_pass(self):
        contract.check_links(ROOT)

    def test_broken_link_missing_translation_and_code_drift_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_source(root)
            en, ko = root / 'docs/maintenance.md', root / 'docs/maintenance.ko.md'
            original = en.read_text()
            en.write_text(original + '\n[missing](missing.md)\n')
            with self.assertRaises(ValueError):
                contract.check_links(root)
            en.write_text(original + '\n```sh\necho untranslated\n```\n')
            with self.assertRaises(ValueError):
                contract.check_links(root)
            en.write_text(original)
            ko.unlink()
            with self.assertRaises(ValueError):
                contract.check_links(root)


if __name__ == '__main__':
    unittest.main()
