# ADR-009: Deploy the exact revision produced by a merged PR

- Status: Accepted; local implementation added, GitHub/Azure integration verification pending
- Decision date: 2026-10-22

## Context

The user wants PR validation followed by a release built from merged `main`, separate deployment, and post-deployment health verification. Deployment must not start on arbitrary pushes. A successful pre-merge PR run does not by itself validate the final revision that landed in the default branch.

## Decision

The Node sample caller listens to `pull_request` types `opened`, `synchronize`, `reopened`, and `closed` for `main`, plus manual dispatch for validation only. It has no push trigger. Unmerged closed PRs skip. PR calls require a same-repository head and a triggering actor other than `dependabot[bot]`; mandatory Sonar and OSV gates remain blocking. A human merging a Dependabot PR is evaluated under those event guards rather than excluded merely because the PR author is a bot.

Only a closed merged PR enables `package_app`. CI explicitly checks out `github.sha`, verifies it equals the event's `merge_commit_sha`, reruns build/tests/scans against that merged revision, then packages it. On this post-merge event Sonar explicitly sets `sonar.branch.name` to the PR base branch to analyze the merged branch. The rationale follows [Sonar staff guidance for closed PR analysis](https://community.sonarsource.com/t/sonarcloud-interprets-closed-pr-as-branch-analysis/59595/6); the configured current integration still requires a real run.

The caller invokes separate CD with `needs: ci` and the same-run package outputs. The deployment chain enforces the closed merged event, actual default base branch and ref, matching event/caller repositories, a non-fork repository, same-repository PR head, and event SHA equal to the PR merge SHA. CD independently repeats those event/repository/revision checks, verifies ZIP checksum and manifest revision before OIDC login, and deploys without rebuilding. Manual dispatch and direct pushes do not deploy. Caller concurrency cancels superseded unmerged validation; merged release runs are not treated as superseded PR builds. Optional GHCR publication retains its separate trusted-push-only contract inside CI.

## Alternatives and trade-offs

- Deploy on every default-branch push: simpler trigger, but does not express the requested merged-PR release policy.
- Reuse the pre-merge PR artifact: avoids repeating CI but can package a revision different from the final merged result. Rerun CI and package the exact merged SHA.
- Rebuild in CD: risks different bytes and application execution near cloud credentials. Transfer the CI package instead.

## Consequences and limits

- Merging starts another CI run before delivery, adding time in exchange for checking the deployed revision. A failure blocks CD even if pre-merge validation passed.
- Repository branch rules and the protected `non-production` Environment remain required remote controls. YAML does not establish those settings, and skipped unauthorized calls do not establish a successful quality result.
- Source tests and the production build precede packaging, but the final ZIP is not currently started and runtime-tested before upload. CD checks health/revision and the home page after deployment; browser/end-to-end coverage remains separate.
- SHA-256 and the manifest identify bytes/revision within the run. SBOMs, signed provenance/attestations, and independent verification remain Stage 2 work under the roadmap and AGENTS instructions.
- Earlier static/test results are historical until checks are rerun against this revision. Actual GitHub, Sonar, Azure deployment, and rollback verification remain pending.
