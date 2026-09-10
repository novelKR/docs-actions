# Initial publication and historical tools

[English](history.md) | [한국어](history.ko.md)

## Recorded first integration

These are dated observations, not a live health dashboard. On 2026-09-10 (KST),
central commit `1191cea41d88f07497be04407b3c949ca8361733` passed
[central CI](https://github.com/novelKR/docs-actions/actions/runs/34385729100).
[Gateway PR #52](https://github.com/novelKR/agent-response-gateway/pull/52) was
merged at `653ce577c6a82280a88829d9bc55aa2058b36891`, and its
[deployment job](https://github.com/novelKR/agent-response-gateway/actions/runs/34432954753/job/102732854728)
reported success using that central SHA. This records an Actions outcome, not
complete browser testing of every page. That central revision used AGPL-3.0-only.

The [original provenance record](../licensing/historical/PROVENANCE-v1.json) and
[original fixture](../tests/fixtures/gateway-reusable.yml) preserve the extraction
from gateway commit `41e1417a84ae7785e1450d2d35240fe0797c96bf` without importing
its Git history. Operational status is intentionally not in the reusable contract.

## Historical commands, not the current onboarding path

Use [README](../README.md) for normal consumers and [maintenance](maintenance.md)
for pin upgrades. The commands below document the old tools; they must not be
copied wholesale into a terminal for an existing repository.

```text
python -B bootstrap/publish.py
python -B bootstrap/publish.py --apply
python -B bootstrap/publish.py --apply --existing-empty
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --central-commit <REVIEWED_FULL_COMMIT_SHA>
python -B scripts/migrate_gateway.py --gateway /path/to/agent-response-gateway --central-commit <REVIEWED_FULL_COMMIT_SHA> --apply
```

The publisher's default is an offline dry run. Only `--apply` performs writes,
using the user's GitHub CLI session authenticated as novelKR and the configured
Git author identity. It creates only a new public docs-actions repository with
an independent initial commit. `--existing-empty` requires a public repository
without refs. It never changes visibility, force-pushes, deletes a repository,
activates Pages or changes protections. On a partial failure, retain the local
`.local/initial-repository` for inspection; do not erase evidence and blindly retry.
This is not a way to update the existing central repository.

The gateway tool expects a clean local `codex/docs-pages-deployment` branch and
exact original file blob hashes. It verifies remote workflow bytes and exact
central main-push/`contracts` CI success, then prints a patch by default. `--apply`
changes the local checkout only and runs focused tests; it never commits, pushes,
merges or deploys. The old branch baseline is no longer a normal operating state.
Refusal against changed/merged sources is intentional; do not bypass its hashes.

The tools and their offline tests remain maintained under MIT in this revision;
the unchanged historical fixture and license evidence retain their exceptions.
The [selected file inventory](../bootstrap/source-files.json) includes those
notices. No credentials, generated sites or private histories are part of it.
