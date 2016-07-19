"""
Utility functions for the Falcon framework.
These modules are already imported by the falcon module and can be accessed directly.
"""

# Hoist misc. utils
from falcon.util import structures
from falcon.util.misc import *  # NOQA
from falcon.util.time import *  # NOQA

CaseInsensitiveDict = structures.CaseInsensitiveDict
