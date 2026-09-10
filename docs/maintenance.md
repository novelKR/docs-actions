# Maintenance and consumer upgrades

[English](maintenance.md) | [한국어](maintenance.ko.md)

## Central changes

The public workflow interface remains v1. The [JSON contract](../contracts/pages-deploy-v1.json)
contains every input type/default/required flag, output, permission, event, scope,
forbidden capability, runtime and concurrency setting. The validator checks the
whole document against the supported interface and the executable YAML.
Unknown keys and duplicate YAML/JSON keys fail; CI cannot skip checks or ignore errors.

A normal `actions/deploy-pages` security update changes its full SHA in **both**
the workflow and `runtime.action` in the JSON contract. Review the actual upstream
commit and license before merging; a syntactically valid SHA is not proof of trust
or even existence. The allowlist still requires the official deploy-pages
repository and a single step without new permissions, commands or inputs.

Do not edit the historical workflow fixture to make an update pass. Historical
blob integrity tests are separate from current policy tests; runtime updates do
not require equality with old executable YAML. An interface/capability change
needs a separately reviewed contract decision, not an incidental dependency bump.
Dependabot PRs are proposals only; synchronize policy where needed and never
label bot activity as human approval. Existing dependency PRs can remain separate.

Protect central main with the `contracts` check and code-owner review. Protect
consumer branches and environments separately. No script here changes protection,
permissions, Pages settings or repository visibility during normal maintenance.

## Consumer SHA changes

Adopt only an actual full central commit SHA after reviewing its diff, license
scope and successful central main-push CI. Then open a consumer PR that updates
the literal workflow reference and any lock or current verification snapshot.
Verify the snapshot against the exact remote workflow bytes; never edit its hash
just to silence drift. Do not execute the historical AGPL fixture as a fallback.

Run that consumer's required checks, including source/artifact integrity and
publication boundaries. Its PR must not deploy. Merge and approve publication
according to its environment policy, then inspect the deployment and served build
manifest. Central CI alone does not verify a consumer's site or OIDC execution.
Changing the central main branch does not upgrade SHA-pinned consumers.

The old gateway migration script only understands the pre-merge PR #52 baseline;
it is not a pin-update tool and must not be run against current main. New consumers
use the caller example; ongoing consumers use reviewed pin-update PRs.

## Ordering and rollback

Use distinct concurrency groups for the whole main workflow and the deployment
job. Keep active main/deployment runs non-cancelling; PR checks can cancel obsolete
PR runs. Concurrency does not guarantee newest-commit-wins ordering and is not a
durable FIFO queue. Inspect older re-runs and pending approvals before publishing.

Reverting the central pin changes deployment code, not already served content.
Recover site content through the consumer's reviewed source/artifact process.
This workflow consumes only current-run artifacts: it does not fetch expired or
cross-run artifacts. Re-running an old main run is an intentional publication of
that run's artifact, subject to artifact availability and current environment rules.

## Verification limits

Run the commands in the [README](../README.md) before a PR. Checks cover negative
capabilities, complete machine contract consistency, preserved historical bytes,
MIT source headers, local documentation links and equal bilingual code examples.
Translation meaning, remote links, ownership and legal permission still need review.
PyYAML is version-pinned but not hash-locked; hash-locking its supported distributions
can be a separate dependency change. No live API calls belong in default tests.
