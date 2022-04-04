#!/usr/bin/env python
"""Patch .coveragerc to drop some 3.10-specific pragmas."""

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def sed_coverage_rc():
    with open(ROOT / '.coveragerc', 'a+') as fp:
        fp.seek(0)
        content = fp.read()
        patched = content.replace('    pragma: no py39,py310 cover\n', '')

        fp.seek(0)
        fp.truncate()
        fp.write(patched)


if __name__ == '__main__':
    if sys.version_info < (3, 9, 0):
        sed_coverage_rc()
