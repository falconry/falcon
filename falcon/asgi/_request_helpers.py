# Copyright 2019 by Kurt Griffiths
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

import inspect
import re


def header_property(header_name):
    """Create a read-only header property.

    Args:
        wsgi_name (str): Case-sensitive name of the header as it would
            appear in the WSGI environ ``dict`` (i.e., 'HTTP_*')

    Returns:
        A property instance than can be assigned to a class variable.

    """

    header_name = header_name.lower()

    def fget(self):
        try:
            return self._asgi_headers[header_name] or None
        except KeyError:
            return None

    return property(fget)


def fixup_wsgi_references(prop):
    fget = prop.fget
    src = inspect.getsource(fget)

    # NOTE(kgriffs): Fixup this special case so the following regex's
    #   will match.
    modified_src = src.replace('CONTENT_LENGTH', 'HTTP_CONTENT_LENGTH')

    # self.env['HTTP_HOST']
    modified_src = re.sub(
        r'self\.env\[["\']HTTP_([^"\']+)["\']\]',
        lambda m: 'self._asgi_headers["{}"]'.format(m.group(1).lower().replace('_', '-')),
        modified_src
    )

    # self.env.get('HTTP_IF_MATCH')
    modified_src = re.sub(
        r'self\.env\.get\(["\']HTTP_([^"\']+)["\']',
        lambda m: 'self._asgi_headers.get("{}"'.format(m.group(1).lower().replace('_', '-')),
        modified_src
    )

    modified_src = re.sub('^    ', '', modified_src, flags=re.MULTILINE)

    scope = inspect.currentframe().f_back.f_globals.copy()
    exec(compile(modified_src, '<string>', 'exec'), scope)

    return scope[fget.__name__]
