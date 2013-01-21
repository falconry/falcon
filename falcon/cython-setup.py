from distutils.core import setup
from distutils.extension import Extension
from Cython.Distutils import build_ext

ext_modules = [
    Extension('api', ['api.py']),
    Extension('api_helpers', ['api_helpers.py']),
    Extension('request', ['request.py']),
    Extension('request_helpers', ['request_helpers.py']),
    Extension('response', ['response.py']),
    Extension('responders', ['responders.py'])
]

setup(
    name='Falcon',
    cmdclass={'build_ext': build_ext},
    ext_modules=ext_modules
)
