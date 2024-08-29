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


class WheelsDirective(sphinx.util.docutils.SphinxDirective):
    """Directive to tabulate build info from a YAML workflow."""

    required_arguments = 1

    @classmethod
    def _emit_table(cls, data):
        columns = len(data[0])
        assert all(
            len(row) == columns for row in data
        ), 'All rows must have the same number of columns'

        width = max(len(cell) for cell in itertools.chain(*data))
        # Leave padding to cell borders
        width += 2

        hline = ('+' + '-' * width) * columns + '+\n'
        output = [hline]
        header_line = True

        for row in data:
            for cell in row:
                # NOTE(vytas): Emojis take two spaces...
                padded_width = width - 1 if cell == _CHECKBOX else width
                output.append('|')
                output.append(cell.center(padded_width))

            output.append('|\n')

            if header_line:
                output.append(hline.replace('-', '='))
                header_line = False
            else:
                output.append(hline)

        return ''.join(output)

    def run(self):
        workflow_path = pathlib.Path(self.arguments[0])
        if not workflow_path.is_absolute():
            workflow_path = FALCON_ROOT / workflow_path
        with open(workflow_path) as fp:
            workflow = yaml.safe_load(fp)

        matrix = workflow['jobs']['build-wheels']['strategy']['matrix']
        include = matrix['include']
        assert not matrix.get('exclude'), 'TODO: exclude is not supported yet'

        supported = set(
            itertools.product(
                [platform['name'] for platform in matrix['platform']], matrix['python']
            )
        )
        supported.update((item['platform']['name'], item['python']) for item in include)

        table = [
            ('Platform / CPython version', '3.8', '3.9', '3.10', '3.11', '3.12', '3.13')
        ]
        for name, description in _CPYTHON_PLATFORMS.items():
            row = [description]
            for cpython in ('cp38', 'cp39', 'cp310', 'cp311', 'cp312', 'cp313'):
                value = _CHECKBOX if (name, cpython) in supported else ''
                row.append(value)
            table.append(row)

        return self.parse_text_to_nodes(self._emit_table(table))


def setup(app):
    app.add_directive('wheels', WheelsDirective)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
