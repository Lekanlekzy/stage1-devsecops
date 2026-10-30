# Enterprise DevSecOps Platform

## What this repository does

This is the source repository for a reusable GitHub Actions CI/CD platform. Application teams keep their own code, tests, dependency manifests, and SonarQube configuration, then call a versioned workflow from this repository through a thin caller workflow.

The central CI workflow is [`.github/workflows/reusable-app-ci.yml`](.github/workflows/reusable-app-ci.yml). It supports fixed profiles for Java with Maven, Java with Gradle, Python, Node.js/TypeScript, .NET/C#, and Go. Each profile runs its documented format, lint, and test checks. Application deployment lives in the separate [`.github/workflows/reusable-app-cd.yml`](.github/workflows/reusable-app-cd.yml).

Every caller runs the mandatory SonarQube Cloud Quality Gate and OSV dependency scan, plus full-history Gitleaks scanning. Gitleaks findings and scan errors are advisory; review its native summary and logs. Container scanning and non-production GHCR publication are optional.

Stage 1 includes opt-in Node application-package deployment to **Azure App Service**, with package checksum verification and post-deployment health checks. The sample validates open pull requests; after a PR is merged into `main`, it reruns CI against that exact merged revision, packages it, and calls CD with `needs: ci`. It does not deploy on a `push` event. Containers remain optional. The first application is the separate [simple_web_app](https://github.com/Lekanlekzy/simple_web_app) repository; the Python regression fixture stays a package. Azure resources and caller configuration are required before cloud verification can complete. See the [setup and rollback runbook](docs/stage-1/azure-app-service.md).

## How the reusable workflow is organized

- **Validation** checks the caller's inputs and required files.
- **Build and test** resolves profile build paths, installs the selected toolchain, and runs that profile's formatting, lint, and unit-test commands. Build output follows the selected profile's conventions.
- **Secret and dependency scans** run as separate jobs. The official Gitleaks Action scans fetched Git history and reports findings as warnings; OSV fails when it finds a vulnerable dependency.
- **SonarQube Cloud** runs in its own job. Only this job receives the project-scoped `SONAR_TOKEN`. Java bytecode and Python coverage reports pass from the build-and-test job as short-lived artifacts, so the Sonar job does not run application build or test scripts with the token.
- **Container build and scan** runs only when requested. It adds OCI labels for the source repository, commit, title, build time, and workflow run, then scans locally without package-write credentials. Publication stays in the same reusable workflow as a separate job, enabled with `publish_image: true` only after every required gate passes.
- **Stage 1 Required Checks** writes a table of expected and actual job results to the GitHub run summary before reporting the aggregate result. It fails if a mandatory gate fails, or if an optional job that was requested does not succeed. Disabled optional jobs appear as `Not requested` only when they were skipped. The same table includes optional container checks and image publication, and labels Gitleaks `Advisory (see scan logs)`.
- **Application packaging** runs in CI when `package_app: true`. The Node build produces a versioned ZIP without cloud credentials. CI exposes its artifact ID, SHA-256, and revision only after the required-checks job succeeds.
- **Application deployment** runs in the separate CD workflow after CI succeeds for the exact revision merged into the actual default branch. It verifies the same-run ZIP's checksum and revision before authenticating with Azure OIDC, then deploys without checkout or application build commands. Its health check verifies HTTP status, the deployed commit, and the home page, with its own deployment summary. Other language profiles currently provide CI, without an application-package deployment adapter.

GitHub-hosted jobs use separate, short-lived runners with separate workspaces. A job that needs caller files checks out the repository for itself; one job's checkout is not shared with another. Checkouts disable persisted credentials so the checkout token is not left in Git configuration for later commands.

## Workflows in this repository

- [`reusable-app-ci.yml`](.github/workflows/reusable-app-ci.yml) is callable only through `workflow_call`; it does not start itself.
- [`reusable-app-cd.yml`](.github/workflows/reusable-app-cd.yml) is a separate `workflow_call` for non-production Azure deployment. The [Node caller example](examples/caller-workflows/node-app-ci-cd.yml.example) calls CI first and CD with `needs: ci`; only CD allows `id-token: write`.
- [`reusable-app-ci-regression.yml`](.github/workflows/reusable-app-ci-regression.yml) calls the central workflow against the Python fixture in [`tests/consumer-repo`](tests/consumer-repo/). It runs for pull requests to `main` and manual dispatch. It skips fork and Dependabot pull requests because those runs do not receive the regression Sonar secret.
- [`main-protection.yml.disabled`](.github/workflows/main-protection.yml.disabled) is intentionally disabled for now. Its retained definition runs the local contract tests, actionlint, and zizmor when restored to a `.yml` filename. GitHub rulesets or classic branch protection separately enforce merge rules; disabling this file does not change remote repository settings.

The regression caller explicitly targets `Lekanlekzy_stage1-devsecops`; no project-key variable is needed. Configure the existing `SONAR_TOKEN` secret with permission to analyze that project. The Sonar organization is fixed to `lekanlekzy`. Never use `pull_request_target` to work around fork-secret restrictions.

## Supply-chain scope

The ZIP checksum and revision checks identify the package built by the same run. SBOM generation, signed build provenance/attestations, and independent attestation verification are planned for Stage 2 in the [roadmap](docs/architecture/four-stage-roadmap.md). Those controls will establish evidence about the components and builder of the released artifact. The packaged ZIP is not currently started and tested before upload; CD performs its first runtime verification after deployment.

## Local checks

Run the dependency-free repository contract suite from the repository root:

```powershell
python -m unittest discover -s tests -v
```

Run the Python fixture checks and generate Sonar's coverage report from PowerShell:

```powershell
Set-Location tests/consumer-repo/python-app
python -m pip install -e '.[dev]'
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov --cov-report=xml:coverage.xml
```

Python callers include pytest, pytest-cov, and Ruff in their `[dev]` extra. The fixture configures relative coverage paths and source scope in `pyproject.toml`; its `coverage.xml` is imported by Sonar. See the [workflow contract](docs/stage-1/reusable-workflow-contract.md#python-coverage) for caller configuration.

Local tests do not verify GitHub Actions execution, SonarQube Cloud configuration or Quality Gate behavior, scanner service results, GHCR permissions, observed status-check names, or repository branch rules. The central workflow's integration behavior must be checked in a configured GitHub caller repository.

## Project guide

- [Reusable workflow contract](docs/stage-1/reusable-workflow-contract.md)
- [Security tools and dependency updates](docs/stage-1/security-tools-and-dependencies.md)
- [Verified action pins](docs/stage-1/action-pins.md)
- [Default-branch protection runbook](docs/stage-1/default-branch-protection.md)
- [Acceptance criteria](docs/stage-1/acceptance-criteria.md)
- [Azure App Service deployment and rollback](docs/stage-1/azure-app-service.md)
- [Architecture decisions](docs/decisions/)
- [Four-stage roadmap](docs/architecture/four-stage-roadmap.md)
