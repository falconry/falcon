FROM pypy:3.10-slim
LABEL org.opencontainers.image.authors="Falcon Framework Maintainers"

RUN pip install uv
RUN uv pip install --no-cache-dir falcon
RUN uv pip install --no-cache-dir bottle Django Flask
COPY ./benchmark.sh benchmark.sh

CMD ["/benchmark.sh"]
