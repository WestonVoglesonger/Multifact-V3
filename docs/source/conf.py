"""
Sphinx configuration for System Narrative Compiler (SNC) documentation.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath("../../backend"))

# Project information
project = "System Narrative Compiler"
copyright = "2024, Weston Voglesonger"
author = "Weston Voglesonger"
version = "0.1.0"
release = version

# General configuration
extensions = [
    "sphinx.ext.autodoc",  # Automatically include docstrings
    "sphinx.ext.napoleon",  # Support for Google-style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
    "sphinx.ext.intersphinx",  # Link to other project's documentation
    "sphinx_autodoc_typehints",  # Use type hints in documentation
    "sphinx_copybutton",  # Add copy button to code blocks
    "myst_parser",  # Support Markdown files
]

# Add any paths that contain templates here
templates_path = ["_templates"]
exclude_patterns = []

# The suffix(es) of source filenames
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# The master toctree document
master_doc = "index"

# Theme configuration
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Intersphinx configuration
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/14/", None),
    "pydantic": ("https://docs.pydantic.dev/", None),
}

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
napoleon_type_aliases = None

# AutoDoc settings
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__",
    "undoc-members": True,
    "exclude-members": "__weakref__",
}