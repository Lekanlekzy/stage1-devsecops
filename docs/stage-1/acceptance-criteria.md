# Stage 1 acceptance criteria

## Workflow contract

- [x] Separate central CI and CD `workflow_call` workflows provide typed contracts; app repos can call CI alone or sequence CI then CD with `needs: ci`.
- [x] Caller workflow examples pass the Sonar secret explicitly; no `secrets: inherit` or arbitrary caller shell commands.
- [x] The supported profiles are fixed to Java/Maven, Java/Gradle, Python, Node.js/TypeScript, .NET/C#, and Go, with required files/conventions documented.
- [x] The workflow has stable intended job names and typed image outputs; exact GitHub contexts remain unverified until a successful caller run.
- [x] Consumer pinning/version upgrade guidance is documented.
- [ ] The updated workflow passes GitHub permission validation in a configured caller; local checks alone do not establish this.
- [x] A same-commit Python consumer fixture calls the central reusable workflow for pull requests to `main` and manual dispatch.
- [x] The regression caller explicitly passes the existing `SONAR_TOKEN` secret for its configured project and skips fork/Dependabot PRs without weakening the reusable workflow's mandatory gates.
- [x] The central workflow fixes the Sonar organization to `lekanlekzy`; callers provide only the target project key and authorized token, with cross-repository secret access documented.
- [x] Validation checks caller configuration; build-path resolution lives in the `Build and test` job.
- [x] The aggregate gate writes a run-summary table before failing on unsuccessful mandatory/requested checks; unrequested optional jobs must be skipped.

## Required quality and security gates

- [x] Each profile runs its required format/lint/test commands with explicit failure behavior.
- [x] Python requires pytest-cov in `[dev]`, generates `coverage.xml` with relative source paths in the build job, and transfers it to the isolated Sonar job for import.
- [x] The four Python fixture tests pass locally with 100% coverage, and the XML source paths resolve relative to the application directory.
- [ ] A GitHub run confirms Python report delivery and Sonar coverage import; local test coverage alone does not prove the remote Quality Gate passes.
- [x] SonarQube Cloud is mandatory, scoped to a project/org, and configured to wait for the remote Quality Gate.
- [x] Missing Sonar project/config/token, service error, scan error, or Quality Gate failure does not silently pass.
- [x] The SHA-pinned official Gitleaks Action runs scanner v8.30.0 with default rules, redaction, and no project-ID exception; a PR/push follow-up scans full history using the installed binary.
- [x] Both Gitleaks scan steps use step-level continuation: findings and Action/scanner errors are advisory, while checkout/configuration failures still block. No custom result classifier or findings outputs are used.
- [x] Gitleaks uses its native summary and scan logs; comments/artifact upload are disabled. The aggregate row reads `Advisory (see scan logs)`.
- [ ] A GitHub run verifies advisory Gitleaks execution and summary reporting; local configuration checks do not establish a clean secret scan.
- [x] The SHA-pinned full OSV reusable workflow scans recursively, fails on current vulnerabilities or scanner errors, and declares the upstream-required `actions: read`, `contents: read`, and `security-events: write` scopes without enabling SARIF upload.
- [ ] The fixture passes the restored OSV workflow against current vulnerability data. An earlier direct-CLI smoke test returned findings for a resolved Pygments dependency; that historical result is not validation of the restored workflow.
- [x] Every external Action reference uses a full commit SHA documented in `action-pins.md`; the Gitleaks scanner version is fixed separately through the Action.
- [x] Snyk/Veracode are documented as inactive alternatives; they are not represented as passing/active gates.
- [ ] The six profiles pass end-to-end in real GitHub Actions caller repositories.
- [ ] SonarQube Cloud org/project bindings, token scope, selected plan, and quality gates are verified for every onboarded caller.

## Container safety

- [x] Container checks and publication default to false. Opt-in publication remains a separate job in the Stage 1 CI reusable workflow and requires `run_container_checks: true`.
- [x] Trivy scans the local image before the publish job.
- [x] The publisher is a separate package-write job that does not check out or execute application code.
- [x] Publication is restricted to a non-fork push on the caller's actual default branch and the caller owner's GHCR namespace.
- [x] The publisher verifies the downloaded artifact hash and image config ID, then verifies the published manifest's config digest.
- [x] The publisher targets the fixed `non-production` GitHub Environment.
- [x] CI callers allow the CI workflow's required scopes (`actions: read`, `contents: read`, `pull-requests: read`, `security-events: write`, `packages: write`), without OIDC. OSV receives its three required scopes; Gitleaks receives `contents: read` and `pull-requests: read`; build/test, Sonar, and container jobs have only `contents: read`; only the guarded publisher has `packages: write`; the summary has no token permissions. CD callers permit only `id-token: write`, narrowed to the isolated deployment job.
- [x] Container builds add OCI labels for source, revision, title, creation time, and workflow run before scanning.
- [ ] The `non-production` GitHub Environment is protected, GHCR access and image tag policy are configured, and registry verification succeeds in the consuming repository.
- [ ] No pull request or fork run can publish an image or receive package-write credentials in a GitHub test repository.

## Non-production cloud delivery

