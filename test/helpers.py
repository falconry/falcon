class StartResponseMock:
    def __init__(self):
        self._called = 0
        self.status = None
        self.headers = None
    
    def __call__(self, status, headers):
        self._called += 1
        self.status = status
        self.headers = headers

    def call_count(self):
        return self._called


def create_environ(path='/', query_string=''):
    return {
        'SERVER_SOFTWARE': 'WSGIServer/0.1 Python/2.7.3',
        'TERM_PROGRAM_VERSION': '309',
        'REQUEST_METHOD': 'GET',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'HOME': '/Users/kurt',
        'DISPLAY': '/tmp/launch-j5GrQm/org.macosforge.xquartz:0',
        'TERM_PROGRAM': 'Apple_Terminal',
        'LANG': 'en_US.UTF-8',
        'SHELL': '/bin/bash',
        '_': '/Library/Frameworks/Python.framework/Versions/2.7/bin/python',
        'SERVER_PORT': '8003',
        'HTTP_HOST': 'localhost:8003',
        'SCRIPT_NAME': '',
        'HTTP_ACCEPT': '*/*',
        'wsgi.version': '(1, 0)',
        'wsgi.run_once': 'False',
        'wsgi.multiprocess': 'False',
        '__CF_USER_TEXT_ENCODING': '0x1F5:0:0',
        'USER': 'kurt',
        'LOGNAME': 'kurt',
        'PATH_INFO': path,
        'QUERY_STRING': query_string,
        'HTTP_USER_AGENT': 'curl/7.24.0 (x86_64-apple-darwin12.0) '
                           'libcurl/7.24.0 OpenSSL/0.9.8r zlib/1.2.5',
        'SERVER_NAME': 'WSGIRef',
        'REMOTE_ADDR': '127.0.0.1',
        'SHLVL': '1',
        'wsgi.url_scheme': 'http',
        'CONTENT_LENGTH': '',
        'TERM_SESSION_ID': '51EE7744-E45F-455C-AC2E-E232A521094D',
        'SSH_AUTH_SOCK': '/tmp/launch-0N2o9o/Listeners',
        'Apple_PubSub_Socket_Render': '/tmp/launch-2ZwqSM/Render',
        'wsgi.multithread': 'True',
        'TMPDIR': '/var/folders/4g/mzp3qmyn33v_xjn1h69y1d3h0000gn/T/',
        'LSCOLORS': 'ExCxFxDxBxegedabagaced',
        'GATEWAY_INTERFACE': 'CGI/1.1',
        'CLICOLOR': '1',
        'Apple_Ubiquity_Message': '/tmp/launch-NTB6Mp/Apple_Ubiquity_Message',
        'PWD': '/Users/kurt/Projects/rax/falcon',
        'CONTENT_TYPE': 'text/plain',
        'wsgi.file_wrapper': 'wsgiref.util.FileWrapper',
        'REMOTE_HOST': '1.0.0.127.in-addr.arpa',
        'COMMAND_MODE': 'unix2003'
    }
