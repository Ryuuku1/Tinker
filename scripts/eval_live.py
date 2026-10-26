"""Live behavioral evals for the Claude Code host: run the cases in evals/live through `claude plugin eval`, then gate.

run   Snapshots this checkout once (tracked and untracked files, never ignored ones such as .tinker/) into its own
      <temp>/tinker_eval_<runId>/tinker, renders the Claude plugin bundle from that copy into .../home/.tinker/plugin
      (no hooks), copies evals/live there as the bundle's eval suite and runs `claude plugin eval` on it. Each case
      scaffold builds its workspace as a Tinker root from the snapshot, so an edit made during a run never reaches a
      case and runs can go in parallel. The run folder stays behind as the record of what was measured; the JSON
      result is copied to evals/live/results/<runId>.json. Defaults: --model opus, -j 4, one run per case unless the
      case says `runs:`, --ablation none. --adaptive then runs each case that fell short, in this run or in the
      accepted baseline, twice more and merges those runs into the result, so one unlucky run on either side does
      not decide a gate. A call that starts more than 20 agent runs first reads the account's five-hour usage (one
      Haiku turn) and refuses when the runs likely won't fit; --force skips the check.
gate  Compares a result with evals/live/accepted.json per set (regression, heldout), averaging per case: exit 0 pass,
      1 fail, 2 invalid. --accept records the result as the new baseline, with each case's means.

Eval runs cannot sandbox shell tools on Windows, so cases get Read/Grep/Glob, Write/Edit, Skill and Agent only.
Scaffolds are bash: they need bash (Git Bash on Windows) and git on PATH.
"""
import argparse
from datetime import datetime, timezone
import fnmatch
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
LIVE = Path("evals") / "live"
BUNDLE_EVALS = "evals"  # the bundle's eval dir (a single segment, claude plugin eval's default)
SETS = ("regression", "heldout")
PLACEHOLDER = "  append_system_prompt: TINKER_AGENTS_MD"
ROOT_NOTE = ("This session's working directory is the Tinker root: the charter below is its AGENTS.md, and "
             "the charter's relative links and .tinker/ paths resolve against it.")
USAGE_CHECK_ABOVE = 20
RERUNS = 2  # --adaptive: more runs for a case that fell short, so a single miss weighs a third of its score
# Bundle files only another host reads, and the hooks (an eval measures the charter, not this machine's runtime).
NOT_IN_BUNDLE = ("hooks/", "plugin.json", ".agents/plugins/")
RENDER = r"""
import json, sys
from pathlib import Path
tree, home = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(tree / "scripts"))
import install_apps
base, files = install_apps.bundle_files(tree, home, sys.executable, "0.0.0-eval")
sys.stdout.write(json.dumps({"base": str(base), "files": files}))
"""


class EvalError(Exception):
    pass


# ---------------------------------------------------------------- case.yaml (the small subset the cases use)

def _scalar(value):
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        return [_scalar(v) for v in value[1:-1].split(",") if v.strip()]
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        return value[1:-1]
    return int(value) if re.fullmatch(r"\d+", value) else value


def read_case(path):
    """Top-level scalars and inline lists, the execution/context keys, and each grader's own keys."""
    case, section = {"graders": []}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        match = re.match(r"\s*(-\s+)?([A-Za-z_]+):(?:\s+(.*))?$", line)
        if indent == 0:
            if match:
                section = match.group(2)
                if match.group(3):
                    case[section] = _scalar(match.group(3))
        elif not match:
            continue
        elif section == "graders":
            if match.group(1) and indent == 2:
                case["graders"].append({match.group(2): _scalar(match.group(3) or "")})
            elif indent == 4 and case["graders"]:
                case["graders"][-1].setdefault(match.group(2), _scalar(match.group(3) or ""))
        elif section in ("execution", "context") and indent == 2 and not match.group(1):
            case.setdefault(section, {})[match.group(2)] = _scalar(match.group(3) or "")
    return case


def case_dirs(root):
    live = Path(root) / LIVE
    return [p.parent for p in sorted(live.glob("*/case.yaml")) if not p.parent.name.startswith("_")]


def case_set(case):
    return "heldout" if "heldout" in (case.get("tags") or []) else "regression"


