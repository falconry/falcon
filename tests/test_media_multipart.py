import io
import itertools
import os
import random

import pytest

import falcon
from falcon import media
from falcon import testing
from falcon.util import BufferedReader

from _util import create_app  # NOQA: I100


try:
    import msgpack  # type: ignore
except ImportError:
    msgpack = None


EXAMPLE1 = (
    b'--5b11af82ab65407ba8cdccf37d2a9c4f\r\n'
    b'Content-Disposition: form-data; name="hello"\r\n\r\n'
    b'world\r\n'
    b'--5b11af82ab65407ba8cdccf37d2a9c4f\r\n'
    b'Content-Disposition: form-data; name="document"\r\n'
    b'Content-Type: application/json\r\n\r\n'
    b'{"debug": true, "message": "Hello, world!", "score": 7}\r\n'
    b'--5b11af82ab65407ba8cdccf37d2a9c4f\r\n'
    b'Content-Disposition: form-data; name="file1"; filename="test.txt"\r\n'
    b'Content-Type: text/plain\r\n\r\n'
    b'Hello, world!\n\r\n'
    b'--5b11af82ab65407ba8cdccf37d2a9c4f--\r\n')

EXAMPLE2 = (
    b'-----------------------------1574247108204320607285918568\r\n'
    b'Content-Disposition: form-data; name="description"\r\n\r\n'
    b'\r\n'
    b'-----------------------------1574247108204320607285918568\r\n'
    b'Content-Disposition: form-data; name="moderation"\r\n\r\n'
    b'approved\r\n'
    b'-----------------------------1574247108204320607285918568\r\n'
    b'Content-Disposition: form-data; name="title"\r\n\r\n'
    b'A simple text file example.\r\n'
    b'-----------------------------1574247108204320607285918568\r\n'
    b'Content-Disposition: form-data; name="uploadid"\r\n\r\n'
    b'00l33t0174873295\r\n'
    b'-----------------------------1574247108204320607285918568\r\n'
    b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
    b'Content-Type: text/plain\r\n\r\n'
    b'Hello, world!\n'
    b'\r\n'
    b'-----------------------------1574247108204320607285918568--\r\n'
)
EXAMPLE2_PART_COUNT = 5

EXAMPLE3 = (
    b'--BOUNDARY\r\n'
    b'Content-Disposition: form-data; name="file"; filename="bytes"\r\n'
    b'Content-Type: application/x-falcon\r\n\r\n' +
    b'123456789abcdef\n' * 64 * 1024 * 2 +
    b'\r\n'
    b'--BOUNDARY\r\n'
    b'Content-Disposition: form-data; name="empty"\r\n'
    b'Content-Type: text/plain\r\n\r\n'
    b'\r\n'
    b'--BOUNDARY--\r\n'
)

LOREM_IPSUM = (
    'Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod '
    'tempor incididunt ut labore et dolore magna aliqua. Dolor sed viverra '
    'ipsum nunc aliquet bibendum enim. In massa tempor nec feugiat. Nunc '
    'aliquet bibendum enim facilisis gravida. Nisl nunc mi ipsum faucibus '
    'vitae aliquet nec ullamcorper. Amet luctus venenatis lectus magna '
    'fringilla. Volutpat maecenas volutpat blandit aliquam etiam erat velit '
    'scelerisque in. Egestas egestas fringilla phasellus faucibus scelerisque '
    'eleifend. Sagittis orci a scelerisque purus semper eget duis. Nulla '
    'pharetra diam sit amet nisl suscipit. Sed adipiscing diam donec '
    'adipiscing tristique risus nec feugiat in. Fusce ut placerat orci nulla. '
    'Pharetra vel turpis nunc eget lorem dolor. Tristique senectus et netus '
    'et malesuada.\n'
).encode()

EXAMPLE4 = (
    b'--boundary\r\n'
    b'Content-Disposition: form-data; name="lorem1"; filename="bytes1"\r\n'
    b'Content-Type: text/plain\r\n\r\n' +
    LOREM_IPSUM +
    b'\r\n'
    b'--boundary\r\n'
    b'Content-Disposition: form-data; name="empty"\r\n'
    b'Content-Type: text/plain\r\n\r\n'
    b'\r\n'
    b'--boundary\r\n'
    b'Content-Disposition: form-data; name="lorem2"; filename="bytes1"\r\n'
    b'Content-Type: text/plain\r\n\r\n' +
    LOREM_IPSUM +
    b'\r\n'
    b'--boundary--\r\n'
)


