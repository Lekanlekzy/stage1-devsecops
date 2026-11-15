# Regression consumer fixture

This directory is a small application-repository fixture used to exercise the
central `workflow_call` contract. The active caller is
`.github/workflows/reusable-app-ci-regression.yml` at the repository root. It
calls the reusable workflow from the same commit, so a pull request that changes
`reusable-app-ci.yml` tests that exact revision against this Python project.

The regression caller explicitly targets `Lekanlekzy_stage1-devsecops`; it does
not need a project-key Actions variable. Configure the central repository's
existing `SONAR_TOKEN` Actions secret with permission to analyze that project.
The caller passes the same secret name; no separate regression token is required.

The Sonar organization is fixed to `lekanlekzy`. The reusable workflow does not
automatically expose this repository's token to calls from application
repositories. Each external caller must explicitly pass a `SONAR_TOKEN` secret
available to its own repository, with permission to analyze the target project.

The regression caller runs on pull requests targeting `main` and manual dispatch.
Fork pull requests and Dependabot pull requests skip the secret-backed caller.
Main-protection static validation is intentionally disabled for now. The
reusable workflow's mandatory Sonar gate remains fail-closed for normal
application callers.

The fixture's `requirements-dev.txt` exposes its direct dev dependencies to the
OSV scanner and must match `pyproject.toml`. The scanner needs a supported
dependency manifest; this release does not extract these dependencies from
`pyproject.toml` alone. Scanner findings and missing package sources fail the gate.

## Python checks and coverage

From the repository root in PowerShell:

```powershell
Set-Location tests/consumer-repo/python-app
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov --cov-report=xml:coverage.xml
```

The `[dev]` extra includes pytest, pytest-cov 7.1.0, and Ruff. Coverage uses
`source = ["src"]`, `relative_files = true`, and `branch = true` in `pyproject.toml`.
CI uploads `coverage.xml` from the build-and-test job and restores it into the
same application directory in the isolated Sonar job. The central workflow
supplies `sonar.python.coverage.reportPaths=coverage.xml` on the scanner command
line; the fixture repeats it in `sonar-project.properties` for standalone scans.
Sonar imports the report and does not generate coverage itself. Generated
coverage files are local build output and do not belong in Git.

Gitleaks scans full history with the default rules and no project-ID exception.
The Action and full-history scan are advisory with redacted output; findings
and scan errors continue CI. Review the native Action summary and scan logs.
Checkout and central-configuration errors still fail the job.

## Container App sample

The Python fixture also serves a small HTTP application from its Dockerfile.
It listens on 0.0.0.0:8080, serves a home page at /, and exposes /healthz as
JSON with status "ok" and the APP_REVISION supplied at image build time. The
container runs as a non-root user and has no third-party runtime dependencies.

The regression caller builds and vulnerability-scans this image for its
eligible pull requests and manual runs. It sets run_container_checks to true
and publish_image to false, so it never pushes an image or deploys to Azure.
The regression run is skipped for fork and Dependabot pull requests because it
uses the Sonar secret.

To try the image locally from PowerShell, use two terminals:

    Set-Location tests/consumer-repo/python-app
    docker build --build-arg APP_REVISION=local -t stage1-python-consumer:local .

In the first terminal:

    docker run --rm -p 8080:8080 stage1-python-consumer:local

In the second terminal:

    Invoke-RestMethod http://localhost:8080/healthz
    Invoke-WebRequest http://localhost:8080/

For an application repository that publishes from its default branch and
deploys to Azure Container Apps, see
examples/caller-workflows/python-container-ci-cd.yml.example. Provision an
existing Container App with external HTTPS ingress targeting port 8080, and
configure the caller's Azure OIDC variables and Sonar settings before using
that example. The reusable CD workflow deploys the scanned GHCR digest and
verifies the health response and commit revision.