def count_runs(root, case_glob=None, tags=(), runs=None, ablation="none"):
    """The agent runs a call starts: matching cases x runs per case x arms (with-without doubles it)."""
    arms = 2 if ablation == "with-without" else 1
    total = 0
    for folder in case_dirs(root):
        if case_glob and not fnmatch.fnmatchcase(folder.name, case_glob):
            continue
        case = read_case(folder / "case.yaml")
        if tags and not set(tags) & set(case.get("tags") or []):
            continue
        total += arms * (runs or case.get("runs") or 1)
    return total


# ---------------------------------------------------------------- run

def five_hour_usage(claude):
    """(percent used, reset time) from one Haiku turn's rate_limit_event, or None when it cannot be read."""
    command = [claude, "-p", "ok", "--model", "haiku", "--output-format", "stream-json", "--verbose", "--max-turns", "1"]
    try:  # outside any checkout, so no project settings or MCP servers join the probe
        proc = subprocess.run(command, cwd=tempfile.gettempdir(), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)
    except (OSError, subprocess.SubprocessError):
        return None
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict) or event.get("type") != "rate_limit_event":
            continue
        window = ((event.get("rate_limit_info") or {}).get("unifiedWindows") or {}).get("five_hour") or {}
        try:
            return 100 * float(window["utilization"]), datetime.fromtimestamp(int(window["resetsAt"]))
        except (KeyError, TypeError, ValueError, OverflowError, OSError):
            continue
    return None


def usage_refusal(claude, total, percent):
    """None when `total` more agent runs fit the five-hour window, else why they do not."""
    usage = five_hour_usage(claude)
    if usage is None:
        return ("Could not read the five-hour usage (no rate_limit_event from `claude -p`). "
                "Check that claude works, or pass --force to skip the check.")
    used, resets = usage
    needed = total * percent
    if used + needed > 100:
        return (f"Not starting {total} eval runs: at about {percent}% of the five-hour window each they need "
                f"~{round(needed)}%, and {round(used)}% is already used (the window resets at {resets:%H:%M}). "
                "Wait for the reset or narrow the run (--case, --tag, --runs, --ablation none); --force skips this "
                "check.")
    print(f"Five-hour window: {round(used)}% used, this run needs ~{round(needed)}% ({total} runs).")
    return None


def with_runs(case):
    return (case.get("arms") or {}).get("with") or []