EXAMPLES = {
    '5b11af82ab65407ba8cdccf37d2a9c4f': EXAMPLE1,
    '---------------------------1574247108204320607285918568': EXAMPLE2,
    'BOUNDARY': EXAMPLE3,
    'boundary': EXAMPLE4,
}


# APPSEC: This SHA256 hash is safe against preimage attacks.
HASH_BOUNDARY = (
    'fbeff51e0f5630958701f4941aec5595addcb3ee1b70468c8bd4be920304c184')


@pytest.mark.parametrize('boundary', list(EXAMPLES))
def test_parse(boundary):
    handler = media.MultipartFormHandler()
    example = EXAMPLES[boundary]
    form = handler.deserialize(
        io.BytesIO(example),
        'multipart/form-data; boundary=' + boundary,
        len(example))

    for part in form:
        output = io.BytesIO()
        part.stream.pipe(output)
        assert isinstance(output.getvalue(), bytes)


@pytest.mark.parametrize('buffer_size,chunk_size', list(itertools.product(
    (
        32,
        64,
        128,
        256,
    ),
    (
        7,
        8,
        9,
        10,
        32,
        64,
        128,
        256,
    ),
)))
def test_parsing_correctness(buffer_size, chunk_size):
    example = EXAMPLES['boundary']
    handler = media.MultipartFormHandler()
    stream = BufferedReader(io.BytesIO(example).read, len(example),
                            buffer_size)
    form = handler.deserialize(
        stream, 'multipart/form-data; boundary=boundary', len(example))

    for part in form:
        if part.name in ('lorem1', 'lorem2'):
            part_stream = part.stream
            result = []
            while True:
                chunk = part_stream.read(chunk_size)
                if not chunk:
                    break
                result.append(chunk)

            assert b''.join(result) == LOREM_IPSUM


def test_missing_boundary():
    handler = media.MultipartFormHandler()

    with pytest.raises(falcon.HTTPInvalidHeader):
        handler.deserialize(io.BytesIO(), 'multipart/form-data', 0)

    with pytest.raises(falcon.HTTPInvalidHeader):
        handler.deserialize(io.BytesIO(), 'multipart/form-data; boundary=', 0)

    overlong = '-' * 71
    content_type = 'multipart/form-data; boundary=' + overlong
    with pytest.raises(falcon.HTTPInvalidHeader):
        handler.deserialize(io.BytesIO(), content_type, 0)


def test_empty_input():
    handler = media.MultipartFormHandler()
    form = handler.deserialize(
        io.BytesIO(), 'multipart/form-data; boundary=404', 0)
    with pytest.raises(falcon.MediaMalformedError):
        for part in form:
            pass


def test_serialize():
    handler = media.MultipartFormHandler()
    with pytest.raises(NotImplementedError):
        handler.serialize({'key': 'value'}, 'multipart/form-data')


@pytest.mark.parametrize('charset,data', [
    ('utf-8', b'Impossible byte: \xff'),
    ('utf-8', b'Overlong... \xfc\x83\xbf\xbf\xbf\xbf ... sequence'),
    ('ascii', b'\x80\x80\x80'),
    ('pecyn', b'AAHEHlRoZSBGYWxjb24gV2ViIEZyYW1ld29yaywgMjAxOQ=='),
])
def test_invalid_text_or_charset(charset, data):
    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="text"\r\n'
        b'Content-Type: text/plain; ' +
        'charset={}\r\n\r\n'.format(charset).encode() +
        data +
        b'\r\n'
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="empty"\r\n'
        b'Content-Type: text/plain\r\n\r\n'
        b'\r\n'
        b'--BOUNDARY--\r\n'
    )

    handler = media.MultipartFormHandler()

    form = handler.deserialize(
        io.BytesIO(data), 'multipart/form-data; boundary=BOUNDARY', len(data))
    with pytest.raises(falcon.MediaMalformedError):
        for part in form:
            part.text


def test_unknown_header():
    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="empty"\r\n'
        b'Content-Coolness: fair\r\n'
        b'Content-Type: text/plain\r\n\r\n'
        b'\r\n'
        b'--BOUNDARY--\r\n'
    )

    handler = media.MultipartFormHandler()
    form = handler.deserialize(
        io.BytesIO(data), 'multipart/form-data; boundary=BOUNDARY', len(data))

    for part in form:
        assert part.data == b''


