from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

module_names = (
    'api',
    'api_helpers',
    'request',
    'request_helpers',
    'response',
    'response_helpers',
    'responders',
    'http_error',
    'exceptions'
)

ext_modules = [Extension(m, [m + '.py']) for m in module_names]

setup(
    name='Falcon',
    cmdclass={'build_ext': build_ext},
    ext_modules=ext_modules
)
