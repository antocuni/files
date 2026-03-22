#!/usr/bin/env python3
"""
Deploy SPy playground to antocuni-files repo.
Creates: ~/pypy/misc/antocuni-files/spy/playground/DATE-BRANCH-COMMIT/
"""
import os
import subprocess
import shutil
import sys
from pathlib import Path

ANTOCUNI_FILES = Path(__file__).parent.parent.parent  # antocuni-files/
DEPLOY_BASE = ANTOCUNI_FILES / "spy/playground"
SPY_REPO = Path.home() / "anaconda/spy"
PLAYGROUND_DIR = SPY_REPO / "playground"
PYTHON = SPY_REPO / "venv/bin/python"

# Files/dirs that exist in the playground during development but should not be deployed
EXCLUDE = {"Makefile", "tests", "spyast"}


def get_git_info() -> tuple[str, str, str]:
    branch = subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
        cwd=SPY_REPO, text=True
    ).strip()
    commit = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=SPY_REPO, text=True
    ).strip()
    # Author date in YYYY-MM-DD format
    date = subprocess.check_output(
        ["git", "log", "-1", "--format=%as"],
        cwd=SPY_REPO, text=True
    ).strip()
    return branch, commit, date


def patch_playground_index(dest_dir: Path, branch: str, commit: str, date: str) -> None:
    index = dest_dir / "index.html"
    content = index.read_text()

    content = content.replace(
        "<title>SPy playground</title>",
        f"<title>SPy playground [{branch}@{commit}]</title>",
    )
    banner = (
        f'    <div id="deploy-info" style="'
        f'position:fixed;top:4px;right:8px;font-size:11px;'
        f'color:#888;font-family:monospace;z-index:9999">'
        f"{branch}@{commit} ({date})</div>"
    )
    content = content.replace("<body>", f"<body>\n{banner}", 1)

    index.write_text(content)



def build_playground() -> None:
    if not PYTHON.exists():
        print(f"error: venv not found at {PYTHON}", file=sys.stderr)
        sys.exit(1)
    print("Running 'make local' in playground/...")
    # Prepend venv/bin to PATH so that both the playground Makefile and the
    # nested libspy Makefile (which hardcodes bare 'python') use the venv Python.
    env = os.environ.copy()
    env["PATH"] = f"{PYTHON.parent}:{env['PATH']}"
    subprocess.check_call(
        ["make", "local", f"PYTHON={PYTHON}"],
        cwd=PLAYGROUND_DIR,
        env=env,
    )


def main() -> None:
    if not SPY_REPO.is_dir():
        print(f"error: spy repo not found at {SPY_REPO}", file=sys.stderr)
        sys.exit(1)

    if not ANTOCUNI_FILES.is_dir():
        print(f"error: antocuni-files repo not found at {ANTOCUNI_FILES}", file=sys.stderr)
        sys.exit(1)

    build_playground()

    branch, commit, date = get_git_info()
    # Replace '/' in branch names (e.g. feature/foo) with '-' for safe directory names
    safe_branch = branch.replace("/", "-")
    deploy_name = f"{date}-{safe_branch}-{commit}"
    dest_dir = DEPLOY_BASE / deploy_name

    print(f"Branch:  {branch}")
    print(f"Commit:  {commit}")
    print(f"Date:    {date}")
    print(f"Target:  {dest_dir}")

    if dest_dir.exists():
        print("Destination already exists, removing...")
        shutil.rmtree(dest_dir)

    dest_dir.mkdir(parents=True, exist_ok=True)

    for item in PLAYGROUND_DIR.iterdir():
        if item.name in EXCLUDE:
            continue
        target = dest_dir / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)

    patch_playground_index(dest_dir, branch, commit, date)

    # Update the spy/playground/index.html listing
    genindex = ANTOCUNI_FILES / "genindex.py"
    subprocess.check_call([sys.executable, str(genindex), str(DEPLOY_BASE)])

    print("Done!")
    print(f"\nNext steps:")
    print(f"  cd {ANTOCUNI_FILES}")
    print(f"  git add spy/playground/")
    print(f'  git commit -m "Add SPy playground {deploy_name}"')
    print(f"  git push")


if __name__ == "__main__":
    main()
