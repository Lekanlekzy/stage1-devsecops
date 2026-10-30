# Stage 1 reusable workflow contract

## Caller interface

Application repositories keep a thin caller workflow and a small amount of application-specific build and Sonar configuration. CI lives in `.github/workflows/reusable-app-ci.yml`; application deployment and health verification live in `.github/workflows/reusable-app-cd.yml`. Both expose `workflow_call`. Use CI alone for build/test/scan, or a second caller job with `needs: ci` to deploy its successful package.

Required caller inputs are `language` and `sonar_project_key`. The SonarQube Cloud organization is fixed to `lekanlekzy` in the central workflow. `SONAR_TOKEN` is a required named secret. The caller passes it explicitly; `secrets: inherit` is not used. The caller also provides a `sonar-project.properties` file in its working directory so the project's source and test paths can be reviewed with the application.

Supported `language` values are `java-maven`, `java-gradle`, `python`, `node`, `dotnet`, and `go`. Versions and paths use typed `string` or `boolean` inputs. The workflow rejects unknown profiles, path escapes, missing profile files, absent npm scripts, invalid Sonar keys, missing Sonar configuration, and unsafe publication requests. It does not accept caller shell commands.

| Input | Type | Default | Purpose |
|---|---|---|---|
| `language` | string | required | Fixed profile name |
| `working_directory` | string | `.` | Application project directory within the repository |
| `java_version` | string | `21` | Java runtime for both Java profiles |
| `python_version` | string | `3.12` | Python runtime |
| `node_version` | string | `24` | Node.js runtime |
| `node_typescript` | boolean | `true` | Require and run the npm `typecheck` script |
| `dotnet_version` | string | `10.0.x` | .NET SDK version |
| `dotnet_project` | string | empty | Optional .NET solution/project path if detection is ambiguous |
| `go_version` | string | `1.27.x` | Go runtime |
| `sonar_project_key` | string | required | Existing SonarQube Cloud project key |
| `run_container_checks` | boolean | `false` | Build and scan the configured Dockerfile |
| `container_context` | string | `.` | Docker build context relative to repository root |
| `publish_image` | boolean | `false` | Publish the scanned image after all gates pass; requires container checks and a trusted default-branch push |
| `image_name` | string | empty | Optional lowercase `ghcr.io/owner/name` in the caller owner's namespace; defaults to `ghcr.io/<caller-repository>` |
| `package_app` | boolean | `false` | Build a versioned Node deployment ZIP; requires `package:ci` and does not deploy |

Every CI caller job declares `actions: read`, `contents: read`, `pull-requests: read`, `security-events: write`, and `packages: write` as the permission ceiling. Gitleaks uses `pull-requests: read` to discover PR commits. The pinned OSV reusable workflow declares `actions: read`, `contents: read`, and `security-events: write`; `security-events: write` remains required by its definition even with `upload-sarif: false`. GitHub validates the publisher's package-write requirement even when publication is disabled. CI does not need OIDC permission. A separate CD caller permits only `id-token: write`. Workflow defaults are `permissions: {}` and individual jobs narrow their tokens as listed below. Same-run artifact transfers do not themselves require an `actions: read` GitHub API token.

`reusable-app-ci.yml` exposes `image_uri` and `image_digest` from its publisher job after successful publication. These outputs are empty when publication is disabled. The container job's image ID and archive hash remain internal outputs used to verify the exact scanned image.

When `package_app: true`, CI exposes `app_package_artifact_id`, `app_package_sha256`, and `app_revision` through the successful `Stage 1 Required Checks` job. They identify the same-run ZIP and source commit; they remain empty if packaging is disabled or required checks do not succeed. Pass all three outputs to CD rather than looking up an artifact by name or rebuilding the application.

### Sample trigger and revision contract

The Node caller listens to `pull_request` events targeting `main`, with types `opened`, `synchronize`, `reopened`, and `closed`, plus `workflow_dispatch` for validation only. It has no `push` trigger. Open PR events run CI without a deployment package; a closed unmerged PR skips. For PR calls, the head repository must equal the caller repository and the triggering actor must not be `dependabot[bot]`. These guards do not relax the mandatory Sonar gate or use `pull_request_target`.

