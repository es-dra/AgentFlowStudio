param(
    [switch]$DryRun,
    [switch]$AllowRemoteVideo,
    [switch]$NoOpen,
    [string]$RunRoot = "",
    [string]$ProviderConfig = "",
    [string]$SourceKeyframe = "data\processed\runs\memory_advantage_demo_012\asset_i2i_i2v_consistency\live\memory_assisted\neon_rain_turn\image\image_candidates\candidate_001.jpg"
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message"
}

function Write-TextFile {
    param(
        [string]$Path,
        [string]$Content
    )
    $parent = Split-Path -Parent $Path
    if ($parent) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    Set-Content -LiteralPath $Path -Value $Content -Encoding UTF8
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

if (-not $RunRoot) {
    $stamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $RunRoot = "data\processed\runs\memory_advantage_recording_016\neon_rain_turnback_i2v_$stamp"
}

$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $Python)) {
    throw "Project venv Python not found: $Python"
}

$SourcePath = Join-Path $RepoRoot $SourceKeyframe
if (-not (Test-Path -LiteralPath $SourcePath)) {
    throw "Source keyframe not found: $SourcePath"
}

$RunRootPath = Join-Path $RepoRoot $RunRoot
$ProtocolDir = Join-Path $RunRootPath "protocol"
$BaselineOutput = Join-Path $RunRootPath "live\baseline\neon_rain_turnback\i2v"
$MemoryOutput = Join-Path $RunRootPath "live\memory_backed\neon_rain_turnback\i2v"
$CompareDir = Join-Path $RunRootPath "comparison_videos"
$CompareVideo = Join-Path $CompareDir "neon_rain_baseline_vs_memory_15s.mp4"
$ProviderConfigPath = ""
if ($ProviderConfig) {
    if ([System.IO.Path]::IsPathRooted($ProviderConfig)) {
        $ProviderConfigPath = $ProviderConfig
    } else {
        $ProviderConfigPath = Join-Path $RepoRoot $ProviderConfig
    }
}

$UserTask = @'
Create a 15 second vertical 3D anime cinematic video. The same young woman from the source keyframe crosses a neon rain street at night, avoids a passing light sweep, turns back to camera, then stops under a flickering abstract neon sign. Keep the character recognizable, keep the high ponytail, white T-shirt, blue skinny jeans, and white sneakers, with coherent rain, reflections, hair, cloth, and foot contact.
'@

$BaselinePrompt = @"
Animate this source keyframe as a 15 second vertical 3D anime cinematic shot.
Task: $UserTask
Shot checkpoints: 0-3s front three-quarter readable character; 3-6s she begins walking through neon rain; 6-10s a light sweep and rain partially obscure her face and torso; 10-13s she turns back toward camera; 13-15s she stops under a flickering abstract neon sign, same character and outfit visible.
Use natural camera motion, stable geometry, wet street reflections, coherent rain and clothing motion.
"@

$MemoryPrompt = @"
Animate this source keyframe as a 15 second vertical 3D anime cinematic shot.
Task: $UserTask
Runtime memory projection: character memory card keeps the same face shape, eye spacing, nose bridge, lip shape, jawline, long high ponytail with loose face-framing strands, slim athletic build, full-length white fitted short-sleeve T-shirt tucked into blue skinny jeans with waist covered, and white sneakers.
Scene memory card: neon rain street at night, wet asphalt reflections, blue-magenta signage glow, readable skin tone, rain falls downward with slight side wind, puddles react to footsteps.
Feedback memory patch: do not introduce hair accessories, do not expose midriff, do not change into coat/dress/armor, recover the same face and same outfit after rain or light occlusion, keep foot contact and puddle interaction physically plausible.
Shot checkpoints: 0-3s front three-quarter readable character; 3-6s she begins walking through neon rain; 6-10s a light sweep and rain partially obscure her face and torso; 10-13s she turns back toward camera with ponytail inertia and wet cloth motion; 13-15s she stops under a flickering abstract neon sign, same face, outfit, and body silhouette recovered.
Avoid: another woman, generic anime face, short hair, crop top, exposed midriff, new logo text, live-action drift.
"@

Write-Step "Preparing recording experiment files"
New-Item -ItemType Directory -Force -Path $ProtocolDir | Out-Null
Write-TextFile -Path (Join-Path $ProtocolDir "user_task.txt") -Content $UserTask
Write-TextFile -Path (Join-Path $ProtocolDir "baseline_prompt.txt") -Content $BaselinePrompt
Write-TextFile -Path (Join-Path $ProtocolDir "memory_backed_prompt.txt") -Content $MemoryPrompt
Write-TextFile -Path (Join-Path $ProtocolDir "recording_notes.md") -Content @"
# AFS-MEMORY-ADVANTAGE-RECORDING-016

