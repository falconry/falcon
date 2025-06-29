# Copyright 2025 by Vytautas Liuolia.
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

"""Hacks and workarounds for Sphinx bugs."""

import sphinx.util.inspect


def patch_type_alias_forward_ref(cls: type) -> None:
    def __hash__(obj) -> int:
        return hash(obj.name)

    # NOTE(vytas): Based on various issue comments in the Sphinx repo.
    def __repr__(obj) -> str:
        return obj.name

    cls.__hash__ = __hash__
    cls.__repr__ = __repr__


def setup(app):
    patch_type_alias_forward_ref(sphinx.util.inspect.TypeAliasForwardRef)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
