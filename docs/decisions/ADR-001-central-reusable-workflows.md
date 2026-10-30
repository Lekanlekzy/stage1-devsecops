# ADR-001: Central reusable GitHub Actions workflows

- Status: Proposed for Stage 1
- Decision date: 2026-10-18

## Context
Application teams need a common pipeline without copying workflow implementation into every repository. Security controls and supported language profiles should be maintained centrally and adopted through controlled versions.

## Decision
Use a dedicated central repository that exposes GitHub Actions reusable workflows through `workflow_call`. Application repositories call those workflows at a controlled tag or commit SHA, with only a thin caller workflow containing app-specific inputs.

## Alternatives
- Copy/paste workflow files: simplest at first, but drift and uneven security controls grow over time.
- Composite actions only: useful for reusable steps, but they do not provide the complete multi-job workflow contract by themselves.
- One centrally triggered pipeline dispatch: can centralize orchestration but complicates source context, permissions and feedback for the initial use case.
- Jenkins/Tekton/GitLab/Azure Pipelines: candidates for a future CI-engine review; not adopted for Stage 1.

## Consequences
- Central updates can benefit multiple applications, but changes need compatibility and versioning discipline.
- Private reusable-workflow repositories require correct Actions access settings in the called repo and callers.
- Callers must provide sufficient permissions; reusable workflows cannot elevate permissions beyond the caller.
- Each caller needs a thin workflow and tests of the contract.
- GitHub-specific workflow logic may require a separate implementation if a different CI engine is later selected.
