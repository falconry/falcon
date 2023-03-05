import base64
import io
import json

import pytest

import falcon
from falcon import media
from falcon import testing

from _util import create_app  # NOQA: I100


"""
Request takes tuples like (filename, data, content_type, headers)

"""


class MultipartAnalyzer:
    @staticmethod
    def on_post(req, resp):
        values = []
        for part in req.media:
            # For mixed nested file requests
            part_type = part.content_type
            inner_form = []
            if part.content_type.startswith('multipart/mixed'):
                for nested in part.media:
                    inner_form.append({'name': nested.name, 'text': nested.text})
                    part_type = 'multipart/mixed'
            # ----------------------------------------------------
            values.append(
                {
                    'content_type': part_type,
                    'data': inner_form or part.data.decode(),
                    'filename': part.filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                    'text': part.text,
                }
            )

        resp.media = values

    @staticmethod
    def on_post_media(req, resp):
        deserialized = []
        for part in req.media:
            part_media = part.get_media()
            assert part_media == part.media

            deserialized.append(part_media)
        resp.media = deserialized

    @staticmethod
    def on_post_image(req, resp):
        values = []
        for part in req.media:
            values.append(
                {
                    'content_type': part.content_type,
                    'data': base64.b64encode(part.data).decode(),
                    'filename': part.filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                }
            )

        resp.media = values


class AsyncMultipartAnalyzer:
    @staticmethod
    async def on_post(req, resp):
        values = []
        form = await req.get_media()
        async for part in form:
            # For mixed nested file requests
            part_type = part.content_type
            inner_form = []
            if part_type.startswith('multipart/mixed'):
                part_form = await part.get_media()
                async for nested in part_form:
                    inner_form.append({'name': nested.name, 'text': await nested.text})
                    part_type = 'multipart/mixed'
            # ----------------------------------------------------
            values.append(
                {
                    'content_type': part_type,
                    'data': inner_form or (await part.data).decode(),
                    'filename': part.filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                    'text': (await part.text),
                }
            )
        resp.media = values

    @staticmethod
    async def on_post_media(req, resp):
        deserialized = []
        form = await req.media
        async for part in form:
            part_media = await part.get_media()
            assert part_media == await part.media
            deserialized.append(part_media)

        resp.media = deserialized

    @staticmethod
    async def on_post_image(req, resp):
        values = []
        form = await req.get_media()
        async for part in form:
            data = await part.data
            values.append(
                {
                    'content_type': part.content_type,
                    'data': base64.b64encode(data).decode(),
                    'filename': part.filename,
                    'name': part.name,
                    'secure_filename': part.secure_filename if part.filename else None,
                }
            )
        resp.media = values


@pytest.fixture
def client(asgi):
    app = create_app(asgi)

    # For handling mixed nested requests -----------------------
    parser = media.MultipartFormHandler()
    parser.parse_options.media_handlers[
        'multipart/mixed'
    ] = media.MultipartFormHandler()

    # ------------------------------------------------------------

    app.req_options.media_handlers = media.Handlers(
        {
            falcon.MEDIA_JSON: media.JSONHandler(),
            falcon.MEDIA_MULTIPART: parser,  # media.MultipartFormHandler()
        }
    )

    app.req_options.default_media_type = falcon.MEDIA_MULTIPART
    resource = AsyncMultipartAnalyzer() if asgi else MultipartAnalyzer()

    app.add_route('/submit', resource)
    app.add_route('/media', resource, suffix='media')
    app.add_route('/image', resource, suffix='image')

    return testing.TestClient(app)


# region - TESTING THE files PARAMETER IN simulate_request FOR DIFFERENT DATA

# region - TESTING CONSISTENCY OF UPLOAD OF DIFFERENT FORMAT FOR files

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


# endregion

# region - TEST DIFFERENT DATA TYPES in json part
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

    # Result will be unordered, because both fileobj and data are present.
    # When all files are tuples, response will be unordered if json
    # contains dictionaries - then resp.json == expected_list can be used.

    assert len(resp.json) == len(expected_list)
    assert all(map(lambda el: el in expected_list, resp.json))


def test_upload_multipart_datalist(client):
    resp = client.simulate_post(
        '/submit',
        files=FILES1,
        json=[('data1', 5), ('data2', ['hello', 'bonjour']), ('empty', None)],
    )
    print(resp.json)
    asserts_data_types(resp)


