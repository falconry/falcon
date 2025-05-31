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


Stable Release Status
---------------------

As Falcon is a relatively small project with limited resources and funding, ...
(**Current Release**).

We also provide limited security support for the latest release of the old
stable SemVer major series until it either falls back two major releases
behind, or two years pass from the first release of the current stable series,
whichever comes first (**Security Maintenance**).

Other versions are considered End of Life (**EOL**).

The table below summarizes the history of Falcon stable (1.0+) releases
alongside their maintenance status. (You can find even older release history in
our repository's commit tree, or PyPI.)

.. falcon-releases:: changes/

TODO: write...


Pre-releases and Development Versions
-------------------------------------

TODO: write...

That being said, we do try to keep the main development branch in good shape at
all times; our Continuous Integration gates ensure that both ``master``
commits, and pull requests being merged, pass all tests on all supported
platforms.
