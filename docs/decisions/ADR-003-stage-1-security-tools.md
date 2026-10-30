# ADR-003: Stage 1 security tool baseline

- Status: Accepted for Stage 1
- Decision date: 2026-10-18

## Context

The central workflow needs repeatable quality/SAST, secret, dependency, and optional image checks across six language profiles. The baseline runs on GitHub-hosted runners and grants each job the scopes required by its selected integration. Sonar, OSV, and requested Trivy gates fail closed. At the user's request, Gitleaks findings and scan errors are advisory.

## Decision

- Require SonarQube Cloud analysis and its Quality Gate for all six profiles. Fix the organization to `lekanlekzy`, retain the caller's target project key, and explicitly pass `SONAR_TOKEN` with analysis permission for that project. Isolate the Sonar scanner from the job that executes project build/test scripts.
- Use the official Gitleaks Action v3 pinned by full commit SHA with scanner v8.30.0 and a central config extending its default rules. Retain `fetch-depth: 0`. The Action selects changed-commit ranges for PR/push events, so an advisory follow-up uses its installed binary to scan full history with redacted verbose output. Enable the native Action summary; disable comments and report-artifact uploads. Grant `contents: read` and `pull-requests: read` for PR commit discovery.
- Keep Gitleaks simple: no project-ID exception, result classifier, or custom findings outputs. Both scan steps use `continue-on-error: true`. Findings and Action/scanner errors continue CI; checkout and configuration errors still block. The aggregate table labels the job `Advisory (see scan logs)` and does not claim the scan was clean.
- Use Google's full OSV reusable workflow, pinned to the verified commit recorded in `action-pins.md`, as the mandatory dependency vulnerability gate with scanner v2.6.0. Fail on all current findings or scanner errors without uploading SARIF. ADR-006 records the required nested permissions and the user's decision to restore this integration after a direct-CLI experiment.
- Use Trivy for optional image scanning before publication, failing on HIGH/CRITICAL OS and library findings.
- Keep Snyk and Veracode inactive; they can be evaluated later if licensing and organization requirements justify them.

## Alternatives and trade-offs

- GitHub Advanced Security CodeQL, secret scanning, and dependency review may integrate well with GitHub but availability depends on plan, repository visibility, and organization settings. They are optional and do not replace the configured OSV/Gitleaks/Sonar checks in this Stage 1 contract.
- Snyk/Veracode could provide additional proprietary analysis but introduce licensing, account/token, data-flow, and policy choices not yet made.
- Direct Gitleaks CLI/container scanning remains an alternative, but the user requested the official Action and a preference for maintained Actions for future tool integrations. Keep the full-history follow-up because the Action's event-based scan range alone does not meet the Stage 1 baseline. Verify each Action's full SHA, permissions, compatibility, and failure behavior before adoption. See the [official Action documentation](https://github.com/gitleaks/gitleaks-action).
- Blocking findings, project-specific exceptions, and custom exit-code classification were superseded by the user's simpler advisory policy. Gitleaks findings or scan failures no longer block merge or optional publication; reviewers use the native summary and logs.
- SARIF upload would improve GitHub UI reporting. It remains disabled, although the pinned upstream reusable workflow still declares `security-events: write`; callers must allow that scope for GitHub permission validation. Direct CLI scanning can avoid this scope but was superseded by the user's choice to restore the reusable workflow.

## Consequences

- SonarQube Cloud account/project setup, plan selection, and a token are prerequisites. Fork PRs do not receive that secret and fail closed until an authorized scan can run.
- PR/push runs perform the Action's range scan plus a full-history scan; the latter may increase scan time. The Action pin and fixed scanner version do not independently verify the downloaded scanner archive digest. GitHub execution remains unverified.
- The active tool versions and action pins must be reviewed and updated through pull requests; Dependabot covers GitHub Actions references.
- This design does not claim comprehensive source coverage beyond the six documented profile/tool combinations, produce SBOMs or provenance, or claim SLSA conformance.
