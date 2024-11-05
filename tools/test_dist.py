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

EXPECTED_SCRIPTS = set({'falcon-bench', 'falcon-inspect-app', 'falcon-print-routes'})
EXPECTED_PACKAGES = set({'falcon'})


def test_package(package):
    with tempfile.TemporaryDirectory() as tmpdir:
        venv = pathlib.Path(tmpdir) / 'venv'
        venv_bin = venv / 'bin'
        venv_pip = venv_bin / 'pip'
        subprocess.check_call((sys.executable, '-m', 'venv', venv))
        logging.info(f'Created a temporary venv in {venv}.')

        subprocess.check_call((venv_pip, 'install', '--upgrade', 'pip'))
        subprocess.check_call((venv_pip, 'install', '-r', REQUIREMENTS))
        logging.info(f'Installed test requirements in {venv}.')

        (venv_site_pkg,) = venv.glob('lib/python*/site-packages')
        bin_before = {path.name for path in venv_bin.iterdir()}
        pkg_before = {path.name for path in venv_site_pkg.iterdir()}

        subprocess.check_call((venv_pip, 'install', package))
        logging.info(f'Installed {package} into {venv}.')

        bin_after = {path.name for path in venv_bin.iterdir()}
        assert bin_after - bin_before == EXPECTED_SCRIPTS, (
            f'Unexpected scripts installed in {venv_bin} from {package}: '
            f'{bin_after - bin_before - EXPECTED_SCRIPTS}'
        )
        pkg_after = {
            path.name for path in venv_site_pkg.iterdir() if path.suffix != '.dist-info'
        }
        assert pkg_after - pkg_before == EXPECTED_PACKAGES, (
            f'Unexpected packages installed in {venv_site_pkg} from {package}: '
            f'{pkg_after - pkg_before - EXPECTED_PACKAGES}'
        )

        subprocess.check_call((venv_bin / 'pytest', TESTS), cwd=venv)
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
