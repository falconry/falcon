#!/usr/bin/env python
# Copyright 2013 by Rackspace Hosting, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Script that prints out the routes of an API instance.
"""

from __future__ import print_function

from functools import partial
import inspect

import falcon


def print_routes(api, verbose=False):  # pragma: no cover
    """
    Initial call.

    :param api: The falcon.API or callable that returns an instance to look at.
    :type api: falcon.API or callable
    :param verbose: If the output should be verbose.
    :type verbose: bool
    """
    traverse(api._router._roots, verbose=verbose)


def traverse(roots, parent='', verbose=False):
    """
    Recursive call which also handles printing output.

    :param api: The falcon.API or callable that returns an instance to look at.
    :type api: falcon.API or callable
    :param parent: The parent uri path to the current iteration.
    :type parent: str
    :param verbose: If the output should be verbose.
    :type verbose: bool
    """
    for root in roots:
        if root.method_map:
            print('->', parent + '/' + root.raw_segment)
            if verbose:
                for method, func in root.method_map.items():
                    if func.__name__ != 'method_not_allowed':
                        if isinstance(func, partial):
                            real_func = func.func
                        else:
                            real_func = func

                        try:
                            source_file = inspect.getsourcefile(real_func)
                            source_lines = inspect.getsourcelines(real_func)
                            source_info = '{}:{}'.format(source_file,
                                                         source_lines[1])
                        except TypeError:
                            # NOTE(vytas): If Falcon is cythonized, all default
                            # responders coming from cythonized modules will
                            # appear as built-in functions, and raise a
                            # TypeError when trying to locate the source file.
                            source_info = '[unknown file]'

                        print('-->' + method, source_info)

        if root.children:
            traverse(root.children, parent + '/' + root.raw_segment, verbose)


def main():
    """
    Main entrypoint.
    """
    import argparse

    parser = argparse.ArgumentParser(
        description='Example: print-api-routes myprogram:app')
    parser.add_argument(
        '-v', '--verbose', action='store_true',
        help='Prints out information for each method.')
    parser.add_argument(
        'api_module',
        help='The module and api to inspect. Example: myapp.somemodule:api',
    )
    args = parser.parse_args()

    try:
        module, instance = args.api_module.split(':', 1)
    except ValueError:
        parser.error(
            'The api_module must include a colon between '
            'the module and instance')
    api = getattr(__import__(module, fromlist=[True]), instance)
    if not isinstance(api, falcon.API):
        if callable(api):
            api = api()
            if not isinstance(api, falcon.API):
                parser.error(
                    '{0} did not return a falcon.API instance'.format(
                        args.api_module))
        else:
            parser.error(
                'The instance must be of falcon.API or be '
                'a callable without args that returns falcon.API')
    print_routes(api, verbose=args.verbose)


if __name__ == '__main__':
    main()
