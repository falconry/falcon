import csv
import io


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
