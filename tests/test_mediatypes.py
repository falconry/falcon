import itertools

import pytest

from falcon import errors
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


def test_media_type_private_cls():
    mt1 = mediatypes._MediaType.parse('image/png')
    assert mt1.main_type == 'image'
    assert mt1.subtype == 'png'
    assert mt1.params == {}

    mt2 = mediatypes._MediaType.parse('text/plain; charset=latin-1')
    assert mt2.main_type == 'text'
    assert mt2.subtype == 'plain'
    assert mt2.params == {'charset': 'latin-1'}


def test_media_range_private_cls():
    mr1 = mediatypes._MediaRange.parse('image/png')
    assert mr1.main_type == 'image'
    assert mr1.subtype == 'png'
    assert mr1.quality == 1.0
    assert mr1.params == {}

    mr2 = mediatypes._MediaRange.parse('text/plain; charset=latin-1; Q=0.9')
    assert mr2.main_type == 'text'
    assert mr2.subtype == 'plain'
    assert pytest.approx(mr2.quality) == 0.9
    assert mr2.params == {'charset': 'latin-1'}

    mr3 = mediatypes._MediaRange.parse('*; q=0.7')
    assert mr3.main_type == '*'
    assert mr3.subtype == '*'
    assert pytest.approx(mr3.quality) == 0.7
    assert mr3.params == {}


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
    ('text/plain;format=flowed', 1.0),
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
            (_RFC_9110_EXAMPLE_ACCEPT, _RFC_9110_EXAMPLE_VALUES),
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
    'accept,media_type,quality_value',
    [
        (
            'application/*, */wildcard; q=0.7, */*; q=0.25',
            'test/wildcard; expect=pass',
            0.7,
        ),
        (
            'application/*, */wildcard; q=0.7, */*; q=0.25',
            'application/wildcard; expect=pass',
            1.0,
        ),
        (
            'application/*, */wildcard; q=0.7, */*; q=0.25',
            'test/something; expect=pass',
            0.25,
        ),
        (
            'text/x-python, text/*; q=0.33, text/plain; format=fixed',
            'text/plain; format=flowed',
            0.33,
        ),
        (
            # NOTE(vytas): Same as one of the RFC 7231 examples, just with some
            #   media ranges reordered. python-mimeparse fails to yield the
            #   correct result in this specific case.
            'text/*;q=0.3, text/html;level=1, text/html;q=0.7, '
            'text/html;level=2;q=0.4, */*;q=0.5',
            'text/html; level=3',
            0.7,
        ),
    ],
)
def test_quality(accept, media_type, quality_value):
    assert pytest.approx(mediatypes.quality(media_type, accept)) == quality_value


@pytest.mark.parametrize(
    'accept,media_type',
    [
        (
            'foo/bar, test/app; q=0.2, test/app; p=1; q=0.9, test/app;p=1;r=2',
            'test/app',
        ),
        ('test/app; q=0.1, test/app; p=1; q=0.2, test/app;p=1;r=2', 'test/app; p=1'),
        (
            '*/app; q=0.1, simple/app; test=true; q=0.2, simple/app; color=blue',
            'simple/app; test=true',
        ),
    ],
)
def test_quality_prefer_exact_match(accept, media_type):
    assert pytest.approx(mediatypes.quality(media_type, accept)) == 0.2


_QUALITY_NONE_MATCHES_EXAMPLES = [
    ('application/json', 'application/yaml'),
    ('audio/*; q=0.2, audio/basic', 'video/mp3'),
    (
        'falcon/peregrine; speed=high; unladen=true',
        'falcon/peregrine; speed=average',
    ),
    ('text/html, text/plain', 'text/x-python'),
    ('*/json; q=0.2, application/json', 'application/msgpack'),
    (
        'text/x-python, image/*; q=0.33, text/plain; format=fixed',
        'text/plain; format=flowed',
    ),
]


@pytest.mark.parametrize('accept,media_type', _QUALITY_NONE_MATCHES_EXAMPLES)
def test_quality_none_matches(accept, media_type):
    assert mediatypes.quality(media_type, accept) == 0.0


@pytest.mark.parametrize(
    'media_types,accept,expected',
    [
        (['application/json'], 'application/json', 'application/json'),
        (['application/json'], 'application/json; charset=utf-8', 'application/json'),
        (
            ['application/json', 'application/yaml'],
            'application/json, */*; q=0.2',
            'application/json',
        ),
    ],
)
def test_best_match(media_types, accept, expected):
    assert mediatypes.best_match(media_types, accept) == expected


_BEST_MATCH_NONE_MATCHES_EXAMPLES = [
    ([_mt], _acc) for _mt, _acc in _QUALITY_NONE_MATCHES_EXAMPLES
] + [
    (['application/json', 'application/yaml'], 'application/xml, text/*; q=0.7'),
    (
        ['text/plain', 'falcon/peregrine; load=unladen'],
        'falcon/peregrine; load=heavy',
    ),
]


@pytest.mark.parametrize('media_types,accept', _BEST_MATCH_NONE_MATCHES_EXAMPLES)
def test_best_match_none_matches(media_types, accept):
    assert mediatypes.best_match(media_types, accept) == ''


@pytest.mark.parametrize('media_type', ['', 'word document', 'text'])
def test_invalid_media_type(media_type):
    with pytest.raises(errors.InvalidMediaType):
        mediatypes.quality(media_type, '*/*')


def _generate_strings(items):
    yield from items


@pytest.mark.parametrize(
    'media_range',
    [
        '',
        'word document',
        'text',
        'text/plain; q=high',
        '*/*; q=inf',
        '*/*; q=-inf',
        '*/*; q=nan',
        'application/very-important; q=1337.0',
    ],
)
def test_invalid_media_range(media_range):
    with pytest.raises(errors.InvalidMediaRange):
        mediatypes.quality('falcon/peregrine', media_range)

    with pytest.raises(errors.InvalidMediaRange):
        mediatypes.best_match(_generate_strings(['falcon/peregrine']), media_range)


@pytest.mark.parametrize(
    'accept',
    ['*/*', 'application/xml, text/*; q=0.7, */*; q=0.3'],
)
@pytest.mark.parametrize('media_types', [(), [], {}, _generate_strings(())])
def test_empty_media_types(accept, media_types):
    assert mediatypes.best_match(media_types, accept) == ''