def test_from_buffered_stream():
    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="empty"\r\n'
        b'Content-Coolness: fair\r\n'
        b'Content-Type: text/plain\r\n\r\n'
        b'\r\n'
        b'--BOUNDARY--\r\n'
    )

    handler = media.MultipartFormHandler()
    stream = BufferedReader(io.BytesIO(data).read, len(data))
    form = handler.deserialize(
        stream, 'multipart/form-data; boundary=BOUNDARY', len(data))

    for part in form:
        assert part.data == b''


def test_body_part_media():
    handler = media.MultipartFormHandler()

    content_type = ('multipart/form-data; boundary=' +
                    '5b11af82ab65407ba8cdccf37d2a9c4f')
    form = handler.deserialize(
        io.BytesIO(EXAMPLE1), content_type, len(EXAMPLE1))

    expected = {'debug': True, 'message': 'Hello, world!', 'score': 7}

    for part in form:
        if part.content_type == 'application/json':
            assert part.media == part.media == expected


def test_body_part_properties():
    handler = media.MultipartFormHandler()

    content_type = ('multipart/form-data; boundary=' +
                    '5b11af82ab65407ba8cdccf37d2a9c4f')
    form = handler.deserialize(
        io.BytesIO(EXAMPLE1), content_type, len(EXAMPLE1))

    for part in form:
        if part.content_type == 'application/json':
            assert part.name == part.name == 'document'
        elif part.name == 'file1':
            assert part.filename == part.filename == 'test.txt'
            assert part.secure_filename == part.filename


def test_empty_filename():
    data = (
        b'--a0d738bcdb30449eb0d13f4b72c2897e\r\n'
        b'Content-Disposition: form-data; name="file"; filename=\r\n\r\n'
        b'An empty filename.\r\n'
        b'--a0d738bcdb30449eb0d13f4b72c2897e--\r\n'
    )

    handler = media.MultipartFormHandler()
    content_type = ('multipart/form-data; boundary=' +
                    'a0d738bcdb30449eb0d13f4b72c2897e')
    stream = BufferedReader(io.BytesIO(data).read, len(data))
    form = handler.deserialize(stream, content_type, len(data))

    for part in form:
        assert part.filename == ''
        with pytest.raises(falcon.MediaMalformedError):
            part.secure_filename


@falcon.runs_sync
async def test_async_unsupported():
    if falcon.ASGI_SUPPORTED:
        pytest.skip('Testing missing ASGI support')

    handler = media.MultipartFormHandler()
    with pytest.raises(NotImplementedError):
        await handler.deserialize_async(
            'Dummy', 'multipart/form-data; boundary=BOUNDARY', None)


class MultipartAnalyzer:
    def on_post(self, req, resp):
        values = []
        for part in req.media:
            values.append({
                'content_type': part.content_type,
                'data': part.data.decode(),
                'filename': part.filename,
                'name': part.name,
                'secure_filename': part.secure_filename if part.filename else None,
                'text': part.text,
            })

        resp.media = values

    def on_post_media(self, req, resp):
        deserialized = []
        for part in req.media:
            part_media = part.get_media()
            assert part_media == part.media
            deserialized.append(part_media)

        resp.media = deserialized

    def on_post_mirror(self, req, resp):
        parts = []
        for part in req.get_media():
            parts.append({
                'content': part.stream.read(),
                'content_type': part.content_type,
                'name': part.name,
            })

        resp.content_type = falcon.MEDIA_MSGPACK
        resp.media = parts


class AsyncMultipartAnalyzer:
    async def on_post(self, req, resp):
        values = []
        form = await req.get_media()
        async for part in form:
            # NOTE(vytas): use the async property form to exercise that too.
            values.append({
                'content_type': part.content_type,
                'data': (await part.data).decode(),
                'filename': part.filename,
                'name': part.name,
                'secure_filename': part.secure_filename if part.filename else None,
                'text': (await part.text),
            })

        resp.media = values

    async def on_post_media(self, req, resp):
        deserialized = []
        form = await req.media
        async for part in form:
            part_media = await part.get_media()
            assert part_media == await part.media
            deserialized.append(part_media)

        resp.media = deserialized

    async def on_post_mirror(self, req, resp):
        parts = []
        async for part in await req.get_media():
            parts.append({
                'content': await part.stream.read(),
                'content_type': part.content_type,
                'name': part.name,
            })

        resp.content_type = falcon.MEDIA_MSGPACK
        resp.media = parts


