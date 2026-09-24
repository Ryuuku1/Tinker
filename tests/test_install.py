"""Installer and generator tests against a temporary home; no real app configuration is touched.

Host CLIs are fakes that record their calls and update the temporary home's settings the way
the real CLIs do; they prove the installer's bookkeeping, not live host registration.
"""
import hashlib
import json
import os
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import install_apps  # noqa: E402

PYTHON = getattr(sys, "_base_executable", sys.executable)
# Antigravity refuses paths that need quoting (Python under "Program Files", a home with spaces).
APPS = ("claude", "codex") + (("antigravity",) if install_apps.SAFE_PATH.match(PYTHON) and
                              install_apps.SAFE_PATH.match(str(Path(tempfile.gettempdir()).resolve())) else ())
FAKE_CLI = r'''
import json, os, sys
from pathlib import Path
name, args = sys.argv[1], sys.argv[2:]
here = Path(__file__).resolve().parent
line = " ".join([name, *args])
with open(here / "calls.log", "a", encoding="utf-8") as log:
    log.write(line + "\n")
failing = (here / "fail.txt").read_text(encoding="utf-8").splitlines() if (here / "fail.txt").exists() else []
if any(prefix and line.startswith(prefix) for prefix in failing):
    sys.exit(1)
home = Path((here / "home.txt").read_text(encoding="utf-8").strip())  # only ever the test's disposable home
if name == "claude" and args[:2] in (["plugin", "install"], ["plugin", "uninstall"]):
    path = home / ".claude" / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    plugins = settings.setdefault("enabledPlugins", {})
    if args[1] == "install":
        plugins[args[2]] = True
    else:
        plugins.pop(args[2], None)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings), encoding="utf-8")
if name == "codex" and args[:2] in (["plugin", "add"], ["plugin", "remove"]):
    path = home / ".codex" / "config.toml"
    block = '[plugins."%s"]\nenabled = true\n' % args[2]
    text = (path.read_text(encoding="utf-8") if path.exists() else "").replace(block, "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + block if args[1] == "add" else text, encoding="utf-8")
'''


class InstallCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.lines = []

    def installer(self, **kw):
        return install_apps.Installer(self.home, kw.pop("python", PYTHON), out=self.lines.append, **kw)

    def install(self, apps=APPS, **kw):
        return self.installer(**kw).install(list(apps))

    def steps(self, action):
        return [line for line in self.lines if re.search(rf"\s{re.escape(action)}\s", line)]

    def fake_cli(self, exit_code=0, fail=()):
        """Fake `claude` and `codex` on PATH; commands starting with a `fail` prefix exit 1."""
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "fake_cli.py").write_text(FAKE_CLI, encoding="utf-8")
        (bin_dir / "home.txt").write_text(str(self.home), encoding="utf-8")
        (bin_dir / "fail.txt").write_text("\n".join(fail or (["claude", "codex"] if exit_code else [])), encoding="utf-8")
        for name in ("claude", "codex"):
            if os.name == "nt":
                (bin_dir / f"{name}.cmd").write_text(f'@"{PYTHON}" "%~dp0fake_cli.py" {name} %*\r\n'
                                                     "@exit /b %errorlevel%\r\n", encoding="utf-8")
            else:
                script = bin_dir / name
                script.write_text(f'#!/bin/sh\nexec "{PYTHON}" "$(dirname "$0")/fake_cli.py" {name} "$@"\n')
                script.chmod(0o755)
        patcher = mock.patch.dict(os.environ, {"PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", "")})
        patcher.start()
        self.addCleanup(patcher.stop)
        return bin_dir / "calls.log"

    def record(self):
        return json.loads((self.home / ".tinker" / "apps.json").read_text(encoding="utf-8"))

    def copy_package(self):
        """A disposable checkout to install from, so a test can change the charter."""
        root = self.tmp / "checkout"
        for name in ("AGENTS.md", "policies", "roles", "templates", "profiles", ".agents/skills", "scripts"):
            source, target = ROOT / name, root / name
            if source.is_dir():
                shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        return root


