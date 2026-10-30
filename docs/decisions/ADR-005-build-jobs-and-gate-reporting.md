# ADR-005: Build jobs, Sonar artifact transfer, and gate reporting

- Status: Accepted for Stage 1
- Decision date: 2026-10-21

## Context

The caller's build scripts execute untrusted application code. Sonar analysis needs a project-scoped token, and Java analysis additionally needs compiled classes. GitHub-hosted jobs have separate workspaces. The aggregate gate must report actual job results clearly while still failing closed.

## Decision

Keep configuration validation in the `Validation` job. Resolve build paths and execute profile commands in `Build and test`. Pass the Java bytecode directory as that job's output and transfer the compiled classes to the separate Sonar job through a same-run artifact retained for one day. Keep application build scripts outside the job that receives the Sonar token. Existing archive extraction guards remain mandatory.

For Python, require pytest-cov in the `[dev]` extra and generate `coverage.xml` during build/tests with `pytest --cov --cov-report=xml:coverage.xml`. Application configuration declares relative coverage paths and source directories. Transfer that same-run report to the application directory in the Sonar job and import it with the centrally supplied scanner argument `-Dsonar.python.coverage.reportPaths=coverage.xml`. Do not rerun tests or install application dependencies with the Sonar token. Other profiles retain their existing test commands; this change establishes only the Python coverage handoff.

Write the aggregate gate's expected status, actual status, and verdict for every job to `GITHUB_STEP_SUMMARY` before returning its status. Require success for mandatory and requested optional jobs, and skipped for unrequested optional jobs. Reporting a table must not turn a failed, cancelled, skipped mandatory, or unknown result into success. Gitleaks is advisory under ADR-003: its aggregate row says `Advisory (see scan logs)` without classifying findings or scan errors. Checkout/configuration failures remain blocking.

Keep one aggregate table in the Stage 1 reusable workflow. It covers validation/build/scans, optional container checks, and optional image publication. ADR-006 documents the caller permission ceiling and the separate publisher job within that workflow.

## Alternatives and trade-offs

- A combined build/Sonar job avoids transfer but leaves the token on a runner where application code has executed; rejected.
- Rebuilding in the Sonar job executes application build scripts in the job with the token; rejected.
- A dependency cache is intended for reusable inputs and does not provide the same explicit per-run handoff of build output; retain artifacts.
- An external artifact repository adds storage configuration and credentials without a Stage 1 requirement; defer.
- Shared self-hosted runner storage is outside Stage 1 and weakens job isolation; defer.

## Consequences

- Java calls transfer compiled classes; Python calls transfer their coverage report. Both use same-run artifacts and preserve the separate Sonar job. Coverage paths must resolve against the application's checkout rather than the original runner's absolute path.
- Job IDs and display names change from `quality` / `Application quality` to `build-and-test` / `Build and test`; consumers must use observed GitHub status contexts after a successful run.
- Local tests execute the actual aggregate-gate script across successful, skipped, cancelled, failed, and unknown job results. A GitHub run is still required to verify artifact delivery and summary rendering.

See [GitHub's workflow artifact guidance](https://docs.github.com/en/actions/tutorials/store-and-share-data) for passing files between jobs.
