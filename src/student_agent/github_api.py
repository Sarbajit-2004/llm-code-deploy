from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

import requests
from rich.console import Console

console = Console()
ROOT = Path(__file__).resolve().parents[2]
GITHUB_API = "https://api.github.com"


# ──────────────────────────────────────────────────────────────────────────────
# Utilities
# ──────────────────────────────────────────────────────────────────────────────
def _run(cmd: list[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess:
    """Run a command and raise on failure; prints trimmed stdout/stderr for context."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed: {' '.join(cmd)}\n"
            f"STDOUT:\n{proc.stdout}\n"
            f"STDERR:\n{proc.stderr}"
        )
    return proc


def _git(*args: str) -> subprocess.CompletedProcess:
    return _run(["git", *args], cwd=ROOT)


def _headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",  # works for both classic & fine-grained PATs
        "Accept": "application/vnd.github+json",
        "User-Agent": "llm-code-deploy-student-agent",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _load_env_file(path: Path) -> None:
    """
    Lightweight .env loader that OVERRIDES existing env vars.
    This makes .env the source of truth for local runs.
    """
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()


@dataclass
class GHConfig:
    token: str
    user: str
    repo: str
    branch: str = "main"
    pages_build_dir: str = "docs"   # default to /docs (valid Pages source)
    cname: Optional[str] = None

    @classmethod
    def from_env(cls) -> "GHConfig":
        _load_env_file(ROOT / ".env")  # allow values from .env
        token = os.getenv("GITHUB_TOKEN", "").strip()
        user = os.getenv("GITHUB_USER", "").strip()
        repo = os.getenv("GITHUB_REPO", "").strip()
        branch = os.getenv("GITHUB_DEFAULT_BRANCH", "main").strip()
        pages_build_dir = os.getenv("PAGES_BUILD_DIR", "docs").strip()
        cname = os.getenv("PAGES_CNAME", "").strip() or None

        missing = [
            k for k, v in {
                "GITHUB_TOKEN": token,
                "GITHUB_USER": user,
                "GITHUB_REPO": repo,
            }.items() if not v
        ]
        if missing:
            raise ValueError(
                f"Missing env vars: {', '.join(missing)} (set them in .env)"
            )

        return cls(
            token=token,
            user=user,
            repo=repo,
            branch=branch,
            pages_build_dir=pages_build_dir,
            cname=cname,
        )


# ──────────────────────────────────────────────────────────────────────────────
# GitHub API helpers
# ──────────────────────────────────────────────────────────────────────────────
def create_repo_if_missing(cfg: GHConfig) -> Dict[str, Any]:
    """Create repo under the authenticated user if it doesn't exist."""
    s = requests.Session()
    s.headers.update(_headers(cfg.token))

    r = s.get(f"{GITHUB_API}/repos/{cfg.user}/{cfg.repo}", timeout=20)
    if r.status_code == 200:
        return r.json()

    if r.status_code != 404:
        raise RuntimeError(f"Failed to check repo: {r.status_code} {r.text}")

    payload = {
        "name": cfg.repo,
        "private": False,
        "has_issues": True,
        "has_projects": False,
        "has_wiki": False,
    }
    r = s.post(f"{GITHUB_API}/user/repos", json=payload, timeout=30)
    if r.status_code not in (201, 202):
        raise RuntimeError(f"Create repo failed: {r.status_code} {r.text}")
    return r.json()


def ensure_git_identity() -> None:
    """Set a basic git identity if missing."""
    try:
        _git("config", "--get", "user.email")
    except Exception:
        _git("config", "user.email", "you@example.com")
        _git("config", "user.name", "Student Agent")


def ensure_branch(branch: str) -> None:
    """Ensure the working branch exists and is checked out."""
    try:
        _git("rev-parse", "--verify", branch)
        _git("checkout", branch)
    except Exception:
        _git("checkout", "-b", branch)


def ensure_remote_origin(cfg: GHConfig) -> None:
    """Configure 'origin' remote using token auth."""
    remote_url = f"https://{cfg.user}:{cfg.token}@github.com/{cfg.user}/{cfg.repo}.git"
    try:
        _git("remote", "set-url", "origin", remote_url)
    except Exception:
        _git("remote", "add", "origin", remote_url)


def initial_commit_if_needed(msg: str = "chore: initial commit") -> None:
    try:
        _git("rev-parse", "--verify", "HEAD")
        # Already committed; nothing to do
    except Exception:
        _git("add", "-A")
        _git("commit", "-m", msg)


def push_branch(cfg: GHConfig) -> None:
    _git("push", "-u", "origin", cfg.branch)


def enable_pages(cfg: GHConfig) -> Dict[str, Any]:
    """Enable Pages from <branch>/<pages_build_dir>. Treat 200/201/202/204 as success."""
    s = requests.Session()
    s.headers.update(_headers(cfg.token))

    # Optionally write CNAME file into the build dir
    if cfg.cname:
        cname_file = ROOT / cfg.pages_build_dir / "CNAME"
        cname_file.parent.mkdir(parents=True, exist_ok=True)
        cname_file.write_text(cfg.cname.strip() + "\n", encoding="utf-8")

    payload = {"source": {"branch": cfg.branch, "path": f"/{cfg.pages_build_dir}"}}
    SUCCESS = {200, 201, 202, 204}

    # Try to create a Pages site
    r = s.post(f"{GITHUB_API}/repos/{cfg.user}/{cfg.repo}/pages", json=payload, timeout=30)
    if r.status_code in SUCCESS:
        return {"status": r.status_code, "mode": "created"}

    # If already exists or needs update, try PUT (update config)
    if r.status_code in (409, 422, 400, 404):
        r2 = s.put(f"{GITHUB_API}/repos/{cfg.user}/{cfg.repo}/pages", json=payload, timeout=30)
        if r2.status_code in SUCCESS:
            return {"status": r2.status_code, "mode": "updated"}
        raise RuntimeError(f"Enable/Update Pages failed: {r2.status_code} {r2.text}")

    raise RuntimeError(f"Pages API error: {r.status_code} {r.text}")


def pages_url(cfg: GHConfig) -> str:
    if cfg.cname:
        return f"https://{cfg.cname}/"
    return f"https://{cfg.user}.github.io/{cfg.repo}/"


# ──────────────────────────────────────────────────────────────────────────────
# High-level one-shot helper
# ──────────────────────────────────────────────────────────────────────────────
def bootstrap_and_deploy() -> Dict[str, Any]:
    """
    One-shot:
      - load env
      - create repo if missing
      - ensure git identity/branch
      - set remote with token
      - initial commit (if needed), push
      - enable GitHub Pages
    Returns dict with 'sha' and 'pages_url'.
    """
    cfg = GHConfig.from_env()
    console.print(f"[bold]GitHub[/bold] target: {cfg.user}/{cfg.repo} on branch {cfg.branch}")

    ensure_git_identity()
    create_repo_if_missing(cfg)
    ensure_branch(cfg.branch)
    ensure_remote_origin(cfg)
    initial_commit_if_needed()
    push_branch(cfg)
    enable_pages(cfg)

    sha = _git("rev-parse", "HEAD").stdout.strip()
    return {"sha": sha, "pages_url": pages_url(cfg)}
