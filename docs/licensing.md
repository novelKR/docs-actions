# License scope and transition

[English](licensing.md) | [한국어](licensing.ko.md)

## Maintained implementation

This revision offers the maintained docs-actions workflow, Python tools, tests,
documentation and examples under the [MIT license](../LICENSE), except for the
historical materials explicitly listed below. This is a repository-specific
license transition, not a relicensing of agent-response-gateway or GitHub Actions.
The MIT choice makes reuse of a small deployment component and caller examples
straightforward while retaining copyright, permission and warranty notices.

When copying substantial portions of the maintained implementation or examples,
include the MIT copyright and permission notice. Commercial use is permitted
under MIT; no separately purchased permission is required by this repository.
Invoking the deployment workflow does not impose MIT on independently authored
consumer code, documents or static output. Third-party code/assets in a site
still have their own requirements.

## Historical exceptions

| Material | Retained terms and purpose |
| --- | --- |
| [Original workflow fixture](../tests/fixtures/gateway-reusable.yml) | AGPL-3.0-only; inert source evidence, not a second executable workflow |
| [Fixture notice](../tests/fixtures/gateway-reusable.yml.license) | Accompanies the original fixture; must be retained when copying it |
| [Original provenance](../licensing/historical/PROVENANCE-v1.json) | Historical AGPL-3.0-only record, unchanged |
| [Original AGPL text](../licensing/historical/AGPL-3.0.txt) | Unchanged license document; its own verbatim-copy notice remains in force |

Whole-repository archives contain these exceptions and are **not MIT-only
archives**. Keep their notices with them. Consumers calling only the maintained
workflow do not execute or ship this historical fixture. A consumer that chooses
to copy a fixture must retain the terms attached to that particular copy.
The old fixture remains AGPL even though the maintained implementation is MIT.

[PROVENANCE.json](../PROVENANCE.json) separates current licensing from extraction
history and records exact historical Git blob hashes. Checks preserve those
bytes independently from current deployment policy. A source hash is integrity
evidence, not proof of copyright ownership or permission to relicense.

## Earlier versions and rights review

Initial central commit `1191cea41d88f07497be04407b3c949ca8361733` was published as
AGPL-3.0-only. This transition does not rewrite history, revoke prior AGPL grants,
or silently replace the license of consumers still pinned to that revision.
To adopt this maintained MIT revision, consumers review the actual merged SHA,
its scope and CI, then update their own pin, lock and any copied current snapshot.
Do not advertise the old SHA as an MIT release.

The transition is prepared at the maintainer's direction. Before merging it,
confirm authority to offer the maintained code, including the extracted portion,
under MIT and review any third-party contribution terms. Repository administration
access, source authorship metadata and passing tests are not a legal clearance.
No signed assignment, CLA or third-party consent is asserted by this repository.
Historical evidence and third-party license documents are excluded from the MIT
grant rather than relabeled. The AGPL gateway project remains independently licensed.

## Third-party tools and contributions

Official GitHub Actions are referenced at full SHAs, not vendored. For example,
[the current deploy-pages license](https://github.com/actions/deploy-pages/blob/d6db90164ac5ed86f2b6aed7e0febac5b3c0c03e/LICENSE)
is MIT; referenced software retains its own copyright and notices. CI-only
PyYAML and its distribution retain their own license. An update needs source and
license review; this file is not a license grant for external software.

Contribute only code you have authority to provide under the destination file's
terms. Identify copied material and retain required notices. Nothing here
requires assignment of copyright or claims that a CLA has been signed.
For the actual permission text, use [LICENSE](../LICENSE); this guide adds no
restrictions to it and is not a legal opinion about arbitrary combined products.

References: [MIT](https://opensource.org/license/mit) ·
[AGPL v3](https://www.gnu.org/licenses/agpl-3.0.html).
