import django
from django.http import HttpResponse

_body = django.x_test_body
_headers = django.x_test_headers


def hello(request, account_id):
    user_agent = request.META['HTTP_USER_AGENT']  # NOQA
    limit = request.GET.get('limit', '10')  # NOQA
    response = HttpResponse(_body)

    for name, value in _headers.items():
        response[name] = value

    return response
