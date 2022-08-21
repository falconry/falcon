#!/usr/bin/env python

import argparse
import pathlib

CLEAN_EXTENSIONS = frozenset({'.c', '.pyc', '.so'})


def clean(root):
    for path in root.iterdir():
        if path.is_file() and path.suffix in CLEAN_EXTENSIONS:
            path.unlink()
        elif path.is_dir():
            clean(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Recursively clean intermediate compile results.'
    )
    parser.add_argument('directory', help='root directory to operate on')
    args = parser.parse_args()

    clean(pathlib.Path(args.directory).resolve())
