import unittest.mock as mock
import io
import json
import pytest

from falcon import media


def test_base_handler_contract():
    class TestHandler(media.BaseHandler):
        pass

    with pytest.raises(TypeError) as err:
        TestHandler()

    assert 'abstract methods deserialize, serialize' in str(err.value)



class TestJSONHandler(object):

    @staticmethod
    def mock_dumps(media, **kwargs):
        return json.dumps(
            {
                'media': media,
                'kwargs': kwargs,
            }
        )

    @staticmethod
    def mock_loads(stream, **kwargs):
        return {
            'stream': stream,
            'kwargs': kwargs,
        }

    @pytest.mark.parametrize(
        'body, kwargs, expected',
        [
            ('test', None, b'{"media": "test", "kwargs": {"ensure_ascii": false}}'),
            ('test', {'ensure_ascii': True}, b'{"media": "test", "kwargs": {"ensure_ascii": true}}'),
        ]
    )
    def test_custom_serialization(self, body, kwargs, expected):
        JH = media.JSONHandler(dumps=self.mock_dumps, dumps_kwargs=kwargs)
        assert JH.serialize(body, 'application/javacript') == expected

    @pytest.mark.parametrize(
        'body, kwargs',
        [
            (b'[1, 2]', {}),
            (b'[1, 2]', {'special_param': True}),
        ]
    )
    def test_custom_deserialization(self, body, kwargs):
        JH = media.JSONHandler(loads=self.mock_loads, loads_kwargs=kwargs)
        assert JH.deserialize(io.BytesIO(body), 'application/javacript', len(body)) == {
            'stream': body.decode(),
            'kwargs': kwargs,
        }


    def test_passing_false_turns_off_kwargs(self):
        dumps = mock.Mock(wraps=self.mock_dumps)
        loads = mock.Mock(wraps=self.mock_loads)
        JH = media.JSONHandler(
            dumps=dumps,
            dumps_kwargs=False,
            loads=loads,
            loads_kwargs=False,
        )

        JH.serialize([1, 2], 'application/json')
        JH.deserialize(io.BytesIO(b'[1, 2]'), 'application/json', 6)

        dumps.assert_called_once_with([1, 2])
        loads.assert_called_once_with('[1, 2]')

