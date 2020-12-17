.. _outputting_csv_recipe:

Outputting CSV Files
====================

Generating a CSV (or PDF, etc.) report and making it available as a downloadable
file is a fairly common back-end service task.

The easiest approach is to simply write CSV rows to an ``io.StringIO`` stream,
and then assign its value to :attr:`resp.text <falcon.Response.text>`:

.. tabs::

    .. group-tab:: WSGI

        .. code:: python

            class Report:

                def on_get(self, req, resp):
                    output = io.StringIO()
                    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writerow(('fruit', 'quantity'))
                    writer.writerow(('apples', 13))
                    writer.writerow(('oranges', 37))

                    resp.content_type = 'text/csv'
                    resp.downloadable_as = 'report.csv'
                    resp.text = output.getvalue()

    .. group-tab:: ASGI

        .. code:: python

            class Report:

                async def on_get(self, req, resp):
                    output = io.StringIO()
                    writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writerow(('fruit', 'quantity'))
                    writer.writerow(('apples', 13))
                    writer.writerow(('oranges', 37))

                    resp.content_type = 'text/csv'
                    resp.downloadable_as = 'report.csv'
                    resp.text = output.getvalue()

Here we set the response ``Content-Type`` to ``"text/csv"`` as
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

.. tabs::

    .. group-tab:: WSGI

        .. code:: python

            class Report:

                class PseudoTextStream:
                    def __init__(self):
                        self.clear()

                    def clear(self):
                        self.result = []

                    def write(self, data):
                        self.result.append(data.encode())

                def fibonacci_generator(self, n=1000):
                    stream = self.PseudoTextStream()
                    writer = csv.writer(stream, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writerow(('n', 'Fibonacci Fn'))

                    previous = 1
                    current = 0
                    for i in range(n+1):
                        writer.writerow((i, current))
                        previous, current = current, current + previous

                        yield from stream.result
                        stream.clear()

                def on_get(self, req, resp):
                    resp.content_type = 'text/csv'
                    resp.downloadable_as = 'report.csv'
                    resp.stream = self.fibonacci_generator()

    .. group-tab:: ASGI

        .. code:: python

            class Report:

                class PseudoTextStream:
                    def __init__(self):
                        self.clear()

                    def clear(self):
                        self.result = []

                    def write(self, data):
                        self.result.append(data.encode())

                async def fibonacci_generator(self, n=1000):
                    stream = self.PseudoTextStream()
                    writer = csv.writer(stream, quoting=csv.QUOTE_NONNUMERIC)
                    writer.writerow(('n', 'Fibonacci Fn'))

                    previous = 1
                    current = 0
                    for i in range(n+1):
                        writer.writerow((i, current))
                        previous, current = current, current + previous

                        for chunk in stream.result:
                            yield chunk
                        stream.clear()

                async def on_get(self, req, resp):
                    resp.content_type = 'text/csv'
                    resp.downloadable_as = 'report.csv'
                    resp.stream = self.fibonacci_generator()

        .. note::
            At the time of writing, Python does not support ``yield from`` here
            in an asynchronous generator, so we substitute it with a loop
            expression.
