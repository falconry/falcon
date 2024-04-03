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
