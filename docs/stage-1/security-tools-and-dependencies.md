# Stage 1 security tools and dependency updates

## Required checks

| Area | Tool | Gate behavior |
|---|---|---|
| Formatting, lint, and unit tests | Fixed per-language profile in `reusable-app-ci.yml` | Any missing configuration, non-zero command, or test failure fails the required check |
| Source quality and SAST | SonarQube Cloud | Required token/project/config; scanner waits for the configured Quality Gate and fails on service, analysis, or gate failure |
| Secret scanning | Official SHA-pinned Gitleaks Action v3 with scanner v8.30.0 | Default rules and redacted output; PR/push full-history follow-up; findings and Action/scanner errors are advisory, reported through native summary/logs |
| Dependency vulnerabilities | Google's full OSV reusable workflow pinned by commit SHA, scanner v2.6.0 | Recursive scan including ignored files, empty central config overriding caller suppressions, no call analysis; `fail-on-vuln: true`, no SARIF upload; findings and scanner errors fail the check |
| Container vulnerabilities | Trivy action, only when container checks are enabled | Scans the built image before any publisher job; HIGH and CRITICAL OS/library findings fail |

Snyk and Veracode are not active Stage 1 gates. They can be evaluated later as alternatives or integrations after licensing, data handling, false positive, token, and coverage requirements are known. GitHub Advanced Security CodeQL, secret protection, and dependency review may be added as optional integrations when the repository plan and organization configuration permit them. They are not silently substituted for the configured checks above.

## Dependabot policy

The central repository has a small Python regression consumer fixture in `tests/consumer-repo/python-app`, in addition to its GitHub Actions workflow references. `.github/dependabot.yml` therefore enables weekly `pip` updates for that fixture and weekly GitHub Actions updates. It does not enable other package ecosystems without a corresponding manifest.

Application repositories should add only ecosystems represented by their actual manifests/build files. Examples to adapt:

| Application dependency type | Dependabot ecosystem | Typical directory / manifest |
|---|---|---|
| Maven | `maven` | Directory containing `pom.xml` |
| Gradle | `gradle` | Directory containing `build.gradle`, `build.gradle.kts`, or version catalog |
| Python with pip | `pip` | Directory containing `requirements*.txt`, `pyproject.toml`, or `Pipfile` |
| npm | `npm` | Directory containing `package.json` and lock file |
| NuGet | `nuget` | Directory containing `.csproj`, `.sln`, or `packages.config` |
| Go modules | `gomod` | Directory containing `go.mod` |
| Container base images | `docker` | Directory containing a `Dockerfile` |
| GitHub Actions references | `github-actions` | `/` |

For example, an application repository using Maven and GHCR might configure:

```yaml
version: 2
updates:
  - package-ecosystem: maven
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

Version update PRs are distinct from Dependabot alerts and security updates. Repository or organization settings must enable security alerts and Dependabot security updates where supported; adding an `updates` entry alone does not switch those features on. OSV remains the mandatory CI vulnerability gate regardless of alert/update settings. Review the Dependabot ecosystem and manifest support for the current GitHub product before onboarding a new application type.

## Untrusted pull requests and publishing

Application code is untrusted input to test and build jobs. Those jobs have only `contents: read`, do not persist the checkout token, and receive no package-write credential. The Sonar token is scoped to one analysis step in a separate job that does not run project scripts. Fork workflows receive no secrets by GitHub design and therefore fail the required Sonar gate closed.

The central Gitleaks configuration extends default rules without project-ID exceptions. The Action and PR/push full-history follow-up both use `continue-on-error: true`, so findings and scan errors do not block later jobs or optional publication. Checkout/configuration failures still block. Native summary and redacted logs provide results; the aggregate row reads `Advisory (see scan logs)` without classifying findings.

The Gitleaks Action uses `contents: read` and `pull-requests: read` for PR commit discovery. Comments and report-artifact uploads are disabled; the native summary is enabled, and no PR write permission is needed. The Action selects changed commits on PR/push events, followed by an advisory full-history scan using its installed binary. See the [official Action documentation](https://github.com/gitleaks/gitleaks-action) and [pinned implementation](https://github.com/gitleaks/gitleaks-action/blob/e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e/src/index.js).

The OSV nested workflow requires `actions: read`, `contents: read`, and `security-events: write` in its pinned definition, including when `upload-sarif: false`. Allow those scopes in both the dependency job and caller; Gitleaks separately needs the read scopes above. Least privilege means selecting the scopes each job actually requires and using read access where sufficient.

The optional publisher runs only after the mandatory tests/scans and image scan succeed, and only for a `push` to the actual default branch in a non-fork repository. It has no checkout step and no app-script execution. Keep this publisher in `reusable-app-ci.yml`, enabled with `publish_image: true` and `run_container_checks: true`. Callers also allow `packages: write` because the optional publisher is part of the static workflow definition. Only that publisher receives a package-write runtime token. Same-run artifact downloads use runtime credentials and do not add another `actions: read` requirement. The publisher targets the fixed `non-production` GitHub Environment. Create and protect that environment in every caller repository before enabling publication; configure branch restrictions and, where appropriate, required reviewers. Also configure and verify the caller's default-branch rules and GHCR package permissions. Workflow YAML cannot create those remote controls.

Image tags use the caller commit SHA for traceability. Treat tags as mutable unless GHCR/package policy explicitly enforces immutability. The digest output is the identity to retain for downstream use. This Stage 1 design does not produce SBOMs, attestations, provenance, signatures, or SLSA conformance claims.
