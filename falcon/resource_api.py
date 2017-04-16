# Copyright 2013 IBM Corp
#
# Author: Tong Li <litong01@us.ibm.com>
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import falcon
from falcon import api_helpers
from falcon import hooks


RESOURCE_METHOD_FLAG = 'fab05a04-b861-4651-bd0c-9cb3eb9a6088'


class Restify(object):
    def __init__(self, path='', method='GET'):
        if not path:
            raise Exception('Path has to be specified.')

        if method.upper() not in falcon.HTTP_METHODS:
            raise Exception('Invalid request method.')
        self.path = path
        self.method = method.upper()

    def __call__(self, func):
        setattr(func, RESOURCE_METHOD_FLAG, self)
        return func


class ResourceAPI(falcon.API):

    def add_route(self, resource):
        """Associates uri patterns with resource methods.

        A resource is an instance of a class that defines various methods
        to handle http requests.

        Use this class to create applications which serve a standard
        compliant ReSTful API. For example, you may have an API which manage
        monitoring data, there can be multiple implementations of the API
        using different technologies. One can use Mongodb, the other can use
        Cassandra. To make the configuration of the application very easy,
        each implementation provides a class with set of methods decorated
        by class Restify, the application can simply using single entry
        configuration to load different implementations.

        For example::

            class ExampleResource(object):
                @Restify(path='/path1/', method='post')
                def func1(self, req, res):
                    pass

                @Restify(path='/path2/{id}/key/', method='get')
                def func2(self, req, res, id):
                    pass

                def func3(self, req, res, id):
                    pass

        With the above class, the following code will add the class method
        func1, func2 to handle post and get requests respectively, method
        func3 won't be added to the routes.::

            app.add_route(ExampleResource())

        Args:
            resource (instance): Object which represents an HTTP/REST
                "resource". Falcon will pass requests to various decorated
                methods to handle http requests.
        """
        if not resource:
            raise Exception('Not a valid resource')

        path_maps = {}
        for attr in dir(resource):
            method = getattr(resource, attr)
            if callable(method) and hasattr(method, RESOURCE_METHOD_FLAG):
                flag = getattr(method, RESOURCE_METHOD_FLAG)
                map = path_maps.get(flag.path)
                if not map:
                    uri_fields, template = (
                        api_helpers.compile_uri_template(flag.path))
                    map = (template, {})
                    path_maps[flag.path] = map

                new_method = hooks._wrap_with_hooks(
                    self._before, self._after, method, resource)
                map[1][flag.method] = new_method

        for item in path_maps:
            self._routes.insert(0, (path_maps[item][0],
                                    path_maps[item][1],
                                    resource))
