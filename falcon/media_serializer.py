from typing import MutableMapping
from typing import Union

from falcon.link import Link


class Serializer:
    def serialize(
        self, media: MutableMapping[str, Union[str, int, None, Link]], content_type: str
    ) -> bytes:
        raise NotImplementedError()
