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
Script that prints out the routes of an App instance.
"""
import importlib

import falcon
from falcon.util.inspect import inspect_app, inspect_routes


def print_routes(api, verbose=False):
    routes = inspect_routes(api)
    for route in routes:
        print(route.as_string(verbose))


def make_parser():
    "Creates the parsed or the application"
    import argparse

    parser = argparse.ArgumentParser(
        description="Example: falcon-print-routes myprogram:app"
    )
    parser.add_argument(
        "-r",
        "--route_only",
        action="store_true",
        help="Prints only the information regarding the routes",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Prints out information for each method.",
    )
    parser.add_argument(
        "app_module",
        help="The module and app to inspect. Example: myapp.somemodule:api",
    )
    return parser


def load_app(parser, args):

    try:
        module, instance = args.app_module.split(":", 1)
    except ValueError:
        parser.error(
            "The app_module must include a colon between the module and instance"
        )

    app = getattr(importlib.import_module(module), instance)
    if not isinstance(app, falcon.App):
        if callable(app):
            app = app()
            if not isinstance(app, falcon.App):
                parser.error(
                    "{0} did not return a falcon.App instance".format(args.app_module)
                )
        else:
            parser.error(
                "The instance must be of falcon.App or be "
                "a callable without args that returns falcon.App"
            )
    return app


def main():
    """
    Main entrypoint.
    """
    parser = make_parser()
    args = parser.parse_args()
    app = load_app(parser, args)
    if args.route_only:
        print_routes(app, verbose=args.verbose)
    else:
        print(inspect_app(app).as_string(args.verbose))


if __name__ == "__main__":
    main()
