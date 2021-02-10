# Copyright 2021 by Kurt Griffiths
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

"""Private args module extension for Sphinx.

This extension exludes underscore-prefixed args and kwargs from the function
signature.
"""


def _on_process_signature(app, what, name, obj, options, signature, return_annotation):
    if what in ('function', 'method') and signature and '_' in signature:
        filtered = []

        for token in signature[1:-1].split(','):
            token = token.strip()

            if not token.startswith('_'):
                filtered.append(token)

        signature = f'({", ".join(filtered)})'

    return signature, return_annotation


def setup(app):
    app.connect('autodoc-process-signature', _on_process_signature)

    return {'parallel_read_safe': True}
