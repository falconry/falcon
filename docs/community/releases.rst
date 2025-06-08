Releases and Versioning
=======================

Falcon is developed in the open (yes, You can :doc:`contribute <contributing>`
too!) primarily using the
`falconry/falcon <https://github.com/falconry/falcon>`__ GitHub repository.
Newer releases are available from our GitHub
`release page <https://github.com/falconry/falcon/releases>`__.
Unless noted otherwise in specific files, Falcon releases are covered by the
:ref:`Apache 2.0 License <falcon_license>`.


.. _semver:

Semantic Versioning
-------------------

Falcon strictly adheres to `SemVer <https://semver.org/>`__ -- incompatible API
changes are only introduced in conjunction with a major version increment.
Furthermore, when we make breaking changes in a new major version of the
framework, the old behavior or feature removal is deprecated in advance at
least one minor release leading to the change. In addition to documenting
deprecations, we do our best to emit deprecation :mod:`warnings`
(where feasible).

While there seems to be
`no clear consensus <https://github.com/semver/semver/issues/716>`__ on whether
removing platform support constitutes a SemVer breaking change, Falcon assumes
that it does (unless we have communicated otherwise in advance, e.g., the
:doc:`Falcon 4.x series </changes/4.0.0>` only guarantees Python 3.10+
support).

.. _supported_releases:

Supported Releases
------------------

.. _stable_release_current:

.. rubric:: Current Release

As Falcon is a relatively small project with limited resources and funding, we
only actively support the current SemVer major/minor release.

Although older minor releases from the current Falcon series are formally
considered :ref:`stable_release_eol`, the upgrade path to the current release
ought to be effortless thanks to Falcon's strict :ref:`SemVer <semver>`
guarantees.

.. _stable_release_security:

.. rubric:: Security Maintenance

We also provide limited security maintenance for the latest release of the old
stable SemVer major series until *(1)* it falls back two major releases
behind, or *(2)* 730 days (two years bar the possibility of a leap year) pass
from the first release of the current stable series
(whichever comes first).

"Security maintenance" of an old stable release here means providing new patch
versions in response to security vulnerabilities. Other bugs (regardless of
their impact) and compatibility with new Python versions are only addressed in
the :ref:`stable_release_current`. Reported security vulnerabilities are
evaluated on a case by case basis, with the Common Vulnerability Scoring System
(CVSS) score reaching at least "Medium" (4.0+) as a starting point.

.. _stable_release_eol:

.. rubric:: EOL

Other Falcon versions are considered End of Life (**EOL**).

If you are stuck on an old Falcon version, you are still welcome to
:ref:`ask for help <help>`! However, while we may be able to advise how to work
around a specific issue, we will not ship new patch versions to
EOL Falcon releases.


Stable Release Status
---------------------

The below table summarizes the history of Falcon stable (1.0+) releases
alongside their maintenance status:

.. falcon-releases:: changes/

(You can find even older (0.x) release history in our repository's commit tree,
or PyPI.)


Pre-releases and Development Versions
-------------------------------------

The upcoming Falcon version release normally lives in our main development
branch (``master``). If you absolutely need a new unreleased feature or fix,
You can :ref:`install <install>` it directly from GitHub, however, we strongly
recommend to deploy only stable Falcon releases to production.
That being said, we do try to keep the main development branch in good shape at
all times; our Continuous Integration gates ensure that both ``master``
commits, and pull requests being merged, pass all tests on the supported
platforms.

Prior to a new stable release, we normally cut several alphas, betas, and
release candidates. Falcon has no fixed pre-release schedule (unlike, e.g.,
CPython), and the exact number of pre-releases depends on many factors, such as
the scope of the impending stable release, the extent of issues found in beta
testing, and ultimately, it is decided at the discretion of the release manager
and the core maintainer team.
