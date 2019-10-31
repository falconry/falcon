# PERF(vytas): Cache an empty string object.
cdef EMPTY_STRING = u''


cdef unicode cy_decode(unsigned char* data, Py_ssize_t start,  Py_ssize_t end,
                       Py_ssize_t encoded_start):
    # TODO(vytas): Implement actual decoding
    return data[start:end].decode()


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
            encoded_start_key = pos
        else:
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
