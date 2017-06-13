import pytest

from falcon import media


@pytest.mark.parametrize('key', ['', None])
def test_set_invalid_handlers(key):
    handlers = media.Handlers()

    with pytest.raises(ValueError) as err:
        handlers[''] = 'nope'

    assert str(err.value) == 'Media Type cannot be None or an empty string'
