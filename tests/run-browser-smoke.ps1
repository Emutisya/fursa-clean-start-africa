$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$run = Join-Path $root (".browser-check\run-" + [guid]::NewGuid().ToString("N"))
$profile = Join-Path $run "profile"
$serverLog = Join-Path $run "server.log"
$serverErrors = Join-Path $run "server-errors.log"
$server = $null
$browser = $null
New-Item -ItemType Directory -Path $profile -Force | Out-Null
function Wait-FileContent($path, $pattern) {
    for ($attempt = 0; $attempt -lt 100; $attempt++) {
        if (Test-Path $path) {
            $text = Get-Content $path -Raw
            if ($text -match $pattern) { return $Matches[0] }
        }
        Start-Sleep -Milliseconds 100
    }
    throw "Timed out waiting for isolated smoke-test endpoint: $path"
}
function Stop-OwnedTree($process) {
    if ($null -eq $process) { return }
    $ids = [System.Collections.Generic.List[int]]::new()
    $ids.Add($process.Id)
    $snapshot = @(Get-CimInstance Win32_Process | Select-Object ProcessId, ParentProcessId)
    for ($index = 0; $index -lt $ids.Count; $index++) {
        foreach ($child in $snapshot | Where-Object ParentProcessId -EQ $ids[$index]) {
            if (-not $ids.Contains([int]$child.ProcessId)) { $ids.Add([int]$child.ProcessId) }
        }
    }
    for ($index = $ids.Count - 1; $index -ge 0; $index--) {
        Stop-Process -Id $ids[$index] -Force -ErrorAction SilentlyContinue
    }
}
try {
    $edge = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $edge) { throw "Installed Microsoft Edge is required; no browser is downloaded." }
    $server = Start-Process -FilePath (Get-Command python).Source -ArgumentList "-m", "fursa", "serve", "--port", "0" -WorkingDirectory $root -RedirectStandardOutput $serverLog -RedirectStandardError $serverErrors -PassThru
    $app = Wait-FileContent $serverLog 'http://127\.0\.0\.1:\d+'
    $health = Invoke-RestMethod "$app/api/health"
    if ($health.status -ne "ok") { throw "Isolated model server is not ready." }
    $browser = Start-Process -FilePath $edge -ArgumentList "--headless=new", "--remote-debugging-port=0", "--remote-debugging-address=127.0.0.1", "--user-data-dir=`"$profile`"", "--no-first-run", "--no-default-browser-check", "about:blank" -PassThru
    $port = Wait-FileContent (Join-Path $profile "DevToolsActivePort") '^\d+'
    $debugger = "http://127.0.0.1:$port"
    $null = Invoke-RestMethod "$debugger/json/version"
    & node (Join-Path $PSScriptRoot "browser-smoke.mjs") $app $debugger (Join-Path $run "exports")
    if ($LASTEXITCODE -ne 0) { throw "Browser smoke checks failed." }
}
finally {
    Stop-OwnedTree $browser
    Stop-OwnedTree $server
    Remove-Item $run -Recurse -Force -ErrorAction SilentlyContinue
}
