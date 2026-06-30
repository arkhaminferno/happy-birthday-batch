# One-time setup for Windows 11 + NVIDIA GPU (e.g. RTX 5070).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

Write-Host "== CelebrateVibes setup (Windows) =="

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Install Git for Windows first: https://git-scm.com/download/win"
    exit 1
}

if (Get-Command git-lfs -ErrorAction SilentlyContinue) {
    git lfs install
    git lfs pull
} else {
    Write-Host "WARN: git-lfs not found — install: winget install GitHub.GitLFS"
}

foreach ($tool in @("ffmpeg", "ffprobe")) {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Host "WARN: $tool not on PATH — install: winget install Gyan.FFmpeg"
    }
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}

Write-Host "Installing batch dependencies..."
uv sync

$AceDir = if ($env:ACESTEP_ROOT) { $env:ACESTEP_ROOT } else { Join-Path (Split-Path $Root -Parent) "ACE-Step-1.5" }
if (Test-Path (Join-Path $AceDir "acestep")) {
    Write-Host "ACE-Step found at: $AceDir"
    Write-Host "Run once in ACE-Step folder: uv sync"
} else {
    Write-Host ""
    Write-Host "ACE-Step not found at: $AceDir"
    Write-Host "Clone it for audio generation:"
    Write-Host "  git clone https://github.com/ace-step/ACE-Step-1.5.git `"$AceDir`""
    Write-Host "  cd `"$AceDir`""
    Write-Host "  uv sync"
    Write-Host "Or set ACESTEP_ROOT to your existing checkout."
}

Write-Host ""
Write-Host "Setup complete. Next steps:"
Write-Host "  1) Terminal A — start API:"
Write-Host "       scripts\start_acestep_api.bat"
Write-Host "  2) Terminal B — init LLM (first time):"
Write-Host "       scripts\batch.cmd init-api"
Write-Host "  3) Generate + render:"
Write-Host "       scripts\batch.cmd generic-intro --force --video"
Write-Host "       scripts\batch.cmd ae-batch --slug rahul-in-birthday-edm-party --limit 1"
Write-Host "  4) Health check:"
Write-Host "       scripts\batch.cmd doctor"
