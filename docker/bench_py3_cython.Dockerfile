FROM python:3.10
LABEL org.opencontainers.image.authors="Falcon Framework Maintainers"

# We don't currently benchmark JSON deserialization, but in the future we might
# RUN pip install orjson

RUN pip install uv
RUN uv pip install -v --no-cache-dir --no-binary falcon falcon
RUN uv pip install --no-cache-dir bottle Django Flask
COPY ./benchmark.sh /benchmark.sh

CMD ["/benchmark.sh"]
