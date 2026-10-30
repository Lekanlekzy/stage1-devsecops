# Four-stage DevSecOps maturity roadmap

## Stage 1 — Quick secure CI/CD
- GitHub Actions with GitHub-hosted runners.
- A central repository provides reusable workflows; application repositories call them.
- Keep CI in `reusable-app-ci.yml` and application deployment in `reusable-app-cd.yml`. Callers can use CI alone or sequence CI then CD with `needs: ci`; optional image publication remains inside CI.
- Validate open PRs; after a PR merges into the default branch, rerun CI on its exact merged revision, package it, then deploy and verify health. The sample does not deploy on `push` or manual dispatch.
- Support profiles: Java/Maven, Java/Gradle, Python, Node.js/TypeScript, .NET, Go.
- Tests, baseline quality/security checks, container build/scan, and optional publishing to one non-production registry.
- Deploy a versioned application package to Azure App Service in non-production, starting with Node. Verify the package checksum, application health, and deployed commit. Containers remain optional.
- Provide manual rollback with the previous retained package and record the deployment URL and version. Keep publication and deployment opt-in.
- Bootstrap the first cloud target using its portal or documented setup commands; infrastructure as code remains Stage 3A.

Stage 1 completion requires a working path from commit to a running application. The two reusable workflows implement CI with optional image publication and Node packaging, followed by optional package deployment and health checks in CD. Azure account setup and real cloud deployment/rollback verification remain pending. The ZIP is not currently runtime-tested before deployment. See [ADR-007](../decisions/ADR-007-stage-1-managed-cloud-delivery.md), [ADR-008](../decisions/ADR-008-separate-application-deployment-workflow.md), and [ADR-009](../decisions/ADR-009-deploy-exact-merged-revision.md).

## Stage 2 — Standardized and traceable delivery
- Workflow versioning and controlled adoption across repositories.
- SBOMs, build provenance/attestations, artifact digest traceability, independent verification, release-policy evidence, and controlled promotion.

These controls are assigned to Stage 2 by the incremental architecture. Stage 1 checksums detect different package bytes; signed provenance and verification will provide evidence of how and by whom those bytes were built.

## Stage 3A — Infrastructure as code
- Introduce Terraform or a selected alternative through a separate reusable infrastructure workflow.
- Validate, plan, scan, review, approve, and apply; protect remote state and credentials.

## Stage 3B — Application deployment and GitOps
- Standardize and extend Stage 1 deployment automation as environments and applications grow.
- Introduce Helm chart validation/package/versioning and Kubernetes manifest/policy checks.
- Evaluate Argo CD vs Flux for GitOps reconciliation. Helm packages application resources; GitOps controllers reconcile desired state.

## Stage 4 — Enterprise hardening and governance
- Add ephemeral self-hosted runner pools only where needed; compare VMs vs Kubernetes-based runners/ARC.
- Evaluate HashiCorp Vault vs cloud-managed secret managers; use OIDC/short-lived credentials where supported.
- Isolate build execution and provenance-signing authority; implement enterprise multi-registry policy, replication, audit, runtime verification, observability, and disaster recovery.
- Compare GitHub Actions with Jenkins, Tekton, GitLab CI/CD, Azure Pipelines, or other relevant CI engines against concrete requirements.

## SLSA note
Long-term design targets are SLSA Source L4 and Build L3. These are targets, not claims of conformance. Each applicable requirement must be implemented and assessed with supporting evidence before claiming a level.
