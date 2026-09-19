# Copyright 2014-2026 by Falcon Contributors.
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
import time

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

# NOTE(vytas): Afford overriding the current date with SOURCE_DATE_EPOCH for
#   reproducible documentation builds.
#   (See also: https://reproducible-builds.org/docs/source-date-epoch/)
build_date = datetime.datetime.fromtimestamp(
    int(os.environ.get('SOURCE_DATE_EPOCH', time.time())), tz=datetime.timezone.utc
)

project = 'Falcon'
copyright = f'{build_date.year} Falcon Contributors'
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
    'ext.newsfragments',
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

# NOTE(SatvikMishra08): Emit warnings for unresolved references (#1888). Keep
#   nitpick_ignore(_regex) categorized — prefer fixing live docs over growing
#   a catch-all. Historical changelog links to removed APIs are ignored below.
nitpicky = True

nitpick_ignore = [
    # Type aliases noted in the autodoc_type_aliases TODO above
    ('py:class', 'SyncMiddleware'),
    ('py:class', 'AsyncMiddleware'),
    ('py:class', 'PreparedMiddlewareResult'),
    ('py:class', 'AsyncPreparedMiddlewareResult'),
    ('py:class', 'AsyncPreparedMiddlewareWsResult'),
    # Removed / renamed names still linked from historical changelogs (and a
    # few live docs that still use legacy cross-ref spellings)
    ('py:attr', 'Response.body_encoded'),
    ('py:attr', 'Response.content_range'),
    ('py:attr', 'Response.stream'),
    ('py:attr', 'Request.media'),
    ('py:attr', 'falcon.HTTPError.has_representation'),
    ('py:attr', 'falcon.HTTPStatus.body'),
    ('py:attr', 'falcon.HTTP_204'),
    ('py:attr', 'falcon.HTTP_NO_CONTENT'),
    ('py:attr', 'falcon.Response.body'),
    ('py:attr', 'falcon.DEFAULT_MEDIA_TYPE'),
    ('py:attr', 'falcon.MEDIA_MSGPACK'),
    ('py:attr', 'six.PY2'),
    ('py:attr', 'falcon.asgi.App.req_options'),
    ('py:attr', 'falcon.asgi.App.resp_options'),
    ('py:attr', 'falcon.asgi.App.router_options'),
    ('py:attr', 'falcon.media.MultipartFormHandler.parse_options'),
    ('py:class', 'API'),
    ('py:class', 'NoRepresentation'),
    ('py:class', 'Request'),
    ('py:class', 'Resource'),
    ('py:class', 'AsgiRequest'),
    ('py:class', 'AsgiResponse'),
    ('py:class', 'AsgiResponderCallable'),
    ('py:class', 'ResponderCallable'),
    ('py:class', 'ResponseStatus'),
    ('py:class', 'RetryAfter'),
    ('py:class', 'HeaderArg'),
    ('py:class', 'Link'),
    ('py:class', 'SSEvent'),
    ('py:class', 'MethodDict'),
    ('py:class', 'HTTPErrorKeywordArguments'),
    ('py:class', 'MultipartFormHandler'),
    ('py:class', 'BufferedReader'),
    ('py:class', 'PyBufferedReader'),
    ('py:class', '.CORSMiddleware'),
    ('py:class', 'falcon.CaseInsensitiveDict'),
    ('py:class', 'falcon.HTTPPayloadTooLarge'),
    ('py:class', 'falcon.WebSocketPayloadType'),
    ('py:class', 'falcon.constants.WebSocketPayloadType'),
    ('py:class', 'falcon.http_error.NoRepresentation'),
    ('py:class', 'falcon.http_error.OptionalRepresentation'),
    ('py:class', 'falcon.testing.TestBase'),
    ('py:class', 'falcon.routing.compiled.ConverterDict'),
    ('py:class', 'falcon.util.sync.Result'),
    ('py:class', 'collections.MutableMapping'),
    ('py:class', 'testtools.TestCase'),
    ('py:class', '_Traversable'),
    ('py:class', 'falcon.inspect._Traversable'),
    ('py:data', 'falcon.DEFAULT_MEDIA_TYPE'),
    ('py:data', 'falcon.MEDIA_JSON'),
    ('py:data', 'MultipartParseOptions.default_charset'),
    ('py:exc', 'HttpInvalidHeader'),
    ('py:func', 'falcon.create_task'),
    ('py:func', 'falcon.deprecated'),
    ('py:func', 'falcon.get_http_status'),
    ('py:func', 'falcon.get_running_loop'),
    ('py:func', 'falcon.routing.compile_uri_template'),
    ('py:meth', 'Request.get_media'),
    ('py:meth', 'Request.get_param'),
    ('py:meth', 'process_resource'),
    ('py:meth', 'uri.decode'),
    ('py:meth', 'falcon.get_http_status'),
    ('py:meth', 'falcon.media.Handlers.find_by_media_type'),
    ('py:meth', 'falcon.routing.compile_uri_template'),
    ('py:meth', 'falcon.routing.create_http_method_map'),
    ('py:meth', 'falcon.routing.util.map_http_methods'),
    ('py:meth', 'functools.partial'),
    ('py:meth', 'functools.wraps'),
    ('py:meth', 'inspect.getargspec'),
    ('py:meth', 'inspect.signature'),
    ('py:meth', 'asyncio.AbstractEventLoop.set_default_executor'),
    ('py:mod', 'msgpack'),
    ('py:mod', 'python-mimeparse'),
    ('py:mod', 'six'),
    ('py:mod', 'testtools'),
]

# Pattern-based ignores for typing noise Sphinx cannot resolve cleanly.
nitpick_ignore_regex = [
    (r'py:class', r'falcon\._typing\..+'),
    (r'py:class', r'falcon\.request\._T'),
    (r'py:class', r'falcon\.testing\.(client|helpers)\._.+'),
    (r'py:class', r'^_(ReqT|RespT|AReqT|ARespT|R)$'),
    (r'py:class', r'.*\[.*'),  # truncated autodoc generics
    (
        r'py:class',
        r'^(callable|iterable|iterator|optional|types|instance|func|function|'
        r'any|awaitable|datetime|io|UUID|this|_asyncio\.Task|'
        r'asyncio\.locks\.Condition|JSON serializable|'
        r'MessagePack serializable|Returns the "host)$',
    ),
]


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
autodoc_type_aliases = {
    'SyncMiddleware': 'SyncMiddleware',
    'AsyncMiddleware': 'AsyncMiddleware',
    'PreparedMiddlewareResult': 'PreparedMiddlewareResult',
}

# -- Options for HTML output --------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_css_files = ['custom.css']
html_js_files = [('custom-icons.js', {'defer': 'defer'})]
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
