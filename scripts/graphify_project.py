"""Build or inspect a clean Git baseline and independent linked-worktree graphs."""

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _run(args, cwd, *, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, errors="replace", check=False)
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()[-2000:]
        raise RuntimeError(f"{' '.join(str(item) for item in args[:2])} failed (exit {result.returncode}): {detail}")
    return result.stdout.strip()


def _git(path, *args):
    return _run(["git", "-C", str(path), *args], path)


def _same_path(left, right):
    if not isinstance(left, (str, os.PathLike)) or not isinstance(right, (str, os.PathLike)):
        return False
    return os.path.normcase(str(Path(left).resolve())) == os.path.normcase(str(Path(right).resolve()))


def _repository_root(path):
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Pass an absolute repository path")
    path = path.resolve(strict=True)
    if not path.is_dir():
        raise ValueError(f"Repository is not a directory: {path}")
    return Path(_git(path, "rev-parse", "--show-toplevel")).resolve(strict=True)


def _worktrees(source):
    entries = []
    for block in _git(source, "worktree", "list", "--porcelain").split("\n\n"):
        fields = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if "worktree" in fields:
            entries.append(fields)
    if not entries or "bare" in entries[0]:
        raise ValueError(f"Graphify needs a non-bare primary checkout for {source}")
    return entries


def resolve_worktree(project, *, worktree_path=None, ticket=None):
    """Return (primary, selected linked worktree or None) from Git's registration."""
    source = _repository_root(project)
    entries = _worktrees(source)
    primary = Path(entries[0]["worktree"]).resolve(strict=True)
    registered = [(Path(entry["worktree"]).resolve(strict=True), entry.get("branch", ""))
                  for entry in entries[1:] if "prunable" not in entry and Path(entry["worktree"]).is_dir()]
    if worktree_path is not None:
        wanted = _repository_root(worktree_path)
        matches = [path for path, _ in registered if _same_path(path, wanted)]
        if len(matches) != 1:
            raise ValueError(f"{worktree_path} is not a registered linked worktree of {primary}")
        return primary, matches[0]
    if ticket is not None:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", ticket):
            raise ValueError("Ticket must contain only letters, digits, '.', '_' or '-'")
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(ticket) + r"(?![A-Za-z0-9])", re.I)
        matches = [path for path, branch in registered if pattern.search(path.name) or pattern.search(branch)]
        if len(matches) == 1:
            return primary, matches[0]
        if not matches:
            raise ValueError(f"No worktree matches ticket '{ticket}' in {primary}; pass --worktree-path")
        raise ValueError(f"{len(matches)} worktrees match ticket '{ticket}' in {primary}; pass --worktree-path")
    if not _same_path(source, primary):
        raise ValueError(f"{source} is a linked worktree; pass --worktree-path or a unique --ticket")
    return primary, None


def _baseline_branch(primary, explicit):
    """The branch the caller chose, validated against this repository. No repository name selects
    one: invocations that relied on an earlier built-in default now pass --baseline-branch."""
    if not explicit:
        raise ValueError(f"Establishing a baseline for {primary} needs an explicit branch; pass --baseline-branch <branch>")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", explicit):
        raise ValueError(f"Invalid baseline branch: {explicit}")
    try:
        _git(primary, "rev-parse", "--verify", "--quiet", f"refs/heads/{explicit}")
    except RuntimeError:
        raise ValueError(f"Baseline branch '{explicit}' does not exist in {primary}") from None
    return explicit


def _state(path):
    branch = subprocess.run(
        ["git", "-C", str(path), "symbolic-ref", "--quiet", "--short", "HEAD"],
        cwd=path, capture_output=True, text=True, errors="replace", check=False,
    )
    if branch.returncode not in (0, 1):
        raise RuntimeError(f"Cannot read Git branch for {path}: {branch.stderr.strip()}")
    # Git status trusts skip-worktree and assume-unchanged index flags. Such
    # checkouts cannot prove that their live files match the committed tree.
    flags = _git(path, "ls-files", "-v", "-z").split("\0")
    hidden = any(entry and (entry[0] == "S" or entry[0].islower()) for entry in flags)
    return {
        "head": _git(path, "rev-parse", "HEAD"),
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "dirty": hidden or bool(_git(path, "status", "--porcelain=v1", "--untracked-files=all")),
    }


