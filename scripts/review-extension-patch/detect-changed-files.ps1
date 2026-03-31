<#
.SYNOPSIS
 Detect changed files for code review.

.DESCRIPTION
 Includes tracked changes (committed/staged/unstaged) and untracked files.
#>

[CmdletBinding()]
param(
 [switch]$Json,
 [Alias("h")]
 [switch]$Help
)

$ErrorActionPreference = 'Stop'

if ($Help) {
 @"
Usage: detect-changed-files.ps1 [OPTIONS]

Detect changed files for code review.

Includes tracked changes (committed/staged/unstaged) and untracked files.

OPTIONS:
 -Json Output in JSON format
 -Help, -h Show this help message
"@
 exit 0
}

function Write-ErrorAndExit {
 param(
 [string]$Message,
 [int]$Code = 1
 )
 if ($Json) {
 [PSCustomObject]@{ error = $Message } | ConvertTo-Json -Compress
 } else {
 Write-Error "Error: $Message"
 }
 exit $Code
}

function Parse-ZOutput {
 param([object[]]$Raw)
 if (-not $Raw) { return @() }
 $joined = ($Raw -join "`n")
 return @($joined -split "`0" | Where-Object { $_ -ne "" })
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
 Write-ErrorAndExit "git is not available. The review extension requires git to identify changed files." 1
}

$null = git rev-parse --git-dir 2>$null
if ($LASTEXITCODE -ne 0) {
 Write-ErrorAndExit "Not a git repository. The review extension requires git to identify changed files." 1
}

$CurrentBranch = ""
try {
 $CurrentBranch = (git branch --show-current 2>$null | Out-String).Trim()
} catch {
 $CurrentBranch = ""
}

$DefaultBranch = ""
try {
 $symref = (git symbolic-ref refs/remotes/origin/HEAD 2>$null | Out-String).Trim()
 if ($symref -match "refs/remotes/origin/(.+)$") {
 $DefaultBranch = $Matches[1]
 }
} catch {}

if (-not $DefaultBranch) {
 $null = git rev-parse --verify origin/main 2>$null
 if ($LASTEXITCODE -eq 0) { $DefaultBranch = "main" }
}
if (-not $DefaultBranch) {
 $null = git rev-parse --verify origin/master 2>$null
 if ($LASTEXITCODE -eq 0) { $DefaultBranch = "master" }
}

$ChangedFiles = @()
$Mode = ""

if ($CurrentBranch -and $DefaultBranch -and ($CurrentBranch -ne $DefaultBranch)) {
 $MergeBase = ""
 try {
 $MergeBase = (git merge-base "origin/$DefaultBranch" HEAD 2>$null | Out-String).Trim()
 } catch {}

 if ($MergeBase) {
 $committedFiles = Parse-ZOutput (git diff --name-only -z --diff-filter=ACMR "$MergeBase...HEAD" 2>$null)
 $stagedFiles = Parse-ZOutput (git diff --cached --name-only -z --diff-filter=ACMR 2>$null)
 $unstagedFiles = Parse-ZOutput (git diff --name-only -z --diff-filter=ACMR 2>$null)
 $untrackedFiles = Parse-ZOutput (git ls-files --others --exclude-standard -z 2>$null)

 $ChangedFiles = @($committedFiles + $stagedFiles + $unstagedFiles + $untrackedFiles | Sort-Object -Unique)
 $Mode = "Feature branch diff ($DefaultBranch...HEAD) + uncommitted + untracked changes"
 } else {
 $DefaultBranch = ""
 }
}

if (-not $Mode) {
 $stagedFiles = Parse-ZOutput (git diff --cached --name-only -z --diff-filter=ACMR 2>$null)
 $unstagedFiles = Parse-ZOutput (git diff --name-only -z --diff-filter=ACMR 2>$null)
 $untrackedFiles = Parse-ZOutput (git ls-files --others --exclude-standard -z 2>$null)
 $ChangedFiles = @($stagedFiles + $unstagedFiles + $untrackedFiles | Sort-Object -Unique)
 $Mode = "Working directory changes (staged + unstaged + untracked)"
 if (-not $DefaultBranch) { $DefaultBranch = "(unknown)" }
}

if ($ChangedFiles.Count -eq 0) {
 if ($Json) {
 [PSCustomObject]@{
 branch = $CurrentBranch
 default_branch = $DefaultBranch
 mode = $Mode
 changed_files = @()
 message = "No changes detected. Nothing to review."
 } | ConvertTo-Json -Compress
 } else {
 Write-Output "No changes detected. Nothing to review."
 }
 exit 2
}

if ($Json) {
 [PSCustomObject]@{
 branch = $CurrentBranch
 default_branch = $DefaultBranch
 mode = $Mode
 changed_files = $ChangedFiles
 } | ConvertTo-Json -Compress
} else {
 Write-Output "BRANCH: $CurrentBranch"
 Write-Output "DEFAULT_BRANCH: $DefaultBranch"
 Write-Output "MODE: $Mode"
 Write-Output "CHANGED_FILES:"
 foreach ($f in $ChangedFiles) {
 Write-Output " $f"
 }
}

exit 0
