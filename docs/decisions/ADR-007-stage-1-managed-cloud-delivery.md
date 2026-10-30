# ADR-007: Stage 1 deployment to a managed cloud service

- Status: Accepted; implementation added, Azure integration verification pending
- Decision date: 2026-10-22

## Context

The original roadmap named Stage 1 CI/CD but implemented CI and optional GHCR publication, deferring application deployment to Stage 3B. The user clarified that Stage 1 should include working delivery and chose cloud hosting for the simplest initial deployment.

## Decision

Use Azure App Service code deployment in non-production, starting with the separate `simple_web_app` Node application. Preserve the Python regression fixture and keep Docker/GHCR/Trivy optional. Build a versioned application ZIP without cloud credentials, stamp its commit, and verify its SHA-256 before deployment. Six-profile CI does not imply six-profile code deployment; Node is the initial supported deployment adapter.

Keep deployment opt-in, limited to trusted merged PRs into the actual default branch, and separate from application build execution. Use the official SHA-pinned Azure login and web-app deployment actions with OIDC and an identity scoped to the target app. Only the CD caller and deployment job permit `id-token: write`; CI has no Azure configuration or OIDC permission. [ADR-008](ADR-008-separate-application-deployment-workflow.md) records the separate reusable CD workflow, and [ADR-009](ADR-009-deploy-exact-merged-revision.md) supersedes push-triggered deployment with exact merged-revision delivery. Existing image publication remains inside the CI reusable workflow with its own push-only guard.

Verify `/healthz` returns HTTP 200, `status: ok`, and the expected commit, then verify the home page. Retry during startup and fail CD on an unhealthy or stale revision. The sample also checks built asset presence; browser/user-journey tests remain separate. Retain packages for 30 days and document manual rollback without rebuilding; automatic rollback is deferred. Bootstrap the first Azure target through its portal or documented commands. No cloud resources have been created by this implementation.

## Alternatives and trade-offs

- Defer all deployment to Stage 3B: leaves Stage 1 without the working CI/CD path the user requested.
- Manage a virtual machine: adds host maintenance and deployment setup to the first delivery example.
- Introduce Terraform, Kubernetes, Helm, or GitOps now: expands Stage 1 beyond its agreed incremental scope. Stages 3A and 3B will automate provisioning and standardize deployment as the platform grows.

## Consequences

- The workflow can deploy Node application packages and verify health. The [runbook](../stage-1/azure-app-service.md) documents setup and manual rollback; actual Azure deployment and rollback still require verification.
- The sample frontend uses a small Node server for static assets and health, without production npm dependencies. Runtime configuration and packaging are application-specific.
- Azure account access, resource settings, federated identity, and operating costs must be established before the first deployment. App Service code deployment avoids requiring registry credentials for this path.
- Existing Sonar/OSV/Trivy gate behavior and advisory Gitleaks behavior remain unchanged.
