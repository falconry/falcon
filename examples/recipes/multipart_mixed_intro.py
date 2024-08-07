import falcon
import falcon.media

parser = falcon.media.MultipartFormHandler()
parser.parse_options.media_handlers['multipart/mixed'] = (
    falcon.media.MultipartFormHandler()
)
