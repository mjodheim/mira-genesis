# Pull-request validation

This branch exists solely to run the frozen M013b tests and evaluation on GitHub Actions for an auditable commit. No protocol parameter is changed here.

Rerun history:

1. NumPy was missing during test collection.
2. Torch was then found missing because the historical core imports it globally.
3. The workflow now installs the repository runtime dependencies. No scientific code, seed, threshold or budget changed.
