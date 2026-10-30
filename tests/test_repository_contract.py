"""Local, dependency-free acceptance checks for the central workflow contract."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import textwrap
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "reusable-app-ci.yml"
WORKFLOW = WORKFLOW_PATH.read_text(encoding="utf-8")
ACTIVE_WORKFLOWS = "\n".join(
    path.read_text(encoding="utf-8")
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml"))
)
ACTION_PINS = (ROOT / "docs" / "stage-1" / "action-pins.md").read_text(encoding="utf-8")


def publication_allowed(
    *,
    requested: bool,
    container_checks: bool,
    event: str,
    ref: str,
    default_branch: str,
    repository: str,
    event_repository: str,
    repository_is_fork: bool,
) -> bool:
    """Mirror the documented publish preconditions for negative acceptance cases."""
    return (
        requested
        and container_checks
        and event == "push"
        and bool(default_branch)
        and ref == f"refs/heads/{default_branch}"
        and repository == event_repository
        and not repository_is_fork
    )


def profile_configuration_valid(
    profile: str,
    files: set[str],
    *,
    node_scripts: set[str] | None = None,
    dotnet_projects: int = 0,
    dotnet_project_selected: bool = False,
) -> bool:
    """Expected negative-case contract for required project files and scripts."""
    required_files = {
        "java-maven": {"pom.xml"},
        "java-gradle": {"gradlew", "build.gradle"},
        "python": {"pyproject.toml"},
        "node": {"package.json", "package-lock.json"},
        "go": {"go.mod"},
    }
    if profile == "dotnet":
        return dotnet_project_selected or dotnet_projects == 1
    if profile not in required_files or not required_files[profile].issubset(files):
        return False
    if profile == "node":
        required = {"lint", "format:check", "build", "test:ci", "typecheck"}
        return required.issubset(node_scripts or set())
    return True


class WorkflowContractTests(unittest.TestCase):
    def test_all_six_profiles_have_fixed_commands_and_prerequisites(self) -> None:
        profile_markers = {
            "java-maven": ("pom.xml", "spotless:check", "checkstyle:check", "verify"),
            "java-gradle": ("gradlew", "build.gradle", "./gradlew --no-daemon check"),
            "python": ("pyproject.toml", "ruff check .", "ruff format --check .", "pytest"),
            "node": ("package-lock.json", "npm run lint", "npm run format:check", "npm run test:ci"),
            "dotnet": ("dotnet_project", "dotnet format", "dotnet test"),
            "go": ("go.mod", "gofmt -l", "go vet ./...", "go test ./..."),
        }
        for profile, markers in profile_markers.items():
            with self.subTest(profile=profile):
                self.assertIn(profile, WORKFLOW)
                for marker in markers:
                    self.assertIn(marker, WORKFLOW)

    def test_workflow_call_has_typed_inputs_and_explicit_outputs(self) -> None:
        self.assertIn("workflow_call:", WORKFLOW)
        self.assertIn("type: boolean", WORKFLOW)
        self.assertIn("type: string", WORKFLOW)
        for input_name in (
            "language",
            "working_directory",
            "java_version",
            "python_version",
            "node_version",
            "dotnet_version",
            "go_version",
            "sonar_project_key",
            "run_container_checks",
            "publish_image",
            "package_app",
        ):
            self.assertRegex(WORKFLOW, rf"(?m)^      {re.escape(input_name)}:")
        self.assertNotIn("sonar_organization", WORKFLOW)
        self.assertIn("-Dsonar.organization=lekanlekzy", WORKFLOW)
        self.assertNotIn("GITLEAKS_LICENSE", WORKFLOW)
        self.assertIn("image_uri:", WORKFLOW)
        self.assertIn("image_digest:", WORKFLOW)
        self.assertIn("value: ${{ jobs.publish.outputs.image_uri }}", WORKFLOW)

    def test_mandatory_security_gates_fail_closed_and_use_no_inherited_secrets(self) -> None:
        self.assertIn("SONAR_TOKEN:\n        description:", WORKFLOW)
        self.assertIn("required: true", WORKFLOW)
        self.assertIn("SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}", WORKFLOW)
        self.assertIn("-Dsonar.qualitygate.wait=true", WORKFLOW)
        self.assertIn("-Dsonar.qualitygate.timeout=300", WORKFLOW)
        self.assertIn("osv-scanner-reusable.yml@c7c7bcb0773cc4678a674ada03a66cc5c4325476", WORKFLOW)
        self.assertIn("fail-on-vuln: true", WORKFLOW)
        self.assertIn("upload-sarif: false", WORKFLOW)
        self.assertIn("--no-ignore", WORKFLOW)
        self.assertIn("--no-call-analysis=all", WORKFLOW)
        self.assertIn("--config=/dev/null", WORKFLOW)
        self.assertIn("exit-code: '1'", WORKFLOW)
        self.assertIn("--redact=100", WORKFLOW)
        self.assertIn("gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e", WORKFLOW)
        self.assertIn("GITLEAKS_VERSION: '8.30.0'", WORKFLOW)
        self.assertIn("GITLEAKS_CONFIG: ${{ runner.temp }}/central-gitleaks.toml", WORKFLOW)
        self.assertIn('gitleaks git "$GITHUB_WORKSPACE" --config="$RUNNER_TEMP/central-gitleaks.toml" --redact=100 --verbose', WORKFLOW)
        self.assertIn("GITLEAKS_ENABLE_COMMENTS: 'false'", WORKFLOW)
        self.assertIn("GITLEAKS_ENABLE_UPLOAD_ARTIFACT: 'false'", WORKFLOW)
        self.assertNotIn("git --source", WORKFLOW)
        self.assertIn("useDefault = true", WORKFLOW)
        self.assertNotIn("secrets: inherit", WORKFLOW)
        self.assertEqual(len(re.findall(r"(?m)^\s*continue-on-error:\s*true\s*$", WORKFLOW)), 2)
        secret_scan = WORKFLOW.split("\n  secret-scan:\n", 1)[1].split("\n  dependency-scan:\n", 1)[0]
        self.assertEqual(secret_scan.count("continue-on-error: true"), 2)
        self.assertIn("GITLEAKS_ENABLE_SUMMARY: 'true'", secret_scan)
        self.assertNotIn("gitleaks-result", WORKFLOW)
        self.assertNotIn("ACTION_EXIT_CODE", WORKFLOW)
        self.assertNotIn("SECRET_FINDINGS", WORKFLOW)
        self.assertIn("Advisory (see scan logs)", WORKFLOW)

    def test_missing_profile_configuration_is_rejected(self) -> None:
        self.assertIn("Unsupported language profile", WORKFLOW)
        self.assertIn("requires pom.xml", WORKFLOW)
        self.assertIn("requires the Gradle wrapper", WORKFLOW)
        self.assertIn("requires pyproject.toml", WORKFLOW)
        self.assertIn("requires package-lock.json", WORKFLOW)
        self.assertIn("sonar-project.properties must be an existing file", WORKFLOW)
        self.assertIn("requires go.mod", WORKFLOW)
        self.assertFalse(profile_configuration_valid("unknown", set()))
        self.assertFalse(profile_configuration_valid("java-maven", set()))
        self.assertFalse(profile_configuration_valid("python", {"setup.py"}))
        self.assertFalse(profile_configuration_valid("node", {"package.json"}, node_scripts=set()))
        self.assertFalse(profile_configuration_valid("dotnet", set(), dotnet_projects=0))
        self.assertFalse(profile_configuration_valid("dotnet", set(), dotnet_projects=2))

    def test_gitleaks_uses_default_rules_without_project_exceptions(self) -> None:
        config_text = WORKFLOW.split("<<'TOML'\n", 1)[1].split("\n          TOML", 1)[0]
        config = tomllib.loads(textwrap.dedent(config_text))
        self.assertEqual(config, {
            "title": "Central Gitleaks baseline",
            "extend": {"useDefault": True},
        })

    def test_python_coverage_is_transferred_to_the_isolated_sonar_job(self) -> None:
        build = WORKFLOW.split("\n  build-and-test:\n", 1)[1].split("\n  secret-scan:\n", 1)[0]
        sonar = WORKFLOW.split("\n  sonar:\n", 1)[1].split("\n  container:\n", 1)[0]
        self.assertIn("python -m pytest --cov --cov-report=xml:coverage.xml", build)
        upload = build.split("- name: Upload Python coverage for Sonar analysis\n", 1)[1].split("      - name:", 1)[0]
        download = sonar.split("- name: Download Python coverage for Sonar analysis\n", 1)[1].split("      - name:", 1)[0]
        for step in (upload, download):
            self.assertIn("if: ${{ inputs.language == 'python' }}", step)
            self.assertIn("name: sonar-python-coverage-${{ github.run_id }}-${{ github.run_attempt }}", step)
        self.assertIn("actions/upload-artifact@", upload)
        self.assertIn("path: ${{ inputs.working_directory }}/coverage.xml", upload)
        self.assertIn("if-no-files-found: error", upload)
        self.assertIn("retention-days: 1", upload)
        self.assertIn("actions/download-artifact@", download)
        self.assertIn("path: ${{ inputs.working_directory }}", download)
        self.assertIn("-Dsonar.python.coverage.reportPaths=coverage.xml", sonar)
        self.assertNotIn("SONAR_TOKEN", build)
        self.assertNotIn("python -m pytest", sonar)

        fixture = ROOT / "tests/consumer-repo/python-app"
        project = tomllib.loads((fixture / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertTrue(any(dependency.startswith("pytest-cov==") for dependency in project["project"]["optional-dependencies"]["dev"]))
        self.assertEqual(project["tool"]["coverage"]["run"], {"relative_files": True, "source": ["src"], "branch": True})
        self.assertIn("sonar.python.coverage.reportPaths=coverage.xml", (fixture / "sonar-project.properties").read_text(encoding="utf-8"))

    def test_node_profile_requires_each_declared_ci_script(self) -> None:
        self.assertFalse(
            profile_configuration_valid(
                "node",
                {"package.json", "package-lock.json"},
                node_scripts={"lint", "test:ci"},
            )
        )
        self.assertTrue(
            profile_configuration_valid(
                "node",
                {"package.json", "package-lock.json"},
                node_scripts={"lint", "format:check", "build", "test:ci", "typecheck"},
            )
        )

    def test_publication_is_opt_in_and_rejects_unsafe_events_and_repositories(self) -> None:
        self.assertRegex(WORKFLOW, r"(?s)publish_image:.*?default: false")
        self.assertIn("publish_image requires run_container_checks=true", WORKFLOW)
        self.assertIn("Image publication is allowed only for push events", WORKFLOW)
        self.assertIn("actual default branch", WORKFLOW)
        self.assertIn("disabled in fork repositories", WORKFLOW)
        self.assertIn("packages: write", WORKFLOW)
        publish_job = WORKFLOW.split("\n  publish:\n", maxsplit=1)[1].split("\n  required-checks:", maxsplit=1)[0]
        self.assertIn("name: non-production", publish_job)
        self.assertNotIn("actions/checkout", publish_job)
        self.assertIn("needs: [validate, build-and-test, secret-scan, dependency-scan, sonar, container]", publish_job)
        self.assertIn("if: ${{ inputs.publish_image &&", publish_job)
        self.assertNotIn("always()", publish_job)

        safe = dict(
            requested=True,
            container_checks=True,
            event="push",
            ref="refs/heads/main",
            default_branch="main",
            repository="acme/service",
            event_repository="acme/service",
            repository_is_fork=False,
        )
        self.assertTrue(publication_allowed(**safe))
        unsafe_cases = (
            {**safe, "event": "pull_request"},
            {**safe, "ref": "refs/heads/feature"},
            {**safe, "repository_is_fork": True},
            {**safe, "event_repository": "contributor/service"},
            {**safe, "container_checks": False},
            {**safe, "requested": False},
        )
        for case in unsafe_cases:
            with self.subTest(case=case):
                self.assertFalse(publication_allowed(**case))

    def test_image_artifact_and_remote_digest_are_verified(self) -> None:
        self.assertIn("sha256sum --check scanned-image.tar.sha256", WORKFLOW)
        self.assertIn("Downloaded image does not match the scanned image ID", WORKFLOW)
        self.assertIn("Published GHCR image does not match the scanned image config digest", WORKFLOW)
        self.assertIn("image_digest=$image_digest", WORKFLOW)

    def test_all_active_external_action_refs_are_full_sha_pinned(self) -> None:
        references = re.findall(r"(?m)^\s+uses:\s+[^\s]+@([0-9a-f]+)", ACTIVE_WORKFLOWS)
        self.assertTrue(references)
        for sha in references:
            with self.subTest(sha=sha):
                self.assertEqual(len(sha), 40)
                self.assertIn(sha, ACTION_PINS)
        for line in ACTIVE_WORKFLOWS.splitlines():
            if re.match(r"\s+uses:\s", line):
                if re.search(r"@[0-9a-f]{40}\b", line):
                    self.assertRegex(line, r"#[^\n]+")

    def test_dependabot_targets_only_existing_central_dependency_sources(self) -> None:
        dependabot = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertIn("package-ecosystem: github-actions", dependabot)
        self.assertEqual(dependabot.count("package-ecosystem:"), 2)
        self.assertIn("interval: weekly", dependabot)
        self.assertIn("directory: /tests/consumer-repo/python-app", dependabot)
        docs = (ROOT / "docs" / "stage-1" / "security-tools-and-dependencies.md").read_text(encoding="utf-8")
        for ecosystem in ("maven", "gradle", "pip", "npm", "nuget", "gomod", "docker", "github-actions"):
            self.assertIn(f"`{ecosystem}`", docs)
        self.assertIn("does not switch those features on", docs)

    def test_main_protection_workflow_is_intentionally_disabled_and_retained(self) -> None:
        active = ROOT / ".github" / "workflows" / "main-protection.yml"
        disabled = ROOT / ".github" / "workflows" / "main-protection.yml.disabled"
        self.assertFalse(active.exists())
        self.assertTrue(disabled.is_file())
        workflow = disabled.read_text(encoding="utf-8")
        self.assertIn("pull_request:", workflow)
        self.assertIn("branches: [main]", workflow)
        self.assertIn("actionlint -color", workflow)
        self.assertIn("v1.7.12", workflow)
        self.assertIn("8aca8db96f1b94770f1b0d72b6dddcb1ebb8123cb3712530b08cc387b349a3d8", workflow)
        self.assertIn("zizmorcore/zizmor-action@85b2b9fb8e3325e7a23d7d0a9d7ba5ae0f999e3e", workflow)
        runbook = (ROOT / "docs" / "stage-1" / "default-branch-protection.md").read_text(encoding="utf-8")
        self.assertIn("intentionally disabled", runbook)
        self.assertIn("exact successful check contexts", runbook)
        self.assertIn("bypass list empty", runbook)
        self.assertIn("force pushes", runbook)
        self.assertIn("actual default branch", runbook)
        self.assertIn("does not enforce", runbook)

    def test_regression_caller_runs_reusable_workflow_on_main_prs_and_manual_dispatch(self) -> None:
        caller_path = ROOT / ".github" / "workflows" / "reusable-app-ci-regression.yml"
        caller = caller_path.read_text(encoding="utf-8")
        self.assertIn("pull_request:", caller)
        self.assertIn("workflow_dispatch:", caller)
        self.assertIn("branches: [main]", caller)
        self.assertIn("uses: ./.github/workflows/reusable-app-ci.yml", caller)
        self.assertIn("working_directory: tests/consumer-repo/python-app", caller)
        self.assertIn("SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}", caller)
        self.assertIn("github.event.pull_request.head.repo.full_name == github.repository", caller)
        self.assertIn("github.actor != 'dependabot[bot]'", caller)
        self.assertIn("publish_image: false", caller)

        fixture = ROOT / "tests" / "consumer-repo" / "python-app"
        self.assertTrue((fixture / "pyproject.toml").is_file())
        self.assertTrue((fixture / "sonar-project.properties").is_file())
        self.assertTrue((fixture / "src" / "regression_consumer" / "calculator.py").is_file())
        self.assertTrue((fixture / "test" / "test_calculator.py").is_file())
        self.assertFalse((ROOT / "examples" / "config").exists())

    def test_callers_map_only_named_secret_and_declare_the_required_permission_ceiling(self) -> None:
        caller = (ROOT / "examples" / "caller-workflows" / "python-app.yml.example").read_text(encoding="utf-8")
        publisher = (ROOT / "examples" / "caller-workflows" / "publish-image.yml.example").read_text(encoding="utf-8")
        self.assertIn("SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}", caller)
        self.assertNotIn("GITLEAKS_LICENSE", caller)
        self.assertIn("publish_image: false", caller)
        self.assertIn("actions: read", caller)
        self.assertIn("pull-requests: read", caller)
        self.assertIn("security-events: write", caller)
        self.assertIn("packages: write", caller)
        self.assertIn("packages: write", publisher)
        self.assertIn("run_container_checks: true", publisher)
        self.assertIn("publish_image: true", publisher)
        self.assertIn("/.github/workflows/reusable-app-ci.yml@main", publisher)


class RequiredChecksTests(unittest.TestCase):
    """Execute the actual workflow's aggregate-gate script against job outcomes."""

    def run_gate(self, **overrides: str) -> tuple[subprocess.CompletedProcess[str], str]:
        job = WORKFLOW.split("\n  required-checks:\n", maxsplit=1)[1]
        script = textwrap.dedent(job.split("        run: |\n", maxsplit=1)[1])
        results = {
            "VALIDATE_RESULT": "success",
            "BUILD_TEST_RESULT": "success",
            "SECRET_RESULT": "success",
            "DEPENDENCY_RESULT": "success",
            "SONAR_RESULT": "success",
            "CONTAINER_RESULT": "skipped",
            "PUBLISH_RESULT": "skipped",
            "RUN_CONTAINER_CHECKS": "false",
            "PUBLISH_IMAGE": "false",
            **overrides,
        }
        with tempfile.TemporaryDirectory() as directory:
            summary_path = Path(directory) / "summary.md"
            completed = subprocess.run(
                [sys.executable, "-c", script],
                env={**os.environ, **results, "GITHUB_STEP_SUMMARY": str(summary_path)},
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            summary = summary_path.read_text(encoding="utf-8")
        return completed, summary

    def test_successful_requested_jobs_and_skipped_optional_jobs_pass(self) -> None:
        for configuration in (
            {},
            {"RUN_CONTAINER_CHECKS": "true", "CONTAINER_RESULT": "success"},
            {
                "RUN_CONTAINER_CHECKS": "true",
                "PUBLISH_IMAGE": "true",
                "CONTAINER_RESULT": "success",
                "PUBLISH_RESULT": "success",
            },
        ):
            with self.subTest(configuration=configuration):
                completed, summary = self.run_gate(**configuration)
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn("| Check | Expected | Result | Gate |", summary)
                self.assertEqual(sum(line.startswith("|") for line in summary.splitlines()), 9)
                self.assertIn("| Build and test | success | success | Passed |", summary)

    def test_mandatory_jobs_fail_closed_and_still_write_the_table(self) -> None:
        for job in (
            "VALIDATE_RESULT",
            "BUILD_TEST_RESULT",
            "SECRET_RESULT",
            "DEPENDENCY_RESULT",
            "SONAR_RESULT",
        ):
            for result in ("failure", "cancelled", "skipped", ""):
                with self.subTest(job=job, result=result):
                    completed, summary = self.run_gate(**{job: result})
                    self.assertEqual(completed.returncode, 1, completed.stderr)
                    self.assertIn("::error::", completed.stdout)
                    self.assertIn("| Failed |", summary)
                    self.assertIn("| Image publication | skipped | skipped | Not requested |", summary)

    def test_optional_jobs_must_match_the_requested_behavior(self) -> None:
        for configuration in (
            {"RUN_CONTAINER_CHECKS": "true", "CONTAINER_RESULT": "skipped"},
            {"RUN_CONTAINER_CHECKS": "true", "CONTAINER_RESULT": "failure"},
            {"CONTAINER_RESULT": "success"},
            {"PUBLISH_RESULT": "success"},
            {"PUBLISH_IMAGE": "true", "CONTAINER_RESULT": "skipped", "PUBLISH_RESULT": "success"},
            *(
                {
                    "RUN_CONTAINER_CHECKS": "true",
                    "PUBLISH_IMAGE": "true",
                    "CONTAINER_RESULT": "success",
                    "PUBLISH_RESULT": result,
                }
                for result in ("skipped", "failure", "cancelled", "unknown")
            ),
        ):
            with self.subTest(configuration=configuration):
                completed, summary = self.run_gate(**configuration)
                self.assertEqual(completed.returncode, 1, completed.stderr)
                self.assertIn("| Failed |", summary)


if __name__ == "__main__":
    unittest.main()
