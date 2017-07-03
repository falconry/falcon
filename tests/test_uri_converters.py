import string

import pytest

from falcon.routing import converters


@pytest.mark.parametrize('segment,num_digits,min,max,expected', [
    ('123', None, None, None, 123),
    ('01', None, None, None, 1),
    ('001', None, None, None, 1),
    ('0', None, None, None, 0),
    ('00', None, None, None, 00),

    ('1', 1, None, None, 1),
    ('12', 1, None, None, None),
    ('12', 2, None, None, 12),

    ('1', 1, 1, 1, 1),
    ('1', 1, 1, None, 1),
    ('1', 1, 1, 2, 1),
    ('1', 1, 2, None, None),
    ('1', 1, 2, 1, None),
    ('2', 1, 1, 2, 2),
    ('2', 1, 2, 2, 2),
    ('3', 1, 1, 2, None),

    ('12', 1, None, None, None),
    ('12', 1, 1, 12, None),
    ('12', 2, None, None, 12),
    ('12', 2, 1, 12, 12),
    ('12', 2, 12, 12, 12),
    ('12', 2, 13, 12, None),
    ('12', 2, 13, 13, None),
])
def test_int_filter(segment, num_digits, min, max, expected):
    c = converters.IntConverter(num_digits, min, max)
    assert c.convert(segment) == expected


@pytest.mark.parametrize('segment', (
    ['0x0F', 'something', '', ' '] +
    ['123' + w for w in string.whitespace] +
    [w + '123' for w in string.whitespace]
))
def test_int_filter_malformed(segment):
    c = converters.IntConverter()
    assert c.convert(segment) is None


@pytest.mark.parametrize('num_digits', [0, -1, -10])
def test_int_filter_invalid_config(num_digits):
    with pytest.raises(ValueError):
        converters.IntConverter(num_digits)
