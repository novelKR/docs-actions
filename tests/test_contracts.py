# SPDX-License-Identifier: MIT
"""Offline contract and bootstrap/migration regressions; never access live GitHub."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'bootstrap')]
import check_contract as contract
import publish
import migrate_gateway as migrate

CENTRAL = (ROOT / contract.WORKFLOW).read_text(encoding='utf-8')
ORIGINAL = (ROOT / 'tests/fixtures/gateway-reusable.yml').read_text(encoding='utf-8')
SHA = 'b' * 40  # Synthetic test value only; never a production pin.


class ContractTests(unittest.TestCase):
    def test_valid_deployment_contract(self):
        self.assertIn('deploy', contract.validate_reusable(CENTRAL)['jobs'])

    def test_original_extraction_is_preserved_independently(self):
        self.assertIn('deploy', contract.load(ORIGINAL)['jobs'])
        self.assertEqual(migrate.blob(ORIGINAL.encode()), '3e8d92e678397e5b7ffbeb2b10ddf27f3bb002f5')

    def test_license_bytes_preserved(self):
        self.assertEqual(migrate.blob((ROOT / 'licensing/historical/AGPL-3.0.txt').read_bytes()), 'be3f7b28e564e7dd05eaf59d64adba1a4065ac0e')

    def test_yaml_on_key_and_false_boolean(self):
        doc = contract.load('on:\n  workflow_call:\nflag: false\n')
        self.assertIn('on', doc)
        self.assertIs(doc['flag'], False)

    def test_duplicate_yaml_keys_rejected(self):
        with self.assertRaises(ValueError):
            contract.load('permissions: {}\npermissions: {contents: write}\n')

    def test_unsafe_yaml_tags_rejected(self):
        with self.assertRaises(yaml.YAMLError):
            contract.load('a: !!python/object/apply:os.system [echo unsafe]\n')

    def mutated(self, change):
        doc = contract.load(CENTRAL)
        change(doc)
        return yaml.safe_dump(doc, sort_keys=False)

    def test_no_arbitrary_input_or_secrets(self):
        for key in ('target-repository', 'run-id', 'build-command', 'environment'):
            with self.subTest(key=key), self.assertRaises(ValueError):
                contract.validate_reusable(self.mutated(lambda d: d['on']['workflow_call']['inputs'].update({key: {'type': 'string'}})))
        with self.assertRaises(ValueError):
            contract.validate_reusable(self.mutated(lambda d: d['on']['workflow_call'].update({'secrets': {}})))

    def test_pr_and_tag_deployment_guards_cannot_be_relaxed(self):
        for guard in ('true', 'always()', "github.event_name == 'pull_request'", "startsWith(github.ref, 'refs/tags/')"):
            with self.subTest(guard=guard), self.assertRaises(ValueError):
                contract.validate_reusable(self.mutated(lambda d: d['jobs']['deploy'].update({'if': guard})))

    def test_privileged_job_cannot_build_or_checkout(self):
        for step in ({'run': 'npm run build'}, {'uses': 'actions/checkout@' + 'c' * 40}):
            with self.subTest(step=step), self.assertRaises(ValueError):
                contract.validate_reusable(self.mutated(lambda d: d['jobs']['deploy']['steps'].append(step)))

    def test_extra_permissions_rejected(self):
        with self.assertRaises(ValueError):
            contract.validate_reusable(self.mutated(lambda d: d['permissions'].update({'contents': 'write'})))

    def test_unpinned_action_and_preview_rejected(self):
        with self.assertRaises(ValueError):
            contract.validate_reusable(self.mutated(lambda d: d['jobs']['deploy']['steps'][0].update({'uses': 'actions/deploy-pages@v4'})))
        with self.assertRaises(ValueError):
            contract.validate_reusable(self.mutated(lambda d: d['jobs']['deploy']['steps'][0]['with'].update({'preview': 'true'})))

    def test_environment_and_concurrency_cannot_be_overridden(self):
        for field, value in (('environment', {'name': 'unprotected'}), ('concurrency', {'group': 'github-pages', 'cancel-in-progress': True})):
            with self.subTest(field=field), self.assertRaises(ValueError):
                contract.validate_reusable(self.mutated(lambda d: d['jobs']['deploy'].update({field: value})))

    def test_central_ci_is_read_only_and_has_no_deployment(self):
        contract.validate_ci((ROOT / '.github/workflows/ci.yml').read_text())

    def test_machine_readable_contract_matches_workflow(self):
        machine = json.loads((ROOT / 'contracts/pages-deploy-v1.json').read_text())
        workflow = contract.load(CENTRAL)
        self.assertEqual(machine['permissions'], workflow['permissions'])
        self.assertEqual(set(machine['inputs']), set(workflow['on']['workflow_call']['inputs']))
        self.assertEqual(machine['environment'], workflow['jobs']['deploy']['environment']['name'])


class BootstrapTests(unittest.TestCase):
    def test_public_selection_excludes_git_and_local_state(self):
        files = publish.selected_files(ROOT)
        self.assertIn('LICENSE', files)
        self.assertIn(contract.WORKFLOW, files)
        self.assertFalse(any(x.startswith(('.git/', '.local/', '.private/')) for x in files))

    def test_wrong_owner_and_private_repository_rejected(self):
        with self.assertRaises(ValueError):
            publish.verify_owner({'login': 'someone-else'})
        publish.verify_owner({'login': 'novelKR'})
        for value in ({'full_name': 'novelKR/docs-actions', 'private': True}, {'full_name': 'other/docs-actions', 'private': False}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                publish.verify_repo(value)

    def test_path_traversal_and_private_paths_rejected(self):
        for value in ('../secret', '/secret', '.git/config', '.private/a', '.env'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / 'bootstrap').mkdir()
                (root / 'bootstrap/source-files.json').write_text(json.dumps([value]))
                with self.subTest(value=value), self.assertRaises(ValueError):
                    publish.selected_files(root)

    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bootstrap').mkdir()
            (root / 'actual').write_text('test')
            (root / 'link').symlink_to(root / 'actual')
            (root / 'bootstrap/source-files.json').write_text('["link"]')
            with self.assertRaises(ValueError):
                publish.selected_files(root)

    def test_dry_run_never_calls_github(self):
        with patch.object(publish, 'run', return_value=''), patch.object(publish, 'api') as api:
            self.assertEqual(publish.main([]), 0)
            api.assert_not_called()

    def test_real_write_requires_apply_and_owner_check(self):
        with patch.object(publish, 'run', return_value=''), patch.object(publish.shutil, 'which', return_value='/bin/mock'), patch.object(publish, 'api', return_value={'login': 'other'}) as api:
            self.assertEqual(publish.main(['--apply']), 1)
            self.assertEqual(api.call_args_list[0].args, ('user',))
            self.assertEqual(api.call_count, 1)


class MigrationTests(unittest.TestCase):
    def test_mutable_refs_rejected(self):
        for value in ('main', 'v1', '', 'a' * 7, 'g' * 40, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                migrate.sha40(value)

    def success_run(self, **override):
        result = {'id': 1, 'head_sha': SHA, 'event': 'push', 'head_branch': 'main', 'path': '.github/workflows/ci.yml', 'status': 'completed', 'conclusion': 'success'}
        return {**result, **override}

    def test_exact_successful_main_push_required(self):
        self.assertEqual(migrate.verify_run({'workflow_runs': [self.success_run()]}, SHA), 1)
        for override in ({'head_sha': 'c' * 40}, {'event': 'pull_request'}, {'status': 'in_progress'}, {'conclusion': 'failure'}, {'head_branch': 'review'}, {'path': '.github/workflows/other.yml'}):
            with self.subTest(override=override), self.assertRaises(ValueError):
                migrate.verify_run({'workflow_runs': [self.success_run(**override)]}, SHA)

    def test_later_failed_ci_cannot_use_older_success(self):
        with self.assertRaises(ValueError):
            migrate.verify_run({'workflow_runs': [self.success_run(), self.success_run(id=2, conclusion='failure')]}, SHA)

    def test_remote_source_and_contracts_job_are_verified(self):
        raw = CENTRAL.encode()
        values = [{'full_name': 'novelKR/docs-actions', 'private': False},
                  {'type': 'file', 'encoding': 'base64', 'sha': migrate.blob(raw), 'content': base64.b64encode(raw).decode()},
                  {'workflow_runs': [self.success_run()]},
                  {'jobs': [{'name': 'contracts', 'status': 'completed', 'conclusion': 'success'}]}]
        with patch.object(migrate, 'api', side_effect=values):
            self.assertEqual(migrate.verified_central(SHA), CENTRAL)

    def test_remote_blob_tampering_rejected(self):
        values = [{'full_name': 'novelKR/docs-actions', 'private': False},
                  {'type': 'file', 'encoding': 'base64', 'sha': 'd' * 40, 'content': base64.b64encode(CENTRAL.encode()).decode()}]
        with patch.object(migrate, 'api', side_effect=values), self.assertRaises(ValueError):
            migrate.verified_central(SHA)

    def test_changed_gateway_baseline_rejected(self):
        files = {name: 'changed' for name in migrate.BASE_BLOBS}
        with self.assertRaises(ValueError):
            migrate.changes_for(files, SHA, CENTRAL)

    def sample_files(self):
        test_source = '''import json
from pathlib import Path
ROOT = Path(".")
class Checks:
    @classmethod
    def setUpClass(cls):
        cls.reusable = (ROOT / ".github/workflows/reusable-pages-deploy.yml").read_text(encoding="utf-8")
    def check(self):
        self.assertIn("uses: ./.github/workflows/reusable-pages-deploy.yml", deploy)
'''
        return {migrate.CI: 'jobs:\n  docs-pages:\n    uses: ./.github/workflows/reusable-pages-deploy.yml\n', migrate.TEST: test_source, migrate.WORKFLOW: ORIGINAL}

    def test_migration_writes_literal_sha_lock_and_snapshot(self):
        result = migrate.render_changes(self.sample_files(), SHA, CENTRAL)
        self.assertIn('@' + SHA, result[migrate.CI])
        self.assertIsNone(result[migrate.WORKFLOW])
        self.assertEqual(result[migrate.FIXTURE], CENTRAL)
        lock = json.loads(result[migrate.LOCK])
        self.assertEqual(lock['workflow_sha256'], hashlib.sha256(CENTRAL.encode()).hexdigest())
        compile(result[migrate.TEST], 'migration-test', 'exec')

    def test_missing_or_duplicate_anchors_rejected(self):
        for value in ('none', 'old old'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                migrate.replace_once(value, 'old', 'new')

    def test_generated_patch_really_applies_add_edit_and_delete(self):
        files = self.sample_files()
        changes = migrate.render_changes(files, SHA, CENTRAL)
        unified = migrate.patch_for(files, changes)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', '-b', 'review'], cwd=root, check=True)
            for name, text in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text)
            subprocess.run(['git', 'apply', '--check', '-'], cwd=root, input=unified, text=True, check=True)
            subprocess.run(['git', 'apply', '-'], cwd=root, input=unified, text=True, check=True)
            for name, text in changes.items():
                if text is None:
                    self.assertFalse((root / name).exists())
                else:
                    self.assertEqual((root / name).read_text(), text)


if __name__ == '__main__':
    unittest.main()
