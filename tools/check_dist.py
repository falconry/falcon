#!/usr/bin/env python

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
DIST = HERE.parent / 'dist'


def check_dist(dist):
    sdist = None
    versions = set()
    wheels = []

    for path in dist.iterdir():
        if not path.is_file():
            continue

        if path.name.endswith('.tar.gz'):
            assert sdist is None, f'sdist already exists: {sdist}'
            sdist = path.name

        elif path.name.endswith('.whl'):
            wheels.append(path.name)

        else:
            sys.stderr.write(f'Unexpected file found in dist: {path.name}\n')
            sys.exit(1)

        package, _, _ = path.stem.partition('.tar')
        falcon, version, *_ = package.split('-')
        assert falcon == 'falcon', 'Unexpected package name: {path.name}'
        versions.add(version)

    if not versions:
        sys.stderr.write('No artifacts collected!\n')
        sys.exit(1)
    if len(versions) > 1:
        sys.stderr.write(f'Multiple versions found: {tuple(versions)}!\n')
        sys.exit(1)
    version = versions.pop()

    wheel_list = '    None\n'
    if wheels:
        wheel_list = ''.join(f'    {wheel}\n' for wheel in sorted(wheels))

    print(f'[{dist}]\n')
    print(f'sdist found:\n    {sdist}\n')
    print(f'wheels found:\n{wheel_list}')
    print(f'version identified:\n    {version}\n')


def main():
    description = 'Check artifacts (sdist, wheels) inside dist dir.'

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-d',
        '--dist-dir',
        default=str(DIST),
        help='dist directory to check (default: %(default)s)',
    )

    args = parser.parse_args()
    check_dist(pathlib.Path(args.dist_dir))


if __name__ == '__main__':
    main()
