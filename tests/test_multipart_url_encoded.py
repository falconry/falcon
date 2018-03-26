import json
import os
import pytest
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
        method="POST"
    ))

    assert req.form_data == {'name': 'John Doe', 'foo': ['baz', 'bar']}


def test_multipart_file_upload():
    """Ensure that multipart input format works as intended"""
    # @hug.post()
    # def test_multipart_post(**kwargs):
    #     return kwargs

    # with open(os.path.join(BASE_DIRECTORY, 'artwork', 'logo.png'),'rb') as logo:
    #     prepared_request = requests.Request('POST', 'http://localhost/', files={'logo': logo}).prepare()
    #     logo.seek(0)
    #     output = json.loads(hug.defaults.output_format({'logo': logo.read()}).decode('utf8'))
    #     assert hug.test.post(api, 'test_multipart_post',  body=prepared_request.body,
    #                          headers=prepared_request.headers).data == output



    # import sys
    # import traceback
    # import os

    # import json
    # import datetime
    # import time

    # import fetcher_tables

    # import pymysql

    # import elasticsearch
    # from redis_crud import redisCrud

    # import threading

    # from pathlib import Path

    # import config

    # import data_source.dataGenerator as DATA_GENERATOR

    PATH_TO_UPLOAD_FILE = os.path.dirname(os.path.abspath(__file__)) + "/../logo/banner.jpg"

    with open(PATH_TO_UPLOAD_FILE,'rb') as logo:

        prepared_request = requests.Request('POST', 'http://localhost/', files={'logo': logo}).prepare()
        logo.seek(0)

        # output = json.loads(hug.defaults.output_format({'logo': logo.read()}).decode('utf8'))

        output = logo.read()

        req = Request(testing.create_environ(
            host='example.com',
            path='/languages',
            app='backoffice',
            headers=prepared_request.headers,
            body=prepared_request.body,
            method="POST"
        ))

        # assert req.files == {'name': 'John Doe', 'foo': ['baz', 'bar']}


        req.files["pancard"].set_max_upload_size(1*1024*1024)

        path = "/tmp/" + req.files["pancard"].name

        response = req.files["pancard"].uploadto("/tmp/" + path)

        
        assert req.files == output


        
        # assert hug.test.post(api, 'test_multipart_post',  body=prepared_request.body, headers=prepared_request.headers).data == output
