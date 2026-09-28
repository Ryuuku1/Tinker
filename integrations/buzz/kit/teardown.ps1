#Requires -Version 7.2
<#
.SYNOPSIS
Stops the agents and the relay of one kit project; asks before deleting its data, keys, images or state folder.

.DESCRIPTION
Without confirmation it only stops containers. Deleting the volumes removes the community, the admin and agent
identities, the agents' work folder and the build caches; setup.ps1 then starts from scratch with new keys.
Only resources named after -Project are touched, by exact name. A folder mounted with -Repository is never touched.

.EXAMPLE
.\teardown.ps1                      # stop, then asks before deleting volumes
.\teardown.ps1 -Images -StateFolder # also asks before deleting the agent image and the state folder
#>
[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param([string]$Project = 'tinker-buzz', [string]$StateRoot, [switch]$Images, [switch]$StateFolder)
. (Join-Path $PSScriptRoot 'kit.ps1') -Project $Project -StateRoot $StateRoot
$s = Read-KitState

Stop-Agent
if (Test-Path -LiteralPath "$STATE\compose.yml") {
  Invoke-Compose down; if ($LASTEXITCODE) { throw 'compose down failed' }
}
'The agents and the relay are stopped.'

$existing = @(docker volume ls -q)
$ours = @($VOL.Values | Where-Object { $existing -contains $_ })
$composeVolumes = @($existing | Where-Object { $_ -in "${Project}_buzz-postgres-data", "${Project}_buzz-redis-data", "${Project}_buzz-git-data" })
if (($ours + $composeVolumes) -and $PSCmdlet.ShouldProcess((($ours + $composeVolumes) -join ', '),
    'Delete the relay data, the admin and agent keys, the work folder and the build caches')) {
  if (Test-Path -LiteralPath "$STATE\compose.yml") { Invoke-Compose down -v; if ($LASTEXITCODE) { throw 'compose down -v failed' } }
  foreach ($v in $ours) { docker volume rm $v | Out-Null; if ($LASTEXITCODE) { throw "could not delete volume $v" } }
  Remove-Item -LiteralPath "$STATE\.env" -Force -ErrorAction SilentlyContinue   # the relay secrets
  foreach ($k in 'admin', 'agents', 'owner', 'channels', 'agentMembership', 'agentConfig') { $s.Remove($k) }
  Save-KitState $s
  'Deleted the volumes and the relay secrets; setup.ps1 will generate new identities.'
}
if ($Images -and $s.image -and (docker images -q $s.image) -and $PSCmdlet.ShouldProcess($s.image, 'Delete the agent image')) {
  docker image rm $s.image | Out-Null; if ($LASTEXITCODE) { throw "could not delete $($s.image)" }
  $s.Remove('image'); Save-KitState $s
}
if ($StateFolder -and (Test-Path -LiteralPath $STATE) -and $PSCmdlet.ShouldProcess($STATE, 'Delete the state folder (sources, logs, kit.json)')) {
  if (@(docker volume ls -q | Where-Object { $_ -in @($VOL.Values) })) { throw 'Delete the volumes first: the state folder holds their .env' }
  Remove-Item -LiteralPath $STATE -Recurse -Force
  "Deleted $STATE"
}
'Revoke the Claude token when you no longer need it (GUIDE.md, Cleanup).'
