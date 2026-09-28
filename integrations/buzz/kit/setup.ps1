#Requires -Version 7.2
<#
.SYNOPSIS
Sets up a local Buzz relay and Tinker's team on this Windows PC: Tinker (the Lead), Tinker Reviewer and Tinker
Researcher, owned by your Buzz Desktop identity, in channels whose canvases show how to work with them.

.DESCRIPTION
Idempotent and resumable: after a failure, fix the cause and run it again with the same parameters. It never
regenerates keys over an existing relay. Keys and relay secrets are generated inside containers and never printed;
the credential file is only passed to Docker. The only host folder a container mounts is -Repository, read-only.
See GUIDE.md and EXAMPLES.md.

.EXAMPLE
.\setup.ps1                                       # relay, profiles and channels, then it prints what to do in Buzz Desktop
.\setup.ps1 -OwnerNpub npub1... -CredentialFile "$HOME\tinker-buzz-secrets\claude.env" -Repository C:\src\my-repo
#>
[CmdletBinding()]
param(
  [string]$Project = 'tinker-buzz',
  [ValidateRange(1024, 65535)][int]$Port = 3000,
  [string]$TinkerRepo = (Join-Path $PSScriptRoot '..\..\..'),
  [string]$TinkerCommit,     # default: the kit's pin
  [string]$CredentialFile,   # a path only: passed to docker --env-file, never read
  [string]$OwnerNpub,        # your Buzz Desktop npub; without it, setup stops once the relay and channels are up
  [string]$Repository,       # a folder every agent reads at /repo, mounted read-only; kept for reruns, '' removes it
  [string]$StateRoot)        # default %LOCALAPPDATA%\TinkerBuzz; pass the same value to kit.ps1 and teardown.ps1
. (Join-Path $PSScriptRoot 'kit.ps1') -Project $Project -StateRoot $StateRoot
$TinkerRepo = (Resolve-Path -LiteralPath $TinkerRepo).Path
if (-not $TinkerCommit) { $TinkerCommit = $PIN.TinkerCommit }
if ($OwnerNpub -and $OwnerNpub -notmatch '^(npub1[02-9ac-hj-np-z]{58}|[0-9a-f]{64})$') { throw "Not an npub: $OwnerNpub" }
if ($Repository) {
  if (-not (Test-Path -LiteralPath $Repository -PathType Container)) { throw "Repository folder not found: $Repository" }
  $Repository = (Resolve-Path -LiteralPath $Repository).Path
}
$LOGS = "$STATE\logs"; $ENVFILE = "$STATE\.env"; $CTX = "$STATE\agent"; $ROLES = @($AGENTS.Keys)
$KITARGS = "-Project $Project" + $(if ($StateRoot) { " -StateRoot '$StateRoot'" } else { '' })   # for the hints below
$script:n = 0
function Step([string]$Title) { $script:n++; "`n[$script:n/12] $Title" }
function Assert-Exit([string]$What) { if ($LASTEXITCODE) { throw "$What failed (exit $LASTEXITCODE)" } }
# Final check: file names in the kit folder or the setup logs that hold a key, a relay secret or the credential.
function Invoke-SecretScan([hashtable]$Settings) {
  "`nFinal check: secret scan of the kit folder and the setup logs"
  $scan = @('create', '--label', "tinker.kit=$Project", '--user', '0:0', '-v', "$($VOL.humankeys):/humankeys:ro") +
    @($ROLES | ForEach-Object { '-v', "$($VOL["$_-key"]):/keys/${_}:ro" })
  if ($Settings.credentialFile) { $scan += @('--env-file', $Settings.credentialFile) }
  $c = docker @scan $Settings.image bash /kit/secretscan.sh /tmp/relay.env /tmp/kit /tmp/logs; Assert-Exit 'creating the scan container'
  try {
    docker cp $ENVFILE "${c}:/tmp/relay.env" | Out-Null; docker cp $KIT "${c}:/tmp/kit" | Out-Null; docker cp $LOGS "${c}:/tmp/logs" | Out-Null
    $result = docker start -a $c
  } finally { docker rm -f $c | Out-Null }
  $result | ForEach-Object { "  $_" }
  if ($result -notcontains 'secret-scan hits=0') { throw 'A secret was found in the kit folder or the logs (file names above): delete that copy and rotate the secret' }
}

