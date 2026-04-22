# ==================================================================================== #
# VARIABLES
# ==================================================================================== #

# Makefile Colors
PURPLE := \033[95m
BLUE := \033[94m
CYAN := \033[96m
GREEN := \033[92m
ORANGE := \033[93m
RED := \033[91m
ENDC := \033[0m
BOLD := \033[1m
UNDERLINE := \033[4m

# ==================================================================================== #
# HELPERS & CHECKS
# ==================================================================================== #

.PHONY: help
help:
	@echo "$(BOLD)eo-maxar-example$(ENDC)"
	@echo ""
	@echo "$(BOLD)First-time setup:$(ENDC)"
	@echo "  $(CYAN)make init$(ENDC)          Build images, start services, install deps, load data"
	@echo ""
	@echo "$(BOLD)Returning to the project:$(ENDC)"
	@echo "  $(CYAN)make start$(ENDC)         Start existing services (no rebuild, no data load)"
	@echo "  $(CYAN)make stop$(ENDC)          Stop services without removing them"
	@echo "  $(CYAN)make down$(ENDC)          Stop and remove services"
	@echo ""
	@echo "$(BOLD)Development:$(ENDC)"
	@echo "  $(CYAN)make install$(ENDC)       Sync deps and install pre-commit hooks"
	@echo "  $(CYAN)make test$(ENDC)          Run the test suite"
	@echo "  $(CYAN)make check$(ENDC)         Run all code quality checks"
	@echo "  $(CYAN)make ps$(ENDC)            Show status of running services"
	@echo "  $(CYAN)make logs$(ENDC)          Tail logs from all services"
	@echo "  $(CYAN)make logs SERVICE=x$(ENDC) Tail logs from a specific service"
	@echo ""
	@echo "$(BOLD)Maintenance:$(ENDC)"
	@echo "  $(CYAN)make build$(ENDC)         Rebuild all Docker images"
	@echo "  $(CYAN)make build-browser$(ENDC) Rebuild only the STAC browser image"
	@echo "  $(CYAN)make rebuild$(ENDC)       Full teardown and reinitialise"
	@echo "  $(CYAN)make clean$(ENDC)         Stop services and remove all build artifacts"

.PHONY: check-env
check-env:
	@if ! command -v docker &> /dev/null; then \
		echo "$(RED)Error: docker is not installed. Please install Docker to continue.$(ENDC)"; \
		exit 1; \
	fi
	@if ! docker info >/dev/null 2>&1; then \
		echo "$(RED)Error: Docker daemon is not running. Please start Docker Desktop and try again.$(ENDC)"; \
		exit 1; \
	fi
	@if ! command -v uv &> /dev/null; then \
		echo "$(RED)Error: uv is not installed. Please install uv to continue (pip install uv).$(ENDC)"; \
		exit 1; \
	fi

# ==================================================================================== #
# PROJECT LIFECYCLE & SETUP
# ==================================================================================== #

.PHONY: init
init: check-env build install setup-db
	@echo "$(PURPLE)--- Project Initialized Successfully! ---$(ENDC)"
	@echo "$(CYAN)Explore the STAC Browser at http://localhost:8085$(ENDC)"
	@echo "$(CYAN)To start using the notebook, run: source .venv/bin/activate$(ENDC)"

.PHONY: start
start: check-env
	@echo "$(PURPLE)--- Starting Services ---$(ENDC)"
	@docker compose up -d
	@echo "$(GREEN)Services running. STAC Browser: http://localhost:8085$(ENDC)"

.PHONY: stop
stop:
	@echo "$(PURPLE)--- Stopping Services ---$(ENDC)"
	@docker compose stop
	@echo "$(GREEN)Services stopped (containers preserved).$(ENDC)"

.PHONY: up
up: check-env
	@echo "$(PURPLE)--- Starting Docker Services ---$(ENDC)"
	@docker compose up -d
	@echo "$(GREEN)Services are running in detached mode.$(ENDC)"

.PHONY: setup-db
setup-db:
	@echo "$(PURPLE)--- Setting up Database ---$(ENDC)"
	@echo "$(BLUE) > Loading data into pgSTAC... This may take a moment.$(ENDC)"
	@uv run setup
	@echo "$(GREEN)Database setup complete.$(ENDC)"

.PHONY: down
down:
	@echo "$(PURPLE)--- Stopping Docker Services ---$(ENDC)"
	@docker compose down
	@echo "$(GREEN)Services stopped.$(ENDC)"

.PHONY: ps
ps:
	@docker compose ps

.PHONY: logs
logs:
	@echo "$(PURPLE)--- Tailing Logs (Press Ctrl+C to stop) ---$(ENDC)"
	@docker compose logs -f $(SERVICE)

.PHONY: build
build: check-env
	@echo "$(PURPLE)--- Building Docker Images ---$(ENDC)"
	@docker compose build
	@docker compose up -d
	@echo "$(GREEN)Images rebuilt and services started.$(ENDC)"

.PHONY: build-browser
build-browser: check-env
	@echo "$(PURPLE)--- Rebuilding STAC Browser Image ---$(ENDC)"
	@docker compose build stac-browser
	@docker compose up -d stac-browser
	@echo "$(GREEN)STAC Browser rebuilt. Visit http://localhost:8085$(ENDC)"

.PHONY: rebuild
rebuild: clean init
	@echo "$(GREEN)Project rebuilt successfully!$(ENDC)"


# ==================================================================================== #
# DEVELOPMENT & QA
# ==================================================================================== #

.PHONY: install
install: check-env
	@echo "$(PURPLE)--- Installing Environment ---$(ENDC)"
	@echo "$(BLUE) > Creating virtual environment and syncing dependencies...$(ENDC)"
	@uv sync --all-groups
	@echo "$(BLUE) > Installing pre-commit hooks...$(ENDC)"
	@uvx pre-commit install
	@echo "$(GREEN)Install complete! Activate with: source .venv/bin/activate$(ENDC)"

.PHONY: test
test:
	@echo "$(PURPLE)--- Running Tests ---$(ENDC)"
	@uv run pytest tests/ -v
	@echo "$(GREEN)Tests complete.$(ENDC)"

.PHONY: check
check:
	@echo "$(PURPLE)--- Running Code Quality Checks ---$(ENDC)"
	@echo "$(BLUE) > Checking lock file...$(ENDC)"
	@uv lock --locked
	@echo "$(BLUE) > Linting code with pre-commit...$(ENDC)"
	@uvx pre-commit run -a
	@echo "$(BLUE) > Static type checking with pyrefly...$(ENDC)"
	@uv run pyrefly check
	@echo "$(BLUE) > Running noxfile...$(ENDC)"
	@uvx nox
	@echo "$(GREEN)All checks passed!$(ENDC)"

# ==================================================================================== #
# HOUSEKEEPING
# ==================================================================================== #

.PHONY: clean
clean: down
	@echo "$(PURPLE)--- Cleaning Project ---$(ENDC)"
	@echo "$(BLUE) > Removing Docker volumes, build artifacts, and caches...$(ENDC)"
	@rm -rf .pgdata dist .pytest_cache .ruff_cache
	@echo "$(GREEN)Clean complete.$(ENDC)"
