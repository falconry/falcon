import cgi
import json
import pytest
import base64

import falcon
from falcon import media
from falcon import testing

from _util import create_app  # NOQA: I100


"""
Request takes tuples like (filename, data, content_type, headers)

"""


class MultipartAnalyzer:
    def on_post(self, req, resp):
        values = []
        for part in req.media:
            data = part.data.decode()
            inner_form = []
            if part.content_type.startswith('multipart/mixed'):
                print(f'we are in part with {part.data}')
                for nested in part.media:
                    print(f'we are in nested with {nested.name}')
                    inner_form.append(
                        {
                            'content_type': nested.content_type,
                            'data': nested.data.decode(),
                            'filename': nested.filename,
                            'name': nested.name,
                            'text': nested.text,
                        }
                    )
                data = inner_form

            values.append(
                {
                    'content_type': part.content_type,
                    'data': data,
                    'filename': part.filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                    'text': part.text,
                }
            )

        resp.media = values

    def on_post_media(self, req, resp):
        deserialized = []
        for part in req.media:
            part_media = part.get_media()
            assert part_media == part.media
            deserialized.append(part_media)

        resp.media = deserialized

    def on_post_image(self, req, resp):
        values = []
        for part in req.media:
            # Save a copy of the image, encode in base64 and re-decode to compare. This way we avoid invalid characters
            # and get a more 'manageable' output.
            new_filename = part.filename.split('.')[0] + '_posted.png'
            f = open(new_filename, 'w+b')
            f.write(part.data)
            f.close()
            new_file64 = base64.b64encode(open(new_filename, 'rb').read())
            values.append(
                {
                    'content_type': part.content_type,
                    'data': new_file64.decode(),
                    'filename': part.filename,
                    'new_filename': new_filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                }
            )

        resp.media = values


class AsyncMultipartAnalyzer:
    async def on_post(self, req, resp):
        values = []
        form = await req.get_media()
        async for part in form:
            values.append(
                {
                    'content_type': part.content_type,
                    'data': (await part.data).decode(),
                    'filename': part.filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                    'text': (await part.text),
                }
            )
        resp.media = values

    async def on_post_media(self, req, resp):
        deserialized = []
        form = await req.media
        async for part in form:
            part_media = await part.get_media()
            assert part_media == await part.media
            deserialized.append(part_media)

        resp.media = deserialized

    async def on_post_image(self, req, resp):
        values = []
        form = await req.get_media()
        async for part in form:
            new_filename = part.filename.split('.')[0] + '_posted.png'
            data = await part.data
            values.append(
                {
                    'content_type': part.content_type,
                    'data': base64.b64encode(data).decode(),
                    'filename': part.filename,
                    'new_filename': new_filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                }
            )
        resp.media = values


class MultipartFileUpload:
    def on_post(self, req, resp):
        upload = cgi.FieldStorage(fp=req.stream, environ=req.env)
        data = upload['file'].file.read().decode('utf-8')
        resp.media = dict(data=data)


class AsyncMultipartFileUpload:
    async def on_post(self, req, resp):
        deserialized = []
        form = await req.media
        async for part in form:
            upload = cgi.FieldStorage(fp=part.stream, environ=req.scope)
            print(f'upload is {upload.fp.read()}')
            data = await upload['file'].file.read().decode('utf-8')

            print(f'the dict is {dict(data=data)} and the dump is {dict(data=data)}')
            deserialized.append(dict(data=data))
        resp.media = deserialized


@pytest.fixture
def client(asgi):
    app = create_app(asgi)
    parser = media.MultipartFormHandler()
    parser.parse_options.media_handlers[
        'multipart/mixed'
    ] = media.MultipartFormHandler()
    app.req_options.media_handlers = media.Handlers(
        {
            falcon.MEDIA_JSON: media.JSONHandler(),
            falcon.MEDIA_MULTIPART: parser,  # media.MultipartFormHandler()
        }
    )

    app.req_options.default_media_type = falcon.MEDIA_MULTIPART
    resource = AsyncMultipartAnalyzer() if asgi else MultipartAnalyzer()
    resourcecgi = AsyncMultipartFileUpload() if asgi else MultipartFileUpload()
    app.add_route('/submit', resource)
    app.add_route('/uploadcgi', resourcecgi)
    app.add_route('/media', resource, suffix='media')
    app.add_route('/image', resource, suffix='image')

    return testing.TestClient(app)


# ----- TESTING THE files PARAMETER IN simulate_request FOR DIFFERENT DATA TYPES
payload1 = b'{"debug": true, "message": "Hello, world!", "score": 7}'

FILES1 = {
    'fileobj': 'just some stuff',
    'hello': (None, 'world'),
    'document': (None, payload1, 'application/json'),
    'file1': ('test.txt', 'Hello, world!', 'text/plain'),
}
FILES1_TUPLES = [
    ('fileobj', 'just some stuff'),
    ('hello', (None, 'world')),
    ('document', (None, payload1, 'application/json')),
    ('file1', ('test.txt', 'Hello, world!', 'text/plain')),
]

