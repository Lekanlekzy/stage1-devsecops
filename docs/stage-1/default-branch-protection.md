# Stage 1 — Default-branch protection setup and verification

## Status

The central main-protection workflow is intentionally disabled at the user's request, with its definition retained at `.github/workflows/main-protection.yml.disabled`. GitHub does not execute that file. Restore the `.yml` extension only when activation is requested; the definition then runs the local contract suite, actionlint, and zizmor for pull requests targeting `main` and pushes to `main`. It reports results and does not enforce branch policy. No GitHub ruleset or classic protection settings have been changed from this workspace, and hosted enforcement remains unverified. Actual emitted check contexts remain unknown.

## Enforcement versus validation

There are two distinct controls:

1. An Actions workflow validates repository content and reports check results.
2. A GitHub repository ruleset or classic branch protection rule enforces merge and branch-update restrictions.

An Actions workflow alone cannot block direct pushes, force pushes, or deletion. Apply equivalent rules to the central repository and each application repository, targeting each repository's actual default branch. Explicitly target both `main` and `master` only if both are intentionally maintained.

## Recommendation: repository ruleset

Use an active repository ruleset for the default branch where the GitHub plan and organization policy support it. Rulesets provide explicit enforcement state, branch targeting, policy layering, and an auditable bypass list. Keep that list empty so administrators are subject to the rules. Classic branch protection is a fallback when rulesets are unavailable or the organization already manages the equivalent legacy controls; in classic settings enable **Do not allow bypassing the above settings**.

Neither option prevents sufficiently privileged organization or enterprise owners from changing or deleting the policy itself. Limit ruleset administration to a small governance group and use the organization's audit controls. GitHub platform-owner privileges cannot be removed by repository settings.

| Requirement | Ruleset / branch setting |
|---|---|
| Require a pull request | Require a pull request before merging. This blocks ordinary direct updates through GitHub's protected branch path. |
| Require mandatory checks | Require status checks to pass; select only the exact successful check contexts displayed by GitHub after a real run. |
| Require up-to-date branch | Enable strict status checks / require branches to be up to date with the target branch before merging. |
| Linear history | Require linear history; disable merge commits in the repository's allowed merge methods. |
| No bypass | Ruleset bypass list empty. For classic protection, enable the administrator bypass restriction above. |
| No force pushes | Leave force-push allowance disabled. |
| No deletion | Leave branch deletion allowance disabled. |

## Safe activation order

1. When the user requests activation, rename `.github/workflows/main-protection.yml.disabled` to `main-protection.yml`, then push the central workflows and acceptance suite through the normal reviewed change process. If the GitHub repository uses a default branch other than `main`, update the workflow branch filters to match it.
2. Configure the existing `SONAR_TOKEN` in repository Actions settings, ensuring it can analyze `Lekanlekzy_stage1-devsecops` in the fixed `lekanlekzy` Sonar organization. The regression caller sets that project key explicitly and needs no project-key variable. Then run the regression caller successfully from an internal pull request. Fork and Dependabot pull requests skip the secret-backed caller.
3. Run `Main protection validation` successfully on a pull request.
4. Open the Actions runs and record the exact emitted context(s). For each consuming application, run its caller workflow successfully and record that caller's own mandatory status check. Do not rely on a central repository check to validate application code.
5. In repository Settings, create an active default-branch ruleset (or classic protection fallback), require PRs, choose the exact successful status checks, require strict/up-to-date status, require linear history, keep bypass empty, and disallow force pushes and deletion.
6. Repeat for each consuming application repository, requiring its application caller check(s).
7. Verify on GitHub that direct push, failed-check merge, stale-branch merge, force push, branch deletion, and administrator bypass are rejected. Confirm only squash/rebase methods remain if linear history is required.

Check names are not guessed in this runbook. The local workflow job display names are `Main protection checks`, `Python consumer regression`, and `Stage 1 Required Checks`, but GitHub may show caller workflow/job prefixes or reusable-workflow contexts. Make only the exact context mandatory after it appears in the ruleset selector from a successful real run. Keep workflow and job names stable after activation.

## Limitations

The local repository has a configured Git remote, but its hosted default branch, plan, and administrator settings have not been queried. No status name has been observed in GitHub, and remote branch protection remains unverified. The retained workflow definition targets `main`; confirm that against the hosted repository's actual default branch before activation. GitHub rules cannot prevent a sufficiently privileged platform owner from modifying the settings, so governance and audit of policy administration remain necessary.
