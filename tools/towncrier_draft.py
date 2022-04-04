#!/usr/bin/env python

import argparse
import atexit
import pathlib
import subprocess

import toml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent


def _write_changelog(target, data):
    with open(ROOT / target, 'wb') as rst:
        rst.write(data)


def get_target_filename():
    with open(ROOT / 'pyproject.toml') as pyproject_toml:
        project = toml.load(pyproject_toml)

    return project['tool']['towncrier']['filename']


def render_draft(target, template):
    draft = subprocess.check_output(('towncrier', '--draft'), cwd=ROOT)

    # NOTE(vytas): towncrier does not seem to respect our preference for not
    #   creating a title, so we remove it manually.
    #   (See also: https://github.com/twisted/towncrier/issues/345)
    draft = draft.split(b'=============', 1)[-1]
    draft = draft.lstrip(b'=').lstrip()

    # NOTE(vytas): towncrier --draft does not seem to use the template,
    #   so we substitute manually.
    rendered = template.replace(b'.. towncrier release notes start', draft, 1)

    print(f'Writing changelog to {target}')
    _write_changelog(target, rendered)


def build_docs():
    subprocess.check_call(
        (
            'sphinx-build',
            '-W',
            '-E',
            '-b',
            'html',
            ROOT / 'docs',
            ROOT / 'docs/_build/html',
        )
    )


def main():
    description = (
        'Render towncrier news fragments and write them to the changelog template.'
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-n', '--dry-run', action='store_true', help='dry run: do not write any files'
    )
    args = parser.parse_args()

    target = get_target_filename()
    with open(ROOT / target, 'rb') as rst:
        template = rst.read()

    if args.dry_run:
        # NOTE(vytas): Restore the template once we are done.
        atexit.register(_write_changelog, target, template)

    render_draft(target, template)
    build_docs()


if __name__ == '__main__':
    main()
