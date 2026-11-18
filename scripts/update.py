"""Update this Tinker checkout and the installations made from it, or only check whether it is behind.

    python scripts/update.py [--check] [--dry-run]
    python scripts/update.py --schedule [--every-hours N] [--dry-run]
    python scripts/update.py --unschedule [--dry-run]

Fetches origin with every prompt off, so an unattended run fails instead of waiting for a password. Then fast-forwards
the default branch (origin/HEAD, else main or master) only when the checkout is on it, its tracked files are clean and
it has no commits of its own; otherwise it says why and changes nothing: it never stashes, switches, resets or merges.
Then it re-runs the freshly pulled installer for each installation made from this checkout (a home ~/.tinker or
~/.tinker-NAME whose config.json names it as root) when the pull moved HEAD or an app there is stale, with the apps,
interpreter and --instance it recorded. It runs the installer, so run it yourself, not through an agent.

--check only fetches and records how far behind the checkout is: it pulls and installs nothing. --dry-run fetches and
says what it would do. Every run except --dry-run records its result in this checkout's .tinker/update.json, which
status and the session-start note read. --schedule registers a Windows Task Scheduler task that runs --check daily at
09:00 (every N hours with --every-hours), as you and only while you are logged on, catching up after sleep: no agent,
no tokens. --unschedule removes it. Neither touches a task that runs another checkout's script. On macOS and Linux they
print the crontab line to add instead. Standard library only.
"""
import argparse
import datetime
import hashlib
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import tinker_runtime  # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # a windowless scheduled run must not open consoles for git
LOCK_STALE = 15 * 60


def record_path(root):
    return Path(root) / ".tinker" / "update.json"


def git_env(root):
    """Nobody may be watching (the scheduled check): never wait on a credential or host-key prompt."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")
    if not env.get("GIT_SSH_COMMAND") and not env.get("GIT_SSH") and not git(root, "config", "--get", "core.sshCommand",
                                                                             env=env)[0]:
        env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o ConnectTimeout=20"
    return env


def git(root, *args, env=None, timeout=300):
    """Run git in root; returns (ok, stdout lines, combined text for messages)."""
    try:
        done = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8",
                              errors="replace", stdin=subprocess.DEVNULL, env=env, timeout=timeout,
                              creationflags=NO_WINDOW)
    except (OSError, subprocess.SubprocessError) as error:
        return False, [], str(error)
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    return done.returncode == 0, lines, " ".join((done.stdout + done.stderr).split())


def first(root, *args, env=None):
    ok, lines, _ = git(root, *args, env=env)
    return lines[0] if ok and lines else None


def default_branch(root, env=None):
    ref = first(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD", env=env)
    if ref and ref.startswith("origin/"):
        return ref[len("origin/"):]
    for name in ("main", "master"):
        if git(root, "show-ref", "--verify", "--quiet", f"refs/remotes/origin/{name}", env=env)[0]:
            return name
    return None


def plural(count, word):
    return f"{count} {word}{'' if count == 1 else 's'}"


def same_path(a, b):
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except (OSError, ValueError, TypeError):
        return False


def installations(home, root):
    """(instance, home folder, config) for each Tinker home whose own records name this checkout as root.
    Another installation's home (its records in another shape, or another root) is never read further."""
    found = []
    for folder in sorted(Path(home).glob(".tinker*")):
        name = folder.name
        instance = name[len(".tinker-"):] if name.startswith(".tinker-") else "" if name == ".tinker" else None
        if instance is None or not tinker_runtime.valid_instance(instance) or not folder.is_dir():
            continue
        status, records = tinker_runtime.read_state(folder / "apps.json")
        if status != "ok" or tinker_runtime.foreign_records(records):
            continue
        cfg = tinker_runtime.read_json(folder / "config.json")
        if isinstance(cfg, dict) and cfg.get("root") and same_path(cfg["root"], root):
            apps = [h for h in tinker_runtime.HOSTS if h in (cfg.get("hosts") or {})] or \
                   [h for h in tinker_runtime.HOSTS if h in records["apps"]]
            found.append({"instance": instance, "folder": folder, "config": cfg, "apps": apps})
    return found


def stale_apps(found, root):
    """The installation's apps whose installed copy is not this checkout's charter."""
    return [app for app in found["apps"] if tinker_runtime.install_state(found["config"], app, root) != "current"]


