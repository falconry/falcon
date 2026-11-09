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

# NOTE: These are installed explicitly before the package under test, so that
#   we can verify that Falcon itself does not pull in any other distribution.
CHECK_REQUIREMENTS = ('packaging', 'pytest')
# NOTE: pip is bootstrapped by venv itself.
VENV_TOOLING = frozenset({'pip'})


def requirement_closure(names):
    """Return the given distributions together with their runtime requirements."""
    import importlib.metadata

    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name

    pending = [canonicalize_name(name) for name in names]
    closure = set()

    while pending:
        name = pending.pop()
        if name in closure:
            continue
        closure.add(name)

        for spec in importlib.metadata.requires(name) or ():
            req = Requirement(spec)
            if req.marker is None or req.marker.evaluate({'extra': ''}):
                pending.append(canonicalize_name(req.name))

    return closure


def check_installed(allowed):
    """Exit with an error if any distributions beyond the allowed ones are found."""
    import importlib.metadata

    from packaging.utils import canonicalize_name

    installed = {
        canonicalize_name(dist.metadata['Name'])
        for dist in importlib.metadata.distributions()
    }
    unexpected = sorted(installed - requirement_closure(allowed) - VENV_TOOLING)
    if unexpected:
        sys.exit(f'Unexpected distributions installed: {", ".join(unexpected)}')


def test_package(package):
    with tempfile.TemporaryDirectory() as tmpdir:
        venv = pathlib.Path(tmpdir) / 'venv'
        venv_bin = venv / 'bin'
        venv_pip = venv_bin / 'pip'
        subprocess.check_call((sys.executable, '-m', 'venv', venv))
        logging.info(f'Created a temporary venv in {venv}.')

        subprocess.check_call((venv_pip, 'install', '--upgrade', 'pip'))
        subprocess.check_call((venv_pip, 'install', *CHECK_REQUIREMENTS))
        logging.info(f'Installed {", ".join(CHECK_REQUIREMENTS)} in {venv}.')

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

        subprocess.check_call(
            (venv_bin / 'python', __file__, '--check-installed', 'falcon')
            + CHECK_REQUIREMENTS
        )
        logging.info(f'{package} does not install any third-party distributions.')

        subprocess.check_call((venv_pip, 'install', '-r', REQUIREMENTS))
        logging.info(f'Installed test requirements in {venv}.')

        subprocess.check_call((venv_bin / 'pytest', TESTS), cwd=venv)
        logging.info(f'{package} passes tests.')


def main():
    description = 'Test Falcon packages (sdist or generic wheel).'
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        'package', metavar='PACKAGE', nargs='*', help='sdist/wheel(s) to test'
    )
    # NOTE: Used internally by test_package() to run the check inside the
    #   temporary venv, where packaging is available.
    parser.add_argument(
        '--check-installed', metavar='DIST', nargs='+', help=argparse.SUPPRESS
    )
    args = parser.parse_args()

    if args.check_installed:
        check_installed(args.check_installed)
        return

    if not args.package:
        parser.error('the following arguments are required: PACKAGE')

    for package in args.package:
        test_package(package)


if __name__ == '__main__':
    main()
