import pytest

from falcon.media_serializer import Serializer


class TestSerializer:
    def test_interface_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            Serializer().serialize({'data': 'any'}, 'any')
