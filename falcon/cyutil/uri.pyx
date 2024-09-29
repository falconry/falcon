# Copyright 2019-2024 by Vytautas Liuolia.
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


from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libc.string cimport memcpy


cdef list build_hex_table():
    cdef list result = [-1] * 0x10000
    for ch1 in '0123456789abcdefABCDEF':
        for ch2 in '0123456789abcdefABCDEF':
            try:
                result[(ord(ch1) << 8) | ord(ch2)] = int(ch1 + ch2, 16)
            except ValueError:
                pass

    return result


# PERF(vytas): Cache hex characters lookup table
cdef int[0x10000] HEX_CHARS
HEX_CHARS[:] = build_hex_table()

# PERF(vytas): Cache an empty string object.
cdef EMPTY_STRING = u''


cdef inline int cy_decode_hex(unsigned char nibble1, unsigned char nibble2):
    return HEX_CHARS[(nibble1 << 8) | nibble2]


cdef unicode cy_decode(unsigned char* data, Py_ssize_t start, Py_ssize_t end,
                       Py_ssize_t encoded_start, bint unquote_plus):
    # PERF(vytas): encoded_start being -1 signifies that the caller
    #   (cy_parse_query_string) has already verified that no encoding
    #   characters exist in the provided substring data[start:end].
    if encoded_start < 0:
        return data[start:end].decode()

    cdef unsigned char* result
    cdef Py_ssize_t src_start = start
    cdef Py_ssize_t dst_start = 0
    cdef Py_ssize_t pos
    cdef int decoded

    result = <unsigned char*> PyMem_Malloc(end - start)
    if not result:
        raise MemoryError()

    try:
        for pos in range(encoded_start, end):
            if data[pos] not in b'+%':
                continue

            if src_start < pos:
                memcpy(result + dst_start, data + src_start,
                       pos - src_start)

            dst_start += pos - src_start
            src_start = pos

            if data[pos] == b'+' and unquote_plus:
                result[dst_start] = b' '
                dst_start += 1
                src_start += 1
                continue

            # NOTE(vytas): Else %
            if pos < end - 2:
                decoded = cy_decode_hex(data[pos+1], data[pos+2])
                if decoded < 0:
                    continue

                # NOTE(vytas): Succeeded decoding a byte
                result[dst_start] = decoded
                dst_start += 1
                src_start += 3
                # NOTE(vytas): It is somewhat ugly to wind the loop variable
                #   like that, but hopefully it is a lesser sin in C.
                pos += 2

        if src_start < end:
            memcpy(result + dst_start, data + src_start,
                   end - src_start)

        return result[:dst_start + end - src_start].decode('utf-8', 'replace')

    finally:
        PyMem_Free(result)


cdef cy_handle_csv(dict result, bint keep_blank, unicode key, bytes value):
    # NOTE(kgriffs): Falcon supports a more compact form of lists, in which the
    # elements are comma-separated and assigned to a single param instance. If
    # it turns out that very few people use this, it can be deprecated at some
    # point.

    # NOTE(vytas): This case of csv=True is no longer the default request
    # option so we largely reimplement the unoptimized Python version here.

    cdef old_value = result.get(key)
    cdef list additional_values
    cdef unicode decoded

    # NOTE(steffgrez): Falcon decodes value at the last moment. So query parser
    # won't mix up between percent-encoded comma (as value) and comma-separated
    # list (as reserved character for sub-delimiter).
    if b',' in value:
        # NOTE(kgriffs,vytas): Normalize the result in the case that some
        #   elements are empty strings, such that the result will be the same
        #   for 'foo=1,,3' as 'foo=1&foo=&foo=3'
        #   (but only if keep_blank is set to False).
        additional_values = [
            cy_decode(element, 0, len(element), 0, True)
            for element in value.split(b',') if keep_blank or element
        ]

        if old_value is None:
            result[key] = additional_values
        elif isinstance(old_value, list):
            old_value.extend(additional_values)
        else:
            additional_values.insert(0, old_value)
            result[key] = additional_values

    else:
        decoded = cy_decode(value, 0, len(value), 0, True)

        if old_value is None:
            result[key] = decoded
        elif isinstance(old_value, list):
            old_value.append(decoded)
        else:
            result[key] = [old_value, decoded]


