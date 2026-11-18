"""Opt-in install of Tinker into Claude Code, Codex and Antigravity at user level.

Renders a small bundle (never this checkout) and registers it with each app's own CLI:
  ~/.tinker/runtime/tinker_runtime.py   the hook script the apps run (stable path)
  ~/.tinker/plugin/                 charter copy + Claude/Codex plugin manifests, hooks, skills, agents
  ~/.codex/agents/tinker-<role>.toml Codex teammates (Codex plugins carry no agents)
  ~/.gemini/config/plugins/tinker/  Antigravity plugin (rules, hooks, skills, agents)
  ~/.tinker/config.json, apps.json  root pointer, per-app revisions; what was written, with hashes
Replaces or deletes only files apps.json records with their current hash; a marker or folder name
never authorizes anything. Every unit is checked before writing, staged and validated (the staged
hook must deny a tamper payload), then activated behind a journal that restores the previous files
on failure. Registration is per app, recorded as enabled, disabled or unknown; nothing is atomic
across apps. Refuses an app where another Tinker installation is enabled or its settings cannot be
read, and a home whose apps.json it did not write (another installation can share the product name).
--instance <name> installs beside another installation instead, under its own names: home
~/.tinker-<name>, marketplace tinker-<name>, plugin id tinker@tinker-<name>, Antigravity folder
tinker-<name>. Where another Tinker is enabled, Claude gets this one installed but turned off, and
Codex and Antigravity are left out. Run it yourself, not through an agent. --dry-run prints the
plan; --uninstall removes only what apps.json records, after each app confirms its plugin is gone. --write-descriptors regenerates
this checkout's project descriptors. --design-skills instead installs the third-party design skills
globally through their own CLIs (npx); their files are theirs, never recorded in apps.json.
An install also schedules scripts/update.py --check for this checkout, daily by default (Windows Task
Scheduler; elsewhere it prints the crontab line): --update-check-hours 1-23 checks more often, 0 removes
it. Uninstalling the last installation made from this checkout removes it.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time

if sys.version_info < (3, 11):  # the hooks run on this interpreter too
    sys.exit(f"Tinker needs Python 3.11 or newer; {sys.executable} is {sys.version.split()[0]}. The python3 that "
             "comes with macOS is often 3.9: install a newer one (python.org, Homebrew or uv) and run this with it.")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tinker_runtime  # noqa: E402  (shared: charter files, digest, marker, hook names)
import update as tinker_update  # noqa: E402  (the daily update check)

ROOT = Path(__file__).resolve().parents[1]
MARKER_FILE = ".tinker-generated"
MARKETPLACE = "tinker-local"
PLUGIN_ID = f"tinker@{MARKETPLACE}"
SAFE_PATH = re.compile(r"^[A-Za-z0-9._:@\\/-]+$")  # @: Homebrew keeps Python under python@3.x
# Keep these in step with tinker_runtime.TOOL_KINDS. '-' makes Claude read a matcher as an unanchored regex;
# anchor it so only these tools reach the gate. Claude names a plugin's MCP tools mcp__plugin_<plugin>_<server>__<tool>.
CLAUDE_MATCHER = ("^(Bash|PowerShell|Monitor|Write|Edit|MultiEdit|NotebookEdit"
                  r"|mcp__(plugin_[\w.-]+_)?scheduled-tasks__(create|update)_scheduled_task)$")
CODEX_MATCHER = "^(Bash|apply_patch|automation_update)$"  # automation_update is not a documented hook tool name
# Antigravity's anchoring is undocumented, so the names stay unanchored: an extra match asks, a missed one is silent.
# `schedule` alone is anchored so tools such as a schedule listing never reach the gate.
ANTIGRAVITY_MATCHER = "run_command|code_action|write_to_file|replace_file_content|multi_replace_file_content|^schedule$"
ABOUT = "Tinker software team: Lead charter, nine specialists, workflows, approvals and presence."
AUTHOR = {"name": "Tinker"}
TOOLS = {
    "read": {"claude": "Read, Grep, Glob", "antigravity": ["view_file", "grep_search", "find_by_name", "list_dir"],
             "sandbox": "read-only", "policy": "off"},
    "write": {"claude": "Read, Grep, Glob, Edit, Write, Bash",
              "antigravity": ["view_file", "grep_search", "replace_file_content", "write_to_file", "run_command"],
              "sandbox": "workspace-write", "policy": "sandbox"},
}
# A role's optional `tier: light` marks a search-only helper: Claude runs it on its small model at low effort, and every
# host gives it only its own charter (on Claude also without CLAUDE.md, which would load the Lead charter), so a lookup
# costs a fraction of a full specialist. A cost hint, not a model matrix.
TIERS = {"light": {"claude": "model: haiku\neffort: low\nomitClaudeMd: true\n"}}
FINAL = {"read": "Read/search and return findings only; the Lead saves any requested artifact.",
         "write": "Edit or execute writing commands only while explicitly holding sole writing ownership."}
# The design skills policies/frontend-design.md routes UI work to. The CLI versions are pinned; the skill content is
# upstream's (skills-lock.json records the hashes reviewed on 2026-11-04). Hooks stay off: a global install would
# write Impeccable's hook into whatever folder the installer runs in.
DESIGN_SOURCES = ("emilkowalski/skill", "Leonxlnx/taste-skill")
SKILLS_CLI, IMPECCABLE_CLI = "skills@1.7.6", "impeccable@4.8.0"
SKILL_AGENTS = {"claude": "claude-code", "codex": "codex", "antigravity": "antigravity"}
IMPECCABLE_PROVIDERS = {"claude": "claude", "codex": "codex", "antigravity": "antigravity"}
NO_TELEMETRY = {"DO_NOT_TRACK": "1", "DISABLE_TELEMETRY": "1", "IMPECCABLE_NO_TELEMETRY": "1"}


# ---------------------------------------------------------------- roles and descriptors

def roles(root=ROOT):
    found = {}
    for path in sorted((root / "roles").glob("*.md")):
        fields = tinker_runtime.front_matter(path)
        if not re.fullmatch(r"[a-z][a-z-]*", path.stem) or fields.get("access") not in TOOLS or not fields.get("description"):
            raise ValueError(f"{path} needs front matter with description and access: read|write")
        if fields.get("tier", "light") not in TIERS or (fields.get("tier") and fields["access"] != "read"):
            raise ValueError(f"{path}: tier must be one of {sorted(TIERS)} and only on a read role")
        found[path.stem] = fields
    return found


def instructions(role, access, where, tier=None):
    if tier:
        return (f"Read roles/{role}.md {where['place']} and follow it. Do not spawn helpers. "
                "Use only the supplied scope; return actual evidence, never a simulated result. " + FINAL[access])
    return (f"Read {where['lead']}, policies/delegation.md and roles/{role}.md {where['place']}. "
            "Follow the canonical charter and the assigned target repository instructions. Do not spawn helpers. "
            "Use only the supplied scope and effective permissions; if a prerequisite is missing, return it to the Lead. "
            "Return actual evidence, never a simulated result. Do not update the shared checkpoint. " + FINAL[access])


def claude_agent(name, fields, body):
    tier = TIERS[fields["tier"]]["claude"] if fields.get("tier") else ""
    return (f"---\nname: {name}\ndescription: {json.dumps(fields['description'])}\n"
            f"tools: {TOOLS[fields['access']]['claude']}\n{tier}---\n\n{body}\n")


def codex_agent(name, fields, body):
    text = (f"name = {json.dumps(name)}\ndescription = {json.dumps(fields['description'])}\n"
            f"sandbox_mode = \"{TOOLS[fields['access']]['sandbox']}\"\n"
            f"developer_instructions = \"\"\"\n{body}\n\"\"\"\n\n[agents]\nenabled = false\n")
    if fields["access"] == "read":  # reader roles get no shell, as delegation policy requires
        text += "\n[features]\nshell_tool = false\n"
    return text


def antigravity_agent(name, fields, body):
    tools = "".join(f"  - {tool}\n" for tool in TOOLS[fields["access"]]["antigravity"])
    return (f"---\nname: {name}\ndescription: {json.dumps(fields['description'])}\ntools:\n{tools}"
            f"mainAgent: false\nsubagent: true\ncommandExecutionPolicy: {TOOLS[fields['access']]['policy']}\n---\n\n{body}\n")


PROJECT_PLACE = {"lead": "AGENTS.md", "place": "relative to the Tinker root supplied in the handoff"}


def project_descriptors(root=ROOT):
    """The checked-in descriptors, generated from roles/*.md front matter (drift-tested)."""
    files = {}
    for role, fields in roles(root).items():
        body = instructions(role, fields["access"], PROJECT_PLACE, fields.get("tier"))
        files[f".claude/agents/tinker-{role}.md"] = claude_agent(f"tinker-{role}", fields, body)
        files[f".codex/agents/tinker-{role}.toml"] = codex_agent(f"tinker-{role}", fields, body)
        files[f".agents/agents/tinker-{role}.md"] = antigravity_agent(f"tinker-{role}", fields, body)
    return files


# ---------------------------------------------------------------- charter copy

LINK = re.compile(r"\]\(([^)\s]+)\)")


def charter_tree(root, lead_path="AGENTS.md", instance="", python=None):
    """Charter files keyed by their bundle path, with relative links re-pointed at the copies.

    Skills move from .agents/skills/<name> to skills/<name>; AGENTS.md moves to lead_path.
    Links to files outside the charter point at the checkout by absolute path. A named installation's
    copy names its own home, and its runtime commands carry --instance. Off Windows, Tinker's
    scripts run on the hooks' interpreter.
    """
    files = tinker_runtime.charter_files(root)
    moved = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        if rel == "AGENTS.md":
            moved[rel] = lead_path
        elif rel.startswith(".agents/skills/"):
            moved[rel] = "skills/" + rel[len(".agents/skills/"):]
        else:
            moved[rel] = rel
    tree = {}
    for path in files:
        rel = path.relative_to(root).as_posix()
        new = moved[rel]
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")

        def relink(match):
            target = match.group(1)
            if target.startswith(("http://", "https://", "#", "mailto:")):
                return match.group(0)
            link, _, anchor = target.partition("#")
            source = (path.parent / link).resolve()
            try:
                source_rel = source.relative_to(root.resolve()).as_posix()
            except ValueError:
                return match.group(0)
            anchor = f"#{anchor}" if anchor else ""
            if source_rel in moved:
                start = Path(new).parent.as_posix()
                return f"]({os.path.relpath(moved[source_rel], start).replace(os.sep, '/')}{anchor})"
            return f"]({source.as_posix()}{anchor})"
        text = LINK.sub(relink, text)
        text = text.replace("python scripts/graphify_project.py",
                            f"python \"{(root / 'scripts' / 'graphify_project.py').as_posix()}\"")
        if instance:
            text = re.sub(r"~/\.tinker(?![\w-])", f"~/{tinker_runtime.instance_names(instance)['home']}", text)
            text = text.replace('scripts/tinker_runtime.py"`', f'scripts/tinker_runtime.py" --instance {instance}`')
        if python and os.name != "nt":  # macOS has no `python`, and an app's PATH may reach only its old python3
            text = re.sub(r"(?<![\w.-])python (?=scripts/|\")", shlex.quote(Path(python).as_posix()) + " ", text)
        tree[new] = text
    return tree


# ---------------------------------------------------------------- hook commands

def hook_commands(python, runtime, event, host, instance=""):
    exe, script = str(python), str(runtime)
    if not tinker_runtime.valid_instance(instance):
        raise ValueError(f"'{instance}' is not an installation name")
    tail = ["--instance", instance] if instance else []  # the runtime's state_dir() follows it
    words = " ".join([event, "--host", host, *tail])
    posix = f'"{Path(exe).as_posix()}" -I -S "{Path(script).as_posix()}" {words}'
    if host == "claude":  # exec form: no shell parses it
        return {"type": "command", "command": Path(exe).as_posix(),
                "args": ["-I", "-S", Path(script).as_posix(), event, "--host", host, *tail]}
    if host == "codex":  # PowerShell: a leading string needs `&`, and only `exit` passes exit code 2 through
        return {"type": "command", "command": posix,
                "commandWindows": f'& "{exe}" -I -S "{script}" {words}; exit $LASTEXITCODE'}
    # cmd /c mangles quotes differently per spawner (Node strips outer ones, Go escapes inner ones as \"),
    # so the Antigravity line carries no quotes at all; both paths must need none (and no ~, which it expands).
    limit = "only ASCII letters, digits and . _ : @ \\ / - (no spaces, ~, % or non-ASCII)"
    shell = "cmd /c" if os.name == "nt" else "a shell"
    if not SAFE_PATH.match(exe):
        raise ValueError(f"Antigravity runs hooks through {shell} unquoted; pass --python with a path of {limit} (got {exe}).")
    if not SAFE_PATH.match(script):
        raise ValueError(f"Antigravity runs hooks through {shell} unquoted; the home folder path needs {limit} (got {script}).")
    return {"type": "command", "command": f"{exe} -I -S {script} {words}"}


def claude_hooks(python, runtime, instance=""):
    def group(event, timeout, matcher=None):
        entry = {"hooks": [dict(hook_commands(python, runtime, event, "claude", instance), timeout=timeout)]}
        return [dict({"matcher": matcher}, **entry) if matcher else entry]
    return {"hooks": {"SessionStart": group("session-start", 10, "startup|resume|clear|compact|fork"),
                      "UserPromptSubmit": group("prompt-submit", 10),
                      "PreToolUse": group("pre-tool", 10, CLAUDE_MATCHER),
                      # Claude only: its PostToolUse can replace a tool's output, so long test logs arrive trimmed.
                      "PostToolUse": group("post-tool", 30, "Bash|PowerShell"),
                      "Stop": group("stop", 10), "SessionEnd": group("session-end", 5)}}


def codex_hooks(python, runtime, instance=""):
    def group(event, timeout, matcher=None):
        handler = dict(hook_commands(python, runtime, event, "codex", instance), timeout=timeout)
        entry = {"hooks": [handler]}
        return [dict({"matcher": matcher}, **entry) if matcher else entry]
    return {"hooks": {"SessionStart": group("session-start", 10, "startup|resume|clear|compact"),
                      "UserPromptSubmit": group("prompt-submit", 10),
                      "PreToolUse": group("pre-tool", 10, CODEX_MATCHER),
                      "Stop": group("stop", 10), "SessionEnd": group("session-end", 3)}}


def antigravity_hooks(python, runtime, instance=""):
    handler = lambda event: dict(hook_commands(python, runtime, event, "antigravity", instance), timeout=10)  # noqa: E731
    return {tinker_runtime.instance_names(instance)["folder"]: {"enabled": True,
                           "PreToolUse": [{"matcher": ANTIGRAVITY_MATCHER, "hooks": [handler("pre-tool")]}],
                           "PreInvocation": [handler("session-start")], "Stop": [handler("stop")]}}


# ---------------------------------------------------------------- rendering

def user_agents(root, charter_dir, lead):
    where = {"lead": lead, "place": f"in the installed Tinker charter at {Path(charter_dir).as_posix()} "
                                    f"(checkpoints and knowledge stay under {Path(root).as_posix()}/.tinker)"}
    return {role: (fields, instructions(role, fields["access"], where, fields.get("tier")))
            for role, fields in roles(root).items()}


def bundle_files(root, home, python, version, instance=""):
    names = tinker_runtime.instance_names(instance)
    base = home / names["home"] / "plugin"
    runtime = home / names["home"] / "runtime" / "tinker_runtime.py"
    files = {f"{k}": v for k, v in charter_tree(root, instance=instance, python=python).items()}
    files[MARKER_FILE] = f"Rendered by {root / 'scripts' / 'install_apps.py'}; re-run it instead of editing.\n"
    files[".claude-plugin/plugin.json"] = dumps({"name": "tinker", "version": version, "description": ABOUT,
                                                 "author": AUTHOR, "hooks": "./hooks/claude.json"})
    files[".claude-plugin/marketplace.json"] = dumps({"name": names["marketplace"], "owner": AUTHOR,
                                                      "description": "Tinker, installed from this machine.",
                                                      "plugins": [{"name": "tinker", "source": "./",
                                                                   "version": version, "description": ABOUT}]})
    files["plugin.json"] = dumps({"$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
                                  "name": "tinker", "version": version, "description": ABOUT, "author": AUTHOR,
                                  "extensions": {"com.openai": {"hooks": "./hooks/codex.json", "interface": {
                                      "displayName": "Tinker", "shortDescription": "Software team teammates",
                                      "developerName": "Tinker", "category": "Developer Tools",
                                      "capabilities": ["Interactive", "Read", "Write"]}}}})
    files[".agents/plugins/marketplace.json"] = dumps({
        "name": names["marketplace"], "interface": {"displayName": "Tinker"},
        "plugins": [{"name": "tinker", "source": {"source": "local", "path": "./"},
                     "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                     "category": "Developer Tools"}]})
    files["hooks/claude.json"] = dumps(claude_hooks(python, runtime, instance))
    files["hooks/codex.json"] = dumps(codex_hooks(python, runtime, instance))
    for role, (fields, body) in user_agents(root, base, "AGENTS.md").items():
        files[f"agents/{role}.md"] = claude_agent(role, fields, body)
    return base, files


def codex_agent_files(root, home, instance=""):
    base = home / tinker_runtime.instance_names(instance)["home"] / "plugin"
    return {home / ".codex" / "agents" / f"tinker-{role}.toml": codex_agent(f"tinker-{role}", fields, body)
            for role, (fields, body) in user_agents(root, base, "AGENTS.md").items()}


def antigravity_files(root, home, python, instance=""):
    names = tinker_runtime.instance_names(instance)
    base = home / ".gemini" / "config" / "plugins" / names["folder"]
    files = charter_tree(root, lead_path="rules/AGENTS.md", instance=instance, python=python)
    files[MARKER_FILE] = f"Rendered by {root / 'scripts' / 'install_apps.py'}; re-run it instead of editing.\n"
    files["plugin.json"] = dumps({"name": names["folder"]})
    files["hooks.json"] = dumps(antigravity_hooks(python, home / names["home"] / "runtime" / "tinker_runtime.py", instance))
    for role, (fields, body) in user_agents(root, base, "rules/AGENTS.md").items():
        files[f"agents/tinker-{role}.md"] = antigravity_agent(f"tinker-{role}", fields, body)
    return base, files


def dumps(value):
    return json.dumps(value, indent=2) + "\n"


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- installer

def replace(source, target):
    """os.replace with the short retry Windows needs while a reader holds the target open."""
    for attempt in range(5):
        try:
            os.replace(source, target)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.05)


def encode(content):
    return content if isinstance(content, bytes) else content.encode("utf-8")


def digest(files):
    """One digest for a set of rendered files, keyed by their paths."""
    total = hashlib.sha256()
    for path in sorted(files, key=str):
        total.update(str(path).encode("utf-8") + b"\0" + encode(files[path]) + b"\0")
    return total.hexdigest()


def is_link(path):
    return path.is_symlink() or bool(getattr(path, "is_junction", lambda: False)())


class Installer:
    """Installs, updates and removes only what apps.json records as Tinker's, by path and hash.

    Each unit (runtime, bundle, Codex agents, Antigravity plugin, config) is checked for conflicts
    before anything is written, staged and validated under ~/.tinker/staging/, then activated
    file by file behind a journal: previous files are backed up and restored if a replacement fails,
    and an interrupted run leaves `pending` hashes that let the next run recognise its own files.
    Registration is per app and never atomic across apps.
    """

    def __init__(self, home, python, dry_run=False, skip_cli=False, root=ROOT, out=print, instance=""):
        self.home, self.python, self.dry, self.skip_cli, self.root = Path(home), str(python), dry_run, skip_cli, Path(root)
        self.out, self.steps, self.failed = out, [], False
        if not tinker_runtime.valid_instance(instance):
            raise ValueError(f"'{instance}' is not an installation name (a-z, 0-9, at most 20, not 'local')")
        self.instance, self.names = instance, tinker_runtime.instance_names(instance)
        self.plugin_id, self.marketplace = self.names["plugin_id"], self.names["marketplace"]
        self.beside = {}  # app -> the other Tinker plugin ids that stay enabled there; ours is installed but off
        self.state = self.home / self.names["home"]
        self.apps_file = self.state / "apps.json"
        status, previous = tinker_runtime.read_state(self.apps_file)
        if status == "ok" and tinker_runtime.foreign_records(previous):
            status, previous = "foreign", None  # another installation's records: never read, never rewritten
        self.unreadable = status in ("unreadable", "foreign")
        self.records = status
        self.previous = previous or {}
        files, pending, apps = (self.previous.get(k) for k in ("files", "pending", "apps"))
        self.files = {p: h for p, h in files.items() if isinstance(h, str)} if isinstance(files, dict) else {}
        self.pending = {p: [h for h in v if isinstance(h, str)] for p, v in pending.items()
                        if isinstance(v, list)} if isinstance(pending, dict) else {}
        self.apps = {a: dict(v) for a, v in apps.items() if a in tinker_runtime.HOSTS and isinstance(v, dict)} \
            if isinstance(apps, dict) else {}
        artifacts = self.previous.get("artifacts")
        self.artifacts = dict(artifacts) if isinstance(artifacts, dict) else {}
        self.staging, self.staged_count = None, 0

    def step(self, app, action, detail):
        self.steps.append((app, action, detail))
        if action in ("Failed", "Refused"):
            self.failed = True

    # ---- ownership: recorded path and hash, never a marker or a folder name
    def owner(self, path):
        """'absent', 'owned' (recorded and unmodified, or mid-activation), 'changed' or 'foreign'."""
        path = Path(path)
        if not path.exists() and not is_link(path):
            return "absent"
        if is_link(path) or not path.is_file():
            return "foreign"
        key, current = str(path), sha256(path.read_bytes())
        if self.files.get(key) == current or current in self.pending.get(key, []):
            return "owned"
        return "changed" if key in self.files or key in self.pending else "foreign"

    def recorded_under(self, folder):
        return sorted({p for p in (*self.files, *self.pending) if Path(p).is_relative_to(folder)})

    def conflicts(self, files, folder=None):
        """Why a unit cannot be activated. Nothing is written."""
        if folder is not None and (folder.exists() or is_link(folder)):
            if is_link(folder) or not folder.is_dir():
                return [f"{folder} is a link or a file; move it away and re-run"]
            if not self.recorded_under(folder) and any(folder.iterdir()):
                return [f"{folder} exists and holds nothing recorded as Tinker's; move it away and re-run"]
        found = []
        for path in files:
            state = self.owner(path)
            if state == "changed":
                found.append(f"{path} changed since Tinker wrote it; move your copy away and re-run")
            elif state == "foreign":
                found.append(f"{path} exists and was not written by Tinker; move it away and re-run")
        return found

    # ---- staging and activation
    def stage(self, files):
        """Write candidates to this run's staging folder and validate them; {target: staged copy}."""
        if self.staging is None:
            self.staging = self.state / "staging" / f"{os.getpid()}-{os.urandom(4).hex()}"
        staged = {}
        for target, content in files.items():
            data = encode(content)
            if target.suffix == ".json":
                json.loads(data.decode("utf-8"))
            elif target.suffix == ".toml":
                import tomllib
                tomllib.loads(data.decode("utf-8"))
            copy = self.staging / str(self.staged_count) / target.name
            self.staged_count += 1
            copy.parent.mkdir(parents=True)
            copy.write_bytes(data)
            if sha256(copy.read_bytes()) != sha256(data):
                raise OSError(f"staged copy of {target} does not match what was rendered")
            staged[target] = copy
        return staged

    def activate(self, name, staged, stale=(), top=None):
        """Replace one unit's files from staging, all or nothing. Returns True when the unit is active."""
        changed = {t: s for t, s in staged.items() if not (t.is_file() and t.read_bytes() == s.read_bytes())}
        moved = [str(t) for t in changed if self.owner(t) not in ("absent", "owned")]
        if moved:  # changed by someone else since preflight: never replace it
            self.step(name, "Refused", f"{', '.join(moved)} changed during the install; nothing in {name} was replaced")
            return False
        previous = {str(t): self.pending.get(str(t)) for t in changed}
        for target, source in changed.items():  # journal: every hash that is ours stays ours until it settles
            known = [self.files.get(str(target)), *self.pending.get(str(target), []), sha256(source.read_bytes())]
            self.pending[str(target)] = list(dict.fromkeys(h for h in known if h))
        self.save()
        done = []
        try:
            for target, source in changed.items():
                backup = None
                if target.exists():
                    backup = self.staging / "backup" / name / str(len(done)) / target.name
                    backup.parent.mkdir(parents=True)
                    shutil.copy2(target, backup)
                target.parent.mkdir(parents=True, exist_ok=True)
                replace(source, target)
                done.append((target, backup))
        except Exception as error:
            for target, backup in reversed(done):
                if backup:
                    replace(backup, target)
                else:
                    target.unlink(missing_ok=True)
            for key, hashes in previous.items():  # an earlier interrupted run's hashes stay recognised
                if hashes:
                    self.pending[key] = hashes
                else:
                    self.pending.pop(key, None)
            self.save()
            self.step(name, "Failed", f"activation failed ({type(error).__name__}: {error}); previous files restored")
            return False
        for target in staged:  # every staged file is now on disk exactly as staged
            self.pending.pop(str(target), None)
            self.files[str(target)] = sha256(target.read_bytes())
        for path in stale:
            self.remove_owned(Path(path), name, top)
        return True

    # ---- removal
    def remove_owned(self, path, app, top=None):
        """Delete one file only while it is recorded as Tinker's and unmodified."""
        state = self.owner(path)
        if state == "absent":
            self.forget(path)
            return True
        if state != "owned":
            self.step(app, "Kept", f"{path} changed since install or is not Tinker's; not removed")
            return False
        if not self.dry:
            path.unlink()
            directory = path.parent
            while top is not None and directory.is_relative_to(top):  # empty folders this removal left behind
                try:
                    directory.rmdir()
                except OSError:
                    break
                directory = directory.parent
        self.forget(path)
        return True

    def forget(self, path):
        self.files.pop(str(path), None)
        self.pending.pop(str(path), None)

    def remove_folder(self, folder, app):
        """Remove the recorded, unmodified files under folder; anything else keeps its folder."""
        removed = [self.remove_owned(Path(p), app, folder) for p in self.recorded_under(folder)]
        if not self.dry and folder.is_dir() and any(p.is_file() for p in folder.rglob("*")):
            self.step(app, "Kept", f"{folder}: it still holds files Tinker did not write")
        return all(removed)

    # ---- host CLIs and registration state
    def cli(self, app, name, args, may_fail=False, env=None, timeout=180):
        shown = f"{name} {' '.join(args)}"
        if self.dry or self.skip_cli:
            self.step(app, "Would run" if self.dry else "Skipped", shown)
            return False
        exe = shutil.which(name)
        if not exe:
            self.step(app, "Skipped", f"{name} is not on PATH; run later: {shown}")
            return False
        env = dict(os.environ, HOME=str(self.home), USERPROFILE=str(self.home), **(env or {}))
        try:
            result = subprocess.run([exe, *args], capture_output=True, text=True, errors="replace", timeout=timeout, env=env)
        except (OSError, subprocess.TimeoutExpired) as error:
            self.step(app, "Noted" if may_fail else "Failed", f"{shown} -> {error}")
            return False
        if result.returncode == 0:
            self.step(app, "Ran", shown)
            return True
        detail = " ".join((result.stderr or result.stdout).split())[:200]
        self.step(app, "Noted" if may_fail else "Failed", f"{shown} -> exit {result.returncode}: {detail}")
        return False

    SETTINGS = {"claude": ".claude/settings.json", "codex": ".codex/config.toml", "antigravity": ".gemini/config/config.json"}

    def plugins(self, app, other=False):
        """{plugin id or Antigravity folder: enabled value} for this plugin, or with other=True for every other
        Tinker installation: any other tinker@ plugin or tinker[-<name>] folder, or this plugin's id or folder
        while these records do not account for the app. 'unknown' when the settings cannot be read or understood."""
        ours = app in self.apps
        match = (lambda key: key.startswith("tinker@") and not (ours and key == self.plugin_id)) if other \
            else (lambda key: key == self.plugin_id)
        if app == "claude":
            status, settings = tinker_runtime.read_state(self.home / ".claude" / "settings.json")
            if status == "missing":
                return {}
            plugins = settings.get("enabledPlugins", {}) if status == "ok" else None
            if not isinstance(plugins, dict):
                return "unknown"
            return {key: value for key, value in plugins.items() if match(key)}
        if app == "codex":
            path = self.home / ".codex" / "config.toml"
            if not path.exists():
                return {}
            try:
                import tomllib
                plugins = tomllib.loads(path.read_text(encoding="utf-8")).get("plugins", {})
            except (OSError, ValueError, ImportError):  # tomllib.TOMLDecodeError is a ValueError
                return "unknown"
            if not isinstance(plugins, dict) or any(not isinstance(v, dict) for k, v in plugins.items() if match(k)):
                return "unknown"
            return {key: value.get("enabled", True) for key, value in plugins.items() if match(key)}
        parent = self.home / ".gemini" / "config" / "plugins"
        if other:
            names = sorted(p.name for p in parent.iterdir() if re.fullmatch(r"tinker(-[a-z0-9]+)?", p.name)) \
                if parent.is_dir() else []
        else:
            names = [self.names["folder"]]
        found = {}
        config_status, config = tinker_runtime.read_state(self.home / ".gemini" / "config" / "config.json")
        for name in names:
            folder = parent / name
            if not folder.is_dir() or (other and self.recorded_under(folder)):
                continue
            status, manifest = tinker_runtime.read_state(folder / "plugin.json")
            if status == "missing" and not other:  # our folder without its manifest is no loadable plugin;
                continue                           # for another installation the folder alone counts, to stay safe
            plugins = (config or {}).get("plugins", {}) if config_status != "unreadable" else None
            choice = plugins.get(name, {}) if isinstance(plugins, dict) else None
            found[name] = "unknown" if not isinstance(choice, dict) or status == "unreadable" else \
                not (choice.get("enabled") is False or (manifest or {}).get("disabled"))
        return found

    def registration(self, app, other=False):
        """'enabled', 'disabled' (absent or turned off) or 'unknown' (settings unreadable or not understood),
        for this plugin, or with other=True for any other Tinker installation (see plugins)."""
        values = self.plugins(app, other)
        if values == "unknown":
            return "unknown"
        if any(value is True for value in values.values()):
            return "enabled"
        return "disabled" if all(value is False or value is None for value in values.values()) else "unknown"

    def others_enabled(self, app):
        values = self.plugins(app, other=True)
        return [key for key, value in values.items() if value is True] if isinstance(values, dict) else []

    UNKNOWN_RECORDS = {
        "unreadable": "{} cannot be read, so which files are Tinker's is unknown; nothing was changed. Repair it "
                      "and re-run",
        "foreign": "{} was written by another Tinker installation (the same product name, another installer), "
                   "which owns this home; nothing was changed. Install beside it with --instance <name> (a name "
                   "no other installation uses: its own home, marketplace and plugin id), or use project mode "
                   "(README, \"Choose how to run it\"), which runs this checkout from its own folder. Either way "
                   "that installation stays as it is",
    }
    DISABLE_OTHER = {
        "claude": "claude plugin disable {} --scope user",
        "codex": "codex plugin remove {} (or disable it in the Codex app's Plugins view)",
        "antigravity": "set \"plugins\": {{\"{}\": {{\"enabled\": false}}}} in ~/.gemini/config/config.json",
    }

    def disable_other(self, app, ids):
        return "; ".join(self.DISABLE_OTHER[app].format(i) for i in ids or ["tinker@tinker-local"])

    # ---- self-test: run each rendered command through its real shell with a tamper payload
    def self_test(self, app, handler):
        tamper = f"echo x > ~/{self.names['home']}/runtime/tinker_runtime.py"
        payload = json.dumps({"session_id": "", "cwd": str(self.root), "tool_name": "Bash",
                              "tool_input": {"command": tamper}})
        runs = []
        if app == "antigravity":
            payload = json.dumps({"conversationId": "", "workspacePaths": [str(self.root)],
                                  "toolCall": {"name": "run_command", "args": {"CommandLine": tamper}}})
            # Both plausible spawners: Node's verbatim `/d /s /c "..."` string, and an escaped argv (Go's default).
            runs = [f'cmd.exe /d /s /c "{handler["command"]}"', ["cmd.exe", "/d", "/c", handler["command"]]] \
                if os.name == "nt" else [["sh", "-c", handler["command"]]]
        elif app == "codex":
            shell = (shutil.which("pwsh") or shutil.which("powershell")) if os.name == "nt" else shutil.which("sh")
            if not shell:
                self.step(app, "Noted", "no shell found to self-test the hook command")
                return True
            runs = [[shell, "-NoProfile", "-Command", handler["commandWindows"]] if os.name == "nt" else [shell, "-c", handler["command"]]]
        else:
            runs = [[handler["command"], *handler["args"]]]
        env = dict(os.environ, USERPROFILE=str(self.home), HOME=str(self.home))
        for argv in runs:
            try:
                result = subprocess.run(argv, input=payload.encode("utf-8"), capture_output=True, timeout=30, env=env)
            except (OSError, subprocess.TimeoutExpired) as error:
                self.step(app, "Failed", f"hook self-test could not run: {error}")
                return False
            text = (result.stdout + result.stderr).decode("utf-8", "replace")
            if not ("tinker[tamper]" in text and (result.returncode == 2 if app != "antigravity" else '"deny"' in text)):
                self.step(app, "Failed", f"hook self-test failed (exit {result.returncode}): {text[:200]}")
                return False
        self.step(app, "Checked", f"staged hook self-test denied a tamper payload ({len(runs)} spawn form{'s' if len(runs) > 1 else ''})")
        return True

    def hook_handler(self, app, runtime, python):
        if app == "claude":
            return claude_hooks(python, runtime, self.instance)["hooks"]["PreToolUse"][0]["hooks"][0]
        if app == "codex":
            return codex_hooks(python, runtime, self.instance)["hooks"]["PreToolUse"][0]["hooks"][0]
        return antigravity_hooks(python, runtime, self.instance)[self.names["folder"]]["PreToolUse"][0]["hooks"][0]

    # ---- earlier manifests
    def migrate(self):
        """Read an earlier installer's records into this shape. Only a writing run saves the result;
        missing evidence stays missing and never becomes an ownership or activation claim."""
        if self.previous.get("schema") == 2:
            return
        status, config = tinker_runtime.read_state(self.state / "config.json")
        config = config if status == "ok" else {}
        for entry in self.apps.values():
            if "rendered" in entry:
                continue
            # The earlier installer rewrote one digest on every run: it describes only the app installed with it.
            version = entry.get("version")
            charter = config.get("charter_sha256") if version and version == config.get("version") else None
            revision = {"version": version, "charter_sha256": charter} if version else None
            entry.update(rendered=revision, activated=revision if entry.pop("registered", False) else None,
                         registration="unknown", recovery=None)

    def recovery(self, app):
        bundle = self.state / "plugin"
        if app == "claude":
            off = f"; claude plugin disable {self.plugin_id} --scope user" if app in self.beside else ""
            return f"claude plugin marketplace add {bundle}; claude plugin install {self.plugin_id} --scope user{off}"
        return f"codex plugin marketplace add {bundle}; codex plugin add {self.plugin_id}; then trust the hooks in /hooks"

    def switch(self, app):
        """How to make this installation the enabled one in Claude, everywhere or in one project."""
        others = self.beside[app]
        off = "; ".join(f"claude plugin disable {i} --scope user" for i in others)
        local = ", ".join([*(f"\"{i}\": false" for i in others), f"\"{self.plugin_id}\": true"])
        return (f"{off}; claude plugin enable {self.plugin_id} --scope user. For one project only, put "
                f"\"enabledPlugins\": {{{local}}} in its .claude/settings.local.json")

    # ---- install
    def install(self, apps):
        apps = list(apps)
        if self.unreadable:
            self.step("all", "Refused", self.UNKNOWN_RECORDS[self.records].format(self.apps_file))
            return self.finish()
        self.migrate()
        for app in list(apps):
            state = self.registration(app, other=True)
            others = self.others_enabled(app) if state == "enabled" else []
            mine = self.names["folder"] if app == "antigravity" else self.plugin_id
            beside = state == "enabled" and self.instance and mine not in others
            if beside and app == "claude":  # installed, then turned off: one chat never runs two Tinker gates
                self.beside[app] = others
                continue
            if beside:  # Codex's CLI cannot keep a plugin installed but off, and Antigravity loads every plugin folder
                self.step(app, "Skipped", f"another Tinker installation ({', '.join(others)}) is enabled in {app}, which "
                                          "cannot hold a second one turned off; this one stays out of it. To switch: "
                                          f"{self.disable_other(app, others)}, then re-run with --instance {self.instance} "
                                          f"--app {app}")
            elif state == "enabled":
                self.step(app, "Refused", f"another Tinker installation is enabled in this app; disable it first "
                                          f"({self.disable_other(app, others)}), then re-run")
            elif state == "unknown":
                self.step(app, "Refused", f"~/{self.SETTINGS[app]} cannot be read, so another Tinker installation may be "
                                          "enabled there; repair it and re-run")
            if state != "disabled":
                apps.remove(app)
        if not apps:
            return self.finish()
        staging = self.state / "staging"
        for leftover in sorted(staging.iterdir()) if staging.is_dir() else []:
            self.step("all", "Noted", f"{leftover} was left by an interrupted install (copies and backups); delete it once this run succeeds")
        version = f"0.3.{time.strftime('%Y%m%d%H%M%S', time.gmtime())}"
        charter = tinker_runtime.charter_digest(self.root)
        runtime, config = self.state / "runtime" / "tinker_runtime.py", self.state / "config.json"
        base = self.state / "plugin"
        units = {"runtime": (None, {runtime: (self.root / "scripts" / "tinker_runtime.py").read_bytes()})}
        if {"claude", "codex"} & set(apps):
            rendered = bundle_files(self.root, self.home, self.python, version, self.instance)[1]
            units["bundle"] = (base, {base / rel: content for rel, content in rendered.items()})
        if "antigravity" in apps:
            try:
                folder, files = antigravity_files(self.root, self.home, self.python, self.instance)
                units["antigravity"] = (folder, {folder / rel: content for rel, content in files.items()})
            except ValueError as error:
                self.step("antigravity", "Refused", str(error))
                apps.remove("antigravity")
        agents, kept_agents = {}, []
        if "codex" in apps:
            for path, content in codex_agent_files(self.root, self.home, self.instance).items():
                if self.owner(path) in ("absent", "owned"):
                    agents[path] = content
                else:
                    kept_agents.append(str(path))
                    self.step("codex", "Kept", f"{path} exists and is not Tinker's unmodified file; that teammate was not installed")
            units["agents"] = (None, agents)
        # Preflight every unit before anything is written.
        for name in ("runtime", "config"):
            problems = self.conflicts(units[name][1] if name in units else [config])
            for problem in problems:
                self.step("all", "Refused", problem)
            if problems:
                return self.finish()
        for name, dependents in (("bundle", ("claude", "codex")), ("antigravity", ("antigravity",))):
            if name in units:
                folder, files = units[name]
                problems = self.conflicts(files, folder)
                for problem in problems:
                    self.step(name, "Refused", problem)
                if problems:
                    units.pop(name)
                    if name == "bundle":
                        units.pop("agents", None)
                    apps = [a for a in apps if a not in dependents]
        if not apps:
            return self.finish()
        if self.dry:
            self.step("all", "Would write", f"{runtime} (hook runtime, stable path)")
            for name in ("bundle", "antigravity"):
                if name in units:
                    self.step(name, "Would render", f"{units[name][0]} ({len(units[name][1])} files, version {version})")
            for app in ("claude", "codex"):
                if app in apps:
                    self.register(app)
            return self.finish()
        try:
            staged = {name: self.stage(files) for name, (_, files) in units.items()}
        except (OSError, ValueError, ImportError) as error:  # tomllib is missing before Python 3.11
            self.step("all", "Failed", f"rendered files did not validate ({error}); nothing was changed")
            return self.finish(cleanup=True)
        # The runtime is shared: every app in this run, and every app already running it, must see the staged
        # copy deny a tamper payload through its own shell before it replaces the active one. An app outside
        # this run is tested with the interpreter its installed hooks use.
        status, previous_config = tinker_runtime.read_state(config)
        fallback = (previous_config or {}).get("python") if status == "ok" else None
        active_apps = {a for a, e in self.apps.items() if isinstance(e.get("activated"), dict)}
        failed = []
        for app in sorted(set(apps) | active_apps):
            python = self.python if app in apps else (self.apps[app]["activated"].get("python") or fallback or self.python)
            try:
                handler = self.hook_handler(app, staged["runtime"][runtime], python)
            except ValueError as error:
                self.step(app, "Failed", f"its hook self-test cannot be built with {python}: {error}")
                failed.append(app)
                continue
            if not self.self_test(app, handler):
                failed.append(app)
        running = [a for a in failed if a in active_apps]
        if running:
            self.step("all", "Refused", f"the staged runtime failed the self-test for {', '.join(running)}, which already "
                                        "run the installed runtime; nothing was activated. Include them in this run "
                                        "(--app all) with a working --python to reinstall their hooks as well")
            return self.finish(cleanup=True)
        apps = [a for a in apps if a not in failed]
        if not apps or not self.activate("runtime", staged["runtime"]):
            return self.finish(cleanup=True)
        self.artifacts["runtime"] = {"path": str(runtime), "rendered": sha256(units["runtime"][1][runtime]),
                                     "activated": self.files.get(str(runtime))}
        revision = {"version": version, "charter_sha256": charter, "python": self.python}
        active = set()
        if "bundle" in units and {"claude", "codex"} & set(apps):
            bundle_rev = dict(revision, digest=digest(units["bundle"][1]))
            stale = [p for p in self.recorded_under(base) if Path(p) not in units["bundle"][1]]
            previous = (self.artifacts.get("bundle") or {}).get("activated")
            ok = self.activate("bundle", staged["bundle"], stale, base)
            self.artifacts["bundle"] = {"path": str(base), "rendered": bundle_rev, "activated": bundle_rev if ok else previous}
            if ok:
                self.step("bundle", "Rendered", f"{base} ({len(units['bundle'][1])} files, version {version})")
                active.add("bundle")
        if "codex" in apps and "bundle" in active:
            stale = [p for p in self.apps.get("codex", {}).get("agents") or [] if Path(p) not in agents and p not in kept_agents]
            if self.activate("codex", staged["agents"], stale):
                active.add("agents")
        if "antigravity" in apps and "antigravity" in units:
            folder, files = units["antigravity"]
            stale = [p for p in self.recorded_under(folder) if Path(p) not in files]
            if self.activate("antigravity", staged["antigravity"], stale, folder):
                active.add("antigravity")
                self.step("antigravity", "Rendered", f"{folder} ({len(files)} files)")
        for app in apps:
            entry = self.apps.setdefault(app, {})
            if app == "antigravity":
                unit = units.get("antigravity", (None, {}))[1]
                rendered = dict(revision, digest=digest(unit), dir=str(units["antigravity"][0])) if unit else None
                files_active = registered = "antigravity" in active
            else:
                rendered = self.artifacts.get("bundle", {}).get("rendered")
                files_active = "bundle" in active and (app != "codex" or "agents" in active)
                registered = files_active and self.register(app)
            # Registering after a failed activation would load the restored, older files: re-run instead.
            recovery = None if registered else self.recovery(app) if app != "antigravity" and files_active \
                else "re-run the installer"
            entry.update(rendered=rendered, activated=rendered if registered else entry.get("activated"),
                         registration=self.registration(app), recovery=recovery)
            if app == "codex" and "agents" in active:
                entry["agents"] = sorted({*map(str, agents), *(p for p in entry.get("agents") or [] if p in kept_agents and p in self.files)})
            if not registered and not any(a == app and action == "Failed" for a, action, _ in self.steps):
                self.step(app, "Pending", f"rendered but not active in {app}; to finish: {recovery}")
            if registered and app in self.beside:
                self.step(app, "Next", f"Installed but turned off: {', '.join(self.beside[app])} stays the enabled "
                                       f"Tinker, so a chat never runs two gates and charters. To switch: {self.switch(app)}.")
            elif registered:
                self.step(app, "Next", {
                    "claude": "Start a new chat; skills appear as /tinker:<skill>, teammates as @agent-tinker:<role>.",
                    "codex": "Restart Codex and trust the Tinker hooks in /hooks (needed after every install); "
                             "skills appear as $<skill>, teammates as @tinker-<role>.",
                    "antigravity": "Restart Antigravity; the rule, skills and tinker-<role> agents load from the plugin."}[app])
        settings = {"root": str(self.root), "version": version, "runtime": str(runtime), "python": self.python,
                    "hosts": {app: {"charter_sha256": e["activated"].get("charter_sha256"), "version": e["activated"].get("version")}
                              for app, e in sorted(self.apps.items()) if isinstance(e.get("activated"), dict)}}
        try:
            staged_config = self.stage({config: dumps(settings)})
        except (OSError, ValueError) as error:
            self.step("all", "Failed", f"{config} could not be staged ({error}); the apps above were activated, but "
                                       "status may show them stale until the installer runs again")
        else:
            self.activate("config", staged_config)
        return self.finish(cleanup=True)

    def register(self, app):
        """Register the activated bundle with the app's CLI. False when not confirmed this run."""
        bundle = str(self.state / "plugin")
        if app == "claude":
            self.cli("claude", "claude", ["plugin", "marketplace", "add", bundle], may_fail=True)
            self.cli("claude", "claude", ["plugin", "marketplace", "update", self.marketplace], may_fail=True)
            installed = self.cli("claude", "claude", ["plugin", "install", self.plugin_id, "--scope", "user"], may_fail=True)
            registered = self.cli("claude", "claude", ["plugin", "update", self.plugin_id], may_fail=True) or installed
            # An install turns the plugin on, also one turned off earlier: beside another Tinker, turn it off again.
            if app in self.beside and (registered or self.dry) and \
                    not self.cli("claude", "claude", ["plugin", "disable", self.plugin_id, "--scope", "user"]) and registered:
                self.step(app, "Failed", f"{self.plugin_id} and {', '.join(self.beside[app])} are both enabled now; run "
                                         f"claude plugin disable {self.plugin_id} --scope user")
        else:
            self.cli("codex", "codex", ["plugin", "marketplace", "add", bundle], may_fail=True)
            self.cli("codex", "codex", ["plugin", "remove", self.plugin_id], may_fail=True)
            registered = self.cli("codex", "codex", ["plugin", "add", self.plugin_id], may_fail=True)
        if not registered and not self.dry and not self.skip_cli and shutil.which(app):
            self.step(app, "Failed", f"{self.plugin_id} is not registered: the {app} CLI did not confirm it (see above); "
                                     f"files stay in place for recovery: {self.recovery(app)}")
        return registered

    # ---- third-party design skills
    def design_skills(self, apps):
        """Install the design skills for these apps at user level with their own CLIs, without telemetry."""
        for source in DESIGN_SOURCES:
            self.cli("design", "npx", ["--yes", SKILLS_CLI, "add", source, "--global", "--skill", "*", "--yes",
                                       "--agent", *(SKILL_AGENTS[a] for a in apps)], env=NO_TELEMETRY, timeout=600)
        self.cli("design", "npx", ["--yes", IMPECCABLE_CLI, "install", "--global", "--no-hooks", "--yes",
                                   "--providers=" + ",".join(IMPECCABLE_PROVIDERS[a] for a in apps)],
                 env=NO_TELEMETRY, timeout=600)
        if not self.failed and not self.dry:
            self.step("design", "Next", "Start a new chat. Re-run --design-skills to update them.")
        return self.finish(save=False)

    # ---- uninstall
    def uninstall(self, apps):
        if self.unreadable:
            self.step("all", "Refused", self.UNKNOWN_RECORDS[self.records].format(self.apps_file))
            return self.finish()
        self.migrate()
        for app in [a for a in apps if a in self.apps]:
            if app == "antigravity":
                folder = Path(self.apps[app].get("dir") or (self.apps[app].get("rendered") or {}).get("dir")
                              or self.home / ".gemini" / "config" / "plugins" / self.names["folder"])
                cleared = self.remove_folder(folder, app)
            elif app == "claude":
                cleared = self.cli("claude", "claude", ["plugin", "uninstall", self.plugin_id, "--scope", "user"], may_fail=True)
            else:
                cleared = self.cli("codex", "codex", ["plugin", "remove", self.plugin_id], may_fail=True)
            state = self.registration(app)
            self.apps[app]["registration"] = state
            if self.dry:
                self.step(app, "Would remove", "registration and rendered files, once the app confirms it")
                continue
            if not ((cleared and app != "antigravity") or state == "disabled"):
                self.step(app, "Kept", f"registration {state}, not confirmed removed; " + (
                    "files it could not remove stay in its plugin folder, so Antigravity may still load them; remove "
                    "them yourself, then re-run --uninstall" if app == "antigravity" else
                    f"its files stay so the app keeps working. Remove {self.plugin_id} with the app, then re-run --uninstall"))
                self.failed = True
                continue
            if app in ("claude", "codex"):
                self.cli(app, app, ["plugin", "marketplace", "remove", self.marketplace], may_fail=True)
            if app == "codex":
                for path in self.apps[app].get("agents") or []:
                    self.remove_owned(Path(path), "codex")
            self.apps.pop(app)
            self.step(app, "Removed", "registration and rendered files")
        if not self.dry and not ({"claude", "codex"} & set(self.apps)) and self.recorded_under(self.state / "plugin"):
            self.remove_folder(self.state / "plugin", "bundle")
            self.artifacts.pop("bundle", None)
            self.step("bundle", "Removed", f"{self.state / 'plugin'} (files Tinker wrote)")
        if not self.dry and not self.apps:
            self.remove_owned(self.state / "config.json", "all")
            runtime = self.state / "runtime" / "tinker_runtime.py"
            self.step("all", "Kept", f"{runtime}: open chats still run it (a missing script exits 2 and blocks their tools); "
                                     f"restart open Claude, Codex and Antigravity chats, then delete {self.state}")
            self.step("all", "Kept", f"{self.state / 'state'} (presence, approvals and run outcomes); delete it yourself if unwanted")
        return self.finish()

    # ---- records and report
    def save(self):
        if self.dry:
            return
        self.state.mkdir(parents=True, exist_ok=True)
        tinker_runtime.write_json(self.apps_file, {"schema": 2, "root": str(self.root), "apps": self.apps,
                                               "artifacts": self.artifacts, "files": self.files, "pending": self.pending})

    def finish(self, cleanup=False, save=True):
        if save and not self.dry and (self.previous or self.files or self.apps):
            self.save()
        if cleanup and self.staging is not None:
            shutil.rmtree(self.staging, ignore_errors=True)  # this run's own copies; activation no longer needs them
            try:
                self.staging.parent.rmdir()
            except OSError:
                pass
        width = max((len(a) for a, _, _ in self.steps), default=3)
        for app, action, detail in self.steps:
            self.out(f"{app:<{width}}  {action:<12} {detail}")
        return 1 if self.failed else 0


def write_descriptors(root=ROOT):
    for rel, content in project_descriptors(root).items():
        path = root / rel
        if not path.exists() or path.read_bytes().decode("utf-8").replace("\r\n", "\n") != content:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))
            print(f"wrote {rel}")


def instance_name(value):
    if not tinker_runtime.valid_instance(value):
        raise argparse.ArgumentTypeError(f"'{value}' is not an installation name (a-z, 0-9, at most 20, not 'local')")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app", choices=["all", *tinker_runtime.HOSTS], default="all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--skip-app-cli", action="store_true", help="render files but do not call claude/codex")
    parser.add_argument("--home", default=str(Path.home()), help="user home to install into (tests use a temporary one)")
    parser.add_argument("--instance", default="", type=instance_name, metavar="NAME",
                        help="install beside another Tinker installation under its own names: ~/.tinker-NAME, "
                             "plugin id tinker@tinker-NAME (pass it again to update or uninstall)")
    parser.add_argument("--python", default=getattr(sys, "_base_executable", sys.executable),
                        help="interpreter the hooks run (never a virtual environment launcher)")
    parser.add_argument("--write-descriptors", action="store_true", help="regenerate this checkout's project descriptors")
    parser.add_argument("--design-skills", action="store_true",
                        help="install the third-party design skills at user level with npx (needs Node.js)")
    parser.add_argument("--update-check-hours", type=int, choices=range(25), default=24, metavar="0-24",
                        help="check whether this checkout is behind origin daily (24, the default) or every N hours, "
                             "with no agent (Windows Task Scheduler); 0 removes the check")
    args = parser.parse_args(argv)
    if args.write_descriptors:
        write_descriptors()
        return 0
    apps = list(tinker_runtime.HOSTS) if args.app == "all" else [args.app]
    installer = Installer(args.home, args.python, args.dry_run, args.skip_app_cli, instance=args.instance)
    if args.dry_run:
        print("[dry run] nothing is written and no app CLI runs")
    if args.design_skills:
        return installer.design_skills(apps)
    if args.uninstall:
        code = installer.uninstall(apps)
        others = [f for f in tinker_update.installations(args.home, ROOT) if f["instance"] != args.instance]
        if code == 0 and args.app == "all" and not others and not args.skip_app_cli:
            tinker_update.schedule(ROOT, remove=True, dry_run=args.dry_run)
        return code
    code = installer.install(apps)
    # Whenever an installation from this checkout exists, also after a partial failure; a check that cannot be
    # scheduled never fails the install: the schedule says why.
    if not args.skip_app_cli and (args.dry_run or tinker_update.installations(args.home, ROOT)):
        tinker_update.schedule(ROOT, args.update_check_hours or 24, remove=not args.update_check_hours,
                               dry_run=args.dry_run)
    return code


if __name__ == "__main__":
    sys.exit(main())