This run is for a prerecording workflow demonstration.

- Source keyframe: same file for both lanes.
- Baseline lane: current user task plus source keyframe only.
- Memory-backed lane: same task and source keyframe plus character, scene, and feedback memory projection.
- Provider route: Kling I2V, duration 15s, mode pro. Live provider calls require either -AllowRemoteVideo or AFS_ALLOW_REMOTE_VIDEO=true in the current shell, plus -ProviderConfig or AFS_PROVIDER_CONFIG.
- Claim boundary: provider/runtime evidence and visual review only; not human acceptance, business validation, or durable memory runtime proof.

"@

Write-Host "Repo root: $RepoRoot"
Write-Host "Run root:  $RunRootPath"
Write-Host "Source:    $SourcePath"
Write-Host "Dry run:   $DryRun"
Write-Host "Remote video allowed by switch: $AllowRemoteVideo"

if ($DryRun) {
    Write-Step "Dry run complete; provider calls were not made"
    exit 0
}

if ($AllowRemoteVideo) {
    $env:AFS_ALLOW_REMOTE_VIDEO = "true"
}

$VideoGate = ([string]$env:AFS_ALLOW_REMOTE_VIDEO).Trim().ToLowerInvariant()
if ($VideoGate -notin @("1", "true", "yes", "on")) {
    throw "Remote video calls are disabled. Re-run with -AllowRemoteVideo, or set AFS_ALLOW_REMOTE_VIDEO=true in this shell."
}

$ProviderConfigEnv = ([string]$env:AFS_PROVIDER_CONFIG).Trim()
$ProviderConfigArgs = @()
if ($ProviderConfigPath) {
    if (-not (Test-Path -LiteralPath $ProviderConfigPath)) {
        throw "Provider config not found: $ProviderConfigPath"
    }
    $ProviderConfigArgs = @("--provider-config", $ProviderConfigPath)
} elseif (-not $ProviderConfigEnv) {
    throw "Provider config is required. Pass -ProviderConfig with a local ignored config file, or set AFS_PROVIDER_CONFIG in this shell."
} elseif (-not (Test-Path -LiteralPath $ProviderConfigEnv)) {
    throw "Provider config from AFS_PROVIDER_CONFIG was not found: $ProviderConfigEnv"
}

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "ffmpeg was not found in PATH; install or add ffmpeg before running the live comparison."
}

Write-Step "Running baseline Kling I2V"
& $Python -m apps.cli.main kling-i2v-smoke `
    --image $SourcePath `
    --prompt $BaselinePrompt `
    --output $BaselineOutput `
    --duration 15 `
    --mode pro `
    --poll-interval-sec 5 `
    --max-polls 180 `
    --transport curl `
    @ProviderConfigArgs

Write-Step "Running memory-backed Kling I2V"
& $Python -m apps.cli.main kling-i2v-smoke `
    --image $SourcePath `
    --prompt $MemoryPrompt `
    --output $MemoryOutput `
    --duration 15 `
    --mode pro `
    --poll-interval-sec 5 `
    --max-polls 180 `
    --transport curl `
    @ProviderConfigArgs

$BaselineVideo = Join-Path $BaselineOutput "video_candidates\candidate_001.mp4"
$MemoryVideo = Join-Path $MemoryOutput "video_candidates\candidate_001.mp4"
if (-not (Test-Path -LiteralPath $BaselineVideo)) {
    throw "Baseline video not found after provider run: $BaselineVideo"
}
if (-not (Test-Path -LiteralPath $MemoryVideo)) {
    throw "Memory-backed video not found after provider run: $MemoryVideo"
}

Write-Step "Building side-by-side comparison video"
New-Item -ItemType Directory -Force -Path $CompareDir | Out-Null
& ffmpeg -y -i $BaselineVideo -i $MemoryVideo `
    -filter_complex "[0:v]scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2,setsar=1[v0];[1:v]scale=540:960:force_original_aspect_ratio=decrease,pad=540:960:(ow-iw)/2:(oh-ih)/2,setsar=1[v1];[v0][v1]hstack=inputs=2[v]" `
    -map "[v]" -an -c:v libx264 -pix_fmt yuv420p $CompareVideo

Write-Step "Completed"
Write-Host "Baseline video:      $BaselineVideo"
Write-Host "Memory-backed video: $MemoryVideo"
Write-Host "Comparison video:    $CompareVideo"
Write-Host "Protocol files:      $ProtocolDir"

if (-not $NoOpen) {
    Invoke-Item $CompareVideo
}
