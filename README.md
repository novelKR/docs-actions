# docs-actions

[English](README.md) | [한국어](README.ko.md)

Reusable, caller-owned GitHub Pages deployments. The intended public repository
is `novelKR/docs-actions`. This source package does not itself establish that the
remote repository, a release, or a Pages deployment exists.

## Boundary

Each consumer owns its documentation sources, framework, builds, integrity and
publication checks, Pages artifacts, production site and `github-pages` environment.
This repository owns **only the deployment implementation and its tests**.
It is not an aggregate documentation portal, a cross-repository administrator,
or a central holder of consumer credentials.

```text
Consumer PR -> read-only build/check -> review artifact; no deployment
Consumer main -> build once -> verify -> Pages artifact -> required CI gate
                                                     -> reusable workflow
                                                        from this repository
                                                     -> CONSUMER's Pages site
```

The reusable workflow does not check out code, run build commands, install
packages, inherit application secrets, accept a PAT, select another repository,
read an artifact from another run, or override the deployment environment.
It uses the caller's token and repository context. Central CI has only
`contents: read`; publishing permissions belong to each consumer's deploy job.

## Deployment contract v1

See [the workflow](.github/workflows/reusable-pages-deploy.yml) and
[the machine-readable contract](contracts/pages-deploy-v1.json).

| Item | Contract |
| --- | --- |
| `artifact-name` | String; default `github-pages`; already uploaded in the caller's current run |
| `publication-branch` | String; default `main`; caller must also restrict its environment to this branch |
| `page-url` | Output reported by a successful official Pages deployment |
| Permissions | `pages: write` and `id-token: write`, on the caller's deploy job only |
| Accepted events | `push` or `workflow_dispatch` on the publication branch |
| Environment | Fixed `github-pages`, in the caller repository |
| Build and checks | Entirely the caller's responsibility, completed before calling |
| Runtime | One SHA-pinned `actions/deploy-pages` step, GitHub-hosted runner |

An artifact's name does not prove it was reviewed. The consumer must bind its
build manifest to the intended commit, verify file hashes and publication
boundaries, and call only after its required gate. Enforce human approval in
that consumer's environment when needed. Do not use `pull_request_target` or
promote an untrusted PR artifact with this contract.

The repository-local deployment concurrency group prevents simultaneous Pages
deployments; it does not implement newest-commit-wins ordering. Preserve the
consumer's main-run serialization. Deliberately re-running an older main run
can publish old contents. Cross-run artifact rollback is not implemented here.

## First publication of this infrastructure repository

