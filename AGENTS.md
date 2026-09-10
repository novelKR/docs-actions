# Repository instructions

This repository owns a narrow, caller-owned Pages deployment contract. Keep
builds and publication checks in consumers. The privileged workflow must not
checkout source, install dependencies, execute arbitrary commands, accept PATs,
inherit application secrets, select another repository/run, or override the
fixed github-pages environment. Do not change live sites or protections.

Maintained code/docs/examples use MIT. Historical exceptions are listed in
PROVENANCE.json and docs/licensing.md; preserve their exact bytes and notices.
License changes require explicit maintainer direction and rights review before
merge. Hashes do not establish ownership. Never relicense third-party code by
changing a header. Preserve previous grants and upstream attribution.

Keep dependency updates on reviewed full SHAs. A change to the deploy action
must update the workflow and runtime action in contracts/pages-deploy-v1.json
in the same PR, not rewrite historical fixtures. The contract validator checks
capabilities; no test may claim that an arbitrary SHA is reviewed or exists.
Keep English/Korean documents and examples consistent. Initial bootstrap and
gateway migration are historical, baseline-specific tools, not upgrade paths.

Use Python 3.11+ and requirements-ci.txt. Run:

    python -B -m unittest discover -s tests -v
    python -B scripts/check_contract.py
    python -B bootstrap/publish.py

The last command is a local dry run, not a request to create a repository.
All live mutations require --apply; never force-push, auto-merge, auto-migrate
consumers, or invent source/release SHAs. Mock network calls in unit tests.
Source-contract tests do not prove hosted CI, OIDC, legal approval or a live
site. Preserve unrelated changes and existing dependency-update PRs.

For documentation-site changes, use Node 24.21.0 and the committed npm lock.
Run npm ci, npm test and npm run build under docs-site, then run
`python -B docs-site/scripts/site.py check`. Preview only through the verified
loopback Python server. Do not start a Vite or esbuild development server.
