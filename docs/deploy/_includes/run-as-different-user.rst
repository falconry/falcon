Running your Application as a Different User
''''''''''''''''''''''''''''''''''''''''''''

It is best to execute the application as a different OS user than the one who
owns the source code for your application. The application user should *NOT*
have write access to your source. This mitigates the chance that someone could
write a malicious Python file to your source directory through an upload
endpoint you might define; when your application restarts, the malicious file is
loaded and proceeds to cause any number of Bad Things™ to happen.

.. literalinclude:: snippets/useradd.sh
  :language: sh

It is helpful to switch to the project user (myproject) and use the home
directory as the application environment.

If you are working on a remote server, switch to the myproject user and pull
down the source code for your application.

.. literalinclude:: snippets/git-clone.sh
  :language: sh


.. note::

  You could use a tarball, zip file, scp or any other means to get your source
  onto a server.

Next, create a virtual environment which can be used to install your
dependencies.

.. literalinclude:: snippets/create-venv.sh
  :language: sh