def rerun_short(args, claude, base, bundle, env, result, short_before=()):
    """--adaptive: run each case that fell short here or in the baseline (short_before) RERUNS more times, unless it
    already has more than RERUNS runs, and merge those runs into the result."""
    def fell_short(case):  # an errored run keeps the result invalid whatever follows, so only complete cases re-run
        runs = with_runs(case)
        return bool(runs) and all(r.get("turns") and not r.get("error") for r in runs) and len(runs) <= RERUNS and (
            sum(float(r.get("score") or 0) for r in runs) < len(runs) or case.get("name") in short_before)
    doc = json.loads(result.read_text(encoding="utf-8-sig"))
    short = [case for case in doc.get("cases") or [] if fell_short(case)]
    doc["adaptive"], doc["mergedFrom"] = True, []
    if short:
        print(f"Adaptive: {len(short)} case(s) fell short, here or in the baseline; each runs {RERUNS} more times: "
              f"{', '.join(c['name'] for c in short)}", flush=True)
    refusal = (None if args.force or RERUNS * len(short) <= USAGE_CHECK_ABOVE
               else usage_refusal(claude, RERUNS * len(short), args.percent_per_run))
    if refusal:
        print(f"{refusal} The first runs stand.", file=sys.stderr)
        short = []
    for case in short:
        again_path = result.with_name(f"rerun-{case['name']}.json")
        subprocess.run(base + ["--ablation", "none", "--json", str(again_path), "--case", case["name"],
                               "--runs", str(RERUNS)], cwd=bundle, env=env)
        try:
            again = json.loads(again_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            print(f"Adaptive: the re-run of {case['name']} wrote no result; its first runs stand.", file=sys.stderr)
            continue
        for other in again.get("cases") or []:
            if other.get("name") == case["name"]:
                case.setdefault("arms", {}).setdefault("with", []).extend(with_runs(other))
        doc["costUsd"] = round(float(doc.get("costUsd") or 0) + float(again.get("costUsd") or 0), 4)
        doc["mergedFrom"].append(again_path.name)
    result.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")


def snapshot(root, dest):
    """Copy the checkout's tracked and untracked-but-not-ignored files into dest."""
    listed = subprocess.run(["git", "-C", str(root), "-c", "core.quotepath=off", "ls-files", "-z", "--cached",
                             "--others", "--exclude-standard"], capture_output=True)
    if listed.returncode != 0:
        raise EvalError(f"Listing the working tree of {root} failed (eval_live.py runs from a git checkout).")
    count = 0
    for rel in listed.stdout.decode("utf-8").split("\0"):
        source = Path(root) / rel
        if not rel or not source.is_file():  # deleted from the working tree, or a submodule
            continue
        target = Path(dest) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        count += 1
    return count


def fill_case(text, charter):
    block = "\n".join(f"    {line}" if line else "" for line in [ROOT_NOTE, "", *charter.splitlines()])
    text = text.replace(PLACEHOLDER, "  append_system_prompt: |\n" + block)
    if not re.search(r"(?m)^runs:", text):  # one run per case unless the case asks for more
        text = re.sub(r"(?m)^(name:.*)$", r"\1\nruns: 1", text, count=1)
    return text


def render_bundle(tree, home):
    """The Claude plugin bundle the installer would render from tree, minus hooks, plus the live eval suite."""
    proc = subprocess.run([sys.executable, "-I", "-c", RENDER, str(tree), str(home)], capture_output=True,
                          text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise EvalError(f"Rendering the bundle failed:\n{proc.stderr.strip()}")
    rendered = json.loads(proc.stdout)
    bundle = Path(rendered["base"])
    for rel, content in rendered["files"].items():
        if rel.startswith(NOT_IN_BUNDLE):
            continue
        if rel == ".claude-plugin/plugin.json":
            manifest = json.loads(content)
            manifest.pop("hooks", None)
            content = json.dumps(manifest, indent=2) + "\n"
        path = bundle / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    charter = (tree / "AGENTS.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    source, evals = tree / LIVE, bundle / BUNDLE_EVALS
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source)
        if not path.is_file() or rel.parts[0] == "results" or rel.as_posix() == "accepted.json":
            continue
        target = evals / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.name == "case.yaml":
            target.write_text(fill_case(path.read_text(encoding="utf-8"), charter), encoding="utf-8", newline="\n")
        else:
            target.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    # The scaffolds' Tinker root: the snapshot, never the live checkout.
    (evals / "_shared" / "root.txt").write_text(tree.as_posix() + "\n", encoding="utf-8", newline="\n")
    return bundle


def scaffold_env():
    """PATH with Git Bash first on Windows: from Windows, `bash` is often WSL's, which cannot run the scaffolds."""
    env = os.environ.copy()
    git = shutil.which("git")
    if os.name == "nt" and git:
        git_bin = Path(git).resolve().parent.parent / "bin"
        if (git_bin / "bash.exe").is_file():
            env["PATH"] = str(git_bin) + os.pathsep + env.get("PATH", "")
    missing = [tool for tool in ("bash", "git") if not shutil.which(tool, path=env.get("PATH"))]
    if missing:
        raise EvalError(f"The case scaffolds need {' and '.join(missing)} on PATH.")
    return env


def accepted_file(args, root):
    return Path(args.accepted) if args.accepted else Path(root) / LIVE / "accepted.json"


def short_in_baseline(args, root):
    """The cases the accepted baseline recorded below 1.0, when it was measured the way this run measures."""
    path = accepted_file(args, root)
    try:
        accepted = json.loads(path.read_text(encoding="utf-8-sig")) if path.is_file() else {}
    except (OSError, ValueError):
        return set()
    if str(accepted.get("model")) != str(args.model) or not accepted.get("adaptive"):
        return set()
    return {name for name, means in (accepted.get("cases") or {}).items() if float(means.get("score", 1)) < 1}


def run(args, root, temp=None):
    claude = shutil.which("claude")
    if not claude:
        raise EvalError("claude is not on PATH.")
    total = count_runs(root, args.case, args.tag or (), args.runs, args.ablation)
    if total == 0:
        raise EvalError("No case matches --case/--tag.")
    if not args.force and total > USAGE_CHECK_ABOVE:
        refusal = usage_refusal(claude, total, args.percent_per_run)
        if refusal:
            raise EvalError(refusal)
    env = scaffold_env()

    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    run_dir = Path(temp or tempfile.gettempdir()) / f"tinker_eval_{run_id}"
    tree = run_dir / "tinker"
    snapshot(root, tree)
    bundle = render_bundle(tree, run_dir / "home")
    result = run_dir / "result.json"
    base = [claude, "plugin", "eval", ".", "--eval-dir", BUNDLE_EVALS, "--scaffold", "--allow-tools", "Write", "Edit",
            "--trust-plugin", "--no-publish", "--model", args.model, "--concurrency", str(args.jobs)]
    command = base + ["--json", str(result), "--ablation", args.ablation]
    if args.case:
        command += ["--case", args.case]
    if args.tag:
        command += ["--tag", *args.tag]
    if args.runs:
        command += ["--runs", str(args.runs)]
    print(f"Run folder: {run_dir} ({total} agent runs)", flush=True)
    code = subprocess.run(command, cwd=bundle, env=env).returncode
    if not result.is_file():
        print(f"No result was written ({result}); claude exited with {code}.", file=sys.stderr)
        return code or 1
    if args.adaptive:
        rerun_short(args, claude, base, bundle, env, result, short_in_baseline(args, root))
    kept = Path(root) / LIVE / "results" / f"{run_id}.json"
    kept.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result, kept)
    print(f"Result: {kept}")
    return code


# ---------------------------------------------------------------- gate

def mean(values):
    return sum(values) / len(values)


def case_means(result, root):
    """Each case's set, mean score, mean cost per run and run count on the plugin arm, and the cases with errored or
    unstarted runs."""
    means, errored = {}, []
    for case in result.get("cases") or []:
        name = case.get("name")
        yaml = Path(root) / LIVE / str(name) / "case.yaml"
        if not yaml.is_file():
            raise EvalError(f"Case '{name}' in the result has no {LIVE.as_posix()}/{name}/case.yaml.")
        runs = with_runs(case)
        if not runs or any(r.get("error") or not r.get("turns") for r in runs):
            errored.append(name)
        if runs:
            means[name] = {"set": case_set(read_case(yaml)), "score": mean([float(r.get("score") or 0) for r in runs]),
                           "costPerRunUsd": mean([float(r.get("costUsd") or 0) for r in runs]), "runs": len(runs)}
    return means, list(dict.fromkeys(errored))


def summarize(result, root):
    """Per-set score and cost per run of the plugin arm, averaged per case so a case that --adaptive re-ran weighs
    what a case run once does, the set's run count, and the cases with errored runs."""
    means, errored = case_means(result, root)
    if not means and not errored:
        raise EvalError("The result holds no case runs.")
    summary = {}
    for name in SETS:
        items = [m for m in means.values() if m["set"] == name]
        if items:
            summary[name] = {"score": round(mean([m["score"] for m in items]), 3),
                             "costPerRunUsd": round(mean([m["costPerRunUsd"] for m in items]), 4),
                             "runs": sum(m["runs"] for m in items)}
    return summary, errored


def uneven_cases(means, accepted):
    """Cases that fell short on one side and ran a different number of times on each, so their means compare runs
    of unequal weight; a baseline case perfect in its one adaptive run is the usual one."""
    lines = []
    for name, now in sorted(means.items()):
        before = ((accepted or {}).get("cases") or {}).get(name)
        if before and (now["score"] < 1 or before["score"] < 1) and now["runs"] != before["runs"]:
            lines.append(f"{name} ({round(now['score'], 3)} over {now['runs']} here, {before['score']} over "
                         f"{before['runs']} in the baseline)")
    return lines


def gate(args, root):
    result_path = Path(args.result)
    accepted_path = accepted_file(args, root)
    try:
        result = json.loads(result_path.read_text(encoding="utf-8-sig"))
        summary, errored = summarize(result, root)
        means, _ = case_means(result, root)
    except (OSError, ValueError, EvalError) as error:
        print(f"INVALID: {error}")
        return 2
    accepted = json.loads(accepted_path.read_text(encoding="utf-8-sig")) if accepted_path.is_file() else None
    model, adaptive = (result.get("suite") or {}).get("modelOverride"), bool(result.get("adaptive"))
    new_model = bool(accepted) and str(accepted.get("model")) != str(model)
    new_mode = bool(accepted) and bool(accepted.get("adaptive")) != adaptive  # re-runs lift a flaky case's score
    passed = not errored and not new_model and not new_mode and bool(summary)
    print("| Set | Runs | Score | Accepted | Cost/run (USD) | Accepted | Verdict |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for name, now in summary.items():
        base = ((accepted or {}).get("sets") or {}).get(name)
        if errored:
            verdict = "INVALID"
        elif new_model:
            verdict = "new model"
        elif new_mode:
            verdict = "new mode"
        elif not base:
            verdict = "no baseline"
        elif now["score"] < base["score"] - args.score_tolerance:
            verdict = "FAIL: score"
        elif now["costPerRunUsd"] > base["costPerRunUsd"] * (1 + args.cost_tolerance):
            verdict = "FAIL: cost"
        else:
            verdict = "pass"
        passed = passed and verdict == "pass"
        print(f"| {name} | {now['runs']} | {now['score']} | {base['score'] if base else '-'} | {now['costPerRunUsd']} "
              f"| {base['costPerRunUsd'] if base else '-'} | {verdict} |")
    if errored:
        print(f"INVALID: run(s) errored or never started ({', '.join(map(str, errored))}); re-run before gating.")
        if args.accept:
            print("Refusing to accept a result with errored runs.")
        return 2
    if new_model:
        print(f"Model changed ({accepted.get('model')} -> {model}): this result cannot pass the gate; "
              "--accept makes it the new baseline.")
    if new_mode:
        print(f"Adaptive mode changed ({'on' if accepted.get('adaptive') else 'off'} -> {'on' if adaptive else 'off'}): "
              "this result cannot pass the gate; --accept makes it the new baseline.")
    if not accepted:
        print(f"No baseline at {accepted_path}: review the result, then --accept records the first one.")
    uneven = [] if new_model or new_mode else uneven_cases(means, accepted)
    if uneven:
        print("Uneven runs: " + "; ".join(uneven) + ". A mean over fewer runs is the weaker estimate; measure that "
              "side to the same count before trusting a verdict these cases decide.")
    if args.accept:
        kept = not (new_model or new_mode)
        sets = dict((accepted or {}).get("sets") or {}) if kept else {}
        sets.update(summary)
        cases = dict((accepted or {}).get("cases") or {}) if kept else {}
        cases.update({name: {"set": m["set"], "score": round(m["score"], 3),
                             "costPerRunUsd": round(m["costPerRunUsd"], 4), "runs": m["runs"]}
                      for name, m in means.items()})
        commit = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
        record = {"acceptedAt": result.get("startedAt"), "result": result_path.name,
                  "commit": commit.stdout.strip() if commit.returncode == 0 else "", "model": model,
                  "adaptive": adaptive, "sets": sets, "cases": dict(sorted(cases.items()))}
        accepted_path.parent.mkdir(parents=True, exist_ok=True)
        accepted_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
        print(f"Accepted as the new baseline: {accepted_path}")
        return 0
    return 0 if passed else 1


# ---------------------------------------------------------------- command line

def parser():
    top = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = top.add_subparsers(dest="command", required=True)
    r = sub.add_parser("run", help="snapshot this checkout and run the live cases through claude plugin eval")
    r.add_argument("--case", help="case folder name glob")
    r.add_argument("--tag", nargs="+", action="extend", help="only cases with one of these tags")
    r.add_argument("--runs", type=int, help="runs per case (default: the case's runs:, else 1)")
    r.add_argument("--model", default="opus")
    r.add_argument("-j", "--jobs", type=int, default=4, help="agent runs at once (1-8)")
    r.add_argument("--ablation", choices=("none", "with-without"), default="none")
    r.add_argument("--adaptive", action="store_true",
                   help=f"run each case that falls short here or in the baseline {RERUNS} more times and merge those "
                        "runs into the result")
    r.add_argument("--accepted", help=f"baseline whose short cases --adaptive re-runs (default {LIVE.as_posix()}/"
                                      "accepted.json)")
    r.add_argument("--force", action="store_true", help="skip the five-hour usage check")
    r.add_argument("--percent-per-run", type=float, default=0.4,
                   help="share of the five-hour window one agent run is assumed to use (default 0.4)")
    g = sub.add_parser("gate", help="compare a result with the accepted baseline")
    g.add_argument("--result", required=True)
    g.add_argument("--accept", action="store_true", help="record this result as the new baseline")
    g.add_argument("--accepted", help=f"baseline file (default {LIVE.as_posix()}/accepted.json)")
    g.add_argument("--score-tolerance", type=float, default=0.02)
    g.add_argument("--cost-tolerance", type=float, default=0.10)
    return top


def main(argv=None, root=ROOT, temp=None):
    args = parser().parse_args(argv)
    try:
        return run(args, root, temp) if args.command == "run" else gate(args, root)
    except EvalError as error:
        print(error, file=sys.stderr)
        return 2 if args.command == "gate" else 1


if __name__ == "__main__":
    sys.exit(main())
