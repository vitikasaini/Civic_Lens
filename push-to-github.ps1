param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUser,

    [Parameter(Mandatory=$true)]
    [string]$PatToken
)

# -----------------------------------------------------------------
# 1️⃣ Allow the script to run even if the default policy is restrictive
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force

# -----------------------------------------------------------------
# 2️⃣ Clean previous build artefacts & rebuild the frontend
Remove-Item -Recurse -Force .\frontend\dist
npm ci
npm run build

# -----------------------------------------------------------------
# 3️⃣ Initialise Git (if the repo is not already a Git repo)
git init
git add .

# -----------------------------------------------------------------
# 4️⃣ Commit with a safe, ASCII‑only message
git commit -m 'Initial commit - ready for GitHub'

# -----------------------------------------------------------------
# 5️⃣ Add the remote using the supplied PAT (the token is **not** stored)
git remote add origin https://$PatToken@github.com/$GitHubUser/civicLens.git

# -----------------------------------------------------------------
# 6️⃣ Push to GitHub
git branch -M main
git push -u origin main