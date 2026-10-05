"""scripts/tinker_platform.py: the stored Windows or Linux choice, its precedence, and the kit commands it runs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tinker_platform  # noqa: E402


class PlatformTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)

    def test_unset_means_detected_from_this_machine(self):
        self.assertEqual(tinker_platform.configured(self.root), "auto")
        self.assertEqual(tinker_platform.resolve(self.root, environ={}), (tinker_platform.detected(), "detected"))

    def test_a_stored_choice_wins_over_detection_and_the_environment_over_both(self):
        path = tinker_platform.save("windows", self.root)
        self.assertEqual(path, self.root / ".tinker" / "platform.json")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"platform": "windows"})
        self.assertEqual(tinker_platform.resolve(self.root, environ={}), ("windows", str(path)))
        self.assertEqual(tinker_platform.resolve(self.root, environ={"TINKER_PLATFORM": "Linux"}),
                         ("linux", "TINKER_PLATFORM"))
        # auto in the environment defers to the stored choice; a typo is refused, never guessed.
        self.assertEqual(tinker_platform.resolve(self.root, environ={"TINKER_PLATFORM": "auto"})[0], "windows")
        with self.assertRaises(ValueError):
            tinker_platform.resolve(self.root, environ={"TINKER_PLATFORM": "debian"})
        tinker_platform.save("auto", self.root)
        self.assertEqual(tinker_platform.resolve(self.root, environ={})[1], "detected")

    def test_an_unreadable_or_unknown_choice_is_auto(self):
        path = self.root / ".tinker" / "platform.json"
        path.parent.mkdir()
        for text in ("{broken", '["linux"]', '{"platform": "macos"}'):
            with self.subTest(text=text):
                path.write_text(text, encoding="utf-8")
                self.assertEqual(tinker_platform.configured(self.root), "auto")
        with self.assertRaises(ValueError):
            tinker_platform.save("debian", self.root)

    def test_linux_runs_the_bash_scripts_with_the_arguments_unchanged(self):
        kit = tinker_platform.KIT
        self.assertEqual(tinker_platform.kit_command("linux", "setup", ["--project", "x", "-OwnerNpub", "n"]),
                         ["bash", str(kit / "setup.sh"), "--project", "x", "-OwnerNpub", "n"])
        self.assertEqual(tinker_platform.kit_command("linux", "kit", ["Get-KitStatus"]),
                         ["bash", str(kit / "kit.sh"), "Get-KitStatus"])
        for script in tinker_platform.KIT_SCRIPTS:
            self.assertTrue((kit / f"{script}.sh").is_file() and (kit / f"{script}.ps1").is_file(), script)
        with self.assertRaises(ValueError):
            tinker_platform.kit_command("linux", "rm", [])

    def test_windows_gets_powershell_parameters_from_the_bash_spelling(self):
        argv = tinker_platform.kit_command("windows", "setup", [
            "--project", "x", "--repository", "C:\\src\\a b", "--repository", "D:\\it's", "--owner-npub", "npub1q",
            "-Port", "3100"])
        self.assertEqual(argv[1:3], ["-NoProfile", "-Command"])
        self.assertEqual(argv[3], f"& '{tinker_platform.KIT / 'setup.ps1'}' -Project 'x' -OwnerNpub 'npub1q' -Port 3100 "
                                  "-Repository 'C:\\src\\a b','D:\\it''s'")
        self.assertTrue(argv[3].endswith("-Repository 'C:\\src\\a b','D:\\it''s'"))
        self.assertTrue(tinker_platform.kit_command("windows", "setup", ["--repository", ""])[3].endswith("-Repository ''"))
        self.assertTrue(tinker_platform.kit_command("windows", "teardown", ["--yes", "--images"])[3]
                        .endswith("teardown.ps1' -Confirm:$false -Images"))
        self.assertEqual(tinker_platform.kit_command("windows", "kit", ["--project", "x", "Stop-Agent", "tester"])[3],
                         f". '{tinker_platform.KIT / 'kit.ps1'}' -Project 'x'; Stop-Agent tester")
        for bad in (["--owner-npub"], ["--nope", "x"]):
            with self.subTest(args=bad), self.assertRaises(ValueError):
                tinker_platform.kit_command("windows", "setup", bad)

    def test_the_command_line_shows_and_stores_the_choice(self):
        script = str(ROOT / "scripts" / "tinker_platform.py")
        out = subprocess.run([sys.executable, script], capture_output=True, text=True, check=True,
                             env={"TINKER_PLATFORM": "linux", "PATH": ""})
        self.assertIn("Platform: linux (from TINKER_PLATFORM)", out.stdout)
        self.assertIn("setup.sh", out.stdout)
        bad = subprocess.run([sys.executable, script, "set", "debian"], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)

    def test_the_installer_accepts_the_platform(self):
        import install_apps
        out = subprocess.run([sys.executable, str(ROOT / "scripts" / "install_apps.py"), "--help"],
                             capture_output=True, text=True, check=True)
        self.assertIn("--platform", out.stdout)
        self.assertIs(install_apps.tinker_platform, tinker_platform)


if __name__ == "__main__":
    unittest.main()
