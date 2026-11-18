import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tinker_runtime  # noqa: E402
import update  # noqa: E402


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


class UpdateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name).resolve()
        origin = base / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
        self.root = base / "tinker"
        self.other = base / "other"
        for clone in (self.root, self.other):
            subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True, capture_output=True)
            identify(clone)
        run(self.root, "checkout", "-q", "-B", "main")
        commit_file(self.root, "a.txt", "one\n", "initial")
        run(self.root, "push", "-q", "-u", "origin", "main")
        run(self.root, "remote", "set-head", "origin", "main")
        run(self.other, "pull", "-q", "origin", "main")
        run(self.other, "checkout", "-q", "main")
        self.home = base / "home"
        self.home.mkdir()
        self.runs = []

    def upstream(self, count=1):
        for index in range(count):
            commit_file(self.other, f"new{index}.txt", "x\n", f"upstream change {index}")
        run(self.other, "push", "-q", "origin", "main")

    def install(self, instance="", root=None, apps=("claude",), digest="old", shape="ours"):
        folder = self.home / (f".tinker-{instance}" if instance else ".tinker")
        folder.mkdir()
        records = {"apps": {a: {} for a in apps}, "files": {}} if shape == "ours" else {"Claude": {"source": "x"}}
        (folder / "apps.json").write_text(json.dumps(records), encoding="utf-8")
        config = {"root": str(root or self.root), "python": sys.executable,
                  "hosts": {a: {"charter_sha256": digest, "version": "1"} for a in apps}}
        (folder / "config.json").write_text(json.dumps(config), encoding="utf-8")
        return folder

    def update(self, **kwargs):
        lines = []

        def fake_run(command, **_):
            self.runs.append(command)
            return subprocess.CompletedProcess(command, 0)
        code = update.update(self.root, self.home, say=lines.append, run=fake_run, **kwargs)
        return code, "\n".join(lines)

    def record(self):
        return json.loads((self.root / ".tinker" / "update.json").read_text(encoding="utf-8"))

    def head(self):
        return run(self.root, "rev-parse", "HEAD")

    def test_check_records_how_far_behind_and_pulls_nothing(self):
        self.upstream(2)
        before = self.head()
        code, out = self.update(check=True, scheduled=True)
        self.assertEqual(code, 0)
        self.assertEqual(self.head(), before)
        record = self.record()
        self.assertEqual((record["status"], record["behind"], record["default"]), ("behind", 2, "main"))
        self.assertIn("2 new commits on origin/main", out)
        self.assertEqual(record["scheduled_at"], record["checked"])
        self.assertEqual(self.runs, [])

    def test_a_manual_run_keeps_the_scheduled_time(self):
        self.update(check=True, scheduled=True)
        scheduled = self.record()["scheduled_at"]
        self.update(check=True)
        self.assertEqual(self.record()["scheduled_at"], scheduled)

    def test_update_fast_forwards_and_reinstalls_each_installation_from_this_checkout(self):
        self.install()
        self.install("personal", apps=("claude", "codex", "antigravity"))
        self.install("work", root=self.other)  # another checkout's installation
        self.install("org", shape="theirs")  # another edition's records
        self.upstream()
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.head(), run(self.root, "rev-parse", "origin/main"))
        self.assertIn("upstream change 0", out)
        installs = [(c[c.index("--app") + 1], c[c.index("--instance") + 1] if "--instance" in c else "") for c in self.runs]
        self.assertEqual(sorted(installs), [("all", "personal"), ("claude", "")])
        self.assertTrue(all(c[1].endswith("install_apps.py") and "--python" in c and str(self.home) in c for c in self.runs))
        record = self.record()
        self.assertEqual((record["status"], record["behind"]), ("updated", 0))

    def test_nothing_pulled_reinstalls_only_a_stale_app(self):
        current = tinker_runtime.charter_digest(self.root)
        folder = self.install(apps=("claude", "codex"), digest=current)
        config = json.loads((folder / "config.json").read_text(encoding="utf-8"))
        config["hosts"]["codex"]["charter_sha256"] = "old"
        (folder / "config.json").write_text(json.dumps(config), encoding="utf-8")
        code, out = self.update()
        self.assertEqual(code, 0, out)
        self.assertEqual([c[c.index("--app") + 1] for c in self.runs], ["codex"])

    def test_current_installations_are_left_alone(self):
        self.install(digest=tinker_runtime.charter_digest(self.root))
        code, out = self.update()
        self.assertEqual((code, self.runs), (0, []))
        self.assertIn("current", out)
        self.assertEqual(self.record()["status"], "current")

    def test_a_failed_reinstall_is_an_error(self):
        self.install()
        self.upstream()
        code = update.update(self.root, self.home, say=lambda _: None,
                             run=lambda command, **_: subprocess.CompletedProcess(command, 3))
        self.assertEqual(code, 1)
        self.assertEqual(self.record()["status"], "error")
        self.assertIn("installer exit 3", self.record()["detail"])

    def test_dry_run_changes_and_records_nothing(self):
        self.install()
        self.upstream()
        before = self.head()
        code, out = self.update(dry_run=True)
        self.assertEqual(code, 0)
        self.assertEqual(self.head(), before)
        self.assertIn("would fast-forward main", out)
        self.assertIn("would reinstall the default installation", out)
        self.assertEqual(self.runs, [])
        self.assertFalse((self.root / ".tinker" / "update.json").exists())

    def test_blocked_on_another_branch_with_local_commits_or_dirty_files(self):
        self.upstream()
        run(self.root, "checkout", "-q", "-b", "feature")
        code, out = self.update()
        self.assertEqual(code, 1)
        self.assertIn("on branch feature, not main", out)
        run(self.root, "checkout", "-q", "main")
        Path(self.root, "a.txt").write_text("changed\n", encoding="utf-8")
        code, out = self.update()
        self.assertIn("1 tracked file with uncommitted changes", out)
        run(self.root, "checkout", "-q", "--", "a.txt")
        commit_file(self.root, "mine.txt", "x\n", "local work")
        before = self.head()
        code, out = self.update()
        self.assertEqual(code, 1)
        self.assertIn("1 local commit", out)
        self.assertEqual(self.head(), before)
        self.assertEqual(self.record()["status"], "blocked")
        self.assertEqual(self.runs, [])

    def test_a_failed_fetch_keeps_the_last_known_count(self):
        self.upstream(3)
        self.update(check=True)
        run(self.root, "remote", "set-url", "origin", str(Path(self.tmp.name) / "missing.git"))
        code, out = self.update(check=True)
        self.assertEqual(code, 1)
        record = self.record()
        self.assertEqual((record["status"], record["behind"]), ("error", 3))
        self.assertIn("fetch failed", out)

    def test_another_running_update_is_skipped(self):
        with update.Lock(self.root) as held:
            self.assertTrue(held.held)
            with update.Lock(self.root) as second:
                self.assertFalse(second.held)
        with update.Lock(self.root) as again:
            self.assertTrue(again.held)


