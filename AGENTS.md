# Codex Instructions — Enterprise DevSecOps Platform

## Mission
Build a reusable, secure, auditable DevSecOps pipeline platform incrementally. The central pipeline lives in this repository; application repositories call its versioned reusable workflows.
## First task behavior
Before editing, read `README.md`, `docs/stage-1/implementation-brief.md`, `docs/stage-1/acceptance-criteria.md`, and `docs/architecture/four-stage-roadmap.md`, and inspect the existing repository. Do not require a separate plan or approval before implementing work the user has requested.

## Working rules
- Make small, reviewable changes. Never implement all four stages at once.
- Enterprise-grade describes the pipeline quality goal, not a GitHub Enterprise subscription or organization account. Do not infer paid plans or account types from that goal; configure only credentials required by the current account.
- Stage 1 uses GitHub Actions and GitHub-hosted runners. Do not introduce self-hosted runners, ARC, Vault, Terraform execution, Helm, Argo CD, Flux, Kubernetes provisioning, production deployment, or enterprise multi-registry routing yet.
- Stage 1 uses Azure App Service code deployment in non-production, starting with the separate `simple_web_app` Node application; preserve the Python fixture. Keep containers optional and deployment opt-in. Deploy a versioned application ZIP verified by SHA-256, isolate OIDC cloud authentication from builds, and verify health and deployed revision. Document manual rollback with a retained package. CI supports six profiles; do not claim package deployment support beyond Node until adapters are implemented. Bootstrap Azure through the portal or documented commands; preserve the later-stage boundaries above. Cloud execution and rollback remain unverified until real runs succeed.
- Keep application deployment and health verification in `reusable-app-cd.yml`, separate from `reusable-app-ci.yml`. Validate PRs before merge; the Node caller packages only on a closed-and-merged PR into the actual default branch and reruns CI against the exact merge revision before CD with `needs: ci`. Do not deploy on push or manual dispatch. Require same-repository/non-fork trust checks and a matching event SHA, PR merge SHA, and package revision. Only the CD caller/job allows OIDC `id-token: write`; it verifies the same-run ZIP checksum and revision before Azure login and executes no application build commands. Keep optional GHCR publication push-only. SBOM/provenance generation and independent attestation verification remain Stage 2; a checksum is not trusted provenance, and the ZIP has no pre-deployment runtime test yet.
- Keep the central reusable-workflow repository distinct from application repositories. Include a thin caller example and document what must be configured in the caller repository.
- Use supported `workflow_call` inputs with types, defaults, and validation. Prefer fixed language profiles over arbitrary caller-supplied shell commands.
- Stage 1 language profile targets: Java with Maven, Java with Gradle, Python, Node.js/TypeScript, .NET, and Go. Be explicit about language-specific prerequisites and test conventions; do not claim support for a profile unless it is implemented and tested/documented.
- Start with a single non-production container destination. GHCR may be the demonstrator default, but keep publication opt-in and configurable. Never publish on pull_request or from untrusted code. Do not invent organizational registry URLs.
- Keep optional image publication as a separate job in the single Stage 1 `reusable-app-ci.yml`; do not introduce a separate publishing reusable workflow. Callers must allow the job-token permission ceiling required by that definition; narrow each runtime job to its actual needs.
- Separate test/scan permissions from image-publish permissions wherever practical. Use least-privilege `GITHUB_TOKEN` permissions; never use `write-all`.
- Do not pass secrets with `secrets: inherit`; declare and pass only what is required. Prefer GitHub's job token and workload identity where supported over long-lived static credentials.
- Prioritize official, maintained GitHub Actions for Gitleaks and other tool integrations going forward. Pin Actions to verified full commit SHAs and document required permissions and license secrets.
- Before using third-party GitHub Actions, verify official repository, active maintenance, permissions, compatibility, and the exact full commit SHA. Never invent a SHA. If verified SHAs cannot be established, document that blocker and keep an explicit non-production placeholder rather than claiming production readiness.
- Treat application code and pull-request input as untrusted. Never give untrusted pull requests package-publish rights or privileged credentials.
- Use the fixed SonarQube Cloud organization `lekanlekzy`; do not accept a caller organization override. The regression caller uses the existing `SONAR_TOKEN` secret. Other repositories must explicitly pass a caller-accessible repository or organization secret because a reusable workflow cannot read its source repository's secrets.
- Make SonarQube Cloud analysis and its Quality Gate a mandatory Stage 1 gate. Pass only a project-scoped `SONAR_TOKEN` explicitly to the separate Sonar job; GitHub fork PRs do not receive it and must fail closed rather than use `pull_request_target`.
- Keep OSV-Scanner, SonarQube Cloud, and requested Trivy gate failures blocking; mandatory gates must not silently skip or use `continue-on-error`.
- At the user's request, keep Gitleaks simple and advisory: use the official Action and a PR/push full-history follow-up with step-level `continue-on-error: true`, default rules, redaction, and no project-ID exceptions. Findings and Action/scanner errors do not block CI; checkout/configuration steps still block on failure. Use the Action's native summary and scan logs; do not add result classifiers or custom findings outputs. The aggregate row says `Advisory (see scan logs)` and must not claim a clean scan.
- Configure Dependabot only for ecosystems represented by actual manifests in each repository. Dependabot version updates do not by themselves enable security alerts or security updates.
- Add timeout-minutes, concurrency control where appropriate, explicit inputs/outputs, safe logging, and clear failure behavior.
- Do not report a test or security scan as passed unless it actually ran and the result is known.
- Do not push, publish, deploy, open remote PRs, or change remote settings unless the user explicitly authorizes the action.
- Record material technology or security decisions as ADRs, including alternatives and trade-offs.
- Update documentation and acceptance criteria when behavior changes.

