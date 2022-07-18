.. _organizing-your-project:

Organizing Your Project
==============================
A Falcon Project directory can look like this::

     appname
         ├── .venv
         ├── appname
         │   ├── __init__.py
         │   ├── app.py
         │   ├── config.py
         │   ├── middleware.py
         │   └──package_1
         │         ├── __init__.py
         │         ├── resource.py
         │         ├── hook.py
         │         └──otherfiles.py
         └── tests
              ├──test_app.py
              └──test_package_1
                   └──test_package_1.py


Let's take a closer look on what does each file represent:

- **app.py**: Main entry point of your application, usually this is where you define your routing, and also where you start your app, check out the :ref:`falcon.app <app>` for more.
- **config.py**: Configurations for your project, Falcon is unopinionated concerning how you configure your own application(see also a related question in our FAQ: :ref:`configuration-approaches`).
- **middleware.py**: Middleware for your project, middleware is a way to execute logic before the framework routes the request, check out :ref:`middleware <middleware>` for more.
- **package_1/resource.py**: What do we mean by resource here is whatever your project provides through URLs(e.g., Library application resources can be book or renter), checkout our :ref:`quickstart <quickstart>` to get a feel on how resources work!
- **package_1/hook.py**: Hooks runs logic before and or after an individual responder(CRUD methods of a resource) or an entire resource, checkout :ref:`hooks <hooks>` for more.

It's recommended to checkout our :ref:`tutorial <tutorial>` to get a better feel on how Falcon works as a whole.


**Further reading**

- `Structuring your project <https://docs.python-guide.org/writing/structure/>`__.
- `Falcon Projects templates and samples <https://github.com/falconry/falcon/wiki/Project-Templates-and-Samples>`__.    