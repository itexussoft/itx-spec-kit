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
      "extensions/itx-gates/hooks/architecture_runner.py",
      "extensions/itx-gates/hooks/rule_to_pattern_mapper.py",
      "extensions/itx-gates/hooks/architecture_adapters/__init__.py",
      "extensions/itx-gates/hooks/architecture_adapters/generic_command_adapter.py",
      "extensions/itx-gates/hooks/architecture_adapters/spectral_adapter.py",
      "extensions/itx-gates/hooks/architecture_adapters/archunit_adapter.py",
      "extensions/itx-gates/hooks/architecture_adapters/modulith_adapter.py",
      "extensions/itx-gates/hooks/architecture_parsers/__init__.py",
      "extensions/itx-gates/hooks/architecture_parsers/sarif.py",
      "extensions/itx-gates/hooks/architecture_parsers/junit_xml.py",
      "extensions/itx-gates/hooks/architecture_parsers/jsonpath.py",
      "extensions/itx-gates/hooks/mutation_runner.py",
      "extensions/itx-gates/hooks/mutation_remediation.py",
      "extensions/itx-gates/hooks/smell_mapping.py",
      "extensions/itx-gates/hooks/mutation_adapters/__init__.py",
      "extensions/itx-gates/hooks/mutation_adapters/generic_command_adapter.py",
      "extensions/itx-gates/hooks/mutation_adapters/stryker_adapter.py",
      "extensions/itx-gates/hooks/mutation_adapters/pitest_adapter.py",
      "extensions/itx-gates/hooks/mutation_adapters/cargo_mutants_adapter.py",
      "extensions/itx-gates/hooks/mutation_adapters/python_adapter.py",
      "extensions/itx-gates/hooks/validators/__init__.py",
      "extensions/itx-gates/hooks/validators/trading_ast.py",
      "extensions/itx-gates/hooks/validators/banking_heuristic.py",
      "extensions/itx-gates/hooks/validators/sast_validator.py",
      "extensions/itx-gates/hooks/validators/health_regex.py",
      "extensions/itx-gates/hooks/validators/saas_platform_heuristic.py",
      "harnesses/temporal-fakes/example-fake/fake_deployment.py",
      "harnesses/temporal-fakes/example-fake/contract_test.py",
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
      "tests/test_architecture_wave_f.py",
      "tests/test_mutation_wave_g.py",
      "tests/test_smell_mapping_h1.py",
      "tests/test_temporal_fakes_h2.py",
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