- [x] Select Azure App Service code deployment and document its setup and federated identity requirements. Containers remain optional.
- [x] CI optionally packages Node with `package_app: true`, exposing the artifact ID, SHA-256, and revision only through its successful required-checks job.
- [x] The Node caller validates PRs on `opened`, `synchronize`, and `reopened`; on `closed` with `merged: true` into `main`, it reruns CI on the exact merged revision and enables packaging. Closed unmerged PRs skip, manual dispatch validates only, and the sample has no push trigger. Same-repository heads and the non-Dependabot triggering-actor guard remain in place.
- [x] CI explicitly checks out `github.sha` and validates post-merge SHA equality against the event's `merge_commit_sha`. The post-merge Sonar scan explicitly targets the PR base branch; live integration remains unverified.
- [x] A separate `reusable-app-cd.yml` requires successful CI and a trusted closed merged PR into the actual default branch with a matching ref and merge SHA. It verifies the same-run ZIP checksum and release revision before isolated OIDC authentication, without checkout or application build commands. Push and manual runs cannot deploy.
- [x] Caller concurrency cancels superseded unmerged PR validation without treating merged release runs as cancellable PR builds.
- [x] Implement post-deployment HTTP, JSON status, expected revision, and home-page checks; report them in a separate CD deployment summary. The CI table covers CI and optional image jobs.
- [x] Document manual rollback using a retained ZIP and its SHA-256, without rebuilding. Failed health checks do not automatically roll back.
- [x] The actual local Node sample passes lint, formatting, production build, three health/HTTP checks, and package creation with Node 24. Server line coverage is 94.19%; this does not establish the remote Sonar Quality Gate result.
- [x] The actual central ZIP step stamps the expected revision and produces a matching checksum in local validation. Package and Node coverage handoffs use artifact IDs so job retries retain their original build references.
- [ ] The separate `simple_web_app` caller and server pass GitHub CI and expose the expected health response on Azure.
- [ ] Configure Azure resources, OIDC identity, GitHub Environment protections, repository variables, and Sonar project/token for the application.
- [ ] Verify rollback to a previous package in Azure and confirm the restored application revision.
- [ ] A configured GitHub caller completes CI, package delivery, cloud deployment, verification, and rollback in the real non-production environment. Image publication is optional.

Known limits: the completed ZIP is not started and runtime-tested before upload; source tests/build and post-deployment health do not establish that. SBOM/build provenance or attestations and independent verification remain Stage 2 scope. Current SHA-256/revision checks are not trusted provenance; Stage 1 does not claim these future controls.

## Main/default-branch protection

- [x] Documentation distinguishes validation workflow results from GitHub enforcement settings.
- [x] GitHub ruleset is recommended over classic protection when available; trade-offs and platform-owner limitations are documented.
- [x] Required setup covers PRs, mandatory successful checks, strict/up-to-date branches, linear history/no merge commits, empty bypass, no force pushes, and no deletion.
- [ ] Active main-protection validation runs the local contract tests, actionlint, and zizmor for pull requests to `main` and pushes to `main`. Temporarily disabled by user request; definition retained as `main-protection.yml.disabled`.
- [x] Required status contexts are not guessed; documentation requires a successful GitHub run and exact context selection first.
- [ ] Central repository's actual default branch has active verified protection.
- [ ] Each consuming application's actual default branch has equivalent active verified protection and requires its caller check(s).
- [ ] GitHub test PR verifies failed-check, stale-branch, direct-push, force-push, delete, merge-commit, and admin-bypass behavior.

## Dependabot and validation

- [x] Central Dependabot config targets only represented dependency sources: GitHub Actions references and the Python regression fixture.
- [x] Application ecosystem examples include Maven, Gradle, pip, npm, NuGet, Go modules, Docker, and GitHub Actions.
- [x] Docs distinguish version update PRs from security alerts/security updates and from mandatory OSV checks.
- [x] Local standard-library contract tests include negative cases for bad profile, missing profile/config, blocking scanner error handling and advisory Gitleaks configuration, unsafe publish event/ref/fork, missing container checks, and empty optional output behavior.
- [x] Before the CI/CD split, active workflows, caller examples, and the retained disabled definition passed local `actionlint` v1.7.12 syntax validation. This historical result does not validate the new CD definition.
- [x] After the CI/CD split and before the merged-PR trigger changes, `actionlint` v1.7.12 passed for eight active/retained workflow definitions and caller examples, including the actual application caller (2026-10-22). Static Python parsing passed for ten embedded scripts and the repository test modules; tests were not executed.
- [x] Current merged-PR delivery passes `actionlint` v1.7.12 for eight workflow definitions/examples, including the applied application caller, and static Python parsing for ten embedded scripts (2026-10-22). Tests were not executed.
- [ ] `zizmor` workflow security analysis passes in a suitable local or CI environment.
- [x] Before the CI/CD workflow split, all 22 repository contract/permission checks passed locally after the Node deployment changes (2026-10-22). This historical result does not validate the separate CD workflow.
- [ ] Repository contract/permission checks are rerun against the CI/CD split and merged-PR delivery contract. Actual Azure and GitHub integration remain unverified.

Stage 1 is not production-ready until a real application caller has completed GitHub validation and the relevant organization has reviewed Sonar, secret, package, and branch-rule settings. Local tests do not establish remote integration success.
