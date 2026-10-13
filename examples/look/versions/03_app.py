import falcon

from .images import Resource

app = application = falcon.App()

images = Resource()
app.add_route('/images', images)
