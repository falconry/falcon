### Contributing ###

Kurt Griffiths (kgriffs) is the creator and current maintainer of the Falcon framework. Pull requests are always welcome.

Before submitting a pull request, please ensure you have added/updated the appropriate tests (and that all existing tests still pass with your changes), and that your coding style follows PEP 8 and doesn't cause pyflakes to complain.

#### Additional style rules ####

* Docstrings are required for classes, attributes, methods, and functions.
* Docstrings are [napolean-flavored][docstrings] so they look good from both
the CLI and in RTD.
* Format non-trivial comments using your GitHub nick and one of these prefixes:
    * TODO(riker): Damage report!
    * NOTE(riker): Well, that's certainly good to know.
    * PERF(riker): Travel time to the nearest starbase?
    * APPSEC(riker): In all trust, there is the possibility for betrayal.
* Commit messages should be formatted using [AngularJS conventions][ajs] (one-liners are OK for now but body and footer may be required as the project matures).
* When catching exceptions, name the variable `ex`.
* Use whitespace to separate logical blocks of code and to improve readability.
* No single-character variable names except for trivial indexes when looping,
or in mathematical expressions implementing well-known formulas.
* Heavily document code that is especially complex and/or clever.
* When in doubt, optimize for readability.

[ajs]: http://goo.gl/QpbS7
[docstrings]: http://sphinxcontrib-napoleon.readthedocs.org/en/latest/example_google.html#example-google-style-python-docstrings
[goog-style]: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html#Comments
