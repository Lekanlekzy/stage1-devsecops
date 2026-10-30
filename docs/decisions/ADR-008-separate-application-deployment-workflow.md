# ADR-008: Separate application deployment from CI

- Status: Accepted; local workflow refactor implemented, GitHub/Azure execution verification pending
- Decision date: 2026-10-22

## Context

Stage 1 added non-production Azure App Service deployment to the CI reusable workflow. The user requested a separate deployment workflow so applications can use CI alone, or call CI and then CD when delivery is wanted. The earlier decision to keep optional GHCR image publication inside CI remains in force.

## Decision

Keep builds, tests, scans, optional container checks, and optional GHCR publication in `reusable-app-ci.yml`. Replace CI's deployment switch with `package_app: false` by default. Only Node currently supports packaging: its fixed `package:ci` script creates a ready-to-run directory, and the central build stamps the source revision and produces a ZIP and SHA-256 without Azure credentials.

Expose `app_package_artifact_id`, `app_package_sha256`, and `app_revision` only through CI's successful required-checks job. A thin application caller invokes `reusable-app-cd.yml` in a second job with `needs: ci`, passing those outputs plus Azure resource and identity configuration. CD accepts trusted closed merged PRs into the actual default branch, downloads the exact same-run artifact, and verifies its checksum and packaged revision before Azure authentication. [ADR-009](ADR-009-deploy-exact-merged-revision.md) records the merge trigger and exact-revision guards, superseding the initial push-triggered design. CD has no checkout or application build commands. Only the CD caller/deployment job permits OIDC `id-token: write`; CI retains its existing permission ceiling and named Sonar secret.

CD retains the fixed `non-production` GitHub Environment, deployment concurrency, pinned Azure Actions, five-minute health/revision verification, and manual rollback runbook. CI's aggregate table reports CI and optional image results. CD reports deployment and health separately and exposes its URL only after health succeeds.

## Alternatives and trade-offs

- Keep deployment as a conditional CI job: fewer workflow files, but every CI caller must allow OIDC and the CI interface contains Azure configuration. The user requested the separate workflow.
- Rebuild in CD: avoids package transfer but executes application scripts near cloud credentials and can produce a different release. Use the CI package instead.
- Start CD through `workflow_run`: allows independent runs but adds cross-run artifact and trust handling. Two reusable calls in the same caller run keep sequencing and artifact identity explicit.
- Split GHCR publication too: outside this request and contrary to the existing Stage 1 publication decision. Keep it in CI.

## Consequences and validation

- Applications can call CI without Azure configuration or OIDC permission. Deployment is selected by adding the second reusable call.
- The caller must preserve `needs: ci` and pass CI's outputs. Repository administrators still control the caller; default-branch restrictions and the protected non-production Environment remain required remote controls.
- Package identity verifies the bytes and release revision; Stage 1 does not claim signed provenance or independent attestation verification.
- Existing app health behavior is unchanged. It checks server availability, expected release identity, built assets, and the home page; it does not provide browser or business end-to-end testing.
- Local and remote validation evidence must identify the workflow version checked. Tests run before this split do not establish that the new contract works on GitHub. Azure deployment and rollback remain unverified until real runs succeed.
