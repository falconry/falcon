import http
from typing import Dict
from typing import List
from typing import Tuple
from typing import Union

NormalizedHeaders = Dict[str, str]
RawHeaders = Union[NormalizedHeaders, List[Tuple[str, str]], None]
Status = Union[http.HTTPStatus, str, int]
