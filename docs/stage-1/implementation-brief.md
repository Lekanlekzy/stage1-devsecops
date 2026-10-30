# Stage 1 implementation brief

## Purpose and architecture

Build centrally maintained CI and application-deployment workflows for GitHub Actions and GitHub-hosted runners. Application repositories call `.github/workflows/reusable-app-ci.yml` via `workflow_call` for CI, and optionally call `.github/workflows/reusable-app-cd.yml` from a second job with `needs: ci`; they do not copy pipeline logic. Keep the caller thin and put application-specific build/Sonar scope in the repository.

The reusable workflow has typed fixed-profile inputs, explicit Sonar variables and secret, validation, profile build/tests, mandatory security gates, optional container checks, and an opt-in GHCR publisher job within the same reusable workflow. Validation checks configuration; the build-and-test job resolves build paths. The aggregate required-checks job writes expected/actual results to a run-summary table before enforcing its gate. The workflow has no `push` or `pull_request` trigger of its own. A caller is required to start it.

## Language profiles

- **Java/Maven:** require `pom.xml`; prefer Maven Wrapper; pin Spotless and Checkstyle plugin versions; run formatter check, Checkstyle, and `verify`.
- **Java/Gradle:** require Gradle Wrapper and build file; configure formatter/linter/tests under Gradle's `check` task.
- **Python:** require `pyproject.toml` and pip-installable `[dev]` extra with Ruff, pytest, and pytest-cov. Run `pytest --cov --cov-report=xml:coverage.xml`; configure relative coverage paths and source scope, then transfer the report to the isolated Sonar job.
- **Node.js/TypeScript:** require `package.json`, `package-lock.json`, and `lint`, `format:check`, `build`, and `test:ci` scripts. Tests produce `coverage/lcov.info` for isolated Sonar analysis; `typecheck` is mandatory by default for TypeScript. Optional `package_app: true` additionally requires `package:ci` to produce a ready-to-run `deploy/` directory for CD.
- **.NET/C#:** provide one discoverable `.sln`, `.slnx`, or `.csproj`, or set the typed `dotnet_project` path.
- **Go:** require `go.mod`; run gofmt validation, `go vet`, and `go test`.

Runtime versions are explicit typed inputs with defaults and caller overrides. These versions are inputs to an evolving toolchain and must be reviewed periodically. Do not accept arbitrary shell commands.

## Security gates

- SonarQube Cloud is mandatory for source quality/SAST. The central workflow fixes the organization to `lekanlekzy`; each caller provides an existing project key, project `sonar-project.properties` file, and named `SONAR_TOKEN` secret authorized for that project. Analysis waits for the configured quality gate. Missing project/token/config, service error, scan error, or gate failure fails closed.
- The official SHA-pinned Gitleaks Action v3 runs scanner v8.30.0 with central default rules and no project-ID exception. Checkout retains full history; a PR/push follow-up uses the installed binary to scan all history with redacted verbose output. Both scan steps use `continue-on-error: true`, so findings and scan errors are advisory; checkout/configuration failures still block. Use the native Action summary and logs, with no custom classification or findings outputs. Comments and report artifacts are disabled; the aggregate table labels the scan `Advisory (see scan logs)`.
- Google's SHA-pinned full OSV reusable workflow scans repository dependencies recursively with scanner v2.6.0, `fail-on-vuln: true`, and `upload-sarif: false`. It reports all current findings rather than only newly introduced pull-request findings. Fixed scanner arguments include ignored files, disable call analysis, and override caller suppressions with an empty `/dev/null` TOML configuration on Ubuntu. Its nested jobs require `actions: read`, `contents: read`, and `security-events: write`; callers allow these scopes because the upstream definition requests them even when SARIF upload is disabled. Findings and scan errors fail the gate.
- Trivy scans container images when container checks are enabled and fails for HIGH/CRITICAL operating system or library vulnerabilities.
- Snyk and Veracode are not active Stage 1 gates. Evaluate them later only after licensing and data-flow requirements are established.

