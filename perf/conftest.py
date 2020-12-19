import pathlib
# import subprocess

HERE = pathlib.Path(__file__).resolve().parent
print(HERE)


def pytest_configure(config):
    config.addinivalue_line('markers', 'hello: "hello" performance metric')
