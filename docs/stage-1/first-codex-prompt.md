# First Codex prompt — Stage 1 planning

> Bootstrap reference. Current `AGENTS.md` and ADRs supersede this prompt. Main-protection validation is intentionally disabled as of 2026-10-21; preserve that pause until the user requests activation.

Paste this into Codex while the repository is open.

```text
Read AGENTS.md, README.md, docs/stage-1/implementation-brief.md,
docs/stage-1/acceptance-criteria.md, docs/stage-1/default-branch-protection.md,
docs/architecture/four-stage-roadmap.md, and the current ADRs.

This repository is the central reusable-workflow repository. Application repositories
must call its versioned workflow_call interfaces and keep only thin callers plus
application-specific configuration.

Stage 1 uses GitHub Actions and GitHub-hosted runners for Java/Maven, Java/Gradle,
Python, Node.js/TypeScript, .NET/C#, and Go. Plan mandatory format/lint/tests,
SonarQube Cloud SAST and Quality Gate, Gitleaks secret scanning, OSV dependency
scanning, and optional Trivy container checks plus opt-in GHCR publication. Publication
must be separate, disabled by default, and inaccessible to untrusted pull requests.

Before editing, inspect the repository and return a plan covering the workflow contract,
all six language profiles, mandatory/optional gates, action-SHA verification, caller
configuration, Dependabot ecosystems, publication separation, local/remote tests, and
default-branch enforcement. Maintain an active main-protection validation workflow
and a same-commit consumer regression caller for pull requests to main. Do not guess
required status-check contexts or claim branch rules are active based on workflow YAML.
Recommend rulesets or classic branch protection and explain enforcement limitations.

Do not implement Stage 2, Terraform, Helm, Argo CD, Flux, Vault, self-hosted runners,
ARC, production deployment, multi-registry routing, or claim SLSA conformance. Do not
edit files, access remote services, create secrets, push commits, publish images, or
change remote repository settings until the implementation plan is approved.
```
