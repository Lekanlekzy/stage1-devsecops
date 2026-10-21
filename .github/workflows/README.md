# Workflow directory

`reusable-app-ci.yml` is the central application-facing workflow. It declares only `workflow_call`; application repositories call it through thin workflows and pass named inputs plus the required `SONAR_TOKEN` secret.

`reusable-app-ci-regression.yml` calls that workflow from the same commit against the Python fixture in `tests/consumer-repo/python-app`. It runs for pull requests targeting `main`, pushes to `main`, and manual dispatch. The Sonar regression variables and project-scoped token must be configured in repository Actions settings. Fork and Dependabot pull requests skip the secret-backed call.

`main-protection.yml.disabled` is intentionally disabled at the user's request. GitHub does not load this filename as a workflow. When activation is requested, restoring the `.yml` extension enables the retained definition for the local contract suite, actionlint, and zizmor on pull requests targeting `main` and pushes to `main`. GitHub rulesets or classic branch protection enforce branch policy separately; remote settings are unchanged.

See `docs/stage-1/reusable-workflow-contract.md`, `docs/stage-1/action-pins.md`, and `docs/stage-1/default-branch-protection.md` for caller requirements, verified tool pins, and repository settings.
