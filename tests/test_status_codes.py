import http
import sys

import pytest

from falcon import status_codes


class TestStatusCodes:
    @pytest.mark.skipif(
        sys.version_info < (3, 13), reason='Outdated http statuses definitions'
    )
    @pytest.mark.parametrize('status', status_codes.__all__)
    def test_statuses_are_in_compliance_with_http_from_python313(self, status):
        status_code, message = self._status_code_and_message(status)
        if status_code >= 700:
            pytest.skip('Codes above 700 are not defined in http package')
        http_status = http.HTTPStatus(status_code)
        if status_code in [418, 422]:
            assert http_status.phrase != message
        else:
            assert http_status.phrase == message

    def _status_code_and_message(self, status: str):
        status = getattr(status_codes, status)
        value, message = status.split(' ', 1)
        return int(value), message
