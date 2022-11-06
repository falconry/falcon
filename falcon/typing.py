# Copyright 2021-2022 by Vytautas Liuolia.
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

from typing import Any, Callable, Pattern, TypeVar, Union

from falcon.request import Request
from falcon.response import Response

# Common definitions
ExceptionClass = TypeVar('ExceptionClass', bound=BaseException)

RequestClass = TypeVar('RequestClass', bound=Request)
ResponseClass = TypeVar('ResponseClass', bound=Response)


# Error handlers
ErrorHandler = Callable[[RequestClass, ResponseClass, ExceptionClass, dict], Any]


# Error serializers
ErrorSerializer = Callable[[RequestClass, ResponseClass, ExceptionClass], Any]


# Sinks
# TODO(vytas): Is it possible to specify a Callable or a Protocol that defines
#   type hints for the two first parameters, but accepts any number of keyword
#   arguments afterwords?
# class SinkCallable(Protocol):
#     def __call__(sef, req: Request, resp: Response, <how to do?>): ...
SinkPrefix = Union[str, Pattern]
