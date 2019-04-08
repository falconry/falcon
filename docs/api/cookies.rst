.. _cookies:

Cookies
-------

.. _getting-cookies:

Getting Cookies
~~~~~~~~~~~~~~~

Cookies can be read from a request either via the
:py:meth:`~.Request.get_cookie_values` method or the :py:attr:`~.Request.cookies`
attribute on the :py:class:`~.Request` object. Generally speaking, the
:py:meth:`~.Request.get_cookie_values` method should be used unless you need a
collection of all the cookies in the request.

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):

            cookies = req.cookies

            my_cookie_values = req.get_cookie_values('my_cookie')
            if my_cookie_values:
                # NOTE: If there are multiple values set for the cookie, you
                # will need to choose how to handle the additional values.
                v = my_cookie_values[0]

                # ...

.. _setting-cookies:

Setting Cookies
~~~~~~~~~~~~~~~

Setting cookies on a response may be done either via
:py:meth:`~.Response.set_cookie` or :py:meth:`~.Response.append_header`.

One of these methods should be used instead of
:py:meth:`~.Response.set_header`. With :py:meth:`~.Response.set_header` you
cannot set multiple headers with the same name (which is how multiple cookies
are sent to the client).

Simple example:

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):

            # Set the cookie 'my_cookie' to the value 'my cookie value'
            resp.set_cookie('my_cookie', 'my cookie value')


You can of course also set the domain, path and lifetime of the cookie.

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):
            # Set the maximum age of the cookie to 10 minutes (600 seconds)
            # and the cookie's domain to 'example.com'
            resp.set_cookie('my_cookie', 'my cookie value',
                            max_age=600, domain='example.com')


You can also instruct the client to remove a cookie with the
:py:meth:`~.Response.unset_cookie` method:

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):
            resp.set_cookie('bad_cookie', ':(')

            # Clear the bad cookie
            resp.unset_cookie('bad_cookie')

.. _cookie-secure-attribute:

The Secure Attribute
~~~~~~~~~~~~~~~~~~~~

By default, Falcon sets the `secure` attribute for cookies. This
instructs the client to never transmit the cookie in the clear over
HTTP, in order to protect any sensitive data that cookie might
contain. If a cookie is set, and a subsequent request is made over
HTTP (rather than HTTPS), the client will not include that cookie in
the request.

.. warning::

    For this attribute to be effective, your web server or load
    balancer will need to enforce HTTPS when setting the cookie, as
    well as in all subsequent requests that require the cookie to be
    sent back from the client.

When running your application in a development environment, you can
disable this default behavior by setting
:py:attr:`~.ResponseOptions.secure_cookies_by_default` to ``False``
via :any:`API.resp_options`. This lets you test your app locally
without having to set up TLS. You can make this option configurable to
easily switch between development and production environments.

See also: `RFC 6265, Section 4.1.2.5`_

.. _RFC 6265, Section 4.1.2.5:
    https://tools.ietf.org/html/rfc6265#section-4.1.2.5
