#!/usr/bin/env python

import argparse
import importlib.metadata
import sys

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

# NOTE: Installer tooling that may be present in any fresh virtualenv.
INSTALLER_TOOLING = frozenset({'pip', 'setuptools', 'wheel'})


def requirement_closure(names):
    """Return the given distributions together with their runtime requirements."""
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


def unexpected_distributions(allowed):
    installed = {
        canonicalize_name(dist.metadata['Name'])
        for dist in importlib.metadata.distributions()
    }
    return sorted(installed - requirement_closure(allowed) - INSTALLER_TOOLING)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check that no unexpected distributions are installed.'
    )
    parser.add_argument('allowed', nargs='+', help='allowed distributions')
    args = parser.parse_args()

    unexpected = unexpected_distributions(args.allowed)
    if unexpected:
        sys.exit(f'Unexpected distributions installed: {", ".join(unexpected)}')

    print('OK: no unexpected distributions installed.')