@pytest.fixture
def custom_client(asgi):
    def _factory(options):
        multipart_handler = media.MultipartFormHandler()
        for key, value in options.items():
            setattr(multipart_handler.parse_options, key, value)
        req_handlers = media.Handlers({
            falcon.MEDIA_JSON: media.JSONHandler(),
            falcon.MEDIA_MULTIPART: multipart_handler,
        })

        app = create_app(asgi)
        app.req_options.media_handlers = req_handlers
        app.resp_options.media_handlers = media.Handlers({
            falcon.MEDIA_JSON: media.JSONHandler(),
            falcon.MEDIA_MSGPACK: media.MessagePackHandler(),
        })

        resource = AsyncMultipartAnalyzer() if asgi else MultipartAnalyzer()
        app.add_route('/submit', resource)
        app.add_route('/media', resource, suffix='media')
        app.add_route('/mirror', resource, suffix='mirror')

        return testing.TestClient(app)

    return _factory


@pytest.fixture
def client(custom_client):
    return custom_client({})


def test_upload_multipart(client):
    resp = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=5b11af82ab65407ba8cdccf37d2a9c4f',
        },
        body=EXAMPLE1)

    assert resp.status_code == 200
    assert resp.json == [
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
            'data': 'Hello, world!\n',
            'filename': 'test.txt',
            'name': 'file1',
            'secure_filename': 'test.txt',
            'text': 'Hello, world!\n',
        },
    ]


@pytest.mark.parametrize('truncated_by', [1, 2, 3, 4])
def test_truncated_form(client, truncated_by):
    resp = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=5b11af82ab65407ba8cdccf37d2a9c4f',
        },
        body=EXAMPLE1[:-truncated_by])

    assert resp.status_code == 400
    assert resp.json == {
        'description': 'unexpected form structure',
        'title': 'Malformed multipart/form-data request media',
    }


def test_unexected_form_structure(client):
    resp1 = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=5b11af82ab65407ba8cdccf37d2a9c4f',
        },
        body=EXAMPLE1[:-2] + b'--\r\n')

    assert resp1.status_code == 400
    assert resp1.json == {
        'description': 'unexpected form structure',
        'title': 'Malformed multipart/form-data request media',
    }

    resp2 = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=5b11af82ab65407ba8cdccf37d2a9c4f',
        },
        body=EXAMPLE1[:-4] + b'**\r\n')

    assert resp2.status_code == 400
    assert resp2.json == {
        'description': 'unexpected form structure',
        'title': 'Malformed multipart/form-data request media',
    }


def test_data_too_large(client):
    resp = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=BOUNDARY',
        },
        body=EXAMPLE3)

    assert resp.status_code == 400
    assert resp.json == {
        'description': 'body part is too large',
        'title': 'Malformed multipart/form-data request media',
    }


@pytest.mark.parametrize('max_body_part_count', list(range(7)) + [100, 1000])
def test_too_many_body_parts(custom_client, max_body_part_count):
    client = custom_client({'max_body_part_count': max_body_part_count})
    boundary = '---------------------------1574247108204320607285918568'
    resp = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=' + boundary,
        },
        body=EXAMPLE2)

    if 0 < max_body_part_count < EXAMPLE2_PART_COUNT:
        assert resp.status_code == 400
        assert resp.json == {
            'description': 'maximum number of form body parts exceeded',
            'title': 'Malformed multipart/form-data request media',
        }
    else:
        assert resp.status_code == 200
        assert len(resp.json) == EXAMPLE2_PART_COUNT


@pytest.mark.skipif(not msgpack, reason='msgpack not installed')
def test_random_form(client):
    part_data = [os.urandom(random.randint(0, 2**18)) for _ in range(64)]
    form_data = b''.join(
        '--{}\r\n'.format(HASH_BOUNDARY).encode() +
        'Content-Disposition: form-data; name="p{}"\r\n'.format(i).encode() +
        b'Content-Type: application/x-falcon-urandom\r\n\r\n' +
        part_data[i] +
        b'\r\n'
        for i in range(64)
    ) + '--{}--\r\n'.format(HASH_BOUNDARY).encode()

    handler = media.MultipartFormHandler()
    content_type = ('multipart/form-data; boundary=' + HASH_BOUNDARY)
    form = handler.deserialize(
        io.BytesIO(form_data), content_type, len(form_data))

    resp = client.simulate_post(
        '/mirror', headers={'Content-Type': content_type}, body=form_data)
    assert resp.status_code == 200
    form = msgpack.unpackb(resp.content, raw=False)

    for index, part in enumerate(form):
        assert part['content'] == part_data[index]
        assert part['content_type'] == 'application/x-falcon-urandom'


