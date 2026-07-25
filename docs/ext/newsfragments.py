# Copyright 2026 by Vytautas Liuolia.
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

"""Towncrier newsfragments draft automatically baked into the docs."""

import pathlib
import re
import subprocess

from sphinx.errors import ExtensionError

FALCON_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
NEWSFRAGMENTS_DIR = FALCON_ROOT / 'docs' / '_newsfragments'


class TowncrierDraftRenderer:
    """Newsfragment draft renderer for the configured Towncrier file."""

    _FALCON_RELEASE_MARKER = '\n.. falcon-release:'
    _TOWNCRIER_DRAFT_STUB = '\nNo significant changes.\n'
    _TOWNCRIER_FILENAME_PATTERN = re.compile(r'filename = "docs/(.+)\.rst"\n')
    _TOWNCRIER_MARKER = '.. towncrier release notes start'

    def __init__(self, document):
        self._document = document

    @classmethod
    def load_project(cls):
        pyproject = FALCON_ROOT / 'pyproject.toml'
        documents = cls._TOWNCRIER_FILENAME_PATTERN.findall(pyproject.read_text())
        assert len(documents) == 1, 'Expected exactly one tool.towncrier.filename'
        return cls(documents[0])

    def _has_newsfragments(self):
        return any(NEWSFRAGMENTS_DIR.glob('*.rst'))

    def _render_draft(self):
        if not self._has_newsfragments():
            # NOTE(vytas): To ease the work for 3rd party packagers, we do not
            #   require the towncrier executable unless we actually have any
            #   newsfragments, otherwise we just simulate its stub.
            return self._TOWNCRIER_DRAFT_STUB

        try:
            draft = subprocess.check_output(('towncrier', '--draft'), cwd=FALCON_ROOT)
        except FileNotFoundError:
            raise ExtensionError(
                '`towncrier` binary was not found in the current environment',
                modname='ext.newsfragments',
            )
        except subprocess.CalledProcessError as ex:
            raise ExtensionError(
                f'error calling `towncrier`: {type(ex).__name__}: {ex}',
                modname='ext.newsfragments',
            )

        return draft.decode()

    def modify_rst_source(self, app, docname, source):
        if docname != self._document:
            return

        document = source[0]
        if self._TOWNCRIER_MARKER not in document:
            return
        if self._FALCON_RELEASE_MARKER in document:
            # Don't mess with finalized releases.
            return

        draft = self._render_draft()
        source[0] = document.replace(self._TOWNCRIER_MARKER, draft, 1)


def setup(app):
    renderer = TowncrierDraftRenderer.load_project()
    app.connect('source-read', renderer.modify_rst_source)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
