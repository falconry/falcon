#!/usr/bin/env python

import argparse
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
FALCON_ROOT = HERE.parent
DIST = FALCON_ROOT / 'dist'

CHANGELOGS = FALCON_ROOT / 'docs' / 'changes'
RELEASE_STABLE_VERSION_PATTERN = re.compile(r'^(\d+)\.(\d+).(\d+)$')
RELEASE_META_PATTERN = re.compile(r'\.\.\s+falcon-release\:\s+([\d-]+)')


def check_dist(dist, git_ref):
    sdist = None
    versions = set()
    wheels = []

    if git_ref:
        git_ref = git_ref.split('/')[-1].lower()

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

        if git_ref and version != git_ref:
            sys.stderr.write(
                f'Unexpected version: {path.name} ({version} != {git_ref})\n'
            )
            sys.exit(1)

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

    release_date = None
    if RELEASE_STABLE_VERSION_PATTERN.match(version):
        changelog = CHANGELOGS / f'{version}.rst'
        if not changelog.is_file():
            sys.stderr.write(f'Changelog for stable release missing: {changelog}\n')
            sys.exit(1)
        if not (meta := RELEASE_META_PATTERN.search(changelog.read_text())):
            sys.stderr.write(f'falcon-release meta missing in: {changelog}\n')
            sys.exit(1)
        release_date = meta.group(1)

    print(f'[{dist}]\n')
    print(f'sdist found:\n    {sdist}\n')
    print(f'wheels found:\n{wheel_list}')
    print(f'version identified:\n    {version}\n')
    print(f'release date:\n    {release_date}\n')


def main():
    description = 'Check artifacts (sdist, wheels) inside dist dir.'

    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-d',
        '--dist-dir',
        default=str(DIST),
        help='dist directory to check (default: %(default)s)',
    )
    parser.add_argument(
        '-r',
        '--git-ref',
        help='check version against git branch/tag ref (e.g. $GITHUB_REF)',
    )

    args = parser.parse_args()
    check_dist(pathlib.Path(args.dist_dir).resolve(), args.git_ref)


if __name__ == '__main__':
    main()
