# Copyright 2023-2024 by Vytautas Liuolia.
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

"""Media (aka MIME) type parsing and matching utilities."""

from __future__ import annotations

from typing import Dict, Iterator, Tuple

__all__ = ('parse_header',)


def _parse_param_old_stdlib(s: str) -> Iterator[str]:
    while s[:1] == ';':
        s = s[1:]
        end = s.find(';')
        while end > 0 and (s.count('"', 0, end) - s.count('\\"', 0, end)) % 2:
            end = s.find(';', end + 1)
        if end < 0:
            end = len(s)
        f = s[:end]
        yield f.strip()
        s = s[end:]


def _parse_header_old_stdlib(line: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    Note:
        This method has been copied (almost) verbatim from CPython 3.8 stdlib.
        It is slated for removal from the stdlib in 3.13.
    """
    parts = _parse_param_old_stdlib(';' + line)
    key = parts.__next__()
    pdict: Dict[str, str] = {}
    for p in parts:
        i = p.find('=')
        if i >= 0:
            name = p[:i].strip().lower()
            value = p[i + 1 :].strip()
            if len(value) >= 2 and value[0] == value[-1] == '"':
                value = value[1:-1]
                value = value.replace('\\\\', '\\').replace('\\"', '"')
            pdict[name] = value
    return key, pdict


def parse_header(line: str) -> Tuple[str, Dict[str, str]]:
    """Parse a Content-type like header.

    Return the main content-type and a dictionary of options.

    Args:
        line: A header value to parse.

    Returns:
        tuple: (the main content-type, dictionary of options).

    Note:
        This function replaces an equivalent method previously available in the
        stdlib as ``cgi.parse_header()``.
        It was removed from the stdlib in Python 3.13.
    """
    if '"' not in line and '\\' not in line:
        key, semicolon, parts = line.partition(';')
        if not semicolon:
            return (key.strip(), {})

        pdict = {}
        for part in parts.split(';'):
            name, equals, value = part.partition('=')
            if equals:
                pdict[name.strip().lower()] = value.strip()

        return (key.strip(), pdict)

    return _parse_header_old_stdlib(line)