def installer_runs(found, apps, home, root):
    """Installer command lines that refresh these apps of one installation, as it was installed."""
    base = [sys.executable, str(Path(root) / "scripts" / "install_apps.py"), "--home", str(home)]
    python = found["config"].get("python")
    if python and Path(python).is_file():
        base += ["--python", python]
    if found["instance"]:
        base += ["--instance", found["instance"]]
    if set(apps) == set(tinker_runtime.HOSTS):
        return [base + ["--app", "all"]]
    return [base + ["--app", app] for app in apps]


# ---------------------------------------------------------------- result record and lock

def read_record(root):
    record = tinker_runtime.read_json(record_path(root))
    return record if isinstance(record, dict) else {}


def save_record(root, state, scheduled=False):
    """Record this run's result; a scheduled run's time survives later manual runs, so a stopped check shows."""
    previous = read_record(root)
    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    record = {"checked": now, "root": str(root), **state,
              "scheduled_at": now if scheduled else previous.get("scheduled_at")}
    path = record_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(f".update.{os.getpid()}.tmp")
        temp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
        os.replace(temp, path)
    except OSError as error:
        print(f"  could not record the result in {path}: {error}")


class Lock:
    """One update at a time per checkout: the scheduled check and a manual update may meet."""

    def __init__(self, root):
        self.path, self.held = record_path(root).with_name("update.lock"), False

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                os.close(os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                self.held = True
                break
            except FileExistsError:
                try:
                    if time.time() - self.path.stat().st_mtime < LOCK_STALE:
                        break
                    self.path.unlink()  # left behind by a run that was killed
                except OSError:
                    break
        return self

    def __exit__(self, *_):
        if self.held:
            try:
                self.path.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------- update and check

def update(root, home, check=False, dry_run=False, scheduled=False, say=print, run=subprocess.run):
    """Check or update one checkout; returns the exit code."""
    root = Path(root)

    def stop(status, detail, facts=None):
        say(f"  {detail}")
        if not dry_run:
            save_record(root, {"status": status, "detail": detail, **(facts or {})}, scheduled)
        return 1

    say(f"Tinker {'update check' if check else 'update'}{' (dry run)' if dry_run else ''}: {root}")
    if not git(root, "rev-parse", "--git-dir")[0]:
        return stop("error", f"{root} is not a git checkout")
    env = git_env(root)
    before = first(root, "rev-parse", "--short", "HEAD", env=env)
    default = default_branch(root, env)
    ok, _, text = git(root, "fetch", "--prune", "--quiet", "origin", env=env)
    if not ok and default:  # colliding remote refs: the default branch alone
        ok, _, text = git(root, "fetch", "--quiet", "origin", default, env=env)
    if not ok:
        # Offline (a run at wake before the network is up): keep the last known count, so waiting updates stay visible.
        known = {"head": before}
        if isinstance(read_record(root).get("behind"), int):
            known["behind"] = read_record(root)["behind"]
        return stop("error", f"fetch failed: {tinker_runtime.one_line(text, 300)}", known)
    default = default_branch(root, env)
    if not default or not git(root, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{default}", env=env)[0]:
        return stop("error", "no default branch on origin (origin/HEAD, main or master)", {"head": before})

    branch = first(root, "branch", "--show-current", env=env) or ""
    behind = int(first(root, "rev-list", "--count", f"HEAD..origin/{default}", env=env) or 0)
    ahead = int(first(root, "rev-list", "--count", f"origin/{default}..HEAD", env=env) or 0)
    facts = {"branch": branch, "default": default, "behind": behind, "head": before}

    if check:
        detail = f"{plural(behind, 'new commit')} on origin/{default}: run python scripts/update.py" if behind \
            else f"up to date with origin/{default}"
        say(f"  {detail}")
        if not dry_run:
            save_record(root, {"status": "behind" if behind else "current", "detail": detail, **facts}, scheduled)
        return 0

    if branch != default:
        on = f"branch {branch}" if branch else "a detached HEAD"
        return stop("blocked", f"not updated: the checkout is on {on}, not {default}; switch to {default} and run it "
                               "again", facts)
    if behind:
        if ahead:
            return stop("blocked", f"not updated: {default} has {plural(ahead, 'local commit')} that origin/{default} "
                                   "lacks; push or rebase them first", facts)
        dirty = git(root, "status", "--porcelain", "--untracked-files=no", env=env)[1]
        if dirty:
            return stop("blocked", f"not updated: {plural(len(dirty), 'tracked file')} with uncommitted changes; "
                                   "commit or stash them first", facts)
        if dry_run:
            say(f"  would fast-forward {default} from {before} to origin/{default} ({plural(behind, 'commit')})")
        else:
            ok, _, text = git(root, "merge", "--ff-only", "--quiet", f"origin/{default}", env=env)
            if not ok:
                return stop("blocked", f"not updated: fast-forward failed: {tinker_runtime.one_line(text, 300)}", facts)
            after = first(root, "rev-parse", "--short", "HEAD", env=env)
            say(f"  {default} {before} -> {after} ({plural(behind, 'commit')})")
            for subject in git(root, "log", "--format=%s", "--max-count=8", f"{before}..{after}", env=env)[1]:
                say(f"    {subject}")
            if behind > 8:
                say(f"    ... and {behind - 8} more")
    else:
        say(f"  {default} at {before}: nothing to pull")

    facts.update(head=first(root, "rev-parse", "--short", "HEAD", env=env), behind=behind if dry_run else 0)
    moved = behind > 0
    plans = []
    for found in installations(home, root):
        apps = found["apps"] if moved else stale_apps(found, root)
        if apps:
            plans.append((found, apps))
    if not plans:
        say("  no installation from this checkout needs a reinstall" if moved
            else "  every installation from this checkout is current")
        if not dry_run:
            save_record(root, {"status": "updated" if moved else "current",
                               "detail": f"up to date with origin/{default}", **facts}, scheduled)
        return 0
    failed = []
    for found, apps in plans:
        label = f"--instance {found['instance']}" if found["instance"] else "the default installation"
        for command in installer_runs(found, apps, home, root):
            if dry_run:
                say(f"  would reinstall {label}: {subprocess.list2cmdline(command)}")
                continue
            say(f"  reinstalling {label} ({', '.join(apps)}) from {facts['head']}")
            # The pulled installer, in its own process: this one still holds the scripts as they were before the pull.
            done = run(command, stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
            if done.returncode != 0:
                failed.append(f"{label} (installer exit {done.returncode})")
    if dry_run:
        return 0
    if failed:
        return stop("error", f"reinstall failed: {'; '.join(failed)}", facts)
    say("  next: start a new chat (restart Codex and Antigravity, and trust the hooks in Codex)")
    save_record(root, {"status": "updated", "detail": f"updated to {facts['head']} and reinstalled", **facts}, scheduled)
    return 0


# ---------------------------------------------------------------- daily check

def task_name(root):
    """One task per checkout; the default installation's name stays free for another Tinker edition."""
    digest = hashlib.sha256(os.path.normcase(str(Path(root).resolve())).encode("utf-8")).hexdigest()[:8]
    return f"TinkerUpdateCheck-{digest}"


def check_command(root, python=None):
    """(program, arguments) the scheduled check runs, windowless: pythonw, else a headless console."""
    python = Path(python or getattr(sys, "_base_executable", None) or sys.executable)
    script = Path(root) / "scripts" / "update.py"
    arguments = f"\"{script}\" --check --scheduled"
    windowless = python.with_name("pythonw.exe")
    if windowless.is_file():
        return str(windowless), arguments
    conhost = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "conhost.exe"
    if conhost.is_file():  # a plain console action flashes a window on every run
        return str(conhost), f"--headless \"{python}\" {arguments}"
    return str(python), arguments


def task_xml(root, every_hours, program, arguments, start=None):
    start = start or datetime.datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    when = "daily at 09:00" if every_hours == 24 else f"every {every_hours} h from 09:00"
    repetition = "" if every_hours == 24 else (f"<Repetition><Interval>PT{every_hours}H</Interval><Duration>P1D</Duration>"
                                               "<StopAtDurationEnd>false</StopAtDurationEnd></Repetition>")
    description = (f"Tinker: checks {when} whether {root} is behind origin (git fetch only; no agent, no tokens). "
                   f"Result in {record_path(root)}.")
    return f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>{escape(description)}</Description></RegistrationInfo>
  <Triggers>
    <CalendarTrigger>{repetition}<StartBoundary>{start.strftime('%Y-%m-%dT%H:%M:%S')}</StartBoundary><Enabled>true</Enabled>
      <ScheduleByDay><DaysInterval>1</DaysInterval></ScheduleByDay></CalendarTrigger>
  </Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <ExecutionTimeLimit>PT10M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec><Command>{escape(program)}</Command><Arguments>{escape(arguments)}</Arguments><WorkingDirectory>{escape(str(root))}</WorkingDirectory></Exec>
  </Actions>
</Task>
""", when


def schtasks(*args):
    try:
        done = subprocess.run(["schtasks", *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                              stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, timeout=60)
    except (OSError, subprocess.SubprocessError) as error:
        return False, str(error)
    return done.returncode == 0, done.stdout + done.stderr


def existing_task(name, root):
    """None when there is no such task, else whether its action runs this checkout's update.py."""
    ok, text = schtasks("/Query", "/TN", name, "/XML")
    if not ok:
        return None
    script = os.path.normcase(str(Path(root) / "scripts" / "update.py"))
    actions = re.findall(r"<Arguments>(.*?)</Arguments>", text, re.S)
    return any(script in os.path.normcase(html.unescape(arguments)) for arguments in actions)


def cron_line(root, python=None):
    python = python or sys.executable
    return f"0 9 * * * cd \"{root}\" && \"{python}\" scripts/update.py --check --scheduled >/dev/null 2>&1"


def schedule(root, every_hours=24, remove=False, dry_run=False, name=None, say=print, platform=None):
    """Register, replace or remove this checkout's daily check; returns the exit code."""
    name = name or task_name(root)
    if (platform or os.name) != "nt":
        if remove:
            say(f"update check: remove the crontab line that runs {Path(root) / 'scripts' / 'update.py'} (crontab -e)")
        else:
            say(f"update check: not scheduled (Task Scheduler is Windows only); to check daily, add with crontab -e: "
                f"{cron_line(root)}")
        return 1
    ours = existing_task(name, root)
    if ours is False:
        say(f"update check: task {name} exists and runs another checkout's script; left alone")
        return 1
    if remove:
        if ours is None:
            say(f"update check: no scheduled task {name}")
            return 0
        if dry_run:
            say(f"update check: would remove scheduled task {name}")
            return 0
        ok, text = schtasks("/Delete", "/TN", name, "/F")
        say(f"update check: removed scheduled task {name}" if ok
            else f"update check: could not remove {name}: {tinker_runtime.one_line(text, 200)}")
        return 0 if ok else 1
    program, arguments = check_command(root)
    xml, when = task_xml(root, every_hours, program, arguments)
    verb = "replace" if ours else "register"
    if dry_run:
        say(f"update check: would {verb} scheduled task {name} ({when}): {program} {arguments}")
        return 0
    folder = tempfile.mkdtemp(prefix="tinker-task-")
    path = Path(folder) / "task.xml"
    try:
        path.write_text(xml, encoding="utf-16")
        ok, text = schtasks("/Create", "/TN", name, "/XML", str(path), "/F")
    finally:
        path.unlink(missing_ok=True)
        os.rmdir(folder)
    done = {"register": "registered", "replace": "replaced"}[verb]
    say(f"update check: {done} scheduled task {name} ({when}, git fetch only)" if ok else f"update check: could not {verb} {name}: {tinker_runtime.one_line(text, 200)}")
    return 0 if ok else 1


def hours(value):
    number = int(value)
    if not 1 <= number <= 24:
        raise argparse.ArgumentTypeError("--every-hours takes 1 to 24")
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check", action="store_true", help="fetch and record how far behind; pull and install nothing")
    action.add_argument("--schedule", action="store_true", help="register the daily check (Windows Task Scheduler)")
    action.add_argument("--unschedule", action="store_true", help="remove this checkout's scheduled check")
    parser.add_argument("--dry-run", action="store_true", help="fetch, then say what would happen; record nothing")
    parser.add_argument("--every-hours", type=hours, default=24, help="with --schedule: 24 (daily, the default) or 1-23")
    parser.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--home", default=str(Path.home()), help="user home whose installations are refreshed (tests)")
    parser.add_argument("--task-name", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.schedule or args.unschedule:
        return schedule(ROOT, args.every_hours, remove=args.unschedule, dry_run=args.dry_run, name=args.task_name)
    with Lock(ROOT) as lock:
        if not lock.held:
            print("Tinker update: another update of this checkout is running; skipped.")
            return 0
        return update(ROOT, args.home, check=args.check, dry_run=args.dry_run, scheduled=args.scheduled)


if __name__ == "__main__":
    sys.exit(main())
