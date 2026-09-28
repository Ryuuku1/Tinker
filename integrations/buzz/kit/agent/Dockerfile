# Tinker's Buzz agents and Tinker Flow (one image), built without mounting any host folder. Stage 1
# fetches the pinned Buzz source and builds buzz-acp and buzz; stage 2 adds claude-agent-acp 0.81.2 (it bundles
# Claude Code 2.1.280) and installs Tinker into this image's own home. setup.ps1 puts tinker.tar, deny.py, scripts/
# and roles/ in the build context, and verifies the pins recorded under /kit against kit.ps1.
FROM rust:1.95-bookworm@sha256:6258907abe69656e41cd992e0b705cdcfabcbbe3db374f92ed2d47121282d4a1 AS buzz
ARG BUZZ_REPO=https://github.com/block/buzz
ARG BUZZ_COMMIT=781d39510cf23cfe224e8f521ae06a23377e06de
RUN git init -q /src && git -C /src remote add origin "$BUZZ_REPO" \
    && git -C /src fetch -q --depth 1 origin "$BUZZ_COMMIT" \
    && git -C /src -c advice.detachedHead=false checkout -q FETCH_HEAD \
    && test "$(git -C /src rev-parse HEAD)" = "$BUZZ_COMMIT"
WORKDIR /src
RUN --mount=type=cache,target=/usr/local/cargo/registry --mount=type=cache,target=/target \
    CARGO_TARGET_DIR=/target cargo build --release --locked -p buzz-acp -p buzz-cli \
    && install -D -m 755 -t /out/bin /target/release/buzz-acp /target/release/buzz
RUN mkdir -p /out/kit && git rev-parse HEAD > /out/kit/buzz-commit.txt \
    && grep -o 'source = "git+[^"]*"' Cargo.lock | sort -u > /out/kit/cargo-git.txt \
    && cp deploy/compose/compose.yml /out/kit/compose.yml \
    && (cd /out/bin && sha256sum buzz-acp buzz) > /out/kit/binaries.sha256

FROM node:24-bookworm@sha256:64af3819f9275802414d7cdc38c27e9d82bd564dec4d4da87d008255d36c63b4
RUN apt-get update && apt-get install -y --no-install-recommends python3 git jq socat \
    && rm -rf /var/lib/apt/lists/*
RUN npm install -g --prefix /opt/acp --ignore-scripts @agentclientprotocol/claude-agent-acp@0.81.2 \
    && npm ls -g --prefix /opt/acp --all --depth=2 > /opt/acp/npm-ls.txt
COPY --from=buzz /out/bin/ /usr/local/bin/
COPY --from=buzz /out/kit/ /kit/
COPY scripts/ /kit/
COPY roles/ /kit/roles/
ADD tinker.tar /opt/
COPY deny.py /opt/kit/deny.py
# Each role's system prompt: Tinker's Buzz protocol at the pinned commit, then the role's own rules.
RUN mkdir /kit/prompts && for r in /kit/roles/*.md; do \
      { cat /opt/tinker/integrations/buzz/protocol.md; echo; cat "$r"; } > "/kit/prompts/${r##*/}"; done
# A Windows checkout mounted under /repos may have CRLF files (agent.sh trusts each mounted repository by path).
RUN git config --system core.autocrlf input
# The bundled claude must be on PATH before the installer runs, or the plugin is never registered.
RUN ln -s /opt/acp/lib/node_modules/@agentclientprotocol/claude-agent-acp/node_modules/@anthropic-ai/claude-agent-sdk-linux-x64/claude /usr/local/bin/claude \
    && useradd -m -u 10001 -s /bin/bash agent \
    && install -d -o agent -g agent /work /opt/tinker/.tinker /home/agent/chat
ENV PATH=/opt/acp/bin:$PATH HOME=/home/agent \
    CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1 DISABLE_AUTOUPDATER=1 DISABLE_TELEMETRY=1 DISABLE_ERROR_REPORTING=1
USER agent
RUN python3 /opt/tinker/scripts/install_apps.py --app claude --home /home/agent --python /usr/bin/python3 \
      > /home/agent/tinker-install.log 2>&1 || (cat /home/agent/tinker-install.log; exit 1)
RUN python3 /opt/kit/deny.py /home/agent/.claude/settings.json lead
WORKDIR /work
LABEL tinker.kit=buzz
