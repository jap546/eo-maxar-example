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
init: check-env up install setup-db
	@echo "$(PURPLE)--- Project Initialized Successfully! ---$(ENDC)"
	@echo "$(CYAN)Explore the STAC Browser at http://localhost:8085$(ENDC)"
	@echo "$(CYAN)To start using the notebook, run: source .venv/bin/activate$(ENDC)"

.PHONY: up
up: check-env
	@echo "$(PURPLE)--- Starting Docker Services ---$(ENDC)"
	@docker compose up -d
	@echo "$(GREEN)✅ Services are running in detached mode.$(ENDC)"

.PHONY: setup-db
setup-db:
	@echo "$(PURPLE)--- Setting up Database ---$(ENDC)"
	@echo "$(BLUE) > Loading data into pgSTAC... This may take a moment.$(ENDC)"
	@uv run setup
	@echo "$(GREEN)✅ Database setup complete.$(ENDC)"

.PHONY: down
down:
	@echo "$(PURPLE)--- Stopping Docker Services ---$(ENDC)"
	@docker compose down
	@echo "$(GREEN)✅ Services stopped.$(ENDC)"

.PHONY: logs
logs:
	@echo "$(PURPLE)--- Tailing Logs (Press Ctrl+C to stop) ---$(ENDC)"
	@docker compose logs -f

.PHONY: rebuild
rebuild: clean init
	@echo "$(GREEN)✅ Project rebuilt successfully!$(ENDC)"


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
	@echo "$(GREEN)✅ Install complete! Activate with: source .venv/bin/activate$(ENDC)"

.PHONY: check
check:
	@echo "$(PURPLE)--- 🧐 Running Code Quality Checks ---$(ENDC)"
	@echo "$(BLUE) > Checking lock file...$(ENDC)"
	@uv lock --locked
	@echo "$(BLUE) > Linting code with pre-commit...$(ENDC)"
	@uvx pre-commit run -a
	@echo "$(BLUE) > Static type checking with mypy...$(ENDC)"
	@uvx mypy --config-file .github/linters/.mypy.ini .
	@echo "$(BLUE) > Running noxfile...$(ENDC)"
	@uvx nox
	@echo "$GREEN)✅ All checks passed!$(ENDC)"

# ==================================================================================== #
# HOUSEKEEPING
# ==================================================================================== #

.PHONY: clean
clean: down ## Stop services and remove all build artifacts and data.
	@echo "$(PURPLE)--- 🧹 Cleaning Project ---$(ENDC)"
	@echo "$(BLUE) > Removing Docker volumes, build artifacts, and caches...$(ENDC)"
	@rm -rf .pgdata dist .mypy_cache .pytest_cache .ruff_cache
	@echo "$(GREEN)✅ Clean complete.$(ENDC)"

.PHONY: help
help: ## 🙋 Display this help message.
	@echo "$(BOLD)Makefile Commands:$(ENDC)"
	@uvx python -c "import re; \
	[[print(f'  {m[0].replace(':', '')[:20]:<22} {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
