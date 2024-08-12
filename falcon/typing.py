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

from __future__ import annotations

import http
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Pattern,
    Tuple,
    TYPE_CHECKING,
    Union,
)

if TYPE_CHECKING:
    from falcon.request import Request
    from falcon.response import Response


Link = Dict[str, str]

# Error handlers
ErrorHandler = Callable[['Request', 'Response', BaseException, dict], Any]

# Error serializers
ErrorSerializer = Callable[['Request', 'Response', BaseException], Any]

JSONSerializable = Union[
    Dict[str, 'JSONSerializable'],
    List['JSONSerializable'],
    Tuple['JSONSerializable', ...],
    bool,
    float,
    int,
    str,
    None,
]

# Sinks
SinkPrefix = Union[str, Pattern]

# TODO(vytas): Is it possible to specify a Callable or a Protocol that defines
#   type hints for the two first parameters, but accepts any number of keyword
#   arguments afterwords?
# class SinkCallable(Protocol):
#     def __call__(sef, req: Request, resp: Response, <how to do?>): ...
Headers = Dict[str, str]
HeaderList = Union[Headers, List[Tuple[str, str]]]
ResponseStatus = Union[http.HTTPStatus, str, int]
