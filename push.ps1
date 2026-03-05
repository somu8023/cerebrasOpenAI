#!/usr/bin/env pwsh
# ─────────────────────────────────────────────────────────────
#  push.ps1  —  Cerebras FactCheck production deploy script
#  Usage:  .\push.ps1 "your commit message"
#
#  Auto-bumps version.txt on every call:
#    1.0 → 1.1 → 1.2 → … → 1.10 → 2.0 → 2.1 → … → 2.10 → 3.0
# ─────────────────────────────────────────────────────────────

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Message
)

$versionFile = Join-Path $PSScriptRoot "version.txt"

# ── Read current version ──────────────────────────────────────
if (-not (Test-Path $versionFile)) {
    "1.0" | Set-Content $versionFile -NoNewline
}
$raw = (Get-Content $versionFile -Raw).Trim()

# ── Parse X.Y ────────────────────────────────────────────────
if ($raw -match '^(\d+)\.(\d+)$') {
    $major = [int]$Matches[1]
    $minor = [int]$Matches[2]
} else {
    Write-Host "ERROR: version.txt has unexpected format '$raw'" -ForegroundColor Red
    exit 1
}

# ── Bump logic: minor 0-10, then major++ ─────────────────────
if ($minor -ge 10) {
    $major++
    $minor = 0
} else {
    $minor++
}
$newVersion = "$major.$minor"

# ── Write new version ─────────────────────────────────────────
$newVersion | Set-Content $versionFile -NoNewline
Write-Host "Version bumped: $raw → $newVersion" -ForegroundColor Cyan

# ── Stage, commit, push ───────────────────────────────────────
git add -A
git commit -m "v$newVersion — $Message"
git push

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓  Deployed v$newVersion" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "✗  Push failed. Rolled back version to $raw" -ForegroundColor Red
    $raw | Set-Content $versionFile -NoNewline
    exit 1
}
