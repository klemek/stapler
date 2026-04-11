# ENV

UV ?= uv

ifeq (, $(shell which uv))
	UV ?= python3 -m uv
endif

RUFF ?= $(UV) run ruff
TY ?= $(UV) run ty

# DOCS

.PHONY: help
help: ## show this message
	@echo "Usage: make [target1] (target2) ..."
	@echo ""
	@echo "Commands/Targets:"
	@grep -E '(^[a-zA-Z0-9_%-]+:.*?##.*$$)|(^##)' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}{printf "\033[32m%-20s\033[0m %s\n", $$1, $$2}' | sed -e 's/\[32m##/[33m/'
	@echo ""
	@echo "Environment:"
	@grep -E '^[a-zA-Z0-9_-]+\s*[?:]?=.*$$' $(MAKEFILE_LIST) | grep -Eo '^[a-zA-Z0-9_-]+' | xargs -I {} make -s print-{}

.PHONY: print-%
print-%:
	@echo -e '\033[32m$*\033[0m = $($*)'

# FILES

.venv: uv.lock
	@$(UV) sync

# TOOLS

.PHONY: ruff
ruff: .venv ## ruff check
	@$(RUFF) check

.PHONY: ruff-fix
ruff-fix: .venv ## ruff check (and fix)
	@$(RUFF) check --fix --unsafe-fixes

.PHONY: ruff-format
ruff-format: .venv ## ruff format
	@$(RUFF) format

.PHONY: ruff-format-check
ruff-format-check: .venv ## ruff format (check only)
	@$(RUFF) format --check

.PHONY: ty
ty: .venv ## ty check
	@$(TY) check

# ACTIONS

.PHONY: format
format: ruff-fix ruff-format ## format project

.PHONY: lint
lint: ruff ruff-format-check ty ## lint project