def test_invalid_random_form(client):
    length = random.randint(2**20, 2**21)
    resp = client.simulate_post(
        '/submit',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=' + HASH_BOUNDARY,
        },
        body=os.urandom(length))

    assert resp.status_code == 400


def test_nested_multipart_mixed():
    class Forms:
        def on_post(self, req, resp):
            example = {}
            for part in req.media:
                if part.content_type.startswith('multipart/mixed'):
                    for nested in part.media:
                        example[nested.filename] = nested.text

            resp.media = example

    parser = media.MultipartFormHandler()
    parser.parse_options.media_handlers['multipart/mixed'] = (
        media.MultipartFormHandler())

    app = falcon.App()
    app.req_options.media_handlers[falcon.MEDIA_MULTIPART] = parser
    app.add_route('/forms', Forms())
    client = testing.TestClient(app)

    form_data = (
        b'--AaB03x\r\n'
        b'Content-Disposition: form-data; name="field1"\r\n\r\n'
        b'Joe Blow\r\n'
        b'--AaB03x\r\n'
        b'Content-Disposition: form-data; name="docs"\r\n'
        b'Content-Type: multipart/mixed; boundary=BbC04y\r\n\r\n'
        b'--BbC04y\r\n'
        b'Content-Disposition: attachment; filename="file1.txt"\r\n\r\n'
        b'This is file1.\r\n\r\n'
        b'--BbC04y\r\n'
        b'Content-Disposition: attachment; filename="file2.txt"\r\n'
        b'Content-Transfer-Encoding: binary\r\n\r\n'
        b'Hello, World!\r\n\r\n'
        b'--BbC04y--\r\n\r\n'
        b'--AaB03x--\r\n'
    )
    resp = client.simulate_post(
        '/forms',
        headers={'Content-Type': 'multipart/form-data; boundary=AaB03x'},
        body=form_data,
    )
    assert resp.status_code == 200
    assert resp.json == {
        'file1.txt': 'This is file1.\r\n',
        'file2.txt': 'Hello, World!\r\n',
    }


def test_content_transfer_encoding_header(client):
    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="file"; filename="bytes"\r\n'
        b'Content-Transfer-Encoding: Base64'
        b'Content-Type: application/x-falcon\r\n\r\n'
        b'UGVyZWdyaW5lIEZhbGNvbiADLgA='
        b'\r\n'
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="empty"\r\n'
        b'Content-Type: text/plain\r\n\r\n'
        b'\r\n'
        b'--BOUNDARY--\r\n'
    )

    resp = client.simulate_post(
        '/submit',
        headers={'Content-Type': 'multipart/form-data; boundary=BOUNDARY'},
        body=data)

    assert resp.status_code == 400
    assert resp.json == {
        'description': ('the deprecated Content-Transfer-Encoding header '
                        'field is unsupported'),
        'title': 'Malformed multipart/form-data request media',
    }


def test_unsupported_charset(client):
    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="text"\r\n'
        b'Content-Type: text/plain; charset=pecyn\r\n\r\n'
        b'AAHEHlRoZSBGYWxjb24gV2ViIEZyYW1ld29yaywgMjAxOQ=='
        b'\r\n'
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="empty"\r\n'
        b'Content-Type: text/plain\r\n\r\n'
        b'\r\n'
        b'--BOUNDARY--\r\n'
    )

    resp = client.simulate_post(
        '/submit',
        headers={'Content-Type': 'multipart/form-data; boundary=BOUNDARY'},
        body=data)

    assert resp.status_code == 400
    assert resp.json == {
        'description': 'invalid text or charset: pecyn',
        'title': 'Malformed multipart/form-data request media',
    }


