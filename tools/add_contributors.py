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
    authors = []
    for commit in iter_commits(until):
        login = commit['author'].get('login')
        if not login:
            continue
        authors.append((login, commit['commit']['author']['name']))

    seen = set()
    result = {}
    for login, name in reversed(authors):
        if login not in seen:
            seen.add(login)
        result[login] = name

    return result


def _get_towncrier_filename():
    with open(ROOT / 'pyproject.toml') as pyproject_toml:
        project = toml.load(pyproject_toml)
    return project['tool']['towncrier']['filename']


def _update_authors(contributors):
    pass


def _update_towncrier_template(template, contributors):
    pass


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