Step 'Preflight: Docker with Linux containers, Compose, Git, a free port'
$os = docker version --format '{{.Server.Os}}' 2>$null
if ($LASTEXITCODE -or $os -ne 'linux') { throw 'Start Docker Desktop and switch it to Linux containers' }
$compose = (docker compose version --short) -replace '^v', ''
if ([version]($compose -replace '[^0-9.].*$', '') -lt [version]'2.24.4') { throw "Docker Compose 2.24.4 or newer is required (found $compose)" }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git is required' }
git -C $TinkerRepo cat-file -e "$TinkerCommit^{commit}" 2>$null
if ($LASTEXITCODE) { throw "Tinker commit $TinkerCommit is not in ${TinkerRepo}: fetch it, or pass -TinkerRepo and -TinkerCommit" }
New-Item -ItemType Directory -Force $STATE, $LOGS | Out-Null
$s = Read-KitState
if ($s.port -and $s.port -ne $Port -and (Test-Path -LiteralPath $ENVFILE)) {
  throw "This project was set up on port $($s.port): use -Port $($s.port), or run teardown.ps1 first"
}
$ours = (Test-Path -LiteralPath "$STATE\compose.yml") -and (Test-Path -LiteralPath $ENVFILE) -and (Invoke-Compose ps -q relay 2>$null)
if (-not $ours -and @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue).Count) {
  throw "Port $Port is in use: choose another with -Port"
}
$s.project = $Project; $s.port = $Port; $s.tinkerCommit = $TinkerCommit
if ($PSBoundParameters.ContainsKey('Repository')) { $s.repository = $Repository }
if (-not $s.channels) { $s.channels = @{} }
if (-not $s.agentConfig) { $s.agentConfig = @{} }
Save-KitState $s
"  Docker $os, Compose $compose, state folder $STATE" + $(if ($s.repository) { "`n  Repository (read-only at /repo): $($s.repository)" } else { '' })

Step 'Pinned relay image'
docker pull --quiet $PIN.RelayImage | Out-Null; Assert-Exit "docker pull $($PIN.RelayImage)"
if ((docker image inspect $PIN.RelayImage --format '{{index .Config.Labels "org.opencontainers.image.revision"}}') -ne $PIN.RelayRevision) {
  throw 'The relay image revision label does not match the pin'
}
"  $($PIN.RelayImage.Split('@')[1].Substring(0, 19))... revision $($PIN.RelayRevision.Substring(0, 9))"

Step 'Build buzz-acp and buzz from the pinned Buzz source, and the agent image with Tinker (one docker build)'
$inputs = @("$KIT\agent\Dockerfile", "$KIT\agent\deny.py") + @(Get-ChildItem "$KIT\scripts", "$KIT\roles" -File | Sort-Object FullName).FullName
$kitHash = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes(
  (($inputs | ForEach-Object { (Get-FileHash -LiteralPath $_).Hash }) -join '')))).Substring(0, 8).ToLower()
$image = "$Project-agent:$($TinkerCommit.Substring(0, 12))-$kitHash"   # new Tinker commit or kit files: new image
if (-not (docker images -q $image)) {
  Remove-Item -LiteralPath "$CTX\scripts", "$CTX\roles" -Recurse -Force -ErrorAction SilentlyContinue   # no stale files
  New-Item -ItemType Directory -Force "$CTX\scripts", "$CTX\roles" | Out-Null
  git -c core.autocrlf=false -C $TinkerRepo archive --format=tar --prefix=tinker/ -o "$CTX\tinker.tar" $TinkerCommit
  Assert-Exit 'git archive of Tinker'
  Copy-Item "$KIT\agent\Dockerfile", "$KIT\agent\deny.py" $CTX -Force
  Copy-Item "$KIT\scripts\*" "$CTX\scripts" -Force
  Copy-Item "$KIT\roles\*" "$CTX\roles" -Force
  '  First build: 10-30 minutes, mostly downloads and Rust (log: logs\build-agent.log); a rerun resumes from the cache'
  docker build -t $image $CTX *> "$LOGS\build-agent.log"; Assert-Exit "docker build (see $LOGS\build-agent.log)"
}
"  $image"

