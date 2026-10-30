# ADR-002: Default-branch enforcement and check activation

- Status: Accepted for Stage 1; remote enforcement deferred
- Decision date: 2026-10-18

## Context

Actions workflows report validation results. GitHub branch rulesets or classic branch protection enforce PR-only changes and required merge controls. A Git remote is configured, but no hosted repository settings or Actions runs have been queried, so the actual default branch, successful check contexts, and available GitHub settings remain unverified.

## Decision

Prefer an active repository ruleset targeting the actual default branch, with an empty bypass list. Use classic branch protection only when rulesets are unavailable or the organization requires that mechanism; enable **Do not allow bypassing the above settings**. Require PRs, mandatory successful status checks, strict/up-to-date checks, linear history with merge commits disabled, and disabled force pushes/deletion. Apply equivalent policy to each application repository, requiring its own caller workflow check.

Keep a central validation workflow active on pull requests targeting `main` and pushes to `main`, along with a same-commit regression caller for the reusable workflow. These workflows report validation results only. Do not select or document a required context based on an assumed name. Run the central and application workflows successfully, copy the exact context from GitHub's selector, then activate the corresponding ruleset.

### Temporary operating exception — 2026-10-21

The user requested that central main-protection validation remain disabled for now. Its definition is retained as `.github/workflows/main-protection.yml.disabled`; it must not be automatically reactivated to satisfy the baseline or local tests. This pauses the central contract/actionlint/zizmor workflow while the reusable-workflow regression caller remains active. No remote branch-rule settings were changed. The active-validation acceptance item remains incomplete until activation is requested and verified.

Keep bypass lists empty. Repository settings cannot prevent sufficiently privileged organization or enterprise owners from changing ruleset administration; restrict those permissions and audit changes. No Actions job receives administrative permissions to manage rulesets.

## Alternatives

- **Rulesets (selected):** better explicit enforcement and bypass governance, with reusable targeting and policy layering. Requires a GitHub plan/settings that supports repository rulesets.
- **Classic branch protection:** widely available and acceptable where rulesets are unavailable, but configured per branch/repository and depends on the administrator bypass switch.
- **Workflow-only validation:** rejected as an enforcement mechanism because it cannot block direct branch updates.

## Consequences

- Policy remains a documented requirement until it is enabled and verified on GitHub.
- Exact required status contexts are intentionally pending a successful run.
- Strict checks can require a PR to rerun after the base branch advances.
- Platform owners may retain non-removable authority to change or deactivate repository policy.
