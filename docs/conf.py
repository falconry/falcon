# Copyright 2014-2025 by Falcon Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import multiprocessing
import os
import sys

try:
    import falconry_pygments_theme
except ImportError:
    # NOTE(vytas): If one is packaging Falcon documentation, it might be
    #   impractical to spend time and effort on our Pygments styles.
    falconry_pygments_theme = None

sys.path.insert(0, os.path.abspath('..'))

import falcon  # noqa: E402

# -- Build tweaks -------------------------------------------------------------

# NOTE(kgriffs): Work around the change in Python 3.8 that breaks sphinx
#   on macOS. See also:
#
#   * https://github.com/sphinx-doc/sphinx/issues/6803
#   * https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods
#
if not sys.platform.startswith('win'):
    multiprocessing.set_start_method('fork')

# _on_rtd is whether we are on readthedocs.org
# _on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# Used to alter sphinx configuration for the Dash documentation build
_dash_build = os.environ.get('DASHBUILD', False) == 'True'

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))
sys.path.insert(0, os.path.abspath('.'))

# -- Project information ------------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

_version_components = falcon.__version__.split('.')
_prerelease_version = any(
    not component.isdigit() and not component.startswith('post')
    for component in _version_components
)


project = 'Falcon'
copyright = '{year} Falcon Contributors'.format(year=datetime.datetime.now().year)
author = 'Kurt Griffiths et al.'
version = '.'.join(_version_components[0:2])
release = falcon.__version__

# -- General configuration ----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.intersphinx',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
    'sphinx_copybutton',
    'sphinx_design',
    'myst_parser',
    # Falcon-specific extensions
    'ext.autodoc_customizations',
    'ext.cibuildwheel',
    'ext.doorway',
    'ext.falcon_releases',
    'ext.private_args',
    'ext.rfc',
    'ext.workarounds',
]

templates_path = ['_templates']
exclude_patterns = ['_build', '_newsfragments']

# The name of the Pygments (syntax highlighting) style to use.
# NOTE(vytas): The PyData theme uses separate Pygments style settings for HTML,
#   so we specify a print-friendly theme here for the likes of latexpdf.
pygments_style = 'bw'

# myst configuration
myst_enable_extensions = ['tasklist']
myst_enable_checkboxes = True

# Intersphinx configuration
intersphinx_mapping = {'python': ('https://docs.python.org/3', None)}

# NOTE(vytas): The autodoc_type_aliases mapping below doesn't really work as
#   advertised...
#   Sphinx is looking for the mapped types defined as classes, however, typing
#   aliases constructed with the help of the | operator (or Union meta type),
#   etc, are recognized as module data/attributes, not types.
# TODO(vytas): When defining a class alias manually, it seems to work as
#   expected, e.g.,
#
#   .. class:: PreparedMiddlewareResult
#
#       An alias for the return type of prepare_middleware().
#
#   See also https://github.com/sphinx-doc/sphinx/issues/10785 & related issues
#   for discussion and potentially better workarounds.
# TODO(vytas): If we enable the "nitpicky" mode, we will have to add exceptions
#   for all unresolved aliases.
autodoc_type_aliases = {
    'SyncMiddleware': 'SyncMiddleware',
    'AsyncMiddleware': 'AsyncMiddleware',
    'PreparedMiddlewareResult': 'PreparedMiddlewareResult',
}

# -- Options for HTML output --------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_css_files = ['custom.css']
html_js_files = ['custom-icons.js']
html_favicon = '_static/img/favicon.ico'
html_logo = '_static/img/logo.svg'
html_static_path = ['_static']
html_theme = 'pydata_sphinx_theme'
html_show_sourcelink = False

html_context = {
    # NOTE(vytas): We don't provide any default, the browser's preference
    # should be used.
    # 'default_mode': 'light',
    'prerelease': _prerelease_version,  # True if tag is not the empty string
}

# Theme options are theme-specific and customize the look and feel further.
# https://pydata-sphinx-theme.readthedocs.io/en/stable/user_guide/index.html

_falconry_styles = falconry_pygments_theme is not None

html_theme_options = {
    # NOTE(vytas): If our Pygments styles are unavailable, fall back to the
    #   visually closest Gruvbox styles.
    #   NB that Gruvbox does not meet the WCAG 2.1 AA requirements for contrast.
    'pygments_light_style': 'falconry-light' if _falconry_styles else 'gruvbox-light',
    'pygments_dark_style': 'falconry-dark' if _falconry_styles else 'gruvbox-dark',
    'header_links_before_dropdown': 4,
    'external_links': [
        {
            'name': 'Get Help',
            'url': 'https://falcon.readthedocs.io/community/help.html',
        },
        {'name': 'Falcon Wiki', 'url': 'https://github.com/falconry/falcon/wiki'},
        {
            'name': 'Support Falcon',
            'url': 'https://falconframework.org/#sectionSupportFalconDevelopment',
        },
    ],
    'icon_links': [
        {
            'name': 'GitHub',
            'url': 'https://github.com/falconry/falcon',
            'icon': 'fa-brands fa-github',
        },
        {
            'name': 'PyPI',
            'url': 'https://pypi.org/project/falcon',
            'icon': 'fa-custom fa-pypi',
        },
        {
            'name': 'Falcon Home',
            'url': 'https://falconframework.org',
            'icon': 'fa-custom fa-falcon',
        },
    ],
    'logo': {
        'text': 'Falcon',
    },
    'navbar_end': ['theme-switcher', 'navbar-icon-links'],
    'footer_start': ['copyright'],
    'footer_end': ['theme-version'],
}

if _dash_build:
    html_theme_options.update(font_size=13)


# -- Options for LaTeX output -------------------------------------------------

# NOTE(vytas): The default engine fails to build citing unsupported Unicode
# characters.
latex_engine = 'xelatex'

latex_elements = {
    'papersize': 'a4paper',
    # The font size ('10pt', '11pt' or '12pt').
    # 'pointsize': '10pt',
    # Additional stuff for the LaTeX preamble.
    # 'preamble': '',
}

latex_documents = [
    (
        'index',
        'Falcon.tex',
        'Falcon Documentation',
        'Kurt Griffiths et al.',
        'manual',
    ),
]

# -- Options for manual page output -------------------------------------------

man_pages = [('index', 'falcon', 'Falcon Documentation', ['Kurt Griffiths et al.'], 1)]

# -- Options for Texinfo output -----------------------------------------------

texinfo_documents = [
    (
        'index',
        'Falcon',
        'Falcon Documentation',
        'Kurt Griffiths et al.',
        'Falcon',
        'One line description of project.',
        'Miscellaneous',
    ),
]
