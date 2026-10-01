"""Real Git coverage for the optional kit's exact-path checkout trust."""
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GIT = shutil.which("git")


def git_bash():
    if os.name != "nt":
        return shutil.which("bash")
    if GIT:
        for parent in Path(GIT).resolve().parents:
            candidate = parent / "usr/bin/bash.exe"
            if candidate.is_file():
                return str(candidate)
    return None


BASH = git_bash()


@unittest.skipUnless(GIT and BASH, "Git and Git Bash/bash required")
class MountedCheckoutTests(unittest.TestCase):
    def test_kit_trust_allows_local_clones_without_trusting_unrelated_repositories(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            mounts = root / "repos"
            checkout = mounts / "example"
            unrelated = root / "unrelated"
            config = root / "gitconfig"
            config.write_text("", encoding="utf-8")
            env = {**os.environ, "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1"}

            def git(*args, assumed_owner=False):
                effective = dict(env)
                if assumed_owner:
                    effective["GIT_TEST_ASSUME_DIFFERENT_OWNER"] = "1"
                else:
                    effective.pop("GIT_TEST_ASSUME_DIFFERENT_OWNER", None)
                return subprocess.run([GIT, *args], env=effective, capture_output=True, text=True)

            for repo in (checkout, unrelated):
                self.assertEqual(git("init", "-q", str(repo)).returncode, 0)
                (repo / "note.txt").write_text("fixture\n", encoding="utf-8")
                self.assertEqual(git("-C", str(repo), "add", "note.txt").returncode, 0)
                committed = git("-C", str(repo), "-c", "user.name=Fixture", "-c",
                                "user.email=fixture@example.invalid", "commit", "-qm", "fixture")
                self.assertEqual(committed.returncode, 0, committed.stderr)

            # Exercise the kit's actual startup loop with /repos mapped to this fixture.
            script = (ROOT / "integrations/buzz/kit/scripts/agent.sh").read_text(encoding="utf-8")
            loop = re.search(r"(?m)^for d in /repos/.*?; done$", script)
            self.assertIsNotNone(loop, "kit startup must establish checkout trust before starting agents")
            shell_mounts = mounts.as_posix()
            if os.name == "nt":
                shell_mounts = "/" + shell_mounts[0].lower() + shell_mounts[2:]
            command = loop.group().replace("/repos", shlex.quote(shell_mounts))
            trusted = subprocess.run([BASH, "-c", command], env=env, capture_output=True, text=True)
            self.assertEqual(trusted.returncode, 0, trusted.stderr)

            status = git("-C", str(checkout), "status", "--porcelain", assumed_owner=True)
            self.assertEqual(status.returncode, 0, status.stderr)
            # upload-pack checks the .git directory separately from its checkout.
            metadata = git("-C", str(checkout / ".git"), "rev-parse", "--is-inside-git-dir",
                           assumed_owner=True)
            self.assertEqual(metadata.returncode, 0, metadata.stderr)
            clone = git("clone", "--quiet", "--depth", "1", checkout.as_uri(),
                        str(root / "writer-copy"), assumed_owner=True)
            self.assertEqual(clone.returncode, 0, clone.stderr)
            self.assertEqual((root / "writer-copy/note.txt").read_text(), "fixture\n")
            denied = git("-C", str(unrelated), "status", "--porcelain", assumed_owner=True)
            self.assertNotEqual(denied.returncode, 0)
            self.assertIn("dubious ownership", denied.stderr)


if __name__ == "__main__":
    unittest.main()
