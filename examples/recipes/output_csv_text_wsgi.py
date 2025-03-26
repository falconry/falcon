import csv
import io

import falcon


class Report:
    def on_get(self, req, resp):
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_NONNUMERIC)
        writer.writerow(('fruit', 'quantity'))
        writer.writerow(('apples', 13))
        writer.writerow(('oranges', 37))

        resp.content_type = falcon.MEDIA_CSV
        resp.downloadable_as = 'report.csv'
        resp.text = output.getvalue()
