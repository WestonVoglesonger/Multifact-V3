"""
Sphinx configuration for System Narrative Compiler (SNC) documentation.
"""

import os
import sys

# Add the project root directory to the Python path
sys.path.insert(0, os.path.abspath("../.."))

# Project information
project = "System Narrative Compiler"
copyright = "2024, Weston Vogelsong"
author = "Weston Vogelsong"

# General configuration
extensions = [
    "sphinx.ext.autodoc",  # Automatically include docstrings
    "sphinx.ext.napoleon",  # Support for Google-style docstrings
    "sphinx.ext.viewcode",  # Add links to source code
    "sphinx_autodoc_typehints",  # Use type hints in documentation
    "sphinx_rtd_theme",  # Use the Read the Docs theme
    "sphinx_copybutton",  # Add copy button to code blocks
    "myst_parser",  # Support Markdown files
]

# Add any paths that contain templates here
templates_path = ["_templates"]
exclude_patterns = []

# Theme configuration
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

# Napoleon settings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = True
napoleon_use_ivar = True
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