Requires Python 3.11+, Git, a configured global Git author identity, and a GitHub
CLI authenticated to `github.com` as `novelKR`, with permission to create the
repository and push workflow files. Do not paste tokens into source or chat.
The deployment workflow itself needs none of these bootstrap credentials.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-ci.txt
python -B -m unittest discover -s tests -v
python -B scripts/check_contract.py
python -B bootstrap/publish.py
```

The last command is a **local dry run**: no GitHub requests or remote writes.
After reviewing the selected files, explicitly publish:

```sh
python -B bootstrap/publish.py --apply
```

This creates the new **public** `novelKR/docs-actions`, makes an independent
initial commit from the selected source files, and pushes `main` without force.
No gateway history is imported. Git identity comes from your Git configuration;
the tool does not invent a person or email. It does not change global Git config.
The file inventory excludes `.git`, `.local`, private files and installed packages.
It refuses symlinks and unsafe paths.

To use a repository you have explicitly created but left completely empty:

```sh
python -B bootstrap/publish.py --apply --existing-empty
```

A private or nonempty repository is rejected; visibility is never changed.
A partial failure preserves `.local/initial-repository` for inspection and
manual recovery. It does not delete a newly created repository or retry writes
blindly. Do not erase the preserved directory until the remote state is understood.

Inspect the new central `CI` run and its `contracts` job. The initial source push
is not a CI pass, tag, release or production deployment. Bootstrap records the
actual source SHA in `.local/published.json`; it never fabricates a release SHA.

## Connect the first consumer

The prepared migration targets the existing `agent-response-gateway` PR #52
branch `codex/docs-pages-deployment` as inspected at commit `41e1417a84ae7785e1450d2d35240fe0797c96bf`.
It does **not** enroll any other repository.

After central CI succeeds, with that PR branch checked out locally and clean:

```sh
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway
```

This reads the actual central SHA from the bootstrap record, verifies the public
remote workflow's bytes, verifies its exact main-push CI and `contracts` result,
checks the gateway origin/branch and known source blob hashes, and prints a patch.
No local or remote gateway changes occur without `--apply`.

```sh
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --apply
```

The applied patch changes the caller to a literal full central SHA, removes its
local executable copy, records a consumer lock and an inert verified workflow
snapshot, and adapts the existing workflow-contract tests. The snapshot is an
offline verification fixture, not a second executable workflow. The focused
gateway tests are run after local application. No commits, pushes or merges are
automatic. Review the diff and run the full gateway checks before updating PR #52.
Changed gateway source blobs fail explicitly instead of overwriting newer work.
If PR #52 has since merged or changed, rebase/review the migration before use.

An explicit SHA can replace the bootstrap record with
`--central-commit <REVIEWED_FULL_COMMIT_SHA>`. Mutable refs are rejected.
Neither an absent remote repository nor a still-running/failed central CI is
accepted, even if the caller's deployment job would be skipped on a PR.

## Additional consumers and upgrades

Use the [caller job fragment](examples/caller-job.yml.example) only after the
repository-specific builder has uploaded its verified Pages artifact and the
required gate has succeeded. The fragment is not a complete workflow and its
SHA marker is deliberately not a fabricated commit.

Consumers retain their own VitePress, MkDocs or other build logic, base path,
legal notices and integrity checks. They need no PAT or central repository write
access for deployment. A public caller must be permitted to use this public
reusable workflow by its Actions policy.

Pin the central workflow to a reviewed full commit SHA. Central changes therefore
do **not** silently propagate to every consumer. Adopt each new SHA through a
consumer PR and its checks; revert that pin through a PR when necessary.
`v1` names the interface contract, not an assertion that a Git tag exists.
Dependabot proposes updates to this repository's Actions and CI-only parser;
it does not auto-merge, grant approval or upgrade consumers automatically.

Before using production deployment, each consumer must enable Pages with the
GitHub Actions source and restrict `github-pages` to its publication branch.
Configure required reviewers when approval is needed. Protect this repository's
`main` with required `contracts` checks and code-owner review. The included
[CODEOWNERS](.github/CODEOWNERS) file alone does not enable protection rules.
No tool in this source package changes those administrative settings.

## Validation and provenance

Central tests parse the YAML and exercise permission, event, artifact, pinning,
bootstrap and migration failure boundaries. These are **offline source-contract
checks**, not a replacement for GitHub's workflow-schema validation, cross-repo
OIDC validation or an actual Pages deployment. No default test makes live calls.
`PyYAML==6.0.3` is a version-pinned development dependency, not a runtime dependency
of deployment and not a hash-locked dependency set.

The extracted workflow's executable YAML mapping matches its original gateway
version. [PROVENANCE.json](PROVENANCE.json) records the source commit and blobs.
[LICENSE](LICENSE) is the exact original AGPL-3.0 text; project code remains
AGPL-3.0-only. No additional commercial permission or legal approval is implied.
GitHub Actions are referenced, not vendored. No font assets or generated websites
are included.

See [repository instructions](AGENTS.md) and [security boundaries](SECURITY.md).

## Primary references

- [Reusable workflow access, context and permissions](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations)
- [GitHub Pages artifact/deployment requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [GitHub CLI API calls](https://cli.github.com/manual/gh_api)
- [Repository creation API](https://docs.github.com/en/rest/repos/repos#create-a-repository-for-the-authenticated-user)
- [Pinned CI parser](https://pypi.org/project/PyYAML/6.0.3/)
