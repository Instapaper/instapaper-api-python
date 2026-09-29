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

The release workflow publishes to TestPyPI when run manually and publishes to PyPI when a version tag is pushed.

1. Update `__version__` in `instapaper/__init__.py`.
2. Move the changes under a dated version heading in `CHANGELOG.md`.
3. Commit and push `main`.
4. In GitHub Actions, open the **Release** workflow and choose **Run workflow** on `main`. This publishes the package to TestPyPI.
5. Install the TestPyPI build in a clean environment and verify it:

   ```sh
   python -m venv /tmp/instapaper-api-test
   /tmp/instapaper-api-test/bin/pip install \
     --index-url https://test.pypi.org/simple/ \
     --no-deps \
     instapaper-api==1.0.0
   /tmp/instapaper-api-test/bin/python -c \
     "import instapaper; print(instapaper.__version__)"
   ```

6. Tag the tested commit and push the tag:

   ```sh
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```

The tagged run checks that the tag matches `__version__`, rebuilds the package, and publishes it to PyPI.

### One-time trusted publishing setup

The release workflow uses trusted publishing, so no API token is stored in GitHub. PyPI and TestPyPI are separate services and each needs its own account and publisher configuration.

1. Sign in to TestPyPI and go to **Publishing**, then add a pending GitHub publisher with:
   - PyPI project name: `instapaper-api`
   - Owner: `Instapaper`
   - Repository: `instapaper-api-python`
   - Workflow: `release.yml`
   - Environment: `testpypi`
2. In the GitHub repository settings, create an environment named `testpypi`.
3. Sign in to PyPI and go to **Publishing**, then add a pending GitHub publisher with the same project, owner, repository, and workflow values, but with:
   - Environment: `pypi`
4. In the GitHub repository settings, create an environment named `pypi`. Add required reviewers so production releases wait for approval. TestPyPI generally does not need required reviewers.

### Publishing manually

If you need to publish without the workflow:

```sh
python -m build
twine upload dist/*
```
