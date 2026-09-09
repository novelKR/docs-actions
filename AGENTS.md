# Repository instructions

This repository owns a narrow, caller-owned GitHub Pages deployment contract.
Preserve the separate build/deploy privilege boundary. Do not add arbitrary
commands, source checkout, dependency installation, PATs, inherited secrets,
remote-repository selection, cross-run artifacts or environment overrides to the
privileged reusable workflow. Do not create Pages sites or change protections.

Keep all third-party Actions on reviewed full commit SHAs. Updates are PRs,
never automatic consumer migrations. Do not invent release SHAs or live URLs.
Keep README.md and README.ko.md consistent. Preserve LICENSE and PROVENANCE.json.
Do not copy gateway history, private records or user credentials here.

Use Python 3.11+ and the pinned CI-only requirements. Run:

    python -B -m unittest discover -s tests -v
    python -B scripts/check_contract.py

Bootstrap and migration tools default to no writes. Real GitHub operations must
require --apply, fail on unexpected owner/source/visibility, and never force-push.
Unit tests must mock GitHub; they do not prove hosted CI, OIDC or live deployment.
Do not merge or publish a release merely because local tests pass.
