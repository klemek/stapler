# ENV

UV ?= uv

ifeq (, $(shell which uv))
	UV ?= python3 -m uv
endif

RUFF ?= $(UV) run --active ruff
TY ?= $(UV) run --active ty
DOCKER ?= docker
DOCKER_TAG ?= localhost/stapler:latest
TOKEN ?= secret
PORT ?= 8080

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
	@$(UV) sync --active

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

.PHONY: docker-build
docker-build: ## docker build
	@$(DOCKER) build . -t $(DOCKER_TAG)

.PHONY: docker-run
docker-run: docker-build ## docker run
	@$(DOCKER) run -it -p $(PORT):8080 -v ./data:/data $(DOCKER_TAG) --token $(TOKEN)

# ACTIONS

.PHONY: format
format: ruff-fix ruff-format ## format project

.PHONY: lint
lint: ruff ruff-format-check ty ## lint project

.PHONY: build
build: docker-build ## build project

.PHONY: start
start: build docker-run ## start server in localhost
