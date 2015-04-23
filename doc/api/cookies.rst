.. _cookies:

Cookies
-------

Cookie support is available in Falcon version 0.3 or later.

.. _getting-cookies:

Getting Cookies
~~~~~~~~~~~~~~~

Cookies can be read from a request via the :py:attr:`~.Request.cookies`
request attribute:

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):

            cookies = req.cookies

            if "my_cookie" in cookies:
                my_cookie_value = cookies["my_cookie"]
            # ....

The :py:attr:`~.Request.cookies` attribute is a regular
:py:class:`dict` object.

.. tip :: :py:attr:`~.Request.cookies` returns a
    copy of the response cookie dict. Assign it to a variable as in the above example
    for better performance.

.. _setting-cookies:

Setting Cookies
~~~~~~~~~~~~~~~

Setting cookies on a response is done via the :py:meth:`~.Response.set_cookie`.

You should use :py:meth:`~.Response.set_cookie` instead of
:py:meth:`~.Response.set_header` or :py:meth:`~.Response.append_header`.

With :py:meth:`~.Response.set_header` you cannot set multiple headers
with the same name (which is how multiple cookies are sent to the client).

:py:meth:`~.Response.append_header` appends multiple values to the same
header field, which is not compatible with the format used by `Set-Cookie`
headers to send cookies to clients.

Simple example:

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):
            # Set the cookie "my_cookie" to the value "my cookie value"
            resp.set_cookie("my_cookie", "my cookie value")


You can of course also set the domain, path and lifetime of the cookie.

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):
            # Set the 'max-age' of the cookie to 10 minutes (600 seconds)
            # and the cookies domain to "example.com"
            resp.set_cookie("my_cookie", "my cookie value",
                            max_age=600, domain="example.com")


If you set a cookie and want to get rid of it again, you can
use the :py:meth:`~.Response.unset_cookie`:

.. code:: python

    class Resource(object):
        def on_get(self, req, resp):
            resp.set_cookie("bad_cookie", ":(")
            # clear the bad cookie
            resp.unset_cookie("bad_cookie")
