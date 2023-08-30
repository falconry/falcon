import pytest

from falcon.typing import MediaHandlers
from falcon.typing import Serializer


class TestSerializer:
    def test_interface_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            Serializer().serialize({'data': 'any'}, 'any')


class TestMediaHandlers:
    def test_interface_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError):
            MediaHandlers()._resolve('any', 'any', False)
