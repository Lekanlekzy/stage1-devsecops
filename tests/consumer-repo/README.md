# Regression consumer fixture

This directory is a small application-repository fixture used to exercise the
central `workflow_call` contract. The active caller is
`.github/workflows/reusable-app-ci-regression.yml` at the repository root. It
calls the reusable workflow from the same commit, so a pull request that changes
`reusable-app-ci.yml` tests that exact revision against this Python project.

Before the real GitHub regression can pass, configure these settings in the
central repository:

- Actions variable `SONAR_REGRESSION_ORGANIZATION` with the SonarQube Cloud
  organization key.
- Actions variable `SONAR_REGRESSION_PROJECT_KEY` with the dedicated regression
  project key.
- Actions secret `SONAR_REGRESSION_TOKEN` scoped to that Sonar project.

The regression caller runs on pull requests targeting `main`, pushes to `main`,
and manual dispatch. Fork pull requests and Dependabot pull requests skip the
secret-backed caller; the central static validation workflow still runs. The
reusable workflow's mandatory Sonar gate remains fail-closed for normal
application callers.

This is a fixture inside the central repository, not a second remote GitHub
repository. A separate remote consumer repository can be added when the
organization is ready to provision one.
