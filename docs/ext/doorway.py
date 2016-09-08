# Copyright 2016 by Rackspace Hosting, Inc.
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

"""Doorway module extension for Sphinx.

This extension modifies the way the top-level "falcon" doorway module
is documented.
"""


def _on_process_docstring(app, what, name, obj, options, lines):
    """Process the docstring for a given python object."""

    # NOTE(kgriffs): Suppress the top-level docstring since it is
    #   typically used with autodoc on rst pages that already have their
    #   own introductory texts, tailored to a specific subset of
    #   things that have been hoisted into the 'falcon' doorway module.
    if what == 'module' and name == 'falcon':
        lines[:] = []


def setup(app):
    app.connect('autodoc-process-docstring', _on_process_docstring)

    return {'parallel_read_safe': True}
