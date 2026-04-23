param(
  [Parameter(Mandatory = $false)][ValidateSet("test", "compile", "validate-catalog", "build-pattern-index", "build-artifacts", "release", "clean-dist")][string]$Task = "test",
  [string]$Version = "0.1.0"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "..")
$PythonCmd = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

switch ($Task) {
  "test" {
    & $PythonCmd -m unittest discover -s (Join-Path $Root "tests") -p "test_*.py"
  }
  "compile" {
    $files = @(
      "extensions/itx-gates/hooks/orchestrator.py",
      "extensions/itx-gates/hooks/core_orchestrator/base.py",
      "extensions/itx-gates/hooks/core_orchestrator/github_spec_kit.py",
      "extensions/itx-gates/hooks/security_providers/__init__.py",
      "extensions/itx-gates/hooks/security_providers/semgrep_provider.py",
      "extensions/itx-gates/hooks/security_providers/bandit_provider.py",
      "extensions/itx-gates/hooks/security_providers/noop_provider.py",
      "extensions/itx-gates/hooks/validators/__init__.py",
      "extensions/itx-gates/hooks/validators/trading_ast.py",
      "extensions/itx-gates/hooks/validators/banking_heuristic.py",
      "extensions/itx-gates/hooks/validators/sast_validator.py",
      "extensions/itx-gates/hooks/validators/health_regex.py",
      "extensions/itx-gates/hooks/validators/saas_platform_heuristic.py",
      "scripts/validate_catalog.py",
      "scripts/build_catalog_artifacts.py",
      "scripts/build_pattern_index.py",
      "scripts/build_knowledge_manifest.py",
      "scripts/itx_init.py",
      "scripts/itx_specify.py",
      "scripts/release.py",
      "scripts/patch.py",
      "extensions/itx-gates/commands/run_speckit.py",
      "tests/test_orchestrator.py",
      "tests/test_release.py",
      "tests/test_validate_catalog.py",
      "tests/test_itx_init.py",
      "tests/test_patch.py",
      "tests/test_saas_validator.py",
      "tests/test_sast_and_context_router.py",
      "tests/test_itx_gates_runtime_state.py"
    )
    foreach ($f in $files) {
      & $PythonCmd -m py_compile (Join-Path $Root $f)
    }
  }
  "validate-catalog" {
    & $PythonCmd (Join-Path $Root "scripts/validate_catalog.py")
  }
  "build-artifacts" {
    & $PythonCmd (Join-Path $Root "scripts/validate_catalog.py")
    & $PythonCmd (Join-Path $Root "scripts/build_pattern_index.py")
    & $PythonCmd (Join-Path $Root "scripts/build_catalog_artifacts.py")
  }
  "build-pattern-index" {
    & $PythonCmd (Join-Path $Root "scripts/build_pattern_index.py")
  }
  "release" {
    & $PythonCmd (Join-Path $Root "scripts/release.py") --version $Version
  }
  "clean-dist" {
    $dist = Join-Path $Root "dist"
    if (Test-Path $dist) {
      Get-ChildItem -Path $dist -Filter "*.zip" | Remove-Item -Force
    }
  }
}
