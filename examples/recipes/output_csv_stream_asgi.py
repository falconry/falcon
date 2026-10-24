from __future__ import annotations

from collections.abc import AsyncIterator
import csv

import falcon
import falcon.asgi


class Report:
    class PseudoTextStream:
        def __init__(self) -> None:
            self.clear()

        def clear(self) -> None:
            self.result: list[bytes] = []

        def write(self, data: str) -> None:
            self.result.append(data.encode())

    async def fibonacci_generator(self, n: int = 1000) -> AsyncIterator[bytes]:
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

    async def on_get(
        self, req: falcon.asgi.Request, resp: falcon.asgi.Response
    ) -> None:
        resp.content_type = falcon.MEDIA_CSV
        resp.downloadable_as = 'report.csv'
        resp.stream = self.fibonacci_generator()