Only `closed` with `merged: true` enables `package_app`. This run revalidates the merged result rather than deploying the earlier PR-validation artifact. CI checks out explicit `github.sha` and rejects a post-merge run unless it equals the event's `pull_request.merge_commit_sha`. Its Sonar invocation explicitly sets `sonar.branch.name` to the PR base branch for closed merged events, analyzing the merged default-branch revision rather than submitting analysis to a closed PR. The live Sonar/GitHub behavior still needs a configured integration run.

The caller's CD job requires successful CI, a closed merged PR, base branch equal to the actual default branch (`main` for the sample), the current ref equal to that default branch, matching event/caller repositories, a non-fork repository, a same-repository PR head, and `github.sha` equal to `pull_request.merge_commit_sha`. CD repeats the trust/revision checks before deployment. Neither direct pushes nor manual dispatch deploy. Concurrency cancels superseded unmerged PR validation; it does not cancel a merged release run as though it were an old PR build. Optional GHCR publication keeps its independent trusted-push-only contract.

For publication, call the same workflow with `publish_image: true` and `run_container_checks: true`, optionally setting `image_name`. Validation rejects publication outside a non-fork default-branch push. The publisher depends on every mandatory gate and the container scan. Only the Sonar job receives `SONAR_TOKEN`; the publisher uses its own job token for GHCR.

| Job type | Explicit GITHUB_TOKEN permissions |
|---|---|
| Validation, build/tests, Sonar, container build/scan | `contents: read` |
| Gitleaks secret scan | `contents: read`, `pull-requests: read` |
| OSV dependency scan | `actions: read`, `contents: read`, `security-events: write` |
| Aggregate result tables | none |
| Isolated publisher in `reusable-app-ci.yml` | `packages: write` |
| Isolated Azure deployment in `reusable-app-cd.yml` | `id-token: write` |

The updated caller examples use `Lekanlekzy/stage1-devsecops` at `main` until the first approved release. See `examples/caller-workflows/publish-image.yml.example` for an opt-in publishing caller of the same workflow.

## Language profile requirements

| Profile | Required files and conventions | Central checks |
|---|---|---|
| Java with Maven | `pom.xml`; wrapper preferred. Pin Spotless and Checkstyle plugin versions in the POM. | `spotless:check`, `checkstyle:check`, `verify`; compiled classes required for Sonar |
| Java with Gradle | `gradlew`, `build.gradle` or `build.gradle.kts`; wire formatter, linter, and unit-test tasks into Gradle's `check` task. | `./gradlew check`; compiled classes required for Sonar |
| Python | `pyproject.toml`, pip-installable project, `[dev]` extra containing Ruff, pytest, and pytest-cov; coverage source/relative paths configured. | `pip install -e '.[dev]'`, Ruff lint/format check, `pytest --cov --cov-report=xml:coverage.xml` |
| Node.js / TypeScript | `package.json`, `package-lock.json`; required scripts `lint`, `format:check`, `build`, and `test:ci`; tests write `coverage/lcov.info`. TypeScript also requires `typecheck` by default. | `npm ci` and required scripts |
| .NET / C# | Exactly one discoverable `.sln`, `.slnx`, or `.csproj`, or set `dotnet_project`. | `dotnet format --verify-no-changes`, `dotnet test` |
| Go | `go.mod`. | `gofmt` check, `go vet ./...`, `go test ./...` |

The language setup and commands are implemented in the reusable workflow. Local contract tests check that each fixed profile remains present and that required failure guards have not been removed. A real GitHub caller run is still required to verify each toolchain and profile end to end before the profile is treated as operationally accepted.

The `Validation` job checks caller configuration without emitting build paths. The `Build and test` job resolves the selected .NET project and Java bytecode directory, then runs the profile commands. Its name covers those profile commands; Python uses an editable install and Node uses its required scripts, so a distribution package is not promised for every profile. Java bytecode is transferred to the separate Sonar job using a same-run, one-day artifact. This preserves the boundary between executing application build scripts and using the Sonar token.

