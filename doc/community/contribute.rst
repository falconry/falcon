.. _contribute:

Contribute to Falcon
====================

`Kurt Griffiths <http://kgriffs.com>`_ is the creator and current
maintainer of the Falcon framework. He works with a growing team of
friendly and stylish volunteers like yourself, who review patches,
implement features, fix bugs, and write docs for the project.

Your ideas and patches are always welcome!

IRC
---
If you are interested in helping out, please join the **#falconframework**
IRC channel on `Freenode <https://www.freenode.net/>`_.
It's the best way to discuss ideas, ask questions, and generally stay
in touch with fellow contributors. We recommend setting up a good
IRC bouncer, such as ZNC, which can record and play back any conversations
that happen when you are away.

.. include:: contrib-snip.rst

Pull Requests
-------------
Before submitting a pull request, please ensure you have added new
tests and updated existing ones as appropriate. We require 100%
code coverage. Also, please ensure your coding style follows PEP 8 and
doesn't make pyflakes sad.

**Additional Style Rules**

* Docstrings are required for classes, attributes, methods, and functions.
* Use `napolean-flavored`_ dosctrings to make them readable both when
  using the *help* function within a REPL, and when browsing
  them on *Read the Docs*.
* Format non-trivial comments using your GitHub nick and an appropriate
  prefix. Here are some examples:
    .. code:: python

        # TODO(riker): Damage report!
        # NOTE(riker): Well, that's certainly good to know.
        # PERF(riker): Travel time to the nearest starbase?
        # APPSEC(riker): In all trust, there is the possibility for betrayal.

* Commit messages should be formatted using `AngularJS conventions`_
  (one-liners are OK for now but bodies and footers may be required as the
  project matures).
* When catching exceptions, name the variable ``ex``.
* Use whitespace to separate logical blocks of code and to improve readability.
* Do not use single-character variable names except for trivial indexes when
  looping, or in mathematical expressions implementing well-known formulae.
* Heavily document code that is especially complex or clever!
* When in doubt, optimize for readability.

.. _napolean-flavored: http://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html#example-google-style-python-docstrings
.. _AngularJS conventions: http://goo.gl/QpbS7
