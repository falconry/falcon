import sys

if sys.version_info < (3, 8):
    from typing_extensions import Protocol as Protocol
else:
    from typing import Protocol as Protocol
