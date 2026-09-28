# Tinker's team in Buzz on your own Windows PC

This kit sets up a private Buzz relay on your PC and runs Tinker's team as three Buzz agents that answer
only you: **Tinker** (the Lead), **Tinker Reviewer** and **Tinker Researcher**. You chat with them from Buzz
Desktop in four channels whose canvases show how to work with each one; [EXAMPLES.md](EXAMPLES.md) has
worked examples. Everything runs in Docker on your machine; nothing is published beyond `127.0.0.1`. The
relay and the agents' safety settings match the lab setup the kit was built from (see the
[integration README](../README.md) and the [Buzz protocol](../protocol.md) every agent follows).

## 1. Prerequisites

- Windows 10 or 11 with **Docker Desktop** running **Linux containers** (Compose 2.24.4 or newer is included).
- **PowerShell 7** (`pwsh`) and **Git for Windows**.
- **Claude Code**, only to create your token (section 3).
- About **8 GB** of free disk space: sources, build caches, the agent image and base images.
- About **10-30 minutes** for the first setup: about 4.7 GB of images to download, then the Rust build (97 s on
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
and store it yourself; setup only passes the file's path to Docker and never reads it. All three agents share it.

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

## 4. Run the setup

From `Tinker\integrations\buzz\kit` in PowerShell 7:

```powershell
.\setup.ps1 -Repository C:\src\my-repo       # -Repository is optional
```

This first run builds everything, starts the relay on `ws://localhost:3000`, publishes the agents' profiles and
creates the channels, then stops and tells you to join from Buzz Desktop (section 5). Parameters:

- `-Repository <folder>`: a folder every agent reads at `/repo`, **mounted read-only**. It is kept for later runs;
  `-Repository ''` removes it. Every agent can read everything in it, including `.git` and untracked files.
- `-Port 3100` if 3000 is taken; `-Project <name>` for a second, separate setup.
- `-StateRoot <folder>` to keep setup's state somewhere other than `%LOCALAPPDATA%\TinkerBuzz` (pass it to
  `kit.ps1` and `teardown.ps1` too).

Setup is idempotent: after an error, fix the cause and run the same command again. It never regenerates keys
over an existing relay, and it restarts an agent only when that agent's settings changed.

What it does, in order: preflight; pulls the relay image by digest; one `docker build` that fetches Buzz `781d395`,
builds `buzz-acp` and `buzz` (its three Cargo Git dependencies locked), and builds the agent image with Tinker
installed in the image only, all from pinned base images and `claude-agent-acp` 0.81.2; verifies those pins, the
compose file's SHA-256 and each role's prompt; generates the admin key, one key per agent and the relay secrets
inside containers; starts the relay on `127.0.0.1:<port>`; checks the bootstrap and routing; adds members; sets
each agent's profile; creates the channels with a purpose and a canvas; starts the three agents and checks their
startup, deny rules and mounts; scans the kit folder and the setup logs for secrets. The only folder from your PC
a container mounts is `-Repository`, read-only; everything else goes in and out through `docker build` and
`docker cp`. Setup's own state (logs, relay secrets, `kit.json`) lives in `%LOCALAPPDATA%\TinkerBuzz\<project>`,
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
2. Choose **Add Community** and enter exactly `ws://localhost:3000` (or your `-Port`). A bare host becomes `wss://`.
3. You will see **Not a member yet** with your npub. Copy it, then run, from the kit folder:

   ```powershell
   .\setup.ps1 -OwnerNpub <your npub> -CredentialFile "$HOME\tinker-buzz-secrets\claude.env"
   ```

   Repeat any `-Port`, `-Project` or `-StateRoot` you used in section 4. This adds you to the relay and the
   channels, and starts the three agents with you as their owner. Then press **Try again**. (If you already
   know your npub, pass `-OwnerNpub` in section 4; without `-CredentialFile`, setup stops before the agents.)
