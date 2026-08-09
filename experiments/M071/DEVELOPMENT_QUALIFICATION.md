# M071 development qualification

Exact evidence commit `0875fa72d724db2af8a7b10b33c876a0e047576d` was qualified by the first
GitHub pull-request run without rerun:

- CI run `31332620871`;
- Python 3.11: 1,226 passed, 1 skipped in 1,240.29 seconds;
- Python 3.13: 1,226 passed, 1 skipped in 1,145.84 seconds;
- repository integrity passed;
- attribution run `31332620902` passed;
- every job completed on attempt 1.

The different local/CI skip counts are platform-expected: local Windows skipped two symlink tests,
while Linux skipped one optional Docker integration. No scientific trial was rerun.

This qualification verifies the committed M071 evidence and repository integration. It does not
upgrade the public 1/2 external result into a canonical, private, independently reproduced,
general-agent or AGI result.
