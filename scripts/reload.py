"""Keep checkouts current and remove only work that is proven merged.

    python scripts/reload.py [--dry-run] [--keep BRANCH ...] [PATH ...]

For each repository (the one containing the current directory when no PATH is given): fetch --prune origin, remove
the linked worktrees and delete the local branches whose work is proven merged, then fast-forward the default branch.
Proven merged means one of: the branch tip is an ancestor of origin/<default>; every commit's patch is already there
(git cherry prints no '+'); or, for a GitHub origin with gh available, a merged pull request whose head commit is the
tip. Stashes, untracked files, dirty, locked or in-use worktrees and remote branches are never touched and nothing is
pushed. --dry-run prints what would happen and changes nothing but the fetch. Exit 1 only when a git command it needed
failed. Standard library only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

GITHUB = re.compile(r"github\.com[:/]")


def git(cwd, *args):
    """Run git in cwd; returns (ok, stdout lines, combined text for messages)."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", stdin=subprocess.DEVNULL, env=env)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    return done.returncode == 0, lines, " ".join((done.stdout + done.stderr).split())


def first(cwd, *args):
    ok, lines, _ = git(cwd, *args)
    return lines[0] if ok and lines else None


def merged_pull_request_heads(root, branch):
    """Head commits of merged GitHub pull requests from this branch; None when gh cannot answer."""
    url = first(root, "remote", "get-url", "origin")
    if not url or not GITHUB.search(url) or not shutil.which("gh"):
        return None
    try:
        done = subprocess.run(["gh", "pr", "list", "--state", "merged", "--head", branch, "--json", "headRefOid"],
                              cwd=str(root), capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, timeout=60)
        if done.returncode != 0:
            return None
        return {entry.get("headRefOid") for entry in json.loads(done.stdout or "[]")}
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
        return None


def proven_merged(root, branch, base, pr_heads=merged_pull_request_heads):
    """The proof that the branch's work is in base, or None. Never guesses: any doubt means not proven."""
    tip = first(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}")
    if not tip:
        return None
    if git(root, "merge-base", "--is-ancestor", tip, base)[0]:
        # A branch whose reflog shows only its creation is new work with no commits yet, not a merged branch.
        ok, entries, _ = git(root, "reflog", "show", "--format=%H", f"refs/heads/{branch}")
        return "tip is an ancestor of the default branch" if ok and len(entries) > 1 else None
    ok, cherry, _ = git(root, "cherry", base, tip)
    if ok and cherry and not any(line.startswith("+") for line in cherry):
        return "every patch is already in the default branch (git cherry)"
    heads = pr_heads(root, branch)
    if heads and tip in heads:
        return "its merged pull request has this tip as head commit (gh)"
    return None


