#!/usr/bin/env python

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


def render_draft(target):
    with open(ROOT / target, 'rb') as rst:
        template = rst.read()
    # NOTE(vytas): Restore the template once we are done.
    atexit.register(_write_changelog, target, template)

    draft = subprocess.check_output(('towncrier', '--draft'), cwd=ROOT)
    # NOTE(vytas): towncrier --draft does not seem to use the template,
    #   so we substitute manually.
    rendered = template.replace(b'.. towncrier release notes start', draft, 1)
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


if __name__ == '__main__':
    target = get_target_filename()
    render_draft(target)
    build_docs()
