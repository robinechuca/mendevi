#!/usr/bin/env python3

"""Configuration for generated the Sphinx documenation."""
# python docstring tips: https://www.sphinx-doc.org/en/master/usage/domains/python.html

# -- Path setup --------------------------------------------------------------
import datetime
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from mendevi import __author__, __version__

# -- Project information -----------------------------------------------------
project = "mendevi"
author = __author__
version = __version__
release = version
now = datetime.datetime.now()
today = f"{now.year}-{now.month:02}-{now.day:02} {now.hour:02}H{now.minute:02}"
copyright = f"2024-{now.year}, {author}, GPL"
source_suffix = ".rst"
master_doc = "index"
language = "en"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", ".venv"]
html_theme = "furo"
pygments_style = "sphinx"
extensions = [
    # "numpydoc",  # to include the numpy functions
    "recommonmark",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    # "sphinx.ext.extlinks",  # in pillow conf
    # "sphinx.ext.githubpages",
    "sphinx.ext.ifconfig",
    "sphinx.ext.intersphinx",  # in pillow conf
    "sphinx.ext.mathjax",  # for latex math (apt install libjs-mathjax or Node-mathjax-full)
    "sphinx.ext.viewcode",  # in pillow conf
    "sphinx_copybutton",  # in pillow conf
    "sphinx_inline_tabs",  # in pillow conf
    # "sphinxcontrib.video",  # for video insertion in doc
    "sphinxext.opengraph",  # for website metadata
]
todo_include_todos = True
intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}
mathjax_path = "https://cdn.mathjax.org/mathjax/latest/MathJax.js?config=TeX-AMS-MML_HTMLorMML"

# -- Set light mode by default ----------------------------------------------
default_dark_mode = False

# -- API Autogeneration ------------------------------------------------------
autosectionlabel_prefix_document = True
autosummary_generate = True
templates_path = ["_templates"]  # add any paths that contain templates here, relative to this directory
autoclass_content = "both"  # include dunder methods (like __init__) documentation