def test_upload_multipart_datalisttuple(client):
    resp = client.simulate_post(
        '/submit',
        files=FILES1,
        json=[('data1', 5), ('data2', ('hello', 'bonjour')), ('empty', None)],
    )
    asserts_data_types(resp)


def test_upload_multipart_datalistdict(client):
    """json data list with dict"""
    resp = client.simulate_post(
        '/submit',
        files=FILES1,
        json=[('data1', 5), ('data2', {'hello', 'bonjour'}), ('empty', None)],
    )
    asserts_data_types(resp)


def test_upload_multipart_datadict(client):
    """json data dict with list"""
    resp = client.simulate_post(
        '/submit',
        files=FILES1,
        json={'data1': 5, 'data2': ['hello', 'bonjour'], 'empty': None},
    )
    asserts_data_types(resp)


def test_upload_multipart_datadicttuple(client):
    """json data dict with tuple"""
    resp = client.simulate_post(
        '/submit',
        files=FILES1,
        json={'data1': 5, 'data2': ('hello', 'bonjour'), 'empty': None},
    )
    asserts_data_types(resp)


def test_upload_multipart_datadictdict(client):
    """json data dict with dict"""
    resp = client.simulate_post(
        '/submit',
        files=FILES1,
        json={'data1': 5, 'data2': {'hello', 'bonjour'}, 'empty': None},
    )
    asserts_data_types(resp)


# endregion


