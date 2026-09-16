# Build Instructions

## Prerequisites

- Python 3.10 or later
- pip

## Setup

Create a virtual environment and install the package with the development extras:

```sh
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

For builds and releases, also install the build extras:

```sh
pip install -e ".[build]"
```

## Running tests

```sh
pytest
```

With coverage:

```sh
pytest --cov=instapaper --cov-report=term-missing
```

## Linting and formatting

```sh
ruff check .
ruff format --check .
```

Use `ruff format .` to apply formatting.

## Type checking

```sh
mypy instapaper tests examples
```

## Building

```sh
python -m build
twine check dist/*
```

This writes a source distribution and a wheel to `dist/`.

## Releasing

Releases are published to PyPI by GitHub Actions when a version tag is pushed.

1. Update `__version__` in `instapaper/__init__.py`.
2. Move the changes under a dated version heading in `CHANGELOG.md`.
3. Commit, then tag and push:

   ```sh
   git tag v0.1.0
   git push origin main v0.1.0
   ```

The `release` workflow checks that the tag matches `__version__`, builds the package, and publishes it.

### One-time PyPI setup

The release workflow uses PyPI trusted publishing, so no API token is stored in GitHub. Before the first release:

1. Sign in to PyPI with the Instapaper account.
2. Go to **Your projects > Publishing** (for a project that doesn't exist yet, use **Add a new pending publisher**).
3. Add a GitHub publisher with:
   - PyPI project name: `instapaper-api`
   - Owner: `Instapaper`
   - Repository: `instapaper-api-python`
   - Workflow: `release.yml`
   - Environment: `pypi`
4. In the GitHub repository settings, create an environment named `pypi`. Adding required reviewers there makes each release wait for approval.

### Publishing manually

If you need to publish without the workflow:

```sh
python -m build
twine upload dist/*
```
