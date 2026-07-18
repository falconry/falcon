FROM python:3.10-slim
LABEL org.opencontainers.image.authors="Falcon Framework Maintainers"

RUN pip install uv
RUN FALCON_DISABLE_CYTHON=Y uv pip install -v --no-cache-dir --no-binary falcon falcon
RUN uv pip install --no-cache-dir bottle Django Flask
COPY ./benchmark.sh /benchmark.sh

CMD ["/benchmark.sh"]