# region - TEST INVALID DATA TYPES FOR FILES
def test_invalid_files(client):
    """invalid file type"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files='heya')


def test_invalid_files_null(client):
    """empty file in files"""
    with pytest.raises(ValueError):
        client.simulate_post('/submit', files={'file': ()})


# endregion

# region - TEST NESTED FILES UPLOAD


FILES6 = {
    'field1': 'Joe Blow',
    'docs': (
        None,
        json.dumps(
            {
                'file1': ('file1.txt', 'this is file1'),
                'file2': (
                    'file2.txt',
                    'Hello, World!',
                ),
            }
        ).encode(),
        'multipart/mixed',
    ),
    'document': (None, payload1, 'application/json'),
}


def test_nested_multipart_mixed(client):
    resp = client.simulate_post('/submit', files=FILES6)
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
            'data': [
                {'name': 'file1', 'text': 'this is file1'},
                {'name': 'file2', 'text': 'Hello, World!'},
            ],
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


# endregion

# endregion

#  region - TEST UPLOADING ACTUAL FILES: TEXT, IMAGE

IMAGE_FILE = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\xe1\x00\x00'
    b'\x00\xe1\x08\x03\x00\x00\x00\tm"H\x00\x00\x00uPLTE\xff\xff\xff'
    b'\xf0\xadN\xf0\xacK\xef\xa9A\xf0\xaaF\xef\xa8?\xf0\xaaE\xef\xa8'
    b'=\xff\xfe\xfc\xfe\xfb\xf6\xfd\xf6\xed\xfe\xf8\xf1\xf1\xb3'
    b'\\\xfb\xea\xd5\xfd\xf3\xe6\xfa\xe6\xcd\xf3\xbdu\xf2\xb9k\xf0'
    b'\xafQ\xf4\xc5\x88\xf9\xe1\xc3\xf7\xd6\xad\xf8\xdc\xb8\xf5\xcc'
    b'\x97\xfc\xef\xde\xf1\xb5a\xf2\xbbp\xf8\xd9\xb2\xfb\xe9\xd3\xf1'
    b'\xb1W\xfa\xe4\xc8\xf5\xc9\x90\xf6\xd1\xa1\xf4\xc2\x81\xf7\xd4'
    b'\xa7\xf4\xc7\x8b\xf5\xca\x94\xef\xa42\xf6\xd0\x9e_\xd7\x99\xa5'
    b'\x00\x00\rcIDATx\x9c\xed]i\x97\xaa8\x10\x95JHX\x14A\x11Q\xdb'
    b'\x05\xed\xf6\xff\xff\xc4aS\x11\x03$!\x10f\xc6\xfb\xe9\xbd\xd3'
    b'\x07\xcc%IU\xa5\xb6\xccf_|\xf1\xc5\x17_|\xf1\xc5\x17\xff38\xba'
    b'\x0700\x1c?\xd0=\x84a\x11\xafh\xa4{'
    b'\x0c\x83"\xc6@-\xdd\x83\x18\x12\x0b\nx\xab{'
    b'\x10C"\x9dA\x83z\xbaG1 '
    b'\xbc\x15\x18\xb0\xd7=\x8a\x01\xe1\x1c\xc10\xd0\x7fX\xce\xd8'
    b'\xf3\x94 \xac\\\xdd\xe3\x18\x0e{'
    b'l\x18\x06>\xeb\x1eF\x1b\xac^R\xf0FR\x82\x06Z\xa8\x1a\xcd\x10X'
    b'\xcf{<\xbcA\x19A8*\x1b\xcd\x00\x88\xa9/\xff\xf0\x89f\x04\x8di'
    b'+C\x1f\xdd\xa4\x9fu\x00\x8c\xc9/\xd2%"\x1b\xe9\x87w\x05A\x83('
    b'\x1c\x90j\xa4\xb2\x1e-e\x1f\xde\xa2\x82 '
    b'$*\x87\xa4\x18kb\xa0X\xf2\xd9eI\xd0 '
    b'\x13V\xf7w3\x15\x13\x92\x87\x02wU\xae\xd1)\xdb\xa4\x87T\x14'
    b'\x82\xac\xb2X\xe3\x92\xa0\x01J\x07\xa5\x12\x17\xb3\x879\xb24'
    b'\x9f\x04{\xa8\x9bAa\xad\xf3}\x84B\xb9\xa7\x9fk\xd4 '
    b'\x17\xb5\x03S\x05gG\x8aM$g3o\xc9\x83\xe0T\xcf\x15\x11-\xe6\x00'
    b'\xe4\x1cH\x1ez\x124\xcc)\xea\xfb\xd8\x7f\xec"r\x95zA\x82_\x0c'
    b'\xd1\xf4\xfc\x88\xf6\x1d?\x07H\xa5\xb4\xe1\xa22\x85\xc6\xf4'
    b'\xce\x86\xd1\xf1\xb5\x87`.\xa5\r}0*\xaf\xb0U\x8f\xb0\x1f\xa2'
    b'\x15\xaa\x0c\x8f\xdce\xde\xf1C+S\x08\xbb)\xf9\x11\xed\xe8hV'
    b'\xf8\xa5\x0c\xa5\x16iu\x17\xa6\xb2j:\x0c\x9dK\x8d\x9f\xa4\xb2'
    b'\xf6\xa81I\x86?\t\x90w~\xa9\x18<\xc9\xbc\xe9N&\xc8\xd0\xb9\xce'
    b'\t6\xea\x80\x9d\xd4\xcb\xd0\xfbK& '
    b'i\xdc\xc8\xa7\x1f\xd3\x97\xc1\x94\xb2\xd8\xc2w\x86\x06\xd1\xac'
    b'-\x9c0\xc1\x88EO\xda\x81\xe4\xd7\xde&\xa7R\x15\xc1\x8b|@\x9f'
    b'\xab\xf314\xa9)t>6\xb36\xbb4\xde\x04\xd00{'
    b'\xc5\x14\xca\x99\xa4\xf5Ej\xe0_\xc5\x03\xe7\x82\x15_\x8e\xec'
    b'\xbd\xf7\x82\xf9#\xf5\xeau}MH\x9f\xa1\xe5a/\x7fW]\xf4\xd2O\xbf'
    b'\x96{\xf9\xfc\xe3\xc5#{'
    b'1\x9cp\xbd2q\x17\xbd\xf4\xcb\x1brG\x82\xb8\xbeH\xc7\xf5Dy\x87'
    b'\xbd\x818\xe8e\x1f^rX\x11\xf9x\x95\xe4\x86\x16\x87w\xdd\xa1'
    b'\xce\xb5\xf9\xfc\xee\xb2>\xce3C4\x9bc,'
    b'S\xef:\xef\xdez\x95\xcf.wjJ\xb1g\xfc\xc8\xf0\x9e\x1ao\x13\x88'
    b'\xd0K\t\x82\xecW\xb7W\x8c\xdf\x81\xe3\xa0\x86\x9b\x15\xfaD\x88'
    b'^\xf6\xd1\xe5\x14E\n\x97\xb2\xde7\xa4\xd2w\xee\xab6\xad\xce'
    b'\x86\x9c1\x93#f2\x1c\xce\xfa^\xf8\x94Or\xbe\r\x87J\x9d\x99\n'
    b'\x9c>\x95E\x06$\x1f\xc0j\xfd\xb5=\x15\xa6\x97\xed\xc1\x1e\x04g'
    b'\x11\x9b\xa1\x01\x03\x1c0\xd2\xf9\x93\xe0g\xc0\xaa\x97{'
    b'\x93\xa1\x0es`\xe5\x116w-\xbe\xfd\xf2\x91\xcc\xfb\xe9\xae&\x86'
    b'\x06\x95\x0eC6\xfcP\xf3\x99\xa8\x15\xa8\xef\xa7nd\x08+\x95\xc2'
    b'\xc6M\x98\x12\xad\x13\x80{\x0b\x84\xa6}('
    b"m\xc93\x11\xcf\xe5&\x90\xec\xfaG\x18>N\x87/\xa8S\x8a'q\x05"
    b'\x91\x01\xe8Y\x81S\xacA['
    b'\x14_P\x91;#\x92\x12\xa1\x061\x94\x88\x82E\xcb\xfePd\xbc\x85R['
    b'\x10\x90\x8a\tL\xe1\xb4\xfd<V\x11\rn['
    b"%\xcd@;iC\xb4\x8e\x0f'\xc6\xdb\xef\xf4O\x8e\x8aAb\x89b\xb2Q"
    b'\xe7\x96\xfe1\xdb~\xca<\xf4|\xbd\xc5:\xbbt\x00\xa8\xaf2\x84'
    b'\xe9\xb52\xecc\xd4\xe7H\x84\xd5\x04\x90\xb9Zc\xc3\xed\xf8\xc8r'
    b'~\xf4\x07\xa2\xf6\xef\xc7\x001\x94\x1b\xfdu\x97w\x1d}N.\x8e'
    b'!\xb8FS\x15\xa8>\xc6\xbei\xb2\xdb\x1e\x90\xcc_\xc9\xd0*\xc6'
    b'\x180\x83!"\n^\xe7('
    b'\xa4\xc5\xcd\x8f\x98&\x84\x81N\xa5L_\xd4;\xa8T\xec|6\xfbt6\xb7'
    b"\x01\x05C%\x81\x9c\xba\xa5\x81\x99\xc8\xa8'!1\x03H.O\x86\x0b"
    b'\x1c\xe2\x80\x04\x12\xc7P\x11U\x08\x862\x1b\x86\x81\x03\x87'
    b']\x05 ,o6\x02\xe6\x1a\x9e\x0f\x9a\xa6\xc4gwP\xc1\xfcq\xeb\xc8'
    b'?\x85d\xe8tH\x9eI\xcc\x8e\xa3B+\xb5\xf9l\xfd\x81\x1e\xc9\xf7'
    b"\x9c\xb0v\\\x9f\x1b\xb0\x80\xda\xe0|g\xfe\xe9\x06'XI\xf1\xee"
    b'\xfa\xd8{\xeeilq\x1e\xd4\t\x8e\x928\xff\xdbe\xd8\x94\x00\x93W'
    b'\xa6wk\xd9\x12X.EF\x18;^\xfb\n\xed\xb8\x0c\xab6\xdf\xc1\xfb7'
    b'\x1b6\n\xf4B\xd7\x11\xa32$r\xe5P\xff\xdc\xa7&<Z\xbe\xae\xc7'
    b'\xaf\x9f9<\x0c\xec\x90\x16\xeb]\x03Z2u\x08P\x04\xb4\xeeXZW\xde'
    b'}=j\xd5\xbf+\xe0\xb6\xc5\x1di\x03\xbc_\x0b\x8d\x9b\xf6a\xef'
    b'\x05\xec,3h\xd9@!\xe7\x14\x92\xb1\xcb\x00\xad_\x81\xd3\x00'
    b'\xa0[c\x04\xae\xcbo\xf0\x00\x1e?\r\xf2 '
    b'\xe2\x9e\xc6\xd0\xb0T=\xde)\x1cQ\xcc<\x11\xaf\x04\x1c\x0f`\xb2'
    b'\x95\xe3\x9dW\xceh\xc9d\xb5\x13\x11\x1f5\xd0\xf3\xe7('
    b'm\xceS\x85\\\xda\xbd\x02\x1c\x842A\xc8\xea\xe3\xe0\xc8\xe14('
    b'\x1e\xd5\x96\xc8\x1a\x1fE\\d\x80\x92\x9a\xc4\xe14Iu\xd6\xc8Y'
    b'\xbe\x90#\x17\xe37\x1b\xc7\xe3\xb4gzx)\x15`#\x94U\x00\xf4^1UY'
    b'\x99r\xcc\xa7\xf4\xd6W\x85biYh\xff\\\xa96\xaf \xd5\xdd>\xe5G,'
    b'\xec\xf7r%\xf1\x9a\xa4\xa4oX\xab7\xb8Ox\xe5\x94\x94%o\xbc'
    b'\xaaBoI@\x01\xc1\xe0mY\x11\xc6\xe7\xd5J\x81t\xf3\x9b\t\x0c\xb6'
    b'\x1cr\x16u\xe0\x9e\xc2i\xb45Xsn\xa9r\xcc\xd9$r\xbb\x81\xf5o'
    b'\xc3\x0c\x96Ph%\xdb\x89.\xf7\x03\x92\xb5\x13\xaa\xc1\xce>mb'
    b'\x98\xce!\x7f\xc0\x10\xe9\xaf\x1f\xcb!\x12\xe2L\xf7\xe1\x92'
    b'\xfb\x8b\x8c\xeb\xbeh\x81#\xe0\xd8\x08D\x82\xda\xd3\xe9D\xf5'
    b'\xcbK\x11\x0c\xc7\n\xf8\xbfG\x8f.:\x8a\xd1\x1d\x03/\xe7\xc4pf'
    b'\xbe\x80\xe8\xa5\xd3ik\x90\xf0,'
    b'<@\xbee\xefDt\x8bf\xb3\xbb\n\x8e\x08\x0b\x10\xe3:['
    b'\x08%?M\xa9$\xbeK\xc3\x01\xa1\xab\xad=\xdb\x8a%qO\xc3\xa2'
    b')\x110\x87\x0e\x00\x98 '
    b'DQpYdm\x0f\x84\xac\x9ft\xdb\xear\xd1\xb0py\xafe\xcf\x89aX\x05'
    b'\xc9\xef&:e.k\xe7\xdaZ\xda\xca\x84\xde\xf3}\r\xcf\xe6C)9\x13'
    b'\xe6\xfb\xdb5\\x\x0f\x83\xc4]^vb%Z%C\xfdG\xa7\x17\xca0\x12\xa6'
    b'\xabd{zQ\xf3\xe2\xe8\x92\xec\x88)A/\xc3tD\xe9,'
    b'oH\x90N\xde\xef\xb2 '
    b'\xe7\xc6\xcb\xcd\xd9\xdf\x1d\xc1L\xd7\xaa\x1c;-\xa5\xc6m\xd8#s'
    b'\x9dg|\xc6\xd1v\x9f\xcaNDRj\xb2\xdcJ\x86\xd3j\xb6u\xbd\xb83'
    b'\xfbt\x0f(\xe5,\xd8\xed\xc6\xd4ZO\xba\x07\x1f\xf1\x14['
    b'\xf3cZ]\xfd\xe2D\\\x19t\x01M\xe3\xf8\x9b\xc3\xf3\x19=T\xfa3'
    b'\x9cN\xdf\xc2+\x1d\x80\xdf4\xfcl9\xecD8\x11\x9d\x0b\x92}t\xd4'
    b'\xc3\r\x04\xadM^\xe0\x11\x12\xd9x '
    b'rd\x17\xc34<\x89\xaf\x96\xb4\xeaa*\xaeO\x95\x04o\x18P\x02t\x1a'
    b'\x9e\xc4\xcb@\x9bp:\xed\xc2\xc5J\tD\xa0\xb2\xfe\xb6\x0f\x86['
    b'\xa4\x13\xf1$v\xd4\xb4\xf5\xc1DB\x16\x8b\xe1\x18\xean\x08W'
    b'\x827\xf5[\x1cS\xf1$\x0e\xc8p"\x9e\xc4\x01\x19\xfa\xd3P\x87r'
    b'%\xd8|\x14\xff\x92)8\xa2\x1a\x1bf\xa8\x00\xee\xd7\x90E\r\xb6C'
    b'\x99\xdd9\x00\xb4\x9b\xa6\xfc\xd5\t\x92\x14\xb5\xdf\x12"P\x97'
    b'%\t\xdd\x11Df\xd8\xb0\xa9q\xaa\x14\x80hu\xd60\xfaE\xa6\xd6\xd6'
    b'\xd6\xdb+\xdc\x9dp\xd4i\xdb\xc4\x9f6\x1b\xfe;de\x93\n)b\x9d'
    b'=\x99\x9f\x91_ \x84 '
    b'd"\x02I\xbe\xa8l\x95\xbe\x9bq\xea\xf2\xd88\x14<\x00\'\xd7\xc3'
    b'!\\.\x7f\xe2\x87\x1db\te\xbaw\x80\xea;G\x15\x0ca\xc5\n\xf3]Mu'
    b'\xf2F\xdfA\xaaH.5\xd9q\xcc\x1f\xd1\x98v3\xf4]\xd2\x97\xe7\xec5'
    b'\xb6L\xb6n\xca\xa6Q}\xe7;^d\xfd\x10\xf0\xa5\xf1\xcf?;U\xbbQ'
    b'\xdfV\xbc\x99\x06\x18\xcd\x7f\xb6\xae\xa0Ho\xe8\x8b\xd2l)\xf9k'
    b'\x93\x03\xdeM\xaeIY\x1d\x1a#\xde\xde\xe1\xda~\x8c\x8b\x03%\x1c'
    b'\xc7,\x94\x15\xc62Pa\xa9N(\x9a\xc8@\x18\xf4\x17\xab\x13\xcb['
    b'\xf8\x80\x02\x8e\x93\xca\x90ba\xd9w?\xca\xf7\xea\x1e\r\x0b_'
    b'\xb2\xff\xeac\x12\xa7\xe1\xe7oE|\xc3}8\x9a\xd3p\x83\xb7\xc3Kz'
    b'\xc8\xd5\xa9\x84\xa3:p\x12\xa9\x92\xaeA\xbbc\x8a\x0f\xb6/m'
    b'\xadN\xa6\xfe\xa2\x0b\xbf\xd2\x14\xcdI%\x825\xc1\xf6fWY\x8a'
    b'\xff\x8e\xeb\xdc\x7f\xa9\x1foeO\xc7d2U4-\xf0\x01\xc3\x0fw\xfb'
    b'\xa4:t\xbb\x889\x90\xb5\xf7\x82#oS\x8c\x0f\xc0J7\x81N\xb8Y'
    b'\xfd(\xb9\n\x96\x9e\xbe\xa0\xad\x8b\x047\x8a\xd9\x03\xf9<\x152'
    b'\xf5uZ\xd4-\xd0\x05\x7f\x15b\rS\x89\xf07\xe2\x9e\x9b4\xf8>kn'
    b'\xb7\x07\xd0\x9a\x04?z\xcf!1\x94U\xc3\xa9u\xd2\x940\x06h\xb5'
    b'\xf3\x83#i6`U\xdf9\xa1\x16\x8f\x16\x05\xd0\x94\x03`\x06\xa7L'
    b'\xab[^\x94\x18M\x17\x1c\xeai\xca\xc3\x89G\xc8\x91\xb8\xcc\xb4F'
    b'\xa8&\xe8\xe7\x97T\xb2('
    b'*it?\x10\x9e\xb4H\xec1\xe6\x10p-D\xe0\\\x08\xcb\xfd\x81&\x92'
    b']\xcb\xc0\xb3\xbf\x17Z|\\\x1a\xc9 '
    b'\x98\xe1\xc4*\x04\x98\xec9\xea\x95aD\x16\x0c\xb3\x869n7\\\xde'
    b'>\\\xe7zC\xc3\xcd\xa8\xf4\xc3H\x19~\xecC\xca\\{'
    b'\xee\x1e\x1f\x16\xf7:\xc7\x89n\xc5J\xafK\xb2\xf8h\xc5\xd0\x18a'
    b'\n\x11\\\xe2{\xcd\x8d\x85\xa6h\xbd]*\xb2\x05-\xea\xd5\xd1m=J7'
    b'\x88n\xe3\xda<\xca\xde\xe58 '
    b'.\xd5I#^\xbd\xcd\x10j\xd3\xe3\xd6\x1d\xd1{'
    b'|~\xe3\xa8\xaf\xcfY\x03\xceo\x99\x1b\xd8\xae%\xe3t\xad:\xe7F'
    b'\xe1\xba<W\x8c\x00XM!\xb5\xef\t\xe7\xbd\x97\x02\xecf\xef\x04qw'
    b'\xcb\xabE\xf0\xb7\xda\xfc\xf8/\xfd\x88\x03\xad\xb6Mx\xf3\x93'
    b'\xf3&\x8c\x8b\x83@h<\xd6WnV\xe3\xbf\xe5\xf2}J\xb9\\\xf6\x11'
    b'\xa5\xc7(<>\xbf\xd5\xe0=\xcc[\xb0\xc8\xae\xb6\xc5\x98 '
    b'\xfa\xb7\xbbF\x9b\xf2\x02{H\xcd\xe9\xe3|>\x0fn\xf1{'
    b'\x05?\xde\xf1\xcd\x86\x9b\x98\xe6nyy\x9e<\x906\x1f\xb1['
    b')&\xcd\xd2\x89\x8a\xff\x91\xe0\xfa,'
    b'a\x7f;\x1e\xe2\x1d\xb7\xfe\x0e\rb\xdeNO\xcf\xb9\x82{'
    b'\x8a\xe4\xc0<\xde\xe2\x8ax\x7f\xeb\xa7\x8f\xe7\x02\x06\x8a'
    b'\xb3O\x15\xe3\xf2\xf4H,'
    b'C\x17\xe5\x83\xe7B\x84\xb2N\x185\xc3\xb3\x1av\xf0+b\x9f\x04b'
    b'\x16\xd8\x9d\x02\xba\xc5\xe72X\xa7I\xf3\x87\x7f\xc7\xc8\xb2W'
    b'\xb5I|.);\xa9\x08V\xf1\xbb\x0bO$\xdd\xe2\x9b\xc74\xca\xde\x8d'
    b'\xd2\x0f\xce\xc1\x9ayU\x9f(^!\x8c\xf1_1Y?\x95~\xd2 '
    b'\xb3\xcc\xb2\x9e\xdbd\x1e\x9d\x8b\xddnj\xb2\xdf\x1ew\xe1\xe1l'
    b'&\xcd\xd0\r\xcf\xebu~eR\x9cT\x82\xc1h.u\x0crv8\x95`\xebC\xf1'
    b'\xa9\x90\x96\x9b\xec\x9dR\xda\xd10"\xaf\x1dh{'
    b'\xcb\xcai\x0f\x08\x96\xbd9\xcd\xceJW\xf11:\xe7"\x8dH\xddp\xd3'
    b'\x13e\n8YgY\xa8\xd4\xf5\xc8*\x03\xe0W\x0f\x10@\xc6E\xde&\xc9'
    b')\x02\xb9\x84\xb9\xa9J\xf8\xd5\x8d2\x14u\n\xd9A5\xa6\xe9F\xb9'
    b'}t\xc9\x00\xbf\x9f\xc7\xac8k"?\xceSY\x01\x8f\xee\x7f\xcb\xed'
    b'\xea\xc2+\xb1_\xcf\xecO\xfdx\xec\xbb\xb0\x9c\xfc\x93\xe1\xf9'
    b'"\xca\xd6\x85\x94\xc4\xea\x85\xcc!\x03f.F,'
    b'fCV\xbc\xedK\xb10+\x00E^\xde@\x0c\xed\xc7=j\xa4f\xa7\xf9\xbc'
    b'\xfe\xa9\xb8g\x08\xbd\xafS|\xecs\xcdt\x86\xf2Dm\xae\xedmF\x16'
    b'\x8b\xdf\xc5\xd4\x07A\xf5z\xadL\xec\x00\nk\xed\x91\xe1\xafo'
    b'\x82Li\xbd\x93\xb9\xb3\xcc%\x18MF<N%\xe6\xe5\xf9\xef\xcc\x93'
    b"\x9f]+\xed\xbc\x8c\xd1\xc2\xe9\xd2\xd7'\x18\x93\x87X\x0e\xdd"
    b'=\xc9\x95o\xdfu\xc1\x8f\x0b}m\xb3t\na\xee\x14\x02\xbe\x00\t'
    b'\xb7\x19\xc7\xde\xd9\xcd\xcfEA\xcfv\xeeC\x00z\x1bk\x1a\xdd\x8a'
    b'\x13\xc5\x078:\xe9\x0cVl\xb5\xd4\xa8\xcb\xae\xa8\xc6=\x85\xc3'
    b'\xeb\x92[\x128\x85\x15E\x8e\x1a2\xfc\xce4U\x8b^U\xce\xd0\x8cYf'
    b'\n\xf4u&\xdd^\x06\x12\xc4^\xfe\r\xc1\xf4GW\xffvj\xbb<\x9c'
    b'\xc1Eb\x1b*,TJ\xfb\xa6\xc5V\x9c\xae@\x0f\xb3['
    b'n+b\xa4\xf0\x1a]n\x1c\xccR\x0b.\xf3\xa5TH\xd1K\xffl\xc3\xaa3'
    b'\xc4L\xac\xb0X)h7\x9e\xc4y\xe0\xb7\xb4\xe2\x8a\xab\xd6\xd4\xf5'
    b'\x9ey\xb3%R\xf3\xd4)J\xae\x00\xf9cgM\x17\x0c\xcdkQ\xd2\xa7.A'
    b'\xed\xbd\xab\x03\x807;\x97\xed\xff\xc6N\xda\xc8/\xa3\xc5A\x99'
    b'\x8b\xa1.+\xa6\xd6\xfc\x1c\xe8r\x16\x95\xe7\x174\x1f\xd5\x9d'
    b'\x1agm\x073\x87L\x1e\xaeP\xc8\xb0\x96\xb5\x02$|^.2n\x05\x83'
    b'\x15@\xe1\x85\xcf\x8fU\xea.u\xf8h`\x9fZ\xe23\xb7H\xf0\x1c\xf9'
    b'\xea\x88\x03*B\xf4\xb9\x19\xa2.\x9b\x82Q\xc7\x9aR\xb4\xf2'
    b'\xcd8r\x13\x1fkNr%\xb5\xc0J3bX\x1d\x01\xfeN\x99v\x82\xd1K4\xdc'
    b'\xd2\x9a\xbac\x85\xb7\x19\xda\x0c\x82@\xf0,'
    b'\x8b+`vLyxDD\xe1\x14\x86\xd5E\nY\xa4\xc4\xa4\xf3sn\x0b:\xfe^Sz'
    b'\xd8\x95r\x86ax\x10\xfe\xd1\x07`\xb5\xdb\xaf\xef\x9bW\x07\xdc'
    b'\x99\xae\xfc\xb7\xc3M\xe5/['
    b'^\x0eG\x1b\x9d/\xbe\xf8\xe2\x8b/\xbe\xf8\xe2\x8b/\xbe\xf8\xa2'
    b'\x01\xff\x00)\x1f\xa5\xd7^b1\xac\x00\x00\x00\x00IEND\xaeB`\x82'
)


def test_upload_image(client):
    filename = 'tests/files/falcon.png'
    file64 = base64.b64encode(IMAGE_FILE)

    resp = client.simulate_post('/image', files={'image': (filename, IMAGE_FILE)})

    assert resp.status_code == 200
    assert resp.json == [
        {
            'content_type': 'text/plain',
            'data': file64.decode(),
            'filename': filename,
            'name': 'image',
            'secure_filename': filename.replace('/', '_'),
        }
    ]


def test_upload_fileobj(client):
    fileobj = io.BytesIO(IMAGE_FILE)
    fileobj.name = '/tests/img_readable'

    resp = client.simulate_post('/image', files={'image': fileobj})

    assert resp.status_code == 200
    assert resp.json == [
        {
            'content_type': 'text/plain',
            'data': base64.b64encode(IMAGE_FILE).decode(),
            'filename': 'img_readable',
            'name': 'image',
            'secure_filename': 'img_readable',
        }
    ]
