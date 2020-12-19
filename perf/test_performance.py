import pytest

from metrics import hello


@pytest.mark.hello
def test_something():
    hello.run()
