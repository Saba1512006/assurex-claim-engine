# Assemble the submission folder in the faculty's layout and zip it (Windows PowerShell 5.1 or 7).
#
#   powershell -ExecutionPolicy Bypass -File scripts\make_submission.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\make_submission.ps1 -Destination D:\
#
# Result (default on the Desktop):
#   AssureX-Claim-Engine-Submission\
#     Source_Code\   the project without venv, .git, caches, the local database, .env and the video
#     Documents\     copied from submission\Documents (python reports/build_submission_documents.py)
#     Videos\        Demonstration.mp4 (copied from demo_video\AssureX_Demo.mp4)
#   AssureX-Claim-Engine-Submission.zip

param(
    [string]$Destination = [Environment]::GetFolderPath("Desktop"),
    [string]$Name = "AssureX-Claim-Engine-Submission"
)

$ErrorActionPreference = "Stop"
$project = Split-Path -Parent $PSScriptRoot
$root = Join-Path $Destination $Name
$zip = "$root.zip"

Write-Host "Project : $project"
Write-Host "Output  : $root"

if (Test-Path $root) { Remove-Item -Recurse -Force $root }
if (Test-Path $zip) { Remove-Item -Force $zip }
$src = New-Item -ItemType Directory -Force -Path (Join-Path $root "Source_Code")
$docs = New-Item -ItemType Directory -Force -Path (Join-Path $root "Documents")
$videos = New-Item -ItemType Directory -Force -Path (Join-Path $root "Videos")

# 1. Source code. robocopy exit codes below 8 mean success.
$excludeDirs = @("venv", ".venv", "env", ".git", "__pycache__", ".pytest_cache", "node_modules", "submission",
                 "demo_video", "uploads", ".idea", ".vscode")
$excludeFiles = @(".env", "*.pyc", "*.db", "*.db-journal", "Thumbs.db", "desktop.ini")
robocopy $project $src.FullName /E /NFL /NDL /NJH /NJS /NP /XD $excludeDirs /XF $excludeFiles | Out-Null
if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }
New-Item -ItemType Directory -Force -Path (Join-Path $src.FullName "data\uploads") | Out-Null
Write-Host "Source_Code : copied"

# 2. Documents
$docSource = Join-Path $project "submission\Documents"
if (-not (Test-Path $docSource)) { throw "submission\Documents is missing: run git pull (or python reports/build_submission_documents.py)" }
Copy-Item -Path (Join-Path $docSource "*") -Destination $docs.FullName -Recurse -Force
Write-Host ("Documents   : {0} files" -f (Get-ChildItem $docs.FullName).Count)

# 3. Video
$video = Join-Path $project "demo_video\AssureX_Demo.mp4"
if (Test-Path $video) {
    Copy-Item $video (Join-Path $videos.FullName "Demonstration.mp4")
    Write-Host "Videos      : Demonstration.mp4"
} else {
    Write-Warning "demo_video\AssureX_Demo.mp4 not found: download it from https://github.com/Saba1512006/assurex-claim-engine/blob/demo-video/AssureX_Demo.mp4 and run this script again."
}

# 4. Zip
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($root, $zip, [System.IO.Compression.CompressionLevel]::Optimal, $true)
$sizeMb = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host ""
Write-Host "Done: $zip ($sizeMb MB)"
Write-Host "Upload the zip to Google Drive and share it as 'Anyone with the link - Viewer'."
