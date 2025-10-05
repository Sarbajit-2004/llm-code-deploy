# LLM Code Deployment — Student Agent & Mock Evaluator

Deterministic, CLI-first workflow to accept a Signed Request Envelope (SRE), scaffold a minimal repo (MIT + Makefile + static `/app`), and notify a mock faculty evaluator (FastAPI). Targets a public GitHub Pages deploy in later steps.

---

## Requirements
- Python **3.10+**
- [`uv`](https://github.com/astral-sh/uv) installed and on PATH
- Git
- (Optional) VS Code

> On Windows with paths containing spaces (e.g., `Project 1`), always quote the path in commands.

---

## Quick Start

### 1) Create venv & install deps
```powershell
# From the project root (e.g., D:\Project 1\llm-code-deploy)
uv venv --clear
uv sync --link-mode=copy
