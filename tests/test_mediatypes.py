import itertools

import pytest

from falcon.util import mediatypes


@pytest.mark.parametrize(
    'value,expected',
    [
        ('', ('', {})),
        ('strange', ('strange', {})),
        ('text/plain', ('text/plain', {})),
        ('text/plain ', ('text/plain', {})),
        (' text/plain', ('text/plain', {})),
        (' text/plain ', ('text/plain', {})),
        ('   text/plain   ', ('text/plain', {})),
        (
            'falcon/peregrine;  key1; key2=value; key3',
            ('falcon/peregrine', {'key2': 'value'}),
        ),
        (
            'audio/pcm;rate=48000;encoding=float;bits=32',
            ('audio/pcm', {'bits': '32', 'encoding': 'float', 'rate': '48000'}),
        ),
        (
            'falcon/*; genus=falco; family=falconidae; class=aves; ',
            ('falcon/*', {'class': 'aves', 'family': 'falconidae', 'genus': 'falco'}),
        ),
        ('"falcon/peregrine" ; key="value"', ('"falcon/peregrine"', {'key': 'value'})),
        ('falcon/peregrine; empty=""', ('falcon/peregrine', {'empty': ''})),
        ('falcon/peregrine; quote="', ('falcon/peregrine', {'quote': '"'})),
        ('text/plain; charset=utf-8', ('text/plain', {'charset': 'utf-8'})),
        ('stuff/strange; missing-value; missing-another', ('stuff/strange', {})),
        ('stuff/strange; missing-value\\missing-another', ('stuff/strange', {})),
        (
            'application/falcon; P1 = "key; value"; P2="\\""',
            ('application/falcon', {'p1': 'key; value', 'p2': '"'}),
        ),
    ],
)
def test_parse_header(value, expected):
    assert mediatypes.parse_header(value) == expected


_RFC_7231_EXAMPLE_ACCEPT = (
    'text/*;q=0.3, text/html;q=0.7, text/html;level=1, '
    'text/html;level=2;q=0.4, */*;q=0.5'
)
_RFC_7231_EXAMPLE_VALUES = [
    ('text/html;level=1', 1.0),
    ('text/html', 0.7),
    ('text/plain', 0.3),
    ('image/jpeg', 0.5),
    ('text/html;level=2', 0.4),
    ('text/html;level=3', 0.7),
]

_RFC_9110_EXAMPLE_ACCEPT = (
    'text/*;q=0.3, text/plain;q=0.7, text/plain;format=flowed, '
    'text/plain;format=fixed;q=0.4, */*;q=0.5'
)
# NOTE(vytas): Including the errata https://www.rfc-editor.org/errata/eid7138.
_RFC_9110_EXAMPLE_VALUES = [
    ('text/plain;format=flowed', 1),
    ('text/plain', 0.7),
    ('text/html', 0.3),
    ('image/jpeg', 0.5),
    ('text/plain;format=fixed', 0.4),
    ('text/html;level=3', 0.3),
]

_RFC_EXAMPLES = list(
    itertools.chain.from_iterable(
        ((accept,) + media_type_quality for media_type_quality in example_values)
        for accept, example_values in (
            (_RFC_7231_EXAMPLE_ACCEPT, _RFC_7231_EXAMPLE_VALUES),
            (_RFC_9110_EXAMPLE_ACCEPT, _RFC_7231_EXAMPLE_VALUES),
        )
    )
)

_RFC_EXAMPLE_IDS = list(
    itertools.chain.from_iterable(
        (
            f'{rfc}-{media_type}-{quality_value}'
            for media_type, quality_value in example_values
        )
        for rfc, example_values in (
            ('RFC-7231', _RFC_7231_EXAMPLE_VALUES),
            ('RFC-9110', _RFC_7231_EXAMPLE_VALUES),
        )
    )
)


@pytest.mark.parametrize(
    'accept,media_type,quality_value', _RFC_EXAMPLES, ids=_RFC_EXAMPLE_IDS
)
def test_quality_rfc_examples(accept, media_type, quality_value):
    assert pytest.approx(mediatypes.quality(media_type, accept)) == quality_value


@pytest.mark.parametrize(
    'accept,media_type',
    [
        ('application/json', 'application/yaml'),
        ('audio/*; q=0.2, audio/basic', 'video/mp3'),
        (
            'falcon/peregrine; speed=high; unladen=true',
            'falcon/peregrine; speed=average',
        ),
        ('text/html, text/plain', 'text/x-python'),
        ('*/json; q=0.2, application/json', 'application/msgpack'),
    ],
)
def test_quality_none_matches(accept, media_type):
    assert mediatypes.quality(media_type, accept) == 0.0