def _clean_baseline(primary, branch):
    state = _state(primary)
    if state["branch"] != branch:
        raise ValueError(f"Primary checkout is on '{state['branch']}', expected baseline branch '{branch}'")
    if state["dirty"]:
        raise ValueError(f"Primary checkout has uncommitted changes: {primary}")
    return state


def _clean_worktree(path):
    state = _state(path)
    if state["dirty"]:
        raise ValueError(f"Worktree has uncommitted changes: {path}; commit and reindex")
    return state


def graph_parent(project, package_root=PACKAGE_ROOT, scope="baselines"):
    """Stable, path-keyed output parent; old flat graph directories stay untouched."""
    if scope not in {"baselines", "worktrees"}:
        raise ValueError(f"Unknown graph scope: {scope}")
    project = Path(project).resolve(strict=True)
    package_root = Path(package_root).resolve(strict=True)
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", project.name).strip("-.") or "project"
    digest = hashlib.sha256(os.path.normcase(str(project)).encode("utf-8")).hexdigest()[:16]
    result = package_root / ".tinker" / "graphs" / scope / f"{slug}-{digest}"
    if not result.resolve().is_relative_to(package_root):
        raise ValueError("Graph output escapes the Tinker checkout")
    return result


def _graph_dir(source, package_root, scope):
    return graph_parent(source, package_root, scope) / "graphify-out"


def _identity(graph_dir, source, scope, *, create=False):
    graph_dir = Path(graph_dir)
    package_root = graph_dir.parents[4].resolve(strict=True)
    if not graph_dir.resolve().is_relative_to(package_root):
        raise ValueError("Graph output escapes the Tinker checkout")
    identity = graph_dir / "source.json"
    if graph_dir.exists():
        if not identity.is_file():
            raise ValueError(f"Existing graph has no source identity: {graph_dir}")
        try:
            recorded = json.loads(identity.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Invalid graph source identity: {identity}") from exc
        if not isinstance(recorded, dict):
            raise ValueError(f"Invalid graph source identity: {identity}")
        if recorded.get("scope") != scope or not _same_path(recorded.get("source"), source):
            raise ValueError(f"Graph output belongs to a different source: {graph_dir}")
    elif create:
        graph_dir.mkdir(parents=True)
        identity.write_text(json.dumps({"source": str(source), "scope": scope}) + "\n", encoding="utf-8")
    return identity.is_file()


def _metadata(graph_dir):
    path = graph_dir / "revision.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Invalid graph revision metadata: {path}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Invalid graph revision metadata: {path}")
    return data


def _assert_private_files(graph_dir):
    for directory in (graph_dir, *graph_dir.parents):
        if directory.is_symlink() or (hasattr(directory, "is_junction") and directory.is_junction()):
            raise ValueError(f"Graph output contains a linked directory: {directory}")
    for name in ("source.json", "graph.json", "manifest.json", "graph.html", "revision.json"):
        path = graph_dir / name
        if path.is_symlink() or (path.is_file() and path.stat().st_nlink > 1):
            raise ValueError(f"Graph output contains a linked graph file: {path}")


def _valid_files(graph_dir):
    _assert_private_files(graph_dir)
    for name in ("graph.json", "manifest.json", "graph.html"):
        path = graph_dir / name
        if not path.is_file() or not path.stat().st_size:
            return False
    return True