FILES1_RESP = [
    {
        'content_type': 'text/plain',
        'data': 'just some stuff',
        'filename': 'fileobj',
        'name': 'fileobj',
        'secure_filename': 'fileobj',
        'text': 'just some stuff',
    },
    {
        'content_type': 'text/plain',
        'data': 'world',
        'filename': None,
        'name': 'hello',
        'secure_filename': None,
        'text': 'world',
    },
    {
        'content_type': 'application/json',
        'data': '{"debug": true, "message": "Hello, world!", "score": 7}',
        'filename': None,
        'name': 'document',
        'secure_filename': None,
        'text': None,
    },
    {
        'content_type': 'text/plain',
        'data': 'Hello, world!',
        'filename': 'test.txt',
        'name': 'file1',
        'secure_filename': 'test.txt',
        'text': 'Hello, world!',
    },
]


def test_upload_multipart_dict(client):
    resp = client.simulate_post('/submit', files=FILES1)

    assert resp.status_code == 200
    assert resp.json == FILES1_RESP


def test_upload_multipart_list(client):
    resp = client.simulate_post('/submit', files=FILES1_TUPLES)

    assert resp.status_code == 200
    assert resp.json == FILES1_RESP


FILES3 = {
    'bytes': ('bytes', b'123456789abcdef\n' * 64 * 1024 * 2, 'application/x-falcon'),
    'empty': (None, '', 'text/plain'),
}


def test_body_too_large(client):
    resp = client.simulate_post('/submit', files=FILES3)
    assert resp.status_code == 400
    assert resp.json == {
        'description': 'body part is too large',
        'title': 'Malformed multipart/form-data request media',
    }


FILES5 = {
    'factorials': (
        None,
        '{"count": 6, "numbers": [1, 2, 6, 24, 120, 720]}',
        'application/json',
    ),
    'person': (
        None,
        'name=Jane&surname=Doe&fruit=%F0%9F%8D%8F',
        'application/x-www-form-urlencoded',
    ),
}


def test_upload_multipart_media(client):
    resp = client.simulate_post('/media', files=FILES5)

    assert resp.status_code == 200
    assert resp.json == [
        {'count': 6, 'numbers': [1, 2, 6, 24, 120, 720]},
        {
            'fruit': b'\xF0\x9F\x8D\x8F'.decode('utf8'),  # u"\U0001F34F",
            'name': 'Jane',
            'surname': 'Doe',
        },
    ]


def asserts_data_types(resp):
    assert resp.status_code == 200
    expected_list = [
        {
            'content_type': 'text/plain',
            'data': 'just some stuff',
            'filename': 'fileobj',
            'name': 'fileobj',
            'secure_filename': 'fileobj',
            'text': 'just some stuff',
        },
        {
            'content_type': 'text/plain',
            'data': '5',
            'filename': None,
            'name': 'data1',
            'secure_filename': None,
            'text': '5',
        },
        {
            'content_type': 'text/plain',
            'data': 'hello',
            'filename': None,
            'name': 'data2',
            'secure_filename': None,
            'text': 'hello',
        },
        {
            'content_type': 'text/plain',
            'data': 'bonjour',
            'filename': None,
            'name': 'data2',
            'secure_filename': None,
            'text': 'bonjour',
        },
        {
            'content_type': 'text/plain',
            'data': 'world',
            'filename': None,
            'name': 'hello',
            'secure_filename': None,
            'text': 'world',
        },
        {
            'content_type': 'application/json',
            'data': '{"debug": true, "message": "Hello, world!", "score": 7}',
            'filename': None,
            'name': 'document',
            'secure_filename': None,
            'text': None,
        },
        {
            'content_type': 'text/plain',
            'data': 'Hello, world!',
            'filename': 'test.txt',
            'name': 'file1',
            'secure_filename': 'test.txt',
            'text': 'Hello, world!',
        },
    ]
    # Result will be unordered, because both fileobj and data are present. When all files are tuples, response will be
    # unordered if json contains dictionaries - then resp.json == expected_list can be used.
    assert len(resp.json) == len(expected_list)
    assert all(map(lambda el: el in expected_list, resp.json))


# -------Tests for multipart with files param and json data, where data comes in different types----------
def test_upload_multipart_datalist(client):
    resp = client.simulate_post(
        '/submit', files=FILES1, json=[('data1', 5), ('data2', ['hello', 'bonjour'])]
    )
    asserts_data_types(resp)


def test_upload_multipart_datalisttuple(client):
    resp = client.simulate_post(
        '/submit', files=FILES1, json=[('data1', 5), ('data2', ('hello', 'bonjour'))]
    )
    asserts_data_types(resp)


def test_upload_multipart_datalistdict(client):
    """json data list with dict"""
    resp = client.simulate_post(
        '/submit', files=FILES1, json=[('data1', 5), ('data2', {'hello', 'bonjour'})]
    )
    asserts_data_types(resp)


def test_upload_multipart_datadict(client):
    """json data dict with list"""
    resp = client.simulate_post(
        '/submit', files=FILES1, json={'data1': 5, 'data2': ['hello', 'bonjour']}
    )
    asserts_data_types(resp)


