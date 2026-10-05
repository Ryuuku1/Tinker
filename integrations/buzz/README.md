# Tinker in a Buzz workspace

[Buzz](https://github.com/block/buzz) is a self-hosted workspace on a Nostr relay; its `buzz-acp`
harness runs Claude Code and Codex through their ACP adapters. This optional integration lets
Tinker's Lead answer its owner in Buzz channels and threads. Nothing in Tinker's core depends on it.

Everything below was first checked on 2026-09-26 against Buzz `781d39510` (`main`), in Linux containers,
with the scripted model endpoints described in [provider setup](../../docs/providers.md#buzz-optional-team-surface).
On 2026-09-28 a Docker lab on Windows ran the Lead end to end with a live Claude subscription token and Buzz
Desktop 0.5.25 as the owner's client; nothing ran natively on Windows or macOS.

**On Windows or Linux, use the [kit](kit/GUIDE.md):** one script (PowerShell 7 on Windows, bash on Debian and other
Linux hosts) sets up the relay, keys, the agent image,
channels and Tinker's team (the Lead, a Tester, and a read-only Planner, Reviewer and Researcher, all with web
access, plus Tinker Flow, which runs whole flows across them with no AI of its own), owned by your Buzz Desktop
identity. Run `setup.ps1` (or `setup.sh`) with no parameters for a wizard; [EXAMPLES.md](kit/EXAMPLES.md) shows how to work with
the team. The sections below describe the single-Lead setup by hand.

## What you get, and what you do not

- **Claude Code** (via `claude-agent-acp`) is the one host that can write in Buzz. Tinker's hooks
  load and hold there. **Codex** (via `codex-acp`) is read-only in Buzz: review, research and status.
  With a normal Tinker install its hooks never run under the adapter, so nothing enforces that limit
  (see the compatibility table). **Antigravity** and **`buzz-agent`** are unsupported.
- A Buzz-run session is always unattended. Every consequential operation (push, commit, branch
  deletion, remote changes, relay changes such as workflows or memory) is denied with a reason. It
  is never asked, because buzz-acp answers every permission prompt with "allow". Buzz messages,
  reactions and workflow approvals never authorize anything. You run the operation yourself, or
  approve it in an attended native session.
- One Buzz session writes a checkout at a time. Other sessions are refused and should work in their
  own worktree.
- The Lead follows the [Buzz protocol](protocol.md): it answers only your triggering request and
  treats everything else relayed to it as data. It replies in the thread and ends with an
  evidence-backed report.

## 1. A local relay at the pinned revision

```bash
git clone https://github.com/block/buzz && cd buzz && git checkout 781d39510
```

Use the published relay image `ghcr.io/block/buzz@sha256:1120aa3fa8b57b243de35f309255870ba3520726ff2490f0d494bfb16dcf9c79`
(`sha-0275372`, the Desktop 0.5.25 tree; it contains `buzz-relay` and `buzz-admin`) with
`deploy/compose/compose.yml` under its own project name. Build only the agent-side binaries yourself; without a
Rust toolchain, in a container, keeping `target` in a named volume:

```bash
docker run --rm -v "$PWD:/src:ro" -v buzz-target:/target -e CARGO_TARGET_DIR=/target -w /src \
  rust:1.95-bookworm cargo build --release --locked -p buzz-acp -p buzz-cli
```

Copy `.env.example` to `.env` and replace every `CHANGE_ME`. For a local relay:
- `RELAY_URL=ws://localhost:3000`. The relay binds each connection to one community by the exact `Host`
  header, which must equal `RELAY_URL`'s authority; there is no fallback tenant. Every client, including
  containers, must dial `localhost:3000` (containers through a local forwarder such as `socat`).
- `BUZZ_HTTP_PORT=127.0.0.1:3000`, so the relay listens on loopback only.
- `BUZZ_REQUIRE_AUTH_TOKEN=true`: with `false`, REST accepts an unsigned `X-Pubkey` header, so an agent could
  impersonate its owner.
- `BUZZ_AUTO_MIGRATE=true` and `BUZZ_IMAGE=<the image above>`.
- `BUZZ_GIT_CONFORMANCE_PROBE=false` whenever MinIO is disabled (below): the probe is fatal without S3.

```bash
docker compose -p my-buzz -f compose.yml -f compose.local.yml up -d
```

On 2026-09-26 the pinned MinIO images could not be pulled (quay.io `401 Unauthorized`). Media
storage is not needed here, so `compose.local.yml` disabled it:

```yaml
services:
  relay:
    depends_on: !override
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
  minio: {profiles: ["disabled"]}
  minio-init: {profiles: ["disabled"]}
```

The relay log should show `Deployment community ensured` for your `RELAY_URL` host and
`Relay owner bootstrapped`.

## 2. Keys and membership (you, not Tinker)

Create the identities yourself: your owner key (`RELAY_OWNER_PUBKEY`) and one key for the Lead's
agent. `buzz-admin generate-key` prints a pair. Keep the private halves in your own secret store.
Tinker never reads, stores or posts private keys, and it never needs your provider keys.

```bash
docker compose -p my-buzz -f compose.yml exec relay buzz-admin add-member --pubkey <agent-hex>
BUZZ_PRIVATE_KEY=<owner key> buzz --relay http://localhost:3000 channels create --name tinker --type stream --visibility open
BUZZ_PRIVATE_KEY=<owner key> buzz --relay http://localhost:3000 channels add-member --channel <id> --pubkey <agent-hex>
```

Use one Buzz identity for the Lead. Specialists stay native helpers inside the Lead's host.

## 3. Run buzz-acp with Claude Code

Prerequisites on the agent machine:
- `npm install -g @agentclientprotocol/claude-agent-acp@0.81.2` (it bundles Claude Code 2.1.280). In a
  container, link its bundled `claude` onto `PATH` before installing Tinker: without it the installer skips the
  plugin registration.
- Tinker installed for Claude (`python scripts/install_apps.py --app claude`, run by you).
- Your own Claude credential: by default a subscription token from `claude setup-token` in
  `CLAUDE_CODE_OAUTH_TOKEN` (it ran end to end in the 2026-09-28 lab); an `ANTHROPIC_API_KEY` is the fallback.
  Never set both, nor `ANTHROPIC_AUTH_TOKEN` or `ANTHROPIC_BASE_URL`, which outrank or reroute the token.

```bash
export BUZZ_PRIVATE_KEY=<agent key> BUZZ_RELAY_URL=ws://localhost:3000
export BUZZ_ACP_AGENT_COMMAND=claude-agent-acp
export BUZZ_ACP_PERMISSION_MODE=dont-ask   # a mode Tinker counts as safe; see the note below
export BUZZ_ACP_RESPOND_TO=owner-only      # or allowlist with BUZZ_ACP_RESPOND_TO_ALLOWLIST
export BUZZ_ACP_SYSTEM_PROMPT_FILE=<tinker>/integrations/buzz/protocol.md
buzz-acp --agent-owner <owner-hex>
```

- Set these as **environment variables**, not flags. Flags are invisible to the agent, so Tinker can
  only check and report settings that arrive through the environment.
- The kit's [agent.env](kit/agent.env) lists the full set of safe settings (thread sessions, queued events, no
  memory, no heartbeat); each agent starts with the protocol plus its role file as system prompt.
