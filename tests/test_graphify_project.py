"""Git-backed checks for on-demand Graphify graphs."""

import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "graphify_project.py"


def helper():
    spec = importlib.util.spec_from_file_location("graphify_project", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(path, *args):
    result = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True, check=False)
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)}: {result.stderr}")
    return result.stdout.strip()


def labels(result):
    graph = json.loads(Path(result["graph_json"]).read_text(encoding="utf-8"))
    return {node.get("label") for node in graph["nodes"]}


class GraphifyProjectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        base = Path(self.temporary.name)
        self.package = base / "bot"
        self.package.mkdir()
        self.primary = base / "source"
        self.primary.mkdir()
        git(self.primary, "init", "-q", "-b", "main")
        git(self.primary, "config", "user.name", "Graphify Test")
        git(self.primary, "config", "user.email", "graphify@example.invalid")
        (self.primary / "base.py").write_text("class SharedBaseSymbol:\n    pass\n", encoding="utf-8")
        (self.primary / ".gitignore").write_text("ignored.py\n", encoding="utf-8")
        (self.primary / ".graphifyignore").write_text("!ignored.py\n", encoding="utf-8")
        git(self.primary, "add", ".")
        git(self.primary, "commit", "-qm", "base")
        self.alpha = base / "ticket-77-a"
        self.beta = base / "ticket-77-b"
        git(self.primary, "worktree", "add", "-qb", "ticket-77-a", str(self.alpha), "HEAD")
        git(self.primary, "worktree", "add", "-qb", "ticket-77-b", str(self.beta), "HEAD")

    def commit_file(self, checkout, name, content):
        (checkout / name).write_text(content, encoding="utf-8")
        git(checkout, "add", name)
        git(checkout, "commit", "-qm", name)
        return git(checkout, "rev-parse", "HEAD")

    def test_selection_requires_unique_registered_worktree(self):
        graph = helper()
        self.assertTrue(hasattr(graph, "resolve_worktree"), "worktree selection API is missing")
        self.assertEqual(graph.resolve_worktree(self.primary, worktree_path=self.alpha)[1], self.alpha.resolve())
        self.assertEqual(graph.resolve_worktree(self.primary, ticket="ticket-77-a")[1], self.alpha.resolve())
        with self.assertRaisesRegex(ValueError, "registered linked worktree"):
            graph.resolve_worktree(self.primary, worktree_path=self.primary)
        with self.assertRaisesRegex(ValueError, "No worktree matches"):
            graph.resolve_worktree(self.primary, ticket="999")
        with self.assertRaisesRegex(ValueError, "2 worktrees match"):
            graph.resolve_worktree(self.primary, ticket="77")
        with self.assertRaisesRegex(ValueError, "pass --worktree-path"):
            graph.resolve_worktree(self.alpha)
        self.assertFalse((self.package / ".tinker" / "graphs").exists())

    def test_detached_worktree_and_invalid_source_metadata_are_controlled(self):
        graph = helper()
        git(self.alpha, "switch", "--detach", "-q")
        self.assertIsNone(graph._state(self.alpha)["branch"])
        graph_dir = graph.graph_parent(self.alpha, self.package, "worktrees") / "graphify-out"
        graph_dir.mkdir(parents=True)
        (graph_dir / "source.json").write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid graph source identity"):
            graph.graph_status(self.primary, self.package, worktree_path=self.alpha)

    def product_repository(self, name, branches):
        repo = Path(self.temporary.name) / name
        repo.mkdir()
        git(repo, "init", "-q", "-b", branches[0])
        git(repo, "config", "user.name", "Graphify Test")
        git(repo, "config", "user.email", "graphify@example.invalid")
        self.commit_file(repo, "app.py", "class App:\n    pass\n")
        for branch in branches[1:]:
            git(repo, "switch", "-qc", branch)
        return repo

    def test_no_repository_name_selects_a_baseline_branch(self):
        graph = helper()
        for name in ("sample-web", "sample-api", "acme-widgets"):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "pass --baseline-branch"):
                graph._baseline_branch(Path(name), None)
        self.assertEqual(graph._baseline_branch(self.primary, "main"), "main")
        with self.assertRaisesRegex(ValueError, "does not exist"):
            graph._baseline_branch(self.primary, "development")
        product = self.product_repository("sample-web", ["development", "release"])
        with self.assertRaisesRegex(ValueError, "pass --baseline-branch"):
            graph.build_graph(product, self.package, graphify_bin="missing-graphify-cli")
        # An explicit branch is honoured whatever the repository is called: selection and the clean
        # baseline check pass, and only the deliberately missing CLI stops the run.
        with self.assertRaisesRegex(RuntimeError, "Graphify CLI is unavailable"):
            graph.build_graph(product, self.package, graphify_bin="missing-graphify-cli", baseline_branch="release")
        self.assertFalse((self.package / ".tinker" / "graphs").exists())

    def test_baseline_status_uses_the_recorded_branch_unless_one_is_given(self):
        graph = helper()
        head = git(self.primary, "rev-parse", "HEAD")
        graph_dir = graph.graph_parent(self.primary, self.package, "baselines") / "graphify-out"
        graph._identity(graph_dir, self.primary.resolve(), "baselines", create=True)
        for name in ("graph.json", "manifest.json", "graph.html"):
            (graph_dir / name).write_text("present", encoding="utf-8")
        graph._write_revision(graph_dir, self.primary.resolve(), "baselines", head, head, "main",
                              graph.graphify_version())
        self.assertTrue(graph.graph_status(self.primary, self.package)["verified"])
        self.assertTrue(graph.graph_status(self.primary, self.package, baseline_branch="main")["verified"])
        git(self.primary, "branch", "other")
        self.assertFalse(graph.graph_status(self.primary, self.package, baseline_branch="other")["verified"])
        git(self.primary, "switch", "-q", "other")
        self.assertFalse(graph.graph_status(self.primary, self.package)["verified"])  # off its recorded branch

    def test_cli_requires_an_explicit_baseline_branch_to_ensure(self):
        graph = helper()
        with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            self.assertEqual(graph.main([str(self.primary)]), 1)
        self.assertIn("pass --baseline-branch", stderr.getvalue())

    def test_hardlinked_graph_file_is_rejected_before_extraction(self):
        graph = helper()
        graph_dir = graph.graph_parent(self.alpha, self.package, "worktrees") / "graphify-out"
        graph_dir.mkdir(parents=True)
        outside = self.package / "sentinel.json"
        outside.write_text("preserve me", encoding="utf-8")
        try:
            os.link(outside, graph_dir / "graph.json")
        except OSError as exc:
            self.skipTest(f"hardlinks unavailable: {exc}")
        self.assertTrue(hasattr(graph, "_assert_private_files"), "private graph file guard is missing")
        with self.assertRaisesRegex(ValueError, "linked graph file"):
            graph._assert_private_files(graph_dir)
        self.assertEqual(outside.read_text(encoding="utf-8"), "preserve me")

    def test_invalid_seed_revision_cannot_verify_a_handoff_link(self):
        graph = helper()
        graph_dir = graph.graph_parent(self.alpha, self.package, "worktrees") / "graphify-out"
        graph._identity(graph_dir, self.alpha.resolve(), "worktrees", create=True)
        for name in ("graph.json", "manifest.json", "graph.html"):
            (graph_dir / name).write_text("present", encoding="utf-8")
        (graph_dir / "revision.json").write_text(json.dumps({
            "source": str(self.alpha.resolve()), "scope": "worktrees",
            "head": git(self.alpha, "rev-parse", "HEAD"), "baseline_head": "0" * 40,
        }), encoding="utf-8")
        status = graph.graph_status(self.primary, self.package, worktree_path=self.alpha)
        self.assertFalse(status["verified"])
        self.assertNotIn("graph_html", status)
        with self.assertRaisesRegex(RuntimeError, "No current, source-verified graph"):
            graph.query_graph(self.primary, "SharedBaseSymbol", self.package, worktree_path=self.alpha)

    @unittest.skipUnless(shutil.which("graphify"), "optional Graphify CLI unavailable")
    def test_independent_worktrees_behind_baseline_and_cache_only_cleanup(self):
        graph = helper()
        self.assertTrue(hasattr(graph, "resolve_worktree"), "worktree selection API is missing")
        alpha_head = self.commit_file(self.alpha, "alpha.py", "class AlphaOnlySymbol:\n    pass\n")
        (self.alpha / "ignored.py").write_text("class IgnoredUncommittedSymbol:\n    pass\n", encoding="utf-8")
        self.assertFalse(git(self.alpha, "status", "--porcelain=v1", "--untracked-files=all"))
        self.commit_file(self.beta, "beta.py", "class BetaOnlySymbol:\n    pass\n")
        self.commit_file(self.primary, "newer.py", "class NewerBaselineSymbol:\n    pass\n")
        (self.primary / "ignored.py").write_text("class IgnoredBaselineUncommittedSymbol:\n    pass\n", encoding="utf-8")
        self.assertFalse(git(self.primary, "status", "--porcelain=v1", "--untracked-files=all"))
        baseline = graph.build_graph(self.primary, self.package, baseline_branch="main")
        self.assertNotIn("IgnoredBaselineUncommittedSymbol", labels(baseline))
        with self.assertRaisesRegex(RuntimeError, "No current, source-verified graph"):
            graph.query_graph(self.primary, "SharedBaseSymbol", self.package, worktree_path=self.alpha)
        alpha = graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        beta = graph.build_graph(self.primary, self.package, worktree_path=self.beta, baseline_branch="main")
        self.assertEqual(len(graph._worktrees(self.primary)), 3, "temporary commit checkouts must be removed")
        self.assertNotEqual(alpha["graph_json"], beta["graph_json"])
        self.assertEqual(alpha["head"], alpha_head)
        self.assertEqual(alpha["baseline_head"], baseline["head"])
        alpha_dir = Path(alpha["graph_json"]).parent
        alpha_graph_bytes = Path(alpha["graph_json"]).read_bytes()
        alpha_revision = alpha_dir / "revision.json"
        revision_bytes = alpha_revision.read_bytes()
        alpha_revision.unlink()
        with self.assertRaisesRegex(ValueError, "metadata"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        self.assertEqual(Path(alpha["graph_json"]).read_bytes(), alpha_graph_bytes)
        alpha_revision.write_bytes(revision_bytes)
        self.assertTrue({"SharedBaseSymbol", "AlphaOnlySymbol"} <= labels(alpha))
        self.assertFalse({"BetaOnlySymbol", "NewerBaselineSymbol", "IgnoredUncommittedSymbol"} & labels(alpha))
        self.assertIn("BetaOnlySymbol", labels(beta))
        self.assertFalse({"AlphaOnlySymbol", "NewerBaselineSymbol"} & labels(beta))
        self.assertFalse((self.primary / "graphify-out").exists())
        self.assertFalse((self.alpha / "graphify-out").exists())
        self.assertFalse(Path(alpha["graph_json"]).samefile(baseline["graph_json"]))
        self.assertFalse(Path(alpha["manifest_json"]).samefile(baseline["manifest_json"]))
        status = graph.graph_status(self.primary, self.package, worktree_path=self.beta)
        self.assertTrue(status["verified"])
        self.assertEqual(status["source"], str(self.beta.resolve()))
        self.assertEqual(status["graph_html"], beta["graph_html"])
        answer = graph.query_graph(self.primary, "BetaOnlySymbol", self.package, worktree_path=self.beta, budget=800)
        self.assertIn("BetaOnlySymbol", answer)
        self.assertIn(str(self.beta.resolve()), answer)
        alpha_file = self.alpha / "alpha.py"
        committed_alpha = alpha_file.read_bytes()
        git(self.alpha, "update-index", "--skip-worktree", "alpha.py")
        alpha_file.write_text("class HiddenTrackedSymbol:\n    pass\n", encoding="utf-8")
        self.assertFalse(git(self.alpha, "status", "--porcelain=v1", "--untracked-files=all"))
        self.assertFalse(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        alpha_file.write_bytes(committed_alpha)
        git(self.alpha, "update-index", "--no-skip-worktree", "alpha.py")
        with self.assertRaisesRegex(ValueError, "worktree"):
            graph.query_graph(self.primary, "SharedBaseSymbol", self.package)
        seed = alpha["baseline_head"]
        self.commit_file(self.primary, "latest.py", "class LatestBaselineSymbol:\n    pass\n")
        self.assertTrue(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])
        unchanged = graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        self.assertEqual(unchanged["status"], "current")
        self.assertEqual(unchanged["baseline_head"], seed)
        self.assertEqual(unchanged["head"], alpha_head)
        self.commit_file(self.alpha, "more.py", "class AlphaAfterBaselineAdvance:\n    pass\n")
        updated = graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        self.assertEqual(updated["baseline_head"], seed)
        self.assertIn("AlphaAfterBaselineAdvance", labels(updated))
        self.assertFalse({"NewerBaselineSymbol", "LatestBaselineSymbol"} & labels(updated))
        cache = Path(updated["graph_json"]).parent / "cache"
        cache.mkdir(exist_ok=True)
        (cache / "transient").write_text("cache", encoding="utf-8")
        legacy = self.package / ".tinker" / "graphs" / "legacy-project"
        legacy.mkdir()
        (legacy / "graph.json").write_text("legacy", encoding="utf-8")
        self.assertTrue(graph.cleanup_graph(self.primary, self.package, worktree_path=self.alpha)["removed_cache"])
        self.assertFalse(cache.exists())
        for name in ("graph.json", "manifest.json", "graph.html", "revision.json"):
            self.assertTrue((cache.parent / name).is_file(), name)
        self.assertEqual((legacy / "graph.json").read_text(encoding="utf-8"), "legacy")
        self.assertTrue(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])

    @unittest.skipUnless(shutil.which("graphify"), "optional Graphify CLI unavailable")
    def test_dirty_baseline_and_worktree_block_graphs_until_commit(self):
        graph = helper()
        self.assertTrue(hasattr(graph, "resolve_worktree"), "worktree selection API is missing")
        baseline = graph.build_graph(self.primary, self.package, baseline_branch="main")
        alpha = graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        baseline_bytes = Path(baseline["graph_json"]).read_bytes()
        alpha_bytes = Path(alpha["graph_json"]).read_bytes()
        base_file = self.primary / "base.py"
        original_base = base_file.read_bytes()
        base_file.write_text("class UnstagedBaseline: pass\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        base_file.write_bytes(original_base)
        (self.primary / "untracked.py").write_text("class UntrackedBaseline: pass\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        git(self.primary, "add", "untracked.py")
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        git(self.primary, "restore", "--staged", "untracked.py")
        (self.primary / "untracked.py").unlink()
        git(self.primary, "switch", "-qc", "wrong-branch")
        with self.assertRaisesRegex(ValueError, "baseline branch"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        git(self.primary, "switch", "-q", "main")
        self.assertEqual(Path(baseline["graph_json"]).read_bytes(), baseline_bytes)
        self.assertEqual(Path(alpha["graph_json"]).read_bytes(), alpha_bytes)
        alpha_base = self.alpha / "base.py"
        alpha_original = alpha_base.read_bytes()
        alpha_base.write_text("class UnstagedWorktree: pass\n", encoding="utf-8")
        self.assertFalse(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        alpha_base.write_bytes(alpha_original)
        (self.alpha / "draft.py").write_text("class DraftOnly: pass\n", encoding="utf-8")
        status = graph.graph_status(self.primary, self.package, worktree_path=self.alpha)
        self.assertFalse(status["verified"])
        self.assertNotIn("graph_html", status)
        with self.assertRaisesRegex(RuntimeError, "No current, source-verified graph"):
            graph.query_graph(self.primary, "SharedBaseSymbol", self.package, worktree_path=self.alpha)
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        git(self.alpha, "add", "draft.py")
        with self.assertRaisesRegex(ValueError, "uncommitted"):
            graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        git(self.alpha, "commit", "-qm", "draft")
        self.assertFalse(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])
        refreshed = graph.build_graph(self.primary, self.package, worktree_path=self.alpha, baseline_branch="main")
        self.assertIn("DraftOnly", labels(refreshed))
        self.assertTrue(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])

    def test_graphify_version_reads_the_release_or_nothing(self):
        graph = helper()

        def completed(code):
            return subprocess.CompletedProcess(["graphify", "--version"], code, "graphify 0.9.105\n", "")

        with mock.patch.object(graph.shutil, "which", return_value="graphify"):
            with mock.patch.object(graph.subprocess, "run", return_value=completed(0)):
                self.assertEqual(graph.graphify_version(), "0.9.105")
            with mock.patch.object(graph.subprocess, "run", return_value=completed(2)):
                self.assertIsNone(graph.graphify_version())
            with mock.patch.object(graph.subprocess, "run", side_effect=OSError("denied")):
                self.assertIsNone(graph.graphify_version())
        with mock.patch.object(graph.shutil, "which", return_value=None):
            self.assertIsNone(graph.graphify_version())

    def test_a_graph_too_large_for_the_html_view_still_completes(self):
        graph = helper()
        graph_dir = graph.graph_parent(self.alpha, self.package, "worktrees") / "graphify-out"
        graph_dir.mkdir(parents=True)
        error = ["graphify export failed (exit 1): 6000 communities, too large for HTML viz"]

        def run(args, source, out, graphify_bin):
            if args[0] != "extract":
                raise RuntimeError(error[0])
            for name in ("graph.json", "manifest.json"):
                (out / name).write_text("{}", encoding="utf-8")
            return ""

        with mock.patch.object(graph, "_graphify", run):
            graph._extract(self.alpha, graph_dir, "graphify")
            self.assertIn("too large", (graph_dir / "graph.html").read_text(encoding="utf-8"))
            self.assertTrue(graph._valid_files(graph_dir))
            error[0] = "graphify export failed (exit 1): disk full"
            with self.assertRaisesRegex(RuntimeError, "disk full"):
                graph._extract(self.alpha, graph_dir, "graphify")
        self.assertFalse((graph_dir / "graph.html").exists())

    def test_a_new_graphify_release_rebuilds_from_scratch_and_reseeds_worktrees(self):
        graph = helper()
        release, extracts = ["1.0.0"], []

        def run(args, source, graph_dir, graphify_bin):
            manifest = graph_dir / "manifest.json"
            if args[0] == "extract":  # record the scope and the index an incremental run would start from
                extracts.append((graph_dir.parts[-3], manifest.read_text(encoding="utf-8")
                                 if manifest.is_file() else None))
                (graph_dir / "graph.json").write_text(json.dumps({"nodes": []}), encoding="utf-8")
                manifest.write_text(release[0], encoding="utf-8")
            else:
                (graph_dir / "graph.html").write_text("<html></html>", encoding="utf-8")
            return ""

        def build(**options):
            return graph.build_graph(self.primary, self.package, baseline_branch="main", **options)

        with mock.patch.object(graph, "graphify_version", side_effect=lambda *_: release[0]), \
                mock.patch.object(graph, "_graphify", run), \
                mock.patch.object(graph.shutil, "which", return_value="graphify"):
            build(worktree_path=self.alpha)
            self.assertEqual(build(worktree_path=self.alpha)["status"], "current")
            self.assertEqual(extracts, [("baselines", None), ("worktrees", "1.0.0")])
            head = self.commit_file(self.primary, "newer.py", "class Newer:\n    pass\n")
            build()  # same release, new HEAD: incremental from the indexed baseline
            self.assertEqual(extracts[2], ("baselines", "1.0.0"))
            release[0] = "1.1.0"
            alpha = build(worktree_path=self.alpha)
            self.assertEqual(extracts[3:], [("baselines", None), ("worktrees", "1.1.0")])
            revision = json.loads((Path(alpha["graph_json"]).parent / "revision.json").read_text(encoding="utf-8"))
            self.assertEqual((revision["graphify"], revision["baseline_head"]), ("1.1.0", head))
            release[0] = None  # an unreadable release never forces a rebuild
            self.assertTrue(graph.graph_status(self.primary, self.package, worktree_path=self.alpha)["verified"])
            release[0] = "1.2.0"
            status = graph.graph_status(self.primary, self.package, worktree_path=self.alpha)
            self.assertFalse(status["verified"])
            self.assertIn("Graphify release", status["reason"])


if __name__ == "__main__":
    unittest.main()
