$ErrorActionPreference = "Stop"
$api = if ($env:CAOS_API_URL) { $env:CAOS_API_URL } else { "http://localhost:8000" }
$health = Invoke-RestMethod "$api/health"
if ($health.status -ne "ok") { throw "CAOS API health check failed" }
Write-Host "CAOS API is healthy: $($health.service)"
