FROM python:3.11-slim

# Install git for repository operations
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the package definition first for dependency caching
COPY pyproject.toml README.md ./
COPY mira_core/ mira_core/
COPY metamorphosis/ metamorphosis/
COPY scripts/ scripts/
COPY tests/ tests/

# Install the package
RUN pip install --no-cache-dir -e ".[dev]"

# Default command: run the complete test suite
CMD ["python", "-m", "pytest", "tests/", "-x", "-v"]