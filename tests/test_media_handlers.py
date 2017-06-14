import pytest

from falcon import media


@pytest.mark.parametrize('key', ['', None])
def test_set_invalid_handlers(key):
    handlers = media.Handlers()

    with pytest.raises(ValueError) as err:
        handlers[''] = 'nope'

    assert str(err.value) == 'Media Type cannot be None or an empty string'


def test_base_handler_contract():
    class TestHandler(media.BaseHandler):
        pass

    with pytest.raises(TypeError) as err:
        TestHandler()

    assert 'abstract methods deserialize, load, serialize' in str(err.value)