Python coverage is generated in the build-and-test job and restored as `coverage.xml` in the application directory. Node tests similarly provide `coverage/lcov.info`. The central scanner supplies each profile's report path. Only report data crosses this boundary; the Sonar job does not rerun tests or install application dependencies. Other profiles do not yet have a central coverage-report convention.

Fork PRs cannot access the Sonar token under GitHub's normal protections and therefore fail the required gate closed. Do not use `pull_request_target`. The test/build job receives no Sonar or publish secret; the Sonar job is separate and does not execute project build scripts.

## Container build and publication

`run_container_checks` and `publish_image` default to false. Publication is enabled in the same Stage 1 reusable workflow with both inputs set to true. The build job has read-only repository access and no package-write permission. It builds locally and Trivy scans the local image. When publication is requested, it uploads the exact scanned image artifact and identity metadata. The separate publisher job depends on successful validation, build/tests, mandatory scans, Sonar, and container scanning; it downloads the artifact, checks its archive hash and image config ID, publishes a commit-SHA tag to GHCR, and verifies the remote image config digest. It does not check out or execute application code.

The publisher accepts only a non-fork `push` to the caller repository's actual default branch and the GHCR namespace belonging to the caller owner. Every caller allows the complete workflow's required scopes: `actions: read`, `contents: read`, and `security-events: write` for OSV, `pull-requests: read` for Gitleaks PR commit discovery, and `packages: write` for the conditional publisher. Gitleaks receives `contents: read` and `pull-requests: read`. Other runtime source jobs receive only `contents: read`; the publisher receives only `packages: write` and the summary receives no permissions. It targets a fixed `non-production` GitHub Environment, which each caller repository must create and protect, and requires GHCR package access before publication. Image SHA tags provide traceability; tag immutability depends on GHCR/package policy. Stage 1 does not generate SBOMs, attestations, signatures, or provenance.

Prefer maintained official GitHub Actions for tool integrations, verify their full commit references and required permissions, and preserve mandatory gate behavior.

## Stage 1 cloud delivery

Use the separate Node sample `simple_web_app` for non-production Azure App Service **code deployment**, without requiring containers or modifying the Python package fixture. CI optionally builds an application ZIP with `package_app: true` and records its SHA-256. Only after mandatory gates and any requested container/publication jobs succeed does CI expose `app_package_artifact_id`, `app_package_sha256`, and `app_revision` through the aggregate job.

The Node caller validates PRs targeting `main` on `opened`, `synchronize`, and `reopened`. On `closed` with `merged: true`, it reruns CI and enables packaging for the exact merged revision: explicit checkout of `github.sha` and validation against `pull_request.merge_commit_sha` prevent the earlier PR artifact from being deployed. Sonar explicitly analyzes the PR base branch on this post-merge run. Closed unmerged PRs skip; manual dispatch validates only; the caller has no push trigger. Same-repository PR heads are required and bot-triggered calls are skipped. Superseded unmerged PR validation may be cancelled; merged release runs are not cancelled as PR validation.

The caller's CD job uses `needs: ci`, passes those package outputs and Azure configuration to `reusable-app-cd.yml`, and permits only `id-token: write`. CI callers do not need OIDC permission or Azure inputs. CD requires the closed merged event, actual default base branch/ref, matching event/caller repositories, a non-fork repository, same-repository head, and event SHA equal to the PR merge SHA. It verifies the same-run package's checksum and revision before Azure login, then deploys without checkout or application build commands. The fixed `non-production` Environment and deployment concurrency guard remain in CD. Optional GHCR image publication stays inside CI with its existing push-only restriction; it is disabled in the sample's merged-PR delivery path.

