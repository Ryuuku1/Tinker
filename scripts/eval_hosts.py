"""Live evals on Codex (`codex exec`) and Antigravity (`agy`): the runner behind `eval_live.py run --host codex|agy`.

Each case runs the same setup.sh the Claude path runs (from the same rendered suite, so the workspace is the snapshot's
Tinker root), then the host headless in that workspace, one case at a time. The run folder keeps the prompt, the raw
event stream, the answer, the files the run created or changed and the workspace, and grading reads only those, so a
run can be graded again offline. Grading is local, after the host has finished:
  regex        on the answer (last_message), the trace (answers, commands and tool calls) or a workspace file;
  file_exists  a glob in the workspace;
  tool_used    the host's own tool events mapped to the case's tool names (TOOL_MAP), plus a before/after file diff
               (a new file is a Write, a changed or deleted one an Edit); a tool with no observable event on the host is
               n/a, never a count of 0, and leaves the score's denominator;
  llm          the pinned judge (--judge-model) through `claude -p`, three votes, majority; this script's prompt, so it
               is the same model as `claude plugin eval`'s judge, not the same judge.
A run that did not finish (no completion event, a failure event, an empty answer, a timeout) or whose grader could not
decide gets an error, which the gate reads as INVALID. Neither host reports cost: costUsd is 0, tokens sit beside it.
Neither host runs isolated: the user's own setup it loads (USER_SETUP) is recorded with a content hash as userSetup,
and the gate refuses to pass a result whose userSetup differs from its baseline's.
"""
from datetime import datetime, timezone
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import uuid

AGY_MODEL = "gemini-4-hydrogen-xhigh"  # "Gemini 4 Hydrogen (XHigh)" in `agy models`
AGY_EFFORT = "xhigh"
CODEX_MODEL = "provider-default"  # what a result records when no --model was given: codex gets no -m
TIMEOUT = 900  # seconds per run; no host here has Claude's max_turns
VOTES = 3
SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".ruff_cache", "node_modules"}
# The case's tool name -> how the host shows it: "diff" reads the workspace before and after the run; a tuple names the
# host's own tool events. A tool missing here has no event to observe on that host, so its grader is n/a.
TOOL_MAP = {  # agy's names as its step events carry them (`read_file`, though `init` lists `view_file`)
    "codex": {"Write": "diff", "Edit": "diff"},  # it reads, searches and edits through its shell: no per-tool events
    "agy": {"Write": "diff", "Edit": "diff", "Read": ("read_file", "view_file"), "Agent": ("invoke_subagent",)},
}
# The user's own setup each CLI loads beside the workspace: neither has a switch to drop it short of moving its home,
# which holds the sign-in. agy loads its plugins (an installed Tinker too, whose hook refuses commands), skills and
# GEMINI.md; codex its home's AGENTS.md and skills, and ~/.agents/skills. A run measures the snapshot with these.
USER_SETUP = {
    "codex": ("{codex}/AGENTS.md", "{codex}/AGENTS.override.md", "{codex}/skills", "{home}/.agents/skills"),
    "agy": ("{home}/.gemini/GEMINI.md", "{home}/.gemini/config/plugins", "{home}/.gemini/config/skills",
            "{home}/.gemini/antigravity-cli/skills", "{home}/.agents/skills"),
}
JUDGE_SYSTEM = ("You grade one reply of an AI agent for an eval. Decide whether the reply meets the criterion. "
                "Answer with exactly one word: PASS if it meets the criterion, FAIL if it does not.")
USAGE_LIMIT = re.compile(r"usage limit|rate limit|quota", re.I)


# ---------------------------------------------------------------- case.yaml

def case_prompt(path):
    """The case's `prompt: |` block under execution, dedented."""
    lines, block = Path(path).read_text(encoding="utf-8").splitlines(), None
    for line in lines:
        if block is None:
            if re.fullmatch(r"  prompt: \|", line):
                block = []
            continue
        if line.strip() and len(line) - len(line.lstrip(" ")) <= 2:
            break
        block.append(line[4:])
    if not block:
        raise ValueError(f"{path} has no `prompt: |` block")
    return "\n".join(block).strip() + "\n"