### Python coverage

Run `pytest --cov --cov-report=xml:coverage.xml` from `working_directory`. Configure Coverage.py in the application's `pyproject.toml`, adapting `source` to the application's source directories:

```toml
[tool.coverage.run]
source = ["src"]
relative_files = true
branch = true
```

The bare `--cov` option enables coverage while retaining the configured source scope. Supplying a source value overrides that configuration. The build-and-test job uploads `coverage.xml`; the separate Sonar job downloads it into the application's `working_directory` before analysis. For Python, the central workflow automatically supplies this scanner argument:

```text
-Dsonar.python.coverage.reportPaths=coverage.xml
```

The fixture repeats this property in `sonar-project.properties` for standalone scans; Python callers do not need to duplicate it for this reusable workflow.

Sonar imports the report; it does not run tests or calculate coverage from source alone. The Sonar job receives report data without executing application tests or installing the application's dependencies. Use CI-based Sonar analysis for coverage. See [Sonar's Python coverage documentation](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/test-coverage/python-test-coverage). Other language profiles currently retain their existing test commands without a central coverage-report convention.

## Scans, gates, and failure behavior

The official Gitleaks Action v3 is pinned by full commit SHA and installs scanner v8.30.0. Checkout fetches full history and the central config extends default rules without project-ID exceptions. The Action scans commit ranges on PR/push events, followed by `gitleaks git "$GITHUB_WORKSPACE" --config="$RUNNER_TEMP/central-gitleaks.toml" --redact=100 --verbose` to scan full history; manual Action runs already scan full history.

Both scan steps use `continue-on-error: true`: findings and Action/scanner errors are advisory. Checkout and central-configuration failures still block. Review the native Action summary and redacted logs; there are no custom result classifiers or findings outputs. Comments and report-artifact upload are disabled. The aggregate row says `Advisory (see scan logs)` rather than claiming a clean result.

All callers run profile validation, profile lint/format/unit tests, full-history Gitleaks scanning, the SHA-pinned Google OSV reusable workflow, and a SonarQube Cloud analysis that waits for the remote quality gate. Missing project files/configuration, errors from blocking tools, a missing Sonar token, OSV dependency vulnerability findings, test failures, or a failed Sonar quality gate fail the workflow. Mandatory gates propagate failures. The upstream OSV scan step collects vulnerability results before its reporter enforces `fail-on-vuln`; its scan-error guard also prevents a missing report from passing. OSV scans recursively from the repository root with `fail-on-vuln: true` and `upload-sarif: false`. Fixed scanner arguments disable call analysis, include ignored files, and select `/dev/null` as an empty TOML configuration, overriding repository suppression files. Applications need scanner-supported manifests or lockfiles; the fixture supplies `requirements-dev.txt` matching its direct dev dependencies because the scanner does not extract them from `pyproject.toml` alone.

Container build and Trivy image scanning run only when `run_container_checks` is true. HIGH and CRITICAL OS/library findings fail the gate. Publication is opt-in through `publish_image: true` in the same reusable workflow; it also requires `run_container_checks: true`. Its separate `packages: write` publisher runs only after every mandatory gate and the container scan succeed. The publisher targets the caller repository's fixed `non-production` GitHub Environment. Create and protect that environment in each caller repository before enabling publication. The job only downloads the scanned image artifact, verifies its archive and image ID, pushes a SHA-tagged image to GHCR, and compares the remote manifest's config digest with the scanned image ID. It does not check out or execute application code.

The image builder sets OCI labels for the source URL, source revision, repository title, UTC creation time, and workflow-run URL before scanning. These labels help operators identify an image; they are not attestations or signatures. Application-specific license/vendor/author metadata belongs in the application's Dockerfile when accurate.

The `Stage 1 Required Checks` job runs with `always()` and writes a table to `GITHUB_STEP_SUMMARY`, including each check's expected status, actual status, and verdict. The table is written even when a gate fails. Mandatory and requested optional jobs must succeed; unrequested container and publication jobs must be skipped. The same table includes image publication and labels a successful Gitleaks job `Advisory (see scan logs)`. A skipped, cancelled, failed, or unknown required job result fails the aggregate gate; Gitleaks scan-step failures are allowed to continue.

