FROM python:3.7
MAINTAINER Falcon Framework Maintainers

RUN pip install cython

# We don't currently benchmark JSON deserialization, but in the future we might
# RUN pip install orjson

RUN pip install -v --no-cache-dir --no-binary :all: falcon
RUN pip install --no-cache-dir bottle "django<2" flask
COPY ./benchmark.sh /benchmark.sh

CMD /benchmark.sh
