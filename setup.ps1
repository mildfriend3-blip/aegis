<#
  AEGIS — one-shot setup and run for Windows (PowerShell).

  Quickest (paste both lines — the first fixes TLS on older PowerShell):

      [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
      irm https://raw.githubusercontent.com/mildfriend3-blip/aegis/main/setup.ps1 | iex

  Or clone and run it locally (most reliable):

      git clone https://github.com/mildfriend3-blip/aegis.git
      cd aegis
      .\setup.ps1

  It will, in order:
    1. fetch the current code (update the checkout, or clone it)
    2. create a virtual environment and install AEGIS into it
    3. check that Ollama is installed, running, and has the model
    4. check that the model actually supports tool calling
    5. run the guarded benchmark against it

  No API key, no account, nothing installed outside this folder. Use a different
  local model with:   .\setup.ps1 -Model llama3.1:8b
#>
param(
    [string]$Model = "qwen3:8b"
)

$ErrorActionPreference = "Stop"

function Say($m)  { Write-Host "==> $m" -ForegroundColor Cyan }
function Warn($m) { Write-Host "!!  $m" -ForegroundColor Yellow }
function Die($m)  { Write-Host "xx  $m" -ForegroundColor Red; throw $m }

$RepoUrl = "https://github.com/mildfriend3-blip/aegis.git"

# --- where are we? ------------------------------------------------------
if ($PSScriptRoot) { $start = $PSScriptRoot } else { $start = (Get-Location).Path }
if ((Test-Path (Join-Path $start "pyproject.toml")) -and (Test-Path (Join-Path $start "aegis"))) {
    $Dir = $start                                   # already inside the repo
} else {
    $Dir = Join-Path $start "aegis"                 # clone into ./aegis
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Die "Git is not installed. Get it from https://git-scm.com/download/win and re-run."
}

# --- 1. current code ----------------------------------------------------
if (Test-Path (Join-Path $Dir ".git")) {
    Say "Updating the checkout in $Dir"
    Push-Location $Dir
    git pull --ff-only
    Pop-Location
} elseif (Test-Path (Join-Path $Dir "pyproject.toml")) {
    Say "Using the AEGIS folder in $Dir"
} else {
    Say "Cloning AEGIS into $Dir"
    git clone $RepoUrl $Dir
}
Set-Location $Dir

# --- 2. python + venv + install ----------------------------------------
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Die "Python is not on PATH. Install it from https://python.org (tick 'Add python.exe to PATH') and re-run."
}

$Py = Join-Path $Dir ".venv\Scripts\python.exe"
if (-not (Test-Path $Py)) {
    Say "Creating a virtual environment (.venv)"
    python -m venv .venv
}

Say "Installing AEGIS into the virtual environment"
& $Py -m pip install --upgrade pip
& $Py -m pip install -e '.[dev]'
if ($LASTEXITCODE -ne 0) { Die "Install failed. Scroll up for the pip error." }

# --- 3. ollama present and running -------------------------------------
Say "Checking Ollama"
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Die "Ollama is not installed. Get it from https://ollama.com/download, then re-run."
}
try {
    Invoke-RestMethod "http://localhost:11434/api/tags" -TimeoutSec 5 | Out-Null
} catch {
    Die "Ollama is installed but not answering on port 11434. Start it from the Start menu (or run 'ollama serve'), then re-run."
}

# --- 4. model present, and tool-capable --------------------------------
$have = @()
try { $have = (Invoke-RestMethod "http://localhost:11434/api/tags").models.name } catch {}
if (-not ($have | Where-Object { $_ -eq $Model -or $_ -like "$Model*" })) {
    Say "Pulling $Model (first run only — this can take a few minutes)"
    ollama pull $Model
}

Say "Checking that $Model supports tool calling"
try {
    $show = Invoke-RestMethod "http://localhost:11434/api/show" -Method Post `
            -ContentType "application/json" -Body (@{ model = $Model } | ConvertTo-Json)
} catch {
    Die "Could not read the model's capabilities from Ollama."
}
if (-not ($show.capabilities -contains "tools")) {
    Warn "$Model does not advertise tool calling, so it will answer in prose and the"
    Warn "benchmark would be meaningless. Try one of these instead:"
    Warn "    .\setup.ps1 -Model qwen3:8b"
    Warn "    .\setup.ps1 -Model llama3.1:8b"
    Warn "    .\setup.ps1 -Model llama3-groq-tool-use:8b"
    Warn "The full list is at https://ollama.com/search"
    Die "$Model is not tool-capable."
}

# --- 5. run -------------------------------------------------------------
$env:AEGIS_OPENAI_API_KEY  = "ollama"
$env:AEGIS_OPENAI_BASE_URL = "http://localhost:11434/v1"
$env:AEGIS_OPENAI_MODEL    = $Model

Say "Running the guarded benchmark against $Model"
Write-Host ""
& $Py -m aegis.cli guarded --target openai --verbose
Write-Host ""
Say "Done. Read 'tool calls proposed' above — if it is 0, the model is not calling tools."
Say "Next:  aegis guard --simulate   (the always-on defender)   or   aegis run  (the benchmark)"
