# Documentation site operations

[English](site.md) | [한국어](site.ko.md)

The site builds this repository's selected English and Korean Markdown with
VitePress. Documents and build tools remain local to this consumer; publication
uses the same reusable deployment contract offered to other repositories.

## Build and preview

Use Node 24.21.0, npm 11.19.0 and Python 3.11 or later. The committed npm lock
and original web notices are verified during the build. Use the pinned Node
binary on PATH; set DOCS_PYTHON when the Python executable has another name.

```sh
python3.14 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_contract.py
npm ci --prefix docs-site --ignore-scripts
npm test --prefix docs-site
npm run build --prefix docs-site
python -B docs-site/scripts/site.py check
python -B docs-site/scripts/site.py preview
```

The preview serves verified files only at http://127.0.0.1:43141/docs-actions/.
It has no rebuild or hot reload. Rebuild after editing sources. Do not expose a
development server as the public site. Generated files stay under .local/.

## Sources and user interface

[pages.json](../docs-site/pages.json) selects five paired guides. Both languages
have navigation, local search, source links and original Markdown copying.
The browser fetches the current page's selected Markdown for copying; clipboard
permission failure is reported. Search uses the browser's local index.
The site is published under /docs-actions/ and /docs-actions/ko/.

## Publication and approval

The Documentation site workflow runs contract and site checks on PRs with
read-only permissions and retains a review artifact. A main push or manual main
run additionally requires an exact source commit and a clean checkout before
packaging the same verified directory. Its deployment job calls the local
reusable workflow from that same commit, with pages: write and id-token: write.
The reusable workflow does not call the documentation workflow again.

Before the first deployment, configure this repository's Pages source as GitHub
Actions. Restrict the github-pages environment to the main branch and choose the
required reviewer policy. Reviewers authorize that deployment run, not future
runs. Keep contracts and docs-build as required PR checks after their first
successful runs. These settings are administrative operations, not performed
by the documentation build.

After approval, verify the actual URL, both languages and build-manifest.json.
Compare its source_commit with the deployed commit and its file hashes with the
same CI run's review artifact. CI success alone is not proof of live publication.
An older main rerun can publish older content; see [maintenance](maintenance.md).

## Source and dependency notices

The site implementation is independently maintained under MIT; architectural
reference and build versions are recorded in [site provenance](../docs-site/PROVENANCE.json).
[Notice policy](../docs-site/licensing/policy.json) pins the original notices
for shipped client packages and embedded icons. The generated site includes
LICENSE.txt, web-notices.txt and web-dependencies.json. Do not stamp changed
notice hashes without reviewing the corresponding sources and terms.
The whole repository also retains historical AGPL exceptions described in
[license scope](licensing.md); those are not bundled as site implementation.

## Development dependency advisories

The pinned VitePress 1.6.4 graph currently reports npm audit advisories for its
Vite and esbuild development-server dependencies. The supported workflow only
builds static files and previews them with the verified Python server; it does
not start the Vite or esbuild development server. Do not substitute an exposed
Vite development server for that preview. This restriction is not a dependency
patch: review a compatible toolchain upgrade separately and keep the warning
visible in dependency review. See the [Vite advisory](https://github.com/vitejs/vite/security/advisories/GHSA-fx2h-pf6j-xcff)
and [esbuild advisory](https://github.com/evanw/esbuild/security/advisories/GHSA-67mh-4wv8-2f99).
