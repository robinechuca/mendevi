#!/usr/bin/env python3

"""Executes analyser of code quality."""

try:
    from pylama.main import shell
except ImportError as err:
    raise ImportError("pylama paquage is required (pip install mendevi[test])") from err

from mendevi.utils import get_project_root


def test_mccabe_pycodestyle_pydocstyle_pyflakes():
    """Run these linters throw pylama on cutcutcodec."""
    root = get_project_root()
    assert not shell(  # fast checks
        [
            "--options", str(root.parent / "pyproject.toml"),
            "--linters", "mccabe,pycodestyle,pydocstyle,pyflakes", "--async",
            str(root),
        ],
        error=False,
    )


# def test_mypy():
#     """Run mypy throw pylama on cutcutcodec."""
#     root = get_project_root()
#     assert not shell(  # fast checks
#         [
#             "--options", str(root.parent / "pyproject.toml"),
#             "--linters", "mypy", "--async",
#             str(root),
#         ],
#         error=False,
#     )


def test_pylint():
    """Run pylint throw pylama on cutcutcodec."""
    root = get_project_root()
    assert not shell(  # fast checks
        [
            "--options", str(root.parent / "pyproject.toml"),
            "--linters", "pylint",
            str(root),
        ],
        error=False,
    )