## SonarQube Cloud setup

Before using the workflow, a Sonar administrator must configure the `lekanlekzy` SonarQube Cloud organization and GitHub connection, import/create each repository's project, select the subscription plan, and review the project's quality profile and Quality Gate. Application settings provide `SONAR_PROJECT_KEY` as a variable and an analysis token authorized for that project as `SONAR_TOKEN`. The regression caller explicitly sets `sonar_project_key: Lekanlekzy_stage1-devsecops` and passes the existing `SONAR_TOKEN` secret; no regression project-key variable is needed. No Sonar organization variable or input is required. Every caller provides the conventional `sonar-project.properties` file in its working directory. The scan action sends analysis to the fixed SonarQube Cloud service URL; repository properties cannot redirect the token to another host.

`sonar_project_key` identifies the existing SonarQube Cloud project that receives this application's analysis, issues, history, and Quality Gate result. It is a non-secret identifier, separate from the display name and from the secret used to authenticate. The project must belong to `lekanlekzy`; `SONAR_TOKEN` must authorize analysis of that project. Read the key from the intended Sonar project's configuration and store it as a GitHub Actions variable. The caller input becomes the scanner's `sonar.projectKey` parameter.

A cross-repository reusable workflow cannot read secrets stored only in the central workflow repository. Each caller explicitly passes `SONAR_TOKEN` from a secret available to its own repository. Where GitHub organization secrets are available, an organization secret can supply the same token to selected repositories; its repository access policy and Sonar project permissions still need configuration. The central regression runs in this repository and therefore passes this repository's existing `SONAR_TOKEN`. See [GitHub reusable workflow secrets](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#passing-inputs-and-secrets-to-a-reusable-workflow).

