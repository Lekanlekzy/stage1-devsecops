# ADR-006: Single Stage 1 workflow with minimum job permissions

- Status: Accepted for Stage 1; GitHub integration verification pending
- Decision date: 2026-10-21

## Context

GitHub rejected the OSV nested reusable workflow because its scan job unconditionally requests `security-events: write`, even when `upload-sarif` is false. Another run reported missing `actions: read`. A called workflow cannot elevate the caller's permission ceiling. A direct-CLI replacement was attempted, but the user requested restoration of the OSV reusable workflow and clarified that required read/write scopes should be granted rather than removing the integration to avoid them. GitHub also validates the permission requirement of a conditional publisher, even when publication is disabled. The user requires publication to remain part of the single Stage 1 reusable workflow.

## Decision

Restore `google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@c7c7bcb0773cc4678a674ada03a66cc5c4325476`, whose pinned workflow uses scanner v2.6.0. Use the full-scan wrapper for all current dependency findings on pull requests, pushes, and manual runs, rather than the PR wrapper's comparison against a base revision. Scan recursively from the repository root with `fail-on-vuln: true` and `upload-sarif: false`. Fix scanner arguments to `--recursive --no-ignore --no-call-analysis=all --config=/dev/null ./`, including ignored files, disabling call analysis, and overriding caller suppressions with empty TOML configuration on Ubuntu. Grant its required `actions: read`, `contents: read`, and `security-events: write` scopes. The security-event write request remains part of the upstream job definition when upload is disabled.

Keep build/tests, scans, container checks, and optional publication in `reusable-app-ci.yml`. The `publish_image` input defaults to false and requires `run_container_checks: true` when enabled. Preserve `image_uri` and `image_digest` as actual publication outputs, empty when publication is disabled. One required-checks table covers every mandatory gate and both optional jobs.

This single-workflow decision applies to CI and optional image publication. Application ZIP deployment added later lives in a separate `reusable-app-cd.yml`, as requested by the user and recorded in [ADR-008](ADR-008-separate-application-deployment-workflow.md). CI callers do not gain OIDC permission through that addition.

Use empty workflow permission defaults and explicit job permissions: validation, build/tests, Sonar, and container jobs receive only `contents: read`; the official Gitleaks Action job receives `contents: read` and `pull-requests: read` for PR commit discovery; the OSV dependency job receives its three required scopes; the publisher receives only `packages: write`; and the summary receives no permissions. Same-run artifact actions use runtime credentials without adding an `actions: read` API-token requirement.

Every caller declares `actions: read`, `contents: read`, `pull-requests: read`, `security-events: write`, and `packages: write` as the ceiling for the complete called workflow, including callers with publication disabled. This permits the selected OSV integration and guarded publisher without issuing package-write tokens to build/test/scan jobs. The publisher requires a non-fork push to the caller's actual default branch, every mandatory gate and image scan to pass, the caller owner's GHCR namespace, and the fixed `non-production` environment. It has no checkout or Sonar token, verifies archive and image identity, and publishes the exact scanned image.

Fix the Sonar organization to `lekanlekzy`. The same-repository regression explicitly passes the existing `SONAR_TOKEN`, authorized for its configured regression project. External repositories must explicitly pass an authorized secret available in their own repository; a secret stored only in the central repository is not automatically available through a reusable call. Where applicable, an organization secret with selected repository access can provide the token.

## Alternatives and trade-offs

- Direct CLI scanning: can use only `contents: read` and avoid the upstream security-event permission, but the user chose to restore the reusable integration and grant its declared requirements. This supersedes the earlier CLI decision.
- Move publication to a separate reusable workflow: would allow strictly read-only caller ceilings, but the user explicitly rejected that split for Stage 1.
- Combine building and publishing in one job: would expose a package-write token while application build code executes; rejected.
- Use a long-lived registry secret to avoid the job-token ceiling: adds credential management and distribution; rejected.

## Consequences and validation

- All callers need the OSV scopes, Gitleaks PR-read scope, and package-write ceiling, even for validation-only runs. Runtime job permissions and publication conditions enforce the boundary within the shared workflow. Review central workflow changes and adopt an immutable release reference when available.
- The wrapper SHA does not make its version-tagged scanner container immutable, and the upstream jobs lack explicit timeouts. These upstream limitations remain visible rather than being described as centrally enforced controls.
- The fixture includes a requirements file matching its direct dev dependencies because this OSV release does not extract them from `pyproject.toml` alone. Real applications must provide scanner-supported dependency sources; missing sources fail the scan.
- Permission checks compare caller ceilings against the central job declarations and selected upstream requirements. Only the publisher gets package-write access; only OSV gets security-event write access. Gate checks cover failure, cancellation, skipped, and successful results, including optional publication.
- A historical direct-CLI smoke test returned vulnerability findings for a resolved Pygments dependency. This is not a passing scan or validation of the restored reusable workflow. GitHub execution of the updated workflow, Sonar token access, and GHCR publication remain unverified.

Sources: [pinned full OSV workflow](https://github.com/google/osv-scanner-action/blob/c7c7bcb0773cc4678a674ada03a66cc5c4325476/.github/workflows/osv-scanner-reusable.yml), [GitHub permission ceilings](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations), [GitHub reusable workflow secrets](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#passing-inputs-and-secrets-to-a-reusable-workflow), [pinned artifact action](https://github.com/actions/download-artifact/blob/9000827ccba6bdab643e8b6fd33ac0654aef8333/action.yml).
