Falcon
======

<img align="right" style="padding-left: 10px" src="https://upload.wikimedia.org/wikipedia/commons/thumb/3/39/Brown-Falcon%2C-Vic%2C-3.1.2008.jpg/160px-Brown-Falcon%2C-Vic%2C-3.1.2008.jpg" alt="falcon picture" />

**[Experimental]**

Falcon is a fast, light-weight framework for building cloud APIs. It tries to do as little as possible while remaining highly effective. 

> Perfection is finally attained not when there is no longer anything to add, but when there is no longer anything to take away. 
>
> *- Antoine de Saint-Exupéry*

### Design Goals ###

**Light-weight.** Only the essentials are included, with few dependencies. We work to keep the code lean-n-mean, making Falcon easier to test, optimize, and deploy. 

**Surprisingly agile.** Although light-weight, Falcon is surprisingly effective. Getting started with the framework is easy. Common web API idioms are supported out of the box without getting in your way. This is a framework designed for journeyman web developers and master craftsman alike.

**Cloud-friendly.** Falcon uses the web-friendly Python language, and speaks WSGI, so you can deploy it on your favorite stack. The framework is designed from the ground up to embrace HTTP, not work against it. Plus, diagnostics are built right in to make it easier to track down sneaky bugs and frustrating performance problems. 

### Usage ###

More/better docs are on our TODO list, but in the meantime, here is a simple example showing how to create a Falcon API.

```python
class ThingsResource:
    def on_get(self, req, resp):
        """Handles GET requests"""
        resp.status = falcon.HTTP_200
        resp.body = 'Hello world!'

# falcon.API instances are callable WSGI apps
wsgi_app = api = falcon.API()

# Resources are represented by long-lived class instances
things = ThingsResource()

# things will handle all requests to the '/things' URL path
api.add_route('/things', things)
```

Here is a more involved example, demonstrating getting headers and query parameters, handling errors, and reading/writing message bodies. 

```python
class ThingsResource:

    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('thingsapi.' + __name__)

    def on_get(self, req, resp):
        user_id = req.get_param('user_id', required=True)
        marker = req.get_param('marker', default='')
        limit = req.get_param('limit', default=50)

        # Alternatively, do this in middleware
        token = req.get_header('X-Auth-Token')

        if token is None:
            raise falcon.HTTPUnauthorized('Auth token required',
                                          'Please provide an auth token as '
                                          'part of the request',
                                          'http://docs.example.com/auth')

        if not token_is_valid(token, user_id):
            raise falcon.HTTPUnauthorized('Authentication required',
                                          'The provided auth token is not '
                                          'valid. Please request a new token '
                                          'and try again.',
                                          'http://docs.example.com/auth')

        # Alternatively, do this in middleware
        if not req.client_accepts_json():
            raise falcon.HTTPUnsupportedMediaType(
                'Media Type not Supported',
                'This API only supports the JSON media type.',
                'http://docs.examples.com/api/json')

        try:
            result = self.db.get_things(marker, limit)
        except Exception as ex:
            self.logger.error(ex)

            description = ('Aliens have attacked our base. We will be back'
                           'as soon as we fight them off. We appreciate your'
                           'patience.')

            raise falcon.HTTPServiceUnavailable('Service Outage', description)

        resp.set_header('X-Powered-By', 'Donuts')
        resp.status = falcon.HTTP_200
        resp.body = json.dumps(result)

    def on_post(self, req, resp):
        try:
            raw_json = req.body.readall()
        except Exception:
            raise falcon.HTTPError(falcon.HTTP_748,
                                   'Read Error',
                                   "Could not read the request body. I bet "
                                   "it's them ponies again.")

        try:
            thing = json.loads(raw_json.decode('utf-8'))
        except ValueError:
            raise falcon.HTTPError(falcon.HTTP_753,
                                   'Malformed JSON',
                                   'Could not decode the request body. The '
                                   'JSON was incorrect.')

        try:
            proper_thing = self.db.add_thing(thing)
        except StorageError:
            raise falcon.HTTPError(falcon.HTTP_725,
                                   'Database Error',
                                   "Sorry, couldn't write your thing to the "
                                   'database. It worked on my machine.')

        resp.status = falcon.HTTP_201
        resp.set_header('Location', '/{userId}/things/' + proper_thing.id)

wsgi_app = api = falcon.API()

db = StorageEngine()
things = ThingsResource(db)
api.add_route('/{user_id}/things', things)

```

### Contributing ###

Pull requests are welcome. Just make sure to include tests and follow PEP 8 and your commit messages are formatted using [AngularJS conventions][ajs] (one-liners are OK for now but body and footer may be required as the project matures). Comments follow [Google's style guide][goog-style-comments].

[ajs]: http://goo.gl/QpbS7
[goog-style-comments]: http://google-styleguide.googlecode.com/svn/trunk/pyguide.html#Comments