class GeneratorTests(unittest.TestCase):
    def test_project_descriptors_have_no_drift(self):
        rendered = install_apps.project_descriptors(ROOT)
        self.assertEqual(len(rendered), 3 * len(install_apps.roles(ROOT)))
        for rel, content in rendered.items():
            with self.subTest(file=rel):
                current = (ROOT / rel).read_bytes().decode("utf-8").replace("\r\n", "\n")
                self.assertEqual(current, content, "regenerate with: python scripts/install_apps.py --write-descriptors")

    def test_rendered_charter_links_resolve_inside_the_copy(self):
        for lead in ("AGENTS.md", "rules/AGENTS.md"):
            tree = install_apps.charter_tree(ROOT, lead_path=lead)
            self.assertIn(lead, tree)
            self.assertIn("skills/tinker-team/SKILL.md", tree)
            for rel, text in tree.items():
                for target in re.findall(r"\]\(([^\s)]+)\)", text):
                    if target.startswith(("https://", "http://", "#")):
                        continue
                    link = target.split("#")[0]
                    with self.subTest(lead=lead, file=rel, target=target):
                        if re.match(r"^[A-Za-z]:/|^/", link):
                            self.assertTrue(Path(link).exists())
                        else:
                            self.assertIn(posixpath.normpath(posixpath.join(posixpath.dirname(rel), link)), tree)

    def test_graphify_commands_point_at_the_checkout(self):
        skill = install_apps.charter_tree(ROOT)["skills/tinker-graphify/SKILL.md"]
        self.assertNotIn("python scripts/graphify_project.py", skill)
        self.assertIn(f'python "{(ROOT / "scripts" / "graphify_project.py").as_posix()}"', skill)


class RenderTests(InstallCase):
    def test_install_renders_every_app(self):
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))
        pending = self.steps("Pending")  # skipped registration is visible, never reported as done
        self.assertEqual(sorted(line.split()[0] for line in pending), ["claude", "codex"], "\n".join(self.lines))
        state = self.home / ".tinker"
        self.assertEqual((state / "runtime" / "tinker_runtime.py").read_bytes(), (ROOT / "scripts" / "tinker_runtime.py").read_bytes())
        bundle = state / "plugin"
        for rel in (install_apps.MARKER_FILE, "AGENTS.md", "skills/tinker-team/SKILL.md", "agents/reviewer.md",
                    ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "plugin.json",
                    ".agents/plugins/marketplace.json", "hooks/claude.json", "hooks/codex.json"):
            self.assertTrue((bundle / rel).is_file(), rel)
        manifest = json.loads((bundle / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        codex_manifest = json.loads((bundle / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], codex_manifest["version"])
        self.assertEqual(codex_manifest["extensions"]["com.openai"]["hooks"], "./hooks/codex.json")
        reviewer = (bundle / "agents" / "reviewer.md").read_text(encoding="utf-8")
        self.assertIn("tools: Read, Grep, Glob\n", reviewer)
        self.assertNotRegex(reviewer, r"(?m)^(memory|hooks|mcpServers|permissionMode):")
        self.assertIn(bundle.as_posix(), reviewer)
        agents = sorted((self.home / ".codex" / "agents").glob("tinker-*.toml"))
        self.assertEqual(len(agents), 8)
        import tomllib
        for path in agents:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            reader = data["sandbox_mode"] == "read-only"
            self.assertEqual(data.get("features"), {"shell_tool": False} if reader else None, path.name)
            self.assertEqual(data["agents"], {"enabled": False})
        if "antigravity" in APPS:
            plugin = self.home / ".gemini" / "config" / "plugins" / "tinker"
            self.assertTrue((plugin / "rules" / "AGENTS.md").is_file())
            self.assertFalse((plugin / "AGENTS.md").exists())
            self.assertEqual(len(list((plugin / "agents").glob("tinker-*.md"))), 8)
        config = json.loads((state / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["root"], str(ROOT))
        record = json.loads((state / "apps.json").read_text(encoding="utf-8"))
        self.assertEqual(set(record["apps"]), set(APPS))
        for path, digest in record["files"].items():
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), digest, path)

    @unittest.skipUnless(os.name == "nt" and shutil.which("pwsh") and shutil.which("cmd"), "needs Windows shells")
    def test_rendered_hook_commands_pass_their_shell_self_test(self):
        self.install(skip_cli=True)
        checked = self.steps("Checked")
        self.assertEqual(len(checked), len(APPS), "\n".join(self.lines))

    def test_hook_command_forms(self):
        runtime = self.home / ".tinker" / "runtime" / "tinker_runtime.py"
        claude = install_apps.claude_hooks(PYTHON, runtime)["hooks"]
        pre = claude["PreToolUse"][0]
        for name in ("Bash", "PowerShell", "Write", "NotebookEdit", "mcp__scheduled-tasks__update_scheduled_task",
                     "mcp__plugin_acme_scheduled-tasks__create_scheduled_task"):
            self.assertTrue(re.search(pre["matcher"], name), name)
        for name in ("TodoWrite", "BashOutput", "mcp__x__Edit", "Read", "mcp__plugin_acme_other__create_scheduled_task",
                     "mcp__scheduled-tasks__list_scheduled_tasks"):
            self.assertFalse(re.search(pre["matcher"], name), name)
        gated = install_apps.antigravity_hooks("/usr/bin/python3", runtime)["tinker"]["PreToolUse"][0]["matcher"]
        for name in ("run_command", "write_to_file", "schedule"):
            self.assertTrue(re.search(gated, name), name)
        self.assertFalse(re.search(gated, "list_schedules"))
        self.assertEqual(pre["hooks"][0]["args"][:2], ["-I", "-S"])
        self.assertEqual(claude["SessionStart"][0]["matcher"], "startup|resume|clear|compact|fork")
        codex = install_apps.codex_hooks(PYTHON, runtime)["hooks"]
        windows = codex["PreToolUse"][0]["hooks"][0]["commandWindows"]
        self.assertTrue(windows.startswith('& "') and windows.endswith("; exit $LASTEXITCODE"))
        self.assertLessEqual(codex["SessionEnd"][0]["hooks"][0]["timeout"], 3)
        antigravity = install_apps.antigravity_hooks("/usr/bin/python3", runtime)["tinker"]
        for handler in (antigravity["PreToolUse"][0]["hooks"][0], antigravity["PreInvocation"][0], antigravity["Stop"][0]):
            self.assertNotIn('"', handler["command"])
        with self.assertRaises(ValueError):
            install_apps.antigravity_hooks("C:/Program Files/Python/python.exe", runtime)
        with self.assertRaises(ValueError):
            install_apps.antigravity_hooks("/usr/bin/python3", Path("C:/Users/John Smith/.tinker/runtime/tinker_runtime.py"))

    def test_reinstall_keeps_hook_commands_stable(self):
        with mock.patch.object(install_apps.time, "strftime", return_value="20260101000000"):
            self.install(skip_cli=True)
        first = (self.home / ".tinker" / "plugin" / "hooks" / "codex.json").read_bytes()
        with mock.patch.object(install_apps.time, "strftime", return_value="20260102000000"):
            self.install(skip_cli=True)
        bundle = self.home / ".tinker" / "plugin"
        self.assertEqual((bundle / "hooks" / "codex.json").read_bytes(), first)
        self.assertEqual(json.loads((bundle / "plugin.json").read_text(encoding="utf-8"))["version"], "0.3.20260102000000")

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.install(dry_run=True), 0)
        self.assertEqual(list(self.home.iterdir()), [])
        self.assertTrue(self.steps("Would render"))
        self.assertTrue(self.steps("Would run"))


