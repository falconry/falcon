#!/usr/bin/env python

import argparse
import atexit
import logging
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile

logging.basicConfig(
    format='[tox_sdist.py] %(asctime)s [%(levelname)s] %(message)s', level=logging.INFO
)
HERE = pathlib.Path(__file__).resolve().parent
DIST = HERE.parent / 'dist'


def build_sdist():
    subprocess.check_call((sys.executable, 'setup.py', 'sdist'))
    archives = sorted(DIST.glob('*.tar.gz'), key=lambda p: p.stat().st_mtime)
    assert archives, 'no sdist archives found, something is wrong!'
    archive = archives[-1]
    logging.info(f'Built sdist: {archive}.')
    return archive


def extract_sdist(archive, target):
    with tarfile.open(archive) as targz:
        targz.extractall(target)

    content = target / archive.with_suffix('').stem
    assert content.is_dir, 'no extracted directory found, something is wrong!'
    logging.info(f'Extracted {archive} to {content}.')
    return content


def exec_tox(tox_ini_dir):
    logging.info(f'Running tox in {tox_ini_dir}...')
    subprocess.check_call(('tox', '--version'))
    subprocess.check_call(('tox',), cwd=tox_ini_dir)


def _cleanup(target):
    shutil.rmtree(target)
    logging.info(f'Removed temporary directory {target}.')


def main():
    description = 'Build, extract sdist to a temp path, and run tox within.'

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-p', '--path', help='path to extract sdist to (default: create temp)'
    )
    args = parser.parse_args()

    target = args.path
    if not target:
        target = tempfile.mkdtemp(prefix='falcon-')
        atexit.register(_cleanup, target)
    target = pathlib.Path(target)
    logging.info(f'Using target path: {target}.')

    archive = build_sdist()
    extracted = extract_sdist(archive, target)
    exec_tox(extracted)


if __name__ == '__main__':
    main()
