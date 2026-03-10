$ErrorActionPreference = "Stop"
$nodeRoot = Split-Path (Get-Command npx -ErrorAction Stop).Source -Parent
$npm = Join-Path $nodeRoot 'npm.cmd'
$npx = Join-Path $nodeRoot 'npx.cmd'
& $npm install
& $npx playwright install chromium
