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

"""RFC extension for Sphinx.

This extensions adds hyperlinking for any RFC references that are
formatted like this::

    RFC 7231; Section 6.5.3
"""

import re

IETF_DOCS = 'https://datatracker.ietf.org/doc/html'
RFC_PATTERN = re.compile(r'RFC (\d{4}), Section ([\d\.]+)')


def _render_section(section_number, rfc_number):
    template = '`{0} <https://tools.ietf.org/html/rfc{1}#section-{0}>`_'
    return template.format(section_number, rfc_number)


def _process_line(line):
    m = RFC_PATTERN.search(line)
    if not m:
        return line

    rfc = m.group(1)
    section = m.group(2)

    template = (
        '`RFC {rfc}, Section {section} <{ietf_docs}/rfc{rfc}#section-{section}>`__'
    )

    rendered_text = template.format(rfc=rfc, section=section, ietf_docs=IETF_DOCS)

    return line[: m.start()] + rendered_text + line[m.end() :]


def _on_process_docstring(app, what, name, obj, options, lines):
    """Process the docstring for a given python object."""

    if what == 'module' and name == 'falcon':
        lines[:] = []
        return

    lines[:] = [_process_line(line) for line in lines]


def setup(app):
    app.connect('autodoc-process-docstring', _on_process_docstring)

    return {'parallel_read_safe': True}
