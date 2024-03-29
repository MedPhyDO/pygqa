# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config


# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#

'''
conf
====

configuration for inline documentation with sphinx 

'''
__author__ = "R. Bauer" 
__copyright__ = "2020, MedPhyDO - Machbarkeitsstudien im Rahmen von Bachelor und Masterarbeiten an der TU-Dortmund / FH-Dortmund und Klinikum Dortmund"
__credits__ = ["R. Bauer", "K.Loot"]
__license__ = "MIT"
__version__ = "0.2.0"
__status__ = "Prototype"

import os
import sys

if not os.path.abspath("./_ext") in sys.path:
    sys.path.insert(0, os.path.abspath('../..'))

    # own extensions
    # Set Python’s module search path, sys.path, accordingly so that Sphinx can find them
    sys.path.append(os.path.abspath("./_ext"))

# --- General configuration --------------------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html
#  
project = 'webdoc'
author = __author__
copyright = __copyright__
version = __version__
release = __version__

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.todo',
    'm2r2',
    'sphinx.ext.napoleon',
    'ext_restdoc',
]

# The suffix(es) of source filenames.
source_suffix = {
    '.rst': 'restructuredtext',
    '.txt': 'markdown',
    '.md': 'markdown',
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The language for content autogenerated by Sphinx.
language = 'en'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# 'library/xml' – ignores the library/xml directory
# 'library/xml*' – ignores all files and directories starting with library/xml
# '**/.svn' – ignores all .svn directories
exclude_patterns = [
    'ui',
    '**/docs*',
    '**/tests*',
    '**/resources*',
    '**/.docs*',
    'htmlcov',
]

# --- Options for sphinx.ext.autodoc  ----------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#confval-autodoc_default_options

# Both the class’ and the __init__ method’s docstring are concatenated and inserted.
autoclass_content = "both"

# --- Options for sphinx.ext.autosummary  ------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/extensions/autosummary.html

autosummary_generate = True

# --- Options for sphinx.ext.todo --------------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/extensions/todo.html

todo_include_todos = True

# --- Options for m2r2 -------------------------------------------------------
#
# https://github.com/crossnox/m2r2

m2r_parse_relative_links = True

# --- Options for HTML output ------------------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# The theme to use for HTML and HTML Help pages.
html_theme = 'bizstyle'

# The style sheet to use for HTML pages
html_style = 'bizstyle.css'

# A list of additional CSS files
html_css_files = ['isp_bizstyle.css']

# Name of the logo image file with path
html_logo = 'docs/logo.png'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# No links to the reST sources will be added to the sidebar.
html_show_sourcelink = False

# --- Options for sphinx.ext.napoleon ----------------------------------------
#
# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = True
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True
