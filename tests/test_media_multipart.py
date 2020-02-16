import io
import itertools
import os
import random

import pytest

import falcon
from falcon import media
from falcon import testing
from falcon.util import BufferedReader


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
    with pytest.raises(falcon.HTTPBadRequest):
        for part in form:
            pass


def test_serialize():
    handler = media.MultipartFormHandler()
    with pytest.raises(NotImplementedError):
        handler.serialize({'key': 'value'}, 'multipart/form-data')


def test_content_transfer_encoding_header():
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

    handler = media.MultipartFormHandler()
    form = handler.deserialize(
        io.BytesIO(data), 'multipart/form-data; boundary=BOUNDARY', len(data))
    with pytest.raises(falcon.HTTPBadRequest):
        for part in form:
            pass


def test_unsupported_charset():
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

    handler = media.MultipartFormHandler()
    form = handler.deserialize(
        io.BytesIO(data), 'multipart/form-data; boundary=BOUNDARY', len(data))
    with pytest.raises(falcon.HTTPBadRequest):
        for part in form:
            part.text


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
    with pytest.raises(falcon.HTTPBadRequest):
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


def test_filename_star():
    # NOTE(vytas): Generated by requests_toolbelt 0.9.1 on Py2
    #   (interestingly, one gets a "normal" filename on Py3.7).

    data = (
        b'--a0d738bcdb30449eb0d13f4b72c2897e\r\n'
        b'Content-Disposition: form-data; name="file"; '
        b"filename*=utf-8''%E2%AC%85%20Arrow.txt\r\n\r\n"
        b'A unicode arrow in the filename.\r\n'
        b'--a0d738bcdb30449eb0d13f4b72c2897e--\r\n'
    )

    handler = media.MultipartFormHandler()
    content_type = ('multipart/form-data; boundary=' +
                    'a0d738bcdb30449eb0d13f4b72c2897e')
    stream = BufferedReader(io.BytesIO(data).read, len(data))
    form = handler.deserialize(stream, content_type, len(data))
    for part in form:
        assert part.filename == '⬅ Arrow.txt'
        assert part.secure_filename == '__Arrow.txt'

    data = data.replace(b'*=utf-8', b'*=esoteric')
    stream = BufferedReader(io.BytesIO(data).read, len(data))
    form = handler.deserialize(stream, content_type, len(data))
    for part in form:
        with pytest.raises(falcon.HTTPBadRequest):
            part.filename


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
        with pytest.raises(falcon.HTTPBadRequest):
            part.secure_filename


@pytest.mark.parametrize('max_headers_size', [64, 140, 141, 142, 256, 1024])
def test_headers_edge_cases(max_headers_size):
    data = (
        b'--a0d738bcdb30449eb0d13f4b72c2897e\r\n'
        b'X-Falcon: Peregrine\r\n'
        b'Content-Type: application/vnd.oasis.opendocument.text\r\n'
        b'Junk\r\n'
        b'Content-Disposition: form-data; name="file"; filename=hd.txt\r\n\r\n'
        b'No, it is not an ODT document...\r\n'
        b'--a0d738bcdb30449eb0d13f4b72c2897e--\r\n'
    )

    handler = media.MultipartFormHandler()
    handler.parse_options.max_body_part_headers_size = max_headers_size

    content_type = ('multipart/form-data; boundary=' +
                    'a0d738bcdb30449eb0d13f4b72c2897e')
    stream = BufferedReader(io.BytesIO(data).read, len(data))
    form = handler.deserialize(stream, content_type, len(data))

    if max_headers_size < 142:
        with pytest.raises(falcon.HTTPBadRequest):
            list(form)
    else:
        assert len(list(form)) == 1


class MultipartAnalyzer:
    def on_post(self, req, resp):
        values = []
        for part in req.media:
            values.append({
                'content_type': part.content_type,
                'data': part.data.decode(),
                'filename': part.filename,
                'name': part.name,
                'text': part.text,
            })

        resp.media = values


@pytest.fixture
def client():
    app = falcon.App()
    app.add_route('/media', MultipartAnalyzer())

    return testing.TestClient(app)


@pytest.fixture
def custom_client():
    def _factory(options):
        multipart_handler = media.MultipartFormHandler()
        for key, value in options.items():
            setattr(multipart_handler.parse_options, key, value)
        handlers = media.Handlers({
            falcon.MEDIA_JSON: media.JSONHandler(),
            falcon.MEDIA_MULTIPART: multipart_handler,
        })

        app = falcon.App()
        app.req_options.media_handlers = handlers
        app.add_route('/media', MultipartAnalyzer())

        return testing.TestClient(app)

    return _factory


def test_upload_multipart(client):
    resp = client.simulate_post(
        '/media',
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
            'text': 'world',
        },
        {
            'content_type': 'application/json',
            'data': '{"debug": true, "message": "Hello, world!", "score": 7}',
            'filename': None,
            'name': 'document',
            'text': None,
        },
        {
            'content_type': 'text/plain',
            'data': 'Hello, world!\n',
            'filename': 'test.txt',
            'name': 'file1',
            'text': 'Hello, world!\n',
        },
    ]


@pytest.mark.parametrize('truncated_by', [1, 2, 3, 4])
def test_truncated_form(client, truncated_by):
    resp = client.simulate_post(
        '/media',
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
        '/media',
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
        '/media',
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
        '/media',
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
        '/media',
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

    for index, part in enumerate(form):
        assert part.content_type == 'application/x-falcon-urandom'
        assert part.data == part_data[index]


def test_invalid_random_form(client):
    length = random.randint(2**20, 2**21)
    resp = client.simulate_post(
        '/media',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=' + HASH_BOUNDARY,
        },
        body=os.urandom(length))

    assert resp.status_code == 400
