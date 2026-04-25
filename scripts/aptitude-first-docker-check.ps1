<#
.SYNOPSIS
Runs the fresh Docker sanity check for the Aptitude server/client contract.

.DESCRIPTION
Use this after starting or downloading the server Docker stack for the first
time. The script can start the server stack, seed demo skills, download a
tar.zst artifact from the Aptitude /content endpoint, run the live artifact
contract test, and install a skill from Aptitude into a local demo folder.

.EXAMPLE
.\aptitude-first-docker-check.cmd

.EXAMPLE
.\aptitude-first-docker-check.cmd -NoStartServer

.EXAMPLE
.\aptitude-first-docker-check.cmd -NoStartServer -FullClientTests
#>

param(
    [string]$ServerRoot = "C:\Dev\apptitude-server\aptitude-server",
    [string]$ClientRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
    [string]$BaseUrl = "",
    [string]$ReadToken = "",
    [string]$SkillQuery = "Python Base Runtime",
    [string]$DemoSlug = "python.base",
    [string]$DemoVersion = "1.1.0",
    [string]$PostmanSlug = "postman.primary.1775674127381-77801",
    [string]$PostmanVersion = "1.0.0",
    [string]$OutputRoot = "",
    [switch]$NoStartServer,
    [switch]$NoBuild,
    [switch]$SkipLiveTests,
    [switch]$FullClientTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found on PATH."
    }
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

function Wait-ForReadyz {
    param(
        [string]$Url,
        [int]$Attempts = 60,
        [int]$SleepSeconds = 2
    )

    $readyUrl = "$($Url.TrimEnd('/'))/readyz"
    for ($attempt = 1; $attempt -le $Attempts; $attempt++) {
        try {
            $response = Invoke-WebRequest -Uri $readyUrl -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            if ($attempt -eq $Attempts) {
                throw "Server did not become ready at $readyUrl. Last error: $($_.Exception.Message)"
            }
        }

        Start-Sleep -Seconds $SleepSeconds
    }
}

function Get-HeaderValue {
    param(
        [object]$Headers,
        [string]$Name
    )

    $value = $Headers[$Name]
    if ($null -eq $value) {
        return ""
    }
    if ($value -is [array]) {
        return ($value -join ",")
    }
    return [string]$value
}

function Assert-ZstdMagic {
    param([string]$Path)

    $bytes = [System.IO.File]::ReadAllBytes($Path)
    if ($bytes.Length -lt 4) {
        throw "Artifact is too small to be tar.zst: $Path"
    }

    $actual = $bytes[0..3]
    $expected = [byte[]](0x28, 0xb5, 0x2f, 0xfd)
    for ($i = 0; $i -lt 4; $i++) {
        if ($actual[$i] -ne $expected[$i]) {
            $hex = ($actual | ForEach-Object { $_.ToString("x2") }) -join " "
            throw "Artifact is not zstd. Expected magic '28 b5 2f fd', got '$hex'."
        }
    }
}

$resolvedServerRoot = (Resolve-Path $ServerRoot).Path
$resolvedClientRoot = (Resolve-Path $ClientRoot).Path

if ([string]::IsNullOrWhiteSpace($BaseUrl)) {
    $BaseUrl = if ($env:APTITUDE_SERVER_BASE_URL) { $env:APTITUDE_SERVER_BASE_URL } else { "http://localhost:8000" }
}
if ([string]::IsNullOrWhiteSpace($ReadToken)) {
    $ReadToken = if ($env:APTITUDE_READ_TOKEN) { $env:APTITUDE_READ_TOKEN } else { "reader-token.dev-reader-secret" }
}
if ([string]::IsNullOrWhiteSpace($OutputRoot)) {
    $OutputRoot = Join-Path $resolvedClientRoot "aptitude_download_demo"
}

