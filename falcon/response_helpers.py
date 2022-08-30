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

"""Utilities for the Response class."""

from falcon.util import uri
from falcon.util.misc import isascii
from falcon.util.misc import secure_filename


def header_property(name, doc, transform=None):
    """Create a header getter/setter.

    Args:
        name: Header name, e.g., "Content-Type"
        doc: Docstring for the property
        transform: Transformation function to use when setting the
            property. The value will be passed to the function, and
            the function should return the transformed value to use
            as the value of the header (default ``None``).

    """
    normalized_name = name.lower()

    def fget(self):
        try:
            return self._headers[normalized_name]
        except KeyError:
            return None

    if transform is None:

        def fset(self, value):
            if value is None:
                try:
                    del self._headers[normalized_name]
                except KeyError:
                    pass
            else:
                self._headers[normalized_name] = str(value)

    else:

        def fset(self, value):
            if value is None:
                try:
                    del self._headers[normalized_name]
                except KeyError:
                    pass
            else:
                self._headers[normalized_name] = transform(value)

    def fdel(self):
        del self._headers[normalized_name]

    return property(fget, fset, fdel, doc)


def format_range(value):
    """Format a range header tuple per the HTTP spec.

    Args:
        value: ``tuple`` passed to `req.range`
    """

    # PERF(kgriffs): % was found to be faster than str.format(),
    # string concatenation, and str.join() in this case.

    if len(value) == 4:
        result = '%s %s-%s/%s' % (value[3], value[0], value[1], value[2])
    else:
        result = 'bytes %s-%s/%s' % (value[0], value[1], value[2])

    return result


def format_content_disposition(value, disposition_type='attachment'):
    """Format a Content-Disposition header given a filename."""

    # NOTE(vytas): RFC 6266, Appendix D.
    #   Include a "filename" parameter when US-ASCII ([US-ASCII]) is
    #   sufficiently expressive.
    if isascii(value):
        return '%s; filename="%s"' % (disposition_type, value)

    # NOTE(vytas): RFC 6266, Appendix D.
    #   * Include a "filename*" parameter where the desired filename cannot be
    #     expressed faithfully using the "filename" form.  Note that legacy
    #     user agents will not process this, and will fall back to using the
    #     "filename" parameter's content.
    #   * When a "filename*" parameter is sent, to also generate a "filename"
    #     parameter as a fallback for user agents that do not support the
    #     "filename*" form, if possible.
    #   * When a "filename" parameter is included as a fallback (as per above),
    #     "filename" should occur first, due to parsing problems in some
    #     existing implementations.
    return "%s; filename=%s; filename*=UTF-8''%s" % (
        disposition_type,
        secure_filename(value),
        uri.encode_value(value),
    )


def format_etag_header(value):
    """Format an ETag header, wrap it with " " in case of need."""

    if value[-1] != '"':
        value = '"' + value + '"'

    return value


def format_header_value_list(iterable):
    """Join an iterable of strings with commas."""
    return ', '.join(iterable)


def is_ascii_encodable(s):
    """Check if argument encodes to ascii without error."""
    try:
        s.encode('ascii')
    except UnicodeEncodeError:
        # NOTE(tbug): Py3 will raise this if string contained
        # chars that could not be ascii encoded
        return False
    except AttributeError:
        # NOTE(tbug): s is probably not a string type
        return False
    return True
