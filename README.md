# docs-actions

[English](README.md) | [한국어](README.ko.md)

Deployment-only GitHub Pages workflows for independently owned repositories.
Each consumer builds and verifies its own site; this repository supplies only
the final deployment job. It is not a documentation portal or credential broker.

The maintained implementation, documentation and examples use **MIT**. Historical
AGPL evidence is explicitly excluded; see [license scope](docs/licensing.md).
The gateway project's license and existing consumer pins are not changed here.

## Use from a consumer repository

First enable Pages with the GitHub Actions source, protect the publishing branch,
and restrict the consumer's `github-pages` environment to that branch. Require an
environment reviewer when publication needs human approval. A CODEOWNERS file
alone does not enforce these settings. Allow this public reusable workflow in
the consumer's Actions policy.

Keep these stages in the consumer's own workflow:

```text
PR -> read-only build and verification -> review artifact; no deployment
main -> build once -> verify source and file hashes -> Pages artifact
     -> required CI gate -> pinned central workflow -> consumer's Pages site
```

Upload with `actions/upload-pages-artifact` after validating the exact output
files, manifest source SHA, clean build provenance, and publication/license
boundaries. Pin the upload action to a reviewed full SHA. Use a unique artifact
name within the run, and keep its retention longer than the expected approval
wait. Builds and uploads need no Pages write permission. Do not rebuild in the
privileged deployment job or promote an untrusted PR artifact.

Add this **job fragment** beneath the caller's `jobs:` mapping, after its existing
build and required gate jobs. Replace the marker with a real full commit SHA
whose code, license scope and central CI you have reviewed. The marker is not an
existing tag or release, and this fragment is not a standalone workflow.

```yaml
# SPDX-License-Identifier: MIT
# Insert AFTER your repository-specific build and required gate jobs.
# Replace the explicit marker with a reviewed, real 40-character commit SHA.
# This is a job fragment, NOT a complete runnable workflow.
docs-pages:
  needs: ci-required
  if: >-
    (github.event_name == 'push' || github.event_name == 'workflow_dispatch') &&
    github.ref == 'refs/heads/main'
  permissions:
    pages: write
    id-token: write
  uses: novelKR/docs-actions/.github/workflows/reusable-pages-deploy.yml@<REVIEWED_FULL_COMMIT_SHA>
  with:
    artifact-name: github-pages
    publication-branch: main
```

The `ci-required` job must require successful build/publication checks; skipping
or failing them must block deployment. Grant only the calling deployment job
`pages: write` and `id-token: write`. Do not use `secrets: inherit`. Each consumer
retains its own toolchain, base path, notices, artifact checks and site settings.
See [maintenance and pin updates](docs/maintenance.md) before adopting a new SHA.

## Contract v1

[Machine-readable contract](contracts/pages-deploy-v1.json) ·
[Workflow](.github/workflows/reusable-pages-deploy.yml)

| Item | Value |
| --- | --- |
| `artifact-name` | Optional string; default `github-pages`; current caller run only |
| `publication-branch` | Optional string; default `main`; environment restrictions must match |
| `page-url` | Output returned by a successful official Pages deployment |
| Events | `push` or `workflow_dispatch` on the publication branch |
| Environment | Fixed `github-pages` in the caller repository |
| Permissions | `pages: write`, `id-token: write` on the deploy job |
| Execution | One full-SHA-pinned official `actions/deploy-pages` step |

No checkout, build command, package installation, PAT input, inherited application
secret, target-repository selector, cross-run artifact, preview or environment
override is provided. The artifact name is not proof of review: the caller owns
verification and approval. GitHub evaluates the reusable workflow in the caller's
repository context; central CI itself remains read-only.

Deployments share a repository-local `github-pages` concurrency group and do not
cancel an active deployment. This is **not newest-commit-wins ordering**. Preserve
the caller's main-run serialization; an intentionally re-run older main run may
publish old content. Do not reuse the deployment concurrency group for the whole
caller workflow. Cross-run artifact rollback is outside this contract.

## Development and verification

Python 3.11+ and Git are required for tests. The deployment job does not install
Python or this repository's dependencies.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_contract.py
```

The CI-only PyYAML dependency is version-pinned, not hash-locked. Tests check YAML,
negative capabilities, complete contract consistency, historical evidence,
license headers and bilingual examples. They do not prove upstream SHA existence,
legal ownership, human approval, GitHub OIDC behavior or a live deployment.

Normal development does **not** run the initial publisher or gateway migration.
Those baseline-specific tools are retained for historical recovery only; see
[initial publication history](docs/history.md). That document records the first
central CI and consumer deployment without treating it as a permanent health claim.

## License and contributions

Copying maintained code or examples requires preserving the MIT copyright and
permission notice. Invoking the workflow does not relicense a consumer's independent
code or documentation. Whole-repository copies must also retain the notices for
historical exceptions. Third-party Actions/dependencies keep their own licenses.
See [LICENSE](LICENSE), [license scope](docs/licensing.md) and
[PROVENANCE.json](PROVENANCE.json).

Submit only contributions you have authority to offer under the applicable file
license. Identify external sources and their terms. No copyright assignment,
commercial exception, CLA execution or legal approval is implied by CI.
See [repository instructions](AGENTS.md) and [security boundaries](SECURITY.md).

## Primary references

[Reusable workflow context and permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations) ·
[Pages artifact and deployment requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) ·
[MIT license](https://opensource.org/license/mit)
