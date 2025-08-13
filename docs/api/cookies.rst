.. _cookies:

Cookies
-------

This page describes the API provided by Falcon to manipulate cookies.

.. _getting-cookies:

Getting Cookies
~~~~~~~~~~~~~~~

Cookies can be read from a request either via the
:meth:`~.falcon.Request.get_cookie_values` method or the
:attr:`~.falcon.Request.cookies` attribute on the
:class:`~.falcon.Request` object. Generally speaking, the
:meth:`~.falcon.Request.get_cookie_values` method should be used unless you
need a collection of all the cookies in the request.

.. note::

    :class:`falcon.asgi.Request` implements the same cookie methods and
    properties as :class:`falcon.Request`.

Here's an example showing how to get cookies from a request:

.. tab-set::

    .. tab-item:: WSGI

        .. code:: python

            class Resource:
                def on_get(self, req, resp):

                    # Get a dict of name/value cookie pairs.
                    cookies = req.cookies

                    my_cookie_values = req.get_cookie_values('my_cookie')

                    if my_cookie_values:
                        # NOTE: If there are multiple values set for the cookie, you
                        #   will need to choose how to handle the additional values.
                        v = my_cookie_values[0]

    .. tab-item:: ASGI

        .. code:: python

            class Resource:
                async def on_get(self, req, resp):

                    # Get a dict of name/value cookie pairs.
                    cookies = req.cookies

                    # NOTE: Since get_cookie_values() is synchronous, it does
                    #   not need to be await'd.
                    my_cookie_values = req.get_cookie_values('my_cookie')

                    if my_cookie_values:
                        # NOTE: If there are multiple values set for the cookie, you
                        #   will need to choose how to handle the additional values.
                        v = my_cookie_values[0]

.. _setting-cookies:

Setting Cookies
~~~~~~~~~~~~~~~

Setting cookies on a response may be done either via
:meth:`~falcon.Response.set_cookie` or :meth:`~falcon.Response.append_header`.

One of these methods should be used instead of
:meth:`~falcon.Response.set_header`. With :meth:`~falcon.Response.set_header` you
cannot set multiple headers with the same name (which is how multiple cookies
are sent to the client).

.. note::

    :class:`falcon.asgi.Request` implements the same cookie methods and
    properties as :class:`falcon.Request`. The ASGI versions of
    :meth:`~falcon.asgi.Response.set_cookie` and
    :meth:`~falcon.asgi.Response.append_header`
    are synchronous, so they do not need to be ``await``'d.

Simple example:

.. code:: python

    # Set the cookie 'my_cookie' to the value 'my cookie value'
    resp.set_cookie('my_cookie', 'my cookie value')


You can of course also set the domain, path and lifetime of the cookie.

.. code:: python

    # Set the maximum age of the cookie to 10 minutes (600 seconds)
    #   and the cookie's domain to 'example.com'
    resp.set_cookie('my_cookie', 'my cookie value',
                    max_age=600, domain='example.com')


You can also instruct the client to remove a cookie with the
:meth:`~falcon.Response.unset_cookie` method:

.. code:: python

    # Set a cookie in middleware or in a previous request.
    resp.set_cookie('my_cookie', 'my cookie value')

    # -- snip --

    # Clear the cookie for the current request and instruct the user agent
    #   to expire its own copy of the cookie (if any).
    resp.unset_cookie('my_cookie')

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
:attr:`~falcon.ResponseOptions.secure_cookies_by_default` to ``False``
via :attr:`falcon.App.resp_options` or
:attr:`falcon.asgi.App.resp_options`. This lets you test your app
locally without having to set up TLS. You can make this option configurable to
easily switch between development and production environments.

See also: `RFC 6265, Section 4.1.2.5`_

The SameSite Attribute
~~~~~~~~~~~~~~~~~~~~~~

The `SameSite` attribute may be set on a cookie using the
:meth:`~falcon.Response.set_cookie` method. It is generally a good idea to
at least set this attribute to ``'Lax'`` in order to mitigate
`CSRF attacks <https://www.owasp.org/index.php/Cross-Site_Request_Forgery_(CSRF)>`_.

Currently, :meth:`~falcon.Response.set_cookie` does not set `SameSite` by
default, although this may change in a future release.

.. _RFC 6265, Section 4.1.2.5:
    https://tools.ietf.org/html/rfc6265#section-4.1.2.5

When unsetting a cookie, :meth:`~falcon.Response.unset_cookie`,
the default `SameSite` setting of the unset cookie is ``'Lax'``, but can be changed
by setting the 'same_site' kwarg.

The Partitioned Attribute
~~~~~~~~~~~~~~~~~~~~~~~~~

Starting from Q1 2024, Google Chrome started to
`phase out support for third-party cookies
<https://developers.google.com/privacy-sandbox/3pcd/prepare/prepare-for-phaseout>`__.
If your site is relying on cross-site cookies, it might be necessary to set the
``Partitioned`` attribute. ``Partitioned`` usually requires the
:ref:`Secure <cookie-secure-attribute>` attribute to be set. While this is not
enforced by Falcon, the framework does set ``Secure`` by default, unless
specified otherwise
(see also :attr:`~falcon.ResponseOptions.secure_cookies_by_default`).

Currently, :meth:`~falcon.Response.set_cookie` does not set ``Partitioned``
automatically depending on other attributes (like ``SameSite``),
although this may change in a future release.

.. note::
    The standard :mod:`http.cookies` module does not support the `Partitioned`
    attribute in versions prior to Python 3.14. Therefore, Falcon performs a
    simple monkey-patch on the standard library module to backport this
    feature for apps running on older Python versions.