def test_filename_star(client):
    # NOTE(vytas): Generated by requests_toolbelt 0.9.1 on Py2
    #   (interestingly, one gets a "normal" filename on Py3.7).

    data = (
        b'--a0d738bcdb30449eb0d13f4b72c2897e\r\n'
        b'Content-Disposition: form-data; name="file"; '
        b"filename*=utf-8''%E2%AC%85%20Arrow.txt\r\n\r\n"
        b'A unicode arrow in the filename.\r\n'
        b'--a0d738bcdb30449eb0d13f4b72c2897e--\r\n'
    )
    content_type = ('multipart/form-data; boundary=' +
                    'a0d738bcdb30449eb0d13f4b72c2897e')

    resp = client.simulate_post(
        '/submit', headers={'Content-Type': content_type}, body=data)
    assert resp.status_code == 200
    assert resp.json == [{
        'content_type': 'text/plain',
        'data': 'A unicode arrow in the filename.',
        'filename': '⬅ Arrow.txt',
        'name': 'file',
        'secure_filename': '__Arrow.txt',
        'text': 'A unicode arrow in the filename.',
    }]

    data = data.replace(b'*=utf-8', b'*=esoteric')
    resp = client.simulate_post(
        '/submit', headers={'Content-Type': content_type}, body=data)
    assert resp.status_code == 400
    assert resp.json == {
        'description': 'invalid text or charset: esoteric',
        'title': 'Malformed multipart/form-data request media',
    }


@pytest.mark.parametrize('max_headers_size', [64, 140, 141, 142, 256, 1024])
def test_headers_edge_cases(custom_client, max_headers_size):
    client = custom_client({'max_body_part_headers_size': max_headers_size})

    data = (
        b'--a0d738bcdb30449eb0d13f4b72c2897e\r\n'
        b'X-Falcon: Peregrine\r\n'
        b'Content-Type: application/vnd.oasis.opendocument.text\r\n'
        b'Junk\r\n'
        b'Content-Disposition: form-data; name="file"; filename=hd.txt\r\n\r\n'
        b'No, it is not an ODT document...\r\n'
        b'--a0d738bcdb30449eb0d13f4b72c2897e--\r\n'
    )
    content_type = ('multipart/form-data; boundary=' +
                    'a0d738bcdb30449eb0d13f4b72c2897e')

    resp = client.simulate_post(
        '/submit', headers={'Content-Type': content_type}, body=data)

    if max_headers_size < 142:
        assert resp.status_code == 400
        assert resp.json == {
            'description': 'incomplete body part headers',
            'title': 'Malformed multipart/form-data request media',
        }
    else:
        assert len(resp.json) == 1


def test_deserialize_part_media(client):
    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="factorials"\r\n'
        b'Content-Type: application/json\r\n\r\n'
        b'{"count": 6, "numbers": [1, 2, 6, 24, 120, 720]}\r\n'
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="person"\r\n'
        b'Content-Type: application/x-www-form-urlencoded\r\n\r\n'
        b'name=Jane&surname=Doe&fruit=%F0%9F%8D%8F\r\n'
        b'--BOUNDARY--\r\n'
    )

    resp = client.simulate_post(
        '/media',
        headers={'Content-Type': 'multipart/form-data; boundary=BOUNDARY'},
        body=data)

    assert resp.status_code == 200
    assert resp.json == [
        {'count': 6, 'numbers': [1, 2, 6, 24, 120, 720]},
        {'fruit': '🍏', 'name': 'Jane', 'surname': 'Doe'},
    ]


def test_deserialize_custom_media(custom_client):
    class FirstByteHandler(media.BaseHandler):
        exhaust_stream = True

        def deserialize(self, stream, content_type, content_length):
            first_byte = stream.read(1)
            if first_byte:
                return '0x{:02x}'.format(first_byte[0])
            return ''

        async def deserialize_async(self, stream, content_type,
                                    content_length):
            first_byte = await stream.read(1)
            if first_byte:
                return '0x{:02x}'.format(first_byte[0])
            return ''

    handlers = media.Handlers(
        {'application/x-falcon-first-byte': FirstByteHandler()})
    client = custom_client({'media_handlers': handlers})

    data = (
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="first"\r\n'
        b'Content-Type: application/x-falcon-first-byte\r\n\r\n'
        b'\r\n'
        b'--BOUNDARY\r\n'
        b'Content-Disposition: form-data; name="second"\r\n'
        b'Content-Type: application/x-falcon-first-byte\r\n\r\n'
        b'Hi!\r\n'
        b'--BOUNDARY--\r\n'
    )

    resp = client.simulate_post(
        '/media',
        headers={'Content-Type': 'multipart/form-data; boundary=BOUNDARY'},
        body=data)

    assert resp.status_code == 200
    assert resp.json == ['', '0x48']
