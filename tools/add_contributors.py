#!/usr/bin/env python

import argparse
import pathlib
import re

import requests
import toml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

FALCON_CREATOR = 'kgriffs'
FALCON_REPOSITORY_API = 'https://api.github.com/repos/falconry/falcon'

STABLE_RELEASE_TAG = r'^\d+\.\d+\.\d+(\.post\d+)?$'

AUTHORS_SEPARATOR = '\n(et al.)\n\n'
AUTHORS_LINE = r'^\* (?:(?:.+ \(([\w-]+)\)$)|([\w-]+$))'

RST_CONTRIBUTOR_LINE = r'- `[\w-]+ <https://github.com/([\w-]+)>`__?\n'
RST_CONTRIBUTOR_TEMPLATE = '- `{login} <https://github.com/{login}>`__\n'


def get_latest_tag():
    uri = f'{FALCON_REPOSITORY_API}/tags'
    for tag in requests.get(uri).json():
        if re.match(STABLE_RELEASE_TAG, tag['name']):
            return tag['name'], tag['commit']['sha']


def iter_commits(until=None):
    page = 1
    uri = f'{FALCON_REPOSITORY_API}/commits'

    while commits := requests.get(uri).json():
        for commit in commits:
            if until and commit['sha'] == until:
                return
            yield commit

        page += 1
        uri = f'{FALCON_REPOSITORY_API}/commits?page={page}'


def aggregate_contributors(until=None):
    result = {}
    for commit in iter_commits(until):
        login = commit['author'].get('login')
        if not login:
            continue
        if login in result:
            result.pop(login)
        # NOTE(vytas): Exploit dictionary ordering in Python 3.7+.
        result[login] = commit['commit']['author']['name']

    return dict(item for item in reversed(result.items()))


def _get_towncrier_filename():
    with open(ROOT / 'pyproject.toml', 'r') as pyproject_toml:
        project = toml.load(pyproject_toml)
    return project['tool']['towncrier']['filename']


def _update_authors(contributors):
    with open(ROOT / 'AUTHORS', 'r') as authors_file:
        content = authors_file.read()

    authors, separator, footer = content.partition(AUTHORS_SEPARATOR)
    assert separator, 'AUTHORS file structure not understood, please inspect manually'

    existing = set({FALCON_CREATOR})
    for line in reversed(authors.splitlines()):
        match = re.match(AUTHORS_LINE, line)
        if not match:
            break
        login = match.group(1) or match.group(2)
        existing.add(login.lower())

    with open(ROOT / 'AUTHORS', 'w') as authors_file:
        authors_file.write(authors)

        for login, name in contributors.items():
            if login.lower() in existing:
                continue
            if login == name:
                authors_file.write(f'* {login}\n')
            else:
                authors_file.write(f'* {name} ({login})\n')

        authors_file.write(separator)
        authors_file.write(footer)


def _update_towncrier_template(template, contributors):
    with open(template, 'r') as template_file:
        content = template_file.read()

    content, *matches = re.split(RST_CONTRIBUTOR_LINE, content)

    contributors = set(contributors)
    contributors.update(matches[::2])
    for separator in matches[1::2]:
        assert (
            separator == ''
        ), f'unexpected separator between contributor lines: {separator!r}'

    with open(template, 'w') as template_file:
        template_file.write(content)

        for login in sorted(contributors, key=lambda s: s.lower()):
            template_file.write(RST_CONTRIBUTOR_TEMPLATE.format(login=login))


def main():
    towncrier_template = _get_towncrier_filename()

    description = (
        'Find new contributors to Falcon since the last Git tag. '
        'Optionally append them to AUTHORS and the active Towncrier template.'
    )
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-n', '--dry-run', action='store_true', help='dry run: do not write any files'
    )
    parser.add_argument(
        '--no-authors', action='store_true', help='do not write AUTHORS'
    )
    parser.add_argument(
        '--no-towncrier', action='store_true', help=f'do not write {towncrier_template}'
    )
    args = parser.parse_args()

    tag, commit = get_latest_tag()
    contributors = aggregate_contributors(until=commit)

    if contributors:
        print(f'Contributors since the latest stable tag ({tag}):')
        for login, name in contributors.items():
            print(f' * {name} ({login})')
    else:
        print('No contributors (with a GitHub account) found since the latest tag.')
        return

    if not args.dry_run:
        if not args.no_authors:
            _update_authors(contributors)
        if not args.no_towncrier:
            _update_towncrier_template(towncrier_template, contributors)


if __name__ == '__main__':
    main()
