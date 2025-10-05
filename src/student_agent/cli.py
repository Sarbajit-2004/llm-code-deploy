import json
from pathlib import Path
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .verify_sre import verify_sre

console = Console()
ROOT = Path(__file__).resolve().parents[2]  # project root
STATE_DIR = ROOT / ".state"
STATE_DIR.mkdir(parents=True, exist_ok=True)


@click.group()
def cli():
    """Student Agent CLI for SRE-driven deployments."""
    pass


# ──────────────────────────────────────────────────────────────────────────────
# accept: verify and store the SRE
# ──────────────────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--sre", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True,
              help="Path to SRE JSON")
def accept(sre: Path):
    """Verify and accept an SRE (stores a copy under .state/accepted_sre.json)."""
    data = json.loads(sre.read_text(encoding="utf-8"))
    ok, info = verify_sre(data)
    if not ok:
        console.print(f"[red]SRE verification failed:[/red] {info}")
        raise SystemExit(1)

    (STATE_DIR / "accepted_sre.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(Panel.fit("[green]SRE accepted and saved to .state/accepted_sre.json[/green] ✅"))


# ──────────────────────────────────────────────────────────────────────────────
# scaffold: create a minimal repo layout, MIT license, Makefile, and sample app
# ──────────────────────────────────────────────────────────────────────────────
@cli.command()
def scaffold():
    """Scaffold repo structure with MIT license, Makefile, and a tiny web page."""
    app_dir = ROOT / "app"
    docs_dir = ROOT / "docs"
    app_dir.mkdir(exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)

    # .gitignore
    gitignore = ROOT / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "__pycache__/\n*.pyc\n.venv/\n.env\n.state/\nserver/results/\n*.pdf\n*.mp4\n.uv/\n",
            encoding="utf-8",
        )

    # LICENSE (MIT)
    license_file = ROOT / "LICENSE"
    if not license_file.exists():
        license_file.write_text(
            "MIT License\n\nCopyright (c) 2025 Sarbajit "
            "Kumar De\n\nPermission is hereby granted, free of charge, to any person "
            "obtaining a copy of this software and associated documentation files "
            "(the \"Software\"), to deal in the Software without restriction, including "
            "without limitation the rights to use, copy, modify, merge, publish, "
            "distribute, sublicense, and/or sell copies of the Software, and to permit "
            "persons to whom the Software is furnished to do so, subject to the "
            "following conditions:\n\nThe above copyright notice and this permission "
            "notice shall be included in all copies or substantial portions of the "
            "Software.\n\nTHE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY "
            "KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF "
            "MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. "
            "IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY "
            "CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, "
            "TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE "
            "SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.\n",
            encoding="utf-8",
        )

    # Makefile
    makefile = ROOT / "Makefile"
    if not makefile.exists():
        makefile.write_text(
            ".PHONY: setup lint test run-server\n"
            "setup:\n\tuv sync\n"
            "lint:\n\truff check src server tests || true\n"
            "test:\n\tpytest -q || true\n"
            "run-server:\n\tuv run uvicorn server.faculty_server:app --reload --port 8088\n",
            encoding="utf-8",
        )

    # Tiny sample app page for GitHub Pages
    index_html = app_dir / "index.html"
    if not index_html.exists():
        index_html.write_text(
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>LLM Code Deploy — Sample App</title></head>"
            "<body style='font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif'>"
            "<h1>LLM Code Deployment — Sample App</h1>"
            "<p>If you can see this via GitHub Pages, your deploy path works. ✅</p>"
            "</body></html>",
            encoding="utf-8",
        )

    console.print(Panel.fit("[green]Scaffold complete[/green] — created LICENSE, Makefile, app/index.html"))


# ──────────────────────────────────────────────────────────────────────────────
# notify: send commit SHA + Pages URL to evaluator (mock)
# ──────────────────────────────────────────────────────────────────────────────
@cli.command()
@click.option("--endpoint", required=True, help="Faculty notification endpoint, e.g. http://127.0.0.1:8088/evaluate/static")
@click.option("--sha", required=True, help="Commit SHA")
@click.option("--pages-url", required=True, help="GitHub Pages URL")
def notify(endpoint, sha, pages_url):
    """Notify the faculty evaluator with deployment details."""
    try:
        import requests
        payload = {"sha": sha, "pages_url": pages_url}
        r = requests.post(endpoint, json=payload, timeout=10)
        r.raise_for_status()
        console.print(Panel.fit(f"[green]Notified[/green] {endpoint}\nResponse: {r.json()}"))
    except Exception as exc:
        console.print(f"[yellow]Notification attempt failed:[/yellow] {exc}")
        if Confirm.ask("Continue anyway and mark as notified locally?", default=True):
            (STATE_DIR / "last_notify.json").write_text(
                json.dumps({"endpoint": endpoint, "sha": sha, "pages_url": pages_url}, indent=2),
                encoding="utf-8",
            )
            console.print("[green]Saved[/green] .state/last_notify.json")


if __name__ == "__main__":
    cli()
