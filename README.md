<#
.SYNOPSIS
    Builds the React frontend, commits the repo, and pushes to GitHub.
.PARAMETER GitHubUser
    Your GitHub username or organization name.
.PARAMETER PatToken
    A personal access token (PAT) with `repo` scope.
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUser,

    [Parameter(Mandatory=$true)]
    [string]$PatToken
)

# -------------------------------------------------
# 1️⃣  Allow this script to run even if the default
#      execution policy is restrictive (only for this session)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# -------------------------------------------------
# 2️⃣  -----------------------------------------------------------------
#    Clean any previous build artefacts and rebuild the frontend
# -----------------------------------------------------------------
Write-Host "🔧  Cleaning previous build artefacts…" -ForegroundColor Cyan
Remove-Item -Recurse -Force .\frontend\dist  -ErrorAction SilentlyContinue

Write-Host "📦  Installing frontend dependencies…" -ForegroundColor Cyan
Push-Location .\frontend
# First run `npm install` – it creates package‑lock.json if missing
npm install
# Now a clean install can be done with `npm ci` (optional)
# npm ci
Write-Host "🚀  Building the React app…" -ForegroundColor Cyan
npm run build
Pop-Location

# -------------------------------------------------
# 3️⃣  Initialise / update the git repo (if not already)
if (-not (Test-Path .git)) {
    git init
}
git add .
git status   # just to show what will be committed

# -------------------------------------------------
# 4️⃣  Commit with a safe ASCII‑only message
git commit -m 'Initial commit - ready for GitHub' `
    -ErrorAction SilentlyContinue   # ignore if there is nothing new

# -------------------------------------------------
# 5️⃣  Set (or replace) the remote URL – use the exact repo name you created
$remoteUrl = "https://$PatToken@github.com/$GitHubUser/Civic_Lens.git"
git remote remove origin 2>$null   # ignore error if remote does not exist
git remote add origin $remoteUrl

# -------------------------------------------------
# 6️⃣  Push to GitHub (force‑push only if the remote is empty)
Write-Host "📤  Pushing to GitHub…" -ForegroundColor Cyan
git branch -M main
git push -u origin main