The post-deployment check requires HTTP 200 from `/healthz`, JSON `status: ok`, the expected commit in `revision`, and a working home page, with a five-minute retry window. The sample endpoint also detects missing built assets. These checks establish basic readiness and release identity; browser and business end-to-end tests remain separate. Source tests and a production build precede packaging, but the final ZIP is not currently runtime-tested before deployment. Failed verification fails CD and does not automatically roll back. CI retains its own required-checks table; CD writes the deployment/health summary. Packages are retained for 30 days for documented manual rollback. Only Node currently has a package deployment adapter; six-profile CI remains separate from deployment support. Bootstrap Azure resources and federated identity using the [setup/rollback runbook](azure-app-service.md). Cloud execution and rollback remain unverified. Terraform, Helm, and GitOps remain later-stage work; [ADR-007](../decisions/ADR-007-stage-1-managed-cloud-delivery.md) records the cloud choice, [ADR-008](../decisions/ADR-008-separate-application-deployment-workflow.md) the CI/CD boundary, and [ADR-009](../decisions/ADR-009-deploy-exact-merged-revision.md) the merge-triggered release.

## Supply-chain boundary

Stage 1 records package SHA-256 and revision and deploys the same-run artifact without rebuilding. A checksum is not trusted build provenance. SBOM generation, build provenance/attestations, and independent verification are assigned to Stage 2 by the agreed roadmap and AGENTS instructions, rather than omitted because of the GitHub account type. They are not generated or verified by the current pipeline.

## Dependencies and updates

The central repository includes one small Python project under `tests/consumer-repo/python-app` to exercise the workflow. Its `.github/dependabot.yml` therefore enables weekly `github-actions` updates and `pip` updates for that fixture. App repositories add ecosystem entries only for real manifests. Dependabot version PRs do not enable security alerts or Dependabot security updates; those are repository/organization settings. OSV remains the required CI dependency gate.

## Default-branch protection

Recommend repository rulesets, with empty bypass lists, over classic branch protection when available. Require PRs, mandatory successful checks, strict/up-to-date checks, linear history/no merge commits, and disable force pushes/deletion. Classic protection is acceptable when rulesets are unavailable and must enable the administrator bypass restriction. Apply equivalent controls to application repositories.

The central main-protection workflow is intentionally paused at the user's request, with its definition retained as `main-protection.yml.disabled`. Restoring the `.yml` extension is required before it reports checks on pull requests to `main` and pushes to `main`. GitHub rules enforce restrictions separately. The active `reusable-app-ci-regression.yml` caller exercises the local Python consumer fixture on pull requests to `main` and manual dispatch, using the explicit project key `Lekanlekzy_stage1-devsecops` and the existing `SONAR_TOKEN` authorized for that project in `lekanlekzy`; no regression project-key variable is needed. External application callers explicitly pass a token available in their own repository; storing it only in the central repository does not make it available across repositories. Fork and Dependabot pull requests skip that secret-backed caller. Select required check contexts only from GitHub's observed check selector after real successful runs; do not guess. Organization/enterprise owners may retain authority to edit policy, so limit and audit settings administration.

## Local versus GitHub validation

Local tests can validate repository contract text, required gates, full SHA references, action permissions, publication guards, dependency config, and the active workflow/caller configuration. They also execute the aggregate-gate reporting script against success and failure cases. The retained main-protection definition is configured to run actionlint and zizmor when activated. Actionlint v1.7.12 has passed locally; local checks do not prove that the reusable workflow executes correctly on GitHub.

Only a GitHub run can verify actual reusable workflow execution, secret availability (including fork behavior), Sonar binding/plan/Quality Gate, OSV and Trivy service behavior, the check contexts GitHub shows, protected-branch enforcement, GitHub Environment reviewers, and GHCR package permissions/publication. A Git remote is configured, but no remote workflow or settings validation has been performed from this workspace.

## Not included

No self-hosted runners/ARC, Vault, Terraform execution, Helm, Argo CD, Flux, production deployment, enterprise multi-registry routing, SLSA claims, or repository-administration token automation.
