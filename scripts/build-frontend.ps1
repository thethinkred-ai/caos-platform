$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$frontend = Join-Path $root "frontend"
$env:VITE_API_URL = if ($env:VITE_API_URL) { $env:VITE_API_URL } else { "https://api-caos.thinkred.ru/api/v1" }
npm --prefix $frontend ci
npm --prefix $frontend run build
Write-Host "Upload $frontend\dist to the TimeWeb document root for caos.thinkred.ru"
