param(
    [switch]$AllowLLM,
    [switch]$AllowImage,
    [switch]$AllowVideo,
    [string]$ProviderConfig = "",
    [int]$Port = 8790
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
Set-Location $repo

if (-not (Test-Path -LiteralPath "apps\studio\index.html")) {
    throw "AFS Studio static entry is missing. Start this script from a complete AgentFlowStudio checkout."
}

$env:AFS_ALLOW_REMOTE_LLM = $(if ($AllowLLM) { "true" } else { "false" })
$env:AFS_ALLOW_REMOTE_IMAGE = $(if ($AllowImage) { "true" } else { "false" })
$env:AFS_ALLOW_REMOTE_VIDEO = $(if ($AllowVideo) { "true" } else { "false" })
$env:AFS_ALLOW_REMOTE_ASR = "false"
$env:AFS_ALLOW_EXTERNAL_DOWNLOAD = "false"

if ($ProviderConfig) {
    $env:AFS_PROVIDER_CONFIG = $ProviderConfig
}

$providerConfigPresent = $false
if ($ProviderConfig) {
    $providerConfigPresent = Test-Path -LiteralPath $ProviderConfig
}

Write-Host "AFS Studio internal test runtime"
Write-Host "Runtime: http://127.0.0.1:$Port/studio/"
Write-Host "Gates: LLM=$($env:AFS_ALLOW_REMOTE_LLM) IMAGE=$($env:AFS_ALLOW_REMOTE_IMAGE) VIDEO=$($env:AFS_ALLOW_REMOTE_VIDEO) ASR=$($env:AFS_ALLOW_REMOTE_ASR) DOWNLOAD=$($env:AFS_ALLOW_EXTERNAL_DOWNLOAD)"
Write-Host "Provider config present: $providerConfigPresent"

& .\.venv\Scripts\python.exe -m apps.cli.main runtime-service --host 127.0.0.1 --port $Port
