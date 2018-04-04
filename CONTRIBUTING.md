## Contributer's Guide

Thanks for your interest in the project! We welcome pull requests from
developers of all skill levels. To get started, simply fork the master branch
on GitHub to your personal account and then clone the fork into your
development environment.

If you would like to contribute but don't already have something in mind,
we invite you to take a look at the issues listed under our [next milestone][ms].
If you see one you'd like to work on, please leave a quick comment so that we don't
end up with duplicated effort. Thanks in advance!

Kurt Griffiths (**kgriffs** on GH, Gitter, and Twitter) is the original
creator of the Falcon framework, and currently co-maintains the project
along with John Vrbanac (**jmvrbanac** on GH and Gitter, and
**jvrbanac** on Twitter). Falcon is developed by a growing community of
users and contributors just like you.

Please don't hesitate to reach out if you have any questions, or just need a
little help getting started. You can find us in
[falconry/dev][gitter] on Gitter.

Please note that all contributors and maintainers of this project are subject to our [Code of Conduct][coc].

### Pull Requests

Before submitting a pull request, please ensure you have added or updated tests as appropriate, and that all existing tests still pass with your changes on both Python 2 and Python 3. Please also ensure that your coding style follows PEP 8.

You can check all this by running the following from within the Falcon project directory (requires Python 2.7 and Python 3.6 to be installed on your system):

```bash
$ pip install tox
$ tox -e py27,py36,pep8
```

You may also use Python 3.4 or 3.5 if you don't have 3.6 installed on your system. This is just a quick sanity check to verify that your patch works across both Python 2 and Python 3.

If you are using pyenv and get an error along the lines of "failed to get version_info", you will need to activate all the Python versions required by tox before trying again. For example:

```bash
$ pyenv shell 2.7.14 3.6.4
```

### Test coverage

Pull requests must maintain 100% test coverage of all code branches. This helps ensure the quality of the Falcon framework. To check coverage before submitting a pull request:

```bash
$ tools/mintest.sh
```

It is necessary to combine test coverage from multiple environments in order to account for branches in the code that are only taken for a given Python version.

The script generates an HTML coverage report that can be viewed by simply opening `.coverage_html/index.html` in a browser. This can be helpful in tracking down specific lines or branches that are missing coverage.

### Debugging

We use pytest to run all of our tests. Pytest supports pdb and will break as expected on any
`pdb.set_trace()` calls. If you would like to use pdb++ instead of the standard Python
debugger, run one of the following tox environments:

```bash
$ tox -e py2_debug
$ tox -e py3_debug
```

If you wish, you can customize Falcon's `tox.ini` to install alternative debuggers, such as ipdb or pudb.

### Benchmarking

A few simple benchmarks are included with the source under ``falcon/bench``. These can be taken as a rough measure of the performance impact (if any) that your changes have on the framework. You can run these tests by invoking one of the tox environments included for this purpose (see also the ``tox.ini`` file). For example:

```bash
$ tox -e py27_bench
```

Note that you may pass additional arguments via tox to the falcon-bench command:

```bash
$ tox -e py27_bench -- -h
$ tox -e py27_bench -- -b falcon -i 20000
```

Alternatively, you may run falcon-bench directly by creating a new virtual environment and installing falcon directly in development mode. In this example we use pyenv with pyenv-virtualenv from within a falcon source directory:

```bash
$ pyenv virtualenv 3.6.2 falcon-sandbox-36
$ pyenv shell falcon-sandbox-36
$ pip install -r requirements/bench
$ pip install -e .
$ falcon-bench
```

Note that benchmark results for the same code will vary between runs based on a number of factors, including overall system load and CPU scheduling. These factors may be somewhat mitigated by running the benchmarks on a Linux server dedicated to this purpose, and pinning the benchmark process to a specific CPU core.

### Documentation

To check documentation changes (including docstrings), before submitting a PR, ensure the tox job builds the documentation correctly:

```bash
$ tox -e docs

# OS X
$ open docs/_build/html/index.html

# Gnome
$ gnome-open docs/_build/html/index.html

# Generic X Windows
$ xdg-open docs/_build/html/index.html
```

### Code style rules

* Docstrings are required for classes, attributes, methods, and functions.
* Docstrings should utilize the [napolean style][docstrings] in order to make them read well, regardless of whether they are viewed through `help()` or on [Read the Docs][rtd].
* Please try to be consistent with the way existing docstrings are formatted. In particular, note the use of single vs. double backticks as follows:
    * Double backticks
        * Inline code
        * Variables
        * Types
        * Decorators
    * Single backticks
        * Methods
        * Params
        * Attributes
* Format non-trivial comments using your GitHub nick and one of these prefixes:
    * TODO(riker): Damage report!
    * NOTE(riker): Well, that's certainly good to know.
    * PERF(riker): Travel time to the nearest starbase?
    * APPSEC(riker): In all trust, there is the possibility for betrayal.
* When catching exceptions, name the variable `ex`.
* Use whitespace to separate logical blocks of code and to improve readability.
* No single-character variable names except for trivial indexes when looping,
or in mathematical expressions implementing well-known formulas.
* Heavily document code that is especially complex and/or clever.
* When in doubt, optimize for readability.

### Commit Message Format

Falcon's commit message format uses [AngularJS's style guide][ajs], reproduced here for convenience, with some minor edits for clarity.

Each commit message consists of a **header**, a **body** and a **footer**. The header has a special format that includes a **type**, a **scope** and a **subject**:

```
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

No line may exceed 100 characters. This makes it easier to read the message on GitHub as well as in various git tools.

#####  Type
Must be one of the following:

* **feat**: A new feature
* **fix**: A bug fix
* **docs**: Documentation only changes
* **style**: Changes that do not affect the meaning of the code (white-space, formatting, missing semi-colons, etc)
* **refactor**: A code change that neither fixes a bug or adds a feature
* **perf**: A code change that improves performance
* **test**: Adding missing tests
* **chore**: Changes to the build process or auxiliary tools and libraries such as documentation generation

##### Scope
The scope could be anything specifying place of the commit change. For example: `$location`, `$browser`, `$compile`, `$rootScope`, `ngHref`, `ngClick`, `ngView`, etc...

##### Subject
The subject contains succinct description of the change:

* use the imperative, present tense: "change" not "changed" nor "changes"
* don't capitalize first letter
* no dot (.) at the end

##### Body
Just as in the **subject**, use the imperative, present tense: "change" not "changed" nor "changes"The body should include the motivation for the change and contrast this with previous behavior.

##### Footer
The footer should contain any information about **Breaking Changes** and is also the place to reference GitHub issues that this commit **Closes**.

[ajs]: https://github.com/angular/angular.js/blob/master/CONTRIBUTING.md#commit
[docstrings]: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html#example-google-style-python-docstrings
[goog-style]: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html#Comments
[rtd]: https://falcon.readthedocs.io
[coc]: https://github.com/falconry/falcon/blob/master/CODEOFCONDUCT.md
[freenode]: https://www.freenode.net/
[gitter]: https://gitter.im/falconry/dev
[ml-join]: mailto:users-join@mail.falconframework.org?subject=join
[ml-archive]: https://mail.falconframework.org/archives/list/users@mail.falconframework.org/
[ms]: https://github.com/falconry/falcon/milestones
