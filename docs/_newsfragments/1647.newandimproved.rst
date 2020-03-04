When no route matches a request, the framework will now raise a
specialized subclass of :class:`~.falcon.HTTPNotFound`
(:class:`~.falcon.HTTPRouteNotFound`) so that
a custom error handler can distinguish that specific case if desired.
