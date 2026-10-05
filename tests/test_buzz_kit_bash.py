"""The Linux kit (kit.sh, setup.sh, teardown.sh): the same checks test_buzz runs against kit.ps1, in bash with Docker
mocked, plus parity with kit.ps1's pins and team so the two platforms cannot drift apart."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "integrations" / "buzz" / "kit"
OWNER = "o" * 64
HAVE_BASH = bool(shutil.which("bash") and shutil.which("jq")) and os.name != "nt"
# A settings fixture shared by the run-argument tests (kit.json's shape on both platforms).
SETTINGS = r"""
s=$(jq -nc --arg o "%s" '{port: 3200, owner: $o, image: "img:1", credentialFile: "/secrets/c.env",
  repositories: ["/src/Tinker", "/work/sample-app"], channels: {reviews: "c2", zeta: "c3", requests: "c1"},
  agents: {flow: ("f" * 64)}}')
for r in "${AGENT_ROLES[@]}"; do s=$(jq -c --arg r "$r" '.agents[$r] = ($r + ("x" * (64 - ($r | length))))' <<<"$s"); done
""" % OWNER


@unittest.skipUnless(HAVE_BASH, "bash and jq unavailable")
class BashKitTests(unittest.TestCase):
    def bash(self, script, stdin="", check=True):
        """Source kit.sh (project t, a temporary state root) in bash, run the script, return (stdout, stderr)."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.state = folder.name
        probe = Path(folder.name) / "probe.sh"
        probe.write_text(f". '{KIT / 'kit.sh'}' --project t --state-root '{folder.name}' || exit 9\n{script}\n",
                         encoding="utf-8")
        out = subprocess.run(["bash", str(probe)], input=stdin, capture_output=True, text=True, timeout=120,
                             env={**os.environ, "HOME": folder.name})
        if check:
            self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout, out.stderr

    def json(self, script, **kw):
        return json.loads(self.bash(script, **kw)[0])

    def test_scripts_parse_and_are_executable(self):
        for name in ("kit.sh", "setup.sh", "teardown.sh"):
            with self.subTest(script=name):
                path = KIT / name
                self.assertEqual(subprocess.run(["bash", "-n", str(path)], capture_output=True).returncode, 0)
                self.assertTrue(os.access(path, os.X_OK), f"{name} is not executable")
                self.assertTrue(path.read_text(encoding="utf-8").startswith("#!/usr/bin/env bash\n"))

    def test_each_agent_has_its_own_key_and_the_specialists_mount_read_only(self):
        runs = self.json(SETTINGS + r"""
out='{}'
for r in "${AGENT_ROLES[@]}"; do Get-AgentRunArgs "$r" "$s"; out=$(jq -c --arg r "$r" --argjson a "$(json_array "${RUN_ARGS[@]}")" '.[$r] = $a' <<<"$out"); done
Get-AgentRunArgs lead "$(jq -c 'del(.repositories)' <<<"$s")"
jq -c --argjson a "$(json_array "${RUN_ARGS[@]}")" '.["no-repository"] = $a' <<<"$out" """)
        self.assertEqual(list(runs), ["lead", "planner", "tester", "reviewer", "researcher", "no-repository"])
        writers = {"lead", "tester"}  # everyone else reads /work
        for role, argv in runs.items():
            def after(flag, argv=argv):
                return [argv[i + 1] for i, a in enumerate(argv) if a == flag]
            volumes, env = after("-v"), after("-e")
            with self.subTest(role=role):
                role = "lead" if role == "no-repository" else role
                self.assertEqual(argv[:2], ["-d", "--init"])
                self.assertEqual(after("--name"), [f"t-{role}"])
                self.assertEqual([v for v in volumes if "/agentkey" in v], [f"t-{role}-key:/agentkey:ro"])
                self.assertIn("t-work:/work" + ("" if role in writers else ":ro"), volumes)
                self.assertEqual(argv[-3:], ["img:1", "bash", "/kit/agent.sh"])
                self.assertEqual(after("-w"), ["/home/agent/chat"])  # sessions start in a private folder
                self.assertEqual(after("--cap-drop"), ["ALL"])
                self.assertEqual(after("--security-opt"), ["no-new-privileges:true"])
                self.assertEqual(after("--env-file"), ["/secrets/c.env", str(KIT / "agent.env")])
                for setting in (f"KIT_ROLE={role}", f"BUZZ_ACP_SYSTEM_PROMPT_FILE=/kit/prompts/{role}.md",
                                "BUZZ_ACP_AGENT_OWNER=" + OWNER, "BUZZ_RELAY_URL=ws://localhost:3200"):
                    self.assertIn(setting, env)
                value = {e.split("=", 1)[0]: e.split("=", 1)[1] for e in env}
                self.assertEqual(value["KIT_CHANNELS"], "c1,c2,c3")  # sorted: a stable settings hash
                self.assertNotIn("BUZZ_ACP_CHANNELS", value)
                home = {"lead": "c1", "reviewer": "c2"}.get(role, "")  # #requests, #reviews; the others are absent
                self.assertEqual(value["KIT_HOME_CHANNEL"], home)
                self.assertEqual("without a mention" in value["BUZZ_ACP_TEAM_INSTRUCTIONS"], bool(home))
                self.assertIn(OWNER, value["BUZZ_ACP_TEAM_INSTRUCTIONS"])
                self.assertEqual(value["BUZZ_ACP_RESPOND_TO_ALLOWLIST"], "f" * 64)
                self.assertIn("f" * 64, value["BUZZ_ACP_TEAM_INSTRUCTIONS"])
        for role in ("lead", "planner", "tester", "reviewer", "researcher"):
            volumes = [runs[role][i + 1] for i, a in enumerate(runs[role]) if a == "-v"]
            self.assertIn("/src/Tinker:/repos/Tinker:ro", volumes)
            self.assertIn("/work/sample-app:/repos/sample-app:ro", volumes)
            self.assertEqual([v for v in volumes if "/repos/" in v and not v.endswith(":ro")], [])  # never writable
            team = next(e for e in runs[role] if e.startswith("BUZZ_ACP_TEAM_INSTRUCTIONS="))
            self.assertIn("Read-only repositories: /repos/Tinker, /repos/sample-app.", team)
        self.assertFalse([a for a in runs["no-repository"] if "/repos/" in a])

    def test_tinker_flow_runs_without_a_model_credential_or_files(self):
        argv = self.json(SETTINGS + r"""
s=$(jq -c '.channels = {requests: "c1", flows: "c9"}' <<<"$s")
Get-FlowRunArgs "$s"; json_array "${RUN_ARGS[@]}" """)

        def after(flag):
            return [argv[i + 1] for i, a in enumerate(argv) if a == flag]
        self.assertEqual(after("--name"), ["t-flow"])
        self.assertEqual(after("-v"), ["t-flow-key:/agentkey:ro"])  # its key only: no /work, no repositories
        self.assertEqual(after("--env-file"), [])  # no Claude credential: Tinker Flow runs no model
        self.assertEqual(argv[-3:], ["img:1", "bash", "/kit/flow.sh"])
        self.assertEqual(after("--cap-drop"), ["ALL"])
        env = dict(e.split("=", 1) for e in after("-e"))
        self.assertEqual(env["PYTHONUNBUFFERED"], "1")
        self.assertEqual((env["FLOW_OWNER"], env["FLOW_SELF"]), (OWNER, "f" * 64))
        self.assertEqual(env["FLOW_CHANNELS"], "c1,c9")
        self.assertEqual(env["FLOW_HOME"], "c9")
        agents = json.loads(env["FLOW_AGENTS"])
        self.assertEqual(list(agents), ["lead", "planner", "tester", "reviewer", "researcher"])
        self.assertEqual(agents["planner"], {"name": "Tinker Planner", "hex": "planner".ljust(64, "x")})

    def test_the_startup_check_catches_colored_error_lines(self):
        # buzz-acp colors its log; the check strips the codes before it reads ERROR lines.
        result = self.json(r"""
OWNER=@OWNER@; KIT_STARTUP_SECONDS=5
Save-KitState "$(jq -nc --arg o "$OWNER" '{port: 3200, owner: $o, channels: {requests: "c1"}, repositories: ["/src/r"]}')"
sleep() { :; }
docker() {
  local e=$'\e' m err deny
  err="$e[2m2026-09-28T19:08:00Z$e[0m $e[31mERROR$e[0m $e[2mpool::prompt$e[0m$e[2m:$e[0m failed"
  case $1 in
    logs)
      [[ $CASE_ERROR == startup ]] && echo "$err"
      for m in "buzz-acp starting: relay=ws://localhost:3200 agents=1 subscribe=${CASE_SUBSCRIBE:-Config} dedup=Queue" \
               'agent initialized' 'connected to relay at ws://localhost:3200' "agent owner: $OWNER" \
               ${CASE_RULES:+"rule 'home': invalid filter expression: unexpected end"} 'subscribed to channel c1'; do
        echo "$e[2m2026-09-28T19:07:58Z$e[0m $e[32m INFO$e[0m $e[2mbuzz_acp$e[0m$e[2m:$e[0m $m"
      done
      [[ $CASE_ERROR == later ]] && echo "$err" ;;   # a failed turn long after startup
    ps) echo abc123 ;;
    exec)
      case ${@: -1} in
        /proc/mounts) echo "v /work ext4 $CASE_WORK,relatime 0 0"; echo "g /repos/r fuse $CASE_REPO,relatime 0 0" ;;
        /home/agent/buzz-acp.toml) printf '%s\n' '[[rules]]' 'name = "mention"' '[[rules]]' 'name = "home"' \
          "channels = [\"${CASE_HOME:-c1}\"]" "filter = 'author == \"$OWNER\" && !(str_starts_with(content, \"@\"))'" ;;
        *) read -r -a deny <<<"$CASE_DENY"; jq -nc --argjson d "$(json_array "${deny[@]}")" '{permissions: {deny: $d}}' ;;
      esac ;;
  esac
}
writer='Bash(curl:*)'; readonly_deny='Bash(curl:*) Write Edit'   # the deny rules each case reports
results='{}'
run() {   # run <name> <role> CASE_X=value...: one case; Test-AgentStartup fails in its own subshell
  local name=$1 role=$2 kv msg; shift 2
  CASE_ERROR= CASE_SUBSCRIBE= CASE_RULES= CASE_HOME=
  for kv; do printf -v "${kv%%=*}" '%s' "${kv#*=}"; done
  if msg=$(Test-AgentStartup "$role" 2>&1 >/dev/null); then msg=passed; fi
  results=$(jq -c --arg n "$name" --arg m "$msg" '.[$n] = $m' <<<"$results")
}
run startup-error lead CASE_ERROR=startup CASE_WORK=rw CASE_REPO=ro CASE_DENY="$writer"
run later-error lead CASE_ERROR=later CASE_WORK=rw CASE_REPO=ro CASE_DENY="$writer"
run clean lead CASE_WORK=rw CASE_REPO=ro CASE_DENY="$writer"
run lead-without-web lead CASE_WORK=rw CASE_REPO=ro CASE_DENY=WebFetch
run repository-writable lead CASE_WORK=rw CASE_REPO=rw CASE_DENY="$writer"
run reviewer-writable-work reviewer CASE_WORK=rw CASE_REPO=ro CASE_DENY="$readonly_deny"
run reviewer-clean reviewer CASE_WORK=ro CASE_REPO=ro CASE_DENY="$readonly_deny"
run researcher-may-edit researcher CASE_WORK=ro CASE_REPO=ro CASE_DENY="$writer"
run mentions-only lead CASE_WORK=rw CASE_REPO=ro CASE_DENY="$writer" CASE_SUBSCRIBE=Mentions
run bad-rule lead CASE_WORK=rw CASE_REPO=ro CASE_DENY="$writer" CASE_RULES=bad
run wrong-home lead CASE_WORK=rw CASE_REPO=ro CASE_DENY="$writer" CASE_HOME=c9
echo "$results" """.replace("@OWNER@", OWNER))
        self.assertTrue(result["startup-error"].startswith("Error: Not started cleanly: t-lead"), result["startup-error"])
        for passing in ("later-error", "clean", "reviewer-clean"):  # a later failed turn is not a startup failure
            self.assertEqual(result[passing], "passed", passing)
        for failing, agent in (("reviewer-writable-work", "t-reviewer"), ("researcher-may-edit", "t-researcher"),
                               ("lead-without-web", "t-lead"), ("repository-writable", "t-lead"),
                               ("mentions-only", "t-lead"), ("bad-rule", "t-lead"), ("wrong-home", "t-lead")):
            self.assertTrue(result[failing].startswith(f"Error: Not started cleanly: {agent}"), (failing, result[failing]))

    def test_role_names_are_case_insensitive_everywhere(self):
        out, _ = self.bash(r"""
calls="$STATE_ROOT/calls"
docker() { printf '%s\n' "$*" >> "$calls"; }
Stop-Agent Reviewer TESTER >/dev/null
cat "$calls" """)
        calls = out.splitlines()
        self.assertTrue(calls and all(("t-reviewer" in c or "t-tester" in c) for c in calls), calls)
        self.assertFalse([c for c in calls if "Reviewer" in c or "TESTER" in c])

    def test_copy_agent_work_takes_one_folder_under_work_through_a_read_only_mount(self):
        result = self.json(r"""
Save-KitState '{"image": "img:1"}'
calls="$STATE_ROOT/calls"; : > "$calls"
docker() { printf '%s\n' "$*" >> "$calls"; [[ $1 == create ]] && echo c0ffee; return 0; }
result='{}'
for f in .. . a/b 'a\b' ../x; do
  if Copy-AgentWork "$f" /dest >/dev/null 2>&1; then v=copied; else v=refused; fi
  result=$(jq -c --arg f "$f" --arg v "$v" '.[$f] = $v' <<<"$result")
done
result=$(jq -c --rawfile c "$calls" '.refusedCalls = ($c | split("\n") | map(select(. != "")))' <<<"$result"); : > "$calls"
ok=$(Copy-AgentWork docs-typos /dest)
jq -c --arg ok "$ok" --rawfile c "$calls" '.ok = $ok | .calls = ($c | split("\n") | map(select(. != "")))' <<<"$result" """)
        for folder in ("..", ".", "a/b", r"a\b", "../x"):
            self.assertEqual(result[folder], "refused", folder)
        self.assertEqual(result["refusedCalls"], [])
        calls = result["calls"]
        self.assertTrue(calls[0].startswith("create ") and "t-work:/work:ro" in calls[0], calls)
        self.assertIn("cp c0ffee:/work/docs-typos /dest", calls)
        self.assertEqual(calls[-1], "rm -f c0ffee")
        self.assertEqual(result["ok"], "Copied /work/docs-typos to /dest/docs-typos")

    def test_the_wizard_asks_until_each_answer_is_valid(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        repo, worktree = Path(folder.name) / "Repo", Path(folder.name) / "Wt"
        (repo / ".git").mkdir(parents=True)
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: /elsewhere", encoding="utf-8")
        credential = Path(folder.name) / "claude.env"
        credential.write_text("", encoding="utf-8")  # the wizard only checks that the file exists
        answers = ["Bad Name!", "team-buzz", "80", "3300", str(worktree), str(repo), str(credential), "y"]
        out, err = self.bash(r"""
Test-PortFree() { return 0; }
Read-SetupAnswers || exit 3
read -r rest && exit 4   # every answer was read: no question was skipped or asked twice too often
jq -nc --arg p "$ANSWER_PROJECT" --argjson n "$ANSWER_PORT" --arg c "$ANSWER_CREDENTIAL_FILE" \
  --argjson r "$(json_array "${ANSWER_REPOSITORY[@]}")" '{Project: $p, Port: $n, CredentialFile: $c, Repository: $r}' """,
                             stdin="\n".join(answers) + "\n")
        a = json.loads(out)
        self.assertEqual((a["Project"], a["Port"]), ("team-buzz", 3300))
        self.assertEqual(a["Repository"], [str(repo.resolve())])
        self.assertEqual(a["CredentialFile"], str(credential))
        self.assertEqual(err.count("Use lowercase letters"), 1)
        self.assertEqual(err.count("Use a free port"), 1)
        self.assertEqual(err.count("main clone, not a git worktree"), 1)
        out, _ = self.bash("Test-PortFree() { return 0; }\nRead-SetupAnswers && exit 5 || echo declined",
                           stdin="\n".join(answers[1:2] + answers[3:4] + ["", str(credential), "n"]) + "\n")
        self.assertEqual(out.strip(), "declined")  # setup.sh then changes nothing

    def test_npub_and_the_command_line(self):
        out, _ = self.bash("ConvertTo-Npub " + "7e7e9c42a91bfef19fa929e5fda1b72e0ebc1a4c1141673e2794234d86addf4e")
        self.assertEqual(out.strip(), "npub10elfcs4fr0l0r8af98jlmgdh9c8tcxjvz9qkw038js35mp4dma8qzvjptg")
        run = subprocess.run(["bash", str(KIT / "kit.sh"), "NPUB", "7e" * 32], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(run.stdout.startswith("npub1"))
        for argv in (["--project", "Bad!", "status"], ["no-such-command"]):
            with self.subTest(argv=argv):
                run = subprocess.run(["bash", str(KIT / "kit.sh"), *argv], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
        # A failing command ends itself, never the shell that sourced kit.sh.
        out, _ = self.bash("Copy-AgentWork ../x 2>/dev/null; echo \"alive $?\"")
        self.assertEqual(out.strip(), "alive 1")

    def test_setup_refuses_bad_arguments_before_touching_docker(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        worktree = Path(folder.name) / "wt"
        worktree.mkdir()
        (worktree / ".git").write_text("gitdir: /elsewhere", encoding="utf-8")
        for args, message in ((["--port", "80"], "Port must be"), (["--owner-npub", "nope"], "Not an npub"),
                              (["--repository", str(worktree)], "git worktree cannot be mounted"),
                              (["--repository", str(Path(folder.name) / "missing")], "Repository folder not found"),
                              (["--bogus", "x"], "Unknown option")):
            with self.subTest(args=args):
                run = subprocess.run(["bash", str(KIT / "setup.sh"), "--state-root", folder.name, *args],
                                     capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                     env={**os.environ, "PATH": "/usr/bin:/bin"})
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(message, run.stderr)


@unittest.skipUnless(HAVE_BASH, "bash and jq unavailable")
class KitParityTests(unittest.TestCase):
    """kit.sh and kit.ps1 share pins, the team and the channels; a change to one must reach the other."""

    def ps(self):
        return (KIT / "kit.ps1").read_text(encoding="utf-8")

    def sh(self, script):
        out = subprocess.run(["bash", "-c", f". '{KIT / 'kit.sh'}' --project t --state-root /nonexistent >/dev/null\n{script}"],
                             capture_output=True, text=True, check=True)
        return out.stdout

    def test_pins_match(self):
        ps = self.ps()
        scalar = {key: re.search(rf"\b{key}\s*=\s*'([^']+)'", ps).group(1)
                  for key in ("BuzzCommit", "ComposeSha256", "RelayImage", "RelayRevision", "TinkerCommit", "ArchifyCommit")}
        cargo = re.findall(r"'(git\+[^']+)'", ps)
        binaries = dict(re.findall(r"'(buzz(?:-acp)?)'\s*=\s*'([0-9a-f]{64})'", ps))
        sh = json.loads(self.sh(r"""jq -n --arg BuzzCommit "$PIN_BUZZ_COMMIT" --arg ComposeSha256 "$PIN_COMPOSE_SHA256" \
          --arg RelayImage "$PIN_RELAY_IMAGE" --arg RelayRevision "$PIN_RELAY_REVISION" --arg TinkerCommit "$PIN_TINKER_COMMIT" \
          --arg ArchifyCommit "$PIN_ARCHIFY_COMMIT" --arg acp "${PIN_BINARIES[buzz-acp]}" --arg buzz "${PIN_BINARIES[buzz]}" \
          '{scalar: {$BuzzCommit, $ComposeSha256, $RelayImage, $RelayRevision, $TinkerCommit, $ArchifyCommit},
            binaries: {"buzz-acp": $acp, buzz: $buzz}, cargo: $cargo}' --argjson cargo "$(json_array "${PIN_CARGO_GIT[@]}")" """))
        self.assertEqual(sh["scalar"], scalar)
        self.assertEqual(sh["cargo"], cargo)
        self.assertEqual(sh["binaries"], binaries)

    def test_team_and_channels_match(self):
        ps = self.ps()
        agents = {m.group(1): {"name": m.group(2), "writes": m.group(3) == "true", "web": m.group(4) == "true",
                               "home": m.group(5), "about": m.group(7)}
                  for m in re.finditer(r"(\w+)\s*=\s*@\{ name = '([^']+)'; writes = \$(true|false); web = \$(true|false); "
                                       r"home = '([\w-]+)'\s*about = ([\"'])(.*?)\6 \}", ps)}
        block = ps[ps.index("$CHANNELS = [ordered]@{"):]
        block = block[:block.index("\n}")]
        channels = dict(re.findall(r"^\s+'?([\w-]+)'?\s*=\s*'(.*)'$", block, re.M))
        flow = re.search(r"\$FLOW = @\{ name = '([^']+)'\s*about = '([^']+)' \}", ps)
        sh = json.loads(self.sh(r"""
a='{}'; for r in "${AGENT_ROLES[@]}"; do
  a=$(jq -c --arg r "$r" --arg n "${AGENT_NAME[$r]}" --argjson w "${AGENT_WRITES[$r]}" --argjson web "${AGENT_WEB[$r]}" \
    --arg h "${AGENT_HOME[$r]}" --arg ab "${AGENT_ABOUT[$r]}" \
    '.[$r] = {name: $n, writes: ($w == 1), web: ($web == 1), home: $h, about: $ab}' <<<"$a"); done
c='{}'; for n in "${CHANNEL_NAMES[@]}"; do c=$(jq -c --arg n "$n" --arg p "${CHANNEL_PURPOSE[$n]}" '.[$n] = $p' <<<"$c"); done
jq -n --argjson a "$a" --argjson c "$c" --arg fn "$FLOW_NAME" --arg fa "$FLOW_ABOUT" '{agents: $a, channels: $c, flow: [$fn, $fa]}' """))
        self.assertEqual(list(agents), ["lead", "planner", "tester", "reviewer", "researcher"])
        self.assertEqual(sh["agents"], agents)
        self.assertEqual(list(sh["agents"]), list(agents))  # the same order: startup checks and status follow it
        self.assertEqual(sh["channels"], channels)
        self.assertEqual(list(sh["channels"]), list(channels))
        self.assertEqual(sh["flow"], list(flow.groups()))

    def test_every_powershell_command_has_a_bash_twin(self):
        ps_functions = set(re.findall(r"^function ([A-Z]\w+-\w+)", self.ps(), re.M))
        sh = (KIT / "kit.sh").read_text(encoding="utf-8")
        sh_functions = set(re.findall(r"^([A-Z]\w+-\w+)\(\)", sh, re.M))
        self.assertTrue(ps_functions)
        self.assertEqual(ps_functions - sh_functions, set())
        setup_ps = (KIT / "setup.ps1").read_text(encoding="utf-8")
        setup_sh = (KIT / "setup.sh").read_text(encoding="utf-8")
        steps = lambda text: re.findall(r"^Step [\"'](.+?)[\"']$", text, re.M)  # noqa: E731
        normalize = lambda s: s.replace("buildx, ", "")  # noqa: E731  (the Linux preflight also checks buildx)
        self.assertEqual([normalize(s) for s in steps(setup_sh)], steps(setup_ps))


if __name__ == "__main__":
    unittest.main()
