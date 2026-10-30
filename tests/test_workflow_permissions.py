"""Check caller permission ceilings and the tokens issued to Stage 1 jobs."""

from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI = (ROOT / ".github/workflows/reusable-app-ci.yml").read_text(encoding="utf-8")
CD = (ROOT / ".github/workflows/reusable-app-cd.yml").read_text(encoding="utf-8")


def jobs(workflow: str) -> dict[str, str]:
    parts = re.split(r"(?m)^  ([a-z][a-z0-9_-]*):\n", workflow.split("\njobs:\n", 1)[1])
    return dict(zip(parts[1::2], parts[2::2]))


def permissions(job: str) -> dict[str, str]:
    match = re.search(r"(?m)^    permissions:( \{\})?\n", job)
    if match is None:
        raise AssertionError("Every job must declare its permission budget explicitly.")
    result = {}
    if match.group(1):
        return result
    for line in job[match.end():].splitlines():
        scope = re.fullmatch(r"      ([a-z-]+): (none|read|write)", line)
        if not scope:
            break
        result[scope[1]] = scope[2]
    return result


class WorkflowPermissionTests(unittest.TestCase):
    def test_fixture_scanner_manifest_matches_the_installed_direct_dependencies(self) -> None:
        fixture = ROOT / "tests/consumer-repo/python-app"
        project = tomllib.loads((fixture / "pyproject.toml").read_text(encoding="utf-8"))
        scanned = {
            line.strip() for line in (fixture / "requirements-dev.txt").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertEqual(scanned, set(project["project"]["optional-dependencies"]["dev"]))

    def test_runtime_jobs_have_only_the_permissions_they_use(self) -> None:
        self.assertIn("\npermissions: {}\n", CI)
        for name, body in jobs(CI).items():
            with self.subTest(job=name):
                expected = {"contents": "read"}
                if name == "publish":
                    expected = {"packages": "write"}
                elif name == "secret-scan":
                    expected = {"contents": "read", "pull-requests": "read"}
                elif name == "dependency-scan":
                    expected = {"actions": "read", "contents": "read", "security-events": "write"}
                elif name == "required-checks":
                    expected = {}
                self.assertEqual(permissions(body), expected)
                self.assertNotIn("GITLEAKS_LICENSE", body)
                if name != "sonar":
                    self.assertNotIn("SONAR_TOKEN", body)
        self.assertIn("osv-scanner-reusable.yml@c7c7bcb0773cc4678a674ada03a66cc5c4325476", CI)
        self.assertNotIn("actions: write", CI)
        self.assertNotIn("id-token:", CI)
        self.assertIn("\npermissions: {}\n", CD)
        self.assertEqual(permissions(jobs(CD)["deploy"]), {"id-token": "write"})

    def test_image_publication_stays_in_ci_with_application_cd_separate(self) -> None:
        reusable = {
            path.name for path in (ROOT / ".github/workflows").glob("*.yml")
            if "  workflow_call:" in path.read_text(encoding="utf-8")
        }
        self.assertEqual(reusable, {"reusable-app-ci.yml", "reusable-app-cd.yml"})
        publish = jobs(CI)["publish"]
        self.assertIn("needs: [validate, build-and-test, secret-scan, dependency-scan, sonar, container]", publish)
        self.assertIn("if: ${{ inputs.publish_image &&", publish)
        self.assertIn("github.event_name == 'push'", publish)
        self.assertIn("github.event.repository.default_branch", publish)
        self.assertIn("github.event.repository.fork != true", publish)
        self.assertIn("name: non-production", publish)
        self.assertNotIn("always()", publish)
        self.assertNotIn("actions/checkout", publish)
        self.assertNotIn("SONAR_TOKEN", publish)
        self.assertIn("needs.container.outputs.archive_sha256", publish)
        self.assertIn("needs.container.outputs.image_id", publish)

    def test_write_scopes_are_limited_to_osv_publication_and_deployment(self) -> None:
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            for name, body in jobs(path.read_text(encoding="utf-8")).items():
                for scope, access in permissions(body).items():
                    with self.subTest(workflow=path.name, job=name, scope=scope):
                        if access == "write":
                            self.assertIn(scope, {"packages", "security-events", "id-token"})
                            if path.name == "reusable-app-ci.yml":
                                self.assertEqual(name, {"packages": "publish", "security-events": "dependency-scan"}[scope])
                            elif path.name == "reusable-app-cd.yml":
                                self.assertEqual((name, scope), ("deploy", "id-token"))
                            else:
                                self.assertIn("uses: ./.github/workflows/reusable-app-ci.yml", body)

    def test_caller_ceilings_allow_every_job_without_extra_scopes(self) -> None:
        for relative in (
            ".github/workflows/reusable-app-ci-regression.yml",
            "examples/caller-workflows/python-app.yml.example",
            "examples/caller-workflows/publish-image.yml.example",
            "examples/caller-workflows/node-app-ci-cd.yml.example",
        ):
            workflow = (ROOT / relative).read_text(encoding="utf-8")
            for name, body in jobs(workflow).items():
                with self.subTest(caller=relative, job=name):
                    ceiling = permissions(body)
                    if "/.github/workflows/reusable-app-cd.yml" in body:
                        self.assertEqual(ceiling, {"id-token": "write"})
                        self.assertIn("needs: ci", body)
                        nested_workflow = CD
                    else:
                        self.assertEqual(ceiling, {"actions": "read", "contents": "read", "pull-requests": "read", "security-events": "write", "packages": "write"})
                        self.assertIn("/.github/workflows/reusable-app-ci.yml", body)
                        nested_workflow = CI
                    levels = {"none": 0, "read": 1, "write": 2}
                    for nested in jobs(nested_workflow).values():
                        for scope, access in permissions(nested).items():
                            self.assertLessEqual(levels[access], levels[ceiling.get(scope, "none")])


if __name__ == "__main__":
    unittest.main()
