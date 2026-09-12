.. _outputting_csv_recipe:

Outputting CSV Files
====================

Generating a CSV (or PDF, etc.) report and making it available as a downloadable
file is a fairly common back-end service task.

The easiest approach is to simply write CSV rows to an ``io.StringIO`` stream,
and then assign its value to :attr:`resp.text <falcon.Response.text>`:

.. tab-set::

    .. tab-item:: WSGI
        :sync: wsgi

        .. literalinclude:: ../../../examples/recipes/output_csv_text_wsgi.py
            :language: python

    .. tab-item:: ASGI
        :sync: asgi

        .. literalinclude:: ../../../examples/recipes/output_csv_text_asgi.py
            :language: python

Here we set the response ``Content-Type`` to :data:`~falcon.constants.MEDIA_CSV` as
recommended by `RFC 4180 <https://tools.ietf.org/html/rfc4180>`_, and assign
the downloadable file name ``report.csv`` via the ``Content-Disposition``
header (see also: :ref:`serve-downloadable-as`).

Streaming Large CSV Files on the Fly
------------------------------------

If generated CSV responses are expected to be very large, it might be worth
streaming the CSV data as it is produced. This approach will both avoid excessive
memory consumption, and reduce the viewer's time-to-first-byte (TTFB).

In order to stream CSV rows on the fly, we will initialize the CSV writer with
our own pseudo stream object. Our stream's ``write()`` method will simply
accumulate the CSV data in a list. We will then set :attr:`resp.stream
<falcon.Response.stream>` to a generator yielding data chunks from this list:

.. tab-set::

    .. tab-item:: WSGI
        :sync: wsgi

        .. literalinclude:: ../../../examples/recipes/output_csv_stream_wsgi.py
            :language: python

    .. tab-item:: ASGI
        :sync: asgi

        .. literalinclude:: ../../../examples/recipes/output_csv_stream_wsgi.py
            :language: python

        .. note::
            At the time of writing, Python does not support ``yield from`` here
            in an asynchronous generator, so we substitute it with a loop
            expression.
