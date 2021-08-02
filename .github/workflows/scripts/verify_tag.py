import argparse
from os import environ
from pathlib import Path

# See https://docs.github.com/en/actions/reference/environment-variables
ENV_VARIABLE = 'GITHUB_REF'


def go():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'folder', help='Directory where to look for wheels and source dist'
    )

    args = parser.parse_args()

    if ENV_VARIABLE not in environ:
        raise RuntimeError('Expected to find %r in environ' % ENV_VARIABLE)

    directory = Path(args.folder)
    candidates = list(directory.glob('*.whl')) + list(directory.glob('*.tar.gz'))
    if not candidates:
        raise RuntimeError('No wheel or source dist found in folder ' + args.folder)
    raw_value = environ[ENV_VARIABLE]
    tag_value = raw_value.split('/')[-1]

    errors = []
    for candidate in candidates:
        name = candidate.stem
        if name.endswith('.tar'):
            name = name[:-4]
        parts = name.split('-')
        if len(parts) < 2:
            errors.append(str(candidate))
            continue
        version = parts[1]
        if version.lower() != tag_value.lower():
            errors.append(str(candidate))

    if errors:
        raise RuntimeError(
            'Expected to find only wheels or or source dist with tag %r'
            '(from env variable value %r). Found instead %s'
            % (tag_value, raw_value, errors)
        )
    print('Found %s wheels or source dist with tag %r' % (len(candidates), tag_value))


if __name__ == '__main__':
    go()
