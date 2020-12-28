# Copyright 2020 by Vytautas Liuolia.
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

from falcon.errors import UnsupportedError, UnsupportedScopeError
from falcon.util.misc import _lru_cache_safe


@_lru_cache_safe(maxsize=16)
def _validate_asgi_scope(asgi_version, scope_type, spec_version, http_version):
    if not asgi_version.startswith('3.'):
        raise UnsupportedScopeError(
            f'Falcon requires ASGI version 3.x. Detected: {asgi_version}'
        )

    if scope_type == 'http':
        spec_version = spec_version or '2.0'
        if not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                f'The ASGI "http" scope version {spec_version} is not supported.'
            )
        if http_version not in {'1.0', '1.1', '2', '3'}:
            raise UnsupportedError(
                f'The ASGI "http" scope does not support HTTP version {http_version}.'
            )
        return spec_version

    if scope_type == 'websocket':
        spec_version = spec_version or '2.0'
        if not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                'Only versions 2.x of the ASGI "websocket" scope are supported.'
            )
        if http_version not in {'1.1', '2', '3'}:
            raise UnsupportedError(
                f'The ASGI "websocket" scope does not support HTTP version {http_version}.'
            )
        return spec_version

    if scope_type == 'lifespan':
        spec_version = spec_version or '1.0'
        if not spec_version.startswith('1.') and not spec_version.startswith('2.'):
            raise UnsupportedScopeError(
                'Only versions 1.x and 2.x of the ASGI "lifespan" scope are supported.'
            )
        return spec_version

    # NOTE(kgriffs): According to the ASGI spec: "Applications should
    #   actively reject any protocol that they do not understand with
    #   an Exception (of any type)."
    raise UnsupportedScopeError(
        f'The ASGI "{scope_type}" scope type is not supported.'
    )
