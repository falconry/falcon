# Copyright 2021-2023 by Vytautas Liuolia.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shorthand definitions for more complex types."""
import http
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import MutableMapping
from typing import Optional
from typing import Pattern
from typing import Tuple
from typing import Union


Link = Dict[str, str]


class Serializer:
    def serialize(
        self, media: MutableMapping[str, Union[str, int, None, Link]], content_type: str
    ) -> bytes:
        raise NotImplementedError()


class MediaHandlers:
    def _resolve(
        self, media_type: str, default: str, raise_not_found: bool = False
    ) -> Tuple[Serializer, Optional[Callable], Optional[Callable]]:
        raise NotImplementedError()


from falcon.request import Request  # noqa: E402
from falcon.response import Response  # noqa: E402


# Error handlers
ErrorHandler = Callable[[Request, Response, BaseException, dict], Any]

# Error serializers
ErrorSerializer = Callable[[Request, Response, BaseException], Any]

# Sinks
SinkPrefix = Union[str, Pattern]

# TODO(vytas): Is it possible to specify a Callable or a Protocol that defines
#   type hints for the two first parameters, but accepts any number of keyword
#   arguments afterwords?
# class SinkCallable(Protocol):
#     def __call__(sef, req: Request, resp: Response, <how to do?>): ...
NormalizedHeaders = Dict[str, str]
RawHeaders = Union[NormalizedHeaders, List[Tuple[str, str]]]
Status = Union[http.HTTPStatus, str, int]
