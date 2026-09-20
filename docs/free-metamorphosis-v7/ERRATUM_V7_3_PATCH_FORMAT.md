# v7.3 erratum — exact Git patch header disclosure

**Status:** prospective disclosure-only repair before canonical Attempt 023 evaluation.

The generated v7 prompt previously required a "normal unified Git patch". The frozen patch parser accepts changed paths only from lines beginning with `diff --git a/`. The first A023 proposer therefore returned a patch that was valid for the standard `patch` utility but not admissible to the frozen v7 parser.

The rejection occurred during transcript verification, before the external evaluator entrypoint. No observation was spent and the campaign remains at **22 / 24**.

v7.3 changes only the generated proposer wording so the already-existing patch-format requirement is explicit:

`diff --git a/<path> b/<path>`

Unchanged from v7.2:
- frozen scorer and strategy weights;
- fitness policy;
- proposal context and research memory;
- external evaluator;
- patch parser and canonical runner;
- parent-selection rule;
- attempt and generation budgets.

Control validation passes on Python 3.11 and 3.13.

- v7.2 control head: `395e240a25c5e4ec30d9ac57d62a9ebbfff201b4`
- v7.3 repaired control head: `0d210c8ddfe0a42bcade819eed43c9fe079805a0`
- rejected patch: `b5c973e2c8854427d4e11590cf1f7366a26fb4d8a44a64749ee497ab7090fae6`
- rejected transcript: `f310970c8af77de27ccb104be8b7db86ffe8685077a6272dbe23f3f1b218b3d3`
- repaired A023 bundle: `8179676ad6309920ae2f9ace4dfbd3a284c3efea571f4afe3ba51d138611b1ae`
- repaired A023 prompt: `8ca60329516e3d9aac364fe19fdd7f7f3b81ebcdda4a83a17e934049d6e9edbf`