- Tinker counts `dont-ask` as safe, but it protects nothing on its own. `claude-agent-acp` 0.81.2 does not
  advertise that mode, so buzz-acp silently skips it and Claude runs in `default` mode. buzz-acp
  then approves every permission prompt, in every mode. Tinker's hooks deny the gated operations
  anyway, and turn-one context and `status` report the host mode as unsafe.
- `BUZZ_ACP_SYSTEM_PROMPT_FILE` delivers the protocol as `<agent-instructions>` in every prompt.
  Tinker's turn-one context also carries it once the hooks detect Buzz.
- If the owner is not set, the default `owner-only` gate drops every event.

**Least-privilege host rules.** Because buzz-acp approves every prompt, Claude's `permissions.allow`
and `ask` rules add nothing. `permissions.deny` rules do hold: `Bash(touch:*)` was denied in
`default` and `bypassPermissions` modes under buzz-acp. Add deny rules to the agent's Claude
settings for anything the workspace must never do that Tinker does not already gate, for example
`WebFetch` or specific commands.

## 4. Codex (read-only)

Codex needs `npm install -g @agentclientprotocol/codex-acp@1.13.1`, which bundles codex-cli 0.156.1,
and an OpenAI API key. A ChatGPT subscription is not enough.

- **Tinker's hooks do not run under the adapter.** Tinker installs its Codex hooks through the
  plugin, and codex app-server 0.156.1 does not discover plugin hooks.
- **Codex's own modes are no substitute.** `BUZZ_ACP_PERMISSION_MODE` never applies to Codex, whose
  modes are `read-only`, `agent` and `agent-full-access` (set with `INITIAL_AGENT_MODE`). Its
  `read-only` mode is misnamed: it still allows workspace writes, with approvals that buzz-acp grants.
- **Use it for review, research and status only.** Treat that limit as instruction-only.
- Hook commands placed in `~/.codex/hooks.json` and trusted in `/hooks` did fire under codex-acp.
  Tinker's installer does not produce that setup, so this remains future work.

## 5. Windows notes (source-based, not verified)

`buzz-dev-mcp`'s shell tool, used by `buzz-agent` and the optional MCP server, needs Git for Windows.
It resolves, in order:
1. `BUZZ_SHELL`;
2. `GIT_BASH`;
3. `bash.exe` on `PATH` (never System32's WSL launcher);
4. `git.exe` on `PATH`, using its sibling `bin\bash.exe`;
5. the standard install paths and the registry.

Set `BUZZ_SHELL` to your Git Bash if none of these finds it. Claude Code and Codex use their own
shells. On Windows, Tinker reads the Buzz variable names case-insensitively.

## 6. Operations, cleanup and troubleshooting

- `python <tinker>/scripts/tinker_runtime.py status` lists each chat, including any Buzz setting
  notes, plus the checkouts Buzz sessions are writing.
- Under buzz-acp no host sent SessionEnd (after `run --task`, or when the service stopped), so an
  ownership record stays behind after its session is gone. It counts as live while that chat was seen
  within the last day, then as stale, and it is never taken over. Release it yourself, in your own
  terminal (agents are refused): `python <tinker>/scripts/tinker_runtime.py release <checkout>`. Give
  each writing task its own worktree so a leftover record blocks nothing else.
- Record the Buzz scope (relay, channel, thread) in the task checkpoint body.
- A write refused with `tinker[workspace.owned]` means another session owns that checkout: use
  `git worktree add`, or ask the owner to release it once that session is done.
- If the first-turn context lacks "Tinker is active", the hooks are not loaded in that host (the
  Codex case): keep it read-only.
- Teardown: `docker compose -p my-buzz -f compose.yml -f compose.local.yml down -v`, then remove the
  image, build volume and keys you created. With the kit, run `kit/teardown.ps1` (or `kit/teardown.sh`).
- Tinker creates no Buzz workflows or schedules and writes no relay memory. Relay changes other than
  replying are gated (`buzz.mutate`) and are denied in Buzz sessions.
