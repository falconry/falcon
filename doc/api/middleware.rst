.. _middleware:

Middleware Components
=====================

Middleware components provide a way to execute logic before the
framework routes each request, after each request is routed but before
the target responder is called, or just before the response is returned
for each request. Components are registered with the `middleware` kwarg
when instantiating Falcon's :ref:`API class <api>`.

.. Note::
    Unlike hooks, middleware methods apply globally to the entire API.

Falcon's middleware interface is defined as follows:

.. code:: python

    class ExampleComponent(object):
        def process_request(self, req, resp):
            """Process the request before routing it.

            Args:
                req: Request object that will eventually be
                    routed to an on_* responder method.
                resp: Response object that will be routed to
                    the on_* responder.
            """

        def process_resource(self, req, resp, resource):
            """Process the request after routing.

            Args:
                req: Request object that will be passed to the
                    routed responder.
                resp: Response object that will be passed to the
                    responder.
                resource: Resource object to which the request was
                    routed. May be None if no route was found for
                    the request.
            """

        def process_response(self, req, resp, resource):
            """Post-processing of the response (after routing).

            Args:
                req: Request object.
                resp: Response object.
                resource: Resource object to which the request was
                    routed. May be None if no route was found
                    for the request.
            """

.. Tip::
    Because *process_request* executes before routing has occurred, if a
    component modifies ``req.path`` in its *process_request* method,
    the framework will use the modified value to route the request.

Each component's *process_request*, *process_resource*, and
*process_response* methods are executed hierarchically, as a stack, following
the ordering of the list passed via the `middleware` kwarg of
:ref:`falcon.API<api>`. For example, if a list of middleware objects are
passed as ``[mob1, mob2, mob3]``, the order of execution is as follows::

    mob1.process_request
        mob2.process_request
            mob3.process_request
                mob1.process_resource
                    mob2.process_resource
                        mob3.process_resource
                <route to responder method>
            mob3.process_response
        mob2.process_response
    mob1.process_response

Note that each component need not implement all `process_*`
methods; in the case that one of the three methods is missing,
it is treated as a noop in the stack. For example, if ``mob2`` did
not implement *process_request* and ``mob3`` did not implement
*process_response*, the execution order would look
like this::

    mob1.process_request
        _
            mob3.process_request
                mob1.process_resource
                    mob2.process_resource
                        mob3.process_resource
                <route to responder method>
            _
        mob2.process_response
    mob1.process_response

If one of the *process_request* middleware methods raises an
error, it will be processed according to the error type. If
the type matches a registered error handler, that handler will
be invoked and then the framework will begin to unwind the
stack, skipping any lower layers. The error handler may itself
raise an instance of HTTPError, in which case the framework
will use the latter exception to update the *resp* object.
Regardless, the framework will continue unwinding the middleware
stack. For example, if *mob2.process_request* were to raise an
error, the framework would execute the stack as follows::

    mob1.process_request
        mob2.process_request
            <skip mob1/mob2 process_resource, mob3, and routing>
        mob2.process_response
    mob1.process_response

Finally, if one of the *process_response* methods raises an error,
or the routed on_* responder method itself raises an error, the
exception will be handled in a similar manner as above. Then,
the framework will execute any remaining middleware on the
stack.
