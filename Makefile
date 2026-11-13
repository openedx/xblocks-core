.DEFAULT_GOAL := help

.PHONY: upgrade help requirements quality format test docs
.PHONY: extract_translations

REPO_ROOT := $(shell pwd)
SRC_DIR := src
EXTRACT_DIR := conf/locale/en/LC_MESSAGES

help:
	@perl -nle'print $& if m{^[\.a-zA-Z_-]+:.*?## .*$$}' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m  %-25s\033[0m %s\n", $$1, $$2}'

quality: ## run quality checks
	tox -e quality

format: ## auto-fix ruff lint and formatting issues
	uv run ruff check --fix .
	uv run ruff format .

test: ## run tests against all supported Python/Django combinations
	tox -e "py312-django{42,52}"

docs: ## build documentation
	tox -e docs

upgrade: ## update uv.lock and regenerate uv constraints from edx-lint
	uv run --with edx-lint edx_lint write_uv_constraints pyproject.toml
	uv lock --upgrade

requirements: ## install development environment requirements using uv
	uv sync --group dev
	uv tool install tox --with tox-uv

# XBlock directories: each src/xblock_<name>/ that has its own conf/ subdir
XBLOCKS=$(shell find $(REPO_ROOT)/$(SRC_DIR) -mindepth 2 -maxdepth 2 -type d -name 'conf' -exec dirname {} \;)

## Localization targets

extract_translations: ## extract strings to be translated, outputting .po files under <module_name>/conf/locale/
	@for xblock in $(XBLOCKS); do \
		module_name=$$(basename $$xblock); \
		echo "Extracting translations for $$module_name..."; \
		cd $$xblock && i18n_tool extract --no-segment; \
		if [ -f $$xblock/$(EXTRACT_DIR)/djangojs.po ]; then \
			msgcat $$xblock/$(EXTRACT_DIR)/django.po $$xblock/$(EXTRACT_DIR)/djangojs.po \
				-o $$xblock/$(EXTRACT_DIR)/django.po && rm -f $$xblock/$(EXTRACT_DIR)/djangojs.po; \
		fi; \
		mkdir -p $(REPO_ROOT)/$$module_name/$(EXTRACT_DIR); \
		if [ -f $$xblock/$(EXTRACT_DIR)/django.po ]; then \
			mv $$xblock/$(EXTRACT_DIR)/django.po $(REPO_ROOT)/$$module_name/$(EXTRACT_DIR)/django.po; \
		fi; \
	done

selfcheck: ## check that the Makefile is well-formed
	@echo "The Makefile is well-formed."