def graph_status(project, package_root=PACKAGE_ROOT, *, worktree_path=None, ticket=None, baseline_branch=None):
    """Read-only freshness check. Only verified results expose graph paths for handoff."""
    primary, selected = resolve_worktree(project, worktree_path=worktree_path, ticket=ticket)
    source = selected or primary
    scope = "worktrees" if selected else "baselines"
    graph_dir = _graph_dir(source, package_root, scope)
    result = {"verified": False, "source": str(source), "scope": scope, "reason": "No graph index found"}
    if not graph_dir.exists():
        return result
    _identity(graph_dir, source, scope)
    data = _metadata(graph_dir)
    if not data or not _valid_files(graph_dir):
        result["reason"] = "Graph files or revision metadata are missing"
        return result
    state = _state(source)
    if state["dirty"]:
        result["reason"] = "Checkout has uncommitted changes"
        return result
    if not selected:  # without an explicit branch, check against the branch this baseline recorded
        branch = _baseline_branch(primary, baseline_branch) if baseline_branch else data.get("branch")
        if not isinstance(branch, str) or state["branch"] != branch or data.get("branch") != branch:
            result["reason"] = (f"Baseline branch differs from '{branch}'" if isinstance(branch, str)
                                else "Baseline graph records no branch; pass --baseline-branch")
            return result
    seed = data.get("baseline_head")
    if (not _same_path(data.get("source"), source) or data.get("head") != state["head"]
            or data.get("scope") != scope or not isinstance(seed, str)
            or not re.fullmatch(r"[0-9a-f]{40,64}", seed)):
        result["reason"] = "Graph source, HEAD or seed baseline revision differs"
        return result
    try:
        _git(primary, "cat-file", "-e", data["baseline_head"] + "^{commit}")
    except RuntimeError:
        result["reason"] = "Seed baseline commit cannot be verified"
        return result
    result.update({
        "verified": True,
        "head": state["head"],
        "baseline_head": data["baseline_head"],
        "graph_json": str(graph_dir / "graph.json"),
        "manifest_json": str(graph_dir / "manifest.json"),
        "graph_html": str(graph_dir / "graph.html"),
    })
    result.pop("reason")
    return result


def _graphify(args, source, graph_dir, graphify_bin):
    env = os.environ.copy()
    env["GRAPHIFY_OUT"] = str(graph_dir)
    return _run([graphify_bin, *args], source, env=env)


@contextmanager
def _head_snapshot(source, head):
    """Scan a detached checkout of HEAD, never the possibly ignored live files."""
    root = Path(tempfile.mkdtemp(prefix="tinker-graphify-")).resolve()
    if root.parent != Path(tempfile.gettempdir()).resolve():
        raise RuntimeError(f"Unexpected Graphify snapshot location: {root}")
    hooks = root / "hooks"
    hooks.mkdir()
    snapshot = root / os.urandom(16).hex()
    env = os.environ.copy()
    env["GIT_LFS_SKIP_SMUDGE"] = "1"
    env["GIT_TERMINAL_PROMPT"] = "0"
    registered = False
    try:
        _run(["git", "-C", str(source), "-c", f"core.hooksPath={hooks}",
              "worktree", "add", "--detach", str(snapshot), head], source, env=env)
        registered = True
        state = _state(snapshot)
        if state["head"] != head or state["dirty"]:
            raise RuntimeError(f"Graphify snapshot is not a clean checkout of {head}")
        yield snapshot
    finally:
        if registered:
            _run(["git", "-C", str(source), "worktree", "remove", "--force", str(snapshot)],
                 source, env=env)
        hooks.rmdir()
        root.rmdir()


def _extract(source, graph_dir, graphify_bin):
    _assert_private_files(graph_dir)
    (graph_dir / "graph.html").unlink(missing_ok=True)
    _graphify(["extract", str(source), "--code-only", "--out", str(graph_dir.parent)], source, graph_dir, graphify_bin)
    for name in ("graph.json", "manifest.json"):
        path = graph_dir / name
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            raise RuntimeError(f"Graphify extraction did not produce {path}")
    _graphify(["export", "html", "--graph", str(graph_dir / "graph.json")], source, graph_dir, graphify_bin)
    if not _valid_files(graph_dir):
        raise RuntimeError(f"Graphify did not produce a complete graph at {graph_dir}")


