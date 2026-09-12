#!/usr/bin/env python
"""Patch .coveragerc to drop some 3.10-specific pragmas."""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

DIRECTIVES = (
    '    pragma: no py39,py310 cover\n',
    '    pragma: no py311 cover\n',
)


def sed_coverage_rc():
    version_short = 'py{}{}'.format(*sys.version_info[:2])

    with open(ROOT / '.coveragerc', 'a+') as fp:
        fp.seek(0)
        content = fp.read()

        for directive in DIRECTIVES:
            if version_short in directive:
                continue
            content = content.replace(directive, '')

        fp.seek(0)
        fp.truncate()
        fp.write(content)

    print(f'.coveragerc content after adjustment for {version_short}:\n')
    print(content)


if __name__ == '__main__':
    sed_coverage_rc()
