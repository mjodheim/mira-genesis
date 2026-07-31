# Pull-request validation

This branch exists solely to run the frozen M013b tests and evaluation on GitHub Actions for an auditable commit. No protocol parameter is changed here.

Rerun reason: the previous job stopped during test collection because NumPy was absent from the runner. The workflow now installs the declared runtime dependency; no scientific code or threshold changed.
