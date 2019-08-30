import io

import pytest

import falcon
from falcon import media
from falcon import testing
from falcon.util import BufferedStream


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


EXAMPLES = {
    '5b11af82ab65407ba8cdccf37d2a9c4f': EXAMPLE1,
    '---------------------------1574247108204320607285918568': EXAMPLE2,
    'BOUNDARY': EXAMPLE3,
}


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
    stream = BufferedStream(io.BytesIO(data).read, len(data))
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
    stream = BufferedStream(io.BytesIO(data).read, len(data))
    form = handler.deserialize(stream, content_type, len(data))
    for part in form:
        assert part.filename == '⬅ Arrow.txt'
        assert part.secure_filename == '__Arrow.txt'

    data = data.replace(b'*=utf-8', b'*=esoteric')
    stream = BufferedStream(io.BytesIO(data).read, len(data))
    form = handler.deserialize(stream, content_type, len(data))
    for part in form:
        with pytest.raises(falcon.HTTPBadRequest):
            part.filename


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
    handlers = media.Handlers({
        falcon.MEDIA_JSON: media.JSONHandler(),
        falcon.MEDIA_MULTIPART: media.MultipartFormHandler(),
    })
    api = falcon.API()
    api.req_options.media_handlers = handlers
    api.add_route('/media', MultipartAnalyzer())

    return testing.TestClient(api)


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

        api = falcon.API()
        api.req_options.media_handlers = handlers
        api.add_route('/media', MultipartAnalyzer())

        return testing.TestClient(api)

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
        'description': 'unexpected EOF without delimiter',
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
        'description': 'unexpected form epilogue',
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


def test_too_many_body_parts(custom_client):
    client = custom_client({'max_body_part_count': 4})
    boundary = '---------------------------1574247108204320607285918568'
    resp = client.simulate_post(
        '/media',
        headers={
            'Content-Type':
            'multipart/form-data; boundary=' + boundary,
        },
        body=EXAMPLE2)

    assert resp.status_code == 400
    assert resp.json == {
        'description': 'maximum number of form body parts exceeded',
        'title': 'Malformed multipart/form-data request media',
    }
