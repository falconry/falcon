import csv


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
        for i in range(n + 1):
            writer.writerow((i, current))
            previous, current = current, current + previous

            for chunk in stream.result:
                yield chunk
            stream.clear()

    async def on_get(self, req, resp):
        resp.content_type = 'text/csv'
        resp.downloadable_as = 'report.csv'
        resp.stream = self.fibonacci_generator()