def inline_map(value):
    """`{ source: file, path: a/b }` as a dict; any other value unchanged."""
    if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
        return {k.strip(): v.strip() for k, v in (part.split(":", 1) for part in value[1:-1].split(","))}
    return value


# ---------------------------------------------------------------- host output

def events_of(path):
    events = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    return events


def parse_codex(events, answer):
    """`codex exec --json`: answers, trace, tool events, tokens, turn count and the error, if the run did not finish."""
    messages, trace, tools, usage, completed, failed, turns = [], [], [], {}, False, None, 0
    for event in events:
        kind = event.get("type")
        if kind == "item.completed":
            item = event.get("item") or {}
            turns += 1
            if item.get("type") == "agent_message":
                messages.append(str(item.get("text") or ""))
                trace.append(messages[-1])
            elif item.get("type") == "command_execution":
                trace.append(f"$ {item.get('command')}\n{item.get('aggregated_output') or ''}")
                tools.append(("shell", {"command": item.get("command")}))
            elif item.get("type") in ("mcp_tool_call", "collab_tool_call", "web_search"):
                tools.append((str(item.get("tool") or item.get("type")), item))
                trace.append(json.dumps(item, separators=(",", ":")))
        elif kind == "turn.completed":
            completed, usage = True, event.get("usage") or {}
        elif kind == "turn.failed":
            failed = str((event.get("error") or {}).get("message") or "turn.failed")
    final = answer or ""  # the -o file: an empty one fails the run even when messages streamed
    error = failed or (None if completed else "no turn.completed") or (None if final.strip() else "empty -o answer")
    return {"final": final, "trace": "\n\n".join(trace), "tools": tools, "usage": usage, "turns": turns,
            "error": error}


def parse_agy(events, answer=""):
    """`agy -p --output-format stream-json`: {"event": "init"|"step_update"|"result", <that name>: {...}}. A step
    streams as ACTIVE updates (an answer's text_delta pieces) and ends DONE or ERROR, so each step_index counts once;
    the last answer step is the last message, as on Claude, and result.response joins every answer step."""
    init, result, steps = {}, None, {}
    for event in events:
        kind = event.get("event")
        if kind == "init":
            init = event.get("init") or {}
        elif kind == "result":
            result = event.get("result") or {}
        elif kind == "step_update":
            step = event.get("step_update") or {}
            seen = steps.setdefault(step.get("step_index"), {"text": ""})
            seen["text"] += str(step.get("text_delta") or "")
            seen.update({k: v for k, v in step.items() if k != "text_delta"})
    trace, tools, texts, turns = [], [], [], 0
    for step in steps.values():
        if step.get("step_type") == "agent_response":
            turns += step.get("state") == "DONE"
            if step["text"].strip():
                texts.append(step["text"])
                trace.append(step["text"])
        elif step.get("step_type") in ("tool", "subagent"):
            info = step.get("tool_info") or {}
            data = info.get("parameters") or step.get("subagent_info") or {}
            tools.append((str(step.get("tool_name") or info.get("name") or ""), data))
            trace.append(f"{tools[-1][0]} {json.dumps(data, separators=(',', ':'), ensure_ascii=False)}\n"
                         f"{info.get('output') or info.get('error') or ''}")
    final = answer or (texts[-1] if texts else "")
    status = str((result or {}).get("status") or "")
    denied = [str(d.get("action") or d) for d in (result or {}).get("denied_actions") or [] if d]
    if result is None:
        error = "no result event"
    elif status.upper() != "SUCCESS":
        error = f"result status {status or 'missing'}: {str(result.get('error') or '')[:300]}".rstrip(": ")
    elif denied:  # a permission request print mode cannot answer ends the turn, and the status still says SUCCESS
        error = f"stopped on a permission request: {', '.join(denied)}"
    else:
        error = None if final.strip() else "empty answer"
    return {"final": final, "trace": "\n\n".join(trace), "tools": tools, "usage": (result or {}).get("usage") or {},
            "turns": turns, "error": error,
            "init": {k: init.get(k) for k in ("model", "permission_mode", "cwd") if k in init}}


