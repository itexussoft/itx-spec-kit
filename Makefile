PYTHON ?= python3
VERSION ?= 0.1.0

.PHONY: help test compile validate-catalog build-pattern-index build-artifacts release clean-dist patch

help:
	@echo "Available targets:"
	@echo "  make test              - Run unit tests"
	@echo "  make compile           - Compile Python files for syntax checks"
	@echo "  make validate-catalog  - Validate catalog/manifests consistency"
	@echo "  make build-pattern-index - Generate preset pattern-index.md files"
	@echo "  make build-artifacts   - Build catalog release zips into dist/"
	@echo "  make release VERSION=x.y.z - Bump versions across manifests/catalog"
	@echo "  make patch WORKSPACE=path - Patch an already-bootstrapped project"
	@echo "  make clean-dist        - Remove generated zip artifacts"

test:
	$(PYTHON) -m unittest discover -s tests -p "test_*.py"

compile:
	$(PYTHON) -m py_compile \
		extensions/itx-gates/hooks/orchestrator.py \
		extensions/itx-gates/hooks/validators/__init__.py \
		extensions/itx-gates/hooks/validators/trading_ast.py \
		extensions/itx-gates/hooks/validators/banking_heuristic.py \
		extensions/itx-gates/hooks/validators/health_regex.py \
		extensions/itx-gates/hooks/validators/saas_platform_heuristic.py \
		extensions/itx-gates/commands/run_speckit.py \
		scripts/validate_catalog.py \
		scripts/build_catalog_artifacts.py \
		scripts/build_pattern_index.py \
		scripts/build_knowledge_manifest.py \
		scripts/itx_init.py \
		scripts/itx_specify.py \
		scripts/release.py \
		scripts/patch.py \
		tests/test_orchestrator.py \
		tests/test_release.py \
		tests/test_validate_catalog.py \
		tests/test_itx_init.py \
		tests/test_patch.py \
		tests/test_saas_validator.py

validate-catalog:
	$(PYTHON) scripts/validate_catalog.py

build-pattern-index:
	$(PYTHON) scripts/build_pattern_index.py

build-artifacts: validate-catalog build-pattern-index
	$(PYTHON) scripts/build_catalog_artifacts.py

release:
	$(PYTHON) scripts/release.py --version $(VERSION)

patch:
	@test -n "$(WORKSPACE)" || (echo "Usage: make patch WORKSPACE=/path/to/project" && exit 1)
	$(PYTHON) scripts/patch.py --workspace $(WORKSPACE)

clean-dist:
	rm -f dist/*.zip
