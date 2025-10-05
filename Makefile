# ---- LLM Code Deploy: convenience targets ----
# Tip (Windows): If you don't have GNU Make, you can run these commands directly
# or install make via Chocolatey:  choco install make

.PHONY: setup lint test run-server accept scaffold notify-static notify-dynamic notify-llm

# Install deps from pyproject.toml
setup:
	uv sync --link-mode=copy

# Start the mock Faculty Evaluation Server
run-server:
	uv run uvicorn server.faculty_server:app --reload --port 8088

# Lint & test (optional)
lint:
	uv run ruff check src server tests || true
test:
	uv run pytest -q || true

# CLI helpers
accept:
	uv run python -m src.student_agent.cli accept --sre tests/fixtures/sample_sre.json

scaffold:
	uv run python -m src.student_agent.cli scaffold

# Notify endpoints (override SHA/PAGES via env: make notify-static SHA=dev PAGES=http://example.com)
SHA ?= dev
PAGES ?= http://example.com
BASE ?= http://127.0.0.1:8088

notify-static:
	uv run python -m src.student_agent.cli notify --endpoint $(BASE)/evaluate/static --sha $(SHA) --pages-url $(PAGES)

notify-dynamic:
	uv run python -m src.student_agent.cli notify --endpoint $(BASE)/evaluate/dynamic --sha $(SHA) --pages-url $(PAGES)

notify-llm:
	uv run python -m src.student_agent.cli notify --endpoint $(BASE)/evaluate/llm --sha $(SHA) --pages-url $(PAGES)
