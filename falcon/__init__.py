"""A fast micro-framework for building cloud APIs."""
version_tuple = (0, 0, 1, '-dev')

def get_version_string():
    if isinstance(version_tuple[-1], basestring):
        return '.'.join(map(str, version_tuple[:-1])) + version_tuple[-1]

    return '.'.join(map(str, version_tuple))

version = get_version_string()
"""Current version of Falcon."""

# Hoist classes and functions into the falcon namespace
from api import Api
from status_codes import *