def default_branch(root):
    ref = first(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if ref and ref.startswith("origin/"):
        return ref[len("origin/"):]
    for name in ("main", "master"):
        if git(root, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{name}")[0]:
            return name
    return None


def list_worktrees(root):
    """Porcelain worktree entries as dicts (path, branch, locked); the first one is the main checkout."""
    entries, current = [], None
    for line in git(root, "worktree", "list", "--porcelain")[1] + [""]:
        if line.startswith("worktree "):
            current = {"path": line[len("worktree "):], "branch": None, "locked": False}
            entries.append(current)
        elif current is not None and line.startswith("branch refs/heads/"):
            current["branch"] = line[len("branch refs/heads/"):]
        elif current is not None and line.startswith("locked"):
            current["locked"] = True
    return entries


def inside(path, folder):
    path, folder = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(folder))
    return path == folder or path.startswith(folder.rstrip(os.sep) + os.sep)


def reload_repository(target, keep, dry_run, say):
    """Reload one repository; returns True when every git command it needed succeeded."""
    ok_all = True
    ok, lines, text = git(target, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not ok or not lines:
        say(f"{target}: not a git repository, skipped")
        return False
    root = Path(lines[0]).resolve().parent
    say(f"== {root}")
    ok, _, text = git(root, "fetch", "--prune", "--quiet", "origin")
    if not ok:
        say(f"fetch failed: {text}")
        return False
    default = default_branch(root)
    if not default:
        say("no main or master on origin: skipped")
        return True
    base = f"refs/remotes/origin/{default}"
    cwd = os.getcwd()

    worktrees = list_worktrees(root)
    main = worktrees[0] if worktrees else {"path": str(root), "branch": None, "locked": False}
    main_branch = main["branch"]
    removed = set()
    for wt in worktrees[1:]:
        name = wt["branch"] or "(detached)"
        label = f"worktree {wt['path']} [{name}]"
        if not wt["branch"]:
            say(f"kept {label}: detached HEAD")
        elif wt["branch"] in keep:
            say(f"kept {label}: listed in --keep")
        elif wt["locked"]:
            say(f"kept {label}: locked")
        elif not os.path.isdir(wt["path"]):
            say(f"kept {label}: folder is missing")
        elif inside(cwd, wt["path"]):
            say(f"kept {label}: the current directory is inside it")
        else:
            proof = proven_merged(root, wt["branch"], base)
            ok, status, text = git(wt["path"], "status", "--porcelain")
            if not proof:
                say(f"kept {label}: not proven merged")
            elif not ok or status:
                say(f"kept {label}: merged, but it has uncommitted or untracked files")
            elif dry_run:
                say(f"would remove {label} ({proof})")
                removed.add(wt["branch"])
            else:
                ok, _, text = git(root, "worktree", "remove", wt["path"])
                if ok:
                    say(f"removed {label} ({proof})")
                    removed.add(wt["branch"])
                else:
                    say(f"could not remove {label}: {text}")
                    ok_all = False

    # The main checkout leaves a merged branch for the default branch, so the branch can then be deleted.
    if main_branch and main_branch != default and main_branch not in keep:
        proof = proven_merged(root, main_branch, base)
        if proof and git(root, "status", "--porcelain")[1]:
            say(f"main checkout stays on {main_branch}: merged, but it has uncommitted or untracked files")
        elif proof:
            if dry_run:
                say(f"would switch the main checkout from {main_branch} to {default} ({proof})")
                main_branch = default
            else:
                ok, _, text = git(root, "switch", "--quiet", default)
                if ok:
                    say(f"switched the main checkout from {main_branch} to {default} ({proof})")
                    main_branch = default
                else:
                    say(f"could not switch the main checkout to {default}: {text}")
                    ok_all = False
        else:
            say(f"main checkout stays on {main_branch}: not proven merged")

    checked_out = {wt["branch"] for wt in worktrees[1:] if wt["branch"] and wt["branch"] not in removed}
    if main_branch:
        checked_out.add(main_branch)
    for branch in git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads")[1]:
        if branch == default or branch in keep or branch in checked_out:
            continue
        proof = proven_merged(root, branch, base)
        if not proof:
            say(f"kept branch {branch}: not proven merged")
        elif dry_run:
            say(f"would delete branch {branch} ({proof})")
        else:
            ok, _, text = git(root, "branch", "-d", branch)
            if not ok:  # -d refuses squash and rebase merges; the proof above is what allows -D
                ok, _, text = git(root, "branch", "-D", branch)
            if ok:
                say(f"deleted branch {branch} ({proof})")
            else:
                say(f"could not delete branch {branch}: {text}")
                ok_all = False

    local = first(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{default}")
    remote = first(root, "rev-parse", "--verify", "--quiet", base)
    if main_branch == default:
        if local == remote:
            say(f"{default} is up to date")
        elif git(root, "status", "--porcelain")[1]:
            say(f"{default} not fast-forwarded: the main checkout has uncommitted or untracked files")
        elif dry_run:
            say(f"would fast-forward {default} to origin/{default}")
        else:
            ok, _, text = git(root, "merge", "--ff-only", "--quiet", base)
            if ok:
                say(f"fast-forwarded {default} to origin/{default}")
            else:
                say(f"could not fast-forward {default}: {text}")
                ok_all = False
    elif local and remote and default not in checked_out:
        if local == remote:
            say(f"{default} is up to date")
        elif not git(root, "merge-base", "--is-ancestor", local, remote)[0]:
            say(f"{default} not moved: the local branch is not an ancestor of origin/{default}")
        elif dry_run:
            say(f"would move {default} to origin/{default}")
        else:
            ok, _, text = git(root, "update-ref", "-m", "reload: fast-forward", f"refs/heads/{default}", remote, local)
            if ok:
                say(f"moved {default} to origin/{default}")
            else:
                say(f"could not move {default}: {text}")
                ok_all = False
    elif local and remote and local != remote:
        say(f"{default} not moved: it is checked out in a worktree")
    return ok_all


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("paths", nargs="*", metavar="PATH", help="repositories (a worktree counts); default: the current one")
    parser.add_argument("--dry-run", action="store_true", help="print what would happen and change nothing")
    parser.add_argument("--keep", action="append", default=[], metavar="BRANCH", help="branch never removed; repeatable")
    args = parser.parse_args(argv)
    keep, failed, seen = set(args.keep), False, set()
    for target in args.paths or ["."]:
        ok, lines, _ = git(target, "rev-parse", "--path-format=absolute", "--git-common-dir")
        key = os.path.normcase(os.path.realpath(lines[0])) if ok and lines else None
        if key in seen:
            continue
        seen.add(key)
        if not reload_repository(target, keep, args.dry_run, print):
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