cdef cy_parse_query_string(unsigned char* data, Py_ssize_t length,
                           bint keep_blank, bint csv):
    cdef Py_ssize_t pos
    cdef unsigned char current

    cdef Py_ssize_t start = 0
    cdef Py_ssize_t encoded_start_key = -1
    cdef Py_ssize_t encoded_start_val = -1
    cdef Py_ssize_t partition = -1

    cdef unicode key
    cdef unicode value
    cdef old_value
    cdef dict result = {}

    for pos in range(length):
        # PERF(vytas): Quick check if we need to do anything special with the
        #   current character.
        #   Cython should translate this check into a switch statement.
        if data[pos] not in b'%&+,=':
            continue

        current = data[pos]

        if current == b'&':
            # TODO(vytas): DRY this with the "if length > start" block below.
            #   Keep them in sync until they are improved to share code.
            if pos > start:
                if partition >= 0:
                    key = cy_decode(data, start, partition, encoded_start_key, True)
                    if csv and encoded_start_val >= 0:
                        cy_handle_csv(result, keep_blank, key, data[partition+1:pos])
                        start = pos + 1
                        encoded_start_key = -1
                        encoded_start_val = -1
                        partition = -1
                        continue

                    value = cy_decode(data, partition+1, pos, encoded_start_val, True)
                else:
                    key = cy_decode(data, start, pos, encoded_start_key, True)
                    value = EMPTY_STRING

                if value is not EMPTY_STRING or keep_blank:
                    old_value = result.get(key)

                    if old_value is None:
                        result[key] = value
                    elif isinstance(old_value, list):
                        old_value.append(value)
                    else:
                        result[key] = [old_value, value]

            start = pos + 1
            encoded_start_key = -1
            encoded_start_val = -1
            partition = -1
            continue

        if current == b'=':
            if partition < 0:
                partition = pos
            continue

        # else: current in b'%+,'

        # PERF(vytas): Record positions of the first encoded character, if any.
        #  This will be used to determine where to start decoding, if at all.
        if partition < 0:
            if encoded_start_key < 0:
                encoded_start_key = pos
        else:
            if encoded_start_val < 0:
                encoded_start_val = pos

    # NOTE(vytas): This block is largely the same (although not identical as it
    #   does not need to compute the endoded_start_* values) as the above
    #   "if pos > start" (see also the DRY TODO note earlier in this function).
    #   Keep them in sync until they are improved to share code.
    if length > start:
        if partition >= 0:
            key = cy_decode(data, start, partition, encoded_start_key, True)
            if csv and encoded_start_val >= 0:
                cy_handle_csv(result, keep_blank, key, data[partition+1:length])
                return result

            value = cy_decode(data, partition+1, length, encoded_start_val, True)
        else:
            key = cy_decode(data, start, length, encoded_start_key, True)
            value = EMPTY_STRING

        if value is not EMPTY_STRING or keep_blank:
            old_value = result.get(key)

            if old_value is None:
                result[key] = value
            elif isinstance(old_value, list):
                old_value.append(value)
            else:
                result[key] = [old_value, value]

    return result


def parse_query_string(unicode query_string not None, bint keep_blank=False,
                       bint csv=False):
    cdef bytes byte_string = query_string.encode('utf-8')
    cdef unsigned char* data = byte_string
    return cy_parse_query_string(data, len(byte_string), keep_blank, csv)


def decode(unicode encoded_uri not None, bint unquote_plus=True):
    cdef bytes byte_string = encoded_uri.encode('utf-8')
    cdef unsigned char* data = byte_string
    return cy_decode(data, 0, len(byte_string), 0, unquote_plus)
