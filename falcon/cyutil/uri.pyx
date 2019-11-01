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


cdef unicode cy_decode(unsigned char* data, Py_ssize_t start,  Py_ssize_t end,
                       Py_ssize_t encoded_start):
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

            if data[pos] == b'+':
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

        return result[:dst_start + end - src_start].decode()

    finally:
        PyMem_Free(result)


cdef cy_parse_query_string(unsigned char* data, Py_ssize_t length, bint keep_blank):
    cdef Py_ssize_t pos
    cdef unsigned char current

    cdef Py_ssize_t start = 0
    cdef Py_ssize_t encoded_start_key = -1
    cdef Py_ssize_t encoded_start_val = -1
    cdef Py_ssize_t partition = -1

    cdef unicode key
    cdef unicode value
    cdef dict result = {}

    for pos in range(length):
        # PERF(vytas): Quick check if we need to do anything special with the
        #   current character.
        #   Cython should translate this check into a switch statement.
        if data[pos] not in b'&=%+':
            continue

        current = data[pos]

        if current == b'&':
            if pos > start:
                if partition >= 0:
                    key = cy_decode(data, start, partition, encoded_start_key)
                    value = cy_decode(data, partition+1, pos, encoded_start_val)
                else:
                    key = cy_decode(data, start, pos, encoded_start_key)
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

        # else: current in b'%+'

        # PERF(vytas): Record positions of the first encoded character, if any.
        #  This will be used to determine where to start decoding, if at all.
        if partition < 0:
            if encoded_start_key < 0:
                encoded_start_key = pos
        else:
            if encoded_start_val < 0:
                encoded_start_val = pos

    if length > start:
        if partition >= 0:
            key = cy_decode(data, start, partition, encoded_start_key)
            value = cy_decode(data, partition+1, length, encoded_start_val)
        else:
            key = cy_decode(data, start, length, encoded_start_key)
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


def parse_query_string(unicode query_string not None, bint keep_blank=False):
    cdef bytes byte_string = query_string.encode('ascii')
    cdef unsigned char* data = byte_string
    return cy_parse_query_string(data, len(byte_string), keep_blank)