PARSERS = {"codex": parse_codex, "agy": parse_agy}


# ---------------------------------------------------------------- the workspace diff

def files_of(work):
    """{posix path relative to work: sha256} for every file outside VCS and cache folders."""
    found = {}
    for base, dirs, names in os.walk(work):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in names:
            path = Path(base) / name
            found[path.relative_to(work).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return found


def changes(work, before):
    """The Write (new file) and Edit (changed or deleted file) events a before/after diff shows, inputs as Claude's
    tools would carry them: file_path absolute, plus the file's whole new content."""
    after, events = files_of(work), []
    for rel in sorted(set(before) | set(after)):
        if before.get(rel) == after.get(rel):
            continue
        path = (Path(work) / rel).as_posix()
        text = (Path(work) / rel).read_text(encoding="utf-8", errors="replace") if rel in after else ""
        if rel in before:
            events.append({"tool": "Edit", "input": {"file_path": path, "new_string": text}})
        else:
            events.append({"tool": "Write", "input": {"file_path": path, "content": text}})
    return events


# ---------------------------------------------------------------- grading

def regex_flags(flags):
    return (re.I if "i" in flags else 0) | (re.M if "m" in flags else 0) | (re.S if "s" in flags else 0)


def grade_regex(grader, parsed, work):
    target = inline_map(grader.get("target") or "last_message")
    if isinstance(target, dict) and target.get("source") == "file":
        path = Path(work) / target["path"]
        if not path.is_file():
            return False, f"file {target['path']} missing"
        text, where = path.read_text(encoding="utf-8", errors="replace"), f"file {target['path']}"
    elif target == "trace":
        text, where = parsed["trace"], "trace"
    elif target == "last_message":
        text, where = parsed["final"], "last message"
    else:
        raise ValueError(f"unknown regex target {target!r}")
    found = re.search(str(grader["pattern"]), text, regex_flags(str(grader.get("flags") or "")))
    match = str(grader.get("match") or "contains")
    if match == "contains":
        return bool(found), f"matched {found.group(0)[:80]!r}" if found else f"pattern not found in {where}"
    if match == "not_contains":
        return not found, f"matched {found.group(0)[:80]!r} (expected absent)" if found else f"absent from {where}"
    raise ValueError(f"unknown regex match {match!r}")


def grade_file_exists(grader, work):
    pattern, want = str(grader["path"]), str(grader.get("exists", "true")).lower() != "false"
    hits = [rel for rel in files_of(work) if fnmatch.fnmatchcase(rel, pattern)]
    if want:
        return bool(hits), f"{hits[0]} present" if hits else f"{pattern} missing (expected present)"
    return not hits, f"{hits[0]} present (expected absent)" if hits else f"{pattern} absent as expected"


def tool_events(host, parsed, diff):
    """(case tool name, input) for each event the host's TOOL_MAP can name."""
    names = TOOL_MAP[host]
    events = [(e["tool"], e["input"]) for e in diff if names.get(e["tool"]) == "diff"]
    for name, data in parsed["tools"]:
        events += [(tool, data) for tool, source in names.items() if isinstance(source, tuple) and name in source]
    return events


def grade_tool_used(grader, host, parsed, diff):
    tool = str(grader["tool"])
    if tool not in TOOL_MAP[host]:
        return None, f"n/a: {tool} has no observable event on {host}"
    pattern = grader.get("input_match")
    count = sum(1 for name, data in tool_events(host, parsed, diff) if name == tool and (
        not pattern or re.search(str(pattern), json.dumps(data, separators=(",", ":"), ensure_ascii=False))))
    low, high = int(grader.get("min", 1)), grader.get("max")
    ok = count >= low and (high in (None, "") or count <= int(high))
    return ok, f"{tool} called {count}x (expected {low}..{'inf' if high in (None, '') else high})"


def judge(claude, model, criteria, reply, focus=None, votes=VOTES):
    """(verdict PASS/FAIL or None when a vote was unreadable, votes, judge cost in USD)."""
    text = f"Criterion: {criteria}\n\nReply:\n<<<\n{reply}\n>>>\n"
    if focus:
        text += f"\nFile {focus[0]}:\n<<<\n{focus[1]}\n>>>\n"
    command = [claude, "-p", "--model", model, "--tools", "", "--setting-sources", "project",
               "--disable-slash-commands", "--no-session-persistence", "--max-turns", "1", "--output-format", "json",
               "--system-prompt", JUDGE_SYSTEM]
    said, cost = [], 0.0
    for _ in range(votes):  # from the temp folder, so no project settings, plugins or MCP servers join the judge
        try:
            proc = subprocess.run(command, input=text, cwd=tempfile.gettempdir(), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=300)
            doc = json.loads(proc.stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            said.append(None)
            continue
        cost += float(doc.get("total_cost_usd") or 0)
        word = re.match(r"\s*[*_`]*\s*(PASS|FAIL)\b", str(doc.get("result") or ""), re.I)
        said.append(word.group(1).upper() if word else None)
    if None in said:
        return None, said, cost
    return ("PASS" if said.count("PASS") * 2 > len(said) else "FAIL"), said, cost


def grade_llm(grader, parsed, work, claude, model):
    focus = inline_map(grader.get("focus"))
    pair = None
    if isinstance(focus, dict) and focus.get("source") == "file":
        path = Path(work) / focus["path"]
        pair = (focus["path"], path.read_text(encoding="utf-8", errors="replace") if path.is_file() else "(missing)")
    verdict, said, cost = judge(claude, model, grader["criteria"], parsed["final"], pair)
    votes = " ".join(v or "?" for v in said)
    if verdict is None:
        raise ValueError(f"unreadable judge reply (votes: {votes})")
    return verdict == "PASS", f"judge votes: {votes}", cost


def grade_run(host, case, folder, claude=None, judge_model=None):
    """Grade a finished run folder (events.jsonl, answer.txt, changes.json, work/) against the case's graders."""
    folder = Path(folder)
    answer = (folder / "answer.txt").read_text(encoding="utf-8") if (folder / "answer.txt").is_file() else ""
    parsed = PARSERS[host](events_of(folder / "events.jsonl"), answer.strip() and answer)
    saved = folder / "changes.json"
    diff = json.loads(saved.read_text(encoding="utf-8")) if saved.is_file() else []
    work, graders, total, earned, judge_cost, failed = folder / "work", [], 0.0, 0.0, 0.0, None
    for grader in case["graders"]:
        kind, weight = grader.get("type"), float(grader.get("weight") or 1)
        try:
            if kind == "regex":
                ok, why = grade_regex(grader, parsed, work)
            elif kind == "file_exists":
                ok, why = grade_file_exists(grader, work)
            elif kind == "tool_used":
                ok, why = grade_tool_used(grader, host, parsed, diff)
            elif kind == "llm":
                if parsed["error"]:
                    ok, why = False, "not judged: the run did not finish"
                else:
                    ok, why, cost = grade_llm(grader, parsed, work, claude, judge_model)
                    judge_cost += cost
            else:
                raise ValueError(f"unknown grader type {kind!r}")
        except (KeyError, ValueError, re.error) as error:
            ok, why, failed = False, f"grader error: {error}", failed or f"grader {grader.get('name')}: {error}"
        graders.append({"name": grader.get("name"), "type": kind, "weight": weight, "pass": ok, "explanation": why})
        if ok is not None:
            total += weight
            earned += weight if ok else 0
    error = parsed["error"] or failed or (None if total else f"every grader is n/a on {host}")
    run = {"score": None if error else round(earned / total, 4), "costUsd": 0, "turns": parsed["turns"] or 1,
           "error": error, "usage": parsed["usage"], "judgeCostUsd": round(judge_cost, 4), "graders": graders,
           "folder": folder.as_posix()}
    if parsed.get("init"):
        run["init"] = parsed["init"]
    return run


# ---------------------------------------------------------------- running a host

def user_setup(host):
    """{~ path: content hash} of each non-empty file or folder entry in USER_SETUP[host], so a gate can tell when it
    changed between a baseline and a result."""
    home = Path.home()
    codex = Path(os.environ.get("CODEX_HOME") or home / ".codex")
    found = {}
    for pattern in USER_SETUP[host]:
        base = Path(pattern.format(home=home, codex=codex))
        for item in sorted(base.iterdir()) if base.is_dir() else [base] if base.is_file() else []:
            files = sorted(p for p in item.rglob("*") if p.is_file()) if item.is_dir() else [item]
            if not sum(f.stat().st_size for f in files):
                continue
            digest = hashlib.sha256()
            for file in files:
                digest.update(file.relative_to(item).as_posix().encode() + b"\0" + file.read_bytes() + b"\0")
            found[item.as_posix().replace(home.as_posix(), "~", 1)] = digest.hexdigest()[:12]
    return found


def version(exe):
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=60)
        return (proc.stdout or proc.stderr).strip().splitlines()[0]
    except (OSError, subprocess.SubprocessError, IndexError):
        return "unknown"


def host_command(host, exe, args, work, prompt, folder):
    """(command, stdin text) for one headless run in work."""
    if host == "codex":
        command = [exe, "exec", "--ignore-user-config", "--skip-git-repo-check", "-s", "workspace-write"]
        if os.name == "nt":  # --ignore-user-config drops the user's Windows sandbox setting, and reads fail without one
            command += ["-c", "windows.sandbox=elevated"]
        command += ["-c", "approval_policy=never"]
        command += ["-c", f"model_reasoning_effort={args.effort}"] if args.effort else []
        command += ["-m", args.model] if args.model else []
        return command + ["-C", str(work), "--json", "-o", str(folder / "answer.txt"), "--ephemeral", "-"], prompt
    return [exe, "-p", prompt, "--output-format", "stream-json", "--model", args.model, "--effort", args.effort,
            "--mode", "accept-edits", "--print-timeout", f"{args.timeout}s",
            "--disable-slash-commands",  # a prompt's /tinker:... would expand the installed plugin, not the snapshot
            "--log-file", str(folder / "agy.log")], None


def run_once(command, stdin, cwd, folder, timeout):
    """Run command with stdout to events.jsonl and stderr to stderr.txt; (seconds, timed out)."""
    start = time.monotonic()
    with open(folder / "events.jsonl", "w", encoding="utf-8") as out, \
            open(folder / "stderr.txt", "w", encoding="utf-8") as err:
        proc = subprocess.Popen(command, cwd=cwd, stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                                stdout=out, stderr=err, text=True, encoding="utf-8", errors="replace")
        try:
            proc.communicate(stdin, timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            if os.name == "nt":  # the host's own child processes too
                subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
            else:
                proc.kill()
            proc.wait()
            timed_out = True
    return time.monotonic() - start, timed_out


def selected(lv, root, args):
    for folder in lv.case_dirs(root):
        if args.case and not fnmatch.fnmatchcase(folder.name, args.case):
            continue
        case = lv.read_case(folder / "case.yaml")
        if args.tag and not set(args.tag) & set(case.get("tags") or []):
            continue
        yield folder.name, case


def run_host(args, root, temp, lv):
    """`eval_live.py run --host codex|agy`: lv is the eval_live module (its snapshot, bundle and scaffold helpers)."""
    host = args.host
    if args.adaptive or args.ablation != "none":
        raise lv.EvalError(f"--adaptive and --ablation with-without run on the claude host only, not {host}.")
    exe, claude = shutil.which(host), shutil.which("claude")
    if not exe:
        raise lv.EvalError(f"{host} is not on PATH.")
    cases = list(selected(lv, root, args))
    if not cases:
        raise lv.EvalError("No case matches --case/--tag.")
    needs_judge = any(g.get("type") == "llm" for _, case in cases for g in case["graders"])
    if needs_judge and not claude:
        raise lv.EvalError("claude is not on PATH, and the llm graders need it for the judge.")
    env = lv.scaffold_env()
    run_id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
    run_dir = Path(temp or tempfile.gettempdir()) / f"tinker_eval_{run_id}"
    tree = run_dir / "tinker"
    lv.snapshot(root, tree)
    fingerprint = lv.tree_fingerprint(tree)
    suite = lv.render_bundle(tree, run_dir / "home") / lv.BUNDLE_EVALS  # the scaffolds, LF and with root.txt
    bash = shutil.which("bash", path=env["PATH"])
    doc = {"host": host, "hostVersion": version(exe), "startedAt": datetime.now(timezone.utc).isoformat(),
           "suite": {"modelOverride": args.model or CODEX_MODEL, "judgeModel": args.judge_model,
                     "effort": args.effort or "provider-default"},
           "tree": fingerprint, "userSetup": user_setup(host), "costUsd": 0, "cases": []}
    total = sum(args.runs or case.get("runs") or 1 for _, case in cases)
    print(f"Run folder: {run_dir} ({total} {host} runs, one at a time)", flush=True)
    if doc["userSetup"]:
        groups = {}
        for key in doc["userSetup"]:
            parent, _, name = key.rpartition("/")
            groups.setdefault(parent if parent.endswith(("skills", "plugins")) else key, []).append(name)
        print(f"Not isolated: {host} also loads the user's own "
              + ", ".join(k if k in doc["userSetup"] else f"{k} ({', '.join(v) if len(v) < 6 else len(v)})"
                          for k, v in groups.items())
              + "; the runs measure the snapshot with them (userSetup in the result).", flush=True)
    stop = None
    for name, case in cases:
        prompt, runs = case_prompt(tree / lv.LIVE / name / "case.yaml"), []
        for index in range(args.runs or case.get("runs") or 1):
            folder = run_dir / "runs" / f"{name}-{index + 1}"
            work = folder / "work"
            work.mkdir(parents=True)
            (folder / "prompt.md").write_text(prompt, encoding="utf-8")
            if stop:
                (folder / "events.jsonl").write_text("", encoding="utf-8")
                runs.append({"score": None, "costUsd": 0, "turns": 0, "error": f"not run: {stop}"})
                continue
            setup = subprocess.run([bash, (suite / name / "setup.sh").as_posix()], cwd=work, env=env,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace")
            if setup.returncode != 0:
                raise lv.EvalError(f"The scaffold of {name} failed:\n{setup.stderr.strip()}")
            before = files_of(work)
            command, stdin = host_command(host, exe, args, work, prompt, folder)
            seconds, timed_out = run_once(command, stdin, work, folder, args.timeout)
            (folder / "changes.json").write_text(json.dumps(changes(work, before), indent=1), encoding="utf-8")
            run = grade_run(host, case, folder, claude, args.judge_model)
            if timed_out:
                run.update(score=None, error=f"timed out after {args.timeout}s")
            run["durationMs"] = round(seconds * 1000)
            if run["error"] and USAGE_LIMIT.search(run["error"]):
                stop = f"{host} reported a usage limit ({run['error'][:200]})"
            runs.append(run)
            verdicts = ", ".join(f"{g['name']} {'n/a' if g['pass'] is None else 'pass' if g['pass'] else 'FAIL'}"
                                 for g in run["graders"])
            print(f"{name} #{index + 1}: score {run['score']} in {round(seconds)}s"
                  + (f", ERROR {run['error']}" if run["error"] else "") + f" ({verdicts})", flush=True)
        doc["cases"].append({"name": name, "arms": {"with": runs}})
    doc["judgeCostUsd"] = round(sum(r.get("judgeCostUsd") or 0 for c in doc["cases"] for r in c["arms"]["with"]), 4)
    result = run_dir / "result.json"
    result.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
    kept = Path(root) / lv.LIVE / "results" / f"{run_id}.json"
    kept.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(result, kept)
    print(f"Result: {kept.as_posix()}")
    if stop:
        print(f"Stopped early: {stop}. Retry after the reset; the result stays invalid.", flush=True)
    return 1 if stop else 0
