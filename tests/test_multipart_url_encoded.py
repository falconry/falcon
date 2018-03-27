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


def assertFileUpload(fileStream, output):
    fileStream.set_max_upload_size(1 * 1024 * 1024)
    file_path = tempfile.gettempdir() + '/' + fileStream.name
    upload_status = fileStream.uploadto(file_path)
    if upload_status is True:
        with open(file_path, 'rb') as uploaded_file:
            content = uploaded_file.read()
            assert content == output
        os.remove(file_path)


def test_multipart_file_upload():
    """Ensure that multipart input format works as intended"""
    file1_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/banner.jpg'
    file2_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/banner.xcf'
    file3_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/logo.svg'
    file4_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/mstile-150x150.png'
    file5_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/mstile-310x310.png'
    with open(file1_path, 'rb') as file1,\
    open(file2_path, 'rb') as file2,\
    open(file3_path, 'rb') as file3,\
    open(file4_path, 'rb') as file4,\
    open(file5_path, 'rb') as file5:

        text_fields = {
            'name': 'John Doe',
            'foo': ['baz', 'bar'],
            'file1': 'John Doe',
            'file2': ['baz', 'bar'],
            'multifile': ['baz', 'bar'],
            'blank_field': ''
        }
        file_fields = {
            'file1': file1,
            'file2': file2,
            'multifile': file3,
            'file4': file4,
            'file5': file5,
            'enptyFileField': b''
        }
        prepared_request = requests.Request(
            method='POST',
            url='http://localhost/',
            data=text_fields,
            files=file_fields
        ).prepare()

        file1.seek(0)
        file1_content = file1.read()

        file2.seek(0)
        file2_content = file2.read()

        file3.seek(0)
        file3_content = file3.read()

        file4.seek(0)
        file4_content = file4.read()

        file5.seek(0)
        file5_content = file5.read()

        req = Request(testing.create_environ(
            host='example.com',
            path='/languages',
            app='backoffice',
            headers=prepared_request.headers,
            body=prepared_request.body,
            method='POST'
        ))

        assert req.form_data == text_fields

        assertFileUpload(req.files['file1'], file1_content)

        assertFileUpload(req.files['file2'], file2_content)

        assertFileUpload(req.files['multifile'], file3_content)

        assertFileUpload(req.files['file4'], file4_content)

        assertFileUpload(req.files['file5'], file5_content)