def _write_revision(graph_dir, source, scope, head, baseline_head, branch=None):
    data = {"source": str(source), "scope": scope, "head": head, "baseline_head": baseline_head}
    if branch:
        data["branch"] = branch
    (graph_dir / "revision.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _result(source, graph_dir, status, data):
    return {
        "status": status, "source": str(source), "head": data["head"],
        "baseline_head": data["baseline_head"], "graph_json": str(graph_dir / "graph.json"),
        "manifest_json": str(graph_dir / "manifest.json"), "graph_html": str(graph_dir / "graph.html"),
    }


def build_graph(project, package_root=PACKAGE_ROOT, graphify_bin="graphify", *,
                worktree_path=None, ticket=None, baseline_branch=None):
    """Ensure baseline first, then index only the selected worktree's clean HEAD."""
    primary, selected = resolve_worktree(project, worktree_path=worktree_path, ticket=ticket)
    branch = _baseline_branch(primary, baseline_branch)
    baseline_before = _clean_baseline(primary, branch)
    if not shutil.which(graphify_bin):
        raise RuntimeError("Graphify CLI is unavailable; install the official graphifyy package")
    base_dir = _graph_dir(primary, package_root, "baselines")
    if base_dir.exists():
        _identity(base_dir, primary, "baselines")
        previous_base = _metadata(base_dir)
        if previous_base and (not _same_path(previous_base.get("source"), primary)
                              or previous_base.get("scope") != "baselines"):
            raise ValueError(f"Baseline graph revision belongs to a different source: {base_dir}")
    base_status = graph_status(primary, package_root, baseline_branch=branch)
    if not base_status["verified"]:
        _identity(base_dir, primary, "baselines", create=True)
        _assert_private_files(base_dir)
        _write_revision(base_dir, primary, "baselines", None, baseline_before["head"], branch)
        with _head_snapshot(primary, baseline_before["head"]) as snapshot:
            _extract(snapshot, base_dir, graphify_bin)
        if _clean_baseline(primary, branch)["head"] != baseline_before["head"]:
            raise RuntimeError("Baseline changed during extraction; graph is unavailable")
        _write_revision(base_dir, primary, "baselines", baseline_before["head"], baseline_before["head"], branch)
        base_result = _result(primary, base_dir, "updated", _metadata(base_dir))
    else:
        base_result = _result(primary, base_dir, "current", _metadata(base_dir))
    if selected is None:
        return base_result
    selected_before = _clean_worktree(selected)
    graph_dir = _graph_dir(selected, package_root, "worktrees")
    if graph_dir.exists():
        _identity(graph_dir, selected, "worktrees")
    status = graph_status(primary, package_root, worktree_path=selected)
    if status["verified"]:
        return _result(selected, graph_dir, "current", _metadata(graph_dir))
    previous = _metadata(graph_dir) if graph_dir.exists() else None
    if graph_dir.exists() and previous is None and any(
            (graph_dir / name).exists() for name in ("graph.json", "manifest.json", "revision.json")):
        raise ValueError(f"Existing worktree graph lacks valid revision metadata: {graph_dir}")
    if previous and (not _same_path(previous.get("source"), selected)
                     or previous.get("scope") != "worktrees"):
        raise ValueError(f"Graph output belongs to a different source: {graph_dir}")
    seed = previous.get("baseline_head") if previous else baseline_before["head"]
    if previous and (not isinstance(seed, str) or not re.fullmatch(r"[0-9a-f]{40,64}", seed)):
        raise ValueError(f"Invalid seed baseline revision: {graph_dir}")
    if previous:
        try:
            _git(primary, "cat-file", "-e", seed + "^{commit}")
        except RuntimeError as exc:
            raise ValueError(f"Seed baseline revision is not a repository commit: {graph_dir}") from exc
        if not all((graph_dir / name).is_file() for name in ("graph.json", "manifest.json")):
            raise ValueError(f"Existing worktree graph files are incomplete: {graph_dir}")
    _identity(graph_dir, selected, "worktrees", create=True)
    if not previous:
        _assert_private_files(base_dir)
        _assert_private_files(graph_dir)
        for name in ("graph.json", "manifest.json"):
            source_file = base_dir / name
            shutil.copy2(source_file, graph_dir / name)
        seed = baseline_before["head"]
    _assert_private_files(graph_dir)
    _write_revision(graph_dir, selected, "worktrees", None, seed)
    with _head_snapshot(selected, selected_before["head"]) as snapshot:
        _extract(snapshot, graph_dir, graphify_bin)
    if _clean_worktree(selected)["head"] != selected_before["head"]:
        raise RuntimeError("Worktree HEAD changed during extraction; graph is unavailable")
    _write_revision(graph_dir, selected, "worktrees", selected_before["head"], seed)
    return _result(selected, graph_dir, "updated", _metadata(graph_dir))


def query_graph(project, question, package_root=PACKAGE_ROOT, *, worktree_path=None,
                ticket=None, budget=1200, graphify_bin="graphify"):
    if not worktree_path and not ticket:
        raise ValueError("Select a worktree with --worktree-path or --ticket")
    if not 1 <= budget <= 100000:
        raise ValueError("Budget must be between 1 and 100000")
    status = graph_status(project, package_root, worktree_path=worktree_path, ticket=ticket)
    if not status["verified"]:
        raise RuntimeError(f"No current, source-verified graph for {status['source']}: {status['reason']}")
    output = _graphify(["query", question, "--graph", status["graph_json"], "--budget", str(budget)],
                       Path(status["source"]), Path(status["graph_json"]).parent, graphify_bin)
    return f"Source: {status['source']} at {status['head']}\n{output}"


def cleanup_graph(project, package_root=PACKAGE_ROOT, *, worktree_path=None, ticket=None):
    if not worktree_path and not ticket:
        raise ValueError("Select a worktree with --worktree-path or --ticket")
    _, selected = resolve_worktree(project, worktree_path=worktree_path, ticket=ticket)
    graph_dir = _graph_dir(selected, package_root, "worktrees")
    if not graph_dir.exists():
        return {"source": str(selected), "removed_cache": False}
    _identity(graph_dir, selected, "worktrees")
    _assert_private_files(graph_dir)
    cache = graph_dir / "cache"
    if (cache.is_symlink() or (hasattr(cache, "is_junction") and cache.is_junction())
            or cache.resolve() != graph_dir.resolve() / "cache"):
        raise ValueError(f"Unsafe Graphify cache path: {cache}")
    removed = cache.is_dir()
    if removed:
        shutil.rmtree(cache)
    return {"source": str(selected), "removed_cache": removed}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="Absolute path to the repository checkout")
    parser.add_argument("--action", choices=("ensure", "status", "query", "cleanup"), default="ensure")
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--worktree-path", type=Path)
    selection.add_argument("--ticket")
    parser.add_argument("--baseline-branch", help="branch the primary checkout's baseline follows; required to "
                                                  "ensure a graph, optional for status (default: the recorded branch)")
    parser.add_argument("--query")
    parser.add_argument("--budget", type=int, default=1200)
    args = parser.parse_args(argv)
    options = {"worktree_path": args.worktree_path, "ticket": args.ticket}
    try:
        if args.action == "ensure":
            result = build_graph(args.project, baseline_branch=args.baseline_branch, **options)
        elif args.action == "status":
            result = graph_status(args.project, baseline_branch=args.baseline_branch, **options)
        elif args.action == "query":
            if not args.query:
                parser.error("--query is required for query action")
            print(query_graph(args.project, args.query, budget=args.budget, **options))
            return 0
        else:
            result = cleanup_graph(args.project, **options)
    except (OSError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("verified", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
