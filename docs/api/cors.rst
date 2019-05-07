.. _cors:

Cors
=====

Falcon allows an easy way to enable or disable your CORS policies. By
default CORS policies are enable in the :any:`falcon.API` object so all request
coming from other systems with different domains will be blocked. You can
change this easy just by instantiating a :any:`falcon.API` passing the parameter
`cors_enable` as `True`.

Usage
-----

.. code:: python

    import falcon

    # falcon.API instances are callable WSGI apps
    app = falcon.API(cors_enable=True)

