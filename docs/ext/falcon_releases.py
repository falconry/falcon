# Copyright 2025 by Vytautas Liuolia.
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

"""
Information on stable Falcon releases.

This extension aggregates a table of maintained and EOL Falcon releases from
the provided path containing changelogs.
"""

import pathlib
import re

import sphinx.util.docutils

FALCON_DOCS_ROOT = pathlib.Path(__file__).resolve().parent.parent


class FalconReleasesDirective(sphinx.util.docutils.SphinxDirective):
    """Directive to tabulate the summary of stable Falcon releases."""

    required_arguments = 1
    has_content = True

    _CHANGELOG_PATTERN = re.compile(r'^(\d+)\.(\d+).(\d+)\.rst$')

    def run(self):
        changelog_path = pathlib.Path(self.arguments[0])
        if not changelog_path.is_absolute():
            changelog_path = FALCON_DOCS_ROOT / changelog_path

        releases = []
        for path in changelog_path.iterdir():
            if not (mt := self._CHANGELOG_PATTERN.match(path.name)):
                continue
            version = tuple(map(int, mt.groups()))
            releases.append(version)

        releases.sort()
        content = '\n'.join(f'* ``{version=}``' for version in releases)
        return self.parse_text_to_nodes(content)


def setup(app):
    app.add_directive('falcon-releases', FalconReleasesDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
