#!/usr/bin/env python

import argparse
import logging
import pathlib
import subprocess
import sys
import tempfile

logging.basicConfig(
    format='[test_dist.py] %(asctime)s [%(levelname)s] %(message)s', level=logging.INFO
)

FALCON_ROOT = pathlib.Path(__file__).resolve().parent.parent
REQUIREMENTS = FALCON_ROOT / 'requirements' / 'cibwtest'
TESTS = FALCON_ROOT / 'tests'


def test_package(package):
    with tempfile.TemporaryDirectory() as tmpdir:
        venv = pathlib.Path(tmpdir) / 'venv'
        subprocess.check_call((sys.executable, '-m', 'venv', venv))
        logging.info(f'Created a temporary venv in {venv}.')

        subprocess.check_call((venv / 'bin' / 'pip', 'install', '--upgrade', 'pip'))
        subprocess.check_call((venv / 'bin' / 'pip', 'install', '-r', REQUIREMENTS))
        logging.info(f'Installed test requirements in {venv}.')
        subprocess.check_call(
            (venv / 'bin' / 'pip', 'install', package),
        )
        logging.info(f'Installed {package} into {venv}.')

        subprocess.check_call((venv / 'bin' / 'pytest', TESTS), cwd=venv)
        logging.info(f'{package} passes tests.')


def main():
    description = 'Test Falcon packages (sdist or generic wheel).'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'package', metavar='PACKAGE', nargs='+', help='sdist/wheel(s) to test'
    )
    args = parser.parse_args()

    for package in args.package:
        test_package(package)


if __name__ == '__main__':
    main()