$runStamp = Get-Date -Format "yyyyMMdd-HHmmss"
$runRoot = Join-Path $OutputRoot $runStamp
$artifactDir = Join-Path $runRoot "server-artifacts"
$installDir = Join-Path $runRoot "installed-from-aptitude"
$artifactPath = Join-Path $artifactDir "$DemoSlug-$DemoVersion.tar.zst"

Require-Command "uv"
Require-Command "docker"

Write-Step "Preparing output folder"
New-Item -ItemType Directory -Force -Path $artifactDir | Out-Null
Write-Host "Output: $runRoot"

if (-not $NoStartServer) {
    Write-Step "Starting Aptitude server Docker stack and seeding demo tar.zst skills"
    Push-Location $resolvedServerRoot
    try {
        $env:APP_ENV = "dev"
        Invoke-Checked "docker" @("compose", "up", "-d", "db")
        if (-not $NoBuild) {
            Invoke-Checked "docker" @("compose", "build", "server")
        }
        Invoke-Checked "docker" @("compose", "run", "--rm", "migrate")
        Invoke-Checked "docker" @("compose", "up", "-d", "server")
        Invoke-Checked "docker" @("compose", "--profile", "demo", "run", "--rm", "demo-seed")
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Step "Using the already-running Aptitude server"
}

Write-Step "Waiting for server readiness"
Wait-ForReadyz -Url $BaseUrl

Write-Step "Downloading a skill artifact directly from Aptitude /content"
$headers = @{
    Authorization = "Bearer $ReadToken"
    Accept = "application/zstd,application/octet-stream,*/*"
}
$contentUrl = "$($BaseUrl.TrimEnd('/'))/skills/$DemoSlug/$DemoVersion/content"
$response = Invoke-WebRequest -Uri $contentUrl -Headers $headers -OutFile $artifactPath -PassThru -UseBasicParsing -TimeoutSec 30
$contentType = Get-HeaderValue -Headers $response.Headers -Name "Content-Type"
Assert-ZstdMagic -Path $artifactPath
Write-Host "Downloaded: $artifactPath"
Write-Host "Content-Type: $contentType"
Write-Host "Zstd magic: 28 b5 2f fd"

Push-Location $resolvedClientRoot
try {
    $env:APTITUDE_SERVER_BASE_URL = $BaseUrl
    $env:APTITUDE_READ_TOKEN = $ReadToken
    $env:APTITUDE_SERVER_TIMEOUT_SECONDS = "10"
    $env:APTITUDE_DEMO_ARTIFACT_SLUG = $DemoSlug
    $env:APTITUDE_DEMO_ARTIFACT_VERSION = $DemoVersion
    $env:APTITUDE_POSTMAN_ARTIFACT_SLUG = $PostmanSlug
    $env:APTITUDE_POSTMAN_ARTIFACT_VERSION = $PostmanVersion
    $env:UV_CACHE_DIR = ".uv-cache"

    if (-not $SkipLiveTests) {
        Write-Step "Running the live artifact contract test"
        Invoke-Checked "uv" @(
            "run", "--extra", "dev", "python", "-m", "pytest",
            "tests\integration\registry\test_postman_artifact_contract.py",
            "-vv"
        )
    }

    Write-Step "Installing a skill from Aptitude into the demo output folder"
    Invoke-Checked "uv" @(
        "run", "aptitude", "install", $SkillQuery,
        "--target", $installDir,
        "--interaction-mode", "never",
        "--json"
    )

    if ($FullClientTests) {
        Write-Step "Running full client verification"
        Invoke-Checked "uv" @("run", "--extra", "dev", "python", "-m", "pytest")
        Invoke-Checked "uv" @("run", "--extra", "dev", "ruff", "check", "src", "tests")
        Invoke-Checked "uv" @("run", "--extra", "dev", "python", "-m", "mypy", "src", "tests")
    }
}
finally {
    Pop-Location
}

Write-Step "Done"
Write-Host "Raw server artifact: $artifactPath"
Write-Host "Installed skill folder: $installDir"
Write-Host "This download came from Aptitude server at $BaseUrl, not GitHub."
