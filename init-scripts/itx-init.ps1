param(
  [Parameter(ValueFromRemainingArguments = $true)][string[]]$PassthroughArgs
)

$ErrorActionPreference = "Stop"
$KitRoot = Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")
$PythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

& $PythonCmd (Join-Path $KitRoot "scripts/itx_init.py") @PassthroughArgs
exit $LASTEXITCODE
