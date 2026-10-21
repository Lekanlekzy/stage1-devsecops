# Enterprise DevSecOps Platform

## What this repository does

This is the source repository for a reusable GitHub Actions CI platform. It is not an application repository: application teams keep their own code, tests, dependency manifests, and SonarQube project configuration, then call a versioned workflow from this repository through a thin caller workflow.

The central workflow is [`.github/workflows/reusable-app-ci.yml`](.github/workflows/reusable-app-ci.yml). It supports fixed profiles for Java with Maven, Java with Gradle, Python, Node.js/TypeScript, .NET/C#, and Go. Each profile runs its documented format, lint, and test checks.

Every caller also runs the mandatory SonarQube Cloud Quality Gate, full-history Gitleaks scan, and OSV dependency scan. Container build and Trivy scanning are optional. GHCR publication is separately gated, disabled by default, and limited to a protected `non-production` environment.

## How the reusable workflow is organized

- **Validation** checks the caller's inputs and required files.
- **Build and test** resolves profile build paths, installs the selected toolchain, and runs that profile's formatting, lint, and unit-test commands. Build output follows the selected profile's conventions.
- **Secret and dependency scans** run as separate jobs. Gitleaks fetches full Git history; OSV fails when it finds a vulnerable dependency.
- **SonarQube Cloud** runs in its own job. Only this job receives the project-scoped `SONAR_TOKEN`. For Java, compiled bytecode is passed from the build-and-test job as a short-lived artifact so the Sonar job does not run application build scripts with the token.
- **Container build and scan** runs only when requested. It adds OCI labels for the source repository, commit, title, build time, and workflow run, then scans locally without package-write credentials. If publication is requested, a separate publisher verifies and publishes that same image after the required gates pass.
- **Stage 1 Required Checks** writes a table of expected and actual job results to the GitHub run summary before reporting the aggregate result. It fails if a mandatory gate fails, or if an optional job that was requested does not succeed. Disabled optional jobs appear as `Not requested` only when they were skipped.

GitHub-hosted jobs use separate, short-lived runners with separate workspaces. A job that needs caller files checks out the repository for itself; one job's checkout is not shared with another. Checkouts disable persisted credentials so the checkout token is not left in Git configuration for later commands.

## Workflows in this repository

- [`reusable-app-ci.yml`](.github/workflows/reusable-app-ci.yml) is callable only through `workflow_call`; it does not start itself.
- [`reusable-app-ci-regression.yml`](.github/workflows/reusable-app-ci-regression.yml) calls the central workflow against the Python fixture in [`tests/consumer-repo`](tests/consumer-repo/). It runs for pull requests and pushes to `main`, and supports manual dispatch. It skips fork and Dependabot pull requests because those runs do not receive the regression Sonar secret.
- [`main-protection.yml.disabled`](.github/workflows/main-protection.yml.disabled) is intentionally disabled for now. Its retained definition runs the local contract tests, actionlint, and zizmor when restored to a `.yml` filename. GitHub rulesets or classic branch protection separately enforce merge rules; disabling this file does not change remote repository settings.

For the secret-backed regression, configure the `SONAR_REGRESSION_ORGANIZATION` and `SONAR_REGRESSION_PROJECT_KEY` Actions variables and a project-scoped `SONAR_REGRESSION_TOKEN` secret. Never use `pull_request_target` to work around fork-secret restrictions.

## Local checks

Run the dependency-free repository contract suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

Run the Python fixture's unit test from PowerShell:

```powershell
Set-Location tests/consumer-repo/python-app
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s test -v
```

Local tests do not verify GitHub Actions execution, SonarQube Cloud configuration or Quality Gate behavior, scanner service results, GHCR permissions, observed status-check names, or repository branch rules. The central workflow's integration behavior must be checked in a configured GitHub caller repository.

## Project guide

- [Reusable workflow contract](docs/stage-1/reusable-workflow-contract.md)
- [Security tools and dependency updates](docs/stage-1/security-tools-and-dependencies.md)
- [Verified action pins](docs/stage-1/action-pins.md)
- [Default-branch protection runbook](docs/stage-1/default-branch-protection.md)
- [Acceptance criteria](docs/stage-1/acceptance-criteria.md)
- [Architecture decisions](docs/decisions/)
- [Four-stage roadmap](docs/architecture/four-stage-roadmap.md)