## Default-branch protection baseline
- Treat default-branch protection as two parts: (1) a pull-request validation workflow that produces stable required checks, and (2) GitHub repository rules/rulesets that enforce the merge policy. A GitHub Actions workflow alone cannot prevent direct pushes.
- Protect the repository's actual default branch, whether named `main`, `master`, or something else. Also target `main`/`master` explicitly only if the repository intentionally maintains both.
- Require a pull request, require the mandatory CI status checks, and require the branch to be up to date with the base branch before merge (strict status checks).
- Do not configure bypass actors. If using classic branch protection, enable “Do not allow bypassing the above settings” so the rules apply to administrators.
- Disable force pushes and branch deletion for the protected default branch. Configure the required status-check context only after the workflow has reported a successful check at least once; select the exact check shown by GitHub and keep its name stable and unique. Never guess a status context.
- Apply an equivalent ruleset to each application repository. Require the application caller's required CI check(s), not just the central pipeline repository's own validation check.
- Stage 1 may document/configure these controls through GitHub settings. Do not grant a workflow broad administrative tokens merely to manage repository rules. Automating rulesets as code can be evaluated later.
- Main-protection validation is temporarily disabled at the user's request (2026-10-21). Keep its definition at `.github/workflows/main-protection.yml.disabled` and do not re-enable it automatically. When the user requests activation, restore the `.yml` extension to report checks on pull requests to `main` and pushes to `main`. GitHub rulesets/classic protection remain separate remote controls, and required status contexts stay unconfigured until a successful GitHub run reveals their exact names.
- Keep a secret-backed regression caller for the central reusable workflow. It must use a same-commit consumer fixture, pass only the named `SONAR_TOKEN` secret authorized for the regression Sonar project, skip fork/Dependabot PR calls, and never weaken mandatory gates to make the fixture pass.

## Stage 1 security baseline
Stage 1 baseline: language-specific format/lint/tests; mandatory SonarQube Cloud source analysis and Quality Gate; full-history Gitleaks secret scanning with advisory findings and scan errors; mandatory OSV dependency vulnerability scanning; and optional Trivy container scanning before publication. Snyk and Veracode are inactive alternatives. Keep image publication disabled by default, use a commit-SHA tag, and retain/verify the published digest. Distinguish required gates from optional integrations that need a license, token, or external service. Fail closed for mandatory checks.

## Future-stage roadmap (not to implement now)
- Stage 2: strengthen standardization and traceability, add SBOM/provenance and independent verification.
- Stage 3A: infrastructure as code (Terraform or evaluated alternative).
- Stage 3B: Helm plus GitOps (evaluate Argo CD vs Flux).
- Stage 4: runner hardening, Vault or managed secret-store alternatives, signing isolation, registry governance, enterprise policy/audit, resilience, and CI engine evaluation (GitHub Actions vs Jenkins/Tekton/others).

## Definition of done
A change is complete when its tests and relevant static validation have actually run (or a limitation is stated), docs are updated, no secrets or fabricated claims are introduced, the reusable workflow contract is clear, and security gates cannot be trivially bypassed by caller inputs.
