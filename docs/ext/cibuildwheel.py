# Copyright 2024-2025 by Vytautas Liuolia.
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
Binary wheels table extension for Sphinx.

This extension parses a GitHub Actions workflow for building binary wheels, and
summarizes the build onfiguration in a stylish table.
"""

import itertools
import pathlib

import sphinx.util.docutils
import yaml

FALCON_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
DOT_GITHUB = FALCON_ROOT / '.github'

_CHECKBOX = '\u2705'
_CPYTHON_PLATFORMS = {
    'manylinux_x86_64': '**Linux Intel** ``manylinux`` 64-bit',
    'musllinux_x86_64': '**Linux Intel** ``musllinux`` 64-bit',
    'manylinux_i686': '**Linux Intel** ``manylinux`` 32-bit',
    'musllinux_i686': '**Linux Intel** ``musllinux`` 32-bit',
    'manylinux_aarch64': '**Linux ARM** ``manylinux`` 64-bit',
    'musllinux_aarch64': '**Linux ARM** ``musllinux`` 64-bit',
    'manylinux_ppc64le': '**Linux PowerPC** ``manylinux`` 64-bit',
    'musllinux_ppc64le': '**Linux PowerPC** ``musllinux`` 64-bit',
    'manylinux_s390x': '**Linux IBM Z** ``manylinux``',
    'musllinux_s390x': '**Linux IBM Z** ``musllinux``',
    'macosx_x86_64': '**macOS Intel**',
    'macosx_arm64': '**macOS Apple Silicon**',
    'win32': '**Windows** 32-bit',
    'win_amd64': '**Windows** 64-bit',
    'win_arm64': '**Windows ARM** 64-bit',
}

_EXTEND_CPYTHONS = frozenset({'cp38', 'cp39'})


class WheelsDirective(sphinx.util.docutils.SphinxDirective):
    """Directive to tabulate build info from a YAML workflow."""

    required_arguments = 1
    has_content = True

    @classmethod
    def _emit_table(cls, data):
        columns = len(data[0])
        assert all(len(row) == columns for row in data), (
            'All rows must have the same number of columns'
        )
        # NOTE(vytas): +2 is padding inside cell borders.
        width = max(len(cell) for cell in itertools.chain(*data)) + 2
        hline = ('+' + '-' * width) * columns + '+\n'
        output = [hline]

        for row in data:
            for cell in row:
                # NOTE(vytas): Emojis take two spaces...
                padded_width = width - 1 if cell == _CHECKBOX else width
                output.append('|' + cell.center(padded_width))
            output.append('|\n')

            header_line = row == data[0]
            output.append(hline.replace('-', '=') if header_line else hline)

        return ''.join(output)

    def run(self):
        workflow_path = pathlib.Path(self.arguments[0])
        if not workflow_path.is_absolute():
            workflow_path = FALCON_ROOT / workflow_path

        # TODO(vytas): Should we package cibuildwheel.yaml into sdist too?
        #   For now, if .github is missing, we simply hide the table.
        if not workflow_path.is_file() and not DOT_GITHUB.exists():
            return []

        with open(workflow_path) as fp:
            workflow = yaml.safe_load(fp)

        matrix = workflow['jobs']['build-wheels']['strategy']['matrix']
        platforms = matrix['platform']
        include = matrix.get('include', [])
        assert not matrix.get('exclude'), 'TODO: exclude is not supported yet'
        supported = set(
            itertools.product(
                [platform['name'] for platform in platforms], matrix['python']
            )
        )
        supported.update((item['platform']['name'], item['python']) for item in include)
        cpythons = sorted(
            {cp for _, cp in supported} | _EXTEND_CPYTHONS,
            key=lambda val: (len(val), val),
        )

        header = ['Platform / CPython version']
        table = [header + [cp.replace('cp3', '3.') for cp in cpythons]]
        table.extend(
            [description]
            + [(_CHECKBOX if (name, cp) in supported else '') for cp in cpythons]
            for name, description in _CPYTHON_PLATFORMS.items()
        )

        content = '\n'.join(self.content) + '\n\n' + self._emit_table(table)
        return self.parse_text_to_nodes(content)


def setup(app):
    app.add_directive('wheels', WheelsDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
