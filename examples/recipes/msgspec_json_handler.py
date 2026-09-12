import msgspec

import falcon.media

json_handler = falcon.media.JSONHandler(
    dumps=msgspec.json.encode,
    loads=msgspec.json.decode,
)
