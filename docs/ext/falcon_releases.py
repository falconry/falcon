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

import collections
import datetime
import enum
import itertools
import pathlib
import re

import sphinx.util.docutils

FALCON_DOCS_ROOT = pathlib.Path(__file__).resolve().parent.parent


class _FalconRelease:
    """A stable Falcon release."""

    _CHANGELOG_PATTERN = re.compile(r'^(\d+)\.(\d+).(\d+)\.rst$')
    _RELEASE_META_PATTERN = re.compile(r'\.\.\s+falcon-release\:\s+([\d-]+)')

    _PYPI_API_URL = 'https://pypi.org/pypi/falcon/{version}/json'

    @classmethod
    def from_changelog(cls, path):
        if not (mt := cls._CHANGELOG_PATTERN.match(path.name)):
            return None

        version = tuple(map(int, mt.groups()))
        if mt := cls._RELEASE_META_PATTERN.search(path.read_text()):
            date = datetime.date.fromisoformat(mt.group(1))
        else:
            date = None

        return cls(version, date)

    @classmethod
    def gather(cls, changelog_path):
        releases = [cls.from_changelog(path) for path in changelog_path.iterdir()]
        return sorted(
            release
            for release in releases
            if release is not None and not release.is_zerover
        )

    @property
    def is_zerover(self):
        return self.major == 0

    @property
    def major(self):
        return self.version[0]

    @property
    def version_str(self):
        return '.'.join(map(str, self.version))

    @property
    def version_major_minor(self):
        return '.'.join(map(str, self.version[:2]))

    def __init__(self, version, date=None):
        self.version = version
        self.date = date

    @property
    def doc_link(self):
        return f':doc:`{self.version_str} </changes/{self.version_str}>`'

    @property
    def doc_link_major_minor(self):
        return f':doc:`{self.version_major_minor} </changes/{self.version_str}>`'

    @property
    def rst_repr(self):
        return f'{self.doc_link} ({self.date})'

    def __eq__(self, other):
        return self.version == other.version

    def __lt__(self, other):
        return self.version < other.version

    def __repr__(self):
        return f'<falcon-{self.version_str} {self.date}>'

    def _load_date_from_pypi(self):
        # NOTE(vytas): This is not really used, but it is handy to verify the
        #   dates of historical releases, and other types of debugging.
        import requests

        resp = requests.get(self._PYPI_API_URL.format(version=self.version_str))
        if resp.status_code == 200:
            artifact, *_ = resp.json()['urls']
            upload_date, _, _ = artifact['upload_time'].partition('T')
            self.date = datetime.date.fromisoformat(upload_date)
        return self.date


_FalconMajorMinor = collections.namedtuple('_FalconMajorMinor', ('first', 'latest'))


class _ReleaseStatus(enum.Enum):
    current = 'current'
    security = 'security'
    eol = 'eol'

    @property
    def ref(self):
        return f':ref:`stable_release_{self.value}`'


class FalconReleasesDirective(sphinx.util.docutils.SphinxDirective):
    """Directive to tabulate the summary of stable Falcon releases."""

    _OLDSTABLE_MAINTENANCE_PERIOD = datetime.timedelta(days=365 * 2)

    required_arguments = 1
    has_content = True

    def run(self):
        changelog_path = pathlib.Path(self.arguments[0])
        if not changelog_path.is_absolute():
            changelog_path = FALCON_DOCS_ROOT / changelog_path

        releases = _FalconRelease.gather(changelog_path)
        for release in releases[:-1]:
            assert release.date is not None, (
                f'{release} has no release date metadata (and is not latest)'
            )
        if releases[-1].date is None:
            releases.pop()

        stable_releases = []
        for _, group in itertools.groupby(
            reversed(releases), lambda rel: rel.version_major_minor
        ):
            series = list(group)
            stable_releases.append(
                _FalconMajorMinor(first=min(series), latest=max(series))
            )

        current = stable_releases[0]
        current_series = sorted(
            rel for rel in stable_releases if rel.first.major == current.first.major
        )
        oldstable = max(
            rel for rel in stable_releases if rel.first.major == current.first.major - 1
        )

        header = '.. list-table::\n    :header-rows: 1\n\n'
        rows = [
            (
                'Major/Minor Version',
                'First Release',
                'Latest Patch Release',
                'Release Status',
            )
        ]

        for first, latest in stable_releases:
            eol_label = ''
            if latest == current.latest:
                status = _ReleaseStatus.current
            elif latest == oldstable.latest:
                eol_date = (
                    current_series[0].first.date + self._OLDSTABLE_MAINTENANCE_PERIOD
                )
                if datetime.date.today() < eol_date:
                    status = _ReleaseStatus.security
                    # NOTE(vytas): Move to a new line because otherwise table
                    #   layout gets messed up in an unpleasant way.
                    eol_label = f'\n\n        (until {eol_date})'
                else:
                    status = _ReleaseStatus.eol
                    eol_label = f'(since {eol_date})'
            else:
                status = _ReleaseStatus.eol

            rows.append(
                (
                    first.doc_link_major_minor,
                    first.rst_repr,
                    latest.version_str if latest == first else latest.rst_repr,
                    f'{status.ref} {eol_label}',
                )
            )

        content = '\n\n'.join(
            '    * ' + '\n      '.join(f'- {cell}' for cell in row) for row in rows
        )

        return self.parse_text_to_nodes(header + content)


def setup(app):
    app.add_directive('falcon-releases', FalconReleasesDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
