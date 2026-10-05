"""Choose which platform's scripts this Tinker checkout runs: Windows (PowerShell 7) or Linux (bash, Debian tested).

  python scripts/tinker_platform.py                       # show the platform in use and where it comes from
  python scripts/tinker_platform.py set linux             # or windows, or auto (detect from this machine)
  python scripts/tinker_platform.py kit setup [args...]   # run the Buzz kit's setup, teardown or kit commands

The choice is stored in this checkout's ignored .tinker/platform.json, so it survives pulls and needs no fork.
TINKER_PLATFORM in the environment outranks it for one command. `auto` picks windows on Windows and linux
everywhere else. `kit` takes the bash spelling on every platform (--project x, --owner-npub npub1...,
--repository a --repository b, --yes) and turns it into PowerShell parameters on Windows; -Project style passes as is.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KIT = ROOT / "integrations" / "buzz" / "kit"
CHOICES = ("auto", "windows", "linux")
PLATFORMS = ("windows", "linux")
KIT_SCRIPTS = ("setup", "teardown", "kit")


def settings_file(root=ROOT):
    return Path(root) / ".tinker" / "platform.json"


def detected():
    return "windows" if os.name == "nt" else "linux"


def configured(root=ROOT):
    """The stored choice (auto when unset or unreadable)."""
    try:
        value = json.loads(settings_file(root).read_text(encoding="utf-8")).get("platform")
    except (OSError, ValueError, AttributeError):
        return "auto"
    return value if value in CHOICES else "auto"


def resolve(root=ROOT, environ=None):
    """(platform, source): the environment, then the stored choice, then this machine."""
    env = (os.environ if environ is None else environ).get("TINKER_PLATFORM", "").strip().lower()
    if env:
        if env not in CHOICES:
            raise ValueError(f"TINKER_PLATFORM must be one of {', '.join(CHOICES)}, not {env!r}")
        if env != "auto":
            return env, "TINKER_PLATFORM"
    stored = configured(root)
    if stored != "auto":
        return stored, str(settings_file(root))
    return detected(), "detected"


def save(choice, root=ROOT):
    if choice not in CHOICES:
        raise ValueError(f"platform must be one of {', '.join(CHOICES)}, not {choice!r}")
    path = settings_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"platform": choice}, indent=2) + "\n", encoding="utf-8")
    return path


VALUE_OPTIONS = {"project": "Project", "port": "Port", "tinker-repo": "TinkerRepo", "tinker-commit": "TinkerCommit",
                 "credential-file": "CredentialFile", "owner-npub": "OwnerNpub", "repository": "Repository",
                 "state-root": "StateRoot"}
FLAG_OPTIONS = {"images": "-Images", "state-folder": "-StateFolder", "yes": "-Confirm:$false"}


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def ps_arguments(args):
    """bash-style options (--owner-npub x, repeated --repository) as PowerShell parameters; -Options pass as they are."""
    out, repos, rest = [], None, list(args)
    while rest:
        arg = rest.pop(0)
        name = arg[2:].lower() if arg.startswith("--") else None
        if name in FLAG_OPTIONS:
            out.append(FLAG_OPTIONS[name])
        elif name in VALUE_OPTIONS:
            if not rest:
                raise ValueError(f"{arg} needs a value")
            value = rest.pop(0)
            if name == "repository":
                repos = (repos or []) + ([value] if value else [])
            else:
                out += [f"-{VALUE_OPTIONS[name]}", ps_quote(value)]
        elif name is not None:
            raise ValueError(f"unknown option {arg}")
        else:
            out.append(arg)
    if repos is not None:  # -Repository '' removes the stored repositories, as --repository '' does
        out += ["-Repository", ",".join(map(ps_quote, repos)) if repos else "''"]
    return out


def kit_command(platform, script, args=()):
    """The argv that runs one Buzz kit script for the platform. bash takes either spelling of the options."""
    if script not in KIT_SCRIPTS:
        raise ValueError(f"kit script must be one of {', '.join(KIT_SCRIPTS)}, not {script!r}")
    if platform == "linux":
        return ["bash", str(KIT / f"{script}.sh"), *args]
    shell = shutil.which("pwsh") or "pwsh"
    if script == "kit":  # kit.ps1 is dot-sourced, then one of its commands runs: kit --project x Get-KitStatus
        prelude, rest = [], list(args)
        while len(rest) >= 2 and rest[0].lower() in ("--project", "--state-root", "-project", "-stateroot"):
            prelude += ps_arguments(rest[:2]) if rest[0].startswith("--") else [rest[0], ps_quote(rest[1])]
            rest = rest[2:]
        command = " ".join(rest) or "Get-KitStatus"
        return [shell, "-NoProfile", "-Command", " ".join([".", ps_quote(KIT / "kit.ps1"), *prelude]) + f"; {command}"]
    return [shell, "-NoProfile", "-Command", " ".join(["&", ps_quote(KIT / f"{script}.ps1"), *ps_arguments(args)])]


def describe(root=ROOT):
    platform, source = resolve(root)
    lines = [f"Platform: {platform} ({'from ' + source if source != 'detected' else 'detected on this machine'})",
             f"Stored choice: {configured(root)} ({settings_file(root)})"]
    if platform == "linux":
        lines += ["Buzz kit: integrations/buzz/kit/setup.sh, kit.sh and teardown.sh (bash; Docker Engine, jq, git, curl)"]
    else:
        lines += ["Buzz kit: integrations/buzz/kit/setup.ps1, kit.ps1 and teardown.ps1 (PowerShell 7; Docker Desktop)"]
    if platform != detected():
        lines.append(f"Note: this machine looks like {detected()}; the stored choice wins until you run `set auto`.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="action")
    sub.add_parser("show", help="show the platform in use (the default)")
    chosen = sub.add_parser("set", help="store the platform for this checkout")
    chosen.add_argument("platform", choices=CHOICES)
    kit = sub.add_parser("kit", help="run a Buzz kit script for the platform")
    kit.add_argument("script", choices=KIT_SCRIPTS)
    kit.add_argument("args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.action == "set":
            print(f"Stored {args.platform} in {save(args.platform)}")
            print(describe())
            return 0
        if args.action == "kit":
            command = kit_command(resolve()[0], args.script, args.args)
            if not shutil.which(command[0]):
                print(f"{command[0]} is not installed; it runs the {resolve()[0]} kit scripts", file=sys.stderr)
                return 127
            return subprocess.run(command, cwd=KIT).returncode
        print(describe())
        return 0
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
