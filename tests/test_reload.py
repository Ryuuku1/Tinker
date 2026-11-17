import contextlib
import io
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import reload  # noqa: E402


def run(cwd, *args):
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


def identify(repo):
    run(repo, "config", "user.name", "Test User")
    run(repo, "config", "user.email", "test@example.com")
    run(repo, "config", "commit.gpgsign", "false")


def commit_file(repo, name, text, message):
    Path(repo, name).write_text(text, encoding="utf-8", newline="")
    run(repo, "add", name)
    run(repo, "commit", "-q", "-m", message)


@contextlib.contextmanager
def working_directory(path):
    before = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(before)


class ReloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        self.origin = base / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.origin)], check=True)
        self.work = base / "work"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.work)], check=True, capture_output=True)
        identify(self.work)
        run(self.work, "checkout", "-q", "-B", "main")
        commit_file(self.work, "a.txt", "one\n", "initial")
        run(self.work, "push", "-q", "-u", "origin", "main")
        run(self.work, "remote", "set-head", "origin", "main")
        self.other = base / "other"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.other)], check=True, capture_output=True)
        identify(self.other)
        self.base = base

    def reload(self, *argv, cwd=None):
        out = io.StringIO()
        with working_directory(cwd or self.work), contextlib.redirect_stdout(out):
            code = reload.main(list(argv))
        return code, out.getvalue()

    def branch_exists(self, name):
        return bool(subprocess.run(["git", "-C", str(self.work), "show-ref", "--verify", "--quiet",
                                    f"refs/heads/{name}"]).returncode == 0)

    def merged_branch_with_worktree(self, name="feat-a", start="main"):
        """A branch with a commit, a linked worktree on it, and origin's main advanced to that commit."""
        folder = self.base / f"wt-{name}"
        run(self.work, "worktree", "add", "-q", "-b", name, str(folder), start)
        commit_file(folder, f"{name}.txt", "x\n", f"work on {name}")
        run(self.work, "push", "-q", "origin", f"{name}:main")
        return folder

    def test_ancestor_merged_branch_and_worktree_are_removed_and_main_fast_forwards(self):
        folder = self.merged_branch_with_worktree()
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertFalse(folder.exists(), out)
        self.assertFalse(self.branch_exists("feat-a"), out)
        self.assertIn("ancestor", out)
        self.assertEqual(run(self.work, "rev-parse", "main"), run(self.work, "rev-parse", "origin/main"))
        self.assertTrue((self.work / "feat-a.txt").exists())

    def test_squash_merged_branch_is_detected_through_cherry_and_deleted(self):
        run(self.work, "branch", "feat-sq")
        folder = self.base / "wt-sq"
        run(self.work, "worktree", "add", "-q", str(folder), "feat-sq")
        commit_file(folder, "s.txt", "squash\n", "feature")
        run(self.work, "worktree", "remove", str(folder))
        commit_file(self.other, "s.txt", "squash\n", "feature (squashed)")
        commit_file(self.other, "t.txt", "later\n", "unrelated follow-up")
        run(self.other, "push", "-q", "origin", "main")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertFalse(self.branch_exists("feat-sq"), out)
        self.assertIn("git cherry", out)

    def test_unmerged_branch_and_its_worktree_are_kept(self):
        folder = self.base / "wt-wip"
        run(self.work, "worktree", "add", "-q", "-b", "wip", str(folder))
        commit_file(folder, "wip.txt", "unfinished\n", "wip")
        run(self.work, "branch", "also-wip", "wip")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertTrue(folder.exists())
        self.assertTrue(self.branch_exists("wip"))
        self.assertTrue(self.branch_exists("also-wip"))
        self.assertIn("not proven merged", out)

    def test_a_branch_with_no_commits_of_its_own_is_not_treated_as_merged(self):
        folder = self.base / "wt-fresh"
        run(self.work, "worktree", "add", "-q", "-b", "fresh", str(folder))
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertTrue(folder.exists())
        self.assertTrue(self.branch_exists("fresh"))

    def test_dirty_worktree_is_kept(self):
        folder = self.merged_branch_with_worktree()
        (folder / "a.txt").write_text("edited\n", encoding="utf-8")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertTrue(folder.exists())
        self.assertTrue(self.branch_exists("feat-a"))
        self.assertIn("uncommitted", out)

    def test_worktree_with_an_untracked_file_is_kept(self):
        folder = self.merged_branch_with_worktree()
        (folder / "scratch.txt").write_text("notes\n", encoding="utf-8")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertTrue(folder.exists())
        self.assertTrue((folder / "scratch.txt").exists())
        self.assertIn("untracked", out)

    def test_worktree_in_use_by_the_current_directory_is_kept(self):
        folder = self.merged_branch_with_worktree()
        code, out = self.reload(cwd=folder)
        self.assertEqual(code, 0, out)
        self.assertTrue(folder.exists())
        self.assertIn("current directory", out)

    def test_keep_protects_branch_and_worktree(self):
        folder = self.merged_branch_with_worktree()
        other = self.merged_branch_with_worktree("feat-b", "feat-a")
        run(self.work, "worktree", "remove", str(other))
        code, out = self.reload("--keep", "feat-a", "--keep", "feat-b")
        self.assertEqual(code, 0, out)
        self.assertTrue(folder.exists())
        self.assertTrue(self.branch_exists("feat-a"))
        self.assertTrue(self.branch_exists("feat-b"))
        self.assertIn("listed in --keep", out)
        code, out = self.reload("--keep", "feat-b")
        self.assertFalse(folder.exists(), out)
        self.assertFalse(self.branch_exists("feat-a"))
        self.assertTrue(self.branch_exists("feat-b"))

    def test_dry_run_changes_nothing(self):
        folder = self.merged_branch_with_worktree()
        before = [run(self.work, "branch", "--list"), run(self.work, "worktree", "list"), run(self.work, "rev-parse", "main")]
        code, out = self.reload("--dry-run")
        after = [run(self.work, "branch", "--list"), run(self.work, "worktree", "list"), run(self.work, "rev-parse", "main")]
        self.assertEqual(code, 0, out)
        self.assertEqual(before, after)
        self.assertTrue(folder.exists())
        self.assertIn("would remove worktree", out)
        self.assertIn("would delete branch feat-a", out)
        self.assertIn("would fast-forward main", out)

    def test_default_branch_is_fast_forwarded(self):
        commit_file(self.other, "b.txt", "new\n", "advance origin")
        run(self.other, "push", "-q", "origin", "main")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertEqual(run(self.work, "rev-parse", "main"), run(self.other, "rev-parse", "main"))
        self.assertIn("fast-forwarded main", out)

    def test_default_branch_not_checked_out_is_moved_with_update_ref(self):
        run(self.work, "checkout", "-q", "-b", "wip")
        commit_file(self.work, "wip.txt", "unfinished\n", "wip")
        commit_file(self.other, "b.txt", "new\n", "advance origin")
        run(self.other, "push", "-q", "origin", "main")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertEqual(run(self.work, "rev-parse", "main"), run(self.other, "rev-parse", "main"))
        self.assertEqual(run(self.work, "rev-parse", "--abbrev-ref", "HEAD"), "wip")
        self.assertIn("moved main", out)

    def test_main_checkout_on_a_merged_branch_switches_to_default_and_deletes_it(self):
        run(self.work, "checkout", "-q", "-b", "done")
        commit_file(self.work, "done.txt", "x\n", "done")
        run(self.work, "push", "-q", "origin", "done:main")
        code, out = self.reload()
        self.assertEqual(code, 0, out)
        self.assertEqual(run(self.work, "rev-parse", "--abbrev-ref", "HEAD"), "main")
        self.assertFalse(self.branch_exists("done"), out)

    def test_proven_merged_accepts_a_matching_pull_request_head_and_rejects_others(self):
        run(self.work, "checkout", "-q", "-b", "pr")
        commit_file(self.work, "pr.txt", "x\n", "pr work")
        tip = run(self.work, "rev-parse", "pr")
        base = "refs/remotes/origin/main"
        self.assertIn("pull request", reload.proven_merged(self.work, "pr", base, lambda root, branch: {tip}))
        self.assertIsNone(reload.proven_merged(self.work, "pr", base, lambda root, branch: {"0" * 40}))
        self.assertIsNone(reload.proven_merged(self.work, "pr", base, lambda root, branch: None))

    def test_gh_is_not_asked_when_origin_is_not_github(self):
        self.assertIsNone(reload.merged_pull_request_heads(self.work, "anything"))


if __name__ == "__main__":
    unittest.main()
