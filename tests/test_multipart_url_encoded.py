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


def assertFileUpload(fileStream, output, path, upload_folder=None):
    fileStream.set_max_upload_size(1 * 1024 * 1024)
    if not upload_folder:
        upload_folder = tempfile.gettempdir()
    file_path = upload_folder + '/' + fileStream.name
    upload_status = fileStream.uploadto(file_path)
    if upload_status is True:
        with open(file_path, 'rb') as uploaded_file:
            content = uploaded_file.read()
            assert content == output
        assert fileStream.size == os.path.getsize(path)
        assert fileStream.type is not None
        assert fileStream.error is None
        os.remove(file_path)
    else:
        assert fileStream.error is not None


def test_multipart_file_upload():
    """Ensure that multipart input format works as intended"""
    file1_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/banner.jpg'
    file2_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/banner.xcf'
    file3_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/logo.svg'
    file4_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/mstile-150x150.png'
    file5_path = os.path.dirname(os.path.abspath(__file__)) + '/../logo/mstile-310x310.png'

    file1 = open(file1_path, 'rb')
    file2 = open(file2_path, 'rb')
    file3 = open(file3_path, 'rb')
    file4 = open(file4_path, 'rb')
    file5 = open(file5_path, 'rb')

    text_fields = {
        'name': 'John Doe',
        'foo': ['baz', 'bar', 'baz1', 'bar1'],
        'file1': 'John Doe',
        'file4': ['baz', 'bar', 'baz1', 'bar1'],
        'blank_field': ''
    }
    file_fields = [
        ('file1', file1),
        ('multifile', file2),
        ('multifile', file3),
        ('file4', file4),
        ('file5', file5),
        ('enptyFileField', b'')
    ]
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

    assertFileUpload(req.files['file1'], file1_content, file1_path)

    assert isinstance(req.files['multifile'], list) and len(req.files['multifile']) == 2
    k = 0
    multifile_data = [
        {
            "content": file2_content,
            "path": file2_path
        },
        {
            "content": file3_content,
            "path": file3_path
        }
    ]
    for fileStream in req.files['multifile']:
        assertFileUpload(fileStream, multifile_data[k]['content'], multifile_data[k]['path'])
        k = k + 1
    assertFileUpload(req.files['file4'], file4_content, file4_path)
    assertFileUpload(req.files['file5'], file5_content, file5_path, '/var')

    assert req.form_data == text_fields

    file1.close()
    file2.close()
    file3.close()
    file4.close()
    file5.close()


def test_simple_get():
    """Ensure that urlencoded input format works as intended"""
    req = Request(testing.create_environ(
        host='example.com',
        path='/languages',
        app='backoffice',
        method='GET'
    ))
    assert req.form_data is None
    assert req.files is None
