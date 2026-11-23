import subprocess
import tempfile
import unittest
from pathlib import Path

from assaystone.model import Step, Trace
from assaystone.replay import git_preimage, infer_test_evidence, is_git_repo


class TestEvidenceTest(unittest.TestCase):
    def _infer(self, command: str, output: str, ok: bool = True):
        trace = Trace(
            id="t",
            task="",
            steps=[Step("Bash", {"command": command}, output, ok)],
        )
        infer_test_evidence(trace)
        return trace.evidence.get("test_exit_code")

    def test_build_success(self):
        self.assertEqual(self._infer("mvn test", "BUILD SUCCESS"), 0)

    def test_zero_failures(self):
        self.assertEqual(self._infer("npm test", "Tests: 0 failed, 5 passed"), 0)

    def test_failure(self):
        self.assertEqual(self._infer("pytest", "1 failed, 4 passed"), 1)

    def test_failed_tool_result(self):
        self.assertEqual(self._infer("go test ./...", "FAIL", ok=False), 1)

    def test_non_test_command(self):
        self.assertIsNone(self._infer("ls", "OK"))

    def test_grep_token_in_tests_is_not_a_test_run(self):
        self.assertIsNone(
            self._infer('grep -rn "token" test/fixtures', "api token found: abc123")
        )

    def test_latest_is_not_a_test_run(self):
        self.assertIsNone(self._infer("latest-release", "ok"))

    def test_no_tests_ran_is_unknown(self):
        self.assertIsNone(self._infer("pytest", "no tests ran in 0.01s"))

    def test_failed_summary(self):
        self.assertEqual(self._infer("pytest", "FAILED (failures=1)"), 1)

    def test_zero_failures_is_success(self):
        self.assertEqual(self._infer("npm test", "Tests: 0 failed, 5 passed"), 0)

    def test_build_success_is_success(self):
        self.assertEqual(self._infer("mvn test", "BUILD SUCCESS"), 0)

    def test_git_preimage_from_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            sub = repo / "sub"
            sub.mkdir()
            (sub / "a.py").write_text("old = 1\n", encoding="utf-8")
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                ["git", "-c", "user.email=a@b.c", "-c", "user.name=t", "commit", "-qm", "init"],
                cwd=repo,
                check=True,
            )
            (sub / "a.py").write_text("new = 2\n", encoding="utf-8")
            self.assertTrue(is_git_repo(sub))
            preimage = git_preimage(sub, ["a.py"])
            try:
                self.assertEqual((Path(preimage.name) / "a.py").read_text(encoding="utf-8"), "old = 1\n")
            finally:
                preimage.cleanup()


if __name__ == "__main__":
    unittest.main()
