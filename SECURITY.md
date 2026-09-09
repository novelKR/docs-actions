# Security boundaries

The central repository is a code-distribution point, not a credential broker.
Its compromise must not silently change SHA-pinned consumers. Review both central
changes and consumer pin updates; a full SHA does not certify trustworthy code.

The caller is responsible for protecting source branches, validating source and
artifacts, binding the publishing commit, selecting trustworthy dependencies,
and configuring environment approvals. The artifact's existence or name is not
an attestation or proof of human review. Keep build jobs unprivileged.

Never add a build command, arbitrary script, checkout, external token, inherited
application secrets, target-repository selector, cross-run artifact selector,
preview mode, or environment-name override to the deployment-only contract.
Never change a public site's deployment permissions in a PR validation job.

Bootstrap needs user-side account management authority, but deployment does not.
Bootstrap and migration default to no writes. They cannot make a missing server
permission available. Keep the user's GitHub CLI session out of source, artifacts
and logs. No token input or token serialization is provided.

Source-contract tests cannot simulate GitHub's authorization service, OIDC claims,
protected environments or actual CDN publication. Test those after approved
publication and distinguish the result from offline tests. Do not put sensitive
vulnerability details into a public issue or a generated log.