Step 'Verify the build: Buzz commit, Cargo Git sources, compose file, binaries, Claude Code, Tinker and the prompts'
$facts = docker run --rm $image bash -c 'cat /kit/buzz-commit.txt /kit/cargo-git.txt /kit/binaries.sha256' | Out-String
if ($facts -notmatch "(?m)^$($PIN.BuzzCommit)\r?$") { throw 'The image was not built from the pinned Buzz commit' }
$gitSources = @([regex]::Matches($facts, 'source = "(git\+[^"]+)"') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
if (Compare-Object $gitSources @($PIN.CargoGit | Sort-Object)) { throw 'Cargo.lock names Git sources other than the pinned three' }
foreach ($b in 'buzz-acp', 'buzz') {
  $h = [regex]::Match($facts, "(?m)^([0-9a-f]{64})\s+$b\r?$").Groups[1].Value
  if ($h -eq $PIN.Binaries[$b]) { "  $b sha256 matches the lab build" } else { "  $b sha256 $h (the lab build was $($PIN.Binaries[$b]))" }
}
$c = docker create $image; Assert-Exit 'creating a container to copy compose.yml'
try { docker cp "${c}:/kit/compose.yml" "$STATE\compose.yml" | Out-Null; Assert-Exit 'copying compose.yml' } finally { docker rm -f $c | Out-Null }
if ((Get-FileHash "$STATE\compose.yml").Hash.ToLower() -ne $PIN.ComposeSha256) { throw 'compose.yml does not match its pinned SHA-256' }
$check = docker run --rm $image bash -c ('claude --version; claude plugin list; jq ".permissions.deny | length" ~/.claude/settings.json; ' +
  'jq .apiKeyHelper ~/.claude/settings.json; compgen -e | grep -cE "^(ANTHROPIC_|CLAUDE_CODE_OAUTH_TOKEN$|CLAUDE_CODE_USE_)"; ' +
  'jq -r "(.env // {}) | keys[]" ~/.claude/settings.json | grep -cE "^(ANTHROPIC_|CLAUDE_CODE_OAUTH_TOKEN$|CLAUDE_CODE_USE_)"; ' +
  'git hash-object /opt/tinker/scripts/tinker_runtime.py; buzz-acp --help | head -n 1; grep -c "claude-agent-acp@0.81.2" /opt/acp/npm-ls.txt; ' +
  'for r in ' + ($ROLES -join ' ') + '; do { cat /opt/tinker/integrations/buzz/protocol.md; echo; cat "/kit/roles/$r.md"; } | ' +
  'cmp -s - "/kit/prompts/$r.md" && echo "prompt $r"; done; git config --system --get safe.directory') | Out-String
$blob = git -C $TinkerRepo rev-parse "${TinkerCommit}:scripts/tinker_runtime.py"
$ok = [ordered]@{
  'Buzz commit, 3 Cargo Git sources and compose.yml pinned' = $true
  'Claude Code 2.1.280' = $check -match '2\.1\.280 \(Claude Code\)'
  'tinker plugin enabled' = $check -match 'tinker@tinker-local[\s\S]*?enabled'
  "8 deny rules (the Lead's), no apiKeyHelper, no credential names" = $check -match '(?m)^8\r?\n^null\r?\n^0\r?\n^0\r?$'
  'runtime matches the Tinker commit' = $check -match [regex]::Escape($blob)
  'buzz-acp runs; claude-agent-acp 0.81.2' = $check -match 'ACP harness that bridges Buzz events to AI agents\r?\n[1-9]'
  'each role prompt is the protocol, then its role file' = -not @($ROLES | Where-Object { $check -notmatch "(?m)^prompt $_\r?$" })
  'git trusts /repo only' = $check -match '(?m)^/repo\r?$'
}
$ok.GetEnumerator() | ForEach-Object { "  $($_.Key): $($_.Value)" }
if ($ok.Values -contains $false) { throw 'The agent image check failed' }
$s.image = $image; Save-KitState $s

Step 'Keys and relay secrets, generated inside containers and never printed'
if (Test-Path -LiteralPath $ENVFILE) {
  if (-not $s.admin -or @($ROLES | Where-Object { -not ($s.agents -and $s.agents[$_]) })) {
    throw ".env exists but kit.json lacks public keys: run teardown.ps1, then setup again"
  }
  '  Keys exist; never regenerated over a relay'
} else {
  if (@(docker volume ls -q) -contains "${Project}_buzz-postgres-data") { throw 'The relay database exists but .env is gone: run teardown.ps1 to start over' }
  $mounts = @('-v', "$($VOL.humankeys):/humankeys") + @($ROLES | ForEach-Object { '-v', "$($VOL["$_-key"]):/keys/$_" })
  $c = docker create --label "tinker.kit=$Project" --user 0:0 --entrypoint bash @mounts $PIN.RelayImage /tmp/keygen.sh $Port $PIN.RelayImage @ROLES
  Assert-Exit 'creating the key container'
  try {
    docker cp "$KIT\scripts\keygen.sh" "${c}:/tmp/keygen.sh" | Out-Null; Assert-Exit 'copying keygen.sh'
    $out = docker start -a $c   # public keys, or a refusal; never a secret
    if ($LASTEXITCODE) { throw "Key generation failed: $out" }
    docker cp "${c}:/out/.env" $ENVFILE | Out-Null; Assert-Exit 'copying the relay secrets out'
  } finally { docker rm -f $c | Out-Null }
  $s.agents = @{}
  foreach ($l in $out) {
    if ($l -match '^([a-z]+)=([0-9a-f]{64})$') { if ($Matches[1] -eq 'admin') { $s.admin = $Matches[2] } else { $s.agents[$Matches[1]] = $Matches[2] } }
  }
  if (-not $s.admin -or @($ROLES | Where-Object { -not $s.agents[$_] })) { throw 'Key generation did not print every public key' }
  Save-KitState $s
  "  Generated the admin identity, one identity per agent ($($ROLES -join ', ')) and the relay secrets"
}

Step "Relay up, published on 127.0.0.1:$Port only"
Invoke-Compose config --quiet; Assert-Exit 'compose config'
Invoke-Compose up -d --wait *> "$LOGS\compose-up.log"; Assert-Exit "compose up (see $LOGS\compose-up.log)"
$published = @(docker port "$Project-relay-1" 3000)
if ($published.Count -ne 1 -or $published[0] -ne "127.0.0.1:$Port") { throw "The relay must be published on 127.0.0.1:$Port only, not: $published" }
Invoke-Compose ps --format '  {{.Service}}: {{.State}} {{.Health}}'

Step 'Bootstrap check and routing probe'
$relayLog = Invoke-Compose logs relay 2>&1 | Out-String
if ($relayLog -notmatch "Deployment community ensured`",`"host`":`"localhost:$Port`"" -or $relayLog -notmatch 'Relay owner bootstrapped') {
  throw "The relay did not bootstrap the community for localhost:${Port}: check 'docker logs $Project-relay-1'"
}
$ws = '-s', '-o', 'NUL', '-m', '3', '-w', '%{http_code}', '-H', 'Connection: Upgrade', '-H', 'Upgrade: websocket',
      '-H', 'Sec-WebSocket-Version: 13', '-H', 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ=='
$hostCode = curl.exe @ws "http://localhost:$Port/"
$wrongCode = curl.exe @ws -H 'Host: relay:3000' "http://localhost:$Port/"
$probe = '. /kit/forward.sh; curl -s -o /dev/null -m 3 -w "%{http_code}" -H "Connection: Upgrade" -H "Upgrade: websocket" ' +
         '-H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" "http://localhost:$KIT_PORT/"'
$inCode = docker run --rm --label "tinker.kit=$Project" --network $NET -e "KIT_PORT=$Port" $image bash -c $probe
$codes = "host=$hostCode wrong-host=$wrongCode container=$inCode"   # curl exits 28 after the upgrade; only the codes count
"  $codes"
if ($codes -ne 'host=101 wrong-host=404 container=101') { throw 'Routing probe failed: clients must reach the relay as localhost:<port>' }

Step 'Relay membership (buzz-admin add-member)'
function Add-RelayMember([string]$Key) {
  $o = Invoke-Compose exec -T relay buzz-admin add-member --pubkey $Key 2>&1 | Out-String
  if ($o -match '(?:added|already a member:)\s*([0-9a-f]{64})') { $Matches[1] } else { throw "add-member failed for $Key" }
}
foreach ($r in $ROLES) { [void](Add-RelayMember $s.agents[$r]) }
$s.agentMembership = 'direct'   # a direct member never gets an owner recorded; see GUIDE.md, Phase 2
if ($OwnerNpub) { $s.owner = Add-RelayMember $OwnerNpub }
Save-KitState $s
foreach ($r in $ROLES) { "  $($AGENTS[$r].name.PadRight(18)) $(ConvertTo-Npub $s.agents[$r])" }
if ($s.owner) { "  $('Owner'.PadRight(18)) $(ConvertTo-Npub $s.owner)" }

Step 'Agent profiles: a name and an about line, published with each agent key'
foreach ($r in $ROLES) {
  Invoke-As $r users set-profile --name $AGENTS[$r].name --about $AGENTS[$r].about | Out-Null; Assert-Exit "setting the $r profile"
  "  $($AGENTS[$r].name)"
}

Step 'Channels: the owner and every agent as members, a purpose and a canvas each'
$all = @(Invoke-Admin channels list | Out-String | ConvertFrom-Json)
foreach ($name in $CHANNELS.Keys) {
  $ch = $all | Where-Object name -eq $name | Select-Object -First 1
  if (-not $ch) {
    Invoke-Admin channels create --name $name --type stream --visibility open --description $CHANNELS[$name] | Out-Null
    Assert-Exit "creating #$name"
    $ch = @(Invoke-Admin channels list | Out-String | ConvertFrom-Json) | Where-Object name -eq $name | Select-Object -First 1
  }
  $id = $ch.channel_id; $s.channels[$name] = $id; $done = @()
  $members = @(Invoke-Admin channels members --channel $id | Out-String | ConvertFrom-Json).pubkey
  foreach ($k in @($ROLES | ForEach-Object { $s.agents[$_] }) + @($s.owner) | Where-Object { $_ -and $members -notcontains $_ }) {
    Invoke-Admin channels add-member --channel $id --pubkey $k | Out-Null; Assert-Exit "adding a member to #$name"; $done += 'member'
  }
  $info = @(Invoke-Admin channels search --query $name | Out-String | ConvertFrom-Json) | Where-Object channel_id -eq $id   # get omits the purpose
  if ($info.purpose -ne $CHANNELS[$name]) {
    Invoke-Admin channels purpose --channel $id --purpose $CHANNELS[$name] | Out-Null; Assert-Exit "setting the purpose of #$name"; $done += 'purpose'
  }
  $canvas = (Get-Content -LiteralPath "$KIT\channels\$name.md" -Raw).TrimEnd()
  if (((Invoke-Admin canvas get --channel $id | Out-String) -replace '\r', '').TrimEnd() -ne $canvas) {   # Out-String joins with CRLF
    $canvas | Invoke-Admin canvas set --channel $id --content - | Out-Null; Assert-Exit "setting the canvas of #$name"; $done += 'canvas'
  }
  "  #$($name.PadRight(11)) $id" + $(if ($done) { "  (set: $(($done | Select-Object -Unique) -join ', '))" } else { '' })
}
Save-KitState $s

if (-not $CredentialFile) { $CredentialFile = $s.credentialFile }
if (-not $s.owner -or -not $CredentialFile) {   # the agents need both; stop here without starting anything
  $again = ".\setup.ps1 $KITARGS -Port $Port"
  "`nThe relay is up at ws://localhost:$Port with the channels. Next (GUIDE.md, Buzz Desktop):"
  if (-not $s.owner) {
    "  1. In Buzz Desktop choose Add Community and enter ws://localhost:$Port."
    "  2. Copy your npub from 'Not a member yet', then run this again with it and your token file:"
    "     $again -OwnerNpub <your npub> -CredentialFile <your env file>"
    "  3. Back in Buzz Desktop, press Try again."
  } else {
    "  1. In Buzz Desktop choose Add Community and enter ws://localhost:${Port}: you are already a member."
    "  2. To start the agents, run this again with your token file (GUIDE.md, section 3):"
    "     $again -CredentialFile <your env file>"
  }
  Invoke-SecretScan $s
  return
}

Step 'Start the agents with the safe settings and you as their owner'
if (-not (Test-Path -LiteralPath $CredentialFile -PathType Leaf)) { throw "Credential file not found: $CredentialFile" }
$names = docker run --rm --env-file $CredentialFile $image bash -c `
  'compgen -e | grep -E "^(ANTHROPIC_|CLAUDE_CODE_OAUTH_TOKEN$|CLAUDE_CODE_USE_|AWS_|GOOGLE_|CLOUD_ML_)" | sort | paste -sd, -'
if ($names -notin 'CLAUDE_CODE_OAUTH_TOKEN', 'ANTHROPIC_API_KEY') {
  throw "The credential file must set exactly one of CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY (names found: $names)"
}
"  Credential variable: $names (the value is never read)"
$s.credentialFile = (Resolve-Path -LiteralPath $CredentialFile).Path
Save-KitState $s
$safe = (Get-FileHash -LiteralPath "$KIT\agent.env").Hash
$restart = @()
foreach ($r in $ROLES) {   # restart an agent only when its run settings changed
  $wanted = [Convert]::ToHexString([Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes(
    ((Get-AgentRunArgs $r $s) + $safe) -join "`n")))
  if ((docker ps -q --filter "name=^/$Project-$r$") -and $s.agentConfig[$r] -eq $wanted) { "  $($AGENTS[$r].name) is already running with these settings" }
  else { $restart += $r; $s.agentConfig[$r] = $wanted }
}
Save-KitState $s
if ($restart) { Stop-Agent $restart; Start-Agent $restart }

Step 'Startup check'
Test-AgentStartup
"`nTinker's team is running. In Buzz Desktop open #tinker-lab and @mention an agent by name:"
foreach ($r in $ROLES) { "  $($AGENTS[$r].name.PadRight(18)) $(ConvertTo-Npub $s.agents[$r])" }
"Worked examples: EXAMPLES.md. Status: . .\kit.ps1 $KITARGS; Get-KitStatus   (Stop-Agent and Start-Agent there too)"
Invoke-SecretScan $s