class OwnershipTests(InstallCase):
    def test_user_files_and_folders_are_never_overwritten(self):
        mine = self.home / ".codex" / "agents" / "tinker-reviewer.toml"
        mine.parent.mkdir(parents=True)
        mine.write_text("# the user's own agent\n", encoding="utf-8")
        foreign = self.home / ".gemini" / "config" / "plugins" / "tinker"
        foreign.mkdir(parents=True)
        (foreign / "notes.md").write_text("user notes\n", encoding="utf-8")
        self.assertEqual(self.install(skip_cli=True), 1)
        self.assertEqual(mine.read_text(encoding="utf-8"), "# the user's own agent\n")
        self.assertEqual((foreign / "notes.md").read_text(encoding="utf-8"), "user notes\n")
        self.assertTrue(self.steps("Kept") and self.steps("Refused"))
        record = json.loads((self.home / ".tinker" / "apps.json").read_text(encoding="utf-8"))
        self.assertNotIn(str(mine), record["apps"]["codex"]["agents"])
        self.assertNotIn("antigravity", record["apps"])

    def test_apps_with_another_tinker_enabled_are_refused(self):
        # Another installation may use this very plugin id and folder; only these records make them ours.
        (self.home / ".claude").mkdir()
        (self.home / ".claude" / "settings.json").write_text(json.dumps({"enabledPlugins": {"tinker@tinker-local": True}}))
        (self.home / ".codex").mkdir()
        (self.home / ".codex" / "config.toml").write_text('[plugins."tinker@tinker-local"]\nenabled = true\n')
        (self.home / ".gemini" / "config" / "plugins" / "tinker").mkdir(parents=True)
        self.assertEqual(self.install(skip_cli=True), 1)
        self.assertEqual(len(self.steps("Refused")), 3)
        self.assertFalse((self.home / ".tinker" / "runtime").exists())
        self.lines.clear()
        (self.home / ".claude" / "settings.json").write_text(json.dumps({"enabledPlugins": {"tinker@tinker-local": False}}))
        (self.home / ".codex" / "config.toml").write_text('[plugins."tinker@tinker-local"]\nenabled = false\n')
        (self.home / ".gemini" / "config" / "config.json").write_text(json.dumps({"plugins": {"tinker": {"enabled": False}}}))
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))
        self.lines.clear()
        (self.home / ".claude" / "settings.json").write_text(json.dumps(
            {"enabledPlugins": {install_apps.PLUGIN_ID: True, "tinker@elsewhere": True}}))
        self.assertEqual(self.installer(skip_cli=True).install(["claude"]), 1)
        self.assertTrue(any("another Tinker" in line for line in self.steps("Refused")), "\n".join(self.lines))

    def test_uninstall_keeps_apps_that_still_list_the_plugin(self):
        self.install(skip_cli=True)
        (self.home / ".claude").mkdir(exist_ok=True)
        (self.home / ".claude" / "settings.json").write_text(json.dumps({"enabledPlugins": {install_apps.PLUGIN_ID: True}}))
        (self.home / ".codex" / "config.toml").write_text(f'[plugins."{install_apps.PLUGIN_ID}"]\nenabled = true\n')
        self.lines.clear()
        self.installer(skip_cli=True).uninstall(list(APPS))
        state = self.home / ".tinker"
        self.assertTrue((state / "runtime" / "tinker_runtime.py").is_file())
        self.assertTrue((state / "plugin").is_dir())
        self.assertFalse((self.home / ".gemini" / "config" / "plugins" / "tinker").exists())
        record = json.loads((state / "apps.json").read_text(encoding="utf-8"))
        self.assertEqual(set(record["apps"]), {"claude", "codex"})

    def test_uninstall_finishes_when_the_apps_no_longer_list_the_plugin(self):
        self.install(skip_cli=True)
        self.lines.clear()
        self.assertEqual(self.installer(skip_cli=True).uninstall(list(APPS)), 0, "\n".join(self.lines))
        state = self.home / ".tinker"
        self.assertFalse((state / "plugin").exists())
        self.assertTrue((state / "runtime" / "tinker_runtime.py").is_file())  # open chats may still run it
        record = self.record()  # kept as the runtime's ownership evidence, so a reinstall recognises it
        self.assertEqual(record["apps"], {})
        self.assertEqual(set(record["files"]), {str(state / "runtime" / "tinker_runtime.py")})
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))

    def test_failed_claude_registration_is_reported(self):
        self.fake_cli(exit_code=1)
        self.assertEqual(self.install(apps=("claude",)), 1)
        self.assertTrue(any("not registered" in line for line in self.steps("Failed")), "\n".join(self.lines))
        self.assertFalse(self.steps("Next"))

    def test_install_and_uninstall_through_the_app_clis(self):
        log = self.fake_cli()
        self.assertEqual(self.install(), 0, "\n".join(self.lines))
        calls = log.read_text().splitlines()
        self.assertIn(f"claude plugin install {install_apps.PLUGIN_ID} --scope user", [c.strip() for c in calls])
        self.assertIn(f"codex plugin add {install_apps.PLUGIN_ID}", [c.strip() for c in calls])
        edited = self.home / ".codex" / "agents" / "tinker-engineer.toml"
        edited.write_text(edited.read_text(encoding="utf-8") + "# user edit\n", encoding="utf-8")
        self.lines.clear()
        self.installer().uninstall(list(APPS))
        state = self.home / ".tinker"
        self.assertTrue((state / "runtime" / "tinker_runtime.py").exists())
        self.assertTrue(any("restart open" in line for line in self.steps("Kept")))
        self.assertFalse((state / "plugin").exists())
        self.assertEqual(self.record()["apps"], {})
        self.assertFalse((state / "config.json").exists())
        self.assertTrue(edited.is_file())
        self.assertEqual(list((self.home / ".codex" / "agents").glob("tinker-*.toml")), [edited])
        self.assertIn(f"claude plugin uninstall {install_apps.PLUGIN_ID} --scope user",
                      [c.strip() for c in log.read_text().splitlines()])


