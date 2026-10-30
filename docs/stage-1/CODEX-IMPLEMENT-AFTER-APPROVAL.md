# Codex implementation prompt — use after plan approval

> Bootstrap reference. Current `AGENTS.md` and ADRs supersede this prompt. Main-protection validation is intentionally disabled as of 2026-10-21; preserve that pause until the user requests activation.

```text
Implement only the approved Stage 1 design in this repository. Work in small,
reviewable changes. This repository hosts central reusable GitHub Actions workflows;
application repositories call them through thin, versioned callers.

Required profile targets: Java/Maven, Java/Gradle, Python, Node.js/TypeScript, .NET/C#,
and Go. Use typed workflow_call inputs, fixed profile commands, validation, stable
job display names, minimal GITHUB_TOKEN permissions, full-SHA-pinned external Actions,
timeouts, and explicit failures.

Make SonarQube Cloud a mandatory SAST/quality gate. Require explicit project/org
configuration and pass only a project-scoped SONAR_TOKEN to its isolated scanner job.
Use Gitleaks OSS for full-history secret scanning and OSV-Scanner for dependency
vulnerabilities. Do not activate Snyk or Veracode. Keep scanner errors and mandatory
gate failures fail-closed.

Optional container checks must build and scan before an isolated publisher. Publication
defaults off, accepts only an authorized non-fork push to the caller's actual default
branch, targets GHCR, and uses packages:write only in the publisher job. The publisher
must not check out or execute application code. Verify the published digest against
the exact scanned image artifact. Do not publish an image during implementation.

Configure Dependabot only for dependency ecosystems that actually exist in the central
repository. Document application examples for Maven, Gradle, pip, npm, NuGet, Go,
Docker, and GitHub Actions. Explain that update PRs do not themselves enable security
alerts or Dependabot security updates.

Keep a main-protection validation workflow active for pull requests to main and
pushes to main. It reports results; GitHub branch rules enforce the policy. Keep a
same-commit consumer fixture and a regression caller that invokes the reusable
workflow on those events with a project-scoped Sonar test secret. Skip the
secret-backed regression for fork and Dependabot pull requests. Do not guess required
check names or configure remote branch settings. Document ruleset versus classic
branch protection, PRs, required checks, strict/up-to-date branches, linear history/no
merge commits, empty bypass, force-push/deletion restrictions, administrator limits,
and app-repo equivalent controls.

Add static contract tests and negative cases for missing configuration, invalid
profiles, scanner errors/failure behavior, unsafe publication, and optional outputs.
Run available local tests and actionlint/zizmor if installed; report missing tool or
remote checks plainly. Never claim GitHub, Sonar, package, branch-rule, or publishing
behavior passed without a real GitHub run. Do not push, create secrets, configure remote
settings, publish, deploy, or open remote PRs.
```