class ScheduleTests(unittest.TestCase):
    root = Path(tempfile.gettempdir()) / "tinker-checkout"

    def test_outside_windows_it_prints_the_crontab_line(self):
        lines = []
        code = update.schedule(self.root, say=lines.append, platform="posix")
        self.assertEqual(code, 1)
        self.assertIn("crontab -e", lines[0])
        self.assertIn("scripts/update.py --check --scheduled", lines[0])

    def test_daily_and_hourly_tasks_catch_up_after_sleep(self):
        daily, when = update.task_xml(self.root, 24, "pythonw.exe", '"x" --check --scheduled')
        self.assertEqual(when, "daily at 09:00")
        self.assertIn("<StartWhenAvailable>true</StartWhenAvailable>", daily)
        self.assertIn("<DaysInterval>1</DaysInterval>", daily)
        self.assertNotIn("<Repetition>", daily)
        self.assertIn("<ExecutionTimeLimit>PT10M</ExecutionTimeLimit>", daily)
        hourly, when = update.task_xml(self.root, 2, "pythonw.exe", "x")
        self.assertIn("<Interval>PT2H</Interval>", hourly)
        self.assertEqual(when, "every 2 h from 09:00")

    def test_the_check_runs_this_checkouts_script_without_a_window(self):
        program, arguments = update.check_command(self.root)
        self.assertIn(str(self.root / "scripts" / "update.py"), arguments)
        self.assertIn("--check --scheduled", arguments)
        if os.name == "nt":
            self.assertRegex(Path(program).name.lower(), r"^(pythonw|conhost)\.exe$")

    def test_task_names_differ_per_checkout(self):
        self.assertNotEqual(update.task_name(self.root), update.task_name(self.root.parent))
        self.assertTrue(update.task_name(self.root).startswith("TinkerUpdateCheck-"))

    def query(self, arguments):
        xml = f'<?xml version="1.0" encoding="UTF-16"?><Task><Actions><Exec><Arguments>{arguments}</Arguments></Exec></Actions></Task>'
        return mock.patch.object(update, "schtasks", side_effect=lambda *a: (True, xml) if a[0] == "/Query" else (True, ""))

    def test_a_task_running_another_checkouts_script_is_left_alone(self):
        lines = []
        with self.query("-File C:\\elsewhere\\scripts\\tinker-update.ps1 -Check") as calls:
            self.assertEqual(update.schedule(self.root, say=lines.append, name="T", platform="nt"), 1)
            self.assertEqual(update.schedule(self.root, remove=True, say=lines.append, name="T", platform="nt"), 1)
        self.assertEqual([c.args[0] for c in calls.call_args_list], ["/Query", "/Query"])
        self.assertIn("another checkout's script", lines[0])

    def test_its_own_task_is_replaced_or_removed(self):
        lines = []
        own = f"&quot;{self.root / 'scripts' / 'update.py'}&quot; --check --scheduled"
        with self.query(own) as calls:
            self.assertEqual(update.schedule(self.root, say=lines.append, name="T", platform="nt", dry_run=True), 0)
            self.assertEqual(update.schedule(self.root, remove=True, say=lines.append, name="T", platform="nt"), 0)
        self.assertIn("would replace scheduled task T", lines[0])
        self.assertEqual(calls.call_args_list[-1].args, ("/Delete", "/TN", "T", "/F"))

    def test_the_words_the_gate_lets_through_never_change_the_schedule(self):
        own = f"&quot;{update.ROOT / 'scripts' / 'update.py'}&quot; --check --scheduled"
        with self.query(own) as calls, mock.patch("sys.stderr"), mock.patch("sys.stdout"):
            for words in (["--schedule", "--check"], ["--unschedule", "--check"], ["--sched", "--dry-run"]):
                with self.assertRaises(SystemExit, msg=words):
                    update.main(words)
            for words in (["--schedule", "--dry-run"], ["--unsch", "--dry-run"]):
                self.assertEqual(update.main(words + ["--task-name", "T"]), 0 if os.name == "nt" else 1, words)
        self.assertNotIn("/Create", [c.args[0] for c in calls.call_args_list])
        self.assertNotIn("/Delete", [c.args[0] for c in calls.call_args_list])


if __name__ == "__main__":
    unittest.main()
