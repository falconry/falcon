.. _deploy:


Deploying Falcon (Linux + NGINX + uWSGI)
========================================


NGINX is a wonderfully powerful webserver and uWSGI is a highly-configurable
WSGI application server. Together, NIGNX and uWSGI create a one-two punch of
speed and functionality which will suffice for most applications. In addition,
it is possible to scale horizontally to create a highly available environment.
The configuration below does not go that far, but it is possible.

Also, we assume you are deploying to Linux. Sorry Windows folks.


Running your Application as a Different User
''''''''''''''''''''''''''''''''''''''''''''

It is best to execute the application as a different OS user than the one who
owns the source code for your Application. The application user should *NOT*
have write access to your source. This mitigates the chance that someone could
write a malicious Python file to your source directory through an upload
endpoint you might define; when your application restarts, that file is run and
BadThings\ :sup:`(tm)` happen.

.. code:: sh

  $ useradd myproject --create-home
  $ useradd myproject-runner --no-create-home

It is helpful to switch to the project user (myproject) and use the home
directory as the application environment. This gives you an easy location to
install your source code, create files, and a bunch of other nice things which
are outside the scope of this quick start.

If you are working on a remote server, switch to the myproject user and pull
down the source code for your application.

.. code:: sh

  $ git clone git@github.com/myorg/myproject.git /home/myproject/src

Then create a virtual environment which can be used to install your
dependencies.

.. code:: sh

  $ python3 -m venv /home/myproject/venv

Then install your dependencies.

.. code:: sh

  $ /home/myproject/venv/bin/pip install -r /home/myproject/src/requirements.txt
  $ /home/myproject/venv/bin/pip install -e /home/myproject/src
  $ /home/myproject/venv/bin/pip install uwsgi


.. note::

  The exact commands for creating a virtual environment might differet based on
  the Python version you are using and the system you are on. At the end of the day
  we need a virtualenv in /home/myproject/venv with your project dependencies
  installed.


Okay, that is all for getting your application on the server and setting up the
environment.

Preparing your Application for Service
''''''''''''''''''''''''''''''''''''''

You likely have a way to configure your application, maybe with a ``create_api``
function or something like that. This "thing" that configures your application
gives you an instance of :any:`falcon.API`.

We need to expose that in some way so that uWSGI can find it, we will do that by
creating a wsgi.py file. The contents for your file should change bases on how
your application is configured. When all is said and done, have a variable
called ``application`` which is your :any:`falcon.API` instance.

.. code-block:: python
  :caption: /home/myproject/src/wsgi.py

  import os
  import myproject

  config = myproject.get_config(os.environ['MYPROJECT_CONFIG'])
  application = myproject.create_api(config)

This is a bare bones wsgi file. It imports your application and creates the
:any:`falcon.API` instance that represents our application, exposing it as the
variable called ``application``. This file is what we will point uWSGI at to
load your application.

Note that we did not call ``run`` like a developer might do within a Flask
application during development or use `wsgiref.simple_server.make_server` , we
simply assigned our `API` instance to ``application``. We *do not* want to start
a server, uWSGI will do that and starting one here will have unexpected results.


Getting Falcon behind uWSGI
'''''''''''''''''''''''''''

With our wsgi.py file setting up our application it is time to configure uWSGI.
To do this, we create a uwsgi.ini file. In general, you shouldn't commit this
file, it's creation should be of your deployment tool which is targeting the
environment which are deploying.

This configuration, when executed, will create a new uWSGI server which will be
pointed at our wsgi.py file and served on 127.0.0.1:8080.

.. code-block:: ini
  :caption: /home/myproject/src/uwsgi.ini

  [uwsgi]
  master = 1
  vacuum = true
  socket = 127.0.0.1:8080
  enable-threads = true
  thunder-lock = true
  threads = 2
  processes = 2
  virtualenv = /home/myproject/venv
  wsgi-file = /home/myproject/src/wsgi.py
  chdir = /home/myproject/src
  uid = myproject-runner
  gid = myproject-runner


.. note:: Thread vs Processes vs gevent

  There is a lot of questions to ask when deciding how to manage the processes
  that actually run your Python code. Are you generally CPU bound or IO bound?
  Is your application code thread safe? How many CPU's do you have? What system
  are you on? Do you need an in-process cache?

  You will have to do some research to understand this problem and no answers
  can be given to your specific needs. In general uWSGI is so flexible you will
  be able to find a solution that meets your applications needs. This
  configuration enables both threads and processes. Reasearch, experiment, know
  what you are doing, be smart.


There are some important items in here, like ``uid`` and ``gid``. Note that
those values are set to the application runner and not the owner of the
application which should be the owner and group on the `/home/myproject/src` and
`/home/myproject/venv` directory. You should have 755 permissions on the `src`
and `venv` directories and 644 permission on the files within those directories.
This should give you read-access for the `myproject-runner` user.

You can now start uwsgi like this:

.. code:: sh

  $ /home/myproject/venv/bin/uwsgi -c uwsgi.ini

If everything goes well you should see something like this:

::

    *** Operational MODE: preforking+threaded ***
    WSGI app 0 (mountpoint='') ready in 1 seconds on interpreter 0x7fc5a282ba00 pid: 91828 (default app)
    *** uWSGI is running in multiple interpreter mode ***
    spawned uWSGI master process (pid: 91828)
    spawned uWSGI worker 1 (pid: 91866, cores: 2)
    spawned uWSGI worker 2 (pid: 91867, cores: 2)



Making NGINX & uWSGI Talk
'''''''''''''''''''''''''

NGINX is used to proxy API requests to uWSGI which starts and manages your
application. In NGINX parlance, we will create an "upstream" and direct that
upstream (via local IP) to our now running uWSGI application.

The configuration looks like this:

.. code-block:: ini
  :caption: /etc/nginx/sites-avaiable/myproject.conf

  server {
    listen 80;
    server_name myproject.com;

    access_log /var/log/nginx/myproject-access.log;
    error_log  /var/log/nginx/myproject-error.log  warn;

    location / {
      uwsgi_pass 127.0.0.1:8080
      include uwsgi_params;
    }
  }


.. code-block:: sh

  $ sudo service start nginx

NGINX should start and you should now have a working application.


Further Considerations
''''''''''''''''''''''

We did not explain how to setup TLS (HTTPS) for NGINX, that is an exercise for
the reader. Consider using Let's Encrypt which offers free, short-term
certificates which auto-renew the LE docs are the best place to learn how to
integrate that within NGINX.

Also, you might want to setup a database or any number of other services. That
is not covered here since there are so many different services, possible
configurations, network challenges, and security concerns.