def test_upload_multipart_datadicttuple(client):
    """json data dict with tuple"""
    resp = client.simulate_post(
        '/submit', files=FILES1, json={'data1': 5, 'data2': ('hello', 'bonjour')}
    )
    asserts_data_types(resp)


def test_upload_multipart_datadictdict(client):
    """json data dict with dict"""
    resp = client.simulate_post(
        '/submit', files=FILES1, json={'data1': 5, 'data2': {'hello', 'bonjour'}}
    )
    asserts_data_types(resp)


def test_invalid_files(client):
    """invalid file type"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files='heya')


def test_invalid_files(client):
    """empty file in files"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files={'file': ()})


def test_invalid_dataint(client):
    """invalid data type in json, int"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files=FILES1, json=5)


def test_invalid_datastr(client):
    """invalid data type in json, str"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files=FILES1, json='yo')


def test_invalid_databyte(client):
    """invalid data type in json, b''"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files=FILES1, json=b'yo self')


# ------TEST UPLOADING ACTUAL FILES: TEXT, IMAGE ----------------------------

LOREM_FILE = (
    'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do '
    'eiusmod tempor\n'
    'incididunt ut labore et dolore magna aliqua. Dolor sed viverra '
    'ipsum nunc\n'
    'aliquet bibendum enim. In massa tempor nec feugiat. Nunc aliquet '
    'bibendum enim\n'
    'facilisis gravida. Nisl nunc mi ipsum faucibus vitae aliquet nec '
    'ullamcorper.\n'
    'Amet luctus venenatis lectus magna fringilla. Volutpat maecenas '
    'volutpat blandit\n'
    'aliquam etiam erat velit scelerisque in. Egestas egestas fringilla '
    'phasellus\n'
    'faucibus scelerisque eleifend. Sagittis orci a scelerisque purus '
    'semper eget\n'
    'duis. Nulla pharetra diam sit amet nisl suscipit. Sed adipiscing '
    'diam donec\n'
    'adipiscing tristique risus nec feugiat in. Fusce ut placerat orci '
    'nulla.\n'
    'Pharetra vel turpis nunc eget lorem dolor. Tristique senectus et '
    'netus et\n'
    'malesuada.'
)


def test_upload_file(client):
    resp = client.simulate_post(
        '/submit', files={'file': open('tests/files/loremipsum.txt', 'rb')}
    )

    assert resp.status_code == 200
    assert resp.json == [
        {
            'content_type': 'text/plain',
            'data': LOREM_FILE,
            'filename': 'loremipsum.txt',
            'name': 'file',
            'secure_filename': 'loremipsum.txt',
            'text': LOREM_FILE,
        },
    ]


def test_upload_image(client):
    filename = 'tests/files/falcon.png'
    imagebin = open(filename, 'rb').read()
    file64 = base64.b64encode(imagebin)

    resp = client.simulate_post(
        '/image', files={'image': (filename, open(filename, 'rb'))}
    )
    new_filename = filename.split('.')[0] + '_posted.png'

    assert resp.status_code == 200
    assert resp.json == [
        {
            'content_type': 'text/plain',
            'data': file64.decode(),
            'filename': filename,
            'new_filename': new_filename,
            'name': 'image',
            'secure_filename': filename.replace('/', '_'),
        }
    ]


FILES6 = {
    'field1': 'Joe Blow',
    'docs': (
        None,
        json.dumps(
            {
                'file1': (
                    'file1.txt',
                    'this is file1',
                    None,
                    {'Content-Disposition': 'attachment'},
                ),
                'file2': (
                    'file2.txt',
                    'Hello, World!',
                    None,
                    {'Content-Disposition': 'attachment'},
                ),
            }
        ).encode(),
        'multipart/mixed',
    ),
    'document': (None, payload1, 'application/json'),
}


def test_nested_multipart_mixed(client):
    resp = client.simulate_post('/submit', files=FILES6)
    print(f'response in mixed is {resp.json}')
    assert resp.status_code == 200
    assert resp.json == [
        {
            'content_type': 'text/plain',
            'data': 'Joe Blow',
            'filename': 'field1',
            'name': 'field1',
            'secure_filename': 'field1',
            'text': 'Joe Blow',
        },
        {
            'content_type': 'multipart/mixed',
            'data': '{"file1": ["file1.txt", "this is file1"], "file2": ["file2.txt", "Hello, World!"]}',
            'filename': None,
            'name': 'docs',
            'secure_filename': None,
            'text': None,
        },
        {
            'content_type': 'application/json',
            'data': '{"debug": true, "message": "Hello, world!", "score": 7}',
            'filename': None,
            'name': 'document',
            'secure_filename': None,
            'text': None,
        },
    ]


# def test_upload_file_cgi(client):
#     resp = client.simulate_post('/uploadcgi', files={'file': open('tests/loremipsum.txt', 'rb')})
#
#     # assert resp.status_code == 200
#     assert resp.json == LOREM_FILE
