import os
import tempfile

import requests

from falcon.request import Request
import falcon.testing as testing


def test_urlencoded():
    """Ensure that urlencoded input format works as intended"""
    test_data = b'foo=baz&foo=bar&name=John+Doe'
    headers = {'content-type': 'application/x-www-form-urlencoded'}
    req = Request(testing.create_environ(
        host='example.com',
        path='/languages',
        app='backoffice',
        headers=headers,
        body=test_data,
        method='POST'
    ))
    assert req.form_data == {'name': 'John Doe', 'foo': ['baz', 'bar']}


def test_multipart_file_upload():
    """Ensure that multipart input format works as intended"""
    PATH_TO_UPLOAD_FILE = os.path.dirname(os.path.abspath(__file__)) + '/../logo/banner.jpg'
    with open(PATH_TO_UPLOAD_FILE, 'rb') as logo:
        prepared_request = requests.Request(
            'POST',
            'http://localhost/',
            files={'logo': logo}
        ).prepare()
        logo.seek(0)
        output = logo.read()
        req = Request(testing.create_environ(
            host='example.com',
            path='/languages',
            app='backoffice',
            headers=prepared_request.headers,
            body=prepared_request.body,
            method='POST'
        ))
        req.files['logo'].set_max_upload_size(1 * 1024 * 1024)
        file_path = tempfile.gettempdir() + '/' + req.files['logo'].name
        upload_status = req.files['logo'].uploadto(file_path)
        if upload_status is True:
            with open(file_path, 'rb') as uploaded_file:
                content = uploaded_file.read()
                assert content == output
            os.remove(file_path)