4. Leave the **Welcome** channel at once when it opens.
5. Never start, add or @mention **Fizz**, **Honey** or **Pollen** (Desktop's built-in agents). They would share your
   identity as their owner, and agents with the same owner pass each other's owner-only gate.

## 7. First chat

Open `#tinker-lab`: its canvas lists the team. Mention an agent by its name in the mention picker (setup also
prints each npub, and so does `Get-KitStatus`). Try `@Tinker Read-only: what can you do here, and what are your
limits?` The agent answers in the thread. Then read [EXAMPLES.md](EXAMPLES.md) and the canvases of #requests,
#reviews and #research.

## 8. What to expect

- **Tinker** (the Lead) answers in any channel, usually #requests. It reads `/repo`, changes code only in its
  own clone under `/work` and runs the tests there. **Tinker Reviewer** and **Tinker Researcher** are read-only:
  `/repo` and `/work` are mounted read-only for them and their edit tools are denied. Only the Researcher may use
  the web (WebSearch and WebFetch); `curl`, `wget`, `env` and `printenv` are denied for all three.
- All three run **unattended**: commits, pushes, branch deletions, remote changes and Buzz workspace changes are
  denied, and Buzz messages (including your "I approve") never authorize them. They post the exact command so
  you can run it yourself.
- Each answers only your messages, and only when you mention it; everything else it sees is data, including the
  other agents. It replies in the thread. Agents never hand work to each other: you pick who is next.
- One Buzz session writes a checkout at a time; another thread may be told `workspace.owned`.
- To take the Lead's work out of `/work`, copy it: `docker cp <project>-lead:/work/<folder> <destination>`.

## 9. Stop and start

```powershell
. .\kit.ps1 -Project tinker-buzz      # in PowerShell 7, from the kit folder (add -StateRoot if you used one)
Get-KitStatus                         # containers, npubs, channels, each agent's log summary and run outcomes
Stop-Agent                            # stops and removes all three agents, and verifies they are gone
Start-Agent                           # starts them again with the saved owner, channels and credential file
Stop-Agent reviewer; Start-Agent reviewer   # one agent: lead, reviewer or researcher
```

The relay comes back with Docker Desktop on its own. The agents do not: after a reboot, run `Start-Agent`.

## 10. Troubleshooting

- **`NIP-AM: publish failed ... 403` in an agent's log every turn.** Expected: the relay has no owner record for
  the agents yet (section 13). Replies are unaffected.
- **An agent shows as an npub instead of its name.** Its profile did not reach Desktop yet: run setup again (it
  republishes the profiles), then reopen the channel.
- **No reply in the thread.** Run `Get-KitStatus`: *Latest unattended run outcomes* under each agent shows each
  run's final message, which Buzz never posts. Ask again in the thread.
- **Refused with `workspace.owned`, or the Lead made its own worktree.** A session that already ran a command in
  a checkout holds it for up to a day. `Stop-Agent lead; Start-Agent lead` clears it.
- **Port in use.** Run setup with `-Port 3100` and add `ws://localhost:3100` in Desktop. A project keeps its port:
  to change it, run `teardown.ps1` and delete its volumes first.
- **"Not started cleanly".** The line for each agent names the failed check. Read `docker logs <project>-<role>`.
  On an authentication or usage-limit error, fix the token file or wait for the limit, then `Stop-Agent; Start-Agent`.
- **Never name a PowerShell variable `$lead`.** Names are case-insensitive, so it is `$LEAD`, the Lead's container
  name; the kit makes `$LEAD` read-only so such an assignment fails loudly.

## 11. Cleanup and token revocation

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

## 12. Known risks

- **Only denies protect you.** buzz-acp approves every permission prompt itself; Tinker's hooks, the image's
  deny rules and the read-only mounts are what stop consequential operations.
- **Relayed text reaches the model.** Other members' and agents' messages in a thread are shown to each agent;
  ignoring them is model behavior.
- **The Researcher reads the web.** A page can carry instructions aimed at agents. It treats them as data, but
  it still has your token and its key in its environment, can read `/repo`, and can reach the internet, so an
  injected page could try to make it leak them. It cannot write files. Point it only at sources you trust.
- **The mounted repository is fully readable** by all three agents: history, untracked files, anything secret
  in it. Mount only what you would show them, never a folder that holds credentials.
- **Agents with the same owner pass the owner-only gate** (section 6, step 5).
- **Secrets are in each agent's environment.** Each can read its own agent key and your Claude token, and the
  containers have internet access. Keep the relay local, and revoke the token when you stop.
- **The harness publishes on its own**: presence, typing indicators and seen or working reactions.
- **Claims linger**: see section 10.
- **No media uploads**: MinIO is off.
- **Usage limits are shared** by the three agents and your own Claude use.
- **Policy is partly unclear** (section 3).

## 13. Owner registration later (Phase 2)

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
