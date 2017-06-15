import pytest

from falcon import media


def test_base_handler_contract():
    class TestHandler(media.BaseHandler):
        pass

    with pytest.raises(TypeError) as err:
        TestHandler()

    assert 'abstract methods deserialize, serialize' in str(err.value)
