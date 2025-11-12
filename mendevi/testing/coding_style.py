"""Executes analyser of code quality."""

import os
import subprocess

from mendevi.utils import get_project_root


def run_ruff(args: list[str]) -> bool:
    """Run Ruff with given arguments, return True if no lint errors."""
    cmd = ["ruff", "check", *args]
    env = os.environ | {"FORCE_COLOR": "1"}
    result = subprocess.run(cmd, check=False, capture_output=True, text=True, env=env)
    print(result.stdout)
    print(result.stderr)
    return result.returncode == 0


def test_linting() -> None:
    """Run Ruff (replaces mccabe, pycodestyle, pydocstyle, pyflakes, pylint)."""
    root = get_project_root()
    assert run_ruff([str(root), "--config", str(root.parent / "pyproject.toml")])
