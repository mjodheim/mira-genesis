# Contributing to Mira Genesis

Thank you for contributing. Mira Genesis treats provenance, negative results and experimental
boundaries as part of the research output, so contribution history must remain auditable.

## Licence of contributions

By submitting a contribution, you agree to license material you own under the licence applicable
to that part of the repository:

- software contributions under `AGPL-3.0-only`;
- non-software documentation and research records under `CC-BY-4.0`.

You retain copyright in contributions you own. You must not submit material that you cannot
license on these terms. Third-party material must carry complete origin and licence information.

## Developer Certificate of Origin

Every commit must be signed off under the [Developer Certificate of Origin](DCO). Add a sign-off
with:

```text
git commit --signoff
```

The resulting commit message must contain a `Signed-off-by:` line matching a contributor identity
that you are authorised to use. The sign-off certifies the complete DCO; it is not a copyright
assignment.

## Authorship and AI assistance

- Preserve existing copyright, licence, citation and provenance records.
- Describe material changes accurately and do not claim authorship of unchanged upstream work.
- Disclose substantial use of generative tools when it affects the provenance of code, evidence,
  analysis or prose.
- Confirm that submitted AI-assisted material can be licensed under the applicable project terms.
- Do not present a fork or derivative as the official Mira Genesis project.

## Scientific changes

Changes must preserve frozen and canonical artifacts. A negative result must not be deleted or
rewritten as a success. New claims require tests, explicit authority boundaries and reproducible
evidence appropriate to their scope.

Before opening a pull request, run:

```text
pytest -q
python scripts/check_repository_integrity.py
```

Pull requests should explain the changed claim or behaviour, the relevant validation and any
effect on frozen or canonical evidence.