class ActivationTests(InstallCase):
    """Manifest-and-hash ownership, staged activation, partial registration and per-app revisions."""

    def bundle(self):
        return self.home / ".tinker" / "plugin"

    def tree(self, folder):
        return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob("*") if p.is_file()}

    def failing_replace(self, error, nth=2):
        """Activation that raises `error` on its nth replacement inside the bundle."""
        real, seen = install_apps.replace, []

        def replace(source, target):
            if Path(target).is_relative_to(self.bundle()):
                seen.append(target)
                if len(seen) == nth:
                    raise error
            return real(source, target)
        return mock.patch.object(install_apps, "replace", replace)

    def versioned(self, stamp):
        return mock.patch.object(install_apps.time, "strftime", return_value=stamp)

    def assert_manifest_matches_disk(self):
        record = self.record()
        self.assertFalse(record.get("pending"))
        for path, digest in record["files"].items():
            self.assertEqual(hashlib.sha256(Path(path).read_bytes()).hexdigest(), digest, path)

    def test_foreign_runtime_and_config_are_never_replaced(self):
        for rel in ("runtime/tinker_runtime.py", "config.json"):
            with self.subTest(file=rel):
                shutil.rmtree(self.home / ".tinker", ignore_errors=True)
                target = self.home / ".tinker" / rel
                target.parent.mkdir(parents=True)
                target.write_text("the user's own file\n", encoding="utf-8")
                self.lines.clear()
                self.assertEqual(self.install(skip_cli=True), 1)
                self.assertEqual(target.read_text(encoding="utf-8"), "the user's own file\n")
                self.assertTrue(any(str(target) in line for line in self.steps("Refused")), "\n".join(self.lines))
                self.assertFalse(self.bundle().exists())

    def test_another_installations_home_is_never_rewritten(self):
        # Another Tinker installation can share this home (same product name): its records are not ours.
        state = self.home / ".tinker"
        theirs = {state / "apps.json": json.dumps({"Claude": {"plugin": "tinker", "version": "1.0"}}),
                  state / "config.json": json.dumps({"root": "C:/elsewhere", "team": "core"}),
                  state / "plugin" / ".claude-plugin" / "plugin.json": json.dumps({"name": "tinker"})}
        for path, text in theirs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        for run in ("install", "uninstall"):
            with self.subTest(run=run):
                self.lines.clear()
                installer = self.installer(skip_cli=True)
                self.assertEqual(getattr(installer, run)(list(APPS)), 1)
                self.assertTrue(any("apps.json" in line for line in self.steps("Refused")), "\n".join(self.lines))
                self.assertEqual({p: p.read_text(encoding="utf-8") for p in theirs}, theirs)
                self.assertFalse((state / "runtime").exists())

    def test_dry_run_reports_conflicts_and_writes_nothing(self):
        target = self.home / ".tinker" / "runtime" / "tinker_runtime.py"
        target.parent.mkdir(parents=True)
        target.write_text("mine\n", encoding="utf-8")
        self.assertEqual(self.install(dry_run=True), 1)
        self.assertTrue(any(str(target) in line for line in self.steps("Refused")), "\n".join(self.lines))
        self.assertEqual([p for p in self.home.rglob("*") if p.is_file()], [target])

    def test_modified_owned_files_survive_update_and_uninstall(self):
        self.install(skip_cli=True)
        edited = self.bundle() / "AGENTS.md"
        edited.write_text(edited.read_text(encoding="utf-8") + "\nlocal note\n", encoding="utf-8")
        before = edited.read_bytes()
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True), 1)
        self.assertEqual(edited.read_bytes(), before)
        self.assertTrue(any("AGENTS.md" in line for line in self.steps("Refused")), "\n".join(self.lines))
        self.lines.clear()
        self.installer(skip_cli=True).uninstall(list(APPS))
        self.assertEqual(edited.read_bytes(), before)

    def test_extra_files_in_rendered_folders_survive_update_and_uninstall(self):
        self.install(skip_cli=True)
        folders = [self.bundle()]
        if "antigravity" in APPS:
            folders.append(self.home / ".gemini" / "config" / "plugins" / "tinker")
        for folder in folders:
            (folder / "skills" / "my-notes.md").write_bytes(b"mine\n")
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))
        self.lines.clear()
        self.assertEqual(self.installer(skip_cli=True).uninstall(list(APPS)), 0, "\n".join(self.lines))
        for folder in folders:  # everything Tinker wrote is gone; the user's file and its folder stay
            self.assertEqual(self.tree(folder), {"skills/my-notes.md": b"mine\n"})

    def test_a_failed_activation_restores_the_previous_files(self):
        with self.versioned("20260101000000"):
            self.install(skip_cli=True)
        before = self.tree(self.bundle())
        self.lines.clear()
        with self.versioned("20260102000000"), self.failing_replace(PermissionError("simulated lock")):
            self.assertEqual(self.install(skip_cli=True), 1)
        self.assertEqual(self.tree(self.bundle()), before)
        self.assertTrue(any("restored" in line for line in self.steps("Failed")), "\n".join(self.lines))
        self.assert_manifest_matches_disk()
        for app in ("claude", "codex"):  # registering now would load the restored, older bundle
            self.assertEqual(self.record()["apps"][app]["recovery"], "re-run the installer")
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))
        self.assert_manifest_matches_disk()

    def test_an_interrupted_activation_is_recovered_by_the_next_install(self):
        with self.versioned("20260101000000"):
            self.install(skip_cli=True)
        # Not an Exception, so no rollback runs: the files are left half-replaced, as by a killed process.
        with self.versioned("20260102000000"), self.failing_replace(KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.install(skip_cli=True)
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))
        self.assert_manifest_matches_disk()

    def test_an_interrupted_then_failed_activation_is_still_recovered(self):
        with self.versioned("20260101000000"):
            self.install(skip_cli=True)
        with self.versioned("20260102000000"), self.failing_replace(KeyboardInterrupt()):
            with self.assertRaises(KeyboardInterrupt):
                self.install(skip_cli=True)
        for nth in (1, 2):  # before and after the half-replaced file is replaced once more
            with self.subTest(nth=nth), self.versioned(f"2026010{2 + nth}000000"), \
                    self.failing_replace(PermissionError("simulated lock"), nth):
                self.lines.clear()
                self.assertEqual(self.install(skip_cli=True), 1, "\n".join(self.lines))
                self.assertFalse(self.steps("Refused"), "\n".join(self.lines))  # nothing mistaken for the user's
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))
        self.assert_manifest_matches_disk()

    def test_a_file_changed_after_preflight_is_not_replaced(self):
        self.install(skip_cli=True)
        target = self.bundle() / "AGENTS.md"
        real = install_apps.Installer.stage

        def stage_then_edit(installer, files):
            staged = real(installer, files)
            if target in files:  # the user edits the file while the install is running
                target.write_bytes(b"edited during the install\n")
            return staged
        self.lines.clear()
        with self.versioned("20260201000000"), mock.patch.object(install_apps.Installer, "stage", stage_then_edit):
            self.assertEqual(self.install(skip_cli=True), 1)
        self.assertEqual(target.read_bytes(), b"edited during the install\n")

    def test_a_runtime_failing_a_registered_app_self_test_is_not_activated(self):
        root = self.copy_package()
        self.fake_cli()
        self.assertEqual(self.installer(root=root).install(list(APPS)), 0, "\n".join(self.lines))
        runtime = self.home / ".tinker" / "runtime" / "tinker_runtime.py"
        before = runtime.read_bytes()
        (root / "scripts" / "tinker_runtime.py").write_bytes(before + b"\n# a newer runtime\n")
        real = install_apps.Installer.self_test

        def failing(installer, app, handler):
            if app == "codex":
                installer.step(app, "Failed", "simulated self-test failure")
                return False
            return real(installer, app, handler)
        self.lines.clear()
        with mock.patch.object(install_apps.Installer, "self_test", failing):
            self.assertEqual(self.installer(root=root).install(["claude"]), 1)
        self.assertEqual(runtime.read_bytes(), before)  # Codex still runs the runtime it was tested with
        self.assertTrue(any("codex" in line for line in self.steps("Refused")), "\n".join(self.lines))

    @unittest.skipUnless("antigravity" in APPS, "Antigravity needs a path without spaces or ~")
    def test_apps_outside_the_run_are_self_tested_with_their_own_interpreter(self):
        self.assertEqual(self.install(skip_cli=True), 0, "\n".join(self.lines))  # Antigravity activates without a CLI
        seen = {}

        def record(installer, app, handler):
            seen[app] = json.dumps(handler)
            return True
        other = "C:/Program Files/Python/python.exe"  # an interpreter Antigravity's hooks could never use
        with mock.patch.object(install_apps.Installer, "self_test", record):
            self.installer(python=other, skip_cli=True).install(["claude"])
        self.assertIn(other, seen.get("claude", ""))
        self.assertIn(Path(PYTHON).as_posix().split("/")[-1], seen.get("antigravity", ""))
        self.assertNotIn("Program Files", seen.get("antigravity", "Program Files"))

    def test_a_config_that_cannot_be_staged_is_reported(self):
        real = install_apps.Installer.stage

        def stage(installer, files):
            if any(path.name == "config.json" for path in files):
                raise OSError("simulated full disk")
            return real(installer, files)
        with mock.patch.object(install_apps.Installer, "stage", stage):
            self.assertEqual(self.install(skip_cli=True), 1)
        self.assertTrue(any("config.json" in line for line in self.steps("Failed")), "\n".join(self.lines))
        self.assertFalse((self.home / ".tinker" / "staging").exists())

    @unittest.skipUnless("antigravity" in APPS, "Antigravity needs a path without spaces or ~")
    def test_antigravity_uninstall_is_confirmed_by_its_own_manifest(self):
        self.install(skip_cli=True)
        folder = self.home / ".gemini" / "config" / "plugins" / "tinker"
        (folder / "skills" / "mine.md").write_bytes(b"mine\n")
        (self.home / ".gemini" / "config" / "config.json").write_text("{broken", encoding="utf-8")
        self.lines.clear()
        self.assertEqual(self.installer(skip_cli=True).uninstall(["antigravity"]), 0, "\n".join(self.lines))
        self.assertNotIn("antigravity", self.record()["apps"])
        self.assertEqual(self.tree(folder), {"skills/mine.md": b"mine\n"})

    def test_migration_attributes_a_digest_only_to_the_matching_version(self):
        state = self.home / ".tinker"
        state.mkdir()
        (state / "config.json").write_text(json.dumps({"version": "0.3.2", "charter_sha256": "a" * 64}), encoding="utf-8")
        (state / "apps.json").write_text(json.dumps({"apps": {
            "claude": {"version": "0.3.2", "registered": True}, "codex": {"version": "0.3.1", "registered": True}},
            "files": {}}), encoding="utf-8")
        installer = self.installer(dry_run=True)
        installer.migrate()
        self.assertEqual(installer.apps["claude"]["activated"]["charter_sha256"], "a" * 64)
        self.assertIsNone(installer.apps["codex"]["activated"]["charter_sha256"])  # its evidence was overwritten

    def test_failed_registration_is_recorded_as_partial_with_recovery(self):
        self.fake_cli(fail=("claude plugin install", "claude plugin update"))
        self.assertEqual(self.install(apps=("claude",)), 1)
        claude = self.record()["apps"]["claude"]
        self.assertIsNone(claude.get("activated", "missing"))
        self.assertEqual(claude.get("registration"), "disabled")
        self.assertIn("claude plugin install", claude.get("recovery") or "")
        self.assertTrue((self.bundle() / ".claude-plugin" / "plugin.json").is_file())  # kept: recovery needs it
        self.assertFalse(self.steps("Next"))

    def test_registration_is_recorded_as_each_app_reports_it(self):
        self.fake_cli()
        self.assertEqual(self.install(), 0, "\n".join(self.lines))
        record = self.record()
        for app in APPS:
            with self.subTest(app=app):
                self.assertEqual(record["apps"][app]["registration"], "enabled")
                self.assertEqual(record["apps"][app]["activated"], record["apps"][app]["rendered"])

    def test_unreadable_host_settings_refuse_install_and_keep_uninstall_unknown(self):
        settings = self.home / ".claude" / "settings.json"
        settings.parent.mkdir()
        settings.write_text("{broken", encoding="utf-8")
        self.assertEqual(self.install(apps=("claude",), skip_cli=True), 1)
        self.assertTrue(any("settings.json" in line for line in self.steps("Refused")), "\n".join(self.lines))
        self.assertFalse(self.bundle().exists())
        self.assertEqual(settings.read_text(encoding="utf-8"), "{broken")
        settings.write_text("{}", encoding="utf-8")
        bin_dir = self.fake_cli().parent
        self.lines.clear()
        self.assertEqual(self.install(apps=("claude",)), 0, "\n".join(self.lines))
        settings.write_text("{broken", encoding="utf-8")
        (bin_dir / "fail.txt").write_text("claude plugin uninstall", encoding="utf-8")
        self.lines.clear()
        self.assertEqual(self.installer().uninstall(["claude"]), 1)
        self.assertEqual(self.record()["apps"]["claude"]["registration"], "unknown")
        self.assertTrue((self.bundle() / ".claude-plugin" / "plugin.json").is_file())

    def test_updating_one_app_leaves_the_others_visibly_stale(self):
        root = self.copy_package()
        self.fake_cli()
        self.assertEqual(self.installer(root=root).install(list(APPS)), 0, "\n".join(self.lines))
        (root / "AGENTS.md").write_text((root / "AGENTS.md").read_text(encoding="utf-8") + "\nA new rule.\n",
                                        encoding="utf-8")
        self.lines.clear()
        self.assertEqual(self.installer(root=root).install(["claude"]), 0, "\n".join(self.lines))
        runtime = self.home / ".tinker" / "runtime" / "tinker_runtime.py"
        env = dict(os.environ, USERPROFILE=str(self.home), HOME=str(self.home))
        status = subprocess.run([PYTHON, "-I", "-S", str(runtime), "status"], capture_output=True, env=env,
                                timeout=60).stdout.decode("utf-8")
        self.assertRegex(status, r"- claude: current")
        for app in APPS[1:]:
            self.assertRegex(status, rf"- {app}: stale")
        record = self.record()
        self.assertNotEqual(record["apps"]["codex"]["activated"], record["apps"]["claude"]["activated"])
        payload = json.dumps({"session_id": "c1", "cwd": str(self.tmp), "source": "startup"}).encode("utf-8")
        context = subprocess.run([PYTHON, "-I", "-S", str(runtime), "session-start", "--host", "codex"], input=payload,
                                 capture_output=True, env=env, timeout=60).stdout.decode("utf-8")
        self.assertIn("checkout changed since install of this app (codex)", context)

    def test_an_earlier_manifest_is_read_as_is_and_migrated_only_by_an_install(self):
        self.install(skip_cli=True)
        state = self.home / ".tinker"
        current = self.record()
        config = {"root": str(ROOT), "version": "0.3.20260101000000", "runtime": str(state / "runtime" / "tinker_runtime.py"),
                  "charter_sha256": install_apps.tinker_runtime.charter_digest(ROOT), "python": PYTHON}
        (state / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        files = dict(current["files"], **{str(state / "config.json"):
                                          hashlib.sha256((state / "config.json").read_bytes()).hexdigest()})
        legacy = {"version": config["version"], "root": str(ROOT), "files": files, "apps": {
            "claude": {"plugin": install_apps.PLUGIN_ID, "version": config["version"], "registered": True},
            "codex": {"plugin": install_apps.PLUGIN_ID, "version": config["version"], "registered": True,
                      "agents": current["apps"]["codex"]["agents"]}}}
        (state / "apps.json").write_text(json.dumps(legacy), encoding="utf-8")
        saved = (state / "apps.json").read_bytes()
        env = dict(os.environ, USERPROFILE=str(self.home), HOME=str(self.home))
        status = subprocess.run([PYTHON, "-I", "-S", str(state / "runtime" / "tinker_runtime.py"), "status"],
                                capture_output=True, env=env, timeout=60).stdout.decode("utf-8")
        self.assertRegex(status, r"- claude: current")
        self.assertEqual(self.install(dry_run=True, apps=("claude", "codex")), 0, "\n".join(self.lines))
        self.assertEqual((state / "apps.json").read_bytes(), saved)  # reading never migrates
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True, apps=("claude", "codex")), 0, "\n".join(self.lines))
        self.assertEqual(self.record().get("schema"), 2)
        self.assert_manifest_matches_disk()
        del legacy["files"][str(state / "runtime" / "tinker_runtime.py")]  # missing evidence is never ownership
        (state / "apps.json").write_text(json.dumps(legacy), encoding="utf-8")
        self.lines.clear()
        self.assertEqual(self.install(skip_cli=True, apps=("claude",)), 1)
        self.assertTrue(any("tinker_runtime.py" in line for line in self.steps("Refused")), "\n".join(self.lines))


if __name__ == "__main__":
    unittest.main()