Sonar requires a project identity for analysis. This platform additionally requires that identity as an explicit workflow input because Sonar and its Quality Gate are mandatory Stage 1 checks. Although Sonar can read a key from `sonar-project.properties`, the workflow deliberately supplies the reviewed caller value on the command line. The key does not create a project or grant permission; configure the target project and token before invoking the workflow. See [Sonar analysis parameters](https://docs.sonarsource.com/sonarqube-cloud/analyzing-source-code/analysis-parameters/parameters-not-settable-in-ui).

The six requested profiles map to Sonar's Java, Python, JavaScript/TypeScript, C#, and Go analyzers. Plan and private code line limits vary; select a plan that supports the organization's private code volume and required features. Sonar's free private-project allowance and plan details can change, so verify them with Sonar before onboarding repositories.

`SONAR_TOKEN` is used only in the dedicated Sonar scan job. It is never available to the job that executes project build/test scripts or to the image builder/publisher. GitHub does not pass repository secrets to workflows triggered by fork pull requests. Since Sonar is mandatory, a fork PR with no token fails closed and cannot merge until an authorized analysis run is available. The caller must not use `pull_request_target` to work around this limitation.

### Disable the Sonar pull-request comment

In the SonarQube Cloud project, open **Administration > General Settings > Pull Requests > Integration with GitHub**, then turn **Enable summary comment** off. This disables the Conversation-tab summary comment while retaining the GitHub check and mandatory Quality Gate. This is a project setting, not a workflow permission change. See [Sonar's GitHub integration documentation](https://docs.sonarsource.com/sonarqube-cloud/managing-your-projects/administering-your-projects/devops-platform-integration/github). No remote setting is changed by the repository files.

## Node application-package deployment

Containers and image publication are independent of Node packaging and CD. The Node caller example uses neither. Application-package deployment is currently implemented only for Node; the other profiles retain their CI support. `build` runs for every Node caller and `test:ci` must produce `coverage/lcov.info`, transferred to the isolated Sonar job.

For deployment, the Node caller enables `package_app: true` only for a closed merged PR. Its fixed `package:ci` script creates a ready-to-run `deploy/` directory with its runtime package.json, server, built output, and any production dependencies. The central build stamps `release.json` with the exact merged commit, archives the directory as `app.zip`, and records SHA-256 without Azure credentials. The artifact is retained for 30 days. The successful CI aggregate exposes its artifact ID, checksum, and revision after validation, build/tests, Sonar, OSV, completion of advisory Gitleaks scanning, and any requested container/publication jobs. Source tests and the production build run before packaging; the completed ZIP is not currently started and runtime-tested before upload.

The caller's second job calls `reusable-app-cd.yml` with `needs: ci` and these typed inputs:

| CD input | Type | Default | Purpose |
|---|---|---|---|
| `app_package_artifact_id` | string | required | Exact package artifact ID exposed by successful CI in the same workflow run |
| `app_package_sha256` | string | required | Expected ZIP SHA-256 from CI |
| `app_revision` | string | required | Source commit from CI; must match the current run and packaged `release.json` |
| `azure_webapp_name` | string | required | Existing dedicated non-production App Service name |
| `azure_client_id` | string | required | Federated Azure identity client ID |
| `azure_tenant_id` | string | required | Azure tenant ID |
| `azure_subscription_id` | string | required | Azure subscription ID |
| `health_check_path` | string | `/healthz` | JSON endpoint returning HTTP 200, `status: ok`, and the deployed commit in `revision` |

CD validates its inputs and accepts only a trusted closed merged PR into the caller's actual default branch under the revision guards above. Its isolated deployment job has no checkout or application build commands: it downloads the same-run artifact by ID, verifies the ZIP checksum and release revision, logs into Azure using OIDC, and deploys the ZIP through the official pinned Azure action. It uses the fixed `non-production` GitHub Environment and serializes deployments to the target app. CD takes no Sonar secret. The CI table reports CI/image gates; deployment and health have a separate CD summary. CD exposes `deployment_url` only after successful health verification.

The health contract requires HTTP 200, JSON `status: ok`, and `revision` equal to the deployed commit, followed by a successful nonempty home-page response. The sample's endpoint also checks that built assets exist. This catches an unavailable app, incomplete package, or old release; it does not run browser interactions or business end-to-end tests. Startup checks retry for five minutes; failures block the deployment result. No automatic rollback is attempted. Retained packages support manual rollback without rebuilding. See the [Azure setup, health, and rollback runbook](azure-app-service.md). Azure resource setup and real deployment/rollback validation remain required.

### Supply-chain boundary

The checksum checks package bytes and the manifest records the expected revision within this run. SBOM generation, signed build provenance/attestations, and attestation verification remain planned Stage 2 controls under the roadmap and AGENTS instructions. Current package identity checks do not establish independent trusted provenance. No SBOM or attestation is currently generated or verified.

## Stable checks and caller upgrades

Central job display names are intended to remain stable: `Validation`, `Build and test`, `Gitleak scan`, `Dependency vulnerabilities`, `SonarQube Cloud quality gate`, `Container build and scan`, `Publish non-production image`, and the aggregate `Stage 1 Required Checks`. `Validation` and `Build and test` replace the earlier `Contract validation` and `Application quality` names. Any caller that selected an earlier check must select the newly observed context after a successful run. GitHub may present a check context with caller workflow/job prefixes. No check context is mandatory until the workflow has completed successfully in the actual consuming repository and the exact check name appears in GitHub's selector.

Consumers should pin a tested release tag or, for stronger immutability, a full commit SHA. Central releases follow semantic versioning: additive optional inputs may be added in a minor release; breaking input, output, permission, or gate changes require a new major version. Test changes against the caller example and contract suite, publish an immutable release tag only after review, and have consumers upgrade through a pull request with their exact current check contexts visible. Dependabot can propose central workflow reference updates.

The regression caller uses `./.github/workflows/reusable-app-ci.yml`, so GitHub loads the reusable workflow from the same commit as the caller. Permission fixes must be committed together and checked in a new run from the updated revision; rerunning an older revision does not include local edits. See [GitHub's caller reference rules](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#calling-a-reusable-workflow).

GitHub has reported permission validation failures. A successful run of the updated workflow and the exact external status context remain unverified.
