# Tinker's team in Buzz on your own PC (Windows or Linux)

This kit sets up a private Buzz relay on your PC and runs Tinker's team as five Buzz agents that answer
only you: **Tinker** (the Lead), **Tinker Planner**, **Tinker Tester**, **Tinker Reviewer** and **Tinker
Researcher**, plus **Tinker Flow**, which runs a whole flow across them from one message and has no AI of its
own. You chat with them from Buzz Desktop in seven channels whose canvases show how to work with each one;
[EXAMPLES.md](EXAMPLES.md) has worked examples. One command sets it all up (section 4). Everything runs in Docker
on your machine; nothing is published beyond `127.0.0.1`. The
relay and the agents' safety settings match the lab setup the kit was built from (see the
[integration README](../README.md) and the [Buzz protocol](../protocol.md) every agent follows).

This optional kit uses Claude Code for its container agents. Tinker's main Claude Code,
Codex and Antigravity entry points work independently of the kit.

**Windows or Linux.** The kit has two equivalent sets of scripts: PowerShell 7 for Windows (`setup.ps1`, `kit.ps1`,
`teardown.ps1`) and bash for Debian and other Linux hosts (`setup.sh`, `kit.sh`, `teardown.sh`). They share the
pins, the team, the agent image and every check. This guide shows the Windows commands; on Linux read
[section 15](#15-linux-debian) first, which lists the prerequisites, the token and Desktop steps, and the bash form
of every command. `python scripts/tinker_platform.py kit setup ...` runs whichever set this checkout is configured
for ([README](../../../README.md#windows-or-linux)).

## 1. Prerequisites

- Windows 10 or 11 with **Docker Desktop** running **Linux containers** (Compose 2.24.4 or newer is included).
- **PowerShell 7** (`pwsh`) and **Git for Windows**.
- On Linux instead: Docker Engine with Compose 2.24.4+ and buildx, bash, git, jq and curl (section 15).
- **Claude Code**, only to create your token (section 3).
- About **9 GB** of free disk space: sources, build caches, the agent image (3.1 GB) and base images.
- About **10-30 minutes** for the first setup: about 4.9 GB of images to download, then the Rust build (97 s on
  the PC the kit was tested on). Later runs take under a minute.

## 2. Get Tinker at the kit's commit

```powershell
git clone <Tinker repository URL> Tinker
git -C Tinker checkout master             # or the exact commit you were given
```

The agent image installs Tinker at the commit the kit pins (`-TinkerCommit`, default in [kit.ps1](kit.ps1)), taken
with `git archive` from this clone, so your working tree's own changes never reach the image.

## 3. Your own Claude token

The agents use **your** Claude subscription through a long-lived token from `claude setup-token`. You create it
and store it yourself; setup only passes the file's path to Docker and never reads it. All the agents share it.

1. Open a **new PowerShell window of your own**: never an agent's shell or a terminal panel an agent can read.
2. Run `claude setup-token` and approve in the browser with the account you intend to use. It prints the token once.
3. Copy the **whole** token (it may wrap over several lines), then save it without pasting it at any prompt:

   ```powershell
   Read-Host 'Copied the whole token? Press Enter' | Out-Null
   $t = (Get-Clipboard -Raw) -replace '\s', ''
   if ($t -notmatch '^[A-Za-z0-9_-]{80,}$') { Remove-Variable t; Set-Clipboard -Value ' '; throw 'Copy the whole token again' }
   New-Item -ItemType Directory -Force "$HOME\tinker-buzz-secrets" | Out-Null
   [IO.File]::WriteAllText("$HOME\tinker-buzz-secrets\claude.env", "CLAUDE_CODE_OAUTH_TOKEN=$t`n")
   Remove-Variable t; Set-Clipboard -Value ' '; Clear-Host
   ```

4. If Windows clipboard history (Win+V) is on, delete the token's entry there. Close the window.

Rules: never paste the token into a chat, a prompt, a file inside the repository or your shell profile, and never
set it in your Windows environment. The file must hold exactly one line.

**Fallback: an API key.** If you or your company prefer API billing, put `ANTHROPIC_API_KEY=<key>` in that file
instead (never both). Use a key you can revoke, ideally in a workspace with a spend limit.

**Terms and policy.** Using your own subscription in Claude Code, including `setup-token` for scripts, is
documented by Anthropic ([authentication](https://code.claude.com/docs/en/authentication)). Sharing your
credentials, or letting other people drive your account, is prohibited
([Consumer Terms](https://www.anthropic.com/legal/consumer-terms)); the kit's owner-only gate means only you can
drive these agents. Whether a relay-triggered agent on a personal plan counts as permitted automated use is not
spelled out. If your login is a company Team or Enterprise seat, your company's policy and admin settings apply:
ask first. When in doubt, use the API-key fallback. Agent turns count against the same usage limits as your own
Claude use.

## 4. Run the setup wizard

Install Buzz Desktop first (section 5). Then, from `Tinker\integrations\buzz\kit` in PowerShell 7:

```powershell
.\setup.ps1
```

With no parameters, setup is a wizard. It asks four things, each again until the answer is valid:

1. A project name (`tinker-buzz`).
2. A free port (it suggests one).
3. The repositories the agents may read. These are comma-separated main clones, not git worktrees.
4. Your token file from section 3.

It then builds and starts everything. When the relay is up it tells you to add the community in Buzz Desktop,
and waits for the npub Desktop shows you (section 6). Answer, and it adds you and starts the team.

For unattended or scripted runs, pass parameters instead; the wizard is skipped:

- `-Repository C:\src\app, C:\src\lib`: folders every agent reads at `/repos/<folder name>`, **mounted
  read-only**. They are kept for later runs; `-Repository ''` removes them. Every agent can read everything in
  them, including `.git` and untracked files. Pass main clones: a git worktree's `.git` file points to a Windows
  path that git inside Linux cannot follow.
- `-OwnerNpub <npub>` and `-CredentialFile <path>`: without both, setup stops before starting the agents.
- `-Port 3100` if 3000 is taken; `-Project <name>` for a second, separate setup.
- `-StateRoot <folder>` to keep setup's state somewhere other than `%LOCALAPPDATA%\TinkerBuzz` (pass it to
  `kit.ps1` and `teardown.ps1` too).

Setup is idempotent: after an error, fix the cause and run it again. It never regenerates keys over an existing
relay, and it restarts an agent only when that agent's settings changed.

What it does, in order: preflight; pulls the relay image by digest; one `docker build` that fetches Buzz `781d395`,
builds `buzz-acp` and `buzz` (its three Cargo Git dependencies locked), fetches archify `2ab3cae` (the diagram
skill, section 9), and builds the agent image with Tinker installed in the image only, all from pinned base images
and `claude-agent-acp` 0.81.2; verifies those pins, the compose file's SHA-256, each role's prompt and archify
(root-owned files, no update checks, its full gate passing in Chromium with no network); generates the admin key, one key per agent and Tinker Flow's key
and the relay secrets inside containers; starts the relay on `127.0.0.1:<port>`; checks the bootstrap and
routing; adds members; sets each profile; creates the channels with a purpose and a canvas; starts the agents
and Tinker Flow and checks their startup, subscription rules, deny rules and mounts; scans the kit folder and the setup logs for
secrets. The only folders from your PC a container mounts are the `-Repository` folders, read-only; everything
else goes in and out through `docker build` and `docker cp`. Setup's own state (logs, relay secrets, `kit.json`) lives in `%LOCALAPPDATA%\TinkerBuzz\<project>`,
never in the repository.

## 5. Buzz Desktop 0.5.25

Download `Buzz_0.5.25_x64-setup_alpha-unsigned.exe` from the
[desktop-v0.5.25 release](https://github.com/block/buzz/releases/tag/desktop-v0.5.25) and check it before running:

```powershell
$f = "$HOME\Downloads\Buzz_0.5.25_x64-setup_alpha-unsigned.exe"
(Get-FileHash $f).Hash -eq 'FFF84C9048ACBB0592D873F6CC8C8CD9816C43A753042407BFA47B452C2BDA43' -and (Get-Item $f).Length -eq 55559951
```

It must print `True`. The installer is **unsigned**, so Windows warns about it and your company's policy decides
whether you may install it. Launch it from the Start menu, not from a terminal.

## 6. Onboarding

1. On **Connect your AI provider**, choose **Set up later**. Never click Install or Connect for Claude or Codex: the
   kit brings its own agents, and a Desktop-managed one would run without Tinker's protections.
2. When the wizard says so, choose **Add Community** and enter exactly `ws://localhost:3000` (or your port). A
   bare host becomes `wss://`.
3. You will see **Not a member yet** with your npub. Copy it and paste it into the wizard: it adds you to the
   relay and the channels and starts the team with you as their owner. Then press **Try again**. (Without the
   wizard: `.\setup.ps1 -OwnerNpub <your npub> -CredentialFile "$HOME\tinker-buzz-secrets\claude.env"`, repeating
   any `-Port`, `-Project` or `-StateRoot` you used.)
4. Leave the **Welcome** channel at once when it opens.
5. Never start, add or @mention **Fizz**, **Honey** or **Pollen** (Desktop's built-in agents). They would share your
   identity as their owner, and agents with the same owner pass each other's owner-only gate.

## 7. First chat

Open `#tinker-lab`: its canvas lists the team. Mention an agent by its name in the mention picker (setup also
prints each npub, and so does `Get-KitStatus`). Try `@Tinker Read-only: what can you do here, and what are your
limits?` The agent answers in the thread. In each agent's own channel no mention is needed: just write in
#requests for Tinker, or in #planning, #testing, #reviews or #research. Then try a whole flow in #flows, where you
just write too: `help`. In the mention picker, turn on **Automatically mention agents** so your replies in a
thread keep the agent you mentioned addressed. Read [EXAMPLES.md](EXAMPLES.md) and the canvases of #requests,
#flows, #planning, #testing, #reviews and #research.

## 8. What to expect

| Agent | Home channel | `/work` | Does |
|---|---|---|---|
| **Tinker** (the Lead) | #requests | writes its own clones | explains, plans and changes code, runs the tests |
| **Tinker Planner** | #planning | read-only | shapes ideas: outcome, scope, acceptance criteria |
| **Tinker Tester** | #testing | writes its own `test-<topic>` copies | writes and runs tests, reports counts and gaps |
| **Tinker Reviewer** | #reviews | read-only | reviews a branch, commit or folder with `file:line` |
| **Tinker Researcher** | #research | read-only | answers from the code and the web, with sources |
| **Tinker Flow** | #flows | none | runs a whole flow across the agents; no AI of its own |

- Every agent reads the repositories under `/repos` (read-only for all) and may use the web (WebSearch and
  WebFetch). The read-only agents also have their edit tools denied. `curl`, `wget`, `env` and `printenv` are
  denied for all of them. These denies stop tools, not the network or the shell: Bash can still reach the
  internet, and every agent can write its own home folder. The hard write barriers are the read-only mounts.
- Every agent uses the kit's short Buzz base prompt instead of Buzz's 17.7 KB default, and runs without Claude
  Code's commit instructions and auto memory: fewer tokens per session and no instructions that contradict
  Tinker. `Get-KitUsage` shows what each agent used (section 10).
- Each chat session starts in the agent's own folder, never in `/work`, so files one agent writes there are not
  loaded as another agent's settings or instructions.
- All of them run **unattended**: commits, pushes, branch deletions, remote changes and Buzz workspace changes
  are denied, and Buzz messages (including your "I approve") never authorize them. They post the exact command
  so you can run it yourself.
- Each answers only your messages (and the steps of your flows, below): wherever you mention it, and whatever you
  write in its home channel without a mention, unless the message mentions another agent. Everything else it
  sees is data, including the other agents. It replies in the thread. Agents never hand work to each other on
  their own: you pick who is next, or a flow does. Agents in different threads work at the same time.
- One Buzz session writes a checkout at a time; another thread may be told `workspace.owned`.
- To take work out of `/work`, copy the folder to your PC with `Copy-AgentWork` (section 10).

## 9. Flows: the whole team from one message

`story <request>` in #flows (no mention needed there; in any other kit channel, `@Tinker Flow story <request>`,
and answer it by name there too, `@Tinker Flow go` or `@Tinker Flow stop`, since an untagged reply goes to that
channel's agent) runs Planner, Tinker, Tester and Reviewer in order, in one thread under your message. A request that starts with no
flow's name gets a suggestion: Tinker Flow guesses the flow from your words and waits for you to reply `go`, or
another flow's name, in the thread, so a wrong guess costs nothing. Tinker Flow posts each step with a mention of
one agent and hands it only your request and the earlier reports it needs, quoted as data, with every `@` made
inert so a quote cannot trigger another agent. A step ends when the agent has replied and Buzz's seen and working
reactions on the step are gone. Then a ✅ line gives the time and the folder to copy out. The flows are `story`,
`bug`, `review` and `research` (`scripts/flows.json`; `help` lists them), and replying `stop` in a flow's thread
stops it.

Tinker Flow has no model and no Claude credential: orchestration costs no tokens. It obeys only you, runs one flow
at a time, and cannot loop, since every flow has a fixed list of steps. The agents accept its steps through
buzz-acp's allowlist (`BUZZ_ACP_RESPOND_TO=allowlist`, which always includes you, plus Tinker Flow's key only). A
step that fails, times out or is never picked up stops the flow with a ⏹️ line.

**Diagrams.** Every agent has [archify](https://github.com/tt-a1i/archify) (MIT) 3.0.1 as a user skill, pinned
to commit `2ab3cae`, its files owned by root in the image and its update checks off. It turns typed JSON into a
checked, self-contained HTML diagram: architecture, workflow, sequence, data flow or lifecycle. Ask Tinker (or
Tinker Tester for a test's view) for one. It draws in `/work/diagram-<topic>` and ends with archify's `finalize`:
validation (for a diagram of code under `/repos`, every cited source is checked against the committed code at the
revision it pins), a provenance check that the HTML is exactly what was validated, and a check in Chromium. A
diagram of uncommitted work cites no sources, and the reply says so. Copy the folder out with `Copy-AgentWork` and
open its `.html` file in your browser. The read-only agents write no files, so they give the facts and send you
to Tinker. An agent draws only when you ask; the skill's one-paragraph description is in every session's prompt,
and the rest loads only when a diagram is drawn.

## 10. Stop, start and usage

```powershell
. .\kit.ps1 -Project tinker-buzz      # in PowerShell 7, from the kit folder (add -StateRoot if you used one)
Get-KitStatus                         # containers, npubs, channels, each agent's log summary and run outcomes
Get-KitUsage                          # tokens per agent since it started: input, cache reads and writes, output
Stop-Agent                            # stops and removes every agent, and verifies they are gone
Start-Agent                           # starts them again with the saved owner, channels and credential file
Stop-Agent tester; Start-Agent tester # one agent: lead, planner, tester, reviewer or researcher
Stop-Flow; Start-Flow                 # Tinker Flow
Copy-AgentWork docs-typos "$HOME\Downloads"   # copies /work/docs-typos to your PC, agents running or not
```

The relay comes back with Docker Desktop on its own. The agents do not: after a reboot, run `Start-Agent` and
`Start-Flow` (or setup again). When a new kit version adds an agent, run setup again: it creates only the new
agent's key and keeps every other one. `Get-KitUsage` reads each agent's own session transcripts, so it counts
since that agent last started; a high cache share means the prompts are being reused, which is what keeps turns
cheap.

## 11. Troubleshooting

- **`NIP-AM: publish failed ... 403` in an agent's log every turn.** Expected: the relay has no owner record for
  the agents yet (section 14). Replies are unaffected.
- **An agent shows as an npub instead of its name.** Its profile did not reach Desktop yet: run setup again (it
  republishes the profiles), then reopen the channel.
- **No reply in the thread.** Run `Get-KitStatus`: *Latest unattended run outcomes* under each agent shows each
  run's final message, which Buzz never posts. Ask again in the thread.
- **An untagged message got no answer.** Only an agent's own channel and #flows take messages without a mention;
  in #tinker-lab or any other channel, mention the agent. Even there, the channel's agent (Tinker Flow, in #flows)
  skips a message that starts with `@` or `!` or has `@Tinker` in it: such a message reaches only the agents you
  picked in the mention picker, so a name typed or pasted as `@Tinker ...` without the picker reaches nobody. In an
  agent's own channel every other message of yours goes to that agent, replies in a flow's thread included, so
  run flows in #flows.
- **Refused with `workspace.owned`, or the Lead made its own worktree.** A session that already ran a command in
  a checkout holds it for up to a day. `Stop-Agent lead; Start-Agent lead` clears it.
- **Port in use.** Run setup with `-Port 3100` and add `ws://localhost:3100` in Desktop. A project keeps its port:
  to change it, run `teardown.ps1` and delete its volumes first.
- **"Not started cleanly".** The line for each agent names the failed check. Read `docker logs <project>-<role>`.
  On an authentication or usage-limit error, fix the token file or wait for the limit, then `Stop-Agent; Start-Agent`.
- **A flow stops with "did not pick the step up".** The agent is not running, or it does not list Tinker Flow on
  its allowlist (an agent started by an older kit): run setup again, then retry the flow.
- **A flow waits a long time on one step.** That agent is still working (its 💬 reaction is on the step). Watch
  its thread, or reply `stop` in the flow's thread (`@Tinker Flow stop` outside #flows); a step gives up after
  an hour.
- **Never name a PowerShell variable `$lead`.** Names are case-insensitive, so it is `$LEAD`, the Lead's container
  name; the kit makes `$LEAD` read-only so such an assignment fails loudly. The same holds for the kit's other
  names: `$agents` is `$AGENTS` and `$flow` is `$FLOW`.

## 12. Cleanup and token revocation

```powershell
.\teardown.ps1                        # stops everything, then asks before deleting volumes
.\teardown.ps1 -Images -StateFolder   # also asks before deleting the agent image and the state folder
```

Teardown never touches the `-Repository` folder. Docker keeps the Rust build cache for later rebuilds;
`docker builder prune` frees it (for every project on the PC). Then delete `$HOME\tinker-buzz-secrets`, and revoke
the token: open [claude.ai/settings/claude-code](https://claude.ai/settings/claude-code) and remove the
authorization created on setup day. If you cannot identify it, log out of all sessions from claude.ai. Otherwise
the token stays valid until it expires after a year. For the API-key fallback, revoke the key in the Anthropic
Console.

## 13. Known risks

- **Only denies protect you.** buzz-acp approves every permission prompt itself; Tinker's hooks, the image's
  deny rules and the read-only mounts are what stop consequential operations.
- **Relayed text reaches the model.** Other members' and agents' messages in a thread are shown to each agent;
  ignoring them is model behavior.
- **Every agent reads the web.** A page can carry instructions aimed at agents. They treat pages as data, but each
  still has your token and its key in its environment, can read `/repos`, and can reach the internet, so an
  injected page could try to make one leak them. The Lead and the Tester can also write `/work`. Ask about
  sources you trust, and mount only repositories you would show them.
- **Tinker Flow is trusted like you, for flow steps.** Its key sits in its own volume and it acts only on your
  messages, but anyone holding that key could post steps the agents accept. Keep the relay local, and delete its
  volume with the others when you stop (`teardown.ps1`).
- **Reports travel between agents in flows.** A later step quotes an earlier agent's report as data, with every
  `@` made inert. If one agent were misled, its report still reaches the next one as quoted text.
- **A writer's folders are not trusted by the others.** The Lead or the Tester could leave a hostile git config or
  instructions in `/work`. The kit forces `core.fsmonitor=false` and `core.hooksPath=/dev/null` for every git
  command, and the Reviewer reads diffs with `--no-ext-diff --no-textconv`; git filter drivers and a `CLAUDE.md`
  inside such a folder are still read if an agent works there.
- **The mounted repositories are fully readable** by every agent: history, untracked files, anything secret
  in it. Mount only what you would show them, never a folder that holds credentials.
- **archify's browser runs without Chromium's sandbox.** The agents have no capabilities and no new privileges,
  so Chromium cannot build one (`ARCHIFY_CHROME_NO_SANDBOX=1`). It opens only the agent's own diagram, as the
  same user that already runs commands in that container; the container is the boundary.
- **An agent can change its own home.** archify's files are root-owned, but each agent owns `~/.claude`: a misled
  agent could swap the skill folder or write `~/.claude/CLAUDE.md`, and its later sessions would read that. Both
  live in the container, not in a volume, so `Stop-Agent` and `Start-Agent` give it a clean copy.
- **Agents with the same owner pass the owner-only gate** (section 6, step 5).
- **Secrets are in each agent's environment.** Each can read its own agent key and your Claude token, and the
  containers have internet access. Keep the relay local, and revoke the token when you stop.
- **The harness publishes on its own**: presence, typing indicators and seen or working reactions.
- **Claims linger**: see section 11.
- **No media uploads**: MinIO is off.
- **Usage limits are shared** by all the agents and your own Claude use, and every message of yours in an
  agent's own channel is a task for that agent, so it spends a turn.
- **Policy is partly unclear** (section 3).

## 14. Owner registration later (Phase 2)

The kit adds each agent's key directly as a relay member so it can connect today. A direct member never gets an
owner recorded: the relay admits it before looking at any owner attestation (Buzz `buzz-relay`
`src/api/mod.rs:114-121`, `src/handlers/auth.rs:44-57`). That causes the NIP-AM 403. To register yourself as the
agents' owner later, for each agent:

1. Mint a NIP-OA attestation (`BUZZ_AUTH_TAG`) with your own owner key, on your machine
   (`crates/buzz-sdk/examples/compute_auth_tag.rs` in the Buzz source). The kit never handles your owner key.
2. Remove the agent's direct membership, after `. .\kit.ps1`:
   `Invoke-Compose exec -T relay buzz-admin remove-member --pubkey <the agent's hex in kit.json, under agents>`.
3. Start the agent with `BUZZ_AUTH_TAG` set. The relay then admits it through you and records you as its owner
   (`src/api/mod.rs:123-151`). `Start-Agent` does not pass an attestation yet; that is part of Phase 2. Agents
   with a recorded owner become siblings that pass each other's owner-only gate, so this also needs a rule that
   keeps them from triggering each other.

## 15. Linux (Debian)

The bash scripts do what the PowerShell ones do, step for step: the same twelve setup steps, image, checks, state
(`kit.json`) and agent commands. Tested with unit tests and a preflight on Debian 12 with Docker Engine 29; a full
setup on Linux has not yet been recorded as live evidence (the 2026-09-28 lab ran on Windows).

**Prerequisites.** Docker Engine from [Docker's apt repository](https://docs.docker.com/engine/install/debian/)
(`docker-ce`, `docker-buildx-plugin`, `docker-compose-plugin`): Debian's own `docker-compose` package is the old v1
and does not work. Then let your user run Docker without sudo, and install the rest:

```bash
sudo usermod -aG docker "$USER"    # then log out and in again
sudo apt install git jq curl iproute2
```

Setup checks for Compose 2.24.4 or newer and for buildx (the agent image's build uses cache mounts). The relay is
published on `127.0.0.1` only, as on Windows. Docker Engine runs natively, so there is no Docker Desktop to start:
the relay comes back with the Docker service after a reboot, the agents do not (`./kit.sh Start-Agent`).

**Your Claude token (section 3).** Run `claude setup-token` in a terminal of your own, copy the whole token, then
save it from the clipboard (`wl-paste` on Wayland, `xclip` on X11), never pasting it at a prompt:

```bash
read -r -p 'Copied the whole token? Press Enter'
t=$( { wl-paste 2>/dev/null || xclip -o -selection clipboard; } | tr -d '[:space:]')
if [[ $t =~ ^[A-Za-z0-9_-]{80,}$ ]]; then mkdir -p -m 700 ~/tinker-buzz-secrets; (umask 077; printf 'CLAUDE_CODE_OAUTH_TOKEN=%s\n' "$t" > ~/tinker-buzz-secrets/claude.env); else echo 'Copy the whole token again'; fi
unset t; { wl-copy ' ' 2>/dev/null || printf ' ' | xclip -selection clipboard; }; clear
```

The rules of section 3 hold: never put the token in your shell history, your profile or the repository.

**Buzz Desktop 0.5.25 (section 5).** The same release has a Debian package. Check it before installing (the
SHA-256 and size are the release's published asset digest; the kit was tested with the Windows build only):

```bash
f=~/Downloads/Buzz_0.5.25_amd64.deb
echo '0990e351453d7eb31e50a498df8efced5ede57931bb414fc50cc9ca56d672293  '"$f" | sha256sum -c - && stat -c %s "$f"   # 123075866
sudo apt install "$f"
```

**Setup (section 4).** From `Tinker/integrations/buzz/kit`, in any shell:

```bash
./setup.sh
```

With no arguments it is the same wizard. Unattended, the options are the PowerShell parameters in kebab case (the
PowerShell spelling, such as `-OwnerNpub`, is accepted too), and `--repository` repeats instead of taking a list:

```bash
./setup.sh --owner-npub npub1... --credential-file ~/tinker-buzz-secrets/claude.env --repository ~/src/app --repository ~/src/lib
```

State lives in `${XDG_DATA_HOME:-~/.local/share}/TinkerBuzz/<project>` instead of `%LOCALAPPDATA%\TinkerBuzz`.
Repositories are mounted read-only as on Windows; the agents run as uid 10001, so they can read files that are
readable by others (the usual `644` and `755`), never a folder only your user may read.

**Every command.** `kit.sh` runs one command per call from any shell (zsh included), with the same names as
`kit.ps1`; in bash you can also source it (`. ./kit.sh --project tinker-buzz`) and call the functions directly.

| Windows (PowerShell 7) | Linux (bash) |
| --- | --- |
| `.\setup.ps1` | `./setup.sh` |
| `. .\kit.ps1 -Project tinker-buzz; Get-KitStatus` | `./kit.sh --project tinker-buzz Get-KitStatus` (or `status`) |
| `Get-KitUsage` | `./kit.sh Get-KitUsage` (or `usage`) |
| `Stop-Agent; Start-Agent` | `./kit.sh Stop-Agent; ./kit.sh Start-Agent` |
| `Stop-Agent tester; Start-Agent tester` | `./kit.sh Stop-Agent tester; ./kit.sh Start-Agent tester` |
| `Stop-Flow; Start-Flow` | `./kit.sh Stop-Flow; ./kit.sh Start-Flow` |
| `Copy-AgentWork docs-typos "$HOME\Downloads"` | `./kit.sh Copy-AgentWork docs-typos ~/Downloads` (or `copy`) |
| `Invoke-Compose exec -T relay buzz-admin ...` | `./kit.sh Invoke-Compose exec -T relay buzz-admin ...` |
| `.\teardown.ps1` | `./teardown.sh` |
| `.\teardown.ps1 -Images -StateFolder` | `./teardown.sh --images --state-folder` (`--yes` skips the questions) |

When an agent, a canvas or Tinker Flow tells you to run `Copy-AgentWork <topic>`, run
`./kit.sh Copy-AgentWork <topic> <destination>`. The "never name a PowerShell variable `$lead`" warning
(section 11) does not apply: bash names are case-sensitive.

**Linux troubleshooting.**

- **"Docker is not reachable".** Start the service (`sudo systemctl start docker`) and check that `docker ps` works
  without sudo; after `usermod` you must log in again.
- **"Docker buildx is required".** Install `docker-buildx-plugin`; without it the build fails on its cache mounts.
- **A repository's files are missing inside the agents.** They are not readable by others: the agents run as
  another user. Fix the permissions, or mount a copy.

**Keeping the two in step.** A change to a `.ps1` script needs the same change in its `.sh` twin (and the other way
round). `tests/test_buzz_kit_bash.py` runs the PowerShell kit's checks against the bash kit with Docker mocked, and
fails when the pins, the team, the channels, the setup steps or the command names of `kit.sh` and `kit.ps1` differ.
