#!/usr/bin/env python

import argparse
import pathlib
import subprocess

import pprint

import requests
import toml

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent

FALCON_COMMITS_API = 'https://api.github.com/repos/falconry/falcon/commits'


def get_count_since_last_tag():
    output = subprocess.check_output(('git', 'describe', '--abbrev=40'))
    output = output.decode()
    if '-' not in output:
        return 0
    return int(output.split('-')[1])


def query_contributors(count=None):
    if count is None:
        count = get_count_since_last_tag()

    remaining = count
    result = {}
    page = 1
    uri = f'{FALCON_COMMITS_API}?page={page}'

    while remaining > 0:
        commits = requests.get(uri).json()
        for commit in commits:
            remaining -= 1
            print(remaining)

            login = commit['author'].get('login')
            pprint.pprint(
                [commit['sha'], login, commit['commit']['author'].get('date')]
            )
            if remaining <= 0:
                break
            if not login or login in result:
                continue
            result[login] = commit['commit']['author']['name']

        page += 1
        uri = f'{FALCON_COMMITS_API}?page={page}'

    return result


def get_towncrier_filename():
    with open(ROOT / 'pyproject.toml') as pyproject_toml:
        project = toml.load(pyproject_toml)
    return project['tool']['towncrier']['filename']


def main():
    towncrier_file = get_towncrier_filename()

    description = (
        'Find new contributors to Falcon since the last stable release. '
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
        '--no-towncrier', action='store_true', help=f'do not write {towncrier_file}'
    )
    args = parser.parse_args()

    contributors = query_contributors()
    pprint.pprint(contributors)


if __name__ == '__main__':
    main()
