# SPDX-License-Identifier: MIT
"""Regress the selected-source boundary and the actual publication contract."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('site_tools',ROOT/'docs-site/scripts/site.py')
site=importlib.util.module_from_spec(spec);spec.loader.exec_module(site)
sys.path.insert(0,str(ROOT/'scripts'))
import check_contract

class SiteTests(unittest.TestCase):
    def test_registered_sources_exist_in_both_languages(self):
        pages=site.pages(ROOT)
        self.assertEqual(len(pages),10)
        self.assertEqual({p['locale'] for p in pages},{'en','ko'})
        self.assertEqual(len({p['route'] for p in pages}),10)

    def test_prose_links_have_no_duplicate_base(self):
        text=site.remap('[Guide](docs/maintenance.md)', 'README.md', {'docs/maintenance.md':'/guide/maintenance'}, ROOT,'a'*40)
        self.assertEqual(text,'[Guide](/guide/maintenance)')

    def test_site_omits_language_preamble_but_preserves_original_source(self):
        raw=(ROOT/'README.md').read_bytes()
        rendered=site.remap(raw.decode(),'README.md',{},ROOT,'a'*40)
        self.assertNotIn('[English](',rendered)
        self.assertEqual((ROOT/'README.md').read_bytes(),raw)
        code='```md\n[English](README.md) | [한국어](README.ko.md)\n```\n'
        self.assertEqual(site.remap(code,'README.md',{},ROOT,'a'*40),code)

    def test_fenced_and_inline_examples_are_not_executed_or_rewritten(self):
        text='`<placeholder>`\n```yaml\n${{ secrets.EXAMPLE }}\n[example](missing.md)\n```\n'
        self.assertEqual(site.remap(text,'README.md',{},ROOT,'a'*40),text)

    def test_unreviewed_html_includes_resources_and_external_schemes_fail(self):
        for text in ['<script>alert(1)</script>','{{ expression }}','<<< source','![image](https://example.test/image)','[x](javascript:bad)','[x](../../private.md)']:
            with self.subTest(text=text), self.assertRaises(ValueError):site.remap(text,'README.md',{},ROOT,'a'*40)

    def test_source_symlinks_and_reserved_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'file').write_text('data');(root/'link').symlink_to(root/'file')
            for p in ['link','../file','/file','.private/file']:
                with self.subTest(path=p),self.assertRaises(ValueError):site.safe_file(root,p)

    def fixture(self,root):
        out=root/'.local/docs-site/dist';out.mkdir(parents=True)
        page=b'<h1 id="title">Synthetic</h1>'
        for name in ['index.html','ko/index.html','404.html','guide/one.html']:
            p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(page)
        raw=b'# Synthetic\n';(root/'README.md').write_bytes(raw)
        (out/'sources/en').mkdir(parents=True);(out/'sources/en/one.md').write_bytes(raw)
        for name in ['LICENSE.txt','web-notices.txt','web-dependencies.json']:(out/name).write_text('synthetic')
        c={'schema':site.SCHEMA,'source_commit':'a'*40,'working_tree':False,'pages':[{'source':'README.md','route':'/guide/one','copy':'sources/en/one.md','sha256':site.digest(raw)}]}
        (root/'.local/docs-site/catalogue.json').write_text(json.dumps(c));return out,c

    def test_output_rejects_missing_pages_extra_files_and_changed_copy(self):
        for kind in ['missing','extra','copy']:
            with self.subTest(kind=kind),tempfile.TemporaryDirectory() as d:
                root=Path(d);out,c=self.fixture(root);site.inventory(out,c,root)
                if kind=='missing':(out/'ko/index.html').unlink()
                elif kind=='extra':(out/'unexpected.txt').write_text('extra')
                else:(out/'sources/en/one.md').write_text('changed')
                with self.assertRaises(ValueError):site.inventory(out,c,root)

    def test_external_resources_and_broken_anchors_fail(self):
        for html in ['<script src="https://example.test/script.js"></script>','<a href="/docs-actions/guide/one#absent">x</a>']:
            with tempfile.TemporaryDirectory() as d:
                root=Path(d);out,c=self.fixture(root);(out/'index.html').write_text(html)
                with self.assertRaises(ValueError):site.inventory(out,c,root)

    def test_manifest_binds_clean_exact_commit_and_immutable_output(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out,c=self.fixture(root);site.verify(root,record=True)
            with patch.object(site,'git',side_effect=['a'*40,'']):site.verify(root,commit='a'*40)
            with self.assertRaises(ValueError):site.verify(root,commit='b'*40)
            with patch.object(site,'git',side_effect=['a'*40,' M README.md']),self.assertRaises(ValueError):site.verify(root,commit='a'*40)
            (out/'index.html').write_text('<h1>Changed</h1>')
            with self.assertRaises(ValueError):site.verify(root)

    def test_sources_cannot_change_after_preparation(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);site.verify(root,record=True);(root/'README.md').write_text('changed')
            with self.assertRaises(ValueError):site.verify(root)

    def test_docs_workflow_checks_before_main_only_same_commit_deployment(self):
        w=check_contract.load((ROOT/'.github/workflows/docs.yml').read_text())
        self.assertEqual(w['permissions'],{'contents':'read'})
        build=w['jobs']['docs-build'];deploy=w['jobs']['docs-deploy']
        self.assertEqual(build['permissions'],{'contents':'read'})
        self.assertEqual(deploy['needs'],'docs-build')
        self.assertEqual(deploy['uses'],'./.github/workflows/reusable-pages-deploy.yml')
        self.assertEqual(deploy['permissions'],{'pages':'write','id-token':'write'})
        self.assertIn("github.ref == 'refs/heads/main'",deploy['if'])
        self.assertIn("github.repository == 'novelKR/docs-actions'",deploy['if'])
        steps=build['steps'];runs=[s.get('run','') for s in steps]
        for command in ['python -B -m unittest discover -s tests -v','python -B scripts/check_contract.py','npm test --prefix docs-site','npm run build --prefix docs-site','python -B docs-site/scripts/site.py check']:
            self.assertIn(command,runs)
        upload=next(i for i,s in enumerate(steps) if s.get('uses','').startswith('actions/upload-pages-artifact@'))
        check=next(i for i,s in enumerate(steps) if s.get('run','').endswith('--commit "$GITHUB_SHA"'))
        self.assertLess(check,upload)
        self.assertEqual(steps[upload]['with']['path'],'.local/docs-site/dist/')
        self.assertEqual(steps[upload]['if'],deploy['if'])
        self.assertFalse((ROOT/'.github/workflows/docs-lock-prep.yml').exists())

    def test_public_markdown_is_download_only_and_vue_resolves_from_pinned_install(self):
        config=(ROOT/'docs-site/.vitepress/config.mts').read_text()
        self.assertIn("srcExclude: ['public/**']",config)
        self.assertIn('docs-site/node_modules/vue/server-renderer/index.mjs',config)
        self.assertIn("provider: 'local'",config)

if __name__=='__main__':unittest.main()
